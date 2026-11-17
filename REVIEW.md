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

**Last used:** PLG-45, SRV-175, HLP-185, INS-41, TST-514.

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
| Low | 0 | 20 |
| **Total** | **0** | **20** |

## Review log

### 2026-11-17: the disallow-any-explicit branch against main (ROADMAP item 99), the diff only

- **How:** two reviewer subagents, no tests run. One took `mypy.ini`, `tests/unit/test_types.py`, AGENTS.md and
  ROADMAP.md. The other took the 54 removed `# type: ignore[no-untyped-call]` comments in 50 files, and what still
  refers to them. The lead agent read each suspicion. Three needed a scratch probe outside Designer: mypy 2.4.1 run with
  the repository's `mypy.ini` on small files in the scratchpad. It measured the mark's place in a signature spanning
  several lines (TST-496), the `Any` inside an expression (TST-497), and `FORCE_COLOR=1` (TST-499). No suspicion was
  settled as wrong.
- **Not verified:** none.
- **Resolutions assessed:** none in scope. REVIEW.md had no entries after its cleanup.
- **Findings:** TST-496 to TST-500, all Low. Both reviewers found TST-498, merged into one entry.
- **Suggested order:** TST-497 and TST-496 first, since they change what AGENTS.md tells agents and reviewers to do.
  Then TST-498 and TST-499 in the test, then TST-500's wording.
- **Checked and found fine:**
  - The new test fails with `disallow_any_explicit` off.
  - Output the test can't parse fails it rather than passing it: a crash, column numbers, a syntax error.
  - The test reads Windows paths and CRLF line endings.
  - `_mypy` keeps what the two whole-repo runs checked: cwd, env with `MYPYPATH`, cache dir, argument order, and the
    message when mypy isn't installed.
  - A file named on the command line replaces `mypy.ini`'s `files`. The sd, PySide6 and shiboken6 section keeps their
    own code quiet. Without Designer, sd's names are an implicit `Any`, never an explicit one.
  - The three `untyped_calls_exclude` names match their definitions in Designer's sd package. mypy matches a name
    exactly or by dotted prefix, so they let no other function through. No other unannotated sd function is called in
    checked code.
  - The removed ignores left no dead cast, annotated local or import. Every remaining cast still has its explanation.
  - Nothing still refers to the removed ignores or to the old `# Any:` mark. The remaining sd ignores (`union-attr`,
    `attr-defined`) still justify `--no-warn-unused-ignores` in the run without Designer.

### 2026-11-17: the one-record-read branch against main (ROADMAP item 106), the diff only

- **How:** two reviewer subagents, no tests run. One took the server code (`server_tools/lifecycle.py`, `log.py`), the
  other the unit tests (`tests/unit/test_lifecycle_env.py`) and ROADMAP.md row 106. The lead agent read the code at
  each suspicion. Reading settled them all: no scratch probe was needed. No suspicion was settled as wrong.
- **Not verified:** none.
- **Resolutions assessed:** none in scope. No resolved entry's fix is in this diff.
- **Findings:** SRV-175, TST-501 and TST-502, all Low. Both reviewers found TST-501, merged into one entry.
- **Suggested order:** SRV-175 first, as its fix decides TST-501's: with the record's age taken from the one read, the
  forced-quit test can use the real `_agent_log`. Then TST-501, then TST-502.
- **Checked and found fine:**
  - `_agent_record`'s one parse gives the home `_home_in` gave: a record that isn't a dict raises at `record['pid']`
    before `.get('home')`, a `home` that isn't a string gives None, and a malformed record is still forgotten.
  - `designer_status` reads the records after the listing on the idle path, as before, and `_started_by` and
    `_others` now answer from one read. A change between the read and the listing can still only give "the user's".
  - `_quit` with no agent's record: `_agents()` now runs before `_running_on`'s process listing. A launch recording
    its Designer in that gap gives at worst the refusal, which ends nothing.
  - On Windows, `_running_on` returns before `agents` is used, and nothing is recorded.
  - `_quit_evidence` uses its result only when the Designer is still listed afterwards.
  - The three places ROADMAP row 106 leaves unchanged (`start()`, `_log_for`, `_end_if_past_startup`): the reasoning
    holds.
  - Each new count test fails on main: status idle 3 reads for 2, status while a job runs 5 for 2, the quit on a port
    where none runs 3 for 2, the forced quit 2 for 1.
  - `ANOTHER_LAUNCHS`, recorded without a home, gives what main's `(11, b'{}')` fakes gave: `_home_in(b'{}')` was
    None. The `sorted_out` fake passes `agents` through, and `_how_to_end`'s one-argument call still works.
  - Records live in each test's own `tmp_path` (conftest), and the patches are undone after each test.
  - Types: `_Recorded`'s fields and `dict[int, int]` (port to process ID) are exact. The diff adds no `Any`.

### 2026-11-17: the one-record-read branch against main, second review: SRV-175, TST-501 and TST-502's fixes, and the window check's new report

- **How:** two reviewer subagents, no tests run. One took the server code and its unit tests (`lifecycle.py`, `log.py`,
  `tests/unit/test_lifecycle_env.py`) and ROADMAP.md row 106, the other the window check's new report
  (`tests/test_all_tools/window_server.py`, `common.py`, `editor_panels_and_fit/checks.py`,
  `tests/unit/test_selftest_window_server.py`). The lead agent read the code at each suspicion. One scratch probe outside
  Designer, plain Python on this Mac, measured `active_app()` (two `lsappinfo` runs) at 9.5 ms median and 11 ms at most,
  and naming the 5 apps that showed a normal window at 17 ms, once.
- **Settled as wrong:** that naming apps with `ps` in the sampling thread blinds the watch. The probe measured 17 ms
  for every app on screen, once, under one sampling interval (`FRONT_EVERY`, 50 ms). A `ps` that hangs hasn't been seen,
  and a name `ps` prints can't fail to decode: APFS requires its file names to be valid UTF-8.
- **Not verified:** none.
- **Resolutions assessed:** SRV-175, TST-501 and TST-502 hold. SRV-175's test fails on the old `getmtime` with the
  record removed, and its **Also covered** list matches every `agent_designer_file(` in `mcp_server`. TST-501's test
  reads the record once where main read it twice. TST-502's comment matches main's reads, idle and while a job runs.
