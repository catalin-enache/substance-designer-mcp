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

**Last used:** PLG-45, SRV-277, HLP-256, INS-51, TST-888, AGT-134.

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
| High | 0 | 1 |
| Medium-high | 0 | 0 |
| Medium | 0 | 1 |
| Low-medium | 0 | 9 |
| Low | 0 | 69 |
| **Total** | **0** | **80** |

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
| 2026-11-24, the rollback spike | Opus (developer) | 1 | 0 | 0 | 295,286 | 18 min |
| 2026-11-24, step 1 | Opus (developer) | 1 | 0 | 0 | 314,995 | 42 min |
| 2026-11-24, round 1 (step 1) | Sonnet | 3 | 12 [4 Low-medium, 8 Low] | 12 [4 Low-medium, 8 Low] | 623,007 | 12 min |
| 2026-11-24, round 1 (step 1) | settling | 1 | 0 | 0 | 136,834 | 4 min |
| 2026-11-24, round 1's fixes | Opus (developer) | 1 | 0 | 0 | 159,945 | 27 min |
| 2026-11-24, round 2 (round 1's fixes) | Sonnet | 2 | 6 [1 Low-medium, 5 Low] | 6 [1 Low-medium, 5 Low] | 403,577 | 10 min |
| 2026-11-24, round 2's fixes | Opus (developer) | 1 | 0 | 0 | 54,279 | 14 min |
| 2026-11-24, GUIDE.md's Undo rule reworded (the user's word) | Opus (developer) | 1 | 0 | 0 | 5,660 | 1 min |
| 2026-11-24, round 3 (round 2's fixes, the rule) | Sonnet | 1 | 0 | 0 | 163,037 | 6 min |
| 2026-11-24, step 2 (the other tools' rollback, `sys.exit`) | Opus (developer) | 1 | 0 | 0 | 483,415 | 35 min |
| 2026-11-24, step 2's `sys.exit(0)` checks on the installed plugin | Opus (developer) | 1 | 0 | 0 | 3,748 | 1 min |
| 2026-11-24, round 4 (step 2) | Sonnet | 2 | 4 [4 Low] | 4 [4 Low] | 382,919 | 10 min |
| 2026-11-24, round 4's fixes | Opus (developer) | 1 | 0 | 0 | 64,462 | 11 min |
| 2026-11-24, step 3 (the crash's three ideas, the self-test's Undo and Redo) | Opus (developer) | 1 | 1 [1 Low-medium] | 1 [1 Low-medium] | 391,352 | 30 min |
| 2026-11-24, round 5 (step 3, round 4's fixes) | Sonnet | 2 | 6 [6 Low] | 6 [6 Low] | 438,130 | 10 min |
| 2026-11-24, round 5's fixes | Opus (developer) | 1 | 0 | 0 | 84,770 | 13 min |
| 2026-11-24, round 6 (the entire branch) | Opus | 3 | 13 [13 Low] | 13 [13 Low] | 793,440 | 22 min |
| 2026-11-24, round 6 (the entire branch) | settling | 1 | 0 | 0 | 86,833 | 7 min |
| 2026-11-24, round 6's fixes | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 104,727 | 17 min |
| 2026-11-25, TST-867's fix | Opus (developer) | 1 | 0 | 0 | 6,202 | 2 min |
| 2026-11-25, round 7 (round 6's fixes) | Opus | 1 | 2 [2 Low] | 2 [2 Low] | 223,656 | 12 min |
| 2026-11-25, round 7's fixes | Opus (developer) | 1 | 0 | 0 | 40,182 | 9 min |
| 2026-11-25, round 8 (the entire branch) | Opus | 3 | 5 [1 Low-medium, 4 Low] | 5 [1 Low-medium, 4 Low] | 808,956 | 18 min |
| 2026-11-25, round 8 (the entire branch) | settling | 2 | 0 | 0 | 363,548 | 9 min |
| 2026-11-25, round 8's fixes | Opus (developer) | 1 | 0 | 0 | 59,482 | 12 min |
| 2026-11-25, step 4 (`undo_edits`, TST-873) | Opus (developer) | 1 | 0 | 0 | 452,642 | 38 min |
| 2026-11-25, round 9 (step 4) | Sonnet | 2 | 5 [1 Medium, 1 Low-medium, 3 Low] | 5 [1 Medium, 1 Low-medium, 3 Low] | 393,761 | 11 min |
| 2026-11-25, round 9 (step 4) | settling | 1 | 0 | 0 | 170,278 | 9 min |
| 2026-11-25, round 9's fixes | Opus (developer) | 1 | 0 | 0 | 168,629 | 28 min |
| 2026-11-25, round 10 (round 9's fixes) | Sonnet | 2 | 6 [6 Low] | 6 [6 Low] | 420,704 | 11 min |
| 2026-11-25, round 10 (round 9's fixes) | settling | 1 | 0 | 0 | 161,603 | 13 min |
| 2026-11-25, round 10's fixes | Opus (developer) | 1 | 0 | 0 | 70,229 | 13 min |
| 2026-11-25, round 11 (the entire branch) | Opus | 3 | 8 [8 Low] | 8 [8 Low] | 855,334 | 19 min |
| 2026-11-25, round 11's fixes | Opus (developer) | 1 | 0 | 0 | 75,309 | 12 min |
| 2026-11-25, round 12 (round 11's fixes) | Opus | 1 | 1 [1 Low] | 1 [1 Low] | 230,337 | 12 min |
| 2026-11-25, round 12's fix | Opus (developer) | 1 | 0 | 0 | 46,004 | 7 min |
| 2026-11-25, round 13 (the entire branch) | Opus | 3 | 4 [1 High, 3 Low] | 4 [1 High, 3 Low] | 864,271 | 16 min |
| 2026-11-25, round 13 (the entire branch) | settling | 1 | 0 | 0 | 169,841 | 22 min |
| 2026-11-25, round 13's fixes and the user's six changes | Opus (developer) | 1 | 0 | 0 | 455,736 | 81 min |
| 2026-11-25, round 13's follow-ups (redone steps after two calls, the tracer's docstring) | Opus (developer) | 1 | 0 | 0 | 34,634 | 7 min |
| 2026-11-25, the commit's fallback to `UndoGroup` and its check (the user's request) | Opus (developer) | 1 | 0 | 0 | 51,165 | 11 min |
| 2026-11-25, round 14 (round 13's fixes) | Opus | 2 | 6 [1 Low-medium, 5 Low] | 6 [1 Low-medium, 5 Low] | 479,736 | 17 min |
| 2026-11-25, round 14's fixes (sd's public transaction functions, untraced) | Opus (developer) | 1 | 0 | 0 | 114,117 | 22 min |
| 2026-11-25, round 15 (round 14's fixes) | Opus | 1 | 0 | 0 | 215,249 | 13 min |
| 2026-11-25, round 16 (the entire branch) | Opus | 3 | 0 | 0 | 881,825 | 16 min |
| 2026-11-25, round 16's leftovers (the beyond check's guard, `_failure`'s docstring) | Opus (developer) | 1 | 0 | 0 | 9,732 | 2 min |
| 2026-11-25, the read-only sentence in `_tool`'s docstring (the user's decision) | Opus (developer) | 1 | 0 | 0 | 3,706 | 2 min |
| **Total** | | **66** | **80 [1 High, 1 Medium, 9 Low-medium, 69 Low]** | **80 [1 High, 1 Medium, 9 Low-medium, 69 Low]** | **12,817,284** | **734 min** |

## Review log

### 2026-11-24: apply-edits-precheck, round 1 (step 1 of PLAN.md: the rollback, apply_edits first)

- **Scope:** `git diff 77e6be2 6862240 -- . ':(exclude)PLAN.md'`.
- **How:** three Sonnet reviewers: the rollback mechanism (`designer_rollback.py`, `core.py`, their unit tests); apply_edits'
  messages and the guard tests; the live checks and the docs. No tests run. A runner's probes in its own Designer
  (port 9961, the branch's server): `set_link_display` on one of two packages with tagged steps; a nested
  `UndoGroup` in `execute_designer_code`; odd step names; a rolled-back `bitmap` op; `isModified()` after
  `create_graph` and after a rollback. Settled as wrong:
  - "Nothing changed in Designer" overclaiming for a bitmap resource or a package a call made: measured, a rolled-back
    `bitmap` op leaves the package's resources as before (a `copy` file stays on disk, which the note says), and the
    spike measured a failed `create_graph` save removing its package; loading packages is a history step too
    ("Open Package(s)");
  - a nested undo group in a script leaving its inner step below ours: measured, it merges into the call's step and
    the rollback takes it back;
  - odd step names (`&`, a newline, an empty label, long, Unicode) failing the tag check: measured, Designer stores
    them verbatim and each rolled back;
  - the "saved package stays modified" check passing on a value already there: measured, `isModified()` is False
    right after `create_graph`'s save and True after the rollback;
  - the planned `menu()` wrapper sentence missing from GUIDE.md: the lead's choice, as the pitfall didn't reproduce
    in a fresh Designer (PLAN.md);
  - Edit > Undo not the same history as the toolbar's: the probe of 2026-11-24 measured Edit > Undo's parent is
    `HistoryActionsMgr` and its trigger reverted another package's top step.
  Not reported, step 2's planned work: the code tools' docstrings and `undo_label`'s description (the tag now
  appended), and live checks of the other tools' rollback. Not worth a fix: a cancel landing in the two traced lines
  before `settrace(None)` (today's behaviour); `_bridge`'s wait covering a 60 s rollback after a timeout only just;
  the not-rolled-back text's lowercase "its node was added".
- **Not verified:** none.
- **Resolutions assessed:** none in scope.
- **Findings:** SRV-252, SRV-253, HLP-256, TST-842 (4 Low-medium); SRV-254, SRV-255, SRV-256, TST-843, TST-844,
  TST-845, TST-846, TST-847 (8 Low).
- **Unspecified** (in PLAN.md's Waiting for the user): GUIDE.md's rule trigger "while one of the user's graphs is
  open", now that the history is one for the whole app; a script ending with `sys.exit()` rolled back whole.
- **Suggested order:** SRV-252 and SRV-253 first (each can mislead the agent about the user's work), then TST-842.
- **Checked and found fine:** no path undoes a step that isn't the call's own (the tag per call, the same string to
  the group and the check, a call with no step finding "not ours"); the rollback runs once, after the commit,
  untraced, and re-raises the call's own error; every apply_edits failure path's text (first op, later op, an add
  that made its node, a deleted node, the pre-check); the old "Ctrl+Z" text gone; the guard tests not weakened; the
  rolled-back, nothing-undone, facts and output-name live checks failing without the code; the new Designer scripts
  following the rules; GUIDE.md's exception matching the user's words.


### 2026-11-24: apply-edits-precheck, round 2 (round 1's fixes)

- **Scope:** `git diff ec5a5aa 369d9f5 -- . ':(exclude)PLAN.md' ':(exclude)ROADMAP.md'`.
- **How:** two Sonnet reviewers: the server, helpers, rollback and unit tests; the live checks and docs. No tests run,
  no probes: settled by reading. Not worth a fix: what one Ctrl+Z does right after `set_link_display` (unmeasured, and
  no doc states it); `history_facts.py` undoing the top step without checking it is its own (it can only hit an earlier
  self-test step); the hand-kept 60 s in the two Designer scripts; `test_set_function.py`'s `KEPT=` substring check;
  `ScriptAborted` printing no `KEPT=` line (older than the branch, rare).
- **Not verified:** none.
- **Resolutions assessed:** SRV-252, SRV-253, SRV-254, SRV-255, SRV-256, HLP-256, TST-842, TST-845, TST-846 and
  TST-847 hold; TST-843 and TST-844 hold but too narrowly (TST-848, TST-849), and four follow-ups
  (TST-850, SRV-257, SRV-258, TST-851) on SRV-252, SRV-253, SRV-255 and TST-842.
- **Findings:** TST-850 (1 Low-medium); SRV-257, SRV-258, TST-848, TST-849, TST-851 (5 Low); all generation 2.
- **Checked and found fine:** the template's names after `/simplify` (`_builtins` bound before the call's code; only
  the module body in SRV-257 can raise); the `KEPT=` lines reaching the agent only when nothing was undone, from their
  three print sites in apply_edits and set_function; each new test failing without its fix but TST-851's row; the
  facts check of the wait failing when the events stop; the clean-ups; the import block putting `sys.path` back;
  `categories.py`'s figure and order.

### 2026-11-24: apply-edits-precheck, round 3 (round 2's fixes, and GUIDE.md's Undo rule reworded)

- **Scope:** `git diff b656321 32cbed8 -- . ':(exclude)PLAN.md'`.
- **How:** one Sonnet reviewer; no tests run, no probes. Not reported: README's "Otherwise apply_edits and
  set_function say in their error what stays changed" overstating for 'not landed' and a first op failing (a
  generation-3 docs follow-up changing nothing anyone does: DECISIONS.md, Low-value findings); the template's names
  outside its guard (`_builtins`, `sys.stdout`, an exception whose `__str__` raises: contrived).
- **Not verified:** none.
- **Resolutions assessed:** TST-850, SRV-257, SRV-258, TST-848, TST-849 and TST-851 hold.
- **Findings:** none. Step 1's reviews are done (the `project-code-review` skill, step 7).
- **Unspecified** (in PLAN.md's Waiting for the user): the self-test's Edit > Undo, run in the user's Designer on
  Windows, is guarded by "the self-test graph is in the editor", not by "the top step is the self-test's own", as the
  reworded rule asks.
- **Checked and found fine:** the reworded rule is the user's sentence, the tools' own case matches the code, and no
  other doc keeps the old wording; the template's guard leaves the call's own error and prints the state; each fix's
  test fails without it.

### 2026-11-24: rollback-failed-calls, round 4 (step 2 of PLAN.md: the other tools' rollback, `sys.exit`)

- **Scope:** `git diff 32cbed8 73f3256 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the server, the plugin, the docs and the unit tests; the live checks. No tests run,
  no probes. Settled as wrong or not worth a fix:
  - the plugin's `run` reply changed (`sys.exit(0)` now `ok`) with `PROTOCOL` still 2: not a bug. The messages'
    shape is unchanged, `VERSION` rose for behaviour changes before with no protocol change (4 to 8 in 9446b2c), and
    a stale v8 plugin only gives the old behaviour (an error, the change kept). Raising `PROTOCOL` would refuse every
    call until Designer restarts;
  - the timeout case's 1 s limit before its change is made: `ADD` is a package scan and one `newNode`, milliseconds,
    and every run passed. The final check's parallel run would show it;
  - `categories.py`'s batch figure omitting the `sys.exit` checks: the two timing runs held them (28 checks each,
    the developer's report), and the comment's list only describes the category;
  - a script that unloads its package before it raises, its step then undone: the slot is the toolbar's own Undo,
    which Designer handles for a user's Ctrl+Z after closing a package; a very unlikely case.
- **Not verified:** none.
- **Resolutions assessed:** none in scope.
- **Findings:** SRV-259, SRV-260, TST-852, TST-853: 4 Low. A few Low: once fixed, step 2's reviews are done (the
  `project-code-review` skill, step 7).
- **Simplifications** (the branch's own code, fixed with the findings): `batch/checks.py` imports a function `after`
  that four locals of the module shadow (`run()` and `check_a_batch_failing_after_adds_and_connects_is_rolled_back`);
  `failed_calls.py`'s `ERROR = 'ERROR '` also matches the code tools' `--- ERROR ---` marker; `during_rollback(what:
  str)` could be `Literal['cancel', 'queue']`, as the script's `Args.what` is; `t = ''` in `failed_calls.py` is dead.
- **Checked and found fine:** the exit rule agrees in the plugin's `_run` and the template for `None`, `0`, `False`,
  `1`, `True`, strings, tuples and other exceptions, with `settrace(None)` still first; every name the template uses
  after the user's code goes through `_builtins`; `TAG_FORM` is true of `_tag()`; each new unit test fails without its
  change; every listed live check is there and fails without its behaviour; the cancel-during check's callback can't
  act on a later job; `after()` cleans up in a `finally`; no fixed sleeps.

### 2026-11-24: rollback-failed-calls, round 5 (step 3 of PLAN.md, and round 4's fixes)

- **Scope:** `git diff 73f3256 84a469f -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: 3a-3c with round 4's server fixes; 3d with round 4's fixes in the checks. No tests
  run. The lead's probe: `python3 scripts/read_crash_dump.py` on the kept dump of 2026-11-24 printed x11 `outputsi`
  and `outputsize` at `sp+0x018`, within `STACK_TOP`, and the database line naming port 9951's home: the docstring's
  claim holds. Settled as wrong or not worth a fix:
  - the guard matching the label and the tag's form, not the exact step: the check can't know its call's tag (TST-854),
    each check reads its call's change before sending, and a step of that form is the self-test's own;
  - no live check that sees the guard refuse: it would repeat the unit tests' guard (DECISIONS.md, Low-value
    findings); the developer saw both refusals fail a check in scratch runs;
  - nothing ties the stand-in rollback of the snippet's unit tests to `designer_rollback.py`: a rename there fails the
    whole `undo` category at once;
  - the checks' copies of the tools' labels: a drift fails the `undo` category loudly, naming the top step;
  - `put_back`'s docstring, "hit some other step": a step of the check's label now (fixed with the findings).
- **Not verified:** none. The fire-time `_top()` read before the trigger, where `edit_menu.py`'s docstring records
  that code run in the callback once broke the Undos (lsappinfo, a subprocess): two whole runs of `undo` passed (the
  developer); a runner repeats the category after round 5's fixes, and its result goes in the next round's log.
- **Resolutions assessed:** SRV-259 questioned by SRV-261; SRV-260, TST-852 and TST-853 hold, and so do round 4's
  Simplifications.
- **Findings:** INS-48, TST-855, SRV-261 (follows SRV-259, generation 2), TST-856, TST-857, TST-858: 6 Low, with
  TST-854 (Low-medium, the developer's) still open. A few Low: once fixed, step 3's reviews are done (the
  `project-code-review` skill, step 7). The longest chain still growing: SRV-259 → SRV-261, generation 2.
- **Unspecified** (in PLAN.md's Waiting for the user): whether the live-check skill's tainted-Designer rule reaches
  beyond probes: a Designer `alone.run` keeps open between internal-object checks and editing checks, and the tools'
  own rollback, which holds the toolbar's wrappers and calls its `undo()` slot within one job.
- **Checked and found fine:** the crash reader opens only the dump and `log.txt`, handles short or missing context
  and stack, stays readable by Python 3.9, and its tightened frame regex is no weaker; 3b and 3c say what the step
  says; `UNDONE` claims only what the rollback does and every quoter follows; the guard reads the top at fire time,
  Undo's or Redo's, escapes the label, takes the regex from the constants and fires or resends nothing on a refusal;
  every check's label is its tool's; the wrappers are dropped with the job.

### 2026-11-24: rollback-failed-calls, round 6 (the entire branch against main, the first Opus round)

- **Scope:** `git diff main...f78a1e4 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`.
- **How:** three Opus reviewers: the rollback's mechanism, the server, the helpers, the plugin and the docs with their
  unit tests; the rollback's live checks; step 3. No tests run. A runner's probe (round 5's Not verified): the `undo`
  category 20 times in one Designer on port 9976, its own, the fire-time `_top()` read before the trigger included:
  20 of 20 runs passed, 300 of 300 Undos and Redos sent once and shown within 0.5 s, no crash dump. The lead read its
  scripts (one run per process through `alone.run(undo.run, port=9976)`, the PASS and FAIL lines counted). Settled as
  wrong or not worth a fix:
  - an error inside `_top()` in the timer callback read as "never fired", and the Undo sent again: nothing fires, so
    the user's work is safe (step 3's choice, KISS);
  - the `rollback` fixture of `test_rollback.py` typed `types.ModuleType`: the project's pattern for loaded modules;
  - `history()` on an `undo-button` without a default action, a user's edit joining a code tool's group while its
    script runs an event loop, a callback the failed script scheduled making a step during the rollback, and the
    `KEPT=` advice when the batch made no step: unseen, and safe or the user's own Ctrl+Z either way;
  - `mcp_selftest_history` left loaded until the category's clean-up, the blocked save's file left in the scratch
    folder, `designer_rollback` left in Designer's `sys.modules`: no later check reads them.
- **Not verified:** on Windows, `batch/designer_scripts/during_rollback.py` starts the second client
  (`subprocess.run` of the self-test's `python.exe`) from inside Designer, a GUI process, with no
  `CREATE_NO_WINDOW`: each call may open a console window over the user's windows, in a Windows run in the user's
  Designer (2 to 5 in the queue check). There is no Windows here; what would check it: that `subprocess.run` from
  `execute_designer_code` on Windows, watching for a `ConsoleWindowClass` window.
- **Resolutions assessed:** TST-848 questioned by SRV-262; SRV-254 by SRV-263 and TST-864; SRV-260 by TST-866;
  TST-842 by TST-862 and TST-864; TST-845 by TST-863. The others in scope hold: SRV-252 to SRV-261 but those,
  HLP-256, TST-843, TST-844, TST-846, TST-847, TST-849 to TST-858, INS-48.
- **Findings:** INS-49, SRV-262 (follows TST-848, generation 3), SRV-263, SRV-264, TST-859 to TST-866, AGT-133: 13
  Low. More than a few: the developer fixes them, and Opus rounds review the fixes (the `project-code-review` skill,
  step 7). The longest chain still growing: TST-843 → TST-848 → SRV-262, generation 3.
- **Unspecified** (in PLAN.md's Waiting for the user): the tainted-Designer rule's reach, now with its places:
  `history_facts.py` (an event filter on internal menus, wrappers held, the `undo()` slot called) followed in the same
  Designer by `batch`'s editing checks, `undo_steps.py` by `set_link_display`, and a probe's own Undo of its top
  step, which the skill allows.
- **Checked and found fine:** every path from a failure to the error, none undoing another step (the top check, the
  invoke and the wait's start with no event processing between, an exact comparison, a fresh tag per call, the
  plugin's `draining`); the tag defined once and matched by every reader through the constants; the wait woken by
  the dropdowns' events with a safety-net limit; the wrappers held, the filter on menus only and removed; every
  approved live check there and failing without its behaviour; clean-ups; the crash reader opening only the dump and
  `log.txt`; `UNDO_REDO` never firing on a step that isn't the self-test's own, and every refusal named.

### 2026-11-25: rollback-failed-calls, round 7 (round 6's fixes)

- **Scope:** `git diff c6ad658 894f326 -- . ':(exclude)PLAN.md'`.
- **How:** one Opus reviewer; no tests run, no probes. Not reported: TST-866's "says what became of the step" being
  loose for "not ours" (a generation-3 docs follow-up changing nothing anyone does: DECISIONS.md, Low-value
  findings). The reviewer's Unspecified, `project_constants.py` now imported in Designer's Python by two of the
  self-test's Designer scripts with no doc saying it must stay importable there: settled by the lead as the docs of
  this branch's own change, its docstring saying so with TST-868's fix.
- **Not verified:** none new.
- **Resolutions assessed:** TST-865 questioned by TST-868, AGT-133 by AGT-134; INS-49, SRV-262, SRV-263, SRV-264,
  TST-859 to TST-864, TST-866 and TST-867 hold. A note under TST-865 on `history_facts.py`'s comment.
- **Findings:** TST-868 (follows TST-865, generation 2), AGT-134 (follows AGT-133, generation 2): 2 Low. A few Low:
  once fixed, an Opus round reviews the entire branch again (the `project-code-review` skill, step 7).
- **Checked and found fine:** every reader and writer of the tag but the unit tests below on the one definition;
  both Designer scripts import `project_constants.py` and `designer_rollback.py` by path and put `sys.path` back;
  `history_facts.py`'s guard reads the top before anything is installed and its check can't pass without the slot
  called, a wake and the Redo top its last step; `read` keeps the first of equal slices, as main's `read64` did, and
  opens no file; INS-49's and TST-860's tests fail without their fixes; no older test weakened.

### 2026-11-25: rollback-failed-calls, round 8 (the entire branch against main, Opus again)

- **Scope:** `git diff main...94da019 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`.
- **How:** three Opus reviewers, split as in round 6. No tests run. Two runners' probes, each in a Designer of its
  own, the lead reading their code:
  - port 9976: an Undo triggered through Edit > Undo, with a step B made between `trigger()` and the landing, in
    the same callback, in a later 0-ms callback, or by the next bridge job: `trigger()` changes nothing at once; the
    undo lands as Designer next processes events, a few tens of ms later, and takes the step on top then. B was
    undone in 8 of 8 runs where it was made before the landing (TST-873);
  - port 9977: a failed `apply_edits` on a graph not in the editor, rolled back, with Designer hidden and on screen,
    the editor holding another graph, nothing, or one opened earlier: in 14 of 14 runs the editor's current graph,
    its view and the dock titles stayed as they were, and a watch on view creation and title changes saw nothing
    during the call. A reviewer's suspicion that a rollback may switch the user's editor: settled as wrong.
  Settled as wrong or not worth a fix: `roll_back`'s docstring not naming 'Qt is quitting' for 'not landed' (a
  generation-3 docs follow-up changing nothing anyone does); `_with_undo`'s docstring on the plugin's tracer (style);
  `KEPT=` lines of a code tool's own output moved into the error (needs a script printing them); the rollback's undo
  sent without raising the main window (the Undo checks measured it landing inside a job's event processing).
  The lead's decisions on two leftovers of this branch, fixed with the findings: the Designer scripts put back the
  `sys.modules` entries they replace (`project_constants`, `designer_rollback`), and ROADMAP item 131's "wait for the
  camera's glide (~0.8 s)" says to wait on a callback, the figure only measured.
- **Not verified:** none new.
- **Resolutions assessed:** TST-861 questioned by TST-870, SRV-259 by TST-871, TST-854 by TST-873. All other
  resolutions in scope hold, rounds 6 and 7's included.
- **Findings:** TST-869, TST-870 (follows TST-861, generation 2), TST-871 (follows SRV-259, generation 2), TST-872:
  4 Low. TST-873 (follows TST-854, generation 2), Low-medium, measured: its fix is the user's to choose (PLAN.md,
  Waiting for the user), and asked at once.
- **Checked and found fine:** no path of the tools undoes a step that isn't the call's own: the rollback's top check,
  invoke and wait run with no event processing between, and its wait holds the user's input and every other job;
  every reader on the tag's one definition; the editor left as it was by a rollback; the crash reader on short,
  overlapping and moved dumps; every refusal of `UNDO_REDO` named.

### 2026-11-25: rollback-failed-calls, round 9 (step 4 of PLAN.md, `undo_edits`, and round 8's fixes)

- **Scope:** `git diff 26339bd dd0b353 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the server and Designer-side code with their unit tests; the docs, the rules and the
  live checks, with TST-873's recheck. No tests run. One runner's probes in a Designer of its own (port 9974), the
  lead reading their code:
  - every tool that doesn't go through `_with_undo`, the Undo dropdown read before and after one call: `describe_node`
    of an atomic or a library node adds 8 or 9 untagged steps (none for a function node), `set_link_display` 4, every
    other tool none (SRV-265);
  - `apply_edits`, then each of those, then `undo_edits()` and `undo_edits(include_others=True)`, 18 times in one
    Designer and once each in fresh ones: every first call refused naming those steps, every second undid them and
    the edit, Designer up, no crash dump; across `set_link_display` the saved file keeps the display change;
  - an undo landing through `undo_steps`, the Undo dropdown read at once and again after processing pending events,
    20 rounds: never different; `listed_steps.py` 20 times: `after` 25 and `first_after` true each time. A
    suspicion that the check reads the Undo list before it is refilled: settled as wrong.
  Settled as wrong or not worth a fix: a second `undo_edits` while the first's undo hasn't landed (its reply says not
  to, and the approved text says stop and say); `include_others` undoing what is in the way at that call, not what
  the refusal named (the user's choice "b"); README's category table not naming the new checks; `sweep_param`'s
  `edit=False` comment and `_undo`'s long docstring line (style).
- **Not verified:** none new.
- **Unspecified:** a session's subagents share its server, so `undo_edits`' memory: whether agents of one session are
  meant to share it; on a Windows run in the user's Designer, the self-test's `include_others` check would undo a
  step of the user's made since its refusal, and no doc says whether the user's "not a problem for me" covers it.
- **Resolutions assessed:** TST-873, and round 8's TST-869 to TST-872: they hold.
- **Findings:** SRV-265 (Medium, measured), SRV-266 (Low-medium, confirmed), TST-874, TST-875, TST-876 (Low,
  confirmed). Suggested order: SRV-265, SRV-266 with its test gap, then the three checks. The longest chain still
  growing: none (no finding questions a resolution).
- **Checked and found fine:** the approved rule verbatim in the four places; no agent-facing doc telling an agent to
  undo another way outside the two exceptions; the automatic rollback's strings and wait unchanged on the shared
  function; the per-step top check; same-named steps each seen landing; no step of the user's undone without
  `include_others`; the job untraced; the memory dropped and kept as the reply says; the read calls' classification;
  the hints, the `HINTS` row and README's count.

### 2026-11-25: rollback-failed-calls, round 10 (round 9's fixes)

- **Scope:** `git diff f48c38c f24d722 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers, split as in round 9: the code with its unit tests and SRV-265's and SRV-266's
  rechecks; the live checks and the descriptions, with TST-874 to TST-876's rechecks. No tests run. One runner's
  probe in Designers of its own (port 9974), the lead reading its code. It repeated, in each round: a misspelt
  `describe_node` (rolled back), a library and an atomic `describe_node`, an edit, `undo_edits(include_others=True)`,
  then a Redo of every step undone, through the history manager's `redo()` slot. In one variant, the rolled-back
  step was also redone and undone again. Each library package was unloaded first, so each round loaded it afresh.
  That was 150 rounds in four fresh Designers, 722 undos and redos: no crash, no crash dump, every redo landed, and
  the open packages went back each time. A reviewer's suspicion that undoing or redoing these steps may hit the
  double-unload crash: settled as wrong. The misspelt `describe_node`'s error ended with the UNDONE sentence each
  time (SRV-268, measured).
  Settled as wrong or not worth a fix: parallel calls swapping order in `STEPS` at the 25-step boundary, or a
  concurrent append lost to `STEPS[:] =` (very unlikely); `SessionStep`'s docstring not naming packages (not
  misleading); undoing a `describe_node` step after its package was unloaded by other means (needs an unusual action
  between the calls); `categories.py`'s dated 31 s for `batch` (a dated measurement; remeasured with the fixes, as
  the lead's decision on a leftover); `undo.py`'s long docstring line (style).
- **Not verified:** none new.
- **Unspecified:** whether Designer's Redo list is meant to survive a read tool's call. `describe_node` and
  `search_nodes`' first scan each add one step, so after `undo_edits` they clear the Redo list, as their 8 or 9
  untagged steps did before this branch.
- **Resolutions assessed:** SRV-265 questioned by SRV-267; SRV-266 by SRV-269; TST-876 by TST-878. TST-874,
  TST-875 and SRV-265's grouping and live checks hold.
- **Findings:** SRV-267 (follows SRV-265, generation 2), SRV-268 (measured), SRV-269 (follows SRV-266, generation
  2), TST-877, TST-878 (follows TST-876, generation 2), TST-879: 6 Low. So step 4's Sonnet reviews are done once the
  developer fixes them. The longest chains still growing: SRV-265 → SRV-267, SRV-266 → SRV-269, TST-876 → TST-878,
  each at generation 2.
- **Checked and found fine:** SRV-266's fix traced by hand over full and partial lists, each new test killing its own
  mutation; `describe_node`'s success path unchanged; `_library_index` wrapped only on its first, cached scan; every
  helper that makes or loads a package wrapped; the new checks' clean-up on failure, the second client's server and
  the 30 steps included; the descriptions' read list matching the `edit=False` sites; `undo_edits`' description at
  1,173 characters.

### 2026-11-25: rollback-failed-calls, round 11 (the entire branch against main, Opus, after step 4)

- **Scope:** `git diff main...b39b453 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`.
- **How:** three Opus reviewers: the rollback's mechanism, `undo_edits`, the server, the helpers, the plugin and
  `project_constants.py` with their unit tests; the live self-test with its unit tests; the crash reader with the
  docs, rules, skills and ROADMAP. No tests run, no probes: settled by reading.
  Settled as wrong or not worth a fix: `sys.exit(0.0)` counting as a normal end (contrived); after a Designer
  restart, old names in `STEPS` making a count above the listed edits refused once 25 new steps are listed (a smaller
  count works); `_session` as a TypedDict (`monkeypatch.setitem` needs a mapping). The `example` category's failing
  builds are now rolled back, a whole build's step with its library packages, and no run of it is recorded on the
  branch: the developer runs it in a scratch run with the fixes. The lead's decisions on two leftovers of this
  branch, fixed with the findings: the unit tests that append to the real `server.STEPS` reset it (no later test
  depends on it), and `categories.py`'s undated "16 s" for `link_display`, which took 47.5 s in round 10's scratch
  run, is remeasured.
- **Not verified:** none new.
- **Unspecified:** whether an agent asked to bring back steps `undo_edits` undid may trigger Redo from code, or asks
  the user: the rule forbids only Undo, and no tool redoes. Whether `undo_edits`' description or reply says that a
  file saved before the undo keeps what was saved, as `set_link_display`'s now does. The tainted-Designer rule's
  reach (round 5's Unspecified) gains two places: `undo_edits` holds the toolbar's wrappers and calls the history
  manager's `undo()` slot between editing calls, by design; round 10's probe called `redo()` between edits.
- **Resolutions assessed:** SRV-268 questioned by SRV-270, TST-873 by TST-882, TST-844 by TST-883. All other
  resolutions in scope hold, SRV-267, SRV-269 and TST-878 (generation 2) included.
- **Findings:** SRV-270 (follows SRV-268, generation 2), SRV-271, TST-880, TST-881, TST-882 (follows TST-873,
  generation 3), TST-883 (follows TST-844, generation 2), INS-50, INS-51: 8 Low, all confirmed by reading. More than
  a few, so after the fixes, Opus rounds review them, then the entire branch again. Suggested order: SRV-270,
  SRV-271, then the docs and the tests. The longest chain still growing: TST-854 → TST-873 → TST-882, at generation
  3.
- **Checked and found fine:** no path undoes a step that isn't the call's or the session's own (the top read before
  each undo, no events between it, the invoke and the wait, the prefix planned in one job); `STEPS` added only when
  the script is built and dropped on `undone`, `gone` and a rollback's `undone`; `_failure`'s lookup on the
  template's `UndoGroup(%r)`; every tool now in `_with_undo` keeping its success output; the plugin's `sys.exit`
  test matching the template's; every live check failing without its code and cleaning up on failure; the
  `sys.modules` put-backs; `UNDO_REDO`'s guard and put-back; the waits; step 4's rule verbatim in its four places
  and no other route to undo in any agent-facing text; README's count and rows; the crash reader opening only the
  dump and `log.txt` in the database, never the `__sentry-event`.

### 2026-11-25: rollback-failed-calls, round 12 (round 11's fixes)

- **Scope:** `git diff 997a46b 6bd5e82 -- . ':(exclude)PLAN.md'`.
- **How:** one Opus reviewer, with round 11's eight rechecks, the two leftovers and the user's two answers of
  2026-11-25 (Redo from code allowed; nothing said of a saved file). No tests run, no probes: settled by reading.
  Settled as wrong or not worth a fix: two test names saying a little more than their checks
  (`test_the_one_undo_history_is_said_shared_by_every_package`, `test_no_rule_steers_an_agent_from_undo_edits`); the
  self-test's failure messages `NOT_OURS top=%r` and `history_facts.py`'s showing escapes under the invisible form
  (no pattern reads them). The lead's decision on a leftover, fixed with the finding: GUIDE.md's Redo sentence, the
  user's rule, gets a test pinning it, as the Undo rule has.
- **Not verified:** none new.
- **Unspecified:** a step brought back by a Redo no longer counts as the session's, since the tool dropped its name
  when it undid it: `undo_edits` then names the agent's own step as another's. Whether a Redo from code first
  checks that the Redo list's top is the agent's own step (a Ctrl+Z of the user's after `undo_edits` puts theirs
  there); GUIDE.md describes no way to redo. Round 10's Unspecified (a read's step clears the Redo list) weighs more
  now that GUIDE.md names bringing back undone steps as Redo's use.
- **Resolutions assessed:** SRV-271 questioned by SRV-272. The other seven hold (SRV-270, TST-880 to TST-883,
  INS-50, INS-51), and so do both leftovers (`STEPS` reset per unit test; `link_display`'s time).
- **Findings:** SRV-272 (follows SRV-271, generation 2), Low, confirmed. Only a few Low, so the Opus rounds on round
  11's fixes are done once the developer fixes it; then an Opus round of the entire branch. The longest chain still
  growing: TST-854 → TST-873 → TST-882, at generation 3.
- **Checked and found fine:** no reader of the new quoting still expects `repr`'s form; the constants-switching test
  leaves nothing switched for later tests; `READ_UNDONE` against each of the seven reads; GUIDE.md's Redo sentence
  against the user's words and the Undo rule; TST-880's row failing with the label emptied; the conftest reset
  shared by `server`, `core` and `undo`.

### 2026-11-25: rollback-failed-calls, round 13 (the entire branch against main, Opus)

- **Scope:** `git diff main...5bbb8ba -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`.
- **How:** three Opus reviewers, split as in round 11. No tests run. One runner's probe in Designers of its own
  (port 9974), the lead reading its code. Each of 81 calls of `execute_designer_code` added a node, slept 2 s, then
  ran k trivial statements, with `timeout_s=1`. For k = 2 to 39, the abort landed before the C commit and the step
  stayed open (SRV-273, measured). With it open, later edits listed no step; Designer's undo took back the newest
  change and listed nothing; one `commitTransaction()` listed it all. No crash dump in about 40 restarts.
  Settled as wrong or not worth a fix: two other checks blind the same way as TST-884 (`batch`'s and
  `graph_edit_create`'s "an add whose params fail leaves no node"), as a unit test holds the guard
  (`test_an_add_whose_node_cant_be_removed_again_says_so_apart_from_its_error`); item 112's pointer to `UNDO_REDO`'s
  comment, the fact being in the snippet below it (a generation-4 docs follow-up); a crash test's name saying more
  than its order check (as round 12 judged). The lead's decisions on two leftovers of this branch, fixed with the
  findings: `minidumps.py`'s docstring naming `test_old_python.py`, which never imports it; `.claude/rules/python.md`'s
  Typing naming `designer_rollback.py` among the files run on Designer's Python.
- **Not verified:** none new.
- **Unspecified:** none new. Step 4's "no hard block" in the code tools is recorded only in PLAN.md: for the user at
  convergence, as what must outlast the branch.
- **Resolutions assessed:** SRV-264 questioned by SRV-274, TST-877 by TST-885. All other resolutions in scope hold.
- **Findings:** SRV-273 (High, measured); SRV-274 (follows SRV-264, generation 2), TST-884, TST-885 (follows
  TST-877, generation 2): 3 Low. With a High, the developer fixes them, then Opus rounds on the fixes, then the
  entire branch again. Suggested order: SRV-273 first.
- **Checked and found fine:** the docs, rules, skills and the crash reader, with nothing to report; no path undoes a
  step that isn't the call's or the session's own while each step commits; the memory of the session's steps and
  `_failure`'s lookup; the quoting at every site; every live check failing without its code and cleaning up; the
  waits.


### 2026-11-25: rollback-failed-calls, round 14 (round 13's fixes, their follow-ups, the user's changes, the fallback)

- **Scope:** `git diff 8b26222 8c3a6cf -- . ':(exclude)PLAN.md'`.
- **How:** two Opus reviewers: the server, the rollback, the plugin and the unit tests; the live self-test and the
  docs. Their claims were the approved texts and the user's later instructions of 2026-11-25, given whole. No tests
  run, no probes: settled by reading, SRV-275 with round 13's measurement of nested transactions.
  Settled as wrong or not worth a fix: a step undone, redone, then pushed below the 25 listed steps keeping its mark,
  so a count reaching past the list gets FEWER instead of the refusal (undo, a Redo from code and 25 more steps; not
  a regression: the step was dropped before); the timeout check's `end` guards disagreeing (`if end` against `end >
  0`), seen only after a failure no run has had; `BIND_GRAPH` left bound when `undo_top.py` fails (no later check
  reads it); `test_types.py`'s docstring listing the files run in Designer without "only"; SRV-273's "Also covered"
  superseded by its later note (the entry reads right top to bottom); SRV-273's "from k = 34", which a reviewer
  couldn't reproduce by reading (the test fails without the fix either way).
- **Not verified:** none new.
- **Unspecified:** the template ignoring the private C calls' results, raised by a reviewer, is settled by the
  user's choice for SRV-276 (the public functions raise).
- **Resolutions assessed:** SRV-273 questioned by SRV-275, SRV-276, SRV-277, TST-886 and TST-887; its main path
  holds (no traced event between the code's end and the commit). SRV-274, TST-884 and TST-885 hold, and so do the
  user's six changes.
- **Findings:** SRV-275 (Low-medium), SRV-276, SRV-277, TST-886, TST-887 (each following SRV-273, generation 2),
  TST-888: 5 Low, all confirmed. The user chose SRV-276's fix at once (2026-11-25, "ok go ahead"): the public
  transaction functions with tracing off, the private names, the fallback and its check dropped. More than a few, so
  Opus rounds on the fixes follow, then the entire branch again.
- **Checked and found fine:** sd's private transaction functions being ctypes calls that run no Python frame; the
  template's frame untraced from its first line, both branches reaching the commit with no traced event;
  `SystemExit` and code setting its own tracer; the fallback's binding falling back whole; `_failure`'s lookup
  matching only the template's line; the names guard; the marks on undone steps; the redone check and its Designer
  scripts; the example through `sd_run`; `CREATE_NO_WINDOW` and its test; the docs of the user's decisions.

### 2026-11-25: rollback-failed-calls, round 15 (round 14's fixes)

- **Scope:** `git diff 27c511e 3ac7974 -- . ':(exclude)PLAN.md'`.
- **How:** one Opus reviewer, its claim the approved texts with the user's later instructions of 2026-11-25 (the
  public transaction functions with tracing off; `set_link_display` left as it is), sd's `sdhistoryutils.py` and the
  plugin's tracer read. No tests run, no probes.
  Not worth a fix (each a generation-3 follow-up of SRV-276 or SRV-277, changing nothing anyone does): no test fails
  with the open's tracing-off pair removed (the code is right by reading; the fakes' preamble and the live check's
  deadline can't reach the open), noted under SRV-276; the `include_others` check's docstring saying a step made
  meanwhile is never undone, where README states the window right; two docstrings saying "tracing is off from their
  code's end to the commit", where what holds is that no traced event comes, as `_with_undo`'s says; a test's tags
  built from `'a'`/`'b'`, which fails loudly if the alphabet changes; two fakes typed `type`; three self-test scripts
  opening their own `UndoGroup` through `sd_run`, in an agent's own Designer only.
- **Not verified:** none new.
- **Unspecified:** none new.
- **Resolutions assessed:** SRV-275, SRV-276, SRV-277, TST-886, TST-887 and TST-888 hold. A refused open raises
  before the code runs and the plugin puts the tracer back; a refused commit can come only from code that commits
  more than it opens.
- **Findings:** none. So the Opus rounds on the fixes are done; next, an Opus round of the entire branch.
- **Checked and found fine:** the template's preamble, open, both branches and commit, with no traced event between
  the code's end and the commit; Designer's `__import__` reached only in the preamble or with tracing off; code
  setting its own tracer or raising `SystemExit`; the fakes tracing as sd's functions do; no stale reference to the
  private names, the fallback or its check; the installed plugin byte-identical to the repo's.

### 2026-11-25: rollback-failed-calls, round 16 (the entire branch against main, Opus)

- **Scope:** `git diff main...3f49484 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`.
- **How:** three Opus reviewers, split as in round 13, their claims the approved texts with the user's later
  instructions of 2026-11-25. No tests run, no probes.
  Not worth a fix, or the lead's leftovers fixed after: `check_undo_edits_refuses_calls_beyond_the_steps_listed`
  sends `include_others` with no guard, which could undo a user's change only on a Windows run in their Designer
  with its setup failing partway or the refusal regressed (two reviewers; the lead's decision: guard it, one
  condition, as it can touch the user's work); `_failure`'s docstring still says `code` names the step "in its undo
  group" (the lead's decision: reword); TST-887's test name saying more than its check; the fire-time `_top()` read
  before `trigger()`, settled by round 6's probe and measured again only by the final check's pool run.
  Both leftovers fixed after the round: the check sends `include_others` only when its two edits and all 30 of
  `BURY`'s steps were made (a scratch run with `BURY` failing after 10 sent it before the fix, and not after);
  `_failure`'s docstring names the template's `_step = ...` line. `batch` passed whole.
- **Not verified:** none new.
- **Unspecified:** `describe_node` and `search_nodes` keep `read_only=True` while each atomic or library describe,
  and the first scan, adds an undo step and so clears the Redo list; `_tool`'s docstring defines read-only without
  naming the undo history. It predates the branch (8 or 9 untagged steps on main). The user, 2026-11-25 ("agree
  with all"): the hint stays, and `_tool`'s docstring says a read's own undo step doesn't count as a change.
- **Resolutions assessed:** every resolution in scope holds, SRV-252 to SRV-277, HLP-256, INS-48 to INS-51 and the
  TST entries included; the installed plugin byte-identical to the repo's.
- **Findings:** none. The reviews look converged (the `project-code-review` skill, step 7).
- **Checked and found fine:** no path undoes a step that isn't the call's or the session's own; no traced event
  between the code's end and the commit, nor around the open; the memory of the session's steps and its marks;
  every tool in `_with_undo` keeping its output apart from the plan's additions; every unit test and live check
  failing without its code and cleaning up; no check depending on another's state; step 4's rule verbatim in its
  four places and no other route to undo in any agent-facing text; the user's later rules said where agents read
  them; README, GUIDE, the rules, the skills and ROADMAP against the code; the crash reader opening only the dump
  and `log.txt`.
---

## High

- [x] **SRV-273 · A timeout's or cancel's abort can skip the commit of a call's undo step, which stays open and swallows every later step** · `mcp_server/server_tools/core.py` (`_with_undo`'s template), `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py` (`_make_tracer`) · measured · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** The plugin's tracer raises its abort once, at the 64th trace event after a cancel or timeout, in any
    frame but the plugin's. When the code's last statement is a long C call, the countdown runs past the end of the
    code into the template's `with _SDH.UndoGroup(...)` exit. sd's `UndoGroup.__exit__` and `commitTransaction` are
    Python, and `sd.getContext()` runs `from sd import context` through importlib's and shiboken's Python frames on
    every call, so about 38 traced events come before the C commit. The plugin's docstring says context exits "such
    as UndoGroup committing its transaction, run to the end", and `_with_undo`'s says "once the step has committed".
  - **Measured** (a runner's own Designer, round 13's log). The code added a node, then `time.sleep(2)`, then k
    trivial statements, with `timeout_s=1`. For k = 2 to 39 the abort landed before the C commit, in
    `getContext`, its import machinery, `commitTransaction`, `__exit__`, or the `with` line. In each case the step
    was never listed, the node stayed, and nothing was rolled back. For k = 0, 1 and 40 to 80 the call was rolled
    back. With the transaction left open:
    - an `apply_edits` after it applied but listed no step of its own;
    - an `sd_run` edit outside any group listed no step either;
    - `undo_edits()` sent the undo of the session's newest listed step, an older one, which never showed landing.
      Designer's undo took back the open transaction's newest change instead, the `sd_run` node, and the reply
      said "Nothing undone".
    - Nothing closed the transaction by itself. One `commitTransaction()` from `sd_run` listed it, under the
      opening call's name, with every change made since.
  - **Scenario.** In the user's Designer, an agent's `execute_designer_code` ends with a compute or an export and
    times out, or is cancelled. Until Designer restarts, no later step of the agent's or the user's is listed:
    - the rollback can't take back anything;
    - `undo_edits` misreports what it did;
    - the user's Ctrl+Z silently removes their newest change.

    The same window is there for every call in `_with_undo`. That includes `describe_node` and `search_nodes`' first
    scan, which the branch put in an undo group (60 s timeouts).
  - **Fix.** Make the commit one the abort can't skip, for every call in `_with_undo`. Prefer the server's
    template, if a way there closes the window whole: the measured window includes the `with` line itself. If only
    the plugin's tracer can close it, for example by raising only in the user's code's frames, stop and report. A
    plugin change reaches the user's plugin folder, and only the lead installs it, on the user's word. The fact
    about an open transaction goes in `designer_rollback.py`'s docstring. A live check: the measured case, with the
    step listed and rolled back for every k.
  - **Resolution: done**, in the server's template, no plugin change.
    - **Measured first** (the developer's own Designer): on the old template, k = 0 to 8 statements after the sleep
      left the step open, the abort landing in getContext's import, `commitTransaction`, `__exit__` or the `with`
      line. From k = 9 it landed in the code. The fixed template, swept over k = 0 to 80, listed each step with its
      node or rolled it back, with none left open.
    - **Test:**
      - `test_plugin.py` runs the template under the plugin's real tracer for k = 0 to 79. It failed on the old
        template from k = 34.
      - `batch`'s `check_a_timeout_never_leaves_a_calls_step_open` first measures where a 64-statement call's
        abort lands (`end`). It then aims five calls at events 1, 3, 5, 7 and 9 after the code: on the old template,
        the `with` line, `__exit__`, `commitTransaction`, getContext and its import. It failed on the old template
        ("left open by [1, 3, 5, 7, 9]") and passes on the fix, `batch` taking 66 s.
      - A unit guard keeps the template's names apart from the helpers'.
    - **Cause:** `UndoGroup.__exit__` reaches the C commit through traced Python frames (`commitTransaction`,
      `sd.getContext` and its import machinery), and the tracer's abort can land on any of them.
    - **Fix:** the template binds sd's C transaction functions before the code runs. It sets its own frame's
      `f_trace` to None and commits in both branches, so no traced event lies between the code's end and the
      commit. `designer_rollback.py`'s docstring states what an open transaction does.
    - **Also covered:** every call in `_with_undo`, reads included. The template relies on two private names of
      sd's context (`SDHistoryUtils_newTransaction`, `SDHistoryUtils_commitTransaction`): a Designer that renames
      them fails every wrapped call, which the self-test shows at once.
    - **Note (2026-11-25):** the plugin's `_make_tracer` docstring, which said context exits such as UndoGroup's
      commit "run to the end", says an abort landing inside a context exit's own Python code cuts it short, and
      points here (docstring only). The lead reinstalled the plugin on the user's word ("yes reinstall the plugin if
      needed"), the installed copy matching the repo's.
    - **Note (2026-11-25):** the user asked for a fallback and a check ("yes add the fallback and the check, even it
      the fallback will kick in in a later designer version i still want to know that we relied on fallback and
      we'll find again what functions to call and fix it properly"). When sd's context lacks either C function
      (`TRANSACTIONS` in `core.py`), the template commits through sd's `UndoGroup`, its window included.
      `batch`'s designer facts check `check_sds_context_has_the_functions_the_steps_commit_through` fails naming the
      missing ones and saying the tools fell back; it failed with a name misspelt and passes. Two unit tests in
      `test_rollback.py`: without the names, a call commits through `UndoGroup` (seen failing first); with them,
      `UndoGroup` is never used (seen failing with the template's name misspelt).
  - Questioned by SRV-275, SRV-276, SRV-277, TST-886 and TST-887 (2026-11-25).
  - Note (2026-11-25): its "`batch` taking 66 s" was wrong. Remeasured for TST-886 in Designers just started, the
    category takes about 30 s with the same checks.

## Medium-high

## Medium

- [x] **SRV-265 · `describe_node` and `set_link_display` leave untagged steps, which `undo_edits` takes for someone else's** · `mcp_server/designer_helpers/describe.py` (the temporary package), `mcp_server/server_tools/layout.py` (`set_link_display`'s reload), `mcp_server/designer_rollback.py` (`undo_session`) · measured · found 2026-11-25 by two reviewers (Sonnet)
  - **Defect.** The server remembers only the calls `_with_undo` wraps. Measured in a runner's own Designer (round
    9's log), `describe_node` of an atomic or a library node leaves 8 or 9 steps with no tag: `Reference package`,
    `Set User Package`, `Add Atomic Node` or `Add Instance Node`, `Unset User Package`, `Unreference package`,
    `Unknown`, and for a library node `Open Package(s)`. A function node leaves none. `set_link_display` leaves 4:
    `Unset User Package`, `Unreference package`, `Unknown`, `Open Package(s)`. No other tool leaves any. After either
    tool, `undo_edits()` refused in every run, naming those steps as not the session's and telling the agent to ask
    the user.
  - **Scenario.** An agent calls `apply_edits`, then `describe_node` (as GUIDE.md advises before an edit), then wants
    its edit back. `undo_edits()` refuses and has the agent ask the user about steps the user never made. With the
    user's yes, `include_others` undoes them (no crash in 18 runs). Across `set_link_display`, the graph goes back to
    before the display change while the saved file keeps it.
  - **Fix.** Make these tools' steps the session's where that is safe: run them in a tagged undo step of their own
    (`_with_undo(..., edit=False)`), after measuring whether one undo group holds all their steps and whether undoing
    it is safe (`describe.py`, `_unload_new_packages`: unloading a package twice crashed Designer). Where it isn't,
    say so where the agent reads it: the tools' and `undo_edits`' descriptions, and the refusal naming those steps as
    Designer's own, from these tools.
  - **Resolution: done**.
    - **Measured first** (the developer's own Designer): `describe_node` run inside one tagged undo group leaves one
      step, for atomic and library nodes alike, and none for a function node. Undoing that step put the open
      packages back each time, in 3 rounds over four definitions. A Redo after it, and a failing describe rolled
      back, also left Designer up, with no crash dump. `set_link_display`'s reload is two bridge calls by design, so
      one group can't hold it.
    - **Test:** live, all seen failing before the fix:
      - `batch`'s `check_undo_edits_takes_describe_nodes_steps_along_uncounted` (refused, naming `'Set User
        Package', 'Unknown', 'Reference package', ...`);
      - `link_display`'s `check_undo_edits_names_a_reloads_steps_as_designers_own` (the refusal had no note);
      - `batch`'s `check_undo_edits_takes_search_nodes_scan_along_uncounted`, which uses a second client so the
        first library scan runs there.

      Unit, in `test_undo_edits.py`, also seen failing: `describe_node`'s step remembered as a read, `search_nodes`'
      scan remembered as a read, the refusal's note on a reload's steps, and the reload remembered.
    - **Cause:** the server tagged only the calls `_with_undo` wraps. `describe_node`, `search_nodes`' first library
      scan and `set_link_display`'s reload ran outside it, and they make Designer's own steps through temporary or
      reloaded packages.
    - **Fix:**
      - `describe_node` (`discovery.py`) and `_library_index`'s `list_atomic()` call (`search_nodes`) run in
        `_with_undo(..., edit=False)`. Their steps are reads: undone along the way, uncounted, marked.
      - `set_link_display` takes the lead's "say so" path. Its reload sets `_session['package_reloaded']`. After that,
        `undo_edits`' refusal names the steps among `RELOAD_STEPS` (the four names measured) as Designer's own steps
        of that reload, not the user's.
      - `set_link_display`'s and `undo_edits`' descriptions say so, and `undo_edits`' lists `describe_node` and
        `search_nodes` among the reads.
    - **Also covered:**
      - `search_nodes`' scan, found by the developer's `/simplify`: with no compositing graph in the editor, it left
        7 untagged steps. Grouped, it leaves one, and undoing it was safe in 3 rounds. The runner's probe had a graph
        open.
      - Every helper that makes a package was searched; `create_graph` was already wrapped.
      - A `describe_node` that fails after making its package is now rolled back, its error ending with the UNDONE
        sentence, as `preview_node`'s does.
      - The other categories' checks of these tools pass (45).
      - Reload steps are matched by Designer's English step names, so in another UI language the note doesn't
        show, and the refusal still names the steps.
  - Questioned by SRV-267 (2026-11-25).

## Low-medium

- [x] **TST-850 · The fake loop returns when its limit fires, whether or not the limit is wired to quit the wait** · `tests/unit/history_fakes.py:276-281`, `mcp_server/designer_rollback.py:101` · confirmed · follows TST-842, generation 2 · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** After a pass with no `quit()`, `Designer.pass_events` emits the active timer's `timeout` and returns 0,
    whatever `timeout` is connected to; a real `QEventLoop.exec` returns only on `quit()`.
  - **Scenario.** `limit.timeout.connect(loop.quit)` is dropped in `_undo`: the never-lands test still passes (clock
    60, 'not landed'), while in Designer a rollback whose undo never lands blocks its main thread for good, untraced,
    so no cancel reaches it.
  - **Fix.** Have the fake fail ("the loop would wait forever") when the timer's `timeout` didn't quit the loop.
  - **Resolution: done**.
    - **Test:** the fake `Designer.pass_events` raises "the loop would wait forever: its timer's timeout doesn't quit it"
      when the timer it fired didn't call `quit()`; with `limit.timeout.connect(loop.quit)` removed,
      `test_an_undo_that_never_lands_is_sent_once_and_said_once_the_limit_is_over` passed on the old fake and fails on
      the new one.
    - **Cause:** the fake returned from `exec` after firing the timer, whatever it was connected to.
    - **Fix:** the fake above.
    - **Also covered:** the landing tests' event-filter wake (TST-842) still pinned.

- [x] **SRV-252 · A rollback that fails after sending the undo tells the agent the ops stay applied and to press Ctrl+Z** · `mcp_server/designer_rollback.py:135-136`, `mcp_server/server_tools/core.py:366` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `roll_back` returns `'failed: ...'` for any error of its own, also after `slot.invoke` sent the undo
    (`_top(found.redo)`, `loop.exec` and `removeEventFilter` can still raise), and `_failure` maps it to the helpers'
    `KEPT=` text: "ops 0-N were applied (added: ...); while its undo step is the newest, Ctrl+Z reverts the whole
    batch". The `failed:` text itself is shown nowhere.
  - **Scenario.** The undo lands, then the wait raises: the graph is rolled back, the agent is told its ops stay and
    to press Ctrl+Z, which would undo the previous step, possibly the user's; the listed "added" nodes no longer
    exist. A broken rollback (a Designer update) never shows why.
  - **Fix.** Tell apart a failure before the undo was sent ('failed', as today) from one after it (the 'not landed'
    text: look, don't undo again), and put the rollback's own error in the error.
  - **Resolution: done**.
    - **Test:** `test_an_error_once_the_undo_was_sent_is_said_as_not_seen_landing` and
      `test_an_error_clearing_up_after_the_undo_landed_still_says_undone` (`tests/unit/test_rollback.py`), and the
      `_failure` rows for `not landed: ...` and `failed`, each failing before the fix.
    - **Cause:** every error of the rollback's own became 'failed', which the server showed with the helpers' `KEPT=`
      text and its Ctrl+Z advice, never with the reason.
    - **Fix:** an error once the undo was sent returns 'not landed: <why>' (look first, don't undo again, no `KEPT=`
      text); a clean-up error after the outcome is known is swallowed; every state but 'undone' and 'not ours' says
      why, shown in the error (`NOT_LANDED % why`, `NOT_RUN % why`).
    - **Also covered:** Qt quitting now says so instead of "after 60 s"; 'no history' became a 'failed: ...' with its
      reason.
  - Questioned by SRV-258 (2026-11-24).

- [x] **SRV-253 · The rollback's template calls `print`, `exec`, `compile` and `__import__` from the script's own globals** · `mcp_server/server_tools/core.py:340-353` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The call's code runs with `exec(..., globals())`, and the `except` block then looks up `__import__`,
    `exec`, `compile` and `print` in those same globals, outside any `try`; so does `_rollback["roll_back"]`.
  - **Scenario.** A script that did `from re import *` (`re.__all__` has `compile`) raises: `compile(ROLLBACK, ...,
    "exec")` calls `re.compile` with three arguments, its TypeError replaces the script's error, and nothing is
    rolled back. A script that rebinds `print` does the same.
  - **Fix.** Bind what the template needs before the call's code runs (for example `import builtins as _b`), or guard
    the whole `except` body and re-raise the call's own error after it.
  - **Resolution: done**.
    - **Test:** `test_a_call_rebinding_builtins_is_still_rolled_back_and_its_own_error_raised` (`from re import *`,
      then `print`, `exec`, `__import__` rebound, then a raise); with the template's bare names put back it fails with
      a TypeError replacing the call's ValueError (run after `/simplify`).
    - **Cause:** the `except` block looked its names up in the script's globals.
    - **Fix:** the template imports `builtins as _builtins` before the call's code, and the `except` block calls only
      `_builtins.__import__`, `_builtins.exec(_builtins.compile(...))` into a fresh dict and `_builtins.print`, then
      re-raises; `roll_back` catches its own errors.
    - **Also covered:** the rollback's own lookup `_rollback["roll_back"]` runs in that fresh dict.
  - Questioned by SRV-257 (2026-11-24).

- [x] **HLP-256 · `set_function`'s error says what stays changed, and the rollback then says nothing changed** · `mcp_server/designer_helpers/functions.py:598` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `raise RuntimeError('%s; %s keeps its new function, and the inputs set so far' % (e, name))` goes
    through `_with_undo`: when the rollback undoes the step, `_failure` appends UNDONE, so the error reads "... keeps
    its new function, and the inputs set so far. Nothing changed in Designer: ...". The module docstring
    (`functions.py:19-21`) and `set_function_resource`'s (~551-555) say the same as the error. `edits.py:487`'s "node
    %s could not be removed again ..., delete it by hand" is the same pattern (rare: `deleteNode` failing right after
    `newNode`).
  - **Scenario.** An inputs' value fails after an existing function graph's output node moved: the agent reads both
    that the function stays and that nothing changed.
  - **Fix.** Print what stays on a `KEPT=` line, as apply_edits now does, so it shows only when nothing was undone,
    and say so in the two docstrings.
  - **Resolution: done**.
    - **Test:** `test_set_function.py::test_an_input_not_made_leaves_an_existing_function_graph_with_its_new_function`
      (now the bare error and a `KEPT=` line) and `test_an_add_whose_node_cant_be_removed_again_says_so_apart_from_its_error`,
      each failing before the fix.
    - **Cause:** the helpers put what stays in the exception's text, which the server can't hide after a rollback.
    - **Fix:** `functions.py` and `edits.py` print it on a `KEPT=` line and raise the base error; the server shows it
      only when nothing was undone; the module's and `set_function_resource`'s docstrings say so.
    - **Also covered:** the helpers' raise texts searched (keep, stay, left, by hand, applied, was added): batch.py,
      functions.py and edits.py were the three; "nothing was applied" refusals hold either way.


- [x] **TST-842 · No test sees the rollback's wait woken by Designer's events** · `tests/unit/history_fakes.py:188-196, 244-267`, `mcp_server/designer_rollback.py` · confirmed · found 2026-11-24 by two reviewers (Sonnet)
  - **Defect.** The fake `QEventLoop.exec` returns after each pass whether `quit()` was called or not, so removing
    `self.loop.quit()` in `_Changed.eventFilter`, or the `installEventFilter` loop, passes every unit test. No live
    check measures that the dropdowns' ActionRemoved/ActionAdded arrive and wake the wait, which the module's
    docstring states as a Designer fact.
  - **Scenario.** The wiring breaks, or a Designer update stops those events: each rollback waits the whole 60 s
    limit, then reports 'undone'; every test still passes, only slower.
  - **Fix.** Make the fake `exec` return only once `quit()` was called during its pass (else fire the limit) and
    assert no time passed in the landing tests; a "designer facts" live check that an undo of a committed step wakes
    a filter on the dropdowns before any limit.
  - **Resolution: done**.
    - **Test:** the fake `QEventLoop.exec` returns before the limit only if `quit()` was called in its pass, and the
      landing tests assert no time passed; without `self.loop.quit()` both fail at 60 s, without the
      `installEventFilter` loop they fail too. A "designer facts" live check (`batch/designer_scripts/history_facts.py`):
      an undo of the newest step through the manager's slot wakes the rollback's own filter before its limit
      (measured: the limit still running, the step on top of Redo).
    - **Cause:** the fake loop returned whether woken or not, and no live check measured the events.
    - **Fix:** the fake and the facts check above.
    - **Also covered:** the stray-changes test asserts the same.
  - Questioned by TST-850 (2026-11-24).
  - Questioned by TST-862 (2026-11-24).
  - Questioned by TST-864 (2026-11-24).

- [x] **TST-854 · GUIDE's Undo from a script doesn't say how to tell the top step is your own** · `mcp_server/GUIDE.md:545-553` · confirmed · found 2026-11-24 by the developer (Opus)
  - **Defect.** The core rule (`GUIDE.md:9-13`), reworded in this branch, reads "never trigger Undo unless the top
    step is your own", and sends the reader to "the scripting part, Undo from a script" for how. That part says how
    to find and schedule Edit > Undo, not how to read the top step or recognise one's own. A call's step is named
    with its `undo_label` and a random tag (` #` and 8 hex digits), which the call's reply doesn't give.
  - **Scenario.** An agent's script made a step in the user's Designer, and the agent wants it undone. Following the
    scripting part, it triggers Edit > Undo without reading the top step; if the user made a step since, Undo takes
    the user's.
  - **Fix.** In Undo from a script: give the call a unique `undo_label`; before triggering, read the Undo dropdown's
    top (the toolbar's `undo-button`, its `defaultAction().menu()`, the `QAction` wrappers held, as
    `mcp_server/designer_rollback.py` reads it); trigger only when its text is the label followed by the tag's form;
    otherwise don't, and tell the user. Within GUIDE's budget.
  - **Resolution: done**.
    - **Test:** none can fail on a guide's text; settled by reading. It rests on the `batch` facts (a step's name is
      exact, its tag included), `undo_label`'s description (built from `TAG_FORM`) and the `undo` category's guard,
      which reads the top in the callback as `designer_rollback.py` does and was seen refusing in step 3's runs.
    - **Cause:** the core rule pointed to Undo from a script, which said how to schedule Edit > Undo but not how to
      recognise one's own step.
    - **Fix:** Undo from a script: a unique `undo_label`; the step named with it and a tag of the form its description
      gives, which the reply doesn't show; the top step's name read first in the callback, as `designer_rollback.py`
      reads it; a trigger only on the label followed by the tag's form, otherwise none and the user told; a Redo read
      the same way. The core rule's pointer: "To tell your own step and trigger Undo from code". The user's sentence is
      unchanged, and the core stays within its budget.
    - **Also covered:** no other doc tells an agent how to trigger Undo.
  - Questioned by TST-873 (2026-11-25).

- [x] **TST-873 · An Undo triggered through Edit > Undo takes the step on top when it lands, not the one checked** · `tests/test_all_tools/common.py` (`UNDO_REDO`'s `_fire`), `mcp_server/GUIDE.md` (scripting part, Undo from a script) · measured · follows TST-854, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** `_fire` reads the dropdown's top, then calls `trigger()` and returns; GUIDE.md tells an agent to do
    the same. The runner's probe (round 8's log): `trigger()` changes nothing at once, the undo lands as Designer next
    processes events, a few tens of ms later, and it reverts the step on top then. A step made in between, in the same
    callback or by a bridge job starting 30 ms or more after the trigger, was the one undone in 8 of 8 runs.
  - **Scenario.** In the user's Designer (a Windows self-test run, or an agent following GUIDE.md), the user makes a
    step in that window: the Undo takes the user's step, not the checked one.
  - **Fix.** The user's choice: close the window where the undo is sent (wait for the landing in the same callback,
    the user's input held, as `designer_rollback.py` does, or send it through `roll_back` itself), or say the fact in
    GUIDE.md and the self-test's docs.
  - **Resolution: done** by PLAN.md's step 4, the user's choice (2026-11-25): agents undo only with the new tool
    `undo_edits`, and the self-test's Edit > Undo stays as the user's exception, its window documented.
    - **Test:** `test_no_part_of_the_guide_describes_triggering_undo_another_way` (`tests/unit/test_guide.py`)
      failed on GUIDE.md's "Edit > Undo" recipe, and passes without it;
      `test_every_agent_is_told_to_undo_with_undo_edits_in_four_places` pins the rule in the guide's core, the
      server's instructions, `undo_edits`' description and the code tools' descriptions.
    - **Cause:** GUIDE.md's scripting part told agents to schedule Edit > Undo's `trigger()` and return, so the
      Undo landed on whatever step was on top a few tens of ms later.
    - **Fix:** the recipe is removed; "Undo from a script" points to `undo_edits`, which undoes each step only while
      it is on top and waits in the same job until it lands, the user's input held (`designer_rollback.undo_steps`).
      The self-test's `UNDO_REDO` stays, in the self-test's own Designer: `common.py`'s comment and README's
      self-test paragraph give its landing window.
    - **Also covered:** apply_edits' KEPT line, which pointed to Ctrl+Z, now points to `undo_edits`; the live-check
      skill's probe exception; the comments that cited the old rule.
  - Questioned by TST-882 (2026-11-25).

- [x] **SRV-266 · With 25 steps listed, `undo_edits` keeps the names of calls that left no step, and refuses with a wrong reason** · `mcp_server/designer_rollback.py:228-232` (`undo_session`) · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `done['gone'] = [] if full else [...]` and `if full and len(asked) < min(count, len(edits))`. Once
    the dropdown lists `LISTED` steps, no name is ever dropped. A name with no step counts as maybe older than the
    list: a failed call rolled back, a code call that changed nothing, a step the user undid. The approved text
    says a name no longer in the list "is dropped, not counted", and the tool's description says the same.
  - **Scenario.** In a Designer with 25 steps or more, the session makes E1, a failed `apply_edits` E2 (rolled back),
    then E3. `undo_edits(count=3)` gets "Nothing undone: ... only 2 of the 3 calls asked for are among them. An older
    step can't be checked", though E1 and E3 are both listed. E2 stays remembered, so every later count above the
    reachable steps is refused the same way.
  - **Fix.** Tell gone from older by order: a name not listed that is newer than the oldest of the session's listed
    names is gone. That needs the session's names in one ordered list. Unit tests: a full list with every call asked
    for listed, undone; a full list with `count` above the known edits, undone with the fewer said; the scenario
    above. Today, two mutations (`elif full:` as beyond; `len(asked) < count`) pass every unit test.
  - **Resolution: done**.
    - **Test:** in `test_rollback.py`, four tests of a full dropdown: the entry's scenario (it failed, `'beyond'`), all
      the calls asked for listed, a count above the session's edits, and a call older than those listed being kept.
      In `test_undo_edits.py`, the server's side of the scenario (it failed with the BEYOND refusal). The two
      mutations each fail them: `if full:` 8 tests, `len(asked) < count` 6.
    - **Cause:** once the dropdown listed 25 steps, no name was ever dropped, and a name with no step counted as
      maybe older than the list.
    - **Fix:**
      - `undo_session` takes the session's steps as one ordered list of `(name, edit)`, oldest first, and the server
        sends `STEPS`.
      - The dropdown lists the newest steps with none left out. So a name not listed is gone and dropped when it is
        newer than the session's oldest listed step, or when fewer than 25 are listed.
      - `beyond` is refused only when fewer than `count` edits are listed, the list is full, and some edit is older
        than the session's oldest listed step.
    - **Also covered:** the description's "a step undone or rolled back already doesn't [count]" holds with a full
      list too.
  - Questioned by SRV-269 (2026-11-25).

- [x] **SRV-275 · An abort inside an undo group the code opens itself can still leave the call's step open** · `mcp_server/server_tools/core.py:400-404` (`_with_undo`'s template), `mcp_server/server_tools/scripting.py` (the code tools' descriptions) · confirmed · follows SRV-273, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** The template opens the call's transaction, runs the code, and commits once. The code may open its own
    group, for example `with SDHistoryUtils.UndoGroup('x'): ...; graph.compute()`. If it times out in the compute,
    the countdown runs into that group's traced exit path, the window round 13 measured. The inner commit is then
    skipped. Designer counts nested transactions: in round 13's probe, an inner group's open and commit inside the
    open one were balanced, and one commit closed it. So the template's one commit leaves the call's transaction
    open, which is SRV-273's state.
  - **Scenario.** An agent's `execute_designer_code` opens its own `UndoGroup`, as some of Designer's own plugins do,
    and times out inside it. Until Designer restarts, no later step is listed.
  - **Fix.** Generation 2, KISS: the code tools' descriptions, and GUIDE.md's scripting part, say not to open an undo
    group of one's own, since the call is already one step.
  - **Resolution: done**.
    - **Test:** `test_the_code_tools_and_the_scripting_part_say_not_to_open_an_undo_group`
      (`tests/unit/test_guide.py`) failed first.
    - **Fix:** generation 2. Both code tools' descriptions say "Don't open an undo group of your own: the call is one
      already, and a timeout inside yours can leave its step open."; GUIDE.md's "Undo from a script" says the same.
      The descriptions stay within `CLAUDE_CODE_LIMIT`.

## Low

- [x] **SRV-254 · The undo slot's `invoke` result is ignored** · `mcp_server/designer_rollback.py:105` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `found.slot.invoke(found.manager)` returns a bool (the PySide6 stub), and False means nothing was sent;
    the fake's `invoke` always returns True.
  - **Scenario.** The call isn't sent: the wait runs the whole limit, returns 'not landed', and the agent reads that
    an undo was sent and not to undo again, while the changes are still there.
  - **Fix.** Return 'failed' with a reason when `invoke` returns False, with a unit test.
  - **Resolution: done**.
    - **Test:** `test_an_undo_slot_not_called_is_said_failed_and_nothing_is_waited_for`, which got 'not landed' before.
    - **Cause:** `invoke()`'s False was ignored.
    - **Fix:** False gives "failed: Designer's undo() slot wasn't called", with no wait; the fake returns the slot's
      result.
    - **Also covered:** the only `invoke` call.
  - Questioned by SRV-263 (2026-11-24).
  - Questioned by TST-864 (2026-11-24).


- [x] **SRV-255 · `_failure` takes the first `ROLLBACK=` line, and misses one glued to a script's last output** · `mcp_server/server_tools/core.py:363-365` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `re.search(r'^ROLLBACK=(.*)$', output, re.M)` finds the first line starting with it, and only at a
    line's start.
  - **Scenario.** A code tool's script prints without a final newline (`print(..., end='')`) and raises: the output
    holds `xROLLBACK=undone`, the state is missed, the error reads as if no rollback ran although it did, and the line
    stays in the output. (A script printing `ROLLBACK=undone` itself is contrived.)
  - **Fix.** Print the rollback's line after a newline, and read the last match.
  - **Resolution: done**.
    - **Test:** `test_the_rollbacks_line_starts_a_line_of_its_own_after_output_left_unfinished` and
      `test_the_rollbacks_line_is_the_last_one_printed_after_a_newline` (two rows), failing before.
    - **Cause:** the line could be glued to unfinished output, and the first match was taken.
    - **Fix:** the template prints it after a newline; `_failure` takes the last `\nROLLBACK=` match and removes it.
    - **Also covered:** the `KEPT=` lines come from the helpers' own prints, each on its own line.
  - Questioned by TST-851 (2026-11-24).

- [x] **SRV-256 · apply_edits' docstring promises a sentence the error doesn't always have** · `mcp_server/server_tools/edits.py:140-141` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** "Designer's Undo then takes back what the earlier ops did, and the error says nothing changed; if it
    can't, the error says what stays applied, with the nodes added." When the first op fails, the error has neither
    sentence (`batch.py` prints no `KEPT=` at `i == 0`); 'not landed' says to look instead.
  - **Scenario.** An agent waits for "nothing changed" or a list of what stays, and gets neither.
  - **Fix.** Say what each case's error has, including that an error with neither sentence means no op before the
    failing one was applied.
  - **Resolution: done**.
    - **Test:** none can fail on a docstring: settled by reading.
    - **Cause:** the docstring left out the cases with neither sentence.
    - **Fix:** it names each case: undone and says nothing changed; not made, says what stays; sent but not seen
      landing, says to look; an error with none of these means nothing before the failing op was applied.
    - **Also covered:** the tool description's limit holds (`test_server`).


- [x] **TST-843 · README says a failed edit leaves nothing changed, without the conditions** · `README.md:99-102` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** "A call that fails after it changed something takes its own step back at once, so a failed edit leaves
    nothing changed." The code does it only when its tagged step is on top; a file the call wrote stays, and the
    package shows as modified (measured).
  - **Scenario.** A user trusts a failed call to have left their work untouched when another step was on top.
  - **Fix.** Narrow it: the error says when it was taken back; a file it wrote stays; otherwise the error says what
    stays.
  - **Resolution: done**.
    - **Test:** none: a doc, settled by reading.
    - **Cause:** the sentence dropped the rollback's conditions.
    - **Fix:** README says a failed call takes its own step back if that step is still the newest, that its error
      says so, that a file it wrote stays, and otherwise that its error says what stays changed.
    - **Also covered:** GUIDE.md's Undo rule states the condition already.
  - Questioned by TST-848 (2026-11-24).

- [x] **TST-844 · `set_link_display` is said to clear the undo history, and comments still say Undo acts per document** · `README.md:102`, `mcp_server/server_tools/layout.py:93`, `tests/test_all_tools/common.py:282-283` · measured · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** README says set_link_display "reloads the package, which clears its undo history", layout.py "the
    package's undo history is reset". Measured (port 9961): with tagged steps of two packages in the history,
    `set_link_display` on one cleared nothing and added four untagged steps on top ("Open Package(s)", "Unknown",
    "Unreference package", "Unset User Package"); a rollback on the reloaded package still worked. Comments keep the
    per-document model: `common.py:282-283`, `undo/preparations.py:1`, `__main__.py:16`, `undo/checks.py:1`,
    `tests/unit/test_selftest_pool.py:1120`, `test_selftest_undo.py:739,786`.
  - **Scenario.** An agent or user believes a reload wiped the history, or that Undo targets the graph in focus.
  - **Fix.** Say what the reload does to the history (its four steps on top, nothing cleared), with a "designer
    facts" check, and reword the comments to the one history.
  - **Resolution: done**.
    - **Test:** the "designer facts" check `link_display.check_a_reload_clears_no_step_of_the_undo_history`
      (`link_display/designer_scripts/undo_steps.py`): a tagged step stays listed after `set_link_display`, and the
      top is new; it passes, which shows the docs were wrong.
    - **Cause:** the docs predate the one-history measurement.
    - **Fix:** README and `set_link_display`'s docstring say the reload adds steps of its own and clears none; the
      comments in `common.py`, `undo/preparations.py`, `__main__.py`, `undo/checks.py`, `test_selftest_pool.py` and
      `test_selftest_undo.py` say one history.
    - **Also covered:** a grep for "in focus" and "per document" in the repository.
  - Questioned by TST-849 (2026-11-24).
  - Questioned by TST-883 (2026-11-25).

- [x] **TST-845 · Two new live checks don't clean up when they fail** · `tests/test_all_tools/batch/checks.py:159-192, 232-247` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** In the "step after ours" check, a broken guard undoes the blur step, and the `finally`'s one
    `apply_edits` deleting both ids is refused whole by the pre-check ("not found"), leaking the other node; the
    rollback then waits its 60 s limit, as long as `sd_run`'s default timeout, so `TimeoutExpired` can leave both. The
    rolled-back check leaves `y`, the input `rolled_back` and `lv`'s value when the rollback fails.
  - **Scenario.** A regression makes the checks fail and leave nodes behind in the category's graph.
  - **Fix.** Delete only the nodes still there, one call each or after `describe_graph`; an `sd_run` timeout above
    the rollback's limit; a `finally` for the rolled-back check's nodes and input.
  - **Resolution: done**.
    - **Test:** a scratch run with `roll_back` made to return early: the check failed and its `finally` left the
      graph as prepared (2 nodes, no exposed input, lv at its defaults).
    - **Cause:** the clean-up assumed the rollback had worked.
    - **Fix:** the rolled-back check's `finally` deletes the nodes not there before, removes `rolled_back` and puts
      `levelinlow` back; the step-after-ours check deletes only the nodes its `LEFT=` names; both `sd_run` scripts get
      `SCRIPT_S = 130` s, above the rollback's limit.
    - **Also covered:** the facts check unloads its packages in a `finally` already.
  - Questioned by TST-863 (2026-11-24).


- [x] **TST-846 · Implicit `Any` in the new checks, and a second `History` protocol** · `tests/test_all_tools/batch/checks.py:237, 255`, `tests/test_all_tools/batch/designer_scripts/` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `dict(re.findall(...))` is `dict[Any, Any]` and `{k: json.loads(v) ...}` is `dict[str, Any]`
    (`.claude/rules/python.md`, Typing); the two Designer scripts cast to a local `History` Protocol that duplicates
    `designer_rollback.History`.
  - **Scenario.** A rename in `designer_rollback.History` passes mypy and fails only when the live check runs.
  - **Fix.** `dict[str, str]` and `dict[str, list[str | None]]`; type against `designer_rollback`'s own protocol if
    the scripts can import its name, or say why not.
  - **Resolution: done**.
    - **Test:** none can fail on it: mypy doesn't report an implicit `Any`; settled by reading.
    - **Cause:** values from `re.findall` and `json.loads`, and a local protocol.
    - **Fix:** `dict[str, str]`, `list[str | None] | None`, `dict[str, object]`; the three Designer scripts import
      `designer_rollback` itself (a six-line block each), so mypy checks them against its real types.
    - **Also covered:** the new link_display script.


- [x] **TST-847 · The batch category's recorded time predates its new checks** · `tests/test_all_tools/categories.py:71` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `batch.run,  # 1 s: apply_edits` in the list kept by measured times; the category now runs two
    `sd_run` subprocesses, a create and save, and several failing calls.
  - **Scenario.** The pool starts batch later than its time warrants.
  - **Fix.** Measure it as the list's other figures were, and update its figure and place.
  - **Resolution: done**.
    - **Test:** two scratch runs of the whole batch category with their server's start: 9.8 s and 14.4 s.
    - **Cause:** the figure predated the new checks.
    - **Fix:** `categories.py` records 12 s with the runs' figures, the category moved before `bridge` (11 s);
      `test_selftest_categories` and `test_selftest_workers` pass.
    - **Also covered:** link_display gains two reloads (about 2-3 s, unmeasured), left for the final check's figures.

- [x] **SRV-257 · The rollback module's own top-level code runs unguarded in the template's `except` block** · `mcp_server/server_tools/core.py:357` · confirmed · follows SRV-253, generation 2 · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `roll_back` catches its own errors, but `_builtins.exec(_builtins.compile(ROLLBACK, ...), _rollback)`
    runs the module's imports (PySide6, typing) and class statements with no guard.
  - **Scenario.** A Designer or PySide6 update moves a name the module imports: the `ImportError` replaces the call's
    error (an `_edit` tool shows only its last line), and nothing is rolled back.
  - **Fix.** Guard the `except` body (`try: ... except BaseException: pass`) before the bare `raise`, with a unit test
    whose stand-in `ROLLBACK` raises at import and expects the call's own error.
  - **Resolution: done**.
    - **Test:** `test_a_rollback_whose_own_module_fails_to_load_leaves_the_calls_own_error` (a stand-in `ROLLBACK`
      raising ImportError at import): it failed before the fix, and fails again with the guard removed.
    - **Cause:** the module's imports and classes ran in the template's `except` block unguarded; `/simplify` had
      dropped the guard as redundant.
    - **Fix:** the template wraps the rollback's load and call in `try ... except BaseException`, its error made the
      state ("failed: <type>: <text>"), then re-raises the call's own error; `_with_undo`'s docstring says why the
      guard stays.
    - **Also covered:** SRV-253's test still fails with the `_builtins` binding removed.

- [x] **SRV-258 · A rollback state of several lines is cut in the error, its rest left in the output** · `mcp_server/designer_rollback.py` (`'failed: %s: %s'`, `'not landed: %s: %s'`), `mcp_server/server_tools/core.py:373-376` · confirmed · follows SRV-252, generation 2 · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `_failure` reads `\nROLLBACK=(.*)` to the first newline, and an error's text can span lines (PySide6's
    "called with wrong argument types:" lists the signatures below it).
  - **Scenario.** A PySide6 change makes `invoke` fail so: the error says "couldn't run (TypeError: ... wrong argument
    types:)", the useful part is left in the tool's output.
  - **Fix.** Make the state one line where it is made (`' '.join(str(e).split())`).
  - **Resolution: done**.
    - **Test:** `test_a_state_of_several_lines_is_printed_on_one`, failing before the fix; with the collapse removed,
      it and SRV-257's two-line ImportError test fail.
    - **Cause:** `_failure` reads the state to the end of its line.
    - **Fix:** the template prints `"\n" + ROLLBACK_LINE + " ".join(_state.split())`: one place for every state, the
      guard's included.
    - **Also covered:** `designer_rollback.py` unchanged.

- [x] **TST-848 · README still says more than the code about a failed call** · `README.md:94, 100-102` · confirmed · follows TST-843, generation 2 · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The Tools table's Editing row says "a batch failing partway is undone whole", with no condition; and
    "Otherwise its error says what stays changed" holds only for apply_edits and set_function, the tools that print
    `KEPT=` lines (and 'not landed' says to look instead).
  - **Scenario.** A script raised after its changes with another step on top: the error is the bare traceback, while
    the README promises what stays.
  - **Fix.** The condition in the Editing row (while its step is the newest), and the sentence narrowed to the two
    tools that say what stays.
  - **Resolution: done**.
    - **Test:** none: a doc, settled by reading.
    - **Cause:** the two sentences kept an unconditional claim.
    - **Fix:** the Editing row says a batch failing partway "is undone whole while its step is the newest"; the Undo
      paragraph says `apply_edits` and `set_function` say what stays changed, the two tools that print `KEPT=` lines.
    - **Also covered:** GUIDE.md's Undo rule had the condition already.
  - Questioned by SRV-262 (2026-11-24).

- [x] **TST-849 · The "reload clears no step" check sees only another package's step** · `tests/test_all_tools/link_display/checks.py:~190-200`, `ROADMAP.md:153` · confirmed · follows TST-844, generation 2 · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The check asserts the step of a second package's `create_graph` stays, while README and `layout.py`
    say of the whole history that the reload clears none, the reloaded package's own steps included (true today: the
    round 1 probe measured both). ROADMAP item 8 still says the reload "resets the package's undo history".
  - **Scenario.** A Designer update clears only the reloaded package's steps: the check still passes.
  - **Fix.** Check that every tagged step listed before is still listed after (or narrow the check's name and
    docstring); fix ROADMAP item 8's clause.
  - **Resolution: done**.
    - **Test:** `link_display.check_a_reload_clears_no_step_of_the_undo_history` now makes a step in the reloaded
      package itself and checks that the two newest steps listed before (that step, and another package's) are still
      listed after, and the top changed (the dropdown lists the newest 25); it passes, a Designer fact.
    - **Cause:** the check saw only another package's step.
    - **Fix:** the check and its docstring; ROADMAP item 8 says the reload adds steps of its own and clears none.
    - **Also covered:** README and `layout.py` already said so.

- [x] **TST-851 · The "last one" test row doesn't pin the last match** · `tests/unit/test_rollback.py:307-311` · confirmed · follows SRV-255, generation 2 · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The row's first `ROLLBACK=` line has no newline before it, so `\nROLLBACK=` finds one match only.
  - **Scenario.** `_failure` taking the first match again (`lines[0]`) passes both rows.
  - **Fix.** A newline before the row's first line, and the expected output adjusted.
  - **Resolution: done**.
    - **Test:** the row puts a newline before its first `ROLLBACK=` line; with `_failure` taking `lines[0]`, it fails.
    - **Cause:** the row's first line didn't match the pattern.
    - **Fix:** the row and its expected output.
    - **Also covered:** the other row of the test unchanged.

- [x] **SRV-259 · Step 2's docstrings skip two tools whose failure is now rolled back** · `mcp_server/server_tools/edits.py:19` (`create_graph`), `mcp_server/server_tools/measure.py:348` (`sweep_param`) · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** Step 2's approved text: "Docs: the docstrings of the tools whose failure now leaves nothing changed".
    Only the two code tools' docstrings changed. `create_graph`'s still reads "Create a new package with one empty
    compositing graph. One undo step.", and `sweep_param`'s "the sweep is an undo step and marks the package as
    modified", though the step's live checks show both rolled back when they fail after a change.
  - **Scenario.** An agent whose `create_graph` fails on its save isn't told by the tool that no package is left, and
    may look for it or unload it.
  - **Fix.** One sentence in each of the two docstrings. The other wrapped tools have no natural failure after a
    change (the developer's report), and GUIDE.md's Undo rule states the mechanism once: they stay as they are.
  - **Resolution: done**.
    - **Test:** none can fail on a docstring; settled by reading. Both sentences rest on step 2's live checks
      `batch.check_a_graph_whose_save_fails_leaves_no_package` and `check_a_sweep_failing_on_its_output_is_rolled_back`.
    - **Cause:** step 2 reworded only the two code tools' docstrings.
    - **Fix:** `create_graph`'s docstring: "If the save fails, Designer's Undo takes that step back while it is the
      newest, the package with it, and the error says so"; `sweep_param`'s: "If the sweep fails after it set a value,
      Designer's Undo takes that step back while it is the newest, and the error says so".
    - **Also covered:** the other wrapped tools have no natural failure after a change, and stay as they are;
      `test_server`'s description limits pass.
  - Questioned by SRV-261 (2026-11-24).
  - Questioned by TST-871 (2026-11-25).

- [x] **SRV-260 · "Nothing changed in Designer" claims more than an undo step takes back** · `mcp_server/server_tools/core.py:321-324` (`UNDONE`) · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `UNDONE` reads "Nothing changed in Designer: its Undo took back what the call had done before it
    failed (a file the call wrote stays, and its package may still show as modified)." The rollback undoes one step
    of the history. The code tools reach it too, and a script can change what the history doesn't hold: a widget
    changed through Qt, a handler connected to a signal, a file written (the one exception the text names).
  - **Scenario.** A script hides a dock through Qt, edits a graph, then raises. The edit is undone, the error says
    nothing changed in Designer, and the dock stays hidden.
  - **Fix.** Say what Designer's Undo took back, the call's undo step, and that what the history doesn't hold stays,
    such as a file the call wrote; keep "its package may still show as modified". Name only what is measured. The
    tests and docs quoting the sentence follow.
  - **Resolution: done**.
    - **Test:** the live checks match a phrase of the new sentence, `ROLLED_BACK` ("took back the call's own undo
      step", `project_constants.py`). Against the old `UNDONE`, 12 of 30 failed with it missing: every rollback check
      of `batch` and `graph_edit_output_fields`' one-name-twice check. With the fix, `batch` and
      `graph_edit_output_fields` passed 45 of 45 in a scratch run, and again after `/simplify`.
    - **Cause:** `UNDONE` said "Nothing changed in Designer", but the rollback undoes one step of the history.
    - **Fix:** `UNDONE` (`server_tools/core.py`), built from `ROLLED_BACK`: "Designer's Undo took back the call's own
      undo step, with its edits. What the call did that the step doesn't hold stays, such as a file it wrote, and its
      package may still show as modified." `_failure`'s docstring follows.
    - **Also covered:** "nothing changed" and "changes nothing" grepped in `mcp_server`, `plugin`, `client`, `tests`,
      README.md and GUIDE.md: fixed in `apply_edits`' docstring, `designer_rollback.py`'s first line and the checks of
      `batch` and `graph_edit_output_fields`; the pre-check refusal, the safeguards refusals, the frames3d facts and
      DECISIONS.md make other claims. ROADMAP.md item 37's Approach follows (the lead).
  - Questioned by TST-866 (2026-11-24).

- [x] **TST-852 · Comments cite PLAN.md, which is deleted before the merge** · `tests/unit/test_rollback.py:77`, `tests/unit/test_rollback.py:105`, `tests/unit/test_plugin.py:781` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** "(PLAN.md)", "(the user, 2026-11-24, PLAN.md step 2)" and "(PLAN.md, step 2)". PLAN.md dies with the
    branch (AGENTS.md, Working on this project; the `delegate` skill, The merge).
  - **Scenario.** After the merge, a reader following the pointer finds no PLAN.md.
  - **Fix.** Drop the PLAN.md pointers and keep the user's date; where the pointer gives the reason, say it in the
    comment. Look for other code, tests or docs outside `.claude/` and AGENTS.md citing PLAN.md for a fact.
  - **Resolution: done**.
    - **Test:** none can fail on a comment; `git grep 'PLAN\.md'` outside `.claude/`, AGENTS.md, REVIEW.md and PLAN.md
      shows nothing left citing PLAN.md for a fact.
    - **Cause:** three comments pointed at PLAN.md, deleted with the branch.
    - **Fix:** `tests/unit/test_rollback.py`'s two comments and `tests/unit/test_plugin.py`'s one keep their reason
      and the user's date, without the pointer.
    - **Also covered:** the other hits (`docs/agent-workflow.md`, `test_agents.py`, `test_guide.py`,
      `test_large_reads.py`, `docs_text.py`) are about PLAN.md in the workflow.

- [x] **TST-853 · The queued-job check's docstring claims the plugin's re-entry guard, never seen catching it** · `tests/test_all_tools/batch/checks.py:443-446` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The docstring says the queued job runs after the call, "(the plugin starts no job inside another)".
    The check was seen failing only with the rollback disabled (the developer's report). The guard, `draining` in the
    plugin's `_drain`, was never removed in a run, which needs a changed plugin in the user's plugin folder, where
    agents' Designers load it from. Whether a queued job would nest without the guard depends on Qt's event order
    (the bridge's 100 ms poll timer against the undo's events), which reading can't settle.
  - **Scenario.** A refactor drops the guard. The check may still pass, while its docstring says it covers it.
  - **Fix.** Narrow the docstring to what the check shows: the job queued during the rollback ran after the call,
    and the call was rolled back. Name `tests/unit/test_plugin.py::test_a_job_never_starts_inside_the_running_one`
    as the guard's test. No run with the guard removed (AGENTS.md, Keep it simple).
  - **Resolution: done**.
    - **Test:** none: only the docstring is narrowed, as the fix says.
    - **Cause:** the docstring claimed the plugin's re-entry guard, which the check was never seen catching.
    - **Fix:** the docstring says the queued job ran after the call, not inside the rollback's wait, and the call was
      rolled back; that whether the job would nest without `draining` isn't seen there; and names
      `test_a_job_never_starts_inside_the_running_one` as the guard's test.
    - **Also covered:** the plugin's `_drain` comment already names the same test.

- [x] **INS-48 · The crash reader names a database for a dump moved out of Crashpad's folders** · `scripts/read_crash_dump.py:394-397` (`_database`), `scripts/read_crash_dump.py:435` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `_database` returns the dump's grandparent folder for any path, and the report prints it as "the
    crash handler's database". Only the docstring qualifies it: "as long as the dump stays where Crashpad wrote it".
  - **Scenario.** A runner copies a dump into its scratchpad and reads it there. The report names the scratchpad's
    parent as the crash handler's database, not the crashed Designer's home.
  - **Fix.** Print the line only when the dump's folder is Crashpad's `completed` or `pending`, with a unit test of a
    dump in another folder.
  - **Resolution: done**.
    - **Test:** `test_a_dump_moved_out_of_crashpads_folders_names_no_database_nor_its_log`, a dump in
      `Sentry-Crashpad/scratch/` with a log where the guess would look: it failed printing the database line, then
      reading that log; it passes. `test_the_crash_handlers_database_is_said` also checks a dump in `pending/`.
    - **Cause:** `_database` took the dump's grandparent for any path, and the database line and `_log_tail` trusted it.
    - **Fix:** `_database` returns None unless the dump's folder is one of `REPORTS` (`pending`, `completed`); the line
      is printed, and the log looked for, only when it gives a path. `dump_folders` takes its names from `REPORTS`.
    - **Also covered:** `_log_tail`, the same guess. Nothing else derives a database from a dump's path.

- [x] **TST-855 · The test that the `__sentry-event` attachment is never read sees only `builtins.open`** · `tests/unit/test_read_crash_dump.py:161-178` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The test records `builtins.open`. `pathlib.Path.open`, `read_bytes` and `read_text` go through
    `io.open`, which that patch leaves as it is (`tests/unit/windows_simulation.py:37-38` patches both for this).
  - **Scenario.** A later change reads the attachment with `Path(...).read_bytes()`. The test, the only guard of the
    rule that the user's Adobe account is never read, still passes.
  - **Fix.** Record through `io.open` too, as `windows_simulation.py` does.
  - **Resolution: done**.
    - **Test:** with the script mutated to read `__sentry-event` through `pathlib.Path(...).read_bytes()`, the test
      as it was passed and the new one fails, listing the event among the files opened; restored, it passes.
    - **Cause:** `Path.open`, `read_bytes` and `read_text` open through `io.open`, which patching `builtins.open`
      leaves alone.
    - **Fix:** one recorder, `mock.Mock(wraps=io.open)`, set on both `io.open` and `builtins.open`; the test asserts
      the paths opened.
    - **Also covered:** the other patches of `builtins.open` in `tests/unit` (`conftest.full_disk`,
      `test_link_display.py`) guard no "never read".

- [x] **SRV-261 · `set_function`'s docstring skips its rollback, though it fails after a change** · `mcp_server/server_tools/functions.py:395-411` · confirmed · follows SRV-259, generation 2 · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** SRV-259's resolution left the other wrapped tools as they were, as having no natural failure after
    a change. `set_function` has one: on an existing function graph, `_set_inputs` can raise after the output node
    has moved (`mcp_server/designer_helpers/functions.py:590-600`, its `KEPT=` line), and the rollback now takes it
    back.
  - **Scenario.** An agent's `set_function` with inputs fails on an existing function graph. Its description says
    nothing of the rollback, unlike `create_graph`'s and `sweep_param`'s.
  - **Fix.** One clause in `set_function`'s docstring, within `test_server`'s description limits. Generation 2: the
    docstring only.
  - **Resolution: done**.
    - **Test:** none can fail on a docstring; settled by reading. `test_server`'s description limits pass.
    - **Cause:** SRV-259's resolution took `set_function` to have no failure after a change.
    - **Fix:** `set_function`'s docstring ends "If a function graph it replaces fails to take its new inputs,
      Designer's Undo takes that step back while it is the newest, and the error says so."

- [x] **TST-856 · The self-test's docs give its Undo's guard as the editor graph alone** · `README.md:271-273`, `tests/test_all_tools/__main__.py:15-16`, `tests/test_all_tools/undo/checks.py:1-3` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** They say an Undo or a Redo is sent only while the self-test graph is in the editor, a check failing
    naming the graph in the editor otherwise. Since 3d, it is also sent only when the dropdown's top step is the
    check's own call's, a check failing naming that step otherwise.
  - **Scenario.** A person deciding whether to run the self-test in their own Designer reads README.md, and doesn't
    learn that it never undoes or redoes a step that isn't its own.
  - **Fix.** The second condition in the three sentences.
  - **Resolution: done**.
    - **Test:** none; docs, settled by reading. The docs tests pass.
    - **Cause:** step 3 added the top-step condition without updating these texts.
    - **Fix:** README.md, `__main__.py`'s and `undo/checks.py`'s docstrings give both conditions, and that the check
      fails naming the graph in the editor or the top step. `put_back`'s docstring: "took back a step of the check's
      label, possibly another call's" (round 5's log).
    - **Also covered:** `git grep` of the old phrases finds no other; `common.py`'s `UNDO_REDO` comment had both.

- [x] **TST-857 · The snippet's `fullmatch` is never tried on a near-miss top step** · `tests/unit/test_selftest_pool.py` (the snippet's not-firing test), `tests/test_all_tools/common.py:350-353` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The snippet's unit tests give the dropdown's top as `'Add Node'`, `None` or the check's own step.
    The near misses (the own step and one more character, a prefix before it) are tried only by a test calling
    `re.fullmatch` itself (`test_selftest_pool.py:1229`). The snippet's `fullmatch` swapped for `match` or `search`
    passes every unit test.
  - **Scenario.** A refactor writes `re.match`. A top named the label, the tag and more fires the Undo, and no unit
    test fails.
  - **Fix.** The own step plus `'0'`, and `'x'` plus the own step, as tops in the snippet's not-firing test.
  - **Resolution: done**.
    - **Test:** the two near misses, for Undo and Redo, in the snippet's not-firing test: with `fullmatch` swapped for
      `match`, 2 fail; for `search`, 4; restored, all pass.
    - **Cause:** only a test calling `re.fullmatch` itself tried near misses.
    - **Fix:** the two tops in the snippet's test; the snippet was right.
    - **Also covered:** the snippet holds the only `fullmatch` on a step name; `roll_back` compares names with `!=`,
      under its own tests.

- [x] **TST-858 · `NOT_OURS top=None` doesn't tell a missing history from an empty dropdown** · `tests/test_all_tools/common.py:323-326`, `tests/test_all_tools/common.py:350-352` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `_top()` returns None both when `history()` finds no dropdowns and when the dropdown lists no step,
    and the check fails with `NOT_OURS top=None` for both. The rollback keeps the two apart.
  - **Scenario.** A Designer update renames the toolbar's `undo-button`. Every Undo and Redo check fails with
    `NOT_OURS top=None`, pointing at the dropdown's contents instead of the lookup.
  - **Fix.** A text of its own when no history is found, which the pattern can't match, pinned in
    `test_an_action_without_designers_history_doesnt_fire`.
  - **Resolution: done**.
    - **Test:** `test_an_action_without_designers_history_doesnt_fire` pins `NOT_OURS top="no Undo and Redo dropdowns
      of Designer's history found"`; it failed with `top=None`.
    - **Cause:** `_top()` returned None both for no history and for an empty dropdown.
    - **Fix:** `_top()` in `UNDO_REDO` returns that text, the rollback's own wording, which the pattern can't match.
    - **Also covered:** the self-test's other readers of `history()` (`history_facts.py`, `undo_steps.py`) already
      raise their own text when it is None.

- [x] **INS-49 · The crash reader's `read` stops at the first memory range holding an address** · `scripts/read_crash_dump.py:194-200` (`read`, `read64`) · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `read` returns the bytes of the first range with `start <= address < start + len(memory)`, fewer
    where it ends. On main, `read64` required all 8 bytes in a range and moved on to the next one otherwise.
  - **Scenario.** A small range of the memory list (listed before the thread stacks) holds a frame record's address
    but ends within 8 bytes after it, while the thread's stack holds the whole record. The frame walk stops there,
    and the stack's text can be cut short the same way.
  - **Fix.** `read` prefers a range holding all `size` bytes, as main's `read64` did, with a unit test of two
    overlapping ranges.
  - **Resolution: done**.
    - **Test:** `test_a_range_of_the_memory_list_cut_short_gives_way_to_one_holding_the_bytes_whole`: two ranges of
      the memory list before the stack, cut short, one of them over a frame record; frame 3 was missing, and is said.
    - **Cause:** `read` returned the first range holding the address.
    - **Fix:** `_Dump.read` returns the longest slice any range holding the address gives.
    - **Also covered:** `read` is the only reader of the memory; `read64` and `_stack_top` go through it.

- [x] **SRV-262 · `execute_designer_code`'s docstring says Ctrl+Z reverts its step, unconditionally** · `mcp_server/server_tools/scripting.py:38` · confirmed · follows TST-848, generation 3 · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** "All changes form one undo step (Ctrl+Z in Designer reverts them)." Designer keeps one history for
    every package, so Ctrl+Z reverts the call's step only while it is the newest, as README.md and GUIDE.md now say.
  - **Scenario.** An agent relays the docstring's claim; the user has made a step since, and their Ctrl+Z takes back
    their own step.
  - **Fix.** Generation 3, narrowing only: delete the parenthetical.
  - **Resolution: done**.
    - **Test:** none; a docstring, narrowed (generation 3).
    - **Fix:** the parenthetical deleted.
    - **Also covered:** `git grep Ctrl+Z` finds only statements with the condition.

- [x] **SRV-263 · `_undo`'s and `roll_back`'s docstrings leave out the slot not called** · `mcp_server/designer_rollback.py:91-96` (`_undo`), `mcp_server/designer_rollback.py:134` (`roll_back`) · confirmed · follows SRV-254, generation 2 · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `_undo` returns "failed: Designer's undo() slot wasn't called" when `invoke` returns False. Its
    docstring lists 'undone' and the 'not landed' cases, then "one before it is raised"; `roll_back`'s gives
    'failed' as "Designer's history wasn't found, or by its own error".
  - **Scenario.** A maintainer reading `_undo`'s results misses a returned 'failed', and takes an error before the
    send to be always raised.
  - **Fix.** Name the case in both docstrings. Generation 2.
  - **Resolution: done**.
    - **Test:** none; docstrings.
    - **Fix:** `_undo`'s docstring names the slot not called as "failed: ...", nothing sent; `roll_back`'s 'failed'
      item names it too.

- [x] **SRV-264 · `_failure`'s `kept` is an implicit `list[Any]`** · `mcp_server/server_tools/core.py:390` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `kept = re.findall(...)`: typeshed gives `list[Any]`, so mypy checks nothing done with its items
    (`.claude/rules/python.md`, Typing: an implicit `Any` is looked for by hand).
  - **Scenario.** A later change treats an item as something other than a string, and mypy passes it.
  - **Fix.** `kept: list[str]`, as TST-846 did in `checks.py`.
  - **Resolution: done**.
    - **Test:** none can fail; lint and types pass.
    - **Fix:** `kept: list[str] = re.findall(...)`.
  - Questioned by SRV-274 (2026-11-25).

- [x] **TST-859 · ROADMAP item 95 says both facts were found by either tool** · `ROADMAP.md:35` (item 95) · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** "Both were found without any permission prompt, by `log show ...`, or by `osascript -l JavaScript`
    with `CGWindowListCopyWindowInfo`". The runner's diagnosis listed the windows once with the window list (owner,
    pid, layer); the 80 s in front and the end 6 ms after the window closed come from `log show`'s events.
  - **Scenario.** Whoever implements item 95 expects the window list to time the crashed process's end.
  - **Fix.** Say which tool gave what: `log show` the times, the window list the window while it is open.
  - **Resolution: done**.
    - **Test:** none; ROADMAP text, the docs tests passing.
    - **Fix:** item 95 says `log show` gave the times, and the window list listed the window while it was open.

- [x] **TST-860 · The stack-text test passes whether the text is read from sp or from the stack's start** · `tests/unit/test_read_crash_dump.py:195` (`test_the_top_of_the_crashing_threads_stack_is_said_as_text`) · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** Its dump has `sp` equal to the stack range's start, and the test checks only that `%#x % STACK`
    appears. Code reading the thread's stack range from its start passes, while the docstrings say "from sp".
  - **Scenario.** A refactor reads the stack range from its start; in a real dump, where the range starts below sp,
    the text shown begins before sp, and every test passes.
  - **Fix.** `sp` above the range's start, the string after it, and `sp+0x000` expected to begin there.
  - **Resolution: done**.
    - **Test:** sp at `STACK + 0x10`, a string below it and `outputsize` at it; with `_stack_top` reading from the
      range's start, the test fails; restored, it passes. The old test passed under that mutation.
    - **Cause:** the test's sp was the range's start.
    - **Fix:** the test only; the code read from sp.

- [x] **TST-861 · The new self-test unit tests type Undo and Redo as `str`** · `tests/unit/test_selftest_pool.py:1167`, `tests/unit/test_selftest_pool.py:1183`, `tests/unit/test_selftest_undo.py:876-911` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `which: str`, `list[tuple[str, str]]` and `Callable[[str, str], str]` where `Literal['Undo',
    'Redo']` is known (`.claude/rules/python.md`: a container whose items' types say less than is known).
  - **Scenario.** A test passing `'undo'` or another word type-checks.
  - **Fix.** `Literal['Undo', 'Redo']`, or `common.Which`, as `test_selftest_undo.py:311` already spells it.
  - **Resolution: done**.
    - **Test:** none can fail; lint and types pass.
    - **Fix:** `Which = Literal['Undo', 'Redo']` once, in `tests/unit/selftest_fakes.py`, used by both files;
      `test_which_is_undo_or_redo` pins it against `common.undo_redo`'s.
  - Questioned by TST-870 (2026-11-25).

- [x] **TST-862 · `history_facts.py` triggers Designer's Undo without reading that the top step is its own** · `tests/test_all_tools/batch/designer_scripts/history_facts.py:70` · confirmed · follows TST-842, generation 2 · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** It invokes Designer's `undo()` slot on the history's top step without first reading that it is the
    script's own. Round 2 named this not worth a fix; since then GUIDE.md's core rule reads "In the user's Designer,
    never trigger Undo unless the top step is your own", and step 3d guarded the self-test's other Undo on the user's
    word, for a case as unlikely. On Windows the self-test runs in the user's Designer.
  - **Scenario.** A Designer update changes the history (what this facts check exists to catch), say `undo()` acting
    on the document in focus; the first Windows run after it undoes the user's newest step before the facts fail.
  - **Fix.** Invoke only when the Undo dropdown's top is the script's last step; otherwise print it and skip.
  - **Resolution: done**.
    - **Test:** `history_facts.py` mutated to compare the top with its first step: it refuses to undo, and
      `check_one_history_for_every_package_each_step_shown_as_it_commits` fails; restored, it passes.
    - **Cause:** the script invoked `undo()` without reading the top step.
    - **Fix:** the script reads `designer_rollback._top(history.undo)` and raises, undoing nothing, unless the top is
      its last step.
    - **Also covered:** `step_after_ours.py` undoes through `roll_back`, which reads the top; `UNDO_REDO` since 3d.

- [x] **TST-863 · The queued job's `sd_run` gives up before the job it waits behind can end** · `tests/test_all_tools/batch/checks.py:453` · confirmed · follows TST-845, generation 2 · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `sd_run('-c', NESTED)` keeps the default 60 s timeout, while the job ahead can take `LIMIT_S`
    (30 s) and the rollback's 60 s limit. TST-845's fix gave `sd_run` a timeout above the rollback's limit
    elsewhere (`SCRIPT_S`).
  - **Scenario.** A rollback whose undo never lands: `TimeoutExpired` leaves the check, the category reports that
    `batch.run` didn't reach its end instead of this check's failure, and its last check never runs.
  - **Fix.** `timeout=SCRIPT_S`.
  - **Resolution: done**.
    - **Test:** none run (forcing a 60 s rollback wait); settled by reading.
    - **Fix:** `sd_run('-c', NESTED, timeout=SCRIPT_S)`.
    - **Also covered:** the other `sd_run` calls of `batch/checks.py` pass `SCRIPT_S`; `during_rollback.py`'s
      `--status` and `--cancel` aren't queued.

- [x] **TST-864 · The fact that an undo wakes the rollback's filter can't tell its causes apart** · `tests/test_all_tools/batch/designer_scripts/history_facts.py:70-74`, `tests/test_all_tools/batch/checks.py:324-329` · confirmed · follows TST-842 and SRV-254, generation 2 · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `invoke`'s result is ignored: a slot not called waits the 60 s and reads as Designer's events
    stopping. An undo landing within `invoke` never enters `loop.exec`, and the check passes, while
    `designer_rollback.py`'s docstring cites it for an undo landing as Designer processes the events after it.
  - **Scenario.** A Designer change of either kind is reported as the other, or the fact the docstring rests on is
    never established.
  - **Fix.** Print whether the slot was called and how many times the loop woke; require the slot called and at
    least one wake.
  - **Resolution: done**.
    - **Test:** the facts check requires `called` True, at least one wake, the limit still running and the Redo top
      the script's last step; it failed before the script's change (neither key printed), and passes. Measured on
      port 9975: `called` true, 1 wake, the limit running.
    - **Cause:** `invoke`'s result was ignored, and an undo landing within `invoke` would never enter the loop.
    - **Fix:** the script prints `called` and counts the loop's wakes; the check's docstring says so.

- [x] **TST-865 · `history_facts.py` builds the tag itself, not from the tag's constants** · `tests/test_all_tools/batch/designer_scripts/history_facts.py:54` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `'self-test: a step in %s #%s' % (..., secrets.token_hex(4))`. The user's instruction: the tag's
    form is defined once, as constants, "so if we want to make it invisible we just change that constant"; after such
    a change, this fact still checks ` #` and 8 hex digits.
  - **Scenario.** The tag made invisible, and a Designer dropping zero-width characters: every rollback check reads
    "not ours", and the facts check, which should name the cause, passes.
  - **Fix.** Build the names from `TAG_PREFIX`, `TAG_ALPHABET` and `TAG_LENGTH`.
  - **Resolution: done**.
    - **Test:** none can fail on the form today; `batch` passes with names built from the constants.
    - **Cause:** the script wrote the tag itself, as `server_tools/core.py`, which held the constants, can't be
      imported in Designer.
    - **Fix:** `TAG_PREFIX`, `TAG_ALPHABET`, `TAG_LENGTH` and `new_tag()` moved to `project_constants.py` (standard
      library only); `core.py` imports them and keeps `TAG_FORM`; `common.py`, `history_facts.py` and the unit tests
      use them. `history_facts.py` defines no function now and ends with `del history`.
    - **Also covered:** `step_after_ours.py` built its tag by hand too, and now uses `new_tag()`.
  - Questioned by TST-868 (2026-11-25).
  - Note (2026-11-25): `history_facts.py`'s comment says "the toolbar's wrappers go now" at `del history`, while
    `menu`, `loop`, `woken` and `limit` still hold theirs until the job's scope goes, microseconds later (round 7).

- [x] **TST-866 · ROADMAP item 37's title and Approach claim more than the rollback does** · `ROADMAP.md:57` (item 37) · confirmed · follows SRV-260, generation 2 · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** The title reads "A failed call leaves nothing changed", the claim SRV-260 removed from `UNDONE`.
    The Approach says the rollback "waits for the Undo dropdown's events" (it filters both dropdowns and stops when
    the Redo dropdown's top is the label) and that the error says "what stays and why" (the code tools' errors don't).
  - **Scenario.** A reader of the roadmap takes a failed call to leave nothing changed in Designer.
  - **Fix.** Narrow the title and the two phrases to what the code does.
  - **Resolution: done**.
    - **Test:** none; ROADMAP text, the docs tests passing.
    - **Fix:** the title "A failed call's own undo step rolled back"; the rollback "waits until the Redo dropdown's
      top is that step, woken by both dropdowns' events"; its error "says what became of the step"
      (`server_tools/core.py`, `_failure`). The item stays checked, its Done note unchanged.

- [x] **AGT-133 · `designer-code.md` doesn't say how a change of `designer_rollback.py` reaches Designer** · `.claude/rules/designer-code.md:16-17` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** "How changes reach Designer" lists `server.py`, `server_tools/`, `designer_helpers/` and
    `designer_preferences.py`. `mcp_server/designer_rollback.py`, new in this branch, is read by the server once,
    at import, and embedded in every call.
  - **Scenario.** An agent edits `designer_rollback.py` and tests it against a server started before, seeing the old
    rollback.
  - **Fix.** Name it in that list.
  - **Resolution: done**.
    - **Test:** none; a rule's text, the docs tests passing.
    - **Fix:** `designer-code.md` names `designer_rollback.py`: the server reads the helpers and the rollback once and
      sends them with every call.
  - Questioned by AGT-134 (2026-11-25).

- [x] **TST-867 · README's How it works doesn't name the rollback's file** · `README.md:24-60` (How it works) · confirmed · found 2026-11-25 by the developer (Opus)
  - **Defect.** The section's table names each part, where it runs and what it does (the plugin, the server, the
    helpers, the command-line client, `designer_preferences.py`). `mcp_server/designer_rollback.py`, new in this
    branch, is read by the server and sent into Designer with every call, and isn't named; nor does the flow below say
    that a failing call's step is taken back (`.claude/rules/docs.md`: architecture goes in How it works).
  - **Scenario.** A person reading How it works to find what runs inside Designer doesn't learn of the rollback.
  - **Fix.** Name it where the section says what is sent with each call, in a line.
  - **Resolution: done**.
    - **Test:** none can fail on a README sentence; settled by reading, the docs tests passing.
    - **Cause:** the branch added `designer_rollback.py` without a row in How it works or a word in its flow.
    - **Fix:** a row after the helpers' ("The rollback", sent with each call the server wraps in an undo step, run
      only when the call fails, taking back that call's own step while it is the newest, the error saying so), and the
      flow's step 1 ending "with the rollback that takes that step back if the program fails".
    - **Also covered:** `designer-code.md` names it (AGT-133); no other doc lists what is sent with a call.

- [x] **TST-868 · The self-test's unit tests write the tag's form by hand** · `tests/unit/test_selftest_pool.py:1007`, `tests/unit/test_selftest_pool.py:1221-1229` · confirmed · follows TST-865, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** `OWN = STEP + ' #0123abcd'`, and the `own_step` cases (`' #ffffffff'`, `' #0123abc'`,
    `'#0123abcd'`), spell the tag's current form. The user's instruction: the form is defined once, as constants,
    "so if we want to make it invisible we just change that constant", and "the unit tests check the tag against
    them".
  - **Scenario.** The tag made invisible by its constants alone: every firing test through `_undo_redo_on_fakes`
    fails, and the cases expecting no match pass without testing what they say.
  - **Fix.** Build `OWN` and the cases from `TAG_PREFIX`, `TAG_ALPHABET` and `TAG_LENGTH` (a character short, one
    more, one outside the alphabet; the missing-prefix case only while the prefix isn't empty). Generation 2: the
    tests only. With it, `project_constants.py`'s docstring says the self-test's Designer scripts import it in
    Designer's Python, so it keeps to the standard library (round 7's Unspecified).
  - **Resolution: done**.
    - **Test:** with the tag's constants set to the invisible form (`''`, four zero-width characters, 16), the tests
      as they were failed 7; rebuilt, they and `test_rollback`'s tag tests pass under it and under the real form.
      `test_project_constants_imports_only_the_standard_library` (`tests/unit/test_constants.py`) failed with `import
      pydantic` added to `project_constants.py`, and passes restored.
    - **Cause:** `OWN` and the own-step cases spelled the tag's current form.
    - **Fix:** `TAG = TAG_PREFIX + TAG_ALPHABET[0] * TAG_LENGTH`, `OWN = STEP + TAG`, a character outside the
      alphabet by construction, the cases in `OWN_STEP_CASES`, the missing-prefix case only while the prefix isn't
      empty. `project_constants.py`'s docstring: the self-test's Designer scripts import it inside Designer, so it
      imports only the standard library, which the new test checks.
    - **Also covered:** the other hand-written tags (`test_rollback.py`'s `LABEL` and siblings) are opaque names to
      `roll_back`, which compares exactly, and pass under the invisible form.

- [x] **AGT-134 · `designer-code.md` says the server sends the helpers and the rollback with every call** · `.claude/rules/designer-code.md:16-18` · confirmed · follows AGT-133, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** "The server reads the helpers and the rollback once, and sends them with every call." The code
    tools send no helpers (`scripting.py`, `_with_undo(code, ...)`), and the read tools send no rollback (no
    `_with_undo`). README's new row says it right: "with each call the server wraps in an undo step".
  - **Scenario.** A maintainer trusting the rule expects a failed read tool to run the rollback.
  - **Fix.** Generation 2, narrowing: the helpers with the calls that use them, the rollback with each call wrapped
    in an undo step; or only "reads ... once".
  - **Resolution: done**.
    - **Test:** none; a rule's sentence, the docs tests passing.
    - **Fix:** "The server reads the helpers and the rollback once. It sends the helpers with the calls that use them,
      and the rollback with each call it wraps in an undo step."
    - **Also covered:** README.md's helpers row made the same claim, and now says "with each call that uses them"; its
      rollback row was right. The note under TST-865: `history_facts.py`'s comment says what `del history` drops.

- [x] **TST-869 · No test sees the stack text's cap of `STACK_TOP` bytes** · `scripts/read_crash_dump.py:389`, `tests/unit/test_read_crash_dump.py:195` · confirmed · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** The docstrings say only the top `STACK_TOP` (256) bytes from sp are printed; no test's stack holds
    more than 0x60 bytes from sp.
  - **Scenario.** A refactor reads to the stack's end; on a real dump, which holds the thread's whole stack, the
    report prints thousands of lines, and every test passes.
  - **Fix.** A test whose stack holds more than `STACK_TOP` bytes from sp, expecting exactly `STACK_TOP // 64` lines.
  - **Resolution: done**.
    - **Test:** `test_only_the_top_of_the_stack_is_said` (`tests/unit/test_read_crash_dump.py`): a stack of 4 ×
      `STACK_TOP` bytes more than the frames, exactly `STACK_TOP // TEXT_LINE` lines starting `  sp+`. A guard: it
      failed with `_stack_top` reading `1 << 20` bytes, and passes restored.
    - **Fix:** the test only.

- [x] **TST-870 · One helper of the snippet tests still types Undo and Redo as `str`** · `tests/unit/test_selftest_pool.py:1033`, `tests/unit/test_selftest_pool.py:1042`, `tests/unit/test_selftest_pool.py:1064` · confirmed · follows TST-861, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** `-> tuple[ModuleType, list[str], ...]` and `fired: list[str] = []`, which only ever hold `'Undo'` or
    `'Redo'`; TST-861 gave the tests `Which` and missed this helper.
  - **Scenario.** A test appending another word type-checks.
  - **Fix.** `list[Which]`, and the loop over a `tuple[Which, ...]`. Generation 2: the tests only.
  - **Resolution: done**.
    - **Test:** none can fail, as mypy accepts `str`; mypy is clean.
    - **Fix:** generation 2, the tests only. `_undo_redo_on_fakes` returns `tuple[ModuleType, list[Which], ...]`,
      with `fired: list[Which]`, and its Edit menu's actions loop over `actions: tuple[Which, ...]`.

- [x] **TST-871 · The failed-save check of `create_graph` sees the graph gone, not the package** · `tests/test_all_tools/batch/checks.py:375-390` · confirmed · follows SRV-259, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** It checks that `describe_graph` says "not found in open user packages", true of any package without
    that graph; `create_graph`'s docstring (SRV-259's fix) promises the package taken back with the step, and names
    this check as its test.
  - **Scenario.** A Designer that no longer undoes `newUserPackage` in the group leaves an empty package after each
    failed save, and the check passes.
  - **Fix.** Count the open user packages before and after the call, and require them equal. Generation 2.
  - **Resolution: done**.
    - **Test:** `batch`'s `check_a_graph_whose_save_fails_leaves_no_package`, live in the developer's own Designer.
      The scenario was made with a scratch `setup(ctx)` opening an empty package after the failing `create_graph`:
      the check as it was passed ("not found in open user packages"); the new one failed (`PACKAGES=4 ->
      PACKAGES=5`). Without that leftover it passes, and so does the whole category, run twice.
    - **Fix:** generation 2, the check only. A `PACKAGES` snippet prints the count of open user packages, run before
      and after the call; the check requires `'PACKAGES=' in before and before == after`, so a failed read shows as
      its own error, and its detail shows both. The docstring says what is compared.

- [x] **TST-872 · Values of a known set typed `str` in the rollback's unit-test fakes and tables** · `tests/unit/test_rollback.py:37-38`, `tests/unit/test_rollback.py:312-342`, `tests/unit/history_fakes.py:25-63`, `tests/unit/history_fakes.py:200-299` · confirmed · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** The events' kinds (`'enter'`, `'commit'`; `'ActionAdded'`, `'ActionRemoved'`), the loop's flags,
    `invoked`'s `'undo()'` and the 7 outcomes of the notes table are `str` where a `Literal` is known
    (`.claude/rules/python.md`, the most specific type).
  - **Scenario.** A typo in a fake's event kind type-checks, and shows only as a failing comparison.
  - **Fix.** `Literal`s for each.
  - **Resolution: done**.
    - **Test:** none can fail; mypy is clean on `history_fakes.py`, `test_rollback.py` and `test_plugin.py`.
    - **Fix:** `history_fakes.py` gains `EventKind` (the menus' event kinds), `Flag` (the loop's flag), `Slot`
      (`invoked`) and `GroupEvent` (`sd_modules`' events), each a `Literal`; `test_rollback.py` uses `GroupEvent`
      in `_Probe`, and a `Says` `Literal` of the notes table's 7 outcomes.
    - **Also covered:** `test_plugin.py`'s `sd_modules([])` still type-checks.

- [x] **TST-874 · The first `undo_edits` check can't tell newest first from oldest first** · `tests/test_all_tools/batch/checks.py:517-540` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** It expects `['Claude: apply 1 edits', 'Claude: code', 'Claude: apply 1 edits']`, a palindrome, and
    its docstring says the reply names each call's step "newest first".
  - **Scenario.** A reply listing the steps oldest first passes.
  - **Fix.** Calls whose steps are named apart (two `apply_edits` of 1 and 2 ops, say).
  - **Resolution: done**.
    - **Test:** the check expects `['Claude: apply 2 edits', 'Claude: code', 'Claude: apply 1 edits']`. With the
      reply mutated to list oldest first, it failed in a scratch run.
    - **Fix:** the last call has two ops, so the names differ.

- [x] **TST-875 · The read check has the read on top of an edit, not between edits, and doesn't check which step is marked** · `tests/test_all_tools/batch/checks.py:596-618` · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** The approved text's live check is "a read tool's call between edits". The check makes an edit, then
    a `preview_node`, then `undo_edits()`. `re.search(SAID_STEP + r" \(a read of this session's", t)` matches the
    mark after any step, the edit's included.
  - **Scenario.** A planning slip that counts a read in the middle of the steps asked for, or marks the edit as the
    read, passes.
  - **Fix.** An edit, a read, an edit, then `undo_edits(count=2)`; the mark checked on the read's step and not on
    the edits'.
  - **Resolution: done**.
    - **Test:** the check is now an edit, `preview_node`, an edit, then `undo_edits(count=2)`. It checks each step's
      mark: `[('Claude: apply 2 edits', ''), ('Claude: preview node', READ_SAID), ('Claude: apply 1 edits', '')]`.
      With reads mutated to count, it failed: the first edit stayed and the graph changed.
    - **Fix:** as the entry asks.

- [x] **TST-876 · No live check of the refusal beyond the 25 listed steps, which a check's docstring claims** · `tests/test_all_tools/batch/checks.py:621-640`, `mcp_server/server_tools/undo.py` (the description) · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `undo_edits`' description says nothing is undone when the calls asked for aren't all among the
    newest 25 steps, and `check_the_undo_list_shows_the_newest_steps_only`'s docstring ends "undo_edits refuses calls
    asked for beyond the steps listed". No live check runs that refusal (AGENTS.md: a documented behaviour gets a
    live check).
  - **Scenario.** A refusal that undoes part of the steps passes every live check.
  - **Fix.** A live check of the refusal, after SRV-266's fix: a call, then more than 25 steps on top, then
    `undo_edits` refused with nothing undone. Or the docstring's claim dropped, and the description's held by a
    live check.
  - **Resolution: done**.
    - **Test:** `batch`'s `check_undo_edits_refuses_calls_beyond_the_steps_listed`: a call, 30 steps of `sd_run`'s on
      top, then `undo_edits(include_others=True)`. It is refused ("shows its newest 25 steps, and only 0 of the 1
      calls asked for"), and the graph is unchanged; the nodes are deleted after. With the `beyond` refusal
      disabled, it failed (a NO_STEPS refusal instead).
    - **Fix:** the live check; the facts check's docstring now points to it.
  - Questioned by TST-878 (2026-11-25).

- [x] **SRV-267 · The reload note says "not the user's" as a fact, and nothing says the reload's save stays in the file** · `mcp_server/server_tools/undo.py:40-41`, `mcp_server/server_tools/undo.py:113-118`, `mcp_server/server_tools/layout.py:247` · confirmed · follows SRV-265, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `if reloaded and _session['package_reloaded']:` adds "... are Designer's own steps of set_link_display's
    reload of a package, not the user's". The flag is set once for the whole session, and the four names are
    Designer's generic ones (`'Unknown'`, `'Open Package(s)'`, ...). `set_link_display` saved the package, the
    earlier edit included, before its reload. Round 9 measured that after `undo_edits(include_others=True)` the file
    keeps the edit and the display change, and no description says so.
  - **Scenario.** After one `set_link_display`, the user opens a package (File > Open) on top of the agent's calls.
    The refusal tells the agent that step is not the user's. Separately, an agent undoes across a reload and tells
    the user the edit is gone, while the saved file still holds it.
  - **Fix.** Generation 2, wording only. The note says the steps are most likely Designer's own, from
    `set_link_display`'s reload, without "not the user's". `set_link_display`'s description says that its save stays
    in the file after an undo.
  - **Resolution: done**.
    - **Test:** `test_the_reload_note_says_the_steps_are_most_likely_its_own_and_where_its_save_stays`
      (`tests/unit/test_undo_edits.py`) failed: the note said "not the user's", with no "most likely".
    - **Fix:** generation 2, wording only. `RELOAD_STEPS_NOTE` reads "Of these, %s are most likely Designer's own
      steps of set_link_display's reload of a package." `set_link_display`'s description adds: "Taking back the
      reload takes the display change back in Designer, but the file keeps what it saved, the edits made before it
      included."
    - **Also covered:** `link_display`'s live check matches the new wording and passes.

- [x] **SRV-268 · A read call's failure says Undo took back "its edits", and no test pins the text** · `mcp_server/server_tools/core.py:324` (`UNDONE`), `mcp_server/server_tools/discovery.py:119-120` · measured · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `describe_node` now runs in `_with_undo(..., edit=False)`. A misspelt definition makes the
    temporary package before it raises, so the error ends with `UNDONE`: "Designer's Undo took back the call's own
    undo step, with its edits. What the call did that the step doesn't hold stays, such as a file it wrote, and its
    package may still show as modified." A lookup has no edits and no package of the user's. `preview_node`'s and
    the other reads' failures say the same. No unit test or live check holds a read's failure text.
  - **Scenario.** An agent misspells a definition in `describe_node`, the commonest error of that tool, and reads the
    error as its own earlier edit being undone.
  - **Fix.** A read's failure (`edit=False`) says only that its temporary step was taken back. A unit test pins it.
  - **Resolution: done**.
    - **Test:** `test_a_reads_failure_says_only_its_own_step_was_taken_back` (`tests/unit/test_undo_edits.py`),
      over `describe_node`, `preview_node`, `node_stats` and `sweep_param`, with `apply_edits` still saying `UNDONE`.
      Each goes through the tool's real `_with_undo` and `_bridge`, only `_send` faked. It failed: no `READ_UNDONE`.
    - **Cause:** `_failure` said `UNDONE` for every rollback, not knowing the call was a read.
    - **Fix:** `READ_UNDONE`: "Designer's Undo took back the call's own undo step, which held only what the call made
      for itself." It keeps `ROLLED_BACK`, which the live checks look for. On `undone`, `_failure` finds the call's
      step as the newest in `STEPS` whose `UndoGroup(<name>)` the script sent holds, and says `READ_UNDONE` for a
      read's.
    - **Also covered:** every `edit=False` call takes that path, `check_tiling`, `compare_to_reference` and
      `search_nodes` included; the edits' text is unchanged. The text is the server's, so no live check holds it;
      `discovery`'s misspelt-definition checks match by substring and pass.
  - Questioned by SRV-270 (2026-11-25).

- [x] **SRV-269 · A failed call rolled back, older than the 25 listed steps, is never dropped** · `mcp_server/designer_rollback.py:237-239` (`undo_session`), `mcp_server/server_tools/core.py` (`STEPS`) · confirmed · follows SRV-266, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** SRV-266's fix drops a name with no step only when it is newer than the session's oldest listed step.
    A failed call that was rolled back, or a code call that changed nothing, stays an edit in `STEPS`. Once 25 steps
    or more have passed, it counts as maybe below the list, and `beyond` is refused for a count above the edits
    listed. The description says a step "undone or rolled back already doesn't" count.
  - **Scenario.** An early `apply_edits` fails and is rolled back. Many calls later, `undo_edits(count=N)` for every
    call left is refused with "An older step can't be checked", though that call left no step.
  - **Fix.** Generation 2. The server drops a call's name when its rollback said `undone` (it reads that state
    already). For a call that made no step, either the call reports it or the description narrows its claim,
    whichever is simpler.
  - **Resolution: done**.
    - **Test:** `test_a_failed_calls_step_its_rollback_took_back_is_forgotten[undone]`
      (`tests/unit/test_undo_edits.py`) failed (`assert 1 == 0`); its `[not ours]` case, the step kept, passes.
    - **Fix:** generation 2. `_failure`'s lookup of the call's step (SRV-268) drops it from `STEPS` when the rollback
      said `undone`. The no-step case takes the simpler option: `undo_edits`' description says "A call that made no
      step, such as code that changed nothing, still counts once it is older than the steps listed, so a count
      reaching past those is refused", which the existing `beyond` tests hold.
    - **Also covered:** a step its rollback kept (`not ours`, `failed`, `not landed`) stays remembered.

- [x] **TST-877 · The `search_nodes` check fails when a compositing graph is in the editor** · `tests/test_all_tools/batch/checks.py:713` (`check_undo_edits_takes_search_nodes_scan_along_uncounted`) · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** `list_atomic` (`designer_helpers/editor.py:356-363`) makes its temporary package only
    `if g is None`. With a compositing graph current, the scan makes no step, its name is dropped as gone, and the
    reply lacks `'Claude: search nodes'`, which the check requires. Its docstring states batch's preparation, not
    the editor.
  - **Scenario.** A Windows run is in the user's Designer (README, the self-test), where the user's graph can be
    in the editor while `batch` runs. The check fails on a correct build.
  - **Fix.** With a graph in the editor (`graph_in_editor`), the check is skipped with its reason, or accepts the
    reply without the scan's step.
  - **Resolution: done**.
    - **Test:** the check, in a scratch run whose `setup` opened batch's graph in the editor: as it was (the skip
      disabled), it failed, the reply naming only `'Claude: apply 1 edits'`; now it is skipped ("mcp_selftest is in
      the editor").
    - **Fix:** with `graph_in_editor(ctx.c)` non-empty, the check skips with its reason; its docstring says why.
  - Questioned by TST-885 (2026-11-25).

- [x] **TST-878 · The live "beyond" check can't see an undo that went partway** · `tests/test_all_tools/batch/checks.py:721-745` (`check_undo_edits_refuses_calls_beyond_the_steps_listed`) · confirmed · follows TST-876, generation 2 · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.** No call of the session is among the 25 listed steps, so nothing is planned and any code undoes
    nothing: the graph is unchanged by construction. TST-876's scenario was "A refusal that undoes part of the steps
    passes every live check", and it still does.
  - **Scenario.** A `beyond` condition regressed to `not asked` undoes one listed call of two and passes.
  - **Fix.** Generation 2, a check: an edit, the 30 steps, another edit, then `undo_edits(count=2,
    include_others=True)`. Expect the refusal ("only 1 of the 2") with the graph unchanged, the second edit's node
    still there.
  - **Resolution: done**.
    - **Test:** the check is now an edit, 30 steps of `sd_run`'s, another edit, then `undo_edits(count=2,
      include_others=True)`, expecting "only 1 of the 2 calls asked for" and the graph unchanged. With `beyond`
      mutated to `not asked`, it failed ("Undid 1 step..."); as is, it passes.
    - **Fix:** generation 2, the check its entry describes.

- [x] **TST-879 · Two unit tests of `undo_edits` pass on mutated code** · `tests/unit/test_rollback.py` (the full-list tests), `tests/unit/test_undo_edits.py` (`test_a_refusal_names_the_steps_of_a_reload_as_designers_own`) · confirmed · found 2026-11-25 by a reviewer (Sonnet)
  - **Defect.**
    - `any(edit for _, edit in steps[:first])` (`designer_rollback.py:239`) has no test with a read older than the
      list, so `bool(steps[:first])` passes every test.
    - The reload test's others are the four reload names only, so a note naming every other step passes.
  - **Scenario.** Either mutation passes the unit suite.
  - **Fix.** A full list with an older read and the edits listed, count 3: undone, the fewer said. The reload test
    with one more name, which the note leaves out.
  - **Resolution: done**.
    - **Test:** `test_with_the_dropdown_full_a_read_older_than_those_listed_doesnt_refuse_the_count`
      (`tests/unit/test_rollback.py`) fails on `bool(steps[:first])`. The reload test has one more step, `'Add Atomic
      Node'`, which the note leaves out, and fails on a note naming every other step.
    - **Fix:** the tests only.

- [x] **SRV-270 · A read's rollback text says its step held only what the call made for itself** · `mcp_server/server_tools/core.py:329` (`READ_UNDONE`) · confirmed · follows SRV-268, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** `READ_UNDONE = "Designer's Undo %s, which held only what the call made for itself."`. That is
    wrong for `sweep_param`, whose step holds values set on the user's node parameter, and its docstring says the
    sweep "marks the package as modified". It is wrong too for the reads that add a temporary output node to the
    user's graph (`preview_node`, `node_stats`, `check_tiling`, `compare_to_reference`). DECISIONS.md, Library
    packages, says that node "can leave the package marked modified". `UNDONE`, which these reads said before,
    kept "its package may still show as modified".
  - **Scenario.** `sweep_param` stops at its second value. Its error ends "... which held only what the call made
    for itself", and the agent tells the user nothing of theirs was touched, while their package shows as modified.
  - **Fix.** Generation 2, narrowing: the clause dropped, and the package's modified mark said where it can be.
  - **Resolution: done**.
    - **Test:** `test_a_reads_rollback_text_claims_nothing_of_what_its_step_held` (`tests/unit/test_undo_edits.py`)
      failed: the text said "made for itself" and not "may still show as modified".
    - **Fix:** generation 2, wording: `READ_UNDONE` reads "Designer's Undo took back the call's own undo step, and
      the package it worked in may still show as modified." Its comment names the sweep's values, the temporary
      output node and DECISIONS.md, Library packages.

- [x] **SRV-271 · With the tag's invisible form, `undo_edits`' replies show escapes, and five live checks fail** · `mcp_server/server_tools/undo.py:107`, `mcp_server/server_tools/undo.py:115-116`, `tests/test_all_tools/batch/checks.py:61` (`SAID_STEP`) · confirmed · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** The replies quote each step's name with `repr`. The invisible form `project_constants.py` gives
    (`'​‌‍⁠'`, 16) is made of characters Python's `repr` escapes. Checked: `repr('a​⁠')`
    is `'a\\u200b\\u2060'`. The user, 2026-11-24: "if we want to make it invisible we just change that constant".
  - **Scenario.** The constants are switched to the invisible form. Every name in `undo_edits`' replies carries 16
    `\uXXXX` escapes, about 96 visible characters. `SAID_STEP` expects the raw characters, so five `batch` checks
    fail.
  - **Fix.** The replies quote a name as `'%s'`, not with `repr`.
  - **Resolution: done**.
    - **Test:** `test_with_the_tags_invisible_form_the_reply_names_each_step_as_it_is`
      (`tests/unit/test_undo_edits.py`). In the test only, the tag's constants switch to the invisible form, in
      `project_constants` and the self-test's `common`. An edit's and a read's steps go through the real
      `_with_undo`, then `undo_edits()` and `undo_edits(include_others=True)` run on the faked history. It asserts no
      `\u` escape in either reply, and that the live checks' pattern finds both steps. It failed: the reply held the
      escapes.
    - **Fix:** `undo.py`'s `_quoted(name)` (`"'%s'"`) for every name in the replies, the refusal's and the reload
      note's included; `undo_steps`' "not ours" state quotes the top the same way. `batch/checks.py`'s `SAID_STEP`
      is built by `said_step()`, so the test builds it under the switched constants.
    - **Also covered:** the other `%r` and `repr(` in `mcp_server` are code literals, such as the script's
      `UndoGroup(%r)`, which must stay so. The tests and the live check that spelled the old quoting now use `'%s'`.
  - Questioned by SRV-272 (2026-11-25).

- [x] **TST-880 · No unit test holds the label `put_back`'s Redo is sent for** · `tests/test_all_tools/undo/edit_menu.py:315`, `tests/unit/test_selftest_undo.py` · confirmed · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** `redo = await send(c, graph, 'Redo', lambda described: described != before, sent.label)`. In
    `test_each_undo_and_redo_is_for_the_step_of_the_checks_own_call`, every Undo shows, so `put_back` never sends.
    `test_the_redo_putting_back_an_undo_that_never_showed_is_read_until_it_shows` goes through a fake that ignores
    the label.
  - **Scenario.** The label replaced by `''` passes the unit suite. The Redo then refuses `NOT_OURS` after a failed
    check, and the self-test leaves its own step undone in its own graph.
  - **Fix.** One recorded case of an Undo that never shows, expecting `('Redo', <the call's label>)`.
  - **Resolution: done**.
    - **Test:** a row `'set put back'` in `test_each_undo_and_redo_is_for_the_step_of_the_checks_own_call`: an Undo
      that fires and never shows, expecting `[('Undo', 'Claude: apply 1 edits'), ('Redo', 'Claude: apply 1
      edits')]`. It fails with `put_back`'s label emptied; the code was right.
    - **Fix:** the test only.

- [x] **TST-881 · GUIDE.md's rules still say "Prefer this over Undo"** · `mcp_server/GUIDE.md:20-21` · confirmed · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** "**`snapshot_graph` before risky or large edits** to a user's graph, then `diff_graph` and report
    the diff. Prefer this over Undo." The rule two bullets above says to undo one's own work with `undo_edits` and,
    with no other steps on top, to "undo as you need". A snapshot reverts nothing.
  - **Scenario.** An agent wanting its risky edit back is steered away from `undo_edits` by the rule below.
  - **Fix.** Drop "Prefer this over Undo."
  - **Resolution: done**.
    - **Test:** `test_no_rule_steers_an_agent_from_undo_edits` (`tests/unit/test_guide.py`) failed.
    - **Fix:** "Prefer this over Undo." is dropped from GUIDE.md's snapshot rule.

- [x] **TST-882 · ROADMAP items 37 and 112 cite GUIDE.md text step 4 removed** · `ROADMAP.md:57` (item 37), `ROADMAP.md:31` (item 112) · confirmed · follows TST-873, generation 3 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** Item 37: "GUIDE.md's rule: in the user's Designer, never trigger Undo unless the top step is your
    own", the old rule. Item 112: "GUIDE.md says such an Undo sometimes did nothing in a Designer just started
    ...", a sentence step 4 removed; the fact is now in `tests/test_all_tools/common.py`'s `UNDO_REDO` comment.
  - **Scenario.** An agent reading ROADMAP before proposing work meets a rule GUIDE.md no longer has, or looks for
    a fact GUIDE.md no longer holds.
  - **Fix.** Generation 3, narrowing, no check added: item 37's sentence gives step 4's rule or goes; item 112
    points to `UNDO_REDO`'s comment.
  - **Resolution: done**.
    - **Fix:** generation 3, narrowing, no check added. Item 37 reads "GUIDE.md's rule: undo your own work with
      `undo_edits`, and only with it."; item 112 points to `common.UNDO_REDO`'s comment for the main window's fact.

- [x] **TST-883 · "One undo history for every package" reads as one history per package** · `README.md:102`, `mcp_server/GUIDE.md:12`, `ROADMAP.md:57` · confirmed · follows TST-844, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** README: "Designer keeps one undo history for every open package". GUIDE.md: "Designer keeps one
    Undo history for every package". "One X for every Y" reads as one per package. The fact is one history shared
    by every package (`designer_rollback.py`'s docstring: "one history for the whole app").
  - **Scenario.** A user reads README, presses Ctrl+Z in package A's graph expecting A's newest step, and undoes
    package B's.
  - **Fix.** Generation 2, wording: one undo history shared by all open packages, in the three places.
  - **Resolution: done**.
    - **Test:** `test_the_one_undo_history_is_said_shared_by_every_package` (`tests/unit/test_guide.py`), over
      README.md, GUIDE.md and ROADMAP.md, failed in all three.
    - **Fix:** generation 2, wording: "one undo history, shared by all open packages" in README.md and item 37, "one
      Undo history, shared by all packages" in GUIDE.md's rule.

- [x] **INS-50 · The crash reader's docstring suggests the stack's values are printed** · `scripts/read_crash_dump.py:18-19` · confirmed · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** "the crashing thread's registers x0 to x30, and the top STACK_TOP bytes of its stack, each with its
    bytes' printable ASCII". Registers print a value and their text; the stack prints its text only
    (`_stack_top`).
  - **Scenario.** A diagnoser expects return addresses or a saved frame pointer from the stack lines, and gets text.
  - **Fix.** "... and the top STACK_TOP bytes of its stack as printable ASCII".
  - **Resolution: done**.
    - **Test:** none; a docstring, the docs tests passing.
    - **Fix:** "registers x0 to x30, each with its bytes' printable ASCII, and the top STACK_TOP bytes of its stack as
      printable ASCII".

- [x] **INS-51 · Two implicit `Any` in functions the branch adds** · `tests/unit/test_read_crash_dump.py:178`, `scripts/read_crash_dump.py:214` · confirmed · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** `opened = [os.path.abspath(call.args[0]) for call in spy.call_args_list]` is a `list[Any]` (Mock's
    `call.args`). `*regs, sp, pc = struct.unpack_from('<33Q', ...)` gives `Any`s returned unchecked as
    `tuple[list[int], int, int]` (`.claude/rules/python.md`, Typing: look for implicit `Any` yourself).
  - **Scenario.** A change of what either holds type-checks unseen.
  - **Fix.** `str(call.args[0])`; `int(...)` on the unpacked values, as the file's `read64` does.
  - **Resolution: done**.
    - **Test:** none can fail, as mypy sees no `Any`; `test_read_crash_dump.py` with lint and types passes.
    - **Fix:** `registers()` unpacks with `int(value) for value in struct.unpack_from(...)`; the test uses
      `os.path.abspath(str(call.args[0]))`.

- [x] **SRV-272 · The quoting of SRV-271's fix is tested at one of its five places** · `tests/unit/test_undo_edits.py:298-302`, `mcp_server/server_tools/undo.py:121-122`, `mcp_server/server_tools/undo.py:136`, `mcp_server/designer_rollback.py:171` · confirmed · follows SRV-271, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** The new test's only step that isn't the session's is untagged (`'Add Atomic Node'`), so only the
    list of steps undone is seen quoted under the invisible form. The refusal's others (`map(_quoted, others)`),
    the reload note's names, the step a stop names (`stopped_at`) and `undo_steps`' "not ours" (`"'%s'" % top`) can
    each go back to `repr` with every unit test passing: their tests use plain ASCII names. The resolution's "the
    tests that spelled the old quoting now use `'%s'`" says more than the tests do: most still build the expected
    text with `%r`, which matches only because the names are plain.
  - **Scenario.** With the invisible tag, another session's tagged step sits on top. The refusal's quoting reverted
    to `repr` shows 16 escapes per name, and no unit test fails.
  - **Fix.** Generation 2, a test may be added: under the switched constants, a tagged step of another session's
    on top (made after the switch, not remembered), so the refusal and the `include_others` reply name it; and a
    case of a stop midway and of `undo_steps`' "not ours" under the switch.
  - **Resolution: done**.
    - **Test:** in `tests/unit/test_undo_edits.py`, a parametrised `names` fixture gives four exact-equality tests
      either the plain fake names or invisible-tagged ones, made after the tag's constants switch to the invisible
      form; the third, another session's step, is never remembered. The tests: the refusal naming the other step,
      the `include_others` reply naming it, the step a stop midway names, and the step on top midway as
      `undo_steps`' "not ours" gives it. `test_rollback.py::test_another_step_on_top_is_left_alone` gains an
      `[invisible tag]` row. Each untested site reverted to `repr` alone failed its cases (the refusal's others; the
      stop's step; `undo_steps`' "not ours"), and passes restored. The reload note's names are Designer's fixed
      ASCII step names, which never carry the tag.
    - **Fix:** the tests only; the code was right. Every expected reply text in `test_undo_edits.py` now uses the
      literal `'%s'`; three built with `server._quoted(...)` use `"'%s'" % name`, so a reverted `_quoted` can't
      change both sides. Left with `repr`, as code literals: `'UndoGroup(%r)'` (as `_with_undo` writes it), and in
      `test_rollback.py` the `TAG_FORM` description test and the stand-in rollback's code.
    - **Also covered:** GUIDE.md's Redo sentence, the user's rule, is pinned word for word by
      `test_the_scripting_part_says_redo_may_be_triggered_from_code` (`tests/unit/test_guide.py`), which failed with
      the sentence removed (the lead's decision on round 12's leftover).

- [x] **SRV-274 · `_failure`'s `state` is typed `str | Any`** · `mcp_server/server_tools/core.py:408` · confirmed · follows SRV-264, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** `state = lines[-1].group(1) if lines else ''`. Typeshed gives `Match.group(1)` `AnyStr | MaybeNone`,
    and `MaybeNone` is `Any`, so `word`, `why` and the texts built from them go unchecked. SRV-264 narrowed `kept` in
    this function and missed this value from the same source.
  - **Scenario.** A change that makes `state` something else type-checks unseen.
  - **Fix.** Generation 2: `state: str = ...`.
  - **Resolution: done**.
    - **Test:** none can fail, as mypy sees no `Any`; lint and types pass.
    - **Fix:** generation 2, `state: str`.

- [x] **TST-884 · The example's two failing-build checks pass without the example closing its package** · `tests/test_all_tools/example/checks.py:50-80` · confirmed · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** The checks run the failing copies through `run_designer_script`, which now rolls back the whole
    build's step, its new package with it (round 11's fixes ran `example`: both errors end with UNDONE; TST-871
    measured an undone group's `newUserPackage` removing the package). So `UNSAVED_LEFT=0` holds whether or not the
    example unloads its package (`examples/build_dwarf_trimsheet.py:156-157`, `:518-521`).
  - **Scenario.** A refactor drops the example's unloads. A user runs it from Designer's Python Editor, where no undo
    group wraps it, and each failed build leaves an unsaved package; both checks pass.
  - **Fix.** Run the two failing copies through `sd_run`, which no undo group wraps, as a Python Editor run isn't.
    Seen failing with the unloads replaced by `pass`.
  - **Resolution: done**.
    - **Test:** both checks failed with the example's unloads replaced by `pass` (`UNSAVED_LEFT=1` and `=2`), and
      pass restored; `example` 15 PASS.
    - **Fix:** the two failing copies run through `sd_run`.

- [x] **TST-885 · The `search_nodes` check's docstring says any graph in the editor stops the scan's step** · `tests/test_all_tools/batch/checks.py:702-703` · confirmed · follows TST-877, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** "With a graph in the editor ... the scan makes no step". `list_atomic`
    (`designer_helpers/editor.py:356-363`) skips its package only for a compositing graph; with a function graph
    there it still makes its step.
  - **Scenario.** A maintainer reads the docstring as the rule of when the scan makes a step.
  - **Fix.** Generation 2, wording: "may make no step (with a compositing graph there)"; the skip stays.
  - **Resolution: done**.
    - **Fix:** generation 2, the docstring's wording.

- [x] **SRV-276 · The fallback keeps `UndoGroup`'s window, and the private C calls' results are ignored** · `mcp_server/server_tools/core.py:396-416` (`_with_undo`'s template) · confirmed · follows SRV-273, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** Under the fallback, every commit runs through traced Python (the lambda, `__exit__`,
    `commitTransaction`, `getContext`), so SRV-273's window comes back until the code is fixed again. Separately,
    the template ignores the `c_int` results of the two private C calls, where sd's own wrappers raise
    `APIException`: a failed commit now passes silently, and a failed open lets the code run outside any step.
  - **Scenario.** A Designer whose sd lost the private names reopens the window on every call. A commit Designer
    refuses goes unreported.
  - **Fix** (the user's choice, 2026-11-25: "ok go ahead", to the lead's proposal). Commit through sd's public
    `SDHistoryUtils.newTransaction` and `commitTransaction`, the functions `UndoGroup` uses, with Python tracing
    off around both calls. The template's frame is already untraced. The tracer is saved and put back after the
    open, and left off from the commit on, so no traced event can come between the code's end and the commit. Drop
    the private names (`TRANSACTIONS`), the fallback and its designer facts check, as nothing is left to fall back
    from. The public functions raise on a refused open or commit. The timeout check stays as the window's guard.
  - **Resolution: done**.
    - **Test:** in `tests/unit/test_rollback.py`, an open sd refuses raises its error and the code never runs (it
      failed: the code ran); a commit sd refuses raises its error (it failed: did not raise); the code runs traced.
      With the commit's `settrace(None)` removed, `test_plugin.py`'s k = 0 to 79 sweep fails from k = 51, and
      `batch`'s timeout check fails, all five aimed calls left open; on the fix both pass.
    - **Fix:** generation 2, the user's choice. The template imports `SDHistoryUtils` and sets its own frame's
      `f_trace` to None. It binds `sys.settrace`, saves the tracer, turns tracing off, calls `newTransaction`, and
      puts the tracer back before the code runs. In both branches it turns tracing off, then calls
      `commitTransaction`, tracing left off from there on. Read in sd's `sdhistoryutils.py`: `UndoGroup` calls
      exactly those two functions, and both raise `APIException` on an error result. Removed: `TRANSACTIONS`, the
      fallback and its two unit tests, the designer facts check. The fakes' `SDHistoryUtils` functions are Python
      over C stand-ins, so they trace as sd's do.
    - **Also covered:** the new template's own first version turned tracing off through
      `_builtins.__import__("sys")`, between the code's end and the commit. In Designer `__import__` is
      `__feature_import__`, which runs Python (`feature_import`): the timeout check failed with all five aimed
      calls left open, and a probe put the abort on that line. `sys.settrace` is now bound before the code runs.
      The k = 0 to 79 sweep installs a Python `__import__` as Designer does; it failed at k = 44 to 46 on that
      version and passes on the fix. `batch` passed whole twice in Designers just started.
    - **Note (2026-11-25, round 15):** no test fails with the open's tracing-off pair removed, as the fakes'
      preamble and the live check's deadline can't reach the open; the code is right by reading, and
      `test_rollback.py`'s comment there says more than its test checks.

- [x] **SRV-277 · The two docstrings on where an abort lands say too much and too little** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:151-156`, `mcp_server/designer_rollback.py:19-22` · confirmed · follows SRV-273, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.**
    - Both say, unconditionally, that the server's calls commit "out of its reach", which was false under the
      fallback.
    - The plugin's docstring names only an abort inside a context exit's own Python code. Round 13 also measured
      one on the `with` line as the block ends, which skips the exit whole, even an exit written in C.
  - **Scenario.** A maintainer reads a C `__exit__` as safe from the abort.
  - **Fix.** Generation 2, wording, after SRV-276's switch: say how the server's calls commit out of the abort's
    reach (tracing off), and that an abort can land between a block's end and its exit call. The plugin change is a
    docstring; the lead reinstalls it, as the user agreed.
  - **Resolution: done**.
    - **Fix:** generation 2, wording. The plugin's `_make_tracer` docstring and `designer_rollback.py`'s say that an
      abort on the `with` line as a block ends, before the exit is called, skips the exit whole, even one written in
      C (round 13's landing probe), and that the server's calls commit out of its reach because tracing is off from
      their code's end to the commit. The lead reinstalled the plugin on the user's word, the installed copy
      matching the repo's.
    - **Note (2026-11-25, round 15):** only the plugin's docstring says "even one written in C"; both say the server's
      calls commit out of the abort's reach.

- [x] **TST-886 · `batch`'s recorded times contradict each other** · `tests/test_all_tools/categories.py:58-61` · confirmed · follows SRV-273, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** The figure went from 37 s, to 66 s (SRV-273's resolution), to 29 s, to 22 s in the developer's
    last runs, while checks were only added. The pool starts categories slowest first by these figures, and one of
    them is false.
  - **Scenario.** `batch`, placed by a figure too low, ends the full run's tail.
  - **Fix.** Two scratch runs of `batch` in a Designer just started, with each check's time logged; if one is far
    slower, find the check that waits; then the figure, the order and SRV-273's resolution's figure.
  - **Resolution: done**.
    - **Measured:** two runs of `batch`, each in a Designer just started: 31.0 s and 28.5 s, each check's time from
      the gaps in `common.checked`. No check is far slower: the first holds the start (6.7 to 10.1 s), the timeout
      check 7 s, the `search_nodes` scan check 2.8 s, every other under 1.5 s.
    - **Fix:** `categories.py` records 30 s, placed between `link_display` (30 s) and `safeguards` (23 s). SRV-273's
      66 s was wrong; a note under it says so.

- [x] **TST-887 · The timeout check commits a transaction even when none is open** · `tests/test_all_tools/batch/checks.py:877-883` (`kept()`) · confirmed · follows SRV-273, generation 2 · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** The docstring says "A step left open is committed". The code sends `commitTransaction()` whenever
    the step isn't listed for any reason: a user's step on top, a node count that differs, a first call not rolled
    back. What a commit with nothing open does in Designer is unmeasured.
  - **Scenario.** On a Windows run in the user's Designer, the user makes a change during the check, and the check
    sends a commit with nothing open into their Designer.
  - **Fix.** Generation 2: commit only when the step is shown open (this call's node is there, and the Undo top is
    unchanged).
  - **Resolution: done**.
    - **Test:** `test_the_timeout_check_commits_only_a_step_shown_open`
      (`tests/unit/test_selftest_check_setups.py`) failed first: a user's step on top gave `open`.
    - **Fix:** generation 2. `step_shown()` in `batch/checks.py` says `listed`, `open` (the call's node is there and
      the Undo top unchanged) or `other`; only `open` is committed.

- [x] **TST-888 · README names a narrower `include_others` window than the check has** · `README.md:280-281`, `tests/test_all_tools/batch/checks.py:633-639` · confirmed · found 2026-11-25 by a reviewer (Opus)
  - **Defect.** README: "a change you make between that check's refusal and its second call would be undone too".
    The check calls `undo_edits(include_others=True)` whatever the refusal named, so a change made between its
    `apply_edits` and the refusal is undone too. The user's decision 2 of 2026-11-25 accepted the narrower window.
  - **Scenario.** On a Windows run in the user's Designer, the user changes something during the check's two
    `sd_run` calls. The check fails, and still undoes the user's change.
  - **Fix.** The check calls `include_others` only when the refusal named exactly its two `sd_run` steps, which keeps
    the window the user accepted.
  - **Resolution: done**.
    - **Test:** a scratch run of the real check with one more `sd_run` step made after its two, as a user's change
      would be: before the fix, `include_others` was sent and "Undid 4 steps", the extra one included; after it, it
      isn't sent, and the check fails saying what the refusal named.
    - **Fix:** `include_others` is sent only when both `sd_run` steps were made and the refusal named exactly two;
      the docstring and README's sentence say so.
