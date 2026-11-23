"""Runs inside Designer (run_designer_script), for params' "designer facts" check of a Gradient Map's keys and a Curve's
points (checks.py, check_gradient_and_curve_keys): their types, what a new node and a new key hold, what
setPropertyValue takes and what a value read keeps, what keys compute, and the keys after a save and a reload.

It builds its cells in a package of its own, reads them after one graph.compute(), prints one line per fact,
`label | what it measured`, and closes the package. The graph is 16 px at 32-bit float. A cell is a gradient or curve
node fed by a ramp: a Pixel Processor whose pixel i of each row reads i/15, so pixels 0, 5, 10 and 15 read 0, 1/3, 2/3
and 1. The grey ramp is grayscale; the colour ramp is (i/15, i/15, i/15, i/15). A cell's line gives its pixels 0, 3,
5, 7, 10, 12 and 15, each value with three decimals: a grey's value, or a colour's R/G/B/A."""

import ctypes
import os
import shutil
import struct
import tempfile
from collections.abc import Sequence
from typing import cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import ColorRGBA, float2, int2
from sd.api.sdgraph import SDGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackage import SDPackage
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdtexture import SDTexture
from sd.api.sdtype import SDType
from sd.api.sdtypearray import SDTypeArray
from sd.api.sdtypefloat import SDTypeFloat
from sd.api.sdtypestruct import SDTypeStruct
from sd.api.sdvalue import SDValue
from sd.api.sdvaluearray import SDValueArray
from sd.api.sdvaluebool import SDValueBool
from sd.api.sdvaluecolorrgba import SDValueColorRGBA
from sd.api.sdvalueenum import SDValueEnum
from sd.api.sdvaluefloat import SDValueFloat
from sd.api.sdvaluefloat2 import SDValueFloat2
from sd.api.sdvalueint import SDValueInt
from sd.api.sdvalueint2 import SDValueInt2
from sd.api.sdvaluestring import SDValueString
from sd.api.sdvaluestruct import SDValueStruct
from sd.api.sdvaluetexture import SDValueTexture

IN, OUT = SDPropertyCategory.Input, SDPropertyCategory.Output
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
PIXELS = (0, 3, 5, 7, 10, 12, 15)
CURVES = ('curveluminance', 'curvered', 'curvegreen', 'curveblue', 'curvealpha')
type Colour = tuple[float, float, float, float]
type Point = tuple[float, float]
type Cells = list[tuple[str, SDNode]]  # (its line's label, the node it reads), read after the compute
RED, GREEN, BLUE = (1.0, 0.0, 0.0, 1.0), (0.0, 1.0, 0.0, 1.0), (0.0, 0.0, 1.0, 1.0)
BOTH_SIDES = ('isLeftBroken', 'isRightBroken')  # a curve point's two sides broken


def prop(owner: SDNode | SDGraph, pid: str) -> SDProperty:
    return cast(SDProperty, owner.getPropertyFromId(pid, IN))


def struct_type(type_id: str) -> SDTypeStruct:
    return cast(SDTypeStruct, SDTypeStruct.sNew('sbs::compositing::' + type_id))


GRADIENT_KEY, CURVE_KEY = struct_type('gradient_key_rgba'), struct_type('curve_key')


def shown(value: SDValue | None) -> str:
    """A member's value: None, a bool, a number with four decimals, or a vector's or colour's components."""
    if value is None:
        return 'None'
    x = value.get()  # type: ignore[attr-defined]  # every concrete SDValue has get()
    for names in (('r', 'g', 'b', 'a'), ('x', 'y')):
        if hasattr(x, names[0]):
            return '(%s)' % ', '.join('%g' % round(getattr(x, n), 4) for n in names)
    return '%g' % round(x, 4) if isinstance(x, float) else str(x)


def members(t: SDType) -> str:
    """An array type: its id, then its item type's members, each with its type."""
    item = cast(SDTypeStruct, cast(SDTypeArray, t).getItemType())
    return '%s: %s' % (
        t.getId(),
        ', '.join('%s %s' % (m.getId(), cast(SDType, m.getType()).getId()) for m in item.getMembers()),
    )


