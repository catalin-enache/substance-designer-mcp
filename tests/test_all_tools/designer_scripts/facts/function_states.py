"""Runs inside Designer (run_designer_script), for the "designer facts" checks in facts.py: what a function graph
on a parameter does, the table in AGENTS.md (sd API gotchas). Prints one line per case; facts.py compares them.

On a white uniform, a levels node's levelouthigh is its output. Everything happens in a package of this script's
own, closed again, and each cell gets a fresh node, since setting the value deletes the function graph."""

import ctypes
import os
import shutil
import struct
import tempfile
from typing import Any, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import ColorRGBA, float4, int2
from sd.api.sdgraph import SDGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackage import SDPackage
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdtexture import SDTexture
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
pm = cast(SDPackageMgr, sd.getContext().getSDApplication().getPackageMgr())  # type: ignore[no-untyped-call]


def grey(x: float) -> SDValueFloat4:
    return SDValueFloat4.sNew(float4(x, x, x, 1))


def new_package(identifier: str) -> tuple[SDPackage, SDSBSCompGraph]:
    pkg = pm.newUserPackage()
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier(identifier)
    return pkg, g


def input_of(g: SDGraph, input_id: str) -> SDProperty:
    return cast(SDProperty, g.getPropertyFromId(input_id, C))


def add_get(fg: SDGraph, input_id: str) -> SDNode:
    get = cast(SDNode, fg.newNode('sbs::function::get_float4'))
    get.setInputPropertyValueFromId('__constant__', SDValueString.sNew(input_id))
    return get


def add_function(node: SDNode, prop: SDProperty) -> SDGraph:
    # returns the function graph that is already there, if any: the 'expose' cell measures that
    return cast(SDGraph, node.newPropertyGraph(prop, 'SDSBSFunctionGraph'))


def fresh(g: SDGraph, state: str) -> tuple[SDNode, SDProperty]:
    source = cast(SDNode, g.newNode('sbs::compositing::uniform'))
    source.setInputPropertyValueFromId('outputcolor', SDValueColorRGBA.sNew(ColorRGBA(1, 1, 1, 1)))
    levels = cast(SDNode, g.newNode('sbs::compositing::levels'))
    source.newPropertyConnectionFromId('unique_filter_output', levels, 'input1')
    output = cast(SDNode, g.newNode('sbs::compositing::output'))
    levels.newPropertyConnectionFromId('unique_filter_output', output, 'inputNodeOutput')
    prop = cast(SDProperty, levels.getPropertyFromId(PARAM, C))
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
    value = cast(SDValueTexture, levels.getPropertyValue(levels.getProperties(SDPropertyCategory.Output)[0]))
    texture = cast(SDTexture, value.get())
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
            g.setPropertyValue(cast(SDProperty, g.newProperty(name, SDTypeFloat4.sNew(), C)), grey(value))
        for state in ('none', 'empty', 'no-output', 'output'):
            levels, prop = fresh(g, state)
            cells = ['stored %s, output %s' % (stored(levels, prop), computed(g, levels))]
            levels, prop = fresh(g, state)
            levels.setPropertyValue(prop, grey(0.6))
            cells.append('set: function %s, output %s' % (function_of(levels, prop), computed(g, levels)))
            levels, prop = fresh(g, state)
            fg = add_function(levels, prop)
            fg.setOutputNode(add_get(fg, 'second'), True)
            cells.append('expose: function %s, output %s' % (function_of(levels, prop), computed(g, levels)))
            levels, prop = fresh(g, state)
            if state != 'none':
                levels.deletePropertyGraph(prop)
            cells.append('delete: stored %s, output %s' % (stored(levels, prop), computed(g, levels)))
            print('%s | %s' % (state, ' | '.join(cells)))
        # a get node connected to nothing, then the input a connected one reads taken away
        levels, prop = fresh(g, 'output')
        add_get(cast(SDGraph, levels.getPropertyGraph(prop)), 'second')
        before = computed(g, levels)
        g.setPropertyValue(input_of(g, 'second'), grey(0.1))
        changed = computed(g, levels)
        g.deleteProperty(input_of(g, 'first'))
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
                levels = cast(SDNode, g.newNode('sbs::compositing::levels'))
                ids.append(levels.getIdentifier())
                fg = add_function(levels, cast(SDProperty, levels.getPropertyFromId(PARAM, C)))
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
                prop = cast(SDProperty, levels.getPropertyFromId(PARAM, C))
                counts.append(function_of(levels, prop))
            print('reloaded | %s' % ' | '.join(counts))
        finally:
            pm.unloadUserPackage(pkg)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def uniform_source(g: Any, value: float) -> Any:
    source = g.newNode('sbs::compositing::uniform')
    source.setInputPropertyValueFromId('outputcolor', SDValueColorRGBA.sNew(ColorRGBA(value, value, value, 1)))
    return source


