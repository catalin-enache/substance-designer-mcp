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

**Last used:** PLG-45, SRV-184, HLP-224, INS-46, TST-693, AGT-123.

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
| Low-medium | 0 | 8 |
| Low | 0 | 76 |
| **Total** | **0** | **85** |

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
| 2026-11-20, step 1 of ROADMAP item 112 | Opus (developer) | 1 | 2 [1 Low-medium, 1 Low] | 2 [1 Low-medium, 1 Low] | 370,525 | 29 min |
| 2026-11-20, the first review (step 1) | Sonnet | 2 | 8 [8 Low] | 8 [8 Low] | 264,808 | 7 min |
| 2026-11-20, the first review (step 1) | settling | 1 | 0 | 0 | 79,181 | 2 min |
| 2026-11-20, the first review's fixes | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 235,048 | 35 min |
| 2026-11-20, the second review (the first review's fixes) | Sonnet | 2 | 4 [1 Low-medium, 3 Low] | 4 [1 Low-medium, 3 Low] | 337,639 | 8 min |
| 2026-11-20, the second review's fixes | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 101,621 | 17 min |
| 2026-11-21, the lean plan's Undo and zoom (items 2 and 3), TST-655 | Opus (developer) | 1 | 3 [3 Low] | 3 [3 Low] | 700,487 | 90 min |
| 2026-11-21, HLP-208, HLP-209 and TST-656 | Opus (developer) | 1 | 0 | 0 | 74,714 | 14 min |
| 2026-11-21, HLP-210's cause and fix | Opus (developer) | 1 | 0 | 0 | 76,770 | 25 min |
| 2026-11-21, the review of the whole branch | Opus | 3 | 14 [2 Low-medium, 12 Low] | 14 [2 Low-medium, 12 Low] | 635,251 | 15 min |
| 2026-11-21, the review of the whole branch | settling | 1 | 0 | 0 | 160,594 | 10 min |
| 2026-11-21, the whole-branch review's fixes | Opus (developer) | 1 | 0 | 0 | 340,943 | 42 min |
| 2026-11-21, HLP-211's reader of the Rasterizer's settings | Opus (developer) | 1 | 0 | 0 | 115,472 | 27 min |
| 2026-11-21, the review of the whole-branch review's fixes | Opus | 2 | 9 [1 Low-medium, 8 Low] | 9 [1 Low-medium, 8 Low] | 450,849 | 15 min |
| 2026-11-21, the fixes of HLP-215, HLP-216, TST-667 to TST-670, TST-672, TST-673 | Opus (developer) | 1 | 0 | 0 | 199,742 | 38 min |
| 2026-11-21, the review of the second round of fixes | Opus | 2 | 8 [1 Low-medium, 7 Low] | 8 [1 Low-medium, 7 Low] | 439,480 | 13 min |
| 2026-11-21, the fixes of TST-676 to TST-678 and HLP-217 | Opus (developer) | 1 | 2 [1 Low-medium, 1 Low] | 2 [1 Low-medium, 1 Low] | 76,316 | 13 min |
| 2026-11-21, the fixes of TST-679 and TST-680 | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 56,799 | 13 min |
| 2026-11-21, the fix of TST-681 | Opus (developer) | 1 | 0 | 0 | 9,798 | 3 min |
| 2026-11-21, the review of the third round of fixes | Opus | 2 | 10 [1 Low-medium, 9 Low] | 10 [1 Low-medium, 9 Low] | 374,158 | 12 min |
| 2026-11-21, the fixes of TST-683, SRV-184 and HLP-218 | Opus (developer) | 1 | 0 | 0 | 66,391 | 14 min |
| 2026-11-21, the review of the fourth round of fixes | Opus | 2 | 6 [6 Low] | 6 [6 Low] | 398,471 | 12 min |
| 2026-11-21, the fixes of HLP-219, HLP-220 and TST-684 | Opus (developer) | 1 | 0 | 0 | 52,823 | 11 min |
| 2026-11-21, the review of the whole branch, again | Opus | 3 | 7 [7 Low] | 7 [7 Low] | 835,011 | 18 min |
| 2026-11-21, the fixes of HLP-221, HLP-222, TST-685, TST-687 to TST-689 | Opus (developer) | 1 | 0 | 0 | 251,444 | 27 min |
| 2026-11-21, the review of the whole-branch review's fixes, again | Opus | 2 | 6 [6 Low] | 6 [6 Low] | 448,598 | 16 min |
| 2026-11-21, the fixes of TST-690 to TST-692 and HLP-223 | Opus (developer) | 1 | 0 | 0 | 96,864 | 14 min |
| 2026-11-21, the fixes of TST-693 and HLP-224 | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 147,384 | 28 min |
| **Total** | | **39** | **83 [8 Low-medium, 75 Low]** | **83 [8 Low-medium, 75 Low]** | **7,397,181** | **568 min** |

## Review log

### 2026-11-20: the flaky-live-checks branch, step 1 (a failing live check keeps its evidence)

- **Scope:** `git diff 40300b8 01c9379 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers, one on the pool's part (`__main__.py`, `workers.py`, the pool's tests), one on the
  two checks' diagnostics and the Undo snippet (`common.UNDO_REDO`, `undo/`, `editor_panels_and_fit/`, their tests);
  the claim was the user's approved text of the branch's rules and step 1, with their later instructions. No tests
  run. The developer's two new problems settled: TST-641 by reading, TST-640 by the runner's probe on port 9921
  (`scratchpad/zoom_probe.py`, read by the lead): the check's own framing call and `shoot_3d(path, zoom=k)` for k = 0
  to 6 in a hidden Designer's 342 x 362 panel gave plane widths 226, 250, 278, 310, 342 (edges at both sides), then
  no plane edge at k = 5 and 6, whose renders are byte-identical (difference 0.000; k = 4 is 7.601 from k = 6).
  Nothing settled as wrong.
- **Not verified:** none.
- **Resolutions assessed:** none in scope.
- **Findings:** TST-640 (Low-medium), TST-641 to TST-649 (Low). TST-649 was the diagnostics reviewer's Unspecified
  note A, settled by the lead as the change doing less than its claim ("the active app").
- **Suggested order:** TST-640 first: step 2's reproduction counts failures with this check, so it must see a lost
  notch. Then TST-646 (a failing run's repair), then the rest.
- **Checked and found fine:** the verdicts and the passing paths are unchanged (both reviewers); the timing lines are
  taken at the pool's poll; `one_run`'s `failed` matches a worker's exit code; the `temp_folder` refactor; `_fire`
  and `_state` reach `acts`, `found` and `sys` through the plugin's one exec scope, and `_state()` can't keep the
  action from firing; the new unit tests fail without their change; Designer's PySide6 6.8.6 stubs have the calls
  used. Notes, not findings: `sys._selftest_undo_fired` stays on Designer's `sys` after a passing run, reset by each
  schedule; the 10 s poll is diagnostic only, after the verdict; the skip paths (`NOT_FOCUSED`, `NO_ACTION`) keep no
  state, for step 4, where the skips are to go (the branch's rule 8).

### 2026-11-20: the flaky-live-checks branch, the first review's fixes

- **Scope:** `git diff 6021280 ae294ed -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers, the pool's part (`workers.py`, README, the pool's tests) and the checks' part (the
  zoom check, the Undo checks, `UNDO_REDO`, their tests), each rechecking its resolutions; the claim as in the first
  review, with TST-640's verdict change allowed. No tests run by the reviewers. The lead ran two to settle: the TST-423
  guard test fails (TST-651), and `tests/unit/test_types.py` passes. Settled as wrong: `as_prepared.py:30` passing
  `SDValueArray.sNew(...)`, whose type allows `None`, to `setAnnotationPropertyValueFromId`, which PyCharm flags: mypy
  strict accepts it, and mypy is the check that counts (`.claude/rules/python.md`). Folded into TST-650 as a note: the
  checks reviewer's untested `_front()` failure branch, which TST-650's fix removes.
- **Not verified:** none.
- **Resolutions assessed:** TST-640 to TST-649 hold; TST-651 follows TST-640, TST-652 follows TST-641, TST-653 follows
  TST-642 and TST-644, TST-654 follows TST-644, each generation 2.
- **Findings:** TST-651 (Low-medium), TST-652 to TST-654 (Low).
- **Suggested order:** TST-651 (a unit test failing now), TST-650, then the rest.
- **Checked and found fine:** the passing paths (an empty `evidence` removes the run's folder as before; a non-empty
  one implies a failed run); the keep reasons and `none`; the scratch folder found where the worker made it; the
  zoom check's band (1.78 to 1.96 against 1.69 and 2.08 for a step lost or added) and its guards against a missing
  render; the 10 s poll's end never taken for success; `test_selftest_undo.py`'s scripted reads. Notes, not findings:
  the pool's own waits have no limit (`workers.schedule`, `unit_proc.wait()`), pre-existing, now in PLAN.md's step 6;
  the add and code-run checks still read their verdict through `NODE_EXISTS`, whose `processEvents()` may run a late
  Undo inside the job, step 4's ground; `said += text(...)` in the zoom check joins two replies without a separator,
  cosmetic.

### 2026-11-21: the flaky-live-checks branch, the whole branch against main

- **Scope:** `git diff main...aabae97 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`, 27 files.
- **How:** three Opus reviewers by area: the pool and the evidence a failure keeps (`workers.py`, `__main__.py`,
  `categories.py`, README, `renders.py`, their tests); the Undo (`common.py`, `undo/`, GUIDE.md, their tests); the 3D
  shot's zoom (`designer_helpers/`, `views.py`, the zoom and wheel facts checks, their tests). The claim: the branch's
  rules 1 to 8 as first committed (40300b8), step 1, the lean plan (6f44135), and the user's later words, quoted. No
  tests run by the reviewers. The lead settled every suspicion by reading, except HLP-211, which the runner's probe
  measured on port 9980 (`scratchpad/probe/`, read by the lead).
- **Not verified:** none.
- **Resolutions assessed:** TST-640, TST-642 to TST-650, TST-652, TST-654, TST-656, HLP-209 hold. Questioned:
  TST-641 (its tests went with TST-655's rewrite: TST-661), TST-653 (TST-660), TST-655 (TST-658), HLP-208 (HLP-213),
  HLP-210 (TST-666). TST-651 holds; a note added under it.
- **Findings:** TST-657 and HLP-211 (Low-medium); TST-658 to TST-666, HLP-212 to HLP-214 (Low). Merged: TST-658,
  from the pool's and the Undo's reviewers.
- **Suggested order:** HLP-211 with HLP-214 and HLP-212 (the rest test and the settle share the count's target:
  with the Rasterizer's Samples below 8, a settle that says when it ended at its net would say so on every shot);
  TST-657; then the checks' and docs' findings.
- **Settled as wrong, or not raised:**
  - The tool never resends a wheel notch, where the lean plan says "the tool resends a notch Designer confirms it
    didn't take" (the zoom reviewer). Measured: Designer gives no sign of a dropped notch (`sendEvent` True and
    `isAccepted()` False for every notch, taken or dropped; the wheel facts check), so no notch is ever confirmed
    not taken, and the plan's resend has no case to act on. Stopping and saying so follows rules 3, 6 and 7.
  - `taken()`'s limit went from NO_RESTART (1 s) to SETTLE_LIMIT (3 s), against rule 1's "no longer limit" (the zoom
    reviewer's Unspecified). NO_RESTART was a time a step was expected to take, whose end the code took for going
    on; its end now stops the moves and is said. Rules 3 and 7, and `.claude/rules/waits.md` (a limit is a safety
    net, never the expected time), decide it.
  - `edit_menu.py` polls `describe_graph` where `waits.md` asks for a callback first (the Undo reviewer's
    Unspecified). The self-test talks to Designer only through MCP calls, from outside it: no callback reaches it
    there, which is the case `waits.md` polls for.
  - "no code job goes to Designer" in `edit_menu.py`'s docstring, though `describe_graph` is a job too (the Undo
    reviewer): the sentence names the code jobs that run `processEvents()`, and misleads no one.
  - The run's folder removed after a failed parent check has no unit test (generation 3, docs that change nothing
    anyone does), and the pool's own waits with no limit (on main; the old step 6, outside the lean plan): the pool's
    reviewer, under DECISIONS.md, Project rules.
- **Notes:** under TST-646 (`put_back`'s Redo) and TST-651 (its guard's names). Other leftovers, not raised: `_steps`
  has no unit test; `_stopped`'s "within 3 s" is per wait, so a "not sent" after the look may have waited about 6 s;
  `said += text(...)` in the zoom check joins two replies without a separator.
- **Unspecified, for the user:** the pool prints each worker's start and end, not the unit suite's, though its load
  is one of the run's conditions (the pool's reviewer). ROADMAP item 42 plans to delete old `sd_mcp_selftest_*`
  folders, which a failed macOS run now keeps on purpose (outside this branch's scope).
- **Longest chain still growing:** TST-642 → TST-653 → TST-660, generation 3.
- **Checked and found fine:** the arm and disarm of the Edit menu's action (a resend can't undo twice); every Undo
  read bounded by `LANDING_S` and `SENDS`, the limit's end never taken for success; no check retries itself; the
  verdicts read the graph; no skip left in `undo` or the zoom checks; `_wheel` sends nothing after a notch not at rest
  or with no sign; `from_rest` marks after `_at_rest`, so the look's restart isn't a notch's sign; every wait and loop
  is bounded; the pool's keeping and reasons (TST-643, TST-644), its tests tied to where the worker makes its scratch
  (TST-645); no new `Any`, `noqa` or `type: ignore`.

### 2026-11-21: the flaky-live-checks branch, the whole-branch review's fixes

- **Scope:** `git diff aabae97 8c44c2d -- . ':(exclude)PLAN.md'`: the fixes of TST-657 to TST-666 and HLP-211 to
  HLP-214, DECISIONS.md's new entry and ROADMAP's.
- **How:** two Opus reviewers, the 3D shot (`designer_helpers/`, `views.py`, `editor_panels_and_fit/`, their tests,
  DECISIONS.md) and the rest (`undo/`, `workers.py`, `__main__.py`, README, GUIDE.md, ROADMAP.md, their tests); the
  claim as in the review of the whole branch, with the user's choice for HLP-211 quoted. No tests run. All settled by
  reading.
- **Not verified:** none.
- **Resolutions assessed:** TST-657, TST-658, TST-661, TST-663, TST-665, TST-666, HLP-212, HLP-213 hold. Questioned:
  HLP-211 (HLP-215, HLP-216), TST-659 (TST-670), TST-660 (TST-669), TST-662 (TST-667, TST-668), TST-664 (TST-672),
  HLP-214 (TST-673).
- **Findings:** HLP-215 (Low-medium); HLP-216, TST-667 to TST-673 (Low). Merged into HLP-215: the 3D reviewer's
  suspicions 1, 2, 3 and 6, all of the Rasterizer read on the Parameters panel; into HLP-216, its 4 and 5; into
  TST-670, the pool reviewer's S4 and S5.
- **The user's decision (2026-11-21):** shown HLP-215, the user chose "Drop the read (Recommended)": no Parameters
  panel access; with Samples below 8 or antialiasing off, an on-screen zoom is refused and the result names the
  setting and where to change it; a settle ending with the count below 8 says so the same way. DECISIONS.md's entry
  went back to the tiling and the environment.
- **Suggested order:** HLP-215 with HLP-216 and TST-673 (the 3D shot's waits and their docs), then TST-672, then the
  Undo's TST-667 and TST-668, then TST-669 and TST-670. TST-671 was the lead's own wording, fixed by the lead.
- **Not raised:** README's "then triggers Redo the same way", untrue for the set check alone, and GUIDE.md's "drives
  ... the Rasterizer's settings", which HLP-215's fix removes: neither misleads anyone acting on it (the pool
  reviewer). Outside this diff, older code: `view3d._switched`'s fixed loop of 10 x 0.1 s, whose end is taken for
  success (the 3D reviewer), the kind of wait the lean plan left out (its old step 6).
- **Notes:** under TST-655 (a failed read leaves the action armed).
- **Longest chain still growing:** TST-642 → TST-653 → TST-660 → TST-669, generation 4.
- **Checked and found fine:** the default path reads nothing and leaves the panel as it was; nothing is read off
  screen or with no count shown; `_TurnBackFailed` keeps the tiling's and environment's errors as they were; the
  diff adds no wait or retry in the Undo and the pool, no `Any`, `noqa` or `type: ignore`; `check_the_quits` has one
  caller; ROADMAP items 113 and 114 are as approved.

### 2026-11-21: the flaky-live-checks branch, the second round of fixes

- **Scope:** `git diff cfdf3d3 f4a2138 -- . ':(exclude)PLAN.md'`: the fixes of HLP-215, HLP-216, TST-667 to TST-670,
  TST-672 and TST-673, and the user's rule on tests that fail at random (DECISIONS.md, the `live-check` skill,
  AGENTS.md, `docs/agent-workflow.md`, ROADMAP.md).
- **How:** two Opus reviewers, the 3D shot and the rest (the Undo, the pool, the rule's texts with the `runner` file
  and the `delegate` skill); the claim as before, with the user's choice for HLP-215 and their words on the rule
  quoted. No tests run. All settled by reading; `designer_helpers/view3d.py`'s docstring is where TST-675's figure was
  measured.
- **Not verified:** none.
- **Resolutions assessed:** HLP-215, TST-667 to TST-673 hold. Questioned: HLP-215 (TST-677), HLP-216 (HLP-217),
  HLP-214 (TST-678). The rule, the lead's text: AGT-111, TST-674, AGT-112, TST-675, TST-676.
