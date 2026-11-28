# GUIDE.md: notes for AI agents driving Substance Designer

`get_guide()` serves this part, the core, which every Designer session reads. `get_guide('scripting')` serves the part
for raw `sd` and Qt code, at the end.

## Rules that protect the user's work

- **Never print, log or send the bridge token** (`~/.sd_claude_bridge_kve_token`): it gives code execution in Designer.
- **Undo your own work with `undo_edits`, and only with it.** It takes back your calls, newest first. If steps
  that aren't yours sit on top of them (the user's, or another session's), it stops and names them: ask the user
  whether those may be undone too, and if they agree, call it again with `include_others`. With no such steps on top,
  undo as you need. Designer keeps one Undo history, shared by all packages, so any other Undo can hit the user's
  step (it happened once; an immediate Redo restored it). A call that fails after it changed something takes back its
  own step itself, only when that step, named with the call's tag, is on top (`_with_undo`, `server_tools/core.py`).
- **A Designer the user opened is theirs: never close it.** If a task needs it closed or restarted, or needs Designer
  while it is closed, ask the user to save, close and reopen it, or to open it. Don't get around that with `kill` or a
  script, even when the user asks: tell them to close it, as Designer then asks them about unsaved work itself. A
  Designer an agent started is disposable: `quit_designer` ends it. Close yours when done, so the user doesn't start
  working in it.
- **`snapshot_graph` before risky or large edits** to a user's graph, then `diff_graph` and report the diff.
- **Never hot-reload the sd_claude_bridge_kve plugin** (`importlib.reload` inside Designer): the running server keeps
  references to the old module and the bridge breaks until Designer restarts.

## Which tool for what

Parameters are described in each tool's schema; this is when to reach for which.

- **Start:** `designer_status`; `quit_designer` (the rules).
- **Find and understand nodes:** `search_nodes`, then `describe_node` for connector ids, parameter types, **enum
  values**, library slider ranges. Never guess ids or enum numbers; pick values inside the slider range.
- **Inspect a graph:** `describe_graph`, `list_graph_inputs`.
- **Safety net:** `undo_edits`, `snapshot_graph`, `list_snapshots`, `diff_graph` (the rules).
- **Look:** `preview_node` (any node, even one feeding no output), `screenshot_designer` (what the user sees),
  `open_graph` (open the graph first, so the user and screenshots see it). A material on a mesh, in Designer's own
  renderer: `screenshot_designer('3d', graph=...)`; `mesh='Plane'`, `view='Top'` and `tiling=2` show how it repeats.
  A material made for one asset is judged on it: `mesh=` takes the path of the asset's mesh file.
  `shader_model` renders the material under another shader model. What the 3D view shows, with no image:
  `screenshot_designer('3d', as_text=True)`.
- **Measure:** `node_stats` (exact numbers; prefer them to eyeballing), `check_tiling` (trim sheets only need
  horizontal), `compare_to_reference` for tones against a reference image (add it to the graph with an `apply_edits`
  `bitmap` op if wanted). `node_stats(against=...)` compares two outputs pixel by pixel, of two nodes or of one.
  `analyze_reference` reads a photo's palette as Gradient Map keys; its result says how to read its errors.
- **Tune a value:** `sweep_param`, not edit-rebuild-look loops.
- **Edit:** `apply_edits` for every node edit, one or many. Also `create_graph`, `remove_graph_input`,
  `set_graph_size`.
- **Write a function:** `set_function`.
- **Make graphs readable** (every graph you build or restructure): `arrange_graph` (positions only), then `add_frame`
  per logical section and `add_comment` for non-obvious choices.
  - **Portals when the wires get cluttered.** Check with `screenshot_designer('graph')` after `open_graph`. Signs: one
    output fanning out to many nodes, wires crossing sections, a bundle you can't follow. Then
    `set_link_display(mode='portal')`, typically `fanout_at_least=4` plus `longer_than=1000`, screenshot again, and keep
    short local wires visible.
- **Bigger logic:** `run_designer_script` (a script on disk, preferred for anything long) or `execute_designer_code`;
  `cancel_designer_job` aborts. Read `get_guide('scripting')` first and confirm to the user: until then those two refuse
  to run.
- **Output:** `save_package`; `export_outputs`; `sbsar_info` + `render_sbs` (exposed params, size, formats);
  `preview_maps` for rendered files.
- **Diagnose:** `read_designer_log` when the bridge misbehaves.

**Loop:** search/describe → build (script or `apply_edits`) → `describe_graph` + `preview_node` on intermediate nodes →
`sweep_param` → `node_stats` / `check_tiling` → render or export → `preview_maps` → fix → repeat. Look at the result,
on a mesh too (`screenshot_designer('3d', graph=...)`), before telling the user it works.

Fallback without MCP: `client/sd_run.py script.py [--timeout N]`, `-c CODE`, `--status`, `--cancel`, run with a Python
3.12+ such as the venv's (no undo grouping, no `ARGS`).

## Environment facts

- Crash dumps: Designer's `Sentry-Crashpad/completed` (`pending` while its upload waits; for one an agent started on
  macOS, under `/tmp/sd_mcp_<uid>_<port>/home`). How: `server_tools/lifecycle.py`.

## First sd pitfalls

- `$outputsize` is log2 of the size in pixels (11 is 2048 px, 13 is 8192 px, the largest; `apply_edits`, `sweep_param`,
  `create_graph` and `set_graph_size` refuse more). That holds at Absolute, which is what `set` makes it; while
  inherited it is a log2 offset, and so is a graph input bound to it (`describe_graph` shows `0 x 0` for an overridable
  graph). Generators inherit the graph size; filters inherit from their input, a Pixel Processor from the graph. Node
  positions are node **centres**; a node is 96×96 graph units.
- **`sd.api.apiexception.APIException` derives from `BaseException`, not `Exception`:** `except Exception` won't catch
  it. Use `except (Exception, APIException)`.
- Valid atomic ids: `graph.getNodeDefinitions()` (29 in Designer 16; a function graph lists `sbs::function::*`). Check
  an id is in that set **before** `graph.newNode(id)`: an unknown id reportedly hangs Designer 15 (16 raises).
- Blend modes: copy 0, add 1, subtract 2 (enum id spelled `substract`), multiply 3, addsub 4, max 5, min 6, switch 7,
  divide 8, overlay 9, screen 10, softlight 11.

## Library node facts (Designer 16)

- `gradient_linear_1` with `rotation` 0: **1.0 at the top row, 0.0 at the bottom**, constant across x. With levels this
  makes a vertical coordinate, handy for per-row height profiles (bands, chamfers) in trim sheets.
