"""Runs inside Designer (run_designer_script), for the "designer facts" checks in checks.py: what a function graph
on a parameter does, the table in GUIDE.md (sd API gotchas). Prints one line per case; checks.py compares them.

On a white uniform, a levels node's levelouthigh is its output. Everything happens in a package of this script's
own, closed again, and each cell gets a fresh node, since setting the value deletes the function graph. The cells are
built first and read after one graph.compute(): each takes about 0.9 s however small the graph (GUIDE.md, sd API), and
a cell's nodes are its own, so one compute serves them all."""

import ctypes
import os
import shutil
import struct
import tempfile
from collections.abc import Callable
from typing import cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sbs.sdsbscompnode import SDSBSCompNode
from sd.api.sdbasetypes import ColorRGBA, float4, int2
from sd.api.sdgraph import SDGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackage import SDPackage
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdresource import SDResource
from sd.api.sdtexture import SDTexture
from sd.api.sdtype import SDType
from sd.api.sdtypefloat4 import SDTypeFloat4
from sd.api.sdtypeint import SDTypeInt
from sd.api.sdtypeint2 import SDTypeInt2
from sd.api.sdvaluecolorrgba import SDValueColorRGBA
from sd.api.sdvalueenum import SDValueEnum
from sd.api.sdvaluefloat4 import SDValueFloat4
from sd.api.sdvalueint import SDValueInt
from sd.api.sdvalueint2 import SDValueInt2
from sd.api.sdvaluestring import SDValueString
from sd.api.sdvaluetexture import SDValueTexture

C = SDPropertyCategory.Input
PARAM = 'levelouthigh'
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()


def grey(x: float) -> SDValueFloat4:
    return SDValueFloat4.sNew(float4(x, x, x, 1))


def new_package(identifier: str) -> tuple[SDPackage, SDSBSCompGraph]:
    pkg = pm.newUserPackage()
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier(identifier)
    return pkg, g


def property_of(owner: SDNode | SDResource, pid: str, category: SDPropertyCategory = C) -> SDProperty:
    """`owner`'s property `pid`: an input unless `category` says otherwise."""
    return cast(SDProperty, owner.getPropertyFromId(pid, category))


def new_input(g: SDGraph, name: str, kind: SDType) -> SDProperty:
    return cast(SDProperty, g.newProperty(name, kind, C))


def texture_of(node: SDNode, output: SDProperty) -> SDTexture:
    """The texture on `node`'s `output`, as the last compute left it."""
    return cast(SDTexture, cast(SDValueTexture, node.getPropertyValue(output)).get())


def enum_value(prop: SDProperty, value_id: str) -> SDValueEnum:
    """The value `value_id` of the enum parameter `prop`."""
    return SDValueEnum.sFromValueId(cast(SDType, prop.getType()).getId(), value_id)


def add_get(fg: SDGraph, input_id: str) -> SDNode:
    get: SDNode = fg.newNode('sbs::function::get_float4')
    get.setInputPropertyValueFromId('__constant__', SDValueString.sNew(input_id))
    return get


def add_function(node: SDNode, prop: SDProperty) -> SDGraph:
    # returns the function graph that is already there, if any: the 'expose' cell measures that
    return cast(SDGraph, node.newPropertyGraph(prop, 'SDSBSFunctionGraph'))


def fresh(g: SDGraph, state: str) -> tuple[SDNode, SDProperty]:
    source: SDNode = g.newNode('sbs::compositing::uniform')
    source.setInputPropertyValueFromId('outputcolor', SDValueColorRGBA.sNew(ColorRGBA(1, 1, 1, 1)))
    levels: SDNode = g.newNode('sbs::compositing::levels')
    source.newPropertyConnectionFromId('unique_filter_output', levels, 'input1')
    output: SDNode = g.newNode('sbs::compositing::output')
    levels.newPropertyConnectionFromId('unique_filter_output', output, 'inputNodeOutput')
    prop = property_of(levels, PARAM)
    levels.setPropertyValue(prop, grey(0.5))
    if state != 'none':
        fg = add_function(levels, prop)
        if state != 'empty':
            get = add_get(fg, 'first')
            if state == 'output':
                fg.setOutputNode(get, True)
    return levels, prop


def computed(g: SDSBSCompGraph, levels: SDNode) -> str:
    g.compute()
    return output_of(levels)


