# AGENTS.md: changing this project

For AI agents working on this repository. Driving Substance Designer (the tools, the rules that protect the user's
work, the `sd` API and Designer facts) is in [mcp_server/GUIDE.md](mcp_server/GUIDE.md): `get_guide()` serves its core, `get_guide('scripting')` the `sd` API part.
Read its rules before touching the bridge, the token or the plugin, or running anything against Designer, and its
scripting part before writing code that runs inside Designer.

Push, or merge into `main`, only when the user asks; the repository is public. The lead commits on a branch other than
`main` as often as it sees fit, without asking, and before each review (the `project-code-review` skill, Scope). A
commit to `main` waits for the user's request. No other agent commits (the user, 2026-11-19).
**There is no CI and none is planned**: don't add GitHub Actions or other CI.

## Working on this project

How the plugin, server, helpers and command-line tools fit together: README.md, **How it works**.

**Rules for some files only** are in `.claude/rules/`. Claude Code loads one, once per agent and again after a
compaction, when a Read or a Write touches a file the rule's `paths:` match, or a Bash `cat`, `head`, `tail`, `sed -n`
or `grep` prints its lines unpiped. A `wc -c`, a piped command and PyCharm's `read_file` load none (measured 2026-11-19
and 2026-11-20; the compaction, 2026-11-20). So read the one for the files you work on:

- `python.md`: every Python file (PyCharm's tools first for navigating and checking code, typing, `Any`, strings of
  code, keeping each file to its main logic, `/simplify` once the tests pass, the commands after editing);
- `docs.md`: every Markdown, Python and tool config file (where each kind of knowledge goes, keeping the docs current,
  writing docs, docstrings and comments);
- `docs-tests.md`: a change of Markdown, a comment or a docstring;
- `unit-tests.md`: `tests/unit/`;
- `waits.md`: the code that waits on Designer, Qt or the OS (callbacks, never measured times);
- `designer-code.md`: the server, the helpers, the plugin and the bridge (the guide's file and the server's
  instructions, the environment variables included);
