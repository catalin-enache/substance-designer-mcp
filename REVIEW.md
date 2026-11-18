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
`mcp_server/server.py`, `server_tools/` and `designer_preferences.py`, **HLP** `mcp_server/designer_helpers/`, **INS** installer, uninstaller,
command-line client, example and `scripts/`, **TST** tests and docs. A new area gets a new prefix, added here.

**Last used:** PLG-45, SRV-183, HLP-206, INS-46, TST-556.

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
| Medium | 0 | 0 |
| Low-medium | 0 | 2 |
| Low | 0 | 39 |
| **Total** | **0** | **41** |

## Review log

### 2026-11-18: the environment-light branch against main (ROADMAP item 73, the diff only, uncommitted)
- **How:** three reviewers read the diff, one area each: the helpers (`designer_helpers/view3d.py`, `shot3d.py`), the
  server and the docs (`server_tools/views.py`, README.md, GUIDE.md, ROADMAP.md), and the tests (unit, live, the designer
  facts script). No tests run. The lead agent settled each suspicion by reading, or with scratch probes, one at a time
  in a Designer it started, running the branch's helpers (their joined source) on graphs of its own
  (`mcp_probe_review`, `mcp_probe_review2`), then quit. Settled as wrong:
  - The ranges clamped by Designer's spin boxes (server reviewer; tests reviewer, for a negative rotation): measured
    while the branch was built, Exposure's and Turns' spin boxes go from -3.4e38 to 3.4e38, Degrees' from -1.2e41 to
    1.2e41, and -45 degrees was taken (Turns -0.125).
  - The Exposure lookup taking a field named `intensity` of the user's graph or node (helpers reviewer): a graph with an
    input `intensity` open in the editor, then its Blur node shown in the Parameters panel by a left click. Each time,
    0.1 s after Environment > Edit properties the panel showed the environment, and only its field matched; the
    graph's and the node's own `intensity` fields have no spin box, which the lookup requires. The real
    `set_3d_view(environment_exposure=2.0)` left the graph's input at 0.5.
  - A rotation and an exposure set after a map's drop in the same call not taken (helpers reviewer):
    `set_3d_view(environment='studio_white_hard_sunlight', environment_rotation=45.0, environment_exposure=1.25)`, then
    the panel built again read Exposure 1.25 and 45 degrees (0.125 turns), one `intensity` field.
  - The drop's QMimeData freed while Designer still uses it (helpers reviewer): with a real drag, QDrag owns its mime
    data and deletes it once the drop is over, so Designer can't keep it either.
  - The field's poll a fixed-time wait (helpers reviewer): the poll is `_tiling_spin`'s 100 ms one, moved into
    `_panel_field`, which `tests/unit/test_frames3d.py` keeps on purpose.
  - Maps that may not signal within their drop (helpers reviewer, the 14 MB map and the only `.hdr`): each of the 34
    maps, dropped after another, made the Environment field signal exactly once within the drop, each drop returning
    within 0.01 s.
  - A Designer an agent started inheriting the user's exposure, which the designer fact would read as Designer's
    default (tests reviewer): the environment isn't in the preferences plist (only `session.view3d.layout`) nor in the
    agent's `user_preferences.xml`; a Designer quit at Exposure 1.25 and 45 degrees started again at 0 and 0.
- **Not verified:** none.
- **Resolutions assessed:** none in scope (REVIEW.md was cleaned up after the last merge).
- **Findings:** 10: Low-medium SRV-181; Low SRV-182, HLP-189, HLP-190, HLP-191, TST-537, TST-538, TST-539, TST-540,
  TST-541. Generation 1 each.
- **Suggested order:** SRV-181 (an agent reads the rotation as relative), then HLP-189, HLP-191 and HLP-190 (what the
  tool says when a step fails), then the tests and docs (TST-538 to TST-541, SRV-182, TST-537).
- **Simplifications:** none beyond the fixes.
- **Checked and found fine:**
  - The refusals before anything changes: an unknown map, a hidden Parameters panel, a missing Environment > Edit
    properties.
  - The abort handler's `panel_begun`, and `_in_properties`' `finally` after an abort in `show` or `setting`.
  - The flag timers: C++ slots only, parented to an object only the frame holds.
  - The server's options: `''`, 0, NaN and the bounds, a rotation or exposure of 0 given and sent, refused with another
    panel. The call string `', '.join(map(repr, setup))`, a map name with a space ("studio 02") included. The lines
    returned beside the image, the begun lines when the set-up stops partway.
  - The designer facts script: its own code, SIGNALLED counted within the drop, its slot disconnected in its
    `finally`.
  - DECISIONS.md: the Parameters panel goes back to the graph in the editor, as decided for the tiling.
- **Longest chain still growing:** none (generation 1).