- **Findings:** TST-503 to TST-507, all Low. TST-507 follows SRV-175 and TST-501, generation 2.
- **Suggested order:** TST-507 first, as it makes the unit suite fail on Windows. Then TST-503 in the watch, then
  TST-505 and TST-506 in the new tests, then TST-504's wording.
- **Checked and found fine:**
  - `fronts` counts what the old loop in `stayed_behind` counted: the same condition with `active_only`, the last
    sample counting for nothing, a stretch split while Designer is the active app.
  - `covering` answers as `in_front_of_another` did: the same windows, order, `over` and overlap. Nothing else used
    `in_front_of_another`.
  - `Sample.at` and `common.checked` share `time.monotonic()`, across the watch's thread. Only the category's own
    thread calls `check()`. `names` is read once the watch's thread has ended.
  - `fronts_said` with fewer than two samples finds no stretch and reads no sample.
  - `lifecycle/checks.py` uses only `FrontWatch` and `stayed_off_screen`. `test_selftest_window_states.py` still finds
    `check_designer_stayed_behind` right after the watched block.
  - `_read_record`'s `os.fstat` gives the `st_mtime` of the file read. Records are put in place with `os.replace`, so
    the bytes and the time come from one record.
  - `_Recorded`'s field order matches its constructor and `ANOTHER_LAUNCHS`, and every fake `_agent_log` takes three
    arguments.
  - Types: no `Any`; `list[tuple[float, str]]`, `Mapping[int, str]` and the NamedTuples are exact.

### 2026-11-17: the one-record-read branch against main, third review: TST-503 to TST-508's fixes