- **Findings:** AGT-111 (Low-medium); TST-674 to TST-678, AGT-112, HLP-217 (Low).
- **The user's decision (2026-11-21):** asked how a check that only the full run makes should count when it fails,
  the user: "run teh category in isolation for which that test is belonging". So a live check is rerun through the
  pool with its category alone (`--only`), which makes the pool's checks for it; the check that every tool was
  exercised, made only over a full run, counts as failed (the lead's reading, told the user).
- **Fixed by the lead, whose texts they were:** AGT-111, TST-674, AGT-112, TST-675. Left to the developer: TST-676 to
  TST-678, HLP-217.
- **Notes:** under TST-672 (the start framings' replies), TST-673 (the exposure's `and settled`) and HLP-215 (a show at
  Samples below 8 waits its net on every shot; `_set_environment`'s `below_rest()` outside its try). The Undo
  reviewer's outside-the-diff point, `say()` returning at once for a refused resend, is older code and drops nothing a
  failure needs beyond the refusal it prints.
- **Unspecified, answered by the lead:** a random failure's evidence lives in temporary folders, which a reboot or
  `uninstall.py` may remove; the row says where it was kept, and nothing copies it. A category rerun where another of
  its checks fails: that check failed alone, so it is a failure.
- **Longest chain still growing:** HLP-211 → HLP-215 → TST-677, generation 3; TST-642 → ... → TST-669 ended at
  generation 4.
- **Checked and found fine:** nothing of the Rasterizer read is left; the default settings' waits are as before HLP-211;
  `below_rest` returns '' off screen, with no count and at SAMPLES; every kept line names its category; the rule's five
  texts agreed with each other and with the user's words; no `Any`, `noqa`, `type: ignore` or `cast` added.

---

### 2026-11-21: the flaky-live-checks branch, the third round of fixes

- **Scope:** `git diff f4a2138 e1914fc -- . ':(exclude)PLAN.md'`: the fixes of TST-676 to TST-681 and HLP-217, and the
  lead's of AGT-111, TST-674, AGT-112 and TST-675, the rule's texts.
- **How:** two Opus reviewers, the 3D shot and the rule's seven texts with the pool's code they tell; the claim as
  before. No tests run. All settled by reading, HLP-218's path included; its rate under the pool isn't measured.
- **Not verified:** none.
- **Resolutions assessed:** TST-676 to TST-681, HLP-217, AGT-111, TST-674, AGT-112 and TST-675 hold. Questioned:
  AGT-111 (AGT-113, AGT-114, AGT-118), TST-675 (TST-682), TST-677 (TST-683), TST-679 (SRV-184).
- **Findings:** AGT-113 (Low-medium); AGT-114 to AGT-118, TST-682, TST-683, SRV-184, HLP-218 (Low). HLP-218 is in
  older code of the branch, outside the round's diff.
- **Fixed by the lead, whose texts they were:** AGT-113 to AGT-118 and TST-682. Left to the developer: TST-683,
  SRV-184, HLP-218.
- **Notes:** under TST-676 (its comment, now saying what it reads). HLP-215's resolution cites
  `test_a_count_below_8_on_screen_names_what_may_hold_it_there`, renamed since
  `test_a_count_below_8_names_what_may_hold_it_there`. Not raised (DECISIONS.md, Low-value findings): two put-back
  guards of the Rasterizer check that miss only when two independent failures come together. ROADMAP.md's section
  says more of a row that exists than the other texts (its last failure's cells updated), without contradicting them.
- **Unspecified, for the user:** whether the pool's checks over the whole run (the count of quits forced, the
  preferences, a crash dump outside the run) and a live check off macOS get a rerun of their own, now outside the rule
  (AGT-113, AGT-114); whether a row's count past some number reopens the rule or forces a fix, as the Reopen if names
  only the table's growth. **Answered by the lead:** a random failure in a final check that fails for another reason
  is listed too, before the merge, as the rule's row goes in "after the final check and before the merge".
- **Longest chain still growing:** HLP-211 → HLP-215 → TST-677 → TST-683, generation 4.
- **Checked and found fine:** the rule's seven texts agree on the procedure, and no leftover of the old wording is
  outside REVIEW.md; `_cells` keeps an escaped FAIL line at 6 cells; `below_rest`'s callers always print what it
  returns, and `HELD % (count, '')` is the old on-screen text; frames3d.py's docstrings match the code; no `Any`,
  `noqa`, `type: ignore`, `cast` or skip added.

---

### 2026-11-21: the flaky-live-checks branch, the fourth round of fixes

- **Scope:** `git diff e1914fc 2e7b06a -- . ':(exclude)PLAN.md'`: the lead's fixes of AGT-113 to AGT-118 and TST-682,
  the user's answers on the rule, ROADMAP.md's items 40 and 38 moved first, and the developer's fixes of TST-683,
  SRV-184 and HLP-218.
- **How:** two Opus reviewers, the 3D shot and the rule with ROADMAP.md; the claim as before, with the user's answers
  quoted. No tests run. All settled by reading.
- **Not verified:** none.
- **Resolutions assessed:** AGT-113 to AGT-118, TST-682, TST-683, SRV-184 and HLP-218 hold. Questioned: AGT-113
  (AGT-120, AGT-121), AGT-114 (AGT-119, AGT-121), HLP-218 (HLP-219, HLP-220, TST-684).
- **Findings:** AGT-119 to AGT-121, HLP-219, HLP-220, TST-684 (Low). Only a few Low: the rounds on the fixes end
  here, and the entire branch is reviewed next.
- **The user's answers (2026-11-21):** a count of quits forced that passes its rerun: "Merge, and tell me"; another
  check failing in the whole live rerun: "Rerun it alone too"; a check that skips in its rerun: "Rerun once clear"
  (a failure if its cause can't be cleared); off macOS, the checks only the whole run makes: "Whole Windows run". In
  DECISIONS.md and the `live-check` skill, guarded by the rule's docs test.
- **Fixed by the lead, whose texts they were:** AGT-119 to AGT-121. Left to the developer: HLP-219, HLP-220, TST-684.
- **Notes:** under AGT-116 (no test guards its clause; the docs test's comment names it). AGT-117's "24 lines added"
  was before the user's answers. Not raised: `off_defaults`' `when` and `set_rasterizer`'s `kind` could be `Literal`s;
  a put-back refused by NOT_AS_READ says the page "wasn't read after the put-back"; no committed live check of the look
  made again (a check of Designer's part already re-measures it).
- **Unspecified, answered by the lead:** one wheel step's rest, with REST_LOOKS looks each under `_bring`'s limits, can
  outlast the call's 120 s timeout in the extreme, as several steps could before: every wait ends at its limit, so
  nothing hangs (the branch's rule 7).
- **Longest chain still growing:** AGT-111 → AGT-113 → AGT-120, generation 4; HLP-211 → ... → TST-683 ended at 4.
- **Checked and found fine:** `--only` takes several categories (`nargs='+'`), `--no-unit` gives `run_pool(unit=False)`,
  and `run_pool` always runs the quits' and the preferences' checks; the count's FAIL names its categories; ROADMAP.md's
  rows 40 and 38 are byte-identical moves; `below_rest`'s three callers match SRV-184's docstring; REST_LOOKS looks
  again only off screen, with nothing sent, and every exit is bounded; no `Any`, `noqa`, `type: ignore`, `cast` or
  skip added.

---

### 2026-11-21: the flaky-live-checks branch, the whole branch against main, again

- **Scope:** `git diff main...b5cdcac -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`, 39 files.
- **How:** three Opus reviewers: the 3D shot's tool code (with GUIDE.md and README.md), its live checks, and the Undo,
  the pool and the rule's texts; the claim as at aabae97, with the user's words since quoted. No tests run. All settled
  by reading.
- **Not verified:** TST-687's effect, an armed Edit menu action landing on another document in the user's Designer:
  it needs the one run, on Windows; the fix removes the path.
- **Resolutions assessed:** every one in scope holds but TST-664 (TST-688, TST-689), HLP-214 (HLP-222) and TST-662
  (TST-685).
- **Findings:** HLP-221, HLP-222, TST-685 to TST-689, all Low. Only a few Low: **the reviews look converged.**
- **Fixed by the lead, whose text it was:** TST-686. Left to the developer: the other six.
- **Notes, fixed by the lead:** GUIDE.md's 3D view paragraph, a rewrap left by HLP-215, back to `main`'s text; the
  rule's off-macOS clause names "the checks only the whole run makes there, such as" the two it listed, as the
  reviewer found two more (the user's Designer still running after the run, the run reaching its end); its example
  says the zoom check passed 3 in 3 "in scratch runs", as ROADMAP item 112 has it.
- **Notes, not raised** (DECISIONS.md, Low-value findings): `window_states.py` says "1 run in 60" where `view3d.py`
  says 2 in 120 of the same measurement; `window_states.LOOKED` copies shot3d's wordings with no test tying them; a
  test comment says the undisturbed zoom stays on screen, where it looked once live; `_stopped`'s `move`,
  `wheel_facts`' `mode` could be `Literal`s; views.py's "Each wheel step waits for the 3D view to be at rest" leaves
  out a view with no count shown; the `runner` file's "in the same brief" can't hold off macOS, where its "not rerun
  and why" reports it.
- **Unspecified, answered by the lead:** off macOS, `_bring` does nothing, so a wheel step from a view off screen
  with its count left below 8 is refused, said: each step is sent only from rest (DECISIONS.md, "The 3D shot never
  sends a wheel step ... again").
- **Unspecified, for the user:** whether ROADMAP item 112 stays checked when the final check lists its own Undo or
  zoom check as failed at random, as the user's memory says a flaky check's fix counts only once proven in the full
  run's conditions.
- **Outside the scope:** `_Frames.settled`'s first wait, from `main`, takes no restart within NO_RESTART (1 s) as
  nothing changed; under load a `graph=` shot whose outputs reach the mesh later would render before them. Like the
  older waits the lean plan left out; ROADMAP item 100 holds that kind.
- **Longest chain still growing:** AGT-111 → AGT-113 → AGT-120, generation 4, none added to it this round.
- **Checked and found fine:** every wait and retry of the tool ends at a limit, and no limit's end is taken for
  success; a look again comes only while nothing was sent; `send` resends only after a read that disarmed the action;
  the pool's evidence and kept lines; the rule's commands against `__main__.py`, `workers.py` and `alone.py`, and its
  eight texts agree; no check retries itself; each forced case that didn't happen fails; no `Any`, `noqa` or skip
  added.

---

### 2026-11-21: the flaky-live-checks branch, the whole-branch review's fixes, again

- **Scope:** `git diff b5cdcac 23e1e8f -- . ':(exclude)PLAN.md'`: the fixes of HLP-221, HLP-222, TST-685 to TST-689,
  the lead's notes fixed with them, and the user's answer on item 112.
- **How:** two Opus reviewers, the 3D shot (its tool code and checks) and the Undo with the rule's texts; the claim as
  before, with the user's answer quoted. The user chose this round before the final check ("Opus round, then check").
  No tests run. All settled by reading.
- **Not verified:** TST-690's effect, as TST-687's: it needs the one run on Windows.
- **Resolutions assessed:** HLP-221, HLP-222, TST-685, TST-686, TST-688, TST-689 hold, with notes; questioned: TST-687
  (TST-690, TST-691), TST-688 (TST-692), HLP-221 (HLP-223).
- **Findings:** TST-690, TST-691, AGT-122, AGT-123, TST-692, HLP-223, all Low, of 9 suspicions: three are leftovers in
  tests no later check depends on, written as notes (under TST-687, TST-689 and HLP-222). Only a few Low: the final
  check follows, as the user chose, once the developer's fixes are in.
- **Fixed by the lead, whose texts they were:** AGT-122, AGT-123. Left to the developer: TST-690, TST-691, TST-692,
  HLP-223, and the three notes.
- **Notes, not raised:** HLP-222's open case gains a detail: `_at_rest`'s read of the count at SAMPLES could clear
  `undrawn`, but `shown` can fail from a count at 8 with an UpdateRequest pending, so a clear there needs measuring; the
  line stays a "may" beside the step's stop. A zoom-only set-up whose first rest's look raises now says "(0 sent)".
  TST-685's test constant is about 120 characters, not 115. `edit_menu.py`'s "A read of the action's state that fails
  leaves the action armed" says more than known: "may leave". `Path(ast.literal_eval(...))` takes an implicit `Any`.
- **Longest chain still growing:** TST-664 → TST-688 → TST-692, generation 3.
- **Checked and found fine:** no wait, retry or limit added or changed; the off-macOS clause and the example agree in
  both texts; `begin_send` needn't reset `unread`, every path that sets it returning; on a failed read `fired` stays
  None, so `put_back` sends no Redo; GUIDE.md's 3D view paragraph is `main`'s; no `noqa`, `type: ignore`, `cast` or
  skip added.

---

## High

## Medium-high

## Medium

- [x] **HLP-210 · An on-screen 3D zoom of 2 steps or more returns a render of its last notch's first frame** · `mcp_server/designer_helpers/frames3d.py`, `_Counts.settled` · measured · found 2026-11-21 by the runner (Sonnet)
  - **Defect.** After its moves, the 3D shot's set-up waits once with `settled(since)`, from a mark taken before the
    zoom. `_Counts.settled` took the first restart since that mark, then any paint at the count at rest. The branch's
    zoom fix sends each notch only from a view at rest, so notch 1's restart and its count back at 8 met that
    condition, and the render was taken at the last notch's first frame: overlay count 1, one sample, aliased edges.
  - **Scenario.** Both full runs of 2026-11-21 (802 of 803) failed the zoom check's off-screen-from-rest case: 6 steps
    taken (1.88x), its render 2.09 grey levels from the undisturbed zoom, at the checker squares' edges only,
    pixel-identical in both runs. The off-screen render was the settled one; every on-screen zoom of 2 steps or more
    gave the user an unsettled render. The check missed it in scratch runs: there the plane had no checker, which only
    earlier checks of the category put on. Its other case passed because both of its renders were unsettled alike.
  - **Resolution: done**.
    - **Test:** `edge_probe.py`, a scratch probe: the on-screen zoom of 6 rendered at count 1, the hidden one at 8,
      3 of 3. `tests/unit/test_frames3d.py`:
      `test_a_view_restarted_again_after_settling_is_settled_once_its_latest_restart_counted_back` and
      `test_a_step_of_several_moves_waits_for_the_count_back_after_the_last` failed on the old code. The changed zoom
      check alone failed all 3 verdicts before the fix, each 2.09.
    - **Cause:** the settle ended at the first restart since its mark, which a step of several moves passes long before
      its last.
    - **Fix:** `_Counts.settled` waits for the count back at rest after the latest restart since the mark. The zoom
      check passed 10 of 10 after it, every render 0.00 from a plain shot right after it. The whole
      `editor_panels_and_fit` category passed 129 of 129 in a Designer just started.
    - **Also covered:** the predicate serves every caller of `settled`, whereas HLP-161 and HLP-192, the same cause,
      had each moved a mark at one caller. The two-turn orbit and set_3d_view's two-drag pan are unchanged at 0.00.
      The zoom check now puts its own checker on the plane, and compares each render, the undisturbed one included,
      with a plain shot right after it, so it sees an unsettled render alone and against an unsettled reference.
  - Questioned by TST-666 (2026-11-21).

## Low-medium

- [x] **TST-679 · The Rasterizer check's refusal needs the count, which the stop line gives only on screen** · `mcp_server/designer_helpers/frames3d.py:309-318` (`below_rest`), `tests/test_all_tools/editor_panels_and_fit/checks.py` (the Rasterizer check) · measured · found 2026-11-21 by the developer (Opus)
  - **Defect.** `below_rest` returns '' off screen, "where the count stays as last drawn", so a refused wheel step
    whose window was off screen at the stop says "the 3D view didn't come to rest within 3 s" with no count and no
    cause, and the check, which requires them, fails though the zoom was refused. The result depends on the window's
    state at the stop (the branch's rule 2).
  - **Scenario.** Measured once in 13 runs, with the put-back forced to fail: the shot said UNDRAWN three times, the
    window off screen at the stop, "the refusal said: False", the plane 1.00x. In a full run, another Designer
    covering the window does the same. A user with Samples 4 and a covered window gets no hint of the cause.
  - **Fix.** The stop and "hadn't settled" lines give the count off screen too, as the count last drawn, with the
    same causes, so neither the user nor the check depends on where the window was. Measured first: the count read
    off screen at such a stop.
  - Questioned by SRV-184 (2026-11-21).

  - **Resolution: done**.
    - **Measured:** `scratchpad/offscreen_stop_probe.py` hid the window before the zoom's first step and again after
      `_at_rest`'s look: at the stop, `count()` read the count last drawn, 4 at Samples 4 and 1 with antialiasing off,
      and the stop line had no count, every time.
    - **Tests**, red first: `test_a_count_below_8_names_what_may_hold_it_there` (off screen at 4, at 1, at rest) and
      `test_what_may_hold_the_count_below_8_is_said_once_a_watch` (on screen and off), `test_frames3d.py`; the
      Rasterizer check with the same hiding failed both cases ("the refusal said: False").
    - **Fix:** `below_rest` gives the count off screen too, "when last drawn", with the same causes; the stop line,
      the "hadn't settled" lines and UNDRAWN all use it. The docstrings and `views.py` say so.
    - **Proof:** the Rasterizer check 3 of 3, and the off-screen run passing both cases, on the final code.
  - Questioned by TST-681 (2026-11-21).

- [x] **AGT-111 · The rule for tests failing at random gives no way to rerun alone a check only the full run makes** · `.claude/skills/live-check/SKILL.md:110-114`, `DECISIONS.md` · confirmed · follows the rule of 2026-11-21, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** It said "a live check in a scratch run of its category, in a Designer just started", while the same
    skill says only the full suite makes the run's start checks and the pool's parent checks: each category's quit and
    crash dumps, the forced quits, the preferences, the coverage.
  - **Scenario.** The final check fails `closes render's Designer, which left no crash dump`; `alone.run(render.run)`
    passes, never judging the quit; the crash is listed as random, and the branch merges.
  - **Resolution: done**, by the lead, per the user's decision (2026-11-21, "run teh category in isolation for which
    that test is belonging"): a live check is rerun through the pool with its category alone
    (`tests/test_all_tools --only <category>`), which makes the pool's checks for it; the check that every tool was
    exercised counts as failed. DECISIONS.md's entry, the `live-check` skill, the `runner` file and
    `docs/agent-workflow.md` say so; the docs tests pass.
  - Note (2026-11-21): the user changed the coverage clause: "yes change it". The check that every tool was exercised
    names the tools no check ran for; the categories exercising them are rerun alone, and if they pass with checks run
    for those tools, it failed at random too, as any rerun that passes.
  - Questioned by AGT-113 (2026-11-21).
  - Questioned by AGT-114 (2026-11-21).
  - Questioned by AGT-118 (2026-11-21).


- [x] **HLP-215 · HLP-211's read of the Rasterizer's settings reaches into the Parameters panel mid-shot** · `mcp_server/designer_helpers/frames3d.py:302-316, 427-431`, `view3d.py:771-794` · confirmed · follows HLP-211, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The read (`_read_target`, `_rasterizer_count`) can run in any wait for the count at rest, and:
    - a read that raises (the Parameters panel closed, no single renderer checked, a control not found, the panel
      not turning back) fails the whole shot, a plain one included, which rendered before;
    - a read inside `_set_environment`'s settle turns the panel to the graph, so the next environment field
      (`dome_rotation_angle`, `intensity`) isn't found;
    - it runs at the default settings too, under load, when the count is still climbing at a net, which the user's
      choice ("Only with non-default settings, the Parameters panel flips") didn't cover;
    - an abort in its turn-back leaves the panel on the Rasterizer page (`panel_begun` covers only the tiling and
      the environment).
  - **Scenario.** Samples 4 and Designer in front: `screenshot_designer('3d', environment=<another map>,
    environment_rotation=90)` fails on the rotation. Samples 4 and the Parameters panel closed: a plain 3D shot
    raises.
  - **Fix.** The user's decision, 2026-11-21: drop the read. No Parameters panel access; the count at rest stays
    SAMPLES. On screen, a zoom whose view doesn't come to rest is refused, and the result names the count it saw
    and the settings that stop it below 8 (the Rasterizer's Samples, its accumulation antialiasing, Renderer > Edit
    settings), or a view still refining. A settle that ends with the count below 8 says the same. The Rasterizer
    check expects that, its settings put back. DECISIONS.md's entry back to the tiling and the environment (done).

  - **Resolution: done**, the read dropped (the user's decision).
    - **Tests**, each red first: `test_a_count_stopped_below_8_is_no_rest_and_reaches_no_panel` and
      `test_a_settle_stuck_below_8_ends_unsettled_and_reaches_no_panel` (the panel's helpers made to raise),
      `test_a_count_below_8_on_screen_names_what_may_hold_it_there` (`test_frames3d.py`);
      `test_a_view_held_below_8_samples_says_what_may_hold_it_there` (`test_view3d_helpers.py`);
      `test_a_view_held_below_8_samples_once_on_screen_says_what_may_hold_it_there` (`test_shot3d.py`). The live
      `check_an_on_screen_3d_zoom_held_below_8_samples_is_refused_naming_the_rasterizers_settings` failed on cfdf3d3
      (the read let the zoom through, 1.37x) and on a stop line without the count and causes.
    - **Fix:** the read, its hook, its constants and `_TurnBackFailed` removed; the count at rest is SAMPLES.
      `_Frames.below_rest()` gives, on screen with the count below 8, "its sample count at N, below 8: it may still
      have been refining, or the Rasterizer's Samples may be set below 8 or its accumulation antialiasing off
      (Renderer > Edit settings)", the causes once a watch. A refused wheel step's line, each "hadn't settled" line
      and UNDRAWN carry it. The docstrings, `views.py` and GUIDE.md say so; DECISIONS.md's entry was put back.
    - **Proof:** the live check 3 of 3 at Samples 4 and with antialiasing off (refused, no STALE, the plane at 0
      steps, the settings put back); the zoom check 10 of 10; `editor_panels_and_fit` 131 of 131 in a Designer just
      started. Measured: with Samples 4, each shot whose window comes back on screen waits its 3 s at the look and
      says UNDRAWN with the count.
  - Questioned by TST-677 (2026-11-21).
  - Note (2026-11-21): with Samples below 8, every shot whose window comes back on screen waits its 3 s at the look
    and says UNDRAWN with the count, which frames3d.py's docstring doesn't say; `_set_environment`'s return calls
    `below_rest()` outside the try that names what was set, which raises only if the overlay's labels went mid-shot.

- [x] **TST-657 · GUIDE.md's Undo recipe gives a limit but not what to do when it passes** · `mcp_server/GUIDE.md:91-93` · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The recipe now reads "then read the result in later calls (`describe_graph`) until it shows, with a
    limit, since it may land after the call that scheduled it returns". It says nothing of what to do past the limit.
    The self-test resends only an action its own read says never fired (`common.UNDO_FIRED`, which also disarms it),
    and never one that fired; the guide gives agents nothing like it.
  - **Scenario.** An agent reaches its limit with the Undo not shown and sends Undo again. The first lands late, as
    the self-test measured (3 s with its timer forced; `edit_menu.py`'s docstring), and two steps of the user's graph
    are reverted, against GUIDE.md's rules that protect the user's work and the branch's rule 6.
  - **Fix.** One sentence: past the limit, don't send it again, since it may still land; say so, and look with
    `snapshot_graph` or `diff_graph` before anything else.
  - **Resolution: done**, docs only. GUIDE.md adds: "Past the limit, don't send it again: the first may still land,
    and two steps would be reverted. Tell the user, and look with `diff_graph` or `snapshot_graph` before anything
    else." The docs tests pass.

- [x] **HLP-211 · With the Rasterizer's Samples below 8, or its accumulation antialiasing off, every on-screen 3D zoom is refused** · `mcp_server/designer_helpers/frames3d.py:272-293` (`_resting`, `_at_rest`) · measured · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `_resting` reads the view as at rest only at `count >= SAMPLES` (8), and a notch is sent only from
    rest. The count stops where the Rasterizer's settings say, which frames3d.py's docstring left "not measured".
  - **Scenario.** Measured by the runner's probe (port 9980): Renderer > Edit settings, Samples 1, Samples 4, and
    "Enable rasterizer accumulation antialiasing" off stopped the overlay's count at 1, 4 and 1. Each
    `shoot_3d(..., zoom=2)` on screen then said "wheel step 1 of 2 not sent: the 3D view didn't come to rest within
    3 s" and didn't zoom. Seven other Rasterizer fields at their lowest left the count at 8. A user can save such
    settings as the 3D view's default state (Scene > Save Current State As Default); the user's Designer has none.
  - **Fix.** The count at rest is the view's own target, read as state: the Rasterizer's Samples, or 1 with its
    accumulation antialiasing off. The rest test and the settle after a step both use it (HLP-214). Measure it first,
    with a live check that sets the setting, zooms on screen, and puts it back.
  - **Resolution: done**, the Parameters panel read approved by the user (2026-11-21; DECISIONS.md, "After setting the
    3D view's tiling or environment, or reading its Rasterizer's settings ...").
    - **Test:** `check_the_3d_zoom_settles_on_the_rasterizers_own_count` (`editor_panels_and_fit/checks.py`, its set-up
      `rasterizer.py`) sets Samples 4, then antialiasing off, each put back. It failed on the code before the fix:
      "wheel step 1 of 3 not sent", the plane 1.00x. Unit tests, red first: `test_frames3d.py` (a view at rest at its own
      count, read once a watch, a read that fails stops the wait and guesses nothing, nothing read off screen) and
      `test_view3d_helpers.py` (`test_the_views_count_at_rest_is_read_from_its_renderers_settings`,
      `test_a_read_of_the_rasterizers_settings_that_fails_stops_the_step_and_says_why`).
    - **Cause:** the count at rest was SAMPLES whatever the Rasterizer's settings.
    - **Fix:** each watch's count at rest is SAMPLES until a wait for it ends at its net with the count below it, on
      screen. Then `view3d._rasterizer_count` reads it once: the Renderer menu's checked renderer, then for the
      Rasterizer its Samples, or 1 with antialiasing off, on the Parameters panel's Rasterizer page, turned back to the
      graph in the editor, and said. A read that fails stops the step, saying why. With antialiasing off, a notch's
      sign is the frame after it, as with no count. Measured: the read takes 0.25 s; at Samples 4 a notch on screen
      drew paints reading 4, 1, 1, 2, 3, 4; with antialiasing off, each read 1.
    - **Proof:** the Rasterizer check 3 of 3 on the final code (1.37x for three steps, 0.00 from a plain shot after,
      the count at the render 4, then 1, the settings put back); the zoom check 10 of 10; the wheel facts check; the
      whole `editor_panels_and_fit` category 131 of 131 in a Designer just started.
    - **Also covered:** a count past SAMPLES (the GPU Pathtracer) is read as at rest, so no wait reaches its net and
      nothing is read: as HLP-209 says. Under load at the default settings, a view still below 8 at the net is read
      too, which gives 8.
  - Questioned by HLP-215 (2026-11-21).
  - Questioned by HLP-216 (2026-11-21).

- [x] **TST-640 · The zoom check can't see one lost notch: 5 and 6 notches give the same render** · `tests/test_all_tools/editor_panels_and_fit/checks.py:1637-1658` · measured · found 2026-11-20 by the developer (Opus)
  - **Defect.** `check_wheel_steps_sent_as_designers_window_goes_off_screen_are_all_taken` zooms `zoom = 6` notches and
    passes on `hidden and apart < 1.0`. In a hidden Designer's 342 x 362 3D panel the plane fills the view from 5
    notches on: the k = 5 and k = 6 renders are byte-identical (the runner's probe; the review log).
  - **Scenario.** A hidden zoom that loses one of its 6 notches renders as the undisturbed one, difference 0.00, and
    the check passes: the loss of one step, the failure ROADMAP item 112 is about, goes unseen, and step 2 would
    under-count it.
  - **Fix.** A zoom at which each notch still shows (the plane's width at 0 to 4 notches: 226, 250, 278, 310, 342),
    and a verdict on the plane's width against the zoom expected, beside the difference (the branch's rule 8: judge
    what the user gets). Seen failing with one notch dropped from the scratch script.
  - **Resolution: done**.
    - **Test:** the live check, with one hidden notch dropped from the scratch script only (`notches - 1` in
      `_HIDDEN_MID_ZOOM`): before the fix it passed, 0.00 grey levels; after, `FAIL ... the plane 1.69x as wide as at
      the start (1.11^6 = 1.87); 18.89 grey levels` (start 154 px, undisturbed 290, hidden 261, in a 342 px panel).
      Unforced it passes at 1.88x, 0.00.
    - **Cause:** framed, the plane spans the panel 4 steps in, so 5 and 6 steps rendered alike, and the verdict only
      compared the hidden render with the undisturbed one.
    - **Fix:** both framing calls start 4 steps out (`{**THREE_D, **TOP, 'zoom': -4}`), a start render is saved through
      `shoot_3d`, and the verdict adds the plane's width ratio against `STEP**6` within 5% and fails a plane clipped at
      the panel's edge, beside the difference; on failure the three renders are said.
    - **Also covered:** the three other zoom-width checks of the file (about lines 164, 290, 380) zoom at most 3 or 4
      steps from where each step still shows; two guard a clipped plane, and the Light tool's band fails a clipped
      extra step anyway.
  - Questioned by TST-651 (2026-11-20).

- [x] **TST-651 · TST-640's fix fails the TST-423 guard test, which counts two `grey_file(` in the zoom check** · `tests/unit/test_selftest_window_states.py:481-487` · measured · follows TST-640, generation 2 · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** `test_the_wheel_steps_check_compares_two_renders_saved_alike` asserts
    `body.count('grey_file(') == 2`; the fixed check reads three renders (the start, the undisturbed, the hidden). The
    lead ran it: `1 failed`, on that line.
  - **Scenario.** The next whole unit run fails; the fix's own test runs didn't include this file.
  - **Fix.** Assert what TST-423 guards: every render the check compares is saved through `shoot_3d`, none a tool's
    shot shrunk to `max_size`; not a count.
  - **Resolution: done**.
    - **Test:** the guard failed on `count == 2`, as the lead measured.
    - **Fix:** `test_the_wheel_steps_check_compares_only_renders_saved_alike` asserts by AST over the check that every
      path given to `grey_file` was given to `shoot_3d` (directly, or through `window_states.hidden_mid_zoom`), and that
      no tool's shot is read; two mutations fail it (the start's width read from `screenshot_designer`'s shot; a file
      `shoot_3d` didn't save). `test_selftest_window_states.py` ran whole.
  - Note (2026-11-21): the guard matches the paths by name, and `plain_after`'s parameter is also `path`, so
    `plain_after(<a tool's shot>)` would pass it. If the test is touched, narrow its comment rather than strengthen it.

- [x] **AGT-113 · The rule says the category's rerun makes the pool's checks over the whole run** · `DECISIONS.md`, the rule's entry; `.claude/skills/live-check/SKILL.md`, When the final check fails · confirmed · follows AGT-111, generation 3 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** Both texts list "Designer's preferences, the forced quits" among the checks the pool makes "for that
    category". Three of the pool's checks belong to no category: the count of quits forced over every worker
    (`workers.py`, "no more than two quits forced during their shutdown"), the preferences as before the run
    (`PREFERENCES`) and a crash dump outside the run.
  - **Scenario.** A full run fails the count with one quit forced each in render, params and lifecycle. Each
    category rerun alone forces at most one and passes, so the failure is listed as random and the branch merges,
    where DECISIONS.md, Bridge and quitting, says to reopen. For the preferences, no category can be rerun at all.
  - **Fix.** Generation 3, docs only: drop them from the lists, and say the rule doesn't cover the pool's checks over
    the whole run.
  - **Resolution: done**, by the lead, whose text it was: both texts list only the category's quit and crash dumps
    and the start checks, and say the rule doesn't cover the pool's other checks over the whole run, which belong to
    no category: the count of quits forced, Designer's preferences and a crash dump outside the run. The user's words
    cover a test "in a category"; whether those checks get a rerun of their own is the user's, in the log.
  - Note (2026-11-21): the user chose a rerun for them ("rerun"): the count of quits forced with the categories
    it names, together (`--only`); the preferences and a crash dump outside the run with the whole live
    self-test (`--no-unit`). In DECISIONS.md and the `live-check` skill, by the lead.
  - Questioned by AGT-120 (2026-11-21).
  - Questioned by AGT-121 (2026-11-21).

## Low

- [x] **TST-641 · The add and two-nodes Undo checks print none of the new diagnostics** · `tests/test_all_tools/undo/checks.py:18-30` · confirmed · found 2026-11-20 by the developer (Opus)
  - **Defect.** Only `check_one_undo_puts_an_outputs_fields_back` says on failure whether its Undo landed late and in
    what state it was scheduled and fired. The add check (`gone = 'EXISTS=False' in ...`, then a Redo at once) and the
    two-nodes check go through the same `UNDO_REDO` and fail the same way, with nothing more than their verdict.
  - **Scenario.** The add check fails in a full run (it did before `SOLO`: REVIEW.md TST-234), and the next diagnosis
    has no evidence: the same pattern fixed in one instance only (AGENTS.md, fix the pattern).
  - **Fix.** The same diagnostic for each Undo check, its predicate the check's own (the node gone, the two nodes
    gone), before its Redo.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_selftest_undo.py`, `test_the_add_checks_undo_is_said_and_redone_only_if_it_never_landed`
      and the code-run check's twin, `[late|never]`, failed with no diagnostic line. Live, with the Undo's timer forced
      to 3000 ms from the script: before, both checks failed with nothing more; after, each said its state as
      scheduled (with the front app) and as fired, and "the Undo landed late, 2.9 s after it was scheduled".
    - **Fix:** the add and two-nodes checks are `check_` functions calling `late_undo.after_a_failed_undo` with their
      own predicate (`nodes_gone`), which polls `describe_graph`; their verdict reads stay `NODE_EXISTS`.
    - **Also covered:** the set check goes through the same helper; the add check's `NODE_EXISTS` read after its Redo is
      gone (it ran events inside a job: PLAN.md, the developer's measurements).
  - Questioned by TST-652 (2026-11-20).
  - Questioned by TST-661 (2026-11-21).

- [x] **TST-642 · README says the self-test's scratch folder is deleted once Designer closes: a failed run now keeps it** · `README.md:261` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** "Its files go in a temporary folder (`sd_mcp_selftest_...`), deleted once its Designer has closed."
    `one_run` now keeps it when a check failed or the run raised, and the pool keeps the run's folder and the failed
    workers' Designer folders.
  - **Scenario.** A user reads that nothing is left, while a failed run leaves the scratch folder and, in a pool, about
    90 MB per failed worker's Designer folder.
  - **Fix.** The sentence says what is kept on failure, that the output names it, and that it is deleted by hand once
    read.
  - **Resolution: done**.
    - **Fix:** README's paragraph says a run that passed deletes the folder once its Designer has closed, a run that
      failed keeps it with the pictures its checks saved, and on macOS each failed category's Designer folder (its
      log, about 90 MB); on Windows it is always left; the output names each folder left, to delete by hand. The docs
      tests pass.
  - Questioned by TST-653 (2026-11-20).

- [x] **TST-643 · A "kept" line can name a Designer folder never made, and drops why a forced quit's folder is kept** · `tests/test_all_tools/workers.py:551-552, 571-572` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** `keep |= {port_of[n]: "%s failed, its Designer's folder" % n for n in failed}` names every failed
    worker's `agent_folder(port)`, and `_clean_up` prints it whether or not it exists. The same `|=` overwrites
    "its quit was forced or sampled" for a port in both sets.
  - **Scenario.** A worker whose server fails before `launch_designer` gets "kept, X failed, its Designer's folder:
    <path>" for a folder that isn't there; a failed worker whose quit was forced loses the reason that says its log
    shows how far the quit got.
  - **Fix.** Name the folder only when it exists, else say none, as the scratch line does; join both reasons. Tests for
    a failed worker without a folder and for a port in both sets.
  - **Resolution: done**.
    - **Test:** `test_a_failed_worker_with_no_designers_folder_nor_scratch_is_said_so` failed on a line naming a folder
      that wasn't there; `test_a_failed_worker_whose_quit_was_forced_says_both_why_its_folder_is_kept` failed with one
      reason.
    - **Fix:** one loop builds each port's reasons, joined with `; `, the failure first; `_clean_up` says `none` for a
      folder that doesn't exist.

- [x] **TST-644 · A failed run keeps every passing worker's folder and the unit suite's temp folder too** · `tests/test_all_tools/workers.py:553, 577-578` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** `keep_root=bool(failed)` keeps the whole run's folder, so each passing worker's `root/<name>/` (log,
    results, snapshots, `tmp`) and `root/unit/` (the unit suite's `pytest-of-*` temp) stay. The claim: "Passing workers
    are cleaned as now"; the docstring: "A passing worker's are removed".
  - **Scenario.** Step 2's stress runs fail on purpose, run after run, and each keeps everything of its passing
    workers beside the failed one's evidence.
  - **Fix.** With `keep_root`, remove each passing worker's folder, and `unit/` unless the unit suite failed; the
    docstring says what stays.
  - **Resolution: done**.
    - **Test:** `test_a_failed_workers_scratch_and_designers_folders_are_kept_and_named` (4 cases) failed on
      `sorted(os.listdir(root)) == ['render']`; new `test_a_failed_unit_suite_alone_keeps_its_folder_in_the_runs`.
    - **Fix:** `_clean_up(root, chosen, keep, evidence)` removes everything in the run's folder but the evidence: the
      failed workers' folders, and the unit suite's whenever it failed, alone included; it says
      `the run's folder kept, with only the folders of what failed: <root> (render, unit)`. The docstring says so.
  - Questioned by TST-653 (2026-11-20).
  - Questioned by TST-654 (2026-11-20).

- [x] **TST-645 · The pool's tests don't tie the worker's scratch to where the pool looks for it** · `tests/unit/test_selftest_pool.py:659-690, 851-880` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** The one-run tests fake `tempfile.mkdtemp` with `lambda prefix: str(scratch)` and never check
    `prefix == SCRATCH_PREFIX` or that the folder is under the worker's `TMPDIR`; the pool test builds
    `root/render/tmp/sd_mcp_selftest_x` by hand. The scratch line's `or 'none'` branch, and a passing worker not listed
    as kept, are untested.
  - **Scenario.** A change of the prefix or of where the worker's scratch goes passes every test, and the pool then says
    "its scratch folder: none" for a failure whose shots are elsewhere.
  - **Fix.** The one-run test asserts the prefix and the `TMPDIR`; the pool test covers a failed worker with no scratch
    and asserts no "kept" line for a passing one.
  - **Resolution: done**.
    - **Test:** the one-run test uses the real `mkdtemp` under a `TMPDIR` it sets and asserts the parent and
      `SCRATCH_PREFIX`; the pool test makes the scratch in the worker env's `TMPDIR` (`workers.envs`) with the prefix
      and asserts no "kept" line for a passing worker; the `none` branch is TST-643's test. A coverage gap, no bug: both
      passed before any change, and two mutations fail them (`mkdtemp(prefix='sd_mcp_x_')` in `one_run`; the pool
      globbing `folder_of[name]` in place of `temp_folder(...)`).

- [x] **TST-646 · After a late Undo, the check's Redo applies the set again, and the repair puts back only the identifier** · `tests/test_all_tools/undo/checks.py:105-108` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** On failure the check now waits up to 10 s for a late Undo (`say_how_the_undo_went`), then sends a Redo
    whatever it saw. Once the Undo has landed, Redo is enabled (the add check's "Redo restores it" passes on it) and
    re-applies `identifier='undo_me' label='Undo' usage='roughness'`; the repair then sets only `identifier='height'`.
    Before the change, the Redo went at once, found nothing to redo, and the late Undo set the fields back.
  - **Scenario.** A run where the Undo lands late leaves the output labelled `Undo` with usage `roughness` for the
    rest of the category.
  - **Fix.** `say_how_the_undo_went` returns whether the Undo landed; the Redo goes only when it didn't; the repair
    puts back the label and the usage too.
  - **Resolution: done**.
    - **Test:** `test_an_undo_that_lands_late_is_said_and_never_redone` failed with a Redo among the calls;
      `test_an_undo_at_once_passes_with_no_diagnostic` failed on an `apply_edits` repair; new
      `test_designer_scripts.py::test_undos_output_is_put_back_as_its_preparation_made_it`. Live, a late Undo forced,
      a probe after the set check read `identifier='height' label='Undo' usage=roughness` before the fix and
      `identifier='height' usage=none`, as prepared, after.
    - **Fix:** `after_a_failed_undo` sends the Redo only when the Undo never landed; the repair is
      `undo/designer_scripts/as_prepared.py` (identifier `height`, empty label and usages, which `apply_edits` can't
      clear), raising on a missing node.
    - **Also covered:** the add and two-nodes checks follow the same rule through the same helper.
  - Note (2026-11-21): `put_back`'s Redo is not read back, and `as_prepared` or the delete follows at once. An Undo
    landing after `LANDING_S`, or a Redo landing late, can re-apply the set after the repair. Its docstring's "hit some
    other step" may be "did nothing, or is still pending". `undo` runs last, and nothing reads that state after it.

- [x] **TST-647 · "never fired" says more than the read shows** · `tests/test_all_tools/undo/late_undo.py:35-37` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** `'never fired' if said == 'None'`: `None` means the action hadn't fired when `FIRED` was read, about
    `LATE_UNDO_S` after it was scheduled. It may fire later and undo a later step.
  - **Scenario.** The next diagnosis reads "never fired" as the cause, where the evidence is "not yet, 10 s on".
  - **Fix.** "hadn't fired when read, N s after it was scheduled".
  - **Resolution: done**.
    - **Test:** `test_an_undo_that_never_lands_is_said_then_redone` failed on its regex.
    - **Fix:** "the Edit menu's action hadn't fired when read, N s after it was scheduled". Live, in an earlier late
      run, the add check's late timer, never waited for by the old code, fired in the next check and undid the set
      check's step: the finding's scenario.

- [x] **TST-648 · `late_undo.py` has no unit test** · `tests/test_all_tools/undo/late_undo.py:22-41` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** `say_how_the_undo_went` branches on a late landing, none, the `FIRED` read (`None`, a state, not read)
    and a missing `AT_SCHEDULE`; `fields_back` and the order (the diagnostic before the Redo) are untested. Pure
    Python on the MCP client's side, which AGENTS.md gives a unit test (`git grep -i undo tests/unit` finds none of it).
  - **Scenario.** A change that moves the Redo above the diagnostic, or breaks a branch, passes every test.
  - **Fix.** Unit tests with a fake call returning scripted `describe_graph` texts, `time.monotonic` and
    `asyncio.sleep` patched (as `tests/unit/test_selftest_renders.py`'s `_shots_in_turn` does).
  - **Resolution: done**.
    - **Test:** new `tests/unit/test_selftest_undo.py`, 8 tests on a fake Designer whose reads follow a script, with
      `time.monotonic` and `asyncio.sleep` patched (`_shots_in_turn`'s way): late, never and at once, the order (the
      diagnostic before the Redo and the repair), "not said" and "not read".

- [x] **TST-649 · The Undo's diagnostic says whether Designer is active, not which app is** · `tests/test_all_tools/common.py:257-261` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** Step 1's claim: "prints the state at the trigger: the active app, `activeWindow()`, `focusWindow()`".
    `_state()` prints `QGuiApplication.applicationState().name`, Designer's own Active or Inactive, so the app in
    front, which the snippet's comment and GUIDE.md give as the cause, isn't named.
  - **Scenario.** The Undo fails with Designer inactive; the output can't say whether another Designer, the terminal
    or Finder was in front.
  - **Fix.** Add the frontmost app's name and process id as macOS reports it, beside Designer's own state.
  - **Resolution: done**.
    - **Test:** `test_undo_and_redo_keep_designers_state_as_scheduled_and_as_fired` (2 cases) failed on the old
      snippet.
    - **Fix:** `_front()` runs `lsappinfo front`, then `info -only name -only pid`, and adds
      `front=<name> (<pid>) designer=<pid>` to the state as scheduled (live: `front=PyCharm (1949) designer=56661`).
      Not as the action fires: there it kept the Undo from landing (TST-650).

- [x] **TST-650 · The Undo's diagnostic runs `lsappinfo` inside the job that schedules the Undo** · `tests/test_all_tools/common.py:269-298` · confirmed · found 2026-11-20 by the developer (Opus)
  - **Defect.** TST-649's fix reads the front app with two `subprocess.run(['lsappinfo', ...])` calls in `UNDO_REDO`,
    as the Undo is scheduled. The snippet's own comment (`common.py:248`) records that the same calls in the timer's
    callback, before or after the trigger, kept the Undo from landing (all 6 Undos of an unforced run, measured by the
    developer). At schedule time one unforced run passed: whether it never matters is unmeasured.
  - **Scenario.** A diagnostic added to explain the Undo's random failure changes, now and then, whether the Undo
    lands, in every run: the test is no longer the one it diagnoses (the branch's rule 8).
  - **Fix.** Nothing extra runs in Designer around the Undo: the front app is read from outside Designer, by the
    self-test's client (`window_server`, which reads it already), as the Undo is scheduled and as the check reads its
    result.
  - Note (2026-11-20): the second review: `_front()` runs for the Redo too, each `lsappinfo` with a 5 s timeout on
    Designer's main thread, inside the job; and its failure branch (`front=unread (...)`) has no test. Both go with
    the fix.
  - **Resolution: done**.
    - **Test:** `test_undo_and_redo_keep_designers_state_as_scheduled_and_as_fired` asserts no `subprocess` and no
      `lsappinfo` in `UNDO_REDO`, and failed first on it; new `test_the_app_in_front_is_read_by_the_self_test` (4
      cases: an app, the executable named, an app that has quit, `lsappinfo` unable to tell) and
      `test_a_state_not_said_is_said_so` (off macOS).
    - **Fix:** `_front()` is gone from `UNDO_REDO`, for the Undo and the Redo. Each Undo check starts a `FrontRead()`
      (`late_undo.py`: `window_server.active_app()` on a thread of the self-test's own, joined only when a failure is
      said) just before its `UNDO_REDO` call and another just before its verdict's read. A first version with
      `FrontWatch` sampled every 50 ms with a window list and `ps` runs as the Undo was scheduled; `/simplify` replaced
      it. Live: unforced, the three checks and the whole category pass; with a late Undo forced, each says
      "the app in front, as macOS said it: pycharm (1949) as the Undo was scheduled, pycharm (1949) as the check read
      it; Designer's process 68538" and that it landed late.

- [x] **TST-652 · `nodes_gone` takes a failed `describe_graph` for an Undo that landed** · `tests/test_all_tools/undo/late_undo.py:25-27` · confirmed · follows TST-641, generation 2 · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** `lambda described: not set(ids) & set(positions(described))`: an error reply has no node lines, so
    the predicate is true on it.
  - **Scenario.** Under the load these diagnostics are for, a `describe_graph` poll fails; the add or two-nodes check
    then prints "the Undo landed late, 0.1 s after it was scheduled" and sends no Redo, a wrong lead for the next
    diagnosis. `fields_back` can't misread it: an error text is false for it.
  - **Fix.** The predicate also requires `describe_graph`'s header (`graph ...`, as `describe.py` prints it); a unit
    test feeds it an error text.
  - **Resolution: done**.
    - **Test:** `test_a_graph_that_couldnt_be_described_is_no_undo_that_landed`: the add check, its polls returning
      error results, must say the Undo didn't land and send the Redo; it fails when `not described.is_error and` is
      dropped.
    - **Fix:** the poll skips a failed read by `CallToolResult.is_error` (`prepared_call`'s idiom), in place of a
      check of `describe_graph`'s header, which would tie it to `describe.py`'s format.
    - **Also covered:** `fields_back` was false on an error already; the verdict reads: TST-655.

- [x] **TST-653 · README and the pool's docstring say a failed run keeps and names its folders, which two cases don't** · `README.md:261-266` · confirmed · follows TST-642 and TST-644, generation 2 · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** "A run that failed keeps it ... The output names each folder it leaves" and "The run's folder is kept
    when anything failed, holding only the folders of what failed" (`workers.py:28-31`). A run failed only by a
    pool-level check (`check_the_quits`, `check_the_preferences`, a tool never exercised) has an empty `evidence` and
    removes the run's folder; with a Designer of the run still running, `if left:` keeps the whole folder, passing
    workers' included, and names only the ports.
  - **Scenario.** A reader looks for a failed run's folder that was never kept, or reads "only what failed" over a
    folder holding everything.
  - **Fix.** Generation 2: narrow both sentences to what is kept: when a worker or the unit suite failed, and all of
    it while a Designer of the run may still run, its ports named.
  - **Resolution: done**.
    - **Fix:** README: the folder is deleted once its Designer has closed unless a category failed (a check failed, or
      its run broke off), then what is kept, Windows always leaving it, and the output naming each folder it keeps.
      `workers.py`'s bullet: a failed worker or unit suite keeps the run's folder with only their folders; a run failed
      only by the parent's own checks removes it; while a Designer of the run may still run, all of it is kept and its
      ports named. The docs tests pass.
  - Questioned by TST-660 (2026-11-21).

- [x] **TST-654 · The removal of the launch lock's file from a kept run's folder is never tested, and the test's message claims it** · `tests/test_all_tools/workers.py:593-594` · confirmed · follows TST-644, generation 2 · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** `else:  # the launch lock's file` / `os.remove(path)` is reached by no test: the fake pool never makes
    `launch.lock` (`Gate(root)` makes only `changing/`), yet `test_selftest_pool.py:699`'s message ends "the lock".
    Replacing `os.remove(path)` with `pass` leaves every test green. It is also the one removal there not guarded
    (`ignore_errors`, `suppress`).
  - **Scenario.** A worker killed while holding the lock with `own=None` leaves `launch.lock`
    (`Gate.worker_ended` removes it only for its holder); a change that stops removing it, or a removal that raises
    after the summary, goes unseen.
  - **Fix.** The test writes `root/launch.lock` and asserts it is gone; the removal is guarded as the others are.
  - **Resolution: done**.
    - **Test:** `test_a_kept_runs_folder_loses_the_launch_locks_file[removed|its removal fails]` writes
      `root/launch.lock`; "its removal fails" (a `PermissionError`) failed first, escaping `run_pool`; "removed" fails
      on the finding's mutation.
    - **Fix:** `with contextlib.suppress(OSError): os.remove(path)`; the older test's message no longer claims the lock.

- [x] **TST-655 · "One Undo reverts the whole run" passes when its reads fail** · `tests/test_all_tools/undo/checks.py:106-119` · confirmed · found 2026-11-20 by the developer (Opus)
  - **Defect.** `present()` returns `'EXISTS=True' in text(...)` for each node; an error reply has no `EXISTS=True`, so
    two failed reads give `[False, False]` and `check(..., not any(states), ...)` passes.
  - **Scenario.** Under load both `NODE_EXISTS` jobs fail, and the check says the Undo reverted the run, which it
    didn't show (the branch's rule 8: the test tests what it says).
  - **Fix.** Each read is a state read or a failure: an error reply fails the check, naming it. With the lean plan's
    Undo fix, which reads the graph with `describe_graph` in place of `NODE_EXISTS`.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_selftest_undo.py`, rewritten: an error read passing failed first, with 18 other tests
      for the old flow's reasons (the verdict taken at the first read, no resend, skips where failures belong). Live:
      the `undo` category passed 30 of 30, each run in a Designer just started (180 verdicts, none skipped, nothing sent
      twice). Forced: a late Undo passes where HEAD failed, an action that never fired passes on the second send, and
      an action that does nothing fails naming it.
    - **Cause:** `present()` took an error reply for "absent", so failed reads passed as a reverted run.
    - **Fix:** the checks await `undo/edit_menu.py`'s `send`, which reads the graph with `describe_graph` until it
      shows the Undo, `LANDING_S` at most, a safety net. An error reply fails the check, naming it. It resends only an
      action `UNDO_FIRED` says never fired, `SENDS` times at most; a fired action that never showed fails, named.
    - **Also covered:** the add and set checks read the same way; `NODE_EXISTS` is removed, as nothing uses it;
      `NOT_FOCUSED` and `NO_ACTION` fail instead of skipping (the branch's rule 8); the set check fails when its set
      wasn't applied, sending no Undo. GUIDE.md's Undo recipe now reads the result in later calls until it shows.
  - Questioned by TST-658 (2026-11-21).
  - Note (2026-11-21): `send` returns at a failed read and leaves the action armed until the next send arms its own;
    if it fires late, it can undo a later step, and `put_back` sends no Redo for it. It shows only in a run already
    failing, and `undo` runs last.

- [x] **HLP-208 · view3d.py's new wheel facts have no "designer facts" check** · `mcp_server/designer_helpers/view3d.py:14-28` · confirmed · found 2026-11-21 by the developer (Opus)
  - **Defect.** The module docstring states Designer facts the zoom's code relies on: one event of several notches is
    taken as one notch; notches sent back to back are dropped; nothing says a notch was dropped; no state of the 3D
    dock but the overlay's count moves with a notch. No live check re-measures them: `wheel_step.py` drives the graph
    view, not the 3D view. AGENTS.md: "A claim in these docs without a test is a guess: test it or remove it."
  - **Scenario.** A Designer update takes a multi-notch event whole, or stops dropping notches sent back to back. The
    docstring and the one-event-per-notch design stay as they are, and nothing fails.
  - **Fix.** A "designer facts" check for each fact the code relies on, or the claim narrowed or removed.
  - **Resolution: done**.
    - **Test:** `check_the_3d_views_wheel_takes_one_notch_an_event_and_drops_those_back_to_back`
      (`editor_panels_and_fit/checks.py`, its snippet `window_states.wheel_facts`). It sends 6 notches three ways, on
      screen and hidden, each from the view at rest: one event, back to back, and by the shot's own `_wheel`. It
      judges each by the plane's width against the start's. Expecting back to back to take all six, it failed for
      that reason ("back: 1 / 1" against 6); it passed 3 of 3 on the final code. A case not at rest, or not hidden,
      fails it.
    - **Fix:** the check re-measures the three facts the code relies on: one event is one notch; back to back, one
      step; `sendEvent` True and `isAccepted()` False for each event, taken or dropped. The dock-state search is no
      longer claimed in view3d.py's docstring, which names the check.
  - Questioned by HLP-213 (2026-11-21).

- [x] **HLP-209 · With the GPU Pathtracer, a count past SAMPLES reads as "at rest" while the view accumulates on** · `mcp_server/designer_helpers/frames3d.py:272-276` · confirmed · found 2026-11-21 by the developer (Opus)
  - **Defect.** `_resting` returns `count >= SAMPLES`, and its docstring says that means "the view drew its
    accumulation's last frame". The module docstring says the GPU Pathtracer counts on (frames3d.py:32: 143 samples
    after 6 s). With it, the view counts as at rest mid-accumulation, so `from_rest`'s "neither can be left over by a
    step before" doesn't hold there, and nothing says so.
  - **Scenario.** A 3D view on the GPU Pathtracer goes off screen mid-zoom. A notch is sent with an accumulation's
    request in flight, as in the lost run 52, and its wait can take that request for its sign, which the docstrings
    say can't happen.
  - **Fix.** The docstrings (`_resting`, `from_rest`, the module's, view3d.py's) say what holds with a count past
    SAMPLES, as they do for no count. No new mechanism: the lean plan (the user, 2026-11-20).
  - **Resolution: done**, docstrings only.
    - **Fix:** `_resting`, `from_rest`, frames3d.py's module docstring and view3d.py's say, from the code, that with a
      count past SAMPLES the view reads as at rest while it accumulates. On screen, a dropped notch shows no restart,
      so its wait runs to its net and the moves stop, said. Off screen, a notch can take a left-over request for its
      sign, as with no count. view3d.py's says neither was measured.

- [x] **TST-656 · `SOLO`'s comment gives a cause the 2026-11-20 failure didn't have** · `tests/test_all_tools/categories.py:63-65` · confirmed · found 2026-11-21 by the developer (Opus)
  - **Defect.** The comment says `undo` runs alone because beside other Designers Undo of an output's fields failed,
    until the window was raised first. In the 2026-11-20 final check, the set check failed with `undo` run last and
    alone, no other Designer running. The comment says neither that, nor that `undo/edit_menu.py`'s reads are what
    now handle a late Undo.
  - **Scenario.** A reader takes `SOLO` for the Undo's fix, and drops or weakens `edit_menu.py`'s reads.
  - **Fix.** The comment adds the failure alone and points to `edit_menu.py`. `SOLO` stays: whether `undo` still needs
    it wasn't measured.
  - **Resolution: done**, a comment only: `categories.py`'s comment adds that the 2026-11-20 final check's Undo failed
    with `undo` run last and alone, that `undo/edit_menu.py` now reads an Undo back until the graph shows it, and
    that whether `undo` still needs to run alone wasn't measured.

- [x] **TST-658 · README and `__main__`'s docstring describe the Undo checks' old flow** · `README.md:266-267`, `tests/test_all_tools/__main__.py:15-17` · confirmed · follows TST-655, generation 2 · found 2026-11-21 by two reviewers (Opus, Opus)
  - **Defect.** README: "it triggers Undo and Redo, but only while its own graph is the one in the editor; it skips
    that check otherwise". `__main__`: "checks that exactly its own step was undone, and redoes at once if not". Now
    `NOT_FOCUSED` and `NO_ACTION` fail the check, naming the state (`edit_menu.send`), and a Redo follows only an
    Undo that fired and never showed (`put_back`).
  - **Scenario.** On Windows the self-test runs in the user's Designer. They switch the editor to another graph
    during `undo` and get "FAIL ... not scheduled: NOT_FOCUSED current=<their graph>", where README promised a skip.
  - **Fix.** Both say what the checks do now: a check fails, naming the graph in the editor, when its own isn't; it
    reads the graph until its step shows undone; an Undo that fired and never showed is redone.
  - **Resolution: done**, docs only. README now says the check triggers Undo through the Edit menu and reads the
    graph until the step shows undone, then Redo the same way; it fails, naming the graph in the editor, when its own
    isn't the one there; an Undo that fired and never showed is redone. `__main__`'s docstring says the same.

- [x] **TST-659 · A category failed only by its quit check loses its Designer's folder, with the log** · `tests/test_all_tools/workers.py:288-292, 555-562` · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `run_pool` keeps a Designer's folder when its worker's exit code isn't 0, or when `_quit_to_keep`
    finds "forced" or a sample in the quit's reply. The parent's quit check (`check_the_quits`) also fails a quit
    whose reply `closed_by_quit` rejects, such as "No Designer is running on port N.", and that case keeps nothing.
  - **Scenario.** `render` passes every check, so its worker exits 0. Its Designer then dies before the quit, killed
    under the load of four Designers, with no crash dump. The quit check fails; `_clean_up` removes the Designer's
    folder and the run's folder, and the log that would explain it goes too, against the branch's rule 5.
  - **Fix.** Keep the Designer's folder of every category whose quit check failed, with that reason; the pool's
    docstring says so. A fake-pool unit test, a passing worker whose quit reply is "No Designer is running on port
    N.", fails first.
  - **Resolution: done**.
    - **Test:** `test_a_passing_workers_failed_quit_keeps_its_designers_folder` (`tests/unit/test_selftest_pool.py`)
      failed first: nothing kept.
    - **Cause:** the pool kept a Designer's folder for a failed worker or a forced or sampled quit, never for a failed
      quit check.
    - **Fix:** `check_the_quits` returns the categories whose quit check failed, and `run_pool` keeps their Designers'
      folders ("its quit check failed"); the pool's docstring says so. The crash-dump branch with no results adds to
      that set too.
  - Questioned by TST-670 (2026-11-21).

- [x] **TST-660 · README says a failed category keeps its scratch folder; one failed only by its quit check keeps none** · `README.md:261-263` · confirmed · follows TST-653, generation 3 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** README: "unless a category failed: one of its checks failed, or its run broke off. Then the folder
    is kept, with the pictures its checks saved". A category's quit check (the pool's docstring calls it so) is made
    by the parent after the worker deleted its scratch folder; `workers.py:30-31` says so.
  - **Scenario.** `render`'s quit fails in the parent; README says its pictures were kept, and none were.
  - **Fix.** Generation 3: narrow the sentence, no new check. "unless one of the checks its run made failed, or its
    run broke off", and with TST-659, that a failed quit check keeps the Designer's folder.
  - **Resolution: done**, the claim narrowed (generation 3). README: "unless one of the checks its run made failed, or
    its run broke off", and "A category whose quit check failed keeps its Designer's folder too."
  - Questioned by TST-669 (2026-11-21).

- [x] **TST-661 · No test checks the add and code-run Undo checks' failure diagnostics any more** · `tests/unit/test_selftest_undo.py` · confirmed · follows TST-641, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** TST-641's tests went with TST-655's rewrite. The diagnostic lines (`_said(out)`) are asserted for the
    set check only; for add and code run, `test_a_read_that_failed_fails_the_check_naming_it` asserts the verdict
    line alone.
  - **Scenario.** The add check is changed to `check('apply_edits', name, undo.shown is not None, undo.detail())` in
    place of `recorded(...)`. Its diagnostics disappear and every test passes.
  - **Fix.** Assert the diagnostics for the add and code-run checks too, for example in a "fired and never showed"
    case of each.
  - **Resolution: done**, a test only. `test_the_add_and_code_run_checks_say_why_an_undo_that_fired_never_showed`
    asserts the diagnostics for add and the code run. It passes on today's code, and failed on a copy of
    `undo/checks.py` with `recorded()` replaced by `check()`, the finding's mutation.

- [x] **TST-662 · A failure after a resend doesn't say an earlier send never fired** · `tests/test_all_tools/undo/edit_menu.py:110-126` · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `Sent.detail` gives the count of sends only when the graph showed the step, or when the last action
    never fired. A refusal, a failed read, a read that said nothing, and a fired action that never showed drop it.
  - **Scenario.** Send 1 never fires and is disarmed after 10 s; send 2 fires and never shows. The FAIL reads as one
    send, and the evidence that Designer's zero timer didn't run for 10 s is lost (rules 5 and 8).
  - **Fix.** The detail, or `say()`, gives the count of sends whenever it is more than one.
  - **Resolution: done**.
    - **Test:** `test_a_failure_after_a_resend_says_how_many_sends` failed first: no "sent 2 times" in the line.
    - **Fix:** `Sent.detail` puts the count of sends first, within the 150 characters `common.check` keeps; `_why()`
      holds the other texts.
    - **Also covered:** a resend that was refused, or whose read failed, says why rather than "never fired"
      (`test_a_resend_that_failed_says_why_and_how_many_sends`, red on the developer's first version).
  - Questioned by TST-667 (2026-11-21).
  - Questioned by TST-668 (2026-11-21).
  - Questioned by TST-685 (2026-11-21).

- [x] **TST-663 · `Sent.which` and `send`'s `which` are typed `str` where `Literal['Undo', 'Redo']` fits** · `tests/test_all_tools/undo/edit_menu.py:96, 159` · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `which: str  # 'Undo' or 'Redo'`. `.claude/rules/python.md`: the most specific type that fits.
  - **Scenario.** A misspelt `which` passes mypy and yields `NO_ACTION ... menus: none` at run time.
  - **Fix.** `Literal['Undo', 'Redo']` for both.
  - **Resolution: done**. `Which = Literal['Undo', 'Redo']` types `Sent.which` and `send`;
    `test_which_is_undo_or_redo` failed first (`<class 'str'>`).

- [x] **HLP-212 · A zoom whose first notch isn't sent still says the set-up moved the camera** · `mcp_server/designer_helpers/view3d.py:1128`, `shot3d.py:412-423` · measured · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `changed = True  # moving: a drag or a wheel step follows` is set before the moves, and stays True
    when `_wheel` sends none. `shoot_3d` then retakes the render and, with it identical to the one before, prints
    STALE: "identical to the render before the set-up, though the set-up moved the camera ...".
  - **Scenario.** Measured with HLP-211's probe: Samples 4, and antialiasing off, each printed "wheel step 1 of 2
    not sent" and then the STALE line, which contradicts it.
  - **Fix.** `changed` is set only once a move was sent.
  - **Resolution: done**.
    - **Test:** `test_a_set_up_whose_moves_sent_none_changed_nothing[none sent]` (`tests/unit/test_view3d_helpers.py`)
      failed first: `True is False`.
    - **Fix:** `changed` is recorded where a move is sent: a drag given, or a wheel step whose rest gave its wait.

- [x] **TST-664 · The zoom check, on failure, doesn't print the tool's own lines** · `tests/test_all_tools/editor_panels_and_fit/checks.py:1694-1725` · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The tool's reply `t` holds the "3D view: +6 wheel steps (...)" line and the marks (painted before the
    hide, at rest at the hide), and the undisturbed shot's `said` its own; on failure the check prints neither, nor
    the `_after.png` renders its docstring says it prints.
  - **Scenario.** A run fails with "the plane 1.37x": whether the tool stopped the zoom and said why, or lost a step
    silently, can't be told (rules 5 and 7). The wheel facts check drops its re-framing calls' results the same way.
  - **Fix.** On failure, print the tool's `3D view:` and mark lines, and pass the `_after` renders to `say_renders`.
  - **Resolution: done**.
    - **Test:** `test_a_failed_zoom_check_prints_the_tools_lines_and_the_plain_shot_after` failed first: the stop line
      wasn't printed.
    - **Fix:** on a failure, the zoom check prints the tool's `3D view:` lines and the case's marks, and passes the
      `_after` render to `say_renders`.
  - Questioned by TST-672 (2026-11-21).
  - Questioned by TST-688 (2026-11-21).
  - Questioned by TST-689 (2026-11-21).

- [x] **TST-665 · The wheel facts check's event detail is cut at 150 characters** · `tests/test_all_tools/editor_panels_and_fit/checks.py:1806` · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `'each event: %s' % ','.join(sent)` is 165 characters for its 14 events, and `common.check` cuts a
    detail at 150. Both full runs of 2026-11-21 printed it ending "True/F".
  - **Scenario.** The 14th event differs, or a 15th comes: the FAIL line looks like a passing list cut short.
  - **Fix.** On failure, print the events on a line of their own, or give their count and the ones that differ.
  - **Resolution: done**.
    - **Test:** `test_a_failed_wheel_facts_check_says_which_event_differed` failed first: the differing event was cut.
    - **Fix:** the detail gives the count of events and of True/False, and the others; a failure prints the whole
      list on a line of its own. The developer proposes, outside this branch's cause, a ROADMAP item: `common.check`
      cutting every detail at 150 characters, which findings reshape one by one (TST-312, TST-334, TST-361, TST-662,
      TST-665).

- [x] **HLP-213 · view3d.py's docstring states away-direction wheel facts the facts check doesn't re-measure** · `mcp_server/designer_helpers/view3d.py:14-21` · confirmed · follows HLP-208, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "One event carrying several notches (angleDelta 6 x 120, or -3 x 120) is taken as one notch", and the
    sentence after it says the self-test's wheel facts check re-measures the one event and the notches back to back.
    The check sends closer notches only (`window_states._WHEEL_FACTS`).
  - **Scenario.** A Designer update takes -3 x 120 whole; nothing fails, and the sentence still reads as re-measured.
  - **Fix.** Say the check re-measures the closer direction, and that the away facts were measured once, with the
    date; or add an away case.
  - **Resolution: done**, the claim narrowed (generation 2). view3d.py's docstring says the check re-measures the
    closer direction, and that the away event (-3 x 120) was measured once, on 2026-11-20.

- [x] **TST-666 · The zoom check drops `with_checker`'s result, so a plane without edges goes unseen** · `tests/test_all_tools/editor_panels_and_fit/checks.py:1655` · confirmed · follows HLP-210, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `await with_checker(c, {**start, 'graph': VIEW3D_GRAPH})` ignores the shot it returns, which may be
    without the checker when its retakes end (`RETAKE_S`). Every other caller reads it.
  - **Scenario.** The checker never shows; the zoom and its plain shots are compared on a plain plane, where an
    unsettled render reads 0.00 (HLP-210), and the check passes blind.
  - **Fix.** The zoom check fails, naming the cause, when the result isn't an image showing the checker
    (`transitions(grey(r)) < CHECKER`, as the other callers test).
  - **Resolution: done**.
    - **Test:** `test_the_zoom_check_fails_when_the_checker_never_showed` failed first: three PASS lines.
    - **Fix:** the checker is checked on the start's render, a file `shoot_3d` saved, as the TST-423 and TST-651 guard
      requires; without it, the three verdicts fail and no zoom is sent.

- [x] **HLP-214 · The settle after a step takes its wait's end for success** · `mcp_server/designer_helpers/frames3d.py:340-341, 353-354, 369` · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `_Frames.settled`, `moved` and `shown` drop the results of their waits, SETTLE_LIMIT at most, a
    safety net; the render follows whether the count came back or not (rule 3).
  - **Scenario.** Under load, the count isn't back at rest within 3 s after a zoom's last notch. The render is the
    unsettled one HLP-210 measured, and the tool's result says nothing.
  - **Fix.** The waits' results reach the set-up, which says the 3D view hadn't settled within the limit. With
    HLP-211's target, so that a Rasterizer stopping below 8 isn't said unsettled on every shot.
  - **Resolution: done**.
    - **Tests**, each red first: `test_a_settle_says_whether_the_view_settled`, `test_a_turn_says_whether_it_ended`,
      `test_a_show_says_whether_the_view_drew_what_changed` (`test_frames3d.py`); `test_a_step_whose_view_never_settled_says_so`
      (`test_view3d_helpers.py`); `test_a_window_put_back_on_screen_says_when_its_view_never_drew_what_changed`
      (`test_shot3d.py`).
    - **Fix:** `settled`, `moved`, `shown` and `_renders_alike` return whether they ended on their state. A step whose
      wait ended at its limit says " (the 3D view hadn't settled within 3 s after it)": mesh, graph, view and Frame,
      the moves, tiling, environment. `shoot_3d` prints "3D render: the 3D view hadn't settled within 3 s after
      Designer's window came back on screen" when `shown` didn't end on its state. The tool's docstring says so.
  - Questioned by TST-673 (2026-11-21).
  - Questioned by TST-678 (2026-11-21).
  - Questioned by HLP-222 (2026-11-21).

- [x] **HLP-216 · Two Rasterizer settings the shot doesn't read are left undocumented** · `mcp_server/designer_helpers/frames3d.py:33-34, 295-300, 383-384, 401-402` · confirmed · follows HLP-211, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** With the Rasterizer's Samples above 8, `_resting` reads the view as at rest at 8, so a render is taken
    mid-accumulation, while the docstrings say the Rasterizer's count at rest is its Samples. With antialiasing off,
    the count stays at 1, so `_restarts` (a count below the one before) never sees a step's restart: `settled` and
    `moved` end at NO_RESTART as if the step changed nothing, and a viewpoint's turn can be cut.
  - **Scenario.** Samples 16: every shot renders at a count near 8, less refined than the view at rest, and differs
    run to run. Antialiasing off: `shoot_3d(p, view='Left')` renders before the turn ended.
  - **Fix.** No new mechanism (HLP-215's decision): the docstrings state both limits, as HLP-209's do for the GPU
    Pathtracer, and claim nothing measured that wasn't.
  - **Resolution: done**, docstrings only: frames3d.py says that with Samples above 8 a count going on past 8 reads
    as at rest at 8, the render taken mid-accumulation, and that with antialiasing off no restart shows, so `settled`
    and `moved` end at NO_RESTART as if nothing changed; both marked not measured.
  - Questioned by HLP-217 (2026-11-21).

- [x] **TST-667 · After a resend, the Undo's failure lines print the first send's "hadn't fired" with the last send's** · `tests/test_all_tools/undo/edit_menu.py:195-202, 160-163` · confirmed · follows TST-662, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `fired`, `fired_said` and `fired_read` aren't reset when a send starts; when send 2 returns early (its
    read failed), `say()` prints send 1's "the Edit menu's action hadn't fired when read, 10.0 s after it was
    scheduled" among send 2's lines.
  - **Scenario.** Send 1 never fires; send 2's `describe_graph` fails: the output says send 2's action hadn't fired,
    a read that was never made (rule 5).
  - **Fix.** Reset those fields at each send, and assert `_said(out)` in
    `test_a_resend_that_failed_says_why_and_how_many_sends`.
  - **Resolution: done**. `test_a_resend_that_failed_says_why_and_how_many_sends` asserts what `say()` prints and
    failed first (send 1's "hadn't fired" printed). `Sent.begin_send()` resets `fired`, `fired_said` and
    `fired_read` at each send.

- [x] **TST-668 · No test covers a resend that is refused** · `tests/test_all_tools/undo/edit_menu.py:120` · confirmed · follows TST-662, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `if self.fired is False and not (self.refused or self.error)`: changing it to `not self.error` passes
    every test, since the fake answers every Undo alike.
  - **Scenario.** Send 1 never fires, then send 2 gets `NOT_FOCUSED`: with that change, the FAIL reads "never fired,
    sent 2 times" and drops the state Designer gave.
  - **Fix.** A case where only the second Undo is answered `NOT_FOCUSED current=x`, asserting "sent 2 times, the action
    before never fired; not scheduled: NOT_FOCUSED".
  - **Resolution: done**, a test only: `test_a_resend_refused_says_the_state_designer_gave`, its fake answering each
    Undo in turn. It passes on today's code and failed on the entry's mutation ("never fired, sent 2 times").

- [x] **TST-669 · README's sentence on what a failure keeps reads as the whole run's again** · `README.md:261-263` · confirmed · follows TST-660, generation 4 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "unless one of the checks its run made failed": the paragraph's subject is the self-test, so "its run"
    reads as the whole run, which includes the pool's own checks, and "that category's" refers to nothing.
  - **Scenario.** Only the preferences, the coverage or a quit check fails: README says the pictures were kept, and
    the run's folder was removed (`workers.py:32-33`).
  - **Fix.** Generation 4: narrow the words, no check. "unless one of a category's own checks failed, or its run broke
    off".
  - **Resolution: done**, the words narrowed (generation 4): "unless one of a category's own checks failed, or its
    run broke off".

- [x] **TST-670 · A folder kept for a failed quit check doesn't say whose it is, and `_clean_up`'s docstring leaves the reason out** · `tests/test_all_tools/workers.py:569-572, 580-585` · confirmed · follows TST-659, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The output prints "kept, its quit check failed: /tmp/sd_mcp_<uid>_<port>", and no worker's header or
    quit reply names the port; `_clean_up`'s docstring lists the forced or sampled quits and the failed workers, not
    a failed quit check.
  - **Scenario.** Two categories' quit checks fail in one run: which folder holds whose log can't be told (rule 5).
  - **Fix.** The line names the category ("<name>'s quit check failed", the forced or sampled reason too), and the
    docstring adds the reason.
  - **Resolution: done**. Three assertions now expect "render's quit was forced or sampled" and "render's quit check
    failed", red first. Each kept reason names its category; `_clean_up`'s docstring lists the failed quit check.
    - **Also covered:** `_clean_up`'s other lines, each with a test red first: a folder holding a crash dump ("kept,
      render's folder holds a crash dump") and the folders kept while a Designer may run ("<category>'s (port N)").

- [x] **TST-671 · ROADMAP item 42's amendment names the wrong folders to spare** · `ROADMAP.md`, item 42 · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** Its cleanup deletes `sd_mcp_selftest_*` in the system temp folder, and the amendment named the
    Designer's folder, `/tmp/sd_mcp_<uid>_<port>`, which that glob never matches, and not the run's folder
    (`sd_mcp_selftest_workers_*`), which holds a failing worker's scratch folder and does match.
  - **Scenario.** An implementation sparing only what the item names deletes the run's folder and the evidence in it.
  - **Resolution: done**, by the lead, whose wording it was: the item names the run's folder and what it holds, and
    the Designers' folders, as the user's approval meant (2026-11-21: "its cleanup must spare the folders a failed
    macOS run now keeps on purpose as evidence").

- [x] **TST-672 · The zoom checks still drop their re-framing calls' replies and the tool's "3D render:" lines** · `tests/test_all_tools/editor_panels_and_fit/checks.py:1674, 1695, 1729-1732, 1778, 1869` · confirmed · follows TST-664, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `await c('screenshot_designer', start)` drops the reply where the zoom check and the wheel facts check
    re-frame, which TST-664's scenario named; `_said_by_the_tool` keeps the `3D view:` lines only, so UNDRAWN ("3D
    render: ... hadn't settled") isn't printed on a failure.
  - **Scenario.** A re-framing's zoom -4 stops ("wheel step 2 of 4 not sent"): the case starts closer than its start
    render, and the FAIL shows a wrong ratio with no cause.
  - **Fix.** Keep each re-framing's reply and print its tool lines on a failure; print the "3D render:" lines too.
  - **Resolution: done**. The zoom check's and the wheel facts check's failure tests now include a re-framing that
    stopped short and an UNDRAWN line, red first. Both checks keep each re-framing's reply and print its tool lines
    on a failure; `_said_by_the_tool` keeps the "3D render:" lines. The other checks' re-framings (a view, mesh, tiling
    or graph with no wheel step, no plane width measured from them) still drop their replies.
  - Note (2026-11-21): the zoom check's first framing (`with_checker`) and the wheel facts check's start shot still
    drop their replies on a failed verdict; a start whose zoom -4 stopped short would show only low ratios.

- [x] **TST-673 · HLP-214's test covers the unsettled line for three steps of seven** · `tests/unit/test_view3d_helpers.py:1418-1424` · confirmed · follows HLP-214, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** It makes `settled` return False for the moves, the mesh and the viewpoint only, not the graph step,
    Frame alone, the tiling or the environment's three waits.
  - **Scenario.** `_unsettled` dropped from any of those passes every test.
  - **Fix.** Cases for the graph, Frame alone, the tiling, and the environment with a name and a rotation where only
    the second settle is False.
  - **Resolution: done**, tests only: four cases (a graph's outputs, Frame alone, the tiling, the environment with only
    its second settle False). They pass on today's code; each failed on a copy with its own `_unsettled` dropped.
  - Note (2026-11-21): its cases make only the rotation's settle False; dropping `and settled` from the exposure's
    settle (view3d.py) still passes every test.

- [x] **TST-674 · The random failure's ROADMAP.md row is written after the final check, and its FAIL line breaks the table** · `DECISIONS.md`, `ROADMAP.md`, `.claude/skills/delegate/SKILL.md:87-90` · confirmed · follows the rule of 2026-11-21, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The lead adds the row once the rerun passed, after the final check, while the `delegate` skill puts
    what outlasts the branch in ROADMAP.md before it; and every check line holds a `|`, so a FAIL line pasted in the
    row gives 6 cells against a header of 5, which `test_every_row_of_a_docs_table_has_as_many_cells_as_its_header`
    refuses.
  - **Scenario.** The first time the rule applies, main gets a ROADMAP.md that fails a docs test.
  - **Resolution: done**, by the lead: the row is added after the final check and before the merge, with the docs tests
    run on it, and a `|` in its FAIL line written `\|` (DECISIONS.md, the `live-check` skill, ROADMAP.md's section);
    the `delegate` skill's merge paragraph and `docs/agent-workflow.md`'s step 9 name it.

- [x] **AGT-112 · The `runner` file wasn't updated for the rule** · `.claude/agents/runner.md:18-27, 63-71` · confirmed · follows the rule of 2026-11-21, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** It still said "When the final check fails, report the failures", and its report asked for no rerun
    result nor the folders kept, which the row needs.
  - **Scenario.** A runner following its own file reports the failures without rerunning them.
  - **Resolution: done**, by the lead: the file says to rerun each failing test alone in the same brief, as the
    skill says, and to report each failure's rerun (passed, failed, or not rerun and why) and the folders kept for it.

- [x] **TST-675 · DECISIONS.md's reason for the rule overclaims, and its figure cites no home** · `DECISIONS.md`, the rule's entry · confirmed · follows the rule of 2026-11-21, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "A pass alone says the tool works in a session like the user's", while its own example, a step lost
    in 2 runs of 120 in a quiet Designer, passed 3 of 3 rerun alone; and the figure cites ROADMAP item 112, which
    hasn't it (it is in `designer_helpers/view3d.py`'s docstring).
  - **Scenario.** A reader takes one pass alone as proof the tool works for users.
  - **Resolution: done**, by the lead: "A pass alone shows the failure is rare, or needs the full run's conditions",
    and the figure cites `designer_helpers/view3d.py`, with the condition it was measured in.
  - Questioned by TST-682 (2026-11-21).

- [x] **TST-676 · No docs test keeps the rule's wording in its places** · `tests/unit/test_agents.py` · confirmed · follows the rule of 2026-11-21, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The user's earlier workflow rules each have one (`test_the_users_rules_of_2026_11_20_keep_their_wording`);
    no test reads "at random" in DECISIONS.md, the `live-check` skill, AGENTS.md, `docs/agent-workflow.md`, the
    `runner` file or ROADMAP.md's section.
  - **Scenario.** The skill loses "A test already listed there, or one that fails alone too, is a failure", and every
    test passes.
  - **Fix.** One test asserting the rule's key wording in each place, ROADMAP.md's section with its header row.
  - **Resolution: done**. `test_the_users_rule_on_tests_that_fail_at_random_keeps_its_wording`
    (`tests/unit/test_agents.py`) asserts the rule's wording in DECISIONS.md, the `live-check` skill, the `runner`
    file, AGENTS.md, `docs/agent-workflow.md` and ROADMAP.md's section with its 6-cell header, and that the clauses the
    user dropped are gone. It failed on 9 of 9 copies of the docs each missing one sentence.
  - Note (2026-11-21): its comment said it reads the rule "in each place it is written"; it reads six of the
    seven, not the `delegate` skill's merge sentence, and a few key clauses in each (a reviewer, Opus). The
    comment now says so; no assertion added, at generation 3.

- [x] **TST-677 · The Rasterizer check's put-back guard can no longer fail** · `tests/test_all_tools/editor_panels_and_fit/checks.py:1901-1906` · confirmed · follows HLP-215, generation 3 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `if ' after' in t and ' after' not in back:`: the put-back snippet shows the window while the setting
    is still lowered, so UNDRAWN ("... hadn't settled within 3 s after Designer's window came back on screen") is in
    `back` whether the put-back worked or not.
  - **Scenario.** The put-back raises; no "wasn't put back" FAIL, and the later 3D checks run at Samples 4.
  - **Fix.** Generation 3, mending the guard this round broke: match the snippet's own line
    (`re.search(r'^RASTERIZER .* after', back, re.M)`).
  - **Resolution: done** (generation 3, the guard mended). `test_the_rasterizer_check_fails_when_its_setting_isnt_put_back`
    (`test_selftest_check_setups.py`) failed first: a put-back reply holding UNDRAWN passed. A put-back now counts as
    done only by the defaults' own line (`rasterizer.DEFAULTS_SET`), stricter than the snippet's `after` line, which a
    put-back leaving Samples at 4 still prints. Live, with the put-back forced to fail, both cases said "the setting
    wasn't put back".
  - Questioned by TST-683 (2026-11-21).

- [x] **HLP-217 · frames3d.py's antialiasing-off sentence says more than the code does** · `mcp_server/designer_helpers/frames3d.py:73-75` · confirmed · follows HLP-216, generation 3 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "settled and moved end at NO_RESTART as if the step changed nothing": a watch's first paint, with no
    count before it, counts as a restart, so on a Designer already on screen the first step's settle waits for 8 to
    its limit and says "hadn't settled ..., its sample count at 1", and `moved` isn't cut.
  - **Scenario.** The user's Designer in front, antialiasing off: `screenshot_designer('3d', view='Left')` takes 3 s
    and says unsettled, not "as if the step changed nothing".
  - **Fix.** Generation 3, docs only: "can end at NO_RESTART as if the step changed nothing", or name when.
  - **Resolution: done** (generation 3, docs only): with antialiasing off, only a watch's first paint reads as a
    restart, so the first step of a shot in a Designer already on screen runs to its net and says unsettled, and a
    later step's `settled` and `moved` can end at NO_RESTART as if it changed nothing; marked not measured.

- [x] **TST-678 · `SHOWN_ALREADY`'s wrapper drops `settled()`'s result** · `tests/test_all_tools/editor_panels_and_fit/checks.py:990-993` · confirmed · follows HLP-214, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `def _counted(self, since): _waits.append(since); _settled(self, since)` returns None, where callers
    use the result since HLP-214.
  - **Scenario.** In a failing run (`WAITS > 0`), every wrapped wait reads as unsettled and adds "hadn't settled"
    lines that aren't so (rule 5).
  - **Fix.** Return `_settled(self, since)`, with a test.
  - **Resolution: done**. `test_the_shown_already_checks_count_of_waits_keeps_each_waits_result` failed first
    (`[None, None] == [True, False]`); the wrapper passes its arguments through and returns `settled()`'s result. No
    other wrapper of a `_Frames` wait in `tests/test_all_tools/` drops its result.

- [x] **TST-680 · The Rasterizer check's precondition says "not set" when the set ran** · `tests/test_all_tools/editor_panels_and_fit/checks.py` (the Rasterizer check) · confirmed · found 2026-11-21 by the developer (Opus)
  - **Defect.** "not set, not at Designer's defaults" is said when a case's own value was at its default and its set
    ran, but the other setting was left lowered.
  - **Scenario.** In the forced run, the antialiasing case's set ran while Samples stayed at 4; its line says "not
    set", which sends the reader the wrong way, though its tail shows the after line.
  - **Fix.** The message says what was read: which setting wasn't at its default, and its value.
  - **Resolution: done**. `test_the_rasterizer_checks_precondition_says_which_setting_it_read_off_its_default` failed
    first; `rasterizer.off_defaults(t)` says which setting it read off its default and its value, or that the page
    wasn't read.

- [x] **TST-681 · The Rasterizer check needs the exact count, which a window that left mid-accumulation gives lower** · `tests/test_all_tools/editor_panels_and_fit/checks.py:1885` · confirmed · follows TST-679, generation 2 · found 2026-11-21 by the developer (Opus)
  - **Defect.** The refusal it requires is "... its sample count at %d" with the case's own count (4, or 1). Off
    screen, the tool now gives the count last drawn, which, with the window gone mid-accumulation at Samples 4, can
    truthfully read 1 to 3.
  - **Scenario.** In a full run another Designer covers the window while the view climbs back to 4; the line says
    "at 2 when last drawn", and the check fails though the zoom was refused and the line is true. 13 of 13 runs read
    4 here.
  - **Fix.** Require a count below 8 there, any, with the refusal, no STALE, the plane at 0 steps and the count at the
    render as now; a unit test, red first.
  - **Resolution: done**. `test_the_rasterizer_checks_refusal_takes_any_count_below_8` (`test_selftest_check_setups.py`)
    failed first on a stop line "at 2 when last drawn"; the check reads the stop line's count with a regex and
    requires it below 8, with "(Renderer > Edit settings)". The Rasterizer check and the off-screen run passed once each.

- [x] **AGT-114 · The rule's rerun of a live check refuses off macOS** · `DECISIONS.md`, the rule's entry; `.claude/skills/live-check/SKILL.md`, When the final check fails · confirmed · follows AGT-111, generation 3 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The rerun is `tests/test_all_tools --only <category>`, which refuses off macOS
    (`__main__.py`: "--only runs through the pool, which is macOS only (ROADMAP item 65): nothing run"), while the
    `runner` file still has a final check on Windows.
  - **Scenario.** A Windows final check fails a live check; the runner can't rerun it alone, and no text says what
    that counts as.
  - **Fix.** Generation 3, docs only: say the rerun of a live check is on macOS.
  - **Resolution: done**, by the lead: "on macOS, a live check through the pool with its category alone", and the rule
    doesn't cover a live check off macOS, where `--only` refuses (ROADMAP item 65). In the log for the user.
  - Note (2026-11-21): the user chose a rerun off macOS too ("rerun"): its category alone in a scratch run
    (`alone.run`). In DECISIONS.md and the `live-check` skill, by the lead.
  - Questioned by AGT-119 (2026-11-21).
  - Questioned by AGT-121 (2026-11-21).

- [x] **AGT-115 · DECISIONS.md words the second random failure in the opposite term from the user's** · `DECISIONS.md`, the rule's entry; `tests/unit/test_agents.py` · confirmed · follows the rule of 2026-11-21, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The user: "it counts as failed and is failing counter is increased but no fix is mandatory".
    DECISIONS.md: "again counts as passed too: its count goes up", and the docs test asserts the user's "again counts
    as failed" absent.
  - **Scenario.** The behaviour is the same, the count raised and the merge going ahead, but the record of the
    user's decision reads as the opposite of the user's words.
  - **Fix.** Say what happens, in neither term, as ROADMAP.md's section does.
  - **Resolution: done**, by the lead: "One already listed there that fails at random again has its count raised, and
    the merge goes ahead: it is fixed when ROADMAP.md gets to it". The docs test asserts that sentence, and that
    neither "again counts as passed" nor "again counts as failed" is there.

- [x] **AGT-116 · The `address-review` skill reopens a finding on any full-run failure** · `.claude/skills/address-review/SKILL.md`, step 4 · confirmed · follows the rule of 2026-11-21, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "if the full run the user asks for later shows it failing there, the finding is open again", with no
    exception for a failure that passes rerun alone, which the rule counts as passed.
  - **Scenario.** The final check fails the zoom check guarding a resolved finding, and its category alone passes:
    the `live-check` skill lists it and merges; this step reopens the finding and has it fixed first.
  - **Fix.** "... shows it failing there, and failing alone too (the `live-check` skill, When the final check fails)".
  - **Resolution: done**, by the lead, as the Fix says. **Also covered:** the other texts that send a final check's
    failure to REVIEW.md (the `live-check` skill, the `runner` file, `docs/agent-workflow.md`, the `delegate` skill)
    come after the rerun alone, or name it.
  - Note (2026-11-21): no test guards its clause; the rule's docs test's comment now names step 4 among the
    places it leaves out (a reviewer, Opus; generation 3, no assertion added).

- [x] **AGT-117 · The branch rewrapped about twelve DECISIONS.md entries it doesn't touch** · `DECISIONS.md` · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** A rewrap left about 20 lines of one or two words, and split two possessives off their code spans
    ("`set_link_display`" / "'s", "`expose`" / "'s"), which render as "`set_link_display` 's".
    `.claude/rules/docs.md`: "Don't rewrite untouched text only for its style ... it adds noise to the diff".
  - **Fix.** Revert those hunks.
  - **Resolution: done**, by the lead: DECISIONS.md is `main`'s with the branch's two entries added, the rule's and
    "The 3D shot never sends a wheel step or a drag move again" (`git diff main -- DECISIONS.md`: 24 lines added,
    none removed).

- [x] **AGT-118 · The coverage clause can't be read from an `--only` run's summary** · `DECISIONS.md`, the rule's entry; `.claude/skills/live-check/SKILL.md`, When the final check fails · confirmed · follows AGT-111, generation 3 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "if they pass with checks run for those tools": an `--only` run judges only the tools its checks ran
    (`workers.py`: `tools = sorted(set(tools) & set(common.results))`), so its summary reads "N/N tools covered" and
    never names a tool no check ran for.
  - **Scenario.** The full run says `NOT covered: ['foo']`, as foo's only check is no longer reached; `--only` of its
    category passes with "N/N tools covered", and the failure is listed as random.
  - **Fix.** Generation 3, docs only: name where to read it.
  - **Resolution: done**, by the lead: "Their PASS lines in the rerun's output show those checks ran, as its summary
    leaves out a tool no check ran for", in both texts.

- [x] **TST-682 · The rule's figure says "in a quiet Designer", which its home doesn't** · `DECISIONS.md`, the rule's entry · confirmed · follows TST-675, generation 3 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "2 runs of 120 with the window hidden right after the first step, in a quiet Designer:
    `designer_helpers/view3d.py`": the docstring there has the 2 in 120 and the hiding, not the quiet Designer.
  - **Fix.** Generation 3, docs only: drop the words.
  - **Resolution: done**, by the lead: the words dropped.

- [x] **TST-683 · The Rasterizer check's put-back FAIL blames the case's own setting when only the other is still off** · `tests/test_all_tools/editor_panels_and_fit/checks.py:1909-1912` · confirmed · follows TST-677, generation 4 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `if rasterizer.SET.search(t) and rasterizer.DEFAULTS_SET not in back:` then "the setting wasn't put
    back": `DEFAULTS_SET` needs both settings at their defaults after the put-back, so a case whose own setting was put
    back fails it while the other case's setting is still off. The comment's "each reply holds UNDRAWN" doesn't hold
    for the set's reply `t`: at the defaults, a window back from rest at 8 settles and prints none.
  - **Scenario.** The Samples case's put-back fails and Samples stays at 4. The antialiasing case's set runs, its
    precondition rightly names "Samples 4.0 (8.0 by default)", and its put-back works (`RASTERIZER samples=4.0 aa=True
    after`); the check then also says the antialiasing case's "setting wasn't put back", the same pattern as TST-680.
  - **Fix.** Generation 4: narrow the message and the comment, add no check. The FAIL says what was read after the
    put-back, as `rasterizer.off_defaults` does for the line before ("not at Designer's defaults after the put-back:
    Samples 4.0 (8.0 by default)"); the comment: "a put-back's reply can hold UNDRAWN".
  - **Resolution: done** (generation 4, the message and comment narrowed, no new check), by the developer.
    `test_the_rasterizer_check_fails_when_its_setting_isnt_put_back` (`test_selftest_check_setups.py`), its
    expectations rewritten, failed on the old message. `rasterizer.off_defaults(said, when)` reads the before or
    after line and names each setting off its default, or that the page wasn't read; the put-back FAIL uses it,
    and the comment says a put-back's reply can hold UNDRAWN. Forced live: "wasn't read after the put-back".

- [x] **SRV-184 · `screenshot_designer`'s docstring gives the count whenever the view is held below 8** · `mcp_server/server_tools/views.py:97-99` · confirmed · follows TST-679, generation 3 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "Held below 8 samples, the result gives the view's count (off screen, as last drawn) and what may hold
    it there": `below_rest()` is said only by a step refused (`_stopped`), a wait that ended at its limit
    (`_unsettled`) and the look's UNDRAWN.
  - **Scenario.** Samples at 4, Designer's window already in front (not covered, hidden or minimized), and a plain
    `screenshot_designer('3d')`: `_bring` waits for nothing (`shot3d.py`, the look), no step runs, and the render is
    taken at 4 samples with no word of it. An agent takes a result with no count to mean the view was at 8.
  - **Fix.** Generation 3, docs only: narrow the sentence to when the result says it, from the code.
  - **Resolution: done** (generation 3, docs only), by the developer: the docstring gives the count only when a
    wheel step isn't sent, or the view hadn't settled within 3 s after a step or after the window came back
    (`_stopped`, `_unsettled`, UNDRAWN), and says a shot where none of this happens says nothing of the count.

- [x] **HLP-218 · `_at_rest` refuses a wheel step when the window leaves the screen again after the look** · `mcp_server/designer_helpers/frames3d.py` (`_Frames._at_rest`) · confirmed, by reading; its rate not measured · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** After `again()`, the shot's look, `rested()` is `self._resting() or not self._drawing()`: with the
    window off screen again before the count is back at SAMPLES, the wait ends at once and `_at_rest` returns False.
    The step isn't sent, the camera's moves end, and the line says the view "didn't come to rest within 3 s", which
    may be after much less. Nothing was sent then, so a look again, as `_bring` does up to BRINGS times, can't take a
    step twice: DECISIONS.md's "never sends a wheel step ... again" doesn't cover it.
  - **Scenario.** At the default Samples 8, another Designer of the pool covers the window during the climb back to 8
    after the look (about 0.2 s): the zoom stops before its step, a random failure of the zoom checks that depends on
    the window in front.
  - **Fix.** Test first: the view brought to rest again while nothing was sent, within a limit of its own, and the
    line saying how long it waited; a unit test with a window that leaves after the look, and a forced live case if
    one can make it (hidden right after `_at_rest`'s look at Samples 8, while the count climbs).
  - **Resolution: done**, by the developer. At Samples 8 the climb back is inside the look's own wait, so the
    defect needs that wait ended at its limit, or Samples below 8. Tests, red first:
    `test_a_window_gone_again_after_the_look_is_looked_at_again_while_nothing_was_sent` (`test_frames3d.py`) and
    `test_a_wheel_step_refused_says_how_long_its_rest_was_waited_for` (`test_view3d_helpers.py`). Fix: `_at_rest`
    looks again while nothing was sent, `REST_LOOKS` (3) times at most, a safety net, and `_stopped` says how long
    the rest was waited for. Forced live (hidden again after a look cut at its limit): 1 step of 3 before, +3
    after. **Also covered:** `settled`, `moved`, `shown` and `_renders_alike` end off screen by design;
    `next_frame` after the render's look is left as HLP-149's resolution keeps it.
  - Questioned by HLP-219 (2026-11-21).
  - Questioned by HLP-220 (2026-11-21).
  - Questioned by TST-684 (2026-11-21).

- [x] **AGT-119 · Off macOS, the rule's rerun of a live check can't run** · `DECISIONS.md`, the rule's entry; `.claude/skills/live-check/SKILL.md`, When the final check fails · confirmed · follows AGT-114, generation 4 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "Off macOS ... a live check is rerun with its category alone in a scratch run (`alone.run`)": on
    Windows no Designer is recorded as an agent's (`lifecycle.py`, `if sys.platform == 'win32': ... return`), so
    `alone._refusal` takes the Designer the final check left open for the user's and runs nothing. The start checks
    and the user's graph put back are made only by the whole run there, which a scratch run can't make.
  - **Scenario.** A Windows final check fails a `params` check; `alone.run(params.run)` exits 2, and no text says what
    a rerun that can't run counts as.
  - **Fix.** Generation 4, docs only, and the user's answer (2026-11-21, "Whole Windows run").
  - **Resolution: done**, by the lead: a category's check is rerun in a scratch run once the user has closed the
    Designer the run left open, as `alone.run` takes every running Designer there for the user's; the start checks and
    the check that the user's graph is back in the editor are rerun with the whole run there.

- [x] **AGT-120 · A count of quits forced that passes its rerun merges, where Bridge and quitting reopens on it** · `DECISIONS.md`, the rule's entry against Bridge and quitting · confirmed · follows AGT-113, generation 4 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The rule counts a rerun that passes as passed for the merge; Bridge and quitting says "Reopen if: that
    check fails", and nothing in the procedure raises it. Two entries also reopen on what a crash dump points at.
  - **Scenario.** The final check fails "no more than two quits forced during their shutdown"; `--only` of the three
    categories forces two and passes; the row goes in, the branch merges, and the reopen is never told.
  - **Fix.** The user's (2026-11-21, "Merge, and tell me").
  - **Resolution: done**, by the lead: a failure that meets another entry's Reopen if still meets it when its rerun
    passes, such as the count of quits forced or a crash dump pointing at a cause; the merge goes ahead, and the lead
    tells the user (DECISIONS.md and the `live-check` skill).

- [x] **AGT-121 · ROADMAP.md and `docs/agent-workflow.md` still say every rerun is a category alone** · `ROADMAP.md`, Tests that failed at random; `docs/agent-workflow.md`, step 9 · confirmed · follows AGT-113 and AGT-114, generation 4 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "(a live check: its category alone)", while the count of quits forced reruns several categories
    together and the preferences the whole live self-test.
  - **Fix.** Generation 4, docs only: drop the parenthetical, keeping the pointer to DECISIONS.md.
  - **Resolution: done**, by the lead: both say the runner reran it alone "as it needs", with the pointer.

- [x] **HLP-219 · No test checks the time a refused wheel step now says** · `mcp_server/designer_helpers/frames3d.py` (`_Frames._at_rest`); `tests/unit/test_view3d_helpers.py`; `tests/unit/test_selftest_check_setups.py` · confirmed · follows HLP-218, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The one test of the new line fakes `rest_waited = 7.4`; no test reads it from a real `_Frames`, and
    the Rasterizer check's widened regex (`within [\d.]+ s`) is unit-tested only with "within 3 s".
  - **Scenario.** `rest_waited` set before the loop, or never, and every test still passes while the result says 0 s
    or 3 s for a rest of about 9 s; the regex put back to "within 3 s", and no unit test fails, while live it fails at
    random on "3.1" or a rest that needed a look.
  - **Fix.** Generation 2: a unit test of the real `_at_rest`, `time.monotonic` patched, asserting `rest_waited`
    covers the looks; a "within 6.1 s" case in `test_the_rasterizer_checks_refusal_takes_any_count_below_8`.
  - **Resolution: done** (generation 2, tests only), by the developer. `test_the_rests_time_covers_its_looks`
    (`test_frames3d.py`) runs the real `_at_rest` with `time.monotonic` patched, each look 3 s on: `rest_waited` is
    6.0; `test_the_rasterizer_checks_refusal_takes_any_count_below_8` gains "a rest that waited 6.1 s". Both pass
    on the code, as guards, and each failed on its forced break: `rest_waited` set before the looks (`0.0 == 6.0`),
    the regex back to "within 3 s" (the 6.1 s case refused).

- [x] **HLP-220 · Two docstrings on the rest's wait no longer match the code** · `mcp_server/designer_helpers/view3d.py` (module docstring); `mcp_server/designer_helpers/frames3d.py` (`_at_rest`) · confirmed · follows HLP-218, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** view3d.py: "A notch the view didn't come to rest before, or whose sign never came, each within
    SETTLE_LIMIT, ... the step says so (_stopped)": the rest now runs up to REST_LOOKS + 1 waits, and `_stopped` says
    the time measured. frames3d.py: "the look is made again, REST_LOOKS times at most": the loop holds the first look,
    so REST_LOOKS looks in all.
  - **Fix.** Narrow both sentences to the code.
  - **Resolution: done** (docs), by the developer: `_at_rest` makes "up to REST_LOOKS looks in all, each followed by
    a wait of SETTLE_LIMIT at most", `rest_waited` from its first wait to its end; view3d.py says a rest is made
    of waits of SETTLE_LIMIT at most each, up to REST_LOOKS looks again, and `_stopped` says how long it waited.

- [x] **TST-684 · No check reports the tool's new looks again** · `tests/test_all_tools/editor_panels_and_fit/checks.py` (the zoom checks' detail, `_said_by_the_tool`) · confirmed · follows HLP-218, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The branch's rule 8: "It reports how many retries the tool needed, so a tool that now retries every
    time shows". `_at_rest` now makes the shot's look up to REST_LOOKS times; the zoom checks' details don't say how
    many, and `_said_by_the_tool` keeps only the `3D view:` and `3D render:` lines, dropping `_bring`'s "Designer's
    window: ... again".
  - **Scenario.** A change leaves the window off screen after each look: every step's rest looks 2 or 3 times, each
    step is still sent from rest, the checks pass, and no run shows the tool now retrying every time.
  - **Fix.** The zoom checks' detail gives the number of looks the shot made, or the step's line says it when more
    than one.
  - **Resolution: done**, by the developer, in the checks (the tool unchanged). `test_the_zoom_check_says_how_many_looks_each_shot_made`
    failed first (no looks in the details); `checks._looks` counts `window_states.LOOKED`, the second wordings
    of shot3d's `BROUGHT` and `QT_RESTORED` that `_bring` prints at each look, and the zoom check's three details
    and the wheel facts check's back-to-back one end "; looks N". `test_the_zoom_checks_longest_detail_keeps_its_looks`
    keeps it within `check()`'s 150 characters. Live: looks 1 undisturbed, 3 hidden mid-zoom, 2 hidden from rest,
    twice alike. The count covers every look of the shot, not only a rest's; a tool-side count was left out, as it
    would change what agents read.

- [x] **HLP-221 · A wheel step's rest can refuse the shot mid-zoom, and the error doesn't say how far the zoom got** · `mcp_server/designer_helpers/frames3d.py` (`_at_rest`); `mcp_server/designer_helpers/view3d.py` (`_3d_set_up`) · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `_at_rest`'s look is `_Screen.again`, which calls `_bring`, and `_bring` raises ("isn't on screen 3 s
    after it was shown again"; "went off screen again ... each of the 3 times"). On `main` the look ran only before a
    step; now it runs inside `_wheel`, and the zoom's step goes in `done` only once `_wheel` returns. So the error
    lists the steps before the zoom, or none, and never the notches already sent. Four docstrings list when the look
    runs and leave the wheel's rest out: `_Screen`, `_on_screen`, `shoot_3d` (`shot3d.py`) and `_3d_set_up`.
  - **Scenario.** `screenshot_designer('3d', zoom=6)`: notches 1 to 3 taken, then the window keeps leaving at each
    look. The error is `_bring`'s alone, with "3D view, setting: +6 wheel steps"; an agent that shoots again with the
    same zoom leaves the user's view zoomed further than asked, against `set_3d_view`'s "an error after a change says
    what was set" (REVIEW.md HLP-200).
  - **Fix.** Count the notches sent; on an error, the zoom's step goes in `done` with that count ("+6 wheel steps (2
    sent)"); the four docstrings name the rest's look. Test first: a fake `from_rest` raising on its third call.
  - **Resolution: done**, by the developer. `test_a_zoom_whose_rest_fails_mid_zoom_says_the_notches_sent`
    (`test_view3d_helpers.py`), its fake's `from_rest` raising on call 3, failed first: the error was the look's
    alone. The zoom's line goes in `done` before the wait, as HLP-200's pattern, and `resting()` updates it with the
    notches sent: "+6 wheel steps (2 sent)"; `changed` follows from them. The four docstrings name the look inside a
    wheel step's rest.
  - Questioned by HLP-223 (2026-11-21).

- [x] **HLP-222 · UNDRAWN says "3D render:" at every look, also before a step that then settles** · `mcp_server/designer_helpers/shot3d.py` (`UNDRAWN`, `_wait_on_screen`) · confirmed · follows HLP-214, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `_wait_on_screen` prints `UNDRAWN` ("3D render: the 3D view hadn't settled within 3 s after Designer's
    window came back on screen") whenever `shown` ends at its limit, at every look: before each step, inside a wheel
    step's rest, and before the render. `views.py` keeps every `3D render: ` line in the reply.
  - **Scenario.** Under load, a covered window comes back for a step's look and `shown` ends at its limit; the step
    then waits for its restart and for the count back at 8, and the render is settled, yet the reply says the 3D
    render hadn't settled, and the tool's docstring tells the agent to shoot again with no set-up.
  - **Fix.** Generation 2: print UNDRAWN only at the render's own look, or word it for the look when a step follows.
  - **Resolution: done** (generation 2), by the developer. The latest wait decides: `shown()` records `undrawn`, and
    `settled()` and `moved()` clear it once a step restarts the view, or compare renders where no count shows;
    `_wait_on_screen` prints nothing, and `shoot_3d` says UNDRAWN after the render, from the last look's record.
    Tests, red first: `test_a_look_that_ended_at_its_limit_is_recorded_until_a_step_restarts_the_view` (6 cases),
    `test_with_no_count_shown_a_steps_renders_compared_end_the_looks_record` (`test_frames3d.py`),
    `test_a_look_whose_view_hadnt_drawn_within_the_limit_says_nothing_itself` and
    `test_a_view_that_hadnt_settled_since_the_latest_look_is_said_after_the_render` (`test_shot3d.py`); two older
    tests replaced, their HLP-215 count asserted after the render. The developer's open case: a look ended at its
    limit, `_at_rest` then reads 8 and sends a notch that restarts nothing, and the render says "hadn't settled";
    not measured.
  - Note (2026-11-21): the Rasterizer check's put-back comment, "a put-back's reply can hold UNDRAWN", and two
    comments of its unit test say what was so before HLP-222: `_SET` uses `_on_screen`, never `shoot_3d`, so its
    reply holds no UNDRAWN now (a reviewer, Opus).
  - Questioned by HLP-224 (2026-11-21).

- [x] **TST-685 · An Undo send refused has its state cut from the FAIL line and printed nowhere** · `tests/test_all_tools/undo/edit_menu.py` (`Sent._why`, `Sent.say`) · confirmed · follows TST-662, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `_why` gives "not scheduled: " + the state UNDO_REDO printed, after TST-662's "sent %d times, the action
    before never fired; " when resent, and `common.check` keeps 150 characters; `say()` returns at once for a refused
    send, so the rest is printed nowhere.
  - **Scenario.** A state line from the scratchpad's logs is about 115 characters. A resent NO_ACTION, TST-668's
    case, is about 185 and is cut right before "'Undo' enabled=False", the fact that explains it; with Designer
    active, `active=` and `focus=` lengthen a first send's past 150 too.
  - **Fix.** `say()` prints the refusal whole on a line of its own; a unit test with a realistic NO_ACTION state.
  - **Resolution: done**, by the developer. `test_a_refused_resend_prints_its_state_whole` (`test_selftest_undo.py`),
    a NO_ACTION state of about 125 characters, resent, failed first (nothing under the FAIL); `say()` prints the
    refusal whole: "the Undo, not scheduled: <state>".

- [x] **TST-686 · ROADMAP item 112's Done note calls a run before the review rounds' fixes "the final check"** · `ROADMAP.md`, item 112 · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "The final check passed 806 of 806 live checks and 2887 unit tests" is the run at 559a7c5; 17 code
    files changed since, and the final check runs just before the merge (AGENTS.md, Running the tests).
  - **Scenario.** The real final check lists this branch's Undo or zoom check as failed at random, while `main`'s item
    112 says the final check passed 806 of 806.
  - **Resolution: done**, by the lead, whose text it was: "The full suites, run at 559a7c5 before the review rounds'
    fixes, passed ..."; the final check's own figures replace it before the merge.

- [x] **TST-687 · An Undo send whose read fails returns with its Edit menu's action maybe still armed** · `tests/test_all_tools/undo/edit_menu.py` (`send`) · confirmed, the path by reading; whether an armed action lands on another document isn't measured · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `send` returns at a failed `describe_graph` read, and at a failed `UNDO_FIRED` read, without the read
    of the action's state that disarms one not fired yet. In the one run (Windows), the self-test uses the user's
    Designer if it is open, `script_runner` runs after `undo`, and Edit > Undo acts on the document in focus; the
    note of TST-646 and TST-655, "nothing reads that state after it", holds only in the pool.
  - **Scenario.** A `describe_graph` read fails in the one run; the action is still armed, fires during a later job,
    and undoes a step of a graph in focus then, possibly the user's, with no line saying so.
  - **Fix.** A small defensive change (DECISIONS.md, Low-value findings: "anything that can touch the user's work"):
    read `UNDO_FIRED`, which disarms it, before returning on a failed `describe_graph` read, and say when that read
    fails too that the action may still fire.
  - **Resolution: done**, by the developer. On a failed `describe_graph` read, `send` reads UNDO_FIRED, which
    disarms the action, before returning, its answer not taken for the check's; a state read that fails, there or
    after the reads, sets `unread`, and `say()` prints "the Edit menu's action may still fire". Tests, red on the
    old code: `test_a_failed_read_of_the_graph_disarms_the_action_before_returning`,
    `test_an_action_whose_state_couldnt_be_read_is_said_to_maybe_still_fire` (2 cases). An Undo that fired just
    before that read is still not put back with a Redo, as before.
  - Questioned by TST-690 (2026-11-21).
  - Questioned by TST-691 (2026-11-21).
  - Note (2026-11-21): `test_a_failed_read_of_the_graph_disarms_the_action_before_returning` takes the first
    `describe_graph`, the set check's read before the Undo, so it passes with the state read anywhere after it;
    asserting the calls from the Undo on, `['Undo', 'describe_graph', 'fired', 'as prepared']`, pins it (a
    reviewer, Opus).

- [x] **TST-688 · The zoom check's failure report raises on a plain shot after that failed** · `tests/test_all_tools/editor_panels_and_fit/renders.py` (`plain_after`); `checks.py` (the zoom check) · confirmed · follows TST-664, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `plain_after` drops its shot's reply and returns `(<path>_after.png, 255.0)` when the shot saved
    nothing; the zoom check then passes that path to `say_renders`, whose `grey_file` raises `FileNotFoundError`.
  - **Scenario.** In a full run, the plain shot after the hidden-mid-zoom render raises in Designer ("isn't on screen 3
    s after it was shown again"). The FAIL says "255.00 from a shot after", then `say_renders` raises: `run_steps`
    counts the category as failed with a traceback, and the wheel facts check, the Rasterizer check and about 20
    later checks don't run. The undisturbed zoom's `settled` FAIL gives no tool line and no render either: against
    the branch's rule 5 and the zoom check's docstring.
  - **Fix.** `plain_after` returns its shot's reply too, and the check prints its tool lines when it failed;
    `say_renders` says "not saved" for a missing path; a unit test with no `_after` file saved.
  - **Resolution: done**, by the developer. `plain_after` returns its shot's reply too; `say_renders` says "not
    saved" for a missing file; the zoom check prints the last lines of a shot that saved nothing. Tests, red first:
    `test_a_render_not_saved_is_said_so` (FileNotFoundError),
    `test_a_plain_shot_after_that_saved_nothing_returns_what_was_said`,
    `test_the_zoom_check_says_what_its_plain_shot_after_said_when_it_saved_nothing`.
  - Questioned by TST-692 (2026-11-21).

- [x] **TST-689 · The 3D checks' unit fake touches no render on Windows** · `tests/unit/test_selftest_check_setups.py` (`Shots3d.c`) · confirmed · follows TST-664, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `re.findall(r"'(%s[^']*\.png)'" % re.escape(str(folder)), code)`: the checks write their paths with
    `%r`, which doubles a backslash, so on Windows the pattern matches nothing.
  - **Scenario.** The unit suite on Windows (ROADMAP item 18): no render exists, every zoom check stops at its first
    guard, and six tests fail; `test_windows_simulation.py` can't see it, as it changes `sys.platform`, not paths.
  - **Fix.** The fake reads each quoted `.png` literal with `ast.literal_eval` and touches those under `folder`.
  - **Resolution: done**, by the developer: the fake reads each quoted `.png` literal with `ast.literal_eval` and
    touches those under the folder. `test_the_3d_checks_fake_touches_a_path_as_the_code_writes_it`, a folder
    `back\slash`, failed first ("no checker on the plane at the start").
  - Note (2026-11-21): its test's folder `back\\slash` is two folders on Windows, where `mkdir()` without
    `parents=True` raises; `mkdir(parents=True)` keeps it running there (a reviewer, Opus).

- [x] **TST-690 · The Redo `put_back` sends is never disarmed after the last Undo check** · `tests/test_all_tools/undo/edit_menu.py` (`put_back`); `undo/checks.py` (`run`) · confirmed, the path by reading; its effect isn't measured · follows TST-687, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `put_back` arms a Redo through the Edit menu after an Undo that fired and never showed, and nothing
    reads its state: after the add and set checks the next send's arm disarms it, after the code-run check, the last,
    nothing does. TST-687's defect named TST-646's note about this Redo; its fix covered `send` only.
  - **Scenario.** In the one run on Windows, the code-run check's Undo fires and never shows; its Redo's timer doesn't
    fire, then fires during `script_runner`, on the document in focus then.
  - **Fix.** Read `UNDO_FIRED` once where nothing follows, at the end of `undo`'s `run` after its last clean-up, and
    say a Redo not fired, or "may still fire" when that read fails; not straight after the Redo, which would disarm it
    before its timer runs. A unit test whose Redo never fires.
  - **Resolution: done**, by the developer. UNDO_FIRED prints `ARMED True/False` first, whether an action was
    armed since the last read, as `FIRED None` can't tell one not fired from none armed; `read_left_armed` reads it
    in `undo`'s `run`, in a `finally` after the last clean-up, and says an action armed that hadn't fired, which the
    read disarmed, or "may still fire" when the read fails. Tests, red first:
    `test_the_undo_checks_end_reading_the_action_left_armed` (4 cases),
    `test_the_undo_checks_end_reads_the_action_left_armed_when_a_check_raised`, and the ARMED lines in
    `test_selftest_pool.py`. Live: a passing run's end read gets the code-run check's own Redo, fired; nothing said.

- [x] **TST-691 · After a failed graph read, the state read's answer is thrown away** · `tests/test_all_tools/undo/edit_menu.py` (`send`) · confirmed · follows TST-687, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The new `UNDO_FIRED` read on a failed `describe_graph` keeps only an error, so the FAIL never says
    whether the action had fired, which that read now knows.
  - **Fix.** Keep the answer in a field only `say()` prints, out of `fired`, so `put_back` and `detail()` behave as
    now (the branch's rule 5).
  - **Resolution: done**, by the developer: the state read after a failed graph read goes in `fired_said`, which only
    `say()` prints; `fired` stays None, so `detail()` and `put_back` are as before.
    `test_a_failed_read_of_the_graph_says_what_the_actions_state_read_after_it_said` (2 cases) failed first.

- [x] **AGT-122 · DECISIONS.md writes the user's answer on item 112 as a rule for every branch** · `DECISIONS.md`, the rule's entry · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "A test the branch was to make robust that fails at random reopens the branch's ROADMAP.md item ...
    (the user, 2026-11-21: "Merge, reopen 112")": the question asked of item 112 only.
  - **Resolution: done**, by the lead: "The user's answer, 2026-11-21, asked of item 112: "Merge, reopen 112"; this
    form for every branch is the lead's reading, told the user."

- [x] **AGT-123 · The two texts point "its row" at different rows** · `DECISIONS.md`, the rule's entry; `.claude/skills/live-check/SKILL.md`, When the final check fails · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** DECISIONS.md: "the merge goes ahead with its row, and the item is unchecked"; the skill: "unchecks the
    branch's ROADMAP.md item, its row saying why"; the random-failures table has no cell for a reason, and the docs
    test guarded only DECISIONS.md's sentence.
  - **Resolution: done**, by the lead: both say the merge goes ahead with the test's row in "Tests that failed at
    random", and the item is unchecked, its Done note naming that row; the docs test asserts both.

- [x] **TST-692 · The undisturbed zoom's failure shows neither its shots' replies nor their renders when both saved** · `tests/test_all_tools/editor_panels_and_fit/checks.py` (the zoom check) · confirmed · follows TST-688, generation 3 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `if from_after >= 1.0: _say_unsaved(...)`: only a shot that saved nothing is said. TST-688's own
    scenario named this verdict ("gives no tool line and no render either"), and the docstring says "On failure it
    prints each render's plane width, mean grey and path".
  - **Scenario.** Under load, the plain shot after the undisturbed zoom renders at its look's limit and says UNDRAWN;
    the `settled` verdict fails with "1.40 grey levels from it; looks 1" alone, and the random failure reads as the
    zoom's own, which by the user's answer would reopen item 112.
  - **Fix.** Generation 3: output, not a check. Under the `settled` FAIL, the plain shot after's tool lines and both
    renders (`say_renders`), or the docstring narrowed to what is printed.
  - **Resolution: done** (generation 3, output only), by the developer: under the undisturbed zoom's `settled` FAIL,
    `_say_shots` prints each shot's tool lines, or a shot that saved nothing its reply's last lines, then the
    renders. `test_the_undisturbed_zooms_failure_says_its_shots_and_their_renders_when_both_saved` failed first.

- [x] **HLP-223 · Three more docstrings say when the look runs and leave out a wheel step's rest** · `mcp_server/designer_helpers/shot3d.py` (`_Screen`, `again`, `between`) · confirmed · follows HLP-221, generation 2 · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** `again()`: "Before a set-up step or a render"; `between()`: "Before each set-up step and render"; the
    class: "by between() before each set-up step and render". `from_rest(between)` runs them in a wheel step's rest,
    and `_bring` raises from inside `_wheel` through them; `again()` already left out the viewpoint's turn.
  - **Fix.** Add the viewpoint's turn and a wheel step's rest (`_Frames.from_rest`) to the three, as HLP-221's four now
    say.
  - **Resolution: done** (docs), by the developer: `_Screen`, `between()` and `again()` add "after a viewpoint's
    turn, and in a wheel step's rest (_Frames.from_rest)". The three notes under TST-687, TST-689 and HLP-222 are
    fixed too, with no new check.

- [x] **TST-693 · The self-test's Edit menu Undo or Redo can land on a graph other than its own, and `put_back`'s Redo is never read** · `tests/test_all_tools/common.py` (`UNDO_REDO`); `tests/test_all_tools/undo/edit_menu.py` (`put_back`) · confirmed, the path by reading; its effect isn't measured · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** UNDO_REDO checks that the self-test graph is current when it schedules the action, not when the zero
    timer fires, and Edit > Undo acts on the document in focus then. `put_back` sends its Redo unread: its landing
    is never confirmed (the "unread Redo" class behind TST-687 and TST-690; the developer's altitude review).
  - **Scenario.** In the one run on Windows, in the user's Designer, another graph is current when an armed action
    fires: a step of it is undone or redone, and no line says so.
  - **Fix.** The user's, 2026-11-21: fixed in the branch ("nothing else in roadmap fix it here"). The action fires only
    if the self-test graph is still current at fire time, and says so when it isn't; `put_back`'s Redo goes through
    `send`'s read until it shows. A forced live case with another graph current at fire time.
  - **Resolution: done**, by the developer.
    - **Measured** (a probe, 3 repeats per case): with another package's graph opened in the editor right after the
      schedule, `getCurrentGraph()` read that graph at fire time, yet Edit > Undo still removed the self-test graph's
      node, 3 of 3. So the guard errs on the safe side: it refuses an action that would have landed on its own graph.
      What Edit > Undo follows instead isn't measured, nor a case where an Undo lands on another document.
    - **Fix.** `UNDO_REDO` (`common.py`) fires only if its graph is still current, read by a new `_current()`, and
      otherwise keeps `NOT_CURRENT current=<id>`. `send` (`edit_menu.py`) ends there with no resend, and the FAIL
      line says "the Edit menu's action didn't fire: NOT_CURRENT current=<id>". `put_back(c, graph, sent)` sends its
      Redo through `send`, read until it shows, and prints "the Redo putting it back: <detail>" when it never does.
    - **Tests, red first:** `test_an_action_whose_graph_isnt_current_as_it_fires_doesnt_fire`
      (`test_selftest_pool.py`), `test_an_action_that_found_another_graph_current_as_it_fired_fails_saying_so` and
      `test_the_redo_putting_back_an_undo_that_never_showed_is_read_until_it_shows` (`test_selftest_undo.py`); the
      older tests that pinned the unread Redo now read it. Forced live cases: another graph opened at fire time
      failed the check's guard on HEAD (the Undo fired, the check passed) and passes with the fix, the node kept; an
      Undo that never shows has its node put back by the read Redo. The undo category passed in fresh Designers.
    - **A cost:** `put_back`'s Redo can wait up to `LANDING_S` (10 s) when it never shows, on a failure path only.

- [x] **HLP-224 · The 3D shot says the view "hadn't settled" after a look that ended at its limit, though the view drew what changed** · `mcp_server/designer_helpers/frames3d.py` (`_Frames.undrawn`) · measured · follows HLP-222, generation 3 · found 2026-11-21 by the developer (Opus)
  - **Defect.** HLP-222's open case. A look that ends at its limit records `undrawn`, and only a step's restart
    clears it. When the zoom's notch then restarts nothing, the render's reply says UNDRAWN, though the view had
    drawn the change.
  - **Scenario.** Measured with its conditions forced (Designer hidden before the shot, the look's waits cut to 0 s,
    the notch a no-op): the reply said "3D render: the 3D view hadn't settled within 3 s ...", yet the render was
    0.00 grey levels from a plain shot right after it, 3 of 3. Sixty real notches all restarted the view, so the
    trigger is a notch with no sign, the documented stop case.
  - **Fix.** Generation 3: `undrawn` re-reads the look's own predicate before it is said.
  - **Resolution: done**, by the developer. `_Frames.undrawn` is a property: it keeps the look's mark and re-reads
    the paints and UpdateRequests counted since, through `_look_drawn(since)`, which `shown()` reads too. A count at
    8 alone never clears it, since with a frame asked for that count can be the one before the change. Test, red
    first: `test_a_look_that_ended_at_its_limit_isnt_said_once_the_view_drew_what_changed` (`test_frames3d.py`, 3
    cases; "nothing changed" and "restarted and back" failed, "a frame asked for, the count stale" stays said). The
    forced probe says nothing with the fix, 3 of 3, still 0.00 from the plain shot after; the zoom, wheel facts and
    Rasterizer checks pass in scratch runs. `shot3d.py`'s UNDRAWN comment and the tool's docstring narrowed to
    match.
