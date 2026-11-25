---
paths:
  - "**/*.py"
---

# Python in this repository

The rules for every Python file, and the commands for its tests while working (AGENTS.md, Working on this project
and Running the tests, point here).

**Navigating and checking code: PyCharm's MCP tools first** (`mcp__pycharm__*`, when PyCharm has this project open;
it resolves Designer's `sd` and PySide6 through the repo's `.idea`): `search_symbol` to find a definition
(`include_external` for Designer's and the libraries' code), `get_symbol_info` for a symbol's signature and docs,
`analyze_calls` for callers and callees, `get_file_problems` or `lint_files` after an edit, `rename_refactoring` for a
rename across files. Fall back to the command line (grep, `git grep`, reading files) only when they don't help enough:
they aren't connected, a call refuses or finds nothing (`analyze_calls` takes only names it resolves), or you need
every use of a name, which `search_symbol` doesn't give (it finds where a name is defined). mypy strict and ruff (the
unit tests) stay the checks that count; PyCharm's inspections don't replace them.

**After editing,** run `mcp_server/venv/bin/ruff check --fix .` and `mcp_server/venv/bin/ruff format .` (`test_lint.py`
runs `ruff check` and `ruff format --check`). Then run the tests of your change by name. They are the tests added or
modified for it, and the unit tests that read the source of the files it changes. A guard test the change never touched
still fails on it: `test_library_refusal.py` failed on a reader added to the helpers, and no developer had run that
test since (REVIEW.md TST-754). To find those tests, grep `tests/unit` for:
- `designer_helpers.source()` or `part_source(`, which read the helpers' text;
- the `helpers` and `faked_helpers` fixtures, which run the joined helpers;
- `server_source()`, `selftest_sources()` and the walks of `mcp_server` or `tests/test_all_tools`, which read the
  server's or the self-test's files;
- `repo_files()` (`tests/unit/docs_text.py`), which lists every file of the repository for the scans of
  `test_constants.py`, `test_guide.py` and `test_types.py`.

Lint and types always run with them (about 10 s):
`mcp_server/venv/bin/python -m pytest <test ids> tests/unit/test_lint.py tests/unit/test_types.py`, the test ids files
or single tests (`tests/unit/test_x.py::test_name`). A change of Markdown, a comment or a
docstring adds the docs tests (`.claude/rules/docs-tests.md`).

**Typing** (`test_types.py` runs mypy strict over every Python file). The helpers, the plugin, the example and
`mcp_server/designer_rollback.py` (the rollback and `undo_edits`' undo, sent into Designer) are checked against
Designer's own `sd` package and PySide6 stubs (found in the Designer install) and run on Designer's
Python 3.13, which evaluates annotations when a `def` runs: every name in an annotation there must exist at runtime
(import real types, `from sd.api.sdnode import SDNode`, never only under `if TYPE_CHECKING:`), and no `from __future__
import annotations` (the helpers are joined into one script, where it can't come first). Every other Python file
needs Python 3.12 (`MIN_PYTHON` in `project_constants.py`), and mypy and ruff check the code as 3.12 (DECISIONS.md,
Project rules). The scripts a user starts (`install.py`, `uninstall.py`, `client/sd_run.py`,
`scripts/review_lookup.py`, `scripts/read_crash_dump.py`; `ENTRY_SCRIPTS` in `tests/unit/conftest.py`) run only on
3.12 or later too, but are started with whatever `python3` is installed, a stock Mac's being 3.9. Each starts with
`import sys` and a check of `sys.version_info` that refuses an older Python with a message, before any other import.
`mcp_server/server.py` does too, for a venv an older Python made (`SERVER_SCRIPT`). Python reads a whole file before it
runs the first line, so such a file stays readable by 3.9: it leaves out the syntax added after 3.9 (`type`
statements, `def f[T]`, `match`), and may call anything 3.12 has. ruff checks most of that syntax (`ruff.toml`);
`tests/unit/test_old_python.py` checks the refusal and, where a Python 3.9 is installed, the rest on it.

**The most specific type that fits; `Any` is the last resort.** mypy checks nothing through an `Any`, so before
writing `Any` (or a `dict`, `list` or `tuple` whose items' types say less than is known: a
record's `dict[str, object]` where a `TypedDict` fits; a bare one strict mypy refuses already) look for what the value
really is: a type of the code it comes from (`SDNode`, `Reply`,
`subprocess.CompletedProcess[str]`), a union of the few it can be, a `TypedDict` for a dict with known keys (a record,
a reply, a worker's results), a `Protocol` for an object of which only some attributes are used, `Callable[[...], ...]`
for a function, a `TypeVar` for a value passed through, `object` for one only stored, printed or compared, or for
parsed JSON before it is checked (it makes the checks explicit). `Any` stays where nothing narrower is true or can be
checked (a fake standing in for a type it can't subclass, what sd's own stubs leave untyped), marked as an exception
with its reason: `# type: ignore[explicit-any]  # <reason>`, on the line mypy reports. For a function, that is its
`def` line, even when the signature spans several lines. An `Any` so marked, with a reason that holds, is accepted.
mypy refuses an `Any` written in an annotation, a signature, a `cast` or a type alias without the mark, the `...` of
`Callable[..., T]` included (`disallow_any_explicit` in `mypy.ini`). It doesn't report an `Any` inside an expression,
such as `defaultdict[str, Any](int)`, nor one that comes in implicitly, such as `json.loads`'s result
(`tests/unit/test_types.py`), so look for those yourself. A function you change gets the same look: an `Any`,
or a `dict`, `list` or `tuple` whose items' types say less than is known, that it holds and could be narrower is
narrowed in the same change.
Reviewers report what is left in the functions a branch's diff adds or changes, and anywhere in a whole-project review
(`.claude/agents/reviewer.md`, What to hunt for).

**Strings of code** (`tests/unit/test_selftest_safety.py` checks the self-test's and the server's modules). A string of
several lines is written `dedent("""...""")` (`textwrap`), not joined pieces with `\n`; the server's own calls into the
helpers are one-line strings by design. Tests that read source text match whitespace-tolerantly (`c\(\s*'tool'`), as
formatting may split a call over lines.

**Keep each file to its main logic.** Code that isn't what a file is about (the setup a test needs, a parser, a helper
its reader doesn't need to follow the main flow) goes into a module of its own beside it, named for what it does
(`preparations.py`, `parsing.py`), and is imported from there: a reader of a file meets its main logic first, not its
scaffolding. It applies to new code and to code a change touches; a move alone changes no behaviour, so the existing
tests of the code it touches run before and after and pass both times.

**Simplify the change before reviewing it.** Once a change of code passes its tests, the agent that made it runs
`/simplify` on it, once per change it hands back, a round of fixes included. `/simplify` is Claude Code's built-in
skill. It reviews the diff for reuse, simplification, efficiency and altitude, then applies the fixes in this session.
Skip a fix that goes against AGENTS.md, a rule or skill it points to, or DECISIONS.md, or one that would only
restyle a comment, docstring or doc. The fixes change no behaviour, so the rule for a rename or a move applies
(AGENTS.md, Start with the tests). The change's last passing test run is the run before the fixes: don't repeat it.
After the fixes, run the tests of the code they touch, with lint and types: they must pass. Start `/simplify`'s four
cleanup agents as the `analyst` agent, which only reads. A change of Markdown files alone skips this step, and so does a
review.
