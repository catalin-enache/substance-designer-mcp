"""
MCP server for Adobe Substance 3D Designer.

Talks to the sd_bridge plugin running inside Designer (127.0.0.1:9877, token in
~/.sd_bridge_token) and wraps Designer's sbscooker / sbsrender command-line tools.
"""
import io
import json
import re
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image as PILImage
from mcp.server.mcpserver import MCPServer, Image
from mcp.server.mcpserver.exceptions import ToolError

PORT = int(os.environ.get('SD_BRIDGE_PORT', '9877'))
TOKEN_FILE = os.path.expanduser('~/.sd_bridge_token')

# Folder holding sbscooker / sbsrender. Override with SD_DESIGNER_BIN_DIR.
DEFAULT_BIN_DIRS = {
    'darwin': ['/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app/Contents/MacOS'],
    'win32': [r'C:\Program Files\Adobe\Adobe Substance 3D Designer'],
}
EXE = '.exe' if sys.platform == 'win32' else ''


def _find_tool(name):
    dirs = [os.environ['SD_DESIGNER_BIN_DIR']] if os.environ.get('SD_DESIGNER_BIN_DIR') else []
    dirs += DEFAULT_BIN_DIRS.get(sys.platform, [])
    for d in dirs:
        path = os.path.join(d, name + EXE)
        if os.path.isfile(path):
            return path
    return shutil.which(name)


SBSCOOKER = _find_tool('sbscooker')
SBSRENDER = _find_tool('sbsrender')

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS_MD = os.path.join(os.path.dirname(HERE), 'AGENTS.md')
with open(os.path.join(HERE, 'designer_helpers.py')) as _f:
    HELPERS = _f.read()


def _agent_guide():
    try:
        with open(AGENTS_MD, encoding='utf-8') as f:
            return f.read()
    except OSError:
        return 'AGENTS.md not found next to mcp_server/.'


server = MCPServer(
    name='substance-designer',
    # The full agent notes ship with the server so every client gets them
    instructions=_agent_guide(),
)


@server.resource('designer://agents-guide', name='agents-guide', mime_type='text/markdown',
                 description='Notes and API gotchas for agents driving Substance Designer (AGENTS.md).')
def agents_guide() -> str:
    return _agent_guide()


def _with_undo(code, label):
    # Group everything the script does into one undo step in Designer
    return ('from sd.api.sdhistoryutils import SDHistoryUtils as _SDH\n'
            'with _SDH.UndoGroup(%r):\n'
            '    exec(compile(%r, __file__, "exec"), globals())\n' % (label, code))


def _helpers_call(call):
    return HELPERS + '\n\n' + call + '\n'


def _send(request, wait):
    """Send one JSON request to the plugin and return its reply dict."""
    try:
        with open(TOKEN_FILE) as f:
            request['token'] = f.read().strip()
    except FileNotFoundError:
        raise ToolError('No bridge token found. Is the sd_bridge plugin loaded in Designer?')
    try:
        with socket.create_connection(('127.0.0.1', PORT), timeout=wait) as s:
            s.sendall(json.dumps(request).encode('utf-8'))
            s.shutdown(socket.SHUT_WR)
            data = b''
            while chunk := s.recv(65536):
                data += chunk
    except ConnectionRefusedError:
        raise ToolError('Designer is not reachable. Start Designer (the sd_bridge plugin loads on startup).')
    except socket.timeout:
        raise ToolError('No reply from Designer after %ds. It may be busy with a long call; '
                        'try cancel_designer_job or check Designer.' % wait)
    return json.loads(data.decode('utf-8'))


def _bridge(code, path=None, timeout=None):
    # timeout: seconds before the plugin aborts the script (None = no limit)
    request = {'code': code, 'path': path}
    if timeout:
        request['timeout'] = timeout
    reply = _send(request, wait=(timeout or 900) + 60)
    text = reply['output']
    if not reply['ok']:
        text += '\n--- ERROR ---\n' + reply['error']
    return text or '(no output)'


