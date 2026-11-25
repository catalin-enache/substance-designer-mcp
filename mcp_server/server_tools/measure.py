"""Measuring pixels: node_stats, sweep_param, check_tiling, and the pixel decoding they share. Reading image files is
image_reading.py's."""

import io
import json
import os
import re
import shutil
import tempfile
from typing import Annotated, Literal, TypedDict

import numpy as np
import numpy.typing as npt
from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image as PILImage
from pydantic import Field

from project_constants import Json

from .core import (
    AnyJson,
    Box,
    Graph,
    NoneIfEmpty,
    Output,
    Pixel,
    _bridge,
    _helpers_call,
    _output_note_in,
    _tool,
    _with_undo,
)

# decoded pixels: (H, W, C) floats
Pixels = npt.NDArray[np.float64]
Values = npt.NDArray[np.float64]  # one channel of them, (H, W) or flattened
# what decoded pixels hold: colour ('RGBA', 3 or 4 channels) or grey ('L', 1 channel, or 2 with alpha)
PixelLayout = Literal['RGBA', 'L']
# the type of one channel of a raw pixel, by Designer's pixel format (_PIXEL_TYPES)
PixelType = type[np.uint8 | np.uint16 | np.float16 | np.float32]

_PIXEL_TYPES: dict[str, tuple[PixelType, float]] = {
    '8': (np.uint8, 255.0),
    '16': (np.uint16, 65535.0),
    '16F': (np.float16, 1.0),
    '32F': (np.float32, 1.0),
}


# Designer's SBSPixelFormat names: channel prefix -> (channel count, order to put them in RGB(A)/L(A)).
# Longest prefixes first: LUMALPHA before LUM, RGBA before RGB.
_PIXEL_LAYOUTS: list[tuple[str, int, list[int]]] = [
    ('LUMALPHA', 2, [0, 1]),
    ('LUM', 1, [0]),
    ('RGBA', 4, [0, 1, 2, 3]),
    ('BGRA', 4, [2, 1, 0, 3]),
    ('RGB', 3, [0, 1, 2]),
    ('BGR', 3, [2, 1, 0]),
]


class _Layout(TypedDict):
    """A raw pixel buffer's layout, as the helpers print it in JSON (describe.py's dump_node_pixels, sweep.py's
    sweep_param): its size in pixels, bytes per row and per pixel, and Designer's pixel format (e.g. RGBA16)."""

    width: int
    height: int
    pitch: int
    bpp: int
    format: str


class _NodePixels(_Layout):
    """dump_node_pixels' PIXELS= line: the layout and the node read ('<id> <kind>.<output>'). _node_pixels adds the
    note: the helpers' line saying which output was taken (_output_note_in), or None without one."""

    node: str
    note: str | None


class _SweepTile(_Layout):
    """sweep_param's SWEEP= line, one per value tried: the layout, the value's index (its file is <index>.raw) and the
    value as the parameter holds it, only printed here: the helpers' fmt() form, a vector's or colour's components read
    back as a list, and a Gradient Map's keys or a Curve's points as nested lists."""

    index: int
    value: Json


def _decode_pixels(raw: bytes, meta: _Layout) -> tuple[Pixels, PixelLayout]:
    """Raw Designer pixel buffer -> (float array (H, W, C), values normalised to 0..1 for ints;
    'RGBA' for colour (3 or 4 channels, B and R swapped back for BGR formats) or 'L' for
    grayscale (1 channel, or 2 with alpha))."""
    fmt_name = meta['format']  # e.g. RGBA16, LUM8, RGBA32F, BGR8, LUMALPHA16F
    prefix, channels, order = next((l for l in _PIXEL_LAYOUTS if fmt_name.startswith(l[0])), ('', 0, None))
    depth = fmt_name[len(prefix) :]
    if not prefix or depth not in _PIXEL_TYPES:
        raise ToolError('unsupported pixel format %s' % fmt_name)
    dtype, scale = _PIXEL_TYPES[depth]
    rows = np.frombuffer(raw, dtype=np.uint8).reshape(meta['height'], meta['pitch'])
    rows = rows[:, : meta['width'] * meta['bpp']].copy()
    data = rows.view(dtype).reshape(meta['height'], meta['width'], channels)[:, :, order].astype(np.float64)
    return data / scale, ('RGBA' if channels >= 3 else 'L')


