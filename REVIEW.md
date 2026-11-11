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

**Last used:** PLG-42, SRV-118, HLP-106, INS-27, TST-314.

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
| Low | 0 | 15 |
| **Total** | **0** | **15** |

## Review log

### 2026-11-11: branch `quit-hang-cause` against main (ROADMAP item 70: a sample before a forced quit), the diff only

- **How:** one reviewer, the whole diff (7 files); no tests run. The lead settled the suspicions by reading and by
  plain-process probes of macOS's `sample` on dummy Python processes, no Designer: `sample` killed after 0.2, 0.5,
  0.9, 1.3 and 2 s of a 5 s sample; a file already at its path; a target ending mid-sample; a process ID not running.
  And the four `_sampling` unit tests run with `fcntl` unimportable (`sys.modules['fcntl'] = None`), as on Windows.
- **Not verified:** none.
- **Settled as wrong:** a `sample` killed at its time limit leaving Designer suspended (each time the target went on
  running and SIGTERM ended it); a stale file named as fresh (`sample` overwrites a file at its path, and writes one,
  exit 0, when its target ends mid-sample; its errors go to stderr, exit 255); a decoding error escaping `_sample`
  (what it prints is ASCII: its messages, the process's name, the path in `/tmp/sd_mcp_<uid>_<port>`). Not raised: the
  tool docstring naming the file (it says what the result holds, as for the log's line); ROADMAP item 70's wording.
- **Resolutions assessed:** none (a new branch).
- **Findings:** SRV-111 to SRV-114, TST-308 to TST-310 (Low), all generation 1.
- **Suggested order:** SRV-111 (a misreported quit), SRV-112, SRV-113, then TST-308 to TST-310 and SRV-114.
- **Checked and found fine:** the order sample, second look, force (guarded by the ending-while-sampled test); the
  result's wording against `closed_by_quit`, `normal_close`, the pool's `'forced' in quit`, `quit after (\d+)s` and
  `sampled first: (\S+)` (no punctuation after the path); the 30 s limit against the busy and frozen checks'
  `took < 30`; Windows and the no-folder case; the path in a folder `_checked_folder` vouches for (this user's, not a
  link, made 0o700); never the user's Designer (the start-checked record `_force_end` then ends); `capture_output`
  keeping `sample`'s output off the MCP stream; the unit tests' guard against a real sample; each new unit test
  failing without its change; the live check failing for the right reason; the sample files' fate (the pool's
  clean-up, `uninstall.py`); the run times against the four full runs and DECISIONS.md.

### 2026-11-11: branch `quit-hang-cause` against main, the whole diff, after SRV-111 to TST-310

- **How:** one reviewer, the whole diff; no tests run (it evaluated `samples.py`'s two regexes on example names). The
  lead: the detail printed by lifecycle's sample check, measured against `check`'s cut (149 characters printed of
  233); the name regex on six C++ and Objective-C names; and a scratch probe repeating the launch sample check's
  scenario ten times in a Designer of its own (a task held in the thread pool, the windows closed, the bridge gone, the
  record aged, `launch_designer`).
- **Not verified:** none.
- **Settled as wrong:** the launch sample check sampling before the shutdown reaches the thread pool's wait, and so
  failing now and then: in ten tries every sample had the main thread in `QThreadPool::waitForDone` (sampled within a
  second of the bridge going), as in three scratch runs of `lifecycle`; the one earlier sample whose heaviest path ran
  through `FSEventStream` held that wait too. Not raised: the new test helpers inline in their test files (they build
  on `_Processes` and `_closes`, inline there too: moving them alone would split them); `launch_designer`'s docstring
  not naming the sample (its note does).
- **Resolutions assessed:** all seven; their fixes hold. Questioned: SRV-113 and SRV-114 (SRV-116), TST-310 (TST-311,
  TST-312), SRV-114 and TST-308 to TST-310 (TST-313, their records).
- **Findings:** SRV-115, SRV-116, TST-311, TST-312, TST-313 (Low). Longest chain: TST-310 → TST-311 / TST-312,
  generation 2.
- **Suggested order:** SRV-115 (a hang's sample lost), TST-311, TST-312, then SRV-116 and TST-313.
- **Checked and found fine:** `_end_if_past_startup`'s `str | None` and both callers (`is None`, so a launch without a
  sample still notes the end; the note's wording still matched where tested); the result's wording against
  `closed_by_quit`, `normal_close`, the pool's `'forced' in quit` and `quit after (\d+)s`; SRV-111's order and test;
  both errors naming the sample; `_force_end`'s other callers and `common.end_own_designer` (no hang to sample); the
  `_POSIX_QUIT` marker on the nine tests that need it; the `CALL` regex on `sample`'s format (branch marks, `???`
  lines, the next thread ending the path, the count's column as depth); the conftest guard; the run times; ROADMAP
  item 70; REVIEW.md's table, Last used and resolution wordings.

### 2026-11-11: branch `quit-hang-cause` against main, the whole diff, after SRV-115 to TST-313

- **How:** one reviewer, the whole diff; no tests run (it evaluated `_bare` and `CALL` on about 20 odd names). The lead
  settled the rest by reading.
- **Not verified:** none.
- **Settled as wrong:** README's "about 300 KB" (measured 270 to 350 KB in the first review's probe).
- **Not raised** (DECISIONS.md, Project rules: low-value findings about the tests and docs): lifecycle's own readers of
  a quit (`common.normal_close`, the other port's `remove_its_folder`) keeping no folder for a quit that names a sample,
  which shows only when one of its normal closes ends while sampled, unseen here, its worst a temporary folder deleted;
  a docstring line of `lifecycle.py` left at 190 characters by SRV-116's rewrap; the second review's resolutions
  without every line TST-313 asked of the first's; ROADMAP item 18's "(those two first)", still true.
- **Resolutions assessed:** SRV-115, SRV-116, TST-311 to TST-313; their fixes hold. Questioned: SRV-115 (SRV-118,
  TST-314), SRV-116 (SRV-118), TST-313 (SRV-117).
- **Findings:** SRV-117, SRV-118, TST-314 (Low). Longest chain: SRV-114 → TST-313 → SRV-117, generation 3 (the tools'
  code, so raised); SRV-118 at 3 narrows sentences.
- **Suggested order:** SRV-117, TST-314, SRV-118.
- **Simplifications:** `run_pool`'s `keep` reads `(part.get('quit') or '')` twice; a small helper would read better.
- **Checked and found fine:** every reader of `QUIT_SAMPLED` (the failure sentence, "could not be sampled first", never
  matches it, nor holds "forced"); `(\S+)` ending at the launch note's newline; `_bare` and `CALL` on `(anonymous
  namespace)`, `operator()()`, `operator()(int) const`, nested and tagged templates, Objective-C, empty and unbalanced
  names (bounded, can't raise); the `keep` set; lifecycle's deliberate forced quits' folder deleted, their detail the
  main thread; both callers of `_end_if_past_startup`; `layout.py:138` and its test; ROADMAP item 18's seven cases;
  REVIEW.md's Last used, table, Questioned-by lines and generations.

---

## High

## Medium-high

## Medium

## Low-medium

## Low

- [x] **SRV-111 · The log is read before the sample, so a close taking during the sample is reported "had not closed"** · `mcp_server/server_tools/lifecycle.py:844-845` · confirmed · found 2026-11-11
  - **Defect.** `evidence = _quit_evidence(port)` comes before `sampled = _sampled_before_force(own, port)`, which
    takes 1.4 to 1.9 s (measured); the force follows the sample, so the evidence is that much older than before.
  - **Scenario.** A close that takes just past the wait, while the sample runs, Designer then hanging in its shutdown:
    "forced: it had not closed" quoting an older line, and the self-test fails that quit (`closed_by_quit`).
  - **Fix.** Sample first, then read the log, then look again and force: the log as close to the force as before.
  - **Resolution: done.**
    - **Test:** `test_a_close_logged_while_it_is_sampled_counts` (the fake sample logs the close): failed, "forced: it
      had not closed"; passes now.
    - **Cause:** the sample was put after the log's read.
    - **Fix:** `quit_designer` samples, then reads the log, then looks again and forces.
    - **Also covered:** `launch_designer`'s force (SRV-113) reads no log.

- [x] **SRV-112 · A force that fails drops the sample from its error** · `mcp_server/server_tools/lifecycle.py:858` · confirmed · found 2026-11-11
  - **Defect.** `raise ToolError(_could_not_end(own))` leaves out `sampled`, though the file was written.
  - **Scenario.** A Designer that SIGKILL can't end, when its stacks matter most: the error names no sample.
  - **Fix.** Add `sampled` to the error; a unit test of a process that doesn't end.
  - **Resolution: done.**
    - **Test:** `test_a_force_that_fails_names_the_sample`: failed, the error naming no sample; passes now.
    - **Cause:** the error was built before the sample existed, and wasn't changed with it.
    - **Fix:** `quit_designer`'s error adds the sample's sentence.
    - **Also covered:** `launch_designer`'s (`test_launch_names_the_sample_of_one_it_cant_end`, with SRV-113).

- [x] **SRV-113 · `launch_designer` force-ends an agent's Designer past its start-up with no sample** · `mcp_server/server_tools/lifecycle.py:568-577` (`_end_if_past_startup`) · confirmed · found 2026-11-11
  - **Defect.** The other path that forces an agent's Designer, one not answering past `STARTUP_LIMIT`, calls
    `_force_end` without `_sampled_before_force`; it can be one hung in its shutdown, as lifecycle's "ends an agent's
    Designer not answering" check builds with `hold_thread_pool`.
  - **Scenario.** A quit interrupted after its close, Designer hanging in its shutdown, ended by the next
    `launch_designer`: no evidence of the hang.
  - **Fix.** Sample there too and name the file in its "Ended a Designer an agent started" note; a unit test, and the
    live check's result read.
  - **Resolution: done.**
    - **Test:** `test_launch_samples_an_agents_it_ends` and `test_launch_names_the_sample_of_one_it_cant_end`: failed, no
      sample taken; and `lifecycle`'s new "samples the agent's Designer it ends before forcing it, the thread pool's
      wait shown", in a scratch run: failed, no sample named; all pass now.
    - **Cause:** only `quit_designer`'s force was given a sample.
    - **Fix:** `_end_if_past_startup` samples before `_force_end` and returns the sentence (None when it ended nothing);
      `launch_designer`'s note names the file, and its error when the force fails. The module's "Quitting." says both.
    - **Also covered:** `_force_end`'s other caller, `launch_designer`'s cleanup of one it started and can't record,
      ends a process just started: nothing hung there to sample.
  - Questioned by SRV-116 (2026-11-11).

- [x] **SRV-114 · The sampling's wording: a doubled period, the time in three places, a sentence out of order** · `mcp_server/server_tools/lifecycle.py:26-34, 780, 804`, `tests/unit/test_lifecycle_env.py:977` · confirmed · found 2026-11-11
  - **Defect.** `' Its threads could not be sampled first: %s.'` with `sample`'s own message, which ends in a period
    (measured: "...because it no longer appears to be running."): "..". "About 1.5 s" is stated in the module
    docstring, `_sample`'s and a test comment, for 1.4 to 1.9 s measured. The module's sample sentence now comes before
    "So quit_designer only closes the windows", which follows from the sentences before it, not from the sample.
  - **Scenario.** A reader of a failed sample sees "running.."; a reader of the module reads the "So" as following
    from the sample.
  - **Fix.** Strip a trailing period from the message; the time once, "1.5 to 2 s", in the module docstring; the
    sample sentence after the "So" sentence.
  - **Resolution: done.**
    - **Test:** `test_a_forced_quit_whose_sample_fails_is_forced_and_says_why`, with `sample`'s message as measured:
      failed, "running.."; passes now.
    - **Fix:** the message's own period stripped; "1.5 to 2 s" once, in the module docstring, `_sample`'s and the test
      comment no longer saying it; the sample sentence after "So quit_designer only closes the windows".
    - **Cause:** the sentence added its own period after a message that ends in one.
    - **Also covered** (added for TST-313): the server's other sentences with a message before a period (`%s.' %`):
      `layout.py`'s "could not reopen %s: %s." took a `ToolError`'s text, which ends in one: fixed the same way, its
      test (`test_set_link_display_reports_success_when_the_reopen_fails`, the error now ending in a period) failed with
      "..", passes; `lifecycle.py`'s list of other ports and `snapshots.py`'s graph name end in none.
  - Questioned by SRV-116, TST-313 (2026-11-11).

- [x] **TST-308 · The four `_sampling` unit tests fail on Windows** · `tests/unit/test_lifecycle_env.py:917-985` · measured · found 2026-11-11
  - **Defect.** `_sampling` sets `sys.platform` to `'darwin'`, so the quit's `_forget_started` passes
    `_launch_lock_if_free`'s Windows guard and runs `import fcntl`. Run with `fcntl` unimportable (2026-11-11), all four
    failed with `ModuleNotFoundError` at `lifecycle.py:419`.
  - **Scenario.** The unit suite on Windows (AGENTS.md: run `pytest` there): four more failures besides the two
    ROADMAP item 18 expects.
  - **Fix.** Skip them on Windows (`skipif(sys.platform == 'win32')`, as the neighbouring tests that need POSIX do), or
    patch `_forget_started` in `_sampling`.
  - **Resolution: done.**
    - **Test:** the sampling tests collected as on Windows (a scratch pytest plugin: `sys.platform` reading `win32`
      while `test_lifecycle_env.py` is collected, `fcntl` unimportable): with the marker off, nine failed at `import
      fcntl`; with it, nine skipped.
    - **Fix:** `_POSIX_QUIT`, the neighbours' `skipif(sys.platform == 'win32')`, on every test that runs a quit or a
      launch through `_sampling` or `_fake_sample`; the one calling `_sampled_before_force` alone runs there.
    - **Cause:** `_sampling` forces macOS, so the quit's clean-up takes the macOS path, which imports `fcntl`.
    - **Also covered** (added for TST-313): the file's other tests that force macOS or Linux, run as on Windows (the
      platform `win32` for each test too): seven cases reach the launch lock's `import fcntl`
      (`test_launch_starts_the_binary_with_the_port`, `test_each_designer_started_has_a_temp_folder_of_its_own`,
      `test_each_designer_started_on_macos_has_a_home_of_its_own`, two each, and
      `test_the_record_says_which_home_the_designer_got`): outside this branch, listed in ROADMAP item 18 beside the two
      it names. The simulation's other failures come from macOS standing in for Windows, not from Windows.
  - Questioned by TST-313 (2026-11-11).

- [x] **TST-309 · No unit test sees a Designer that quits within its wait being sampled, nor `sample` missing** · `tests/unit/test_lifecycle_env.py:917-1012` · confirmed · found 2026-11-11
  - **Defect.** With `_sampled_before_force` moved above the wait loop, every test passes: the normal quit has no
    folder, and the `_sampling` tests' Designer stays or ends in the sample. `_sample`'s `OSError` branch (no
    `/usr/bin/sample`) is never run.
  - **Scenario.** A change that samples every quit, 1.5 to 2 s and a file each, goes unseen.
  - **Fix.** A `_sampling` test whose Designer ends within the wait, asserting no sample; an `OSError` case in the
    parametrized `_sample` test.
  - **Resolution: done.**
    - **Test:** `test_a_designer_quitting_within_its_wait_is_not_sampled` and an `OSError` case of
      `test_sample_runs_macos_sample_for_a_second_into_the_file`: both pass on the code; with the sample moved above
      the wait, the first failed, and with `OSError` no longer caught, the second.
    - **Fix:** the tests.
    - **Cause:** the new tests covered what a sample does, not when none is taken.
    - **Also covered** (added for TST-313): `launch_designer`'s sample (SRV-113), by reading: `_end_if_past_startup`
      samples only once it has decided to end one.
  - Questioned by TST-313 (2026-11-11).

- [x] **TST-310 · When the new live check fails, its detail names a file the pool then deletes** · `tests/test_all_tools/lifecycle/checks.py:555-564`, `tests/test_all_tools/workers.py` (`_clean_up`) · confirmed · found 2026-11-11
  - **Defect.** The detail is only the sample's path; lifecycle's deliberate forced quits don't put its port in
    `forced`, so `_clean_up` deletes the folder, the sample with it.
  - **Scenario.** A full run where the stuck Designer's main thread waits elsewhere: the check fails and what it
    waited on is gone.
  - **Fix.** Put the main thread's first frames in the detail (the lines after its `com.apple.main-thread` header).
  - **Resolution: done.**
    - **Test:** `test_the_main_threads_heaviest_calls_are_read_from_a_sample` and
      `test_a_result_naming_a_sample_gives_its_text_and_where_the_main_thread_was`, on a sample's text as `sample`
      writes it: failed on the stubs; pass now.
    - **Fix:** `tests/test_all_tools/lifecycle/samples.py`: `sampled` reads the file a result names, `main_thread` the
      main thread's heaviest path, its deepest six calls outside `libsystem_*`, without arguments; both sample checks
      give that, then the path. A first version kept the system's calls and arguments: in a scratch run four `mach_msg`
      calls filled the check's 150 characters, the call above them cut off.
    - **Cause:** the check's detail was the sample's path, which the pool deletes with lifecycle's folder.
    - **Also covered** (added for TST-313): the launch sample check (SRV-113) reads it the same way.
  - Questioned by TST-311, TST-312, TST-313 (2026-11-11).

- [x] **SRV-115 · A Designer ending while it is sampled leaves its sample unnamed, and the pool deletes it** · `mcp_server/server_tools/lifecycle.py:850-856`, `_sampled_before_force`'s file name, `tests/test_all_tools/workers.py` (`run_pool`'s `forced`) · confirmed · found 2026-11-11
  - **Defect.** After the sample, a Designer that has ended is a plain quit: "Designer quit after Ns.", the sample not
    named, though `sample` writes its file when its target ends mid-sample (measured in the first review). The pool
    keeps a folder only for a quit result holding "forced", so that file goes. And the file's name,
    `forced_quit_<pid>.sample.txt`, holds "forced": named in a plain quit, it would fail `closed_by_quit`.
  - **Scenario.** A category's quit, `wait_s` 30, its shutdown hanging and ending by itself at 31 s, during the sample:
    an item-70 hang caught, and its evidence deleted.
  - **Fix.** A file name without "forced"; the sample named in that result too; the pool keeping a folder whose quit
    names a sample; unit tests of both.
  - **Resolution: done.**
    - **Test:** `test_a_designer_ending_while_sampled_is_not_reported_forced` (its fake sample writes the file as the
      process ends): failed, the result naming no sample; `test_a_quit_ending_while_sampled_passes_and_keeps_its_folder`
      (`test_selftest_pool.py`): failed, the folder deleted; both pass now.
    - **Cause:** the plain quit's result was written before the sample existed; the pool kept folders by "forced" alone.
    - **Fix:** the file is `threads_<pid>.sample.txt`; the plain quit after a sample names it; the sentence's words are
      `QUIT_SAMPLED` (`project_constants.py`), which `run_pool` reads to keep a folder (printing "kept, its quit was
      forced or sampled") and `check_the_quits` to print the quit whole; the pool's docstring says so.
    - **Also covered:** `launch_designer`'s note names the file too, its old name no longer in a result; a scratch run
      of `lifecycle` (48 checks, none failed) named `threads_<pid>.sample.txt` in every forced quit.
  - Questioned by SRV-118, TST-314 (2026-11-11).
  - Note (2026-11-11): `test_selftest_lifecycle.py`'s
    sample test still names its file `forced_quit_11.sample.txt`, the old name; `sampled` reads any path.

- [x] **SRV-116 · The sampling's sentences and formatting: claims beyond the checks, long lines, a split call, a shadowed name · follows SRV-113 and SRV-114, generation 2** · `mcp_server/server_tools/lifecycle.py:33-35, 570-572, 690, 735, 818, 851-853`, `tests/unit/test_selftest_lifecycle.py` (`SAMPLE`'s comment), `tests/test_all_tools/lifecycle/samples.py:9`, `README.md:386` · confirmed · found 2026-11-11
  - **Defect.** "shows its main thread in `QThreadPool::waitForDone` (measured, lifecycle's two sample checks)": both
    checks test the string anywhere in the file. `_end_if_past_startup`'s "the sentence naming the file ('' for none)":
    a failed sample's sentence names none; "Its threads sampled first, as..." isn't a sentence. `SAMPLE`'s "as macOS's
    sample writes it (measured...)": the format is, its `QThreadPoolPrivate::reset()` sibling isn't. "on macOS,
    macOS's `sample` ... into its own folder" reads as `sample`'s folder. Lines 35 (159 characters) and 818 (174) left
    unwrapped in docstrings; `_quit_evidence(port)` split over three lines by its comment; the outer `ended`
    (`str | None`) shadowed by `start()`'s (bool); two spaces in a regex PyCharm flags. README's agent folders hold
    "settings, log and crash dumps": samples too now.
  - **Scenario.** A reader takes the main thread as checked, or the comment's sample as measured.
  - **Fix.** Narrow each sentence, or check the main thread's path (`main_thread`); wrap the lines, the comment on its
    own line, `ended` renamed outside `start()`, ` {2}` in the regex; README's folders list samples.
  - **Resolution: done.** No behaviour changes, the touched tests run before and after (`test_lifecycle_env.py`,
    `test_selftest_lifecycle.py`). The module's sentence says the sample "holds `QThreadPool::waitForDone`", and that the
    server runs `sample`, into that Designer's folder; `_end_if_past_startup`'s docstring names what it returns;
    `SAMPLE`'s comment says the format is measured and the sibling made up; the long lines wrapped, the tool docstring's
    paragraph with them (its words unchanged); `_quit_evidence(port)` on one line under its comment; the outer `ended`
    is `ended_sample`; ` {2}` in `CALL`; README's agent folders hold the sample of one about to be forced, about 300 KB.
  - Questioned by SRV-118 (2026-11-11).