- `tile_generator`: `Offset` is the row offset. The same layout and `Offset_Random_Seed` twice give a matching per-tile
  random mask, with `Luminance_Variation-Contrast` on the second.
- `bevel`: `distance` ~0.02–0.08 for small chamfers.
- Ready-made materials (`materials/pbr/...`): outputs start with `diffuse`, which is black on a metal (`metal_003`).
- `noise_anisotropic_noise`: default streaks run horizontally (`X_Amount`, `Y_Amount`).
- Atomic `warp` intensity is strong: ~0.05–0.1 gives a gentle wave; 1.5 destroys the pattern.
- Atomic `normal`: `inversedy=True` gives **OpenGL** normals (Blender): where height rises towards the top of the image,
  green is below 0.5 (a raised band's top chamfer is above 0.5).
- `curvature_smooth`'s `normal_format` (DirectX 0, OpenGL 1) must match the normals fed: 1 after atomic `normal` with
  `inversedy=True`, 0 after `inversedy=False`. The other value reads a horizontal ridge as concave.
- Atomic `blend`'s `opacity` input, `opacitymult` at 1, its default, in every `blendingmode`: a grey image there is
  the opacity. A colour one gave the `destination`, as opacity 0, also with R = G = B. Grey and colour are the image's
  type, LUM or RGBA, as `node_stats` names its format. A Pixel Processor's float with `colorswitch` on, its default,
  is RGBA, and so is the bitmap of an RGB PNG. The bitmap of an 8-bit grey PNG is LUM, a mask as it is. For a mask,
  turn a Pixel Processor's `colorswitch` off, or add Grayscale Conversion. The cases measured: the scripting part, A
  blend's opacity.
- Atomic `blend` of a grey image and a colour one: it gives its `destination`'s type, and a `source` of the other type
  blends as a zero of that type. So a grey `source` over a colour `destination` gives the `destination`, in every
  `blendingmode` but switch. The cases measured: the scripting part, A blend of a grey image and a colour one.

# Scripting: raw `sd` and Qt code

Served by `get_guide('scripting')`: read it before writing code for `execute_designer_code` or `run_designer_script`.
The rules and the first pitfalls are in the core, `get_guide()`. Changing this project itself:
[AGENTS.md](../AGENTS.md).

## sd API gotchas

- No `pysbs` (the Automation Toolkit is enterprise-licensed): everything goes through the in-app `sd` API via the
  bridge, plus `sbscooker`/`sbsrender`.
- Code runs on Designer's main thread, so the UI freezes while a script runs. Keep scripts finite.
- Atomic nodes: `graph.newNode('sbs::compositing::<name>')`, output connector `unique_filter_output`. Common inputs:
  `input1` (levels, blur, normal, warp, directionalwarp, transformation…), blend `source` / `destination` / `opacity`,
  warp `inputgradient`, directionalwarp `inputintensity`, output node `inputNodeOutput`.
- Library graphs in a script: they are in `app.getPath(SDApplicationPath.DefaultResourcesDir)/packages` and its
  subfolders; `pkgMgr.loadUserPackage(path)` loads one (check `getPackages()` first to reuse an open one), then
  `pkg.findResourceFromUrl('<graph id>')` and `graph.newInstanceNode(resource)`. A loaded library package is among
  `getUserPackages()` too: the API has no flag for it. The tools refuse to change a library graph, but your own code
  isn't checked: Designer takes an edit to a library graph, and a package using it sees it at once (seen by hand).
- Instance (library) nodes: connector ids are the library graph's identifiers (bevel: in `input`, outs `height` /
  `normal`; tile_generator: out `TileGenerator`).
- Property types matter (`node.getPropertyFromId(id, SDPropertyCategory.Input).getType()`): levels `levelin*/levelout*`
  are **float4**; uniform `outputcolor` is **ColorRGBA**; `blendingmode`, `$format`, `$tiling` are **enums** (set via an
  enumerator's `getDefaultValue()` or `SDValueEnum.sFromValueId(type, id)`). `apply_edits`' `set` op converts for you
  and validates before changing anything.
- `$format` enum ids: `8_bits_per_channel`, `16_bits_per_channel`, `hdr_low_precision`, `hdr_high_precision` (type
  `sbs::compositing::format`).
- Bitmaps: `SDResourceBitmap.sNewFromFile(pkg, path, EmbedMethod.X)` + `graph.newInstanceNode(res)` gives an atomic
  `bitmap` node (out `unique_filter_output`, param `bitmapresourcepath` = `pkg:///<resource id>`). The `EmbedMethod`
  docstrings in `sdresource.py` are shifted by one: `Linked` references the original file; `CopiedAndLinked` copies it
  into `<package>.resources/` with an `XXXXXX-` prefix (before the package's first save, into
  `<QDir.tempPath()>/Adobe/Adobe Substance 3D Designer/` (Designer's own temp folder), moved on saving; copies there
  stay after an unsaved package closes, and a later copy of a taken name gets `1-`, `2-`... in front); `BinaryEmbedded`
  raises `NotSupported`. The node's `$outputsize` is the log2 of each of the image's sides, rounded up, and the image
  is stretched to that size with a bilinear filter, not padded: a 50x10 image computed 64x16, its two halves meeting
  at x 32 with two pixels blended. A side computes 8192 px at most, even where `$outputsize` reads 14, the image shrunk
  to it: a 9000x10 image computed 8192x16, two pixels blended at its halves' boundary ("designer facts", the `bitmaps`
  check of bitmap sizes). A JPEG's EXIF orientation is applied (3, 6 and 8 measured, and a multi-picture JPEG's, saved
  as .jpg), and a PNG's (eXIf) and a TIFF's are kept in the stored frame (the `bitmaps` check of orientations). How
  the reference tools read a file's orientation: their `reference_region`'s description.
- **Pixel buffers:** a texture's raw buffer, which `node_stats` reads: little-endian, uint8 / uint16 / float16 / float32
  per `getPixelFormat()`, row stride `getRowPitch()`. Outputs seen so far are `RGBA*` or `LUM*` (even an imported RGB
  JPG or grey+alpha PNG computes as `RGBA8`); the other `SBSPixelFormat` layouts (`RGB*`, `BGR8`, `BGRA8`,
  `LUMALPHA*`) are decoded too, untested against Designer.
- **The abort of a timeout or `cancel_designer_job`** comes from a trace hook in the plugin. A script catching
  `BaseException` swallows it: don't.
- **An abort landing where Python only reports an exception** (a finalizer such as every sd object's `__del__`, a
  weakref callback, a Qt slot) is raised again at the next traced event (in the script, a module it imports or a loop
  driven from C), also when the finalizer raises an error of its own or runs long.
