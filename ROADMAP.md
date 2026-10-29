# ROADMAP.md: what's still to do

The road map for perfecting this MCP. It only lists **open** work: when an item is done, delete
it here (git history keeps the record) and document the result as AGENTS.md describes. Effort is
a rough guess: S = under an hour, M = a few hours, L = a day or more.

## Next

| # | Item | Why | Approach | Effort |
|---|---|---|---|---|
| 1 | **Better cancel for long computations** | Timeouts and `cancel_designer_job` can't interrupt one long C++ call such as a huge `graph.compute()` | Try Designer's own Tools > **Cancel rendering** (Esc) action from the plugin's network thread, or via a queued Qt call, when a cancel arrives during a compute; verify it really aborts the compute | M |
| 2 | **`export_for_blender`**: maps plus a small manifest | One-step hand-off of a material to Blender (with the Blender MCP) | Export outputs, then write a JSON with each map's role, colour space, bit depth and normal convention (OpenGL), plus the graph's size | S |
| 3 | **Upgrade the example script** | `examples/build_dwarf_trimsheet.py` predates the layout tools: its graph is cramped, fixed-size and has no frames or portals | After building: `arrange_graph`-style layout per strip, a frame per strip, portals for the shared gradient and long links, overridable size | M |

## Later

| # | Item | Why | Approach | Effort |
|---|---|---|---|---|
| 4 | **3D view control** | `screenshot_designer('3d')` shows whatever is displayed; checking a material on a plane or sphere needs the user | Drive the 3D View's Scene and Materials menus the same way the screenshot drives Camera > Copy Render (lazy menus, keep references); pick a mesh, assign a graph's outputs | M |
| 5 | **Portals without a reload** | `set_link_display` must save, edit the file and reload, which resets the package's undo history | Look for an in-app path: the graph view's link items or context-menu actions (Qt), or an undocumented API property; fall back to the file edit | M |
| 6 | **Designer crash on reopen after a reload** | Once in about ten self-test runs (2026-10-29), Designer crashed in its own code as `set_link_display` reopened the graph after reloading the package (crash dump in Designer's Sentry-Crashpad folder; the log's last line was the graph view opening) | Let the reload settle longer before reopening (process events, wait for the package to be loaded), or reopen only on request; run the portal steps in a loop to measure the crash rate before and after | M |
| 7 | **Function graph / Pixel Processor editing** | Custom maths inside materials currently needs hand-written scripts | Tools to create function graphs on parameters or in Pixel Processors: add function nodes, connect, set constants, set the output node (the `expose_param` code already builds a minimal function graph) | L |
| 8 | **Slider ranges for atomic nodes** | `describe_node` shows ranges only for library nodes; the API exposes none for the 29 atomic nodes | Curate a small table of sensible ranges for the commonly used atomic parameters (levels, blend opacity, warp intensity, blur, normal intensity...), clearly marked as recommendations | S |
| 9 | **3D view inside window screenshots** | In `screenshot_designer('window')` the 3D area is black | Composite the `3d` render into the window capture at the 3D dock's position | S |
| 10 | **Large-graph output limits** | `diff_graph` on very large graphs can return very long text (`describe_graph` already has `limit`) | `offset` paging for `describe_graph`, a line limit and per-section summary for `diff_graph` | S |
| 11 | **Edge-local tiling metric** | `check_tiling` compares the seam with the *average* step over the whole image, so a seamless pattern whose steepest part sits on the edge scores too high (a sine: ratio 1.58, "probably fine") | Compare the seam with the steps right next to it (columns 0→1 and W-2→W-1, per row), keep the global ratio as a fallback; update the unit test in `tests/unit/test_pixels.py` | S |
| 12 | **Untested corners from the code review** | Fixed or reviewed, but not checkable live yet | `search_nodes` while a function graph is open in the editor (the atomic list is cached per session, so a live test needs a fresh server); the plugin's `stop()` closing the socket while `accept()` waits (may keep the port busy after disabling the plugin in Plugin Manager; untested); `quit_designer` when the bridge is dead but Designer still runs (unit-tested only) | S |

## Needs the user or other machines

| # | Item | Why | What's needed |
|---|---|---|---|
| 13 | **Test on Windows** | Paths, installer, log location and plugin folder are written for Windows but untested; so are the exclusive port binding (`SO_EXCLUSIVEADDRUSE`), the `tasklist` CSV check, the installer running `claude.cmd`, and reading `.sbsar` archives with Windows' `tar` | Someone with Windows and Designer runs `install.py` and the self-test, and reports the failures |
| 14 | **Test on other Designer versions** | Only Designer 16.0.7 is tested; 15.x reportedly hangs on unknown node ids, which the server already guards against | Run the self-test on Designer 14.x / 15.x and note differences in AGENTS.md |
| 15 | **Releases** | Users currently clone `main` | Version numbers, a CHANGELOG, tagged GitHub releases; maybe a one-line install command |

## Ideas, not yet decided

- A `material_report` tool: one call that renders all outputs, checks tiling, value ranges and
  normal convention, and summarises problems.
- Snapshot housekeeping: `prune_snapshots` (keep the last N per graph).
- A `get_selection` tool: what the user has selected in the graph, so "this node" works naturally.
