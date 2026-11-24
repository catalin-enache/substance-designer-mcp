"""Editing graphs: apply_edits (every node and connection edit), create_graph, and exposed inputs
(list_graph_inputs, remove_graph_input, set_graph_size)."""

from typing import Annotated

from pydantic import Field

from .core import Graph, JsonObject, _bridge, _checked, _edit, _helpers_call, _local_path, _tool


@_tool(read_only=False, destructive=True, idempotent=False, open_world=False)
def create_graph(
    name: Annotated[str, Field(description="The new graph's identifier.")],
    save_path: Annotated[str | None, Field(description='Optional .sbs path to save the package to.')] = None,
    size_log2: Annotated[
        int, Field(description='Output size 2^size_log2 (default 2048; 13 is 8192 px, the largest).')
    ] = 11,
) -> str:
    """Create a new package with one empty compositing graph. One undo step."""
    return _edit('create_graph(%r, %r, %d)' % (name, _local_path(save_path), size_log2), 'Claude: create graph ' + name)


@_tool(read_only=True, destructive=False, idempotent=True, open_world=False)
def list_graph_inputs(graph: Graph = None) -> str:
    """List a graph's exposed inputs (type, value, label/min/max, which node parameters they
    drive, FX-Map functions and those on the graph's own parameters as last saved included) and
    whether its output size is fixed or overridable. A get
    node that doesn't feed its function's output, or a function with no output node, drives nothing
    and isn't listed, though remove_graph_input still refuses while it names the input."""
    return _checked(_bridge(_helpers_call('list_graph_inputs(%r)' % graph), timeout=60))


@_tool(read_only=False, destructive=True, idempotent=True, open_world=False)
def remove_graph_input(
    input_id: Annotated[str, Field(description="The exposed input's identifier.")], graph: Graph = None
) -> str:
    """Delete an exposed graph input. Parameters bound to it (as an expose op binds them) keep its
    current value. Refuses, changing nothing, while another function (an expression, a Pixel
    Processor, even if it is one get, an FX-Map's, one on the graph's own parameter as last saved, one
    with no output node yet, a leftover get node) still names the input,
    saying which have no effect today, or while a parameter can't hold its value (an int beyond an
    enum's values). One undo step."""
    return _edit('remove_graph_input(%r, %r)' % (graph, input_id), 'Claude: remove input ' + input_id)


@_tool(read_only=False, destructive=True, idempotent=True, open_world=False)
def set_graph_size(
    size_log2: Annotated[int, Field(description='Output size 2^size_log2 (13 is 8192 px, the largest).')],
    graph: Graph = None,
    overridable: Annotated[
        bool,
        Field(
            description='True (default) makes the size follow the parent with that default, so '
            "render_sbs(size_log2=...) can override it; False fixes it. A fixed size isn't exposed, so size overrides "
            'are ignored.'
        ),
    ] = True,
) -> str:
    """Set the graph's output size. One undo step."""
    return _edit('set_graph_size(%r, %d, %r)' % (graph, size_log2, overridable), 'Claude: set graph size')