def keys_of(n: SDNode, pid: str) -> str:
    """The keys `n`'s array `pid` holds, in their order, each its members' values; 'none' for none."""
    array = cast(SDValueArray, n.getPropertyValue(prop(n, pid)))
    return array_text(array)


def array_text(array: SDValueArray) -> str:
    keys = []
    for i in range(array.getSize()):
        key = cast(SDValueStruct, array.getItem(i))
        item = cast(SDTypeStruct, key.getType())
        keys.append(
            ' '.join('%s %s' % (m.getId(), shown(key.getPropertyValueFromId(m.getId()))) for m in item.getMembers())
        )
    return '; '.join(keys) or 'none'


def gradient_key(position: float, colour: Colour, midpoint: float | None = None) -> SDValueStruct:
    key = cast(SDValueStruct, SDValueStruct.sNew(GRADIENT_KEY))
    key.setPropertyValueFromId('value', SDValueColorRGBA.sNew(ColorRGBA(*colour)))
    key.setPropertyValueFromId('position', SDValueFloat.sNew(position))
    if midpoint is not None:
        key.setPropertyValueFromId('midpoint', SDValueFloat.sNew(midpoint))
    return key


def curve_key(point: Point, left: Point | None = None, right: Point | None = None, *flags: str) -> SDValueStruct:
    """A curve_key at `point`: its handles set only when given, and its bools `flags` (isLocked...) True."""
    key = cast(SDValueStruct, SDValueStruct.sNew(CURVE_KEY))
    key.setPropertyValueFromId('position', SDValueFloat2.sNew(float2(*point)))
    for member, handle in (('left', left), ('right', right)):
        if handle is not None:
            key.setPropertyValueFromId(member, SDValueFloat2.sNew(float2(*handle)))
    for flag in flags:
        key.setPropertyValueFromId(flag, SDValueBool.sNew(True))
    return key


def on_point(x: float, y: float) -> SDValueStruct:
    """A curve_key whose two handles are on its point."""
    return curve_key((x, y), (x, y), (x, y))


def array(item: SDType, keys: Sequence[SDValue]) -> SDValueArray:
    made = cast(SDValueArray, SDValueArray.sNew(item, 0))
    for key in keys:
        made.pushBack(key)
    return made


def link(source: SDNode, target: SDNode, input_id: str) -> None:
    source.newPropertyConnectionFromId('unique_filter_output', target, input_id)


def function_node(fg: SDGraph, definition: str, constant: SDValue | None = None) -> SDNode:
    n: SDNode = fg.newNode('sbs::function::' + definition)
    if constant is not None:
        n.setInputPropertyValueFromId('__constant__', constant)
    return n


def ramp(g: SDSBSCompGraph, colour: bool) -> SDNode:
    """A Pixel Processor whose pixel i of each row reads floor($pos.x * 16) / 15: grayscale, or (v, v, v, v)."""
    pp: SDNode = g.newNode('sbs::compositing::pixelprocessor')
    pp.setInputPropertyValueFromId('colorswitch', SDValueBool.sNew(colour))
    fg = cast(SDGraph, pp.newPropertyGraph(prop(pp, 'perpixel'), 'SDSBSFunctionGraph'))
    x = function_node(fg, 'swizzle1', SDValueInt.sNew(0))
    link(function_node(fg, 'get_float2', SDValueString.sNew('$pos')), x, 'vector')
    scaled = function_node(fg, 'mul')
    link(x, scaled, 'a')
    link(function_node(fg, 'const_float1', SDValueFloat.sNew(16)), scaled, 'b')
    floor = function_node(fg, 'floor')
    link(scaled, floor, 'a')
    value = function_node(fg, 'div')
    link(floor, value, 'a')
    link(function_node(fg, 'const_float1', SDValueFloat.sNew(15)), value, 'b')
    if colour:
        pair = function_node(fg, 'vector2')
        link(value, pair, 'componentsin')
        link(value, pair, 'componentslast')
        value = function_node(fg, 'vector4')
        link(pair, value, 'componentsin')
        link(pair, value, 'componentslast')
    fg.setOutputNode(value, True)
    return pp


