"""One-off edits: set_params, add_node, connect, disconnect, delete_nodes, import_bitmap."""

from .core import (
    _CURVE_KEY,
    _GRADIENT_KEY,
    MAX_SIZE_LOG2,
    APIException,
    Callable,
    Json,
    SDGraph,
    SDNode,
    SDProperty,
    SDPropertyCategory,
    SDSBSCompGraph,
    SDSBSCompNode,
    SDTypeArray,
    SDTypeEnum,
    SDTypeStruct,
    SDValue,
    SDValueArray,
    SDValueStruct,
    Sequence,
    Shown,
    TypedDict,
    _annotation_text,
    _default_output,
    _definition_id,
    _find_node,
    _finite,
    _graph_to_edit,
    _new_instance,
    _new_node,
    _nodes,
    _output_nodes,
    _output_note,
    _position,
    _refuse_bad_size,
    _size_property,
    _type,
    _xy,
    cast,
    fmt,
    node_kind,
    os,
    re,
)
from .describe import _library_graph
from .graph_inputs import (
    _PROGRAMS,
    _REPLACE,
    _driver_text,
    _driving_graph,
    _offset_note,
    _plain_binding,
    _refuse_bad_size_on_input,
    _refuse_no_input,
    _refuse_no_output,
)


def _target(g: SDSBSCompGraph, node_id: str | None) -> SDSBSCompNode | SDSBSCompGraph:
    """'graph' addresses the graph's own parameters, e.g. $outputsize (only that name: an empty id is
    no node, as in apply_edits' pre-check; REVIEW.md HLP-45)."""
    return g if node_id == 'graph' else _node(g, node_id)


def _node(g: SDSBSCompGraph, node_id: str | None) -> SDSBSCompNode:
    """A node of g, never the graph itself, for every tool that needs a node: 'graph' is no node, and
    taking it for one failed halfway (delete_nodes, move_nodes: REVIEW.md HLP-31), with an unclear
    error, or crashed Designer (open_graph's focusGraphNode: HLP-41). _target is for parameters."""
    return cast(SDSBSCompNode, _graph_node(g, node_id))  # the nodes of a compositing graph


def _graph_node(g: SDGraph, node_id: str | None) -> SDNode:
    """_node of any graph, a function graph's too: a node of g, never the graph itself."""
    node = _find_node(g, str(node_id)) if node_id not in (None, '') else None
    if node is None:
        raise RuntimeError('node %r not found in graph %s' % (node_id, g.getIdentifier()))
    return node


def _parameter(node: SDSBSCompNode, node_id: str | None, pid: str) -> SDProperty:
    """The parameter `pid` of a node: refused when the node has none of that id, or has an input connector of it."""
    prop = node.getPropertyFromId(pid, SDPropertyCategory.Input)
    if prop is None:
        raise RuntimeError('%r is not a parameter of node %s; see describe_node' % (pid, node_id))
    if prop.isConnectable():
        raise RuntimeError('%r is an input connector of node %s, not a parameter; see describe_node' % (pid, node_id))
    return prop


def _made_absolute(target: SDSBSCompNode | SDSBSCompGraph, prop: SDProperty) -> bool:
    """Makes a $ parameter of a node or the graph Absolute, every one but $randomseed alike. Measured for two: inherited,
    $format and $outputsize ignore a value (REVIEW.md HLP-24), and a function on $format is ignored, one on $outputsize
    read as an offset (GUIDE.md, Building a function graph). $randomseed counts while inherited too (added to its
    parent's seed), and only then follows the graph's seed and a .sbsar's control (REVIEW.md HLP-25, HLP-27). Returns
    whether it made `prop` Absolute."""
    from sd.api.sdproperty import SDPropertyInheritanceMethod

    pid = prop.getId()
    if not pid.startswith('$') or pid == '$randomseed' or not hasattr(target, 'setPropertyInheritanceMethod'):
        return False
    try:
        target.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
    except (Exception, APIException):
        return False
    return True