# What goes in apply_edits' ops: each op's fields, then what each op does
OPS = """\
Each op is a dict:
{"op": "add", "definition": "levels", "ref": "lv", "position"?: [x, y], "identifier"?: "...", "label"?: "...",
 "usage"?: "...", "params"?: {...}}
{"op": "bitmap", "path": "/abs/image.png", "ref": "img", "embed"?: "link", "position"?: [x, y],
 "name"?: "..."}
{"op": "set", "node": "lv", "identifier"?: "...", "label"?: "...", "usage"?: "...", "params"?: {...}}
                                                        (node: a ref, a node id, or "graph")
{"op": "connect", "from": "a", "to": "lv", "input": "input1", "output"?: "..."}
{"op": "disconnect", "node": "lv", "input": "input1"}
{"op": "move", "node": "lv", "position": [x, y]}
{"op": "delete", "node": "lv"}
{"op": "expose", "node": "lv", "param": "...", "input_id"?: "...", "label"?: "...", "default"?: ...,
 "min"?: 0, "max"?: 1, "step"?: 0.1, "group"?: "..."}
add: definition is atomic ('levels', 'blend') or library ('tile_generator', 'hbao.sbs/hbao', 'materials/pbr/bricks_001');
  position is the node's centre, by default to the right of the existing nodes; params as in set, and a bad one
  refuses the whole add, so no node is left.
identifier, label, usage: an output node's, on add or set; a set op gives these or params. identifier is the exported
  file's name (letters, digits, _ and -), label its display name, usage its tag, such as baseColor, normal, roughness,
  metallic, height or ambientOcclusion, which replaces any tag it had (RGBA; sRGB for baseColor, diffuse, emissive and
  specular, otherwise Linear). On another node, with params on a set op, or badly formed, they refuse the whole batch; an
  identifier another output has, in any case, is refused when its op runs, since export_outputs refuses two such outputs.
  Renaming an output that existed before this call can break a closed graph using it: the result says so, tell the user.
  describe_graph shows them.
bitmap: an image file (png, jpg, tga, exr, tif, psd...) as a Bitmap node (output connector
  `unique_filter_output`), for references, masks and hand-painted maps. embed: "link"
  references the file where it is (an existing link to the same file is reused); "copy" copies
  it into `<package>.resources/` (into a temp folder until the package is saved). Embedding the
  image in the .sbs is not available through the API. The node's size is each side rounded up to
  a power of 2, 8192 px at most, the image stretched or shrunk to it (50x10 computes 64x16); set
  its `$outputsize` to change it. name: resource identifier (default: the file name).
set: node "graph" = the graph itself, e.g. a fixed-size graph's $outputsize (an overridable
  graph's size is refused: use set_graph_size). Values are converted to the parameter's type:
  numbers, bools, lists for vectors/colors ([r,g,b(,a)]), enums by id or number ('max', 5 or
  '5'). Every value is checked before any is set. A parameter driven by a graph input (an
  expose op) or a function is refused: set the graph input instead (node "graph"), or replace the
  function with set_function; so is one with a function that has no output node, which drives
  nothing but would be deleted. A $
  parameter is made Absolute so its value takes effect ($format and $outputsize ignore theirs
  while inherited); except $randomseed, on a node or the graph, whose inheritance is left as it
  is: inherited, its value counts (added to the parent's seed), and only an inherited seed
  follows the graph's seed and the cooked .sbsar's Random Seed. To fix a seed on purpose,
  change its inheritance with execute_designer_code. Prints old -> new for params. $outputsize is log2 of the size in pixels (11 is 2048 px; above 13 or below 0 is refused).
  A Gradient Map's gradientrgba takes keys [[position, [r, g, b(, a)]], ...], position 0 to 1, alpha 1 if left out; an
  optional third item is the midpoint, 0 if left out. The Gradient Map's own interpmode is linear at 0, its default,
  where midpoints change nothing, eases at 1, where they act, and at 3 holds each key's colour up to the next. At
  interpmode 0, of two keys at one position, the first listed shows. At interpmode 0, a colour input gave every pixel
  the colour of the key at position 0, also listed first. A Curve's curveluminance, curvered, curvegreen, curveblue
  and curvealpha take points [[x, y], ...], x 0 to 1, joined by straight lines; [[x, y], [left x, y], [right x, y]]
  gives a point Bezier handles, as absolute points, and set makes every point unlocked and unbroken. Only curveluminance acts on a grey input. On a
  colour one it acts on R, G and B after curvered, and each other array on its own channel. The list replaces every
  key, [] removes them. The result and describe_graph(include_params) read them back in this shape, a broken side with
  its handle on its point; past 16 keys, a whole graph's listing gives their count, and node_ids on the node gives
  every key.
connect: from's output (default: the one tagged base colour, else its first; the result says which) to to's input connector; replaces an existing
  link on that input. An input "#name" (a letter after the #) is an input value of the to node, which set_function's
  expressions on that node read as #name. It is made with the output's type if missing; the output must be a value (a
  Value Processor's) of its type. A Pixel or Value Processor's second and later input images are "input:1",
  "input:2"...: each appears once the one before it has a connection, so connect them in order.
disconnect: removes the connection(s) going into the node's input connector.
delete: the node and its connections.
expose: a node parameter as a graph input (same type as the parameter; enums become ints),
  like Designer's own "Expose" action. The input starts at the parameter's current value
  unless default is given; min/max/step/group set the slider. The input then shows up in
  sbsar_info and can be set with render_sbs(params=...). Refuses a parameter that already has a
  function with nodes (replacing it would lose that logic)."""


@_tool(read_only=False, destructive=True, idempotent=False, open_world=False)
def apply_edits(ops: Annotated[list[JsonObject], Field(description=OPS)], graph: Graph = None) -> str:
    """Edit a graph: one or more ops in one call and one undo step.
    Refs let later ops use nodes added earlier in the batch ("ref" is optional, a string other than "graph";
    the result prints each new node's id). Every field's name, every node an op names, and every position, is
    checked before any op runs: a field the op doesn't take, an unknown id, a ref not added by an earlier op, a node an
    earlier delete op removes, "graph" anywhere but a set op, a position that isn't [x, y], or a wrong identifier, label or
    usage (see ops) refuses the whole batch, nothing changed. Other mistakes (a missing field, a wrong connector or parameter id, a bad value) show only when their op
    runs: ops run in order and stop at the first failing one (earlier ops stay applied, and the error
    lists the nodes already added, with their refs; Ctrl+Z on the graph reverts the whole batch)."""
    ops = [{**op, 'path': _local_path(path)} if isinstance(path := op.get('path'), str) else op for op in ops]
    return _edit('apply_edits(%r, %r)' % (graph, ops), 'Claude: apply %d edits' % len(ops))
