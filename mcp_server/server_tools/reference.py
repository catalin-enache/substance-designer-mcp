"""analyze_reference: what a reference image holds, read from its file alone, so Designer may be closed. The image is
read by image_reading.py's _open_image, and its reference_region taken in the image it returns.

The palette (ROADMAP item 119) is the image's colour as a function of its luminance, as one Gradient Map gives it.
_palette reads it in four steps:

1. Each opaque pixel's values are clipped to 0..1, as the keys are, so that a float image's errors keep their order.
   Its luminance (_GREY: Designer's grey) is stretched from its 1st to its 99th percentile to 0..1: those are the
   keys' positions. When the two are equal (about 98% of the pixels or more at one luminance), it is
   stretched from its minimum to its maximum instead.
2. That range is cut into _LEVELS levels. Each level holding pixels gives a point: its pixels' mean position (0 for
   the darkest level, 1 for the brightest) and mean colour.
3. The keys go on some of those points (_knots): the first and the last, and between them the ones whose straight
   lines miss the other points least, weighted by their pixels, chosen by dynamic programming.
4. The keys' colours are the least squares fit over the pixels (_fit) of the keys' Gradient Map: linear between
   keys, the nearest key's colour outside them (GUIDE.md's scripting part, Gradient Map keys and Curve points).

The fit error is the RMS over R, G, B between the image and that Gradient Map on its luminance. The least error is the
same with a key on every level held: the colour that varies at one luminance, which no keys remove. One key's error,
the image's mean colour everywhere, is what they read against. The three are least squares fits over nested keys (one
key, these keys, a key on every level held), so before the colours are clipped to 0..1 one key's error is the largest
of them and the least error the smallest. Nothing is random, so the same image gives the same keys. k-means and median
cut were weighed and left out: their keys bunch at nearly one luminance, and k-means needs a seed.
"""

import json
import math
import os
from typing import Annotated, NamedTuple

import numpy as np
import numpy.typing as npt
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image as PILImage
from pydantic import Field

from .core import Box, NoneIfEmpty, _tool
from .image_reading import _finite, _integer_scale, _non_finite, _opaque, _open_image, _reference_pixels
from .measure import Values, _crop_box, _rgb

Colours = npt.NDArray[np.float64]  # (N, 3): R, G, B per row

_LEVELS = 64  # the luminance levels the stretched range is cut into, at most one key each
# The R, G, B weights of the luminance: the mean of R, G and B, Designer's grey. Its Grayscale Conversion gives it at its
# default, so the photo's own grey through that node and a levels from the range printed matches the keys' positions
# (GUIDE.md, The greys of a colour image). compare_to_reference's luma stays Rec.709's (compare.py's _LUMA)
_GREY: npt.NDArray[np.float64] = np.full(3, 1 / 3)
_MOST_PIXELS = 1 << 20  # a larger image is sampled down to about this many pixels first


class _Palette(NamedTuple):
    """A palette as _palette reads it: the keys' positions (0..1) and colours (R, G, B); the luminance at positions 0
    and 1, and whether those are its minimum and maximum (its 1st and 99th percentiles being equal) rather than those
    percentiles; the fit error, the least error (a key on every level held) and one key's error (the mean colour)."""

    positions: Values
    colours: Colours
    low: float
    high: float
    extremes: bool
    error: float
    floor: float
    one_key: float


def _palette(rgb: Colours, keys: int) -> _Palette:
    """The palette of the pixels `rgb`, (N, 3), clipped to 0..1 first, in at most `keys` keys (the module docstring)."""
    rgb = np.clip(rgb, 0, 1)
    grey = rgb @ _GREY
    low, high = (float(v) for v in np.percentile(grey, [1, 99]))
    extremes = low == high
    if extremes:  # about 98% of the pixels or more at one luminance: from the darkest to the brightest instead
        low, high = float(grey.min()), float(grey.max())
    t = np.clip((grey - low) / (high - low), 0, 1) if high > low else np.zeros(len(rgb))
    level = np.minimum((t * _LEVELS).astype(np.intp), _LEVELS - 1)
    counts = np.bincount(level, minlength=_LEVELS)
    held = np.flatnonzero(counts)
    weights = counts[held].astype(np.float64)
    positions = np.bincount(level, t, _LEVELS)[held] / weights
    if len(held) > 1:
        positions[[0, -1]] = 0, 1  # the darkest level holds the pixels at 0, the brightest those at 1
    means = _binned(level, rgb, _LEVELS)[held] / weights[:, None]
    chosen = positions[_knots(positions, means, weights, keys)]
    colours, error = _fit(t, rgb, chosen)
    floor = error if len(chosen) == len(positions) else _fit(t, rgb, positions)[1]
    one_key = float(np.sqrt(rgb.var(axis=0).mean()))  # the RMS of each pixel from the mean colour
    return _Palette(chosen, colours, low, high, extremes, error, floor, one_key)