def _make_value(prop: SDProperty, value: Json | Shown, inherited: bool = False) -> SDValue:
    """Build the SDValue matching the property's type from a plain Python value. inherited: for a $outputsize, whether
    it stays inherited, which makes the value an offset (_refuse_bad_size).

    value is parsed JSON, or a value as fmt() shows it. A builder refuses a value it can't convert: as_bool and
    as_int with RuntimeError, float() and int() with TypeError or ValueError. A string parameter takes any value, as
    str() gives it (REVIEW.md HLP-183). A bool parameter takes a value that isn't a string by its truth: [false] gives
    True (REVIEW.md HLP-185)."""
    from sd.api.sdbasetypes import ColorRGBA, float2, float3, float4, int2, int3, int4
    from sd.api.sdvaluebool import SDValueBool
    from sd.api.sdvaluecolorrgba import SDValueColorRGBA
    from sd.api.sdvalueenum import SDValueEnum
    from sd.api.sdvaluefloat import SDValueFloat
    from sd.api.sdvaluefloat2 import SDValueFloat2
    from sd.api.sdvaluefloat3 import SDValueFloat3
    from sd.api.sdvaluefloat4 import SDValueFloat4
    from sd.api.sdvalueint import SDValueInt
    from sd.api.sdvalueint2 import SDValueInt2
    from sd.api.sdvalueint3 import SDValueInt3
    from sd.api.sdvalueint4 import SDValueInt4
    from sd.api.sdvaluestring import SDValueString

    ptype = _type(prop)
    if isinstance(ptype, SDTypeArray):
        item = cast(SDTypeStruct, ptype.getItemType())  # an array parameter's items are structs (keys)
        if item.getId() in _KEY_READERS:
            return _new_keys(prop, item, value)
    if isinstance(ptype, SDTypeEnum):
        options = [(e.getId(), cast(SDValueEnum, e.getDefaultValue())) for e in ptype.getEnumerators()]
        for eid, ev in options:
            if (
                value == eid
                or (not isinstance(value, bool) and value == ev.get())
                or (isinstance(value, str) and value.strip() == str(ev.get()))
            ):
                return ev
        raise RuntimeError(
            '%s: %r is not one of %s'
            % (prop.getId(), value, ', '.join('%s=%s' % (eid, ev.get()) for eid, ev in options))
        )
    tid = ptype.getId()
    # the items of a list, none for another value. The cast: their type is what the builders convert (the docstring)
    seq = cast(list[str | float], list(value)) if isinstance(value, (list, tuple)) else []

    def as_bool(v: Json | Shown) -> bool:
        if isinstance(v, str):
            if v.strip().lower() not in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
                raise RuntimeError('%s expects true or false, got %r' % (prop.getId(), v))
            return v.strip().lower() in ('true', '1', 'yes', 'on')
        return bool(v)

    def as_int(v: str | float) -> int:
        if isinstance(v, float) and not v.is_integer():
            raise RuntimeError('%s is an integer parameter; %r is not a whole number' % (prop.getId(), v))
        return int(v)

    # the casts: these conversions take a number, a bool or a string (the docstring)
    builders: dict[str, Callable[[], SDValue]] = {
        'bool': lambda: SDValueBool.sNew(as_bool(value)),
        'int': lambda: SDValueInt.sNew(as_int(cast(str | float, value))),
        'float': lambda: SDValueFloat.sNew(float(cast(str | float, value))),
        'string': lambda: SDValueString.sNew(str(value)),
        'float2': lambda: SDValueFloat2.sNew(float2(*map(float, seq))),
        'float3': lambda: SDValueFloat3.sNew(float3(*map(float, seq))),
        'float4': lambda: SDValueFloat4.sNew(float4(*map(float, seq))),
        'int2': lambda: SDValueInt2.sNew(int2(*map(as_int, seq))),
        'int3': lambda: SDValueInt3.sNew(int3(*map(as_int, seq))),
        'int4': lambda: SDValueInt4.sNew(int4(*map(as_int, seq))),
        'ColorRGBA': lambda: SDValueColorRGBA.sNew(ColorRGBA(*map(float, ([*seq, 1.0])[:4]))),
    }
    if tid not in builders:
        raise RuntimeError('%s: unsupported parameter type %s' % (prop.getId(), tid))
    if tid[-1].isdigit() and len(seq) != int(tid[-1]):
        raise RuntimeError('%s expects %s values' % (prop.getId(), tid[-1]))
    if tid == 'ColorRGBA' and len(seq) not in (3, 4):
        raise RuntimeError('%s expects a colour [r, g, b] or [r, g, b, a]' % prop.getId())
    if prop.getId() == '$outputsize' and seq:  # as the builder converts them, so numbers sent as strings count
        _refuse_bad_size('$outputsize', [as_int(v) for v in seq], value, inherited)
    return builders[tid]()


