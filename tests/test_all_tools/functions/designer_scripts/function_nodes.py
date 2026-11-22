"""Runs inside Designer (run_designer_script), for functions' "designer facts" checks (checks.py): what function
nodes, and the processors that hold them, do. ARGS: part, the facts it measures:

- `types`: the types inputs and outputs list (getTypes()) before and after connections, and what a connection of the
  wrong type does;
- `constants`: the value class each const_* node takes, what a swizzle's index means, and what vector3 and vector4
  make of each size of component;
- `processors`: a fresh Pixel and Value Processor's function, the types perpixel takes, what each type of output
  computes, and a Value Processor's output type;
- `replacements`: three ways of replacing a Pixel Processor's function, and what each keeps;
- `size`: the size a Pixel Processor computes at, by its $outputsize inheritance;
- `dollar`: what a function on a node's $outputsize and $format computes, by their inheritance;
- `atan2`: what atan2 makes of its one float2;
- `variables`: what the `$` variables read, each with the get_* node ARGS['getters'] names: in a Pixel Processor's
  function, then $pos and $size in a Value Processor's and in a parameter's;
- `computed`: what the nodes the compiler builds compute, each of asymmetric constants, and rand at every pixel;
- `values`: a node's input values (`#name`): how newProperty makes one, what connects into it, what get_* nodes read
  of it, and whether the drive survives a save and a reload;
- `resources`: function graphs stored in the package: how one is made and given its inputs, what decides its output's
  type, what an instance node of one shows and computes, and what replacing its nodes, inputs and output does to an
  instance calling it;
- `sampling`: what samplecol and samplelum read: their modes, where pos reads, each index, in a function graph a Pixel
  Processor calls and in a Value Processor;
- `image_inputs`: a Pixel or Value Processor's input images, input:1 and after: what lists them, and what connects;
- `editor`: what openResourceInEditor opens of a function graph of the package, of a Pixel Processor's perpixel and of
  a parameter's function: the graph the editor has current then, and the title of its graph panel.

The part builds its cells in a package of its own, reads them after one graph.compute() (about 0.9 s however small
the graph: GUIDE.md, sd API), prints one line per fact, and closes the package. A cell is a node read after the
compute, most often a Pixel Processor whose function makes what its line says. A cell's pixel (0, 0) is read with two
decimals."""

import ctypes
import math
import os
import shutil
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import NotRequired, TypedDict, cast

import sd
from PySide6.QtWidgets import QApplication, QDockWidget
from sd.api.apiexception import APIException
from sd.api.qtforpythonuimgrwrapper import QtForPythonUIMgrWrapper
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sbs.sdsbscompnode import SDSBSCompNode
from sd.api.sbs.sdsbsfunctiongraph import SDSBSFunctionGraph
from sd.api.sdbasetypes import ColorRGBA, float2, float3, float4, int2, int3, int4
from sd.api.sddefinition import SDDefinition
from sd.api.sdgraph import SDGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackage import SDPackage
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdresource import SDResource
from sd.api.sdtexture import SDTexture
from sd.api.sdtype import SDType
from sd.api.sdtypebool import SDTypeBool
from sd.api.sdtypefloat import SDTypeFloat
from sd.api.sdtypefloat2 import SDTypeFloat2
from sd.api.sdtypefloat3 import SDTypeFloat3
from sd.api.sdtypefloat4 import SDTypeFloat4
from sd.api.sdtypeint import SDTypeInt
from sd.api.sdtypeint2 import SDTypeInt2
from sd.api.sdtypeint3 import SDTypeInt3
from sd.api.sdtypeint4 import SDTypeInt4
from sd.api.sdtypestring import SDTypeString
from sd.api.sduimgr import SDUIMgr
from sd.api.sdvalue import SDValue
from sd.api.sdvaluebool import SDValueBool
from sd.api.sdvaluecolorrgba import SDValueColorRGBA
from sd.api.sdvaluefloat import SDValueFloat
from sd.api.sdvaluefloat2 import SDValueFloat2
from sd.api.sdvaluefloat3 import SDValueFloat3
from sd.api.sdvaluefloat4 import SDValueFloat4
from sd.api.sdvalueint import SDValueInt
from sd.api.sdvalueint2 import SDValueInt2
from sd.api.sdvalueint3 import SDValueInt3
from sd.api.sdvalueint4 import SDValueInt4
from sd.api.sdvaluestring import SDValueString
from sd.api.sdvaluetexture import SDValueTexture


class Args(TypedDict):
    part: str
    # `variables`, `resources` and `sampling`: the get_* definition reading each variable
    getters: NotRequired[dict[str, str]]
    symbols: NotRequired[dict[str, str]]  # `computed`: the operator of each comparison's definition


ARGS: Args = globals()['ARGS']
IN, OUT = SDPropertyCategory.Input, SDPropertyCategory.Output
Method = SDPropertyInheritanceMethod
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
type Cells = list[tuple[str, SDNode]]  # (what its line says, the node it reads), read after the compute
# the values a const_* node takes on __constant__
type Value = (
    SDValueBool
    | SDValueFloat
    | SDValueFloat2
    | SDValueFloat3
    | SDValueFloat4
    | SDValueInt
    | SDValueInt2
    | SDValueInt3
    | SDValueInt4
    | SDValueString
)


def prop(owner: SDNode | SDGraph, pid: str, category: SDPropertyCategory = IN) -> SDProperty:
    return cast(SDProperty, owner.getPropertyFromId(pid, category))


def types_of(p: SDProperty) -> str:
    return ','.join(t.getId() for t in p.getTypes())


def types(n: SDNode, pid: str, category: SDPropertyCategory = IN) -> str:
    return types_of(prop(n, pid, category))


def output_types(n: SDNode) -> str:
    return types(n, 'unique_filter_output', OUT)


def operands(n: SDNode) -> str:
    """The types of a two-input operator's inputs and output."""
    return 'a %s | b %s | out %s' % (types(n, 'a'), types(n, 'b'), output_types(n))


def new_graph(size_log2: int) -> tuple[SDPackage, SDSBSCompGraph]:
    """A package of its own, with a graph of 2^size_log2 px (Absolute: a new graph's size follows its parent)."""
    pkg = pm.newUserPackage()
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_function_nodes')
    sized(g, Method.Absolute, size_log2)
    return pkg, g


def to_output(g: SDGraph, n: SDNode) -> None:
    """`n` feeding an output node of its own: graph.compute() computes only what feeds one."""
    link(n, g.newNode('sbs::compositing::output'), 'inputNodeOutput')


def sized(owner: SDSBSCompGraph | SDSBSCompNode, method: SDPropertyInheritanceMethod, size_log2: int) -> None:
    """`owner`'s $outputsize inheritance, then its value: changing the inheritance doesn't keep the value."""
    p = prop(owner, '$outputsize')
    owner.setPropertyInheritanceMethod(p, method)
    owner.setPropertyValue(p, SDValueInt2.sNew(int2(size_log2, size_log2)))


def function_graph(n: SDNode, pid: str) -> SDGraph:
    """The function graph newPropertyGraph makes on `n`'s parameter `pid`."""
    return cast(SDGraph, n.newPropertyGraph(prop(n, pid), 'SDSBSFunctionGraph'))


def cell(g: SDGraph, colorswitch: bool = True) -> tuple[SDSBSCompNode, SDGraph]:
    """A Pixel Processor feeding an output node, and the empty function graph made on its perpixel."""
    pp = cast(SDSBSCompNode, g.newNode('sbs::compositing::pixelprocessor'))
    pp.setInputPropertyValueFromId('colorswitch', SDValueBool.sNew(colorswitch))
    to_output(g, pp)
    return pp, function_graph(pp, 'perpixel')


def node(fg: SDGraph, definition: str, constant: SDValue | None = None) -> SDNode:
    """A new sbs::function node, its __constant__ set if given."""
    n: SDNode = fg.newNode('sbs::function::' + definition)
    if constant is not None:
        n.setInputPropertyValueFromId('__constant__', constant)
    return n


def link(source: SDNode, target: SDNode, input_id: str) -> None:
    source.newPropertyConnectionFromId('unique_filter_output', target, input_id)


def raised(e: BaseException) -> str:
    return 'raised %s %s' % (type(e).__name__, e)


def connects(source: SDNode, target: SDNode, input_id: str) -> str:
    """What connecting `source` to `target`'s `input_id` did: what it raised, or the connections read back on that
    input (a connection call can also return None without raising)."""
    try:
        link(source, target, input_id)
    except (Exception, APIException) as e:
        return raised(e)
    n = len(target.getPropertyConnections(prop(target, input_id)))
    return 'raised nothing, %d connection%s' % (n, '' if n == 1 else 's')


def joined(fg: SDGraph, vector: str, first: SDNode, last: SDNode) -> SDNode:
    """A vector2..4 node (`vector`) of `first`, then `last`."""
    v = node(fg, vector)
    link(first, v, 'componentsin')
    link(last, v, 'componentslast')
    return v


def fed(fg: SDGraph, definition: str, /, **inputs: SDNode) -> SDNode:
    """A node of `definition` fed on each of `inputs` ({input id: node})."""
    n = node(fg, definition)
    for input_id, source in inputs.items():
        link(source, n, input_id)
    return n


def binary(fg: SDGraph, definition: str, a: SDNode, b: SDNode) -> SDNode:
    """A node of `definition` (add, mul, div...) of `a` and `b`."""
    return fed(fg, definition, a=a, b=b)


def as_floats(fg: SDGraph, ints: SDNode, n: int) -> SDNode:
    """An int to int4 node cast to floats (tofloat to tofloat4)."""
    return fed(fg, 'tofloat' if n == 1 else 'tofloat%d' % n, value=ints)


def texture(n: SDNode) -> SDTexture:
    return cast(SDTexture, cast(SDValueTexture, n.getPropertyValue(n.getProperties(OUT)[0])).get())


def pixel(n: SDNode, x: int = 0, y: int = 0) -> str:
    """The values of pixel (x, y), each with two decimals, of an 8-bit texture, as these cells compute."""
    t = texture(n)
    at = t.getPixelBufferAddress() + y * t.getRowPitch() + x * t.getBytesPerPixel()
    return ' '.join('%.2f' % (b / 255) for b in ctypes.string_at(at, t.getBytesPerPixel()))


def greys(n: SDNode) -> list[float]:
    """The first value of every pixel, row by row, of an 8-bit texture `n` computed, as these cells compute."""
    t = texture(n)
    extent, step = t.getSize(), t.getBytesPerPixel()
    rows = [ctypes.string_at(t.getPixelBufferAddress() + y * t.getRowPitch(), extent.x * step) for y in range(extent.y)]
    return [row[x * step] / 255 for row in rows for x in range(extent.x)]


def pixel_format(n: SDNode) -> str:
    """The pixel format of the texture `n` computed, such as RGBA8."""
    return str(texture(n).getPixelFormat()).split('.')[-1]