@server.tool()
def designer_status() -> str:
    """Report Designer's version, the bridge state (idle/running) and the open user packages."""
    bridge = _send({'cmd': 'status'}, wait=10)
    return bridge.get('output', '') + '\n' + _bridge(
        "import sd\n"
        "app = sd.getContext().getSDApplication()\n"
        "print('Designer', app.getVersion())\n"
        "for p in app.getPackageMgr().getUserPackages():\n"
        "    print('package:', p.getFilePath() or '(unsaved)')\n"
        "    for r in p.getChildrenResources(True):\n"
        "        print('   ', type(r).__name__, r.getIdentifier())\n"
    )


@server.tool()
def cancel_designer_job() -> str:
    """Abort the script currently running in Designer (and drop queued ones). Takes effect the
    next time Python code runs, so one long C++ call (e.g. graph.compute()) finishes first."""
    return _send({'cmd': 'cancel'}, wait=10).get('output', '')


@server.tool()
def execute_designer_code(code: str, undo_label: str = 'Claude: code', timeout_s: int = 120) -> str:
    """Run Python inside Substance Designer (full `sd` API) and return printed output and errors.
    All changes form one undo step named `undo_label` (Ctrl+Z in Designer reverts them).
    The script is aborted after `timeout_s` seconds (0 = no limit)."""
    return _bridge(_with_undo(code, undo_label), '<execute_designer_code>', timeout_s)


@server.tool()
def run_designer_script(path: str, timeout_s: int = 600) -> str:
    """Run a Python file inside Substance Designer; `__file__` is set to its absolute path.
    All changes form one undo step named after the file. Aborted after `timeout_s` seconds
    (0 = no limit)."""
    path = os.path.abspath(os.path.expanduser(path))
    with open(path) as f:
        return _bridge(_with_undo(f.read(), 'Claude: ' + os.path.basename(path)), path, timeout_s)


@server.tool()
def describe_graph(graph: str | None = None, node_ids: list[str] | None = None,
                   include_params: bool = False, limit: int = 400) -> str:
    """List a graph's nodes: id, type (atomic name or instance:<library graph>), position and
    incoming connections (`input<-sourceNodeId.output`). `graph` is the graph identifier
    (default: the graph open in Designer's UI). `include_params` adds every parameter that
    differs from its default. Use `node_ids` to focus on a few nodes."""
    return _bridge(_helpers_call('describe_graph(%r, %r, %r, %d)' % (graph, node_ids, include_params, limit)), timeout=60)


@server.tool()
def describe_node(definition: str) -> str:
    """Show a node type's connectors and parameters (ids, types, labels, defaults, enum values).
    `definition`: atomic name ('levels', 'blend', 'sbs::compositing::normal') or library package
    '<file>[/<graph id>]' as found in Designer's packages folder ('tile_generator', 'hbao.sbs/hbao')."""
    return _bridge(_helpers_call('describe_node(%r)' % definition), timeout=60)