def output_of(levels: SDNode) -> str:
    """The output as the last compute left it."""
    texture = texture_of(levels, levels.getProperties(SDPropertyCategory.Output)[0])
    raw = ctypes.string_at(texture.getPixelBufferAddress(), texture.getBytesPerPixel())
    if str(texture.getPixelFormat()).endswith('16'):
        return '%.2f' % (struct.unpack_from('<H', raw)[0] / 65535)
    return '%.2f' % (raw[0] / 255)


def stored(levels: SDNode, prop: SDProperty) -> str:
    return '%.2f' % cast(SDValueFloat4, levels.getPropertyValue(prop)).get().x


def function_of(levels: SDNode, prop: SDProperty) -> str:
    fg = levels.getPropertyGraph(prop)
    return 'none' if fg is None else '%d nodes %d outputs' % (len(fg.getNodes()), len(fg.getOutputNodes()))


def states() -> None:
    """Each state against set, expose (a get node made the output) and delete."""
    pkg, g = new_package('mcp_selftest_functions')
    try:
        g.setInputPropertyValueFromId('$outputsize', SDValueInt2.sNew(int2(4, 4)))
        for name, value in (('first', 0.25), ('second', 0.75)):
            g.setPropertyValue(new_input(g, name, SDTypeFloat4.sNew()), grey(value))
        rows = []
        for state in ('none', 'empty', 'no-output', 'output'):
            as_made = fresh(g, state)
            set_ = fresh(g, state)
            set_[0].setPropertyValue(set_[1], grey(0.6))
            exposed = fresh(g, state)
            fg = add_function(*exposed)
            fg.setOutputNode(add_get(fg, 'second'), True)
            deleted = fresh(g, state)
            if state != 'none':
                deleted[0].deletePropertyGraph(deleted[1])
            rows.append((state, as_made, set_, exposed, deleted))
        # a get node connected to nothing, then the input a connected one reads taken away
        levels, prop = fresh(g, 'output')
        add_get(cast(SDGraph, levels.getPropertyGraph(prop)), 'second')
        g.compute()
        for state, as_made, set_, exposed, deleted in rows:
            cells = [
                'stored %s, output %s' % (stored(*as_made), output_of(as_made[0])),
                'set: function %s, output %s' % (function_of(*set_), output_of(set_[0])),
                'expose: function %s, output %s' % (function_of(*exposed), output_of(exposed[0])),
                'delete: stored %s, output %s' % (stored(*deleted), output_of(deleted[0])),
            ]
            print('%s | %s' % (state, ' | '.join(cells)))
        before = output_of(levels)
        g.setPropertyValue(property_of(g, 'second'), grey(0.1))
        changed = computed(g, levels)
        g.deleteProperty(property_of(g, 'first'))
        print(
            'unconnected get | output %s, its input changed %s, the connected input removed %s'
            % (before, changed, computed(g, levels))
        )
    finally:
        pm.unloadUserPackage(pkg)


def reload() -> None:
    """A function graph's output node, or the lack of one, survives a save and a reload."""
    folder = tempfile.mkdtemp(prefix='mcp_selftest_functions')
    try:
        path = os.path.join(folder, 'function_outputs.sbs')
        pkg, g = new_package('mcp_selftest_fn_outputs')
        ids = []
        try:
            for has_output in (True, False):
                levels: SDNode = g.newNode('sbs::compositing::levels')
                ids.append(levels.getIdentifier())
                fg = add_function(levels, property_of(levels, PARAM))
                get = add_get(fg, 'first')
                if has_output:
                    fg.setOutputNode(get, True)
            pm.savePackageAs(pkg, path)
        finally:
            pm.unloadUserPackage(pkg)
        pkg = pm.loadUserPackage(path)
        try:
            g = cast(SDSBSCompGraph, pkg.findResourceFromUrl('mcp_selftest_fn_outputs'))
            counts = []
            for node_id in ids:
                levels = cast(SDNode, g.getNodeFromId(node_id))
                prop = property_of(levels, PARAM)
                counts.append(function_of(levels, prop))
            print('reloaded | %s' % ' | '.join(counts))
        finally:
            pm.unloadUserPackage(pkg)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def uniform_source(g: SDGraph, value: float) -> SDNode:
    source: SDNode = g.newNode('sbs::compositing::uniform')
    source.setInputPropertyValueFromId('outputcolor', SDValueColorRGBA.sNew(ColorRGBA(value, value, value, 1)))
    return source


def with_output(g: SDGraph, node: SDNode, connector: str = 'unique_filter_output') -> None:
    node.newPropertyConnectionFromId(connector, g.newNode('sbs::compositing::output'), 'inputNodeOutput')