def _channel_names(data: Pixels, layout: str) -> str:
    """Channel letters of decoded pixels: 'RGBA', 'RGB', 'LA' or 'L'."""
    return ('RGBA', 'RGB')[data.shape[2] == 3] if layout == 'RGBA' else 'LA'[: data.shape[2]]


def _crop_box(region: Box, w: int, h: int, what: str) -> Box:
    """(x0, y0, x1, y1) for region [x0, y0, x1, y1] in pixels, clamped to a w x h image. An empty
    or inverted region is an error (numpy would silently wrap negative coordinates)."""
    x0, y0, x1, y1 = region
    x0, x1 = max(0, min(x0, w)), max(0, min(x1, w))
    y0, y1 = max(0, min(y0, h)), max(0, min(y1, h))
    if x1 <= x0 or y1 <= y0:
        raise ToolError('%s %s is empty for the %dx%d image' % (what, list(region), w, h))
    return x0, y0, x1, y1


def _crop(data: Pixels, region: Box, what: str) -> Pixels:
    """data[y0:y1, x0:x1] for region [x0, y0, x1, y1], clamped to the image (see _crop_box)."""
    x0, y0, x1, y1 = _crop_box(region, data.shape[1], data.shape[0], what)
    return data[y0:y1, x0:x1]


def _node_pixels(
    node_id: str, graph: str | None, output: str | None, tool: str
) -> tuple[Pixels, PixelLayout, _NodePixels]:
    """A node's output computed in Designer: (pixels 0..1 as (H, W, C) floats, 'RGBA' or 'L', meta);
    see _decode_pixels."""
    tmp_dir = tempfile.mkdtemp(prefix='sd_px_')
    raw_path = os.path.join(tmp_dir, 'pixels.raw')
    try:
        text = _bridge(
            _with_undo(
                _helpers_call('dump_node_pixels(%r, %r, %r, %r)' % (node_id, raw_path, graph, output)),
                'Claude: ' + tool.replace('_', ' '),
                edit=False,  # its step, a temporary node added and removed, changes nothing (core.py, SessionStep)
            ),
            '<%s>' % tool,
            300,
        )
        found = re.search(r'PIXELS=(\{.*\})', text)
        if not found or not os.path.exists(raw_path):
            raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'no pixel data')
        meta: _NodePixels = json.loads(found.group(1))
        meta['note'] = _output_note_in(text)
        with open(raw_path, 'rb') as f:
            data, layout = _decode_pixels(f.read(), meta)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return data, layout, meta


def _diff_lines(a: Pixels, a_names: str, b: Pixels, b_names: str, box: Box, tolerance: float) -> list[str]:
    """One line per channel both images have, by name (_channel_names), in a's order. Each line gives the largest
    absolute difference and where it is, the mean, and how many pixels differ by more than `tolerance`. a and b are
    whole images of one size, and box (x0, y0, x1, y1) the part compared. The location is in the whole image's pixels,
    on a tie the first pixel in row order."""
    x0, y0, x1, y1 = box
    lines = []
    for name in (n for n in a_names if n in b_names):
        d = a[y0:y1, x0:x1, a_names.index(name)] - b[y0:y1, x0:x1, b_names.index(name)]
        np.abs(d, out=d)
        y, x = np.unravel_index(np.argmax(d), d.shape)
        over = np.count_nonzero(d > tolerance)
        lines.append(
            '%s diff: max %.6f at (%d,%d)  mean %.6f  over %g: %d px (%.2f%%)'
            % (name, d[y, x], x + x0, y + y0, d.mean(), tolerance, over, 100 * over / d.size)
        )
    return lines


