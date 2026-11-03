"""Exposed parameters: expose_param, list_graph_inputs, remove_graph_input, set_graph_size."""

import xml.etree.ElementTree as ET

from .core import (
    Any,
    APIException,
    SDDefinition,
    SDGraph,
    SDNode,
    SDProperty,
    SDPropertyCategory,
    SDSBSCompGraph,
    SDType,
    SDTypeEnum,
    SDValue,
    _graph_to_edit,
    cast,
    find_graph,
    fmt,
)
from .edits import _make_value, _node

_GETTERS = {
    'float': 'get_float1',
    'float2': 'get_float2',
    'float3': 'get_float3',
    'float4': 'get_float4',
    'ColorRGBA': 'get_float4',
    'int': 'get_integer1',
    'int2': 'get_integer2',
    'int3': 'get_integer3',
    'int4': 'get_integer4',
    'bool': 'get_bool',
    'string': 'get_string',
}


def _graph_inputs(g: SDSBSCompGraph) -> list[SDProperty]:
    return [p for p in g.getProperties(SDPropertyCategory.Input) if not p.getId().startswith('$')]


def _set_annotation(g: SDSBSCompGraph, prop: SDProperty, key: str, value: Any) -> None:
    from sd.api.sdvaluebool import SDValueBool
    from sd.api.sdvaluefloat import SDValueFloat
    from sd.api.sdvaluestring import SDValueString

    v: SDValue
    if isinstance(value, bool):
        v = SDValueBool.sNew(value)
    elif isinstance(value, (int, float)):
        v = SDValueFloat.sNew(float(value))
    else:
        v = SDValueString.sNew(str(value))
    g.setPropertyAnnotationValueFromId(prop, key, v)


def expose_param(
    identifier: str | SDSBSCompGraph | None,
    node_id: str | None,
    param: str,
    input_id: str | None = None,
    label: str | None = None,
    default: Any = None,
    minimum: Any = None,
    maximum: Any = None,
    step: Any = None,
    group: str | None = None,
) -> None:
    """Create a graph input with the parameter's own type and drive the parameter from it."""
    from sd.api.sdtypeint import SDTypeInt
    from sd.api.sdvaluestring import SDValueString

    g = _graph_to_edit(identifier)
    node = _node(g, node_id)
    prop = node.getPropertyFromId(param, SDPropertyCategory.Input)
    if prop is None or prop.isConnectable():
        raise RuntimeError('%r is not a parameter of node %s; see describe_node' % (param, node_id))
    ptype = cast(SDType, prop.getType())  # a parameter always has a type
    is_enum = isinstance(ptype, SDTypeEnum)
    type_id = 'int' if is_enum else ptype.getId()
    getter = _GETTERS.get(type_id)
    if getter is None:
        raise RuntimeError('parameters of type %s cannot be exposed by this tool' % type_id)
    input_id = input_id or param
    if g.getPropertyFromId(input_id, SDPropertyCategory.Input) is not None:
        raise RuntimeError('graph already has an input %r; pick another input_id' % input_id)
    try:
        existing = node.getPropertyGraph(prop)  # an empty one is reused below
    except (Exception, APIException):
        existing = None
    driven = _driving_graph(node, prop)
    if driven is not None:
        _refuse_no_output(driven, node_id, param)
        _refuse_no_input(g, driven, node_id, param)
        raise RuntimeError(
            '%s.%s is already driven by a function; replacing it would lose that logic. Edit the function by hand%s.'
            % (node_id, param, ', or remove its graph input first' if _plain_binding(driven) is not None else '')
        )
    from sd.api.sdvalueenum import SDValueEnum
    from sd.api.sdvalueint import SDValueInt

    # validate first; a parameter always has a value
    value = _make_value(prop, default) if default is not None else cast(SDValue, node.getPropertyValue(prop))
    if is_enum:
        value = SDValueInt.sNew(int(cast(SDValueEnum, value).get()))
    inp = cast(SDProperty, g.newProperty(input_id, SDTypeInt.sNew() if is_enum else ptype, SDPropertyCategory.Input))
    created_graph = existing is None
    get = None
    old_value = cast(SDValue, node.getPropertyValue(prop))  # adding a function graph resets it to the default
    try:
        g.setPropertyValue(inp, value)
        _set_annotation(g, inp, 'label', label or input_id.replace('_', ' ').capitalize())
        for key, val in (('min', minimum), ('max', maximum), ('step', step), ('group', group)):
            if val is not None:
                _set_annotation(g, inp, key, val)
        fg = cast(SDGraph, existing or node.newPropertyGraph(prop, 'SDSBSFunctionGraph'))
        get = fg.newNode('sbs::function::' + getter)
        get.setInputPropertyValueFromId('__constant__', SDValueString.sNew(input_id))
        fg.setOutputNode(get, True)
    except (Exception, APIException):
        # leave nothing half-made: a function graph left on the parameter would count as "driven";
        # a reused empty one loses the node added to it (REVIEW.md HLP-15)
        try:
            if created_graph:
                _delete_function(node, prop)
                node.setPropertyValue(prop, old_value)  # as it was (REVIEW.md HLP-21)
            elif get is not None:
                fg.deleteNode(get)
        except (Exception, APIException):
            pass
        g.deleteProperty(inp)  # don't leave an input that drives nothing
        raise
    print(
        'exposed %s.%s as graph input %r (%s, default %r)'
        % (node_id, param, input_id, type_id, fmt(g.getPropertyValue(inp)))
    )