@server.tool()
def preview_node(node_id: str, graph: str | None = None, output: str | None = None,
                 max_size: int = 512) -> Image:
    """Compute the graph in Designer and return the image produced by one node (any node, not
    just outputs). Get node ids from describe_graph. `output` picks a connector on multi-output
    nodes (default: first). `graph` defaults to the graph open in Designer's UI."""
    tmp_dir = tempfile.mkdtemp(prefix='sd_preview_')
    out_path = os.path.join(tmp_dir, 'node.png')
    try:
        # Wrapped in an undo step because a temporary output node may be added and removed
        text = _bridge(_with_undo(_helpers_call('save_node_output(%r, %r, %r, %r)' % (
            node_id, out_path, graph, output)), 'Claude: preview node'), '<preview_node>', 300)
        if not os.path.exists(out_path):
            # Keep only the final error line(s) from Designer's traceback
            raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'preview failed')
        im = _load_8bit(out_path)
        im.thumbnail((max_size, max_size))
        buf = io.BytesIO()
        im.save(buf, format='PNG')
        return Image(data=buf.getvalue(), format='png')
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@server.tool()
def screenshot_designer(panel: str = 'window', max_size: int = 1400) -> Image:
    """Capture Designer's own UI (never other apps): panel = window, graph, 2d, 3d, explorer,
    parameters, library or console. Shows what the user sees (node layout, 2D view, properties).
    '3d' returns the 3D view's own render (material on the mesh); the user's clipboard is
    restored afterwards. Inside 'window' the 3D view appears black."""
    tmp_dir = tempfile.mkdtemp(prefix='sd_shot_')
    out_path = os.path.join(tmp_dir, 'shot.png')
    try:
        text = _bridge(_helpers_call('save_screenshot(%r, %r)' % (panel, out_path)), timeout=60)
        if not os.path.exists(out_path):
            raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'screenshot failed')
        im = PILImage.open(out_path).convert('RGB')
        im.thumbnail((max_size, max_size))
        buf = io.BytesIO()
        im.save(buf, format='PNG')
        return Image(data=buf.getvalue(), format='png')
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@server.tool()
def save_package(graph_or_path: str | None = None, save_as: str | None = None) -> str:
    """Save an open package from Designer. graph_or_path: a graph identifier or the package's
    file path (default: graph open in the UI). save_as: new absolute .sbs path (required for
    packages that were never saved)."""
    return _checked(_bridge(_helpers_call('save_package(%r, %r)' % (graph_or_path, save_as)), timeout=120))


@server.tool()
def export_outputs(graph: str, output_dir: str, outputs: list[str] | None = None,
                   file_format: str = 'png') -> str:
    """Compute a graph inside Designer and save its output nodes' textures directly (no
    sbscooker/sbsrender), named after the output identifiers. Reflects the current, possibly
    unsaved, state of the graph. outputs: subset of output identifiers (default: all)."""
    return _checked(_bridge(_helpers_call('export_outputs(%r, %r, %r, %r)' % (
        graph, output_dir, outputs, file_format)), timeout=600))


def _edit(call, label):
    # Quick edits run inside one undo step, like execute_designer_code
    return _checked(_bridge(_with_undo(HELPERS + '\n\n' + call + '\n', label), '<quick edit>', 60))


@server.tool()
def add_node(definition: str, graph: str | None = None, position: list[float] | None = None,
             params: dict | None = None) -> str:
    """Add a node and return its id. definition: atomic ('levels', 'blend') or library
    ('tile_generator', 'hbao.sbs/hbao'). position: [x, y] (default: right of existing nodes).
    params: initial parameter values (same rules as set_params). One undo step."""
    return _edit('add_node(%r, %r, %r, %r)' % (graph, definition, position, params),
                 'Claude: add ' + definition)


@server.tool()
def set_params(node_id: str, params: dict, graph: str | None = None) -> str:
    """Set parameters on a node (node_id 'graph' = the graph itself, e.g. $outputsize).
    Values are converted to the parameter's type: numbers, bools, lists for vectors/colors
    ([r,g,b(,a)]), enums by id or number ('max' or 5). Prints old -> new. One undo step."""
    return _edit('set_params(%r, %r, %r)' % (graph, node_id, params), 'Claude: set params on ' + node_id)


@server.tool()
def connect(from_node: str, to_node: str, to_input: str, from_output: str | None = None,
            graph: str | None = None) -> str:
    """Connect from_node's output (default: its first) to to_node's input connector
    (replaces an existing link on that input). One undo step."""
    return _edit('connect(%r, %r, %r, %r, %r)' % (graph, from_node, to_node, to_input, from_output),
                 'Claude: connect')


@server.tool()
def disconnect(node_id: str, input_id: str, graph: str | None = None) -> str:
    """Remove the connection(s) going into node_id's input connector. One undo step."""
    return _edit('disconnect(%r, %r, %r)' % (graph, node_id, input_id), 'Claude: disconnect')


