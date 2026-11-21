# DECISIONS.md: what is already settled

This is the memory for the whole project, for all time. `REVIEW.md` is the memory per branch, which the lead writes
from the reviewers' and the developer's reports; its history stays in git.

Won't-fix items and project rules that a reviewer could plausibly raise again.
A finding that contradicts an entry here is dropped, unless the entry's **Reopen if** holds; then it
is a new finding that names the entry and the evidence. Unlike an answer in `REVIEW.md`, an entry can't be questioned
any other way.

Each entry stands on its own: the decision, the reason and what would reopen it, pointing at the code,
test or doc it concerns. Entries don't cite review findings. "The user" is named only where the record
says so. Measured Designer behaviour lives in `GUIDE.md` or the module's docstring; an entry links to it rather than repeating it.

An entry is a bold one-line decision, then the reason, then `Reopen if: <condition>.`, with who decided and
when if the user did. An entry comes from a decision of the user's, on a finding or about the project. A false
finding (not a bug, not reproducible) is no decision and stays in `REVIEW.md` (the user, 2026-11-20). Only what would
stop reviewers raising the same finding again goes in. A cleanup of `REVIEW.md` adds
nothing here. Agents may update the names and paths an entry points at; changing what was decided, or removing an
entry, takes the user (the `address-review` skill (`.claude/skills/address-review/SKILL.md`), **Recording decisions**).

## Project rules