def with_output(g: Any, node: Any, connector: str = 'unique_filter_output') -> None:
    node.newPropertyConnectionFromId(connector, g.newNode('sbs::compositing::output'), 'inputNodeOutput')


def texture_of(g: Any, node: Any, connector: str) -> Any:
    g.compute()
    return node.getPropertyValue(node.getPropertyFromId(connector, SDPropertyCategory.Output)).get()


def grey_of(g: Any, node: Any, connector: str = 'unique_filter_output') -> str:
    texture = texture_of(g, node, connector)
    return '%.2f' % (ctypes.string_at(texture.getPixelBufferAddress(), 1)[0] / 255)


def function_on(node: Any, prop: Any, getter: str, input_id: str, output: bool = True) -> None:
    fg = node.newPropertyGraph(prop, 'SDSBSFunctionGraph')
    get = fg.newNode('sbs::function::' + getter)
    get.setInputPropertyValueFromId('__constant__', SDValueString.sNew(input_id))
    if output:
        fg.setOutputNode(get, True)


def other_kinds() -> None:
    """The same states on an enum parameter, a library-style instance node's parameter (a graph of this package, no
    library package loaded), and $outputsize: the table holds for the first two, not for the last."""
    pkg, inner = new_package('mcp_selftest_functions_inner')
    try:
        # the instanced graph's output is its input
        inner.setPropertyValue(cast(SDProperty, inner.newProperty('amount', SDTypeFloat4.sNew(), C)), grey(1.0))
        levels: Any = inner.newNode('sbs::compositing::levels')
        uniform_source(inner, 1.0).newPropertyConnectionFromId('unique_filter_output', levels, 'input1')
        function_on(levels, levels.getPropertyFromId(PARAM, C), 'get_float4', 'amount')
        result: Any = inner.newNode('sbs::compositing::output')
        levels.newPropertyConnectionFromId('unique_filter_output', result, 'inputNodeOutput')
        result.setAnnotationPropertyValueFromId('identifier', SDValueString.sNew('result'))
        g: Any = SDSBSCompGraph.sNew(pkg)
        g.setIdentifier('mcp_selftest_functions_kinds')
        size = g.getPropertyFromId('$outputsize', C)
        g.setPropertyInheritanceMethod(size, SDPropertyInheritanceMethod.Absolute)
        g.setPropertyValue(size, SDValueInt2.sNew(int2(4, 4)))
        for name, kind, value in (('f4', SDTypeFloat4, grey(0.25)), ('i1', SDTypeInt, SDValueInt.sNew(3))):
            g.setPropertyValue(g.newProperty(name, kind.sNew(), C), value)
        g.setPropertyValue(g.newProperty('i2', SDTypeInt2.sNew(), C), SDValueInt2.sNew(int2(3, 3)))

        def enum_case() -> tuple[Any, Any, Any]:
            node = g.newNode('sbs::compositing::blend')
            uniform_source(g, 0.5).newPropertyConnectionFromId('unique_filter_output', node, 'source')
            uniform_source(g, 0.5).newPropertyConnectionFromId('unique_filter_output', node, 'destination')
            with_output(g, node)
            prop = node.getPropertyFromId('blendingmode', C)
            node.setPropertyValue(prop, SDValueEnum.sFromValueId(prop.getType().getId(), 'add'))
            return node, prop, lambda: grey_of(g, node)

        def instance_case() -> tuple[Any, Any, Any]:
            node = g.newInstanceNode(inner)
            with_output(g, node, 'result')
            prop = node.getPropertyFromId('amount', C)
            node.setPropertyValue(prop, grey(0.5))
            return node, prop, lambda: grey_of(g, node, 'result')

        def enum_min(prop: Any) -> Any:
            return SDValueEnum.sFromValueId(prop.getType().getId(), 'min')

        def grey_six(prop: Any) -> Any:
            return grey(0.6)

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
                before = read()
                if state != 'none':
                    node.deletePropertyGraph(prop)
                deleted = read()
                node, prop, read = make()
                if state == 'empty':
                    node.newPropertyGraph(prop, 'SDSBSFunctionGraph')
                elif state != 'none':
                    function_on(node, prop, getter, input_id, state == 'output')
                node.setPropertyValue(prop, new_value(prop))
                print(
                    '%s %s | output %s | set: function %s, output %s | delete: output %s'
                    % (label, state, before, function_of(node, prop), read(), deleted)
                )
        for method in (SDPropertyInheritanceMethod.Absolute, SDPropertyInheritanceMethod.RelativeToParent):
            for state in ('none', 'empty', 'no-output', 'output'):
                node = g.newNode('sbs::compositing::levels')
                uniform_source(g, 1.0).newPropertyConnectionFromId('unique_filter_output', node, 'input1')
                with_output(g, node)
                prop = node.getPropertyFromId('$outputsize', C)
                node.setPropertyInheritanceMethod(prop, method)
                node.setPropertyValue(prop, SDValueInt2.sNew(int2(5, 5)))
                if state == 'empty':
                    node.newPropertyGraph(prop, 'SDSBSFunctionGraph')
                elif state != 'none':
                    function_on(node, prop, 'get_integer2', 'i2', state == 'output')
                pixels = texture_of(g, node, 'unique_filter_output').getSize().x
                held = node.getPropertyValue(prop).get()
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

        def switches(where: str, node: Any, pid: str) -> None:
            prop = node.getPropertyFromId(pid, C)
            cells = []
            for method in (SDPropertyInheritanceMethod.Absolute, SDPropertyInheritanceMethod.RelativeToParent):
                node.setPropertyInheritanceMethod(prop, method)
                node.newPropertyGraph(prop, 'SDSBSFunctionGraph')
                node.deletePropertyGraph(prop)
                cells.append('%s -> %s' % (method.name, node.getPropertyInheritanceMethod(prop).name))
            print('%s on %s: delete: %s' % (pid, where, ', '.join(cells)))

        levels_node = g.newNode('sbs::compositing::levels')
        for pid in ('$format', '$tiling', '$pixelratio', '$pixelsize', '$randomseed'):
            switches('levels', levels_node, pid)
        switches('instance', g.newInstanceNode(inner), '$outputsize')
    finally:
        pm.unloadUserPackage(pkg)


