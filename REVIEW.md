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

**Last used:** PLG-42, SRV-148, HLP-146, INS-36, TST-418.

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
| Medium | 0 | 3 |
| Low-medium | 0 | 20 |
| Low | 0 | 90 |
| **Total** | **0** | **113** |

## Review log

### 2026-11-13: the preferences-put-back branch against main (the diff only: ROADMAP item 67)

- **How:** three reviewers read the diff (uncommitted, three new files): the product code (`designer_preferences.py`,
  the changed parts of `server_tools/lifecycle.py`, `uninstall.py`), the tests and the pool's new end check, and the
  docs and docstrings. No tests run. The lead agent settled every suspicion by reading, and with two probes outside
  Designer, on scratch domains and the user's plist read only: a plist file cfprefsd had never read, made unreadable
  (mode 000), exports as an empty `<dict/>`, exit 0 (SRV-126); the user's plist (a copy exported before the work)
  holds no `<real>` value and 65 booleans. Settled as wrong: a render tool (`sbsrender`, `sbscooker`) writing the
  user's Designer log, which would make every put-back drop its copy and the pool's check skip (two reviewers): that
  log's mtime is 2026-11-07, though the full run of 2026-11-12 ran the `render` category and today's runs ran since;
  values compared with `==` missing a NaN or a bool turned int: the user's file has no reals at all, and no change of
  a value's type was ever seen; a test comment saying a bridge run "added nothing" (the run's own check said "0 keys
  added").
- **Not verified:** none.
- **Resolutions assessed:** none in scope (no earlier findings on this branch).
- **Findings:** TST-356 (Medium); SRV-125, SRV-126 (Low-medium); SRV-127 to SRV-132, INS-34, TST-357 to TST-365 (Low).
  Merged: SRV-129 and SRV-132 (the product and docs reviewers), INS-34 (the same two), TST-358 (two lists of the
  tests reviewer). Leftovers in tests, not findings: the unit tests' `dict(BEFORE)` and `dict(_USERS)` are shallow
  copies of constants holding lists and dicts (none is changed in place today); `FakeDefaults`' delete error says
  "Domain ... not found." where the real `run_defaults` would keep stderr's last line (no test reads it); the pool
  tests repeat `workers.PREFERENCES` as a string of their own (a rename fails them loudly); `test_the_copy_is_the_users_alone`
  can't tell 0o600 from 0o644 under a 077 umask.
- **Suggested order:** TST-356 first (the Windows unit suite stops collecting two files); then the user's file:
  SRV-126, SRV-125, SRV-131, SRV-130, SRV-127, SRV-128; then the messages (SRV-129, INS-34), the tests (TST-357,
  TST-358, TST-360, TST-361), and the docs (SRV-132, TST-359, TST-362 to TST-365). SRV-125's and SRV-131's fixes are
  design choices worth showing the user first.
- **Simplifications:** none.
- **Checked and found fine:** the preferences lock is a leaf: taken under `_launch_lock(port)` in a launch, never
  holding a port lock itself, so no deadlock; `saved()`, the put-back and Popen run under one flock, and Popen returns
  after exec, so a put-back once it is released sees the new process (`pgrep -f`); the copy is made once while any
  Designer runs and put back by the last quit; deletes then import are idempotent on a retry and the copy is kept
  until the read-back matches; no exception escapes into a tool (`run_defaults` maps OSError, SubprocessError and its
  timeout to PreferencesError; a lock that can't be opened becomes a sentence; `_any_designer` counts an unlistable
  state as running); the `with A if home else nullcontext('') as said` construct; nothing done off macOS (`saved()`,
  `put_back()`, `_preferences_items`; `fcntl` imported inside `_lock`); `designer_preferences.py` and `uninstall.py`
  run on Python 3.9 (`from __future__ import annotations`, nothing evaluated at runtime); the copy is made 0600 with
  `O_CREAT|O_EXCL` and put in place with `os.replace`; `FakeDefaults` behaves as the real `defaults` where the code
  depends on it (whole-domain XML export, empty when never written, delete of a missing key failing, import merging);
  no unit test reaches the real `defaults`, the user's log folder, home or Designers today (AGENT_RECORD_DIR and the
  data folder patched; uninstall loads the same patched module; every `run_pool` goes through `pool()`, which fakes
  `designer_pids`); each new test fails without what it guards, besides the branches TST-358 lists; no older test
  weakened (the summary count grows by the one new check on macOS); the ROADMAP item 67 note matches what was
  measured; the DECISIONS entry has its parts and sits under Bridge and quitting; the other mentions of the shared
  plist (`alone.py`, `launch_lock.py`, the hand-over check, `editor_panels_and_fit/checks.py`) still read right.
- **Chains:** none; every finding is generation 1.

### 2026-11-13: the preferences-put-back branch against main, second review (the diff only: ROADMAP item 67 and the typing rules)