class _GradientKey(TypedDict):
    """A Gradient Map key as _gradient_key checks it: its members, by id."""

    position: float
    value: list[float]
    midpoint: float


class _CurvePoint(TypedDict):
    """A Curve point as _curve_point checks it: its members, by id (its flags keep a new key's False)."""

    position: list[float]
    left: list[float]
    right: list[float]


type _GivenKey = _GradientKey | _CurvePoint


def _new_keys(prop: SDProperty, item: SDTypeStruct, value: Json | Shown) -> SDValueArray:
    """A Gradient Map's keys or a Curve's points, an array of `item` structs, from `value` as _given_keys takes it.
    Designer takes an array of another item type, raising nothing, and converts it (GUIDE.md, Gradient Map keys and
    Curve points), so each key is built of the parameter's own item type. Members left out keep a new key's value."""
    members = {m.getId(): m for m in item.getMembers()}
    keys = cast(SDValueArray, SDValueArray.sNew(item, 0))  # the casts: sNew's type allows None
    for given in _given_keys(prop.getId(), item.getId(), value):
        # a curve point's isLocked and broken flags are left as a new key has them, False: every point set comes out
        # unlocked and unbroken, as the set text says (the lead's choice, the user, 2026-11-22)
        key = cast(SDValueStruct, SDValueStruct.sNew(item))
        for member_id, member_value in given.items():
            # the cast: a TypedDict's items() gives its values as object; each is a float or a list of floats
            key.setPropertyValue(members[member_id], _make_value(members[member_id], cast(Json, member_value)))
        keys.pushBack(key)
    return keys


_UNIT = (0.0, 1.0)  # a key's position and midpoint, and a point's x


def _number(where: str, v: Json | Shown, bounds: tuple[float, float] | None = None) -> float:
    """`v` as a float, a number or one written as a string (as the other parameters take them), within `bounds` when
    given; refused naming `where` otherwise, and so is one that isn't finite (_finite). A bool is no number here: True
    would be a position of 1."""
    shown = '%s is a number%s, not %r' % (where, ' from %g to %g' % bounds if bounds else '', v)
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        raise RuntimeError(shown)
    try:
        number = float(v)
    except ValueError:
        raise RuntimeError(shown) from None
    if not _finite(number) or (bounds and not bounds[0] <= number <= bounds[1]):
        raise RuntimeError(shown)
    return number


def _given_keys(pid: str, item_id: str, value: Json | Shown) -> list[_GivenKey]:
    """The keys given for the array parameter `pid` of `item_id` structs, each as {member id: its value}, every key
    checked before any is built; a mistake names its key, `pid[i]` (_gradient_key, _curve_point). fmt reads them back
    in this form (_shown_keys). An empty list gives no keys."""
    shape, read = _KEY_READERS[item_id]
    if not isinstance(value, (list, tuple)):
        raise RuntimeError('%s takes a list of %s, not %r' % (pid, shape, value))
    return [read('%s[%d]' % (pid, i), key) for i, key in enumerate(value)]


