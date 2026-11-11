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

**Last used:** PLG-42, SRV-110, HLP-106, INS-27, TST-307.

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
| Medium | 0 | 2 |
| Low-medium | 0 | 5 |
| Low | 0 | 23 |
| **Total** | **0** | **30** |

## Review log

### 2026-11-11: branch `quit-hang-in-full-run` against main (ROADMAP item 69), the diff only

- **How:** two reviewers, one on the server (`quit_designer`, `_shutdown_stuck_at`, their unit tests), one on the
  self-test and the docs (`closed_by_quit`, the quit checks, `check_the_quits`, the pool test, DECISIONS.md, ROADMAP item
  69); no tests run. The server reviewer read, read-only, the logs of two agent Designers the lead's scratch runs left in
  `/tmp` (nine sessions each: normal quits, quits stuck in teardown, quits forced with the window refusing to close),
  which the lead read again for SRV-107 and SRV-106 before removing those folders. One scratch probe by the lead, in a
  Designer of its own: forced during its `aboutToQuit` handler (SRV-106). No suspicion settled as wrong; the long-line
  half of one (no line over 300 characters in either log) was dropped and its blank-line half merged into SRV-106.
- **Not verified:** whether item 69's two hangs fell before or after "Destroy Main Window". The macOS system log puts
  them after AppKit's "Termination aborted", and Designer's own log can't be timed against it; the hangs don't reproduce
  on demand and their logs were deleted with their folders (`workers._clean_up`). The next occurrence, with its log
  line quoted and its folder kept (SRV-106's fix), would settle it.
- **Resolutions assessed:** none in REVIEW.md. DECISIONS.md's new entry ("A quit forced only at the end of Designer's
  own shutdown passes the self-test's checks of a normal close"): its mechanism ("its main window destroyed") is what
  SRV-106 and SRV-107 find wanting, and TST-288 finds its **Reopen if** can't be noticed; its decision isn't questioned.
- **Findings:** SRV-106, TST-288 (Medium); SRV-107, TST-289 (Low-medium); SRV-108, TST-290, TST-291, TST-292 (Low).
  SRV-106 and TST-288 merge reports of both reviewers. Longest chain growing: none (all generation 1).
- **Suggested order:** SRV-106 and TST-288 first, together: they decide whether the change does what it was made for
  (SRV-106's choice of sign and wording may touch the DECISIONS entry, which takes the user); then SRV-107, TST-289;
  then the Lows.
- **Checked and found fine:** the import of `_shutdown_stuck_at` inside `quit_designer` (log.py imports lifecycle; looked
  up at call time, patching unaffected); the log read before `_force_end` (after it the record, and so the home, are
  gone); exceptions caught (`ToolError`, `OSError`, decoding replaced); a normal quit reads no log; a busy, frozen or
  unanswering Designer has no mark in its current session; only the agent's own home is read, under `_checked_folder`;
  the forced-quit checks ("window stays open", "running a job", "frozen main thread": `FORCED_NOT_CLOSED`; "stuck in its
  shutdown": `FORCED_IN_TEARDOWN`, failing before the server change and passing after); every place that judges a quit's
  reply was found (`alone.py`, `check_a_designer_of_its_own` and the clean-up quits don't judge the text); our plugin's
  `stop()` blocks nowhere and Python plugins unload before "Destroy Main Window" (Designer's own NodeAlignment plugin
  logs its uninit there); the DECISIONS entry's format and every name and path in the docs; README's Self-test section.

### 2026-11-11: branch `quit-hang-in-full-run` against main, the whole diff, after SRV-106 to SRV-108 and TST-288 to TST-292

- **How:** two reviewers, the server (`designer_helpers/quit.py`, `quit_designer`, `server_tools/log.py`, the `QUIT_*`
  constants, `test_lifecycle_env.py`) and the self-test and records (`closed_by_quit`, the lifecycle quit checks,
  `workers.py`, the pool tests, DECISIONS.md, ROADMAP item 69, REVIEW.md); no tests run. The server reviewer read the
  marker lines of the user's shared Designer log; the lead counted them again (SRV-109), without reading its content.
  One scratch probe by the lead in a Designer of its own, which settled a suspicion as wrong: an `aboutToQuit` handler
  blocking the main thread without processing events (`time.sleep(15)`, the lifecycle check's handler runs
  `processEvents`), `quit_designer(wait_s=10)`: "forced during its shutdown: every window had closed", the helper's line
  in the log, so writing it doesn't need the main thread after the print.
- **Not verified:** whether a Windows hand-over (a double-clicked `.sbs` with Designer open) writes a session header
  into the log a running Designer shares (SRV-109 is settled for macOS by the user's log); Windows isn't here.
- **Resolutions assessed:** all eight of this branch. SRV-106: its cause and fix hold, its sign is "no visible window"
  rather than its close (HLP-102), its line can go to another job (HLP-103), and lifecycle's quits are left out
  (TST-293). SRV-107: holds for a start in progress, regresses on hand-over sessions (SRV-109). SRV-108: holds, its
  tail read untested (TST-294). TST-288: holds for the categories, not lifecycle (TST-293), its threshold attributed to
  the user (TST-298). TST-289: never seen failing (TST-295). TST-290: holds. TST-291: its docstring still omits a case
  (TST-296). TST-292: holds.
- **Findings:** SRV-109, HLP-102, TST-293 (Low-medium); HLP-103, TST-294, TST-295, TST-296, TST-297, TST-298 (Low).
  Duplicates merged: HLP-102 (both reviewers). Longest chain growing: SRV-106 → HLP-102 / HLP-103 / TST-293 / TST-294,
  and SRV-107 → SRV-109, generation 2; the next round of findings only about tests or docs narrows claims (Follow-up
  chains).
- **Suggested order:** SRV-109 and HLP-102 (wrong results), then TST-293, then the Lows; TST-298 needs the user.
- **Checked and found fine:** every reply `quit_designer` can return against `closed_by_quit` (only a plain quit and
  one forced during its shutdown pass); the `quit after Ns` parse (a force after the whole wait reads 40 or more);
  the new aboutToQuit check (fails on the branch's first wording, tells its two markers apart, a watched step); the helper's
  direct call; the plugin's job redirect keeps the request's text out of the log; the run-level check's boundary and its
  test; the session slicing across lifecycle's quits; every path to the force; the helper refusing another process
  before scheduling anything, and never sent on Windows; `%r` of a constant; the tail read's partial line and a session
  longer than the tail; exceptions and paths read; typing; the records' names and paths.

### 2026-11-11: branch `quit-hang-in-full-run` against main, the whole diff, after SRV-109 to TST-298

- **How:** two reviewers, the server and the self-test with its records; no tests run. The server reviewer read the
  session-marker lines and about 25 teardown lines of the user's shared log. Two scratch probes by the lead in Designers
  of its own: Designer's window hidden and a tool window shown, `quit_designer(wait_s=5)` (HLP-104); a message box
  refusing its close as Designer's window closes, an `aboutToQuit` handler writing a marker before holding, `wait_s` 10;
  the modal dialog quit and what the helper logged; every window hidden, a forced quit, and the shared preferences file
  (`defaults read 'com.adobe.Adobe Substance 3D Designer'`, compared, not printed) before and after. Settled as wrong:
  the refusing message box (Designer doesn't quit: its `aboutToQuit` never ran, so the helper's "1 of the 2 window(s)
  it closed still open" and "had not closed" are right); the modal dialog (the helper logs `QUIT_CLOSED`, the quit takes
  2 s); the shared file (unchanged).
- **Not verified:** the quit helper's job running before Designer's main loop, during a start's `processEvents` (the
  windows closed, `quit()` without effect, `QUIT_CLOSED` logged): a race at start-up that won't reproduce on demand; a
  quit sent at the first answer of a Designer starting, many times, would show it.
- **Resolutions assessed:** all seventeen; SRV-106 to SRV-108, TST-288 to TST-292, TST-294 to TST-296 and TST-298 hold.
  Questioned: SRV-109 (SRV-110), HLP-102 (HLP-104, TST-301), TST-293 (TST-299, TST-300), TST-297 (TST-302). SRV-107's
  test name went stale: a note under it.
- **Findings:** SRV-110, HLP-104, TST-299, TST-300, TST-301, TST-302 (Low). Longest chains growing: SRV-106 → HLP-102 →
  HLP-104 / TST-301, SRV-107 → SRV-109 → SRV-110, TST-288 → TST-293 → TST-299 / TST-300, generation 3: all Low, the test
  and docs ones narrowing claims; SRV-110 and HLP-104 are the tools' code, cases needing a hand-over during a start or a
  script hiding Designer's window.
- **Suggested order:** SRV-110 and HLP-104 (wrong results), then the four narrowings.
- **Notes:** with only the other port's quit forced during its shutdown, the pool also keeps lifecycle's own folder (an
  extra 90 MB); the fake text in `test_selftest_lifecycle.py` keeps the earlier wording, "every window had closed", which nothing
  reads; lifecycle gained two relaunches, so README's "about 3 minutes" and DECISIONS' "about 3.5 minutes" may go stale,
  which the next full run's times will show; the aboutToQuit check reads its log about 2.5 s after the helper's print,
  where Designer took the line within 2 s.
- **Checked and found fine:** `normal_close` records in the worker's own `common`, the one `_ended` reads, once per
  check, no category calling it; lifecycle's five normal closes go through it and its two deliberate forces don't; the
  count and its tests; every place judging a quit or deleting an agent folder; the relaunches after the new forced
  quits; every path to the force and the precedence of the result's wording; exceptions and paths read; the hand-over
  shapes of the user's log (several hand-overs, a stale-PID start, a session with no "Application uninitialized", two in
  one session, lines after it), but SRV-110's; HLP-103's docstring; the records' names and paths, but SRV-107's test.

### 2026-11-11: branch `quit-hang-in-full-run` against main, the whole diff, after SRV-110 to TST-302

- **How:** two reviewers, the server and the self-test with its records; no tests run. A plain-Python probe of
  `_last_start` on the interleaved shape below, and two scratch probes by the lead in Designers of its own: two
  processes started from the binary with the running agent Designer's home and temp folder, at once and 1 s apart, its
  own log dumped from the plugin's line on, then `read_designer_log(contains='listening on')`; a prompt shown as
  Designer's window closes that itself ignores Close, an `aboutToQuit` marker, `quit_designer(wait_s=8)` (HLP-105).
  Settled as wrong: `_last_start` taking the first of two hand-over sessions whose lines interleave
  (`[NEW, START, LISTENING, NEW, NEW, HANDED_OVER, HANDED_OVER, ENDED, ENDED]` gives the first header, by the probe):
  the shape doesn't arise. Designer's processes write the log each at its own offset, the later write over the
  earlier (a line cut mid-word), and the first line overwritten is a hand-over's header; both times `_last_start` took
  the SDK line and the plugin's line was found. Dropped too: a restart whose header comes before the previous
  instance's "Application uninitialized" (transient, the user's log only: `quit_designer` returns once the process is
  gone).
- **Resolutions assessed:** SRV-110, HLP-104, TST-299 to TST-302, and the earlier ones after their latest change: all
  hold. Questioned: HLP-104 (HLP-105, TST-305), TST-299 (TST-303). TST-295's check was replaced: a note under it.
- **Findings:** HLP-105, TST-303, TST-304, TST-305 (Low). Longest chains growing: SRV-106 → HLP-102 → HLP-104 →
  HLP-105 / TST-305, TST-288 → TST-293 → TST-299 → TST-303, generation 4. HLP-105 is the tools' code, a window that
  refuses its close shown as Designer's closes; the rest narrow or move.
- **Suggested order:** HLP-105 (a wrong result), then TST-303 to TST-305.
- **Notes:** no check runs the "no window shown" case any more: the helper's one condition covers it, and at
  generation 4 nothing is added. A probe handing over into an agent's own log leaves the hand-over's "Application
  uninitialized" as the log's last line, which a forced quit then quotes; only probes start the binary with an agent's
  home. The DECISIONS entry's "lifecycle's normal closes are counted" is as broad as ROADMAP's wording (only those
  whose check reached `normal_close`); where the count misses one, that check fails anyway; changing it takes the
  user, so not raised.
- **Checked and found fine:** a `QStackedWidget` among the visible top-level widgets is Designer's own window in every
  state an agent's Designer gets into (Home screen, floated panels are `QDockWidget`s, dialogs `QDialog`s); the
  helper's three outcomes; `_last_start` on every other shape, and its cost; `_quit_evidence` and `quit_designer` (the
  constant can't come from the request's text, an earlier quit's line in the same session, the second look after the
  read, `_agent_log` unchanged); typing and the one-line call; every lifecycle quit traced against the new helper;
  every place that judges a quit or deletes an agent folder; the DECISIONS entry's format, names and paths; the status
  table, Last used and generations. The module's "closing the visible top-level widgets quits Designer" reads with
  Designer's window among them, as its last sentence says.

### 2026-11-11: branch `quit-hang-in-full-run` against main, the whole diff, after HLP-105 to TST-305

- **How:** two reviewers, the server and the self-test with its records; no tests run. A plain-Python check of the
  unit test's fixture (`'\n'.join([..., 'x', ''])` read back and split ends with `'x'`), and three scratch probes by the
  lead, one after another in a Designer of its own: `QApplication.instance().quitOnLastWindowClosed()` (True); a prompt
  shown through `QTimer.singleShot(0)` from the Close of Designer's window, refusing its own close, an `aboutToQuit`
  marker, `quit_designer(wait_s=8)`; a non-modal `QDialog` parented to Designer's window, refusing its close, the same
  marker, `quit_designer(wait_s=10)` (HLP-106).
- **Resolutions assessed:** HLP-105, TST-303, TST-304 and TST-305, and the earlier ones after their latest change.
  Questioned: HLP-105 (HLP-106, TST-307) and SRV-106 (TST-306); the others hold.
- **Findings:** HLP-106, TST-306, TST-307 (Low). Longest chain growing: SRV-106 → HLP-102 → HLP-104 → HLP-105 → HLP-106
  / TST-307, generation 5. HLP-106 is the tools' code, both cases needing a script or plugin that shows or parents a
  window refusing its close; TST-307 narrows; TST-306 is generation 2, a fixture that can't see its case.
- **Suggested order:** TST-306 and TST-307, then HLP-106 (its fix chosen first: the limit stated, or a judgement after
  Designer's own quit has had its turn).
- **Notes:** TST-304 questioned HLP-102's and HLP-104's resolution text, but carries no chain mark and they no
  "Questioned by" line; the last log entry lists HLP-104 and TST-299 both as holding and as questioned. Neither changes
  what anyone does.
- **Checked and found fine:** `w not in shown` (no `__eq__` on `QWidget`: identity, the wrappers kept alive by
  `shown`); closing a window shown since changes nothing Designer's own quit wouldn't do (it sends the same Close
  first); the own-window condition judging only `shown`; `quit_designer`'s wording precedence, the read before the
  force and the second look; `_quit_evidence`'s exceptions and early return; `_last_start`'s bounds; every unit test
  but TST-306's case failing without its change; the new refusing-prompt check (fails on the helper before HLP-105,
  watched step, `has_ended`, the count of 10, not through `normal_close`); `refuse` passed by both callers;
  `hide_own_window.py` doing what the inline code did; the docstrings, ROADMAP items 69 and 70, the DECISIONS entry;
  REVIEW.md's table, Last used, resolution wordings and hashes.

---

## High

## Medium-high

## Medium

- [x] **SRV-106 · `quit_designer` says "forced: it had not closed" for a close that took when Designer hangs before "Destroy Main Window", and names no log line then** · `mcp_server/server_tools/lifecycle.py:803-810`, `mcp_server/server_tools/log.py:108-130`, `tests/test_all_tools/workers.py:373-385`, `ROADMAP.md:28`, `DECISIONS.md:173-177` · measured · found 2026-11-11
  - **Defect.** "Destroy Main Window" sits partway through Designer's teardown: in every closed session of the agent
    logs read, about 8 teardown lines come before it ("ThumbsManager: Uninit", "Waiting for thumbs generation
    finished...", "stopProcessQueries", the Python plugins' uninit, "Uninitializing App Interop") and about 14 after.
    A Designer forced anywhere before it, its close taken, is reported "forced: it had not closed", with no line named;
    the self-test's normal-close checks then fail as before. Probe (2026-11-11): a Designer running
    `lifecycle/quit_slow_shutdown` (7 s in its window's close handler, 7 s in `aboutToQuit`), `quit_designer(wait_s=10)`:
    the close handler finished, AppKit logged `terminate:`, the `aboutToQuit` handler was still running at the force,
    and the result was "Designer quit after 11s (forced: it had not closed)." with nothing in its log past start-up.
    Item 69's own hangs came after AppKit's "Termination aborted" (macOS's system log); whether before or after the mark
    is unknown, and `workers._clean_up` deletes a worker's folder, its log in it, unless it holds a crash dump. So
    ROADMAP item 69's "the next one's result names where its log stopped" holds only past the mark. The wording says
    more than the mark: log.py's comment ("once its close has taken, before its own teardown"), the result's "at the
    end of its shutdown", the docstring's "whether its close had taken, Designer stuck in its own teardown". The quoted
    line can be blank (126 blank lines in one of those logs).
  - **Scenario.** Item 69 happens again, hung at "Waiting for thumbs generation finished...": the run fails with "forced:
    it had not closed", nothing quoted, and the log deleted.
  - **Fix.** Quote the last non-blank line of its own log in both forced results whenever it was read; say "had not
    closed" only when the log was read and shows no teardown begun, and say when it couldn't be read; take an earlier
    sign of a close taken (the first teardown line, "ThumbsManager: Uninit", in every closed session and in no refused
    one in those logs, or the plugin's own record of the close), measured again; word the comment, result and docstring
    by the sign chosen; keep a worker's folder when its quit was forced. The DECISIONS entry names "its main window
    destroyed": changing the sign changes what it says, which takes the user. (Two reviewers.)
  - **Resolution: done.** The user said to fix every open finding after being told this one's sign touches the DECISIONS
    entry; the entry now names the new sign.
    - **Test:** live, `lifecycle`'s new "forces one stuck in its aboutToQuit, saying its close had taken, without a
      crash" (`quit_slow_shutdown`, `wait_s` 10), run against a scratch copy holding the committed server: "Designer
      quit after 11s (forced: it had not closed)." with its close handler finished; after the fix, "forced during its
      shutdown: every window had closed; its log stopped at ...". Unit:
      `test_a_forced_quit_after_every_window_closed_says_so_and_quotes_its_logs_last_line`,
      `test_a_forced_quit_says_it_had_not_closed_unless_its_session_logged_every_window_closed` (the last line quoted in
      both), `test_a_forced_quit_with_no_log_of_its_own_says_so` (`test_lifecycle_env.py`);
      `test_a_forced_quits_designer_folder_is_kept_to_read_its_log` (`test_selftest_pool.py`), which failed (the folder
      deleted).
    - **Cause:** the sign was a line of Designer's own teardown, logged partway through it; Designer logs none before
      its `aboutToQuit` handlers have run (measured), so a shutdown hanging earlier read as a close that didn't take.
    - **Fix:** the quit helper (`designer_helpers/quit.py`) logs `QUIT_CLOSED` (`project_constants.py`) once every
      window has closed, or how many are still open (measured 2026-11-11: a print from that timer lands in Designer's
      log, readable 2 s later while an `aboutToQuit` handler holds the main thread); `quit_designer` passes it the line,
      reads the own log's session (`_quit_evidence`, `server_tools/log.py`) and says "forced during its shutdown: every
      window had closed", "forced: it had not closed", or "forced; its log could not be read", each read one quoting the
      last line that isn't blank; `workers._clean_up` keeps a worker's folder when its quit was forced; the wording of
      `lifecycle.py`'s docstring, `quit_designer`'s, DECISIONS.md and ROADMAP item 69 follows.
    - **Also covered:** every check of a forced quit (`lifecycle`: window stays open, stuck in its shutdown, running a
      job, frozen main thread, stuck in its aboutToQuit) and of a normal close (`closed_by_quit`); the one place that
      calls the helper directly ("the close asked of another process changes nothing") passes the line too.
  - Questioned by HLP-102, HLP-103, TST-293, TST-294, TST-306 (2026-11-11).

- [x] **TST-288 · Every quit of a run can hang in Designer's teardown and no check fails, so the new decision's **Reopen if** can't be noticed** · `tests/test_all_tools/common.py:73-76`, `tests/test_all_tools/lifecycle/checks.py:224, 508, 652, 678, 511, 231`, `tests/test_all_tools/workers.py:271-275`, `DECISIONS.md:177` · confirmed · found 2026-11-11
  - **Defect.** `closed_by_quit` (`'Designer quit after' in t and ('forced' not in t or FORCED_IN_TEARDOWN in t)`) passes
    every normal-close check on a quit forced in the teardown, and their "no crash dump" halves pass with the teardown
    cut short (a crash in its last steps never happens). The other quit checks don't read the text
    (`check_a_designer_of_its_own`, "Designer quits once its main window closes"). The DECISIONS entry's "Reopen if:
    such quits become frequent" relies on someone noticing, and each one is a pass.
  - **Scenario.** A change to the plugin or helpers leaves a task in `QThreadPool.globalInstance()` (what
    `hold_thread_pool.py` does on purpose): every Designer hangs in `~QCoreApplication`, every quit is "forced at the end
    of its shutdown" after its 30 s, every check passes, and the user's own Designer, with the same plugin, hangs at its
    quit.
  - **Fix.** A check over the whole run that fails on a pattern (say, more than one quit forced in its teardown,
    listed in the summary), or one quit kept strict where item 69's start-up window can't apply (lifecycle's quit with
    unsaved changes, of a Designer that has run for minutes); either keeps each quit passing on its own, as decided.
    (Two reviewers.)
  - **Resolution: done.**
    - **Test:** `test_more_than_two_quits_forced_during_their_shutdown_fail_the_run` (2 pass, 3 fail, the categories
      named) and the summary's count in `test_the_pool_runs_every_category_once_and_prints_one_summary`
      (`test_selftest_pool.py`): both failed, the check missing.
    - **Cause:** each quit forced during its shutdown passes its own check, as decided, and nothing counted them.
    - **Fix:** `workers.check_the_quits` adds "no more than two quits forced during their shutdown", listing them; the
      DECISIONS entry's **Reopen if** is now that check failing.
    - **Also covered:** lifecycle's own quits are left out of the count (its forced ones are on purpose); the crash-dump
      halves of a quit forced during its shutdown are bounded by the same count.
  - Questioned by TST-293, TST-298 (2026-11-11).

## Low-medium

- [x] **SRV-109 · A hand-over process's session header now counts as the running Designer's last start · follows SRV-107, generation 2** · `mcp_server/server_tools/log.py:142-155` (`_last_start`), its users `read_designer_log` and `_last_port` (`_log_for`), `mcp_server/GUIDE.md:108-109` · confirmed · found 2026-11-11
  - **Defect.** A second Designer process that hands over to a running one and exits writes "===== New Session =====",
    "[INFO][IPC] Found instance PID", then "Application uninitialized", with no "Python SDK Version" line: the user's
    shared log holds three such sessions in a row (lines 26499, 26533, 26567). `return max(session, sdk, 0)` takes such
    a header, later than the running Designer's SDK line, as the start; on main those sessions were ignored.
  - **Scenario.** With the user's Designer running, its binary started again (a terminal, a tool): `read_designer_log()`
    shows only the hand-over's dozen lines, and `contains='listening on'` (GUIDE.md's advice when the bridge misbehaves)
    finds nothing; `_last_port(shared)` says None instead of the user's port, so `_log_for` of an agent's ended Designer
    can take the shared log, SRV-84's case. GUIDE.md still says "since the last start" means after the SDK line.
  - **Fix.** Take the header only for a session that hasn't ended (no "Application uninitialized" after it); not by
    "Found instance PID", which a normal start finding a stale PID logs too; a unit case of that shape; GUIDE.md's line.
  - **Resolution: done.**
    - **Test:** `test_the_last_start_is_the_session_still_running`, its hand-over case (`test_lifecycle_env.py`): failed,
      the hand-over's header taken as the start.
    - **Cause:** SRV-107's rule took the latest session header after the SDK line, ended or not.
    - **Fix:** `_last_start` takes the latest header after the SDK line whose session hasn't logged "Application
      uninitialized" (`ENDED`), else the SDK line; GUIDE.md's line says both.
    - **Also covered:** its three users (`read_designer_log`, `_last_port` and so `_log_for`, `_quit_evidence`), each
      by a case of that test or the quit tests.
  - Questioned by SRV-110 (2026-11-11).

- [x] **HLP-102 · The quit helper's sign is "no visible window", not "its close taken" · follows SRV-106, generation 2** · `mcp_server/designer_helpers/quit.py:24-29`, `project_constants.py:36-38`, `mcp_server/server_tools/lifecycle.py` (docstring, "Quitting."), `DECISIONS.md` (Bridge and quitting) · confirmed · found 2026-11-11
  - **Defect.** `still = [w for w in qt_app.topLevelWidgets() if w.isVisible()]` lists the windows again after the
    loop: one shown during the close (a prompt from a Close handler: `lifecycle/quit_prompt_after_close`) is still
    visible, so the helper logs "1 window(s) still open", although Designer quits once its main window has closed
    (measured, HLP-19; lifecycle's "Designer quits once its main window closes, even with another window shown", which
    doesn't read the result). And with no window visible when the timer fires, nothing is closed and the helper logs
    `QUIT_CLOSED`.
  - **Scenario.** A Designer showing a window as it closes, then hanging in its shutdown, is reported "forced: it had not
    closed" and its category check fails; one with no window shown is reported "every window had closed" without a
    close.
  - **Fix.** Judge by the windows the helper closed: `QUIT_CLOSED` only if it closed at least one and none of those is
    visible; or key on the visible `QStackedWidget`, which makes Designer quit (HLP-19). A check of the prompt case
    reading the result. The words "once every window has closed" in DECISIONS.md follow, which takes the user.
    (Two reviewers.)
  - **Resolution: done.** The user said to fix every open finding.
    - **Test:** live, `lifecycle`'s new "logs its close taken when a window shows as the main window closes" (the
      prompt case, reading the log) and "forces one with no window shown, saying it had not closed, without a crash"
      (every window hidden, `wait_s` 3), run against a scratch copy holding the server and helper before this fix: the first
      found no `QUIT_CLOSED` (measured before: "quit: 1 window(s) still open after the close", Designer quitting by
      itself in 2 s), the second read "forced during its shutdown: every window had closed" with nothing closed; both
      pass now.
    - **Cause:** the helper listed the windows again after the loop, those shown since included, and judged an empty
      list a close.
    - **Fix:** `designer_helpers/quit.py` judges by the windows it closed: `QUIT_CLOSED` only if it closed at least one
      and none of those is still visible; otherwise "no window was shown to close" or "N of the M window(s) it closed
      still open". The result says "its close had taken"; `project_constants.py`, `lifecycle.py`'s docstring and the
      DECISIONS entry say "every window it closed".
    - **Also covered:** the window that refuses its close (still "had not closed", quoting the helper's line).
  - Questioned by HLP-104, TST-301 (2026-11-11).

- [x] **TST-293 · Lifecycle's quits forced during their shutdown are neither counted nor kept, and the records say a worker's are · follows SRV-106 and TST-288, generation 2** · `tests/test_all_tools/workers.py:281, 380`, `tests/test_all_tools/lifecycle/checks.py:229, 255-266, 514, 685, 711`, `tests/test_all_tools/common.py:61`, `ROADMAP.md:28`, `DECISIONS.md` (Bridge and quitting), `REVIEW.md` (SRV-106's and TST-288's Also covered) · confirmed · found 2026-11-11
  - **Defect.** `in_shutdown` and `forced` read `part['quit']`, None for lifecycle; four of lifecycle's checks are
    normal closes passing on a quit forced during its shutdown (another port, unsaved changes, slow shutdown, modal
    dialog), only two of its forced quits are on purpose; `remove_its_folder` deletes the second Designer's folder
    whatever its quit said; `check` cuts a detail at 150 characters, about 34 of the quoted line. TST-288's "its forced
    ones are on purpose", ROADMAP item 69 and the DECISIONS entry ("more than two such quits in one run", "a worker's
    folder is kept") say more.
  - **Scenario.** Item 69 again in lifecycle's modal-dialog quit, as first seen: the check passes, the count leaves it
    out, lifecycle's folder (every session's log) is deleted, and the PASS line keeps "[INFO][Python] [sd_claude_bridge_k".
  - **Fix.** Lifecycle reports its normal closes forced during their shutdown to the pool (a list in its results next to
    `quit`), counted and keeping its folder; `remove_its_folder` keeps a folder whose quit was forced; a forced quit's
    whole text printed; or every record narrowed to "the categories' quits".
  - **Resolution: done.**
    - **Test:** `test_lifecycles_quits_forced_during_their_shutdown_count_and_keep_its_folder`
      (`test_selftest_pool.py`), seen failing by mutation with either the count or the kept folder taken out;
      `test_a_normal_close_forced_during_its_shutdown_is_recorded_for_the_pool` (`test_selftest_lifecycle.py`) and
      `test_a_workers_results_carry_its_quits_forced_during_their_shutdown` (`test_selftest_summary.py`), failing with
      `normal_close` and the results' key missing.
    - **Cause:** the pool read only the categories' `quit`; lifecycle's normal closes judged themselves.
    - **Fix:** `common.normal_close(t, what)` records a normal close forced during its shutdown in
      `common.forced_in_shutdown` and prints its whole text; lifecycle's five normal closes use it; a worker's results
      carry the list (`__main__._ended`); `check_the_quits` counts it and prints a forced category quit whole;
      `run_pool` keeps the folder of a worker with any; the other port's Designer's folder is kept when its quit was
      forced (`remove_its_folder`).
    - **Also covered:** the records (ROADMAP item 69, the DECISIONS entry) now say lifecycle's are counted. Not covered
      by a test: `remove_its_folder`'s keep, which the live check can't force on demand.
  - Questioned by TST-299, TST-300 (2026-11-11).

- [x] **SRV-107 · Before a new start's "Python SDK Version" line, the previous session's "Destroy Main Window" counts as this one's** · `mcp_server/server_tools/log.py:129, 133-139` · confirmed · found 2026-11-11
  - **Defect.** `_shutdown_stuck_at` slices at `_last_start`, the last "Python SDK Version", which Designer writes about
    430 lines into a session ("===== New Session =====" at its first line); the home, per port, outlives quits and its
    `log.txt` grows. In one of those logs a session's mark is at line 523 and the next session's "Python SDK Version" at
    971, its "===== New Session =====" at 541.
  - **Scenario.** `launch_designer` times out with Designer still starting (slow, under load, a dialog before plugins
    load) and the agent or a clean-up calls `quit_designer`: forced, the result says "forced at the end of its shutdown",
    quoting a start-up line, and `closed_by_quit` passes it as a normal close.
  - **Fix.** Slice at the later of the last "===== New Session =====" and the last "Python SDK Version"; a unit case
    with the previous session's mark and a new session before its SDK line. The same boundary serves
    `read_designer_log(since_last_start=True)` and `_last_port`: decide each on purpose (the address-review skill,
    step 3).
  - **Resolution: done.**
    - **Test:** `test_the_last_start_is_its_session_before_the_plugins_load` (read_designer_log and `_last_port`) and the
      parametrized `test_a_forced_quit_says_it_had_not_closed_unless_its_session_logged_every_window_closed` case "still
      starting" (`test_lifecycle_env.py`): read_designer_log showed the previous session's lines.
    - **Cause:** `_last_start` took the last "Python SDK Version", logged about 430 lines into a session.
    - **Fix:** `_last_start` takes the later of the last "===== New Session =====" (`NEW_SESSION`) and the last
      "Python SDK Version": once the plugins have loaded nothing changes, while Designer starts the previous session no
      longer counts.
    - **Also covered:** all three users, on purpose: `_quit_evidence`; `read_designer_log(since_last_start=True)`, which
      during a start now shows that start's lines; `_last_port`, which then says None ("can't tell"), so `_log_for`
      takes the newer of the two logs instead of naming the previous session's port.
  - Questioned by SRV-109, TST-294 (2026-11-11).
  - Note (2026-11-11): its test is now the first case of `test_the_last_start_is_the_session_still_running`
    (`test_lifecycle_env.py`), merged by SRV-109's fix.

- [x] **TST-289 · "A slow shutdown within its wait is left to finish" now passes on a forced end** · `tests/test_all_tools/lifecycle/checks.py:640, 652` · confirmed · found 2026-11-11
  - **Defect.** The check is about `quit_designer` not forcing a slow shutdown; with `closed_by_quit` it passes on "forced
    at the end of its shutdown". `finished` still catches a force before both handlers end; what passes now is a force
    after them, which its name and comment ("left to finish") deny.
  - **Scenario.** A regression in the wait forces just after the 14 s of handlers (wait_s 40), or the teardown hangs
    after them: the check reports "left to finish" for a Designer that was forced.
  - **Fix.** Keep this check strict (`'forced' not in t`), or rename it and its comment to what it checks.
  - **Resolution: done.**
    - **Test:** the check itself; read against its scenario: a force before both handlers end still fails `finished`,
      and one after them but before the 40 s now fails too.
    - **Cause:** `closed_by_quit` accepted any force during the shutdown.
    - **Fix:** the check also requires, when forced, that the quit came after its whole wait (`quit after Ns`, N >= 40),
      its comment saying so: a slow shutdown left to finish within its wait, Designer's own hang past it allowed.
    - **Also covered:** the other normal-close checks keep `closed_by_quit` alone: none is about the wait.
  - Questioned by TST-295 (2026-11-11).

## Low

- [x] **SRV-108 · The log read before the force widens the window in which a Designer that quits by itself is reported forced, and can reach the shared log** · `mcp_server/server_tools/lifecycle.py:797-803`, `mcp_server/server_tools/log.py:119-128` · confirmed · found 2026-11-11
  - **Defect.** Between the wait loop's last look and the SIGTERM, `_shutdown_stuck_at` now runs `_agent_home` (ps,
    pgrep), `_log_for` (the user's Designer data folder walked, `_agent_designer` and `_agent_home` again) and reads the
    whole log (about 300 KB after nine sessions).
  - **Scenario.** The Designer ends by itself in that window: `_force_end`'s SIGTERM meets `ProcessLookupError`
    (suppressed) and returns True, and the result says forced. If it ends between `_agent_home` and `_log_for`'s own
    `_agent_designer`, `_log_for` takes its "none running" branch, which can return the shared log, which the helper's
    docstring says isn't read. Needs a quit ending within a fraction of a second of `wait_s`.
  - **Fix.** Look at the process again after the read and report a plain quit if it's gone (or have `_force_end` say its
    first signal found no process); build the own log's path from the home directly; read only the log's tail.
  - **Resolution: done.**
    - **Test:** `test_a_designer_ending_while_its_log_is_read_is_not_reported_forced`, and `_log_for` made to fail in
      every forced-quit test (`test_lifecycle_env.py`): the first failed with no `_agent_log` to read through.
    - **Cause:** the read ran between the last look and the SIGTERM, through `_log_for`, which can return the shared log.
    - **Fix:** `_agent_log` (split out of `_log_for`, unchanged) gives the own log only; `_quit_evidence` reads its last
      256 KB (`LOG_TAIL`); `quit_designer` looks again after the read and reports a plain quit if it has gone.
    - **Also covered:** `_log_for` keeps its behaviour, through the same `_agent_log`.
  - Questioned by TST-294 (2026-11-11).

- [x] **TST-290 · The self-test's copies of `quit_designer`'s wording aren't tied to the server's, and the pool test can't tell which category failed** · `tests/test_all_tools/common.py:69-70`, `tests/unit/test_selftest_pool.py:479-488`, `tests/unit/test_lifecycle_env.py` (the new asserts) · confirmed · found 2026-11-11
  - **Defect.** `FORCED_IN_TEARDOWN` and `FORCED_NOT_CLOSED` copy the server's text by hand, and the pool test's fake
    ('... (forced at the end of its shutdown: its log stopped at "Remove PID").') already differs from it (no "its main
    window was destroyed"). The pool test asserts `count(False) == 2`: with the two constants swapped in
    `closed_by_quit`, render passes, measure and facts fail, still 2.
  - **Scenario.** The server's wording changes with its unit tests: every unit test passes and the self-test's checks
    go stale until a live run; a rewording without "forced" makes `closed_by_quit` pass a forced quit.
  - **Fix.** The two phrases defined once (`project_constants.py`, which both sides import) and used by the server, the
    self-test and the unit tests; the pool test asserts by category (render's check failed, measure's passed).
  - **Resolution: done.**
    - **Test:** `test_a_quit_forced_before_its_close_took_or_none_fails_that_categorys_check` asserts each category's
      line (render's and facts' FAIL, measure's PASS); the texts are built from the constants.
    - **Cause:** the wording was copied by hand into the self-test.
    - **Fix:** `QUIT_FORCED_IN_SHUTDOWN`, `QUIT_FORCED_NOT_CLOSED` and `QUIT_CLOSED` in `project_constants.py`, used by
      `quit_designer`, the quit helper's caller, `common.closed_by_quit`, `workers.check_the_quits`, `lifecycle`'s checks
      and the unit tests.
    - **Also covered:** `common.FORCED_IN_TEARDOWN` and `FORCED_NOT_CLOSED` removed.

- [x] **TST-291 · `check_the_quits`' docstring says a forced quit fails a category's check** · `tests/test_all_tools/workers.py:252-253` · confirmed · found 2026-11-11
  - **Defect.** "each category's quit check, failed by a forced quit, none, or a crash dump": a quit forced in its
    teardown now passes (`closed_by_quit`).
  - **Scenario.** A reader of the pool takes any forced quit for a failure.
  - **Fix.** "failed by a forced quit whose close hadn't taken (`common.closed_by_quit`), none, or ...".
  - **Resolution: done.** Docs only: the docstring says a quit forced before its close took (`common.closed_by_quit`),
    and the new count of quits forced during their shutdown.
  - Questioned by TST-296 (2026-11-11).

- [x] **TST-292 · The DECISIONS entry's evidence lives only in a ROADMAP row that can be deleted, and the module's account of quitting leaves item 69 out** · `DECISIONS.md:173-177`, `mcp_server/server_tools/lifecycle.py:18-24` · confirmed · found 2026-11-11
  - **Defect.** The entry cites "(ROADMAP item 69)" for the hang it rests on; ROADMAP's checked items "can be deleted
    later". DECISIONS' introduction puts measured behaviour in GUIDE.md or the module's docstring, and `lifecycle.py`'s
    "Quitting." paragraph names the licence-check hangs but not this one.
  - **Scenario.** ROADMAP's checked rows are cleared: the entry's reason (the system-log evidence, what was ruled out)
    survives only in git history.
  - **Fix.** A short account of item 69's hang in `lifecycle.py`'s "Quitting." paragraph, the entry pointing there.
  - **Resolution: done.** Docs only: `lifecycle.py`'s "Quitting." paragraph gives the hang (two Designers just started,
    about 30 s after their close, the system log's account, not reproduced) and why the helper logs `QUIT_CLOSED`; the
    DECISIONS entry points there.

- [x] **HLP-103 · The quit helper's line goes to another job's output if one runs when its timer fires · follows SRV-106, generation 2** · `mcp_server/designer_helpers/quit.py:29`, `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:236` · confirmed · found 2026-11-11
  - **Defect.** The plugin runs a job under `contextlib.redirect_stdout(buf)`, which is process-wide; the helper prints
    300 ms after the quit's job, to whatever `sys.stdout` is then.
  - **Scenario.** Another client's job starts within those 300 ms (30 ms after the quit's at the earliest) and processes
    events: the timer fires inside it, the line goes into its reply, and a hang after it reads "forced: it had not
    closed". Needs two clients on one port.
  - **Fix.** Write the line where Designer's log takes it whatever job runs (`sys.__stdout__`, if its log takes that:
    measure), or have the plugin log it; otherwise say the limit in the helper's docstring.
  - **Resolution: done**, by the finding's last fix, the limit said: the others cost a plugin change for a case needing
    two clients on one port within 300 ms. Measured (2026-11-11): `sys.__stdout__` reaches no line of
    Designer's log, from a job or a timer; `logging` reaches it from inside a job, its handler holding Designer's own
    stderr, but every line as `[ERROR][Python]`, which would put a normal quit in every errors-only read. The helper's
    docstring gives the limit and those measurements.

- [x] **TST-294 · Tests of this branch that can't see what they're named for · follows SRV-106, SRV-107 and SRV-108, generation 2** · `tests/unit/test_lifecycle_env.py:832, 868-876, 908-917`, `mcp_server/server_tools/log.py:130, 133-135`, `tests/unit/test_selftest_pool.py:532-539` · confirmed · found 2026-11-11
  - **Defect.** `_forced_with`'s fake `_agent_log` returns None, which the real one never does (it raises `ToolError`):
    `if not path: return None` is dead code shaped by it, and dropping `ToolError` from the `except` (the stuck Designer
    then never ended, the agent told "still starting") fails no test. No log is longer than `LOG_TAIL`: reading the whole
    file passes every test. No case has both markers with the SDK line last: a rule preferring the header whenever one
    exists passes. The pool test of a kept folder checks one is kept, not which.
  - **Scenario.** Any of those edits: every test passes.
  - **Fix.** The fake raises `ToolError` as the real one does (or the real `_agent_log` on a home in `tmp_path`), line 130
    dropped; a log over `LOG_TAIL` with the previous session's mark before the cut; a `[NEW, ..., START, x]` case
    expecting `[START, x]`; the kept folder named (render's port).
  - **Resolution: done.**
    - **Test:** the fake `_agent_log` raises `ToolError` as the real one does, and `if not path` is gone from
      `_quit_evidence`; `test_a_forced_quit_reads_its_logs_tail_and_judges_this_session` (a log past `LOG_TAIL`: the
      previous session's mark in the tail and its first line before the cut, then this session longer than the tail);
      the SDK-last case of `test_the_last_start_is_the_session_still_running`; the kept folder named by port. These
      guard what the code does already: each passed before the other fixes, as a guard should.
    - **Cause:** the fakes and cases were shaped by the code, not by what it guards against.
    - **Fix:** as above.
    - **Also covered:** reading the whole file still passes the tail tests, as both answers are the same by design; the
      tail is a bound on the read, not a behaviour.

- [x] **TST-295 · The slow-shutdown check's new condition and the three "had not closed" tightenings were never seen failing · follows TST-289, generation 2** · `tests/test_all_tools/lifecycle/checks.py:531, 572, 593, 679-685`, `REVIEW.md` (TST-289's Test) · confirmed · found 2026-11-11
  - **Defect.** Against the server of the branch's first change, and main's, the slow quit isn't forced and the three forced checks already
    read "had not closed": each passes before and after. AGENTS.md wants a changed check seen failing; TST-289's
    resolution says "read against its scenario".
  - **Scenario.** A check that can't fail goes unseen; one written wrong passes.
  - **Fix.** Scratch copies of the server, one forcing at about 15 s whatever `wait_s`, one always saying "forced during
    its shutdown", each run through the checks and recorded.
  - **Resolution: done.**
    - **Test:** `lifecycle` run against a scratch copy whose `quit_designer` says "forced during its shutdown: its close
      had taken" of every quit: the slow-shutdown check failed (forced at 16 s of a 40 s wait), and so did the four
      "had not closed" checks (window stays open, running a job, frozen main thread, no window shown); with the code
      as it is, all pass. One copy for both: a force at 15 s would have cut the 14 s of handlers and failed `finished`
      instead.
    - **Cause:** the earlier resolution judged those checks by reading.
    - **Fix:** none to the checks: the run recorded here.
  - Note (2026-11-11): the "no window shown" check was replaced by HLP-104's "forces one whose own window wasn't shown,
    saying it had not closed, without a crash", seen failing there.

- [x] **TST-296 · Docstrings of the pool that say less, or other, than its code · follows TST-291, generation 2** · `tests/test_all_tools/workers.py:1-30, 253-255, 385-388` · confirmed · found 2026-11-11
  - **Defect.** `check_the_quits` names a quit forced before its close took, none, or a crash dump, not "forced; its log
    could not be read", which fails too; `_clean_up` says "its log says where its shutdown stopped" of every forced quit,
    one whose close never took included; the module's docstring, which holds the pool's rules (ROADMAP item 68), names
    neither the count of quits forced during their shutdown nor the folders kept after a forced quit.
  - **Scenario.** A reader of the pool's rules misses two of them.
  - **Fix.** Those three places say it.
  - **Resolution: done.** Docs only: `check_the_quits` names the unreadable log and lifecycle's count, `_clean_up` says a
    forced quit's log says how far that quit got, and the module's docstring gives both rules.

- [x] **TST-297 · ROADMAP item 69 is checked while its open work, the cause, has no item** · `ROADMAP.md:28` · confirmed · found 2026-11-11
  - **Defect.** Its Done text ends "Left: the cause, unconfirmed ..., and such a quit still takes its whole wait";
    checked rows can be deleted, and the DECISIONS entry reopens if "the cause is confirmed", which nothing pursues; the
    earlier plan (the pool's times per worker, a probe under the full run's load) is gone.
  - **Scenario.** The checked row is cleared: nothing says the cause is still open.
  - **Fix.** A new unchecked item for the cause, with the probes tried and what would settle it.
  - **Resolution: done.** Docs only: ROADMAP item 70, "The cause of item 69's hang", unchecked, with the probes tried
    and what would settle it; item 69's Done text points there, and the DECISIONS entry's **Reopen if** too.
  - Questioned by TST-302 (2026-11-11).

- [x] **TST-298 · The DECISIONS entry calls the "more than two" threshold and its new Reopen if the user's choice** · `DECISIONS.md` (Bridge and quitting) · confirmed · found 2026-11-11
  - **Defect.** TST-288's fix added "more than two such quits in one run fail a check of their own" and "Reopen if: that check
    fails" to an entry ending "The user's choice, 2026-11-11"; the user chose the way (the first of three) and to fix
    every finding, and TST-288 suggested "say, more than one": the number was the fixing agent's.
  - **Scenario.** A reviewer takes the threshold as the user's and doesn't question it.
  - **Fix.** Ask the user; record their answer, or word the entry so the number isn't theirs.
  - **Resolution: done.** The user was asked and answered "keep two" (2026-11-11); the entry says the threshold is the
    user's choice, with the way.

- [x] **SRV-110 · `_last_start` drops a start's header when any later session has ended, not only its own · follows SRV-109, generation 3** · `mcp_server/server_tools/log.py:143-151`, `mcp_server/GUIDE.md:108-109` · confirmed · found 2026-11-11
  - **Defect.** `if lines[i].startswith(NEW_SESSION) and not any(ENDED in line for line in lines[i:])` looks for
    "Application uninitialized" from the header to the end of the file: a start in progress loses its header once a
    later session has ended, a hand-over during that start.
  - **Scenario.** `[NEW, START, LISTENING, CLOSED, ENDED, NEW, starting, NEW, HANDED_OVER, ENDED, still starting]`: the
    last start is the previous session's SDK line, so `read_designer_log` shows the previous session (SRV-107's case),
    `_last_port` its port where it can't tell, and a forced quit reads "its close had taken" of a Designer starting. Needs
    a second process handing over while the first starts.
  - **Fix.** Bound the look to the header's own session, up to the next header; a unit case of that shape; the
    docstring and GUIDE.md's line.
  - **Resolution: done.**
    - **Test:** the case "a hand-over while one starts" of `test_the_last_start_is_the_session_still_running`
      (`test_lifecycle_env.py`): failed, the previous session's SDK line taken as the start.
    - **Cause:** the look for "Application uninitialized" ran to the end of the file.
    - **Fix:** `_last_start` looks in each header's own lines, up to the next header; its docstring and GUIDE.md's line
      say so.
    - **Also covered:** its three users, through the same function.

- [x] **HLP-104 · The quit helper reports a close taken when the windows it closed weren't Designer's own · follows HLP-102, generation 3** · `mcp_server/designer_helpers/quit.py:28-38`, `mcp_server/server_tools/lifecycle.py:27-29, 819`, `project_constants.py:38-40` · measured · found 2026-11-11
  - **Defect.** `QUIT_CLOSED` is logged when every window the helper closed is hidden, whichever they were; Designer
    quits on its own window, the visible `QStackedWidget` (HLP-19). Probe (2026-11-11): Designer's window hidden, a
    `Qt.Tool` window shown, `quit_designer(wait_s=5)`: the helper closed the tool window and logged `QUIT_CLOSED`,
    Designer stayed, and the result read "forced during its shutdown: its close had taken". The reverse holds: a
    message box refusing its close keeps Designer from quitting (its `aboutToQuit` never ran), so the helper's "1 of the
    2 window(s) it closed still open" is right there.
  - **Scenario.** A script hides Designer's window and leaves another shown: a quit forced after it passes the
    self-test's normal-close checks and tells the agent its close had taken.
  - **Fix.** `QUIT_CLOSED` only if Designer's own window was among those it closed and every window it closed is
    hidden; a check of that case; the wording follows.
  - **Resolution: done.**
    - **Test:** `lifecycle`'s no-window check became "forces one whose own window wasn't shown, saying it had not closed,
      without a crash" (Designer's window hidden, a `Qt.Tool` window shown, `wait_s` 5): in a scratch run on the helper
      before this fix it failed, "forced during its shutdown: its close had taken"; it passes now, the helper
      logging "Designer's own window wasn't shown: 1 other window(s) closed".
    - **Cause:** the helper judged the windows it closed, whichever they were.
    - **Fix:** `designer_helpers/quit.py` logs `QUIT_CLOSED` only if a `QStackedWidget`, Designer's own window, was
      among the windows it closed and none of those is still visible; `project_constants.py`, `lifecycle.py`'s
      docstring and the DECISIONS entry say "Designer's own among them".
    - **Also covered:** HLP-102's case of no window shown, the same condition now (no own window among those closed);
      the refusing message box, measured to keep Designer from quitting, still "had not closed"; the prompt, modal and
      aboutToQuit cases pass in the same run.
  - Questioned by HLP-105, TST-305 (2026-11-11).

- [x] **TST-299 · The records say a forced quit's folder is kept and printed whole; lifecycle's are only when its normal close was forced during its shutdown and its check reached `normal_close` · follows TST-293, generation 3** · `tests/test_all_tools/common.py:73-79`, `tests/test_all_tools/lifecycle/checks.py:517-518, 729, 755-756`, `tests/test_all_tools/workers.py:22-24, 389-401`, `ROADMAP.md:28` · confirmed · found 2026-11-11
  - **Defect.** `normal_close` records only `QUIT_FORCED_IN_SHUTDOWN`, and three checks reach it only after another
    condition (`'discarding unsaved changes' in t and normal_close(...)`, `finished and ...`, `'MODAL=QMessageBox' in
    modal and ...`); lifecycle's folder is kept from that list alone. The pool's docstring ("a Designer's folder is kept
    after a forced quit"), ROADMAP item 69 and `normal_close`'s "printed whole" say more.
  - **Scenario.** Lifecycle's modal quit forced before its close took: its check fails, lifecycle's folder is deleted.
  - **Fix.** Narrow the records to what the code does (generation 3): a category's folder after a forced quit;
    lifecycle's after a normal close forced during its shutdown that its check reached.
  - **Resolution: done.** Docs only: the pool's docstring, ROADMAP item 69 and `normal_close`'s docstring say it.
  - Questioned by TST-303 (2026-11-11).

- [x] **TST-300 · The pool test's "printed whole" assertion can't fail · follows TST-293, generation 3** · `tests/unit/test_selftest_pool.py:574` · confirmed · found 2026-11-11
  - **Defect.** `assert '[INFO][IPC] Remove PID' in out, 'a forced quit printed whole, not cut at 150 characters'`: the
    fake text is 95 characters, its detail about 118, under the cut, so the check's own line holds it.
  - **Scenario.** The print of a forced category quit deleted (`workers.py:277-278`): the test passes.
  - **Fix.** Drop the assertion (generation 3).
  - **Resolution: done.** The assertion dropped.

- [x] **TST-301 · The no-window check needs the helper's line to be the log's last · follows HLP-102, generation 3** · `tests/test_all_tools/lifecycle/checks.py:679` · confirmed · found 2026-11-11
  - **Defect.** `'no window' in t` comes only from the quoted last line of the log; nothing keeps a Designer just
    started from logging another line between the helper's print and the read, 3 s later.
  - **Scenario.** A late start-up line, likelier under the pool's load: the check fails though the result said "forced:
    it had not closed".
  - **Fix.** Drop `'no window' in t` (generation 3): `QUIT_FORCED_NOT_CLOSED in t` fails on HLP-102's defect already.
  - **Resolution: done.** The check, rewritten for HLP-104, asserts `QUIT_FORCED_NOT_CLOSED in t` and nothing of the
    quoted line.

- [x] **TST-302 · ROADMAP item 70 says "ruled out" of probes that didn't reproduce it · follows TST-297, generation 2** · `ROADMAP.md:29` · confirmed · found 2026-11-11
  - **Defect.** "Ruled out by scratch probes (2026-11-11): two quits at once, CPU load, ...": item 69 says "not
    reproduced"; the load probe wasn't the full run's (four Designers working, the unit suite beside them), and the proxy
    reached only some hosts.
  - **Scenario.** Whoever takes item 70 skips load as a cause, though the hang came only in a full run.
  - **Fix.** "Not reproduced by scratch probes (2026-11-11): ...".
  - **Resolution: done.** Docs only: "Not reproduced by scratch probes (2026-11-11), none of them the full run's load".

- [x] **HLP-105 · The quit helper logs its close taken while a window shown during the close, refusing its own, keeps Designer open · follows HLP-104, generation 4** · `mcp_server/designer_helpers/quit.py:28-40`, `project_constants.py:38-40`, `mcp_server/server_tools/lifecycle.py:27-29` · measured · found 2026-11-11
  - **Defect.** The helper judges only the windows it listed before closing them (`shown`); a window shown as
    Designer's own closes is never looked at, and if it refuses its close, Designer doesn't quit. Probe (2026-11-11): an
    event filter on Designer's `QStackedWidget` shows a `QLabel` on Close, the label ignoring Close itself, and an
    `aboutToQuit` marker; `quit_designer(wait_s=8)`: the label showed, `aboutToQuit` never ran, and the result read
    "forced during its shutdown: its close had taken". With a prompt that accepts its close (`quit_prompt_after_close`),
    Designer quits.
  - **Scenario.** A script or plugin in an agent's Designer shows a non-modal "unsaved work" window as Designer's
    window closes, ignoring Close until answered: the quit is forced after its wait, the agent is told the close had
    taken, and the self-test passes it as a normal close (`closed_by_quit`).
  - **Fix.** After the loop, close once each window shown since, and judge those with the others: `QUIT_CLOSED` only if
    they hide too; measure the accepting and the refusing prompt in one probe first, with a check of the refusing one.
    Or state the limit in the helper's docstring, as HLP-103's resolution did.
  - **Resolution: done.**
    - **Test:** `lifecycle`'s new "forces one kept open by a prompt refusing its close, saying it had not closed, without
      a crash" (`quit_prompt_after_close.py` with `refuse`, `wait_s` 5): in a scratch run before the fix it failed,
      "forced during its shutdown: its close had taken"; it passes now, the helper logging "1 of the 2 window(s) it
      closed still open".
    - **Cause:** the helper listed the windows, closed them and judged only those: one shown during the close was never
      looked at.
    - **Fix:** `designer_helpers/quit.py` closes once each window shown since its list and judges it with the others;
      its docstring says which windows it closed.
    - **Also covered:** in the same run the accepting prompt still logs `QUIT_CLOSED` (Designer quits in 2 s), and
      Designer's window hidden, the windows ignoring Close, the stuck shutdown, the aboutToQuit, slow and modal cases
      pass. `project_constants.py`, `lifecycle.py`'s docstring and the DECISIONS entry ("once every window it closed has
      closed") still hold, the windows shown since being among those it closed; a window shown by those, a second
      prompt, isn't closed ("once"). The prompt check's comment, "not by the windows shown after", rewritten.
  - Questioned by HLP-106, TST-307 (2026-11-11).

- [x] **TST-303 · ROADMAP item 69 and `_clean_up`'s docstring say more than the code of the line and of the folders kept · follows TST-299, generation 4** · `ROADMAP.md:28`, `tests/test_all_tools/workers.py:400-402` · confirmed · found 2026-11-11
  - **Defect.** ROADMAP: "the quit helper logs `QUIT_CLOSED` (`project_constants.py`) once every window it closed has
    closed", without HLP-104's "Designer's own among them"; "lifecycle's after a normal close forced during its
    shutdown", without TST-299's "that its check reached". `_clean_up`: "unless one still runs there, left a crash dump
    or had a quit forced", while lifecycle's deliberate forced quits (six of them) keep nothing: only the ports in
    `forced` are kept, lifecycle's only through `forced_in_shutdown`.
  - **Scenario.** HLP-104's probe (Designer's window hidden, a tool window closed): ROADMAP says the line is logged;
    it isn't. A reader of `_clean_up` looks for lifecycle's folder after its deliberate forced quits: deleted.
  - **Fix.** Narrow (generation 4): ROADMAP points at `project_constants.py` and the pool's docstring instead of
    restating them; `_clean_up` says "or is among `forced` (`run_pool`)".
  - **Resolution: done.** Docs only: ROADMAP item 69 points at `project_constants.py` for when the line is logged and at
    the pool's docstring for the quits counted and the folders kept; `_clean_up`'s docstring names `forced`. Also
    covered: the pool's docstring counted "lifecycle's normal closes" too; it says those that reach
    `common.normal_close`.

- [x] **TST-304 · Two resolutions record commit hashes** · `REVIEW.md` (HLP-102's Test, HLP-104's Test) · confirmed · found 2026-11-11
  - **Defect.** HLP-102: "run against a scratch copy holding d71331e's server and helper"; HLP-104: "in a scratch run
    on the code as committed in 21fa031". AGENTS.md: "a resolution line giving the evidence, and no commit hash
    (branches are squashed into main)"; the `address-review` skill, step 7, too.
  - **Scenario.** Once the branch is squashed into main, neither hash resolves: a reader can't tell what code the check
    failed against.
  - **Fix.** Name the state instead: "the server and helper before HLP-102's fix", "the helper before this fix". The
    hashes in findings' Defects and the review log aren't covered by the rule; the same wording may replace them.
  - **Resolution: done.** HLP-102's and HLP-104's Tests name the state ("the server and helper before this fix", "the
    helper before this fix"). Also covered: TST-295's and TST-298's Defects and two review log entries, named the same
    way; this entry's Defect quotes them.

- [x] **TST-305 · The HLP-104 check's Qt code runs inline where the live-check skill puts it in a script · follows HLP-104, generation 4** · `tests/test_all_tools/lifecycle/checks.py:658-678` · confirmed · found 2026-11-11
  - **Defect.** Eleven lines of Qt code (imports, an `isinstance(w, QStackedWidget)` filter, a hide loop,
    `QWidget(None, Qt.WindowType.Tool)`, kept alive through `vars(sys)`) in an `execute_designer_code` string; the
    skill: "Python with real logic that runs inside Designer (more than a handful of lines, imports ... included, or Qt
    code that gains from type checks)" goes in `designer_scripts/`, as its neighbours `quit_ignores_close.py` and
    `quit_prompt_after_close.py` do. Its comment cites "(HLP-19)" without "REVIEW.md".
  - **Scenario.** A wrong enum or constructor there isn't caught by mypy or ruff; the check then fails only on
    `HIDDEN=1` missing, the traceback cut to the detail's 150 characters, where `designer_script` fails "script ...
    ran" with it.
  - **Fix.** Move the snippet unchanged to `lifecycle/designer_scripts/hide_own_window.py`, run with
    `designer_script`; no behaviour or check changes; "REVIEW.md HLP-19" in the comment.
  - **Resolution: done.** A move: `lifecycle/designer_scripts/hide_own_window.py`, run with `designer_script`, the
    comment citing "REVIEW.md HLP-19". The check passed in the scratch run before the move (inline) and after it.

- [x] **HLP-106 · The quit helper's line predicts Designer's quit before Designer decides it: a refusing window shown a moment later, or one Qt's quit skips, makes it wrong · follows HLP-105, generation 5** · `mcp_server/designer_helpers/quit.py:29-46`, its claims at `quit.py:9-14` and `project_constants.py:38-40` · measured · found 2026-11-11
  - **Defect.** The helper judges the windows when its timer slot runs; Designer's own quit (Qt 6's `QEvent::Quit`:
    close every visible top-level window, give up if one refuses, skipping parented dialogs, popups and
    `WA_DontShowOnScreen` windows) runs after the slot returns. Probes (2026-11-11), each with an `aboutToQuit` marker:
    (a) a `QLabel` shown through `QTimer.singleShot(0)` from the Close of Designer's window, ignoring Close: the helper
    logged `QUIT_CLOSED`, the label showed, `aboutToQuit` never ran, and `quit_designer(wait_s=8)` read "forced during
    its shutdown: its close had taken"; (b) a non-modal `QDialog` parented to Designer's window, ignoring Close: the
    helper logged "1 of the 2 window(s) it closed still open", and Designer quit by itself in 2 s.
  - **Scenario.** (a) A script or plugin in an agent's Designer posts a non-modal "unsaved work" window from the
    window's Close handler: the agent is told the close had taken, and the self-test passes it as a normal close
    (`closed_by_quit`); a second prompt shown by one the helper closed does the same. (b) A parented dialog that
    refuses its close, then a shutdown that hangs: "forced: it had not closed" (the safe direction: the check fails).
  - **Fix.** Either state the limit, as HLP-103's resolution did: the line says Designer's window and every window the
    helper closed were hidden when it judged, before Designer's own quit decides; a window shown after, or one Qt's quit
    skips, isn't judged as Designer judges it. Or judge after Designer's quit has had its turn: a second timer (about
    1 s) logging "still open" if a top-level window that Qt's quit counts is visible, the server reading `QUIT_CLOSED`
    with no such line after it; measured first that the timer doesn't fire in a normal quit, nor in the aboutToQuit and
    thread-pool cases (a nested event loop in the teardown would fire it). A choice for the user.
  - **Resolution: done**, the limit stated: the user's choice of the two (2026-11-11), recorded in DECISIONS.md (Bridge
    and quitting). `designer_helpers/quit.py`'s docstring gives both cases and what was measured, and its comment no
    longer says every window refusing its close keeps Designer from quitting; `project_constants.py`'s comment and
    `lifecycle.py`'s docstring say the line is the helper's judgement, pointing at those limits. No check added, as for
    HLP-103's limit. Also covered: the tool's docstring ("whether its close had taken") left as it is, an agent using
    the tool acting no differently (AGENTS.md's table); the threshold's DECISIONS entry still holds.

- [x] **TST-306 · The forced-quit unit test's last line isn't blank, so quoting the last line that isn't blank is unguarded · follows SRV-106, generation 2** · `tests/unit/test_lifecycle_env.py:853`, `mcp_server/server_tools/log.py:137-138` · confirmed · found 2026-11-11
  - **Defect.** The fixture `[NEW, START, '[INFO] ready', CLOSED, '[INFO][IPC] Remove PID', '']` is written
    `'\n'.join(lines)`: the `''` only adds a final newline, which `splitlines()` drops (checked in plain Python), so
    `_quit_evidence` never sees a blank line; SRV-106's fix quotes the last line that isn't blank (a real log ended in
    126).
  - **Scenario.** `said[-1] if said else ''` replaced by `lines[-1].strip() if lines else ''`: every unit test passes,
    and a forced quit on a log ending in blank lines quotes `""`.
  - **Fix.** End the fixture with lines that are blank in the file (`'', ''` or `'   '`), and see the test fail under
    that mutation.
  - **Resolution: done.**
    - **Test:** the forced-quit test's fixture ends `'', '   ', ''`: with `said[-1] if said else ''` replaced by
      `lines[-1].strip() if lines else ''` it failed, quoting `""`, where the old fixture passed under that mutation;
      it passes on the code.
    - **Cause:** the trailing `''` only made the file end in a newline, which `splitlines()` drops.
    - **Fix:** the fixture.
    - **Also covered:** the "had not closed" cases also assert the quoted line; their fixtures end in a line that isn't
      blank, the blank case resting on this one.

- [x] **TST-307 · The "designer facts" prompt check can no longer fail on the fact it names · follows HLP-105, generation 5** · `tests/test_all_tools/lifecycle/checks.py:622-647`, `tests/test_all_tools/lifecycle/designer_scripts/quit_prompt_after_close.py:1-2`, `mcp_server/server_tools/lifecycle.py:19-20` · measured · found 2026-11-11
  - **Defect.** "Designer quits once its main window closes, even with another window shown": since HLP-105 the helper
    closes the prompt too, and Designer quits on its last window closed (`quitOnLastWindowClosed()` is True, measured
    2026-11-11), so a Designer that stayed while another window showed would pass. The module's "closing the visible
    top-level widgets quits Designer normally, even with another top-level window showing (measured)" rests on it.
  - **Scenario.** A Designer version that no longer quits on its own window's close: the check passes, and the
    docstring's fact goes stale unseen.
  - **Fix.** Narrow (generation 5): the check's name and comment, and the script's docstring, say what it shows
    (Designer quits once the helper has closed its window and a prompt shown as it closed, logging `QUIT_CLOSED`);
    the module drops "even with another top-level window showing (measured)". No check added.
  - **Resolution: done.** Narrowed: the check is "Designer quits once the helper has closed its window and a prompt shown
    as it closed", and its comment and the script's docstring say so; `lifecycle.py`'s docstring drops "even with
    another top-level window showing (measured)", keeping the modal dialog. The renamed check passed in a scratch run of
    `lifecycle` (46 checks, none failed).