- **Output nodes:** annotation `usages` = `SDValueArray` of `SDValueUsage.sNew(SDUsage.sNew('baseColor', 'RGBA',
  'sRGB'))`; annotations `identifier` / `label` via `SDValueString`. The identifier becomes the exported/rendered file
  name; `apply_edits` sets all three. In your own code Designer checks little: a new output gets a name of its own
  (`output`, `output_1`), but two can be given the same one; other characters are rewritten (`../a b.c` gives
  `___a_b_c`; `1abc` and `a-b` stay); a usage's name, components and colour space are taken as given; another node
  raises. **Renaming an output reaches only what is open.** A graph using it through an instance, open during the
  rename, follows (connector and link renamed, also after saving and reloading). One that was closed keeps the old
  connector and computes black, with no error and not marked modified. A new instance wired from the new name computes
  right again, with default parameters. Renaming back with that graph open doesn't help: the connector and the link go
  too.
- **Connections are reported from the queried node's side:** for `c` in `node.getPropertyConnections(prop)`,
  `getOutputPropertyNode()` / `getOutputProperty()` is `node`/`prop` itself and `getInputPropertyNode()` is the
  **other** node, whatever direction the data flows.
- `graph.compute()` computes the nodes feeding an **output node**, and takes about 0.9 s however small the graph, with
  nothing changed since the last one too (measured: a 3-node 4×4 graph and a 63-node one): build what you need to read,
  compute once, then read every node. `node.getPropertyValue(outputProp).get()` is then an `SDTexture`. A node feeding no output got no texture in a fresh
  graph but did in the self-test's busier one, so rely on neither: attach a temporary output node, as `preview_node` and
  `node_stats` do.
- Exposing a parameter = a graph input via `graph.newProperty(id, type, SDPropertyCategory.Input)` (annotations `label`,
  `min`, `max`, `step`, `group`…) plus a function graph on the node parameter (`node.newPropertyGraph(prop,
  'SDSBSFunctionGraph')`) whose output node is `sbs::function::get_<type>` with `__constant__` = the input id
  (`get_float1..4`, `get_integer1..4`, `get_bool`, `get_string`). Use the parameter's own type; enums → int. What a
  function graph on a parameter does (float4 and enum parameters of atomic nodes, float4 of an instance node, "designer
  facts"; only a graph with an output node drives the value, and `fg.getOutputNodes()` tells, also after a reload):

  | Function graph | Output follows | `setPropertyValue` | `deletePropertyGraph` | The tools |
  |---|---|---|---|---|
  | None | stored value | sets it | - | set, sweep, expose |
  | Empty | stored value | sets it, **deletes the graph** | stored value stays reset | set, sweep, expose (reuses it) |
  | Nodes, no output node | stored value | sets it, **deletes the graph and its nodes** | stored value stays reset | refuse, and say it drives nothing; `set_function` replaces it |
  | Nodes and an output node | the function | sets it, **deletes the graph and its nodes** | stored value stays reset | refuse; `set_function` replaces it |

  `$` parameters differ: `deletePropertyGraph` switches any of them back to the node's default inheritance (relative to
  input on a levels node, all six; relative to parent on an instance node, `$outputsize` measured), so put the inheritance
  back, then set the value, as `remove_graph_input` does. At Absolute, `$outputsize` with an empty function or none
  reaching an output node follows its input or parent, not the stored value. Setting an int on an enum parameter is
  accepted whatever it is, and a value beyond the enum's can't be read back (`get()` raises). Adding a function graph
  resets the stored value to the default. `newPropertyGraph` on a parameter that has one returns it, nodes kept. A graph
  has one output node: `setOutputNode(k, True)` moves it to `k`, leaving the old function unused in the graph. A `get`
  node not feeding the output has no effect (`list_graph_inputs` leaves it out of `drives:`). An FX-Map's own graph
  (`node.getReferencedResource()`, no identifier) holds functions that read the graph's inputs too: its output follows
  such an input, and the tools count and list them. A function on the graph's own parameter drives it too (measured on
  `$outputsize`), but `SDGraph` has no `getPropertyGraph`, so the tools read those from the package's file, as last
  saved. Removing an input that a connected `get` reads changes the output with no error, so `remove_graph_input`
  refuses while a function other than a plain binding (one `get`, its output) names it.