- **How:** two reviewer subagents, no tests run. One took the window check's report and its tests
  (`tests/test_all_tools/window_server.py`, `common.py`, `editor_panels_and_fit/checks.py`,
  `tests/unit/test_selftest_window_server.py`), the other the Windows skips and the simulation
  (`tests/unit/windows_simulation.py`, `test_windows_simulation.py`, the marks in `test_lifecycle_env.py`,
  `test_view3d_helpers.py` and `test_install.py`, AGENTS.md's paragraph, ROADMAP item 18). The lead agent read the code
  at each suspicion. One scratch probe outside Designer: the simulation with every name Windows lacks that the code
  uses also removed (`signal.SIGKILL`, `signal.SIGALRM`, `signal.setitimer`, `os.geteuid`, `termios`, `resource`),
  run over the files that mention any of them; 17 more cases failed (TST-509).
- **Not verified:** whether the five cases `SIMULATION_ONLY` lists pass on Windows itself: no Windows machine here
  (ROADMAP item 18). TST-511 narrows the comment that claims it.
- **Resolutions assessed:** TST-503, TST-504, TST-505 and TST-507 hold. TST-506 holds for its test; its **Also
  covered** is questioned by TST-513. TST-508 holds for the marks it made; the simulation it rests on is questioned by
  TST-509, and two of its marks by TST-510 and TST-511.
- **Findings:** TST-509 to TST-514, all Low. Longest chains still growing: TST-508 → TST-509, TST-510 and TST-511,
  and TST-506 → TST-513, generation 2 each.
- **Suggested order:** TST-509 first, as it is TST-508's scenario again; TST-510 and TST-511 with it, in the same marks.
  Then TST-512, TST-514 and TST-513.
- **Checked and found fine:**
  - Patching `window_server.time` reaches only `_watch`, and the watch's thread is joined before the patch is undone.
  - `third_kept` and `read` are set inside the watch's own read, after the sample before it is kept, so each wait
    returns with that sample there.
  - `covering` and the naming share `_shown`: every window that can be covered is named in the sample that lists it.
  - The plugin loads only in the subprocess (`-p`); the outer process and its `os`, `sys.modules` and environment are
    untouched. Replacing `PYTHONPATH` there is harmless: conftest puts the repository's folders on the path itself.
  - The guard's pattern catches a file that can't be collected and folds a parametrized case into its test's name; an
    empty run fails it, as `SIMULATION_ONLY` isn't empty. 300 s is a limit: `run` kills the child.
  - Every other `_SETS_UNIX` test sets macOS; every other `_RECORDED` test checks a record `_remember_started` skips on
    Windows; the reasons of `_logs`', `_forced_with`'s, the socket test's and the forced quit's skips hold.
  - `test_install.py`'s assertion matches `install.py`'s two messages, and the view3d skip matches `view3d.py`, where
    only macOS holds a window.

---

## High

## Medium-high

## Medium

## Low-medium

## Low

- [x] **TST-496 · AGENTS.md puts the mark on the `Any`'s line; for a signature spanning several lines mypy wants it on the `def` line** · `AGENTS.md:160` · measured · found 2026-11-17
  - **Defect.** AGENTS.md says an `Any` that stays is "marked as an exception with its reason on the same line:
    `# type: ignore[explicit-any]  # <reason>`". mypy reports a function's explicit `Any` on its `def` line, and an
    ignore covers only the line it is on. When ruff splits a signature over several lines, the mark on the parameter's
    line doesn't silence the error.
  - **Scenario.** The probe ran mypy with `mypy.ini` on `def f(\n    x: Any,  # type: ignore[explicit-any]\n) -> None:
    ...`. It reported `4: Explicit "Any" is not allowed [explicit-any]` on the `def` line and
    `5: Unused "type: ignore" comment [unused-ignore]` on the parameter's line. The same mark on the `def` line drew no
    error. An agent following AGENTS.md gets two errors it can't explain, and a wasted round.
  - **Fix.** AGENTS.md says the mark goes on the line mypy reports, which for a function is its `def` line. The test's
    probe gets a function on several lines with the mark on its `def` line, expecting no error.
  - **Resolution: done.**
    - **Test:** the probe in `test_mypy_refuses_an_explicit_any` (`tests/unit/test_types.py`) gets `def i(` over three
      lines, with the mark on its `def` line, and expects no error. The defect was AGENTS.md's wording, so this line
      passed before the fix too. It backs the new sentence.
    - **Cause:** AGENTS.md placed the mark by the `Any`. mypy reports a function's explicit `Any` on its `def` line, and
      an ignore covers only its own line.
    - **Fix:** AGENTS.md says the mark goes on the line mypy reports. For a function, that is its `def` line, even when
      the signature spans several lines.
    - **Also covered:** searched the docs, skills and Python for "reason on", "on its line" and "same line". The
      `project-code-review` skill said an `Any` is marked "with its reason on its line". It now says "with its reason,
      as those rules say", leaving the place to AGENTS.md.

- [x] **TST-497 · The new sentences say mypy reports every `Any` written out; it misses one written inside an expression** · `AGENTS.md:161`, `mypy.ini:14`, `tests/unit/test_types.py:105`, `ROADMAP.md:88` · measured · found 2026-11-17
  - **Defect.** AGENTS.md says "mypy refuses every `Any` written out without the mark". mypy.ini's comment, the new
    test's docstring and ROADMAP item 99's text say mypy reports every `Any` written out. mypy checks annotations,
    signatures, casts and aliases. It doesn't check an `Any` in a type used as a value in an expression.
  - **Scenario.** The probe ran mypy with `mypy.ini` on `a = defaultdict[str, Any](int)`, `take(dict[str, Any])`,
    `c = list[Any]()` and `b: object = Any`. It found no issue. AGENTS.md tells reviewers to look only for an `Any`
    that comes in implicitly, so one trusting it misses these.
  - **Fix.** The sentences name where mypy looks (an annotation, a signature, a `cast`, an alias) instead of "every".
    AGENTS.md also names the gap: an `Any` inside an expression, such as `defaultdict[str, Any](int)`, isn't reported,
    so look for those too. The test's probe gets that line, expecting no error, so the sentence has its check.
  - **Resolution: done.**
    - **Test:** the probe in `test_mypy_refuses_an_explicit_any` gets `g = defaultdict[str, Any](int)` and expects no
      error on it. The defect was in the sentences, not in mypy.ini, so this line passed before the fix too. It backs
      the narrowed sentences. The probe also gets `Pair = tuple[str, Any]` and `def h(x: Any)`, each expected to be
      reported, since the sentences now name type aliases and signatures.
    - **Cause:** the sentences went from the cases measured for ROADMAP item 99 (annotations, casts, aliases) to every
      `Any` written out.
    - **Fix:** AGENTS.md, mypy.ini's comment, the test's docstring and ROADMAP item 99 name where mypy looks: an
      annotation, a signature, a `cast`, a type alias. AGENTS.md, mypy.ini and the docstring name the gap, an `Any`
      inside an expression. AGENTS.md says to look for those too.
    - **Also covered:** searched the docs, skills and Python for "every `Any`" and "every Any". No other place says it.

- [x] **TST-498 · The new test's `errors` is a `set[Any]`, from `re.findall`** · `tests/unit/test_types.py:110` · confirmed · found 2026-11-17
  - **Defect.** `errors = set(re.findall(r'probe\.py:(\d+): error: .*\[([a-z-]+)\]$', ...))`. typeshed gives
    `re.findall` the return type `list[Any]`, so mypy checks nothing about the comparison with `expected`. AGENTS.md
    asks for such an implicit `Any` to be narrowed in a function the branch adds. Both reviewers found it.
  - **Scenario.** A change of the regex to one group makes `errors` a set of `str`. mypy says nothing, and the
    mismatch shows only when the test runs.
  - **Fix.** `errors: set[tuple[str, str]] = set(re.findall(...))`.
  - **Resolution: done.**
    - **Test:** none can fail on it, since mypy doesn't report an implicit `Any` (TST-497). `test_types.py` checks that
      the annotation fits what `re.findall` returns here.
    - **Fix:** `errors: set[tuple[str, str]] = set(re.findall(...))`.
    - **Also covered:** the test's other locals (`probe`, `result`, `expected`) get their types from typed calls, with no
      `Any`. The branch adds no other `re.findall`.

- [x] **TST-499 · The new test fails, with mypy.ini right, when `FORCE_COLOR` or `MYPY_FORCE_COLOR` is set** · `tests/unit/test_types.py:110` · measured · found 2026-11-17
  - **Defect.** The test's regex ends with `\[([a-z-]+)\]$`. With either variable set, mypy colours its output even
    when piped, and each error line ends in a reset escape after the code, so `$` never matches.
  - **Scenario.** The probe ran mypy with `FORCE_COLOR=1`, piped. The line came out as
    `probe_color.py:3: ^[[1m^[[31merror:^[(B^[[m Explicit ... ^[[33m[explicit-any]^[(B^[[m`. The test would then find no
    error, and fail on a correct mypy.ini with a message that points at the config. The same run with
    `--no-color-output` printed plain text. Neither variable is set here today.
  - **Fix.** `_mypy` passes `--no-color-output`.
  - **Resolution: done.**
    - **Test:** `test_mypy_refuses_an_explicit_any` runs mypy with `MYPY_FORCE_COLOR=1`, which mypy reads before
      `FORCE_COLOR`. Without the fix it failed with `assert set() == {('10', 'explicit-any'), ...}`: the regex found no
      error in the coloured lines. The test first ran three times (neither variable, `FORCE_COLOR=1`,
      `MYPY_FORCE_COLOR=1`), and the two forced runs failed this way. The `/simplify` pass kept one forced run, since
      the flag overrides both variables alike, and the run without colour couldn't fail on it.
    - **Cause:** mypy colours its output when either variable is set, even into a pipe. The reset escape after each
      error code kept the test's `$` from matching.
    - **Fix:** `_mypy` passes `--no-color-output`, for every run in `test_types.py`.
    - **Also covered:** the other tests that read a tool's output. `test_lifecycle_env.py`'s mypy run asserts
      `'kqueue' not in result.stdout`. Colour wraps a quoted name in escapes without splitting it (the review's probe
      printed `^[[1m"Any"^[(B^[[m`), so that check can't pass falsely. `test_lint.py`'s ruff runs check only the exit
      code.

- [x] **TST-500 · mypy.ini and ROADMAP item 99 say every Designer script calls the three excluded sd functions first** · `mypy.ini:17`, `ROADMAP.md:88` · confirmed · found 2026-11-17
  - **Defect.** mypy.ini says "The sd functions that every Designer script calls first", and ROADMAP item 99's Done
    text says the same. `sd.getContext()` is called in about 60 checked files, but `getQtForPythonUIMgr()` in only 6:
    `core.py` and five Designer scripts.
  - **Scenario.** A maintainer meets another unannotated sd function, such as `ctx.getLogger()`. The comment's rule,
    "every script calls them first", doesn't say whether that one belongs in the list or takes an ignore.
  - **Fix.** Say what the list holds: the sd functions that scripts call to reach the application and its Qt UI
    manager.
  - **Resolution: done.**
    - **Fix:** mypy.ini and ROADMAP item 99 say the list holds the sd functions that Designer scripts call to reach the
      application and its Qt UI manager.
    - **Also covered:** searched for "every Designer script". No other place says it.

- [x] **SRV-175 · `_agent_log` looks at the record again, for its age, after its caller's one read** · `mcp_server/server_tools/log.py:81`, `log.py:56-60`, `log.py:101`, `mcp_server/server_tools/lifecycle.py:719-720` · confirmed · found 2026-11-17
  - **Defect.** `_log_for` takes the home from one read of the record (`found = _agent_record(port)`), then calls
    `_agent_log(port, found.home)`. That runs `os.path.getmtime(agent_designer_file(port))`, a second look at the record
    file, outside any `try`. `read_designer_log` calls `_log_for` outside any `try` too (`log.py:101`). The branch's new
    docstring of `_agent_record` says "A caller takes everything it decides on from one call", which this look doesn't
    follow. The look predates the branch.
  - **Scenario.** `read_designer_log(port=9901)` finds the agent's Designer running. Before the `getmtime`, another
    server's quit sees that Designer exit and removes its record. The tool then fails with a raw
    `[Errno 2] No such file or directory` naming the record file, instead of the log of the Designer that just quit.
    The window is the time between the read and the `getmtime`. In a forced quit the same look gives "its log could not
    be read", but the record goes only once the Designer has exited, and `_quit` then returns before using the log.
  - **Fix.** Take the record's age from the one read: `_record_bytes` reads it from the open file (`os.fstat`), and
    `_Recorded` carries it to `_agent_log`. A unit test calls `read_designer_log` with the real `_agent_log` and a
    record removed after its first read.
  - **Resolution: done.**
    - **Test:** `test_the_log_of_a_designer_whose_record_goes_after_its_read_is_its_own`
      (`tests/unit/test_lifecycle_env.py`) calls `read_designer_log(port=OTHER)` with the real `_agent_log`, the record
      removed after its first read (`_record_reads(monkeypatch, then_gone=True)`). Before the fix it failed with
      `FileNotFoundError: [Errno 2] No such file or directory` naming the record file, as the scenario says.
    - **Cause:** `_agent_log` took the record's age with `os.path.getmtime(agent_designer_file(port))`: a second look
      at the file after its caller's one read, outside any `try`.
    - **Fix:** `_read_record` (`lifecycle.py`, was `_record_bytes`) returns the bytes and the time the record was
      written, both from one open (`os.fstat`). `_Recorded` carries the time as `written`. `_agent_log(port, home,
      written)` compares the log with it, `_log_for` passes `found.written`, and `_quit_evidence` takes the
      `_Recorded`. The record is put in place with `os.replace`, so the open file keeps the bytes and the time of the
      record read. `_agent_record`'s docstring now says its callers take the fields they use from one call.
    - **Also covered:** searched `mcp_server` for `agent_designer_file(`. `_forget_started` reads the record again on
      purpose, to remove it only if it still holds what was read. `_still_starting` looks at its age before
      `_agent_record` in `_end_if_past_startup`, which keeps `pgrep` and `ps` out of each wait (REVIEW.md SRV-158); ROADMAP
      row 106 lists it. The other uses write the record. No other caller looks at it again after a read. The live
      lifecycle category, which reads its Designers' own logs and forces quits through `_agent_log`, passed whole in a
      scratch run: 55 checks.

- [x] **TST-501 · The forced-quit test passes only through a fake `_agent_log`; its claim is false for the real code** · `tests/unit/test_lifecycle_env.py:1447-1455`, `tests/unit/test_lifecycle_env.py:498`, `ROADMAP.md:24` · confirmed · found 2026-11-17
  - **Defect.** `test_a_forced_quit_reads_its_log_from_the_home_its_record_gave` removes the record after its first read
    (`_record_reads(monkeypatch, then_gone=True)`) and expects the log's evidence. Its comment says a record gone by
    then "lost the log's evidence". ROADMAP row 106 says such a quit "still reads its log". `_forced_with` fakes
    `_agent_log`, and the real one reads the record's age (SRV-175). With the record gone that raises, and
    `_quit_evidence` returns None, as on main. Both reviewers found it.
  - **Scenario.** A reader takes the test as proof that a forced quit survives a record removed meanwhile. With the
    real `_agent_log` the quit still says "its log could not be read". The scenario is also unreachable: the record goes
    only once the Designer has exited, and `_quit` then returns before using the log.
  - **Fix.** Claim what the change does: one read of the record and one process listing fewer. Drop `then_gone` from
    the test and from `_record_reads`, keeping `reads == [server.PORT]`, which fails on main. Narrow the test's comment
    and the ROADMAP row to that. If SRV-175 is fixed first, a test with the real `_agent_log` may claim more.
  - **Resolution: done.**
    - **Test:** `test_a_forced_quit_reads_its_record_once`, renamed from
      `test_a_forced_quit_reads_its_log_from_the_home_its_record_gave`, counts the reads without removing the record:
      `reads == [server.PORT]`. On main it read `[9877, 9877]`, seen in the branch's first failing run. It passes on the
      branch's code, since the defect was the claim.
    - **Cause:** the test removed the record after its first read and expected the log's evidence, which only the fake
      `_agent_log` gave. The scenario can't happen either: the record goes only once the Designer has exited, and
      `_quit` then returns before using the log.
    - **Fix:** the test claims one read. Its comment and ROADMAP row 106 say a forced quit takes the home for its log
      from its one read, no more. `then_gone` stays in `_record_reads` for SRV-175's test, which uses the real
      `_agent_log`.
    - **Also covered:** searched the branch's tests and ROADMAP row 106 for "still reads its log" and "lost the log's
      evidence": none left.

- [x] **TST-502 · Two more of the branch's sentences say more than the code shows** · `tests/unit/test_lifecycle_env.py:1298-1301`, `ROADMAP.md:24` · confirmed · found 2026-11-17
  - **Defect.**
    - `test_designer_status_reads_each_record_once`'s comment says main's `_started_by` "read every record through
      _sorted_out, then its port's again". That holds only while a job runs. Idle, the process answering is known, and
      main read the port's record in `_started_by` and every record in `_others`. Its last sentence describes a record
      removed between two reads, which the test never does.
    - ROADMAP row 106 lists "three places" that read the records twice for two separate checks, as if complete.
      `launch_designer` has more: at the timeout, `_agent_designer(port)` (`lifecycle.py:1204`) then `_how_to_end(port)`
      (`lifecycle.py:1212`), and in the wait, `may_have_exited()` then `_may_hold(port)` (`lifecycle.py:1172`).
  - **Scenario.** A reader of the test learns a wrong read count for the idle case. A reader of the row takes the list
    as the whole of what was left.
  - **Fix.** The comment names both cases and drops the removal sentence, or says the test counts the reads only. The
    row says "such as" before its examples, or lists the other two.
  - **Resolution: done.**
    - **Fix:** the test's comment names both cases. Idle, `_started_by` read the port's record and `_others` every
      record. While a job runs, `_sorted_out` read every record, `_started_by` the port's again and `_others` every
      record once more. The removal sentence is gone. ROADMAP row 106 says "such as" before its examples of the places
      left unchanged.
    - **Also covered:** the comments of the branch's other new tests (the forced quit, the quit on a port where none
      runs, the log whose record goes) checked against main's reads: they hold.

