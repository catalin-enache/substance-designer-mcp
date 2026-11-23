"""Runs inside Designer (run_designer_script), for facts' checks of a blend's opacity and of a blend of a grey image and
a colour one (checks.py). First, what an atomic blend, `blendingmode` copy, its `opacitymult` at its default, gives
with its `opacity` input fed each grey and colour image. Its `source` is white and its `destination` (0.2, 0.4, 0.6,
1), each a colour uniform; or, for grey sides, grey uniforms, white over 0.2. Every feed goes into a blend of each
kind of sides, in a graph of each format (8-bit, 16-bit and 32-bit float), each graph in a package of its own, unloaded
at the end, read after one graph.compute().
In the float graph, each blendingmode the blend's enum lists also blends (0.7, 0.5, 0.3, 1) over that destination four
times, as MODE_CASES says, and blends sides of two types: each source of TYPE_CASES over the destination of colour or
of grey sides, with each feed of TYPE_FEEDS in its opacity. ARGS: grey_png and rgb_png, two PNGs fed as bitmap nodes.

Prints, for each graph:
- the `opacitymult` of its first blend;
- in the float graph, the blendingmode ids;
- one line per blend of a feed, `label | blend <format> <pixel> | opacity <format> <pixel>`, the second half the image
  fed into its `opacity`, `opacity -` with nothing connected;
- one line per blend of a mode, `label | blend <format> <pixel>`.

Each pixel is pixel (0, 0), each value with two decimals."""

import array
import ctypes
from collections.abc import Callable
from functools import partial
from itertools import product
from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import ColorRGBA, int2
from sd.api.sdgraph import SDGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdresource import EmbedMethod
from sd.api.sdresourcebitmap import SDResourceBitmap
from sd.api.sdtexture import SDTexture
from sd.api.sdtypeenum import SDTypeEnum
from sd.api.sdvaluebool import SDValueBool
from sd.api.sdvaluecolorrgba import SDValueColorRGBA
from sd.api.sdvalueenum import SDValueEnum
from sd.api.sdvaluefloat import SDValueFloat
from sd.api.sdvalueint2 import SDValueInt2
from sd.api.sdvaluetexture import SDValueTexture


class Args(TypedDict):
    grey_png: str  # an 8-bit grey PNG (mode L)
    rgb_png: str  # an RGB PNG whose R, G and B are equal


ARGS: Args = globals()['ARGS']
IN, OUT = SDPropertyCategory.Input, SDPropertyCategory.Output
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
type Rgba = tuple[float, float, float, float]
type Feed = Callable[[SDGraph], SDNode | None]  # builds what feeds the opacity input, or nothing
# the ending of each graph's pixel format: the array code of one value, and what it is divided by
DECODED = {'8': ('B', 255), '16': ('H', 65535), '32F': ('f', 1)}
# the colour uniforms fed into a blend's opacity
COLOURS: tuple[Rgba, ...] = ((0.5, 0.5, 0.5, 1), (1, 1, 1, 1), (1, 1, 1, 0.5), (1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1))
WHITE: Rgba = (1, 1, 1, 1)
# the destinations: of colour sides, and of grey sides
DESTINATION: Rgba = (0.2, 0.4, 0.6, 1)
GREY_DESTINATION: Rgba = (0.2, 0.2, 0.2, 1)
MODE_SOURCE: Rgba = (0.7, 0.5, 0.3, 1)  # the source the blends of each mode share
FORMATS = (('8_bits_per_channel', '8-bit'), ('16_bits_per_channel', '16-bit'), ('hdr_high_precision', 'float'))
# the graph that blends in each blendingmode: in 32-bit float, a grey 0.5 and an opacitymult of 0.5 are the same value
MODES_GRAPH = 'float'


def prop(owner: SDNode | SDGraph, pid: str) -> SDProperty:
    return cast(SDProperty, owner.getPropertyFromId(pid, IN))


def absolute(g: SDSBSCompGraph, pid: str, value: SDValueInt2 | SDValueEnum) -> None:
    """The graph's `pid` made Absolute, then set: a new graph's follows its parent."""
    p = prop(g, pid)
    g.setPropertyInheritanceMethod(p, SDPropertyInheritanceMethod.Absolute)
    g.setPropertyValue(p, value)


def link(source: SDNode, target: SDNode, input_id: str) -> None:
    source.newPropertyConnectionFromId('unique_filter_output', target, input_id)