def _gradient_key(where: str, key: Json | Shown) -> _GradientKey:
    """A Gradient Map key, [position, [r, g, b(, a)]] or [position, [r, g, b(, a)], midpoint]: position and midpoint
    from 0 to 1, the midpoint 0 when left out, as a new key has. A position below 0 makes every pixel the last key's
    colour (measured), and one above 1 is no grey of a 0..1 input."""
    if not isinstance(key, (list, tuple)) or len(key) not in (2, 3):
        raise RuntimeError(
            '%s: a key is [position, [r, g, b(, a)]] or [position, [r, g, b(, a)], midpoint], not %r' % (where, key)
        )
    colour = key[1]
    wrong = '%s: colour is [r, g, b] or [r, g, b, a], not %r' % (where, colour)
    if not isinstance(colour, (list, tuple)) or len(colour) not in (3, 4):
        raise RuntimeError(wrong)
    try:
        rgba = [_number(where, c) for c in colour]
    except RuntimeError:
        raise RuntimeError(wrong) from None
    return {
        # above 1 is refused, though Designer computes it, to catch a 0..255 or percent mistake (the lead's choice, the
        # user, 2026-11-22)
        'position': _number(where + ': position', key[0], _UNIT),
        'value': rgba,
        'midpoint': _number(where + ': midpoint', key[2], _UNIT) if len(key) == 3 else 0.0,
    }


def _curve_point(where: str, key: Json | Shown) -> _CurvePoint:
    """A Curve point: [x, y], its handles put on the point, which joins the points by straight lines (a new key's
    handles, at (0, 0), bend the curve: measured); or [[x, y], [left x, y], [right x, y]], the handles absolute points.
    x from 0 to 1, as one below 0 computes a wrong value at 0 (measured); y any number."""
    wrong = '%s: a point is [x, y] or [[x, y], [left x, y], [right x, y]], not %r' % (where, key)
    if not isinstance(key, (list, tuple)) or len(key) not in (2, 3):
        raise RuntimeError(wrong)
    handled = len(key) == 3
    point = key[0] if handled else key
    if not isinstance(point, (list, tuple)) or len(point) != 2 or any(isinstance(c, (list, tuple)) for c in point):
        raise RuntimeError(wrong)
    # x above 1 is refused, to catch a 0..255 or percent mistake (the lead's choice, the user, 2026-11-22)
    position = [_number(where + ': x', point[0], _UNIT), _number(where + ': y', point[1])]
    if not handled:
        return {'position': position, 'left': position, 'right': position}
    handles = [
        [*_position(h, '%s: the %s handle' % (where, side))] for side, h in zip(('left', 'right'), key[1:], strict=True)
    ]
    return {'position': position, 'left': handles[0], 'right': handles[1]}


# what each item type's list holds, as a refusal names it, and the function reading one of its keys
_KEY_READERS: dict[str, tuple[str, Callable[[str, Json | Shown], _GivenKey]]] = {
    _GRADIENT_KEY: ('keys, [[position, [r, g, b(, a)]], ...], an optional midpoint third', _gradient_key),
    _CURVE_KEY: ('points, [[x, y], ...], each with optional handles [[x, y], [left x, y], [right x, y]]', _curve_point),
}


