# REVIEW.md: review findings

Findings from code reviews of this repository, kept across several reviews as a file in the project. How many is
the user's choice, most likely the life of a feature branch; the history stays in git for good.

This file is the **memory per branch**. The lead writes it from the reviewers' and the developer's reports, as in a
PR review: a finding is raised, then fixed or answered with why not, so the next reviewers know what was settled and
don't raise it again. Once the branch is merged it can be cleaned up. `DECISIONS.md` is the memory for
the whole project.

A new review **appends** its findings to the matching severity section and adds itself to the log; it never removes
or rewrites existing entries. An entry is checked when it is resolved, always with a resolution line that starts
with one of these wordings: `done`, `not a bug`, `not reproducible`, `won't fix`, `moved to ROADMAP.md (item N, the
user, <date>)`. Format and rules: `.claude/skills/project-code-review/` (SKILL.md, TEMPLATE.md).

**Confidence.**
- *Confirmed*: the lead agent read the code and the defect is visible in it, as quoted.
- *Measured*: reading couldn't settle it, and the lead agent's scratch probe in Designer showed it (the entry gives
  the probe and what it measured; the `project-code-review` skill). A failure of the final check is *measured* too:
  the entry gives the failing test and its output. A finding is one or the other, never a guess.

**Found by.** An entry's title line ends with who found the finding and the model that agent ran on:
`found 2026-11-20 by a reviewer (Sonnet)`, `by the developer (Opus)`, `by the runner (Sonnet)` or `by the lead (Opus)`.
Two reviewers who found it are both named: `by two reviewers (Opus, Sonnet)`, or `by two reviewers (Sonnet)` when
both ran on one model. The model is the one the agent ran on: its file's, or the one the lead passed on the Agent call.
Older entries don't have it.

**IDs.** One prefix per area, numbered on: **PLG** plugin and bridge protocol, **SRV**
`mcp_server/server.py`, `server_tools/` and `designer_preferences.py`, **HLP** `mcp_server/designer_helpers/`, **INS** installer, uninstaller,
command-line client, example and `scripts/`, **TST** tests and the docs outside `.claude/`, **AGT** everything in
`.claude/` (agents, hooks, skills, rules, `settings.json`). A finding over several files takes the prefix of its first
location. A new area gets a new prefix, added here.

**Last used:** PLG-45, SRV-280, HLP-294, INS-51, TST-959, AGT-134.

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
| Low-medium | 0 | 27 |
| Low | 0 | 85 |
| **Total** | **0** | **112** |

## Reviews by model