def format_and_pixel(n: SDNode) -> str:
    return '%s %s' % (pixel_format(n), pixel(n))


def size(n: SDNode) -> str:
    return '%d px' % texture(n).getSize().x


def computed(g: SDSBSCompGraph, cells: Cells, read: Callable[[SDNode], str] = pixel) -> None:
    g.compute()
    for label, n in cells:
        print('%s | %s' % (label, read(n)))


def constant(fg: SDGraph, *xs: float) -> SDNode:
    """A const_float1..4 node of these components."""
    value: SDValue
    if len(xs) == 1:
        value = SDValueFloat.sNew(xs[0])
    elif len(xs) == 2:
        value = SDValueFloat2.sNew(float2(*xs))
    elif len(xs) == 3:
        value = SDValueFloat3.sNew(float3(*xs))
    else:
        value = SDValueFloat4.sNew(float4(*xs))
    return node(fg, 'const_float%d' % len(xs), value)


def listed(xs: tuple[float, ...]) -> str:
    return '(%s)' % ', '.join('%g' % x for x in xs)


def pair(v: int2) -> str:
    return '%d,%d' % (v.x, v.y)


def measure_types(g: SDSBSCompGraph) -> None:
    _, scratch = cell(g)
    add = node(scratch, 'add')
    first = cast(SDType, prop(add, 'unique_filter_output', OUT).getType()).getId()
    print('add, nothing connected | %s | getType %s' % (operands(add), first))
    link(node(scratch, 'const_float2'), add, 'a')
    print('add, a float2 connected | %s' % operands(add))
    link(node(scratch, 'const_float2'), add, 'b')
    print('add, two float2 connected | %s' % operands(add))
    into_b = node(scratch, 'add')
    link(node(scratch, 'const_float2'), into_b, 'b')
    print('add, a float2 into b first | %s' % operands(into_b))
    for made, other in (('float2', 'float1'), ('float1', 'float2')):
        narrowed = node(scratch, 'add')
        link(node(scratch, 'const_' + made), narrowed, 'a')
        said = connects(node(scratch, 'const_' + other), narrowed, 'b')
        print('add, a %s then a %s connected | %s | %s' % (made, other, said, operands(narrowed)))
    sample = node(scratch, 'samplecol')
    said = connects(node(scratch, 'const_float1'), sample, 'pos')
    print('samplecol, a float1 into pos | %s | pos %s' % (said, types(sample, 'pos')))
    print('gt | %s' % operands(node(scratch, 'gt')))
    choice = node(scratch, 'ifelse')
    print('ifelse, nothing connected | out %s' % output_types(choice))
    link(node(scratch, 'const_float3'), choice, 'ifpath')
    print('ifelse, a float3 ifpath | elsepath %s | out %s' % (types(choice, 'elsepath'), output_types(choice)))
    dot = node(scratch, 'dot')
    link(node(scratch, 'const_float2'), dot, 'a')
    print('dot, a float2 connected | %s' % operands(dot))
    scaled = node(scratch, 'mulscalar')
    link(node(scratch, 'const_float3'), scaled, 'a')
    print(
        'mulscalar, a float3 connected | a %s | scalar %s | out %s'
        % (types(scaled, 'a'), types(scaled, 'scalar'), output_types(scaled))
    )
    # what an add of a float2 and a float computes, beside an add of two float2
    cells: Cells = []
    for xs in ((0.1,), (0.1, 0.1)):
        pp, fg = cell(g)
        added = binary(fg, 'add', constant(fg, 0.2, 0.4), constant(fg, *xs))
        fg.setOutputNode(joined(fg, 'vector4', added, constant(fg, 0, 1)), True)
        cells.append(('add of float2 (0.2, 0.4) and float%d %s, computed' % (len(xs), listed(xs)), pp))
    computed(g, cells)


def measure_constants(g: SDSBSCompGraph) -> None:
    _, scratch = cell(g)
    values: dict[str, Value] = {
        'bool': SDValueBool.sNew(True),
        'float1': SDValueFloat.sNew(0.5),
        'float2': SDValueFloat2.sNew(float2(0.5, 0.25)),
        'float3': SDValueFloat3.sNew(float3(0.5, 0.25, 1)),
        'float4': SDValueFloat4.sNew(float4(0.5, 0.25, 1, 2)),
        'int1': SDValueInt.sNew(3),
        'int2': SDValueInt2.sNew(int2(3, 4)),
        'int3': SDValueInt3.sNew(int3(3, 4, 5)),
        'int4': SDValueInt4.sNew(int4(3, 4, 5, 6)),
        'string': SDValueString.sNew('x'),
    }
    classes = []
    for kind, value in values.items():
        k = node(scratch, 'const_' + kind)
        default = cast(SDValue, k.getInputPropertyValueFromId('__constant__'))
        k.setInputPropertyValueFromId('__constant__', value)
        back = cast(Value, k.getInputPropertyValueFromId('__constant__'))
        same = type(back) is type(value) and str(back.get()) == str(value.get())
        classes.append('%s %s%s' % (kind, type(default).__name__, '' if same else ' (not read back)'))
    print('const_* __constant__ | ' + ' | '.join(classes))
    for kind, other in (('float2', SDValueFloat.sNew(0.5)), ('float1', SDValueInt.sNew(1))):
        k = node(scratch, 'const_' + kind)
        try:
            k.setInputPropertyValueFromId('__constant__', other)
            said = 'accepted, reads %s' % type(k.getInputPropertyValueFromId('__constant__')).__name__
        except (Exception, APIException) as e:
            said = raised(e)
        print('const_%s given an %s | %s' % (kind, type(other).__name__, said))
    cells: Cells = []
    for index in range(4):
        pp, fg = cell(g, colorswitch=False)
        swizzle = node(fg, 'swizzle1', SDValueInt.sNew(index))
        link(constant(fg, 0.1, 0.2, 0.3, 0.4), swizzle, 'vector')
        fg.setOutputNode(swizzle, True)
        cells.append(('swizzle1 %d of (0.1, 0.2, 0.3, 0.4)' % index, pp))
    # each read as a float4: what the swizzle gives, then `then` if it gives fewer components
    swizzles: list[tuple[str, SDValue, tuple[float, ...], str]] = [
        ('swizzle2', SDValueInt2.sNew(int2(2, 0)), (0.5, 1), 'swizzle2 (2, 0) of (0.1, 0.2, 0.3, 0.4), then (0.5, 1)'),
        ('swizzle3', SDValueInt3.sNew(int3(2, 0, 1)), (1,), 'swizzle3 (2, 0, 1) of (0.1, 0.2, 0.3, 0.4), then 1'),
        ('swizzle4', SDValueInt4.sNew(int4(3, 2, 1, 0)), (), 'swizzle4 (3, 2, 1, 0) of (0.1, 0.2, 0.3, 0.4)'),
    ]
    for definition, indices, then, label in swizzles:
        pp, fg = cell(g)
        swizzle = node(fg, definition, indices)
        link(constant(fg, 0.1, 0.2, 0.3, 0.4), swizzle, 'vector')
        fg.setOutputNode(joined(fg, 'vector4', swizzle, constant(fg, *then)) if then else swizzle, True)
        cells.append((label, pp))
    # componentsin counts from 0.1, componentslast goes on from there; a vector3 shows with a last 1
    for vector, first, last in (
        ('vector4', 3, 1),
        ('vector4', 1, 3),
        ('vector4', 2, 2),
        ('vector4', 1, 1),
        ('vector4', 2, 3),
        ('vector3', 1, 2),
        ('vector3', 2, 1),
        ('vector3', 1, 1),
        ('vector3', 2, 2),
    ):
        pp, fg = cell(g)
        v = node(fg, vector)
        connected = [
            connects(constant(fg, *[0.1 * (i + 1) for i in range(first)]), v, 'componentsin'),
            connects(constant(fg, *[0.1 * (first + i + 1) for i in range(last)]), v, 'componentslast'),
        ]
        fg.setOutputNode(v if vector == 'vector4' else joined(fg, 'vector4', v, constant(fg, 1)), True)
        cells.append(('%s of %d and %d components | %s' % (vector, first, last, '; '.join(connected)), pp))
    computed(g, cells)


def measure_processors(g: SDSBSCompGraph) -> None:
    for definition, pid in (('pixelprocessor', 'perpixel'), ('valueprocessor', 'function')):
        fresh: SDNode = g.newNode('sbs::compositing::' + definition)
        switch = fresh.getPropertyFromId('colorswitch', IN)  # a Pixel Processor's only
        print(
            'a new %s | %s graph %s | resource %s%s'
            % (
                definition,
                pid,
                fresh.getPropertyGraph(prop(fresh, pid)),
                fresh.getReferencedResource(),
                '' if switch is None else ' | colorswitch %s' % cast(SDValueBool, fresh.getPropertyValue(switch)).get(),
            )
        )
    pp, fg = cell(g)
    takes = []
    for state in ('', 'a float output node, '):
        if state:
            fg.setOutputNode(constant(fg, 0.5), True)
        for colorswitch in (True, False):
            pp.setInputPropertyValueFromId('colorswitch', SDValueBool.sNew(colorswitch))
            takes.append('%scolorswitch %s %s' % (state, colorswitch, types(pp, 'perpixel')))
    print('perpixel takes | ' + ' | '.join(takes))
    vp: SDNode = g.newNode('sbs::compositing::valueprocessor')
    fn = function_graph(vp, 'function')  # no output node yet: value_processor() would set one
    outputs = ['no output node %s' % output_types(vp)]
    for kind in ('float2', 'bool', 'int3', 'float4'):
        fn.setOutputNode(node(fn, 'const_' + kind), True)
        outputs.append('%s %s' % (kind, output_types(vp)))
    print("a Value Processor's output | %s | function takes %s" % (' | '.join(outputs), types(vp, 'function')))
    cells: Cells = []
    cases: list[tuple[bool, tuple[float, ...]]] = [
        *((on, xs) for on in (True, False) for xs in ((0.5,), (0.2, 0.4, 0.6, 0.8), (0.2, 0.4), (0.2, 0.4, 0.6))),
        *((False, xs) for xs in ((0.6, 0, 0, 1), (0, 0.6, 0, 1), (0, 0, 0.6, 1), (0, 0, 0, 0.6))),
    ]
    for colorswitch, xs in cases:
        pp, fg = cell(g, colorswitch)
        fg.setOutputNode(constant(fg, *xs), True)
        cells.append(('colorswitch %s, perpixel float%d %s' % (colorswitch, len(xs), listed(xs)), pp))
    # 1 and True: what a conversion to float would make white
    others: list[tuple[str, SDValue, str]] = [
        ('const_int1', SDValueInt.sNew(1), 'int1 1'),
        ('const_int2', SDValueInt2.sNew(int2(1, 1)), 'int2 (1, 1)'),
        ('const_int3', SDValueInt3.sNew(int3(1, 1, 1)), 'int3 (1, 1, 1)'),
        ('const_int4', SDValueInt4.sNew(int4(1, 1, 1, 1)), 'int4 (1, 1, 1, 1)'),
        ('const_bool', SDValueBool.sNew(True), 'bool True'),
    ]
    for colorswitch in (True, False):
        for definition, value, label in others:
            pp, fg = cell(g, colorswitch)
            fg.setOutputNode(node(fg, definition, value), True)
            cells.append(('colorswitch %s, perpixel %s' % (colorswitch, label), pp))
    computed(g, cells, format_and_pixel)