@_tool(read_only=False, destructive=False, idempotent=True, open_world=False)
def node_stats(
    node_id: Annotated[str, Field(description='The node whose output is measured.')],
    graph: Graph = None,
    output: Output = None,
    region: Annotated[
        NoneIfEmpty[Box],
        Field(description='[x0, y0, x1, y1] in pixels to restrict the stats, and the comparison with against.'),
    ] = None,
    points: Annotated[
        list[Pixel] | None, Field(description="[[x, y], ...] pixel values of node_id's output to sample.")
    ] = None,
    against: Annotated[
        str | None,
        Field(
            description='A node of the same graph, whose output is compared pixel by pixel. node_id itself compares two '
            'of its outputs: output and against_output.'
        ),
    ] = None,
    against_output: Annotated[
        str | None,
        Field(
            description="Which of against's outputs (default: the one tagged base colour, else the first; the result "
            'says which).'
        ),
    ] = None,
    tolerance: Annotated[
        float,
        Field(
            ge=0,
            description='With against: a pixel counts as differing where a channel differs by more than this, in 0..1 '
            'units (the default is about half an 8-bit step).',
        ),
    ] = 0.002,
) -> str:
    """Exact pixel statistics of any node's output (computed in Designer, read from the raw
    buffer, so 16-bit/float precision is kept). Per channel: min, max, mean, std.
    Values are 0..1 for integer formats. Use it to verify results numerically.
    With against, it also compares the output with another node's, or with another output of node_id, pixel by pixel,
    over the channels both have (in region if given). Per channel it gives the largest absolute difference and where
    it is, the mean, and how many pixels differ by more than tolerance. Two outputs of different sizes, or a grey one
    against a colour one (with alpha or not), are refused, naming both.
    The call may add a temporary output node and delete it, one undo step per output read."""
    data, layout, meta = _node_pixels(node_id, graph, output, 'node_stats')
    h, w, _ = data.shape
    lines = ['%s: %dx%d %s' % (meta['node'], w, h, meta['format'])]
    if meta['note']:
        lines.append(meta['note'])
    box = _crop_box(region or (0, 0, w, h), w, h, 'region')
    x0, y0, x1, y1 = box
    area = data[y0:y1, x0:x1]
    if region:
        lines.append('region %s (%dx%d px)' % (list(region), area.shape[1], area.shape[0]))
    names = _channel_names(data, layout)
    for ch, name in enumerate(names):
        a = area[:, :, ch]
        lines.append('%s: min %.4f  max %.4f  mean %.4f  std %.4f' % (name, a.min(), a.max(), a.mean(), a.std()))
    if against:
        other, other_layout, other_meta = _node_pixels(against, graph, against_output, 'node_stats')
        oh, ow, _ = other.shape
        if (ow, oh) != (w, h):
            raise ToolError(
                "can't compare outputs of different sizes: %s is %dx%d, %s is %dx%d"
                % (meta['node'], w, h, other_meta['node'], ow, oh)
            )
        if other_layout != layout:
            raise ToolError(
                '%s is %s and %s is %s: one is grey and the other colour. Compare one channel of the colour output, '
                'taken with an rgba_split node, or another output'
                % (meta['node'], meta['format'], other_meta['node'], other_meta['format'])
            )
        lines.append('against %s: %dx%d %s' % (other_meta['node'], ow, oh, other_meta['format']))
        if other_meta['note']:
            lines.append(other_meta['note'])
        lines += _diff_lines(data, names, other, _channel_names(other, other_layout), box, tolerance)
    for x, y in points or []:
        if 0 <= x < w and 0 <= y < h:
            lines.append(
                'pixel (%d,%d): %s'
                % (x, y, ', '.join('%s=%.4f' % (n, v) for n, v in zip(names, data[y, x], strict=False)))
            )
        else:
            lines.append('pixel (%d,%d): outside the %dx%d image' % (x, y, w, h))
    return '\n'.join(lines)


def _rgb(data: Pixels, layout: PixelLayout) -> Pixels:
    """Decoded pixels -> their R, G, B as (H, W, 3): a grey image's one channel three times, alpha left out."""
    return data[:, :, :3] if layout == 'RGBA' else np.repeat(data[:, :, :1], 3, axis=2)