@server.tool()
def delete_nodes(node_ids: list[str], graph: str | None = None) -> str:
    """Delete nodes (and their connections) from a graph. One undo step."""
    return _edit('delete_nodes(%r, %r)' % (graph, node_ids), 'Claude: delete nodes')


@server.tool()
def open_graph(graph: str, node_id: str | None = None) -> str:
    """Open a graph in Designer's graph editor (so the user and screenshot_designer see it);
    with node_id, also centre the graph view on that node."""
    return _checked(_bridge(_helpers_call('open_graph(%r, %r)' % (graph, node_id)), timeout=60))


@server.tool()
def create_graph(name: str, save_path: str | None = None, size_log2: int = 11) -> str:
    """Create a new package with one empty compositing graph (output size 2^size_log2,
    default 2048). save_path: optional .sbs path to save it to. One undo step."""
    return _edit('create_graph(%r, %r, %d)' % (name, save_path, size_log2), 'Claude: create graph ' + name)


@server.tool()
def move_nodes(positions: dict[str, list[float]], graph: str | None = None) -> str:
    """Move nodes: {"node_id": [x, y], ...}. One undo step."""
    return _edit('move_nodes(%r, %r)' % (graph, positions), 'Claude: move nodes')


_LIBRARY_CACHE = {}


def _library_index():
    """Scan Designer's library packages once: graph id, label, category, description."""
    if 'entries' in _LIBRARY_CACHE:
        return _LIBRARY_CACHE
    lines = _bridge(_helpers_call('list_atomic()'), timeout=60).splitlines()
    resources = [l.split('=', 1)[1] for l in lines if l.startswith('RESOURCES_DIR=')][0]
    atomic = [l.split('=', 1)[1] for l in lines if l.startswith('ATOMIC=')]
    pkg_dir = os.path.join(resources, 'packages')
    entries = []
    for file_name in sorted(os.listdir(pkg_dir)):
        if not file_name.endswith('.sbs'):
            continue
        try:
            root = ET.parse(os.path.join(pkg_dir, file_name)).getroot()
        except ET.ParseError:
            continue
        for g in root.iter('graph'):
            ident = g.find('identifier')
            if ident is None:
                continue
            attrs = g.find('attributes')
            def attr(tag):
                el = attrs.find(tag) if attrs is not None else None
                return el.get('v') if el is not None else ''
            entries.append({'file': file_name, 'graph': ident.get('v'), 'label': attr('label'),
                            'category': attr('category'), 'description': attr('description'),
                            'hidden': (attr('hideInLibrary') or '0') == '1'})
    _LIBRARY_CACHE.update(entries=entries, atomic=atomic, pkg_dir=pkg_dir)
    return _LIBRARY_CACHE


@server.tool()
def search_nodes(query: str, limit: int = 30, include_hidden: bool = False) -> str:
    """Find node types by name, label, category or description, across atomic nodes and
    Designer's whole node library (not just loaded packages). Results show the `definition`
    to pass to add_node / describe_node. Words in the query must all match."""
    index = _library_index()
    words = [w.lower() for w in query.split()]
    def matches(text):
        text = text.lower()
        return all(w in text for w in words)
    q = query.lower().strip()
    def rank(name):
        # exact name, then name prefix, then all words in the name, then description-only hits
        name = name.lower()
        return 0 if name == q else 1 if name.startswith(q) else 2 if matches(name) else 3
    out = []
    for a in index['atomic']:
        short = a.replace('sbs::compositing::', '')
        if matches(short + ' ' + a):
            out.append((rank(short), 'atomic   %-28s definition=%r' % (short, short)))
    for e in index['entries']:
        if e['hidden'] and not include_hidden:
            continue
        haystack = ' '.join((e['file'], e['graph'], e['label'], e['category'], e['description']))
        if matches(haystack):
            base = e['file'][:-4]
            definition = base if e['graph'] == base else '%s/%s' % (e['file'], e['graph'])
            desc = re.sub(r'<[^>]+>', ' ', e['description'] or '').replace('\n', ' ')
            desc = re.sub(r'\s+', ' ', desc).strip()
            name = e['label'] or e['graph']
            out.append((min(rank(name), rank(e['graph'])), 'library  %-28s definition=%r  [%s]%s' % (
                name, definition, e['category'], ('  ' + desc[:90]) if desc else '')))
    if not out:
        return 'No node types match %r.' % query
    out = [line for _, line in sorted(out, key=lambda item: item[0])]
    more = '' if len(out) <= limit else '\n... %d more (refine the query or raise limit)' % (len(out) - limit)
    return '\n'.join(out[:limit]) + more