NEW = (0.8, 0.6, 0.4, 1)  # the replacing function's constant; the old one is (0.2, 0.4, 0.6, 1)


def function_of(n: SDNode, pid: str = 'perpixel') -> SDGraph:
    """The function graph `n`'s parameter `pid` has."""
    return cast(SDGraph, n.getPropertyGraph(prop(n, pid)))


def replaced_in_place(pp: SDSBSCompNode) -> None:
    """New nodes built beside the old ones, the output node moved to them, then the old nodes deleted."""
    fg = function_of(pp)
    old = list(fg.getNodes())
    fg.setOutputNode(constant(fg, *NEW), True)
    for n in old:
        fg.deleteNode(n)


def replaced_after_deleting(pp: SDSBSCompNode) -> None:
    """The old nodes deleted, then new ones built."""
    fg = function_of(pp)
    for n in list(fg.getNodes()):
        fg.deleteNode(n)
    fg.setOutputNode(constant(fg, *NEW), True)


def replaced_graph(pp: SDSBSCompNode) -> None:
    """deletePropertyGraph, then newPropertyGraph and new nodes."""
    perpixel = prop(pp, 'perpixel')
    pp.deletePropertyGraph(perpixel)
    fg = function_graph(pp, 'perpixel')
    fg.setOutputNode(constant(fg, *NEW), True)


def replacement_state(pp: SDSBSCompNode, source: SDNode) -> str:
    """What a replacement could lose: the connections, two other parameters, and the function (its node count, its
    output node's constant)."""
    fg = function_of(pp)
    size_prop = prop(pp, '$outputsize')
    ins = sources(pp, 'input')
    outs = [
        cast(SDDefinition, cast(SDNode, c.getInputPropertyNode()).getDefinition()).getId()
        for c in pp.getPropertyConnections(pp.getProperties(OUT)[0])
    ]
    outputs = [cast(SDValueFloat4, n.getInputPropertyValueFromId('__constant__')).get() for n in fg.getOutputNodes()]
    return 'input and output connected %s | $randomseed %s | $outputsize %s %s | %d nodes, output %s' % (
        ins == [source.getIdentifier()] and outs == ['sbs::compositing::output'],
        cast(SDValueInt, pp.getInputPropertyValueFromId('$randomseed')).get(),
        pp.getPropertyInheritanceMethod(size_prop).name,
        pair(cast(SDValueInt2, pp.getPropertyValue(size_prop)).get()),
        len(fg.getNodes()),
        ', '.join(listed((v.x, v.y, v.z, v.w)) for v in outputs),
    )


def measure_replacements(g: SDSBSCompGraph) -> None:
    cells: Cells = []
    ways: list[tuple[str, Callable[[SDSBSCompNode], None] | None]] = [
        ('untouched', None),
        ('built beside, output moved, old deleted', replaced_in_place),
        ('old deleted, then built', replaced_after_deleting),
        ('deletePropertyGraph, newPropertyGraph', replaced_graph),
    ]
    for label, way in ways:
        source: SDNode = g.newNode('sbs::compositing::uniform')
        pp, fg = cell(g)
        link(source, pp, 'input')
        pp.setInputPropertyValueFromId('$randomseed', SDValueInt.sNew(7))
        sized(pp, Method.Absolute, 3)
        fg.setOutputNode(constant(fg, 0.2, 0.4, 0.6, 1), True)
        if way is not None:
            way(pp)
        cells.append(('replaced: %s | %s' % (label, replacement_state(pp, source)), pp))
    computed(g, cells, lambda n: '%s %s' % (size(n), pixel(n)))


def measure_size(g: SDSBSCompGraph) -> None:
    source = cast(SDSBSCompNode, g.newNode('sbs::compositing::uniform'))
    sized(source, Method.Absolute, 3)
    levels: SDNode = g.newNode('sbs::compositing::levels')
    link(source, levels, 'input1')
    cells: Cells = [('the input, Absolute 3,3', source), ('a levels node on it', levels)]
    for n in (source, levels):
        to_output(g, n)
    settings: list[tuple[str, bool, SDPropertyInheritanceMethod | None, int]] = [
        ('its default', True, None, 0),
        ('its default, no input', False, None, 0),
        ('RelativeToInput 0,0', True, Method.RelativeToInput, 0),
        ('RelativeToInput 1,1', True, Method.RelativeToInput, 1),
        ('Absolute 4,4', True, Method.Absolute, 4),
    ]
    for label, connected, method, size_log2 in settings:
        pp, fg = cell(g)
        if method is None:
            p = prop(pp, '$outputsize')
            label += ' (%s %s)' % (
                pp.getPropertyInheritanceMethod(p).name,
                pair(cast(SDValueInt2, pp.getPropertyValue(p)).get()),
            )
        else:
            sized(pp, method, size_log2)
        if connected:
            link(source, pp, 'input')
        fg.setOutputNode(constant(fg, 0.5), True)
        cells.append(('a Pixel Processor on it, $outputsize %s' % label, pp))
    computed(g, cells, size)


def quarter_turns(n: SDNode) -> str:
    """A grey cell's angle a, computed as a / (4 pi) + 0.5, read back in units of pi/2 with one decimal (a byte is
    0.03 of them)."""
    turns = (ctypes.string_at(texture(n).getPixelBufferAddress(), 1)[0] / 255 - 0.5) * 8
    return '%.1f' % (round(turns, 1) + 0.0)  # + 0.0: no -0.0


def measure_atan2(g: SDSBSCompGraph) -> None:
    cells: Cells = []
    for xy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
        pp, fg = cell(g, colorswitch=False)
        angle = node(fg, 'atan2')
        link(constant(fg, *xy), angle, 'a')
        shifted = binary(fg, 'add', binary(fg, 'mul', angle, constant(fg, 1 / (4 * math.pi))), constant(fg, 0.5))
        fg.setOutputNode(shifted, True)
        cells.append(('atan2 of float2 %s, in units of pi/2' % listed(xy), pp))
    computed(g, cells, quarter_turns)


def get(fg: SDGraph, getter: str, name: str) -> SDNode:
    """A get_* node, `getter`, reading `name`: a variable or an input value."""
    return node(fg, getter, SDValueString.sNew(name))


def variable(fg: SDGraph, name: str) -> SDNode:
    """A get_* node reading the variable `name`, its definition the check's (ARGS['getters'])."""
    return get(fg, ARGS['getters'][name], name)


def measure_variables(g: SDSBSCompGraph) -> None:
    """Each variable in a cell of its own: a float2 as the colour's R and G, the int $tiling as a grey. Then $pos and
    $size in a Value Processor's function, as its output, and a component of each in a parameter's function, a blend's
    opacitymult, white over black."""
    shown: dict[str, SDNode] = {}
    for name, by in (('$pos', 1.0), ('$size', 16.0), ('$sizelog2', 4.0)):
        pp, fg = cell(g)
        scaled = binary(fg, 'div', variable(fg, name), constant(fg, by, by))
        fg.setOutputNode(joined(fg, 'vector4', scaled, constant(fg, 0, 1)), True)
        shown[name] = pp
    grey, fg = cell(g, colorswitch=False)
    fg.setOutputNode(binary(fg, 'div', as_floats(fg, variable(fg, '$tiling'), 1), constant(fg, 4.0)), True)
    processors: dict[str, SDNode] = {}
    for name in ('$pos', '$size'):
        vp: SDNode = g.newNode('sbs::compositing::valueprocessor')
        read_by(vp, 'function', ARGS['getters'][name], name)
        to_output(g, vp)
        processors[name] = vp
    blends: dict[str, SDNode] = {}
    for label, name, index, by in (
        ('$pos.x', '$pos', 0, 1.0),
        ('$pos.y', '$pos', 1, 1.0),
        ('$size.x over 16', '$size', 0, 16.0),
        ('$size.y over 16', '$size', 1, 16.0),
    ):
        blend = white_over_black(g)
        fn = function_graph(blend, 'opacitymult')
        component = node(fn, 'swizzle1', SDValueInt.sNew(index))
        link(variable(fn, name), component, 'vector')
        fn.setOutputNode(binary(fn, 'div', component, constant(fn, by)), True)
        blends[label] = blend
    g.compute()
    getters = ARGS['getters']
    for x, y in ((0, 0), (5, 2)):
        print('$pos read with %s, at pixel (%d, %d) | %s' % (getters['$pos'], x, y, pixel(shown['$pos'], x, y)))
    print('$size read with %s, over 16 | %s' % (getters['$size'], pixel(shown['$size'])))
    print('$sizelog2 read with %s, over 4 | %s' % (getters['$sizelog2'], pixel(shown['$sizelog2'])))
    print('$tiling read with %s, over 4 | %s' % (getters['$tiling'], pixel(grey)))
    for name, vp in processors.items():
        v = cast(SDValueFloat2, vp.getPropertyValue(prop(vp, 'unique_filter_output', OUT))).get()
        print("%s read with %s in a Value Processor's function | %.2f %.2f" % (name, getters[name], v.x, v.y))
    for label, blend in blends.items():
        print("%s in a blend's opacitymult, at pixel (5, 2) | %s" % (label, pixel(blend, 5, 2)))


def int_value(*xs: int) -> SDValue:
    """An SDValueInt to SDValueInt4 of these components."""
    if len(xs) == 1:
        return SDValueInt.sNew(xs[0])
    if len(xs) == 2:
        return SDValueInt2.sNew(int2(*xs))
    if len(xs) == 3:
        return SDValueInt3.sNew(int3(*xs))
    return SDValueInt4.sNew(int4(*xs))


def integers(fg: SDGraph, *xs: int) -> SDNode:
    """A const_int1..4 node of these components."""
    return node(fg, 'const_int%d' % len(xs), int_value(*xs))


def written(xs: tuple[int, ...]) -> str:
    """'2' for one component, '(1, 0)' for several."""
    return '%d' % xs[0] if len(xs) == 1 else listed(xs)


def truth(fg: SDGraph, x: bool) -> SDNode:
    return node(fg, 'const_bool', SDValueBool.sNew(x))


def word(x: bool) -> str:
    return 'true' if x else 'false'


def number(fg: SDGraph, condition: SDNode) -> SDNode:
    """A bool as 1 or 0, through an ifelse."""
    return fed(fg, 'ifelse', condition=condition, ifpath=constant(fg, 1.0), elsepath=constant(fg, 0.0))