- [x] **TST-311 · The sample parser cuts Objective-C and template names, and drops the C library's calls · follows TST-310, generation 2** · `tests/test_all_tools/lifecycle/samples.py:10, 39`, `tests/unit/test_selftest_lifecycle.py` (its tests) · confirmed · found 2026-11-11
  - **Defect.** `re.sub(r'(?<=[\w~>])\(.*$', '', name)` cuts at the first `(` after a word character, evaluated:
    `-[NSApplication(NSAppleEventHandling) _handleAEQuit]` → `-[NSApplication`; `std::__1::__function::__func<Foo::bar()
    ::$_0, ...>::operator()()` → `std::__1::__function::__func<Foo::bar`; `Foo<decltype(x)>::f()` → `Foo<decltype`.
    `SYSTEM = 'libsystem_'` also drops `libsystem_c` (`exit`, `__cxa_finalize_ranges`), `libsystem_malloc` and
    `libsystem_platform`, more than its comment's "the kernel's and pthread's waits". `sampled first: (\S+)` matches
    the failure sentence's first word too (harmless: not a file). Its test has no same-depth sibling after a leaf
    (`<=` and `<` pass alike) and no Objective-C name.
  - **Scenario.** Item 69's hang began in AppKit's termination: a failing check's detail reads `-[NSApplication <
    -[NSApplication`, the selectors lost; a hang in the exit handlers shows none of them.
  - **Fix.** Strip only a balanced argument list at the end (and a trailing ` const`), leaving names ending in `]`;
    leave out only `libsystem_kernel` and `libsystem_pthread`; anchor on "Its threads, sampled first: "; test cases for
    those names and a sibling after a leaf.
  - **Resolution: done.**
    - **Test:** `test_the_main_threads_calls_keep_their_names_and_the_c_librarys` (an AppKit category method, a lambda's
      call operator, a const template member, `exit`, a kernel wait and a lighter sibling): failed, "Foo<decltype <
      std::__1::__function::__func<Foo::bar < -[NSApplication < start"; passes now, and fails again with `<=` made `<`.
    - **Cause:** the regex cut at the first `(` after a word character; `libsystem_` held the C library too.
    - **Fix:** `_bare` strips only the balanced argument list at the end and a trailing ` const`, leaving a name ending
      in `]` whole; `SYSTEM` is `libsystem_kernel` and `libsystem_pthread`; `sampled` matches `QUIT_SAMPLED`.

- [x] **TST-312 · The sample checks' detail is cut before its path · follows TST-310, generation 2** · `tests/test_all_tools/lifecycle/samples.py:20, 23`, `tests/test_all_tools/common.py:61` · confirmed · found 2026-11-11
  - **Defect.** `check` prints `detail.strip()[:150]`; six frames fill it (149 characters printed of 233, measured on
    the scratch run's line), so "then the path" in `sampled`'s docstring and TST-310's resolution is never printed.
  - **Scenario.** A check failing in a scratch run, its folder kept: nothing printed says where the sample is.
  - **Fix.** Fewer frames, or the path left out of the detail and the docstring saying so.
  - **Resolution: done.**
    - **Test:** `test_a_result_naming_a_sample_gives_its_text_and_where_the_main_thread_was` asserts the detail is the
      main thread's calls alone: failed, the path after them; passes now.
    - **Cause:** the calls fill the 150 characters `check` prints.
    - **Fix:** `sampled`'s detail leaves the path out, and its docstring says why.

- [x] **TST-313 · Four resolutions and the last log entry leave out what the template asks for · follows SRV-114 and TST-308 to TST-310, generation 2** · `REVIEW.md` (SRV-114, TST-308, TST-309, TST-310; the log entry of the first review) · confirmed · found 2026-11-11
  - **Defect.** The address-review skill (step 7) asks a fix's resolution for its **Cause** and **Also covered**: these
    four give **Test** and **Fix** only (SRV-114's search for the doubled period elsewhere unrecorded). The template's
    log entry has a **Not verified** bullet, "none, if none": the first review's has none.
  - **Scenario.** A reader can't tell whether the pattern was looked for elsewhere.
  - **Fix.** Add the missing lines.
  - **Resolution: done.** SRV-114, TST-308, TST-309 and TST-310 have their **Cause** and **Also covered**, marked as
    added for this finding; the first review's log entry has its **Not verified** line. Searching for them found more:
    `layout.py`'s doubled period, fixed with a test (SRV-114's Also covered), and seven older tests that would fail on
    Windows, listed in ROADMAP item 18 (TST-308's).
  - Questioned by SRV-117 (2026-11-11).

- [x] **SRV-117 · `_reload_package_file`'s error doubles a period, and the reopen warning can end "?." · follows TST-313, generation 3** · `mcp_server/server_tools/layout.py:231-235, 140` · confirmed · found 2026-11-11
  - **Defect.** `'%s. The package was closed in Designer and could not be opened again: ...' % (e, ...)` puts a
    `ToolError`'s text before a period, and those end in one ("Designer closed the connection without a reply (it may
    be starting or quitting)."): "..". SRV-114's search looked for `%s.'` only, a period ending the string. The reopen
    warning's `str(e).rstrip('.')` then adds one after a message ending in "?" ("Is the ... plugin loaded in
    Designer?"): "?.".
  - **Scenario.** `set_link_display` whose reload fails as Designer quits: "...quitting).. The package was closed...".
  - **Fix.** One helper for a message put before a period of the caller's: its own period dropped, none added after
    "?" or "!"; both places, a unit test of each.
  - **Resolution: done.**
    - **Test:** `test_a_failed_reloads_message_keeps_its_own_period` (`test_server.py`, the bridge's "...starting or
      quitting)."): failed, "quitting).. The package was closed"; `test_set_link_display_reports_success_when_the_reopen_fails`
      gains a case ending in "?": failed, "?."; both pass now.
    - **Cause:** each caller added a period of its own after a message that may end in a stop.
    - **Fix:** `core._sentence` ends a text with one stop, its own (. ? !) or a period; the reopen warning, the reload's
      error and `_sampled_before_force`'s failure sentence use it.
    - **Also covered:** the server's sentences that put a message before a period of their own, searched as `%s.` and
      `%s. ` in `server_tools/`: those three; `lifecycle.py`'s list of other ports and `snapshots.py`'s graph name hold
      no message, nor do `launch_designer`'s "nothing is lost: %s. If" (`_how_to_end`'s texts end in no stop) and "did not
      answer within %ds%s." (fixed words).