def _to_display(data: Pixels, layout: PixelLayout) -> PILImage.Image:
    """Decoded pixels (0..1 floats) -> 8-bit RGB PIL image for previews."""
    return PILImage.fromarray((np.clip(_rgb(data, layout), 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')


LABEL_CHARS = 48  # the most characters of a tile's label drawn


def _labelled(im: PILImage.Image, label: str, short: str | None = None) -> PILImage.Image:
    """Image with a dark caption bar on top: `label` on one line, its newlines as spaces (Pillow can't measure a
    newline), or `short` where `label` would be cut: longer than LABEL_CHARS, or wider than the image."""
    from PIL import ImageDraw

    tile = PILImage.new('RGB', (im.width, im.height + 18), (30, 30, 30))
    tile.paste(im, (0, 18))
    draw = ImageDraw.Draw(tile)
    shown = ' '.join(label.splitlines())
    if short is not None and (len(shown) > LABEL_CHARS or draw.textlength(shown) > im.width - 4):
        shown = short
    draw.text((4, 3), shown[:LABEL_CHARS], fill=(230, 230, 230))
    return tile


def _sheet(tiles: list[PILImage.Image], gap: int = 6) -> Image:
    """Tiles side by side on white -> MCP PNG image."""
    sheet = PILImage.new(
        'RGB', (sum(t.width for t in tiles) + gap * (len(tiles) - 1), max(t.height for t in tiles)), 'white'
    )
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0))
        x += t.width + gap
    buf = io.BytesIO()
    sheet.save(buf, format='PNG')
    return Image(data=buf.getvalue(), format='png')


def _channel_summary(data: Pixels, layout: str) -> str:
    names = _channel_names(data, layout)
    return '  '.join(
        '%s %.3f..%.3f (mean %.3f)'
        % (
            n,
            data[:, :, i].min(),
            data[:, :, i].max(),
            data[:, :, i].mean(),
        )
        for i, n in enumerate(names)
    )


@_tool(read_only=False, destructive=False, idempotent=True, open_world=False)
def sweep_param(
    node_id: Annotated[str, Field(description='The node whose parameter is swept.')],
    param: Annotated[str, Field(description="The parameter's id.")],
    values: Annotated[list[AnyJson], Field(description='The values to try.')],
    graph: Graph = None,
    view_node: Annotated[
        str | None,
        Field(
            description='The node to look at (default: the swept node), e.g. the final output while sweeping an early '
            'node.'
        ),
    ] = None,
    output: Annotated[
        str | None,
        Field(
            description="Which of view_node's outputs (default: the one tagged base colour, else the first; the result "
            'says which).'
        ),
    ] = None,
    tile_size: Annotated[
        int, Field(description="Each tile's longest side in pixels, at most (a larger image is scaled down).")
    ] = 256,
) -> list[str | Image]:
    """Try several values of one parameter and see them side by side: returns a labelled image
    strip plus per-value channel ranges, then restores the original value. A value too long for its
    tile's label, such as keys, is labelled by its place in values (#1, #2...). node_id='graph' with
    param=<input id> sweeps an exposed graph input (then view_node is required). Values are converted as in apply_edits' set op, but a $ parameter is made Absolute for the sweep
    even where a set op refuses it or leaves it inherited (an overridable graph's $outputsize, the
    graph's $randomseed), so its values are absolute ones. The parameter ends where it started,
    inheritance included, but the sweep is an undo step and marks the package as modified. If the sweep fails after it
    set a value, Designer's Undo takes that step back while it is the newest, and the error says so."""
    if not values:
        raise ToolError('values: give at least one value to try')  # REVIEW.md SRV-30
    tmp_dir = tempfile.mkdtemp(prefix='sd_sweep_')
    try:
        text = _bridge(
            _with_undo(
                _helpers_call(
                    'sweep_param(%r, %r, %r, %r, %r, %r, %r)'
                    % (graph, node_id, param, values, tmp_dir, view_node, output)
                ),
                'Claude: sweep ' + param,
                edit=False,  # its step, the values set and the first put back, changes nothing (core.py, SessionStep)
            ),
            '<sweep_param>',
            600,
        )
        metas: list[_SweepTile] = [json.loads(m) for m in re.findall(r'SWEEP=(\{.*\})', text)]
        if not metas:
            raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'sweep produced nothing')
        tiles: list[PILImage.Image] = []
        # the helper prints 'restored <node>.<param> to ...' once the value is back; a line of its own: an output's
        # name in the note can hold the word too (REVIEW.md SRV-61)
        restored = re.search(r'^restored .*$', text, re.M)
        lines = [
            '%s.%s sweep (%s):'
            % (
                node_id,
                param,
                restored.group(0) if restored else 'original NOT restored!',
            )
        ]
        note = _output_note_in(text)
        if note:
            lines.append(note)
        for meta in metas:
            with open(os.path.join(tmp_dir, '%d.raw' % meta['index']), 'rb') as f:
                data, layout = _decode_pixels(f.read(), meta)
            lines.append(
                '%s = %r (%dx%d): %s'
                % (param, meta['value'], meta['width'], meta['height'], _channel_summary(data, layout))
            )
            im = _to_display(data, layout)
            im.thumbnail((tile_size, tile_size))
            # a value too long for its label, such as keys, is labelled by its place in values, first so that a narrow
            # tile keeps it: cut, every tile would show its first key (REVIEW.md SRV-222, SRV-223)
            tiles.append(_labelled(im, '%s = %s' % (param, meta['value']), '#%d %s' % (meta['index'] + 1, param)))
        if '--- ERROR ---' in text:
            error = text.split('--- ERROR ---', 1)[1].strip().splitlines()
            lines.append(
                'Sweep stopped after %d of %d value(s): %s' % (len(metas), len(values), error[-1] if error else 'error')
            )
        if not restored:
            lines.append('WARNING: the original value may not have been restored:\n' + text[-1500:])
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return ['\n'.join(lines), _sheet(tiles)]