def measure_computed(g: SDSBSCompGraph) -> None:
    """Each node of asymmetric constants in a cell of its own, its labels saying how each is read. The comparisons'
    operators are the compiler's (ARGS['symbols'])."""
    cells: Cells = []
    symbols = ARGS['symbols']

    def new(label: str, size: int = 1) -> SDGraph:
        """A cell's function graph: a grey cell, or a colour one for a float2 to float4."""
        pp, fg = cell(g, colorswitch=size > 1)
        cells.append((label, pp))
        return fg

    def show(fg: SDGraph, v: SDNode, size: int = 1) -> None:
        """`v` as the cell's output, a float2 or a float3 padded to a colour with (0, 1) or 1."""
        if 1 < size < 4:
            v = joined(fg, 'vector4', v, constant(fg, 0, 1) if size == 2 else constant(fg, 1))
        fg.setOutputNode(v, True)

    def over(fg: SDGraph, ints: SDNode, n: int, by: float) -> SDNode:
        """An int to int4 as floats, over `by`: what the labels' "over 4" or "over 10" reads."""
        return binary(fg, 'div', as_floats(fg, ints, n), constant(fg, *[by] * n))

    def shifted(fg: SDGraph, x: SDNode, by: float, then: float) -> SDNode:
        """(x + by) / then, as the labels say."""
        return binary(fg, 'div', binary(fg, 'add', x, constant(fg, by)), constant(fg, then))

    def whole(fg: SDGraph, ints: SDNode) -> SDNode:
        """An int as a float, plus 5, over 10: what the labels' "(x + 5) / 10" reads."""
        return shifted(fg, as_floats(fg, ints, 1), 5.0, 10.0)

    fg = new('vector2 of 0.1 and 0.2', 2)
    show(fg, joined(fg, 'vector2', constant(fg, 0.1), constant(fg, 0.2)), 2)
    # an int4's components all differ from 0, which a missing one computes: over 10, so that none reaches 1
    vectors: list[tuple[int, tuple[int, ...], tuple[int, ...], float]] = [
        (2, (1,), (2,), 4.0),
        (3, (1,), (2, 3), 4.0),
        (4, (1, 2), (3, 5), 10.0),
    ]
    for n, first, last, by in vectors:
        fg = new('ivector%d of %s and %s, over %g' % (n, written(first), written(last), by), n)
        show(fg, over(fg, joined(fg, 'ivector%d' % n, integers(fg, *first), integers(fg, *last)), n, by), n)
    swizzles: list[tuple[int, tuple[int, ...], tuple[int, ...], float]] = [
        (1, (2,), (1, 2, 3), 4.0),
        (2, (1, 0), (1, 2, 3), 4.0),
        (3, (2, 0, 1), (1, 2, 3), 4.0),
        (4, (3, 2, 1, 0), (1, 2, 3, 5), 10.0),
    ]
    for n, indices, xs, by in swizzles:
        fg = new('iswizzle%d %s of %s, over %g' % (n, written(indices), listed(xs), by), n)
        swizzle = node(fg, 'iswizzle%d' % n, int_value(*indices))
        link(integers(fg, *xs), swizzle, 'vector')
        show(fg, over(fg, swizzle, n, by), n)
    for definition, symbol, a, b in (('sub', '-', 0.7, 0.2), ('div', '/', 0.2, 0.8), ('pow', '**', 0.5, 2.0)):
        fg = new('%s %g %s %g' % (definition, a, symbol, b))
        show(fg, binary(fg, definition, constant(fg, a), constant(fg, b)))
    fg = new('mod 0.7 % 0.4')
    show(fg, binary(fg, 'mod', constant(fg, 0.7), constant(fg, 0.4)))
    fg = new('mod -0.3 % 1, then (x + 1) / 2')
    show(fg, shifted(fg, binary(fg, 'mod', constant(fg, -0.3), constant(fg, 1.0)), 1.0, 2.0))
    pairs: list[tuple[str, str, tuple[float, ...], tuple[float, ...]]] = [
        ('sub', ' - ', (0.7, 0.9), (0.2, 0.1)),
        ('div', ' / ', (0.2, 0.3), (0.8, 0.5)),
        ('mod', ' % ', (0.7, 0.9), (0.4, 0.5)),
        ('pow', ' ** ', (0.5, 0.9), (2, 1)),
        ('min', ' and ', (0.7, 0.1), (0.2, 0.6)),
        ('max', ' and ', (0.7, 0.1), (0.2, 0.6)),
    ]
    for definition, between, left, right in pairs:
        fg = new('%s of %s%s%s' % (definition, listed(left), between, listed(right)), 2)
        show(fg, binary(fg, definition, constant(fg, *left), constant(fg, *right)), 2)
    functions = (
        *(('abs', -0.3, '-0.3'), ('sqrt', 0.25, '0.25'), ('sin', math.pi / 6, 'pi/6'), ('cos', math.pi / 3, 'pi/3')),
        *(('tan', 0.4, '0.4'), ('exp', -1.2, '-1.2'), ('log', 1.5, '1.5'), ('log2', 1.5, '1.5')),
    )
    for definition, x, label in functions:
        fg = new('%s %s' % (definition, label))
        show(fg, fed(fg, definition, a=constant(fg, x)))
    for definition, x, by, then in (('floor', -0.3, 2.0, 4.0), ('ceil', -0.3, 2.0, 4.0), ('neg', 0.3, 1.0, 2.0)):
        fg = new('%s %g, then (x + %g) / %g' % (definition, x, by, then))
        show(fg, shifted(fg, fed(fg, definition, a=constant(fg, x)), by, then))
    for definition, a, b in (('min', 0.7, 0.2), ('max', 0.2, 0.7)):
        fg = new('%s %g, %g' % (definition, a, b))
        show(fg, binary(fg, definition, constant(fg, a), constant(fg, b)))
    fg = new('dot of (0.2, 0.5) and (0.5, 0.4)')
    show(fg, binary(fg, 'dot', constant(fg, 0.2, 0.5), constant(fg, 0.5, 0.4)))
    fg = new('rand of 0.1, then x + 0.5')  # so that a negative reads below 0.5 (REVIEW.md SRV-214)
    show(fg, binary(fg, 'add', fed(fg, 'rand', a=constant(fg, 0.1)), constant(fg, 0.5)))
    noise, fg = cell(g, colorswitch=False)  # read at every pixel, after the cells
    fg.setOutputNode(fed(fg, 'rand', a=constant(fg, 1.0)), True)
    for definition, symbol, i, j in (('div', '/', 7, 2), ('div', '/', 7, -2), ('mod', '%', -7, 3), ('sub', '-', 2, 5)):
        fg = new('%s of ints %d %s %d, then (x + 5) / 10' % (definition, i, symbol, j))
        show(fg, whole(fg, binary(fg, definition, integers(fg, i), integers(fg, j))))
    fg = new('mul of (0.2, 0.5) and (0.5, 0.4)', 2)
    show(fg, binary(fg, 'mul', constant(fg, 0.2, 0.5), constant(fg, 0.5, 0.4)), 2)
    fg = new('mulscalar of (0.2, 0.6) and 0.5', 2)
    show(fg, fed(fg, 'mulscalar', a=constant(fg, 0.2, 0.6), scalar=constant(fg, 0.5)), 2)
    fg = new('lerp from 0.2 to 0.6 at 0.25')
    show(fg, fed(fg, 'lerp', a=constant(fg, 0.2), b=constant(fg, 0.6), x=constant(fg, 0.25)))
    fg = new('cartesian of rho 0.5 and theta pi/3', 2)
    show(fg, fed(fg, 'cartesian', rho=constant(fg, 0.5), theta=constant(fg, math.pi / 3)), 2)
    for condition in (True, False):
        fg = new('ifelse %s, 0.2, 0.7' % word(condition))
        paths = {'ifpath': constant(fg, 0.2), 'elsepath': constant(fg, 0.7)}
        show(fg, fed(fg, 'ifelse', condition=truth(fg, condition), **paths))
    comparisons = (
        *(('lr', 0.2, 0.7), ('lr', 0.7, 0.7), ('lreq', 0.7, 0.7), ('lreq', 0.7, 0.2), ('gt', 0.7, 0.2)),
        *(('gt', 0.7, 0.7), ('gteq', 0.7, 0.7), ('gteq', 0.2, 0.7), ('eq', 0.7, 0.7), ('eq', 0.2, 0.7)),
        *(('noteq', 0.2, 0.7), ('noteq', 0.7, 0.7)),
    )
    for definition, a, b in comparisons:
        fg = new('%s %g %s %g' % (definition, a, symbols[definition], b))
        show(fg, number(fg, binary(fg, definition, constant(fg, a), constant(fg, b))))
    for definition, a, b in (('and', True, False), ('and', True, True), ('or', True, False)):
        fg = new('%s %s, %s' % (definition, word(a), word(b)))
        show(fg, number(fg, binary(fg, definition, truth(fg, a), truth(fg, b))))
    for x in (True, False):
        fg = new('not %s' % word(x))
        show(fg, number(fg, fed(fg, 'not', a=truth(fg, x))))
    for x in (1.7, -1.7, 2.5):
        fg = new('toint1 %g, then (x + 5) / 10' % x)
        show(fg, whole(fg, fed(fg, 'toint1', value=constant(fg, x))))
    toints: list[tuple[float, ...]] = [(1.7, 2.2), (1.7, 2.2, 3.9), (1.7, 2.2, 3.9, 5.5)]
    for values in toints:
        n = len(values)
        fg = new('toint%d of %s, over 10' % (n, listed(values)), n)
        show(fg, over(fg, fed(fg, 'toint%d' % n, value=constant(fg, *values)), n, 10.0), n)
    fg = new('tofloat of int -7, then (x + 5) / 10')
    show(fg, whole(fg, integers(fg, -7)))
    for i, j in ((-1, 1), (1, 2)):
        fg = new('lr of ints %d %s %d' % (i, symbols['lr'], j))
        show(fg, number(fg, binary(fg, 'lr', integers(fg, i), integers(fg, j))))
    fg = new('neg of int 3, then (x + 5) / 10')
    show(fg, whole(fg, fed(fg, 'neg', a=integers(fg, 3))))
    computed(g, cells)
    drawn = greys(noise)
    print('rand of 1, at each of the %d pixels | %d values' % (len(drawn), len(set(drawn))))


