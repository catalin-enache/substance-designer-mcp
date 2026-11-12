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
command-line client, example and `scripts/`, **TST** tests and docs. A new area gets a new prefix, added here.

**Last used:** PLG-42, SRV-124, HLP-123, INS-33, TST-355.

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
| Low-medium | 0 | 4 |
| Low | 0 | 32 |
| **Total** | **0** | **36** |

## Review log

### 2026-11-12: branch `camera-angle-pan` against main (the diff only, ROADMAP item 74)

- **How:** two reviewers read the diff, one the helpers, the server and their unit tests (`view3d.py`, `views.py`,
  `test_view3d.py`, `test_view3d_helpers.py`, `test_finite_numbers.py`), one the live checks and the docs
  (`editor_panels_and_fit/checks.py`, `renders.py`, `designer_scripts/tool_3d.py`, README, GUIDE, ROADMAP, REVIEW.md).
  No tests were run. One scratch probe, in a Designer an agent started (its layout put back after: docked, Selection
  off, the Camera tool), measured:
  - pan in a wide and a tall viewport (627x253, 325x583): `[0.25, 0]` moved 0.249 of the width and `[0, 0.25]` 0.249
    of the height at both;
  - orbit at those sizes: `[90, 0]` from Front 0.00 from Designer's Right view, `[0, 90]` 0.30 and 0.45 from its Top;
    `[90, 90]` from Front 0.00 from `[0, 90]` from Right, two turns in one call;
  - drags of 1, 3 and 8 px, left and middle, with Selection on and off, and the tool switch under the Light tool: the
    Parameters panel unchanged every time;
  - a press under the Camera tool, the Light tool selected, then the release: hovering after, under either tool, moved
    nothing (0.00);
  - the rounded cube from the Bottom against the Top: 41.6.

  Settled as wrong:
  - the vertical pan's height/width factor, and orbit rates depending on the viewport's size (the code is right at
    every size measured);
  - short drags under the Selection toggle, or the tool switch, changing the Parameters panel;
  - a release sent after the Light tool is back (an abort landing on a drag's `finally`: the inner `finally` puts the
    Light tool back first) leaving a drag stuck: harmless;
  - a reversed vertical turn passing the orbit check: Bottom is 41.6 from Top, far over its bound of 3;
  - `camera.trigger()` not being checked: the live check shows it takes, and fails if it didn't.
- **Not verified:** the rates on a display of pixel ratio 2 (Retina). Every measurement, the checks' included, was at
  pixel ratio 1, the only display here being 1920 x 1080; Designer may count a drag in device pixels. What would check
  it: `editor_panels_and_fit`'s orbit and pan checks on a Retina Mac.
- **Resolutions assessed:** HLP-120 holds: the fix addresses its cause, and its unit test and live check fail without
  it. Questioned by TST-337 for its wording only.
- **Findings:** 4 Low: HLP-121, TST-335, TST-336, TST-337. Both reviewers found TST-336 and TST-337 in part.
- **Suggested order:** HLP-121 first, a result said and not done; then TST-335 and TST-336, which share the live checks;
  TST-337 last. Longest chain: HLP-120 → TST-337, generation 2.
- **Checked and found fine:**
  - the drags' signs and rounding (the unit tests' pixel numbers recompute); zero components give no drag; wrong
    lengths, out-of-range values and non-finite numbers are refused before anything reaches Designer;
  - the order of the steps (view, orbit, pan, zoom, tiling) and the pause after every drag, the wheel's too;
  - the tools looked up before any change, and only when a drag or the wheel goes to the viewport;
  - the Light tool comes back after an error or an abort at every line of the moving block;
  - a drag's button is always released;
  - the notes said before each change, and an error after one says what was set;
  - all three new checks skip in the user's Designer, and none leaves state a later check reads;
  - `tool_3d.py` as a designer script, the wheel snippet inline;
  - README, GUIDE and ROADMAP items 67, 77 and 90 agree with the code.


### 2026-11-12: branch `camera-angle-pan` against main, second review (the diff only)

- **How:**
  - Two reviewers read the diff, in the same areas as the first review. No tests were run.
  - Probes, in a Designer an agent started, with the shared preferences backed up and put back after (`defaults
    import`, and the three thumbnail keys the probes added deleted), measured:
    - a hover arriving in a drag, a mouse move with no button as the user's real mouse sends it, after the 5th of 10
      moves (HLP-122): it stops the drag wherever it is;
    - keyboard focus: the window's focus stayed on the graph view after `orbit`, `pan` and `zoom`;
    - the rounded cube's Front against Right: 16.99;
    - the Light tool's fact: the render before it against after it 0.00. The 0.61 first seen came from a render right
      after a mesh change, which differs from a settled one by 0.61.
  - Settled as wrong:
    - a synthetic press moving keyboard focus into the 3D view;
    - the Light tool fact's drags changing the light, or the light kept into the next Designer;
    - the docstring's sizes claiming more than was measured: the early probes measured the orbit too at 124x362 and
      419x443 (both rates at all five sizes).
- **Not verified:** unchanged, a display of pixel ratio 2. HLP-122's hover was simulated, not made with the real
  cursor, which would move the user's mouse; to Designer both are a move with no button held.
- **Resolutions assessed:** HLP-120, HLP-121, TST-335, TST-336 and TST-337 hold for what they fixed. Questioned:
  - HLP-121 by HLP-123 (a docstring's sign);
  - TST-335 by TST-340 and TST-341;
  - TST-336 by TST-339 and TST-340.
- **Findings:** 6:
  - Low-medium: HLP-122;
  - Low: HLP-123, TST-338, TST-339, TST-340, TST-341.
- **Suggested order:** HLP-122 first, a result said and not done when the user moves the mouse; then TST-338, the abort
  path's bookkeeping; the rest, docs and test details, together. Longest chain: generation 2 (HLP-121 → HLP-123,
  TST-335 → TST-340 and TST-341, TST-336 → TST-339 and TST-340, HLP-120 → TST-337).
- **Checked and found fine:**
  - the sub-pixel refusal and the carried values: signs, rounding (half a pixel rounds to 0 and is refused), messages;
  - every new check skips in the user's Designer, and puts the Light tool and the Selection toggle back in a `finally`;
  - the thresholds reject a rate 5 % off and a wheel step more or fewer;
  - the Light tool's fact can't pass with any of its three moves taking effect;
  - REVIEW.md's counts and Last used line;
  - README, GUIDE and ROADMAP items 67, 74, 77 and 90.


### 2026-11-12: branch `camera-angle-pan` against main, third review (the diff only)

