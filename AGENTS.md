# AGENTS.md: notes for AI agents driving Substance Designer

You have access to the user's **running** Substance 3D Designer through the `substance-designer` MCP server. These
notes were learned the hard way: read them before writing `sd` scripts. (Served whole by `get_guide` and the resource
`designer://agents-guide`. The server's own instructions are one short paragraph, as MCP clients cut long ones: leave
these tools alone unless the user asks for Designer work; right before the first Designer tool call, call `get_guide()`
and confirm to the user.)

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
  the user", tell the user, in those terms (Output nodes, below).
- Commit or push only when the user asks; the repository is public. **There is no CI and none is planned**: don't add
  GitHub Actions or other CI.

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
  contrast is higher than a baseColor's (dwarf house: whole image EMD 0.33; lit stone wall vs the stone strip 0.04; a
  wall in shadow 0.085 darker). The suggested `x*gain + bias` is a starting point for levels, not a target.
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
    short local wires visible. On the trim sheet this hid 85 of 253 wires (58 from one gradient), output identical.
- **Bigger logic:** `run_designer_script` (a script on disk, preferred for anything long) or `execute_designer_code`;
  `cancel_designer_job` aborts.
- **Output:** `save_package`; `export_outputs` (straight from Designer, live unsaved state; within a few 1/65535 steps
  of the cooked render at a few pixels: the self-test allows 8 and prints what it measured; why renders differ run to
  run is ROADMAP item 17); `sbsar_info` + `render_sbs` (exposed params, size, formats); `preview_maps` for rendered
  files.

**Loop:** search/describe → build (script or `apply_edits`) → `describe_graph` + `preview_node` on intermediate nodes →
`sweep_param` → `node_stats` / `check_tiling` → render or export → `preview_maps` → fix → repeat. Look at the result
before telling the user it works.

Fallback without MCP: `python client/sd_run.py script.py [--timeout N]`, `-c CODE`, `--status`, `--cancel` (no undo
grouping, no `ARGS`).

## Undo, timeouts, plugin lifecycle

- Each code run and each edit tool is one Designer undo transaction (`SDHistoryUtils.UndoGroup`), so Ctrl+Z reverts a
  whole run (the self-test checks one Undo and one Redo for an `apply_edits` add op and for a code run).
- Undo history is **per document** (Edit > Undo reverts the last step of the graph in focus). If you must trigger it:
  the actions live in a `QMenu` (find them via `QApplication.instance().allWidgets()`, not `mainWindow.findChildren`)
  and apply **asynchronously**: schedule them with `QTimer.singleShot(0, action.trigger)` (outside your own undo group)
  and call `QApplication.processEvents()` before reading results.
- Timeouts and cancel use a trace hook in the plugin: the abort happens the next time Python runs, so one long C++ call
  (a huge `graph.compute()`) completes first. A script catching `BaseException` swallows the abort: don't. An abort
  landing where Python only reports an exception (a finalizer such as every sd object's `__del__`, a weakref callback,
  a Qt slot) is raised again at the next traced event (in the script, a module it imports or a loop driven from C), also
  when the finalizer raises an error of its own or runs long. A job still queued after 15 minutes is dropped, never run
  late.
- **Never hot-reload the sd_claude_bridge_kve plugin** (`importlib.reload` inside Designer): the running server keeps
  references to the old module and the bridge breaks until Designer restarts.

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
  Version" line logged once per start). Read it when the bridge misbehaves or a plugin change doesn't seem to load.
- Harmless log noise: creating an exposed input logs "No output node defined" and "Some Get nodes don't have a variable
  name" until the function node is named. The exposure works.
- **Several Designers side by side** (ROADMAP item 49), one per bridge port, on macOS (other platforms not tried:
  `launch_designer`). Designer is single-instance: starting, it reads the ID of the last one started
  (`session.instancePID`, preferences plist) and looks for its socket (`algipc-...-<ID>`, 41 bytes) in its own temp
  folder; found, it hands over its arguments and exits (`[IPC] Found instance PID` in the log). So `launch_designer`
  starts the binary, in `/`, with `SD_BRIDGE_PORT`, `TMPDIR=/tmp/sd_mcp_<uid>_<port>/temp/` (a socket path has at most
  103 bytes; under `/var/folders/...` it was too long and Designer made none) and, on macOS,
  `CFFIXED_USER_HOME=.../home`: Designer then keeps its log, settings and crash-dump database there (not one byte to the
  user's log, their `user_preferences.xml` left as it was) and loads user plugins from `SBS_DESIGNER_PYTHON_PATH`, set
  to the plugin folders the user's Designer loads (its newest project file's, else Designer's default, where install.py
  puts the plugin), then any value already set. `HOME` is unchanged, so the token is found. Each is recorded per port,
  with its home (Quitting, below); `read_designer_log(port=...)` reads its log, also after it ended. The user's
  Designers share one log, their lines not told apart. The preferences plist stays shared (each Designer writes its
  `session.instancePID` there), so none is started next to the user's (`lsof`: listening on another port). Tests:
  `test_lifecycle_env.py`, `lifecycle.check_launch_on_another_port`,
  `lifecycle.check_a_designer_sharing_the_temp_folder_hands_over`.

