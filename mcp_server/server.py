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
def import_bitmap(path: str, graph: str | None = None, embed: str = 'link',
                  position: list[float] | None = None, name: str | None = None) -> str:
    """Add an image file (png, jpg, tga, exr, tif, psd...) to a graph as a Bitmap node and return
    its id (output connector `unique_filter_output`). For references, masks and hand-painted maps.
    embed: 'link' references the file where it is (an existing link to the same file is reused);
    'copy' copies it into `<package>.resources/` (into a temp folder until the package is saved).
    Embedding the image in the .sbs is not available through the API. The node keeps the image's
    own size; set its `$outputsize` with set_params to change it. name: resource identifier
    (default: the file name). position as in add_node. One undo step."""
    return _edit('import_bitmap(%r, %r, %r, %r, %r)' % (graph, path, embed, position, name),
                 'Claude: import bitmap')


@server.tool()
def open_graph(graph: str, node_id: str | None = None) -> str:
    """Open a graph in Designer's graph editor (so the user and screenshot_designer see it;
    closes Designer's Home screen if it is showing).
    Without node_id the whole graph is fitted in view; with node_id the view centres on that node."""
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


def _node_pixels(node_id, graph, output, tool):
    """A node's output computed in Designer: (pixels 0..1 as (H, W, C) floats, 'RGBA' or 'L', meta)."""
    tmp_dir = tempfile.mkdtemp(prefix='sd_px_')
    raw_path = os.path.join(tmp_dir, 'pixels.raw')
    try:
        text = _bridge(_with_undo(_helpers_call('dump_node_pixels(%r, %r, %r, %r)' % (
            node_id, raw_path, graph, output)), 'Claude: ' + tool.replace('_', ' ')), '<%s>' % tool, 300)
        found = re.search(r'PIXELS=(\{.*\})', text)
        if not found or not os.path.exists(raw_path):
            raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'no pixel data')
        meta = json.loads(found.group(1))
        with open(raw_path, 'rb') as f:
            data, layout = _decode_pixels(f.read(), meta)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return data, layout, meta


