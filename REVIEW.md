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

- *Confirmed*: the defect is visible in the code as quoted.
- *Plausible*: the code path exists, but whether it bites depends on Designer, the OS or timing.
- *Verified by hand*: checked against the code after the review, not only by the reviewer.

**IDs.** One prefix per area, numbered on: **PLG** plugin and bridge protocol, **SRV**
`mcp_server/server.py` and `server_tools/`, **HLP** `mcp_server/designer_helpers/`, **INS** installer, uninstaller,
command-line client and example, **TST** tests and docs. A new area gets a new prefix, added here.

**Last used:** PLG-31, SRV-81, HLP-82, INS-26, TST-146.

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
| Medium | 0 | 3 |
| Low-medium | 0 | 2 |
| Low | 0 | 4 |
| **Total** | **0** | **10** |

## Review log

### 2026-11-05: branch `quit-review-fixes` against `main`, the diff and the uncommitted changes

- **How:** one read-only reviewer, reading the code before the resolutions; no Designer, no live self-test. Unit tests ran (692 passed), with probes and five mutations in a scratch copy; one mutation didn't apply, so it says nothing. The finding read against the code by hand. Not checked: the live checks, which were only read, and a C++ call holding the GIL.
- **Resolutions assessed:** all nine hold. TST-146 is questioned by SRV-81, for one message its search missed.
- **Findings:** 1: low (SRV-81). No behaviour defect, nothing that can end the wrong process or lose the user's work. Nothing added to the longest chain, HLP-82 -> SRV-74 -> SRV-78, generation 3.
- **Suggested order:** SRV-81 alone.
- **Not entries:** no test guards `running and` in `if running and _end_if_past_startup()`, which the "larger wait_s" advice relies on; the code is right, and at generation 3 about tests only it adds no check. A retry that waits leaves the Home screen up, which `open_graph` closes. A timed-out close's result says "try cancel_designer_job" above "forced": noise.
- **Checked and found fine:** `_bridge`'s conditional and its precedence; `quit_designer(%d)` has one server caller and the self-test's other; an agent's ended with the user's running starts nothing and signals nothing; a retry with a larger `wait_s`, either side of the limit, ends the old one and gives the new one the whole wait; `_started_by` never calls the port's other Designer the agent's; a close left queued in a frozen Designer of the user's only refuses when it thaws; removing `_still_starting`, `running == [own]`, the close's limit or `running and` from the restart check each failed a test; docstrings, AGENTS.md, README.md and the state table match the code.

### 2026-11-05: branch `quit-review-fixes` against `main`, the diff only

- **How:** one read-only reviewer, reading the code before the resolutions; no Designer, no live self-test. Unit tests and probes with a faked process list and bridge ran. Every finding read against the code by hand. Not checked: whether the plugin's status thread keeps answering during a main-thread freeze (the GIL), what macOS does on `open -a` right after a force-end, and a second Designer binding the port while one is stuck closing.
- **Resolutions assessed:** SRV-73, SRV-76, TST-146 and SRV-77 hold. SRV-74 holds for jobs running and queued, questioned by SRV-78. SRV-75 holds for a `wait_s` under the limit, questioned by SRV-79 and SRV-80.
- **Findings:** 3: 1 medium (SRV-78), 2 low (SRV-79, SRV-80). Nothing that can end the user's Designer or lose their work. Longest chain growing: HLP-82 -> SRV-74 -> SRV-78, generation 3, kept as an entry because it is a hang in the tools' code.
- **Dropped:** a healthy older Designer ended after one failed status call, and other triggers with that result, by "A Designer the user opened is theirs; one an agent started is disposable"; a Designer the user opens during the wait, by "A Designer the user opens during `launch_designer`'s wait can be recorded as the agent's".
- **Suggested order:** SRV-78, then SRV-79 and SRV-80, all in `launch_designer` and `quit_designer`.
- **Checked and found fine:** `^process (\d+)$` can match only the real first line, and the output's other readers use substrings, a UID regex or `is_error`; `'idle, 0 queued'` can't match `idle, 10 queued`; the record's age is read only after the record is verified, and a restart writes a fresh one; the call that started a Designer is never ended by its own loop; with an agent's ended and the user's running, nothing new starts and the user's gets no signal; on Windows nothing reaches `_force_end`; a refused status ends only the agent's; the self-test restores the record in `finally`, and its job thread is a daemon with a 60 s limit.