_PIXEL_TYPES = {'8': (np.uint8, 255.0), '16': (np.uint16, 65535.0), '16F': (np.float16, 1.0), '32F': (np.float32, 1.0)}


def _decode_pixels(raw, meta):
    """Raw Designer pixel buffer -> float array (H, W, C), values normalised to 0..1 for ints."""
    fmt_name = meta['format']                       # e.g. RGBA16, LUM8, RGBA32F
    channels = 4 if fmt_name.startswith('RGBA') else 1
    depth = fmt_name[4:] if channels == 4 else fmt_name[3:]
    if depth not in _PIXEL_TYPES:
        raise ToolError('unsupported pixel format %s' % fmt_name)
    dtype, scale = _PIXEL_TYPES[depth]
    rows = np.frombuffer(raw, dtype=np.uint8).reshape(meta['height'], meta['pitch'])
    rows = rows[:, :meta['width'] * meta['bpp']].copy()
    data = rows.view(dtype).reshape(meta['height'], meta['width'], channels).astype(np.float64)
    return data / scale, ('RGBA' if channels == 4 else 'L')


@server.tool()
def node_stats(node_id: str, graph: str | None = None, output: str | None = None,
               region: list[int] | None = None, points: list[list[int]] | None = None) -> str:
    """Exact pixel statistics of any node's output (computed in Designer, read from the raw
    buffer, so 16-bit/float precision is kept). Per channel: min, max, mean, std.
    region: [x0, y0, x1, y1] in pixels to restrict the stats. points: [[x, y], ...] pixel
    values to sample. Values are 0..1 for integer formats. Use it to verify results numerically."""
    tmp_dir = tempfile.mkdtemp(prefix='sd_px_')
    raw_path = os.path.join(tmp_dir, 'pixels.raw')
    try:
        text = _bridge(_with_undo(_helpers_call('dump_node_pixels(%r, %r, %r, %r)' % (
            node_id, raw_path, graph, output)), 'Claude: node stats'), '<node_stats>', 300)
        found = re.search(r'PIXELS=(\{.*\})', text)
        if not found or not os.path.exists(raw_path):
            raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'no pixel data')
        meta = json.loads(found.group(1))
        with open(raw_path, 'rb') as f:
            data, layout = _decode_pixels(f.read(), meta)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    h, w, _ = data.shape
    lines = ['%s: %dx%d %s' % (meta['node'], w, h, meta['format'])]
    area = data
    if region:
        x0, y0, x1, y1 = region
        area = data[max(0, y0):min(h, y1), max(0, x0):min(w, x1)]
        lines.append('region [%d,%d,%d,%d] (%dx%d px)' % (x0, y0, x1, y1, area.shape[1], area.shape[0]))
    names = 'RGBA' if layout == 'RGBA' else 'L'
    for ch, name in enumerate(names):
        a = area[:, :, ch]
        lines.append('%s: min %.4f  max %.4f  mean %.4f  std %.4f' % (name, a.min(), a.max(), a.mean(), a.std()))
    for x, y in points or []:
        if 0 <= x < w and 0 <= y < h:
            lines.append('pixel (%d,%d): %s' % (x, y, ', '.join('%s=%.4f' % (n, v) for n, v in zip(names, data[y, x]))))
        else:
            lines.append('pixel (%d,%d): outside the %dx%d image' % (x, y, w, h))
    return '\n'.join(lines)