- `changing-tools.md`: the tools and the helpers (the `mcp-builder` skill, `.claude/skills/mcp-builder/`, before
  designing or changing a tool, and its defaults this project doesn't follow);
- `live-checks.md`: the live self-test (scratch runs, and the `live-check` skill, `.claude/skills/live-check/SKILL.md`);
- `install.md`: the installer and the registration.

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
and tests show? Fix what you find and look again, until a fresh look finds nothing a reviewer could report that is
worth a fix (**Keep it simple**, below).

**Keep it simple** when you decide in the user's name how something is done: choose the way that won't make the code
complex in the long run. Don't address very extreme cases that won't likely happen and need complex code. Prefer
simplicity whenever the complexity weighs far more than the value added (the user, 2026-11-23: "chose simplicity
(KISS)"; "Dont be tempted to fix extreme cases that wont likely happen").

**A branch's plan is in PLAN.md** (repo root), the lead's: the main session, which talks with the user. If it is
there, read it before anything else, at the start of a session and after a compaction, and continue from it. How the
lead writes it, keeps it current and ends it with the branch: the `delegate` skill. A subagent never writes PLAN.md. It
reads it only when its brief names it, and a reviewer never: it holds the lead's own account of the work.

**Reviews go in REVIEW.md** (repo root, committed with the changes it records), the memory per branch: the lead
writes it from the reviewers' and the developer's reports. DECISIONS.md is the memory for the whole project. The
skills hold its rules: `project-code-review` (`.claude/skills/project-code-review/`) to review, `address-review`
(`.claude/skills/address-review/`) to fix or answer findings, and `cleanup-review` (`.claude/skills/cleanup-review/`)
for a cleanup, which only the user starts, by asking for one explicitly.

### Running the tests

**Tests run at two stages** (DECISIONS.md, Project rules). While working, the agent that changes the code runs the
tests of its own work only: unit tests by name and scratch runs, never a full suite. At the end, the `runner` agent
runs the full suites, the final check, when the user asks. A review runs none, unit or live (the `project-code-review` skill
or the built-in `/code-review`): reviewers read the code and the tests and report what reading can't settle as a
suspicion, with what would settle it; the agent leading the review settles each before anything is recorded, with
scratch probes run as the `project-code-review` skill's **Who settles what** says.

**The full suites run only when the user asks:** the whole unit suite (`pytest` with no test ids) and a whole run of the
live self-test (`tests/test_all_tools`). Never start one on your own: not for TDD, not after a fix, not between
reviews. When the reviews look converged, the user decides what comes next (the `project-code-review` skill, step 7).
The final check is both suites in full, just before merging into `main`; both must pass, a test that fails at random
and passes rerun alone counting as passed (DECISIONS.md, Project rules).
Docs changed alone run the docs tests instead, the final check included (`.claude/rules/docs-tests.md`). The command
for each run the user asks for: the `live-check` skill (`.claude/skills/live-check/SKILL.md`), The suites.

**Unit tests while working:** only those added or modified for the change (for a refactor, the existing tests of the
code it touches), and those that read the source of the files it changes (`.claude/rules/python.md`), as often as
useful. **Lint and types always run too**, and the docs tests with any change of Markdown, a comment or a docstring,
alone or with code. The commands: `.claude/rules/python.md` and `.claude/rules/docs-tests.md`. The rules for Python and
for the unit tests: `.claude/rules/python.md` and `.claude/rules/unit-tests.md`.

### Delegating to subagents

The project's agents are defined in `.claude/agents/`. Each loads AGENTS.md and the user's memory index, `MEMORY.md`
(not the memory files it links), but not the conversation. Each reports to the lead, which decides what comes next.
The lead is the main session, the one that talks with the user. Of these agents, only the `developer` starts others:
`/simplify`'s cleanup agents on its own change, and `analyst` agents for research or a web search. They report to the
developer and start none (the user, 2026-11-19). In a subagent, the messages come from the agent that started it, not
from the user. Where a file tells an agent to ask, tell or propose something to the user, a subagent reports it to the
lead, which asks the user. Where this file, or a rule or skill it points to, waits for the user's word (the full
suites, a decision), the lead waits for it before the brief, and the brief says the user gave it. The `runner` runs the
full suites on such a brief without asking again.

**The user's standing request is that the lead delegates by the `delegate` skill's table without asking first each
time** (the user, 2026-11-18). Before an expensive or long unit starts, the lead still tells the user what it will
cost, how long it will take and what comes back: from outside, a long silent run and a runaway one look the same.

**The lead reads a thing itself when it knows in advance the output will be small:** a tiny file, a few known lines,
an output capped in the call. When it can't tell the size in advance, it asks an `analyst`. An analyst for a tiny
read costs more tokens than the context it saves (the user, 2026-11-19). **Keep it yourself:**

- a handful of tool calls, or a lookup whose target is known;
- the read a claim depends on: the lines it quotes, which are known and small. Also the one measurement that settles a
  disagreement between two reports. The cost of reading is never a reason to skip it.

The lead never fetches or searches the web, even one known page: it always asks the `analyst` (the user,
2026-11-19).

**Any other output of unknown size is capped in the call itself,** or measured first: a count (`grep -c`, `wc -l`),
`head` or `tail`, `-q`, `--stat` or `--shortstat`, `git log --oneline -20`, a tool's own limit parameter, or `wc -c`
before the read. When the answer needs more than that cap shows (many files, the history, a long log), ask the
`analyst`. Monitor too: its events land in the lead's context, so the lead filters its command to the few lines it
acts on. A log to read goes to the `analyst`, and waiting for an end is a background Bash that exits on it (the
`delegate` skill, `.claude/skills/delegate/SKILL.md`, A long run).

**Hooks keep large reads out of the lead's context,** in every main session, and let a subagent's calls through. They
refuse the lead's web fetches and searches, a read that returns over 20 KB, and a Bash command that would print over
20 KB of files. They add a note to an output of 8,000 characters or more, and to the lead's 8th reading call of a turn,
and each 8th after it. Their rules: the docstring of `.claude/hooks/large_reads.py`.

`.claude/settings.json` also caps a successful command's output at 10,000 characters (`bashOutputMaxChars`), in the
subagents too: past it, the context gets the path of a file holding the whole output and a 2 KB preview, and the part
needed is read from that file. A failing command's output isn't capped by it (`large_reads.py`'s docstring).

**Before starting or resuming an agent, and before continuing the loop from PLAN.md (a session's start, a compaction),
load the `delegate` skill** (`.claude/skills/delegate/SKILL.md`): which agent does what, the lead's loop from PLAN.md
to the merge, what a brief holds, and how a changed agent file reaches the agents. Load it, like any skill, again
before following it when its file may have changed, or a compaction came, since it was loaded: the copy in the context
keeps the text as loaded, and a compaction may cut it short or drop it (Claude Code's docs, Skills, Skill content
lifecycle).

### Deploying and diagnosing

- **Fresh clone, or a deleted `mcp_server/venv`:** run `python3 install.py` (Windows: `py -3 install.py`) first;
  without the venv the server can't start, and the `.mcp.json` command says so in `/mcp`. Then the user reconnects
  `/mcp`. `designer_status` shows which Python and library versions the server runs on.
- **The `python3 ...` commands** in these docs and the skills need a `python3` of 3.12 or later (DECISIONS.md, Project
  rules); where it is older, each script says so. `mcp_server/venv/bin/python` runs them too, but `uninstall.py` should
  run on a system Python, as it removes the venv (it says so when it runs on the venv's; REVIEW.md INS-42).
- **The server, the helpers, the plugin and the bridge,** how a change reaches Designer, the guide's file, the server's
  instructions and the environment variables included: `.claude/rules/designer-code.md`. **The installer and the
  registration:** `.claude/rules/install.md`.
- **An edited agent file, or an edited AGENTS.md,** and the agents it reaches: the `delegate` skill
  (`.claude/skills/delegate/SKILL.md`).
- **A Designer that crashed or hung:** the `live-check` skill (`.claude/skills/live-check/SKILL.md`).
- **When tools fail:** match the symptom in README.md, Troubleshooting, and try `read_designer_log`. If Designer isn't
  running or answering, ask the user to open it, or to save, close and reopen it (in tests and work on this project,
  `launch_designer`). If the bridge accepts connections but never answers, or a tool is missing in Claude Code, only the
  user can fix it (restart Designer / reconnect `/mcp`): tell them.