def _driving_graph(node: SDNode, prop: SDProperty) -> SDGraph | None:
    """The function graph on a parameter that the tools must not overwrite, or None. An empty one
    (no nodes) drives nothing and holds nothing, so the stored value counts ($outputsize differs: AGENTS.md). One with nodes but no
    output node drives nothing either (_has_output), but setting the value would delete its nodes,
    so it is returned too. The states are measured: AGENTS.md, sd API gotchas."""
    try:
        fg: SDGraph | None = node.getPropertyGraph(prop)
    except (Exception, APIException):
        return None
    if fg is None or not len(fg.getNodes()):
        return None
    return fg


def _has_output(fg: SDGraph) -> bool:
    """Whether this function graph has an output node; without one it drives nothing."""
    return len(fg.getOutputNodes()) > 0


def _refuse_no_output(fg: SDGraph, node_id: str | None, param: str) -> None:
    """Raise if this function graph has no output node, instead of calling it what drives the value."""
    if not _has_output(fg):
        raise RuntimeError(
            '%s.%s has a function with no output node: it drives nothing, and '
            'this would replace it. Give it an output node in Designer, or delete it first '
            '(deletePropertyGraph in code).' % (node_id, param)
        )


def _reads_no_input(g: SDSBSCompGraph, fg: SDGraph) -> bool:
    """Whether this function is one get node of a name that isn't an input of the graph. $ and # names are Designer's
    own, some of them properties of the graph, so they don't count."""
    source = _plain_binding(fg)
    return (
        source is not None
        and not str(source).startswith(('$', '#'))
        and g.getPropertyFromId(str(source), SDPropertyCategory.Input) is None
    )


def _driver_text(g: SDSBSCompGraph, fg: SDGraph) -> str:
    """What drives a parameter with this function, as a tool says it."""
    source = _plain_binding(fg)
    if source is None:
        return 'a function'
    if _reads_no_input(g, fg):
        return 'a function reading %r, which is not an input of this graph' % source
    if str(source).startswith(('$', '#')):
        return 'a function reading %r' % source
    return 'graph input %r' % source


