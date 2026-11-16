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

**Last used:** PLG-43, SRV-171, HLP-181, INS-39, TST-479.

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
| Medium-high | 0 | 1 |
| Medium | 0 | 7 |
| Low-medium | 0 | 53 |
| Low | 0 | 175 |
| **Total** | **0** | **236** |

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

### 2026-11-15: three full runs of both suites on main, after the invisible-3d-shot merge

- **How:** at the user's request, both suites in full three times in a row (`tests/test_all_tools`): 23 categories,
  four Designers at once, the unit suite beside them. No review: the failures were read from the runs' logs and the
  code.
- **Results:**
  - Runs 1 and 2 passed: 736 of 736 live checks, 1653 unit tests.
  - Run 3 passed 732 of 734 live checks and 1653 unit tests. Both failures were in `editor_panels_and_fit`: the Light
    tool check (HLP-147) and the click fact (TST-419). The Light tool check records one check instead of three when
    a shot fails, hence 734.
  - Every run: no crash dump, the user's preferences as before the run, no Designer left running. The runs took 543,
    558 and 533 s.
- **Not verified:** what closed the Explorer's menu (HLP-147), and which window the click fact's click-through
  reading reached (TST-419). Each happened in one run of three, and the log doesn't say. What would check them:
  HLP-147's measurement, and TST-419's reading naming the window in the next full run.
- **Findings:** 2: Low-medium HLP-147, TST-419.
- **Suggested order:** HLP-147 (the tool's code), then TST-419.
- **Later the same day:** the user reported Designer coming in front of their windows during the runs, taking their
  keyboard. Measured and resolved: SRV-149 (Medium), the launches. Then, at the user's request, the window checks
  were reworked so Designer stays off the user's screen but where a check needs it in front:
  - every Designer the run starts is hidden once it answers (all 555 checks of the other categories passed in a
    hidden Designer);
  - the window checks set up their ways behind every window, watched for a window of Designer's in front meanwhile;
  - the few that need a window in front of the user's run together, after them, in every full run;
  - the material check's dialog unhid Designer, which then stayed over the user's other windows for about 10 s: its
    windows and the dialog are now transparent meanwhile, then Designer is hidden again (measured: none of its
    windows on screen during the check).
- **Then:** TST-420 (Low-medium), the window checks' fixed waits, at the user's request. Then HLP-148 (Low-medium),
  at the user's request: the 3D shot's own fixed waits, most of a shot's time, measured step by step in a Designer an
  agent started.
  HLP-148 resolved the same day. The fixed waits left outside the shot became SRV-150 and TST-421, under the rule the
  user added to AGENTS.md.
- **Then,** at the user's request, the four open findings addressed: HLP-147, TST-419, SRV-150 and TST-421, measured
  first in a Designer an agent started. Found along the way: HLP-149 (Low-medium, resolved), the shot's moves off
  screen; SRV-151 (Low-medium, open), the fixed waits no callback found yet replaces; SRV-152 (Medium, open), a
  launch's window in front of the active app's, which fails lifecycle's check.

---

### 2026-11-15: the full-run-failures branch against main (the diff only)

- **Scope:** the branch's uncommitted diff against main: HLP-147, HLP-148, HLP-149, SRV-150, TST-419, TST-420 and
  TST-421's fixes, the front watch, and the window checks reworked to stay off the user's screen.
- **How:** four reviewers read the diff: the helpers, the server, the window checks, and the self-test's
  infrastructure with the docs. No tests were run. The lead agent settled each suspicion by reading. Where reading
  couldn't, it used three probes, one at a time, in a hidden Designer an agent started (port 9877):
  - wheel notches past the camera's limit;
  - the overlay's labels after a mesh switch;
  - a front watch around the material check.
  It also ran mypy with `--platform win32`.
- **Resolutions assessed:** HLP-147, HLP-148, HLP-149, SRV-150, TST-419, TST-420 and TST-421, whose fixes are in this
  diff. Their causes and fixes hold. Questioned, as follow-ups:
  - HLP-148: HLP-150, HLP-151, HLP-152, TST-430;
  - HLP-147: HLP-153;
  - HLP-149: HLP-154, TST-423;
  - SRV-150: SRV-153, SRV-154, TST-424, TST-426;
  - TST-421: TST-425, TST-426, TST-427.
  TST-422's check lost its guard to the rework, which has no finding of its own.
- **Findings:** 19.
  - Medium: TST-422.
  - Low-medium: HLP-150, HLP-151, SRV-153, TST-423, TST-424, TST-425.
  - Low: SRV-154, TST-426, TST-427, HLP-152, HLP-153, HLP-154, HLP-155, TST-428, HLP-156, TST-429, TST-430, TST-431.
- **Dropped:**
  - A zombie Designer making `_exited` wait its whole limit. Measured: kqueue reports a zombie's exit at once.
  - lifecycle's changes never seen passing. It ran whole in a scratch run, 53 of 54, the failure SRV-152 (noted under
    TST-421).
  - Wheel notches past the camera's limit each waiting NO_RESTART. Measured off screen: 90 notches past 30, each
    taken in about 0.03 s, one in 30 at the full 1 s.
  - The overlay's labels going stale after a mesh switch. Measured: the four labels held were still valid, and the
    same objects, after Scene's mesh changed.
  - The material check's dialog taking the user's keyboard. Measured: a front watch around it saw Designer active in
    0 of 154 samples.
  - "every category's checks passed in a Designer hidden so" (`common.py`, two unit tests). The log of 2026-11-15
    records all 555 checks of the other categories passing in a hidden Designer.
  - bridge's `wait_for` polling every 0.05 s: it is on main, not in this diff.
- **Not verified:** each needs Designer drawing, or a window of another app's, on the user's screen, which takes
  their go:
  - whether an unload in a Designer on screen also finishes its teardown before the next call;
  - whether `to_back()` waits its whole limit when a window of the user's covers all of Designer's frame (its
    `shown_again` waits for exposure);
    Note (2026-11-16): measured with the user's go: it doesn't (the fourth review's log).
  - whether `_PUT`'s 'minimized' way, made opaque as macOS's minimize animation runs, flies to the Dock opaque;
  - whether a GPU Pathtracer view brought back on screen with nothing changed waits SETTLE_LIMIT (3 s) each time.
- **Not included:** SRV-151's note already leaves the plugin's WAKE_DELAY_MS to the user. AGENTS.md's wait rule
  contradicts the DECISIONS.md entry on it, and the user decides which stands.
- **Suggested order:**
  1. TST-422, the check guarding the put-back behind the user's window;
  2. HLP-150, the tool's code;
  3. SRV-153, which fails the unit suite on Windows;
  4. TST-423, TST-425, TST-424;
  5. HLP-151, with a callback for an accumulation that ends lower;
  6. the Low ones, HLP-153 first.
  SRV-152 (Medium, open) fails lifecycle's launch check, and its measurement shows Designer on the user's screen.
- **Checked and found fine:**
  - no `_until` runs inside another's slot, and the renders are taken between polls;
  - the timers are owned by a QObject the frame holds, in `_until` and `_menu_once`;
  - `frames.close()` runs in each path's `finally`;
  - the parts' order, and no name defined twice;
  - the placeholder replaces of `during_pan`, `hidden_mid_zoom`, `closed_early`, `_DRAG` and `read`;
  - `EVENT_DONE` and `until`'s states run no event loop;
  - `stayed_behind`, `in_front_of_another` and `PUT_BACK_IN_FRONT` against their unit tests;
  - `with_checker`'s retakes;
  - `_HITS`' window in the way;
  - the kqueue exit watch on a child (unit tests).
- **Chains:** every follow-up is generation 2. The longest still growing is HLP-148's, at generation 2.
- **Then,** at the user's request, the 19 findings addressed in the suggested order, test first, with Designer on
  the user's screen for TST-422's check and HLP-151's measurement (their go). 18 done; TST-431 not a bug (its change
  failed three window checks), and SRV-154 not a bug for a launch's own start. Found along the way, both resolved:
  TST-432 (Medium-high), `HIDE` never hiding a Designer, which left the probe's Designer on the user's screen for
  about 20 s; SRV-155 (Low-medium), the same handle in `launch_designer`'s give-back. Not run live: lifecycle (its
  launches come up in front of the user's window, SRV-152) and the launch paths.
- **Then,** at the user's request, the two left open (SRV-152, SRV-151) and the hunt for WAKE_DELAY_MS's callback,
  with their go for Designer launches in front of their windows, one crash and Designer shown for HLP-151's case.
  Both resolved. WAKE_DELAY_MS: with the wait at 0, `measure`'s one-compute check passed in 5 of 5 Designers opened
  hidden; on 2026-11-11 it failed 4 runs of 5 in Designers started from their binary, shown. So what Designer needs
  the moment for wasn't found: reproducing the failure takes a Designer shown on the user's screen. The 30 ms stays,
  as DECISIONS.md has it.

---

### 2026-11-15: the full-run-failures branch against main, second review (the diff only)

- **Scope:** the branch's uncommitted diff against main, after the first review's 21 findings, SRV-151 and SRV-152
  were addressed.
- **How:** four reviewers read the diff: the lifecycle server, the plugin with the crash waits, the 3D helpers, and
  the self-test's checks. No tests were run. The lead agent settled each suspicion by reading. Where reading
  couldn't, it used probes, one at a time:
  - in plain Python with Designer's PySide6: `_until` after `QCoreApplication.exit(0)` (HLP-157);
  - in plain Python: a kqueue given a negative timeout (SRV-159);
  - in one Designer opened hidden by the branch's `launch_designer` (alone's fresh server, port 9877), nothing
    opaque on the user's screen:
    - its environment and its crash handler, as `ps -E` and `pgrep` show them, while it ran and after its quit;
    - `_CLEAR` after the 'transparent in front' way, 8 times;
    - the covered way brought on screen by `_on_screen`, 3 times, and the drawing fact's covered way, 3 times;
    - a mesh switch and a tiling while hidden, then shown, twice each.
- **Dropped:**
  - `_CLEAR` making a window opaque while it is still on screen. Designer's main window was off the window server's
    list as macOS said hidden, 8 of 8.
  - A mesh or a tiling changed off screen, then shown with a render from before. At the show the view restarted by
    its second event, and the wait settled in 0.16 to 0.38 s, 4 of 4.
  - A second crash dump in one home missed after a first one (crash_watch). It takes two crashes, and the run fails
    on the first (DECISIONS.md, "Low-value findings about the tests and docs are not raised").
  - lifecycle's `CLOSE_WINDOWS_ONLY` reply never read. It matters only with a stale plugin installed, where the check
    still fails (the same rule).
  - The plugin's VERSION left at 8. No rule ties it to plugin changes, the wire protocol is unchanged, and `quit.py`
    handles a plugin without `_after_reply`.
  - The launch's front watch ending as the call returns, so a Designer unhiding itself later goes unseen: no sign of
    it.
  - shot3d.py's line "as its 3D view isn't drawn while covered": it held in the Designer probed (TST-433).
- **Not verified:**
  - Whether activating a Designer opened hidden unhides it. If it does, `give_back_activation`'s new "still hidden"
    branch never runs, and such a Designer is shown again. Measuring it makes Designer the active app, which takes the
    user's keyboard, so it takes their go.
    Note (2026-11-16): measured with the user's go: it does (SRV-161).
  - Whether `_Frames.shown` waits SETTLE_LIMIT for a covered window Qt keeps exposed, which may draw no paint at the
    show. The exposed-while-covered state SRV-152 recorded didn't occur in the Designer probed (TST-433), and what
    brings it about is unknown.
- **Resolutions assessed:** those whose fixes are in this diff: the first review's 21, SRV-151 and SRV-152.
  Questioned, as follow-ups:
  - SRV-152: TST-433, SRV-156, SRV-157, SRV-160, TST-441;
  - SRV-149: TST-435;
  - HLP-148: HLP-159;
  - HLP-150: HLP-157;
  - HLP-151: HLP-158, TST-439;
  - SRV-151: PLG-43, TST-436, TST-437;
  - SRV-153: SRV-159;
  - SRV-154: SRV-158;
  - TST-422: TST-438;
  - TST-425: TST-437;
  - TST-427: TST-440;
  - TST-432: TST-434.
  The others hold. DECISIONS.md: the 3D shot's entry stands, as its Reopen if is about what the user sees; so does
  WAKE_DELAY_MS's, with no callback found.
- **Findings:** 20.
  - Medium: TST-433.
  - Low-medium: HLP-157, SRV-156.
  - Low: SRV-157, SRV-158, SRV-159, SRV-160, HLP-158, HLP-159, PLG-43, TST-434 to TST-443.
- **Suggested order:**
  1. TST-433: the drawing fact fails in the Designer probed. Measure first what decides a covered window's exposure;
  2. HLP-157, the tools' code: a wait that runs on after Qt's quit;
  3. SRV-156 with SRV-157 and SRV-160, the launch's `open` path;
  4. the other Low ones.
- **Checked and found fine:**
  - `_until`, the quit aside: its limit, a wake lost between two looks caught at the next tick, an abort landing in
    its own frame, a nested wait;
  - HLP-153's messages and the fade's error; `_viewport`; the parts' order;
  - the after-reply callbacks: queued once the socket is closed, each run once, none for a refused or dropped job;
    `quit.py`'s fallback for an older plugin;
  - the crash waits: `pgrep -fl` prints whole command lines; the mark holds for /tmp and /private/tmp; off macOS
    the wait runs to its limit;
  - `_found_launched`: processes running before the launch, and other ports' launches, are left out; the exit
    watch's paths;
  - TST-422's, TST-423's, TST-425's and TST-429's checks; the off-screen block's structure; `who()`; `_HITS`;
    link_display's and bridge's new checks.
- **Chains:** the longest still growing are at generation 3: HLP-148 → HLP-150 → HLP-157; HLP-148 → HLP-151 →
  HLP-158 and TST-439; SRV-150 → SRV-153 → SRV-159; SRV-150 → SRV-154 → SRV-158; TST-421 → TST-432 → TST-434;
  TST-421 → TST-427 → TST-440; TST-421 → TST-425 → TST-437's material test. Those about tests or docs alone have
  fixes that make the claim smaller.

---

### 2026-11-16: the full-run-failures branch against main, third review (the diff only)

- **Scope:** the branch's uncommitted diff against main, after the second review's 20 findings, SRV-161, TST-444 and
  HLP-160 were addressed.
- **How:** four reviewers read the diff: the lifecycle server with the plugin and the macOS window helper, the 3D
  helpers, the editor_panels_and_fit checks with the window-server reader, and the self-test's infrastructure with the
  docs. No tests were run. The lead agent settled each suspicion by reading. Where reading couldn't, it used one probe,
  in a Designer opened hidden by the branch's `launch_designer` (alone, port 9877), nothing opaque on the user's
  screen. Its parts:
  - the 3D view's overlay labels before any shot;
  - a modal QMessageBox and a top-level window shown in the hidden Designer, each at opacity 0, every window of
    Designer's transparent and click-through first;
  - the HLP-158 check's read after a set-up from minimized, 5 times;
  - `covered` at each render of the transparent check's three ways, 3 times each;
  - Edit properties alone, the window on screen as a shot puts it;
  - 60 moves while Designer was hidden, each `taken()` timed.
- **Dropped:**
  - lifecycle's modal dialog, and its windows shown, unhiding a hidden Designer in front of the user's windows.
    Measured: the QMessageBox and the top-level window left Designer hidden 3 s on, its main window off screen, and
    Designer not the active app.
  - The HLP-158 check reading the minimized state before macOS says it. Measured: minimized at once, 5 of 5.
  - The tiling's wait taking a restart of Edit properties for its own. Measured: Edit properties alone drew no paint.
  - `alone.close`'s fixed 10 s wait for a crash dump: main's code, not in this diff.
  - `_has_port`'s `ps` and `_found_launched`'s `pgrep` with no time limit: so are the file's other process listings,
    on main too, and none was seen to hang. `open` got one because it can (SRV-160).
  - HLP-159's other case, a step's late restart landing after the next step's mark: it takes two steps each slower
    than NO_RESTART to show, and no such step is known.
- **Resolutions assessed:** those whose fixes are in this round: the second review's 20, SRV-161, TST-444 and
  HLP-160. Questioned, as follow-ups:
  - SRV-158: SRV-162;
  - HLP-158: HLP-161, HLP-163;
  - HLP-160: HLP-166, TST-445, TST-446;
  - SRV-151: TST-447;
  - TST-437: TST-448;
  - TST-428: TST-450;
  - TST-442, PLG-43, SRV-161: TST-451;
  - TST-443: TST-452.
  The others hold. The DECISIONS.md entries added on this branch name code that exists, and match it.
- **Findings:** 15.
  - Low-medium: SRV-162, HLP-161.
  - Low: HLP-162 to HLP-166, TST-445 to TST-452.
- **Suggested order:**
  1. SRV-162, the launch's wait;
  2. HLP-161, a render taken mid-accumulation;
  3. HLP-163, HLP-164, HLP-162, HLP-166, HLP-165, the other waits;
  4. TST-445, TST-446, TST-447, then the rest.
- **Checked and found fine:**
  - SRV-156's copy kept after `_OpenedUnfound`, SRV-157's whole-variable match, SRV-159's clamp, SRV-160's wait for
    `open`, SRV-161's `started_hidden` for an app bundle only;
  - PLG-43's tracing off, and no other code run from the plugin's slots under a job's tracer;
  - HLP-157's quit, HLP-158's `settled` and `taken` and the turn under `_on_screen`, HLP-159's drop rule, HLP-160's
    wait with the fade before it and an abort after it;
  - `_until`'s timers and connections after an abort; the window waits' spies removed in a `finally`;
  - FRAMES' and SHOWN_FROM_HIDDEN's scope (WHO, contextlib, the helpers' names), their spies removed and Display >
    Samples put back in a `finally`; COVERS recorded only once the window is on screen, not at the put-back's hide;
  - the off-screen and in-front split, pinned by its unit test;
  - `dumps_may_come`'s per-port marks, `CrashWatch.settle`, `end_own_designer`, `hide_designer` only in a Designer
    the self-test started, link_display's unload fact;
  - `WorkerResults` against what `__main__` writes.
- **Chains:** the longest still growing are at generation 4: SRV-150 → SRV-154 → SRV-158 → SRV-162; HLP-148 → HLP-151
  → HLP-158 → HLP-161 and HLP-163; TST-437 → TST-448; TST-442 → TST-451. Those about tests or docs alone (TST-448,
  TST-451) have fixes that make the claim smaller.

---

### 2026-11-16: the full-run-failures branch against main, fourth review (the diff only)

- **Scope:** the branch's uncommitted diff against main, after the third review's 15 findings and SRV-163 were
  addressed.
- **How:** four reviewers read the diff: the server with the plugin and the macOS window helper, the 3D helpers, the
  editor_panels_and_fit checks with the window readers, and the self-test's infrastructure with the docs. No tests
  were run. The lead agent settled each suspicion by reading. Where reading couldn't, it ran four probe scripts, one
  at a time, each in a Designer opened hidden by the branch's `launch_designer` (alone, port 9877). Designer's windows
  stayed hidden, or on screen transparent and click-through, as a 3D shot makes them. The probes:
  - `to_back`'s wait in `put('covered')`, timed, 3 times;
  - the Light tool check's moves, each timed, under the Light and the Camera tool;
  - a show from a count left low (Designer hidden mid-accumulation, then `screen.again()`), 5 times;
  - drags right after a mesh switch; then a mesh and an orbit in one call, in two, and in the shot's set-up, each part
    alone, and `[90, 0]` from Front against view Right.
- **Dropped:**
  - A drag's wait ending on an UpdateRequest that came mid-drag (`taking` counts requests from before the press).
    Measured: no request came during any of 8 drags, and each wait ended on one 0.03 s after the release. The probe
    found HLP-168 instead.
  - SRV-162's poll running all of `_running_on` every POLL_S while no Designer is recorded. It is the poll AGENTS.md
    asks for where no callback exists: a Designer that starts listening on another port has none. Its docstring's
    "nothing says so" is half true, as a watch on the records folder would say a record. That is a generation-5
    follow-up on a doc that changes nothing anyone does (DECISIONS.md, "Low-value findings about the tests and docs
    are not raised").
  - The frames fact's unit test passing with `_shown`'s "every paint reads 8" removed. It is generation 3 on tests,
    whose fix would add a case, and no sentence says each clause is pinned (the chain rule; the same decision).
- **Not verified:** each needs a window on the user's screen, which takes their go.
  - Whether the window checks' set-ups (`to_back`, `_PUT`'s IN_FRONT ways) wait out their 3 s limit when another
    app's window covers Designer's whole frame at the unhide. HLP-166 replaced that wait in `give_back_activation`.
    In the Designer probed, no other app's window was in front of Designer's. `to_back`'s wait ended at the show in
    0.02 s, 3 of 3: Qt exposed the window while macOS said it covered. The first review's log asks the same.
    Note (2026-11-16): measured with the user's go, a window of theirs in front: it doesn't. macOS said Designer's
    window covered whole, one window of another app's in front of it, and Qt exposed the window at the unhide: the
    waits ended in 0.020 to 0.024 s, `to_back`'s 3 of 3 and the 'on screen' way's 3 of 3.
  - Whether lifecycle's hand-over check, which starts a Designer from its binary, puts a window on the user's
    screen, or makes the run's hidden Designer come in front as it takes the hand-over (DECISIONS.md, the Project
    rules entry on Designer during tests; README's exception for it). What would check it: a FrontWatch around the
    start and the hand-over, with `stayed_off_screen` read for both processes.
    Note (2026-11-16): measured with the user's go: it doesn't. Under a front watch (about 157 samples over 11 s
    each time), neither the Designer started from its binary nor the run's hidden Designer was the active app or had
    a window on screen, at any layer, 3 of 3. The check passed each time.
- **Resolutions assessed:** those whose fixes are in this round, the third review's 15 and SRV-163, and the fixes the
  findings below follow. Questioned, as follow-ups:
  - SRV-163: SRV-164;
  - HLP-163: HLP-167;
  - HLP-158: HLP-168;
  - HLP-164: HLP-169;
  - TST-445: TST-453;
  - TST-421: TST-454, TST-455, TST-457;
  - HLP-150: TST-455;
  - TST-426: TST-456;
  - TST-452: TST-459.
  TST-458 is TST-261's defect back, brought by SRV-151's crash wait. The others hold: SRV-162, HLP-161, HLP-162,
  HLP-165, HLP-166 (its Also covered: Not verified, above), TST-446 to TST-451. DECISIONS.md's 3D shot and camera turn
  entries stand: their Reopen if isn't met.
- **Findings:** 11.
  - Low-medium: TST-453.
  - Low: SRV-164, HLP-167, HLP-168, HLP-169, TST-454 to TST-459.
- **Suggested order:**
  1. HLP-167 and HLP-168, the tools' code: a shot rendered mid-accumulation, and a set-up that varies;
  2. SRV-164, the launch;
  3. TST-453, a false failure of the full run;
  4. TST-454, TST-457, TST-458, then the rest.
- **Checked and found fine:**
  - `_pgrep`'s exit codes and `OSError`; `_NoListing` in core.py, bound in both modules; the callers that catch it
    (`_any_designer`, `_agent_record`, `_appeared`, `_launched_now`, `_start_designer`'s `_force_end`s);
  - `may_have_exited`'s watches and their close in the `finally`; quit.py's `_after_reply` lookup and its fallback;
    the plugin's callbacks after a failed send, and `_on_after`'s docstring;
  - `_Counts`' `seen` aligned with the paints; a shot's first `_Frames` counting a low paint as a restart; every
    `_Frames` wait bounded and woken; renders taken between polls; the abort paths' clean-ups;
  - FIRST_SHOT's and FRAMES_DROPPED's patches put back in a `finally`; `run()`'s order; the windows put back after
    each put; the spies removed;
  - `crash_handlers`' None and `dumps_may_come`; `CrashWatch.settle`'s attribution; `end_own_designer` waiting on its
    own process; `hide_designer` only where the self-test started Designer;
  - ROADMAP item 100's figures against the code; DECISIONS.md's names and paths.
- **Chains:** the longest still growing is at generation 5: HLP-148 → HLP-151 → HLP-158 → HLP-163 → HLP-167. Next,
  at generation 4: HLP-158 → HLP-168. The generation-3 follow-ups about tests or docs alone (TST-453, TST-455's cancel
  check, TST-456, TST-459) have fixes that add no check.
- **Then,** at the user's request, the 11 findings addressed in the suggested order, test first, all done. HLP-168
  was measured first: moves made off screen don't always come out as on screen, the mesh step aside. The user
  chose to run a `set_3d_view` that moves the camera on screen ("Show the window (Recommended)"), added to
  DECISIONS.md's camera turn entry. The in-front window checks weren't run in a scratch run, as they put an opaque
  window over the user's; the fixes change nothing they judge.
- **Then,** at the user's request, DECISIONS.md's camera turn entry was removed: nothing cited it, and AGENTS.md's
  wait rule already rules out what it turned down (notes under HLP-158 and HLP-168). The entry on Designer during
  tests was cut to its rule, its reason and its reopen condition.

---

### 2026-11-16: the full-run-failures branch from ec984a9 to HEAD, fifth review (one diff)

- **Scope:** every change from ec984a9 to HEAD (cb66092), ec984a9 included, read as one diff:
  `git diff c9d9774..HEAD`, c9d9774 being ec984a9's parent, 83 files. The code as it stands at HEAD, the five
  commits read together, since each built on the one before.
- **How:** seven reviewers read the diff by area: the lifecycle server with the plugin; the preferences put-back,
  uninstall and crash dumps; the 3D view's set-up and its waits; the 3D shot's window; the editor_panels_and_fit
  checks; the window states and readers; the self-test's infrastructure with the docs. No tests were run. The lead
  agent settled each suspicion by reading. Where reading couldn't, it ran four probes, one at a time, each in a
  Designer opened hidden by the branch's `launch_designer` (port 9877). Designer's windows stayed hidden, or on
  screen transparent and click-through, as a 3D shot makes them. The probes:
  - the preferences lock, timed through three launches by `open` and their quits, the server run in the probe's
    process;
  - `set_3d_view(mesh=...)` in a Designer just started, before any 3D shot (HLP-170);
  - set-ups of an orbit of two drags, or of one, then a zoom, 8 in all, each `settled()` timed with the counts read
    around its mark;
  - Qt's signals and the top-level widget's events during 4 minimizes and 4 hides (HLP-173).
- **Dropped:**
  - The preferences lock held through `open` and the search for its process, against DECISIONS.md's "(up to about
    10 s)". Measured: a launch held it 0.24 to 0.25 s, 3 of 3. The limits of `open` and the search run only on
    failure, which SRV-160 bounded. The entry's Reopen if isn't met.
  - A move option after an orbit of two drags never seeing its restart, the mark being taken at a count of 1, so
    that `settled()` would wait NO_RESTART. Measured: the count climbed to 3 after the mark before the zoom
    restarted it, and each wait ended in 0.046 to 0.049 s, 4 of 4, and 4 of 4 after an orbit of one drag.
  - The user's clipboard switching between the render and their text during a shot's renders: DECISIONS.md's
    clipboard entry (the user doesn't mind losing their clipboard when an agent needs it, as long as the text comes
    back).
  - The first 3D shot's check skipping if a 3D shot ever comes before it in `run()`: a guard against a future edit,
    and its skip says why in each run.
  - The same facts in AGENTS.md, README.md, the live-check skill and `alone.py` (the crash dump folders, uploads
    off, `alone.close()` naming a dump): they agree (DECISIONS.md, low-value findings: two places that agree).
- **Not verified:**
  - Off macOS, `view=` with Designer minimized. `_on_screen` does nothing there, so the turn's wait ends at once,
    and Frame comes right after it, which on macOS cancels the turn. Before this range it waited VIEW_TURN. It
    needs Windows: set the view with Designer minimized, then compare a shot with one set with the window shown.
  - Whether an unload in a Designer on screen finishes its teardown before the next call: the first review's Not
    verified, still open. SRV-167 narrows the docs meanwhile. It needs Designer drawing on the user's screen, which
    takes their go.
    Note (2026-11-16): measured with the user's go: it does. In a Designer an agent started, shown on screen, opaque
    and not the active app, with Designer's `node_align_tools` loaded, link_display's fact read 327 widgets gone
    within the unload, 504 by the next call and 504 by the one after, 5 of 5, as hidden. 20 `set_link_display`
    reloads (portal, then wire) all reloaded and reopened, with no crash dump.
  - Whether the window checks' 'minimized' way, made opaque as macOS's minimize animation runs, flies to the Dock
    opaque: the first review's Not verified, still open. Moving its `fade(False)` after `until(reached)` would make
    the question moot. Seeing it takes the user's go.
    Note (2026-11-16): measured with the user's go: it does (TST-472). Sampled from outside Designer during
    `put('minimized')`, about 0.1 to 0.65 s after the call began, the window server listed Designer's main window
    on screen at opacity 1, shrinking from its frame to the Dock's icon, 6 of 6. It was listed behind every other
    app's window in each sample.
- **Resolutions assessed:** those whose fixes are in this range, the four earlier reviews' of this branch included.
  Questioned, as follow-ups:
  - SRV-152: SRV-165;
  - SRV-124: SRV-166;
  - SRV-150: SRV-167;
  - SRV-151: TST-466;
  - HLP-162 and HLP-152: HLP-170;
  - HLP-150: HLP-171;
  - HLP-163: HLP-172;
  - HLP-145 and HLP-160: HLP-173;
  - HLP-168: HLP-174, TST-465;
  - HLP-167: TST-463;
  - TST-418: TST-464;
  - TST-453: TST-464, TST-467;
  - TST-417: TST-467;
  - TST-420: TST-465;
  - TST-441: TST-468;
  - TST-426: TST-469.

  HLP-161 holds (the probe above). The others hold. DECISIONS.md's entries in scope stand: their Reopen if isn't
  met, and the names and paths they cite exist.
- **Findings:** 22.
  - Low-medium: SRV-165, HLP-170, TST-460.
  - Low: SRV-166, SRV-167, INS-37, HLP-171 to HLP-175, TST-461 to TST-471.
- **Suggested order:**
  1. SRV-165, a launch that can end the user's Designer;
  2. HLP-170, a tool failing in a Designer just started;
  3. TST-460, TST-470 and TST-471, Designer's windows in front of the user's during tests;
  4. the tools' code: SRV-166, HLP-171, HLP-172, HLP-173, INS-37;
  5. the tests' waits: TST-466, TST-469, TST-463;
  6. the docs and types: SRV-167, HLP-174, TST-465, TST-467, TST-468, TST-464, TST-462, HLP-175, TST-461.
- **Checked and found fine:**
  - the plugin's after-reply callbacks: each run once, in order, on the main thread, none for a status or a cancelled
    job; `_pgrep` and `_NoListing` at every caller; `open`'s limit and its stderr; `_OpenedUnfound` raised after
    `saved()`, which keeps the copy; the locks taken in one order, the port's then the preferences';
  - `designer_preferences.py` at HEAD: the put-back's order, the copy written 0600 then replaced, no error escaping
    into a tool or into uninstall; `uninstall.py` on every path; the standalone scripts on Python 3.9;
    `read_crash_dump.py`'s offsets and bounds against the minidump layout;
  - crash uploads written only in an agent's own home; `--env CFFIXED_USER_HOME` keeping an agent's Designer out of
    the user's log and plist;
  - `_drag`'s guard and its release in a `finally`; `taking()`'s counts; `_wheel`'s wait per notch; `_Counts`'
    rules (HLP-159, HLP-167); `_until`'s connections; `_Frames`' close; views.py's checks of orbit and pan;
  - `_Screen`'s put-back orders, the refusal after BRINGS, every spy removed in a `finally`, nothing making Designer
    the active app;
  - every `put()` cleared in a `finally`; the snippets' filters and watches closed; the checks' readers failing when
    they can't tell;
  - the pool: `choose()` next to the user's Designer, the put-back through `_any_designer`, every crash wait
    bounded, `check_the_preferences` after every worker; the unit tests kept off the real plist, log and crash
    folders.
- **Chains:** the longest still growing is at generation 6: HLP-148 → HLP-151 → HLP-158 → HLP-163 → HLP-167 →
  TST-463. At generation 5: HLP-163 → HLP-172, in the tools' code; HLP-158 → HLP-168 → HLP-174 and TST-465, docs.
  The follow-ups at generation 3 or later about tests or docs alone (HLP-174, TST-463 to TST-465, TST-467 to
  TST-469) have fixes that add no check.
- **Then,** with the user's go, the two questions that needed a window on their screen were measured (the notes
  under Not verified): the unload on screen as hidden, and the 'minimized' way flying to the Dock opaque, which became
  TST-472 (Low-medium). The findings: 23.
- **Then,** at the user's request, all 23 addressed in the suggested order, test first, all done. Measured first: the
  second show after SHOW_AGAIN never came since HLP-160 (60 of 60 waits), and no Qt callback says a hide or a
  minimize (HLP-173, which then dropped its wake-ups). The first run of the category failed one check on a leftover
  of HLP-170's new check, which then set the mesh alone. Live: HLP-170's and TST-472's checks failed in their scratch
  runs, then against the old code put back in a copy for the run; then the whole category passed, 96 of 96, in a
  Designer just started, its in-front checks with the user's go.

### 2026-11-16: the full-run-failures branch, sixth review (eccfc1a: the fifth review's fixes)

- **Scope:** the changes since the fifth review, `git diff cb66092..eccfc1a`: one commit, 34 files, the fixes of the
  fifth review's 23 findings. Whether each of those resolutions holds.
- **How:** three reviewers read the diff by area: the server, the crash dump script and the docs; the 3D helpers; the
  self-test. No tests were run. The lead agent settled each suspicion by reading, and with two probes. Nothing of
  Designer's came on the user's screen:
  - in plain Python, on Designer's own Python 3.13.9 and on 3.12: three helpers' try/finally shapes, copied with
    fakes, an abort raised at each traced event in turn (HLP-177);
  - in a Designer `launch_designer` opened hidden on port 9877, after editor_panels_and_fit's preparation: the mesh
    shown before and after NEVER_DREW (TST-475). Its quit took 1 s and left no crash dump.
- **Dropped:**
  - SRV-166's second test not checking which path ran, with setup it doesn't use. By reading, each case takes the path
    its id names: SIGTERM ends the process, and `-1` makes `_force_end` fail, so the call raises. Asserting the path
    would make a generation 4 check of a test alone stronger (Follow-up chains). The launch fakes are a guard: nothing
    real starts.
  - shot3d.py's sentence that no Qt callback says the window is off screen after a minimize, where HLP-173 measured
    the top-level widget's Hide event for each minimize. That event came before the window server stopped listing the
    window, the state the wait reads, so it can't end the wait. A docs follow-up at generation 3 that changes nothing
    anyone does (DECISIONS.md, low-value findings). ROADMAP item 101 measures AppKit's notifications.
  - `_CLEAR`'s NOT_HIDDEN, which no caller reads. It shows only after a hide that failed, which no run has seen, and
    the worst it does is leave a Designer an agent started on screen, transparent and click-through (DECISIONS.md,
    low-value findings).
- **Not verified:** whether the window server draws Designer's windows opaque during TST-474's loop. Seeing it takes
  Designer's windows opaque on the user's screen, which needs their go. TST-474's fix doesn't depend on it.
- **Resolutions assessed:** the fifth review's 23, all fixed in this range. Questioned, as follow-ups:
  - INS-37: INS-38;
  - SRV-165: SRV-170;
  - SRV-166: SRV-168, SRV-169;
  - HLP-170: HLP-176, TST-475;
  - HLP-171: HLP-177;
  - HLP-173: HLP-178;
  - TST-460: TST-474;
  - TST-461: TST-476;
  - TST-471: TST-473.

  The others hold: SRV-167, HLP-172, HLP-174, HLP-175, TST-462 to TST-470, TST-472. DECISIONS.md's entries in scope
  stand: their Reopen if isn't met.
- **Findings:** 11.
  - Low-medium: INS-38, HLP-177.
  - Low: SRV-168, SRV-169, SRV-170, HLP-176, HLP-178, TST-473 to TST-476.
- **Suggested order:**
  1. HLP-177, the user's parameter, a temporary node or package, or the Explorer menu's look left after an abort;
  2. INS-38, two unit tests failing on Windows;
  3. the tools' code: SRV-169, SRV-168, HLP-176;
  4. the self-test: TST-473, TST-474;
  5. the docs, names and types: SRV-170, HLP-178, TST-475, TST-476.
- **Checked and found fine:**
  - SRV-165: the home, `/tmp/sd_mcp_<uid>_<port>/home`, holds no space, so splitting `ps -E`'s line is safe;
    `CFFIXED_USER_HOME` is set on every `open` path; the marks are matched as whole variables; two matches would need
    the same port and home, which `_launch_lock` and `before` rule out;
  - SRV-166's raise in `_quit`, in order; `_sentence` leaving a failed sample's own stop alone; SRV-167's GUIDE.md
    and docstring against the log's measurement; INS-37's checks matching `_checked_folder`'s and uninstall.py's, on
    Python 3.9 too;
  - HLP-171 in `_3d_render`: an abort anywhere in its put-back leaves the text put back, at most twice; HLP-170's
    other paths (`moved()`, `shown()`, Samples off on screen); HLP-172's `between()` before the recursion; HLP-173's
    waits, bounded, and its refusal; HLP-174's docstrings; HLP-175's marks;
  - the re-indented `run()` (`git diff -w`: the moved `with` and the new checks only); `window(geometry, name, ...)`
    at every caller; `_UNDER`'s `del`; every set-up's clear in a `finally`; TST-472's order and its check; `low()`;
    PopupWatch's `layer`; `alone.close_with`'s poll; `_quit_to_keep`; each new source test failing on the old
    snippets.
- **Chains:** TST-463's chain, at generation 6, stopped: its resolution holds. The longest still growing is at
  generation 4: SRV-124 → … → SRV-166 → SRV-168 and SRV-169; HLP-148 → HLP-150 → HLP-171 → HLP-177; HLP-170 →
  HLP-176 and TST-475. SRV-169, SRV-168, HLP-176 and HLP-177 are in the tools' code. The follow-ups about docs or
  tests alone at generation 3 or later (SRV-170, HLP-178, TST-475) have fixes that make the claim smaller.
- **Then,** at the user's request, all 11 addressed in the suggested order, test first, all done. Measured first, in
  Designers an agent started, hidden: a package's UID, not its handle, names it from one listing to the next, and
  unloading a package twice crashed that Designer. In plain Python, an abort at a `try:` line escapes the `try` around
  it in the same function, which the look's restructure followed. The fixes were saved aside while every new test ran
  against the old code: each failed, unit and live; then they passed. Scratch runs: HLP-177's live checks, measure and
  discovery whole (40 of 40), and editor_panels_and_fit's changed paths in a Designer just started under a front watch
  (11 of 11). The in-front group didn't run.

### 2026-11-16: the full-run-failures branch from ec984a9 to HEAD, seventh review (one diff)

- **Scope:** every change from ec984a9 to HEAD (f1ad9f6), ec984a9 included, read as one diff:
  `git diff c9d9774..HEAD`, 89 files. The code as it stands at HEAD. f1ad9f6, the sixth review's fixes, was read for
  the first time.
- **How:** seven reviewers read the diff by area: the lifecycle server with the plugin; the preferences put-back,
  uninstall and crash dumps; the 3D view's set-up and its waits; the 3D shot's window and the clipboard; the helpers'
  put-backs after an abort; the editor_panels_and_fit checks; the self-test's infrastructure with the docs. No tests
  were run. The lead agent settled each suspicion by reading, and with two probe runs, one after the other. Each ran
  in a Designer `launch_designer` opened hidden on port 9877 (`alone.run`, a graph of the probe's own). Designer's
  windows stayed hidden, or on screen transparent and click-through, as a 3D shot makes them. The user's clipboard
  text was saved first and put back after. The probes:
  - a render taken as Designer's window came on screen during `_renders_alike`'s wait, in a view that never drew;
  - whether `g.compute()`, `loadUserPackage` and `newInstanceNode` run Qt's events: a 0 ms timer, a posted event, and
    a mouse-moved NSEvent queued in Designer's own application, seen by a native event filter;
  - the clipboard after a 3D shot: read while a 12 s job held Designer's main thread, after that Designer was killed,
    and after a normal quit (HLP-181).

  Neither Designer left a crash dump.
- **Dropped:**
  - `_delete_new_nodes` and `_unload_new_packages` removing a node or a package the user added while the call ran,
    where the old code removed only the one it made. Measured: `g.compute()` runs Qt's events (a 0 ms timer ran inside it
    in 3 computes of 3, a posted event in 2 of 2). A mouse-moved event queued before it was dispatched only after it
    (1 of 1), where one queued before a `processEvents` was dispatched there. `loadUserPackage` and `newInstanceNode` ran none. The user's input waits for the call's end, and no job
    runs inside another (PLG-35).
  - `_renders_alike`'s first render, taken as the window comes on screen, coming before any paint in a view that never
    drew, and raising. Measured: the render came after the view's first paint and gave an image (1 of 1).
  - The Explorer menu left opaque by an abort in a look that found no menu yet (two reviewers): the menu is there at
    the first look (measured; the look's comment). An abort reaching the look's call after one was dropped elsewhere
    is the case `_menu_once`'s docstring gives.
  - A second Designer ended in launch_designer's wait replacing the note of the first: main's code, unchanged by the
    range. It needs two servers launching on one port, with both Designers hung.
  - SRV-170 missing the name and comment of `test_the_process_open_started_is_the_new_one_with_its_port`, which give
    the port alone: a generation 4 wording follow-up that changes nothing anyone does (DECISIONS.md, low-value
    findings). So is `_unload_new_packages`' citation of discovery's checks for a library package's file: those checks
    pin the file only for a package the API makes.
  - The hand-over Designer, started from its binary, uploading a crash report: it never answers, and the server's
    docstring says a crash before a Designer answers may still be uploaded. No run has seen it crash.
  - `Reply` copied from `server_tools/core.py` into `common.py`, filled by `raw_request`'s `Any`: `raw_request` is
    main's, unchanged (DECISIONS.md, vague types).
  - Outside the range, for the user to weigh: `tests/unit/test_library_subfolders.py:126` calls `os.geteuid()`, which
    Windows lacks, in a test not skipped there. It is main's code from before ec984a9; the Windows unit suite fails it.
- **Resolutions assessed:** the sixth review's 11, all fixed in f1ad9f6. Questioned, as follow-ups:
  - HLP-177: HLP-179, HLP-180;
  - INS-38: INS-39;
  - SRV-169: SRV-171;
  - TST-474: TST-478.

  The others hold: SRV-168, SRV-170, HLP-176, HLP-178, TST-473, TST-475, TST-476. DECISIONS.md's entries in scope
  stand, except the clipboard entry, whose Reopen if holds (HLP-181).
- **Findings:** 8.
  - Low-medium: HLP-179, HLP-180, HLP-181, INS-39.
  - Low: SRV-171, TST-477, TST-478, TST-479.
- **Suggested order:**
  1. HLP-179, a tool's result saying the user's parameter may not be back;
  2. HLP-180 and HLP-181, the user's screen and clipboard after a 3D shot. HLP-181's fix may want the user's word,
     as the clipboard entry is theirs;
  3. INS-39, two unit tests failing on Windows;
  4. SRV-171, the tools' errors;
  5. the self-test: TST-478, TST-477;
  6. the types: TST-479.
- **Checked and found fine:**
  - SRV-168's order on every path; SRV-169's `try` in `_quit` covering each listing after the close;
    `_quit_evidence` never raising `_NoListing`; SRV-170's comment, conftest parameter and renamed test;
    `_force_end`'s other callers; the locks taken port first; `_remember_started` under both locks;
  - INS-38's `getattr(os, 'getuid', None)` and its 'no user ids' case, which fails on the old code; no other
    POSIX-only call reachable on Windows in the preferences, uninstall and crash dump code; the plist written only by
    `_put_back`, after `running()` and `_users_ran_since`; the dump reader's bounds; Python 3.9;
  - HLP-176's fix and test; HLP-177's `unfade` order, `_menu_once`'s two put-backs, and the look's handler covering
    `fade`'s and `pick`'s `try:` lines; every other `finally` of the helpers (`_set_tiling`, `_drag`, `_mouse`, the
    spies); the order of PARTS;
  - HLP-177 in sweep, describe and editor: each put-back runs again untraced, and never unloads or deletes twice;
    nothing is made before either `try:` line; `at_each_event` raises at every event, and each test fails on the old
    code; the live checks fail without the fix and clean up;
  - HLP-178's docstring; HLP-171's put-back at HEAD; HLP-173's waits; nothing making Designer the active app; holds
    and spies balanced;
  - TST-473's order and its pin, with no order dependence; TST-474's `_CLEAR` and its pin; TST-475; TST-476;
  - the pool's `check_the_quits` and `check_the_preferences`, `alone.close_with`, the launch lock, `HIDE`'s order,
    `link_display`'s unload fact, the removed pauses; every name the changed docs cite exists.
- **Chains:** the longest still growing is at generation 5, in the tools' code: HLP-148 → HLP-150 → HLP-171 →
  HLP-177 → HLP-179 and HLP-180; SRV-124 → … → SRV-166 → SRV-169 → SRV-171. At generation 3: INS-37 → INS-38 →
  INS-39, the script's code with its tests; TST-460 → TST-474 → TST-478, the self-test's code, which can leave
  Designer opaque on the user's screen. Its fix adds no check beyond its unit pin.
- **Then,** at the user's request, all 8 addressed in the suggested order, test first, all done. Every new test failed
  first: the unit tests in one run, the three live checks in one scratch run. HLP-181's unit test and TST-477's new
  version, written with or as the fix, failed with the fix taken out and on a mutant without the lock. HLP-181's fix
  was measured first: resolving Qt's promises through Carbon crashed that Designer, and reading them back worked. After
  the fixes, the scratch run passed 16 of 16: the three new checks, HLP-177's sweep checks, and editor_panels_and_fit's
  shot window checks off screen under a front watch. Then `/simplify` once (AGENTS.md), its fixes changing no
  behaviour: the clipboard's read-back made a method of `_MacWindow`, the wait for a running job shared
  (`common.until_job_running`), the sweep's fakes shared, `at_rest` the only way to the clear's snippet, the step
  sentences joined plainly. Two slips of the fixes it found were mended: the material check stopped only after its
  tiling shot, and a test's message lacked its `% where`. Left out: the material check hiding Designer through
  `at_rest` in a job of its own (a change of behaviour), a helper for the two measure checks' set-up (a module of its
  own for six lines). The touched unit tests passed before and after, and the scratch run passed 18 of 18, with the
  bridge's cancel check.

---

## High

## Medium-high

- [x] **TST-432 · The self-test's HIDE never hid a Designer: the window handle it took was already deleted** · follows TST-421, generation 2 · `tests/test_all_tools/common.py` (`HIDE`), `editor_panels_and_fit/checks.py` (`ADD_MATERIAL`) · measured · found 2026-11-15
  - **Defect.** `HIDE` took `mw.window().windowHandle()` in one expression. A line later the handle read "Internal
    C++ object (PySide6.QtGui.QWindow) already deleted", and `_event_signal` raised before the hide.
  - **Scenario.** Measured while addressing the review (2026-11-15): a Designer `alone.run` started stayed on the
    user's screen, opaque, for a whole probe run, about 20 s ("self-test: Designer wasn't hidden: ... already
    deleted"). The same expression, in 4 of 4 fresh calls, gave a deleted handle; with `mw.window()` held first, a valid one.
    Once a wrapper was held elsewhere, the same expression gave a valid handle too. Every Designer the self-test
    started since TST-421's change stayed on the user's screen: in a full run, each worker's.
  - **Fix.** Hold the top-level widget while its handle is used: `top = mw.window()`, then `top.windowHandle()`.
  - **Resolution: done.**
    - **Test:** `check_the_self_tests_hide_hides_designer` (editor_panels_and_fit) failed in its scratch run on the
      deleted handle, then passed (`HIDDEN=True`). `test_no_window_handle_is_taken_through_a_wrapper_dropped_at_once`
      fails on the expression anywhere in the code.
    - **Also covered:** `ADD_MATERIAL` took the handle the same way; SRV-155 in the tool's code. No other
      `windowHandle()` call takes it through a dropped wrapper.
  - Questioned by TST-434 (2026-11-15).

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

  - Note (2026-11-16): HLP-160 found a cause that fits these readings (`hidden=False covered=True`): brought in
    front before Designer's unhide took, the window went behind the active app's window as it took. The shot now
    waits for the unhide first; the show-again after SHOW_AGAIN stays.
  - Questioned by HLP-173 (2026-11-16).
- [x] **SRV-149 · A Designer launch_designer starts comes in front of the user's windows and takes their keyboard until it answers** · follows SRV-148, generation 2 · `mcp_server/server_tools/lifecycle.py:324-336` (`_designer_env`), `:413-430` (`_started`) · measured · found 2026-11-15
  - **Defect.** `_started` runs Designer's own binary. Designer's Qt makes the app the active one as it finishes
    launching, so its window comes in front of the user's and their typing goes into it. SRV-148 gives the keyboard
    back only once Designer answers, about 6 to 20 s later. A full run of the self-test starts 23 Designers, so the
    user's work is interrupted again and again: they reported "it is a deal breaker" (2026-11-15).
  - **Scenario.** Measured. SRV-148's probe found every launch in front as the active app. Designer's Qt is 6.8.6, and
    its Cocoa plugin reads `QT_MAC_DISABLE_FOREGROUND_APPLICATION_TRANSFORM`, which stops that activation. A probe
    started one agent's Designer through `launch_designer` with that variable set in the server's environment, and
    watched from another process: the active app (`lsappinfo front`) and the window server's list, every 50 ms, with
    PyCharm in front. It ran three times, twice with `QT_MAC_SET_RAISE_PROCESS=0` set too. In each, over about 190
    samples of the 8.6 to 8.8 s launch, Designer was never the active app, and its window was never the frontmost
    normal window. The only Designer window above PyCharm's was one at popup level, 575 × 387 in the middle of the
    screen, fading out (opacity 0.94 to 0.05) over 0.13 to 0.22 s as Designer answered: its splash or Home screen,
    most likely. A screenshot of the whole window worked after it. `QT_MAC_SET_RAISE_PROCESS=0` isn't needed, and the
    undo checks rely on a raise activating Designer (TST-234).
  - **Fix.** `_designer_env` sets `QT_MAC_DISABLE_FOREGROUND_APPLICATION_TRANSFORM=1` on macOS. Test: a unit test of
    the environment, and a lifecycle live check watching a launch from the self-test's process, both seen failing
    first.
  - **Resolution: done.**
    - **Test:** `test_lifecycle_env.py::test_a_designer_started_on_macos_doesnt_make_itself_the_active_app` failed
      first: the variable wasn't set. Lifecycle's new check "starts Designer behind the other apps: never the active
      app, its window never in front of theirs" (renamed since: below), in `check_launch_on_another_port`, watches the second Designer's
      launch from the self-test's process (`window_server.FrontWatch`). In its scratch run it failed first: "the
      active app 4.60 s, its window the frontmost 1.93 s; 120 samples, 41 listing its windows". After the fix it
      passed: 0.00 s and 0.00 s, of 92 samples, 27 listing its windows, and the splash's fade above the other windows
      in 2 samples. The watch's own unit tests: `test_selftest_window_server.py`.
    - **Then measured** (2026-11-15), with each window's bounds read too: the Designer started came up behind the active
      app's window but over another app's window, for 1.88 s of its launch, never the frontmost. So the check, renamed
      "starts Designer behind the app in front: never the active app, its window never in front of its", counts only
      the active app's windows (`stayed_behind(..., active_only=True)`), and the docs say "behind the app in front".
    - **Cause:** Designer's Qt makes the app the active one as it finishes launching, and nothing turned that off.
    - **Fix:** `_designer_env` sets `QT_MAC_DISABLE_FOREGROUND_APPLICATION_TRANSFORM` (`STAY_BEHIND`) on macOS. The
      module docstring has the measurement. `give_back_activation` stays, for a Designer that still becomes the
      active app. `QT_MAC_SET_RAISE_PROCESS` is left as Qt sets it, for Undo (TST-234).
    - **Also covered:** every Designer the server starts gets its environment from `_designer_env`, and so does the
      self-test's hand-over check, which starts the binary itself. The window checks now set up their ways behind every
      window, with Designer hidden at rest, and those that need a window in front of the user's run together, after
      them. The Undo checks still raise and activate their Designer's window, as Undo needs. The tool's docstring,
      `mac_window.py`'s docstring and README say a Designer starts behind the app in front. The CoreGraphics reading
      the popups' watch had moved to `window_server.py`, shared by both watches.
  - Questioned by TST-435 (2026-11-15).

- [x] **SRV-152 · A Designer launch_designer starts comes up in front of the active app's window** · `mcp_server/server_tools/lifecycle.py` (`_start_designer`, `STAY_BEHIND`), `tests/test_all_tools/lifecycle/checks.py` (`check_launch_on_another_port`) · measured · found 2026-11-15
  - **Defect.** The window of a Designer an agent starts showed in front of the active app's window, in front of the
    user's work, though `STAY_BEHIND` was measured to start it behind that window (lifecycle.py's docstring). It
    never became the active app, so the keyboard stayed the user's.
  - **Scenario.** Measured with lifecycle's watch of the window server (2026-11-15), four launches of a second Designer
    on another port, while the user worked: in front of the active app's window for 3.69, 0.65 and 5.66 s, and from
    its first appearance, 4.5 to 4.9 s into the launch, until the launch returned. At that first sample, its window
    was the frontmost normal window, the active app's one window right behind it. The same with the launch's old 2 s
    poll restored for one probe run, so SRV-150's change isn't the cause. A scratch run earlier the same day passed,
    0.00 s in front. `check_launch_on_another_port` fails.
  - **Fix.** Measure what decides it: which app is active, how many windows it has, and whether a start flag
    (`open -g`, or Qt's) keeps Designer's window behind. Measuring it shows Designer's window in front of the user's,
    so it takes the user's go.
  - Note (2026-11-15): README.md ("start behind the window you're working in") and lifecycle.py's docstring
    still say a launch stays behind the active app's window. The fix brings them in line with what it measures.
  - **Resolution: done.**
    - **Measured first** (2026-11-15, with the user's go), `launch_designer` with its process started each way, under
      the front watch, the active app's window in front:
      - from its binary (`STAY_BEHIND` set): in front of another app's window for 2.70 s and 0.69 s, of two launches;
      - `open -n -g`: 0.63 s, of one;
      - `open -n -g -j` (hidden): none of its windows on screen and never the active app, in 4 of 4 launches, each
        answering in 5.4 to 6.4 s. `ps -E` read `SD_BRIDGE_PORT` in the new process's environment each time.
    - **Test:** `test_launch_opens_a_new_instance_hidden_with_the_port`,
      `test_the_process_open_started_is_the_new_one_with_its_port`, `test_a_process_open_started_that_never_shows_is_said`,
      the watch's `test_a_designer_started_hidden_shows_no_window_and_never_becomes_the_active_app`,
      `test_the_launch_check_judges_designer_started_off_screen` and
      `test_a_designer_started_hidden_that_became_the_active_app_stays_hidden` failed. Live: lifecycle's launch check.
    - **Fix:** on macOS an app bundle is opened by `open -n -g -j`, with the variables Designer reads passed by
      `--env` (`_opened`). Its process is the new one whose environment has the launch's port, looked for every
      POLL_S (`_found_launched`). `give_back_activation` leaves a hidden Designer hidden. Lifecycle's check judges
      `window_server.stayed_off_screen`: never the active app, no window of its on screen. Docs:
      `launch_designer`'s docstring, lifecycle.py's and mac_window.py's, README.
    - **Found along the way:** Designers `open` starts behave unlike those started from their binary. Covered, their
      window stays exposed for Qt, and their 3D view draws (also with `open -g`, shown: 1 launch). The drawing fact now
      says so; the stale-render check uses the minimized way; `_PUT` and the cover events wait on macOS's covered state,
      not exposure. The check that a shot's window is transparent at each render no longer judges macOS's covered
      state there: unhidden, a window of the user's may cover it until the shot brings it in front. shot3d.py's
      docstring says the rest was measured in Designers started from their binary. DECISIONS.md's 3D-shot entry
      stands: the shot still brings a covered window in front.
    - **Result:** in scratch runs, lifecycle whole 54 of 54 (twice); in a Designer opened hidden,
      `editor_open_and_zoom` and `layout` whole, the panel screenshots, the 3D view and window checks off screen, the
      HIDE check: 92 of 92. The frames fact failed once of 4 runs there (one paint in 3 s after a pan, shown), and
      passed the 3 runs after: not reproduced.
    - **Not run:** the window checks in front of the user's windows other than TST-422's, and `undo`: a full run.
  - Questioned by TST-433, SRV-156, SRV-157, SRV-160 and TST-441 (2026-11-15).
  - Questioned by SRV-165 (2026-11-16).
- [x] **TST-422 · The covered-during-shot check passes whatever becomes of the order after the shot** · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_a_window_covered_during_a_3d_shot_is_put_in_front_again`), `window_states.py` (`_CLEAR`) · confirmed · found 2026-11-15
  - **Defect.** The docstring says Designer's window "goes back behind that window after". That half no longer tests
    anything. `_CLEAR` now leaves Designer hidden (on main it ended with `mac.unhide()`), and the check puts nothing on
    screen before `during_pan(path, 'cover')`. So the shot starts from a hidden Designer and hides it again at its
    end. `_MacWindow.covered()` is True for a hidden Designer, so `read(showing('covered=True'))` and
    `state.get('covered') == 'True'` hold whatever order the windows were left in.
  - **Scenario.** Read in the code (2026-11-15). A shot that leaves Designer's window in front of the cover, or behind
    every window, passes as long as it hides Designer at its end. Only the "in front again" half (`AGAIN`) is still
    judged. The put-back behind a user's window is what keeps Designer off the user's screen.
  - **Fix.** Set the check up on screen first (`put('on screen')`; it runs in the in-front block already). Then judge
    `hidden=False` and the cover in front of Designer's main window, read with `read(in_order([('cover', 'main')]))`.
  - **Resolution: done.**
    - **Test:** the check itself, rewritten. In its scratch run, with the shot's `mac.put_below(behind)` removed from
      the helpers, it failed: `order=main,cover` after the shot. `test_the_covered_during_a_shot_check_starts_on_screen_and_reads_the_order_after`
      pins its set-up.
    - **Cause:** `clear()` leaves Designer hidden, so the shot began hidden and hid Designer again, and a hidden
      Designer reads `covered=True` whatever the order.
    - **Fix:** the check puts Designer on screen first (`put('on screen')`), then reads the state once the cover is in
      front of Designer's main window (`read(in_order([('cover', 'main')]))`), and judges `hidden=False` and that order.
    - **Result:** in its scratch run (Designer in front of the user's windows for a few seconds, with their go), it
      passed: the plane moved 0.249 of the view, Designer put back behind the cover.
  - Questioned by TST-438 (2026-11-15).
- [x] **TST-433 · A covered window didn't draw in a Designer launch_designer opened, so the drawing fact fails there, and four checks lost their guard on its account** · follows SRV-152, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_the_3d_view_isnt_drawn_while_designers_window_is_off_screen`, `check_a_3d_shot_keeps_designers_window_transparent_and_click_through_while_off_screen`, `check_a_render_that_didnt_follow_a_pan_is_said`, `check_a_plain_3d_shot_shows_a_change_made_while_designers_window_was_off_screen`, `check_a_3d_shot_puts_designers_window_on_screen_without_taking_focus`), `mcp_server/designer_helpers/shot3d.py` (the module docstring, `_wait_on_screen`) · measured · found 2026-11-15
  - **Defect.** SRV-152's resolution recorded that in a Designer `open` starts, a covered window stays exposed for
    Qt and its 3D view draws. The drawing fact now expects that: `still = [way for way in off_screen if way !=
    'covered']`, so a covered render that a pan leaves unchanged fails it. On that account, four checks no longer
    judge whether a covered window was brought on screen:
    - the transparent-at-each-render check reads only opacity and click-through;
    - the stale-render check minimizes the window instead;
    - the plain-shot check's covered case can't tell a shot that brought the window on screen from one that didn't;
    - the focus check's plane movement can't either.
    shot3d.py's docstrings and the checks' docstrings state the fact.
  - **Scenario.** Measured in a Designer launch_designer opened (`open -n -g -j`, alone's fresh server, 2026-11-15):
    - the drawing fact's covered way (`window_states.panned('covered')`), 3 times: `SAME=True`, with
      `covered=True exposed=False`, as for the minimized way;
    - the covered way brought on screen by `_on_screen`, 3 times: `exposed=False` before it.
    So the drawing fact fails there. SRV-152's scratch run passed with covered windows drawn, so both states occur
    in Designers opened hidden, and what decides it is unknown. Where covered windows draw, a shot that stopped
    bringing a covered window in front passes every check.
  - **Fix.** Measure what decides a covered window's exposure. Until then:
    - the drawing fact says which state it saw for the covered way and doesn't judge it;
    - the covered cases judge what doesn't depend on drawing: Designer's main window ahead of the cover at each
      render (`ahead(order, 'main', 'cover')`, an order that changes with the window), and `hidden=False` and
      `minimized=False` for the other ways;
    - the docstrings say both states were seen.
  - **Resolution: done.**
    - **Measured first** (2026-11-16), in a Designer launch_designer opened hidden (alone, port 9877): the covered way
      set up, the time macOS said covered and Qt's expose events logged, then the pan, 6 tries, 3 of them waiting up to
      3 s for Qt to stop exposing the window. In each, the render followed the pan with `exposed=True`, still so 3 s
      after `covered=True` in the 3 that waited; no expose event came after the cover. The review's Designer saw the
      opposite, 6 of 6. So the state held per Designer, and what decides it wasn't found.
    - **Test:** `check_a_3d_shot_keeps_designers_window_transparent_and_click_through_while_off_screen` judges where the
      window is at each render (`BROUGHT_ON_SCREEN`: Designer's main window ahead of its cover, `minimized=False`,
      `hidden=False`). In its scratch run, with the shot's `show()` and `unhide()` made to do nothing, the covered case
      failed: 2 renders, none brought on screen, while opacity and click-through held, which the old judgement passed.
    - **Cause:** SRV-152's fix took one Designer's covered state for every Designer `open` starts, and four checks
      dropped their guard on it.
    - **Fix:** the drawing fact says the covered way's state ("covered: drawn, Qt keeping the window exposed", or "not
      drawn") and doesn't judge it. The focus check's and the plain shot's docstrings say their covered case can't tell,
      and name the check that judges it. shot3d.py's module docstring and `_wait_on_screen`'s, and window_states'
      comments, say both states were seen; the shot's covered line says "may not be drawn".
    - **Also covered:** the stale-render check uses the minimized way already; its docstring now says so (TST-442).
    - **Result:** in the scratch run, the drawing fact passed (covered: drawn); the transparent-at-each-render check
      passed its 3 ways, 2 of 2 renders on screen each; the focus check and the plain shot passed their 3 ways.
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
  - Note (2026-11-16): open again. The branch's final check after the seventh review failed here, 768 of 769 live
    checks passing. launch_designer's sample showed the main thread at
    `f2d_flush_rpc < FSEventStreamFlushSync < QFseventsFileSystemWatcherEngine::addPaths < QFileSystemWatcher::addPaths
    < QFileSystemWatcher::addPath < QObject::event`, a third step before either wait. The fix had added the one more
    step seen, not the whole teardown.
  - **Resolution: done, the teardown as a whole.**
    - **Test:** `test_selftest_lifecycle.py::test_a_sample_shows_designer_anywhere_in_its_teardown[a file watcher]`
      failed first. Its fixture is that sample, which `test_the_file_watchers_sample_reads_as_the_full_run_printed_it`
      pins. The pool, the sign-in stop, a running Designer and no sample stay as cases. `lifecycle` passed whole in a
      scratch run on a port of its own, 55 checks.
    - **Measured:** a probe sampled two hidden Designers an agent started, at 1 ms, from their windows' close on, with
      the pool held. Before `destroyApplication`, main deletes the main window and exports the brush presets, about
      30 ms in all. Every slower step runs inside `destroyApplication`:
      - deleting the render engine, whose posted file-watcher event waits on macOS's file events (0.75 s and 0.01 s);
      - deleting the other components, the sign-in stop among them;
      - unloading the render back end;
      - the application's pool wait.
    - **Measured, the log:** `[INFO][Environment] Destroy Application` is the log's last line, written inside
      `destroyApplication` before the pool wait.
    - **Cause:** the checks listed the shutdown's steps one at a time, as full runs found them. When it is sampled
      depends on the load: launch_designer samples as soon as the bridge has closed.
    - **Fix:**
      - `lifecycle/samples.py`'s `in_shutdown` accepts the main thread anywhere in `destroyApplication`
        (`SHUTDOWN_CALL`, replacing `SHUTDOWN_WAITS`).
      - The launch_designer check waits for that log line (`TEARDOWN_LOGGED`) before ending the Designer, polled with
        a limit. Sampled then, the Designer is inside `destroyApplication` whatever the load.
      - The quit_designer check samples after its 15 s wait, as before; the tool gives it no point to wait for.
      - Both labels say "its teardown shown", and `server_tools/lifecycle.py`'s docstring says the same.
    - **Also covered:** the two checks are the only readers of a sample's stacks, as before.

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
  - Questioned by SRV-149 (2026-11-15).

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
  - Questioned by TST-419 (2026-11-15).
  - Questioned by TST-467 (2026-11-16).

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
  - Questioned by TST-464 (2026-11-16).

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

- [x] **HLP-147 · A 3D shot with `graph=` is refused when something closes the Explorer's menu before its action is picked, and the menu isn't opened again** · `mcp_server/designer_helpers/view3d.py:285-334` (`_apply_outputs`), `:236-254` (`_MenuPick.failure`) · measured · found 2026-11-15
  - **Defect.** `_apply_outputs` opens the Explorer's context menu once. The fade sees the menu at 0 ms, and the pick
    first looks at 100 ms. When the menu has closed by then, `failure()` says "closed before its action was picked"
    (HLP-146), and the shot raises. Nothing opens the menu again, so one close by something outside the shot fails
    the whole shot.
  - **Scenario.** Measured in the third of three full runs on main (2026-11-15), twice in `editor_panels_and_fit`:
    - The Light tool check's first shot was refused: "the Explorer's menu for graph mcp_selftest_view3d closed before
      its action was picked; the 3D view was already set: Plane". The check failed.
    - The transparency check's set-up shot was refused the same way. That check doesn't judge its set-up shot, and it
      passed.

    The same event failed the invisible-3d-shot branch's third final check, then said as "didn't open" (HLP-146). So
    it happened in 2 of the last 5 full runs. What closed the menu wasn't seen. Neither check holds the pool's launch
    lock, and HLP-146 names a likely cause: a change of the active app, which the pool's Designers cause as they start
    and quit. In the user's Designer, the user switching apps during those 100 ms might do the same.
  - **Fix.** Measure first what closes the menu, in a scratch run: the menu opened while another app is made active,
    and while another Designer starts. Then open the menu again when it closed before its pick, a few times, before
    refusing; the error stays when every try closed. Test: a live check closing the menu before its pick in the first
    try only (as `popups.closed_early` does in every try), and a unit test for the tries.

  - **Resolution: done.**
    - **Measured first,** in a Designer an agent started (2026-11-15). The menu's "View Outputs In 3D View" was there
      and enabled at the first look, 2 to 6 ms after the menu opened, in three menus. A menu held open for 60 s stayed
      open while another Designer an agent starts was launched (6 s) and quit (2 s) on another port, and Designer's app
      state didn't change. So what closed the menus in the full runs wasn't found. A click in the user's windows and
      another app made active weren't measured: both touch the user's focus.
    - **Test:** `editor_panels_and_fit.check_an_explorers_menu_closed_before_its_pick_is_opened_again` (new) closes the
      menu as the fade makes it transparent, in the first try only. Its scratch run failed first, the shot refused:
      "closed before its action was picked". `check_an_explorers_menu_closed_before_its_pick_is_said_so_and_gets_its_look_back`
      now closes it in every try and asks for each menu's look back: it failed first with one try. The unit tests in
      `test_view3d_helpers.py` failed first: the menu opened again when closed or never seen, but not when it had no
      action; the tries said; each window given its look back; the look picking as it fades.
    - **Cause:** the menu was opened once, and its action picked 100 ms after it opened. Anything closing it meanwhile
      refused the whole shot.
    - **Fix:** `_menu_once` opens the menu. One look makes it transparent, then picks its action, as soon as the menu
      shows, so nothing has those 100 ms. `_apply_outputs` opens it again when no menu was looked in (closed first, or
      never seen open), MENU_TRIES (3) times at most, and the error then says "in each of 3 tries". `_MenuPick.pick`
      leaves a menu closed already.
    - **Result:** in a scratch run, both checks pass: the shot taken after one close; refused after three, each menu's
      window opaque and clickable again. The other menu checks pass too.
    - **Also covered:** a menu without the action, or with it disabled, isn't opened again: that is Designer's answer,
      the same each time. A menu the guard had to close isn't either.
- [x] **TST-419 · The click fact retries only for windows in front of Designer's window, but its click-through reading reaches the window under it, and says only "another" when that isn't the cover** · follows TST-417, generation 2 · `tests/test_all_tools/editor_panels_and_fit/window_states.py:153-178` (`_HITS`), `:62-66` (`in_front_of`), `tests/test_all_tools/editor_panels_and_fit/checks.py:721-744` · measured · found 2026-11-15
  - **Defect.** `_HITS` reads three times which window a click at the middle of Designer's window would reach. With
    Designer's window click-through, the click should reach the window under it, the cover. The retry
    (`without_others_in_front`) looks only at the normal windows in front of Designer's window (`in_front_of(mac)`;
    TST-417's note). A window between Designer's window and the cover, or one at another level, changes the third
    reading unseen. `hit()` names such a window only 'another', so the failure doesn't say whose window it was.
  - **Scenario.** Measured in the third of three full runs on main (2026-11-15): `opaque=main transparent=main
    through=another`. It came on the first try, with no window found in front (the detail says no tries), while the
    check held the pool's launch lock, so no Designer of the run was starting or quitting. Runs 1 and 2 passed it.
    The log can't tell which window it was.
  - **Fix.** Name the window `hit()` finds when it is neither Designer's main window nor the cover: its owner and its
    layer (CoreGraphics' window list). Count such a window in the click-through reading as one in the way, so the
    reading is taken again, as one with a window in front is. Test: a unit test for the count, and a scratch run with
    a window brought between Designer's window and the cover in the first try only, then in every try.
  - Note (2026-11-15): a scratch run of the whole category, one Designer and no pool, timing each check, met it too:
    `opaque=main transparent=main through=another`, again on the first try. In the same run the not-drawn fact found
    another app's window in front in all three tries of its 'partly covered' and 'transparent in front' ways, and
    failed so. No other Designer ran, and the user said they were working in their own windows during the runs.

  - **Resolution: done.**
    - **Test:** `test_selftest_window_states.py::test_a_click_reading_that_reaches_neither_designers_window_nor_the_cover_names_it_and_is_taken_again`
      failed first. The live part: a scratch script put a window of Designer's own between its main window and the
      cover, in the click fact's first try, then in every try (the scratch script only, at the user's go for the
      windows in front of theirs). Before the fix, that run didn't show this failure alone. It found a window in front
      at the middle of Designer's in all three tries, the injected one there in the first only, and said "another".
    - **Cause:** the retry counted only the windows in front of Designer's window. A window between it and the cover,
      or at another level, changed the click-through reading unseen, and `hit()` named it only "another".
    - **Fix:** `hit()` counts such a window as one in the way, so the reading is taken again (`without_others_in_front`),
      and names it by its owner and layer (`who()`, from CoreGraphics' list). `tries_said` says "a window in the way".
    - **Result:** in the first try only, the fact passed in 2 tries. In every try, it failed in 3, naming the window:
      `through=another(Substance 3D Designer, layer 0)`.
- [x] **TST-420 · The window checks wait fixed times for macOS to settle, and take about 5 of a full run's 9 minutes** · `tests/test_all_tools/editor_panels_and_fit/window_states.py` (`_PUT`, `_CLEAR`, `_READ`, `to_back`, `window`, `_HITS`, `_UNDER`, `_PANNED`) · measured · found 2026-11-15
  - **Defect.** Each snippet waits a fixed time after changing a window, whatever the change: `_PUT` 2.0 s at its end,
    plus 1.0 s after placing the windows it makes, `to_back` 1.0 s, `window` 0.5 s for each window, `_CLEAR` 1.5 s,
    `_READ` 0.5 s. So each way of each window check costs about 6 to 7 s of waiting alone, over about 40 ways. A full
    run takes as long as its slowest category, and `editor_panels_and_fit` is that one, because of them.
  - **Scenario.** Measured (2026-11-15). A full run took 4 to 4.4 min before the 3D shot's window work, 6.8 min after
    its first part, and 8.5 to 9.6 min after the second. Timed one by one in a scratch run of the category (474 s),
    the window checks took 324 s; the four slowest 72, 47, 40 and 35 s. The user: "where are we going if our time to
    develop is 90% tests timing?"
  - **Fix.** Measure how long macOS and Qt take to report each state the snippets wait for (minimized, covered,
    hidden, on screen, shown again; Qt's exposure), then wait for that state, with a limit, instead of a fixed time.
    Test: a unit test that the snippets wait on a state, not a fixed time; the window checks timed before and after in
    a scratch run of those checks only.
  - **Resolution: done.**
    - **Measured first:** each state was reported within 0.04 to 0.07 s; a window un-minimized, or minimized, within
      0.63 s, macOS's animation. Qt's events say each change: an expose event on Designer's windows as macOS covers,
      hides or shows them, a window-state change as it minimizes them, and a hide or show of the 3D view's widget as
      Qt minimizes or restores the page. The 3D view's own window is exposed once Designer shows it again; moved or
      minimized before that, the change was undone. A page Qt minimized changes no flag and no window's exposure as its
      view stops drawing, which some runs saw within 0.6 s and others not at all within 3 s.
    - **Test:** `test_selftest_window_states.py::test_the_ways_wait_for_their_state_not_a_fixed_time` failed first, on
      `_PUT`'s fixed waits (1.0, 1.0, 1.0 and 2.0 s). It also asks that no margin be timed after a state (the user:
      under load a time measured idle can be too short), and that a page Qt minimized wait for the 3D view's hide
      event.
    - **Cause:** each snippet waited the longest time a change had been seen to take, whatever the change.
    - **Fix:** `until(state)` waits for the state, woken by each of Qt's events about Designer's windows (expose, show,
      hide, window state) and looking every 100 ms where none comes, with a 3 s limit in case none does. Each way waits
      for its own state: minimized or hidden and not exposed, covered and not exposed, or drawn with nothing of another
      app's in front. Shown again means the 3D view's own window exposed. A window the checks make waits until macOS
      lists it on screen before it is placed. A page Qt minimized waits for the view's hide event. At the user's
      choice, the drawing fact no longer measures that state: nothing says when its view stops drawing.
      `shot3d.py`'s docstring says so instead of its earlier claim.
    - **Result:** in a scratch run of the window checks alone, they took 234 s, 324 s before; every one passed, and the
      watch over those off screen read 0.00 s in front of another app's windows. The rest of their time is the 3D shots
      they take, two or three a case.
    - **Also covered:** `_CLEAR` waits for the window un-minimized, then hidden. The click and window-under facts keep
      their waits: they time macOS's covered state on purpose (TST-412).
  - Questioned by TST-465 (2026-11-16).

- [x] **HLP-148 · Every 3D shot waits fixed times for the 3D view to draw, most of the shot's time** · `mcp_server/designer_helpers/shot3d.py` (`DRAW_WAIT`, `_wait_on_screen`, `shoot_3d`'s retakes), `mcp_server/designer_helpers/view3d.py` (`_3d_set_up`'s steps, `VIEW_TURN`, `DRAG_PAUSE`, `WHEEL_PAUSE`) · measured · found 2026-11-15
  - **Defect.** The shot sleeps a fixed time wherever it waits for the 3D view, whatever the view does meanwhile:
    - 0.5 s once Designer's window is on screen (`DRAW_WAIT`), in every shot of a window brought on screen;
    - after a mesh 0.5 s, after a graph's outputs 1.0 s, after a view 1.0 s (`VIEW_TURN`), then 0.3 s after Frame,
      and 0.5 s at the end of every set-up;
    - 0.2 s after each drag (`DRAG_PAUSE`) and each wheel step (`WHEEL_PAUSE`);
    - 0.5 s before each retake of a render identical to the one before the set-up.
  - **Scenario.** Measured in a Designer an agent started (2026-11-15), each step of the shot timed in Designer:
    - The render itself takes 0.03 s, bringing the window on screen about 0.07 s, and putting it back 0.07 s. A plain
      shot of a hidden Designer took 0.76 s, 0.5 s of it `DRAW_WAIT`. A pan took 1.5 s, zoom=3 2.0 s, a mesh 1.9 s,
      view='Top' 2.6 s and graph= 3.4 s. Of those, 1.0, 1.3, 1.0, 1.8 and 1.5 s are fixed waits.
    - The 3D view says when it has drawn. Each frame it draws is a Paint event on its viewport. Its overlay label
      (Display > Samples, on by default) counts the frames its antialiasing accumulates: "Samples: 8" at rest. Each
      pan, orbit, wheel step, mesh, viewpoint, Frame, graph's outputs and tiling restarted the count at 1. It came back
      to 8 within 0.1 to 0.2 s, and the render then stopped changing. A paint's label shows the count before that
      paint: the first paint after a change still read 8.
    - Two things in the view are built in. The accumulation takes 8 frames, about 0.15 s. A viewpoint or Frame turns
      the camera over about 0.8 s, Designer's own transition, and the count stays at 1 until the turn ends. No setting
      for the transition was found: none in the preferences, the 3D view's menus or its renderer's settings. So the
      0.3 s after Frame, plus the 0.5 s at the end, end about where its turn does: the render was still changing by
      0.4 grey levels 0.73 s after Frame.
    - Designer shown again with nothing changed while hidden: its first three paints read 8, within 0.06 s. With a pan
      made while hidden: the second paint read 1, and the count was back at 8 after 0.32 s. Both cases waited 0.5 s.
    - The view's own pace is enough between inputs. Wheel steps sent each once the view drew a frame after the one
      before took 0.34 s for 3 and 0.48 s for 6, where 0.2 s apart takes 0.6 and 1.2 s. The renders were identical to
      those of steps sent 0.2 s apart, 2 runs of 3 cases. Two drags sent once the view restarted after the first
      (0.024 s) matched two sent 0.2 s apart too. Sent back to back, the first was lost, as `view3d.py`'s docstring
      says.
    - What the count can't say: with Display > Samples off, the label shows only "Render Time". The GPU Pathtracer
      counts on (143 samples after 6 s). The viewpoint the camera already has restarts nothing.
  - **Fix.** Wait for the view's signals instead of fixed times:
    - Watch the viewport's Paint events through the shot and read the count at each, in an event loop like TST-420's:
      woken by the events, looking every 100 ms where none comes, with a limit.
    - After the window comes on screen, and after each set-up step: wait for the count to restart, then for it to come
      back to what it was before, at most 8. The GPU Pathtracer then gets 8 samples.
    - Between drags and wheel steps: wait for the view's next frame.
    - A step with no restart, or a view showing no count, needs a rule of its own: a limit, or renders compared.
    - Test: a unit test that the shot waits on the view, not a fixed time. A designer fact for the count's restart and
      return. The 3D checks timed before and after in a scratch run.
  - **Resolution: done.** The user chose the rules for the cases with no clear signal (2026-11-15): the GPU
    Pathtracer's render taken at 8 samples, a step that restarts nothing waited for at most 1 s, and renders compared
    every 100 ms where no count shows. The user also made the rule general, in AGENTS.md: callbacks first, hunted for;
    a poll every 100 ms where none exists; never a time measured here.
    - **Test:** `test_frames3d.py::test_the_3d_shot_waits_on_the_view_not_a_fixed_time` failed first, on `shot3d.py`'s
      `_settle(DRAW_WAIT)` and `_settle(step)`. The rules' unit tests in `test_frames3d.py` failed on names not yet
      there. The live fact `check_the_3d_views_frames_say_when_it_has_drawn` failed in a scratch run with the helpers
      set aside (`_viewport` not defined). The tests of the shot and the set-up in `test_shot3d.py` and
      `test_view3d_helpers.py` now pin each wait: the view waited for once on screen, each retake after a frame, each
      step on the view.
    - **Measured while fixing:** the fact found two things the first rules missed.
      - A pan made right before Designer was shown still read 8 at the first two paints. Its restart came at the third,
        after an UpdateRequest. A show with nothing changed gives paints only, no UpdateRequest.
      - Designer hidden mid-accumulation leaves the label lower than 8: after the material check's Materials > Add, it
        read 1, 3 and 2 in three tries. The first rule took 1 for no count and compared renders inside the wait's
        slot. Each render runs Designer's events itself, so the waits nested, and one shot held the bridge until its
        120 s timeout (sampled: the main thread in a tick's render, `findChildren` and `processEvents`).
    - **Cause:** each wait slept the longest time its change had been seen to take, whatever the view did meanwhile.
    - **Fix:** `designer_helpers/frames3d.py` watches the 3D viewport through the shot (`_Frames`): each Paint event,
      the overlay's count read at it, and each UpdateRequest. `waits.py`'s `_until` waits for a state, woken by Qt's
      signals and events, looking every 100 ms otherwise, with a limit.
      - After a step: the count restarts, then reaches 8, or the view goes quiet for one poll after a frame.
      - After a viewpoint, before Frame: the count rises after its restart, so the camera's turn is over.
      - After each drag and each wheel step: the view's next frame, with none awaited off screen.
      - Once the window is on screen: a restart and its return. Otherwise, the show's paints read no restart, the
        view asked for no frame, and nothing more came for one poll.
      - With no count shown: renders compared every 100 ms, taken between polls, never in a slot.
      - Elsewhere: the window's exposure waits for Qt's expose events, the render waits for the clipboard's
        `dataChanged`, and a retake follows a frame or isn't taken. `DRAW_WAIT`, `VIEW_TURN`, `DRAG_PAUSE`,
        `WHEEL_PAUSE` and the set-up's last 0.5 s are gone.
    - **Result:** in scratch runs, all checks passed: the 12 view checks of `editor_panels_and_fit`, the new fact, and
      the 10 window checks that keep Designer off the user's screen. The view checks took 108 s, 162 s before. Each
      kind of shot through the tool, before and after: plain 0.76 to 0.46 s; pan 1.56 to 0.65 s; orbit 1.54 to 0.62
      s; zoom=3 1.99 to 0.64 s; view='Top' 2.63 to 1.34 s; graph= 3.32 to 1.15 s; mesh= 1.87 to 1.43 s; tiling= 2.15
      to between 1.37 and 2.30 s. Not run: the window checks that put a window in front of the user's (they run in
      the full suite).
    - **Also covered:** the same pattern elsewhere in the shot: the exposure poll every 0.05 s, the off-screen poll,
      and the clipboard poll. Outside the shot, the fixed waits and slow polls left are SRV-150 (the tools) and
      TST-421 (the self-test). Its direct drags keep a 0.2 s pause, as they drag while Designer is hidden, where no
      frame comes.
  - Questioned by HLP-159 (2026-11-15).

- [x] **SRV-150 · Outside the 3D shot, the tools still wait fixed times, and some of their polls look every 1 to 2 s** · `mcp_server/server_tools/layout.py` (`_reload_package_file`), `mcp_server/server_tools/lifecycle.py` (`_force_end`, `launch_designer`'s loop, `quit_designer`'s loop), `mcp_server/designer_helpers/mac_window.py` (`give_back_activation`) · confirmed · found 2026-11-15
  - **Defect.** AGENTS.md now says a wait waits for the callback that says the thing happened, polls every 100 ms
    only where none exists, and never waits a time measured here (the user, 2026-11-15). These don't:
    - `_reload_package_file` sleeps `RELOAD_SETTLE_S` (0.5 s) after the unload and again after the load, for
      Designer's event loop to tear down the old graph views;
    - `give_back_activation` waits 1.0 s after hiding Designer and 1.0 s after showing it again, whatever macOS did;
    - `_force_end` looks for the process every 1 s, `launch_designer` asks for the status every 2 s, and
      `quit_designer` looks for the process every 1 s.
  - **Scenario.** Read in the code (2026-11-15). Each launch or quit ends up to 1 or 2 s after the Designer answered
    or went, and the self-test's pool launches and quits a Designer per category.
  - **Fix.** A callback where one exists: the views' own signals, or a call that returns once Designer's event loop
    ran, for the reload; macOS's state, looked at every 100 ms, for the activation; the process's exit, for the
    quits (a kqueue process-exit event on macOS). Otherwise a poll every 100 ms. Not affected: the plugin's accept
    loop, whose sleep is a back-off after an error, not a wait for something to happen.

  - **Resolution: done.**
    - **Measured first,** in a Designer an agent started (2026-11-15). An unload's widgets, each watched for its
      destruction: 327 went within the unload's call, the other 177 before the next call started (0.06 s after), none
      in the four calls after, in three tries. A load changed nothing after its call. At a quit, Designer's process and
      its crash handler ended within the same 20 ms sample.
    - **Test:** these unit tests failed first:
      - `test_link_display.py::test_reload_is_split_in_separate_calls_with_no_pause`;
      - `test_mac_window.py::test_the_hide_and_the_show_are_waited_for_on_qts_callbacks_not_a_fixed_time`;
      - the new tests at the end of `test_lifecycle_env.py`: the status asked every POLL_S, the quit and the forced end
        waiting for the process's exit, and the exit watch on a real process (it ends, it outlives the limit, it was
        gone before);
      - `test_waits.py`: every timed wait in the tools, the plugin, the helpers and the self-test is a 100 ms poll or
        listed with its reason.
      The new designer fact `link_display.check_an_unloads_widgets_are_gone_once_the_next_call_starts` passes: 327,
      504, 504.
    - **Cause:** each wait slept a time once seen to be enough, or looked every 1 or 2 s, whatever happened meanwhile.
    - **Fix:**
      - `_reload_package_file` makes its calls with no pause between them: the bridge runs Designer's event loop
        between two calls. GUIDE.md says so.
      - `_exited` waits for a Designer's exit on macOS's kqueue process-exit event (`_exit_watch`), and looks every
        POLL_S (0.1 s) elsewhere. `quit_designer` and `_force_end` use it, FORCE_WAIT_S a limit after each signal.
      - `launch_designer` asks the status every POLL_S: nothing says when the bridge starts listening.
      - `give_back_activation` waits for Qt's applicationStateChanged after the hide, and the window's expose event
        after the show, ACTIVATION_WAIT at most.
    - **Result:** in scratch runs, link_display passes whole, and lifecycle on a port of its own passes 53 of 54. The one
      failing is SRV-152: a launch's window in front of the active app's, which fails with the old 2 s poll as well.
    - **Also covered:** the plugin's job poll every 100 ms and its accept loop's back-off stay. The fixed waits left are
      SRV-151.
  - Questioned by SRV-167 (2026-11-16).
- [x] **TST-421 · The self-test still waits fixed times outside the window checks' ways** · `tests/test_all_tools/common.py` (`HIDE`, `new_crash_dumps`, `end_own_designer`, `cancel_from_second_client`), `__main__.py`, `category_run.py` (`_cleaned`), `safeguards/checks.py`, `lifecycle/checks.py`, `editor_panels_and_fit/checks.py` (`MOVES_UNDER_ANY_TOOL`, `ADD_MATERIAL`), `renders.py` (`with_checker`), `window_states.py` (`_DRAG`, `_PANNED`) · confirmed · found 2026-11-15
  - **Defect.** The same rule as SRV-150. These sleep a fixed time where something could say when it happened:
    - `HIDE` 1.0 s after hiding; `ADD_MATERIAL` 1.0 s after the menu and 1.0 s after hiding again, its dialog named
      after 500 ms;
    - 0.5 s between a clean-up or an unload and the next call (`__main__.py`, `_cleaned`, `safeguards`);
    - `end_own_designer` 5 s after SIGTERM; `cancel_from_second_client` 2 s before cancelling; `lifecycle`'s checks
      1 to 2 s after a quit, a job started, a freeze or a modal dialog, and a status asked every 1 s;
    - `with_checker` 1.0 s between retakes; `MOVES_UNDER_ANY_TOOL` 0.2 s between its moves and 0.5 s after;
      `_DRAG` and `_PANNED` 0.2 s after their drags, then 0.5 or 0.3 s. These drag while Designer is hidden, where
      the 3D view draws no frame to wait for (HLP-148).
    - `new_crash_dumps` looks every 0.5 s.
  - **Scenario.** Read in the code (2026-11-15).
  - **Fix.** As SRV-150's. Not affected: the sleeps that are a check's subject (the bridge checks' slow jobs,
    `hold_thread_pool`, `quit_slow_shutdown`, the timer fact counting a timer's firings), and the click and
    window-under facts, which time macOS's covered state on purpose (TST-412).

  - **Resolution: done.**
    - **Measured first:** Designer hidden, drags sent back to back were lost, and each move was followed by an
      UpdateRequest (HLP-149).
    - **Test:** `test_waits.py::test_nothing_waits_a_fixed_time_but_the_waits_that_stay` failed first on every site the
      entry lists, and on four it missed: the bridge checks' waits for a long job to start and for an idle bridge,
      `window_states`' `_READ` and `_PUT` (half a second each), and `_DURING_PAN`'s. Unit tests for `with_checker`,
      `end_own_designer` and the window snippets failed first.
    - **Cause:** as SRV-150's.
    - **Fix:**
      - `HIDE` waits for Designer off screen: hidden for macOS, and its window no longer exposed for Qt (its expose
        event).
      - `ADD_MATERIAL` names the dialog as it opens, looks for the material every 100 ms, and waits for Designer off
        screen again.
      - The clean-ups' and `safeguards`' unloads go on with no pause (SRV-150's measurement).
      - `end_own_designer` waits on the server's `_exited`.
      - `cancel_from_second_client`, lifecycle's long job and the bridge's queue check look at the status every POLL_S
        until a job runs (`job_running`).
      - Lifecycle's freeze writes a file as it begins, and the check waits for that. Its modal dialog is looked for
        every POLL_S. The quit refusals wait for nothing: the server refuses before anything is sent, and the helper
        before its close's timer starts.
      - `with_checker` retakes as each shot returns, each shot waiting for the 3D view, RETAKE_S at most.
      - `MOVES_UNDER_ANY_TOOL`, `_DRAG` and `_PANNED` wait for each move to be taken (`_Frames.taken`), with no wait
        after.
      - `_DURING_PAN` waits for what its event did (`EVENT_DONE`). `read()` waits for the state its check reads
        (`showing`, `in_order`), and `_PUT` for the window exposed again.
      - The crash dumps, the launch lock and the pool look every 0.1 s.
    - **Result:** in scratch runs, 216 of 217 checks passed: editor_panels_and_fit's 3D checks and its window checks
      off the user's screen, then bridge, safeguards and link_display whole. The material check failed: its first wait
      looked at the menu inside the wait's own event loop, and the waits nested until the job's timeout, as HLP-148's
      had. It now looks between polls, and passes.
    - **Not run in a scratch run:** the window checks that put a window in front of the user's, but the click fact
      (`read()`'s conditions in `check_a_window_covered_during_a_3d_shot_is_put_in_front_again` and the in-front cases
      of the put-back check, `_PUT`'s wait for those ways). The full suite runs them.
    - **Also covered:** the waits that stay are listed in `test_waits.py` with their reasons: a check's subject, the
      click and window-under facts (TST-412), and SRV-151's.
  - Note (2026-11-15): lifecycle's changes ran whole in a scratch run too, on a port of its own: 53 of 54
    passed, the failure SRV-152's.
  - Questioned by TST-454, TST-455 and TST-457 (2026-11-16).
- [x] **HLP-149 · Off screen, the 3D shot's drags and wheel steps went back to back, and some were lost** · `mcp_server/designer_helpers/view3d.py` (`run`'s drags, `_wheel`), `mcp_server/designer_helpers/frames3d.py` (`_Frames.next_frame`) · measured · found 2026-11-15
  - **Defect.** HLP-148 made each drag and wheel step wait for the 3D view's next frame (`next_frame`), which returns
    at once off screen, where the view draws none. A window of the user's covering Designer's during a set-up of
    several drags or wheel steps sent the rest back to back. Found while addressing TST-421.
  - **Scenario.** Measured in a Designer an agent started (2026-11-15). Designer hidden, three pans back to back came
    out 25 grey levels apart on average from the same pans 0.2 s apart. A zoom of 6 steps, Designer hidden at its
    first, came out 55 grey levels from the same zoom undisturbed.
  - **Resolution: done.**
    - **Measured first:** hidden, each pan, wheel step or turn was followed by one UpdateRequest, 0.02 to 0.04 s later,
      and no paint. Moves sent each after it came out as moves 0.2 s apart, within 0.01 grey levels on average.
    - **Test:** `test_frames3d.py::test_a_move_is_taken_once_the_view_draws_on_screen_or_asks_for_a_frame_off_screen`
      and the orbit and zoom cases of `test_view3d_helpers.py::test_each_step_waits_for_the_3d_view_to_take_it` failed
      first. The live `editor_panels_and_fit.check_wheel_steps_sent_as_designers_window_goes_off_screen_are_all_taken`
      (new) failed first in its scratch run: 54.86 grey levels.
    - **Cause:** off screen, nothing was waited for between two moves.
    - **Fix:** `_Frames.taken()` waits for the view to take a move: its next frame on screen, its next UpdateRequest
      off screen, NO_RESTART at most. The set-up's drags and wheel steps use it. The frames fact re-measures the
      UpdateRequests.
    - **Result:** the live check passes, 0.00 grey levels apart.
    - **Also covered:** the self-test's own drags while Designer is hidden (TST-421). The shot's retakes keep
      `next_frame`: no move is waited for there.

- [x] **SRV-151 · Fixed waits left that no callback found yet replaces** · `mcp_server/designer_helpers/quit.py` (`quit_designer`'s `QTimer.singleShot(300, ...)`), `tests/test_all_tools/lifecycle/checks.py` (`CLOSE_WINDOWS_ONLY`), `tests/test_all_tools/crash_watch.py`, `tests/test_all_tools/workers.py` (`CRASH_WAIT_S`) · confirmed · found 2026-11-15
  - **Defect.** These still wait a measured time (AGENTS.md: callbacks first):
    - `quit_designer` closes Designer's windows 300 ms after its call returns, so the bridge can still reply.
      `CLOSE_WINDOWS_ONLY` does the same;
    - the crash-dump checks wait 10 s after a quit for a dump that may come (`CrashWatch`, `CRASH_WAIT_S`).
  - **Scenario.** Read in the code (2026-11-15); listed in `test_waits.py` as open.
  - **Fix.** A callback for each:
    - the close: the plugin telling a job its reply was sent (a plugin change, with a restart of Designer);
    - the crash dumps: Designer's crash handler ending. At a normal quit it ended within the same 20 ms sample as
      Designer (measured). After a crash it wasn't measured: a crash in an agent's Designer can open Adobe's crash
      window on the user's screen, so measuring it takes the user's go.
  - **Not included:** the plugin's 30 ms between two jobs (`WAKE_DELAY_MS`). DECISIONS.md settles it ("No job starts
    sooner than 30 ms after the one before ended", the user's choice, 2026-11-11), and its **Reopen if** doesn't hold:
    what Designer needs the moment for wasn't found. AGENTS.md's wait rule, added after it, contradicts it: the user
    decides which stands.
  - **Resolution: done.**
    - **Measured first** (2026-11-15): an agent's Designer crashed (`ctypes.string_at(0)` in a job, with the user's
      go). Its dump was in `pending/` within the second, as Adobe's crash window opened. The crashed process and its
      crash handler both ran until that window closed, then ended within 0.5 s. At a normal quit the handler ends with
      Designer (measured earlier).
    - **Test:** `test_a_jobs_after_reply_callbacks_run_on_the_main_thread_once_its_reply_is_sent`,
      `test_an_after_reply_callback_that_raises_doesnt_stop_the_others` (test_plugin.py),
      `test_the_windows_are_closed_once_the_reply_is_sent_not_after_a_time` (test_quit_helper.py), the crash watch's
      and the pool's waits (`test_crash_watch_waits_once_at_the_end_and_records_each_check`,
      `test_a_dump_may_come_while_its_designers_crash_handler_runs_and_none_is_there`,
      `test_the_wait_for_crash_dumps_lasts_while_one_may_come_looked_at_every_poll`, and more) failed.
    - **Fix:**
      - the plugin hands each job `_after_reply`; what the job gives it runs on the main thread once the reply is
        sent (`_Waker.after`). `quit_designer` and lifecycle's `CLOSE_WINDOWS_ONLY` close Designer's windows there. An
        older plugin, until Designer restarts, has none: the helper then closes 300 ms after, as before;
      - the crash dumps are waited for while a crash dump may still come (`common.dumps_may_come`): a Designer's
        crash handler still runs, its database in that Designer's home, and no new dump is there. Looked at every
        POLL_S, 10 s at most (`CrashWatch.settle`, `workers.wait_for_dumps`).
    - **Result:** `install.py` run, then lifecycle whole in a scratch run, 54 of 54; the plugin in a Designer just
      opened hands jobs `_after_reply`.
    - **Not done:** WAKE_DELAY_MS, the user's decision: the hunt for its callback (below, in the review log).
  - Questioned by PLG-43, TST-436 and TST-437 (2026-11-15).
  - Questioned by TST-466 (2026-11-16).
- [x] **HLP-150 · An abort during `_until` leaves its slot connected to the signals it was given** · follows HLP-148, generation 2 · `mcp_server/designer_helpers/waits.py:74-86` · confirmed · found 2026-11-15
  - **Defect.** `_until` connects the plain function `look` to its signals and disconnects them in its `finally`. An
    abort raised in `look` is a slot's: Qt drops it, and the plugin raises it again at the next traced line
    (`_make_tracer`). That line is the `finally`'s first, `tick.stop()`. The rest of the `finally` is skipped:
    `end.stop()` and every `signal.disconnect(look)`.
    ```python
        finally:
            tick.stop()
            end.stop()
            for signal in connected:
                signal.disconnect(look)
    ```
  - **Scenario.** Read in the code and the plugin's tracer (2026-11-15). A job cancelled while `_3d_render` waits on
    the clipboard: during `loop.exec()` the only traced Python is `look`, so the abort nearly always lands there. From
    then until Designer restarts, `look` stays connected to `clipboard.dataChanged` (screenshots.py), and runs
    `clipboard.image()` and `loop.quit()` on a dead loop at each clipboard change. The same holds for
    `applicationStateChanged` (mac_window.py). Each abort adds one more. The comment "the timers go with this frame"
    covers the timers only.
  - **Fix.** Make the slot a method of a QObject the frame alone holds, as `owner` holds the timers, so Qt drops its
    connections when that object goes. A unit test aborts in `look` and checks that no connection is left.

  - **Resolution: done.**
    - **Test:** `bridge`'s `check_a_wait_cancelled_leaves_nothing_connected`: a job waiting in `_until` on a signal of
      an object kept in `sys`, cancelled from a second client. In its scratch run it failed: `CONNECTED=1`. Unit:
      `test_a_wait_runs_no_python_in_a_slot`.
    - **Cause:** `look`, a Python function, was the slot of the signals and the tick. An abort landing in it was
      raised again at the `finally`'s first line, which skipped the disconnects.
    - **Fix:** `_until` connects every signal and both timers to the event loop's own `quit`, and looks at `state()`
      in its own frame between two runs of the loop. No Python runs in a slot, so an abort is raised in `_until`'s
      body and its `finally` runs whole. A first fix, `look` as a method of a QObject the frame holds, still failed
      (`CONNECTED=1`): after an abort the traceback keeps the frame, and so the QObject, alive.
    - **Also covered:** every `_until` of the helpers and the self-test's snippets goes through this one function.
      `window_states.py` has its own `until`, whose wake is an event filter, not a connected signal.
    - **Result:** passed in its scratch run (`CONNECTED=0`), with the 3D view checks off screen (41 of 44 passed, the
      3 others failing on TST-431's change, then passing once it was reverted), the Explorer menu checks, and
      bridge, safeguards and link_display whole (176 of 176).
  - Questioned by HLP-157 (2026-11-15).
  - Questioned by TST-455 (2026-11-16).
  - Questioned by HLP-171 (2026-11-16).
- [x] **HLP-151 · `_Frames`' "quiet" rule is a margin of one poll after the last frame** · follows HLP-148, generation 2 · `mcp_server/designer_helpers/frames3d.py` (`_Counts.settled`, `_Counts.shown`, `_Frames._quiet`) · confirmed · found 2026-11-15
  - **Defect.** `settled()` and `shown()` take "nothing drawn or asked for during TICK" as the end of an
    accumulation. That reuses the poll's interval as a measured time after a state, which AGENTS.md's wait rule
    forbids ("no margin after a state").
    ```python
    return time.monotonic() - self._last >= TICK / 1000.0
    ```
  - **Scenario.** Read in the code (2026-11-15). Where the view's frames come more than 100 ms apart (a large 3D view,
    a heavy material, several Designers sharing the GPU), the view counts as quiet between two ordinary frames.
    `settled()` then returns after the restart and one more paint, and the render is taken mid-accumulation, with
    nothing said. Not measured: timing the paints of an accumulation needs Designer drawing, on the user's screen.
  - **Fix.** Use the quiet rule only for a view no longer exposed, or find the callback that says an accumulation
    ended lower than its target (HLP-148 measured it: Designer hidden mid-accumulation).

  - **Resolution: done.**
    - **Measured first** (2026-11-15), in a Designer an agent started, shown transparent with the user's go:
      - on screen, each frame of an accumulation is an UpdateRequest then its paint, about 30 ms apart, and nothing
        comes after the last one: nothing says it ended but its count;
      - hidden, nothing changed, no UpdateRequest; a pan brings one, a viewpoint one after another while it turns;
      - shown with nothing changed: three paints reading 8, no UpdateRequest (5 of 5 shows);
      - shown after a change whose UpdateRequest came while hidden: an UpdateRequest or a restart by the second
        paint (9 of 9). A pan right before the show, its UpdateRequest not come, read 8 at three paints.
    - **Test:** `test_frames3d.py`'s rules and waits, failing before (the old signatures, and
      `test_a_show_with_nothing_changed_ends_at_its_second_paint` waiting for a third paint). The frames fact's new
      case, "shown from hidden right after a pan's UpdateRequest came", passed in its scratch run.
    - **Fix:** after a step, a label left lower ends the wait once the view is off screen (Qt's exposure), not quiet.
      Once shown, two paints with no restart and no UpdateRequest since say nothing changed. `_quiet` and its
      timestamp are gone. An accumulation ending lower on screen (a renderer setting; not measured) now waits
      SETTLE_LIMIT. frames3d.py's docstring has the measurements.
    - **Also covered:** the frames fact waits for Designer's own restart in its changed cases, as `shown()` now ends
      sooner.
  - Questioned by HLP-158 and TST-439 (2026-11-15).
- [x] **SRV-153 · The exit watch fails mypy off macOS, and two of its paths are unguarded or untested** · follows SRV-150, generation 2 · `mcp_server/server_tools/lifecycle.py` (`_ExitWatch`, `_exit_watch`, `_exited`) · confirmed · found 2026-11-15
  - **Defect.**
    - `_ExitWatch.__init__`'s annotation `'select.kqueue | None'` names a class `select` has only on BSD and macOS.
      `mypy --platform win32` (and `linux`) fails: `Name "select.kqueue" is not defined`. The unit suite's
      `test_types.py` then fails on Windows.
    - `select.kqueue()` is called before the `try`: an OSError there (no file descriptors left) escapes `_exit_watch`
      instead of falling back to the poll.
    - `_exited`'s poll counts `ceil(limit / POLL_S)` sleeps, each followed by a `pgrep`. The wait runs past `limit`
      by every `pgrep`'s time.
    - No test covers the watch timing out while `pgrep` already says the process is gone (`watch.wait(limit) or pid
      not in _designer_pids()`).
  - **Scenario.** Read in the code, and mypy run with `--platform win32` (2026-11-15).
  - **Fix.** Annotate with a name that exists on every platform (`object`, with the use behind a `sys.platform`
    check), move `select.kqueue()` into the `try`, make the poll end at a deadline, and add the missing unit test.

  - **Resolution: done.**
    - **Test:** `test_the_poll_for_a_process_ends_at_its_limit_however_long_each_look_takes` (it ended at 4.0 s for a
      limit of 1 s), `test_a_kqueue_that_cant_be_made_falls_back_to_the_poll` (the OSError escaped),
      `test_the_exit_watch_type_checks_where_kqueue_doesnt_exist` (mypy `--platform linux` named `select.kqueue`)
      failed. `test_a_watch_that_times_out_with_the_process_already_gone_says_it_ended` passed before any change:
      that branch worked, and had no test.
    - **Fix:** `_ExitWatch` takes a `_Queue`, a Protocol of the two methods it calls. `select.kqueue()` is called in
      a `try` that falls back to the poll. `_exited`'s poll ends at a deadline on `time.monotonic()`.
    - **Correction:** the entry said the annotation fails the unit suite on Windows. Main already has 18 mypy errors
      on the server with `--platform win32` (`fcntl`, `os.getuid`, `signal.SIGKILL`...) and 3 with `linux`; this one
      was added to them. Those are on main, outside this branch's diff, and not addressed here.
    - **Also covered:** `no_sleep` in `test_lifecycle_env.py` now advances a clock of the test's own, so the deadline
      ends as it would (with a no-op sleep and the real clock, the file took 155 s, now 8.5 s).
  - Questioned by SRV-159 (2026-11-15).
- [x] **TST-423 · The wheel-steps check compares a shot shrunk to 700 px with a full-size render** · follows HLP-149, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_wheel_steps_sent_as_designers_window_goes_off_screen_are_all_taken`) · confirmed · found 2026-11-15
  - **Defect.** `undisturbed` comes from the tool with `THREE_D`'s `max_size` 700, which the server applies with a
    thumbnail. `shoot_3d(PATH, ...)` saves the render at full size. `difference()` returns 255 for two sizes.
    `renders.moved_left`'s docstring already records the mismatch (TST-396).
  - **Scenario.** Read in the code (2026-11-15). The scratch run passed (0.00) because the render there was at most
    700 px. A wider 3D view, or a Retina-scaled render over 700 px, fails at "255.00 grey levels", with nothing wrong
    in the shot.
  - **Fix.** Take the undisturbed render through `shoot_3d` to a file too, or bring both to one size before comparing.

  - **Resolution: done.**
    - **Test:** the check itself, rewritten. In its scratch run, with the snippet's waits after the hide removed, it
      failed at 54.86 grey levels; `test_the_wheel_steps_check_compares_two_renders_saved_alike` pins the two renders.
    - **Fix:** the undisturbed zoom goes through `shoot_3d` to a file too, so both renders are saved alike, at full
      size.
    - **Result:** passed in its scratch run, 0.00 grey levels apart.
- [x] **TST-424 · The unload fact leaves its slots connected, and its clean-up can load a second copy** · follows SRV-150, generation 2 · `tests/test_all_tools/link_display/checks.py` (`UNLOAD_WATCHED`, `check_an_unloads_widgets_are_gone_once_the_next_call_starts`) · confirmed · found 2026-11-15
  - **Defect.**
    - The `destroyed` slots stay connected to every widget of Designer, and `sys.mcp_selftest_gone` stays, for the
      rest of the category.
    - The first call is outside the `try`. If it raises after the unload, nothing loads the package again.
    - If the unload is refused, the package is still loaded, and the `finally` loads a second copy.
    - The docstring says "none in the call after" and "none later". The assertion compares the second and third counts
      only, one call later.
  - **Scenario.** Read in the code (2026-11-15).
  - **Fix.** Disconnect the slots and delete the attribute in the last call. Move the first call into the `try`, and
    load the package again only when it isn't loaded. Narrow the docstring to what the assertion compares.

  - **Resolution: done.**
    - **Test:** `test_the_unload_fact_leaves_nothing_connected_and_loads_the_package_only_if_gone` failed. In its
      scratch run, after the fact, `sys` held neither of its attributes (`LEFT=False False`).
    - **Fix:** `GONE_DONE` disconnects the slot from each widget still there and deletes both attributes, in the
      `finally`; the first call is inside the `try`; `LOAD_IF_GONE` loads the package only when no copy of it is
      loaded. The docstring says what the assertion compares.
    - **Result:** passed in its scratch run, [327, 504, 504], and link_display whole.
- [x] **TST-425 · The material check never judges "hidden again", and its fade has no `finally`** · follows TST-421, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`ADD_MATERIAL`, `check_a_material_the_mesh_doesnt_use_doesnt_stop_tiling`) · confirmed · found 2026-11-15
  - **Defect.**
    - The snippet prints `HIDDEN AGAIN=%s`, but the check never judges it: a Designer left unhidden over the user's
      windows passes.
    - Designer's windows are made transparent and click-through before the trigger, and made opaque after the polling
      loop, with no `try`/`finally`. If `_menu_action(...)` or the loop raises, the windows stay transparent and the
      timers keep running until the next `clear()`.
  - **Scenario.** Read in the code (2026-11-15). Also measured (2026-11-15): the dialog doesn't make Designer the
    active app. A front watch around the check saw Designer active in 0 of 154 samples. So the reviewer's third point,
    the check unwatched while it may take the keyboard, is dropped.
  - **Fix.** Judge `HIDDEN AGAIN=True`. Wrap the fade, the timers and the hide in `try`/`finally`.
  - **Resolution: done.**
    - **Test:** the check, with "HIDDEN AGAIN" read as False in its scratch run: it failed. Unit:
      `test_the_material_check_judges_designer_hidden_again_and_puts_its_windows_back_in_a_finally`.
    - **Fix:** the check judges `HIDDEN AGAIN=True` on macOS. The fade, the timers and the hide are in a
      `try`/`finally`, and the windows are made opaque in the hide's own `finally`. The snippet holds the top-level
      widget while it uses its handle (TST-432).
    - **Result:** passed in its scratch run.
  - Questioned by TST-437 (2026-11-15).

- [x] **SRV-155 · `launch_designer`'s keyboard give-back raises once it has hidden Designer, leaving it hidden** · follows SRV-150, generation 2 · `mcp_server/designer_helpers/mac_window.py` (`give_back_activation`) · confirmed · found 2026-11-15
  - **Defect.** `give_back_activation` hides Designer, then takes `mw.window().windowHandle()` in one expression,
    which is deleted by the next line (TST-432's measurement). `_event_signal` raises there, before the show.
  - **Scenario.** A Designer that became the active app as it started: `launch_designer` hides it, the bridge call
    fails, and the Designer stays hidden. Read in the code with TST-432's measurement (2026-11-15); not run live:
    Designer becoming the active app takes the user's keyboard.
  - **Fix.** Hold the top-level widget while its handle is used.
  - **Resolution: done.** `test_no_window_handle_is_taken_through_a_wrapper_dropped_at_once` failed on this line
    and TST-432's, then passed; `give_back_activation`'s unit test now hands it the handle through a held top-level
    widget and checks its spy is removed.
- [x] **HLP-157 · `_until` runs on once Qt's quit has run: past its limit, until the job is aborted** · follows HLP-150, generation 3 · `mcp_server/designer_helpers/waits.py:75-76` · measured · found 2026-11-15
  - **Defect.** HLP-150's fix enters the event loop again at each wake: `while not state() and end.isActive():
    loop.exec()`. Once `QCoreApplication.exit()` has run, `QEventLoop.exec()` returns at once, processing no event,
    until the application's own loop unwinds. So no timer fires, `end` stays active, and the loop calls `state()`
    without end. Qt also removes the posted Quit events each time an event loop is entered.
  - **Scenario.** Measured in plain Python with Designer's PySide6 (2026-11-15): `QCoreApplication.exit(0)` from a
    timer 0.2 s into `_until(state, 1.0)`, whose `state()` turns true after 3 s. The wait returned at 3.00 s, after
    6.3 million calls of `state()`. A second `_until` after it, its state never true, hadn't ended after 20 s. In
    Designer: the user quits while a 3D shot waits on the clipboard, an expose event or the view's frames. Designer
    then spins on its main thread until the plugin aborts the job at its time limit. Not measured in Designer:
    whether its own quit runs `exit()` while a job waits. On main, a wait returned once its loop did.
  - **Fix.** End the wait when `loop.exec()` returns a negative value, or run
    `loop.processEvents(QEventLoop.ProcessEventsFlag.WaitForMoreEvents)` instead of entering `exec()` again. Add a
    unit test of `_until` itself, with a loop whose `exec` returns -1 (TST-428: `_until` is tested by its source text
    only).
  - **Resolution: done.**
    - **Test:** `test_a_wait_ends_once_qts_quit_has_run` (test_frames3d.py): `_until` with an event loop whose `exec()`
      returns -1 and a limit timer that never fires. It failed: "the wait ran on after the quit", past 100 looks.
    - **Cause:** HLP-150's fix enters the event loop again at each wake. After Qt's quit, `exec()` returns at once and
      no timer fires, so `end` stays active.
    - **Fix:** `_until` ends when `exec()` returns a negative value (waits.py, with its docstring).
    - **Also covered:** the self-test's own `until()` (window_states.py) ran the same loop, spinning to its clock limit:
      it ends there too. No other `exec()` loop in the helpers, the plugin or the self-test.
    - **Result:** passes. Not measured in Designer: whether its quit runs `exit()` while a job waits.
- [x] **SRV-156 · A failure after `open` started Designer is handled as a start that failed: the preferences copy is dropped, and the Designer is left running unrecorded** · follows SRV-152, generation 2 · `mcp_server/server_tools/lifecycle.py` (`_opened`, `_started`, `_start_designer`), `designer_preferences.py` (`saved`) · confirmed · found 2026-11-15
  - **Defect.** `_opened` can raise after `open` exited 0, with Designer already starting:
    - `_found_launched` times out;
    - `_designer_pids()` raises `_NoListing` in its loop;
    - `ps` raises OSError.
    `_start_designer` turns each into `_NotStarted`, and `saved()` drops the fresh copy of the preferences plist ("the
    start failed: no Designer started on it"). The Designer is neither recorded nor ended.
  - **Scenario.** Read in the code (2026-11-15). Under load `ps` fails, or the process isn't listed within
    LAUNCH_FOUND_S. The agent's Designer runs with a home of its own and writes the shared plist: its
    `session.instancePID` at its start, its session keys at its quit. No copy is left to put back. The `_NoListing`
    and OSError cases also say "Designer could not be started from ...; set SD_DESIGNER_APP" while it runs. The
    unrecorded path that already exists (`_remember_started` failing) keeps the copy and tries `_force_end`.
  - **Fix.** Once `open` exited 0, handle a failure as the unrecorded path does: keep the copy, say Designer was
    opened, look once more for a new process with the port, and end it. Test it with `_found_launched` raising after
    a fake `open`.
  - **Resolution: done.**
    - **Test:** `test_a_designer_open_started_whose_process_isnt_found_keeps_the_copy_of_the_preferences`, found at a
      last look and ended, or not found. It failed: the error said only "its process wasn't found within 60 s", the copy
      was dropped, and the file wasn't put back.
    - **Cause:** `_start_designer` took any ToolError of `_started` for a start that failed, inside `saved()`, which
      drops a fresh copy when its block raises.
    - **Fix:** `_opened` raises `_OpenedUnfound` once `open` exited 0, or didn't exit (SRV-160), and the process wasn't
      found or listed, with the process one last look finds (`_launched_now`). `_start_designer` ends that one under the
      lock (`_force_end`) and raises after `saved()`'s block, so the copy is kept. launch_designer says "Designer was
      opened, but ...": its process ended (the copy put back), not ended (`kill -9`), or not found (it counts as the
      user's).
    - **Also covered:** the not-found sentence moved out of `_found_launched` into the launch's error.
    - **Result:** passes.
- [x] **SRV-161 · A Designer opened hidden that becomes the active app is shown again by give_back_activation** · `mcp_server/designer_helpers/mac_window.py` (`give_back_activation`), `mcp_server/server_tools/lifecycle.py` (`launch_designer`) · measured · found 2026-11-16
  - **Defect.** Becoming the active app unhides a hidden Designer. `give_back_activation` reads `hidden` only once
    Designer is the active app, so a Designer opened hidden reads shown then: it is hidden, then shown again, opaque, on
    the user's screen. Its "still hidden" branch never runs that way.
  - **Scenario.** Measured (2026-11-16, with the user's go) in the agent's Designer opened hidden (alone, port 9877),
    its windows transparent and click-through: `activateIgnoringOtherApps:` gave `hidden=False active=True`, its window
    on screen; hidden again after, PyCharm in front before and after. No launch was seen becoming the active app (4 of 4,
    SRV-152's), so it takes a Designer that does. It was the review's Not verified item.
  - **Fix.** launch_designer passes `started_hidden=True` for an app bundle (opened by `open -j`), and
    `give_back_activation` leaves Designer hidden then.
  - **Resolution: done.**
    - **Test:** `test_a_designer_started_hidden_that_activation_showed_is_hidden_again` failed (no such parameter);
      `test_a_designer_started_gives_the_keyboard_back_once_its_home_screen_is_closed[an app bundle, opened hidden]`
      failed: `give_back_activation()` sent.
    - **Fix:** as above; a binary in SD_DESIGNER_APP still gets `give_back_activation()`.
    - **Result:** passes; the second Designer's launch in the scratch run passed.
- [x] **TST-444 · The frames fact's part on screen fails now and then: right after the show, a pan draws one paint in 3 s** · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`FRAMES`, `check_the_3d_views_frames_say_when_it_has_drawn`) · measured · found 2026-11-16
  - **Defect.** Inside `_on_screen`, the first part read "a pan [8]; a viewpoint []" and "OFF=8": one paint after the
    pan, none after the viewpoint or Display > Samples. The parts after it, shown again, passed.
  - **Scenario.** In the scratch run of 2026-11-16, 1 of 4 runs of the check (3 of 3 passed right after), and 1 of 4 in
    SRV-152's. In the full run the check fails then. Whether it is the shot's HLP-145 (a window shown while macOS still
    counted it covered) isn't known: no state was printed.
  - **Fix.** Print the window's state (exposed, covered, hidden, order) when a change draws nothing, measure what
    happened, then wait for that state, or show the window again as `_wait_on_screen` does.
  - **Resolution: done.**
    - **Test:** the check, run in the scratch run with its state printed, passed 16 of 16 alone (10 in one Designer, 6
      in Designers just started) and 6 of 6 after the material check. Run after the window checks it ran after in the
      failing run (off screen, transparent, covered put back, focus, plain shot, stale render), it failed in 6 of 7
      tries: the part on screen in 4, a part shown from hidden in the other 2. The state read `exposed=False covered=True hidden=False`, with PyCharm's window in front of Designer's,
      the active app's (`in_front`, named by `window_owner.WHO`). Qt had exposed the window at the show, then stopped
      exposing it after the first paint.
    - **Cause:** the shot's own defect, HLP-160: brought in front before Designer's unhide took, the window went behind
      the active app's window as it took. The check pans with no look between its steps, where the shot looks again
      before each one (`_Screen.again`), so its view drew nothing more.
    - **Fix:** HLP-160's, in the shot. The check now records each time Qt stops exposing the window while it is read
      on screen (COVERS: the stretch, macOS's covered, the windows in front), and reads again, once, when that
      happened, printing it. It prints the window's state where a wait on screen ran out (STATES), the shot's lines
      with it. `who()` moved from `window_states._WINDOW` into `window_owner.WHO`, which both use.
    - **Also covered:** the parts shown from hidden (SHOWN_CHANGED, SHOWN_UNCHANGED, SHOWN_TAKEN) record covers and
      states the same way: one cover was read there too, before the fix.
    - **Result:** after HLP-160's fix, the window checks then the check, 3 times, passed 55 of 55, never read again; the
      check alone passed in each run since. The in-front window checks, which use `who()` through `_WINDOW` (`_HITS`),
      weren't run: they put Designer's windows opaque in front of the user's.
- [x] **HLP-160 · A 3D shot of a hidden Designer brings its window in front before the unhide took: the window goes behind the active app's, and the view stops drawing** · `mcp_server/designer_helpers/shot3d.py` (`_Screen._bring`) · measured · found 2026-11-16
  - **Defect.** For a hidden Designer, `_bring` called `unhideWithoutActivation`, then `orderFrontRegardless` at
    once. The unhide takes as Designer's events run. The window brought in front before that ended up behind the
    active app's window, and covered whole, Qt no longer exposed it: the 3D view drew nothing more.
  - **Scenario.** Found addressing TST-444 (2026-11-16), in the agent's Designer (alone, port 9877), with PyCharm the
    active app. A probe, 5 tries each:
    - hidden, then shown at once: PyCharm's window in front 5 of 5, the window no longer exposed 0.07 to 0.095 s
      after the unhide;
    - sent behind every window, then brought in front, with no hide: nothing in front, 5 of 5;
    - shown once macOS no longer said Designer hidden (isHidden, looked at every 100 ms): nothing in front, 5 of 5,
      each watched 3 s.
    Qt's applicationStateChanged never fired for the unhide. The shot coped through `again()`, before each step and
    render, saying "brought in front again, transparent, as another window covered it during the shot", which no
    window of the user's had done. A step's wait ending off screen in between took longer.
  - **Fix.** Wait for macOS to no longer say Designer is hidden, then bring the window in front.
  - **Resolution: done.**
    - **Test:** `test_a_hidden_designer_is_brought_in_front_once_macos_says_its_unhide_took` (a fake whose unhide
      takes as its events run) failed: brought in front before the unhide took. Live,
      `check_a_hidden_designers_window_is_brought_in_front_for_a_3d_shot_once_its_unhide_took` failed 3 of 3 in the
      scratch run, 3 runs: `(True, ['PyCharm, layer 0'], 0)`. It judges only while the active app shows a window
      (`window_server.windows_now`, `shows_a_window`, with unit tests). A "designer facts" half ran the old steps
      again beside it: a window came in front 10 of 10 times, then 0 of 2 in a later run, PyCharm still active. A fact
      that holds only in some runs can't be a check, so that half was dropped; the fact is in shot3d.py's docstring,
      measured once.
    - **Cause:** `unhideWithoutActivation` returns before the unhide is done, and the window brought in front meanwhile
      went behind the active app's window as it took.
    - **Fix:** `_Screen._wait_unhidden`, after the unhide: waits for `not mac.hidden()`, woken by the window's expose
      events and looked at every TICK ms, ON_SCREEN_WAIT at most; then `mac.show()`. The measured facts are in
      shot3d.py's module docstring.
    - **Also covered:** the other unhides. `give_back_activation` unhides and only waits for the window to be exposed:
      it brings nothing in front. The window checks' set-ups (`window_states`: `to_back`, `_PUT`'s ways in front) wait
      for the unhide before they move the window.
    - **Result:** passes: the live check 9 of 9 in that Designer and 2 of 2 in Designers just started. The touched
      unit tests pass, with lint and types.
  - Questioned by HLP-173 (2026-11-16).

- [x] **SRV-162 · A launch watching a Designer not yet recorded never looks again if that Designer turns out to be another launch's: it waits out wait_s, then names other Designers to end** · follows SRV-158, generation 4 · `mcp_server/server_tools/lifecycle.py` (`launch_designer`'s `may_have_exited`) · confirmed · found 2026-11-16
  - **Defect.** `may_have_exited` watches the exits of the Designers that may hold the port, unrecorded ones included,
    and looks them up again only once one exits. An unrecorded Designer can leave that list without exiting: another
    launch records it on its own port, or it starts listening on another port. Its exit never comes, so the loop never
    looks again. Main ran `_running_on(port)` every round.
  - **Scenario.** Read in the code. In the pool, launch A has started its Designer, which pgrep lists, but hasn't
    recorded it yet. Launch B's first `_running_on(B)`, under no lock, counts it as one that may hold B's port, so B
    starts none. If it is still unrecorded at B's first look, B watches its exit and waits wait_s (240 s). B then
    fails ("Designer is already running, but its bridge did not answer ..."), naming the other workers' Designers.
    The user's Designer starting as an agent launches does the same; main refused within 2 s (`_users_next_to`). How
    often the window opens wasn't measured.
  - **Fix.** Watch the exit only of a recorded Designer. For an unrecorded one, look again each round, as main did, or
    when the records folder changes. The comment and the docstring to match.
  - **Resolution: done.**
    - **Test:** `test_a_launch_waiting_on_an_unrecorded_designer_starts_one_once_that_designer_leaves_the_port` (it
      replaces SRV-158's test of the unrecorded case). Its fakes: a Designer no record names, which never exits and
      leaves the port at the fourth look. It failed: the launch waited out wait_s and raised "Designer is already
      running, but its bridge did not answer within 30s ... `kill 22`".
    - **Cause:** SRV-158 watched an unrecorded Designer's exit and looked again only once it came. An unrecorded
      Designer can leave the port without exiting: another launch records it on its own port, or it listens on
      another. Nothing says either.
    - **Fix:** `may_have_exited` watches only the Designer another launch recorded on this port, which holds the port
      until it exits. With none recorded it returns True, so `_running_on(port)` runs each round, every POLL_S, as no
      callback exists (AGENTS.md). Its docstring says so.
    - **Also covered:** the other wait on processes, `_exited`, watches one process's exit, which is what it waits
      for. SRV-158's recorded case and its test (`..._reads_its_record_once_and_closes_its_watch`) are unchanged.
    - **Result:** passes, with the launch tests of `test_lifecycle_env.py`, lint and types.
- [x] **HLP-161 · set_3d_view's moves wait from a mark taken before the look that can bring the window back on screen, so the show's own restart ends their wait** · follows HLP-158, generation 4 · `mcp_server/designer_helpers/view3d.py` (`_3d_set_up`'s `run`, the moving block) · confirmed · found 2026-11-16
  - **Defect.** The moving block takes `since = watched.mark()`, then each option's `begin()`, which runs `between`:
    in a shot, `screen.again()` (HLP-158). If the window went off screen, `again()` brings it back and waits in
    `frames.shown()` for the view to restart and count back to 8. `settled(since)` then takes that restart and that 8
    for the moves': it ends before the moves' own count is back.
  - **Scenario.** Read in the code. `screenshot_designer('3d', orbit=[45, 0], pan=[0.2, 0])`: during the orbit's
    drags the user clicks a window of their own through Designer's click-through window, which then covers it.
    `begin('pan')` brings it in front again, the show restarts and settles, the pan restarts the count, and
    `settled(since)` returns at once. The render is taken a few samples in, noisy with the GPU Pathtracer, and nothing
    says so. A single option does the same when the window went off screen during the step before. The other steps
    take their mark after `begin()`.
  - **Fix.** Take the mark after each option's `begin()`, before its moves, and wait on the last one. Test with real
    `_Counts` and a `between` that appends a restart and a return to 8.
  - **Resolution: done.**
    - **Test:** `test_the_moves_wait_from_a_mark_taken_after_the_look_before_the_last_of_them` (orbit then pan, orbit
      then zoom, pan alone): the mark the moves' `settled()` waits from must come after the last option's look
      (`between`) and before its first move. Put back at the old place, the mark came before every look: `3 < 0` and
      `0 < 0`, 3 of 3 cases.
    - **Cause:** the moving block took one mark before the options' `begin()`. Each `begin()` runs the shot's look,
      which can bring the window back and wait for the view's restart, after that mark.
    - **Fix:** `_3d_set_up`'s moving block marks after each option's `begin()`, before its moves. `settled()` waits
      from the last option's mark.
    - **Also covered:** the other steps (mesh, graph, view, Frame, tiling) already marked after their `begin()`. The
      viewpoint's turn has a look of its own after it now (HLP-163).
    - **Result:** passes. Live, in the scratch run below (HLP-163): orbit, pan, zoom and orbit with pan all pass.
- [x] **TST-453 · Two checks that read the windows in front of Designer's run without the pool's launch lock** · follows TST-445, generation 3 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_a_hidden_designers_window_is_brought_in_front_for_a_3d_shot_once_its_unhide_took`, `check_the_3d_views_frames_say_when_it_has_drawn`) · confirmed · found 2026-11-16
  - **Defect.**
    - Both judge readings that a window of another Designer of the run can change: SHOWN_FROM_HIDDEN's
      `mac.in_front()`, and the frames fact's COVERS.
    - TST-417 found such readings failing in the full run as the pool's Designers started and quit. The four window
      checks it fixed read inside `no_designer_starting()`.
    - These two retry (TRIES, and the frames fact's "read again, once") but hold no lock. TST-445's Also covered took
      the retry half of TST-417 and left the lock out.
    - `test_the_window_checks_the_pool_disturbed_read_while_no_designer_starts` lists the four checks, not these two.
  - **Scenario.** Read in the code. In a full run, a Designer of the pool quits and macOS passes the activation to
    another, or lifecycle's hand-over check starts one from its binary (this review's Not verified). A window of it
    comes in front of Designer's while the HLP-160 check reads `in_front` three times, and the check fails as
    HLP-160's defect.
  - **Fix.** Read inside `with no_designer_starting():`, as the other four do, and add both names to the unit test's
    list. It adds no check and makes none stronger (the chain rule).
  - Note (2026-11-16): the hand-over check's two Designers were never active and showed no window, 3 of 3 under a
    front watch (the fourth review's log). What stays is the activation passed between the pool's Designers as
    they quit.
  - **Resolution: done.**
    - **Test:** `test_the_window_checks_the_pool_disturbed_read_while_no_designer_starts`, given both checks and the
      readings they take (`SHOWN_FROM_HIDDEN`, `WHO + FRAMES`): both failed, "reads windows without holding the launch
      lock".
    - **Cause:** the two checks came after TST-417, and took its retries but not its lock.
    - **Fix:** both read inside `with no_designer_starting():`, the HLP-160 check from its first reading of the windows
      to its last try. Their docstrings say so.
    - **Also covered:** the four checks the test listed already hold the lock.
    - **Result:** passes. Both checks pass in a scratch run.
  - Questioned by TST-464 (2026-11-16).
  - Questioned by TST-467 (2026-11-16).
- [x] **SRV-165 · A launch through `open` can record the user's Designer as its own, which `quit_designer` then ends** · follows SRV-152, generation 2 · `mcp_server/server_tools/lifecycle.py` (`_has_port`, `_launched_now`, `_found_launched`; their uses in `_start_designer`) · confirmed · found 2026-11-16
  - **Defect.**
    - `open` gives no process ID. The launch takes its Designer to be the newest new Designer process whose
      environment sets `SD_BRIDGE_PORT` to the launch's port:
      ```python
      for pid in sorted(set(_designer_pids()) - before, reverse=True):
          if _has_port(pid, port):
              return pid
      ```
    - Before SRV-152 the started process was the server's own child, so its ID was known.
    - README tells a user with a custom port to start Designer "from a shell where it is set, or set it
      system-wide". Their Designer's environment then sets the same variable, to the port the server uses by
      default.
    - `_appeared` looks for a Designer that appeared before the start only, not during `open` and the search.
  - **Scenario.** Read in the code. The user has `SD_BRIDGE_PORT` set system-wide, and an agent calls
    `launch_designer()`. The user opens their Designer while `open` runs, or before the agent's process is listed.
    The whole launch under the preferences lock took 0.24 to 0.25 s in this review's probe, and the search goes on
    up to LAUNCH_FOUND_S when the process is slow to show.
    - The newest matching process is the user's, so it is recorded as the agent's, with the agent's home.
    - `quit_designer` then closes it, dropping their unsaved changes, or forces it.
    - On the `_OpenedUnfound` path, `_launched_now` can pick it, and `_force_end` ends it at once.

    This breaks DECISIONS.md's "The tools never end the user's".
  - **Fix.** Match the launch's own `CFFIXED_USER_HOME=<home>` too, or its `TMPDIR`. Both are unique to the launch's
    port and user, and both go through `open --env`. If more than one new process matches, raise `_OpenedUnfound`
    rather than take one. A unit test: two new processes with the port, the newer one without the home.
  - **Resolution: done.**
    - **Test:** `test_a_designer_the_user_starts_with_the_launchs_port_isnt_taken_for_the_launchs`, through
      `_found_launched` and `_launched_now`: with the user's newer process carrying the port alone, both took it.
      `test_a_launch_is_known_by_its_port_and_its_home`, and `test_the_process_open_started_is_looked_for_with_the_launchs_port`
      expecting the home too, failed on the names missing.
    - **Cause:** the launch's process was matched by its port alone, a variable a Designer the user starts with
      SD_BRIDGE_PORT set has too.
    - **Fix:** `_launch_marks(env)` gives the launch's port and its home (`CFFIXED_USER_HOME`), and `_carries(pid,
      marks)` wants each as a whole variable of `ps -E`. `_found_launched` and `_launched_now` take the marks. The
      module docstring and `_remember_started`'s say so.
    - **Also covered:** `_launched_now`, the last look before `_OpenedUnfound`'s force, uses the same marks. A Designer
      started from its binary is the server's own child, its ID known. `_appeared` reads the Designers listening on
      the port, not environments.
    - **Result:** passes. Each scratch run since launched its Designer through `open` and found its process by both.
  - Questioned by SRV-170 (2026-11-16).
- [x] **HLP-170 · `set_3d_view` without a move fails in a Designer whose 3D view never drew, after switching the mesh** · follows HLP-162 and HLP-152, generation 3 · `mcp_server/designer_helpers/frames3d.py` (`_Frames.settled`, `_Frames._renders_alike`), `mcp_server/designer_helpers/view3d.py` (`set_3d_view` and its docstring) · measured · found 2026-11-16
  - **Defect.**
    - Without orbit, pan or zoom, `set_3d_view` runs its steps off screen (`set_up(None, None)`).
    - A view that never drew shows no count, so its `_Frames` has no `_Counts` (HLP-162). Each step's `settled()`
      then compares renders, and `_renders_alike` takes one through Copy Render at once: `last = self._render()`.
    - Off screen, a view that never drew gives no render, and `_3d_render` raises after RENDER_LIMIT.
    - The docstring says renders go through the clipboard only "With Display > Samples off" (HLP-152).
  - **Scenario.** Measured (2026-11-16) in a Designer that `launch_designer` had just opened hidden, with
    editor_panels_and_fit's preparation and no 3D shot yet. `set_3d_view(graph='mcp_selftest_view3d',
    mesh='Sphere')` printed "3D view, setting: Sphere" and switched the mesh. Then it raised "the 3D view did not
    produce a render (is a material shown?)" after 5.3 s, its one render having raised. Before this range,
    `set_3d_view` took no render. The graph and tiling steps wait with `settled()` the same way (read in the code).
    A viewpoint runs on screen, where the view draws.
  - **Fix.** Off screen with no count shown, end a step's wait on the UpdateRequest since the step, as
    `asked_off_screen` does where a count shows, with no render; or run the set-up on screen when the view hasn't
    drawn yet. Say in the docstring when renders go through the clipboard. A live check in a Designer just started,
    before any 3D shot, run where the first-shot check runs.
  - **Resolution: done.**
    - **Test:** `test_with_no_count_shown_a_step_off_screen_takes_no_render_and_ends_once_the_view_asks_for_a_frame`
      (Display > Samples off, and a view that never drew): the render raised, as in the probe. Live,
      `check_set_3d_view_sets_up_a_view_that_never_drew`, first in `run()`, failed in its scratch run: "the 3D view
      did not produce a render". Its first version put the test graph's outputs on the mesh too, and left them for
      the check of `graph=`, which then failed in the category's run; it sets the mesh alone now, and failed the same
      way against the old `_renders_alike`, put back in a copy of the file for that run only.
    - **Cause:** off screen with no count shown, each step's wait took a render first. A view that never drew gives
      none there, and off screen every render is the view's last frame anyway (HLP-163).
    - **Fix:** `_renders_alike` takes no render off screen: it waits for its `ended()`, NO_RESTART at most (the
      step's UpdateRequest; the turn's going off screen). set_3d_view's docstring and frames3d.py's say when renders
      go through the clipboard.
    - **Also covered:** `settled()` and `moved()` compare renders through `_renders_alike`; `shown()` compared only on
      screen already.
    - **Result:** passes, unit and live (96 of 96 checks in the category's scratch run, in a Designer just started).
  - Questioned by HLP-176 (2026-11-16).
  - Questioned by TST-475 (2026-11-16).
- [x] **TST-460 · The window checks' set-ups go on when a wait for Designer's window runs out, and can leave its windows opaque in front of the user's** · `tests/test_all_tools/editor_panels_and_fit/window_states.py` (`until`, `to_back`, `window`, `_PUT`, `_CLEAR`) · confirmed · found 2026-11-16
  - **Defect.**
    - `until(state, limit=3.0)` returns nothing, so no caller can tell a state that came from a limit that ran out:
      ```python
      while not state() and _time.monotonic() - start < limit:
      ```
    - `to_back` sends `orderBack:` whether or not `shown_again` came. Its own comment says a window moved before
      that "was undone". The caller's `fade(False)` then makes Designer's windows opaque.
    - `window()` places its window and makes it opaque after its own `until`, the same way.
    - `window()` registers its window in `sys.mcp_selftest_*` only when it returns. An abort or an error after
      `made.show()` leaves a window that `clear()` can't close: transparent but not click-through, so it takes the
      user's clicks.
  - **Scenario.** Read in the code. `shown_again` needs Qt to expose Designer's window. TST-433 found Designers
    where a covered window isn't exposed, and HLP-166 dropped the same wait from `give_back_activation` for that
    reason. In such a Designer, with another app's window covering Designer's whole frame at the unhide, the wait
    runs its 3 s and `orderBack:` comes before the window is shown. Designer's windows come back near the front,
    and `fade(False)` leaves them opaque in front of the user's windows until the check's clear. The fourth review
    measured the wait ending in 0.02 s with a window of the user's in front, 6 of 6, in one Designer.
  - **Fix.** `until` returns `state()`. `to_back` and `window()` raise when their wait fails, before any placing or
    opacity 1, and `window()` registers its window before `show()`. The check's clear then hides Designer, still
    transparent and click-through. A unit test for each.
  - **Resolution: done.**
    - **Test:** `test_a_set_up_whose_wait_for_designers_window_runs_out_stops_before_it_places_a_window_or_makes_one_opaque`
      failed: `until` returned nothing. `test_a_window_the_checks_make_is_registered_for_the_clear_before_it_shows`
      failed: `window()` registered nothing.
    - **Cause:** `until` dropped its state, so the set-ups went on once a limit ran out; `window()`'s callers registered
      its window once it returned.
    - **Fix:** `until` returns `state()`. `to_back`, `window()` and the 'hidden' way raise when their wait runs out,
      before placing a window or making one opaque; the check's clear then hides Designer. `window(geometry, name,
      ...)` registers its window as `sys.mcp_selftest_<name>` before it shows; `_UNDER` forgets its own once it closed
      it. `_CLEAR` makes the windows opaque only once Designer is hidden, and otherwise leaves them transparent and
      click-through, saying NOT_HIDDEN.
    - **Also covered:** `_PUT`'s last `until(reached)` and `_READ`'s are followed by the state they print, which the
      checks judge. The IN_FRONT ways' waits come before windows meant to be in front. `_DURING_PAN`'s and
      `_HIDDEN_MID_ZOOM`'s print what they saw. `_CLEAR`'s wait for the un-minimize is followed by the hide, which
      doesn't need it.
    - **Result:** passes; the window checks pass in the category's scratch run (96 of 96 checks in the category's scratch run, in a Designer just started).
  - Questioned by TST-474 (2026-11-16).
- [x] **TST-472 · The window checks' 'minimized' way makes Designer's window opaque while it flies to the Dock** · `tests/test_all_tools/editor_panels_and_fit/window_states.py` (`_PUT`, the 'minimized' way) · measured · found 2026-11-16
  - **Defect.** The way minimizes the main window, then makes Designer's windows opaque at once, while macOS's
    minimize animation still runs; `until(reached)` waits only after that:
    ```python
    if way == 'minimized':
        mac._object(mac._window, 'performMiniaturize:')
    ...
    else:
        fade(False)
    ...
    until(reached)
    ```
  - **Scenario.** Measured with the user's go (2026-11-16), in a Designer an agent started: sampled from outside
    Designer during `put('minimized')`, the window server listed Designer's main window on screen at opacity 1 from
    about 0.1 s to 0.65 s after the call began, shrinking from its frame (1599 by 993) to the Dock's icon (36 by 25),
    6 of 6. It was listed behind every other app's window at each sample, so the user sees it wherever their windows
    leave its path to the Dock uncovered. The full run sets this way up about ten times. The front watch counts only
    windows in front of another app's, so it can't see this.
  - **Fix.** For 'minimized', make the windows opaque once macOS says the window is minimized and the window server
    no longer lists it, as `_Screen.put_back` waits for the window off screen before its unfade. A unit test pins the
    order, and a live check samples the window list during the way.
  - **Resolution: done.**
    - **Test:** `test_the_minimized_way_makes_designers_windows_opaque_only_once_the_window_is_off_screen` failed: no
      wait in the way's branch. Live, `check_the_minimized_way_shows_none_of_designers_windows_as_its_window_flies_to_the_dock`
      samples the window server's list from the self-test's process (`popups.PopupWatch` at every layer, given a
      `layer`). Run against the old order, put back in a copy of the file for that run only, it failed: 961 of 1,056
      samples with a window of Designer's on screen at an opacity above 0.
    - **Cause:** the way made Designer's windows opaque right after `performMiniaturize:`, and waited for the
      minimize only after that.
    - **Fix:** the 'minimized' way waits until macOS says the window minimized and the window server no longer lists
      it, then makes the windows opaque with the other ways behind; it raises if that never comes.
    - **Also covered:** the 'hidden' way made them opaque only once hidden already; 'qt minimized' runs only in front.
    - **Result:** passes, unit and live (96 of 96 checks in the category's scratch run, in a Designer just started).
- [x] **INS-38 · `_own_folder` calls `os.getuid()`, which Windows lacks, and two unit tests reach it there** · follows INS-37, generation 2 · `scripts/read_crash_dump.py:362-370` (`_own_folder`), `tests/unit/test_read_crash_dump.py:303,349` · confirmed · found 2026-11-16
  - **Defect.**
    - INS-37's `_own_folder` compares the folder's owner with `os.getuid()`, which exists on Unix only:
      ```python
      return stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
      ```
    - Two tests that run on Windows give `dump_folders()` an agents' folder that exists, so they reach that call:
      - `test_the_dumps_are_looked_for_in_each_designers_crashpad_folders` now makes the folder (`agents.mkdir()`);
      - in `test_a_dump_waiting_for_its_upload_is_read_as_the_newest`, `_dump(...)` makes `tmp_path/agent` before
        `main([])` runs.
    - Neither is skipped on Windows. TST-349 and TST-352 made the first one pass there.
    - The script itself is safe on Windows: `agent_designer_folders()` returns `[]` where `os` has no `getuid`.
  - **Scenario.** Read in the code. The unit suite on Windows, its final check included, fails both tests with
    `AttributeError: module 'os' has no attribute 'getuid'`.
  - **Fix.** Give the two tests an `os.getuid` that returns the folder's owner
    (`monkeypatch.setattr(os, 'getuid', ..., raising=False)`), since they stand for macOS's folders, or skip them on
    win32 as INS-37's own test is.
  - **Resolution: done.**
    - **Test:** `test_the_dumps_are_looked_for_in_each_designers_crashpad_folders` and
      `test_a_dump_waiting_for_its_upload_is_read_as_the_newest` also run with `os.getuid` removed (the `user_ids`
      fixture, 'no user ids'). Both raised `AttributeError: module 'os' has no attribute 'getuid'`.
    - **Cause:** `_own_folder` called `os.getuid()`, which Windows lacks. The two tests stand for macOS's folders and
      reach that call there.
    - **Fix:** `_own_folder` compares the folder's owner only where `os` has `getuid`. Windows has no agents' folders:
      `agent_designer_folders` lists none there.
    - **Also covered:** every other `os.getuid()`. The server's `_checked_folder` runs on macOS only (its callers check
      the platform), `agent_folder_name` on POSIX, and `uninstall.py` only on what `agent_designer_folders` lists; its
      folder tests are skipped on win32.
    - **Result:** passes, with the rest of `test_read_crash_dump.py`.
  - Questioned by INS-39 (2026-11-16).
- [x] **HLP-177 · An abort landing in a `finally` skips putting back the user's parameter, a temporary node or package, and the Explorer menu's look: HLP-171's Also covered missed them** · follows HLP-171, generation 4 · `mcp_server/designer_helpers/sweep.py:66-101` (`sweep_param`), `mcp_server/designer_helpers/describe.py:255-256` (`describe_node`), `:298-300` (`_with_node_texture`), `mcp_server/designer_helpers/editor.py:360-362` (`list_atomic`), `mcp_server/designer_helpers/view3d.py:383-386` (`_menu_once`) · measured · found 2026-11-16
  - **Defect.**
    - The plugin's tracer raises its abort at a traced event, then stops tracing. Landed on a `finally`'s first line,
      the abort skips the rest of that `finally` (HLP-150, HLP-171).
    - HLP-171's Also covered says "the helpers' other put-backs of the user's state have such a handler": an outer
      handler, run untraced, that puts the state back again. These have none:
      - `sweep_param`: the swept parameter's value and its inheritance. `$outputsize` and `$format` are made Absolute
        before the `try:`, and the `finally` starts with an inner `try:`:
        ```python
        target.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
        try:
            ...
        finally:
            # the inheritance first: changing it resets the value to the default (REVIEW.md HLP-26)
            try:
                if inherit is not None:
                    target.setPropertyInheritanceMethod(prop, inherit)
            finally:  # the value goes back even if putting the inheritance back fails
                target.setPropertyValue(prop, original)
        ```
      - `_with_node_texture`: the temporary output node it adds to the user's graph
        (`if temp_output is not None: g.deleteNode(temp_output)`). It serves preview_node, node_stats and the other
        tools that read a node's pixels, and sweep_param.
      - `describe_node` and `list_atomic`: the temporary package each creates (`_PM.unloadUserPackage(tmp)`).
      - `_menu_once`: the Explorer menu's window, which `fade` held and made transparent and click-through
        (`for timer in timers: timer.stop()`, then `state.unfade()`). That window outlives the menu (HLP-146).
  - **Scenario.** Measured (2026-11-16) in plain Python, on Designer's own Python 3.13.9 and on 3.12. A probe copied
    each shape with fakes and raised an abort at each traced event in turn, as the plugin's tracer does:
    - sweep_param's shape:
      - an abort at the outer `try:` left the inheritance Absolute;
      - one at the inner `try:` left both the inheritance and the last swept value;
      - one at the inner `finally`'s first line left the value.

      Each `try:` line gives a line event.
    - `_with_node_texture`'s: an abort at either line of its `finally` left the node.
    - `_menu_once`'s: an abort at any of its `finally`'s three lines left the menu faded.

    So a sweep_param call that times out or is cancelled can leave the user's node changed, with no "restored" line.
    The tools run inside one undo step (`_with_undo`), so the user's Undo removes a value or node left this way, but
    nothing tells them to. The odds per abort are HLP-171's: the tracer looks once every 64 events.
  - **Fix.** The shape HLP-171 gave `_3d_render`: a flag set once the put-back has run, and an outer
    `except BaseException:` that does it again unless the flag says it ran. In `sweep_param`, the outer handler covers
    the lines from the inheritance change on. A unit test for each, with a trace function raising at the line, as
    HLP-171's test does.
  - **Resolution: done.**
    - **Measured first** (2026-11-16):
      - In a Designer an agent started: a package's handle differs from one listing to the next, and its UID doesn't.
        A package made through the API is listed with a UID of its own and no file, and the list is as before once it
        is unloaded. Unloading one package twice crashed that Designer: SIGSEGV in `UnreferencePackageCommand::execute`,
        a crash dump in its folder.
      - In plain Python, on 3.12 and Designer's 3.13: an abort raised at a `try:` line escapes that `try`'s handlers,
        and those of any `try` around it in the same function. A caller's handler catches it.
    - **Test:** `tests/unit/test_put_backs.py`. Its harness, `tests/unit/aborts.py`, raises the abort at every traced
      event in turn: the helper's, and those of the fakes standing for sd's Python wrappers. Qt's fakes aren't counted,
      as Qt is C++. Each test failed:
      - sweep_param left the inheritance Absolute and the value at the default;
      - `_with_node_texture` left the node;
      - describe_node and list_atomic left the package;
      - `_menu_once` left the menu open.

      Live, in their scratch run, each with an abort raised at the put-back's line by a tracer of the check's:
      - measure's `check_an_abort_putting_a_sweeps_parameter_back_still_puts_it_back` failed: Absolute after, then the
        value 0, 0;
      - measure's `check_an_abort_removing_a_measures_temporary_output_still_removes_it` failed: 4 nodes, then 5;
      - discovery's `check_an_abort_unloading_describe_nodes_package_still_unloads_it` failed: `LEFT=1`.

      `test_an_abort_at_a_try_line_escapes_the_try_around_it_but_not_one_in_a_caller` pins the Python fact.
      Discovery's `check_a_package_made_has_a_uid_of_its_own_and_no_file_and_goes_once_unloaded` pins the Designer one.
    - **Cause:** the put-backs ran in a `finally` only. An abort skips the rest of the `finally` it lands in, and
      nothing ran them again. A node or package made as the abort landed, in sd's wrapper after its C++ call, had no
      name in the helper.
    - **Fix:** each put-back runs again in an outer `except BaseException:`, which runs untraced after the abort:
      - sweep_param: `put_back()`, the inheritance then the value, with the outer `try` from the inheritance's change
        on. Set twice, they are the same.
      - `_with_node_texture`: `_delete_new_nodes(g, before)`, the nodes whose identifier wasn't listed before.
      - describe_node and list_atomic: `_unload_new_packages(before)`, the packages with no file whose UID wasn't
        listed before (`_package_uids`). Listed again each time, neither deletes or unloads anything twice.
      - `_menu_once`: the timers stopped and `unfade()` again. `unfade` sets the look first, then forgets the hold just
        before ending it: an abort between the two leaves a hold, never a second release.
      - The look: its handler covers the whole look and closes the popup open then, unless it was open before. The
        fade records its own error, so the look has no `try:` inside.
    - **Also covered:** every `finally` of the helpers.
      - Already put back by an untraced handler: `_3d_render`'s clipboard (HLP-171), `_on_screen`'s window, and
        `_3d_set_up`'s mouse button, Light tool and Parameters panel.
      - pick's `menu.close()`: an abort there now reaches the look's handler, which closes the menu.
      - Not the user's state: the event filters, held by their frames; `_Frames.close()`; `_until`'s timers (HLP-150);
        `mac_window.py`'s `CFRelease`.
      - Nested `try:` lines with a change before them in the same function, where an abort escapes the handler (the
        measurement above): the look's, removed; `_drag`'s, whose guard goes with its frame; the 3D set-up's, where
        nothing needs putting back yet. `add_node`'s and `expose_param`'s are in handlers of errors, not of aborts.
      - Left: an abort at the look's call, or at its `try:` line, comes before any of the look runs. The menu stays as
        it opened until the guard closes it, MENU_GUARD at most. `_menu_once`'s docstring says so, and the unit test
        allows it there only.
    - **Result:** passes, unit and live. In the scratch runs: measure and discovery whole, 40 of 40, and the Explorer
      menu checks in a Designer just started.
  - Questioned by HLP-179 (2026-11-16).
  - Questioned by HLP-180 (2026-11-16).
- [x] **HLP-179 · `sweep_param` stopped by an error no longer says the parameter was put back, and the tool then warns it may not be** · follows HLP-177, generation 5 · `mcp_server/designer_helpers/sweep.py:76-114` (`sweep_param`), `mcp_server/server_tools/measure.py:230-258`, `tests/unit/test_pixels.py:120-127` · confirmed · found 2026-11-16
  - **Defect.**
    - HLP-177 moved the `restored` line out of the `finally`, after the inner `try`:
      ```python
      try:  # from the inheritance's change on: ...
          try:
              ...
          finally:
              put_back()
          print('restored %s.%s to %r' % (node_id or 'graph', param, original_text))
      except BaseException:
          if not put[0]:
              put_back()
          raise
      ```
      Any exception skips the line, though the inner `finally` has put the parameter back.
    - The server reads that line to say the value was put back:
      ```python
      restored = re.search(r'^restored .*$', text, re.M)
      ...
      if not restored:
          lines.append('WARNING: the original value may not have been restored:\n' + text[-1500:])
      ```
    - No test saw it. `test_sweep_reports_a_value_that_failed` fakes the helper's old output ("'restored' from the
      finally"), and `test_put_backs.py` doesn't read what the helper prints.
  - **Scenario.** Read in the code. A sweep's later value fails: the node produces no texture, or `use` can't write
    its file. The sweep stops after the first values, with the parameter back. The result says "original NOT
    restored!" and "WARNING: the original value may not have been restored". An agent may then tell the user their
    parameter was changed, or set it again. Before HLP-177, the line came from the `finally`.
  - **Fix.** Print the line in `put_back()`, after its `try`/`finally` and before `put[0] = True`. A second run prints
    it again, and the server takes the first. A unit test of the helper: a sweep whose second value raises prints the
    line, and so does one aborted at each event (`aborts.at_each_event`). The comment in `test_pixels.py` follows.
  - **Resolution: done.**
    - **Test:** in `test_put_backs.py`, `test_a_sweep_stopped_by_an_error_says_its_parameter_is_back`, a sweep whose
      second value raises, and HLP-177's abort at each event, which now wants the line once the parameter changed: it
      failed, with the parameter back and no `restored` line.
      Live: `check_a_sweep_stopped_by_an_error_says_its_parameter_is_back` (measure) failed in its scratch run, "no
      restored line" with the parameter as before, then passed.
    - **Cause:** HLP-177 moved the line after the put-back's `try`, where any exception skipped it.
    - **Fix:** `put_back()` prints the line, after putting the parameter back and before its flag. Run again after an
      abort, it prints it again. The comment in `test_pixels.py` says where the line comes from.
    - **Also covered:** the server reads no other line a helper prints to say it put something back (`server_tools/`
      searched: `measure.py`'s alone). HLP-177's abort check passes too.
- [x] **HLP-180 · An abort in a 3D shot's put-back leaves Designer's window on screen, opaque; HLP-177's Also covered says an untraced handler puts it back** · follows HLP-177, generation 5 · `mcp_server/designer_helpers/shot3d.py:296-327` (`_Screen.put_back`), `:331-350` (`_on_screen`), `ROADMAP.md` item 91 · confirmed · found 2026-11-16
  - **Defect.**
    - HLP-177's Also covered lists "`_on_screen`'s window" as "already put back by an untraced handler". The handler
      gives the windows their look back, not their place:
      ```python
      except BaseException:
          screen.unfade()
          screen.opaque_first()
          raise
      ```
    - `put_back` runs traced once the shot ends. `mac.active()`, `mac.lowest()` and `_listed`'s loop over every window
      on screen are Python. An abort landing before a step (`mac.minimize()`, `mac.put_below(behind)`, `mac.hide()`)
      skips it. The `finally` then runs `unfade()`, untraced, which makes the window opaque where `_bring` left it.
    - An abort in `_wait_off_screen`, after `minimize()` or `hide()`, makes the window opaque before it is off
      screen. It then flies to the Dock opaque, as TST-472 measured for the self-test's way.
    - `_on_screen`'s docstring says "An abort landing on that step leaves the window on screen, opaque". ROADMAP item
      91 lists "the window sent back or hidden again after one (`shot3d.py`)" as open. It also lists sweep_param's,
      preview_node's, the clipboard's and editor.py's put-backs, which HLP-171 and HLP-177 fixed.
  - **Scenario.** Read in the code. `screenshot_designer('3d')` runs in the user's Designer, minimized, covered or
    hidden. A cancel or the job's timeout lands as the shot puts the window back. The window stays on the user's
    screen, opaque: un-minimized, in front of the window that covered it, or with Designer shown. An aborted job
    returns no line saying so.
  - **Fix.** HLP-177's shape:
    - a flag set once `put_back`'s steps have run;
    - `_on_screen`'s handler runs the steps again unless the flag is set, waits for the window off screen, then gives
      the looks back. A step run twice is safe: `miniaturize:` on a minimized window, `hide:` on a hidden app,
      `orderWindow:relativeTo:` again.

    A unit test with `aborts.at_each_event` over `_on_screen`, the Mac fake traced, checks the window's state as
    well as its look. ROADMAP item 91 then says what is left.
  - **Resolution: done.**
    - **Test:** `test_shot3d.py::test_an_abort_at_any_event_of_the_shot_leaves_the_window_where_it_was_found_and_opaque_once_there`,
      minimized, covered and hidden, an abort at every traced event: it failed at `_on_screen`'s call of put_back, the
      window left on screen. Live: `check_an_abort_putting_a_shots_window_back_still_hides_designer_again`
      (editor_panels_and_fit), an abort at put_back's `mac.hide()`, the looks given back by the check only once
      Designer is hidden: it failed in its scratch run (HIDDEN_AFTER=False), then passed.
    - **Cause:** put_back's `finally` gave the windows their look back wherever they were, and the handler did the
      same. Nothing ran the steps again.
    - **Fix:** put_back runs its steps and the wait for the window off screen (`_sent_back`), then gives the looks
      back. A step's own error gives them back at once. An abort leaves them, and `_on_screen`'s handler runs
      put_back again, untraced, unless it ran to its end (`done`). `_on_screen`'s docstring says the window is put
      back after an abort too.
    - **Also covered:** an abort in the wait off screen: the handler runs the steps and the wait again before the
      looks. ROADMAP item 91 checked: this was its last case. In the scratch run under a front watch, the shot's window
      checks off screen passed, and Designer stayed behind and not the active app (525 samples).
- [x] **HLP-181 · The text a 3D shot puts back on the clipboard stays with Designer's process until something reads it: lost when that Designer is ended by force, and a paste waits while it is busy** · `mcp_server/designer_helpers/screenshots.py:83-88` (`_3d_render`'s `put_back`); DECISIONS.md, "The 3D screenshot puts back only the clipboard's text; the rest may be lost" · measured · found 2026-11-16
  - **Defect.**
    - `put_back` gives Qt a new `QMimeData` holding the user's text: `clipboard.setMimeData(backup)`. On macOS the
      text then stays in Designer's process. Designer hands it over only when another app asks for it.
    - Every render of a shot puts it back so, several per step where no count shows (`_renders_alike`).
  - **Scenario.** Measured (2026-11-16) in Designers `launch_designer` opened hidden on port 9877. The user's
    clipboard text was saved first and put back after. A marker was copied with `pbcopy`, then:
    - after a `screenshot_designer('3d')`, a 12 s job held Designer's main thread. `pbpaste`, started 2 s into the
      job, was the first read since the shot. It returned the marker after 10.02 s, as the job ended (1 of 1). Read
      before a job instead, it came back in 0.02 s;
    - after a shot, with nothing reading the clipboard, that Designer was killed (SIGKILL). `pbpaste` returned nothing,
      0 bytes (1 of 1);
    - after a shot, a normal `quit_designer`: the marker came back (1 of 1).

    DECISIONS.md's entry rests on the text coming back. Its Reopen if, "the text is seen not to come back", holds
    for a Designer that crashes or is ended by force after a shot. `quit_designer` forces a Designer hung in its
    shutdown, as in the self-test's runs. In the user's own Designer, a paste in another app waits while an agent's
    job holds Designer's main thread.
  - **Fix.** Write the text to the pasteboard at once on macOS. AppKit can do it, called as `mac_window.py` calls it:
    `NSPasteboard.generalPasteboard`'s `clearContents`, then `setString:forType:` for each text type Qt kept. Qt's
    `setMimeData` stays elsewhere. What comes back stays the text alone, as the entry says. A live check: after a
    shot, `pbpaste` gets the marker while a job holds Designer's main thread, within a limit.
  - **Resolution: done.**
    - **Measured first** (2026-11-16, in Designers an agent started, hidden):
      - Carbon's `PasteboardResolvePromises(kPasteboardResolveAllPromises)` crashed Designer: SIGSEGV in HIServices at
        0x1f, the constant read as a pasteboard. The dump stayed in that Designer's own folder.
      - Every type of the general pasteboard read back in Designer's process right after the put-back: the paste
        during a 12 s job came in 0.013 s, and the text was there after a SIGKILL (1 of 1 each).
    - **Test:** `check_the_text_a_3d_capture_puts_back_can_be_pasted_while_designer_is_busy` (editor_panels_and_fit):
      a shot, then a job holding Designer's main thread until the check has pasted. It failed in its scratch run
      (PASTED_MEANWHILE=False: the paste came after the job), then passed. Unit:
      `test_shot3d.py::test_the_users_text_put_back_after_a_render_is_handed_to_the_pasteboard_at_once` failed with
      the call taken out of the code, and passes with it.
    - **Cause:** on macOS, Qt's `setMimeData` promises the data. Designer hands it over only when another app asks.
    - **Fix:** `_MacWindow.hand_over_clipboard` (mac_window.py) reads back every type on the general pasteboard, each
      read freed at once (an autorelease pool of its own). `_3d_render`'s put-back calls it after `setMimeData` on
      macOS, so a put-back run again after an abort does it too. The unit tests fake `_mac_window`, as the real one
      reads the machine's clipboard. The measurement is in its docstring.
    - **Also covered:** no other helper writes the clipboard. Windows wasn't measured: there, Qt also hands its data
      over on request, through OLE. DECISIONS.md's entry stands as written: the text alone comes back, now also after
      a forced end.
- [x] **INS-39 · `read_crash_dump.py` names a dump's signal from the signal table of the Python it runs on: on Windows an abort reads "signal 6", and two unit tests fail there** · follows INS-38, generation 3 · `scripts/read_crash_dump.py:200-215` (`_exception`), `tests/unit/test_read_crash_dump.py:84-87,448-450` · confirmed · found 2026-11-16
  - **Defect.**
    - `_exception` names the signal of a macOS dump with the host's `signal` module:
      ```python
      said += ', signal %s' % signal.Signals(number).name
      ```
    - Windows' C runtime numbers signals its own way: SIGABRT is 22 there. CPython builds `signal.Signals` from that
      `<signal.h>`, so 6 has no name in it. `Signals(6)` raises ValueError, and the line reads "EXC_CRASH, signal 6".
    - `test_an_abort_is_said_with_its_signal` and `test_it_runs_as_a_script` want "exception: EXC_CRASH, signal
      SIGABRT", and run on Windows. INS-38 made the crash dump tests run there, looking at `os.getuid` only.
  - **Scenario.** Read in the code. The unit suite on Windows, its final check included, fails both tests. The test
    of a crash from another exception passes only because SIGSEGV is 11 on both systems.
  - **Fix.** A table of macOS's signal names (`<sys/signal.h>`: 1 SIGHUP to 31 SIGUSR2), as `MACH_EXCEPTIONS` is
    one of Mach's, and no `signal` import. A unit test with the module's `signal` replaced by one numbering signals
    as Windows does.
  - **Resolution: done.**
    - **Test:** `test_read_crash_dump.py::test_a_dumps_signal_is_named_as_macos_numbers_it_whatever_system_reads_it`,
      the script's `signal` replaced by Windows' numbering: it failed, "signal 6" and "signal 10".
    - **Cause:** the signal of a macOS dump was named from the table of the Python reading it.
    - **Fix:** `MACOS_SIGNALS`, from `<sys/signal.h>` (all 31 alike with this Mac's `signal` module), and no `signal`
      import.
    - **Also covered:** the script reads no other host table for a dump's data: `MACH_EXCEPTIONS` is Mach's already.

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

- [x] **SRV-154 · The launch poll runs `pgrep` and `lsof` every 0.1 s on its refused path** · follows SRV-150, generation 2 · `mcp_server/server_tools/lifecycle.py` (the launch loop: `_control('status', ...)` refused, `_with_uploads_off`) · confirmed · found 2026-11-15
  - **Defect.** The launch loop now looks every POLL_S. On each refused connection, its error path runs the process
    and port lookups (`pgrep`, `lsof`) again. Before, that happened every 2 s.
  - **Scenario.** Read in the code (2026-11-15). A launch takes 4 to 5 s before the bridge listens, so about 45 rounds
    of subprocesses instead of 2 or 3.
  - **Fix.** Look up the process and the port only when the refusal says something new, or every few rounds.

  - **Resolution: done,** and *not a bug* for a launch's own start.
    - **Test:** `test_a_launch_waiting_for_another_launchs_designer_looks_it_up_once_its_process_exits` failed (6
      lookups). `test_a_launch_waiting_for_its_own_start_looks_up_no_process_between_its_polls` passed before any
      change: after its own start, the refused path looks up nothing (`running` is False).
    - **Fix:** waiting for a Designer another launch started on the port, the loop looks it up (`_running_on`) only
      once that Designer's exit watch says it exited, or none can be made (`_ExitWatch.ended`).
    - **Not run live:** the launch paths; the scratch runs used the Designer already running.
  - Questioned by SRV-158 (2026-11-15).
- [x] **TST-426 · Waits the wait rule's test doesn't see, and two that block or keep a margin** · follows SRV-150 and TST-421, generation 2 · `tests/unit/test_waits.py`, `tests/unit/test_selftest_window_server.py`, `tests/test_all_tools/common.py` (`cancel_from_second_client`), `lifecycle/checks.py` (the modal poll) · confirmed · found 2026-11-15
  - **Defect.**
    - `test_waits.py`'s regex matches only a timer started at a number literal. `timers[-1].start(after)`
      (`_menu_once`'s guard, MENU_GUARD) goes unseen, though its docstring says "every timer started at a fixed
      time". It doesn't read `tests/unit`, where `test_selftest_window_server.py` waits `time.sleep(0.3)` and
      `time.sleep(0.1)`.
    - `cancel_from_second_client` calls `job_running`, a blocking socket call, on the asyncio loop.
    - lifecycle's modal poll sleeps POLL_S after finding the dialog too: a margin after the state.
  - **Scenario.** Read in the code (2026-11-15).
  - **Fix.** Match a timer started at any argument, list the ones that stay, and narrow the docstring to what is
    matched. Wait on the watch's samples in the unit test. Run `job_running` in a thread (`asyncio.to_thread`), and break
    the modal poll before its sleep.

  - **Resolution: done.**
    - **Test:** `test_waits.py`, widened, failed on 9 waits it hadn't seen; `test_the_second_client_looks_at_the_bridge_off_the_event_loop`
      and `test_the_modal_dialog_poll_stops_once_the_dialog_is_seen` failed.
    - **Fix:** `WAIT` matches anything started with an argument but 0 (the next event loop turn) and a regex match's
      start; `tick.start(TICK)` is a poll; the waits that stay are listed: WAKE_DELAY_MS (DECISIONS.md, which AGENTS.md's
      rule contradicts, the user's to decide), `_until`'s limit, `_menu_once`'s look and guard. The window-server unit
      test waits on its samples, polled every 100 ms, and accepts samples naming no active app.
      `cancel_from_second_client` runs `job_running` in a thread. The modal poll breaks once the dialog is seen and
      sleeps with `asyncio.sleep`.
    - **Not changed:** the unit tests' own sleeps elsewhere (`test_plugin.py` and others), on main.
    - **Not run live:** lifecycle's modal check: a scratch run of lifecycle launches Designers, which come up in
      front of the user's window (SRV-152). The second client ran in bridge's checks.
  - Questioned by TST-456 (2026-11-16).
  - Questioned by TST-469 (2026-11-16).
- [x] **TST-427 · The bridge's idle probe now runs on a bridge that isn't idle** · follows TST-421, generation 2 · `tests/test_all_tools/bridge/checks.py` (`check_no_job_starts_within_the_wait_after_the_one_before`) · confirmed · found 2026-11-15
  - **Defect.** The 0.5 s before the probe is gone. The probe now reaches the bridge right after the long job's reply,
    within the plugin's WAKE_DELAY_MS, so it is started by the delayed timer, not by the wake or the poll. The check
    still says "a job started on an idle bridge".
  - **Scenario.** Read in the code and the plugin's `_drain` (2026-11-15). The main-thread result still holds, but for
    another path than the one named.
  - **Fix.** Ask `status` until the bridge says it is idle before the probe, or name the path the probe takes.

  - **Resolution: done.** The check and its docstring now say the probe is started by the plugin's wait after a job,
    and passed in bridge's scratch run.
  - Questioned by TST-440 (2026-11-15).
- [x] **HLP-152 · `set_3d_view` goes through the clipboard where no count shows, and doesn't say so** · follows HLP-148, generation 2 · `mcp_server/designer_helpers/view3d.py:617` · confirmed · found 2026-11-15
  - **Defect.** With Display > Samples off, `set_3d_view`'s own `_Frames` compares renders taken through Copy Render to
    Clipboard, up to about 40 a step. Before this branch, `set_3d_view` never touched the clipboard. DECISIONS.md's
    entry covers `screenshot_designer('3d')` only, and `set_3d_view`'s docstring doesn't say it.
  - **Fix.** Say it in `set_3d_view`'s docstring, or wait on paints alone where `set_3d_view` runs without a shot.

  - **Resolution: done.** `set_3d_view`'s docstring says that with Display > Samples off its waits take renders
    through the clipboard, and only the user's text is put back.
  - Questioned by HLP-170 (2026-11-16).
- [x] **HLP-153 · The Explorer menu's failure says the last try's reason, and "didn't open" for a menu whose fade raised** · follows HLP-147, generation 2 · `mcp_server/designer_helpers/view3d.py` (`_MenuPick.failure`, `_menu_once`'s `look`) · confirmed · found 2026-11-15
  - **Defect.**
    - "in each of %d tries" is said with the last try's reason. A first try that closed early and two that didn't
      open says "didn't open, in each of 3 tries".
    - Fade and pick run in one slot now. A fade that raises (`_MacWindow(menu)`, `hold`, `setFlag`) skips the pick. The
      menu stays open until the guard closes it, 5 s later. `failure()` then says "didn't open", hiding both the open
      menu and the guard's close.
    - `pick`'s `closed` branch is reached only when `fade` itself closes the menu, as the check's patch does. A menu
      closed by something else before the look is never seen, and is reported as "didn't open".
  - **Scenario.** Read in the code (2026-11-15).
  - **Fix.** Say "in the last of N tries", or each try's reason. Pick in a `finally` after the fade. Say "closed by the
    guard" when `held` and nothing was picked.

  - **Resolution: done.**
    - **Test:** `test_tries_failing_for_different_reasons_say_each_one`,
      `test_a_fade_that_raises_closes_the_menu_at_once_and_says_why` and
      `test_a_menu_the_guard_closed_with_nothing_picked_is_said_so` failed.
    - **Fix:** `_MenuPick.what()` says one try's reason; `failure()` says each try's when they differ ("..., then ...
      (3 tries)"). A fade that raises closes the menu at once, says why, and isn't tried again: picked from then, the
      action would run with the menu not transparent. A menu the guard closed with nothing picked says so. `pick`'s
      comment says when its closed branch is reached.
    - **Result:** the two Explorer menu checks passed in their scratch run.
- [x] **HLP-154 · Two docstrings name the wait the moves no longer use** · follows HLP-149, generation 2 · `mcp_server/designer_helpers/view3d.py` (`_drag`), `editor.py` (`_wheel`) · confirmed · found 2026-11-15
  - **Defect.** `_drag`'s docstring says `taken()` is "the 3D view's next frame: _Frames.next_frame", and `_wheel`'s
    says "the 3D view's waits for its next frame". Both are passed `_Frames.taken`, which off screen waits for an
    UpdateRequest.
  - **Fix.** Name `_Frames.taken`.

  - **Resolution: done.** `_drag`'s and `_wheel`'s docstrings name `_Frames.taken`.
- [x] **HLP-155 · Unmarked `Any` in the functions this branch adds** · `mcp_server/designer_helpers/waits.py` (`_event_signal`, `_until`), `view3d.py` (`_MenuPick.pick`, `_drag`), `editor.py` (`_wheel`) · confirmed · found 2026-11-15
  - **Defect.** Each has an `Any` without a reason on its line (AGENTS.md's typing rules):
    - `_event_signal(watched: Any, ...) -> Any`: `QtCore.QObject`, and a `Protocol` with `fired`, or marked;
    - `_until`'s `signals: Sequence[Any]`: marked as Qt's signals;
    - `pick(self, menu: Any)`, `_drag(viewport: Any, button: Any, ...)`, `_wheel(viewport: Any, ...)`: marked as Qt
      widgets, as `fade` and `_menu_once` are;
    - `_drag`'s `pressed: list[Any]`: `list[tuple[QtCore.Qt.MouseButton, float, float]]`, as its caller declares it,
      or marked.
  - **Fix.** Narrow or mark each.

  - **Resolution: done.** Each `Any` has its reason on its line: Qt objects, Qt's signals, Qt widgets and buttons.
    `pressed` stays `list[Any]`, marked: `QtCore` can't be named at def time in the helpers.
- [x] **TST-428 · Unit tests that don't evaluate what they guard** · `tests/unit/test_shot3d.py`, `test_mac_window.py`, `test_frames3d.py`, `test_selftest_window_states.py`, `test_lifecycle_env.py` · confirmed · found 2026-11-15
  - **Defect.**
    - Nothing asserts that the Expose spies are removed: dropping the `removeEventFilter` in `_wait_on_screen`,
      `_wait_off_screen` or `give_back_activation` passes.
    - `_Frames.settled`, `moved` and `shown` have no test of their wiring: the restart within NO_RESTART, then
      SETTLE_LIMIT, and no second wait when no restart came. `_until` is tested only by its source text.
    - `showing()` and `in_order()` are tested by their source text only. An inverted comparison in `in_order`'s
      condition passes.
    - Server: the branch where the watch times out but `pgrep` says the process is gone is untested (SRV-153).
  - **Fix.** Record `removeEventFilter` in the fakes and assert one per install. Add tests of `_Frames`' waits with a
    fake `_until`. Evaluate the generated conditions against fake states, in and out of order.

  - **Resolution: done.** Added, each passing on the code as it is, as guards:
    `test_each_spy_on_the_windows_expose_events_is_removed` (minimized, covered, hidden), the spy's removal in
    `give_back_activation`'s test, `_Frames`' waits (`test_a_step_waits_for_its_restart_then_for_the_count_back` and
    four more), and `in_order()` and `showing()` evaluated against fake states. The exit-watch branch is SRV-153's.
- [x] **HLP-156 · A parameter never passed, and the viewport's class name twice** · `mcp_server/designer_helpers/frames3d.py` (`_Frames._wait`, `VIEWPORT`), `view3d.py` (`_3d_set_up`) · confirmed · found 2026-11-15
  - **Defect.** `_wait`'s `woken` is never passed False. `_3d_set_up` looks up the viewport with its own literal
    `'Alg::Gui3D::ViewportWidget'` beside `frames3d.py`'s `_viewport` and `VIEWPORT`.
  - **Fix.** Drop the parameter, and use `_viewport` in `_3d_set_up`.

  - **Resolution: done.** `_wait`'s `woken` is gone; `_3d_set_up` takes its viewport from `_viewport`. Test:
    `test_one_name_for_the_3d_views_viewport_and_no_parameter_never_passed` failed before.
- [x] **TST-429 · The frames fact's waits check less than they appear to** · follows HLP-148 and HLP-149, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`FRAMES`) · confirmed · found 2026-11-15
  - **Defect.**
    - The Samples-off wait's `len(paints(read)) > 0` reads the whole list, never empty by then. The condition is
      `count() is None` alone. `read[start:]` was meant.
    - In HIDDEN_ASKS each pan's slice ends at its first UpdateRequest. A paint after the last pan's is never seen,
      so "draws none" isn't checked for it.
  - **Fix.** Use `paints(read[start:])`. After the hidden pans, check that no Paint came over the whole hidden stretch,
    up to the next call.

  - **Resolution: done.** The Samples-off wait reads the paints since its pan; `HIDDEN_PAINTS` counts every paint over
    the hidden stretch, up to the last pan's UpdateRequest, judged 0; the check's line says so. Test:
    `test_the_frames_facts_samples_off_wait_reads_the_paints_since_its_pan` failed before. The fact passed in its
    scratch run.
- [x] **TST-430 · `who()`'s ctypes calls have no return types, and the front watch's docstring says more than it samples** · `tests/test_all_tools/editor_panels_and_fit/window_states.py` (`who`), `checks.py` (`check_designer_stayed_behind`) · confirmed · found 2026-11-15
  - **Defect.** `CFStringGetCString` returns a Boolean and `CFNumberGetValue` too, but neither has a `restype`, so
    each is read as a `c_int`. The docstring says no window of Designer's "was in front". The watch samples every 50 ms
    or so, plus two `lsappinfo` runs, so a shorter flash is missed.
  - **Fix.** `restype = ctypes.c_bool` for both. "Sampled every FRONT_EVERY s or so" in the docstring.

  - **Resolution: done.** Both calls have `restype = ctypes.c_bool`; the docstring says the watch samples every
    FRONT_EVERY s or so, and what it saw. Test: `test_who_reads_the_booleans_ctypes_returns_as_booleans` failed before.
- [x] **TST-431 · `_CLEAR` overwrites the looks it has just put back** · `tests/test_all_tools/editor_panels_and_fit/window_states.py` (`_CLEAR`) · confirmed · found 2026-11-15
  - **Defect.** `_CLEAR` puts back each look `_PUT` recorded, then `fade(False)` makes every window opaque and
    clickable. The put-back only ends the holds. A window Designer kept transparent or click-through would be changed
    for every later check.
  - **Fix.** Put back the recorded looks last, or apply `fade(False)` only to windows not recorded.
  - **Resolution: not a bug.**
    - **Why not:** at rest every window is opaque and clickable (`_CLEAR`'s comment: "the window back at rest:
      Designer hidden, its windows opaque and clickable"). The looks put back first only end their holds, then
      `fade(False)` makes every window opaque.
    - **Evidence:** with the looks put back last, three window checks failed in a scratch run (the view drawn in the
      covered way, a hidden shot found covered, a render not said). Reverted, they passed.
    - **Test:** `test_clear_leaves_every_window_opaque_and_clickable_after_ending_the_holds` guards the order.
- [x] **SRV-157 · `_has_port` matches a substring, and misses the port when it is the last variable** · follows SRV-152, generation 2 · `mcp_server/server_tools/lifecycle.py` (`_has_port`) · measured · found 2026-11-15
  - **Defect.** `('SD_BRIDGE_PORT=%s ' % port) in shown + ' '`. ps's line ends with a newline, so a port printed last
    reads `SD_BRIDGE_PORT=9877\n `, which doesn't match. A variable whose name ends in `SD_BRIDGE_PORT`, or a value
    holding the text, does match.
  - **Scenario.** Measured (2026-11-15) in a Designer launch_designer opened: `SD_BRIDGE_PORT` was variable 42 of 49,
    launchd's own variables after it (`XPC_SERVICE_NAME`, `XPC_FLAGS`), and `_has_port` returned True. The output
    ended with a newline. So it holds today, as long as a variable follows the port. Both `_found_launched` tests fake
    `_has_port`, so no test reads ps's real output.
  - **Fix.** Match a whole token: `('SD_BRIDGE_PORT=%s' % port) in shown.split()`. Add a unit test on ps's format
    with the port last.
  - **Resolution: done.**
    - **Test:** `test_the_port_is_read_as_a_whole_variable_of_ps`, on ps's format: it failed for the port printed last
      and for another variable ending in `SD_BRIDGE_PORT`.
    - **Cause:** a substring with a space after it, and ps's line ends with a newline.
    - **Fix:** a whole token of `shown.split()`; the port is an int, as elsewhere (TST-443).
    - **Result:** passes; the second Designer's launch in the scratch run found its process.
- [x] **SRV-158 · The launch loop still reads another launch's record twice every POLL_S, and looks up an unrecorded Designer every round** · follows SRV-154, generation 3 · `mcp_server/server_tools/lifecycle.py` (`launch_designer`'s `may_have_exited`, `_end_if_past_startup`) · confirmed · found 2026-11-15
  - **Defect.** Each refused round runs `_end_if_past_startup`, then `may_have_exited`. Each calls `_agent_record`,
    which runs pgrep (`_designer_pids`) and ps (`_process_start`). With no record, `may_have_exited` returns True, and
    `_running_on` (pgrep, lsof) runs every round: SRV-154's pattern. The docstring says "looked up only then". The
    `_ExitWatch` objects in `watched` are never closed; garbage collection closes them.
  - **Scenario.** Read in the code (2026-11-15). Waiting 4 to 6 s for another launch's Designer to answer takes
    about 50 rounds, each with 2 pgrep and 2 ps. Waiting on a Designer no agent recorded that holds the port, such as
    the user's while it starts, `_running_on` runs every 0.1 s for up to wait_s. SRV-154's test patches
    `_agent_record` and `_still_starting` and counts only `_running_on`.
  - **Fix.**
    - Check `_still_starting` (a stat) before `_agent_record`.
    - Read the record once per round.
    - Watch an unrecorded Designer's process too, or look it up less often.
    - Close the watches in a `finally`.
    - Test the ended and no-watch branches.
  - **Resolution: done.**
    - **Test:** `test_a_launch_waiting_for_another_launchs_designer_reads_its_record_once_and_closes_its_watch` failed:
      11 reads over 5 refused rounds, no watch closed.
      `test_a_launch_waiting_on_an_unrecorded_designer_looks_it_up_once_its_process_exits` failed: `_running_on` 6
      times. `test_a_launch_waiting_for_another_launchs_designer_starts_one_once_it_exited`, watched and not, covers the
      ended and no-watch branches (TST-437).
    - **Cause:** each round read the record again, and a Designer no agent recorded had no watch.
    - **Fix:** `_end_if_past_startup` stats the record first (`_still_starting`). `may_have_exited` looks the Designers
      up only once one's exit event came or one can't be watched: the recorded one, else those `_sorted_out` says may
      hold the port. The watches are closed in a `finally`. `_still_starting` reads the file's time before the clock
      (the restarted-Designer test's clock counts calls).
    - **Result:** passes.
- [x] **SRV-159 · `quit_designer` with a negative wait_s raises ValueError after the close was sent** · follows SRV-153, generation 3 · `mcp_server/server_tools/lifecycle.py` (`_ExitWatch.wait`, `_exited`) · measured · found 2026-11-15
  - **Defect.** `_exited(own, wait_s)` passes the limit to `kqueue.control(None, 1, limit)`, which refuses a negative
    timeout. Main's poll ran no round, and the end was forced.
  - **Scenario.** Measured in plain Python (2026-11-15): `select.kqueue().control(None, 1, -1)` raised "ValueError:
    timeout must be positive or None". With `quit_designer(wait_s=-1)` on an agent's Designer, the close is sent, then
    the call fails with that error. The record stays, and the preferences put-back waits for the next call. Nothing
    validates wait_s.
  - **Fix.** Clamp the limit at 0 in `_exited`, or refuse a negative wait_s. Test `_exited(pid, -1)` with a watch.
  - **Resolution: done.**
    - **Test:** `test_a_negative_wait_for_an_exit_is_no_wait`, with a queue refusing a negative timeout as kqueue does:
      it raised "ValueError: timeout must be positive or None".
    - **Fix:** `_exited` takes a negative limit as 0, as main's poll ran no round.
    - **Result:** passes.
- [x] **SRV-160 · `_opened` waits for `open` with no limit, and drops what `open` says when it fails** · follows SRV-152, generation 2 · `mcp_server/server_tools/lifecycle.py` (`_opened`) · confirmed · found 2026-11-15
  - **Defect.** `code = opener.wait()` has no limit (AGENTS.md: every wait gets one). `stderr=quiet` sends `open`'s
    message to DEVNULL, so the error gives only the exit code.
  - **Scenario.** Read in the code (2026-11-15). A LaunchServices stall holds the port's launch lock and the
    preferences lock without end. A wrong SD_DESIGNER_APP says "`open` exited with 1" without "Unable to find
    application".
  - **Fix.** `opener.wait(timeout=...)` as a safety net, and `open`'s stderr in the error.
  - **Resolution: done.**
    - **Test:** `test_opens_failure_is_said_with_what_open_printed_and_its_wait_has_a_limit` failed: no message, no
      limit. `test_an_open_that_doesnt_exit_is_said_as_a_designer_that_may_run` failed: TimeoutExpired raised.
    - **Fix:** `open`'s stderr goes to a temporary file, said in the error; `opener.wait(timeout=OPEN_WAIT_S)`, then
      `open` is ended and the launch handled as SRV-156's.
    - **Result:** passes.
- [x] **HLP-158 · Off screen, a set-up step waits its whole NO_RESTART though the view's UpdateRequests say it took the step, and going off screen is seen only at a tick** · follows HLP-151, generation 3 · `mcp_server/designer_helpers/frames3d.py` (`_Frames.settled`, `_Frames.moved`, `_Frames._wait`, `_Counts.settled`) · measured · found 2026-11-15
  - **Defect.**
    - `settled()` and `moved()` first wait for a paint reading a restart:
      `self._wait(lambda: counts.restart(paints) is not None, NO_RESTART)`. Off screen the view draws none, so this
      wait always runs to its limit, a limit used as the wait's time (AGENTS.md). Only the moves wait for the
      off-screen callback (`taken`).
    - `settled`'s off-screen end reads `self._drawing()`, which Qt's expose events change. The wait is woken only by
      the viewport's paints and UpdateRequests, so going off screen is seen at the next TICK.
    - Gone off screen right at the paint that reads the restart, `first + 1 < len(self.seen)` never holds, and the
      wait runs SETTLE_LIMIT.
  - **Scenario.** Measured in a hidden Designer (2026-11-15):
    - a mesh switch brought an UpdateRequest 0.06 s after it, then one every 30 ms;
    - a tiling brought one 0.71 s into `set_3d_view`, which took 1.82 s.
    Off screen, each step waits 1 s, and `moved()` 1 s before Frame. The self-test's `set_3d_view` calls in a hidden
    Designer pay it. A shot pays it only when the user hides Designer during its set-up, and its render still came
    out right: shown, the view restarted by its second event (HLP-151's rule).
  - **Fix.** Off screen, end the restart wait on an UpdateRequest since the mark, as `taken` does. Wake the waits on
    the top-level window's expose events too. Off screen, accept the restart's paint alone, or say why a second paint
    is needed.
  - **Resolution: done.**
    - **Test:** `test_off_screen_a_step_ends_once_the_view_asks_for_a_frame` failed (`[False]`);
      `test_the_waits_are_woken_as_the_view_goes_off_screen` failed (no expose spy);
      `test_a_view_gone_off_screen_at_the_paint_reading_its_restart_has_settled` failed.
    - **Fix:** off screen, `settled()` ends both its waits on an UpdateRequest since the mark; the waits look again at
      the viewport window's expose events; off screen, the restart's paint alone settles, as it reads the restart's
      frame. `test_a_step_left_lower_ends_once_the_view_is_off_screen` now expects that.
    - **Then, `moved()` off screen** (the user's choice, 2026-11-16: "Show the window first"; DECISIONS.md). Hunted
      first, hidden, 2 turns: only UpdateRequests came, every 22 to 44 ms, for 0.82 and 0.84 s, then nothing, no other
      event on the viewport or its window. So `_3d_set_up`, run without the shot's watch (set_3d_view), turns the camera
      and frames inside `_on_screen`: the window shown transparent for it, then put back. The shot passes `screen.again`
      before each step, so a window gone off screen is shown again before the next one. The wait runs NO_RESTART only
      when the window goes off screen during the turn.
    - **Test:** `test_the_cameras_turn_is_watched_with_designers_window_on_screen` (set up on its own, and in a shot)
      and `test_the_set_up_is_given_the_screens_look_before_each_step` failed: no `_on_screen` around the turn,
      `screen.between` given. Live: `check_a_viewpoint_set_off_screen_is_turned_with_designers_window_on_screen`, hidden
      and minimized, failed in its scratch run ("shown: False"), then passed: shown, put back, the view 0.00 grey levels
      from view=Front.
    - **Result:** after the last change, in its scratch run, 28 of 28: the new check, the viewpoint, orbit, pan, zoom
      and tiling checks, the user's mouse in a turn, the set-up's checks, the Explorer's menu, the wheel steps, and the
      window checks off screen (focus, transparent at each render, the put-back). The material check passed in the run
      before.
  - Questioned by HLP-168 (2026-11-16).
  - Note (2026-11-16): at the user's request, DECISIONS.md's camera turn entry, which recorded this choice, was
    removed: nothing cited it, and AGENTS.md's wait rule already rules out the time limit it turned down. The choice
    stays recorded here and in `set_3d_view`'s docstring.
- [x] **HLP-159 · A step's wait takes a count the step before left low for its own restart** · follows HLP-148, generation 2 · `mcp_server/designer_helpers/frames3d.py` (`_Counts.restart`, `_Counts.moved`, `_Counts.settled`) · confirmed · found 2026-11-15
  - **Defect.** `restart()` returns the first paint since the mark that reads any count below the target. A mark
    taken mid-accumulation reads the count left over as the step's restart. That happens after `moved()` returns at
    about 2, and after a step that ended at NO_RESTART while its change was still coming. `settled` still needs the
    target after it, but `moved` needs only a count above the restart's.
  - **Scenario.** Read in the code (2026-11-15). `graph=` with a material that shows more than NO_RESTART after the
    pick, then `view=`: the graph's late restart (1, then 2) ends `moved()` while the camera turns, and Frame cancels
    the turn. The shot isn't then at the viewpoint asked for. Not measured: it needs a material slower than 1 s to
    show.
  - **Fix.** Count a restart only as a drop from the count before it, or have `mark()` wait for the view at rest.
  - **Resolution: done.**
    - **Test:** `test_a_count_left_climbing_by_the_step_before_isnt_taken_for_the_next_steps_restart` failed: the
      leftover 3 read as the restart.
    - **Fix:** a restart is a count below the target and below the count read before it (`_Counts.restart`).
    - **Also covered:** a show would then have waited SETTLE_LIMIT for an accumulation left lower and going on, which
      has no drop: `_Counts.shown` accepts it reaching the target
      (`test_a_show_after_an_accumulation_left_lower_ends_once_it_reaches_the_target`).
    - **Result:** passes; the 3D view checks passed in the scratch run.
- [x] **PLG-43 · An abort landing in an after-reply callback leaves the callbacks queued after it unrun** · follows SRV-151, generation 2 · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py` (`_Waker._on_after`) · confirmed · found 2026-11-15
  - **Defect.** `_on_after` catches `Exception` around each callback. Delivered inside another job's nested event
    loop, a callback runs under that job's tracer, which skips only the plugin's own file. That job's cancel or time
    limit then raises ScriptAborted, a BaseException, inside the callback.
  - **Scenario.** Read in the code (2026-11-15). It needs the reply's send to outlast WAKE_DELAY_MS, so that the next
    job starts first: a large output to a slow client. The callbacks after it stay in `pending` until another reply
    hands one over. The traceback the plugin prints lands in the other job's output.
  - **Fix.** Run each callback with tracing off, as `untraced` does for the hooks.
  - **Resolution: done.**
    - **Test:** `test_an_abort_of_another_job_doesnt_land_in_an_after_reply_callback`, under the plugin's own tracer
      with an abort due: `_on_after` raised ScriptAborted in the queue's `get_nowait`, before any callback ran.
    - **Fix:** `_on_after` runs with tracing off, put back as it was after.
    - **Result:** passes. install.py was run and the agent's Designer restarted; the second Designer's quit, whose close
      goes through `_after_reply`, passed in the scratch run.
- [x] **TST-434 · The HIDE check runs HIDE on a Designer that is already hidden** · follows TST-432, generation 3 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_the_self_tests_hide_hides_designer`, `run`) · confirmed · found 2026-11-15
  - **Defect.** `run()` hides Designer (`window_states.clear()`) just before the check. HIDE's `mac.hide()` then has
    nothing to do, and `HIDDEN=True` is printed whatever it does. Since SRV-152, every Designer launch_designer opens
    is hidden from its start.
  - **Scenario.** Read in the code (2026-11-15). A HIDE without its `mac.hide()` passes. Only TST-432's raise is
    caught.
  - **Fix** (generation 3: the claim made smaller). The check's name and docstring say what it judges: HIDE runs, and
    Designer is hidden after it. Measuring the hide itself needs Designer shown first, behind every window and
    transparent: the user's call.
  - **Resolution: done (generation 3: the claim made smaller).**
    - The check's name and docstring say HIDE runs and Designer is hidden after it, and that `run()` hides it just
      before, so the hide itself isn't measured. Passed in the scratch run.
- [x] **TST-435 · The cover-closed and cover-minimized cases no longer reach the path that leaves the window in front** · follows SRV-149, generation 3 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`PUT_BACK`, `PUT_BACK_IN_FRONT`, `check_a_covered_window_goes_back_behind_its_cover_or_stays_in_front_once_the_cover_is_gone`) · confirmed · found 2026-11-15
  - **Defect.** Both cases set up the 'covered' way, now behind every window (`to_back()`). The shot records every
    normal window in front of Designer's (`mac.in_front()`, any app's), the user's included. Once the cover is gone,
    `mac.lowest(self._covers)` finds a window of the user's, and the shot says BEHIND, which `STAYS` accepts. On main
    the way was in front of the user's windows: the cover was alone in front, and the cases reached GONE.
  - **Scenario.** Read in the code (2026-11-15). With any window of another app on screen, the path that leaves the
    window in front (HLP-130's) never runs, and both cases pass on BEHIND. The comment on `PUT_BACK_IN_FRONT` says
    "Designer's window left in front once its cover is gone".
  - **Fix** (generation 3: the claim made smaller). The comment and the docstring say both cases accept either.
    Reaching GONE again means setting them up 'covered in front', in front of the user's windows: the user's call.
  - **Resolution: done (generation 3: the claim made smaller).**
    - `PUT_BACK_IN_FRONT`'s comment and the check's docstring say the cover-closed and cover-minimized cases accept
      either put-back, and why.
- [x] **TST-436 · No live check guards the crash wait's match of Designer's crash handler, and a mismatch ends the wait at once** · follows SRV-151, generation 2 · `tests/test_all_tools/common.py` (`crash_handlers`, `dumps_may_come`) · measured · found 2026-11-15
  - **Defect.** `dumps_may_come` waits only while a crashpad_handler line has `--database=` and
    `/<agent folder>/home/`. A change in how the handler is started, such as another argument form or a renamed
    process, makes it return False at once, where the old wait always ran 10 s. Only unit fakes test it, with a line
    written by hand (AGENTS.md: a live check for anything that depends on Designer).
  - **Scenario.** Measured (2026-11-15) in a Designer launch_designer opened: one handler of three matched, with the
    flags `--attachment`, `--database`, `--handshake-fd`, `--metrics-dir`, `--no-rate-limit` and `--url`.
    `dumps_may_come([], <its dumps>)` was True while it ran. After its quit no handler matched, and it was False. So
    it works on this Designer. After an update that changes the command line, lifecycle's "without a crash" checks and
    the pool's quit checks would stop waiting, and a dump written 3 s after a crash would go unseen.
  - **Fix.** A live check: while the run's Designer runs, `dumps_may_come([], <the dumps there>)` is True, and False
    once it has quit.
  - **Resolution: done.**
    - **Test:** lifecycle's `check_launch_on_another_port` judges `dumps_may_come` for its second Designer while it runs
      and once it quit (polled every POLL_S, HANDLER_GONE_S at most). In its scratch run with `crash_handlers` made to
      list none, it failed ("while it ran False"); with the real one it passed (True, then False).
- [x] **TST-437 · Unit tests that pass with their fix undone** · follows SRV-151 and SRV-152, generation 2; TST-425, generation 3 · `tests/unit/test_plugin.py`, `tests/unit/test_selftest_crash_dumps.py`, `tests/unit/selftest_fakes.py`, `tests/unit/test_lifecycle_env.py`, `tests/unit/test_selftest_window_states.py` · confirmed · found 2026-11-15
  - **Defect.**
    - `test_a_jobs_after_reply_callbacks_run_on_the_main_thread_once_its_reply_is_sent`: `_FakeSignal.emit` counts and
      never delivers, so `ran == []` holds with the emit moved before `conn.sendall`.
    - The crash waits:
      - the fake `may_come` ends on any new dump, the user's folder included. The real `dumps_may_come` ends only on
        one in that Designer's home. `test_crash_watch_counts_a_dump_appearing_late` asserts that the wait ended at a
        dump in the user's folder, where the real code waits to its limit;
      - `test_crash_watch_looks_with_the_dumps_known_before_every_step` passes with the union removed
        (`before = self.steps[0].before`): its later dump is in the user's folder, which `shared` leaves out;
      - no test passes `run_port=True`;
      - the pool's fake `wait_for_dumps` (`selftest_fakes.py`) drops `before`.
    - The launch: `test_the_designer_started_is_reaped_when_it_exits` sets SD_DESIGNER_APP to a folder. The launch
      then takes `_opened`, whose `opener.wait()` sets `waited`, so the test passes with the reaping thread deleted.
      No test reaches the binary path on macOS, `open` exiting non-zero, `_started`'s wrapping of `_NoListing` and
      OSError, or the port `_opened` passes, which the conftest fake ignores. `may_have_exited`'s ended and no-watch
      branches are untested.
    - `test_the_material_check_judges_designer_hidden_again_and_puts_its_windows_back_in_a_finally`:
      `snippet.index('try:') < fade + 200` passes with the `try` up to 200 characters after the fade.
  - **Scenario.** Read in the code (2026-11-15): each change named above leaves its test passing.
  - **Fix.**
    - The after-reply test logs the send, the close and the emit, and checks their order.
    - The fake `may_come` filters by home as the real one does. Add a test of a port's old dump seen at a later step,
      and one with `run_port=True`. The pool's fake records `before`.
    - The reaping test points SD_DESIGNER_APP at a file. Add tests for the launch paths listed.
    - The material test (generation 3: the claim made smaller): drop that assertion, or word its message as what it
      checks.
  - **Resolution: done.**
    - **Test:** each test was seen failing with its fix undone, in a scratch mutation of the code, put back after: the
      after-reply order (a new test logging the send, the close and the emit, which failed with the emit moved before
      the send); the union (with `before = self.steps[0].before`); the pool's `before` (with `set()` passed); the
      reaping test (with the thread removed; SD_DESIGNER_APP now a file).
    - **Fix:** the fake `may_come` ends only on a dump in a Designer's home, and the late-dump test writes it in the
      run's; the union test's later dump is in the home of the Designer only the next step looks at; the pool's fake
      records `before`. New: `test_a_dump_may_come_from_the_runs_own_designer` (run_port=True),
      `test_a_binary_in_sd_designer_app_is_started_itself_on_macos`,
      `test_processes_that_cant_be_listed_before_open_are_said_as_no_start`,
      `test_the_process_open_started_is_looked_for_with_the_launchs_port`, `open` exiting non-zero (SRV-160's), and
      `may_have_exited`'s branches (SRV-158's). The material test (generation 3): the 200-character assertion dropped;
      it checks a `finally` after the fade.
- [x] **TST-438 · TST-422's pattern elsewhere: a covered window judged by `covered=True` without `hidden=False`** · follows TST-422, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`AFTER['covered']` in `check_a_3d_shot_puts_designers_window_on_screen_without_taking_focus`, `PUT_BACK`'s judgement) · measured · found 2026-11-15
  - **Defect.** A hidden Designer reads `covered=True` whatever the order (TST-422). The focus check judges the
    covered way's put-back by `covered=True` alone, and `PUT_BACK`'s judgement reads no `hidden`.
  - **Scenario.** Measured (2026-11-15): after `_CLEAR`, a hidden Designer's state still listed its order
    (`hidden=True ... order=main`), so NSApp's `orderedWindows` lists a hidden Designer's windows. A put-back that hid
    Designer instead of putting it behind passes the focus check's covered way. It also passes PUT_BACK's cases judged
    by `('main', 'below')` alone: ON_TOP, and the cover closed or minimized.
  - **Fix.** `showing('covered=True', 'hidden=False')`, and `state.get('hidden') == 'False'` in PUT_BACK's `ok`.
  - **Resolution: done.**
    - **Test:** the focus check's covered way reads `covered=True` and `hidden=False`; PUT_BACK's judgement reads
      `hidden=False`. In the scratch run, with the put-back made to hide Designer after putting it behind, a case judged
      by `('main', 'below')` alone failed; the real cases passed.
    - Measured along the way: a hidden Designer read `order=main,below,cover`, so the cases judged by `('cover',
      'main')` already failed such a put-back.
- [x] **TST-439 · The frames fact's TAKEN case judges neither that Designer was hidden nor that the pan's UpdateRequest came before the show** · follows HLP-151, generation 3 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`FRAMES`, `_changed_by_its_second_paint`) · confirmed · found 2026-11-15
  - **Defect.** `_changed_by_its_second_paint` doesn't require `events[0] is True` (hidden before the show), as
    `_shown` does. The result of `_until(lambda: asked_since(start), 1.0, ...)` isn't printed or judged.
  - **Scenario.** Read in the code (2026-11-15). If an earlier show left Designer up, because the user made it the
    active app, the pan draws on screen, the paints read a restart, and the fact passes. With no UpdateRequest before
    the show, the show's own makes it pass, as in the CHANGED case.
  - **Fix** (generation 3: the claim made smaller). The check's name says what it judges: once shown, an
    UpdateRequest or a restart by the second paint.
  - **Resolution: done (generation 3: the claim made smaller).**
    - The check says "shown after a pan, ..."; a comment says what isn't judged.
- [x] **TST-440 · The bridge's main-thread probe names a path it doesn't measure** · follows TST-427, generation 3 · `tests/test_all_tools/bridge/checks.py` (`check_no_job_starts_within_the_wait_after_the_one_before`) · confirmed · found 2026-11-15
  - **Defect.** The comment says the probe is "sent as the long job's reply came: the plugin's wait after a job starts
    it", and the check is named "a job started by the wait after the one before". The probe goes out after `behind`'s
    reply and `long.join()`. The plugin's wait starts it only if it arrives within WAKE_DELAY_MS; otherwise the wake
    does. The check passes either way.
  - **Scenario.** Read in the code (2026-11-15). Under the pool's load the wake starts it, and the check's line still
    claims the wait's path.
  - **Fix** (generation 3: the claim made smaller). The name and the comment say that a job queued after others runs
    on Qt's main thread.
  - **Resolution: done (generation 3: the claim made smaller).**
    - The check says "a job queued after others runs on Qt's main thread"; its comment and the docstring say which start
      runs it isn't measured.
- [x] **TST-441 · `stayed_off_screen` passes when the active app was never read** · follows SRV-152, generation 2 · `tests/test_all_tools/window_server.py` (`stayed_off_screen`) · confirmed · found 2026-11-15
  - **Defect.** `active = sum(s.active == pid for s in samples)`. A sample whose `lsappinfo` failed has
    `active=None`, which counts as not the active app. The "can't tell" guards cover only the samples and the
    windows listed.
  - **Scenario.** Read in the code (2026-11-15). With `lsappinfo` failing at every sample, lifecycle's launch check
    passes "never the active app" unmeasured.
  - **Fix.** Return False when no sample read the active app, and say so in the detail.
  - **Resolution: done.**
    - **Test:** `test_a_designer_started_hidden_shows_no_window_and_never_becomes_the_active_app[the active app never
      read]` failed (True).
    - **Also covered:** `stayed_behind`, the same pattern:
      `test_a_watch_that_cant_tell_isnt_taken_for_one_that_stayed_behind[the active app never read]` failed too.
    - **Fix:** both return False when no sample read the active app, and say how many did. The launch check passed in
      the scratch run: 69 samples, 69 reading the active app.
  - Questioned by TST-468 (2026-11-16).
- [x] **TST-442 · Docs and comments that say more than, or other than, the code and the measurements** · follows SRV-149, SRV-151 and SRV-152, generation 2 and 3 · `mcp_server/server_tools/lifecycle.py`, `README.md`, `mcp_server/designer_helpers/mac_window.py`, `shot3d.py`, `view3d.py`, the plugin's docstring, `tests/test_all_tools/` (`lifecycle/checks.py`, `window_server.py`, `common.py`, `editor_panels_and_fit/checks.py`), `tests/unit/test_selftest_window_states.py`, `tests/unit/test_frames3d.py`, `tests/unit/test_lifecycle_env.py` · confirmed · found 2026-11-15
  - **Defect.** The server and the plugin:
    - `lifecycle.py`'s module docstring says "So launch_designer starts the binary, in `/`" and that launch_designer
      "records the process it started (its own child)". `_start_designer`'s comments say "still the server's child"
      and "its own child, just started". `_remember_started` says "its own child, so no other can be taken for it".
      An app bundle is now opened by `open`: its process is launchd's child, found by its port.
    - `launch_designer`'s docstring says "on macOS the .app, whose own binary is started", and README.md's
      SD_DESIGNER_APP row "whose own binary it starts". "On macOS it starts Designer hidden" holds only for an app
      bundle: a binary in SD_DESIGNER_APP starts shown.
    - lifecycle.py's module docstring and `_opened`'s say "for up to 5 s": SRV-152 measured 5.66 s.
    - `OPENED_ENV`'s comment says "what of `env` reaches a Designer `open` starts". `_opened`'s docstring says "with
      `env`'s variables Designer reads (OPENED_ENV) on launchd's environment", and
      `test_launch_opens_a_new_instance_hidden_with_the_port`'s message "launchd's environment, with Designer's own on
      it". Measured (2026-11-15): the Designer launch_designer opened had the server's whole environment (CLAUDECODE,
      VIRTUAL_ENV, LANG, SHELL, USER, TERM, its HOME), as `man open` says ("Opened applications inherit environment
      variables"). So the `--env` flags pass nothing `env=env` doesn't.
    - `give_back_activation`'s first sentence says "Designer hidden, then shown": a Designer that was hidden is left
      hidden.
    - The plugin's docstring says a function handed to `_after_reply` runs "once the reply is sent". It also runs
      when the send failed, and one handed over after the job ended never runs.

    The helpers:
    - shot3d.py's module docstring says "The self-test's editor_panels_and_fit re-measures the first point (a window
      of Designer's own covering it)". The bullet's "the rest was measured in Designers started from their binary"
      doesn't say which facts (TST-433 for what the bullet claims).
    - view3d.py: `_MenuPick`'s docstring says "What _apply_outputs' look does"; the look is `_menu_once`'s.
      `failure()`'s says "`tries`: the menus opened"; it counts every try, those whose menu didn't open included.

    The self-test:
    - `check_launch_on_another_port`'s docstring says the Designer "never comes in front of the active app's windows
      ...: it comes up behind them, over the other apps'". The check now judges `stayed_off_screen`.
    - `window_server.py`'s module docstring says "stayed_behind reads the samples for that process", for the launch.
      `stayed_behind`'s `active_only` and `in_front_of_another`'s `over` are now passed only by unit tests, under the
      docstring's "a Designer starting comes up behind them, but over the other apps'".
    - `check_a_render_that_didnt_follow_a_pan_is_said` says "macOS only (the window covered through _MacWindow)". It
      minimizes the window.
    - HIDE's comment (`common.py`) and a section heading of `test_selftest_window_states.py` cite "DECISIONS.md,
      Project rules" for nothing of Designer's in front of the user's windows unless asked. No such entry is there.
      The user's word on it is recorded nowhere: Designer in front of their windows during tests is "a deal breaker",
      and Designer stays minimized, in front only when truly justified.
    - `check_designer_stayed_behind`'s docstring says "no window of Designer's at an opacity above 0". Only normal
      windows (layer 0) are judged. The Explorer's menus (layer 101) are said, not judged.
    - lifecycle's checks say "no wait for a close: its timer is started after the unloads". The close is handed to
      `_after_reply`, with no timer.
    - `common.crash_handlers`' docstring says "Crashpad's, one beside each Designer". `pgrep` lists every app's
      handler: three on this Mac, one of them Designer's.
    - `test_frames3d.py`'s comment says "in 3 of 3 shows ... in 5 of 5". HLP-151's resolution and frames3d.py say 5
      of 5 shows with nothing changed, and an UpdateRequest or a restart by the second paint in 9 of 9.
    - README.md says "On macOS the self-test's Designers start hidden". lifecycle's hand-over check starts the binary
      itself.
  - **Scenario.** Read in the code (2026-11-15); the environment measured as above.
  - **Fix.** Bring each in line with the code and the measurements. For the DECISIONS.md citation, point at the 3D
    shot's entry, or ask the user to record the rule.
  - **Resolution: done.**
    - lifecycle.py: the module docstring starts Designer (an app bundle through `open`), 5.66 s, no "own child"; the
      reaping comment, `_remember_started`, `OPENED_ENV`'s comment and `_opened`'s docstring say what the code does and
      what was measured (the whole environment reaches Designer). `launch_designer`'s docstring and README's
      SD_DESIGNER_APP row: the .app opened hidden, a binary there starts shown. The env test's message.
    - `give_back_activation`'s docstring (now with SRV-161); the plugin's after-reply sentence: after the send, done or
      failed, and none for one handed over after the job.
    - shot3d.py's header (TST-433); view3d.py: `_menu_once`'s look, `tries` every try.
    - The self-test: the launch check's docstring; window_server.py's module docstring and `stayed_behind`'s
      `active_only`, which no check passes now; "minimized through _MacWindow"; `check_designer_stayed_behind`'s layer;
      the quit helper's comment (no timer); `crash_handlers`; test_frames3d.py's counts; README's "start hidden".
    - DECISIONS.md, Project rules: the user's rule recorded, at their word (2026-11-16): no window of an agent's
      Designer in front of the user's during tests unless a check needs it there. HIDE's comment and the unit tests'
      heading cite it.
- [x] **TST-443 · Vague types in functions the diff adds or changes** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py`, `mcp_server/server_tools/lifecycle.py`, `mcp_server/designer_helpers/frames3d.py`, `view3d.py`, `tests/test_all_tools/workers.py`, `bridge/checks.py`, `tests/unit/` · confirmed · found 2026-11-15
  - **Defect.** By file, with the type each should have:
    - the plugin's `_run`, whose signature changed: `scope: dict[str, Any]` (`dict[str, object]`);
      `untraced(hook: Callable[..., Any], *args: Any)` (`Callable[..., object]`, `object`); `unraisable(info: Any)`
      (marked with its reason: `sys.UnraisableHookArgs` exists only in typeshed). `_authorised`: the result of
      `json.loads` (`object` until it is checked);
    - lifecycle.py: `_found_launched(opener: object, ...)` takes an `opener` it never uses, there for the conftest
      fake only; `port: str` there and in `_has_port`, where ports are `int` elsewhere;
    - frames3d.py: `_Frames.__init__`'s `render: Callable[[], Any]` (a QImage only compared: `Callable[[], object]`);
      view3d.py: `_MenuPick.__init__(self, action: str, before: Any)`, not marked;
    - the self-test: `workers.check_the_quits(parts: Mapping[str, dict[str, Any] | None], ...)` (a TypedDict of a
      worker's results); bridge's `ends: dict[str, Any]`, not marked;
    - the unit tests:
      - `test_selftest_window_states.py`: `_functions() -> dict[str, object]` (`dict[str, ast.AsyncFunctionDef]`)
        and `_awaits(nodes: list[object])` (`Sequence[ast.AST]`), the reason for five `type: ignore`s;
      - `test_selftest_window_server.py:37`: `-> list[object]` (`list[Sample]`);
      - `test_selftest_crash_dumps.py`: `may_come(self, ports: Any, ...)` (`Sequence[int]`) and `watch(...) -> Any`,
        not marked;
      - `test_selftest_pool.py`: `may_come(ports: Any, ...)` (`Sequence[int]`);
      - `test_plugin.py`: the fake `run(...) -> Any` (`object`);
      - `test_shot3d.py`: `on_screen(...) -> Any`, not marked;
      - `test_frames3d.py`: `cast(Any, frames)`, not marked;
      - `test_view3d_helpers.py`: the changed fakes `wheel`, `drag`, `failing`, `aborted`, `Watching.__new__` and
        `options: dict[str, Any]`, whose values are only passed on or compared (`object`).
  - **Scenario.** Read in the code (2026-11-15): mypy checks nothing through these.
  - **Fix.** Narrow each, or mark it `# Any: <reason>`.
  - **Resolution: done.**
    - Narrowed: the plugin's `scope` (`dict[str, object]`), `untraced` (`Callable[..., object]`, `object`), the request
      (`object` until checked); `unraisable` marked. lifecycle.py: `_found_launched`'s `opener` a Popen, ports `int`.
      `_Frames`' render `Callable[[], object]`; `_MenuPick`'s `before` marked. workers.py: `WorkerResults`, a TypedDict,
      for `merge`, `check_the_quits` and `_read`, which found a `float | None` in the quit times. bridge's `ends`
      marked.
    - The unit tests: `_functions` and `_awaits` (the five `type: ignore`s gone), `samples` (Sample's fields),
      `may_come` and `find` (`Sequence[int]`), the plugin's fake `run` (`object`), the view3d fakes (`object`); the
      others marked.
    - mypy strict passes.
- [x] **HLP-162 · The first 3D shot in a Designer opened hidden compares renders: its overlay shows no count until the view has drawn** · `mcp_server/designer_helpers/frames3d.py` (`_Frames.__init__`) · measured · found 2026-11-16
  - **Defect.** `_Frames` decides once, as it is made, whether a count shows: `self._counts = _Counts() if
    self.count() is not None else None`. In a Designer launch_designer opened hidden, the 3D view hasn't drawn yet, so
    its labels are empty.
  - **Scenario.** Measured (2026-11-16) in a Designer opened hidden (alone, port 9877), after the category's
    preparation: the four labels read `''` before any shot, and "Samples: 8" after one. So the first shot of an
    agent's Designer waits by comparing renders (`_renders_alike`: a render every TICK ms, through the clipboard), up
    to NO_RESTART and SETTLE_LIMIT a step, though counts show from its first frame on.
  - **Fix.** Make `_Counts` when a count first shows (`_event`), not only as `_Frames` is made.
  - **Resolution: done.**
    - **Test:** `test_a_count_first_shown_once_the_view_has_drawn_is_read_from_then_on` (the labels empty until the
      second paint) failed: the show compared renders. `test_a_show_with_no_count_at_the_paint_after_the_views_first_frame_compares_renders`
      covers Display > Samples off. Live, `check_the_first_3d_shot_in_a_designer_opened_hidden_waits_on_the_views_count`
      runs first among run()'s 3D shots. It wraps `_Frames._renders_alike` and calls `shoot_3d`, and skips when a
      count shows before the shot. In a Designer just started it failed: `(None, 1, 8)` (no count before, 1
      comparison, 8 after).
    - **Cause:** `_Frames` decided once, as it was made, whether a count shows.
    - **Fix:** `_Frames._event` makes `_Counts` at the first paint reading a count, the paints before it read as
      showing none. `shown()`, with no count yet, first waits for that or for the paint after the view's first frame,
      which a label shows the count of. The fact is in frames3d.py's module docstring, measured once.
    - **Also covered:** `settled()` and `moved()` read `_counts` as they begin. A step begun before any count showed
      compares renders for that step only. In a shot, `_bring`'s `shown()` comes before any step.
    - **Result:** the unit tests pass. The live check passes in a Designer just started: `(None, 0, 8)`, 2 runs.
  - Questioned by HLP-170 (2026-11-16).
- [x] **HLP-163 · Three waits still run their limit when the window goes off screen during them** · follows HLP-158, generation 4 · `mcp_server/designer_helpers/frames3d.py` (`_Frames.moved`, `shown`, `_renders_alike`), `shot3d.py` (`_bring`) · confirmed · found 2026-11-16
  - **Defect.** HLP-158 ended `settled()` and `taken()` when the view goes off screen. Three waits don't:
    - `moved()`'s second wait, `counts.moved(paints)`, runs SETTLE_LIMIT (3 s) once the restart was read. Its
      docstring, frames3d.py's and HLP-158's resolution say NO_RESTART.
    - `shown()`'s state ignores `_drawing()`. Off screen meanwhile, it runs SETTLE_LIMIT, and `_bring` returns with the
      window off screen. In the look before a render, the render is then the view's last frame, and no line says so.
    - `_renders_alike()`, where no count shows: off screen the renders are identical, so each step's comparison runs
      NO_RESTART.
  - **Scenario.** Read in the code: the user covers, minimizes or hides Designer's window during a viewpoint's turn,
    or during the look before a render.
  - **Fix.** `shown`: end on `not self._drawing()`, then bring the window in front again or refuse, as
    `_wait_on_screen` does. `_renders_alike`: end off screen on an UpdateRequest since the mark. `moved`: end its
    second wait as `settled` does, or say SETTLE_LIMIT.
  - **Resolution: done.**
    - **Test:** `test_a_show_ends_once_the_window_goes_off_screen_again`, `test_a_turns_wait_ends_once_the_window_goes_off_screen`
      (before and after its restart) and `test_with_no_count_shown_a_step_off_screen_ends_once_the_view_asks_for_a_frame`
      failed: each wait read on past the window going off screen. In test_shot3d.py,
      `test_a_window_covered_again_as_the_view_drew_is_brought_in_front_again` failed: brought once.
      `test_a_window_covered_again_each_time_the_view_drew_is_refused_and_put_back` did not raise. In
      test_view3d_helpers.py, `test_the_cameras_turn_is_watched_with_designers_window_on_screen` failed: no look
      between the turn and Frame.
    - **Cause:** HLP-158 ended `settled()` and `taken()` off screen, but not `shown()`, `moved()` or the comparison of
      renders.
    - **Fix:**
      - `shown()` ends as the view goes off screen (`_Frames.off_screen`). `_Screen._bring` then puts the window on
        screen again, BRINGS (3) times in all, then refuses ("went off screen again while its view drew").
      - `moved()` ends off screen too. The set-up's turn runs the look after it (`between`, or `_on_screen`'s
        `again` when set up alone), which puts the window back and waits there for the view to settle, before Frame.
      - `_renders_alike` takes an `ended()` looked at after each poll: off screen, an UpdateRequest since the step
        (`settled`), or the view off screen (`moved`, `shown`).
      - The docstrings of frames3d.py, view3d.py's `_3d_set_up` and shot3d.py's `_Screen` say so.
    - **Also covered:** `next_frame()` already returns at once off screen; `taken()` ended off screen (HLP-158).
    - **Result:** passes. A scratch run of the new checks and 12 existing off-screen 3D checks, in a Designer just
      started: 32 of 32. The checks that put Designer in front of the user's windows weren't run.
  - Questioned by HLP-167 (2026-11-16).
  - Questioned by HLP-172 (2026-11-16).
- [x] **HLP-164 · A move's wait marks after the move's events ran, so an UpdateRequest delivered meanwhile is missed and the wait runs NO_RESTART** · `mcp_server/designer_helpers/frames3d.py` (`_Frames.taken`), `view3d.py` (`_drag`), `editor.py` (`_wheel`) · measured · found 2026-11-16
  - **Defect.** `taken()` takes its mark when called: after `_drag`'s press, moves and release, or `_wheel`'s notch,
    each followed by `_process_events(2)`. Off screen the view sends one UpdateRequest a move. Delivered within those
    calls, it comes before the mark, and nothing more comes.
  - **Scenario.** Measured (2026-11-16) in a Designer opened hidden: 60 moves, wheel notches and drags in turn. The
    first took 0.95 s, its UpdateRequest delivered before the mark; the other 59 took 0.02 to 0.03 s each. The first
    review's measurement fits: one notch in 30 at the full 1 s.
  - **Fix.** Take the mark before the press or the notch, and pass it to `taken(since)`.
  - **Resolution: done.**
    - **Test:** `test_a_moves_update_request_delivered_before_its_wait_began_ends_the_wait`: an UpdateRequest
      delivered as the move's events ran, off screen. It failed: no `taking`, the API to mark before the move.
      `test_each_wheel_notch_waits_from_a_mark_taken_before_it_is_sent` failed: the mark came after the notch's
      events. `test_a_drag_is_a_press_moves_and_a_release...` expects the mark before the press.
    - **Cause:** `taken()` took its mark when called, after the move's events.
    - **Fix:** `_Frames.taking()`, called before the press or the notch, returns the wait. Its UpdateRequests count
      from then, its paints from the wait's start. `_drag` and `_wheel` take `taking` (optional) and call it before
      the move. The first version counted the paints from before the move too. In the scratch run that lost one of
      zoom=-3's three steps (0.82x), and the zoom with Designer hidden at its first step failed. So paints count
      from the wait's start, with a unit test of it
      (`test_on_screen_a_frame_drawn_while_a_moves_events_ran_doesnt_end_its_wait`). Both facts are in frames3d.py's
      module docstring, measured once.
    - **Also covered:** every caller passing `taken`: the set-up's drags and wheel, the self-test's
      `MOVES_UNDER_ANY_TOOL`, window_states' drags, and `_HIDDEN_MID_ZOOM`'s wrapper of `_wheel`, moved to the new
      protocol. Its check failed until then, as the wrapper's function ran before each notch.
    - **Result:** passes. The zoom checks and the mid-zoom check pass (0.00 grey levels, 3 of 3 alone), in the
      32-check scratch run.
  - Questioned by HLP-169 (2026-11-16).
- [x] **HLP-165 · `_Frames`' spy holds `_Frames` through its callback: after an abort that skips `close()`, the 3D viewport keeps a Python filter until the cyclic GC runs** · `mcp_server/designer_helpers/frames3d.py` (`_Frames.__init__`, `close`), `waits.py` (`_event_signal`) · confirmed · found 2026-11-16
  - **Defect.** `_event_signal(viewport, ('Paint', 'UpdateRequest'), self._event)`: the filter's class closes over
    the bound method, which holds `_Frames`, which holds the filter. Dropped by its frame, the cycle frees nothing
    until the cyclic collector runs, and the viewport's filter and its window's `_exposed` stay installed meanwhile.
    The helpers otherwise rely on a frame's objects going with it after an abort (`_drag`'s guard, `_until`'s timers).
  - **Scenario.** Read in the code: an abort landing on `frames.close()`, in it, or in `_Frames.__init__` after the
    first spy is installed. Each paint of the 3D view then runs Python and grows `seen` until a collection. Objects
    that lived through a shot are likely in an older generation, collected later.
  - **Fix.** Keep the counters in an object the closure holds and that doesn't hold the spies, or give
    `_event_signal` a weak method.
  - **Resolution: done.**
    - **Test:** `test_frames_dropped_without_close_go_at_once_with_their_filters` (the cyclic collector off) failed:
      `_Frames` still alive after its last reference went. Live,
      `check_a_watch_of_the_3d_views_frames_dropped_without_close_goes_at_once` failed: `(False, False)` (the watch
      and its spy both alive).
    - **Cause:** the spy's class closed over the bound method `self._event`, which held `_Frames`, which held the spy.
    - **Fix:** `_Frames.__init__` passes a function that holds `_event` through a `weakref.WeakMethod`.
    - **Also covered:** every other `_event_signal` callback, in the helpers and the self-test's snippets, closes over
      lists or the window, never over an object holding the spy.
    - **Result:** passes; live `(True, True)`.
- [x] **HLP-166 · give_back_activation's unhide waits for its window's exposure, which a window covered whole never gets** · follows HLP-160, generation 2 · `mcp_server/designer_helpers/mac_window.py` (`give_back_activation`) · confirmed · found 2026-11-16
  - **Defect.** For a Designer started shown (a binary in SD_DESIGNER_APP) that became the active app, it hides it,
    unhides it, and waits `_until(handle.isExposed, ACTIVATION_WAIT, ...)`. HLP-160 measured that an unhidden window
    goes behind the active app's window, and that once covered whole, Qt no longer exposes it. HLP-160's Also covered
    took this path for fine, as it brings nothing in front.
  - **Scenario.** Read in the code, with HLP-160's measurement: the active app's window covers Designer's whole, and
    the launch waits ACTIVATION_WAIT (3 s) before it says it gave the keyboard back.
  - **Fix.** Wait for macOS to no longer say Designer is hidden, as `_wait_unhidden` does, not for the exposure.
  - **Resolution: done.**
    - **Test:** `test_the_show_is_waited_for_until_macos_says_designer_is_shown_not_until_its_window_is_exposed` (the
      window never exposed, covered whole) failed: the show's wait read False.
    - **Cause:** `give_back_activation` waited for the window's exposure, which a window covered whole never gets
      (HLP-160).
    - **Fix:** `_wait_unhidden(mac, handle, limit)` in mac_window.py: waits for `not mac.hidden()`, woken by the
      window's expose events and looked at every TICK ms. `give_back_activation` and the shot's `_bring` both use it.
      The `_Screen` method of the same name is gone.
    - **Also covered:** the only other unhide waits are in the self-test's set-ups (HLP-160's Also covered).
    - **Result:** the unit tests pass. No live check: making Designer the active app takes the user's keyboard.
  - Note (2026-11-16): measured with the user's go, at an unhide with Designer's window covered whole by another
    app's window: Qt exposed the window at once, 6 of 6 (the fourth review's log). So the exposure wait this
    replaced may have ended at the show too; give_back_activation's own case wasn't measured. Waiting for macOS's
    unhide holds either way.
- [x] **TST-445 · HLP-160's live check reads the windows in front once, and skips for good when the window readers return nothing** · follows HLP-160, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`SHOWN_FROM_HIDDEN`, `check_a_hidden_designers_window_is_brought_in_front_for_a_3d_shot_once_its_unhide_took`) · confirmed · found 2026-11-16
  - **Defect.**
    - It judges `in_front` empty at one reading. A window the user raises meanwhile, by a click through Designer's
      click-through window, reads as HLP-160's failure. The other window-order readings take theirs again (TRIES,
      `no_designer_starting`: TST-417).
    - It skips when `active_app()` returns None or `windows_now()` lists nothing. A broken reader then makes the check
      a SKIP in every run, and `test_the_windows_on_screen_now_are_read_with_their_owners` passes with `()`.
  - **Scenario.** Read in the code: the user clicks a window of theirs during the read, in a full run.
  - **Fix.** Read again while a window is in front, up to TRIES, and fail only if every read lists one. Skip only
    when windows are listed and none is the active app's; with none listed, or no active app read, fail as "can't
    tell" (TST-405, TST-441).
  - **Resolution: done.**
    - **Test:** `test_whether_the_active_app_shows_a_window_is_unknown_when_either_reading_is_missing` (new
      `window_server.active_shows_a_window`: None with no active app or no window read). Before it, the check skipped
      in both cases. `test_the_windows_on_screen_now_are_read_with_their_owners` now requires a window listed.
    - **Cause:** the check read the windows in front once, and took a missing reading for "nothing to judge".
    - **Fix:** the check fails as "can't tell" when either reading is missing, and skips only when windows are read
      and none is the active app's. It runs SHOWN_FROM_HIDDEN again while a window is in front of Designer's, up to
      TRIES times, failing only if every try finds one. Its detail says how many tries it took.
    - **Also covered:** the other window-order readings retry already (`retries.without_others_in_front`, TST-417).
    - **Result:** passes: the unit tests, and the check in a scratch run, 1 try.
  - Questioned by TST-453 (2026-11-16).
- [x] **TST-446 · The transparent-at-each-render check still doesn't judge `covered`, though HLP-160 explains the readings it was dropped for** · follows HLP-160, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_a_3d_shot_keeps_designers_window_transparent_and_click_through_while_off_screen`) · measured · found 2026-11-16
  - **Defect.** Its comment: whether macOS still counted the window covered at each render "isn't judged: a window of
    the user's where Designer's comes back covers it until the shot brings it in front (REVIEW.md SRV-152)". Each
    RENDER line is read after `screen.again()`, and those readings fit HLP-160's defect, now fixed. So the check
    would pass HLP-160 back.
  - **Scenario.** Measured (2026-11-16) after HLP-160's fix, in a Designer opened hidden, PyCharm the active app: the
    check's three ways, 3 times each, read `covered=False` at each of their 18 renders.
  - **Fix.** Judge `covered == 'False'` at each render, for the minimized, covered and hidden ways, and drop the
    comment's reason.
  - **Resolution: done.**
    - **Test:** the check itself judges `covered == 'False'` at each render, for the minimized, covered and hidden
      ways. Its detail now prints the values. It passes in the scratch run. To see it fail, a scratch run put HLP-160's
      defect back (`_wait_unhidden` a no-op). The hidden way still passed, 6 of 6 tries: HLP-160 didn't show today, as
      in its later runs (0 of 2). So the judgement was seen passing, not failing on the defect. By reading, it fails on
      any render read covered.
    - **Fix:** the judgement added. The comment's reason (SRV-152) replaced by what the shot does since HLP-160.
    - **Result:** passes, 3 ways.
- [x] **TST-447 · A failing `pgrep` reads as no crash handler, so the crash waits end at once** · follows SRV-151, generation 2 · `tests/test_all_tools/common.py` (`crash_handlers`, `dumps_may_come`) · confirmed · found 2026-11-16
  - **Defect.** `crash_handlers()` returns `pgrep`'s stdout and never reads its return code. On an error (2 or 3) the
    empty list makes `dumps_may_come` False, and `CrashWatch.settle` and `workers.wait_for_dumps` stop waiting.
    `designer_pids` raises `NoListing` on the same codes (`test_a_failing_pgrep_is_an_error_not_no_designer`).
  - **Scenario.** Read in the code: `pgrep` failing as a Designer crashes, its dump, written a few seconds later, is
    missed, and the "no crash dump" check passes.
  - **Fix.** Treat a return code other than 0 or 1, or an OSError, as "a dump may come", with a unit test.
  - **Resolution: done.**
    - **Test:** `test_a_failing_pgrep_reads_as_handlers_unknown_not_as_none_running` (exit codes 2 and 3 failed: `[]`),
      `test_a_pgrep_that_cant_run_reads_as_handlers_unknown` (OSError raised through) and
      `test_a_dump_may_come_while_the_crash_handlers_cant_be_listed` (TypeError, then True) failed.
    - **Cause:** `crash_handlers()` read pgrep's output and never its exit code.
    - **Fix:** `crash_handlers()` returns None when pgrep exits other than 0 or 1, or can't run. `dumps_may_come`
      then returns True, so the waits run to their limit.
    - **Also covered:** the other pgrep and ps calls. `_designer_pids` (server and self-test) and uninstall.py read
      the exit code. `_has_port`'s ps failing makes `_found_launched` say the process wasn't found. core.py's
      `_designer_running`, main's code, reads a failing pgrep as no Designer: SRV-163.
    - **Result:** passes.
- [x] **TST-448 · The crash-wait fake says it behaves as `dumps_may_come`, and two tests of the real function read the user's own crash-dump folder** · follows TST-437, generation 4 · `tests/unit/test_selftest_crash_dumps.py` (`_Dumps.may_come`, `test_a_dump_may_come_while_its_designers_crash_handler_runs_and_none_is_there`, `test_a_dump_may_come_from_the_runs_own_designer`) · confirmed · found 2026-11-16
  - **Defect.** The fake's docstring: "as common.dumps_may_come, which never ends on one in the user's folder". It
    has one handler flag for every home, where the real function waits per port. The two tests of the real function
    redirect SHORT_TEMP but not HOME, so `crash_dumps` lists the user's own `~/Library/.../Sentry-Crashpad`. The
    filter that ignores that folder is then guarded only on a machine that holds dumps there. The tests only read it.
  - **Scenario.** Read in the code. No result depends on the fake's difference today.
  - **Fix.** Generation 4, tests only, so the claims get smaller: the fake's docstring says what it does, and a
    comment in the two tests says the user's-folder filter isn't tested there.
  - **Resolution: done (generation 4: the claims made smaller).**
    - The fake's docstring says it has one handler for every home, where `dumps_may_come` looks for each port's.
    - The two tests' comments say HOME isn't redirected, and the filter ignoring the user's folder isn't tested
      there.
- [x] **TST-449 · `test_waits.py` passes bridge's 50 ms status poll as "a job holding the bridge"** · `tests/unit/test_waits.py` (the entry for `bridge/checks.py`'s `time.sleep(0.05)`) · confirmed · found 2026-11-16
  - **Defect.** Of the three `time.sleep(0.05)` it lets through, two are inside jobs (`bridge/checks.py:54` and
    `:96`). The third (`:85`) is `wait_for`'s poll of the bridge's status. The new test vouches for it with a reason
    that isn't true, and lets a poll at 50 ms stand against AGENTS.md's 100 ms. `wait_for`'s result is never read.
  - **Scenario.** Read in the code.
  - **Fix.** Give `wait_for` POLL_S against a deadline, and the entry a count of 2; at least, give `:85` its own
    reason.
  - **Resolution: done.**
    - **Test:** `test_waits.py`'s entry for `bridge/checks.py`'s `time.sleep(0.05)` set to 2: it failed, 3 found.
    - **Fix:** `wait_for` polls the bridge's status every POLL_S against a 5 s deadline, the limit it had (100 times
      0.05 s). The entry keeps its reason for the two sleeps inside jobs.
    - **Result:** passes; the bridge category in a scratch run, 38 of 38.
- [x] **TST-450 · The frames fact's judgements, and the window checks' BROUGHT_ON_SCREEN, have no unit test** · follows TST-428, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`_shown`, `_changed_by_its_second_paint`, `restarted`, `held`, `BROUGHT_ON_SCREEN`) · confirmed · found 2026-11-16
  - **Defect.** They decide in plain Python whether the frames fact and the window checks pass. TST-428 had
    `showing()` and `in_order()` evaluated in unit tests; these were left out, so a comparison any reading satisfies
    would go unseen.
  - **Scenario.** Read: no test names them.
  - **Fix.** Parametrized unit tests on recorded readings: the measured passes, and readings that must fail, TST-439's
    among them.
  - **Resolution: done.**
    - **Test:** `tests/unit/test_selftest_frames_fact.py`, 34 cases: `_restarted`, `_held`, `_shown`,
      `_changed_by_its_second_paint` and each way of `BROUGHT_ON_SCREEN`. Each runs on the readings measured, which
      pass, and on readings that must fail: TST-439's not hidden before, a restart before the request, a request
      after the second paint. With each judgement made to return True, 23 of 34 failed.
    - **Fix:** the frames fact's `restarted` and `held`, nested in the check, moved to module level as `_restarted`
      and `_held`, unchanged.
    - **Result:** passes; the frames fact in the scratch run passes.
- [x] **TST-451 · Comments and docstrings that say other than the code** · follows TST-442, generation 4; PLG-43, generation 3; SRV-161, generation 2 · listed below · confirmed · found 2026-11-16
  - **Defect.**
    - The plugin's `_Waker._on_after`: a callback that raises "is said in Designer's log". Inside another job's nested
      event loop, `_run`'s `redirect_stdout` is active, and the traceback goes into that job's output (PLG-43's own
      scenario).
    - `mac_window.py`, `give_back_activation`: `hidden = mac.hidden()  # started hidden (REVIEW.md SRV-152): left
      so, not shown again`. SRV-161 measured that a Designer opened hidden reads shown once active, as the docstring
      above says, and `started_hidden` handles it. `test_mac_window.py`'s
      `test_a_designer_started_hidden_that_became_the_active_app_stays_hidden` builds that unseen state.
    - `mac_window.py`'s module docstring: "launch_designer now starts it hidden"; a binary in SD_DESIGNER_APP starts
      shown.
    - `lifecycle.py`'s `_designer_env`: "(not seen: `open -a` never passed them on)"; `_opened` now passes the whole
      environment through `open`.
    - `lifecycle/checks.py`'s hand-over check: "Started here from the binary as launch_designer starts one";
      launch_designer opens the app bundle.
    - `lifecycle/checks.py:54`: the comment for CLOSE_WINDOWS_ONLY sits above HANDLER_GONE_S.
    - `editor_panels_and_fit/checks.py`, the material check: `# REVIEW.md TST-425: printed, never judged`, on the line
      that judges `HIDDEN AGAIN=True`.
  - **Scenario.** Read in the code.
  - **Fix.** Make each claim smaller, or move it: "printed to Designer's log, or into the output of a job running
    then"; "hidden while active: not seen (SRV-161), a defence", with the test named so; "opens an app bundle
    hidden"; drop the parenthetical; "from its binary, with the environment launch_designer gives one"; move the
    comment; "was printed, never judged".
  - **Resolution: done (the claims made smaller or moved).**
    - The plugin's `_Waker._on_after`: "printed to Designer's log, or into the output of a job running then".
      install.py run, and the scratch runs' Designer restarted: "installed plugin matches the repo" passes.
    - `give_back_activation`'s `hidden` comment: hidden while active wasn't seen (SRV-161), a defence, with the test
      that builds the state named.
    - mac_window.py's module docstring: an app bundle opens hidden; a binary in SD_DESIGNER_APP starts shown.
    - `_designer_env`'s parenthetical dropped.
    - The hand-over check: "from its binary, with the environment launch_designer gives one".
    - lifecycle/checks.py: the comment moved onto CLOSE_WINDOWS_ONLY.
    - The material check: "was printed, never judged".
- [x] **TST-452 · Vague types in functions the diff adds or changes** · follows TST-443, generation 2 · listed below · confirmed · found 2026-11-16
  - **Defect.**
    - `tests/test_all_tools/bridge/checks.py`, `run`: `replies: dict[str, Any]` and `job(name: str, req: dict[str,
      Any])`, unmarked: `req` fits `dict[str, object]`, `replies` a TypedDict of the plugin's reply. `ends: dict[str,
      Any]  # Any: raw_request's replies, parsed JSON`: AGENTS.md gives parsed JSON `object`.
    - `tests/unit/test_selftest_pool.py`: `write(...) -> dict[str, Any]`, three times; the fake types it
      `Mapping[str, object] | None`.
    - `tests/unit/test_selftest_alone.py`: `async def a_check(ctx: Any)`: `Ctx`, or `object`.
    - `tests/unit/test_selftest_crash_dumps.py`: `_Dumps.watch(self, common: Any)`, unused: `object`.
    - `tests/unit/test_lifecycle_env.py`: the fakes' `request: dict[str, Any]` (three) and `**kw: Any` (four),
      unmarked: `dict[str, object]` and `object`. The one reading `kw['stderr']` narrows it with `isinstance`, or is
      marked.
    - `tests/unit/test_selftest_window_server.py`: `out: object` with `# type: ignore[index]`, where
      `ctypes.Array[ctypes.c_double]` fits, and `# type: ignore[arg-type]` on `Bounded(...)`, which hides that `Server`
      types its windows as 3-tuples.
  - **Scenario.** Read in the code.
  - **Fix.** As listed.
  - **Resolution: done.**
    - bridge/checks.py: `replies` and `ends` are `dict[str, Reply]`, a new TypedDict in common.py (the plugin's reply:
      ok, output, error); `job`'s `req` is `dict[str, object]`.
    - test_selftest_pool.py: every `write` returns `Mapping[str, object]` (or `| None`), as the fake takes it.
    - test_selftest_alone.py: `a_check(ctx: object)`.
    - test_selftest_crash_dumps.py: `_Dumps.watch(self, common: object)`.
    - test_lifecycle_env.py: the two fakes' `request: dict[str, object]`, and the two `begin`s' `**kw: object`. The
      one writing to `stderr` narrows it with `isinstance(..., io.BufferedIOBase)`.
    - test_selftest_window_server.py: `out: ctypes.Array[ctypes.c_double]`, its ignore gone. test_selftest_popups.py's
      `Server` types its windows as `FakeWindow` (3-tuples, or 4 with bounds), so `Bounded(...)` needs no ignore.
    - mypy strict passes.
  - Questioned by TST-459 (2026-11-16).
- [x] **SRV-163 · A failing `pgrep` reads as no Designer running in `_designer_running`** · `mcp_server/server_tools/core.py` (`_designer_running`), its callers in `lifecycle.py` (`_running_on`, `_quit`) · confirmed · found 2026-11-16
  - **Defect.** `_designer_running()` returns `pgrep`'s exit code == 0. On pgrep's own errors (2 or 3), or one that
    can't run (OSError, raised), it reads no Designer. `_designer_pids` (SRV-97) and the self-test's
    `crash_handlers` (TST-447) tell those apart.
  - **Scenario.** Read in the code, found addressing TST-447 (main's code, outside the branch's diff). pgrep failing:
    `quit_designer` says "Designer is not running." while one may run; `launch_designer` reads none running and goes
    on to start one, where `_sorted_out`'s `_designer_pids` raises. The preferences' put-back is safe:
    `_any_designer` reads "can't tell" as a Designer running.
  - **Fix.** Tell "can't tell" apart in `_designer_running` (exit codes other than 0 or 1, OSError), and let each
    caller decide: a Designer may run (as `_any_designer`), or an error saying the processes couldn't be listed.
  - **Resolution: done.**
    - **Test:** `test_lifecycle_env.py`, with the real `_designer_running` and `_designer_pids` and pgrep faked:
      - `test_a_failed_process_listing_isnt_read_as_no_designer_running` (exit code 2, exit code 3, pgrep missing):
        the exit codes didn't raise, and `_running_on` read none running. A missing pgrep raised its raw
        `FileNotFoundError`, which doesn't say the processes couldn't be listed;
      - `test_a_quit_with_the_processes_unlisted_doesnt_say_none_runs`: it didn't raise, as it said "Designer is not
        running.";
      - `test_the_log_with_the_processes_unlisted_isnt_chosen_as_none_running`: `read_designer_log` didn't raise;
      - `test_a_launch_with_the_processes_unlisted_starts_none` passed before the fix: `_users_next_to`'s own listing
        refused the launch before anything started. It stays as a guard;
      - `test_pgrep_finding_designer_or_nothing_reads_as_running_or_not` (exit codes 0 and 1) passed before and after.
    - **Cause:** `_designer_running` ran its own pgrep and read every exit code but 0 as none running, where
      `_designer_pids` (SRV-97) told pgrep's errors apart.
    - **Fix:** `core.py` has one `_pgrep()`, which raises `_NoListing` on exit codes other than 0 or 1 and on an
      `OSError`. `_designer_running` and `lifecycle.py`'s `_designer_pids` both use it, and `_NoListing` moved from
      `lifecycle.py` to `core.py`. Every caller lets the error through: `quit_designer`, `launch_designer` and
      `read_designer_log` (through `_running_on`) say the processes couldn't be listed. `_running_on` already raised
      that error whenever its second listing failed.
    - **Also covered:** every other pgrep. `uninstall.py`'s `folders_in_use`, the self-test's `_pgrep`
      (`designer_alive`, `designer_pids`) and `crash_handlers` (TST-447) already tell the errors apart. Not changed:
      `tasklist` on Windows, in the server and in the self-test's `designer_alive`. An `OSError` there is raised, not
      read as none running, and tasklist's exit codes can't be measured here (no Windows).
    - **Result:** the new tests pass; `test_lifecycle_env.py` and `test_bridge.py` with lint and types, 292 passed;
      the other tests of the touched code (`test_selftest_lifecycle.py`, `test_designer_preferences.py`,
      `test_server.py`, `test_selftest_summary.py`, `test_selftest_alone.py`, `test_uninstall.py`), 242 passed.
  - Questioned by SRV-164 (2026-11-16).
- [x] **SRV-164 · One failed process listing ends launch_designer's wait, and its error, like every `_NoListing` the call lets out, leaves out what the call already did** · follows SRV-163, generation 2 · `mcp_server/server_tools/lifecycle.py` (`launch_designer`) · confirmed · found 2026-11-16
  - **Defect.**
    - Since SRV-163, `_running_on` raises `_NoListing` when pgrep fails. In the wait's loop (`if running and
      may_have_exited() and not _running_on(port)`), nothing catches it, so one failure ends the call. Before, it read
      as no Designer: `start()` listed again under the lock and, finding the Designer, the wait went on.
    - The error is the bare "Designer's processes couldn't be listed (...)", without `told()`. A Designer this call
      ended, with its sample's file, and what was done with Designer's preferences go unsaid, and `none_left()`'s
      put-back doesn't run.
    - The other `_NoListing`s the call lets out leave `told()` out too, on main as well: `start()`'s `_running_on`
      and `_users_next_to`, `_end_if_past_startup`'s `_force_end`, and `_how_to_end` in the timeout's message.
  - **Scenario.** Read in the code. launch_designer waits on a Designer no agent recorded (the user's still
    starting, or another launch's not yet recorded), so `may_have_exited()` is True each round, and one pgrep fails
    (exit code 3, or a fork failing).
  - **Fix.** In the loop, read `_NoListing` as "may still hold the port" and go on waiting, as `_any_designer` reads
    "can't tell". Where it ends the call, raise it with `none_left()` (or `told()`) in front, as the timeout and the
    refusal do.
  - **Resolution: done.**
    - **Test:** in `test_lifecycle_env.py`:
      - `test_a_launch_waiting_on_a_designer_goes_on_when_its_processes_cant_be_listed_once`, one listing failing in
        the wait, raised the listing's error;
      - `test_a_launch_that_ended_a_designer_and_starts_none_puts_back_first[processes unlisted]`, an agent's Designer
        ended, then `_users_next_to`'s listing failing, neither said the Designer ended nor put Designer's preferences
        back.
    - **Cause:** SRV-163 made `_running_on` raise where it had read no Designer. Nothing in launch_designer caught a
      `_NoListing`, so one ended the wait and left `told()` out.
    - **Fix:** the wait's look goes through `_may_hold`, which reads "can't tell" as a Designer that may hold the port,
      so the wait goes on. Any other `_NoListing` launch_designer lets out is raised again with `none_left()` in front:
      what the call did, and Designer's preferences put back if it ended or started one.
    - **Also covered:** `start()`'s `_running_on`, under the lock, still ends the call with that error, now with
      `none_left()`: it can't tell whether to start one. `_end_if_past_startup` and `_how_to_end` inside the call are
      covered by the same clause. `_log_for` (read_designer_log) and `_quit` raise it, as SRV-163 chose.
    - **Result:** passes, with the rest of `test_lifecycle_env.py` (270).
- [x] **HLP-167 · A 3D shot's show from a sample count left low off screen can end at its second paint, and render the first sample** · follows HLP-163, generation 5 · `mcp_server/designer_helpers/frames3d.py` (`_Counts.shown`, `_Frames.shown`), `shot3d.py` (`_Screen._bring`) · measured · found 2026-11-16
  - **Defect.** `_Counts.shown` also ends on `self.unchanged(since) and not asked`: two paints reading no restart, and
    no UpdateRequest since the show. A count left below the target reads no restart at the show: the view went off
    screen mid-accumulation, where HLP-163's waits end. So two expose paints reading it end the wait before
    `_went_on` can wait for the target.
  - **Scenario.** Measured in a probe in a Designer an agent opened hidden (port 9877), inside `_on_screen`
    (transparent and click-through), 5 tries. Each try panned, hid Designer once the count read 3 or less (it read 1
    each time), then called `screen.again()`, with `_Counts.shown` wrapped to say which branch ended the wait:
    - 4 of 5: `_went_on`, at a paint reading 8, 0.09 to 0.10 s after the show began;
    - 1 of 5: `unchanged and not asked`, at the second paint, both reading 1 (`again` took 0.006 s). The count read 1
      then, and 8 after 1.5 s. A render taken then is the first sample's.
    In a shot, the user's click raising a window of theirs over Designer's click-through window during the
    accumulation puts the view off screen the same way.
  - **Fix.** Apply `unchanged and not asked` only when the count read before `since` is None or at the target. A count
    left lower then waits for `_went_on` or a restart, SETTLE_LIMIT the safety net. A unit test: counts 8, 1, a mark,
    then paints reading 1, 1 with `asked=False`: not shown.
  - **Resolution: done.**
    - **Test:** `test_frames3d.py::test_a_show_from_a_count_left_lower_isnt_ended_by_two_paints_reading_it` (counts 8,
      1, then paints reading 1, 1 and no UpdateRequest) was shown. Live,
      `check_a_3d_shots_window_shown_again_mid_accumulation_waits_for_the_count_at_rest` failed in a scratch run: of
      the 5 tries hidden at a count of 3 or less, 2 ended at 1. Its 6 tries each pan, hide Designer once the count
      reads 3 or less, then call `screen.again()`.
    - **Cause:** `unchanged and not asked` tells nothing changed from a change made off screen, a rule measured from a
      count at rest. From a count left lower, the expose paints read that count before the view asks for a frame.
    - **Fix:** `_Counts.shown` applies the rule only when the count read before the show is at the target, or none was
      read (`_before`, also used by `restart` and `_went_on`). frames3d.py's docstring has the measured fact, and its
      waits' bullet the rule.
    - **Also covered:** `settled` and `moved` don't use the rule. A shot's first show starts from no count read, where
      a lower first paint counts as a restart.
    - **Result:** passes: the unit tests of frames3d, shot3d and view3d (234). Live, 6 of 6 tries, each hidden at 1
      and ended at 8. The window checks that bring the window back during a shot pass too.
  - Questioned by TST-463 (2026-11-16).
- [x] **HLP-168 · `set_3d_view` off screen goes on after a mesh switch at the view's first request, while the view still takes the switch: a mesh and an orbit in one call come out differently each time** · follows HLP-158, generation 4 · `mcp_server/designer_helpers/view3d.py` (`_3d_set_up`, the mesh step), `frames3d.py` (`_Frames.settled` off screen) · measured · found 2026-11-16
  - **Defect.** Off screen, `settled` ends at the first UpdateRequest since the step (HLP-158). After a mesh switch,
    that request comes at about 0.07 s, but the view asks for more frames until about 0.32 s. The moves that follow
    in the same call run meanwhile.
  - **Scenario.** Measured in probes in Designers an agent opened hidden (port 9877). Each way started from
    `set_3d_view(mesh='Rounded cube', view='Front')`, its result shot with no set-up, the shots compared in grey levels
    (mean absolute difference):
    - after `set_3d_view(mesh='Sphere')`, the UpdateRequests came at 0.068 s, when the call returned, then at 0.13 to
      0.17 s and at 0.32 s, 3 of 3;
    - `set_3d_view(mesh='Sphere', orbit=[90, 30])` in one call: 1.12 apart between two runs in one Designer, 4.16 in
      another;
    - the mesh, then the orbit in a second call 1.5 s later: 0.00 between runs, and 8 to 35 from the one call;
    - the shot's own set-up (on screen, `mesh='Sphere', orbit=[90, 30]`): 0.00 between runs, and 16 to 20 from the one
      call.
    Each part alone matched on screen and off, 0.00 in 2 of 2: the mesh switch, the orbit's up part `[0, 30]`, and
    `[90, 0]` from Front against view Right, in one call and in two. Not explained: the two calls 1.5 s apart differ
    from the shot's set-up by 11.64, and on screen, the mesh in one shot then the orbit in another differed by 1.49
    between runs.
  - **Fix.** Measure first what says the view has taken a mesh switch off screen (its last UpdateRequest, or a state
    of the scene), and wait for it after the mesh step. Then compare the one call, the two calls and the shot's set-up
    again.
  - **Resolution: done (the user's choice, 2026-11-16: "Show the window (Recommended)").**
    - **Measured first,** in a Designer an agent opened hidden, each set-up from a start the view had drawn, on screen
      (the shot's set-up) against off screen (`set_3d_view`), twice. Orbit [0, 30], orbit [90, 30], orbit [90, 0]
      with pan [0.2, 0], and a mesh switch with orbit [90, 0] came out alike, 0.00. Pan [0.2, 0.1] came out 68.53 grey
      levels away off screen in 1 run of 2. On screen, every set-up repeated exactly. So the mesh step's wait isn't the
      whole cause: moves made off screen don't always come out the same, and nothing found says when they will.
    - **Test:** `test_view3d_helpers.py::test_a_set_up_that_moves_the_camera_runs_with_designers_window_on_screen`
      (orbit, pan, zoom, a mesh with an orbit; a set-up with no move stays off screen but for the turn) failed: the
      moves ran with no window put on screen. Live, `check_set_3d_view_moves_the_camera_as_a_3d_shots_set_up_does` (a
      pan of two drags from Top, set_3d_view's against the shot's, 2 tries) failed in a scratch run: the window wasn't
      put on screen for the pan. The renders matched that time.
    - **Fix:** `set_3d_view` with orbit, pan or zoom runs the whole set-up inside `_on_screen`, on a watch of its own,
      each step after the shot's look (`screen.again`), as a 3D screenshot sets up. Its docstring, frames3d.py's facts
      and DECISIONS.md's camera turn entry say so.
    - **Also covered:** the 3D shot's own set-up already ran on screen. A set-up with no move (mesh, graph, view,
      tiling) stays off screen but for the turn: a mesh switch alone came out alike on and off screen (0.00, 2 of 2).
    - **Result:** passes: the unit tests (117 with view3d's and the parts'), and live, 2 of 2 tries (the window put on
      screen, the renders 0.00 apart). The user's-mouse check, which calls set_3d_view with an orbit and a pan,
      passes.
  - Note (2026-11-16): at the user's request, DECISIONS.md's camera turn entry, which recorded this choice, was
    removed: nothing cited it, and AGENTS.md's wait rule already rules out the time limit it turned down. The choice
    stays recorded here and in `set_3d_view`'s docstring.
  - Questioned by HLP-174 (2026-11-16).
  - Questioned by TST-465 (2026-11-16).
- [x] **HLP-169 · `_drag`'s and `_wheel`'s docstrings say a frame since the press or the notch ends the wait, where only a frame once the move's events ran does** · follows HLP-164, generation 2 · `mcp_server/designer_helpers/view3d.py` (`_drag`), `editor.py` (`_wheel`) · confirmed · found 2026-11-16
  - **Defect.** `_drag`: "(_Frames.taking: a frame of the 3D view since the press; off screen, an UpdateRequest
    since)". `_wheel`: "the 3D view's _Frames.taking, a frame since, or off screen an UpdateRequest since". `taking`
    counts paints from the wait's start, once the move's events ran. Counted from before, zoom=-3 lost one of its
    steps (frames3d.py's docstring). HLP-164's Also covered missed the two.
  - **Scenario.** Read in the code.
  - **Fix.** Say "a frame drawn once the move's events ran; off screen, an UpdateRequest since the press" (the notch,
    for `_wheel`).
  - **Resolution: done.** Both docstrings say a frame drawn once the move's events ran, or off screen an UpdateRequest
    since the press (the notch, for `_wheel`). Docstrings only, so no test.
- [x] **TST-454 · The Light tool check waits out NO_RESTART for each move the tool ignores** · follows TST-421, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`MOVES_UNDER_ANY_TOOL`) · measured · found 2026-11-16
  - **Defect.** Under the Light tool, the wheel and a middle drag don't move the camera. The hidden view then asks for
    no frame, and each move's `taken()` runs its 1 s limit. The limit becomes the wait's time, against AGENTS.md's
    wait rule. The snippet's comment says "each move waits for its request for one".
  - **Scenario.** Measured in a probe in a Designer an agent opened hidden (port 9877), the snippet's moves timed one
    by one, twice under the Light tool and once under the Camera tool:
    - Light tool: each of 3 notches and the middle drag took 1.0 to 1.05 s, with no UpdateRequest. The left drag took
      0.01 s, with one;
    - Camera tool: each move took 0.00 to 0.03 s, with one UpdateRequest.
    So the check spends about 4 s on limits in each run.
  - **Fix.** Send the moves the tool ignores without `taking`, and say why in the comment. Another possible place, not
    measured: `put_and_drag('qt minimized', 40)` (window_states.py), whose 3D view gets a hide event.
  - **Resolution: done.**
    - **Test:** the snippet records how each of its waits ended (`WAITS`), and a new judgement requires each to end on
      the view asking for a frame. It failed in a scratch run: `[False, False, False, False, True]`, the 3 notches and
      the middle drag at their limit.
    - **Cause:** the snippet gave every move a wait. The moves the Light tool ignores change nothing, so the hidden
      view asks for no frame.
    - **Fix:** the wheel and the middle drag go without a wait, and the comment says why. The turn, which moves the
      light, waits.
    - **Also covered:** `put_and_drag('qt minimized', 40)` wasn't measured, and stays as it was.
    - **Result:** passes in a scratch run: `[True]`, with the check's other judgements.
- [x] **TST-455 · Two bridge checks reach the state they test only by timing, and ROADMAP item 100 doesn't list them** · follows TST-421, generation 2, and HLP-150, generation 3 · `tests/test_all_tools/bridge/checks.py` (`check_no_job_starts_within_the_wait_after_the_one_before`, `check_a_wait_cancelled_leaves_nothing_connected`), `ROADMAP.md` (item 100) · confirmed · found 2026-11-16
  - **Defect.**
    - The queue check sends `behind` once the 0.3 s job is seen running. Nothing makes sure `behind` arrives before
      that job ends. Arriving after, it starts on an idle bridge, where the 30 ms rule holds too, so the check passes
      without testing a queued job's start.
    - The cancel check cancels once the status says a job runs. The status says so from the job's start, before the
      helpers' text has run and `_until` has connected. The cancel lands after that only because the second MCP
      client takes about a second to start. Landing earlier, CONNECTED=0 passes without testing the abort's
      disconnects, or `sys.mcp_selftest_source` is missing and the check fails.
    - Item 100 lists the live checks whose verdict load can change, and neither is there.
  - **Scenario.** Read in the code: a loaded machine, where `behind`'s round trip takes over 0.3 s.
  - **Fix.** Add both to item 100, with designs that don't depend on load: the long job loops until a marker file
    exists, made once `wait_for('1 queued')` returns True; the cancelled job writes a marker right before `_until`,
    and the cancel waits for it. No check is made stronger now (generation 3 for the cancel check).
  - **Resolution: done.** ROADMAP item 100 lists both checks, with designs that don't depend on load. No check changed
    (generation 3, for the cancel check).
- [x] **TST-456 · `test_waits.py` claims every fixed wait, but reads one line at a time and no `Event.wait`, so the front watch's 50 ms sampling isn't listed** · follows TST-426, generation 3 · `tests/unit/test_waits.py`, `tests/test_all_tools/window_server.py` (`FRONT_EVERY`) · confirmed · found 2026-11-16
  - **Defect.**
    - The docstring says every sleep, `_settle`, `.start(...)` given a time and single-shot timer after a number is
      a poll or listed. The test matches one line at a time, so a call that formatting splits over lines goes
      unseen. `lifecycle/designer_scripts/modal_dialog.py` already has a `QTimer.singleShot(` with its `0` on the
      next line.
    - It doesn't match `Event.wait(<seconds>)`. `FrontWatch` samples every `FRONT_EVERY` (0.05 s) through
      `self._stop.wait(FRONT_EVERY)`: a poll at 50 ms that is neither in POLLS nor listed. The other `.wait(...)`
      calls given a time wait for an event, with a limit.
    - `test_the_polls_look_every_100_ms` checks POLL_S, not `waits.TICK`, which POLLS accepts too.
  - **Scenario.** Read in the code.
  - **Fix.** Generation 3, tests only, so the claim gets smaller. The docstring says it reads calls written on one
    line, and not `Event.wait`. `FRONT_EVERY` gets the reason for its 50 ms in its comment, or becomes POLL_S. No
    check is added.
  - **Resolution: done (generation 3: the claim made smaller).** `test_waits.py`'s docstring says it reads calls
    written on one line, and neither a call split over lines nor `Event.wait(...)`, naming the front watch's sampling.
    `test_the_polls_look_every_100_ms`'s comment says TICK isn't read. `FRONT_EVERY` has its reason in a comment. No
    check was added. The test passes.
- [x] **TST-457 · Unit tests patch names the code no longer reads, and `end_own_designer`'s SIGKILL has no test** · follows TST-421, generation 2 · `tests/unit/test_selftest_lifecycle.py` (`test_ending_the_runs_designer_forces_only_its_own`), `tests/unit/test_selftest_alone.py:40`, `tests/unit/test_selftest_preparations.py:32`, `tests/unit/test_selftest_summary.py:99` · confirmed · found 2026-11-16
  - **Defect.**
    - TST-421 made `end_own_designer` wait with the server's `_exited`, which reads the server's `_designer_pids`
      (the conftest's `list`: none). The TST-170 test still patches `common.designer_pids` ("another run's is up"),
      `designer_alive` and `time.sleep`, which nothing reads now. `_exited(11, ...)` returns True at once, so the
      case the test was written for isn't set up.
    - No test makes `_exited` return False, so the SIGKILL line is untested. The newer test patches `_exited` to
      True.
    - TST-421 removed `category_run.PAUSE_S`. Three tests still set it, one with the comment "(slept in _cleaned)":
      `_cleaned` no longer sleeps.
  - **Scenario.** Read in the code. A change that sends SIGKILL whenever the server lists any Designer passes the
    TST-170 test.
  - **Fix.** Patch the server's `_designer_pids` to `[12]` (`patch_server`) and drop the dead patches. Add a case
    where `_exited` returns False, expecting `[(11, SIGTERM), (11, SIGKILL)]`. Remove the three PAUSE_S lines.
  - **Resolution: done.**
    - **Test:** `test_ending_the_runs_designer_forces_only_its_own`, now parametrized. The processes are given to the
      server's `_designer_pids`, which `_exited` reads, and the exit watch runs its limit. A case where 11 still runs
      expects SIGTERM, then SIGKILL. With TST-170's defect put back for a moment (SIGKILL whenever the server lists a
      Designer), the case with another run's Designer up failed. The old version's patches reached nothing.
    - **Fix:** the dead patches (`common.designer_pids`, `designer_alive`, `time.sleep`) removed, and the three
      PAUSE_S lines (`test_selftest_alone.py`, `test_selftest_preparations.py`, `test_selftest_summary.py`).
    - **Result:** passes. The three files' tests pass (94).
- [x] **TST-458 · Lifecycle's unit tests reach the real crash handlers and crash-dump folders again, and read the windows on screen** · TST-261's defect back · `tests/test_all_tools/crash_watch.py` (`CrashWatch.settle`), `tests/unit/test_selftest_lifecycle.py` (`_no_wait`, `_prepared`), `tests/test_all_tools/lifecycle/checks.py` (`check_launch_on_another_port`'s FrontWatch) · confirmed · found 2026-11-16
  - **Defect.**
    - SRV-151's crash wait added `coming` (`common.dumps_may_come`), and `settle` looks at it before its deadline:
      `while self.coming(ports, before) and self.clock() < deadline`. `_no_wait` and `_prepared` build the watch with
      `wait_s=0` but no `coming`.
    - So each settle with a step runs the real `dumps_may_come` once: a real `pgrep -fl crashpad_handler`. When a
      Designer an agent started runs on PORT, it also lists the real crash-dump folders, the user's included.
      `_no_wait`'s docstring says "no real crash-dump folder (REVIEW.md TST-261)".
    - On macOS, the tests that reach `check_launch_on_another_port`'s launch start a real `window_server.FrontWatch`:
      a thread reading the active app (`lsappinfo`) and the windows on screen.
    - All of it only reads, and no result depends on it.
  - **Scenario.** Read in the code: the unit suite run while `alone`'s Designer runs on 9877.
  - **Fix.** `settle` looks at the clock first, as `workers.wait_for_dumps` does. The fakes pass a `coming` that
    returns False. The tests patch `FrontWatch`.
  - **Resolution: done.**
    - **Test:** `test_selftest_crash_dumps.py::test_a_watch_with_no_time_to_wait_never_looks_whether_a_dump_may_come`
      failed: a watch with `wait_s=0` called `coming`. In `test_selftest_lifecycle.py`, `_windows_read` records each
      front watch entered, and the 3 cases that reach `check_launch_on_another_port`'s launch entered one watching.
    - **Cause:** `settle` looked at `coming` before its deadline, and the lifecycle tests left `coming` and `FrontWatch`
      real.
    - **Fix:** `settle` looks at its clock first. `_no_wait` and `_prepared` pass `_no_dump_coming`. The two tests make
      the check's front watch one that samples nothing (`_no_front_watch`).
    - **Also covered:** `workers.wait_for_dumps` already looks at the time first. The other unit tests that run
      `lifecycle.run` replace its checks with fakes, so they reach no front watch.
    - **Result:** passes, with the rest of both files.
- [x] **TST-459 · Vague types left in functions the diff adds or changes** · follows TST-452, generation 3 · listed below · confirmed · found 2026-11-16
  - **Defect.**
    - `tests/unit/test_lifecycle_env.py`, unmarked, in functions the diff changes: `**kw: Any` in the `begin`s at lines
      534, 1684 and 1742, and `request: dict[str, Any]` in `send` at line 1691. They fit `object` and
      `dict[str, object]`. TST-452's resolution narrowed two of each.
    - `mcp_server/designer_helpers/view3d.py`, `_drag`'s `pressed: list[Any]`: `list[tuple[Any, float, float]]`, as
      its marker describes it.
    - `tests/unit/test_frames3d.py`: `_frames_counting(...) -> tuple[Any, list[float]]`, `_comparing(frames: Any)` and
      five `cast(Any, frames)`, two of them unmarked, type `_Frames` as `Any`, "a helper loaded from its file". The
      same file gives `_Counts` a Protocol (`Counts`), so a `Frames` Protocol fits. `cast(Any,
      sys.modules['PySide6'])` fits `cast(mock.MagicMock, ...)`, as its reason says.
    - `tests/unit/test_shot3d.py`, `on_screen(...) -> Any  # Any: a helper's context`:
      `contextlib.AbstractContextManager[Screen]`, with a Protocol for what the tests call (`again`, `between`).
    - `tests/unit/test_selftest_frames_fact.py`, `checks() -> Any  # Any: a module imported by name`, and its five
      tests' `checks: Any`: `ModuleType`, as `test_selftest_window_server.py` types its module.
    - `tests/unit/test_selftest_window_server.py`: `windows: tuple[object, ...]` (line 274), the window tuples the
      file's other tests type; `rect: tuple[float, ...]` (line 24), `tuple[float, float, float, float]`.
  - **Scenario.** Read in the code.
  - **Fix.** As listed.
  - **Resolution: done.** As listed:
    - `test_lifecycle_env.py`'s four, `object` and `dict[str, object]`;
    - `_drag`'s `pressed: list[tuple[Any, float, float]]`;
    - `test_frames3d.py`'s `Frames` Protocol, with `_counted` for the reads that need a count shown, and
      `cast(mock.MagicMock, ...)`;
    - `test_shot3d.py`'s `on_screen(...) -> contextlib.AbstractContextManager[Screen]`, with a `Screen` Protocol;
    - `test_selftest_frames_fact.py`'s `ModuleType`;
    - `test_selftest_window_server.py`'s window tuples and `rect`.
    mypy strict passes.
- [x] **SRV-166 · `quit_designer`'s "could not be ended" error leaves out that the crash reports may still be uploaded** · follows SRV-124, generation 3 · `mcp_server/server_tools/lifecycle.py` (`_quit`, `_end_if_past_startup`) · confirmed · found 2026-11-16
  - **Defect.**
    - `_quit` puts the uploads line in `prefix`. Every return carries `prefix`, but the raise doesn't:
      ```python
      prefix = ''.join(line + '\n' for line in (notes, uploads) if line)
      ...
      raise ToolError(_could_not_end(own) + sampled)
      ```
    - `_end_if_past_startup` adds the uploads sentence right after the sample's path, which ends with no stop:
      `sampled + uploads` reads "... threads_N.sample.txt Its crash reports may still be uploaded to Adobe: ...".
  - **Scenario.** Read in the code. A Designer an agent started crashes as it quits, and Adobe's crash window keeps
    its process (ROADMAP item 95), so the quit can't end it. If its Crashpad settings couldn't be written, the error
    doesn't say its crash report may go to Adobe. SRV-124 said "with a line when it can't", and DECISIONS.md's crash
    uploads entry relies on it. The close's notes are dropped the same way.
  - **Fix.** `raise ToolError(prefix + _could_not_end(own) + sampled)`, and `_sentence(sampled)` before the uploads
    sentence. A unit test for each path.
  - **Resolution: done.**
    - **Test:** `test_a_quit_that_cant_end_its_designer_says_its_crash_reports_may_be_uploaded` failed: no uploads
      line. `test_an_agents_designer_ended_past_its_start_up_says_its_sample_then_its_uploads_each_a_sentence`, ended
      and not, failed: "threads_11.sample.txt Its crash reports".
    - **Cause:** `_quit`'s raise left out `prefix`, which every return carries; `_end_if_past_startup` joined the
      sample's sentence, which ends with its path, to the next.
    - **Fix:** the raise carries `prefix` (the close's notes, the uploads line); the sample's sentence gets its stop
      (`_sentence`) when the uploads sentence follows.
    - **Also covered:** `_quit`'s returns put `sampled` last, after `prefix`.
    - **Result:** passes.
  - Questioned by SRV-168 (2026-11-16).
  - Questioned by SRV-169 (2026-11-16).
- [x] **SRV-167 · GUIDE.md and `_reload_package_file` say no pause is needed between unload, load and reopen, measured in hidden Designers only** · follows SRV-150, generation 2 · `mcp_server/GUIDE.md` (the file-level edit pattern), `mcp_server/server_tools/layout.py` (`_reload_package_file`'s docstring) · confirmed · found 2026-11-16
  - **Defect.** GUIDE.md says "an unload's widgets were all gone by the next call, so no pause is needed". The
    docstring says the same, citing link_display's designer fact. That fact, like every self-test run, runs in a
    Designer opened hidden. The crash the three separate calls guard against was in a Designer on screen. Whether an
    unload there finishes its teardown before the next call is the first review's Not verified, and this one's.
  - **Scenario.** Read in the docs. An agent writing a script with the file-level edit pattern for the user's
    Designer, which is on screen, reads that no pause is needed.
  - **Fix.** Say where it was measured: in Designers opened hidden, not in one on screen.
  - **Resolution: done.**
    - **Measured** with the user's go (this review's log, Not verified): on screen, not the active app, link_display's
      fact read as hidden, 5 of 5, and 20 reloads raised nothing and left no crash dump.
    - **Fix:** GUIDE.md and `_reload_package_file`'s docstring say where it was measured: hidden, and on screen but not
      the active app.
    - **Result:** the docs tests pass.
- [x] **INS-37 · `read_crash_dump.py` reads dumps from folders in /tmp without checking they are the user's own** · `scripts/read_crash_dump.py` (`dump_folders`) · confirmed · found 2026-11-16
  - **Defect.** `agent_designer_folders()` lists the names in the shared /tmp that match `sd_mcp_<uid>_<port>`.
    `dump_folders()` looks for dumps in each, with no check that the folder is this user's and not a link:
    ```python
    homes = [os.path.expanduser('~')] + [os.path.join(folder, 'home') for folder in agent_designer_folders()]
    ```
    The server reads these folders only through `_checked_folder` (lstat, a folder, the user's uid; REVIEW.md
    SRV-96), and `uninstall.plan()` checks them the same way.
  - **Scenario.** Read in the code. Another account on the Mac makes `/tmp/sd_mcp_<the user's uid>_<port>` first,
    with a dump newer than any real one and a log beside it. Run with no argument, as AGENTS.md tells agents to after
    a crash, the script prints that dump's messages and that log. An agent diagnosing a crash then reads text another
    account wrote. Nothing of the user's changes.
  - **Fix.** In `dump_folders()`, keep only the folders that are this user's own and not links, as
    `uninstall.plan()` does. A unit test with a link, and one with a folder of another uid.
  - **Resolution: done.**
    - **Test:** `test_a_folder_in_tmp_that_isnt_the_users_own_isnt_read`, with a link and a folder of another uid:
      both were read.
    - **Cause:** the folders were matched by name alone.
    - **Fix:** `dump_folders()` keeps the agents' folders that are this user's own and not links (`_own_folder`, as
      the server's `_checked_folder` and uninstall.py check).
    - **Also covered:** `common.crash_dumps` reads only this run's ports' folders, which `launch_designer` made and
      checked.
    - **Result:** passes.
  - Questioned by INS-38 (2026-11-16).
- [x] **HLP-171 · An abort landing on `_3d_render`'s `finally` skips putting the user's clipboard text back** · follows HLP-150, generation 3 · `mcp_server/designer_helpers/screenshots.py` (`_3d_render`) · confirmed · found 2026-11-16
  - **Defect.** The plugin's tracer raises its abort at a traced line: every 64th event, or the first one after an
    abort dropped in a slot. Raised at a `finally`'s first line, it skips the rest of that `finally` (HLP-150):
    ```python
    finally:
        clipboard.setMimeData(backup)
        app.processEvents()
    ```
    The window code guards the same case with a handler that runs untraced: `_on_screen`'s and `_3d_set_up`'s
    `except BaseException`.
  - **Scenario.** Read in the code and the plugin's `_make_tracer`. A job is cancelled, or times out, as a render
    returns. The abort lands on `clipboard.setMimeData(backup)`, and the render stays on the user's clipboard
    instead of their text. DECISIONS.md's clipboard entry rests on the text coming back. A shot can take several
    renders now: the retakes, and the steps compared by renders where no count shows.
  - **Fix.** An outer `except BaseException:` that puts the backup back unless a flag says the `finally` did, as
    `_on_screen` does for the window. A unit test with the abort at that line.
  - **Resolution: done.**
    - **Test:** `test_an_abort_landing_on_the_renders_put_back_of_the_clipboard_still_puts_the_users_text_back`, a
      trace function raising at the `finally`'s first line as the plugin's does: nothing was put back.
    - **Cause:** the plugin raises an abort at a traced line, then stops tracing; landed on the `finally`'s first line,
      the rest of it didn't run.
    - **Fix:** an outer `except BaseException:`, which runs untraced, puts the text back unless the `finally` did. Each
      put-back is a QMimeData of its own, so twice is harmless.
    - **Also covered:** the helpers' other put-backs of the user's state have such a handler: the window
      (`_on_screen`), the tool and the mouse button (`_3d_set_up`), the Parameters panel (HLP-118).
    - **Result:** passes.
  - Questioned by HLP-177 (2026-11-16).
- [x] **HLP-172 · A window put on screen again within one look stays transparent though the user is in Designer, and its line drops ", transparent"** · follows HLP-163, generation 5 · `mcp_server/designer_helpers/shot3d.py` (`_Screen._bring`) · confirmed · found 2026-11-16
  - **Defect.** `_bring` calls itself when the window went off screen again during its wait, without `between()`:
    ```python
    fade = not self._taken_up()
    print(WINDOW + (BROUGHT[way][again] if fade else BROUGHT[way][again].replace(', transparent', '')))
    ...
    self._bring(again=True, brings=brings - 1)
    ```
    Once the user has made Designer the active app, `fade` is False: nothing more is faded, and the line says the
    window is shown without ", transparent". The windows the first bring faded stay in `_faded`, still transparent:
    only `between()` gives their look back.
  - **Scenario.** Read in the code. During the first bring's wait, the user switches to Designer and minimizes it
    (Cmd-M). The window comes back transparent, and its line says it isn't. The user sees nothing of Designer until
    the next step's look or the put-back, against HLP-136's "made opaque at once".
  - **Fix.** `self.between()` before the recursive `_bring`. A unit test: `Covering`, with the app made active
    during `shown`.
  - **Resolution: done.**
    - **Test:** `test_a_window_put_on_screen_again_within_one_look_once_the_user_is_in_designer_is_made_opaque_first`
      failed: "left transparent, the user in Designer".
    - **Cause:** the bring called itself without the look that gives the windows their look back.
    - **Fix:** `between()` before the recursive bring.
    - **Result:** passes.
- [x] **HLP-173 · The shot's window waits: a measured time decides the second show, and the minimize and hide waits aren't woken by the events Qt sends for them** · follows HLP-145 and HLP-160, generation 2 · `mcp_server/designer_helpers/shot3d.py` (`SHOW_AGAIN`, `_wait_on_screen`, `_Screen._wait_off_screen`), `mcp_server/designer_helpers/mac_window.py` (`_wait_unhidden`) · measured · found 2026-11-16
  - **Defect.**
    - `SHOW_AGAIN = 0.5` puts the window in front again once it isn't exposed 0.5 s after the show; the exposure
      took about 0.3 s where measured. A time measured here decides it, against AGENTS.md's wait rule. HLP-160's fix
      has since removed the cause that fits HLP-145's readings, and nothing says whether the second show still
      happens.
    - `_wait_off_screen` and `_wait_unhidden` look at macOS's state every TICK and as the page's expose events come.
      Their docstrings record a hunt for a callback in Qt's signals only.
  - **Scenario.** Measured (2026-11-16) in a Designer opened hidden, its window on screen transparent and
    click-through, over 2 minimizes and 2 hides, each brought back with the shot's `again()`, polled every 10 ms:
    - The page's and the top-level window's `windowStateChanged` and `visibleChanged`, and `applicationStateChanged`,
      never fired.
    - The top-level widget (`mw.window()`, a QStackedWidget) got a Hide event 0.60 to 0.61 s after each minimize.
      macOS said it minimized, and the window server no longer listed it, at the next look (0.62 to 0.63 s).
    - It got a Hide event 0.002 s after each hide. macOS said Designer hidden at 0.005 s, and the window server
      stopped listing the window at 0.023 to 0.025 s.
    - It got a Show event 0.044 to 0.058 s into each `again()`, which ended at 0.058 to 0.103 s.

    On a slower or busier machine, an exposure later than 0.5 s gets a second show it didn't need.
  - **Fix.** Wake both waits on the top-level widget's Hide and Show events too (`_event_signal(mw.window(), ('Hide',
    'Show'))`), keeping the poll for the window server's list, which lags the hide's event by 0.02 s. AppKit's
    notifications (`NSApplicationDidHideNotification`, `NSApplicationDidUnhideNotification`,
    `NSWindowDidChangeOcclusionStateNotification`) are the next candidates. For SHOW_AGAIN: measure whether the
    second show still happens since HLP-160. Remove it if it never does, or wake it on what says the window is
    still covered.
  - **Resolution: done.**
    - **Measured first** (2026-11-16, in Designers an agent started, windows transparent and click-through):
      - the second show: over 30 shots of a hidden Designer in 10 Designers just started, the window was exposed at
        its first show in 60 of 60 waits, each 0.002 to 0.026 s;
      - callbacks: no Qt signal fired for a hide or a minimize (both windows' `windowStateChanged` and
        `visibleChanged`, `applicationStateChanged`). The top-level widget's Hide and Show events came for a
        minimize and its look after, and in a Designer just started not for a hide right after the shot showed it,
        nor its look after.
    - **Test:** `test_a_window_not_yet_on_screen_after_a_while_is_put_in_front_again_once` failed: a wait of 0.5 s
      before the second show.
    - **Cause:** HLP-145's fix put the window in front again after a time measured then; HLP-160's wait for the unhide
      removed the cause that fits its readings.
    - **Fix:** SHOW_AGAIN is gone: the window is put in front again only once the wait's limit, ON_SCREEN_WAIT, has
      passed, then refused after it again. The waits keep the poll, as no Qt callback says the states; shot3d.py's
      docstring records both measurements. AppKit's notifications: ROADMAP item 101.
    - **Result:** passes; the focus check's hidden way and the other window checks pass in the category's scratch run
      (96 of 96 checks in the category's scratch run, in a Designer just started).
  - Questioned by HLP-178 (2026-11-16).
- [x] **HLP-174 · Two docstrings of the 3D set-up's waits say what the code doesn't do** · follows HLP-168, generation 5 · `mcp_server/designer_helpers/view3d.py` (`_3d_set_up`'s and its `run`'s docstrings), `mcp_server/designer_helpers/frames3d.py` (the module docstring, the bullet on the show) · confirmed · found 2026-11-16
  - **Defect.**
    - `_3d_set_up` says "Run without the shot's watch, the viewpoint's turn and Frame run with the window on screen,
      transparent (_on_screen)", and `run` says "on `frames`, the shot's watch of its frames, or one of its own".
      Since HLP-168, `set_3d_view` with a move passes a watch of its own. Its turn then gets no `_on_screen` of its
      own, as `set_3d_view` already runs inside one. What the code relies on is a caller that passes `frames` already
      keeping the window on screen and passing its look as `between`.
    - frames3d.py, on the show: "With no count to read, renders are compared ...: a change seen, then two renders
      alike". `shown()` passes `changed=False`, so it ends at the first two renders alike, no change seen.
  - **Scenario.** Read in the code.
  - **Fix.** Narrow both (the chain rule): "a watch from a caller that keeps the window on screen and passes its
    look as `between`: the shot, or set_3d_view with a move"; "two renders alike (after a step, a change seen
    first)".
  - **Resolution: done.**
    - **Fix:** `_3d_set_up`'s and `run`'s docstrings name the contract: a caller giving its watch keeps the window on
      screen and passes its look as `between`, the shot or set_3d_view with a move. frames3d.py's show bullet says two
      renders alike, no change needed first.
    - **Result:** lint and types pass.
- [x] **HLP-175 · `Any` without its reason in five functions view3d.py adds** · `mcp_server/designer_helpers/view3d.py` (`_navigation_tools`, `_tool_back`, `_mouse`, `_mouse_guard`, `_release`) · confirmed · found 2026-11-16
  - **Defect.** AGENTS.md keeps an `Any` only when it is marked with its reason on its line; screenshots.py's module
    comment isn't that mark (HLP-129). These have none:
    - `def _navigation_tools(dock: Any, keep: list[Any]) -> tuple[Any, Any]:`, whose `keep` is the caller's
      `list[object]`;
    - `def _tool_back(light: Any, switched: bool)`;
    - `def _mouse(viewport: Any, kind: Any, x: float, y: float, button: Any, buttons: Any)`;
    - `def _mouse_guard() -> Any:`;
    - `def _release(viewport: Any, button: Any, x: float, y: float)`.

    `_drag`, beside them, has its mark.
  - **Scenario.** Read in the code (DECISIONS.md, vague types: reported in the functions a branch's diff adds).
  - **Fix.** `keep: list[object]`, and on the others' lines the mark `_drag` has (`# Any: a Qt widget ...
    (screenshots.py)`).
  - **Resolution: done.**
    - **Fix:** `keep: list[object]`; the five functions marked `# Any:` with their Qt types, as `_drag` is.
    - **Result:** lint and types pass.
- [x] **TST-461 · `Any` without its reason, and containers vaguer than known, in the test code the range adds** · `tests/unit/minidumps.py`, `tests/unit/test_read_crash_dump.py`, `tests/unit/test_selftest_alone.py`, `tests/unit/test_selftest_lifecycle.py`, `tests/unit/test_selftest_crash_dumps.py`, `tests/unit/test_selftest_pool.py`, `tests/unit/test_view3d.py`, `tests/unit/test_view3d_helpers.py`, `tests/test_all_tools/workers.py`, `tests/test_all_tools/editor_panels_and_fit/designer_scripts/tool_3d.py` · confirmed · found 2026-11-16 · found by four reviewers
  - **Defect.** Unmarked, where a narrower type fits (AGENTS.md's typing rules):
    - minidumps.py: `an_abort(**kw: Any)` and `defaults: dict[str, Any]`, which are `Crash`'s fields: a
      `total=False` TypedDict with `Unpack`, or the mark;
    - test_read_crash_dump.py: `_said(path: Path, **kw: Any)`, whose callers pass only `name_frames`,
      `Callable[[str, int, list[int]], list[str]]`;
    - test_selftest_alone.py: `CrashesAsItQuits.__init__(folder: Any)` (`Path`), its `dumps(ports: Any = ())`
      (`Collection[int]`), `_watching(alone: Any)` (`ModuleType`), and `tmp_path: Any` in the three close tests
      (`Path`);
    - test_selftest_lifecycle.py: `lifecycle: Any` in `_windows_read`, `_no_front_watch` and `_prepared`
      (`ModuleType`), `_no_dump_coming(ports: Any)` (`Sequence[int]`), `_no_wait -> list[Any]`, and
      `dict[str, Any]` in the two `test_the_check_on_another_port_*` tests (`dict[str, object]`);
    - test_selftest_crash_dumps.py: `_users_folders(common: Any)` (`ModuleType`);
    - test_selftest_pool.py: `dumps(ports: Any = ())` (`Collection[int]`);
    - test_view3d.py: `value: Any`, widened from `float`: marked, since it goes to parameters of several types;
    - test_view3d_helpers.py: `_tool(...) -> Any` (`SimpleNamespace`), `options: dict[str, Any]` twice
      (`dict[str, object]`), and `object` or the drag record's tuple in `tool_back`, `released`, `Mouse.pressed`,
      `Mouse.held`, `Mouse.mouse`, the two `pressed: list[Any]` and `send`;
    - workers.py: `_quit_to_keep(part: Mapping[str, object])`, only ever given a `WorkerResults`;
    - tool_3d.py: `ARGS: dict[str, Any]` (`dict[str, str | bool]`), and `mw: Any` with no mark.
  - **Scenario.** Read in the code (DECISIONS.md, vague types).
  - **Fix.** Narrow each as listed, or mark it `# Any: <reason>`.
  - **Resolution: done.**
    - **Fix:** narrowed: `_said`'s `name_frames` callable; `Path`, `Collection[int]`, `Sequence[int]`, `ModuleType`,
      `dict[str, object]`, `list[object]` and `SimpleNamespace` in the tests listed; `_quit_to_keep(part:
      WorkerResults)`; tool_3d.py's ARGS a `TypedDict`. Marked where nothing narrower is checked: `an_abort`'s
      `**kw` (Crash's fields, which `dataclasses.replace` checks by name), `test_options_out_of_range_are_refused`'s
      `value`, tool_3d.py's main window, `_no_wait`'s fresh CrashWatch.
    - **Result:** lint and types pass.
  - Questioned by TST-476 (2026-11-16).
- [x] **TST-462 · ROADMAP item 100's list of verdicts that depend on time leaves out three** · `ROADMAP.md` (item 100), `tests/test_all_tools/editor_panels_and_fit/checks.py` (`POPUP_MS`, `check_a_3d_shots_window_shown_again_mid_accumulation_waits_for_the_count_at_rest`, FRAMES) · confirmed · found 2026-11-16
  - **Defect.**
    - The menu check wants Designer's popup on screen at most `POPUP_MS = 20` ms during a shot; 9 ms is the most
      measured.
    - The mid-accumulation check counts a try only if Designer was hidden at a count of 3 or less, and needs 3 such
      tries of 6. How many qualify depends on timing.
    - The frames fact wants each hidden pan's UpdateRequest within a 1 s `_until`.
  - **Scenario.** Read in the code. Under the full run's load, the menu's flash lasts past 20 ms, or fewer than 3
    tries are hidden low, and a check fails while the tool works. Item 100 lists such checks so each is made to
    judge what happened.
  - **Fix.** Add the three to item 100's list.
  - **Resolution: done.**
    - **Fix:** item 100 lists the three.
- [x] **TST-463 · The mid-accumulation check waits out SETTLE_LIMIT in a try that misses the low count, and reads the count before the hide** · follows HLP-167, generation 6 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`SHOWN_FROM_LOWER`, `check_a_3d_shots_window_shown_again_mid_accumulation_waits_for_the_count_at_rest`) · confirmed · found 2026-11-16
  - **Defect.**
    - `_until(low, SETTLE_LIMIT, [frames._spy.fired])` waits for a count of 3 or less. When the count passes 3
      before `low` looks (1 try in 6, says the check's docstring), `low` never comes true, and the wait runs its 3 s
      limit: a limit used as the wait's time (AGENTS.md).
    - `hidden_at = frames.count()` is read before `mac.hide()`, and the off-screen wait's result isn't checked. The
      docstring says "Designer hidden as the count read 3 or less".
  - **Scenario.** Read in the code.
  - **Fix.** End `low` also once the count is back at the target after the restart, so that a missed try ends at
    once. The docstring says the count is read just before the hide. No check is added or made stronger (the chain
    rule).
  - **Resolution: done.**
    - **Fix:** `low()` also ends once the count is back at the target after the restart, so a try that missed the low
      count ends at once and is hidden there, not judged. The docstring and the snippet's comment say the count is
      read just before the hide.
    - **Result:** passes in the category's scratch run (96 of 96 checks in the category's scratch run, in a Designer just started).
- [x] **TST-464 · Two window checks take a try again and keep only the last try's evidence** · follows TST-418 and TST-453, generation 4 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_a_3d_shot_puts_designers_window_on_screen_without_taking_focus`, `check_a_hidden_designers_window_is_brought_in_front_for_a_3d_shot_once_its_unhide_took`) · confirmed · found 2026-11-16
  - **Defect.**
    - The focus check takes a way again, up to TRIES times, while Designer became the active app (TST-418). The
      unhide check takes a try again while a window is in front of Designer's. A pass prints only the number of
      tries, not what the earlier tries saw.
    - TST-418's reason, "the pool's other Designers can hand it activation", has weakened: they start hidden now,
      and both checks read under `no_designer_starting()`.
    - HLP-160's defect came and went: 19 tries of 19 one day, then none of 2 (shot3d.py's docstring).
  - **Scenario.** Read in the code. A regression that takes focus, or leaves the window behind, in one try of two
    passes, and only "2 tries" says something happened.
  - **Fix.** Print each retaken try's reason (the activation lines, or `who` of the windows in front), and say in
    both docstrings that a defect seen in fewer than TRIES tries passes. No check is added or made stronger (the
    chain rule).
  - **Resolution: done.**
    - **Fix:** both checks print each retaken try's reading after their result (the activation and what the shot said
      of it; the windows in front), and their docstrings say a defect seen in fewer than TRIES tries passes.
    - **Result:** passes in the category's scratch run (96 of 96 checks in the category's scratch run, in a Designer just started).
- [x] **TST-465 · Docstrings of the self-test and its unit tests that say more than their checks do** · follows HLP-168 and TST-420, generation 5 · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_the_camera_moves_under_the_light_tool_too`, `check_set_3d_view_moves_the_camera_as_a_3d_shots_set_up_does`), `tests/test_all_tools/editor_panels_and_fit/designer_scripts/tool_3d.py`, `tests/test_all_tools/editor_panels_and_fit/window_states.py` (the module docstring, `put_and_drag`), `tests/unit/test_view3d_helpers.py` (`Mouse`, `test_a_drag_is_a_press_moves_and_a_release_from_the_middle_then_a_pause_all_guarded`) · confirmed · found 2026-11-16
  - **Defect.**
    - The Light tool check says "so zoom, orbit and pan move it under the Camera tool". It takes a zoom and a pan,
      no orbit.
    - HLP-168's check says set_3d_view "puts Designer's window on screen, transparent". It judges
      `"Designer's window: " in said`, any window line.
    - tool_3d.py says "'' selects none". With '', it selects nothing new and reads the tool selected. The Light tool
      check relies on that, reading 'TOOL=Light' after the zoom.
    - window_states.py says the 'qt minimized' way "stops the drawing too", and `put_and_drag` says "the view not
      drawn". TST-420 measured a page Qt minimized drawing in some runs and not others, and TST-433 found covered
      windows drawn in some Designers; shot3d.py says so.
    - test_view3d_helpers.py: `Mouse`'s "'pause' (x the seconds)", the test's name and its comment on the pause. A
      drag now ends on the wait for the view, which the test asserts; no pause is recorded.
  - **Scenario.** Read in the code.
  - **Fix.** Narrow each to what is checked (the chain rule): "zoom and pan"; "puts Designer's window on screen";
    "'' leaves the tool as it is"; "which may stop the drawing"; the test renamed for the wait, its words too.
  - **Resolution: done.**
    - **Fix:** each narrowed to what is checked: "zoom and pan"; "puts Designer's window on screen"; "'' leaves the
      tool as it is"; the Qt-minimized page and `put_and_drag` "may" draw; the drag test renamed for the wait for the
      view, `Mouse`'s docstring and the comment with it.
    - **Result:** the tests pass.
- [x] **TST-466 · `alone.close()` waits its whole 10 s for a crash dump after every quit that leaves none** · follows SRV-151, generation 2 · `tests/test_all_tools/alone.py` (`close_with`, `CLOSE_DUMP_WAIT_S`) · confirmed · found 2026-11-16
  - **Defect.** `common.new_crash_dumps(before, CLOSE_DUMP_WAIT_S)` returns early only when a dump appears. After a
    normal quit, the limit is the wait's time (AGENTS.md's wait rule). SRV-151 moved the run's other crash waits
    onto the crash handler's end (`common.dumps_may_come`). This one, added in ec984a9, stayed timed. The third
    review dropped it as main's code, but it is in this range.
  - **Scenario.** Read in the code. Every `alone.close()` takes 10 s more than its quit, also when
    `designer_status` erred and nothing ran.
  - **Fix.** Wait while `common.dumps_may_come([], before)`, every POLL_S, CLOSE_DUMP_WAIT_S at most, then take
    the new dumps. A unit test with `dumps_may_come` faked, as the pool's has.
  - **Resolution: done.**
    - **Test:** `test_close_after_a_quit_that_leaves_no_dump_waits_only_while_one_may_come` failed: the wait never
      asked whether a dump may come.
    - **Cause:** `alone.close()` kept `new_crash_dumps`' timed wait when SRV-151 moved the others.
    - **Fix:** it waits while `common.dumps_may_come([], before)`, every POLL_S, CLOSE_DUMP_WAIT_S at most (a safety
      net), then takes the new dumps. The crash tests' fake says a dump may come until it is written.
    - **Also covered:** `__main__`'s wait after a run in the user's Designer stays timed: their Designer keeps running,
      so its crash handler says nothing (main's code).
    - **Result:** passes; each `alone.close()` since took its quit's time.
- [x] **TST-467 · The pool's launch lock is said to stop every Designer of the run starting or quitting; lifecycle's own launches and quits go on** · follows TST-417 and TST-453, generation 4 · `tests/test_all_tools/editor_panels_and_fit/retries.py` (the module docstring, `no_designer_starting`), `tests/test_all_tools/launch_lock.py` (the module docstring, `held`), `tests/test_all_tools/workers.py` (its rules) · confirmed · found 2026-11-16 · found by two reviewers
  - **Defect.**
    - `no_designer_starting` says "no Designer of the run starts or quits meanwhile, so none brings windows in front
      or hands activation over". TST-417's resolution and TST-453's note say the same.
    - The lock holds off only the pool's starts (`Gate.try_begin`) and the workers' last quits
      (`launch_lock.changing`). lifecycle's own `launch_designer` and `quit_designer` calls outside its two
      `held(own='lifecycle')` windows take no mark: about ten in `check_quitting_and_starting_again`, and the second
      Designer of `check_launch_on_another_port`. lifecycle runs beside editor_panels_and_fit in the pool.
    - `launch_lock.py`'s docstring, `held()`'s "lifecycle's side" and `workers.py`'s rules still name lifecycle as
      the only holder.
    - retries.py's module docstring says the pool's Designers come in front as they start, which they no longer do
      since they start hidden (SRV-152).
  - **Scenario.** Read in the code. A window check reads `in_front` or the activation while lifecycle quits or
    launches its Designer.
  - **Fix.** Narrow the docstrings (the chain rule): the lock holds off the pool's starts and its workers' quits,
    while lifecycle's own launches and quits, and other scratch runs, go on. Name editor_panels_and_fit as a holder
    in `launch_lock.py` and `workers.py`.
  - **Resolution: done.**
    - **Fix:** retries.py, launch_lock.py (its holders listed: lifecycle, editor_panels_and_fit), workers.py and the
      checks' docstrings say what the lock holds off: the pool's starts and its workers' quits, lifecycle's own
      launches and quits going on. retries.py says the pool's Designers came in front as they started before SRV-152.
    - **Result:** lint passes.
- [x] **TST-468 · `stayed_behind`'s detail doesn't say how many samples read the active app** · follows TST-441, generation 3 · `tests/test_all_tools/window_server.py` (`stayed_behind`) · confirmed · found 2026-11-16
  - **Defect.** TST-441's resolution: "both return False when no sample read the active app, and say how many
    did". `stayed_off_screen` says it. `stayed_behind` counts `read`, then leaves it out of its detail.
  - **Scenario.** Read in the code. `lsappinfo` fails at every sample, and `check_designer_stayed_behind` fails with
    a detail of zeros, "the active app 0.00 s, its window in front of another app's 0.00 s", which reads as a pass.
  - **Fix.** Add the count to the detail. No check is added or made stronger (the chain rule).
  - **Resolution: done.**
    - **Test:** `test_stayed_behinds_detail_says_how_many_samples_read_the_active_app` failed: no count.
    - **Fix:** the detail says how many samples read the active app.
    - **Result:** passes.
- [x] **TST-469 · A unit test of the popup watch sleeps 0.1 s, then wants more than 10 samples** · follows TST-426, generation 3 · `tests/unit/test_selftest_popups.py` (`test_the_watch_samples_the_window_list_and_sees_no_popup_of_a_process_with_none`) · confirmed · found 2026-11-16
  - **Defect.** `time.sleep(0.1)`, then `assert watch.samples > 10 ...`: a fixed sleep (AGENTS.md's wait rule), and
    a count that depends on how fast the window server answers. TST-426 fixed the same pattern in the window
    server's test.
  - **Scenario.** Read in the code. In a full run, the unit suite runs beside four Designers. The window server
    takes longer than 9 ms a sample, and the test fails while the watch works.
  - **Fix.** Drop the count (the chain rule), or look at `watch.samples` every 0.1 s until it passes 10, with a
    limit, as `test_the_front_watch_samples_the_active_app_and_the_windows_on_screen` does.
  - **Resolution: done.**
    - **Fix:** the test looks at `watch.samples` every 0.1 s until it passes 10, 10 s at most; it runs at every layer
      too, as the watch now takes one (TST-472).
    - **Result:** passes.
- [x] **TST-470 · No test pins that `to_back` makes Designer's windows transparent before it shows them** · `tests/test_all_tools/editor_panels_and_fit/window_states.py` (`to_back`), `tests/unit/test_selftest_window_states.py` (`test_the_ways_off_the_users_screen_are_set_up_behind_every_window`) · confirmed · found 2026-11-16
  - **Defect.** `to_back` fades the windows, then unhides, un-minimizes and restores the page, then orders them
    back. The unit test pins only that `to_back()` comes first, and `window()`'s order:
    ```python
    assert behind.lstrip().startswith('to_back()')
    ```
    Moved after the unhide, `fade(True)` would show Designer's windows opaque near the front until the
    `orderBack:` (DECISIONS.md, Designer during tests). The front watch samples every FRONT_EVERY plus two
    `lsappinfo` runs, so it catches such a flash only some of the time.
  - **Scenario.** Read in the code. An edit moves `fade(True)` below the unhide. Every unit test still passes, and
    full runs fail only some of the time.
  - **Fix.** Pin `to_back`'s order in the unit test, as `_CLEAR`'s test does: `fade(True)` before the unhide, the
    de-miniaturize and Qt's restore.
  - **Resolution: done.**
    - **Test:** `test_to_back_makes_designers_windows_transparent_before_it_shows_them_and_leaves_them_so` pins the
      order: `fade(True)` before the unhide, the de-miniaturize and Qt's restore; `orderBack:` after the wait; no
      `fade(False)` inside. It passed on the code, which was right; with `fade(True)` moved after the unhide, a mutant
      made for the run and then removed, it failed (`61 < 44`).
    - **Cause:** the pin covered `window()`'s order and `_CLEAR`'s, not `to_back`'s.
    - **Fix:** the test above.
    - **Result:** passes.
- [x] **TST-471 · The front watch covers the window checks only; the 3D checks before them put Designer's window on screen unwatched** · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`run`), `tests/unit/test_selftest_window_states.py` (the watch's pin) · confirmed · found 2026-11-16
  - **Defect.** `run()` starts `window_server.FrontWatch` after about 25 checks that put a hidden Designer's window
    on screen: every 3D shot (`with_checker`), the frames fact's and SHOWN_FROM_HIDDEN's `_on_screen`, and the
    material dialog's unhide. The unit test pins the watch around the checks that use `window_states` only.
    DECISIONS.md: no window of an agent's Designer comes in front of the user's unless a check needs it there.
  - **Scenario.** Read in the code. A regression that leaves one of those windows opaque in front passes every full
    run. The material check once left Designer over the user's windows for about 10 s (the log of the three full runs
    of 2026-11-15).
  - **Fix.** Start the watch at the first 3D check. A check that needs a window in front there moves after it, as
    the in-front group does.
  - **Resolution: done.**
    - **Test:** `test_the_window_checks_off_screen_are_watched_and_those_in_front_run_after_together` wants no check
      awaited before the watch: it failed, listing the 3D checks.
    - **Cause:** the watch began at the window checks; the 3D checks before them put the window on screen too.
    - **Fix:** `run()` starts the front watch before its first check, and judges it right after the window checks off
      screen, as before; its docstring says so.
    - **Result:** passes; in the category's scratch run `check_designer_stayed_behind` passed over every check up to
      it (96 of 96 checks in the category's scratch run, in a Designer just started).
  - Questioned by TST-473 (2026-11-16).
- [x] **SRV-168 · An agent's Designer ended past its start-up: the stop SRV-166 puts after the sample's path reads as part of the path** · follows SRV-166, generation 4 · `mcp_server/server_tools/lifecycle.py:895-912` (`_end_if_past_startup`), `tests/test_all_tools/lifecycle/samples.py:32` (`sampled`) · confirmed · found 2026-11-16
  - **Defect.**
    - When the uploads sentence follows, SRV-166 ends the sample's sentence with a stop. That sentence ends with the
      sample's path:
      ```python
      if sampled and uploads:  # the sample's sentence ends with its path: a stop before the next (REVIEW.md SRV-166)
          sampled = ' ' + _sentence(sampled.strip())
      ```
      The result then reads "... threads_11.sample.txt. Its crash reports may still be uploaded to Adobe: ...".
    - The self-test takes the path to be everything up to the next space, so the stop becomes part of it:
      ```python
      found = re.search(re.escape(QUIT_SAMPLED) + r' (\S+)', result)
      ```
      An agent copying the path gets the stop too.
    - `_quit` has no such stop: its uploads line comes first, in `prefix`, and the sample's sentence last.
    - The docstring says the function returns "_sampled_before_force's sentence ('' when no sample was tried)". It
      returns the uploads sentence after it too, and the uploads sentence alone when no sample was tried.
  - **Scenario.** Read in the code. `launch_designer` ends an agent's Designer that isn't answering past its start-up,
    and that Designer's Crashpad settings can't be written (missing, or another version). `sampled()` takes
    `threads_11.sample.txt.`, which isn't a file, so lifecycle's check of the sample (`checks.py:747`) finds none.
  - **Fix.** Put the uploads sentence first, as `_quit` does: `uploads + sampled`, and
    `_could_not_end(own) + uploads + sampled` in the raise, without the `_sentence` step. The docstring says it returns
    the uploads sentence, then the sample's. SRV-166's second test follows the new order.
  - **Resolution: done.**
    - **Test:** `test_an_agents_designer_ended_past_its_start_up_says_its_uploads_then_its_sample_its_path_last`,
      ended and not, reads the path as `lifecycle/samples.py` does. It failed on the old order: the sample's sentence
      came first.
    - **Cause:** SRV-166 kept the sample's sentence first and ended it with a stop, which the path then took.
    - **Fix:** `_end_if_past_startup` says the uploads sentence first, then the sample's, as `_quit` does, with no
      `_sentence` step. Its docstring says what it returns.
    - **Also covered:** `_quit` already says the sample last. launch_designer's note puts its own line end after it.
    - **Result:** passes.
- [x] **SRV-169 · A process listing failing after the close drops what the call already did: the close's notes, the uploads line and the sample** · follows SRV-166, generation 4 · `mcp_server/server_tools/lifecycle.py:1342-1363` (`_quit`), `:895-912` (`_end_if_past_startup`), `:1147-1150` (`launch_designer`'s wait) · confirmed · found 2026-11-16
  - **Defect.**
    - SRV-166 made `_quit`'s "could not be ended" error carry `prefix`: the close's notes and the uploads line. Its Also
      covered looked at the returns only. When pgrep fails, `_designer_pids` raises `_NoListing` (SRV-163), which
      leaves `_quit` without them, from three places after the close:
      ```python
      if _exited(own, wait_s):  # its pgrep
      ...
      if own not in _designer_pids():  # after the sample
      ...
      if _force_end(own, port, seen):  # _exited's pgrep
      ```
      The last two drop the sample's path too.
    - In `_end_if_past_startup`, `_force_end` raising `_NoListing` drops `sampled + uploads`. `launch_designer`'s
      `except _NoListing` adds `none_left()` (SRV-164), which doesn't hold them.
    - In `launch_designer`'s wait, the "could not be ended" error of `_end_if_past_startup` leaves out `told()`: a
      Designer the call ended before, and what was done with Designer's preferences.
  - **Scenario.** Read in the code. `quit_designer` sends the close, then pgrep fails once (exit code 3, or a fork
    failing). The error says only that Designer's processes couldn't be listed. It doesn't say the close was asked.
    Nor does it say the crash reports may still be uploaded to Adobe, the line SRV-124 added for when they can't be
    turned off.
  - **Fix.** In `_quit`, catch `_NoListing` from the first wait on and raise it again with `prefix` in front and the
    sample after. In `_end_if_past_startup`, do the same with the uploads and the sample, in SRV-168's order. In
    `launch_designer`'s wait, raise `_end_if_past_startup`'s error with `told()` in front, as the call's other errors
    do. A unit test for each, pgrep failing after the close with the settings missing.
  - **Resolution: done.**
    - **Test:** in `test_lifecycle_env.py`:
      - `test_a_quit_whose_processes_cant_be_listed_after_the_close_still_says_the_close_the_uploads_and_the_sample`,
        the listing failing in the wait, after the sample, or in the forced end. All three raised the bare listing
        error.
      - `test_an_agents_designer_whose_processes_cant_be_listed_as_it_is_ended_still_says_its_sample_and_its_uploads`
        raised it bare too.
      - `test_a_launch_whose_wait_cant_end_an_agents_designer_says_first_the_one_it_ended_before` said only "Designer
        12 could not be ended".
    - **Cause:** SRV-166 made the "could not be ended" error carry what the call had done; the `_NoListing` raised by a
      listing after the close went out without it. In launch_designer's wait, `_end_if_past_startup`'s own error left
      `told()` out.
    - **Fix:** `_quit` raises a listing error from its wait on with `prefix` in front and the sample after.
      `_end_if_past_startup` raises one from the forced end with the uploads and the sample after. launch_designer's
      wait puts `told()` before `_end_if_past_startup`'s error. A listing error still gets `none_left()` in front there.
    - **Also covered:** `_quit`'s listing before the close says nothing was asked yet. launch_designer's
      `_end_if_past_startup` before its wait has done nothing before it.
    - **Result:** passes, with the rest of `test_lifecycle_env.py`.
  - Questioned by SRV-171 (2026-11-16).
- [x] **SRV-170 · A comment and test names still say the launch's process is known by its port alone** · follows SRV-165, generation 3 · `mcp_server/server_tools/lifecycle.py:399`, `tests/unit/conftest.py:147`, `tests/unit/test_lifecycle_env.py:3847-3850` · confirmed · found 2026-11-16
  - **Defect.** SRV-165 made the launch find its process by its port and its home (`_launch_marks`). Three places
    still give the port alone, the first as the reason SRV-165 disproved:
    - lifecycle.py: `with contextlib.suppress(_NoListing):  # new, with the launch's port: certainly this launch's`;
    - conftest.py: `lambda opener, before, port: opener.pid`, a parameter now given the marks;
    - test_lifecycle_env.py: `test_the_process_open_started_is_looked_for_with_the_launchs_port`, and its comment
      "the conftest fake ignores the port; an int, as ports are elsewhere (TST-443)". The value is now a tuple of the
      port's and the home's variables.
  - **Scenario.** Read in the code. A reader of the comment takes the port to be enough, which is what let a launch
    take the user's Designer for its own (SRV-165).
  - **Fix.** Say "its port and its home" in the comment, name the fake's parameter `marks`, and rename the test and
    its comment for the marks. Wording only, at generation 3 (Follow-up chains).
  - **Resolution: done.** Wording and names only, at generation 3: the comment says "its port and home"; the conftest
    fake's parameter is `marks`; the test is `test_the_process_open_started_is_looked_for_with_the_launchs_port_and_home`,
    its comment about the marks. The test passed before and after the rename.
- [x] **HLP-176 · A step off screen with no count shown waits its whole limit once Designer's window comes on screen, and its test can't tell** · follows HLP-170, generation 4 · `mcp_server/designer_helpers/frames3d.py:324-326` (`_renders_alike`), `tests/unit/test_frames3d.py:544-578` · confirmed · found 2026-11-16
  - **Defect.**
    - HLP-170's branch waits for `ended()` alone when the view is off screen at the start:
      ```python
      if not self._drawing():
          self._wait(ended, NO_RESTART)
          return
      ```
      For `settled()`, `ended` is `asked_off_screen`: `self._asked > asked and not self._drawing()`. Once the window
      is on screen, that can't become true. The wait then runs to NO_RESTART, its limit, and returns without
      comparing a render. Before HLP-170, the loop compared renders once the window was on screen.
    - The test HLP-170 added records each wait's limit, not what its state returned. It would pass on a wait that ends
      at its limit (`lambda: False`) or at once (`self.off_screen`). So the "ends once the view asks for a frame" of
      its name goes unchecked.
  - **Scenario.** Read in the code. `set_3d_view(mesh='Sphere')`, with no move, in a hidden Designer whose view shows
    no count (Display > Samples off, or a view that never drew). The user shows Designer before the step's
    UpdateRequest comes. The Expose event wakes the wait, but its state stays False, so it waits the whole second:
    the limit becomes the wait's time, against AGENTS.md's wait rule. The step's draw isn't seen. set_3d_view takes no
    shot, so nothing it says is wrong.
  - **Fix.** Wait on `lambda: ended() or self._drawing()`. If the view is drawing then, compare renders for the time
    left, as on screen. In the test, record `state()` before and after each fake wait: `(False, True)` for
    `settled()`, ended by the UpdateRequest; `(True, True)` for `moved()`, which ends at once off screen. Add a case
    where the window comes on screen during the wait.
  - **Resolution: done.**
    - **Test:** `test_with_no_count_shown_a_step_whose_window_comes_on_screen_during_its_wait_compares_renders_there`
      failed: the wait ended False, and no render was taken. HLP-170's test now records each wait's state, before and
      after the UpdateRequest: `(False, True)` for `settled()`, `(True, True)` for `moved()`.
    - **Cause:** HLP-170's branch waited for `ended()` alone, which can't hold once the window is on screen.
    - **Fix:** `_renders_alike` waits off screen for `ended()` or the window on screen. On screen then, it compares
      renders in the time left of the same limits. Its docstring says so.
    - **Also covered:** `moved()` ends at once off screen, as before. `shown()` compares renders only on screen.
    - **Result:** passes. Live, `check_set_3d_view_sets_up_a_view_that_never_drew` passes in a Designer just started.
      The window coming on screen during a step's wait is in the unit test only: it takes the user's showing Designer.
- [x] **HLP-178 · `_Screen`'s docstring says a window not on screen is refused after ON_SCREEN_WAIT** · follows HLP-173, generation 3 · `mcp_server/designer_helpers/shot3d.py:163-164` · confirmed · found 2026-11-16
  - **Defect.** Since HLP-173, `_wait_on_screen` waits ON_SCREEN_WAIT, puts the window in front again, then refuses
    after ON_SCREEN_WAIT more. Its own docstring and the refusal say so. The class docstring still says:
    ```
    Refused when the window still isn't on screen
    after ON_SCREEN_WAIT, or goes off screen again as its view draws each of BRINGS times it is put there.
    ```
  - **Scenario.** Read in the code. A reader expects one show and a refusal after ON_SCREEN_WAIT; the window is shown
    twice and refused after twice that.
  - **Fix.** Make the claim smaller: "Refused when the window still isn't on screen once `_wait_on_screen` gives up,
    or ...". Wording only, at generation 3 (Follow-up chains).
  - **Resolution: done.** Wording only, at generation 3: the refusal is "once `_wait_on_screen` gives up".
- [x] **TST-473 · The Scene menu check's two 3D shots still run unwatched, and the front watch's check still names the window checks alone** · follows TST-471, generation 2 · `tests/test_all_tools/editor_panels_and_fit/checks.py:2602`, `:2291-2299` (`check_designer_stayed_behind`), `tests/test_all_tools/window_server.py:5-9`, `tests/unit/test_selftest_window_states.py:325` · confirmed · found 2026-11-16
  - **Defect.**
    - TST-471 starts the front watch before the first check, so the 3D checks that put a hidden Designer's window on
      screen are watched. `check_the_3d_views_scene_menu_checks_the_mesh_shown` still comes after the in-front group,
      outside the watch:
      ```python
      await check_a_plain_3d_shot_shows_a_change_made_while_designers_window_was_off_screen(ctx, in_front=True)
      await check_the_3d_views_scene_menu_checks_the_mesh_shown(ctx)
      ```
      It takes two 3D shots with `mesh=`, and nothing it measures needs a window in front of the user's.
    - The unit test pins only the checks right after `check_designer_stayed_behind`
      (`after[1 : 1 + len(IN_FRONT_ONLY) + len(SPLIT)]`), so a check awaited after them goes unwatched and unseen.
    - `check_designer_stayed_behind`'s docstring ("Over the window checks off screen") and its check's name ("the
      window checks off screen never bring a window of Designer's in front ...") still name the window checks alone.
      So does window_server.py's docstring ("the window checks set up off screen", "stayed_behind (the window
      checks')"). A window of Designer's in front during a 3D check or a panel's screenshot would be reported as the
      window checks'.
  - **Scenario.** Read in the code. A change that leaves Designer's window opaque in front after a mesh switch shows
    on the user's screen in every full run, and no check judges it.
  - **Fix.** Move the call into the `with FrontWatch` block, before `check_designer_stayed_behind`, and pin that
    nothing is awaited after the in-front group. Say "every check up to the window checks off screen" in the
    docstrings and the check's name.
  - **Resolution: done.**
    - **Test:** `test_the_window_checks_off_screen_are_watched_and_those_in_front_run_after_together` now wants nothing
      after the in-front group. It failed, listing the Scene menu check.
    - **Cause:** TST-471 moved the watch's start, not this check, which stayed after the in-front group.
    - **Fix:** the Scene menu check runs last in the watched block. The in-front 3D checks set their own mesh, and the
      other two take no 3D shot. `check_designer_stayed_behind`'s docstring and check name, and window_server.py's
      docstring, say every check up to the window checks off screen.
    - **Result:** passes. In a scratch run, the Scene menu check passed under a front watch, judged after it:
      `check_designer_stayed_behind` passed.
- [x] **TST-474 · A clear whose hide fails makes Designer's windows opaque, then transparent again; its docs still say opaque** · follows TST-460, generation 2 · `tests/test_all_tools/editor_panels_and_fit/window_states.py:274-300` (`_CLEAR`), `:517-519` (`clear`), `tests/unit/test_selftest_window_states.py:455` · confirmed · found 2026-11-16
  - **Defect.**
    - TST-460's resolution says `_CLEAR` "makes the windows opaque only once Designer is hidden". It puts back the
      looks `_PUT` recorded before it acts on the hide's result:
      ```python
      hidden = until(mac.hidden)
      for w, look in getattr(sys, 'mcp_selftest_looks', {}).items():  # as _PUT found them
          mac.set_appearance(w, *look)
          mac.let_go(w)
      ...
      fade(not hidden)
      ```
      `_PUT` records the windows at rest, opaque and clickable. When the hide fails, each window goes from transparent
      to opaque, then back to transparent with `fade(True)`.
    - The comment above `_CLEAR` and `clear()`'s docstring still say the clear leaves Designer "hidden, its windows
      opaque and clickable", without the case where it couldn't hide. So does the name of
      `test_clear_leaves_every_window_opaque_and_clickable_after_ending_the_holds`.
  - **Scenario.** Read in the code. After a way in front, a hide that doesn't take leaves Designer's windows on the
    user's screen, opaque for the length of the loop. Whether the window server draws them opaque in that time wasn't
    measured: that takes Designer's windows opaque on the user's screen. The fix doesn't depend on it.
  - **Fix.** Put each look back only `if hidden`, and end every hold (`let_go`) either way, then `fade(not hidden)` as
    now. Add the not-hidden case to the comment, the docstring and the test's name.
  - **Resolution: done.**
    - **Test:** `test_clear_ends_every_hold_and_makes_the_windows_opaque_only_once_designer_is_hidden`, renamed from the
      TST-431 test, wants each look put back under `if hidden` and every hold ended either way. It failed: the looks
      were put back whatever the hide did.
    - **Cause:** TST-460 guarded the final fade, not the looks put back before it.
    - **Fix:** `_CLEAR` puts a look back only once Designer is hidden, and ends every hold either way. The comment above
      `_CLEAR` and `clear()`'s docstring give the not-hidden case.
    - **Result:** passes. In a scratch run, the transparency check's three ways off screen pass, each ended by `clear()`.
  - Questioned by TST-478 (2026-11-16).
- [x] **TST-475 · NEVER_DREW is said to switch the mesh and back, but leaves Plane where a Designer just started shows Rounded cube** · follows HLP-170, generation 4 · `tests/test_all_tools/editor_panels_and_fit/checks.py:1996-2010` (`NEVER_DREW`, `check_set_3d_view_sets_up_a_view_that_never_drew`) · measured · found 2026-11-16
  - **Defect.** The comment says "then a mesh set up and back", and the check's docstring "the mesh is switched, then
    back". The snippet sets Sphere, then Plane, whatever was shown before:
    ```python
    set_3d_view(mesh='Sphere')
    set_3d_view(mesh='Plane')
    ```
  - **Scenario.** Measured (2026-11-16) in a Designer `launch_designer` had just opened hidden, after
    editor_panels_and_fit's preparation. `_mesh_shown` read "Rounded cube" before NEVER_DREW, with no count shown, and
    "Plane" after it. The checks after it start from Plane, not from the mesh shown before.
  - **Fix.** Make the claim smaller: "Sphere, then Plane", in the comment and the docstring. Wording only, at
    generation 4 (Follow-up chains).
  - **Resolution: done.** Wording only, at generation 4: "Sphere, then Plane" in the comment and the docstring.
- [x] **TST-476 · tool_3d.py's types: `tool` optional though always passed, and an `Any` mark whose reason doesn't hold** · follows TST-461, generation 2 · `tests/test_all_tools/editor_panels_and_fit/designer_scripts/tool_3d.py:11-20` · confirmed · found 2026-11-16
  - **Defect.**
    ```python
    class Args(TypedDict, total=False):
        tool: str
        selection: bool


    ...
    mw: Any = app.getQtForPythonUIMgr().getMainWindow()  # Any: a Qt widget, which sd's stubs leave untyped
    ```
    - Every caller passes `tool` (checks.py:324-397), and the script reads `ARGS['tool']`, so `tool` is required.
      Only `selection` is optional.
    - sd types the main window: `getMainWindow(self) -> Optional[QtWidgets.QMainWindow]` (Designer's
      `sd/api/qtforpythonuimgrwrapper.py:28`). The `Any` comes from `getSDApplication`, which sd leaves unannotated.
  - **Scenario.** Read in the code. AGENTS.md's typing rules mark an `Any` only where nothing narrower fits.
  - **Fix.** `tool` required and `selection` optional: a TypedDict with `tool`, and `Args` deriving from it with
    `total=False` and `selection` (`NotRequired` needs Python 3.11, and mypy checks for 3.10). Then
    `mw: QtWidgets.QMainWindow = ...`.
  - **Resolution: done.** `Args` derives from a TypedDict holding the required `tool`, adding `selection` as optional.
    `NotRequired` needs Python 3.11, and mypy checks for 3.10. The main window is typed `QtWidgets.QMainWindow`, as
    sd's wrapper types it. Lint and types pass.
- [x] **SRV-171 · A process listing failing mid-call still drops what the error is about: a quit's error doesn't say the close was asked, and launch_designer's timeout message is lost** · follows SRV-169, generation 5 · `mcp_server/server_tools/lifecycle.py:1369` (`_quit`), `:895-914` (`_end_if_past_startup`), `:933-946` (`_how_to_end`), `:1190-1217` (`launch_designer`), `tests/unit/test_lifecycle_env.py:1035` · confirmed · found 2026-11-16
  - **Defect.**
    - SRV-169's scenario was an error that "doesn't say the close was asked". Its fix puts `prefix` in front, the
      close's notes and the uploads line:
      ```python
      except _NoListing as e:
          raise _NoListing(prefix + _sentence(str(e)) + sampled) from e
      ```
      The quit helper replies "closing Designer" alone, unless it discarded unsaved packages, and `_quit` takes that
      phrase out. So `prefix` is usually empty, and once uploads are off the error is the bare listing sentence. The
      test passes on a reply the helper never gives: `_closes(monkeypatch, said='closing Designer (a note of the
      close)')`.
    - `_end_if_past_startup`'s raise puts the uploads and the sample after the listing's sentence. It doesn't say it
      was ending an agent's Designer. Its docstring says the sample's sentence "ends with the sample's path"; a failed
      sample's ends with its reason.
    - launch_designer's timeout message calls `_how_to_end(port)`, which lists processes (`_sorted_out`,
      `_designer_pids`). A `_NoListing` raised there replaces the whole message ("did not answer within Ns ... ask
      the user to save and close it") with `none_left()` and the listing's sentence. SRV-164's Also covered counted
      it covered by that clause, which adds `none_left()` only.
  - **Scenario.** Read in the code.
    - `quit_designer` on an agent's Designer with nothing unsaved and uploads off; pgrep fails once in the wait. The
      error says only that Designer's processes couldn't be listed. It says neither that the close was asked nor
      whether the Designer was being forced.
    - launch_designer waits its whole wait_s on the user's Designer showing a dialog, and pgrep fails as the message
      is built. The agent isn't told that the bridge didn't answer, nor to ask the user.
  - **Fix.**
    - Name the step in each error: "Designer N was asked to close" in `_quit`, with "and didn't quit within Ns" from
      the force on; "Ending Designer N, an agent's that wasn't answering past its start-up" in
      `_end_if_past_startup`.
    - `_how_to_end` catches `_NoListing` and gives the advice without process IDs.
    - Tests with the helper's real reply, and with the listing failing in `_how_to_end`.
    - The docstring: "with the sample's path, when one was written".
  - **Resolution: done.**
    - **Test:** in `test_lifecycle_env.py`, each of which failed:
      - `test_a_quit_whose_processes_cant_be_listed_after_the_close_still_says_the_close_the_uploads_and_the_sample`,
        now with the helper's own reply, in all three places;
      - `test_an_agents_designer_whose_processes_cant_be_listed_as_it_is_ended_still_says_its_sample_and_its_uploads`:
        the listing's sentence came first;
      - `test_a_launch_timing_out_whose_processes_cant_be_listed_still_says_what_to_do`: the bare listing error.
    - **Cause:** SRV-169 put in front only what `prefix` held, empty for the helper's usual reply. `_how_to_end`'s
      listing let its error out of the message it was part of.
    - **Fix:**
      - `_quit` says "Designer N was asked to close." during the wait, and "Designer N did not quit within Ns and was
        being ended." from the sample on, before the listing's sentence. When the close wasn't asked, its notes say
        so.
      - `_end_if_past_startup` says it was ending an agent's Designer not answering past its start-up. Its docstring
        says the sample's sentence ends with the path when one was written.
      - `_how_to_end` gives the advice without process IDs when they can't be listed.
    - **Also covered:** the other listing errors launch_designer lets out come before it asked Designer anything,
      with what it did in front (SRV-164). read_designer_log raises it, as SRV-163 chose. `_quit`'s look before the
      close has done nothing yet.
- [x] **TST-477 · A unit test of the preferences lock waits a fixed 0.3 s, and under load passes without the lock** · `tests/unit/test_designer_preferences.py:696-709` (`test_a_put_back_waits_for_a_start_in_progress`) · confirmed · found 2026-11-16
  - **Defect.** The test judges the put-back blocked by joining its thread for 0.3 s, a fixed wait (AGENTS.md, Wait
    for callbacks):
    ```python
    waiting.start()
    waiting.join(0.3)
    assert waiting.is_alive() and not done, 'waits for the start'
    running.append(True)  # the one started
    ```
    `test_waits.py` doesn't read `tests/unit`.
  - **Scenario.** Read in the code. Take the lock away, and the thread may not reach `put_back` within 0.3 s, as when
    the unit suite runs beside four Designers in a full run. It is still alive then, so the assert passes.
    `running.append(True)` comes first, the put-back finds a Designer running and returns `''`, which the test
    wants: it passes.
  - **Fix.** Wait for the thread to meet the held lock. Wrap the module's `_lock` (or `fcntl.flock`) to try `LOCK_NB`
    first and set an Event on `BlockingIOError` before blocking. Wait for the Event with a limit, then go on as now.
  - **Resolution: done.**
    - **Test:** the test itself. With the lock taken out of `_lock` (a mutant made for the run, then removed), the new
      version failed, "waits for the start" at its 10 s limit. It passes on the code.
    - **Cause:** a fixed 0.3 s join judged the thread blocked.
    - **Fix:** the put-back's thread says when it meets the held lock: `fcntl.flock` wrapped to try `LOCK_NB` first,
      an Event set on `BlockingIOError`, then the blocking call. The test waits for the Event, 10 s at most.
    - **Also covered:** the other fixed waits the branch added to the unit tests: `watch.wait(0.05)` in
      `test_lifecycle_env.py` is a limit on a process already gone, met at once; `test_plugin.py`'s added
      `time.sleep(0.01)` are polls in loops.
- [x] **TST-478 · After a hide that fails, Designer's windows still end up opaque on the user's screen: the material check's put-back, and the next 3D shot after a clear** · follows TST-474, generation 3 · `tests/test_all_tools/editor_panels_and_fit/checks.py:602-656` (`ADD_MATERIAL`), `window_states.py:275-302,519-522` (`_CLEAR`, `clear`), `mcp_server/designer_helpers/shot3d.py:177-186` (`opaque_first`) · confirmed · found 2026-11-16
  - **Defect.**
    - TST-474 made `_CLEAR` give the looks back only once Designer is hidden. `ADD_MATERIAL`'s `finally` makes every
      window opaque whatever the hide did:
      ```python
      try:
          mac.hide()
          _until(lambda: mac.hidden() and not handle.isExposed(), 3.0, [spy.fired])  # off screen again
      finally:
          handle.removeEventFilter(spy)
          for w in mac.windows(True):
              mac.set_appearance(w, 1.0, False)
      ```
      The snippet's own comment says the dialog's unhide once left Designer over the user's windows.
    - A clear whose hide fails leaves Designer shown, transparent and click-through. It prints NOT_HIDDEN, which no
      caller reads. The next 3D shot's `opaque_first` takes the transparent window for one an earlier shot left so,
      and makes it opaque where it is. `_bring` finds it neither covered, hidden nor minimized, so `put_back` does
      nothing.
    - The sixth review dropped the unread NOT_HIDDEN on DECISIONS.md's low-value rule. It took the worst to be a
      Designer left "transparent and click-through"; the next shot makes it opaque.
  - **Scenario.** Read in the code; no run has seen a hide fail.
    - In the in-front group, a way in front leaves Designer's main window in front of the user's windows, and
      `without_others_in_front`'s clear can't hide it. The next check's `with_checker` shot makes it opaque there,
      unwatched. It stays until a clear hides it.
    - The material check's hide failing leaves the windows opaque until the next clear, several checks later.
  - **Fix.** `ADD_MATERIAL` gives the looks back only once hidden, as `_CLEAR` does. `clear()` raises when its output
    says NOT_HIDDEN, which ends the category's run before another shot. Its test: the material check's unit pin gets
    TST-474's "only once hidden". At generation 3, no new check beyond that pin.
  - **Resolution: done.**
    - **Test:** in `test_selftest_window_states.py`, each of which failed:
      - the material check's pin, which now wants the looks back under `if mac.hidden()`, NOT_HIDDEN printed
        otherwise, and the output read by `stopped_if_shown`;
      - `test_a_clear_that_couldnt_hide_designer_stops_the_category`: no such function;
      - `test_every_clear_of_the_window_checks_goes_through_at_rest`: 17 clears ran directly.
    - **Cause:** TST-474 fixed `_CLEAR`'s looks alone, and NOT_HIDDEN went unread.
    - **Fix:**
      - `ADD_MATERIAL` gives the looks back only once Designer is hidden again, and says NOT_HIDDEN otherwise.
      - `window_states.at_rest` runs every clear: the 17 in checks.py and retries.py's. The snippet is window_states'
        own (`_clear`).
      - `stopped_if_shown` raises on NOT_HIDDEN, as the material check does on its output before its tiling shot. The
        category's run then ends before another shot.
    - **Also covered:** window_states' other `fade(False)` come after a hide or a minimize that took, or after a
      raise (TST-460). In the scratch run, the material check and the window checks off screen passed, each clear
      through `at_rest`.
- [x] **TST-479 · Vague types in functions the branch adds or changes: a new fake's unmarked `Any`, and safeguards' `dict[str, Any]`** · `tests/unit/test_selftest_alone.py:657` (`CrashesAsItQuits.__call__`), `tests/test_all_tools/safeguards/checks.py:67,486,571` (`run`) · confirmed · found 2026-11-16
  - **Defect.**
    - The new `CrashesAsItQuits.__call__(self, name: str, args: dict[str, Any] | None = None) -> Any` carries no
      `# Any:` reason. It copies the signature of its parent's, a function the branch leaves alone.
    - safeguards' `run()`, which the branch changed (two sleeps removed), types three sets of tool arguments
      `dict[str, Any]`:
      - `cases: tuple[tuple[str, Callable[[str], list[dict[str, Any]]], str], ...]`;
      - `edits: list[tuple[str, dict[str, Any]]]`;
      - `calls: list[tuple[str, dict[str, Any]]]`.
  - **Scenario.** Read in the code: AGENTS.md's typing rules, for the functions a branch's diff adds or changes,
    their unchanged lines included (DECISIONS.md, vague types).
  - **Fix.** `dict[str, object]` for the tool arguments, which `Call` accepts. For the override: `args` typed
    `dict[str, object] | None`, and the return `SimpleNamespace`, what `_result` builds, or its `Any` marked with its
    reason.
  - **Resolution: done.** Types only:
    - `dict[str, object]` for safeguards' tool arguments. The loop's `args` is now `arguments`, as `args` is typed
      elsewhere in `run()`.
    - `CrashesAsItQuits.__call__` takes `dict[str, object] | None`, and its `Any` is marked with its reason.

    Lint and types pass, and so does `test_selftest_alone.py`.