## sd API gotchas

- **`sd.api.apiexception.APIException` derives from `BaseException`, not `Exception`:** `except Exception` won't catch
  it. Use `except (Exception, APIException)`.
- Atomic nodes: `graph.newNode('sbs::compositing::<name>')`, output connector `unique_filter_output`. Common inputs:
  `input1` (levels, blur, normal, warp, directionalwarp, transformation…), blend `source` / `destination` / `opacity`,
  warp `inputgradient`, directionalwarp `inputintensity`, output node `inputNodeOutput`.
- Valid atomic ids: `graph.getNodeDefinitions()` (29 in Designer 16; a function graph lists `sbs::function::*`). Check
  an id is in that set **before** `graph.newNode(id)`: an unknown id reportedly hangs Designer 15 (16 raises).
- Instance (library) nodes: connector ids are the library graph's identifiers (bevel: in `input`, outs `height` /
  `normal`; tile_generator: out `TileGenerator`).
- Property types matter (`node.getPropertyFromId(id, SDPropertyCategory.Input).getType()`): levels `levelin*/levelout*`
  are **float4**; uniform `outputcolor` is **ColorRGBA**; `blendingmode`, `$format`, `$tiling` are **enums** (set via an
  enumerator's `getDefaultValue()` or `SDValueEnum.sFromValueId(type, id)`). `apply_edits`' `set` op converts for you
  and validates before changing anything.
- `$format` enum ids: `8_bits_per_channel`, `16_bits_per_channel`, `hdr_low_precision`, `hdr_high_precision` (type
  `sbs::compositing::format`).
- Blend modes: copy 0, add 1, subtract 2 (enum id spelled `substract`), multiply 3, addsub 4, max 5, min 6, switch 7,
  divide 8, overlay 9, screen 10, softlight 11. **Don't trust third-party tables**: one public SD MCP lists 4 = Max /
  5 = Min / 6 = Difference, which is wrong (there is no Difference). Read enums with `describe_node`.
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
  connector and computes black, with no error and not marked modified (measured: pixel `407fbfff`, then `00000000`). A
  new instance wired from the new name computes right again, with default parameters. Renaming back with that graph
  open doesn't help: the connector and the link go too.
- **Connections are reported from the queried node's side:** for `c` in `node.getPropertyConnections(prop)`,
  `getOutputPropertyNode()` / `getOutputProperty()` is `node`/`prop` itself and `getInputPropertyNode()` is the
  **other** node, whatever direction the data flows.
- `graph.compute()` computes the nodes feeding an **output node** (about 1 s for a 190-node 2048² graph);
  `node.getPropertyValue(outputProp).get()` is then an `SDTexture`. A node feeding no output got no texture in a fresh
  graph but did in the self-test's busier one, so rely on neither: attach a temporary output node, as `preview_node` and
  `node_stats` do.
- Exposing a parameter = a graph input via `graph.newProperty(id, type, SDPropertyCategory.Input)` (annotations
  `label`, `min`, `max`, `step`, `group`…) plus a function graph on the node parameter
  (`node.newPropertyGraph(prop, 'SDSBSFunctionGraph')`) whose output node is `sbs::function::get_<type>` with
  `__constant__` = the input id (`get_float1..4`, `get_integer1..4`, `get_bool`, `get_string`). Use the parameter's own
  type; enums → int. What a function graph on a parameter does (measured on a float4 and an enum parameter of atomic
  nodes and a float4 one of an instance node, "designer facts"; only a graph with an output node drives the value, and
  `fg.getOutputNodes()` tells, also after a reload):

  | Function graph | Output follows | `setPropertyValue` | `deletePropertyGraph` | The tools |
  |---|---|---|---|---|
  | None | stored value | sets it | - | set, sweep, expose |
  | Empty | stored value | sets it, **deletes the graph** | stored value stays reset | set, sweep, expose (reuses it) |
  | Nodes, no output node | stored value | sets it, **deletes the graph and its nodes** | stored value stays reset | refuse, and say it drives nothing |
  | Nodes and an output node | the function | sets it, **deletes the graph and its nodes** | stored value stays reset | refuse |

  `$` parameters differ: `deletePropertyGraph` switches any of them back to the node's default inheritance (relative to
  input on a levels node, all six measured; relative to parent on an instance node, `$outputsize` measured), so put the
  inheritance back, then set the value, as `remove_graph_input` does. At Absolute, `$outputsize` with an empty function
  or none reaching an output node follows its input or parent, not the stored value (8,8 stored, 16 px on a 16 px
  graph). Setting an int on an enum parameter is accepted whatever it is, and a value beyond the enum's can't be read
  back (`get()` raises). Adding a function graph resets the stored value to the default. `newPropertyGraph` on a
  parameter that has one returns it, nodes kept. A graph has one output node: `setOutputNode(k, True)` moves it to `k`,
  leaving the old function unused in the graph. A `get` node not feeding the output has no effect (`list_graph_inputs`
  leaves it out of `drives:`). An FX-Map's own graph (`node.getReferencedResource()`, no identifier) holds functions
  that read the graph's inputs too: its output follows such an input, and the tools count and list them. A function on
  the graph's own parameter drives it too (measured on `$outputsize`), but `SDGraph` has no `getPropertyGraph`, so the
  tools read those from the package's file, as last saved. Removing an input that a connected `get` reads changes the
  output with no error, so `remove_graph_input` refuses while a function other than a plain binding (one `get`, its
  output) names it.
