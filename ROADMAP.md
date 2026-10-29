# ROADMAP.md: what's still to do

The road map for perfecting this MCP. It only lists **open** work: when an item is done, delete
it here (git history keeps the record) and document the result as AGENTS.md describes. Effort is
a rough guess: S = under an hour, M = a few hours, L = a day or more.

## Next

| # | Item | Why | Approach | Effort |
|---|---|---|---|---|
| 1 | **`compare_to_reference`**: compare a node's output with a reference image | Match a reference's tones and value distribution with numbers instead of by eye (for example the dwarf house reference) | Load the image server-side, resize to the node's size, report per-channel mean/std differences, histogram distance and an optional difference image; reuse the raw pixel path from `node_stats` | M |
| 2 | **`import_bitmap`**: bring an image file into a graph as a node | Use references, masks or hand-painted textures in graphs | `SDResourceBitmap.sNewFromFile(pkg, path, EmbedMethod.Linked)` plus `graph.newInstanceNode(resource)` (see Designer's `sample_sbs_graph.py`); option to embed instead of link | S |
| 3 | **Tests that run without Designer** (GitHub Actions) | Catch breakage on every push of the public repo, even without Designer | Unit tests for pixel decoding (`_decode_pixels`), `.sbs` parsing and diffing (`_graph_model`, `_diff_models`), the tiling metric, `_default_parent_log2`, search ranking, and that `server.py` starts and lists all tools; fixtures are small hand-made `.sbs` files | S–M |
| 4 | **Better cancel for long computations** | Timeouts and `cancel_designer_job` can't interrupt one long C++ call such as a huge `graph.compute()` | Try Designer's own Tools > **Cancel rendering** (Esc) action from the plugin's network thread, or via a queued Qt call, when a cancel arrives during a compute; verify it really aborts the compute | M |
| 5 | **`export_for_blender`**: maps plus a small manifest | One-step hand-off of a material to Blender (with the Blender MCP) | Export outputs, then write a JSON with each map's role, colour space, bit depth and normal convention (OpenGL), plus the graph's size | S |
| 6 | **Upgrade the example script** | `examples/build_dwarf_trimsheet.py` predates the layout tools: its graph is cramped, fixed-size and has no frames or portals | After building: `arrange_graph`-style layout per strip, a frame per strip, portals for the shared gradient and long links, overridable size | M |

## Later

| # | Item | Why | Approach | Effort |
|---|---|---|---|---|
| 7 | **Smaller always-loaded instructions** | AGENTS.md (~19 KB, about 4,700 tokens) is loaded into every session that uses this server | Keep the essentials (rules, which tool when, top pitfalls) in the instructions and move reference detail behind a `get_guide(topic)` tool or the existing resource. Trade-off: the agent must remember to look things up | M |
| 8 | **3D view control** | `screenshot_designer('3d')` shows whatever is displayed; checking a material on a plane or sphere needs the user | Drive the 3D View's Scene and Materials menus the same way the screenshot drives Camera > Copy Render (lazy menus, keep references); pick a mesh, assign a graph's outputs | M |
| 9 | **Portals without a reload** | `set_link_display` must save, edit the file and reload, which resets the package's undo history | Look for an in-app path: the graph view's link items or context-menu actions (Qt), or an undocumented API property; fall back to the file edit | M |
| 10 | **Function graph / Pixel Processor editing** | Custom maths inside materials currently needs hand-written scripts | Tools to create function graphs on parameters or in Pixel Processors: add function nodes, connect, set constants, set the output node (the `expose_param` code already builds a minimal function graph) | L |
| 11 | **Slider ranges for atomic nodes** | `describe_node` shows ranges only for library nodes; the API exposes none for the 29 atomic nodes | Curate a small table of sensible ranges for the commonly used atomic parameters (levels, blend opacity, warp intensity, blur, normal intensity...), clearly marked as recommendations | S |
| 12 | **3D view inside window screenshots** | In `screenshot_designer('window')` the 3D area is black | Composite the `3d` render into the window capture at the 3D dock's position | S |
| 13 | **Self-test: undo check** | Undo grouping was verified by hand; the self-test skips it because Undo acts on the focused document | Run the check only when no user graph is open in the editor (detect it first), otherwise report it as skipped | S |
| 14 | **Large-graph output limits** | `describe_graph` / `diff_graph` on very large graphs can return very long text | Paging (`offset` / `limit`) and per-section summaries | S |

## Needs the user or other machines

| # | Item | Why | What's needed |
|---|---|---|---|
| 15 | **Test on Windows** | Paths, installer, log location and plugin folder are written for Windows but untested | Someone with Windows and Designer runs `install.py` and the self-test, and reports the failures |
| 16 | **Test on other Designer versions** | Only Designer 16.0.7 is tested; 15.x reportedly hangs on unknown node ids, which the server already guards against | Run the self-test on Designer 14.x / 15.x and note differences in AGENTS.md |
| 17 | **Releases** | Users currently clone `main` | Version numbers, a CHANGELOG, tagged GitHub releases; maybe a one-line install command |

## Ideas, not yet decided

- A `material_report` tool: one call that renders all outputs, checks tiling, value ranges and
  normal convention, and summarises problems.
- Snapshot housekeeping: `prune_snapshots` (keep the last N per graph).
- A `get_selection` tool: what the user has selected in the graph, so "this node" works naturally.