def measure_dollar(g: SDSBSCompGraph) -> None:
    """A uniform colour's $outputsize given a function of the int2 (1, 1), and its $format one of the int 1 (16 bits per
    channel): at the uniform's default inheritance, and made Absolute once the function is built. Each line says the
    size and format computed, and whether the function is still there."""
    cells: Cells = []
    functions: dict[str, SDProperty] = {}  # each cell's parameter with the function, by the uniform's id
    for pid, definition, value, shown in (
        ('$outputsize', 'const_int2', SDValueInt2.sNew(int2(1, 1)), '(1, 1)'),
        ('$format', 'const_int1', SDValueInt.sNew(1), '1'),
    ):
        for absolute in (False, True):
            u = cast(SDSBSCompNode, g.newNode('sbs::compositing::uniform'))
            to_output(g, u)
            p = functions[u.getIdentifier()] = prop(u, pid)
            default = u.getPropertyInheritanceMethod(p).name
            fn = function_graph(u, pid)
            fn.setOutputNode(node(fn, definition, value), True)
            if absolute:
                u.setPropertyInheritanceMethod(p, Method.Absolute)
            how = 'made Absolute after it' if absolute else 'at its default, %s' % default
            cells.append(('a function on %s giving %s, %s' % (pid, shown, how), u))

    def read(u: SDNode) -> str:
        f = u.getPropertyGraph(functions[u.getIdentifier()])
        kept = f is not None and len(f.getNodes()) == 1 and len(f.getOutputNodes()) == 1
        return '%s %s | the function kept %s' % (size(u), pixel_format(u), kept)

    computed(g, cells, read)


def uniform(g: SDGraph, *rgb: float) -> SDNode:
    """A uniform colour of `rgb`, alpha 1."""
    u: SDNode = g.newNode('sbs::compositing::uniform')
    u.setInputPropertyValueFromId('outputcolor', SDValueColorRGBA.sNew(ColorRGBA(*rgb, 1.0)))
    return u


def white_over_black(g: SDGraph) -> SDNode:
    """A blend of a white uniform over a black one, feeding an output node: its pixel is its opacity."""
    blend: SDNode = g.newNode('sbs::compositing::blend')
    for shade, input_id in ((1.0, 'source'), (0.0, 'destination')):
        link(uniform(g, shade, shade, shade), blend, input_id)
    to_output(g, blend)
    return blend


def value_processor(g: SDGraph, *xs: float) -> tuple[SDNode, SDNode]:
    """A Value Processor whose function is a constant of `xs`, and that constant node, to change it."""
    vp: SDNode = g.newNode('sbs::compositing::valueprocessor')
    fn = function_graph(vp, 'function')
    k = constant(fn, *xs)
    fn.setOutputNode(k, True)
    return vp, k


def new_value(n: SDNode, name: str, of: SDType) -> SDProperty:
    """An input value of `n`, as a value connection into `#name` makes it."""
    return cast(SDProperty, n.newProperty(name, of, IN))


def read_by(n: SDNode, pid: str, getter: str, name: str) -> None:
    """`n`'s `pid` given a function of one get_* node, `getter`, reading `name`."""
    fn = function_graph(n, pid)
    fn.setOutputNode(get(fn, getter, name), True)


def half_more(fn: SDGraph, name: str) -> SDNode:
    """The float input value `name` read, + 0.5."""
    return binary(fn, 'add', get(fn, 'get_float1', name), constant(fn, 0.5))


def half_more_processor(g: SDGraph, name: str) -> SDNode:
    """A Value Processor with the float input value `name`, its function `name` + 0.5, feeding an output node."""
    vp: SDNode = g.newNode('sbs::compositing::valueprocessor')
    new_value(vp, name, SDTypeFloat.sNew())
    fn = function_graph(vp, 'function')
    fn.setOutputNode(half_more(fn, name), True)
    to_output(g, vp)
    return vp


def float_out(vp: SDNode) -> str:
    """A Value Processor's float output, with two decimals, after a compute."""
    return '%.2f' % cast(SDValueFloat, vp.getPropertyValue(prop(vp, 'unique_filter_output', OUT))).get()


def opacity_of(g: SDGraph, name: str) -> SDNode:
    """A blend, white over black, with the float input value `name`, which its opacitymult reads."""
    blend = white_over_black(g)
    new_value(blend, name, SDTypeFloat.sNew())
    read_by(blend, 'opacitymult', 'get_float1', name)
    return blend


def listing(n: SDNode, p: SDProperty) -> str:
    """An input value as `n` lists it: whether getProperties lists it, and its types."""
    listed = p.getId() in [q.getId() for q in n.getProperties(IN)]
    return 'listed %s | types %s' % (listed, types(n, p.getId()))


def made(n: SDNode, p: SDProperty | None) -> str:
    return (
        'returned None' if p is None else 'id %s | connectable %s | %s' % (p.getId(), p.isConnectable(), listing(n, p))
    )


def sources(n: SDNode, pid: str) -> list[str]:
    """The nodes connected into `n`'s `pid`: reported from `n`'s side, the input node is the other end (GUIDE.md)."""
    return [cast(SDNode, c.getInputPropertyNode()).getIdentifier() for c in n.getPropertyConnections(prop(n, pid))]


def measure_values(g: SDSBSCompGraph) -> None:
    """Input values made with newProperty, connected and read: the lines say what each call did, then each cell's pixel
    after one compute, then the drive again with the Value Processor changed, and after a save and a reload."""
    float1 = SDTypeFloat.sNew()
    blend = white_over_black(g)
    print("newProperty('#x', a float) | " + made(blend, new_value(blend, '#x', float1)))
    print("newProperty('y', a float) | " + made(blend, new_value(blend, 'y', float1)))
    vp, k = value_processor(g, 0.25)
    two, _ = value_processor(g, 0.2, 0.4)
    two_type = cast(SDType, prop(two, 'unique_filter_output', OUT).getType())
    print(
        "newProperty('#v', a float2 Value Processor's output type) | " + made(blend, new_value(blend, '#v', two_type))
    )
    kinds: SDNode = g.newNode('sbs::compositing::blend')
    made_of = []
    source: SDNode = g.newNode('sbs::compositing::valueprocessor')
    fn = function_graph(source, 'function')
    for kind in ('bool', 'int1', 'int2', 'int3', 'int4', 'float1', 'float2', 'float3', 'float4'):
        fn.setOutputNode(node(fn, 'const_' + kind), True)  # the output takes its type
        given = cast(SDType, prop(source, 'unique_filter_output', OUT).getType())
        new_value(kinds, '#' + kind, given)
        made_of.append('%s %s' % (given.getId(), types(kinds, '#' + kind)))
    print('newProperty with the type of each output a Value Processor gives | ' + ' | '.join(made_of))
    print('a Value Processor into #x | ' + connects(vp, blend, '#x'))
    print("a Value Processor into 'x' | " + connects(vp, blend, 'x'))
    read_by(blend, 'opacitymult', 'get_float1', '#x')
    second = opacity_of(g, '#x')
    link(vp, second, '#x')
    half, _ = value_processor(g, 0.5)
    replaced = connects(half, second, '#x')
    print(
        'a second Value Processor into #x | %s | from the second %s'
        % (replaced, sources(second, '#x') == [half.getIdentifier()])
    )
    image = opacity_of(g, '#t')
    print("a uniform's image into a float #t | " + connects(g.newNode('sbs::compositing::uniform'), image, '#t'))
    print("opacitymult's default | %.2f" % cast(SDValueFloat, prop(image, 'opacitymult').getDefaultValue()).get())
    mixed = opacity_of(g, '#m')
    print('a float2 Value Processor into a float #m | ' + connects(two, mixed, '#m'))
    pp, fg = cell(g)
    new_value(pp, '#x', float1)
    link(vp, pp, '#x')
    fg.setOutputNode(get(fg, 'get_float1', '#x'), True)
    wrong, fg = cell(g)
    new_value(wrong, '#f', float1)
    link(vp, wrong, '#f')
    fg.setOutputNode(joined(fg, 'vector4', get(fg, 'get_float2', '#f'), constant(fg, 0, 1)), True)
    lacking, fg = cell(g)
    fg.setOutputNode(half_more(fg, '#nope'), True)
    alone = opacity_of(g, '#u')
    # a processor's #name with nothing connected, read + 0.5: 0.5 if it reads 0, 0 if the function gives no value
    alone_pp, fg = cell(g)
    new_value(alone_pp, '#u', float1)
    fg.setOutputNode(half_more(fg, '#u'), True)
    cut_pp, fg = cell(g)
    new_value(cut_pp, '#e', float1)
    link(vp, cut_pp, '#e')
    fg.setOutputNode(half_more(fg, '#e'), True)
    alone_vp, cut_vp = half_more_processor(g, '#u'), half_more_processor(g, '#e')
    link(vp, cut_vp, '#e')
    cut = opacity_of(g, '#d')
    link(vp, cut, '#d')
    changed = opacity_of(g, '#c')
    source, _ = value_processor(g, 0.25)
    link(source, changed, '#c')
    fn = function_of(source, 'function')
    fn.setOutputNode(constant(fn, 0.25, 0.25, 0.25, 1), True)
    print(
        'a Value Processor feeding #c, its function changed to a float4 | %d connection | #c types %s | its output %s'
        % (len(sources(changed, '#c')), types(changed, '#c'), output_types(source))
    )
    reader: SDNode = g.newNode('sbs::compositing::valueprocessor')
    new_value(reader, '#x', float1)
    link(vp, reader, '#x')
    read_by(reader, 'function', 'get_float1', '#x')
    to_output(g, reader)
    cells: Cells = [
        ('opacitymult reading #x, the Value Processor at 0.25', blend),
        ('opacitymult reading #x, the second Value Processor at 0.5', second),
        ('opacitymult reading #t, an image', image),
        ('opacitymult reading #m, a float2 (0.2, 0.4)', mixed),
        ('a Pixel Processor reading its #x', pp),
        ('a Pixel Processor reading a float #f with get_float2, in a vector4 with (0, 1)', wrong),
        ('a Pixel Processor reading #nope + 0.5, which it lacks', lacking),
        ('opacitymult reading #u, with nothing ever connected', alone),
        ('a Pixel Processor reading its #u + 0.5, with nothing ever connected', alone_pp),
        ('opacitymult reading #d, the Value Processor at 0.25 connected', cut),
        ('opacitymult reading #c, its source changed to a float4', changed),
    ]
    computed(g, cells)
    print('a Value Processor reading its #x | %s' % float_out(reader))
    print('a Value Processor reading its #u + 0.5, with nothing ever connected | %s' % float_out(alone_vp))
    k.setInputPropertyValueFromId('__constant__', SDValueFloat.sNew(0.75))
    for disconnected, name in ((cut, '#d'), (cut_pp, '#e'), (cut_vp, '#e')):  # as a disconnect after a tool's read
        disconnected.deletePropertyConnections(prop(disconnected, name))
    computed(
        g,
        [
            ('opacitymult reading #x, the Value Processor at 0.75', blend),
            ('opacitymult reading #d, after a disconnect', cut),
            ('a Pixel Processor reading its #e + 0.5, after a disconnect', cut_pp),
        ],
    )
    print('a Value Processor reading its #e + 0.5, after a disconnect | %s' % float_out(cut_vp))
    reloaded(g, blend.getIdentifier(), vp.getIdentifier(), k)


