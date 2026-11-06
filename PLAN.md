# PLAN.md: faster test runs

**Goal:** a full test pass (unit tests plus the live self-test) takes about 12 minutes today, which is longer than
the development it checks. This plan brings a full pass down to about 5.5 minutes, without losing any check. The full
pass runs only when the user asks, the final check before merging included (decision 2); while working, only the
tests added or modified run, a live check on its own with `alone.run` (AGENTS.md, Running the tests).

**In short:** split the live self-test across several Designers running at once (no check is lost, every branch
gains), make the categories' dependencies on each other explicit (needed for that split), remove fixed waits, and
optionally add per-branch selection of the tests to run while working (step 4); the final check stays a full pass.

Everything below was measured on 2026-11-05 on macOS (10 cores, 64 GB, Designer 16), unless it says *estimate*.

---

## 1. Where the time goes today

### Whole run

| Part | Time |
|---|---:|
| Unit tests (`mcp_server/venv/bin/python -m pytest`) | 67 s |
| Live self-test (`mcp_server/venv/bin/python tests/test_all_tools`, Designer started by the test) | 655 s (10.9 min), 500/500 checks |
| **Total, run one after the other** | **about 12 min** |

The unit tests are not the problem: the slowest are mypy (two runs, about 8 s together) and a few tests of the
plugin's abort handling and of `quit_designer` that wait on real timers (1–3 s each).

### Live self-test, per category

| Category | Time | Share | What takes the time |
|---|---:|---:|---|
| `lifecycle` | 178 s | 27% | 8 launches (6.4 s each, 51 s), 9 `quit_designer` calls (55 s), **69 s of fixed sleeps** (below) |
| `facts` | 96 s | 15% | one script, `facts/function_states`, takes 60 s |
| `safeguards` | 79 s | 12% | spread out; the largest is an 11 s export of a library graph |
| `example` | 46 s | 7% | building the 2048 trim sheet and exporting it |
| `render` | 43 s | 7% | spread over exports, `.sbsar` renders and seed checks |
| `inputs` | 34 s | 5% | 18 `remove_graph_input` and 18 `apply_edits` calls, among others |
| `link_display` | 23 s | 4% | save, edit, reload per call |
| `graph_edit.wire` | 22 s | 3% | 16 s of it is the timeout check with finalizers and Qt slots |
| 15 other categories | 117 s | 18% | 0.3–19 s each |
| Start before the first category, clean-up at the end | 16 s | 2% | restoring the library packages takes about 9 s |

### What that shows

- **Launching Designer is not the slow part.** A start takes 6.4 s. In `lifecycle` the larger cost is
  `new_crash_dumps()` (`tests/test_all_tools/common.py`), which waits its full 10 s after each of the 6 quits even
  when no dump appears: 60 s of the 69 s of sleeps.
- **Calls are cheap, but there are many.** 838 tool calls, median 0.2 s, 70% under 0.25 s. The plugin picks up jobs
  on a 100 ms timer (`self.timer.start(100)` in the plugin), so each call waits about 50 ms on average for its turn:
  *estimate* about 40 s per run. Not measured directly.
- **By tool:** `run_designer_script` 125 s (95 calls), `execute_designer_code` 68 s (100), `launch_designer`
  58 s (9), `quit_designer` 55 s (9), `apply_edits` 42 s (223), `export_outputs` 31 s (11).

---

## 2. Can the live tests run in parallel? Yes

### Several Designers side by side

Three Designers started at once, each from the binary inside the app
(`.../Adobe Substance 3D Designer.app/Contents/MacOS/Adobe Substance 3D Designer`) with its own `SD_BRIDGE_PORT`
(9901, 9902, 9903). Each answered on its own port from its own process within 7.5 s.

`launch_designer` can't do this: it uses `open -a`, which brings an already running Designer to the front
instead of starting another.

| 5 computes of a 40-blur graph at 2048 | Each | All three |
|---|---:|---:|
| One after the other | 8.1–8.8 s | 25 s |
| At the same time | 9.9–12.4 s | 12.4 s |

That is the worst case (pure compute): about twice the throughput with three. Memory after that probe was about
11 GB per instance; after a full self-test run it was about 1.9 GB per instance (the peak during a run was not
measured).

### The self-test on three Designers at once

The same 22 categories (all but `lifecycle`), once in each of the three, at the same time:

