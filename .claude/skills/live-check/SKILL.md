---
name: live-check
description: 'Use before writing, changing or running a live self-test check (tests/test_all_tools) or a scratch run with alone.run, for a "designer facts" check, and for the final check before merging into main or when it fails. Covers alone.run and its needs, the order (fail, then pass), what a scratch run can''t prove, the suites, and Designer scripts versus inline snippets.'
---

# Live checks and the suites

The hard rules (who runs tests, when the full suites run, the unit, lint, types and docs-only commands) are in
`AGENTS.md`, Running the tests. This is the procedure for the live self-test, which runs against the real Designer.

**The check lives in the suite:** a function
`async def check_<what>(ctx: Ctx)` of its category's module, awaited by the category's `run(ctx)`; a scratch run calls
that same function, never a copy, so the check seen failing is the one committed. A check being changed moves into
such a function first (`tests/unit/test_selftest_summary.py` fails on a `check_` function its module never awaits).

**Use `alone.run`** (`tests/test_all_tools/alone.py`; its docstring has the details) from a few-line script in the
session's scratchpad, deleted afterwards, never committed:

```python
import sys

sys.path.insert(0, '<repo>/tests')
from test_all_tools import alone, params

# the check being worked on, params.check_<what>; a whole category (params.run) works too
raise SystemExit(alone.run(params.run, needs=['graph']))
```

It opens a fresh MCP server (the session's own tools run the server as it was when the session connected: they don't
see a change to `server_tools/` or the helpers until `/mcp` reconnects), uses a Designer an agent started or starts
one, and refuses the user's (ask them to close it). It builds the environment with the suite's own setup steps
(`needs`: `graph`, `params`, `wired`, `png`, `sbs`, each with those it relies on), then your `setup(ctx)` if the check
needs more (graphs named starting `mcp_selftest`: the clean-up unloads every package holding one), calls the checks and
cleans up. It keeps that Designer open for the next runs; `alone.close()` ends it. `port=` (`run` and `close`) runs on
a port and Designer of its own (server, `raw_request`, `sd_run`, snapshots too), so runs go side by side. Exit code: 0
every check passed, 1 a check failed, 2 no environment (the user's Designer, a launch or a setup that failed) or no
clean-up. A plugin change needs `install.py` and a restart of that Designer first (`alone.close()`, then the next run
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
scratch run proves a check in its own environment, not after the earlier categories of the suite have changed the graph:
only the full run shows that. A refactor of code the self-test reaches (the helpers, the plugin, the Designer scripts)
gets a scratch run of the checks of the code it touches, before and after. A new check in a setup step's category
(`graph_edit.create`, `params`, `graph_edit.wire`, `bitmaps`, `save`) runs inside every need built on that step: while
it still fails, those needs fail to build (exit code 2), so the other checks run on them aren't seen failing for their
own reason. Run such a check on the needs before its category, and the rest of the group in a script of its own.

**What a scratch run can't prove** (only the full suite runs these; changing one, say so rather than claiming it was
seen failing and passing):

- **`lifecycle.py`, the whole category:** it quits and relaunches Designer (a normal quit, a forced one, a stuck
  shutdown, a frozen main thread, a slow quit), checks for crash dumps after each, and checks the record of the Designer
  an agent started; a quit ends the session a scratch run keeps open. Three of its checks end only a Designer they
  started, so they do run alone: `check_launch_on_another_port`, `check_launch_refuses_a_port_another_program_holds`
  (it refuses at once and quits only a Designer it started), and `check_a_designer_sharing_the_temp_folder_hands_over`
  (it skips unless the run's Designer was the last one started: run it first).
- **`__main__.py` at the start of the run:** the `get_guide` checks (instructions' length, the refusal before it is called and the tool
  working after, the core and the scripting part returned), whether Designer was started or already running,
  and the Home screen check (no panel visible while it shows), measurable only right after a fresh start, since Home
  can't be shown again once closed.
- **`__main__.py` at the end:** every tool exercised (and which were all skipped), the user's graph back in the editor,
  and, in a Designer that was already running, that it still runs with no new crash dump.

**When the final check fails,** rerun only the failing tests until they pass: unit tests by name (the summary lists
them) with lint and types; a live check in a scratch run (failing only in the suite: build the state the earlier
categories left into its environment). Then tell the user which suites failed; they ask for those again. When only unit
tests failed, the live self-test needs to run again only if the fixes touch code it reaches (`mcp_server/` (not GUIDE.md alone, which is docs: AGENTS.md, Running the tests), `plugin/`,
`client/`, `examples/`, `tests/test_all_tools/`, `project_constants.py`): its pass was for the code as it was, so tell
the user it must run again. Fixes only elsewhere (`tests/unit/`, `install.py`, `uninstall.py`, `scripts/`, the tool
configs) need only the unit suite again.

**The suites.**

- `mcp_server/venv/bin/python -m pytest`: unit tests, no Designer, about a minute (`pip install -r
  mcp_server/requirements-dev.txt` once). `test_types.py` runs mypy strict (`mypy.ini`) over every Python file:
  annotate everything. (The typing rules: AGENTS.md, Running the tests.) `sd`'s modules star-import each
  other in cycles, so in the whole-repo run some sd return types come out `Any` (`no-any-return`): annotate the local
  (`node: SDNode = g.newNode(...)`). The formatter can move a trailing
  `# type: ignore` or `# noqa` off its line when it rewraps a statement (mypy then reports it): put it back.
- `mcp_server/venv/bin/python tests/test_all_tools`: every tool over MCP against the real Designer, about 11 minutes
  when it starts Designer itself. It starts Designer if none runs and closes it again; one already running stays open,
  and the checks that quit Designer are skipped. Its "designer facts" checks re-measure the Designer behaviour GUIDE.md or a module's docstring
  states: add one with each new fact. One module per category (`bridge.py`, `params.py`, `render.py`...), shared helpers
  and snippets in `common.py`, and the index `__main__.py`, which runs the categories in its `CATEGORIES` order. They
  share one graph; what an earlier category made (the graph `G`, node ids, the saved `.sbs`) reaches later ones through
  `ctx`. Add a check to the category it belongs to (a `check_` function, above); a new category is a module with an
  `async def run(ctx)` added to `CATEGORIES`.
  - **Python with real logic that runs inside Designer** (more than a handful of lines, imports and the graph lookup
    included, or Qt code that gains from type checks), or that several modules run, goes in `designer_scripts/<module>/`
    (`shared/` for several), as a real file run with `common.designer_script` (`run_designer_script`, its values in
    `args`), so ruff and mypy check it; a script that raises fails the run. A shorter probe stays inline where the check
    reads it, as do snippets needing the helpers' text (`helpers_source()`: `run_designer_script` doesn't send them),
    strings that are what the test is about (`execute_designer_code`, its undo step and abort, the bridge, the plugin's
    unit tests), and `common.py`'s clean-up and undo snippets, which guard the user's session. Strings of code: AGENTS.md,
    Running the tests.
  - A snippet that loads one of Designer's library packages stays inline, in a branch that runs only where the
    self-test started Designer (the `else` of `if was_running:`, or `if not was_running:`), never in a script: the unit
    test can't see a branch in another file, so it fails on a script naming both `loadUserPackage` and
    `DefaultResourcesDir`. (A library path passed in through `ARGS` goes unseen: don't.)