@contextmanager
def saved_and_loaded(g: SDSBSCompGraph, after_save: Callable[[], None] | None = None) -> Iterator[SDSBSCompGraph]:
    """g's package saved to a file of its own, `after_save` run, then the package unloaded and loaded again: the graph
    loaded, its package unloaded and the file removed after it."""
    folder = tempfile.mkdtemp(prefix='mcp_selftest_reloaded_')
    try:
        path = os.path.join(folder, 'reloaded.sbs')
        pm.savePackageAs(g.getPackage(), path)
        if after_save is not None:
            after_save()
        pm.unloadUserPackage(g.getPackage())
        loaded = pm.loadUserPackage(path)
        try:
            [again] = [r for r in loaded.getChildrenResources(False) if isinstance(r, SDSBSCompGraph)]
            yield again
        finally:
            pm.unloadUserPackage(loaded)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def reloaded(g: SDSBSCompGraph, blend_id: str, vp_id: str, k: SDNode) -> None:
    """The package saved, its Value Processor's constant `k` then changed from 0.75 to 0.3 unsaved, unloaded and loaded
    again: the blend's #x, its connection and its function, then its drive at 0.75, the file's (the package kept would
    give 0.3), and with the Value Processor set to 0.5 (a drive lost reads the opacity's default, 1). A part lost is
    said on the first line, and the drive isn't read."""
    with saved_and_loaded(g, lambda: k.setInputPropertyValueFromId('__constant__', SDValueFloat.sNew(0.3))) as again:
        blend, vp = again.getNodeFromId(blend_id), again.getNodeFromId(vp_id)
        held = blend.getPropertyFromId('#x', IN) if blend is not None else None
        fn = vp.getPropertyGraph(prop(vp, 'function')) if vp is not None else None
        constants = fn.getOutputNodes() if fn is not None else []
        if blend is None or held is None or len(constants) != 1:
            print(
                "after a save and a reload, #x | lost: the blend %s, its #x %s, the Value Processor's constant %s"
                % (blend is not None, held is not None, len(constants) == 1)
            )
            return
        drive = blend.getPropertyGraph(prop(blend, 'opacitymult'))
        print(
            'after a save and a reload, #x | %s | %d connection, from the Value Processor %s | the function kept %s'
            % (
                listing(blend, held),
                len(sources(blend, '#x')),
                sources(blend, '#x') == [vp_id],
                drive is not None and len(drive.getOutputNodes()) == 1,
            )
        )
        computed(again, [('after a save and a reload, the Value Processor at 0.75, as saved', blend)])
        constants[0].setInputPropertyValueFromId('__constant__', SDValueFloat.sNew(0.5))
        computed(again, [('after a save and a reload, the Value Processor set to 0.5', blend)])


def connectors(n: SDNode | SDGraph, category: SDPropertyCategory) -> str:
    """`n`'s connectors of `category` but the `$` ones, each with its types, in the order getProperties lists them."""
    shown = ['%s %s' % (p.getId(), types_of(p)) for p in n.getProperties(category) if not p.getId().startswith('$')]
    return ', '.join(shown) or 'none'


def resource(g: SDSBSCompGraph, identifier: str, *inputs: tuple[str, SDType]) -> SDSBSFunctionGraph:
    """A function graph of `g`'s package, `identifier`, with `inputs` made by newProperty, in that order."""
    fn = SDSBSFunctionGraph.sNew(g.getPackage())
    fn.setIdentifier(identifier)
    for pid, of in inputs:
        fn.newProperty(pid, of, IN)
    return fn


def painted(fn: SDGraph, first: SDNode, k: SDNode) -> None:
    """`fn`'s output (first.x, first.y, k, 1), `first` a float2."""
    fn.setOutputNode(joined(fn, 'vector4', joined(fn, 'vector3', first, k), constant(fn, 1)), True)


def calling(g: SDGraph, fn: SDResource) -> tuple[SDNode, SDGraph, SDNode]:
    """A Pixel Processor whose perpixel is an instance node of `fn`, its output node: the processor, its function and
    the instance."""
    pp, ppfg = cell(g)
    instance = instance_in(ppfg, fn)
    ppfg.setOutputNode(instance, True)
    return pp, ppfg, instance


def instance_in(fg: SDGraph, fn: SDResource) -> SDNode:
    """An instance node of the function graph `fn` in the function graph `fg`."""
    return cast(SDNode, fg.newInstanceNode(fn))


def type_id(r: SDResource) -> str | None:
    """What a resource's getType() gives, by its id."""
    t = r.getType()
    return t.getId() if t is not None else None


def listing_of(pkg: SDPackage) -> str:
    """The resources a package lists at its top level: each identifier and its class."""
    return ', '.join('%s %s' % (r.getIdentifier(), type(r).__name__) for r in pkg.getChildrenResources(False))


def links(instance: SDNode) -> str:
    """How many connections each of an instance node's inputs has: 'uv 1, k 0'."""
    linked = [
        '%s %d' % (p.getId(), len(instance.getPropertyConnections(p)))
        for p in instance.getProperties(IN)
        if p.isConnectable()
    ]
    return ', '.join(linked) or 'none'


def instance_state(instance: SDNode) -> str:
    """An instance node's definition, its inputs and outputs with their types, its inputs' connections and the
    resource it references."""
    referenced = instance.getReferencedResource()
    return 'definition %s | inputs %s | outputs %s | connected %s | resource %s' % (
        cast(SDDefinition, instance.getDefinition()).getId(),
        connectors(instance, IN),
        connectors(instance, OUT),
        links(instance),
        referenced.getIdentifier() if referenced is not None else None,
    )


def measure_resources(g: SDSBSCompGraph) -> None:
    """Function graphs stored in the package: what SDSBSFunctionGraph.sNew and setIdentifier make, a taken identifier
    included; the inputs newProperty makes on one, of each type; what decides its output's type; what an instance node
    of one shows and computes in a Pixel Processor, an input left unconnected, $pos read inside it and one called from
    another included; what replacing its nodes, its inputs and its output's type does to an instance calling it; a
    save and a reload; delete()."""
    pkg = g.getPackage()
    float1, float2_ = SDTypeFloat.sNew(), SDTypeFloat2.sNew()
    fn = resource(g, 'paint')
    print(
        'a new function graph, given the identifier paint | %s | inputs %s | outputs %s | type %s'
        % (fn.getIdentifier(), connectors(fn, IN), connectors(fn, OUT), type_id(fn))
    )
    print('a second one given paint | %s' % resource(g, 'paint').getIdentifier())
    print("one given the compositing graph's identifier | %s" % resource(g, g.getIdentifier()).getIdentifier())
    made = fn.newProperty('uv', float2_, IN)
    print("newProperty('uv', a float2) | %s" % ('id %s | types %s' % (made.getId(), types_of(made)) if made else None))
    fn.newProperty('k', float1, IN)
    print('its inputs, uv then k | %s' % connectors(fn, IN))
    kinds = resource(g, 'kinds')
    made_of = []
    for name, of in (
        ('b', SDTypeBool.sNew()),
        ('i1', SDTypeInt.sNew()),
        ('i2', SDTypeInt2.sNew()),
        ('i3', SDTypeInt3.sNew()),
        ('i4', SDTypeInt4.sNew()),
        ('f1', float1),
        ('f2', float2_),
        ('f3', SDTypeFloat3.sNew()),
        ('f4', SDTypeFloat4.sNew()),
        ('s', SDTypeString.sNew()),
    ):
        p = kinds.newProperty(name, of, IN)
        made_of.append('%s %s' % (name, types_of(p) if p else None))
    print('newProperty of each type | ' + ' | '.join(made_of))
    outputs = []
    for definition in ('const_float2', 'const_bool', 'const_int3'):
        kinds.setOutputNode(node(kinds, definition), True)
        outputs.append('%s: %s, type %s' % (definition, connectors(kinds, OUT), type_id(kinds)))
    print('its output, by its output node | ' + ' | '.join(outputs))
    painted(fn, get(fn, 'get_float2', 'uv'), get(fn, 'get_float1', 'k'))
    print('paint given a float4 output node | outputs %s | type %s' % (connectors(fn, OUT), type_id(fn)))
    pp, ppfg, called = calling(g, fn)
    print('an instance node of paint in a Pixel Processor | ' + instance_state(called))
    link(constant(ppfg, 0.2, 0.4), called, 'uv')
    link(constant(ppfg, 0.6), called, 'k')
    print('the instance, uv and k connected | ' + instance_state(called))
    unconnected, fg2, alone = calling(g, fn)
    link(constant(fg2, 0.2, 0.4), alone, 'uv')
    where = resource(g, 'where')
    where.setOutputNode(joined(where, 'vector4', variable(where, '$pos'), constant(where, 0, 1)), True)
    at, _, _ = calling(g, where)
    outer = resource(g, 'outer', ('uv', float2_))
    inner = instance_in(outer, fn)
    link(get(outer, 'get_float2', 'uv'), inner, 'uv')
    link(constant(outer, 0.6), inner, 'k')
    outer.setOutputNode(inner, True)
    nested, fg3, through = calling(g, outer)
    link(constant(fg3, 0.2, 0.4), through, 'uv')
    computed(
        g,
        [
            ('paint(uv (0.2, 0.4), k 0.6) in a Pixel Processor', pp),
            ('paint(uv (0.2, 0.4)), k left unconnected', unconnected),
            ('where(), reading $pos at pixel (0, 0) of 4 px', at),
            ('outer(uv (0.2, 0.4)), calling paint(uv, 0.6)', nested),
        ],
    )
    old = list(fn.getNodes())
    swapped = node(fn, 'swizzle2', SDValueInt2.sNew(int2(1, 0)))
    link(get(fn, 'get_float2', 'uv'), swapped, 'vector')
    painted(fn, swapped, binary(fn, 'mul', get(fn, 'get_float1', 'k'), constant(fn, 0.5)))
    for n in old:
        fn.deleteNode(n)
    computed(g, [('paint replaced after a compute, built beside: (uv.y, uv.x, k * 0.5, 1)', pp)])
    fn.newProperty('extra', float1, IN)
    print('paint given an input extra | its inputs %s | the instance %s' % (connectors(fn, IN), instance_state(called)))
    fn.deleteProperty(cast(SDProperty, fn.getPropertyFromId('k', IN)))
    print('paint without its input k | its inputs %s | the instance %s' % (connectors(fn, IN), instance_state(called)))
    computed(g, [('paint without k, which its body still reads', pp)])
    fn.deleteProperty(cast(SDProperty, fn.getPropertyFromId('uv', IN)))
    fn.newProperty('uv', SDTypeFloat3.sNew(), IN)
    print(
        'paint with uv made a float3 | its inputs %s | the instance %s' % (connectors(fn, IN), instance_state(called))
    )
    fn.setOutputNode(constant(fn, 0.5), True)
    print('paint given a float output node | the instance %s' % instance_state(called))
    computed(g, [('paint giving a float 0.5', pp)])
    twin = resource(g, 'twin')
    twin.delete()
    print('a function deleted with delete() | %s' % listing_of(pkg))
    two = measure_more_calls(g)
    reloaded_call(g, pp.getIdentifier(), two)


