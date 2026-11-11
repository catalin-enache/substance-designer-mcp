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

**Last used:** PLG-42, SRV-105, HLP-101, INS-27, TST-287.

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
| Low-medium | 0 | 1 |
| Low | 0 | 5 |
| **Total** | **0** | **6** |

## Review log

### 2026-11-11: branch `pool-rules-in-one-place` against main (ROADMAP item 68), the diff only

- **How:** two reviewers, one on the docs (the live-check skill, AGENTS.md, README, ROADMAP, the docstrings the skill
  now points at), one on the code and tests (`workers.py`, `__main__.py`, the new tests in `test_guide.py` and
  `test_selftest_pool.py`); no tests run, no Designer touched. Every suspicion settled by reading; none needed a probe,
  none settled as wrong. Both reviewers found TST-282, TST-283 and TST-284 on their own: merged.
- **Not verified:** none.
- **Resolutions assessed:** none in scope (the file held no entries). DECISIONS.md's full-suites rule names
  `workers.py` and the live-check skill: both still there, and the skill still lists what a scratch run can't prove.
- **Findings:** TST-282 (Low-medium), TST-283, TST-284, TST-285 (Low). Longest chain growing: none (all generation 1).
- **Suggested order:** TST-282 first (README contradicts ROADMAP item 68's Done text), with TST-284, whose narrow
  regex let README's copy through; then TST-283 and TST-285, both a sentence each.
- **Checked and found fine:** everything else the old skill bullet said is in `workers.py`'s docstring (the rules), in
  `worker_env`'s and `start_unit`'s docstrings (the folders) or in AGENTS.md (one command for both suites, `--only`,
  `--no-unit`); each new test fails on the old text and passes on the new (every `POOL_RULES` name was in the old
  bullet; each of the four docs said "four at once" or "4 by default"; `choose(None)` returned 4 and `--help` said
  "(default 4)" with `AT_ONCE` patched to 7); the bullet regex stops before the "Python with real logic" sub-bullet;
  the new pool test restores what it patches (`fresh`, `monkeypatch`, `sys.platform`) and lists no processes;
  `--help`'s `%d` is formatted before argparse's own `%` expansion; typing and ruff; `choose`'s `asked or AT_ONCE`
  (main refuses `--workers` below 1); the other "four"/"4" in docs are measurements or ROADMAP item 66's own problem
  statement; changed Markdown lines are within 120 characters.

### 2026-11-11: branch `pool-rules-in-one-place` against main, the whole diff, after TST-282 to TST-285

- **How:** two reviewers, docs (the skill, AGENTS.md, README, ROADMAP, the two docstrings) and code and tests
  (`workers.py`, `__main__.py`, the new tests in `test_guide.py` and `test_selftest_pool.py`); no tests run, no
  Designer touched (the reviewers ran the tests' regexes on quoted text in plain Python). Every suspicion settled by
  reading; none settled as wrong. Both found the overclaims merged into TST-286.
- **Not verified:** none.
- **Resolutions assessed:** TST-282 to TST-285 all hold for what they fixed (each test failed on the text or code
  before its fix: checked against 73486ea). Questioned: TST-284's Also covered ("TST-283's and TST-285's tests say what
  they read") and TST-283's test, by TST-286; TST-282's scope (the count's last hop, `run_pool` to `schedule`), by
  TST-287.
- **Findings:** TST-286, TST-287 (Low). Longest chain growing: TST-283 / TST-284 → TST-286 and TST-282 → TST-287,
  generation 2, about tests and docs only: the next round of this kind narrows claims (Follow-up chains).
- **Suggested order:** TST-287 (the one that could hide a wrong count), then TST-286.
- **Checked and found fine:** every pointer leads to text holding what is claimed (skill → `workers.py`'s docstring,
  for the rules and which category runs the start checks; skill → AGENTS.md for commands; AGENTS.md and
  `__main__.py` → `workers.py`; README → `--help`, printing `AT_ONCE`); nothing of the old skill bullet is lost
  (`launch_lock.py`'s docstring holds the lock's two windows); the docstrings match `choose`, `run_pool`, `one_run`
  (`CATEGORIES` leaves `lifecycle` out, kept so by `test_every_category_but_lifecycle_is_listed_once_by_its_run`),
  `finish` (the quit skipped on win32) and `main`; `AT_ONCE` read only by `choose` and `--help`, every caller of
  `run_pool` and `choose` passing a count; the bullet regex; isolation of the new pool test; typing and ruff;
  `test_guide.py` already in the docs-only command; changed lines within 120 characters but table rows.

---

## High

## Medium-high

## Medium

## Low-medium

- [x] **TST-282 · Copies of the default count that the change left: README's architecture table, `run_pool`'s default, and a test's literal** · `README.md:53`, `tests/test_all_tools/workers.py:280`, `tests/unit/test_selftest_pool.py:272, 280` · confirmed · found 2026-11-11
  - **Defect.** ROADMAP item 68 (Done) says the number is `workers.AT_ONCE` and README says "several at once", but
    README's "How it works" table still says "the end-to-end self-test (on macOS four worker processes at once, ...)";
    `run_pool` keeps a default of its own, `def run_pool(slots: int = 4, ...)`, which no caller uses (`main` and every
    unit test pass `slots`); and `test_a_pool_of_four_unless_asked_off_macos_or_with_the_users_designer` pins
    `(None, 'darwin', False, 4)`, its name saying four too.
  - **Scenario.** ROADMAP item 66 sets the default from the machine's memory: README's table still says four, the
    drift item 68 was opened for; a scratch script calling `workers.run_pool(unit=False)` starts 4 whatever
    `AT_ONCE` says; the old test fails on a correct change, its name stale.
  - **Fix.** README:53: "several worker processes at once". `run_pool`: drop the default (`slots: int`), not
    `= AT_ONCE`, which binds at import and wouldn't follow a patch. The parametrized case expects `workers.AT_ONCE`,
    read when the test runs, and the test is renamed. (Two reviewers.)
  - **Resolution: done.**
    - **Test:** `test_these_docs_say_four_neither_at_once_nor_by_default[README.md]` (`test_guide.py`, its pattern
      widened to "four" and up to two words before "at once") failed on "four worker processes at once";
      `test_at_once_alone_holds_the_default_number` (`test_selftest_pool.py`) failed on `run_pool`'s `slots: int = 4`
      (`inspect.signature`: the default was 4, not empty).
    - **Cause:** the change replaced the phrasings it searched for ("four at once", "4 by default") and the two
      readers it named (`choose`, `--help`); README's architecture table and `run_pool`'s signature said the number in
      other words.
    - **Fix:** README:53 "several worker processes at once"; `run_pool(slots: int, ...)`, no default (every caller
      passes one); `test_a_pool_of_at_once_unless_asked_off_macos_or_with_the_users_designer` expects
      `workers.AT_ONCE`, read when it runs.
    - **Also covered:** searched `tests/test_all_tools/`, the pool's unit tests and fakes for `or 4`, `= 4`, `slots=`:
      only `test_the_index_runs_a_pool_one_run_off_macos_and_nothing_next_to_the_users_designer`'s fake `choose`
      (`asked or 4`), which returns its own value and expects it back, so it can't drift from `AT_ONCE`; left. The
      calls `run_pool(4)` in the unit tests pass a count of their own. The other "four"/"4" in docs are measurements or
      ROADMAP item 66's problem statement.
  - Questioned by TST-287 (2026-11-11).

## Low

- [x] **TST-283 · The skill's "What a scratch run can't prove" still says where and when the pool runs the start checks and the crash-dump wait** · `.claude/skills/live-check/SKILL.md:72, 76-78` · confirmed · found 2026-11-11
  - **Defect.** ROADMAP item 68 names "the start checks, the crash dumps" among the rules the skill repeats; the change
    and its test cover only the self-test bullet, and the list keeps "**The run's start checks,** in the first
    category to start after `lifecycle` (`--first`)" and "(`check_the_quits`, after one wait at the end)". The first
    is the sentence that went false once already (TST-265: `first` became the first category not in `SOLO`).
  - **Scenario.** `run_pool` changes which worker gets `--first`, or how it waits for crash dumps; `workers.py`'s
    docstring is updated, this list goes stale, and no test fails (`test_the_skill_points_at_workers_py_for_the_pools_rules`
    reads only the bullet).
  - **Fix.** Keep the names, which this list needs; drop where and when they run, pointing at `workers.py`'s
    docstring instead. (Two reviewers.)
  - **Resolution: done.**
    - **Test:** `test_the_skill_words_no_rule_of_the_pool_as_workers_py_does` (`test_guide.py`), parametrized over
      five wordings of `workers.py`'s docstring ("starts first", "never run at once", "last, alone", "first category
      to start after", "one wait at the end"), each also asserted to be in that docstring, over the whole skill: failed
      on the last two, which the list held.
    - **Cause:** item 68's change and its test covered only the skill's self-test bullet; this list kept where and when
      two of the rules run.
    - **Fix:** the skill's list keeps the names (`--first`, `check_the_quits`, the launch lock, `CLIPBOARD`, `SOLO`)
      and sends "which category runs them" to `workers.py`'s docstring; "after one wait at the end" removed.
    - **Also covered:** the rest of the skill holds none of the five wordings (the test reads it whole); AGENTS.md
      describes no rule of the pool; README's categories table (`undo` last, alone) is for people, README's job, and
      outside this diff.
  - Questioned by TST-286 (2026-11-11).

- [x] **TST-284 · The new doc tests check less than their names and ROADMAP item 68's Done text say, and the count test flags measurements** · `tests/unit/test_guide.py:591, 602, 623-626`, `ROADMAP.md:104`, `README.md:213` · confirmed · found 2026-11-11
  - **Defect.** The Done text says "`test_guide.py` fails on a rule copied into the skill's bullet or a default count
    written in those docs". `test_only_workers_py_says_how_many_run_at_once_by_default` matches four phrasings,
    `\b(?:four|4) (?:at once|by default)\b|\bdefault (?:four|4)\b`: it misses README:53's "four worker processes at
    once" (TST-282), "defaults to 4" or "(default: 4)", and any other number once item 66 changes it, while it fails on
    a measurement written "4 at once" (README's "four at once was measured on a 64 GB Mac" was reworded to "four side
    by side ran" to pass it). `test_the_skill_points_at_workers_py_for_the_pools_rules` looks for six names
    (`POOL_RULES`), so a rule copied back in other words ("`undo` last, alone") passes.
  - **Scenario.** An agent trusts the Done text and takes any new copy of the count in those docs as caught; README:53
    already got through.
  - **Fix.** Make the claims say what is checked: the Done text and the test names ("no doc says four at once or 4
    by default"; "the skill's bullet names none of the pool's rules"). Fixing README:53 is TST-282. (Two reviewers.)
  - **Resolution: done.** The claims narrowed to what is checked; no stronger check for the rules' wording (a
    paraphrase still passes, and says so).
    - **Test:** the renamed tests, run before and after; the count test widened by TST-282 failed on README:53.
    - **Cause:** the names and the Done text described the aim, not the checks.
    - **Fix:** `test_the_skills_bullet_points_at_workers_py_and_names_none_of_the_pools_rules` ("only these names are
      looked for"); `test_these_docs_say_four_neither_at_once_nor_by_default` ("only these phrasings of 4"; a
      measurement made with four is written without "at once", as README's "four side by side"); its pattern also
      takes "default: 4" and "defaults to 4". ROADMAP item 68's Done text lists what each test fails on.
    - **Also covered:** the other new tests' names: `test_at_once_alone_holds_the_default_number` checks `choose`,
      `--help` and `run_pool`, as its comment says; TST-283's and TST-285's tests say what they read.
  - Questioned by TST-286 (2026-11-11).

- [x] **TST-285 · The skill now points at `workers.py` for a Windows run, whose docstring says only "one run, as before"** · `tests/test_all_tools/workers.py:29-30` · confirmed · found 2026-11-11
  - **Defect.** The change removed the skill's "On Windows: one run, without the unit suite; it starts Designer if
    none runs and leaves it open at the end, as one already running, the checks that quit Designer skipped (ROADMAP
    item 65)". The places it points to say less: `workers.py` "Off macOS, where launch_designer starts one per port
    only there, it is one run, as before" ("before" the pool, which the reader can't see), AGENTS.md "On Windows it
    makes one run instead, leaving the unit suite out". What one run does is in `__main__.py`'s docstring and README.
  - **Scenario.** An agent writing a check that quits Designer follows the skill's pointers and doesn't learn that a
    Windows run leaves Designer open and skips `lifecycle` (little weight while the pool and scratch runs are macOS
    only: ROADMAP items 18 and 65).
  - **Fix.** `workers.py`'s last sentence: "it is one run in one Designer (`__main__.py`'s docstring)", in place of
    "as before".
  - **Resolution: done.**
    - **Test:** `test_workers_py_sends_a_windows_run_to_the_index_which_says_what_it_does` (`test_guide.py`): failed,
      `workers.py`'s docstring lacking "one run in one Designer (`__main__.py`'s docstring)"; it also asserts
      `__main__.py`'s docstring says "every category but `lifecycle`" and "leaves it open at the end".
    - **Cause:** the removed skill sentence was the only one beside README saying both what a Windows run leaves out and
      that it leaves Designer open; the places the skill points to said "one run" without what it does.
    - **Fix:** `workers.py`'s last sentence points at `__main__.py`'s docstring, which now also says the run is "of
      every category but `lifecycle`" (`one_run` runs `CATEGORIES`, which leaves it out).
    - **Also covered:** AGENTS.md's "On Windows it makes one run instead, leaving the unit suite out" is the command
      advice it needs; README's Self-test section and commands table already say both.

- [x] **TST-286 · The doc tests' names, comments and ROADMAP item 68's Done text still say more than they check, and the wordings test reads the whole skill · follows TST-283 and TST-284, generation 2** · `tests/unit/test_guide.py:593-599, 624-627, 646-655`, `ROADMAP.md:104` · confirmed · found 2026-11-11
  - **Defect.**
    - `test_the_skill_words_no_rule_of_the_pool_as_workers_py_does` and the Done text ("fails ... on the skill
      wording a rule as `workers.py`'s docstring does") claim every rule; the test looks for five fixed phrases
      (`POOL_RULE_WORDINGS`), two of which ("starts first", "never run at once") the old skill never used: it said
      "`lifecycle` first" and "never at once". Its comment lacks the "only these ... are looked for" the other two
      tests carry (TST-284's Also covered missed it).
    - It reads the whole skill, where other modules' rules are worded alike: SKILL.md:64-65, lifecycle's
      `CrashWatch`, "one 10 s wait at the end of `lifecycle.run`"; SKILL.md:36, `alone.py`'s rule on `facts` and
      `editor_panels_and_fit`. `POOL_RULES`' `'spawn'` matches "spawned" in the bullet too.
    - `test_these_docs_say_four_neither_at_once_nor_by_default`: the "by default" branches need the words side by
      side ("four Designers by default", "the default is 4", "(default of 4)" pass), while the Done text says "four
      ... at once" with any gap (the pattern allows two words). Its comment says each of these said 'four at
      once': the skill said "(4 by default)".
  - **Scenario.** An agent trusts the Done text and copies "no folder shared between workers" into the skill's
    can't-prove list: the tests pass. Someone drops "10 s" from the `CrashWatch` sentence: the test fails on a rule
    that isn't the pool's.
  - **Fix.** Narrow, no new phrasings (generation 2 of a chain about tests and docs only): the wordings test reads only
    the self-test bullet and the "What a scratch run can't prove" list, its name and comment say "these phrases" and
    "only these are looked for"; the count test's name says what it matches ("four or 4 at once or by default, as
    these phrasings"), its comment "said 'four at once' or '4 by default'"; the Done text gives each test's
    check as it is. (Two reviewers.)
  - **Resolution: done.** The claims narrowed and the phrase test confined to the pool's two passages; no new phrasings.
    - **Test:** the old `test_the_skill_words_no_rule_of_the_pool_as_workers_py_does` failed when the skill's
      `CrashWatch` sentence (lifecycle's, not the pool's) lost its "10 s"; its replacement passes on that edit. Checked
      by mutations, each put back from git: the crash-dump wait copied back into the can't-prove list, and where the
      start checks run copied into the bullet, fail it; "spawned" in the bullet passes the names test, "`workers.spawn`"
      fails it.
    - **Cause:** TST-283's test was written over the whole skill and named for every rule; TST-284 narrowed the other
      two tests' claims but not this one's, nor the count test's comment.
    - **Fix:** `test_the_skills_pool_passages_have_none_of_these_phrases_of_workers_py` reads only the self-test bullet
      (`_skill_bullet`) and the list of what a scratch run can't prove (`_skill_cant_prove_list`), its comment "only
      these phrases are looked for, and only there"; the names test matches whole words; the count test is
      `test_these_docs_have_none_of_these_phrasings_of_four_at_once_or_by_default`, its comment listing what the pattern
      takes and saying the docs said "four at once" or "4 by default"; ROADMAP item 68's Done text gives each test's
      check as it is.
    - **Also covered:** the other new tests' names and comments: `test_workers_py_sends_a_windows_run_to_the_index_
      which_says_what_it_does` asserts the three phrases its name implies; `test_at_once_alone_holds_the_default_number`
      checks `choose`, `--help` and `run_pool`'s signature, the last hop being TST-287's assertion.

- [x] **TST-287 · The pool's unit tests can't see `run_pool` passing its count on: the fake `schedule` drops `slots` · follows TST-282, generation 2** · `tests/unit/selftest_fakes.py:119-123`, `tests/test_all_tools/workers.py:325`, `tests/unit/test_selftest_pool.py:301` · confirmed · found 2026-11-11
  - **Defect.** TST-282 took the default out of `run_pool`'s signature and `test_at_once_alone_holds_the_default_number`
    checks `choose`, `--help` and that signature; the count's last hop, `run_pool` handing `slots` to `schedule`, is
    unchecked: the fake `def schedule(names: list[str], slots: int, start: Any, **kw: Any)` never uses `slots`, and no
    test reads the "%d at once" line `run_pool` prints.
  - **Scenario.** An edit writes `schedule(order, AT_ONCE, ...)` or a literal 4 in `run_pool`'s body: `--workers 2` is
    ignored, a copy of the default is back, and every unit test passes (the index's test fakes `run_pool`).
  - **Fix.** The fake records `slots`; a test calling `run_pool(3)` asserts it reached `schedule`.
  - **Resolution: done.** No code defect (`run_pool` passes `slots`); the tests now see it.
    - **Test:** `test_the_pool_runs_every_category_once_and_prints_one_summary` asserts `workers.slots == 3` after
      `run_pool(3)`. Mutation, put back from git: `run_pool` handing `AT_ONCE` to `schedule` in place of `slots` fails
      it.
    - **Cause:** TST-268 made the fake `schedule` check what `run_pool` passes on (`exclusive`, `solo`, `gate`) but not
      the count.
    - **Fix:** the fake `schedule` in `tests/unit/selftest_fakes.py` records `slots` on the module; the test reads it.
    - **Also covered:** every other argument `run_pool` hands `schedule` (`start`, `answering`, `gate`, `exclusive`,
      `solo`, `on_end`): `start` runs each worker in the fake, `gate`, `exclusive` and `solo` are asserted (TST-268),
      `answering` is exercised by `schedule`'s own tests (`test_selftest_pool.py`); `on_end`, which only times each
      category for the summary, is called by no fake and checked by no test: a display, left.