def grey_of(g: SDSBSCompGraph, node: SDNode, connector: str = 'unique_filter_output') -> str:
    g.compute()
    return grey_now(node, connector)


def grey_now(node: SDNode, connector: str = 'unique_filter_output') -> str:
    """The output as the last compute left it."""
    texture = texture_of(node, property_of(node, connector, SDPropertyCategory.Output))
    return '%.2f' % (ctypes.string_at(texture.getPixelBufferAddress(), 1)[0] / 255)


def function_on(node: SDNode, prop: SDProperty, getter: str, input_id: str, output: bool = True) -> None:
    fg = add_function(node, prop)
    get: SDNode = fg.newNode('sbs::function::' + getter)
    get.setInputPropertyValueFromId('__constant__', SDValueString.sNew(input_id))
    if output:
        fg.setOutputNode(get, True)


def other_kinds() -> None:
    """The same states on an enum parameter, a library-style instance node's parameter (a graph of this package, no
    library package loaded), and $outputsize: the table holds for the first two, not for the last."""
    pkg, inner = new_package('mcp_selftest_functions_inner')
    try:
        # the instanced graph's output is its input
        inner.setPropertyValue(new_input(inner, 'amount', SDTypeFloat4.sNew()), grey(1.0))
        levels: SDNode = inner.newNode('sbs::compositing::levels')
        uniform_source(inner, 1.0).newPropertyConnectionFromId('unique_filter_output', levels, 'input1')
        function_on(levels, property_of(levels, PARAM), 'get_float4', 'amount')
        result: SDNode = inner.newNode('sbs::compositing::output')
        levels.newPropertyConnectionFromId('unique_filter_output', result, 'inputNodeOutput')
        result.setAnnotationPropertyValueFromId('identifier', SDValueString.sNew('result'))
        g = SDSBSCompGraph.sNew(pkg)
        g.setIdentifier('mcp_selftest_functions_kinds')
        size = property_of(g, '$outputsize')
        g.setPropertyInheritanceMethod(size, SDPropertyInheritanceMethod.Absolute)
        g.setPropertyValue(size, SDValueInt2.sNew(int2(4, 4)))
        for name, kind, value in (('f4', SDTypeFloat4, grey(0.25)), ('i1', SDTypeInt, SDValueInt.sNew(3))):
            g.setPropertyValue(new_input(g, name, kind.sNew()), value)
        g.setPropertyValue(new_input(g, 'i2', SDTypeInt2.sNew()), SDValueInt2.sNew(int2(3, 3)))

        def enum_case() -> tuple[SDNode, SDProperty, Callable[[], str]]:
            node: SDNode = g.newNode('sbs::compositing::blend')
            uniform_source(g, 0.5).newPropertyConnectionFromId('unique_filter_output', node, 'source')
            uniform_source(g, 0.5).newPropertyConnectionFromId('unique_filter_output', node, 'destination')
            with_output(g, node)
            prop = property_of(node, 'blendingmode')
            node.setPropertyValue(prop, enum_value(prop, 'add'))
            return node, prop, lambda: grey_now(node)

        def instance_case() -> tuple[SDNode, SDProperty, Callable[[], str]]:
            node = cast(SDNode, g.newInstanceNode(inner))
            with_output(g, node, 'result')
            prop = property_of(node, 'amount')
            node.setPropertyValue(prop, grey(0.5))
            return node, prop, lambda: grey_now(node, 'result')

        def enum_min(prop: SDProperty) -> SDValueEnum:
            return enum_value(prop, 'min')

        def grey_six(prop: SDProperty) -> SDValueFloat4:
            return grey(0.6)

        # each case: a node read before and after its function graph is deleted, and a node set once it has one
        cases = []
        for label, make, getter, input_id, new_value in (
            ('enum', enum_case, 'get_integer1', 'i1', enum_min),
            ('instance', instance_case, 'get_float4', 'f4', grey_six),
        ):
            for state in ('none', 'empty', 'no-output', 'output'):
                node, prop, read = make()
                if state != 'none':
                    if state == 'empty':
                        node.newPropertyGraph(prop, 'SDSBSFunctionGraph')
                    else:
                        function_on(node, prop, getter, input_id, state == 'output')
                set_node, set_prop, read_set = make()
                if state == 'empty':
                    set_node.newPropertyGraph(set_prop, 'SDSBSFunctionGraph')
                elif state != 'none':
                    function_on(set_node, set_prop, getter, input_id, state == 'output')
                set_node.setPropertyValue(set_prop, new_value(set_prop))
                cases.append((label, state, node, prop, read, set_node, set_prop, read_set))
        g.compute()
        befores = [read() for *_, read, _, _, _ in cases]
        for _, state, node, prop, *_ in cases:
            if state != 'none':
                node.deletePropertyGraph(prop)
        g.compute()
        for (label, state, _, _, read, set_node, set_prop, read_set), before in zip(cases, befores, strict=True):
            print(
                '%s %s | output %s | set: function %s, output %s | delete: output %s'
                % (label, state, before, function_of(set_node, set_prop), read_set(), read())
            )
        sizes = []
        for method in (SDPropertyInheritanceMethod.Absolute, SDPropertyInheritanceMethod.RelativeToParent):
            for state in ('none', 'empty', 'no-output', 'output'):
                node = cast(SDSBSCompNode, g.newNode('sbs::compositing::levels'))
                uniform_source(g, 1.0).newPropertyConnectionFromId('unique_filter_output', node, 'input1')
                with_output(g, node)
                prop = property_of(node, '$outputsize')
                node.setPropertyInheritanceMethod(prop, method)
                node.setPropertyValue(prop, SDValueInt2.sNew(int2(5, 5)))
                if state == 'empty':
                    node.newPropertyGraph(prop, 'SDSBSFunctionGraph')
                elif state != 'none':
                    function_on(node, prop, 'get_integer2', 'i2', state == 'output')
                sizes.append((method, state, node, prop))
        g.compute()
        for method, state, node, prop in sizes:
            output = property_of(node, 'unique_filter_output', SDPropertyCategory.Output)
            pixels = texture_of(node, output).getSize().x
            held = cast(SDValueInt2, node.getPropertyValue(prop)).get()
            inherited = node.getPropertyInheritanceMethod(prop).name
            if state != 'none':
                node.deletePropertyGraph(prop)
            print(
                '$outputsize %s %s | %s, stored %d,%d, %d px | delete: %s'
                % (
                    method.name,
                    state,
                    inherited,
                    held.x,
                    held.y,
                    pixels,
                    node.getPropertyInheritanceMethod(prop).name,
                )
            )

        def switches(where: str, node: SDSBSCompNode, pid: str) -> None:
            prop = property_of(node, pid)
            cells = []
            for method in (SDPropertyInheritanceMethod.Absolute, SDPropertyInheritanceMethod.RelativeToParent):
                node.setPropertyInheritanceMethod(prop, method)
                node.newPropertyGraph(prop, 'SDSBSFunctionGraph')
                node.deletePropertyGraph(prop)
                cells.append('%s -> %s' % (method.name, node.getPropertyInheritanceMethod(prop).name))
            print('%s on %s: delete: %s' % (pid, where, ', '.join(cells)))

        levels_node = cast(SDSBSCompNode, g.newNode('sbs::compositing::levels'))
        for pid in ('$format', '$tiling', '$pixelratio', '$pixelsize', '$randomseed'):
            switches('levels', levels_node, pid)
        switches('instance', cast(SDSBSCompNode, g.newInstanceNode(inner)), '$outputsize')
    finally:
        pm.unloadUserPackage(pkg)


def fx_map() -> None:
    """An FX-Map's function reads the graph's input: the output follows it, and changes when it is removed."""
    pkg, g = new_package('mcp_selftest_functions_fx')
    try:
        g.setInputPropertyValueFromId('$outputsize', SDValueInt2.sNew(int2(4, 4)))
        g.setPropertyValue(new_input(g, 'f4', SDTypeFloat4.sNew()), grey(0.25))
        fx: SDNode = g.newNode('sbs::compositing::fxmaps')
        with_output(g, fx)
        paramset = cast(SDGraph, fx.getReferencedResource()).getNodes()[0]
        pattern = property_of(paramset, 'patterntype')
        paramset.setPropertyValue(pattern, enum_value(pattern, 'square'))
        function_on(paramset, property_of(paramset, 'opacity'), 'get_float4', 'f4')
        low = grey_of(g, fx)
        g.setPropertyValue(property_of(g, 'f4'), grey(0.75))
        high = grey_of(g, fx)
        g.deleteProperty(property_of(g, 'f4'))
        print('fx-map | input at 0.25 %s | at 0.75 %s | removed %s' % (low, high, grey_of(g, fx)))
    finally:
        pm.unloadUserPackage(pkg)


states()
reload()
other_kinds()
fx_map()
