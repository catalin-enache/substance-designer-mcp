# AGENTS.md: notes for AI agents driving Substance Designer

You have access to the user's **running** Substance 3D Designer through the
`substance-designer` MCP server. These notes were learned the hard way; read them before writing
`sd` scripts. (Also served as the MCP server's instructions and as resource
`designer://agents-guide`; clients may truncate long instructions, so the rules come first.)

## Rules that protect the user's work

- **Never print, log or send the bridge token** (`~/.sd_bridge_token`): it gives code execution
  in Designer.
- **Never trigger Undo while one of the user's graphs is open in the editor.** Undo is per
  document and hits theirs (it happened once; an immediate Redo restored it). See Undo below.
- **Ask before `quit_designer`** (it's the user's app); never pass `discard_unsaved=True` unless
  the user said to drop those changes.
- **`snapshot_graph` before risky or large edits** to a user's graph, then `diff_graph` and
  report the diff. Prefer this over Undo.
- **`set_link_display` saves and reloads the package** (undo history reset): tell the user.
- Commit or push only when the user asks; the repository is public. **There is no CI and none
  is planned**: don't add GitHub Actions or other CI.

## Which tool for what

Parameters are in each tool's description; this is when to reach for which.

- **Start:** `designer_status`; `launch_designer` if Designer isn't running; `quit_designer`
  (see the rules).
- **Find and understand nodes:** `search_nodes` (the 29 atomic nodes and Designer's **whole**
  library; returns the exact `definition`), then `describe_node` for connector ids, parameter
  types, **enum values**, library slider ranges and descriptions. Never guess ids or enum
  numbers; pick values inside the slider range.
- **Inspect a graph:** `describe_graph`, `list_graph_inputs`. Graphs are found by identifier;
  several open graphs with the same identifier (every new graph is "New_Graph") are refused as
  ambiguous unless one of them is open in the editor.
- **Safety net:** `snapshot_graph`, `list_snapshots`, `diff_graph` (see the rules).
- **Look:** `preview_node` (any node, even ones not feeding an output), `screenshot_designer`
  (what the user sees), `open_graph` (open and centre on a node first, so the user and
  screenshots see it).
- **Measure:** `node_stats` (exact numbers; prefer them over eyeballing), `check_tiling`
  (trim sheets only need horizontal), `compare_to_reference` for tones against a reference
  image (`import_bitmap` it too if you want it in the graph). Compare **like with like**: a
  `reference_region` of plain, lit material against the matching `region` of the node. A whole
  product shot is dominated by its background, and lit renders or photos include shading, so
  their contrast is higher than a baseColor's should be (on the dwarf house: whole image EMD
  0.33; a lit stone wall vs the stone strip 0.04; a wall in shadow 0.085 darker). Treat the
  suggested `x*gain + bias` as a starting point for levels, not a target.
- **Tune a value:** `sweep_param` instead of edit-rebuild-look loops; `view_node` watches the
  final output while sweeping an early node.
- **Edit:** one-off `add_node` / `import_bitmap` (reference images, masks, painted maps) /
  `set_params` / `connect` / `disconnect` / `move_nodes` / `delete_nodes`; several changes at
  once with `apply_edits` (one call, one undo step, refs for new nodes); `create_graph`;
  controls with `expose_param` / `remove_graph_input`; size with `set_graph_size`.
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
  as the cooked render up to 16-bit rounding, a few pixels off by <= 3/65535); `sbsar_info` +
  `render_sbs` (exposed params, size, formats); `preview_maps` to look at rendered files.

**Loop:** search/describe → build (script or `apply_edits`) → `describe_graph` + `preview_node`
on intermediate nodes → `sweep_param` to pick values → `node_stats` / `check_tiling` → render or
export → `preview_maps` → fix → repeat. Look at the result before telling the user it works.

Fallback without MCP: `python client/sd_run.py script.py [--timeout N]`, `-c CODE`, `--status`,
`--cancel` (no undo grouping).

## Undo, timeouts, plugin lifecycle

- Each code run and each edit tool is one Designer undo transaction
  (`SDHistoryUtils.UndoGroup`), so Ctrl+Z reverts a whole run (the self-test checks one Undo and
  one Redo for `add_node` and for a code run).
- Undo history is **per document** (Edit > Undo reverts the last step of the graph in focus).
  If you must trigger it yourself: the actions live in a `QMenu` (find them via
  `QApplication.instance().allWidgets()`, not `mainWindow.findChildren`) and apply
  **asynchronously**, so schedule them with `QTimer.singleShot(0, action.trigger)` (outside your
  own undo group) and call `QApplication.processEvents()` before reading results.