def _seam_report(data: Pixels, axis_name: str, seam_axis: int) -> str:
    """Compare the wrap-around seam with typical neighbour steps along one axis."""
    a = np.moveaxis(data, seam_axis, 0)  # axis 0 = direction across the seam
    steps = np.abs(np.diff(a, axis=0))  # all interior neighbour differences
    seam = np.abs(a[0] - a[-1])  # first vs last line (they meet when tiled)
    interior_mean = float(steps.mean())
    seam_mean = float(seam.mean())
    ratio = seam_mean / interior_mean if interior_mean > 1e-9 else (0.0 if seam_mean < 1e-9 else float('inf'))
    worst = float(seam.max())
    per_pos = seam.max(axis=-1)  # worst channel per position along the seam
    worst_at = int(np.argmax(per_pos))
    verdict = 'tiles seamlessly' if ratio <= 1.5 else 'probably fine' if ratio <= 3 else 'VISIBLE SEAM'
    where = 'row' if axis_name == 'horizontal' else 'column'
    return (
        '%s tiling (left/right edges): seam step %.4f vs typical %.4f (ratio %.2f), worst %.4f at %s %d: %s'
        if axis_name == 'horizontal'
        else '%s tiling (top/bottom edges): seam step %.4f vs typical %.4f (ratio %.2f), worst %.4f at %s %d: %s'
    ) % (axis_name.capitalize(), seam_mean, interior_mean, ratio, worst, where, worst_at, verdict)


@_tool(read_only=False, destructive=False, idempotent=True, open_world=False)
def check_tiling(
    node_id: Annotated[str, Field(description='The node whose output is measured.')],
    graph: Graph = None,
    output: Output = None,
    axis: Annotated[
        str, Field(description="'horizontal', 'vertical' or 'both' (trim sheets usually only need horizontal).")
    ] = 'both',
) -> str:
    """Measure whether a node's output tiles: compares the jump across the wrap-around seam
    (left/right edges for 'horizontal', top/bottom for 'vertical') with the typical jump between
    neighbouring pixels. Ratio ~1 = seamless; above ~3 a seam is likely visible.
    The call may add a temporary output node and delete it, within one undo step."""
    if axis not in ('horizontal', 'vertical', 'both'):
        raise ToolError("axis must be 'horizontal', 'vertical' or 'both'")
    data, _, meta = _node_pixels(node_id, graph, output, 'check_tiling')
    lines = ['%s: %dx%d %s' % (meta['node'], meta['width'], meta['height'], meta['format'])]
    if meta['note']:
        lines.append(meta['note'])
    if axis in ('horizontal', 'both'):
        lines.append(_seam_report(data, 'horizontal', 1))
    if axis in ('vertical', 'both'):
        lines.append(_seam_report(data, 'vertical', 0))
    return '\n'.join(lines)