- **Graph size** is log2 (`$outputsize` 11 = 2048), set with
  `graph.setInputPropertyValueFromId('$outputsize', SDValueInt2.sNew(int2(11, 11)))`; `setDefaultParentSize()` takes
  **pixels**. Generators inherit the graph size; filters inherit from their input. A node's `$format` and an absolute
  `$outputsize` only take effect with inheritance set to Absolute; relative to parent or input, `$outputsize` is a log2
  offset. The graph's own `$format` too (a new graph's follows its parent: 16 bits left a generator at RGBA8 until made
  Absolute). `apply_edits`' `set` op and `sweep_param` set Absolute for these. A `$randomseed` (graph or node) is the
  exception: inherited, its value is added to its parent's seed (a render's, or the graph's), and only an inherited graph
  seed stays a control of the cooked .sbsar; made Absolute, it stops following its parent. So the `set` op leaves a
  seed's inheritance as it is; to fix one on purpose, change it in code. **Changing a parameter's inheritance doesn't
  keep its value** (measured on a node's `$outputsize` and the graph's `$randomseed`, both directions; back to inherited
  gave the default): set the inheritance first, then the value (`sweep_param` restores in that order). Compare computed
  pixels with a tolerance: two computes of one setting differed by 2/65535, and raw buffers carry row padding.
- **Inheritance numbers differ between the API and the file.** API `SDPropertyInheritanceMethod`: RelativeToInput 0,
  RelativeToParent 1, Absolute 2. A .sbs `<relativeTo>`: 0 absolute, 1 relative to parent, 2 relative to input; the
  default isn't stored (parent for a graph, input for a node).
- Node positions are node **centres**; a node is 96×96 graph units. Frames: `SDGraphObjectFrame.sNew(graph)` with
  `setTitle`, `setPosition` (top-left), `setSize`, `setColor`, `setDescription`; comments:
  `SDGraphObjectComment.sNew(graph)` or `sNewAsChild(node)` with `setDescription`; list them with
  `graph.getGraphObjects()`.
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
- **Portals** are a per-connection display flag, `<displayType v="1"/>` in a node's own `<connections>/<connection>` in
  the .sbs (function graphs on parameters have their own connections; leave those alone). Designer's own UI portals are
  Dot nodes (`passthrough`): a transmitter given an ID (`<userId v="p1"/>` on its `compNode`) and a receiver that picks
  it in its Input Portal field, stored as an ordinary connection from the transmitter with that flag (seen once by hand,
  Designer 16.0.7; to the API a plain connection). A Dot node has no ID property ("designer facts"); `set_link_display`
  sets the flag on any connection, without Dots. The API can't read or set the flag, so `set_link_display` uses the
  **file-level edit pattern**: snapshot the live graph and copy the saved file, decide on the copy (no change → no
  save), save, edit the .sbs XML, then unload, load and reopen as **three separate bridge calls with short pauses**.
  Back to back, Designer once crashed (a null call in PySide from its own `node_align_tools` plugin, which adds a
  toolbar to each new graph view, while the old views were being torn down); returning to Designer's event loop between
  the steps lets the teardown finish, and 300 stress reloads since were clean. If it recurs, read the newest crash
  dump's crashing module first. A package whose graphs were **never opened in a view** has nothing to tear down, so a
  script that builds one can save, edit and reload it in one call (the example script does, for its portals). Use the
  pattern for other things the API can't do, with a `diff_graph` plus `node_stats` check afterwards.

## Designer UI (Qt)

