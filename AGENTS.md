# AGENTS.md: notes for AI agents driving Substance Designer

You have access to the user's **running** Substance 3D Designer through the
`substance-designer` MCP server. These notes were learned the hard way; read them before writing
`sd` scripts. (Served whole by the `get_guide` tool and the resource `designer://agents-guide`.
The server's own instructions are one short paragraph, because MCP clients cut long ones (see
Working on this project): leave these tools alone unless the user asks for Designer
work; right before the first Designer tool call, call `get_guide()` and confirm to the user.)

## Rules that protect the user's work

- **Never print, log or send the bridge token** (`~/.sd_claude_bridge_kve_token`): it gives code execution
  in Designer.
- **Never trigger Undo while one of the user's graphs is open in the editor.** Undo is per
  document and hits theirs (it happened once; an immediate Redo restored it). See Undo below.
- **Ask before `quit_designer`** (it's the user's app); never pass `discard_unsaved=True` unless
  the user said to drop those changes (or every package it lists is the self-test's own). Exception: while working on this project itself (see Working
  on this project), restart Designer whenever the work needs it and the tools can, without asking.
- **`snapshot_graph` before risky or large edits** to a user's graph, then `diff_graph` and
  report the diff. Prefer this over Undo.
- **`set_link_display` saves and reloads the package** (undo history reset): tell the user.
- Commit or push only when the user asks; the repository is public. **There is no CI and none
  is planned**: don't add GitHub Actions or other CI.

## Which tool for what

Parameters are in each tool's description; this is when to reach for which.

- **Start:** `designer_status`; `launch_designer` if Designer isn't running; `quit_designer`
  (see the rules).
- **Find and understand nodes:** `search_nodes` (the atomic nodes and Designer's **whole**
  library; returns the exact `definition`), then `describe_node` for connector ids, parameter
  types, **enum values**, library slider ranges and descriptions. Never guess ids or enum
  numbers; pick values inside the slider range.
- **Inspect a graph:** `describe_graph`, `list_graph_inputs`. Graphs are found by identifier;
  several open graphs with the same identifier (every new graph is "New_Graph") are refused as
  ambiguous unless one of them is open in the editor.
- **Safety net:** `snapshot_graph`, `list_snapshots`, `diff_graph` (see the rules).
- **Look:** `preview_node` (any node, even ones not feeding an output), `screenshot_designer`
  (what the user sees), `open_graph` (open the graph first, so the user and screenshots see
  it; `frame=` or `node_ids=` zooms the view to one section). Screenshots cost about
  width × height / 750 tokens: keep `max_size` small, `crop` to the part you need, and zoom
  with `open_graph` rather than taking a big shot of the whole graph.
- **Measure:** `node_stats` (exact numbers; prefer them over eyeballing), `check_tiling`
  (trim sheets only need horizontal), `compare_to_reference` for tones against a reference
  image (add it to the graph with an `apply_edits` `bitmap` op if you want it there). Compare **like with like**: a
  `reference_region` of plain, lit material against the matching `region` of the node. A whole
  product shot is dominated by its background, and lit renders or photos include shading, so
  their contrast is higher than a baseColor's should be (on the dwarf house: whole image EMD
  0.33; a lit stone wall vs the stone strip 0.04; a wall in shadow 0.085 darker). Treat the
  suggested `x*gain + bias` as a starting point for levels, not a target.
- **Tune a value:** `sweep_param` instead of edit-rebuild-look loops; `view_node` watches the
  final output while sweeping an early node.
- **Edit:** `apply_edits` for every node edit, one change or many: ops `add`, `bitmap`
  (reference images, masks, painted maps), `set`, `connect`, `disconnect`, `move`, `delete`,
  `expose` (a parameter as a graph input). One call is one undo step; refs name nodes added
  earlier in the batch. Which mistakes refuse the whole batch and which stop it partway: the
  tool's description. Also `create_graph`; `remove_graph_input`; size with `set_graph_size`.
- **Make graphs readable** (every graph you build or restructure): `arrange_graph` (positions
  only), then `add_frame` per logical section and `add_comment` for non-obvious choices.
  - **Use portals when the wires get too cluttered.** Check with `screenshot_designer('graph')`
    after `open_graph`. Signs: one output fanning out to many nodes, wires crossing sections or
    the whole graph, a bundle you can't follow. Then `set_link_display(mode='portal')`,
    typically `fanout_at_least=4` plus `longer_than=1000`, screenshot again, and keep short
    local wires visible so each section still reads. On the trim sheet this hid 85 of 253 wires
    (58 from one shared gradient) with identical output.