def set_params(graph_id: str | SDSBSCompGraph | None, node_id: str | None, params: dict[str, Json]) -> None:
    from sd.api.sdproperty import SDPropertyInheritanceMethod

    g = _graph_to_edit(graph_id)
    target = _target(g, node_id)
    is_graph = node_id == 'graph'
    checked = []  # every value is checked before any is set
    for pid, value in params.items():
        prop = target.getPropertyFromId(pid, SDPropertyCategory.Input)
        if prop is None:
            raise RuntimeError('no parameter %r on %s; see describe_node' % (pid, node_id or 'graph'))
        if prop.isConnectable():
            raise RuntimeError('%r is an input connector; connect to it (a connect op)' % pid)
        if (
            is_graph
            and pid == '$outputsize'
            and g.getPropertyInheritanceMethod(prop) != SDPropertyInheritanceMethod.Absolute
        ):
            # on an overridable graph the value is an offset from the parent size, and making it
            # Absolute would ignore render size overrides from then on (REVIEW.md HLP-22)
            raise RuntimeError(
                "the graph's size follows its parent (overridable); use set_graph_size "
                '(overridable=True keeps it so, False fixes it)'
            )
        driven = _driving_graph(cast(SDNode, target), prop) if not is_graph else None
        if driven is not None:
            # setting it would cut the parameter loose from its graph input or function
            _refuse_no_output(driven, node_id, pid)
            _refuse_no_input(g, driven, node_id, pid)
            if _plain_binding(driven) is None:  # a function, which no graph input stands for (REVIEW.md HLP-230)
                raise RuntimeError('%s.%s is driven by a function; %s' % (node_id, pid, _REPLACE))
            raise RuntimeError(
                "%s.%s is driven by %s; set that instead (a set op on node 'graph')%s"
                % (node_id, pid, _driver_text(g, driven), _offset_note(target, prop))
            )
        _refuse_bad_size_on_input(target, prop, [value])
        checked.append((pid, prop, _make_value(prop, value)))
    for pid, prop, new_value in checked:
        before = fmt(target.getPropertyValue(prop))
        _made_absolute(target, prop)  # the graph's $outputsize gets here only when already Absolute (REVIEW.md HLP-22)
        target.setPropertyValue(prop, new_value)
        print('%s.%s: %r -> %r' % (node_id or 'graph', pid, before, fmt(target.getPropertyValue(prop))))


def atomic_definition_ids(g: SDSBSCompGraph) -> set[str]:
    """The ids of the atomic nodes `g` takes. sd's getNodeDefinitions() gives None when Designer sets no array, as
    getDefinitions() does (REVIEW.md HLP-248)."""
    return {d.getId() for d in g.getNodeDefinitions() or []}


def _resolve_definition(g: SDSBSCompGraph, definition: str) -> SDNode:
    atomic_id = definition if definition.startswith('sbs::') else 'sbs::compositing::' + definition
    # Validate first: newNode() with an unknown id can hang Designer 15
    if atomic_id in atomic_definition_ids(g):
        return _new_node(g, atomic_id)
    res = _library_graph(definition)
    return _new_instance(g, res)  # the resource was found just above


def _place(node: SDNode, position: Sequence[float] | None, existing: list[SDNode]) -> Sequence[float]:
    from sd.api.sdbasetypes import float2

    if position is None:
        # to the right of everything, so it doesn't land on top of existing nodes
        points = [_xy(n.getPosition()) for n in existing] or [(0.0, 0.0)]
        xs, ys = [x for x, _ in points], [y for _, y in points]
        position = (max(xs) + 200.0, sum(ys) / len(ys))
    node.setPosition(float2(float(position[0]), float(position[1])))
    return position


_OUTPUT_DEFINITION = 'sbs::compositing::output'
# the usual names, so 'basecolor' still gives the tag Designer's own graphs use; any other name is kept as given
_USAGES = {
    name.lower(): name
    for name in (
        'ambientOcclusion',
        'anisotropyAngle',
        'anisotropyLevel',
        'baseColor',
        'curvature',
        'diffuse',
        'emissive',
        'glossiness',
        'height',
        'mask',
        'metallic',
        'normal',
        'opacity',
        'roughness',
        'specular',
        'specularLevel',
    )
}
_SRGB_USAGES = {'baseColor', 'diffuse', 'emissive', 'specular'}  # colour maps; the rest hold data


def _check_output_name(g: SDSBSCompGraph, node_id: str | None, identifier: str) -> None:
    """Designer lets two outputs share an identifier (measured), and export_outputs then refuses them. By case too:
    those file names are one file on a Mac or on Windows."""
    for other in _output_nodes(g):
        name = _annotation_text(other, 'identifier')
        if other.getIdentifier() != node_id and name is not None and name.lower() == identifier.lower():
            raise RuntimeError('output node %s already has the identifier %r' % (other.getIdentifier(), name))


