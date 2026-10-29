# ROADMAP.md: what's still to do

The road map for perfecting this MCP. It only lists **open** work: when an item is done, delete
it here (git history keeps the record) and document the result as AGENTS.md describes. Effort is
a rough guess: S = under an hour, M = a few hours, L = a day or more.

## Next

| # | Item | Why | Approach | Effort |
|---|---|---|---|---|
| 1 | **Cheaper screenshots** | `screenshot_designer` is the costliest tool by far: at `max_size=1800` each call costs tens of thousands of tokens (about 306k, 31% of a 1M context, for under ten calls in one session) | A smaller default `max_size`; a `crop` region; JPEG instead of PNG (`quality`); a graph capture without the dock's toolbars; say the cost in the docstring | S |
| 2 | **Zoom the graph view to a region** | `open_graph` either fits the whole graph or centres on one node at full zoom, so looking at one section needed raw Qt (`QGraphicsView.fitInView` on the graph dock's view; scene coordinates are graph units) | `open_graph(fit=...)` taking a frame title, a list of node ids or a rectangle; with a little padding, so a following screenshot shows a readable section | S |
| 3 | **`compare_maps`** | Checking that a change didn't alter the output took ad-hoc numpy scripts each time; and parallel renders aren't bit-identical (see below), so a byte comparison is useless | Compare two folders of maps (or two renders): per map the largest difference, how many pixels differ, the mean, in 1/65535 and in 8-bit steps; a pass/fail `tolerance`; an amplified difference image to look at | S |
| 4 | **Engine and core options for `render_sbs`** | Comparing CPU and GPU, or rendering bit-exactly, needed `sbsrender` by hand | `engine` (`neon`/`sse2` CPU, `mtl`/`ogl3`/`vk`/`d3d11` GPU) and `cpu_count` parameters, passed through as `--engine` / `--cpu-count` | S |
| 5 | **Better cancel for long computations** | Timeouts and `cancel_designer_job` can't interrupt one long C++ call such as a huge `graph.compute()` | Try Designer's own Tools > **Cancel rendering** (Esc) action from the plugin's network thread, or via a queued Qt call, when a cancel arrives during a compute; verify it really aborts the compute | M |
| 6 | **`export_for_blender`**: maps plus a small manifest | One-step hand-off of a material to Blender (with the Blender MCP) | Export outputs, then write a JSON with each map's role, colour space, bit depth and normal convention (OpenGL), plus the graph's size | S |

## Later

| # | Item | Why | Approach | Effort |
|---|---|---|---|---|
| 7 | **3D view control** | `screenshot_designer('3d')` shows whatever is displayed; checking a material on a plane or sphere needs the user | Drive the 3D View's Scene and Materials menus the same way the screenshot drives Camera > Copy Render (lazy menus, keep references); pick a mesh, assign a graph's outputs | M |
| 8 | **Portals without a reload** | `set_link_display` must save, edit the file and reload, which resets the package's undo history | Look for an in-app path: the graph view's link items or context-menu actions (Qt), or an undocumented API property; fall back to the file edit | M |
| 9 | **Function graph / Pixel Processor editing** | Custom maths inside materials currently needs hand-written scripts | Tools to create function graphs on parameters or in Pixel Processors: add function nodes, connect, set constants, set the output node (the `expose_param` code already builds a minimal function graph) | L |
| 10 | **Slider ranges for atomic nodes** | `describe_node` shows ranges only for library nodes; the API exposes none for the 29 atomic nodes | Curate a small table of sensible ranges for the commonly used atomic parameters (levels, blend opacity, warp intensity, blur, normal intensity...), clearly marked as recommendations | S |
| 11 | **3D view inside window screenshots** | In `screenshot_designer('window')` the 3D area is black | Composite the `3d` render into the window capture at the 3D dock's position | S |
| 12 | **Large-graph output limits** | `diff_graph` on very large graphs can return very long text (`describe_graph` already has `limit`) | `offset` paging for `describe_graph`, a line limit and per-section summary for `diff_graph` | S |
| 13 | **Edge-local tiling metric** | `check_tiling` compares the seam with the *average* step over the whole image, so a seamless pattern whose steepest part sits on the edge scores too high (a sine: ratio 1.58, "probably fine") | Compare the seam with the steps right next to it (columns 0→1 and W-2→W-1, per row), keep the global ratio as a fallback; update the unit test in `tests/unit/test_pixels.py` | S |
| 14 | **Untested corners from the code review** | Fixed or reviewed, but not checkable live yet | `search_nodes` while a function graph is open in the editor (the atomic list is cached per session, so a live test needs a fresh server); the plugin's `stop()` closing the socket while `accept()` waits (may keep the port busy after disabling the plugin in Plugin Manager; untested); `quit_designer` when the bridge is dead but Designer still runs (unit-tested only) | S |
| 15 | **Close a package** | Closing scratch builds needed raw code (`unloadUserPackage`) | `close_package(graph or path)`, refusing a package with unsaved changes unless `discard_unsaved=True`, like `quit_designer`; switch the editor away first if the graph is open | S |
| 16 | **Edit frames and comments** | The tools can add frames and comments but not list them with positions, move, resize, retitle or delete them, so reworking a graph's layout needs code | `describe_graph` lists frames/comments with ids, positions and sizes; `edit_graph_objects` to move, resize, retitle, recolour or delete them (or `apply_edits` ops) | M |
| 17 | **Document render determinism** | Measured, not yet written down: the same .sbsar rendered twice differs slightly whenever it computes in parallel (all CPU cores or the GPU: a few pixels by 1-2/65535, up to ~850 in AO, which amplifies height), while `--engine neon --cpu-count 1` is bit-identical; CPU and GPU engines differ more (AO about 1% on average; strongly warped detail such as the trim sheet's wood grain takes visibly different shapes); node ids play no part | A fact in AGENTS.md (Rendering and verifying) with "designer facts" self-test checks: one file rendered twice on one core is byte-identical, two builds of one graph match on one core | S |

## Needs the user or other machines

| # | Item | Why | What's needed |
|---|---|---|---|
| 18 | **Test on Windows** | Paths, installer, log location and plugin folder are written for Windows but untested; so are the exclusive port binding (`SO_EXCLUSIVEADDRUSE`), the `tasklist` CSV check, the installer running `claude.cmd`, and reading `.sbsar` archives with Windows' `tar` | Someone with Windows and Designer runs `install.py` and the self-test, and reports the failures |
| 19 | **Test on other Designer versions** | Only Designer 16.0.7 is tested; 15.x reportedly hangs on unknown node ids, which the server already guards against | Run the self-test on Designer 14.x / 15.x and note differences in AGENTS.md |
| 20 | **Releases** | Users currently clone `main` | Version numbers, a CHANGELOG, tagged GitHub releases; maybe a one-line install command |

## Ideas, not yet decided

- A `material_report` tool: one call that renders all outputs, checks tiling, value ranges and
  normal convention, and summarises problems.
- Snapshot housekeeping: `prune_snapshots` (keep the last N per graph).
- A `get_selection` tool: what the user has selected in the graph, so "this node" works naturally.