- **Building a function graph** ("designer facts", the `functions` checks):
  - **The definitions:** `app.getModuleMgr().getModuleFromId('sbs::function').getDefinitions()` lists 85. Each has
    its inputs and one output, `unique_filter_output`. Read a property's types with `getTypes()`. `getType()` gives
    only the first: `int` for an unconnected `add`, which lists all eight number types. Every input but `__constant__`
    connects.
  - **Input ids:** `a` and `b` on operators and comparisons, `a` alone on one-argument functions. `mulscalar` takes `a`
    and `scalar`, `lerp` `a`, `b` and `x`, `ifelse` `condition`, `ifpath` and `elsepath`, `cartesian` `rho` and
    `theta`. Vectors take `componentsin` and `componentslast`, swizzles `vector`, the casts (`tofloat*`, `toint*`)
    `value`, `samplecol` and `samplelum` `pos`. `atan2` takes one float2, `a`. There is no `clamp`, `length`,
    `normalize`, `step`, `frac`, `asin` or `acos`.
  - **`atan2`** of a float2 (x, y) gives atan2(y, x) in radians: (1, 0) gives 0, (0, 1) π/2, (-1, 0) π and (0, -1)
    -π/2. So y is the second component, a `vector2`'s `componentslast`.
  - **Variables:** a `get_*` node whose `__constant__` is a variable's name reads it. In a Pixel Processor of an 8 px
    graph, `get_float2` reads `$pos` as the pixel's centre over the size, y from the top row: (0.06, 0.06) at pixel
    (0, 0) and (0.69, 0.31) at pixel (5, 2), read at 8 bits. `get_float2` reads `$size` as (8, 8) and `$sizelog2` as
    (3, 3), and `get_integer1` reads `$tiling` as 3. In a Value Processor's function of that graph, `$pos` reads (0, 0)
    and `$size` (8, 8). In a parameter's (a blend's `opacitymult`), `$size` reads (8, 8), and `$pos` isn't the pixel's:
    at pixel (5, 2), where a Pixel Processor's reads (0.69, 0.31), it reads something else. So `$pos` is the pixel's
    only in a Pixel Processor's function and the function graphs one calls. `set_function` refuses it in a Value
    Processor's function and in a parameter's. It takes it in a function graph's, which can't know its callers, and a
    call to that function graph from either of those isn't checked. Adobe's system-variables page gives these types, and
    a float for `$time`, which isn't measured. Adobe's page lists `$depth` and `$number` under the FX-Map, and
    Designer's own packages read them only in FX-Map graphs.
  - **Types:** an `add`'s first connection settles its inputs and output: a float2 into its `a`, or into its `b`, makes
    `a`, `b` and the output float2. **A connection of the wrong type is made anyway, raising nothing**, such
    as a float into that `add`'s `b`, or into `samplecol`'s float2 `pos`: the input then holds that one connection.
    That `add` of a float2 and a float computes the float2 alone, so check the types before connecting. `gt` takes int
    or float and gives a bool. `ifelse` lists eleven types until `ifpath` is connected, then takes its type. `dot` of a
    float2 gives a float, and `mulscalar` of a float3 a float3.
  - **Constants:** `__constant__` takes the value class of the node's type: `SDValueFloat` on `const_float1`,
    `SDValueFloat2` to `SDValueFloat4` on `const_float2` to `const_float4`, and so on for `const_int*` (`SDValueInt`
    on `const_int1`), `const_bool` and `const_string`. Another class raised `APIException` `InvalidType`: an
    `SDValueFloat` on `const_float2`, an `SDValueInt` on `const_float1`.
  - **Swizzles:** `swizzle1`'s `__constant__` is an int, 0 for x up to 3 for w. `swizzle2` to `swizzle4` take an int2
    to int4, one index per component of the result: (2, 0) gives (z, x), (2, 0, 1) gives (z, x, y), and (3, 2, 1, 0)
    gives (w, z, y, x).
  - **Vectors:** `vector3` and `vector4` put `componentsin` first. `vector3` takes a float or a float2 on each input,
    `vector4` a float, a float2 or a float3. Sizes that don't add up connect too, raising nothing: the missing
    components compute 0, and the extra ones are dropped.
  - **What nodes compute**, of asymmetric constants, against Python's values:
    - as Python does: the order of `vector2` to `vector4`, `ivector2` to `ivector4`, the swizzles and the `iswizzle`s;
      `sub`, `div`, `pow`, `mod` and `lerp` (`x` weighs `b`), and `sub`, `div`, `pow`, `mod`, `min` and `max` of two
      float2 component by component; `lr`, `lreq`, `gt`, `gteq`, `eq` and `noteq` as `<`, `<=`, `>`, `>=`, `==` and
      `!=`; `and`, `or` and `not`. Float `mod` of -0.3 by 1 gives 0.7, as Python's `%`;
    - so do `abs`, `sqrt`, `sin`, `cos`, `tan` (angles in radians), `exp`, `log` (the natural one), `log2`, `floor`
      and `ceil` (-0.3 gives -1 and 0), `neg`, `min`, `max` and `dot` of floats. `rand` of 0.1 gave a value from 0 to
      0.1. `rand` of 1 in a Pixel Processor gave values varying from pixel to pixel: more than 8 among the 16 pixels
      of a 4 px graph;
    - `ifelse` takes `ifpath` when the condition is true. `cartesian` takes (rho, theta), theta in radians. `mul` of
      two float2 multiplies them component by component. `toint1` to `toint4` truncate (1.7 gives 1, 2.5 gives 2), and
      so does `div` of the ints 7 and 2 (3);
    - **a negative int computes a wrong value** (measured on macOS arm64): `lr` of -1 and 1 is false, `div` of 7 by
      -2, `mod` of -7 by 3 and `neg` of 3 give 0, and a constant -7 cast to a float gives 5 or more, as does `sub` of
      the ints 2 and 5. `toint1` of a negative float gives 0. Signed values need floats.
  - **A processor's function:** a new Pixel or Value Processor has none: `getPropertyGraph` and
    `getReferencedResource()` give None. `newPropertyGraph(prop, 'SDSBSFunctionGraph')` makes it.
  - **`perpixel`** lists float4 whatever `colorswitch` says (on by default), also once its function's output node is a
    float, with `colorswitch` on or off. What that output computes:
    - `colorswitch` on gives a colour texture (RGBA8 in an 8-bit graph): a float4 is the colour, a float its value in
      R, G and B, alpha 1;
    - `colorswitch` off gives a grayscale one (LUM8 in an 8-bit graph): a float is the value, a float4 the mean of its
      R, G and B, alpha left out;
    - a float2, a float3, a bool, or an int to int4 computes black either way, raising nothing. Of these number and
      bool types, only a float or a float4 makes a value.
  - **A Value Processor's** `function` lists bool, int to int4 and float to float4. Its output takes the type of its
    function's output node: float with none, then float2, bool, int3 or float4 as that node changed.
  - **Replacing a Pixel Processor's function** keeps the node's connections, its `$randomseed` and an Absolute
    `$outputsize`, and computes the new function, each of three ways:
    - new nodes built beside the old ones, the output node moved to them, then the old ones deleted;
    - the old nodes deleted, then new ones built;
    - `deletePropertyGraph` on `perpixel`, then `newPropertyGraph`. Unlike a `$` parameter's own function (above),
      deleting `perpixel`'s left the `$outputsize` inheritance as it was.
  - **A function on a `$` parameter** of a uniform colour in a 64 px graph: at the uniform's default inheritance,
    RelativeToParent, one on `$outputsize` gives an offset (the int2 (1, 1) computed 128 px), and one on `$format` is
    ignored (the int 1 left RGBA8). Made Absolute after the function is built, the function stays and both take effect:
    2 px, and RGBA16. `set_function` makes them Absolute, as `apply_edits`' `set` does.
  - **A Pixel Processor's size:** its `$outputsize` defaults to RelativeToParent 0,0, so it computes at the graph's
    size, not its input's: 64 px in a 64 px graph from an 8 px input, where a levels node computes 8 px. RelativeToInput
    sizes it from the graph too: 64 px at 0,0, 128 px at 1,1. Only Absolute gives it a size of its own.
  - **Input values** carry a value from one node into another's functions:
    - `node.newProperty('#x', SDTypeFloat.sNew(), SDPropertyCategory.Input)` makes one: a connector of that type,
      which `getProperties` lists. A name without `#` gets one added (`y` gives `#y`). The type of a Value Processor's
      output makes one of that type, for each of the nine it gives (bool, int to int4, float to float4);
    - on an instance of a library graph (`contrast_luminosity_grayscale`), `apply_edits`' `connect` into `#v` makes it
      on the node alone: the library graph has no `#v` after it, and its package doesn't read as modified. The node's
      `Luminosity`, its function reading `#v`, followed the Value Processor: 0, then 0.3;
    - `vp.newPropertyConnectionFromId('unique_filter_output', node, '#x')` connects into it, and a second connection
      replaces the first. Connecting into `x` raises `ItemNotFound`;
    - a `get_*` node whose `__constant__` is `#x` reads the node's own `#x`: in a parameter's function (a blend's
      `opacitymult` followed the Value Processor, 0.25 then 0.75), in a Pixel Processor's `perpixel` and in a Value
      Processor's `function`. In a Pixel Processor, a name the node lacks reads 0. In a Pixel Processor's `perpixel`
      and a Value Processor's `function`, a float `#x` with nothing connected, never or after a disconnect, reads 0
      too: each read + 0.5 gave 0.5. Other types aren't measured;
    - **a mismatch connects and computes a wrong value, raising nothing:**
      - an image, or a float2, into a float `#x` made `opacitymult` compute 1, not the value. So did a `#x` with
        nothing connected, never or after a disconnect, read in `opacitymult`'s function;
      - a float `#x` read with `get_float2`, in a `vector4` with (0, 1), gave (0, 1, 0, 0);
      - when the Value Processor's output changes type, the connection stays and `#x` keeps its own type. Reading it
        then computed 1 too.

      So `apply_edits`' `connect` refuses an image or a value of another type, and `set_function` reads `#x` with the
      getter of its type. `set_function` also refuses a `#name` fed another type, one with nothing connected in a
      parameter's function, and a Value Processor's result of another type than an input value it drives. In a
      processor's own function, it says that a `#name` has nothing connected, and that a float one reads 0;
    - the drive survives a save with `savePackageAs` (what `save_package` calls given a path) and a reload: `#x`, its
      connection and the function. After the reload, the blend read the value saved, not one changed after the save,
      and followed the Value Processor;
    - one Undo of `apply_edits`' connect into a new `#x` removes the connection and `#x`, and Redo brings both back
      (the `undo` category).
  - **Function graphs of the package** (the `resources` part of the `functions` checks):
    - `SDSBSFunctionGraph.sNew(package)` makes one, and `setIdentifier` names it. An identifier the package has already
      gets `_1` added: a second `paint` is `paint_1`, and so is one named like the package's compositing graph.
      `delete()` removes one. `getType()` gives the class, `SDSBSFunctionGraph`, not what it returns;
    - `fn.newProperty('uv', SDTypeFloat2.sNew(), SDPropertyCategory.Input)` makes an input, of each type: bool, int to
      int4, float to float4 and string. `getProperties` lists them in the order they were made, also after a save and
      a reload. Ids such as `Uv`, `_k`, `k_`, `a1` and `x_2` are kept as given. Its body reads one with a `get_*` node
      whose `__constant__` is the input's id, as a graph input is read: measured with float, float2, int and bool
      inputs. Read there, `$pos`, `$size`, `$sizelog2` and `$tiling` read as in the calling Pixel Processor (a 4 px
      one measured);
    - a function graph has no output of its own: a call gives its output node's type (a float, float4, bool and int
      measured), which follows that node as it changes;
    - `fg.newInstanceNode(fn)` makes an `sbs::function::instance` node: one input per input of `fn`, of the same id and
      type, in its order, and the output `unique_filter_output`. `getReferencedResource()` gives `fn`. It computes
      `fn` with the values connected in a Pixel Processor's `perpixel`, a Value Processor's `function`, a parameter's
      function (a blend's `opacitymult`) and another function graph. An input left unconnected reads 0, (0, 0, 0) for a
      float3;
    - replacing `fn`'s nodes the way a node's function is replaced (built beside, the output moved, the old nodes
      deleted) after a compute, a call computes the new function. The call follows `fn`'s inputs at once: one added
      shows on it, and one deleted, or deleted and made again of another type, goes with the call's connection into
      it. The connections into the others stay, one after an input deleted too. An input made again is listed last.
      After such a change, some of the call's inputs listed no types until a save and a reload. The call follows a
      change of `fn`'s output's type too;
    - the call survives a save with `savePackageAs` and a reload;
    - one Undo of `set_function`'s `function` removes the function graph it made, and one Undo of a replacement brings
      back its inputs and nodes before; Redo brings each back (the `undo` category).

    `set_function`'s `function` builds one so: once the output node has moved, it keeps each input a function graph
    has that is the next one wanted, so that calls keep their connections into those, and it names what calls it when
    its inputs or output change.
  - **Sampling an image** (the `sampling` part of the `functions` checks): `samplecol` gives a float4, and `samplelum`
    a float, of a Pixel Processor's input image at `pos` (a Value Processor's: the last bullet):
    - `__constant__` is an int2: the input's index (0 for `input`, 1 for `input:1`...), then the mode. The mode is 1
      for bilinear (else nearest) plus 2 for clamp (else repeat), measured on a 4 px image at -0.1, 0.3, 0.7 and 1.1:
      along x with both nodes, along y with `samplecol`. A new node's is (0, 0): nearest, repeating. It holds an index
      up to 2147483647; 2147483648 wraps around to -2147483648;
    - `pos` is a float2 in `$pos`'s frame: (0, 0) the top-left corner, (1, 1) the bottom-right. Sampled at `$pos`, a
      pixel reads the input's same pixel (two measured);
    - `samplelum` gives the mean of R, G and B, as `perpixel` does with `colorswitch` off;
    - an index with nothing connected, beyond the inputs or between two connected ones, reads (0, 0, 0, 0): 70,
      2147483647 and -1 with `input` alone connected too, Designer answering after them. Index 39 of 40 inputs
      connected reads `input:39`;
    - a Value Processor's function samples its own input images: index 0 and 1 measured, nearest and repeating. A
      function graph samples its caller's: called from a Pixel Processor, and from a Value Processor.

    `set_function`'s `sample` and `sample_lum` build them, refusing a sample in a parameter's function, which has no
    input images, and an index above 2147483647. A sample of an input with nothing connected is built, and the result
    says it reads (0, 0, 0, 0) until an image is connected. A function graph's result says so for each node whose own
    function calls it, directly or through other function graphs; an FX-Map's inner nodes aren't read.
  - **A processor's input images** (the `image_inputs` part): a Pixel or Value Processor's second and later inputs are
    `input:1`, `input:2`...:
    - `newProperty` makes none: `input:1`, `input` and `input1`, of the input's type, raise `InvalidType`, and
      `isVariadic()` of `input` gives False;
    - `newPropertyConnectionFromId` connects into an input once the node lists it. A new node lists `input`, and a
      connection into the last one listed adds the next one, empty. One into an input not listed raises
      `ItemNotFound`. After 40 connections, `input:40` is listed next. A disconnected input stays listed while a later
      one is connected; once the later ones are disconnected too, the list ends with one empty input after the last
      connected;
    - the connections survive a save and a reload.

    So `apply_edits`' `connect` reaches `input:1` once `input` is connected, and its refusal of an input not listed
    names the one to connect first.
