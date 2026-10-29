# AGENTS.md: notes for AI agents driving Substance Designer

You have access to the user's **running** Substance 3D Designer through the
`substance-designer` MCP server. These notes were learned the hard way. Read them before
writing `sd` scripts. (This file is also served as the MCP server's instructions and as
resource `designer://agents-guide`.)

## Keeping these docs current (do this every time)

README.md is for people, AGENTS.md is for agents. Every time you improve this project (a new tool, a fix, a workaround, or a fact learned
about Designer), add a short hint where it belongs, in the same change:

| Kind of knowledge | Where it goes |
|---|---|
| How to use the tools well, workflow, sd API / Designer pitfalls, verified facts | **AGENTS.md** (this file), in the matching section |
| A tool's parameters and behaviour | The tool's **docstring in `mcp_server/server.py`**, the single source; don't repeat parameters here |
| Install, configuration, security, troubleshooting, anything a **person** needs | **README.md** |
| Architecture: what the plugin, server, helpers and CLI tools each do | **README.md**, "How it works" |
| How to deploy changes, diagnostics an **agent** needs | **AGENTS.md**, "Working on this project" |
| New or changed tool | Its entry and the tool count in README.md's Tools table, and a check in `tests/test_all_tools.py` |
| Work still to do, ideas, follow-ups | **ROADMAP.md** (remove items when done) |

**Open work lives in [ROADMAP.md](ROADMAP.md)**, the road map for perfecting this MCP. Check it before
proposing improvements, add new ideas there, and when you finish an item delete it from ROADMAP.md in
the same change (git history keeps the record).

**Every new feature or fix comes with a test, in the same change.** A tool, a parameter or a
documented behaviour gets a check in the live self-test (`tests/test_all_tools.py`, against the
real Designer); pure-Python logic gets a unit test in `tests/unit`. A bug fix gets a test that
fails without the fix. A claim in these docs without a test is a guess: test it or remove it.
Both suites must pass before the change is done (Working on this project).

Keep each fact in **one** place and link to it from elsewhere instead of copying it. Fix or
delete hints that turn out to be wrong rather than adding a contradicting one. Run the self-test
before calling a change done.

## Which tool for what

Parameters are in each tool's description; this is when to reach for which.

- **Start:** `designer_status` (bridge state, version, open graphs); `launch_designer` if it isn't running.
  `quit_designer` closes it (ask first: it's the user's app).
- **Find and understand nodes:** `search_nodes` (name/label/category/description across the 29 atomic
  nodes and the **whole** library; returns the exact `definition`), then `describe_node` for
  connector ids, parameter types and **enum values**. Never guess ids or enum numbers.
  `describe_node` also shows library slider ranges (`range a..b step c`) and every parameter's
  description, so pick values inside the range.
- **Inspect a graph:** `describe_graph` (ids, links as `input<-srcId.output`, non-default params,
  frames/comments), `list_graph_inputs` (exposed inputs and what they drive).
- **Safety net:** `snapshot_graph` before risky or large changes to a user's graph (a full .sbs
  copy in `~/.sd_mcp/snapshots/`; the open package, its file and saved state are untouched), then
  `diff_graph` to show exactly what changed against `'saved'`, `'latest'`, a label or a path.
  Prefer this over Undo, which is per document. Report the diff to the user after editing their
  graphs.
- **Look:** `preview_node` (image of any node, even ones not feeding an output),
  `screenshot_designer` (what the user sees: window, graph, 2D, 3D, panels), `open_graph`
  (open a graph and centre on a node first, so the user and screenshots see it).
- **Measure:** `node_stats` (exact min/max/mean/std, regions, sampled pixels). Prefer numbers
  over eyeballing. `check_tiling` measures the wrap-around seam per axis (ratio ≈ 1 seamless,
  > 3 visible); trim sheets only need horizontal.
  `compare_to_reference` matches tones against a reference image (`import_bitmap` it too if you
  want it in the graph). Compare **like with like**: a `reference_region` of plain, lit material
  against the matching `region` of the node. A whole product shot is dominated by its background,
  and lit renders or photos include shading, so their contrast is higher than a baseColor's
  should be (on the dwarf house: whole image EMD 0.33; a lit stone wall vs the stone strip
  0.04; a wall in shadow 0.085 darker). Treat the suggested `x*gain + bias` as a starting point
  for levels, not a target.
- **Tune a value:** `sweep_param` instead of edit-rebuild-look loops: several values of one
  parameter (or of an exposed graph input) side by side with numbers, original restored
  afterwards. Use `view_node` to watch the final output while sweeping an early node.