def measure_more_calls(g: SDSBSCompGraph) -> str:
    """More kinds of calls (REVIEW.md TST-733): int and bool inputs passed; a call giving a bool and an int; $size,
    $sizelog2 and $tiling read inside a function graph a Pixel Processor calls; a float3 input left unconnected; a
    Value Processor's function and a blend's opacitymult calling one; two inputs of one type, in an order that isn't
    their names'; an input deleted between two others (REVIEW.md HLP-233); the ids newProperty makes of a few names
    (REVIEW.md HLP-235). Returns the id of the Pixel Processor calling `two`, read again after the reload."""
    float1 = SDTypeFloat.sNew()
    ib = resource(g, 'ib', ('i', SDTypeInt.sNew()), ('b', SDTypeBool.sNew()))
    quarter = binary(ib, 'div', as_floats(ib, get(ib, 'get_integer1', 'i'), 1), constant(ib, 4.0))
    choice = fed(ib, 'ifelse', condition=get(ib, 'get_bool', 'b'), ifpath=quarter, elsepath=constant(ib, 0.1))
    ib.setOutputNode(choice, True)
    cells: Cells = []
    for on in (True, False):
        pp, fg, call = calling(g, ib)
        link(integers(fg, 3), call, 'i')
        link(truth(fg, on), call, 'b')
        cells.append(('ib(i 3, b true) = b ? i / 4 : 0.1, in a Pixel Processor' if on else 'ib(i 3, b false)', pp))
    big = resource(g, 'big', ('x', float1))
    big.setOutputNode(binary(big, 'gt', get(big, 'get_float1', 'x'), constant(big, 0.5)), True)
    pp, fg, call = calling(g, big)
    link(constant(fg, 0.7), call, 'x')
    fg.setOutputNode(fed(fg, 'ifelse', condition=call, ifpath=constant(fg, 0.8), elsepath=constant(fg, 0.2)), True)
    print('big: its call gives | ' + connectors(call, OUT))
    cells.append(('big(0.7) = 0.7 > 0.5, a bool, in an ifelse giving 0.8 or 0.2', pp))
    three = resource(g, 'three')
    three.setOutputNode(integers(three, 3), True)
    pp, fg, call = calling(g, three)
    fg.setOutputNode(binary(fg, 'div', as_floats(fg, call, 1), constant(fg, 4.0)), True)
    print('three: its call gives | ' + connectors(call, OUT))
    cells.append(('three() = 3, an int, over 4', pp))
    for name, name_read, by, label in (
        ('size16', '$size', 16.0, 'size16() = float4($size / 16, 0, 1), in a 4 px Pixel Processor'),
        ('log4', '$sizelog2', 4.0, 'log4() = float4($sizelog2 / 4, 0, 1)'),
    ):
        reading = resource(g, name)
        scaled = binary(reading, 'div', variable(reading, name_read), constant(reading, by, by))
        reading.setOutputNode(joined(reading, 'vector4', scaled, constant(reading, 0, 1)), True)
        cells.append((label, calling(g, reading)[0]))
    tiling = resource(g, 'tiling4')
    counted_tiling = as_floats(tiling, variable(tiling, '$tiling'), 1)
    tiling.setOutputNode(binary(tiling, 'div', counted_tiling, constant(tiling, 4.0)), True)
    cells.append(('tiling4() = float($tiling) / 4', calling(g, tiling)[0]))
    vec = resource(g, 'vec', ('v', SDTypeFloat3.sNew()))
    marked = binary(vec, 'add', get(vec, 'get_float3', 'v'), constant(vec, 0.25, 0.25, 0.25))
    vec.setOutputNode(joined(vec, 'vector4', marked, constant(vec, 1)), True)
    cells.append(('vec(v) = float4(v + 0.25, 1), its float3 v left unconnected', calling(g, vec)[0]))
    half = resource(g, 'half', ('x', float1))
    half.setOutputNode(binary(half, 'mul', get(half, 'get_float1', 'x'), constant(half, 0.5)), True)
    vp: SDNode = g.newNode('sbs::compositing::valueprocessor')
    blend = white_over_black(g)
    for n, pid in ((vp, 'function'), (blend, 'opacitymult')):
        fn = function_graph(n, pid)
        halved = instance_in(fn, half)
        link(constant(fn, 0.6), halved, 'x')
        fn.setOutputNode(halved, True)
    to_output(g, vp)
    cells.append(("half(x 0.6), a blend's opacitymult calling it, white over black", blend))
    two = resource(g, 'two', ('y', float1), ('x', float1))
    pair = joined(two, 'vector2', get(two, 'get_float1', 'y'), get(two, 'get_float1', 'x'))
    two.setOutputNode(joined(two, 'vector4', pair, constant(two, 0, 1)), True)
    pp_two, fg, call = calling(g, two)
    link(constant(fg, 0.2), call, 'y')
    link(constant(fg, 0.6), call, 'x')
    cells.append(('two(y 0.2, x 0.6) = float4(y, x, 0, 1)', pp_two))
    abc = resource(g, 'abc', ('a', float1), ('b', float1), ('c', float1))
    ab = joined(abc, 'vector2', get(abc, 'get_float1', 'a'), get(abc, 'get_float1', 'b'))
    abc.setOutputNode(
        joined(abc, 'vector4', joined(abc, 'vector3', ab, get(abc, 'get_float1', 'c')), constant(abc, 1)), True
    )
    pp_abc, fg, call_abc = calling(g, abc)
    for pid, x in (('a', 0.2), ('b', 0.4), ('c', 0.6)):
        link(constant(fg, x), call_abc, pid)
    cells.append(('abc(a 0.2, b 0.4, c 0.6) = float4(a, b, c, 1)', pp_abc))
    computed(g, cells)
    print('half(x 0.6) = x * 0.5, a Value Processor calling it | %s' % float_out(vp))
    abc.deleteProperty(prop(abc, 'b'))
    print('abc without b: the call | inputs %s | connected %s' % (connectors(call_abc, IN), links(call_abc)))
    computed(g, [('abc without b, which its body still reads', pp_abc)])
    ids = resource(g, 'ids')
    for pid in ('Uv', '_k', 'k_', 'a1', 'x_2'):
        ids.newProperty(pid, float1, IN)
    print("newProperty's ids for Uv, _k, k_, a1, x_2 | " + connectors(ids, IN))
    return pp_two.getIdentifier()


def reloaded_call(g: SDSBSCompGraph, pp_id: str, two_id: str) -> None:
    """The package saved, unloaded and loaded again: the Pixel Processor's instance and what it computes; the function
    graph `two`'s inputs, which a call gives in their order, and what the Pixel Processor `two_id` calling it
    computes."""
    with saved_and_loaded(g) as again:
        pp: SDNode | None = again.getNodeFromId(pp_id)
        instances = [n for n in function_of(pp).getNodes() if n.getReferencedResource() is not None] if pp else []
        print('after a save and a reload, the instance | %s' % (instance_state(instances[0]) if instances else 'lost'))
        cells: Cells = (
            [('after a save and a reload, paint giving a float 0.5', pp)] if pp is not None and instances else []
        )
        two = [
            r
            for r in again.getPackage().getChildrenResources(True)
            if isinstance(r, SDSBSFunctionGraph) and r.getIdentifier() == 'two'
        ]
        caller: SDNode | None = again.getNodeFromId(two_id)
        print('after a save and a reload, two | inputs %s' % (connectors(two[0], IN) if two else 'lost'))
        if two and caller is not None:
            cells.append(('after a save and a reload, two(y 0.2, x 0.6)', caller))
        computed(again, cells)


XS = (-0.1, 0.3, 0.7, 1.1)  # where a sample's x falls in 4 px: beyond the left edge, between centres, beyond the right
TOP = 0.125  # the top row's centre, in 4 px


def image_input(k: int) -> str:
    """A processor's input image `k`: input, input:1, input:2..."""
    return 'input:%d' % k if k else 'input'


def with_images(n: SDNode, sources: list[SDNode]) -> SDNode:
    """`n`, `sources` connected into its input images in order, as each is listed once the one before it is
    connected."""
    for k, source in enumerate(sources):
        link(source, n, image_input(k))
    return n


def sampling(fg: SDGraph, definition: str, index: int, mode: int, at: SDNode) -> SDNode:
    """A samplecol or samplelum node (`definition`) of the input `index`, in `mode`, at the float2 `at`."""
    s = node(fg, definition, SDValueInt2.sNew(int2(index, mode)))
    link(at, s, 'pos')
    return s


def sampled(
    g: SDGraph,
    sources: list[SDNode],
    index: int,
    definition: str = 'samplecol',
    mode: int = 0,
    x: float = 0.875,
    y: float = TOP,
) -> SDNode:
    """A Pixel Processor whose function samples its input `index` in `mode` at (x, y), `sources` in its input images."""
    pp, fg = cell(g)
    with_images(pp, sources)
    fg.setOutputNode(sampling(fg, definition, index, mode, constant(fg, x, y)), True)
    return pp