- **Bigger logic:** `run_designer_script` (script on disk, preferred for anything long) or
  `execute_designer_code`; `cancel_designer_job` aborts.
- **Output:** `save_package`; `export_outputs` (straight from Designer, live unsaved state; same
  as the cooked render to within a few 1/65535 steps at a few pixels: the self-test allows 8
  and prints what it measured; why renders differ run to run is ROADMAP item 17); `sbsar_info` +
  `render_sbs` (exposed params, size, formats); `preview_maps` to look at rendered files.

**Loop:** search/describe → build (script or `apply_edits`) → `describe_graph` + `preview_node`
on intermediate nodes → `sweep_param` to pick values → `node_stats` / `check_tiling` → render or
export → `preview_maps` → fix → repeat. Look at the result before telling the user it works.

Fallback without MCP: `python client/sd_run.py script.py [--timeout N]`, `-c CODE`, `--status`,
`--cancel` (no undo grouping).

## Undo, timeouts, plugin lifecycle

- Each code run and each edit tool is one Designer undo transaction
  (`SDHistoryUtils.UndoGroup`), so Ctrl+Z reverts a whole run (the self-test checks one Undo and
  one Redo for an `apply_edits` add op and for a code run).
- Undo history is **per document** (Edit > Undo reverts the last step of the graph in focus).
  If you must trigger it yourself: the actions live in a `QMenu` (find them via
  `QApplication.instance().allWidgets()`, not `mainWindow.findChildren`) and apply
  **asynchronously**, so schedule them with `QTimer.singleShot(0, action.trigger)` (outside your
  own undo group) and call `QApplication.processEvents()` before reading results.
- Timeouts and cancel use a trace hook in the plugin: the abort happens the next time Python
  runs, so one long C++ call (a huge `graph.compute()`) completes first. A script that catches
  `BaseException` swallows the abort, so don't do that. A job still queued after 15 minutes is
  dropped, never run late.
- **Never hot-reload the sd_claude_bridge_kve plugin** (`importlib.reload` inside Designer): the running
  server keeps references to the old module and the bridge breaks until Designer restarts.

## Environment facts

- No `pysbs` (the Automation Toolkit is enterprise-licensed). Everything goes through the
  in-app `sd` API via the bridge, plus `sbscooker`/`sbsrender`.
- Code runs on Designer's main thread, so the UI freezes while a script runs. Keep scripts finite.
- Library graphs are `.sbs` files in `app.getPath(SDApplicationPath.DefaultResourcesDir)/packages`.
  In scripts: `pkgMgr.loadUserPackage(path)` (check `getPackages()` first to reuse an open one),
  `pkg.findResourceFromUrl('<graph id>')`, `graph.newInstanceNode(resource)`. Loaded library
  packages count as user packages; the tools skip them when looking up the user's graphs.