### 2026-11-05: commit `320d35f` against its parent, the diff only

- **How:** one read-only reviewer, given the code and none of the earlier conclusions; no Designer, no live self-test. Its unit tests and a probe faking the process list and socket ran; every finding read against the code by hand. Not checked: whether macOS opens a second instance while one is stuck closing, whether `sd` calls hold the GIL, and whether `hold_thread_pool.py` gives the same stack as HLP-82.
- **Resolutions assessed:** HLP-82's holds for its own scenario, with the bridge gone; SRV-74 is the gap. No finding dropped for contradicting a decision: ending or dropping work in an agent's Designer is settled, and none of these argues with it.
- **Findings:** 6: 1 medium-high (SRV-73), 2 medium (SRV-74, SRV-75), 2 low-medium (SRV-76, TST-146), 1 low (SRV-77). Longest chain growing: HLP-82 -> SRV-74, generation 2.
- **Suggested order:** SRV-73, as it can lose the user's work; SRV-75 and SRV-74 in the same function pair; then SRV-76 and TST-146, sentences only; SRV-77 last, the narrowest.
- **Checked and found fine:** a missing, corrupt or wrong-shape record or a reused ID falls back to "the user's", and a stale file goes; `quit_designer` with no record sends nothing and signals nothing; `_force_end` keeps the record if it fails; `start()` retakes `before` on a restart; `end_own_designer` checks ID and start time; the unit tests' fixture keeps them away from real processes and the real record. Windows, where the self-test now leaves its Designer open though README and `__main__.py` say it closes it, belongs with ROADMAP item 18.

---

## High

## Medium-high

- [x] **SRV-73 · `quit_designer` checks one process but sends its close to whichever Designer holds the port** · `mcp_server/server_tools/lifecycle.py` (`quit_designer`, `designer_status`), `mcp_server/designer_helpers/quit.py` · confirmed routing, plausible trigger · verified by hand · found 2026-11-05
  - **Defect.** `own = _agent_designer()` checks the recorded process, then `_bridge(_helpers_call('quit_designer()'), timeout=30)` goes to the port, and nothing ties the two together. The helper unloads every modified package with no prompt, relying on "the server only asks this of a Designer an agent started".
  - **Scenario.** An agent's Designer A is stuck closing, so it is still running with its port released. The user starts a second Designer U (`open -n`, or the binary), whose plugin binds the free port. `quit_designer` finds A, but the job runs in U: U's unsaved packages are dropped and its windows close. A is then force-ended. `designer_status` has the same gap: "Started by an agent: disposable" comes from the record, above a package list from the port's holder. How macOS treats a second start while one is stuck wasn't measured. `test_quit_leaves_the_users_next_to_the_agents` fakes `_bridge`, so it doesn't see this.
  - **Fix.** Pass the process ID in, `quit_designer(%d)`, and raise in the helper before unloading anything if `os.getpid()` differs; the existing `suppress(ToolError)` then goes on to force-end `own` only. `designer_status` compares the ID the same way. A unit test asserts the job carries the ID.
  - **Resolution: done.** Test: `test_quit_names_the_process_it_means` and `test_quit_with_another_designer_on_the_port_only_ends_its_own` failed, the close naming no process; `test_designer_status_goes_by_the_designer_answering` failed, labelling the port's other Designer as the agent's. Live: the close asked of another process raises and the unsaved package stays; `os.getpid()` inside Designer is the recorded process. Cause: the record identifies a process and the bridge a port, and nothing tied them together. Fix: `quit_designer(agent_pid)` in the helper raises before unloading anything if it isn't that process, and the server then force-ends only its own; `designer_status` prints the process answering and labels by it. Also covered: while a job runs, with no listing to ask, `_started_by` calls it the agent's only if it is the one Designer running. `launch_designer`'s `leave_home_screen` goes by the port too, but only closes a Home screen. Not measured: whether macOS opens a second Designer while one is stuck closing.

## Medium