@server.tool()
def expose_param(node_id: str, param: str, graph: str | None = None, input_id: str | None = None,
                 label: str | None = None, default: float | int | bool | str | list[float] | None = None,
                 min: float | None = None, max: float | None = None, step: float | None = None,
                 group: str | None = None) -> str:
    """Expose a node parameter as a graph input (same type as the parameter; enums become ints),
    like Designer's own "Expose" action. The input starts at the parameter's current value
    unless `default` is given; min/max/step/group set the slider. The input then shows up in
    sbsar_info and can be set with render_sbs(params=...). One undo step."""
    return _edit('expose_param(%r, %r, %r, %r, %r, %r, %r, %r, %r, %r)' % (
        graph, node_id, param, input_id, label, default, min, max, step, group), 'Claude: expose ' + param)


@server.tool()
def list_graph_inputs(graph: str | None = None) -> str:
    """List a graph's exposed inputs (type, value, label/min/max, which node parameters they
    drive) and whether its output size is fixed or overridable."""
    return _checked(_bridge(_helpers_call('list_graph_inputs(%r)' % graph), timeout=60))


@server.tool()
def remove_graph_input(input_id: str, graph: str | None = None) -> str:
    """Delete an exposed graph input. Parameters it drove keep its current value. One undo step."""
    return _edit('remove_graph_input(%r, %r)' % (graph, input_id), 'Claude: remove input ' + input_id)


@server.tool()
def set_graph_size(size_log2: int, graph: str | None = None, overridable: bool = True) -> str:
    """Set the graph's output size to 2^size_log2. overridable=True (default) makes the size
    follow the parent with that default, so render_sbs(size_log2=...) can override it;
    False fixes it. One undo step."""
    return _edit('set_graph_size(%r, %d, %r)' % (graph, size_log2, overridable), 'Claude: set graph size')


@server.tool()
def apply_edits(ops: list[dict], graph: str | None = None) -> str:
    """Run several edits in one call and one undo step. Each op is a dict:
    {"op": "add", "definition": "levels", "ref": "lv", "position"?: [x, y], "params"?: {...}}
    {"op": "set", "node": "lv", "params": {...}}            (node: a ref, a node id, or "graph")
    {"op": "connect", "from": "a", "to": "lv", "input": "input1", "output"?: "..."}
    {"op": "disconnect", "node": "lv", "input": "input1"}
    {"op": "move", "node": "lv", "position": [x, y]}
    {"op": "delete", "node": "lv"}
    {"op": "expose", "node": "lv", "param": "...", "input_id"?, "label"?, "default"?, "min"?, "max"?}
    Refs let later ops use nodes added earlier in the batch. Stops at the first failing op
    (earlier ops stay applied; Ctrl+Z on the graph reverts the whole batch)."""
    return _edit('apply_edits(%r, %r)' % (graph, ops), 'Claude: apply %d edits' % len(ops))


DESIGNER_APP = {
    'darwin': '/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app',
    'win32': r'C:\Program Files\Adobe\Adobe Substance 3D Designer\Adobe Substance 3D Designer.exe',
}


@server.tool()
def launch_designer(wait_s: int = 180) -> str:
    """Start Substance Designer if it isn't running and wait until the sd_bridge plugin answers.
    Override the app location with SD_DESIGNER_APP."""
    try:
        return 'Designer already running: ' + _send({'cmd': 'status'}, wait=5).get('output', '')
    except ToolError:
        pass
    app = os.environ.get('SD_DESIGNER_APP') or DESIGNER_APP.get(sys.platform)
    if not app or not os.path.exists(app):
        raise ToolError('Designer not found at %r; set SD_DESIGNER_APP' % app)
    if sys.platform == 'darwin':
        subprocess.Popen(['open', '-a', app])
    elif sys.platform == 'win32':
        os.startfile(app)
    else:
        subprocess.Popen([app])
    started = time.time()
    while time.time() - started < wait_s:
        time.sleep(2)
        try:
            status = _send({'cmd': 'status'}, wait=5).get('output', '')
            return 'Designer started in %.0fs: %s' % (time.time() - started, status)
        except ToolError:
            continue
    raise ToolError('Designer did not answer within %ds. It may be showing a dialog, or the '
                    'sd_bridge plugin did not load (check the Designer log).' % wait_s)


