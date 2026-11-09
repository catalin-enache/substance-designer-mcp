# AGENTS.md: changing this project

For AI agents working on this repository. Driving Substance Designer (the tools, the rules that protect the user's
work, the `sd` API and Designer facts) is in [mcp_server/GUIDE.md](mcp_server/GUIDE.md): `get_guide()` serves its core, `get_guide('scripting')` the `sd` API part.
Read its rules before touching the bridge, the token or the plugin, or running anything against Designer, and its
scripting part before writing code that runs inside Designer.

Commit or push only when the user asks; the repository is public. **There is no CI and none is planned**: don't add
GitHub Actions or other CI.

## Working on this project

How the plugin, server, helpers and command-line tools fit together: README.md, **How it works**.

**Load the `mcp-builder` skill** (`.claude/skills/mcp-builder/`: Anthropic's, from `anthropics/skills` at `ca45fc4`,
trimmed to its Python parts) before designing or changing tools (adding, merging or removing one, its parameters,
description, errors or results), and for evaluations. Where it differs from this file, this file wins. Its defaults this
project doesn't follow: comprehensive API coverage and service-prefixed names (few tools, unprefixed; node edits are
`apply_edits` ops; a new capability is a parameter or op of an existing tool where it fits, else a new tool rather than
an existing one complicated with completely different logic: ROADMAP.md "Fewer tools"); JSON results (they are compact
text for agents); Pydantic input models (inputs are typed parameters). Its code is for mcp 1.x; this server runs mcp
2.x (the note at the top of its `SKILL.md`).

The server (`server_tools/core.py`) loads the guide from `mcp_server/GUIDE.md`: keep it there. Its
instructions (`INSTRUCTIONS` in `server_tools/core.py`) must stay under 4,096 characters, and every tool but
`cancel_designer_job` refuses to run until `get_guide()` has been called in the session, and the two code tools until
`get_guide('scripting')` has too (unit tests check them).

**Every new feature or fix comes with a test, in the same change.** A tool, a parameter or a documented behaviour gets
a check in the live self-test (`tests/test_all_tools/`, against the real Designer); pure-Python logic gets a unit test
in `tests/unit`. A claim in these docs without a test is a guess: test it or remove it. The unit tests fail when a tool
or a tool parameter is never exercised by the self-test, when an `apply_edits` op or an op's field is never passed in
one (run or not), or when a tool is missing from README's Tools table.

**Start with the tests, always (TDD).** Before implementing anything (a tool, a parameter, an op, a helper, a script, a
change in behaviour) or fixing an issue, write the tests that describe what it must do or reproduce the issue, run them
and watch them fail; only then write the code, until they pass. A test written after the code tends to check what the
code happens to do, and one never seen failing may not test anything. For anything that depends on Designer, add a live
check too, seen failing and passing in a scratch run (the `live-check` skill), since a unit test may take a path Designer
never does. Before a fix that depends on Designer's behaviour, measure every case the code distinguishes, and fix the
pattern everywhere it occurs, not just the reported instance (the `address-review` skill, step 3). If the test passes
before any fix, either the issue isn't real or the test can't see it: read the test against the issue to tell which; fix
a blind test and run it again before any fix, and say an issue that isn't real is so rather than "fixing" it. Code that
changes no behaviour (a rename, a move) needs no new failing test: run the existing tests of the code it touches before
and after; they must pass both times.

**Review your own work before calling it done**, as a reviewer, not its author: does it cover the neighbouring cases (a
node as well as the graph, the other parameter, the other code path); would each test fail without the change it guards
(not pass on state an earlier check left, a value already there, or a comparison any rule satisfies); does every test
clean up on failure too; did the change weaken an older test; does any comment, docstring or doc say more than the code
and tests show? Fix what you find and look again, until a fresh look finds nothing a reviewer could report.

**Reviews go in REVIEW.md** (repo root, committed with the changes it records). Three skills: `project-code-review`
(`.claude/skills/project-code-review/`) for reviewing, its `TEMPLATE.md` the format; `address-review`
(`.claude/skills/address-review/`) for fixing or answering findings test first and checking them off; `cleanup-review`
(`.claude/skills/cleanup-review/`) for a cleanup the user asks for. REVIEW.md is the memory per branch: reviewers and
the agents addressing findings talk through it, as in a PR review, and it can be cleaned up once the branch is merged,
its history staying in git. DECISIONS.md is the memory for the whole project. The rules:

- Five sections by severity, from high to low: High, Medium-high, Medium, Low-medium, Low.
- Each finding is one entry starting with a checkbox: unchecked while open, checked once fixed or answered (not a bug,
  not reproducible, won't fix), with a resolution line giving the evidence, and no commit hash (branches are squashed
  into main).
- A new review **appends** its findings to the sections they belong in, plus an entry in the review log; it never
  replaces or rewrites what is there. A finding's number comes from the **Last used** line in the header, updated in
  the same edit.
