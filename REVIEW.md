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

**Last used:** PLG-45, SRV-242, HLP-253, INS-46, TST-806, AGT-125.

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
| Low-medium | 0 | 0 |
| Low | 0 | 3 |
| **Total** | **0** | **3** |

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
| 2026-11-23, step 1 (the run times on record) | Opus (developer) | 1 | 0 | 0 | 150,630 | 7 min |
| 2026-11-23, the first review (a Sonnet round on step 1) | Sonnet | 1 | 1 [1 Low] | 1 [1 Low] | 121,758 | 4 min |
| 2026-11-23, the first review's fixes | Opus (developer) | 1 | 0 | 0 | 24,156 | 2 min |
| 2026-11-23, the second review (the Opus round on the entire branch) | Opus | 1 | 2 [2 Low] | 2 [2 Low] | 147,181 | 8 min |
| 2026-11-23, the second review's fixes | Opus (developer) | 1 | 0 | 0 | 5,193 | 1 min |
| **Total** | | **5** | **3 [3 Low]** | **3 [3 Low]** | **448,918** | **22 min** |

## Review log

### 2026-11-23: stale-run-times' first review, a Sonnet round on step 1

- **Scope:** `git diff 1bfe493 557f58e -- . ':(exclude)PLAN.md'`.
- **How:** one Sonnet reviewer, the whole round. No tests run; one suspicion settled by reading the two full runs'
  worker lines. Not raised, or not worth a fix:
  - "editor_panels_and_fit (about 7 minutes), facts and undo set that time": the runs' worker lines show it (bbc5c50:
    editor 0-443 s, facts 443-509 s, undo 509-527 s; 37c2707: facts 0-58 s, editor 58-503 s, undo 503-521 s);
  - the run's start checks (`--first`) now made in `editor_panels_and_fit`, the first category after `lifecycle`, where
    `functions` made them: no doc or test names the category, and `workers.py`'s "first category to start after
    lifecycle" still holds. For the user, with the cost of a rerun after a start check fails;
  - "425 s" for 425.3 s and 425.9 s, where the neighbours round the mean (425.6);
  - the other categories' comments (`measure` 9 s, `safeguards` 23 s, `render` 35 s against 46-51 s in the full runs),
    and the header's "(measured 2026-11-10 ...)": older figures the step didn't touch. For the user.
- **Unspecified:** none.
- **Not verified:** none.
- **Resolutions assessed:** none in scope.
- **Findings:** TST-804 (Low). A few Lows: step 1's reviews are done once the developer fixes it, then an Opus round on
  the entire branch.
- **Suggested order:** TST-804.
- **Checked and found fine:** each new figure against the measured ones and its source; README's 8.7 minutes (the mean
  of 527 s and 521 s), `lifecycle` about 3 minutes, "the longest after editor_panels_and_fit"; `names()` keeping
  `lifecycle` first, `facts` blocked while `editor_panels_and_fit` runs, `undo` SOLO; the phrasing tests; no other doc
  made wrong; no code changed beyond the list's order.

### 2026-11-23: stale-run-times' second review, the Opus round on the entire branch

- **Scope:** `git diff main...HEAD -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'` at 6d08c5f, with REVIEW.md as the
  record.
- **How:** one Opus reviewer, the whole branch. No tests run, no probes: each suspicion settled by reading. Not
  raised, or not worth a fix:
  - the live-check skill's "about a minute" for the unit suite, which took 204-207 s beside the pool: its time alone
    isn't among the measured figures.
- **Unspecified:** whether the step's "Each figure names its source" asks every figure written into the docs to name
  its runs (README gives a date only): the lead reads it as the plan's figures, each named there. Left as it is.
- **Not verified:** none.
- **Resolutions assessed:** TST-804. It holds; TST-805 follows its fix.
- **Findings:** TST-805, TST-806 (Low). A few Lows: the reviews look converged once the developer fixes them. The
  longest chain: TST-804 → TST-805, generation 2.