def set_output_tags(
    g: SDSBSCompGraph,
    node: SDNode,
    identifier: str | None,
    label: str | None,
    usage: str | None,
    warn_rename: bool = False,
) -> None:
    """Set what was given of an output node's annotations; a usage replaces the tags it had. The values were checked
    in _check_batch, since Designer takes any: it rewrites an identifier's other characters and never checks a usage.
    warn_rename: the output existed before this batch, so another graph may be using it."""
    from sd.api.sdtypeusage import SDTypeUsage
    from sd.api.sdusage import SDUsage
    from sd.api.sdvaluearray import SDValueArray
    from sd.api.sdvaluestring import SDValueString
    from sd.api.sdvalueusage import SDValueUsage

    said = []
    if identifier is not None:
        _check_output_name(g, node.getIdentifier(), identifier)
        old = _annotation_text(node, 'identifier')
        node.setAnnotationPropertyValueFromId('identifier', SDValueString.sNew(identifier))
        said.append('identifier %r' % identifier)
    if label is not None:
        node.setAnnotationPropertyValueFromId('label', SDValueString.sNew(label))
        said.append('label %r' % label)
    if usage is not None:
        name = _USAGES.get(usage.lower(), usage)
        # the casts: sNew's type allows None, and the calls below need a value
        tags = cast(SDValueArray, SDValueArray.sNew(SDTypeUsage.sNew(), 0))
        # RGBA as in nearly every tag of Designer's own graphs, whatever the map holds
        tags.pushBack(
            cast(
                SDValueUsage,
                SDValueUsage.sNew(SDUsage.sNew(name, 'RGBA', 'sRGB' if name in _SRGB_USAGES else 'Linear')),
            )
        )
        node.setAnnotationPropertyValueFromId('usages', tags)
        said.append('usage %s' % name)
    print('output %s: %s' % (node.getIdentifier(), ', '.join(said)))
    if warn_rename and identifier is not None and old != identifier:
        print(
            'Tell the user: output %r was renamed %r. A graph using it that is open follows, but one that is closed keeps '
            'the old connector and computes black, with no error. To repair one: a new instance of this graph, wired from '
            '%r, with its parameters set again; renaming back does not repair it.' % (old, identifier, identifier)
        )


def add_node(
    graph_id: str | SDSBSCompGraph | None,
    definition: str,
    position: Sequence[float] | None = None,
    params: dict[str, Json] | None = None,
) -> str:
    if position is not None:
        position = _position(position)
    g = _graph_to_edit(graph_id)
    existing = _nodes(g)
    node = _resolve_definition(g, definition)
    position = _place(node, position, existing)
    print('added %s %s @(%d,%d)' % (node.getIdentifier(), node_kind(node), position[0], position[1]))
    print('outputs:', [p.getId() for p in node.getProperties(SDPropertyCategory.Output)])
    if params:
        try:
            set_params(graph_id, node.getIdentifier(), params)
        except (Exception, APIException) as e:
            # a bad value refuses the whole add: no half-made node left for a retry to duplicate
            # (set_params checks every value before setting any; REVIEW.md HLP-30)
            try:
                g.deleteNode(node)
            except (Exception, APIException) as removal:  # say both (REVIEW.md HLP-37)
                # what is left, on a line of its own, which the server shows only if the call's rollback didn't take
                # it back (server_tools/core.py, _failure; REVIEW.md HLP-256)
                print(
                    'KEPT=node %s could not be removed again (%s): delete it by hand' % (node.getIdentifier(), removal)
                )
                raise RuntimeError(str(e)) from removal
            raise RuntimeError('%s (the node was not added)' % e) from e
    return node.getIdentifier()