### 2026-11-18: the environment-light branch against main, second review (the diff only, uncommitted)
- **How:** three reviewers read the diff, one area each, as in the first review: the helpers, the server and the docs,
  and the tests. No tests run. The lead agent settled each suspicion by reading, or with scratch probes, one at a time
  in a Designer it started, running the branch's helpers (their joined source, through `client/sd_run.py`) on graphs
  of its own (`mcp_probe_review2b` to `mcp_probe_review2e`), then quit. Settled as wrong:
  - A drop marking the user's package modified or linking the map into it (helpers reviewer): a saved package with its
    graph in the editor read `isModified()` False and one resource before, after one drop, and after the same map
    asked again (two drops).
  - A drag entered and moved but never dropped, as an abort inside `_drop` would leave it (helpers reviewer): the render
    after it matched the one before (0.00 grey levels), and the next set-up's drop was taken (the render changed 6.62).
  - Reset Environment turning the Parameters panel, which `RESET_ENVIRONMENT` doesn't turn back (tests reviewer): the
    panel's title was the graph's before and after the reset; the fields then read 0 degrees and exposure 0.
  - The guide's "to see relief lit from the side" as an unmeasured claim (server reviewer): it says what the option is
    for, not what a render shows; the first review left that advice to the guide on purpose (SRV-182's fix).
  - The Library's HDRI environments not being the 34 files of `view3d/maps` (server reviewer): measured while the
    branch was built.
  - `SIZES`' smallest map being the last of the others (tests reviewer): the code picks it by size, and no rule it could
    fall back to picks the last; TST-538 asked only that it not be the first.
- **Not verified:** none.
- **Resolutions assessed:** the first review's 10, all done. Each test exists, fails without its fix by reading, and
  was seen failing against a mutation, as its resolution says. Questioned: SRV-181 (TST-542: the guide repeats the
  parameter), HLP-191 (HLP-193: an error after the map's drop), TST-539 (TST-545: the facts beside it), TST-540
  (TST-544: two conditions that two sizes still pass).
- **Findings:** 12: Low-medium HLP-192; Low HLP-193, HLP-194, SRV-183, TST-542 to TST-549. Generation 2: HLP-193,
  TST-542, TST-544, TST-545; the others generation 1.
- **Suggested order:** HLP-192 (a shot taken before the last change is drawn), HLP-193, SRV-183, then the tests
  (TST-544 to TST-549), then the docs (HLP-194, TST-542, TST-543).
- **Simplifications:** none beyond the fixes.
- **Checked and found fine:**
  - The fixes of HLP-189, HLP-190 and HLP-191: `_panel_field` and `_panel_spin` keep the tiling's lookup (the exact
    `$tiling` match, the 100 ms poll, `keep`); the signal checked before any drop; the line printed before the other
    map's drop comes back only when the set-up stops partway.
  - `difference()`'s NaN in every caller, and the `near < 3.0 and near < 0.5 * far` rewrites, equal to the `min()` form
    for any number.
  - views.py: NaN and infinity refused, 0 sent as given, '' as none, the call's order, ±180 and ±10 taken.
  - The live check: the reset in its `finally`, `apart()`, each "stays" condition seen failing (SRV-181, TST-539).
  - The unit fakes: `_drops`' faked QtCore is new for each test; HLP-189's test fails on any drop.
  - Designer's maps folder: 34 files, 33 `.exr` and one `.hdr`, no two of one name.
- **Longest chain still growing:** generation 2 (SRV-181 → TST-542, HLP-191 → HLP-193, TST-539 → TST-545, TST-540 →
  TST-544).

### 2026-11-18: the environment-light branch against main, third review (the diff only, uncommitted)
- **How:** `/simplify` ran first, on the refactor that added `_waited_for` and `_frames_of`; its altitude reviewer
  raised one suspicion (HLP-200). Then three reviewers read the diff, one area each: the helpers, the server and the
  docs, and the tests. No tests run. The lead agent settled each suspicion by reading, or with scratch probes, one at a
  time, in a Designer an agent started, through a fresh MCP server running the branch's helpers (`alone.run`) on the
  self-test's graphs (`mcp_selftest_view3d_plain`, cleaned up after). Settled as wrong:
  - `MESH_THEN_TILING` passing blind on a second run, a tiling of 2 left on the Sphere's material (tests reviewer): with
    the Sphere's tiling set to 2, then the Plane's to 1, the Sphere read 1, so the check's clean-up leaves none behind.
  - No test of a mesh shown already answering "no change" (tests reviewer): `test_a_set_up_says_whether_it_changed_what_the_view_shows`
    has the case `({'mesh': 'Sphere'}, True, False)`. The live `SHOWN_ALREADY` not looking for STALE needs nothing
    more then.
- **Not verified:** none.
- **Resolutions assessed:** SRV-183, HLP-192 to HLP-198 and TST-542 to TST-549 hold as their resolutions say. Each
  test exists and fails without its fix, by reading. Questioned: HLP-193 (HLP-200), HLP-195 (HLP-199, HLP-201,
  TST-551), HLP-196 (HLP-203), HLP-198 (TST-551).
- **Findings:** 9, all Low: HLP-199 to HLP-203, TST-550 to TST-553. Generation 3: HLP-200, a defect in the tools'
  code. Generation 2: HLP-199, HLP-201, HLP-203, TST-551. The others are generation 1.
- **Suggested order:** HLP-201 and HLP-202 (a second's wait for nothing, and a STALE warning that misleads), HLP-200,
  HLP-199, then the tests (TST-551, TST-552), then the docs (HLP-203, TST-550, TST-553).
- **Simplifications:** `/simplify` applied two: `run`'s unused default, and four live-check snippets building their
  watch with `_frames_of`. It skipped `_frames_of` as a closing context manager (those snippets use the watch
  directly) and two helpers with one user each today (`_settled_from`, `_checked_on`).
- **Checked and found fine:**
  - The refactor: each path of `run` builds and closes one watch, as before. `_waited_for` marks before every lookup
    inside its change, as before. The abort handler and `_tool_back`'s `finally` are unchanged. `_Frames` is looked up
    at call time, so the unit tests' patches reach it.
  - `changed` for each step (a value shown already, a mesh checked, moves; a view and a graph not counted), and
    `may_change` against what the run can change. views.py's STALE sentence matches shot3d.py's text.
  - DECISIONS.md's two entries match the code: `on_screen = moving or g is not None or switching`, and every
    environment option goes through Environment > Edit properties.
  - The helpers, checks and decisions ROADMAP.md's new rules name exist.
  - The four `_frames_of` snippets build what they built before. `_SWITCHED` passes on the run's answer and
    `may_change`. `STALE_SET_UPS` gives one verdict whatever exposure an earlier check left.
- **Longest chain still growing:** generation 3 (HLP-191 → HLP-193 → HLP-200).

### 2026-11-18: the environment-light branch against main, fourth review (the diff only, uncommitted)
- **How:** three reviewers read the diff, one area each: the helpers, the server and the docs, and the tests. No tests
  run. The lead agent settled each suspicion by reading, or with scratch probes, one at a time, in Designers an agent
  started, through a fresh MCP server running the branch's helpers (`alone.run`) on a graph of its own
  (`mcp_selftest_probe_drop`, cleaned up after). Settled as wrong:
  - A first drop of a map not shown going untaken, so that `_drop_map`'s False skips the wait of a map that changed
    (helpers reviewer; HLP-201's skip). Every first drop of a map not shown was taken. In a Designer just opened,
    hidden, its 3D view never drawn, `_drop_map` took three maps at their first drop. Then `set_3d_view(environment=...)`
    took one map before a 3D shot and two after it, Designer hidden, each in one drop, and one more after a shot that
    set the map itself. The first review saw 34 of 34 on screen. The fallback for an untaken drop is defensive.
    A first probe's second half, calling `_drop_map` from a snippet of its own after a shot, raised "the 3D view took
    no environment map dropped on it". The tool's own call above didn't reproduce it, and what differed wasn't found.
- **Not verified:** none.
- **Resolutions assessed:** HLP-199, HLP-201, HLP-202, TST-551, TST-552 and TST-553 hold as their resolutions say.
  Questioned: HLP-200 (HLP-204, HLP-205, TST-555), HLP-203 (HLP-205), TST-550 (TST-554), HLP-199's ROADMAP part
  (TST-554), HLP-202's live check (TST-556).
- **Findings:** 5, all Low: HLP-204, HLP-205, TST-554, TST-555, TST-556. Generation 4: HLP-204, a defect in the tools'
  code, and TST-555, test only, whose fix narrows. Generation 3: HLP-205 and TST-554, docs only, whose fixes narrow.
  Generation 2: TST-556.
- **Suggested order:** HLP-204, then TST-556 and TST-555, then the docs (HLP-205, TST-554).
- **Simplifications:** none beyond the fixes.
- **Checked and found fine:**
  - `_Waiting` on an error or an abort inside it: no wait, the error goes on. On one in `__exit__`, the step is
    already in `done`. `changed` on every path. Nothing appends between the viewpoint's two records.
  - `_Waiting.since` is typed `tuple[int, int]`; the unit fakes' int marks are only stored and passed back.
  - Item 83's follow-up matches the code: `settled` and `__exit__` return nothing, STALE is said on identical pixels
    alone, and the retake's `next_frame` waits up to NO_RESTART.
  - Every name the docs cite exists. Nothing outside REVIEW.md names `_mesh_shown` or `_waited_for`.
  - The `Shot` fake's `may_change` without the `_mesh_shown` patch. `SHOWN_ALREADY`'s clean-up in its `finally`.
    `difference()`'s NaN fails `apart == 0`.
- **Longest chain still growing:** generation 4 (HLP-191 → HLP-193 → HLP-200 → HLP-204, TST-555).

---

## High

## Medium-high

## Medium

## Low-medium

- [x] **SRV-181 · The docstring and the guide read environment_rotation as a turn from where the light is; the code sets the angle** · `mcp_server/server_tools/views.py:97-98`, `mcp_server/GUIDE.md:49` · confirmed · found 2026-11-18
  - **Defect.** The docstring says "environment_rotation: degrees it turns around the mesh", and the guide
    "`environment_rotation` turns the light around the mesh", right beside `orbit`, "degrees the camera turns around
    the point it looks at", which is relative ("pan, orbit and zoom move from where the camera is"). The code sets the
    field to the value: `_set_environment` commits `rotation` into the Degrees spin box (`_commit` calls
    `spin.setValue(value)`).
  - **Scenario.** An agent calls `environment_rotation=45` twice, expecting the light turned 90 degrees, and gets 45. No
    check tells the two apart: the live check goes from 0 to 90, where both readings give the same render.
  - **Fix.** Say it is the angle the environment is set to, not added to the current one, unlike `orbit`, in the
    docstring and the guide. A live check could set 90 twice and see the render stay.
  - **Resolution: done** (2026-11-18). **Test:** the live check
    `check_the_environment_turns_brightens_and_changes_the_light` sets 90 degrees twice and requires the render to stay
    (under 2 grey levels) with "rotation 90 degrees" said. The code already set the angle; the defect was the text, so
    the check was seen failing in a scratch run with the helpers mutated to add the rotation to the angle shown (12.3
    grey levels), then passing without (0.0). **Cause:** the docstring and the guide said "turns", the word `orbit`
    uses for a move from where the camera is. **Fix:** the docstring says "the angle in degrees it is set to around
    the mesh, -180 to 180 (not added to the angle before, unlike orbit)"; GUIDE.md "sets the light's angle around the
    mesh (not a turn from where it is)". **Also covered:** README.md's Tools row said "turned", now "its angle";
    `set_3d_view`'s and `_set_environment`'s docstrings say "rotation in degrees", which reads either way, left.
  - Questioned by TST-542 (2026-11-18).

- [x] **HLP-192 · One wait covers the environment's three changes, and it can end before the last one is drawn** · `mcp_server/designer_helpers/view3d.py:978-983`, `:627-638` · measured · found 2026-11-18
  - **Defect.** `since = watched.mark()` is taken once before `_set_environment`, which drops the map, then commits the
    rotation, then the exposure, each after a lookup that polls at least 100 ms. `watched.settled(since)` ends at the
    first count back at the target after the first restart since the mark (`_Counts.restart` and `_after_restart`,
    `frames3d.py`), so its condition can hold before the last change is drawn. Found by the helpers reviewer.
  - **Scenario (measured).** A probe ran `shoot_3d` with `studio_white_hard_sunlight`, 90 degrees and exposure 2, after a
    shot under `studio_black_soft_light` at 0 and 0, recording the view's counts. The map's and the rotation's restart
    came at paint 8, the count was back at 8 at paint 17, and the exposure was committed at paint 18 (a second run: 13,
    22, 23). With a graph in the editor, the Parameters panel's turn-back lasted until the view settled again, and the
    shot matched one taken after it (0.00 grey levels). With nothing after the last commit, as with no graph in the
    editor (`_parameters_back` then does nothing and `_switched` returns at once; simulated by replacing both),
    `settled` returned at the commit's own paint, before the view drew the change. The shot then differed from a
    settled one by 1.78 grey levels on average, 112 at most (two runs alike), said set with no STALE line (`moving`
    leaves the environment out).
  - **Fix.** Wait from a mark taken before the last change, as the orbit, pan and zoom steps do (REVIEW.md HLP-161):
    give `_set_environment` the watch and mark right before each change, waiting from the last mark.
  - **Resolution: done** (2026-11-18). **Tests:**
    `test_each_change_through_the_parameters_panel_is_waited_for_from_just_before_it[environment]`
    failed with one wait for three changes (the marks waited from `[1]`, the changes at `[1, 2, 3]`). The live
    `check_a_3d_shot_setting_the_whole_environment_waits_for_its_last_change` sets the whole environment in one shot
    with nothing after its last change, as with no graph in the editor (`NOTHING_AFTER`), then saves the view as it
    settled, both through `shoot_3d`. It failed in its scratch run at 1.20 grey levels apart (under 0.5 required) and
    passed at 0.00 after the fix. In its final form, a mutation removing the exposure's wait made it fail at 7.70.
    **Cause:** the run took one mark before the three changes, each made after a lookup that lets the view draw, and
    `settled`'s condition (the count back at the target after the first restart since the mark) held before the last
    change. **Fix:** `_set_environment` takes the watch, marks right before each change and waits after it; the run's
    environment step no longer waits itself. A value its spin box shows already is neither committed nor waited for,
    as its wait would only run to its limit
    (`test_a_value_the_parameters_panel_shows_already_is_neither_committed_nor_waited_for[environment]`,
    seen failing against a mutation). **Also covered:** the run's other steps make one change for each mark (mesh,
    the view's turn and Frame, tiling), or mark before each option (orbit, pan and zoom: HLP-161). The graph step
    computes the graph and applies its outputs under one mark; only the outputs applied reach the mesh (the module
    docstring). `_drop_map`'s drops run back to back with no event between them, so the view draws only the last.

## Low

- [x] **SRV-182 · views.py repeats a fact the helpers' docstring holds, and states two the tests don't check** · `mcp_server/server_tools/views.py:18`, `:98`, `:114` · confirmed · found 2026-11-18
  - **Defect.** Three sentences, against AGENTS.md's one place for each fact and no claim without a test:
    - `# Designer's fields take any number (a rotation isn't wrapped: 1.75 turns stays 630 degrees)` repeats
      `designer_helpers/view3d.py`'s module docstring.
    - `# where Designer's fields go, 0 their default` says the rotation's default is 0 too. Only the Exposure's is
      checked (the designer fact's BEFORE=).
    - The tool docstring's "(relief shows best lit from the side)" repeats GUIDE.md's "Look" bullet, in the text agents
      pay for with every session.
  - **Scenario.** A later change to one copy leaves the other saying something else; the rotation's default is taken
    as checked.
  - **Fix.** Point to `designer_helpers/view3d.py` instead of repeating its fact, say only Exposure's default (or check
    the rotation's), and leave the advice to the guide.
  - **Resolution: done** (2026-11-18). **Test:** none: the claims were removed, not tested. **Fix:**
    `views.py:17-18` gives the limits as the tool's own and points to `designer_helpers/view3d.py` for Designer's
    fields; `:115` says "values Designer's fields are set to, 0 included", no default claimed for the rotation; the
    docstring's "(relief shows best lit from the side)" is left to GUIDE.md's "Look" bullet. **Also covered:**
    `tests/unit/test_view3d.py`'s comment said "0 their default" too, rewritten the same way.

- [x] **HLP-189 · `_drop_map` doesn't check that the Environment field's signal got connected** · `mcp_server/designer_helpers/view3d.py:584` · confirmed · found 2026-11-18
  - **Defect.** `QtCore.QObject.connect(field, QtCore.SIGNAL('valueChanged()'), flag, QtCore.SLOT('start()'))`'s
    result is never looked at. If the field found has no such signal (another widget of that name, a later Designer),
    no flag ever starts, though each drop changes the map.
  - **Scenario.** The map asked for is dropped and taken, unseen; the smallest other map is dropped and taken, unseen;
    the call raises "the 3D view took no environment map dropped on it" and leaves the 3D view on a map nobody asked for.
  - **Fix.** Before any drop, refuse unless the connection is valid (the Connection returned, or
    `field.metaObject().indexOfSignal('valueChanged()') >= 0`), as `_commit` refuses a spin box with no
    valueChanged().
  - **Resolution: done** (2026-11-18). **Test:**
    `test_an_environment_field_with_no_valuechanged_is_refused_before_any_drop` (a field whose meta-object has no
    `valueChanged()`, each drop failing the test) failed with "the 3D view took no environment map dropped on it",
    after two drops. **Cause:** nothing looked at whether the field has the signal, and the connect's result can't
    tell: a probe in the agent's Designer connected a plain QWidget's `valueChanged()` by its signature and got a
    Connection whose `bool()` is True, as for the Environment field. `indexOfSignal('valueChanged()')` gave 33 for the
    field and -1 for the plain QWidget. **Fix:** `_drop_map` refuses before any drop when the field's
    `indexOfSignal('valueChanged()')` is negative: "the Environment field has no valueChanged() signal, which says a
    map was taken". The live checks still pass (the real field isn't refused). **Also covered:** no other connection by
    signature in the helpers; `_commit` already refuses a spin box without `valueChanged()`.

- [x] **HLP-190 · With no graph in the editor, the environment step says the panel shows the 3D material** · `mcp_server/designer_helpers/view3d.py:489-493` · confirmed · found 2026-11-18
  - **Defect.** `_parameters_back` returns `"the Parameters panel shows the 3D material's properties"` when there is no
    graph in the editor, written for the tiling; `_in_properties` returns it for the environment step too.
  - **Scenario.** No graph in the editor (the 3D view built by one opened earlier, since closed): a shot with
    `environment_exposure=1` says "(the Parameters panel shows the 3D material's properties)" while the panel shows the
    environment's.
  - **Fix.** Pass what the panel was turned to (the material or the environment) to `_parameters_back`, or let
    `_in_properties` say it.
  - **Resolution: done** (2026-11-18). **Test:**
    `test_with_no_graph_in_the_editor_the_panel_is_said_to_show_what_was_set`, for the tiling and the environment:
    the environment's case failed with "(the Parameters panel shows the 3D material's properties)". **Cause:**
    `_parameters_back` held the tiling's text for the case with no graph in the editor, and `_in_properties` returned it
    for any step. **Fix:** `_parameters_back` returns None then, and `_in_properties` takes what the panel was turned
    to (`properties`), which `_set_tiling` and `_set_environment` pass. **Also covered:** the abort handler calls
    `_parameters_back()` for its effect only; the tiling's line is unchanged (the same test's other case).

- [x] **HLP-191 · An environment step that stops partway says less than happened** · `mcp_server/designer_helpers/view3d.py:463`, `:591`, `:955` · confirmed · found 2026-11-18
  - **Defect.** Two cases:
    - An abort after `dropped(other)` leaves the 3D view on Designer's smallest other map, which neither the user nor
      the call asked for. Only "3D view, setting: environment X" was printed.
    - A field with fewer spin boxes than `_panel_spin`'s index (Rotation Angle with one) raises a bare `IndexError:
      list index out of range`, naming no field.
  - **Scenario.** The job's timeout lands while the map shown is dropped again: the agent reads that the environment
    was being set to X, and the view shows `studio_04`.
  - **Fix.** Print a "3D view, setting:" line before the other map's drop, saying it is dropped first; refuse a missing
    spin box with the field's name (`what`).
  - **Resolution: done** (2026-11-18). **Tests:** `test_the_map_dropped_first_is_said_before_its_drop` (an abort as
    the other map is dropped) printed nothing; `test_a_field_with_fewer_spin_boxes_than_asked_is_refused_naming_it`
    (the real `_panel_field` on a Rotation Angle with one spin box) raised the bare `IndexError`. **Fix:** `_drop_map`
    prints "3D view, setting: environment <other> first, then <name> again" before the other map's drop; the server
    returns every "3D view, setting:" line when the set-up stops partway (`views.py`), and the prefix is now one
    constant, `SETTING`, which `begin` uses too. `_panel_field` takes the number of spin boxes needed and waits for
    them, refusing after 3 s with "<what> has no spin box 2 in the Parameters panel (it has 1)". **Also covered:** the
    helpers' other `findChildren(...)[0]`, `shot3d.py`'s `_mesh_shown`, runs only after `_3d_set_up` refused a 3D
    view without its menu bar.
  - Questioned by HLP-193 (2026-11-18).

- [x] **TST-537 · GUIDE.md's list of what the 3D shot drives leaves out the environment** · `mcp_server/GUIDE.md:345-347` · confirmed · found 2026-11-18
  - **Defect.** "`screenshot_designer('3d', ...)` drives its menus, the Explorer's context menu ..., the material's
    Tiling field, and left- and middle-drags on its viewport" reads as the whole list; the branch adds the
    environment's fields in the Parameters panel and file drops on the viewport.
  - **Scenario.** An agent writing raw Qt code for the 3D view, as this section is for, doesn't learn that a drop on
    the viewport sets the environment, or where it is measured.
  - **Fix.** Add the environment's fields and the drop of a map's file to the list, with `designer_helpers/view3d.py`
    as where they are measured.
  - **Resolution: done** (2026-11-18). GUIDE.md's list adds the environment's fields in the Parameters panel and a
    map's file dropped on the viewport, `designer_helpers/view3d.py` still where they are measured. Docs tests pass.

- [x] **TST-538 · Three things the environment's code does have no unit test** · `tests/unit/test_view3d_helpers.py:791`, `:829-834`; `tests/unit/test_view3d.py:91-96` · confirmed · found 2026-11-18
  - **Defect.**
    - The smallest other map: in `SIZES = {'airport': 10, 'corsica_beach': 1000, 'studio': 500}` the smallest is also
      the first, so `next(n for n in maps if n != name)` passes as well as `min(..., key=os.path.getsize)`.
    - `_set_environment`'s success path: which spin box takes each value (the Degrees one, index 1, for the rotation)
      and that the line says the values the spin boxes show, as the tiling's `test_the_tiling_said_is_the_spin_boxs`
      checks. The live check asks 0 and 0, which echoing the arguments passes.
    - The ranges' edges: only 180.5, -181, 10.5 and -11 are refused; `<` for `<=` would refuse ±180 and ±10, advertised,
      with no test failing.
  - **Scenario.** A regression to the first map in order (a large one), to the Turns spin box, or to `<` passes every unit
    test.
  - **Fix.** Make a map that isn't first the smallest (`corsica_beach`), add a success-path test with faked fields whose
    spin boxes show other values than asked, and send exactly 180 and -10.
  - **Resolution: done** (2026-11-18). **Tests:** `SIZES` makes `corsica_beach`, not the first map, the smallest;
    `test_the_environment_said_is_what_its_spin_boxes_show` fakes spin boxes showing other values than asked (45 and
    1.25 for 90 and 1) and checks which field and spin box each value goes to; `test_an_environment_value_is_sent_as_given`
    sends 180, -180, 10 and -10. The code was right, so each was seen failing against a temporary mutation: the first
    other map for the smallest (two tests failed, airport dropped), the Turns spin box for the Degrees one
    (`KeyError`), `<` for `<=` (the four limits refused).

- [x] **TST-539 · "A drop keeps the rotation and the exposure" has no check** · `mcp_server/designer_helpers/view3d.py:88-89`; `tests/test_all_tools/editor_panels_and_fit/checks.py:752-761` · confirmed · found 2026-11-18
  - **Defect.** The module docstring states it (measured while the branch was built: a drop left 0.25 turns and Exposure
    1.5), and no check measures it. In the live check, `other` and `again` both follow a drop, so a drop resetting the
    rotation to 0 would leave `kept` at 0.0 and `changed` passing.
  - **Scenario.** A Designer whose drop resets the rotation: `environment=` alone silently undoes the rotation and
    exposure an earlier call set, and the docstring says otherwise.
  - **Fix.** After `again`, shoot with `environment_rotation` 90 and `environment_exposure` 0 and no map, and require a
    difference under 2 from `again`; or narrow the sentence.
  - **Resolution: done** (2026-11-18). **Test:** the live check sets the exposure to 2 before the drops of `other`
    and `again`, then sets the rotation to 90 and the exposure to 2 again (`set_again`) and requires the render to stay
    (0.0 grey levels). Seen failing in a scratch run with the helpers mutated so each drop resets the rotation and the
    exposure (8.0 grey levels), the other conditions passing. The map's comparison now runs at exposure 2 on both sides
    (`brighter` and `other`).
  - Questioned by TST-545 (2026-11-18).

- [x] **TST-540 · Two conditions of the environment's live check can pass or fail for another reason** · `tests/test_all_tools/editor_panels_and_fit/checks.py:779`, `:793` · confirmed · found 2026-11-18
  - **Defect.**
    - `changed >= 10` was measured at 16.3; the others have three times their threshold (9.6 against 3). A map not set
      gives about 0 (the same map measured 0.0), so 5 tells the two apart with more room on another GPU or panel size.
    - `difference()` returns 255.0 for two renders of different sizes, which passes `moved >= 3` and `changed >= 10`
      whatever the light did.
  - **Scenario.** A smaller 3D panel lowers the map's difference under 10 with no defect; a panel resized between two
    shots passes the rotation's condition with none of it measured.
  - **Fix.** Lower the map's threshold to 5, and require the two renders' shapes to match in both conditions.
  - **Resolution: done** (2026-11-18). **Test:** `test_the_difference_of_two_renders` requires that for two sizes
    neither `>= 3`, `< 2` nor `<= 0.5` holds; it failed on `255.0 >= 3`. **Cause:** 255 failed every "the render stays"
    condition but passed every "the render changed" one. **Fix:** `difference()` returns NaN for two sizes, which no
    comparison passes, and the environment check says the shots' sizes when a pair differs; the map's threshold is 5
    (measured 14.3 grey levels in the scratch runs). **Also covered:** every caller in `tests/test_all_tools/`: the
    "changed" condition of `check_a_plain_3d_shot_shows_a_change_made_while_designers_window_was_off_screen`
    (`changed > 1`) had the same hole and is covered by the NaN; `near < min(3.0, 0.5 * far)` in the orbit, Selection
    and user's-mouse checks passed on `near < 3` alone when the far shot was of another size, since `min()` drops a
    NaN (as it dropped 255's half), so it is written `near < 3.0 and near < 0.5 * far` (seen passing in the scratch
    run); `checks.py:588`'s 255 stands for a failed shot, read only by `changed < 2`; `render/checks.py` gives -1 for
    two shapes, which its `0 <=` and `> 8` conditions fail.
  - Questioned by TST-544 (2026-11-18).

- [x] **TST-541 · Two implicit Anys in the tests the branch adds** · `tests/test_all_tools/editor_panels_and_fit/checks.py:724`, `tests/unit/test_view3d_helpers.py:817` · confirmed · found 2026-11-18
  - **Defect.** `said = dict(re.findall(r'^(\w+)=(.*)$', t, re.M))` is a `dict[Any, Any]`; `qt_core =
    vars(helpers)['QtCore']` is an `Any` where the file's `qt('QtCore')` gives the same object typed. mypy reports
    neither (AGENTS.md, typing: look for those yourself).
  - **Scenario.** A typo in `said.get(...)`'s use or in a faked attribute isn't caught by mypy.
  - **Fix.** `said: dict[str, str] = ...`; `qt_core = qt('QtCore')`.
  - **Resolution: done** (2026-11-18). `said: dict[str, str]` and `qt_core = qt('QtCore')`. **Also covered:**
    `tests/test_all_tools/example/checks.py`'s `outs = dict(re.findall(...))` was the same implicit Any, now
    `dict[str, str]`; `common.refs` is typed by its return annotation. mypy reports neither, so no test fails on
    them; lint and types pass.

- [x] **HLP-193 · An error after the map's drop doesn't say the map was set (follows HLP-191, generation 2)** · `mcp_server/designer_helpers/view3d.py:627-638`, `:982` · confirmed · found 2026-11-18
  - **Defect.** `setting()` drops the map, then looks up the Rotation Angle's and the Exposure's spin boxes and commits
    them. An error there ("has no spin box 2", or `_commit` finding no `valueChanged()`) leaves the map unsaid: with no
    step done before, the run raises it as is; otherwise "the 3D view was already set: ..." lists the earlier steps
    only. The begun line "3D view, setting: environment X, rotation ..." says the step began, not that the map was
    taken. HLP-191's fix covered an abort after the other map's drop and the missing spin box's message, not this.
  - **Scenario.** `environment='studio', environment_rotation=90` where the Rotation Angle has one spin box: the 3D view
    shows studio, and the error says only that the Rotation Angle has no spin box 2. `set_3d_view`'s docstring says
    "an error after a change says what was set".
  - **Fix.** Once the drop was taken, add the map to an error that follows ("...; the environment's map was set:
    studio"), or look the spin boxes up before the drop (whether they outlive it needs a check).
  - **Resolution: done** (2026-11-18). **Test:** `test_an_error_after_the_maps_drop_says_the_environment_set_so_far`
    (the real `_set_environment` through `set_3d_view`, the Rotation Angle's spin box missing after the map's drop)
    failed with the error alone. **Cause:** `setting()` raised whatever came after the drop, and only the run's own
    steps say what was done. **Fix:** `setting()` records each value as it is set, before its wait, and an error after
    any change is raised again with what was set: "...; environment studio set". **Also covered:** the run's steps
    say what they did ("the 3D view was already set: ..."); the tiling step is one change, said by the run once done;
    an abort's lines (the step's begun line, and HLP-191's line before the other map's drop) are unchanged.
  - Questioned by HLP-200 (2026-11-18).

- [x] **HLP-194 · Two docstrings and a test's comment say more or less than the code** · `mcp_server/designer_helpers/view3d.py:579-580`, `mcp_server/designer_helpers/shot3d.py:396-398`, `tests/unit/test_frames3d.py:198` · confirmed · found 2026-11-18
  - **Defect.**
    - `_drop_map`: "Refused otherwise, saying which map the 3D view shows". The first refusal, "the 3D view took no
      environment map dropped on it" (`:608`), names none.
    - `shoot_3d`: "What the steps find as they go is refused after ...: with mesh= and tiling=, the new mesh's material;
      with graph=, its row in the Explorer" reads as the whole list; the environment's fields in the Parameters panel
      and a map not taken are found as they go too.
    - `test_frames3d.py`: "# _tiling_spin's 100 ms polls stay": the poll is `_panel_field`'s now.
  - **Scenario.** A maintainer expects every refusal of `_drop_map` to name the map, or doesn't look for the
    environment's refusals after the window changed.
  - **Fix.** Narrow `_drop_map`'s sentence to the second refusal, add the environment to `shoot_3d`'s list, and name
    `_panel_field` in the comment.
  - **Resolution: done** (2026-11-18). `_drop_map`'s docstring says which refusal names the map shown: when the
    other isn't taken there is none to name. `shoot_3d`'s docstring adds the environment's fields and a map the 3D view
    doesn't take to what the steps find as they go. `test_frames3d.py`'s comment names `_panel_field`'s and
    `_switched`'s polls. Docs and comments only.

- [x] **SRV-183 · "0 by default" reads as environment_exposure's value when it is left out** · `mcp_server/server_tools/views.py:99`, `:141` · confirmed · found 2026-11-18
  - **Defect.** "environment_exposure: its Exposure, -10 to 10, 0 by default, higher brighter", and the error's "(0 by
    default)". In the other tools' docstrings, "default" is the value a parameter takes when left out; here it is the
    value Designer starts with, and a parameter left out changes nothing. Found by the server reviewer.
  - **Scenario.** An agent shoots with `environment_exposure=3` to look into a dark material, then leaves it out,
    expecting 0: the later shots render at 3 (the docstring says elsewhere that a set-up stays set, which an agent
    may not connect to this).
  - **Fix.** "Designer starts at 0" in the docstring and the error.
  - **Resolution: done** (2026-11-18). **Test:** `test_options_out_of_range_are_refused`'s row for 10.5 now matches
    the whole message, and it failed on "(0 by default)". **Fix:** the docstring says "higher brighter (Designer starts
    at 0)", and the error says "(Designer starts at 0)".

- [x] **TST-542 · GUIDE.md repeats the docstring's "set, not added" (follows SRV-181, generation 2)** · `mcp_server/GUIDE.md:49` · confirmed · found 2026-11-18
  - **Defect.** "(not a turn from where it is)" repeats the tool docstring's "(not added to the angle before, unlike
    orbit)" (`views.py:98`). AGENTS.md keeps a tool's parameters and behaviour in its docstring alone; SRV-181's fix
    wrote it in both.
  - **Scenario.** A later change to one copy leaves the other saying something else.
  - **Fix.** Drop the parenthetical from the guide and keep its advice.
  - **Resolution: done** (2026-11-18). The guide keeps its advice, "`environment_rotation` sets the light's angle
    around the mesh, to see relief lit from the side"; "not added" stays in the tool's docstring alone.

- [x] **TST-543 · ROADMAP item 90 doesn't list the environment, measured on macOS only too** · `ROADMAP.md:146` · confirmed · found 2026-11-18
  - **Defect.** Item 90 lists what the 3D set-up drives by names and rates measured only on macOS: its menu entries,
    its viewport's class, the Tiling field (`$tiling`) and the rest. The branch adds the environment's options, its
    Environment > Edit properties, its fields' name endings (`intensity`, `dome_rotation_angle`,
    `environment_texture_name`), the drag and drop of a map's file on the viewport, and the maps' folder
    (`DefaultResourcesDir/view3d/maps`), and the item names none of them.
  - **Scenario.** Whoever takes item 90 scopes the Windows work from its list and leaves out the drop.
  - **Fix.** Add them to the item's list.
  - **Resolution: done** (2026-11-18). Item 90 lists the environment's options, Environment > Edit properties, the
    fields' name endings, the drop of a map's file on the viewport and the maps' folder.

- [x] **TST-544 · Two sizes still pass two conditions (follows TST-540, generation 2)** · `tests/unit/test_selftest_renders.py:95`, `tests/test_all_tools/editor_panels_and_fit/checks.py:809` · confirmed · found 2026-11-18
  - **Defect.**
    - `assert not (apart >= 3 or apart < 2 or apart <= 0.5)` holds for NaN and for any value from 2 to 3: a
      `difference()` giving 2.5 for two sizes passes it, which the plain shot check's `changed > 1` reads as a change
      and `near < 3.0` as near.
    - `gained = float(greys[id(brighter)].mean() - greys[id(turned_again)].mean())` compares two renders' means without
      `apart()`'s check of their sizes.
  - **Scenario.** A panel resized between the two shots changes the background's share of the image: `gained >= 3`
    passes or fails for that, and no sizes are said.
  - **Fix.** `assert math.isnan(apart)`; check the two shapes for `gained` as `apart()` does.
  - **Resolution: done** (2026-11-18). **Test:** `assert math.isnan(renders.difference(a, a[:-1]))`, which failed
    against a mutation giving 2.5 for two sizes, where the old assertion passed. **Fix:** in the light check, `gained` is
    NaN for two sizes through `sized()`, which says them, as `apart()` does.

- [x] **TST-545 · Three facts beside TST-539's have no check (follows TST-539, generation 2)** · `mcp_server/designer_helpers/view3d.py:79-80`, `:84`, `:89`; `tests/test_all_tools/editor_panels_and_fit/checks.py:709` · confirmed · found 2026-11-18
  - **Defect.** TST-539 added a check for "a drop keeps the rotation and the exposure"; the module docstring's next
    claims still have none (AGENTS.md: a claim without a test is a guess):
    - "Environment > Reset Environment puts all three back", which the environment checks' clean-up relies on
      (`RESET_ENVIRONMENT`, whose `ENVIRONMENT_RESET` line nothing reads). This review's probe measured it holding for
      the rotation and the exposure, the Parameters panel left as it was.
    - "A value isn't wrapped: 1.75 turns stays 630 degrees".
    - "a drop alone, or an enter and a move, did nothing".
  - **Scenario.** A Designer whose reset leaves the rotation: the category's later checks run lit at 90 degrees and
    exposure 2, failing far from the cause, while the docstring says the reset puts it back.
  - **Fix.** Read the fields after the facts script's reset (`RESET=0 0`) and require `ENVIRONMENT_RESET` in the
    snippet's text; check the other two or narrow them.
  - **Resolution: done** (2026-11-18). **Tests:** the designer facts script measures each claim, and the facts check
    reads them: `TURNS=630` (1.75 turns in the Turns spin box, then the Degrees one read); `PARTIAL=0 0` (a drop alone,
    then an enter and a move alone, of a map not shown); `RESET=0 0` and `RESET_MAP=1` (the fields after Reset
    Environment, and the map shown before it dropped again). All held in the scratch runs; designer facts measure
    Designer itself. Both environment checks now read the reset's `ENVIRONMENT_RESET` through
    `check_the_environment_is_reset`. **Fix:** the module docstring's reset sentence says what is measured: it "puts
    the rotation and the exposure back to 0, and changes the map".

- [x] **TST-546 · The designer fact's AGAIN=0 has no positive check after it** · `tests/test_all_tools/editor_panels_and_fit/designer_scripts/environment.py:157-162` · confirmed · found 2026-11-18
  - **Defect.** `drop(ARGS['second'])` then `print('AGAIN=%d' % (len(signals) - before - 1))`: a field that stopped
    signalling after the first change (rebuilt by the panel, or disconnected) gives 0 too.
  - **Scenario.** A later Designer rebuilds the Environment field when the map changes: the fact still passes, though
    `_drop_map` relies on that field signalling again (only the light check's `again` shot, through the helper the
    fact vouches for, would fail).
  - **Fix.** Drop `first` once more and require one signal (`BACK=1`).
  - **Resolution: done** (2026-11-18). The facts script drops `first` once more after `AGAIN` and requires one signal
    (`BACK=1`), seen in the scratch runs; `drop()` now returns each drop's own count.

- [x] **TST-547 · test_shot3d doesn't test the environment's arguments through shoot_3d** · `tests/unit/test_shot3d.py:948-1012`, `:1102` · confirmed · found 2026-11-18
  - **Defect.** The `Shot` fake records each set-up's arguments, but no test gives environment values and compares the
    `'set up (...)'` event, and `test_a_set_up_refused_doesnt_touch_the_window` has no unknown environment.
  - **Scenario.** `shoot_3d` passing the rotation and the exposure swapped to `_3d_set_up` passes every unit test; only
    the live check's text catches it.
  - **Fix.** A shot with `environment_rotation=90.0, environment_exposure=1.0` comparing the set-up event, and the case
    `({'environment': 'Studio'}, "unknown environment 'Studio'")` in the refusals.
  - **Resolution: done** (2026-11-18). **Tests:** `test_the_environment_is_given_to_the_set_up_in_its_order` compares
    the set-up event of a shot with a rotation of 90 and an exposure of 1, and `test_a_set_up_refused_doesnt_touch_the_window`
    gains the unknown environment. Both guard code that was right; each failed against a mutation: the rotation and the
    exposure swapped in `shoot_3d`, and the environment not checked before the window changes.

- [x] **TST-548 · The environment check's set-up shot isn't among its shots** · `tests/test_all_tools/editor_panels_and_fit/checks.py:768`, `:782` · confirmed · found 2026-11-18
  - **Defect.** `await c('screenshot_designer', {**THREE_D, 'mesh': 'Sphere', 'view': 'Front', 'graph': VIEW3D_GRAPH})`
    isn't in `shots`, which are checked to be images.
  - **Scenario.** The set-up fails, unsaid: the light's checks then measure whatever mesh and view the check before
    left, while the docstring says "On a sphere from the Front".
  - **Fix.** Keep its result and add it to `shots`.
  - **Resolution: done** (2026-11-18). The set-up shot is kept and among the shots checked to be images. **Also
    covered:** HLP-192's new check runs its set-up and both renders in one snippet, and requires both files.

- [x] **TST-549 · A loose type in a new test** · `tests/unit/test_view3d_helpers.py:906` · confirmed · found 2026-11-18
  - **Defect.** `asked: list[tuple[str, object]] = []`: the second item is always an `int` (the number of spin boxes
    needed, or a spin box's index).
  - **Fix.** `list[tuple[str, int]]`.
  - **Resolution: done** (2026-11-18). `asked: list[tuple[str, int]]`; lint and types pass.

- [x] **HLP-195 · A tiling the spin box shows already is committed again, and its wait runs to its limit** · `mcp_server/designer_helpers/view3d.py:534-543`, `:997-1003` · measured · found 2026-11-18
  - **Defect.** `_set_tiling` commits the value whatever the Tiling spin box shows, and the run waits for the view
    from a mark before it. A value the material has already changes nothing the view shows, so `settled` waits for a
    restart that never comes, until NO_RESTART (1 s): the safety net taken as the time the wait takes, which AGENTS.md
    rules out. HLP-192's fix skips such values for the environment, not for the tiling. Found while addressing
    HLP-192 (the efficiency review of its fix).
  - **Scenario (measured).** A probe in a Designer an agent started committed, with the 3D view on screen, the value
    each spin box showed and then a changed one, twice: the tiling's equal commit restarted nothing and its wait took
    1.56 and 1.50 s (the exposure's and the rotation's 1.04 to 1.15 s), against 0.47 to 1.12 s for a changed value, each
    of which restarted the view. The self-test's shots set `tiling=1.0` again and again, each paying it.
  - **Fix.** As for the environment: skip the commit and the wait when the spin box shows the value, and wait for a
    change from right before its commit.
  - **Resolution: done** (2026-11-18). **Tests:**
    `test_a_value_the_parameters_panel_shows_already_is_neither_committed_nor_waited_for[tiling]` failed: the tiling
    was committed and waited for. The live `check_values_a_3d_set_up_finds_shown_already_take_no_wait` shoots a mesh,
    a tiling and environment values, then the same again, counting the second set-up's waits on the view's frames. It
    failed with one wait, the tiling's, then, extended to the mesh, with one again, the mesh's; with both skips removed
    by a mutation, with two. It passes with none. **Cause:** a value already there was committed, or a mesh already
    shown picked, again, and the step waited for a restart that never came. **Fix:** one helper, `_commit_change`,
    commits a value unless its spin box shows it already, and returns the mark taken right before the commit; the
    tiling and the environment's rotation and exposure go through it. `_set_tiling` takes the watch, as
    `_set_environment` does, waits from that mark, and an error in that wait says the tiling was set
    (`test_each_change_through_the_parameters_panel_is_waited_for_from_just_before_it[tiling]`,
    `test_a_wait_failing_after_a_commit_says_what_was_set`). The run's tiling step no longer waits itself. The
    comparison is exact: the four spin boxes keep 45 decimals, with ranges past the tool's limits (0 to 3.4e38 for the
    tiling), and 2.001 stayed 2.001 (measured). **Also covered:** the mesh step, measured the same way: a mesh picked
    again restarted nothing and waited 0.96 to 1.01 s, against 0.94 and 0.95 s for another mesh, which restarted the
    view. It is now skipped when its Scene action is checked, which matched `_mesh_shown` for both meshes shown
    (measured; `test_a_mesh_shown_already_is_neither_picked_again_nor_waited_for`, which failed first). The view's
    turn and the graph's outputs keep their waits: nothing tells beforehand whether they change what the view shows
    (the camera's position isn't readable: the module docstring). The whole `editor_panels_and_fit` category was run
    in a scratch run, as the skips depend on what the check before left. Two problems that predate the branch came up
    on the way, HLP-196 and HLP-197: the new checks go through `shoot_3d` meanwhile.
  - Questioned by HLP-199, HLP-201 and TST-551 (2026-11-18).
  - Note (2026-11-18): the clean-up of `check_values_a_3d_set_up_finds_shown_already_take_no_wait`,
    `set_3d_view(tiling=1.0)`, isn't in a `finally`. No later check depends on it: they set their tiling (the third
    review).

- [x] **HLP-196 · `set_3d_view(graph=...)` unhides a hidden Designer and leaves it so** · `mcp_server/designer_helpers/view3d.py` (`_3d_set_up`, the graph step: `_apply_outputs`) · measured · found 2026-11-18
  - **Defect.** Run on its own, with Designer's window off screen, `set_3d_view` applies a graph's outputs through the
    Explorer's context menu, a popup, with the window still hidden; Designer is unhidden by it and left so. The 3D shot
    isn't affected: its set-up runs with the window on screen, put back hidden after. Predates this branch: main's
    helpers do the same. Found while addressing HLP-195 (a new check called it).
  - **Scenario (measured).** A scratch run hid Designer (the self-test's `at_rest`), then ran
    `set_3d_view('mcp_selftest_view3d')`, with this branch's helpers and with main's: Designer read hidden before and
    unhidden after, each time. In the category's run, its window then stood opaque in front of Chrome for 3.52 s, and
    the next check found Designer not hidden.
  - **Fix.** Run the graph step with the window on screen, as the 3D shot does and as `set_3d_view` already does for
    camera moves (REVIEW.md HLP-168, the user's choice), or say in the docstring that it needs Designer shown: the
    user's choice, as it changes what they see.
  - **Resolution: done (the user's choice, 2026-11-18: "Show the window (Recommended)", recorded in DECISIONS.md).**
    **Tests:**
    `test_a_set_up_that_moves_the_camera_puts_outputs_on_or_switches_the_mesh_runs_with_designers_window_on_screen[graph]`
    failed: the set-up ran off screen. The live `check_set_3d_view_shows_the_window_for_graph_and_a_mesh_switch`
    (Designer hidden at rest, then `set_3d_view(graph)`, requiring the window put on screen for it and Designer hidden
    after) failed in its scratch run: no window was put on screen. That run left Designer hidden; two runs before had
    left it unhidden, so the unhide doesn't come every time, and the check requires the window put on screen and
    hidden again either way. **Cause:** `set_3d_view` ran `graph=` off screen, and the Explorer's menu can unhide
    Designer. **Fix:** a set-up with `graph=` runs whole with the window on screen, transparent and click-through, then
    put back as it was, as a 3D shot does; `_3d_set_up` decides it, from the steps it checked, and `set_3d_view` runs
    it. **Also covered:** the self-test's `ABORTED` snippet (`graph=` then an abort)
    now runs on screen, and its check passes; the whole `editor_panels_and_fit` category passed in a scratch run (119
    checks), its watch reading Designer the active app or in front for 0.00 s.
  - Questioned by HLP-203 (2026-11-18).

- [x] **HLP-197 · `set_3d_view` off screen loses a tiling set after a mesh switch: its spin box is deleted under it** · `mcp_server/designer_helpers/view3d.py` (`_3d_set_up`, the mesh step; `_set_tiling`, `_commit`) · measured · found 2026-11-18
  - **Defect.** Off screen, the mesh step's wait ends at the view's first request for a frame, while the view still
    takes the switch (HLP-168 measured requests until 0.32 s). The tiling step then finds the new material's Tiling
    spin box, which Designer deletes while it is committed: `RuntimeError: Internal C++ object
    (PySide6.QtWidgets.QDoubleSpinBox) already deleted.` The 3D shot isn't affected (its set-up runs on screen).
    Predates this branch: main's helpers do the same. Found while addressing HLP-195.
  - **Scenario (measured).** With Designer hidden, `set_3d_view(mesh='Plane')` then `set_3d_view(mesh='Sphere',
    tiling=2.0)` raised that error from `_commit`, "the 3D view was already set: Sphere", with this branch's helpers
    (twice, also with an exposure) and with main's.
  - **Fix.** Run a set-up that switches the mesh and then goes through the Parameters panel with the window on screen,
    as for HLP-196 (the user's choice), or wait off screen for what says the switch was taken, if anything does
    (HLP-168 found nothing).
  - **Resolution: done (the user's choices, 2026-11-18: "Show the window (Recommended)", then "Any mesh switch
    (Recommended)"; recorded in DECISIONS.md).** **Tests:**
    `test_a_set_up_that_moves_the_camera_puts_outputs_on_or_switches_the_mesh_runs_with_designers_window_on_screen`'s
    cases with a mesh failed: the set-up ran off screen. The live
    `check_set_3d_view_shows_the_window_for_graph_and_a_mesh_switch` (Designer hidden: mesh switches, a tiling in a
    call of its own after one, then a mesh switch and a tiling in one call) failed with the deleted spin box, and
    passes. **Cause:** off screen, the mesh step's wait ends before the view has taken the switch, and Designer
    rebuilds the Parameters panel meanwhile. A first fix put the window on screen only for a mesh with a tiling or the
    environment's values in the same call; a scratch run then measured a tiling in the next call failing the same way,
    in 9 tiling cases of 9 over three runs (the environment's exposure alone didn't, in 3). **Fix:** a set-up that
    switches the mesh runs whole with the window on screen; a mesh its Scene action checks already is no switch, and
    stays off screen (`test_a_mesh_shown_already_with_a_tiling_runs_off_screen`). The new check failed with the first
    fix's rule brought back by a mutation, on the tiling after a mesh switch in a call of its own. **Also covered:** a
    tiling or the environment's values alone stay off screen (the unit test's other cases); the self-test's
    `TILING_FAILING` snippet (a mesh and a tiling) now runs on screen, and its check passes.

- [x] **HLP-198 · A value committed through the Parameters panel raises when Designer rebuilds the panel right after: the value is taken, its read-back fails** · `mcp_server/designer_helpers/view3d.py` (`_commit`) · measured · found 2026-11-18
  - **Defect.** `_commit` sets the value, invokes the spin box's `valueChanged()`, lets Designer's events run, then
    returns `spin.value()`. Designer can rebuild the Parameters panel within those events, deleting that spin box, and
    the read-back raises `RuntimeError: Internal C++ object (PySide6.QtWidgets.QDoubleSpinBox) already deleted.` Found
    while addressing HLP-197: the self-test's check of a Designer whose view never drew, moved from mesh switches (now
    on screen) to the tiling, failed this way.
  - **Scenario (measured).** In a Designer an agent had just opened, hidden, its 3D view never drawn,
    `set_3d_view(tiling=2.0)` raised that error from `_commit`'s `return spin.value()`; the panel shown again then read
    the tiling 2: the commit was taken. The first `environment_exposure=1.0` there succeeded and was taken (it read 1),
    its spin box deleted too, after the read-back. The calls after the first ran without error. HLP-197's tracebacks
    after a mesh switch failed on the same line.
  - **Fix.** Read the value back from the panel's field found again when the spin box was deleted, rather than from
    the spin box committed.
  - **Resolution: done** (2026-11-18). **Tests:** `test_a_value_committed_is_read_back_from_the_panel_designer_rebuilt`
    (a spin box that raises as PySide does once read after its commit, the field found again showing 2) failed with
    that error. The live `check_set_3d_view_sets_up_a_view_that_never_drew`, moved from mesh switches (now on screen) to
    the tiling set to 2 then back to 1, off screen, in a Designer just opened, failed the same way in its scratch run,
    and passes. **Cause:** `_commit` read the value back from the spin box it committed, which Designer may have deleted
    by then; the value was taken all the same. **Fix:** `_commit` takes how to find the spin box again
    (`_commit_change` passes it: the tiling's, the rotation's and the exposure's lookups), and reads the value from the
    one found again when the first was deleted. **Also covered:** `_commit` is the only place that reads a spin box
    after its commit; the environment's exposure, its spin box deleted after the read-back, needed nothing more.
  - Questioned by TST-551 (2026-11-18).

- [x] **HLP-199 · `_mesh_shown` is no longer used by the tools, though three docs and a designer fact say the set-up reads it (follows HLP-195, generation 2)** · `mcp_server/designer_helpers/shot3d.py:71`, `:369`; `tests/test_all_tools/editor_panels_and_fit/checks.py:2636`; `ROADMAP.md:92`, `:100`; `tests/unit/test_shot3d.py:985` · confirmed · found 2026-11-18
  - **Defect.** HLP-195's fix made the mesh step and `_3d_set_up`'s `switching` read the Scene action of the mesh asked
    (`_menu_action(bar, keep, 'Scene', mesh).isChecked()`, `view3d.py:960`, `:1006`). It removed `shoot_3d`'s call of
    `_mesh_shown`, its only caller in the tools. Only the designer fact's `SHOWN_MESH` snippet still calls it. Yet:
    - shot3d.py's docstring says "The 3D view's Scene menu checks the mesh it shows (_mesh_shown reads it): the
      set-up's mesh step skips a mesh checked already".
    - The fact's docstring says "shot3d.py's _mesh_shown reads it, to tell a mesh switched from the one shown". The fact
      vouches for a reader the set-up doesn't run.
    - ROADMAP items 77 and 85 name `_mesh_shown` among the readers the set-up uses to skip values shown already.
    - The `Shot` fake in test_shot3d.py patches `_mesh_shown`, which nothing calls.

    Found by the helpers reviewer and the docs reviewer.
  - **Scenario.** Whoever builds item 85's text answer reuses `_mesh_shown`, believing the set-up shares it. A change to
    how the set-up reads the mesh then leaves the fact passing.
  - **Fix.** Either make the set-up call the one reader the fact checks, or remove `_mesh_shown` and make the fact read
    what `_3d_set_up` reads. Then fix the two docstrings, the two ROADMAP items and the fake.
  - **Resolution: done** (2026-11-18). No behaviour changed, so no failing test: the tools no longer called
    `_mesh_shown`. The designer fact now reads, in its `SHOWN_MESH` snippet, the Scene action of each mesh with
    `_menu_action`, as the set-up's mesh step does. It passed before (through `_mesh_shown`) and after, in scratch runs.
    **Fix:** `_mesh_shown` is removed from shot3d.py with its docstring bullet. The fact that Scene checks the mesh
    shown, and that the mesh step reads it, is now in view3d.py's module docstring. shot3d.py's list of what the
    self-test re-measures no longer ends with "the last point". The fact's docstring names view3d.py's mesh step.
    ROADMAP items 77 and 85 name the Scene action through `_menu_action`. The `Shot` fake's patch is gone. **Also
    covered:** nothing else in the repo names `_mesh_shown`.
  - Questioned by TST-554 (2026-11-18).

- [x] **HLP-200 · An error after a change doesn't always say what was set (follows HLP-193, generation 3)** · `mcp_server/designer_helpers/view3d.py:680-681`, `:1007-1009`, `:1018-1019`, `:1034-1041`, `:511` · confirmed · found 2026-11-18
  - **Defect.** `set_3d_view`'s docstring says "an error after a change says what was set". HLP-193's fix records each
    environment value as it is set, before its wait. Two paths still leave a change unsaid:
    - **A step's own wait.** `_Frames.settled` can raise: where no count shows, it compares renders, and `_3d_render`
      refuses with "the 3D view did not produce a render". The map records itself only after its wait
      (`changed = _waited_for(watched, lambda: _drop_map(...))`, then `name_set = name`). The mesh, the graph and the
      viewpoint each call `done.append(step)` after theirs. The error then leaves the change out. Raised alone, it says
      nothing of it; after other steps, "the 3D view was already set: ..." lists only those.
    - **The read-back's second look (HLP-198).** `_commit_change` commits, then, when the spin box was deleted, runs
      `return find().value(), since`. If `find()` refuses (no field or spin box found within 3 s), it raises before
      `rotation_set`, `exposure_set` or the tiling's `said` exist. The commit was taken all the same.

    Found by `/simplify`'s altitude reviewer and the helpers reviewer; the lead agent read both paths. Whether Designer
    ever rebuilds the panel without the field is unmeasured (HLP-198's check found it again). The defect is what the
    error says on that path.
  - **Scenario.** `environment='studio_black_soft_light'` with Display > Samples off, and the render comparison's copy
    failing: the view shows the new map, and the error doesn't say so. `environment_rotation=90` with the rebuilt
    panel's field not found: the angle is set, and the error leaves it out.
  - **Fix.** Record a step as done once its change is made, before its wait. Raise `find()`'s refusal again with what
    was committed ("...; the environment's Rotation Angle committed to 90, not read back").
  - **Resolution: done** (2026-11-18). **Tests:** `test_a_wait_failing_after_a_steps_change_says_it_was_set` (the
    mesh, the graph, the viewpoint and the map, with the fake's `settled` raising) failed with the error alone, "the
    view took no frame". `test_a_value_committed_but_not_found_again_is_said_committed` failed with the refusal alone.
    **Cause:** each of those steps recorded itself only after its wait, and `_commit_change`'s second look raised past
    a commit already taken. **Fix:** `_Waiting` (frames3d.py) replaces `_waited_for`. It is a `with` around a step's
    change: it marks as it starts, and on leaving waits unless an error came or `needed` was set False. The mesh, the
    graph, Frame and the map record themselves inside it, once their change is made, before the wait. The viewpoint
    records "view X" after its trigger, and "view X, framed" after Frame. `_commit_change` raises its second look's
    refusal again with "...; <the field> committed to <value>, not read back". **Also covered:** the camera's moves
    record each option before their one wait, as before. The tiling, the rotation and the exposure record their value
    before their wait (HLP-193), and all three go through `_commit_change`'s wrap. HLP-191's line before the other map's
    drop is unchanged.
  - Questioned by HLP-204, HLP-205 and TST-555 (2026-11-18).

- [x] **HLP-201 · A map asked again is still waited for, to the wait's limit (follows HLP-195, generation 2)** · `mcp_server/designer_helpers/view3d.py:680` · measured · found 2026-11-18
  - **Defect.** A map the view shows already is dropped again after another, back to back (`_drop_map` returns False).
    The view takes the net change as none, so `_waited_for` waits for a restart that never comes, until NO_RESTART.
    HLP-195 removed that wait for values and meshes shown already. Its **Also covered** doesn't mention the map. Found
    by the helpers reviewer.
  - **Scenario (measured).** A scratch probe in a Designer an agent started shot `environment=` three times: DARK, DARK
    again, then BRIGHT. It timed `_Frames.settled` and read `_Counts.restart` after each. The first map's wait took
    0.34 s and restarted the view, back to 8. The same map asked again waited 0.95 s with no restart. Another map took
    0.33 s and restarted it. The shot asking the map again took 1.35 s, against 0.97 s and 0.96 s.
  - **Fix.** Wait only when `_drop_map` returns True.
  - **Resolution: done** (2026-11-18). **Tests:** `test_a_map_asked_again_isnt_waited_for` failed with one wait. The
    live `check_values_a_3d_set_up_finds_shown_already_take_no_wait` now asks the same map (DARK) in both shots. It
    failed in its scratch run ("waits: 1") and passes with none. It also compares the two shots' renders: 0.00 grey
    levels apart, before the fix and after, so the render taken with no wait is the view at rest. **Cause:** the map's
    wait ran whatever `_drop_map` answered. **Fix:** `_Waiting`'s `needed` takes `_drop_map`'s answer: a map taken at
    its first drop is waited for, and one dropped back after another isn't. view3d.py's module docstring says so,
    with the check. **Also covered:** values and a mesh shown already (HLP-195). The viewpoint and the graph keep their
    waits, since nothing says beforehand whether they change what the view shows.

- [x] **HLP-202 · STALE flags a tiling change on a material with no pattern, after a wait of a second** · `mcp_server/designer_helpers/shot3d.py:93-98`, `:428-439`; `mcp_server/designer_helpers/view3d.py:1078` · measured · found 2026-11-18
  - **Defect.** Since this branch, a tiling committed counts as a change (`changed |= tiled`), so `shoot_3d` compares
    the render after it with the one before. On a material with no pattern, the tiling changes nothing the render
    shows. The retake then waits for a next frame (`_Frames.next_frame`, NO_RESTART at most), and STALE says "The 3D
    view may not have been drawn", though it was. STALE's only caveat is a pan or zoom with no mesh in view. Found by
    the helpers reviewer.
  - **Scenario (measured).** A scratch probe put the self-test's plain graph (`PLAIN_OPS`: a Uniform Color into two
    outputs) on a Plane from the Top at tiling 1, then shot `tiling=2`, `tiling=1` and `tiling=1`. STALE was printed for
    both changes, which took 2.14 s and 2.08 s. It wasn't printed for the same tiling again, which committed nothing and
    took 0.89 s. An agent shooting an early material reads it as a view not drawn, and shoots again.
  - **Fix.** Name the case in STALE ("a tiling on a material with no pattern changes nothing"), as the pan's case is
    named. The fix should also measure whether a change of the light can leave such a render identical.
  - **Resolution: done** (2026-11-18). **Measured first:** a scratch probe put the plain graph (`PLAIN_OPS`) on a
    Plane from the Top, then on a Sphere from the Front. On each it shot a tiling of 2, rotations of 90 and 180
    degrees, an exposure of 1 and another map. Only the tiling left the render identical, on both. **Tests:** the new
    `check_a_tiling_on_a_material_with_no_pattern_is_said_to_change_nothing` failed in its scratch run on the shot's
    line, which named no such case. Its designer fact passed: the renders at tiling 1 and 2 were 0.00 grey levels
    apart. `test_shot3d.py`'s STALE text failed on the old line. **Fix:** STALE adds "and a tiling changes nothing on
    a material with no pattern". **Not changed:** the retake still waits for a next frame, NO_RESTART at most, before
    the line. Skipping it when a step's own wait saw the view draw the change would change the retake for every
    set-up: proposed to the user as a follow-up.
  - Questioned by TST-556 (2026-11-18).

- [x] **HLP-203 · `_3d_set_up`'s and `run`'s docstrings describe `set_3d_view` as before HLP-196's fix (follows HLP-196, generation 2)** · `mcp_server/designer_helpers/view3d.py:900-905`, `:962-966` · confirmed · found 2026-11-18
  - **Defect.**
    - `_3d_set_up` says "Run without a watch, the viewpoint's turn and Frame run with the window on screen". It also
      says "A caller giving its watch keeps the window on screen itself, and passes its look as `between`: the shot,
      or set_3d_view with a move". `set_3d_view` now always calls the set-up without a watch, and `run` keeps the
      window on screen for moves, `graph=` and a mesh switch. The first sentence leaves those out.
    - `run` says "`between` run before each". On screen, `run` passes its own look (`screen.again`) instead of the
      caller's `between`. No caller passes one there today.

    Found by the helpers reviewer.
  - **Scenario.** A maintainer looks in `set_3d_view` for the watch its docstring says it gives for a move, and finds
    none. Or they pass a `between` without a watch, and it goes unused on screen.
  - **Fix.** Narrow both docstrings to what the code does (generation 2, docs only).
  - **Resolution: done** (2026-11-18). Docstrings only. `_3d_set_up`'s says the shot gives its watch and its look,
    and keeps the window on screen itself. Run without a watch, as `set_3d_view` runs it, a set-up that moves the
    camera, puts a graph's outputs on the mesh or switches the mesh runs its steps on screen; any other runs only the
    viewpoint's turn and Frame there. `run`'s says that on screen its own look runs before each step instead of
    `between`.
  - Questioned by HLP-205 (2026-11-18).

- [x] **TST-550 · ROADMAP's rules for a 3D set-up step say more than the steps they describe; item 90 mischaracterizes two on-screen cases** · `ROADMAP.md:65`, `:67`, `:82`, `:170` · confirmed · found 2026-11-18
  - **Defect.** The 3D view section's list says an item is built "as the camera, the mesh, the tiling and the light
    are". Three of its rules don't hold for those steps, and item 90 misreads two findings:
    - **Checked first** says "the step's menu entries, buttons and fields are looked up, and refused, before anything
      changes". The Parameters panel's fields exist only once Edit properties shows them, and with mesh= only after the
      switch. They are found as the step reaches them, and refused after the window changed, as `shoot_3d`'s docstring
      says.
    - **Skipped when shown already** says "a value the view shows already ... isn't set again, and costs no wait". The
      map can't be read. Asked again, it is dropped twice and waited for (HLP-201).
    - **Checked live** says "the step gets a case in `check_a_render_that_didnt_follow_a_set_up_is_said`". Its cases
      are a pan and an exposure. The mesh, the tiling, the map, the orbit and the zoom have none.
    - **Item 90** says "`set_3d_view` run on its own puts it on screen too for camera moves, `graph=` and a mesh
      switch, which came out differently off screen on macOS (REVIEW.md HLP-168, HLP-196, HLP-197)". HLP-196 was the
      Explorer's menu unhiding Designer, and HLP-197 a spin box deleted as it was set. The list also repeats
      `set_3d_view`'s docstring and DECISIONS.md.

    Found by the docs reviewer.
  - **Scenario.** Item 75's implementer plans to refuse the Height scale field before any change, which can't be done.
    Or they expect a map shown already to cost nothing.
  - **Fix.**
    - Say that fields are found as the step reaches them.
    - Name the map as the exception.
    - Scope **Checked live** to a new step.
    - Point item 90 to DECISIONS.md's 3D screenshot entry for the on-screen set-ups.
  - **Resolution: done** (2026-11-18). Docs only. ROADMAP's rules now say:
    - a field of the Parameters panel is found as the step reaches it, and refused then, naming it;
    - a value that can't be read, like the map, is set again, and waited for only if the view takes it as a change
      (HLP-201);
    - a menu or toolbar change waits in `with _Waiting(watched)`, and a field from the mark `_commit_change` takes;
    - the step records its change before its wait (HLP-200);
    - "Checked live" is for a new step, and says the stale check's cases today are a pan and an exposure.

    Item 90 points to DECISIONS.md's 3D screenshot entry for the set-ups that went wrong off screen.
  - Questioned by TST-554 (2026-11-18).

- [x] **TST-551 · Two tests pass a mutation of what they guard (follows HLP-198 and HLP-195, generation 2)** · `tests/unit/test_view3d_helpers.py:1915`; `tests/test_all_tools/editor_panels_and_fit/checks.py:787`, `:803` · confirmed · found 2026-11-18
  - **Defect.**
    - **HLP-198's test** is `test_a_value_committed_is_read_back_from_the_panel_designer_rebuilt`. The spin box found
      again shows the value asked: `iter([Rebuilt(1.0), Spin(2.0)])`, with tiling 2.0. So a fallback of
      `except RuntimeError: return value, since` passes it, though it says the value asked rather than the value the
      panel shows. The live `NEVER_DREW` check reads "3D view: tiling 2 (" the same way.
    - **The light check** says "set to 90 degrees again, it stays (REVIEW.md SRV-181: the angle is set, not added)".
      Since HLP-195, the second 90 equals what the Degrees spin box shows, so nothing is committed. An angle added to
      the shown one in `_commit` passes. A unit test still catches it: 45 shown, 90 asked, `set == [90.0]`.

    Found by the tests reviewer.
  - **Fix.** Make the rebuilt panel's spin box show another value (2.5), and expect it said as shown. Narrow the light
    check's docstring to the skip, and name the unit test that guards SRV-181.
  - **Resolution: done** (2026-11-18). **Test:** in HLP-198's test, the spin box found again shows 2.5 where 2.0 was
    asked, and the line must say 2.5. It failed against a mutation returning the value asked, where the old test
    passed. **Fix:** the light check's docstring and condition now claim only what it shows: "environment_rotation set
    to the angle shown: said set, and the render stays". The docstring names the unit test that guards SRV-181,
    `test_the_environment_said_is_what_its_spin_boxes_show`. The live `NEVER_DREW` line stays as it is: there Designer
    shows the value committed, and the read-back's source is the unit test's to check.

- [x] **TST-552 · No helper test gives the environment's rotation or exposure 0** · `tests/unit/test_view3d_helpers.py:1045-1080` · confirmed · found 2026-11-18
  - **Defect.** `lit = environment is not None or environment_rotation is not None or environment_exposure is not None`
    (`view3d.py:908`) runs the environment step for 0. The helper tests give 90, 1 and 2. A 0 appears only in a
    refusal case (`:713`), which `paneled` decides, not `lit`. `test_shot3d.py`'s cases of 0 go through the `Shot`
    fake, which builds its own set-up. If `lit` became a truthiness test, `set_3d_view(environment_rotation=0.0)` would
    change nothing, and no unit test would fail. Found by the tests reviewer.
  - **Scenario.** An agent puts the light back with `environment_rotation=0, environment_exposure=0`. Nothing is set,
    and the '3D view: ...' line says nothing of the environment.
  - **Fix.** Add a case where the rotation shows 45 and 0 is asked, which commits and answers that the view changed.
  - **Resolution: done** (2026-11-18). **Test:** two cases of `test_a_set_up_says_whether_it_changed_what_the_view_shows`,
    a rotation of 0 and an exposure of 0 with the spin box showing 2.5, answer that the view changed. The code was
    right. Both failed against a mutation testing `lit` by truthiness.

- [x] **TST-553 · Two comments in the 3D checks describe the snippets as they were before this branch** · `tests/test_all_tools/editor_panels_and_fit/checks.py:1939`, `:2400-2402` · confirmed · found 2026-11-18
  - **Defect.** "# shoot_3d with a pan, the image removed" stays above `SHOT_WITH`'s new comment. `NEVER_DREW`'s
    comment says "then the mesh set up, Sphere, then Plane", but since HLP-198's fix the snippet sets the tiling to 2,
    then 1. Found by the tests reviewer.
  - **Fix.** Delete the first comment, and rewrite the second for the tiling.
  - **Resolution: done** (2026-11-18). The old comment above `SHOT_WITH` is deleted. `NEVER_DREW`'s comment says the
    tiling is set to 2, then back to 1.

- [x] **HLP-204 · An error turning the Parameters panel back, after the tiling or the environment was set, leaves the value unsaid (follows HLP-200, generation 4)** · `mcp_server/designer_helpers/view3d.py:541-559` · confirmed · found 2026-11-18
  - **Defect.** `_in_properties` runs `setting()`, then in its `finally` `_switched(...)` and `_parameters_back()`. When
    `setting()` returned, the tiling or the environment is set and waited for. If the turn-back then raises
    (`openResourceInEditor`, or the panel's title read by `_switched`), the error replaces the return. The run's
    `done.append(said)` never runs, so the error says "the 3D view was already set: ..." without that value, or
    nothing. Found by the docs reviewer; the lead agent read the path. Whether the turn-back ever raises is
    unmeasured. The defect is what the error says on that path.
  - **Scenario.** `set_3d_view(tiling=2.0)` with the graph in the editor closed between the commit and the turn-back:
    the tiling is 2, and the error doesn't say so.
  - **Fix.** Raise a turn-back's error again with what `setting()` said ("...; tiling 2 set").
  - **Resolution: done** (2026-11-18). **Test:** `test_a_turn_back_failing_after_a_value_was_set_says_it_was_set`
    (the real `_in_properties`, the setting returning "tiling 2", then `_parameters_back` raising) failed with the
    turn-back's error alone. **Cause:** the turn-back ran in a `finally`, and its error replaced what the setting
    returned. **Fix:** once the setting returned, `_in_properties` raises a turn-back's error again with what it set
    ("...; tiling 2 set"). Before that, an error is raised as it was. **Also covered:** `_in_properties` is the one
    turn-back after a change; the tiling and the environment both go through it. The abort handler's
    `_parameters_back` runs after an abort, which is said by the step's begun line.

- [x] **HLP-205 · Two docstrings say more than the code (follows HLP-203 and HLP-200, generation 3)** · `mcp_server/designer_helpers/view3d.py:499-506`, `:908-915` · confirmed · found 2026-11-18
  - **Defect.**
    - `_3d_set_up` says "They run `between`, when given, before each step" and "The same look runs after the turn,
      before Frame". Both hold only when the caller gives a watch. Run without one, `run` passes its own look instead
      of `between`. Line 915 also runs past the 120 characters the docs keep to.
    - `_commit_change` doesn't say it raises "...; <field> committed to <value>, not read back" when its second look
      fails (HLP-200's fix).

    Found by the helpers reviewer.
  - **Scenario.** A maintainer passes a `between` to a set-up run on its own and expects it run before each step.
  - **Fix.** Narrow `_3d_set_up`'s sentences to a caller giving its watch, and say the raise in `_commit_change`'s
    docstring (generation 3, docs only: the claims are narrowed, no check is added).
  - **Resolution: done** (2026-11-18). Docstrings only, narrowed. `_3d_set_up`'s says `between` runs before each
    step and after the viewpoint's turn when the caller gives a watch, and that a set-up run without one uses its own
    look instead. Its long line is wrapped. `_commit_change`'s says it raises "...; <what> committed to <value>, not
    read back" when its second look refuses.

- [x] **TST-554 · ROADMAP's 3D rules and two items still say more than the code (follows TST-550 and HLP-199, generation 3)** · `ROADMAP.md:65-67`, `:82-84`, `:103`, `:169` · confirmed · found 2026-11-18
  - **Defect.**
    - **Checked first** says the step's menu entries are looked up before anything changes, fields excepted. With
      mesh=, the entries under the mesh's material are found only after the switch: the set-up checks only
      `('Materials',)` then (`view3d.py:962`). TST-550 named this; its fix covered the fields only.
    - The **Off screen** rule and item 107 repeat the list of set-ups `set_3d_view` runs on screen ("camera moves,
      `graph=` and a mesh switch"), which `set_3d_view`'s docstring and DECISIONS.md hold. TST-550's fix removed the copy
      from item 90 only.
    - Item 85 reads the mesh "from the panel's title" in its first sentence, then says the set-up reads the Scene
      action, "one reader for both".

    Found by the docs reviewer.
  - **Scenario.** Item 88's implementer looks up the shader model in the material's submenu before a mesh switch,
    and finds the old mesh's material. Or a fourth on-screen case lands in DECISIONS.md, and the two ROADMAP copies stay
    at three.
  - **Fix.** Add the material's entries after a mesh switch to **Checked first**. Point the rule and item 107 to
    DECISIONS.md's 3D screenshot entry. Make item 85 read the mesh from the Scene action and the renderer from the
    title (generation 3, docs only: narrowed).
  - **Resolution: done** (2026-11-18). Docs only, narrowed. **Checked first** names the two kinds found as the step
    reaches them: a field of the Parameters panel, and, with mesh=, the entries under the new mesh's material. The
    **Off screen** rule and item 107 point to the set-ups DECISIONS.md's 3D screenshot entry lists. Item 85 reads the
    mesh from its checked Scene action and the renderer from the panel's title.

- [x] **TST-555 · The step-wait test's view case can't tell where the viewpoint records itself (follows HLP-200, generation 4)** · `tests/unit/test_view3d_helpers.py:1148` · confirmed · found 2026-11-18
  - **Defect.** `({'view': 'Top'}, 'view Top')` checks `'view Top' in` the error. The fake's `moved()` never raises,
    so only Frame's wait fails, and "view Top" is part of "view Top, framed". So the test still passes with
    `done.append('view %s' % view)` moved after `watched.moved(since)`, or with `done[-1] = step` moved after Frame's
    wait. HLP-200's resolution says the viewpoint records "view X" after its trigger and "view X, framed" after Frame.
    Found by the helpers and the tests reviewers.
  - **Scenario.** A later edit moves the record after the turn's wait. An error in that wait leaves the view unsaid
    again, and every test passes.
  - **Fix.** Generation 4, test only: narrow. Say in the case that it covers an error in Frame's wait, and expect
    "view Top, framed". Add no case.
  - **Resolution: done** (2026-11-18). Narrowed (generation 4, test only): the view case says it covers an error in
    Frame's wait, and expects "view Top, framed". No case added.

- [x] **TST-556 · The no-pattern check reads a graph another check builds, and its fact passes if that graph never reached the mesh (follows HLP-202, generation 2)** · `tests/test_all_tools/editor_panels_and_fit/checks.py:561-590`, `:548-550` · confirmed · found 2026-11-18
  - **Defect.**
    - `check_a_tiling_on_a_material_with_no_pattern_is_said_to_change_nothing` shoots `graph=VIEW3D_PLAIN`, which
      `check_opening_the_editors_graph_again_leaves_the_outputs_on_the_mesh` creates. The live-check skill wants what
      a check reads built by its category's `prepare(ctx)`. In the full run the order holds. Run alone, or moved
      earlier, both its checks fail with "a shot failed".
    - The designer fact `apart == 0` also holds when the plain graph's outputs never reached the mesh. The checker the
      check before left, shot at tiling 1 and 2, gives two identical renders too, and STALE then names the case all
      the same.

    Found by the tests reviewer.
  - **Fix.** Build `VIEW3D_PLAIN` in `preparations.prepare`, as `VIEW3D_GRAPH` is. Require the first render to show no
    pattern (`transitions` below the checker's).
  - **Resolution: done** (2026-11-18). **Test:** the check run on its own in a scratch run failed both its conditions
    with "a shot failed": the graph didn't exist. **Fix:** the category's `prepare` builds `VIEW3D_PLAIN` beside
    `VIEW3D_GRAPH`, in a Designer the self-test started, and the check before only opens it. The designer fact also
    requires the first render to show no pattern (at most 2 dark-light changes, against the checker's 6 or more). The
    check then passed on its own and after the check before (0 changes at tiling 1).

- [x] **HLP-206 · A turn-back failing after the setting failed replaces the setting's error, which said what was set (follows HLP-204, generation 5)** · `mcp_server/designer_helpers/view3d.py:542-567` · confirmed · found 2026-11-18
  - **Defect.** In `_in_properties`, when `setting()` raises, its error can say what was set: "...; tiling 2 set" (a
    wait failing after the commit). The `finally` then turns the panel back. If that raises too, `said` is None, so the
    bare `raise` re-raises the turn-back's error, which replaces the one in flight, and "tiling 2 set" is lost. Found
    by `/simplify`'s altitude reviewer while HLP-204 was addressed; the lead agent read the path.
  - **Scenario.** `set_3d_view(tiling=2.0)` whose wait fails after the commit, then whose turn-back fails: the error
    names only the turn-back, though the tiling is 2.
  - **Fix.** When the setting's own error is in flight, keep it and add the turn-back's after it.
  - **Resolution: done** (2026-11-18). **Test:**
    `test_a_turn_back_failing_after_the_setting_failed_keeps_the_settings_error` (the setting raising "the view took
    no frame; tiling 2 set", then the turn-back raising) failed with the turn-back's error alone. **Cause:** an error in
    a `finally` replaces the one in flight. **Fix:** `_in_properties` keeps the setting's own error and adds the
    turn-back's after it: "...; tiling 2 set; and turning the Parameters panel back failed: ...". An abort in flight is
    left as it was. **Also covered:** the "...; X set" wording of the tiling's wait, the environment's partial set and
    the turn-back after a setting now comes from one helper, `_with_set`, with the messages unchanged
    (`/simplify`).