- [x] **TST-503 · A sample's time is taken before its windows are read: a stretch can be placed one check early** · `tests/test_all_tools/window_server.py:172` · measured · found 2026-11-17
  - **Defect.** `Sample(time.monotonic(), active_app(), on_screen(cg, cf, keys))` evaluates its arguments left to
    right: the time first, then two `lsappinfo` runs, then the windows. `said` places a stretch by comparing that time
    with the checks' marks (`common.checked`), as if it were when the windows were read.
  - **Scenario.** The probe measured `active_app()` at 9.5 ms median, 11 ms at most. A check recorded in that gap
    (check X), with the window brought in front by the next one before the read, gives a line saying "before check X":
    the stretch is placed one check early.
  - **Fix.** Take the time right after `on_screen` reads the windows, as the stretch is about them.
  - **Resolution: done.**
    - **Test:** `test_a_samples_time_is_taken_once_its_windows_are_read` (`tests/unit/test_selftest_window_server.py`)
      records the order of the watch's calls through fakes. Before the fix: `['time', 'active app', 'windows']`.
    - **Cause:** `Sample(time.monotonic(), active_app(), on_screen(...))` evaluates the time first.
    - **Fix:** the watch reads the active app, then the windows, then takes the time. `Sample.at`'s comment says so.
    - **Also covered:** no other code builds a `Sample`. The popup watch (`editor_panels_and_fit/popups.py`) takes its
      time after reading the windows already, and only for durations.