- The graph editor's node view is a `QGraphicsView` inside the `areaB_` dock (a title bar and two toolbar rows above
  it); its **scene coordinates are graph units**. **Don't set its transform** (`fitInView`, `scale`): Designer keeps its
  own zoom level beside it, and the user's next wheel step jumps from that stale level (seen once: one notch went from a
  22 % fit to very close). Zoom with synthetic `QWheelEvent`s on the viewport, 1.2x per notch in Designer 16, and pan
  with `centerOn` (safe); `open_graph(frame=...)` does this, and the self-test checks a wheel step after a fit is
  exactly 1.2x. **Don't send it synthetic key events or right-clicks**: twice (right-click menus, then a sent Ctrl+C,
  which copied nothing, as sent key events bypass Qt's shortcuts) the view went empty, its nodes intact, and only
  unloading the package brought it back. A synthetic left click on a node selected it and switched the Parameters panel
  to it (seen twice); `setSelected(True)` on its scene item selects it too (the API reports it) but leaves the panel as
  it was (seen by hand). The API itself can't select nodes in the view (`focusGraphNode` only centres one). After such
  experiments, restart Designer before real work (the user's: ask them): once, with the Parameters panel still showing a
  Dot of a package unloaded since, the next edit in another graph crashed Designer.
- Current graph: `getQtForPythonUIMgr().getCurrentGraph()`; editor control via **`app.getUIMgr()`**:
  `openResourceInEditor(graph)`, `focusGraphNode(graphViewID, node)` (ids via `getGraphViewIDCount/At`,
  `getGraphFromGraphViewID`), `getGraphNodeBBox`, `setExplorerSelection`. The dock's "Fit in view (selection)" (F) fits
  the selection, or everything when nothing is selected; `open_graph` fits every node, frame and free comment by wheel
  zoom instead.
- **Quitting.** `getQtForPythonUIMgr().getMainWindow()` is a **hidden** QMainWindow; closing it does nothing. The window
  the user sees is a top-level `QStackedWidget` ("Adobe Substance 3D Designer"); closing the visible top-level widgets
  quits Designer normally, even with another top-level window showing (measured) or a modal dialog open. If a window
  refuses to close, Qt 6's `QApplication.quit()` gives up too, and `QApplication.exit(0)` stops the event loops, but
  Designer's teardown then races its own background threads: twice Adobe's licence check (`Alg::BinaryHardeningService`,
  on a `QtConcurrent` thread) crashed reading a destroyed profile and the process hung over 30 s. The shutdown can also
  hang at the very end, in `~QCoreApplication` waiting for the thread pool (seen once with the licence check; a Python
  task held in `QThreadPool.globalInstance()` does it on demand). So `quit_designer` only closes the windows, and past
  its wait the server ends the process (SIGTERM, then SIGKILL), only for a Designer an agent started. `launch_designer`
  records the process it started (its own child), its start time and, on macOS, its home in `agent_designer_file(port)`
  (`project_constants.py`), one per port, so a `/mcp` reconnect keeps it and a reused ID doesn't count; on Windows
  nothing is recorded, so every Designer counts as the user's. A close goes to whichever Designer holds the port, so it
  names the recorded process and any other refuses (`os.getpid()` inside Designer is that process, checked live). The
  plugin answers status from another thread, so a main thread frozen outside a job reads as idle (measured with a timer
  slot sleeping in a loop). Crash dumps: Designer's `Sentry-Crashpad/completed` (for one an agent started on macOS, in
  its home: Several Designers).
- The stack has two pages: the main window and the **Home screen** (current after a fresh start). While Home shows, no
  panel reports itself visible (`launch_designer` prints the count before and after closing it), so `launch_designer`
  and `open_graph` close it first, with Home's own "Close home screen" button (`close_btn`); keep the stack and the
  page referenced while clicking, or PySide reports the button as already deleted.
- PySide wrappers for Designer's Qt objects go stale ("Internal C++ object already deleted") unless you keep Python
  references to their parents; menus fill lazily (emit `menu.aboutToShow` first).
- **Screenshots:** `QWidget.grab()` on Designer's widgets only. **Never use `QScreen.grabWindow`**, not even with
  Designer's own window id: on macOS both copy the screen area, capturing whatever covers Designer (the user's other
  apps). Widget capture can't see the GPU-drawn 3D view (a grab of its viewport is leftover black or grey blocks,
  varying between calls), so `3d` uses the 3D view's **Camera > Copy Render to Clipboard** and restores the user's
  clipboard in a `finally`. Never use "Save Render...": its modal file dialog blocks the bridge.
- Dock titles change with content, so find panels by object name: `areaA_` explorer, `areaB_` graph, `areaC_`
  parameters, `areaD_` 3D view, `areaE_` 2D view, `areaF_` console (hidden by default; Windows > Console), `areaG_`
  library.

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

## Working on this project

How the plugin, server, helpers and command-line tools fit together: README.md, **How it works**.

**Load the `mcp-builder` skill** (`.claude/skills/mcp-builder/`: Anthropic's, from `anthropics/skills` at `ca45fc4`,
trimmed to its Python parts) before designing or changing tools (adding, merging or removing one, its parameters,
description, errors or results), and for evaluations. Where it differs from this file, this file wins. Its defaults this
project doesn't follow: comprehensive API coverage and service-prefixed names (few tools, unprefixed; node edits are
`apply_edits` ops; a new capability is a parameter or op of an existing tool where it fits, else a new tool rather than
an existing one complicated with completely different logic: ROADMAP.md "Fewer tools"); JSON results (they are compact
text for agents); Pydantic input models (inputs are typed parameters). Its code is for mcp 1.x; this server runs mcp
2.x (the note at the top of its `SKILL.md`).

The server (`server_tools/core.py`) loads this file from the folder above `mcp_server/`: keep it there. Its
instructions (`INSTRUCTIONS` in `server_tools/core.py`) must stay under 4,096 characters, and every text tool result
starts with a reminder until `get_guide()` has been called in the session (unit tests check both).