- **The full suites run only when the user asks; while working, only the tests added or modified run, always with lint
  and types, a live check in a scratch run.** The full suites take longer than the tests of one change (their times:
  `tests/test_all_tools/workers.py`). No agent starts a whole run of either suite on its own, not for TDD, not after a
  fix, not between reviews: when the reviews look converged, the lead says so, and the user decides: another round, or
  the final check (both suites in full, before merging into `main`) when they say the work is done. Lint and types
  (`test_lint.py`, `test_types.py`) run with every test run, whichever tests it has. Docs changed alone run the doc
  tests instead (`.claude/rules/docs-tests.md`). Tests run at two stages: an agent's own tests while working, and the
  full suites at the end, which the `runner` agent runs (the user, 2026-11-19). How each stage runs: AGENTS.md,
  Running the tests, and the `live-check` skill (`.claude/skills/live-check/SKILL.md`).
  A change not having run the full suites, before the user asks for them, is not a finding; a branch merged without
  them passing is.
  Reopen if: the full suites become fast enough to run after every change, or a break found only in the full run cost
  more than the time saved. (The user's decision, 2026-11-06.)

- **A test that fails in a full run and passes rerun alone failed at random, and counts as passed.** The runner reruns
  each test the final check failed, alone, each as it needs (the user, 2026-11-21: "run the category in isolation for
  which that test is belonging", then "rerun"):
  - A unit test is rerun by name.
  - On macOS, a live check is rerun through the pool with its category alone (`tests/test_all_tools --only
    <category>`), which also makes the checks the pool makes for that category: its quit and crash dumps, and the
    run's start checks when they ran in it.
  - The check that every tool was exercised, made only over a full run, names the tools no check ran for: the
    categories whose checks exercise them are rerun alone, and if they pass with checks run for those tools, it failed
    at random too (the user, 2026-11-21). Their PASS lines in the rerun's output show those checks ran, as its summary
    leaves out a tool no check ran for.
  - The pool's other checks over the whole run are rerun with what they need (the user, 2026-11-21: "rerun"). The
    count of quits forced is rerun with the categories it names, together (`--only <category> ...`). Designer's
    preferences and a crash dump outside the run name no category, so they are rerun with the whole live self-test
    (`tests/test_all_tools --no-unit`). Another check failing in that rerun is rerun alone too, as a failure of the
    final check.
  - Off macOS, where `--only` refuses (ROADMAP item 65), a live check is rerun with its category alone in a scratch run
    (`alone.run`, the `live-check` skill), once the user has closed the Designer the run left open: there `alone.run`
    takes every running Designer for the user's. The checks only the whole run makes there, such as its start checks
    and its check that the user's graph is back in the editor, are rerun with the whole run there.

  A check that skips in its rerun is rerun once the cause of the skip is cleared, such as a Designer outside the run;
  one whose cause can't be cleared is a failure. A test that passes alone counts as passed for the merge, and the lead
  adds its row to ROADMAP.md's "Tests that failed at random", or raises the count of the row it has, after the final
  check and before the merge, with the docs tests run on that row (the `live-check` skill, When the final check
  fails). One already listed there that fails at random again has its count raised, and the merge goes ahead: it is
  fixed when ROADMAP.md gets to it, whatever its count (the user, 2026-11-21: "no fix is mandatory since it passed when
  running its category alone. Having it in roadmap is eenough"; "if it passes no fix now. we have it in the table and
  fix it at some time"). A failure that meets another entry's Reopen if still meets it when its rerun passes, such as
  the count of quits forced (Bridge and quitting) or a crash dump pointing at a cause: the merge goes ahead, and the
  lead tells the user. A test the branch was to make robust that fails at random reopens the branch's ROADMAP.md
  item: the merge goes ahead with the test's row in "Tests that failed at random", and the item is unchecked, its
  Done note naming that row, as its fix isn't proven. The user's answer, 2026-11-21, asked of item 112: "Merge,
  reopen 112"; this form for every branch is the lead's reading, told the user. One that fails alone too is a failure, fixed before the merge. A pass alone shows the failure
  is rare, or needs the full run's conditions; the count shows which tests fail now and then, for the tool or the check
  (ROADMAP item 112: its zoom check passed 3 times in 3 in scratch runs, while the 3D zoom lost a step in 2 runs of 120
  with the window hidden right after the first step: `designer_helpers/view3d.py`). The user's decisions, 2026-11-21.
  Reopen if: the table grows faster than its tests are fixed, or the user changes the rule.

- **Only the current and next versions of Designer are supported.** README says older versions aren't, and the plugin's
  manifest asks for 16.0.0, so code needn't work on an older Designer or its older Python.
  Reopen if: the user wants older versions supported. (The user's decision, 2026-11-03.)

- **Every Python file runs only on Python 3.12 or later; the scripts a user starts stay readable by an older Python,
  so that they refuse it with a message.** The server's venv and every test run on 3.12, and the code uses what 3.12
  has, the scripts and the modules they import included. The scripts a user starts (`install.py`, `uninstall.py`,
  `client/sd_run.py`, `scripts/`) are started with whatever `python3` is installed. Run on an older `python3`, such
  as a stock Mac's 3.9, they print "Python 3.12+ is required (found 3.9.6)" instead of a traceback. How the scripts do it:
  `.claude/rules/python.md`, Typing. `uninstall.py` removes the venv, so it should run on a system Python 3.12 or
  later, not the venv's (it says so when it does).
  Reopen if: a system this project supports can't install Python 3.12, or Designer's own Python falls below the
  server's minimum. (The user's decision, 2026-11-17.)

- **Linux is not a target: nothing is fixed, tested or reviewed for it.** The project will never run on Linux, so a
  review raises nothing about it: no finding about code paths, platform guards, tests or docs that would only matter
  there. Where the code or docs name Linux, it is no promise that anything works there.
  Reopen if: the user wants Linux supported. (The user's decision, 2026-11-07.)

- **Low-value findings about the tests and docs are not raised.** A review doesn't report: a defect in the test
  infrastructure that shows only after two failures at once, or after a failure no run here has seen (the process
  listing failing as a run starts), when the worst it does is end or leave a Designer an agent started (disposable)
  or a temporary folder; a live check that only repeats a guard a unit test already gives; a follow-up at generation 3
  or later on the docs that changes nothing anyone does (two places that agree, a figure in a plan). Still raised: any
  defect in the tools' code, anything that can touch the user's work, and a doc that says something false.
  Reopen if: such a finding turns out to have hidden a real break, or the user changes the rule. (The user's decision,
  2026-11-07.)

- **A category's preparation opens its graph in the editor only where its checks read the editor.** Each category of
  the self-test starts from its own preparation in a Designer just started, and most never open their graph, where in
  `main`'s one run earlier categories had left one open. Measured (2026-11-11): `params`, `inputs`, `bitmaps` and
  `safeguards` with their graph open, then also with an output node in it, passed 213 of 213 each time, in 4 Designers;
  no tool they call reads the editor. `facts`, `link_display`, `undo` and the editor categories open theirs, since what
  they check needs it. The user's decision, 2026-11-11.
  Reopen if: a defect shows up that needs a view open, in a category whose preparation doesn't open its graph.

- **A Designer the user opened is theirs; one an agent started is disposable.** The tools never end the user's: `quit_designer`
  refuses, and the agent asks them to save, close and reopen it, or to open it if a task needs it. A user wanting a material already
  has Designer open, so an agent only starts one for tests or work on this project, and ends it however works, force included,
  dropping what is unsaved (`server_tools/lifecycle.py`). The user's decision, 2026-11-05.
  Reopen if: the user changes the rule.

- **During tests, no window of an agent's Designer comes in front of the user's windows unless a check needs it
  there.** It stops their work: "a deal breaker" (the user, 2026-11-15). Reopen if: the user asks for it.

- **No agent has a write guard: what each may change rests on its instructions.** The `developer`'s job is changing
  code, and the `runner` writes scratch scripts and probes, so a guard would block their work. The `analyst` and the
  `reviewer` only read because their files tell them to, and no hook enforces it: "only instruct agents that only have
  to read to do so, without having to enforce them by a limiting hook" (the user, 2026-11-19). A hook that let only
  reading Bash commands through (`.claude/hooks/read_only_bash.py`) was dropped. Each of three reviews found another
  shell form around it, and it cost more than it protected. `.claude/agents/developer.md` says it never commits, runs
  no full suite and starts only `/simplify`'s cleanup agents and `analyst` agents; `.claude/agents/runner.md` says it changes none of the
  repository's files; `analyst.md` and `reviewer.md` say they only read. A review doesn't report a missing guard, nor
  the developer's Agent tool reaching every agent type.
  Reopen if: an agent changes what its instructions forbid. (The user's decisions, 2026-11-18 and 2026-11-19.)

## Security

- **Only the client is authenticated, not the plugin.** A program running as the same user could read
  the owner-only token file anyway, so mutual authentication helps only against another user account
  on the same machine, and scripts carry no secrets. It would also mean a protocol change in the
  plugin, the server, `sd_run.py` and the self-test together (README, Security;
  `test_clients_never_send_the_token`). Agreed with the user, 2026-10-29.
  Reopen if: scripts start carrying secrets, or the bridge becomes reachable from another machine.
- **A client's answer is bound to the port and the request; `port=` takes any port.** Restricting `port=` to ports this
  server launched or recorded was the alternative; the binding (plugin docstring) closes the relay for every port. The
  user's choice, 2026-11-07.
  Reopen if: a client can reach the plugin through a port other than the one it listens on (a port forward, a proxy),
  so the port signed and the port checked differ.
- **The plugin reads a whole request before checking its signature.** The signature covers the bytes as received and
  code runs only after it checks out. Anything reaching the bridge is already on the user's machine (it listens on
  `127.0.0.1`), so the worst a program without the token can do is make Designer hold about 1 GiB for up to 30 s (16
  connections, 64 MiB each). Checking before the whole request has arrived would change the protocol in the plugin, the
  server, `sd_run.py` and the self-test together. The user's decision, 2026-11-04.
  Reopen if: the bridge becomes reachable from another machine.

## Library packages

- **`execute_designer_code` and `run_designer_script` aren't checked for edits to a library graph.**
  On purpose: the tools refuse such edits (`_graph_to_edit`, `designer_helpers/core.py`), and a person's
  or agent's own code is not checked (`GUIDE.md`, Environment facts).
  Reopen if: the user wants scripts restricted.
- **A definition naming a function or another resource isn't told apart from a graph**
  (`designer_helpers/describe.py`). The suggested fix would remove what works for bitmaps and SVGs. What
  remains is a cryptic error, with nothing changed, on an id `search_nodes` never prints. Agreed with the
  user, 2026-11-02.
  Reopen if: such an id starts changing something, or `search_nodes` starts printing such ids.
- **`preview_node` and `node_stats` count as reads on a library graph.** Their temporary output node can leave the package
  marked modified, with its content unchanged, so closing Designer may ask about it. Saving is refused for library packages,
  so the way out is for the user to close Designer without saving it, after saving what they want to keep. The user's decision, 2026-11-04.
  Reopen if: a read is seen to change a library graph's content.

## Snapshots and saving

- **Only a snapshot of an unsaved package gets a fresh UID** (`_fresh_uid`, `server_tools/snapshots.py`).
  A saved package's snapshots, told apart by file, stay Designer's exact copies. The user chose this out
  of three options: re-stamp every snapshot, only unsaved packages', or none and accept the limit.
  Reopen if: the user changes the choice, or snapshots of saved packages get mixed up.
- **Only the files that hold the user's work are written all-or-nothing by our code:** snapshots and `set_link_display`'s
  `.sbs`. The installer's `SKILL.md`, the example's generated `.sbs` and `node_stats`' temporary buffer aren't, because
  they can be recreated. Designer's own saves and exports aren't ours to control. This is about one file being
  half-written, not about a command that makes several changes. The user's decision, 2026-11-04.
  Reopen if: a tool starts writing the user's work another way.

## Function graphs and inputs

- **`drives:` and `remove_graph_input`'s refusal differ on purpose.** `drives:` says what has an effect
  today; the refusal also counts a function with no effect today, since a later edit could connect it
  (`designer_helpers/graph_inputs.py`).
  Reopen if: the user changes the rule.
- **A graph input bound to an instance's parameter isn't checked as a size.** The instance's own parameter and `expose`'s
  default are (`_refuse_bad_size_on_input`, `designer_helpers/graph_inputs.py`); this one is a known limit, stated in that
  docstring. Only an instance a person made reaches it, as `add` instances only library graphs, and following the binding
  would widen the check again for that case. The user's decision, 2026-11-09.
  Reopen if: the tools become able to instance a user's own graph, or an agent is seen to build a wrong size this way.

## Bridge and quitting

- **`quit_designer` repeats the whole protocol-mismatch message when it ends an agent's Designer whose plugin is
  another version.** Its advice ("quit_designer and launch_designer for one an agent started") then names the call that
  has just ended it; what it does is right (`server_tools/lifecycle.py`, `OTHER_PROTOCOL` in `server_tools/core.py`).
  Such a plugin runs only between an update and the next restart of that Designer: older plugins aren't used, as
  `install.py` installs the plugin with the server. The user's decision, 2026-11-07.
  Reopen if: plugins of other versions come to be used next to the server.

- **A stopped plugin server keeps its timer and waker until Designer's Python ends** (`_retired`,
  `uninitializeSDPlugin` in the plugin). Freed with the server, they could be destroyed by a client's thread being served
  as the plugin unloads, off the main thread they belong to. Kept, they could be destroyed after Designer's
  QApplication at quit: measured (2026-11-11), more than 20 quits of Designers on plugin v6 and later left no crash
  dump. The user's decision, 2026-11-11.
  Reopen if: a crash dump at Designer's quit points at them.

- **A quit forced during Designer's own shutdown, its close taken, passes the self-test's checks of a normal close;
  more than two in one run fail a check of their own.** Those checks are about the close (`common.closed_by_quit`);
  past it, a Designer an agent started can hang in its own shutdown (`server_tools/lifecycle.py`, its docstring's
  "Quitting."). `quit_designer` tells the two apart by the line its helper logs in Designer once every window it closed
  has closed, Designer's own among them (`QUIT_CLOSED`, `project_constants.py`), and names the last line of the log; the categories' quits and
  lifecycle's normal closes whose check reached `common.normal_close` are counted (`workers.check_the_quits`). The user's choice, 2026-11-11: this way, over
  confirming the cause first or not quitting a Designer just started; and the threshold, two hangs having been seen at
  once.
  Reopen if: that check fails, or the cause is confirmed and can be avoided (ROADMAP item 70).

- **The quit helper's line is its judgement before Designer's own quit decides: its limits are stated, not worked
  around.** A window refusing its close that shows after the helper judged, or a dialog of Designer's window refusing
  its close, makes that line wrong (`designer_helpers/quit.py`, its docstring); both were seen only with windows a
  probe made, in a Designer an agent started. Judging again once Designer's quit has had its turn would take a second
  timer, measured first against every quit case. The user's choice, 2026-11-11, of two: state the limit, or judge
  again later.
  Reopen if: a quit outside a probe is reported this way wrongly, or a script or plugin that agents use shows such a
  window.

- **No job starts sooner than 30 ms after the one before ended, whatever starts it; a call after a pause starts at
  once.** Started at once, a job found Designer not settled after the one before (measured: `WAKE_DELAY_MS` in the
  plugin). Calls one after the other take about 30 ms each instead of the poll's 85; a call after a pause doesn't wait.
  The tools' second compute stays as a defence; the `measure` check that runs one compute is what fails without the
  wait. The user's choice, 2026-11-11, of three (keep the wake and retry, remove the wake, or wait a little).
  Reopen if: the wait shows too short (that check failing), or what Designer needs the moment for is found.

- **On macOS, the server saves Designer's preferences plist as the first Designer an agent starts is started, and
  puts it back once no Designer runs.** No way to give a Designer a file of its own was found, and agents' Designers
  changed the user's (measured: `designer_preferences.py`). The user made these choices on 2026-11-13, one after the
  other. First, this is done in the server rather than only in the self-test. Then a copy left by Designers that ended
  outside the tools is put back only within 6 hours, and the file is saved again after the user's own Designer ran.
  Then a launch records the Designer it starts under the lock the file is saved under, rather than a look made only
  after a put-back. Last, a Designer that can't be recorded is ended under that lock, and one that can be neither
  recorded nor ended counts as the user's.
  Reopen if: Designer gains a way to keep its preferences elsewhere, a put-back loses a change of the user's, or
  holding the lock through the record or that end (up to about 10 s) makes launches side by side wait noticeably.

- **Designers an agent starts don't upload their crash reports to Adobe.** Designer's crash reporter uploads a crash's
  report with Designer's log, its settings and the user's Adobe account, and turns uploads on as Designer starts; a
  probe's crash was uploaded so. `launch_designer` turns them off in the Designer it started, in its own home, once it
  answers; the user's own Designer and its settings are left alone. Adobe's crash window may still open on a crash.
  How, as measured: `server_tools/lifecycle.py`, Crash reports; checked by
  `lifecycle.check_launch_on_another_port`. The user's decision, 2026-11-12.
  Reopen if: the user wants agents' crash reports sent, or Designer gains a setting of its own for it.

## Output, screenshots and Designer's UI

- **The 3D screenshot puts back only the clipboard's text; the rest may be lost.** `screenshot_designer('3d')` goes
  through the clipboard and backs it up through Qt (`designer_helpers/screenshots.py`), which on macOS kept plain
  text and HTML and lost an image, rich text's RTF and an app's own data, and made several copied files one item (measured
  2026-11-10). Putting it all back took native code running inside the user's Designer, reading
  every kind of data on the clipboard; the user doesn't mind losing their clipboard when an agent needs it, as long as
  the text comes back. The self-test's clipboard checks keep only the user's text too. README says so. The user's
  decision, 2026-11-10.
  Reopen if: the user wants the whole clipboard kept, or the text is seen not to come back.
- **After setting the 3D view's tiling or environment, the Parameters panel goes back to the graph in the editor, not
  to the node that was selected.** `screenshot_designer('3d', tiling=...)` and its environment options set them
  through the Parameters panel, then turn the panel back to the graph in the editor (how, as measured:
  `designer_helpers/view3d.py`). Turning it back to a selected node would take a click on that node in the user's
  graph view, since the API can't show a node in the panel (GUIDE.md, Designer UI). Nothing in the graph changes, and
  one click on the node shows its parameters again. The user's decision, 2026-11-12, for the tiling; widened to the
  environment at their request, 2026-11-18.
  Reopen if: the user wants the selected node back, or the API gains a way to show a node in the Parameters panel.
- **The 3D shot never sends a wheel step or a drag move again; one whose sign doesn't come within its limit ends the
  camera's moves, and the shot says which.** Designer gives no sign that it dropped one: `sendEvent` returns True and
  `isAccepted()` is False for every notch, taken or dropped, and a dropped one shows only as a sign that never comes,
  which a late one also shows until it comes (the self-test's wheel facts check; `designer_helpers/view3d.py`). A step
  sent again could then be taken twice. The lead's choice, which the user approved, 2026-11-21.
  Reopen if: Designer gains a way to tell a dropped step from a late one.
- **A 3D screenshot, and `set_3d_view` where it can't work off screen, put Designer's window on screen transparent, then
  back as it was.** The 3D view doesn't draw off screen (how the shot works around it: `_Screen`,
  `designer_helpers/shot3d.py`). The user chose a transparent, click-through window on screen over refusing the shot.
  On 2026-11-13 they first chose the window brought up visibly. On 2026-11-14, once the transparent window was
  measured, they chose it invisible in every case. If the user makes Designer the active app during the shot, it is
  left on screen if Designer is still the active app as the shot ends; switched to and away again, it is put back as
  found (the user's agreement, 2026-11-13; this wording, 2026-11-14). README once said that apps under the window might pause drawing
  them; the user had that sentence removed once it was found wrong (2026-11-14). The Explorer's menu that `graph=`
  opens is click-through too on macOS, the user's choice of 2026-11-14: whether a click would reach the menu while it
  is only transparent couldn't be measured without clicking on the user's screen (`designer_helpers/view3d.py`).
  `set_3d_view` run on its own does the same for camera moves, `graph=` and any mesh switch; otherwise only a
  viewpoint's turn runs on screen. Why: `set_3d_view`'s docstring, `designer_helpers/view3d.py`. The user chose this
  over refusing those set-ups, for the moves on 2026-11-16, and for `graph=` and any mesh switch on 2026-11-18.
  Reopen if: the user sees the window during a shot, wants it left up or the shot refused, sees an app under it pause
  during a shot, or showing it makes Designer the active app; or a way is found to run those set-ups off screen as
  they come out on screen.
- **Renaming an existing output warns; it isn't refused.** Designer updates only the graphs open during the rename. One that
  was closed computes black, with no error, and the tools can't see it. So `apply_edits`' result tells the agent to tell the
  user, naming the repair (`set_output_tags`; `GUIDE.md`, Output nodes). The user chose this over refusing a rename or only
  documenting it, 2026-11-04.
  Reopen if: the user changes the choice, or the tools become able to see the graphs a rename would break.

- **The rule against a Python event filter on the whole application has no live check.** Checking it would crash a
  Designer on purpose in every full run, and a crash can open Adobe's crash window on the user's screen. It rests on
  the measurement GUIDE.md gives (Designer UI): the crash dump's frames ran from the exit handlers through the pixmap
  cache's destructor, `~QObject` and `~QVariant` into PySide, whose clean-up threw (`recursive_mutex lock failed`), and
  `std::terminate` aborted; the same quit without the filter left no dump. The user's decision, 2026-11-12.
  Reopen if: Designer, Qt or PySide is updated (the crash may be gone, or move), or a crash dump at a quit points at a
  Python wrapper of another of Qt's long-lived objects.

## Tool annotations

- **A tool's annotations judge the user's work, not every trace a call leaves in Designer.** `readOnlyHint` marks a
  tool that leaves the user's graphs, packages and files as they were, and changes nothing else a user sees, such as
  Designer's view, the editor's current graph or the clipboard. `node_stats`, `preview_node`, `check_tiling`
  and `compare_to_reference` count, though each may add a temporary output node and remove it inside an undo step
  (Library packages, above, on the modified flag). `sweep_param` doesn't, as it leaves the package marked modified.
  `destructiveHint` marks a tool that can overwrite or remove the user's work or files; a change of Designer's view,
  of the editor's current graph, or of the clipboard's text, put back, isn't one. `idempotentHint` compares the end
  state of that work, not the undo history. `openWorldHint` is False except on `execute_designer_code` and
  `run_designer_script`: the server talks only to the local Designer, but the code they run can reach anything. Every
  tool declares all four hints, listed in `tests/unit/test_server.py`.
  The user's decision on read-only, 2026-11-21 ("go with your recommendation"); the other hints follow its reading.
  Reopen if: a client is seen acting on a hint in a way that harms the user's work, or the user changes the reading.