def measure_sampling(g: SDSBSCompGraph) -> None:
    """samplecol and samplelum, each cell a Pixel Processor sampling its inputs: the source a Pixel Processor of
    float4($pos, 0.5, 1), and uniform colours. Each mode at XS of the top row, a line per mode, then samplecol's along
    y, down the first column; where pos reads; what each index reads, index 39 of 40 inputs, and large and negative
    indices with input alone connected; what __constant__ holds at and past the largest int; sampling from a function
    graph and in a Value Processor; a new node's constant."""
    src, fg = cell(g)
    fg.setOutputNode(joined(fg, 'vector4', variable(fg, '$pos'), constant(fg, 0.5, 1)), True)
    red, green = uniform(g, 0.9, 0.1, 0.3), uniform(g, 0.2, 0.7, 0.4)
    spread = ', '.join('%g' % x for x in XS)
    # (what the line says, the cells, the channel read): each mode along x, then along y (REVIEW.md TST-742)
    modes = [
        ('%s, mode %d: R at x %s' % (d, mode, spread), [sampled(g, [src], 0, d, mode, x) for x in XS], 0)
        for d in ('samplecol', 'samplelum')
        for mode in range(4)
    ]
    modes += [
        (
            'samplecol, mode %d: G at y %s' % (mode, spread),
            [sampled(g, [src], 0, 'samplecol', mode, 0.125, y) for y in XS],
            1,
        )
        for mode in range(4)
    ]
    gap = sampled(g, [src, red, green], 1)
    after_gap = sampled(g, [src, red, green], 2)
    for n in (gap, after_gap):
        n.deletePropertyConnections(prop(n, 'input:1'))
    identity, fg = cell(g)
    with_images(identity, [src])
    fg.setOutputNode(sampling(fg, 'samplecol', 0, 0, variable(fg, '$pos')), True)
    fn = resource(g, 'sampling', ('uv', SDTypeFloat2.sNew()))
    fn.setOutputNode(sampling(fn, 'samplecol', 1, 0, get(fn, 'get_float2', 'uv')), True)
    caller, cfg, call = calling(g, fn)
    with_images(caller, [src, red])
    link(constant(cfg, 0.875, TOP), call, 'uv')
    cells: Cells = [
        ('samplecol at (0.875, 0.125)', sampled(g, [src], 0)),
        ('samplecol at (0.125, 0.875)', sampled(g, [src], 0, x=0.125, y=0.875)),
        ('samplelum of the colour (0.9, 0.1, 0.3)', sampled(g, [red], 0, 'samplelum')),
        ('samplecol, index 1: input:1, the colour (0.9, 0.1, 0.3)', sampled(g, [src, red], 1)),
        ('samplecol, index 2: input:2, nothing connected', sampled(g, [src, red], 2)),
        ('samplecol, index 5: beyond the inputs', sampled(g, [src, red], 5)),
        ('samplecol, index 0: nothing connected', sampled(g, [], 0)),
        ('samplecol, index 1: input:1 disconnected, input:2 still connected', gap),
        ('samplecol, index 2: input:2, the colour (0.2, 0.7, 0.4), after the disconnected input:1', after_gap),
        ('a function graph sampling index 1 at its uv (0.875, 0.125), called from a Pixel Processor', caller),
        # 40 inputs, the last of another colour
        (
            'samplecol, index 39 of 40 inputs: input:39, the colour (0.2, 0.7, 0.4)',
            sampled(g, [red] * 39 + [green], 39),
        ),
        # large and negative indices, with nothing connected there (REVIEW.md SRV-201)
        *(('samplecol, index %d: input connected only' % k, sampled(g, [src], k)) for k in (70, 2**31 - 1, -1)),
    ]
    processors = []
    for index in (0, 1, None):  # None: a call of the function graph sampling index 1
        vp = with_images(g.newNode('sbs::compositing::valueprocessor'), [src, red])
        vfg = function_graph(vp, 'function')
        at = constant(vfg, 0.875, TOP)
        if index is None:
            called = instance_in(vfg, fn)
            link(at, called, 'uv')
            vfg.setOutputNode(called, True)
        else:
            vfg.setOutputNode(sampling(vfg, 'samplecol', index, 0, at), True)
        to_output(g, vp)
        processors.append(vp)
    g.compute()
    for label, row, channel in modes:
        print('%s | %s' % (label, ' '.join(pixel(n).split()[channel] for n in row)))
    for label, n in cells:
        print('%s | %s' % (label, pixel(n)))
    print('samplecol at $pos: pixels (1, 2) and (3, 0) | %s | %s' % (pixel(identity, 1, 2), pixel(identity, 3, 0)))
    for label, vp in zip(
        (
            'a Value Processor sampling index 0 at (0.875, 0.125)',
            'a Value Processor sampling index 1',
            'a Value Processor calling the function graph sampling index 1',
        ),
        processors,
        strict=True,
    ):
        v = cast(SDValueFloat4, vp.getPropertyValue(prop(vp, 'unique_filter_output', OUT))).get()
        print('%s | %s' % (label, ' '.join('%.2f' % c for c in (v.x, v.y, v.z, v.w))))
    fresh = [node(fn, d) for d in ('samplecol', 'samplelum')]
    defaults = [pair(cast(SDValueInt2, n.getPropertyValue(prop(n, '__constant__'))).get()) for n in fresh]
    print("a new samplecol's and samplelum's __constant__ | " + ' | '.join(defaults))
    given = [node(fn, 'samplecol', SDValueInt2.sNew(int2(k, 0))) for k in (2**31 - 1, 2**31, -1)]
    held = [pair(cast(SDValueInt2, n.getPropertyValue(prop(n, '__constant__'))).get()) for n in given]
    print('__constant__ given (2147483647, 0), then (2147483648, 0), then (-1, 0) | ' + ' | '.join(held))


def image_inputs(n: SDNode) -> str:
    """`n`'s input images as getProperties lists them, each with its connections: 'input 1, input:1 0'."""
    listed = [p for p in n.getProperties(IN) if p.isConnectable() and p.getId().split(':')[0] == 'input']
    return ', '.join('%s %d' % (p.getId(), len(n.getPropertyConnections(p))) for p in listed)


def connected(g: SDGraph, definition: str, source: SDNode, count: int) -> SDNode:
    """A new node of `definition`, `source` connected into its first `count` input images, in order."""
    return with_images(g.newNode('sbs::compositing::' + definition), [source] * count)


def measure_image_inputs(g: SDSBSCompGraph) -> None:
    """A Pixel and a Value Processor's input images, each line for each (REVIEW.md TST-742): what newProperty makes of
    one, what getProperties lists after each connection and disconnect, 40 connected, a connection into an input not
    listed; then a save and a reload."""
    u = uniform(g, 0.5, 0.5, 0.5)
    for kind, definition in (('a Pixel Processor', 'pixelprocessor'), ('a Value Processor', 'valueprocessor')):
        processor: SDNode = g.newNode('sbs::compositing::' + definition)
        held = prop(processor, 'input')
        made = []
        for pid in ('input:1', 'input', 'input1'):
            try:
                processor.newProperty(pid, cast(SDType, held.getType()), IN)
                made.append('%s made' % pid)
            except (Exception, APIException) as e:
                made.append('%s %s' % (pid, raised(e)))
        print("%s: newProperty, of its input's type | %s" % (kind, ' | '.join(made)))
        print('%s: its input, isVariadic | %s' % (kind, held.isVariadic()))
        print('%s: a new one | %s' % (kind, image_inputs(processor)))
        for pid in ('input', 'input:1'):
            print('%s: %s connected | %s | %s' % (kind, pid, connects(u, processor, pid), image_inputs(processor)))
        for pid in ('input:1', 'input:3'):
            fresh: SDNode = g.newNode('sbs::compositing::' + definition)
            print(
                '%s: a new one, %s connected first | %s | %s'
                % (kind, pid, connects(u, fresh, pid), image_inputs(fresh))
            )
        three = connected(g, definition, u, 3)
        print('%s: input, input:1 and input:2 connected | %s' % (kind, image_inputs(three)))
        for pid, label in (('input:1', 'input:1 disconnected'), ('input:2', 'input:2 disconnected too')):
            three.deletePropertyConnections(prop(three, pid))
            print('%s: %s | %s' % (kind, label, image_inputs(three)))
        first = connected(g, definition, u, 2)
        first.deletePropertyConnections(prop(first, 'input'))
        print('%s: input disconnected, input:1 kept | %s' % (kind, image_inputs(first)))
        listed = image_inputs(connected(g, definition, u, 40)).split(', ')
        print('%s: 40 connected | %d listed, the last %s' % (kind, len(listed), listed[-1]))
    vp = connected(g, 'valueprocessor', u, 2)
    kept = connected(g, 'pixelprocessor', u, 3)
    ids = kept.getIdentifier(), vp.getIdentifier()
    with saved_and_loaded(g) as again:
        shown = [image_inputs(n) if (n := again.getNodeFromId(i)) is not None else 'lost' for i in ids]
        print(
            'after a save and a reload, the three of a Pixel Processor, then the Value Processor | ' + ' | '.join(shown)
        )


def in_the_editor() -> str:
    """The graph Designer's editor has current, its class and identifier, and the title of the graph panel (areaB_),
    once the events an open queued have run."""
    app = cast(QApplication, QApplication.instance())
    for _ in range(10):
        app.processEvents()
    # sd's getQtForPythonUIMgr() has no annotations. It gives None only without Designer's UI
    ui: QtForPythonUIMgrWrapper = sd.getContext().getSDApplication().getQtForPythonUIMgr()
    current = ui.getCurrentGraph()
    panels = [w for w in app.allWidgets() if isinstance(w, QDockWidget) and w.objectName().startswith('areaB_')]
    shown = '%s %s' % (type(current).__name__, current.getIdentifier()) if current is not None else 'none'
    return '%s | panel %s' % (shown, ', '.join(repr(p.windowTitle()) for p in panels) or 'none')


def measure_editor(g: SDSBSCompGraph) -> None:
    """openResourceInEditor of the graph, then of its package's function graph probe_fn, then of a Pixel Processor's
    perpixel function, then of probe_fn again, then of a levels node's leveloutlow function: after each, the graph in
    the editor and its panel's title."""
    ui = cast(SDUIMgr, sd.getContext().getSDApplication().getUIMgr())  # there while Designer runs with its UI
    fn = resource(g, 'probe_fn', ('k', SDTypeFloat.sNew()))
    fn.setOutputNode(node(fn, 'const_float1', SDValueFloat.sNew(0.5)), True)
    _, perpixel = cell(g)
    perpixel.setOutputNode(node(perpixel, 'const_float4', SDValueFloat4.sNew(float4(0.2, 0.4, 0.6, 1))), True)
    levels = g.newNode('sbs::compositing::levels')
    leveloutlow = function_graph(levels, 'leveloutlow')
    leveloutlow.setOutputNode(node(leveloutlow, 'const_float4', SDValueFloat4.sNew(float4(0.1, 0.1, 0.1, 1))), True)
    for label, opened in (
        ('the graph', g),
        ('its function graph probe_fn', fn),
        ("then a Pixel Processor's perpixel function", perpixel),
        ('probe_fn again', fn),
        ("then a levels node's leveloutlow function", leveloutlow),
    ):
        ui.openResourceInEditor(opened)
        print('opened %s | %s' % (label, in_the_editor()))


PARTS: dict[str, tuple[int, Callable[[SDSBSCompGraph], None]]] = {  # each part's graph size (log2) and measure
    'types': (2, measure_types),
    'constants': (2, measure_constants),
    'processors': (2, measure_processors),
    'replacements': (2, measure_replacements),
    'size': (6, measure_size),
    'dollar': (6, measure_dollar),
    'atan2': (2, measure_atan2),
    'variables': (3, measure_variables),
    'computed': (2, measure_computed),
    'values': (2, measure_values),
    'resources': (2, measure_resources),
    'sampling': (2, measure_sampling),
    'image_inputs': (2, measure_image_inputs),
    'editor': (2, measure_editor),
}
size_log2, measure = PARTS[ARGS['part']]
package, graph = new_graph(size_log2)
uid = package.getUID()
try:
    measure(graph)
finally:
    for loaded in pm.getUserPackages():  # by its UID, since `values` saves it and loads it again
        if loaded.getUID() == uid:
            pm.unloadUserPackage(loaded)
