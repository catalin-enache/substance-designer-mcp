# Plan: optimise AGENTS.md

AGENTS.md is 57,166 characters against the 60,000 cap in `tests/unit/test_guide.py`
(`test_guide_fits_in_one_tool_result`). The cap stands in for Claude Code's 25,000-token limit on one MCP tool
result, because `get_guide()` returns the whole file. The file has to keep growing, so the cap alone is not the
real problem: the file serves two audiences, and each one pays for the other's half.

## Where the characters are (measured 2026-11-07, after the branch's review fixes)

| Section | Characters | Audience |
|---|---:|---|
| Rules that protect the user's work | 1,545 | Designer use |
| Which tool for what | 4,376 | Designer use |
| Undo, timeouts, plugin lifecycle | 1,483 | Designer use |
| Environment facts | 3,047 | Designer use |
| sd API gotchas | 12,601 | Designer use (scripting) |
| Designer UI (Qt) | 5,114 | Designer use (scripting) |
| Library node facts (Designer 16) | 1,498 | Designer use |
| Rendering and verifying | 1,585 | Designer use |
| Example | 1,153 | Designer use |
| Working on this project | 5,454 | Contributors |
| Running the tests | 12,059 | Contributors |
| Keeping the docs current | 1,736 | Contributors |
| Deploying and diagnosing | 4,956 | Contributors |

- Designer use: about 32k. Contributors: about 24k.
- Every Designer session gets the contributor half through `get_guide()`, about 24k characters it never uses.
- Every Claude Code session in this repo loads the whole file automatically as project instructions (about 14k
  tokens), then may load it again through `get_guide()`.
- Claude Code warns about degraded performance once an automatically loaded instruction file reaches 40 KB
  (claudelint's `claude-md-size` rule, https://claudelint.com/rules/claude-md/claude-md-size, uses the same
  threshold). AGENTS.md is 57 KB, already past it.
- About 12k characters sit in parentheses. Many of them are evidence ("measured", "seen once by hand", stress
  counts, pixel values); "measured", "seen once/twice" and "by hand" alone appear 16 times.

## Rejected: splitting AGENTS.md with `@imports`

claudelint's suggested fix for an oversized file is to move sections into `.claude/rules/` files and `@import`
them. That silences the lint, but it saves no context: Claude Code expands imports when the session starts, so the
agent reads the same characters as before. It can't help `get_guide()` either, because the tool returns the
file's raw text. Only content loaded on demand (a separate file served by a tool, a skill, path-scoped rules, a
plain link the agent follows when it needs to) loads less.

## Steps, biggest gain first

### 1. Split the file by audience

- **AGENTS.md** keeps only *Working on this project* and its subsections. That is what other agent tools expect a
  file with that name to hold, and they load it automatically.
- **The Designer guide** moves to a file of its own (proposed: `mcp_server/GUIDE.md`, or `DESIGNER_GUIDE.md` at the
  root), served by `get_guide()` and the resource `designer://agents-guide`.
- Contributors still get the guide: the server's instructions already make them call `get_guide()` before the first
  Designer tool call.
- Effect: each file gets its own budget, and `get_guide()` drops to about 32k right away.

To change:

- `mcp_server/server_tools/core.py`: `AGENTS_MD`, `_agent_guide()`, the `INSTRUCTIONS` text ("full guide
  (AGENTS.md)"), and the resource name, if it should no longer say "agents-guide".
- The guide's opening note and the "Kind of knowledge" table in *Keeping the docs current*: say which file holds what.
- Tests that name AGENTS.md: `tests/unit/test_guide.py` (`_agents_md`, the size test, the uniqueness check across
  AGENTS/README/ROADMAP, which should cover the new file too), `tests/unit/test_review_lookup.py` (around lines 352,
  372, 571, 584, 607), `tests/unit/test_constants.py:73`, `tests/unit/test_server.py:414`.
- Links from README.md, the skills (`.claude/skills/*`), DECISIONS.md and ROADMAP.md that point into sections that
  move.
- The self-test's `get_guide` checks in `tests/test_all_tools/__main__.py` (whole guide returned): only the full
  live run proves these.

### 2. Serve the guide in tiers

- `get_guide()` returns the **core**: the rules, *Which tool for what*, the loop, *Undo, timeouts, plugin lifecycle*,
  *Environment facts*, *Library node facts*, *Rendering and verifying*, *Example*, and the few sd gotchas everyone hits
  (`APIException` derives from `BaseException`, check atomic ids before `newNode`, blend mode numbers).
- `get_guide('scripting')` returns *sd API gotchas* and *Designer UI (Qt)*, about 17.5k, needed only when writing raw
  `sd` or Qt code.
- Enforcement reuses the "guide not read" mechanism (`GUIDE_NOT_READ`, `_session['guide_read']`): until the
  scripting part has been read in the session, `execute_designer_code` and `run_designer_script` put a reminder at
  the top of their results. The guarantee stays the same; the cost is paid only when it is needed.
- Effect: the always-loaded guide is about 15k, less after step 4.
- This changes how tools behave, so it goes test first: unit tests for the new parameter and the reminder, and a live
  check in a scratch run (*Running the tests*). Load the `mcp-builder` skill first, as tool changes require. Add the
  tool table entry in README.md.

### 3. Move facts that only matter to whoever maintains a tool

The test for each fact: would an agent *using* the tools act differently if it knew this? If not, the fact goes into
the docstrings or comments of the module that does the work, or into README.md's *How it works*. The guide keeps a
one-line pointer. Candidates:

- how several Designers are kept apart (single-instance IPC, the socket path length, `TMPDIR`, `CFFIXED_USER_HOME`,
  plugin loading from `SBS_DESIGNER_PYTHON_PATH`): to `server_tools/lifecycle.py`; the guide keeps "`launch_designer(port=)`
  runs Designers side by side, one per port";
- the internals of quitting (hidden `QMainWindow`, the licence-check crash, the `QThreadPool` hang, SIGTERM/SIGKILL):
  to `lifecycle.py`; the guide keeps the rule (never close the user's Designer);
- the portal file-edit steps, and the `node_align_tools` crash: to the `set_link_display` module; the guide keeps
  "uses the file-level edit pattern; use it for other things the API can't do" plus its checklist;
- the clipboard trick behind 3D screenshots, and the Home screen button: to the screenshot and `open_graph` code;
- the inheritance numbers in the API versus the .sbs file: to the code that reads .sbs files.

Before moving a fact, check that a self-test check or unit test still names it, so it stays findable.

### 4. Strip the evidence notes

- The "designer facts" checks already prove the claims. The evidence (what was measured, how often, pixel values,
  stress counts) moves into each check's docstring; the doc states the fact and, where useful, names the check.
- Keep a short note where the evidence changes what an agent should do, such as "seen once: restart Designer after
  such experiments".
- Effect: roughly 10–15% across both files.
- Watch out: the docs rule "A claim in these docs without a test is a guess" still applies. Every fact kept must
  still map to a check.

### 5. Turn *Running the tests* (11.7k) into a skill

- New skill, for example `.claude/skills/live-check/`, holding: `alone.run` and its `needs`, scratch runs, the order
  (fail, then pass), what a scratch run can't prove, the final check, the suites, designer scripts versus inline
  snippets.
- AGENTS.md keeps a short paragraph of hard rules:
  - test first, every change comes with a test;
  - only the agent changing the code runs tests, and reviews run none;
  - the full suites run only when the user asks;
  - the lint and types command, and the docs-only command (`test_review_lookup.py` checks it appears once);
  - load the skill before writing or running a live check.
- Update the skills that point at *Running the tests* (`address-review`, `project-code-review`).
- Alternative considered: a path-scoped rule (`.claude/rules/` with `paths: tests/**` frontmatter) loads on its own
  when Claude works on matching files, so it doesn't depend on the agent choosing to load a skill. A skill still
  fits better: rules are a Claude Code feature, while AGENTS.md also serves other agent tools, and an agent changing
  `mcp_server/` or `plugin/` needs the test procedure before it touches anything in `tests/`.

### 6. Re-base the size test

- One cap per file, and one cap per tier of the guide.
- AGENTS.md, which Claude Code loads automatically: under 40 KB, the size at which Claude Code warns (the ~20k after
  step 1 leaves room). The guide served by `get_guide()` keeps the 60k cap, which stands in for the limit on one MCP
  tool result.
- Optionally count tokens instead of characters: at about 4 characters per token, 57k characters is roughly 14k
  tokens, well under 25k, so the current cap is conservative. A character cap with a stated ratio is simpler and
  needs no tokenizer.

## Expected result

| | Now | After 1 + 4 | After 1–5 |
|---|---:|---:|---:|
| `get_guide()` (always) | 57k | ~28k | ~12–15k |
| `get_guide('scripting')` | – | – | ~15k |
| AGENTS.md (auto-loaded in this repo) | 57k | ~20k | ~8–10k |

## Order and risk

1. **Steps 1 and 4 first:** mechanical, low risk. Mostly docs, plus the path in `core.py` and the tests that name
   the file. Run the docs-only tests with lint and types (AGENTS.md, *Running the tests*), plus the unit tests of
   `core.py`'s guide code.
2. **Step 3:** docs plus docstrings, no behaviour change. Run the existing tests of the touched modules before and
   after.
3. **Step 2:** a behaviour change, test first, with a live check in a scratch run.
4. **Step 5:** a new skill; docs-only tests.
5. **Step 6** goes with step 1 (per-file caps) and step 2 (per-tier caps).

The full suites run once at the end, when the user says the work is done.
