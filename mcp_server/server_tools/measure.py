"""Measuring pixels: node_stats, sweep_param, check_tiling, and the pixel decoding they share."""

import io
import json
import os
import re
import shutil
import tempfile
from typing import Any, cast

import numpy as np
import numpy.typing as npt
from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image as PILImage

from .core import _bridge, _helpers_call, _tool, _with_undo

# decoded pixels: (H, W, C) floats
Pixels = npt.NDArray[np.float64]
# numpy 2.5's stubs declare ndarray.min()/max() without arguments in a way mypy doesn't match
# ("All overload variants ... require at least one argument"), hence the ignores on those calls.

_PIXEL_TYPES: dict[str, tuple[type[np.generic], float]] = {
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


def _decode_pixels(raw: bytes, meta: dict[str, Any]) -> tuple[Pixels, str]:
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


def _crop_box(region: list[int], w: int, h: int, what: str) -> tuple[int, int, int, int]:
    """(x0, y0, x1, y1) for region [x0, y0, x1, y1] in pixels, clamped to a w x h image. An empty
    or inverted region is an error (numpy would silently wrap negative coordinates)."""
    if len(region) != 4:
        raise ToolError('%s must be [x0, y0, x1, y1]' % what)
    x0, y0, x1, y1 = (int(v) for v in region)
    x0, x1 = max(0, min(x0, w)), max(0, min(x1, w))
    y0, y1 = max(0, min(y0, h)), max(0, min(y1, h))
    if x1 <= x0 or y1 <= y0:
        raise ToolError('%s %s is empty for the %dx%d image' % (what, list(region), w, h))
    return x0, y0, x1, y1


def _crop(data: Pixels, region: list[int], what: str) -> Pixels:
    """data[y0:y1, x0:x1] for region [x0, y0, x1, y1], clamped to the image (see _crop_box)."""
    x0, y0, x1, y1 = _crop_box(region, data.shape[1], data.shape[0], what)
    return data[y0:y1, x0:x1]


def _node_pixels(node_id: str, graph: str | None, output: str | None, tool: str) -> tuple[Pixels, str, dict[str, Any]]:
    """A node's output computed in Designer: (pixels 0..1 as (H, W, C) floats, 'RGBA' or 'L', meta);
    see _decode_pixels."""
    tmp_dir = tempfile.mkdtemp(prefix='sd_px_')
    raw_path = os.path.join(tmp_dir, 'pixels.raw')
    try:
        text = _bridge(
            _with_undo(
                _helpers_call('dump_node_pixels(%r, %r, %r, %r)' % (node_id, raw_path, graph, output)),
                'Claude: ' + tool.replace('_', ' '),
            ),
            '<%s>' % tool,
            300,
        )
        found = re.search(r'PIXELS=(\{.*\})', text)
        if not found or not os.path.exists(raw_path):
            raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'no pixel data')
        meta: dict[str, Any] = json.loads(found.group(1))
        with open(raw_path, 'rb') as f:
            data, layout = _decode_pixels(f.read(), meta)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return data, layout, meta


@_tool()
def node_stats(
    node_id: str,
    graph: str | None = None,
    output: str | None = None,
    region: list[int] | None = None,
    points: list[list[int]] | None = None,
) -> str:
    """Exact pixel statistics of any node's output (computed in Designer, read from the raw
    buffer, so 16-bit/float precision is kept). Per channel: min, max, mean, std.
    region: [x0, y0, x1, y1] in pixels to restrict the stats. points: [[x, y], ...] pixel
    values to sample. Values are 0..1 for integer formats. Use it to verify results numerically."""
    data, layout, meta = _node_pixels(node_id, graph, output, 'node_stats')
    h, w, _ = data.shape
    lines = ['%s: %dx%d %s' % (meta['node'], w, h, meta['format'])]
    area = data
    if region:
        area = _crop(data, region, 'region')
        lines.append('region %s (%dx%d px)' % (list(region), area.shape[1], area.shape[0]))
    names = _channel_names(data, layout)
    for ch, name in enumerate(names):
        a = area[:, :, ch]
        lines.append('%s: min %.4f  max %.4f  mean %.4f  std %.4f' % (name, a.min(), a.max(), a.mean(), a.std()))  # type: ignore[call-overload]  # numpy stubs: see Pixels
    for x, y in points or []:
        if 0 <= x < w and 0 <= y < h:
            lines.append(
                'pixel (%d,%d): %s'
                % (x, y, ', '.join('%s=%.4f' % (n, v) for n, v in zip(names, data[y, x], strict=False)))
            )
        else:
            lines.append('pixel (%d,%d): outside the %dx%d image' % (x, y, w, h))
    return '\n'.join(lines)