- **Gradient Map keys and Curve points** ("designer facts", the `params` check of keys; Undo, the `undo` category).
  Measured on a 16 px ramp in 32-bit float:
  - **The types:** a gradient's `gradientrgba` is an `SDTypeArray<sbs::compositing::gradient_key_rgba>`, whose
    members are `value` (ColorRGBA), `position` and `midpoint` (floats). A curve's `curveluminance`, `curvered`,
    `curvegreen`, `curveblue` and `curvealpha` are `SDTypeArray<sbs::compositing::curve_key>`, whose members are
    `position`, `left` and `right` (float2), and `isLocked`, `isLeftBroken` and `isRightBroken` (bools).
    `interpmode` (an int, 0) and `smoothness` (a float, 0.5) are the gradient node's own parameters, not a key's.
  - **A new node** has no keys, and `getDefaultValue()` of these parameters is None. A new `gradient_key_rgba` holds
    the colour (0, 0, 0, 1), position 0 and midpoint 0. A new `curve_key` holds (0, 0) in all three points, and False
    in each bool.
  - **Setting:** `node.setPropertyValue(prop, array)` takes an `SDValueArray` built with `SDValueArray.sNew(item, 0)`
    and `pushBack` of `SDValueStruct.sNew(item)` structs, and keeps the keys in the order given. It takes an array of
    another item type too, raising nothing: an array of `curve_key` became one key of the new key's values, and an
    array of floats no key. An empty array removes every key. A curve point's `isLocked` and broken flags read back as
    set. A value read is a copy: a set after the read leaves it
    as it was, and changing it changes nothing on the node. The array set is copied too. One Undo of `apply_edits`'
    set reverts a gradient's keys and a curve's points, and Redo brings them back (the `undo` category). The keys and
    their order survive a save and a reload.
  - **A gradient computes** its keys sorted by position, each key's colour exact at its position:
    - with no keys, it gives its input as a grey colour; with one key, that colour everywhere;
    - outside the first and last keys, the nearest key's colour;
    - a colour beyond 0..1 is kept in a float format, and alpha is interpolated too;
    - a key below position 0 (-0.1) made every pixel the last key's colour. One above 1 (1.5) is taken;
    - with `colorswitch` off, it gives the mean of the colour's R, G and B;
    - the midpoints, the `interpmode`s, two keys at one position and a colour image fed: `apply_edits`' `ops`, its
      `set` op.
  - **A curve computes** its points sorted by x, joined by Bezier segments whose handles are absolute points:
    - with no points it gives its input as it is, and with one point, its handles on it, that y everywhere;
    - handles on their point give straight lines. A point made from its position alone keeps its handles at (0, 0),
      which bend the curve: (0, 1) and (1, 0) so gave 0.072 at 0.2, where the line gives 0.8;
    - `isLocked` changes nothing computed. A side marked broken (`isLeftBroken`, `isRightBroken`) computes as if its
      handle were on its point, each side on its own: the first point's right side broken gave the curve with that
      handle on its point, and so did the second point's left side. Both sides of every point broken gave the
      straight line. A side facing no segment, the first point's left, its handle off its point, changed nothing,
      broken or not;
    - two points at one x make a step, each side of it the point given on that side;
    - outside the first and last points, the nearest point's y. A y beyond 0..1 is kept in a float format. A point at
      x -0.2 made the pixel at 0 compute 0, off the line through the points;
    - which arrays act on a grey input and on a colour one: `apply_edits`' `ops`, its `set` op.

  `apply_edits`' `set` and `fmt` follow these facts: `designer_helpers/edits.py` (`_given_keys`) and `core.py`
  (`_shown_keys`).