**Every new feature or fix comes with a test, in the same change.** A tool, a parameter or a documented behaviour gets
a check in the live self-test (`tests/test_all_tools/`, against the real Designer); pure-Python logic gets a unit test
in `tests/unit`. A claim in these docs without a test is a guess: test it or remove it. The unit tests fail when a tool
or a tool parameter is never exercised by the self-test, when an `apply_edits` op or an op's field is never passed in
one (run or not), or when a tool is missing from README's Tools table.

**Start with the tests, always (TDD).** Before implementing anything (a tool, a parameter, an op, a helper, a script, a
change in behaviour) or fixing an issue, write the tests that describe what it must do or reproduce the issue, run them
and watch them fail; only then write the code, until they pass. A test written after the code tends to check what the
code happens to do, and one never seen failing may not test anything. For anything that depends on Designer, add a live
check too, seen failing and passing in a scratch run (Running the tests), since a unit test may take a path Designer
never does: two review findings were disproved this way (an abort raised again during cleanup: Python unsets a trace
function that raises; a job starting inside the running one: Qt doesn't re-fire a timer whose slot is running, only a
direct call in a unit test did). Before a fix that depends on Designer's behaviour, measure every case the code
distinguishes, and fix the pattern everywhere it occurs, not just the reported instance (the `address-review` skill,
step 3: skipping these made findings recur round after round). If the test passes before any fix, either the issue
isn't real or the test can't see it: read the test against the issue to tell which; fix a blind test and run it again
before any fix, and say an issue that isn't real is so rather than "fixing" it. Code that changes no behaviour (a
rename, a move) needs no new failing test: run the existing tests of the code it touches before and after; they must
pass both times.

**Review your own work before calling it done**, as a reviewer, not its author: does it cover the neighbouring cases (a
node as well as the graph, the other parameter, the other code path); would each test fail without the change it guards
(not pass on state an earlier check left, a value already there, or a comparison any rule satisfies); does every test
clean up on failure too; did the change weaken an older test; does any comment, docstring or doc say more than the code
and tests show? Fix what you find and look again, until a fresh look finds nothing a reviewer could report.

**Reviews go in REVIEW.md** (repo root, committed with the changes it records). Three skills: `project-code-review`
(`.claude/skills/project-code-review/`) for reviewing, its `TEMPLATE.md` the format; `address-review`
(`.claude/skills/address-review/`) for fixing or answering findings test first and checking them off; `cleanup-review`
(`.claude/skills/cleanup-review/`) for a cleanup the user asks for. REVIEW.md is the memory per branch: reviewers and
the agents addressing findings talk through it, as in a PR review, and it can be cleaned up once the branch is merged,
its history staying in git. DECISIONS.md is the memory for the whole project. The rules:

- Five sections by severity, from high to low: High, Medium-high, Medium, Low-medium, Low.
- Each finding is one entry starting with a checkbox: unchecked while open, checked once fixed or answered (not a bug,
  not reproducible, won't fix), with a resolution line giving the evidence, and no commit hash (branches are squashed
  into main).
- A new review **appends** its findings to the sections they belong in, plus an entry in the review log; it never
  replaces or rewrites what is there. A finding's number comes from the **Last used** line in the header, updated in
  the same edit.
- Only the user starts a cleanup of REVIEW.md, by asking for one explicitly; agents never truncate it on their own. A
  removed finding stays findable in git: `python3 scripts/review_lookup.py <ID>`.

### Running the tests

**Only the agent that changes the code runs tests.** A review runs none, unit or live (the `project-code-review` skill
or the built-in `/code-review`): reviewers read the code and the tests and report what reading can't settle as a
suspicion, with what would settle it; the agent leading the review settles each before anything is recorded, with
scratch probes of its own, one at a time in one Designer an agent started (the `project-code-review` skill).

**The full suites run only when the user asks:** the whole unit suite (`pytest` with no test ids) and a whole run of the
live self-test (`tests/test_all_tools`). Never start one on your own: not for TDD, not after a fix, not between
reviews. When a review finds nothing, tell the user the work is ready for the final check: both suites in full, run when
the user says the work is done, just before merging into `main`; both must pass (DECISIONS.md, Project rules).

**Unit tests while working:** only those added or modified for the change (for a refactor, the existing tests of the
code it touches), as often as useful. **Lint and types always run too** (about 10 s):
`mcp_server/venv/bin/python -m pytest <test ids> tests/unit/test_lint.py tests/unit/test_types.py`, the test ids files
or single tests (`tests/unit/test_x.py::test_name`). Docs changed alone (Markdown files, the skills included), in a
commit or a whole branch, run only the tests that validate the docs, the final check included, with
`tests/unit/test_lint.py tests/unit/test_types.py` added as always:
`mcp_server/venv/bin/python -m pytest tests/unit/test_constants.py tests/unit/test_guide.py tests/unit/test_review_lookup.py tests/unit/test_server.py`
(`test_review_lookup.py` fails if a test that reads a doc is missing from this command).