What each model found in each review round, the time it took and the tokens it spent. After each round, the lead adds
that round's rows, every column filled: one row per model that ran, and a `settling` row when the lead used agents to
settle suspicions (a runner's probes, analysts). The last row is **Total**, which the lead updates after each round and
each developer run to sum every row above it, and adds after the first round:

- **Review:** the round's date, and which round it is.
- **Model:** the model the row's agents ran on, `settling`, or `<model> (developer)` (below).
- **Instances:** how many agents the row counts.
- **Real findings:** the real findings the round's reviewers on the row's model found, counted from each finding's
  `found ... by <who> (<model>)` (**Found by.**, above). The cell gives their count, then in brackets the count of
  each severity among them, most severe first: `9 [1 Low-medium, 8 Low]`, or `0` for none. The **Total** row sums each
  severity too.
- **Found only by this model:** how many of those no other row of the round found, written the same way.
- **Tokens:** the tokens of the row's agents, together.
- **Time:** the round's slowest agent of the row.

The developer gets a row for each run: every Agent call to a `developer`, and every resume of one with SendMessage
that ends in a report (the user, 2026-11-20). Its **Review** names the work, such as `2026-11-20, the nineteenth
review's fixes`. Its **Model** is `<model> (developer)`, such as `Opus (developer)`, and its **Instances** is 1. Its
two findings cells count the new problems it found that the lead settled as real, or `0` for none. Its **Tokens** and
**Time** come from its completion notice, as a reviewer's do. For a resumed developer, the Tokens are those its notice
adds since that agent's previous notice, and the Time is that run's duration, in minutes. A finding the runner or the
lead found is recorded on its title line only, in no row.

The figures are the usage each agent's completion notice gives (its tokens and duration). The lead's own share isn't
in it. A cleanup empties the table at its end, and git keeps the rows (the `cleanup-review` skill).

| Review | Model | Instances | Real findings | Found only by this model | Tokens | Time |
|---|---|---|---|---|---|---|
| 2026-11-25, step 1 (the state file's facts measured and pinned) | Opus (developer) | 1 | 0 | 0 | 631,822 | 83 min |
| 2026-11-25, round 1 (step 1) | Sonnet | 2 | 13 [6 Low-medium, 7 Low] | 13 [6 Low-medium, 7 Low] | 367,555 | 11 min |
| 2026-11-25, round 1's fixes | Opus (developer) | 1 | 0 | 0 | 204,340 | 36 min |
| 2026-11-25, round 2 (round 1's fixes) | Sonnet | 2 | 10 [3 Low-medium, 7 Low] | 10 [3 Low-medium, 7 Low] | 382,535 | 12 min |
| 2026-11-25, round 2's fixes | Opus (developer) | 1 | 0 | 0 | 103,327 | 31 min |
| 2026-11-25, round 3 (round 2's fixes) | Sonnet | 1 | 2 [2 Low] | 2 [2 Low] | 212,271 | 10 min |
| 2026-11-25, the relink measured (a second developer, the user's request) | Opus (developer) | 1 | 0 | 0 | 295,551 | 23 min |
| 2026-11-25, round 3's fixes | Opus (developer) | 1 | 0 | 0 | 6,211 | 2 min |
| 2026-11-25, step 2 (the state file in code) | Opus (developer) | 1 | 0 | 0 | 406,299 | 30 min |
| 2026-11-25, round 4 (step 2) | Sonnet | 2 | 9 [1 Low-medium, 8 Low] | 9 [1 Low-medium, 8 Low] | 426,056 | 12 min |
| 2026-11-25, round 4's fixes | Opus (developer) | 1 | 0 | 0 | 102,938 | 16 min |
| 2026-11-25, round 5 (round 4's fixes) | Sonnet | 1 | 1 [1 Low] | 1 [1 Low] | 140,635 | 6 min |
| 2026-11-25, round 5's fixes | Opus (developer) | 1 | 0 | 0 | 5,053 | 1 min |
| 2026-11-26, step 3 (the 3D call through the state file) | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 265,735 | 130 min |
| 2026-11-26, round 6 (step 3) | Sonnet | 3 | 15 [7 Low-medium, 8 Low] | 15 [7 Low-medium, 8 Low] | 973,786 | 19 min |
| 2026-11-26, round 6 | settling | 1 | 0 | 0 | 223,709 | 11 min |
| 2026-11-26, round 6's fixes | Opus (developer) | 1 | 0 | 0 | 272,789 | 50 min |
| 2026-11-26, round 7 (round 6's fixes) | Sonnet | 2 | 10 [1 Low-medium, 9 Low] | 10 [1 Low-medium, 9 Low] | 532,860 | 14 min |
| 2026-11-26, round 7's fixes | Opus (developer) | 1 | 0 | 0 | 51,369 | 18 min |
| 2026-11-26, round 8 (round 7's fixes) | Sonnet | 1 | 3 [3 Low] | 3 [3 Low] | 185,568 | 8 min |
| 2026-11-26, round 8's fixes | Opus (developer) | 1 | 0 | 0 | 4,592 | 2 min |
| 2026-11-26, step 4 (the mesh, tiling and environment through the state file) | Opus (developer) | 1 | 0 | 0 | 639,011 | 62 min |
| 2026-11-26, round 9 (step 4) | Sonnet | 2 | 7 [1 Low-medium, 6 Low] | 7 [1 Low-medium, 6 Low] | 593,271 | 14 min |
| 2026-11-26, round 9's fixes | Opus (developer) | 1 | 0 | 0 | 125,820 | 35 min |
| 2026-11-26, round 10 (round 9's fixes) | Sonnet | 1 | 0 | 0 | 238,766 | 10 min |
| 2026-11-26, step 5 (the ROADMAP rows, DECISIONS.md, the docs pass) | Opus (developer) | 1 | 0 | 0 | 358,748 | 24 min |
| 2026-11-26, round 11 (step 5) | Sonnet | 1 | 4 [4 Low] | 4 [4 Low] | 218,679 | 9 min |
| 2026-11-26, round 11's fixes | Opus (developer) | 1 | 1 [1 Low-medium] | 1 [1 Low-medium] | 20,067 | 4 min |
| 2026-11-26, TST-939's fix | Opus (developer) | 1 | 0 | 0 | 30,202 | 7 min |
| 2026-11-26, the agents' effort (the user's request): all to high | Opus (developer) | 1 | 0 | 0 | 108,135 | 2 min |
| 2026-11-26, the agents' effort: the reviewer back to xhigh | Opus (developer) | 1 | 0 | 0 | 4,345 | 1 min |
| 2026-11-26, the agents' effort: the developer back to xhigh | Opus (developer) | 1 | 0 | 0 | 2,591 | 1 min |
| 2026-11-26, round 12 (the entire branch, Opus) | Opus | 3 | 14 [3 Low-medium, 11 Low] | 14 [3 Low-medium, 11 Low] | 997,528 | 22 min |
| 2026-11-26, round 12 | settling | 1 | 0 | 0 | 130,451 | 6 min |
| 2026-11-26, round 12's fixes (and the user's docstring item) | Opus (developer) | 1 | 0 | 0 | 180,917 | 45 min |
| 2026-11-26, the agents' effort: the test follows the user's edit of the analyst (back to xhigh) | Opus (developer) | 1 | 0 | 0 | 3,269 | 1 min |
| 2026-11-26, round 13 (round 12's fixes, Opus) | Opus | 1 | 4 [1 Low-medium, 3 Low] | 4 [1 Low-medium, 3 Low] | 279,896 | 14 min |
| 2026-11-26, round 13's fixes | Opus (developer) | 1 | 0 | 0 | 221,272 | 35 min |
| 2026-11-26, round 14 (round 13's fixes, Opus) | Opus | 1 | 3 [3 Low] | 3 [3 Low] | 196,885 | 9 min |
| 2026-11-26, round 14's fixes | Opus (developer) | 1 | 0 | 0 | 47,198 | 10 min |
| 2026-11-26, round 15 (the entire branch, Opus) | Opus | 3 | 6 [1 Low-medium, 5 Low] | 6 [1 Low-medium, 5 Low] | 1,036,515 | 20 min |
| 2026-11-26, round 15 | settling | 1 | 0 | 0 | 82,865 | 3 min |
| 2026-11-26, round 15's fixes | Opus (developer) | 1 | 1 [1 Low-medium] | 1 [1 Low-medium] | 136,646 | 44 min |
| 2026-11-26, TST-953's fix | Opus (developer) | 1 | 0 | 0 | 35,572 | 11 min |
| 2026-11-26, round 16 (round 15's fixes, Opus) | Opus | 1 | 2 [2 Low] | 2 [2 Low] | 238,875 | 11 min |
| 2026-11-26, round 16's fixes | Opus (developer) | 1 | 0 | 0 | 4,714 | 2 min |
| 2026-11-26, round 17 (the entire branch, Opus) | Opus | 3 | 5 [5 Low] | 5 [5 Low] | 1,079,062 | 22 min |
| 2026-11-26, round 17's fixes | Opus (developer) | 1 | 0 | 0 | 68,606 | 18 min |
| 2026-11-27, the tool's docstring: an aborted set-up shot told to the user (the user's word) | Opus (developer) | 1 | 0 | 0 | 5,857 | 1 min |
| **Total** | | **62** | **111 [26 Low-medium, 85 Low]** | **111 [26 Low-medium, 85 Low]** | **12,880,764** | **968 min** |

## Review log

### 2026-11-25: view3d-state-file, round 1 (step 1: the state file's facts checks)

- **Scope:** `git diff a9113d0 17784ce -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: `facts/state_file.py`, its checks and `preparations.py`; `facts/state_camera.py`,
  the camera checks and `categories.py`. Their claim was step 1's text as the user approved it. No tests run, no
  probes: every finding below is settled by reading. Settled as wrong or not worth a fix: the lights check telling a
  camera-only file from a malformed one (it pins the light back off, which is its claim; the reviewer advised leaving
  it); the follow-the-graph check's leftovers (an open tab, the 3D view unlinked: no later facts check reads them);
  the `aside` copy left in the scratch folder.
- **Not verified:** none. One suspicion is left unsettled because a fix makes it moot: the moves check compares
  against a Front pose framed earlier, from another view, at a tolerance 50 times tighter than the views check's
  (whether Frame's result varies with the view before it). TST-891's fix frames Front in the moves' own script.
- **Resolutions assessed:** none in scope.
- **Findings:** TST-889 to TST-894 (Low-medium), TST-895 to TST-901 (Low); merged: TST-892 and TST-894 (both
  reviewers), TST-901 (types, from both). TST-889 was reported as Medium; it is a check that can't fail, with no
  effect on a user, so Low-medium.
- **Suggested order:** TST-890 first (the user's file on Windows), then TST-889 and TST-892 (checks that don't pin
  their fact), then the rest.
- **Simplifications:** TST-900's branchless decode.
- **Checked and found fine:** the matrix convention against a real file (rows X, Y, Z, position; X level; Y = Z x X);
  encode and decode as inverses, pitches beyond 90 included; orbit and pan signs and units, the pan's height
  fraction converted with h/w; the tolerances against the rates (a wrong rate or vertical unit fails); the
  rotation, exposure, tiling, map and camera rows' edited fields outside their `follows`; `bool(changed)` guarding a
  no-op edit; `check_reset_scene_reads_the_state_file_once_it_has_returned` deterministic; the values check's values
  not Designer's defaults; the path and home check; the AOV check; the preparation and its clean-up; the skip names;
  `categories.py`'s order and figure.


### 2026-11-25: view3d-state-file, round 2 (round 1's fixes on step 1)

- **Scope:** `git diff 42683f4 4c05814 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers, split as in round 1 (the state file and its checks; the camera). Their claim was step
  1's text as the user approved it. No tests run, no probes. Settled as wrong: `kept`'s end load, now required to say
  `LOADED=True`, raising when the base equals the session (the developer's scratch runs of the eight checks and of
  the whole `facts` category passed after that fix, so such a load does restart the count). Left to settle: whether
  the camera row's mid-glide control (10.8 to 13.4 degrees off at the mid Save, measured in an unloaded Designer)
  holds under the parallel full run's load; round 2's fixes run the `facts` category beside other categories to
  settle it.
- **Not verified:** none.
- **Resolutions assessed:** TST-889, TST-895, TST-897 and TST-899 hold. Questioned: TST-890 (TST-908), TST-891
  (TST-902, TST-905), TST-892 (TST-911), TST-893 (TST-904), TST-894 (TST-906), TST-896 (TST-903), TST-898
  (TST-910), TST-900 (TST-902, TST-907), TST-901 (TST-909).
- **Findings:** TST-902 to TST-904 (Low-medium), TST-905 to TST-911 (Low), each following a round 1 entry,
  generation 2, the longest chain.
- **Suggested order:** TST-902 and TST-904 first (step 3's orbit and renderer rest on them), then TST-903, then the
  rest.
- **Checked and found fine:** the home guard in `_sf_path` covering every Designer-side read, write, copy and
  removal, and `kept` refusing before it copies anything; `not_loaded`; the held undo button; the nested `finally`;
  the mid Save placed on callbacks after the load's read; the zoom away's and the orbit over the pole's tolerances
  against a wrong factor or a clamp; the branchless decode against three Designer matrices; `categories.py`'s
  figure.

### 2026-11-25: view3d-state-file, round 3 (round 2's fixes on step 1)

- **Scope:** `git diff cb8d329 6e929ce -- . ':(exclude)PLAN.md'`.
- **How:** one Sonnet reviewer, the whole diff. Its claim was step 1's text as the user approved it. No tests run, no
  probes. Found fine, beyond its list: `pose()` raising on a tilted camera reaches no camera Designer legitimately
  tilts (views, Frame, orbit, pan, zoom and the glide keep X level, as measured). Notes, not findings: a comment line
  left twice in `state_file.py` (239-240), the unit test file's header naming only round 1's IDs, and the moves
  check's `pair` raising on a failed move (a note under TST-911). An optional narrowing of TST-903's sentence (the
  Scene menu read empty at the trigger's return and full at the end, not over the interval) goes with the fixes.
- **Not verified:** none.
- **Resolutions assessed:** TST-902, TST-903 and TST-905 to TST-911 hold. Questioned: TST-904 (TST-912, TST-913).
- **Findings:** TST-912 and TST-913 (Low), generation 3, the longest chain. Only a few Low: step 1's reviews look
  converged once they are fixed.
- **Checked and found fine:** the yaw's flip over the pole (no flip at exactly 90 or at Designer's Top, Bottom's flip
  following float noise, named as not measured); a turn up from a camera upside down (pitch + up, documented as not
  measured); `LOAD_BEGAN` then `LOADED`; TST-904's condition failing when the click does nothing; TST-911's camera
  tracking across rows; `after_moves` composed across the two-call move; the unit tests of `pair`, `angle_off`,
  `turned_apart` and `away`; `REFUSED_WITH_NO_HOME`'s `finally`; the relink check's load and Save told apart; the
  table's totals.

### 2026-11-25: view3d-state-file, round 4 (step 2: the state file in code)

- **Scope:** `git diff 528e2cd 4c41c72 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the part (`state3d.py`, `standalone`, `core.py`, their unit tests); the facts
  checks moved onto it. Their claim was step 2's text as the user approved it, with the user's instruction on `view`
  of 2026-11-25 for the first. No tests run, no probes. Settled as wrong: `view`'s pose missing from the part (the
  user's instruction moves it to step 3, where the table of the built-in meshes' framing is measured). Notes, not
  findings: `kept` clears its `aside` before backing up, so the part's leftover put-back never acts in the checks
  (the Designer is disposable and guarded); the `map` kind's `(.*?)` is the one value pattern not bounded to its
  element, a refusal at worst; values read outside `check(...)` raise where `None` came before, accepted with the
  state file checks running last (TST-898).
- **Not verified:** none. Left to settle in the fixes: whether a state file saved with the GPU Pathtracer set holds
  `___usd___tiling` more than once (the fixture leaves the renderer's settings out), which would refuse every edit of
  the tiling for a user of the path tracer; and the moved checks seen failing once with the part's constants wrong
  (`STATE_VERSION = '11'`, `ZOOM_AWAY = 1/0.9`, `PAN_RATE = 1.0`).
- **Resolutions assessed:** none in scope.
- **Findings:** HLP-257 (Low-medium); TST-914, HLP-258 to HLP-262, TST-915, TST-916 (Low). HLP-258 and HLP-261
  merged from both reviewers.
- **Suggested order:** HLP-257, then TST-914, then the rest.
- **Settled in the fixes** (the developer, one run each): a state file saved with the GPU Pathtracer set holds every
  place once, as the Rasterizer's (it adds 53 of that renderer's parameters), and every field read and edited; the
  moved checks failed with `STATE_VERSION = '11'`, `ZOOM_AWAY = 1/0.9` and `PAN_RATE = 1.0`, each, and pass with
  the constants right.
- **Checked and found fine:** no check got weaker from the move: the `ONE_FIELD` rows edit one field each, as
  `test_each_edit_of_one_field_changes_its_field_alone` pins; `kept`'s home guard and nested `finally`; the values
  check (its background now compared whole); the moves check's constants pinned by Designer's file, not by the code;
  every moved unit test kept as strong; reads and edits refused before anything is built; spans replaced from the
  end; escaping round-tripped; the camera against four Designer matrices; the backup's rename and its four aborts;
  `standalone` binding only the named part's stdlib imports and refusing Designer names; the two re-exports in
  `core.py`.

### 2026-11-25: view3d-state-file, round 5 (round 4's fixes on step 2)

- **Scope:** `git diff f30a86a 362301b -- . ':(exclude)PLAN.md'`.
- **How:** one Sonnet reviewer, the whole diff. Its claim was step 2's text as the user approved it, with the user's
  instruction on `view`. No tests run, no probes. Not worth a fix: an empty `path` record, which the code can't make
  (it is written before the rename). A note under HLP-262 (a test comment saying "blanked").
- **Not verified:** none.
- **Unspecified:** a leftover backup that can't be put back (one made before HLP-257's fix has no `path`; a recorded
  path whose folder was removed) raises, and every later backup raises the same until the backup is removed by hand.
  No doc decides what a call does then. The lead's proposal, for the user with step 3: the call refuses, naming the
  backup's folder and what to do.
- **Resolutions assessed:** HLP-257 to HLP-262 and TST-914 to TST-916 hold. Questioned: HLP-257 (HLP-263).
- **Findings:** HLP-263 (Low), generation 2. Only a few Low: step 2's reviews look converged once it is fixed.
- **Checked and found fine:** what each abort in the backup and the put-back leaves; `standalone` binding and
  refusing as before, keeping every line number; the cache and line-number tests failing on the old code; the
  round trip against four Designer matrices; the orbit-up and pan-up tests; the `stray` column landing after every
  anchor; the Windows simulation's `open` patched soundly; REVIEW.md's counts.

### 2026-11-26: view3d-state-file, round 6 (step 3: the 3D call through the state file)

- **Scope:** `git diff 362301b b5b2613 -- . ':(exclude)PLAN.md'` (step 3, and round 5's fix of HLP-263).
- **How:** three Sonnet reviewers: the sequence and its docs (`scene3d.py`, `state3d.py`, `shot3d.py`, `views.py`,
  GUIDE, README, their unit tests); the removed drag, wheel and Light code and `set_3d_view`, with the sequence's unit
  tests against a Designer fake; the live self-test. Their claim was step 3's text and "What a user sees" as the user
  approved them, with the user's instructions of 2026-11-25 (`view`) and 2026-11-26 (the relink through the Explorer
  menu, a leftover backup removed and said, two consequences accepted). No tests run. Settling: one runner, two scratch
  probes in agents' Designers (what else a load resets; a relink after an sd API edit with no `compute()`).
- **Settled as wrong:** `_relinked` needing a `compute()` first: the relink showed the edit, also with the edit made
  inside the shot after the load (probe 2). The lifecycle check's project file rewritten by the quit: the check passed
  in two scratch runs, which such a rewrite would fail.
- **Not worth a fix:** an abort landing on `put_back`'s `try:` line (the next call puts the backup back, as after any
  abort); a leftover line dropping an aborted call's begun lines (a crash, then an abort).
- **Notes, not findings:** under HLP-263 (generation 3). The one-output graph left unlinked and said departs from the
  option the user chose ("plus a Return on one-output graphs"): a bare Return did nothing, and picking the channel
  needs a usage-to-channel table not measured; the lead told the user on 2026-11-26. `editor._wheel` is merged into
  `_wheel_zoom`, where the step said `_wheel` stays: the same events, accepted. The scene3d tests sit in
  `test_view3d_helpers.py` (a move to a file of their own is optional). Measured besides: with Display > Samples and
  Render time off, a set-up shot took 7.5 s against 2.2-2.6 s, slower, not wrong. Left to the final check: the new
  checks' 3 s settle under the parallel run's load.
- **Unspecified:** off macOS the self-test's Designer has no home of its own, so the editor checks' set-up shots write
  the user's real default state file, each backed up and put back (the facts checks skip there, TST-890). No doc decides
  whether the self-test may: for the user. Also for the user, at convergence: DECISIONS.md's "The 3D shot never sends a
  wheel step or a drag move again" and "A 3D screenshot, and `set_3d_view`" describe code this step removed.
- **Resolutions assessed:** HLP-263 holds; a note under it.
- **Findings:** HLP-264 to HLP-267, TST-917 to TST-920 (Low-medium); HLP-268 to HLP-271, TST-921 to TST-925 (Low).
  HLP-264 and HLP-265 merged from two reviewers each, HLP-271 from three; HLP-268 from the developer's report (a
  reviewer asked it as unspecified); HLP-267 measured by the runner on a reviewer's question. The longest chain, HLP-257 to
  HLP-263, stops at generation 2 (a note at 3).
- **Suggested order:** the put-back (HLP-264, HLP-267, TST-917, TST-918), then the camera (HLP-265, TST-919, TST-920),
  HLP-266, then the Low ones.
- **Checked and found fine:** success, error and abort each leave the backup put back; the bookkeeping of `touched`,
  `changed`, `base`, `linked` and the AOV through the tiling and environment steps; the camera's `begin` before
  anything is written; the leftover handling as the user chose; README, GUIDE and the tool's docstring against the code;
  no removed name referenced anywhere; the remaining `_Frames` and `_Counts` methods all called; `MESHES` and `VIEWS`
  from `FRAMING` keeping their order; the new facts checks each failing without what they guard (the view and files
  back byte for byte, the leftover put back, the leftover removed, the missing field, the Frame table at two aspects,
  the Default State File followed); no fixed sleep added; the loosened menu `looks` assertions hiding nothing; the
  probe's 47 other checkable entries surviving a load.

### 2026-11-26: view3d-state-file, round 7 (round 6's fixes on step 3)

- **Scope:** `git diff 2e123d9 8f3c97f -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the helpers, the server and their unit tests; the live self-test. Their claim was each
  finding's entry, with step 3's text and "What a user sees" as the user approved them and the user's instructions of
  2026-11-26. No tests run, no probes.
- **Settled as wrong:** `_SWITCHED_AT_THE_RENDER` counting a render of `_renders_alike` as the shot's own: those
  renders come only with no sample count showing, which the agents' Designers show by default, and the developer saw
  the case fail without HLP-264's fix.
- **Not worth a fix:** `_overrides_back` matching materials by their menu position after a `mesh=` switch with a camera
  option: the switch lasts the shot, and the put-back sets back the user's mesh's own entries.
- **Left to the final check:** `PAN_OFF` (0.005) on a smaller viewport than the 342 px measured: the band holds about a
  pixel's error at that width; only the pool's run shows its Designers' sizes.
- **Unspecified:** nothing new (round 6's on Windows stands).
- **Resolutions assessed:** all 17 of round 6 hold for their findings; questioned: HLP-264 (HLP-272), HLP-265
  (HLP-273), HLP-266 (TST-926), HLP-267 (HLP-276, TST-930), HLP-268 (TST-927, HLP-274), HLP-271 (HLP-275), TST-919
  (TST-929), TST-925 (TST-928).
- **Findings:** HLP-272 (Low-medium); HLP-273 to HLP-276, TST-926 to TST-930 (Low), all generation 2. HLP-275 merged
  from both reviewers. The longest chains are at generation 2.
- **Suggested order:** HLP-272, then the rest.
- **Checked and found fine:** `SAME_POSE` against the fixture's Default camera; `url2pathname` on both systems; the
  Override Material set-back after each load and its fact; the refused Save's path through the put-back; the three
  claims' tests; the fake's load read in the next wait, and each mutation the round 6 tests name failing; the documented
  steps in the move checks (round 4's `ZOOM_AWAY = 1/0.9` now fails the pan check); the user's-own-view check failing
  from Designer's default pose; the refusal check able to fail; the lifecycle quit judged; `NOTHING_AFTER` selecting the
  put-back's load; no removed name or PLAN.md cite left; REVIEW.md's sums.

### 2026-11-26: view3d-state-file, round 8 (round 7's fixes on step 3)

- **Scope:** `git diff 387d7e5 107aedb -- . ':(exclude)PLAN.md'`.
- **How:** one Sonnet reviewer, the whole diff. Its claim was each finding's entry, with step 3's text as the user
  approved it and the user's instructions of 2026-11-26 (sent word for word after a brief that summarised them). No
  tests run, no probes.
- **Not worth a fix:** HLP-274's clause said for a Save that wrote nothing for another reason (an unwritable folder): no
  doc decides the message for it, and the case is far rarer than the one the clause is for (KISS).
- **Notes, not findings:** TST-927's fake leaves the file's time a second or so ahead of the clock; TST-926's test
  imports inside the function. Neither guards anything later.
- **Resolutions assessed:** all ten of round 7 hold; questioned: HLP-272 (HLP-277), HLP-273 (HLP-279), TST-930
  (HLP-278).
- **Findings:** HLP-277 to HLP-279 (Low), all generation 3 (claims narrowed). Only a few Low: step 3's reviews look
  done once they are fixed.
- **Checked and found fine:** the put-back's look in a `try` of its own, an abort still a `BaseException` that puts the
  backup back; the yaw's wrap at ±180, ±360 and 180 apart; the refusal's clause and README; Materials looked up before
  any change; the URL patch taking effect at call time; the fake's Save time; the type; no code use of `state3d` left in
  the editor checks; the narrowed facts sentence; step 3's sequence against the code (an abort puts the backup back at
  once, more than the plan asks); REVIEW.md's sums.

### 2026-11-26: view3d-state-file, round 9 (step 4: the mesh, tiling and environment through the state file)

- **Scope:** `git diff 7fe0a64 bc677b2 -- . ':(exclude)PLAN.md'` (step 4, and round 8's three narrowings).
- **How:** two Sonnet reviewers: the helpers, the server, the docs and their unit tests; the live self-test. Their
  claim was step 4's text and "What a user sees" as the user approved them, with step 3's sequence and the user's
  instructions of 2026-11-26. No tests run, no probes. The lead found HLP-280 itself before the round (its own brief's
  wrong premise), and both reviewers found it too.
- **Not worth a fix:** `tiling=1e39` (a raw `OverflowError` after the Save, the view and files put back) and
  `tiling=inf`; no live check of a negative rotation or exposure through the file; `rasterizer.py`'s inline commit
  without the old `_commit`'s refusal of a spin box with no change (its Samples case fails visibly if the commit doesn't
  take).
- **Notes, not findings:** HLP-277's sentence still reads as unconditional when the put-back's load raises first
  (generation 4, a claim nobody acts on). For the user at convergence: DECISIONS.md's "After setting the 3D view's
  tiling or environment, the Parameters panel goes back" describes code step 4 removed, as do the two entries round 6
  named. For step 5: ROADMAP.md's 3D notes (76-91) and items 89, 92 and 131 name the removed mechanics.
- **Unspecified:** a reviewer asked whether an unused material should count for `tiling=`: HLP-114 settled it, and
  HLP-280 restores it.
- **Resolutions assessed:** HLP-277 to HLP-279 hold; HLP-265, HLP-267, HLP-268, HLP-272, HLP-273, TST-919, TST-920
  and TST-923 hold through step 4's changes. Questioned: HLP-114 (HLP-280), HLP-192 (TST-932), TST-315 (HLP-281),
  TST-545 (TST-931).
- **Findings:** HLP-280 (Low-medium); SRV-278, HLP-281, TST-931 to TST-934 (Low). The longest chain is at generation 3
  (TST-931).
- **Suggested order:** HLP-280, then TST-932, then the rest.
- **Checked and found fine:** one backup, one Save, one edit of the fields that differ and one Reset Scene; `reads`
  holding only the fields asked; `_state_changes` at 32 bits, the camera left to `_same_pose`; nothing loaded when
  nothing differs; the error and abort paths; `may_change` as before; the mesh reframed from the camera's direction,
  then moved; no removed name referenced; the docs agreeing with the code; each new unit test failing without its
  change; the facts checks of the map's URL, the rotation in turns, the 32-bit floats, a load keeping the file's camera
  and the menu switch's framing, each able to fail; the set-up check's failing-once path; `SHOWN_ALREADY`'s patches;
  the category order.

### 2026-11-26: view3d-state-file, round 10 (round 9's fixes on step 4)

- **Scope:** `git diff eccd27a 6b1a8ff -- . ':(exclude)PLAN.md'`.
- **How:** one Sonnet reviewer, the whole diff. Its claim was each finding's entry, with step 4's text and "What a user
  sees" as the user approved them, HLP-114 and the user's instructions of 2026-11-26. No tests run, no probes.
- **Notes, not findings:** two test comments HLP-280's fix left false (generation 3, in tests no later check depends
  on): a note under HLP-280, for step 5's docs pass. Also noted: `_material_checked` with `mesh=` already shown is
  reached by the live check only; `MATERIALS_USED` with no mapping table is unreachable in practice.
- **Not worth a fix:** `mesh=X, tiling=` after the user assigned a custom material to the whole mesh in the UI (the
  tools never make that assignment).
- **Left to the final check:** TST-932's 0.1 limit (0.000 real, 0.497 simulated) under the parallel run.
- **Resolutions assessed:** HLP-280, HLP-281, SRV-278 and TST-931 to TST-934 hold.
- **Findings:** none. Step 4's reviews are done.
- **Checked and found fine:** `_used_material` and `_IN_MATERIAL` reading and writing the used material's tiling, the
  bound not tripped by the neighbouring tags; `_material_checked` refusing before the window, matching HLP-114's
  filter; the restored live check measuring the render; every caller of `_state_fields` with the tiling; the
  `ADDED_MATERIAL` fixture; `SETTLED`'s placeholders and its render saved at the put-back's load; the Frame check's ids
  Designer's own; the refusal's no-step clause; no removed name left; no new wait or silenced diagnostic.

### 2026-11-26: view3d-state-file, round 11 (step 5: the ROADMAP rows, DECISIONS.md, the docs pass)

- **Scope:** `git diff 08b4f8f b67ff3b -- . ':(exclude)PLAN.md'`.
- **How:** one Sonnet reviewer. Its claim was step 5's text as the user approved it and the user's four answers of
  2026-11-26, quoted with the options offered. No tests run, no probes.
- **Unspecified, settled by the lead:** where the user's "Accept it" (off macOS, the self-test's set-up shots write the
  real default state file, backed up and put back) lives besides ROADMAP item 90's Note: a sentence in README's
  self-test section, stating what the checks do there (a fact for people, not a decision: no DECISIONS.md entry).
- **Resolutions assessed:** the note under HLP-280 holds (one comment deleted, one narrowed). The four DECISIONS.md
  answers hold, but for TST-935's clause.
- **Findings:** TST-935 to TST-938 (Low). Only a few Low: step 5's reviews are done once they are fixed.
- **Checked and found fine:** the 3D rules rewritten for the file against `scene3d.py`, `state3d.py` and `shot3d.py`;
  rows 73, 74 (the decode and the moves), 77, 84, 85, 89, 90, 92, 96, 107 and 131's Approach; "whole" dropped from the
  tool's docstring; the `frames3d.py` sentence; README and GUIDE against the code; the window entry's dates and choices,
  its Reopen if; the wheel entry removed whole; the `73ead3a` pointer resolving.

### 2026-11-26: view3d-state-file, round 12 (the entire branch against main, Opus)

- **Scope:** `git diff main...bfb7ed2 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`.
- **How:** three Opus reviewers: the set-up's sequence and the state file; the remaining 3D helpers, the server, the
  docs and their unit tests; the live self-test. Their claim was the plan's text as the user approved it (all five
  steps and "What a user sees") and the user's later instructions, quoted with their dates, in one file. No tests run.
  Settling: one runner, four scratch probes in an agent's Designer (the AOV and the relink after a set-up shot; an
  output-less graph in the editor; a mesh of the user's own; an orbit from a camera over the pole).
- **Settled as wrong:** the AOV not put back, or the view not following the graph again (probe: both work, two of two;
  the missing checks are TST-941); the orbit's maths over the pole (probe: right from an upside-down start).
- **Not worth a fix, again:** an abort after a leftover line dropping the steps begun (round 6's: a crash, then an
  abort).
- **Notes, not findings:** `state_file.pair` raising on a failed snippet at three new places (the TST-911 pattern, a
  failing run only); orphaned or stacked comments in the editor checks (around 391 and 2360); STALE_SET_UPS' "a change
  from the value before", now from the user's view; `'Parameters panel' not in` guarding a removed message;
  `_sf_sized` reading the size after one event pass (a lag fails the check, never passes it falsely).
- **Unspecified, for the user at convergence:** whether the agent should tell the user when a reply says a leftover
  backup was removed, or that the view no longer follows a graph; a Default State File set in a project file other than
  `user_project.sbsprj` (the call reads only that one).
- **Resolutions assessed:** this branch's, in each area, hold; questioned: HLP-271 (TST-946), TST-905 (HLP-284).
- **Findings:** HLP-282, HLP-283, TST-940 (Low-medium); TST-941 to TST-948, HLP-284, HLP-285, SRV-279 (Low). HLP-282
  and HLP-283 measured by the runner on the reviewers' questions. The longest chain is at generation 3 (HLP-284).
- **Suggested order:** HLP-283 (measure first), HLP-282, TST-940, TST-941, then the rest.
- **Checked and found fine:** the sequence against step 3 (the leftover, the backup, the Save, the edit refused before
  any load, one Reset Scene, the relink or `graph=`, the render, the base loaded back only when touched, the backup
  last; error and abort paths; HLP-272's look); state3d's edits, anchors, 32-bit comparisons, camera maths and framing;
  `standalone`; no removed name referenced; `shoot_3d`'s order; the tool's limits and descriptions but `zoom`'s; GUIDE,
  README but line 417, DECISIONS.md applied as the user said, ROADMAP's rows and rules; the facts put-back checks failing
  without what they guard; `kept` and the lifecycle project file cleaned up on failure; no fixed sleep; the category
  times.

### 2026-11-26: view3d-state-file, round 13 (round 12's fixes, Opus)

- **Scope:** `git diff 8b97418 fc0ee4b -- . ':(exclude)PLAN.md'`.
- **How:** one Opus reviewer, the whole diff. Its claim was each finding's entry, the plan's text and the user's later
  words (the claim file), and the user's "yes the agent can tell me" of 2026-11-26. No tests run, no probes: HLP-286 is
  settled by reading against `.claude/rules/waits.md`, whatever a slower mesh measures.
- **Notes, not findings:** the new facts check of a user's mesh raises on the failure it guards (the TST-911 pattern,
  a failing run only; the state file checks run last, TST-898); TST-946's `STEPS` and `NOTE` are the full set-up's lines
  faked for smaller calls (generation 3); the empty graph HLP-282's check makes stays in the package (no later check
  reads it); a note under TST-941; the wrapper test's plain shot meets the assertion before the wrapper runs (its
  TypeError still fails it without the fix); `TWO_OUTPUTS` repeats `PLAIN_OPS` (categories don't import each other's
  preparations); HLP-284's "not measured: a turn up from a camera upside down" (generation 4).
- **Resolutions assessed:** HLP-282 to HLP-285, SRV-279 and TST-940 to TST-948 hold for their findings; the user's
  docstring item matches `LEFTOVER_REMOVED` and the suffix. Questioned: HLP-282 (HLP-288), HLP-283 (HLP-286, HLP-287,
  TST-949).
- **Findings:** HLP-286 (Low-medium); HLP-287, HLP-288, TST-949 (Low), all generation 2.
- **Suggested order:** HLP-286, then the rest.
- **Checked and found fine:** the zoom description against `_framed` and `_reframed`; README's put-back sentence; the
  lifecycle check's textures and the version folder compared; the AOV set and read back with Beauty restored in a
  `finally`; the abort landing after a load; `LOAD_BEGAN` read once with no event pass; the backups at `STATE_BACKUP`; the
  UID check failing and the category going on; the fakes matching the helpers; no new silenced diagnostic, `Any` or
  fixed sleep.

### 2026-11-26: view3d-state-file, round 14 (round 13's fixes, Opus)

- **Scope:** `git diff 6ded25d 3a5a9b3 -- . ':(exclude)PLAN.md'`.
- **How:** one Opus reviewer, the whole diff; the claim file and each entry. No tests run, no probes: a slower mesh of
  the user's own is a case the user called very unlikely, whose fix would need a new signal from Designer, so the
  claims are narrowed instead of the case probed (KISS).
- **Notes, not findings:** under HLP-286 (the fake's `restarted`); off screen, a user's mesh's waits still end at the
  first UpdateRequest, as HLP-283 recorded.
- **Resolutions assessed:** HLP-286 to HLP-288 and TST-949 hold; questioned: HLP-286 (HLP-289), HLP-288 (HLP-290).
- **Findings:** HLP-289, HLP-290 (Low, generation 3), TST-950 (Low). Only a few Low: once fixed, an Opus round on the
  entire branch.
- **Checked and found fine:** `_restart` keeping `settled`'s first wait; `restarted`'s limit and its off-screen and
  no-count paths; each new frames test failing without its part; `_mesh_listed` raising nothing and read before the
  write; the four relink strings matching their tests; no wrapper needing `restarted`; no fixed sleep, silenced
  diagnostic or `Any` added; REVIEW.md's sums.

### 2026-11-26: view3d-state-file, round 15 (the entire branch against main, Opus)

- **Scope:** `git diff main...c9a7232 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`.
- **How:** three Opus reviewers, split as in round 12; the claim file with the user's words to 2026-11-26. No tests
  run. Settling: one runner, two scratch probes (Override Material across the relink; the frames check from Front).
- **Left to the final check:** `workers.py`'s "lifecycle starts first (the longest category after
  editor_panels_and_fit ...)", now that facts takes 196 s and lifecycle gained a relaunch (only a pool run's times show
  it).
- **Notes, not findings:** TST-946's fakes print no put-back line, and a comment says they do (generation 3, tests
  only); `UNSETTLED` leaves out the step's mesh and graph parts, which its regex doesn't read; the no-outputs check's
  comment says opening VIEW3D_GRAPH puts its outputs on the mesh, where the link comes from the check before; TST-941's
  check reads each move's last take only (a relink failing once, then passing on the retake, passes).
- **Resolutions assessed:** this branch's in each area hold; questioned: HLP-267 (HLP-291), HLP-271 (HLP-293), TST-950
  (TST-952).
- **Findings:** HLP-291 (Low-medium, measured); HLP-292, HLP-293, SRV-280, TST-951 (measured), TST-952 (Low).
- **Suggested order:** HLP-291, then HLP-292 (the same lines), then the rest.
- **Checked and found fine:** removed code referenced nowhere; DECISIONS.md changed only as the user said; the agents'
  effort as the user set it, pinned by `test_agents.py`; the sequence against step 3, the error and abort paths and the
  closures read at call time; state3d's edits, camera maths re-derived by hand, framing, wrap and 32-bit comparisons;
  `restarted` and `_restart`; the tool's descriptions against the code; `shoot_3d`'s order; the facts put-back checks and
  their clean-up; every Designer fact the code relies on pinned or listed as measured only; no fixed sleep, silenced
  diagnostic or `Any` added.

### 2026-11-26: view3d-state-file, round 16 (round 15's fixes and TST-953's, Opus)

- **Scope:** `git diff 3e99549 830345f -- . ':(exclude)PLAN.md'`.
- **How:** one Opus reviewer, the whole diff; the claim file and each entry. No tests run, no probes.
- **Notes, not findings:** under HLP-292 (the record of which case failed first) and HLP-291 (its live check reads the
  put-back only); TST-952's retyped line keeps a comment naming two of the six kinds (generation 3).
- **Resolutions assessed:** HLP-291 to HLP-293, SRV-280, TST-951 to TST-953 hold; questioned: HLP-292 (TST-954).
- **Findings:** TST-954 (Low, generation 2), TST-955 (Low). Only a few Low: once fixed, an Opus round on the entire
  branch.
- **Checked and found fine:** `relinked()` the only caller of `_relinked`, the set-back after it in both places;
  `graph=` leaving Override Material on by design; the fake relink as measured; the new unit tests failing without the
  fix; the live check's clean-up; the relink's step said unsettled once; the render saved after the put-back; the
  description's size; `USERS_PLANE_TOP` before each frames pass; the popup spells and their unit test driving the real
  watch; no fixed sleep, silenced diagnostic or `Any` added; REVIEW.md's sums.

### 2026-11-26: view3d-state-file, round 17 (the entire branch against main, Opus)

- **Scope:** `git diff main...7018093 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`.
- **How:** three Opus reviewers, split as in rounds 12 and 15; the claim file with the user's words to 2026-11-26. No
  tests run, no probes: each suspicion is settled by reading.
- **Not worth a fix:** the relink while the user's editor shows a node's own function, said as "no graph is open in
  the editor" (a rare case, the view left unlinked and said so).
- **Unspecified, settled by the lead:** a `graph=`-only shot refused when the saved base is of another format version
  (after a Designer update): refusing is the safe outcome, kept. **For the user at convergence:** whether the agent
  tells the user when a set-up shot was aborted (a cancel or the 120 s limit) and their view stays as the call set it.
- **Notes, not findings:** `_Screen`'s docstrings name the steps and the render, not the put-back, and "the Explorer's
  menu, which graph= opens", not the relink's (generation 3, nobody acts on them); ROADMAP item 92's "turns the panel
  back nowhere", true in its own sense; `categories.py`'s times predate the checks added since (dated, the order holds);
  the editor holding VIEW3D_PLAIN after the no-pattern check (no check passes falsely); `VIEW_SETTINGS`' comment on a
  timeout (generation 4).
- **Resolutions assessed:** this branch's in each area hold; questioned: TST-921 (TST-956), TST-937 (TST-957), TST-943
  (TST-958).
- **Findings:** TST-956 to TST-959, HLP-294 (Low). **Only a few Low, none above: the reviews converge once they are
  fixed.**
- **Checked and found fine:** the sequence against steps 3 and 4, the error and abort paths, the bookkeeping, the
  camera and fields, state3d's checks and maths, `standalone`, the waits; removed code referenced nowhere; DECISIONS.md
  changed only as the user said; the agents' effort as the user set it; the tool's descriptions and README against the
  code; `shoot_3d`'s order; every new check failing without what it guards; the clean-up on failure; the facts the code
  relies on pinned or listed; no new `Any`, `cast`, `type: ignore`, `noqa` or fixed sleep.
---

## High

## Medium-high

## Medium

## Low-medium

- [x] **TST-889 · The one-field check's mesh row can't fail on the mesh it edits** · `tests/test_all_tools/facts/state_file.py:417-421`, `tests/test_all_tools/facts/checks.py:376-407` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** The check drops every differing path that matches the row's `follows`. The mesh row's `follows`,
    `^/database/(scene/external_scenes|material_mapping_table|selection)/`, matches the field it edits,
    `/database/scene/external_scenes/_1/id` (`values()`, `state_file.py:373`). The other rows' `follows` cover other
    paths than their edits.
  - **Scenario.** A Designer that ignores the file's mesh id on a load keeps the Plane. The state saved after the load
    then differs from the one written only at exempt paths, `changed` holds and the view restarted, so "a state file
    with only its mesh edited loads it" passes. Step 4's mesh through the file relies on that load.
  - **Fix.** Exempt a `follows` path only when the edit didn't change it, which guards every row; or check
    `values(after)['mesh'] == 'sphere'`.
  - **Resolution: done**.
    - **Test:** `test_a_field_edited_that_a_load_put_back_is_reported_though_it_follows_others` (`tests/unit/test_selftest_state_file.py`) failed:
      `[] == ['/database/scene/external_scenes/_1/id']`. Live: a mesh row editing the id to `no_such_mesh` fails.
    - **Cause:** a `follows` path was exempt even when it was the field the row edits.
    - **Fix:** `state_file.not_loaded(changed, written, after, follows)` never exempts a field the edit changed.
    - **Also covered:** every row goes through `not_loaded`.

- [x] **TST-890 · On Windows, the state file checks run in a Designer that shares the user's AppData, and `kept` doesn't need its Save to have worked** · `tests/test_all_tools/facts/state_file.py:286-309`, `tests/test_all_tools/facts/checks.py:46-49` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.**
    - The checks skip only on `ctx.was_running`. On Windows, a run that finds no Designer starts one, and
      `_own_home` gives it no home of its own (`lifecycle.py:310-315`): it reads and writes the user's AppData.
    - `kept` checks only that a file is at the path after `_sf_save()`. `_sf_save` refuses outside
      `CFFIXED_USER_HOME`, but `in_designer` returns that refusal as text, and the user's own default state file
      satisfies the check.
    - From there the checks write the user's `user_view3d_settings.sbsscn` (`state_file.write`), and the menu entries
      check removes it (`os.remove(path)`, `state_file.py:169`). The comment at `checks.py:46-47` says the opposite:
      "never the user's".
  - **Scenario.** A Windows self-test run started with Designer closed, then killed or failing between a write and the
    `finally`, leaves the user's default 3D view state edited or deleted. Their next launch starts the 3D view from it.
  - **Fix.** `kept` refuses before any copy or write unless the path is under the `CFFIXED_USER_HOME` that Designer
    reports. Or the checks skip off macOS too. Correct the comment and `state_file.py`'s docstring.
  - **Resolution: done**.
    - **Test:** `test_the_state_file_checks_skip_where_designer_has_no_home_of_its_own[Windows]` and
      `test_kept_touches_no_state_file_when_designer_refuses_one_outside_its_home` (`tests/unit/test_selftest_state_file.py`) failed. Live: the entries
      check's new `REFUSED_WITH_NO_HOME` fails with the guard taken out of `_sf_path`, and passes with it.
    - **Fix:** `skipped_in_users` skips off macOS too. The home guard moved from `_sf_save` into `_sf_path`, which
      every Designer-side path comes from: the Save, the entries check's `os.remove`, the copies and the mid-load Save.
      `kept` takes its path through `_sf_path` and raises before copying anything when Designer gives none. The comment
      and the docstring say so.
    - **Also covered:** a probe pointing `CFFIXED_USER_HOME` at a folder inside the home didn't trip the guard: Qt's
      AppDataLocation follows the variable each time it is read. So the live check unsets it, the Windows case.
  - Questioned by TST-908 (2026-11-25).

- [x] **TST-891 · The moves check pins neither a zoom away nor an orbit over the pole** · `tests/test_all_tools/facts/state_camera.py:34,44-56`, `tests/test_all_tools/facts/state_file.py:134`, `tests/test_all_tools/facts/checks.py:448-486` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.**
    - The moves are `zoom=2` (closer) and a pitch of 20. `ZOOM_STEP = 0.9` is a step closer. A step away (x1.1,
      measured, not the inverse) is checked nowhere, though the tool takes a negative `zoom`.
    - `pose()`'s branch for a pitch beyond 90 (`matrix[5] < 0`), and the docstring's "goes over the top", are reached
      by no check. `VIEWS` stops at 90 and the moves at 20. Step 1's text asks for the pitch's limits. Today's `orbit`
      takes 90 up from any view, so 120 from Default.
  - **Scenario.** Step 3 moves the camera through the file. A zoom away that reuses 1/0.9, or an orbit clamped at 90,
    makes `zoom=-n` or a high orbit differ from today's, with no check failing.
  - **Fix.** Add a zoom away and an orbit over the pole to the moves, each checked against the file's decode. Frame
    the Front pose they start from in the moves' own script: today the check compares against the Front framed earlier,
    from another view, at a tolerance 50 times tighter than the views check's.
  - **Resolution: done**.
    - **Test:** `test_the_moves_turn_then_pan_along_the_turned_camera_then_zoom[-3-133.1]` (`tests/unit/test_selftest_state_file.py`) failed: 0.9^-3 gave
      137.17. Live: `ZOOM_AWAY = 1/0.9` fails the new move, and so does a pitch expected clamped at 90.
    - **Fix:** `ZOOM_AWAY = 1.1`, and `after_moves` takes `zoom`. A second move: Default, orbit [0, 90] (to 119.95
      degrees, over the pole), zoom -3. Each move frames its start view and saves it in its own script (`_sf_moved`),
      which makes the review log's unsettled suspicion moot.
  - Questioned by TST-902 and TST-905 (2026-11-25).

- [x] **TST-892 · The glide is shown by a paint count, and its end by nothing** · `tests/test_all_tools/facts/state_file.py:378-383,95-112`, `tests/test_all_tools/facts/checks.py:395-405` · confirmed · found 2026-11-25 by two reviewers (Sonnet)
  - **Defect.**
    - "The load glides" is `held >= GLIDE`, at least 10 paints with the count held at its restart. That is a rate:
      the 50 to 60 paints were measured in a scratch run, and a jump drew 3. `None` counts are counted too.
    - "The glide has ended" rests on the state saved after `moved` equalling the one written. That tells only if a
      Save writes the camera mid-glide, which the developer's probes measured but no check shows.
    - Step 3 relies on every load gliding, an unchanged camera included. Only the camera row asserts a glide.
  - **Scenario.** Under the parallel full run's load (four Designers), a real glide draws fewer than 10 paints and the
    check fails. If Save wrote the target pose instead of the live one, a `moved` that returned early would still
    pass.
  - **Fix.** Replace the paint count with a control: a Save made after the load has read the file and before `moved`
    holds a camera other than the one written, and the Save after `moved` holds the one written. Do it for the camera
    row and for one row with the camera unchanged. Drop `GLIDE`.
  - **Resolution: done**.
    - **Test:** live, the camera saved after the glide instead of at the load's end fails the camera row alone
      (0.00 degrees off).
    - **Cause:** part of the finding's premise was wrong, and so was step 1's "every load glides": a load whose
      camera equals the session's doesn't glide at all (5 rows, 2 probe loads). Files built on another Designer's
      state glided from near the default pose; a camera this Designer had saved, about 20 units off, and a pose at yaw
      180 were jumped to (1 load each).
    - **Fix:** `GLIDE`, `HELD` and `glides` are gone. `_sf_load(mid=...)` saves once the count has restarted and the
      Scene menu checks a mesh again, after the load has read the file. The camera row is 10.8 to 13.4 degrees off the
      file's camera there; the rows with the camera unchanged are already on it (0.00 degrees); both end on it.
      Whether a row turns the camera comes from the session's camera, tracked across rows. The docstring lists where a
      glide starts as measured, not checked.
  - Questioned by TST-911 (2026-11-25).

- [x] **TST-893 · Facts later steps rely on have no check, and the docstring doesn't say which were only measured** · `tests/test_all_tools/facts/checks.py:521-530`, `tests/test_all_tools/facts/state_file.py:1-30` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.**
    - Step 1's "Done when" asks for a check of every fact a later step relies on.
    - The AOV check pins that a load resets the AOV, but not that it keeps the renderer. That is the premise of step
      3 having no code for the renderer.
    - Measured but neither checked nor said to be only measured:
      - the user's Default State File (`stateSaveFileUrl`), whose check step 3 plans;
      - the ids of the meshes other than the Sphere;
      - a load in a minimized or covered window.
  - **Scenario.** A Designer update makes Reset Scene change the renderer. Nothing fails, and the call leaves the
    user's renderer changed.
  - **Fix.** The AOV check also reads the Renderer menu's checked action before and after the load. The module
    docstring says which facts were measured but not checked, and which later step's check pins each.
  - **Resolution: done**.
    - **Test:** live, the renderer forced to look changed fails the AOV check.
    - **Fix:** the AOV check reads the Renderer menu's checked action before and after the load (Rasterizer both
      times). `state_file.py`'s docstring lists the facts measured but not checked, with the later step's check that
      pins each.
  - Questioned by TST-904 (2026-11-25).

- [x] **TST-894 · The checks' pure logic has no unit test** · `tests/test_all_tools/facts/state_camera.py`, `tests/test_all_tools/facts/state_file.py` · confirmed · found 2026-11-25 by two reviewers (Sonnet)
  - **Defect.** AGENTS.md: "pure-Python logic gets a unit test in `tests/unit`", and the self-test's own logic has
    unit tests (`tests/unit/test_selftest_*.py`). Nothing under `tests/unit` covers:
    - `state_camera`: `pose`, `encoded`, `turned` and `after_moves`;
    - `state_file`: `fields`, `_alike`, `differing`, `edited`, `values`, `skipped_in_users` and `kept`'s put-back.
  - **Scenario.** The decode breaks beyond a pitch of 90 or at the poles, or `edited` matches twice, and nothing fails
    until a live run, or a check passes on a comparison that is wrong.
  - **Fix.** Unit tests:
    - the camera: round trips `pose(encoded(p)) == p` (pitch beyond 90, yaw wrapping, the poles), `turned` on a sample
      camera text, and `after_moves`' units;
    - the state file: its comparison helpers, and `kept`'s put-back with a fake call, none left when none was found.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_selftest_state_file.py` (new, 42 tests; its fixture `tests/unit/fixtures/state_file.sbsscn`, step 1's capture trimmed, the
      home's path shortened). It covers round trips through `placed` and `pose` (pitches beyond 90, the poles, yaw
      wrapping), Designer's own matrices over and under the pole and at Top, `turned`, `after_moves`' units, `fields`,
      `_alike`, `differing`, `edited`, `values`, each `ONE_FIELD` row's changed paths, `kept`'s put-back with a fake
      Designer, and `skipped_in_users`. The tests of code already right passed at once, as a coverage finding's do; the
      others are under their own findings.
  - Questioned by TST-906 (2026-11-25).

- [x] **TST-902 · The decode's premise, a camera whose X stays level, is shown for no turn that could tilt it** · `tests/test_all_tools/facts/state_camera.py:5,60-68`, `tests/test_all_tools/facts/checks.py:511-522` · confirmed · follows TST-900 and TST-891, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.**
    - `pose()` decodes yaw as X's angle and pitch as Z's against Y's, which holds only while the camera's X stays
      level. It never reads X.y, so a tilted camera decodes without a sign.
    - The checks' turns can't tilt it: the views come from the Camera menu, move 1 turns sideways from a level camera
      (Front), and move 2 turns only up. No check turns sideways from a camera looking up or down, which is where a
      trackball camera would roll. Today's `orbit` allows it, and two calls reach it.
  - **Scenario.** Designer's sideways drag from a pitched camera turns about the camera's own Y. Step 3's `orbit` as
    yaw + right, pitch + up then differs from today's, and a camera the user left tilted decodes wrong, with no check
    failing.
  - **Fix.** Add a move turning sideways from Default (pitch 30), and one from over the pole. `pose()` raises when X.y
    isn't near 0.
  - **Resolution: done**.
    - **Test:** `test_a_tilted_camera_is_refused_as_no_pose_of_ours` (`tests/unit/test_selftest_state_file.py`) failed: a 5 degree roll decoded. Live, the
      new turn sideways from over the pole failed: yaw 14.85 against 75.15 expected, which led to
      `test_a_turn_right_over_the_pole_turns_the_yaw_the_other_way`, failing before the fix too.
    - **Cause:** no tilt: a turn sideways keeps the camera level from Default (pitch 30) and from over the pole
      (pitch 119.95). Over the pole, a turn right turns the yaw the other way (30.15 degrees right took yaw 45 to
      14.85): right as seen on screen, the camera upside down.
    - **Fix:** `pose()` raises when |X.y| exceeds `LEVEL` (1e-4). `_sf_moved(view, start, steps)` runs each step as a
      call of its own; two moves added, sideways from Default and sideways from over the pole. `after_moves` flips the
      yaw's sign when the start pitch's cosine is below 0, as step 3's `orbit` must.
    - **Also covered:** a turn sideways from Top or Bottom, and a turn up from a camera upside down, are named in
      `state_camera.py`'s docstring as not measured.

- [x] **TST-903 · The menu entries check can take the load as ended before it has started** · `tests/test_all_tools/facts/state_file.py:166-167,202-209` · confirmed · follows TST-896, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.**
    - `LOADED` waits with `_until(lambda: bool(_sf_checked('Scene')), ...)`, and `_until` reads the state first
      (`waits.py:70`). If a mesh is still checked in the Scene menu as the trigger returns, `LOADED` holds at once.
    - TST-896's fix removed the one read that showed the menu empty before the load (`LOAD_LEFT_FOR_LATER`). Nothing
      now shows that a mesh checked means the load has ended. The comment says it does.
    - `LOAD_SHOWED_NOTHING` and `NO_UNDO_STEP` are read after that wait.
  - **Scenario.** The old mesh stays checked until the event loop runs. The check then reads "the load showed
    nothing, added no undo step" before the load did anything, and passes whatever the load does.
  - **Fix.** End the wait as `_sf_load` does: a count restart since a mark, then a mesh checked.
  - **Resolution: done**.
    - **Test:** `test_the_entries_check_takes_the_load_as_ended_only_once_it_has_begun` (`tests/unit/test_selftest_state_file.py`) failed.
    - **Fix:** the entries check waits for the Scene menu to check no mesh (`LOAD_BEGAN`), then one again (`LOADED`),
      on the viewport's update requests, with no time. The docstring says the menu checks no mesh while the load
      pends.

- [x] **TST-904 · The renderer is shown kept only when it is the file's, and the Displacement toggle not at all** · `tests/test_all_tools/facts/checks.py:597-617`, `tests/test_all_tools/facts/state_file.py:26,39,230-253` · confirmed · follows TST-893, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.**
    - The check reads the Renderer menu before and after a load in a session saved at the default, Rasterizer, so
      session and file agree. A load that set the renderer from the file, or back to the default, passes as well.
    - The docstring now says the file holds the Displacement toggle and that a load kept it, as measured only.
      Step 1's item 7 names both: step 3 adds no code for either on that premise.
  - **Scenario.** The user works in the GPU path tracer. A call's Reset Scene puts the view back to the rasterizer,
    and nothing fails.
  - **Fix.** From a session whose renderer and toggle differ from the file's: switch the renderer and flip the toggle
    after the base is saved, Reset Scene, read both, then put them back.
  - **Resolution: done**.
    - **Test:** live, with a load expected to set the file's renderer, the check fails. A forced error right after the
      switch failed it and still left the Rasterizer and Displacement off.
    - **Cause:** none in Designer: a load keeps the session's renderer (the GPU Pathtracer, the file saved with the
      Rasterizer) and the session's Displacement toggle, which isn't set from the file though the file holds it. The
      finding's guess that the toggle comes from the file was wrong; the check was what was missing.
    - **Fix:** `check_a_state_file_load_resets_the_aov_and_keeps_the_renderer_and_displacement` sets the GPU
      Pathtracer and flips the toggle after the base is saved, loads, reads both, and puts both back in a `finally`
      (the toggle's put-back asserted). Not OpenGL: it draws no sample count, which the load's wait needs.
  - Questioned by TST-912 and TST-913 (2026-11-25).

- [x] **HLP-257 · A leftover backup is put back onto whatever path the next call resolves** · `mcp_server/designer_helpers/state3d.py:248-283` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** A backup records nothing of the path it came from. `_state_back_up(path, aside)` puts a leftover back
    with `_state_put_back(aside, path)`, onto the current call's path: it removes that file and its `_resources`
    folder and copies the leftover over them, or, when the leftover says there was no file, leaves none.
  - **Scenario.** A call backs up the user's file A and dies. Before the next call the path changes: the user sets a
    Default State File in Project settings, or Designer moves to a new version folder. The next call removes file B,
    the user's other file, with no backup of it. That isn't the risk the user accepted (ours left as their default).
  - **Fix.** One backup per path (its folder named after a hash of the path), or the path stored with the backup and
    a put-back refused onto another path.
  - **Resolution: done**.
    - **Test:** `test_a_leftover_backup_goes_back_to_its_own_path_and_the_next_one_is_left_alone` (`tests/unit/test_state3d.py`): path A
      backed up and left, then path B backed up. It failed: B read `<users/>` instead of `<the users own/>`.
    - **Cause:** a backup recorded nothing of where it came from, and the put-back wrote onto the path the next call
      gave.
    - **Fix:** `_state_back_up` writes the absolute path into the backup (`aside/path`); `_state_put_back(aside)`
      takes no path and puts the backup back onto the one it records, writing or removing nothing elsewhere.
    - **Also covered:** `kept` (`facts/state_file.py`) calls `_state_put_back(base)` and `(found)`; no other caller.
  - Questioned by HLP-263 (2026-11-25).

- [x] **HLP-264 · The put-back loads the user's view with no look first** · `mcp_server/designer_helpers/scene3d.py:341-351` · confirmed · found 2026-11-26 by two reviewers (Sonnet)
  - **Defect.** `between` (the shot's `screen.again`: the windows made opaque once the user made Designer the active
    app, the window put on screen again if it went off; REVIEW.md HLP-136) runs only in `begin()`, before each set-up
    step. `put_back()` prints its own "setting: the 3D view as it was" and loads the base, sets the AOV back and
    relinks through the Explorer menu with no `between()` first. The test of `between` before each step reads
    `designer.set_up()`, which stops at the render, so it can't see the put-back.
  - **Scenario.** The user makes Designer the active app during the render: for the put-back's load, glide wait and
    relink (1 to 6 s) the windows stay transparent and click-through. Off screen, the load's wait runs unwatched,
    against step 8's "wait for the glide on screen".
  - **Fix.** `between()` before the put-back's load, as `begin` makes it; the unit test of `between` extended to the
    put-back.
  - **Resolution: done**.
    - **Test:** `test_the_set_up_runs_the_shots_look_at_the_active_app_before_each_step` (`tests/unit/test_view3d_helpers.py`) reads every event, the
      put-back's included: it failed, the put-back's setting line having no `between` before it. Live: a second case of
      `check_a_3d_shot_makes_designers_window_opaque_at_once_once_designer_is_the_active_app`, Designer made the active
      app at the shot's render: before the fix nothing said the window was made opaque before the put-back.
    - **Cause:** `put_back` printed its own setting line and loaded without `begin`, the only place `between` runs.
    - **Fix:** `put_back` begins its step with `begin('the 3D view as it was')`.
    - **Also covered:** no other step skips `begin`; the relink, the AOV and Override Material run inside steps or
      loads.
  - Questioned by HLP-272 (2026-11-26).

- [x] **HLP-265 · A view the camera shows already says it changed, so the shot retakes and prints a false STALE** · `mcp_server/designer_helpers/scene3d.py:96,209-217,388`, `mcp_server/designer_helpers/shot3d.py:410-430` · confirmed · found 2026-11-26 by two reviewers (Sonnet)
  - **Defect.** `SAME_POSE = 1e-6` degrees is under the float noise of the camera Designer saves. Its own Default
    camera (`tests/unit/test_state3d.py:29-31`, X row `0.707106709, 0, -0.707106769`) decodes to yaw 45.0000024 and
    pitch 29.9999973; `_framed(..., 'Default', ...)` gives 45.0 and 30.0. Top is off by about 3e-6 the same way. No
    test runs a view equal to the camera: `_same_pose` always False passes every test.
  - **Scenario.** A fresh Designer and `view='Default'`: `changed` is True, the shot waits for a frame at rest, the
    renders are identical, and it says "identical ... though the set-up moved the camera ... may not have been drawn.
    Shoot again with the same set-up", which gives the same line again.
  - **Fix.** Compare at the file's precision (1e-4 degrees, as `CAMERA_LEVEL` does for the same noise); a unit test of
    `view='Default'` on the fixture's Default camera, `changed` False.
  - **Resolution: done**.
    - **Test:** `test_a_view_the_camera_shows_already_changes_nothing` (`tests/unit/test_view3d_helpers.py`): the fixture's Default camera and
      `view='Default'`. It failed, `changed` True.
    - **Cause:** `SAME_POSE` (1e-6 degrees) was under the noise of the camera Designer saves.
    - **Fix:** `SAME_POSE = 1e-4`, for the angles and for lengths relative to the distance, with its reason.
    - **Also covered:** no other comparison with a camera Designer saved is so tight; the self-test's `alike` takes
      0.01 degrees.
  - Questioned by HLP-273 (2026-11-26).

- [x] **HLP-266 · A Windows file URL is read as `/C:/...`, so the user's Default State File isn't backed up** · `mcp_server/designer_helpers/state3d.py:332` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** `urllib.parse.unquote(url[len('file://') :])` turns the standard Windows form `file:///C:/Users/me/s.sbsscn`
    into `/C:/Users/me/s.sbsscn`. On Windows `abspath` makes that a path under the current drive's root, `isfile` is
    False, and the backup records "no file". The URL tests use a POSIX path only.
  - **Scenario.** A Windows user with a Default State File: Designer's Save writes their real file with no backup, then
    `_state_text(path)` fails, and every call fails the same, the user's file holding the session's state. Which form
    Designer writes on Windows isn't measured (ROADMAP item 90); the code is wrong for the standard one.
  - **Fix.** `urllib.request.url2pathname(urllib.parse.urlparse(url).path)`; a unit test of a `file:///C:/...` URL read
    as Windows reads it.
  - **Resolution: done**.
    - **Test:** `test_a_windows_default_state_file_url_is_read_as_windows_reads_it` (`tests/unit/test_state3d.py`),
      `url2pathname` patched with `nturl2path`'s: it failed, giving `/C:/Users/me/My Files/s.sbsscn`.
    - **Fix:** `urllib.request.url2pathname(url[len('file://'):])`, the same unquote as before on POSIX (`urlparse` not
      used: it would split a `#` off a path).
    - **Also covered:** `server_tools/lifecycle.py:331` unquotes a file URL the same way, behind the macOS-only
      `_own_home`. Which form Designer writes on Windows stays unmeasured (ROADMAP item 90).
  - Questioned by TST-926 (2026-11-26).

- [x] **HLP-267 · A load turns Materials > Override Material on again, so the user's view doesn't come back with it off** · `mcp_server/designer_helpers/scene3d.py` (`loading`, `_aov_back`) · measured · found 2026-11-26 by the runner (Sonnet)
  - **Defect.** Measured 2026-11-26, on a reviewer's question (scratch probe, an agent's Designer, a linked graph): with Override
    Material off, a set-up shot (`view='Front'`) and a bare Save then Reset Scene each left it on, the Materials
    submenu titled "Default (overridden)" and OpenPBR Surface checked. The file saved with it off differs from the one
    saved with it on in `override_existing_material` alone (false, then true): the load ignores it, as it does the AOV.
    Of the 47 checkable entries of the 3D dock's menus and toolbars (the meshes, AOV and renderers left out), every
    other one changed came back: the Display entries, Display UVs in 2D View, the tool, the toolbar's toggles, the
    material model.
  - **Scenario.** A user who turned Override Material off sees it on after any agent's set-up shot, against "puts the
    user's whole 3D view back".
  - **Fix.** Read it before, and set it back after each load as `_aov_back` does the AOV, found by its leaf text under
    Materials (the submenu's title changes with it); a facts check pinning that a load turns it on although the file
    holds it off, and the put-back's check reading it back.
  - **Resolution: done**.
    - **Test:** the fact, `check_a_state_file_load_turns_override_material_on_though_the_file_holds_it_off` (facts),
      passes: turned off, the file holds false, a load checks the entry again. The put-back's check, "leaves Materials >
      Override Material off, as the user had it" in `check_a_3d_shot_puts_the_users_3d_view_and_default_state_file_back`,
      failed (on after the shot); `test_override_material_is_set_back_after_each_load` (`tests/unit/test_view3d_helpers.py`) failed.
    - **Cause:** a load ignores `override_existing_material` and turns the entry on; only the AOV was set back.
    - **Fix:** the entries read at the call's start (`_overrides`, each material's, in the menu's order) and set back
      in each load's wait after the AOV (`_overrides_back`), which does nothing when every entry is on.
    - **Also covered:** measured anew, the entry exists only while a graph's outputs are on the mesh (scene3d.py's and
      state_file.py's docstrings); the runner's probe found none of the 47 other entries lost.
  - Questioned by HLP-276, TST-930 (2026-11-26).
  - Questioned by HLP-291 (2026-11-26).

- [x] **TST-917 · The fake Designer loads at the trigger and its load-end wait never runs, so the put-back's order is unpinned** · `tests/unit/test_view3d_helpers.py:549-551,628,695-698` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** The fake's `Reset Scene` reads the file at the trigger; Designer reads it once the trigger has
    returned (the module docstrings). `Frames.until` returns True without calling its state, and `_scene_checked` is
    `lambda bar, keep: set()`, so `_state_load`'s end condition (`_scene_checked(bar, keep) - during`) never runs.
    Each of these passes every unit test: the backup put back, or the file rewritten, before the put-back's load
    wait; the file rewritten between the camera's trigger and its wait; the end condition replaced by True or its
    `- during` dropped.
  - **Scenario.** The user's view comes back as whatever file was there when Designer read it, or the next call's Save
    runs before a load ended and saves the scene without its mesh; only the live checks, run on the user's word, would
    catch it.
  - **Fix.** The fake applies a load at the first `until` or `settled` after its trigger, reading the file then; `until`
    calls its state; the fake menu gives `during` at the trigger and `during` plus the mesh later. Then: the put-back's
    load is `SAVED` with the backup put back after it, and the end condition is False while the checked set is
    `during`.
  - **Resolution: done**.
    - **Fix:** the fake's Reset Scene marks a load pending, read in the next wait's event loop (`settled`, or `until`
      while its state is false); `until` reads its state; the fake shows no mesh checked until the load ran.
    - **Test:** `test_a_load_ends_only_once_the_scene_menu_checks_a_mesh_again` and
      `test_the_put_back_loads_the_users_view_before_it_puts_the_backup_back` (`tests/unit/test_view3d_helpers.py`). Each mutation the entry lists
      fails one of them.

- [x] **TST-918 · The put-back's own failure and its waits have no test** · `mcp_server/designer_helpers/scene3d.py:341-351,432-441`, `tests/unit/test_view3d_helpers.py` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** No test makes the base's load or the relink raise in the put-back (`'putting the 3D view back failed'`
    appears in no test), nor makes its wait not settle; `Designer.set_up()` cuts the events at the render. The
    put-back's `try/finally` replaced by a plain sequence, the "and putting the 3D view back failed" wrapper dropped,
    the wait for the base's load dropped, or its `_unsettled` suffix dropped: each passes.
  - **Scenario.** Step 9 ("Put the backup back", "an error after step 3 still runs steps 8 and 9") broken for the case
    it is for: the user's default state file not put back after a failed put-back.
  - **Fix.** A test where the base's load raises: the user's file and folder back, the error ending "; and putting the
    3D view back failed: ..."; one where the put-back's wait doesn't settle, said; one asserting a load-end and a settle
    wait after the put-back's Reset Scene.
  - **Resolution: done**.
    - **Test:** `test_a_put_back_that_fails_still_puts_the_file_back_and_says_so` (after an error, after the render),
      `test_a_put_back_whose_view_never_settled_says_so` (at rest, the load's end) and
      `test_the_put_backs_load_is_waited_for_its_end_then_the_view_at_rest` (`tests/unit/test_view3d_helpers.py`). Each mutation the entry lists fails
      one of them.

- [x] **TST-919 · The live move checks can't tell a wrong pan rate or zoom step, and the docs say the moves are pinned** · `tests/test_all_tools/editor_panels_and_fit/checks.py:89-93,246-276,1666,1968`, `mcp_server/designer_helpers/state3d.py:8-9,23-28`, `tests/test_all_tools/facts/state_camera.py:9-14` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** The editor checks take their expected values from the code's own constants (`STEP, STEP_AWAY = 1 /
    state3d.ZOOM_STEP, 1 / state3d.ZOOM_AWAY`), and the pan check passes within 0.01 of `PANNED` (about 0.1708), a
    5.9 % band, while its docstring says "a rate 5 % off failed". With the facts moves check gone (its oracle, the
    drags, went), `PAN_RATE = 1.0` (0.1673) and `ZOOM_AWAY = 1/0.9` pass every live check; round 4 saw both fail the
    removed check. `state3d.py`'s docstring says its facts are "pinned by those checks", the moves among them;
    `state_camera.py` says they are "not checked since the drags went".
  - **Scenario.** A changed constant turns every pan or zoom-away wrong by a few percent, against "the camera's moves
    are exact" and the tool's documented x1.111 and x1.1, and no check fails.
  - **Fix.** Expected values from the documented numbers (x0.9 a step closer, x1.1 away, the pan's fraction of the
    view), not the code's constants; a pan band a 5 % rate fails, seen live first (a pixel is about 0.003 of the
    width); the two docstrings saying which moves the live checks pin.
  - **Resolution: done**.
    - **Fix:** the editor checks expect the documented steps (1/0.9 and 1/1.1), not state3d's constants. The pan band is
      `PAN_OFF = 0.005`, seen live first (0.1696 and 0.1709 against 0.1708, 0.0012 off at most); `PAN_RATE` times 1.05
      fails the pan check (0.1784) in a scratch run. state3d.py's and state_camera.py's docstrings say what the live
      checks pin and how closely: a pan rate about 3 % off still passes (`PAN_RATE = 1.0`, 2 %, would).
  - Questioned by TST-929 (2026-11-26).

- [x] **TST-920 · No live check moves the camera from the user's own view, with no `view=`** · `tests/test_all_tools/editor_panels_and_fit/checks.py:153-309`, `mcp_server/designer_helpers/scene3d.py:376-382` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** Every orbit, pan and zoom check passes `view=`; the one check of a move from where the camera was
    ("without view=, zoom counts from where the camera is") went with `set_3d_view`. `start['camera']`, and the second
    Save after a mesh switch with a camera option and no view, are reached only by the unit tests' fake.
  - **Scenario.** The user's camera decoded or applied wrong (a pan applied to Designer's default pose): "each call's
    `orbit`, `pan` and `zoom` start from the view the user left" breaks, and every live check passes.
  - **Fix.** From the user's own view set through the menus (`renders.users_checker`): a pan, a zoom and an orbit with
    no `view=`, measured as the existing checks do; one `mesh=` switch with a zoom and no view.
  - **Resolution: done**.
    - **Test:** `check_orbit_pan_and_zoom_start_from_the_users_own_view` (new), from the user's view set through the
      menus: a pan, `zoom=3`, `orbit=[0, -45]`, and `mesh='Sphere'` with `zoom=2`, each the same render as the same move
      from `view='Top'` (0.00 apart) and unlike the user's view (29 to 79). The moves started from Designer's Default
      pose fail all four (34 to 86) in a scratch run.
    - **Deviation:** the pan's size isn't measured from the user's view (the framed plane fills the render, and a pan
      clips it); the `view='Top'` checks pin it.