def _binned(index: npt.NDArray[np.intp], values: Colours, size: int) -> Colours:
    """The sums of the rows of `values`, (N, C), by their `index`, as (size, C)."""
    return np.stack([np.bincount(index, v, size) for v in values.T], axis=1)


def _knots(x: Values, y: Colours, w: Values, keys: int) -> npt.NDArray[np.intp]:
    """The indices of the points the keys go on, of the points at positions `x` with colours `y` and pixel counts `w`:
    every point when there are no more than `keys`, the first for one key. Else the first, the last, and between
    them the ones whose straight lines miss the other points least (squared, weighted by `w`)."""
    m = len(x)
    if m <= keys:
        return np.arange(m)
    if keys == 1:
        return np.array([0])
    # miss[a, b]: what the straight line from point a to point b misses of the points between them; none for b <= a
    miss = np.full((m, m), np.inf)
    for a in range(m - 1):
        for b in range(a + 1, m):
            f = (x[a + 1 : b] - x[a]) / (x[b] - x[a])
            off = y[a + 1 : b] - (y[a] + f[:, None] * (y[b] - y[a]))
            miss[a, b] = w[a + 1 : b] @ (off**2).sum(axis=1)
    # least[b]: the least miss of the keys so far from point 0 to point b; before[n, b]: the key before b when b is
    # key n
    least = np.full(m, np.inf)
    least[0] = 0
    before = np.zeros((keys, m), np.intp)
    for n in range(1, keys):
        total = least[:, None] + miss
        before[n] = total.argmin(axis=0)
        least = total.min(axis=0)
    path = [m - 1]
    for n in range(keys - 1, 0, -1):
        path.append(int(before[n, path[-1]]))
    return np.array(path[::-1])


def _fit(t: Values, rgb: Colours, knots: Values) -> tuple[Colours, float]:
    """The colours of keys at the positions `knots` whose Gradient Map on `t` misses `rgb` least, clipped to 0..1, and
    the RMS over R, G, B of what it misses. Each pixel's colour is a mix of the two keys around it, so the fit is
    linear least squares. The miss is measured with np.interp, as the Gradient Map computes."""
    k = len(knots)
    if k == 1:
        colours = np.asarray(rgb.mean(axis=0, keepdims=True))
    else:
        left = np.clip(np.searchsorted(knots, t, side='right') - 1, 0, k - 2)
        share = np.clip((t - knots[left]) / (knots[left + 1] - knots[left]), 0, 1)
        mixes = ((left, 1 - share), (left + 1, share))  # each pixel's two keys and their shares of its colour
        gram = np.zeros(k * k)
        moments = np.zeros((k, 3))
        for i, wi in mixes:
            moments += _binned(i, wi[:, None] * rgb, k)
            for j, wj in mixes:
                gram += np.bincount(i * k + j, wi * wj, k * k)
        colours = np.clip(np.linalg.lstsq(gram.reshape(k, k), moments, rcond=None)[0], 0, 1)
    made = np.stack([np.interp(t, knots, c) for c in colours.T], axis=1)
    return colours, float(np.sqrt(((made - rgb) ** 2).mean()))


