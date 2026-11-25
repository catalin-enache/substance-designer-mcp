"""A function built from a compiled expression (ROADMAP item 9): a node parameter's, or a function graph stored in the
package. function_target and function_resource_target are what set_function reads first; set_function and
set_function_resource build (server_tools/functions.py compiles the expression between the read and the build).

Both builds go through _built_beside: the new nodes are put beside the old ones, the output node moved to them, then
the old ones deleted. That way keeps a node's connections and other parameters (GUIDE.md, Building a function graph),
and a function graph of the package stays the one its callers' instance nodes reference. A failure before the output
node moves leaves the old function as it was. One while the old nodes are deleted leaves the new function working, and
some of the old nodes unused beside it: a function graph of the package has its inputs as they were then, which the
new function may not read.

On a node, a $ parameter but $randomseed is then made Absolute, as apply_edits' set makes it: inherited, a function on
$format is ignored, and one on $outputsize is an offset (measured for these two).

A function graph of the package gets its inputs once the output node has moved: its body's get_* nodes name them by
id, and need none to be there. So a failure before it leaves the inputs as they were, and with them the connections
calls make into them. An input is kept when it is the next one wanted, so that those connections stay. The others are
deleted, and the rest made in the order given: Designer drops a call's connection into an input deleted, keeps the
connections into the others, and lists an input made again last (GUIDE.md, Function graphs of the package). A failure
while the inputs are set leaves an existing function graph with the new function and the inputs set so far, which its
error says unless the call's rollback takes its step back (server_tools/core.py, _failure); a new function graph is
deleted."""

import json

from .core import (
    _SIZE_UNIT,
    APIException,
    Callable,
    Literal,
    SDGraph,
    SDNode,
    SDPackage,
    SDProperty,
    SDPropertyCategory,
    SDSBSCompGraph,
    SDSBSCompNode,
    SDSBSFunctionGraph,
    SDType,
    TypedDict,
    _definition_id,
    _graph_to_edit,
    _new_instance,
    _new_node,
    _nodes,
    _other_end,
    _output_nodes,
    _package_name,
    _refuse_bad_size,
    _type,
    _type_ids,
    _value,
    cast,
    fmt,
)
from .edits import _image_inputs, _made_absolute, _make_value, _node, _parameter
from .graph_inputs import (
    _GETTERS,
    _PROGRAMS,
    _driving_graph,
    _function_type_id,
    _functions_of,
    _fx_map_functions,
    _graph_inputs,
    _is_processor_program,
    _new_function_graph,
    _take_back_function,
)


class _Typed(TypedDict):
    """A parameter or graph input: its type id, and the get_* that reads it in a function (_GETTERS), None if none does."""

    type: str
    getter: str | None


class _FunctionNode(TypedDict):
    """A node of a compiled expression (function_compiler.Node): its definition without `sbs::function::`, its output's
    type, its `__constant__` (None when it has none) and the index of the earlier node feeding each other input."""

    definition: str
    type: str
    constant: bool | int | float | str | tuple[int, ...] | tuple[float, ...] | None
    inputs: dict[str, int]


class _Function(TypedDict):
    """A compiled expression (function_compiler.Function): its type, its nodes, the index of its output node, and the
    input images it samples."""

    type: str
    nodes: list[_FunctionNode]
    output: int
    samples: list[int]


# what a function is built for: a Pixel or Value Processor's own function, or a parameter's
_Kind = Literal['perpixel', 'function', 'parameter']


class _End(TypedDict):
    """The other end of a value connection: its node and connector, as `node.connector`, and that connector's type."""

    end: str
    type: str


class _Resource(TypedDict):
    """A function graph of the package, as an expression calls it (function_compiler.Resource): its inputs by id, in
    order; its output node's type, None without an output node of one type; the package's function graphs it calls;
    the indices of its caller's input images it samples."""

    inputs: dict[str, _Typed]
    output: str | None
    calls: list[str]
    samples: list[int]


