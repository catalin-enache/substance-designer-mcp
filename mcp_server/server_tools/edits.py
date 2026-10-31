"""Editing graphs: add_node, set_params, connect, disconnect, delete_nodes, import_bitmap,
create_graph, move_nodes, apply_edits, and exposed inputs (expose_param, list_graph_inputs,
remove_graph_input, set_graph_size)."""

from typing import Any

from .core import _bridge, _checked, _edit, _helpers_call, _local_path, _tool


@_tool()
def add_node(
    definition: str, graph: str | None = None, position: list[float] | None = None, params: dict[str, Any] | None = None
) -> str:
    """Add a node and return its id. definition: atomic ('levels', 'blend') or library
    ('tile_generator', 'hbao.sbs/hbao'). position: [x, y] (default: right of existing nodes).
    params: initial parameter values (same rules as set_params); a bad one refuses the whole add,
    so no node is left. One undo step."""
    return _edit('add_node(%r, %r, %r, %r)' % (graph, definition, position, params), 'Claude: add ' + definition)


@_tool()
def set_params(node_id: str, params: dict[str, Any], graph: str | None = None) -> str:
    """Set parameters on a node (node_id 'graph' = the graph itself, e.g. a fixed-size graph's
    $outputsize; an overridable graph's size is refused: use set_graph_size).
    Values are converted to the parameter's type: numbers, bools, lists for vectors/colors
    ([r,g,b(,a)]), enums by id or number ('max', 5 or '5'). Every value is checked before any is set.
    A parameter driven by a graph input (expose_param) or a function is refused: set the graph
    input instead (node_id 'graph'). A $ parameter is made Absolute so its value takes effect ($format
    and $outputsize ignore theirs while inherited); except $randomseed, on a node or the graph, whose
    inheritance is left as it is: inherited, its value counts (added to the parent's seed), and only
    an inherited seed follows the graph's seed and the cooked .sbsar's Random Seed. To fix a seed on
    purpose, change its inheritance with execute_designer_code. Prints old -> new. One undo step."""
    return _edit('set_params(%r, %r, %r)' % (graph, node_id, params), 'Claude: set params on ' + node_id)


@_tool()
def connect(
    from_node: str, to_node: str, to_input: str, from_output: str | None = None, graph: str | None = None
) -> str:
    """Connect from_node's output (default: its first) to to_node's input connector
    (replaces an existing link on that input). One undo step."""
    return _edit('connect(%r, %r, %r, %r, %r)' % (graph, from_node, to_node, to_input, from_output), 'Claude: connect')


@_tool()
def disconnect(node_id: str, input_id: str, graph: str | None = None) -> str:
    """Remove the connection(s) going into node_id's input connector. One undo step."""
    return _edit('disconnect(%r, %r, %r)' % (graph, node_id, input_id), 'Claude: disconnect')


@_tool()
def delete_nodes(node_ids: list[str], graph: str | None = None) -> str:
    """Delete nodes (and their connections) from a graph. One undo step."""
    return _edit('delete_nodes(%r, %r)' % (graph, node_ids), 'Claude: delete nodes')


@_tool()
def import_bitmap(
    path: str,
    graph: str | None = None,
    embed: str = 'link',
    position: list[float] | None = None,
    name: str | None = None,
) -> str:
    """Add an image file (png, jpg, tga, exr, tif, psd...) to a graph as a Bitmap node and return
    its id (output connector `unique_filter_output`). For references, masks and hand-painted maps.
    embed: 'link' references the file where it is (an existing link to the same file is reused);
    'copy' copies it into `<package>.resources/` (into a temp folder until the package is saved).
    Embedding the image in the .sbs is not available through the API. The node keeps the image's
    own size; set its `$outputsize` with set_params to change it. name: resource identifier
    (default: the file name). position as in add_node. One undo step."""
    return _edit(
        'import_bitmap(%r, %r, %r, %r, %r)' % (graph, _local_path(path), embed, position, name), 'Claude: import bitmap'
    )