- [x] **SRV-118 · The sampling's docstrings say less, and other, than the code · follows SRV-115 and SRV-116, generation 3** · `mcp_server/server_tools/lifecycle.py:817-819` (`quit_designer`), `570-573` (`_end_if_past_startup`) · confirmed · found 2026-11-11
  - **Defect.** `quit_designer`'s docstring names the sample among what a forced quit says ("if forced, ... and, on
    macOS, the file its threads were sampled into first"), though one that ends by itself while sampled names it too
    (SRV-115). `_end_if_past_startup`: "('' when nothing was sampled)": a failed sample samples nothing and returns its
    sentence; '' is when no sample was tried.
  - **Resolution: done.** Docs only: `quit_designer`'s docstring says one still running past `wait_s` has its threads
    sampled into a file the result names, also when it then quits by itself; `_end_if_past_startup`'s, '' when no
    sample was tried. The tool docstring's paragraph rewrapped, no line over 120 characters.
  - **Scenario.** An agent reading "Designer quit after 31s. Its threads, sampled first: ..." can't tell from the
    docstring why a quit that wasn't forced names a sample.
  - **Fix.** Narrow (generation 3): the file named once it is past its wait, also when it then quits by itself; ''
    when no sample was tried.

- [x] **TST-314 · The pool's printing of a sampled quit whole has no test · follows SRV-115, generation 2** · `tests/test_all_tools/workers.py:280`, `tests/unit/test_selftest_pool.py` (`test_a_quit_ending_while_sampled_passes_and_keeps_its_folder`) · confirmed · found 2026-11-11
  - **Defect.** `if 'forced' in t or QUIT_SAMPLED in t:` prints the quit whole, part of SRV-115's fix; with `or
    QUIT_SAMPLED in t` removed every test passes: the pool test asserts the folder kept and the PASS line only.
  - **Scenario.** The print lost: a check's detail, cut at 150 characters, is all that says where the sample is.
  - **Fix.** The pool test asserts "render's quit whole:" and the sample's path in the output.
  - **Resolution: done.**
    - **Test:** `test_a_quit_ending_while_sampled_passes_and_keeps_its_folder` asserts the quit printed whole, the
      sample's path in it: it passes, and fails with `or QUIT_SAMPLED in t` removed from `check_the_quits`.
    - **Fix:** the assertion.