class _Target(TypedDict):
    """What a function is built for, as function_target prints it and set_function gets it back (server_tools/
    functions.py reads the same keys)."""

    graph: str  # the graph's identifier
    package: str  # its package, as _package_name says it
    node: str
    parameter: str
    kind: _Kind
    value: _Typed  # the parameter's
    colorswitch: bool | None  # a Pixel Processor's
    # the graph's inputs, by id, and the node's input values, by #name: what a value connected into it gives
    # (apply_edits' connect)
    inputs: dict[str, _Typed]
    fed: dict[str, _End | None]  # what is connected into each input value, None for nothing
    drives: list[_End]  # the input values a Value Processor's output feeds, for its own function
    functions: dict[str, _Resource]  # the package's function graphs, by identifier, which the expression can call
    # a processor's input images, input, input:1... up to the last one connected: whether each is; None for a parameter
    images: list[bool] | None


class _Reach(TypedDict):
    """A node's function calling a function graph, directly or through others: the node as graph/node, the parameter,
    and the node's input images as _Target gives a processor's, None for a parameter's function."""

    where: str
    parameter: str
    images: list[bool] | None


class _ResourceTarget(TypedDict):
    """A function graph of the package as set_function builds it, as function_resource_target prints it and
    set_function_resource gets it back (server_tools/functions.py reads the same keys)."""

    graph: str  # the identifier of the graph whose package holds it
    package: str  # that package, as _package_name says it
    function: str  # its identifier
    functions: dict[str, _Resource]  # the package's function graphs, by identifier, this one too once it exists
    callers: list[str]  # what calls it: function graphs by identifier, a node's function as graph/node.parameter
    fx_map_callers: list[str]  # an FX-Map's inner node's functions calling it, as graph/node/inner.parameter
    reaching: list[_Reach]  # each node's function calling it, directly or through others: what it samples reaches it


_INSTANCE = 'sbs::function::instance'
_SAMPLERS = ('sbs::function::samplecol', 'sbs::function::samplelum')


def _typed(prop: SDProperty) -> _Typed:
    return {'type': _type(prop).getId(), 'getter': _GETTERS.get(_function_type_id(prop))}


def _end(other: SDNode, connector: SDProperty) -> _End:
    """A connection's other end (_other_end), with its connector's type."""
    return {'end': '%s.%s' % (other.getIdentifier(), connector.getId()), 'type': _type(connector).getId()}


def _target_of(
    g: SDSBSCompGraph, node_id: str | None, parameter: str | None
) -> tuple[SDSBSCompNode, SDProperty, _Target]:
    """The node, its parameter (a processor's own function when none is named) and what set_function needs of them.
    Raises if the parameter is missing, a connector (_function_parameter), or of a type no function gives."""
    node, prop, kind = _function_parameter(g, node_id, parameter)
    value = _typed(prop)
    if kind == 'parameter' and value['getter'] is None:
        raise RuntimeError('parameters of type %s cannot take a function from this tool' % value['type'])
    values, fed = _input_values(node)
    outputs = node.getProperties(SDPropertyCategory.Output) if kind == 'function' else []  # what it may drive
    colorswitch = None
    if kind == 'perpixel':
        shown = fmt(node.getInputPropertyValueFromId('colorswitch'))
        colorswitch = shown if isinstance(shown, bool) else None
    target: _Target = {
        'graph': g.getIdentifier(),
        'package': _package_name(g.getPackage()),
        'node': str(node_id),
        'parameter': prop.getId(),
        'kind': kind,
        'value': value,
        'colorswitch': colorswitch,
        'inputs': {p.getId(): _typed(p) for p in [*_graph_inputs(g), *values]},
        'fed': fed,
        'drives': [
            _end(other, connector)
            for out in outputs
            for other, connector in map(_other_end, node.getPropertyConnections(out))
            if connector.getId().startswith('#')
        ],
        'functions': _functions_read(g.getPackage()),
        'images': _images(node, prop),
    }
    return node, prop, target


def _function_parameter(
    g: SDSBSCompGraph, node_id: str | None, parameter: str | None, other_way: str = ''
) -> tuple[SDSBSCompNode, SDProperty, _Kind]:
    """The node, its parameter holding a function (a processor's own when none is named) and the kind of that function:
    what set_function builds on, and describe_graph reads. Raises if the node has no function of its own and no
    parameter is named, adding `other_way` to the message, or if the parameter is missing or a connector."""
    node = _node(g, node_id)
    pid = parameter or _PROGRAMS.get(_definition_id(node))
    if not pid:
        raise RuntimeError(
            'node %s is %s, which has no function of its own: name the parameter; see describe_node%s'
            % (node_id, _definition_id(node), other_way)
        )
    prop = _parameter(node, node_id, pid)
    kind: _Kind = 'parameter'
    if _is_processor_program(node, prop):
        kind = 'perpixel' if pid == 'perpixel' else 'function'
    return node, prop, kind