- Timeouts and cancel use a trace hook in the plugin: the abort happens the next time Python
  runs, so one long C++ call (a huge `graph.compute()`) completes first. A script that catches
  `BaseException` swallows the abort, so don't do that. A job still queued after 15 minutes is
  dropped, never run late.
- **Never hot-reload the sd_bridge plugin** (`importlib.reload` inside Designer): the running
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
  `getDefaultValue()` or `SDValueEnum.sFromValueId(type, id)`). `set_params` converts for you
  and validates before changing anything.
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
  (prefixed `XXXXXX-`; in an OS temp folder until the package is first saved, then moved), and
  `BinaryEmbedded` raises `NotSupported`. The node's `$outputsize` is the image's own size (log2).
- Output nodes: annotation `usages` = `SDValueArray` of
  `SDValueUsage.sNew(SDUsage.sNew('baseColor', 'RGBA', 'sRGB'))`; annotations `identifier` /
  `label` via `SDValueString`. The identifier becomes the exported/rendered file name.
- **Connections are reported from the queried node's side:** for `c` in
  `node.getPropertyConnections(prop)`, `getOutputPropertyNode()` / `getOutputProperty()` is
  `node`/`prop` itself and `getInputPropertyNode()` is the **other** node, whatever direction
  the data flows.
- `graph.compute()` only computes nodes that feed an **output node** (about 1 s for a 190-node
  2048² graph); `node.getPropertyValue(outputProp).get()` is then an `SDTexture`.
- Exposing a parameter = graph input via `graph.newProperty(id, type, SDPropertyCategory.Input)`
  (annotations `label`, `min`, `max`, `step`, `group`…) plus a function graph on the node
  parameter (`node.newPropertyGraph(prop, 'SDSBSFunctionGraph')`) whose output node is
  `sbs::function::get_<type>` with `__constant__` = the input id (`get_float1..4`,
  `get_integer1..4`, `get_bool`, `get_string`). Use the parameter's own type; enums → int.