- **How:**
  - Two reviewers read the diff, in the same areas as before. No tests were run.
  - Probes, in a Designer an agent started, with the shared preferences backed up and put back after (identical, 18,576
    keys), measured:
    - **The 3D view's widgets:** the viewport is a native window (`WA_NativeWindow`, a window handle of its own), with
      mouse tracking. Four `QLabel` children cover about 88 % of it (160x170 each in a 342x362 view; one shows the
      render's samples), without mouse tracking.
    - **A move routed as a real cursor's,** sent to the viewport's own window so Qt picks the receiver (HLP-122's
      note):
      - at (5, 5), outside the labels, it reached the viewport, and `orbit=[90, 0]` came out 60.27 from the Right
        view without the guard and 0.00 with it;
      - over a label, Qt dropped it before the viewport, and the turn came out 0.00 either way.
    - **Enter, Leave and HoverMove,** each sent to the viewport after a drag's 5th move: 0.00 from the Right view.
    - **Designer's event loop:** while a drag's events were sent, the guard saw exactly its 12 (a press, 10 moves, a
      release). A move posted before the 5th was dispatched after it, as the flag fell, and was dropped.
    - **The guard after an abort that skips its removal** (a `_drag` raising the plugin's `ScriptAborted` right after
      `installEventFilter`):
      - `installEventFilter` adds no reference (refcount 2, then 2);
      - the next job found the guard gone (its weak reference dead), and a move sent to the viewport passed no filter.
    - **The 3D dock's toolbars:** two, with the Scene Browser closed or open. One Camera and one Light action, both
      checkable.
    - **The Light tool and Selection set on, then Designer quit and started again:** Camera and off. No key in the
      preferences holds either.
  - **Settled as wrong:**
    - the guard seeing only events sent straight to the viewport (both reviewers): a real cursor's move reaches the
      viewport through its own window, where the guard drops it;
    - Enter, Leave or HoverMove ending a drag, so belonging in `MOUSE_EVENTS`;
    - real events dispatched while `_OWN_MOUSE` is True;
    - the guard staying on the user's view after an abort, and "held by this frame alone" being untrue;
    - another toolbar action named Camera or Light winning the lookup;
    - the checks' `finally` setting the Camera tool and Selection off changing the tool the user's Designer starts
      with: neither is kept across a restart.
  - **A crash the probes caused:** the agent's Designer aborted as it quit, after the routed-move probe. That probe's
    application-level event filter, written in Python, saw a timer event of Qt's pixmap cache (`QPMCache`, a global
    object of Qt's), which gave the cache a Python wrapper. At exit, after Python had shut down, PySide's clean-up of
    that wrapper threw, and `std::terminate` aborted Designer.
    - Read in the crash dump by hand, since no parser here reads arm64 dumps: the crashing thread's frames, named with
      `atos`, go from the exit handlers through `Q_QGS_pm_cache`'s destructor, `~QObject` and `~QVariant` to
      `libpyside6` and `std::terminate`.
    - Reproduced: such a filter on for 40 s, then a quit, left a dump with the same frames; the same wait without the
      filter left none.
    - The branch's code installs no such filter: its only one, the guard, is on the viewport.
  - **Dropped:** lines over 120 characters in two test docstrings and a comment. No rule checks them (E501 is off), and
    they change nothing anyone does.
- **Not verified:** unchanged, a display of pixel ratio 2. A move made with the real cursor itself would move the
  user's mouse. The routed probe enters at the viewport's own window, after macOS has picked it.
- **Resolutions assessed:**
  - Hold up: HLP-122 (measured on the routed path), HLP-123, TST-338, TST-339 and TST-340.
  - Questioned: TST-341, by TST-342.
- **Findings:** 1 Low: TST-342.
- **Suggested order:** TST-342 alone, a change of order in a detail. Longest chain: TST-335 → TST-341 → TST-342,
  generation 3. The code has no open finding.
- **Checked and found fine:**
  - The drags' maths: signs, rounding, the vertical pan factor, `-0.0` skipped.
  - `_OWN_MOUSE`: no abort leaves it True while a guard is on.
  - The abort handler's release and the Light tool put back.
  - The server's zero handling and refusals.
  - Each new unit test fails without the line it guards.
  - Every new check:
    - checks each shot;
    - skips in the user's Designer;
    - puts the tool and the toggle back in a `finally`;
    - has thresholds that reject a stopped drag.
  - README, GUIDE and ROADMAP items 67, 74, 77 and 90 match the code.

---

### 2026-11-12: branch `camera-angle-pan` against main, fourth review (the diff only)

- **Scope:** what changed since the third review (72a8352): the crash tooling (crash uploads off in `launch_designer`,
  `scripts/read_crash_dump.py`, `alone.close` naming a dump), its tests and docs, and TST-342's fix. The three reviews
  before covered the rest of the diff.
- **How:** two reviewers read the diff, one `server_tools/lifecycle.py`, `alone.py`, the live check, their unit tests
  and the docs, one the dump reader, `tests/unit/minidumps.py` and their tests. No tests were run. Every suspicion was
  settled by reading the code (and, for INS-29, Crashpad's database: a finished report waits in `pending/` until its
  upload is done or skipped); no probe was needed. One reviewer read only the structure of a real dump (counts, sizes,
  offsets, one module's UUID), no memory, annotations or attachments. Two folders were listed, by name only: no dump
  in the user's `Sentry-Crashpad` (`new/`, `pending/`, `completed/` all empty), two in an agent's `completed/`.
- **Resolutions assessed:** TST-342 holds (the scratch run's line shows the pan and the toggle).
- **Findings:** 2 Low-medium (SRV-120, TST-343), 11 Low (SRV-121, SRV-122, TST-344 to TST-347, INS-28 to INS-32).
  All generation 1; no chain grew, and TST-335 → TST-341 → TST-342 ended at generation 3.
- **Suggested order:**
  - `launch_designer`'s crash uploads together: SRV-120, SRV-121, SRV-122, then TST-344 and TST-346, whose wording and
    check follow from them.
  - The unit tests' isolation: TST-343, TST-345.
  - The dump reader and its tests: INS-31 and INS-32 (small), INS-28 with TST-347's frame-walk tests, INS-29, INS-30.
- **Checked and found fine:**
  - `_crash_uploads_off` never touches the user's home: no home of its own gives `''`, and `_own_home` is None off
    macOS, so `import fcntl` is never reached on Windows. A missing, short, read-only or foreign file is left as it was,
    with a sentence; the write lands before the lock is dropped.
  - The settings' layout: the magic, options at offset 8, only bit 0 cleared, the rest kept (the unit test compares
    them).
  - `close_with`: the dumps compared with those before the quit, the wait of at most 10 s, none without a quit; the new
    alone tests fail without the wait or the detection.
  - The reader's offsets match the format and a real dump (stream sizes, the exception's context at +164, pc at +264,
    arm64 and macOS in the system info, CrashpadInfo's module list at +48); `minidumps.py` builds the same layout.
  - The pointer-authentication mask clears exactly the real dump's own `address_mask` (`0xffff800000000000`).
  - The walk always ends (with its `caller <= fp` guard; TST-347), and `read64` checks bounds.
  - Privacy: only `attachments/<id>/log.txt` is opened, its last part fixed, so nothing reaches `__sentry-event`; the
    test checks the email isn't printed.
  - Python 3.9; `atos` called with a list, its timeout caught; refusals of another CPU or system; SIGABRT decoded.
  - The editor detail's format: six placeholders, six values.
  - GUIDE's event-filter rule, ROADMAP item 95 and the two new decisions agree with the module's docstring.

### 2026-11-12: branch `camera-angle-pan` against main, fifth review (the diff only)

- **Scope:** what changed since the fourth review (887afbb): the fixes of its 13 findings, in
  `server_tools/lifecycle.py`, `scripts/read_crash_dump.py`, their tests and docs.
- **How:** two reviewers read the diff in the same two areas, each also judging its findings' resolutions. No tests
  were run, and no probe was needed: every suspicion was settled by reading. One reviewer read offsets only in the
  real dump (its directory, module list and CodeView records; all 1206 modules carry an `RSDS` record) and listed the
  formats of Designer's Mach-O files (235 universal with one arm64 slice, 118 thin; none 64-bit universal).
- **Resolutions assessed:**
  - Hold up: SRV-121, SRV-122, TST-343, TST-345, TST-346, INS-28, INS-32, and INS-30's fix (its tests: TST-350).
  - Questioned: SRV-120 by SRV-123, TST-344 by TST-348, TST-347 by TST-349 and TST-350, INS-29 by TST-351, INS-30 by
    TST-350, INS-31 by INS-33.
- **Findings:** 6 Low, all generation 2: SRV-123, INS-33, TST-348 to TST-351.
- **Note, not an entry** (a value a test doesn't put back): under SRV-120.
- **Suggested order:** SRV-123 with TST-348 (what `launch_designer` turns off, and the docs saying when); INS-33; the
  reader's tests: TST-349, TST-350; TST-351 last. Longest chains: SRV-120 → SRV-123 and TST-347 → TST-349, generation
  2; none past it.
- **Checked and found fine:**
  - `_already_running` writes only in the recorded home of an agent's Designer; no record, or a stale or unclear one,
    gives None and nothing is touched. On every "already running" result it reads the record, and with one lists the
    processes (tens of ms on macOS); on Windows no record is ever written.
  - The new unit tests each fail without their fix; no older assertion was weakened (the renamed test gained one).
  - The autouse purge in `test_selftest_alone.py` runs after monkeypatch's undo; no later file looks the modules up
    unpurged.
  - The reader: the walk's cap (64 frames, or 63 when the first record repeats the link register), the first record's
    comparison only, `caller <= fp` still ending a record pointing to itself; the CodeView offset (+76) and the
    Mach-O offsets; `_names`' grouping by path and base, one line per skipped module, its frames still listed;
    `_newest` passing over a file gone; `_log_tail` reaching the database from a bare name, `completed/` or `../`;
    Python 3.9; nothing new opens `attachments/`.
  - The `pending` wording in README, AGENTS and GUIDE matches `dump_folders`.

### 2026-11-12: branch `camera-angle-pan` against main, sixth review (the diff only)

- **Scope:** what changed since the fifth review (cbc8b76): the fixes of its six findings and of the note under
  SRV-120.
- **How:** two reviewers read the diff in the same two areas, each also judging its findings' resolutions. No tests
  were run; every suspicion was settled by reading, but one that can't be checked here (below).
- **Resolutions assessed:**
  - Hold up: SRV-123's fix (its tests: TST-354), TST-348, TST-350, the note under SRV-120, and INS-33's and TST-351's
    fixes (their tests and comment: TST-353, TST-355).
  - Questioned: SRV-120 by SRV-124 (its "Also covered" left `quit_designer` out), TST-349 by TST-352, INS-33 by
    TST-353, SRV-123 by TST-354, TST-351 by TST-355.
- **Findings:** 5 Low: SRV-124 (generation 2, the tools' code), TST-352 to TST-355 (generation 3, tests only: their
  fixes make no check stronger).
- **Not verified:** whether the self-test finds a crash dump on Windows at all. As one reviewer recalls Crashpad's
  source, its Windows database keeps every report in `reports\`, its state in a `metadata` file, with no `completed\`
  or `pending\`; then `common.crash_dumps`' Windows folder finds nothing, and its "no crash dump" checks pass without
  looking. No Windows here: a listing of a Windows Designer's `Sentry-Crashpad` folder would settle it, and, if so, the
  docstring and README would say macOS.
- **Dropped:** the crash watch giving a report moved between two steps' listings to both, one per path: the listings are
  made one after the other after its 10 s wait, a window of milliseconds.
- **Suggested order:** SRV-124 first (the tools' code); then TST-354, TST-355, TST-352, TST-353, each a line or two.
  Longest chains, generation 3: TST-347 → TST-349 → TST-352, INS-31 → INS-33 → TST-353, SRV-120 → SRV-123 → TST-354,
  INS-29 → TST-351 → TST-355.
- **Checked and found fine:**
  - `_with_uploads_off` keeps the refusal as it was when the settings were written; `homes[-1]` is always an agent's
    folder; with no record nothing is written.
  - Every difference of crash-dump sets goes through `new_dumps` (`__main__`'s end check, `alone.close_with`, the crash
    watch, the pool's quits, lifecycle's clean-up); `_report` keys real paths right; `_holds_a_crash_dump` reads
    `pending/`.
  - `_file_build`: an arm64 part past the file's end, a header under 32 bytes, no parts, a part pointing back at the
    universal header: each gives None; a load command running past what was read raises what is caught; the loop moves
    at least 8 bytes a time. `_build` rejects all it did before and more.
  - `_within`: the timer cancelled before the old handler comes back; `_TooLong` isn't an OSError; nothing on Windows.
  - The 64-bit universal branch left no trace in scripts, tests or docs.

## High

## Medium-high

## Medium

## Low-medium

- [x] **HLP-120 · zoom= under the 3D view's Light tool moves nothing and says it zoomed** · `mcp_server/designer_helpers/view3d.py` (set_3d_view, the zoom step) · measured · found 2026-11-12
  - **Defect.** The wheel steps go to the viewport whatever tool its toolbar has selected: `_wheel(viewports[0], zoom,
    WHEEL_PAUSE)`, then `'%+d wheel steps' % zoom` in what it set. Under the Light tool, the wheel doesn't move the camera.
  - **Scenario.** Found while measuring ROADMAP item 74, in a Designer an agent started: the plane seen from the top,
    then 5 wheel steps on the viewport, went from 277 to 419 px wide under the Camera tool, and from 276 to 277 px under
    the Light tool. A user who left their 3D view on the Light tool (L) gets `screenshot_designer('3d', zoom=5)` saying
    "+5 wheel steps" and a render no closer.
  - **Fix.** Select the Camera tool for the wheel, then the Light tool again.
  - **Resolution: done**.
    - **Test:** `test_under_the_light_tool_the_camera_tool_moves_the_camera_then_the_light_tool_comes_back[zoom]`
      (`tests/unit/test_view3d_helpers.py`) failed, since no tool was selected around the wheel; the live check
      `editor_panels_and_fit.check_the_camera_moves_under_the_light_tool_too` failed in its scratch run, the plane 1.01x
      as wide for `zoom=3` under the Light tool, against 1.37 expected. Its designer fact, the wheel under the Light tool
      leaving the plane 275 px then 277 px wide, passed before and after, as a fact does.
    - **Cause:** the toolbar's Camera and Light tools are one group, and under the Light tool neither the wheel nor a
      drag moves the camera. The zoom step only knew the viewport.
    - **Fix:** `set_3d_view` looks up both tools before any change (`_navigation_tools`, refusing a toolbar without
      them) whenever the wheel or a drag goes to the viewport; reads whether the Light tool is selected before
      changing anything; selects the Camera tool; then `_tool_back` selects the Light tool again in a `finally`, and
      again in the abort's handler, run untraced, for an abort landing on that `finally`. The live check also sees the
      Light tool selected after.
    - **Also covered:** the new `orbit=` and `pan=` drags go through the same switch, with the live check measuring a
      pan under the Light tool. `view=`, `mesh=`, `graph=` and `tiling=` go through menus and panels, not the
      viewport, so they leave the tool alone (`test_without_orbit_pan_or_zoom_the_tools_are_left_alone`); `view='Front'`
      turned the camera under the Light tool in the probe, the others weren't measured under it.
  - Questioned by TST-337 (2026-11-12).
  - Note (2026-11-12, TST-337): "reads whether the Light tool is selected before changing anything" means right before
    the Camera tool is selected, after any mesh, graph and view steps; in the scenario, 419 px is the width of the
    probe's panel, at whose edge the plane was cut, not a zoom (5 steps would make it about 467 px).

- [x] **HLP-122 · The user's mouse moving over the 3D view during a drag stops the turn or pan, which is said as done** · `mcp_server/designer_helpers/view3d.py` (`_drag`, `_mouse`) · measured · found 2026-11-12
  - **Defect.** `_mouse` sends each synthetic event, then `_process_events(2)`, which dispatches whatever real events
    are waiting. A real mouse move over the viewport, with no button held, ends Designer's drag, and the drag's moves
    after it do nothing. The step still says the whole turn or pan.
  - **Scenario.** Probe: the helpers' `_mouse` wrapped so that a hover (a `MouseMove` with `NoButton` held) arrives
    after the 5th of a drag's 10 moves, at the viewport's corner, on the drag's own point, or 50 px from it.
    - `orbit=[90, 0]` from Front: 60.27 from Designer's Right view in all three cases, against 0.00 without the hover;
      said "orbit 90 degrees right".
    - `orbit=[90, 90]`: 57.4 from `[0, 90]` from Right.
    - `pan=[0.25, 0]`: 0.099 of the view, against 0.249.
    - A drag takes 2 to 6 ms, while a moving mouse sends an event every 8 to 16 ms. So a user moving their mouse over
      the 3D view while an agent sets it up gets a view other than the one said, quite likely.
    - The hover was simulated (moving the real cursor would move the user's mouse); to Designer both are a move with
      no button held.
  - **Fix.** While a drag runs, drop every mouse event the viewport gets that the drag isn't sending itself: an event
    filter on the viewport, letting through only the events `_mouse` sends, removed in a `finally` and by the abort's
    handler. A live check injects a hover mid-drag, as the probe did, and sees the turn come out whole.
  - **Resolution: done**.
    - **Test:**
      - `check_the_users_mouse_doesnt_stop_a_turn_or_pan` (`editor_panels_and_fit`) sends a hover after a drag's 5th
        move, by itself, not through `_mouse`. It failed in its scratch run, 60.16 from the Right view and 0.099 of the
        view, as the probe measured.
      - Unit tests (`tests/unit/test_view3d_helpers.py`) failed:
        - `test_a_drag_is_a_press_moves_and_a_release_from_the_middle_then_a_pause_all_guarded`: no guard;
        - `test_a_drag_whose_move_fails_still_releases_its_button_and_removes_its_guard`;
        - `test_the_mouse_events_the_helpers_send_are_marked_for_the_guard_while_sent`: no marking.
    - **Cause:** a move with no button held ends Designer's drag, and `_mouse`'s `_process_events` dispatches the
      user's real mouse between the drag's moves.
    - **Fix:**
      - `_mouse` marks its events while it sends them (`_OWN_MOUSE`).
      - `_drag` installs `_mouse_guard()` on the viewport, an event filter dropping every mouse event (`MOUSE_EVENTS`,
        the wheel included) `_mouse` isn't sending. It is on from before the press to after the pause, since a press
        in the pause would undo the drag too, and removed in a `finally`.
      - The guard is held by `_drag`'s frame alone, so it goes with it after an abort that skips the removal.
      - With it, the check's turn was 0.00 from the Right view and its pan 0.249. The editor category: 46 of 46.
    - **Also covered:**
      - The wheel steps of `zoom=` send no press, so a hover can't end them; a real wheel turned during them would add
        to them, unguarded, as before this branch.
      - The menus and the Explorer's context menu (`graph=`, `view=`, `tiling=`) take no drag.
  - Note (2026-11-12, third review):
    - A move routed as a real cursor's, through the viewport's own native window, is dropped by the guard too. Without
      the guard, one at (5, 5) left the turn 60.27 from the Right view; with it, 0.00.
    - Four labels without mouse tracking cover about 88 % of the viewport, and Qt drops a move over them before the
      viewport. So a real cursor ends a drag only over the rest: the margins, and the cross between the labels.
    - The check's hover at (5, 5) is in a margin.

- [x] **SRV-120 · Crash uploads stay on in an agent's Designer a launch finds already running, or whose Home screen it couldn't leave** · `mcp_server/server_tools/lifecycle.py` (launch_designer) · confirmed · found 2026-11-12
  - **Defect.** Uploads are turned off only by the call that started the Designer, once it answers, and after the Home
    screen is left: `return 'Designer already running on port %d: %s' % (port, _control('status', ...))` at the top,
    `if running: return note + 'Designer already running on port %d: %s' % (port, status)` in the wait, and
    `home = _bridge(_helpers_call('leave_home_screen()'), ...)` before `uploads = _crash_uploads_off(...)`.
  - **Scenario.** `launch_designer(wait_s=30)` starts one that needs 45 s and says to call it with a larger `wait_s`
    (or, past its start, "calling this again waits for it"). The next call finds it answering, or waits for it as
    already running, and returns "already running": `_crash_uploads_off` never runs, and Sentry turned uploads on as it
    started. A crash then sends its report with the user's Adobe account, against the user's choice (DECISIONS.md,
    Bridge and quitting; its Reopen if doesn't hold: this is the implementation). The same if `leave_home_screen`
    raises (a bridge timeout): the next call says "already running".
  - **Fix.** Turn them off on both "already running" returns too, with `_agent_home(port)` (None for the user's
    Designer, whose settings stay untouched), and before leaving the Home screen. Unit tests: an agent's record with a
    home and uploads on, `_send` answering, then `launch_designer()`; `leave_home_screen` raising.
  - **Resolution: done**.
    - **Test:** in `tests/unit/test_lifecycle_env.py`,
      `test_launch_turns_crash_uploads_off_in_an_agents_designer_already_running` (answering, and waited for) and
      `test_launch_turns_crash_uploads_off_before_leaving_the_home_screen` failed, uploads still on (`1 == 0`);
      `test_launch_says_when_an_agents_designer_already_running_keeps_crash_uploads_on` failed, no sentence. Live:
      `lifecycle.check_launch_on_another_port`'s new step turns uploads on in its second Designer, as Designer does as
      it starts, then calls `launch_designer` on that port. In its scratch run it failed, "Designer already running on
      port 57699: ... | uploads: on", and passed after the fix, "uploads: off".
    - **Cause:** only the call that started a Designer turned uploads off, and only after leaving the Home screen.
    - **Fix:** `_already_running` (`server_tools/lifecycle.py`) turns them off with `_agent_home(port)` on both
      "already running" returns, and says so when it can't; the started branch turns them off before leaving the Home
      screen. The module's docstring says when, and that a crash before the Designer answers may still be uploaded.
    - **Also covered:** every return of `launch_designer` with a Designer answering: the two "already running" and the
      start. `designer_status` and `quit_designer` start nothing. The user's Designer has no record, so its settings
      are left alone (`test_the_users_designer_already_running_keeps_its_crash_settings`, renamed from
      `test_a_designer_already_running_keeps_its_crash_settings`).
  - Note (2026-11-12, fifth review): the live check's new step turns uploads on in its second Designer and puts
    nothing back if the launch then fails to turn them off; the quit that follows would upload a crash at that
    moment. A `finally` turning them off would close it.
  - Note (2026-11-12): fixed: the step puts them back in a `finally` (`crash_reports.uploads_off`). With a scratch
    break leaving them on, its check failed ("uploads: on") and the `finally` turned them off; without it, all passed.
  - Questioned by SRV-123 (2026-11-12).
  - Questioned by SRV-124 (2026-11-12).

- [x] **TST-343 · The crash-upload unit tests write into the real Designer data folder on Windows, and fail there** · `tests/unit/test_lifecycle_env.py` (`_crashpad_settings` and the four tests using it) · confirmed · found 2026-11-12
  - **Defect.** On Windows `_designer_data_dir(home)` ignores `home` and returns `%LOCALAPPDATA%\Adobe\Adobe Substance 3D
    Designer`, which conftest doesn't redirect; the helper then runs `path.parent.mkdir(parents=True)` and
    `path.write_bytes(content)`. The tests have no Windows skip.
  - **Scenario.** The unit suite on Windows (AGENTS.md has it run there). Where Designer has run, `mkdir` raises
    `FileExistsError` and four tests error, failing the final check. Where it never ran, the tests create the folder
    and leave a fake `settings.dat` (uploads on, a made-up client ID) in the user's real Designer data folder, and
    `_crash_uploads_off` then fails on `import fcntl`.
  - **Fix.** Skip them on Windows (`skipif(sys.platform == 'win32', ...)`, as the module's other macOS-only tests), and
    assert in `_crashpad_settings` that the path is under `home`.
  - **Resolution: done**.
    - **Test:** `test_crash_settings_are_planted_only_under_the_home` simulates Windows (`sys.platform`, and
      `LOCALAPPDATA` in the test's folder). It failed: the helper wrote there, "DID NOT RAISE".
    - **Fix:** `_crashpad_settings` asserts that the path is under the home, and the tests that plant settings are
      skipped on Windows (`_HOMES_OF_THEIR_OWN`; the two about a recorded Designer already were).

## Low

- [x] **HLP-121 · An orbit or pan under a pixel isn't done, and is said as set** · `mcp_server/designer_helpers/view3d.py` (`_orbit_drags`, `_pan_drags`, set_3d_view's orbit and pan steps) · confirmed · found 2026-11-12
  - **Defect.** The drags are rounded to whole pixels and a drag of 0 is dropped (`drags = [(round(-orbit[0] /
    ORBIT_ACROSS), 0), (0, round(orbit[1] / ORBIT_UP))]`, then `if d != (0, 0)`), but the step says the values asked
    for: `begin('orbit ' + _directions(cast(list[float], orbit), ' degrees'))`. The server sends any value that isn't 0
    (`'orbit': orbit if orbit and any(orbit) else None`).
  - **Scenario.** `screenshot_designer('3d', orbit=[0.2, 0])`: `round(-0.2 / 0.45)` is 0, so nothing moves and the result
    is "3D view: ", empty. `orbit=[0.1, 30]` says "orbit 0.1 degrees right, 30 up" with only the turn up done. Under
    about 0.23 degrees across, 0.18 up or down, or 1/712 of the view. Every other value is said as asked, rounded to
    the 0.45 degrees a pixel: `[10, 0]` drags 22 px, 9.9 degrees.
  - **Fix.** Say what the drags carry (a pixel times its rate), or refuse a value that isn't 0 but rounds to no
    pixel, before any change, saying the smallest step; a unit test for each case.
  - **Resolution: done**.
    - **Test:** `test_a_turn_or_pan_under_a_pixel_is_refused_before_anything_changes` (five cases: across, across
      with a turn up, down, right, up with a pan right) and `test_the_turn_and_pan_said_are_what_the_drags_carry`
      (`tests/unit/test_view3d_helpers.py`) failed: nothing refused, and "orbit 10 degrees right, 20 up" said for the
      9.9 and 19.95 degrees dragged.
    - **Cause:** the drags were rounded to whole pixels, and the step said the values asked for.
    - **Fix:** `_drags` (`view3d.py`), under `_orbit_drags` and `_pan_drags`, computes the pixels, refuses a value
      that isn't 0 but rounds to no pixel, before any change ("orbit's 0.2 degrees right is less than one pixel's
      drag, 0.45 degrees: it would do nothing"), and returns what the drags carry, which `_directions` says to 3
      digits. The live checks read the values said back: "orbit 89.9 degrees up" for `[0, 90]`, within half a degree.
    - **Also covered:** `zoom` is whole wheel steps already (an int, said as sent); `tiling` is said from the spin box
      after it is set (`_set_tiling`); the unit tests of the line and the notes say the carried values now.

- [x] **TST-335 · Three live checks pass on a wrong result** · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_pan_moves_the_view_and_zoom_comes_closer_to_the_middle`, `check_the_camera_moves_under_the_light_tool_too`) · confirmed · found 2026-11-12
  - **Defect.**
    - The pan windows, `all(0.22 <= m <= 0.28 for m in moved)` and `0.22 <= moved <= 0.28`, also hold content that
      follows the mouse 1:1: the 89 px drag of `pan=[0.25, 0]` would move it 89/338 = 0.263 of the self-test's
      338 px wide view. So the rate the code relies on (a view's width every PAN_WIDTH pixels, whatever the size) isn't
      told apart from the obvious other one.
    - Zoom after pan, `STEP**4 * 0.9 <= grown <= STEP**4 * 1.1`, takes 1.366 to 1.670: three steps (1.368) pass for
      four. That is the case the pause before the wheel guards ("wheel steps right after a drag zoomed less").
    - The designer fact "under the 3D view's Light tool the wheel doesn't move the camera" discards its snippet's
      result (`await c('execute_designer_code', {'code': ctx.helper_source + WHEEL_UNDER_ANY_TOOL})`), so a snippet that
      raises sends no wheel and the fact passes.
  - **Scenario.** A Designer whose pan follows the mouse, or a pause too short for the wheel after a pan, passes every
    check, and `pan=` and `zoom=` say what they didn't do in a view of another size. The fact passes after a rename of
    `_wheel` or `_3d_dock`.
  - **Fix.** Pan windows of about 0.24 to 0.26 (measured 0.246 to 0.249); zoom after pan within 5 %, as the zoom
    check's ("two steps (1.23x) or four (1.52x) fail"); a marker printed after the wheel, required by the fact.
  - **Resolution: done**.
    - **Test:** the checks, changed first, run against the helpers broken on purpose in scratch runs (each restored
      after):
      - with `PAN_WIDTH = 338`, a rate 5 % off, both pan checks failed at 0.234 of the view, which 0.22 to 0.28 took;
      - with one wheel step lost after a pan, zoom after pan failed at 1.37x;
      - with the snippet raising, the Light tool's designer fact failed for its missing marker.
    - **Fix:**
      - pan windows of 0.24 to 0.26, and the values said read back within 0.005;
      - zoom after pan within 5 % ("three steps (1.37x) or five (1.69x) fail");
      - the snippet prints what it sent (`SENT=wheel,pan,turn`), which the fact requires. Its first run with the
        marker failed for real: the snippet, which now also drags, held no reference to the main window, and the
        viewport's wrapper went stale (GUIDE.md, Designer UI); it holds them now.
    - **What stays:** at the self-test's view, about 340 px wide, near PAN_WIDTH's 356, no window can tell the pan's
      rate from content following the mouse one to one. Only a view of another size could, and resizing the dock is
      carried to the next Designer by the preferences plist (ROADMAP item 67). The pan check's docstring and
      `view3d.py`'s say so, with the five sizes the probes measured.

- [x] **TST-336 · Cases and facts the branch relies on with no check** · `tests/test_all_tools/editor_panels_and_fit/checks.py`, `mcp_server/designer_helpers/view3d.py` (module docstring), `tests/unit/test_view3d.py` · confirmed · found 2026-11-12
  - **Defect.**
    - No live check sends two turns, or a turn and a pan, in one call. Only `'orbit': [90, 0]` and `'orbit': [0, 90]`
      run, so the pause between left-drags is unchecked ("two turns sent back to back came out wrong"). The review's
      probe found it right: `[90, 90]` from Front 0.00 from `[0, 90]` from Right.
    - Module docstring facts no designer fact re-measures:
      - "under Light, neither drags nor the wheel move the camera": only the wheel;
      - "Selection, a toggle beside them, changes nothing a drag does";
      - the rates "whatever the zoom and the viewport's size": every check runs at one size; the review's probe
        measured 627x253 and 325x583, and orbit's sizes aren't said;
      - "it goes on over the top", which nothing relies on.
    - No unit test passes `orbit=[0, 0]` or `pan=[0, 0]`: without `any(...)` the server would send them, and refuse
      them with `panel='graph'`, and every test would pass.
  - **Scenario.** A change in Designer, or in the code, to any of these passes the suite: `orbit=[30, 20]` could come
    out wrong unseen.
  - **Fix.**
    - A check comparing `view='Front', orbit=[90, 90]` with `view='Right', orbit=[0, 90]`.
    - Designer facts for drags under the Light tool and under Selection, or the docstring narrowed to what is checked.
    - The sizes measured written in the docstring. A check at a second size would resize the dock, which the
      preferences plist carries to the next Designer (ROADMAP item 67).
    - "Over the top" removed.
    - A unit test of the zeros.
  - **Resolution: done**.
    - **Test:**
      - `check_orbit_turns_the_camera_around_what_it_looks_at` now compares `[90, 90]` from Front with `[0, 90]` from
        Right. With the helpers' `DRAG_PAUSE = 0.0`, in a scratch run, it failed at 58.5; restored, 0.00.
      - `test_a_turn_pan_or_zoom_of_zero_sets_nothing_up` (`tests/unit/test_view3d.py`) failed, 4 cases, with the
        server's `any(...)` removed; restored, it passes.
      - The designer facts pass, as facts do: under the Light tool, 3 wheel steps, a middle-drag and a left-drag
        moved no edge of the plane; with Selection on, `orbit=[90, 0]` from Front was 0.00 from the Right view and
        the Parameters panel kept what it showed.
    - **Fix:**
      - the two-turn comparison;
      - `check_the_camera_moves_under_the_light_tool_too`'s fact covers both drags as well as the wheel;
      - `check_a_drag_turns_the_camera_alike_with_selection_on`, with `tool_3d.py` setting the toggle and turning it
        off again after;
      - `view3d.py`'s docstring gives the sizes measured (124x362 to 627x253 and 325x583 px, a display of pixel
        ratio 1) and no longer says "it goes on over the top";
      - the zeros' unit test.
      - The editor category: 44 of 44 in its scratch run.

- [x] **TST-337 · HLP-120's resolution and ROADMAP item 74 say slightly more than was shown** · follows HLP-120, generation 2 · `REVIEW.md` (HLP-120), `ROADMAP.md` (item 74) · confirmed · found 2026-11-12
  - **Defect.**
    - HLP-120's resolution says set_3d_view "reads whether the Light tool is selected before changing anything".
      It reads it right before selecting the Camera tool, after any mesh, graph and view steps.
    - Its scenario's "went from 277 to 419 px wide under the Camera tool" is the plane cut at the edge of the
      probe's 419 px wide panel, not a zoom (5 steps would make it about 467).
    - ROADMAP item 74's "zoom after pan staying on a corner, both under the Light tool" reads as if the corner check
      ran under the Light tool. The Light tool's check zooms 3 steps and pans `[0.25, 0]`, each on its own.
  - **Scenario.** The next agent reading them takes them as stated.
  - **Fix.** Narrow them. A note under HLP-120, whose entry isn't rewritten; ROADMAP's sentence: "zoom and pan again
    under the Light tool".
  - **Resolution: done**. Docs only, no test: a note under HLP-120, whose entry isn't rewritten, narrows both
    sentences; ROADMAP item 74 says "zoom and pan again under the Light tool", and adds the two-turn check and the
    designer facts TST-336 added.

- [x] **HLP-123 · `_drags`' docstring gives `steps` the wrong sign** · follows HLP-121, generation 2 · `mcp_server/designer_helpers/view3d.py` (`_drags`) · confirmed · found 2026-11-12
  - **Defect.** It says "`steps` a pixel across and down". The code makes a pixel dragged right or down carry
    `-steps`: `pixels = [round(-values[0] / steps[0]), round(-values[1] / steps[1])]`, carried
    `-pixels[0] * steps[0]`. So `steps` is what a pixel dragged left and up carries: `(0.45, -0.35)` for the orbit,
    where a pixel down raises the camera 0.35.
  - **Scenario.** Someone adding a drag, or changing a rate, by this docstring passes signs reversed, and both
    directions come out wrong. The callers' docstrings are right.
  - **Fix.** "`steps` what a pixel dragged left and up carries, [right, up]".
  - **Resolution: done**. A docstring, no test: `_drags`' now says "`steps` what a pixel dragged left and up carries,
    [right, up]".

- [x] **TST-338 · No unit test sees the real `_drag` hold its button for the abort handler** · `tests/unit/test_view3d_helpers.py`, `mcp_server/designer_helpers/view3d.py` (`_drag`) · confirmed · found 2026-11-12
  - **Defect.** The abort handler releases what `pressed` holds (`for button, x, y in pressed: _release(...)`). The real
    `_drag` puts `(button, end x, end y)` there before its press and takes it out after its release. The tests of the
    real `_drag` only assert `pressed == []` at the end. The test of the handler fakes `_drag` with its own
    `pressed.append(...)`.
  - **Scenario.** Dropping the append and the remove, moving the append after the press, or storing the start point
    passes every unit test. An abort landing on the release would then leave the viewport's button held.
  - **Fix.** The `Mouse` fake records `list(pressed)` at each event. Assert that the press, every move and the release
    saw `[(LeftButton, 0.0, 200.0)]` for the `-200, 50` drag.
  - **Resolution: done**.
    - **Test:** `test_a_drag_holds_its_button_where_the_abort_handler_looks_while_it_is_down`. The `Mouse` fake records
      what `pressed` holds at each event: `[(LeftButton, 0.0, 200.0)]` at the press, every move and the release.
    - **Seen failing:** with the append moved after the press, it failed; restored, it passes.

- [x] **TST-339 · The Selection fact can pass when nothing turned, and the docstring claims both drags** · follows TST-336, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_a_drag_turns_the_camera_alike_with_selection_on`), `mcp_server/designer_helpers/view3d.py` (module docstring) · confirmed · found 2026-11-12
  - **Defect.**
    - The fact requires `near < 3.0` from the Right view alone, with no "nearer than the view beside it" guard as the
      orbit check has. Its first shot, the set-up putting the rounded cube in front, is never checked with
      `is_image`.
    - The docstring says "Selection ... changes nothing a drag does: the camera turned alike, the Parameters panel
      kept". The fact sends only a left-drag (`orbit=[90, 0]`).
  - **Scenario.**
    - If that first set-up fails before any change, a Plane stays from the check before. Seen edge-on from Front and
      from Right, it gives two near-empty renders, and the fact passes whatever the drag did.
    - With the cube in place, a turn that didn't happen fails today: the probe measured Front 16.99 from Right.
    - A middle-drag under Selection is checked nowhere.
  - **Fix.** Keep the first shot, check it, and require `near < min(3.0, 0.5 * difference(turned, front))`. Narrow
    the docstring to a turn, or add a pan to the fact.
  - **Resolution: done**.
    - **Test:** in a scratch run, the Selection fact run after the pan check, its graph's name made one that isn't
      there.
      - Before: it passed with its set-up failed, at 0.00 from the Right view, a plane seen edge-on.
      - After: it fails, naming the failed shot.
    - **Fix:**
      - The fact keeps its first shot and checks every shot.
      - It requires the turn nearer the Right view than half the Front: `near < min(3.0, 0.5 * far)`.
      - With Selection on it also pans, `pan=[0.25, 0]` within 0.24 to 0.26, so the docstring's "changes nothing a drag
        does" is checked for both drags.

- [x] **TST-340 · The self-test's view size: one note in two places, and not fixed** · follows TST-335 and TST-336, generation 2 · `mcp_server/designer_helpers/view3d.py` (module docstring), `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_pan_moves_the_view_and_zoom_comes_closer_to_the_middle`) · confirmed · found 2026-11-12
  - **Defect.**
    - The note that at the self-test's view, "about 340 px wide", the pan's rate and content following the mouse 1:1
      nearly agree is in both docstrings, against AGENTS.md's one place for a fact.
    - The size isn't fixed. It follows the layout the shared preferences plist carries (ROADMAP item 67): this
      branch's first scratch run had a 419 px wide view (the plane 275 px wide, which the zoom check's no-clipping
      bound rules out at 338 px).
    - `view3d.py`'s line 23 runs to 157 characters.
  - **Scenario.** The next agent takes the size as fixed, and reads the note in one place as complete.
  - **Fix.** Keep the note in the pan check's docstring, saying "about 340 px wide in the default docked layout",
    and have `view3d.py` point to it; wrap the long line.
  - **Resolution: done**. Docs, no test.
    - The note is in the pan check's docstring alone: "about 340 px wide in the default docked layout, the one the
      shared preferences plist carries (ROADMAP item 67)".
    - `view3d.py` points to it, and its long line is wrapped.

- [x] **TST-341 · The two new facts' details lose what explains a failure to the 150-character cut** · follows TST-335, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_the_camera_moves_under_the_light_tool_too`, `check_a_drag_turns_the_camera_alike_with_selection_on`) · confirmed · found 2026-11-12
  - **Defect.** `common.check` prints a detail's first 150 characters.
    - The Light tool fact's detail puts `sent.strip()[-80:]`, the snippet's output, after about 117 characters, and
      nothing else prints it.
    - The Selection fact's detail ends with `panel_after`, the part a failure changes, at about 150 characters.
  - **Scenario.** The snippet fails, as it did once with a stale wrapper (TST-335). Its traceback's last line, say a
    `NameError`, is cut; this is what `say_failed` fixed for shots (REVIEW.md TST-334).
  - **Fix.** Print `sent` whole on a line of its own when the marker is missing; put `panel_after` first in the
    Selection fact's detail.
  - **Resolution: done**.
    - **Test:** in the same scratch run, the Light tool's fact with its snippet made to raise.
      - Before: its detail was cut at "Runti".
      - After: a line of its own gives the snippet's last lines, "RuntimeError: the snippet failed: NameError
        stand-in".
    - **Fix:** that line; and the Selection fact's detail starts with the panel after.
  - Questioned by TST-342 (2026-11-12).

- [x] **TST-342 · The Selection fact's detail now loses its pan and the toggle to the 150-character cut** · follows TST-341, generation 3 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_a_drag_turns_the_camera_alike_with_selection_on`) · confirmed · found 2026-11-12
  - **Defect.** TST-341's fix put the panels first:
    `'%s (was %s) | %.2f from Right, %.2f from Front; panned %.3f | %s' % (panel_after.strip(), panel.strip(), near,
    far, moved, selection.strip())`. With `common.check` cutting a detail at 150 characters, the two panels (up to 58
    characters each) push `panned` and `SELECTION=` past the cut.
  - **Scenario.** The branch's own scratch run printed "... (was PANEL=mcp_selftest_view3d|EDITOR=mcp_selftest_view3d_added)
    | 0.00 from Right, 18.79 f". If the pan under Selection fails, or the toggle doesn't take, the line shows neither
    reason. This is what TST-341 set out to prevent.
  - **Fix** (generation 3: no new check). Put the numbers and the toggle first and the panels last:
    `'%.2f from Right, %.2f from Front; panned %.3f | %s | %s (was %s)'`.
  - **Resolution: done** (generation 3: no new check).
    - **Test:** the check alone in a scratch run, before and after.
      - Before: the line was cut at "| 0.00 from Right, 18.79 f", before the pan and the toggle.
      - After: "0.00 from Right, 16.99 from Front; panned 0.249 | TOOL=Camera SELECTION=True |
        PANEL=mcp_selftest_view3d|EDITOR=mcp_selftest (was PANEL=mcp_selftest_v", the panels last.
    - **Fix:** that order in the detail.

- [x] **SRV-121 · A launch whose crash uploads couldn't be turned off runs its sentence on from the status** · `mcp_server/server_tools/lifecycle.py` (launch_designer's result) · confirmed · found 2026-11-12
  - **Defect.** `'Designer started in %.0fs, on port %d%s: %s%s' % (..., status, uploads)` puts `' Its crash reports
    may still be uploaded to Adobe: ...'` right after the plugin's status, which ends with no stop (`'%s v%d: %s, %d
    queued'`, the plugin's `__init__.py`).
  - **Scenario.** Its `settings.dat` missing: the result reads "... idle, 0 queued Its crash reports may still be
    uploaded to Adobe: ...". The unit test checks only that the sentence is there.
  - **Fix.** `_sentence(status)` before it (REVIEW.md SRV-114, SRV-117), with the unit test checking the stop.
  - **Resolution: done**.
    - **Test:** `test_launch_says_when_crash_uploads_couldnt_be_turned_off` now expects ": idle. Its crash reports may
      still be uploaded"; it failed on "idle Its crash reports" (missing, not Crashpad).
    - **Fix:** `_with_uploads` puts `_sentence(status)` before the sentence.
    - **Also covered:** the "already running" result goes through it too (SRV-120's test of a missing file).

- [x] **SRV-122 · Crashpad's settings version isn't checked before bit 0 is changed** · `mcp_server/server_tools/lifecycle.py` (`_crash_uploads_off`) · confirmed · found 2026-11-12
  - **Defect.** Only the magic is checked: `if len(head) < 12 or int.from_bytes(head[:4], 'little') != CRASHPAD_MAGIC`;
    the version (`head[4:8]`, 1) isn't, and the options are taken at offset 8 whatever it is.
  - **Scenario.** A Designer update brings a Crashpad whose settings have another version and layout: bit 0 of
    whatever is at offset 8 is cleared, the result says nothing, and uploads may stay on.
  - **Fix.** Require version 1, else say why in the result, as for a file that isn't Crashpad's; a unit test with
    version 2.
  - **Resolution: done**.
    - **Test:** the same test's `another version` case (version 2): it failed, the result saying nothing.
    - **Fix:** `CRASHPAD_VERSION` (1); settings of another version are left as they are, and the result says why.

- [x] **TST-344 · README and AGENTS say Designers an agent starts upload no crash reports** · `README.md` ("Crash dumps:"), `AGENTS.md` ("When a Designer crashed or hung") · confirmed · found 2026-11-12
  - **Defect.** AGENTS.md: "Designers an agent starts upload no crash reports"; README: "doesn't upload its reports by
    itself". Uploads are off only from the moment `launch_designer` sees the Designer answer: Sentry turns them on at
    every start, in a home reused per port. DECISIONS.md's entry says it right ("once it answers").
  - **Scenario.** A Designer an agent starts crashes as it loads its plugins, before it answers: its report is
    uploaded, and so are those of SRV-120's path.
  - **Fix.** Narrow both to "from the moment `launch_designer` sees it answer".
  - **Resolution: done**.
    - **Test:** none (docs); the tests that validate the docs pass.
    - **Fix:** AGENTS.md: "from the moment `launch_designer` sees them answer"; README: "once it has started ... as soon
      as it answers". DECISIONS.md already said "once it answers".
  - Questioned by TST-348 (2026-11-12).

- [x] **TST-345 · `_alone()` leaves `common.crash_dumps` replaced for the test files after it** · `tests/unit/test_selftest_alone.py` (`_alone`) · confirmed · found 2026-11-12
  - **Defect.** `vars(alone.common)['crash_dumps'] = lambda ports=(), run_port=True: set()` patches the module without
    monkeypatch, and it stays in `sys.modules` after the test; `tests/unit/test_selftest_crash_dumps.py`'s `_common()`
    imports `test_all_tools.common` without purging it, so it gets the patched one.
  - **Scenario.** `pytest tests/unit/test_selftest_alone.py tests/unit/test_selftest_crash_dumps.py`, as an agent runs
    the tests of a change to crash detection: `common.crash_dumps()` returns `set()`, and those tests fail. The whole
    suite hides it, since `test_selftest_categories.py` purges the modules in between.
  - **Fix.** Patch it with `monkeypatch.setitem` (`_alone` taking `monkeypatch`), or purge `test_all_tools.*` after
    each test; `category_run.PAUSE_S`, set the same way a line above, is older and could go the same way.
  - **Resolution: done**.
    - **Test:** `pytest tests/unit/test_selftest_alone.py tests/unit/test_selftest_crash_dumps.py` failed
      (`test_crash_dumps_include_those_of_the_runs_own_designers`), then passed (56 of 56).
    - **Fix:** an autouse fixture in `test_selftest_alone.py` drops the self-test's modules after each test, so
      `category_run.PAUSE_S` and `common.crash_dumps`, patched by `_alone()`, don't reach later files.

- [x] **TST-346 · The uploads check reads them once, right after the launch; "they stayed off" has no check** · `tests/test_all_tools/lifecycle/checks.py` (`check_launch_on_another_port`), `mcp_server/server_tools/lifecycle.py` (its docstring, Crash reports) · confirmed · found 2026-11-12
  - **Defect.** `check('launch_designer', 'turns crash uploads off in the Designer it starts', uploads(theirs) ==
    'off', ...)` runs as `launch_designer` returns. The module's docstring says uploads turned off after the start
    "stayed off", measured once by a probe, and names this check.
  - **Scenario.** A Designer that turns them on again later (after its licence check, say) passes the check, and its
    crashes are uploaded.
  - **Fix.** Read them again just before the check's `quit_designer`, some seconds later, in the same check.
  - **Resolution: done**.
    - **Test:** a second read in `check_launch_on_another_port`, just before its `quit_designer`: "keeps crash uploads
      off in the Designer it started, until it is quit". With a scratch break that turned uploads on just before it,
      it failed ("uploads: on"); without the break it passed ("uploads: off").
    - **Fix:** that check.

- [x] **INS-28 · The dump reader's frame walk drops every repeated return address, so a recursion shows once** · `scripts/read_crash_dump.py` (`_Dump.frames`) · confirmed · found 2026-11-12
  - **Defect.** `if ret & ADDRESS != found[-1]: found.append(ret & ADDRESS)` runs for every frame record, though only
    the first can repeat the link register (a function that saved it and called nothing since); and
    `while fp and len(found) < DEPTH` counts the frames kept, not the records walked.
  - **Scenario.** A crash in a recursion (F calling F, each record returning to the same place): F is printed once,
    then its first caller, hiding the recursion, and the walk runs on to the end of the captured stack.
  - **Fix.** Compare with the link register for the first record only, and count the records walked against `DEPTH`;
    tests in TST-347.
  - **Resolution: done**.
    - **Test:** `test_a_recursion_shows_each_of_its_frames` failed, QtCore's frame said once for three records, and
      `test_the_walk_stops_at_its_depth` failed, once for 100.
      `test_a_return_address_the_link_register_holds_is_said_once` passed before and after: it guards the first
      record's comparison, which stays.
    - **Fix:** `frames` compares with the link register for the first record only, and walks at most `DEPTH` records
      (the frames said, at most `DEPTH`).

- [x] **INS-29 · With no dump given, the reader looks only in `completed/`** · `scripts/read_crash_dump.py` (`dump_folders`), its docstring, `README.md` ("Crash dumps:"), `AGENTS.md`, `mcp_server/GUIDE.md` (Several Designers); the same in `tests/test_all_tools/common.py` (`crash_dumps`) · confirmed · found 2026-11-12
  - **Defect.** `return [os.path.join(home, *DATA, 'Sentry-Crashpad', 'completed') for home in homes]`. Crashpad moves
    a finished report from `new/` to `pending/`, and to `completed/` only once its upload is done or skipped.
  - **Scenario.** The user's Designer (uploads on) crashes; while its report uploads (4 s, measured) or longer if the
    upload can't be made (not measured), the script with no argument reads an older dump as the newest, or says there
    is none. The docs' "writes one per crash into `completed/`" was measured on agents' Designers, uploads off.
  - **Fix.** Look in `pending/` too (its files are finished; `new/` is still being written), and say both in the
    docs. `common.crash_dumps`, which the self-test's end check reads in the user's Designer, the same.
  - **Resolution: done**.
    - **Test:** `test_the_dumps_are_looked_for_in_each_designers_crashpad_folders` failed (no `pending`), and
      `test_a_dump_waiting_for_its_upload_is_read_as_the_newest` read the older dump in `completed/`.
    - **Fix:** `dump_folders` gives each home's `pending` then `completed`; the script's docstring, README, AGENTS.md
      and GUIDE.md say `pending` while the upload waits.
    - **Also covered:** `common.crash_dumps` keeps `completed/` only. Its sets of paths are compared before and after
      a step, so a report moving from `pending/` to `completed/` would count as a new dump. Agents' Designers skip the
      upload, and their reports reach `completed/` at once (measured, uploads off). The user's Designer's report
      waits in `pending/` while it uploads (4 s, measured), within `new_crash_dumps`' 10 s wait; a failed upload
      wasn't measured.
  - Questioned by TST-351 (2026-11-12).

- [x] **INS-30 · The reader names frames from the module now on disk, not checked against the one that crashed** · `scripts/read_crash_dump.py` (`_atos`, `_names`) · confirmed · found 2026-11-12
  - **Defect.** `['atos', '-arch', 'arm64', '-o', path, '-l', hex(base)] + ...` for any module where
    `os.path.isfile(module[2])`. The dump records each module's UUID (its CodeView record, `RSDS` + the UUID: QtCore's
    matched `dwarfdump --uuid` of the file on disk), which nothing compares.
  - **Scenario.** Designer is updated after a crash; its dump stays in an agent's `/tmp` home. The script, run on it,
    names its frames from the new QtCore and Designer: plausible, wrong names, with no warning.
  - **Fix.** Compare the dump's UUID with the file's (`dwarfdump --uuid`, or its `LC_UUID`), and on a mismatch name
    nothing in that module and say why.
  - **Resolution: done**.
    - **Test:** `test_frames_of_another_build_on_disk_are_not_named` (another build, and a file that isn't Mach-O)
      failed: its frames were named. `test_frames_of_the_build_that_crashed_are_named` (universal, and arm64 only)
      passed before and after.
    - **Fix:** `_Dump._build` reads each module's UUID from its CodeView record, and `_file_build` reads the file's
      (`LC_UUID`, arm64's part of a universal file). A module whose two UUIDs differ isn't named, and a line says
      why. A dump that records no UUID is named as before.
    - **Also covered:** the real dump of 2026-11-12, read on the system's Python 3.9: QtCore's and QtGui's frames 10 to
      15 are named as before, with no such line (the UUIDs match; QtCore's agrees with `dwarfdump --uuid`).
  - Questioned by TST-350 (2026-11-12).

- [x] **INS-31 · A malformed module name, or a dump removed during the search, gives a traceback** · `scripts/read_crash_dump.py` (`_Dump._modules`, `main`) · confirmed · found 2026-11-12
  - **Defect.** `self.data[name + 4 : name + 4 + length].decode('utf-16-le')` decodes strictly, and `describe` catches
    only `struct.error`; `max(found, key=os.path.getmtime)` stats files found a moment before.
  - **Scenario.** A dump whose module name has an odd number of bytes: `UnicodeDecodeError`, a traceback and exit 1,
    instead of "the dump is cut short or malformed". A dump removed between the glob and the stat (Sentry pruning old
    reports as a Designer starts): `FileNotFoundError`.
  - **Fix.** Decode with `errors='replace'` (as `messages()` does), and skip a file whose stat fails; a test of each.
  - **Resolution: done**.
    - **Test:** `test_a_module_name_of_an_odd_length_is_read_still` failed with `UnicodeDecodeError` ("decoding with
      'utf-16-le' codec failed"); `test_a_dump_gone_during_the_search_is_passed_over` failed with `FileNotFoundError`
      (`tests/unit/test_read_crash_dump.py`).
    - **Fix:** module names decoded with `'replace'`; `_newest` skips a file whose time can't be read.
    - **Also covered:** the messages were already decoded with `'replace'`; the other reads are `struct` ones, which
      `describe` turns into "cut short or malformed".
  - Questioned by INS-33 (2026-11-12).

- [x] **INS-32 · A dump given by its bare file name loses Designer's log** · `scripts/read_crash_dump.py` (`_log_tail`) · confirmed · found 2026-11-12
  - **Defect.** `database = os.path.dirname(os.path.dirname(path))` is `''` for `a1b2.dmp`, so the log is looked for
    at `attachments/a1b2/log.txt` under the current folder.
  - **Scenario.** `cd .../Sentry-Crashpad/completed && python3 .../read_crash_dump.py a1b2.dmp`: the log's lines are
    left out, with nothing said.
  - **Fix.** `os.path.abspath(path)` first, with a test run from the dump's folder.
  - **Resolution: done**.
    - **Test:** `test_a_dump_given_by_its_file_name_alone_has_designers_log`, run from the dump's folder, failed: the
      log's line was missing.
    - **Fix:** `_log_tail` takes the dump's absolute path.

- [x] **TST-347 · Lines of the dump reader no test guards** · `tests/unit/test_read_crash_dump.py`, `tests/unit/minidumps.py` · confirmed · found 2026-11-12
  - **Defect.** Each of these could be removed or wrong with every test passing:
    - the `caller <= fp` guard in `frames`: every test's chain ends on a zero return address; without the guard, a
      record pointing to itself would loop forever, since its repeated address is never kept (INS-28);
    - the newest dump: the test's newer dump is in the last folder, so `found[-1]` passes as well as `max(...,
      key=os.path.getmtime)`;
    - `dump_folders()`: both tests that need it replace it, so a wrong `DATA` passes;
    - the memory-list stream: `minidumps.py` writes none, so `_memory`'s first loop never runs, though every real dump
      has one (27 ranges in the one read);
    - `_exception`'s `from <exception>` branch: `Crash.code` is never set.
  - **Scenario.** A change to the memory list's stride passes every test, and every real dump is then misread.
  - **Fix.** Tests of a record pointing to itself, a recursion and a chain past `DEPTH` (with INS-28), the newer dump in
    the first folder, `dump_folders()`'s paths, a memory-list stream, and a non-zero code.
  - **Resolution: done**.
    - **Test:** new tests in `tests/unit/test_read_crash_dump.py`: a record pointing to itself, a recursion and a chain
      past `DEPTH` (with INS-28), a record in the memory list's second range, a crash from another exception
      (`from EXC_BAD_ACCESS`), `dump_folders()`'s paths, and the newer dump now in the first folder. Each was seen
      failing on the change it guards, made in the script for a moment and put back: without `caller <= fp`, the
      record pointing to itself failed; with the last dump found instead of the newest, both newest-dump tests failed;
      with a memory-list stride of 12, the memory-list test failed; with a wrong `DATA`, the two folder tests failed.
      The other exception's test passed before and after.
    - **Fix:** those tests; `minidumps.py` writes a memory list, module names of a given length and modules' UUIDs.
  - Questioned by TST-349, TST-350 (2026-11-12).

- [x] **SRV-123 · A Designer answering `launch_designer` with a refusal keeps crash uploads on, the one it just started too** · follows SRV-120, generation 2 · `mcp_server/server_tools/lifecycle.py` (launch_designer's two `except _Refused: raise`) · confirmed · found 2026-11-12
  - **Defect.** A refusal is an answer that comes back raised (`core._exchange`: `raise _Refused(OTHER_PROTOCOL)`, a
    plugin of another bridge protocol; `_control`: `raise _Refused('Designer refused the %r request: ...')`, an invalid
    token), and both of `launch_designer`'s handlers re-raise it before any `_crash_uploads_off`. SRV-120's "Also
    covered" says every return with a Designer answering.
  - **Scenario.** On this project an agent raises `BRIDGE_PROTOCOL`, reconnects `/mcp` and calls `launch_designer`
    before running `install.py`: the Designer it starts answers with the old protocol, the call raises, and Sentry has
    turned uploads on in it. A crash before it is quit, or in its forced quit, sends its report with the user's Adobe
    account.
  - **Fix.** Turn them off before re-raising, in both handlers (`_agent_home(port)`, None for the user's), with the
    sentence when it can't; unit tests of a refusal at the top for a recorded agent's Designer and in the wait for the
    one just started.
  - **Resolution: done**.
    - **Test:** `test_a_designer_it_started_refusing_gets_crash_uploads_off_too` and
      `test_an_agents_designer_refusing_gets_crash_uploads_off_too` (turned off, and settings missing) in
      `tests/unit/test_lifecycle_env.py` failed: uploads still on (`1 == 0`), and no sentence. No live check: a refusal
      needs another token or another plugin's protocol, so changing the user's token file or installing another plugin;
      the file written is the one the live check already measures.
    - **Fix:** `_with_uploads_off` turns them off before the refusal is raised again, in both handlers (the started
      one's home, else `_agent_home(port)`, None for the user's), adding the sentence when it can't.
    - **Also covered:** the raises of `launch_designer` after a Designer answered are those two; its other errors are
      a Designer not answering. The note under SRV-120 is fixed too (there).
  - Questioned by TST-354 (2026-11-12).

- [x] **TST-348 · README says uploads are off "as soon as it answers"; AGENTS.md's sentence lost its platform** · follows TST-344, generation 2 · `README.md` ("Crash dumps:"), `AGENTS.md` ("When a Designer crashed or hung") · confirmed · found 2026-11-12
  - **Defect.** README: "doesn't upload its reports once it has started: `launch_designer` turns that off in its own
    settings as soon as it answers". They are turned off only when a `launch_designer` call sees it answer. AGENTS.md:
    "Designers an agent starts upload no crash reports from the moment `launch_designer` sees them answer", with no
    platform: on Windows no Designer gets a home of its own, and nothing is turned off.
  - **Scenario.** `launch_designer(wait_s=30)` stops waiting, as its result invites; the agent sees the Designer up with
    `designer_status` and works on through other tools: uploads stay on for that Designer's life. On Windows, every
    Designer an agent starts keeps Adobe's setting.
  - **Fix.** README: "once `launch_designer` sees it answer"; AGENTS.md: "On macOS, Designers an agent starts ...".
  - **Resolution: done**.
    - **Test:** none (docs); the tests that validate the docs pass.
    - **Fix:** README: "once `launch_designer` sees it answer"; AGENTS.md: "On macOS, Designers an agent starts ...". The
      module's docstring adds the refusal (SRV-123).

- [x] **INS-33 · A CodeView record cut short raises `ValueError`; a malformed Mach-O on disk can loop or allocate a lot** · follows INS-31, generation 2 · `scripts/read_crash_dump.py` (`_Dump._build`, `_file_build`) · confirmed · found 2026-11-12
  - **Defect.** `_build` checks the size the record declares, not the bytes there: `record = self.data[at : at +
    size]`, `if size < 20 or record[:4] != b'RSDS'`, then `uuid.UUID(bytes_le=record[4:20])`, which raises
    `ValueError` on fewer than 16 bytes; `describe` catches only `struct.error`. INS-31's "Also covered" ("the other
    reads are struct ones") no longer holds. In `_file_build`, `at += length` doesn't move on a `cmdsize` of 0, so the
    loop runs `ncmds` times (up to 2^32), and `f.read(entry * count)` and `f.read(size)` read whatever a huge
    `nfat_arch` or `sizeofcmds` asks.
  - **Scenario.** A dump cut short (a partial copy, a full disk) within a module's CodeView record: in the real dump
    the names and records lie at 163968 to 419456, each name before its record, so the name is read and the record
    raises: a traceback and exit 1 instead of "cut short or malformed". The Mach-O case needs a malformed file at a
    module's path.
  - **Fix.** `len(record) < 20`; in `_file_build`, stop on a `cmdsize` under 8 and bound the counts and sizes by the
    file's size; a test of a record cut short (the last module's record pointed at `RSDS` and 6 bytes at the file's
    end, since `minidumps.py` writes the directory last).
  - **Resolution: done**.
    - **Test:** in `tests/unit/test_read_crash_dump.py`, `test_a_build_record_cut_short_doesnt_stop_the_reading` failed
      with "ValueError: bytes_le is not a 16-char string". `test_a_malformed_macho_file_on_disk_gives_no_build` failed
      in each case:
      - a load command of size 0: still running after 5 s;
      - commands said to be 4 GB: read, and a UUID returned;
      - a universal table of 2^32 - 1 parts: 85.9 GB allocated at the peak (`tracemalloc`).
    - **Fix:** `_build` checks the bytes there, not the size declared; `_file_build` reads no count or size larger than
      the file, and stops at a load command shorter than its header.
    - **Also covered:** the dump's other reads go through `struct` (which `describe` says is "cut short or malformed")
      or slices; names and messages are decoded with `'replace'`.
  - Questioned by TST-353 (2026-11-12).

- [x] **TST-349 · Two of the reader's new tests fail on Windows** · follows TST-347, generation 2 · `tests/unit/test_read_crash_dump.py` (`test_the_dumps_are_looked_for_in_each_designers_crashpad_folders`, `test_a_dump_waiting_for_its_upload_is_read_as_the_newest`) · confirmed · found 2026-11-12
  - **Defect.** Both set `HOME`, which `os.path.expanduser` ignores on Windows (`USERPROFILE` since Python 3.8), so
    `dump_folders()` gives the real profile's folders; the expected list also joins a POSIX path. Every other test in
    the file replaces `dump_folders`.
  - **Scenario.** The unit suite on Windows, part of the final check there (AGENTS.md): the folders differ, and `main`
    finds no dump and returns 1. Nothing is written.
  - **Fix.** Skip both on Windows, as `test_lifecycle_env.py`'s macOS-only tests.
  - **Resolution: done**.
    - **Test:** with `~` expanded as on Windows (a scratch pytest plugin ignoring `HOME`), the folders test failed when it
      set `HOME`; with the fix every test of the file passed so.
    - **Fix:** `_home_is` replaces `os.path.expanduser` for `~` in both tests; the pending test's newest dump is now in
      an agent's folder (TST-350).
  - Questioned by TST-352 (2026-11-12).

- [x] **TST-350 · The reader's tests that would pass without the code they guard, again** · follows TST-347 and INS-30, generation 2 · `tests/unit/test_read_crash_dump.py`, `tests/unit/minidumps.py` · confirmed · found 2026-11-12
  - **Defect.**
    - The newest dump: in all three tests that pick one, it is the first found (the newer in the first folder,
      `pending/` listed first, the gone file before the only real one), so a `_newest` returning the first readable
      path passes them all. TST-347 moved the blind spot from the last found to the first.
    - "No UUID in the dump: named as before" is tested only with an empty file, whose build is None too: with both
      None guards removed (`on_disk = build_of(...)`, `if on_disk != module[3]`) it is still named, though a real
      Mach-O would then be skipped.
    - `_file_build`'s 64-bit universal branch (`entry = 32 if wide`, `'>Q' if wide`) has no test, and none of
      Designer's files uses it.
  - **Scenario.** A change that keeps the first dump found, or drops the None guards, passes every test.
  - **Fix** (generation 2). The newest dump in the middle of three; `macho(BUILD)` in the test of a dump without
    UUIDs; drop the 64-bit universal branch, which nothing here writes.
  - **Resolution: done** (generation 2).
    - **Test:** each test seen failing on the change it guards, made in the script for a moment and put back:
      - with `_newest` keeping the first dump it can read, or the last, both newest-dump tests failed (the newest is now
        the middle of three);
      - with both None guards removed, `test_frames_in_a_module_on_disk_are_named_by_atos`, now with a Mach-O file of a
        build on disk, failed.
    - **Fix:** those tests; the 64-bit universal branch dropped, as none of Designer's 353 Mach-O files has one: such a
      file's build can't be read, so its frames aren't named, and a line says so.

- [x] **TST-351 · `common.crash_dumps` still reads `completed/` only, on reasoning that doesn't tell the two apart** · follows INS-29, generation 2 · `tests/test_all_tools/common.py` (`crash_dumps`) · confirmed · found 2026-11-12
  - **Defect.** INS-29's "Also covered" kept `completed/` only because a report moving from `pending/` to `completed/`
    would count as new. With `completed/` only it already does: a report pending before a step, uploaded during it,
    appears as a new path. And a report whose upload fails is never seen.
  - **Scenario.** The user's Designer crashed a few seconds before `alone.close`, which reads the user's folder too:
    its upload ends within the 10 s wait, and `alone.close` says "a crash dump appeared as it quit" with the user's
    dump, exit 1. Or an agent's Designer crashes before `launch_designer` turns uploads off, offline: its dump is never
    reported. Both are rare: `one_run`'s check that the user's Designer still runs catches their crash, and a crash at
    a launch fails it.
  - **Fix.** Read both folders and compare dumps by file name (Crashpad's report ID), not by path.
  - **Resolution: done**.
    - **Test:** these failed:
      - `test_crash_dumps_include_reports_waiting_for_their_upload` (none found);
      - `test_a_report_uploaded_meanwhile_is_no_new_crash_dump` (the moved report counted as new);
      - `test_crash_watch_takes_no_report_uploaded_meanwhile_for_a_crash` (the quit's check failed);
      - in `tests/unit/test_selftest_pool.py`, `test_a_report_uploaded_during_the_run_is_no_new_dump` (the pool returned
        1) and `test_a_workers_folder_holding_a_crash_dump_is_told[pending]`.
    - **Fix:** `common.crash_dumps` reads `completed/` and `pending/`, each report once. `common.new_dumps` compares
      reports (their database and file name), and is used by `new_crash_dumps`, the crash watch, the pool's quits and
      lifecycle's clean-up of the other port. The pool keeps a folder holding a report still pending.
    - **Also covered:** every difference of two sets of crash dumps (`git grep "crash_dumps("`). Live,
      `lifecycle.check_launch_on_another_port` passed in a scratch run, its "leaves no crash dump" with it, and
      `alone.close` returned 0.
  - Questioned by TST-355 (2026-11-12).

- [x] **SRV-124 · `quit_designer` leaves crash uploads on in an agent's Designer no launch saw answer** · follows SRV-120, generation 2 · `mcp_server/server_tools/lifecycle.py` (`quit_designer`, `_end_if_past_startup`) · confirmed · found 2026-11-12
  - **Defect.** SRV-120's "Also covered" left `quit_designer` out, as it "starts nothing"; but it finds the record
    (`found = _agent_record(port)`) and the Designer answering (`state = _control('status', wait=5, port=port)`), then
    closes it, samples and forces it past its wait, and never turns uploads off. A launch ending a Designer that never
    answered (`_end_if_past_startup`: `_force_end(own, port, seen)`) doesn't either. Quits are where crashes were seen
    (ROADMAP item 95's abort, the module's teardown crashes).
  - **Scenario.** `launch_designer(wait_s=30)` stops waiting; the agent works on through other tools and then calls
    `quit_designer`: a crash in that quit is uploaded with the user's Adobe account. Whether a forced end of one that
    never answered can crash in its teardown wasn't measured.
  - **Fix.** Turn them off in `quit_designer` once the record is found, and in `_end_if_past_startup` before the force
    (`_agent_home(port)`, or the record's home), saying so when they can't be; unit tests of each.
  - **Resolution: done**.
    - **Test:** in `tests/unit/test_lifecycle_env.py`, `test_quit_turns_crash_uploads_off_before_closing_an_agents`
      (closes, and forced) failed, uploads on as the close was asked and as it was forced (`[1]`);
      `test_quit_says_when_crash_uploads_couldnt_be_turned_off` failed, no sentence;
      `test_launch_turns_crash_uploads_off_before_ending_an_agents_not_answering` failed, on as it was forced. No new
      live check: it would leave uploads on through a quit; the file written is the one the live check measures, and
      `lifecycle.check_launch_on_another_port`, whose quits go through it, passed in a scratch run.
    - **Fix:** `quit_designer` turns them off as soon as it finds the record, before asking for the close, with a line
      when it can't; `_end_if_past_startup` before the sample and the force, its sentence added. The home comes from
      the record read (`_home_in`). The module's docstring says so.
    - **Also covered:** the places the server closes or ends a Designer an agent started: those two, and
      `launch_designer`'s (SRV-120, SRV-123). Left as it was: `start()` ending the one it just started when its record
      can't be written, within a second of its start.

- [x] **TST-352 · The folders test still fails on Windows: the agent's home joined with `/`** · follows TST-349, generation 3 · `tests/unit/test_read_crash_dump.py` (`test_the_dumps_are_looked_for_in_each_designers_crashpad_folders`) · confirmed · found 2026-11-12
  - **Defect.** `homes = [str(tmp_path / 'me'), '/tmp/sd_mcp_501_9902/home']`, while the reader joins
    `os.path.join(folder, 'home')`: on Windows `'/tmp/sd_mcp_501_9902\\home'`. TST-349's check simulated only `~`, so
    it couldn't see it.
  - **Scenario.** The unit suite on Windows, its final check: this test fails.
  - **Fix** (generation 3). Build the expected home with `os.path.join`, as the reader does.
  - **Resolution: done** (generation 3).
    - **Test:** none new; by reading, both sides now join with `os.path.join`.
    - **Fix:** the expected agent home built with `os.path.join`.

- [x] **TST-353 · The Mach-O size test takes tracing to be off before it** · follows INS-33, generation 3 · `tests/unit/test_read_crash_dump.py` (`test_a_malformed_macho_file_on_disk_gives_no_build`) · confirmed · found 2026-11-12
  - **Defect.** `tracemalloc.start()` then `tracemalloc.get_traced_memory()[1] < 1 << 20` and `tracemalloc.stop()` in a
    `finally`. If tracing is already on (`-X tracemalloc`, `PYTHONTRACEMALLOC`), `start()` does nothing, the peak is
    the whole session's, and `stop()` ends tracing for every later test.
  - **Scenario.** `PYTHONTRACEMALLOC=1 pytest ...`, as pytest's docs suggest for warnings' tracebacks: the three cases
    fail, and later tests lose their tracing.
  - **Fix** (generation 3). With tracing already on, skip the peak's assertion and leave tracing as it was.
  - **Resolution: done** (generation 3).
    - **Test:** none new. With `PYTHONTRACEMALLOC=1`, the test as it was failed (1 of its 3 cases, in a run of that test
      alone), and passes as it is.
    - **Fix:** with tracing already on, the peak isn't asserted and tracing is left on.

- [x] **TST-354 · An older test lost its Windows skip to a new test's decorator** · follows SRV-123, generation 3 · `tests/unit/test_lifecycle_env.py` (`test_a_designer_it_started_refusing_gets_crash_uploads_off_too`, `test_the_users_designer_already_running_keeps_its_crash_settings`) · confirmed · found 2026-11-12
  - **Defect.** The new test went in between `@_HOMES_OF_THEIR_OWN` and the test it marked: the new one has it twice,
    `test_the_users_designer_already_running_keeps_its_crash_settings` none.
  - **Scenario.** On Windows that test fails on `_crashpad_settings`' assertion (TST-343); nothing is written.
  - **Fix** (generation 3). The decorator back on the older test.
  - **Resolution: done** (generation 3).
    - **Test:** none new; by reading, each of the two tests has the decorator once.
    - **Fix:** the decorator back on `test_the_users_designer_already_running_keeps_its_crash_settings`.

- [x] **TST-355 · `crash_dumps` lists `completed/` before `pending/`, so a report moving between the two is missed** · follows TST-351, generation 3 · `tests/test_all_tools/common.py` (`crash_dumps`) · confirmed · found 2026-11-12
  - **Defect.** `for part in ('completed', 'pending'):  # a report moved between the two listings is kept once`.
    Crashpad moves a report from `pending/` to `completed/`: listed in this order, one moving between the two
    `listdir` calls is in neither, against the comment.
  - **Scenario.** In a `before` set, such a report is later counted as new (TST-351's false crash, in a window of
    milliseconds); in the pool's one listing after its wait, a crash goes unreported.
  - **Fix** (generation 3). List `pending/` first, as `dump_folders` does.
  - **Resolution: done** (generation 3).
    - **Test:** none new; the crash-dump tests pass.
    - **Fix:** `pending/` listed first, with the comment saying why.
