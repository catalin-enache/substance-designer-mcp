"""Exposed parameters: expose_param, list_graph_inputs, remove_graph_input, set_graph_size."""

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

    g = find_graph(identifier)
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
    if _driving_graph(node, prop) is not None:
        raise RuntimeError(
            '%s.%s is already driven by a function; replacing it would lose that logic. '
            'Edit the function by hand, or remove its graph input first.' % (node_id, param)
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
                node.deletePropertyGraph(prop)
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
    """The function graph driving a parameter's value, or None. An empty function graph (no
    nodes) drives nothing, so the stored value counts, as expose_param has always assumed."""
    try:
        fg: SDGraph | None = node.getPropertyGraph(prop)
    except (Exception, APIException):
        return None
    if fg is None or not len(fg.getNodes()):
        return None
    return fg


def _plain_binding(fg: SDGraph) -> Any:
    """The input id if this function graph is exactly what expose_param builds (one get_* node),
    else None: a hand-written expression or a Pixel Processor function."""
    nodes = list(fg.getNodes())
    if len(nodes) == 1 and '::get_' in cast(SDDefinition, nodes[0].getDefinition()).getId():
        return fmt(nodes[0].getInputPropertyValueFromId('__constant__'))
    return None


def _input_users(g: SDSBSCompGraph, plain_only: bool = False) -> dict[Any, list[str]]:
    """input id -> ['node.param', ...] for parameters whose function reads it (with plain_only,
    only those that are nothing but that read)."""
    users: dict[Any, list[str]] = {}
    for node in g.getNodes():
        for prop in node.getProperties(SDPropertyCategory.Input):
            if prop.isConnectable():
                continue
            try:
                fg = node.getPropertyGraph(prop)
            except (Exception, APIException):
                fg = None
            if fg is None:
                continue
            ref = '%s.%s' % (node.getIdentifier(), prop.getId())
            if plain_only:
                name = _plain_binding(fg)
                if name is not None:
                    users.setdefault(name, []).append(ref)
                continue
            for fnode in fg.getNodes():
                if '::get_' in cast(SDDefinition, fnode.getDefinition()).getId():
                    users.setdefault(fmt(fnode.getInputPropertyValueFromId('__constant__')), []).append(ref)
    return users


def list_graph_inputs(identifier: str | SDSBSCompGraph | None = None) -> None:
    g = find_graph(identifier)
    size_prop = cast(SDProperty, g.getPropertyFromId('$outputsize', SDPropertyCategory.Input))  # every graph has it
    method = g.getPropertyInheritanceMethod(size_prop)
    if method == method.__class__.RelativeToParent:
        print('size: overridable, default %d px' % g.getDefaultParentSize().x)
    else:
        print('size: fixed, log2 %s' % (fmt(g.getPropertyValue(size_prop)),))
    users = _input_users(g)
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
    value as a constant. Refuses while a larger function (an expression, a Pixel Processor) still
    reads it, since removing the input would break that function."""
    g = find_graph(identifier)
    inp = g.getPropertyFromId(input_id, SDPropertyCategory.Input)
    if inp is None or input_id.startswith('$'):
        raise RuntimeError('graph has no exposed input %r' % input_id)
    plain = _input_users(g, plain_only=True).get(input_id, [])
    other = [ref for ref in _input_users(g).get(input_id, []) if ref not in plain]
    if other:
        raise RuntimeError(
            'input %r is read inside the functions of %s; edit those by hand first '
            '(nothing was changed)' % (input_id, ', '.join(other))
        )
    value = cast(SDValue, g.getPropertyValue(inp))  # an input always has a value
    for ref in plain:
        nid, pid = ref.split('.', 1)
        # both found by _input_users just above
        node = cast(SDNode, g.getNodeFromId(nid))
        prop = cast(SDProperty, node.getPropertyFromId(pid, SDPropertyCategory.Input))
        node.deletePropertyGraph(prop)
        try:
            node.setPropertyValue(prop, value)
        except (Exception, APIException):
            try:  # an int input bound to an enum parameter
                node.setPropertyValue(prop, _make_value(prop, fmt(value)))
            except (Exception, APIException) as e:
                print('WARNING: %s keeps its previous value; could not set %r (%s)' % (ref, fmt(value), e))
        print('unbound %s (kept value %r)' % (ref, fmt(node.getPropertyValue(prop))))
    g.deleteProperty(inp)
    print('removed graph input', input_id)


def set_graph_size(identifier: str | SDSBSCompGraph | None, size_log2: int, overridable: bool = True) -> None:
    """overridable: size follows the parent (render_sbs size_log2 / $outputsize can change it),
    with 2^size_log2 as default. Otherwise the size is fixed."""
    from sd.api.sdbasetypes import int2
    from sd.api.sdproperty import SDPropertyInheritanceMethod
    from sd.api.sdvalueint2 import SDValueInt2

    g = find_graph(identifier)
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
