"""Output: save_package, export_outputs, render_sbs, sbsar_info, preview_maps (sbscooker,
sbsrender)."""

import contextlib
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from typing import cast

import numpy as np
from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image as PILImage

from .core import SBSCOOKER, SBSRENDER, _bridge, _checked, _helpers_call, _local_path, _tool
from .measure import _crop_box, _sheet
from .snapshots import _v

# a value for an exposed input (render_sbs params)
_Value = float | int | bool | list[float]


@_tool()
def save_package(graph_or_path: str | None = None, save_as: str | None = None) -> str:
    """Save an open package from Designer. graph_or_path: a graph identifier or the package's
    file path (default: graph open in the UI). save_as: new absolute .sbs path (required for
    packages that were never saved)."""
    if graph_or_path and graph_or_path.lower().endswith('.sbs'):
        graph_or_path = _local_path(graph_or_path)
    return _checked(_bridge(_helpers_call('save_package(%r, %r)' % (graph_or_path, _local_path(save_as))), timeout=120))


@_tool()
def export_outputs(graph: str, output_dir: str, outputs: list[str] | None = None, file_format: str = 'png') -> str:
    """Compute a graph inside Designer and save its output nodes' textures directly (no
    sbscooker/sbsrender), named after the output identifiers. Reflects the current, possibly
    unsaved, state of the graph. outputs: subset of output identifiers (default: all); names that
    match no output are listed. Two outputs with one identifier are refused (one file each)."""
    return _checked(
        _bridge(
            _helpers_call('export_outputs(%r, %r, %r, %r)' % (graph, _local_path(output_dir), outputs, file_format)),
            timeout=600,
        )
    )


def _value_arg(value: _Value) -> str:
    if isinstance(value, (list, tuple)):
        return ','.join(str(v) for v in value)
    if isinstance(value, bool):
        return '1' if value else '0'
    return str(value)


@_tool()
def render_sbs(
    sbs_path: str,
    output_dir: str,
    size_log2: int | None = None,
    graph: str | None = None,
    outputs: list[str] | None = None,
    params: dict[str, float | int | bool | list[float]] | None = None,
    output_format: str = 'png',
) -> str:
    """Cook a .sbs in a temporary folder (or take a .sbsar) and render outputs to files named after
    the output nodes (graph_output when several graphs render, so same-named outputs don't collide).
    size_log2: output size override (11 = 2048). Without it a .sbs renders at the graph's default
    parent size (as in Designer) and a .sbsar at its own stored default (often 256 px). graph: graph identifier inside the package
    (default: every graph). outputs: output identifiers to render (default: all).
    params: exposed input values, e.g. {"wear": 0.5, "tint": [1, 0.8, 0.6]}.
    output_format: png, tga, exr, jpg, ... Use sbsar_info to list graphs/inputs/outputs."""
    if not (SBSCOOKER and SBSRENDER):
        raise ToolError(
            'sbscooker/sbsrender not found. Set SD_DESIGNER_BIN_DIR to the folder containing '
            'them (the Designer install folder on Windows, .app/Contents/MacOS on macOS).'
        )
    with _cooked(sbs_path) as sbsar:
        return _render_sbsar(sbsar, sbs_path, output_dir, size_log2, graph, outputs, params, output_format)