| | Wall time | Checks |
|---|---:|---|
| One Designer (the run above) | 460 s | all passed |
| Three Designers, all three running everything | 468 s | 1,355 / 1,356 |

So the self-test barely slows down at all when three run together: it mostly waits on Designer's main thread, not on
the CPU. The one failure was `designer facts: exposing an input logs the documented harmless messages` (counts
before `[71, 23]`, after `[70, 24]`), in one of the three: all instances write one log, so a count taken from it
can be thrown off by another instance. This is very likely the cause, but not proven.

### Split into shards

The categories split across the three, each shard in its original order:

| Shard | Categories | Time | Checks |
|---|---|---:|---|
| A | `bridge`, `discovery`, `graph_edit.create`, `params`, `graph_edit.output_fields`, `graph_edit.wire`, `measure`, `batch`, `inputs`, `layout`, `editor.open_and_zoom`, `undo`, `editor.panels_and_fit` | 171 s | 241 / 241 |
| B | `graph_edit.create`, `bitmaps`, `facts`, `lookup`, `example`, `script_runner` | 161 s | 118 / 121 |
| C | `graph_edit.create`, `bitmaps`, `save`, `safeguards`, `link_display`, `render` | 96 s | 88 / 101, stopped early |
| **Wall time** | | **171 s** (against 460 s) | |

B and C failed on **hidden dependencies**: state an earlier category leaves in the shared graph, which `Ctx` doesn't
show.

- **`facts`:** `facts/api_basics` reads the connection into `levels`' `input1`, made by `graph_edit.wire`
  (`SDApiError.IndexOutOfBounds` without it). `facts/embed_and_parent_size` failed too
  (`SDApiError.InvalidArgument`), and its missing state hasn't been pinned down.
- **`render`:** it expects the output node to be named `height`, which `graph_edit.wire` does (`graph_edit.py:327`).
  Without it, the export wrote `output.png`, and the run stopped at a `FileNotFoundError` after 9 of `render`'s 42
  checks. `link_display` failed its 4 changes too (0 links selected).

So 171 s is too low. With those dependencies supplied and `render` finishing, the *estimate* is about 3–3.5 min for
the live tests other than `lifecycle`.

Two smaller findings from these runs:

- **Environment:** the MCP client's `stdio_client` passes the server only a minimal environment when
  `StdioServerParameters.env` is not set. `SD_BRIDGE_PORT` reached the server only after `PARAMS.env` was set
  explicitly.
- **Library checks skipped:** a run in a Designer it didn't start (`was_running`) skips the checks that load library
  packages (2 in `safeguards`) and the Home screen check. Workers must count as started by the test, or those checks
  are lost.

---

## 3. The plan

Five steps, 0 to 4, in this order. Steps 1 and 2 give most of the gain. Step 4 depends on step 1 but not on step 2.

Each step starts with its tests (the **Tests** of each step below): written first and seen failing, then the code
(AGENTS.md, "Start with the tests, always"). A step's **Live** test that is a run of the whole suite, or of every
category, waits for the user to ask for it, as every full run does (AGENTS.md, Running the tests).

### Step 0: time every run (S)

**What:** the self-test prints each category's time in its summary, and writes the times next to the results.

**Why:** the measurements above came from a wrapper outside the repo, and will go stale. With the times in every
run, a slowdown shows up in the change that caused it, and the shard balance in step 2 can use real numbers.

**Tests:** a unit test of the summary (`tests/unit/test_selftest_summary.py`) with times in it.

### Step 1: explicit dependencies between categories (M)

**One list of dependencies, starting from `alone.py`.** `tests/test_all_tools/alone.py` already runs chosen checks on
their own, and its `NEEDS` already declares which setup steps rely on which. This step grows that into the categories'
declarations below, kept in one place that both `alone.run` and the index read, rather than a second list, and its
scope shrinks to the declarations step 2 needs: with the full suite run only
when the user asks, and `alone.run` rerunning failing checks on their own, `--only` and `--failed` matter less, and
`--isolate` can already be done with `alone.run`.

**What:**
- **Requirements:** each category declares what it needs, as categories to run first (for example `render` needs
  `graph_edit.create`, `graph_edit.wire`, `bitmaps` and `save`). The index (`tests/test_all_tools/__main__.py`)
  adds the requirements of the categories asked for, keeping the order of `CATEGORIES`.