- **How:** three reviewers read the diff, two commits (the feature with the first review's fixes; AGENTS.md's typing
  rules, the review skill's types, ROADMAP items 98 and 99): the product code (`designer_preferences.py`, the changes
  to `server_tools/lifecycle.py` and `uninstall.py`), the tests and the pool's end check, and the docs and docstrings
  with the new typing rules. No tests run, no probes: every suspicion was settled by reading (the code, `mypy.ini`'s
  `strict = True`, `uninstall.py`'s output lines, which tests pass `LEFTOVER_HOURS`). Settled as wrong: DECISIONS'
  "The user's own Designer, an agent working in it included, is never involved" read as untrue because a put-back
  rewrites the file that Designer reads (that rewrite is the decision itself, and nothing is saved or put back for the
  user's Designer: the sentence answers the user's question about their own session); `_lock() -> IO[str]` as too
  vague (no `Any` in it); `started: list[Any]` in `test_lifecycle_env.py` and the pool tests' `write(...) -> dict[str,
  Any]` as the branch's to narrow (they follow the older `_popen` and `pool()` signatures: ROADMAP item 98).
- **Not verified:** none.
- **Resolutions assessed:** all 19 (every fix is in the diff). They hold: SRV-126, SRV-127, SRV-128, SRV-129, SRV-131,
  TST-359, TST-360, TST-361, TST-363, TST-364, TST-365; each test a resolution names exists and, read, fails without
  its fix, but for what TST-368 lists. Questioned: SRV-125 by SRV-133, SRV-130 by SRV-135, SRV-132 and TST-362 by
  TST-366, INS-34 by INS-35, TST-356 by TST-369, TST-357 by TST-367, TST-358 by TST-368.
- **Findings:** 11, all Low: SRV-133 to SRV-136, INS-35, TST-366 to TST-371. Merged: SRV-133 (the product and docs
  reviewers), SRV-136 (all three), INS-35 (all three), TST-367 (the tests and docs reviewers), TST-369 (the same two).
- **Suggested order:** the user's file first (SRV-134, SRV-135); then what is said and tested (SRV-133, INS-35,
  TST-367, TST-368); the docs (TST-366, TST-369, TST-371); the types last (SRV-136, TST-370), TST-370's scope being the
  user's choice.
- **Simplifications:** test scaffolding repeated across files could go into `fake_defaults.py` (AGENTS.md, keep each
  file to its main logic): the user's log written at a time (`test_designer_preferences.py`'s `_the_users_designer_ran`,
  `test_selftest_pool.py`'s `_users_log`, inline in `test_uninstall.py::test_a_copy_dropped_as_the_users_says_so`); the
  non-blocking flock probe (`_held_elsewhere`, inline in `test_launch_saves_designers_preferences_before_its_designer_starts`);
  a copy saved, then the file changed (`_saved` with `_a_designer_changes`, `_saved_as_by_a_launch`,
  `_preferences_saved_and_changed`). `_saved(defaults, ...)` never uses `defaults`.
- **Checked and found fine:** both standalone files on Python 3.9; the lock's descriptor not inherited by Designer
  (`close_fds`); `_put_back`'s order (a Designer running, the user's log, the age, then the read) errs toward leaving
  the file; `saved()` lets the lock go when its body raises, and a put-back failing there keeps the old copy rather
  than saving over it; `Said.failed` right on every path; `told()` on every raise after a start that can carry a save's
  line; the `*/log.txt` glob matches the real layout (`16.0/log.txt`); no unit test reaches the user's file,
  `defaults`, log or Designers; the fake behaves as `defaults` where the code depends on it; the macOS gates; no older
  test weakened; the pool check's skip, FAIL and PASS each pinned; GUIDE.md's line; the live-check skill's additions;
  AGENTS.md's deploy note; ROADMAP items 67, 98 and 99 agree with AGENTS.md and the code (item 98's 150 or so `Any` in
  the product code: 151).
- **Chains:** the longest is generation 2, in seven chains, each followed once (SRV-125, SRV-130, SRV-132 with
  TST-362, INS-34, TST-356, TST-357, TST-358); a third generation of the docs and tests ones would narrow claims.

### 2026-11-13: the preferences-put-back branch against main, third review (the diff only)

- **How:** three reviewers read the diff, three commits, looking hardest at the second review's fixes: the product
  code (`designer_preferences.py`, the changes to `server_tools/lifecycle.py` and `uninstall.py`), the tests and the
  pool's end check, and the docs and docstrings. No tests run, no probes: every suspicion was settled by reading. Not
  raised (DECISIONS.md, Project rules, "Low-value findings about the tests and docs are not raised"): four docstrings
  that list fewer cases than the code has (`put_back`'s `ended`, `saved()`'s lines, `launch_designer`'s lines,
  `put_back_preferences`' copy kept), GUIDE.md's one line with no exceptions (SRV-132 kept it to one), uninstall's
  "(both kept while a Designer runs)", README not naming the `.new` file, ROADMAP item 67's "within 6 hours" (generation
  3 docs that change nothing anyone does); two stale test comments (`test_a_put_back_says_only_what_it_did`'s quoted
  detail, the `[export]` case's "the first delete failed"); `_file_holds_settings`' not-a-plist branch and
  `workers._any_designer`'s `NoListing` untested (`defaults` reads such a file as empty; a listing failing as a run
  starts); the pool's false FAIL when an outside Designer quits between the pool's read and the first launch, or when
  lifecycle's second Designer is left running (a race at the start, or a failure first).
- **Not verified:** none.
- **Resolutions assessed:** the second review's 11 (every fix is in the diff), and the first review's that the new
  findings follow. They hold: SRV-136, INS-35, TST-366, TST-368, TST-369; each test a resolution names exists and,
  read, fails without its fix. Questioned: SRV-127 by SRV-139, SRV-128 by SRV-137, SRV-133 by SRV-140, SRV-134 by
  TST-372, SRV-135 by SRV-138, TST-367 by TST-375, TST-370 by TST-373 and TST-374, TST-371 by TST-372 and TST-375.
- **Findings:** 8, all Low: SRV-137 to SRV-140, TST-372 to TST-375. Merged: SRV-140 (the product code and docs
  reviewers), TST-372 (the tests and docs reviewers), TST-373 (the same two).
- **Suggested order:** the user's file first (SRV-137, SRV-138, SRV-139); then what is said and tested (SRV-140,
  TST-372); the docs (TST-374, TST-375); TST-373 last, its line being the user's choice.
- **Simplifications:** `workers._any_designer` is `common.designer_alive()` with a listing that fails read as running;
  `_count` is written twice (`designer_preferences`, `workers`).
- **Checked and found fine:** `none_left()` at each call site (once per raise; never while a Designer of the call runs:
  `_force_end` true only once the process is gone, no process when `_started` fails, one still starting seen at the
  timeout; "could not be ended" keeps `told()`); the lock order (the port's launch lock, then the preferences lock)
  everywhere, `saved()` yielding once on every path and letting the lock go; `_start_designer`'s line never said twice;
  no exception out of a tool (`run_defaults`, `_put_back_or_say`, `_any_designer`, uninstall's `running`); SRV-134's
  copy kept on an `OSError`; `kept_copy()` agreeing with `saved()` and `_put_back` (it rightly ignores age: the run's
  last quit passes `ended=True`); `quit_designer`'s `ended` on every return of `_quit`; uninstall's Removed and Could
  not remove lines on every outcome; the three modules the standalone scripts share, on Python 3.9; no unit test
  reaching the user's file, `defaults`, log or Designers (the `defaults` fixture autouse, `fresh()` reloading only the
  self-test's modules, `REAL_RUN_DEFAULTS` run only on `/usr/bin/false` or a missing path); every new test's clean-up
  on failure; the macOS gates, nothing importing `fcntl` at a file's top; the end check's FAIL, SKIP and PASS, and its
  reference matching what the last quit restores in every main case; README's How-it-works, uninstall and
  troubleshooting rows; both tool docstrings against `_quit`, `none_left()` and `saved()`; DECISIONS.md's preferences
  and "Vague types" entries; GUIDE.md's line; the live-check skill's additions; ROADMAP item 99; no stale names
  (`refusing()`, `Said`, `failed`).
- **Chains:** the longest is generation 3, in three chains: SRV-125 → SRV-133 → SRV-140 and SRV-130 → SRV-135 →
  SRV-138 (the tools' code: entries at any generation), TST-357 → TST-367 → TST-375 (a docstring: a smaller claim).
  Five more at generation 2 (SRV-137, SRV-139, TST-372, TST-373, TST-374).

### 2026-11-13: the preferences-put-back branch against main, fourth review (the diff only)

- **How:** three reviewers read the diff, four commits, looking hardest at the third review's fixes: the product code
  (`designer_preferences.py`, the changes to `server_tools/lifecycle.py` and `uninstall.py`), the tests and the pool's
  end check, and the docs and docstrings (each stopped once on an API error and was resumed). No tests run. One probe,
  outside Designer: a scratch 20 MB APFS disk image (`hdiutil`, mounted hidden, then detached and deleted), filled
  until writes failed (ENOSPC): removing a file on it worked, writing the lock file's mark failed. Settled as wrong:
  SRV-137's mark missing because removing the copy and writing the lock file fail together (the probe: a full disk
  lets the removal through; SRV-137's causes, an immutable flag or the folder's permissions, leave the lock file
  writable); `_given_up` raising `UnicodeDecodeError` (only `_give_up` writes that file, an ASCII `repr`); `saved()`'s
  `except` dropping what `_dropped` says (the copy is given up, never put back, and the next call says it couldn't be
  removed: nothing anyone does changes); uninstall's "put back first unless ..." for a copy given up (it holds for
  every way a copy is given up but one, whose start already said its changes won't be put back). Not raised
  (DECISIONS.md, Project rules, "Low-value findings about the tests and docs are not raised"): `_put_back`'s "their
  copy was imported" branch untested, and the order test's `find` against its comment (generation 4, tests only, no
  claim to narrow); the comment at `lifecycle.py:811` naming fewer cases than `_NotStarted` has.
- **Not verified:** none.
- **Resolutions assessed:** the third review's 8 (every fix is in the diff). They hold: SRV-138, TST-372, TST-374,
  TST-375; each test a resolution names exists and, read, fails without its fix. Questioned: SRV-137 by SRV-142,
  SRV-139 by SRV-141, TST-376 and TST-377, SRV-140 by SRV-143, TST-373 by TST-378.
- **Findings:** 6: TST-376 (Low-medium); SRV-141 to SRV-143, TST-377, TST-378 (Low). Merged: SRV-141 (all three
  reviewers), SRV-143 (the product code and docs reviewers).
- **Suggested order:** TST-376 first (the unit suite fails while a Designer listens on the default port); then the
  tools' code: SRV-141, SRV-142, SRV-143; then the docs: TST-377, TST-378. SRV-141's fix (the record written before the
  lock goes, or `_appeared` asked only after a put-back) is a choice worth showing the user.
- **Simplifications:** none new.
- **Checked and found fine:** the mark's `repr(float)` of the copy's time (the product reviewer: the same text on
  Python 3.9.6 and 3.12.10; times now about 240 ns apart at the finest, so two copies don't collide); `_give_up`
  writing the lock file in place under the lock, the flock untouched; uninstall removing the lock only once the copy
  is gone; no copy of a running session given up (`_dropped` only once `running()` is False, or for a copy this call
  made); `fresh` and `again` on a failed start; `_NotStarted`'s lines before `none_left()`'s, a bare `raise` only when
  both are empty; `_appeared` raising nothing (`_NoListing` caught) and never off macOS; no import with no value to
  put back; `_quit`'s `ended` on every return; the three standalone modules on Python 3.9; no unmarked `Any` or vague
  container left in the functions the diff adds or changes; `FakeDefaults` and `_Processes` behaving as what they
  stand for where the code depends on it; every new test's clean-up on failure, no older test weakened; the pool's
  `preferences_before`, `check_the_preferences` and `_quit_to_keep`; README's uninstall, troubleshooting and
  How-it-works rows; GUIDE.md's line; the live-check skill; ROADMAP items 67, 98 and 99; DECISIONS.md's preferences
  and "Vague types" entries; `launch_designer`'s and `quit_designer`'s docstrings.
- **Chains:** the longest is generation 4: SRV-125 → SRV-133 → SRV-140 → SRV-143 (result lines: the tools' code). At
  generation 3: SRV-141 and SRV-142 (the tools' code), TST-376, TST-377 and TST-378 (tests and docs: no new check,
  smaller claims). SRV-139 drew three follow-ups.

### 2026-11-13: the preferences-put-back branch against main, fifth review (the diff only)

- **How:** three reviewers read the diff, five commits, looking hardest at the fourth review's fixes: the product code
  (`designer_preferences.py`, the changes to `server_tools/lifecycle.py` and `uninstall.py`), the tests and the pool's
  end check, and the docs and docstrings. No tests run, no probes: every suspicion was settled by reading. Settled as
  wrong: a launch that couldn't open the lock while another server's could, starting its Designer unrecorded beside
  that one's check (the lock file is the same for every server; running out of file descriptors in one server fails
  its Popen too, which opens `/dev/null`); a Designer this same call ended still listed when its check runs
  (`_force_end` is True only once `pgrep` no longer lists it); the lifecycle hand-over check's own unrecorded Designer
  refused in a pool (it runs inside `launch_lock.held(own='lifecycle')`, as does the check that moves the record aside).
  Not raised (DECISIONS.md, Project rules, "Low-value findings about the tests and docs are not raised"): `saved()`'s
  "removed when the start raises" not naming a `check` that raises, `lock_file()`'s docstring not saying "and
  recorded", uninstall's "one that isn't a plist of keys is removed" (generation 3 or later, docs that change nothing
  anyone does); the TST-376 test's `_listening_ports` replaced twice. Not raised as implausible: a lock failing at a
  launch but opening at its quit.
- **Not verified:** none.
- **Resolutions assessed:** the fourth review's 6 (every fix is in the diff). They hold: TST-376, SRV-142, SRV-143,
  TST-377, TST-378; each test a resolution names exists and, read, fails without its fix, and the tests reviewer found
  no mutation of the new code that passes them all. Questioned: SRV-141 by SRV-144; and, older, SRV-127 and SRV-129 by
  SRV-145.
- **Findings:** 3, all Low: SRV-144, SRV-145, TST-379. Merged: SRV-144 (the product code and docs reviewers).
- **Suggested order:** SRV-144 (the tools' code: a wrong refusal), SRV-145 (two result lines), TST-379 (the tests).
- **Simplifications:** none new.
- **Checked and found fine:** what `_appeared` can list once `start()` has looked (`_running_on` and `_users_next_to`
  cover both of `_sorted_out`'s lists, so only a Designer new to `pgrep` or one that left `elsewhere`; an
  `_agent_record` that misreads a start refuses the same way at `start()`'s look); the lock order (the port's launch
  lock, then the preferences lock; under the preferences lock only `_forget_started`'s non-blocking port lock), the
  time added under it (one `ps`, a small file written); `check` raising in `__enter__`, the copy made fresh dropped and
  the lock let go before `none_left()` takes it again, after a put-back, a save again or a failed save; every removal
  of the copy through `_dropped`; the new `elif` reached only through the read-back, `changed` set for the `except`;
  `_dropped`'s and `_not_saved`'s new wordings in `quit_designer`'s result, `launch_designer`'s line and uninstall's
  lines (but for SRV-145); the three standalone modules on Python 3.9 (the `check` default a lambda, the annotations
  strings); no unmarked `Any` or vague container in the functions the diff adds or changes; no exception out of a tool
  on a realistic path; no older unit test or live check broken by the look on every launch; every new test's clean-up
  on failure; no stale claim that `_appeared` runs only when something is said; README's rows, GUIDE.md's line, both
  skills, ROADMAP items 67, 98 and 99, DECISIONS.md's new sentences (names and paths current).
- **Chains:** the longest is generation 4: SRV-125 → SRV-133 → SRV-140 → SRV-143 (resolved) and SRV-127 → SRV-139 →
  SRV-141 → SRV-144 (the tools' code: a wrong refusal). SRV-145 is generation 2, TST-379 generation 1.

### 2026-11-13: the preferences-put-back branch against main, sixth review (the diff only)

- **How:** three reviewers read the diff, six commits, looking hardest at the fifth review's fixes and AGENTS.md's new
  "Writing docs and comments" (under which a sentence is reported only when it misleads, never for its style alone):
  the product code, the tests and the pool's end check, and the docs and docstrings. No tests run, no probes: every
  suspicion was settled by reading. Not raised (DECISIONS.md, Project rules, "Low-value findings about the tests and docs
  are not raised"): the module docstring's "the lock held until the process is started (and recorded: launch_designer)"
  without "or ended", and "a Designer started meanwhile" alone where it says what the look is for (generation 3 or
  later, docs that change nothing anyone does); `STARTED` pinned at only one of its two raises; the crash-settings test
  that no longer sees a launch without a home ask for the plugin folders (a guard it had by accident; nothing changes
  without a home, off macOS only); the project-file guard reading only `server`'s name (`patch_server` binds every
  module's). Not raised, from main: the `kill -9` advice after `_force_end`'s listing fails.
- **Not verified:** none.
- **Resolutions assessed:** the fifth review's 3 (every fix is in the diff). They hold: SRV-144's code and test,
  TST-379; each test a resolution names exists and, read, fails without its fix; the tests reviewer found no mutation
  of c56fb50's code that passes them all. Questioned: SRV-144's change to DECISIONS.md by TST-380; SRV-145 by INS-36.
- **Findings:** 4, all Low: INS-36, TST-380, TST-381, TST-382.
- **Suggested order:** TST-380 first (the user's answer settles it); then INS-36 (the uninstaller's line), TST-381 (the
  writing rule's examples), TST-382 (a type).
- **Simplifications:** none new.
- **Checked and found fine:** `_force_end` under both locks (its `_forget_started` takes the port's lock without
  waiting and, held by this same call, skips; nothing under the preferences lock waits for a port's lock); who waits
  the up to 10 s on that path, and that none of their results change (other ports' launches, whose `wait_s` starts
  after `start()`; quits, `none_left()`, uninstall); every path out of `_start_designer` (the folder refused, the
  start failing, `check` refusing, the record failing with the end working, failing or not seen), the copy and
  `start()`'s line in each; the new wordings in every sentence they reach (`launch_designer`'s line and errors,
  `quit_designer`'s result, uninstall's lines, but for INS-36); the three standalone modules on Python 3.9; no
  exception out of a tool; the lock order everywhere; the reaper thread before the record, as on main; DECISIONS.md's
  names and paths; the new AGENTS.md section's claims against the skills and AGENTS.md elsewhere (but for TST-381);
  every new test's clean-up, the tests reaching neither the user's files nor the bridge port; `AGENTS_SECTIONS`.
- **Chains:** the longest is generation 5: SRV-127 → SRV-139 → SRV-141 → SRV-144 → TST-380 (DECISIONS.md's sentence,
  which the user settles). INS-36 is generation 3 (the uninstaller's line: an entry at any generation); TST-381 and
  TST-382 generation 1.

### 2026-11-13: the preferences-put-back branch against main, seventh review (the diff only)

- **How:** three reviewers read the diff, eight commits, looking hardest at the two since the sixth review (the
  uninstaller's line, DECISIONS.md's entry completed with the user's agreement, the writing rule's examples, conftest's
  type; TST-383's wait for the checker in the 3D checks): the product code, the tests and the live self-test code, and
  the docs. The lead, assessing TST-383, read the two checks that read a retaken shot's text (TST-384), and gave it to
  the reviewers as found. No tests run, no probes: every suspicion was settled by reading. Not raised: `plan()` asking
  `folders_in_use()` twice (a race whose outcome is safe, the put-back asking again; the folders' removal is main's);
  removing the lock and `.new` without holding the lock (INS-34 kept it as a race); a retake that fails printing "didn't
  show" (the check prints the error); `_preferences_items`' docstring not naming a listing that fails (the code beside
  it says it); the designer fact `unchanged < 2` and the plain-graph check's single shot, blind to a late material
  before this change too; the set-up check's `changed < 2` after retakes (a material arriving in steps, never seen).
- **Not verified:** none.
- **Resolutions assessed:** the sixth review's 4 and TST-383 (every fix is in the diff). They hold: INS-36, TST-380,
  TST-381, TST-382; each test a resolution names exists and, read, fails without its fix. Questioned: TST-383 by
  TST-384, TST-385, TST-386 and TST-387.
- **Findings:** 4: TST-384 (Low-medium); TST-385, TST-386, TST-387 (Low). TST-384 found by the lead.
- **Suggested order:** TST-384 (a check failing in the case the wait is for), TST-386 (a pause no test pins, a check
  waiting for a checker it doesn't set), TST-385 (the docs), TST-387 (types).
- **Simplifications:** none new.
- **Checked and found fine:** INS-36 on every path of `put_back_preferences` (the copy kept with nothing said only after
  the first look found a Designer or a failed listing; `STARTED` when a put-back stops partway; `seen` empty only in a
  race with a launch), the uninstaller's other lines agreeing with it, the three standalone modules on Python 3.9
  (compiled with the system's 3.9.6); DECISIONS.md's entry against the code ("up to about 10 s": two signals, five
  looks a second apart each); the writing rule's examples now keeping the whole claim; `with_checker` against its
  docstring and its four unit tests (the retakes pass only `panel` and `max_size`, so no zoom or pan is applied twice);
  the 12 call sites, each after its check's skip, and the shots left plain; the summary rule's exemption, which still
  reports a helper nothing awaits and a check that never runs; ROADMAP item 83's sentence; REVIEW.md's counts.
- **Chains:** the longest still growing is generation 2 (TST-383 → TST-384 to TST-387, the 3D checks' wait). The
  preferences chains are closed at generation 5 (SRV-127 → SRV-139 → SRV-141 → SRV-144 → TST-380).

### 2026-11-13: the preferences-put-back branch against main, eighth review (the diff only)

- **How:** two reviewers read the last commit's changes, the tests and the live self-test code, and the docs (the
  product code unchanged since the seventh review, which found nothing in it). One probe, in a Designer an agent
  started: the 3D view with Designer's window minimized (SRV-146). The docs reviewer's suspicion that "a mesh without
  the checker" doesn't explain the failed pan's 0.000 was settled by the lead's earlier measure (a plane with the
  default material is found: columns 94 to 247 from the Top at zoom -4) and by the probe. Not raised (DECISIONS.md,
  Project rules, low-value findings): a failed retake's guard and the image's place in the result untested (generation
  3, tests only, no claim to narrow); site 1 passing within the wait if Designer itself put the outputs on late while
  `graph=` did nothing (two faults at once); a print's comparison untested; `set_3d_view`'s docstring listing the
  graph before the mesh (main's code).
- **Not verified:** what left the 3D view's shots stale in the full run (TST-388). Tried: full CPU load (12 busy
  processes on 10 cores), another Designer's window over the view, and the window minimized (that one does: SRV-146,
  but nothing minimizes a worker's window). It needs the pool's own conditions, a race that hasn't reproduced on demand;
  a full run with the 3D shots' images kept would show what they held.
- **Resolutions assessed:** the seventh review's 4. They hold as tests: TST-384, TST-386, TST-387 (each test exists and,
  read, fails without its fix). Questioned: TST-385 and, behind it, TST-383 by TST-388: the cause they state isn't
  established, and the wait may not cover the one measured since.
- **Findings:** 2: SRV-146 (Medium), TST-388 (Low-medium).
- **Suggested order:** SRV-146 first (the tool's shot, for every agent); then TST-388, whose fix leans on it.
- **Simplifications:** none new.
- **Checked and found fine:** `with_checker` against its docstring and tests (the text kept only after a retake and only
  on an image; a fresh `CallToolResult` each call, neither frozen nor validated on assignment; the image still first);
  the view check's own graph changing nothing a later check sees; the 12 sites; the summary rule; GUIDE.md's core under
  its 20,000 characters; REVIEW.md's counts.
- **Chains:** TST-383 → TST-385 → TST-388 is at generation 3 (TST-388's fix: smaller claims, with SRV-146's behaviour
  behind them). SRV-146 is generation 1.

### 2026-11-13: the preferences-put-back branch against main, ninth review (the diff only)

- **How:** three reviewers read the diff, looking hardest at the last commit (SRV-146's fix: `shot3d.py`, the server's
  call, the window checks; TST-388's narrowed docs): the product code, the tests and the live self-test code, and the
  docs. The lead settled what reading couldn't in three probes, one at a time, in one Designer an agent started; the
  user's preferences were exported before and were identical after. They measured `getMainWindow()` against the
  top-level window (native before `winId()`, minimized by macOS, restored by Qt, its geometry); the first 3D shot of a
  fresh Designer, with a mesh switch; the mesh read from the Scene menu, and the same mesh twice; a plain shot after a
  pan made with the window off screen, in the four ways; another window covering Designer's during a shot; how long
  macOS takes to say a window sent back is covered, idle and under 12 busy processes.
- **Not verified:** a window on another desktop (Space), behind a full-screen app, or with the screen locked. macOS may
  report such a window occluded. `shoot_3d` then takes it for covered ("brought in front ... as its 3D view isn't drawn
  while covered"), and either `orderFrontRegardless` brings nothing on screen (refused after 3 s, then "sent back behind
  the windows that covered it", untrue), or it switches the user's desktop. Tried: Apple's documentation
  (`occlusionState`'s says nothing of Spaces; `isOnActiveSpace` tells the case apart). Limitation: putting a window on
  another desktop, or an app full screen, switches the user's screen, and locking it stops their work; no public API
  moves a window to another Space. What would check it: the user moving an agent's Designer to another desktop, then a
  3D shot, watching the desktop shown, the result and `isActive`. The product and docs reviewers.
- **Resolutions assessed:** SRV-146 and TST-388 (the eighth review's, both in the diff). They hold as fixes: the tests
  SRV-146 names exist (8 of `_on_screen`, 15 of `shoot_3d`) and, read, fail without the fix; TST-388's sentences say
  what was seen. Questioned: SRV-146 by HLP-124 to HLP-129, SRV-147 and TST-389 to TST-394, its Cause's Qt fact by
  TST-391 (a note under it).
- **Findings:** 13: HLP-124, TST-389, TST-390, TST-391 (Low-medium); HLP-125, HLP-126, HLP-127, HLP-128, HLP-129,
  SRV-147, TST-392, TST-393, TST-394 (Low). TST-389 found by the lead's probe.
- **Dropped:** `shoot_3d`'s render before the set-up failing on a view with no render (not reproduced: the first 3D shot
  of a fresh Designer, the mesh switched, rendered); `_mesh_shown` misreading the mesh (measured right: Rounded cube,
  Sphere, Plane; the same mesh twice said nothing); the wait for the view to draw once on screen too short (not
  reproduced: the plain shot showed a pan made off screen in all four ways, and matched an on-screen render 2 s later
  where that could be read); the covered state read 0.5 s after `orderBack:` too early (0.04 to 0.07 s, idle and
  loaded); `winId()` making the page native (it was before: 7 native widgets before and after).
- **Not raised:** STALE said after a set-up that changes nothing in view (an orbit at the pole, a zoom at its limit):
  the line says "may", and the user asked for the flag whatever the cause; README.md's self-test sentence not saying the
  windows come in front of the user's (not false: DECISIONS.md, Project rules, low-value findings); `with_checker`'s "as
  a defence", and TST-388's Fix line expecting the checks to report the tool's stale line (generation 4, docs, changing
  nothing anyone does); the `NOTES` comment's order beside the put-back line's; check 1's snippet leaving the window off
  screen when its pan fails (a note under SRV-146); an empty temp folder left if `PAN_AS_IT_IS`'s shot raises.
- **Suggested order:** HLP-124 (a stale render said to be fresh); HLP-127 and SRV-147 (refusals); HLP-125 and HLP-126
  (the put-back); HLP-128 (STALE's advice); TST-389 and TST-390 (false failures in the final check); TST-391; TST-392,
  TST-393, TST-394; HLP-129 (types).
- **Simplifications:** `_on_screen`'s Qt-minimized branch handles the page's own state, which only the self-test makes
  (TST-391): reading the top-level's state may serve both.
- **Checked and found fine:** the ctypes calls (result types, the nil argument as sender, receivers never NULL);
  `_on_screen`'s paths (minimized by both, hidden and minimized, a failure in the wait, the set-up or the render going
  through the `finally`); QImage's `==` comparing pixels, and the copies outliving the clipboard's put-back; no caller
  of `save_screenshot('3d')` left; the call string's quoting, an all-zero orbit or pan turned into None, the timeouts;
  the server returning the window's lines beside the image and in errors; `_set_up_checked`'s extraction; the 23 unit
  tests' counts and what each fails on; the three checks' skips, `run()` awaiting them, their snippets dedented; check
  2's clean-up when a tool call fails; GUIDE.md's line telling agents to tell the user; ROADMAP items 90 and 91;
  REVIEW.md's counts.
- **Chains:** the longest still growing is generation 2 (SRV-146 → 13 findings). TST-383 → TST-385 → TST-388 is closed
  at generation 3 (its generation-4 suspicions not raised).

### 2026-11-14: the preferences-put-back branch against main, tenth review (the diff only)

- **How:** three reviewers read the diff, looking hardest at the last commit (the ninth review's fixes: `_Screen`'s
  looks and put-back, `mac_window.py`, `_3d_set_up`, the four new window checks): the product code, the tests and the
  live self-test code, and the docs. The lead settled what reading couldn't in four probes, one at a time, in one
  Designer an agent started (`alone.run` on `editor_panels_and_fit`'s preparation). The user's preferences were
  exported before and were identical after. The probes measured:
  - each set-up step (`graph=`, `mesh=`, `view=`, `pan=`, `zoom=`, `tiling=`) run with Designer not the active app:
    none made it active, and the user's app stayed in front;
  - `orderWindow:relativeTo:` given a window on screen puts Designer's window right behind it; given that window
    minimized, or closed, it puts it behind every window (HLP-130);
  - Designer's window covered whole by an always-on-top window (layer 8): `above()` found none, the shot was taken
    and its render fresh (a pan made under the cover showed, identical to a render on screen after), and Designer's
    window, the front-most normal window before, was behind every window 0.5 s after (HLP-130).

  Settled as wrong: a set-up step making Designer the active app, which the put-back would blame on the user (the
  product and docs reviewers; the first probe); the shot refused under an always-on-top window (the product reviewer;
  it was taken, and drawn).
- **Not verified:** a window on another desktop (Space), behind a full-screen app, or with the screen locked: the
  ninth review's entry, unchanged. And Designer in Stage Manager's side strip (the product reviewer): macOS may report
  its window covered, and `orderFrontRegardless` may then switch the stage the user sees, or show nothing. Limitation:
  turning Stage Manager on rearranges the user's whole screen, and the setting is theirs. What would check it: the user
  turning it on, an agent's Designer in a side strip, then a 3D shot, watching the stage shown, the result's lines and
  `isActive`.
- **Resolutions assessed:** the ninth review's 14 (every fix is in the diff). They hold as fixes: HLP-125, HLP-128,
  SRV-147, TST-389, TST-390, TST-392, TST-393, TST-394; each test a resolution names exists and, read, fails without
  its fix. Questioned: HLP-124 by HLP-131 and TST-396; HLP-126 by HLP-130 and HLP-131; HLP-127, TST-391 and TST-395 by
  TST-398; HLP-129 by HLP-132; SRV-146's tests by TST-397.
- **Findings:** 6, all Low: HLP-130, HLP-131, HLP-132, TST-396, TST-397, TST-398. Merged: HLP-131 (all three
  reviewers and the lead), HLP-132 (the product and tests reviewers), TST-398 (three of the docs reviewer's).
- **Not raised:**
  - `_3d_set_up`'s checks guarded through a fake and the live orbit refusal only (a check moved into `run()` passes
    every test): generation 3, tests only. The test comment states the code's design, which holds, and the rule allows
    no stronger test.
  - `DRAW_WAIT = 0` passing the unit tests: generation 3, tests only; the fix would be a new check.
  - `BROUGHT['covered']`'s "again" line for a window not brought in front before, and, under an always-on-top window,
    "as another window covered it during the shot" for the window that covered it throughout (HLP-130's case).
  - `read()`'s "about 0.1 s" beside `shot3d.py`'s 0.04 to 0.07 s: they measure different events.
  - The covered-during-the-shot check's docstring saying "without taking focus" though it doesn't read `active`
    (check 2 guards focus); the Scene menu's fact read only after the tool switched the mesh (generation 3, docs).
  - The fakes kept in `test_shot3d.py`: its assertions read their records.
  - Check 1's on-screen pans racing another worker's window opening in those 1 to 2 s: TST-390's case, the window put
    in front first; never seen.
  - `CFNumberGetValue`'s type argument declared `c_int` where the header has `CFIndex`: libffi widens it, and the call
    works.
- **Seen outside the diff:**
  - The agent's Designer, just launched by `alone.run`, was the active app when the first probe began, so it had the
    user's keyboard. The lead gave it back (Designer hidden, then shown without activation). The next run, on the same
    Designer, began with it inactive. The launch is `main`'s (`_started`'s `Popen` is unchanged). TST-392's scenario
    says a Designer the self-test starts wasn't active when measured then.
  - `alone.close()`'s quit was forced after 12 s. Designer's log ended in the quit helper's `close_windows` raising
    "Internal C++ object (PySide6.QtWidgets.QMenu) already deleted" (`designer_helpers/quit.py`, unchanged from
    `main`). No crash dump was left.

  Neither is in the diff; whether to follow them up is the user's choice.
- **Suggested order:** HLP-130 and HLP-131 together (the put-back's window, in one place); TST-397 (the guard behind
  the decision on a minimized window); TST-396 (a false failure in the final check); TST-398; HLP-132.
- **Simplifications:** HLP-130's fix leaves `orderBack:` with no case: `send_back()` can go.
- **Checked and found fine:** `run()`'s scoping (every name it assigns is its own, set before it is read; the outer
  ones only read or appended to); the split's order of checks and steps and its abort handler, as before it; the pan's
  drags computed from the viewport's size before the window comes up; the ctypes constants, result types and
  ownership (the Copy array and the two Create strings released, the Get values not, a NULL array guarded); each path
  printing one "brought" line and at most one put-back line; the server's '' mapping and timeouts; `_3d_dock` and
  `_mesh_shown` before the window changes; the clipboard's text put back after every render; `_on_screen`'s `finally`
  on every failure and abort; `_COVERED_DURING_PAN`'s `_drag` rebinding (the plugin gives each call a fresh scope;
  `run()` looks `_drag` up in the globals) and `AS_IT_IS`; the four new checks failing on their defect, their
  `try`/`finally` around `clear()`, `run()` awaiting them; check 2's order assertion and `focus()`; the unit tests'
  look before each render, `_behind` read before `show()`, `active` against `_was_active` both ways; no older test
  weakened; the strings of code; the `BROUGHT` and put-back lines against `_bring` and `put_back`; STALE, the tool's
  docstring and GUIDE.md's Look bullet; DECISIONS.md's entry against `put_back`; README.md's Security bullet (but for
  HLP-130 and HLP-131); ROADMAP items 83, 90 and 91; no stale names; REVIEW.md's counts.
- **Chains:** the longest still growing is generation 3: SRV-146 → HLP-124 and HLP-126 → HLP-130, HLP-131 and TST-396;
  → HLP-127, TST-391 → TST-398; → HLP-129 → HLP-132. HLP-130 and HLP-131 are the tools' code (entries at any
  generation); TST-396 and TST-398 tests and docs (a corrected measurement, smaller claims). TST-397 is generation 2.

### 2026-11-14: the invisible-3d-shot branch against main (the diff only)

- **How:** two reviewers read the diff: the helpers' code (`shot3d.py`, `mac_window.py`), and the tests and docs. The
  lead settled what reading couldn't in one probe, in one Designer an agent started (`alone.run` on
  `editor_panels_and_fit`'s preparation); the user's preferences were exported before and were identical after. It
  measured:
  - Designer's windows (NSApp's): four, three of Qt's, all opaque (`isOpaque`), the main window the only one visible,
    and AppKit's text-input window (`TUINSWindow`), not opaque, not visible;
  - a window of Designer's own fully under the main window: covered with the main window opaque, and still covered
    with it transparent, click-through or not (HLP-133);
  - `shoot_3d(graph=...)` with the window minimized: a popup-level window of Designer's (`QNSPanel`, level 101) on
    screen at opacity 1 on three of a 20 ms timer's ticks, Designer not made the active app (HLP-134);
  - a window minimized, then Designer hidden, then a shot: minimized and hidden after, still minimized once shown
    again;
  - `orderFrontRegardless` then `miniaturize:` at once on a minimized window: minimized, off screen, 3 s later.

  Settled as wrong:
  - a window both minimized and hidden left un-minimized by the `hide:` right after the `miniaturize:` (the product
    reviewer; measured minimized);
  - `miniaturize:` ignored while the window is still coming out of the Dock, leaving it up and saying "minimized
    again" (the product reviewer; measured minimized);
  - a set-up step making Designer the active app, which the put-back would blame on the user (the product reviewer):
    not with `graph=` (above), nor any step in the tenth review's probe of the preferences-put-back branch;
  - `setIgnoresMouseEvents:` NO, set explicitly by the restore, making a window take clicks on its transparent pixels
    (the product reviewer): Designer's windows are opaque; only AppKit's text-input window isn't, and only a shot of a
    hidden Designer sets it;
  - an abort landing in `contextlib`'s own frames leaving the windows transparent (the product reviewer): the plugin's
    `_run` catches the abort and frees its traceback as its `except` ends, which closes the generator; its `finally`
    and handler then put the window back and make it opaque, within the same job. Only the put-back's lines are lost
    to the reply.
- **Not verified:** the Dock during a shot of a minimized window (the product reviewer): `orderFrontRegardless`
  takes the window's tile out of the Dock's minimized section and `miniaturize:` adds it back, and the thumbnail may be
  taken while the window is transparent, so blank. Tried: the user watched one such shot and saw nothing but didn't know
  where in the Dock to look; the window they restored from the Dock afterwards was opaque and not click-through.
  Limitation: checking needs the user's eyes, or a capture of their screen, which isn't taken without their consent.
  What would check it: the user watching the right end of the Dock during a shot of a minimized window. Also, as in
  the earlier reviews: Spaces, a full-screen app, a locked screen, Stage Manager.
- **Resolutions assessed:** those whose fixes this diff changes, `_Screen`'s look and put-back: HLP-124, HLP-125,
  HLP-126, HLP-130, HLP-131, TST-393, TST-397, TST-399. They hold: `again()` before each render, the active check
  before any put-back, the first window found kept while on screen, each named test still there and failing without
  its fix. HLP-125's **Also covered** ("a minimized window stays up anyway") no longer holds, since a minimized window
  is now minimized again: the code still leaves it up when the user made Designer the active app, unguarded
  (TST-402).
- **Findings:** 7: Low-medium HLP-133, HLP-134, TST-401; Low TST-402, TST-403, TST-404, HLP-135. Merged: HLP-135 (both
  reviewers), TST-402 (the tests reviewer's two).
- **Not raised:**
  - README's and the tool docstring's "puts it back as it was" leaving out the window left in front once its cover is
    gone (HLP-130's case): the same wording as `main`'s, which the tenth review checked, and the result's lines say it.
  - An abort landing on the put-back leaving the window up, now opaque: ROADMAP item 91.
  - `_wait_off_screen` giving up after 3 s without a line: the case behind it was measured not to happen (above).
  - A window minimized and hidden at once named only "minimized" on the way in: as on `main`.
- **Suggested order:** HLP-133 and HLP-134 first, since they decide whether "the user sees nothing" holds: each fix
  needs a measurement, and HLP-133's may need the user's choice; then TST-401, TST-402, TST-404, TST-403, HLP-135.
- **Checked and found fine:** the objc_msgSend prototypes (`alphaValue` and `ignoresMouseEvents` read, their setters'
  double and BOOL arguments, `windows`/`count`/`objectAtIndex:`, `retain`/`release`, `miniaturize:`); NSApp's windows
  listed and held with no event processed in between, the main window's pointer the same key as its entry; every hold
  let go of once, never twice, an abort at worst leaking one; an abort in the helpers' own frames (the body, `_bring`,
  `_fade`, `put_back`'s body and `finally`, the handler) ending with every recorded window opaque; GeneratorExit
  caught and raised again; the state combinations (covered then hidden or minimized during the shot, Qt and macOS
  minimized at once, a Qt-minimized page also covered, Designer made active in each state); HLP-127's refusals and
  `_mesh_shown` before the window changes; drags and the wheel sent as Qt events, which click-through doesn't affect;
  every new path returning early off macOS; types (`_faded`'s dict typed, no unmarked `Any`); the new live check's
  `finally: clear()`, its `_3d_render` rebinding through the shared namespace, and its failing before the change;
  `AFTER['minimized']` and the opacity assertion of the tool's shot check; the click-through check's normal cover and
  its own `finally`; the unit tests of `_on_screen`, each failing without its behaviour, the abort parameters all
  landing; no strings of code joined with "\n"; DECISIONS.md's entry against `put_back`; GUIDE.md's Look bullet.
- **Chains:** all seven are generation 1: the branch's new code. The longest still growing from the last branch stays
  generation 3 (SRV-146 → HLP-124/HLP-126 → HLP-130, HLP-131), unchanged.

### 2026-11-14: the invisible-3d-shot branch against main, second review (the diff only)

- **How:** two reviewers read the diff. One took the helpers' code and the docs that describe it (`shot3d.py`,
  `mac_window.py`, `view3d.py`, `views.py`, README, GUIDE.md, DECISIONS.md), the other the tests. No tests were run.
  The lead settled what reading couldn't in probes run one at a time in one Designer an agent started (`alone.run` on
  `editor_panels_and_fit`'s preparation). The user's preferences were exported before and were identical after. It
  measured:
  - the Explorer's menu the fade made transparent, in two shots with `graph=`: destroyed by the time each shot returned
    (`destroyed` fired, `shiboken6.isValid` False), so no later menu opens transparent, the user's own included;
  - NSWindow's `windowNumberAtPoint` at the menu's middle while it was open, the point inside its frame as read back:
    never the menu's number, at opacity 0, at 0.02 with clicks explicitly taken, and at 1. So the call can't tell
    whether a click there would reach the menu (**Not verified**);
  - the menu made click-through too as it was made transparent, by `setIgnoresMouseEvents:` YES on its NSWindow or by
    Qt's `WindowTransparentForInput` on its QWindow: the pick still worked, and the shot came back.

  Settled as wrong:
  - the transparent menu reused later, so the user's right-clicks in the Explorer would open an invisible menu (the
    helpers reviewer): measured destroyed, above;
  - a second popup showing at full opacity, since only the first is made transparent (the helpers reviewer): the one
    known, the channel menu of a graph with one output, is refused before the menu opens (`view3d.py`'s docstring);
  - the lines for a page Qt minimized misreporting it (the helpers reviewer): only a script minimizes the page through
    Qt. Alone, its line is as on `main`. Minimized by macOS too, each line is true of its layer: the page stays
    restored, and the window is minimized again.
- **Not verified:**
  - Whether the Explorer's menu, transparent but not click-through, takes a click the user makes at its place during
    the quarter second it is open (the helpers reviewer). README says the user's clicks go to the window under
    Designer's. Tried: `windowNumberAtPoint` (above), which never reported the menu, even opaque. Limitation: only a
    real click settles it, and none is made on the user's screen without their consent. What would check it: with
    their consent, a click posted at the menu's middle during a shot (CGEventPost) while they leave the mouse alone.
    Making the menu click-through as it is made transparent was measured to keep the pick working.
  - Whether the menu's last milliseconds at full opacity show on screen (the tests reviewer): 0, 9 and 0 ms measured,
    and the check allows 20 ms. The watch reads the window server's list, not what was drawn. What would check it: the
    user's eyes, or a capture of their screen at 120 fps, with their consent.
  - As in the first review: the Dock during a shot of a minimized window; Spaces, a full-screen app, a locked screen,
    Stage Manager.
- **Resolutions assessed:** the seven of the first review, whose fixes are in this diff. Each fix addresses its cause,
  and each named test exists and fails without it. Questioned:
  - HLP-133: its README sentence gives the shot a duration no check measures (TST-408);
  - HLP-134: its live check passes with a watch that sees none of Designer's windows (TST-405), and its unit tests
    don't see the fade's timing or its looking again (TST-406).

  TST-401 to TST-404 and HLP-135 hold.
- **Findings:** 6, all Low: HLP-136, HLP-137, TST-405, TST-406, TST-407, TST-408.
- **Not raised:**
  - An abort landing after `minimize()` or `hide()` in `put_back`, whose `finally` then makes the window opaque before
    it is off screen, which `_on_screen`'s "leaves the window on screen" doesn't cover (the helpers reviewer): aborts
    skipping the put-back's steps are ROADMAP item 91.
  - `_PUT` recording a look before holding the window, `_UNDER`'s window not registered for `clear()`, and the facts
    loop with no `finally` (the tests reviewer): they show only after a failure, in an agent's Designer.
- **Suggested order:** HLP-136 first, as it changes what the user gets when they switch to Designer; then TST-407,
  TST-405, TST-406, TST-408, HLP-137.
- **Checked and found fine:**
  - the fade timer: it skips `before` as `pick` does; its first tick runs in the menu's nested loop, after the menu
    opened; its 0 ms restart runs only while no new popup is open, bounded by `sendEvent`; all three timers are
    parented and stopped, an abort as the third starts included; the opacity doesn't change the pick, which triggers
    the action from code;
  - `_bring`'s fade before `unhide` and `show` in each case; `put_back`'s early returns inside its `try`; the handler's
    `unfade`, then `opaque_first`; the holds balanced; the objc prototypes;
  - `popups.py`: its ctypes prototypes against the C signatures, the three keys present in every entry, the list and
    keys released, the layer and alpha filters, the thread stopped and joined on an exception too, `shown_ms`
    conservative;
  - every new check clearing the window state in a `finally`; `SHOWN` and `AGAIN` against `BROUGHT`; no strings of
    code joined with "\n"; no unmarked `Any` in the tests, nor in the functions of `shot3d.py` and `mac_window.py`
    the diff changes.
- **Chains:** HLP-133 → TST-408 and HLP-134 → TST-405, TST-406 reach generation 2. The other three are generation 1.
  The longest from the last branch stays generation 3, unchanged.

### 2026-11-14: the invisible-3d-shot branch against main, third review (the diff only)

- **How:** two reviewers read the diff. One took the helpers' code and the docs that describe it, the other the
  tests. No tests were run and no probe was needed: reading settled every suspicion.

  Settled as wrong or dropped:
  - the popup watch's `listed` count seeing Designer's main window, not its popups, so a later macOS listing popups
    below layer 100 still passes (the tests reviewer, questioning TST-405): generation 3, about a test alone, and no
    sentence claims the check sees that. `popups.py`'s docstring claims only that a watch seeing none of Designer's
    windows is caught, which it is.
- **Not verified:** as in the earlier reviews: the Dock during a shot of a minimized window; whether the menu's last
  milliseconds at full opacity show; Spaces, a full-screen app, a locked screen, Stage Manager. Also whether a click
  passes through the click-through menu: only its `ignoresMouseEvents` was read, and a click on the user's screen
  isn't made without their consent.
- **Resolutions assessed:** the six of the second review, whose fixes are in this diff. Each fix addresses its cause,
  and each named test exists and fails without it. Questioned:
  - HLP-136: a user already in Designer as the shot began, who leaves and comes back, still sees no window (HLP-138);
    its live check can't tell `between` before a set-up step from `between` before the render, and no test sees its
    guard (TST-409); the transparency check now fails if Designer becomes the active app during a shot (TST-410); the
    tool's docstring and two comments say more than the code (HLP-140);
  - TST-403: its hidden case counts Designer's windows through the code's own `windows(True)` (TST-411);
  - HLP-133: its fact check has no reading of the window under it uncovered (TST-412).

  HLP-137, TST-405 to TST-408 hold.
- **Findings:** 8, all Low: HLP-138, HLP-139, HLP-140, TST-409 to TST-413.
- **Not raised:**
  - DECISIONS.md's "If the user makes Designer the active app during the shot, it is left on screen": the code leaves
    it up only if Designer is still the active app as the shot ends, as on `main` (HLP-125). Its wording takes the
    user (the helpers reviewer).
  - `fade` not filtering to a QMenu as `pick` does: no other popup opens first (the helpers reviewer).
- **Suggested order:** HLP-138 and HLP-139 first, as they change what the user sees; then TST-410, which the final
  check could hit; then TST-409, TST-411, TST-412, HLP-140, TST-413.
- **Checked and found fine:**
  - `between()` in each state: minimized, covered, hidden, a page Qt minimized (nothing made transparent, so nothing
    done); run before `_bring` in `again()`, so a window isn't brought back opaque while others are still
    transparent; the user switching to Designer then away, the window put back as found; the user hiding Designer
    while in it, which makes it not the active app; hidden and taken up at once unreachable; the first `_bring`'s
    lines without "transparent" reachable only if Designer became the active app within microseconds of the shot's
    start;
  - aborts in `between` or `unfade` partway, and in `begin` before its line: `run`'s handler, then `put_back`'s
    `finally`, end every hold once;
  - `begin` running `between` before each of the seven steps; `set_3d_view` passing None, unchanged;
  - the menu made click-through only once it isn't `before`, only during `sendEvent`'s loop, destroyed after each
    shot (measured in the second review), the pick triggering its action from code; on Windows only transparent;
  - `views.py` collecting every "Designer's window: " line, the new one included;
  - the snippets' rebindings (`_MacWindow.active`, `_3d_set_up`, `_MenuPick.pick`) living only in their call's
    namespace, `state()` reading `isActive` directly;
  - the popup watch's unit tests (the fake writing through `byref`, the second window's popup caught, the list
    released), `Timer.starts`, the `Shot` fake's `given`, TST-407's parametrization, the clean-up of every new check
    in a `finally`; no older test weakened; no strings of code joined with "\n"; no unmarked `Any` in the helpers'
    functions the diff changes.
- **Chains:** HLP-136 → HLP-138, TST-409, TST-410, HLP-140; TST-403 → TST-411; HLP-133 → TST-412, all
  generation 2. HLP-139 and TST-413 are generation 1. The longest from the last branch stays generation 3, unchanged.

---

### 2026-11-14: the invisible-3d-shot branch against main, fourth review (the diff only)

- **How:** two reviewers read the diff, the third review's fixes most closely. One took the helpers' code and the
  docs that describe it, the other the tests. No tests were run and no probe was needed: reading settled every
  suspicion.
- **Not verified:** as in the earlier reviews: the Dock during a shot of a minimized window; whether the menu's last
  milliseconds at full opacity show; whether a click passes through the click-through menu; Spaces, a full-screen
  app, a locked screen, Stage Manager.
- **Resolutions assessed:** the eight of the third review and HLP-141, whose fixes are in this diff. Each fix
  addresses its cause, and each named test exists and fails without it: HLP-138's without the forget, HLP-139's two
  unit tests with the window directly in front kept, its live case on the old put-back (in its scratch run).
  Questioned:
  - HLP-138, HLP-140 and HLP-141: four sentences say more than the code and tests (HLP-142);
  - HLP-139: `mac_window.py`'s docstring still names `on_screen` as the guard (HLP-143), and its live case can't see
    a raise that does nothing (TST-415);
  - TST-410: its not-judged path (TST-414).

  TST-409, TST-411, TST-412 and TST-413 hold.
- **Findings:** 4, all Low: HLP-142, HLP-143, TST-414, TST-415. Merged: HLP-142's class docstring sentence (both
  reviewers).
- **Not raised:**
  - A user in Designer minimizing its window, or covering it with a window of Designer's own, during the shot: the
    window is brought back opaque and left up. DECISIONS.md, the 3D screenshot's window: left on screen when the user
    made Designer the active app, and none of its Reopen if holds (the helpers reviewer).
  - README's "If you switch to Designer during the shot, it becomes visible", for a user who leaves Designer and comes
    back between two looks (HLP-142's third sentence): it misleads only about a switch there and back within one
    step.
  - `put()`'s docstring listing `WAYS, DRAWN, ON_TOP` and not `TWO`, and the fake `Mac`'s docstring naming "the window
    in front of it" (the tests reviewer): they mislead no one.
  - `_UNDER` showing the window under in front before its `try` (the tests reviewer): as the second review's "Not
    raised".
- **Suggested order:** HLP-142 and HLP-143 (docs), then TST-415, then TST-414.
- **Checked and found fine:**
  - `between()` clearing `_was_active` only when a look sees Designer not active, and nothing the shot does
    (orderFrontRegardless, unhideWithoutActivation, the Explorer's menu, the clipboard render) taking the active app
    from Designer; `again()` running it before `_bring`, so `fade` reads the updated flag; an abort in it losing
    nothing;
  - `in_front()` read before `_fade` and `show()` at each bring. After the first bring Designer's window is in front
    of every normal window, so a window recorded later was raised or opened during the shot. The window goes behind
    the lowest recorded window still on screen in each case traced: several displays, a window behind it raised, its
    cover closed, minimized or raised again, its cover's app hidden, Designer's own windows among the covers, an
    always-on-top cover, minimized, covered then hidden. The BEHIND, GONE and NONE_FOUND lines match their branches;
  - the fake `Mac`'s `in_front` and `lowest` against the real ones; HLP-131's two unit tests still guarding their
    cases with the default `order`;
  - the `TWO` set-up: the raise leaves `later` only partly over the main window, so it isn't brought in front again;
    `clear()` closes `later`;
  - TST-409's order requirement; TST-410's `switched` read only from the shot's own lines; TST-411's
    `listed('windows')`, its pointers matching `mac._window`; TST-412's alone reading after `orderFrontRegardless`
    and 1 s, cleaned up in a `finally`;
  - no `above()` or `_behind` left; no unmarked `Any` or vague container in the functions the diff adds or changes;
    every multi-line snippet written with `dedent`; no older test weakened.
- **Chains:** HLP-136 → HLP-140 → HLP-142 and TST-410 → TST-414 reach generation 3, both about docs or a test's
  report, so their fixes make claims smaller. HLP-143 and TST-415 are generation 2. The longest from the last branch
  stays generation 3, unchanged.

---

### 2026-11-14: the invisible-3d-shot branch against main, fifth review (the diff only)

- **How:** two reviewers read the diff, the fourth review's fixes most closely. One took the helpers' code and the
  docs that describe it, the other the tests. No tests were run and no probe was needed: reading settled every
  suspicion.
- **Dropped by a decision:** the module docstring's "re-measures ... the second [point]" leaving out "covered once it
  is opaque again" (the helpers reviewer): DECISIONS.md, "Low-value findings about the tests and docs are not
  raised". It is generation 4, and the self-test reads the window under covered while the main window is opaque,
  the same state, though before the transparent reading rather than after it.
- **Not verified:** as in the earlier reviews: the Dock during a shot of a minimized window; whether the menu's last
  milliseconds at full opacity show; whether a click passes through the click-through menu; Spaces, a full-screen
  app, a locked screen, Stage Manager.
- **Resolutions assessed:** the four of the fourth review, whose fixes are in this diff. HLP-142's four sentences and
  HLP-143's `lowest` match the code. TST-415's readings each fail on a no-op event, as its scratch run showed, and
  pass on the code. Questioned: TST-415's `AGAIN` needs a wording the shot doesn't always say, and TST-414's
  docstring says the windows stay opaque from then on (TST-416).
- **Findings:** 2, both Low: HLP-144, TST-416.
- **Not raised:** `views.py`'s sentence leaving out a switch there and back between two looks (the helpers reviewer):
  as the fourth review's "Not raised" for README, which now says the same.
- **Suggested order:** TST-416, which the final check could hit, then HLP-144.
- **Checked and found fine:**
  - `cover_on_screen`: a cover never made reads None, so its event isn't seen and the case fails; `_CLEAR` removes
    the attribute before its last `state()`; only the HLP-124 check makes the cover again, and it doesn't use
    `event_seen`; a cover closed or minimized reads False only off screen, the minimize animation having more than
    1.5 s before `read()`;
  - the extra key in the state line: every older check's judged keys still come before the 150-character cut, the
    RENDER lines gain one key, `order` is unchanged;
  - `SEEN_BY['raise']` failing without the raise; the unit tests pinning each reading, so a constant or reversed one
    fails; `test_every_event_has_a_way_to_be_seen`; the transparency check's detail starting with the state after;
  - the code paths re-traced against the docstrings: Designer active as the shot began, left and back, seen at a
    look or not; a switch to Designer and away for each way; hidden, made active, hidden again; the first `_bring`
    without fading reachable only within microseconds; `_covers` giving the window its place back after a raise, a
    close or a cover's app hidden;
  - the Explorer's menu on Windows, only transparent, no riskier than on `main`; GUIDE.md's and README's 3D bullets;
    types, `dedent`, clean-up in a `finally`, no stale `AGAIN` or `above()` left.
- **Chains:** TST-414 and TST-415 → TST-416 reach generation 3, about a test's match and two sentences, so its fix
  makes claims smaller. HLP-144 is generation 2. The fourth review's HLP-142 chain stopped. The longest from the last
  branch stays generation 3, unchanged.

---

### 2026-11-14: the invisible-3d-shot branch's final check

- **How:** both suites in full (`tests/test_all_tools`): 23 categories, four Designers at once, the unit suite beside
  them. 1633 unit tests passed, and 731 of 735 live checks. The four failures, all in `editor_panels_and_fit`: the
  click fact and the window-under fact (TST-417), and the focus check's covered and hidden cases (TST-418). Each
  failing check passed in two scratch runs right after, in a Designer just started. No crash dump; the user's
  preferences as before the run.
- **Not verified:** a shot of a hidden Designer refused, twice, each time in the focus check's hidden way in a
  Designer just started: in the first of those scratch runs, and in one of TST-418's. The second kept its error:
  "the 3D view isn't drawn: Designer's window isn't on screen 3 s after it was shown", after "shown, transparent
  and without taking focus" and before "hidden again". So the first bring's wait for Qt's exposure ran out, where
  about 0.3 s was measured. Tried, in Designers just started and not:
  - 8 trials of the shot's own steps (its windows made transparent, then `unhideWithoutActivation` and
    `orderFrontRegardless`), half with the windows left opaque: exposed after 0.07 to 0.08 s each time;
  - 21 hidden shots through the tool in the check's sequence (the shot before, `put('hidden')`, the pan shot), with
    macOS's state added to the refusal (a temporary copy of `shot3d.py`, put back): every one taken.

  Limitation: a race that doesn't reproduce on demand. What would check it: the next full run, or a refusal with
  macOS's state in its message. Later the same day, five refusals in 13 runs of the check itself, one of them with
  macOS's state in its message: HLP-145.
- **Findings:** 3: Medium HLP-145; Low-medium TST-417, TST-418.
- **The second final check** (after TST-417, TST-418 and HLP-145): 1646 unit tests passed, and 733 of 735 live
  checks. The two failures, both TST-417's facts (its note): TST-417 open again. HLP-145's hidden shots and the focus
  check passed, the focus check not judging focus three times, Designer the active app before the shot.
- **The third final check** (after TST-417's launch lock): 1650 unit tests passed, and 731 of 735 live checks. The
  four checks holding the lock passed. The four failures are all the transparency check's cases: after each shot,
  one of Designer's windows other than the main one wasn't opaque and clickable (`faded=1`), and it already wasn't
  during the first case's renders (2 faded, 1 expected). Not settled yet: whether that window's own look is so (a
  tooltip's, say, click-through by design), which the check's count takes for one left faded, or the shot left it.
  Settled the next day: a tooltip leaves no such window; the check's own set-up shot with `graph=` had been refused,
  its Explorer's menu closed before its pick and left transparent and click-through (HLP-146).
- **The fourth final check** (after HLP-146): passed, 736 of 736 live checks in 23 categories, 1653 unit tests; the
  user's preferences as before the run.

---

## High

## Medium-high

## Medium

- [x] **TST-356 · The new unit tests break the Windows unit suite** · `tests/unit/test_designer_preferences.py:5,241`, `tests/unit/test_lifecycle_env.py:5,2855,2862` · confirmed · found 2026-11-13
  - **Defect.** Both files `import fcntl` at module level (the repo imported it only inside tests skipped on win32
    until now), and tests of macOS-only behaviour run everywhere: nearly every test of `test_designer_preferences.py`,
    `test_quit_with_no_designer_running_puts_back_a_copy_left`, `test_quit_puts_nothing_back_while_designers_cant_be_listed`
    and `test_defaults_failing_raises_its_error` (`/usr/bin/false`).
  - **Scenario.** On Windows, where the final check runs `pytest` beside the single live run, collecting either file
    raises `ModuleNotFoundError: fcntl`: about 2,800 lines of lifecycle tests stop running, the Windows-relevant ones
    with them; with the import moved, the ungated tests fail, as `saved()` and `put_back()` do nothing there.
  - **Fix.** Import `fcntl` inside the tests that use it; mark `test_designer_preferences.py` macOS-only (keeping
    `test_off_macos_nothing_is_saved_or_put_back` running everywhere), and gate the three other tests.
  - **Resolution: done.**
    - **Test:** `test_lint.py::test_no_module_imports_a_posix_only_module_at_its_top` (an `ast` walk of the repo's own
      Python files for `fcntl`, `termios`, `pwd`, `grp`, `resource`, `posix` imported where a file starts): seen failing
      with `import fcntl` put back at the top of `test_designer_preferences.py` (`['tests/unit/test_designer_preferences.py:6
      fcntl']`), passing without. The gates are read, not run: no Windows here.
    - **Cause:** the new tests took the module-level import and the platform for granted.
    - **Fix:** `fcntl` imported inside the tests that use it (`_held_elsewhere`, the launch test); every test of what is
      done with the plist marked macOS-only (`MACOS`, `_MACOS_PLIST`, uninstall's and the pool's `_MACOS`), the two
      off-macOS tests and the no-real-`defaults` guard left running everywhere.
    - **Also covered:** the whole repository by that test (nothing else imports one at its top); `_HOMES_OF_THEIR_OWN`
      (win32 only) replaced by the macOS gate on the preferences tests, which Linux would fail too.
  - Questioned by TST-369 (2026-11-13).

- [x] **SRV-146 · `screenshot_designer('3d')` returns the renderer's last frame while Designer's window is minimized, saying it set what the image doesn't show** · `mcp_server/designer_helpers/screenshots.py:45-97`, `mcp_server/server_tools/views.py:52` · measured · found 2026-11-13
  - **Defect.** The 3D shot is the view's own "Copy Render to Clipboard", the renderer's image. While Designer's main
    window is minimized the view isn't drawn, and the copy is the last frame drawn: the tool's line says what it set
    ("3D view: pan 0.25 of the view right ...") over an image from before it.
  - **Scenario.** Measured, in a Designer an agent started: a plane from the Top at zoom -4, the checker on it (its
    middle at column 170.5, row 181; 15 dark-light changes); the window minimized (`showMinimized()`, `isMinimized()`
    True), 15 s; `pan=[0.25, 0.25]`: the same middle, 0.00 grey levels from the shot before; `mesh='Rounded cube'`,
    `view='Front'`: 0.00 again, still the plane with its 15 changes. Shown again (`showNormal()`), the same pan moved the
    plane to (85.5, 270), 36.32 from the shot before. The user minimizing Designer while an agent works in it gets the
    agent a material, mesh or camera judged on an image that isn't the one set.
  - **Fix.** The tool measures before it shoots: a minimized window refused, saying the 3D view isn't drawn (or shown
    again and then refused if it stays so; the user's choice whether the tool may restore their window); and, for what
    else may stop the drawing (TST-388), a set-up that moved the camera or switched the mesh followed by a render
    identical to the one before it is a stale shot, said or retaken. A live check: the window minimized, the shot
    refused or said stale; GUIDE.md's line. Settled by the probe above.
  - **Resolution: done.** The user chose (DECISIONS.md, the 3D screenshot puts Designer's window on screen): a
    minimized window un-minimized and left so; then, once probes showed a covered window and a hidden Designer stop
    the drawing too, "Bring forward, then back" for those; and the flag on an identical render.
    - **Test:** `tests/unit/test_shot3d.py` (8 tests of `_on_screen`: each way off screen, the put-back after a failed
      shot, the refusal, nothing done off macOS; 15 of `shoot_3d`: the retakes, the line, which set-ups are compared,
      refusals before the window changes) and `tests/unit/test_view3d.py` (the one helper call; the window's lines
      beside the image and in an error), failing first (no `_on_screen` or `shoot_3d`; the old call). Live, in scratch
      runs: `check_a_3d_shot_puts_designers_window_on_screen_without_taking_focus` failed with the plane moved 0.000
      of the view in all four ways (minimized by macOS, by Qt, covered, hidden), then passed (0.247 to 0.249, the
      line, the window put back as chosen, Designer never the active app); a mutant without `_MacWindow` failed it
      again. `check_a_render_that_didnt_follow_a_pan_is_said` failed on a mutant without the line, then passed. The
      designer facts check `check_the_3d_view_isnt_drawn_while_designers_window_is_off_screen` passes. The whole
      `editor_panels_and_fit` category passed in a scratch run, but for one read of the covered window's state taken
      before macOS updated it (about 0.1 s after the send-back: `window_states.read()` now waits).
    - **Cause:** the 3D view draws only while Designer's window is on screen, and the shot copied the renderer's image
      without looking. Off screen means minimized, fully covered by any window, or Designer hidden (measured; a window
      partly covered draws). macOS minimizing the window leaves Qt's `isMinimized()` False, so Qt alone can't tell.
    - **Fix:** the server calls `shoot_3d` (`designer_helpers/shot3d.py`, a new part) for every '3d' shot. It refuses
      what the arguments alone rule out, and a 3D View panel not shown, before the window changes. `_on_screen` then
      asks macOS through the Objective-C runtime (`_MacWindow`) and puts the window on screen without making Designer
      the active app: un-minimized and left so, or brought in front and sent back after, or shown and hidden again
      after. It refuses when the window still isn't exposed after 3 s. Each step prints a "Designer's window: ..." line,
      which the server returns beside the image and in an error. After a set-up that moved the camera or switched the
      mesh, a render identical to the one before is retaken 3 times, 0.5 s apart, then said ("3D render: ..."). The
      tool's docstring, GUIDE.md, README.md (Security; the self-test) and ROADMAP items 83, 90 and 91 say so;
      `_save_3d_render` became `_3d_render` (the QImage), and `save_screenshot('3d')` refuses.
    - **Also covered:** the other panels' shots paint their widgets (`QWidget.grab()`): with the window minimized,
      'graph', '2d' and 'parameters' came out identical to on screen ('window' differed by 0.4 grey levels, in its 3D
      area, which shows no render anyway). Off macOS nothing was measured and the window is left as it is (ROADMAP
      item 90). A 3D View panel floating in a window of its own isn't looked at (the module docstring). An abort
      landing on the put-back leaves the window on screen (ROADMAP item 91). The self-test's own windows: its
      covering window shown with `raise_()` made Designer the active app, so it goes in front through
      `orderFrontRegardless` instead.
  - Questioned by HLP-124, TST-389, TST-390, TST-391, HLP-125, HLP-126, HLP-127, SRV-147, HLP-128, TST-392, TST-393, TST-394 and HLP-129 (2026-11-13).
  - Note (2026-11-13): the Cause's "macOS minimizing the window leaves Qt's `isMinimized()` False, so Qt alone can't
    tell" holds of `getMainWindow()`, a page: the top-level window's `isMinimized()` is True (TST-391). And
    `check_the_3d_view_isnt_drawn_while_designers_window_is_off_screen` runs each way's put, pan and clear in one
    snippet: a pan that fails leaves the window off screen, which the next check's first shot puts back (the tests
    reviewer; not an entry).
  - Questioned by TST-397 (2026-11-14).

- [x] **HLP-145 · A 3D shot of a hidden Designer is refused about one time in three: its window comes back on screen, but macOS counts it as covered** · `mcp_server/designer_helpers/shot3d.py:82-96,198-216` · measured · found 2026-11-14
  - **Defect.** For a hidden Designer, `_bring` makes every window of its own transparent, then calls
    `unhideWithoutActivation` and `orderFrontRegardless`, and `_wait_on_screen` waits for Qt to say the main window
    is exposed. Sometimes it never is. The shot is refused after 3 s ("the 3D view isn't drawn: Designer's window
    isn't on screen 3 s after it was shown; ask the user to show it"), and Designer is hidden again.
  - **Scenario.** Measured: the focus check's hidden way was refused in 5 of 13 runs of the check, each in a Designer
    just started (the final check's follow-ups, TST-418's scratch runs, the category's). With macOS's state added to
    the refusal (a temporary copy of `shot3d.py`, put back), it read `hidden=False covered=True cg=True
    page_visible=True page_exposed=False active=False`, the page's native window the same throughout. So Designer was
    shown again and CoreGraphics listed its window on screen, but the window's occlusionState said not visible, so Qt
    never exposed it and the view didn't draw. Reading the top-level window's QWindow then raised "Internal C++ object
    (PySide6.QtGui.QWindow) already deleted". The same steps run 8 times in a snippet, and 25 hidden shots through
    the tool in the check's own sequence, were never refused; what makes the check's runs differ isn't known. On
    `main` the window came back opaque. An agent told "ask the user to show it" interrupts the user, which the shot
    was made to spare.
  - **Fix.** Measure first, in the check's own runs, what brings the window's occlusion back: ordering it in front
    again once Designer is no longer hidden, or during the wait; or an opacity just above 0. Then fix it, with the
    hidden way run until the refusal would have shown.
  - **Resolution: done.**
    - **Measured first:** in the check's own runs, a temporary copy of `shot3d.py` did two things once the wait ran
      past a time: past 0.5 s it ordered the window in front again, and past 1.5 s it gave the window an opacity of
      1/255. In 3 of 14 runs the window was still covered for macOS at 0.5 s (`hidden=False covered=True`). Ordered in
      front again, it was exposed within 0.06 s each time, and the opacity step was never reached.
    - **Test:** `test_a_window_not_yet_on_screen_after_a_while_is_put_in_front_again_once` (minimized, covered,
      hidden), with the window exposed only once put in front twice: refused before the fix, the shot taken after.
      `test_a_window_still_not_on_screen_is_refused_and_put_back` now expects the second showing. Live, the focus
      check ran in 10 Designers just started, on the fixed code (a copy saying when it put the window in front
      again). 5 runs needed it, and every shot was taken.
    - **Cause:** the shot ordered the window in front once, as Designer was shown again, then only waited. macOS
      sometimes didn't count the window visible after that, and nothing ordered it in front again.
    - **Fix:** `_wait_on_screen` puts the window in front again (`_MacWindow.show`), once, when it isn't exposed after
      `SHOW_AGAIN` (0.5 s). The measurement is in the module docstring.
    - **Also covered:** every way the window is brought on screen (minimized, covered, hidden, a page Qt minimized)
      goes through the same wait, so each gets the second try; only the hidden way was seen to need it.

## Low-medium

- [x] **SRV-125 · With no log of the user's, an old copy is put back over the user's own later changes** · `designer_preferences.py:79-85,199` · confirmed · found 2026-11-13
  - **Defect.** The only sign that the user's Designer ran since the copy is their `*/log.txt` being newer
    (`if users_log_time() > made:`); with that log missing or older, nothing else stops a put-back.
  - **Scenario.** Agents' Designers end outside the tools (a reboot, a killed server, the self-test's kill), leaving a
    copy; the user then works in their own Designer for days, but their log is gone (a cleaner app, a reinstall) or its
    time is behind; the next `launch_designer` or `quit_designer` with none running deletes every key added since the
    copy and puts the old values back: the change DECISIONS.md's entry names as its reopen condition. The obvious
    second sign doesn't work: a pool run without the put-back left `session.instancePID` as it was before the run
    (only `session.modes.mixer.areas` changed), so a Designer's process ID isn't left there after it quits.
  - **Fix.** A second, independent sign that drops the copy (the user's choice which): an age past which a copy no
    Designer is running for is dropped rather than put back (hours, not days), or the plist file's own mtime compared
    with the last end an agent's Designer was seen to have; say in the result which one dropped it.
  - **Resolution: done** (the user's choice, 2026-11-13: an age).
    - **Test:** `test_designer_preferences.py::test_a_copy_left_behind_is_put_back_only_within_its_hours[7]` (put back,
      as before) and `test_lifecycle_env.py::test_quit_with_no_designer_running_drops_a_copy_left_too_long` (`said` lacked
      the drop) failed; `test_an_old_copy_is_put_back_right_after_its_designer_ended` and the quit test's forced/closes
      runs on a copy 11 hours old guard the other side.
    - **Cause:** a copy left by Designers that ended outside the tools was trusted however old, with the user's log as
      the only sign of their work since.
    - **Fix:** `put_back(running, *, ended)`: without a Designer just ended through the tools (`ended=False`: a launch's
      `saved()`, `quit_designer` ending none, the pool's start, uninstall), a copy older than `LEFTOVER_HOURS` (6) is
      dropped and said; `_quit` returns whether it ended one. DECISIONS.md's entry records it.
    - **Also covered:** every caller passes `ended`, keyword-only so none can leave it out; `session.instancePID` not
      used, as measured.
  - Questioned by SRV-133 (2026-11-13).

- [x] **SRV-126 · An unreadable preferences file is saved as an empty copy, so a later put-back would delete every key** · `designer_preferences.py:148-150,219-226` · measured · found 2026-11-13
  - **Defect.** `_save` keeps whatever `defaults export` prints once it parses as a plist; an empty one is taken as the
    user's file. A put-back then counts every key of the file as added, and the read-back compares with that empty copy.
  - **Scenario.** Probe: a plist written to `~/Library/Preferences` under a scratch domain cfprefsd had never read, mode
    000, then `defaults export <domain> -`: an empty `<dict/>`, exit 0. With the user's file unreadable as a launch saves
    it, and readable again at the put-back, all of its 18,576 keys are deleted one by one, and the put-back reports
    success.
  - **Fix.** In `_save`, refuse an empty export when the plist file exists with a size above an empty one's (say it
    as not saved); in `_put_back`, refuse to delete when the copy is empty and the file isn't, and say so.
  - **Resolution: done.**
    - **Test:** `test_designer_preferences.py::test_an_empty_read_of_a_file_holding_settings_is_not_saved[holding
      settings|unreadable]` (the file written, mode 000 in the second): failed, the empty copy saved;
      `test_an_empty_read_of_a_file_holding_none_is_saved[none|empty]` guards a Designer never run here.
    - **Cause:** an empty export was taken as the user's file, and `defaults` reads an unreadable one as empty.
    - **Fix:** `_save` refuses an empty export while `plist_file()` (read directly, only read) holds settings or can't be
      read, said as not saved. Not done: a refusal at the put-back, as the finding also suggested: an empty copy then
      only comes from a file with no settings, whose agents' keys should be deleted.
    - **Also covered:** `plist_file()` patched to the test's folder by conftest's `defaults` fixture.

- [x] **TST-376 · A new launch test connects to the real bridge port, and fails while a Designer listens there** · follows SRV-139, generation 3 · `tests/unit/test_lifecycle_env.py:2956-2982` · confirmed · found 2026-11-13
  - **Defect.** `test_a_launch_refuses_once_a_designer_starts_during_its_put_back` calls
    `server.launch_designer(wait_s=30)` without `patch_server(monkeypatch, '_send', _no_bridge)`, and no fixture
    replaces `_send` (`no_real_designer_process` and `defaults` don't; `_launch_fakes` replaces only `_bridge`).
    `launch_designer` first asks `_control('status', wait=5, port=port)`, whose `_send` opens
    `socket.create_connection(('127.0.0.1', port))`: the real port 9877 (or `SD_BRIDGE_PORT`).
  - **Scenario.** The user runs `pytest` with their Designer open on the default port (the usual case, as in TST-147),
    or an `alone.run` Designer is open on it: the test sends that plugin a `status` request signed with conftest's
    made-up token, the plugin answers `invalid token` (`plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:439`),
    `_control` raises `_Refused`, `launch_designer` raises it before any put-back, and `said.startswith("Designer's
    preferences couldn't be put back ...")` fails: a false failure, and a request to a real Designer, which
    `no_real_designer_process`'s docstring says no unit test makes. With nothing listening, the connection is refused and
    the test passes. The tests reviewer scanned the file's other calls of `launch_designer`, `quit_designer` and
    `designer_status` without `_send` replaced: none reaches the bridge (no Designer for the quits; `_held_port`;
    `_closes`).
  - **Fix.** `patch_server(monkeypatch, '_send', _no_bridge)` in that test, as its neighbours have. No new check
    (generation 3, tests only). Settled by reading (`_send`, `server_tools/core.py:268-296`; the fixtures).
  - **Resolution: done.**
    - **Test:** the test itself, run with `SD_BRIDGE_PORT` on a scratch stand-in for the plugin (its greeting, then
      every request refused as one with the wrong token): it failed with "Designer refused the 'status' request:
      invalid token"; fixed, it passes with that stand-in listening, which then gets no request.
    - **Cause:** written for SRV-139, it replaced the bridge's `_bridge` (`_launch_fakes`) but not `_send`, which
      `launch_designer`'s first `status` request goes through.
    - **Fix:** `patch_server(monkeypatch, '_send', _no_bridge)` in it, as its neighbours have.
    - **Also covered:** the tests reviewer's scan of the file (no other call of `launch_designer`, `quit_designer` or
      `designer_status` without `_send` replaced reaches a bridge); the three tests added for SRV-141 replace it too.

- [x] **TST-383 · The 3D camera checks failed in a full run, the graph's material reaching the mesh about 20 s late** · `tests/test_all_tools/editor_panels_and_fit/checks.py:165-240` · measured · found 2026-11-13
  - **Defect.** In the final check (the unit suite beside four workers), `orbit=` from Front measured 0.00 from both
    the Right and the Left view, `orbit=[90, 90]` 0.00 from both top views, and `pan=[0.25, 0.25]` moved the plane
    0.000. Those are renders of a mesh without the checker: a rounded cube with no pattern reads the same from either
    side and from every top angle. A later shot of the pan check found the checker again. The same checks passed in a
    scratch run, in a live run without the unit suite, under full CPU load (12 busy processes on 10 cores: the checker
    on the mesh at once, 12 times of 12) and with another Designer's window over the view (the render followed the
    camera). So the delay didn't reproduce on demand. Found by the final check.
  - **Scenario.** The final check fails though the tools work.
  - **Fix.** The checks wait for the checker on the mesh before they measure.
  - **Resolution: done.**
    - **Test:** `test_selftest_renders.py::test_a_shot_is_taken_again_until_the_checker_shows_on_the_mesh`,
      `test_a_shot_with_the_checker_at_once_is_taken_once`, `test_a_shot_waits_for_the_checker_only_so_long` and
      `test_a_shot_that_failed_isnt_taken_again` failed (no `with_checker`). The delay itself didn't reproduce on
      demand, so no live check was seen failing.
    - **Cause:** the checks measured the first shot after a call that switches the mesh or applies a graph, and the 3D
      view can show the graph's material on the mesh late (once, about 20 s).
    - **Fix:** `renders.with_checker` retakes the shot as the 3D view is, a second apart, until the checker shows, at
      most 30 times. The checker shows at 6 dark-light changes or more: 11 to 30 were measured with it and 1 at most
      without, in each kind of shot the checks take. It says how many retakes it took, or that the checker never
      showed. The 12 shots of the 3D checks that switch the mesh or apply the graph, then measure, go through it.
      `test_selftest_summary.py`'s rule now exempts a helper the category's checks await (a helper nothing awaits is
      still reported: tried).
    - **Also covered:** the shots taken before any graph's outputs are on the mesh (the first 3D check's `before` and
      `after`), and those whose image isn't measured, stay plain. An agent's shot may still come before the material:
      ROADMAP item 83 has it. Scratch run: `editor_panels_and_fit`, 46 of 46.
  - Questioned by TST-384, TST-385, TST-386 and TST-387 (2026-11-13).

- [x] **TST-384 · Two 3D checks read the set-up's text from a shot `with_checker` may have retaken, which has none** · follows TST-383, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py:77,500`, `tests/test_all_tools/editor_panels_and_fit/renders.py:99-101` · confirmed · found 2026-11-13
  - **Defect.** `with_checker` returns its last shot, and a retake is a call with only `panel` and `max_size`, whose
    text has no "3D view: ..." line of what was set. Two of its 12 sites then read that line: the first 3D check's
    `VIEW3D_ADDED in text(applied)`, and the check on opening the editor's graph again, `'back on %s' % VIEW3D_PLAIN in
    text(r)` (the Parameters panel turned back by `tiling=`). The lead, assessing TST-383.
  - **Scenario.** The material reaches the mesh late, the case the wait is for: the shot is retaken until the checker
    shows, and the check fails on the text instead of on the image.
  - **Fix.** `with_checker` keeps the first shot's text with the last shot's image (or returns both shots, and the two
    sites read the first's text); a unit test with a retake whose text differs. Settled by reading.
  - **Resolution: done.**
    - **Test:** `test_selftest_renders.py::test_a_retaken_shot_keeps_the_text_of_what_the_call_set` failed: the retaken
      shot's text was empty.
    - **Cause:** `with_checker` returned the last shot as it came, and a retake's call sets nothing, so says nothing.
    - **Fix:** after a retake, the last shot keeps its image and takes the first shot's text (what the call set); the
      docstring says so. Mutation caught: the text not kept.
    - **Also covered:** a retake that failed is returned as it is (its error); the other ten sites read no text of the
      shot. Scratch run: `editor_panels_and_fit`, 46 of 46.

- [x] **TST-388 · The late material is the cause the docs and the wait give, but the evidence fits a stale render, which the wait can accept** · follows TST-383 and TST-385, generation 3 · `mcp_server/GUIDE.md:48-50`, `tests/test_all_tools/editor_panels_and_fit/renders.py:19-20,93-96`, `tests/unit/test_selftest_renders.py:138-139`, `ROADMAP.md:70` · confirmed · found 2026-11-13
  - **Defect.** GUIDE.md ("the material reached the mesh about 20 s after a call ...: a plain mesh right after `graph=`
    may be late"), `RETAKES`' comment and `with_checker`'s docstring, the unit test's comment and ROADMAP item 83 give
    a late material as the cause of TST-383's failure, and TST-383 says the renders were "of a mesh without the
    checker". The failed pan's 0.000 contradicts it: a plane with the default material is found (columns 94 to 247 from
    the Top at zoom -4, measured for TST-383), so a plain plane panned would have moved about 0.25. 0.000 takes the same
    render twice, nothing drawn, or drags not taken; the orbit's identical images fit a stale render as well. A stale
    render is now measured (SRV-146: a minimized window's shots are its last frame). And a stale frame from the check
    before, the checker on it, passes `with_checker` at once: the wait may not cover what happened. The docs reviewer;
    the stale render measured by the lead.
  - **Scenario.** An agent shown an image that doesn't follow `view=` or `orbit=` isn't told to shoot again, only to
    expect a plain mesh; whoever works on ROADMAP item 83 measures a material's delay; the full run fails again the same
    way, the wait taking the stale checker for the material.
  - **Fix (generation 3: smaller claims).** Say what was seen, in each place: once, in a full run, the 3D shots didn't
    follow the camera for about 20 s after a call that switched the mesh and applied the graph; the cause unknown, a
    minimized window being one measured way (SRV-146). GUIDE.md: a 3D shot that doesn't show what the call set (the
    mesh, the view, the material) may be stale: shoot again. Whether the checks need more than `with_checker` follows
    from SRV-146's fix (a stale shot refused or said by the tool, which the checks then report). Settled by reading and
    the probe.
  - **Resolution: done** (generation 3: smaller claims).
    - **Test:** docs and comments only; the tests that validate the docs pass, and `with_checker`'s unit tests are
      unchanged.
    - **Fix:** GUIDE.md's Look bullet drops the late material. It now says the 3D view draws only while Designer's
      window is on screen, which the tool sees to on macOS, and that a 3D shot not showing what the call set may be
      the view's last frame: shoot again. `RETAKES`' comment, `with_checker`'s docstring, the unit test's comment and
      ROADMAP item 83 say what was seen: the 3D shots didn't follow the camera for about 20 s, the cause unknown. The
      wait itself stays, as a defence.
    - **Also covered:** two more ways to the view's last frame were measured for the full run's case. A second agent
      Designer raised and activated over the editor's, as the self-test's Undo snippet does, didn't cover it: the
      first drew on. Another app's window covering Designer does stop the drawing, which SRV-146's fix now handles.
      The full run's trigger stays unverified.
  - Note (2026-11-13): a candidate for the full run's trigger, not measured. Agents' Designers open where the user's
    Designer window was (the shared preferences), so a worker's Designer started while the editor's ran may have opened
    over it and covered it whole (TST-390's case). Before SRV-146's fix, the shots were then the view's last frame. The
    docs reviewer.

- [x] **HLP-124 · The 3D shot puts Designer's window on screen once, before the set-up: a window covered again during the shot is rendered covered, and nothing is said** · follows SRV-146, generation 2 · `mcp_server/designer_helpers/shot3d.py:119-164,201-211`; the docs: `shot3d.py:121,193`, `mcp_server/server_tools/views.py:121`, `ROADMAP.md` item 83 · measured · found 2026-11-13
  - **Defect.** `_on_screen` reads the window's state, and waits for it to be exposed, only before its `yield`. Nothing
    looks again before `shoot_3d`'s renders. The docstrings say the window is on screen "while the 3D view is set up and
    rendered" and "throughout", the server's comment "through the set-up and the render", and ROADMAP item 83 that the
    tool "now prevents" a window off screen. Off screen, the render is the view's last frame (SRV-146). The docs
    reviewer.
  - **Scenario.** Measured, in a Designer an agent started: the checker plane from the Top, on screen; `shoot_3d(out,
    pan=[0.25, 0.0])` with a window of Designer's own brought in front of it 0.17 s, then 0.45 s, into the call (a
    `QTimer`). Both times the render after the pan was taken at 0.79 s with the window covered (`occlusionState` not
    visible, `isExposed()` False), and nothing was said: the render differed from the one before, so no retake and no
    "3D render:" line. A user who clicks their own window back in front while the shot runs (Designer has just come up
    over it) gets the agent the view's last frame. After `graph=`, `view=` or `tiling=` no comparison is made, so an old
    material is judged as the new one.
  - **Fix.** Before each render, look again (the exposure `_wait_on_screen` reads, the macOS state): put the window back
    on screen as at the start and wait, or refuse, with a line saying so. A unit test with the window covered after the
    set-up; the live check covering it during the set-up, as the probe did. Or, the smaller fix, the four sentences
    narrowed to "put on screen before the set-up". Settled by the probe above.
  - **Resolution: done.**
    - **Test:** `test_shot3d.py::test_a_window_put_off_screen_during_the_shot_is_put_on_screen_again` (covered,
      minimized or hidden during the shot) and `test_a_render_identical_after_a_pan_is_taken_again_until_it_differs`
      (each render after a look) failed first: there was no second look. Live,
      `check_a_window_covered_during_a_3d_shot_is_put_in_front_again` brings a window of Designer's own over Designer's
      as the pan's first drag starts, and waits 0.5 s. In its scratch run it failed with the plane moved 0.000 and the
      stale line said, then passed: 0.249, the line "brought in front again", and the window put back behind that cover.
    - **Cause:** `_on_screen` looked at the window once, before the set-up; nothing looked again before the renders.
    - **Fix:** `_on_screen` yields a `_Screen` (`shot3d.py`), and `shoot_3d` calls its `again()` before each render: the
      one before the set-up, the one after, and each retake. A window covered, minimized or hidden meanwhile is put on
      screen the same way as at the start, with a line of its own ("... again ..., as another window covered it during
      the shot"), and put back after as at the start. The four sentences hold now.
    - **Also covered:** the retakes and the plain shot look again too. In the scratch run with Designer's window moved,
      one of the user's windows covered it during the "on screen" step's shot: the tool brought it in front again, and
      the render followed the pan.
  - Questioned by HLP-131 and TST-396 (2026-11-14).

- [x] **TST-389 · The 3D checks' cover is placed from the page's geometry, so it covers Designer's window only near the screen's top-left** · follows SRV-146, generation 2 · `tests/test_all_tools/editor_panels_and_fit/window_states.py:36` · measured · found 2026-11-13
  - **Defect.** `cover.setGeometry(mw.frameGeometry().adjusted(-50, -50, 50, 50))` takes the frame of `getMainWindow()`,
    a page of the top-level `QStackedWidget` (GUIDE.md). Its geometry is relative to that stack, not to the screen, so
    the cover lands at the screen's top-left wherever the window is. The lead, from a probe's printout.
  - **Scenario.** Measured, in a Designer an agent started: the page's `frameGeometry()` (0, 0, 1599, 965), the
    top-level's (52, 30, 1599, 993); the cover came out at (0, 30, 1699, 993), covering the window only because it sits
    52 px from the left. Agents' Designers open where the user's Designer window was (the shared preferences). With the
    user's window more than about 100 px from the left, or 50 px down, the 'covered' way covers nothing, and three
    checks fail in the final check: the designer fact (the render changed by the pan), the shot's "brought in front"
    line missing, and the stale line not said.
  - **Fix.** Place the cover from the window, `mw.window().frameGeometry()`. Have the checks refuse, saying why, when
    `put('covered')`'s STATE line shows the window not covered, rather than fail later. Settled by the probe above.
  - **Resolution: done.**
    - **Test:** a scratch run with the agent's Designer window moved to (400, 172) and made 1025x728. The designer fact
      failed (the covered way's render changed by the pan), check 2's covered way failed (not covered after `put`, no
      line), and check 3 said nothing with the window "covered".
    - **Cause:** the cover took `getMainWindow()`'s frame, the page's geometry inside the top-level window.
    - **Fix:** `window_states.py` places the covers and the window behind from `mw.window().frameGeometry()`. A second
      cause showed in that run: a window already covered by one of the user's windows, brought in front and covered
      again at once, stayed exposed for Qt and drawn, while macOS said it was covered (measured: covered=True
      exposed=True). `put` now waits 0.5 s after bringing the window in front, before covering it. After both, the run
      with the window moved passed all 15 window checks.
    - **Also covered:** `covered_during_pan` and the new 'partly covered' way place their covers from the window too,
      and the 'partly covered' way brings the window in front first, so its strip isn't under the user's windows.

- [x] **TST-390 · Two 3D checks take their on-screen baseline with the window as it is, and a covered window fails them** · follows SRV-146, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py:674-675,784`, `tests/test_all_tools/editor_panels_and_fit/window_states.py:97-101` · confirmed · found 2026-11-13
  - **Defect.** The "on screen" case of `check_the_3d_view_isnt_drawn_while_designers_window_is_off_screen` runs
    `window_states.panned(None)`, whose `read()` doesn't put the window on screen. The `on` step of
    `check_a_render_that_didnt_follow_a_pan_is_said` runs `PAN_AS_IT_IS`, which turns `_mac_window` off. A window fully
    covered isn't drawn (SRV-146), and the `with_checker` shot before each sends a covered window back behind the others
    (`orderBack:`, HLP-126). The tests reviewer; the docs reviewer too.
  - **Scenario.** In a full run, another worker's Designer opens over this one (agents' Designers open at the same
    place, from the user's preferences), or the user's terminal covers it: the fact fails with "on screen True", and the
    stale check with "on screen: True", blaming Designer or the tool.
  - **Fix.** Put the window in front without focus (`window_states.clear()`) before both baselines, and run check 3's
    `on` step through the real `_mac_window`. Settled by reading, on SRV-146's measurement.
  - **Resolution: done.**
    - **Test:** a scratch run with a window of Designer's own kept over Designer's: the designer fact failed with "on
      screen True". Check 3's `on` step passed in that run, because check 2's last `clear()` had brought the window in
      front; reading its code settles it.
    - **Cause:** both baselines read the window as it was, covered or not.
    - **Fix:** `window_states.panned(None)` puts the window on screen, in front of other windows, first (`clear()`).
      Check 3's `on` step shoots through the real `_mac_window`; only its covered step leaves the window as it is
      (`AS_IT_IS`). The same run then passed all 15 checks.
    - **Also covered:** check 2 and the new window checks start from a shot or `clear()`, which put the window on
      screen.

- [x] **TST-391 · `shot3d.py`'s measured Qt facts are the hidden page's, not the window's, and its docstring says the self-test checks more than it does** · follows SRV-146, generation 2 · `mcp_server/designer_helpers/shot3d.py:4-14,153`, `tests/test_all_tools/editor_panels_and_fit/window_states.py:5-6`, `tests/test_all_tools/editor_panels_and_fit/checks.py:662-666` · measured · found 2026-11-13
  - **Defect.** "When macOS minimizes the window, as its minimize button does, Qt's isMinimized() stays False, and Qt's
    own restores (showNormal(), setWindowState()) do nothing" was measured on `getMainWindow()`, a page of the top-level
    `QStackedWidget` (GUIDE.md), not on the window. The 'qt minimized' way (`mw.showMinimized()` on the page) is a state
    no user makes. SRV-146's Cause says "so Qt alone can't tell". And "the self-test's editor_panels_and_fit checks the
    first two points": the designer fact asserts the render unchanged in the four ways and, for the macOS-minimized
    window, `isMinimized()` False and not exposed. Nothing checks another app's window, a window partly covered drawing,
    covered and hidden windows not exposed, the Qt-minimized page exposed, Qt's restores, the forced redraws, nor the
    Scene menu's check mark, which `_mesh_shown` relies on. The docs reviewer (the page) and the tests and docs
    reviewers (the checks).
  - **Scenario.** Measured, in a Designer an agent started, macOS minimizing the window (`performMiniaturize:`): the
    page said `isMinimized()` False, the top-level `QStackedWidget` True (`windowState()` WindowMinimized, not exposed).
    The page's `showNormal()` did nothing; the top-level's restored the window. Whoever does ROADMAP item 90 (Windows),
    or simplifies `_MacWindow`, reads that Qt can't see or undo a minimize, which it can, on the window. (The page was
    native before `_MacWindow` asks for its `winId()`, 7 native widgets before and after: no side effect.)
  - **Fix.** Say the facts of the page and of the window as measured (the code may read the top-level's state,
    `mw.window()`). Describe the 'qt minimized' way as the page's state, or drop it. Narrow the parenthetical to what
    the check asserts, with a designer fact for what the code relies on (a window partly covered drawing; the Scene menu
    checking the mesh shown, measured right: Rounded cube, Sphere, Plane), or mark those claims as measured once. A note
    under SRV-146 points here. Settled by the probe above and by reading.
  - **Resolution: done.**
    - **Test:** designer facts, seen passing (a fact can't be seen failing here). Check 1 now asserts, for the
      macOS-minimized window, the top-level's `isMinimized()` True beside the page's False (`window_states.state()`'s
      `top_minimized`), and a 'partly covered' way drawn (`window_states.DRAWN`: a cover leaving a 100 px strip).
      `check_the_3d_views_scene_menu_checks_the_mesh_shown` reads Sphere, then Plane.
    - **Fix:** `shot3d.py`'s docstring states the facts of the page and of the top-level window as measured: the
      top-level's `showNormal()` restores the window, the page's does nothing. It adds the drags reaching the camera off
      screen, and says which points the self-test re-measures, the rest measured once. `window_states.py` describes 'qt
      minimized' as the page's state. `mac_window.py` holds the window list's facts. ROADMAP item 90 says Qt's top-level
      window sees a minimize. The note under SRV-146 points here.
    - **Also covered:** the code still reads the page's Qt state, for the self-test's 'qt minimized' way, and macOS for
      the rest; reading the top-level instead is left to item 90.
  - Questioned by TST-398 (2026-11-14).

- [x] **TST-395 · The 3D checks count the checker on one row, which can fall on the edge between two rows of squares** · `tests/test_all_tools/editor_panels_and_fit/renders.py:53-64` · measured · found 2026-11-13
  - **Defect.** `transitions()` reads only the render's middle row. A render blends two rows of squares into one grey
    along their edge, so when the middle row falls there it counts no change at all: the row's range is under 40 grey
    levels, which `transitions()` takes for shading. Found while fixing the ninth review's findings.
  - **Scenario.** Measured, in a Designer an agent started: with the 3D view 442x345 (its layout after a scratch run
    resized the window), the checker plane from the Top at zoom -4 filled rows 94 to 251. Row 172 read 160 to 171 grey
    levels, 0 transitions; rows 165 to 180 around it, 15 each. `with_checker` then retook its shot 30 times, "the
    checker didn't show", and every check measuring the checker would fail. Agents' Designers take the user's layout, so
    the 3D view's height, and with it this edge, is the user's.
  - **Fix.** Count on a few rows around the middle (the middle and 3 pixels either way, at least one off an edge while a
    square is more than 6 pixels high) and keep the most; a unit test with a blended middle row. Settled by the
    measurement above.
  - **Resolution: done.**
    - **Test:**
      `test_selftest_renders.py::test_a_middle_row_on_the_edge_between_two_rows_of_squares_still_counts_the_checker`
      failed: 0 transitions, not 7.
    - **Cause:** `transitions()` read the render's middle row alone.
    - **Fix:** it keeps the most of the middle row and the rows 3 pixels either way (`_row_transitions`). The live runs
      after it found the checker without retakes, the whole `editor_panels_and_fit` category passing; the 442x345 layout
      that showed it wasn't run again.
    - **Also covered:** the tiling check and every `with_checker` site count through it. `plane_columns` and
      `plane_middle` read the whole plane, not a row.
  - Questioned by TST-398 (2026-11-14).

- [x] **TST-399 · Two checks of a covered window's put-back fail when Designer becomes the active app during the shot, which the tool then rightly leaves up** · follows HLP-125, generation 3 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_a_window_covered_during_a_3d_shot_is_put_in_front_again`, `check_a_covered_window_goes_back_behind_its_cover_or_stays_in_front_once_the_cover_is_gone`) · measured · found 2026-11-14
  - **Defect.** A Designer that became the active app during the shot is left on screen (HLP-125; DECISIONS.md, the
    3D screenshot entry). Check 4 asserts the window covered after the shot (`state.get('covered') == 'True'`), and
    the put-back check asserts one of its put-back lines and an order. Neither allows for that case. Found by the
    final check.
  - **Scenario.** Measured, in the branch's second final check (723 of 724 live checks): check 4's pan moved the plane
    0.249 of the view, and the shot said "brought in front again ..." and then "left on screen, as Designer became the
    active app during the shot". After it, `active=True covered=False order=main,cover`, so the check failed. What
    made Designer the active app wasn't seen. Agents' Designers become the active app as they launch (seen twice
    that day), and macOS may hand activation to another of them as one quits or hides; a click would do the same.
  - **Fix (generation 3: a smaller claim).** When the shot says it left the window on screen as Designer became the
    active app, the two checks don't judge the put-back, and say so. Check 2 still judges focus where it can
    (TST-392), and the unit tests pin the put-back's choice (HLP-125). A scratch run makes Designer the active app
    during the shot, to see both checks fail first. Settled by the full run's output.
  - **Resolution: done** (generation 3: a smaller claim).
    - **Test:**
      `test_selftest_window_states.py::test_designer_becoming_the_active_app_during_a_shot_is_told_apart` failed
      first: there was no helper. Live, a scratch run made Designer the active app as the pan began (check 4's cover
      and the put-back check's later window). Check 4 failed with `active=True covered=False order=main,cover`.
      Activation had brought Designer's windows in front itself, so nothing was put back and nothing said of it. The
      put-back check's 'covered again' case failed with "left on screen, as Designer became the active app during the
      shot". Both passed after the fix: plainly, judged as before, and activated, the put-back not judged.
    - **Cause:** both checks expected the put-back the shot makes when Designer stays inactive.
    - **Fix:** `window_states.became_active(said, before, after)` tells the case apart. Either the shot said it left
      the window up for that, or Designer is the active app after the shot and wasn't just before it. `during_pan` now
      prints the state first (BEFORE). In that case check 4 judges only the pan, and the put-back check judges nothing,
      and each says "not judged: Designer became the active app during the shot". Their docstrings say so.
    - **Also covered:** check 2 still judges focus where it can (TST-392), so a shot that made Designer the active app
      itself fails there. What made Designer the active app in the full run stays unverified.

- [x] **TST-400 · Two lifecycle checks expect the sample of a Designer stuck in its shutdown to show the thread pool's wait, and its shutdown can still be at Adobe's sign-in stop before it** · `tests/test_all_tools/lifecycle/checks.py:613-618,687-692` · measured · found 2026-11-14
  - **Defect.** "samples one stuck in its shutdown before forcing it, the thread pool's wait shown" (quit_designer, after
    its 15 s wait) and "samples the agent's Designer it ends before forcing it, the thread pool's wait shown"
    (launch_designer) assert `'QThreadPool::waitForDone' in stacks`. Designer's shutdown first stops Adobe's sign-in
    (`NglSSOHandler::Stop`), and only then waits for the pool that `hold_thread_pool` keeps. The checks are `main`'s
    code, unchanged on this branch. Found by the branch's third final check.
  - **Scenario.** Measured. In that full run (723 of 724 live checks), launch_designer's sample showed the main thread
    in `std::condition_variable::wait < ... < adobe::ngl::internal::NglSSOHandler::Stop`, and no pool wait, so the
    check failed; it passed in the two runs before. In a probe in a Designer an agent started, idle, with the pool
    held, the main thread was seen in the sign-in stop 1.5 s into the shutdown, both after its windows were closed and
    after quit_designer's close. From 4 s on it sat in `QThreadPool::waitForDone`, 40 s long. Beside the full run's
    other Designers, the sign-in stop can last longer than the checks wait, and then either check fails while the tool
    did as it should.
  - **Fix.** Both checks accept the main thread at either of the shutdown's measured waits, the sign-in stop or the
    pool's wait. The criterion goes in `lifecycle/samples.py`, with a unit test, and `server_tools/lifecycle.py`'s
    docstring states both. Settled by the full run's output and the probe.
  - **Resolution: done.**
    - **Test:** `test_selftest_lifecycle.py::test_a_sample_shows_designer_at_one_of_its_shutdowns_waits` (the pool, the
      sign-in stop, a running Designer, no sample) failed first: there was no `in_shutdown`. The full run's case can't
      be made on demand; the probe above saw the sign-in stop only 1.5 s in. `lifecycle` passed whole in a scratch run
      on a port of its own, 52 checks, both sample checks showing the pool's wait.
    - **Cause:** the checks knew only the last of the shutdown's two waits.
    - **Fix:** `lifecycle/samples.py`'s `in_shutdown` accepts `SHUTDOWN_WAITS`, the sign-in stop and the pool's wait,
      and both checks use it; their labels say "its shutdown's wait shown". `server_tools/lifecycle.py`'s docstring
      states both waits.
    - **Also covered:** nothing else reads a sample's stacks for a wait: `sampled` and `main_thread` only report
      them.

- [x] **SRV-148 · A Designer launch_designer starts becomes the active app and keeps it: it takes the user's keyboard, and in the pool activation passes between agents' Designers as they quit** · `mcp_server/server_tools/lifecycle.py:876-891` · measured · found 2026-11-14
  - **Defect.** Once its Designer answers, `launch_designer` turns its crash uploads off and closes the Home screen, and
    returns. A Designer started that way becomes the active app as it starts, the one the keyboard types into, and
    nothing gives that back. The launch is `main`'s; the branch's window checks showed it.
  - **Scenario.** Measured, in a probe with two Designers an agent started, the front app read with macOS's
    `lsappinfo`:
    - before any launch, the user's app was in front;
    - Designer A, launched, was in front, and so was B, launched after it;
    - B quitting handed activation back to A;
    - A, hidden and then shown without being made active, gave it back to the user's app;
    - B, launched again and doing the same, gave it back too, and its quit then left the user's app in front.

    So every launch takes the user's keyboard; the lead saw it three times that day, typing going into an agent's
    Designer. In the full run, four Designers at once pass activation around as they start and quit. Activating
    Designer brings its windows in front of others, which is what failed the branch's window checks:
    - TST-399's check 4, the window found active and in front of its cover;
    - in the fourth final check, check 3 ("a render that didn't follow a pan is said"): its window, covered for the
      shot, rendered the pan.
  - **Fix.** Once its Designer answers, `launch_designer` has it give activation back if it holds it: hidden, then
    shown without being made active, as measured. Its result says so. A unit test of the helper, one of the launch,
    and a lifecycle live check that a Designer just launched isn't the active app. Settled by the probe above.
  - **Resolution: done.**
    - **Test:** `test_mac_window.py` (4 tests of the helper: Designer the active app gives it back, one that isn't is
      left alone, nothing off macOS, one still active after says so) failed first, as there was no helper.
      `test_lifecycle_env.py::test_a_designer_started_gives_the_keyboard_back_once_its_home_screen_is_closed` failed
      with the launch making only the Home screen's call. Live, lifecycle's new check "leaves the app in front before
      it the active app, not the Designer it started" failed in a scratch run of the whole category with
      `ACTIVE=True`, the only failure of 53. With the fix the whole category passed, 53 checks, each launch saying "gave
      the keyboard back to the app in front before it".
    - **Cause:** nothing gave back the activation a Designer takes as it starts.
    - **Fix:** `give_back_activation()` (`designer_helpers/mac_window.py`) hides Designer and shows it again without
      making it active, when it is the active app. `launch_designer` calls it once the Home screen is closed, and adds
      its line to the result's parenthesis. The measured facts are in `mac_window.py`'s docstring; the tool's
      docstring says it.
    - **Also covered:** only a Designer the call started gets it: one found running is left as it is. TST-399's "not
      judged" stays, for a click into Designer during a shot. The start checks' regex on the parenthesis still
      matches.

- [x] **HLP-133 · While the shot runs, Designer's transparent window still counts as covering the windows under it** · `mcp_server/designer_helpers/shot3d.py:184-187` · measured · found 2026-11-14
  - **Defect.** `_bring` makes the window transparent and click-through (`self._fade(...)`, then `mac.show()`), but
    macOS still reports the windows under it as covered: the user sees them, their apps are told they can't be seen.
  - **Scenario.** Probe: a window of Designer's own, fully under the main window, read `occlusionState` as covered
    with the main window opaque, and still covered with it at opacity 0, click-through or not. During a 3D shot of a
    minimized, covered or hidden Designer (one to several seconds), the user's windows under that area are told they
    are covered: apps that stop drawing covered windows (browsers, video players) may freeze on screen, then catch up.
  - **Fix.** Measure first whether the window also marked non-opaque while transparent (`setOpaque:` NO, put back
    after) stops covering what is under it, and use that if it does. If not, keep it covering as little as possible
    (the first probe of this feature drew the view with all but 6 px of the window off the screen), or say the side
    effect in DECISIONS.md and README: the user's choice, as it changes what they see.
  - **Resolution: done**, as the user chose: said, not changed.
    - **Test:** `check_a_window_under_designers_transparent_window_still_counts_as_covered` ("designer facts"), passing
      in its scratch run (`opaque=True transparent=True`). A probe first marked the window non-opaque too
      (`setOpaque:` NO): it still reported itself opaque, the window under it was still covered, and the view drew.
    - **Cause:** macOS counts a window under one in front as covered whatever the front window's opacity, and
      `setOpaque:` NO doesn't take on Designer's window.
    - **Fix:** none in the shot. The user chose "Document it (Recommended)" (2026-11-14) over moving the window mostly
      off screen for the shot. README's 3D bullet says apps under it may pause drawing, DECISIONS.md's entry records it
      (with its Reopen if), and `shot3d.py`'s docstring has the measured fact.
    - **Also covered:** GUIDE.md and the tool's docstring are unchanged: an agent has nothing to do about it.
  - Questioned by TST-408 (2026-11-14), and by TST-412 and HLP-141 (2026-11-14).

- [x] **HLP-134 · With `graph=`, the Explorer's context menu shows on the user's screen during an otherwise invisible shot** · `mcp_server/designer_helpers/view3d.py:236-273` (`_apply_outputs`), `mcp_server/designer_helpers/shot3d.py:92-110` (`_Screen`'s docstring) · measured · found 2026-11-14
  - **Defect.** The set-up opens Designer's own context menu on the graph's Explorer row
    (`app.sendEvent(viewport, event)  # returns once the menu has closed`). The menu is a new popup window, made after
    `_fade` ran, so it shows at full opacity above every app's windows, while the docs say the user sees none of the
    shot (`_Screen`: "so the user sees none of it"; the tool's docstring: "transparent so the user doesn't see it").
  - **Scenario.** Probe: Designer's window minimized, `shoot_3d(path, graph=...)`, a 20 ms timer listing Designer's
    visible windows other than the main one: a `QNSPanel` at level 101 (popup menus) at opacity 1, on screen on three
    ticks. The user sees a context menu flash where the Explorer would be; Designer stayed not the active app.
  - **Fix.** Make the menu transparent as soon as it exists (the timer that picks its action finds it), and measure
    how long it still shows; if a flash remains, say so in the docs and DECISIONS.md, for `graph=` only.
  - **Resolution: done.**
    - **Test:** `check_a_3d_shot_with_graph_keeps_the_explorers_menu_off_the_screen`: a watch of the window server's
      list from the self-test's own process (`editor_panels_and_fit/popups.py`, unit-tested in
      `test_selftest_popups.py`). In the scratch run it failed before the fix (Designer's popups on screen for 237 ms,
      in 818 of 13360 samples) and passed after (0 ms, in 0 of 13348). Unit tests in `test_view3d_helpers.py`, failing
      before (no fade, two timers): `test_the_menu_is_made_transparent_once_it_opens`,
      `test_a_popup_open_before_the_menu_isnt_made_transparent`,
      `test_the_menu_opened_is_made_transparent_before_its_action_is_picked`, and the timers' tests with a third timer
      (an abort as it starts too).
    - **Cause:** the set-up opens a new popup after the shot made Designer's windows transparent, and the pick closed
      it 100 ms later, after it had been on screen about 240 ms.
    - **Fix:** `_apply_outputs` starts a third timer at 0 ms (`_MenuPick.fade`), which makes the menu opened since
      transparent (`setWindowOpacity(0)`), starting again until it opens; parented and stopped like the other two.
      Measured first, three shots each: picked at 100 ms, 240 ms on screen; picked at 0 ms, about 155 ms (the menu stays
      while its action runs); made transparent at 0 ms, 0, 9 and 0 ms. `view3d.py`'s docstring has them.
    - **Also covered:** the set-up's other steps open no window: the Scene and Camera menus are triggered as actions,
      filled by `aboutToShow`, never shown; tiling goes through the Parameters panel; the render through its action.
      Every window check sets `graph=` up first, and all passed with the menu transparent.
  - Questioned by TST-405 and TST-406 (2026-11-14), and by HLP-144 (2026-11-14).
  - Note (2026-11-14): on macOS the menu is made click-through too, the user's choice after the second review left
    it under **Not verified** (DECISIONS.md). `_MenuPick.fade` sets Qt's `WindowTransparentForInput`, which
    `test_the_menu_made_transparent_lets_clicks_through_on_macos` checks. The live
    `check_a_3d_shot_with_graph_makes_the_explorers_menu_click_through` failed in its scratch run before the change
    (`through=False`) and passed after, the shot taken.

- [x] **TST-401 · The "transparent in front" designer fact uses an always-on-top cover and never reads the window's state** · `tests/test_all_tools/editor_panels_and_fit/window_states.py:68-80`, `tests/test_all_tools/editor_panels_and_fit/checks.py:654-692` · confirmed · found 2026-11-14
  - **Defect.** `_PUT` makes the cover with `window(..., way != 'covered')`, so 'transparent in front' gets an
    always-on-top cover (layer 8), which `mac.show()` doesn't bring Designer's window in front of. The check then
    reads only `states['minimized']`: neither that the window was in front nor that it was transparent.
  - **Scenario.** The fact passes with the window still under its cover, or with `set_appearance` doing nothing (an
    opaque window in front draws too). Its docstring, `window_states.py`'s and `shot3d.py`'s module docstring ("the
    self-test re-measures ... the second") claim a transparent window in front.
  - **Fix.** Give that way a normal cover (always on top only for `ON_TOP`), and have the check read its STATE:
    `opacity=0`, `through=True`, `covered=False`, `main` ahead of `cover` in `order`.
  - **Resolution: done.**
    - **Test:** the facts check now reads the transparent way's state. In the scratch run it failed before the fix
      (`covered=True`, `order=cover,main,below`: under the always-on-top cover) and passed after (`opacity=0`,
      `through=True`, `covered=False`, `main` ahead of `cover`).
    - **Cause:** `_PUT` gave every way but 'covered' an always-on-top cover (`way != 'covered'`), and the new way went
      into that branch.
    - **Fix:** the cover is always on top for `ON_TOP` alone, and the check reads opacity, click-through, covered and
      the order.
    - **Also covered:** 'covered' and `ON_TOP` keep their covers; `hits()` uses `put('covered')`.

- [x] **TST-417 · Three designer facts read Designer's windows as if no other app's window could come in front, and fail in the full run when one does** · `tests/test_all_tools/editor_panels_and_fit/checks.py:654-760`, `tests/test_all_tools/editor_panels_and_fit/window_states.py` (`_HITS`, `_UNDER`, `panned`) · measured · found 2026-11-14
  - **Defect.** The click fact (`_HITS`) and the window-under fact (`_UNDER`) read with Designer's window, or the
    window under it, brought in front. The not-drawn fact's drawn ways need Designer's window drawn. Each reads once,
    so a window of another app coming in front during the readings changes them, and the check fails though Designer
    behaved as the fact says. The first two facts are new on this branch, and so is the not-drawn fact's transparent
    way (TST-401).
  - **Scenario.** Measured in the branch's final check, 731 of 735 live checks, four Designers at once. The click fact
    read `opaque=another transparent=another through=another`: a window the check didn't make was at the middle of
    Designer's window. The window-under fact read `alone=True opaque=True transparent=True`: the window under was
    covered even alone. Both passed in two scratch runs right after. The pool's other Designers come in front and
    take activation as they start (mac_window.py's docstring), and the user's own windows may come in front too. The
    not-drawn fact passed in that run, but another app's window over Designer's during its drawn ways would stop the
    drawing.
  - **Fix.** Each reading also notes the windows in front of the window it reads, other than those the check put
    there (`in_front()`). A try with one is taken again, up to three tries, and the check fails, saying so, when no
    try was clear. Scratch: a window brought in front of the read window right after it is shown, in the first try
    only, then in every try.
  - **Resolution: done.**
    - **Test:** in their scratch run, a window the checks didn't make, brought in front of the window read right after
      it was shown (scratch only), gave the full run's readings: `opaque=another transparent=another
      through=another`, `alone=True opaque=True transparent=True`, and the not-drawn fact's 'on screen' way not drawn.
      All three facts failed. After the change, with that window in the first try only, all three pass, saying "2
      tries". With it in every try, all three fail: "another app in front in each of 3 tries". Unit test:
      `test_a_reading_is_clear_only_when_no_window_was_found_in_front`, failing before `nothing_in_front` existed.
    - **Cause:** each fact read once, with nothing to tell whether a window had come in front of the window it read.
    - **Fix:** the snippets print `IN_FRONT n`: the windows found in front of the window read, at each reading, but
      those the checks made (`in_front_of` in `_WINDOW`, through `_MacWindow.in_front`). The checks take a reading
      again while one was found, up to three tries (`retries.without_others_in_front`, a module of its own), and fail
      when no try was clear. The not-drawn fact does so for its drawn ways only: another window can't make an
      off-screen way draw.
    - **Also covered:** the other window checks of the category, searched for a reading another app's window could
      change. The put-back, transparency, HLP-124 and HLP-136 checks don't judge when Designer becomes the active app
      (TST-399, TST-410), and they read only Designer's own windows' order. The focus check is TST-418.
  - Note (2026-11-14): the branch's second final check failed two of these facts again (733 of 735 live checks):
    - the not-drawn fact found another app's window in front of Designer's in all three tries of each of its drawn
      ways;
    - the click fact's second try found none in front, yet its click-through reading reached "another" window.
      `in_front_of` counts normal windows only (layer 0), and a window at another level, most likely the splash
      screen of a Designer starting, is missed.
  - **Resolution: done** (after the second final check).
    - **Test:** `test_the_window_checks_the_pool_disturbed_read_while_no_designer_starts`, for the three facts and the
      focus check, failed before the change: none held the pool's launch lock. A scratch run can't show the lock at
      work, as outside a pool it holds nothing; the four checks still pass there. The final check is what shows it.
    - **Cause:** the retries met the windows of a Designer starting, splash screen included, for longer than three
      tries; the splash screen isn't a normal window, which `in_front_of` counts.
    - **Fix:** the four checks read while holding the pool's launch lock (`retries.no_designer_starting`, through
      `launch_lock.held`, as lifecycle holds it). No Designer of the run starts or quits meanwhile, so none brings
      windows in front or hands activation over. The retries stay, for the windows the lock doesn't stop: the
      user's, and another Designer's own work.

    The windows the pool's Designers bring as they start come in bursts longer than three tries.

- [x] **TST-418 · The focus check blames the shot for activation the pool hands to Designer, before or during the shot** · follows TST-392 and TST-399, generation 3 · `tests/test_all_tools/editor_panels_and_fit/checks.py:844-900`, `tests/test_all_tools/editor_panels_and_fit/window_states.py` (`focus`) · measured · found 2026-11-14
  - **Defect.**
    - `kept = window_states.focus(before, state)` compares the state after the shot with the one read before `put`
      sent the window off screen. Designer made the active app between that set-up and the shot is blamed on the
      shot.
    - Designer made the active app from outside during the shot makes the shot leave its window up (HLP-125). The
      check then fails on focus and on the state after, though the shot did what it should. TST-399 made the
      during-pan checks not judge then; this check still judges, to catch a shot that takes focus itself.
  - **Scenario.** Measured in the branch's final check:
    - covered: active=False before, active=True off screen and after; it failed on focus alone, the window put back
      behind its cover;
    - hidden: active=False before and off screen; the shot said "made opaque at once, as Designer became the active
      app during the shot" and "left on screen ..."; active=True after; it failed.
  - **Resolution: done** (generation 3: a smaller claim).
    - **Test:** in its scratch run, the state line read Designer as the active app from the moment the covered window
      was set up (scratch only). The covered way failed before the change, as in the full run (active=False before,
      True off screen and after). It passes after, focus not judged. Unit test:
      `test_designer_made_the_active_app_during_a_shot_is_told_from_the_shot_and_the_states`, failing before
      `activated` existed. Making Designer the active app for real during a shot would take the user's keyboard, so
      the retry is seen only in the unit test and passing live.
    - **Cause:** focus was judged against the state before `put`, and a Designer made the active app from outside
      during the shot, which then leaves its window up, failed the way.
    - **Fix:** focus is judged from the state just before the shot (`off`). A way in which the shot says Designer
      became the active app, or focus was lost, is taken again, up to three tries (`window_states.activated`). It
      fails when every try was so, saying so. `MADE_OPAQUE` and `LEFT_UP` moved to `window_states`.

    Hiding Designer hands activation to the app active before it. If that is another of the pool's Designers and it
    quits during the shot, it hands activation back to this one (mac_window.py's docstring). Both passed in two
    scratch runs right after.
  - **Fix (generation 3: a smaller claim).** Judge focus from the state just before the shot (`off`). Take a way
    again, up to three tries, when the shot says Designer became the active app during it or focus was lost: a shot
    that takes focus itself does so every time, and fails. Unit tests for the decision. Live, the state's `active`
    reading rebound after `put` (scratch only) for the first part; making Designer the active app for real during the
    shot would take the user's keyboard.

- [x] **HLP-146 · An Explorer menu closed before its action is picked is said not to have opened, and is left transparent and click-through** · `mcp_server/designer_helpers/view3d.py:168-235,280-310` (`_MenuPick`, `_apply_outputs`) · measured · found 2026-11-15
  - **Defect.** `_MenuPick.fade` makes the menu transparent and click-through at the fade timer's first tick (0 ms);
    `pick` first looks at 100 ms. A menu closed by something else in between is never picked: `failure()` says
    "didn't open", since `menus` counts only what `pick` saw. Nothing gives the closed menu its look back.
  - **Scenario.** Measured. In the branch's third final check, the transparency check's own set-up shot with `graph=`
    was refused with "the Explorer's menu for graph mcp_selftest_view3d didn't open". From then on Designer had a
    fifth window, not opaque and clickable, and all four of the check's cases failed on it (`faded=1`). In a scratch
    run, closing the menu right after the fade (`_MenuPick.fade` rebound in the snippet alone) gave the same: the
    refusal, then 5 windows, one a hidden `QNSPanel` at (0.0, True). It stayed after the Explorer's next menu in one
    run, and was gone after it in another. That next menu, opened as a user's right-click would get it, was opaque and
    clickable. So the user isn't left an invisible menu, but the shot misreports what happened and leaves a window of
    Designer's transparent and click-through. What closed the menu in the full run wasn't seen; a change of the
    active app, which the pool's Designers cause, closes popups.
  - **Fix.** Once the menu is closed, give the menu the fade changed its look back, if it still exists. Say the menu
    closed before its action was picked when the fade saw one that the pick didn't. Test: a unit test with the menu
    closing between the fade and the pick, and a live check closing it so, both seen failing first.
  - **Resolution: done.**
    - **Measured first:** the menu closed between the fade and the pick is deleted by the Explorer before the shot
      returns ("Internal C++ object (PySide6.QtWidgets.QMenu) already deleted"), and its window stays (`QNSPanel`,
      (0.0, True), hidden). So the look can't be given back through Qt, only to the window.
    - **Test:** `check_an_explorers_menu_closed_before_its_pick_is_said_so_and_gets_its_look_back`, new, closes the
      menu from a timer as soon as the fade made it transparent. In its scratch run it failed before the fix: "didn't
      open", and the menu's window at (0, True); the transparency check after it failed all four cases, as in the
      final check (`faded=1`). Both pass after it. Unit tests, failing before:
      `test_a_menu_closed_before_its_pick_is_said_so_and_its_window_gets_its_look_back` (macOS and Windows) and
      `test_a_menu_picked_has_its_window_given_its_look_back_once_closed`.
    - **Cause:** the fade changed the menu's window and nothing changed it back. The Explorer deletes the menu as it
      closes, and the window of one closed that way was kept. `failure()` counted only the menus the pick saw.
    - **Fix:** on macOS the fade holds the menu's window before changing it, and `_apply_outputs`' `finally` gives
      it its look back once the menu closed, then lets go (`_MenuPick.unfade`). A menu the fade saw and the pick didn't
      is said to have closed before its action was picked. Off macOS the menu is only made transparent, and nothing
      was measured there. The module docstring has the measurement.
    - **Also covered:** a menu picked as usual gets its window's look back too. The shots of Designer's own windows
      already give each window its look back (`_Screen.unfade`).

## Low

- [x] **SRV-127 · A Designer that starts during a put-back has its first writes overwritten** · `designer_preferences.py:197,219-228` · confirmed · found 2026-11-13
  - **Defect.** `running()` is asked once, before the deletes (about 7 ms each) and the import of the whole copy.
  - **Scenario.** The user opens their Designer while `quit_designer` puts the file back after a run that added a few
    hundred keys: their Designer reads a half-restored file and writes its start keys, which the import then overwrites;
    the read-back mostly catches it and keeps the copy, which the user's log then drops.
  - **Fix.** Ask `running()` again before the import (and every so many deletes); if a Designer appeared, stop, keep
    the copy, and say so.
  - **Resolution: done.**
    - **Test:** `test_a_designer_starting_during_a_put_back_stops_it_and_keeps_the_copy` (the import ran) and
      `test_a_designer_starting_during_many_deletes_stops_them_soon` (all 150 deletes ran) failed.
    - **Cause:** `running()` was asked once, before the deletes.
    - **Fix:** asked again every `RECHECK_EVERY` (50) deletes and before the import; a Designer found stops the put-back,
      the copy kept, "a Designer started meanwhile".
    - **Also covered:** the window left between the last look and the import's end is about one `defaults` call.
  - Questioned by SRV-139 (2026-11-13).
  - Questioned by SRV-145 (2026-11-13).

- [x] **SRV-128 · A put-back that worked, or a copy dropped on purpose, is reported as "couldn't be put back" when only the copy's removal fails** · `designer_preferences.py:176-180,200,231` · confirmed · found 2026-11-13
  - **Defect.** `_put_back_or_say` turns any OSError into `_not_put_back`, including `os.remove(path)` after a
    successful import and read-back, and after deciding to leave the file as the user's.
  - **Scenario.** The copy can't be removed (an immutable flag, permissions): `quit_designer` says the file couldn't
    be put back and the copy is kept, though the file was put back (or deliberately left).
  - **Fix.** Catch the removals' OSError on their own and say what was done and that the copy stays.
  - **Resolution: done.**
    - **Test:** `test_a_copy_that_cant_be_removed_doesnt_unsay_what_was_done[put back|dropped]` failed ("couldn't be put
      back").
    - **Cause:** one `except OSError` around the whole put-back, the copy's removals included.
    - **Fix:** `_dropped()` removes the copy after the outcome is decided, adding "The copy ... couldn't be removed (...):
      the next call removes it." to what was done; the next call finds the file unchanged and removes it.
    - **Also covered:** both removals (put back, dropped as the user's or too old) go through `_dropped`; the unreadable
      copy's removal stays a failure, as nothing was put back.
  - Questioned by SRV-137 (2026-11-13).

- [x] **SRV-129 · launch_designer drops what the save said on several paths** · `mcp_server/server_tools/lifecycle.py:345,740-760,787,798,803` · confirmed · found 2026-11-13
  - **Defect.** `told()` ("What comes before the result or the error") replaced `note` only in the result, the
    timeout and the two `_unrecorded` raises after a start; a restart's `start()` still raises with `note` ("Designer not
    found", `_users_next_to`, `_unusable_port`, `_unrecorded(..., 'No Designer was started')`), as do the refusal after a
    start (`_with_uploads_off`), a failing `leave_home_screen` and `return note + _already_running(...)`; and a
    `ToolError` from `_started` inside `saved()` loses `said` altogether. Two reviewers found it.
  - **Scenario.** The first start says "Designer's preferences couldn't be saved first: this Designer's changes to them
    won't be put back", that Designer exits, and the restart is refused: the agent never sees the warning; or a copy
    left behind is put back and Popen fails: the error doesn't say the user's file was just rewritten.
  - **Fix.** Use `told()` wherever `note` is used once a start may have run; prefix `said` to a ToolError from
    `_started`; a unit test for a path besides the timeout.
  - **Resolution: done.**
    - **Test:** `test_a_launch_that_fails_once_started_still_says_what_its_save_did[a refusal|the Home screen failing]`
      and `test_a_launch_whose_designer_cant_be_started_still_says_what_its_save_did` failed;
      `test_a_launch_it_couldnt_record_still_says_what_its_save_did` guards the `_unrecorded` raises (TST-358).
    - **Cause:** `told()` replaced `note` only where it had been written in the first fix.
    - **Fix:** the refusal in the wait (still a `_Refused`), a failing `leave_home_screen`, `_already_running` and every
      raise of `start()` carry `told()`; `_start_designer` prefixes what the save said to a `ToolError` from `_started`.
    - **Also covered:** the restart path the finding described can't carry a save's line: after this call's own start
      `running` is False and no second start follows (read in the loop), so only the paths above can.
  - Questioned by SRV-145 (2026-11-13).

- [x] **SRV-130 · Some ends of an agent's Designer get no put-back after them** · `mcp_server/server_tools/lifecycle.py:735,789,744-760,967-975` · confirmed · found 2026-11-13
  - **Defect.** `launch_designer` can end a Designer (`_end_if_past_startup`) and then raise in `start()` before
    `saved()` runs (not found, port unusable, record unwritable); `_quit`'s wait raising `_NoListing` after its close
    skips the put-back that follows it.
  - **Scenario.** A launch ends an agent's hung Designer, then refuses because another program took the port: none
    runs, but the copy stays; the user opens their Designer next, gets the agent's layout, and their log then makes
    the agent's changes permanent (the copy is dropped).
  - **Fix.** When a launch has ended a Designer and raises before starting another, put back and prefix the sentence;
    in `quit_designer`, try the put-back on that path too (an unlistable state already counts as running).
  - **Resolution: done.**
    - **Test:** `test_a_launch_that_ended_a_designer_and_starts_none_puts_back_first` (an agent's hung Designer ended,
      then the port taken) failed: the file left changed.
    - **Cause:** only `saved()` and `quit_designer` put back; a launch refusing after its end reached neither.
    - **Fix:** `start()`'s refusals take `refusing()`: when this call ended a Designer, a put-back (`ended=True`) first,
      its sentence in the error.
    - **Also covered:** `_quit`'s wait raising `_NoListing`: a put-back there can't run, as the same pgrep failure
      counts as a Designer running; the next call puts back.
  - Questioned by SRV-135 (2026-11-13).

- [x] **SRV-131 · A copy the user's Designer has made useless is kept silently while later agents' Designers add changes nothing will put back** · `designer_preferences.py:117-145,197-199`, `mcp_server/server_tools/lifecycle.py:934-936` · confirmed · found 2026-11-13
  - **Defect.** Once the user's log is newer than the copy, the copy can only be dropped; but `saved()` keeps it while
    any Designer runs, and the put-back says nothing while one runs.
  - **Scenario.** A copy made at T0; the user opens and quits their own Designer while agent A's runs; agent B starts
    after: B's changes pile on the file, and at the last quit the copy is dropped, nobody having been told along the way
    that the agents' changes stay.
  - **Fix.** The user's choice: in `saved()`, when a launch goes ahead (so the user's Designer doesn't run) and the
    copy predates the user's log, replace it with a fresh export, so the final put-back keeps the user's run and undoes
    the later agents'; and say in the put-back's sentence when a copy is doomed.
  - **Resolution: done** (the user's choice, 2026-11-13: save again).
    - **Test:** `test_a_start_after_the_users_designer_ran_saves_the_file_again` failed: the old copy kept, and B's change
      later dropped with it.
    - **Cause:** `saved()` kept any copy while a Designer ran.
    - **Fix:** `saved()` makes the copy again when the user's log is newer than it (a start goes ahead only with the
      user's Designer closed, so the file holds their run), saying "Designer's preferences saved again: ..."; the final
      put-back then keeps the user's run and undoes the later agents'.
    - **Also covered:** a copy dropped by the put-back in `saved()` (none running) is saved afresh as before.

- [x] **SRV-132 · Where the put-back is told to agents: launch_designer's docstring is silent, quit_designer's repeats the guide, and neither says when the file is left** · `mcp_server/server_tools/lifecycle.py:702-719,932-933`, `mcp_server/GUIDE.md:117-119`, `README.md:52` · confirmed · found 2026-11-13
  - **Defect.** A tool's behaviour lives in its docstring (AGENTS.md): `launch_designer`'s says nothing of the save or
    of the line its result can start with; `quit_designer`'s repeats the GUIDE bullet and points back at it; neither
    they nor GUIDE.md give the exception (the file left when the user's Designer ran since); README's row leaves out the
    next launch's put-back. Two reviewers found it.
  - **Scenario.** An agent reading `launch_designer`'s result "Designer's preferences put back ..." has no word for it in
    the tool's description; one told "put back as it was before" expects it after the user's own run too.
  - **Fix.** One short clause in each tool's docstring for its own part, "unless the user's Designer ran since"
    included; GUIDE.md keeps one line and the path, without repeating them.
  - **Resolution: done.**
    - **Test:** docs; the docs' tests pass.
    - **Fix:** `launch_designer`'s docstring: it saves the plist first and when a line comes before its result;
      `quit_designer`'s: it puts it back once none runs, unless the user's Designer ran since, and the result says which,
      without the pointer to the guide; GUIDE.md keeps one line and the paths; README's row names the next launch or quit.
  - Questioned by TST-366 (2026-11-13).

- [x] **INS-34 · uninstall reports the copy's fate wrongly in two cases, and leaves or races on its files** · `uninstall.py:181-209`, `README.md:388-391` · confirmed · found 2026-11-13
  - **Defect.** `put_back_preferences` returns `Kept(said)` whenever the copy is gone, so a copy dropped (the user's
    Designer ran) prints "Removed the copy ..., put back first: ... (Designer's preferences left as they are ...)", and an
    unreadable one "... (couldn't be put back ...)" as a success; an OSError other than FileNotFoundError removing the lock
    after a put-back that worked prints "Could not remove"; a `.plist.new` a save cut short left (0600, the user's
    preferences) is never removed; a lone lock while a Designer runs is neither removed nor listed as kept, though
    README says what is kept is listed, and README doesn't name the lock. Two reviewers found it.
  - **Scenario.** The user uninstalls after opening their own Designer since an agent's run: the output says the copy
    was "put back first" and, in the same line, that the file was left.
  - **Fix.** Label the item "put back first, unless your own Designer ran since"; return the unreadable case as an
    error; suppress OSError on the lock's removal; remove `.new` with the copy; list a kept lock; name the lock in README.
  - **Resolution: done.**
    - **Test:** `test_uninstall.py`: `test_a_copy_dropped_as_the_users_says_so`, `test_says_when_designers_preferences_couldnt_be_put_back[copy unreadable]`,
      `test_lists_the_lock_of_designers_preferences_kept_while_a_designer_runs`, `test_a_lock_that_cant_be_removed_after_a_put_back_is_no_failure`
      and the `.new` in `test_puts_designers_preferences_back_and_removes_their_copy` failed;
      `[a Designer started meanwhile]` guards `said or 'a Designer runs'` (TST-358).
    - **Cause:** the action judged success by the copy being gone, and the items covered the copy, not its other files.
    - **Fix:** `put_back` returns `Said`, its `failed` set when nothing was put back nor left on purpose, which the
      action reports as an error; the label "put back first unless your own Designer ran since"; `.new` and the lock
      removed with `OSError` ignored; a lone lock while a Designer runs listed as kept; README names the lock.
  - Questioned by INS-35 (2026-11-13).

- [x] **TST-357 · The pool's preferences check fails falsely when an agent's Designer outside the run, open at its start, ends during it** · `tests/test_all_tools/workers.py:315-327,367-374` · confirmed · found 2026-11-13
  - **Defect.** `preferences_before` reads the file as it is, while the copy kept from before that outside Designer
    (which the run's last quit puts back) lacks that Designer's own changes.
  - **Scenario.** An `alone.run` Designer is left open (its launch saved copy C0, it changed the file to F1); a full run
    starts (`before` = F1; its launches keep C0); the outside Designer is quit mid-run (its put-back sees the run's
    running); the run's last quit puts C0 back: the check compares C0 with F1 and fails, though the file is as before
    any agent's Designer. (Still running at the end, it skips, rightly.)
  - **Fix.** In `preferences_before`, after its put-back, read `before` from the copy when one is still kept; a pool
    unit test of this case.
  - **Resolution: done.**
    - **Test:** `test_selftest_pool.py::test_the_check_compares_with_the_copy_kept_for_a_designer_outside_the_run`
      failed (FAIL: the instancePID of the outside Designer).
    - **Cause:** `before` was the file, not what the run's last quit would put back.
    - **Fix:** `preferences_before` reads the copy when one is still kept after its own put-back, the file otherwise.
  - Questioned by TST-367 (2026-11-13).

- [x] **TST-358 · Branches and mutations no test pins** · `designer_preferences.py`, `mcp_server/server_tools/lifecycle.py:773,775`, `uninstall.py:181-209`, `tests/test_all_tools/workers.py:347,368` · confirmed · found 2026-11-13
  - **Defect.** Each of these changes passes every test: `saved()` and `put_back()` when `_lock()` raises; `_put_back_or_say`
    when `os.remove` raises; `_save` without `_keys(data)` or without removing a leftover `.new`; `saved()` joining a
    put-back sentence with a not-saved one; a put-back whose export or delete fails; `put_back`'s platform gate (the
    off-macOS test never has a copy, so it returns at the existence check anyway); `told()` reverted to `note` in either
    `_unrecorded` raise; uninstall's lone lock while a Designer runs (`if in_use: return []`: removing it unlinks a lock
    a launch may hold) and `return said or 'a Designer runs'`; the pool check's reference time (every pool test's log
    is newer than `at`, so `users_log_time() > 0` passes; on the user's machine the check would then always skip) and its
    removed-key branch (no test removes a key during a run).
  - **Scenario.** One of these regresses and nothing fails; for the reference time, the end check stops checking.
  - **Fix.** One small unit test each (`monkeypatch` `_lock` or `os.remove` to raise, `fail['export']`/`fail['delete']`
    during a put-back, a `.new` left, a copy present off macOS); pool tests with the user's log older than the run's
    start and a file left changed (a FAIL, not a SKIP), and with a key removed during the run.
  - **Resolution: done.**
    - **Test:** new unit tests, each judged by reading to fail against its mutation: `test_a_lock_that_cant_be_opened_is_said`,
      `test_a_put_back_whose_read_or_delete_fails_keeps_the_copy[export|delete]`, `test_an_export_that_isnt_a_plist_is_not_saved`,
      `test_a_save_cut_short_leaves_nothing_in_the_next_ones_way`, `test_a_start_says_both_a_put_back_and_a_save_that_failed`,
      `test_off_macos_a_copy_left_is_not_put_back`, `test_a_launch_it_couldnt_record_still_says_what_its_save_did`, uninstall's
      lone-lock and `[a Designer started meanwhile]` tests, and in the pool `test_the_preferences_check_still_fails_with_a_users_log_from_before_the_run`
      and a key removed in `test_the_pool_checks_designers_preferences_are_as_before_it[left changed]` ("2 values changed").
      Those for code already right passed at once; the others failed first (SRV-128, INS-34).
  - Questioned by TST-368 (2026-11-13).

- [x] **TST-359 · The live-check skill doesn't know the new check or the new module** · `.claude/skills/live-check/SKILL.md:76,86` · confirmed · found 2026-11-13
  - **Defect.** "What the pool's parent checks" lists `check_the_quits`, the coverage and the unit suite, not
    `check_the_preferences`; the list of code the live self-test reaches leaves out `designer_preferences.py`, which the
    server and the pool's parent both run.
  - **Scenario.** The final check's unit suite fails and the fix touches only `designer_preferences.py`: by the skill,
    only the unit suite runs again, though launches and quits changed.
  - **Fix.** Add both.
  - **Resolution: done.**
    - **Fix:** the live-check skill lists `check_the_preferences` among the pool parent's checks (`--only` runs it too)
      and `designer_preferences.py` among the code the live self-test reaches.

- [x] **TST-360 · Nothing keeps a unit test from reaching the real `defaults` if a call bypasses `run_defaults`** · `tests/unit/conftest.py` (the `defaults` fixture), `tests/unit/test_designer_preferences.py:241-248` · confirmed · found 2026-11-13
  - **Defect.** The fixture replaces `run_defaults` only; `DEFAULTS` stays `/usr/bin/defaults`, and no test asserts the
    fake is in place (as `test_no_unit_test_sees_a_designer_really_running` does for pgrep).
  - **Scenario.** A later change calling `subprocess.run([DEFAULTS, ...])` outside `run_defaults` would run the real
    `defaults` on the user's file from unit tests, deletes and imports included, also while the unit suite runs beside
    the live pool. Today none does.
  - **Fix.** The fixture also points `DEFAULTS` at a path that doesn't exist; a guard test that `run_defaults` is the fake.
  - **Resolution: done.**
    - **Test:** `test_designer_preferences.py::test_no_unit_test_reaches_the_real_defaults` (runs everywhere).
    - **Fix:** conftest's `defaults` fixture also points `DEFAULTS` at a path in the test's folder that doesn't exist.

- [x] **TST-361 · The pool check's failure can lose the count of keys added, and the keys are printed nowhere** · `tests/test_all_tools/workers.py:369-385` · confirmed · found 2026-11-13
  - **Defect.** The detail is the changed values with three names, then the added keys with three; `common.check` cuts it
    at 150 characters, and thumbnail keys run about 50.
  - **Scenario.** Three values changed: "N keys added" is cut off, and the names needed to diagnose are on no line.
  - **Fix.** Both counts first, then the names; on a failure, print the whole sorted lists on a line of their own, as
    `check_the_quits` prints whole quits.
  - **Resolution: done.**
    - **Test:** `test_the_pool_checks_designers_preferences_are_as_before_it[left changed]` failed (the old detail).
    - **Fix:** the detail gives both counts first, then the names; on a failure every key is printed whole, "values
      changed:" and "keys added:" on lines of their own.

- [x] **TST-362 · README's troubleshooting row is wrong for a copy that couldn't be read, and its recovery by hand skips the code's own check** · `README.md:402`, `designer_preferences.py:160-163` · confirmed · found 2026-11-13
  - **Defect.** The row and `put_back`'s docstring say a "couldn't be put back" copy stays and is retried; for an
    unreadable copy the code removes it ("... could not be read (...), so it was removed."). The row's `defaults import`
    by hand doesn't say what the code checks first: not once the user's Designer has run since.
  - **Scenario.** A user looks for a copy that is gone; or, having opened Designer since, imports the old copy over
    their newer layout.
  - **Fix.** Say the unreadable copy is removed; "if you haven't opened Designer since; otherwise delete the copy".
  - **Resolution: done.**
    - **Fix:** README's row says an unreadable copy is removed, and to import by hand only if the user hasn't opened
      Designer since; `put_back`'s docstring names every outcome.
  - Questioned by TST-366 (2026-11-13).

- [x] **TST-363 · Docs and comments claim more than was measured** · `designer_preferences.py:6-10`, `DECISIONS.md` (the new entry), `tests/unit/test_designer_preferences.py:31`, `tests/unit/test_uninstall.py` (the lone-lock test) · confirmed · found 2026-11-13
  - **Defect.** "A Designer can't be given a file of its own: its settings go through cfprefsd, which picks the file"
    states as measured what two failed ways suggest (DECISIONS and ROADMAP say "no way ... was found"); "every Designer
    writes the file as it starts and as it quits (its window layout, its last session, ...)" and DECISIONS' "(its window
    layout, last session, thumbnails)": the last-session keys are in the user's file, but no agent's Designer was seen
    writing them; the test helper "As an agent's Designer does ...: a value changed, a key removed, two added" (no key
    removal was seen); "every launch_designer on macOS leaves it" (only a launch that starts one).
  - **Scenario.** A reader takes these as measured facts.
  - **Fix.** "No way ... was found: ..."; drop "last session" from what Designers were seen writing; "as a Designer
    may"; "every launch_designer that starts one".
  - **Resolution: done.**
    - **Fix:** the module's docstring: "No way ... was found" and what agents' Designers were seen changing (the 122 keys,
      `session.modes.mixer.areas`, the floated dock, `session.instancePID`), "last session" kept only where it describes the
      file's content (README); the test helper "Changes of every kind a put-back undoes"; "every launch_designer that starts
      one"; DECISIONS' entry without the list.

- [x] **TST-364 · The new DECISIONS entry's decision line is unclear and leaves out macOS** · `DECISIONS.md` (Bridge and quitting, the entry on Designer's preferences plist) · confirmed · found 2026-11-13
  - **Defect.** "**Designer's preferences plist is saved as a Designer an agent starts is started, ... for every
    Designer an agent starts.**" is hard to read, says nothing of macOS (nothing is saved elsewhere), and suggests a copy
    per Designer (one is made for the first); the entry also restates measured behaviour, which DECISIONS' introduction
    keeps in GUIDE.md or the module's docstring.
  - **Scenario.** A later reviewer raises Windows behaviour against the entry's wording.
  - **Fix.** "**On macOS, the server saves Designer's preferences plist as the first Designer an agent starts is
    started, and puts it back once no Designer runs.**", the measured part left to `designer_preferences.py`; the
    wording shown to the user, as the entry is theirs.
  - **Resolution: done** (shown to the user with the report).
    - **Fix:** the decision line "On macOS, the server saves Designer's preferences plist as the first Designer an agent
      starts is started, and puts it back once no Designer runs."; the measured part left to the module; the user's two
      choices of this round (6 hours, saving again) added.

- [x] **TST-365 · Small inexact docs and comments** · `designer_preferences.py:2-4`, `README.md:52`, `mcp_server/server_tools/lifecycle.py:78`, `AGENTS.md` (typing paragraph; Deploying, how changes reach Designer), `tests/test_all_tools/workers.py:316-317` · confirmed · found 2026-11-13
  - **Defect.** The module's and README's lists of its users leave out the pool (`workers.py`); the import's comment
    says the package's `__init__` puts the root on sys.path (`core.py` does, the next line says); AGENTS.md lists
    `designer_preferences.py` among "standalone scripts" (it is a module `uninstall.py` imports, reached on an old Python
    only by `uninstall.py --help`), and its deploy note doesn't say a change to it needs the server's restart too;
    `preferences_before`'s docstring ("a copy that agents' Designers ended outside the tools left put back first, as the
    run's first launch would, after this read") is hard to parse.
  - **Scenario.** Readers misled in small ways.
  - **Fix.** Name the pool; "core.py puts the repo root there"; "the standalone scripts and the modules uninstall.py
    imports (`designer_preferences.py`)", and the module in the deploy note; reword the docstring.
  - **Resolution: done.**
    - **Fix:** the module's and README's lists of users name the pool; the import's comment names `core.py`; AGENTS.md
      lists it among "the modules `uninstall.py` imports", says the old-Python test only imports it, and names it in
      how changes reach Designer (the server's restart); `preferences_before`'s docstring rewritten.

- [x] **SRV-133 · A failed put-back's message hides what it did, and its retry can turn into a drop blamed on Designers that "ended outside the tools"** · follows SRV-125, generation 2 · `designer_preferences.py:247-252,265-270,286-299` · confirmed · found 2026-11-13
  - **Defect.** `_not_put_back` says the same "couldn't be put back (...): the copy ... is kept" whether nothing was
    done, some of the added keys were deleted (a stop every `RECHECK_EVERY`, a delete failing), or the whole copy was
    imported and read back otherwise. The retry it implies runs with `ended=False`, where a copy past `LEFTOVER_HOURS`
    (counted from its making) is dropped with "left by Designers that ended outside the tools", untrue after a quit
    through the tools. `'%d hours old'` floors (6.9 hours reads "6 hours old" for a rule of over 6). After a copy saved
    again, "put back as they were before agents' Designers started" leaves out that agents' changes from before the
    user's run stay. Two reviewers found it.
  - **Scenario.** A copy made at 10:00, an agent works until 17:00, `quit_designer` ends its Designer and the put-back
    stops on a `defaults` timeout after 200 deletes: the agent reads that the copy is kept; the next morning's
    `launch_designer` drops it, blaming Designers that ended outside the tools. The half-restored file stays, and no
    message said it was half-restored.
  - **Fix.** Say what was done before the stop ("N of M keys they added removed, values not put back"); in the drop's
    sentence, no cause it can't know ("no Designer was just ended through the tools"), and "over %d hours"; after a
    copy saved again, "as they were when the copy was last saved" or the like.
  - **Resolution: done.**
    - **Test:** `test_designer_preferences.py`: `test_a_put_back_that_fails_keeps_the_copy_and_says_where`,
      `test_a_designer_starting_during_a_put_back_stops_it_and_keeps_the_copy` and
      `test_a_designer_starting_during_many_deletes_stops_them_soon` (no word of the keys removed),
      `test_a_copy_left_behind_is_put_back_only_within_its_hours[6.9]` ("6 hours old", and the cause) and
      `test_a_save_then_a_put_back_once_none_runs_leaves_the_file_as_it_was` (the success line) failed.
    - **Cause:** one sentence for every failure, whatever was done before it; the drop's sentence took the only way to
      an old copy with none just ended to be Designers that ended outside the tools; `%d` floors; the success line
      described the copy's first making.
    - **Fix:** `_put_back` counts the keys it removes and, stopped between them and the import, says ", only partly: N
      of M keys they added removed, no value put back yet"; the drop says "is over 6 hours old and this call ended no
      Designer, so it was dropped: the user may have worked since"; success "put back from the copy made before agents'
      Designers started". The drop of an old copy after a failed put-back stays as decided (the 6 hours), now said in
      the module's docstring and README (TST-366).
    - **Also covered:** the old wordings expected in the lifecycle, uninstall and pool tests.
  - Questioned by SRV-140 (2026-11-13).

- [x] **SRV-134 · Any OSError reading the copy removes it, while the file still holds the agents' changes** · `designer_preferences.py:271-279` · confirmed · found 2026-11-13
  - **Defect.** `except (PreferencesError, OSError) as e: os.remove(path)` treats a passing failure to open or read the
    copy (EMFILE in the long-running server, EIO, EINTR) like content that isn't a plist.
  - **Scenario.** The server is out of file descriptors as `quit_designer` puts back: the copy is removed ("so it was
    removed"), and the next launch saves the file as it is, the agents' changes in it, which no put-back undoes.
  - **Fix.** Remove the copy only on `PreferencesError` (its content is bad); on `OSError` keep it and return
    `_failed(_not_put_back(e))`: one that never reads is still dropped past `LEFTOVER_HOURS`, as `_dropped` removes it
    unread. README's troubleshooting row to match.
  - **Resolution: done.**
    - **Test:** `test_designer_preferences.py::test_a_copy_that_cant_be_opened_now_is_kept` (the module's `open`
      raising EMFILE for the copy) failed: the copy removed, "could not be read".
    - **Cause:** one `except (PreferencesError, OSError)` around the open and the parse.
    - **Fix:** an OSError opening or reading the copy keeps it ("couldn't be put back (...): the copy ... is kept"); only
      content that isn't a plist of keys removes it; README's row says so.
    - **Also covered:** `kept_copy()` (new, TST-367) raises either, which the pool reports as unreadable; uninstall
      keeps such a copy and reports the error (INS-35).
  - Questioned by TST-372 (2026-11-13).

- [x] **SRV-135 · Three more ways a launch leaves no Designer running without a put-back** · follows SRV-130, generation 2 · `mcp_server/server_tools/lifecycle.py:786-792,833-858,342-343` · confirmed · found 2026-11-13
  - **Defect.** SRV-130 put back on `start()`'s refusals after an end, but not: when the Designer this call started is
    force-ended because its record couldn't be written (`raise _unrecorded(port, e, told(), 'Designer (process %d) was
    started, then ended' % pid)`); when the Designer this call started exits during the wait (`running` False, so no
    restart: the timeout's raise after `wait_s`); when `_own_home` or `_own_temp` raises in `_start_designer` after an
    end, before `saved()` (nearly unreachable: `_launch_lock` made the port's folder).
  - **Scenario.** A launch's Designer crashes as it starts: the call waits out its 180 s and raises, none runs, and the
    copy stays; the user opens their Designer before an agent's next call, their log drops the copy, and the crashed
    Designer's writes stay (its `session.instancePID` at least). Within 6 hours, the next call would have put it back.
  - **Fix.** Before those raises, `designer_preferences.put_back(_any_designer, ended=True)` with its sentence in the
    error (it does nothing while any Designer runs); or the reason not to in SRV-130's way.
  - **Resolution: done.**
    - **Test:** `test_lifecycle_env.py`: `test_a_launch_that_ends_the_designer_it_couldnt_record_puts_back`,
      `test_a_launch_whose_designer_exits_during_the_wait_puts_back` and
      `test_a_launch_that_ended_a_designer_and_starts_none_puts_back_first[no home]` failed: the file left changed.
    - **Cause:** only `start()`'s refusals after an end put back.
    - **Fix:** `refusing()` became `none_left()`, which puts back when the call ended or started a Designer (a put-back
      does nothing while any runs), and is used by the raise after force-ending the Designer it couldn't record, the
      timeout's raise, and a `ToolError` from `_start_designer` (its folder refused, or the process not started).
      Live: an `--only bridge` pool run passed 48 of 48, the put-back said in SRV-133's wording, the user's plist
      identical to a backup taken before it.
    - **Also covered:** the "could not be ended" raise keeps `told()` (that Designer runs); a refusal in the wait comes
      from a Designer that answers, so runs.
  - Questioned by SRV-138 (2026-11-13).

- [x] **SRV-136 · The branch's new code uses unmarked `Any` where `object` or a narrower type fits** · `designer_preferences.py:116,126`, `tests/test_all_tools/workers.py:313,329`, `tests/unit/fake_defaults.py:20`, `tests/unit/test_designer_preferences.py:22,40,60,62,332`, `tests/unit/test_lifecycle_env.py:2769,2834,2897` · confirmed · found 2026-11-13
  - **Defect.** AGENTS.md's typing paragraph, added by this branch, asks for the most specific type and a reason beside
    any `Any` kept; the branch's own code has none marked:
    - `_keys(...)` and `current() -> dict[str, Any]`, `workers.py:313` `Preferences = tuple[float, dict[str, Any] |
      str]`, `fake_defaults.py:20` `self.domain`, `test_designer_preferences.py:22` `BEFORE` and `:60,62` `_copy()` and
      its `read`: plist values only stored and compared, `dict[str, object]`;
    - `workers.py:329` `return at, plistlib.load(f)`: an unchecked `Any` in that slot, where `_keys` would check it is
      a dict;
    - `test_designer_preferences.py:40` `running: Any` (`Callable[[], bool]`), `:332` `def no_lock() -> Any`
      (`NoReturn`);
    - `test_lifecycle_env.py:2769` `copies` and `:2897` `at_the_start` (`list[dict[str, object]]`), `:2834` `def
      fails(cmd: list[str], **kw: Any) -> Any` (`**kw: object`, `-> NoReturn`).
    Three reviewers found it.
  - **Scenario.** mypy checks nothing through these; a copy that isn't a dict (only from a hand edit: `_save` checks)
    would stop the pool's end at `saved[key]` with a TypeError instead of a FAIL.
  - **Fix.** The types above; `preferences_before` reads the copy through `_keys` (or a public name for it). Not
    counted: `started: list[Any]` and the pool tests' `write(...)`, which follow older signatures (ROADMAP item 98).
  - **Resolution: done.**
    - **Test:** types (mypy strict over every file); `test_the_copy_kept_is_what_a_put_back_restores` and
      `test_a_kept_copy_that_isnt_a_plist_of_keys_is_refused` failed (no `kept_copy`).
    - **Fix:** the types the finding gives; `preferences_before` reads the copy through `kept_copy()`, which checks it
      as the put-back does.
    - **Also covered:** `Said` removed (INS-35); `started: list[Any]`, the pool tests' `write(...)` and `_lock() ->
      IO[str]` left, as the finding says.

- [x] **INS-35 · uninstall's item for the copy: the 6 hours left out, an unreadable copy reported as "Could not remove ... so it was removed", and its lock and `.new` left** · follows INS-34, generation 2 · `uninstall.py:12-13,181-211`, `README.md:388-393` · confirmed · found 2026-11-13
  - **Defect.** `put_back_preferences` passes `ended=False`, so a copy older than `LEFTOVER_HOURS` is dropped, yet the
    label ("put back first unless your own Designer ran since"), the module docstring ("put back first") and README
    promise a put-back. An unreadable copy, which `_put_back` removes, comes back as an error: "Could not remove the copy
    ...: Designer's preferences couldn't be put back: the copy ... could not be read (...), so it was removed.", and the
    action returns before removing the lock and `.new`. With no copy, the lone lock's action leaves a `.new` a first
    save cut short (the user's preferences, 0600), which nothing lists. README says the copy "and its lock are kept and
    listed" while a Designer runs; with a copy, only the copy is listed. A removal failing in a drop says "the next call
    removes it", and no call follows an uninstall. Three reviewers found parts of it.
  - **Scenario.** The user uninstalls a day after an agent's Designer crashed: the line says the copy was "put back
    first", and its parenthesis that it was dropped as too old.
  - **Fix.** "put back first if it is under 6 hours old and your own Designer hasn't run since, else dropped" in the
    label, the docstring and README; an unreadable copy said as gone (a `Kept`, or its own wording), the lock and `.new`
    removed after it; `.new` removed (or listed) on the lone lock's path; README's "and listed" for the copy alone; for
    uninstall, a failed removal worded without "the next call".
  - **Resolution: done.**
    - **Test:** `test_uninstall.py`: `test_an_old_copy_of_designers_preferences_is_dropped_as_the_label_says`,
      `test_a_copy_of_designers_preferences_that_isnt_a_plist_is_removed_with_its_lock` and
      `test_removes_the_lock_of_designers_preferences_left_with_no_copy[with a save cut short]` failed.
    - **Cause:** the label predated the 6 hours; success was judged by `Said.failed`, which a copy that isn't a plist
      set though it was gone; the lone lock's action knew only the lock.
    - **Fix:** the label, the module's docstring and README name the 6 hours; `put_back_preferences` judges by the copy
      alone (kept: an error; gone: removed, what the put-back said in brackets), so `Said` went; the lock and a save cut
      short are listed and removed together (`_beside_the_copy`); README says the lock is listed when alone;
      `_dropped`'s "it is tried again next time" fits uninstall too.

- [x] **TST-366 · The tools' docstrings and README leave out the 6-hour drop and the save made again** · follows SRV-132 and TST-362, generation 2 · `mcp_server/server_tools/lifecycle.py:723-724,955-956`, `README.md:52,403` · confirmed · found 2026-11-13
  - **Defect.** Both came in the round after SRV-132's docstrings. `launch_designer`'s ("a line before the result says
    when it put back (or dropped) a copy Designers that ended otherwise left, or couldn't save") has no word for "saved
    again", nor for its own put-back after ending a hung Designer; `quit_designer`'s ("unless the user's Designer ran
    since") leaves out the drop of a copy past 6 hours when it ended none; README's How it works row, "within 6 hours",
    doesn't say of what (the copy's making, not the Designers' end); its troubleshooting row's "the next `quit_designer`
    or `launch_designer` with no Designer running tries again" holds only within 6 hours of the copy.
  - **Scenario.** Someone whose agent's Designer ran 8 hours and was closed by hand expects the next call to put the file
    back; it is dropped.
  - **Fix.** One clause in each docstring; "if the copy is under 6 hours old" in both README rows.
  - **Resolution: done.**
    - **Fix:** `launch_designer`'s docstring names saving again and what the line before the result or error says;
      `quit_designer`'s the drop of a copy over 6 hours old when it ended none; README's two rows "if the copy is under
      6 hours old" and "while the copy is under 6 hours old, then drops it". The docs' tests pass.

- [x] **TST-367 · The pool's end check takes as its reference a copy the run's first launch makes again** · follows TST-357, generation 2 · `tests/test_all_tools/workers.py:316-333` · confirmed · found 2026-11-13
  - **Defect.** `preferences_before` takes a kept copy as what the run's last quit puts back, but `saved()` makes the
    copy again when the user's log is newer than it (`again = made is not None and users_log_time() > made`). Its
    docstring's reason for its own put-back ("the run's first launch would do so after this read, and the check fail on
    it") no longer holds now that it reads the copy: the put-back matters only for a copy that launch would drop (past 6
    hours, or the user's log newer), and `test_a_copy_left_from_before_the_run_is_put_back_before_the_pool_reads_the_file`
    (a young copy) fails without it only on its printed line. Two reviewers found it.
  - **Scenario.** An `alone.run` Designer runs, with copy C0; the user opens and closes their own; a full run starts
    (`before` is C0, the put-back waiting for that Designer); the first launch saves the file F as the copy; the outside
    Designer is quit during the run; the last quit puts F back; the check compares F with C0 and fails, the user's log
    being older than the run's start.
  - **Fix.** Read the copy only when it is newer than the user's log, the file otherwise, best through one function of
    `designer_preferences` saying what the next put-back restores; the docstring "dropped or put back first, as the
    run's first launch would"; pool tests of the save made again and of a copy past `LEFTOVER_HOURS` (a FAIL without
    the put-back).
  - **Resolution: done.**
    - **Test:** `test_selftest_pool.py::test_the_check_compares_with_the_file_once_the_users_designer_ran_since_the_copy`
      failed ("1 value changed, 1 key added"); `test_a_copy_too_old_to_put_back_is_dropped_before_the_pool_reads_the_file`
      guards the pool's own put-back (failing without it, by mutation).
    - **Cause:** `before` was any kept copy.
    - **Fix:** `designer_preferences.kept_copy()`, None once the user's Designer ran since the copy (`_users_ran_since`,
      also used by `saved()` and the put-back), read by `preferences_before`; its docstring and the older test's comment
      reworded.
  - Questioned by TST-375 (2026-11-13).

- [x] **TST-368 · More branches no test pins: the second unrecorded raise, three refusals, and every `ended` but quit's** · follows TST-358, generation 2 · `mcp_server/server_tools/lifecycle.py:756,768,771,777,778,792`, `designer_preferences.py:176`, `uninstall.py:184`, `tests/test_all_tools/workers.py:323` · confirmed · found 2026-11-13
  - **Defect.** `test_a_launch_it_couldnt_record_still_says_what_its_save_did` patches `_force_end` to True, so `note`
    in place of `told()` in the "could not be ended" raise (`:792`) fails nothing, though TST-358 named both raises.
    `refusing()` is pinned only where the port is taken (`:774`): `told()` in its place at "not found" (`:768`),
    `_users_next_to` (`:771`) and `_unrecorded(..., 'No Designer was started')` (`:777`) fails nothing. No test passes a
    copy older than `LEFTOVER_HOURS` through `saved()`'s `_put_back_or_say(running, ended)`, the launch's
    `ended=bool(note)`, `refusing()`'s `ended=True`, or the pool's and uninstall's `ended=False`; only quit's and direct
    `put_back` calls have one.
  - **Scenario.** One of those `False` turned `True` brings SRV-125 back (an old copy put back over the user's later
    work, by the server, the pool's parent or uninstall), and the unit suite passes.
  - **Fix.** `_force_end` False with a save's line; a test per `refusing()` site (one parametrized test); an old copy
    through a launch that ended none (dropped), one that ended one (put back), the pool's start and uninstall (dropped).
  - **Resolution: done.**
    - **Test:** each checked by mutation, one at a time, its test failing: `note` in the "could not be ended" raise
      (`test_a_launch_it_couldnt_record_still_says_what_its_save_did[not ended]`); `told()` in place of `none_left()`
      at "not found", the user's Designer and the record
      (`test_a_launch_that_ended_a_designer_and_starts_none_puts_back_first[...]`, on an old copy, which also pins its
      `ended=True`); the launch's `ended=False` (`test_a_launch_that_ended_a_designer_puts_back_an_old_copy_before_its_start`);
      `saved()` passing `True` (`test_a_start_puts_back_an_old_copy_only_right_after_an_end[after none]`); the pool's
      `ended=True`, or no put-back (`test_a_copy_too_old_to_put_back_is_dropped_before_the_pool_reads_the_file`);
      uninstall's `ended=True` (`test_an_old_copy_of_designers_preferences_is_dropped_as_the_label_says`). Also
      `test_launch_puts_back_a_copy_left_by_designers_ended_outside_the_tools[old]`.

- [x] **TST-369 · The POSIX-import guard doesn't walk the plugin or the examples** · follows TST-356, generation 2 · `tests/unit/test_lint.py:41` · confirmed · found 2026-11-13
  - **Defect.** `for folder in ('tests', 'mcp_server', 'client', 'scripts', '.')`, `'.'` its top-level files only,
    skips `plugin/` and `examples/`, while TST-356's resolution says "the whole repository by that test". The plugin
    runs in Designer on Windows too; none of them imports such a module today. Two reviewers found it.
  - **Scenario.** An `import fcntl` at the plugin's top passes the unit suite and stops the bridge loading on Windows.
  - **Fix.** Walk the repository's Python files (`git ls-files '*.py'`, or the root without `venv`, `.git`,
    `__pycache__` and `.claude`), and name the plugin in the test's docstring.
  - **Resolution: done.**
    - **Test:** with `import fcntl` put at the top of the plugin's `__init__.py`, the old test passed; the new one
      failed naming it, and passes without.
    - **Fix:** it walks every folder of the repository but hidden ones (`.git`, `.claude`'s vendored skill, the
      caches), `venv`, `__pycache__` and `node_modules`; its docstring names the plugin.

- [x] **TST-370 · The typing rule names a case strict mypy already refuses, and leaves where type findings stop against ROADMAP item 98 open** · `AGENTS.md:130-142`, `.claude/skills/project-code-review/SKILL.md:152-156` · confirmed · found 2026-11-13
  - **Defect.** "(or a bare `dict`, `list` or `tuple` standing for something whose shape is known)": `mypy.ini`'s
    `strict = True` includes `disallow_any_generics`, so an annotation of a bare `dict` already fails `test_types.py`;
    what fits the words is a container whose items' types say less than is known (`dict[str, object]` for a record a
    `TypedDict` fits). The skill has reviewers report every vague type in their area, with nothing for what ROADMAP item
    98 already plans, and AGENTS.md's "Code you touch" doesn't say whether the function or the file.
  - **Scenario.** A reviewer looks for a bare `dict`, finds none, and misses the records a `TypedDict` fits; a
    whole-project review fills REVIEW.md with item 98's thousand `Any`.
  - **Fix.** "a `dict`, `list` or `tuple` whose items' types say less than is known (a record's `dict[str, object]` where
    a `TypedDict` fits)" in both files; in the skill, type findings for code the review's scope adds or changes, the
    rest left to item 98, and in AGENTS.md "a function you change" or "a file you change": both the user's choice.
  - **Resolution: done** (the user's choice, 2026-11-13: type findings only in what a branch's diff adds or changes;
    "a function you change" is the agent's reading of "code you touch", told to the user).
    - **Fix:** AGENTS.md: "a `dict`, `list` or `tuple` whose items' types say less than is known (...; a bare one strict
      mypy refuses already)", "A function you change gets the same look (the rest of its file is ROADMAP item 98's)",
      reviewers report what a branch's diff adds or changes; the review skill the same, a whole-project review reporting
      none while item 98 is open; item 98's text to match; DECISIONS.md, Project rules, records the user's choice.
  - Questioned by TST-373 and TST-374 (2026-11-13).

- [x] **TST-371 · Small inexact docs and comments** · `designer_preferences.py:26-27,303,309`, `tests/test_all_tools/workers.py:349-353`, `AGENTS.md:124-128` · confirmed · found 2026-11-13
  - **Defect.** "Only through `defaults`, never the file itself", while `_file_holds_settings` reads it (never written
    directly is meant); `_dropped`'s "the next call removes it": the next call tries again, and a lasting cause fails
    each time; `check_the_preferences`' docstring lists its fails without the copy or the file unreadable as the run
    started; AGENTS.md says "the modules `uninstall.py` imports (`designer_preferences.py`) ... do start with `from
    __future__ import annotations`", but `uninstall.py` also imports `project_constants.py`, which doesn't (it runs on
    3.9 as it is, with no `X | None` in it).
  - **Scenario.** Readers misled in small ways; an agent adds `X | None` to `project_constants.py`, taking the module
    named as the only one that counts.
  - **Fix.** "never written directly"; "the next call tries again"; the missing fail in the docstring;
    `project_constants.py` named in AGENTS.md, or given the import.
  - **Resolution: done.**
    - **Fix:** the module's docstring "Written only through `defaults`, never directly"; `_dropped`'s "it is tried
      again next time"; `check_the_preferences`' docstring names the file unreadable as the run started; AGENTS.md names
      `project_constants.py` among the modules the standalone scripts import, which now starts with `from __future__
      import annotations` too (no behaviour changed; `test_old_python.py` passes).
  - Questioned by TST-372 and TST-375 (2026-11-13).

- [x] **SRV-137 · A copy dropped as too old whose removal fails is put back by the next quit, however old** · follows SRV-128, generation 2 · `designer_preferences.py:168-171,273-277,319-328` · confirmed · found 2026-11-13
  - **Defect.** `_dropped` keeps a copy it can't remove ("it is tried again next time"), but only a call with
    `ended=False` drops a copy for its age: the next launch's `saved()` finds the copy (`made` not None, `again`
    False), saves none and starts its Designer, and that Designer's `quit_designer` passes `ended=True`, which skips
    the age check (`if not ended and time.time() - made > LEFTOVER_HOURS * 3600:`) and puts the old copy back. The same
    after a put-back that worked but whose copy couldn't be removed: the next session's quit puts back the copy of the
    session before.
  - **Scenario.** A copy 8 hours old, none running, its removal failing for a lasting cause (an immutable flag, the
    folder's permissions): `launch_designer` says it was dropped but couldn't be removed, and starts a Designer; its
    quit puts the 8-hour-old copy back over the file, the case the 6 hours were chosen for (SRV-125: the user may have
    worked since with no log to show it).
  - **Fix.** A drop that holds whatever the next call's `ended`: a mark beside the copy that `_put_back` honours, or
    `saved()` not starting a session on a copy still there after a put-back that found none running (that copy was
    dropped or put back), saying so. Settled by reading; a unit test: `os.remove` failing for the copy,
    `put_back(NONE_RUNS, ended=False)` on a 7-hour-old copy, then a launch's `saved()` and `put_back(..., ended=True)`:
    the file must not be the copy's.
  - **Resolution: done.**
    - **Test:** `test_designer_preferences.py::test_a_copy_a_drop_couldnt_remove_is_never_put_back[replaced]` and
      `[not even replaced]` failed: `kept_copy()` gave the old copy, which the quit then put back.
    - **Cause:** a drop that couldn't remove the copy left it as it was, so the next launch took it for its session's
      (`made` not None) and that session's quit, with `ended=True`, put it back however old.
    - **Fix:** `_dropped` gives up a copy it can't remove (`_give_up`): its time written in the lock file, which is
      there already and isn't the copy. A copy given up (`_given_up`) is no one's: `_put_back` only tries to remove it
      again, `saved()` saves over it, `kept_copy()` returns None; the sentence adds ", and never put back".
    - **Also covered:** a put-back that worked but couldn't remove its copy (the same `_dropped`;
      `test_a_copy_that_cant_be_removed_doesnt_unsay_what_was_done`, removed by the next call still); the copy a failed
      start removes (SRV-138) goes through `_dropped` too; uninstall reports a copy given up as one it couldn't remove,
      as before. Mutations caught: no mark, `saved()`, `_put_back` or `kept_copy()` ignoring it.
  - Questioned by SRV-142 (2026-11-13).

- [x] **SRV-138 · A launch whose process can't start leaves the copy it just saved, and its error can list the put-backs out of order** · follows SRV-135, generation 3 · `mcp_server/server_tools/lifecycle.py:345-351,753-760,780-785` · confirmed · found 2026-11-13
  - **Defect.** SRV-135's fix has `none_left()` put back for "a `ToolError` from `_start_designer` (its folder refused,
    or the process not started)", but only `if note or homes:`. On a plain first launch, `saved()` saves a copy,
    `_started` raises (Popen fails), and neither is set: the copy stays with no Designer running. When `note` is set,
    `ToolError(first + str(e))` puts `none_left()`'s line before the lines `saved()` said earlier (inside `e`): a
    put-back that failed in `saved()` and then worked in `none_left()` reads "put back ..." first and "couldn't be put
    back ...: the copy ... is kept" last, the copy gone.
  - **Scenario.** `launch_designer` with no Designer running and Designer's binary not executable: the error says it
    couldn't be started; the copy, equal to the file, stays, and within 6 hours the next call that finds none running
    puts it back over what changed since with no log to show it (SRV-125's case).
    `test_a_launch_whose_designer_cant_be_started_still_says_what_its_save_did` makes this very case and asserts
    nothing of the copy.
  - **Fix.** `none_left()` puts back also when this call's `saved()` made the copy (`_start_designer` says so; only
    then, as `ended=True` puts back a copy however old: SRV-137); `e`'s lines before `none_left()`'s. Settled by
    reading.
  - **Resolution: done.**
    - **Test:** `test_lifecycle_env.py::test_a_launch_whose_designer_cant_be_started_still_says_what_its_save_did` and
      `test_designer_preferences.py::test_a_start_that_fails_removes_only_a_copy_it_made[now]` failed, the copy left;
      `test_lifecycle_env.py::test_a_launch_that_ended_a_designer_and_starts_none_says_its_put_backs_in_order` failed,
      the working put-back said before the failed one.
    - **Cause:** `none_left()` puts back only after an end or a start, and a copy made for a start that failed is
      neither; `_start_designer` folded what `saved()` said into its error, so `start()` could only put `none_left()`'s
      lines before it.
    - **Fix:** `saved()` removes a copy it made (not one made again: the running Designer's) when the start raises
      (`_dropped`, so given up if it can't be removed); `_start_designer` raises `_NotStarted`, which carries what
      `saved()` said apart, and `start()` adds that to the lines before `none_left()`'s.
    - **Also covered:** `[again]`, the copy made again kept; SRV-139's refusal raises the same way. Mutations caught.

- [x] **SRV-139 · A launch goes ahead when the put-back before its save sees a Designer start meanwhile** · follows SRV-127, generation 2 · `designer_preferences.py:167-171`, `mcp_server/server_tools/lifecycle.py:345-347,771-773` · confirmed · found 2026-11-13
  - **Defect.** `start()` refuses to start next to the user's Designer (`_users_next_to`) before `_start_designer`,
    whose `saved()` first puts back a copy left behind (about 7 ms a key: a second or so for the 122 keys of a full
    run). That put-back stops on "a Designer started meanwhile" (SRV-127), but nothing passes the stop back: `saved()`
    yields the sentence and the Designer is started anyway, next to the one that appeared. Only a Designer outside the
    tools can be that one (the lock keeps other servers' launches out until the start): the user's. Once their log is
    written, `again` also saves the copy again from the file their running Designer holds, the line saying their
    Designer "ran since".
  - **Scenario.** A copy left by Designers that ended outside the tools; an agent calls `launch_designer` as the user
    opens their Designer: the put-back stops and says so, and an agent's Designer starts next to the user's, which
    `_users_next_to` exists to refuse ("since Designers share Designer's preferences plist").
  - **Fix.** `saved()` tells its caller a Designer appeared (or `_start_designer` asks `_users_next_to(port, '')` again
    inside the `saved()` block, before the start), and the launch refuses as `_users_next_to` does, saying what the
    put-back did. Settled by reading: a race on the user's timing, widened from the moment between the check and the
    start to the put-back's length.
  - **Resolution: done.**
    - **Test:** `test_lifecycle_env.py::test_a_launch_refuses_once_a_designer_starts_during_its_put_back` failed: the
      Designer was started next to the one that appeared.
    - **Cause:** the put-back's stop was only said; nothing looked again between `_users_next_to` and the start.
    - **Fix:** not the entry's: `_users_next_to` asked again wouldn't see a Designer that has just started, which
      listens nowhere yet (`_sorted_out` counts it as one that may be starting on the port). `_start_designer`, inside
      `saved()` and when it said something, refuses if any Designer appeared since `start()` looked (`_appeared`: any
      `_sorted_out(port)` finds, none being there then), with "A Designer started as this one was about to (process
      N): none is started next to it ..."; lifecycle's module docstring names it.
    - **Also covered:** only when `saved()` said something (a put-back, a save again or one that failed): launches
      side by side, which say nothing while another's Designer runs, are never refused by an unrecorded Designer of
      another server. Mutation caught.
  - Questioned by SRV-141, TST-376 and TST-377 (2026-11-13).

- [x] **SRV-140 · The put-back's lines still say more than they know** · follows SRV-133, generation 3 · `designer_preferences.py:51,77,255-260,275,307-316`, `uninstall.py:215`, `README.md:403` · confirmed · found 2026-11-13
  - **Defect.** Four cases SRV-133's fix left:
    - every line calls the copy the one from "before agents' Designers started" (`BEFORE`), but `saved()` makes it
      again only while a Designer runs (`_put_back` returns '' first then), an agent's (a start goes ahead only with
      the user's closed): a copy saved again holds that agent's changes, and the last quit's "put back from the copy
      made before agents' Designers started" is untrue (the comment above that line says as much);
    - a failure after the import (the read-back's `defaults export` failing) gets no `partly` (`partly if removed and
      not imported else ''`) and reads like a failure before anything was done, though the added keys were removed and
      the copy imported;
    - a stop after every added key was removed, with no value to put back (`changed` empty), says "only partly: N of
      N keys they added removed, no value put back yet", the file already as the copy;
    - in `partly`, "they" comes before what it stands for (agents' Designers), named later in the sentence.
    Two reviewers (the product code and the docs).
  - **Scenario.** An agent works in Designer A; the user opens and closes their own; the agent's next launch saves the
    copy again; the last quit says the file is put back from before agents' Designers started, while A's changes from
    before the user's run stay.
  - **Fix (generation 3: smaller claims).** "the copy kept" (or the time it was made) for `BEFORE` wherever it is said
    (the lines, `saved_file()`'s docstring, uninstall's label, README's troubleshooting row); after the import, ",
    after the keys they added were removed and the copy imported"; no "only partly" when nothing was left to import;
    the subject before "they". The tests pinning the wordings change with them, and `not imported` gets a test (the
    tests reviewer: `partly if removed else ''` passes them all).
  - **Resolution: done.**
    - **Test:** `test_designer_preferences.py::test_a_put_back_failing_after_its_import_says_how_far_it_got` (no word of
      the import) and `test_a_put_back_with_no_value_to_put_back_imports_nothing` ("only partly: 2 of 2", the copy kept)
      failed; the wordings expected in the preferences, lifecycle, pool and uninstall tests failed on the old lines.
    - **Cause:** the lines named the copy's first making; `partly` was said only before the import; the look for a
      Designer before the import came even with no value to import.
    - **Fix:** "their copy" for "the copy from before agents' Designers started" everywhere (`BEFORE` removed;
      `saved_file()`'s docstring, uninstall's label "the copy of Designer's preferences launch_designer saved",
      README's troubleshooting row, the pool's line); ", after the keys added since were removed and their copy
      imported" for a failure after the import; no import, so no stop, when no value differs (the file is as the copy
      once the keys added are removed, read back as before); "keys added since" for "keys they added".
    - **Also covered:** the drop on the user's log ("ran since their copy was made"); uninstall's
      `test_says_when_designers_preferences_couldnt_be_put_back[import fails]` now changes a value, so its import runs.
      Mutations caught: always importing, nothing or `partly` said after the import.
  - Questioned by SRV-143 (2026-11-13).

- [x] **TST-372 · The pool's FAIL for a start it couldn't read has no test, and a copy removed while `kept_copy()` reads it counts as unreadable** · follows SRV-134 and TST-371, generation 2 · `tests/test_all_tools/workers.py:325-331,347-353,373-375`, `designer_preferences.py:198-206` · confirmed · found 2026-11-13
  - **Defect.** `preferences_before` turns `kept_copy()` raising (`PreferencesError`, `OSError`) or `current()` failing
    into a string, on which `check_the_preferences` FAILs ("they couldn't be read as the run started"). No unit test
    makes either (none has that line), so removing the `except` (the pool then raises before any worker starts) or
    turning the FAIL into a skip passes them all, though SRV-134's resolution names the path ("which the pool reports
    as unreadable"). `kept_copy()` looks for the copy (`_made()`), then opens it, without the lock: a put-back removing
    it between the two raises `FileNotFoundError`, reported as unreadable, where the code before took a missing copy
    for none. `check_the_preferences`' docstring names only the file unreadable (TST-371's fix), not the copy. Two
    reviewers (the tests and the docs).
  - **Scenario.** A regression in that path goes unseen until a run whose start can't read the file; an `alone.run`
    Designer quit just as a full run starts fails the run's end check.
  - **Fix.** `kept_copy()` returns None on `FileNotFoundError` (or reads under the lock); a pool test with
    `defaults.fail['export']` during `preferences_before` (cleared before the workers), expecting the FAIL line, and
    one with a copy that can't be opened; the docstring "when the file, or the copy kept, couldn't be read as the run
    started". Settled by reading.
  - **Resolution: done.**
    - **Test:** `test_designer_preferences.py::test_a_copy_removed_as_it_is_read_counts_as_none` failed
      (`FileNotFoundError`); `test_selftest_pool.py::test_the_preferences_check_fails_when_the_run_couldnt_read_them_as_it_started[the file]`
      and `[the copy kept]` cover the path (the second failed on the old line): without the `except`, or with the FAIL a
      skip, they fail (mutations).
    - **Cause:** `kept_copy()` opens the copy after looking for it, without the lock; nothing tested the FAIL.
    - **Fix:** `kept_copy()` returns None on `FileNotFoundError`; the pool's line "the copy kept couldn't be read
      (...)"; `check_the_preferences`' docstring names the copy kept too.

- [x] **TST-373 · Where type findings stop isn't one line: authors look at the whole function they change, reviewers at the diff's code, and this branch's changed functions keep unmarked `Any`** · follows TST-370, generation 2 · `AGENTS.md:142-144`, `.claude/skills/project-code-review/SKILL.md:152-153`, `tests/unit/selftest_fakes.py:98,106,118,120,134`, `tests/unit/test_lifecycle_env.py:711`, `tests/test_all_tools/workers.py:457` · confirmed · found 2026-11-13
  - **Defect.** AGENTS.md: "A function you change gets the same look ... (the rest of its file is ROADMAP item 98's).
    Reviewers report the ones left in the code a branch's diff adds or changes"; the skill: "types, in the code a
    branch's diff adds or changes (the rest is ROADMAP item 98's ...)"; item 98's Why: "in the functions a change
    touches, and branch reviews report what their diff leaves". An unchanged line in a changed function is the
    author's under AGENTS.md and item 98, and item 98's or not under the skill, as "code a diff changes" is read: a
    reviewer can go either way, and what authors owe goes unchecked. This branch has such lines, none marked: `pool()`
    in `selftest_fakes.py` (the diff adds its `designer_pids` line: `write: Any, unit: Any = None) -> Any`, `ports:
    Any`, `gates: list[Any]`, `start: Any, **kw: Any`, `**kwargs: Any`), `_launch_with_home`'s `begin(cmd: list[str],
    **kw: Any)` (the diff adds `at_start` to that function), `run_pool`'s `parts: dict[str, dict[str, Any] | None]`
    (a worker's results, AGENTS.md's case for a `TypedDict`; the diff adds two calls there). The second review left
    `pool()`'s `write` to item 98 as following an older signature, before AGENTS.md had the function rule. Two
    reviewers (the docs and the tests).
  - **Scenario.** Two reviews of one branch report different `Any`, and a branch keeps one its author was to narrow.
  - **Fix.** One line in all three, the user's choice: "the functions a branch's diff adds or changes" in the skill
    and AGENTS.md's reviewer sentence (DECISIONS.md's "the code a branch's diff adds or changes" reads either way), or
    AGENTS.md's author rule narrowed to the lines a change touches. With the function line, these narrowed or marked:
    `begin`'s `**kw: object`; in `pool()`, `Callable`s for `write`, `unit` and `start`, `object` for `**kw` and
    `**kwargs`, `Collection[int]` for `ports`, the module it returns and `gates` marked (`# Any: <reason>`); `parts` a
    `TypedDict`, or marked.
  - **Resolution: done** (the user's choice, 2026-11-13: (a), type findings in the functions a branch's diff adds or
    changes; DECISIONS.md's entry updated).
    - **Fix:** the review skill ("in the functions a branch's diff adds or changes, their lines it leaves as they were
      too"), AGENTS.md's reviewer sentence, ROADMAP item 98's Why and DECISIONS.md go by whole functions. In the
      functions this branch changed: `pool()`'s `write: Callable[[str, str, int], Mapping[str, object] | None]`, `unit:
      Callable[[str], Done] | None`, `-> ModuleType` (a `cast` of the module `fresh()` gives), `ports:
      Collection[int]`, `start: Callable[[str], Done]`, `**kw` and `**kwargs: object`, the gate a runtime-checkable
      `_Gate` Protocol, checked; `begin`'s `**kw: object`; `started: list[object]`; the seven new pool tests' `write`
      returning `dict[str, object]`; `run_pool`'s `parts: dict[str, dict[str, object] | None]`, its quit test moved into
      `_quit_to_keep` with the `isinstance` that `object` asks for. No behaviour changed: the pool, lifecycle and
      uninstall tests pass, mypy strict too; a mutation of `_quit_to_keep` fails the pool tests.
    - **Also covered:** every function the diff touches scanned (its AST) for an unmarked `Any`: these were all, but a
      word in `quit_designer`'s docstring.
  - Questioned by TST-378 (2026-11-13).

- [x] **TST-374 · ROADMAP item 98's Approach still looks for bare containers** · follows TST-370, generation 2 · `ROADMAP.md:82` · confirmed · found 2026-11-13
  - **Defect.** TST-370's fix changed item 98's Why ("item 98's text to match"), not its Approach: "each `Any`, and
    each bare `dict`, `list` or `tuple` whose shape is known, narrowed", which strict mypy already refuses
    (`disallow_any_generics`).
  - **Scenario.** Whoever takes item 98 looks for bare containers, finds none, and leaves the `dict[str, object]`
    records a `TypedDict` fits: TST-370's own scenario.
  - **Fix.** AGENTS.md's words: "each `dict`, `list` or `tuple` whose items' types say less than is known".
  - **Resolution: done.**
    - **Fix:** item 98's Approach: "each `dict`, `list` or `tuple` whose items' types say less than is known".

- [x] **TST-375 · Two more inexact docs** · follows TST-371, generation 2, and TST-367, generation 3 · `AGENTS.md:127-128`, `designer_preferences.py:31-32` · confirmed · found 2026-11-13
  - **Defect.** AGENTS.md: "(`tests/unit/test_old_python.py` runs them on an older Python when one is installed; the
    modules only as `uninstall.py --help` imports them)": `install.py` and `scripts/read_crash_dump.py` import
    `project_constants.py` at their top too, and both run on the old Python
    (`test_install_refuses_an_old_python_with_its_message`, `test_read_crash_dump_reads_a_dump_on_an_old_python`). The
    module's docstring: "the pool's end check (workers.check_the_preferences), which compares the file with
    kept_copy()": only when a copy is kept as the run starts; a usual full run compares with the file as read then
    (`preferences_before`'s `current()`).
  - **Scenario.** A reader takes `uninstall.py --help` for the only check of `project_constants.py` on the old Python,
    or `kept_copy()` for the pool's only reference.
  - **Fix (smaller claims).** "the modules through the scripts that import them"; "which compares the file with what
    the run's last quit should leave", or the clause dropped.
  - **Resolution: done.**
    - **Fix:** AGENTS.md "the modules only through the scripts that import them"; the module's docstring "which
      compares the file with what the run's last quit should leave".

- [x] **SRV-141 · `_appeared` can refuse a launch over another server's Designer not yet recorded, and its `if said` guard has no test** · follows SRV-139, generation 3 · `mcp_server/server_tools/lifecycle.py:355-377,822`, `designer_preferences.py:163-166,282-283` · confirmed · found 2026-11-13
  - **Defect.** SRV-139's fix refuses a launch once any Designer appeared since `start()` looked, but only `if said`,
    so that, as its resolution says, launches side by side "are never refused by an unrecorded Designer of another
    server"; `_appeared`'s docstring: "The user's, as other launches wait for the lock". The preferences lock is let go
    when `_start_designer`'s `with designer_preferences.saved(...)` ends, right after Popen, and `start()` records that
    Designer only afterwards (`_remember_started(port, pid, home)`: a `ps`, then a file written). Meanwhile another
    server's launch takes the lock, and if its `saved()` says anything, `_appeared` finds the unrecorded Designer
    (listening nowhere yet: `_sorted_out`'s `here`) and refuses. `saved()` says something while another agent's
    Designer has just started when: every save fails (the plist unreadable, SRV-126's lasting state, says "couldn't be
    saved first" on every launch, neither finding a copy; or `defaults` failing); a copy given up can't be removed
    again (`_dropped('')` comes before `running()`); the lock can't be opened (`yield _not_saved(e)`, no lock held at
    all). No test has a process appear while nothing is said: `appeared = _appeared(port)` without `if said` passes them
    all (the tests reviewer). All three reviewers.
  - **Scenario.** The user's plist unreadable, the pool's workers launch at once: the second takes the lock as the
    first's Popen returns, its own save fails ("couldn't be saved first"), and the first's process is listed before its
    record is written: the second is refused with "A Designer started as this one was about to (process N): ... ask the
    user to close it", N the first worker's Designer, and its category fails. How often reading can't tell: the
    second's `defaults export` and the first's `ps` take about as long.
  - **Fix.** Either the record written before the preferences lock goes (`_start_designer` doing the recording inside
    its `with`; the lock order unchanged, the port's lock then the preferences'), or `_appeared` asked only when a
    put-back ran (the window SRV-139 is about: `saved()` telling its caller so, rather than `said` being non-empty);
    `_appeared`'s docstring corrected; a unit test with an unrecorded process appearing during `saved()` while only the
    save failed (not refused), beside SRV-139's (refused). Settled by reading.
  - **Resolution: done** (the user's choice, 2026-11-13: the record written before the lock goes, rather than the look
    made only after a put-back; DECISIONS.md, Bridge and quitting).
    - **Test:** `test_lifecycle_env.py::test_a_launch_records_its_designer_before_letting_the_preferences_lock_go`
      failed (`[False]`: the lock let go before the record); `test_a_launch_refuses_a_designer_that_appears_as_it_starts`
      failed (nothing said, so the Designer was started next to the one that appeared);
      `test_a_launch_without_the_preferences_lock_takes_no_designer_for_the_users` failed (refused over process 556,
      another server's just started).
    - **Cause:** the lock was let go right after the start, before `start()` recorded the Designer, so a launch waiting
      for it could find that Designer unrecorded and take it for the user's; and `_appeared` was asked whenever
      `saved()` said something, also when the lock couldn't be taken, with no launch then waiting for another.
    - **Fix:** `_start_designer` records its Designer inside `saved()`'s `with`, an error kept and returned rather than
      raised through it (a copy just made would be dropped while the Designer started may have written the file;
      `start()` ends that Designer and puts back, as before). `saved()` takes a `check`, run under the lock before the
      start, whatever is said, and not when the lock couldn't be taken: `_appeared` goes through it, its `if said`
      gone, since every launch now records under the lock and a Designer that appears unrecorded then is the user's,
      after a put-back or not. The lock is held the longer by `_remember_started` (a `ps`, a file written).
      `_start_designer`'s and `_appeared`'s docstrings, lifecycle's module docstring, `saved()`'s, DECISIONS.md's entry.
      The lock probe the tests repeated is `fake_defaults.lock_held()` (the second review's simplification), used by
      three tests.
    - **Also covered:** a record that fails (`test_a_launch_that_ends_the_designer_it_couldnt_record_puts_back`,
      `test_a_launch_it_couldnt_record_still_says_what_its_save_did`) as before; SRV-139's test still refused. Mutations
      caught: the record after the lock goes, the check only when something is said, the check without the lock. Live:
      `--only bridge`, 48/48, the user's plist identical to an export made before the run.
  - Questioned by SRV-144 (2026-11-13).

- [x] **SRV-142 · A copy that isn't a plist and can't be removed isn't given up: it is "kept" for good, and no later launch saves one** · follows SRV-137, generation 3 · `designer_preferences.py:28-29,298-302` · confirmed · found 2026-11-13
  - **Defect.** SRV-137's fix gives up a copy `_dropped` can't remove, but `_put_back` removes a copy that isn't a plist
    of keys with `os.remove(path)` itself: an `OSError` there reaches `_put_back_or_say`, which says "couldn't be put
    back ([Errno 1] ...): their copy is kept, in ...". The copy isn't given up, so every later `saved()` finds it
    (`made` set, `_given_up` False) and saves none, and every put-back says the same: agents' Designers' changes are
    never put back, while the lines promise a copy kept for a later put-back and never say they won't be. The module
    docstring: "one that isn't a plist of keys is removed; one that can't be removed is given up (_give_up), never put
    back". SRV-137's **Also covered** names `_dropped`'s callers, not this removal. The docs reviewer.
  - **Scenario.** A copy damaged on disk (`_save` writes only what reads as keys), with SRV-137's causes for a removal
    that fails (an immutable flag, the folder's permissions): each launch and quit says the copy is kept, and every
    agent's Designer's changes stay in the user's file.
  - **Fix.** That removal through `_dropped`, its own sentence no longer saying "so it was removed" before `_dropped`
    may add that it couldn't be; a unit test with `os.remove` failing on a copy that isn't a plist: given up, and saved
    over by the next start. Settled by reading.
  - **Resolution: done.**
    - **Test:** `test_designer_preferences.py::test_a_copy_that_cant_be_read_nor_removed_is_given_up` failed: "couldn't
      be put back ([Errno 1] Operation not permitted): their copy is kept".
    - **Cause:** that removal was the one of the copy not made through `_dropped`.
    - **Fix:** through `_dropped`: a copy that isn't a plist and can't be removed is given up, and saved over by the
      next start; its line "so it was dropped" (not "removed", which `_dropped` may follow with "couldn't be removed");
      `put_back`'s docstring and README's troubleshooting row say "dropped".
    - **Also covered:** every removal of the copy goes through `_dropped` now (the module's other `os.remove` is
      `_save`'s `.new`); uninstall reports such a copy as kept, with its line. Mutation caught.

- [x] **SRV-143 · Three result lines still say other than what happened** · follows SRV-140, generation 4 · `designer_preferences.py:223-226,328-332,348` · confirmed · found 2026-11-13
  - **Defect.**
    - SRV-140's third case, through the read-back: with no value to put back, every key added removed and the
      read-back failing (its `defaults export`, or the file read otherwise), `elif removed:` says "only partly: 3 of 3
      keys added since removed, no value put back yet", though nothing was left to do; SRV-140's fix removed only the
      stop before the import.
    - SRV-140's fix turned `_dropped`'s "The copy %s couldn't be removed" into "Their copy ...": when `said` is '' (a
      copy given up, a put-back with nothing to do), the stripped line opens with "Their copy", nothing before it
      saying whose, in `quit_designer`'s result and `launch_designer`'s line; SRV-140 had asked for the subject before
      "they".
    - `_not_saved` for a lock that couldn't be opened says "this Designer's changes to them won't be put back", but a
      copy kept for another agent's Designer, made before this one started, is put back by the last quit, this
      Designer's changes with it, when the lock opens then.
    Two reviewers (the product code and the docs).
  - **Scenario.** An agent reads "only partly: 3 of 3 ..., no value put back yet" and expects a value still to come
    back; reads "Their copy /Users/.../.sd_claude_bridge_kve_preferences.plist couldn't be removed" alone on a line;
    reads "won't be put back" though the last quit puts them back.
  - **Fix.** ", after the keys added since were removed" when every key added was removed and no value differed (as
    after an import); "The copy of Designer's preferences %s couldn't be removed"; "may not be put back" for the lock
    (or "won't" only with no copy kept). The tests pinning these wordings change with them. Settled by reading.
  - **Resolution: done.**
    - **Test:** `test_designer_preferences.py::test_a_put_back_with_nothing_left_to_put_back_says_so_when_its_read_back_fails`
      failed ("only partly: 2 of 2"); `test_a_copy_a_drop_couldnt_remove_is_never_put_back[not even replaced]` (the
      quit's line opening "Their copy") and `test_a_copy_that_cant_be_removed_doesnt_unsay_what_was_done` failed;
      `test_a_lock_that_cant_be_opened_is_said` failed ("won't be put back").
    - **Cause:** `partly` took every stop after a delete for one with values left; SRV-140's "Their copy" counted on a
      sentence before it; `_not_saved` said "won't" for a lock that couldn't be taken, as for a save that failed.
    - **Fix:** ", after the keys added since were removed" when every key added was removed and no value differed;
      "The copy of Designer's preferences %s couldn't be removed"; "may not be put back" when the lock can't be taken
      (`_not_saved`'s `will`).
    - **Also covered:** a save that fails keeps "won't": it leaves no copy for this Designer (none, one given up, or one
      made before the user's run, which is dropped). Mutations caught.

- [x] **TST-377 · `saved()`'s docstrings say only an agent's Designer can run while a launch saves, which is what `_appeared` refuses** · follows SRV-139, generation 3 · `designer_preferences.py:16-19,155-156` · confirmed · found 2026-11-13
  - **Defect.** `saved()`: "A copy the user's Designer has run since (only an agent's can run now) is made again from
    the file as it is, holding their run"; the module docstring: "(a start goes ahead only with the user's Designer
    closed, so the file holds their run) ... (one made again is the running Designer's)". SRV-139's fix is for the
    user's Designer starting during `saved()`'s put-back: `_put_back` then stops (or returns '' on `running()`), `again`
    holds once their starting Designer has written its log, and `_save()` copies the file as their starting Designer,
    and the stopped put-back, left it; only then does `_appeared` refuse, and the copy made again (`fresh` False) stays,
    no agent's Designer running. The docs reviewer.
  - **Scenario.** A maintainer takes a copy made again for one an agent's running Designer holds, and builds on that;
    this one is most likely dropped by the next call, as the user's Designer goes on writing its log.
  - **Fix (generation 3: smaller claims).** "(an agent's, or the user's just starting, which the launch then refuses)",
    and the module docstring's two clauses narrowed alike. Settled by reading.
  - **Resolution: done.**
    - **Fix:** `saved()`'s docstring "(a Designer runs now: an agent's, or the user's just starting, which the launch then
      refuses)", without "holding their run"; the module docstring's "(a start goes ahead only with the user's Designer
      closed)" and "(one made again is kept: a Designer was running as it was made)".

- [x] **TST-378 · AGENTS.md has a change narrow only the `Any` in its functions; the review skill and DECISIONS.md name vague containers too** · follows TST-373, generation 3 · `AGENTS.md:142-144` · confirmed · found 2026-11-13
  - **Defect.** AGENTS.md: "A function you change gets the same look: an `Any` it holds that could be narrower is
    narrowed in the same change ... Reviewers report the ones left in the functions a branch's diff adds or changes";
    the review skill has reviewers report there "an `Any`, or a `dict`, `list` or `tuple` whose items' types say less
    than is known", and DECISIONS.md ("Vague types are reported ...") says AGENTS.md "has a change narrow the ones in the
    functions it changes" (vague types), "so authors and reviewers go by one line". The docs reviewer.
  - **Scenario.** An author leaves a record's `dict[str, object]` that a `TypedDict` fits, on an unchanged line of a
    function they change, as AGENTS.md asks no more; a reviewer reports it under the skill.
  - **Fix (generation 3).** AGENTS.md's sentence names what the skill and the decision name: "an `Any`, or a `dict`,
    `list` or `tuple` whose items' types say less than is known, that it holds and could be narrower is narrowed ...
    Reviewers report what is left in ...". No check. Settled by reading.
  - **Resolution: done.**
    - **Fix:** AGENTS.md: "an `Any`, or a `dict`, `list` or `tuple` whose items' types say less than is known, that it
      holds and could be narrower is narrowed in the same change ... Reviewers report what is left in the functions a
      branch's diff adds or changes".

- [x] **SRV-144 · A launch whose record fails lets the lock go with its Designer unrecorded, and another launch's look then takes it for the user's** · follows SRV-141, generation 4 · `mcp_server/server_tools/lifecycle.py:16,351-353,368-376,388-390,836-842`, `designer_preferences.py:191`, `DECISIONS.md:212-214` · confirmed · found 2026-11-13
  - **Defect.** SRV-141's fix records the Designer inside `saved()`'s `with`, but a record that fails is kept as an
    error and the `with` ends: the lock goes with that Designer running and unrecorded, and `start()` ends it only
    afterwards (`_force_end`: SIGTERM, up to 5 s, SIGKILL, up to 5 s more). The same fix made the look under the lock
    run on every launch, not only when something was said. A launch waiting for the lock then takes it, its `check`
    asks `_appeared`, which finds that Designer in `_sorted_out`'s `here` (in no record, listening nowhere yet), and
    refuses. The claims that make it the user's: lifecycle's module docstring ("which a launch holds until its Designer
    is recorded"), `_start_designer`'s ("another launch ... then never takes this Designer for the user's"),
    `_appeared`'s ("which every launch holds until its Designer is recorded (SRV-141): one that appeared is the
    user's"), `saved()`'s comment, and DECISIONS.md's new sentence ("never takes an agent's for the user's").
    `start()`'s own look wouldn't refuse it (it is in `here`, which `_running_on` waits for, not `users`), so the look
    is stricter than the one it backs up. Two reviewers (the product code and the docs).
  - **Scenario.** Two launches side by side (pool workers, or two sessions): A's record fails (`ps` can't read its
    start, `_NoListing`; or the folder fills between `_record_error`'s probe and the write), A's `with` ends, B takes
    the lock, says nothing (A's copy is kept, a Designer runs), and is refused with "A Designer started as this one was
    about to (process N): ... ask the user to close it", N being A's Designer, which A is ending. Before SRV-141's fix
    B asked only when something was said.
  - **Fix.** The Designer whose record failed ended inside the `with`, before the lock goes (`_force_end`, its
    `_forget_started` taking the port's lock without waiting, so no deadlock; the reaper thread started first, as
    `_force_end` waits for `pgrep` to stop listing a child the server hasn't reaped), the lock then held up to about
    10 s on that path only; `start()` says what it says now. That keeps DECISIONS.md's sentence true; narrowing it
    instead takes the user. A unit test: a launch whose record fails, the lock probed as `_force_end` runs (held).
    Settled by reading.
  - **Resolution: done.**
    - **Test:** `test_lifecycle_env.py::test_a_launch_ends_the_designer_it_couldnt_record_before_letting_the_preferences_lock_go`
      failed (`[False]`: the lock let go before the Designer whose record failed was ended).
    - **Cause:** SRV-141's fix kept the record's error and let the `with` end; `start()` ended that Designer only
      afterwards, so for that moment it ran unrecorded with the lock free.
    - **Fix:** `_start_designer` ends it inside the `with` (`_force_end`, `_NoListing` read as not ended, as before) and
      returns the error with whether it was ended; `start()` says what it said. The reaper thread starts right after the
      process, before that, as on main (measured, macOS 26: `pgrep -f` doesn't list a child that has exited and isn't
      reaped yet, so `_force_end` sees it gone either way). `_start_designer`'s and `_appeared`'s docstrings, lifecycle's
      module docstring, `saved()`'s comment, and DECISIONS.md's sentence ("records the Designer it starts, or ends it when
      it can't, ...; one it can neither record nor end counts as the user's, as its error says"), so that it stays true.
    - **Also covered:** the record failing with `_NoListing` (`test_a_designer_whose_start_cant_be_read_is_ended`), the
      put-back once it is ended (`test_a_launch_that_ends_the_designer_it_couldnt_record_puts_back`) and both lines
      (`test_a_launch_it_couldnt_record_still_says_what_its_save_did`) as before. Mutation caught: the end after the lock
      goes. Live: `--only bridge`, 48/48, the user's plist identical to an export made before the run.
  - Questioned by TST-380 (2026-11-13).

- [x] **SRV-145 · Two result lines say what didn't happen: "this Designer's changes" where none started, "a Designer started meanwhile" where none could be listed** · follows SRV-127 and SRV-129, generation 2 · `designer_preferences.py:229-232,320-327`, `mcp_server/server_tools/lifecycle.py:359-362,425-430,826-831` · confirmed · found 2026-11-13
  - **Defect.**
    - `_not_saved` says "this Designer's changes to them won't (or may not) be put back"; since SRV-129's fix
      `_NotStarted` carries what `saved()` said into errors where no Designer started: Popen failing ("...won't be put
      back.\nDesigner could not be started from ...") or `_appeared` refusing ("...won't be put back.\nA Designer
      started as this one was about to ...").
    - Both looks in a put-back raise `PreferencesError('a Designer started meanwhile')` whenever `running()` is True,
      and `_any_designer` is True when Designers can't be listed (`_NoListing`): a `pgrep` that fails mid-put-back reads
      "couldn't be put back (a Designer started meanwhile), only partly: 50 of 122 ...", while `_appeared`, failing the
      same way, returns None and the launch goes ahead as if none had.
  - **Scenario.** The plist unreadable (every save fails, SRV-126's lasting state) and Designer's binary not
    executable: the error speaks of "this Designer's changes" just before saying no Designer started. A `pgrep` that
    fails under load: an agent is told a Designer started that none saw.
  - **Fix.** Smaller claims: "the changes of a Designer started now won't be put back" (or the not-saved part left out
    of `_NotStarted.said`); "a Designer started meanwhile, or Designers couldn't be listed" (or `running` telling the
    two apart). The tests pinning these wordings change with them. Settled by reading.
  - **Resolution: done.**
    - **Test:** `test_lifecycle_env.py::test_a_launch_whose_save_and_start_fail_speaks_of_no_designer_it_started` failed
      ("this Designer's changes" before "Designer could not be started"); the tests pinning both lines failed on the old
      wordings (`test_designer_preferences.py`: the failed save's, the unreadable file's, the lock's, the stop's;
      `test_lifecycle_env.py`'s `_NOT_SAVED` users and SRV-139's refusal).
    - **Cause:** `_not_saved` spoke of a Designer as if started, though `_NotStarted` carries it into errors where none
      was; the put-back's stop named one reason for a `running()` that is also True when Designers can't be listed.
    - **Fix (smaller claims):** "if a Designer is started now, its changes to them won't (may not) be put back";
      `STARTED`, "a Designer started meanwhile, or Designers couldn't be listed", for both stops; `saved()`'s docstring
      "its Designer's changes".
    - **Also covered:** uninstall's put-back, whose `running` is True while its listing fails too, says the same.
  - Questioned by INS-36 (2026-11-13).

- [x] **TST-379 · The launch tests with a home of its own read the user's real Designer project file** · `tests/unit/test_lifecycle_env.py:685-721`, `mcp_server/server_tools/lifecycle.py:296-307,356` · confirmed · found 2026-11-13
  - **Defect.** A launch with a home calls `_plugin_paths()`, which globs and parses the newest
    `default_project.sbsprj` in `_designer_data_dir()`: the user's `~/Library/Application Support/Adobe/Adobe Substance
    3D Designer/*/`. Neither conftest nor `_launch_with_home` replaces `_plugin_paths` or `_designer_data_dir` (the
    `defaults` fixture redirects `designer_preferences.users_data_dir`, the same folder, so that no test reads the
    user's log). It predates the branch (main's three crash-upload tests call `_launch_with_home` with a home); the
    branch adds about eleven such tests (the preferences launches). Only read, errors suppressed, and no test's outcome
    depends on it, but the first review's log says no unit test reaches "the user's log folder, home or Designers".
    The tests reviewer.
  - **Scenario.** Each unit run opens and parses the user's project file; a project file that lists plugin folders
    changes the environment the fake launches pass, unseen.
  - **Fix.** `no_real_designer_process` replaces `_plugin_paths` with a fixed string (the tests of `_plugin_paths`
    itself, which replace `_designer_data_dir`, take the real one through a `REAL_` alias, as `REAL_OWN_TEMP` is).
    Settled by reading.
  - **Resolution: done.**
    - **Test:** `test_lifecycle_env.py::test_no_unit_test_reads_the_users_project_file` (`_designer_data_dir` failing
      when asked for the user's folder) failed: "the user's Designer folder read".
    - **Cause:** conftest replaced the launch's other ways out to the machine, not `_plugin_paths`.
    - **Fix:** `no_real_designer_process` replaces `_plugin_paths` (a folder in the test's `tmp_path`), its docstring
      naming the project file; the tests of `_plugin_paths` itself call it as `REAL_PLUGIN_PATHS`.
    - **Also covered:** no other test file calls `_plugin_paths`; the one test checking the variable a launch passes
      replaces it itself, as before.

- [x] **INS-36 · Uninstall still says "a Designer runs" when Designers couldn't be listed** · follows SRV-145, generation 3 · `uninstall.py:181-187` · confirmed · found 2026-11-13
  - **Defect.** `put_back_preferences` falls back to `'a Designer runs'` when the put-back says nothing and the copy
    stays. That happens only when `running()` was True at `_put_back`'s first look, and uninstall's `running()` is
    `folders_in_use() is not None`, which on macOS is "Designer runs" or "Designer's processes couldn't be listed
    (...)". SRV-145's **Also covered** says uninstall's put-back says the same as the tools now; this line was missed.
    The product code reviewer.
  - **Scenario.** `plan()` lists the copy with `pgrep` working and no Designer running; when the user confirms, `pgrep`
    fails: the output reads "Could not remove the copy of Designer's preferences launch_designer saved ...: a Designer
    runs", though none runs.
  - **Fix.** Say what the check saw: keep `folders_in_use()`'s text from the call `running()` makes and return it, or
    `STARTED`'s wording ("a Designer runs, or Designers couldn't be listed"); the docstring with it; a unit test with
    `folders_in_use` failing only when the item runs. Settled by reading.
  - **Resolution: done.**
    - **Test:** `test_uninstall.py::test_says_when_designers_preferences_couldnt_be_put_back[the listing fails]` (no
      Designer at the plan, the listing failing when the item runs) failed: the line ended "...: a Designer runs".
    - **Cause:** the fallback named one reason for a check that is also True when Designer's processes can't be listed.
    - **Fix:** `put_back_preferences` keeps what `folders_in_use()` said in the check the put-back makes, and returns
      that ("a Designer runs" for "Designer runs", the listing's error otherwise); its docstring with it.
    - **Also covered:** the `[a Designer started meanwhile]` case still reads "a Designer runs"; a put-back that stops
      partway already says `STARTED` (SRV-145).

- [x] **TST-380 · DECISIONS.md's preferences entry changed by an agent: the user hasn't confirmed its new sentence, and its choices line and Reopen-if don't cover the end under the lock** · follows SRV-144, generation 5 · `DECISIONS.md:212-221` · confirmed · found 2026-11-13
  - **Defect.** SRV-144's fix changed what the entry says, not only a name or path: "records the Designer it starts,
    or ends it when it can't, before letting go of the lock", and "(one it can neither record nor end counts as the
    user's, as its error says)", which narrows "never takes an agent's for the user's". AGENTS.md and the
    address-review skill leave such a change to the user. The new sentence was shown to the user after the fix, who
    then asked to commit and review; nothing records that they agreed to it. The entry's choices line ends at "the
    record written under that lock rather than the look made only after a put-back", and its Reopen-if names only
    "holding the lock through the record", though the lock is now also held through `_force_end` (up to about 10 s).
    The docs reviewer.
  - **Scenario.** A later review drops a finding about a Designer that can be neither recorded nor ended as contradicting
    the entry, on a carve-out only an agent wrote.
  - **Fix.** The user's answer: if they agree, the choices line adds "then a Designer that can't be recorded ended under
    that lock" and the Reopen-if "through the record or the end"; if not, the carve-out goes and the case stays in
    REVIEW.md. Settled by reading.
  - **Resolution: done** (the user agreed to the new sentence, 2026-11-13).
    - **Fix:** DECISIONS.md's entry: its choices line adds "then a Designer that can't be recorded ended under that lock,
      one that can be neither recorded nor ended counting as the user's"; its Reopen-if "holding the lock through the
      record or that end (up to about 10 s)".

- [x] **TST-381 · The writing rule's examples drop part of the claim they rewrite, which the same section forbids** · `AGENTS.md:184-185,191,197-198` · confirmed · found 2026-11-13
  - **Defect.** "**Plain words.** 'If the start fails, the copy is removed', not 'removed when the start raises, not
    again'": the second half is `saved()`'s docstring ("A copy made here, not again, is removed when the start raises"),
    and the first drops "not again", though only a copy made fresh is removed (`fresh = none`, `if fresh: _dropped('')`)
    and a copy made again is kept. The section then says: "Rewriting for style never changes what a sentence claims ...
    the new wording must say exactly what the old one did." The subject-and-verb example drops "as the first Designer
    starts, unless one is there already" the same way, though its "..." marks a fragment. The docs reviewer.
  - **Scenario.** An agent applies "Plain words" to `saved()`'s docstring by the example and turns a true sentence into
    a false one: a copy made again said to be removed.
  - **Fix.** Examples whose plain half keeps the whole claim ("If the start fails, the copy it made is removed; a copy
    made again is kept"), or examples with no qualifier to lose. Settled by reading.
  - **Resolution: done.**
    - **Fix:** AGENTS.md's examples keep the whole claim: "The first launch saves a copy of the file, unless one is there
      already", not "Saved as the first Designer starts, unless one is there already: a copy of the file"; "If the start
      fails, a copy made for it is removed. A copy made again is kept", not "A copy made here, not again, is removed when
      the start raises".

- [x] **TST-382 · `no_real_designer_process` keeps `tmp_path: Any`** · `tests/unit/conftest.py:133,146` · confirmed · found 2026-11-13
  - **Defect.** The branch changes `no_real_designer_process` (TST-379's line, its docstring), and its `tmp_path` is
    pytest's `pathlib.Path`, annotated `Any`, unmarked: the new `lambda: str(tmp_path / 'plugins')` and the other uses
    go unchecked. The test files type this fixture `tmp_path: Path`. DECISIONS.md, "Vague types are reported only in
    the functions a branch's diff adds or changes", the lines it leaves as they were included. The tests reviewer.
  - **Scenario.** A typo on `tmp_path` in that fixture passes mypy strict.
  - **Fix.** `tmp_path: Path` (`from pathlib import Path`). Settled by reading.
  - **Resolution: done.**
    - **Fix:** `tmp_path: Path` (`from pathlib import Path`). No behaviour changed: the touched test files, lint and
      types pass before and after.

- [x] **TST-385 · The late material is stated as after either step where both were seen together, and agents aren't told of it** · follows TST-383, generation 2 · `tests/test_all_tools/editor_panels_and_fit/renders.py:93-94`, `REVIEW.md` (TST-383's Cause), `mcp_server/GUIDE.md:47-48` · confirmed · found 2026-11-13
  - **Defect.** `with_checker`'s docstring and TST-383's Cause: "after a call (that) switches the mesh or applies a
    graph". Both failures TST-383 quotes followed one call that did both (the orbit check's Rounded cube after the
    Plane, with `graph=`; the pan check's Plane after the Rounded cube, with `graph=`), as ROADMAP item 83 says ("a call
    that switched the mesh and applied a graph"). And GUIDE.md, which agents read, says to look at the material with
    `screenshot_designer('3d', graph=...)` with nothing of a material that may come late, though it keeps other facts
    "seen once". The docs reviewer.
  - **Scenario.** Whoever measures for ROADMAP item 83 takes a mesh switch alone as a known cause; an agent shown a
    plain mesh right after `graph=`, under load, concludes the graph is wrong and changes it.
  - **Fix.** "after a call that switched the mesh and applied a graph (seen once); shots after calls doing one of them
    wait too, as a defence"; and one line in GUIDE.md where it sends agents to the 3D view: the material once reached
    the mesh about 20 s late, under load (seen once): a plain mesh right after `graph=` may be late, shoot again before
    judging (ROADMAP item 83). Settled by reading.
  - **Resolution: done.**
    - **Fix:** `with_checker`'s docstring: the 3D view "once showed it late after a call that switched the mesh and
      applied a graph; shots after a call doing one of them wait too, as a defence". TST-383's Cause ("switches the mesh
      or applies a graph") stays as written: this entry corrects it. GUIDE.md, where it sends agents to the 3D view:
      "Once, under heavy load, the material reached the mesh about 20 s after a call that switched the mesh and applied
      the graph: a plain mesh right after `graph=` may be late, so shoot again before judging (ROADMAP item 83)."
  - Questioned by TST-388 (2026-11-13).

- [x] **TST-386 · `with_checker`'s pause is pinned by no test, and one check waits for a checker only the check before it puts there** · follows TST-383, generation 2 · `tests/unit/test_selftest_renders.py:112-115`, `tests/test_all_tools/editor_panels_and_fit/checks.py:90` · confirmed · found 2026-11-13
  - **Defect.**
    - The unit tests replace `asyncio.sleep` with a function that does nothing and records nothing: without the
      `await asyncio.sleep(1.0)`, or with `sleep(0)`, they all pass, and the 31 shots come back to back, maybe faster
      than the 20 s the wait is for. The threshold's edge isn't pinned either (the made-up checker has 7 changes, so
      `<=` for `<` passes).
    - `check_a_view_turns_the_camera` waits for the checker with neither `graph=` in its call nor one earlier in the
      check: it is there only because the check before it applied `VIEW3D_ADDED`. Run alone, as the live-check skill
      says to run a changed check, after only its category's preparation (which applies no graph), the mesh has the
      default material: 31 shots, about 30 s more, and "the checker didn't show on the mesh after 30 retakes", though
      the check passes.
    The tests reviewer.
  - **Scenario.** A pause dropped in a later edit passes the unit suite and the full run fails again in the slow case;
    an agent running the view check alone is told of a slow 3D view that isn't there.
  - **Fix.** The fake sleep records its argument, a test asserts the pauses (`[1.0, 1.0]`), and one shot at exactly
    `CHECKER` changes; the view check's call passes `'graph': VIEW3D_GRAPH`, setting what it measures on. Settled by
    reading.
  - **Resolution: done.**
    - **Test:** for the view check, a scratch run of `check_a_view_turns_the_camera` alone: 31 shots, about 49 s, and
      "the checker didn't show on the mesh after 30 retakes", the check passing. The unit tests' new assertions (the
      pauses, a shot at exactly `CHECKER` changes) pass on the code, as they guard it rather than reproduce a defect.
    - **Cause:** the fake sleep recorded nothing; the view check's call set no graph of its own.
    - **Fix:** `_shots_in_turn` returns the pauses asked; the retake test asserts `[1.0, 1.0]`, and a test takes a shot
      at exactly `CHECKER` changes once. The view check's call passes `'graph': VIEW3D_GRAPH`. Mutations caught: no
      pause, a pause of 0, `<=` at the edge. Scratch run of the view check alone after the fix: no retake.
    - **Also covered:** the other `with_checker` sites set the graph in their own call or earlier in the same check
      (`small` after `front` or `first`).

- [x] **TST-387 · Unmarked `Any` in the functions the diff adds or changes, in two unit-test files** · follows TST-383, generation 2 · `tests/unit/test_selftest_renders.py:96,103,106,108,123,135,143,151`, `tests/unit/test_selftest_summary.py:314` · confirmed · found 2026-11-13
  - **Defect.** `_plain(...) -> Any`, `_shots_in_turn(..., shots: list[Any]) -> tuple[Any, list[tuple[str, Any]]]`, its
    `calls: list[tuple[str, Any]]` and `c(name: str, args: Any = None) -> Any`, the four new tests' `renders: Any`, and
    `defined: set[Any]`, an unchanged line in `test_every_category_function_is_run`, which TST-383 changed. None is
    marked with a reason (AGENTS.md's typing rules; DECISIONS.md, "Vague types are reported only in the functions a
    branch's diff adds or changes"). The tests reviewer.
  - **Scenario.** A wrong key or argument in the new fake passes mypy strict.
  - **Fix.** `_plain` the array type `renders.py` uses; `args: dict[str, object] | None`, `calls: list[tuple[str,
    dict[str, object] | None]]`; `renders: ModuleType` (as TST-373 did for `pool()`), or each `Any` kept marked with
    its reason (a `SimpleNamespace` standing for a `CallToolResult`); `defined: set[Callable[..., object]]`. Settled by
    reading.
  - **Resolution: done.**
    - **Fix:** `_plain` returns the array type `renders.py` uses; `_shots_in_turn` takes `list[SimpleNamespace]` and
      returns a `Callable[[str, dict[str, object] | None], Awaitable[SimpleNamespace]]`, its calls (`Calls`) and its
      pauses; `ARGS: dict[str, object]`; the new tests' `renders: ModuleType`; `defined: set[Callable[..., object]]`. No
      behaviour changed: the touched test files, lint and types pass.

- [x] **HLP-125 · The put-back doesn't look again: a Designer the user brought forward during the shot is hidden again, or its window sent behind** · follows SRV-146, generation 2 · `mcp_server/designer_helpers/shot3d.py:158-164` · confirmed · found 2026-11-13
  - **Defect.** The `finally` hides Designer (`hide:`) or sends its window back (`orderBack:`) from the state read at
    the start. A hidden Designer shown, or a covered window brought in front, invites a click. Once the user makes
    Designer the active app, `hide:` hides the app they are working in and activates the next one, and `orderBack:`
    sends the window they type in behind the others, leaving it key (Apple's documentation of both). The product
    reviewer.
  - **Scenario.** A shot with `graph=` and a zoom takes several seconds. The user sees their hidden Designer appear,
    clicks into it, and it vanishes a moment later.
  - **Fix.** Before putting back, ask `isActive` (and, for a covered window, whether it is key). If the user took
    Designer up, leave it and say so. A unit test with the fake turning active during the shot. Settled by reading.
  - **Resolution: done.**
    - **Test:** `test_shot3d.py::test_a_designer_the_user_made_the_active_app_during_the_shot_is_left_on_screen`
      (hidden, covered) failed: Designer was hidden again, or its window sent back.
      `test_a_window_covered_while_designer_was_already_the_active_app_is_put_back` guards the other side. No live
      check: making Designer the active app in a run takes the user's keyboard.
    - **Cause:** the put-back read nothing again.
    - **Fix:** `_Screen` reads `isActive` at the start (`_MacWindow.active()`). At the put-back, a Designer that became
      the active app meanwhile is left on screen, with the line "left on screen, as Designer became the active app
      during the shot". The tool's docstring and README.md say so, and DECISIONS.md's entry, with the user's
      agreement.
    - **Also covered:** a minimized window stays up anyway (DECISIONS.md).

- [x] **HLP-126 · `orderBack:` sends Designer's window behind every window, which the tool calls "sent back behind the windows that covered it"** · follows SRV-146, generation 2 · `mcp_server/designer_helpers/shot3d.py:18,89-90,126,164`, `README.md` (Security), `mcp_server/server_tools/views.py:74-75` · confirmed · found 2026-11-13
  - **Defect.** `orderBack:` moves a window to the back of its level (Apple), behind windows it was in front of before
    the shot. The line returned to agents says "sent back behind the windows that covered it", the module docstring
    "sends it behind the other windows again", README.md and the tool's docstring "put back". The product and docs
    reviewers.
  - **Scenario.** The user's Designer, covered only by their editor, ends behind their browser and Finder too. The
    agent, told it was sent back behind what covered it, tells the user so.
  - **Fix.** Either put the window back in its place (the window just above it, from `CGWindowListCopyWindowInfo`, then
    `orderWindow:relativeTo:`; whether that takes another app's window is to be measured), or say what happens ("sent to
    the back, behind every other window") in the line, the docstrings and README.md. DECISIONS.md's entry says "put back
    after": the first keeps it true, the second asks the user. Settled by reading Apple's `orderBack:`.
  - **Resolution: done.**
    - **Test:**
      `test_shot3d.py::test_a_covered_window_is_brought_in_front_without_focus_and_put_back_behind_the_window_in_front_of_it`
      failed ('send back', not 'put below 7'). Live, check 2's covered way now has a window of Designer's own behind
      Designer's, and reads the order of Designer's windows (NSApp's `orderedWindows`). In its scratch run it failed
      with `order=cover,below,main`, then passed with `cover,main,below`.
    - **Cause:** `orderBack:` moves a window behind every window of its level.
    - **Fix:** measured first (`mac_window.py`'s docstring): CoreGraphics' list of the windows on screen above
      Designer's finds the one directly in front of it, Designer's own or another app's. `orderWindow:relativeTo:` puts
      Designer's window right behind either, and sends it to the back if that window is gone. `_Screen` records that
      window as it brings a covered window in front (again too), and puts it back behind it (`_MacWindow.above()`,
      `put_below()`), saying "put back behind the window that was in front of it". With none found, it uses `orderBack:`
      and says "sent to the back, behind the other windows". DECISIONS.md's "put back after" holds; README.md says "put
      back where it was".
    - **Also covered:** `_MacWindow` moved to a helper part of its own, `mac_window.py` (AGENTS.md, Keep each file to
      its main logic).
  - Questioned by HLP-130 and HLP-131 (2026-11-14).

- [x] **HLP-127 · `set_3d_view`'s refusals come after the window was put on screen: a refused call may leave the user's window un-minimized, and the docstring says what the arguments rule out is refused first** · follows SRV-146, generation 2 · `mcp_server/designer_helpers/shot3d.py:192-205`, `mcp_server/designer_helpers/view3d.py:508-545` · confirmed · found 2026-11-13
  - **Defect.** Before `_on_screen`, `shoot_3d` refuses only `_set_up_checked`'s cases and a 3D View panel not shown.
    `set_3d_view` refuses the rest inside it, before its first change: an orbit or pan of less than a pixel (`_drags`;
    the orbit's by the arguments alone), `tiling=` without the Parameters panel, `graph=` without the Explorer, missing
    tools or menu entries, a mesh with several materials. `shoot_3d`'s docstring: "What the arguments alone rule out,
    and a 3D View panel not shown, are refused first, before the window changes". The product reviewer.
  - **Scenario.** The user minimized Designer. An agent calls `screenshot_designer('3d', orbit=[0.2, 0])`, or `tiling=2`
    with the Parameters panel closed: the window comes up for good ("it stays so"), and the call is refused.
  - **Fix.** Run `set_3d_view`'s checks (everything before its first change) before `_on_screen`; none needs the window
    on screen. Or narrow the docstring and say a refused call may have un-minimized the window. A unit test for the
    orbit case. Settled by reading.
  - **Resolution: done.**
    - **Test:** `test_shot3d.py::test_a_set_up_refused_by_what_designer_shows_doesnt_touch_the_window` failed: the
      set-up's checks weren't run before the window changed. Live,
      `check_a_refused_3d_set_up_leaves_designers_window_as_it_was` (a minimized window, `orbit=[0.2, 0]`) failed in its
      scratch run, the window un-minimized and the line in the error, then passed.
    - **Cause:** `set_3d_view` checked and set up in one call, which `shoot_3d` made inside `_on_screen`.
    - **Fix:** `view3d.py`'s `_3d_set_up` holds `set_3d_view`'s checks and returns its steps, and `set_3d_view` runs
      both (`_3d_set_up(...)()`); its 66 unit tests pass before and after. `shoot_3d` calls `_3d_set_up`, and reads the
      mesh shown, before `_on_screen`, then runs the steps inside it. The checks work with the window minimized: check
      2's shots set up a pan from one.
    - **Also covered:** `_mesh_shown` is read before the window changes too.
  - Questioned by TST-398 (2026-11-14).

- [x] **SRV-147 · `mesh=''` or `view=''` alone is now refused, though the server treats '' as not given** · follows SRV-146, generation 2 · `mcp_server/server_tools/views.py:103,122` · confirmed · found 2026-11-13
  - **Defect.** `given` leaves out `''`, and `setup` maps `graph or None` but passes `mesh` and `view` as they came.
    `shoot_3d` is now called for every '3d' shot, and `_set_up_checked` refuses "unknown mesh ''". Before, a shot with
    nothing given was plain; `mesh=''` with another option was refused then too. The product reviewer.
  - **Scenario.** A client that fills optional strings with '' calls `screenshot_designer('3d', mesh='')`: refused,
    where the same call gave a plain shot on main.
  - **Fix.** `mesh or None, view or None` in `setup`, as for `graph`, and a unit test of the call. Settled by reading.
  - **Resolution: done.**
    - **Test:** `test_view3d.py::test_a_turn_pan_or_zoom_of_zero_or_an_empty_name_sets_nothing_up` (mesh '' and view '',
      panel '3d') failed: `shoot_3d(..., None, '', None, ...)`. graph '', and the 'graph' panel, passed already.
    - **Cause:** the server passed mesh and view as they came, though it counts '' as not given.
    - **Fix:** `mesh or None, view or None`, as for graph.
    - **Also covered:** tiling and zoom are numbers, and an orbit or pan of zeros was already None.

- [x] **HLP-128 · "Shoot again" can move the camera twice: drags given while the view isn't drawn are taken** · follows SRV-146, generation 2 · `mcp_server/designer_helpers/shot3d.py:42-46` (STALE), `mcp_server/server_tools/views.py:75-76`, `mcp_server/GUIDE.md:51` · measured · found 2026-11-13
  - **Defect.** STALE, the tool's docstring and GUIDE.md say "shoot again". `pan` and `orbit` move the camera from where
    it is then (the tool's docstring), and an agent shooting again repeats its call. The docs reviewer.
  - **Scenario.** Measured, in a Designer an agent started: with the window minimized by macOS, by Qt, covered or
    hidden, a pan by the helpers' own drag, then a plain `shoot_3d`. The render showed the pan each time, and matched
    one taken on screen 2 s later in the three ways where that could be read. So drags reach the camera while the view
    isn't drawn. An agent told its render is stale after `pan=[0.25, 0]` sends the call again, and the view shows 0.5
    beside a line saying 0.25.
  - **Fix.** Say "shoot again with no set-up" (a plain shot shows where the camera is) in the three places; the unit
    test of STALE's text follows. Settled by the probe above.
  - **Resolution: done.**
    - **Test:** `test_shot3d.py::test_a_render_still_identical_after_the_retakes_is_said` failed on STALE's text.
    - **Fix:** STALE says "Shoot again with no set-up before judging it: pan, orbit and zoom move the camera from where
      it is"; the tool's docstring and GUIDE.md's Look bullet say the same. That a pan given while the view isn't drawn
      reaches the camera is re-measured by TST-393's live check.
    - **Also covered:** GUIDE.md's Look bullet held the only other "shoot again".

- [x] **TST-392 · The focus check can't fail for a hidden Designer, and passes whatever happened when Designer was active before** · follows SRV-146, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py:733,749` · confirmed · found 2026-11-13
  - **Defect.** `state.get('active') == before.get('active')` compares the state read after the shot with the one read
    before `put`. For 'hidden', the state after is read once `hide:` has run, which deactivates the app (Apple), so an
    activation during the shot is undone before it is read. With Designer active before, the other three ways pass
    whatever the shot did, and 'hidden' fails, since `put`'s `hide:` deactivates it. DECISIONS.md's Reopen if ("showing
    it makes Designer the active app") rests on this check. The tests and docs reviewers.
  - **Scenario.** A change makes `unhideWithoutActivation` activate Designer: the check still passes. Or the user
    clicked the agent's Designer before the check: three ways pass blind, and 'hidden' fails. (A Designer the self-test
    starts wasn't active, measured.)
  - **Fix.** Read `isActive` inside the shot, before the put-back (a snippet wrapping `_on_screen`), or judge focus only
    when Designer wasn't active before and say so otherwise. Or narrow the docstring and SRV-146's claim to three ways.
    Settled by reading.
  - **Resolution: done.**
    - **Test:** `tests/unit/test_selftest_window_states.py` (focus kept, taken, and not judged when Designer was the
      active app before or a state wasn't read) failed first: there was no `window_states.focus`.
    - **Cause:** the check compared the state after with the one before, whatever that was, and hiding Designer again
      deactivates it.
    - **Fix:** check 2 judges focus through `window_states.focus`, only when Designer wasn't the active app before, and
      says when it can't. For 'hidden', HLP-125's put-back leaves a Designer the shot activated shown, so the state
      after (hidden=True expected) fails then. Seeing the check fail live would take the user's keyboard; the unit tests
      show the judgement.

- [x] **TST-393 · Four behaviours of the new 3D shot no test guards** · follows SRV-146, generation 2 · `tests/unit/test_shot3d.py:74,158-164,213`, `mcp_server/designer_helpers/shot3d.py:99-111,198-200` · confirmed · found 2026-11-13
  - **Defect.** `Shot` fakes `_3d_dock` as `object()` and `_on_screen` whole; the fixture's `_settle` records nothing;
    `test_off_macos_the_window_is_left_as_it_is` fakes `_mac_window` itself. Every test passes with any of these:
    `_3d_dock(mw)` moved inside `_on_screen` (the docstring: a 3D View panel not shown is refused before the window
    changes); `_mac_window` without its `sys.platform` gate (every 3D shot would then fail elsewhere than macOS, where
    `ctypes.util.find_library('objc')` finds nothing); `_settle(DRAW_WAIT)` removed from `_wait_on_screen`, or
    `DRAW_WAIT = 0`. A window minimized and Designer hidden at once is untested too. And no live check takes a plain
    shot of a window off screen, the commonest call: the window check pans, and the pan's drags and pause may hide a
    missing wait. The tests and docs reviewers.
  - **Scenario.** A later change drops the wait, or the gate: the suites pass, and a plain shot of a minimized window
    comes back stale, or every 3D shot fails on Windows.
  - **Fix.** Unit tests: `_3d_dock` raising leaves nothing done; `_mac_window` None off darwin (`sys.platform` patched);
    the wait after exposure recorded; minimized and hidden together. A live check: the view changed while the window is
    off screen, then a plain shot shows it (the probe's, measured passing in all four ways). Settled by reading.
  - **Resolution: done.**
    - **Test:** four unit tests in `test_shot3d.py`: the 3D View panel's refusal, `_mac_window` off darwin, the wait
      after exposure, a window minimized with Designer hidden. Each failed on a mutant: `_3d_dock` moved inside
      `_on_screen`, the gate removed, the wait removed, `hidden` read only when not minimized. Live,
      `check_a_plain_3d_shot_shows_a_change_made_while_designers_window_was_off_screen` passed in all four ways (10.96
      grey levels from the view before, 0.00 from one on screen after), and failed in all four on a mutant asking macOS
      nothing (0.00 from the view before).
    - **Cause:** the fakes stood in for each of these, and the window check only panned.
    - **Fix:** the tests above.

- [x] **TST-394 · The window states' parser sits in `checks.py`** · follows SRV-146, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py:651-659` · confirmed · found 2026-11-13
  - **Defect.** `_states` parses what `window_states`' snippets print. AGENTS.md (Keep each file to its main logic) puts
    a parser in a module beside the file: here `window_states.py`, next to the snippets it reads. The tests reviewer.
  - **Scenario.** A reader of `checks.py` meets the parsing before the checks, and a change to a snippet's line has its
    parser in another file.
  - **Fix.** Move `_states` to `window_states.py`. No behaviour changes: the checks' scratch run before and after.
    Settled by reading.
  - **Resolution: done.**
    - **Test:** `test_selftest_window_states.py::test_the_last_state_line_of_each_kind_is_read` failed first: there was
      no `window_states.states`.
    - **Fix:** `_states` moved to `window_states.states`, which checks 1 and 2 and the new checks call. The window
      checks' scratch runs passed after.

- [x] **HLP-129 · Unmarked `Any` and vague containers in the functions the 3D shot's fix added or changed** · follows SRV-146, generation 2 · `mcp_server/designer_helpers/shot3d.py:53,99,104,120,167,200`, `mcp_server/designer_helpers/screenshots.py:45,60`, `mcp_server/designer_helpers/view3d.py:511,525-526,546`, `tests/unit/test_shot3d.py:67,200,206,263,276,300`, `tests/unit/test_view3d.py:145,169,173,183` · confirmed · found 2026-11-13
  - **Defect.** AGENTS.md's typing rules: in the functions a branch changes, an `Any` is narrowed, or marked on its line
    with its reason. Unmarked: `mw: Any` (`_MacWindow.__init__`, `_mac_window`, `_wait_on_screen`, `_on_screen`,
    `_mesh_shown`); `keep: list[Any]` (`_mesh_shown`, `shoot_3d`, `_3d_render`, `set_3d_view`); `_3d_render`'s `-> Any`
    (a QImage); `set_3d_view`'s `camera: Any`, `light: Any` and `pressed: list[Any]`. In the tests: `windowHandle() ->
    Any`, the fakes' `mw: Any`, `options: dict[str, Any]`, `result: Any` and `value: Any`. `screenshots.py`'s module
    comment ("Qt widgets are Any in signatures") isn't the rule's mark. The product and tests reviewers.
  - **Scenario.** mypy checks nothing through them: a wrong attribute on the window, or a fake drifting from the code,
    passes.
  - **Fix.** `keep: list[object]`, `pressed` a `list` of its tuple, the tests' `object`, `SimpleNamespace`, `dict[str,
    object]` and `list[str | Image]`, and the Qt ones marked (`# Any: <reason>`) or given Qt types where the part can
    name them. Types only: the touched tests, lint and types before and after. Settled by reading.
  - **Resolution: done.**
    - **Fix:** `keep: list[object]` (`_mesh_shown`, `shoot_3d`, `_3d_render`, `_3d_set_up`). The Qt widgets and the
      QImage are marked on their lines (`# Any: ...`, with screenshots.py's reason), and so are `camera`, `light` (Qt
      actions) and `pressed` (`_drag`'s record). In the tests: `windowHandle() -> SimpleNamespace`, `mw: object`,
      `options: dict[str, object]`, `result: list[str | Image]`, `value: object`. Types only: lint, types and the
      touched tests pass.
  - Questioned by HLP-132 (2026-11-14).

- [x] **HLP-130 · The put-back sends Designer's window behind every window when the window in front of it has gone off screen, or none was found, and says it put it back behind that window** · follows HLP-126, generation 3 · `mcp_server/designer_helpers/shot3d.py:116-118,144-149`, `mcp_server/designer_helpers/mac_window.py:120-124` · measured · found 2026-11-14
  - **Defect.** `put_back` puts the window right behind the one recorded in front of it, or sends it to the back when
    none was recorded: `elif self._behind is not None: mac.put_below(self._behind)`, then `else: mac.send_back()`.
    - Given a window no longer on screen, `orderWindow:relativeTo:` sends Designer's window behind every window
      (`mac_window.py`'s docstring for a window that doesn't exist; the probe below for a minimized one). The line still
      says "put back behind the window that was in front of it".
    - `above()` returning None means no normal window was in front of Designer's. `orderBack:` then moves the
      front-most normal window to the back.
    - `_bring` sets `_covered` before `_behind = mac.above()`, so an abort landing in `above()` ends at `orderBack:`
      too.

    The product reviewer.
  - **Scenario.** Measured, in a Designer an agent started, with a window of Designer's own standing for the user's:
    - Designer's window put right behind that window, on screen: 1 normal window in front of it, 4 behind.
    - The same window minimized, or closed: 4 in front, 0 behind, so behind every window.
    - Covered whole by an always-on-top window (Qt's `WindowStaysOnTopHint`, layer 8): `above()` found none. The shot
      was taken and its render was fresh: it showed a pan made under the cover. 0.5 s later Designer's window, the
      front-most normal window before, was behind all 4 others, and the line said "sent to the back, behind the
      other windows".

    So a user who closes or minimizes the editor that covered Designer while a shot of several seconds runs (`graph=`
    and a zoom) finds Designer sent behind everything. Closing the editor alone would have left it in view, and the
    agent is told it was put back behind that editor.
  - **Fix.** Before `put_below`, check that the recorded window is still on screen (CoreGraphics' on-screen list, or
    `kCGWindowListOptionIncludingWindow` and `kCGWindowIsOnscreen`). When it isn't, or when none was found, leave
    Designer's window where it is, in front, where it would be without the shot, and say so in the line. Read
    `above()` before setting `_covered`. `orderBack:` then has no case left. Unit tests: the recorded window gone, and
    none found. Settled by the probe above.
  - **Resolution: done.**
    - **Test:** three tests in `test_shot3d.py` failed first:
      - `test_a_covered_window_with_no_window_found_in_front_is_left_in_front`, with 'send back';
      - `test_a_covered_window_whose_window_in_front_went_off_screen_is_left_in_front`, with 'put below 7';
      - `test_an_abort_while_the_window_in_front_is_looked_for_leaves_nothing_to_put_back`, with 'send back'.

      Live, `check_a_covered_window_goes_back_behind_its_cover_or_stays_in_front_once_the_cover_is_gone` failed in its
      scratch run:
      - the cover closed during the shot left `order=below,main` and the line "put back behind the window that was in
        front of it";
      - the cover minimized left `below,main,cover`;
      - under an always-on-top window, `cover,below,main`.

      It then passed with `main,below`, `main,below,cover` and `cover,main,below`, and the lines below. The whole
      `editor_panels_and_fit` category passed, 64 checks.
    - **Cause:** the put-back trusted the window recorded at the start, whatever became of it. It took "none found" as
      "send it to the back". And `_bring` set `_covered` before it looked for the window in front.
    - **Fix:** `_MacWindow.on_screen(number)` reads CoreGraphics' list of the windows on screen, through `_listed`,
      which `above()` now shares. `put_back` puts the window behind the recorded one only while that one is on screen.
      Otherwise it leaves Designer's window in front and says "left in front, as the window that was in front of it is
      no longer on screen". With none found it says "left in front, as no window was found in front of it". `_bring`
      reads `above()` before it sets `_covered`. `send_back` (`orderBack:`) has no case left and is gone, from the
      fake too. `mac_window.py`'s docstring adds the measured facts: a minimized window too, and none found under an
      always-on-top window. `_Screen`'s docstring gives the cases.
    - **Also covered:** README.md's "put back where it was" and the tool's docstring still hold: left in front is where
      the window would be without the shot. `CFNumberGetValue`'s type argument is now `c_long`, as the header's
      `CFIndex` (the product reviewer's note).
  - Note (2026-11-14): the final check failed on its live check's always-on-top case (723 of 724 live checks; the unit
    suite passed). The tool said "put back behind the window that was in front of it", and the order after was
    `cover,main,below`, as expected. A normal window had come in front of Designer's, under the cover, between the
    check's set-up and the shot, most likely another worker's Designer opening. So the tool found that window and put
    Designer's back behind it, which is right; the check expected "no window was found" alone.
  - **Resolution: done** (the live check).
    - **Test:** a scratch run forced the full run's case: a normal window of Designer's own brought in front of
      Designer's, under the always-on-top cover, before the shot. The tool said "put back behind the window that was
      in front of it", with the order `cover,later,main,below`, which the check refused before this fix. It passes
      now, and so does the same check run plainly, all four cases each time.
    - **Fix:** in the cases where Designer's window stays in front (the cover closed or minimized, the always-on-top
      cover), the check also accepts "put back behind the window that was in front of it". A normal window coming in
      front meanwhile is then the one in front. The order of Designer's windows stays the guard: on the old code it
      failed in every case. The check's label states what is expected, and its detail gives the line said.

- [x] **HLP-131 · A window covered at the start and again during the shot is put back behind the later window, in front of the one that covered it** · follows HLP-124 and HLP-126, generation 3 · `mcp_server/designer_helpers/shot3d.py:116-118` · confirmed · found 2026-11-14
  - **Defect.** `_bring` records the window in front each time it brings a covered window in front, the first time and
    on `again()`: `if covered: self._covered = True; self._behind = mac.above()`. A second record replaces the first,
    and the put-back puts Designer's window right behind the second window only. HLP-126's resolution says "(again
    too)". All three reviewers, and the lead.
  - **Scenario.** The user's editor X covers Designer. A `graph=` shot brings Designer in front of X. The user clicks
    their terminal Z, which comes over Designer. `again()` records Z and brings Designer in front again. The put-back
    leaves Z, Designer, X: Designer now covers the editor that covered it, where README.md says it is "put back where
    it was afterwards". In the final check, another worker's Designer window opening over this one during check 2's
    covered shot leaves `order=main,cover,below`, a false failure.
  - **Fix.** Record the window in front only the first time (`if covered and not self._covered`). Fall back to a later
    record only when the first is no longer on screen (HLP-130's check). A unit test: covered by 7 at the start, by 9
    during the shot, then `put below 7`. Settled by reading, on `orderWindow:relativeTo:` as measured (`mac_window.py`;
    HLP-130's probe: right behind a window on screen).
  - **Resolution: done.**
    - **Test:**
      `test_shot3d.py::test_a_window_covered_again_during_the_shot_goes_back_behind_the_window_that_covered_it_first`
      failed with 'put below 9'.
      `test_a_window_covered_again_after_its_first_cover_went_off_screen_goes_back_behind_the_later_one` guards the
      fallback; it passed before too, as the old code always took the later window. Live, the put-back check's
      'covered again during the shot' case failed in its scratch run with `order=later,main,cover,below`, then passed
      with `later,cover,main,below`.
    - **Cause:** each look overwrote the window recorded in front.
    - **Fix:** `_bring` keeps the first window found while that window is on screen, and takes a later one only once it
      isn't (`on_screen`, HLP-130).
    - **Also covered:** a mutant always taking the later window fails the first test, and one never falling back fails
      the second. Check 2's covered way, which another worker's window could fail falsely, now goes back behind its
      cover too.

- [x] **HLP-132 · The `Any` marks on three locals and a nested function give a reason that holds only for signatures read as the helpers load, and a new test's `Any` is unmarked** · follows HLP-129, generation 3 · `mcp_server/designer_helpers/view3d.py:522-523,546`, `mcp_server/designer_helpers/shot3d.py:203`, `tests/unit/test_selftest_renders.py:49` · confirmed · found 2026-11-14
  - **Defect.** screenshots.py's reason is "annotations are evaluated when the helpers load". It doesn't hold here:
    - `camera: Any = None  # Any: a Qt action (screenshots.py: Qt widgets are Any in signatures)`, `light: Any = None`
      and `run()`'s `pressed: list[Any] = []  # Any: a drag's button down, (button, x, y), _drag's own record` are
      locals. Python never evaluates a local's annotation, and `_3d_set_up` imports `QtCore` already.
    - `shoot_3d`'s nested `def render() -> Any:  # Any: a QImage (...)` is evaluated when `shoot_3d` runs, where
      PySide6 can be imported first.
    - The new test `test_a_middle_row_on_the_edge_between_two_rows_of_squares_still_counts_the_checker(renders: Any)`
      has no mark. The file's other new tests take `renders: ModuleType`.

    The product and tests reviewers.
  - **Scenario.** mypy checks nothing through them: a wrong attribute on a tool, or a wrong item in the drag's record,
    passes.
  - **Fix.**
    - `pressed: list[tuple[QtCore.Qt.MouseButton, float, float]]`: `_drag` appends `(button, x + dx, y + dy)`, its x and
      y floats.
    - `camera` and `light`: `QtGui.QAction | None`, narrowed where `run()` uses them (`_navigation_tools` returns two
      of a toolbar's `actions()`).
    - `render() -> QtGui.QImage`, with `from PySide6 import QtGui` in `shoot_3d`.
    - `renders: ModuleType`.

    Types only: the touched tests, lint and types before and after. Settled by reading.
  - **Resolution: done.**
    - **Fix:**
      - `pressed: list[tuple[QtCore.Qt.MouseButton, float, float]]`.
      - `camera` and `light`: `QtGui.QAction | None`. `run()`'s moving block now tests them (`if camera is not None and
        light is not None`), which is `moving`, as they are looked up exactly then.
      - `render() -> QtGui.QImage`, with `QtGui` imported in `shoot_3d`. Its result is annotated on a local, as mypy
        refuses returning `_3d_render`'s `Any` (no-any-return).
      - `renders: ModuleType`.

      Types and that narrowing only: lint, types and the touched tests pass (268), and so does the category's scratch
      run.
    - **Also covered:** the other `# Any:` marks in `shot3d.py` and `view3d.py` are on signatures, where the reason
      holds.

- [x] **TST-396 · The check of a window covered during the shot compares a shot shrunk to 700 px with a render at its own size** · follows HLP-124, generation 3 · `tests/test_all_tools/editor_panels_and_fit/checks.py:841` · confirmed · found 2026-11-14
  - **Defect.** `moved = (plane_middle(grey(base))[0] - plane_middle(grey_file(path))[0]) / grey(base).shape[1]`. `base`
    is `screenshot_designer`'s image, shrunk to fit `max_size` 700 (`THREE_D`; `im.thumbnail` in `views.py`). `path`
    is the render `shoot_3d` saved inside the snippet, never shrunk. The tests reviewer.
  - **Scenario.** Agents' Designers take the user's layout. With the 3D view rendering 850 px wide, `base` is 700 px,
    and a pan of exactly 0.25 measures about 0.196, outside 0.24 to 0.26. The check then fails in the final check
    while the tool is right. The scratch runs passed because their renders were 340 to 440 px wide.
  - **Fix (generation 3: no new check).** Measure each middle as a fraction of its own image's width, or shrink the
    saved render as the tool does. Settled by reading.
  - **Resolution: done** (generation 3: no new check).
    - **Test:** `test_selftest_renders.py::test_a_planes_move_is_measured_as_a_fraction_of_each_renders_width` failed
      first, as there was no `moved_left`. It measures a quarter of an 850 px render against the shot shrunk to 700:
      0.25, where the old formula gives 0.196.
    - **Cause:** the check divided both middles by the shrunk shot's width.
    - **Fix:** `renders.moved_left(before, after)` takes each middle as a fraction of its own render's width, and check
      4 uses it. Check 4 passed in the category's scratch run. Its renders were narrower than 700 px there, a case the
      old formula got right too; a wider 3D view wasn't run.
    - **Also covered:** check 2 and the two camera checks with the same formula ("drags with Selection on", "the user's
      mouse moving in a drag") use it too. Their two shots have the same size, so their results don't change.

- [x] **TST-397 · The fake macOS says a minimized window isn't covered, so nothing guards a minimized window from being sent behind after the shot** · follows SRV-146, generation 2 · `tests/unit/test_shot3d.py:38-39`, `mcp_server/designer_helpers/shot3d.py:111` · confirmed · found 2026-11-14
  - **Defect.** `Mac.covered()` returns `self.state['covered']` alone. macOS reports a minimized window as covered:
    `_MacWindow.covered()`'s docstring says so, and check 1's STATE lines read `minimized=True ... covered=True` every
    time in the ninth review's runs. So nothing tests the guard in `covered = not minimized and not hidden and
    mac.covered()`. The mutant `covered = mac.covered()` passes every unit test, and check 2's minimized way too, which
    reads `minimized`, the line and focus. With that mutant, a minimized window is un-minimized, then put behind the
    window recorded in front of it or sent to the back. DECISIONS.md says it is left up. The tests reviewer.
  - **Scenario.** A later change drops the guard and the suites pass. Every 3D shot of a minimized window then
    un-minimizes it and puts it behind the user's windows.
  - **Fix.** The fake's `covered()` returns True while minimized or hidden too, as macOS does.
    `test_a_minimized_window_is_shown_without_focus_and_stays_so` then fails on the mutant. Settled by reading and the
    ninth review's measured states.
  - **Resolution: done.**
    - **Test:** `test_a_minimized_window_is_shown_without_focus_and_stays_so` failed on the mutant `covered =
      mac.covered()`: the window was put below 7. Every test passes on the code.
    - **Cause:** the fake's `covered()` said False for a minimized or hidden window, where macOS says True.
    - **Fix:** the fake `Mac.covered()` is True while minimized or hidden too, and its `above()` follows it. The code is
      unchanged.

- [x] **TST-398 · Three docs say other than the code: the refusals before the window changes, a designer fact's label, the checker's rows** · follows HLP-127, TST-391 and TST-395, generation 3 · `mcp_server/designer_helpers/shot3d.py:192-193`, `tests/test_all_tools/editor_panels_and_fit/checks.py:676`, `tests/test_all_tools/editor_panels_and_fit/renders.py:1-3` · confirmed · found 2026-11-14
  - **Defect.**
    - `shoot_3d`'s docstring says "Everything the set-up checks, and a 3D View panel not shown, is refused first,
      before the window changes". Some of the set-up's refusals come later, in its steps. With `mesh=` and `tiling=`,
      the new mesh's material is checked once it shows (`_set_tiling`, then `_material`: "the 3D view's mesh has %d
      materials"). `graph=`'s row in the Explorer is checked as it is selected (`_apply_outputs` and `_row_point`:
      "wasn't selected in the Explorer", "row isn't showing in the Explorer (a filter?)"). `set_3d_view`'s docstring
      names the first case.
    - Check 1's label, "the 3D view's render isn't drawn while Designer's window is minimized, covered or hidden, and
      is partly covered", reads as not drawn while partly covered. The check asserts that it is drawn (`drawn ==
      ['on screen', *window_states.DRAWN]`).
    - `renders.py`'s module docstring says "how often its middle row turns from dark to light". Since TST-395,
      `transitions()` keeps the most of three rows.

    The docs reviewer.
  - **Scenario.** Whoever maintains `shoot_3d` reads that no refusal can follow a window change. A reader of a run's
    summary takes the partly covered window as not drawn. Whoever looks into "the checker didn't show" reads the
    middle row alone.
  - **Fix (generation 3: smaller claims).**
    - `shoot_3d`'s docstring: what `_3d_set_up` checks is refused first. What the steps find as they go is refused
      after, with the window's lines in the error: with `mesh=` and `tiling=`, the new mesh's material, and the
      graph's row in the Explorer.
    - The label: "..., and is drawn while partly covered".
    - renders.py: "how often a row near its middle (the most of three) turns from dark to light".

    Settled by reading.
  - **Resolution: done** (generation 3: smaller claims).
    - **Test:** docs only; the tests that validate the docs pass.
    - **Fix:**
      - `shoot_3d`'s docstring: what `_3d_set_up` checks is refused first. What the steps find as they go is refused
        after, with the window's lines in the error: with mesh= and tiling=, the new mesh's material; with graph=, its
        row in the Explorer.
      - Check 1's label: "the 3D view's render is drawn while Designer's window is partly covered, not minimized,
        covered or hidden".
      - `renders.py`'s module docstring: a row near its middle, the most of three, and the move between two renders.

- [x] **TST-402 · Two put-back orderings no unit test guards: a minimized window left up when Designer became active, and a hidden Designer waited for before its windows turn opaque** · `tests/unit/test_shot3d.py:444-456`, `mcp_server/designer_helpers/shot3d.py:207-237` · confirmed · found 2026-11-14
  - **Defect.** `put_back` checks `mac.active() and not self._was_active` before `mac.minimize()`, and waits off screen
    for `self._minimized or self._hidden`. The active test is parametrized for 'hidden' and 'covered' only, and the
    wait is tested only with a minimized window. HLP-125's "a minimized window stays up anyway" no longer holds: a
    minimized window is now minimized again.
  - **Scenario.** `minimize()` moved above the active check minimizes the window from under a user who switched to
    Designer during the shot; `or self._hidden` dropped makes a hidden Designer's windows opaque while still on
    screen. Every unit test passes either way.
  - **Fix.** Add `('minimized', ['fade', 'show', 'unfade'])` to the active test, its last line LEFT; and a hidden
    Designer with `mac.slow = 2`, the two waits before `*EVERY_BACK`.
  - **Resolution: done.**
    - **Test:** the 'minimized' parameter of
      `test_a_designer_the_user_made_the_active_app_during_the_shot_is_left_on_screen`, and
      `test_a_window_put_back_off_screen_is_made_opaque_only_once_off_screen[hidden]`. Both pass on the code,
      which was right; each failed on a mutant of `put_back`: `minimize()` moved above the active check, and
      `or self._hidden` dropped from the wait.
    - **Fix:** the two tests.
    - **Also covered:** HLP-125's "a minimized window stays up anyway" is out of date; this test guards that case.

- [x] **TST-403 · No live check reads a hidden Designer's other windows, and the clean-up restores only the main one** · `tests/test_all_tools/editor_panels_and_fit/window_states.py:47-50,93-104`, `tests/test_all_tools/editor_panels_and_fit/checks.py:805-855` · confirmed · found 2026-11-14
  - **Defect.** For a hidden Designer the shot makes every window of Designer's transparent (`_fade(every=True)`),
    but `state()` and `_CLEAR` read and restore `mac.windows(False)[0]` only.
  - **Scenario.** `windows(every=True)` misreading NSApp's array, or `unfade` missing a window, passes every live
    check: the user's other Designer windows show during the shot, or stay invisible after it, and a window left so
    stays for the category's later checks.
  - **Fix.** In the hidden cases, read each window's look before the put, at each render and after the shot (the
    count that differs from before), and have the clean-up put back the looks read before, not force them opaque.
  - **Resolution: done.**
    - **Test:** the transparency check reads, at each render and after the shot, how many of Designer's windows aren't
      opaque and clickable (`state()`'s `windows=` and `faded=`): all of them for a hidden Designer, one otherwise, none
      after. It passed on the code, and failed in a scratch run whose shot's `_fade` ignored `every` (the hidden case:
      1 of 8).
    - **Fix:** `state()` counts them; `_PUT` records each window's look, holding each, and `_CLEAR` puts them back and
      ends the holds.
    - **Also covered:** the clean-up after every window check now puts back every window's look, not only the main
      window's.
  - Questioned by TST-411 (2026-11-14).

- [x] **TST-404 · The transparency check requires exactly two renders, so a retaken render fails it** · `tests/test_all_tools/editor_panels_and_fit/checks.py:837` · confirmed · found 2026-11-14
  - **Defect.** `len(seen) == 2  # before the pan and after it`, but `shoot_3d` takes a render identical to the one
    before the pan again, up to RETAKES times, and each prints a RENDER line.
  - **Scenario.** Under the full run's load the first render after the pan is still the last frame: three or more
    RENDER lines, all transparent, and the check fails on transparency in the final check.
  - **Fix.** `len(seen) >= 2`; `looks == [during]` still judges each render.
  - **Resolution: done.**
    - **Test:** the transparency check run with the first render after the pan made stale once (a scratch-only
      rebinding of `_3d_render`): it failed before the fix (3 renders, in all four cases) and passed after.
    - **Fix:** `len(seen) >= 2`.

- [x] **HLP-135 · `shot3d.py`'s abort claims say more than the code does, a docstring misleads on the Qt-minimized page, and `opaque_first`'s change isn't recorded** · `mcp_server/designer_helpers/shot3d.py:105-106,124-133,135-144,244,253-256` · confirmed · found 2026-11-14
  - **Defect.**
    - `_fade`'s docstring: "each held first ..., then how it looked recorded, so an abort leaves no change
      unrecorded". The hold is the change before its record: an abort between them leaks a retain (never a release
      too many), and so does one between `del self._faded[window]` and `mac.let_go(window)`.
    - The handler's comment: "an abort landing in put_back skips the rest of it, the windows' opacity too".
      `put_back`'s own `finally` restores the look for an abort anywhere in its body; the handler is needed only for
      one before that `try` or inside `unfade`.
    - `_Screen`'s "brought in front too, as before" reads as transparent like the cases above it; that window is
      brought in front opaque and left there.
    - `opaque_first` sets the opacity, then click-through, unrecorded: an abort between the two leaves the window
      opaque but click-through until the next shot.
  - **Scenario.** A maintainer takes `put_back`'s `finally` for dead code, or the hold order for safe; an abort landing
    in `opaque_first` (after a shot that left the window transparent) leaves Designer looking frozen to clicks.
  - **Fix.** Narrow the docstring and the comment to what the code does; say "opaque, and left in front" for the
    Qt-minimized page; have the handler run `opaque_first` again too.
  - **Resolution: done.**
    - **Test:** `test_an_abort_while_a_window_left_transparent_is_made_opaque_still_leaves_it_opaque_and_clickable`
      failed before the fix (the window stayed transparent: nothing recorded `opaque_first`'s change) and passes after.
    - **Fix:** `_on_screen`'s handler runs `opaque_first` after `unfade`. `_fade`'s and `unfade`'s docstrings say an
      abort may leak a hold and never ends one twice. The handler's comment says which aborts it is for. `_Screen`
      says the Qt-minimized page's window is brought in front opaque and left there.
    - **Also covered:** no other docstring or comment says an abort leaves no change unrecorded.

- [x] **HLP-136 · A user who switches to Designer during a shot sees no window until it ends, and a click then undoes the switch** · `mcp_server/designer_helpers/shot3d.py:198-200,223-225` · confirmed · found 2026-11-14
  - **Defect.** Only `put_back` checks whether the user made Designer the active app
    (`if mac.active() and not self._was_active:`). Until then the window stays transparent and click-through:
    `again()` looks only for a window covered, minimized or hidden.
  - **Scenario.** A shot with `graph=`, `view=` and `tiling=` keeps the window in front for several seconds. The user
    switches to Designer (Cmd-Tab). They see its menu bar but no window, and what they type goes to that invisible
    window. A click on it goes through to the window under it (the measured click-through fact), which makes that
    app the active one. `put_back` then finds Designer not active and minimizes or hides the window again, though
    README says "If you switch to Designer during the shot, it stays up".
  - **Fix.** Once `mac.active() and not self._was_active`, make the windows opaque and clickable at once (`unfade`)
    and record it, so `put_back` leaves the window up. Check in `again()`, and between the set-up's steps where that
    is cheap. A unit test with `active()` turning True before a render.
  - **Resolution: done.**
    - **Test:** `check_a_3d_shot_makes_designers_window_opaque_at_once_once_designer_is_the_active_app`, Designer the
      active app from the set-up's start as the helpers see it (`window_states.switched`), so the user's keyboard
      stays where it is. In its scratch run it failed before the fix (the render after the set-up transparent and
      click-through, nothing said) and passed after (opaque at that render, said, left up). Unit tests failing before:
      in `test_shot3d.py`, `test_designer_made_the_active_app_during_the_shot_is_made_opaque_at_once_and_left_up`
      (minimized, covered and hidden, before a set-up step and before a render),
      `test_a_window_put_on_screen_again_while_the_user_is_in_designer_isnt_made_transparent`,
      `test_designer_made_the_active_app_then_left_during_the_shot_is_put_back`,
      `test_a_designer_already_the_active_app_before_the_shot_stays_transparent_during_it` and
      `test_the_set_up_is_given_the_screens_look_at_the_active_app_for_each_step`; in `test_view3d_helpers.py`,
      `test_the_set_up_runs_the_shots_look_at_the_active_app_before_each_step`.
    - **Cause:** only `put_back` asked whether the user had made Designer the active app. Until then nothing gave the
      windows their look back.
    - **Fix:** `_Screen.between()` makes the windows opaque and clickable at once, and says so, once Designer is the
      active app and wasn't as the shot began. `again()` runs it before each render. The set-up runs it before each
      step: `_3d_set_up`'s steps take it, and `shoot_3d` passes `screen.between`. While Designer is that app, a window
      put on screen again isn't made transparent, and its line leaves out "transparent". Unlike the suggested fix,
      nothing is recorded: a user who goes back to another app before the shot ends finds the window put back as it
      was found, as on `main`. README says the window stays up if Designer is still the app in front when the shot
      ends.
    - **Also covered:** `set_3d_view` runs the same steps without the look, as no window is changed there.
  - Questioned by HLP-138, TST-409, TST-410 and HLP-140 (2026-11-14).

- [x] **TST-405 · The menu check passes when the popup watch sees none of Designer's windows** · follows HLP-134, generation 2 · `tests/test_all_tools/editor_panels_and_fit/popups.py:45-62,89-100`, `tests/test_all_tools/editor_panels_and_fit/checks.py:785`, `tests/unit/test_selftest_popups.py:25` · confirmed · found 2026-11-14
  - **Defect.** `_watch` counts every try (`self.samples += 1`), also when the list is empty or holds no window of
    `pid`, and the check asks only `watch.samples > 100 and watch.shown_ms <= POPUP_MS`. The unit test watches a
    process with no windows, so a `_popup_shown` that always returns False passes it.
  - **Scenario.** A wrong pid, a self-test process the window server lists nothing to, or a later macOS listing popups
    below layer 100: the watch sees nothing, and the check passes as "0 ms" with the menu fully on screen.
  - **Fix.** Count the samples whose list held a window of `pid`, and require more than 100. The shot keeps Designer's
    main window on screen, transparent: measure that it is listed then. Unit-test `_popup_shown`'s pid, layer and
    alpha filters with fake `cg` and `cf`.
  - **Resolution: done.**
    - **Test:** in `test_selftest_popups.py`, the tests of `_seen` (the pid, layer and alpha filters, no list, the list
      released) and the watch's `listed` count on a process with no window, failing before (no `_seen`, no `listed`).
      The live menu check failed in its scratch run before the change (no `listed`) and passed after: 0 ms on screen,
      and 12,460 samples of 12,626 listing one of Designer's windows. Watching a wrong pid (a scratch-only subclass of
      `PopupWatch`), it now fails with 0 listing, where by reading it passed before.
    - **Cause:** the watch counted every sample, whether the list held a window of Designer's or not.
    - **Fix:** `_seen` says whether the list holds a window of the pid, and whether a popup of its is shown.
      `PopupWatch.listed` counts the first, and the check needs more than 100. `popups.py`'s docstring has the count
      measured.
    - **Also covered:** the other window checks read Designer's windows from inside Designer, not through this watch.

- [x] **TST-406 · The unit tests don't see the fade timer's interval or its looking again** · follows HLP-134, generation 2 · `tests/unit/test_view3d_helpers.py:222,289-302`, `mcp_server/designer_helpers/view3d.py:274-276,283-287` · confirmed · found 2026-11-14
  - **Defect.** The fake `Timer.start(after)` drops `after`.
    `test_the_menu_opened_is_made_transparent_before_its_action_is_picked` runs `timers[2]` before `timers[0]`
    itself, so the order its name claims is the test's, not the code's. No test
    runs `fade()` while no popup is open, so `timers[2].start(0)` is never reached.
  - **Scenario.** Every unit test passes with the fade started at 100 ms, with its restart dropped, or with it
    restarting after it made the menu transparent. Only the first is caught by the live check (about 155 ms on
    screen).
  - **Fix.** Have the fake record `after`, and assert `[100, MENU_GUARD, 0]`. Run `timers[2]` with no popup open (it
    is active again), then with the menu (opacity 0, not active again).
  - **Resolution: done.**
    - **Test:** `test_the_pick_the_guard_and_the_fade_start_at_their_times` and
      `test_the_fade_looks_again_until_the_menu_opens_then_stops`, with the fake timer recording each start's interval.
      They pass on the code, which was right. Each failed on a mutant of `_apply_outputs`: the fade started at 100 ms,
      its restart dropped, and its restart after it made the menu transparent.
    - **Fix:** the two tests.

- [x] **TST-407 · No test sees the window made opaque before it is brought on screen** · `tests/unit/test_shot3d.py:322-331`, `tests/test_all_tools/editor_panels_and_fit/checks.py:893-907`, `mcp_server/designer_helpers/shot3d.py:253-254` · confirmed · found 2026-11-14
  - **Defect.** `_on_screen` runs `screen.opaque_first()` before `screen._bring(again=False)`, so `_fade` records the
    window's look once it is opaque. Both tests of a window an earlier shot left transparent start with it on screen,
    where `_bring` does nothing: the unit test with `Mac()`'s defaults, the live `LEFT_TRANSPARENT` case after
    `clear()`.
  - **Scenario.** `opaque_first` moved after `_bring` passes every test. A minimized, covered or hidden window an
    earlier shot left transparent then has its transparent look recorded. It is made opaque in front for the shot, so
    the user sees it, and is put back transparent and click-through, so Designer looks gone.
  - **Fix.** Parametrize the unit test over minimized, covered and hidden with `looks[MAIN] = (0.0, True)`: `done`
    starts `['unfade', 'fade', ...]`, and the window ends `OPAQUE`.
  - **Resolution: done.**
    - **Test:** `test_a_window_an_earlier_shot_left_transparent_is_made_opaque_first`, parametrized over the window on
      screen, minimized, covered and hidden. It passes on the code, which was right, and failed with `opaque_first`
      moved after `_bring`: in 3 of the 4 cases, all but the window on screen.
    - **Fix:** the test.

- [x] **TST-408 · README gives the shot a duration no check measures** · follows HLP-133, generation 2 · `README.md:370-372` · confirmed · found 2026-11-14
  - **Defect.** README says "some may pause drawing them for the shot's second or so". The window stays in front from
    before the set-up to the last render. That is about 0.8 s before the first render (`_wait_on_screen`, then
    `DRAW_WAIT`), plus the set-up's waits (`graph=` about 1.25 s, a view `VIEW_TURN` and 0.3 s, a mesh 0.5 s), plus up
    to `RETAKES` × `DRAW_WAIT` for renders taken again.
  - **Scenario.** GUIDE.md's suggested `graph=`, `view='Top'`, `tiling=2` takes several seconds: a user told "a
    second or so" sees their apps pause for longer.
  - **Fix.** Make the claim smaller: drop the duration ("may pause drawing them during the shot").
  - **Resolution: done.**
    - **Test:** none: the claim is removed.
    - **Fix:** README says "some may pause drawing them during the shot", with no duration.
    - **Also covered:** the next sentence, changed for HLP-136, says the window stays up if Designer is still the app
      in front when the shot ends, which `test_designer_made_the_active_app_then_left_during_the_shot_is_put_back`
      checks.

- [x] **HLP-137 · Vague types in the functions the diff adds or changes in `view3d.py`** · `mcp_server/designer_helpers/view3d.py:194,249,280` · confirmed · found 2026-11-14
  - **Defect.** `_MenuPick.fade(self, menu: Any)` is new, and its `Any` is unmarked. `_apply_outputs(tree: Any,
    graph: Any, keep: list[Any])`, which the diff changes, holds `timers: list[Any] = []`.
  - **Scenario.** mypy checks nothing through them: a wrong call on the graph or a timer goes unseen (AGENTS.md,
    Typing).
  - **Fix.** `graph: SDSBSCompGraph` (already imported; the caller's `g` comes from `_set_up_checked`),
    `keep: list[object]` (the caller's), `timers: list[QtCore.QTimer]` (a local annotation, not evaluated at runtime).
    `tree` and `menu` stay `Any`, marked `# Any: a Qt widget (screenshots.py)`.
  - **Resolution: done.**
    - **Test:** no behaviour changes. The tests of `_apply_outputs` and `_MenuPick` in `test_view3d_helpers.py` pass
      before and after, and so does mypy strict.
    - **Fix:** `graph: SDSBSCompGraph`, `keep: list[object]`, `timers: list[QtCore.QTimer]`. `tree` and `menu` stay
      `Any`, marked `# Any: a Qt widget (screenshots.py)`.
    - **Also covered:** `sys`, which `fade` now uses, moved into `core.py`'s shared imports, as two parts may not both
      import it (`test_designer_helpers.py`); `mac_window.py` takes it from there, its tests passing before and after.

- [x] **HLP-138 · A user already in Designer as the shot began, who leaves and comes back, still sees no window** · follows HLP-136, generation 2 · `mcp_server/designer_helpers/shot3d.py:123,164-166,171,193` · confirmed · found 2026-11-14
  - **Defect.** `self._was_active = mac is not None and mac.active()` is read once, and `_taken_up()` is
    `self._mac.active() and not self._was_active`. With Designer the active app as the shot began, `between()` never
    makes the windows opaque, `_bring` goes on making them transparent, and `put_back` never leaves the window up.
  - **Scenario.** The user is in Designer as an agent's shot starts. They switch to a terminal that covers Designer's
    window, so the next render brings it in front, transparent. They switch back to Designer: they see the terminal
    through the invisible window, their clicks go to the terminal, and their keys to that invisible window. Then
    `put_back` puts it behind the terminal. README says "If you switch to Designer during the shot, it becomes
    visible". `test_a_designer_already_the_active_app_before_the_shot_stays_transparent_during_it` covers only a user
    who never left.
  - **Fix.** Forget `_was_active` once Designer is seen not to be the active app: in `between()`, which `again()` runs
    before each `_bring`, so every bring during the shot comes after that look. A unit test: `Mac(covered=True,
    active=True)`, the user away (`is_active = False`), the window covered again and `again()`, then back
    (`is_active = True`) and `between()`: made opaque, and left up.
  - **Resolution: done.**
    - **Test:** `test_a_user_in_designer_as_the_shot_began_who_left_and_came_back_sees_its_window_at_once` failed
      before the fix (the window still transparent once the user was back in Designer) and passes after. The live
      path, the windows made opaque and the window left up, is HLP-136's check, which passes.
    - **Cause:** `_was_active` was read once, as the shot began, so a user who left Designer and came back never
      counted as having made it the active app.
    - **Fix:** `between()` forgets `_was_active` once Designer is seen not to be the active app; `again()` runs it
      before each bring.
    - **Also covered:** `put_back`'s active check reads the same `_was_active`, so the window is left up too.
  - Questioned by HLP-142 (2026-11-14).

- [x] **HLP-139 · A window covered by several windows can come back in front of one of them, now that clicks go through it** · `mcp_server/designer_helpers/shot3d.py:195-200,246-248`, `mcp_server/designer_helpers/mac_window.py:129-133` · confirmed · found 2026-11-14
  - **Defect.** `_bring` keeps only the nearest window in front of Designer's (`found = mac.above()`, `found[-1]` in
    `above()`), and `put_back` puts it right behind that one (`mac.put_below(self._behind)`). That restores the window
    covered only while that window is still the lowest of those that covered it. During the shot the user's clicks go
    through Designer's window to theirs, so they can reorder them.
  - **Scenario.** Windows A, in front, and B together cover Designer's window D: `_behind` is B. The shot orders them
    D, A, B, with D transparent and click-through. The user clicks B through D, as README says they can: B, D, A.
    `put_back` puts D right behind B, so B, D, A, and makes it opaque: D shows over A wherever B doesn't cover it,
    and the tool says "put back behind the window that was in front of it". B closed during the shot, its close button
    reached through D, leaves D "left in front" (HLP-130), opaque over A, which still covers its place. On `main` a
    click inside D's area reached D, which made Designer the active app and left it up.
  - **Fix.** At the first bring, record every normal window above D (`_listed(CG_ABOVE, number)`, layer 0). At the
    put-back, put D right behind the one of them still on screen that is lowest in the current order. Measure first,
    in a Designer an agent started, with two windows of Designer's own covering it together.
  - **Resolution: done.**
    - **Measured first:** two windows of Designer's own, overlapping, each over a half of its main window, don't make
      it covered for macOS: the view draws, and the shot doesn't bring it in front. So the scenario as written doesn't
      arise. The defect does whenever the window directly in front of Designer's isn't the one covering it.
    - **Test:** the live put-back check's new case (`window_states.TWO`): a window covering Designer's whole, and a
      smaller window of Designer's own in front of it, under the cover, raised during the shot. In its scratch run it
      failed before the fix (`later,main,cover,below`: back in front of its cover, said "put back behind the window
      that was in front of it") and passed after (`later,cover,main,below`). Unit tests failing before:
      `test_a_covered_window_goes_back_behind_its_cover_once_the_user_raised_the_window_in_front_of_it` and
      `test_a_covered_window_goes_back_behind_its_cover_once_the_window_in_front_of_it_closed`.
    - **Cause:** the put-back kept only the window directly in front of Designer's (`above()`), which needn't be the
      one covering it, and which the user can raise during the shot.
    - **Fix:** `_bring` records every normal window in front of Designer's each time it brings it
      (`_MacWindow.in_front`), and `put_back` puts it right behind the one of them still on screen nearest the back
      (`_MacWindow.lowest`). `above()` is gone.
    - **Also covered:** HLP-126's, HLP-130's and HLP-131's cases, unit and live, pass unchanged: one cover, a cover
      closed or minimized, a later window over it, an always-on-top cover. The lines are unchanged, as the window is
      still put right behind a window that was in front of it.
  - Questioned by HLP-143 and TST-415 (2026-11-14).

- [x] **HLP-140 · The tool's docstring and two comments say more than the code does** · follows HLP-136, generation 2 · `mcp_server/server_tools/views.py:75`, `mcp_server/designer_helpers/view3d.py:206`, `mcp_server/designer_helpers/shot3d.py:193` · confirmed · found 2026-11-14
  - **Defect.**
    - `views.py`: "(left up if the user switched to Designer meanwhile)". The code leaves it up only if Designer is
      the active app as the shot ends: a user who switched there and back finds it put back
      (`test_designer_made_the_active_app_then_left_during_the_shot_is_put_back`). README says this exactly; the
      docstring, which agents read and pass on, doesn't.
    - `view3d.py`: `# measured there only: a click at its place reaches the window under it`. What was measured for
      the menu is that the flag sets its `ignoresMouseEvents`, and that the pick still works. That a click goes
      through was measured for Designer's main window only; `windowNumberAtPoint` never reported the menu.
    - `shot3d.py`: `# the user, in Designer, sees it put back`: the line brings the window on screen, and "put back"
      reads as `put_back`.
  - **Scenario.** An agent tells the user their window stays up once they switch to Designer; a maintainer takes the
    menu's click-through for measured.
  - **Fix.** Make each claim smaller: "(left up if Designer is the app in front as the shot ends)"; "measured there
    only: the flag sets the menu's ignoresMouseEvents, and its action is still picked"; "sees it brought back".
  - **Resolution: done.**
    - **Test:** none: the claims are made smaller.
    - **Fix:** `views.py` says "(left up if Designer is the app in front as the shot ends)"; `view3d.py`'s comment, "it
      sets the menu window's ignoresMouseEvents, and the action is still picked"; `shot3d.py`'s, "sees it brought
      back".
    - **Also covered:** DECISIONS.md's sentence on the active app reworded to what the code does, the user's choice
      ("Reword to match (Recommended)", 2026-11-14).
  - Questioned by HLP-142 (2026-11-14).

- [x] **TST-409 · HLP-136's live check can't tell `between` before a set-up step from `between` before a render, and no test sees its guard** · follows HLP-136, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py:971-1013`, `tests/test_all_tools/editor_panels_and_fit/window_states.py:227-242`, `tests/unit/test_shot3d.py:519-536`, `mcp_server/designer_helpers/shot3d.py:171` · confirmed · found 2026-11-14
  - **Defect.**
    - The live check reads the window's look only at each render. With `between` dropped from the set-up's steps, the
      `between()` that `again()` runs before the next render does the same work: the RENDER lines, the line said and
      the state after are the same, and the check passes. The unit tests guard each half.
    - `between()`'s `if self._faded and ...` has no test: dropped, the second `again()` in
      `test_a_window_put_on_screen_again_while_the_user_is_in_designer_isnt_made_transparent` says "made opaque at
      once" again, but the test compares only the last two lines.
  - **Scenario.** A regression repeats "made opaque at once" before every later step and render, or says it for a
    window that was never transparent: agents would tell the user their window was invisible. The live check doesn't
    see the steps' half go.
  - **Fix.** In the live check, require the line before the first step's line
    (`t.index(MADE_OPAQUE) < t.index('3D view, setting: ')`); in the unit test, compare every line; a unit test with
    the window on screen, Designer made the active app, then `again()`: nothing said.
  - **Resolution: done.**
    - **Test:** the live check now needs "made opaque at once" before the first set-up step's line. In its scratch run
      it failed with `shoot_3d` giving the set-up None (the steps' look gone) and passes on the code.
      `test_a_window_put_on_screen_again_while_the_user_is_in_designer_isnt_made_transparent` compares every line, and
      `test_nothing_is_said_when_designer_becomes_the_active_app_with_no_window_made_transparent` is new: both failed
      with `between()`'s `self._faded` guard dropped, and pass on the code.
    - **Fix:** the checks.

- [x] **TST-410 · The transparency check fails if Designer becomes the active app during one of its shots, which the tool now acts on** · follows HLP-136, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py:907-965` · confirmed · found 2026-11-14
  - **Defect.** The check expects every render transparent (`looks == [during]`, `fadings == faded`) in four shots,
    with no guard for Designer becoming the active app. TST-399 saw that happen during a shot in a final run (another
    Designer of the pool handing activation over as it quits, or a click), and the during-pan checks skip judging
    then (`window_states.became_active`). Since HLP-136, that makes the window opaque at the next step or render.
  - **Scenario.** In the final check, a Designer of the pool quits during one of the four shots and hands activation
    to this one: the renders after it are opaque, and the check fails though the tool did what it should.
  - **Fix.** When the shot says "made opaque at once" or "left on screen, as Designer became the active app", judge
    only the renders before it, or say "not judged" as the during-pan checks do (TST-399).
  - **Resolution: done.**
    - **Test:** the transparency check, run with each shot making Designer the active app as its set-up starts (a
      scratch-only `window_states.rendered = window_states.switched`). It failed before the change in the three cases
      off screen, the renders after the switch opaque, and passes after, saying the renders weren't judged. Without the
      switch it judges every render, and passes.
    - **Fix:** when the shot says "made opaque at once" or "left on screen, as Designer became the active app", the
      renders aren't judged (`NOT_JUDGED`, as for TST-399); the windows opaque and clickable after the shot still are.
  - Questioned by TST-414 (2026-11-14).

- [x] **TST-411 · The hidden case counts Designer's windows through the same `windows(True)` the shot uses** · follows TST-403, generation 2 · `tests/test_all_tools/editor_panels_and_fit/window_states.py:45`, `tests/test_all_tools/editor_panels_and_fit/checks.py:940-948` · confirmed · found 2026-11-14
  - **Defect.** `state()` counts `windows=` and `faded=` with `every = mac.windows(True)`, the function the shot fades
    through. TST-403's scenario names `windows(every=True)` misreading NSApp's array; the check can't see that.
  - **Scenario.** A `windows(True)` that drops windows (only the main window, or `range(count - 1)`) passes the hidden
    case, which expects every window faded: `(1, 1)` or `(7, 7)`. The window dropped shows at full opacity when
    Designer is shown for the shot.
  - **Fix.** Count NSApp's windows in the snippet with its own `objectAtIndex:` loop, as `order()` does for
    `orderedWindows`.
  - **Resolution: done.**
    - **Test:** the transparency check, run with the shot's `_MacWindow.windows(True)` leaving out one of Designer's
      windows other than the main one (a scratch-only rebinding). Its hidden case passed before the change (`(8, 8)`)
      and fails after (`(5, 6)`); it passes on the code.
    - **Fix:** `state()` reads NSApp's windows itself (`listed('windows')`, which `order()` now shares), not through
      `_MacWindow.windows`.

- [x] **TST-412 · The covered-under fact has no reading of the window under it uncovered** · follows HLP-133, generation 2 · `tests/test_all_tools/editor_panels_and_fit/window_states.py:159-174`, `tests/test_all_tools/editor_panels_and_fit/checks.py:731-755` · confirmed · found 2026-11-14
  - **Defect.** `_UNDER` reads the window under Designer's as covered twice, the main window opaque then transparent,
    and the check expects `opaque=True transparent=True`. A window that never reached the screen, or was ordered out,
    reads covered too.
  - **Scenario.** The fact passes when `below` isn't on screen at all, so it no longer measures what the module
    docstring and DECISIONS.md say it does.
  - **Fix.** Bring `below` in front first and read it uncovered (`covered=False`), then the two readings.
  - **Resolution: done.**
    - **Test:** the fact check, run with the window under Designer's hidden as it was made (scratch only), passed
      before the change. It now reads that window alone in front first (`alone=False`), and fails when the main window
      is brought in front before that reading (`alone=True`, scratch only).
    - **Fix:** `_UNDER` brings the window under in front and reads it first.
    - **Also covered:** the control showed HLP-133's fact wrong (HLP-141).

- [x] **TST-413 · Vague types in the test functions the diff adds or changes** · `tests/unit/test_view3d_helpers.py:229,233`, `tests/unit/test_shot3d.py:642` · confirmed · found 2026-11-14
  - **Defect.** `Timer.__init__`, which gains `self.starts`, holds `parent: Any = None` and `self.run: Any = None`,
    unmarked. `Shot`'s `set_up` returns `Callable[..., None]`.
  - **Scenario.** mypy checks nothing through them (AGENTS.md, Typing).
  - **Fix.** `parent: object = None` (only stored and compared), `self.run: Callable[[], object] = lambda: None`, and
    `Callable[[object], None]` for `set_up`'s result.
  - **Resolution: done.**
    - **Test:** no behaviour changes: the two files' tests pass before and after, and so does mypy strict.
    - **Fix:** `parent: object = None`, `self.run: Callable[[], object] = lambda: None`, and `Callable[[object], None]`.

- [x] **HLP-141 · HLP-133's fact was wrong: a window under Designer's transparent window stays visible for macOS** · follows HLP-133, generation 2 · `mcp_server/designer_helpers/shot3d.py:15-21`, `README.md:368-372`, `DECISIONS.md`, `tests/test_all_tools/editor_panels_and_fit/checks.py:731-757` · measured · found 2026-11-14
  - **Defect.** HLP-133's probe and fact check made the window under Designer's and never showed it on its own: it
    read covered with Designer's window opaque, and still covered with it transparent. README said "macOS still tells
    the apps with windows under it that those windows are covered, so some may pause drawing them during the shot",
    and DECISIONS.md recorded the user's "Document it" on that basis.
  - **Scenario.** Found addressing TST-412. With the window under shown alone first, it read visible alone, covered
    under Designer's opaque window, and visible under it transparent, 3 times of 3. In the shot's own order
    (transparent, then in front) it read visible at 0.1, 0.5, 1 and 2 s, and covered once opaque, 3 of 3. Read the
    old way, it was covered both times, 3 of 3. The user was told apps may pause for no reason.
  - **Fix.** Say the measured fact, and drop README's sentence: the user's choice ("Remove the sentence
    (Recommended)", 2026-11-14).
  - **Resolution: done.**
    - **Test:** `check_a_window_under_designers_transparent_window_counts_as_visible`, renamed from
      `check_a_window_under_designers_transparent_window_still_counts_as_covered`, expects
      `alone=False opaque=True transparent=False`. It passes in its scratch run, and fails with the main window brought
      in front before the alone reading.
    - **Cause:** a window macOS had never shown read covered, whatever was over it.
    - **Fix:** README's sentence removed. `shot3d.py`'s docstring says the measured fact, without the `setOpaque:`
      sentence, measured the same flawed way. DECISIONS.md's entry says the first measurement was wrong and records the
      user's choice, and its Reopen if names an app seen pausing under the window.
    - **Also covered:** HLP-133's and TST-408's resolutions describe the old sentence; they stay as the history of
      those findings.
  - Questioned by HLP-142 (2026-11-14).
  - Note (2026-11-14): its check failed in the branch's final check, read with a window of another app in
    front: TST-417.

- [x] **HLP-142 · Four sentences on the shot say more than its code and tests do** · follows HLP-138, HLP-140 and HLP-141, generation 3 · `mcp_server/server_tools/views.py:75`, `mcp_server/designer_helpers/shot3d.py:6-9,118-120,167` · confirmed · found 2026-11-14
  - **Defect.**
    - `views.py`: "(left up if Designer is the app in front as the shot ends)". `put_back` leaves the window up only
      if Designer is the active app and wasn't as the shot began (`if mac.active() and not self._was_active`). A
      Designer already the active app as the shot began, and still at its end, has its window put back
      (`test_a_window_covered_while_designer_was_already_the_active_app_is_put_back`). README's sentence, which
      starts "If you switch to Designer during the shot", is right.
    - `_taken_up`'s docstring: "it is, and wasn't as the shot began". Since HLP-138, `between()` clears
      `_was_active` once it sees Designer not active. So `_taken_up()` is also True for a Designer active as the shot
      began that the user left and came back to.
    - The class docstring: "A Designer the active app as the shot began that the user leaves counts as made the
      active app if they come back". `between()` sees the user leave only at its looks, before each set-up step and
      render. A user who leaves and comes back between two looks counts as never having left: the window stays
      transparent and is put back as found, as for a user who never left (DECISIONS.md, the 3D screenshot's window).
    - The module docstring: the self-test "re-measures ... the second [point], but for its time and the identical
      render". That point now includes "A window made under it and never shown read covered either way", which
      `_UNDER` doesn't read: it shows the window alone first. That reading was a scratch-only control (HLP-141).
  - **Scenario.** An agent tells the user their window stays up because Designer is in front as the shot ends,
    though the user never switched. A maintainer reads `_taken_up` as True only for a Designer inactive as the shot
    began, or takes the never-shown reading for guarded.
  - **Fix.** Make each claim smaller (generation 3):
    - `views.py`: "(left up if the user switched to Designer during the shot and it is still the app in front as it
      ends)";
    - `_taken_up`: "it is, and wasn't as the shot began or at a look since (between)";
    - the class docstring: "that the user is seen to have left, at a look before a step or render, counts as made
      the active app once they come back";
    - the module docstring: "but for its time, the identical render and the window never shown".
  - **Resolution: done.**
    - **Test:** none: the claims are made smaller (generation 3).
    - **Fix:**
      - `views.py`: "then puts it back as it was, and says so. It is left up if the user switched to Designer during
        the shot and Designer is still the app in front as it ends";
      - `_taken_up`: "it is, and wasn't as the shot began or at a look since (between)";
      - the class docstring: "A Designer the active app as the shot began counts as made the active app once the user
        comes back to it, if a look before a step or render saw them gone";
      - the module docstring: "but for its time, the identical render and the window never shown".

- [x] **HLP-143 · `mac_window.py`'s docstring names `on_screen` as the guard the put-back no longer uses** · follows HLP-139, generation 2 · `mcp_server/designer_helpers/mac_window.py:9-12` · confirmed · found 2026-11-14
  - **Defect.** "...it puts it behind every window, as orderBack: does: so the shot asks first (on_screen)." Since
    HLP-139, `put_back` no longer asks `on_screen` about the window it puts Designer's behind: `lowest()` keeps only
    the windows CoreGraphics lists on screen. `on_screen` is now used only by `_wait_off_screen`.
  - **Scenario.** A maintainer changing `lowest` doesn't know it keeps Designer's window from going behind every
    window. One changing `on_screen` thinks they touch that guard.
  - **Fix.** "(lowest)" for "(on_screen)".
  - **Resolution: done.**
    - **Test:** none: a name in a docstring.
    - **Fix:** "(lowest)" for "(on_screen)".

- [x] **TST-414 · The transparency check's not-judged path gives a reason that can be wrong, and cuts off what it still judges** · follows TST-410, generation 3 · `tests/test_all_tools/editor_panels_and_fit/checks.py:913-918,952-981,1079` · confirmed · found 2026-11-14
  - **Defect.**
    - The docstring says the window is transparent and click-through while rendered. It doesn't say the renders go
      unjudged once the shot says Designer became the active app.
    - The detail's prefix is `NOT_JUDGED`: "Designer became the active app during the shot, which leaves its window
      up". With only "made opaque at once" said and the user gone again, the window is put back
      (`test_designer_made_the_active_app_then_left_during_the_shot_is_put_back`).
    - The prefix takes 116 characters of the 150 the detail is cut at (TST-334). So the state after the shot, the
      one thing still judged, is cut off, and the `if not ok` block prints the shot's lines, not that state.
  - **Scenario.** In the final check, the pool hands activation to this Designer during a shot, and the window is
    left transparent after it. The FAIL line doesn't say why, and nothing printed below it does.
  - **Fix.** Make the claims smaller (generation 3): the docstring's "Not judged when the shot says Designer became
    the active app (REVIEW.md TST-410)"; a short prefix of its own, without "which leaves its window up"; the state
    after the shot first in the detail.
  - **Resolution: done.**
    - **Test:** none new (generation 3). In its scratch run, with Designer made the active app as each shot's set-up
      starts (scratch only: `window_states.rendered = window_states.switched`), the check passes, its detail starting
      "after: opacity=1 through=False faded=0; renders not judged, as Designer became the active app". It passes on
      the code in the category's scratch run.
    - **Fix:** the docstring says the renders aren't judged once the shot says Designer became the active app, and
      that the state after the shot still is. The detail starts with that state, then a reason of its own, instead of
      `NOT_JUDGED`, which the other checks keep.
  - Questioned by TST-416 (2026-11-14).

- [x] **TST-415 · HLP-139's live case passes on the old put-back if its raise does nothing** · follows HLP-139, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py:1150-1157`, `tests/test_all_tools/editor_panels_and_fit/window_states.py:95-102,270` · confirmed · found 2026-11-14
  - **Defect.** `TWO` leaves `cover,later,main,below`. Without the raise, the put-back before HLP-139 put the window
    behind `later`, the window directly in front of it, which gives that same order. That order satisfies the case's
    three pairs, `(cover, main)`, `(later, main)` and `(main, below)`, and the put-back says BEHIND. Nothing reads
    that the raise happened: not the order, nor the event's line.
  - **Scenario.** A later change makes the raise do nothing: the case passes on the old code too, so it no longer
    guards HLP-139. Its scratch run failed before the fix only because the raise worked then.
  - **Fix.** Add `('later', 'cover')` to the pairs: only the raise puts `later` in front of `cover`. The fix gives
    `later,cover,main,below`, which passes. The `'covered again during the shot'` case, on `main`, has the same
    pattern: its pairs hold if `later` never covered.
  - **Resolution: done.**
    - **Measured first:** a cover closed (Qt's `close()`) or minimized (`miniaturize:`) is still listed in NSApp's
      orderedWindows, at the back, so the order after the shot can't show it. CoreGraphics lists neither on screen.
      The probe read `order=main,below,cover` and `cg_on_screen=False` for both, and with nothing done
      `cover,main,below` and True.
    - **Test:** in its scratch run, with every event of the put-back check made a no-op (scratch only), the check
      passed all five cases before the change. After it, the four cases with an event fail ("later not seen to
      happen", and the same for close, minimize and raise), and the always-on-top case, with none, passes. On the
      code every case passes, in the category's scratch run (74 of 74). Unit tests:
      `test_an_event_during_a_shot_is_seen_to_have_happened_only_by_its_effect` and
      `test_every_event_has_a_way_to_be_seen`, failing before `event_seen` existed.
    - **Cause:** the check read only where the window was put back, never that the event it set up had happened. With
      no event, the old put-back left the same order.
    - **Fix:** `window_states.SEEN_BY` says how each event is seen to have happened, and the put-back check requires
      it (`event_seen`), saying "<event> not seen to happen" when it isn't:
      - a window brought over Designer's: the shot's "brought in front again" line (`AGAIN`, moved from checks.py);
      - TWO's raise: `later` in front of `cover` after the shot, as the entry suggested;
      - the cover closed or minimized: off screen for CoreGraphics, read in the state line (`cover_on_screen`).
    - **Also covered:** the three cases on `main` with the same gap ('covered again during the shot', 'its cover
      closed', 'its cover minimized'), with the user's go-ahead. The HLP-124 check, the other user of `during_pan`'s
      events, already required the "brought in front again" line. `test_every_event_has_a_way_to_be_seen` fails for
      a new event with no way to be seen.
  - Questioned by TST-416 (2026-11-14).

- [x] **HLP-144 · `_Screen`'s docstring says the Explorer's menu is made click-through, which happens on macOS only** · follows HLP-134, generation 2 · `mcp_server/designer_helpers/shot3d.py:99-100` · confirmed · found 2026-11-14
  - **Defect.** "The Explorer's menu, which graph= opens, is made transparent and click-through as it opens
    (view3d.py)." `_MenuPick.fade` makes it click-through only `if sys.platform == 'darwin'`. Elsewhere the menu is
    only transparent, and still takes clicks. DECISIONS.md, view3d.py's module docstring and `fade` say "on macOS
    click-through".
  - **Scenario.** A maintainer working on Windows reads `_Screen` and expects a click at the menu's place during a
    shot to reach the window under it.
  - **Fix.** "is made transparent as it opens, and on macOS click-through too (view3d.py)".
  - **Resolution: done.**
    - **Test:** none: the claim is made smaller.
    - **Fix:** "is made transparent as it opens, and on macOS click-through too (view3d.py)".

- [x] **TST-416 · Two checks miss the "brought in front again" line once Designer is the active app at that look, and two sentences say its windows stay opaque from then on** · follows TST-414 and TST-415, generation 3 · `tests/test_all_tools/editor_panels_and_fit/window_states.py:277-285`, `tests/test_all_tools/editor_panels_and_fit/checks.py:918,952,1121` · confirmed · found 2026-11-14
  - **Defect.**
    - `AGAIN` is the line with ", transparent". Since HLP-136, `_bring` drops those words when Designer is the
      active app at that look: `BROUGHT[way][again] if fade else BROUGHT[way][again].replace(', transparent', '')`.
      `SEEN_BY['cover']` and `SEEN_BY['later']`, and the HLP-124 check (`window_states.AGAIN in t`), need the
      transparent wording.
    - The transparency check's docstring and the comment above `switched` say that Designer becoming the active app
      "makes its windows opaque from then on". A user who switches to Designer and away again, the window covered
      again, has it made transparent again (`_bring`'s `fade = not self._taken_up()`).
  - **Scenario.** In the final check, another Designer of the pool quits during a shot and hands activation to this
    one, and a Designer launching takes it back before the put-back. The look before the render says "brought in
    front again, as another window covered it during the shot", without ", transparent". Nothing says "left on
    screen", and Designer isn't the active app after the shot, so both checks judge the shot, and both fail: "later
    not seen to happen" in the put-back check, and `AGAIN in t` in the HLP-124 check. The tool did what it should.
    How often activation comes and goes within one shot wasn't measured; TST-399 saw it come.
  - **Fix.** Make the claims smaller (generation 3): `AGAIN` becomes the start both wordings share, "Designer's
    window: brought in front again", which no other line starts with; drop "from then on" from the two sentences.
  - **Resolution: done.**
    - **Test:** two cases of `test_an_event_during_a_shot_is_seen_to_have_happened_only_by_its_effect`, the line
      without ", transparent" for the `cover` and `later` events, failed before the change and pass after. In a
      scratch run, `_MacWindow.active` read True from the event during the pan on, and False again just before the
      put-back (scratch only, rebound in the shot's snippet). The shot made the windows opaque at once and said "brought
      in front again, as another window covered it during the shot". The HLP-124 check and the put-back check's
      'covered again during the shot' case both failed before the change ("later not seen to happen"), the window put
      back behind its cover. Both pass after, in that run and with the events as they are.
    - **Cause:** `AGAIN` held the whole line with ", transparent", which `_bring` leaves out once Designer is the active
      app at that look (HLP-136).
    - **Fix:** `AGAIN` is "Designer's window: brought in front again", the start both wordings share; no other line the
      shot says starts that way. "From then on" is dropped from the transparency check's docstring and the comment
      above `switched`.
    - **Also covered:** `AGAIN`'s other users: `SEEN_BY['cover']` and `SEEN_BY['later']`, and the HLP-124 check, all
      through the one constant.