- Python tracebacks from plugins land in the Designer log (`read_designer_log`; "since the last
  start" means after the "Python SDK Version" line Designer logs once per start). Read it when
  the bridge misbehaves or a plugin change doesn't seem to load.
- Harmless log noise: creating an exposed input logs "No output node defined" and "Some Get
  nodes don't have a variable name" until the function node is named. The exposure works.

## sd API gotchas

- **`sd.api.apiexception.APIException` derives from `BaseException`, not `Exception`.**
  `except Exception` will NOT catch it. Use `except (Exception, APIException)`.
- Atomic nodes: `graph.newNode('sbs::compositing::<name>')`, output connector
  `unique_filter_output`. Common inputs: `input1` (levels, blur, normal, warp, directionalwarp,
  transformation…), blend `source` / `destination` / `opacity`, warp `inputgradient`,
  directionalwarp `inputintensity`, output node `inputNodeOutput`.
- Valid atomic ids: `graph.getNodeDefinitions()` (29 in Designer 16; a function graph lists
  `sbs::function::*` instead). Check an id is in that set **before** `graph.newNode(id)`; an
  unknown id reportedly hangs Designer 15 (16 raises).
- Instance (library) nodes: connector ids equal the library graph's identifiers
  (bevel: in `input`, outs `height`/`normal`; tile_generator: out `TileGenerator`).
- Property types matter (`node.getPropertyFromId(id, SDPropertyCategory.Input).getType()`):
  levels `levelin*/levelout*` are **float4**; uniform `outputcolor` is **ColorRGBA**;
  `blendingmode`, `$format`, `$tiling` are **enums** (set via an enumerator's
  `getDefaultValue()` or `SDValueEnum.sFromValueId(type, id)`). `apply_edits`' `set` op converts
  for you and validates before changing anything.
- `$format` enum ids: `8_bits_per_channel`, `16_bits_per_channel`, `hdr_low_precision`,
  `hdr_high_precision` (type `sbs::compositing::format`).
- Blend modes: copy 0, add 1, subtract 2 (enum id spelled `substract`), multiply 3, addsub 4,
  max 5, min 6, switch 7, divide 8, overlay 9, screen 10, softlight 11. **Don't trust
  third-party tables**: one public SD MCP lists 4 = Max / 5 = Min / 6 = Difference, which is
  wrong (there is no Difference). Read enums with `describe_node`.
- Bitmaps: `SDResourceBitmap.sNewFromFile(pkg, path, EmbedMethod.X)` + `graph.newInstanceNode(res)`
  gives an atomic `bitmap` node (out `unique_filter_output`, param `bitmapresourcepath` =
  `pkg:///<resource id>`). The `EmbedMethod` docstrings in `sdresource.py` are shifted by one:
  `Linked` references the original file, `CopiedAndLinked` copies it into `<package>.resources/`
  (prefixed `XXXXXX-`; before the package's first save, into
  `<OS temp>/Adobe/Adobe Substance 3D Designer/`, moved on saving; copies there stay after an
  unsaved package closes, and a later copy of a taken name gets `1-`, `2-`... in front), and
  `BinaryEmbedded` raises `NotSupported`. The node's `$outputsize` is the image's own size (log2).
- Output nodes: annotation `usages` = `SDValueArray` of
  `SDValueUsage.sNew(SDUsage.sNew('baseColor', 'RGBA', 'sRGB'))`; annotations `identifier` /
  `label` via `SDValueString`. The identifier becomes the exported/rendered file name.
- **Connections are reported from the queried node's side:** for `c` in
  `node.getPropertyConnections(prop)`, `getOutputPropertyNode()` / `getOutputProperty()` is
  `node`/`prop` itself and `getInputPropertyNode()` is the **other** node, whatever direction
  the data flows.
- `graph.compute()` computes the nodes that feed an **output node** (about 1 s for a 190-node
  2048² graph); `node.getPropertyValue(outputProp).get()` is then an `SDTexture`. A node feeding no
  output got no texture in a fresh graph, but in the self-test's busier graph one did, so rely on
  neither: attach a temporary output node, as `preview_node` and `node_stats` do.
- Exposing a parameter = graph input via `graph.newProperty(id, type, SDPropertyCategory.Input)`
  (annotations `label`, `min`, `max`, `step`, `group`…) plus a function graph on the node
  parameter (`node.newPropertyGraph(prop, 'SDSBSFunctionGraph')`) whose output node is
  `sbs::function::get_<type>` with `__constant__` = the input id (`get_float1..4`,
  `get_integer1..4`, `get_bool`, `get_string`). Use the parameter's own type; enums → int.
  Adding a function graph to a parameter resets its stored value to the default; setting the
  value deletes an empty function graph (measured with a `set` op; not checked for a graph with
  nodes). An empty function graph drives nothing: the output follows the stored value (the tools
  treat such a parameter as not driven).
- Graph size is log2 (`$outputsize` 11 = 2048), set with
  `graph.setInputPropertyValueFromId('$outputsize', SDValueInt2.sNew(int2(11, 11)))`.
  Generators inherit the graph size; filters inherit from their input. A node's `$format` /
  `$outputsize` only take effect with inheritance set to Absolute (`apply_edits`' `set` op
  and `sweep_param` do that). So does the graph's own `$format` (a new graph's follows its parent:
  setting 16 bits left a generator at RGBA8 until made Absolute); the `set` op does that too.
  A `$randomseed` (the graph's or a node's) is the exception: inherited, its value is added to its
  parent's seed (a render's, or the graph's), and only an inherited graph seed stays a control of
  the cooked .sbsar; made Absolute, a seed stops following its parent. So the `set` op leaves a
  seed's inheritance as it is; to fix one on purpose, change it in code. (Compare computed pixels
  with a tolerance: two computes of one setting differed by 2/65535, and raw buffers carry row
  padding.)
  **Changing a parameter's inheritance doesn't keep its value** (measured on a node's `$outputsize`
  and the graph's `$randomseed`, both directions; back to inherited gave the default): set the
  inheritance first, then the value (`sweep_param` restores in that order).
  `setDefaultParentSize()` takes **pixels**, not log2.
- **Inheritance numbers differ between the API and the file.** API `SDPropertyInheritanceMethod`:
  RelativeToInput 0, RelativeToParent 1, Absolute 2. A .sbs `<relativeTo>`: 0 absolute,
  1 relative to parent, 2 relative to input, and the default isn't stored (parent for a graph,
  input for a node).
