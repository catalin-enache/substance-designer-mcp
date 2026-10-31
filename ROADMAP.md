# ROADMAP.md: what's still to do

The road map for perfecting this MCP. It only lists **open** work: when an item is done, delete
it here (git history keeps the record) and document the result as AGENTS.md describes. Effort is
a rough guess: S = under an hour, M = a few hours, L = a day or more.

## Next

| # | Item | Why | Approach | Effort |
|---|---|---|---|---|
| 1 | **`compare_maps`** | Checking that a change didn't alter the output took ad-hoc numpy scripts each time; and parallel renders aren't bit-identical (see below), so a byte comparison is useless | Compare two folders of maps (or two renders): per map the largest difference, how many pixels differ, the mean, in 1/65535 and in 8-bit steps; a pass/fail `tolerance`; an amplified difference image to look at | S |
| 2 | **Engine and core options for `render_sbs`** | Comparing CPU and GPU, or rendering bit-exactly, needed `sbsrender` by hand | `engine` (`neon`/`sse2` CPU, `mtl`/`ogl3`/`vk`/`d3d11` GPU) and `cpu_count` parameters, passed through as `--engine` / `--cpu-count` | S |
| 3 | **Better cancel for long computations** | Timeouts and `cancel_designer_job` can't interrupt one long C++ call such as a huge `graph.compute()` | Try Designer's own Tools > **Cancel rendering** (Esc) action from the plugin's network thread, or via a queued Qt call, when a cancel arrives during a compute; verify it really aborts the compute | M |
| 4 | **`export_for_blender`**: maps plus a small manifest | One-step hand-off of a material to Blender (with the Blender MCP) | Export outputs, then write a JSON with each map's role, colour space, bit depth and normal convention (OpenGL), plus the graph's size | S |
| 5 | **`install.py should ask if should install globbaly or not`** |  |  |  |
| 6 | **Review matthieuhuguet/substance-designer-mcp** | Another Substance Designer MCP; its [substance-designer-mcp](https://github.com/matthieuhuguet/substance-designer-mcp/tree/master) may list tools or fixes worth adopting | Read the changelog and code, list features we lack, add the useful ones here as items; verify any facts it states against Designer before relying on them (a public SD MCP's blend-mode table was wrong, see AGENTS.md) | S |

## Later

| # | Item | Why | Approach | Effort |
|---|---|---|---|---|
| 7 | **3D view control** | `screenshot_designer('3d')` shows whatever is displayed; checking a material on a plane or sphere needs the user | Drive the 3D View's Scene and Materials menus the same way the screenshot drives Camera > Copy Render (lazy menus, keep references); pick a mesh, assign a graph's outputs | M |
| 8 | **Portals without a reload** | `set_link_display` must save, edit the file and reload, which resets the package's undo history | Look for an in-app path: the graph view's link items or context-menu actions (Qt), or an undocumented API property; fall back to the file edit | M |
| 9 | **Function graph / Pixel Processor editing** | Custom maths inside materials currently needs hand-written scripts | Tools to create function graphs on parameters or in Pixel Processors: add function nodes, connect, set constants, set the output node (the `expose_param` code already builds a minimal function graph) | L |
| 10 | **Slider ranges for atomic nodes** | `describe_node` shows ranges only for library nodes; the API exposes none for the atomic nodes | Curate a small table of sensible ranges for the commonly used atomic parameters (levels, blend opacity, warp intensity, blur, normal intensity...), clearly marked as recommendations | S |
| 11 | **3D view inside window screenshots** | In `screenshot_designer('window')` the 3D area doesn't show the render (leftover content) | Composite the `3d` render into the window capture at the 3D dock's position | S |
| 12 | **Large-graph output limits** | `diff_graph` on very large graphs can return very long text (`describe_graph` already has `limit`) | `offset` paging for `describe_graph`, a line limit and per-section summary for `diff_graph` | S |
| 13 | **Edge-local tiling metric** | `check_tiling` compares the seam with the *average* step over the whole image, so a seamless pattern whose steepest part sits on the edge scores too high (a sine: ratio 1.58, "probably fine") | Compare the seam with the steps right next to it (columns 0→1 and W-2→W-1, per row), keep the global ratio as a fallback; update the unit test in `tests/unit/test_pixels.py` | S |
| 14 | **Untested corners from the code review** | Fixed or reviewed, but not checkable live yet | `search_nodes` while a function graph is open in the editor (the atomic list is cached per session, so a live test needs a fresh server); the plugin's `stop()` closing the socket while `accept()` waits (may keep the port busy after disabling the plugin in Plugin Manager; untested); `quit_designer` when the bridge is dead but Designer still runs (unit-tested only) | S |
| 15 | **Close a package** | Closing scratch builds needed raw code (`unloadUserPackage`) | `close_package(graph or path)`, refusing a package with unsaved changes unless `discard_unsaved=True`, like `quit_designer`; switch the editor away first if the graph is open | S |
| 16 | **Edit frames and comments** | The tools can add frames and comments but not list them with positions, move, resize, retitle or delete them, so reworking a graph's layout needs code | `describe_graph` lists frames/comments with ids, positions and sizes; `edit_graph_objects` to move, resize, retitle, recolour or delete them (or `apply_edits` ops) | M |
| 17 | **Document render determinism** | Measured, not yet written down: the same .sbsar rendered twice differs slightly whenever it computes in parallel (all CPU cores or the GPU: a few pixels by 1-2/65535, up to ~850 in AO, which amplifies height), while `--engine neon --cpu-count 1` is bit-identical; CPU and GPU engines differ more (AO about 1% on average; strongly warped detail such as the trim sheet's wood grain takes visibly different shapes); node ids play no part | A fact in AGENTS.md (Rendering and verifying) with "designer facts" self-test checks: one file rendered twice on one core is byte-identical, two builds of one graph match on one core | S |
| 21 | **Say what a `$` parameter's inheritance means for a .sbsar** | A graph's `$randomseed` (and `$outputsize`) is a control of the cooked material only while it follows its parent; an Absolute one silently drops the slider in Painter, whether the user or a tool made it so (REVIEW.md HLP-25) | `set_params` and `describe_graph` add a note to the graph's `$randomseed` / `$outputsize`: "follows its parent, so a .sbsar keeps the control" or "fixed: a .sbsar has no control for it"; also check whether typing a seed in Designer's own graph parameters leaves the inheritance alone, as `set_params` now does | S |

## Review hotspots

Areas where REVIEW.md's findings came back round after round: a fix drew a new finding in the same
area, whose fix drew another (chains of 3 to 7 generations; the IDs show each chain). Each item
settles one area for good, the way the address-review skill's step 3 now asks of every fix:
measure the whole case table first, cover every instance of the pattern, test each state once.
Recurring causes: fixes built on guessed Designer behaviour, fixes scoped to the reported instance
only, and each fix adding a test and a doc sentence the next review then audited.

| # | Area | Chain (REVIEW.md) | What kept coming back | Approach | Effort |
|---|---|---|---|---|---|
| 22 | **`$` parameters: inheritance and seeds** (`set_params`, `sweep_param`) | HLP-22 → HLP-24 → HLP-25 → HLP-27 → HLP-29 → TST-57, with TST-37/39/40/44/48/52/53/54/56/58, TST-49, SRV-25: 18 findings, 7 deep | Each round found one more case: the graph's other `$` parameters, the graph's seed, a node's seed, a `.sbsar` render, then the docs and fact checks for each | One "designer facts" probe over the whole table: node and graph × `$outputsize` / `$format` / `$randomseed` × inherited / Absolute × computed in Designer / rendered by sbsrender with and without an override. Put the measured table in AGENTS.md (Graph size) in place of the paragraphs grown one case at a time, and check `set_params` and `sweep_param` against every row. With item 21 | M |
| 23 | **`quit_designer`'s forced-exit fallback** | PLG-8 → HLP-12 → HLP-17 / TST-19 → HLP-19 → TST-25, TST-23; HLP-23 → HLP-28 / TST-32 → TST-36 | Each guard against cutting off a normal shutdown left another timing window, and some couldn't be reached by the checks | Write the states down as a table (a window refusing to close, a slow close handler, a slow `aboutToQuit`, every window closed with the process alive, a window appearing late, a modal dialog) with the expected action and time for each; one unit test per row in `test_quit_fallback.py`; keep the live checks only for what only Designer shows | M |
| 24 | **The installer's plugin folder swap** (`install.py`) | INS-10 → INS-12 → INS-16 → INS-19 / INS-20 / INS-21 | Deleting, then rolling back, then a failed rollback, then leftovers, one per round | The same as 23: a state table (no old copy, an old copy, a leftover `.old`, a partly deleted `.old`, a failed copy, a failed rollback, someone else's folder) and one unit test per row in `test_install.py` | S |
| 25 | **`launch_designer`'s wait** | SRV-10 → SRV-15 → SRV-19 → SRV-20 / SRV-21 | Relaunch, wait, restart, how much time is left | A state table for the process and the bridge (not running; starting; answering; running but not answering; exiting during the wait; a second instance), one unit test per row in `test_lifecycle_env.py` with the fakes already there | S |
| 26 | **The self-test's clean-up and crash checks** | PLG-9 → TST-16 → TST-21; PLG-18 → TST-43 → TST-47; TST-30 → TST-33 → TST-51 → TST-59 | A clean-up step that failed skipped the rest; unguarded reads before the `try`; crash detection and the README's account of it | Register each clean-up step as its resource is made (a `contextlib.ExitStack` of callbacks, each run in its own `try`), so no failure can skip another; one crash-dump check at the end; README describes only what the run checks | M |
| 27 | **Refusing Designer's library packages** | HLP-10 → HLP-14 → HLP-18 → HLP-20 → TST-26 / TST-27 | The refusal message kept pointing to a tool that refuses too | One refusal helper used by every path (`_package_of`, `package_file_of`, `save_package`, snapshots), and a test that runs the tool each message suggests on a library graph and sees it work | S |
| 28 | **`open_graph`'s default fit** | HLP-32 → HLP-35 → HLP-38 / HLP-39, TST-68 | What "the whole graph" includes (nodes, frames, comments) and which errors the fit must not hide | Define the fitted area in one place (every node, frame and free comment) and check each kind once, plus each error path (another graph in the editor, an empty graph, no view) | S |
| 29 | **Empty function graphs** | HLP-13 → HLP-16 → TST-22 / TST-24, TST-20 | Whether Designer ignores an empty function graph was assumed, then measured piece by piece | One facts probe: no function graph, an empty one, one with nodes × set the value, compute, expose; AGENTS.md states the table; every caller of `_driving_graph` checked against it | S |
| 30 | **Smaller three-deep chains** | SRV-3 → SRV-14 → SRV-17 (snapshot copies); PLG-15 → PLG-20 → TST-55 (accept loop); PLG-22 → PLG-24 → TST-72 (output buffer); PLG-3 → SRV-16 → SRV-18 (client wait in docstrings); TST-28 → TST-34 → TST-62 (token in the self-test); INS-5 → INS-14 → INS-18 (`.mcp.json`); INS-8 → INS-22 → TST-50 (example re-run); TST-64 → TST-70 → TST-71 (Home screen fact); HLP-26 → TST-42 → TST-45 / TST-46 (inheritance fact) | Mostly a test or a sentence following its fix | Check each is settled: read its last entry and the code; if the pattern could recur, apply step 3 of the address-review skill once; otherwise delete it from this row | S |

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
