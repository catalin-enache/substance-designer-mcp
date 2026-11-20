---
name: live-check
description: 'Use before writing, changing or running a live self-test check (tests/test_all_tools) or a scratch run with alone.run, for a "designer facts" check, for the final check before merging into main or when it fails, and for a Designer that crashed or hung. Covers alone.run and each category''s own preparation, the order (fail, then pass), what a scratch run can''t prove, how a scratch probe runs, a crash or a hung quit, the suites and their commands, and Designer scripts versus inline snippets.'
---

# Live checks and the suites

The hard rules (who runs tests, when the full suites run) are in `AGENTS.md`, Running the tests. The commands for
the tests of a change are in `.claude/rules/python.md` and `.claude/rules/docs-tests.md`. This is the procedure for
the live self-test, which runs against the real Designer, and the commands of the suites.

**The check lives in the suite:** a function
`async def check_<what>(ctx: Ctx)` of its category's `<category>/checks.py`, awaited by the category's `run(ctx)`; a scratch run calls
that same function, never a copy, so the check seen failing is the one committed. A check being changed moves into
such a function first (`tests/unit/test_selftest_summary.py` fails on a `check_` function its category never awaits).

**Use `alone.run`** (`tests/test_all_tools/alone.py`; its docstring has the details) from a few-line script in the
session's scratchpad, deleted afterwards, never committed:

```python
import sys

sys.path.insert(0, '<repo>/tests')
from test_all_tools import alone
from test_all_tools.params import checks as params

# the check being worked on, params.check_<what>; a whole category (params.run) works too
raise SystemExit(alone.run(params.run))
```

It opens a fresh MCP server (the session's own tools run the server as it was when the session connected: they don't
see a change to `server_tools/` or the helpers until `/mcp` reconnects), uses a Designer an agent started or starts
one, and refuses the user's (ask them to close it). It runs each category's checks as the suite does
(`category_run.py`): on a `ctx` of their own, after the category's own preparation (`<category>/preparations.py`), then
your `setup(ctx)` if the check needs more (graphs named starting `mcp_selftest`: the clean-up unloads every package
holding one), then cleans up. It keeps that Designer open for the next runs; `alone.close()` ends it, and returns 1 naming any crash dump its quit left. `port=` (`run` and `close`) runs on
a port and Designer of its own (server, `raw_request`, `sd_run`, snapshots too), so runs go side by side, except a scratch run of `lifecycle`, while no other run's Designer can start, and `facts` or `editor_panels_and_fit` beside another run of either, for the one clipboard (`alone.py`'s docstring). Exit code: 0
every check passed, 1 a check failed, 2 no environment (the user's Designer, a launch, a preparation or a setup that
failed) or no clean-up. A plugin change needs `install.py` and a restart of that Designer first (`alone.close()`, then the next run
starts one). If `alone.run` can't do what a check needs, ask the user to improve it, saying what is missing, and
meanwhile write the script from zero doing what it does: the check function itself; a fresh MCP session,
`stdio_client(common.PARAMS)` as `__main__.py` does; `get_guide` first, both parts; a Designer an agent started; graphs named
starting `mcp_selftest`, removed in a `finally` (`common.CLEAN`, then the library packages put back with
`common.library_packages` / `common.restore_library_packages`, then the self-test graph's snapshots deleted).

**The order:** run the check before the code; it must fail for the reason it is about. A failure saying only that the
tool or parameter doesn't exist yet is the expected one for something new, but shows nothing about the assertions, so
read such a check closely. A check that passes, or fails for another reason, was written wrong, unless it shows a review
finding is false (the `address-review` skill, step 2): fix it and run again. Then write the code, and run the check
again until it passes. Checks worked on together (a feature in several parts, findings addressed together) run in one
scratch script; a "designer facts" check for Designer behaviour the code relies on is written and run the same way. A
check runs on its category's preparation in the suite too, so a scratch run builds its environment there. What differs
in the full run is around it: other Designers starting, quitting and working beside it (their load, the machine's one
clipboard, Designer's shared settings), the unit suite at the same time, and a Designer just started for the category
(no graph open in the editor, so no 3D view, until its preparation opens one); the full run shows those. A check that reads something new of the graph gets it from its own category's `prepare(ctx)`: the minimum it
reads, built with tool calls and `common.py` only (`prepared_call`, `refs`), recording no check, never another
category's code (`tests/unit/test_selftest_preparations.py`). A refactor of code the self-test reaches (the helpers,
the plugin, the Designer scripts) gets a scratch run of the checks of the code it touches, before and after.

**`lifecycle` runs whole in a scratch run,** with `alone.run(lifecycle.run, own_designer=True, port=...)`: it relies
on no other category, starts from a Designer of its own (`check_a_designer_of_its_own`) and ends with none running.
Three of its checks end only a Designer they started, so they also run alone, without `own_designer`:
`check_launch_on_another_port`, `check_launch_refuses_a_port_another_program_holds` and
`check_a_designer_sharing_the_temp_folder_hands_over` (it skips unless the run's Designer was the last one started).
Its "without a crash" checks go through `crash_watch.watching_crashes` (a `CrashWatch`: one wait at the end of
`lifecycle.run`, or of the check run alone, while a dump may still come, 10 s at most, each dump given to its step by
time), never `new_crash_dumps`, which waits
after each step (`tests/unit/test_selftest_lifecycle.py` fails on it). A clean-up deleting a folder unless it holds a
dump goes in the watch's `later()`, so a dump written late isn't deleted with it.

**What a scratch run can't prove** (only the full suite runs these; changing one, say so rather than claiming it was
seen failing and passing):

- **The run's start checks** (`--first`; which category runs them: `workers.py`'s docstring): the `get_guide` checks
  (instructions' length, the refusal before it is called and the tool working after, the core and the scripting part
  returned), Designer started, and the Home screen check (no panel visible while it shows), measurable only right
  after a fresh start, since Home can't be shown again once closed.