- **Known requirements so far:**
  - `graph_edit.create` (the graph `G` and its nodes `clouds`, `slope`, `lv`, `out`): almost every category.
  - `params` (the parameters its checks leave, such as `Samples = 16`): `graph_edit.wire` (measured: run straight
    after `graph_edit.create`, its "links + params" check failed).
  - `graph_edit.wire`: `facts` (the connection into `levels`), `render` (the output named `height`), `inputs`
    (measured: without the connection into `levels`, two of its checks saw an output that didn't change), probably
    `link_display`.
  - `bitmaps` (`ctx.png`): `facts`, `lookup`, `save`.
  - `save` (`ctx.sbs`, `ctx.stats_before`): `render`, `link_display`.
  - None: `bridge`, `discovery`, `example`, `script_runner`, `lifecycle`.
  - Measured with `alone.run` (2026-11-06): `params` passes on `graph_edit.create` alone; `batch`, `inputs`, `layout`
    and `facts`, run in that order, pass on `create`, `params`, `wire` and `bitmaps`.
- **Finding the rest:** run each category alone with its declared requirements, once, as a check of the declarations:
  `alone.run` does this today, one category at a time (an `--isolate` mode would do it for every category in one go).
  With step 2 these runs take a few minutes together.
- **Later, optional:** if running `graph_edit.wire` as a requirement costs too much (22 s), a setup step that builds
  the same graph state directly, without the wire checks.
- **Later, optional, if the user wants them:** `--only <categories>`, running just those plus what they require, in the
  suite's own order, its summary counting only the tools those categories call; and `--failed`, rerunning the
  categories that had a failing check. A failing live check reruns on its own with `alone.run` today (AGENTS.md,
  Running the tests), so neither is needed for the rules.

**Why:**
- **Both other steps need it:** parallel shards (step 2) and per-branch selection (step 4) both run a subset of the
  categories, and the shard runs above showed that a subset fails today.
- **Better tests anyway:** a category's checks then rely only on what is declared, not on whatever earlier
  categories happened to leave behind.

**Tests:**
- **Unit test, declarations:** each category's declared requirements cover the `ctx.` attributes it reads (they can
  be found from the source, as in the measurements).
- **Unit test, the one list:** `alone.run`'s needs and the index read the same declarations.
- **Live:** every category passes alone with its declared requirements (`alone.run`, a category at a time), in runs
  the user asks for, since together they amount to a full run.

### Step 2: the live self-test on several Designers at once (L)