- Graph size is log2 (`$outputsize` 11 = 2048), set with
  `graph.setInputPropertyValueFromId('$outputsize', SDValueInt2.sNew(int2(11, 11)))`.
  Generators inherit the graph size; filters inherit from their input. A node's `$format` /
  `$outputsize` only take effect with inheritance set to Absolute (`set_params` and
  `sweep_param` do that). `setDefaultParentSize()` takes **pixels**, not log2.
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
  save), save, edit the .sbs XML, reload the package, reopen the graph in a separate call
  (reopening in the reload's call can leave the graph panel empty). Use the same pattern for
  other things the API can't do, with a `diff_graph` plus `node_stats` check afterwards.

## Designer UI (Qt)

- Current graph: `getQtForPythonUIMgr().getCurrentGraph()`; editor control via
  **`app.getUIMgr()`**: `openResourceInEditor(graph)`, `focusGraphNode(graphViewID, node)` (ids
  via `getGraphViewIDCount/At`, `getGraphFromGraphViewID`), `getGraphNodeBBox`,
  `setExplorerSelection`. Fit the view: the graph dock's "Fit in view (selection)" (F) fits
  everything when nothing is selected.
- `getQtForPythonUIMgr().getMainWindow()` is a **hidden** QMainWindow; closing it does nothing.
  The window the user sees is a top-level `QStackedWidget` ("Adobe Substance 3D Designer");
  closing the visible top-level widgets quits Designer normally. If a window refuses to close,
  Qt 6's `QApplication.quit()` gives up too; `exit(0)` stops the event loops regardless
  (`quit_designer`'s fallback after 5 s). A modal dialog doesn't stop a programmatic close.
- That stack has two pages: the main window and the **Home screen** (current after a fresh
  start). While Home shows, every dock reports `isVisible()` False and graphs open behind it.
  Leave it with Home's own "Close home screen" button (`close_btn`); keep the stack and the page
  referenced while clicking, or PySide reports the button as already deleted.
- PySide wrappers for Designer's Qt objects go stale ("Internal C++ object already deleted")
  unless you keep Python references to their parents; menus fill lazily (emit
  `menu.aboutToShow` first).
- Screenshots: `QWidget.grab()` on Designer's widgets only. **Never use `QScreen.grabWindow`**,
  not even with Designer's own window id: on macOS both copy the screen area, so they capture
  whatever covers Designer (the user's other apps). The GPU-drawn 3D view is black under widget
  capture, so `3d` uses the 3D view's own **Camera > Copy Render to Clipboard** and restores the
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
  buffer: RGBA or single-channel (`LUM*`), little-endian, uint8 / uint16 / float16 / float32 per
  `getPixelFormat()`, row stride `getRowPitch()`.
- Verify orientation and conventions numerically (sample known pixels), not just visually.

## Example

`examples/build_dwarf_trimsheet.py`: a complete config-driven generator for a 2048² stone +
wood trim sheet (11 horizontal strips, tileable in U), outputting baseColor, normal (OpenGL),
roughness, metallic, height and AO. A good template for band and tile helpers, type-safe
parameter setting, and rebuild-safe package handling. Its size is fixed (call
`set_graph_size(overridable=True)` afterwards for size overrides), and re-running it builds a
fresh graph, so portals, frames and layout changes made afterwards are lost. The self-test
builds a copy with its `OUT_SBS = ...` and `GRAPH_ID = ...` lines rewritten, so keep each of
those assignments on one line.

## Working on this project

How the plugin, server, helpers and command-line tools fit together: README.md, **How it
works**. `server.py` loads this file from the folder above `mcp_server/`, so keep it there.

**Every new feature or fix comes with a test, in the same change.** A tool, a parameter or a
documented behaviour gets a check in the live self-test (`tests/test_all_tools.py`, against the
real Designer); pure-Python logic gets a unit test in `tests/unit`. A bug fix gets a test that
fails without the fix. A claim in these docs without a test is a guess: test it or remove it.
The unit tests enforce part of this: they fail when a tool, a tool parameter or an `apply_edits`
op is never exercised by the self-test, or a tool is missing from README's Tools table.

**Running the tests** (both must pass before a change is done):
- `mcp_server/venv/bin/python -m pytest`: unit tests, no Designer needed, a few seconds.
- `mcp_server/venv/bin/python tests/test_all_tools.py`: every tool over MCP against the real
  Designer, about two minutes. It starts Designer if it isn't running and closes it again; a
  Designer that was already running stays open. Its "designer facts" checks re-measure the
  Designer behaviour this file states, so add one with each new fact.

**Keeping the docs current.** README.md is for people, AGENTS.md is for agents. With every
change (a tool, a fix, a workaround, a fact learned about Designer), add a short note where it
belongs, in the same change. Keep each fact in **one** place and link to it instead of copying
it; fix or delete notes that turn out to be wrong rather than adding a contradicting one.

| Kind of knowledge | Where it goes |
|---|---|
| How to use the tools well, workflow, sd API / Designer pitfalls, verified facts | **AGENTS.md**, in the matching section |
| A tool's parameters and behaviour | The tool's **docstring in `mcp_server/server.py`**, the single source; don't repeat parameters here |
| Install, configuration, security, troubleshooting, anything a **person** needs | **README.md** |
| Architecture: what the plugin, server, helpers and CLI tools each do | **README.md**, "How it works" |
| How to deploy changes, diagnostics an **agent** needs | **AGENTS.md**, this section |
| New or changed tool | Its entry and the tool count in README.md's Tools table, and checks in `tests/test_all_tools.py` |
| Work still to do, ideas, follow-ups | **ROADMAP.md** (delete items when done; git keeps the record) |

Open work lives in [ROADMAP.md](ROADMAP.md): check it before proposing improvements and add
new ideas there.

- **How changes reach Designer:** `server.py` and `designer_helpers.py` changes take effect when
  the MCP server restarts (helpers are re-sent with every call; the user reconnects in `/mcp`,
  or test with a fresh MCP client such as the self-test). **Plugin** changes must be copied into
  Designer's plugin folder (re-run `install.py`; paths in README.md, Install) and need a
  **Designer restart** (with the user's OK: `quit_designer`, then `launch_designer`).
- **The bridge protocol** (plugin docstring): the plugin sends a nonce, the client answers with
  HMAC(token, nonce), so the token never crosses the socket. `server.py`, `client/sd_run.py`
  and the self-test's `raw_request` all speak it; change them together with the plugin.
- Environment variables `SD_DESIGNER_BIN_DIR`, `SD_DESIGNER_APP`, `SD_DESIGNER_LOG`,
  `SD_SNAPSHOT_DIR`, `SD_BRIDGE_PORT`: README.md, Configuration. A port change must reach the
  plugin (Designer's environment) and the server alike.
- **When tools fail:** match the symptom in README.md, Troubleshooting. First try
  `launch_designer`, then `read_designer_log`. If the bridge accepts connections but never
  answers, or a tool is missing in Claude Code, only the user can fix it (restart Designer /
  reconnect `/mcp`), so tell them.