@_tool()
def create_graph(name: str, save_path: str | None = None, size_log2: int = 11) -> str:
    """Create a new package with one empty compositing graph (output size 2^size_log2,
    default 2048). save_path: optional .sbs path to save it to. One undo step."""
    return _edit('create_graph(%r, %r, %d)' % (name, _local_path(save_path), size_log2), 'Claude: create graph ' + name)


@_tool()
def move_nodes(positions: dict[str, list[float]], graph: str | None = None) -> str:
    """Move nodes: {"node_id": [x, y], ...}. One undo step."""
    return _edit('move_nodes(%r, %r)' % (graph, positions), 'Claude: move nodes')


@_tool()
def expose_param(
    node_id: str,
    param: str,
    graph: str | None = None,
    input_id: str | None = None,
    label: str | None = None,
    default: float | int | bool | str | list[float] | None = None,
    min: float | None = None,
    max: float | None = None,
    step: float | None = None,
    group: str | None = None,
) -> str:
    """Expose a node parameter as a graph input (same type as the parameter; enums become ints),
    like Designer's own "Expose" action. The input starts at the parameter's current value
    unless `default` is given; min/max/step/group set the slider. The input then shows up in
    sbsar_info and can be set with render_sbs(params=...). Refuses a parameter that is already
    driven by a function (replacing it would lose that logic). One undo step."""
    return _edit(
        'expose_param(%r, %r, %r, %r, %r, %r, %r, %r, %r, %r)'
        % (graph, node_id, param, input_id, label, default, min, max, step, group),
        'Claude: expose ' + param,
    )


@_tool()
def list_graph_inputs(graph: str | None = None) -> str:
    """List a graph's exposed inputs (type, value, label/min/max, which node parameters they
    drive) and whether its output size is fixed or overridable."""
    return _checked(_bridge(_helpers_call('list_graph_inputs(%r)' % graph), timeout=60))


@_tool()
def remove_graph_input(input_id: str, graph: str | None = None) -> str:
    """Delete an exposed graph input. Parameters bound to it (as expose_param does) keep its
    current value. Refuses, changing nothing, while a larger function (an expression, a Pixel
    Processor) still reads the input. One undo step."""
    return _edit('remove_graph_input(%r, %r)' % (graph, input_id), 'Claude: remove input ' + input_id)


@_tool()
def set_graph_size(size_log2: int, graph: str | None = None, overridable: bool = True) -> str:
    """Set the graph's output size to 2^size_log2. overridable=True (default) makes the size
    follow the parent with that default, so render_sbs(size_log2=...) can override it;
    False fixes it. One undo step."""
    return _edit('set_graph_size(%r, %d, %r)' % (graph, size_log2, overridable), 'Claude: set graph size')


@_tool()
def apply_edits(ops: list[dict[str, Any]], graph: str | None = None) -> str:
    """Run several edits in one call and one undo step. Each op is a dict:
    {"op": "add", "definition": "levels", "ref": "lv", "position"?: [x, y], "params"?: {...}}
    {"op": "bitmap", "path": "/abs/image.png", "ref": "img", "embed"?: "link", "position"?: [x, y],
     "name"?: "..."}
    {"op": "set", "node": "lv", "params": {...}}            (node: a ref, a node id, or "graph")
    {"op": "connect", "from": "a", "to": "lv", "input": "input1", "output"?: "..."}
    {"op": "disconnect", "node": "lv", "input": "input1"}
    {"op": "move", "node": "lv", "position": [x, y]}
    {"op": "delete", "node": "lv"}
    {"op": "expose", "node": "lv", "param": "...", "input_id"?: "...", "label"?: "...", "default"?: ...,
     "min"?: 0, "max"?: 1, "step"?: 0.1, "group"?: "..."}         (as expose_param)
    Refs let later ops use nodes added earlier in the batch. Stops at the first failing op
    (earlier ops stay applied; Ctrl+Z on the graph reverts the whole batch)."""
    ops = [
        {**op, 'path': _local_path(op['path'])} if isinstance(op, dict) and isinstance(op.get('path'), str) else op
        for op in ops
    ]
    return _edit('apply_edits(%r, %r)' % (graph, ops), 'Claude: apply %d edits' % len(ops))