- [x] **TST-504 · The new docstrings say more than the code: a stretch's start is placed, and at most ten are printed** · `tests/test_all_tools/window_server.py:11`, `window_server.py:272-275`, `tests/test_all_tools/common.py:64-65`, `tests/test_all_tools/editor_panels_and_fit/checks.py:2411` · confirmed · found 2026-11-17
  - **Defect.**
    - `said`'s docstring says "the checks around it", the module's "the checks recorded around it", and `common.py`'s
      comment that stretches are "placed between" the marks. `said` places only the stretch's start: the last mark at
      or before it, the first after it.
    - The module's docstring says `fronts_said` "gives each stretch in front a line", and the check's docstring that
      "Each stretch in front is printed whole". At most `FRONTS_SAID` (10) are; the others are counted ("and N more").
  - **Scenario.** A 2 s stretch running on past checks B and C reads as lying between A and B. A reader of a run with
    twelve stretches looks for all twelve.
  - **Fix.** Say "the checks recorded around its start", and "up to FRONTS_SAID stretches, the others counted".
  - **Resolution: done.**
    - **Fix:** `said`'s docstring and the module's say the checks recorded around a stretch's start, the module's and
      the check's that up to `FRONTS_SAID` stretches are said, the others counted, and `common.py`'s comment that a
      stretch's start is placed between the marks.
    - **Also covered:** the other sentences about the report (`Front`, `fronts`, `fronts_said`, `FrontWatch`) checked
      against the code: they hold.

- [x] **TST-505 · The stretch test can't tell the windows of a stretch's first sample from those of its last** · `tests/unit/test_selftest_window_server.py:299-306` · confirmed · found 2026-11-17
  - **Defect.** `Front.window` is "the process's window in front, at its first sample", and `covered` the window it
    covered then. In `test_the_stretches_in_front_name_the_window_and_the_one_it_covered`, the first stretch is two
    identical `OVER` samples.
  - **Scenario.** `fronts` changed to keep the last sample's windows still passes the test.
  - **Fix.** Give the stretch's two samples different windows, and expect the first's.
  - **Resolution: done.**
    - **Test:** the stretch's samples are now `OVER`, then `OVER_RIGHT`, and the first's windows are expected. With
      `fronts` changed for the run to keep the last sample's windows, the test failed (`window=(0, 0.5, 42, (500.0, …))`
      for `(0, 1.0, 42, (0.0, …))`); the code put back, it passes.
    - **Fix:** the test only; `fronts` keeps the first sample's windows already.