- **Edit:** one-off `add_node` / `import_bitmap` (reference images, masks, painted maps) / `set_params` / `connect` / `disconnect` / `move_nodes` /
  `delete_nodes`; several changes at once with `apply_edits` (one call, one undo step, refs for new
  nodes); new graph with `create_graph`; controls with `expose_param` / `remove_graph_input`;
  size with `set_graph_size`.
- **Make graphs readable** (do this for every graph you build or restructure): `arrange_graph`
  (columns by data flow, positions only), then `add_frame` per logical section and `add_comment`
  for non-obvious choices.
  - **Use portals when the wires get too cluttered.** Check with `screenshot_designer('graph')`
    after `open_graph`. Signs of clutter: one output fanning out to many nodes, wires crossing
    sections or the whole graph, or a bundle of lines you can't follow. Then run
    `set_link_display(mode='portal')`, typically `fanout_at_least=4` plus `longer_than=1000`,
    take another screenshot, and keep short local wires visible so each section still reads.
    On the trim sheet this hid 85 of 253 wires (58 from one shared gradient) with identical
    output. Portals are a display change only, but the tool saves and reloads the package, so
    tell the user.
- **Bigger logic:** `run_designer_script` (script on disk, preferred for anything long) or
  `execute_designer_code`. Both time out (`timeout_s`); `cancel_designer_job` aborts.
- **Output:** `save_package`; `export_outputs` (straight from Designer, live unsaved state,
  same as the cooked render up to 16-bit rounding: the self-test sees a few pixels off by
  <= 3/65535); `sbsar_info` + `render_sbs` (cooked .sbsar, exposed
  params, size override, formats); `preview_maps` to look at rendered files.

**Loop:** search/describe → build (script or `apply_edits`) → `describe_graph` + `preview_node`
on intermediate nodes → `sweep_param` to pick values → `node_stats` / `check_tiling` to check the
numbers → render/export → `preview_maps` → fix → repeat. Look at the result before telling the
user something works.

**Self-test:** `mcp_server/venv/bin/python tests/test_all_tools.py` exercises every tool over MCP
on a temporary graph (exit 0 = all passed). Its "designer facts" checks re-measure the Designer
behaviour this file states (enum ids, connector ids, gradient and normal conventions, sd API
quirks); when you add such a fact, add a check there too. It also passes every documented tool
parameter at least once; a new parameter needs a check, not just a docstring line. Run it after changing the server, plugin or helpers.
Also run `mcp_server/venv/bin/python -m pytest` (`tests/unit`, no Designer needed): it
fails if a tool is missing from README's Tools table/count or has no check in the self-test.
Add unit tests there for new pure-Python code (server-side parsing, maths, image handling).

Fallback without MCP: `python client/sd_run.py script.py [--timeout N]`, `--status`, `--cancel`
(no undo grouping).

## Working on this project

How the plugin, server, helpers and command-line tools fit together, and which file does what:
README.md, **How it works**. Agent-specific notes:

`server.py` loads this file from the folder above `mcp_server/` at startup, so keep it there.

- **How changes reach Designer:** `server.py` and `designer_helpers.py` changes take effect when
  the MCP server restarts (helpers are re-sent with every call; the user reconnects in `/mcp`, or
  test them directly with a fresh MCP client such as the self-test). **Plugin** changes must be
  copied into Designer's plugin folder (re-run `install.py`; folder paths in README.md, Install)
  and need a **Designer restart** (never hot-reload; see below): with the user's OK,
  `quit_designer` then `launch_designer`. `quit_designer` refuses while packages have unsaved
  changes; never pass `discard_unsaved=True` unless the user said to drop them.
- The bridge token file (README.md, Security) gives code execution in Designer: **never print,
  log or send its contents anywhere.**
- Environment variables `SD_DESIGNER_BIN_DIR`, `SD_DESIGNER_APP`, `SD_DESIGNER_LOG`, `SD_SNAPSHOT_DIR`, `SD_BRIDGE_PORT`: see README.md,
  Configuration. A port change must be made for the plugin and the server alike.
- **When tools fail:** match the symptom in README.md, Troubleshooting. As an agent, first try
  `launch_designer`, then `read_designer_log`. If the bridge accepts connections but never
  answers, or a tool is missing in Claude Code, only the user can fix it (restart Designer /
  reconnect `/mcp`), so tell them.