def _to_display(data: Pixels, layout: str) -> PILImage.Image:
    """Decoded pixels (0..1 floats) -> 8-bit RGB PIL image for previews."""
    rgb = data[:, :, :3] if layout == 'RGBA' else np.repeat(data[:, :, :1], 3, axis=2)
    return PILImage.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')


def _labelled(im: PILImage.Image, label: str) -> PILImage.Image:
    """Image with a dark caption bar on top."""
    from PIL import ImageDraw

    tile = PILImage.new('RGB', (im.width, im.height + 18), (30, 30, 30))
    tile.paste(im, (0, 18))
    ImageDraw.Draw(tile).text((4, 3), label[:48], fill=(230, 230, 230))
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
            data[:, :, i].min(),  # type: ignore[call-overload]  # numpy stubs: see Pixels
            data[:, :, i].max(),  # type: ignore[call-overload]  # numpy stubs: see Pixels
            data[:, :, i].mean(),
        )
        for i, n in enumerate(names)
    )


@_tool()
def sweep_param(
    node_id: str,
    param: str,
    values: list[Any],
    graph: str | None = None,
    view_node: str | None = None,
    output: str | None = None,
    tile_size: int = 256,
) -> list[str | Image]:
    """Try several values of one parameter and see them side by side: returns a labelled image
    strip plus per-value channel ranges, then restores the original value. node_id='graph' with
    param=<input id> sweeps an exposed graph input (then view_node is required). view_node: the
    node to look at (default: the swept node), e.g. the final output while sweeping an early
    node. Values are converted as in apply_edits' set op, but a $ parameter is made Absolute for the sweep
    even where a set op refuses it or leaves it inherited (an overridable graph's $outputsize, the
    graph's $randomseed), so its values are absolute ones. The parameter ends where it started,
    inheritance included, but the sweep is an undo step and marks the package as modified."""
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
            ),
            '<sweep_param>',
            600,
        )
        metas: list[dict[str, Any]] = [json.loads(m) for m in re.findall(r'SWEEP=(\{.*\})', text)]
        if not metas:
            raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'sweep produced nothing')
        tiles: list[PILImage.Image] = []
        # the helper prints 'restored <node>.<param> to ...' once the value is back
        lines = [
            '%s.%s sweep (%s):'
            % (
                node_id,
                param,
                cast(re.Match[str], re.search(r'restored .*', text)).group(0)
                if 'restored' in text
                else 'original NOT restored!',
            )
        ]
        for meta in metas:
            with open(os.path.join(tmp_dir, '%d.raw' % meta['index']), 'rb') as f:
                data, layout = _decode_pixels(f.read(), meta)
            lines.append(
                '%s = %r (%dx%d): %s'
                % (param, meta['value'], meta['width'], meta['height'], _channel_summary(data, layout))
            )
            im = _to_display(data, layout)
            im.thumbnail((tile_size, tile_size))
            tiles.append(_labelled(im, '%s = %s' % (param, meta['value'])))
        if '--- ERROR ---' in text:
            error = text.split('--- ERROR ---', 1)[1].strip().splitlines()
            lines.append(
                'Sweep stopped after %d of %d value(s): %s' % (len(metas), len(values), error[-1] if error else 'error')
            )
        if 'restored' not in text:
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


@_tool()
def check_tiling(node_id: str, graph: str | None = None, output: str | None = None, axis: str = 'both') -> str:
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