- [x] **HLP-272 · The put-back's look can raise before the base is loaded, so the user's view stays changed** · `mcp_server/designer_helpers/scene3d.py:384-392,410-418`, `mcp_server/designer_helpers/shot3d.py:276-296` · confirmed · follows HLP-264, generation 2 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** HLP-264's fix has `put_back` start with `begin(...)`, which runs `between` first: in `shoot_3d` that is
    `screen.again`, whose `_bring(again=True)` raises "the 3D view isn't drawn: Designer's window went off screen
    again ... shoot again" once the window went off screen each of its BRINGS times. Raised there, `loading(base)` never
    runs; the `finally` puts the backup file back, but the view keeps the shot's camera, mesh and the rest. No test
    gives a `between` that raises.
  - **Scenario.** The user keeps hiding or minimizing Designer during a shot: the render's look raises, the error path
    runs `put_back`, whose look raises again, and the call ends "...; and putting the 3D view back failed: the 3D view
    isn't drawn ...", with the user's view left as the shot set it, against "an error after step 3 still runs steps 8
    and 9". Before HLP-264's fix, the put-back loaded the base whatever the window's state.
  - **Fix.** In `put_back`, a failure of the look is said and the base is loaded all the same; a unit test whose
    `between` raises at the put-back only, the base still loaded (`designer.loads[-1] == SAVED`) and the failure said.
  - **Resolution: done**.
    - **Test:** `test_a_put_backs_look_that_fails_is_said_and_the_users_view_loaded_all_the_same` (`tests/unit/test_view3d_helpers.py`), a `between`
      raising after the render only: it failed, the error escaping and the base never loaded.
    - **Cause:** HLP-264's fix ran the look through `begin`, so a raising look skipped `loading(base)`.
    - **Fix:** `put_back` runs `between()` in a `try` of its own and keeps the failure, then prints its setting line,
      loads the base, and says " (the look before it failed: ...)" after "put back as it was".
    - **Also covered:** every other caller of `between` raises into a path that runs the put-back (each step's `begin`;
      the render's look inside the `with`). No live check: it needs a window that keeps going off screen.
  - Questioned by HLP-277 (2026-11-26).

- [x] **HLP-280 · `tiling=` is refused again once Materials > Add gave the view an unused material** · `mcp_server/designer_helpers/state3d.py:115-118,198-199`, `mcp_server/designer_helpers/scene3d.py:447`, `tests/test_all_tools/editor_panels_and_fit/checks.py:577-585` · confirmed · follows HLP-114, generation 2 · found 2026-11-26 by the lead (Opus) and two reviewers (Sonnet)
  - **Defect.** `_located` raises `TILINGS` for a `___usd___tiling` held more than once, and the state file holds one per
    material, an unused one included. HLP-114 settled that `tiling=` sets the material the mesh uses and doesn't count
    one Materials > Add added, which Designer lists as unused; its live check
    (`check_a_material_the_mesh_doesnt_use_doesnt_stop_tiling`) became one pinning the refusal. The lead's brief for step
    4 said the panel route refused all but one material, which it didn't. The refusal also comes after the window, the
    backup and the Save, where HLP-127 had the old look-up refuse first.
  - **Scenario.** A user who added a material through Materials > Add asks `tiling=2`: refused, against what the tool
    did before the branch ("keeps its options and their limits").
  - **Fix.** Measure first how the file tells the material the mesh uses (the reviewer points at
    `material_mapping_table`) or marks one unused; edit that material's tiling, counting only used ones as HLP-114 did,
    refused before anything changes as HLP-127 had it; the live check of HLP-114 back, through the file.
  - **Resolution: done**.
    - **Measured first** (an agent's Designer, 2026-11-26): Materials > Add writes a second item in the file's materials
      list, with its own `___usd___tiling`; `material_mapping_table` still maps every part of the mesh to `default`, and
      the Materials menu lists the new one "(unused)"; a load with `default`'s tiling edited leaves the other's as it
      was; another mesh id in the same load maps to `default` too.
    - **Test:** in `tests/unit/test_state3d.py`, `test_the_tiling_is_the_material_the_mesh_uses_an_unused_one_left_as_it_is`
      and `test_a_mesh_using_several_materials_is_refused_its_tiling_but_the_others_are_read_and_edited` failed; in
      `tests/unit/test_view3d_helpers.py`, the restored `_material` tests and the two new tiling tests failed. Live:
      HLP-114's `check_a_material_the_mesh_doesnt_use_doesnt_stop_tiling`, back through the file (the checker repeating
      twice as often at tiling 2 as at 1 after Materials > Add, 15 and 31 changes), failed with the shot refused.
    - **Cause:** the file holds one tiling per material, an unused one included, and step 4 refused any file holding more
      than one, after the window, the backup and the Save.
    - **Fix:** `_used_material` reads the material the mesh uses from `material_mapping_table`, and the tiling's place
      is anchored on that material's entry (`_IN_MATERIAL`); a mesh mapped to more than one raises `MATERIALS_USED`.
      `_material_checked` (view3d.py) refuses first, from the Materials menu's materials not marked "(unused)", when
      `tiling` is given and the mesh doesn't switch (HLP-127). The `tiling` description and the docstrings say a mesh
      using more than one material is refused.
    - **Also covered:** every mention of the old refusal reworded; the values-shown check reads the tiling the same way.
      Not covered: a `mesh=` switch away from a mesh using several materials is refused by the file, after the window
      (only an assigned custom material gets there: not worth a fix); the several-materials refusal is unit-tested only
      (assigning a second material isn't measured).
  - Note (2026-11-26, round 10, generation 3): two test comments the fix left false, for step 5's docs pass: the
    ordering comment at `tests/test_all_tools/editor_panels_and_fit/checks.py:2819` ("the state file then holds two
    tilings": the order no longer matters), and `tests/unit/test_state3d.py:371` ("found anywhere, it is the field":
    the tiling is anchored on the used material now; its row's `stray=False` leaves that bound unpinned).

- [x] **TST-939 · A unit test of the values-shown check fails since step 4** · `tests/unit/test_selftest_check_setups.py` (`test_the_shown_already_checks_count_of_waits_keeps_each_waits_result`), `tests/test_all_tools/editor_panels_and_fit/checks.py:750` · confirmed · found 2026-11-26 by the developer (Opus)
  - **Defect.** Step 4 made `SHOWN_ALREADY` wrap `_state_load` (`_settled, _loaded = _Frames.settled, _state_load`); the
    unit test runs the snippet in a namespace with no `_state_load`, so it raises `NameError`. It failed at 10ecc6e,
    with step 5's edits set aside: no run of the touched tests since step 4 included it.
  - **Scenario.** The final check's unit suite fails on it.
  - **Fix.** The name in the test's namespace (a stand-in the fake `shoot_3d` never calls, so the loads stay 0); then
    the tests that read the self-test's sources run again.
  - **Resolution: done**.
    - **Test:** the test itself failed at 10ecc6e with `NameError: name '_state_load' is not defined`.
    - **Cause:** step 4 made `SHOWN_ALREADY` wrap `_state_load`; the namespace the test builds never got the name.
    - **Fix:** a `_state_load` stand-in the fake `shoot_3d` never calls; the test also asserts `LOADS=0`.
    - **Also covered:** it is the only unit test running a self-test snippet in a namespace it builds by hand. The guard
      set (59 files that read or import the self-test's or the helpers' sources, with the Windows simulation, lint,
      types and the docs tests) passed: 3,500 tests.

- [x] **HLP-282 · An editor's graph with no outputs: the view is left unlinked, and nothing says so** · `mcp_server/designer_helpers/scene3d.py:230-250` (`_relinked`) · measured · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `_relinked` says why for no graph and for one output; a graph with none goes on to `_apply_outputs`.
    Measured (a runner's probe, an agent's Designer, 2026-11-26): with the view showing a two-output graph's outputs and
    an output-less graph in the editor, a set-up shot replied "orbit 30 degrees right", "put back as it was", with no
    suffix; a Save after it wrote no textures, so the view followed no graph. The Explorer's entry was enabled and picked
    with no error. Opening the output-less graph alone didn't unlink the view; the shot's load did, and nothing relinked.
  - **Scenario.** The user has a new, empty graph open in the editor: after any agent's set-up shot their view stops
    following the graph it showed, and the reply says it was put back as it was.
  - **Fix.** A graph with no outputs isn't relinked, and the suffix says why, as for one output; a unit case with no
    outputs.
  - **Resolution: done**.
    - **Test:** the case `no outputs` of `test_a_view_whose_graph_cant_be_relinked_is_said_to_follow_it_no_longer`
      (`tests/unit/test_view3d_helpers.py`) failed; live, `check_an_editors_graph_with_no_outputs_is_said_not_to_be_followed` (editor) failed, no suffix.
    - **Cause:** `_relinked` sent an output-less graph to the Explorer's menu, which took it and applied nothing.
    - **Fix:** `_relinked` says "(it no longer follows graph X, which has no outputs to show)" and doesn't relink.
    - **Also covered:** `_set_up_checked` refuses 0 and 1 outputs for `graph=` already.
  - Questioned by HLP-288 (2026-11-26).

- [x] **HLP-283 · A mesh of the user's own: every load waits its 3 s, and the shot says the view hadn't settled** · `mcp_server/designer_helpers/scene3d.py:160-170` (`_state_load`) · measured · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `_state_load` ends a load when the Scene menu checks a mesh again. Measured (a runner's probe,
    `Resources/python/tests/assets/box.fbx` as the mesh's `file://` id): the menu checks nothing at the trigger's return
    and nothing after the load (`AFTER=[]`), though the mesh loaded; the end condition never came (2.90 s, to the limit)
    and the view was at rest at once after. A shot with `orbit=[30, 0]` took 6.3 s and said "(the 3D view hadn't settled
    within 3 s after it)" on the set-up and on the put-back. The facts measured the built-in meshes only.
  - **Scenario.** The user's custom-mesh loop (2026-11-25: the agent tunes the view through the file, shot after shot):
    each shot 6 s slower, and told twice that the view hadn't settled, which reads as a stale render.
  - **Fix.** Measure first what marks the end of a load of a mesh the menu doesn't list (another callback, or the
    file's mesh known before the load); end the wait on it; a facts check pinning it with that mesh, the menu's emptiness
    included.
  - **Resolution: done**.
    - **Measured first** (an agent's Designer, 2026-11-26, `box.fbx` by its `file://` URL, built-in meshes as the
      control): for a built-in mesh the Scene menu clears at the trigger's return and checks the mesh after the load; for
      the `file://` mesh it checks none at the trigger, after, or 1 s later; the view's settle alone ended in 0.89 s, and
      a Save right after held the `file://` id.
    - **Test:** `test_a_load_of_a_mesh_of_the_users_own_ends_once_the_view_settled` (`tests/unit/test_view3d_helpers.py`) failed; live,
      `check_a_load_of_a_mesh_of_the_users_own_ends_once_the_view_settled` (facts): its fact passed, its shot failed
      with "(the 3D view hadn't settled within 3 s after it)" on the set-up and the put-back.
    - **Cause:** `_state_load` ended a load only once the menu checked a mesh again.
    - **Fix:** `loading` reads the written file's mesh; a `file://` one (`state3d.USERS_MESH`) skips the menu's wait and
      ends on the settle alone. The fact is in scene3d.py's and the facts' docstrings.
    - **Also covered:** every caller of `_state_load` (the put-back's load goes through `loading`). Not measured: a mesh
      of the user's own loaded off screen.
  - Questioned by HLP-286, HLP-287, TST-949 (2026-11-26).

- [x] **TST-940 · No check sees Designer write the textures beside the user's Default State File, which two docstrings say the lifecycle check pins** · `tests/test_all_tools/lifecycle/checks.py:590-592,651-671`, `tests/test_all_tools/facts/state_file.py:49-50` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** The check's graph is empty, so a Save writes no textures; it lists the folder after making `theirs.png`
    there itself, which holds whether Designer writes the folder or not. The set-up relies on it: `linked =
    os.path.isdir(_state_resources(path))` decides the relink, and the folder is backed up.
  - **Scenario.** If Designer wrote those textures elsewhere, a user with a Default State File would never be relinked,
    with nothing said, and no check would fail.
  - **Fix.** A graph with two outputs linked in the lifecycle check; after the first Save, PNGs beside the user's file
    and the version folder's `_resources` untouched; seen live.
  - **Resolution: done**.
    - **Test:** the lifecycle check prints the textures beside the file after the first Save, and compares the version
      folder's file and `_resources` before and after; with the empty graph it failed (`TEXTURES=None`).
    - **Fix:** the check's graph has two outputs on the mesh; the user's folder is reset before `theirs.png`; both
      docstrings say what it pins. It passes: the two PNGs beside the user's file, the version folder untouched.

- [x] **HLP-286 · A load of a mesh of the user's own gets only NO_RESTART to begin, the wait's limit taken as its time** · `mcp_server/designer_helpers/scene3d.py:172-174`, `mcp_server/designer_helpers/frames3d.py:106,268` · confirmed · follows HLP-283, generation 2 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** With `listed` False nothing marks the load's end: `_Frames.settled` waits at most NO_RESTART (1 s) for a
    restart and, with none, returns True as if the step changed nothing. A built-in mesh's load gets its second only once
    the menu showed the load ended; a `file://` one's whole load must begin drawing within it (`.claude/rules/waits.md`:
    a limit is a safety net, never the time the wait is expected to take). `box.fbx` began in time.
  - **Scenario.** The user's custom-mesh loop with a mesh slower to import: the wait ends before the load, the render is
    taken mid-load with no "hadn't settled", and a load ending after `_aov_back` and `_overrides_back` leaves the AOV at
    Beauty and Override Material on.
  - **Fix.** For a mesh the menu doesn't list, wait for the load's own restart up to SETTLE_LIMIT before the settle (a
    set-up's load always writes a change, so it restarts the view); a unit test of a restart coming after NO_RESTART.
  - **Resolution: done**.
    - **Test:** in `tests/unit/test_frames3d.py`, `test_a_loads_restart_coming_after_no_restart_is_waited_for` (the load
      drawing 2 s on), `test_a_load_that_never_restarts_the_view_says_so` and the off-screen and no-count cases; the
      user's-mesh test in `tests/unit/test_view3d_helpers.py` expecting a `restarted` wait before each settle; live, the
      facts check of a user's mesh printing `RESTARTED`. They failed (`restarted` didn't exist; the old steps).
    - **Cause:** an unlisted mesh's load waited on `settled` alone, which takes no restart within NO_RESTART as no
      change.
    - **Fix:** `_Frames.restarted` waits up to SETTLE_LIMIT for the load's restart (off screen, its UpdateRequest), shared
      with `settled`'s first wait through `_restart`; `_state_load` runs it before the settle for an unlisted mesh.
    - **Also covered:** with no sample count shown, `restarted` returns at once, so a slow load of a user's mesh with the
      count hidden still gets NO_RESTART for its first changed render: three rare conditions together, not worth a fix
      (KISS).
  - Questioned by HLP-289 (2026-11-26).
  - Note (2026-11-26, round 14): the fake's `restarted` always returns True, so no unit test sees `_state_load` drop
    its result; `test_a_load_that_never_restarts_the_view_says_so` shows only that `restarted` returns False.

- [x] **HLP-291 · The relink after a load turns Override Material on again, after it was set back** · `mcp_server/designer_helpers/scene3d.py:439-443,460-461,504-506` · measured · follows HLP-267, generation 2 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** Each load's wait sets Override Material back (`_overrides_back`), and only then does `_relinked` run the
    Explorer's "View Outputs In 3D View". Measured (a runner's probe, an agent's Designer, 2026-11-26, two rounds each):
    with the entry off, that menu entry alone turned it on; a set-up shot (`orbit=[30, 0]`) on a linked view ended with it
    on. The unit fake's `apply_outputs` never touches it, and the live put-back check never relinks (its view isn't linked,
    and the category's graph has one output).
  - **Scenario.** A user with Override Material off, the view following a graph: after any agent's set-up shot it is on
    again, HLP-267's symptom, and the render itself is overridden.
  - **Fix.** Override Material set back after the relink, in the set-up and the put-back; the fake's relink turning it
    on; a live case with the view linked, seen failing first.
  - **Resolution: done**.
    - **Test:** the fake's relink turns Override Material on, as measured; `test_override_material_is_set_back_after_each_relink`
      (`tests/unit/test_view3d_helpers.py`) failed, the relink leaving it on; live, `check_a_set_up_shot_on_a_view_following_a_graph_leaves_override_material_off`
      (editor) failed ("after the shot [True]") and passes.
    - **Cause:** each load's wait set Override Material back, then the relink turned it on again.
    - **Fix:** a `relinked()` closure runs `_relinked`, then `_overrides_back`, for the set-up and the put-back.
    - **Also covered:** `graph=`'s step leaves it on (the call asked for those outputs), pinned by
      `test_graphs_outputs_put_on_the_mesh_leave_override_material_on`; the put-back sets it back off.
  - Note (2026-11-26, round 16, generation 3): the live check reads Override Material after the put-back only, so it
    would pass with the set-up's half missing; the render's overriding is the unit test's (`rendered == [[False]]`).

- [x] **TST-953 · The Explorer menu's time on screen is measured from the first popup seen to the last, across the shot** · `tests/test_all_tools/editor_panels_and_fit/popups.py:83-85`, `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_a_3d_shot_with_graph_keeps_the_explorers_menu_off_the_screen`) · measured · found 2026-11-26 by the developer (Opus)
  - **Defect.** `shown_ms` is `(times[-1] - times[0]) * 1000`. A `graph=` shot on a linked view now opens two Explorer
    menus, the step's and the put-back's relink, so two glimpses 1.2 s apart read as 1.2 s on screen. Measured in a
    whole category run (2026-11-26): "popups on screen for 1197 ms, in 2 of 14539 samples"; two other runs read 0 ms.
  - **Scenario.** A correct run fails the check at random in the final check.
  - **Fix.** Each spell of sightings measured on its own, the longest compared with the limit; a unit test of two
    glimpses apart.
  - **Resolution: done**.
    - **Test:** `test_two_glimpses_far_apart_are_two_spells_on_screen` (`tests/unit/test_selftest_popups.py`), the real
      `PopupWatch` with its sampling faked, failed by value (1200 ms where the longest spell is 3 ms), and again with the
      old measure put back.
    - **Fix:** `PopupWatch` records spells of consecutive sightings; `shown_ms` returns the longest, from its first
      sighting to its last; the check names the spell it reports. A scratch run on a linked view with `graph=` passed
      ("0 ms at the longest of 1 spells, in 1 of 15868 samples").

## Low

- [x] **TST-895 · The no-undo-step fact passes when no undo list is read** · `tests/test_all_tools/facts/state_file.py:160-165` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `_sf_undo()` returns `None` when it finds no button or no menu, and the check compares the list before
    and after the Save: `None == None`, or `[] == []`, passes. `w.defaultAction()` isn't held, while
    `designer_rollback.py` documents that a menu read through a dropped wrapper is deleted.
  - **Scenario.** A Designer whose undo button has another name passes "adds no undo step" without reading anything.
  - **Fix.** Hold the action, and require a non-empty list read before and after.
  - **Resolution: done**.
    - **Test:** live, the undo button's name changed fails `NO_UNDO_STEP`; before the fix, `None == None` passed.
    - **Fix:** the button, its action and its menu are held, and the list read must be non-empty.

- [x] **TST-896 · The menu entries check takes ten event passes for "before the load"** · `tests/test_all_tools/facts/state_file.py:170-182` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `LOAD_LEFT_FOR_LATER` reads "no mesh yet" after `_process_events()` following Reset Scene. That is
    true only while the load takes longer than those passes: a measured time, against `.claude/rules/waits.md`.
    `check_reset_scene_reads_the_state_file_once_it_has_returned` pins the late read without a time. The
    `_process_events()` after the synchronous Save adds nothing.
  - **Scenario.** A faster machine loads within the passes, and the check fails although Designer behaves as measured.
  - **Fix.** Drop `LOAD_LEFT_FOR_LATER` and the pass after the Save.
  - **Resolution: done**.
    - **Test:** `test_the_entries_check_takes_no_event_passes_for_before_the_load` (`tests/unit/test_selftest_state_file.py`) failed.
    - **Fix:** `LOAD_LEFT_FOR_LATER` and both `_process_events()` calls are dropped.
  - Questioned by TST-903 (2026-11-25).

- [x] **TST-897 · `kept`'s put-back isn't complete when the end load fails** · `tests/test_all_tools/facts/state_file.py:305-309` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** The `finally` puts back the base, loads it, then puts back the file found. If the load's call raises,
    the file found isn't put back. The load's own result, `LOADED`, isn't read.
  - **Scenario.** A load that fails leaves the check's mesh and camera in the Designer, and the next state check's
    base includes them.
  - **Fix.** Nest the `finally` so the file found is always put back, and fail the check when the end load says
    `LOADED=False`.
  - **Resolution: done**.
    - **Test:** `test_kept_puts_back_what_it_found_when_the_end_load_fails_then_says_so` (`tests/unit/test_selftest_state_file.py`), not loaded and
      raising, failed: DID NOT RAISE, and `'<saved/>' == '<found/>'`.
    - **Fix:** a nested `finally` always puts back what was found, then raises unless the end load says
      `LOADED=True`.

- [x] **TST-898 · A state file check that raises ends `facts.run`, and the checks after it never run** · `tests/test_all_tools/facts/checks.py:874-882` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** The eight state file checks run in the middle of `run`. `kept`, `edited`, `pose` and `turned` raise
    `RuntimeError` on a format they don't know, which is what a facts check should catch. The category then records
    only that `facts.run` didn't reach its end (`category_run.py:78-83`).
  - **Scenario.** A Designer update changes the state file's format: the dot properties, package UID and reload UID
    checks after them don't run.
  - **Fix.** Run the state file checks last in `run`.
  - **Resolution: done**.
    - **Test:** `test_the_state_file_checks_run_last` (`tests/unit/test_selftest_state_file.py`) failed. Its first version passed on the bug, comparing
      only the `check_` awaits while the checks after them were inline code; rewritten, it failed for that reason.
    - **Fix:** the state file checks are the last awaits of `run`. The UID checks became
      `check_a_packages_uid_survives_saving_and_a_restamped_one_loads`.
  - Questioned by TST-910 (2026-11-25).

- [x] **TST-899 · The views check is named for every view framed, and measures the Plane at one viewport size** · `tests/test_all_tools/facts/state_file.py:18-19,125-127`, `tests/test_all_tools/facts/state_camera.py:5-6`, `tests/test_all_tools/facts/checks.py:452` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `VIEWED` frames each view on the Plane alone, in the self-test's viewport. The check's name, "each view
    framed looks along its direction, at one point and distance", and the docstrings don't say so. The framing
    distance's dependence on the mesh and on the viewport's aspect is in a docstring only.
  - **Scenario.** A reader takes the views' framing as checked for every mesh and size.
  - **Fix.** Name the Plane in the check and the docstrings. Say that the dependence on the mesh and the aspect was
    measured, not checked.
  - **Resolution: done**.
    - **Fix:** names and docstrings only: "each view framed on the Plane", in the self-test's viewport.
      `state_camera.py`'s docstring gives Frame's dependence on the mesh and the viewport's aspect as measured, not
      checked.

- [x] **TST-900 · The decode branches on the sign of Y.y; a decode without the branch covers the pole** · `tests/test_all_tools/facts/state_camera.py:44-56`, `tests/test_all_tools/facts/checks.py:464` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.**
    - `pose()` decodes yaw and pitch with `asin(Z.y)` and flips both when Y.y is negative. With the camera's X level,
      yaw = atan2(-X.z, X.x) and pitch = atan2(Z.y, Y.y) give both for any pitch, with no branch. That checks out
      for X = (cos y, 0, -sin y), Y = (-sin p sin y, cos p, -sin p cos y), Z = (cos p sin y, sin p, cos p cos y).
    - The comment at `checks.py:464` says Top reads 89.98 degrees because Z.y is float32's nearest to 1. The check
      doesn't show whether Z's other components are 0 or the camera really is at 89.98.
  - **Scenario.** A maintainer reads the comment's cause as measured, or keeps the branch where a sign near zero
    decides it.
  - **Fix.** Use the decode without the branch. Word the comment as what was read, or drop it.
  - **Resolution: done**.
    - **Test:** `test_designers_cameras_at_and_beyond_the_pole_decode_as_loaded[Top]` (`tests/unit/test_selftest_state_file.py`) failed: the pitch was off
      by 0.0198 degrees.
    - **Fix:** the decode without the branch, yaw = atan2(-X.z, X.x) and pitch = atan2(Z.y, Y.y). The checks'
      expectations are unchanged and pass. The Top comment is gone.
  - Questioned by TST-902 and TST-907 (2026-11-25).

- [x] **TST-901 · Types, and a docstring that says more than the check** · `tests/test_all_tools/facts/state_camera.py:38,81`, `tests/test_all_tools/facts/state_file.py:23-24,363-379` · confirmed · found 2026-11-25 by two reviewers (Sonnet)
  - **Defect.**
    - `Pose.target` is `tuple[float, ...]` for a point, and `after_moves`' `viewport`, `orbit` and `pan` are
      `Sequence[float]` for pairs (`.claude/rules/python.md`).
    - `values()` returns a `dict[str, str]` of six fixed keys, which a `TypedDict` fits.
    - The docstring says a Save after a load "deletes the folder". The check reads `[]` for a missing folder and an
      empty one alike (`checks.py:502`).
  - **Scenario.** A type checker can't catch a point of two numbers. A reader takes the folder's deletion as checked.
  - **Fix.** `tuple[float, float, float]` and `tuple[float, float]`; a `TypedDict`; and either "no textures remain" or a
    check that the folder is gone.
  - **Resolution: done**.
    - **Fix:** `Pose.target` is `tuple[float, float, float]`, `after_moves` takes pairs, `Values` is a `TypedDict`,
      and `pair()` replaces `numbers()`. The relink check requires the folder to be gone after the load's Save, and it
      is. No wrong-expectation run was made for the folder.
  - Questioned by TST-909 (2026-11-25).

- [x] **TST-905 · A camera beyond a pitch of 90 is loaded by no live check, and isn't listed as measured only** · `tests/test_all_tools/facts/state_camera.py:8`, `tests/test_all_tools/facts/state_file.py:28-39` · confirmed · follows TST-891, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** Step 1's item 4 asks for the pitch's limits. Only today's orbit up over the north pole is checked
    live. Not checked: an orbit down over the south pole, and a load of a camera beyond 90 or -90, which step 3 writes
    whenever an orbit crosses a pole. The unit tests' matrices can't fail on a Designer change. The docstring's list
    of facts measured but not checked doesn't name these.
  - **Scenario.** A Designer that clamps a loaded camera at 90 breaks step 3's orbit over the pole, with no facts check
    failing.
  - **Fix.** Load a camera at pitch 100 and -100 in a check, each read back as written. Or list them as measured, not
    checked, with step 3's check that pins them.
  - **Resolution: done**.
    - **Fix:** the docstring change, the simpler of the two: the loads at pitch 89, 90, 100, -100 and 180 and at yaw
      200 are listed as measured once each, not checked, with step 3's checks of an orbit over the pole as their
      later check.
  - Questioned by HLP-284 (2026-11-26).

- [x] **TST-906 · Camera helpers added by the fixes have no unit test, and yaw wrapping is shown by one case** · `tests/test_all_tools/facts/state_camera.py:99-124`, `tests/test_all_tools/facts/state_file.py` (`pair`) · confirmed · follows TST-894, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `away` and `turned_apart`, on which the glide's verdict rests, have no unit test. `angle_off` is
    reached only by round trips whose largest yaw is 180, where +180 and -180 give 0 either way. `pair`, which parses
    the moves' `VIEWPORT`, `ORBIT` and `PAN`, has none.
  - **Scenario.** A broken wrap or a misparsed pair passes every unit test.
  - **Fix.** `angle_off(179, -179) == 2` and `angle_off(10, 370) == 0`, `turned_apart` across 180, `pose(away(...))`
    at `AWAY` with the target and distance kept, `pair` on `0.0,-1e-05` and refusing one number.
  - **Resolution: done**.
    - **Test:** new tests in `tests/unit/test_selftest_state_file.py` of `angle_off` (179 and -179, 10 and 370, -170 and 170, 0 and 180), `turned_apart`
      across 180, `away`, and `pair` (one value, refusals). They pass on the code as it is, as a coverage finding's do;
      with the wrap taken out of `angle_off`, 4 failed.

- [x] **TST-907 · The moves check is named for item 74's decode, which `pose()` no longer is** · `tests/test_all_tools/facts/checks.py:511,518` · confirmed · follows TST-900, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** The check's name, "moves it as item 74's decode says", and its docstring name ROADMAP item 74's decode:
    yaw = atan2(Z.x, Z.z) and pitch = asin(Z.y), which can't go beyond 90. `pose()` decodes otherwise since TST-900.
  - **Scenario.** A developer of step 3 copies item 74's formulas and gets a pitch capped at 90.
  - **Fix.** Name `state_camera.pose` in the check and its docstring. The lead carries the decode into ROADMAP item 74's
    note in step 5.
  - **Resolution: done**.
    - **Fix:** the moves checks are named "... moves it as state_camera.pose decodes it", and the docstring names
      `state_camera.pose`. ROADMAP item 74's note is the lead's, in step 5.

- [x] **TST-908 · TST-890's unit test of `kept` passes on the `kept` before the fix** · `tests/unit/test_selftest_state_file.py:256-264` · confirmed · follows TST-890, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** The fake answers the path's call with the refusal. The `kept` before the fix already raised when no
    `PATH=` was printed, with the refusal's text, "own home" included, and touched nothing. So the test passes without
    the fix, and TST-890's resolution says it failed. The Designer-side guard is pinned by the live
    `REFUSED_WITH_NO_HOME` alone.
  - **Scenario.** A reader takes the unit test as the guard's test.
  - **Fix.** The test's comment says it pins the server side's refusal, and that the live row pins the guard.
  - **Resolution: done**.
    - **Fix:** the unit test's comment says it pins `kept`'s own refusal, and that the guard in `_sf_path` is pinned
      live by `REFUSED_WITH_NO_HOME`. So TST-890's resolution saying that test failed is wrong: it failed against an
      intermediate guard of the developer's, not the code before the fix.

- [x] **TST-909 · The relink check can't tell the Save from the load as what removed the textures' folder** · `tests/test_all_tools/facts/state_file.py:24-25`, `tests/test_all_tools/facts/checks.py:565-594` · confirmed · follows TST-901, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** The docstring says a Save after a load "deletes the folder". The check reads the folder only after a
    load and a Save, so the load deleting it reads the same. TST-901's new requirement that the folder be gone was
    never seen failing.
  - **Scenario.** A reader takes "never Save between a load and the relink" as shown by the check.
  - **Fix.** Narrow the sentence to "after a load and a Save, the folder is gone", or read the folder after the load
    too. See the requirement fail once in a scratch run.
  - **Resolution: done**.
    - **Test:** live, with the folder required gone right after the load, the check fails.
    - **Fix:** the relink check reads the folder after the load too, and requires it there; after the Save, gone. The
      docstring says the load leaves the folder and the Save deletes it.

- [x] **TST-910 · TST-898's test doesn't require the state file checks to run together** · `tests/unit/test_selftest_state_file.py:292-299` · confirmed · follows TST-898, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** The test requires only that no `await` follows the last state file check. One state file check before
    the UID checks and the rest after passes it, and that is the bug TST-898 guards.
  - **Scenario.** A later edit puts a check between them, and a state file check that raises skips it again.
  - **Fix.** Require the last awaits of `run` to be the state file checks, all of them.
  - **Resolution: done**.
    - **Test:** `test_the_state_file_checks_run_last_all_together` (`tests/unit/test_selftest_state_file.py`) requires the last awaits of `run` to be every
      state file check. With one moved before the UID check, it failed where the old test passed. The test is the
      fix.

- [x] **TST-911 · A missing mid-glide file makes the one-field check raise instead of failing its row** · `tests/test_all_tools/facts/checks.py:446,455` · confirmed · follows TST-892, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `state_camera.pose(state_file.read(mid))` runs before the `MID_SAVED == 'True'` condition. When the
    mid Save didn't happen, `read` raises `FileNotFoundError`: the row isn't recorded, `facts.run` ends, and the
    checks after it don't run. The `MID_SAVED=False` text is lost.
  - **Scenario.** A mid wait that ends at its limit under load hides why, and skips the AOV and relink checks.
  - **Fix.** Read the mid file only when `MID_SAVED` is `True`; otherwise fail the row with the text's tail.
  - **Resolution: done**.
    - **Test:** live, with the mid Save suppressed, the check raised `FileNotFoundError`.
    - **Fix:** the mid file is read only when `MID_SAVED=True`; otherwise the row fails with "no Save at the load's
      end" and the text's tail. Seen: 6 rows failed, and the check after it ran.
    - **Also covered:** round 2's open question. Run beside three categories (`--workers 4 --only facts functions
      measure params`, twice, exit 0, no failure), the camera row was 12.28 and 13.26 degrees off at the load's end;
      unloaded runs gave 8.55 to 13.4. The mid-glide control holds under load.
  - Note (2026-11-25): the moves check has the same pattern: `state_file.pair(t, 'VIEWPORT')` (`checks.py:554`)
    raises when `_sf_moved` fails in Designer, losing the text and skipping the checks after it. Only a failing run
    meets it (round 3).

- [x] **TST-912 · The put-back of the renderer, Displacement and the AOV isn't "whatever fails"** · `tests/test_all_tools/facts/state_file.py:239-241,286-290` · confirmed · follows TST-904, generation 3 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** The comment says the three are "put back whatever fails". In the `finally`,
    `renderer_back and _sf_displacement(displacement) == displacement` skips the toggle's put-back when the switch back
    to the renderer times out, and a raise in `_sf_menu('Renderer', ...)` skips the toggle's and the AOV's. The check
    still fails then, through `PUT_BACK=False`.
  - **Scenario.** The GPU Pathtracer is slow to switch back under load: the `facts` category's disposable Designer
    ends with Displacement flipped, the check failed, as the last check of `facts.run`.
  - **Fix.** Generation 3: narrow the comment to what the code does ("put back, unless the switch back to the renderer
    fails").
  - **Resolution: done**.
    - **Fix:** generation 3, the claim narrowed: the comment above `VIEW_SETTINGS` says the renderer, the Displacement
      toggle and the AOV are put back unless the switch back to the renderer fails. The comment line left twice is
      gone.

- [x] **TST-913 · The docstring says a load keeps the toggle though the file holds one, which no check reads, and the toggle was tried at the GPU Pathtracer only** · `tests/test_all_tools/facts/state_file.py:27-29,280-285`, `tests/test_all_tools/facts/checks.py:614-616` · confirmed · follows TST-904, generation 3 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** Under "What the checks re-measure", the docstring says a load keeps the session's Displacement toggle
    "though the file holds one (`rs-adobe_displacementenabled`)". No check reads that field. The check flips the
    toggle only with the GPU Pathtracer set; the check's name and that sentence don't say so.
  - **Scenario.** A reader takes the field and the Rasterizer case as checked.
  - **Fix.** Generation 3: move the field's clause to the list of facts measured but not checked, and say in the
    sentence and the check's name that the toggle was tried with the GPU Pathtracer.
  - **Resolution: done**.
    - **Fix:** generation 3, the claim narrowed: the field's clause moved to the docstring's list of facts measured but
      not checked ("the file holds a Displacement toggle (`rs-adobe_displacementenabled`), which a load with the GPU
      Pathtracer set left as the session had it"). The checked sentence and the check's name say the GPU Pathtracer was
      set. Also, with it: the unit test file's header names the IDs its tests cite, and TST-903's sentence is narrowed
      to its two readings.

- [x] **TST-914 · Wrong camera code and unbounded places pass every unit test** · `tests/unit/test_state3d.py:130-134,178-186,206-229`, `mcp_server/designer_helpers/state3d.py:73-76,214-240` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** Each of these leaves the unit tests green:
    - a wrong X or Z component of `_camera_matrix`'s Y row: the decode reads only Y.y, and the camera edit's test
      builds its expectation with `_camera_matrix` itself;
    - `pitch - up` for the orbit: both moves tests turn with `up = 0`;
    - a pan up along world Y instead of the camera's: the one pan test starts at pitch 0;
    - `_IN_MESH` or `_IN_CAMERA` with `.*?` for their bounded dot: the fixture has nothing after them to match.
  - **Scenario.** Step 3 writes a mirrored camera, or an orbit up turned down; only the live moves check, run on the
    user's word, would catch it.
  - **Fix.** `_camera_matrix(_camera_pose(M))` close to M for the four Designer matrices in the tests; a move with a
    pitch other than 0 and `up` other than 0; a fixture copy with an `<id>` or `<dist_to_target>` after the entity.
  - **Resolution: done**.
    - **Test:** in `tests/unit/test_state3d.py`, each failing on the wrong code it guards:
      `test_designers_cameras_decoded_are_written_back_as_designer_saved_them` (four Designer matrices, all 16
      numbers; Y's x negated failed Default and under the pole);
      `test_an_orbit_up_from_a_pitched_camera_raises_it_by_its_degrees` (failed with `pitch - up`);
      `test_a_pan_up_from_a_pitched_camera_moves_the_point_along_the_cameras_own_up` (against Designer's saved Y row;
      failed with world y); the "lacking" test's `stray` column, the removed element put back before `</database>`
      (failed with `_IN_MESH` or `_IN_CAMERA` unbounded).
    - **Also covered:** a probe found a real saved file holds a second `<id>`, the renderer plugin's material's
      (`plugins/HdEclairRendererPlugin/materials/_1/id`), which the bounds keep out.

- [x] **HLP-258 · The part's docstring says its facts are all checked; two are measured only** · `mcp_server/designer_helpers/state3d.py:7-8,13-16,20-21` · confirmed · found 2026-11-25 by two reviewers (Sonnet)
  - **Defect.** It says everything listed is "measured ... and pinned by those checks". Two statements aren't: "Each
    set the map in a Designer just started. Once a map had been dropped on the view, the entity's own alone didn't
    (one Designer each)" (the check edits all four places at once, in a fresh Designer), and "A value at Designer's
    default is written with a `*` in front" (only the fixture shows it).
  - **Scenario.** A reader takes the map's four places and the `*` as checked.
  - **Fix.** List both as measured, not checked.
  - **Resolution: done**.
    - **Fix:** the docstring's "Measured, not checked" lists the `*` on a value at Designer's default and the map's
      four places; the checked list keeps "a value set is written with no `*`", which the values check pins.

- [x] **HLP-259 · The yaw's flip below the south pole is applied but not listed as unmeasured** · `mcp_server/designer_helpers/state3d.py:23-24,34-35,232` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `sideways = right if math.cos(math.radians(start.pitch)) >= 0 else -right` flips the yaw at every
    pitch below -90 as above 90. The flip was measured from pitch 119.95 only; the docstring's "Not measured" doesn't
    name a turn sideways from below the south pole.
  - **Scenario.** A reader takes the flip below the south pole as measured.
  - **Fix.** Name it under "Not measured", or add a move from pitch -100 to the live check.
  - **Resolution: done**.
    - **Fix:** "Not measured" names a turn sideways from below the south pole, where `_camera_moved` turns the yaw the
      other way.

- [x] **HLP-260 · The mesh's "held once" counts the external scenes' anchor, not the ids** · `mcp_server/designer_helpers/state3d.py:73,117-118` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `_IN_MESH = r'<external_scenes>(?:(?!</external_scenes>).)*?'` matches once per `<external_scenes>`,
    the first `<id>` included. A file with two scenes (`<size>2</size>`, `<_1>` and `<_2>`) gives one match: the read
    returns the first id, and an edit changes the first alone. Whether Designer writes two isn't known.
  - **Scenario.** A state file with two external scenes is edited as one, against the docstring's "each place once".
  - **Fix.** A unit test with the scene copied as `<_2>` expecting a refusal, or the docstring narrowed to "per
    anchor".
  - **Resolution: done**.
    - **Fix:** the docstring narrowed (KISS): `_located` counts each place once from its anchor, the mesh's id is the
      first in `external_scenes`, and `_IN_MESH`'s comment says the files measured held one scene (measured this
      round: size 1, the only other `<id>` the plugin's).

- [x] **HLP-261 · Types vaguer than known** · `mcp_server/designer_helpers/state3d.py:79-98,224`, `tests/test_all_tools/facts/checks.py:562-568` · confirmed · found 2026-11-25 by two reviewers (Sonnet)
  - **Defect.** `_camera_moved`'s `orbit` and `pan` are `Sequence[float]` for pairs, which TST-901 had made
    `tuple[float, float]` before the move onto the part. `_PLACES`' kinds are `str` where one of four kinds is known
    (`.claude/rules/python.md`), so a typo in a kind is invisible to mypy.
  - **Scenario.** A caller passes three numbers, or a place names a kind that doesn't exist, and no type check fails.
  - **Fix.** `tuple[float, float]`; a `Literal` of the four kinds, or a `NamedTuple` for a place.
  - **Resolution: done**.
    - **Test:** a temporary probe passing three numbers and a kind `'flot'` passed `test_types.py` before the fix and
      failed after it.
    - **Fix:** `_camera_moved`'s `orbit` and `pan` are `tuple[float, float]`; `_ValueKind` (a `Literal` of the four)
      types `_KINDS` and `_PLACES`.

- [x] **TST-915 · The byte-for-byte test's write half can't fail on macOS** · `tests/unit/test_state3d.py:244-249` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** A plain `open(path, 'w')` writes `\n` as `\n` on macOS, so the write half passes without
    `newline=''`. Only the read half is shown.
  - **Scenario.** A reader takes the write's line ends as tested.
  - **Fix.** Narrow the test's name and claim to the read, or run it in the Windows simulation.
  - **Resolution: done**.
    - **Test:** `test_the_file_is_written_and_read_byte_for_byte_also_as_windows_writes_text` (`tests/unit/test_state3d.py`) patches `open`
      with the Windows simulation's `_open_as_on_windows`; it fails with `newline=''` taken out of `_state_write`.

- [x] **HLP-262 · `standalone`'s "one module, whoever asks" is untested, and its tracebacks are a line off** · `mcp_server/designer_helpers/__init__.py:93-94,112` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** No test shows `standalone('state3d') is standalone('state3d')`, so removing `@functools.cache` passes.
    `part_source` deletes the part's import lines, and the text is compiled under the part's real file, so a
    traceback after `state3d.py:40` shows the line above the one that raised.
  - **Scenario.** A facts check that raises inside `_state_edited` points at the wrong line.
  - **Fix.** Assert the same module twice; blank the dropped lines for `standalone`'s compile.
  - **Resolution: done**.
    - **Test:** `test_a_part_taking_only_the_standard_librarys_names_runs_as_a_module_of_its_own`
      (`tests/unit/test_designer_helpers.py`) asserts the same module twice and `_state_edited`'s first line at its
      `def`; the line check failed (the blank line above).
    - **Fix:** `standalone` parses the part, drops its part imports from the syntax tree, and compiles the tree, which
      keeps the file's line numbers. `part_source` is unchanged.
  - Note (2026-11-25): `tests/unit/test_designer_helpers.py:285-286` says the part's imports are "blanked rather
    than removed"; they are left out of the syntax tree (round 5). Fixed with HLP-263.

- [x] **TST-916 · The facts modules say the tools read, edit and back up the file with the part; no tool calls it yet** · `tests/test_all_tools/facts/state_file.py:16-17,46`, `tests/test_all_tools/facts/state_camera.py:1-3`, `tests/test_all_tools/facts/checks.py:411` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** "as the tools read and edit them", "by the tools' own backup", "are the tools' own", "as the tools read
    them": today only the checks and the unit tests use `state3d`.
  - **Scenario.** A reader looks for the tool that does.
  - **Fix.** "`state3d.py`'s own", until step 3 makes the tools use it.
  - **Resolution: done**.
    - **Fix:** the facts modules, the values check's docstring, `test_selftest_state_file.py`, `test_designer_helpers.py`
      and `__init__.py` say "`state3d.py`'s own" (or "the code the helpers hold"), not "the tools'".

- [x] **HLP-263 · The backup records the absolute path but copies by the path as given** · `mcp_server/designer_helpers/state3d.py:261-270`, `tests/unit/test_state3d.py` · confirmed · follows HLP-257, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `_state_back_up` writes `os.path.abspath(path)` as the backup's path, but tests and copies the file and
    its folder by `path` as given (`os.path.isfile(path)`, `_state_resources(path)`). Every test passes an absolute
    path, so dropping `abspath` passes them all, and HLP-257's resolution says the absolute path is written.
  - **Scenario.** A caller passes a path with a trailing separator: `isfile` is false, the backup says "no file", and
    the put-back on the stripped path removes the user's real file. No caller does today (`_sf_path` joins a fixed
    name); step 3's will.
  - **Fix.** `path = os.path.abspath(path)` first in `_state_back_up`, so the test, the copy and the record use one
    path; a unit test backing up a relative path, the cwd changed before the put-back.
  - **Resolution: done**.
    - **Test:** `test_a_relative_path_is_put_back_where_it_was_once_the_working_folder_changed`
      (`tests/unit/test_state3d.py`): a relative path backed up, the working folder changed, the backup put back. It
      failed with the record made of the raw path. It passed on the code before the fix, which recorded the absolute
      path already: the defect was the copy by another path, which no test could see.
    - **Fix:** `path = os.path.abspath(path)` first in `_state_back_up`, so the record is the path tested and copied.
      The HLP-262 note's comment now says "left out of the syntax tree, so the lines keep their numbers".
  - Note (2026-11-26, round 6, generation 3): the test's comment "and copies from that same path" says more than
    the test shows: it fails only with the record made raw, and passes with the copy by the raw path. The
    resolution's "which no test could see" isn't so: a path with a trailing separator fails before the fix. No caller
    passes one (`_state_default_path` returns a file URL's path). The fix itself holds.

- [x] **HLP-268 · A Default State File changed since Designer started is edited while Designer reads another** · `mcp_server/designer_helpers/scene3d.py:259-260,358-360`, `mcp_server/designer_helpers/state3d.py:315-332` · confirmed · found 2026-11-26 by the developer (Opus)
  - **Defect.** The call reads the path from `user_project.sbsprj` each time; Designer reads that setting at its launch
    only (measured, step 1). After a change in Project settings, the Save writes the file Designer started with, with
    no backup, and the call reads, edits and loads the other. A failed Save (a read-only file) reads the user's old file
    as the base the same way.
  - **Scenario.** The user sets or clears a Default State File, then an agent's set-up shot runs before a restart: the
    shot comes out unchanged with no error, and the file Designer started with holds the session's state.
  - **Fix.** Refuse, putting back what was backed up, unless the Save rewrote `path` (its modification time moved, or it
    exists now when it didn't), saying that a changed Default State File takes a restart of Designer.
  - **Resolution: done**.
    - **Test:** `test_a_save_that_didnt_write_the_default_state_file_is_refused_and_nothing_loaded` (`tests/unit/test_view3d_helpers.py`), two cases (a
      file of the user's; none): it failed, on the user's file refused for its format, then on a FileNotFoundError.
      Live: a case of `check_the_users_default_state_file_is_followed` changing the setting while Designer runs: it
      failed on a FileNotFoundError, and passes: refused, nothing written where the new setting points, no backup left.
    - **Cause:** the call read the path at each call; Designer reads the setting at its launch only.
    - **Fix:** `_state_saved` refuses when the first Save left `path`'s modification time unchanged or left no file,
      saying a changed Default State File takes a restart of Designer; the put-back restores what was backed up. README
      says so, and that the refused shot's Save already wrote the session's state to the file Designer started with.
    - **Also covered:** the second Save, after a mesh switch, isn't checked: the first settled which file Designer
      writes, and a clock coarse to the second could show no new time.
  - Questioned by TST-927, HLP-274 (2026-11-26).

- [x] **HLP-269 · Claims in the set-up's code with no test** · `mcp_server/designer_helpers/scene3d.py:165-184,190-197,396-400` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** No test shows `_relinked`'s reason when the Explorer isn't visible and no `graph=` is given; the wait
    left out when nothing was relinked (`waiting.needed = not unlinked`); or `_directions`' "to 3 digits".
  - **Scenario.** One of them changes and nothing fails.
  - **Fix.** Three small assertions.
  - **Resolution: done**.
    - **Test:** `test_a_relink_with_the_explorer_hidden_is_said_to_follow_the_graph_no_longer`,
      `test_a_relink_that_didnt_run_isnt_waited_for` and `test_the_camera_said_gives_each_value_to_3_digits` (`tests/unit/test_view3d_helpers.py`),
      each failing on its mutation (the reason changed, `waiting.needed = True`, `%.4g`).

- [x] **HLP-270 · `Sequence[float]` for the set-up's known pairs** · `mcp_server/designer_helpers/scene3d.py:190,200` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** `_directions(values: Sequence[float], ...)` and `_camera_said(view, orbit: Sequence[float], pan:
    Sequence[float], zoom)` are called with `turn` and `move` only, `tuple[float, float]`; HLP-261 made `_camera_moved`
    take that pair for the same reason (`.claude/rules/python.md`). The bridge-facing `shoot_3d` and `_3d_set_up` keep
    `Sequence[float]` (HLP-188).
  - **Scenario.** A caller passes three numbers and no type check fails.
  - **Fix.** `tuple[float, float]` in both.
  - **Resolution: done**.
    - **Fix:** `_directions` and `_camera_said` take `tuple[float, float]`; mypy passes.

- [x] **HLP-271 · Comments and docstrings that name removed code or PLAN.md, or say more than the code now does** · listed below · confirmed · found 2026-11-26 by three reviewers (Sonnet)
  - **Defect.**
    - Naming `set_3d_view`: `tests/unit/test_view3d_helpers.py:1000`, `tests/unit/test_library_refusal.py:156`,
      `tests/unit/test_frames3d.py:581,701`.
    - Describing the removed drags, wheel notches or a step of several moves: `tests/unit/test_frames3d.py:202` (lists
      DRAG_PAUSE and WHEEL_PAUSE), `:433`, `:442-445`, `:537-538`, `:688-689`;
      `mcp_server/designer_helpers/frames3d.py:363` (`undrawn`'s evidence, "then a notch with no sign").
    - Citing PLAN.md, which the branch's last commit deletes: `tests/unit/test_view3d_helpers.py:1567,1596,1616,1722`.
    - `mcp_server/server_tools/views.py:241-242`: an error after the set-up leaves "the user's 3D view changed all the
      same"; now an error runs the put-back, and only an abort leaves it.
    - `tests/test_all_tools/editor_panels_and_fit/checks.py:737-745`: `NOTHING_AFTER`'s "after the shot's render"; the
      wrapper also runs at the camera's load.
    - `tests/test_all_tools/workers.py:7-9`: "about 8.7 minutes" (2026-11-23) beside the new editor and facts times,
      which together already pass it; the full run's time after the branch isn't measured.
  - **Scenario.** A reader looks for code that is gone, or takes a claim the code no longer makes.
  - **Fix.** Reword each to what exists, cite the dated instruction or ROADMAP item 131 instead of PLAN.md, or drop the
    line. ROADMAP.md's `set_3d_view` mentions are step 5's; DECISIONS.md's two entries are the user's.
  - **Resolution: done**.
    - **Fix:** each location reworded to what exists: the PLAN.md cites now name ROADMAP item 131 or the user's choice
      of 2026-11-26; `test_frames3d.py`'s scan lists no drag or wheel pause, its measurements are dated as taken with the
      wheel's zoom, and the test of several moves is renamed for what it guards; `undrawn`'s evidence, the
      `views.py` comment and `workers.py`'s minutes (dated before item 131, not measured since). `NOTHING_AFTER` was a
      real slip: it saved a render at the camera's load too; it now saves only from the second render on.
    - **Also covered:** ROADMAP.md (step 5) and DECISIONS.md (the user's) left as they are.
  - Questioned by HLP-275 (2026-11-26).
  - Questioned by TST-946 (2026-11-26).
  - Questioned by HLP-293 (2026-11-26).

- [x] **TST-921 · A mesh switched with a camera: the put-back loading the user's mesh is unpinned** · `tests/unit/test_view3d_helpers.py:1657-1681` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** `test_a_view_is_framed_for_the_mesh_it_shows[mesh=]` asserts `designer.loads[0]` only. The put-back
    loads `base` (the first Save, the user's mesh), not `working` (the second, the new mesh); `base` assigned again after
    the second Save passes every test.
  - **Scenario.** A `mesh=` shot with a camera option leaves the new mesh in the user's view.
  - **Fix.** `designer.loads[-1] == SAVED` in that test.
  - **Resolution: done**.
    - **Test:** `designer.loads[-1] == SAVED` in the framed-for-the-mesh test (`tests/unit/test_view3d_helpers.py`); the mutation the entry names fails
      it.
  - Questioned by TST-956 (2026-11-26).

- [x] **TST-922 · The fixed-time guard doesn't scan the set-up's new part** · `tests/unit/test_frames3d.py:196` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** `test_the_3d_shot_waits_on_the_view_not_a_fixed_time` scans `('shot3d', 'view3d', 'frames3d')`; the
    set-up's steps and waits moved into `scene3d.py`, which has none today.
  - **Scenario.** A fixed `_settle(0.5)` added there passes (`.claude/rules/waits.md`).
  - **Fix.** Add `'scene3d'`.
  - **Resolution: done**.
    - **Fix:** `'scene3d'` added to the scan; a `_settle(0.5)` there fails it.

- [x] **TST-923 · The refusal check's "nothing changed" clause can't fail** · `tests/test_all_tools/facts/checks.py:806` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** `'Reset Scene' not in t`: no line the call prints names the menu entry. A step prints `3D view,
    setting: <step>` before it changes anything.
  - **Scenario.** The refusal comes after a step began, the camera ends as it started, and the check passes against
    step 3's "refused before anything changes".
  - **Fix.** `SETTING not in t` (`3D view, setting`).
  - **Resolution: done**.
    - **Fix:** `'3D view, setting: ' not in t`. With the fields read after a step began, the check fails in a scratch
      run.

- [x] **TST-924 · The Default State File check doesn't judge its quit or its launch** · `tests/test_all_tools/lifecycle/checks.py:589-662` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** The quit is only registered with `watch.check(..., True, ...)`, where lifecycle's other quits go through
    `common.normal_close` (DECISIONS.md, Bridge and quitting: those are the ones counted); the relaunch's result isn't
    checked as its neighbours check theirs (`'Designer started in' in t and 'ERROR' not in t`). Also
    `os.makedirs(os.path.dirname(own))` at line 614 lacks `exist_ok=True`.
  - **Scenario.** A quit forced in shutdown, or a failed launch, shows only as a later "SAVED=" failure, uncounted.
  - **Fix.** Judge the quit with `normal_close` and the launch as its neighbours do; `exist_ok=True`.
  - **Resolution: done**.
    - **Fix:** the quit judged by `normal_close` in a check of its own, the relaunch as its neighbours judge theirs,
      `exist_ok=True`; all pass in a scratch run.

- [x] **TST-925 · The self-test's new pure helpers have no unit test** · `tests/test_all_tools/facts/state_camera.py:60,70`, `tests/test_all_tools/facts/state_file.py` (`backup`, `kept`), `tests/test_all_tools/facts/checks.py` (`kept_files`, `users_files`) · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** `state_camera.alike`, the pass criterion of four new checks, and `said`, `state_file.backup` and `kept`
    removing a shot's backup before and after (its docstring: "A backup a 3D shot left there is removed, before and
    after"), have no test in `tests/unit/test_selftest_state_file.py`.
  - **Scenario.** `alike`'s angle, distance or target tolerance is wrong and the four checks pass anything near.
  - **Fix.** Unit tests of `alike` (equal; a 0.02 degree yaw gap; a 2e-4 distance gap; a target gap), `backup` and the
    kept removal (`.claude/rules/unit-tests.md`).
  - **Resolution: done**.
    - **Test:** in `tests/unit/test_selftest_state_file.py`: `alike` (8 cases), `said`, `backup`, and `kept` removing a
      shot's backup before and after. A mutation of each of `alike`'s tolerances fails them.
  - Questioned by TST-928 (2026-11-26).

- [x] **HLP-273 · A camera at Back can decode as yaw -180, so `view='Back'` shown already still says it changed** · `mcp_server/designer_helpers/scene3d.py:274-282` · confirmed · follows HLP-265, generation 2 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** `_same_pose` compares `abs(a.yaw - b.yaw)` with no turn's wrap. `_framed(..., 'Back')` gives 180; a
    camera Designer saved at Back has X close to (-1, 0, ±1e-7), which `atan2(-X.z, X.x)` decodes as 180 or -180 by the
    noise's sign. The self-test's `angle_off` takes the wrap; `_same_pose` has no such test.
  - **Scenario.** The user's camera at the framed Back and `view='Back'`: a retake and HLP-265's false STALE line.
  - **Fix.** Compare `(a.yaw - b.yaw + 180) % 360 - 180`; a unit test of 180 against -180.
  - **Resolution: done**.
    - **Test:** `test_a_pose_at_back_is_one_whichever_side_of_the_turn_its_yaw_is` (-180, just past -180, just past
      180): the -180 cases failed. A scratch probe decoded Designer's framed Back on the Plane to yaw 179.999995 (once).
    - **Fix:** `_same_pose` compares `(a.yaw - b.yaw + 180) % 360 - 180`.
    - **Also covered:** `_same_pose` is the helpers' only comparison of yaws; the self-test's `angle_off` wraps already.
  - Questioned by HLP-279 (2026-11-26).

- [x] **TST-926 · The POSIX test of the Default State File's URL fails on Windows since HLP-266's fix** · `tests/unit/test_state3d.py:238-245` · confirmed · follows HLP-266, generation 2 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** `url2pathname` is `nturl2path`'s on Windows, so
    `test_the_users_default_state_file_is_the_one_their_project_settings_set` gets `\\a b\\R&D\\s.sbsscn` there for the
    `'/a b/R&D/s.sbsscn'` it asserts. `test_windows_simulation.py` sets `sys.platform`, not `os.name`, so it can't show it
    (`.claude/rules/unit-tests.md`).
  - **Scenario.** A unit run on Windows fails it (ROADMAP item 18).
  - **Fix.** Patch `url2pathname` to `urllib.parse.unquote` in that test, as the Windows test patches it to
    `nturl2path`'s.
  - **Resolution: done**.
    - **Test:** the POSIX test with `url2pathname` set to `nturl2path`'s, as on Windows (a scratch pytest plugin), failed
      on HEAD's test with `'\\a b\\R&D\\s.sbsscn'`.
    - **Fix:** the test patches `url2pathname` to `urllib.parse.unquote`, as its Windows sibling patches it to
      `nturl2path`'s; with the plugin it passes.

- [x] **TST-927 · The fake's Save relies on the clock moving the file's time** · `tests/unit/test_view3d_helpers.py` (the fake's Save; `users_default`), `mcp_server/designer_helpers/scene3d.py:130-142` · confirmed · follows HLP-268, generation 2 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** `_state_saved` refuses when the Save left the modification time unchanged. The unit tests write the
    file, then the fake's Save writes it again within milliseconds. Real use is safe: the put-back's `copy2` keeps the
    user's file's old time.
  - **Scenario.** On a file system whose times move in coarse steps (Windows' clock, about 15 ms), a test falsely meets
    "didn't write".
  - **Fix.** The fake's Save moves the time forward itself (`os.utime`).
  - **Resolution: done**.
    - **Test:** under a simulated coarse clock (a scratch plugin keeping a file's time as it is written), 9 tests of
      `tests/unit/test_view3d_helpers.py` failed on "didn't write".
    - **Fix:** the fake's Save sets the file's time 1 s past what it had (`os.utime`); under that clock all pass.

- [x] **HLP-274 · The refusal of a Save that wrote another file doesn't say what that Save did** · `mcp_server/designer_helpers/scene3d.py:137-141` · confirmed · follows HLP-268, generation 2 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** By the refusal, Designer's Save has written the session's state over the Default State File it started
    with, with no backup (its path isn't known). README says so; the error an agent relays says only that a changed
    Default State File takes a restart of Designer.
  - **Scenario.** The user's start view in that file is lost, and the refusal they read doesn't tell them.
  - **Fix.** A clause in the message: the file Designer started with now holds the session's state.
  - **Resolution: done**.
    - **Test:** HLP-268's unit test expects "The file Designer started with now holds the session's state": it failed.
    - **Fix:** the clause is in the refusal; the lifecycle check asserts it live too.

- [x] **HLP-275 · HLP-271's rewording left a comment saying the opposite of the code, and README's minutes** · `mcp_server/server_tools/views.py:241-242`, `README.md:202` · confirmed · follows HLP-271, generation 2 · found 2026-11-26 by two reviewers (Sonnet)
  - **Defect.** The comment reads "what was set, then, but after an abort, that the view was put back": after an error
    the put-back says the view was put back; after an abort nothing is put back and only the steps begun show. README
    still gives "about 8.7 minutes for both, four Designers side by side (2026-11-23)", which `workers.py` now dates
    before item 131; README's own editor row (about 6 minutes) and facts' 188 s, never run at once, pass it.
  - **Scenario.** A reader takes an abort as putting the view back, or the run's length as measured.
  - **Fix.** The comment as the code does it (an error says what was set, then that the view was put back; an abort
    says the steps begun and leaves the view); README worded as `workers.py`.
  - **Resolution: done**.
    - **Fix:** `views.py`'s comment says what the code does (an error: what was set, then that the view was put back;
      an abort: the steps begun, the view left as they set it); README's minutes dated as `workers.py`'s.

- [x] **TST-928 · A test's changes typed `dict[str, object]`** · `tests/unit/test_selftest_state_file.py` (`test_two_poses_are_alike_...`) · confirmed · follows TST-925, generation 2 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** `change: dict[str, object]` where the values are `float` or `tuple[float, float, float]`
    (`.claude/rules/python.md`).
  - **Scenario.** A wrong value type passes mypy.
  - **Fix.** `dict[str, float | tuple[float, float, float]]`.
  - **Resolution: done**.
    - **Fix:** `dict[str, float | tuple[float, float, float]]`; mypy passes.

- [x] **HLP-276 · The Materials menu, read by every set-up now, isn't among the menus checked first** · `mcp_server/designer_helpers/scene3d.py:360-367` · confirmed · follows HLP-267, generation 2 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** `_overrides` reads Materials after the backup and the Save; `needed`, the menus refused before anything
    changes, lacks `('Materials',)`.
  - **Scenario.** A 3D view without that menu is refused after the Save, not before (the put-back restores the file).
  - **Fix.** `('Materials',)` in `needed` for every set-up.
  - **Resolution: done**.
    - **Test:** `test_the_materials_menu_every_set_up_reads_is_looked_up_before_anything_changes` (`tests/unit/test_view3d_helpers.py`): it failed.
    - **Fix:** `('Materials',)` in `needed` for every set-up; the tiling branch adds only the shown mesh's 'Edit
      properties' path.
    - **Also covered:** the other menus read after the Save: the AOV button (missing, it refuses nothing) and tiling's
      material after a mesh switch, read later by design (HLP-114).

- [x] **TST-929 · The editor checks still load `state3d`, which they no longer use** · `tests/test_all_tools/editor_panels_and_fit/checks.py:10,14,72-75` · confirmed · follows TST-919, generation 2 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** TST-919's fix replaced every use of `state3d.` in the file; the `TYPE_CHECKING` block, `import
    designer_helpers` and `TYPE_CHECKING` itself are left, and the module still runs `standalone('state3d')` at import.
  - **Scenario.** A reader looks for what the checks take from the part.
  - **Fix.** Delete the lines.
  - **Resolution: done**.
    - **Fix:** the `TYPE_CHECKING` block, `import designer_helpers` and `TYPE_CHECKING` deleted.

- [x] **TST-930 · The facts docstring says a Designer just started shows no Override Material entry; no check shows it** · `tests/test_all_tools/facts/state_file.py:32-34` · confirmed · follows HLP-267, generation 2 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** "a Designer just started, no graph opened, shows none" is under what the checks re-measure. The facts
    check opens `STATE_GRAPH` first; with no graph opened the 3D view isn't built at all (lifecycle's
    `check_the_3d_view_waits_for_a_graph`), so there is no Materials menu to show none.
  - **Scenario.** A reader takes the case as checked.
  - **Fix.** Narrow it to what the check shows, or move the case measured to "Measured, not checked", named as it was
    (a graph open with no outputs on the mesh).
  - **Resolution: done**.
    - **Fix:** generation 2, the claim narrowed to what the check shows (a load turns the entry on, a graph's outputs on
      the mesh); the case measured moved to "Measured, not checked" as it was (a graph open in a Designer just started,
      the mesh's material holding no such entry, once). No check added.
  - Questioned by HLP-278 (2026-11-26).

- [x] **HLP-277 · The docstrings say a failed look before the put-back is said; a put-back failing after it drops it** · `mcp_server/designer_helpers/scene3d.py:20-23,410-427` · confirmed · follows HLP-272, generation 3 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** The module's and `put_back`'s docstrings say "a failure of it said". The failure is kept in `looked` and
    printed only on "put back as it was": when `loading(base)()` or the relink then raises, the call's error carries the
    load's failure alone.
  - **Scenario.** A window that keeps going off screen and a load that fails: the off-screen cause isn't said. The base
    load still ran, and the backup is put back.
  - **Fix.** Generation 3, the claim narrowed: the look's failure is said on the put-back's own line. No check added.
  - **Resolution: done**.
    - **Fix:** generation 3, the claim narrowed: the module's and `put_back`'s docstrings say a failure of the look is
      said on the put-back's own line.

- [x] **HLP-278 · `_overrides`' docstring states as a rule a case seen once** · `mcp_server/designer_helpers/scene3d.py` (`_overrides`) · confirmed · follows TST-930, generation 3 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** "none before a graph's outputs are on the mesh": TST-930's fix moved that case to "Measured, not checked"
    (seen once, 2026-11-26) in the facts docstring; the code works either way (no entries, nothing to set back).
  - **Scenario.** A reader takes the case as checked.
  - **Fix.** Generation 3, the claim narrowed: "none seen before ...".
  - **Resolution: done**.
    - **Fix:** generation 3, the claim narrowed: "none seen before a graph's outputs were on the mesh".

- [x] **HLP-279 · `VIEW_DIRECTIONS`' comment says the yaws are as `_camera_pose` decodes them; Back may decode as -180** · `mcp_server/designer_helpers/state3d.py:75` · confirmed · follows HLP-273, generation 3 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** "(yaw, pitch) as _camera_pose decodes it": HLP-273's finding is that a camera at Back decodes as 180 or
    -180 by the noise's sign.
  - **Scenario.** A reader compares a decoded Back with 180 and no wrap.
  - **Fix.** Generation 3, the claim narrowed: "up to the turn's wrap at Back", or the clause dropped.
  - **Resolution: done**.
    - **Fix:** generation 3, the claim narrowed: each view "as _camera_pose decodes it up to the turn's wrap at Back
      (180 or -180)".

- [x] **SRV-278 · Comments that still say the values are set in Designer's fields, or send the limits to state3d.py** · `mcp_server/server_tools/views.py:32-33,195`, `tests/unit/test_view3d.py:133`, `tests/unit/test_shot3d.py:1123` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** "values Designer's fields are set to, 0 included" (three places): nothing is set in a field since step 4,
    the values are written in the state file. "the tool's own limits (the state file's: designer_helpers/state3d.py)":
    state3d.py holds no ±180 or ±10 limit.
  - **Scenario.** A reader looks for the field, or for the limits in state3d.py.
  - **Fix.** "values written in the state file, 0 included"; "the tool's own limits (units: designer_helpers/state3d.py)".
  - **Resolution: done**.
    - **Fix:** "values written in the state file, 0 included", in `views.py`, `test_view3d.py` and `test_shot3d.py`; the
      limits' comment points to their units in `state3d.py`. A grep finds none of the old wordings.

- [x] **HLP-281 · `view3d.py` keeps a clause whose check went with step 4** · `mcp_server/designer_helpers/view3d.py:12-14` · confirmed · follows TST-315, generation 2 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** "and opening that graph again doesn't apply them either": the removed
    `check_opening_the_editors_graph_again_leaves_the_outputs_on_the_mesh` was its pin (TST-315), for `_set_tiling`'s
    turn-back, which is gone; no tool reopens a graph.
  - **Scenario.** A reader takes the clause as checked.
  - **Fix.** Drop it.
  - **Resolution: done**.
    - **Fix:** the clause dropped from `view3d.py`'s docstring; no other copy.

- [x] **TST-931 · The environment's clean-up check asserts nothing, and the fact it stood on isn't measured any more** · `tests/test_all_tools/editor_panels_and_fit/checks.py:591-604,636,1854` · confirmed · follows TST-545, generation 3 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** `check_the_environment_is_reset` passes whenever its snippet prints `ENVIRONMENT_RESET`. TST-545 pinned
    "Reset Environment puts rotation and exposure back to 0 and changes the map" in the removed
    `check_the_environment_is_set_as_measured`. Each shot now loads the user's base back, which the facts put-back check
    compares field by field; the reset after would hide a light the put-back left changed.
  - **Scenario.** None for a user: a PASS line that guards nothing.
  - **Fix.** Generation 3, the claim narrowed: the check and its two calls removed, with "The environment is reset
    after, whatever failed" in the two docstrings; kept as a clean-up, it runs with no `check()`.
  - **Resolution: done**.
    - **Fix:** generation 3, the claim narrowed: `RESET_ENVIRONMENT` and `check_the_environment_is_reset` removed with
      their two calls, and the docstrings' "The environment is reset after, whatever failed". No check added.

- [x] **TST-932 · No live check that a shot setting the light renders the view once it settled** · the removed `check_a_3d_shot_setting_the_whole_environment_waits_for_its_last_change` (`NOTHING_AFTER`), `tests/test_all_tools/editor_panels_and_fit/checks.py` · confirmed · follows HLP-192, generation 2 · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** HLP-192's live guard went with the panel route; the behaviour stays (one load, one `settled` wait).
    Nothing compares the shot's render with the view settled: `_resting` is used nowhere in `tests/` now, and the other
    environment checks need 3 to 5 grey levels where HLP-192's failure showed 1.2 to 1.8.
  - **Scenario.** A map's texture load restarts the view's accumulation after the first count back at rest: the render
    is taken mid-refinement, said set, with no STALE line, and no check fails.
  - **Fix.** The check back through the file: the shot's render against the view settled after the load
    (`watched.until(watched._resting, SETTLE_LIMIT)`), for `mesh='Sphere', view='Front'` with a map, a rotation and an
    exposure; seen live.
  - **Resolution: done**.
    - **Test:** `check_a_3d_shot_setting_the_light_renders_the_view_once_it_settled` (new), through the file: the view
      saved once settled just before the put-back's load, against the shot's render, for `mesh='Sphere', view='Front'`
      with a map, rotation 90 and exposure 2. Live: 0.000 grey levels apart; with `_Frames.settled` returning at once,
      0.497, which passed a 0.5 limit, so the limit is 0.1: the simulated defect fails it, the real run passes.

- [x] **TST-933 · Five mesh ids `mesh=` writes are pinned by no check, and two sentences say all are** · `tests/test_all_tools/facts/checks.py:512-561,720`, `tests/test_all_tools/facts/state_file.py:21-23` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** The switch check picks 6 of the 11 meshes; Cube, Plane (hi-res), Rounded cube, Rounded cylinder and
    Sphere 2 tiles are measured only. The Frame check builds its expectation from `FRAMING[mesh][0]` itself, so it can't
    see a wrong id. The docstrings say each mesh's id is held as the table has it.
  - **Scenario.** One wrong id makes `mesh='Cube'` load a missing mesh, and no check fails.
  - **Fix.** In `check_designers_frame_gives_the_view_tables_poses`, which picks and saves all 11, also require the
    saved file's mesh id to be `FRAMING[mesh][0]`.
  - **Resolution: done**.
    - **Test:** `check_designers_frame_gives_the_view_tables_poses` requires each of the 11 meshes' saved id to be
      `FRAMING[mesh][0]`; a wrong id expected failed both its framing results. The docstrings say each mesh picked is
      held by the table's id.

- [x] **TST-934 · Two refusal checks can't tell "refused first" from "set, then put back"** · `tests/test_all_tools/editor_panels_and_fit/checks.py:476-480,577-585` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** The Explorer refusal passes on `changed < 2`, which the put-back after any error also gives; the tiling
    refusal on a substring the error keeps when it comes after a step ("...; the 3D view was already set: ..."). The
    claim is "checked before anything changes" (HLP-107, HLP-127). TST-923 fixed the same pattern elsewhere.
  - **Scenario.** The Explorer or the tiling read after the load: a visible glide and a put-back, and both pass.
  - **Fix.** `'3D view, setting: ' not in` each refusal's text.
  - **Resolution: done**.
    - **Test:** the Explorer refusal asserts no step began (`SET_UP_STEP not in hidden`); with the refusal simulated
      after the load, the old assertions passed and the new one failed. The tiling refusal it named is gone with
      HLP-280; the several-materials refusal before any change is unit-tested (`triggered() == []`).

- [x] **TST-935 · A user decision and two docs say the node selection is kept after the relink; no check shows it** · `DECISIONS.md:268-269`, `ROADMAP.md:115`, `tests/test_all_tools/editor_panels_and_fit/checks.py:601` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** The reworded Parameters panel entry adds "and the node selection itself is kept", which the user's
    approved wording didn't hold and no check measures (the relink's measurements of 2026-11-25 saw it, unpinned). Item
    89 says the tiling and the environment "no longer turn the panel", and a check's docstring "the Parameters panel left
    as it was", where the set-up's relink turns it.
  - **Scenario.** A reader takes an unmeasured fact as part of the user's decision, or the panel as untouched.
  - **Fix.** The clause dropped from the entry, which is then the user's wording; item 89 and the docstring narrowed to
    what the code does.
  - **Resolution: done**.
    - **Fix:** ", and the node selection itself is kept" dropped from the entry, now the user's wording plus names;
      item 89 says the tiling and the environment go through the file and the relink turns the panel to the graph; the
      check's docstring loses "the Parameters panel left as it was" (it reads no panel).

- [x] **TST-936 · Item 131's Why and Approach disagree on the Displacement toggle** · `ROADMAP.md:105` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** The Why lists "the Displacement toggle" among what the file doesn't hold; the Approach (and the facts
    check, `rs-adobe_displacementenabled`) say the file holds one, which a load keeps as the session had it.
  - **Scenario.** A reader takes the toggle as missing from the file.
  - **Fix.** "(it holds one, which a load keeps: below)" in the Why (`.claude/rules/docs.md`: fix a note found wrong).
  - **Resolution: done**.
    - **Fix:** "the Displacement toggle (the file holds one, but a load keeps the session's: below)".

- [x] **TST-937 · Items 87 and 88 still call a value the file holds a set-up step** · `ROADMAP.md:114,136,140` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** The rewritten rules keep "step" for what the file doesn't hold; item 88 ("The pick is a set-up step")
    and 87 ("set-up steps") say so of the shader model and the toggles, which their own Notes say the file holds; item 82
    mixes both.
  - **Scenario.** A later builder of 87 or 88 gets two instructions.
  - **Fix.** "a field of the state file (the Note)", as items 75 and 84 now say.
  - **Resolution: done**.
    - **Fix:** items 82, 87 and 88 call those values fields of the state file (the Note), under the rules above; 87
      loses "set from code as the Displacement button would be" (that button isn't applied by a load).
  - Questioned by TST-957 (2026-11-26).

- [x] **TST-938 · Done item 112 still describes the wheel rule item 131 removed, and cites DECISIONS.md for it** · `ROADMAP.md:31` · confirmed · found 2026-11-26 by a reviewer (Sonnet)
  - **Defect.** "The 3D shot sends each wheel notch only from a view at rest ... (`designer_helpers/frames3d.py`,
    `view3d.py`; DECISIONS.md)": no wheel notch is sent since item 131, the entry was removed on the user's word, and the
    row's check is gone.
  - **Scenario.** A reader looks for the rule and its decision.
  - **Fix.** "(item 131 removed the wheel steps, 2026-11-26; `designer_helpers/view3d.py` at 73ead3a)", the bare
    DECISIONS.md pointer dropped.
  - **Resolution: done**.
    - **Fix:** "(item 131 removed the wheel steps, 2026-11-26; `designer_helpers/view3d.py` at 73ead3a)", the bare
      DECISIONS.md pointer dropped, the sentence in the past tense.

- [x] **TST-941 · The AOV set back and the relink after a set-up shot are read by no live check** · `mcp_server/designer_helpers/scene3d.py:186-200`, `tests/test_all_tools/facts/checks.py:860-922`, `tests/test_all_tools/editor_panels_and_fit/checks.py` (the user's-own-view check) · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `_aov_back` is reached by the unit test only, with the menu faked; no live shot starts from an AOV other
    than Beauty. No check reads whether the view follows the graph again: the facts put-back check's base isn't linked,
    and the editor checks match "put back as it was" as a substring. A runner's probe (2026-11-26) saw both work: the
    AOV came back as Material roughness, and a Save after the shot wrote the graph's textures, two runs of two.
  - **Scenario.** A change breaks either, and every live check passes.
  - **Fix.** The AOV set to Material roughness before the facts put-back check's shot and read after; in the
    user's-own-view check, no "no longer follows" in the reply and a Save writing the textures; each seen failing with
    its code stubbed.
  - **Resolution: done**.
    - **Test:** the facts put-back check sets Material roughness and reads the AOV after the shot; the user's-own-view
      check requires no "no longer follows" and a Save writing the editor's graph's textures. With `_aov_back` and
      `_relinked` stubbed they failed ("after the shot ['Beauty']", "textures ... ['None']"); on the code they pass.
  - Note (2026-11-26, round 13): its docstring's "no reply says otherwise" reads only the moves' replies, not
    the framed shots'; "no move's reply" says what it checks.

- [x] **TST-942 · The abort check aborts before anything has changed, though it says after a change** · `tests/test_all_tools/editor_panels_and_fit/checks.py:450-456,462-463,493-501` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `ABORTED` asks for `'Plane'`, which the user's view shows by then (set by the user's-own-view check, put
    back by every shot since), so nothing is to load and the abort lands before any change. In main, `set_3d_view` had
    left a Sphere.
  - **Scenario.** The abort after a real load, which the check names (HLP-113), runs nowhere live.
  - **Fix.** `'Sphere'` in `ABORTED` and its assertion.
  - **Resolution: done**.
    - **Fix:** `ABORTED` and its assertion use Sphere, a mesh the view doesn't show, so the abort lands after a load.

- [x] **TST-943 · The fact `_state_load` stands on, no mesh checked as Reset Scene's trigger returns, isn't pinned at the return** · `tests/test_all_tools/facts/state_file.py:14-15,369`, `mcp_server/designer_helpers/scene3d.py:165` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** The facts check waits until the menu clears within its limit; the code reads `during` right at the
    trigger's return. A Designer that cleared it a moment later passes the check, and every load keeping its mesh would
    wait its 3 s.
  - **Scenario.** A Designer update changes the moment; the check passes and the shots slow down, said unsettled.
  - **Fix.** One read with no wait right after the trigger, required empty.
  - **Resolution: done**.
    - **Test:** `test_the_entries_check_reads_the_scene_menu_right_as_the_trigger_returns` failed.
    - **Fix:** the entries check reads `LOAD_BEGAN` once, right after the trigger; it passes live.
  - Questioned by TST-958 (2026-11-26).

- [x] **HLP-284 · state3d.py says the checks pin the orbit over the pole; none does since the drags went** · `mcp_server/designer_helpers/state3d.py:8-9,31-35,39-42` · confirmed · follows TST-905, generation 3 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** The docstring says its facts are pinned by the facts and editor checks, the pitch "over the pole too"
    and the yaw's turn there among them. The facts moves check went with the drags; the editor's orbits stop at Top.
    `orbit`'s up is refused beyond ±90, so a pose over the pole comes only from a camera already upside down; a runner's
    probe (2026-11-26) found the turns from one right (1.9 and 2.5 grey levels apart rolled 180, 13 for the wrong way).
  - **Scenario.** A reader takes the pole as checked.
  - **Fix.** Generation 3, the claim narrowed: the editor checks pin the orbit up to the pole; a camera over it, and the
    yaw's flip there, were measured against the drags (2026-11-25) and once more by probe.
  - **Resolution: done**.
    - **Fix:** generation 3, the claim narrowed: the editor checks pin the orbit up to the pole; a camera over it and
      the yaw's turn there were measured against the drags (2026-11-25) and by probe (2026-11-26), not checked.

- [x] **TST-944 · Off macOS, the values-shown check backs the user's file up where no later shot finds it** · `tests/test_all_tools/editor_panels_and_fit/checks.py:733-739` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `aside = os.path.join(folder, 'aside')`, a scratch folder, where off macOS the path is the user's real
    file; the next shot looks for a leftover at `STATE_BACKUP` only.
  - **Scenario.** A crash between that check's Save and its put-back leaves the session's state as the user's default,
    and no later shot puts theirs back, against README's promise.
  - **Fix.** The aside at `os.path.join(_version_folder(), STATE_BACKUP)`.
  - **Resolution: done**.
    - **Test:** `test_the_shown_already_check_backs_the_users_file_up_where_a_shot_finds_a_leftover` failed
      (`/folder/aside`).
    - **Fix:** the check backs the file up at `_version_folder()/STATE_BACKUP`, as `SAVED_TEXTURES` does.

- [x] **TST-945 · A `cast` hides a None in the facts' UID check** · `tests/test_all_tools/facts/checks.py:349` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `cast(re.Match[str], re.search(...)).group(1)`: a file with no `fileUID` raises AttributeError, ending
    `facts.run` before the state file checks.
  - **Scenario.** A failing run loses the checks after it.
  - **Fix.** Check the match and fail the check with the file's tail (`.claude/rules/python.md`).
  - **Resolution: done**.
    - **Test:** `test_a_package_file_with_no_uid_is_read_as_none` failed.
    - **Fix:** `_file_uid` returns None for no `<fileUID>`; the check fails on it and `facts.run` goes on.
    - **Also covered:** the other `cast(re.Match[str], ...)` read the repository's own sources or are guarded.

- [x] **TST-946 · Unit-test fakes and a comment still give output the branch removed** · `tests/unit/test_view3d.py:17,276`, `tests/unit/test_selftest_check_setups.py:270,287-288` · confirmed · follows HLP-271, generation 2 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `NOTE` ends "(the Parameters panel back on g)", and `STEPS` gives two setting lines where one covers the
    file's fields; the comment at :276 says the user's view "was changed all the same" after an error, which now runs
    the put-back; the Rasterizer fakes reply with the panel suffix `rasterizer.py` no longer prints.
  - **Scenario.** A reader takes the fakes as the helpers' output.
  - **Fix.** The suffix dropped, the steps as the helpers print them, the comment as the code does it.
  - **Resolution: done**.
    - **Fix:** `NOTE` and `STEPS` as the helpers print them, the comment saying the view is put back, the Rasterizer fakes
      without the panel suffix.

- [x] **SRV-279 · `zoom`'s description leaves out a new mesh's framing as its start** · `mcp_server/server_tools/views.py:120` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** "from view's framing or else the user's view": with `mesh=` (not shown yet) and no `view`, the zoom
    starts from the new mesh's framing, from the camera's direction (`_reframed`).
  - **Scenario.** An agent expects `mesh='Sphere', zoom=3` to come closer from its own camera.
  - **Fix.** "from view's framing, a new mesh's framing, or else the user's view", within `CLAUDE_CODE_LIMIT`.
  - **Resolution: done**.
    - **Fix:** "from view's framing, a new mesh's framing, or else the user's view"; the description limit holds.

- [x] **HLP-285 · frames3d.py says the Rasterizer check's steps say nothing; the check takes either** · `mcp_server/designer_helpers/frames3d.py:69-70` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** "its steps say nothing, and the render's line says the count": the check accepts the count said of a
    step or of the render, and its unit test has both.
  - **Scenario.** A reader takes the steps' silence as checked.
  - **Fix.** "... measures a zoom then, its count said of a step or of the render".
  - **Resolution: done**.
    - **Fix:** "... measures a zoom then, its count said of a step or of the render".

- [x] **TST-947 · README says the next shot puts the user's file back; only one that sets the view up does** · `README.md:417` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** A shot without set-up options saves and loads nothing, so it puts no leftover back.
  - **Scenario.** A user takes a plain 3D screenshot as putting their file back.
  - **Fix.** "the next shot that sets the view up puts yours back first".
  - **Resolution: done**.
    - **Fix:** "the next shot that sets the view up puts yours back first".

- [x] **TST-948 · The unit case "the mesh shown" can't tell the mesh shown from the cube it falls back to** · `tests/unit/test_view3d_helpers.py:1384-1393` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** The fixture's `Rounded Cube` isn't a `FRAMING` key, so it frames as the cube anyway;
    `shown = asked.get('mesh', 'cube')` passes every unit test.
  - **Scenario.** The case claims what it can't see (the live user's-own-view check would).
  - **Fix.** A row with the file holding `plane`, expecting `_framed('plane', 'Top', ...)`.
  - **Resolution: done**.
    - **Test:** a row of `test_a_view_is_framed_for_the_mesh_it_shows` with the file holding `plane`; with
      `shown = asked.get('mesh', 'cube')` it alone failed.

- [x] **HLP-287 · Every load now reads the file's mesh, after writing it, and refuses a file with none** · `mcp_server/designer_helpers/scene3d.py:425-426` · confirmed · follows HLP-283, generation 2 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `listed = not _state_fields(content, ['mesh'])['mesh'].startswith(USERS_MESH)` runs after
    `_state_write`, and `_state_fields` raises unless the file holds one mesh id. `reads` holds `mesh` only with a camera
    option or `mesh=`, so a call setting only the light used to pass a base with no mesh id.
  - **Scenario.** Such a call is refused after its step was said and the file written, with "...; and putting the 3D view
    back failed: ...", though the view never changed (rare: a scene saved with no mesh id).
  - **Fix.** `listed` derived without raising, before the write (a missing id counted as listed).
  - **Resolution: done**.
    - **Test:** `test_a_light_set_in_a_file_with_no_mesh_id_is_loaded_as_one_of_a_listed_mesh` raised before the fix.
    - **Fix:** `state3d._mesh_listed` raises nothing, a file with no single mesh id counting as listed; `loading` reads
      it before the write.

- [x] **HLP-288 · The no-outputs suffix names the graph in the editor as the one no longer followed** · `mcp_server/designer_helpers/scene3d.py:245-248`, `tests/test_all_tools/editor_panels_and_fit/checks.py:391` · confirmed · follows HLP-282, generation 2 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** "(it no longer follows graph B, which has no outputs to show)": the view never followed B; it followed the
    graph it showed. The tool's docstring now has the agent pass this line to the user.
  - **Scenario.** The user is told their view no longer follows the empty graph they just opened.
  - **Fix.** Worded like the no-graph case: "(it no longer follows the graph it showed: graph B in the editor has no
    outputs to show)", the unit case and the live check's string with it.
  - **Resolution: done**.
    - **Test:** the `no outputs` case and the live check's string; then the one-output, hidden-Explorer and failure
      branches' strings, each seen failing.
    - **Fix:** `_relinked` says " (it no longer follows the graph it showed: ...)", each branch giving its reason about
      the editor's graph ("graph B in the editor has no outputs to show").
    - **Also covered:** every branch had the same misstatement; all four reworded.
  - Questioned by HLP-290 (2026-11-26).

- [x] **TST-949 · The unit test of a user's mesh can't tell the written file's mesh from the base's** · `tests/unit/test_view3d_helpers.py:1525-1536` · confirmed · follows HLP-283, generation 2 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** The base and the edited file both hold the `file://` mesh, so code reading `listed` from the base passes,
    where HLP-283's resolution says `loading` reads the written file's.
  - **Scenario.** A change reading the base waits wrongly on `mesh='Sphere'` from a user's mesh, and no test fails.
  - **Fix.** A case with the base holding the `file://` mesh and `mesh='Sphere'`: the set-up's load waits on the menu,
    the put-back's doesn't.
  - **Resolution: done**.
    - **Test:** `test_each_load_waits_as_the_mesh_of_the_file_it_loads_says`: the base a user's mesh, `mesh='Sphere'`;
      `listed` read from the base fails it alone.

- [x] **HLP-289 · The docstrings say a user's mesh's first restart stands for its load's end, measured with one small mesh; antialiasing off goes unsaid** · `mcp_server/designer_helpers/scene3d.py:32-34,167-168,176-178`, `mcp_server/designer_helpers/frames3d.py:141,318-324` · confirmed · follows HLP-286, generation 3 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** "the load's own restart of the view, up to SETTLE_LIMIT, stands for its end" rests on `box.fbx`, which
    loads in under a second; a load restarts the view as the scene resets and the camera glides, which a slower import
    may outlast. With the Rasterizer's accumulation antialiasing off, no paint reads as a restart (HLP-216), so such a
    load waits its 3 s limit and says the view hadn't settled. HLP-286's Also covered names only the no-count case.
  - **Scenario.** A reader takes a slow mesh of the user's own as covered.
  - **Fix.** Generation 3, the claims narrowed: what `box.fbx` showed, a slower import and antialiasing off named as not
    measured and not covered (the user called custom meshes very unlikely, 2026-11-25; a signal of the import's end
    would be needed: not worth a fix).
  - **Resolution: done**.
    - **Fix:** generation 3, the claims narrowed: scene3d.py's module docstring says what `box.fbx` showed (under a
      second, its own restart then the view settled ending its load), and names a slower import and accumulation
      antialiasing off as neither measured nor covered, a signal of the import's end being needed; the antialiasing
      mechanism stays in frames3d.py's HLP-216/217 bullet, which names `restarted`.

- [x] **HLP-290 · The one-output suffix still says opening another graph, then the editor's, shows it again** · `mcp_server/designer_helpers/scene3d.py:252-256`, `tests/unit/test_view3d_helpers.py:1468-1469`, `README.md:422-423` · confirmed · follows HLP-288, generation 3 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** After HLP-288's rewording, "it" reads as the graph the view showed, while the advice shows the editor's
    graph; and the advice is untested for a graph with one output (the facts check of "another graph, then it" uses a
    graph with two, on purpose: `facts/preparations.py:15`).
  - **Scenario.** The agent passes the advice on; the user follows it and gets another graph, or a channel prompt.
  - **Fix.** Generation 3, the claim narrowed: the sentence dropped, with the unit string and README's "open another
    graph, then that one".
  - **Resolution: done**.
    - **Test:** the `one output` unit string, changed first, failed on the old code.
    - **Fix:** generation 3, the claim narrowed: the advice dropped from `_relinked`'s one-output branch and from
      README. No live check pins the string.

- [x] **TST-950 · The frames fake's event kinds are typed `str`** · `tests/unit/test_frames3d.py:323,596` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `coming: Sequence[tuple[str, int | None]]` where the kind is one of `'Paint'`, `'UpdateRequest'`, `'Off'`
    or `'Wait'`; `_Frames._event` counts any kind but `'UpdateRequest'` as a paint, so a typo becomes a paint.
  - **Scenario.** `('wait', 2)` passes as a paint, and the test still passes.
  - **Fix.** A `Literal` alias for the kinds (`.claude/rules/python.md`).
  - **Resolution: done**.
    - **Test:** a `('wait', 2)` typo passed mypy before the alias and is refused after it.
    - **Fix:** an `Event` alias (`Literal['Paint', 'UpdateRequest', 'Off', 'Wait']`) types the fake and its rows; the
      fake's `until` asserts a paint's kind, since mypy doesn't check parametrize rows.
  - Questioned by TST-952 (2026-11-26).

- [x] **HLP-292 · The relink's wait after a load, and the AOV and Override Material waits, drop whether the view settled** · `mcp_server/designer_helpers/scene3d.py:208-215,238-246,504-508` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `with _Waiting(watched) as waiting: unlinked = _relinked(...)` and nothing reads `waiting.settled`, where
    the `graph=` step says `_unsettled(waiting.settled, watched)` (HLP-214's pattern, on every step).
  - **Scenario.** A linked view with a camera option: the relink restarts the view and doesn't settle within 3 s; the
    render may be mid-accumulation and the reply says nothing, against the tool's "said after a step".
  - **Fix.** `_unsettled` on the relink's step, said once; the AOV and Override waits folded in the same way, or left as
    rarer; a unit case where the load settles and the relink doesn't.
  - **Resolution: done**.
    - **Test:** `test_a_relink_that_didnt_settle_is_said_once` (the relink alone; the load too) and
      `test_a_view_that_didnt_settle_after_the_aov_set_back_is_said` (`tests/unit/test_view3d_helpers.py`), each failing first.
    - **Fix:** the relink's step says it hadn't settled once, when the load's own wait had; `_aov_back` and
      `_overrides_back` return whether their waits settled, folded into the load's.
    - **Also covered:** the put-back's relink isn't waited for: nothing renders after it.
  - Questioned by TST-954 (2026-11-26).
  - Note (2026-11-26, round 16): the case "the load too" passes on the code before the fix too (the load's line said
    it once already); it guards the warning said once. "The relink alone" and the AOV test are the ones that failed first.

- [x] **HLP-293 · Docstrings that say other than the code or the measurement** · `mcp_server/designer_helpers/shot3d.py:348,384-385,394`, `mcp_server/designer_helpers/frames3d.py:42-44,431-432` · confirmed · follows HLP-271, generation 2 · found 2026-11-26 by two reviewers (Opus)
  - **Defect.** `shoot_3d` says the render is saved "then the view put back", and its waits watched "until the render";
    the put-back comes first and waits on the same frames, and a failed put-back leaves the render unsaved. `_Waiting`
    says "A step of the 3D view's set-up waits this way (view3d.py)": the steps are in `scene3d.py`. frames3d.py says
    "1 of 60 pans", where HLP-164 measured 60 moves, wheel notches and drags in turn.
  - **Scenario.** A maintainer closes the watch at the render, or reads the measurement as of pans.
  - **Fix.** Each said as the code does it and as HLP-164 measured.
  - **Resolution: done**.
    - **Fix:** `_on_screen` and `shoot_3d` say the view is set up, rendered, then put back, the render saved after the
      put-back and the waits watched until it; `_Waiting` points at scene3d.py; frames3d.py says "Of 60 moves, wheel notches
      and drags in turn, ... in 1, the first", from HLP-164 in git history.

- [x] **SRV-280 · The tool's docstring and README don't say that a set-up shot's relink selects the editor's graph in the Explorer and turns the Parameters panel to it** · `mcp_server/server_tools/views.py:176-179`, `README.md:421-422` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** Main said the panel then shows the graph (`tiling`'s description); step 4 removed it, while the relink
    after each load now does it whenever the view follows a graph, and expands a collapsed package (view3d.py's docstring;
    GUIDE, Designer UI; DECISIONS.md, the Parameters panel entry).
  - **Scenario.** The user's Explorer selection and panel change after a zoom, and neither the agent nor the user was
    told.
  - **Fix.** One clause in the docstring and in README's 3D bullet.
  - **Resolution: done**.
    - **Fix:** the tool's docstring and README's 3D bullet say that a view which showed a graph's outputs gets the
      editor's graph's back after each load, through the Explorer, which selects it there, expanding its package, and turns
      the Parameters panel to it (checked against `_apply_outputs` and DECISIONS.md's Parameters panel entry).

- [x] **TST-951 · The frames check's second reading starts with the camera at Front, where Camera > Front redraws nothing** · `tests/test_all_tools/editor_panels_and_fit/checks.py:967,1073-1074` · measured · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** In main each pass set up Top first; now a plain shot changes nothing, and `FRAMES` ends at Front.
    Measured (a runner's probe, 2026-11-26): a first run passed; every run after it, with or without a plain shot between,
    gave `VIEW=[]` and failed `_held`.
  - **Scenario.** A window covers Designer's in the first reading; the retry's second pass fails, counted as random.
  - **Fix.** Before each pass, the user's view set at a view other than Front (`USERS_PLANE_TOP`), as the no-pattern
    check does.
  - **Resolution: done**.
    - **Test:** the frames check run twice in a row in a scratch run: the second failed ("a viewpoint []"), and both pass
      after the fix.
    - **Fix:** before each pass, `USERS_PLANE_TOP` sets the user's view at Top.

- [x] **TST-952 · Two test fakes typed vaguer than known** · `tests/unit/test_view3d_helpers.py:528,623,733,751`, `tests/unit/test_shot3d.py:949` · confirmed · follows TST-950, generation 2 · found 2026-11-26 by two reviewers (Opus)
  - **Defect.** The set-up fake's event kinds are `str`, one of six known; `triggered()` and `steps()` filter on them, so
    a typo drops an event and an absence assertion passes. `test_shot3d`'s `given` holds `Frames | None` where it is always
    a `Frames`.
  - **Scenario.** A mistyped kind makes an absence assertion pass.
  - **Fix.** A `Literal` alias of the kinds, as TST-950 did; `Frames` without `| None`.
  - **Resolution: done**.
    - **Test:** a `'pirnt'` typo passed mypy before the alias and is refused after it.
    - **Fix:** an `Event` alias of the six kinds in the set-up fake; `test_shot3d`'s `given` holds a `Frames`.

- [x] **TST-954 · No test covers Override Material's wait folded into the load's result** · `mcp_server/designer_helpers/scene3d.py:243-255`, `tests/unit/test_view3d_helpers.py:1661,1671,1708` · confirmed · follows HLP-292, generation 2 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `_overrides_back` returns whether its wait settled, folded into `loading`'s; the tests setting
    `designer.overridden = [False]` leave every wait settled, so `_overrides_back` returning True regardless passes them.
    The AOV half has its test.
  - **Scenario.** The fold breaks, and a view unsettled after the Override Material set-back is said settled.
  - **Fix.** A case as the AOV's: Override Material off, the load settled, the set-back's wait not, `UNSETTLED` expected.
  - **Resolution: done**.
    - **Test:** `test_a_view_that_didnt_settle_after_override_material_set_back_is_said`
      (`tests/unit/test_view3d_helpers.py`): Override Material off, the load settled, the set-back's wait not; it failed
      with `_overrides_back` returning True regardless, and passes on the code.

- [x] **TST-955 · ROADMAP's 3D rules don't say the relink turns Override Material on too** · `ROADMAP.md:91-93` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** "A value a load resets, such as the AOV and Override Material, is read first and set back after each
    load": true, but the Explorer's relink turns Override Material on too (HLP-291), which scene3d.py's docstring says
    and the rules leave out.
  - **Scenario.** A value added later from these rules is set back before the relink and lost to it.
  - **Fix.** One clause: a value the relink resets too is set back after the relink (scene3d.py).
  - **Resolution: done**.
    - **Fix:** the rules' "Put back" bullet: "A value the relink resets too, such as Override Material, is set back after
      the relink (`designer_helpers/scene3d.py`; REVIEW.md HLP-291)."

- [x] **TST-956 · TST-921's guard compares the put-back with itself, and two assertions repeat it** · `tests/unit/test_view3d_helpers.py:931-934,1413,1567-1569` · confirmed · follows TST-921, generation 2 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `designer.loads[-1] == designer.state`: the fake's load sets `state` to the file it read, so after any
    run the last load equals it. TST-948's fix changed TST-921's `== SAVED` to this. The second elements at 934 and 1569
    compare `designer.state` read after the run too.
  - **Scenario.** The put-back loading the edited file instead of the base passes the three lines (the byte-for-byte
    `mesh` row and the render-error test still catch it).
  - **Fix.** The user's state kept before the run and compared, or the second elements dropped where the claim is the
    first load's.
  - **Resolution: done**.
    - **Test:** the three tests keep the user's state before the run and compare against it (the tiling test's two
      loads, the framing test's last, the no-mesh-id test's two); with the put-back loading the edited file, all five
      cases fail.

- [x] **HLP-294 · `designer_helpers/__init__.py` says nothing else depends on the parts' order** · `mcp_server/designer_helpers/__init__.py:13-15` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** The parts' annotations are read as they load, so `view3d` and `shot3d` need `frames3d`'s `_Frames`
    before them, and the branch adds `scene3d` reading `Pose` and `_Frames`, and `shot3d` reading `scene3d`'s names. False
    on main already; the load-time binding test catches a reorder.
  - **Scenario.** A reader reorders `PARTS` on the sentence's word.
  - **Fix.** The sentence names what the order serves: a part after the parts its annotations name.
  - **Resolution: done**.
    - **Fix:** the sentence gives the rule: each part after the parts that bind the names it reads at load time, its
      annotations' included; the guard test's name says the same, and passes before and after.

- [x] **TST-957 · ROADMAP item 75 still calls the Height scale a set-up step** · `ROADMAP.md:136` · confirmed · follows TST-937, generation 2 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** "Both are set-up steps (the rules above)": the rules keep "step" for what the file doesn't hold, and the
    Note says the file holds the height scale. TST-937's fix rewrote 82, 87 and 88 and missed this row.
  - **Scenario.** A builder of item 75 gets two instructions for the Height scale.
  - **Fix.** "The button is a set-up step and the Height scale a field of the state file (the rules above): ...".
  - **Resolution: done**.
    - **Fix:** "The button is a set-up step and the Height scale a field of the state file (the rules above): ...".

- [x] **TST-958 · The facts helpers count any checked Scene entry as a mesh checked, where the code counts only a mesh** · `tests/test_all_tools/facts/state_file.py:163,361,364,412,414`, `tests/test_all_tools/facts/checks.py:620` · confirmed · follows TST-943, generation 2 · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `_sf_checked('Scene')` returns every checked entry; `_state_load` subtracts those checked as the trigger
    returns (Display UVs in 2D View, for one), and the unit fake keeps that entry on throughout.
  - **Scenario.** An agent's Designer with Display UVs in 2D View on (the preferences plist is shared): the entries
    check and the user's-mesh fact fail, and the one-field check's mid-load Save may come before the load ended; the code
    itself works there. False failures in the final check.
  - **Fix.** The helpers filtered to `MESHES`, as `SHOWN_ALREADY` and `SHOWN_MESH` do.
  - **Resolution: done**.
    - **Test:** a unit guard requires the only reading of the Scene menu in the facts' snippets to be the meshes' filter
      (it and two tests naming it failed first); live, with Display UVs in 2D View on, the entries check and the user's-mesh
      fact failed falsely before the fix, and all ten checks pass after it.
    - **Fix:** `_sf_meshes()` keeps the Scene menu's checked meshes (`MESHES`), in place of the five readings.

- [x] **TST-959 · Skipped state file checks are recorded under 'designer facts' where they run under screenshot_designer** · `tests/test_all_tools/facts/checks.py:383-390,427,607,919,987,1008,1039` · confirmed · found 2026-11-26 by a reviewer (Opus)
  - **Defect.** `skipped_in_users` calls `skip('designer facts', name, ...)` for 11 names whose `check(...)` calls use
    `'screenshot_designer'`.
  - **Scenario.** In the user's Designer or off macOS, the summary lists them under another tool; a comparison by tool and
    name doesn't match.
  - **Fix.** Each name skipped with its own tool.
  - **Resolution: done**.
    - **Test:** an AST guard requires every name skipped in a facts function to be skipped under the tool its `check()`
      uses; it found the eleven names before the fix, and fails with one call put back.
    - **Fix:** `skipped_in_users(ctx, *names, shots=...)` skips `shots` under `screenshot_designer`.
