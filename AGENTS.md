# AGENTS.md: notes for AI agents driving Substance Designer

You have access to the user's **running** Substance 3D Designer through the
`substance-designer` MCP server. These notes were learned the hard way. Read them before
writing `sd` scripts.

## Tools

| Tool | Use |
|---|---|
| `designer_status` | Bridge state (idle / running Ns), Designer version, open user packages/graphs. Call first. |
| `cancel_designer_job` | Abort the running script (and drop queued ones). |
| `launch_designer(wait_s=180)` | Start Designer if needed and wait until the bridge answers. |
| `screenshot_designer(panel='window')` | Image of Designer's own UI: `window`, `graph`, `2d`, `3d`, `explorer`, `parameters`, `library`, `console`. Use it to see the node layout, the 2D view, the properties, and (`3d`) the material on the 3D mesh. |
| `search_nodes(query)` | Find node types by name/label/category/description across the 29 atomic nodes and Designer's **whole** library (not just loaded packages); returns the exact `definition` for `add_node`/`describe_node`. Use it instead of guessing file names. |
| `open_graph(graph, node_id?)` | Open a graph in Designer's editor (what the user and `screenshot_designer` see), optionally centring the view on a node. |
| `create_graph(name, save_path?, size_log2=11)` | New package with one empty graph. |
| `move_nodes({id: [x, y]})` | Reposition nodes. |
| `describe_node(definition)` | Connectors, parameter ids/types/labels/defaults and **enum values** of a node type: atomic (`levels`, `blend`) or library (`tile_generator`, `hbao.sbs/hbao`). Use it before setting parameters instead of guessing. |
| `describe_graph(graph?, node_ids?, include_params?)` | Nodes with ids, types, positions and incoming links (`input<-srcId.output`); non-default params on request. `graph` defaults to the graph open in the UI. |
| `preview_node(node_id, graph?, output?, max_size?)` | Computes the graph and returns the image of **any** node, the main debugging tool for intermediate steps. Works for nodes that don't feed an output (it attaches a temporary output node and removes it again, inside one undo step). |
| `add_node(definition, graph?, position?, params?)` | Add an atomic or library node and return its id; optional initial params. |
| `set_params(node_id, params, graph?)` | Set parameters with automatic type conversion: numbers, bools, lists for vectors/colours, enums by id or number (`'max'` or `5`). `node_id='graph'` targets graph parameters such as `$outputsize`. Prints old -> new. |
| `connect(from_node, to_node, to_input, from_output?, graph?)` | Link an output to an input connector (replaces an existing link). |
| `disconnect(node_id, input_id, graph?)` / `delete_nodes(node_ids, graph?)` | Remove links / nodes. |
| `execute_designer_code(code, undo_label?, timeout_s=120)` | Run Python inside Designer; `print()` output and tracebacks come back. Aborted after `timeout_s` (0 = no limit). |
| `run_designer_script(path, timeout_s=600)` | Same, for a file (`__file__` is set). Prefer this for anything long, so the script lives on disk. |
| `sbsar_info(sbs_path)` | Graph URLs, exposed inputs (with types) and outputs of a `.sbs`/`.sbsar`. |
| `render_sbs(sbs_path, output_dir, size_log2?, graph?, outputs?, params?, output_format?)` | `sbscooker` → `.sbsar` → `sbsrender`. One file per output, named after the output's identifier. `params` sets exposed inputs (`{"wear": 0.5, "tint": [1, 0.8, 0.6]}`); `output_format` png/exr/tga/jpg… Reports only the files this render wrote. |
| `save_package(graph_or_path?, save_as?)` | Save an open package (by graph identifier or file path), optionally to a new path. |
| `export_outputs(graph, output_dir, outputs?, file_format='png')` | Compute in Designer and save output textures named after the outputs. Uses the live, unsaved state; no cook step. Pixel-identical to `render_sbs`. |
| `preview_maps(map_dir, names?, tile_size?, crop?)` | Side-by-side image of rendered maps; use `crop=[x0,y0,x1,y1]` to inspect details. |

Each `execute_designer_code` / `run_designer_script` call is wrapped in one Designer undo
transaction (`SDHistoryUtils.UndoGroup`), so the user can revert a whole run with Ctrl+Z
(verified: a run adding 3 nodes is removed by one Undo and restored by one Redo).
Undo history is **per document**: Edit > Undo (and the user's Ctrl+Z) reverts the last step
of the graph/package in focus, so a run on a graph that isn't focused is undone from that
graph's own history. If you ever need to trigger Undo/Redo yourself, the actions live in a
`QMenu` (find them through `QApplication.instance().allWidgets()`, not
`mainWindow.findChildren`). They apply **asynchronously**, so call
`QApplication.processEvents()` before reading the result. **Never trigger Undo while one of
the user's graphs is open in the editor**, because it will hit their document. (It happened
once; an immediate Redo restored it, which a full diff against the saved file confirmed.)
These notes are also served as the MCP server's instructions and as resource
`designer://agents-guide`.