- **Suggested order:** TST-806, TST-805.
- **Checked and found fine:** each figure against its measurement, the comment rightly without "with their server's
  start"; `names()`, `schedule`, `CLIPBOARD` and `SOLO` with `editor_panels_and_fit` first, the new order the schedule
  of the bbc5c50 run already run at full load; `--first` now in `editor_panels_and_fit`, changing no state its steps
  start from, and the unit tests taking the first category from `names()[1]`; the phrasing tests; no other code
  changed.

---

## High

## Medium-high

## Medium

## Low-medium

## Low

- [x] **TST-804 · Older pool-time figures left beside the new 8.7 minutes contradict it** · `tests/test_all_tools/workers.py:3,9-10` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** `workers.py:3`, undated: "(simulated with 4: 2.8 to 3.7 min against 5.9 to 6.5)"; `:9-10`: "With 2 at once
    they took 5.6 minutes, and 10.5 with 1 (2026-11-10, before editor_panels_and_fit grew)", after "about 8.7 minutes
    with 4 side by side", where `editor_panels_and_fit` alone takes 425 s; `ROADMAP.md:12`: "which took a full pass from
    about 12 minutes to about 3.4", which README's old 3.2 agreed with and its new 8.7 doesn't. The step asks for these
    files' run times as measured.
  - **Scenario.** A reader takes 2 workers for faster than 4 (README advises `--workers 2` for less memory), or a full
    pass for 3.4 minutes.
  - **Fix.** Delete the 2- and 1-worker figures and the simulated ones, or date them and say they aren't measured
    since; `ROADMAP.md:12` dated, or with today's figure beside it.
  - Questioned by TST-805 (2026-11-23).

  - **Resolution: done**, wording only.
    - **Test:** none new: stale figures in a docstring and ROADMAP's intro; the docs tests and the unit tests reading
      `workers.py` pass.
    - **Cause:** step 1 replaced the current run time and left the pool's 2026-11-10 figures beside it, measured when
      `editor_panels_and_fit` took seconds.
    - **Fix:** `workers.py`'s simulated and 2- and 1-worker figures deleted, the 12 minutes before the pool dated by
      its arrival (2026-11-11); `ROADMAP.md:12`: "to about 3.4 (2026-11-10). On 2026-11-23 a full pass took about 8.7
      minutes."
    - **Also covered:** a search for 3.4, 3.2, 5.6, 10.5, 3.8, 2.8 to 3.7, 5.9 to 6.5 and 12 min, and for any minute
      figure in the self-test, GUIDE, the docs and `.claude/`: no other pool run time left stale; dated records of past
      runs left as they are.

- [x] **TST-805 · TST-804's fix wrote the 8.7 minutes into ROADMAP's intro, a third copy of the suites' time** · `ROADMAP.md:12-13` · confirmed · follows TST-804, generation 2 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** "to about 3.4 (2026-11-10). On 2026-11-23 a full pass took about 8.7 minutes." README.md:196 and
    `workers.py:7-8` hold the figure; DECISIONS.md, Project rules, names `workers.py` as the home of the suites' times.
    `.claude/rules/docs.md`: keep each fact in one place and link to it.
  - **Scenario.** The next re-timing has three places to update, the drift this branch fixed.
  - **Fix.** Wording only (generation 2, narrowing): the sentence deleted, or a pointer to `workers.py`'s docstring.
  - **Resolution: done**, wording only: "to about 3.4 (2026-11-10). `workers.py`'s docstring gives the latest time of a
    full pass." The dated 3.4 stays as history.

- [x] **TST-806 · A unit test's docstring still calls lifecycle the longest worker** · `tests/unit/test_selftest_lifecycle.py:478-479` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** "eight of them were about 80 s of lifecycle, the longest worker", where the branch records
    `editor_panels_and_fit` as the longest (425 s) and lifecycle after it (`workers.py`, README).
  - **Scenario.** A reader takes lifecycle for the run's longest worker, deciding what to speed up.
  - **Fix.** Wording only: "then the longest worker", or the phrase dropped.

  - **Resolution: done**, wording only: "eight of them were about 80 s of lifecycle, then the longest worker"; no other
    claim that lifecycle is the longest left.