- Only the user starts a cleanup of REVIEW.md, by asking for one explicitly; agents never truncate it on their own. A
  removed finding stays findable in git: `python3 scripts/review_lookup.py <ID>`.

### Running the tests

**Only the agent that changes the code runs tests.** A review runs none, unit or live (the `project-code-review` skill
or the built-in `/code-review`): reviewers read the code and the tests and report what reading can't settle as a
suspicion, with what would settle it; the agent leading the review settles each before anything is recorded, with
scratch probes of its own, one at a time in one Designer an agent started (the `project-code-review` skill).

**The full suites run only when the user asks:** the whole unit suite (`pytest` with no test ids) and a whole run of the
live self-test (`tests/test_all_tools`). Never start one on your own: not for TDD, not after a fix, not between
reviews. When a review finds nothing, tell the user the work is ready for the final check: both suites in full, run when
the user says the work is done, just before merging into `main`; both must pass (DECISIONS.md, Project rules).

**Unit tests while working:** only those added or modified for the change (for a refactor, the existing tests of the
code it touches), as often as useful. **Lint and types always run too** (about 10 s):
`mcp_server/venv/bin/python -m pytest <test ids> tests/unit/test_lint.py tests/unit/test_types.py`, the test ids files
or single tests (`tests/unit/test_x.py::test_name`). Docs changed alone (Markdown files, the skills included), in a
commit or a whole branch, run only the tests that validate the docs, the final check included, with
`tests/unit/test_lint.py tests/unit/test_types.py` added as always:
`mcp_server/venv/bin/python -m pytest tests/unit/test_constants.py tests/unit/test_guide.py tests/unit/test_review_lookup.py tests/unit/test_server.py`
(`test_review_lookup.py` fails if a test that reads a doc is missing from this command). After editing, run
`mcp_server/venv/bin/ruff check --fix .` and `mcp_server/venv/bin/ruff format .` (`test_lint.py` runs `ruff check` and
`ruff format --check`).

**Typing** (`test_types.py` runs mypy strict over every Python file). The helpers, the plugin and the example are
checked against Designer's own `sd` package and PySide6 stubs (found in the Designer install) and run on Designer's
Python 3.13, which evaluates annotations when a `def` runs: every name in an annotation there must exist at runtime
(import real types, `from sd.api.sdnode import SDNode`, never only under `if TYPE_CHECKING:`), and no `from __future__
import annotations` (the helpers are joined into one script, where it can't come first). The standalone scripts
(`install.py`, `uninstall.py`, `client/sd_run.py`, `scripts/review_lookup.py`) are the opposite: they run on the system
Python, maybe 3.9, so they do start with `from __future__ import annotations` and evaluate no `X | None` at module level
(`tests/unit/test_old_python.py` runs them on an older Python when one is installed).

**Strings of code** (`tests/unit/test_selftest_safety.py` checks the self-test's and the server's modules). A string of
several lines is written `dedent("""...""")` (`textwrap`), not joined pieces with `\n`; the server's own calls into the
helpers are one-line strings by design. Tests that read source text match whitespace-tolerantly (`c\(\s*'tool'`), as
formatting may split a call over lines.

**Live checks while working: a scratch run.** A new or changed check is seen failing, then passing, on its own in an
environment built for it, with `alone.run` from a script in the session's scratchpad, never through a run of the whole
suite. **Load the `live-check` skill before writing or running a live check, and for the final check:** it has
`alone.run`, the order, what a scratch run can't prove, what to do when the final check fails, and the suites.

### Keeping the docs current

README.md is for people, AGENTS.md for agents changing this project, `mcp_server/GUIDE.md` for agents driving Designer.
With every change (a tool, a fix, a workaround, a fact learned about
Designer), add a short note where it belongs, in the same change. Keep each fact in **one** place and link to it
instead of copying it; fix or delete notes that turn out wrong rather than adding a contradicting one. One repeat is
deliberate: the sentence saying what REVIEW.md and DECISIONS.md each remember.

| Kind of knowledge | Where it goes |
|---|---|
| How to use the tools well, workflow, sd API / Designer pitfalls, verified facts | **`mcp_server/GUIDE.md`**, in the matching section: the core if an agent using only the tools needs it or every script hits it on the first try, otherwise under `# Scripting` |
| How a tool works around Designer: what only whoever maintains it needs (would an agent using the tools act differently without it?) | The **docstring or comments of its module**, not the tool's docstring, which agents pay for; the guide keeps at most a line and the path |
| A tool's parameters and behaviour | The tool's **docstring in its module of `mcp_server/server_tools/`**, the single source; don't repeat parameters in the guide |
| Install, configuration, security, troubleshooting, anything a **person** needs | **README.md** |
| Architecture: what the plugin, server, helpers and CLI tools each do | **README.md**, "How it works" |
| How to deploy changes, diagnostics an **agent** needs | **AGENTS.md**, Deploying and diagnosing |
| New or changed tool | Its entry and the tool count in README.md's Tools table, and checks in `tests/test_all_tools/` |
| What is settled for the whole project: the user's won't fix, rule or choice; a not-a-bug or not-reproducible answer the user acknowledged at a cleanup | **DECISIONS.md** (read by the review skills; agents may update its names and paths, anything else takes the user) |
| Work still to do, ideas, follow-ups | **ROADMAP.md** (check an item when done; checked items can be deleted later, git keeps the record) |

Open work lives in [ROADMAP.md](ROADMAP.md): check it before proposing improvements, and add new ideas there.

### Deploying and diagnosing

- **Fresh clone, or a deleted `mcp_server/venv`:** run `python3 install.py` (Windows: `py -3 install.py`) first;
  without the venv the server can't start, and the `.mcp.json` command says so in `/mcp`. Then the user reconnects
  `/mcp`. `designer_status` shows which Python and library versions the server runs on.
- **The helpers** (`mcp_server/designer_helpers/`) are parts joined into one script (README.md, How it works). A part
  imports what it uses from other parts (`from .core import find_graph`), for PyCharm and readers; `part_source()` drops
  those lines. `tests/unit/test_designer_helpers.py` fails on a missing, extra or misplaced import, a name no part
  defines, and a part file not in `PARTS`. Code needing the helpers' text takes it from `designer_helpers.source()`,
  never from one file.
- **PyCharm** (the repo's `.idea` marks `client`, `mcp_server`, `tests` and `tests/unit` as source roots, also
  Designer's own `sd` and PySide6 folders, which the interpreter `mcp_server/venv` lacks: README.md, Working in
  PyCharm): tests patch a module loaded from its file with `monkeypatch.setitem(vars(module), 'NAME', value)`, not
  `setattr` (PyCharm checks that name against the fixture and reports it missing); standard modules are patched
  directly (`time`, not `server.time`).
- **The server** (`mcp_server/server.py`) only starts it and re-exports the names of `mcp_server/server_tools/`, one
  module per area (`core` holds the bridge and the `_tool` decorator; a new module goes into `MODULES` in its
  `__init__.py`). Unit tests replace a name with `patch_server` (`tests/unit/conftest.py`), which patches every module
  binding it: patching `server` alone doesn't reach the tools.
- **How changes reach Designer:** `server.py`, `server_tools/` and `designer_helpers/` changes take effect when the MCP
  server restarts (helpers are re-sent with every call; the user reconnects in `/mcp`, or test with a fresh MCP client
  such as the self-test). **Plugin** changes must be copied into Designer's plugin folder (re-run `install.py`; paths in
  README.md, Install) and need a **Designer restart**: for a Designer an agent started, `quit_designer` then
  `launch_designer` without asking (say that you did); for the user's, ask them to save, close and reopen it.
