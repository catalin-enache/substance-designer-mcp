"""compare_to_reference: tones of a node against a reference image."""

import os
from typing import cast

import numpy as np
import numpy.typing as npt
from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image as PILImage

from .core import _tool
from .measure import Pixels, _crop, _labelled, _node_pixels, _sheet, _to_display

Values = npt.NDArray[np.float64]  # one channel, (H, W) or flattened

_LUMA = np.array([0.2126, 0.7152, 0.0722])


def _load_reference(path: str, region: list[int] | None = None) -> tuple[Pixels, str]:
    """Image file -> (pixels 0..1 as (H, W, C) floats, 'RGBA' or 'L'; a grayscale image with alpha
    is 'L' with alpha as a second channel). PIL reads 16-bit RGBA PNGs as 8-bit; 16-bit grayscale
    and float (mode F) keep their precision."""
    path = os.path.abspath(os.path.expanduser(path))
    try:
        im = PILImage.open(path)
        im.load()
    except (OSError, ValueError) as e:
        raise ToolError('cannot read %s: %s' % (path, e)) from e
    if im.mode in ('I', 'I;16', 'I;16B', 'I;16L', 'F'):
        a = np.array(im).astype(np.float64)
        if im.mode != 'F':
            a /= 65535.0 if im.mode.startswith('I;16') or a.max() > 255 else 255.0  # type: ignore[call-overload]  # numpy stubs: see measure.Pixels
        data, layout = a[:, :, None], 'L'
    elif im.mode in ('1', 'L'):
        data, layout = np.array(im.convert('L')).astype(np.float64)[:, :, None] / 255.0, 'L'
    elif im.mode in ('LA', 'La'):
        data, layout = np.array(im.convert('LA')).astype(np.float64) / 255.0, 'L'
    else:
        data, layout = np.array(im.convert('RGBA')).astype(np.float64) / 255.0, 'RGBA'
    if region:
        data = _crop(data, region, 'reference_region')
    return data, layout


def _compare_channels(a: Pixels, a_layout: str, b: Pixels, b_layout: str) -> list[tuple[str, Values, Values]]:
    """Shared channels to compare: R, G, B and luma when both are colour, else luma only."""

    def luma(d: Pixels, layout: str) -> Values:
        return d[:, :, :3] @ _LUMA if layout == 'RGBA' else d[:, :, 0]

    chans = [('luma', luma(a, a_layout), luma(b, b_layout))]
    if a_layout == b_layout == 'RGBA':
        chans = [(n, a[:, :, i], b[:, :, i]) for i, n in enumerate('RGB')] + chans
    return chans


def _emd(x: Values, y: Values) -> float:
    """Earth mover's distance between two value distributions: how far values must move on
    average (0..1 units) to turn one histogram into the other."""
    q = np.linspace(0, 1, 257)
    return float(np.abs(np.quantile(x, q) - np.quantile(y, q)).mean())


def _resize(data: Pixels, size: tuple[int, int]) -> Pixels:
    """Float image (H, W, C) -> size (w, h), channel by channel (box when shrinking)."""
    shrink = size[0] < data.shape[1]
    method = PILImage.Resampling.BOX if shrink else PILImage.Resampling.BILINEAR
    return np.dstack(
        [
            np.array(PILImage.fromarray(data[:, :, c].astype(np.float32), 'F').resize(size, method))
            for c in range(data.shape[2])
        ]
    ).astype(np.float64)


def _alpha(data: Pixels) -> Values | None:
    """The alpha channel of decoded pixels (4 channels, or 'L' with alpha), or None."""
    return data[:, :, -1] if data.shape[2] in (2, 4) else None


