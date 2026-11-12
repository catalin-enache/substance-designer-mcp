# REVIEW.md: review findings

Findings from code reviews of this repository, kept across several reviews as a file in the project. How many is
the user's choice, most likely the life of a feature branch; the history stays in git for good.

This file is the **memory per branch**. Agents that review and agents that address findings talk through it, as
in a PR review: a finding is raised, then fixed or answered with why not, so the next reviewers know what was
settled and don't raise it again. Once the branch is merged it can be cleaned up. `DECISIONS.md` is the memory for
the whole project.

A new review **appends** its findings to the matching severity section and adds itself to the log; it never removes
or rewrites existing entries. An entry is checked when it is resolved, always with a resolution line that starts
with one of these wordings: done, not a bug, not reproducible, won't fix. Format and rules:
`.claude/skills/project-code-review/` (SKILL.md, TEMPLATE.md).

**Confidence.**

- *Confirmed*: the lead agent read the code and the defect is visible in it, as quoted.
- *Measured*: reading couldn't settle it, and the lead agent's scratch probe in Designer showed it (the entry gives
  the probe and what it measured; the `project-code-review` skill). A finding is one or the other, never a guess.

**IDs.** One prefix per area, numbered on: **PLG** plugin and bridge protocol, **SRV**
`mcp_server/server.py` and `server_tools/`, **HLP** `mcp_server/designer_helpers/`, **INS** installer, uninstaller,
command-line client and example, **TST** tests and docs. A new area gets a new prefix, added here.

**Last used:** PLG-42, SRV-119, HLP-119, INS-27, TST-334.

A new finding takes the next number for its area, and whoever writes it updates this line in the same edit. Only a
new finding raises it, and a cleanup leaves it as it is. Nothing lowers a committed number; dropping a finding before
committing it undoes its change.

**Findings no longer here.** Only the user starts a cleanup of this file (the `cleanup-review` skill). An ID
cited elsewhere but missing here was usually removed by one, which isn't a dangling reference.
`python3 scripts/review_lookup.py HLP-56` prints the whole entry, from this file or its git history, from any folder
of the repo. If it can't, it says why: the ID never existed, a squash lost it, or the clone is shallow.

## Status

| Severity | Open | Resolved |
|---|---|---|
| High | 0 | 0 |
| Medium-high | 0 | 0 |
| Medium | 0 | 1 |
| Low-medium | 0 | 6 |
| Low | 0 | 27 |
| **Total** | **0** | **34** |

## Review log

### 2026-11-12: branch 3d-view-control against main a fourth time, the diff only (after the fixes of HLP-116 to HLP-118, TST-330 to TST-332)

- **How:** three reviewers, reading only, the same three areas. No tests run, and no probe needed: reading settled
  every suspicion.
- **Resolutions assessed:** HLP-117, TST-330, TST-331, TST-332 hold; questioned: HLP-116 and HLP-118 (by HLP-119), HLP-115
  (by TST-333), HLP-107's note (by TST-334).
- **Findings:** HLP-119, TST-333, TST-334: 3 Low. Dropped under DECISIONS.md's rule on low-value findings:
  `test_the_timers_go_with_the_function_whatever_runs_of_its_finally`'s name says more than its assertion (a test's
  name, generation 4, found by two reviewers); review 3's log naming only the code chains at generation 3. A count
  corrected by a note (TST-330: four fakes behind six tests, not five). Not raised: the handler's `_parameters_back()`
  raising (review 2's probe 4 found no raise there; printing before it is part of HLP-119's fix). Outside the diff, not
  raised: `test_snapshots.py` and its siblings read a `tmp_path` path back out of the helper call (`'(.*?)'`); whether
  Windows' doubled backslashes break it would take a Windows run.
- **Chains:** the longest still growing is at generation 4 (HLP-107 → HLP-113 → HLP-116 → HLP-119): each fix of what an
  abort reports left a narrower window, now single traced events. HLP-119's fix is meant to end it: a note printed
  before each change, so no abort can land between a change and its record.
- **Suggested order:** HLP-119, TST-334, TST-333.
- **Checked and found fine:** the `owner` QObject's lifetime (a frame local, its timers parent-owned, freed as the
  plugin's `except` ends, `keep` never holding it); the handler's turn-back covering every point of `_set_tiling`'s
  `finally`; the wording "stopped while setting" for a step not yet changed; `temp_folders` against every server caller
  (one folder per call, made before the bridge); the timer fact's clean-up through its weakref; the unit fakes'
  signatures; the docs of review 3's fixes against the code.

### 2026-11-12: branch 3d-view-control against main a third time, the diff only (after the fixes of HLP-112 to HLP-115, TST-325 to TST-329)

- **How:** three reviewers, reading only, the same three areas as before (code, tests, docs). No tests run. The lead
  agent's scratch probes, one at a time in a Designer an agent started (port 51529): (1) a graph view zoomed to 0.78
  and off centre, then `screenshot_designer('3d', mesh='Plane', tiling=2)`: scale and centre unchanged; (2) after
  Materials > Add the Parameters panel showed the new material (`Material "mcp_selftest_material"`), and `tiling=2`
  then doubled the transitions on the Plane (15 to 31): the material in use took it; (3) Undo through the self-test's
  own snippet (`common.UNDO_REDO`): the control undid an added node (4 to 3 nodes); after an added node and a set-up
  taking the tiling from 1 to 2, Undo again removed the node (4 to 3) and the tiling stayed (31 transitions); a first
  try triggering Undo by its bare text undid nothing even in the control, so it settled nothing. Settled as wrong: the
  set-up adding to the undo history of the graph in the editor (probe 3); the turn-back resetting the graph view's
  zoom or pan (probe 1); `_tiling_spin` taking the field of a material the panel already showed (probe 2). Dropped
  under DECISIONS.md's rule on low-value findings: `check_the_3d_view_zooms_and_tiles`'s "each passes only what it
  changes" with `closer` and `away` passing `view='Top'` again on purpose (a test comment, generation 3); the module
  docstring's "until it switches again" (measured in this branch's first probes: switching to another graph and back
  applies the outputs; not false). Outside the diff, not raised: the same `finally` pattern as HLP-118 in older code
  (`describe.py`'s temporary output node, `editor.py`, the clipboard put back in `screenshots.py`, `sweep.py`'s
  restored parameter).
- **Resolutions assessed:** HLP-114, TST-326, TST-327, TST-328, TST-329 hold; questioned: HLP-112 (by HLP-118), HLP-113
  (by HLP-116, HLP-117), HLP-114's docs and HLP-115's (by TST-331), TST-325 (by TST-330).
- **Findings:** HLP-116 to HLP-118, TST-330 to TST-332: 1 Low-medium, 5 Low. The last wait outside the `try` was found
  by the lead agent and two reviewers (HLP-116); the lifecycle check's reason by two (TST-331). Longest chains still
  growing: generation 3 (HLP-107 → HLP-113 → HLP-116, HLP-117; HLP-108 → HLP-112 → HLP-118), each a defect in the
  tools' code, which the follow-up rules keep as entries at any generation.
- **Suggested order:** TST-330 (more unit tests failing on Windows), HLP-116 and HLP-117 (one handler), HLP-118, then
  TST-331 and TST-332.
- **Checked and found fine:** the moved `try`s (nothing started before them; Edit properties inside); the `except
  BaseException` branch re-raising unchanged, its print untraced; `_material`'s "(unused)" filter in both lookups;
  `_3d_dock`'s order of refusals, both callers keeping the Home screen's hint; the unit fakes of review 2's tests
  against the code; the lifecycle check's place in `launch_lock.held`, its clipboard-free calls; the clipboard rule;
  the thresholds against the measured values; REVIEW.md's counters, table and logs; GUIDE's 3D line; ROADMAP item 7.

### 2026-11-12: branch 3d-view-control against main again, the diff only (after the fixes of HLP-107 to HLP-111, SRV-119, TST-315 to TST-324)