- [x] **TST-506 · The new naming test polls the watch's samples, though its own fake could say when they are there** · `tests/unit/test_selftest_window_server.py:399-402` · confirmed · found 2026-11-17
  - **Defect.** `test_the_front_watch_names_each_app_once_as_one_of_its_windows_first_shows` waits with
    `while len(watch.samples) < 3 and time.monotonic() < deadline: time.sleep(0.1)`. AGENTS.md polls only where no
    callback exists. The fake `on_screen` is the test's own function, called once per sample.
  - **Scenario.** The test waits up to 0.1 s past its third sample, a time measured here rather than the callback.
  - **Fix.** The fake `on_screen` sets a `threading.Event` at its fourth call, by which the third sample is kept, and the
    test waits on it with its 30 s limit.
  - **Resolution: done.**
    - **Fix:** as suggested: the fake `on_screen` sets `third_kept` at its fourth read, and the test waits on it, 30 s at
      most. TST-503's new test waits the same way, on the first read.
    - **Also covered:** the file's other wait, in `test_the_front_watch_samples_the_active_app_and_the_windows_on_screen`,
      watches the real window server, where nothing calls back: it polls every 0.1 s, as AGENTS.md allows.

- [x] **TST-507 · Tests that need Unix run on Windows unmarked: the branch's two new ones and twelve beside them · follows SRV-175, TST-501, generation 2** · `tests/unit/test_lifecycle_env.py:1373` (`_forced_with`), `test_lifecycle_env.py:2316` (`_logs`) · confirmed · found 2026-11-17
  - **Defect.** `_logs` calls `_own_folder`, which calls `os.getuid()`, which Windows lacks. `_forced_with` records a
    home, so the quit reaches `_crash_uploads_off`'s `import fcntl`, which Windows lacks too. The branch's
    `test_the_log_of_a_designer_whose_record_goes_after_its_read_is_its_own` and `test_a_forced_quit_reads_its_record_once`
    use them without a skip, as twelve tests beside them already did:
    - through `_forced_with`: `test_a_forced_quit_after_every_window_closed_says_so_and_quotes_its_logs_last_line`,
      `test_a_forced_quit_says_it_had_not_closed_unless_its_session_logged_every_window_closed`,
      `test_a_forced_quit_with_no_log_of_its_own_says_so`, `test_a_forced_quit_reads_its_logs_tail_and_judges_this_session`;
    - through `_logs`: `test_the_log_of_a_designer_an_agent_started_is_its_own`,
      `test_the_log_of_an_agents_designer_that_has_ended_is_still_read`,
      `test_the_users_designer_on_a_port_is_read_from_the_shared_log`,
      `test_a_designer_an_agent_started_without_a_home_is_read_from_the_shared_log`,
      `test_the_log_with_the_processes_unlisted_isnt_chosen_as_none_running`,
      `test_an_ended_agents_log_is_read_while_the_users_designer_writes_the_shared_one`,
      `test_the_shared_log_is_read_when_the_users_designer_was_last_on_that_port`,
      `test_an_agents_designer_with_no_log_yet_isnt_read_from_the_shared_log`.
    The file's other tests of the same kind skip there (`_POSIX_QUIT`, `_HOMES_OF_THEIR_OWN`, the SRV-99 test's
    `skipif`), and ROADMAP item 18's list of the unit tests expected to fail on Windows names none of these.
  - **Scenario.** ROADMAP item 18's run of the unit suite on Windows fails these fourteen tests with `AttributeError`
    or `ModuleNotFoundError`, none of them expected.
  - **Fix.** Both helpers skip on Windows (`pytest.skip` when `sys.platform == 'win32'`), which covers every test using
    them, the next ones included.
  - **Resolution: done.**
    - **Test:** `test_the_helpers_that_need_unix_skip_on_windows` (`tests/unit/test_lifecycle_env.py`), over `_logs`
      and `_forced_with`, sets the platform to `win32` and expects a skip. Before the fix both failed with
      `DID NOT RAISE Skipped`.
    - **Cause:** the helpers reach code only Unix has, `_own_folder`'s `os.getuid()` and, through a recorded home,
      `_crash_uploads_off`'s `import fcntl`, and said nothing of Windows.
    - **Fix:** each skips at its start on Windows ("Windows lacks os.getuid", "Windows lacks fcntl"), `_logs` before it
      sets the platform to macOS. `test_a_designer_ending_while_its_log_is_read_is_not_reported_forced`, a forced quit
      with a home built without `_forced_with`, gets the same `skipif`.
    - **Also covered:** a simulation of Windows on macOS, a scratch pytest plugin (the platform `win32`, `fcntl`
      unimportable, no `os.getuid`, as ROADMAP item 18's of 2026-11-11), ran `test_lifecycle_env.py`. 51 cases failed
      before the fix. After it, the 17 through the helpers and the one above skip. The 33 left fail outside this
      pattern, in tests that were there before this branch: TST-508.
  - Note (2026-11-17): `test_the_helpers_that_need_unix_skip_on_windows` was folded into TST-508's
    `test_the_tests_that_depend_on_the_system_skip_on_windows`, which fails if either helper stops skipping: the tests
    using them then fail under the simulation.

- [x] **TST-508 · ROADMAP item 18's list of the unit tests expected to fail on Windows is stale: a simulation fails 33 cases in `test_lifecycle_env.py`** · `ROADMAP.md:139`, `tests/unit/test_lifecycle_env.py` · measured · found 2026-11-17
  - **Defect.** Item 18 names two unit tests that may fail on Windows, and seven cases of `test_lifecycle_env.py` found
    by a simulation on 2026-11-11. The same simulation run while addressing TST-507 (a scratch pytest plugin: the
    platform `win32`, `fcntl` unimportable, no `os.getuid`) fails 33 cases in 25 tests of that file, none through
    `_logs` or `_forced_with`:
    - 14 set the platform to macOS or Linux, then reach the launch lock's `import fcntl`, which the server itself skips
      on Windows (`_launch_lock`): a test's, not the tools';
    - 7 reach `os.getuid()` in the server's own folders (`_checked_folder`, `_own_folder`);
    - 8 assert what macOS records (a Designer remembered, its record read), where Windows records nothing;
    - 4 reach `socket.SO_EXCLUSIVEADDRUSE`, which macOS lacks and Windows has: the simulation's, not Windows'.
    The tests include `test_launch_state_not_running`, `test_launch_ends_an_agents_passing_the_limit`,
    `test_a_folder_that_isnt_ours_is_refused`, `test_a_record_read_while_it_is_written_isnt_lost` and
    `test_environment_overrides`. They were there before this branch.
  - **Scenario.** Someone running item 18's check on Windows meets about 29 failures the item doesn't name, and can't
    tell them from defects of the tools.
  - **Fix.** Either the tests that need Unix or macOS's records skip on Windows, as TST-507's did, each said in the
    marker, or item 18 names them, with the simulation that finds them.
  - **Resolution: done.** The user chose: the tests that depend on the system say which systems they run on and skip
    elsewhere; the others are left as they are.
    - **Test:** `test_the_tests_that_depend_on_the_system_skip_on_windows` (`tests/unit/test_windows_simulation.py`)
      runs, under `windows_simulation.py` (a pytest plugin made of the scratch simulation), every unit test file that
      mentions `sys.platform`, `fcntl` or `os.getuid`, but four it lists with why: twelve files today. It expects only
      what fails in the simulation alone to fail or err, five tests named with why. Before the marks, 35 cases failed
      in the three files holding them: those five, and 30 that depend on the system. With one mark removed for the run,
      it failed naming that test.
    - **Cause:** these tests set the platform to macOS or Linux, call what only Unix has, or check what only macOS
      does, and said nothing of it.
    - **Fix:** two markers in `test_lifecycle_env.py`, one per cause: `_SETS_UNIX` on the 12 tests that set the
      platform, `_RECORDED` ("nothing is recorded there", the file's reason already) on the 7 that check what macOS
      records. `test_the_temp_folder_leaves_room_for_designers_socket` skips on Windows (a Unix socket's path, named
      with `os.getuid`), and `test_a_menu_picked_has_its_window_given_its_look_back_once_closed` off macOS (only macOS
      holds a window transparent). `test_never_registers_globally` runs on Windows too: it expects `.mcp.json` named only
      off Windows, as the installer does (REVIEW.md INS-24). AGENTS.md says how such a test says so, and ROADMAP item 18
      points at the simulation instead of its list.
    - **Also covered:** the simulation run over the whole unit suite. Outside the three files, what fails is the
      simulation's alone: `test_plugin.py`'s 66 cases reach `socket.SO_EXCLUSIVEADDRUSE`, which macOS lacks and Windows
      has; `test_review_lookup.py` (collected) and `test_sbs.py::test_sbsar_default_size` reach Windows' `_winapi`
      through `shutil.which`. The four `SO_EXCLUSIVEADDRUSE` cases and the subprocess of `test_environment_overrides` in
      `test_lifecycle_env.py` are the five listed in the test.

- [x] **TST-509 · The Windows simulation removes only `fcntl` and `os.getuid`: 17 cases using other names Windows lacks fail there unmarked · follows TST-508, generation 2** · `tests/unit/windows_simulation.py:12-15`, `tests/unit/test_windows_simulation.py` (`_system_files`), AGENTS.md (the paragraph on tests that depend on the system), `ROADMAP.md:139` · measured · found 2026-11-17
  - **Defect.** Windows also lacks `signal.SIGKILL`, `signal.SIGALRM`, `signal.setitimer`, `os.geteuid`, `termios` and
    `resource`, which the code or its tests use. `_force_end` (`server_tools/lifecycle.py:903`) takes `signal.SIGKILL`.
    On Windows nothing is recorded, so the tools never reach it there, but tests that write a record themselves do.
    `test_library_subfolders.py:117` calls `os.geteuid()`, and `_system_files`' pattern (`getuid`) doesn't pick it up.
  - **Scenario.** The probe removed those names too and ran the simulation over the files mentioning any of them. 17
    more cases failed: 16 in `test_lifecycle_env.py` that force an agent's Designer to end
    (`test_quit_forces_harder_if_it_must`, `test_quit_forces_an_agents_that_stays`,
    `test_a_forced_quit_reads_no_log_but_its_own`, `test_the_close_has_a_limit_of_its_own` (2),
    `test_quit_doesnt_queue_behind_a_job` (2), `test_a_process_gone_or_not_ours_to_signal_doesnt_raise`,
    `test_a_forced_end_waits_for_the_processs_exit_after_each_signal`, `test_launch_stops_at_an_agents_it_cant_end`,
    `test_launch_says_it_ended_one_even_if_the_new_one_fails`, `test_quit_leaves_the_users_next_to_the_agents`,
    `test_quit_says_so_if_even_that_fails`, `test_quit_forces_an_agents_with_no_bridge`,
    `test_quit_names_the_process_it_means`, `test_quit_with_another_designer_on_the_port_only_ends_its_own`), and
    `test_library_subfolders.py::test_an_unreadable_library_subfolder_is_an_error`. A run on Windows meets them, as TST-508
    said of the others, while AGENTS.md and ROADMAP item 18 say the tests that depend on the system skip there.
  - **Fix.** The plugin removes every name Windows lacks that the code uses, the pattern picks the files using them,
    the 17 cases are marked, and AGENTS.md and item 18 say the simulation removes those names, not that it is Windows.
  - **Resolution: done.**
    - **Test:** `test_the_tests_that_depend_on_the_system_skip_on_windows`, run with the widened plugin before any mark:
      22 failed, the five `SIMULATION_ONLY` cases and the 17 of the scenario.
    - **Cause:** the plugin took away two of the Unix-only names the code uses, and the guard's pattern looked for
      those two.
    - **Fix:** `windows_simulation.py` lists what it takes away: `POSIX_ONLY`, the modules only Unix has, now shared with
      `test_lint.py`, whose list it was (all made unimportable but `posix`, which `os` is built on), and `NAMES`
      (`os.getuid`, `os.geteuid`, `signal.SIGKILL`, `signal.SIGALRM`, `signal.setitimer`, `signal.ITIMER_REAL`). The
      guard builds its pattern from those lists (`MENTIONS`), so they can't drift apart. `_FORCE_ENDS` marks the
      14 tests (16 cases) that end a recorded Designer; `test_an_unreadable_library_subfolder_is_an_error` skips on
      Windows, its folder made unreadable by POSIX permissions. AGENTS.md and item 18 say what the simulation takes
      away, and that a test depending on Windows otherwise shows only in a run there.
    - **Also covered:** searched the code and tests for the names Windows lacks (`git grep` of `signal.SIG*`,
      `os.get*id`, `os.killpg`, `os.fork`, `socket.AF_UNIX`, `termios`, `resource`, `pwd`, `grp`): only those listed are
      used. `tests/test_all_tools/common.py`'s `end_own_designer` takes `signal.SIGKILL` only after reading a record,
      which Windows never writes; its `except` says so in a line.

- [x] **TST-510 · `_SETS_UNIX` marks two tests whole, skipping their `win32` cases, the checks of Windows' own launch · follows TST-508, generation 2** · `tests/unit/test_lifecycle_env.py:2220`, `test_lifecycle_env.py:2237` · confirmed · found 2026-11-17
  - **Defect.** `test_each_designer_started_has_a_temp_folder_of_its_own` and
    `test_each_designer_started_on_macos_has_a_home_of_its_own` are parametrized over `darwin`, `linux` and `win32`.
    Their `win32` case sets Windows, where the launch makes no folder and takes no lock, and passed under the
    simulation. `_SETS_UNIX`, on the whole test, skips it on Windows too, saying it "sets the platform to macOS or
    Linux".
  - **Scenario.** On Windows, the only checks of the launch's environment there never run.
  - **Fix.** The mark on the `darwin` and `linux` cases only: `pytest.param('darwin', marks=_SETS_UNIX)`.
  - **Resolution: done.**
    - **Test:** the guard runs verbose now and fails on any `win32` case skipped under the simulation. Before the fix
      the run listed `test_each_designer_started_has_a_temp_folder_of_its_own[win32] SKIPPED` and
      `test_each_designer_started_on_macos_has_a_home_of_its_own[win32] SKIPPED`.
    - **Fix:** both tests' `darwin` and `linux` cases carry `_SETS_UNIX` through `pytest.param`; the `win32` case runs.
    - **Also covered:** the three other tests parametrized over platforms (one in `test_lifecycle_env.py`, two in
      `test_view3d_helpers.py`, each over `darwin` and `win32`) carry no mark; the guard's check covers any later one.

- [x] **TST-511 · A mark's reason and a comment say what isn't so · follows TST-508, generation 2** · `tests/unit/test_lifecycle_env.py:2862`, `tests/unit/test_windows_simulation.py:19` · confirmed · found 2026-11-17
  - **Defect.**
    - `test_a_failed_process_listing_keeps_a_live_record` is marked `_RECORDED` ("nothing is recorded there"). It
      writes its own record, and fails on Windows because Windows lists processes with `tasklist`, not `pgrep`; its
      neighbours say so (`'tasklist, not pgrep, lists them on Windows'`, line 2897).
    - `SIMULATION_ONLY`'s comment says its five cases fail "only in the simulation, not on Windows". No run on Windows
      measured it (ROADMAP item 18).
  - **Scenario.** Once Windows records its Designers, someone drops the skip the reason names, and the test still fails.
    A reader takes the five cases for passing on Windows.
  - **Fix.** The neighbours' reason on that test; the comment says the five fail in the simulation for its own reasons.
  - **Resolution: done.**
    - **Fix:** as suggested: `'tasklist, not pgrep, lists them on Windows'` on the test, and `SIMULATION_ONLY`'s comment
      says its cases fail in the simulation for reasons of its own, unmeasured on Windows (ROADMAP item 18).
    - **Also covered:** every other mark of the branch read against its test: `_SETS_UNIX` on tests that set macOS,
      `_RECORDED` on tests checking a record, `_FORCE_ENDS` on tests ending a recorded Designer.

- [x] **TST-512 · The guard's `failed` is a `set[Any]`, from `re.findall`** · `tests/unit/test_windows_simulation.py:56` · confirmed · found 2026-11-17
  - **Defect.** `failed = set(re.findall(...))`: typeshed gives `re.findall` `list[Any]`, so mypy checks nothing of
    `failed`. AGENTS.md asks for such an implicit `Any` to be narrowed in a function the branch adds (TST-498 was the
    same).
  - **Scenario.** A second group in the pattern makes `failed` a set of tuples; mypy says nothing.
  - **Fix.** `failed: set[str] = ...`.
  - **Resolution: done.**
    - **Fix:** as suggested. The new `skipped` is a `list[str]` from `re.findall` too, used only in the assertion and its
      message.

- [x] **TST-513 · TST-506's Also covered says the file's other wait has no callback; one can be had · follows TST-506, generation 2** · `tests/unit/test_selftest_window_server.py:179-185` · confirmed · found 2026-11-17
  - **Defect.** TST-506's resolution says `test_the_front_watch_samples_the_active_app_and_the_windows_on_screen`
    watches the real window server, "where nothing calls back", so it polls every 0.1 s. The test can wrap the real
    `on_screen` in one of its own that sets an `Event` at its third call, as TST-506's fix did with a fake: the watch
    still reads the real window server.
  - **Scenario.** The test waits up to 0.1 s past its second sample, a measured time, where a callback exists.
  - **Fix.** The wrapper and an `Event`, waited on with the 30 s limit.
  - **Resolution: done.**
    - **Fix:** the test wraps the real `on_screen`, which sets `second_kept` at its third read, once the second sample is
      kept, and waits on it 30 s at most.
    - **Also covered:** no wait in `tests/unit/test_selftest_window_server.py` polls now.

- [x] **TST-514 · The naming test can't tell a watch that names apps through their popups** · `tests/unit/test_selftest_window_server.py:411` · confirmed · found 2026-11-17
  - **Defect.** The first read lists `(POPUP, 1.0, PID, LEFT)`, and PID shows a normal window from the second read on.
    A watch naming every owner, the popup's included, names PID in the first read instead of the second: `named` is
    still `[OTHER, PID]`. Only the transparent window of `PID + 2` checks what isn't named.
  - **Scenario.** `_shown` changed to filter on opacity alone passes the test, though `FrontWatch`'s docstring and the
    test's comment say a popup isn't named.
  - **Fix.** The popup belongs to a process that never shows a normal window (`PID + 3`), expected never named.
  - **Resolution: done.**
    - **Test:** the first read lists the popup of `PID + 3`, which shows no normal window; `named` must be
      `[OTHER, PID]`. With `_shown` changed for the run to filter on opacity alone, the test failed with
      `[43, 45, 42]`; the code put back, it passes.
    - **Fix:** the test only; `_shown` filters on the layer already.