Timeouts and cancel use a trace hook inside the plugin: the abort happens the next time
Python code runs, so a single long C++ call (one huge `graph.compute()`) completes first.
A script that catches `BaseException` can swallow the abort, so don't do that.

**Never hot-reload the sd_bridge plugin** (`importlib.reload` from inside Designer). The
running server keeps references to the old module, and reloading under it breaks the
bridge until Designer restarts. Plugin changes need a Designer restart.

**Self-test:** `mcp_server/venv/bin/python tests/test_all_tools.py` exercises all tools over
MCP on a temporary graph (exit 0 = all passed). Run it after changing the server, plugin or
helpers, and extend it when you add a tool.

Fallback without MCP: `python client/sd_run.py script.py [--timeout N]`, plus
`--status` and `--cancel` (no undo grouping).

**Loop:** `describe_node` for unfamiliar nodes → write/modify script → `run_designer_script`
→ `describe_graph` + `preview_node` to check intermediate nodes → `render_sbs` →
`preview_maps` → check the numbers too (sample pixels) → fix → repeat. Look at the
result before telling the user something works.

## Environment facts

- No `pysbs` (the Automation Toolkit is enterprise-licensed). Everything goes through the
  in-app `sd` API via the bridge, plus `sbscooker`/`sbsrender`.
- The code runs on Designer's main thread, so the UI freezes while a script runs. Keep scripts finite.
- Library graphs are `.sbs` files in
  `app.getPath(SDApplicationPath.DefaultResourcesDir)/packages`. Load them with
  `pkgMgr.loadUserPackage(path)` (check `getPackages()` first to reuse one that's already
  open), then `pkg.findResourceFromUrl('<graph id>')` and `graph.newInstanceNode(resource)`.
- To discover a library node's parameter and output ids, parse its `.sbs` XML: look for
  `<paraminput><identifier v=...>` and `<graphoutput>`. Image inputs show up as params of type 1/2.
- The Designer log has every Python traceback from plugins:
  macOS `~/Library/Application Support/Adobe/Adobe Substance 3D Designer/<ver>/log.txt`.

## sd API gotchas

- **`sd.api.apiexception.APIException` derives from `BaseException`, not `Exception`.**
  `except Exception` will NOT catch it. Use `except (Exception, APIException)`.
- Atomic nodes: `graph.newNode('sbs::compositing::<name>')`. Output connector id is
  `unique_filter_output`. Common inputs: `input1` (levels, blur, normal, warp,
  directionalwarp, transformation…), blend `source` / `destination` / `opacity`,
  warp `inputgradient`, directionalwarp `inputintensity`, output node `inputNodeOutput`.
- Instance (library) nodes: input/output ids equal the library graph's identifiers
  (e.g. bevel: in `input`, outs `height`/`normal`; tile_generator: out `TileGenerator`).
- Property types matter. Check `node.getPropertyFromId(id, SDPropertyCategory.Input).getType()`:
  - levels `levelinlow/high/mid`, `leveloutlow/high` are **float4** (`SDValueFloat4`).
  - uniform `outputcolor` is **ColorRGBA** (`SDValueColorRGBA`).
  - `blendingmode`, `$format`, `$tiling` are **enums** (`SDTypeEnum`). Set them with an
    enumerator's `getDefaultValue()` or `SDValueEnum.sFromValueId(type, id)`.
- `$format` enum ids: `8_bits_per_channel`, `16_bits_per_channel`, `hdr_low_precision`,
  `hdr_high_precision` (type id `sbs::compositing::format`).
- Blend modes: copy 0, add 1, subtract 2, multiply 3, addsub 4, max 5, min 6,
  switch 7, divide 8, overlay 9, screen 10, softlight 11.
- Graph size: `graph.setInputPropertyValueFromId('$outputsize', SDValueInt2.sNew(int2(11, 11)))`
  (log2, so 11 = 2048). Generators inherit it; filters inherit from their input.
- Output node usage: set annotation `usages` to an `SDValueArray` of
  `SDValueUsage.sNew(SDUsage.sNew('baseColor', 'RGBA', 'sRGB'))`, and annotations
  `identifier` / `label` with `SDValueString`. The identifier becomes the render's file name.