def _render_sbsar(
    sbsar: str,
    sbs_path: str,
    output_dir: str,
    size_log2: int | None,
    graph: str | None,
    outputs: list[str] | None,
    params: dict[str, _Value] | None,
    output_format: str,
) -> str:
    output_dir = os.path.abspath(os.path.expanduser(output_dir))
    os.makedirs(output_dir, exist_ok=True)
    exposed, graphs = _sbsar_contents(sbsar)
    # files are named after the outputs; with several graphs rendered, after the graph too, or two
    # graphs' outputs of the same name would write one file (REVIEW.md SRV-26)
    name = '{inputGraphUrl}_{outputNodeName}' if not graph and len(graphs) > 1 else '{outputNodeName}'
    cmd = [
        cast(str, SBSRENDER),  # render_sbs checked SBSRENDER
        'render',
        sbsar,
        '--output-path',
        output_dir,
        '--output-name',
        name,
        '--output-format',
        output_format,
    ]
    if output_format == 'png':
        cmd += ['--png-format-compression', 'best_speed']
    if graph:
        cmd += ['--input-graph', graph if '://' in graph else 'pkg://' + graph]
    for name in outputs or []:
        cmd += ['--input-graph-output', name]
    values = dict(params or {})
    # sbsrender silently ignores values for inputs the graph doesn't expose, so warn up front
    notes: list[str] = []
    if size_log2:
        values['$outputsize'] = [size_log2, size_log2]
    elif '$outputsize' in exposed and '$outputsize' not in values:
        # An overridable graph renders at sbsrender's own 256 px default unless told otherwise;
        # use the graph's default parent size from the .sbs so the result matches Designer
        default = _default_parent_log2(sbs_path, graph)
        if default:
            values['$outputsize'] = [default, default]
            notes.append("size: using the graph's default parent size, %d px (from the .sbs)" % 2**default)
        elif sbs_path.endswith('.sbs') and not graph and len(set(_default_parent_sizes(sbs_path).values())) > 1:
            notes.append(
                'size: the graphs in this package have different default sizes, so each renders at '
                "sbsrender's 256 px default; pass graph or size_log2"
            )
        elif sbs_path.endswith('.sbsar'):
            cooked = _sbsar_default_log2(sbsar, graph)
            notes.append(
                "size: the .sbsar's own default%s; the cooker doesn't keep the graph's default "
                'parent size, so pass size_log2 (or render the .sbs) for another size'
                % (', %d px' % 2**cooked if cooked else '')
            )
    warnings = [
        'WARNING: input %r is not exposed by this .sbsar, so the value is ignored%s'
        % (
            key,
            ' (graph output size is fixed; expose $outputsize or make it relative to parent to allow size overrides)'
            if key == '$outputsize'
            else '',
        )
        for key in values
        if key not in exposed
    ]
    for key, value in values.items():
        cmd += ['--set-value', '%s@%s' % (key, _value_arg(value))]
    before = _snapshot(output_dir)
    render = _run_tool(cmd, 900)
    if render.returncode != 0:
        raise ToolError('sbsrender failed:\n' + render.stdout[-3000:] + render.stderr[-3000:])
    after = _snapshot(output_dir)
    files = sorted(f for f, stamp in after.items() if before.get(f) != stamp)
    if not files:
        raise ToolError(
            'sbsrender produced no files (check graph/output names with sbsar_info).\n' + render.stdout[-2000:]
        )
    lines = ['%s  %s' % (f, _image_size(os.path.join(output_dir, f))) for f in files]
    return '\n'.join(warnings + notes + ['Rendered %d file(s) to %s:' % (len(files), output_dir)] + lines)


def _default_parent_sizes(sbs_path: str) -> dict[str | None, int]:
    """{graph id: defaultParentSize as log2} from a .sbs ("9x9" = 512 px); {} if unreadable."""
    path = os.path.abspath(os.path.expanduser(sbs_path))
    if not path.endswith('.sbs') or not os.path.exists(path):
        return {}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return {}
    sizes: dict[str | None, int] = {}
    for g in root.iter('graph'):
        ident = g.find('identifier')
        for option in g.iter('option'):
            name = option.find('name')
            if ident is not None and name is not None and name.get('v') == 'defaultParentSize':
                width = _v(option, 'value').split('x')[0]
                if width.isdigit():
                    sizes[ident.get('v')] = int(width)
    return sizes


def _default_parent_log2(sbs_path: str, graph: str | None = None) -> int | None:
    """The default parent size (log2) of `graph`, or of every graph when they all agree; else None."""
    sizes = _default_parent_sizes(sbs_path)
    if graph:
        return sizes.get(graph.split('://')[-1])
    return next(iter(sizes.values())) if len(set(sizes.values())) == 1 else None