- The repository is public on GitHub. Commit and push only when the user asks.
- **There is no CI and none is planned.** Don't add GitHub Actions or other CI; all tests run
  locally (self-test and `tests/unit`).

## Undo, timeouts, plugin lifecycle

- Each code run and each edit tool is wrapped in one Designer undo transaction
  (`SDHistoryUtils.UndoGroup`), so Ctrl+Z reverts a whole run (the self-test checks this: one
  Undo removes a node added by `add_node`, one Redo restores it).
- Undo history is **per document**: Edit > Undo (and Ctrl+Z) reverts the last step of the
  graph in focus. **Never trigger Undo yourself while one of the user's graphs is open in the
  editor**; it hits their document. (It happened once; an immediate Redo restored it, which a
  full diff against the saved file confirmed.) If you must: the actions live in a `QMenu`
  (find them via `QApplication.instance().allWidgets()`, not `mainWindow.findChildren`), and
  they apply **asynchronously**, so call `QApplication.processEvents()` before reading results.
- Timeouts and cancel use a trace hook in the plugin: the abort happens the next time Python
  runs, so one long C++ call (a huge `graph.compute()`) completes first. A script that catches
  `BaseException` swallows the abort, so don't do that.
- **Never hot-reload the sd_bridge plugin** (`importlib.reload` inside Designer). The running
  server keeps references to the old module, and reloading under it breaks the bridge until
  Designer restarts. Plugin changes need a Designer restart.

## Environment facts

- No `pysbs` (the Automation Toolkit is enterprise-licensed). Everything goes through the
  in-app `sd` API via the bridge, plus `sbscooker`/`sbsrender`.
- Code runs on Designer's main thread, so the UI freezes while a script runs. Keep scripts finite.
- Library graphs are `.sbs` files in `app.getPath(SDApplicationPath.DefaultResourcesDir)/packages`.
  In scripts: `pkgMgr.loadUserPackage(path)` (check `getPackages()` first to reuse an open one),
  `pkg.findResourceFromUrl('<graph id>')`, `graph.newInstanceNode(resource)`.
  Use `search_nodes` / `describe_node` to find names and ids instead of parsing XML.
- Python tracebacks from plugins land in the Designer log: use `read_designer_log` (filters:
  `contains`, `errors_only`; by default only since the last start, detected by the
  "Python SDK Version" line Designer logs once per start). Read it when the bridge misbehaves or
  a plugin change doesn't seem to load.
- Harmless log noise: creating an exposed input logs "No output node defined" and "Some Get
  nodes don't have a variable name" for the moment between creating the function node and
  naming it. The exposure still works.

## sd API gotchas

- **`sd.api.apiexception.APIException` derives from `BaseException`, not `Exception`.**
  `except Exception` will NOT catch it. Use `except (Exception, APIException)`.
- Atomic nodes: `graph.newNode('sbs::compositing::<name>')`, output connector
  `unique_filter_output`. Common inputs: `input1` (levels, blur, normal, warp, directionalwarp,
  transformation…), blend `source` / `destination` / `opacity`, warp `inputgradient`,
  directionalwarp `inputintensity`, output node `inputNodeOutput`.
- Valid atomic ids: `graph.getNodeDefinitions()` (29 in Designer 16). Check an id is in that
  set **before** `graph.newNode(id)`; an unknown id reportedly hangs Designer 15 (16 raises).
- Instance (library) nodes: connector ids equal the library graph's identifiers
  (bevel: in `input`, outs `height`/`normal`; tile_generator: out `TileGenerator`).
- Property types matter (`node.getPropertyFromId(id, SDPropertyCategory.Input).getType()`):
  levels `levelin*/levelout*` are **float4**; uniform `outputcolor` is **ColorRGBA**;
  `blendingmode`, `$format`, `$tiling` are **enums** (set via an enumerator's
  `getDefaultValue()` or `SDValueEnum.sFromValueId(type, id)`). `set_params` converts for you.
- `$format` enum ids: `8_bits_per_channel`, `16_bits_per_channel`, `hdr_low_precision`,
  `hdr_high_precision` (type `sbs::compositing::format`).
- Blend modes: copy 0, add 1, subtract 2 (enum id spelled `substract`), multiply 3, addsub 4, max 5, min 6, switch 7,
  divide 8, overlay 9, screen 10, softlight 11. **Don't trust third-party tables**: one public
  SD MCP lists 4 = Max / 5 = Min / 6 = Difference, which is wrong (there is no Difference).
  Read enums with `describe_node`.