def _refuse_no_input(g: SDSBSCompGraph, fg: SDGraph, node_id: str | None, param: str) -> None:
    """Raise if this function reads a name that is no graph input, or one of Designer's own: there is nothing to set
    instead."""
    source = _plain_binding(fg)
    if source is None:
        return
    if _reads_no_input(g, fg):
        raise RuntimeError(
            '%s.%s is driven by %s. Edit the function in Designer, or delete it first (deletePropertyGraph in code).'
            % (node_id, param, _driver_text(g, fg))
        )
    if str(source).startswith(('$', '#')):
        raise RuntimeError(
            '%s.%s is driven by %s. Edit the function in Designer.' % (node_id, param, _driver_text(g, fg))
        )


def _plain_binding(fg: SDGraph) -> Any:
    """The input id if this function graph is exactly what expose_param builds (one get_* node, its
    output), else None: a hand-written expression, a Pixel Processor function, an unfinished one."""
    nodes = list(fg.getNodes())
    if _has_output(fg) and len(nodes) == 1 and '::get_' in cast(SDDefinition, nodes[0].getDefinition()).getId():
        return fmt(nodes[0].getInputPropertyValueFromId('__constant__'))
    return None


def _connected_nodes(fg: SDGraph) -> list[SDNode]:
    """The nodes of this function graph that feed its output node (none without one)."""
    seen: dict[str, SDNode] = {}
    todo = list(fg.getOutputNodes())
    while todo:
        node = todo.pop()
        if node.getIdentifier() in seen:
            continue
        seen[node.getIdentifier()] = node
        for prop in node.getProperties(SDPropertyCategory.Input):
            if prop.isConnectable():
                # reported from the queried node's side: the input node is the other one
                todo.extend(cast(SDNode, c.getInputPropertyNode()) for c in node.getPropertyConnections(prop))
    return list(seen.values())


def _delete_function(node: SDNode, prop: SDProperty) -> None:
    """Delete a parameter's function graph. On a $ parameter that also switches its inheritance
    back to the node's default (measured on all six and an instance node, AGENTS.md), so the inheritance is put back; the caller sets the value after it."""
    compositing_node: Any = node  # the inheritance methods are on the compositing node's class
    method = compositing_node.getPropertyInheritanceMethod(prop) if prop.getId().startswith('$') else None
    node.deletePropertyGraph(prop)
    if method is not None:
        compositing_node.setPropertyInheritanceMethod(prop, method)


def _fx_map_functions(node: SDNode) -> list[tuple[str, SDProperty, SDGraph]]:
    """An FX-Map node's inner functions, which read its graph's inputs: (the inner node's id, parameter, function)."""
    if cast(SDDefinition, node.getDefinition()).getId() != 'sbs::compositing::fxmaps':
        return []
    fx_graph = cast(SDGraph, node.getReferencedResource())
    inner_nodes = fx_graph.getNodes() if fx_graph is not None else []
    return [(inner.getIdentifier(), prop, fg) for inner in inner_nodes for prop, fg in _functions_of(inner)]


def _is_processor_program(node: SDNode, prop: SDProperty) -> bool:
    """A Value or Pixel Processor's function, which is what the node computes: never a plain binding, whatever its size."""
    definition = cast(SDDefinition, node.getDefinition()).getId()
    return definition in ('sbs::compositing::valueprocessor', 'sbs::compositing::pixelprocessor') and prop.getId() in (
        'function',
        'perpixel',
    )