- **The plugin's name** (`sd_claude_bridge_kve`, also its folder names and the token file
  `~/.sd_claude_bridge_kve_token`) is defined once, in `project_constants.py`; the plugin takes it from its own folder.
  To rename: change `PLUGIN` there, rename both `plugin/<name>` folders, update README.md, AGENTS.md and GUIDE.md, and add the old name
  to `install.py`'s clean-up of old copies. `tests/unit/test_constants.py` fails on anything missed.
- **Registration is per folder, never global, for now** (README.md, "Where the tools are available"; ROADMAP item 5
  will make global registration the installer's choice): this repo's committed `.mcp.json`, or
  `claude mcp add --scope local` in another folder. The installer never registers; it writes a user skill (`skill_text`
  in `install.py`) telling sessions elsewhere how to register, and `uninstall.py` removes the skill, the plugin, the
  token, every folder's local registration and a user-scope one (only entries running this repo's `server.py`).
  `.mcp.json` must not contain `${`: Claude Code expands those itself (it once rewrote a shell default away), so its
  `sh -c` command uses plain `$VARS` (`tests/unit/test_mcp_json.py`).
- **The bridge protocol** is defined in the plugin's docstring. `server_tools/core.py`, `client/sd_run.py` and the
  self-test's `raw_request` all speak it: change them together with the plugin, and raise `BRIDGE_PROTOCOL`
  (`project_constants.py`) and the plugin's `PROTOCOL` with any change to it.
- Environment variables `SD_DESIGNER_BIN_DIR`, `SD_DESIGNER_APP`, `SD_DESIGNER_LOG`, `SD_SNAPSHOT_DIR`,
  `SD_BRIDGE_PORT`: README.md, Configuration. A port change must reach the plugin (Designer's environment) and the
  server alike.
- **When tools fail:** match the symptom in README.md, Troubleshooting, and try `read_designer_log`. If Designer isn't
  running or answering, ask the user to open it, or to save, close and reopen it (in tests and work on this project,
  `launch_designer`). If the bridge accepts connections but never answers, or a tool is missing in Claude Code, only the
  user can fix it (restart Designer / reconnect `/mcp`): tell them.