@_tool(read_only=True, destructive=False, idempotent=True, open_world=False)
def analyze_reference(
    reference_path: Annotated[str, Field(description='The reference image file.')],
    reference_region: Annotated[
        NoneIfEmpty[Box],
        Field(
            description='[x0, y0, x1, y1] in pixels: the part of the reference to read, e.g. a flat-lit area of a '
            'photo.'
        ),
    ] = None,
    keys: Annotated[
        int,
        Field(
            description="The palette's Gradient Map keys, 1 or more; fewer when the image has fewer of the 64 "
            'luminance levels.'
        ),
    ] = 5,
) -> str:
    """Read what a reference image holds, from its file alone (Designer may be closed): its palette, the image's colour
    as a function of its luminance, as `keys` Gradient Map keys. The keys come in the form apply_edits' set takes for a
    Gradient Map's gradientrgba. The fit and the errors are those of a Gradient Map at its default interpmode 0, linear
    between keys. The keys' positions stretch the image's luminance (the R, G, B weights of the result's
    luminance line) from its 1st to its 99th percentile to 0..1, or from its minimum to its maximum when those two are
    equal, and the result gives that range. Of two keys or more, the darkest is at 0, the brightest at 1, and the
    others go where the colour bends most.
    The result gives three errors, each the RMS over R, G, B (0..1) of a Gradient Map on the image's luminance against
    the image: the fit error, of these keys; the least error, of a key on every luminance level; and one key's error,
    of the image's mean colour everywhere, which the other two read against. A fit error near the least error means
    more keys won't help, and one above it means they will. A least error near one key's error means the colour
    doesn't follow luminance: where the image holds parts of different colours, a mask may split them, and on one
    material it is its grain, which no keys remove.
    Transparent pixels (alpha < 0.5) are left out, and so are a float image's NaN and infinite ones. Pixel values are
    clipped to 0..1 first, as the keys are. An image over
    about 1 MP is sampled down first, its pixels kept rather than averaged. The same image and arguments give the same keys."""
    if keys < 1:
        raise ToolError('keys is 1 or more, not %d' % keys)
    im = _open_image(reference_path)
    scale = _integer_scale(im)  # the whole image's, before the cut and the sampling, as compare_to_reference reads it
    if reference_region:  # cut before the sampling, which then reads only the region
        im = im.crop(_crop_box(reference_region, im.width, im.height, 'reference_region'))
    head = '%s: %dx%d pixels' % (os.path.basename(reference_path), im.width, im.height)
    if reference_region:
        head += ' in reference_region %s' % list(reference_region)
    if im.width * im.height > _MOST_PIXELS:
        shrink = math.sqrt(_MOST_PIXELS / (im.width * im.height))
        # nearest: each pixel kept is one of the image's, so no colour is made by blending two
        im = im.resize((max(1, int(im.width * shrink)), max(1, int(im.height * shrink))), PILImage.Resampling.NEAREST)
        head += ', sampled down to %dx%d' % im.size
    data, layout = _reference_pixels(im, scale)
    opaque, left_out = _opaque(data)
    rgb = _rgb(data, layout)
    finite, not_finite = _finite(data)  # a float image's NaN and infinite pixels, left out as transparent ones are
    kept = finite if opaque is None else finite & opaque
    if not kept.any():
        raise ToolError('no pixel of the reference is a finite number (NaN or infinite)')
    palette = _palette(rgb[kept], keys)
    found = len(palette.positions)
    lines = [head]
    if left_out:
        lines.append(left_out)
    if not_finite:
        lines.append('ignoring %s' % _non_finite(not_finite))
    weights = '%g R + %g G + %g B' % tuple(_GREY)
    stretched = (
        'the minimum and maximum of %s, as its 1st and 99th percentiles are equal' % weights
        if palette.extremes
        else 'the 1st and 99th percentiles of %s' % weights
    )
    lines += [
        'luminance %.4f to %.4f (%s) at positions 0 and 1' % (palette.low, palette.high, stretched),
        'gradientrgba: '
        + json.dumps(
            [
                [round(p, 4), [*(round(c, 4) for c in colour), 1.0]]
                for p, colour in zip(palette.positions.tolist(), palette.colours.tolist(), strict=True)
            ]
        ),
    ]
    if found < keys:
        lines.append(
            'keys: %d of the %d asked: the image has %d of the %d luminance levels' % (found, keys, found, _LEVELS)
        )
    lines += [
        "fit error %.4f: the RMS over R, G, B (0..1) of these keys' Gradient Map on the image's luminance, against the "
        'image' % palette.error,
        'least error %.4f, with a key on every luminance level: colour varying at one luminance, which no keys remove'
        % palette.floor,
        "one key's error %.4f, the image's mean colour everywhere: what the two errors above read against"
        % palette.one_key,
        "reading the errors: a fit error near the least error means more keys won't help, and one above it that they "
        "will; a least error near one key's error means the colour doesn't follow luminance: where the image holds "
        'parts of different colours, a mask may split them, and on one material it is its grain, which no keys remove',
    ]
    return '\n'.join(lines)