def _graph_parameter_reads(g: SDSBSCompGraph, connected_only: bool) -> dict[str, list[str]]:
    """input id -> ['graph.<parameter>'] for functions on the graph's own parameters. SDGraph has no getPropertyGraph,
    so they are read from the package's file, as last saved; a package never saved has none to read."""
    try:
        root = ET.parse(g.getPackage().getFilePath()).getroot()
    except (OSError, ET.ParseError):
        return {}
    reads: dict[str, list[str]] = {}
    for graph in root.iter('graph'):
        identifier = graph.find('identifier')
        base = graph.find('baseParameters')
        if identifier is None or identifier.get('v') != g.getIdentifier() or base is None:
            continue
        for prm in base:
            function = prm.find('paramValue/dynamicValue')
            name = prm.find('name')
            if function is None or name is None:
                continue
            nodes = {cast(ET.Element, n.find('uid')).get('v'): n for n in function.iter('paramNode')}
            if connected_only:
                wired: dict[Any, ET.Element] = {}
                rootnode = function.find('rootnode')
                todo = [rootnode.get('v')] if rootnode is not None else []
                while todo:
                    uid = todo.pop()
                    if uid in nodes and uid not in wired:
                        wired[uid] = nodes[uid]
                        todo.extend(c.get('v') for c in nodes[uid].findall('connections/connection/connRef'))
                nodes = wired
            for node in nodes.values():
                kind = node.find('function')
                if kind is not None and kind.get('v', '').startswith('get_'):
                    for read in node.iter('constantValueString'):
                        reads.setdefault(read.get('v', ''), []).append('graph.%s' % name.get('v'))
    return reads


def _functions_of(node: SDNode) -> list[tuple[SDProperty, SDGraph]]:
    """A node's parameters that have a function graph, with it."""
    found = []
    for prop in node.getProperties(SDPropertyCategory.Input):
        if prop.isConnectable():
            continue
        try:
            fg = node.getPropertyGraph(prop)
        except (Exception, APIException):
            fg = None
        if fg is not None:
            found.append((prop, fg))
    return found


def _input_users(g: SDSBSCompGraph, plain_only: bool = False, connected_only: bool = False) -> dict[Any, list[str]]:
    """input id -> ['node.param', ...] for parameters whose function has a get node naming it. With
    plain_only, only those that are nothing but that read; with connected_only, only get nodes that
    feed the function's output, which are the ones that affect the value. An FX-Map's functions count,
    as refs with its node's id and "(FX-Map)", never plain."""
    users: dict[Any, list[str]] = {}

    def read(fg: SDGraph, ref: str) -> None:
        for fnode in _connected_nodes(fg) if connected_only else fg.getNodes():
            if '::get_' in cast(SDDefinition, fnode.getDefinition()).getId():
                refs = users.setdefault(fmt(fnode.getInputPropertyValueFromId('__constant__')), [])
                if ref not in refs:  # one function can read an input twice
                    refs.append(ref)

    for node in g.getNodes():
        for prop, fg in _functions_of(node):
            ref = '%s.%s' % (node.getIdentifier(), prop.getId())
            if plain_only:
                name = _plain_binding(fg)
                if name is not None and not _is_processor_program(node, prop):
                    users.setdefault(name, []).append(ref)
            else:
                read(fg, ref)
        if not plain_only:  # never plain, so never unbound
            for inner_id, prop, fg in _fx_map_functions(node):
                read(fg, '%s (FX-Map) %s.%s' % (node.getIdentifier(), inner_id, prop.getId()))
    if not plain_only:  # never plain: nothing can unbind them through the API
        for input_id, refs in _graph_parameter_reads(g, connected_only).items():
            users.setdefault(input_id, []).extend(refs)
    return users


def list_graph_inputs(identifier: str | SDSBSCompGraph | None = None) -> None:
    g = find_graph(identifier)
    size_prop = cast(SDProperty, g.getPropertyFromId('$outputsize', SDPropertyCategory.Input))  # every graph has it
    method = g.getPropertyInheritanceMethod(size_prop)
    if method == method.__class__.RelativeToParent:
        print('size: overridable, default %d px' % g.getDefaultParentSize().x)
    else:
        print('size: fixed, log2 %s' % (fmt(g.getPropertyValue(size_prop)),))
    users = _input_users(g, connected_only=True)
    inputs = _graph_inputs(g)
    if not inputs:
        print('no exposed inputs')
    for inp in inputs:
        notes = []
        for key in ('label', 'min', 'max', 'step', 'group'):
            try:
                v = fmt(g.getPropertyAnnotationValueFromId(inp, key))
            except (Exception, APIException):
                v = None
            if v not in (None, ''):
                notes.append('%s=%r' % (key, v))
        print(
            '%s (%s) = %r  %s  drives: %s'
            % (
                inp.getId(),
                cast(SDType, inp.getType()).getId(),
                fmt(g.getPropertyValue(inp)),
                ' '.join(notes),
                ', '.join(users.get(inp.getId(), [])) or '-',
            )
        )