def fx_map() -> None:
    """An FX-Map's function reads the graph's input: the output follows it, and changes when it is removed."""
    pkg, g = new_package('mcp_selftest_functions_fx')
    try:
        graph: Any = g
        graph.setInputPropertyValueFromId('$outputsize', SDValueInt2.sNew(int2(4, 4)))
        graph.setPropertyValue(graph.newProperty('f4', SDTypeFloat4.sNew(), C), grey(0.25))
        fx = graph.newNode('sbs::compositing::fxmaps')
        with_output(graph, fx)
        paramset = fx.getReferencedResource().getNodes()[0]
        pattern = paramset.getPropertyFromId('patterntype', C)
        paramset.setPropertyValue(pattern, SDValueEnum.sFromValueId(pattern.getType().getId(), 'square'))
        function_on(paramset, paramset.getPropertyFromId('opacity', C), 'get_float4', 'f4')
        low = grey_of(graph, fx)
        graph.setPropertyValue(graph.getPropertyFromId('f4', C), grey(0.75))
        high = grey_of(graph, fx)
        graph.deleteProperty(graph.getPropertyFromId('f4', C))
        print('fx-map | input at 0.25 %s | at 0.75 %s | removed %s' % (low, high, grey_of(graph, fx)))
    finally:
        pm.unloadUserPackage(pkg)


states()
reload()
other_kinds()
fx_map()