- **The greys of a colour image** ("designer facts", the `bitmaps` check of greys), measured in 32-bit float:
  - Grayscale Conversion's default `channelsweights`, (0.33, 0.33, 0.33, 0) as `describe_node` shows them, compute the
    mean of R, G and B, and so do those values set: red gave 0.3333 and white 1. Other weights are taken as given,
    not divided by their sum: (0.34, 0.33, 0.33, 0), summing to 1, gave 0.34 on red, and (0.5, 0.5, 0.5, 0) and
    (0.1, 0.1, 0.1, 0) gave 1.5 and 0.3 on white. `analyze_reference` reads its palette on the mean. Its
    description says how its keys map a photo's own grey.
  - Grayscale Conversion Advanced's `grayscale_type`: 0 Desaturation, the mean of the largest and the smallest of R, G
    and B; 1 Luma, Rec.601's weights (0.299, 0.587, 0.114); 2 Average, the mean; 3 Max; 4 Min. Its default is
    Desaturation.
- **A blend's opacity** ("designer facts", the `facts` check of a blend's opacity): an atomic blend, `blendingmode`
  copy, `opacitymult` at its default. Its sides are colour, a white `source` over a `destination` of (0.2, 0.4, 0.6,
  1), or grey, white over 0.2, in 8-bit, 16-bit and 32-bit float graphs. Fed into its `opacity` input:
  - grey images (LUM) gave their value as the opacity: a `uniform` and a Pixel Processor's float, each with
    `colorswitch` off, the bitmap of an 8-bit grey PNG (mode L), and Grayscale Conversion of three colour images: a
    `uniform`, a Pixel Processor's float with `colorswitch` on, and the bitmap of an RGB PNG whose R, G and B are
    equal;
  - colour images (RGBA) gave the `destination`, as opacity 0: `uniform`s with `colorswitch` on of grey, white, red,
    green and blue, white at alpha 0.5, a Pixel Processor's float with `colorswitch` on, and the bitmap of an RGB PNG
    whose R, G and B are equal;
  - with nothing connected, the blend gave its `source`.

  Every `blendingmode` was measured too, in a 32-bit float graph, a source of (0.7, 0.5, 0.3, 1) over that
  destination. In each, a grey `uniform` 0.5 gave the blend that `opacitymult` 0.5 gives with nothing connected. A
  colour `uniform` (0.5, 0.5, 0.5, 1) gave the one `opacitymult` 0 gives, the `destination`. The blends of
  `opacitymult` 0.5 and 0 differ in each mode.
- **A blend of a grey image and a colour one** ("designer facts", the `facts` check of a blend of a grey image and a
  colour one): an atomic blend whose `source` and `destination` differ in type, LUM and RGBA, gives the
  `destination`'s type. Its `source` blends as a zero of that type:
  - a grey `source` 0.3 over a colour `destination` of (0.2, 0.4, 0.6, 1) gave what a colour `uniform` (0, 0, 0, 0)
    gives there. In every `blendingmode` but switch, that was the `destination`;
  - a colour `source` of (0.3, 0.3, 0.3, 1) over a grey `destination` 0.2 gave what a grey `uniform` 0 gives there.

  Both were measured in a 32-bit float graph, in every `blendingmode`, with nothing in `opacity` and with a grey
  `uniform` 0.5 there. Each differed from the blend of a `source` 0.3 of the `destination`'s type. Designer drew the
  link of a LUM16 grey `source` into an RGBA8 colour `destination` red and dotted, and solid once the `destination`
  was grey (seen once, in a demo).