def _sbsar_default_log2(sbsar: str, graph: str | None = None) -> int | None:
    """Default $outputsize (log2) stored in a .sbsar, or None. A .sbsar is a 7-zip archive whose
    .xml description lists each input's default; the system tar (bsdtar on macOS and Windows 10+)
    can read it."""
    tar = shutil.which('tar')
    if not tar:
        return None
    try:
        listing = subprocess.run([tar, '-tf', sbsar], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None
    wanted = graph.split('://')[-1] if graph else None
    for member in [m for m in listing.stdout.splitlines() if m.endswith('.xml')] if listing.returncode == 0 else []:
        try:
            xml = subprocess.run([tar, '-xOf', sbsar, member], capture_output=True, timeout=60).stdout
        except subprocess.TimeoutExpired:
            return None
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


def _run_tool(cmd: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    """Run one of Designer's command-line tools; a hang becomes a ToolError, not a stuck server."""
    try:
        # UTF-8 whatever the locale (cp1252 on many Windows machines); a stray byte can't fail the call
        return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise ToolError('%s did not finish within %ds' % (os.path.basename(cmd[0]), timeout)) from e


def _sbsar_contents(sbsar: str) -> tuple[set[str], list[str]]:
    """(the input ids it exposes, its graph URLs), from `sbsrender info`."""
    result = _run_tool([cast(str, SBSRENDER), 'info', sbsar], 120)  # callers checked it
    if result.returncode != 0:
        raise ToolError('sbsrender info failed:\n' + result.stdout[-2000:] + result.stderr[-2000:])
    lines = [line.strip() for line in result.stdout.splitlines()]
    return (
        {line.split()[1] for line in lines if line.startswith('INPUT ')},
        [line.split()[1] for line in lines if line.startswith('GRAPH-URL ')],
    )


def _image_size(path: str) -> str:
    try:
        with PILImage.open(path) as im:
            return '%dx%d' % im.size
    except Exception:
        return ''


def _snapshot(folder: str) -> dict[str, tuple[int, int]]:
    # name -> (mtime_ns, size), to tell which files a render wrote
    return {f: (st.st_mtime_ns, st.st_size) for f in os.listdir(folder) for st in [os.stat(os.path.join(folder, f))]}


@contextlib.contextmanager
def _cooked(sbs_path: str) -> Iterator[str]:
    """A .sbsar for this .sbs, cooked into a temporary folder (never next to the user's file,
    where it would replace one of theirs); a .sbsar is used as it is."""
    path = os.path.abspath(os.path.expanduser(sbs_path))
    if path.endswith('.sbsar'):
        yield path
        return
    tmp = tempfile.mkdtemp(prefix='sd_cook_')
    try:
        cook = _run_tool([cast(str, SBSCOOKER), '--inputs', path, '--output-path', tmp], 900)  # callers checked it
        sbsar = os.path.join(tmp, os.path.splitext(os.path.basename(path))[0] + '.sbsar')
        if cook.returncode != 0 or not os.path.exists(sbsar):
            raise ToolError('sbscooker failed:\n' + cook.stdout[-3000:] + cook.stderr[-3000:])
        yield sbsar
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@_tool()
def sbsar_info(sbs_path: str) -> str:
    """List graphs, exposed inputs (with types) and outputs of a .sbs/.sbsar, i.e. what
    render_sbs can take as graph/outputs/params. A .sbs is cooked in a temporary folder."""
    if not (SBSCOOKER and SBSRENDER):
        raise ToolError('sbscooker/sbsrender not found. Set SD_DESIGNER_BIN_DIR.')
    with _cooked(sbs_path) as sbsar:
        info = _run_tool([SBSRENDER, 'info', sbsar], 120)
    if info.returncode != 0:
        raise ToolError(
            'sbsrender info failed (exit %d): %s' % (info.returncode, (info.stderr or info.stdout).strip()[-1500:])
        )
    return info.stdout.strip() or info.stderr.strip()


def _load_8bit(path: str) -> PILImage.Image:
    im: PILImage.Image = PILImage.open(path)
    if im.mode.startswith('I'):
        a = np.array(im).astype('float32')
        # a 16-bit PNG is 0..65535 however dark it is; plain 'I' has no fixed range
        scale = 65535.0 if im.mode.startswith('I;16') or a.max() > 255 else 255.0
        a = (a / scale * 255).clip(0, 255).astype('uint8')
        im = PILImage.fromarray(a)
    return im.convert('RGB')


@_tool()
def preview_maps(
    map_dir: str, names: list[str] | None = None, tile_size: int = 384, crop: list[int] | None = None
) -> Image:
    """Return a side-by-side preview of rendered maps (PNG files in map_dir). `names` picks
    maps by file stem (default: all). `crop` = [x0, y0, x1, y1] in source pixels to zoom in."""
    map_dir = os.path.abspath(os.path.expanduser(map_dir))
    if not os.path.isdir(map_dir):
        raise ToolError('%s is not a folder' % map_dir)
    found = sorted(os.path.splitext(f)[0] for f in os.listdir(map_dir) if f.endswith('.png'))
    if not found:
        raise ToolError('no .png files in %s' % map_dir)
    missing = [n for n in names or [] if n not in found]
    if missing:
        raise ToolError(
            'no map called %s in %s; there are: %s' % (', '.join(repr(n) for n in missing), map_dir, ', '.join(found))
        )
    tiles: list[PILImage.Image] = []
    for stem in names or found:
        im = _load_8bit(os.path.join(map_dir, stem + '.png'))
        if crop:  # checked like every other region (REVIEW.md SRV-23)
            im = im.crop(_crop_box(crop, im.width, im.height, 'crop for %s' % stem))
        scale = tile_size / max(im.size)
        tiles.append(im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale)))))
    return _sheet(tiles)