def fed_node(g: SDSBSCompGraph, definition: str, source: SDNode, arrays: dict[str, SDValueArray]) -> SDNode:
    """A gradient or curve node fed by `source`, feeding an output node of its own, its arrays set from `arrays`."""
    n: SDNode = g.newNode('sbs::compositing::' + definition)
    link(source, n, 'input1')
    link(n, g.newNode('sbs::compositing::output'), 'inputNodeOutput')
    for pid, value in arrays.items():
        n.setPropertyValue(prop(n, pid), value)
    return n


def pixels(n: SDNode) -> str:
    """Pixels PIXELS of `n`'s first row, of a 32-bit float texture, three decimals each (-0 shown as 0)."""
    t = cast(SDTexture, cast(SDValueTexture, n.getPropertyValue(n.getProperties(OUT)[0])).get())
    kind = str(t.getPixelFormat()).split('.')[-1]
    if not kind.endswith('32F'):
        raise RuntimeError('pixels(): %s is not a 32-bit float format' % kind)
    channels = t.getBytesPerPixel() // 4
    row = struct.unpack(
        '<%df' % (t.getSize().x * channels), ctypes.string_at(t.getPixelBufferAddress(), t.getRowPitch())
    )
    values = ['/'.join('%.3f' % (round(v, 3) + 0.0) for v in row[i * channels : (i + 1) * channels]) for i in PIXELS]
    return '%s %s' % (kind, ' '.join(values))


def new_graph(package: SDPackage) -> SDSBSCompGraph:
    g = SDSBSCompGraph.sNew(package)
    g.setIdentifier('mcp_selftest_keys')
    for pid, value in (
        ('$outputsize', SDValueInt2.sNew(int2(4, 4))),
        ('$format', SDValueEnum.sFromValueId('sbs::compositing::format', 'hdr_high_precision')),
    ):
        g.setPropertyInheritanceMethod(prop(g, pid), SDPropertyInheritanceMethod.Absolute)  # then the value
        g.setPropertyValue(prop(g, pid), value)
    return g


def measure_types(g: SDSBSCompGraph) -> None:
    gradient: SDNode = g.newNode('sbs::compositing::gradient')
    curve: SDNode = g.newNode('sbs::compositing::curve')
    print('gradientrgba | %s' % members(cast(SDType, prop(gradient, 'gradientrgba').getType())))
    for pid in CURVES:
        print('%s | %s' % (pid, members(cast(SDType, prop(curve, pid).getType()))))
    own = (
        '%s %s %s'
        % (
            pid,
            cast(SDType, prop(gradient, pid).getType()).getId(),
            shown(gradient.getPropertyValue(prop(gradient, pid))),
        )
        for pid in ('interpmode', 'smoothness')
    )
    print(
        'a new gradient | gradientrgba %s, default %s | %s'
        % (keys_of(gradient, 'gradientrgba'), prop(gradient, 'gradientrgba').getDefaultValue(), ' | '.join(own))
    )
    print(
        'a new curve | %s'
        % ' | '.join(
            '%s %s, default %s' % (pid, keys_of(curve, pid), prop(curve, pid).getDefaultValue()) for pid in CURVES
        )
    )
    for item in (GRADIENT_KEY, CURVE_KEY):
        print(
            'a new %s | %s' % (item.getId(), array_text(array(item, [cast(SDValueStruct, SDValueStruct.sNew(item))])))
        )


