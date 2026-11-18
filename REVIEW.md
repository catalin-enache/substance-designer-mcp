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

**Last used:** PLG-45, SRV-180, HLP-188, INS-46, TST-536.

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
| Low-medium | 0 | 2 |
| Low | 0 | 19 |
| **Total** | **0** | **21** |

## Review log

### 2026-11-18: the python-3-12 branch against main (ROADMAP item 105, the diff only, uncommitted)

- **How:** four reviewers, one area each: the scripts a user starts and the modules they import; the configs and
  their tests; the Designer-side code, the server and the self-test; the docs. No tests run. The lead agent settled
  each suspicion by reading, and with scratch probes outside Designer:
  - importing `project_constants` on `/usr/bin/python3` 3.9.6: `SyntaxError` at `type Json = ...` (SRV-176);
  - the order check's own functions on `def f[T]` and `class C[T]`: `[('a', 'T')]` each (TST-527);
  - `type J = list[J] | Later; X = J` on 3.12: runs, `X.__value__` raises NameError (TST-528);
  - ruff 0.17.3 with `--stdin-filename install.py`: `a[e := 0]` draws no `invalid-syntax`, `match` does; 3.9.6
    refuses both (TST-530).
  The reviewers' own probes: the five scripts parse on 3.9.6, and `project_constants.py` and `designer_preferences.py`
  don't (both imported only after the check); Designer 16.0's release notes list Python 3.13 (the plugin's and the
  helpers' `type` statements parse on every supported Designer); a mypy strict run with numpy 2.5.4 needs the removed
  `call-overload` ignores as 3.10 and not as 3.12. Settled as wrong: designer_preferences.py's "so it runs on the system
  Python too" and ROADMAP item 43's "as sd_run.py does" (both still true: a system Python 3.12+); a TypeAliasType
  breaking a runtime use (nothing calls isinstance, get_args or get_type_hints on Json, JsonSent or Plist, and the tool
  schemas use pydantic's JsonValue: the published schemas are byte-identical to main's, measured before the review).
  ROADMAP.md was reformatted on disk outside this session (2026-11-18 07:32: every table padded, the file 84,774 bytes
  at HEAD, 290,068 now); not a finding of the branch's code, left for the user to decide.
- **Not verified:** on Windows, `py -3 install.py` over a venv a Python 3.10 or 3.11 made, while a connected MCP
  server runs from it: `venv --clear` (the stdlib's `clear_directory`, no error handling) would stop at the first file
  in use, with a traceback and the venv half cleared. Before this change `--clear` ran only over a venv whose Python
  didn't start. Read in the stdlib only; no Windows here. What would check it: on Windows, make a 3.11 venv with
  pydantic-core and numpy, keep a process importing both running, run `py -3.12 -m venv --clear` over it, and record the
  exit code and what is left; then try `os.rename` of the folder while it runs (expected to fail cleanly, a fix's base:
  rename aside, or catch the failure and say to close Claude Code first).
- **Resolutions assessed:** none in scope (REVIEW.md was empty after the last cleanup).
- **Findings:** INS-42 (Low-medium); SRV-176, INS-43, SRV-177, TST-527, TST-528, TST-529, TST-530, TST-531 (Low). Two
  reviewers found INS-42, SRV-176, TST-527 and TST-531.
- **Suggested order:** INS-42 and SRV-176 first (what users meet: commands that refuse, a server failing with a bare
  SyntaxError), then TST-529 (a test that can't see the regression it guards), TST-527 and TST-528 (the order check),
  TST-530 and TST-531 (wording; DECISIONS.md's takes the user), INS-43, SRV-177 (better as a ROADMAP item for every
  tool's fixed-length list parameters).
- **Simplifications:** none beyond the /simplify pass already applied.
- **Checked and found fine:** each script's `import sys` and check come first, before every other import, def and
  `sys.path` change; no `Union`, `Optional`, `__future__`, `noqa: UP` or `typing_extensions` left; `venv_version` and
  `venv_usable` (numbers compared as numbers, a missing or dead python gives None, Python 2's stderr merged, unparsable
  output leads to a remake); `ruff.toml`'s per-file target applies 3.9 to exactly the five scripts, for the linter and
  the formatter; the runpy refusal test leaks nothing and fails with the check in `main()` or at 3.10; the structural
  test ties the scripts' `(3, 12)` to `MIN_PYTHON`; the joined helpers build their annotations and batch.py's
  functional TypedDict with `type Json`, and a scope holding the alias is still collected (HLP-182, PLG-45); the
  plugin's `_Job` and the tracer's `-> _TraceFunc | None` build at load; `inheritance_resets.py` runs through
  `run_designer_script`'s exec nesting; the `bool(...)` wraps change nothing (`check` calls `bool` too); the `Unpack`
  moves and `*tuple[...]`; README's requirements, install and uninstall notes, requirements.txt's lower bounds
  (measured with pip download), ROADMAP row 105's steps all done.
- **Longest chain:** none; every finding is generation 1.

### 2026-11-18: the python-3-12 branch against main, second review (the diff only, uncommitted)

- **How:** four reviewers, one area each: the scripts and the installer; the tools' tuple parameters and the helpers
  receiving them; the tests, configs, Designer-side and self-test changes; the docs. No tests run. The lead agent settled
  each suspicion by reading, and with probes outside Designer:
  - the in-process server's `call_tool` with `[]` for `node_stats`' region, `add_frame`'s colour, `arrange_graph`'s
    spacing, `add_comment`'s position and `preview_maps`' crop: all refused by validation, where main took `[]` as not
    given (`git show HEAD:` of each line) (SRV-178);
  - CPython's installed Makefile: only `install`'s `bininstall` links `bin/python3`; `altinstall` installs
    `python3.12` alone (INS-44).
  The reviewers' own probes, read and kept: a venv made from another venv has the base Python as `sys.base_prefix`; the
  installer run from another venv gave that venv's Python as the uninstall command (INS-44); `'not %r' % (181.0, 0.0)`
  raises "not all arguments converted" (TST-534); `ntpath.join` and the shlex round trip keep the backslash (TST-536);
  through `call_tool`, what agents send is accepted (ints for floats, a colour of 3 or 4, `"[1, 0, 0]"` as text, None;
  a Box's 10.0, not 10.5) and a wrong count is refused naming the parameter, nothing sent. Settled as wrong or not
  reported: pydantic's messages for too few values ("Field required" per position, doubled by Color's union) name the
  parameter and the schema states the count, so they stay; ruff.toml's lines 4 and 14 describe less than they configure
  but nothing false; ROADMAP row 105 keeps its plan in the present tense once checked, as row 41 does; DECISIONS.md's
  date of the user's decision (the evening of 2026-11-17, after HEAD's commit) holds; README.md's bare `python install.py
  --plugins-dir` and `python client/sd_run.py` predate the branch, the latter now under "With a Python 3.12+".
- **Not verified:** the first review's Windows suspicion (`venv --clear` over a venv in use) stands, unchanged.
- **Resolutions assessed:** SRV-176, TST-527, TST-528, TST-529 and TST-531 hold (TST-531's one missed sentence, a test
  comment, is in TST-532). INS-42 questioned by INS-44, INS-46 and TST-532; INS-43 by INS-45; SRV-177 by SRV-178,
  TST-534, TST-535 and HLP-188; TST-530 by TST-533.
- **Findings:** SRV-178 (Low-medium); INS-44, INS-45, INS-46, TST-532, TST-533, TST-534, TST-535, TST-536, HLP-188,
  SRV-179 (Low). Two reviewers found TST-532 (in part), TST-534 and HLP-188.
- **Suggested order:** SRV-178 first (a tool refusing calls that worked; or the user decides it should), then INS-44 and
  INS-46 (commands users copy), TST-535 and TST-534 (tests that can't see a regression), INS-45, HLP-188, TST-536,
  SRV-179, then the wording: TST-532, TST-533 (generation 2 on docs: narrow the sentences).
- **Checked and found fine:** the five scripts and `server.py` compile on 3.9.6, and `server.py` there exits 1 with
  SRV-176's message on stderr and nothing on stdout (no stray output on the JSON-RPC stream); the `.mcp.json` command with
  no venv prints its new message; `_not_finite` walks tuples (`orbit: [NaN, 0]` gives "orbit[0] is nan"); every schema is
  `anyOf [array(items, minItems, maxItems), null]`, Color's 3..4 matching its union; downstream uses of the tuples
  (`set(links)`, `orbit if orbit and any(orbit)`, `_crop_box`'s unpacking, the helpers' indexing and `list(color) +
  ...`); the `sent` fixture's move to conftest.py (nothing used the old one; `test_selftest_lifecycle.py`'s parametrized
  `sent` overrides it); test_old_python's structure, runpy and real-3.9 tests; the remake test's strict fake covering both
  `venv_version` calls; the classification test's strict set equality; the cases moved out of test_view3d, test_output
  and test_pixels covered where they went; the docs' names and paths; no stale 3.10, "3.9 at the oldest", "standalone
  scripts", `typing_extensions` or `TypeAlias` left.
- **Longest chain:** generation 2 (INS-42, INS-43, SRV-177 and TST-530 each followed once).

---

## High

## Medium-high

## Medium

## Low-medium


- [x] **INS-42 · Commands the code prints and the docs give still say a bare `python3` for scripts that now refuse 3.9** · `install.py:108`, `uninstall.py:395`, `client/sd_run.py:100`, `.mcp.json:8`, `tests/test_all_tools/alone.py:245`, `README.md:186`, `mcp_server/GUIDE.md:82` · confirmed · found 2026-11-18
  - **Defect.** The five scripts now refuse a Python older than 3.12, but the commands that lead users and agents to them
    still name a bare `python3` (or `python`), which is 3.9 on a Mac with no other Python (`/usr/bin/python3` 3.9.6 on
    macOS 26.6.2, measured). Before this change `uninstall.py`, `sd_run.py` and `scripts/` ran on 3.9, so these commands
    worked there.
    - The skill the installer writes gives `python3 <repo>/uninstall.py` for removing everything: `(['py', '-3'] if
      sys.platform == 'win32' else ['python3'])` (`install.py:108`). The installer knows a Python 3.12+ there: its own
      `sys.executable`, when that isn't the venv's.
    - `uninstall.py:395`, shown when it runs with the venv's own Python: "Run it with your system Python instead: python3
      uninstall.py". `tests/unit/test_uninstall.py:256` pins the wording.
    - `client/sd_run.py:100` ("python3 install.py"), the `.mcp.json` message ("run python3 install.py"), and alone.py's
      hint "python3 scripts/read_crash_dump.py <dump>".
    - README.md:186, the manual install: "with a Python 3.12 or later:" is followed by `python3 -m venv mcp_server/venv`.
      With a stock Mac's `python3` that makes a 3.9 venv, and pip then fails on `mcp`; with a 3.10 or 3.11 `python3`
      the server later fails at import (SRV-176). GUIDE.md:82's `python client/sd_run.py` names no version.
    - The agents' docs: AGENTS.md (`python3 scripts/review_lookup.py`, `python3 scripts/read_crash_dump.py`), the
      skills' `python3 scripts/review_lookup.py` and README.md's `python3 scripts/read_crash_dump.py` (line 438, a
      script README.md:108's list of those needing 3.12+ leaves out). REVIEW.md's header and the skills' lines are
      pinned by `tests/unit/test_review_lookup.py:96`, `:724`; the header stays as a cleanup keeps it.
  - **Scenario.** A Mac user whose `python3` is 3.9 installs with `python3.12 install.py`, as README.md:121 says. Later an
    agent in another folder follows the skill and runs `python3 <repo>/uninstall.py`: "Python 3.12+ is required (found
    3.9.6)", and nothing says which Python to use. Every command works where `python3` is 3.12+, as on this Mac.
  - **Fix.** In the skill text, name the Python that ran the installer when it isn't the venv's (else `python3`). Give
    the uninstaller's note, the sd_run and `.mcp.json` messages and alone.py's hint README.md:391's form ("a Python 3.12+:
    python3.12 where python3 is older"), and update `test_uninstall.py:256`. In README.md:186 add `# python3.12 -m venv
    ... where python3 is older`; give GUIDE.md:82 README.md:341's "(Python 3.12+, such as mcp_server/venv/bin/python)";
    add `scripts/read_crash_dump.py` to README.md:108's list. One sentence in AGENTS.md, Deploying and diagnosing: the
    `python3 ...` commands need a `python3` of 3.12+, and `mcp_server/venv/bin/python` runs the read-only scripts.
    Two reviewers found it.
  - **Resolution: done.**
    - **Test:** `test_install.py::test_the_skills_uninstall_command_names_the_python_that_ran_the_installer` (a system
      Python, the venv's own) failed with `'python3' == '/opt/python3.12/bin/python3'`;
      `test_uninstall.py::test_warns_when_run_with_the_venvs_own_python` now asks the note for the Python the venv was
      made from and failed on the old note.
    - **Cause:** the commands were written when these scripts ran on 3.9, so a bare `python3` always worked.
    - **Fix:** `install.py`'s new `system_python(venv)` gives the command for `uninstall.py`: the Python that ran the
      installer (it passed the version check); when that is the venv's own, the Python the venv was made from
      (`sys.base_prefix`, a 3.12+ too); `py -3` on Windows. The skill's uninstall command and the uninstaller's note (shown
      when it runs on the venv's Python) both print it; `install.runs_from(venv)` is the one check of "this is the venv's
      own Python" (`uninstall.py` had its own copy). sd_run's no-token message and the `.mcp.json` message say "a Python
      3.12+ (python3.12 where python3 is older)"; alone.py's hint names `mcp_server/venv/bin/python`. README.md's manual install adds "python3.12 where python3 is older" and its list of
      scripts needing 3.12+ gains `scripts/read_crash_dump.py`; GUIDE.md's fallback names the venv's Python and 3.12+;
      AGENTS.md, Deploying and diagnosing, says the `python3 ...` commands need a 3.12+ and which the venv's Python runs.
    - **Also covered:** searched every `python3 `, `python ` and `py -3` command in the code, docs and skills. The
      skills' and REVIEW.md's header's `python3 scripts/review_lookup.py` stay as they are (pinned by
      `test_review_lookup.py`; the AGENTS.md sentence covers them); README.md's `python3 install.py` and `python3
      uninstall.py` lines already said "python3.12 where python3 is older".
  - Questioned by INS-44, INS-46, TST-532 (2026-11-18).

- [x] **SRV-178 · An empty array, which seven optional parameters took as "not given", is now refused** · follows SRV-177, generation 2 · `mcp_server/server_tools/core.py:183-189`, `measure.py:155`, `compare.py:41`, `:208`, `output.py:329`, `layout.py:35`, `mcp_server/designer_helpers/layout.py:140`, `:160` · measured · found 2026-11-18
  - **Defect.** With the tuple types, `[]` fails validation for `node_stats`' `region`, `compare_to_reference`'s `region`
    and `reference_region`, `preview_maps`' `crop`, `arrange_graph`'s `spacing`, `add_frame`'s `color` and
    `add_comment`'s `position`. On main each took `[]` as not given: `if region:` and `if crop:` skipped the crop,
    `tuple(spacing or (200.0, 150.0))` took the default, the helper's `if color:` set no colour, and `_position(position)
    if position and not node_id else None` placed the comment where it goes by default. (`open_graph`'s `rect` and
    `screenshot_designer`'s `crop`, `orbit` and `pan` refused `[]` on main too.) Measured through the in-process server's
    `call_tool`: `node_stats` with `region=[]` gives "4 validation errors", `add_frame` with `color=[]` 7, and
    `arrange_graph`, `add_comment` and `preview_maps` are refused alike.
  - **Scenario.** A client that fills optional fields with empty values (the case SRV-147 fixed for strings, hence
    `graph or None` in views.py) calls `node_stats(node_id='n', region=[])`: whole-image stats on main, validation errors
    now. SRV-177's resolution lists the refusals it added, not this one.
  - **Fix.** Take `[]` as not given again for the top-level optional parameters: a `BeforeValidator` turning an empty
    list into None on the aliases used as `X | None` (not on `Pixel` or `Link` inside lists), with a unit test through
    `call_tool` for each of the seven. Or refusing it is right (the schema's `minItems` now says so): then the user decides,
    and DECISIONS.md records it.
  - **Resolution: done** (the user: "address them all", with `[]` taken as not given, as proposed).
    - **Test:** `test_server.py::test_an_empty_array_is_taken_as_not_given`, for every parameter of `_FIXED`, validates
      `[]` with the tool's own argument model: all 11 failed ("Field required"), the 4 that refused `[]` on main too
      (`rect`, `screenshot_designer`'s `crop`, `orbit`, `pan`) included.
    - **Fix:** `NoneIfEmpty` in `server_tools/core.py`, `Annotated[T | None, BeforeValidator(_empty_is_none)]`, wraps
      every optional parameter of a fixed number of values (`NoneIfEmpty[Box]`, `[XY]`, `[Four]`, `[Color]`): `[]`
      becomes None before the tuple is checked; the schemas are unchanged (compared), and a wrong count is still refused.
    - **Also covered:** `points` and `links` take any number of items: `[]` was and is an empty list, accepted.

## Low

- [x] **SRV-176 · A venv an older Python made, kept after a `git pull`, stops the server with a bare SyntaxError** · `mcp_server/server.py:15-18`, `project_constants.py:35` · measured · found 2026-11-18
  - **Defect.** `server.py` imports `server_tools`, whose `core` imports `project_constants`, now holding `type Json =
    ...`, a SyntaxError before Python 3.12. A venv made with 3.10 or 3.11 (the minimum until this change) runs the server
    until the user re-runs the installer, which now remakes it. Until then the server stops at import with a traceback
    and no word on what to do. Measured with the 3.9 here (3.10 and 3.11 aren't installed; `type` is the same
    SyntaxError on both): importing `project_constants` gives `SyntaxError: invalid syntax` at `type Json = ...`.
  - **Scenario.** A user who installed with 3.11 pulls and reconnects `/mcp` without re-running the installer: `/mcp`
    says "Failed to connect". README.md:147 says to re-run the installer after updating, and its Troubleshooting row
    (README.md:427) says to run the server by hand, "usually Python too old or the venv missing", so the cue exists but the
    error itself points at `project_constants.py`.
  - **Fix.** A check at the top of `server.py`, before `import server_tools`, as the five scripts have: below
    `MIN_PYTHON` it writes "mcp_server/venv runs Python 3.11; run install.py again: it makes the venv again with 3.12+"
    to stderr and exits 1. `server.py` then stays readable by 3.10 (it is a few lines). Or narrow it to a Troubleshooting
    row naming the SyntaxError. Two reviewers found it.
  - **Resolution: done.**
    - **Test:** `test_old_python.py`'s three tests now also run `mcp_server/server.py` (`SERVER_SCRIPT` in conftest.py):
      the check comes first (failed: `import os` came first), the refusal in this Python at 3.9.6 and 3.11.9, and on the
      real 3.9.6 (failed: a traceback); `test_lint.py` asks ruff to check it as 3.9 too.
    - **Cause:** the server imports `project_constants`, now holding `type` statements, with nothing before it to say
      the venv's Python is too old.
    - **Fix:** `server.py` starts with `import sys` and the check, which writes "Python 3.12+ is required (found X). If
      this is mcp_server/venv, an older Python made it: run install.py again, with a Python 3.12+" and exits 1; it stays
      readable by 3.9 (ruff.toml lists it with the five scripts). DECISIONS.md and AGENTS.md say so.
    - **Also covered:** the other files Claude Code or a user starts with a Python that may be older: the five scripts
      (already checked); `tests/test_all_tools/__main__.py` runs on the venv's Python and is no user's (not changed).

- [x] **INS-43 · The installer says the venv is ready in the same words when it made it again** · `install.py:294` · confirmed · found 2026-11-18
  - **Defect.** `print('[2/4] MCP server environment ready (%s): %s' % (venv_version(py) or 'Python version unknown',
    venv))` reads the same whether the venv was kept or made again from an older Python's.
  - **Scenario.** A contributor whose venv was made with 3.11 re-runs the installer: the venv is made again with 3.12,
    and the test tools it held (`requirements-dev.txt`: pytest, mypy, ruff), which the installer doesn't install, are
    gone without a word. They learn it when `python -m pytest` fails.
  - **Fix.** When it made the venv again over one an older Python made, say so in the `[2/4]` line ("made again: the
    one there ran Python 3.11"), with a hint to install `mcp_server/requirements-dev.txt` again for the tests.
  - **Resolution: done.**
    - **Test:** `test_install.py::test_rerun_remakes_a_venv_only_when_a_python_older_than_3_12_made_it` now reads the
      `[2/4]` line: made again from 3.9.6 or 3.11.9 it must say "made again: the one there ran Python X" and name
      `requirements-dev.txt`, kept at 3.12.0 it must not; failed on the old line for both remakes.
    - **Fix:** `main()` reads the venv's version once before (`venv_version`, judged by the new `usable`), and when it
      made the venv again over one that ran, the `[2/4]` line adds ", made again: the one there ran Python 3.11.9. For
      the tests, install mcp_server/requirements-dev.txt again".
    - **Also covered:** the INS-23 repair (a dead python) knew no version, so its line stays as it was.
  - Questioned by INS-45 (2026-11-18).

- [x] **SRV-177 · `node_stats`' and `compare_to_reference`'s pixel parameters are typed looser than their known shape** · `mcp_server/server_tools/measure.py:143-144`, `mcp_server/server_tools/compare.py:192-193` · confirmed · found 2026-11-18
  - **Defect.** In functions this diff changes (only comments removed in them): `region: list[int]` holds `[x0, y0, x1,
    y1]` and `points: list[list[int]]` holds `[[x, y], ...]` (their docstrings), as do `compare_to_reference`'s `region`
    and `reference_region`. The types say nothing of the lengths (AGENTS.md, Typing: the most specific type that fits).
  - **Scenario.** `points=[[1, 2, 3]]` passes the schema and fails in `for x, y in points or []:` with "too many values
    to unpack (expected 2)", which doesn't tell the agent what it sent wrong. `region` gets a clear message from
    `_crop_box` already.
  - **Fix.** `list[tuple[int, int]]` for `points`, `tuple[int, int, int, int]` for the regions. It changes the tools'
    input schemas (the `mcp-builder` skill first) and the same convention runs through other tools, so a ROADMAP item for
    every tool's fixed-length list parameters may fit better than a fix in this branch; the behaviour predates it.
  - **Resolution: done** (the user's choice: in this branch, not as a ROADMAP item).
    - **Test:** `test_server.py::test_a_parameter_of_a_fixed_length_says_it_in_its_schema` (11 parameters) and
      `::test_a_list_of_items_of_a_fixed_length_says_it_in_its_schema` (2) read the schemas the server publishes: all
      failed (any number of items). `::test_every_array_parameter_says_how_many_values_it_takes` classifies every array
      parameter as fixed, a list of fixed items, or any number, so a new one can't come in as `list[...]` unnoticed.
      `::test_a_wrong_number_of_values_is_refused_before_anything_reaches_designer`, with the `sent` fixture (moved from
      `test_finite_numbers.py` to conftest.py): a point of 3 reached the tool (failed: "Designer is not reachable"); a
      region of 3, an orbit of 1 or 3, a pan of 1, a crop of 3 and a colour of 2 are refused too, by pydantic naming the
      parameter, with nothing sent. The region, orbit, pan and crop cases moved there from `test_pixels.py`,
      `test_view3d.py` and `test_output.py`, which called the functions directly, past the schema.
    - **Cause:** the parameters were typed `list[...]`, so their schemas allowed any number of values, and the lengths
      were checked in the tools (some), or not at all (`points`, `links`, `position`, `color`, `spacing`).
    - **Fix:** tuples, as aliases in `server_tools/core.py` that keep the schema short (`_array`, a `WithJsonSchema`
      with `minItems` and `maxItems`, as `AnyJson` does; pydantic's own tuple schema describes every position, 1,173
      characters more over the tools, 390 this way): `Box` (four ints) for `node_stats`' and `compare_to_reference`'s
      regions and `preview_maps`' crop; `list[Pixel]` for `points`; `XY` for `add_comment`'s `position`,
      `arrange_graph`'s `spacing` and `screenshot_designer`'s `orbit` and `pan`; `Four` for its `crop` and
      `open_graph`'s `rect`; `Color` (three or four) for `add_frame`'s `color`; `list[Link]` for `set_link_display`'s
      `links`. The length checks the schema now makes are gone (`_crop_box`, `open_graph`'s rect,
      the crop's, orbit's and pan's); their range checks stay. mypy then found the orbit and pan messages formatting the
      tuple itself (`% orbit`, a TypeError); they print `list(orbit)`, as the crop's message does. The published schemas changed in exactly these 13
      parameters (compared with main's). Scratch run: bitmaps, editor_open_and_zoom, layout, link_display, lookup,
      measure, render, safeguards, facts and three orbit and pan checks of editor_panels_and_fit, 343 checks passed (the
      helpers receive the tuples as Python literals; they index or unpack them).
    - **Also covered:** every array parameter of the 35 tools: `node_ids`, `names`, `outputs`, `from_nodes`,
      `apply_edits`' `ops`, `sweep_param`'s `values` and `render_sbs`' `params` take any number (not changed).
  - Questioned by SRV-178, TST-534, TST-535, HLP-188 (2026-11-18).

- [x] **TST-527 · The helpers' order check counts a PEP 695 generic's own type parameters as names read too early** · `tests/unit/test_designer_helpers.py:73-95` · measured · found 2026-11-18
  - **Defect.** The change taught `_load_time_uses` that a `type` statement's value is lazy, but its `FunctionDef` and
    `ClassDef` branches still visit annotations, returns and bases without the names of `node.type_params`. Measured:
    `_used_before_bound([('a', ast.parse('def f[T](x: T) -> T:\n    return x\n'))])` gives `[('a', 'T')]`, and
    `class C[T]:\n    x: T` the same; both load on 3.12 and 3.13.
  - **Scenario.** ruff now checks the helpers as 3.12 with `UP` selected, so UP046/UP047 ask a `TypeVar` generic helper
    to become `def f[T](...)`. Rewritten so, it makes `test_core_comes_first_and_nothing_else_depends_on_the_order` fail
    with `('part', 'T')`, a false alarm. No helper is generic today. Two reviewers found it.
  - **Fix.** In those branches, count `node.type_params`' names as bound while visiting annotations, returns, bases,
    keywords and the class body; don't visit their bounds (lazy); decorators and defaults keep counting. Add both cases
    to `test_the_checks_below_can_fail`, expecting `[]`.
  - **Resolution: done.**
    - **Test:** `test_the_checks_below_can_fail` gained `def f[T: Later](x: T = D) -> list[T]` and `class C[T](Base[T]):
      x: T`, expecting only `D` and `Base`; it failed with `('a', 'T')`.
    - **Fix:** `_type_params` gives a generic def's or class's type parameters; `_load_time_uses` takes them as bound in
      its annotations and returns, and in a class's bases, keywords and body. Their bounds aren't visited (lazy);
      decorators and defaults still count.

- [x] **TST-528 · A docstring and a comment say a `type` alias's value is evaluated when the alias is first read** · `tests/unit/test_designer_helpers.py:65`, `:244` · measured · found 2026-11-18
  - **Defect.** "nor a type statement's value (evaluated when the alias is first read)" and "evaluates its value only
    when it is first read". Python evaluates it when `__value__` is first accessed. Measured on 3.12: `type J = list[J] |
    Later; X = J` runs; `X.__value__` then raises `NameError: name 'Later' is not defined`. The test's own case (`X = J`,
    expecting `[]`) relies on a read not evaluating it.
  - **Scenario.** A maintainer trusting the comment makes the check count a load-time read of an alias as a use of its
    value, and core's `Json` is reported wrongly.
  - **Fix.** "evaluated only when its `__value__` is first read (typing introspection), not when the script loads or
    reads the alias".
  - **Resolution: done.** The docstring and the comment say a `type` statement's value (and a type parameter's bound)
    is evaluated only when its `__value__` (`__bound__`) is first read, not when the script loads or reads the alias.

- [x] **TST-529 · The remake test's fake answers every command, so it can't tell which Python was asked** · `tests/unit/test_install.py:417` · confirmed · found 2026-11-18
  - **Defect.** `monkeypatch.setattr(subprocess, 'check_output', lambda cmd, **kw: 'Python %s\n' % version)` gives the
    version for any command.
  - **Scenario.** A regression making `venv_version` ask `sys.executable --version` instead of the venv's python (always
    3.12+, past the check at the top of `install.py`) would keep a venv a 3.10 made, the bug item 105 fixes, and this
    test would still pass, as would `test_rerun_repairs_a_venv_whose_python_is_gone` (the link is missing, so
    `check_output` never runs) and `test_rerun_keeps_a_working_venv`.
  - **Fix.** Answer only `[module.venv_python(venv), '--version']` and fail on any other command (`pytest.fail(repr(cmd))`).
  - **Resolution: done.**
    - **Test:** the remake test's fake answers only `[venv_python(venv), '--version']`, and fails the test on any other
      command; it answers 3.12.10 once the venv was made again. Seen guarding: with `venv_version` changed to ask
      `sys.executable`, the test failed ("asked ..."); put back, it passes.

- [x] **TST-530 · The docs say ruff reports the syntax 3.9 lacks in the five scripts; it misses some** · `tests/unit/test_lint.py:28-30`, `ruff.toml:36-38`, `AGENTS.md:159`, `DECISIONS.md:58` · measured · found 2026-11-18
  - **Defect.** "ruff checks them as 3.9, so it reports the syntax 3.9 lacks". Measured with ruff 0.17.3 and
    `--stdin-filename install.py`: `a[e := 0]` (an unparenthesized walrus in a subscript, 3.10) draws only F821, no
    `invalid-syntax`, while `/usr/bin/python3` 3.9.6 refuses it with a SyntaxError; `match` is reported. The test checks
    the config's text only.
  - **Scenario.** Such a line in `client/sd_run.py`, written on a machine with no Python 3.9 (Windows, where
    `test_each_script_refuses_a_real_python_3_9` skips), passes lint; a stock Mac's `python3 sd_run.py` then prints a
    SyntaxError instead of the refusal. The final check on this Mac (3.9.6 installed) would catch it.
  - **Fix.** Narrow the sentences: "most of the syntax 3.9 lacks; test_old_python.py's run on a real Python 3.9 catches
    the rest" (`test_lint.py`, `ruff.toml`, AGENTS.md). DECISIONS.md's wording takes the user.
  - **Resolution: done.** The sentences say "most of the syntax 3.9 lacks", with test_old_python.py's run on a real
    Python 3.9 for the rest: `test_lint.py`'s docstring (naming `a[e := 0]`), the `ruff.toml` comment, AGENTS.md and
    DECISIONS.md (its wording with the user's yes to address all the findings).
  - Questioned by TST-533 (2026-11-18).

- [x] **TST-531 · "Runs only on Python 3.12" reads as exactly 3.12, and "uninstall.py needs a system Python 3.12" says more than the code** · `DECISIONS.md:52`, `:59-60`, `AGENTS.md:155-156`, `install.py:14`, `uninstall.py:20`, `client/sd_run.py:12`, `scripts/review_lookup.py:12`, `scripts/read_crash_dump.py:23` · confirmed · found 2026-11-18
  - **Defect.** The check is `sys.version_info < (3, 12)`, accepting 3.13 and later, and the plugin and helpers run on
    Designer's 3.13 (AGENTS.md, three lines above). And `uninstall.py` with the venv's Python only prints a note and goes
    on (`uninstall.py:389-395`; `test_uninstall.py:251-256` runs it so): only on Windows can't its files be deleted
    while it runs. README.md:391 says it as advice, which holds.
  - **Scenario.** A reviewer reading DECISIONS.md literally takes the plugin's 3.13 for a conflict, or a user reads the
    uninstaller as unusable from the venv on macOS.
  - **Fix.** "runs only on Python 3.12 or later" in the five scripts' comment, AGENTS.md and DECISIONS.md's title; "so it
    should run on a system Python 3.12+, not the venv's (it says so when it does)" for the uninstaller. The DECISIONS.md
    wording is the user's (reworded with them 2026-11-18), so it takes their yes. Two reviewers found it.
  - **Resolution: done** (the user's yes to "3.12 or later", 2026-11-18). "runs only on Python 3.12 or later" in
    DECISIONS.md's title, AGENTS.md and the five scripts' comment; DECISIONS.md says `uninstall.py` "should run on a
    system Python 3.12 or later, not the venv's (it says so when it does)".

- [x] **INS-44 · The uninstall command can name a Python that doesn't exist, or won't later** · follows INS-42, generation 2 · `install.py:171-181`, used at `install.py:107` and `uninstall.py:393` · confirmed · found 2026-11-18
  - **Defect.** `system_python` gives `os.path.join(sys.base_prefix, 'bin', 'python3')` from the venv's own Python and
    `sys.executable` otherwise:
    - only `make install` links `bin/python3`; `make altinstall` installs `bin/python3.12` alone (CPython's Makefile,
      read here: `install` runs `bininstall`, which makes the `python3` link; `altinstall` runs `commoninstall` only).
      Homebrew installs a `python@3.x` that isn't its `python3` that way;
    - the installer run from another venv (a project's `.venv`, pyenv-virtualenv, uv, conda) writes that venv's Python
      into the skill (a reviewer measured it with a venv made from python.org's 3.12); once that venv is deleted, the
      command fails, though the docstring says "a Python 3.12+ of the system";
    - on Windows `py -3` assumes the py launcher, which a Store, uv or scoop Python may lack, and `PY_PYTHON3` or py.ini
      can pin `-3` to an older 3.x (older than this branch, whose lines it rewrote).
  - **Scenario.** A Mac user with Homebrew's `python@3.12` beside a newer default runs `mcp_server/venv/bin/python
    uninstall.py`: the note says to run `.../Versions/3.12/bin/python3 .../uninstall.py`, no such file.
  - **Fix.** In any venv (`sys.prefix != sys.base_prefix`), `os.path.join(sys.base_prefix, 'bin', 'python%d.%d' %
    sys.version_info[:2])`, which both make targets install; else `sys.executable`. On Windows `sys.executable`, or
    `base_prefix\python.exe` in a venv. Tests: the versioned name; a case for the installer run from another venv.
  - **Resolution: done.**
    - **Test:** `test_install.py::test_uninstall_runs_with_the_system_python_that_ran_the_installer`, on darwin and win32,
      outside a venv and in one (`sys.prefix` != `sys.base_prefix`): `system_python()` and the skill's command; all four
      failed (`system_python` took this repo's venv and gave `python3` or `py -3`).
    - **Fix:** `system_python()` gives this Python outside a venv; in any venv, the one it was made from:
      `base_prefix/bin/python3.12` (the name both `make install` and `make altinstall` give), `base_prefix\python.exe` on
      Windows. `uninstall_args()` is the one uninstall command, which the skill and the uninstaller's note both print.

- [x] **INS-45 · The installer's note on the venv made again is missing when the old venv's Python was gone** · follows INS-43, generation 2 · `install.py:312` · confirmed · found 2026-11-18
  - **Defect.** `if before:` adds "made again ... install mcp_server/requirements-dev.txt again" only when the old venv's
    Python answered. When it was a dead link (INS-23's case: its base Python was removed or upgraded), `before` is None,
    `--clear` still empties `site-packages` (pytest, mypy, ruff), and the `[2/4]` line says nothing. INS-43's "Also
    covered" took the version clause for the hint: the hint needs no version.
  - **Scenario.** A contributor upgrades Homebrew's Python, re-runs the installer: the venv is made again without the test
    tools, unsaid.
  - **Fix.** Record whether the venv folder was there before; when it was and the venv is made again, add ", made again"
    (with "the one there ran X" when known) and the hint, which could give the command
    (`mcp_server/venv/bin/python -m pip install -r mcp_server/requirements-dev.txt`). Extend
    `test_rerun_repairs_a_venv_whose_python_is_gone` to read the `[2/4]` line.
  - **Resolution: done.**
    - **Test:** `test_rerun_repairs_a_venv_whose_python_is_gone` now reads the `[2/4]` line: "made again" and
      `requirements-dev.txt`; failed on the old line.
    - **Fix:** `main()` notes whether the venv's folder was there; made again over it, the line says ", made again: the
      one there ran X" or "didn't start", and gives the command installing `requirements-dev.txt` with the venv's Python.

- [x] **INS-46 · The uninstaller's note quotes its command for a POSIX shell, which cmd.exe can't read** · follows INS-42, generation 2 · `uninstall.py:393` · confirmed · found 2026-11-18
  - **Defect.** `again = install.shell_command([...])`: `shell_command` is "for Claude Code's Bash tool" (POSIX quoting,
    forward slashes). This note is for whoever runs `uninstall.py`, often a person in a terminal. With a space in the path
    it gives `py -3 'C:/Users/John Smith/Tools/substance-designer-mcp/uninstall.py'`; cmd.exe doesn't take `'` as a
    quote. Before the branch the note said `py -3 uninstall.py`.
  - **Scenario.** A Windows user in cmd.exe copies the note's command: py gets two arguments and fails.
  - **Fix.** Quote for the user's terminal, as `install.register_command` does: `subprocess.list2cmdline` on Windows.
  - **Resolution: done.**
    - **Test:** `test_uninstall.py::test_warns_when_run_with_the_venvs_own_python` gave the venv a base Python whose path
      has a space and expected it between double quotes; failed on the single quotes. Now
      `test_install.py::test_a_command_for_the_users_terminal_is_quoted_for_it` checks the quoting (double quotes for
      'win32', a POSIX shell's elsewhere), and the note test that the note prints that command.
    - **Fix:** `install.terminal_command`, for the user's terminal: `subprocess.list2cmdline` on Windows, `shlex.join`
      elsewhere (it quotes a `'` or `$` in a path, which list2cmdline doesn't). The note and the `[2/4]` line's pip
      command use it.

- [x] **TST-532 · Three of INS-42's doc fixes say more, or other, than the code** · follows INS-42, generation 2 · `mcp_server/GUIDE.md:82`, `AGENTS.md:245-246`, `tests/unit/test_install.py:452`, `README.md:417` · confirmed · found 2026-11-18
  - **Defect.**
    - GUIDE.md's fallback (the guide's core, served on Windows too) now gives `mcp_server/venv/bin/python client/sd_run.py`
      as the command: on Windows the venv's Python is `mcp_server\venv\Scripts\python.exe`.
    - AGENTS.md: "`mcp_server/venv/bin/python` runs all but `install.py` and `uninstall.py`, which make and remove the
      venv", and test_install.py's comment "The venv's own Python can't run it": the venv's Python runs both. The
      installer keeps a usable venv (`system_python` has a branch for that case, tested), and the uninstaller prints its
      note and goes on (`test_warns_when_run_with_the_venvs_own_python`); only on Windows can't it delete its own files.
    - README.md:417's Troubleshooting row still says "run `python3 install.py`", where the `.mcp.json` message it quotes
      now names a Python 3.12+; INS-42's "Also covered" said README's install lines already did.
  - **Scenario.** An agent on Windows copies GUIDE.md's command; one in this repo avoids the venv's Python for the
    installer when it would do.
  - **Fix.** Narrow: GUIDE.md "`client/sd_run.py ...` with a Python 3.12+, such as the venv's"; AGENTS.md "run `install.py`
    and `uninstall.py` with a system Python 3.12+: they make and remove the venv (`uninstall.py` says so when it runs on
    the venv's)"; the test's comment "shouldn't"; README.md:417 README.md:121's "(python3.12 where python3 is older)".
    Two reviewers found parts of it.
  - **Resolution: done.** GUIDE.md: "`client/sd_run.py ...`, run with a Python 3.12+ such as the venv's". AGENTS.md: the
    venv's Python "runs them too, but `uninstall.py` should run on a system Python, as it removes the venv (it says so when
    it runs on the venv's)". The test comment went with INS-44's rewrite of the test. README.md's row: "`python3
    install.py` (`python3.12` where `python3` is older)".

- [x] **TST-533 · TST-530's narrowed sentences say the real-3.9 run catches the rest, without its condition** · follows TST-530, generation 2 · `AGENTS.md:161`, `ruff.toml:39`, `tests/unit/test_lint.py:31` · confirmed · found 2026-11-18
  - **Defect.** "its run on a real Python 3.9 the rest" / "catches the rest": `test_each_script_refuses_a_real_python_3_9`
    skips unless `/usr/bin/python3` or `python3.9` is a 3.9, so on Windows (TST-530's own scenario) and on a Mac whose
    `/usr/bin/python3` isn't 3.9 nothing catches it. DECISIONS.md says "on a Python 3.9 when one is installed".
  - **Scenario.** A Windows contributor reads that the rest is caught.
  - **Fix.** Add "where one is installed" to the three sentences.
  - **Resolution: done.** AGENTS.md, ruff.toml, test_lint.py's docstring and DECISIONS.md say "where a Python 3.9 is
    installed" (DECISIONS.md's with the user's "address them all").

- [x] **TST-534 · Tests call the tuple-typed tools directly with lists, so they pin a call string no MCP call sends and don't guard the orbit and pan messages' fix** · follows SRV-177, generation 2 · `tests/unit/test_view3d.py:49-50`, `:71-74`, `:95` · confirmed · found 2026-11-18
  - **Defect.** `test_the_3d_view_is_set_up_and_shot_in_one_helper_call` asserts `"shoot_3d(%r, 'g', 'Plane', 'Top', 2,
    2.0, [90.0, -30.0], [0.25, 0.5])"`; through MCP the tool now sends `(90.0, -30.0), (0.25, 0.5)`.
    `test_options_out_of_range_are_refused` passes `[181.0, 0.0]`, with which the old `% orbit` formats: reverting
    SRV-177's `list(orbit)` and `list(pan)` keeps every test passing, while through MCP the out-of-range message raises
    "not all arguments converted during string formatting" (a reviewer's check: `'not %r' % (181.0, 0.0)` raises it).
    No live check sends an out-of-range orbit or pan.
  - **Scenario.** A refactor reverts `list(orbit)`: an agent's orbit of 181 gets a TypeError instead of the message.
  - **Fix.** Give `OPTIONS` and the out-of-range cases tuples, as pydantic delivers them (the call string then pins
    `(90.0, -30.0)`), or call through `server.server.call_tool`. Two reviewers found it.
  - **Resolution: done.**
    - **Test:** test_view3d.py's tests of orbit and pan call the tool through `server.server.call_tool` (`_shoot`), with
      the JSON lists an agent sends, so the tool gets what validation gives; the call string pins `(90.0, -30.0), (0.25,
      0.5)`, and the orbit's and pan's messages must say `not [181.0, 0.0]` and `not [1.5, 0.0]`. Seen guarding: with
      `list(orbit)` back to `orbit`, 2 cases failed; put back, they pass.

- [x] **TST-535 · The wrong-count refusal is tested for some of the new aliases only** · follows SRV-177, generation 2 · `tests/unit/test_server.py:529-555` · confirmed · found 2026-11-18
  - **Defect.** The schema tests read `_array`'s `WithJsonSchema`, which only replaces the published schema: the tuple
    type alone refuses a wrong count. The refusal test covers `XY` (orbit, pan), `Box` (node_stats' region,
    preview_maps' crop), `Pixel` (points) and `Color`, not `Four` (`open_graph`'s `rect`, `screenshot_designer`'s
    `crop`, whose length checks this branch removed), `Link` (`links`) or `compare_to_reference`'s regions.
  - **Scenario.** A maintainer shortens `Four` to `Annotated[list[float], _array('number', 4)]`, thinking `minItems`
    enforces the count: every test passes; `rect=[1, 2, 3]` reaches Designer's helper, `crop=[0, 0, 1]` fails with an
    IndexError at `crop[3]`.
  - **Fix.** Make the refusal cases from `_FIXED` and `_FIXED_ITEMS`: for each, one value too few and one too many (one
    bad item for the lists), expecting a validation error naming the parameter and nothing sent.
  - **Resolution: done.**
    - **Test:** `test_a_wrong_number_of_values_is_refused_before_anything_reaches_designer` takes its cases from
      `_wrong_counts()`: for each parameter of `_FIXED` one value too few and one too many, and one bad item for each of
      `_FIXED_ITEMS` (26 cases), each refused naming the parameter, nothing sent. The tables give each parameter's item
      JSON type, which the schema tests check, so the values are of the right type and refused for their number only. Seen guarding: with `Four` made
      `Annotated[list[float], ...]`, the 4 `rect` and `crop` cases failed; put back, they pass.

- [x] **TST-536 · The new skill test fails on Windows: it expects '/'-joined paths that os.path.join builds with a backslash** · `tests/unit/test_install.py:448-458` · confirmed · found 2026-11-18
  - **Defect.** The test sets `sys.platform = 'darwin'` but keeps the real `os.path`: on Windows `system_python` gives
    `ntpath.join('/opt/python3.12', 'bin', 'python3')`, `'/opt/python3.12\\bin\\python3'`; `shell_command` swaps
    backslashes only under `win32`, so the assert on `'/opt/python3.12/bin/python3'` fails (a reviewer's probe of
    `ntpath.join` and the shlex round trip). The Windows simulation keeps `posixpath`, so it doesn't see it. The older
    `test_skill_commands_survive_a_posix_shell[darwin]` has the same pattern, from before this branch.
  - **Scenario.** The unit suite on Windows (AGENTS.md: it runs there) fails on this test.
  - **Fix.** Build the expected paths with `os.path.join`, in both tests.
  - **Resolution: done.** Both tests build the expected paths with `os.path.join`, swapped to '/' only for 'win32', as
    `shell_command` does (`_in_bash`); the new test replaced the one in the finding (INS-44).

- [x] **HLP-188 · The 3D helpers declare lists for orbit and pan, which now arrive as tuples; `_position` prints the tuple** · follows SRV-177, generation 2 · `mcp_server/designer_helpers/shot3d.py:387-388`, `view3d.py:495`, `:506`, `:522`, `:528`, `:636-637`, `:804-805`, `tests/unit/conftest.py:111-112`, `tests/unit/test_shot3d.py:949`, `mcp_server/designer_helpers/core.py:271` · confirmed · found 2026-11-18
  - **Defect.** `orbit: list[float] | None`, `pan: list[float] | None`, `_drags(..., values: list[float], ...)`,
    `_orbit_drags`, `_pan_drags`, `_directions`, and the tests' `View3dOptions` and `set_up` fake: the server's `%r` call
    now sends `(90.0, 0.0)`; mypy can't see across that string. The values are only indexed, zipped or tested, so it runs.
    The helpers receiving the other tuples already declare `Sequence[float]`. And `_position`'s refusal prints the tuple
    ("position must be [x, y], two numbers, not (1e+31, 20.0)") where views.py now prints lists.
  - **Scenario.** A maintainer trusting the annotation writes `orbit + [0.0]` or `isinstance(orbit, list)`: only the live
    suite shows it.
  - **Fix.** `Sequence[float]` there; `list(value)` in `_position`'s message for a tuple. Two reviewers found it.
  - **Resolution: done.**
    - **Test:** `test_batch_fields.py::test_a_bad_position_is_said_as_the_json_sent`: `_position((1e31, 20.0))` must say
      `not [1e+31, 20.0]`; failed with `(1e+31, 20.0)`.
    - **Fix:** `Sequence[float]` for orbit and pan in `shoot_3d`, `_3d_set_up`, `set_3d_view`, `_drags`, `_orbit_drags`,
      `_pan_drags`, `_directions`, and in the tests' `View3dOptions` and `set_up` fake; `_position` prints a tuple as a
      list.

- [x] **SRV-179 · Two functions this branch adds take types looser than what they get** · `mcp_server/server_tools/core.py:176`, `tests/unit/test_designer_helpers.py:62-67` · confirmed · found 2026-11-18
  - **Defect.** `_array(items: str, ...)` is given only `'integer'`, `'number'` or `'string'`: a typo such as `'float'`
    would publish an invalid schema no check sees. `_type_params(node: ast.AST)` reads `getattr(node, 'type_params',
    [])`, an implicit `Any` (AGENTS.md, Typing: look for those in the functions a change adds).
  - **Fix.** `items: Literal['integer', 'number', 'string']`; `_type_params(node: ast.FunctionDef | ast.AsyncFunctionDef |
    ast.ClassDef | ast.Lambda)`, reading `node.type_params` except for a Lambda.
  - **Resolution: done.** `_array(items: Literal['integer', 'number', 'string'], ...)`; `_type_params` takes a def, class
    or lambda and reads `node.type_params` (none for a lambda); mypy passes.

- [x] **SRV-180 · `open_graph` counts `frame=''` as not given, then sends it, and the helper fits a frame titled ''** · `mcp_server/server_tools/views.py:166-173`, `mcp_server/designer_helpers/editor.py:97`, `:275` · confirmed · found 2026-11-18
  - **Defect.** The choose-one check skips `value not in (None, '', [])`, so `''` is not a choice there; the call then
    passes `frame` as it came (`'open_graph(%r, %r, %r, %r, %r)' % (graph, node_id, node_ids, frame, rect)`), and the
    helper tests `frame is not None`: `_fit_area` looks for a frame titled `''` and raises "no frame titled ''". SRV-147's
    rule ('' is no name) applied to `screenshot_designer`'s names (`graph or None`), not here. Found by /simplify's
    altitude reviewer in the second review's fixes; older than this branch.
  - **Scenario.** A client filling optional fields with empty values calls `open_graph(graph='g', node_ids=['a', 'b'],
    frame='')`: the server lets it through (one choice), and the helper refuses it for the empty frame instead of fitting
    the two nodes; `open_graph(graph='g', frame='')` refuses where the whole graph should fit.
  - **Fix.** Send `node_id or None`, `node_ids or None` and `frame or None`, as the check counts them; a unit test of the
    call sent, and a live check that `node_ids` with `frame=''` fits the nodes.
  - **Resolution: done.**
    - **Test:** `test_server.py::test_open_graph_sends_an_empty_choice_as_not_given` (an empty frame; nodes and an empty
      frame; a frame and an empty node_id and node_ids), through `call_tool` with the `sent` fixture: all three failed,
      the call sent `open_graph('g', None, None, '', None)`. Live: editor_open_and_zoom's "an empty frame is not given:
      node_ids fit", in its scratch run, failed with "no frame titled ''; frames: 'Shape'", then passed ("fitted 2
      node(s)"), 17 checks of 17.
    - **Cause:** the choose-one check and the call took the arguments in two ways: the check skipped `''` and `[]`, the
      call sent them as they came.
    - **Fix:** the call sends `node_id or None`, `node_ids or None` and `frame or None`.
    - **Also covered:** the tools' other optional names: `screenshot_designer`'s already pass `or None` (SRV-147); the
      fixed-count parameters take `[]` as None (SRV-178); a grep of `is None` / `is not None` on optional strings in the
      helpers and `server_tools` found only `frame` treating `''` apart from None.