- **Graph size** is set with `graph.setInputPropertyValueFromId('$outputsize', SDValueInt2.sNew(int2(11, 11)))`;
  `setDefaultParentSize()` takes **pixels**. A node's `$format` and an absolute `$outputsize` only take effect with
  inheritance set to Absolute. The graph's own `$format` too (a new graph's follows its parent: 16 bits
  left a generator at RGBA8 until made Absolute). `apply_edits`' `set` op and `sweep_param` set Absolute for these. A
  `$randomseed` (graph or node) is the exception: inherited, its value is added to its parent's seed (a render's, or the
  graph's), and only an inherited graph seed stays a control of the cooked .sbsar; made Absolute, it stops following its
  parent. So the `set` op leaves a seed's inheritance as it is; to fix one on purpose, change it in code. **Changing a
  parameter's inheritance doesn't keep its value** (on a node's `$outputsize` and the graph's `$randomseed`, both
  directions; back to inherited gave the default): set the inheritance first, then the value (`sweep_param` restores in
  that order). Compare computed pixels with a tolerance: two computes of one setting differed by 2/65535, and raw
  buffers carry row padding.
- Frames: `SDGraphObjectFrame.sNew(graph)` with `setTitle`, `setPosition` (top-left), `setSize`, `setColor`,
  `setDescription`; comments: `SDGraphObjectComment.sNew(graph)` or `sNewAsChild(node)` with `setDescription`; list them
  with `graph.getGraphObjects()`.
- Slider ranges exist only for **library** node parameters, as annotations (`min`, `max`, `step`, `clamp`) on the
  referenced graph's input property. Atomic nodes have none.
- **Saving a package that uses a graph of a never-saved package opens a modal "Save Dependency" file dialog**
  (`savePackage`, `savePackageAs`, `saveCopyOfPackageAs`, measured): the call waits for a person, a timer calling
  `reject()` didn't close it, and cancelling raises `SDApiError.Undefined`. The tools refuse first; in a script, check
  `pkg.getDependencies()` for an empty `getFilePath()`. A saved dependency with unsaved changes opens none. A
  never-saved package closed while in use stays such a dependency until the nodes using it are deleted; a package's own
  graphs aren't listed. A dependency whose file is gone has a path and `getPackage()` `None`, and saves with no dialog.
- `pkgMgr.saveCopyOfPackageAs(pkg, path)` writes a copy without changing the package's path or saved state (what
  snapshots use); `savePackageAs` changes both. `SDPackage.isModified()` tells whether a package has unsaved changes. To
  close earlier builds of a generated graph, unload every user package containing its identifier.
- `SDPackage.getUID()` is the file's `<fileUID>`: unchanged by saving or Save As, and shared by a copy of the file loaded
  again and by a `saveCopyOfPackageAs` copy. A .sbs whose package-level `<fileUID>` (the first, before
  `<dependencies>`) is rewritten loads with the new UID: how snapshots of unsaved packages get their own. A package
  using another's graph stores the dependency by file name, its `<fileUID>` `"0"`, so a package whose UID changes (a
  snapshot restored over it) still serves it. Tell packages apart by file first. `mHandle` differs for every Python
  object wrapping the same package, so it identifies nothing.
- **Portals** are a per-connection display flag (`<displayType v="1"/>` in a node's own `<connections>/<connection>` in
  the .sbs; function graphs on parameters have their own connections, leave those alone) that the API can't read or set,
  so `set_link_display` uses the **file-level edit pattern** (Designer's own Dot-node portals:
  `server_tools/layout.py`). Use it for other things the API can't do: snapshot the live graph and copy the saved file,
  decide on the copy (no change → no save), save, edit the .sbs XML, then unload, load and reopen as **three separate
  bridge calls** (back to back, Designer once crashed while tearing down the old views; returning to its event loop
  between the steps lets that finish: the bridge runs it between two calls, and an unload's widgets were all gone by
  the next call, so no pause is needed; measured in Designers an agent started, hidden and on screen, not the active
  app). If it recurs, read the newest crash dump's crashing module first
  (in this repository: `scripts/read_crash_dump.py`).
  A package whose graphs were **never opened in a view** has nothing to tear down, so a script that builds one can save,
  edit and reload it in one call (the example script does, for its portals). Afterwards, check with `diff_graph` plus
  `node_stats`.
- **Inheritance numbers differ between the API and the file.** API `SDPropertyInheritanceMethod`: RelativeToInput 0,
  RelativeToParent 1, Absolute 2. A .sbs `<relativeTo>`: 0 absolute, 1 relative to parent, 2 relative to input; the
  default isn't stored (parent for a graph; a node's is its own, relative to input on a blur, relative to parent on an
  instance with no input).

## Designer UI (Qt)