def _input_values(node: SDNode) -> tuple[list[SDProperty], dict[str, _End | None]]:
    """A node's input values (#name), and what is connected into each, None for nothing. A connection replaces the one
    before, so an input value has one at most."""
    values = [p for p in node.getProperties(SDPropertyCategory.Input) if p.getId().startswith('#')]
    fed = {p.getId(): next((_end(*_other_end(c)) for c in node.getPropertyConnections(p)), None) for p in values}
    return values, fed


def _images(node: SDNode, prop: SDProperty) -> list[bool] | None:
    """For a processor's own function `prop`, whether each of its input images has a connection, up to the last one
    that has; None for a parameter's function, which has none to sample."""
    if not _is_processor_program(node, prop):
        return None
    connected = [len(node.getPropertyConnections(p)) > 0 for p in _image_inputs(node)]
    while connected and not connected[-1]:
        connected.pop()
    return connected


def function_target(identifier: str | SDSBSCompGraph | None, node_id: str | None, parameter: str | None) -> None:
    """Prints FUNCTION_TARGET=<json>, the target of a function as set_function builds it (_target_of)."""
    print('FUNCTION_TARGET=' + json.dumps(_target_of(_graph_to_edit(identifier), node_id, parameter)[2]))


def _package_functions(pkg: SDPackage) -> dict[str, SDSBSFunctionGraph]:
    """The package's function graphs, in its folders too, by identifier: the one lookup the read and the builds use."""
    return {r.getIdentifier(): r for r in pkg.getChildrenResources(True) if isinstance(r, SDSBSFunctionGraph)}


def _function_graph(g: SDSBSCompGraph, name: str) -> SDSBSFunctionGraph:
    """The function graph `name` of g's package, which describe_graph and open_graph read. Raises naming the ones it
    has when it has none of that name."""
    functions = _package_functions(g.getPackage())
    if name not in functions:
        raise RuntimeError(
            'the package of graph %s has no function graph %r; its function graphs: %s'
            % (g.getIdentifier(), name, ', '.join(sorted(functions)) or 'none')
        )
    return functions[name]


def _calls(fg: SDGraph, pkg: SDPackage) -> list[str]:
    """The function graphs of `pkg` that `fg`'s instance nodes call, by identifier. An instance of another package's
    function graph, such as one of Designer's library, isn't one."""
    called = set()
    for n in _nodes(fg):
        if _definition_id(n) != _INSTANCE:
            continue
        ref = n.getReferencedResource()
        if isinstance(ref, SDSBSFunctionGraph) and _package_name(ref.getPackage()) == _package_name(pkg):
            called.add(ref.getIdentifier())
    return sorted(called)


def _resource(fn: SDGraph, pkg: SDPackage) -> _Resource:
    """What a call of the function graph `fn` needs: its inputs, its output's type, what it calls and the input images
    it samples. A function graph has no output of its own: a call gives its output node's type (GUIDE.md, Function
    graphs of the package)."""
    outputs = _output_nodes(fn)
    listed = _output_types(outputs[0]) if len(outputs) == 1 else []  # unread, it is no output of one type
    return {
        'inputs': {p.getId(): _typed(p) for p in _graph_inputs(fn)},
        'output': listed[0] if len(listed) == 1 else None,
        'calls': _calls(fn, pkg),
        'samples': _sampled(fn),
    }


def _output_types(n: SDNode) -> list[str]:
    """The types a function node's output lists, by id: one once its inputs settle it (GUIDE.md, Building a function
    graph)."""
    return _type_ids(n.getPropertyFromId('unique_filter_output', SDPropertyCategory.Output))


def _sampled(fn: SDGraph) -> list[int]:
    """The input images `fn`'s own samplecol and samplelum nodes sample: the first component of each __constant__
    (GUIDE.md, Sampling an image). A negative one, made in Designer, is no input image: it reads (0, 0, 0, 0), and is
    left out (REVIEW.md SRV-201)."""
    indices = set()
    for n in _nodes(fn):
        if _definition_id(n) in _SAMPLERS:
            held = fmt(n.getPropertyValueFromId('__constant__', SDPropertyCategory.Input))
            if isinstance(held, tuple) and isinstance(held[0], int) and held[0] >= 0:
                indices.add(held[0])
    return sorted(indices)