def measure_values(g: SDSBSCompGraph) -> None:
    """What setPropertyValue takes, a curve point's flags included, and whether a value read, or set, follows the
    node."""
    n: SDNode = g.newNode('sbs::compositing::gradient')
    p = prop(n, 'gradientrgba')
    red, green, blue = RED, GREEN, BLUE
    n.setPropertyValue(p, array(GRADIENT_KEY, [gradient_key(1, blue, 0.5), gradient_key(0, red, 0.25)]))
    print('two keys set unsorted, read back | %s' % keys_of(n, 'gradientrgba'))
    read = cast(SDValueArray, n.getPropertyValue(p))
    n.setPropertyValue(p, array(GRADIENT_KEY, [gradient_key(0.5, green)]))
    print('a value read, after a set | %s' % array_text(read))
    n.setPropertyValue(p, read)
    print('that value set again | %s' % keys_of(n, 'gradientrgba'))
    cast(SDValueStruct, cast(SDValueArray, n.getPropertyValue(p)).getItem(0)).setPropertyValueFromId(
        'position', SDValueFloat.sNew(0.3)
    )
    print('a value read, changed | the node reads %s' % keys_of(n, 'gradientrgba'))
    made = array(GRADIENT_KEY, [gradient_key(0, red)])
    n.setPropertyValue(p, made)
    cast(SDValueStruct, made.getItem(0)).setPropertyValueFromId('position', SDValueFloat.sNew(0.3))
    made.pushBack(gradient_key(1, blue))
    print('the array set, changed after | the node reads %s' % keys_of(n, 'gradientrgba'))
    n.setPropertyValue(p, array(CURVE_KEY, [curve_key((0.5, 0.5))]))
    print('an array of curve_key set on gradientrgba | reads %s' % keys_of(n, 'gradientrgba'))
    n.setPropertyValue(p, array(SDTypeFloat.sNew(), [SDValueFloat.sNew(0.5)]))
    print('an array of float set on gradientrgba | reads %s' % keys_of(n, 'gradientrgba'))
    n.setPropertyValue(p, array(GRADIENT_KEY, [gradient_key(0, red)]))
    n.setPropertyValue(p, array(GRADIENT_KEY, []))
    print('an empty array set on a gradient with a key | reads %s' % keys_of(n, 'gradientrgba'))
    curve: SDNode = g.newNode('sbs::compositing::curve')
    flagged = [
        curve_key((0, 0), (0, 0), (0.5, 0), 'isLocked', 'isRightBroken'),
        curve_key((1, 1), (0.5, 1), (1, 1), 'isLeftBroken'),
    ]
    curve.setPropertyValue(prop(curve, 'curveluminance'), array(CURVE_KEY, flagged))
    print("a curve's flags set, read back | reads %s" % keys_of(curve, 'curveluminance'))


def gradient_cells(g: SDSBSCompGraph, grey: SDNode, colour: SDNode) -> Cells:
    """Gradient nodes fed by the grey ramp, or by the colour ramp where a cell says so."""
    red, green, blue = RED, GREEN, BLUE

    def cell(keys: list[SDValueStruct], source: SDNode = grey, **params: SDValue) -> SDNode:
        n = fed_node(g, 'gradient', source, {'gradientrgba': array(GRADIENT_KEY, keys)} if keys else {})
        for pid, value in params.items():
            n.setPropertyValue(prop(n, pid), value)
        return n

    two = [gradient_key(0, red), gradient_key(1, blue)]
    cells: Cells = [
        ('gradient, no keys', cell([])),
        ('gradient, one key, red at 0.5', cell([gradient_key(0.5, red)])),
        (
            'gradient, red at 0, green at 1/3, blue at 1, given blue, red, green',
            cell([gradient_key(1, blue), gradient_key(0, red), gradient_key(1 / 3, green)]),
        ),
        (
            'gradient, red then green at 0.4, blue at 1',
            cell([gradient_key(0.4, red), gradient_key(0.4, green), gradient_key(1, blue)]),
        ),
        (
            'gradient, green then red at 0.4, blue at 1',
            cell([gradient_key(0.4, green), gradient_key(0.4, red), gradient_key(1, blue)]),
        ),
        ('gradient, red at 0.2, blue at 0.8', cell([gradient_key(0.2, red), gradient_key(0.8, blue)])),
        ('gradient, red at 0, blue at 1', cell(two)),
    ]
    for midpoint in (0.25, 0.5, 1.0):
        cells.append(
            (
                'gradient, red at 0, blue at 1, midpoints %g' % midpoint,
                cell([gradient_key(0, red, midpoint), gradient_key(1, blue, midpoint)]),
            )
        )
    for mode, midpoint in ((1, 0.0), (1, 0.5), (3, 0.0)):
        cells.append(
            (
                'gradient, red at 0, blue at 1, interpmode %d, midpoints %g' % (mode, midpoint),
                cell(
                    [gradient_key(0, red, midpoint), gradient_key(1, blue, midpoint)],
                    interpmode=SDValueInt.sNew(mode),
                ),
            )
        )
    cells += [
        (
            'gradient, (2, -1, 0.5, 0.5) at 0, blue at 1',
            cell([gradient_key(0, (2.0, -1.0, 0.5, 0.5)), gradient_key(1, blue)]),
        ),
        ('gradient, red at -0.1, blue at 1.1', cell([gradient_key(-0.1, red), gradient_key(1.1, blue)])),
        ('gradient, red at 0, blue at 1.5', cell([gradient_key(0, red), gradient_key(1.5, blue)])),
        (
            'gradient, red at 0, white at 1, colorswitch off',
            cell([gradient_key(0, red), gradient_key(1, (1.0, 1.0, 1.0, 1.0))], colorswitch=SDValueBool.sNew(False)),
        ),
        ('gradient, red at 0, blue at 1, on the colour ramp', cell(two, colour)),
    ]
    return cells