- **What the pool's parent checks** (`workers.py`): every worker's quit and the crash dumps (`check_the_quits`), every
  tool exercised over all the workers (and which were all skipped), the `unit tests` check, Designer's preferences
  plist as before the run (`check_the_preferences`: `--only` runs it too, through the pool); and its scheduling: the
  launch lock, `CLIPBOARD`, `SOLO`.
- **In the user's Designer,** only in a run there (Windows today): their graph back in the editor, and that it still
  runs with no new crash dump.

**How a probe runs,** whoever runs it. A scratch probe is a review's, settling a suspicion that reading can't (the
`project-code-review` skill, Who settles what), or one measuring for a fix (the `address-review` skill, **All the
findings' tests first, run together**, point 4):

- **Where it runs:** a Designer an agent started (`launch_designer`), never the user's, one probe at a time in each.
  If the user's Designer is open, ask them to close it: a probe's leftovers or crash would land in their work. Close
  the agent's Designer when its work is done (GUIDE.md, the rules).
- **What it touches:** a new package of its own, with a graph name no other probe uses, unloaded at the end, never the
  user's packages; GUIDE.md's rules apply (no Undo, no hot reload of the plugin).
- **Where the code lives:** outside the repo (the session's scratchpad or a temp folder), run with
  `run_designer_script`, `execute_designer_code` or `client/sd_run.py`, and deleted afterwards. The session's own tools
  reach only the Designer on the session's port. On a port of its own, a probe runs `client/sd_run.py` with
  `SD_BRIDGE_PORT=<port>`, or goes through a fresh server on that port, as `alone.run(..., port=...)` opens. The
  session's own tools also run the server and helpers as they were when the session connected: a probe of the
  branch's changes to `server_tools/` or the helpers goes through a fresh server (an MCP session of its own, as
  `alone.py` opens) or after `/mcp` reconnects.
  `client/sd_run.py` sends only the probe's own code.
- **How it waits:** as `.claude/rules/waits.md` says, for a callback, never for a time measured here. That rule loads
  for no file in the scratchpad: read it.
- **Outside Designer,** a review's probe: a suspicion about pure-Python code that reading can't settle gets a scratch
  probe too, plain Python run from the scratchpad, with the same rules. It is not a test and is never committed: the
  agent addressing the finding writes the real test.
- **What goes in the entry,** for a review's probe: the probe in short and what it measured, in the scenario, so the
  agent addressing the finding can start its test from it.

**When the final check fails,** each failure goes in `REVIEW.md` (the user, 2026-11-19). The runner reports the
failures, the lead writes each one, as a new finding or a reopened one (the `address-review` skill, step 4), and the
developer fixes them. The developer reruns only the failing tests until they pass: unit tests by name (the summary lists
them) with lint and types; a live check in a scratch run (failing only in the full run: run it beside other Designers, with
`port=`, or in a Designer just started, `alone.close()` first). Then the lead tells the user which suites failed, and
recommends another review or those suites again, by the size of the fixes. The user decides. When only unit
tests failed, the live self-test needs to run again only if the fixes touch code it reaches, a comment or a docstring
included (`mcp_server/` (not GUIDE.md alone, which is docs: `.claude/rules/docs-tests.md`), `plugin/`,
`client/`, `examples/`, `tests/test_all_tools/`, `project_constants.py`, `designer_preferences.py`): its pass was for the code as it was, so the
lead tells the user it must run again. Fixes only elsewhere (`tests/unit/`, `install.py`, `uninstall.py`, `scripts/`, the tool
configs) need only the unit suite again.

**When a Designer crashed or hung:** a crash leaves a dump in that Designer's `Sentry-Crashpad/completed` (`pending`
while its upload waits; GUIDE.md, Several Designers). `python3 scripts/read_crash_dump.py [dump]` reads one (macOS
arm64; with no dump, the newest of any Designer's): the exception, the messages Crashpad kept (often an abort's
reason), the crashing thread's frames and Designer's log as it crashed. A crash can also open Adobe's crash window
on the user's screen and keep the crashed process until the window closes (ROADMAP item 95): close it for a Designer
an agent started. A Designer hung in its quit has its threads sampled before it is forced (macOS: `quit_designer`'s
or `launch_designer`'s result names the file; ROADMAP item 70). `alone.close()` names any dump its quit left.
On macOS, Designers an agent starts upload no crash reports from the moment `launch_designer` sees them answer
(DECISIONS.md, Bridge and quitting).

**The suites.** They run only when the user asks (AGENTS.md, Running the tests). Which command for what the user
asks:

- **Both suites** (the final check included, but for docs changed alone: `.claude/rules/docs-tests.md`):
  `mcp_server/venv/bin/python tests/test_all_tools`. On macOS it runs every category in a Designer of its own, several
  at once (`--workers N`; the pool's rules: `tests/test_all_tools/workers.py`), with the whole unit suite beside them:
  one command for both. With a Designer of the user's open it runs nothing and says so: ask them to save and close it.
  On Windows it makes one run instead, leaving the unit suite out: run `pytest` at the same time, as a background
  command.
- **The unit suite alone:** `mcp_server/venv/bin/python -m pytest`.
- **The live suite alone:** `mcp_server/venv/bin/python tests/test_all_tools --no-unit`.
- **Chosen categories** (macOS): `mcp_server/venv/bin/python tests/test_all_tools --only <category>...`, through the
  pool with its safety checks, without the unit suite; not a final check.

What each suite is:

- `mcp_server/venv/bin/python -m pytest`: unit tests, no Designer, about a minute (`pip install -r
  mcp_server/requirements-dev.txt` once). `test_types.py` runs mypy strict (`mypy.ini`) over every Python file:
  annotate everything. (The typing rules: `.claude/rules/python.md`.) `sd`'s modules star-import each
  other in cycles, so in the whole-repo run some sd return types come out `Any` (`no-any-return`): annotate the local
  (`node: SDNode = g.newNode(...)`). The formatter can move a trailing
  `# type: ignore` or `# noqa` off its line when it rewraps a statement (mypy then reports it): put it back.
- `mcp_server/venv/bin/python tests/test_all_tools`: every tool over MCP against the real Designer
  (the pool: `tests/test_all_tools/workers.py`). How it runs, and which command for what the user
  asks: above.
  Its "designer facts" checks re-measure the Designer behaviour GUIDE.md or a module's docstring
  states: add one with each new fact. One folder per category (`bridge/`, `params/`, `render/`...: its `run(ctx)` and checks in
  `checks.py`, the `prepare(ctx)` building what they read in `preparations.py`, the Designer scripts only it runs in
  `designer_scripts/`), shared helpers and snippets in `common.py`, and the index `__main__.py`, which runs the
  categories in `categories.py`'s order. None reads what another made: each runs on a `ctx` of its own, after its own
  preparation, and is cleaned up after it (`category_run.py`). Add a check to the category it belongs to (a `check_`
  function, above); a new category is a folder with an `__init__.py`, a `checks.py` holding its `async def run(ctx)` and,
  if its checks read a graph, a `preparations.py`; imported in `categories.py` and added to `CATEGORIES`, in its place by its time.
  - **Python with real logic that runs inside Designer** (more than a handful of lines, imports and the graph lookup
    included, or Qt code that gains from type checks), or that several categories run, goes in `<category>/designer_scripts/`
    (`designer_scripts/shared/` for several), as a real file run with `common.designer_script` (`'<category>/<script>'`,
    `'shared/<script>'`) (`run_designer_script`, its values in
    `args`), so ruff and mypy check it; a script that raises fails the run. A shorter probe stays inline where the check
    reads it, as do snippets needing the helpers' text (`helpers_source()`: `run_designer_script` doesn't send them),
    strings that are what the test is about (`execute_designer_code`, its undo step and abort, the bridge, the plugin's
    unit tests), and `common.py`'s clean-up and undo snippets, which guard the user's session. Strings of code:
    `.claude/rules/python.md`.
  - A snippet that loads one of Designer's library packages stays inline, in a branch that runs only where the
    self-test started Designer (the `else` of `if was_running:`, or `if not was_running:`), never in a script: the unit
    test can't see a branch in another file, so it fails on a script naming both `loadUserPackage` and
    `DefaultResourcesDir`. (A library path passed in through `ARGS` goes unseen: don't.)