- Bitmaps: `SDResourceBitmap.sNewFromFile(pkg, path, EmbedMethod.X)` + `graph.newInstanceNode(res)`
  gives an atomic `bitmap` node (out `unique_filter_output`, param `bitmapresourcepath` =
  `pkg:///<resource id>`). The `EmbedMethod` docstrings in `sdresource.py` are shifted by one:
  `Linked` references the original file, `CopiedAndLinked` copies it into `<package>.resources/`
  (prefixed `XXXXXX-`; in an OS temp folder until the package is first saved, then moved), and
  `BinaryEmbedded` raises `NotSupported`. The node's `$outputsize` is the image's own size (log2),
  not the graph's. Verified: pixels read back exactly.
- Output nodes: annotation `usages` = `SDValueArray` of
  `SDValueUsage.sNew(SDUsage.sNew('baseColor', 'RGBA', 'sRGB'))`; annotations `identifier` /
  `label` via `SDValueString`. The identifier becomes the exported/rendered file name.
- **Connections are reported from the queried node's side:** for `c` in
  `node.getPropertyConnections(prop)`, `getOutputPropertyNode()` / `getOutputProperty()` is
  `node`/`prop` itself and `getInputPropertyNode()` / `getInputProperty()` is the **other** node,
  whatever direction the data flows.
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
  `$outputsize` only take effect with inheritance set to Absolute (`set_params` does that).
  `setDefaultParentSize()` takes **pixels** (values under 16 are clamped to 16). See Rendering
  for how size interacts with sbsrender.
- Node positions are node **centres**; a node is 96×96 in graph units. Frames:
  `SDGraphObjectFrame.sNew(graph)` with `setTitle`, `setPosition` (top-left), `setSize`,
  `setColor`, `setDescription`; comments: `SDGraphObjectComment.sNew(graph)` or
  `sNewAsChild(node)` with `setDescription`; list them with `graph.getGraphObjects()`.
- Slider ranges exist only for **library** node parameters, as annotations (`min`, `max`,
  `step`, `clamp`) on the referenced graph's input property. Atomic nodes expose no ranges, only
  `prop.getDescription()`.