def curve_cells(g: SDSBSCompGraph, grey: SDNode, colour: SDNode) -> Cells:
    """Curve nodes fed by the grey ramp, or by the colour ramp where a cell says so."""
    invert = [on_point(0, 1), on_point(1, 0)]

    def cell(arrays: dict[str, list[SDValueStruct]], source: SDNode = grey) -> SDNode:
        return fed_node(g, 'curve', source, {pid: array(CURVE_KEY, keys) for pid, keys in arrays.items()})

    return [
        ('curve, no keys', cell({})),
        (
            'curve, (0, 1) and (1, 0) from their points alone',
            cell({'curveluminance': [curve_key((0, 1)), curve_key((1, 0))]}),
        ),
        ('curve, (0, 1) and (1, 0), handles on their points', cell({'curveluminance': invert})),
        ('curve, (1, 0) and (0, 1), handles on their points', cell({'curveluminance': invert[::-1]})),
        *(
            (
                'curve, (0, 0) right (0.5, 0), (1, 1) left (0.5, 1)%s' % said,
                cell(
                    {
                        'curveluminance': [
                            curve_key((0, 0), (0, 0), (0.5, 0), *first),
                            curve_key((1, 1), (0.5, 1), (1, 1), *second),
                        ]
                    }
                ),
            )
            # each point's flags: its sides broken one by one. The first point's left faces no segment, its handle on its
            # point here; off its point below
            for said, first, second in (
                ('', (), ()),
                (', locked', ('isLocked',), ('isLocked',)),
                (', broken', BOTH_SIDES, BOTH_SIDES),
                (", the first point's right side broken", ('isRightBroken',), ()),
                (", the second point's left side broken", (), ('isLeftBroken',)),
                (', both sides of the first point broken', BOTH_SIDES, ()),
            )
        ),
        # what each broken side is measured against: its handle on its point, no flag set
        (
            'curve, (0, 0) right on its point, (1, 1) left (0.5, 1)',
            cell({'curveluminance': [on_point(0, 0), curve_key((1, 1), (0.5, 1), (1, 1))]}),
        ),
        (
            'curve, (0, 0) right (0.5, 0), (1, 1) left on its point',
            cell({'curveluminance': [curve_key((0, 0), (0, 0), (0.5, 0)), on_point(1, 1)]}),
        ),
        # the first point's left side, which faces no segment, its handle off its point: used, then broken
        *(
            (
                'curve, (0, 0) left (0.2, 0.3) right (0.5, 0), (1, 1) left (0.5, 1)%s' % said,
                cell(
                    {
                        'curveluminance': [
                            curve_key((0, 0), (0.2, 0.3), (0.5, 0), *flags),
                            curve_key((1, 1), (0.5, 1), (1, 1)),
                        ]
                    }
                ),
            )
            for said, flags in (('', ()), (', its left side broken', ('isLeftBroken',)))
        ),
        (
            'curve, (0, 0), (0.5, 1), (1, 0) on their points',
            cell({'curveluminance': [on_point(0, 0), on_point(0.5, 1), on_point(1, 0)]}),
        ),
        ('curve, (0.5, 0.25) alone, on its point', cell({'curveluminance': [on_point(0.5, 0.25)]})),
        (
            'curve, (0, 0), (0.5, 0) then (0.5, 1), (1, 1)',
            cell({'curveluminance': [on_point(0, 0), on_point(0.5, 0), on_point(0.5, 1), on_point(1, 1)]}),
        ),
        (
            'curve, (0, 0), (0.5, 1) then (0.5, 0), (1, 1)',
            cell({'curveluminance': [on_point(0, 0), on_point(0.5, 1), on_point(0.5, 0), on_point(1, 1)]}),
        ),
        ('curve, (0, -1) and (1, 2)', cell({'curveluminance': [on_point(0, -1), on_point(1, 2)]})),
        ('curve, (0.2, 0) and (0.8, 1)', cell({'curveluminance': [on_point(0.2, 0), on_point(0.8, 1)]})),
        ('curve, (-0.2, 0) and (1.2, 1)', cell({'curveluminance': [on_point(-0.2, 0), on_point(1.2, 1)]})),
        *(('curve, grey ramp, %s inverts' % pid, cell({pid: invert})) for pid in CURVES if pid != 'curveluminance'),
        *(('curve, colour ramp, %s inverts' % pid, cell({pid: invert}, colour)) for pid in CURVES),
        (
            'curve, colour ramp, curveluminance and curvered invert',
            cell({'curveluminance': invert, 'curvered': invert}, colour),
        ),
        # which runs first: curveluminance then curvered gives R (1 - x) / 2, the other order 1 - x / 2 (REVIEW.md
        # TST-781)
        (
            'curve, colour ramp, curveluminance inverts and curvered halves',
            cell({'curveluminance': invert, 'curvered': [on_point(0, 0), on_point(1, 0.5)]}, colour),
        ),
    ]