def _functions_read(pkg: SDPackage) -> dict[str, _Resource]:
    return {name: _resource(fn, pkg) for name, fn in _package_functions(pkg).items()}


def _callers(pkg: SDPackage, name: str, functions: dict[str, _Resource]) -> tuple[list[str], list[str], list[_Reach]]:
    """What calls the function graph `name`: the package's function graphs, by identifier, then each function on a
    node of its compositing graphs, as graph/node.parameter; and apart, each on an FX-Map's inner node, as
    graph/node/inner.parameter, which set_function can't reach (REVIEW.md HLP-239). Then each node's function calling
    it directly or through others, with the node's input images, which what it samples reads (REVIEW.md SRV-199).
    Nothing calls one the package doesn't have yet, so its graphs aren't searched then."""
    if name not in functions:
        return [], [], []
    found = [f for f, r in functions.items() if name in r['calls']]
    inner: list[str] = []
    reaching: list[_Reach] = []
    for g in pkg.getChildrenResources(True):
        if isinstance(g, SDSBSCompGraph):
            for node in _nodes(g):
                where = '%s/%s' % (g.getIdentifier(), node.getIdentifier())
                for p, fg in _functions_of(node):
                    calls = _calls(fg, pkg)
                    if name in calls:
                        found.append('%s.%s' % (where, p.getId()))
                    if _reaches(calls, name, functions):
                        reaching.append({'where': where, 'parameter': p.getId(), 'images': _images(node, p)})
                inner += [
                    '%s/%s.%s' % (where, i, p.getId())
                    for i, p, fg in _fx_map_functions(node)
                    if name in _calls(fg, pkg)
                ]
    return found, inner, reaching


def _reaches(calls: list[str], name: str, functions: dict[str, _Resource]) -> bool:
    """Whether the function graphs `calls`, or those they call, include `name`."""
    seen: set[str] = set()
    waiting = list(calls)
    while waiting:
        f = waiting.pop()
        if f == name:
            return True
        if f not in seen and f in functions:
            seen.add(f)
            waiting += functions[f]['calls']
    return False


def _resource_target(g: SDSBSCompGraph, name: str) -> _ResourceTarget:
    """What set_function_resource needs of the function graph `name` of g's package. Raises if another resource of the
    package has that identifier: Designer would give the function graph another one (GUIDE.md, Function graphs of the
    package)."""
    pkg = g.getPackage()
    for r in pkg.getChildrenResources(True):
        if r.getIdentifier() == name and not isinstance(r, SDSBSFunctionGraph):
            kind = 'graph' if isinstance(r, SDSBSCompGraph) else 'resource'
            raise RuntimeError(
                'the package holds a %s named %r already: give the function graph an identifier of its own'
                % (kind, name)
            )
    functions = _functions_read(pkg)
    callers, fx_map_callers, reaching = _callers(pkg, name, functions)
    return {
        'graph': g.getIdentifier(),
        'package': _package_name(pkg),
        'function': name,
        'functions': functions,
        'callers': callers,
        'fx_map_callers': fx_map_callers,
        'reaching': reaching,
    }


def function_resource_target(identifier: str | SDSBSCompGraph | None, name: str) -> None:
    """Prints FUNCTION_RESOURCE=<json>, the function graph `name` of the graph's package as set_function_resource
    builds it (_resource_target)."""
    print('FUNCTION_RESOURCE=' + json.dumps(_resource_target(_graph_to_edit(identifier), name)))


def _laid_out(nodes: list[_FunctionNode]) -> list[tuple[float, float]]:
    """A position for each node: in columns, each node to the right of the nodes feeding it."""
    columns: list[int] = []
    rows: dict[int, int] = {}
    places = []
    for n in nodes:
        column = 1 + max((columns[i] for i in n['inputs'].values()), default=-1)
        columns.append(column)
        rows[column] = rows.get(column, -1) + 1
        places.append((150.0 * column, 100.0 * rows[column]))
    return places