def to_output(g: SDGraph, n: SDNode) -> None:
    """`n` feeding an output node of its own: graph.compute() computes only what feeds one."""
    link(n, g.newNode('sbs::compositing::output'), 'inputNodeOutput')


def uniform(g: SDGraph, rgba: Rgba, colorswitch: bool) -> SDNode:
    n: SDNode = g.newNode('sbs::compositing::uniform')
    n.setInputPropertyValueFromId('colorswitch', SDValueBool.sNew(colorswitch))
    n.setInputPropertyValueFromId('outputcolor', SDValueColorRGBA.sNew(ColorRGBA(*rgba)))
    return n


def processor(g: SDGraph, colorswitch: bool) -> SDNode:
    """A Pixel Processor whose function is the float 0.5."""
    n: SDNode = g.newNode('sbs::compositing::pixelprocessor')
    n.setInputPropertyValueFromId('colorswitch', SDValueBool.sNew(colorswitch))
    fg = cast(SDGraph, n.newPropertyGraph(prop(n, 'perpixel'), 'SDSBSFunctionGraph'))
    half: SDNode = fg.newNode('sbs::function::const_float1')
    half.setInputPropertyValueFromId('__constant__', SDValueFloat.sNew(0.5))
    fg.setOutputNode(half, True)
    return n


def converted(g: SDGraph, of: Callable[[SDGraph], SDNode]) -> SDNode:
    """Grayscale Conversion, at its default, of the node `of` builds."""
    n: SDNode = g.newNode('sbs::compositing::grayscaleconversion')
    link(of(g), n, 'input1')
    return n


def bitmap(g: SDGraph, path: str) -> SDNode:
    """A bitmap node of the image file at `path`, linked. sd types the node as optional: it is there, an instance of
    the resource just made (designer_helpers/core.py, _new_instance)."""
    res = SDResourceBitmap.sNewFromFile(g.getPackage(), path, EmbedMethod.Linked)
    return cast(SDNode, g.newInstanceNode(res))


def listed(rgba: Rgba) -> str:
    return '(%s)' % ', '.join('%g' % v for v in rgba)


def pixel(n: SDNode) -> str:
    """The format of the texture `n` computed, then its pixel (0, 0)."""
    t = cast(SDTexture, cast(SDValueTexture, n.getPropertyValue(n.getProperties(OUT)[0])).get())
    fmt = str(t.getPixelFormat()).split('.')[-1]
    code, scale = next(decoded for end, decoded in DECODED.items() if fmt.endswith(end))
    values = array.array(code, ctypes.string_at(t.getPixelBufferAddress(), t.getBytesPerPixel()))
    return '%s %s' % (fmt, ' '.join('%.2f' % (v / scale) for v in values))


def blending_modes(n: SDNode) -> list[str]:
    """The ids of every blendingmode the blend `n`'s enum lists, in its order."""
    return [e.getId() for e in cast(SDTypeEnum, prop(n, 'blendingmode').getType()).getEnumerators()]


def blend(
    g: SDGraph,
    source: SDNode,
    destination: SDNode,
    feed: SDNode | None,
    mode: str = 'copy',
    multiplier: float | None = None,
) -> SDNode:
    """A blend in `mode` of `source` over `destination`, `feed` into its opacity, its opacitymult `multiplier` if given."""
    n: SDNode = g.newNode('sbs::compositing::blend')
    n.setInputPropertyValueFromId('blendingmode', SDValueEnum.sFromValueId('sbs::compositing::blendingmode', mode))
    if multiplier is not None:
        n.setInputPropertyValueFromId('opacitymult', SDValueFloat.sNew(multiplier))
    link(source, n, 'source')
    link(destination, n, 'destination')
    if feed is not None:
        link(feed, n, 'opacity')
    to_output(g, n)
    return n