def _checked(text):
    # Turn a Designer-side traceback into a clean tool error
    if '--- ERROR ---' in text:
        raise ToolError(text.strip().splitlines()[-1])
    return text


def _value_arg(value):
    if isinstance(value, (list, tuple)):
        return ','.join(str(v) for v in value)
    if isinstance(value, bool):
        return '1' if value else '0'
    return str(value)


@server.tool()
def render_sbs(sbs_path: str, output_dir: str, size_log2: int | None = None, graph: str | None = None,
               outputs: list[str] | None = None, params: dict[str, float | int | bool | list[float]] | None = None,
               output_format: str = 'png') -> str:
    """Cook a .sbs (or take a .sbsar) and render outputs to files named after the output nodes.
    size_log2: output size override (11 = 2048). graph: graph identifier inside the package
    (default: every graph). outputs: output identifiers to render (default: all).
    params: exposed input values, e.g. {"wear": 0.5, "tint": [1, 0.8, 0.6]}.
    output_format: png, tga, exr, jpg, ... Use sbsar_info to list graphs/inputs/outputs."""
    if not (SBSCOOKER and SBSRENDER):
        raise ToolError('sbscooker/sbsrender not found. Set SD_DESIGNER_BIN_DIR to the folder containing '
                        'them (the Designer install folder on Windows, .app/Contents/MacOS on macOS).')
    sbsar = _cook(sbs_path)
    output_dir = os.path.abspath(os.path.expanduser(output_dir))
    os.makedirs(output_dir, exist_ok=True)
    cmd = [SBSRENDER, 'render', sbsar, '--output-path', output_dir,
           '--output-name', '{outputNodeName}', '--output-format', output_format]
    if output_format == 'png':
        cmd += ['--png-format-compression', 'best_speed']
    if graph:
        cmd += ['--input-graph', graph if '://' in graph else 'pkg://' + graph]
    for name in outputs or []:
        cmd += ['--input-graph-output', name]
    values = dict(params or {})
    # sbsrender silently ignores values for inputs the graph doesn't expose, so warn up front
    exposed = _exposed_inputs(sbsar)
    notes = []
    if size_log2:
        values['$outputsize'] = [size_log2, size_log2]
    elif '$outputsize' in exposed and '$outputsize' not in values:
        # An overridable graph renders at sbsrender's own 256 px default unless told otherwise;
        # use the graph's default parent size from the .sbs so the result matches Designer
        default = _default_parent_log2(sbs_path, graph)
        if default:
            values['$outputsize'] = [default, default]
            notes.append('size: using the graph\'s default parent size, %d px (from the .sbs)' % 2 ** default)
    warnings = ['WARNING: input %r is not exposed by this .sbsar, so the value is ignored%s'
                % (key, ' (graph output size is fixed; expose $outputsize or make it relative '
                        'to parent to allow size overrides)' if key == '$outputsize' else '')
                for key in values if key not in exposed]
    for key, value in values.items():
        cmd += ['--set-value', '%s@%s' % (key, _value_arg(value))]
    before = _snapshot(output_dir)
    render = subprocess.run(cmd, capture_output=True, text=True)
    if render.returncode != 0:
        raise ToolError('sbsrender failed:\n' + render.stdout[-3000:] + render.stderr[-3000:])
    after = _snapshot(output_dir)
    files = sorted(f for f, stamp in after.items() if before.get(f) != stamp)
    if not files:
        raise ToolError('sbsrender produced no files (check graph/output names with sbsar_info).\n'
                        + render.stdout[-2000:])
    lines = ['%s  %s' % (f, _image_size(os.path.join(output_dir, f))) for f in files]
    return '\n'.join(warnings + notes + ['Rendered %d file(s) to %s:' % (len(files), output_dir)] + lines)