- [x] **SRV-74 · `quit_designer` can wait about 15 minutes before `wait_s` starts (follows HLP-82, generation 2)** · `mcp_server/server_tools/lifecycle.py` (`quit_designer`), `mcp_server/server_tools/core.py` (`_bridge`), plugin `__init__.py` · confirmed · verified by hand · found 2026-11-05
  - **Defect.** The close is an ordinary queued job, so `_bridge` waits `QUEUE_WAIT + 30 + 60` = 990 s, and the force-end comes only after it returns. "After wait_s it is force-ended" doesn't hold while Designer is busy.
  - **Scenario.** A long script, or one stuck in the modal "Save Dependency" dialog, runs in an agent's Designer. `quit_designer(wait_s=10)` queues behind it, gets "Designer was busy for 900s" 15 minutes later, swallows the error, and only then starts its 10 s. The live checks use an idle bridge and the unit tests fake `_bridge`, so neither sees it. HLP-82's own case, with the bridge gone, is fixed.
  - **Fix.** Ask `_control('status', wait=5)` first and send the close only when it reports idle with 0 queued; otherwise go straight to the wait and the force-end, with a note that a job was running.
  - **Resolution: done.** Test: `test_quit_doesnt_queue_behind_a_job`, running and queued, failed with the close sent; a live check holds the bridge with a job and `quit_designer(wait_s=2)` forces it (2 s, within the check's limit of 30). Cause: the close was a queued job, and the wait began only after it returned. Fix: `quit_designer` asks the status first and sends the close only when idle with nothing queued; otherwise the result says it was busy. A failed request of any kind is now reported in the result rather than swallowed. Also covered: `designer_status` already asks first. Not covered: a job starting between the status and the close, a window of milliseconds.
  - Questioned by SRV-78 (2026-11-05).

- [x] **SRV-75 · `launch_designer` ends an agent's Designer that is only slow, so a retry may never finish** · `mcp_server/server_tools/lifecycle.py` (`launch_designer`) · confirmed; the GIL case plausible · verified by hand · found 2026-11-05
  - **Defect.** Any failure of the 5 s status call counts as "not answering", including a Designer still starting: `ended = own is not None and _force_end(own)`. The docstring says both that one still starting is waited for and that an agent's not answering is ended.
  - **Scenario.** `launch_designer(wait_s=60)` on a machine needing 90 s fails, with the record already written. The retry kills the half-started process and starts over, so the same `wait_s` never succeeds; before this change the retry waited and did. A second session calling it during the first's launch kills that session's Designer, as the record is global. A long C++ call holding the GIL over 5 s might make a healthy one look dead (not measured). Ending it is allowed by "A Designer the user opened is theirs; one an agent started is disposable"; the defect is not getting anywhere, and the docstring. ROADMAP item 25's state table has no row for it.
  - **Fix.** Force-end only a process older than a startup limit, and wait on a younger one. Correct the docstring and add the table row.
  - **Resolution: done.** Test: `test_launch_state_agents_still_starting` failed with the process signalled, and `test_launch_state_agents_too_slow_for_this_wait` with `Ended...` and no advice. Cause: every failed status call counted as stuck, with no idea of how long the process had had. Fix: `launch_designer` waits on one whose record is younger than `STARTUP_LIMIT` (180 s, its default wait; the self-test's starts took 6 to 9 s), and ends it once past that, during the wait too; the message says calling again waits for it. Docstring corrected, three rows added to the state table, the live check ages the record. Also covered: a second session during a launch is the same case. Not covered: an older Designer whose status call fails while a long C++ call holds the GIL, not measured; it is disposable, and AGENTS.md no longer sends agents to `launch_designer` first.
  - Questioned by SRV-79 and SRV-80 (2026-11-05).

- [x] **SRV-78 · `quit_designer` can still wait about 15 minutes when Designer's main thread is frozen (follows SRV-74, generation 3)** · `mcp_server/server_tools/lifecycle.py` (`quit_designer`), `mcp_server/server_tools/core.py` (`_bridge`) · confirmed path, plausible trigger · verified by hand · found 2026-11-05
  - **Defect.** The status check doesn't show that the main thread can run the close: the plugin answers status from the client's thread, and `busy_since` is set only inside `_drain`, on the main thread's timer. So a frozen main thread reads `idle, 0 queued`, and the close goes out with `_bridge`'s wait of 990 s. SRV-74's "Not covered", a window of milliseconds, understates this.
  - **Scenario.** An agent's Designer is stuck outside a bridge job: a long C++ call from the UI or a timer, a deadlock, or a start past the plugin's load and before the event loop runs. `quit_designer(wait_s=10)` sees idle, queues the close, gets "busy for 900s" 15 minutes later, and only then starts its 10 s. A probe with a faked bridge showed the waits `status 5, close 990`. How often the main thread freezes with the bridge's thread still answering wasn't measured.
  - **Fix.** Give the close a limit of its own, tied to `wait_s`, and treat a timeout as "did not reply": a job left queued can only run in the process being ended. This closes the window SRV-74 named too. A unit test asserts the wait is bounded. `designer_status` and `leave_home_screen` have the same queued wait but promise no time, so they stay.
  - **Resolution: done.** Test: `test_the_close_has_a_limit_of_its_own` failed with `[990] == [10]`. Live: a timer slot sleeping in a loop freezes the main thread outside any job; the status reads `idle, 0 queued`, which a "designer facts" check now holds, and `quit_designer(wait_s=2)` forces it after the close's 10 s with no reply. Cause: the wait on the close was the one for any queued job, while the status check could only see bridge jobs. Fix: `_bridge` takes a `wait`, and `quit_designer` gives its close `max(wait_s, 10)`; a timeout goes on to the force-end. Also covered: this closes the window SRV-74 left, a job starting between the status and the close. `designer_status` and `leave_home_screen` keep the long wait, as they promise no time and end nothing.

## Low-medium

- [x] **SRV-76 · The `kill` advice for the user's Designer doesn't say when it is safe** · `mcp_server/server_tools/lifecycle.py` (`launch_designer`, `_how_to_end`), `README.md` Troubleshooting · confirmed · verified by hand · found 2026-11-05
  - **Defect.** `' It may also be stuck closing: %s.' % _how_to_end() if running else ''` is printed for every running Designer whose bridge doesn't answer, and never says "only if its windows have gone", the condition that makes it safe.
  - **Scenario.** The user's Designer has unsaved graphs, and its bridge doesn't answer because another program holds the port or the plugin didn't load. The agent relays "end it in Activity Monitor, or with `kill 123`", and the user loses their work. README's "Nothing is lost" rests on the same condition.
  - **Fix.** Reword: if its windows have closed, end it with the ID and command; otherwise ask them to save and close it. The message keeps the ID and the command the user asked for.
  - **Resolution: done.** Test: `test_launch_state_users_not_answering`, extended, failed with `substring not found`. Cause: the advice was written for the stuck case and printed for every Designer not answering. Fix: the message gives the ID and command under "If its windows have closed", then says that if they are open, ask the user to save and close it; README's Troubleshooting row says the same. Also covered: `test_launch_state_second_instance` goes through the same text; an agent's own young Designer gets no `kill` advice at all.

- [x] **TST-146 · Docs still describe the old quit, one of them backwards** · `README.md` (Tools table), `AGENTS.md` (When tools fail), `mcp_server/designer_helpers/screenshots.py` · confirmed · verified by hand · found 2026-11-05
  - **Defect.** README's Tools table says `quit_designer` "refuses while there are unsaved changes"; it now drops them in an agent's Designer and refuses the user's outright. AGENTS.md's "When tools fail" says "First try `launch_designer`", against its own rule to ask the user to open Designer. `screenshots.py` cites the deleted `test_quit_fallback`, and the docstrings of `designer_scripts/lifecycle/quit_slow_shutdown.py` and `quit_ignores_close.py` still say "fallback".
  - **Scenario.** A person reading the table believes unsaved work in an agent's Designer is protected. An agent doing a user's material work after a crash starts a Designer recorded as disposable, the user works in it, and a later `quit_designer` drops that work.
  - **Fix.** Correct these sentences; no new checks.
  - **Resolution: done.** Test: none, as these are sentences. Cause: the docs were searched for the fallback and `discard_unsaved`, not for what they said `quit_designer` and `launch_designer` do. Fix: README's Tools table; AGENTS.md's "When tools fail" no longer starts with `launch_designer`; the comment in `screenshots.py` and the two scripts' docstrings. Also covered: no other mention of `test_quit_fallback` or the old refusal; the fallback is named only by ROADMAP's checked item 23, which says it is gone. README and `__main__.py` saying the self-test closes its Designer don't hold on Windows; that is ROADMAP item 18.
  - Questioned by SRV-81 (2026-11-05).

## Low

- [x] **SRV-77 · The process recorded as an agent's can be one the user opened during the wait** · `mcp_server/server_tools/lifecycle.py` (`launch_designer`, `_remember_started`) · plausible · verified by hand · found 2026-11-05
  - **Defect.** `_remember_started(before)` runs through the whole wait and takes the only new process, whoever started it.
  - **Scenario.** `open -a` leaves no lasting process (a crash at startup), and the user opens Designer within the 180 s. It is recorded as the agent's, its Home screen is closed, and a later `quit_designer` drops their work.
  - **Fix.** Record only a process whose start time is within a few seconds of the `start()` call.
  - **Resolution: won't fix**, the user's decision (2026-11-05), recorded in `DECISIONS.md`. Test: none, no code changed.

- [x] **SRV-79 · Past the limit and impossible to end, `launch_designer` says a later call will end it (follows SRV-75, generation 2)** · `mcp_server/server_tools/lifecycle.py` (`launch_designer`, `_end_if_past_startup`) · confirmed · verified by hand · found 2026-11-05
  - **Defect.** `_force_end` failing returns False, the same as "still starting", so the message promises what has just failed, and the loop repeats the signals at every poll, about 10 s each.
  - **Scenario.** An agent's Designer past the limit ignores SIGKILL, stuck in an uninterruptible call. A faked process list showed four SIGTERM and SIGKILL pairs, then "calling this again waits for it, and ends it". `quit_designer` already says "could not be ended; ask the user to run `kill -9`".
  - **Fix.** After the first failed force-end, stop trying and give `quit_designer`'s message.
  - **Resolution: done.** Test: `test_launch_stops_at_an_agents_it_cant_end` failed, its error not matching. Cause: a failed force-end returned the same False as "still starting". Fix: `_end_if_past_startup` raises at the first failure, with the message `quit_designer` uses, now one function, `_could_not_end`. Also covered: both of `launch_designer`'s calls go through it, at the start and during the wait.

- [x] **SRV-80 · With the default `wait_s`, a retry gets no more time and nothing says to pass a larger one (follows SRV-75, generation 2)** · `mcp_server/server_tools/lifecycle.py` (`launch_designer`), `project_constants.py` · confirmed logic, plausible trigger · verified by hand · found 2026-11-05
  - **Defect.** `STARTUP_LIMIT` equals the default wait, so a start over 180 s times out with no advice, and the retry, seconds later, finds it past the limit and ends it. SRV-75's "a retry may never finish" remains above the limit. A call that starts Designer isn't limited, so `wait_s=300` works, but nothing says so. The self-test's starts took 6 to 9 s; whether a real one takes over 180 s, a cold start or a sign-in dialog, is unknown.
  - **Fix.** One sentence in that branch of the message: if it needs longer, call with a larger `wait_s`. No new check.
  - **Resolution: done.** Test: `test_launch_times_out_when_the_bridge_never_answers`, extended, failed with the sentence missing. Cause: the limit equals the default wait, and the message gave no way out. Fix: the message says "If it needs longer, call this with a larger wait_s", where it starts or restarted Designer itself. No new check beyond that sentence. Also covered: a retry with a larger `wait_s` finds the old one past the limit, ends it and gives the new one the whole wait, which `test_launch_state_agents_not_answering` shows for a start after an end.

- [x] **SRV-81 · "Designer is not reachable" still tells the agent to start Designer (follows TST-146, generation 2)** · `mcp_server/server_tools/core.py` (`_send`), `mcp_server/server_tools/lifecycle.py` (`quit_designer`) · confirmed text, plausible effect · verified by hand · found 2026-11-05
  - **Defect.** `'Designer is not reachable. Start Designer (the %s plugin loads on startup).'` goes against the rule to ask the user to open it, which TST-146 corrected in AGENTS.md but not in this message. `quit_designer` now shows it too, having swallowed it before this branch.
  - **Scenario.** Any tool, with Designer closed or crashed: the agent has a tool named `launch_designer`, starts a Designer recorded as disposable, the user works in it, and a later `quit_designer` drops that work. And a Designer stuck closing with its port released reports "did not reply: Designer is not reachable. Start Designer (...)", then "Designer quit after Ns (forced...)".
  - **Fix.** Change the sentence only, for example "Designer is not reachable: if it is closed, ask the user to open it (the %s plugin loads on startup)." No test or doc quotes the old wording.
  - **Resolution: done.** Test: `test_a_closed_designer_is_left_for_the_user_to_open` failed on the old wording. Cause: the message predates the rule to ask the user, and TST-146 searched the docs, not the tools' messages. Fix: `_send` says "Designer is not reachable: if it is closed, ask the user to open it". Also covered: `mcp_server/server_tools`, `designer_helpers`, `client`, `install.py` and `uninstall.py` searched for advice to start Designer, and none other found; `client/sd_run.py` only says Designer isn't running.