def remove_graph_input(identifier: str | SDSBSCompGraph | None, input_id: str) -> None:
    """Delete a graph input; parameters bound to it (as expose_param does) keep its current
    value as a constant. Refuses while another function (an expression, a Pixel Processor, one with
    no output node yet) still reads it, since removing the input would break that function."""
    g = _graph_to_edit(identifier)
    inp = g.getPropertyFromId(input_id, SDPropertyCategory.Input)
    if inp is None or input_id.startswith('$'):
        raise RuntimeError('graph has no exposed input %r' % input_id)
    plain = _input_users(g, plain_only=True).get(input_id, [])
    other = [ref for ref in _input_users(g).get(input_id, []) if ref not in plain]
    if other:
        reading = _input_users(g, connected_only=True).get(input_id, [])
        idle = [ref for ref in other if ref not in reading]
        raise RuntimeError(
            'input %r is read inside the functions of %s; edit those by hand first (nothing was changed)%s'
            % (
                input_id,
                ', '.join(other),
                '. %s: no effect on the output today, but a later edit could connect it' % ', '.join(idle)
                if idle
                else '',
            )
        )
    value = cast(SDValue, g.getPropertyValue(inp))  # an input always has a value
    # every value built before anything is deleted: an int set on an enum parameter is accepted whatever it is, and
    # leaves a value that can't be read back
    kept = []
    for ref in plain:
        nid, pid = ref.split('.', 1)
        # both found by _input_users just above
        node = cast(SDNode, g.getNodeFromId(nid))
        prop = cast(SDProperty, node.getPropertyFromId(pid, SDPropertyCategory.Input))
        same_type = cast(SDType, prop.getType()).getId() == cast(SDType, inp.getType()).getId()
        try:
            kept.append((ref, node, prop, value if same_type else _make_value(prop, fmt(value))))
        except (Exception, APIException) as e:
            raise RuntimeError(
                "%s can't keep input %r's value %r (%s); set a value it can hold first (nothing was changed)"
                % (ref, input_id, fmt(value), e)
            ) from e
    for ref, node, prop, new_value in kept:
        _delete_function(node, prop)
        try:
            node.setPropertyValue(prop, new_value)
        except (Exception, APIException) as e:
            print('WARNING: %s is at its default; could not set %r (%s)' % (ref, fmt(new_value), e))
        print('unbound %s (kept value %r)' % (ref, fmt(node.getPropertyValue(prop))))
    g.deleteProperty(inp)
    print('removed graph input', input_id)


def set_graph_size(identifier: str | SDSBSCompGraph | None, size_log2: int, overridable: bool = True) -> None:
    """overridable: size follows the parent (render_sbs size_log2 / $outputsize can change it),
    with 2^size_log2 as default. Otherwise the size is fixed."""
    from sd.api.sdbasetypes import int2
    from sd.api.sdproperty import SDPropertyInheritanceMethod
    from sd.api.sdvalueint2 import SDValueInt2

    g = _graph_to_edit(identifier)
    prop = cast(SDProperty, g.getPropertyFromId('$outputsize', SDPropertyCategory.Input))  # every graph has it
    if overridable:
        g.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.RelativeToParent)
        g.setDefaultParentSize(int2(2**size_log2, 2**size_log2))
        g.setPropertyValue(prop, SDValueInt2.sNew(int2(0, 0)))
        print('size: overridable, default %d px' % g.getDefaultParentSize().x)
    else:
        g.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
        g.setPropertyValue(prop, SDValueInt2.sNew(int2(size_log2, size_log2)))
        print('size: fixed %d px' % 2**size_log2)