def connect(
    graph_id: str | SDSBSCompGraph | None,
    from_node: str | None,
    to_node: str | None,
    to_input: str,
    from_output: str | None = None,
) -> None:
    g = _graph_to_edit(graph_id)
    src, dst = _node(g, from_node), _node(g, to_node)  # nodes, never the graph (REVIEW.md HLP-41)
    outs = [p.getId() for p in src.getProperties(SDPropertyCategory.Output)]
    out_id, how = from_output, None
    if not from_output and outs:
        out_id, how = _default_output(src, outs)
    if out_id not in outs:
        raise RuntimeError('output %r not on node %s; outputs: %s' % (out_id, from_node, outs))
    made = _input_value(src, from_node, str(out_id), dst, to_node, to_input) if to_input.startswith('#') else ''
    ins = [p.getId() for p in dst.getProperties(SDPropertyCategory.Input) if p.isConnectable()]
    if to_input not in ins:
        raise RuntimeError(
            'input %r not on node %s; connectors: %s%s' % (to_input, to_node, ins, _later_image(dst, to_input))
        )
    src.newPropertyConnectionFromId(out_id, dst, to_input)
    note = ' (%s)' % _output_note(how) if how and len(outs) > 1 else ''
    print('connected %s.%s -> %s.%s%s%s' % (from_node, out_id, to_node, to_input, note, made))


# the types of a node's input values: those of a value, as a Value Processor gives it (server_tools/functions.py VALUE)
_VALUE_TYPES = ('bool', 'int', 'int2', 'int3', 'int4', 'float', 'float2', 'float3', 'float4')


def _input_value(src: SDNode, from_node: str | None, out_id: str, dst: SDNode, to_node: str | None, name: str) -> str:
    """Makes `dst`'s input value `name` (a `#`, a letter, then letters, digits or _, as set_function reads it) of the
    type of `src`'s output `out_id`, unless `dst` has it already. Returns what connect's line adds. Refuses an output
    that isn't a value, such as an image, and an input value of another type: Designer connects either, raising
    nothing, and a function reading it computes a wrong value (GUIDE.md, Building a function graph)."""
    if not re.fullmatch(r'#[A-Za-z][A-Za-z0-9_]*', name):
        raise RuntimeError(
            'input value %r: a # and a letter, then letters, digits or _, the name set_function reads it by' % name
        )
    given = _type(cast(SDProperty, src.getPropertyFromId(out_id, SDPropertyCategory.Output)))
    if given.getId() not in _VALUE_TYPES:
        raise RuntimeError(
            '%s.%s gives %s, not a value: an input value takes a bool, an int to int4 or a float to float4, as a Value '
            'Processor gives' % (from_node, out_id, given.getId())
        )
    held = dst.getPropertyFromId(name, SDPropertyCategory.Input)
    if held is None:
        dst.newProperty(name, given, SDPropertyCategory.Input)
        return '; made %s, an input value of type %s' % (name, given.getId())
    if _type(held).getId() != given.getId():
        raise RuntimeError(
            '%s.%s is an input value of type %s, and %s.%s gives type %s: connect it into another #name'
            % (to_node, name, _type(held).getId(), from_node, out_id, given.getId())
        )
    return ''


def _image_inputs(node: SDNode) -> list[SDProperty]:
    """A Pixel or Value Processor's input images, as Designer lists them: input, input:1, input:2..., the last one
    empty, after the last one connected (GUIDE.md, A processor's input images)."""
    listed = [
        p
        for p in node.getProperties(SDPropertyCategory.Input)
        if p.isConnectable() and re.fullmatch(r'input(:[1-9]\d*)?', p.getId())
    ]
    return sorted(listed, key=lambda p: int(p.getId().partition(':')[2] or 0))


def _later_image(node: SDNode, input_id: str) -> str:
    """What connect's refusal adds for an input image `input_id` a processor doesn't list yet: the one to connect
    first, since Designer lists input:N once input:N-1 has a connection; '' for any other connector."""
    # input:1 and after: no processor lists input:0 or input:01 (REVIEW.md HLP-240)
    if _definition_id(node) not in _PROGRAMS or not re.fullmatch(r'input:[1-9]\d*', input_id):
        return ''
    return (
        ': a Pixel or Value Processor lists input:1, input:2... one at a time, each once the one before it has a '
        'connection: connect an image into %s first' % _image_inputs(node)[-1].getId()
    )


