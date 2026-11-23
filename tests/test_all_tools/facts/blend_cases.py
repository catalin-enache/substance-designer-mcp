"""What check_a_blend_opacity_fed_a_colour_image (checks.py) feeds and reads: the colours fed into a blend's opacity,
a grey PNG (mode L) and an RGB PNG whose R, G and B are equal, saved for it, the lines
facts/designer_scripts/blend_opacity.py is expected to print, and the lines of each blendingmode it compares. Also the
lines check_a_blend_of_a_grey_image_and_a_colour_one compares: each blendingmode's blends of two types. Both checks
read one run of that script (blend_lines)."""

import os
from typing import TypedDict

from PIL import Image as PILImage

from test_all_tools.common import Ctx, designer_script, said, text

Rgba = tuple[float, float, float, float]
# a feed's label: the opacity the blend takes from it, and the image it computes, one value for LUM, four for RGBA,
# none with nothing connected
Feeds = dict[str, tuple[float, tuple[()] | tuple[float] | Rgba]]

HALF: Rgba = (0.5, 0.5, 0.5, 1)  # what a Pixel Processor's float 0.5 computes with colorswitch on
# the colour uniforms fed into a blend's opacity (blend_opacity.py's COLOURS)
COLOURS: tuple[Rgba, ...] = (HALF, (1, 1, 1, 1), (1, 1, 1, 0.5), (1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1))
# blend_opacity.py's destinations, a white source over each: of colour sides, and of grey sides
DESTINATION: Rgba = (0.2, 0.4, 0.6, 1)
GREY_DESTINATION = 0.2
# each graph's name in the lines, and the ending of its pixel formats
DEPTHS = (('8-bit', '8'), ('16-bit', '16'), ('float', '32F'))
# the graph that blends in each blendingmode, and the ending of its pixel formats (blend_opacity.py's MODES_GRAPH, which
# says why)
MODES_GRAPH = 'float'
MODES_DEPTH = dict(DEPTHS)[MODES_GRAPH]
# every blendingmode of the atomic blend, by enum id, in its order (GUIDE.md, First sd pitfalls)
MODES = (
    'copy',
    'add',
    'substract',
    'multiply',
    'addsub',
    'max',
    'min',
    'switch',
    'divide',
    'overlay',
    'screen',
    'softlight',
)
# what each blend of two types has in its opacity (blend_opacity.py's TYPE_FEEDS)
TYPE_FEEDS = ('nothing', 'a grey uniform 0.5')


class ModeBlends(TypedDict):
    """A mode's four blends in MODES_GRAPH, each as blend_opacity.py printed it."""

    grey: str  # the opacity input fed a grey uniform 0.5
    colour: str  # the opacity input fed a colour uniform (0.5, 0.5, 0.5, 1)
    half: str  # nothing connected, opacitymult 0.5
    zero: str  # nothing connected, opacitymult 0


def by_mode(t: str, mode: str) -> ModeBlends:
    """What blend_opacity.py printed of `mode`'s four blends, each found by the end of its label (its MODE_CASES)."""

    def line(label: str) -> str:
        return said(t, '%s, %s mode, %s' % (MODES_GRAPH, mode, label))

    return ModeBlends(
        grey=line('opacity a grey uniform 0.5'),
        colour=line('opacity a colour uniform (0.5, 0.5, 0.5, 1)'),
        half=line('opacity nothing, opacitymult 0.5'),
        zero=line('opacity nothing, opacitymult 0'),
    )


class TypeBlends(TypedDict):
    """A mode's six blends of two types in MODES_GRAPH, one feed in their opacity, each as blend_opacity.py printed
    it."""

    grey_over_colour: str  # a grey source 0.3 over the colour destination
    clear_over_colour: str  # a colour source (0, 0, 0, 0) over it
    colour_over_colour: str  # a colour source (0.3, 0.3, 0.3, 1) over it
    colour_over_grey: str  # a colour source (0.3, 0.3, 0.3, 1) over the grey destination
    black_over_grey: str  # a grey source 0 over it
    grey_over_grey: str  # a grey source 0.3 over it


def by_types(t: str, mode: str, feed: str) -> TypeBlends:
    """What blend_opacity.py printed of `mode`'s six blends of two types with `feed` in their opacity, each found by
    the name ending its label, its key in TYPE_CASES."""

    def line(name: str) -> str:
        return said(t, '%s, %s mode, opacity %s, %s' % (MODES_GRAPH, mode, feed, name))

    return TypeBlends(
        grey_over_colour=line('grey_over_colour'),
        clear_over_colour=line('clear_over_colour'),
        colour_over_colour=line('colour_over_colour'),
        colour_over_grey=line('colour_over_grey'),
        black_over_grey=line('black_over_grey'),
        grey_over_grey=line('grey_over_grey'),
    )


# each category run's lines of blend_opacity.py, by its scratch folder (blend_lines)
_LINES: dict[str, str] = {}


async def blend_lines(ctx: Ctx) -> str:
    """What facts/designer_scripts/blend_opacity.py printed, run once per category run, as both blend checks read its
    lines."""
    c, scratch = ctx.c, ctx.scratch
    if scratch not in _LINES:
        _LINES[scratch] = text(await designer_script(c, 'facts/blend_opacity', **pngs(scratch)))
    return _LINES[scratch]


def pngs(folder: str) -> dict[str, str]:
    """blend_opacity.py's ARGS: an 8-bit grey PNG (mode L) at 128, and an RGB PNG at (128, 128, 128), 4 px each, saved
    in `folder`."""
    paths = {
        'grey_png': os.path.join(folder, 'selftest_grey_l.png'),
        'rgb_png': os.path.join(folder, 'selftest_grey_rgb.png'),
    }
    PILImage.new('L', (4, 4), 128).save(paths['grey_png'])
    PILImage.new('RGB', (4, 4), (128, 128, 128)).save(paths['rgb_png'])
    return paths


def listed(values: Rgba) -> str:
    """A colour as blend_opacity.py's labels give it, such as (1, 0, 0, 1)."""
    return '(%s)' % ', '.join('%g' % v for v in values)


def image(depth: str, *values: float) -> str:
    """A texture as blend_opacity.py prints it: LUM<depth> with one value, RGBA<depth> with four, two decimals each."""
    return '%s%s %s' % ('LUM' if len(values) == 1 else 'RGBA', depth, ' '.join('%.2f' % v for v in values))


def over(destination: float, opacity: float) -> float:
    """A channel of the blend, copy: white over `destination` at `opacity`."""
    return destination + (1 - destination) * opacity


def expected_lines(feeds: Feeds) -> dict[str, str]:
    """blend_opacity.py's lines, {label: what it measured}: in each graph of DEPTHS, a blend's opacitymult, 1 by
    default, then each feed of `feeds` into a blend with colour sides and one with grey sides."""
    lines = {}
    for name, depth in DEPTHS:
        lines["%s, a blend's opacitymult" % name] = '1'
        for label, (opacity, fed) in feeds.items():
            fed_image = image(depth, *fed) if fed else '-'
            for side, blended in (
                ('colour', image(depth, *(over(d, opacity) for d in DESTINATION[:3]), 1)),
                ('grey', image(depth, over(GREY_DESTINATION, opacity))),
            ):
                lines['%s, %s sides, opacity %s' % (name, side, label)] = 'blend %s | opacity %s' % (blended, fed_image)
    return lines