def _built_beside(
    function_graph: Callable[[], SDGraph],
    function: _Function,
    functions: dict[str, SDSBSFunctionGraph],
    take_back: Callable[[list[SDNode]], None],
) -> tuple[int, int]:
    """Builds `function` (function_compiler.Function: its nodes, each fed by earlier ones, and its output) in the function
    graph `function_graph()` makes or gives, beside its nodes, makes its output node the graph's, then deletes the old
    nodes (the module docstring). An instance node is made of its function graph in `functions`. Returns how many nodes
    it built and deleted. A failure before the output node moves calls `take_back` with the nodes built so far, then
    raises."""
    from sd.api.sdbasetypes import float2

    nodes, output = function['nodes'], function['output']  # before anything changes (REVIEW.md HLP-226)
    built: list[SDNode] = []
    try:
        fg = function_graph()
        old = _nodes(fg)
        for n, (x, y) in zip(nodes, _laid_out(nodes), strict=True):
            instance = n['definition'] == 'instance'  # its constant is the function graph's identifier
            if instance:
                fnode = _new_instance(fg, functions[str(n['constant'])])
            else:
                fnode = _new_node(fg, 'sbs::function::%s' % n['definition'])
            built.append(fnode)
            fnode.setPosition(float2(x, y))
            if n['constant'] is not None and not instance:
                # a node given a constant has the input: its definition lists one (function_compiler.DEFINITIONS)
                held = cast(SDProperty, fnode.getPropertyFromId('__constant__', SDPropertyCategory.Input))
                fnode.setPropertyValue(held, _make_value(held, n['constant']))
            for input_id, source in n['inputs'].items():
                built[source].newPropertyConnectionFromId('unique_filter_output', fnode, input_id)
        fg.setOutputNode(built[output], True)
    except (Exception, APIException):
        take_back(built)
        raise
    for replaced in old:
        fg.deleteNode(replaced)
    return len(built), len(old)


def _built_line(where: str, function: _Function, built: int, deleted: int) -> str:
    """The build's line: what it built where, the output's type, and what it replaced."""
    replaced = '; deleted the %s it replaced' % _counted(deleted, 'node') if deleted else ''
    return '%s: built %s, its output a %s%s' % (where, _counted(built, 'function node'), function['type'], replaced)


def set_function(identifier: str | SDSBSCompGraph | None, target: _Target, function: _Function) -> None:
    """Build `function` (function_compiler.Function) as the function of `target`, which must be as function_target gave
    it: nothing is built otherwise."""
    g = _graph_to_edit(identifier)
    where = '%s.%s' % (target['node'], target['parameter'])
    node, prop, now = _target_of(g, target['node'], target['parameter'])
    if now != target:
        raise RuntimeError('%s changed since set_function read it; nothing was built: call set_function again' % where)
    # a tuple for a constant int2, None for a size computed from other nodes
    constant = function['nodes'][function['output']]['constant']
    if target['parameter'] == '$outputsize' and isinstance(constant, tuple):
        # Designer computes 8192 px from 15, refusing nothing
        _refuse_bad_size('$outputsize', [int(v) for v in constant], constant)
    existing = _driving_graph(node, prop)  # None for an empty one too: newPropertyGraph returns it
    old_value = _value(node, prop)  # a new function graph resets it
    built, deleted = _built_beside(
        lambda: existing or _new_function_graph(node, prop, where),
        function,
        _package_functions(g.getPackage()),
        lambda added: _take_back_function(node, prop, existing, old_value, added),
    )
    print(_built_line(where, function, built, deleted))
    if _made_absolute(node, prop):
        size = ': the function gives %s' % _SIZE_UNIT if target['parameter'] == '$outputsize' else ''
        print("%s is Absolute now, as apply_edits' set makes it%s" % (where, size))


def _new_type(type_id: str) -> SDType:
    """A new SDType of a function graph's input: bool, int to int4, float to float4, or string, by its id."""
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

    types: dict[str, Callable[[], SDType]] = {
        'bool': SDTypeBool.sNew,
        'int': SDTypeInt.sNew,
        'int2': SDTypeInt2.sNew,
        'int3': SDTypeInt3.sNew,
        'int4': SDTypeInt4.sNew,
        'float': SDTypeFloat.sNew,
        'float2': SDTypeFloat2.sNew,
        'float3': SDTypeFloat3.sNew,
        'float4': SDTypeFloat4.sNew,
        'string': SDTypeString.sNew,
    }
    return types[type_id]()


