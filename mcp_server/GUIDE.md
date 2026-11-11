# GUIDE.md: notes for AI agents driving Substance Designer

You have access to the user's **running** Substance 3D Designer through the `substance-designer` MCP server. These notes
were learned the hard way: read them before writing `sd` scripts. (`get_guide()` serves this part,
`get_guide('scripting')` the sd API and Qt part at the end; the resource `designer://agents-guide` serves both. The
server's own instructions are one short paragraph, as MCP clients cut long ones: leave these tools alone unless the user
asks for Designer work; right before the first Designer tool call, call `get_guide()` and confirm to the user. Changing
this project itself: [AGENTS.md](../AGENTS.md).)

## Rules that protect the user's work

- **Never print, log or send the bridge token** (`~/.sd_claude_bridge_kve_token`): it gives code execution in Designer.
- **Never trigger Undo while one of the user's graphs is open in the editor.** Undo is per document and hits theirs (it
  happened once; an immediate Redo restored it). See Undo below.
- **A Designer the user opened is theirs: never close it.** If a task needs it closed or restarted (a plugin change, the
  self-test's quit checks), or needs Designer and it is closed, ask the user to save, close and reopen it, or to open
  it; `quit_designer` refuses. Don't get around that with `kill` or a script, even when the user asks: tell them to
  close it, as Designer then asks them about unsaved work itself. A Designer an agent started is disposable:
  `quit_designer` ends it, forcing if needed and dropping unsaved changes; `designer_status` says which it is. Close
  yours when done, so the user doesn't start working in it.
- **`snapshot_graph` before risky or large edits** to a user's graph, then `diff_graph` and report the diff. Prefer
  this over Undo.
- **`set_link_display` saves and reloads the package** (undo history reset): tell the user.
- **Renaming an output that already existed can break a closed graph using it:** when `apply_edits`' result says "Tell
  the user", tell the user, in those terms (Output nodes, in the scripting part).
- **Never hot-reload the sd_claude_bridge_kve plugin** (`importlib.reload` inside Designer): the running server keeps
  references to the old module and the bridge breaks until Designer restarts.

## Which tool for what

Parameters are in each tool's description; this is when to reach for which.

- **Start:** `designer_status`; if Designer isn't running, ask the user to open it (`launch_designer` is for tests and
  work on this project); `quit_designer` (the rules). Designers side by side, each on a bridge port of its own: Several
  Designers, below.
- **Find and understand nodes:** `search_nodes` (the atomic nodes and Designer's **whole** library of compositing
  graphs, not its function graphs: ready-made materials such as `materials/pbr/bricks_001` included, hidden ones on
  `include_hidden`; an empty result says how many match; returns the exact `definition`), then `describe_node` for
  connector ids, parameter types, **enum values**, library slider ranges and descriptions. Never guess ids or enum
  numbers; pick values inside the slider range.
- **Inspect a graph:** `describe_graph`, `list_graph_inputs`. Graphs are found by identifier; several open graphs with
  the same one (every new graph is "New_Graph") are refused as ambiguous unless one is open in the editor.
- **Safety net:** `snapshot_graph`, `list_snapshots`, `diff_graph` (the rules).
- **Look:** `preview_node` (any node, even one feeding no output), `screenshot_designer` (what the user sees),
  `open_graph` (open the graph first, so the user and screenshots see it; `frame=` or `node_ids=` zooms to one
  section). A screenshot costs about width × height / 750 tokens: keep `max_size` small, `crop`, and zoom with
  `open_graph` rather than shooting the whole graph big.
- **Measure:** `node_stats` (exact numbers; prefer them to eyeballing), `check_tiling` (trim sheets only need
  horizontal), `compare_to_reference` for tones against a reference image (add it to the graph with an `apply_edits`
  `bitmap` op if wanted). Compare **like with like**: a `reference_region` of plain, lit material against the matching
  `region`. A whole product shot is dominated by its background, and lit renders or photos include shading, so their
  contrast is higher than a baseColor's. The suggested `x*gain + bias` is a starting point for levels, not a target.
- **Tune a value:** `sweep_param`, not edit-rebuild-look loops; `view_node` watches the final output while sweeping an
  early node.
- **Edit:** `apply_edits` for every node edit, one or many: ops `add`, `bitmap` (reference images, masks, painted
  maps), `set`, `connect`, `disconnect`, `move`, `delete`, `expose` (a parameter as a graph input). One call is one undo
  step; refs name nodes added earlier in the batch; which mistakes refuse the whole batch and which stop it partway: its
  description. Also `create_graph`, `remove_graph_input`, `set_graph_size`.