- Node positions are node **centres**; a node is 96×96 in graph units. Frames:
  `SDGraphObjectFrame.sNew(graph)` with `setTitle`, `setPosition` (top-left), `setSize`,
  `setColor`, `setDescription`; comments: `SDGraphObjectComment.sNew(graph)` or
  `sNewAsChild(node)` with `setDescription`; list them with `graph.getGraphObjects()`.
- Slider ranges exist only for **library** node parameters, as annotations (`min`, `max`,
  `step`, `clamp`) on the referenced graph's input property. Atomic nodes have none.
- `pkgMgr.saveCopyOfPackageAs(pkg, path)` writes a copy without changing the package's path or
  saved state (what snapshots use); `savePackageAs` changes both. `SDPackage.isModified()`
  tells whether a package has unsaved changes. To close earlier builds of a generated graph,
  unload every user package containing its identifier.
- **Portals** are a per-connection display flag, `<displayType v="1"/>` inside a node's own
  `<connections>/<connection>` in the .sbs (function graphs on parameters have their own
  connections; leave those alone). Dot nodes (`passthrough`) are just optional reroute points.
  The API can't read or set the flag, so `set_link_display` uses the **file-level edit
  pattern**: snapshot the live graph and copy the saved file, decide on the copy (no change → no
  save), save, edit the .sbs XML, then unload, load and reopen as **three separate bridge calls
  with short pauses**. Back to back, Designer once crashed: a null call in PySide from its own
  `node_align_tools` plugin, which adds a toolbar to each new graph view, while the old views
  were still being torn down (crash dump in Designer's `Sentry-Crashpad/completed`). Returning
  to Designer's event loop between the steps lets the teardown finish; 300 stress reloads since
  have been clean. If it recurs, read the newest dump's crashing module first. A package whose
graphs were **never opened in a view** has nothing to tear down, so a script that builds one can
save, edit and reload it in a single call (the example script does, for its portals). Use the same pattern for
  other things the API can't do, with a `diff_graph` plus `node_stats` check afterwards.

## Designer UI (Qt)

- The graph editor's node view is a `QGraphicsView` inside the `areaB_` dock (the dock adds a
  title bar and two toolbar rows above it); its **scene coordinates are graph units**.
  **Don't set its transform** (`fitInView`, `scale`): Designer keeps its own zoom level beside
  it, and the user's next mouse-wheel step jumps from that stale level (seen once: one notch up
  went from a 22 % fit to very close). Zoom with synthetic `QWheelEvent`s on the viewport
  instead, 1.2x per notch in Designer 16, and pan with `centerOn` (panning is safe);
  `open_graph(frame=...)` does this, and the self-test checks that a wheel step after a fit
  is exactly 1.2x.
- Current graph: `getQtForPythonUIMgr().getCurrentGraph()`; editor control via
  **`app.getUIMgr()`**: `openResourceInEditor(graph)`, `focusGraphNode(graphViewID, node)` (ids
  via `getGraphViewIDCount/At`, `getGraphFromGraphViewID`), `getGraphNodeBBox`,
  `setExplorerSelection`. The graph dock's "Fit in view (selection)" (F) fits the selection, or
  everything when nothing is selected; `open_graph` fits every node, frame and free comment by wheel zoom instead.