def _input_of(p: SDProperty) -> tuple[str, str]:
    """A function graph's input as set_function_resource gives it: its id and its type's id."""
    return p.getId(), _type(p).getId()


def _set_inputs(fn: SDGraph, inputs: list[tuple[str, str]]) -> None:
    """Gives the function graph `fn` the inputs `inputs` ([(id, type id)]), in that order: each it has is kept when it
    is the next one wanted, and with it the connections calls make into it, and deleted otherwise; then the rest are
    made (the module docstring). Raises if Designer then lists other inputs, as a renamed id would make (REVIEW.md
    HLP-235)."""
    kept = 0
    for p in _graph_inputs(fn):
        if kept < len(inputs) and _input_of(p) == inputs[kept]:
            kept += 1
        else:
            fn.deleteProperty(p)
    for pid, type_id in inputs[kept:]:
        fn.newProperty(pid, _new_type(type_id), SDPropertyCategory.Input)
    made = [_input_of(p) for p in _graph_inputs(fn)]
    if made != inputs:
        raise RuntimeError(
            'Designer gave the function graph %s the inputs %s, not %s'
            % (fn.getIdentifier(), _shown(made), _shown(inputs))
        )


def _shown(inputs: list[tuple[str, str]]) -> str:
    """Inputs as a line says them: 'uv float2, k float'."""
    return ', '.join('%s %s' % pair for pair in inputs)


def set_function_resource(
    identifier: str | SDSBSCompGraph | None,
    target: _ResourceTarget,
    inputs: list[tuple[str, str]] | None,
    function: _Function,
) -> None:
    """Build `function` (function_compiler.Function) as the function graph target['function'] of the graph's package,
    with `inputs` ([(id, type id)], in a call's order; None keeps the ones it has): made if the package has none, else
    its nodes replaced and its inputs set (_set_inputs) once the output node has moved, the graph kept, so that the
    functions calling it still find it. `target` must be as function_resource_target gave it: nothing is built
    otherwise. A failure deletes a function graph it made. On an existing one, a failure before the output node moves
    deletes the nodes it built and leaves the inputs as they were; one after leaves the new function, with the inputs
    set so far, said on a KEPT= line (the module docstring)."""
    g = _graph_to_edit(identifier)
    name = target['function']
    if _resource_target(g, name) != target:
        raise RuntimeError(
            'the function graph %s changed since set_function read it; nothing was built: call set_function again'
            % name
        )
    pkg = g.getPackage()
    functions = _package_functions(pkg)
    fn: SDSBSFunctionGraph | None = functions.get(name)
    new = fn is None

    def function_graph() -> SDGraph:
        nonlocal fn
        if fn is None:
            fn = SDSBSFunctionGraph.sNew(pkg)
            fn.setIdentifier(name)
            if fn.getIdentifier() != name:  # Designer renames a taken identifier, which the read refuses
                raise RuntimeError('Designer named the function graph %s, not %s' % (fn.getIdentifier(), name))
        return fn

    def take_back(added: list[SDNode]) -> None:
        # raises nothing, so that the build raises its failure
        try:
            if fn is not None and new:
                fn.delete()
            elif fn is not None:
                for n in added:
                    fn.deleteNode(n)
        except (Exception, APIException):
            pass

    built, deleted = _built_beside(function_graph, function, functions, take_back)
    made = cast(SDSBSFunctionGraph, fn)  # function_graph() gave it
    try:
        if inputs is not None:
            _set_inputs(made, inputs)
    except (Exception, APIException):
        if new:
            take_back([])
        else:  # the output node has moved: say what is left (REVIEW.md HLP-238), on a line of its own, which the server
            # shows only if the call's rollback didn't take it back (server_tools/core.py, _failure; REVIEW.md HLP-256)
            print('KEPT=%s keeps its new function, and the inputs set so far' % name)
        raise
    where = '%s(%s)' % (name, _shown([_input_of(p) for p in _graph_inputs(made)] if inputs is None else inputs))
    if new:
        where += ', a new function graph of %s' % target['package']
    print(_built_line(where, function, built, deleted))


def _counted(n: int, what: str) -> str:
    """'1 node', '3 nodes'."""
    return '%d %s%s' % (n, what, '' if n == 1 else 's')