**What:**
- **Workers:** when no Designer is running, the self-test starts N Designers (default 3, `--workers N`; `--workers 1`
  is today's run) from the binary, each with its own free port (from 9901 up, checked before use), its own MCP
  server (with `SD_BRIDGE_PORT` passed through `PARAMS.env`), its own `SD_SNAPSHOT_DIR` and its own scratch folder.
- **Shards:** the categories are split into N shards. Each shard is a list of categories plus their requirements
  (step 1), balanced by the times from step 0, so the slowest shard sets the wall time.
- **Results:** each worker writes its checks, skips and times to a file. The index merges them and prints one
  summary, in which tool coverage is the union over all shards.
- **A serial stage after the shards:** first the workers are closed (asked to close through the bridge, then
  SIGTERM to their own recorded process IDs only, as `end_own_designer` does). Then, with no other Designer
  running:
  - `lifecycle`: its checks look for any Designer process (`pgrep`), and `launch_designer` uses `open -a`.
  - The checks that count lines in Designer's log (`read_designer_log`, the harmless-messages fact). The log is
    shared, so another instance can throw the counts off.
- **Workers count as started by the test**, per worker, so the checks that load library packages and the Home screen
  check run.
- **The unit tests run at the same time as the live shards:** they don't use Designer.
- **When the user's Designer is open,** the self-test keeps today's behaviour: one run, in that Designer, nothing
  quit. Running workers next to the user's Designer hasn't been tried (the port, the shared settings files).

**Why:**
- **No check is lost:** unlike selection, every check still runs, so no bug can slip through.
- **Every branch gains:** this includes the large branches that selection would send to a full run anyway. Recent
  branches changed 13–93 files.
- **Measured, not guessed:** three runs at once took the time of one (468 s against 460 s), and the split ran in
  171 s against 460 s.

**Expected:** about 3.5 min for the shards, then about 2 min for `lifecycle` after step 3: about 5.5 min for a full
pass, against 12 today (*estimate*).

**Tests:**
- **Unit tests:** the shard planner (every category runs exactly once, requirements are included in order, the
  shards are balanced), merging results, choosing free ports, and passing the environment to each worker's server.
- **Live:** the self-test itself, with `--workers 3` and with `--workers 1`.

**Docs:**
- **AGENTS.md, "Running the tests":** the new options, what runs in the serial stage and why.
- **README.md, How it works:** the workers.
- **AGENTS.md, Environment facts:** that several Designers run side by side with their own `SD_BRIDGE_PORT`, but
  share the log, the crash dump folder, the temp folder and the settings files. Backed by a "designer facts" check,
  as with every fact there.

### Step 3: remove fixed waits (S–M)

**What and why, largest first:**
- **Crash-dump wait in `lifecycle` (saves about 50 s):** instead of waiting 10 s after each of the 6 quits, note the
  time of each step, wait once at the end of `lifecycle`, and assign any new dump to the step whose time window
  holds its modification time.
  - **Caveat:** the crash checks have a history (REVIEW.md TST-16, TST-21, TST-43, ROADMAP item 26), so the
    change keeps "a dump that appears late still counts". The final wait stays 10 s.
- **`facts/function_states` (up to about 50 s, unknown):** it takes 60 s, because nested loops over parameter kinds,
  function-graph states and inheritance call `compute()` each time. First profile it, then try a smaller graph
  size or fewer computes, with the same rows of the table in AGENTS.md checked.
- **The plugin's 100 ms poll timer (about 40 s, *estimate*):** measure first. Then try a shorter interval, or
  waking the main thread when a job arrives, after checking Designer's idle CPU use.
  - **Users gain too:** every tool call for real users would be faster.
  - **Cost:** it's a plugin change, so it needs `install.py` and a Designer restart.
- **pytest-xdist for the unit tests (optional):** with step 2 the unit tests run during the live shards, so this
  matters only for a run of the unit tests alone. Keep it only if every test passes unchanged in parallel.

**Tests:**
- **Unit test, crash dumps:** assigning dumps to steps by time, including a dump that appears after the last step.
- **Live:** the `lifecycle` checks, unchanged.

### Step 4: run only what a branch touches (M)

Optional (decision 2): for the runs while working, if the user adopts it; the final check stays a full pass.

**What:**
- **The script:** `scripts/select_tests.py` lists the files changed against `main` (`git diff main...HEAD`, plus
  uncommitted changes) and maps them to unit test files and self-test categories. Requirements come from step 1,
  and the categories can run on the workers of step 2.
- **The map:** in the repo, from file patterns to tests. For example:
  - `mcp_server/server_tools/lifecycle.py` and `mcp_server/designer_helpers/quit.py` →
    `tests/unit/test_lifecycle_env.py` and the `lifecycle` category.
  - `tests/test_all_tools/designer_scripts/<module>/` → that module's category (the folder is already named after
    it).
- **A full run for anything shared:** `plugin/`, `project_constants.py`, `mcp_server/server_tools/core.py`,
  `mcp_server/designer_helpers/core.py`, `tests/test_all_tools/common.py` and `tests/test_all_tools/__main__.py`.
