"""What bitmaps' checks of a palette build and read (checks.py: check_designer_greys, check_photo_to_gradient_map): a
strip of known colours and a synthetic photo, each saved as an 8-bit PNG, the greys Designer's nodes are expected to
make of them, and analyze_reference's and compare_to_reference's results read as numbers."""

import json
import re
from collections.abc import Callable
from typing import NamedTuple

import numpy as np
from PIL import Image as PILImage

from project_constants import JsonSent

Rgb = tuple[float, float, float]
Rgba = tuple[float, float, float, float]
# the strip's colours, as 8-bit values: red, green, blue, white, black, a grey, and an orange and a teal whose R, G and B
# all differ
STRIP: tuple[tuple[int, int, int], ...] = (
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 255),
    (0, 0, 0),
    (128, 128, 128),
    (204, 102, 51),
    (51, 153, 204),
)
# px: the side of each of the strip's swatches, so that the strip is 64x8: a bitmap node of an image whose sides aren't
# powers of 2 stretches it (GUIDE.md's scripting part, Bitmaps)
SWATCH = 8
# the photo's colours at its left edge, its middle and its right edge. The mean of R, G and B rises from one to the next,
# and Rec.709's luma rises too, by other steps: keys placed by another grey than Designer's land elsewhere
RAMP: tuple[Rgb, Rgb, Rgb] = ((0.10, 0.10, 0.40), (0.25, 0.65, 0.20), (0.95, 0.85, 0.60))
SHIFT = 0.04  # each odd row of the photo has its R raised and its G lowered by this, its grey unchanged


def strip(path: str) -> str:
    """STRIP's colours as square swatches side by side, SWATCH px each, saved at `path`."""
    pixels = np.concatenate([np.full((SWATCH, SWATCH, 3), rgb, np.uint8) for rgb in STRIP], axis=1)
    PILImage.fromarray(pixels).save(path)
    return path


def strip_points() -> list[list[int]]:
    """A pixel in the middle of each of strip()'s swatches, in STRIP's order."""
    return [[i * SWATCH + SWATCH // 2, SWATCH // 2] for i in range(len(STRIP))]


def photo(path: str) -> str:
    """A synthetic photo, 128x64, saved at `path`: each column is RAMP's colour at its place, linear from the left edge
    to the middle and from the middle to the right edge. Each odd row is shifted by SHIFT, so the photo's colour varies
    at one grey, which no Gradient Map matches: its fit error is above 0."""
    t = np.linspace(0, 1, 128)
    row = np.stack([np.interp(t, [0, 0.5, 1], [rgb[c] for rgb in RAMP]) for c in range(3)], axis=1)
    rows = np.repeat(row[None], 64, axis=0)
    rows[1::2] += [SHIFT, -SHIFT, 0]
    PILImage.fromarray(np.round(rows * 255).astype(np.uint8)).save(path)
    return path


class Grey(NamedTuple):
    """A grey check_designer_greys measures: what its line says, the node's definition and parameters, its input
    connector, and the grey it gives of a colour."""

    said: str
    definition: str
    params: dict[str, JsonSent]
    connector: str
    of: Callable[[Rgb], float]


def _desaturated(rgb: Rgb) -> float:
    return (max(rgb) + min(rgb)) / 2


# Grayscale Conversion Advanced's grayscale_type, from 0: what it is, and the grey it gives of a colour
_ADVANCED: tuple[tuple[str, Callable[[Rgb], float]], ...] = (
    ('Desaturation: the mean of the largest and smallest of R, G, B', _desaturated),
    # Rec.601's weights, those of its package's own grayscaleconversion node
    ("Luma: Rec.601's", lambda rgb: float(np.dot((0.299, 0.587, 0.114), rgb))),
    ('Average: the mean of R, G and B', lambda rgb: float(np.mean(rgb))),
    ('Max', max),
    ('Min', min),
)


def _conversion(said: str, params: dict[str, JsonSent], grey: Callable[[Rgb], float]) -> Grey:
    return Grey('Grayscale Conversion' + said, 'grayscaleconversion', params, 'input1', grey)


def _weighted(weights: Rgb) -> Grey:
    """Grayscale Conversion with `weights` set, taken as given: each colour's grey their sum of R, G and B so
    weighted."""
    said = ', weights (%s, 0), summing to %g: taken as given' % (', '.join('%g' % w for w in weights), sum(weights))
    return _conversion(said, {'channelsweights': [*weights, 0]}, lambda rgb: float(np.dot(weights, rgb)))


def _advanced(said: str, params: dict[str, JsonSent], grey: Callable[[Rgb], float]) -> Grey:
    return Grey('Grayscale Conversion Advanced' + said, 'grayscale_conversion_advanced', params, 'input', grey)


def expected_greys(weights: Rgb) -> list[Grey]:
    """The greys check_designer_greys measures: Grayscale Conversion at its default, against the palette's `weights`;
    the default's weights set, which give the mean of R, G and B; weights summing to 1, above 1 and below 1, each
    taken as given; and Grayscale Conversion Advanced at its default and with each of its types."""
    return [
        _conversion(" at its default: the palette's grey", {}, lambda rgb: float(np.dot(weights, rgb))),
        _conversion(
            ", the default's weights (0.33, 0.33, 0.33, 0) set: the mean of R, G and B",
            {'channelsweights': [0.33, 0.33, 0.33, 0]},
            lambda rgb: float(np.mean(rgb)),
        ),
        *[_weighted(w) for w in ((0.34, 0.33, 0.33), (0.5, 0.5, 0.5), (0.1, 0.1, 0.1))],
        _advanced(' at its default: Desaturation', {}, _desaturated),
        *[_advanced(', ' + said, {'grayscale_type': kind}, grey) for kind, (said, grey) in enumerate(_ADVANCED)],
    ]


# a Gradient Map key as set takes it: its position, its R, G, B and A
Key = tuple[float, Rgba]


class Palette(NamedTuple):
    """analyze_reference's result: the keys, the luminance at positions 0 and 1, its R, G and B weights, and the fit
    error."""

    keys: list[Key]
    low: float
    high: float
    weights: Rgb
    error: float


def _line(pattern: str, t: str) -> re.Match[str]:
    found = re.search(pattern, t, re.M)
    if found is None:
        raise AssertionError('no line %r in: %s' % (pattern, t.strip()[-300:]))
    return found


def palette(t: str) -> Palette:
    """analyze_reference's result `t`, read; AssertionError without one of its lines, which the run reports."""
    keys: list[Key] = [
        (float(position), (float(r), float(g), float(b), float(a)))
        for position, (r, g, b, a) in json.loads(_line(r'^gradientrgba: (.*)$', t).group(1))
    ]
    span = _line(r'^luminance ([\d.]+) to ([\d.]+) .* of ([\d.]+) R \+ ([\d.]+) G \+ ([\d.]+) B', t)
    low, high, r, g, b = (float(v) for v in span.groups())
    return Palette(keys, low, high, (r, g, b), float(_line(r'^fit error ([\d.]+):', t).group(1)))


def rgb_rmse(t: str) -> float | None:
    """compare_to_reference(aligned=True)'s result `t`: the RMS over R, G and B of its pixel-by-pixel RMSE, as
    analyze_reference gives its fit error; None without the three lines."""
    found = dict(re.findall(r'^\s+([RGB])\s+mean abs diff [\d.]+\s+RMSE ([\d.]+)', t, re.M))
    if sorted(found) != ['B', 'G', 'R']:
        return None
    return float(np.sqrt(np.mean([float(v) ** 2 for v in found.values()])))