def measure_reloaded(g: SDSBSCompGraph, grey: SDNode) -> None:
    """A gradient's and a curve's keys, unsorted, before and after the package is saved, unloaded and loaded again."""
    gradient_keys = [gradient_key(1, BLUE, 0.5), gradient_key(0.4, GREEN), gradient_key(0.4, RED)]
    gradient = fed_node(g, 'gradient', grey, {'gradientrgba': array(GRADIENT_KEY, gradient_keys)})
    curve_keys = [on_point(1, 0), curve_key((0, 1), (0, 1), (0.3, 0.9))]
    curve = fed_node(g, 'curve', grey, {'curveluminance': array(CURVE_KEY, curve_keys)})
    # {node id: (its array, its keys before)}
    before = {
        n.getIdentifier(): (pid, keys_of(n, pid)) for n, pid in ((gradient, 'gradientrgba'), (curve, 'curveluminance'))
    }
    folder = tempfile.mkdtemp(prefix='mcp_selftest_keys_')
    try:
        path = os.path.join(folder, 'keys.sbs')
        pm.savePackageAs(g.getPackage(), path)
        pm.unloadUserPackage(g.getPackage())
        loaded = pm.loadUserPackage(path)
        try:
            [again] = [r for r in loaded.getChildrenResources(False) if isinstance(r, SDSBSCompGraph)]
            for nid, (pid, keys) in before.items():
                after = keys_of(cast(SDNode, again.getNodeFromId(nid)), pid)
                print(
                    '%s after a save and a reload | %s'
                    % (pid, 'as before' if after == keys != 'none' else 'before %s, after %s' % (keys, after))
                )
        finally:
            pm.unloadUserPackage(loaded)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


new_package = pm.newUserPackage()
uid = new_package.getUID()
try:  # its graph made inside: a failure making it still unloads the package (REVIEW.md TST-766)
    graph = new_graph(new_package)
    measure_types(graph)
    measure_values(graph)
    grey_ramp, colour_ramp = ramp(graph, False), ramp(graph, True)
    cells = gradient_cells(graph, grey_ramp, colour_ramp) + curve_cells(graph, grey_ramp, colour_ramp)
    graph.compute()
    for label, cell_node in cells:
        print('%s | %s' % (label, pixels(cell_node)))
    measure_reloaded(graph, grey_ramp)
finally:
    for package in pm.getUserPackages():  # by its UID, since measure_reloaded saves it and loads it again
        if package.getUID() == uid:
            pm.unloadUserPackage(package)