- **A full run for any file the map doesn't name:** a gap in the map costs time, never a missed bug.
- **Always run:** ruff and mypy (`test_lint.py`, `test_types.py`) and the tests that read the sources as text
  (`test_server.py`'s coverage checks, `test_selftest_safety.py`).
- **Docs only:** the four doc tests that `AGENTS.md` already lists.
- **Entry point:** `tests/test_all_tools --changed` (and the same for the unit tests) runs the selection.

**Why a script, not a framework:** the pytest plugins that select tests don't fit this repo.
- **pytest-testmon** follows coverage, which misses three things here:
  - the helpers, which run as one joined script under a made-up file name (`<sd_claude_bridge_kve>`);
  - the tests that read files as text;
  - code that runs inside Designer.
- **pytest-impacted and pytest-impact** follow imports, with the same blind spots.
- **None of them** reach the live self-test, which isn't a pytest suite.
- **The unit tests alone** take only 67 s, so selecting among them saves less than a minute.

**Why:** while working, a branch that changes one area gets its related tests in about 1–3 min (*estimate*: about 1 min for a `sweep_param` change,
about 2 min for a rendering change, about 3 min for one in quitting or launching).

**Tests:**
- **Unit test, the map:** every file tracked by git is matched by a pattern or listed as "full run", so the map
  can't quietly go out of date.
- **Unit test, the selection:** example diffs give the expected tests, and an unknown file gives the full run.

**Docs:**
- **AGENTS.md, "Running the tests":** when to use `--changed`.
- **The `address-review` skill, step 4:** `--changed` instead of naming the tests by hand, once the user adopts it.

---

## 4. Expected result (*estimate*)

| | Now | After |
|---|---:|---:|
| Live tests other than `lifecycle` | about 8 min | about 3.5 min (step 2) |
| `lifecycle`, run alone | 3 min | about 2 min (step 3) |
| Unit tests | 1 min | none extra (run alongside, step 2) |
| **Full pass** | **12 min** | **about 5.5 min** |
| Related tests while working, a branch changing one area | not run today | about 1–3 min (step 4, optional) |
| The final check, any branch | 12 min | about 5.5 min (a full pass) |

---

## 5. Risks and open questions

- **Shared settings:** every Designer writes `user_preferences.xml`, `com.adobe.Adobe Substance 3D Designer.plist`
  and the files in `16.0/databases/` (`~/Library/Application Support/Adobe/Adobe Substance 3D Designer/`), and the
  last one to quit wins. A single run already rewrites them. No crash was seen with three, but damage from writes at
  the same time wasn't checked.
- **Hidden dependencies:** step 1's runs of each category alone are what find them. Until it passes for every category, a
  sharded run can fail on state, as B and C did.
- **Next to the user's Designer:** not tried. The plan keeps today's single run when one is open.
- **Windows:** measured on macOS only. On Windows no Designer counts as an agent's yet (ROADMAP item 18), so the
  workers may need the same handling.
- **Memory:** 1.9 GB per instance after a run, 11 GB after a heavy compute. More than 3 workers needs a look at the
  peak.
- **More workers:** only 3 were measured. `facts` alone takes 80–96 s, so beyond about 4 workers the wall time stops
  falling unless `facts` is split.

## 6. Decisions for the user

1. **Order of the steps:** the recommendation is 0, 1, 2, 3, 4 (parallel before selection, since it loses no check
   and helps every branch).
2. **When a full run is required: decided (the user, 2026-11-06).** The full suites run only when the user asks,
   the final check before merging into `main` included. While working, only the tests added or modified run, always
   with lint and types: unit tests by name, and a live check by calling its function (in the suite, called from its
   category's `run(ctx)`) from a scratch script, in an environment the agent builds for it (AGENTS.md, Running the
   tests; DECISIONS.md, Project rules). What this changes in the plan:
   - **Step 1 matters less:** a check is already seen failing and passing on its own, with `alone.run`, which builds
     the suite's own setup steps. `--only` would add the categories that run in between, and so show the cases where
     a check behaves differently after them.
   - **Step 2 still matters:** it is what makes each full run the user asks for take 5.5 min instead of 12.
   - **Step 4 becomes optional:** it would add the tests related to the changed files, not only the ones added or
     modified. That catches a break before the full run, at the cost of more time while working. Adopting it changes
     the rule, so it waits for the user; it never replaces the final check, which stays a full pass.
3. **This file:** `AGENTS.md` puts work still to do in ROADMAP.md. Should the steps become ROADMAP items once
   agreed, with this file deleted after, or should it stay for the length of this work?

## Appendix: how the measurements were made

- **Timing:** a wrapper outside the repo imported the self-test's index and wrapped:
  - each entry of `CATEGORIES` and `lifecycle.run`, with a timer;
  - `ClientSession.call_tool`, for each tool call's time;
  - `time.sleep` and `asyncio.sleep`, for the fixed waits;
  - stdout, with a time stamp per line, for each check's time.

  The run itself was unchanged. Step 0 replaces this wrapper.
- **Several Designers:** a script started three from the binary with `SD_BRIDGE_PORT` set, waited for each port to
  answer, compared `os.getpid()` inside Designer with the process it started, and timed the compute probe one after
  the other and at the same time. The self-test then ran three times in parallel (each through the wrapper, with its
  own port, `SD_SNAPSHOT_DIR` and `PARAMS.env`), then as the three shards. Afterwards the three Designers were asked
  to close through the bridge: all closed by themselves, with no crash dump.