def _compare_report(
    node: Pixels, node_layout: str, ref: Pixels, ref_layout: str, aligned: bool = False
) -> tuple[list[str], Values | None]:
    """Compare a node's pixels with a reference: value distributions always, pixel by pixel when
    aligned. Returns (text lines, absolute luma difference image or None)."""
    lines: list[str] = []
    mask_n: npt.NDArray[np.bool_] | None = None
    mask_r: npt.NDArray[np.bool_] | None = None
    if _alpha(ref) is not None and (cast(Values, _alpha(ref)) < 0.5).any():
        mask_r = cast(Values, _alpha(ref)) >= 0.5
        if not mask_r.any():
            raise ToolError('the reference is fully transparent')
        lines.append('ignoring %.1f%% transparent reference pixels' % (100 - 100 * mask_r.mean()))
    diff: Values | None = None
    if aligned:
        h, w = node.shape[:2]
        if abs(ref.shape[1] / ref.shape[0] - w / h) > 0.01 * w / h:
            lines.append(
                'WARNING: aspect ratios differ (%dx%d vs %dx%d); the reference is stretched'
                % (w, h, ref.shape[1], ref.shape[0])
            )
        if ref.shape[:2] != (h, w):
            ref = _resize(ref, (w, h))
            if mask_r is not None:  # ref has alpha, and resizing keeps it
                mask_r = cast(Values, _alpha(ref)) >= 0.5
        mask_n = mask_r
    chans = _compare_channels(node, node_layout, ref, ref_layout)
    lines.append(
        '%-5s %-36s %-36s %s' % ('', 'node: mean std (p5 p50 p95)', 'reference: mean std (p5 p50 p95)', 'difference')
    )
    fixes: list[str] = []
    for name, a, b in chans:
        a = a[mask_n] if mask_n is not None else a.ravel()
        b = b[mask_r] if mask_r is not None else b.ravel()
        pa, pb = np.percentile(a, [5, 50, 95]), np.percentile(b, [5, 50, 95])
        sa, sb = float(a.std()), float(b.std())
        lines.append(
            '%-5s %.3f %.3f (%.3f %.3f %.3f)%s %.3f %.3f (%.3f %.3f %.3f)%s mean %+.3f  contrast x%.2f  EMD %.3f'
            % (
                name,
                a.mean(),
                sa,
                *pa,
                ' ' * 7,
                b.mean(),
                sb,
                *pb,
                ' ' * 7,
                b.mean() - a.mean(),
                sb / sa if sa > 1e-9 else float('inf'),
                _emd(a, b),
            )
        )
        if sa > 1e-9:
            gain = sb / sa
            fixes.append('%s: x*%.3f %+.3f' % (name, gain, b.mean() - a.mean() * gain))
    emd = _emd(
        chans[-1][1][mask_n] if mask_n is not None else chans[-1][1].ravel(),
        chans[-1][2][mask_r] if mask_r is not None else chans[-1][2].ravel(),
    )
    lines.append(
        'luma distributions: %s (EMD %.3f; rough guide: < 0.02 close, < 0.05 similar)'
        % ('close' if emd < 0.02 else 'similar' if emd < 0.05 else 'different', emd)
    )
    if fixes:
        lines.append('to match mean and contrast (levels/linear map): ' + ', '.join(fixes))
    if aligned:
        lines.append('pixel by pixel (reference resized to %dx%d):' % (node.shape[1], node.shape[0]))
        for name, a, b in chans:
            d = np.abs(a - b)
            if mask_n is not None:
                d = d[mask_n]
            lines.append(
                '  %-5s mean abs diff %.4f  RMSE %.4f  max %.4f' % (name, d.mean(), np.sqrt((d**2).mean()), d.max())
            )
        diff = np.abs(chans[-1][1] - chans[-1][2])
        if mask_n is not None:
            diff = np.where(mask_n, diff, 0.0)
    return lines, diff


def _histogram_tile(node_luma: Values, ref_luma: Values, width: int, height: int, bins: int = 64) -> PILImage.Image:
    """Luma histograms: node as filled bars, reference as an orange line."""
    from PIL import ImageDraw

    hn = np.histogram(node_luma, bins=bins, range=(0, 1))[0].astype(float)
    hr = np.histogram(ref_luma, bins=bins, range=(0, 1))[0].astype(float)
    hn, hr = hn / max(hn.sum(), 1), hr / max(hr.sum(), 1)
    top = max(hn.max(), hr.max(), 1e-9)
    im = PILImage.new('RGB', (width, height), (24, 24, 24))
    d = ImageDraw.Draw(im)
    bw = width / bins

    def y(v: float) -> float:
        return cast(float, height - 1 - v / top * (height - 20))

    for i, v in enumerate(hn):
        d.rectangle([i * bw, y(v), (i + 1) * bw - 1, height - 1], fill=(90, 150, 220))
    d.line([((i + 0.5) * bw, y(v)) for i, v in enumerate(hr)], fill=(255, 150, 40), width=2)
    d.text((4, 3), 'node', fill=(90, 150, 220))
    d.text((40, 3), 'reference', fill=(255, 150, 40))
    return im


@_tool()
def compare_to_reference(
    node_id: str,
    reference_path: str,
    graph: str | None = None,
    output: str | None = None,
    region: list[int] | None = None,
    reference_region: list[int] | None = None,
    aligned: bool = False,
    tile_size: int = 256,
) -> list[str | Image]:
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
        data = _crop(data, region, 'region')
    ref, ref_layout = _load_reference(reference_path, reference_region)
    lines, diff = _compare_report(data, layout, ref, ref_layout, aligned)
    lines.insert(
        0,
        '%s (%dx%d %s) vs %s (%dx%d)'
        % (
            meta['node'],
            data.shape[1],
            data.shape[0],
            meta['format'],
            os.path.basename(reference_path),
            ref.shape[1],
            ref.shape[0],
        ),
    )
    tiles: list[PILImage.Image] = []
    for im, label in ((_to_display(data, layout), 'node'), (_to_display(ref, ref_layout), 'reference')):
        im.thumbnail((tile_size, tile_size))
        tiles.append(_labelled(im, label))
    chans = _compare_channels(data, layout, ref, ref_layout)
    alpha = _alpha(ref)
    ref_luma = chans[-1][2] if alpha is None or (alpha >= 0.5).all() else chans[-1][2][alpha >= 0.5]
    tiles.append(
        _labelled(
            _histogram_tile(
                chans[-1][1].ravel(), ref_luma.ravel(), tile_size, max(max(t.height for t in tiles) - 18, 96)
            ),
            'luma histograms',
        )
    )
    if diff is not None:
        peak = max(float(diff.max()), 1e-9)  # type: ignore[call-overload]  # numpy stubs: see measure.Pixels
        im = _to_display((diff / peak)[:, :, None], 'L')
        im.thumbnail((tile_size, tile_size))
        tiles.append(_labelled(im, 'difference (white = %.3f)' % peak))
    return ['\n'.join(lines), _sheet(tiles)]