- The graph editor's node view is a `QGraphicsView` inside the `areaB_` dock (a title bar and two toolbar rows above
  it); its **scene coordinates are graph units**. **Don't set its transform** (`fitInView`, `scale`): Designer keeps its
  own zoom level beside it, and the user's next wheel step jumps from that stale level (seen once). Zoom with synthetic
  `QWheelEvent`s on the viewport, 1.2x per notch in Designer 16, and pan with `centerOn` (safe); `open_graph(frame=...)`
  does this. **Don't send it synthetic key events or right-clicks**: twice (right-click menus, then a sent Ctrl+C, which
  copied nothing, as sent key events bypass Qt's shortcuts) the view went empty, its nodes intact, and only unloading
  the package brought it back. A synthetic left click on a node selected it and switched the Parameters panel to it
  (seen twice); `setSelected(True)` on its scene item selects it too (the API reports it) but leaves the panel as it
  was, and so does `clearSelection()`. The `editor_open_and_zoom` check of the Parameters panel ("designer facts")
  measures this on a node, a Dot, a frame and a comment, reading the panel after one `processEvents()` pass. It starts
  from the panel on the graph in the editor, then from the panel on another graph, which `setExplorerSelection` turns
  it to while the editor keeps its graph. The API itself can't select nodes in the view (`focusGraphNode` only centres
  one). After such experiments, restart Designer before real work (the user's: ask them): once, with the Parameters
  panel still showing a Dot of a package unloaded since, the next edit in another graph crashed Designer.
- **Unloading a package leaves the Parameters panel showing its graph**, even the graph that was in the editor
  ("designer facts", the `editor_open_and_zoom` check of the Parameters panel). `setExplorerSelection` of a graph still
  loaded turns the panel to it and keeps the graph in the editor, so a script can turn the panel off a package it
  unloads. The crash above didn't recur in 21 trials on macOS, in a Designer an agent started (2026-11-23), with the
  panel left on a graph, a Dot or a node of an unloaded package. Each trial went on with edits and computes in another
  graph through the tools, and a paint of the panel and a quit crashed nothing either.
- Current graph: `getQtForPythonUIMgr().getCurrentGraph()`; editor control via **`app.getUIMgr()`**:
  `openResourceInEditor(graph)`, `focusGraphNode(graphViewID, node)` (ids via `getGraphViewIDCount/At`,
  `getGraphFromGraphViewID`), `getGraphNodeBBox`, `setExplorerSelection`. `openResourceInEditor` opens a function
  graph of the package too: it is then the current graph, and the graph panel's title is its identifier. A node's
  function (a Pixel Processor's `perpixel`, a levels node's `leveloutlow`) it opens as the node's graph instead, also
  from a function graph open (the `editor` part of the `functions` checks), so `open_graph` refuses one. The dock's "Fit in view (selection)" (F) fits
  the selection, or everything when nothing is selected; `open_graph` fits every node, frame and free comment by wheel
  zoom instead.
- **The editor's selection**, which `describe_graph(selected=True)` reads ("designer facts", the `editor_open_and_zoom`
  checks of the selection getters):
  - `getQtForPythonUIMgr().getCurrentGraphSelectedNodes()` gives the selected nodes, a Dot too.
    `getCurrentGraphSelectedObjects()` gives the selected frames, comments (a node's own too) and pins. Each is
    empty, not None, when nothing is selected. A selected link is in neither. The sd API marks
    `getCurrentGraphSelection()` deprecated in favour of the first (`sd/api/qtforpythonuimgrwrapper.py`).
  - They read the graph in the editor, and show a `setSelected` at once, before any event is processed. Opening the
    graph already there keeps its selection. Opening another gives that graph's, and the first graph's selection is
    gone when it is opened again.
  - Once the editor's graph is closed and Designer's event loop has removed its view (`getGraphViewIDCount()` 0),
    `getCurrentGraph()` gives None and both getters raise `APIException` (`InvalidArgument`). So check
    `getCurrentGraph()` first.
- **Never call `parentItem()` on the graph view's scene items** ("designer facts", the `editor_open_and_zoom` check of
  `parentItem`). On a node's comment item, it made the node's item Python's (`shiboken6.Shiboken.ownedByPython` turned
  True). Python then deleted the item with its wrapper: the node left the view, still in the graph, and a later
  deletion crashed Designer (seen 2026-11-23). `Shiboken.invalidate()` on that wrapper at once left the item in the view.
- **Undo from a script:** don't. Undo your own work with `undo_edits` (the rules, in the core). It undoes each step
  only while it is on top of Designer's one Undo history, and waits in the same job until the step has landed, the
  user's input held (`mcp_server/designer_rollback.py`). Redo you may trigger from code when you need it, for example
  to bring back steps `undo_edits` undid (the user, 2026-11-25: "an agent can trigger redo from code as well if it
  needs it"). Don't open an undo group of your own either (`SDHistoryUtils.UndoGroup`, `newTransaction`): each code
  call is one step already, and a timeout or cancel inside your group can leave that step open (REVIEW.md SRV-275).
- **Quitting:** through `quit_designer` (the rules), not from a script: `QApplication.exit(0)` has crashed Designer and
  left it hung. The plugin answers status from another thread, so a main thread frozen outside a job reads as idle.
  How: `server_tools/lifecycle.py`.
- `getQtForPythonUIMgr().getMainWindow()` is a **hidden** QMainWindow; the window the user sees is a top-level
  `QStackedWidget` with two pages, the main window and the **Home screen** (current after a fresh start). While Home
  shows, no panel reports itself visible, so `launch_designer` and `open_graph` close it first.
- PySide wrappers for Designer's Qt objects go stale ("Internal C++ object already deleted") unless you keep Python
  references to their parents; menus fill lazily (emit `menu.aboutToShow` first).
- **Never install a Python event filter on the application** (`QApplication.instance().installEventFilter`): it is
  called with Qt's own long-lived objects too (the pixmap cache, for its timer), which get Python wrappers, and
  Designer aborts as it quits, after Python has shut down (a filter on 40 s, then a quit: a crash dump in PySide's
  clean-up; without it, none; measured 2026-11-12). Filter the widget you mean and remove the filter when done, as
  the watch of the 3D view's frames does (`designer_helpers/frames3d.py`).
- **Screenshots:** `QWidget.grab()` on Designer's widgets only. **Never use `QScreen.grabWindow`**, not even with
  Designer's own window id: on macOS both copy the screen area, capturing whatever covers Designer (the user's other
  apps). Widget capture can't see the GPU-drawn 3D view: use `screenshot_designer('3d')`. Never use "Save Render...":
  its modal file dialog blocks the bridge.
- **The 3D view** has no API: `screenshot_designer('3d', ...)` drives its menus and the Explorer's context menu (opened
  on the Explorer's tree only; the warning above about the graph view stands, and an open menu holds the bridge until it
  closes). Its camera, mesh, tiling, environment and shader model go through the view's own state file, which the Scene
  menu saves and loads; the shot writes it and puts it back, the user's view with it. A mesh file of the user's own is
  written there by its URL, which loads it with no file dialog. What Designer does there,
  measured: `designer_helpers/view3d.py`, `scene3d.py` and `state3d.py`. `as_text` reads the view without a render, from
  that file and from the 3D view's menus and title (how: `scene3d.py`, `_3d_shown`). How to tell when the view has drawn
  a change (its paints and its overlay's sample count), instead of waiting a fixed time: `designer_helpers/frames3d.py`.
- Dock titles change with content, so find panels by object name: `areaA_` explorer, `areaB_` graph, `areaC_`
  parameters, `areaD_` 3D view, `areaE_` 2D view, `areaF_` console (hidden by default; Windows > Console), `areaG_`
  library.

## Example

`examples/build_dwarf_trimsheet.py`: a config-driven generator for a 2048² stone + wood trim sheet (11 horizontal
strips, tileable in U) with baseColor, normal (OpenGL), roughness, metallic, height and AO. A template for band and tile
helpers, type-safe parameter setting, rebuild-safe package handling, and a readable graph: nodes grouped into sections
as built, laid out by data flow inside each, one titled frame per section (its description carries the notes), portals
for long links between sections, an overridable size (2048 by default). Re-running it closes the previous build (the
package at `OUT_SBS`) and builds a fresh graph, so later edits are lost: change the script instead. It refuses while
that build has unsaved changes (more, for whoever changes it: its docstring).