@server.tool()
def node_stats(node_id: str, graph: str | None = None, output: str | None = None,
               region: list[int] | None = None, points: list[list[int]] | None = None) -> str:
    """Exact pixel statistics of any node's output (computed in Designer, read from the raw
    buffer, so 16-bit/float precision is kept). Per channel: min, max, mean, std.
    region: [x0, y0, x1, y1] in pixels to restrict the stats. points: [[x, y], ...] pixel
    values to sample. Values are 0..1 for integer formats. Use it to verify results numerically."""
    data, layout, meta = _node_pixels(node_id, graph, output, 'node_stats')
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
    {"op": "bitmap", "path": "/abs/image.png", "ref": "img", "embed"?: "link", "position"?, "name"?}
    {"op": "set", "node": "lv", "params": {...}}            (node: a ref, a node id, or "graph")
    {"op": "connect", "from": "a", "to": "lv", "input": "input1", "output"?: "..."}
    {"op": "disconnect", "node": "lv", "input": "input1"}
    {"op": "move", "node": "lv", "position": [x, y]}
    {"op": "delete", "node": "lv"}
    {"op": "expose", "node": "lv", "param": "...", "input_id"?, "label"?, "default"?, "min"?, "max"?}
    Refs let later ops use nodes added earlier in the batch. Stops at the first failing op
    (earlier ops stay applied; Ctrl+Z on the graph reverts the whole batch)."""
    return _edit('apply_edits(%r, %r)' % (graph, ops), 'Claude: apply %d edits' % len(ops))


def _to_display(data, layout):
    """Decoded pixels (0..1 floats) -> 8-bit RGB PIL image for previews."""
    rgb = data[:, :, :3] if layout == 'RGBA' else np.repeat(data[:, :, :1], 3, axis=2)
    return PILImage.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')


def _labelled(im, label):
    """Image with a dark caption bar on top."""
    from PIL import ImageDraw
    tile = PILImage.new('RGB', (im.width, im.height + 18), (30, 30, 30))
    tile.paste(im, (0, 18))
    ImageDraw.Draw(tile).text((4, 3), label[:48], fill=(230, 230, 230))
    return tile


def _sheet(tiles, gap=6):
    """Tiles side by side on white -> MCP PNG image."""
    sheet = PILImage.new('RGB', (sum(t.width for t in tiles) + gap * (len(tiles) - 1),
                                 max(t.height for t in tiles)), 'white')
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0))
        x += t.width + gap
    buf = io.BytesIO()
    sheet.save(buf, format='PNG')
    return Image(data=buf.getvalue(), format='png')


def _channel_summary(data, layout):
    names = 'RGBA' if layout == 'RGBA' else 'L'
    return '  '.join('%s %.3f..%.3f (mean %.3f)' % (n, data[:, :, i].min(), data[:, :, i].max(),
                                                     data[:, :, i].mean()) for i, n in enumerate(names))


@server.tool()
def sweep_param(node_id: str, param: str, values: list, graph: str | None = None,
                view_node: str | None = None, output: str | None = None, tile_size: int = 256) -> list:
    """Try several values of one parameter and see them side by side: returns a labelled image
    strip plus per-value channel ranges, then restores the original value. node_id='graph' with
    param=<input id> sweeps an exposed graph input (then view_node is required). view_node: the
    node to look at (default: the swept node), e.g. the final output while sweeping an early
    node. Values use the same rules as set_params. Net effect on the graph: none."""
    tmp_dir = tempfile.mkdtemp(prefix='sd_sweep_')
    try:
        text = _bridge(_with_undo(_helpers_call('sweep_param(%r, %r, %r, %r, %r, %r, %r)' % (
            graph, node_id, param, values, tmp_dir, view_node, output)), 'Claude: sweep ' + param),
            '<sweep_param>', 600)
        metas = [json.loads(m) for m in re.findall(r'SWEEP=(\{.*\})', text)]
        if not metas:
            raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'sweep produced nothing')
        tiles, lines = [], ['%s.%s sweep (%s):' % (node_id, param, re.search(r'restored .*', text).group(0)
                                                     if 'restored' in text else 'original NOT restored!')]
        for meta in metas:
            with open(os.path.join(tmp_dir, '%d.raw' % meta['index']), 'rb') as f:
                data, layout = _decode_pixels(f.read(), meta)
            lines.append('%s = %r: %s' % (param, meta['value'], _channel_summary(data, layout)))
            im = _to_display(data, layout)
            im.thumbnail((tile_size, tile_size))
            tiles.append(_labelled(im, '%s = %s' % (param, meta['value'])))
        if 'restored' not in text:
            lines.append('WARNING: the original value may not have been restored:\n' + text[-1500:])
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return ['\n'.join(lines), _sheet(tiles)]


def _seam_report(data, axis_name, seam_axis):
    """Compare the wrap-around seam with typical neighbour steps along one axis."""
    a = np.moveaxis(data, seam_axis, 0)                 # axis 0 = direction across the seam
    steps = np.abs(np.diff(a, axis=0))                  # all interior neighbour differences
    seam = np.abs(a[0] - a[-1])                         # first vs last line (they meet when tiled)
    interior_mean = float(steps.mean())
    seam_mean = float(seam.mean())
    ratio = seam_mean / interior_mean if interior_mean > 1e-9 else (0.0 if seam_mean < 1e-9 else float('inf'))
    worst = float(seam.max())
    per_pos = seam.max(axis=-1)                         # worst channel per position along the seam
    worst_at = int(np.argmax(per_pos))
    verdict = ('tiles seamlessly' if ratio <= 1.5 else 'probably fine' if ratio <= 3
               else 'VISIBLE SEAM')
    where = 'row' if axis_name == 'horizontal' else 'column'
    return ('%s tiling (left/right edges): seam step %.4f vs typical %.4f (ratio %.2f), worst %.4f at %s %d: %s'
            if axis_name == 'horizontal' else
            '%s tiling (top/bottom edges): seam step %.4f vs typical %.4f (ratio %.2f), worst %.4f at %s %d: %s') % (
        axis_name.capitalize(), seam_mean, interior_mean, ratio, worst, where, worst_at, verdict)


@server.tool()
def check_tiling(node_id: str, graph: str | None = None, output: str | None = None,
                 axis: str = 'both') -> str:
    """Measure whether a node's output tiles: compares the jump across the wrap-around seam
    (left/right edges for 'horizontal', top/bottom for 'vertical') with the typical jump between
    neighbouring pixels. Ratio ~1 = seamless; above ~3 a seam is likely visible. axis:
    'horizontal', 'vertical' or 'both' (trim sheets usually only need horizontal)."""
    if axis not in ('horizontal', 'vertical', 'both'):
        raise ToolError("axis must be 'horizontal', 'vertical' or 'both'")
    data, _, meta = _node_pixels(node_id, graph, output, 'check_tiling')
    lines = ['%s: %dx%d %s' % (meta['node'], meta['width'], meta['height'], meta['format'])]
    if axis in ('horizontal', 'both'):
        lines.append(_seam_report(data, 'horizontal', 1))
    if axis in ('vertical', 'both'):
        lines.append(_seam_report(data, 'vertical', 0))
    return '\n'.join(lines)


_LUMA = np.array([0.2126, 0.7152, 0.0722])


def _load_reference(path, region=None):
    """Image file -> (pixels 0..1 as (H, W, C) floats, 'RGBA' or 'L'). PIL reads 16-bit RGBA PNGs
    as 8-bit; 16-bit grayscale and float (mode F) keep their precision."""
    path = os.path.abspath(os.path.expanduser(path))
    try:
        im = PILImage.open(path)
        im.load()
    except (OSError, ValueError) as e:
        raise ToolError('cannot read %s: %s' % (path, e))
    if im.mode in ('I', 'I;16', 'I;16B', 'I;16L', 'F'):
        a = np.array(im).astype(np.float64)
        if im.mode != 'F':
            a /= 65535.0 if im.mode.startswith('I;16') or a.max() > 255 else 255.0
        data, layout = a[:, :, None], 'L'
    elif im.mode in ('1', 'L', 'LA'):
        data, layout = np.array(im.convert('L')).astype(np.float64)[:, :, None] / 255.0, 'L'
    else:
        data, layout = np.array(im.convert('RGBA')).astype(np.float64) / 255.0, 'RGBA'
    if region:
        x0, y0, x1, y1 = region
        data = data[max(0, y0):y1, max(0, x0):x1]
        if not data.size:
            raise ToolError('reference_region %s is empty for the %dx%d image' % (region, im.width, im.height))
    return data, layout


def _compare_channels(a, a_layout, b, b_layout):
    """Shared channels to compare: R, G, B and luma when both are colour, else luma only."""
    def luma(d, layout):
        return d[:, :, :3] @ _LUMA if layout == 'RGBA' else d[:, :, 0]
    chans = [('luma', luma(a, a_layout), luma(b, b_layout))]
    if a_layout == b_layout == 'RGBA':
        chans = [(n, a[:, :, i], b[:, :, i]) for i, n in enumerate('RGB')] + chans
    return chans


def _emd(x, y):
    """Earth mover's distance between two value distributions: how far values must move on
    average (0..1 units) to turn one histogram into the other."""
    q = np.linspace(0, 1, 257)
    return float(np.abs(np.quantile(x, q) - np.quantile(y, q)).mean())


def _resize(data, size):
    """Float image (H, W, C) -> size (w, h), channel by channel (box when shrinking)."""
    shrink = size[0] < data.shape[1]
    method = PILImage.Resampling.BOX if shrink else PILImage.Resampling.BILINEAR
    return np.dstack([np.array(PILImage.fromarray(data[:, :, c].astype(np.float32), 'F').resize(size, method))
                      for c in range(data.shape[2])]).astype(np.float64)


def _compare_report(node, node_layout, ref, ref_layout, aligned=False):
    """Compare a node's pixels with a reference: value distributions always, pixel by pixel when
    aligned. Returns (text lines, absolute luma difference image or None)."""
    lines = []
    mask_n = mask_r = None
    if ref_layout == 'RGBA' and (ref[:, :, 3] < 0.5).any():
        mask_r = ref[:, :, 3] >= 0.5
        if not mask_r.any():
            raise ToolError('the reference is fully transparent')
        lines.append('ignoring %.1f%% transparent reference pixels' % (100 - 100 * mask_r.mean()))
    diff = None
    if aligned:
        h, w = node.shape[:2]
        if abs(ref.shape[1] / ref.shape[0] - w / h) > 0.01 * w / h:
            lines.append('WARNING: aspect ratios differ (%dx%d vs %dx%d); the reference is stretched' % (
                w, h, ref.shape[1], ref.shape[0]))
        if ref.shape[:2] != (h, w):
            ref = _resize(ref, (w, h))
            if mask_r is not None:
                mask_r = ref[:, :, 3] >= 0.5
        mask_n = mask_r
    chans = _compare_channels(node, node_layout, ref, ref_layout)
    lines.append('%-5s %-36s %-36s %s' % ('', 'node: mean std (p5 p50 p95)', 'reference: mean std (p5 p50 p95)',
                                          'difference'))
    fixes = []
    for name, a, b in chans:
        a = a[mask_n] if mask_n is not None else a.ravel()
        b = b[mask_r] if mask_r is not None else b.ravel()
        pa, pb = np.percentile(a, [5, 50, 95]), np.percentile(b, [5, 50, 95])
        sa, sb = float(a.std()), float(b.std())
        lines.append('%-5s %.3f %.3f (%.3f %.3f %.3f)%s %.3f %.3f (%.3f %.3f %.3f)%s mean %+.3f  contrast x%.2f  EMD %.3f' % (
            name, a.mean(), sa, *pa, ' ' * 7, b.mean(), sb, *pb, ' ' * 7, b.mean() - a.mean(),
            sb / sa if sa > 1e-9 else float('inf'), _emd(a, b)))
        if sa > 1e-9:
            gain = sb / sa
            fixes.append('%s: x*%.3f %+.3f' % (name, gain, b.mean() - a.mean() * gain))
    emd = _emd(chans[-1][1][mask_n] if mask_n is not None else chans[-1][1].ravel(),
               chans[-1][2][mask_r] if mask_r is not None else chans[-1][2].ravel())
    lines.append('luma distributions: %s (EMD %.3f; rough guide: < 0.02 close, < 0.05 similar)' % (
        'close' if emd < 0.02 else 'similar' if emd < 0.05 else 'different', emd))
    if fixes:
        lines.append('to match mean and contrast (levels/linear map): ' + ', '.join(fixes))
    if aligned:
        lines.append('pixel by pixel (reference resized to %dx%d):' % (node.shape[1], node.shape[0]))
        for name, a, b in chans:
            d = np.abs(a - b)
            if mask_n is not None:
                d = d[mask_n]
            lines.append('  %-5s mean abs diff %.4f  RMSE %.4f  max %.4f' % (
                name, d.mean(), np.sqrt((d ** 2).mean()), d.max()))
        diff = np.abs(chans[-1][1] - chans[-1][2])
        if mask_n is not None:
            diff = np.where(mask_n, diff, 0.0)
    return lines, diff


def _histogram_tile(node_luma, ref_luma, width, height, bins=64):
    """Luma histograms: node as filled bars, reference as an orange line."""
    from PIL import ImageDraw
    hn = np.histogram(node_luma, bins=bins, range=(0, 1))[0].astype(float)
    hr = np.histogram(ref_luma, bins=bins, range=(0, 1))[0].astype(float)
    hn, hr = hn / max(hn.sum(), 1), hr / max(hr.sum(), 1)
    top = max(hn.max(), hr.max(), 1e-9)
    im = PILImage.new('RGB', (width, height), (24, 24, 24))
    d = ImageDraw.Draw(im)
    bw = width / bins
    y = lambda v: height - 1 - v / top * (height - 20)
    for i, v in enumerate(hn):
        d.rectangle([i * bw, y(v), (i + 1) * bw - 1, height - 1], fill=(90, 150, 220))
    d.line([((i + 0.5) * bw, y(v)) for i, v in enumerate(hr)], fill=(255, 150, 40), width=2)
    d.text((4, 3), 'node', fill=(90, 150, 220))
    d.text((40, 3), 'reference', fill=(255, 150, 40))
    return im


@server.tool()
def compare_to_reference(node_id: str, reference_path: str, graph: str | None = None,
                         output: str | None = None, region: list[int] | None = None,
                         reference_region: list[int] | None = None, aligned: bool = False,
                         tile_size: int = 256) -> list:
    """Compare a node's output with a reference image file, with numbers. Always compares value
    distributions (works for a photo that isn't pixel-aligned with the material): per channel
    mean, std, percentiles, the mean shift, the contrast ratio and the earth mover's distance
    (EMD: how far values must move on average, 0..1), plus a linear map (x*gain + bias) that
    would match mean and contrast. R, G, B are compared when both are colour, luma always.
    aligned=True also compares pixel by pixel (reference resized to the node; for references made
    for the same layout, e.g. an earlier render) and adds a difference image.
    region / reference_region: [x0, y0, x1, y1] in pixels to compare parts, e.g. one trim strip
    with the matching area of a photo. Transparent reference pixels (alpha < 0.5) are ignored.
    Returns the numbers and an image: node | reference | luma histograms | difference."""
    data, layout, meta = _node_pixels(node_id, graph, output, 'compare_to_reference')
    if region:
        x0, y0, x1, y1 = region
        data = data[max(0, y0):y1, max(0, x0):x1]
        if not data.size:
            raise ToolError('region %s is empty for the %dx%d node' % (region, meta['width'], meta['height']))
    ref, ref_layout = _load_reference(reference_path, reference_region)
    lines, diff = _compare_report(data, layout, ref, ref_layout, aligned)
    lines.insert(0, '%s (%dx%d %s) vs %s (%dx%d)' % (meta['node'], data.shape[1], data.shape[0], meta['format'],
                                                    os.path.basename(reference_path), ref.shape[1], ref.shape[0]))
    tiles = []
    for im, label in ((_to_display(data, layout), 'node'), (_to_display(ref, ref_layout), 'reference')):
        im.thumbnail((tile_size, tile_size))
        tiles.append(_labelled(im, label))
    chans = _compare_channels(data, layout, ref, ref_layout)
    ref_luma = chans[-1][2] if ref_layout != 'RGBA' or (ref[:, :, 3] >= 0.5).all() else chans[-1][2][ref[:, :, 3] >= 0.5]
    tiles.append(_labelled(_histogram_tile(chans[-1][1].ravel(), ref_luma.ravel(), tile_size,
                                           max(max(t.height for t in tiles) - 18, 96)), 'luma histograms'))
    if diff is not None:
        peak = max(float(diff.max()), 1e-9)
        im = _to_display((diff / peak)[:, :, None], 'L')
        im.thumbnail((tile_size, tile_size))
        tiles.append(_labelled(im, 'difference (white = %.3f)' % peak))
    return ['\n'.join(lines), _sheet(tiles)]


def _designer_log_path():
    if os.environ.get('SD_DESIGNER_LOG'):
        return os.environ['SD_DESIGNER_LOG']
    if sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support/Adobe/Adobe Substance 3D Designer')
    elif sys.platform == 'win32':
        base = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Adobe', 'Adobe Substance 3D Designer')
    else:
        base = os.path.expanduser('~/.local/share/Adobe/Adobe Substance 3D Designer')
    logs = []
    for root, _dirs, files in os.walk(base):
        if 'log.txt' in files:
            logs.append(os.path.join(root, 'log.txt'))
    return max(logs, key=os.path.getmtime) if logs else None


@server.tool()
def read_designer_log(lines: int = 60, contains: str | None = None, errors_only: bool = False,
                      since_last_start: bool = True) -> str:
    """Read the end of Designer's log, where every plugin/Python traceback lands. contains:
    case-insensitive text to filter on (e.g. 'sd_bridge', 'Traceback'). errors_only: only
    [ERROR]/[WARNING] lines. since_last_start: ignore lines from before Designer's last start.
    Override the location with SD_DESIGNER_LOG."""
    path = _designer_log_path()
    if not path or not os.path.exists(path):
        raise ToolError('Designer log not found; set SD_DESIGNER_LOG to its path')
    with open(path, encoding='utf-8', errors='replace') as f:
        content = f.read().splitlines()
    if since_last_start:
        content = content[_last_start(content):]
    if errors_only:
        content = [l for l in content if '[ERROR]' in l or '[WARNING]' in l]
    if contains:
        needle = contains.lower()
        content = [l for l in content if needle in l.lower()]
    tail = content[-lines:] if lines > 0 else content
    header = '%s (%d matching line%s, showing %d)' % (path, len(content), '' if len(content) == 1 else 's', len(tail))
    return header + '\n' + '\n'.join(tail)


def _last_start(lines):
    """Index of the most recent Designer start-up: Designer logs "Python SDK Version" exactly
    once per start, just before plugins load. 0 if not found."""
    for i in range(len(lines) - 1, -1, -1):
        if 'Python SDK Version' in lines[i]:
            return i
    return 0


SNAPSHOT_DIR = os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), '.sd_mcp', 'snapshots')


def _safe_name(text):
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', text).strip('_') or 'snapshot'


def _copy_package(graph, path):
    text = _bridge(_helpers_call('save_package_copy(%r, %r)' % (graph, path)), timeout=120)
    found = dict(re.findall(r'^(COPY|PACKAGE|GRAPH)=(.*)$', text, re.M))
    if 'COPY' not in found or not os.path.exists(path):
        raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'could not copy package')
    return found


@server.tool()
def snapshot_graph(graph: str | None = None, label: str | None = None) -> str:
    """Save a snapshot of a graph's package (a full .sbs copy) before risky work. It doesn't
    change the open package, its file or its saved state. Compare later with diff_graph; the
    snapshot .sbs can also be opened in Designer to recover anything. Snapshots live in
    ~/.sd_mcp/snapshots/<graph>/ (override with SD_SNAPSHOT_DIR)."""
    stamp = time.strftime('%Y%m%d-%H%M%S')
    tmp = os.path.join(tempfile.mkdtemp(prefix='sd_snap_'), 'copy.sbs')
    try:
        info = _copy_package(graph, tmp)
        folder = os.path.join(SNAPSHOT_DIR, _safe_name(info['GRAPH']))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, stamp + ('-' + _safe_name(label) if label else '') + '.sbs')
        shutil.move(tmp, path)
    finally:
        shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)
    return 'snapshot of %s saved: %s' % (info['GRAPH'], path)


def _snapshots(graph_id):
    folder = os.path.join(SNAPSHOT_DIR, _safe_name(graph_id))
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.sbs'))


@server.tool()
def list_snapshots(graph: str | None = None) -> str:
    """List saved snapshots (newest last). graph: graph identifier (default: all graphs)."""
    graphs = [_safe_name(graph)] if graph else (sorted(os.listdir(SNAPSHOT_DIR)) if os.path.isdir(SNAPSHOT_DIR) else [])
    lines = []
    for gid in graphs:
        for path in _snapshots(gid):
            lines.append('%s  %s' % (gid, path))
    return '\n'.join(lines) if lines else 'No snapshots%s.' % (' for ' + graph if graph else '')


def _graph_model(sbs_path, graph_id):
    """Parse one graph of a .sbs into comparable dicts."""
    root = ET.parse(sbs_path).getroot()
    g = next((x for x in root.iter('graph') if x.find('identifier') is not None
              and x.find('identifier').get('v') == graph_id), None)
    if g is None:
        raise ToolError('graph %r not found in %s' % (graph_id, sbs_path))
    def value_of(param):
        pv = param.find('paramValue')
        if pv is None or not len(pv):
            return ''
        el = pv[0]
        return 'function' if el.tag == 'dynamicValue' else (el.get('v') or '')
    nodes = {}
    for n in g.find('compNodes') if g.find('compNodes') is not None else []:
        uid = n.find('uid').get('v')
        impl = n.find('compImplementation')
        kind = '?'
        if impl is not None and len(impl):
            el = impl[0]
            if el.tag == 'compFilter':
                kind = el.find('filter').get('v')
            elif el.tag == 'compInstance':
                path = el.find('path').get('v') if el.find('path') is not None else ''
                kind = 'instance:' + re.sub(r'^pkg:///|\?.*$', '', path)
            elif el.tag == 'compOutputBridge':
                kind = 'output'
            elif el.tag == 'compInputBridge':
                kind = 'input'
        # atomic and library (instance) nodes store parameters the same way
        params = {prm.find('name').get('v'): value_of(prm)
                  for prm in (impl.iter('parameter') if impl is not None else [])}
        links, display = set(), {}
        conns = n.find('connections')
        for c in (conns if conns is not None else []):
            key = (c.find('identifier').get('v'), c.find('connRef').get('v'))
            links.add(key)
            dt = c.find('displayType')
            display[key] = 'portal' if dt is not None and dt.get('v') == '1' else 'wire'
        pos = n.find('GUILayout/gpos')
        nodes[uid] = {'kind': kind, 'params': params, 'links': links, 'display': display,
                      'pos': pos.get('v') if pos is not None else ''}
    inputs = {}
    for pi in g.iter('paraminput'):
        dv = pi.find('defaultValue')
        inputs[pi.find('identifier').get('v')] = dv[0].get('v') if dv is not None and len(dv) else ''
    size = {}
    for prm in (g.find('baseParameters') if g.find('baseParameters') is not None else []):
        rel = prm.find('relativeTo')
        size[prm.find('name').get('v')] = '%s (%s)' % (value_of(prm), {'0': 'relative to input', '1': 'relative to parent',
                                                                         '2': 'absolute'}.get(rel.get('v') if rel is not None else '', 'absolute'))
    for opt in g.iter('option'):
        if opt.find('name') is not None and opt.find('name').get('v') == 'defaultParentSize':
            size['defaultParentSize'] = opt.find('value').get('v')
    return {'nodes': nodes, 'inputs': inputs, 'size': size}


def _diff_models(old, new, show_positions):
    out = []
    on, nn = old['nodes'], new['nodes']
    added = [i for i in nn if i not in on]
    removed = [i for i in on if i not in nn]
    for i in added:
        out.append('+ node %s %s' % (i, nn[i]['kind']))
    for i in removed:
        out.append('- node %s %s' % (i, on[i]['kind']))
    moved = 0
    for i in (i for i in nn if i in on):
        a, b = on[i], nn[i]
        for name in sorted(set(a['params']) | set(b['params'])):
            va, vb = a['params'].get(name, '(default)'), b['params'].get(name, '(default)')
            if va != vb:
                out.append('~ node %s %s: %s %s -> %s' % (i, b['kind'], name, va, vb))
        for port, src in sorted(b['links'] - a['links']):
            out.append('~ node %s %s: link %s <- %s added' % (i, b['kind'], port, src))
        for port, src in sorted(a['links'] - b['links']):
            out.append('~ node %s %s: link %s <- %s removed' % (i, b['kind'], port, src))
        for key in sorted(a['links'] & b['links']):
            if a['display'].get(key) != b['display'].get(key):
                out.append('~ node %s %s: link %s <- %s shown as %s (was %s)' % (
                    i, b['kind'], key[0], key[1], b['display'].get(key), a['display'].get(key)))
        if a['pos'] != b['pos']:
            moved += 1
            if show_positions:
                out.append('~ node %s %s: moved %s -> %s' % (i, b['kind'], a['pos'], b['pos']))
    for name in sorted(set(old['inputs']) | set(new['inputs'])):
        va, vb = old['inputs'].get(name), new['inputs'].get(name)
        if va is None:
            out.append('+ graph input %s = %s' % (name, vb))
        elif vb is None:
            out.append('- graph input %s' % name)
        elif va != vb:
            out.append('~ graph input %s: %s -> %s' % (name, va, vb))
    for name in sorted(set(old['size']) | set(new['size'])):
        if old['size'].get(name) != new['size'].get(name):
            out.append('~ graph %s: %s -> %s' % (name, old['size'].get(name), new['size'].get(name)))
    summary = '%d added, %d removed, %d changed line(s), %d node(s) moved' % (
        len(added), len(removed), len([l for l in out if l.startswith('~') and ': moved ' not in l]), moved)
    return summary, out


@server.tool()
def diff_graph(graph: str | None = None, against: str = 'saved', show_positions: bool = False) -> str:
    """Show what changed in a graph: nodes added/removed, parameter changes, links
    added/removed, exposed inputs and size. against: 'saved' (the package's file on disk),
    'latest' (newest snapshot), a snapshot label, or a .sbs path. The live graph is read
    without modifying it. Positions are only counted unless show_positions=True."""
    tmp_dir = tempfile.mkdtemp(prefix='sd_diff_')
    try:
        info = _copy_package(graph, os.path.join(tmp_dir, 'live.sbs'))
        gid = info['GRAPH']
        if against == 'saved':
            ref = info.get('PACKAGE')
            if not ref or not os.path.exists(ref):
                raise ToolError('the package has never been saved; diff against a snapshot instead')
        elif against == 'latest':
            snaps = _snapshots(gid)
            if not snaps:
                raise ToolError('no snapshots for %s; take one with snapshot_graph' % gid)
            ref = snaps[-1]
        elif against.endswith('.sbs'):
            ref = os.path.abspath(os.path.expanduser(against))
        else:
            matches = [p for p in _snapshots(gid) if _safe_name(against) in os.path.basename(p)]
            if not matches:
                raise ToolError('no snapshot matching %r; see list_snapshots' % against)
            ref = matches[-1]
        summary, lines = _diff_models(_graph_model(ref, gid), _graph_model(os.path.join(tmp_dir, 'live.sbs'), gid),
                                      show_positions)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    head = '%s (live) vs %s: %s' % (gid, ref, summary)
    if lines:
        return head + '\n' + '\n'.join(lines)
    moved_only = not summary.endswith(' 0 node(s) moved')
    return head + ('\nOnly node positions differ (show_positions=True lists them).' if moved_only else '\nNo differences.')


@server.tool()
def arrange_graph(graph: str | None = None, node_ids: list[str] | None = None,
                  spacing: list[float] | None = None) -> str:
    """Tidy a graph: left-to-right columns by data flow, ordered to reduce crossing links,
    outputs in the last column. Only positions change (connections are never touched).
    node_ids: arrange just these nodes, from their current top-left. spacing: [dx, dy]
    (default [200, 150]). One undo step."""
    return _edit('arrange_graph(%r, %r, %r)' % (graph, node_ids, tuple(spacing or (200.0, 150.0))),
                 'Claude: arrange graph')


@server.tool()
def add_frame(node_ids: list[str], title: str, graph: str | None = None, color: list[float] | None = None,
              description: str | None = None) -> str:
    """Draw a titled frame around nodes (e.g. one per section of a material). color: [r, g, b(, a)]
    0..1. description: text shown in the frame. One undo step."""
    return _edit('add_frame(%r, %r, %r, %r, %r)' % (graph, node_ids, title, color, description),
                 'Claude: add frame ' + title)


@server.tool()
def add_comment(text: str, graph: str | None = None, node_id: str | None = None,
                position: list[float] | None = None) -> str:
    """Add a comment to a graph: attached to node_id, or free-standing at position [x, y].
    One undo step."""
    return _edit('add_comment(%r, %r, %r, %r)' % (graph, text, node_id, position), 'Claude: add comment')


_DISPLAY = {'portal': '1', 'wire': None}


@server.tool()
def set_link_display(graph: str | None = None, mode: str = 'portal', from_nodes: list[str] | None = None,
                     fanout_at_least: int | None = None, longer_than: float | None = None,
                     links: list[list[str]] | None = None) -> str:
    """Show connections as portals (hidden wires with a symbol at each end) or as normal wires, to
    reduce wire clutter. Pick links by any of: from_nodes (all outgoing links of these nodes),
    fanout_at_least (all links from outputs that feed at least N inputs), longer_than (links
    longer than this distance in graph units; nodes are ~96 wide), links ([[to_node, input], ...]).
    mode: 'portal' or 'wire'. Designer's API can't do this, so the tool takes a snapshot, saves the
    package, edits the .sbs and reloads it (the package's undo history is reset; the graph is
    reopened). The package must have been saved to a file once."""
    if mode not in _DISPLAY:
        raise ToolError("mode must be 'portal' or 'wire'")
    if not (from_nodes or fanout_at_least or longer_than or links):
        raise ToolError('choose links with from_nodes, fanout_at_least, longer_than or links')
    text = _bridge(_helpers_call('package_file_of(%r)' % graph), timeout=120)
    info = dict(re.findall(r'^(FILE|GRAPH|OPEN)=(.*)$', text, re.M))
    if 'FILE' not in info:
        raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'could not save the package')
    path, gid = info['FILE'], info['GRAPH']
    snap = snapshot_graph(gid, 'before ' + mode + 's')
    tree = ET.parse(path)
    g = next(x for x in tree.getroot().iter('graph') if x.find('identifier') is not None
             and x.find('identifier').get('v') == gid)
    nodes = {n.find('uid').get('v'): n for n in g.find('compNodes')}
    def pos(uid):
        gp = nodes[uid].find('GUILayout/gpos') if uid in nodes else None
        return [float(v) for v in gp.get('v').split()[:2]] if gp is not None else None
    conns = []                                   # (downstream uid, connection element, source uid, source output)
    for uid, n in nodes.items():
        for c in n.iter('connection'):
            out = c.find('connRefOutput')
            conns.append((uid, c, c.find('connRef').get('v'), out.get('v') if out is not None else ''))
    fanout = {}
    for _, _, src, out in conns:
        fanout[(src, out)] = fanout.get((src, out), 0) + 1
    wanted_links = {(str(a), str(b)) for a, b in (links or [])}
    chosen = []
    for down, c, src, out in conns:
        port = c.find('identifier').get('v')
        pick = (from_nodes and src in {str(x) for x in from_nodes}) \
            or (fanout_at_least and fanout[(src, out)] >= fanout_at_least) \
            or ((down, port) in wanted_links)
        if not pick and longer_than:
            a, b = pos(src), pos(down)
            pick = a is not None and b is not None and ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 > longer_than
        if pick:
            chosen.append((down, c, src, port))
    changed = 0
    for down, c, src, port in chosen:
        dt = c.find('displayType')
        if _DISPLAY[mode] is None:
            if dt is not None:
                c.remove(dt)
                changed += 1
        else:
            if dt is None:
                dt = ET.SubElement(c, 'displayType')
            if dt.get('v') != _DISPLAY[mode]:
                dt.set('v', _DISPLAY[mode])
                changed += 1
    if changed:
        tree.write(path, encoding='UTF-8', xml_declaration=True)
    _checked(_bridge(_helpers_call('reload_package(%r, %r)' % (path, None)), timeout=180))
    if info.get('OPEN') == '1':
        open_graph(gid)   # reopen in a separate call so the editor has settled after the reload
    return ('%d of %d selected link(s) changed to %s in %s (of %d links in the graph); package saved and '
            'reloaded. %s' % (changed, len(chosen), mode, gid, len(conns), snap))


DESIGNER_APP = {
    'darwin': '/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app',
    'win32': r'C:\Program Files\Adobe\Adobe Substance 3D Designer\Adobe Substance 3D Designer.exe',
}


@server.tool()
def launch_designer(wait_s: int = 180) -> str:
    """Start Substance Designer if it isn't running and wait until the sd_bridge plugin answers.
    When it starts Designer it also closes the Home screen, so the editor panels are visible.
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
        except ToolError:
            continue
        # we started it, so nobody is using the Home screen: show the editor panels
        home = _bridge(_helpers_call('leave_home_screen()'), timeout=30).strip()
        return 'Designer started in %.0fs%s: %s' % (time.time() - started, ' (%s)' % home if home else '', status)
    raise ToolError('Designer did not answer within %ds. It may be showing a dialog, or the '
                    'sd_bridge plugin did not load (check the Designer log).' % wait_s)


def _designer_running():
    """True while a Designer process exists (the bridge port closes before the process exits)."""
    if sys.platform == 'win32':
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Adobe Substance 3D Designer.exe', '/NH'],
                             capture_output=True, text=True).stdout
        return 'Adobe Substance 3D Designer.exe' in out
    return subprocess.run(['pgrep', '-f', 'MacOS/Adobe Substance 3D Designer( |$)'],
                          capture_output=True).returncode == 0


@server.tool()
def quit_designer(discard_unsaved: bool = False, wait_s: int = 60) -> str:
    """Close Substance Designer and wait until its process has exited (for example to restart it
    after a plugin change, with launch_designer). Refuses while any open package has unsaved
    changes and lists them; save them first, or pass discard_unsaved=True to drop those changes
    (only when the user said so)."""
    try:
        _send({'cmd': 'status'}, wait=5)
    except ToolError:
        if not _designer_running():
            return 'Designer is not running.'
        raise ToolError('A Designer process is running but the bridge does not answer; '
                        'close Designer by hand.')
    text = _checked(_bridge(_helpers_call('quit_designer(%r)' % discard_unsaved), timeout=30))
    started = time.time()
    while time.time() - started < wait_s:
        time.sleep(1)
        if not _designer_running():
            notes = text.replace('closing Designer', '').strip()
            return (notes + '\n' if notes else '') + 'Designer quit after %.0fs.' % (time.time() - started)
    raise ToolError('Designer is still running after %ds; it may be showing a dialog.' % wait_s)


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
    size_log2: output size override (11 = 2048). Without it a .sbs renders at the graph's default
    parent size (as in Designer) and a .sbsar at its own stored default (often 256 px). graph: graph identifier inside the package
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
        elif sbs_path.endswith('.sbsar'):
            cooked = _sbsar_default_log2(sbsar, graph)
            notes.append('size: the .sbsar\'s own default%s; the cooker doesn\'t keep the graph\'s default '
                         'parent size, so pass size_log2 (or render the .sbs) for another size'
                         % (', %d px' % 2 ** cooked if cooked else ''))
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


def _sbsar_default_log2(sbsar, graph=None):
    """Default $outputsize (log2) stored in a .sbsar, or None. A .sbsar is a 7-zip archive whose
    .xml description lists each input's default; the system tar (bsdtar on macOS and Windows 10+)
    can read it."""
    tar = shutil.which('tar')
    if not tar:
        return None
    listing = subprocess.run([tar, '-tf', sbsar], capture_output=True, text=True)
    wanted = graph.split('://')[-1] if graph else None
    for member in [m for m in listing.stdout.splitlines() if m.endswith('.xml')] if listing.returncode == 0 else []:
        xml = subprocess.run([tar, '-xOf', sbsar, member], capture_output=True).stdout
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            continue
        for g in root.iter('graph'):
            if wanted and g.get('pkgurl', '').split('://')[-1] != wanted:
                continue
            for inp in g.iter('input'):
                if inp.get('identifier') == '$outputsize':
                    width = inp.get('default', '').split(',')[0]
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
    return _sheet(tiles)


if __name__ == '__main__':
    server.run()