- **How:** three reviewers, reading only: the code (`designer_helpers/view3d.py`, `editor.py`'s `_wheel`,
  `screenshots.py`'s `_3d_dock`, `server_tools/views.py`, `core.py`'s `_tool` and `_not_finite`, `scripting.py`), the
  tests (`editor_panels_and_fit`'s checks, preparations, renders and Designer scripts, `categories.py`, the unit tests
  `test_view3d.py`, `test_view3d_helpers.py`, `test_finite_numbers.py`, `test_selftest_renders.py`) and the docs
  (GUIDE.md, README.md, ROADMAP.md, DECISIONS.md, the docstrings). No tests run. The lead agent's scratch probes, one at
  a time in a Designer an agent started (port 51529, then a fresh one on it): (1) a tiling that works: the Parameters
  panel's title had already changed when `_switched` ran, which waited 0.0 s, twice; (2) "View Outputs In 3D View"'s
  trigger took 0.00 s with six 4K outputs and 0.01 s at 1K; (3) Materials > Add asks a name in a `QInputDialog`; with
  a second material named, `mesh='Plane', tiling=2` was refused ("the 3D view's mesh has 2 materials: Default
  (overridden), Second (unused) (overridden)"), the Plane had one, and the Sphere had one again once switched back to;
  (4) a package's function graph in the editor: `tiling=2` worked, the editor stayed on it; `openResourceInEditor` on a
  Pixel Processor's own function opened its parent graph instead, raising nothing; (5) `_apply_outputs` with the second
  timer's start raising (an abort landing there), no reference of the probe's kept to the timers: the pick timer was
  still active after the job and closed the next menu opened, in a later job, within 0.6 s; the menu after that stayed
  open, as did the control's before; (6) a fresh Designer before any graph was opened: the 3D dock visible with no menu
  bar and no viewport, `screenshot_designer('3d')` failing with "3D View menu bar not found" and with `mesh=` with
  "the 3D View's menu bar or viewport wasn't found"; once a graph was opened, one of each; (7) that Designer's default
  mesh from the Default view: 0.98 as high as wide; (8) `editor_panels_and_fit` then `facts` in one Designer, as one
  run orders them now: 100 checks passed, facts' widget capture against the render 88.1 grey levels apart (more than
  20 needed). Settled as wrong: the guard firing while the action runs, reporting a menu left open when none was
  (probe 2); `mesh=` doing nothing unseen by any check (probe 7: the view check's slanted ratio under 0.85 fails on the
  default mesh, which each category's fresh Designer starts on); the 3D view the editor category leaves changing what
  `facts` measures (probe 8); the turn-back raising with a function graph in the editor, hiding the result (probe 4).
  Dropped: `get_guide` not going through `_tool` (its one parameter is a string).
- **Not verified:** whether the Parameters panel's turn-back moves the user's editor out of a node's own function
  (a Pixel Processor's), which `getCurrentGraph()` may return while the user edits it: `openResourceInEditor` on such a
  function opened its parent graph (probe 4), but the probes couldn't open one in the editor as a user does: a
  double-click sent to the graph view selected the node only, and clicking a button of its Parameters panel opened a
  modal dialog that held the job past its timeout (the Designer was forced to quit). It would take opening a Pixel
  Processor's function by hand in a Designer an agent started, then `set_3d_view(tiling=2)` and reading
  `getCurrentGraph()` and the graph view before and after.
- **Resolutions assessed:** all sixteen hold for what they fixed; questioned: HLP-107 (by HLP-113, HLP-114), HLP-108
  (by HLP-112, TST-326), TST-321 (by TST-328), TST-324 (by TST-327).
- **Findings:** HLP-112 to HLP-115, TST-325 to TST-329: 1 Low-medium, 8 Low. The abort saying nothing of what was set
  was found by all three reviewers (HLP-113); the mesh being replaced checked for materials by two (HLP-114). The
  longest chain still growing is at generation 2 (HLP-107 → HLP-113, HLP-114; HLP-108 → HLP-112, TST-326).
- **Suggested order:** TST-325 (six unit tests failing on Windows), HLP-112 (a timer left running after an abort),
  HLP-113, HLP-114, HLP-115, then TST-326 to TST-329.
- **Simplifications:** the "build VIEW3D_GRAPH unless built" block now has four copies in `checks.py`.
- **Checked and found fine:** `_tool`'s check with MCP's keyword calls and the unit tests' positional ones
  (`bind_partial`), numpy floats (a float subclass), bools and ints not walked, paths such as `ops[0]['position'][0]`;
  no tool's legitimate input is a number that isn't finite; `run_designer_script`'s opt-out (JSON keeps them); every name
  in `view3d.py` imported from the part defining it; `pick`'s `finally` runs untraced after a raise; the guard has no
  Python frame and stops at the popup open before; the order of the up-front checks (the graph before any panel);
  `_switched` bounded and free when the panel has switched (probe 1); `_set_tiling` reports the spin box's value;
  the '3D view:' lines on the server's render and crop errors; `_wheel` unchanged for `open_graph`; the unit fakes'
  signatures against the code; each named test fails without its fix (reading); thresholds against the measured values;
  the 3D checks skip in the user's Designer and leave the Parameters panel on the editor's graph; REVIEW.md's table,
  counters and log; the DECISIONS.md entry; README's and ROADMAP's items 73 to 90 against what was built; the zoom
  figures in every place.

### 2026-11-12: branch 3d-view-control against main, the diff only (ROADMAP item 7: screenshot_designer('3d', ...) sets up the 3D view)

- **How:** three reviewers, reading only: the code (`designer_helpers/view3d.py`, `editor.py`'s `_wheel`,
  `server_tools/views.py`), the tests (`editor_panels_and_fit`'s checks, preparations, renders and Designer script,
  `categories.py`, the three new unit test files) and the docs (GUIDE.md, README.md, ROADMAP.md, DECISIONS.md, the
  docstrings). No tests run. The lead agent's scratch probes, one at a time in a Designer an agent started (port 51529):
  (1) the editor showing a brick graph A, `graph=` a checker graph B with `tiling=1`: B stayed on the mesh (mean R-B
  -16.5, the bricks 36.4), so turning the Parameters panel back doesn't put A's outputs back; (2) the graph view after
  those Explorer context menus: 48 items before and after, visible; (3) after `collapse_package`,
  `setExplorerSelection` alone left the package expanded; (4) outputs added to the open graph, then the graph computed
  and 2 s of events: the mesh still showed the earlier material (39 transitions, R-B 36.4: the bricks), so the designer
  fact doesn't hang on timing; (5) a Levels node shown in the Parameters panel: its field is named `tiling`, the
  material's `$tiling`, and `tiling=2` doubled the transitions (15 to 31) with the panel back on the graph; (6) the
  Tiling spin box: 0 to 3.4e38, 45 decimals; one ViewportWidget in the 3D dock, visible; (7) `View Outputs In 3D View`
  on graphs with two outputs (one without a usage, the same usage twice, a custom usage, neither with a usage): no
  second menu and no dialog in any. Settled as wrong: the material's field taken from a node's page (probe 5); a
  second ask or a modal dialog after the action for two outputs (probe 7); the tiling clamped or rounded (probe 6);
  reopening the editor's graph undoing `graph=` (probe 1); a hidden ViewportWidget taken (probe 6); the Explorer's
  context menu harming the graph view (probe 2); the designer fact passing only because the shot comes at once (probe
  4); a second scratch run in one Designer starting with the pattern on the mesh (every repeated scratch run of this
  branch in one Designer read none before). Dropped: `mesh=''` or `view=''` reaching Designer (its refusal names `''`,
  nothing changes); the dict spreads `**THREE_D` counting as `graph` in `test_every_tool_parameter_is_exercised_live`
  (`graph` is also passed literally; a weakness of that older test only once that is removed).
- **Not verified:** the whole set-up on Windows (another OS here): ROADMAP item 90 says what would check it.
- **Resolutions assessed:** none in scope (REVIEW.md held no findings).
- **Findings:** HLP-107 to HLP-110, TST-315 to TST-324: 1 Medium, 4 Low-medium, 9 Low; the three reviewers' reports on
  the partial changes merged into HLP-107, and the collapsed package's two into TST-320. Every one is generation 1.
- **Suggested order:** HLP-107 (what an error leaves in the user's 3D view and panel), HLP-108 (a held job), then
  TST-315 and TST-316 (facts and timers without a test), TST-317 (zoom's starting point and the state kept), the Lows.
- **Simplifications:** the faked-helpers fixture of the unit tests now has eight copies (`test_view3d_helpers.py`,
  `test_default_output.py`, `test_library_refusal.py`...): one in conftest; the "build VIEW3D_GRAPH unless built" block
  twice in `checks.py`; `set_3d_view`'s dock and menu-bar lookup repeating `_save_3d_render`'s.
- **Checked and found fine:** `_wheel` with `pause=0` behaves as before for `open_graph` (a fresh event per notch);
  the `view3d` part's imports and PARTS; every consumer of `screenshot_designer` reads `content[0]`, still the image;
  `%r` of the user's strings into the helper call, `zoom or None`, options refused off `panel='3d'` before anything is
  sent; the timers stopped in a `finally`; the one-output refusal before any change; each view, zoom and tiling check
  fails if its option does nothing; the Parameters panel check fails without the turn-back; the view-changing checks
  skip in the user's Designer; CLIPBOARD and the category's place by time; the unit tests' refusal and `_MenuPick`
  cases each guard their condition; the 34 environment maps; `SDResourceScene` in the API; ROADMAP's numbering.

---

## High

## Medium-high

## Medium

- [x] **HLP-107 · An error after the first change hides what was already changed, and leaves the Parameters panel on the 3D material** · `mcp_server/designer_helpers/view3d.py:240-300`, `mcp_server/server_tools/views.py:95-109` · confirmed · found 2026-11-12
  - **Defect.** `set_3d_view`'s docstring says "Everything is checked before anything changes", but the Explorer panel (`:159`), its tree and the graph's row, the Parameters panel (`:210`), the Materials menu and the `$tiling` field are only checked when their step comes, after the mesh, outputs, view or zoom have changed; the `done` list is printed only at the end (`:300`), so the error carries none of it. `_set_tiling` raising after `Edit properties` skips the turn-back (`:235`), so the panel stays on the material. `screenshot_designer` drops the '3D view:' line when the render or the crop fails after the set-up succeeded.
  - **Scenario.** `screenshot_designer('3d', mesh='Plane', tiling=2)` with the Parameters panel closed: the user's mesh becomes the Plane, the error names only the panel, and the agent tells the user nothing changed. The refusals check passes one option at a time, so it can't see this.
  - **Fix.** Check the Explorer (with `graph`) and the Parameters panel (with `tiling`) before the first change; turn the panel back in a `finally` once Edit properties ran; on an error, say what was already set (the `done` list) and keep the '3D view:' line when only the render fails. A check: a refused combined call (`mesh=` with a refused `graph=`) leaves the 3D render as it was.
  - **Resolution: done**.
    - **Test:** `test_a_panel_it_needs_is_checked_before_anything_changes` (tiling, graph: the Scene mesh triggered
      before the panel's error, or no up-front check at all), `test_the_menu_entries_it_needs_are_looked_up_before_anything_changes`,
      `test_an_error_after_a_change_says_what_was_set`, `test_the_parameters_panel_is_turned_back_when_the_tiling_fails`
      (`tests/unit/test_view3d_helpers.py`) and `test_a_shot_that_fails_after_the_set_up_says_what_was_set` (render,
      crop: the last line was the error; `tests/unit/test_view3d.py`), each failing before the fix; the live
      `check_a_set_up_checks_what_it_needs_first_and_says_what_it_set` failed in its scratch run (the render changed 44.7
      grey levels: the mesh became the Sphere before the Parameters panel's error; the panel left on `Material "Default"`,
      the error saying nothing of the Sphere) and passes after (0.0 levels; "the 3D view was already set: Sphere"; the
      panel back on the graph). Its Tiling field fails once the panel shows it; failing at once, the panel's switch to the
      material came after the turn-back (HLP-111). Without the `finally`, a mutant run of the check failed on the panel.
    - **Cause:** each panel and menu entry was looked up only as its step came, after earlier steps had changed the
      view; what was set was printed only at the end; the panel was turned back only after a tiling that worked; the
      server returned only the error's last line.
    - **Fix:** `set_3d_view` (`designer_helpers/view3d.py`) checks the graph, the 3D View, the Explorer's tree
      (`_explorer_tree`, with `graph`), the Parameters panel (with `tiling`) and every menu entry it will trigger (Scene >
      mesh, Camera > view and Frame, Materials > material > Edit properties) before the first change, and looks each up
      again as it is used; an error after a change is raised again as "...; the 3D view was already set: ...";
      `_set_tiling` turns the panel back in a `finally` (`_parameters_back`); `screenshot_designer` adds the '3D view:'
      line to its error when the render or the crop fails after the set-up.
    - **Also covered:** every step of the set-up (mesh, graph, view, zoom, tiling) and both of the server's errors after
      the bridge call (render, crop); the docstring now says what is checked first.
  - Questioned by HLP-113, HLP-114 (2026-11-12).
  - Note (2026-11-12): in one scratch run of six, `check_a_set_up_checks_what_it_needs_first_and_says_what_it_set` found a render that wasn't an image (a difference of 255.0); not reproduced in five more runs, and the run kept no log of it. The check now prints a failed shot's error.
  - Questioned by TST-334 (2026-11-12): its note says the check now prints a failed shot's error, which its printed line cuts.
  - Note (2026-11-12): the failed shot's error is now printed on a line of its own (TST-334: the check's detail cut it).

## Low-medium

- [x] **HLP-108 · A cancel or timeout landing in the menu timer leaves the Explorer menu open and the job held** · `mcp_server/designer_helpers/view3d.py:175-198` · confirmed · found 2026-11-12
  - **Defect.** The plugin drops an abort raised in a Qt slot and raises it again at the next traced event (`_make_tracer`'s docstring). `pick` triggers the action, then closes the menu, with no `finally`; the 5 s guard `close_menus` is a Python slot too, so a re-armed abort raises at its first event and its body never runs.
  - **Scenario.** A `cancel_designer_job` or the job's deadline while `View Outputs In 3D View` runs: the abort lands in `pick` between `trigger()` and `menu.close()`, the menu stays open, `sendEvent` doesn't return, and the bridge is held until someone clicks the menu away (in a Designer an agent started, no one does).
  - **Fix.** `menu.close()` in a `finally` in `pick`; a guard that runs no Python, such as the found menu's `close` connected to a timer (measure that PySide connects it as a C++ slot).
  - **Resolution: done**.
    - **Test:** `test_the_menu_is_closed_even_when_the_trigger_raises` (an exception standing in for the abort; failed
      before: no `finally`), `test_the_guard_closes_the_popups_above_the_one_open_before_and_runs_no_python` (Python
      frames recorded with `sys.settrace` while the guard runs: none) and `test_the_guard_closes_at_most_five_popups`
      (`tests/unit/test_view3d_helpers.py`). Measured first (scratch probes): the Explorer's context menu is a new QMenu
      each time, with no parent, deleted once closed, so nothing can be connected to it before it opens; a guard made of
      C callables closed it after 1 s, its only Python frames the plugin's own `_drain` (untraced by `_make_tracer`).
      The live 3D checks pass with it (`editor_panels_and_fit`, scratch run).
    - **Cause:** an abort raised in a Qt slot is dropped and raised again at the next Python line run, so both the
      close after the trigger and the Python guard `close_menus` could be skipped, leaving the menu's loop running.
    - **Fix:** `_MenuPick.pick` closes the menu in a `finally` (Python unsets a trace function that raises, so the
      `finally` runs); the guard is `_popup_closer`, `functools.partial(deque(maxlen=0).extend,
      map(methodcaller('close'), islice(iter(activePopupWidget, before), 5)))`: no Python frame for an abort to land
      in. Whether it ran (its timer no longer active) gives the "still open" failure. The module docstring says why.
    - **Also covered:** the other QTimer in the helpers (`quit.py`'s close at quit) runs after the job, not inside a
      nested loop the job waits on; the pick timer itself is Python, so an abort landing as it is called leaves the menu
      to the guard.
  - Questioned by HLP-112, TST-326 (2026-11-12).
- [x] **TST-315 · Facts view3d.py's docstring states, and the code relies on, have no check** · `mcp_server/designer_helpers/view3d.py:6-23` · confirmed · found 2026-11-12
  - **Defect.** No check measures that the Scene and Camera menus list MESHES and VIEWS, that every preset mesh has one material (`_material` sets the first), that the 3D view keeps its state from graph to graph, or that opening the editor's graph again doesn't apply its outputs, which `_set_tiling`'s turn-back relies on (probe 1 of this review: it doesn't); the checks use Plane with Default and Top only, every `graph=` already in the editor.
  - **Scenario.** A Designer update renames a mesh or gives Mat ball two materials: the refusal offers agents a name that fails, or `tiling=` tiles one material of two; or reopening the editor's graph starts applying its outputs, and `graph=B, tiling=...` with A in the editor shows A while the line says B. Nothing fails.
  - **Fix.** One "designer facts" check: the Scene and Camera menus' texts (nothing triggered) against MESHES and VIEWS, and with the editor on another graph, `graph=` plus `tiling=` keeps the given graph on the mesh; drop the sentences no check measures (one material per mesh, the state kept), or check them.
  - **Resolution: done**.
    - **Test:** two "designer facts" checks in `editor_panels_and_fit`: `check_the_3d_views_menus_have_the_meshes_and_views`
      (each Scene > mesh and Camera > view and Frame looked up, nothing triggered: `MISSING=[]`; with a mesh the menu
      lacks added, a scratch mutant printed `MISSING=['Scene > Teapot']`) and
      `check_opening_the_editors_graph_again_leaves_the_outputs_on_the_mesh` (a plain graph in the editor, then
      `graph=` the checker with `tiling=`: 15 transitions, the panel back on the plain graph; without `graph=`, a mutant
      read 0). Both pass in the scratch run, as facts do. One material per mesh was measured on all 11 meshes, then made
      code rather than a fact: `_material` refuses a mesh with several (`test_a_mesh_with_several_materials_is_refused`,
      failing before). "Keeps its state from graph to graph" became "what is set stays", which
      `check_the_3d_view_zooms_and_tiles` now measures: a zoom without `view` after another goes from where the camera
      was left (0.75x, against 0.56x from the framed view), and the tiling of 2 stays (31 transitions, 15 at 1).
    - **Fix:** those checks; `_material`'s refusal; the module docstring narrowed to them.
    - **Also covered:** every sentence of `view3d.py`'s docstring read against a check: the zoom away (1.09x a step),
      the context menu's lifetime and the guard (HLP-108's probe and unit tests).
- [x] **TST-316 · Nothing tests that _apply_outputs stops its timers** · `mcp_server/designer_helpers/view3d.py:192-198` · confirmed · found 2026-11-12
  - **Defect.** The `finally` stopping both timers has no test: the unit tests cover `_row_point` and `_MenuPick` only.
  - **Scenario.** A change drops the `stop()`: the pick timer, which starts itself again every 100 ms, later triggers or closes a context menu the user opens, and no test fails.
  - **Fix.** A unit test with a faked `QtCore.QTimer` and `sendEvent`: returning with no menu, and raising, both timers end stopped.
  - **Resolution: done**.
    - **Test:** `test_both_timers_are_stopped_whatever_the_menu_does` (`tests/unit/test_view3d_helpers.py`), with
      `sendEvent` returning without a menu and raising: it passes with the code, which stopped them already; a mutant
      without `timer.stop()` failed both cases.
    - **Fix:** the test.
- [x] **TST-317 · The tool's docstring doesn't say the set-up stays, nor that zoom counts from the current camera** · `mcp_server/server_tools/views.py:66-73` · confirmed · found 2026-11-12
  - **Defect.** "as the user sees it too" says the user's 3D view changes, not that the mesh, camera, tiling and material stay for later shots; and `zoom` adds to wherever the camera is unless `view` is given (the checks pass `view='Top'` with every zoom for that reason).
  - **Scenario.** An agent calls `zoom=3` twice and gets six steps; it sets `tiling=2` once, and every later shot, and the user's view, stay tiled.
  - **Fix.** One clause: what it sets stays (for later shots and the user); zoom counts from the current camera, from the framed view after `view`.
  - **Resolution: done**.
    - **Test:** `check_the_3d_view_zooms_and_tiles` now measures both clauses (TST-315's resolution): zoom without `view`
      counts from the camera the call before left, and the tiling stays.
    - **Fix:** `screenshot_designer`'s docstring: "it stays set, for later shots and in the user's view" and "zoom:
      wheel steps from where the camera is (after view, from the framed view)".

- [x] **TST-325 · On Windows the server tests' bridge fake can't find the shot's path, so six tests fail on correct code** · `tests/unit/test_view3d.py:24` · confirmed · found 2026-11-12
  - **Defect.** `re.search(r"""'([^'\\]+shot\.png)'""", ...)` reads the path `screenshot_designer` writes into the call with `%r`; on Windows that path holds backslashes, doubled by `%r`, which `[^'\\]` excludes, so nothing matches (a scratch probe in plain Python: `re.search(pattern, repr(r'C:\Users\me\AppData\Local\Temp\sd_shot_x\shot.png'))` is None) and the fake's `assert out is not None` fails.
  - **Scenario.** The final check on Windows runs `pytest` beside the one live run (AGENTS.md): `test_the_3d_view_is_set_up_in_the_same_job_before_its_render`, `test_the_setup_line_comes_beside_the_image`, both cases of `test_without_options_nothing_is_set_up_and_only_the_image_comes_back` and of `test_a_shot_that_fails_after_the_set_up_says_what_was_set` fail, with nothing wrong in the code.
  - **Fix.** Patch `tempfile.mkdtemp` to a folder under `tmp_path` and take the path from there, or match a quoted string with escapes and decode it with `ast.literal_eval`.
  - **Resolution: done**.
    - **Test:** the bridge fake now gives the shot's folder a backslash in its name on macOS too, as a Windows path has:
      with that alone the six tests failed here as on Windows ("assert None is not None" in the fake).
    - **Cause:** the fake read the path back out of the helper call, whose `%r` doubles backslashes, with a pattern
      excluding them.
    - **Fix:** the fake patches `tempfile.mkdtemp`, keeps the folder it made, saves the shot there and checks only that
      the call names that path (its `repr`).
    - **Also covered:** no other unit test reads a path back out of the helpers' code (searched for the pattern).
  - Questioned by TST-330 (2026-11-12).
  - Note (2026-11-12): its Also covered missed five fakes (TST-330); its patch is now the `temp_folders` fixture.

- [x] **TST-330 · Five more unit-test bridge fakes read a temp path out of the helper call and fail on Windows · follows TST-325, generation 2** · `tests/unit/test_default_output.py:72, 160, 217`, `tests/unit/test_pixels.py:124` · confirmed · found 2026-11-12
  - **Defect.** TST-325's "Also covered" says no other unit test reads a path back out of the helpers' code, but these do, with patterns that exclude the backslashes `%r` doubles in a Windows path: `([^'"\\ ]+node\.png)` and `([^'"\\\\ ]+pixels\.raw)` match nothing (a plain-Python scratch probe against `repr` of a Windows temp path), `([^'"\\ ]*sd_sweep_[^'"\\ ]+)` matches the bare folder name (`sd_sweep_ab`), and `(/[^'\\]*sd_sweep_\w+)` needs a leading `/`.
  - **Scenario.** The Windows final check's `pytest` fails on correct code: `test_preview_returns_the_note_beside_the_image`, `test_preview_returns_only_the_image_when_there_is_no_note`, `test_the_pixel_tools_carry_the_note[node_stats]` and `[check_tiling]`, `test_a_failed_restore_is_reported_with_an_output_named_like_restored`, `test_sweep_reports_a_value_that_failed`.
  - **Fix.** TST-325's way: patch `tempfile.mkdtemp` (a backslash in the folder's name on macOS too) and take the path from the folder it made; correct TST-325's "Also covered" with a note. The code is main's, but the search the resolution claims is this branch's.
  - **Resolution: done**.
    - **Test:** the six tests, given a folder whose name holds a backslash on macOS too (the new `temp_folders`
      fixture in `tests/unit/conftest.py`), failed here as on Windows before their fakes changed.
    - **Cause:** each fake read its temp path back out of the helper call, with a pattern a Windows path's escaped
      backslashes defeat.
    - **Fix:** `temp_folders` patches `tempfile.mkdtemp`, keeps the folders it made and names them with a backslash
      where paths don't use one; the five fakes and `test_view3d.py`'s (TST-325's own patch, now this one) take their
      folder from it.
    - **Also covered:** every unit test matching a temp path in the helpers' code (searched for `mkdtemp` prefixes
      and the patterns reading them: `sd_preview_`, `sd_px_`, `sd_sweep_`, `sd_shot_`; `sd_cook_` and `sd_diff_` are
      never read back by a fake).
  - Note (2026-11-12): four fakes, behind the six tests, not five (`test_default_output.py:72, 160, 217`, `test_pixels.py:124`).

## Low

- [x] **HLP-109 · The menu timer and the guard act on any popup, the user's own included** · `mcp_server/designer_helpers/view3d.py:175-191` · confirmed · found 2026-11-12
  - **Defect.** `pick` takes `activePopupWidget()` as the Explorer's menu and closes it; the guard closes up to five popups. A job runs inside whatever event loop is current, a menu the user has open included.
  - **Scenario.** The user has a menu open when the job runs and the Explorer's menu doesn't open: `pick` closes the user's menu and reports "had no 'View Outputs In 3D View'".
  - **Fix.** Record the popup open before `sendEvent` and act only on a different one.
  - **Resolution: done**.
    - **Test:** `test_a_popup_open_before_the_menu_isnt_taken_for_it` (failed before: no `before`) and the guard's test
      in HLP-108's resolution (it stops at the popup open before). Measured in a scratch probe: with a menu of "the
      user's" open, the guard closed the Explorer's menu and left that one open.
    - **Cause:** both timers took whatever popup was active.
    - **Fix:** `_apply_outputs` records the popup open before `sendEvent`; `_MenuPick` never takes it for the
      Explorer's menu, and `_popup_closer` stops at it.
- [x] **HLP-110 · The result and the refusals say more, or other, than the code knows** · `mcp_server/designer_helpers/view3d.py:226-230, 256-300`, `mcp_server/server_tools/views.py:70, 87` · confirmed · found 2026-11-12
  - **Defect.** "tiling %g" reports the value asked for and `invokeMethod`'s False (the signal not found, nothing committed) is ignored; "the outputs of %s on it (%d)" counts output nodes, and says "on it" with no mesh given; a disabled action counts as picked; a graph with no outputs gets "Designer would ask which channel" and "preview_node shows one output", and the tool's docstring says "a single output" where the code refuses fewer than two; the 3D dock's error lacks `_save_3d_render`'s Home-screen hint; `tiling=inf` passes `not tiling > 0` and reaches Designer as a NameError.
  - **Scenario.** A Designer whose spin box lost its signal: the line says "tiling 2" and nothing changed; an agent passes a graph with no outputs and is told about channels.
  - **Fix.** Raise when `invokeMethod` returns False and report the spin box's value; "the graph's N outputs"; skip a disabled action; "has no outputs" said plainly, "fewer than two outputs" in the docstring; the Home hint; refuse a tiling that isn't finite.
  - **Resolution: done**.
    - **Test:** `test_a_tiling_the_spin_box_didnt_take_is_an_error`, `test_the_tiling_said_is_the_spin_boxs`,
      `test_a_disabled_action_isnt_triggered_and_is_said`, `test_the_line_says_what_was_set`,
      `test_a_graph_with_fewer_than_two_outputs_is_refused_before_the_panels_are_looked_at` (no outputs said plainly;
      `tests/unit/test_view3d_helpers.py`) and the `inf` and `nan` cases of
      `test_zoom_and_tiling_out_of_range_are_refused` (`tests/unit/test_view3d.py`; `inf` passed before), each failing
      before the fix. Measured first: `invokeMethod` returned True for the spin box's `valueChanged`, False for a name
      it lacks.
    - **Fix:** `_set_tiling` raises when `invokeMethod` returns False and reports the spin box's value; the line says
      "graph X's outputs on the mesh"; a disabled action isn't triggered and is said; "has no outputs to show", and
      the tool's docstring says "fewer than two outputs"; the 3D View's error comes from `_3d_dock`
      (`designer_helpers/screenshots.py`), shared with the render, Home screen hint included; `tiling` must be finite.
    - **Also covered:** other tools' floats reach helper calls the same way: SRV-119.
  - Note (2026-11-12): `tiling`'s finite check moved to the `_tool` decorator with SRV-119.
- [x] **TST-318 · The refusals check fails instead of skipping where the user's Designer hides its 3D View** · `tests/test_all_tools/editor_panels_and_fit/checks.py:184` · confirmed · found 2026-11-12
  - **Defect.** The one-output refusal comes after the 3D dock check (`view3d.py:260`), so with no 3D View visible the answer is "the 3D View panel is not visible" and `'one output' in t` fails; the 3D capture check skips there.
  - **Scenario.** A run in the user's Designer (Windows, one run) with the 3D View closed: a failure no fix can clear.
  - **Fix.** Skip on `'not visible' in t and ctx.was_running`, as the capture check does.
  - **Resolution: done**.
    - **Test:** `test_a_graph_with_fewer_than_two_outputs_is_refused_before_the_panels_are_looked_at` (with the 3D View
      hidden the error was "not visible"; failed before).
    - **Fix:** `set_3d_view` refuses the graph before it looks at any panel, so the refusals check doesn't hang on the
      3D View; no skip needed.
- [x] **TST-319 · The zoom check lets a step too many away pass, and may clip the plane coming closer** · `tests/test_all_tools/editor_panels_and_fit/checks.py:103-123` · confirmed · found 2026-11-12
  - **Defect.** Steps away measured 0.77x for three (about 0.917 each), so four (0.71x) fall inside `[STEP**-3 * 0.95, STEP**-3 * 1.1]` = [0.69, 0.80]; three steps closer make the plane 330 of 372 px, so a narrower 3D panel would clip it and `plane_width` would stop growing.
  - **Scenario.** A regression sending one wheel step more going away passes; a Designer with a narrower 3D panel fails a correct zoom.
  - **Fix.** A lower bound near 0.74 going away; and fail with the reason when `plane_columns` touches the image's first or last column.
  - **Resolution: done**.
    - **Test:** the zoom checks in their scratch runs: three steps away measured 0.76x to 0.78x over four runs (0.75x
      from a zoomed camera), within `STEP_AWAY**3` x [0.95, 1.05] = [0.73, 0.81], which two steps (0.84x) and four
      (0.71x) miss.
    - **Fix:** `STEP_AWAY = 0.917` for steps away; the zoom closer fails, saying so, when the plane touches the
      render's first or last column.
- [x] **TST-320 · The collapsed package's expansion is credited to scrollTo, but setExplorerSelection does it** · `mcp_server/designer_helpers/view3d.py:100-102`, `tests/test_all_tools/editor_panels_and_fit/checks.py:157-158`, `tests/unit/test_view3d_helpers.py:61-66`, `ROADMAP.md` item 7 · measured · found 2026-11-12
  - **Defect.** Probe 3 of this review: after the package was collapsed, `setExplorerSelection` alone left it expanded, before any `scrollTo`; the docstrings say QTreeView.scrollTo expands it ("measured live"), the check's docstring says "the package is expanded first" as if the tool did it, and the unit test named for scrolling before the point is read passes with the order reversed (its fake `visualRect` doesn't depend on `scrollTo`).
  - **Scenario.** A maintainer drops `setExplorerSelection` for another way to pick the row, trusting `scrollTo` to expand: the row of a collapsed package isn't showing and is refused.
  - **Fix.** Credit `setExplorerSelection` in the docstrings and ROADMAP; name the unit test for what it checks, or make its `visualRect` require the scroll first.
  - **Resolution: done**.
    - **Test:** `test_a_graphs_row_is_scrolled_into_view_before_its_point_is_read`: its fake `visualRect` now gives the
      row's point only once `scrollTo` ran; a mutant reading the point first failed it.
    - **Fix:** `_row_point`'s docstring no longer credits `scrollTo`; the module docstring, the check's docstring and
      ROADMAP item 7 credit `setExplorerSelection`.
- [x] **TST-321 · Docs and comments that say more, or other, than what is measured** · `mcp_server/server_tools/views.py:68-70`, `ROADMAP.md` item 7, `tests/test_all_tools/editor_panels_and_fit/checks.py:25, 31-32`, `README.md:92`, `tests/unit/test_view3d.py:14` · confirmed · found 2026-11-12
  - **Defect.** "never reach it otherwise" / "never get there" / "never reach it": switching to another graph and back applies them (`view3d.py:11`); item 7 calls the default cube the cause (the outputs explain the default material on it) and lists "the viewpoints" where Default and Top are measured; the TOP comment says each 3D check starts from Top, which two don't; README's "the 3D view set up first" reads as always; the unit test's NOTE isn't the line the helper prints.
  - **Scenario.** An agent told outputs never reach the 3D view doesn't think of switching graphs; a reader of the README thinks every 3D shot changes the view.
  - **Fix.** "don't reach it until Designer switches to the graph"; item 7 narrowed to what its checks measure; the comment narrowed; "optionally set up first"; the NOTE as printed.
  - **Resolution: done**.
    - **Fix:** "don't reach it until Designer switches graphs" (the tool's docstring, the check's docstring, the module
      docstring); item 7 says the mesh kept the default material, the Default and Top viewpoints, zoom both ways; the
      TOP comment says what a call sets stays; README's "optionally set up first"; the unit test's NOTE is the line
      the helper prints.
  - Questioned by TST-328 (2026-11-12).
- [x] **TST-322 · One fact in several places** · `mcp_server/GUIDE.md:47-49`, `DECISIONS.md:217-224`, `mcp_server/server_tools/views.py:15`, `mcp_server/designer_helpers/view3d.py:9-10` · confirmed · found 2026-11-12
  - **Defect.** GUIDE's core repeats the tool docstring's "outputs added ... never reach" fact, read by every session; the DECISIONS entry repeats `view3d.py`'s measured Tiling facts, where the file's introduction says an entry links to them; the zoom factor is written in four places, and the module docstring, its home, leaves out that steps away are shorter (about 1.09x).
  - **Scenario.** One of the copies is corrected and the others go on saying the old thing.
  - **Fix.** GUIDE keeps the pointer and the usage hint (Plane, Top, tiling); the DECISIONS entry keeps the decision, its reason and the link (its wording takes the user); the module docstring gets the shorter steps away and the comment drops the number.
  - **Resolution: done**.
    - **Fix:** GUIDE's core keeps the pointer and the usage hint, the fact staying in the tool's docstring; the
      DECISIONS.md entry keeps the decision, its reason and the link, the measured Tiling facts left to
      `view3d.py` (the user's go-ahead to fix every finding, 2026-11-12); the zoom's size is in the module docstring
      (both ways) and the tool's docstring, the server's comment pointing there.
- [x] **TST-323 · GUIDE's scripting line on the Explorer's context menu could read as permission for synthetic context menus anywhere** · `mcp_server/GUIDE.md:331-333` · confirmed · found 2026-11-12
  - **Defect.** It says the tool opens the Explorer's context menu with a `QContextMenuEvent`, a few lines below "Don't send it synthetic key events or right-clicks" (the graph view went blank), without saying it was only seen safe on the Explorer's tree (probe 2 of this review: the graph view kept its 48 items).
  - **Scenario.** An agent writing Qt code opens a context menu on the graph view by event, as the line seems to allow.
  - **Fix.** "on the Explorer's tree; the graph view's warning stands".
  - **Resolution: done**.
    - **Fix:** GUIDE's line says the `QContextMenuEvent` goes to the Explorer's tree only, and that the warning above
      about the graph view stands.
- [x] **TST-324 · Qt code inline in a check, where the live-check skill puts it in a Designer script** · `tests/test_all_tools/editor_panels_and_fit/checks.py:131-147` · confirmed · found 2026-11-12
  - **Defect.** The Parameters panel check runs seven lines of dock lookup inline, and takes `docks[0]` without `isVisible()`, unlike `_visible_dock`.
  - **Scenario.** Two Parameters docks, one hidden: the check reads the hidden one's title.
  - **Fix.** A Designer script in `designer_scripts/`, taking the visible dock.
  - **Resolution: done**.
    - **Fix:** `designer_scripts/editor_panels_and_fit/parameters_panel.py`, taking the visible Parameters dock, used by
      the zoom and tiling check and HLP-107's check.
  - Questioned by TST-327 (2026-11-12).
- [x] **HLP-111 · An abort right after Edit properties can leave the Parameters panel on the 3D material · follows HLP-107, generation 2** · `mcp_server/designer_helpers/view3d.py` (`_set_tiling`) · measured · found 2026-11-12
  - **Defect.** `_set_tiling` turns the panel back in a `finally`, but Designer switches the panel to the material over a few event loops after Edit properties; a failure before that switch turns it back first, and the switch lands after. Only an abort can fail that early: `_tiling_spin`'s own "not found" waits up to 3 s, by when the panel has switched.
  - **Scenario.** Measured while addressing HLP-107: with `_tiling_spin` replaced by one raising at once, the panel ended on `Material "Default" - Rasterizer`, the editor on the graph. A cancel at that moment leaves the user's Parameters panel on the 3D material; one click on a node brings it back.
  - **Fix.** Let the panel finish its switch before turning it back (process events until it shows the material, bounded), or turn it back once more after a short wait.
  - **Resolution: done**.
    - **Test:** `test_the_parameters_panel_is_turned_back_once_it_shows_the_material` (a panel whose title changes after
      three waits; turned back while it still read `g` before the fix) and `test_the_wait_for_the_panel_to_switch_ends`
      (a title that never changes: at most 10 waits); the live `check_a_set_up_checks_what_it_needs_first_and_says_what_it_set`
      now fails the Tiling at once, before the panel shows the material, as an abort in the first poll would: in its
      scratch run the panel stayed on `Material "Default" - Rasterizer` before the fix and is back on the graph after.
    - **Cause:** the turn-back ran as soon as the tiling failed, while Designer's switch to the material was still to
      come.
    - **Fix:** `_set_tiling` reads the panel's title before Edit properties and, in its `finally`, waits up to 1 s
      (`_switched`) for the title to change before turning it back; the module docstring says so.
    - **Also covered:** the tiling that works waits for nothing more (the panel has switched by the time its field
      was found); `_parameters_back` has no other caller.
- [x] **SRV-119 · A number that isn't finite reaches a helper call as `inf` or `nan` and fails as a NameError** · `mcp_server/server_tools/views.py:145` (`open_graph`'s `rect`), `mcp_server/server_tools/layout.py:39, 54, 64` (`arrange_graph`'s `spacing`, `add_frame`'s `color`, `add_comment`'s `position`), `mcp_server/server_tools/edits.py:107` (`apply_edits`' ops), `mcp_server/server_tools/measure.py:216` (`sweep_param`'s `values`) · confirmed · found 2026-11-12
  - **Defect.** JSON input such as `1e999`, `Infinity` or `NaN` becomes a float that isn't finite (measured: `json.loads` and pydantic both give `inf` and `nan`, in a float and in a list of floats); these tools write their values into the helper call with `%r`, which gives `inf` or `nan`, names the joined helpers don't define. Found addressing HLP-110, whose `tiling` is now refused.
  - **Scenario.** `open_graph(rect=[0, 0, 1e999, 100])`: Designer answers `NameError: name 'inf' is not defined`, nothing changes, and the agent can't tell which value was wrong.
  - **Fix.** One check in the server for every float a tool takes, nested ones included (the `_tool` decorator, or where each call is built), refusing a number that isn't finite by its parameter's name.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_finite_numbers.py`, through the server's `call_tool` as a client's call arrives: an
      `inf` or `nan` in each of the tools listed, `render_sbs`' `params` and `screenshot_designer`'s `tiling`, nested
      ones included (`ops[0]['position'][0]`), is refused naming where it is, with nothing sent; each failed before the
      fix (sent on to the bridge, or to sbscooker for `render_sbs`). `run_designer_script`'s `args` still pass (JSON
      keeps them), and `1e999`, `Infinity` and `NaN` are checked to validate to such numbers.
    - **Cause:** each tool wrote its values into the helper call with `%r`, and nothing refused a number that isn't
      finite.
    - **Fix:** the `_tool` decorator (`server_tools/core.py`) walks every argument, lists and dicts included
      (`_not_finite`), and refuses such a number before the tool runs: "rect[2] is inf, which isn't a finite number:
      nothing was sent to Designer". `run_designer_script` opts out (`finite=False`); `screenshot_designer`'s own
      finite check (HLP-110) is gone, this one covering it.
    - **Also covered:** every tool goes through `_tool`; the self-test's categories passing numbers most (editor,
      layout, batch: 69 checks) pass with it in a scratch run.
- [x] **HLP-112 · An abort landing before a clean-up's `try` leaves the pick timer running after the job, or the Parameters panel on the material · follows HLP-108, generation 2** · `mcp_server/designer_helpers/view3d.py:224-231` (`_apply_outputs`), `:283-285` (`_set_tiling`) · measured · found 2026-11-12
  - **Defect.** The timers are created and started in a loop before the `try` whose `finally` stops them: once the pick timer has started, the loop's second pass and the `try:` line are traced events where an abort can be raised, and then nothing stops it; `pick` starts itself again every 100 ms until a menu opens, and its connection keeps it alive. In `_set_tiling`, Edit properties is triggered on the line before its `try`, so an abort on the `try:` line skips the turn-back (HLP-111's scenario).
  - **Scenario.** Measured (probe 5 of this review's log): with the second timer's start raising, the pick timer was still active after the job and closed the next menu opened, in a later job, within 0.6 s. A cancel or timeout landing in those few events leaves the user's next menu closed as it opens; an Explorer context menu would also have "View Outputs In 3D View" triggered on it. Rare: a window of a few traced events.
  - **Fix.** Create, connect and start the timers inside the `try` (its `finally` stopping whichever exist), and trigger Edit properties inside `_set_tiling`'s `try` (`_switched` is bounded, so a trigger that never ran costs one second).
  - **Resolution: done**.
    - **Test:** `test_both_timers_are_stopped_whatever_the_menu_does`'s new case (the second timer's start raising, as
      an abort there would: the first was left active before the fix) and
      `test_the_parameters_panel_is_turned_back_when_edit_properties_raises` (no turn-back before the fix), in
      `tests/unit/test_view3d_helpers.py`. What a leaked timer does in Designer was measured by the review's probe 5; no
      live check repeats the unit test's guard (DECISIONS.md, low-value findings).
    - **Cause:** the timers were started, and Edit properties triggered, on lines before the `try` whose `finally`
      undoes them.
    - **Fix:** `_apply_outputs` makes, connects and starts each timer inside the `try`, its `finally` stopping those
      made; `_set_tiling` triggers Edit properties inside its `try`.
    - **Also covered:** `pick`'s menu (its `try` starts after the menu is counted: a menu left there is the guard's,
      which has no Python frame); no other change in `view3d.py` comes before its clean-up's `try`.
  - Questioned by HLP-118 (2026-11-12).
- [x] **HLP-113 · A cancel or timeout after a change says nothing of what was set · follows HLP-107, generation 2** · `mcp_server/designer_helpers/view3d.py:313, 378-383` · confirmed · found 2026-11-12
  - **Defect.** `except Exception` doesn't catch the plugin's `ScriptAborted`, a `BaseException`, and the '3D view:' line is printed only at the end, so an abort after the mesh or the outputs changed comes back as "ScriptAborted: ..." alone; the docstring says "an error after a change says what was set".
  - **Scenario.** `screenshot_designer('3d', mesh='Plane', graph='big')` whose compute runs past the job's 120 s, or a `cancel_designer_job` during the zoom: the user's mesh and view changed, the agent is told only that the job stopped. `_bridge` returns a failed job's output with its error, and `screenshot_designer` already adds the '3D view:' lines to its error, so a line printed before the abort would reach the agent.
  - **Fix.** On a `BaseException` after a change, print `'3D view: ' + ', '.join(done)` (saying it stopped there) and raise it again unchanged, so the plugin still reports the abort. All three reviewers found it.
  - **Resolution: done**.
    - **Test:** `test_an_abort_after_a_change_says_what_was_set_and_goes_on` and
      `test_an_abort_before_any_change_says_nothing` (unit), and a third part of the live
      `check_a_set_up_checks_what_it_needs_first_and_says_what_it_set`: `_apply_outputs` raising a `BaseException` of
      its own after the mesh changed; in its scratch run the reply held only the abort before the fix, and "3D view:
      Plane; then stopped" with the abort after.
    - **Cause:** only `Exception` was caught, and what was set was printed at the end alone.
    - **Fix:** `set_3d_view` prints "3D view: ...; then stopped" on a `BaseException` after a change and raises it
      again unchanged; `screenshot_designer` adds that line to its error, as for others.
  - Questioned by HLP-116, HLP-117 (2026-11-12).
- [x] **HLP-114 · tiling= with mesh= is refused for the materials of the mesh being replaced, an unused one included · follows HLP-107, generation 2** · `mcp_server/designer_helpers/view3d.py:86-101` (`_material`), `:352-353` · measured · found 2026-11-12
  - **Defect.** The up-front check reads the Materials menu before `Scene > mesh` changes the mesh, and `_material` counts every material, those Designer marks unused included.
  - **Scenario.** Measured (probe 3 of this review's log): a second material added to the Sphere (Materials > Add, named), `mesh='Plane', tiling=2` was refused with "the 3D view's mesh has 2 materials: Default (overridden), Second (unused) (overridden)", although the Plane had one and the Sphere had one again once switched to. The same count refuses `tiling=` alone on a mesh with an unused material, where the used one is the one to tile. Nothing changes; the agent is told about a mesh it is replacing.
  - **Fix.** With `mesh` given, check only that the Materials menu has Edit properties' path after the switch (`_set_tiling` reads the new mesh's material anyway), and count only the materials not marked unused.
  - **Resolution: done**.
    - **Test:** `test_a_material_the_mesh_doesnt_use_isnt_counted`,
      `test_tiling_with_a_mesh_doesnt_count_the_materials_of_the_mesh_it_replaces` and the "another mesh" case of
      `test_the_menu_entries_it_needs_are_looked_up_before_anything_changes` (unit), and the live
      `check_a_material_the_mesh_doesnt_use_doesnt_stop_tiling` (a material added through Materials > Add, named in
      Designer's dialog by a timer): refused for "2 materials" in its scratch run before the fix, tiled after.
    - **Cause:** the up-front lookup read the Materials menu before the mesh changed, and every material was counted.
    - **Fix:** with `mesh=` the up-front check only looks the Materials menu up, the new mesh's material read as
      `_set_tiling` shows it; `_material` leaves out materials listed "(unused)" (measured: Designer's own label).
  - Questioned by TST-331 (2026-11-12).
- [x] **HLP-115 · Before any graph has been opened, the 3D view's errors don't say that opening one builds it** · `mcp_server/designer_helpers/view3d.py:338-339`, `mcp_server/designer_helpers/screenshots.py` (`_save_3d_render`) · measured · found 2026-11-12
  - **Defect.** Designer builds the 3D view's menu bar and viewport only once a graph has been opened (probe 6 of this review's log: none of either before, one of each after), so the set-up says "the 3D View's menu bar or viewport wasn't found" and the render "3D View menu bar not found", neither saying what to do; the 3D dock's other error already gives such a hint (the Home screen).
  - **Scenario.** A Designer just started, nothing opened yet: `screenshot_designer('3d', mesh='Plane')` fails with a message an agent can't act on.
  - **Fix.** Say "the 3D view is built once a graph is opened: open_graph first" when the dock has no menu bar, in one place both use (`_3d_dock`).
  - **Resolution: done**.
    - **Test:** `test_the_3d_view_before_any_graph_was_opened_is_said` (unit) and the live
      `check_the_3d_view_waits_for_a_graph` in `lifecycle`, right after its Designer starts (no other category's has
      never opened a graph): it looks the 3D dock up and runs a set-up with no render, as a 3D shot would use the
      clipboard beside the categories of `categories.CLIPBOARD`. In scratch runs, each in a Designer that had never
      opened a graph: with `_3d_dock` as before the fix, the dock was taken as built and the set-up said "menu bar or
      viewport wasn't found"; with the fix both say to open a graph. The whole `lifecycle` category passed with the
      check in place (50 checks, its first version taking 3D shots).
    - **Fix:** `_3d_dock` (`designer_helpers/screenshots.py`), shared by the render and the set-up, says "the 3D view
      isn't built yet: Designer builds it once a graph is opened (open_graph)" when the dock has no menu bar; the
      module docstring of `view3d.py` says what was measured.
  - Questioned by TST-331 (2026-11-12).
  - Note (2026-11-12): the lifecycle check's reason narrowed by TST-331: in a pool most categories' Designers never open a graph either.
  - Questioned by TST-333 (2026-11-12).
- [x] **TST-326 · Nothing fails when the guard's firing isn't reported · follows HLP-108, generation 2** · `mcp_server/designer_helpers/view3d.py:235`, `tests/unit/test_view3d_helpers.py` (`test_both_timers_are_stopped_whatever_the_menu_does`) · confirmed · found 2026-11-12
  - **Defect.** `held = not timers[1].isActive()` has no test: the `Timer` fake never fires, and `failure(held=True)` is tested on `_MenuPick` alone; a mutant `held = False` passes every unit and live check.
  - **Scenario.** A change that loses `held` reports a second menu closed unanswered as success, the outputs maybe not on the mesh, and no test fails.
  - **Fix.** In the timers' test, keep each timer's `run`; in the faked `sendEvent`, run the pick with `Menu(VIEW)` and leave the guard's timer inactive, as when it fired; expect the "still open" error.
  - **Resolution: done**.
    - **Test:** `test_a_menu_the_guard_had_to_close_is_a_failure` (the pick runs with the menu open, the guard's timer
      then inactive: the "still open" error) and `test_a_menu_closed_by_the_pick_alone_is_no_failure`; a mutant with
      `held = False` failed the first.
- [x] **TST-327 · collapse_package.py takes the first Explorer dock, visible or not · follows TST-324, generation 2** · `tests/test_all_tools/editor_panels_and_fit/designer_scripts/collapse_package.py:17` · confirmed · found 2026-11-12
  - **Defect.** `next(d for d in mw.findChildren(QtWidgets.QDockWidget) if d.objectName().startswith('areaA_'))` has no `isVisible()`, the pattern TST-324 fixed in `parameters_panel.py` and its Also covered didn't list; the tool's `_explorer_tree` takes the visible one.
  - **Scenario.** With a hidden Explorer dock found first, the script collapses that one's tree and prints `COLLAPSED=True`, and the check passes without the visible package collapsed.
  - **Fix.** `and d.isVisible()`.
  - **Resolution: done**.
    - **Fix:** `collapse_package.py` takes the visible Explorer dock; `check_graph_finds_its_row_in_a_collapsed_package`
      passes with it (scratch run).
- [x] **TST-328 · Two sentences that say other than the code · follows TST-321, generation 2** · `mcp_server/server_tools/views.py:69-70`, `tests/test_all_tools/editor_panels_and_fit/checks.py:39-41, 101, 112`, `ROADMAP.md` item 7 · confirmed · found 2026-11-12
  - **Defect.** "outputs added to the graph open in the editor don't reach it until Designer switches graphs" reads as any switch, where switching to another graph puts that one's outputs on the mesh (the module docstring: "until it switches again", to that graph), and no check measures the "until" (the designer fact measures that they don't arrive); the zoom check's docstring says each call "passes only what it changes", but `tiled` passes `view='Top'` again.
  - **Scenario.** An agent switches to another graph and back expecting the outputs, or to another graph alone; a reader trusts the check's docstring.
  - **Fix.** "don't reach it by themselves" in the tool's docstring, the check's docstring and item 7; drop `'view': 'Top'` from `tiled` (the camera then also shown to stay across a tiling call) or the parenthetical.
  - **Resolution: done**.
    - **Fix:** "don't reach it by themselves" in the tool's docstring, the designer fact's docstring and ROADMAP item
      7; `tiled` passes only `tiling` now, the zoom check passing with it (scratch run).
- [x] **TST-329 · GUIDE's scripting line gives the tool's mechanism without its hazard** · `mcp_server/GUIDE.md:330-333` · confirmed · found 2026-11-12
  - **Defect.** "the Explorer's context menu (a `QContextMenuEvent` on the Explorer's tree only, its action picked by a `QTimer` while the menu runs; ...)" is how the tool works around Designer, which AGENTS.md's table keeps in the module's docstring (the guide keeping a line and the path), and read as a recipe it leaves out what HLP-108 found: an open menu holds the job and the bridge, and an abort can skip a Python timer's slot.
  - **Scenario.** An agent writing Qt code copies the pattern without a guard; its slot fails, the menu stays open, and the bridge is held until someone clicks.
  - **Fix.** Drop the mechanism, or replace it with "an open menu holds the bridge until it closes"; keep the path.
  - **Resolution: done**.
    - **Fix:** GUIDE's line keeps what the tool drives and the path, with the hazard ("an open menu holds the bridge
      until it closes") in place of the mechanism.
- [x] **HLP-116 · An abort during a step's wait, or the last one, still says nothing of what was set · follows HLP-113, generation 3** · `mcp_server/designer_helpers/view3d.py:359-388`, `tests/unit/test_view3d_helpers.py` (`test_an_abort_before_any_change_says_nothing`) · confirmed · found 2026-11-12
  - **Defect.** Each step triggers its change, then waits (`_settle(0.5)` after the mesh, 1.0 after the outputs, `VIEW_TURN` and 0.3 for the view, `_wheel`'s pauses), and only then appends it to `done`; the last `_settle(0.5)` and the print are after the `try`. The waits are traced loops taking most of the set-up's time, so most aborts land in one: the change is made and not said. `test_an_abort_before_any_change_says_nothing` raises in the up-front lookups, before the `try`, so it never reaches the `if done:` it is named for.
  - **Scenario.** `screenshot_designer('3d', mesh='Plane')` cancelled during the mesh's wait: the mesh changed, the reply is the bare `ScriptAborted`; `zoom=10` cancelled midway: some steps applied, none said; any abort in the last 0.5 s: everything set, nothing said.
  - **Fix.** Record each step as it is triggered (a "while setting ..." note for the step under way) and move the last wait inside the `try`; the test's name narrowed to what it covers (the follow-up rules, generation 3), or its abort moved to the first trigger.
  - **Resolution: done**.
    - **Test:** `test_an_abort_during_a_steps_wait_says_that_step` (an abort in the mesh's wait: nothing printed
      before), `test_an_abort_in_the_last_wait_says_all_that_was_set` (nothing printed before) and the updated
      `test_an_abort_after_a_change_says_what_was_set_and_goes_on`; the test named for an abort before any change
      renamed to what it covers (`test_an_abort_while_the_menus_are_looked_up_says_nothing`). The live set-up check's
      abort part now expects the step under way: it failed before the fix ("then stopped" alone) and passes after.
    - **Cause:** a step was recorded only after its wait, and the last wait was outside the `try`.
    - **Fix:** `set_3d_view` notes each step as it starts (`doing`) and the abort's line says "then stopped while setting
      ..."; the last wait is inside the `try`.
  - Questioned by HLP-119 (2026-11-12).
- [x] **HLP-117 · An API error after a change is reported as an abort · follows HLP-113, generation 3** · `mcp_server/designer_helpers/view3d.py:379-388` · confirmed · found 2026-11-12
  - **Defect.** `except Exception` doesn't catch the sd API's `APIException`, a `BaseException` (GUIDE.md: use `except (Exception, APIException)`), so it falls into the branch commented "an abort" and prints "...; then stopped".
  - **Scenario.** `mesh='Plane', graph='g'` where `g.compute()`, `setExplorerSelection` or `openResourceInEditor` raises an API error: the agent gets the error with "3D view: Plane; then stopped", which reads as a cancel, not "...; the 3D view was already set: Plane".
  - **Fix.** `except (Exception, APIException) as e:`, with a unit test raising an API error after the mesh changed.
  - **Resolution: done**.
    - **Test:** `test_an_api_error_after_a_change_says_what_was_set` (the helpers' fixture now gives `APIException` as
      Designer has it, a `BaseException`): before the fix it came out as the API error itself, through the abort branch.
    - **Fix:** `except (Exception, APIException) as e:`.
    - **Also covered:** no other `except Exception` in the branch's code.
- [x] **HLP-118 · A clean-up's `finally` entered without an abort runs traced, so one landing on its first lines skips it · follows HLP-112, generation 3** · `mcp_server/designer_helpers/view3d.py:237-239` (`_apply_outputs`), `:299-301` (`_set_tiling`) · confirmed · found 2026-11-12
  - **Defect.** HLP-112 closed the window before each `try`; a `finally` reached normally is traced too, so an abort landing on `for timer in timers:` or on `_switched(...)` skips the rest of it. `pick` closes over `timers` and its connection keeps it alive, so a timer not stopped outlives the job (review 2's probe 5 measured that).
  - **Scenario.** After a pick that worked, the guard left active closes up to five popups within 5 s after the job, the user's menu or the next job's Explorer menu (which then reports "didn't open"); in `_set_tiling`, the panel is left on the 3D material. A window of a few traced events.
  - **Fix.** Give the timers a parent `QObject` held only by the function's frame, so they are deleted with it whatever runs of the `finally`; in `_set_tiling`, `_parameters_back` in a `finally` of its own around `_switched`.
  - **Resolution: done**.
    - **Test:** `test_the_timers_go_with_the_function_whatever_runs_of_its_finally` (the timers made with a parent;
      none before) and `test_an_abort_escaping_the_tiling_turns_the_panel_back` (no turn-back before), unit; the live
      designer fact `check_a_timer_goes_with_the_parent_its_function_held`: a timer never stopped, its slot holding it,
      fired 15 more times after its function returned with no parent, and 0 with a parent the function held alone.
    - **Cause:** a `finally` reached without an abort runs traced, and nothing else stopped what it skipped.
    - **Fix:** `_apply_outputs`' timers have a parent `QObject` held by its frame alone, so they go with it whatever
      runs of the `finally`; `set_3d_view`'s abort handler, which runs untraced, turns the Parameters panel back when
      the tiling step was under way.
  - Questioned by HLP-119 (2026-11-12).
- [x] **TST-331 · Docstrings that say more than the code and its checks · follows HLP-115 and HLP-114, generation 3** · `tests/test_all_tools/lifecycle/checks.py` (`check_the_3d_view_waits_for_a_graph`), `mcp_server/designer_helpers/view3d.py:6, 27, 312-315` · confirmed · found 2026-11-12
  - **Defect.** The lifecycle check says "only a Designer of its own can show it: no other category's has never opened a graph", but in a pool most categories' Designers never open one (DECISIONS.md: "most never open their graph"); HLP-115's resolution repeats it. `set_3d_view`'s docstring says the menu entries it needs are checked before anything changes, but with `mesh=` and `tiling=` the new mesh's material and Edit properties are found after the mesh changed (the comment below says so). The module docstring's "(before, its dock is empty)" says more than probe 6 of review 2 measured (no menu bar, no viewport), and "until the mesh uses it" more than any probe saw.
  - **Scenario.** A maintainer puts checks needing a fresh Designer only in lifecycle's lock window; a reader of `set_3d_view` expects nothing to change before a refusal of the new mesh's material.
  - **Fix.** Narrow each (the follow-up rules, generation 3): "measured right after its Designer starts, before any graph is opened"; "(with mesh=, the new mesh's material once it shows)"; "(before, it has neither)"; "is listed "(unused)""; a note under HLP-115.
  - **Resolution: done**.
    - **Fix:** the lifecycle check: "measured right after its Designer starts, before any graph is opened"; `set_3d_view`'s
      docstring: "(with mesh=, the new mesh's material once it shows)"; the module docstring: "(before, its dock has
      neither)", 'is listed as "(unused)"'; a note under HLP-115.
- [x] **TST-332 · The tool's docstring doesn't say tiling= turns the user's Parameters panel to the graph in the editor** · `mcp_server/server_tools/views.py:68-74` · confirmed · found 2026-11-12
  - **Defect.** It says the set-up stays in the user's view, about the 3D view, and that `graph` selects it in the Explorer, but not that `tiling` leaves the Parameters panel on the graph in the editor instead of the node they had selected (DECISIONS.md's entry); an agent learns it from the result line, after the call.
  - **Scenario.** An agent working in the user's Designer uses `tiling=` without telling them their panel will change.
  - **Fix.** A few words: "tiling: ...; the Parameters panel then shows the graph in the editor".
  - **Resolution: done**.
    - **Fix:** the tool's docstring: "tiling: how often the material repeats on the mesh (the user's Parameters panel
      then shows the graph in the editor)".
- [x] **HLP-119 · An abort between two steps, or on the last line, still misreports what was set · follows HLP-116, generation 4** · `mcp_server/designer_helpers/view3d.py:369-403` · confirmed · found 2026-11-12
  - **Defect.** `doing` isn't cleared when its step is appended to `done`, so an abort landing on the next step's `if` line (or on `doing = ''` after the tiling) says "...Plane; then stopped while setting Plane"; the final `print` is after the `try`, so an abort on that line says nothing; an abort landing in the traced `except (Exception, APIException)` handler escapes the abort handler and loses "already set"; and the abort handler turns the panel back before it prints, so an error there would lose the line.
  - **Scenario.** `screenshot_designer('3d', mesh='Plane', tiling=2)` cancelled as the mesh's wait ends: "3D view: Plane; then stopped while setting Plane"; cancelled on the last line: everything set, nothing said. Each a window of one traced event.
  - **Fix.** End the class rather than its next window: print a note before each change (e.g. "3D view, setting: Plane"), so no abort can land between a change and its record, and have the server add those notes to an error, keeping only the summary line on success; in the abort handler, print before turning the panel back.
  - **Resolution: done**.
    - **Test:** `test_each_step_is_said_before_its_change` (the order of notes and triggers; the summary used to be the
      only print), the abort tests updated to the notes (`test_an_abort_after_a_change_says_what_was_set_and_goes_on`,
      `test_an_abort_during_a_steps_wait_says_that_step`, `test_an_abort_in_the_last_wait_says_all_that_was_set`), and
      `test_a_set_up_that_stopped_says_the_steps_it_began` (server), each failing before the fix; the live set-up
      check's abort part, failing before (the old "then stopped while setting" line) and passing after, the whole
      `editor_panels_and_fit` category with it (35 checks, scratch run).
    - **Cause:** what was set was recorded after each change and said in one print at the end, so every line between a
      change and its record was a window.
    - **Fix:** `set_3d_view` prints "3D view, setting: <step>" before each change and the summary before its last wait;
      the abort handler only turns the Parameters panel back (when the tiling step began), printing nothing;
      `screenshot_designer` adds to an error the summary if there is one, else the steps begun, and returns only the
      summary beside the image; its docstring says "stopped partway, the steps it began".
- [x] **TST-333 · Pointers to the checks that miss what this branch added · follows HLP-115, generation 2** · `tests/test_all_tools/editor_panels_and_fit/checks.py:1` and `run`'s docstring, `mcp_server/designer_helpers/view3d.py:3-4` · confirmed · found 2026-11-12
  - **Defect.** The category's module docstring and `run`'s say "every panel's screenshot, the clipboard, then fitting the whole graph", though `run` now ends with the 3D view's checks (README.md and `categories.py` say so); `view3d.py` says `editor_panels_and_fit` checks what the tool relies on, but its first point (the 3D view built once a graph is opened) is checked in `lifecycle`, as `editor_panels_and_fit`'s preparation opens a graph first.
  - **Scenario.** A maintainer looking for the 3D view's checks, or for the check of that fact, is sent to the wrong place.
  - **Fix.** "..., then the 3D view set up" in both docstrings; "...editor_panels_and_fit checks what the tool relies on, lifecycle the first point".
  - **Resolution: done**.
    - **Fix:** the category's module docstring and `run`'s end with "then the 3D view set up"; `view3d.py`'s pointer
      names lifecycle for its first point.
- [x] **TST-334 · The failed shot's error the set-up check adds is cut from its printed line · follows HLP-107's note, generation 2** · `tests/test_all_tools/editor_panels_and_fit/checks.py:278-283`, also `:58`, `:118` · confirmed · found 2026-11-12
  - **Defect.** `common.check` prints a detail's first 150 characters (`common.py:62`), and the set-up check's text before the appended error is about 145 (the Parameters panel's error in a list, " | the render changed 255.0 grey levels"), so the error added after HLP-107's unexplained failure shows its first five characters; `difference` also gives 255.0 for two images of two sizes, when nothing is appended. The same cut hides a failed shot in `check_the_3d_view_zooms_and_tiles` (the base shot's set-up line alone is about 142 characters) and leaves about 51 for the third shot in the designer fact on outputs added to the open graph.
  - **Scenario.** The failure in HLP-107's note happens again, in the full run: the line ends "255.0 grey levels | Error" and the cause is lost a second time; HLP-107's note says the check now prints it.
  - **Fix.** Print a failed shot's error on a line of its own (as `common.normal_close` does, "as a check's detail is cut"), say the two sizes when both are images, join only the shots that failed, and add a note under HLP-107.
  - **Resolution: done**.
    - **Test:** `test_a_failed_shot_is_said_whole_on_a_line_of_its_own`, `test_two_shots_of_two_sizes_are_said` and
      `test_shots_that_worked_say_nothing` (`tests/unit/test_selftest_renders.py`), failing before (no helper).
    - **Fix:** `renders.say_failed` prints each failed shot's whole error on a line of its own, or the sizes of two
      images of two sizes; the set-up check, `check_the_3d_view_zooms_and_tiles` and the designer fact on outputs added
      to the open graph call it, their check's detail saying "a shot failed (below)".