def disconnect(graph_id: str | SDSBSCompGraph | None, node_id: str | None, input_id: str) -> None:
    g = _graph_to_edit(graph_id)
    node = _node(g, node_id)
    prop = node.getPropertyFromId(input_id, SDPropertyCategory.Input)
    if prop is None or not prop.isConnectable():
        raise RuntimeError('%r is not an input connector on node %s' % (input_id, node_id))
    count = len(node.getPropertyConnections(prop))
    node.deletePropertyConnections(prop)
    print('removed %d connection(s) into %s.%s' % (count, node_id, input_id))


def delete_nodes(graph_id: str | SDSBSCompGraph | None, node_ids: list[str]) -> None:
    g = _graph_to_edit(graph_id)
    nodes = [(nid, _node(g, nid)) for nid in node_ids]  # every id found before anything is deleted
    for nid, node in nodes:
        kind = node_kind(node)
        g.deleteNode(node)
        print('deleted %s %s' % (nid, kind))


def import_bitmap(
    graph_id: str | SDSBSCompGraph | None,
    path: str,
    embed: str = 'link',
    position: Sequence[float] | None = None,
    name: str | None = None,
) -> str:
    """Bitmap node for an image file. embed: 'link' (reference the file where it is) or 'copy'
    (copy into <package>.resources/, or a temp folder until the package is saved).
    Embedding into the .sbs itself isn't supported by the API (NotSupported)."""
    from sd.api.sdresource import EmbedMethod
    from sd.api.sdresourcebitmap import SDResourceBitmap
    from sd.api.sdvalueint2 import SDValueInt2

    if position is not None:
        position = _position(position)
    methods = {'link': EmbedMethod.Linked, 'copy': EmbedMethod.CopiedAndLinked}
    if embed not in methods:
        raise RuntimeError('embed must be one of %s' % ', '.join(methods))
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(path):
        raise RuntimeError('no such file: %s' % path)
    g = _graph_to_edit(graph_id)
    pkg = g.getPackage()
    existing = _nodes(g)
    res = None
    if embed == 'link' and not name:
        # reuse a resource that already links this file instead of adding probe_1, probe_2...
        for r in pkg.getChildrenResources(True):
            if (
                isinstance(r, SDResourceBitmap)
                and r.getEmbedMethod() == EmbedMethod.Linked
                and os.path.normpath(r.getFilePath() or '') == path
            ):
                res = r
                print('reusing bitmap resource', r.getIdentifier())
                break
    if res is None:
        res = SDResourceBitmap.sNewFromFile(pkg, path, methods[embed])
        if res is None:
            raise RuntimeError('Designer could not load %s as a bitmap' % path)
        if name:
            res.setIdentifier(name)
        print('bitmap resource %s (%s): %s' % (res.getIdentifier(), embed, res.getFilePath()))
    node = _new_instance(g, res)  # of the resource made or found just above
    position = _place(node, position, existing)
    size = cast(SDValueInt2, node.getPropertyValue(_size_property(node)))
    sides = size.get()
    # a side's log2 above 13 still computes 8192 px, the image shrunk to it ("designer facts"; REVIEW.md SRV-239)
    largest = (
        '; a side computes 8192 px at most (%d): the image is shrunk to it' % MAX_SIZE_LOG2
        if max(sides.x, sides.y) > MAX_SIZE_LOG2
        else ''
    )
    print(
        'added %s bitmap @(%d,%d), size %s (log2 of each side, rounded up: the image is stretched to it%s; set '
        '$outputsize to change)' % (node.getIdentifier(), position[0], position[1], fmt(size), largest)
    )
    print('outputs:', [p.getId() for p in node.getProperties(SDPropertyCategory.Output)])
    return node.getIdentifier()