- **Make graphs readable** (every graph you build or restructure): `arrange_graph` (positions only), then `add_frame`
  per logical section and `add_comment` for non-obvious choices.
  - **Portals when the wires get cluttered.** Check with `screenshot_designer('graph')` after `open_graph`. Signs: one
    output fanning out to many nodes, wires crossing sections, a bundle you can't follow. Then
    `set_link_display(mode='portal')`, typically `fanout_at_least=4` plus `longer_than=1000`, screenshot again, and keep
    short local wires visible.
- **Bigger logic:** `run_designer_script` (a script on disk, preferred for anything long) or `execute_designer_code`;
  `cancel_designer_job` aborts. Read `get_guide('scripting')` first and confirm to the user: until then those two refuse
  to run.
- **Output:** `save_package`; `export_outputs` (straight from Designer, live unsaved state; within a few 1/65535 steps
  of the cooked render at a few pixels; why renders differ run to run is ROADMAP item 17); `sbsar_info` + `render_sbs`
  (exposed params, size, formats); `preview_maps` for rendered files.

**Loop:** search/describe → build (script or `apply_edits`) → `describe_graph` + `preview_node` on intermediate nodes →
`sweep_param` → `node_stats` / `check_tiling` → render or export → `preview_maps` → fix → repeat. Look at the result
before telling the user it works.

Fallback without MCP: `python client/sd_run.py script.py [--timeout N]`, `-c CODE`, `--status`, `--cancel` (no undo
grouping, no `ARGS`).

## Undo and timeouts

- Each code run and each edit tool is one Designer undo transaction (`SDHistoryUtils.UndoGroup`), so Ctrl+Z reverts a
  whole run.
- Undo history is **per document** (Edit > Undo reverts the last step of the graph in focus). If you must trigger it:
  the actions live in a `QMenu` (find them via `QApplication.instance().allWidgets()`, not `mainWindow.findChildren`)
  and apply **asynchronously**: schedule them with `QTimer.singleShot(0, action.trigger)` (outside your own undo group)
  and call `QApplication.processEvents()` before reading results. Raise and activate the main window first
  (`getQtForPythonUIMgr().getMainWindow()`, `raise_()`, `activateWindow()`): in a Designer just started, with another
  Designer in front, Undo of an output's fields sometimes did nothing without it. It leaves the other app in front.
- Timeouts and cancel use a trace hook in the plugin: the abort happens the next time Python runs, so one long C++ call
  (a huge `graph.compute()`) completes first. A script catching `BaseException` swallows the abort: don't. An abort
  landing where Python only reports an exception (a finalizer such as every sd object's `__del__`, a weakref callback,
  a Qt slot) is raised again at the next traced event (in the script, a module it imports or a loop driven from C), also
  when the finalizer raises an error of its own or runs long. A job still queued after 15 minutes is dropped, never run
  late.

## Environment facts

- No `pysbs` (the Automation Toolkit is enterprise-licensed): everything goes through the in-app `sd` API via the
  bridge, plus `sbscooker`/`sbsrender`.
- Code runs on Designer's main thread, so the UI freezes while a script runs. Keep scripts finite.
- Library graphs are `.sbs` files in `app.getPath(SDApplicationPath.DefaultResourcesDir)/packages` and its subfolders.
  In scripts: `pkgMgr.loadUserPackage(path)` (check `getPackages()` first to reuse an open one),
  `pkg.findResourceFromUrl('<graph id>')`, `graph.newInstanceNode(resource)`. Loaded library packages count as user
  packages; the tools skip them when looking a graph up by name, and refuse to save them, edit their files or change
  their graphs, with one message (`_library_refusal`). The graph open in the editor can still be one: reading it and
  `snapshot_graph` with no graph given work. Your own code isn't checked: Designer takes an edit to a library graph, and
  a package using it sees it at once (seen by hand).
- Plugin tracebacks land in Designer's log (`read_designer_log`; "since the last start" means after the "Python SDK
  Version" line logged once per start, or, while Designer is still starting, from its "===== New Session =====", a
  session that ended at once, a process handing over to the running Designer, not counting). Read it when the bridge misbehaves or a plugin change doesn't seem to load.
