"""describe_graph of a function (describe_function): a node's, found as set_function finds it (_function_parameter),
with what feeds each input value it reads (_input_values); or a function graph of the package (_function_graph, which
open_graph opens too). And the line naming the package's function graphs in describe_graph of a graph
(_function_graphs_line)."""

from .core import (
    APIException,
    SDGraph,
    SDNode,
    SDPackage,
    SDPropertyCategory,
    SDSBSCompGraph,
    _definition_id,
    _focused,
    _links_text,
    _more,
    _node_head,
    _nodes,
    _output_nodes,
    _package_name,
    _type,
    find_graph,
    fmt,
    node_kind,
)
from .functions import (
    _counted,
    _function_graph,
    _function_parameter,
    _functions_read,
    _input_values,
    _Kind,
    _output_types,
    _resource,
    _shown,
    _Typed,
)
from .graph_inputs import _input_read

# what a node's function is, by its _Kind
_FUNCTION_OF: dict[_Kind, str] = {
    'perpixel': "a Pixel Processor's function",
    'function': "a Value Processor's function",
    'parameter': "a parameter's function",
}


def describe_function(
    identifier: str | SDSBSCompGraph | None,
    node_id: str | None,
    parameter: str | None,
    function: str | None,
    node_ids: list[str] | None = None,
    limit: int = 400,
) -> None:
    """describe_graph of a function: the function graph `function` of the graph's package, or else the function of
    node node_id on `parameter` (default: a processor's own). Then its nodes (_function_node_line), only `node_ids`'
    when given, `limit` at most."""
    g = find_graph(identifier)
    fg = _function_graph_read(g, function) if function else _node_function_read(g, node_id, parameter)
    if fg is None:
        return
    nodes = _focused(_nodes(fg), node_ids)
    for n in nodes[:limit]:
        print(_function_node_line(n))
    _more(nodes, limit)


def _function_graph_read(g: SDSBSCompGraph, function: str) -> SDGraph:
    """Prints the first lines of describe_function of the function graph `function` of g's package: its nodes and its
    output node, then its inputs. Returns it."""
    pkg = g.getPackage()
    fg: SDGraph = _function_graph(g, function)
    print('function graph %s of %s: %s' % (function, _package_name(pkg), _contents(fg)))
    print('inputs: %s' % (_inputs_shown(_resource(fg, pkg)['inputs']) or 'none'))
    return fg


def _node_function_read(g: SDSBSCompGraph, node_id: str | None, parameter: str | None) -> SDGraph | None:
    """Prints the first lines of describe_function of node node_id's function on `parameter`: its nodes and its output
    node, then the input values it reads. Returns it; None, saying so, when the parameter has none or an empty one, or
    when it can't be read. Any parameter's, also of a type set_function refuses to build (REVIEW.md HLP-244)."""
    # a node with none of its own may be one to describe in its graph, a call without node_id (REVIEW.md SRV-218)
    node, prop, kind = _function_parameter(
        g,
        node_id,
        parameter,
        ', or describe the node in its graph: describe_graph(node_ids=[%r]), with no node_id' % node_id,
    )
    where = '%s.%s' % (node_id, prop.getId())
    try:
        fg: SDGraph | None = node.getPropertyGraph(prop)
    except (Exception, APIException) as e:  # not "no function": one may be there (REVIEW.md HLP-245)
        print("%s: its function couldn't be read (%s)" % (where, e))
        return None
    if fg is None or not _nodes(fg):
        print('%s has %s' % (where, 'no function' if fg is None else 'an empty function'))
        return None
    print('%s, %s, in graph %s: %s' % (where, _FUNCTION_OF[kind], g.getIdentifier(), _contents(fg)))
    for line in _input_values_read(fg, node):
        print(line)
    return fg


def _contents(fg: SDGraph) -> str:
    """A function's nodes and its output node, as describe_function's first line says them: '3 nodes, output node 7
    mul -> float', or that it has no output node."""
    outputs = _output_nodes(fg)
    nodes = _counted(len(_nodes(fg)), 'node')
    if not outputs:
        return nodes + ', no output node'
    return '%s, output node %s %s -> %s' % (
        nodes,
        outputs[0].getIdentifier(),
        node_kind(outputs[0]),
        _types(outputs[0]),
    )


def _types(n: SDNode) -> str:
    """A function node's output types, as a line says them: 'float', 'int,float', or 'none'."""
    return ','.join(_output_types(n)) or 'none'


def _function_node_line(n: SDNode) -> str:
    """A function's node as describe_function lists it: its id, kind and position, as a graph's node; its constant
    when it has one; its output's types; its incoming connections."""
    line = _node_head(n)
    held = n.getPropertyFromId('__constant__', SDPropertyCategory.Input)
    if held is not None:
        line += ' = %r' % (fmt(n.getPropertyValue(held)),)
    return '%s -> %s%s' % (line, _types(n), _links_text(n))


def _input_values_read(fg: SDGraph, node: SDNode) -> list[str]:
    """A line for each input value (#name) the get_* nodes of `node`'s function `fg` read, and what feeds it
    (_input_values): so a function left reading a value of another type, or nothing, shows. Designer reads one fed
    another type wrongly, raising nothing (GUIDE.md, Input values)."""
    names = {
        name
        for n in _nodes(fg)
        if '::get_' in _definition_id(n) and (name := _input_read(n)) is not None and name.startswith('#')
    }
    if not names:
        return []
    values, fed = _input_values(node)
    types = {p.getId(): _type(p).getId() for p in values}
    lines = []
    for name in sorted(names):
        if name not in fed:
            lines.append('reads %s: the node has no input value of that name' % name)
            continue
        own, source = types[name], fed[name]
        if source is None:
            feeds = 'with nothing connected'
        else:
            wrong = '' if source['type'] == own else ', which Designer reads wrongly'
            feeds = 'fed by %s, of type %s%s' % (source['end'], source['type'], wrong)
        lines.append('reads %s: an input value of type %s, %s' % (name, own, feeds))
    return lines


def _inputs_shown(inputs: dict[str, _Typed]) -> str:
    """A function graph's inputs, as _resource gives them, as a line says them: 'uv float2, k float' (_shown)."""
    return _shown([(i, typed['type']) for i, typed in inputs.items()])


def _function_graphs_line(pkg: SDPackage) -> str:
    """describe_graph's line naming a package's function graphs, each with its inputs and its output's type, as a call
    gives them; '' when it has none."""
    called = [
        '%s(%s) -> %s' % (name, _inputs_shown(r['inputs']), r['output'] or 'no output of one type')
        for name, r in _functions_read(pkg).items()
    ]
    return 'function graphs of the package: %s' % ', '.join(called) if called else ''