def _default_parent_log2(sbs_path, graph=None):
    """The graph's defaultParentSize option ("9x9" = 512 px) from a .sbs, or None."""
    path = os.path.abspath(os.path.expanduser(sbs_path))
    if not path.endswith('.sbs') or not os.path.exists(path):
        return None
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    wanted = graph.split('://')[-1] if graph else None
    for g in root.iter('graph'):
        ident = g.find('identifier')
        if wanted and (ident is None or ident.get('v') != wanted):
            continue
        for option in g.iter('option'):
            name = option.find('name')
            if name is not None and name.get('v') == 'defaultParentSize':
                width = option.find('value').get('v').split('x')[0]
                return int(width) if width.isdigit() else None
    return None


def _exposed_inputs(sbsar):
    info = subprocess.run([SBSRENDER, 'info', sbsar], capture_output=True, text=True).stdout
    return {line.split()[1] for line in info.splitlines() if line.strip().startswith('INPUT ')}


def _image_size(path):
    try:
        with PILImage.open(path) as im:
            return '%dx%d' % im.size
    except Exception:
        return ''


def _snapshot(folder):
    # name -> (mtime_ns, size), to tell which files a render wrote
    return {f: (st.st_mtime_ns, st.st_size) for f in os.listdir(folder)
            for st in [os.stat(os.path.join(folder, f))]}


def _cook(sbs_path):
    path = os.path.abspath(os.path.expanduser(sbs_path))
    if path.endswith('.sbsar'):
        return path
    cook = subprocess.run([SBSCOOKER, '--inputs', path, '--output-path', os.path.dirname(path)],
                          capture_output=True, text=True)
    sbsar = os.path.splitext(path)[0] + '.sbsar'
    if cook.returncode != 0 or not os.path.exists(sbsar):
        raise ToolError('sbscooker failed:\n' + cook.stdout[-3000:] + cook.stderr[-3000:])
    return sbsar


@server.tool()
def sbsar_info(sbs_path: str) -> str:
    """List graphs, exposed inputs (with types) and outputs of a .sbs/.sbsar, i.e. what
    render_sbs can take as graph/outputs/params."""
    if not (SBSCOOKER and SBSRENDER):
        raise ToolError('sbscooker/sbsrender not found. Set SD_DESIGNER_BIN_DIR.')
    info = subprocess.run([SBSRENDER, 'info', _cook(sbs_path)], capture_output=True, text=True)
    return info.stdout.strip() or info.stderr.strip()


def _load_8bit(path):
    im = PILImage.open(path)
    if im.mode.startswith('I'):
        a = np.array(im).astype('float32')
        a = (a / (65535.0 if a.max() > 255 else 255.0) * 255).clip(0, 255).astype('uint8')
        im = PILImage.fromarray(a)
    return im.convert('RGB')


@server.tool()
def preview_maps(map_dir: str, names: list[str] | None = None, tile_size: int = 384,
                 crop: list[int] | None = None) -> Image:
    """Return a side-by-side preview of rendered maps (PNG files in map_dir). `names` picks
    maps by file stem (default: all). `crop` = [x0, y0, x1, y1] in source pixels to zoom in."""
    map_dir = os.path.abspath(os.path.expanduser(map_dir))
    stems = names or sorted(os.path.splitext(f)[0] for f in os.listdir(map_dir) if f.endswith('.png'))
    tiles = []
    for stem in stems:
        im = _load_8bit(os.path.join(map_dir, stem + '.png'))
        if crop:
            im = im.crop(tuple(crop))
        scale = tile_size / max(im.size)
        tiles.append(im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale)))))
    gap = 6
    sheet = PILImage.new('RGB', (sum(t.width for t in tiles) + gap * (len(tiles) - 1),
                                 max(t.height for t in tiles)), 'white')
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0))
        x += t.width + gap
    buf = io.BytesIO()
    sheet.save(buf, format='PNG')
    return Image(data=buf.getvalue(), format='png')


if __name__ == '__main__':
    server.run()
