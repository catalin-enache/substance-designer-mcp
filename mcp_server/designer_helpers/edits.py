"""One-off edits: set_params, add_node, connect, disconnect, delete_nodes, import_bitmap."""

from .core import (
    Any,
    APIException,
    Callable,
    SDNode,
    SDProperty,
    SDPropertyCategory,
    SDSBSCompGraph,
    SDSBSCompNode,
    SDType,
    SDTypeEnum,
    SDValue,
    Sequence,
    cast,
    find_graph,
    fmt,
    node_kind,
    os,
)
from .describe import _library_path, _load_library
from .graph_inputs import _driving_graph, _plain_binding


def _target(g: SDSBSCompGraph, node_id: str | None) -> SDSBSCompNode | SDSBSCompGraph:
    """'graph' (or empty) addresses the graph's own parameters, e.g. $outputsize."""
    if node_id in (None, '', 'graph'):
        return g
    node = g.getNodeFromId(str(node_id))
    if node is None:
        raise RuntimeError('node %s not found in graph %s' % (node_id, g.getIdentifier()))
    return cast(SDSBSCompNode, node)  # the nodes of a compositing graph


def _node(g: SDSBSCompGraph, node_id: str | None) -> SDNode:
    """A node of g, never the graph itself, for every tool that needs a node: 'graph' is no node, and
    taking it for one failed halfway (delete_nodes, move_nodes: REVIEW.md HLP-31), with an unclear
    error, or crashed Designer (open_graph's focusGraphNode: HLP-41). _target is for parameters."""
    # annotated: sd's star imports in import cycles can leave its return types Any for mypy
    node: SDNode | None = g.getNodeFromId(str(node_id)) if node_id not in (None, '') else None
    if node is None:
        raise RuntimeError('node %r not found in graph %s' % (node_id, g.getIdentifier()))
    return node