- `getQtForPythonUIMgr().getMainWindow()` is a **hidden** QMainWindow; closing it does nothing.
  The window the user sees is another top-level widget (`QStackedWidget` titled "Adobe Substance
  3D Designer"); closing the visible top-level widgets quits Designer normally (`quit_designer`).
  If a window refuses to close (a dialog), Qt 6's `QApplication.quit()` gives up too; `exit(0)`
  stops the event loops regardless, which is `quit_designer`'s fallback after 5 s.
  `SDPackage.isModified()` tells whether a package has unsaved changes.
- That visible widget is a 2-page stack: the main window (page 0) and the **Home screen**
  (page 1, current after a fresh start). While Home shows, every dock reports `isVisible()`
  False, graphs open behind it, and only whole-window captures work (they render the hidden
  main window). Leave it with Home's own "Close home screen" button (`close_btn`);
  `open_graph` and a `launch_designer` that started Designer do this.
- Fit the graph view: the graph dock's toolbar action "Fit in view (selection)" (shortcut F)
  fits everything when nothing is selected (`open_graph` without a node does this).
- **Portals** are a per-connection display flag, `<displayType v="1"/>` inside the
  `<connection>` element in the .sbs (no flag = normal wire). Any connection can be a portal; Dot
  nodes (`passthrough`) are just optional reroute points. The sd API can't read or set it, so
  `set_link_display` uses the **file-level edit pattern**: snapshot, save the package, edit the
  .sbs XML, reload the package, reopen the graph in a separate call (reopening in the same call as
  the reload can leave the graph panel empty). Reloading resets that package's undo history.
  Use the same pattern for other things the API can't do, always with a snapshot and a
  `diff_graph` plus `node_stats` check that the output is unchanged.
- `pkgMgr.saveCopyOfPackageAs(pkg, path)` writes a copy without changing the package's path or
  saved state (what snapshots use); `savePackageAs` does change them.
- UI: current graph via `getQtForPythonUIMgr().getCurrentGraph()`; editor control via
  **`app.getUIMgr()`**: `openResourceInEditor(graph)`, `focusGraphNode(graphViewID, node)`
  (ids via `getGraphViewIDCount/At`, `getGraphFromGraphViewID`), `getGraphNodeBBox`,
  `setExplorerSelection`.
- `pkgMgr.savePackageAs()` doesn't reliably leave the package reporting that file path. To
  close earlier builds, unload every user package containing your graph identifier.

## Library node facts (Designer 16)

- `gradient_linear_1` with `rotation` 0: **1.0 at the top row, 0.0 at the bottom**, constant
  across x. With levels this makes a vertical coordinate, handy for per-row height profiles
  (bands, chamfers) in trim sheets.
- `tile_generator`: `Nb_X`, `Nb_Y`, `Pattern_Type` (2 = square, 1 = image input, 9 = brick
  default), `Scale`, `Offset` (row offset), `Offset_Random`, `Offset_Random_Seed`,
  `Free_Rotation` (degrees), `Luminance_Variation-Contrast` (float2: random luminance per tile,
  contrast). The same seed/layout twice gives a matching per-tile random mask.
- `bevel`: `distance` (~0.02–0.08 for small chamfers), `smoothing`; out `height`.
- `hbao`: in `input`, out `output`. `curvature_smooth`: in `input` (normal), out `height`.
- `noise_anisotropic_noise`: default streaks run horizontally (`X_Amount`, `Y_Amount`).
- Atomic `warp` intensity is strong: ~0.05–0.1 gives a gentle wave; 1.5 destroys the pattern.
- Atomic `normal`: `inversedy=True` gives **OpenGL** normals (Blender). Verified: on a raised
  band the top chamfer's green is > 0.5.

## Rendering and verifying

- **sbsrender ignores inputs the .sbsar doesn't expose**, silently (`render_sbs` warns).
- **Graph size:** a fixed (Absolute) `$outputsize` isn't exposed, so size overrides are ignored.
  An overridable graph (`set_graph_size(..., overridable=True)`: relative to parent, offset 0,
  `defaultParentSize` = 2^n) exposes `$outputsize`; `--set-value $outputsize@n,n` sets the
  **parent** size, and a non-zero relative offset is applied on top. Without an override
  sbsrender assumes a 256 px parent, so `render_sbs` reads the graph's `defaultParentSize` from
  the .sbs and passes it. `render_sbs` prints each file's size, so check it.
- **A cooked .sbsar forgets the default parent size:** sbscooker writes `$outputsize` default
  `8,8` (256 px) whatever the graph's `defaultParentSize` (no cooker option changes it), so a
  .sbsar renders at 256 px here and in other Substance apps unless a size is set. `render_sbs`
  on a .sbsar says so (it reads the default from the archive's .xml with the system `tar`);
  pass `size_log2` or render the .sbs.
- Pixel precision: grayscale 16-bit PNGs load in PIL as `I;16` (normalise by 65535), but PIL
  loads 16-bit **RGBA** PNGs as 8-bit. For exact values use `node_stats`, which reads the raw
  buffer: RGBA or single-channel (`LUM*`), little-endian, uint8 / uint16 / float16 / float32 per
  `getPixelFormat()`, row stride `getRowPitch()`.
- Verify orientation and conventions numerically (sample known pixels), not just visually.

## Screenshots

- `QWidget.grab()` on Designer's widgets only. **Never use `QScreen.grabWindow`**, not even
  with Designer's own window id: on macOS both copy the screen area, so they capture whatever
  covers Designer (the user's other apps).
- The GPU-drawn 3D view is black under widget capture, so `3d` triggers the 3D view's own
  **Camera > Copy Render to Clipboard**, reads the image, and restores the user's clipboard in a
  `finally` (verified repeatedly). Its menus fill lazily: emit `menu.aboutToShow` and keep Python
  references to menus and actions, or the wrappers go stale ("Internal C++ object already
  deleted"). Never use "Save Render...": its modal file dialog blocks the bridge.
- Dock titles change with content ("dwarf_trimsheet", "Blend"). Find panels by object name:
  `areaA_` explorer, `areaB_` graph, `areaC_` parameters, `areaD_` 3D view, `areaE_` 2D view,
  `areaF_` console, `areaG_` library.

## Example

`examples/build_dwarf_trimsheet.py`: a complete config-driven generator for a 2048² stone +
wood trim sheet (11 horizontal strips, tileable in U), outputting baseColor, normal (OpenGL),
roughness, metallic, height and AO. A good template for band and tile helpers, type-safe
parameter setting, and rebuild-safe package handling. (Its size is fixed; call
`set_graph_size(overridable=True)` afterwards if you need size overrides. Re-running it builds a
fresh graph, so portals, frames and layout changes made afterwards are lost; reapply them.)
The self-test builds a copy with its `OUT_SBS = ...` and `GRAPH_ID = ...` lines rewritten, so
keep each of those assignments on one line.