FEEDS: dict[str, Feed] = {
    'nothing': lambda g: None,
    'a grey uniform 0.5': partial(uniform, rgba=(0.5, 0.5, 0.5, 1), colorswitch=False),
    **{'a colour uniform %s' % listed(rgba): partial(uniform, rgba=rgba, colorswitch=True) for rgba in COLOURS},
    "a Pixel Processor's float 0.5, colorswitch on": partial(processor, colorswitch=True),
    "a Pixel Processor's float 0.5, colorswitch off": partial(processor, colorswitch=False),
    'Grayscale Conversion of a colour uniform (0.2, 0.4, 0.6, 1)': partial(
        converted, of=partial(uniform, rgba=(0.2, 0.4, 0.6, 1), colorswitch=True)
    ),
    'a bitmap of an 8-bit grey PNG at 128': partial(bitmap, path=ARGS['grey_png']),
    'a bitmap of an RGB PNG at (128, 128, 128)': partial(bitmap, path=ARGS['rgb_png']),
    "Grayscale Conversion of a Pixel Processor's float 0.5, colorswitch on": partial(
        converted, of=partial(processor, colorswitch=True)
    ),
    'Grayscale Conversion of a bitmap of an RGB PNG at (128, 128, 128)': partial(
        converted, of=partial(bitmap, path=ARGS['rgb_png'])
    ),
}
# each blend of a mode: the feed of FEEDS into its opacity, and its opacitymult (None: the default)
MODE_CASES: tuple[tuple[str, float | None], ...] = (
    ('a grey uniform 0.5', None),
    ('a colour uniform (0.5, 0.5, 0.5, 1)', None),
    ('nothing', 0.5),
    ('nothing', 0),
)
# each blend of two types in a mode, by the name ending its label: its source, a uniform of that colour and colorswitch,
# and the sides whose destination it goes over
TYPE_CASES: dict[str, tuple[Rgba, bool, str]] = {
    'grey_over_colour': ((0.3, 0.3, 0.3, 1), False, 'colour'),
    'clear_over_colour': ((0, 0, 0, 0), True, 'colour'),
    'colour_over_colour': ((0.3, 0.3, 0.3, 1), True, 'colour'),
    'colour_over_grey': ((0.3, 0.3, 0.3, 1), True, 'grey'),
    'black_over_grey': ((0, 0, 0, 1), False, 'grey'),
    'grey_over_grey': ((0.3, 0.3, 0.3, 1), False, 'grey'),
}
TYPE_FEEDS = ('nothing', 'a grey uniform 0.5')  # the feeds of FEEDS into each blend of two types' opacity

for format_id, format_name in FORMATS:
    package = pm.newUserPackage()
    try:
        graph = SDSBSCompGraph.sNew(package)
        graph.setIdentifier('mcp_selftest_blend_opacity')
        absolute(graph, '$outputsize', SDValueInt2.sNew(int2(2, 2)))
        absolute(graph, '$format', SDValueEnum.sFromValueId('sbs::compositing::format', format_id))
        sides = {
            'colour': (uniform(graph, WHITE, True), uniform(graph, DESTINATION, True)),
            'grey': (uniform(graph, WHITE, False), uniform(graph, GREY_DESTINATION, False)),
        }
        built = []
        feeds: dict[str, SDNode | None] = {}
        for feed_label, made in FEEDS.items():
            feeds[feed_label] = feed = made(graph)
            if feed is not None:
                to_output(graph, feed)
            for side, (source, destination) in sides.items():
                label = '%s, %s sides, opacity %s' % (format_name, side, feed_label)
                built.append((label, blend(graph, source, destination, feed), feed))
        default = cast(SDValueFloat, built[0][1].getInputPropertyValueFromId('opacitymult')).get()
        print("%s, a blend's opacitymult | %g" % (format_name, default))
        mode_blends = []
        if format_name == MODES_GRAPH:
            modes = blending_modes(built[0][1])
            print('%s, blendingmode ids | %s' % (format_name, ', '.join(modes)))
            mode_source, (_, mode_destination) = uniform(graph, MODE_SOURCE, True), sides['colour']
            for mode, (feed_label, multiplier) in product(modes, MODE_CASES):
                opacitymult = '' if multiplier is None else ', opacitymult %g' % multiplier
                label = '%s, %s mode, opacity %s%s' % (format_name, mode, feed_label, opacitymult)
                n = blend(graph, mode_source, mode_destination, feeds[feed_label], mode, multiplier)
                mode_blends.append((label, n))
            for type_name, (rgba, colorswitch, side) in TYPE_CASES.items():
                type_source = uniform(graph, rgba, colorswitch)
                for mode, feed_label in product(modes, TYPE_FEEDS):
                    label = '%s, %s mode, opacity %s, %s' % (format_name, mode, feed_label, type_name)
                    mode_blends.append((label, blend(graph, type_source, sides[side][1], feeds[feed_label], mode)))
        graph.compute()
        for label, n, feed in built:
            print('%s | blend %s | opacity %s' % (label, pixel(n), '-' if feed is None else pixel(feed)))
        for label, n in mode_blends:
            print('%s | blend %s' % (label, pixel(n)))
    finally:
        pm.unloadUserPackage(package)