- `getQtForPythonUIMgr().getMainWindow()` is a **hidden** QMainWindow; closing it does nothing.
  The window the user sees is a top-level `QStackedWidget` ("Adobe Substance 3D Designer");
  closing the visible top-level widgets quits Designer normally. If a window refuses to close,
  Qt 6's `QApplication.quit()` gives up too. `QApplication.exit(0)` stops the event loops, but
  Designer's teardown then races its own background threads: twice Adobe's licence check
  (`Alg::BinaryHardeningService`, on a `QtConcurrent` thread) crashed reading a destroyed
  profile, and the process hung for over 30 s. So `quit_designer`'s fallback after 5 s is
  `os._exit(0)`: no teardown, no race (Designer doesn't save its window layout then). A window that
  refuses to close is forced at 5 s. Once every window has closed, or while a close handler is still
  running, the shutdown is left to finish; about 35 s after the quit, a window still visible (a stuck
  handler), or a Designer still running with every window closed, is forced then. Designer quits once its main window has closed, even with another
  top-level window showing (measured: a window shown during the close; gone in 2 s). (`aboutToQuit` can't serve as the
  signal: its slots run in connection order, after any connected earlier.) A modal
  dialog doesn't stop a programmatic close. Crash dumps: Designer's `Sentry-Crashpad/completed`.
- That stack has two pages: the main window and the **Home screen** (current after a fresh
  start). While Home shows, no panel reports itself visible (`launch_designer` prints the count before and
  after closing it), so `launch_designer` and `open_graph` close it first.
  Leave it with Home's own "Close home screen" button (`close_btn`); keep the stack and the page
  referenced while clicking, or PySide reports the button as already deleted.
- PySide wrappers for Designer's Qt objects go stale ("Internal C++ object already deleted")
  unless you keep Python references to their parents; menus fill lazily (emit
  `menu.aboutToShow` first).
- Screenshots: `QWidget.grab()` on Designer's widgets only. **Never use `QScreen.grabWindow`**,
  not even with Designer's own window id: on macOS both copy the screen area, so they capture
  whatever covers Designer (the user's other apps). Widget capture can't see the GPU-drawn 3D
  view: a grab of its viewport is leftover content (black or grey blocks, varying between calls),
  so `3d` uses the 3D view's own **Camera > Copy Render to Clipboard** and restores the
  user's clipboard in a `finally`. Never use "Save Render...": its modal file dialog blocks the
  bridge.
- Dock titles change with content. Find panels by object name: `areaA_` explorer, `areaB_`
  graph, `areaC_` parameters, `areaD_` 3D view, `areaE_` 2D view, `areaF_` console (hidden by
  default; Windows > Console), `areaG_` library.

## Library node facts (Designer 16)

- `gradient_linear_1` with `rotation` 0: **1.0 at the top row, 0.0 at the bottom**, constant
  across x. With levels this makes a vertical coordinate, handy for per-row height profiles
  (bands, chamfers) in trim sheets.
- `tile_generator`: `Nb_X`, `Nb_Y`, `Pattern_Type` (2 = square, 1 = image input, 9 = brick
  default), `Scale`, `Offset` (row offset), `Offset_Random`, `Offset_Random_Seed`,
  `Free_Rotation` (degrees), `Luminance_Variation-Contrast` (float2: random luminance per tile,
  contrast). The same seed/layout twice gives a matching per-tile random mask.
- `bevel`: `distance` (~0.02–0.08 for small chamfers), `smoothing`; outs `height`, `normal`.
- `hbao`: in `input`, out `output`. `curvature_smooth`: in `input` (normal), out `height`.
- `noise_anisotropic_noise`: default streaks run horizontally (`X_Amount`, `Y_Amount`).
- Atomic `warp` intensity is strong: ~0.05–0.1 gives a gentle wave; 1.5 destroys the pattern.
- Atomic `normal`: `inversedy=True` gives **OpenGL** normals (Blender): where height rises
  towards the top of the image, green is below 0.5 (a raised band's top chamfer is above 0.5).

## Rendering and verifying

- **sbsrender ignores inputs the .sbsar doesn't expose**, silently (`render_sbs` warns).
- **Graph size:** a fixed (Absolute) `$outputsize` isn't exposed, so size overrides are ignored.
  An overridable graph (`set_graph_size(..., overridable=True)`: relative to parent, offset 0,
  `defaultParentSize` = 2^n) exposes `$outputsize`; `--set-value $outputsize@n,n` sets the
  **parent** size, and a non-zero relative offset is applied on top. Without an override
  sbsrender assumes a 256 px parent, so `render_sbs` passes the graph's `defaultParentSize`
  from the .sbs. Check the printed file sizes.
- **A cooked .sbsar forgets the default parent size:** sbscooker writes `$outputsize` default
  `8,8` (256 px) whatever the graph's `defaultParentSize` (no cooker option changes it), so a
  .sbsar renders at 256 px here and in other Substance apps unless a size is set. `render_sbs`
  on a .sbsar says so (it reads the archive's .xml with the system `tar`).
- Pixel precision: grayscale 16-bit PNGs load in PIL as `I;16` (normalise by 65535), but PIL
  loads 16-bit **RGBA** PNGs as 8-bit. For exact values use `node_stats`, which reads the raw
  buffer: little-endian, uint8 / uint16 / float16 / float32 per `getPixelFormat()`, row stride
  `getRowPitch()`. Outputs seen so far are `RGBA*` or `LUM*`: even an imported RGB JPG or
  grey+alpha PNG computes as `RGBA8`. The other `SBSPixelFormat` layouts (`RGB*`, `BGR8`,
  `BGRA8`, `LUMALPHA*`) are decoded too, untested against Designer.
- Verify orientation and conventions numerically (sample known pixels), not just visually.

## Example

`examples/build_dwarf_trimsheet.py`: a complete config-driven generator for a 2048² stone +
wood trim sheet (11 horizontal strips, tileable in U), outputting baseColor, normal (OpenGL),
roughness, metallic, height and AO. A good template for band and tile helpers, type-safe
parameter setting, and rebuild-safe package handling, and for a generator that leaves a readable
graph: nodes grouped into sections as they are built, laid out by data flow inside each section,
one titled frame per section (its description carries the notes), portals for long links
between sections, and an overridable size (2048 by default). Re-running it closes the previous
build (the package at `OUT_SBS`) and builds a fresh graph, so edits made afterwards are lost;
change the script instead. It refuses while that build has unsaved changes, and leaves other
packages with a graph of the same name open (a copy saved elsewhere, an unsaved one). Re-running
with the previous build open in an editor tab (an unload and a reload in one call) caused no
crash in five tries, and the self-test's re-runs do it too. The self-test
builds a copy with its `OUT_SBS = ...` and `GRAPH_ID = ...` lines rewritten, so keep each of
those assignments on one line.

## Working on this project

How the plugin, server, helpers and command-line tools fit together: README.md, **How it
works**.

**Load the `mcp-builder` skill** (`.claude/skills/mcp-builder/`: Anthropic's, from `anthropics/skills` at
`ca45fc4`, trimmed to its Python parts) before designing or changing tools: adding, merging or removing
one, its parameters, description, errors or results. Use it for tool design, descriptions, error
messages and evaluations; where it differs from this file (tests and docs follow the rules below), this
file wins. Defaults of the skill this project doesn't follow: comprehensive API coverage and
service-prefixed names (this project keeps few tools with unprefixed names: node edits are `apply_edits`
ops, not tools of their own; a new capability is a parameter or op of an existing tool where one fits,
a new tool only for a workflow none fits, ROADMAP.md "Fewer tools"); JSON next to Markdown results (the
results are compact text for agents); Pydantic input models (inputs are typed parameters). Its code is
for mcp 1.x; this server runs mcp 2.x (the note at the top of its `SKILL.md`).

The server (`server_tools/core.py`) loads this file from the folder above `mcp_server/`, so keep it there. Its
instructions (`INSTRUCTIONS` in `server_tools/core.py`) must stay under 4,096 characters, and every text tool result starts with a reminder until `get_guide()`
has been called in the session (unit tests check both).

**Every new feature or fix comes with a test, in the same change.** A tool, a parameter or a
documented behaviour gets a check in the live self-test (`tests/test_all_tools/`, against the
real Designer); pure-Python logic gets a unit test in `tests/unit`. A claim in these docs
without a test is a guess: test it or remove it.

**Fix issues test first (TDD).** Reproduce the issue with a test and watch it fail; then fix
the code until the test passes. Before a fix that depends on Designer's behaviour, measure every
case the code distinguishes, and fix the pattern everywhere it occurs, not just the reported
instance (the `address-review` skill, step 3: skipping these made findings recur round after round). If the test passes before any fix, the issue isn't real (or
the test doesn't reproduce it): say so rather than "fixing" it. For anything that depends on
Designer, reproduce it in the live self-test too, since a unit test may take a path Designer
never does. Two review findings were disproved this way: an abort raised again during cleanup
(Python unsets a trace function that raises) and a job starting inside the running one (Qt
doesn't re-fire a timer whose slot is running; only a direct call in a unit test did).

**Review your own work before calling it done.** When you implement something, or write or run
its tests, step back once it seems finished and look at it as a reviewer would, not as its author:
does it cover the neighbouring cases (a node as well as the graph, the other parameter, the other
code path), would each test fail without the change it guards (not pass on state an earlier check
left, a value already there, or a comparison any rule satisfies), does every test clean up on
failure too, did the change weaken an older test, and does any comment, docstring or doc now say
more than the code and tests show? Fix what you find, then look again the same way, and repeat
until a fresh look finds nothing a reviewer could report. Only then say it is done.

**Reviews go in REVIEW.md** (in the repo root, committed with the changes it records). Two skills:
`project-code-review` (`.claude/skills/project-code-review/`) for reviewing, whose `TEMPLATE.md` is the
format, and `address-review` (`.claude/skills/address-review/`) for fixing or answering findings
test first and checking them off.
The rules:
- Five sections by severity, from high to low: High, Medium-high, Medium, Low-medium, Low.
- Each finding is one entry starting with a checkbox: unchecked while open, checked once it is
  fixed or answered (not a bug, not reproduced, won't fix), with a resolution line giving the
  commit and the evidence.
- A new review **appends** its findings to the sections they belong in, plus an entry in the
  review log; it never replaces or rewrites what is already there.
The unit tests enforce part of this: they fail when a tool or a tool parameter is never exercised by
the self-test, when an `apply_edits` op or an op's field is never passed in one (run or not), or when a
tool is missing from README's Tools table.

**Running the tests** (both must pass before a change is done):
- `mcp_server/venv/bin/python -m pytest`: unit tests, no Designer needed, a few seconds
  (`pip install -r mcp_server/requirements-dev.txt` once). They include `test_types.py`, which runs
  mypy strict (`mypy.ini`) over every Python file: everything you write is fully annotated. The
  helpers, the plugin and the example are checked against Designer's own `sd` package and PySide6
  stubs (found in the Designer install). They run on Designer's Python 3.13, which evaluates
  annotations when a `def` runs, so every name in an annotation there must exist at runtime: import
  real types (`from sd.api.sdnode import SDNode`), never only under `if TYPE_CHECKING:`, and no
  `from __future__ import annotations` (the helpers are joined into one script, where it can't come first).
  The standalone scripts (`install.py`, `uninstall.py`, `client/sd_run.py`) are the opposite: they run on
  the system Python, which can be 3.9, so they do start with `from __future__ import annotations` and
  evaluate no `X | None` at module level (`tests/unit/test_old_python.py` runs them on an older Python
  when one is installed).
  `sd`'s modules star-import each other in cycles, so in the whole-repo run some sd return types come
  out `Any` (`no-any-return`): annotate the local (`node: SDNode = g.newNode(...)`).
  `test_lint.py` runs Ruff (`ruff.toml`): `ruff check` and `ruff format --check`. After editing, run
  `mcp_server/venv/bin/ruff check --fix .` and `mcp_server/venv/bin/ruff format .`. The formatter can
  move a trailing `# type: ignore` or `# noqa` off the line it was for when it rewraps a statement;
  mypy then reports it, so put it back on the right line. Tests that read source text match
  whitespace-tolerantly (`c\(\s*'tool'`): formatting may split a call over lines.
- `mcp_server/venv/bin/python tests/test_all_tools`: every tool over MCP against the real
  Designer, about two minutes. It starts Designer if it isn't running and closes it again; a
  Designer that was already running stays open. Its "designer facts" checks re-measure the
  Designer behaviour this file states, so add one with each new fact.
  The folder holds one module per category (`bridge.py`, `params.py`, `render.py`...), shared
  helpers and snippets in `common.py`, and the index `__main__.py`, which runs the categories in
  the order of its `CATEGORIES` list. They share one graph and run only in that order; what an
  earlier category made (the graph `G`, node ids, the saved `.sbs`) reaches later ones through
  `ctx`. Add a check to the category it belongs to; a new category is a module with an
  `async def run(ctx)` added to `CATEGORIES`.

**Keeping the docs current.** README.md is for people, AGENTS.md is for agents. With every
change (a tool, a fix, a workaround, a fact learned about Designer), add a short note where it
belongs, in the same change. Keep each fact in **one** place and link to it instead of copying
it; fix or delete notes that turn out to be wrong rather than adding a contradicting one.

| Kind of knowledge | Where it goes |
|---|---|
| How to use the tools well, workflow, sd API / Designer pitfalls, verified facts | **AGENTS.md**, in the matching section |
| A tool's parameters and behaviour | The tool's **docstring in its module of `mcp_server/server_tools/`**, the single source; don't repeat parameters here |
| Install, configuration, security, troubleshooting, anything a **person** needs | **README.md** |
| Architecture: what the plugin, server, helpers and CLI tools each do | **README.md**, "How it works" |
| How to deploy changes, diagnostics an **agent** needs | **AGENTS.md**, this section |
| New or changed tool | Its entry and the tool count in README.md's Tools table, and checks in `tests/test_all_tools/` |
| Work still to do, ideas, follow-ups | **ROADMAP.md** (check an item when done; checked items can be deleted later, git keeps the record) |

Open work lives in [ROADMAP.md](ROADMAP.md): check it before proposing improvements and add
new ideas there.

- **Fresh clone, or a deleted `mcp_server/venv`:** run `python3 install.py` (Windows:
  `py -3 install.py`) before anything else; without the venv the server can't start, and the
  `.mcp.json` command says so in `/mcp`. Then the user reconnects `/mcp`. `designer_status` shows
  which Python and library versions the server runs on.
- **The helpers** (`mcp_server/designer_helpers/`) are parts joined into one script (README.md, How
  it works). A part imports what it uses from other parts (`from .core import find_graph`), for PyCharm
  and readers; `part_source()` drops those lines, since the joined script already has the names.
  `tests/unit/test_designer_helpers.py` fails on a missing, extra or misplaced import, on a name no part
  defines, and on a part file not in `PARTS`. Code that needs the helpers' text (the self-test's
  snippets) takes it from `designer_helpers.source()`, never from one file.
- **PyCharm** (the repo's `.idea` marks `client`, `mcp_server`, `tests` and `tests/unit` as source roots;
  the interpreter is `mcp_server/venv`): tests patch a module loaded from its file with
  `monkeypatch.setitem(vars(module), 'NAME', value)`, not `setattr`, whose name PyCharm checks against the
  fixture and reports as missing; standard modules are patched directly (`time`, not `server.time`).
- **The server** (`mcp_server/server.py`) only starts it and re-exports the names of
  `mcp_server/server_tools/`, one module per area (`core` holds the bridge and the `_tool`
  decorator; a new module goes into `MODULES` in its `__init__.py`). Unit tests replace a name with
  `patch_server` (`tests/unit/conftest.py`), which patches every module that binds it: patching
  `server` alone no longer reaches the tools.
- **How changes reach Designer:** `server.py`, `server_tools/` and `designer_helpers/` changes take effect when
  the MCP server restarts (helpers are re-sent with every call; the user reconnects in `/mcp`,
  or test with a fresh MCP client such as the self-test). **Plugin** changes must be copied into
  Designer's plugin folder (re-run `install.py`; paths in README.md, Install) and need a
  **Designer restart** (`quit_designer`, then `launch_designer`). **When working on this project,
  restart Designer whenever the work needs it (a plugin change, a crashed Designer that
  `launch_designer` can start again, a run of the self-test from a closed Designer) without asking
  first;** just say that you did. That covers what `quit_designer` and `launch_designer` can do: a
  bridge that accepts connections but never answers still needs the user (When tools fail, below).
  The rest still holds: `quit_designer` refuses unsaved changes, and `discard_unsaved=True` drops
  every unsaved package, so pass it only when the user said so or every package it lists is the
  self-test's own (`mcp_selftest...`).
- **The plugin's name** (`sd_claude_bridge_kve`, also its folder names and the token file
  `~/.sd_claude_bridge_kve_token`) is defined once, in `project_constants.py`; the plugin itself
  takes it from its own folder. To rename: change `PLUGIN` there, rename both `plugin/<name>`
  folders, update README.md/AGENTS.md, and add the old name to `install.py`'s clean-up of old
  copies. `tests/unit/test_constants.py` fails on anything missed.
- **Registration is per folder, never global, for now** (README.md, "Where the tools are available";
  ROADMAP item 5 will make global registration the installer's choice):
  this repo's committed `.mcp.json`, or `claude mcp add --scope local` in another folder. The
  installer never registers; it writes a user skill (`skill_text` in `install.py`) that tells
  sessions elsewhere how to register, and `uninstall.py` removes the skill, the plugin, the token
  and every folder's local registration (only entries that run this repo's `server.py`). `.mcp.json` must not contain `${`: Claude Code expands those itself
  (it once rewrote a shell default away), so its `sh -c` command uses plain `$VARS`
  (`tests/unit/test_mcp_json.py`).
- **The bridge protocol** (plugin docstring): the plugin sends a nonce, the client answers with
  HMAC(token, nonce), so the token never crosses the socket. `server_tools/core.py`, `client/sd_run.py`
  and the self-test's `raw_request` all speak it; change them together with the plugin.
- Environment variables `SD_DESIGNER_BIN_DIR`, `SD_DESIGNER_APP`, `SD_DESIGNER_LOG`,
  `SD_SNAPSHOT_DIR`, `SD_BRIDGE_PORT`: README.md, Configuration. A port change must reach the
  plugin (Designer's environment) and the server alike.
- **When tools fail:** match the symptom in README.md, Troubleshooting. First try
  `launch_designer`, then `read_designer_log`. If the bridge accepts connections but never
  answers, or a tool is missing in Claude Code, only the user can fix it (restart Designer /
  reconnect `/mcp`), so tell them.