- Harmless log noise: creating an exposed input logs "Some Get nodes don't have a variable name", and may log "No
  output node defined", until the function node is named. The exposure works.
- **Several Designers side by side:** `launch_designer(port=...)` runs one per bridge port, on macOS (other platforms
  not tried: `launch_designer`), each with its own temp folder, log, settings and crash dumps, recorded per port;
  `read_designer_log(port=...)` reads its log, also after it ended. The user's Designers share one log, their lines not
  told apart. All share the preferences plist, so none is started next to the user's.
  Crash dumps: Designer's `Sentry-Crashpad/completed` (for one an agent started on macOS, under
  `/tmp/sd_mcp_<uid>_<port>/home`). How: `server_tools/lifecycle.py`.

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
  divide 8, overlay 9, screen 10, softlight 11. **Don't trust third-party tables**: one public SD MCP lists 4 = Max /
  5 = Min / 6 = Difference, which is wrong (there is no Difference). Read enums with `describe_node`.

## Library node facts (Designer 16)

- `gradient_linear_1` with `rotation` 0: **1.0 at the top row, 0.0 at the bottom**, constant across x. With levels this
  makes a vertical coordinate, handy for per-row height profiles (bands, chamfers) in trim sheets.
- `tile_generator`: `Nb_X`, `Nb_Y`, `Pattern_Type` (2 = square, 1 = image input, 9 = brick default), `Scale`, `Offset`
  (row offset), `Offset_Random`, `Offset_Random_Seed`, `Free_Rotation` (degrees), `Luminance_Variation-Contrast`
  (float2: random luminance per tile, contrast). The same seed and layout twice give a matching per-tile random mask.
- `bevel`: `distance` (~0.02–0.08 for small chamfers), `smoothing`; outs `height`, `normal`.
- Ready-made materials (`materials/pbr/...`): outputs start with `diffuse`, which is black on a metal (`metal_003`).
  With no `output`, tools take the one tagged base colour, else the first, and say which; pass `output` for another
  (`normal`, `roughness`, `metallic`, `height`...). `normal_format` defaults to DirectX (0); OpenGL is 1.