- **Connections are reported from the queried node's side:** for `c` in
  `node.getPropertyConnections(prop)`, `c.getOutputPropertyNode()` / `getOutputProperty()` is
  `node`/`prop` itself, and `c.getInputPropertyNode()` / `getInputProperty()` is the **other**
  node, whatever direction the data flows.
- `graph.compute()` only computes nodes that feed an **output node**; others have no texture.
- Computing in-app: `graph.compute()` (about 1 s for a 190-node 2048² graph), then
  `node.getPropertyValue(outputProp).get()` is an `SDTexture`; `.save(path)` writes PNG.
- Current UI graph: `sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()`.
- Editor control lives on **`app.getUIMgr()`** (not the Qt UI manager): `openResourceInEditor(graph)`,
  `focusGraphNode(graphViewID, node)` (view ids via `getGraphViewIDCount/At`,
  `getGraphFromGraphViewID`), `getGraphNodeBBox`, `setExplorerSelection`.
- Valid atomic node ids: `graph.getNodeDefinitions()` (29 in Designer 16). Check an id is in that
  set **before** `graph.newNode(id)`, because an unknown id reportedly hangs Designer 15 (16 raises).
- Don't trust third-party node references for enum values. One public SD MCP's docs list blend
  mode 4 = Max / 5 = Min / 6 = Difference, but the real values are 4 addsub, 5 max, 6 min,
  7 switch (no Difference). Always read enums with `describe_node`.
- `pkgMgr.savePackageAs()` doesn't reliably leave the package reporting that file path. To
  close earlier builds, unload every user package containing your graph identifier instead
  of using `getUserPackageFromFilePath`.

## Library node facts (Designer 16)

- `gradient_linear_1` with `rotation` 0: value **1.0 at the top row, 0.0 at the bottom**,
  constant across x. Combined with levels, this makes a vertical coordinate, which is useful
  for building per-row height profiles (bands, chamfers) for trim sheets.
- `tile_generator`: `Nb_X`, `Nb_Y`, `Pattern_Type` (2 = square, 1 = image input, 9 = brick
  default), `Scale`, `Offset` (row offset), `Offset_Random`, `Offset_Random_Seed`,
  `Free_Rotation` (degrees), `Luminance_Variation-Contrast` (float2: random luminance per
  tile, contrast). Use the same seed/layout twice to get a matching per-tile random mask.
- `bevel`: `distance` (~0.02–0.08 for small chamfers), `smoothing`; out `height`.
- `hbao`: in `input`, out `output`. `curvature_smooth`: in `input` (normal), out `height`.
- `noise_anisotropic_noise`: default streaks run horizontally (`X_Amount`, `Y_Amount`).
- Atomic `warp` intensity is strong: ~0.05–0.1 gives a gentle wave, and 1.5 destroys the pattern.
- Atomic `normal`: `inversedy=True` gives **OpenGL** normals (Blender). Verified on a raised
  band: the top chamfer's green is > 0.5.

## Rendering / verifying

- Screenshots use `QWidget.grab()` on Designer's widgets. **Never use `QScreen.grabWindow`**,
  not even with Designer's own window id: on macOS both copy the screen area, so they capture
  whatever covers Designer (the user's other apps). Widget capture can't read the GPU-drawn
  3D view (it comes out black), so `3d` triggers the 3D view's own **Camera > Copy Render to
  Clipboard**, reads the image, and restores the user's clipboard in a `finally` (verified
  with Unicode text). Its menus are filled lazily: emit `menu.aboutToShow`, and keep Python
  references to the actions and menus, or the wrappers go stale ("Internal C++ object already
  deleted"). Never use the 3D view's "Save Render...", which opens a modal file dialog that
  blocks the bridge.
- Dock titles change with content ("dwarf_trimsheet", "Blend"). Find panels by object name:
  `areaA_` explorer, `areaB_` graph, `areaC_` parameters, `areaD_` 3D view, `areaE_` 2D view,
  `areaF_` console, `areaG_` library.

- `sbsrender --set-value` **silently ignores inputs the .sbsar doesn't expose**, `$outputsize`
  included. A graph whose `$outputsize` inheritance is set to Absolute (as the trim sheet
  example does) always renders at its fixed size. `render_sbs` now warns about this and
  prints each file's dimensions, so read the warnings and check the sizes.

- Renders are 16-bit PNGs (`I;16`). Normalise by 65535 when sampling with PIL/numpy.
- Verify orientation and convention numerically (sample known pixels), not just visually.

## Example

`examples/build_dwarf_trimsheet.py` is a complete config-driven generator for a 2048² stone + wood
trim sheet (11 horizontal strips, tileable in U), outputting baseColor, normal (OpenGL),
roughness, metallic, height and AO. It's a good template for band and tile helpers,
type-safe parameter setting, and rebuild-safe package handling.