**Live checks while working: a scratch run.** A new or changed check is seen failing, then passing, on its own in an
environment built for it, never through a run of the whole suite. **The check lives in the suite:** a function
`async def check_<what>(ctx: Ctx)` of its category's module, awaited by the category's `run(ctx)`; a scratch run calls
that same function, never a copy, so the check seen failing is the one committed. A check being changed moves into
such a function first (`tests/unit/test_selftest_summary.py` fails on a `check_` function its module never awaits).

**Use `alone.run`** (`tests/test_all_tools/alone.py`; its docstring has the details) from a few-line script in the
session's scratchpad, deleted afterwards, never committed:

```python
import sys

sys.path.insert(0, '<repo>/tests')
from test_all_tools import alone, params

# the check being worked on, params.check_<what>; a whole category (params.run) works too
raise SystemExit(alone.run(params.run, needs=['graph']))
```

It opens a fresh MCP server (the session's own tools run the server as it was when the session connected: they don't
see a change to `server_tools/` or the helpers until `/mcp` reconnects), uses a Designer an agent started or starts
one, and refuses the user's (ask them to close it). It builds the environment with the suite's own setup steps
(`needs`: `graph`, `params`, `wired`, `png`, `sbs`, each with those it relies on), then your `setup(ctx)` if the check
needs more (graphs named starting `mcp_selftest`: the clean-up unloads every package holding one), calls the checks and
cleans up. It keeps that Designer open for the next runs; `alone.close()` ends it. `port=` (`run` and `close`) runs on
a port and Designer of its own (server, `raw_request`, `sd_run`, snapshots too), so runs go side by side. Exit code: 0
every check passed, 1 a check failed, 2 no environment (the user's Designer, a launch or a setup that failed) or no
clean-up. A plugin change needs `install.py` and a restart of that Designer first (`alone.close()`, then the next run
starts one). If `alone.run` can't do what a check needs, ask the user to improve it, saying what is missing, and
meanwhile write the script from zero doing what it does: the check function itself; a fresh MCP session,
`stdio_client(common.PARAMS)` as `__main__.py` does; `get_guide` first; a Designer an agent started; graphs named
starting `mcp_selftest`, removed in a `finally` (`common.CLEAN`, then the library packages put back with
`common.library_packages` / `common.restore_library_packages`, then the self-test graph's snapshots deleted).

**The order:** run the check before the code; it must fail for the reason it is about. A failure saying only that the
tool or parameter doesn't exist yet is the expected one for something new, but shows nothing about the assertions, so
read such a check closely. A check that passes, or fails for another reason, was written wrong, unless it shows a review
finding is false (the `address-review` skill, step 2): fix it and run again. Then write the code, and run the check
again until it passes. Checks worked on together (a feature in several parts, findings addressed together) run in one
scratch script; a "designer facts" check for Designer behaviour the code relies on is written and run the same way. A
scratch run proves a check in its own environment, not after the earlier categories of the suite have changed the graph:
only the full run shows that. A refactor of code the self-test reaches (the helpers, the plugin, the Designer scripts)
gets a scratch run of the checks of the code it touches, before and after. A new check in a setup step's category
(`graph_edit.create`, `params`, `graph_edit.wire`, `bitmaps`, `save`) runs inside every need built on that step: while
it still fails, those needs fail to build (exit code 2), so the other checks run on them aren't seen failing for their
own reason. Run such a check on the needs before its category, and the rest of the group in a script of its own.

**What a scratch run can't prove** (only the full suite runs these; changing one, say so rather than claiming it was
seen failing and passing):

- **`lifecycle.py`, the whole category:** it quits and relaunches Designer (a normal quit, a forced one, a stuck
  shutdown, a frozen main thread, a slow quit), checks for crash dumps after each, and checks the record of the Designer
  an agent started; a quit ends the session a scratch run keeps open. Three of its checks end only a Designer they
  started, so they do run alone: `check_launch_on_another_port`, `check_launch_refuses_a_port_another_program_holds`
  (it refuses at once and quits only a Designer it started), and `check_a_designer_sharing_the_temp_folder_hands_over`
  (it skips unless the run's Designer was the last one started: run it first).
- **`__main__.py` at the start of the run:** the four `get_guide` checks (instructions' length, the reminder before and
  after it is called, the whole guide returned), whether Designer was started or already running, and the Home screen
  check (no panel visible while it shows), measurable only right after a fresh start, since Home can't be shown again
  once closed.
- **`__main__.py` at the end:** every tool exercised (and which were all skipped), the user's graph back in the editor,
  and, in a Designer that was already running, that it still runs with no new crash dump.

**When the final check fails,** rerun only the failing tests until they pass: unit tests by name (the summary lists
them) with lint and types; a live check in a scratch run (failing only in the suite: build the state the earlier
categories left into its environment). Then tell the user which suites failed; they ask for those again. When only unit
tests failed, the live self-test needs to run again only if the fixes touch code it reaches (`mcp_server/`, `plugin/`,
`client/`, `examples/`, `tests/test_all_tools/`, `project_constants.py`): its pass was for the code as it was, so tell
the user it must run again. Fixes only elsewhere (`tests/unit/`, `install.py`, `uninstall.py`, `scripts/`, the tool
configs) need only the unit suite again.

**The suites.**

- `mcp_server/venv/bin/python -m pytest`: unit tests, no Designer, about a minute (`pip install -r
  mcp_server/requirements-dev.txt` once). `test_types.py` runs mypy strict (`mypy.ini`) over every Python file:
  annotate everything. The helpers, the plugin and the example are checked against Designer's own `sd` package and
  PySide6 stubs (found in the Designer install) and run on Designer's Python 3.13, which evaluates annotations when a
  `def` runs: every name in an annotation there must exist at runtime (import real types, `from sd.api.sdnode import
  SDNode`, never only under `if TYPE_CHECKING:`), and no `from __future__ import annotations` (the helpers are joined
  into one script, where it can't come first). The standalone scripts (`install.py`, `uninstall.py`,
  `client/sd_run.py`, `scripts/review_lookup.py`) are the opposite: they run on the system Python, maybe 3.9, so they
  do start with `from __future__ import annotations` and evaluate no `X | None` at module level
  (`tests/unit/test_old_python.py` runs them on an older Python when one is installed). `sd`'s modules star-import each
  other in cycles, so in the whole-repo run some sd return types come out `Any` (`no-any-return`): annotate the local
  (`node: SDNode = g.newNode(...)`). `test_lint.py` runs Ruff (`ruff.toml`), `ruff check` and `ruff format --check`: after editing, run
  `mcp_server/venv/bin/ruff check --fix .` and `mcp_server/venv/bin/ruff format .`. The formatter can move a trailing
  `# type: ignore` or `# noqa` off its line when it rewraps a statement (mypy then reports it): put it back. Tests that
  read source text match whitespace-tolerantly (`c\(\s*'tool'`), as formatting may split a call over lines.
- `mcp_server/venv/bin/python tests/test_all_tools`: every tool over MCP against the real Designer, about 11 minutes
  when it starts Designer itself (PLAN.md, measured). It starts Designer if none runs and closes it again; one already
  running stays open, and the checks that quit Designer are skipped. Its "designer facts" checks re-measure the
  Designer behaviour this file states: add one with each new fact. One module per category (`bridge.py`, `params.py`,
  `render.py`...), shared helpers and snippets in `common.py`, and the index `__main__.py`, which runs the categories in
  its `CATEGORIES` order. They share one graph; what an earlier category made (the graph `G`, node ids, the saved
  `.sbs`) reaches later ones through `ctx`. Add a check to the category it belongs to (a `check_` function, above); a
  new category is a module with an `async def run(ctx)` added to `CATEGORIES`.
  - **Python with real logic that runs inside Designer** (more than a handful of lines, imports and the graph lookup
    included, or Qt code that gains from type checks), or that several modules run, goes in `designer_scripts/<module>/`
    (`shared/` for several), as a real file run with `common.designer_script` (`run_designer_script`, its values in
    `args`), so ruff and mypy check it; a script that raises fails the run. A shorter probe stays inline where the check
    reads it, as do snippets needing the helpers' text (`helpers_source()`: `run_designer_script` doesn't send them),
    strings that are what the test is about (`execute_designer_code`, its undo step and abort, the bridge, the plugin's
    unit tests), and `common.py`'s clean-up and undo snippets, which guard the user's session. The server's own calls
    into the helpers are one-line strings by design. A string of several lines is written `dedent("""...""")`
    (`textwrap`), not joined pieces with `\n` (`tests/unit/test_selftest_safety.py` checks the self-test's and the
    server's modules).
  - A snippet that loads one of Designer's library packages stays inline, in a branch that runs only where the
    self-test started Designer (the `else` of `if was_running:`, or `if not was_running:`), never in a script: the unit
    test can't see a branch in another file, so it fails on a script naming both `loadUserPackage` and
    `DefaultResourcesDir`. (A library path passed in through `ARGS` goes unseen: don't.)

### Keeping the docs current

README.md is for people, AGENTS.md for agents. With every change (a tool, a fix, a workaround, a fact learned about
Designer), add a short note where it belongs, in the same change. Keep each fact in **one** place and link to it
instead of copying it; fix or delete notes that turn out wrong rather than adding a contradicting one. One repeat is
deliberate: the sentence saying what REVIEW.md and DECISIONS.md each remember.

| Kind of knowledge | Where it goes |
|---|---|
| How to use the tools well, workflow, sd API / Designer pitfalls, verified facts | **AGENTS.md**, in the matching section |
| A tool's parameters and behaviour | The tool's **docstring in its module of `mcp_server/server_tools/`**, the single source; don't repeat parameters here |
| Install, configuration, security, troubleshooting, anything a **person** needs | **README.md** |
| Architecture: what the plugin, server, helpers and CLI tools each do | **README.md**, "How it works" |
| How to deploy changes, diagnostics an **agent** needs | **AGENTS.md**, Deploying and diagnosing |
| New or changed tool | Its entry and the tool count in README.md's Tools table, and checks in `tests/test_all_tools/` |
| What is settled for the whole project: the user's won't fix, rule or choice; a not-a-bug or not-reproducible answer the user acknowledged at a cleanup | **DECISIONS.md** (read by the review skills; agents may update its names and paths, anything else takes the user) |
| Work still to do, ideas, follow-ups | **ROADMAP.md** (check an item when done; checked items can be deleted later, git keeps the record) |

Open work lives in [ROADMAP.md](ROADMAP.md): check it before proposing improvements, and add new ideas there.

### Deploying and diagnosing

- **Fresh clone, or a deleted `mcp_server/venv`:** run `python3 install.py` (Windows: `py -3 install.py`) first;
  without the venv the server can't start, and the `.mcp.json` command says so in `/mcp`. Then the user reconnects
  `/mcp`. `designer_status` shows which Python and library versions the server runs on.
- **The helpers** (`mcp_server/designer_helpers/`) are parts joined into one script (README.md, How it works). A part
  imports what it uses from other parts (`from .core import find_graph`), for PyCharm and readers; `part_source()` drops
  those lines. `tests/unit/test_designer_helpers.py` fails on a missing, extra or misplaced import, a name no part
  defines, and a part file not in `PARTS`. Code needing the helpers' text takes it from `designer_helpers.source()`,
  never from one file.
- **PyCharm** (the repo's `.idea` marks `client`, `mcp_server`, `tests` and `tests/unit` as source roots, also
  Designer's own `sd` and PySide6 folders, which the interpreter `mcp_server/venv` lacks: README.md, Working in
  PyCharm): tests patch a module loaded from its file with `monkeypatch.setitem(vars(module), 'NAME', value)`, not
  `setattr` (PyCharm checks that name against the fixture and reports it missing); standard modules are patched
  directly (`time`, not `server.time`).
- **The server** (`mcp_server/server.py`) only starts it and re-exports the names of `mcp_server/server_tools/`, one
  module per area (`core` holds the bridge and the `_tool` decorator; a new module goes into `MODULES` in its
  `__init__.py`). Unit tests replace a name with `patch_server` (`tests/unit/conftest.py`), which patches every module
  binding it: patching `server` alone doesn't reach the tools.
- **How changes reach Designer:** `server.py`, `server_tools/` and `designer_helpers/` changes take effect when the MCP
  server restarts (helpers are re-sent with every call; the user reconnects in `/mcp`, or test with a fresh MCP client
  such as the self-test). **Plugin** changes must be copied into Designer's plugin folder (re-run `install.py`; paths in
  README.md, Install) and need a **Designer restart**: for a Designer an agent started, `quit_designer` then
  `launch_designer` without asking (say that you did); for the user's, ask them to save, close and reopen it.
- **The plugin's name** (`sd_claude_bridge_kve`, also its folder names and the token file
  `~/.sd_claude_bridge_kve_token`) is defined once, in `project_constants.py`; the plugin takes it from its own folder.
  To rename: change `PLUGIN` there, rename both `plugin/<name>` folders, update README.md/AGENTS.md, and add the old name
  to `install.py`'s clean-up of old copies. `tests/unit/test_constants.py` fails on anything missed.
- **Registration is per folder, never global, for now** (README.md, "Where the tools are available"; ROADMAP item 5
  will make global registration the installer's choice): this repo's committed `.mcp.json`, or
  `claude mcp add --scope local` in another folder. The installer never registers; it writes a user skill (`skill_text`
  in `install.py`) telling sessions elsewhere how to register, and `uninstall.py` removes the skill, the plugin, the
  token, every folder's local registration and a user-scope one (only entries running this repo's `server.py`).
  `.mcp.json` must not contain `${`: Claude Code expands those itself (it once rewrote a shell default away), so its
  `sh -c` command uses plain `$VARS` (`tests/unit/test_mcp_json.py`).
- **The bridge protocol** is defined in the plugin's docstring. `server_tools/core.py`, `client/sd_run.py` and the
  self-test's `raw_request` all speak it: change them together with the plugin, and raise `BRIDGE_PROTOCOL`
  (`project_constants.py`) and the plugin's `PROTOCOL` with any change to it.
- Environment variables `SD_DESIGNER_BIN_DIR`, `SD_DESIGNER_APP`, `SD_DESIGNER_LOG`, `SD_SNAPSHOT_DIR`,
  `SD_BRIDGE_PORT`: README.md, Configuration. A port change must reach the plugin (Designer's environment) and the
  server alike.
- **When tools fail:** match the symptom in README.md, Troubleshooting, and try `read_designer_log`. If Designer isn't
  running or answering, ask the user to open it, or to save, close and reopen it (in tests and work on this project,
  `launch_designer`). If the bridge accepts connections but never answers, or a tool is missing in Claude Code, only the
  user can fix it (restart Designer / reconnect `/mcp`): tell them.