- `hbao`: in `input`, out `output`. `curvature_smooth`: in `input` (normal), out `height`.
- `noise_anisotropic_noise`: default streaks run horizontally (`X_Amount`, `Y_Amount`).
- Atomic `warp` intensity is strong: ~0.05–0.1 gives a gentle wave; 1.5 destroys the pattern.
- Atomic `normal`: `inversedy=True` gives **OpenGL** normals (Blender): where height rises towards the top of the image,
  green is below 0.5 (a raised band's top chamfer is above 0.5).

## Rendering and verifying

- **sbsrender ignores inputs the .sbsar doesn't expose**, silently (`render_sbs` warns).
- **Graph size:** a fixed (Absolute) `$outputsize` isn't exposed, so size overrides are ignored. An overridable graph
  (`set_graph_size(..., overridable=True)`: relative to parent, offset 0, `defaultParentSize` = 2^n) exposes
  `$outputsize`; `--set-value $outputsize@n,n` sets the **parent** size, a non-zero relative offset applied on top.
  Without an override sbsrender assumes a 256 px parent, so `render_sbs` passes the graph's `defaultParentSize` from the
  .sbs. Check the printed file sizes.
- **A cooked .sbsar forgets the default parent size:** sbscooker writes `$outputsize` default `8,8` (256 px) whatever
  the graph's `defaultParentSize` (no cooker option changes it), so a .sbsar renders at 256 px here and in other
  Substance apps unless a size is set. `render_sbs` on a .sbsar says so (it reads the archive's .xml with `tar`).
- Pixel precision: grayscale 16-bit PNGs load in PIL as `I;16` (normalise by 65535), but PIL loads 16-bit **RGBA**
  PNGs as 8-bit. For exact values use `node_stats`, which reads the raw buffer: little-endian, uint8 / uint16 / float16 /
  float32 per `getPixelFormat()`, row stride `getRowPitch()`. Outputs seen so far are `RGBA*` or `LUM*` (even an
  imported RGB JPG or grey+alpha PNG computes as `RGBA8`); the other `SBSPixelFormat` layouts (`RGB*`, `BGR8`, `BGRA8`,
  `LUMALPHA*`) are decoded too, untested against Designer.
- Verify orientation and conventions numerically (sample known pixels), not just visually.

## Example

`examples/build_dwarf_trimsheet.py`: a config-driven generator for a 2048² stone + wood trim sheet (11 horizontal
strips, tileable in U) with baseColor, normal (OpenGL), roughness, metallic, height and AO. A template for band and tile
helpers, type-safe parameter setting, rebuild-safe package handling, and a readable graph: nodes grouped into sections
as built, laid out by data flow inside each, one titled frame per section (its description carries the notes), portals
for long links between sections, an overridable size (2048 by default). Re-running it closes the previous build (the
package at `OUT_SBS`) and builds a fresh graph, so later edits are lost: change the script instead. It refuses while
that build has unsaved changes, and leaves other packages with a graph of that name open (a copy saved elsewhere, an
unsaved one). Re-running with the previous build open in an editor tab (an unload and a reload in one call) caused no
crash in five tries, and the self-test's re-runs do it too. The self-test builds a copy with its `OUT_SBS = ...` and
`GRAPH_ID = ...` lines rewritten, so keep each of those assignments on one line.

# Scripting: raw `sd` and Qt code

Served by `get_guide('scripting')`: read it before writing code for `execute_designer_code` or `run_designer_script`.
The rules and the first pitfalls are in the core, `get_guide()`.

## sd API gotchas

- Atomic nodes: `graph.newNode('sbs::compositing::<name>')`, output connector `unique_filter_output`. Common inputs:
  `input1` (levels, blur, normal, warp, directionalwarp, transformation…), blend `source` / `destination` / `opacity`,
  warp `inputgradient`, directionalwarp `inputintensity`, output node `inputNodeOutput`.
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
  raises `NotSupported`. The node's `$outputsize` is the image's own size (log2).
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
  | Nodes, no output node | stored value | sets it, **deletes the graph and its nodes** | stored value stays reset | refuse, and say it drives nothing |
  | Nodes and an output node | the function | sets it, **deletes the graph and its nodes** | stored value stays reset | refuse |

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
  bridge calls with short pauses** (back to back, Designer once crashed while tearing down the old views; returning to
  its event loop between the steps lets that finish). If it recurs, read the newest crash dump's crashing module first.
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
  (seen twice); `setSelected(True)` on its scene item selects it too (the API reports it) but leaves the panel as it was
  (seen by hand). The API itself can't select nodes in the view (`focusGraphNode` only centres one). After such
  experiments, restart Designer before real work (the user's: ask them): once, with the Parameters panel still showing a
  Dot of a package unloaded since, the next edit in another graph crashed Designer.
- Current graph: `getQtForPythonUIMgr().getCurrentGraph()`; editor control via **`app.getUIMgr()`**:
  `openResourceInEditor(graph)`, `focusGraphNode(graphViewID, node)` (ids via `getGraphViewIDCount/At`,
  `getGraphFromGraphViewID`), `getGraphNodeBBox`, `setExplorerSelection`. The dock's "Fit in view (selection)" (F) fits
  the selection, or everything when nothing is selected; `open_graph` fits every node, frame and free comment by wheel
  zoom instead.
- **Quitting:** through `quit_designer` (the rules), not from a script: `QApplication.exit(0)` has crashed Designer and
  left it hung. The plugin answers status from another thread, so a main thread frozen outside a job reads as idle.
  How: `server_tools/lifecycle.py`.
- `getQtForPythonUIMgr().getMainWindow()` is a **hidden** QMainWindow; the window the user sees is a top-level
  `QStackedWidget` with two pages, the main window and the **Home screen** (current after a fresh start). While Home
  shows, no panel reports itself visible, so `launch_designer` and `open_graph` close it first.
- PySide wrappers for Designer's Qt objects go stale ("Internal C++ object already deleted") unless you keep Python
  references to their parents; menus fill lazily (emit `menu.aboutToShow` first).
- **Screenshots:** `QWidget.grab()` on Designer's widgets only. **Never use `QScreen.grabWindow`**, not even with
  Designer's own window id: on macOS both copy the screen area, capturing whatever covers Designer (the user's other
  apps). Widget capture can't see the GPU-drawn 3D view: use `screenshot_designer('3d')`. Never use "Save Render...":
  its modal file dialog blocks the bridge.
- Dock titles change with content, so find panels by object name: `areaA_` explorer, `areaB_` graph, `areaC_`
  parameters, `areaD_` 3D view, `areaE_` 2D view, `areaF_` console (hidden by default; Windows > Console), `areaG_`
  library.