def _make_value(prop: SDProperty, value: Any) -> SDValue:
    """Build the SDValue matching the property's type from a plain Python value."""
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

    ptype = cast(SDType, prop.getType())  # a parameter always has a type
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
    # a list or None; the builders below run only after the length checks
    seq: Any = list(value) if isinstance(value, (list, tuple)) else None

    def as_bool(v: Any) -> bool:
        if isinstance(v, str):
            if v.strip().lower() not in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
                raise RuntimeError('%s expects true or false, got %r' % (prop.getId(), v))
            return v.strip().lower() in ('true', '1', 'yes', 'on')
        return bool(v)

    def as_int(v: Any) -> int:
        if isinstance(v, float) and not v.is_integer():
            raise RuntimeError('%s is an integer parameter; %r is not a whole number' % (prop.getId(), v))
        return int(v)

    builders: dict[str, Callable[[], SDValue]] = {
        'bool': lambda: SDValueBool.sNew(as_bool(value)),
        'int': lambda: SDValueInt.sNew(as_int(value)),
        'float': lambda: SDValueFloat.sNew(float(value)),
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
    if tid[-1].isdigit() and (seq is None or len(seq) != int(tid[-1])):
        raise RuntimeError('%s expects %s values' % (prop.getId(), tid[-1]))
    if tid == 'ColorRGBA' and (seq is None or len(seq) not in (3, 4)):
        raise RuntimeError('%s expects a colour [r, g, b] or [r, g, b, a]' % prop.getId())
    return builders[tid]()


def set_params(graph_id: str | SDSBSCompGraph | None, node_id: str | None, params: dict[str, Any]) -> None:
    from sd.api.sdproperty import SDPropertyInheritanceMethod

    g = find_graph(graph_id)
    target = _target(g, node_id)
    is_graph = node_id in (None, '', 'graph')
    checked = []  # every value is checked before any is set
    for pid, value in params.items():
        prop = target.getPropertyFromId(pid, SDPropertyCategory.Input)
        if prop is None:
            raise RuntimeError('no parameter %r on %s; see describe_node' % (pid, node_id or 'graph'))
        if prop.isConnectable():
            raise RuntimeError('%r is an input connector; use connect' % pid)
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
            source = _plain_binding(driven)
            raise RuntimeError(
                "%s.%s is driven by %s; set that instead (set_params node_id='graph')"
                % (node_id, pid, 'graph input %r' % source if source else 'a function')
            )
        checked.append((pid, prop, _make_value(prop, value)))
    for pid, prop, new_value in checked:
        before = fmt(target.getPropertyValue(prop))
        if pid.startswith('$') and pid != '$randomseed' and hasattr(target, 'setPropertyInheritanceMethod'):
            # $outputsize/$format etc. only take effect when not inherited, on a node or the graph
            # (REVIEW.md HLP-24); the graph's $outputsize gets here only when already Absolute (HLP-22).
            # A $randomseed counts while inherited too (added to its parent's seed), and only then
            # follows the graph's seed and a .sbsar's control (REVIEW.md HLP-25, HLP-27)
            try:
                target.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
            except (Exception, APIException):
                pass
        target.setPropertyValue(prop, new_value)
        print('%s.%s: %r -> %r' % (node_id or 'graph', pid, before, fmt(target.getPropertyValue(prop))))


def atomic_definition_ids(g: SDSBSCompGraph) -> set[str]:
    return {d.getId() for d in g.getNodeDefinitions()}


def _resolve_definition(g: SDSBSCompGraph, definition: str) -> SDNode:
    atomic_id = definition if definition.startswith('sbs::') else 'sbs::compositing::' + definition
    # Validate first: newNode() with an unknown id can hang Designer 15
    if atomic_id in atomic_definition_ids(g):
        node: SDNode = g.newNode(atomic_id)
        return node
    path, graph_id = _library_path(definition)
    if not os.path.exists(path):
        raise RuntimeError('%r is neither an atomic node nor a library package (%s)' % (definition, path))
    res = _load_library(path).findResourceFromUrl(graph_id)
    if res is None:
        raise RuntimeError('graph %r not found in %s' % (graph_id, path))
    return cast(SDNode, g.newInstanceNode(res))  # the resource was found just above


def _place(node: SDNode, position: Sequence[float] | None, existing: list[SDNode]) -> Sequence[float]:
    from sd.api.sdbasetypes import float2

    if position is None:
        # to the right of everything, so it doesn't land on top of existing nodes
        xs = [n.getPosition().x for n in existing] or [0.0]
        ys = [n.getPosition().y for n in existing] or [0.0]
        position = (max(xs) + 200.0, sum(ys) / len(ys))
    node.setPosition(float2(float(position[0]), float(position[1])))
    return position


def add_node(
    graph_id: str | SDSBSCompGraph | None,
    definition: str,
    position: Sequence[float] | None = None,
    params: dict[str, Any] | None = None,
) -> str:
    g = find_graph(graph_id)
    existing = list(g.getNodes())
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
                raise RuntimeError(
                    '%s; and node %s could not be removed again (%s), delete it by hand'
                    % (e, node.getIdentifier(), removal)
                ) from removal
            raise RuntimeError('%s (the node was not added)' % e) from e
    return node.getIdentifier()


def connect(
    graph_id: str | SDSBSCompGraph | None,
    from_node: str | None,
    to_node: str | None,
    to_input: str,
    from_output: str | None = None,
) -> None:
    g = find_graph(graph_id)
    src, dst = _node(g, from_node), _node(g, to_node)  # nodes, never the graph (REVIEW.md HLP-41)
    outs = [p.getId() for p in src.getProperties(SDPropertyCategory.Output)]
    out_id = from_output or (outs[0] if outs else None)
    if out_id not in outs:
        raise RuntimeError('output %r not on node %s; outputs: %s' % (out_id, from_node, outs))
    ins = [p.getId() for p in dst.getProperties(SDPropertyCategory.Input) if p.isConnectable()]
    if to_input not in ins:
        raise RuntimeError('input %r not on node %s; connectors: %s' % (to_input, to_node, ins))
    src.newPropertyConnectionFromId(out_id, dst, to_input)
    print('connected %s.%s -> %s.%s' % (from_node, out_id, to_node, to_input))


def disconnect(graph_id: str | SDSBSCompGraph | None, node_id: str | None, input_id: str) -> None:
    g = find_graph(graph_id)
    node = _node(g, node_id)
    prop = node.getPropertyFromId(input_id, SDPropertyCategory.Input)
    if prop is None or not prop.isConnectable():
        raise RuntimeError('%r is not an input connector on node %s' % (input_id, node_id))
    count = len(node.getPropertyConnections(prop))
    node.deletePropertyConnections(prop)
    print('removed %d connection(s) into %s.%s' % (count, node_id, input_id))


def delete_nodes(graph_id: str | SDSBSCompGraph | None, node_ids: list[str]) -> None:
    g = find_graph(graph_id)
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

    methods = {'link': EmbedMethod.Linked, 'copy': EmbedMethod.CopiedAndLinked}
    if embed not in methods:
        raise RuntimeError('embed must be one of %s' % ', '.join(methods))
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(path):
        raise RuntimeError('no such file: %s' % path)
    g = find_graph(graph_id)
    pkg = g.getPackage()
    existing = list(g.getNodes())
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
    node = cast(SDNode, g.newInstanceNode(res))  # of the resource made or found just above
    position = _place(node, position, existing)
    # a bitmap node always has $outputsize
    size = fmt(node.getPropertyValue(cast(SDProperty, node.getPropertyFromId('$outputsize', SDPropertyCategory.Input))))
    print(
        "added %s bitmap @(%d,%d), size %s (log2, the image's own; set $outputsize to change)"
        % (node.getIdentifier(), position[0], position[1], size)
    )
    print('outputs:', [p.getId() for p in node.getProperties(SDPropertyCategory.Output)])
    return node.getIdentifier()
