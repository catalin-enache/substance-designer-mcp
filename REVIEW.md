# REVIEW.md: review findings

Findings from code reviews of this repository, kept across several reviews as a file in the project. How many is
the user's choice, most likely the life of a feature branch; the history stays in git for good.

This file is the **memory per branch**. The lead writes it from the reviewers' and the developer's reports, as in a
PR review: a finding is raised, then fixed or answered with why not, so the next reviewers know what was settled and
don't raise it again. Once the branch is merged it can be cleaned up. `DECISIONS.md` is the memory for
the whole project.

A new review **appends** its findings to the matching severity section and adds itself to the log; it never removes
or rewrites existing entries. An entry is checked when it is resolved, always with a resolution line that starts
with one of these wordings: `done`, `not a bug`, `not reproducible`, `won't fix`, `moved to ROADMAP.md (item N, the
user, <date>)`. Format and rules: `.claude/skills/project-code-review/` (SKILL.md, TEMPLATE.md).

**Confidence.**
- *Confirmed*: the lead agent read the code and the defect is visible in it, as quoted.
- *Measured*: reading couldn't settle it, and the lead agent's scratch probe in Designer showed it (the entry gives
  the probe and what it measured; the `project-code-review` skill). A failure of the final check is *measured* too:
  the entry gives the failing test and its output. A finding is one or the other, never a guess.

**Found by.** An entry's title line ends with who found the finding and the model that agent ran on:
`found 2026-11-20 by a reviewer (Sonnet)`, `by the developer (Opus)`, `by the runner (Sonnet)` or `by the lead (Opus)`.
Two reviewers who found it are both named: `by two reviewers (Opus, Sonnet)`, or `by two reviewers (Sonnet)` when
both ran on one model. The model is the one the agent ran on: its file's, or the one the lead passed on the Agent call.
Older entries don't have it.

**IDs.** One prefix per area, numbered on: **PLG** plugin and bridge protocol, **SRV**
`mcp_server/server.py`, `server_tools/` and `designer_preferences.py`, **HLP** `mcp_server/designer_helpers/`, **INS** installer, uninstaller,
command-line client, example and `scripts/`, **TST** tests and the docs outside `.claude/`, **AGT** everything in
`.claude/` (agents, hooks, skills, rules, `settings.json`). A finding over several files takes the prefix of its first
location. A new area gets a new prefix, added here.

**Last used:** PLG-45, SRV-183, HLP-207, INS-46, TST-639, AGT-110.

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
| Medium-high | 0 | 2 |
| Medium | 0 | 0 |
| Low-medium | 0 | 18 |
| Low | 0 | 174 |
| **Total** | **0** | **194** |

## Reviews by model

What each model found in each review round, the time it took and the tokens it spent. After each round, the lead adds
that round's rows, every column filled: one row per model that ran, and a `settling` row when the lead used agents to
settle suspicions (a runner's probes, analysts). The last row is **Total**, which the lead updates after each round and
each developer run to sum every row above it, and adds after the first round:

- **Review:** the round's date, and which round it is.
- **Model:** the model the row's agents ran on, `settling`, or `<model> (developer)` (below).
- **Instances:** how many agents the row counts.
- **Real findings:** the real findings the round's reviewers on the row's model found, counted from each finding's
  `found ... by <who> (<model>)` (**Found by.**, above). The cell gives their count, then in brackets the count of
  each severity among them, most severe first: `9 [1 Low-medium, 8 Low]`, or `0` for none. The **Total** row sums each
  severity too.
- **Found only by this model:** how many of those no other row of the round found, written the same way.
- **Tokens:** the tokens of the row's agents, together.
- **Time:** the round's slowest agent of the row.

The developer gets a row for each run: every Agent call to a `developer`, and every resume of one with SendMessage
that ends in a report (the user, 2026-11-20). Its **Review** names the work, such as `2026-11-20, the nineteenth
review's fixes`. Its **Model** is `<model> (developer)`, such as `Opus (developer)`, and its **Instances** is 1. Its
two findings cells count the new problems it found that the lead settled as real, or `0` for none. Its **Tokens** and
**Time** come from its completion notice, as a reviewer's do. For a resumed developer, the Tokens are those its notice
adds since that agent's previous notice, and the Time is that run's duration, in minutes. A finding the runner or the
lead found is recorded on its title line only, in no row.

The figures are the usage each agent's completion notice gives (its tokens and duration). The lead's own share isn't
in it. A cleanup empties the table at its end, and git keeps the rows (the `cleanup-review` skill).

| Review | Model | Instances | Real findings | Found only by this model | Tokens | Time |
|---|---|---|---|---|---|---|
| 2026-11-20, thirteenth (the whole branch) | Opus | 4 | 8 [8 Low] | 5 [5 Low] | 1,021,051 | 17 min |
| 2026-11-20, thirteenth (the whole branch) | Sonnet | 4 | 7 [7 Low] | 4 [4 Low] | 971,644 | 11 min |
| 2026-11-20, the thirteenth review's fixes | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 391,392 | 31 min |
| 2026-11-20, AGT-95's fix | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 30,194 | 5 min |
| 2026-11-20, AGT-96's fix | Opus (developer) | 1 | 0 | 0 | 23,219 | 4 min |
| 2026-11-20, fourteenth (the thirteenth's fixes) | Sonnet | 2 | 4 [4 Low] | 4 [4 Low] | 373,952 | 8 min |
| 2026-11-20, the fourteenth review's fixes | Opus (developer) | 1 | 0 | 0 | 45,116 | 9 min |
| 2026-11-20, step 7 rewritten to the review flow | Opus (developer) | 1 | 0 | 0 | 33,597 | 6 min |
| 2026-11-20, the finder per finding and the table by model | Opus (developer) | 1 | 0 | 0 | 79,635 | 11 min |
| 2026-11-20, fifteenth (Step C, the review flow and REVIEW.md's fields) | Sonnet | 2 | 9 [1 Low-medium, 8 Low] | 9 [1 Low-medium, 8 Low] | 279,469 | 5 min |
| 2026-11-20, the fifteenth review's fixes | Opus (developer) | 1 | 0 | 0 | 53,748 | 10 min |
| 2026-11-20, sixteenth (the fifteenth's fixes) | Sonnet | 1 | 4 [4 Low] | 4 [4 Low] | 161,001 | 7 min |
| 2026-11-20, seventeenth (the entire branch) | Opus | 4 | 9 [1 Low-medium, 8 Low] | 9 [1 Low-medium, 8 Low] | 1,119,339 | 18 min |
| 2026-11-20, the seventeenth review's fixes | Opus (developer) | 1 | 0 | 0 | 437,447 | 33 min |
| 2026-11-20, eighteenth (the seventeenth's fixes) | Opus | 2 | 3 [3 Low] | 3 [3 Low] | 360,058 | 10 min |
| 2026-11-20, the eighteenth review's fixes | Opus (developer) | 1 | 0 | 0 | 44,392 | 5 min |
| 2026-11-20, nineteenth (the entire branch again) | Opus | 4 | 4 [4 Low] | 4 [4 Low] | 1,114,949 | 19 min |
| 2026-11-20, nineteenth (the entire branch again) | settling | 2 | 0 | 0 | 46,031 | 0 min |
| 2026-11-20, the nineteenth review's fixes | Opus (developer) | 1 | 0 | 0 | 240,730 | 13 min |
| 2026-11-20, the user's three decisions | Opus (developer) | 1 | 0 | 0 | 214,146 | 13 min |
| 2026-11-20, the fifth resolution wording | Opus (developer) | 1 | 0 | 0 | 80,616 | 8 min |
| 2026-11-20, a `read_file` past a file's end | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 30,304 | 3 min |
| 2026-11-20, AGT-108's fix and five answers | Opus (developer) | 1 | 0 | 0 | 147,861 | 18 min |
| 2026-11-20, Show the plan first | Opus (developer) | 1 | 0 | 0 | 6,876 | 1 min |
| 2026-11-20, DECISIONS.md's skill paths | Opus (developer) | 1 | 0 | 0 | 6,749 | 2 min |
| 2026-11-20, the 300 ms in the wait rule | Opus (developer) | 1 | 0 | 0 | 9,624 | 2 min |
| 2026-11-20, the window-state settles in the wait rule | Opus (developer) | 1 | 0 | 0 | 8,596 | 2 min |
| 2026-11-20, twentieth (the user's answers, `982a9cc..91ec8f3`) | Sonnet | 2 | 4 [4 Low] | 4 [4 Low] | 345,623 | 9 min |
| 2026-11-20, the twentieth review's fixes, the column renamed, Monitor | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 84,022 | 15 min |
| 2026-11-20, AGT-110's fix | Opus (developer) | 1 | 0 | 0 | 4,971 | 1 min |
| **Total** | all | **47** | **56 [2 Low-medium, 54 Low]** | **50 [2 Low-medium, 48 Low]** | **7,766,352** | **296 min** |

## Review log

### 2026-11-19: the agent-delegation branch's diff (uncommitted, against main)

- **How:** three `reviewer` agents, the agent's first use (ROADMAP item 102): one for the reading agents' guard, one
  for the size checks against large reads, one for the agents and the docs that route work to them. No tests run. The
  lead's probes, none in Designer: plain Python in the scratchpad loading the two hooks; `sort` and `uniq` run in a
  scratch folder; mypy run on a scratch tree; this session's subagent transcripts read for what each agent was given
  and called; one `analyst` running four `cd` commands through the guard; a Bash call printing 8,100 characters and
  exiting 1; PyCharm's `read_file` on a probe notebook and a probe PNG (all deleted afterwards). Settled as wrong:
  - "the developer can't start agents, so its `/simplify` can't run": measured false. The developer's transcript
    holds 8 Agent calls, and four `analyst` agents ran at spawn depth 2;
  - "the wildcards in `tools` (`mcp__pycharm__*`, `mcp__substance-designer__*`) may not be honoured": measured false.
    The developer's transcripts list PyCharm's `apply_patch` and Designer's `launch_designer` among its tools;
  - "the analyst's 'you don't design solutions' keeps `/simplify`'s helpers from proposing changes": false. Two
    `/simplify` runs with `analyst` helpers on this branch returned concrete simplifications, applied (7 in the
    developer's run);
  - "`/simplify`'s fixes get no test run before them": false. `/simplify` skips a fix well outside the diff, so its
    fixes touch the change's own code, whose last passing run is the run before them, as AGENTS.md says;
  - "PyCharm's `read_file` of a notebook or a PNG goes unmeasured by the exemption meant for Read": measured. PyCharm
    returns a notebook's cell sources as `#%%` cells, not its JSON, so the file's size wouldn't measure it either, and
    it refuses a PNG ("Could not get document");
  - "the guard let `cd <repo> && ...` through": measured. Claude Code drops a leading `cd` to the working directory
    before the hook sees the command; `cd /tmp && pwd` and `cd <repo>/tests && pwd` were blocked.
- **Not verified:** the memory index's slug rule ("each `/` turned into `-`", in the agent files) for a path holding
  `.` or `_`: no project folder under `~/.claude/projects` has one here. A session started in such a folder would show
  it.
- **Resolutions assessed:** none: `REVIEW.md` held no findings.
- **Findings:** AGT-1 to AGT-15 and TST-557 to TST-568: 2 Medium-high, 5 Low-medium, 20 Low. Two reviewers found the
  implicit `Any` of TST-563, in different files: merged.
- **Suggested order:** AGT-1 and AGT-2, the two writes through the guard; TST-557, the fail-open test the lead's own
  fix weakened; AGT-3; TST-558; TST-559 and TST-560, which the user may want to decide on; then the Low ones by file:
  the guard (AGT-12 to AGT-14, the guard's half of TST-562), the size checks (AGT-4 to AGT-9, TST-561, the rest of
  TST-562), the agents and docs (AGT-10, AGT-11, AGT-15, TST-565 to TST-568), the types (TST-563, TST-564).
- **Longest chain:** none; every finding is generation 1.
- **Checked and found fine:** the guard's tokenizer against zsh (quotes, backslashes, `|&`, `&|`, `&!`, `&>`, the two
  redirections it lets through, `#`); no alias or function of the user's shadowing an allowed program; bfs's full
  action list against `words`; ugrep's options that run, write or wait (Claude Code's `grep` wrapper also sends
  `--filter`, `--pager`, `--view`, `--config`, `---` and `--save-config` to macOS's grep; `-Q` reaches ugrep);
  `_second_file` against macOS uniq for `--`, `-` and options after the first file; git's `-c`, `-C`, `-p`, and
  environment assignments refused; the guard's hook command blocking on a missing venv, an exception and an unreadable
  call; the agents' `hooks:` blocks equal to `GUARD_HOOK`. The size checks: failing open (the settings command, `main`
  catching every exception, exit 2 only after a refusal is printed); no hang on a FIFO or device (`S_ISREG`,
  `isfile`); Read's and PyCharm's ranges and errors against the measurements; BSD `head`, `tail` and `sed` forms; `cd`
  chaining; trailing `/` and `/.`; URLs and archive entries; PLAN.md by `samefile`; the note's threshold, its skip of a
  saved output and its JSON. The agents: a reviewer had only Bash, Read and PyCharm's reading tools (no Edit, Write,
  Agent or Designer tool: item 102's check), and the guard blocked its `echo`, `git branch` and `which`; every rule
  of the old step 3 of `project-code-review` is in `reviewer.md` (AGT-15 aside); the follow-up chains and the
  convergence rule agree between the skill and `reviewer.md`; `DOC_TESTS` and the docs-only command agree;
  `test_agents.py`'s frontmatter reader and the skills check; ROADMAP item 110's figures.
- **Unspecified (no doc decides; raised with the user):** the runner's Write and unguarded Bash, the user's choice
  recorded only in PLAN.md, which the merge deletes; a review through the built-in `/code-review` doesn't use the
  `reviewer` agent; the `address-review` steps that talk to the user, when the developer follows them; a subagent's
  harness tells it that no agent's message is the user's consent, while AGENTS.md has the brief say the user gave it
  (the runner and the full suites); both hooks size a Bash call with `run_in_background` as a foreground one; WebStorm's
  `read_file` and PyCharm's search tools aren't covered by the size checks; the guard refuses `git status` while
  `git diff` refreshes the index as it does, and refuses `git -C`.

### 2026-11-19: second review of the agent-delegation branch (uncommitted, against main)

- **How:** three `reviewer` agents, one each for the guard, the size checks, and the agents with their docs, each told
  not to read PLAN.md and to read AGENTS.md from disk (AGT-11). No tests run. The lead's probes, none in Designer: `tail
  +1f`, `tail +1F` and zsh's `ls 2>&1x` in a scratch folder; the guard's answers in plain Python; Read in the lead's
  session (its line prefix; a relative path after `cd tests/unit`; a BMP, a TIFF and a HEIC; a 3,000-character line); a
  `runner` starting two background tasks; the lead's TaskStop on one of them; `git show --stat` of 4db5fd5 and 9446b2c;
  the tools reference's output limits. Settled as wrong:
  - "Read resolves a relative path from the session's folder after a `cd`": measured false. After `cd tests/unit`,
    Read found `conftest.py` and not `tests/unit/conftest.py`: the call's `cwd`, as the hook has it;
  - "Read shows other image formats as images": measured false. Read refuses BMP, TIFF and HEIC as binary files, so
    nothing reaches the context either way;
  - "Read cuts lines over 2,000 characters": measured false. A 3,000-character line came back whole;
  - "user choices recorded outside DECISIONS.md (the untrusted folder, the runner's brief, `~`, `git status`, `-C`)":
    not a defect. The `address-review` skill (Recording decisions): a choice that AGENTS.md or the code's comments
    already answer stays there.
- **Not verified:** none.
- **Resolutions assessed:** all 27 of the first review, by the reviewers (each for its area) and the lead (the branch's
  tests rerun, 584 passed; the guard on the fixed forms). They hold except where a finding here questions them:
  TST-560 (TST-569), AGT-12 (AGT-17), AGT-9 (AGT-19), TST-559 (AGT-21), TST-566 (TST-570), TST-565 (TST-571), TST-562
  (TST-573).
- **Findings:** AGT-16 to AGT-22 and TST-569 to TST-573: 4 Low-medium, 8 Low. Not converged (step 7 of the skill):
  a Low-medium finding gets another review once fixed.
- **Suggested order:** AGT-16 and AGT-17 (the guard's hang and its background calls); AGT-18 (the runner can't stop a
  run); TST-569 (PLAN.md and the merge); then the Low ones: AGT-19, AGT-20, TST-573 (the hooks and their tests),
  AGT-21, AGT-22, TST-570, TST-571, TST-572 (the docs).
- **Longest chain:** generation 2 (seven findings follow a first-review resolution).
- **Checked and found fine:** the 27 resolutions above; the leading `~` for `-C` (only index 0 skipped, `~[...]` still
  refused); every other way zsh makes one word several needs a character the guard refuses or a global alias, and the
  shell snapshot runs `unalias -a`; no reader has an option that writes or starts a harmful program; the hook commands
  block (guard) or pass (size checks) on every failure; the size checks' failure note, cap and settings pins; the
  agent files, AGENTS.md, DECISIONS.md and the skills agree on the final check, the write guards and the tools.
- **Unspecified (raised with the user):** uniq refuses a leading `~` while `-C` passes it, and uniq's message says it
  "may expand into several words", false for a leading `~`; what reloads AGENTS.md for subagents besides a compaction;
  whether a subagent may write PLAN.md; whether `install.py`, which the runner runs, counts as the "configuration"
  `runner.md` forbids it to change; how Claude Code runs a hook command on Windows (the size checks may be off there,
  the guard's Bash unguarded).

### 2026-11-19: third review of the agent-delegation branch (uncommitted, against main)

- **How:** three `reviewer` agents in the background, one each for the guard, the lead's hooks, and the agents with
  their docs, each told not to read PLAN.md and to read AGENTS.md from disk. No tests run. Before it, the lead answered
  the second review's Unspecified items as the user chose: a call's fields (FIELDS), a leading `~` in uniq's words, Grep
  and Glob counted, `runner.md`'s "the repository's files", a subagent never writes PLAN.md. The lead's probes, none in
  Designer: a hook logging the Bash payload (`tool_input` holds only the fields the call gave); `Read('~/...')`; the
  hook's count file in a turn a notification started; a 12,000-character output under the cap; one WebSearch; a
  foreground command outliving a 3 s timeout, stopped with TaskStop. Two `analyst` agents read Claude Code's docs (the
  tools reference, sub-agents, model-config, hooks, env-vars) and the session's transcripts. Settled as wrong:
  - "a 12,000-character output saved under the cap may lack `persistedOutputPath`, and get a false note": measured,
    no note came;
  - "WebSearch was never seen blocked live": measured, the hook refused it;
  - "what `onFailure: block` does is unsourced": the hooks reference ("Block the action when a hook fails"): from
    v2.1.295, a failure or a timeout of the hook blocks the call as exit 2 does.
- **Not verified:** none.
- **Resolutions assessed:** the second review's 12, by the reviewers. They hold except AGT-17 (AGT-24), AGT-22 (AGT-30)
  and TST-570 (TST-575). TST-573 holds for its five lines; a note under it names two more.
- **Findings:** AGT-23 to AGT-33, TST-574 and TST-575: 2 Low-medium, 11 Low. Not converged (step 7 of the skill): a
  Low-medium finding gets another review once fixed.
- **Suggested order:** AGT-24 (the guard's moved commands; its fix is the user's choice), AGT-23 (`~` reads); then the
  code: AGT-29, AGT-25, AGT-28, AGT-27; then the docs: AGT-33, AGT-26, AGT-30, AGT-31, AGT-32, TST-574, TST-575.
- **Longest chain:** generation 3 (AGT-12 → AGT-17 → AGT-24; TST-566 → TST-570 → TST-575).
- **Checked and found fine:** FIELDS pinned both ways; a leading `~` skips only index 0 (`~*`, `~[`, `~/a~b`
  refused, and zsh's `~user`, `~+`, `~-`, `~N` give one word); the tokenizer against zsh (comments, escapes,
  RC_QUOTES, `;;`, reserved words and precommands refused, history expansion off); no reader writes or starts a
  harmful program; the guard's hook command and frontmatter; AGT-16, AGT-19 (each figure fails with `'%6d\t'`), AGT-20,
  TST-569, AGT-21, TST-571, AGT-18, TST-572; the web block for the lead only; the nudge's counting, isolation and
  registration; mypy reaching `.claude/hooks`; `DOC_TESTS`; the agents' tools against their rules.
- **Unspecified (raised with the user):** PyCharm's other reading tools (`get_symbol_info`, `analyze_calls`,
  `list_directory_tree`, `get_file_problems`, `lint_files`) aren't counted by the nudge; the count files are never
  removed; who runs a review's measurement (AGENTS.md's "Keep it yourself" and the skill's Who settles what); "the
  lead" means both the agent's starter and the main session (`analyst.md`'s "The lead can't fetch the web" is false
  for `/simplify`'s analysts); commands the guard passes can fill memory and sort's temporary files until stopped; in
  this repository `git log --show-signature` starts gpg and `--ext-diff` or `--textconv` start the configured drivers.

### 2026-11-19: fourth review of the agent-delegation branch (committed, against main)

- **Scope:** `git diff main...HEAD` at `81b840a`, with the two step-back passes made since the third review. PLAN.md
  not reviewed.
- **How:** two `reviewer` agents in the background, one for the hooks with their settings, tests and docs, one for the
  agents and the rules. Both were told to read AGENTS.md and the skills from disk and not to read PLAN.md. No tests
  run. The lead's probes, none in Designer:
  - an analyst given a word that is in no file, resumed with SendMessage after it finished, answered with the word and
    no tool call: a finished agent goes on with its context;
  - this session's count file, read before and after a failing `ls` (exit 1), went from 4 to 5: the lead's failed
    reading calls are counted. A `grep` finding nothing came back as a success and was counted too.
- **Settled as wrong:**
  - "AGENTS.md's SendMessage sentence rests on the tool's description alone": measured, it holds (above);
  - "the lead's PostToolUseFailure payloads may lack `session_id` and `prompt_id`, so its failed calls go uncounted":
    measured, they are counted. The docstring's incomplete list of fields is AGT-36.
- **Not verified:** none.
- **Resolutions assessed:** the third review's 13, by the lead: all hold. The reviewers also rechecked AGT-3 to AGT-9,
  AGT-19, AGT-20, AGT-23, AGT-25 to AGT-28, AGT-33, TST-557, TST-558, TST-561 to TST-564 and TST-574: they hold, but
  for a sentence AGT-3's fix left (AGT-35).
- **Findings:** AGT-34 to AGT-44 and TST-576 to TST-578: 14 Low. Converged (step 7 of the skill): once these are
  fixed, the work goes to the final check, not to another review.
- **Suggested order:** the code first: AGT-34, AGT-39, AGT-38. Then the docs that misdirect: AGT-40, AGT-41, AGT-43,
  AGT-37, AGT-42, AGT-36, AGT-35. Then TST-577, AGT-44, TST-578. TST-576 waits for the user's wording.
- **Longest chain still growing:** generation 2 (AGT-3 → AGT-35, AGT-26 → AGT-42, TST-566 → TST-576, TST-572 →
  TST-578).
- **Checked and found fine:**
  - the hook: the tests' size figures recomputed; `_comment`, `_commands` and `_printed` against zsh and BSD's option
    forms; FIFOs and devices never opened; failing open (the settings command, `$CLAUDE_PROJECT_DIR` unset, a
    SyntaxError exiting 1); the five registrations against READING_TOOLS; every hook letting a subagent's calls
    through; `bash_note`'s saved output and "at least";
  - the tests and types: `DOC_TESTS` against the docs-only command; mypy reaching `.claude/hooks` and not
    `.claude/worktrees/`; the payload TypedDicts and the `_Hook` Protocol; the skips' platform reasons; AGENTS.md's
    limits pinned; `test_agents.py`'s tests each failing without what they check; the wording tests;
  - the docs: README's `disableAllHooks` against the hooks reference; every cited section, heading, file, skill and
    agent; each agent's tools against its rules; one owner per job; a failed final check reported by the runner and
    fixed by the developer; DECISIONS.md's write-guard entry against the four agent files; PLAN.md's rules across
    AGENTS.md, the docs table and `reviewer.md`.
- **Not raised:** "Tests run at two stages" and the review skill leave out the chosen categories the runner runs:
  generation 4 of TST-566's chain, changing nothing anyone does (DECISIONS.md, Low-value findings).
- **Unspecified (raised with the user):**
  - whether the runner may run the final check on Windows, in the user's Designer (AGT-41);
  - whether a developer addressing findings writes a new problem's REVIEW.md entry itself or reports it to the lead:
    two developers at once would take the same ID;
  - whether the Bash size check is meant for a command that succeeds, whose output the 10,000-character cap already
    saves to a file.
- **Decided by the user (2026-11-19):** the user asks for the final check in the main session, and the lead gives it to
  the runner, which runs it wherever Claude runs, macOS or Windows (AGT-41's fix). A developer addressing findings
  writes a new problem's entry itself, and only one developer runs at a time (AGENTS.md, Delegating to subagents). The
  Bash size check stays as it is, beside the cap: the simpler choice, which the user left to the lead. TST-576: "Fix
  them all".
- **Changed by the user (2026-11-19, their workflow):** only the lead writes REVIEW.md. A developer proposes a new
  problem it finds, and the lead settles it, then writes it or rejects it, after a debate if they disagree.

### 2026-11-19: fifth review of the agent-delegation branch (uncommitted: the hook's new code)

- **Scope:** `git diff HEAD -- .claude/hooks/large_reads.py tests/unit/test_large_reads.py`, with the new
  `tests/unit/counted_reads.py` and `tests/unit/notebook_files.py` read whole: the developer's fixes of AGT-34 to
  AGT-46 in the hook and its tests, not committed yet. The same batch's docs were left to the comparison below.
- **How:** one `reviewer` agent, as the user's workflow (2026-11-19) has the lead review a developer's work when it
  finishes. Beside it, two `analyst` agents compared that workflow with the lead's files and with the agents' files.
- **Settled as wrong:**
  - a notebook's empty cell rebuilt as its marker and an empty line: the lead's `read_file` of a notebook with empty
    markdown cells (`[]` and `''`) between code cells showed `L3: #%% md` then an empty `L4: `, as `_notebook`
    rebuilds it;
  - two new helpers left in the test file (`_bytes_read`, `_returned`): the file's other helpers are of the same kind,
    and a helper of a few lines beside its tests is part of the file's logic.
- **Not verified:** none.
- **Resolutions assessed** by the reviewer, read by the lead: AGT-34 to AGT-39, AGT-45 and AGT-46 hold, but for
  AGT-34's **Also covered** (AGT-48), AGT-45 (AGT-47) and AGT-46 (AGT-49).
- **Findings:** AGT-47 to AGT-49 and TST-579: 4 Low. All Low, so converged by the skill's rule; the user decides (their
  workflow, 2026-11-19).
- **Suggested order:** AGT-47 and TST-579 (the tests' figures), then AGT-48, AGT-49.
- **Longest chain still growing:** generation 2 (AGT-45 → AGT-47, AGT-34 → AGT-48, AGT-46 → AGT-49).
- **Checked and found fine:** `_last`'s lower bound with its partial first line; `_bounded`'s upper bound; `_capped`
  with lines of CAP-1, CAP and 2×CAP bytes and a cut line at the end; files of 1 MB or less sized as before; every
  error caught by `main()`, which lets the call through; no loop without progress; the tests' figures recomputed;
  `Counter` counting every read; the types; AGENTS.md and README against the code.
- **Not raised:** a one-loop `_scan` (the same behaviour, slower for small files); a notebook's JSON parsed whole
  (AGT-45's resolution says so); `_numbered` counting the `\r` of a regular file's CRLF, outside the diff and
  unmeasured for `read_file`, which turns a notebook's CR and CRLF into newlines.
- **Addressed (2026-11-19):** the four by the developer in PLAN.md's Step A, written by the lead; AGT-50, found by the
  developer while addressing them and settled by the lead's own `read_file` of a CRLF and a lone-CR file.
- **Unspecified (raised with the user):** what `read_file` returns for an `offset` past the end of a file. The hook
  sizes the last line there, which matters only for a file over 1 MB with a last line over 20 KB.

### 2026-11-19: sixth review of the agent-delegation branch (Step A, `849879f..9910caa`)

- **Scope:** `git diff 849879f 9910caa`, by paths and without PLAN.md: the hook and its tests; AGENTS.md, DECISIONS.md,
  the agent files and the tests pinning their wording; the skills.
- **How:** three `reviewer` agents at once, the user's decisions of 2026-11-19 given as the docs' claim. Settling: a
  `runner`'s mutation probe (AGT-62); an `analyst` on CPython's buffer size (TST-588); an `analyst` checking every
  quote, all found (AGT-55 and AGT-56 in part).
- **Settled as wrong, or not raised:** "a new step starts a new developer" and "while its context helps" (the lead's
  own detail of decision 5, kept); "no review while the developer edits", wider than "the code under review" by
  design (a reviewer reading whole files meets no half-edited code); the memory index missing a file (it lists it);
  a lone-CR file's refusal with no working way on, and a refused `cat` of a PDF or image sent to Read (rare); the
  developer's analysts reporting to the developer (no effect).
- **Resolutions assessed:** AGT-47 to AGT-50 and TST-579, by the hook's reviewer: they hold, but for AGT-50's tests
  (AGT-62). AGT-21, AGT-31, AGT-32, AGT-43, AGT-44, TST-559, TST-568, TST-569, by the docs' reviewer: they hold.
- **Findings:** TST-580 and AGT-51, Low-medium; AGT-52 to AGT-63 and TST-581 to TST-588, Low. Not converged: a
  review follows the fixes.
- **The lead's readings of the user's words** (PLAN.md lists them for the user at convergence): AGT-51's timing,
  TST-581's convergence, AGT-54's loop per step, AGT-59's "files outside the repository".
- **Suggested order:** TST-580 and AGT-51; AGT-62 and TST-588, test first; then the docs, in one developer run with
  PLAN.md's Step B, which edits the same files.
- **Longest chain still growing:** generation 3 (AGT-46 → AGT-49 → AGT-63).
- **Addressed (2026-11-19):** all 22, by one developer with PLAN.md's Step B, each resolution assessed and written by
  the lead; DECISIONS.md's convergence sentence by the lead (AGT-53), in the user's words.

### 2026-11-19: seventh review of the agent-delegation branch (Step B and the sixth review's fixes, `850dfd5..8591ac9`)

- **Scope:** `git diff 850dfd5 8591ac9`, by paths, PLAN.md left out: the hook and its tests; AGENTS.md, DECISIONS.md,
  README.md, ROADMAP.md, the agent files, the rules and the `delegate` skill; the other skills and the tests pinning
  the docs.
- **How:** three `reviewer` agents at once, Step B's approved text quoted as the claim (whole to one, in part to
  another: from now on whole to each, as step 3 says). Settling: a `runner`'s two probes (rules loaded by a Bash
  read; mypy's type after the `isinstance`); Step B part 4's own measurements (a runner's SendMessage to the lead; a
  background timer).
- **Settled as wrong, or not raised:** SendMessage unmeasured (measured, AGT-68 records it); item 110's "about 21 KB"
  target (a figure; every part it names moved); AGENTS.md listing 5 of the 7 rules (by the test's design); the docs
  tests' trigger written in five agreeing places; the mypy tip on `sd`'s import cycles staying in live-check (before
  this diff). The user's memory file giving `git diff main...<branch>` without the exclusion: fixed by the lead (the
  memory is outside the repository).
- **Resolutions assessed:** AGT-51 to AGT-63 and TST-580 to TST-588, by the three reviewers: they hold, but for
  TST-580 (TST-593) and TST-583 (TST-594).
- **Findings:** AGT-64 to AGT-70 and TST-589 to TST-595: 14 Low, none higher. All Low, but not "a few" (the lead's
  judgment): one more round, its review sized to the fixes.
- **Suggested order:** AGT-64, TST-595, AGT-66 (code and tests, test first); then the docs, with PLAN.md's round
  items (the reviewer's part of the review skill into `reviewer.md`).
- **Longest chain still growing:** generation 3 (AGT-46 → AGT-49 → AGT-63) stopped; generation 2 now (TST-580 →
  TST-593, TST-583 → TST-594).
- **Unspecified (decided by the lead, listed in PLAN.md):** a reviewer of one area gets the whole approved step, not
  its parts.
- **Addressed (2026-11-19):** all 14 and the round's two PLAN.md items by one developer, each resolution assessed and
  written by the lead; TST-596 found by the developer and settled by the lead.

### 2026-11-19: eighth review of the agent-delegation branch (the seventh review's fixes, `d6b92b7..daf047d`)

- **Scope:** `git diff d6b92b7 daf047d`, by paths, PLAN.md left out: the hook and the unit tests; the docs, the agent
  files, the skills, the rules, ROADMAP.md and `mypy.ini`.
- **How:** two `reviewer` agents at once, each told to read its new `reviewer.md` from disk; the approved round items
  quoted whole as the claim. Settling: a `runner`'s probe of which Bash commands load a rule (AGT-71).
- **Settled as wrong, or not raised:** a long run started in the foreground blocking the lead (the lead's Agent tool
  runs every subagent in the background, by its description); a two- or four-letter prefix escaping `_prefixes`
  (every prefix has three letters); DECISIONS.md's "doc tests" beside "docs tests" (misleads no one). A reviewer's
  system prompt already held the new `reviewer.md`: inconclusive, since a message of the user's may have come after
  the edit.
- **Resolutions assessed:** AGT-64 to AGT-70 and TST-589 to TST-596, by the two reviewers: they hold, but for AGT-66
  (AGT-72), AGT-67 (AGT-71), TST-590 (TST-597) and TST-591 (TST-600).
- **Findings:** AGT-71, AGT-72 and TST-597 to TST-601: 7 Low, small, five of them generation 2 narrowing a claim.
  Converged (the lead's judgment of "a few", the user, 2026-11-19): once these are fixed, Step A and Step B are
  done, and Step C follows.
- **Suggested order:** TST-601 and AGT-72 (tests); then AGT-71, TST-597 to TST-600.
- **Longest chain still growing:** generation 2.
- **Unspecified (for the user at convergence, in PLAN.md):** how an edit to a preloaded skill's text reaches an agent
  started in the same turn; whether a rule loaded before a compaction comes back after it.
- **Addressed (2026-11-19):** all 7 by one developer, each resolution assessed and written by the lead. Steps A and B
  are done.

### 2026-11-19: ninth review of the agent-delegation branch (Step C, `e923201..43f5093`)

- **Scope:** `git diff e923201 43f5093 -- docs/ AGENTS.md`: `docs/agent-workflow.md`, written by the lead, and its row in
  AGENTS.md's table.
- **How:** one `reviewer`, Step C's text quoted whole as the claim; every claim checked against the setup's files.
- **Settled as wrong, or not raised:** a probe of whether an unpiped `cat` loads a rule (the fix copies AGENTS.md's
  measured wording instead); a docs test pinning the story's claims (Unspecified; the lead's decision: no, the story
  points to the homes and reviews check it); AGENTS.md's list of rules leaving out `changing-tools.md` and
  `live-checks.md` (by the test's design).
- **Findings:** AGT-73 and AGT-74 Low-medium; AGT-75 to AGT-80 Low. Not converged: a review follows the fixes.
- **Suggested order:** AGT-73, AGT-74, then AGT-77 and AGT-76, then the rest.
- **Longest chain still growing:** generation 1.
- **Addressed (2026-11-19):** all 8 by one developer, each resolution assessed and written by the lead.

### 2026-11-19: eleventh review of the agent-delegation branch (Step D, `a9da3b9..5f37835`)

- **Scope:** `git diff a9da3b9 5f37835`, PLAN.md and `docs/agent-workflow.md` left out (the story is rewritten last,
  the user's order): AGENTS.md and the rules; the skills, agents and hook; the tests and the code's comments.
- **How:** three `reviewer` agents at once, Step D's approved text quoted whole as the claim. The tenth review, of the
  story, was stopped unfinished at the user's word, nothing recorded.
- **Settled as wrong, or not raised:** `MOVED_PARTS` over-matching correct pointers, and the rules test missing a
  subfolder of `.claude/rules/` (no effect today: DECISIONS.md, Low-value findings about the tests and docs); the
  facts-once test's empty case (before this diff). The story's stale pointers and its copy table wait for its rewrite.
- **Checked and found fine:** every moved part word for word in its home (two reviewers diffed it mechanically);
  every rule's paths against the files they serve; GUIDE.md, `INSTRUCTIONS` and every tool's docstring unchanged; the
  hook's docstring holding every fact AGENTS.md dropped.
- **Findings:** AGT-81 Low-medium; AGT-82 to AGT-88 and TST-602 to TST-604 Low. Not converged: a review follows.
- **Suggested order:** AGT-81, AGT-87, AGT-85, AGT-88, AGT-83, then the rest.
- **Longest chain still growing:** generation 1 (this step's own).
- **Addressed (2026-11-19):** all 11 by one developer, each resolution assessed and written by the lead.

### 2026-11-19: twelfth review of the agent-delegation branch (the eleventh review's fixes, `e5e4700..bfcb54b`)

- **Scope:** `git diff e5e4700 bfcb54b`, PLAN.md, `docs/` and REVIEW.md left out: the docs, skills, agents, rules and
  hook; the tests.
- **How:** two `reviewer` agents at once, Step D's approved text quoted as the claim.
- **Resolutions assessed:** AGT-81 to AGT-88 and TST-602 to TST-604: they hold, but for AGT-82 (TST-607), AGT-83
  (AGT-90), AGT-87 (AGT-89, TST-605) and AGT-88 (TST-606).
- **Not raised:** the new `MOVED_OUT` patterns' over-match of a correct pointer (fails loudly; DECISIONS.md, Low-value
  findings); `docs.md`'s "tool config" not covering JSON (holds no comments); `test_review_lookup.py`'s line-wrap
  replace (before this diff).
- **Findings:** AGT-89, AGT-90 and TST-605 to TST-607: 5 Low, all generation 2. **Converged** (the lead's judgment of
  "a few"): once fixed, Step D is done.
- **Decided by the lead:** AGT-89 keeps the hooks' notes over Step D's "two or three lines" (listed for the user).
- **Addressed (2026-11-19):** all 5 by one developer, each resolution assessed and written by the lead. Step D is done.
- **Longest chain still growing:** generation 2.

---

### 2026-11-20: thirteenth review of the agent-delegation branch (the whole branch against main, the Sonnet comparison)

- **Scope:** `git diff main...HEAD -- . ':(exclude)PLAN.md'` at `22144af`, `docs/agent-workflow.md` (Step C rewrites
  it) and REVIEW.md left out. A round on `4a08458..22144af` was started and stopped for this one (the user's choice).
- **How:** four areas (the hooks; the agents and skills; AGENTS.md, the rules and the docs; the code and the other
  tests), each given to an Opus `reviewer` and a Sonnet one (`model: sonnet`, the user's yes for this trial), one brief
  per area. The claim: the approved texts of Steps A, B, D and E, each from the first commit holding it, and the
  user's instructions of 2026-11-20.
- **Resolutions assessed:** the reviewers rechecked this branch's resolutions in their areas; all hold.
- **Settled:** AGT-91's Read case is false, measured: `Read('<folder>/link/../x')` returned the small `x`, and the hook
  let it through (Read resolves `..` lexically). Its Bash case, and every other suspicion, confirmed by reading the
  lines it quotes.
- **Findings:** 12 Low: AGT-91 to AGT-94, TST-608 to TST-614, HLP-207. Found by Opus only: AGT-91, AGT-92, AGT-93,
  TST-611, TST-613. By Sonnet only: TST-608, AGT-94, HLP-207. By both: TST-612, TST-614. TST-609 by Opus in full
  (Sonnet: 2 of 7 places, as a note); TST-610 by Sonnet (Opus: as an Unspecified item). Sonnet saw AGT-93 and dropped
  it.
- **Not converged** (the lead's judgment: 12 Low is more than "a few", as 14 was at the seventh review): fixed, then one
  more round.
- **Unspecified, for the user:** `.claude/rules/waits.md` against DECISIONS.md's 30 ms entry (`test_waits.py:49-50`
  says the user decides which stands; three reviewers); the prefix of a finding on a skill or a rule (AGT or TST,
  both used); a finding failing the won't-fix criterion 3 has no resolution wording; three rare cases of the hook
  (Read's `allow_large`, a `read_file` past a file's end, a whole `read_file` of a huge file of short lines); whether
  a checked ROADMAP item's figures follow later changes; an unpiped `cat` seemed to load rules, which AGENTS.md doesn't
  list; the 15,000-byte budget written only in the test; the first review's `run_in_background` item, still open.
- **For the final check:** the plugin's file changed (a comment), so its brief says so: `install.py` and a restart
  come first (the bridge check "installed plugin matches the repo").
- **Not raised:** `tests/unit/test_selftest_pool.py:331`'s inline join (captured output, not a doc, so outside Step E
  (d)); ROADMAP item 18 not mentioning `\r\n` (incomplete, not false); the finder taking another file's bold label
  as a section (no such pointer).
- **Cost:** Opus 1,021,051 tokens, 12.5 to 17 min per area; Sonnet 971,644 tokens, 7.5 to 11 min.
- **Addressed (2026-11-20):** all 12 by one developer, each resolution assessed and written by the lead. The developer
  found AGT-95 (follows AGT-91), settled by the two measurements.
  AGT-95 fixed by the same developer, who found AGT-96 (follows AGT-91); the lead measured it with its own `read_file`.
  AGT-96 fixed by the same developer, and measured again by the lead.
- **Longest chain still growing:** generation 2 (TST-608).

---

### 2026-11-20: fourteenth review of the agent-delegation branch (the thirteenth review's fixes, `22144af..0785f61`)

- **Scope:** `git diff 22144af 0785f61 -- . ':(exclude)PLAN.md'`, REVIEW.md and `docs/agent-workflow.md` left out.
- **How:** two `reviewer` agents on Sonnet (`model: sonnet` passed, the reviewer file's new default not yet loaded):
  the hook and its tests; the skills, the agent file, ROADMAP.md and the other tests. The claim: each fixed finding's
  entry and resolution, and the user's instructions of 2026-11-20.
- **Resolutions assessed:** AGT-91 to AGT-96, TST-608 to TST-614 and HLP-207 hold; AGT-91's Also covered got a note
  (AGT-96).
- **Findings:** AGT-97, AGT-98, TST-615, TST-616: 4 Low. **The Sonnet rounds look converged** (project-code-review,
  step 7): once these are fixed, the rounds switch to Opus. The user (2026-11-20): the first Opus round reviews "the
  entire branch diff against main".
- **Unspecified, for the user:** none new (the Opus round's scope was asked at once and answered).
- **Not raised:** `tests/unit/test_guide.py`'s "once in DECISIONS.md" (reads as history); "leftover" used for two
  things in `project-code-review` (nobody misled); `PROSE_AFTER_AGENTS_MD`'s unbounded middle (fails loudly; DECISIONS.md,
  Low-value findings); the AGT-95 test's older sibling named "absolute paths" (a real path is absolute);
  `docs/agent-workflow.md` lacking `hook_calls.py` (Step C).
- **Cost:** 373,952 tokens for the two reviewers, 7.5 to 8 min each.
- **Addressed (2026-11-20):** all 4 by the same developer, each resolution assessed and written by the lead.
- **Found by:** added to the title lines of AGT-91 to AGT-98, TST-608 to TST-616 and HLP-207 (the user, 2026-11-20,
  with the template's new field), and the thirteenth and fourteenth rounds' rows to Reviews by model. TST-610 counts as
  Sonnet's alone: Opus raised it only as an Unspecified item.
- **Longest chain still growing:** generation 2 (AGT-98, TST-615, TST-616).

---

### 2026-11-20: fifteenth review of the agent-delegation branch (Step C with the review flow and REVIEW.md's new fields, `a0cc89d..16f7745`)

- **Scope:** `git diff a0cc89d 16f7745 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`; REVIEW.md's new header
  paragraph and table read against the template.
- **How:** two `reviewer` agents on Sonnet (the reviewer file's default): the story; the skills, the template and the
  tests. The claim: Step C's text and the user's instructions of 2026-11-20.
- **Resolutions assessed:** AGT-97 and TST-610 hold in their new form.
- **Dropped:** "cleanup step 6 gives the user a reason the user didn't give": the user wrote "it is enough for me to
  read it just before cleanup" (2026-11-20), which the claim file lacked; added to it.
- **Findings:** TST-617 (Low-medium), TST-618 to TST-624 and AGT-99 (Low). TST-621 fixed by the lead at once. The
  Sonnet rounds are not done: once these are fixed, another Sonnet round.
- **Decided by the lead (Unspecified items):** the Total row sums the rows, as the user said ("total ... keep
  increasing the counts"), so a finding both models found counts in each, and Time sums each row's slowest agent; a
  whole-branch round's claim is each step's text from the first commit holding it (AGT-99); two reviewers of one model
  are written "by two reviewers (Sonnet)" (TST-622).
- **Not raised:** the thirteenth and fourteenth log entries' Cost lines, which the table now holds too (older entries
  keep their form).
- **Addressed (2026-11-20):** TST-617 to TST-621 by the lead (the story, REVIEW.md); TST-622 to TST-624 and AGT-99 by
  the developer, each resolution assessed and written by the lead.
- **Longest chain still growing:** generation 2 (TST-619).

---

### 2026-11-20: sixteenth review of the agent-delegation branch (the fifteenth review's fixes, `e44f44e..7f86626`)

- **Scope:** `git diff e44f44e 7f86626 -- . ':(exclude)PLAN.md'`; REVIEW.md's header and table against the template.
- **How:** one `reviewer` agent on Sonnet. The claim: each fixed finding's entry, Step C's text and the user's
  instructions.
- **Resolutions assessed:** TST-617 to TST-624 and AGT-99 hold, but for TST-620 (TST-625).
- **Findings:** TST-625 to TST-628, 4 Low, all in the story, fixed by the lead. **The Sonnet rounds of the last step
  are done** (project-code-review, step 7): next, the Opus round on the entire branch.
- **Unspecified, for the user:** a finding the developer found (AGT-95 and AGT-96, on Opus) is in no row of the table
  by model (TST-622's reading of the user's item 17); whether such findings should count in a row.
- **Not raised:** the diff-command test's `in` in place of `endswith` (the whole-branch commands pinned apart);
  `_number` reading Time only as "N min"; one long line in the story.
- **Longest chain still growing:** generation 2 (TST-625, TST-628).

---

### 2026-11-20: seventeenth review of the agent-delegation branch (the first Opus round on the entire branch)

- **Scope:** `git diff main...HEAD -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'` at `b847842`, all of it, the story
  included.
- **How:** four `reviewer` agents on Opus (`model: opus` passed, project-code-review step 7): the hooks; the agents,
  skills and story; AGENTS.md, the rules and the docs; the code and the other tests. The claim: the five steps' texts,
  each from the first commit holding it, and the user's instructions of 2026-11-20 (items 1 to 19).
- **Resolutions assessed:** this branch's resolutions in each area hold, but for those the story's Step C rewrite
  brought back (TST-629, TST-630: AGT-59, AGT-73, AGT-74, AGT-75, AGT-77, AGT-78), TST-558's walks (TST-634) and
  AGT-97's Opus stage (AGT-100).
- **Settled by the lead's probes:** Read returned a 2,100-line file whole (no cap at 2,000, as AGT-8 measured), so the
  hook's docstring and its test stay true; the thirteenth review's Unspecified "Read's `allow_large`" item needs no
  change. The story's two anecdotes are true (the fourth review's `git diff main...HEAD` printed PLAN.md; the status
  test refused the lead's wrong totals), so that part of TST-632 was dropped.
- **Findings:** TST-629 (Low-medium), TST-630 to TST-634 and AGT-100 to AGT-102 (Low). More than a few: once fixed,
  Opus rounds review the fixes, then the entire branch again (step 7).
- **Unspecified, for the user:** the docs tests run on a change of Markdown, while they also check comments and
  docstrings in `.py`, `.ini` and `.toml` files (`docs_text.DOC_SUFFIXES`), so a comment-only change can leave a
  dangling pointer found only at the final check.
- **Not raised:** "22, 14, then 7 ... before converging" (generation 3, misleads no one); DECISIONS.md entries that
  repeat measurements (before the branch; each still stops a finding); the user's memory file lacking the REVIEW.md
  exclusion (outside the repository; the lead updated it).
- **Longest chain still growing:** generation 2.

---

### 2026-11-20: eighteenth review of the agent-delegation branch (an Opus round on the seventeenth review's fixes, `b847842..64ea38f`)

- **Scope:** `git diff b847842 64ea38f -- . ':(exclude)PLAN.md'`; REVIEW.md's table by model against the template.
- **How:** two `reviewer` agents on Opus (`model: opus`): the hook, its new module and the code tests; the skills,
  rules, AGENTS.md, the story and the docs tests. The claim: each fixed finding's entry and the user's instructions
  (items 20 to 22 new).
- **Resolutions assessed:** TST-629 to TST-634 and AGT-100 to AGT-102 hold, but for AGT-101 (AGT-103, AGT-104) and
  TST-631 (TST-635).
- **Dropped:** "the table's cells differ from the user's example `5 [3(low), 2(medium)]`": the lead told the user it
  would write "9 [1 Low-medium, 8 Low]", most severe first, matching the severity names, and the user went on; listed
  with the lead's decisions at convergence.
- **Findings:** AGT-103, AGT-104, TST-635: 3 Low. The Opus rounds on the fixes are done (project-code-review, step 7):
  once fixed, an Opus round on the entire branch again.
- **Unspecified, for the user:** whether a change of comments or docstrings alone counts as "docs changed alone"
  (already asked).
- **Not raised:** the ruff test's non-skipped path (generation 3); `load_script` appending `.claude/hooks` last (no
  effect); the story's copy-table gaps for `python.md`'s After editing and `unit-tests.md` (generation 3, a copier
  writes those rules anyway); "13.1 KB" read as Step D's history.
- **Longest chain still growing:** generation 2 (AGT-103, AGT-104, TST-635).

---

### 2026-11-20: nineteenth review of the agent-delegation branch (the Opus round on the entire branch again)

- **Scope:** `git diff main...HEAD -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'` at `179b257`, all of it, the story
  included.
- **How:** four `reviewer` agents on Opus (`model: opus`): the hooks; the agents, skills and story; AGENTS.md, the
  rules and the docs; the code and the other tests. The claim: the five steps' texts, each from the first commit
  holding it, and the user's instructions of 2026-11-20 (items 1 to 22).
- **Resolutions assessed:** this branch's resolutions in each area hold, but for AGT-99's claim (AGT-106). Step 2's
  "Questioned by" line is missing under 31 questioned entries (TST-636).
- **Settled by the lead's probes:** the rules' `**/*` patterns reach files under `.claude/`. A fresh analyst's first
  Read, of `.claude/hooks/command_lines.py`, showed `python.md`, `docs.md` and `docs-tests.md`; another's, of
  `.claude/agents/analyst.md`, showed `docs.md` and `docs-tests.md`. The controls after them (`install.py`, README.md)
  showed only the rules not yet loaded. The suspicion that the patterns skip dot folders was dropped.
- **Findings:** AGT-105 to AGT-107 and TST-636: 4 Low, none above. The reviews converged (project-code-review, step
  7): once these are fixed, the convergence report.
- **Unspecified, for the user:**
  - the `address-review` skill's Show the plan first exempts the developer only: when the lead fixes findings itself
    (the story, at the sixteenth review), does the loop's "without asking" cover it?
  - DECISIONS.md names two skills without a path (`:20`, the `address-review` skill, Recording decisions; `:32`, the
    `live-check` skill, added by this branch), while a reviewer, who reads DECISIONS.md first, has no Skill tool.
- **Not raised:** loading the hook in the tests leaves `.claude/hooks` first on `sys.path` (no later check depends on
  it); the story's copy table dropping "this project's docs" tests while a kept hook test pins README's pointer
  (generation 3); the story's gaps (`git status` for new files, "with its acceptance criteria", the docs-alone final
  check, `waits.md` in the rules row) and "13.1 KB" (generation 3); `test_lint.py`'s "runs on Windows" (ROADMAP items
  18 and 111); Step E's "21" flattenings, 17 on main (a figure in the approved text, no effect); `test_waits.py:49-50`
  still names the question the user decides (Waiting for the user).
- **Longest chain still growing:** generation 2 (AGT-106).

---

### 2026-11-20: twentieth review of the agent-delegation branch (the user's answers after convergence, `982a9cc..91ec8f3`)

- **Scope:** `git diff 982a9cc 91ec8f3 -- . ':(exclude)PLAN.md'`, the user asking for "one review round on today's
  changes".
- **How:** two `reviewer` agents on Sonnet, the reviewer's default: the hook and its tests; everything else. The claim:
  the user's answers of 2026-11-20 after convergence, items 23 to 37, each the user's words and the lead's proposal
  they approved, the later standing over items 1 to 22.
- **Resolutions assessed:** AGT-108 holds.
- **Settled by the lead's probes:** `read_file`'s first erroring offset is one past the last line, the empty line
  after a last newline counted: on `a\nb`, offset 2 showed `L2: b` and 3 errored; on `a\nb\n`, offset 3 showed
  `L3: ` and 4 errored (probe files in the repository, removed). So the boundary the hook and its test take holds.
- **Dropped:** "the check returning None when no line is shown changes no refusal": AGT-108's Fix asked for None, the
  function's docstring contract, and a unit test of a function's return is legitimate.
- **Findings:** AGT-109, TST-637 to TST-639: 4 Low. The round's reviews are done once they are fixed.
- **Not raised:** Monitor can stream any file's lines into the lead's context unsized: a route for any file, before
  this diff, not the background call's (the lead reads an output file with Read or Bash, both sized); a possible
  ROADMAP.md item. Item 23 reaching `/simplify` and the live rerun after a failed final check: told to the user with
  the change. README's bare "docs alone", with its pointer to the rule. The seventeenth review's Unspecified item
  (comments or docstrings alone as docs alone) is answered by item 23. Old log entries listing `read_file` past the
  end as open: history.
- **Table:** the nineteenth review's `settling` row (the two analysts' dot-folder probes) was missing, and is added.
- **Longest chain still growing:** generation 1.

---

## High

## Medium-high

- [x] **AGT-1 · `sort --o=FILE` writes any file through the guard: long options shorter than 4 characters are never checked** · `.claude/hooks/read_only_bash.py:72, 97, 225-226` · measured · found 2026-11-19
  - **Defect.** `SHORTEST = len('--op')` skips every long option of 3 characters, and `--o` doesn't match the short
    letters' `-[^-]`. macOS sort parses with `getopt_long`, which takes any unambiguous prefix, so `--o` means
    `--output`.
  - **Scenario.** In a scratch folder, `printf 'b\na\n' > in; sort --o=out in` wrote `out` holding `a`, `b`, and
    `refusal('sort --o=out in')` and `refusal('sort --o out in')` both return None. With stdin as the input, the
    content is free: `jq -n -r '"..."' | sort - --o=$HOME/.zshrc` passes and rewrites any file the user can write.
    The analyst has WebFetch, so injected web content is a way in. Git Bash's GNU sort and tail read `--o` and `--f`
    the same way.
  - **Fix.** `SHORTEST = len('--o')`: git grep's `--or` and git log's `--oneline` stay allowed (neither is a prefix of
    a forbidden option). Add `sort --o=out x` and `git grep --op=true x` to the refused cases (the second pins
    `SHORTEST`, TST-562).
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_read_only_bash.py::test_the_guard_blocks_any_other_command[sort --o=out x]` and `[sort --o out x]` returned None; `[git grep --op=true x]` pins `SHORTEST` at 4 or less (the pins were checked against copies of the hook with each guarding line removed, by the developer's scratch mutation script: every pin fails there).
    - **Cause:** `SHORTEST = len('--op')` skipped every long option shorter than 4 characters, and macOS sort's `getopt_long` takes any unambiguous prefix (measured: `sort --o=out2 in` wrote `out2`).
    - **Fix:** `SHORTEST = len('--o')`: only `--` alone is skipped (`--=x` measured ambiguous to sort, tail, uniq and ugrep). The docstring says so.
    - **Also covered:** every `long` list goes through this one check (git, ugrep, sort, tail). `git grep -e a --or -e b` and `git log --oneline` stay allowed; `sort --output=out x` refused. The lead ran the guard on `sort --o=out in` and `sort --o out in` after the fix: both refused.

- [x] **AGT-2 · `uniq` given a glob that matches two files overwrites the second: the guard counts the word, not the files** · `.claude/hooks/read_only_bash.py:99, 232-240` · measured · found 2026-11-19
  - **Defect.** `_second_file` counts the words as written, and an unquoted `*`, `?` or `[` passes the tokenizer as
    plain text. zsh expands the glob before uniq runs, and uniq writes its second operand.
  - **Scenario.** In a scratch folder with `a1` holding `x`, `x` and `a2` holding `keep`, `uniq a?` overwrote `a2`
    with `x`; `refusal('uniq a?')` is None. `uniq .claude/hooks/*.py` would overwrite the untracked guard with
    `large_reads.py`, which lets every subagent's call through: the guard would then let everything pass, and the file
    has no copy in git.
  - **Fix.** Have the tokenizer mark the words holding an unquoted `*`, `?` or `[`, and have `one_file` refuse such a
    word; or let uniq read only stdin. A glob can also expand to a planted file named like an option (`-delete`): a
    residual risk, needing such a file first.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `[uniq a?]`, `[uniq -c .claude/hooks/*.py]`, `[uniq [ab]]` and `[uniq -c "a?"]` returned None.
    - **Cause:** `_second_file` counts the words as written, and zsh expands a glob before uniq runs.
    - **Fix:** uniq refuses any word holding one of GLOBS (`*?[^#~`), quoted or not (`_glob_refusal`): more than needed, within the user's decision. `^`, `#` and `~` are glob characters only with EXTENDED_GLOB, which Claude Code's shell has off (measured with `setopt`); the docstring records it, and the residual of a glob expanding to a planted file named like an option.
    - **Also covered:** the new `git -C <dir>` had the same hole (`git -C c* log` could become `git -C c1 checkout log`): refused the same way, `[git -C c* log]` and `[git -C 'c?' log]` seen failing first. The lookup's ID pattern refuses glob characters, and git's subcommand must equal a GIT name. Note: `~` in GLOBS also refuses `git -C ~/x log`, raised with the user.

## Medium

## Low-medium

- [x] **AGT-3 · PyCharm's relative paths are sized from the call's `cwd`, but PyCharm reads them from its project** · `.claude/hooks/large_reads.py:19, 121` · measured · found 2026-11-19
  - **Defect.** `path = _path(_text(fields, 'cwd'), file_path)` joins a relative path to the call's `cwd`, which
    follows an earlier `cd` (the docstring's own measurement). PyCharm's `read_file` takes project-relative paths and a
    `projectPath`.
  - **Scenario.** A probe gave `read_refusal` a PyCharm read of `mcp_server/GUIDE.md` (32,730 bytes) with
    `cwd=<repo>/tests/unit`: None, while the same call from the root is refused. After a `cd tests/unit`, the lead's
    PyCharm read of the guide puts all of it in the context. A file of the same name under the `cwd` instead decides
    the answer, and a refusal then gives that file's size. `test_a_relative_path_is_measured_from_the_calls_cwd` uses
    the `cwd` as the project.
  - **Fix.** For `mcp__pycharm__read_file`, join a relative path to `tool_input['projectPath']` when given, else to the
    repository's root (`CLAUDE_PROJECT_DIR`, or the folder `PLAN` is found from). Change the test and the docstring.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_large_reads.py::test_pycharms_relative_path_is_measured_from_its_project` failed with "the repository's file" (the `cwd`'s small file of that name decided); `test_pycharms_project_is_the_repository` failed too.
    - **Cause:** `_path(cwd, ...)` was used for both tools.
    - **Fix:** PROJECT is the repository's root, from `__file__` (PLAN derives from it). PyCharm's relative path is joined to `projectPath`, else to PROJECT. Read keeps the call's `cwd` (measured: Read took `mypy.ini` as a relative path); its test is renamed `test_reads_relative_path_is_measured_from_the_calls_cwd`.
    - **Also covered:** Bash sizing keeps the call's `cwd`, right for a shell.
  - Questioned by AGT-35 (2026-11-19).

- [x] **TST-557 · The fail-open test's missing-script half passes without the script check** · `tests/unit/test_large_reads.py:424-428` · measured · found 2026-11-19
  - **Defect.** The temporary project lacks the venv too, and the command's `[ -x "$p" ] || exit 0` (added by the
    lead's own review on this branch) exits 0 before the script is ever needed.
  - **Scenario.** A probe ran the command without `[ -f "$s" ] || exit 0`: exit 0 with no venv, so the test still
    passes; with a venv Python, exit 2, a block. A change dropping the script check from both `COMMAND` and
    `settings.json` passes every test, and a checkout without the script then blocks every Read and Bash call of the
    user's session.
  - **Fix.** In that half, give the temporary project a venv Python (`mcp_server/venv/bin/python` linked to
    `sys.executable`) and no script.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** the test's own fix; the pins were checked against copies of the hook with each guarding line removed, by the developer's scratch mutation script: every pin fails there: the missing-script half fails with `[ -f "$s" ]` removed, the no-venv half with `[ -x "$p" ]` removed.
    - **Cause:** the temporary project lacked the venv too, so the venv check exited 0 first.
    - **Fix:** the missing-script half runs with a venv Python (a link to `sys.executable`) and no script.

- [x] **TST-558 · `files = ., .claude` makes mypy fail while a Claude Code worktree sits in `.claude/worktrees/`** · `mypy.ini:9` · measured · found 2026-11-19
  - **Defect.** mypy searches all of `.claude`, and Claude Code creates its worktrees in `.claude/worktrees/`
    (EnterWorktree's description; the Agent tool's `isolation: "worktree"` too). Each worktree holds a copy of every
    module.
  - **Scenario.** On a scratch tree with this `mypy.ini`, `a.py`, `.claude/hooks/h.py` and a copy of both under
    `.claude/worktrees/w/`, mypy stopped on "Duplicate module" ("errors prevented further checking"). With
    `files = ., .claude/hooks`, it found no issues. `test_types.py` fails while such a worktree exists.
  - **Fix.** `files = ., .claude/hooks`; `test_mypy_reaches_the_python_files_in_hidden_folders` accepts it as written.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** a check that no `files` entry reaches `.claude/worktrees/` failed with `['.claude/']`.
    - **Fix:** `files = ., .claude/hooks`, the reason in a comment. The mcp-builder `exclude` kept (the test drops that skill's `.py` files with it).
  - Questioned by TST-634 (2026-11-20).

- [x] **TST-559 · The PLAN.md rule reaches every agent, so reviewers read the author's account of the work** · `AGENTS.md:90-93` · confirmed · found 2026-11-19
  - **Defect.** "If it is there, read it before anything else, at the start of a session and after a compaction, and
    continue from it" is loaded into every subagent with AGENTS.md. PLAN.md holds the lead's summary of the work and
    its own verdicts, which `reviewer.md` ("Review blind") and AGENTS.md (a review gets "the code and the claim, never a
    verdict") keep from reviewers.
  - **Scenario.** In this review the size checks' reviewer read PLAN.md, whose step 7 says what the lead's review
    found and fixed. A developer is also told to "continue from it", past its unit.
  - **Fix.** Limit the rule to the lead, the main session. A subagent reads PLAN.md only when its brief names it, and a
    reviewer never.
  - **Resolution: done** (2026-11-19).
    - **Test:** none: a change of docs alone (AGENTS.md, Running the tests); the doc tests pass (313).
    - **Cause:** the rule was written for the lead, but AGENTS.md is loaded into every agent, and the rule named no reader.
    - **Fix:** AGENTS.md's paragraph makes PLAN.md the lead's, the main session's: a subagent reads it only when its brief names it, and a reviewer never (the user, 2026-11-19).
    - **Also covered:** the agent files name no PLAN.md; the review skill's briefs (step 3) don't either.
  - Questioned by AGT-21 (2026-11-19).
- [x] **TST-560 · "git history keeps it" is false for a plan the squash merge deletes** · `AGENTS.md:94` · confirmed · found 2026-11-19
  - **Defect.** "The squash merge into `main` deletes PLAN.md, so `main` never holds a finished branch's plan; git
    history keeps it." Branches are deleted after their squash merge (the repository holds only `main` and this
    branch; origin only `main`), and this branch's PLAN.md isn't committed. A plan deleted before the squash is in no
    commit that survives. Earlier plans survived only because they were committed into `main` (4db5fd5, then deleted
    in 9446b2c).
  - **Scenario.** This branch's "Settled with the user" list and its ideas from the tutorial's hooks are lost at the
    merge; a later review raises the runner's write tools again (this review did, as Unspecified).
  - **Fix.** The user decides: commit PLAN.md with the squash and delete it in a commit after, as a cleanup of
    REVIEW.md works; or narrow the sentence and say to move what must last into DECISIONS.md or ROADMAP.md first.
  - **Resolution: done** (2026-11-19).
    - **Test:** none: a change of docs alone (AGENTS.md, Running the tests); the doc tests pass (313).
    - **Cause:** the sentence assumed the plan survives in the branch's history, but branches are deleted after their squash merge.
    - **Fix:** the user decided (2026-11-19) that PLAN.md is the branch's memory and dies with it: it may be committed on the branch, never enters `main`. AGENTS.md says so, and that what must outlast the branch goes into DECISIONS.md or ROADMAP.md before the merge. No DECISIONS.md entry: AGENTS.md's rule answers it.
    - **Also covered:** PLAN.md's own header says the merge deletes it, which holds.
  - Questioned by TST-569 (2026-11-19).
- [x] **TST-569 · The squash merge doesn't leave PLAN.md out by itself, and no doc names the step that does · follows TST-560, generation 2** · `AGENTS.md:96`, PLAN.md's header · confirmed · found 2026-11-19
  - **Defect.** "It may be committed on the branch, but never enters `main`: the squash merge leaves it out." A squash merge takes the branch's whole tree: 4db5fd5 brought an earlier PLAN.md into `main` (362 lines), and 9446b2c deleted it later. PLAN.md's header says "the squash merge into `main` deletes it" (TST-560's Also covered took it as holding).
  - **Scenario.** The lead commits PLAN.md on the branch, as the rule allows; the squash brings it into `main`, and the next session, told to read it first and continue from it, continues a finished plan.
  - **Fix.** Name the step and who takes it: before the squash merge, the lead moves what must last into DECISIONS.md or ROADMAP.md, then deletes PLAN.md in the branch's last commit. PLAN.md's header says the same.
  - **Resolution: done** (2026-11-19).
    - **Test:** none: a change of docs alone (AGENTS.md, Running the tests); the doc tests pass.
    - **Cause:** TST-560's fix described the rule's outcome as a property of the squash merge, which takes the branch's whole tree.
    - **Fix:** AGENTS.md names the step and who takes it: the lead moves what must outlast the branch into DECISIONS.md or ROADMAP.md, then deletes PLAN.md in the branch's last commit, before the merge. PLAN.md's header and its last step say the same.
    - **Also covered:** no skill or agent file describes the merge; TST-560's Also covered (the header "holds") is corrected by this fix.

- [x] **AGT-16 · tail's old `+Nf` syntax follows a file forever, and the guard lets it through** · `.claude/hooks/read_only_bash.py:123, 267` · measured · found 2026-11-19
  - **Defect.** `Forbidden(long=('--follow',), short='fF')` looks for the letters only in an argument matching `-[^-]`. macOS tail still takes its historic syntax, where `+1f` means `-f -n +1`.
  - **Scenario.** In a scratch folder, `tail +1f f` and `tail +1F f` were still running after 3 s, while `tail -n +1 f` ended at once; `refusal('tail +1f AGENTS.md')` and `refusal('tail +5F AGENTS.md')` are None. A reading agent's call then waits until the Bash timeout, or forever in the background (AGT-17). The docstring says `tail -f` is refused.
  - **Fix.** For tail, look for the letters in an argument starting with `+` too; refused cases `tail +1f x` and `tail +5F x`; the docstring's short-options bullet says so.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_the_guard_blocks_any_other_command[tail +1f ...]`, `[tail +5F ...]` and `[tail +1cf ...]` returned None before the fix; `tail +5 AGENTS.md` stays allowed.
    - **Cause:** short letters were looked for only in an argument matching `-[^-]`, while macOS tail still reads its historic `+N[bcl][fFr]` syntax.
    - **Fix:** `Forbidden(plus=True)` for tail refuses `f` and `F` in an argument starting with `+`; the message says macOS tail reads `+Nf` as `-n +N -f`; the docstring's short-options bullet says so. Measured: `tail +1f`, `+1F`, `+1cf` and `-1f` ran forever; `+5` and `+5r` ended; `tail +f f` took `+f` as a file.
    - **Also covered:** no other reader in READERS has a `+` syntax that waits (`sort +1`, `uniq +5` are key and skip forms; uniq's `+5` counts as a file under `_second_file`). The lead checked `tail +1f AGENTS.md` refused and `tail +5 AGENTS.md` allowed after the fix.

- [x] **AGT-17 · The guard ignores `run_in_background`, so output with no end runs without a timeout · follows AGT-12, generation 2** · `.claude/hooks/read_only_bash.py:22-23, 49`, `_command` · confirmed · found 2026-11-19
  - **Defect.** `_command` reads only `tool_input['command']`. AGT-12's fix says "`cat /dev/zero` passes, and prints until the Bash call's timeout", but a background call has no foreground timeout. Claude Code's tools reference: a command's output streams to a working file, and a command whose output passes 5 GB is killed.
  - **Scenario.** A reading agent starts `cat /dev/zero`, `jq -n 'repeat(1)'` or `tail +1f x` with `run_in_background`: up to 5 GB written to disk, or a process that runs until stopped. The shell's own `&` is refused for the same reason (`:49`).
  - **Fix.** Refuse a call whose `tool_input.run_in_background` is true (a reading agent has no need of it); `run_in_background` in `HookInput`, and a hook test exiting 2; the docstring sentence says what bounds the output.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_a_command_run_in_the_background_is_blocked` failed (no `call_refusal`), and `test_the_hook_exits_0_to_let_through_and_2_to_block`'s background case exited 0.
    - **Cause:** the guard read only `tool_input.command`.
    - **Fix:** `call_refusal(call)` refuses a call whose `run_in_background` is anything but absent or false, and `main` calls it; the docstring says a background command has no timeout and its output streams to a file until 5 GB (Claude Code's tools reference). `analyst.md` and `reviewer.md` say to run each command in the foreground.
    - **Also covered:** the research nudge counts a Bash call through `call_refusal`, so the lead's background reads don't count.
  - Questioned by AGT-24 (2026-11-19).

- [x] **AGT-18 · The runner is told to stop a background task through its handle, but has no tool for it** · `.claude/agents/runner.md:4, 26-30` · measured · found 2026-11-19
  - **Defect.** "A process started in the background stops through the handle that started it." The runner's tools are Bash, Read, Write and Designer's: no TaskStop.
  - **Scenario.** A probe: a `runner` started two background tasks, was woken when the first ended (exit code 3, status `failed`, its output file named), and reported it had no tool to stop the second (`sleep 120`); the lead stopped it with TaskStop by its handle. A hung suite can't be stopped by the runner, and its Designers stay up.
  - **Fix.** Give the runner TaskStop (measure that a subagent can use it), with `TaskStop` in `test_agents.py`'s BUILT_IN; or have `runner.md` report a hung task's handle to the lead, which stops it (measured).
  - **Resolution: done** (2026-11-19).
    - **Test:** `test_every_tool_an_agent_names_exists` failed with `{'runner': ['TaskStop']}` once the lead added `TaskStop` to `runner.md`'s tools; the developer added it to `BUILT_IN`. Measured: a `runner` started `sleep 120` in the background and stopped it with TaskStop ("Successfully stopped task").
    - **Cause:** `runner.md` told the runner to stop a background task through its handle, but its tools held none for it.
    - **Fix:** `TaskStop` in the runner's tools; `runner.md` says a notification wakes it when a background task ends, with its exit code and output file, and to stop a hung run with TaskStop and the task's ID (both measured).
    - **Also covered:** the lead can stop a subagent's background task by its ID too (measured in the second review); the developer starts no background suite.

- [x] **AGT-23 · A Read of a `~/` path passes the size check, as the hook joins it to the cwd** · `.claude/hooks/large_reads.py:242`, `_path` · measured · found 2026-11-19
  - **Defect.** `read_refusal` measures `_path(folder, file_path)`, which joins `~/x` to the call's `cwd`: `<cwd>/~/x` doesn't exist, so `os.stat` raises and the read passes as a missing file. Read itself expands a leading `~`: the lead's `Read('~/Tools/substance-designer-mcp/mypy.ini', limit=3)` returned the file's first 3 lines. The docstring lists no `~` case among the reads that pass, and AGENTS.md says a read returning over 20 KB is refused.
  - **Scenario.** The lead reads `~/.claude/projects/<slug>/<session>.jsonl` (the review skill and the agent files name such `~/.claude/projects/...` paths): hundreds of KB reach its context, unchecked.
  - **Fix.** Expand a leading `~` for Read, as Read does (measure a path with a leading space, and PyCharm's `read_file` with `~`, first); a test with a big file under a patched `HOME`. Authority: the module's docstring and AGENTS.md's "before a read" bullet.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_reads_leading_tilde_names_the_home_folder_and_read_files_doesnt` failed: the hook let a Read of `~/big.py`, a 32 KB file in a patched home folder, through as a missing file.
    - **Cause:** `read_refusal` joined Read's `file_path` to the call's `cwd` as written, so `~/x` named `<cwd>/~/x`.
    - **Fix:** `_home` takes the blanks off around Read's path and expands a leading `~/`, as Read does. Measured by the developer: Read read `~/x`, ` ~/x`, a tab before `~/x` and ` /abs/x`, and didn't expand `~user/x`; PyCharm's `read_file` found no file at `~/x`, so its path isn't expanded. The module's docstring records both.
    - **Also covered:** the blanks around any Read path (` /abs/x` passed before as a relative path). `bash_refusal`'s `cat ~/x` still passes unsized, as its docstring says of a word the shell expands.

- [x] **AGT-24 · A foreground command past its timeout moves to the background, so a reading agent's command that never ends runs on · follows AGT-17, generation 3** · `.claude/hooks/read_only_bash.py:23-25`, `.claude/agents/analyst.md:4`, `.claude/agents/reviewer.md:4` · measured · found 2026-11-19
  - **Defect.** The guard's docstring says "`cat /dev/zero` passes, and prints until the Bash call's timeout", and AGT-17's fix refuses only `run_in_background`. Measured: the lead's foreground `python3 -c 'import time; time.sleep(120)'` with `timeout: 3000` "did not complete within its 3s timeout and was moved to the background"; the process ran until the lead stopped it with TaskStop. Claude Code's tools reference ("Foreground commands that move to the background", "When a background command stops"): the move is the default, except for a command starting with `sleep`; a foreground subagent's moved command stops when its run ends, a background subagent's keeps running after its final response, with no time limit in a local session, until it exits, is stopped, or passes 5 GB of output. The only switch, `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`, is session-wide and also removes `run_in_background` and background subagents.
  - **Scenario.** A reviewer, started in the background as the review skill does, runs `cat /dev/zero`, `cmp /dev/zero /dev/zero` or `jq -n 'repeat(1)'`, which the guard passes: at the timeout it moves to the background and writes up to 5 GB to the task's output file. The analyst and the reviewer have no TaskStop to end it (nor has the developer). A code effect, so the generation-3 narrowing doesn't apply.
  - **Fix.** TaskStop in the analyst's and the reviewer's tools, with a line in each to stop a command moved to the background (and `test_agents.py`'s pins); the guard's docstring says what the timeout does. Alternatives for the user: refuse the words naming a device under `/dev/` but `/dev/null`; or accept it and say so. Authority: the guard's docstring; AGENTS.md, Wait for callbacks (a limit is a safety net).
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_agents.py::test_an_agent_with_bash_can_stop_a_command_moved_to_the_background` failed for the analyst, the developer and the reviewer: no TaskStop.
    - **Cause:** only the runner could stop a background task, and the reading agents' files relied on the guard.
    - **Fix:** the user's choice (DECISIONS.md, No agent has a write guard): the guard is deleted, with its docstring. TaskStop is in the analyst's, the reviewer's and the developer's tools, and each file says that a command outliving its timeout is moved to the background and keeps running (Claude Code's tools reference, "Foreground commands that move to the background"), to stop it with TaskStop once it isn't needed, and before reporting.
    - **Also covered:** the runner had TaskStop and its line already; the test checks every agent with Bash.

- [x] **TST-580 · The review skill's diff commands print PLAN.md to the reviewers** · `.claude/skills/project-code-review/SKILL.md:63-72` · confirmed · found 2026-11-19
  - **Defect.** The Scope gives `git diff <commit>` with the new files `git status --short` lists, `git diff main...<branch>` and `git diff $(git merge-base main HEAD)`, none leaving out PLAN.md, which is tracked on the branch (`git ls-files PLAN.md`). AGENTS.md and `reviewer.md` (Review blind) say a reviewer never reads it.
  - **Scenario.** A reviewer runs its brief's command and reads the lead's account, its verdicts and the decisions it took alone: the anchoring blind review exists to avoid.
  - **Fix.** Each command takes `-- . ':(exclude)PLAN.md'`, and a PLAN.md in `git status` is never read. Authority: AGENTS.md (A branch's plan); `reviewer.md`, Review blind.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_agents.py::test_every_diff_command_the_review_skill_gives_leaves_plan_md_out`, failing first on the three commands.
    - **Fix:** each Scope command ends `-- . ':(exclude)PLAN.md'`, and a PLAN.md `git status --short` lists is never read; `git diff --stat 849879f 9910caa` lists PLAN.md, the same with the pathspec doesn't.
  - Questioned by TST-593 (2026-11-19).

- [x] **AGT-51 · Three files give three timings for a DECISIONS.md entry, a won't-fix or a ROADMAP item** · `AGENTS.md:239-245`, `.claude/skills/project-code-review/SKILL.md:199-207`, `.claude/skills/address-review/SKILL.md:141-154, 171-172` · confirmed · found 2026-11-19
  - **Defect.** AGENTS.md lists them among what stops the loop, then says a decision that doesn't block the next step waits in PLAN.md; step 8 holds them until convergence ("Until then PLAN.md holds it"); `address-review` proposes them "now", "in the same change as the REVIEW.md resolution" and "in the same report". Found by two reviewers.
  - **Scenario.** A not-a-bug entry or a ROADMAP item that blocks nothing: one file stops the loop for it, one holds it, one ties it to the developer's report, which ends before the user answers.
  - **Fix.** One rule, in one home, from the user's words ("interrupt me only if strictly needed and cannot wait until reviews converge"): such proposals wait in PLAN.md for convergence unless one blocks the next step, and the lead adds what the user approves. The stop list keeps only what blocks; `address-review` drops "now" and "in the same change"; "records ... all but what stops the loop" says "decides". Authority: the user, 2026-11-19; AGENTS.md, Keeping the docs current.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** one home, AGENTS.md's "The loop is the lead's": the stop list, now a list, keeps what blocks; a DECISIONS.md entry, a won't fix or a ROADMAP item waits in PLAN.md and is asked at convergence, the lead adding what the user approves. `address-review` drops "now" and "in the same change"; the review skill's step 8 points to AGENTS.md.
    - **Test:** docs; the docs tests passed (574).

- [x] **AGT-73 · The story's copy table drops rules the setup depends on, and starts DECISIONS.md empty while the copied files cite it** · `docs/agent-workflow.md:180, 186` · confirmed · found 2026-11-19
  - **Defect.** It keeps AGENTS.md's Working on this project, Running the tests, Delegating to subagents, Keeping the docs current and Writing docs, and calls Deploying and diagnosing project-specific: that section holds How changes reach the agents, which the story's own lesson rests on; the commit rule (AGENTS.md's opening) is above the listed sections; "Start empty" for DECISIONS.md, while `analyst.md`, `reviewer.md` and AGENTS.md cite its entries No agent has a write guard and Project rules.
  - **Scenario.** Another repository's lead restarts agents on stale definitions, has no commit rule for its safety net, and its reviews raise the write guard again.
  - **Fix.** Name How changes reach the agents and the commit paragraph among what to keep; carry over DECISIONS.md's setup entries (no write guard, the two-stage tests, the low-value findings). Authority: Step C's text ("what each needs changed for another project").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead). Docs alone: the docs tests passed (606).
    - **Fix:** the copy table's AGENTS.md row keeps the commit rule, the merge, and How changes reach the agents; DECISIONS.md has its own row: carry over its introduction and the three setup entries (the two stages of tests, low-value findings not raised, no write guard), each approved anew by the other project's user; REVIEW.md starts without findings, ROADMAP.md empty.
  - Questioned by TST-626, TST-629 (2026-11-20).

- [x] **AGT-74 · The story's step 3 contradicts its own "Who decides what" on changes to a step** · `docs/agent-workflow.md:35-37, 96-98` · confirmed · found 2026-11-19
  - **Defect.** "no detail is added to a step afterwards without the user", against "The lead decides alone ... a developer's proposed change that keeps that goal and what users see" (AGENTS.md, The loop is the lead's, stops only for a change beyond the plan); "each sized for one developer run, with its goal and its acceptance criteria" appears in no setup file; "how to implement within the plan's goal" is listed as the lead's, while `developer.md` says how to implement its unit is the developer's.
  - **Scenario.** One lead stops for the user on every slight change; another doesn't.
  - **Fix.** Step 3 says what AGENTS.md says: a change beyond what the plan delivers goes to the user; drop or cite the sizing; the lead decides on the developer's proposed changes, the developer on how it implements. Authority: AGENTS.md, The loop is the lead's.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead). Docs alone: the docs tests passed (606).
    - **Fix:** step 3 says what AGENTS.md says (every step in full detail, the user's approval, a change beyond what the plan delivers to the user); the sizing claim dropped; Who decides what opens with the developer deciding how it implements, then the lead deciding what isn't the user's, the user's list matching AGENTS.md. **Also covered:** the list's unsupported items dropped.
  - Questioned by TST-630 (2026-11-20).

- [x] **AGT-81 · Nothing makes the lead load the `delegate` skill before a loop decision that isn't an agent's start** · `AGENTS.md:63-64, 143`, `.claude/skills/delegate/SKILL.md:3` · confirmed · found 2026-11-19
  - **Defect.** AGENTS.md's one trigger: "Before starting an agent, load the `delegate` skill"; the skill's description adds "while the lead runs its loop". Step D moved the loop's stop list there (beyond the plan, a cost over the announced, asking at once in doubt), and AGENTS.md keeps no copy. A session's start or a compaction has the lead read PLAN.md and continue, and a round of fixes resumes the developer, which isn't a start.
  - **Scenario.** After a compaction drops the skill, the lead settles a report or meets a change to the plan, and decides alone what the stop list reserves for the user.
  - **Fix.** One trigger in both places: before starting or resuming an agent, and before continuing the loop from PLAN.md (a session's start, a compaction), load the `delegate` skill. Authority: `.claude/rules/docs.md` (a skill is named where the work comes up); the user's decision that the loop stops for what is theirs.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_agents_md_and_the_delegate_skill_give_the_same_triggers`, failing first in both cases. **Fix:** AGENTS.md and the skill's description: before starting or resuming an agent (the Agent tool, or SendMessage), and before continuing the loop from PLAN.md (a session's start, a compaction), load the `delegate` skill.

- [x] **TST-617 · The story has an analyst check the quoted lines so the lead doesn't open them, against the rules** · `docs/agent-workflow.md:46-49` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** Flow step 5: "An analyst can check that twenty quoted lines are where the reviewers say, so the lead doesn't open twenty places." `project-code-review`, Who settles what: the lead "reads the lines each suspicion quotes itself"; AGENTS.md, Keep it yourself: "The cost of reading is never a reason to skip it."
  - **Scenario.** An agent setting up another repository from the story has an analyst confirm locations, and its lead settles suspicions it never read.
  - **Fix.** Delete the sentence, or say an analyst may check that the locations exist before the lead reads each quoted line. Authority: the two rules; `.claude/rules/docs.md` (the setup's files win).
  - **Resolution: done** (2026-11-20, by the lead, who writes the story).
    - **Fix:** the sentence deleted; flow step 5 keeps "The lead reads the lines each one quotes". **Test:** the docs tests (a sentence removed).

- [x] **TST-629 · The story's copy table has a copier replace skills and rules that the copied files point to · follows AGT-73, generation 2** · `docs/agent-workflow.md:201`, `:206`, `:207` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** "Replace it with the new project's own way of running its integration tests and the full suites" (`live-check`), "Write the new project's rules" and "replace the project's own rules and pointers" (AGENTS.md) drop setup sections the copied files cite: `live-check`'s How a probe runs (`project-code-review`, `address-review`) and When the final check fails (`developer.md`); `python.md`'s Simplify the change, `docs.md`'s Keeping the docs current and Writing docs and comments, `docs-tests.md` (the agent files, the `delegate` brief, `cleanup-review`); AGENTS.md's opening commit rule and its PLAN.md paragraph. The table at `279087c` kept them; Step C's rewrite dropped them, and TST-626 restored only DECISIONS.md.
  - **Scenario.** The receiving agent follows the cells; its review skill points to a probe procedure that no longer exists, and nobody is assigned to final-check failures.
  - **Fix.** Each row names the setup sections to keep. Authority: AGT-73; Step C ("what each needs changed").
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Fix:** each copy-table row names the setup sections the copied files point to: AGENTS.md's commit rule, tests first, the self-review, PLAN.md and REVIEW.md, the two stages and Delegating to subagents; `live-check`'s The suites, How a probe runs, When the final check fails and the crashed-program section; `python.md`'s Simplify the change, `docs.md`'s two sections, `docs-tests.md`. **Test:** the docs tests.

## Low

- [x] **AGT-4 · The note after a big Bash output never comes for a command that fails** · `.claude/hooks/large_reads.py:42`, `AGENTS.md:235` · measured · found 2026-11-19
  - **Defect.** The hook is registered on PostToolUse, which Claude Code doesn't run for a Bash call that exits
    non-zero. Both texts say every output of 8,000 characters or more that reached the context whole gets the note.
  - **Scenario.** In the lead's session, `head -c 8100 /dev/zero | tr '\0' x; exit 1` reached the context whole and
    got no note; a 9 KB output of a command that succeeded got one (2026-11-18). A failing test run, often the largest
    output, gets none.
  - **Fix.** Register the hook on PostToolUseFailure too, if its payload carries the output (measure it first), or
    narrow both sentences to a command that succeeds.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_a_failing_commands_output_gets_the_note_too`, `test_a_failing_commands_output_cut_short_is_at_least_its_size`, `test_a_subagents_bash_output_gets_none` (a failed call), `test_the_hook_exits_2_to_refuse_a_read_and_prints_the_note_as_json` (the PostToolUseFailure JSON) and `test_the_settings_register_...`: all failed before the fix.
    - **Cause:** the hook was registered only on PostToolUse, which a failed Bash call never gets (measured by the lead: a failing call fires `PostToolUseFailure`, whose `error` holds "Exit code N" and the output cut to about 10,000 characters, and whose `additionalContext` reaches the context).
    - **Fix:** `.claude/settings.json` registers the hook on `PostToolUseFailure` too; `bash_note` sizes `error` after its `Exit code N` line; from FAILURE_CUT (10,000) on, the note says "at least". `_answer` prints the event's own `hookEventName`. AGENTS.md's sentence says the note comes whether the command succeeded or failed. The measurements are in the docstring.
    - **Also covered:** the measurement also showed a failing output is never saved to a file (a 40,001-character one reached the context as about 20 KB, cut in the middle): the docstring and AGT-5's message take it into account.

- [x] **AGT-5 · The Bash refusal says the output would fill the context, but Claude Code saves a big one to a file** · `.claude/hooks/large_reads.py:157` · confirmed · found 2026-11-19
  - **Defect.** "this command would print %d KB ... into your context, and over %d KB fills it". The docstring's own
    measurement: a 60 KB output was saved to a file, and only a 2 KB preview reached the context.
  - **Scenario.** `cat` of a 60 KB file is refused as putting 60 KB into the context; it would put 2 KB.
  - **Fix.** Say what happens past Claude Code's limit (saved, with a 2 KB preview), or refuse only up to it (measure
    the limit first: a 30,000-character cut was seen).
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** the Bash refusal must say "only part" and not "fills": it failed on "...into your context, and over 20 KB fills it".
    - **Fix:** "...and a command printing over 20 KB of files is refused. Claude Code puts an output into your context whole up to a size it sets, and only part of a bigger one." No threshold is claimed.
    - **Also covered:** the read refusal said "fills your context" too; it now says "a read over 20 KB is refused", line numbers included.

- [x] **AGT-6 · A quoted word starting with `#` ends the command line, so a big `cat` after it isn't sized** · `.claude/hooks/large_reads.py:31-32, 314` · measured · found 2026-11-19
  - **Defect.** `shlex` takes the quotes off before `token.startswith('#')`, so a quoted `'# type: ignore'` is read as a
    comment and the rest of the line is dropped. The docstring says a word starting with `#` begins a comment "as in
    the shell"; the shell doesn't treat a quoted one so.
  - **Scenario.** A probe: `cat big.py` (30 KB) is refused, `grep -c '# type: ignore' a.py && cat big.py` passes.
  - **Fix.** Find the comment before the quotes are taken off (a `#` starting an unquoted word), or give such a line
    up as unsized instead of dropping its tail; narrow the docstring's sentence.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `[grep -c '# type: ignore' small.py && cat big.py]`, `["#"]` and `[\#]` returned None; `[x'#']`, `[x#y]`, `[cat big.py;# a comment]` and `[echo # ; cat big.py]` pin the scanner (the last fails without `_comment`).
    - **Cause:** `shlex` took the quotes off before the `#` check.
    - **Fix:** `_comment` finds the shell's comment on the raw line (outside quotes, not after a backslash, at a word start after a blank or an operator); `shlex` gets only the text before it.
    - **Also covered:** a quoted operator word (`'>'`, `'|'`) still counts as an operator, so such a line passes unsized: already in the docstring, and a pass is the accepted direction. One scanner in place of `shlex` would close it, a behaviour change left to the user.

- [x] **AGT-7 · Two comments say what the size checks don't do** · `.claude/hooks/large_reads.py:107`, `tests/unit/test_large_reads.py:298` · confirmed · found 2026-11-19
  - **Defect.** `SEPARATORS = (';', '&&', '||')  # between commands whose outputs all reach the context`: the right
    side of `||` runs only when the left fails, and the hook counts both (an upper bound, `test_large_reads.py:277`).
    `'cat big.py > out.txt',  # other hooks and checks handle redirections`: no hook or check handles a redirection in
    a main session; the guard is the reading agents' only.
  - **Scenario.** A reader takes `cat a.py || cat b.py` (15 KB each) as printing 30 KB, and a redirection as checked
    elsewhere.
  - **Fix.** Say that `||` counts both sides, as an upper bound; say a redirection passes unsized, as the docstring
    does.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: comments only.
    - **Fix:** SEPARATORS' comment and the docstring say both sides of `||` add up, though the right side runs only when the left fails; the test comment says "a redirection: the hook doesn't size the line".

- [x] **AGT-8 · PyCharm's whole read is sized by the whole file, though PyCharm shows at most 2,000 lines** · `.claude/hooks/large_reads.py:132-137` · confirmed · found 2026-11-19
  - **Defect.** A read with neither `offset` nor `limit` is sized by the file for both tools. PyCharm's `read_file`
    shows at most 2,000 lines, half from each end (the docstring's measurement), which `_pycharm_returns(path, None,
    None)` already models.
  - **Scenario.** A file of 5,000 lines of 8 bytes (40 KB) is refused for PyCharm, whose read would return 16 KB.
  - **Fix.** Size a whole PyCharm read with `_pycharm_returns`.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_pycharms_whole_read_is_sized_by_the_2000_lines_it_shows` failed: the read was refused by the whole file's size. 15,000 lines of 2 bytes pass for PyCharm (about 18 KB shown) and are refused for Read; 3,000 lines of 100 bytes are refused with "2000 lines".
    - **Fix:** no whole-read branch: PyCharm's read always goes through `_pycharm_returns`.
    - **Also covered:** measured that a whole Read returned all 2,006 lines of a 2,005-line file: Read has no 2,000-line cap, and its whole read stays the whole file.

- [x] **AGT-9 · "A read that returns over 20 KB is refused": the line numbers Read adds aren't counted** · `.claude/hooks/large_reads.py:9`, `AGENTS.md:230` · confirmed · found 2026-11-19
  - **Defect.** The hook sums the lines' bytes. Read returns each line with its number and a tab (about 7 characters).
    Only PLAN.md, deleted at the merge, says so.
  - **Scenario.** A file of 2,000 lines and 17 KB passes, and its read returns about 31 KB.
  - **Fix.** Count the numbers (Read's and PyCharm's formats), or narrow both sentences to the bytes of the lines read.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_the_line_numbers_count_in_the_size` failed (None): 2,000 lines of 8 bytes give 31 KB and 2,001 lines for Read, 29 KB and 2,000 lines for PyCharm. The other tests' sizes updated (the limit's edge now 19,993/19,994 bytes).
    - **Cause:** the sizes summed the lines' bytes only.
    - **Fix:** `_numbered` numbers the lines as each tool does, with the empty line after a last newline (measured: Read showed it, line 2006): Read `%6d\t` (its tool description, not measured), PyCharm `L%d: ` and its `...N lines truncated...` line (measured by the lead). The early pass of a file of 20 KB or less is gone, since the numbers can take it over. AGENTS.md's sentence says the line numbers count.
  - Questioned by AGT-19 (2026-11-19).
- [x] **AGT-10 · The user's memory index is loaded for subagents; four sentences say it isn't** · `AGENTS.md:202-203`, `.claude/agents/analyst.md:40`, `reviewer.md:42`, `developer.md:29` · measured · found 2026-11-19
  - **Defect.** "Each loads AGENTS.md, but not the conversation, nor the user's memory index"; the agent files: "It
    isn't loaded for you".
  - **Scenario.** The transcripts of this review's three reviewers, and of the developer earlier, start with the
    memory index's contents beside AGENTS.md. The memory files it links aren't loaded.
  - **Fix.** Say the index is loaded, and to read the memory files it links that touch the task.
  - **Resolution: done** (2026-11-19).
    - **Test:** none: a change of docs alone (AGENTS.md, Running the tests); the doc tests pass (313).
    - **Cause:** the sentences followed the docs read when the agents were written, not what Claude Code gives a subagent.
    - **Fix:** AGENTS.md says each agent loads the memory index, `MEMORY.md`, not the files it links; `analyst.md`, `developer.md` and `reviewer.md` say the index is loaded and where the linked files are.
    - **Also covered:** `runner.md` names no memory file.

- [x] **AGT-11 · Subagents get AGENTS.md as the session loaded it, not as edited since** · `AGENTS.md:345-347` · measured · found 2026-11-19
  - **Defect.** The bullet "How changes reach the agents" covers the agent files only. AGENTS.md reaches a subagent as
    the session last loaded it.
  - **Scenario.** This review's three reviewers got AGENTS.md without step 5's guard paragraph and this bullet, and
    with the sentence step 7 changed ("Only the `developer` starts agents..."), though both edits were on disk before
    they started. Rules edited in a session reach later agents only after the session loads AGENTS.md again (the
    reviewers' copy matched the one loaded at the session's compaction).
  - **Fix.** Add to the bullet that an edit of AGENTS.md reaches the agents started after the session next loads it
    (a compaction did; measure whether anything else does).
  - **Resolution: done** (2026-11-19).
    - **Test:** none: a change of docs alone (AGENTS.md, Running the tests); the doc tests pass (313).
    - **Cause:** the bullet was written from a measurement of the agent files only.
    - **Fix:** the bullet says AGENTS.md reaches an agent as the session last loaded it, with the measurement, and to put a new rule in the brief of the agents started before the session loads it again.
    - **Also covered:** the review skill's step 3 says AGENTS.md is loaded for each reviewer, which holds.

- [x] **AGT-12 · The guard's docstring says it refuses what waits forever, but devices pass** · `.claude/hooks/read_only_bash.py:21`, `tests/unit/test_read_only_bash.py:105` · confirmed · found 2026-11-19
  - **Defect.** "if none of its arguments writes a file, deletes one, starts a program or waits forever". Only the
    options listed in FORBIDDEN are refused: `refusal('cat /dev/zero')` is None, as is a read of a FIFO or
    `/dev/tty`.
  - **Scenario.** `cat /dev/zero` prints until the Bash call's timeout.
  - **Fix.** Narrow the sentence to the listed options, or refuse arguments under `/dev/`.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_the_guard_reads_the_words_not_the_files_they_name`: `cat /dev/zero` passes and the docstring must say so; it failed on the docstring.
    - **Cause:** the docstring claimed whatever "waits forever" is refused.
    - **Fix:** the docstring and Forbidden's docstring narrowed to the listed arguments (those that write, delete, start a program, or wait for keys or more lines: ugrep's `-Q`, `tail -f`); the guard reads words, not the files they name.
  - Questioned by AGT-17 (2026-11-19).
- [x] **AGT-13 · The guard refuses patterns and option values holding a forbidden letter, saying they write** · `.claude/hooks/read_only_bash.py:79, 226, 228` · confirmed · found 2026-11-19
  - **Defect.** The `short` letters are looked for in every argument starting with `-`, not only in clusters of
    options (the comment at `:79` says "in a cluster"), and the message says the argument "writes a file, deletes one,
    starts a program or waits forever".
  - **Scenario.** `grep -eQuery x .` is refused with "-eQuery writes a file, ...", as are `git grep -eOpen` and
    `sort -T/tmp/o`. The refusal is safe; the message misleads the agent.
  - **Fix.** Say what was matched and how to pass it (a value given apart from its option).
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `[grep -eQuery x .]`, `[git grep -eOpen x]` and `[sort -T/tmp/o x]` expect "the letter Q in -eQuery"; they failed on "-eQuery writes a file...". New allowed cases: `grep -e Query x .`, `git grep -e Open x`, `sort -T /tmp/o x`.
    - **Fix:** a message of its own, naming the letter and how to pass a value ("given apart from its option (-e Query, not -eQuery)"); Forbidden.short's comment and a docstring bullet match it.

- [x] **AGT-14 · The guard's docstring and an allowed test case give `review_lookup.py` several IDs; it takes one** · `.claude/hooks/read_only_bash.py:18`, `tests/unit/test_read_only_bash.py:34` · confirmed · found 2026-11-19
  - **Defect.** "with finding IDs or `--last-used`", and the allowed case `python3 scripts/review_lookup.py HLP-56
    TST-1`. `scripts/review_lookup.py:129` declares `nargs='?'`.
  - **Scenario.** The command the test allows exits 2 with "unrecognized arguments".
  - **Fix.** Say "a finding ID", and use one in the test.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `[python3 scripts/review_lookup.py HLP-56 TST-1]` and `[python3 scripts/review_lookup.py]` expect "one finding ID"; both returned None. The allowed case is `HLP-56` alone.
    - **Cause:** the guard took any number of IDs; review_lookup takes one (`nargs='?'` in a required group).
    - **Fix:** exactly one argument, an ID or `--last-used`; the docstring says "a finding ID".

- [x] **AGT-15 · `reviewer.md`'s rule to search for every instance reads as covering only the two patterns before it** · `.claude/agents/reviewer.md:57-60` · confirmed · found 2026-11-19
  - **Defect.** The old step 3 of `project-code-review` said "A defect that recurs ... is **one** finding listing every
    location". `reviewer.md` puts "Search for each pattern elsewhere: one finding lists every location" after "the
    list in the `address-review` skill's step 6 ..., and these two".
  - **Scenario.** A reviewer reports a recurring defect outside those lists once per location.
  - **Fix.** State it as a rule of its own, for every finding.
  - **Resolution: done** (2026-11-19).
    - **Test:** none: a change of docs alone (AGENTS.md, Running the tests); the doc tests pass (313).
    - **Cause:** the old step 3's rule moved into a sentence about two listed patterns.
    - **Fix:** `reviewer.md`'s "What to hunt for" ends with a rule of its own: a recurring defect is one finding, and every finding's pattern is searched for elsewhere.
    - **Also covered:** the rest of the old step 3 is in `reviewer.md` (the review log's "Checked and found fine").

- [x] **TST-561 · A test makes a folder named `jar:`, which Windows refuses** · `tests/unit/test_large_reads.py:193` · confirmed · found 2026-11-19
  - **Defect.** `_big(tmp_path / 'jar:' / 'big.class')`: Windows file names can't hold `:`, and the test has no
    `win32` skip. The Windows simulation runs on macOS and can't see it; the same file already leaves out `*` and `?`
    on `win32` (`:340`).
  - **Scenario.** A unit run on Windows errors in `test_a_url_or_an_archive_entry_passes_even_where_a_file_has_that_name`.
  - **Fix.** Leave out that case on `win32`, with the reason, as `:340` does.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none can fail on macOS, as the entry says; `test_windows_simulation` passes.
    - **Fix:** the `jar:` folder is made only off `win32`, with the reason, as the file does for `*` and `?`.

- [x] **TST-562 · Tests that pass without the code they guard** · `tests/unit/test_large_reads.py:230, 302-303`, `tests/unit/test_read_only_bash.py:81-105` · confirmed · found 2026-11-19
  - **Defect.**
    - `{'offset': 0, 'limit': 250}` of `test_a_range_pycharms_read_file_refuses_passes`: without the `first < 1`
      guard, the hook sizes the last line (100 bytes, measured) and passes the read anyway;
    - `cat \`echo big.py\`` and `cat $(echo big.py)` pass without the expansion check: no file is named `` `echo ``,
      and `(` makes the line unsized;
    - every long option the guard's tests refuse has 6 characters or more, so `SHORTEST` could be 5 or 6; `tail -F`,
      `--query`, `-okdir`, `-fprint0`, `-fprintf`, `\r` and a backtick inside double quotes have no case.
  - **Scenario.** A typo in any of those entries, or a guard removed, passes the suite.
  - **Fix.** A case each that fails without its code: an `offset` of 0 on a file whose last line alone is over 20 KB;
    the expansion cases with a file of the expanded name; `git grep --op=true x` (AGT-1) and the missing entries.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** the tests' own fixes; the pins were checked against copies of the hook with each guarding line removed, by the developer's scratch mutation script: every pin fails there.
    - **Fix:** the guard: cases for `tail -F`, `grep --query`, `-okdir`, `-fprint0`, `-fprintf`, `\r`, a backtick inside double quotes, `sort --output` and `git grep --op=true`. The size checks: a file whose last line alone is 25,000 bytes pins `offset` 0 and -1, `limit` -1 and 5001 (`limit` 0 shows nothing either way in the new code); files named `` `echo `` and `` big.py` `` pin the backtick in EXPANDED.
  - Questioned by TST-573 (2026-11-19).
- [x] **TST-563 · An implicit `Any` where the type is known: `json.loads`'s result, and a module loaded from its file** · `tests/unit/test_agents.py:136`, `tests/unit/test_large_reads.py:35, 448`, `tests/unit/test_read_only_bash.py:18`, `tests/unit/conftest.py:178` · confirmed · found 2026-11-19
  - **Defect.** `servers = json.loads(...)['mcpServers']` and `settings = json.loads(...)` are `Any`. `_guard()` and
    `_hook()` return `ModuleType`, so every call into the hooks goes through `Any`. Found by two reviewers.
  - **Scenario.** mypy checks nothing through them, as AGENTS.md's typing rules say.
  - **Fix.** `object` for the parsed JSON, narrowed where it is read (`tests/unit/test_mcp_json.py:28` annotates its
    `json.load`); a `Protocol` with the functions each test calls (`refusal`; `read_refusal`, `bash_refusal`,
    `bash_note`, `main`...) as `_guard`'s and `_hook`'s return type.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: types; mypy strict passes.
    - **Fix:** `_guard() -> _Guard` and `_hook() -> _Hook` are Protocols (precedent `scripts/review_lookup.py:118`; mypy accepts a `ModuleType` for them, probed); the parsed JSON is `servers: dict[str, object]` in test_agents, `object` in test_large_reads. `load_script` keeps returning `ModuleType`, its true type.

- [x] **TST-564 · The hooks' fake payloads are `dict[str, object]` where a `TypedDict` fits** · `tests/unit/test_read_only_bash.py:129`, `tests/unit/test_large_reads.py:46-76` · confirmed · found 2026-11-19
  - **Defect.** `_bash`, `_payload`, `_read` and `_run` build a hook call, a record with known keys (`session_id`,
    `cwd`, `hook_event_name`, `tool_name`, `tool_input`...), as `dict[str, object]`.
  - **Scenario.** A misspelt key in a test's payload goes unseen by mypy.
  - **Fix.** A `TypedDict` for the call (`total=False` for the fields only some events carry), as AGENTS.md's typing
    rules ask for a record.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: types; mypy strict passes.
    - **Fix:** `HookInput`, `HookResponse` and `HookCall` (`total=False`) TypedDicts in conftest beside `run_hook`, which takes a `HookCall`; every payload builder returns one; `offset` and `limit` are `object`, as the tests pass values the tools refuse.
  - Questioned by TST-574 (2026-11-19).
  - Questioned by TST-608 (2026-11-20).

- [x] **TST-565 · `test_agents.py`'s docstring says more than its tests** · `tests/unit/test_agents.py:1-2` · confirmed · found 2026-11-19
  - **Defect.** "each one parses, starts no other agent, and gets only the tools its job allows":
    `test_only_the_developer_starts_agents` checks that the developer does start agents, and only the reading agents'
    tools are checked against their job.
  - **Scenario.** A reader takes the runner's and the developer's tools as checked.
  - **Fix.** Narrow the docstring to what the tests check.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: a docstring.
    - **Fix:** the docstring says only what the tests check: each agent parses and names only tools and skills that exist, only the developer starts agents, the review skill starts the `reviewer` agent, and AGENTS.md's routing names every agent.
  - Questioned by TST-571 (2026-11-19).
- [x] **TST-566 · The runner may run the change's tests, but `runner.md` doesn't list them, and DECISIONS.md says only the agent changing the code runs tests** · `.claude/agents/runner.md:15-22`, `AGENTS.md:115` · confirmed · found 2026-11-19
  - **Defect.** AGENTS.md: "Only the agent that changes the code runs tests. It may hand them to the `runner` agent."
    `runner.md`'s "What you run" lists the full suites, chosen categories, scratch runs, probes and `install.py`, not
    the unit tests by name. DECISIONS.md, Project rules, still says "Only the agent changing the code runs tests".
  - **Scenario.** A runner handed the change's unit tests finds them outside its list; a reviewer raises the
    contradiction with DECISIONS.md.
  - **Fix.** Add the change's unit tests (with lint and types) to `runner.md`'s list; the user rewords the DECISIONS.md
    entry (agents may change only its names and paths), for example "runs tests, itself or through the `runner`".
  - **Resolution: done** (2026-11-19).
    - **Test:** `tests/unit/test_guide.py::test_agents_md_keeps_the_hard_rules` pinned the old rule ("**Only the agent that changes the code runs tests.**"): it failed on the new text, and pins `**Tests run at two stages**` now.
    - **Cause:** the runner's part in running tests was added to AGENTS.md without its stage, and the user's rule in DECISIONS.md wasn't reworded.
    - **Fix:** the user's decision (2026-11-19): while working, the agent changing the code runs only the tests of its own work, never a full suite; at the end the `runner` runs the full suites, the final check, when the user asks. Reworded in DECISIONS.md (Project rules), AGENTS.md (Running the tests; the table's `runner` row), the review skill's opening and `runner.md`, which also runs the suites on the lead's brief without asking for the user's word again (the user: the runner must not refuse). The delegation section says the lead waits for the user's word before the brief.
    - **Also covered:** searched the docs and skills for "agent that changes the code" and "agent changing the code": the review skill's line 17, fixed; no other.
  - Questioned by TST-570 (2026-11-19).
  - Questioned by TST-576 (2026-11-19).
- [x] **TST-567 · The review skill doesn't say what the lead does with a reviewer's Unspecified items** · `.claude/skills/project-code-review/SKILL.md:181-191` · confirmed · found 2026-11-19
  - **Defect.** `reviewer.md` reports items no doc decides under **Unspecified**, "for the lead to raise with the
    user"; steps 4 to 8 of the skill never mention them.
  - **Scenario.** A lead drops them, and the docs' gaps stay.
  - **Fix.** One line in step 8: raise the Unspecified items with the user, in the same report.
  - **Resolution: done** (2026-11-19).
    - **Test:** none: a change of docs alone (AGENTS.md, Running the tests); the doc tests pass (313).
    - **Cause:** `reviewer.md` added the category without the skill's steps taking it up.
    - **Fix:** step 8 of the skill lists the reviewers' Unspecified items among what the lead proposes to the user, each decided or left open.
    - **Also covered:** the template's review log has no field for them; this review's log lists them under **Unspecified**, as step 8 now says.

- [x] **TST-568 · AGENTS.md says twice to tell the user how long a long unit will take** · `AGENTS.md:216, 256` · confirmed · found 2026-11-19
  - **Defect.** "The lead still says before an expensive or long unit what it will cost and how long it will take" and
    "**Before a long unit starts,** tell the user about how long it will take and what comes back".
  - **Scenario.** One is changed and the other isn't (AGENTS.md: keep each fact in one place).
  - **Fix.** Keep one, with cost, duration and what comes back.
  - **Resolution: done** (2026-11-19).
    - **Test:** none: a change of docs alone (AGENTS.md, Running the tests); the doc tests pass (313).
    - **Cause:** the standing request and the brief rules each said it.
    - **Fix:** one sentence in the standing request: cost, duration and what comes back, and why; the paragraph "Before a long unit starts" removed.
    - **Also covered:** no other copy in AGENTS.md or the agent files.

- [x] **AGT-19 · Read's line numbers are counted with cat -n's padding, which Read doesn't add · follows AGT-9, generation 2** · `.claude/hooks/large_reads.py:144`, docstring · measured · found 2026-11-19
  - **Defect.** `READ_NUMBER = '%6d\t'`, from Read's tool description. Read puts the number and a tab, unpadded: the lead's Read of `conftest.py` returned `1\t"""Unit tests...` (2026-11-19). The hook counts up to 5 bytes too many a line.
  - **Scenario.** A 400-line file of 18,000 bytes is refused as 21 KB though Read returns about 19,500 bytes; the tests pin the padded edges and figures.
  - **Fix.** `READ_NUMBER = '%d\t'`, the measurement in the docstring; the tests' figures and edges follow.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** the size figures failed against the padded format: `test_a_whole_read...` (33 KB, not 32), `...just_over_the_limit...` (19,998 bytes refused), `test_the_line_numbers_count_in_the_size` (31 KB, not 25), `test_a_range_over_20_kb...` (27, not 26), `test_a_range_is_sized...[offset 109]`, the hook test.
    - **Cause:** `READ_NUMBER = '%6d\t'` came from Read's tool description ("cat -n format"); Read doesn't pad.
    - **Fix:** `READ_NUMBER = '%d\t'`, the lead's measurement in the docstring; the tests' figures and edges follow (offset 108 refused, 109 passes).
    - **Also covered:** PyCharm's `L<n>: ` format is unchanged.

- [x] **AGT-20 · A printer named by a path or after a precommand isn't sized, and `chdir` or `builtin cd` leaves the hook's folder where it was** · `.claude/hooks/large_reads.py:343, 352`, docstring · confirmed · found 2026-11-19
  - **Defect.** The hook knows a command only by its bare first word: `/bin/cat big.py`, `command cat`, `env cat`, `time cat`, `nice cat`, `X=1 cat big.py` pass unsized, and none is in the docstring's list of lines it can't size. zsh's `chdir` is `cd`, and `builtin cd sub` runs it; the hook moves its folder for neither.
  - **Scenario.** `chdir sub && cat big.py` is sized in the old folder: refused when that folder's `big.py` is big, unsized otherwise. With the 10,000-character cap a successful unsized output is saved to a file anyway; a failing one reaches the context, with the note after it.
  - **Fix.** `chdir` as `cd`; a line with `builtin` given up as unsized; a first word holding `/` or `=`, and the precommands, either given up or listed in the docstring's "can't size" list.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_a_command_is_sized_by_the_lines_it_prints[chdir sub && cat deep.py]` and `[chdir sub; cat big.py]` failed; `test_a_command_it_cant_size_passes` failed for `chdir missing`, `builtin cd`, `noglob cd`, `nocorrect cd`, `- cd`, `X=1 cd`, `time cd`, `eval cd`, `eval 'cd sub'`, `{ cd sub }`, `source x` and `. x`.
    - **Cause:** the hook knew a command only by its bare first word.
    - **Fix:** `chdir DIR` is followed like `cd DIR`; `_run` finds the word zsh runs after assignments and the words of BEFORE (`builtin noglob nocorrect - time ! { if elif then else while until do`); a word of MOVES (`cd chdir pushd popd eval source . repeat`) that isn't a followed cd stops the sizing there, keeping what came before. Printers named by a path, after an assignment or another word stay unsized, listed in the docstring with pins. Measured in zsh which of these move the folder; recorded in the docstring.
    - **Also covered:** a search word (`grep -n source small.py; cat big.py`) no longer gives up a line; `cat big.py; pushd sub` is now refused (it passed before: a change of behaviour); a function of the user's profile still moves the folder unseen, as the docstring says.

- [x] **AGT-21 · `reviewer.md` doesn't say a reviewer never reads PLAN.md, and AGENTS.md reaches it as the session last loaded it · follows TST-559, generation 2** · `.claude/agents/reviewer.md:48-52`, `.claude/skills/project-code-review/SKILL.md:157` · confirmed · found 2026-11-19
  - **Defect.** The rule lives only in AGENTS.md (`:94-95`), which reaches an agent as the session last loaded it (AGT-11); an agent file reaches agents from the next turn. Step 3 of the skill says AGENTS.md "is loaded for it already".
  - **Scenario.** In a session that edited AGENTS.md, a reviewer follows its old copy ("read it before anything else") and reads PLAN.md: TST-559's scenario again. This review's reviewers were kept from it only by their briefs.
  - **Fix.** `reviewer.md`'s "Review blind": don't read PLAN.md, the lead's account of the work. Step 3: put the rules AGENTS.md gained since the session loaded it in the brief.
  - **Resolution: done** (2026-11-19).
    - **Test:** none: a change of docs alone (AGENTS.md, Running the tests); the doc tests pass.
    - **Cause:** the rule lived only in AGENTS.md, which reaches a subagent as the session last loaded it (AGT-11).
    - **Fix:** `reviewer.md`'s "Review blind" says not to read PLAN.md, even where the agent's copy of AGENTS.md says to read it first. Step 3 of the `project-code-review` skill says to put in each brief what AGENTS.md has gained since the session loaded it.
    - **Also covered:** the analyst and the runner read PLAN.md only when their brief names it, as AGENTS.md says; this review's and the developer's briefs said so explicitly.

- [x] **AGT-22 · The developer has WebFetch, while AGENTS.md sends every web fetch to the analyst, which the developer can't start** · `.claude/agents/developer.md:4`, `AGENTS.md:232`, `.claude/agents/analyst.md:43` · confirmed · found 2026-11-19
  - **Defect.** "Never a web fetch or search, even of one known page: it always goes to the `analyst`" names no subject, and AGENTS.md is loaded into the developer, which may start only `/simplify`'s agents. `analyst.md`'s web line names Designer's and the libraries' documentation, not Claude Code's.
  - **Scenario.** A developer needing a page either fetches it against the rule, or can't fetch it at all.
  - **Fix.** The user decides the rule's reach: the lead's only ("The lead never fetches..."), or every agent's (WebFetch dropped from the developer, which reports the page it needs). `analyst.md` names Claude Code's documentation too.
  - **Resolution: done** (2026-11-19).
    - **Test:** `test_large_reads.py::test_the_leads_web_fetch_and_search_go_to_the_analyst` (WebFetch and WebSearch)
      and `test_the_hook_exits_2_to_refuse_the_leads_web_call` failed before the fix (no `web_refusal`; the lead's
      WebFetch passed), as did the settings test; all pass. Live: the lead's WebFetch of example.com was blocked with
      the hook's message.
    - **Cause:** the rule named no subject, and nothing enforced it.
    - **Fix:** the user decided its reach (2026-11-19): the lead's only; "any other subagent should be allowed to do
      web search". `large_reads.py`'s `web_refusal` refuses the lead's WebFetch and WebSearch, registered in
      `.claude/settings.json`, and lets a subagent's through (`agent_id`). AGENTS.md says "The lead never fetches or
      searches the web" and that the subagents, the developer included, fetch for themselves; `analyst.md`'s web line
      names Claude Code's documentation and says the lead's web questions come to it.
    - **Also covered:** the other agents with web tools: the analyst (WebFetch, WebSearch) and the developer (WebFetch)
      keep them; the reviewer and the runner have none.
  - Questioned by AGT-30 (2026-11-19).

- [x] **TST-570 · The runner's row and file still give it scratch runs, which the two stages give the agent changing the code · follows TST-566, generation 2** · `AGENTS.md:219`, `.claude/agents/runner.md:11, 20` · confirmed · found 2026-11-19
  - **Defect.** DECISIONS.md (Project rules) and AGENTS.md (Running the tests): while working, the agent changing the code runs its own unit tests and scratch runs; the runner runs the full suites at the end. The runner's row lists "scratch runs and probes", and `runner.md` "**scratch runs** (`alone.run`) ... as the brief says".
  - **Scenario.** A reviewer raises the contradiction again, or a lead reads DECISIONS.md as forbidding a scratch run handed to the runner.
  - **Fix.** Narrow the runner's row and `runner.md` to the final check, chosen categories when the user asks, the review's probes and diagnosing a Designer.
  - **Resolution: done** (2026-11-19).
    - **Test:** none: a change of docs alone (AGENTS.md, Running the tests); the doc tests pass.
    - **Cause:** TST-566's fix changed the stages but left the runner's scope as it was.
    - **Fix:** the runner's table row, its description and `runner.md` give it the full suites and the chosen categories the user asked for, a review's probes the lead hands it, and a Designer to diagnose; `runner.md` says the scratch runs of a change are run by the agent making it.
    - **Also covered:** searched AGENTS.md, the agent files and the skills for "scratch runs and probes" and "scratch runs or probes": none left.
  - Questioned by TST-575 (2026-11-19).

- [x] **TST-571 · `test_agents_md_says_what_to_give_each_agent` passes with the routing table deleted · follows TST-565, generation 2** · `tests/unit/test_agents.py:179-182` · confirmed · found 2026-11-19
  - **Defect.** The test checks only that each "`name`" appears in the section; all four names appear in its prose too ("only the `developer` starts others", "The `runner` runs the full suites", "ask the `analyst`"). The docstring (TST-565's fix) says AGENTS.md's routing names every agent.
  - **Scenario.** The table loses a row, or the whole table, and the test still passes.
  - **Fix.** Check the table's rows: `set(re.findall(r'^\| `(\w+)` \|', section, re.M)) == set(ONLY_READS)`.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** by mutation: the old check passes on AGENTS.md with the table's rows deleted, the new one fails.
    - **Fix:** `set(re.findall(r'^\| `(\w+)` \|', section, re.M)) == set(ONLY_READS)`, with a comment.

- [x] **TST-572 · ROADMAP item 110's figures are out of date** · `ROADMAP.md:24` · confirmed · found 2026-11-19
  - **Defect.** "It is 33,477 bytes, 84% of the 40,000-byte limit ..., after the agent-delegation branch added 6 KB". AGENTS.md is 35,550 bytes (89%), 8,356 more than at HEAD (27,194).
  - **Scenario.** The item understates how close the limit is.
  - **Fix.** Give the figures as of the merge, or without exact bytes.
  - **Resolution: done** (2026-11-19).
    - **Test:** none: a change of docs alone.
    - **Fix:** item 110 gives the figures without exact bytes: about 36 KB, 90% of the limit, about 9 KB added by this branch (36,206 bytes against 27,194 at HEAD when written).
  - Questioned by TST-578 (2026-11-19).

- [x] **TST-573 · Guard lines that block real escapes have no test failing without them · follows TST-562, generation 2** · `tests/unit/test_read_only_bash.py:74-172`, `.claude/hooks/read_only_bash.py:96, 123, 175, 211, 217-218` · measured · found 2026-11-19
  - **Defect.** TST-562's pins fail without their lines, but these lines have none: the `\\` escape inside double quotes (`:211`; without it, `ls "a\\" ; rm x` would pass); `_ends_a_word` (zsh's `ls 2>&1x` wrote a file named `1x`, measured; the guard refuses it, unpinned); tail's `--follow` (GNU tail on Windows); GLOBS' `^` and `#`.
  - **Scenario.** A change removing one of them passes the suite and lets a write through.
  - **Fix.** One refused case each: `ls "a\\" ; rm x`, `ls 2>&1x`, `tail --follow x`, `uniq a^b`, `uniq a#`.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** by mutation: each case is refused by the guard, and a copy of the guard without its line lets the command through.
    - **Fix:** five refused cases: `ls "a\\" ; rm x \\" b"` (the entry's `ls "a\\" ; rm x` stayed refused under the mutation, as a quote never closed; zsh ran the second command of the new case), `ls 2>&1x`, `tail --follow log.txt`, `uniq a^b`, `uniq a#`.
  - Note (2026-11-19, third review): two more lines block real escapes with no case failing without them: the tab as a word separator (`read_only_bash.py:180`; without it `find .<TAB>-delete` passes as one word and zsh runs `find . -delete`) and `\"` inside double quotes (`:220`; without it `ls "\"" ; rm x ; \"` passes and zsh runs `rm x`), traced by the guard's reviewer. A generation-3 finding about tests adds no check (the review skill, Follow-up chains), and this resolution claims only its five lines: whether to pin these two anyway, as security code, is the user's call.
  - Note (2026-11-19): the guard was removed with its tests, as the user chose (DECISIONS.md, No agent has a write guard). Neither these two lines nor the five are left to pin.

- [x] **AGT-25 · Calls counted at once can lose counts or restart the count, beyond "a call late, or twice"** · `.claude/hooks/large_reads.py:90`, `_counted` (`:331-345`) · confirmed · found 2026-11-19
  - **Defect.** `_counted` reads the file, then `open(path, 'w')` empties it before `json.dump` writes. N calls counted at once that all read the same count lose N-1 counts (all N get the note if they read 7), and a call reading while another has emptied the file gets `ValueError`, so its count restarts at 1. The docstring says only "a note may come a call late, or twice".
  - **Scenario.** The lead's parallel Reads overlap their PostToolUse hooks: a note comes several calls late, or several times; rarely, up to 7 calls late after a restart.
  - **Fix.** Narrow the sentence: a note may come late, or more than once. Optionally write through a temporary file and `os.replace`, which removes the restart. Authority: the docstring's own sentence.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: a sentence narrowed.
    - **Fix:** the docstring says calls counted at once may each read the count before another writes it, so a note may come late, or more than once, and that a call reading the file while another rewrites it finds it cut short, its count restarting at 1. No `os.replace`: the note's timing doesn't need it, and a test of it would need concurrent writes.

- [x] **AGT-26 · Facts about Claude Code and the hook are stated without their source, and two say more than was measured** · `AGENTS.md:370-372`, `.claude/hooks/large_reads.py:319`, `tests/unit/test_large_reads.py:675`, `tests/unit/test_agents.py:113` · confirmed · found 2026-11-19
  - **Defect.** Found by two reviewers, checked by an analyst against the docs and the transcripts.
    - AGENTS.md, How changes reach the agents: "a new or edited agent file reaches the agents started from the next turn on. An agent started in the same turn gets the old definition, or none for a new file" cites nothing. It was measured (the 2026-11-18 transcript, Claude Code 2.1.326): a reviewer started 85 s after its new file was written got "Agent type 'reviewer' not found"; an analyst and a reviewer started 2 to 4 minutes after their files were edited, in the same turn, had no Bash tool, and after the user's next message they had it. The docs (sub-agents, "Write subagent files") say instead that a change is seen "within a few seconds and the next delegation uses the updated definition".
    - "An agent already running keeps its definition": neither a doc nor a measurement.
    - "This Claude Code has no `/agents` command": the command exists and prints that its wizard was removed (the user ran it, 2026-11-18).
    - `large_reads.py:319` and `test_large_reads.py:675` both say "its import was half of the hook's own start (measured 2026-11-19)", without the method or what "start" covers.
    - `test_agents.py:113`'s effort fallback matches Claude Code's model-config page ("falls back to the highest supported level at or below the one you set"), uncited.
  - **Scenario.** A lead trusts the running-agent sentence, or the docs' "next delegation", and briefs an agent from the old definition; a reader can't tell a measured fact from a guess.
  - **Fix.** Cite the measurement or the doc for each; drop the running-agent sentence unless measured; "`/agents` only prints a notice"; the import fact once, with its method, the other place pointing to it. Authority: AGENTS.md, "A claim in these docs without a test is a guess"; one fact in one place.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: docs and comments. The import fact was measured again.
    - **Fix:** AGENTS.md, How changes reach the agents: an agent file reached the agents started after the user's next message, with the 2026-11-18 measurement (Claude Code 2.1.326); the docs' "next delegation" said as theirs; the running-agent sentence dropped; `/agents` only prints that its wizard was removed. The tempfile fact is stated once, in `large_reads.py`, with its method: `python -X importtime` gave about 4 ms for tempfile against about 7 ms for the hook's other imports, in a run of the hook of about 28 ms (2026-11-19, `runpy` gone). "Half of the hook's own start" held only against those imports. The test's comment points to the hook's. `test_agents.py` quotes Claude Code's model-config page for the effort fallback.
  - Questioned by AGT-42 (2026-11-19).

- [x] **AGT-27 · A turn a notification starts has its own `prompt_id`, so the nudge doesn't count "within one prompt of the user's"** · `AGENTS.md:257`, `.claude/hooks/large_reads.py:73, 82-85, 195` · measured · found 2026-11-19
  - **Defect.** AGENTS.md and the docstring say the 8th reading call "within one prompt of the user's" gets the note, measured only across prompts the user typed. Measured: in a turn started by a subagent's report, this session's count file (`large_reads_<session>.json`) read count 1 after one Read, while the user's prompt before it had passed 16 counted calls.
  - **Scenario.** One prompt of the user's that spans several notification turns (background reviewers reporting) restarts the count at each, so the note comes later than the docs say, or never.
  - **Fix.** Narrow the wording to a turn: a message of the user's, or a notification that starts one (RESEARCH_NOTE already says "this turn"). Authority: AGENTS.md's hooks bullet.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: wording.
    - **Fix:** AGENTS.md and the docstring count a turn, which starts with a message of the user's or with a notification such as a subagent's report, each with a `prompt_id` of its own (the docstring cites the lead's measurement). RESEARCH_READS's comment, `research_note`'s docstring, conftest's `prompt_id` comment and the tests' names and docstrings say turn.

- [x] **AGT-28 · The call-fields and Grep-and-Glob changes left two sentences untrue: the guard's conditions, and the note's list of reading calls** · `.claude/hooks/large_reads.py:78-80, 197` · confirmed · found 2026-11-19
  - **Defect.** Found by two reviewers. The docstring says a Bash call counts when "every simple command of its line only reads, and it doesn't run in the background", but `call_refusal` now also refuses a call holding a field outside FIELDS. RESEARCH_NOTE lists "(Read, PyCharm reads and searches, Bash commands that only read)", without Grep and Glob, which now count.
  - **Scenario.** The lead's `git log -1` with `dangerouslyDisableSandbox` isn't counted, against the docstring; a lead on Windows isn't told its Greps count.
  - **Fix.** Name `call_refusal` without restating its conditions, or add the fields; add Grep and Glob to the note. Authority: the `address-review` skill, step 6 (a sentence a change made untrue).
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_the_8th_reading_call_of_a_turn_and_each_8th_after_it_get_the_research_note` failed: the note said "(Read, PyCharm reads and searches, Bash commands that only read)", without Grep and Glob.
    - **Cause:** Grep and Glob joined READING_TOOLS without the note, and the fields check joined `call_refusal` without the docstring.
    - **Fix:** the note names Read, Grep, Glob, PyCharm's reading tools and Bash commands that only read. With the guard gone, `_only_reads` is the hook's own approximate test, and the docstring gives its conditions.

- [x] **AGT-29 · `call_refusal` passes an implicit `Any` to `refusal`** · `.claude/hooks/read_only_bash.py:320-331` · confirmed · found 2026-11-19
  - **Defect.** `isinstance(call, dict)` narrows `object` to `dict[Any, Any]`, so `tool_input` and `tool_input['command']` are `Any`: mypy checks nothing there. No effect on behaviour, as `isinstance(..., str)` runs first.
  - **Scenario.** A later change passing another field to `refusal` goes unchecked.
  - **Fix.** Narrow `command = tool_input.get('command')` with `isinstance` and pass `command`, as `large_reads.py`'s `_leads` and `_object` keep the input as `dict[str, object]`. Authority: AGENTS.md, Typing (an implicit `Any` in a function the diff adds is narrowed).
  - **Resolution: done** (2026-11-19, by the `developer` agent): the code went with the guard (DECISIONS.md, No agent has a write guard).
    - **Also covered:** the new `_only_reads` reads the call through `_object` and `_text`, as `dict[str, object]` and `str`.

- [x] **AGT-30 · "The subagents fetch for themselves, the developer included" says more than their tools · follows AGT-22, generation 2** · `AGENTS.md:235` · confirmed · found 2026-11-19
  - **Defect.** The frontmatter: the analyst has WebFetch and WebSearch, the developer WebFetch only, the reviewer and the runner neither. The user's words were that the hook allows the other subagents' web calls.
  - **Scenario.** A lead briefs the runner to check a documentation page, or the developer to search for one: they can't.
  - **Fix.** Narrow it to what the hook and the tools allow: the hook lets a subagent's call through; the analyst fetches and searches, the developer fetches a page it can name. Authority: AGENTS.md, Writing docs (a sentence that misleads).
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: a sentence narrowed.
    - **Fix:** AGENTS.md: the hook lets a subagent's call through; the `analyst` fetches and searches, and the `developer` fetches a page it can name.
    - **Also covered:** `test_large_reads.py`'s comment said the same; it now says a subagent's call passes.

- [x] **AGT-31 · The PLAN.md row of "Keeping the docs current" doesn't say the file is the lead's** · `AGENTS.md:315` · confirmed · found 2026-11-19
  - **Defect.** The row sends "what is done, what is left" to PLAN.md; `developer.md` tells the developer to update the docs "(AGENTS.md, Keeping the docs current)", while AGENTS.md's PLAN.md paragraph says a subagent never writes PLAN.md.
  - **Scenario.** A developer finishing a unit records it in PLAN.md, the lead's file.
  - **Fix.** "**PLAN.md**, the lead's (Working on this project)". Authority: AGENTS.md's PLAN.md paragraph (the user, 2026-11-19).
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: docs.
    - **Fix:** the row reads "**PLAN.md**, the lead's (Working on this project)".

- [x] **AGT-32 · AGENTS.md names a commit among what a brief passes on with the user's word, but no agent commits** · `AGENTS.md:211-212` · confirmed · found 2026-11-19
  - **Defect.** "Where this file waits for the user's word (a commit, the full suites, a decision), the lead waits for it before the brief": the developer "never commits" (`developer.md`, DECISIONS.md), the runner changes no committed file, the analyst and the reviewer only read.
  - **Scenario.** A lead with the user's word to commit puts it in a developer's brief; the developer refuses, as its file says.
  - **Fix.** Drop "a commit" from the parenthesis. Authority: DECISIONS.md, the developer and runner entry.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: docs.
    - **Fix:** "a commit" dropped from the parenthesis.

- [x] **AGT-33 · The web rule's reason says WebFetch has no limit, and that every page fills the context** · `AGENTS.md:234`, `.claude/hooks/large_reads.py:26-27` · measured · found 2026-11-19
  - **Defect.** Claude Code's tools reference ("WebFetch tool behavior"): "WebFetch reads up to 100,000 characters of a page's content per call", and "For most fetches, it then runs the prompt against the content in a separate model call". An analyst measured: documentation pages under 100,000 characters (code.claude.com, modelcontextprotocol.io) came back whole, the prompt ignored; example.com and a raw GitHub file came back as the small model's answer; 89 KB pages were saved to a file with a 2 KB preview; longer pages got an answer covering their first 100,000 characters. The lead's own fetch of a settings page (2026-11-18 and 2026-11-19) returned 45,978 characters whole.
  - **Scenario.** A reader takes "no limit to cap it" as fact, or doubts the rule because most fetches return an answer.
  - **Fix.** Narrow the reason to what was measured: some pages come back whole, up to 100,000 characters (a 46 KB documentation page did), and which ones isn't documented; drop "no limit to cap it". The rule itself is the user's. Authority: the tools reference; AGENTS.md, "A claim in these docs without a test is a guess".
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: docs and a message.
    - **Fix:** AGENTS.md and the docstring: WebFetch reads up to 100,000 characters of a page (the tools reference), some pages come back whole, the prompt ignored, as a 46 KB documentation page did, and which ones isn't documented. "No limit to cap it" dropped; the rule stays.
    - **Also covered:** `web_refusal`'s message said "a page's size is known only once it has filled your context"; it now says a fetch may return a whole page, up to 100,000 characters. `test_large_reads.py`'s comment too.

- [x] **TST-574 · `HookCall`'s docstring says "the fields ... the hooks read", but two are read by none · follows TST-564, generation 2** · `tests/unit/conftest.py:220-221` · confirmed · found 2026-11-19
  - **Defect.** No hook reads `tool_use_id` or `is_interrupt`; the tests send them to make the payload realistic (`test_large_reads.py:77, 111`).
  - **Scenario.** A reader looks in the hooks for code reading those fields.
  - **Fix.** "... that the hooks read or the tests send". Authority: the address-review skill, step 6.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: a docstring.
    - **Fix:** "... that the hooks of `.claude/hooks` read or the tests send", and a comment on `tool_use_id` and `is_interrupt`: sent by the tests, read by no hook.

- [x] **TST-575 · Two places still give the runner runs that TST-570 gave to the agent changing the code · follows TST-570, generation 3** · `AGENTS.md:220`, `.claude/agents/runner.md:26-27` · confirmed · found 2026-11-19
  - **Defect.** The runner's row ends "A run that doesn't return promptly goes to it, in the background", and `runner.md` says its preloaded `live-check` skill has "what to do when the final check fails": that section reruns the failing tests "until they pass" and tells the user. `runner.md:22-23`: "The scratch runs of a change are run by the agent making it". TST-570's search for "scratch runs and probes" and "scratch runs or probes" missed both.
  - **Scenario.** A lead sends a slow scratch run of its own change to the runner by the row, which `runner.md` sends back; a runner whose final check fails reruns checks until they pass, without a fix, and is told to tell the user, which it can't.
  - **Fix.** Generation 3, docs only: narrow. Drop the row's last sentence (or "Of these, a run that ..."), and `runner.md`'s "and what to do when the final check fails" (a failing final check is reported). Authority: DECISIONS.md, Project rules (two stages); TST-570.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: docs.
    - **Fix:** the runner's row ends at "a Designer that crashed or hung"; `runner.md` says the skill has `alone.run` and what a scratch run can't prove, and to report the failures when the final check fails.

- [x] **AGT-34 · A refused `read_file` sends the lead to Read with the path as PyCharm took it, which Read finds from the cwd** · `.claude/hooks/large_reads.py:280-288` · confirmed · found 2026-11-19
  - **Defect.** `read_refusal` names `file_path` in its message, as the call gave it. PyCharm's `read_file` finds a relative path from the project (`projectPath`, else PROJECT), and Read from the call's cwd (the module's docstring, lines 22-25). The message now sends a `read_file` to Read for a range.
  - **Scenario.** After `cd tests/unit`, the lead's `read_file('mcp_server/GUIDE.md')` (32,730 bytes) is refused, naming `mcp_server/GUIDE.md`. The lead's `Read('mcp_server/GUIDE.md', offset=1, limit=300)` then finds no file.
  - **Fix.** For `read_file`, name the absolute path the hook measured (`path`), with a test using a relative path. Authority: the module's docstring ("A refused `read_file` is sent to Read for a range").
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_a_refused_read_file_names_its_file_by_the_absolute_path_read_finds` (`tests/unit/test_large_reads.py`). Before the fix it failed: the refusal named `sub/big.py`, where the test wanted the absolute path under the project, and under `projectPath`.
    - **Cause:** `read_refusal` named `file_path` as the call gave it. `read_file` finds a relative path from the project, and Read, which the refusal sends a range to, finds it from the cwd.
    - **Fix:** a refused `read_file` names `path`, the absolute path the hook measured. A refused Read still names the path as given, which Read finds the same way again. The module's docstring says so.
    - **Also covered:** a `file://` URL (AGT-46) is named by its path too. The Bash refusal names its files as written, found from the call's cwd as the shell finds them: not affected.
  - Questioned by AGT-48 (2026-11-19).

- [x] **AGT-35 · The docstring's sentence on a relative path after a `cd` reads as covering PyCharm's `read_file` too · follows AGT-3, generation 2** · `.claude/hooks/large_reads.py:22-25` · confirmed · found 2026-11-19
  - **Defect.** The bullet says Read finds a relative path from the call's cwd, and `read_file` from the project. The next line, "A relative path after a `cd` is found from the folder the `cd` moved to", goes on without naming Read. It is false for `read_file` (`test_pycharms_relative_path_is_measured_from_its_project`).
  - **Scenario.** A maintainer reads that `read_file` follows a `cd`, and sizes its paths from the cwd again: AGT-3 comes back.
  - **Fix.** Generation 2, docs: "Read finds a relative path after a `cd` from the folder the `cd` moved to", before the PyCharm sentence. Authority: the `address-review` skill, step 6 (a sentence a fix made untrue).
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: a docstring alone.
    - **Fix:** the bullet says "Read finds a relative path after a `cd` from the folder the `cd` moved to", before the sentence on `read_file`, and inside the bullet: the line had lost its indentation.
    - **Also covered:** the docstring's other sentences on a `cd` (the Bash command's) name what they cover.

- [x] **AGT-36 · The docstring's list of a failed Bash call's payload leaves out `session_id` and `prompt_id`, which the count needs** · `.claude/hooks/large_reads.py:129-131` · measured · found 2026-11-19
  - **Defect.** "Its payload holds `cwd`, `duration_ms`, `effort`, `error`, `hook_event_name`, `is_interrupt`, `permission_mode`, `tool_input`, `tool_name` and `tool_use_id`" reads as the whole payload. Lines 94-96 say a PostToolUseFailure payload carries `session_id` and `prompt_id`, measured only in a subagent's calls, and `_counted` needs both.
  - **Measured** (the lead, 2026-11-19): this session's count file went from 4 to 5 across a failing `ls` of a missing folder (exit 1), between two reads of the file. The lead's failure payloads carry both fields, and its failed reading calls are counted.
  - **Scenario.** A reader of lines 129-131 concludes that a failed call can't be counted, and doubts line 85 or changes the count.
  - **Fix.** Add `session_id` and `prompt_id` to the list, or say it lists only the fields besides those; cite the lead's measurement at lines 94-96. Authority: the module's docstring.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: a docstring alone.
    - **Fix:** the list now opens "Besides `session_id` and `prompt_id`, which the count reads (above)". The turn's bullet cites the lead's measurement: its count went from 4 to 5 across a failing `ls`.

- [x] **AGT-37 · README says the settings save a long Bash output to a file, but only a command that succeeds has its output saved** · `README.md:336` · confirmed · found 2026-11-19
  - **Defect.** "The same settings save a long Bash output to a file and show the session a preview". AGENTS.md and the hook's docstring say a failing command's output isn't capped: a failing 15,000-character output reached the context whole (measured 2026-11-19).
  - **Scenario.** A person expects a long failing test run to show only a preview.
  - **Fix.** "save a long output of a command that succeeds". Authority: AGENTS.md, Writing docs (a sentence that misleads).
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: README alone.
    - **Fix:** "The same settings save a long output of a Bash command that succeeds to a file".
    - **Also covered:** AGENTS.md's sentence on the cap says "a successful command's output", and the hook's docstring says the same: not affected.

- [x] **AGT-38 · "PLAN.md is never refused, by Read or `read_file`": no test covers `read_file`** · `AGENTS.md:255`, `tests/unit/test_large_reads.py:220` · confirmed · found 2026-11-19
  - **Defect.** `test_the_repositorys_plan_is_read_whole_and_no_other_file_of_that_name` reads PLAN.md with Read only. `read_file` finds a relative `PLAN.md` from the project, another way into `_is_plan`. The code is shared, so nothing is wrong today.
  - **Scenario.** A change to how `read_file`'s path is found refuses PLAN.md, and no test fails.
  - **Fix.** A `tool=PYCHARM` case in that test, with PLAN.md relative and absolute. Authority: AGENTS.md, "A claim in these docs without a test is a guess".
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_the_repositorys_plan_is_read_whole_and_no_other_file_of_that_name` gained `read_file`'s cases: a relative `PLAN.md` found from the project while the call's cwd holds another `PLAN.md`, the absolute path, and `docs/PLAN.md` refused. They passed before any change, as the finding says (the code is shared). They failed on a mutation that let only Read's PLAN.md through (`not pycharm and _is_plan(path)`): the `read_file` case failed, after the Read cases passed. The mutation was reverted.
    - **Fix:** the test alone.

- [x] **AGT-39 · `_counted` keeps an implicit `Any`** · `.claude/hooks/large_reads.py:386-389` · confirmed · found 2026-11-19
  - **Defect.** `isinstance(held, dict)` narrows `object` to `dict[Any, Any]`, so both `.get` calls return `Any` and mypy checks nothing there. No effect on behaviour: `isinstance(previous, int)` follows. AGT-29 found the same pattern in the guard; `_leads` and `_object` avoid it.
  - **Scenario.** A later change reading another field of the count file goes unchecked.
  - **Fix.** Pass `held` through `_object`, as `dict[str, object]`. Authority: AGENTS.md, Typing (an implicit `Any` in a function the diff adds).
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none can fail on it: no behaviour changes. The research count's 46 tests (`tests/unit/test_large_reads.py -k "research or count or turn or reading_call"`) passed before and after, and the whole file after. `mypy --strict --disallow-any-expr` on the hook reported `Expression type contains "Any" (has type "Any | bool")` at `_counted`'s `previous` line before, and nothing there after.
    - **Fix:** `_dict(value)` returns `value` as a `dict[str, object]`, or `{}`. `_counted` reads its file through it, and `_object` and `_leads` use it.
    - **Also covered:** the new notebook code reads its JSON through `_dict` and `_list`, a `list[object]`, so it holds no `list[Any]`. What `--disallow-any-expr` still reports is `json.load`'s own result, passed straight to `_dict` or `_answer`, and typeshed's: `re.Match`'s items, `json.dump`'s parameter, `dict.fromkeys`.

- [x] **AGT-40 · AGENTS.md says the hooks stay off in "a fresh clone or a worktree" until `install.py` makes the venv: a worktree is unmeasured, and `install.py` there installs its plugin** · `AGENTS.md:247-248` · confirmed · found 2026-11-19
  - **Defect.** The sentence holds where `$CLAUDE_PROJECT_DIR` has no venv. A session moved into a worktree (`EnterWorktree`) may keep the main checkout as `$CLAUDE_PROJECT_DIR`, so the hooks would run from the main checkout: unmeasured. And `install.py` copies the plugin into Designer and writes the user skill (its docstring).
  - **Scenario.** A user working in a worktree runs `install.py` there to turn the hooks on, and their Designer gets the worktree's plugin.
  - **Fix.** Narrow it to a fresh clone ("in a clone without `mcp_server/venv`") and drop the worktree. Authority: AGENTS.md, "A claim in these docs without a test is a guess", and How changes reach Designer.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: docs.
    - **Fix:** AGENTS.md: "where the project folder has no `mcp_server/venv`, as in a fresh clone". The worktree is dropped.
    - **Also covered:** README's hooks section and the hook's docstring name no worktree: not affected.

- [x] **AGT-41 · `runner.md`'s Designer rules hold only on macOS: on Windows the runner can't run the final check** · `.claude/agents/runner.md:37-38, 44` · confirmed · found 2026-11-19
  - **Defect.** "Use only a Designer an agent started. If the user's Designer is open, stop and report ... The full suite refuses to run beside it and says so", and "Close the Designers you started". On Windows the self-test makes one run in one Designer: it starts one if none runs and leaves it open, and reopens the user's graph in theirs (`tests/test_all_tools/__main__.py`'s docstring). No Designer counts as an agent's there (`finish`, ROADMAP item 18). AGENTS.md, Running the tests, gives the Windows command of the final check.
  - **Scenario.** On Windows the user asks for the final check. With their Designer open, the runner stops, though the suite wouldn't refuse. With it closed, the suite starts one the runner can't close.
  - **Fix.** Say these rules are macOS's. What the runner does on Windows is the user's call (the review log's Unspecified items). Authority: AGENTS.md, Running the tests; `__main__.py`'s docstring.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: an agent's instructions.
    - **Fix:** the user's decision (the review log, 2026-11-19). `runner.md`, Designer: "Use only a Designer an agent started, but for the final check on Windows (below)", and "On macOS the full suite refuses to run beside it". A new bullet: the final check on Windows runs as the suite does there (`__main__.py`'s docstring): one run in one Designer, the user's if it is open, else one the suite starts and leaves open. `pytest` runs at the same time, as a background command (AGENTS.md, Running the tests). The runner doesn't quit that Designer, and reports it as left running.

- [x] **AGT-42 · "Turn" means two things in AGENTS.md · follows AGT-26, generation 2** · `AGENTS.md:380`, `AGENTS.md:262-263` · confirmed · found 2026-11-19
  - **Defect.** How changes reach the agents: "not those started before it in the same turn". The hooks bullet: "A turn starts with a message of the user's, or with a notification such as a subagent's report". AGT-26's measurement covers agents started before the user's next message, not whether a turn a notification starts loads an edited file.
  - **Scenario.** A developer's report starts a turn in the hooks' sense. The lead reads "the same turn" as over, and starts an edited agent before the user's next message.
  - **Fix.** Generation 2, docs: "not those started before that message". Authority: AGENTS.md, Writing docs ("Name what you mean").
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: docs.
    - **Fix:** "not those started before that message".
    - **Also covered:** the hooks' bullet keeps its "turn", which it defines itself.

- [x] **AGT-43 · `developer.md` doesn't list the fixes after a failed final check, which AGENTS.md's table gives the developer** · `.claude/agents/developer.md:3, 17` · confirmed · found 2026-11-19
  - **Defect.** The table's developer row ends "or the fixes a failed final check needs". `developer.md`'s objective is "part of a ROADMAP item, or the REVIEW.md IDs to address". The `live-check` skill's procedure for a failed final check ends "Then tell the user which suites failed", which a subagent can't do.
  - **Scenario.** A brief to fix a failed final check matches neither objective. The developer follows the skill and is told to tell the user.
  - **Fix.** Add it to the objective and the description, and say the developer reports to the lead which suites must run again. Authority: AGENTS.md's table (one rule in one place).
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: an agent's instructions.
    - **Fix:** `developer.md`'s description and objective list the fixes a failed final check needs. Its report gives the suites that must run again (the `live-check` skill, When the final check fails), which the lead tells the user.
    - **Also covered:** the user's decision that a developer addressing findings writes a new problem's entry itself (the `address-review` skill, After a group): `developer.md` says nothing against it. The rule that one developer runs at a time is in AGENTS.md's table, the developer's row.

- [x] **AGT-44 · Two names for one thing: `analyst.md` says "the lead" to `/simplify`'s analysts, and AGENTS.md once calls `/simplify`'s agents "review agents"** · `.claude/agents/analyst.md:10, 49, 56`, `AGENTS.md:75` · confirmed · found 2026-11-19
  - **Defect.** AGENTS.md defines the lead as the main session, and says `/simplify`'s agents report to the developer. `analyst.md` tells every analyst "The lead decides what to do with your brief" and to report to the lead. AGENTS.md:75 says "`/simplify`'s four review agents"; Delegating to subagents, `developer.md` and DECISIONS.md say "cleanup agents".
  - **Scenario.** No effect on behaviour: a report reaches the agent that started it. A reader meets two names for one thing.
  - **Fix.** "the agent that started you" where `analyst.md` means it; "cleanup agents" at AGENTS.md:75. Authority: AGENTS.md, Writing docs.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: docs.
    - **Fix:** `analyst.md` says "the agent that started you" where it said the lead, "the agent that started it" in its description, and "name it in your brief" for a command it lacks. AGENTS.md: "`/simplify`'s four cleanup agents".
    - **Also covered:** ROADMAP item 110 said "`/simplify`'s four helpers": now "cleanup agents". `reviewer.md` and `runner.md` say "the lead", which only starts them (AGENTS.md's table): not affected.

- [x] **TST-576 · DECISIONS.md's two stages give the agent's own tests as only those it added or changed · follows TST-566, generation 2** · `DECISIONS.md:41-42` · confirmed · found 2026-11-19
  - **Defect.** "the unit tests it added or changed, and its live checks in scratch runs". AGENTS.md also has the agent run the existing tests of the code a refactor touches (Running the tests; Start with the tests, for a rename or a move), and of the code `/simplify`'s fixes touch.
  - **Scenario.** A developer reads DECISIONS.md first (`developer.md`, Before writing code) and skips the existing tests of a refactor.
  - **Fix.** The user's wording to change (DECISIONS.md's introduction), for example "the unit tests of its own work (those it added or changed; for a refactor or `/simplify`'s fixes, the existing tests of the code touched)". Authority: AGENTS.md, Running the tests.
  - **Resolution: done** (the user: "Fix them all", 2026-11-19).
    - **Test:** none can fail on it: no test reads DECISIONS.md's wording (searched `tests/unit` for it). The docs tests passed after the change.
    - **Cause:** TST-566's rewording named the tests an agent adds or changes, and left out the existing tests AGENTS.md has it run for a refactor and for `/simplify`'s fixes.
    - **Fix:** DECISIONS.md, Project rules: "Those are the unit tests it added or changed, the existing tests of the code a refactor or `/simplify`'s fixes touch, and its live checks in scratch runs".
    - **Also covered:** the same paragraph's last sentence gave the scratch probes to "its lead agent ... in Designer", TST-577's pattern. It now says "Scratch probes check what reading can't settle (the `project-code-review` skill, Who settles what)".

- [x] **TST-577 · The review skill's opening and the `address-review` skill still give the probes to the lead alone** · `.claude/skills/project-code-review/SKILL.md:28`, `.claude/skills/address-review/SKILL.md:47` · confirmed · found 2026-11-19
  - **Defect.** The review skill, line 28: "with a **scratch probe**: temporary code of its own, run in Designer". `address-review`, line 47: "the way the `project-code-review` skill's lead agent probes". **Who settles what** (lines 33-46) has the lead write a probe or its outline, and the runner run it.
  - **Scenario.** A reader of the opening paragraph alone runs a Designer probe in the main session. No bug for a reader who goes on to Who settles what.
  - **Fix.** Line 28: "temporary code written for it (**Who settles what** says who writes and runs it)"; `address-review`: "as the `project-code-review` skill's **How a probe runs** says". Authority: one rule in one place (AGENTS.md, Keeping the docs current).
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: docs.
    - **Fix:** the review skill: "temporary code written for it, run in Designer (**Who settles what** says who writes and runs it)", and "A review's probes run one at a time" where it said "The lead agent's probes". `address-review`, step 4: "as the `project-code-review` skill's **How a probe runs** says".
    - **Also covered:** DECISIONS.md, Project rules: the lead's edit for TST-576 made the two-stages paragraph's last sentence point to Who settles what. TEMPLATE.md's and REVIEW.md's "the lead agent's scratch probe" say whose probe it is, which stays the lead's, written or outlined by it: not affected.

- [x] **TST-578 · ROADMAP item 110's figures are out of date again · follows TST-572, generation 2** · `ROADMAP.md:24` · confirmed · found 2026-11-19
  - **Defect.** "about 36 KB, 90% of the 40,000-byte limit `test_guide.py` sets, after the agent-delegation branch added about 9 KB": AGENTS.md is now 37,643 bytes (94%), 10,449 more than main's.
  - **Scenario.** A reader plans item 110 from a budget that is wrong.
  - **Fix.** Drop the figures that change with each edit, and keep "near the 40,000-byte limit `test_guide.py` sets": a narrower claim, which the next edit can't make stale. Authority: AGENTS.md, Writing docs.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** none: docs.
    - **Fix:** item 110 says AGENTS.md "is near the 40,000-byte limit `test_guide.py` sets". Its size, its share of the limit, the bytes the branch added and its tokens are dropped: each changes with every edit.

- [x] **AGT-45 · A sized read is scanned to the end of its range, however big the file** · `.claude/hooks/large_reads.py:455-510` · confirmed · found 2026-11-19
  - **Defect.** `_read_returns` sizes every line from `offset` to the end of the range, `_pycharm_returns` keeps the last lines with a `deque` over the whole rest of the file, and `_sizes` does the same for `cat`, `tail` and `sed -n`. The decision needs only to know that the read passes READ_LIMIT. A line is also read whole, however long.
  - **Scenario.** The lead's whole Read of a multi-GB log, or one with an `offset` alone, makes the hook read the whole file before it refuses: seconds of a hook that runs before every read, and the whole file in memory for a file of one line.
  - **Fix.** Stop the scan once the read is known to pass READ_LIMIT, with a refusal that says only what is known ("over 20 KB"). Keep the exact size where the scan is complete, and a range near the start stopping at its end. Raised by the coordinator for the user (2026-11-19), who wants it fixed now.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_a_big_files_read_is_sized_only_until_it_passes_the_limit`, `test_a_big_files_read_file_is_sized_only_until_it_passes_the_limit`, `test_a_big_files_command_is_sized_only_until_it_passes_the_limit` and `test_a_long_line_of_a_big_file_is_read_only_in_part`. `Counter` in `tests/unit/counted_reads.py` counts the bytes the hook reads. Before the fix each failed on its refusal: "2109 KB and 20001 lines", "214 KB and 2000 lines", "2000 KB and 20000 lines" and "3001 KB and 1 lines", where "over 20 KB" was expected. A scratch run with the counting `open` showed the old code reading all 2,000,000 bytes of a 2 MB file for a whole Read, a whole `read_file` and `tail -n 20`, and 8,192 for a range near the start.
    - **Cause:** each sizer scanned its whole range, `read_file`'s and `tail`'s last lines through a `deque` over the rest of the file, and a line was read whole.
    - **Fix:** in a file over BIG (1 MB), `_scan` stops once the total passes READ_LIMIT. `Returned.whole` is then False, and the refusal says "over 20 KB" (`_amount`). `_capped` reads a line up to CAP bytes, and passes its rest only when the next line is asked for. `_last` reads the last lines back from the end of the file. `_bounded` decides `read_file`'s reads from the lower and upper bounds of the last lines' numbers, and `_pycharm_returns` reads the lines between them only when the bounds can't tell. A file under BIG is sized as before, so the earlier tests' exact sizes hold.
    - **Also covered:** Bash's `cat`, `head`, `tail` and `sed -n` (`_sizes`), and a notebook's rebuilt text (AGT-46). Three mutations checked the new paths, each failing its test: without `head.lines == half`, a read from near the end of a big file, exactly 20,000 bytes, was refused; without the upper bound, `limit=1` read the 2 MB file whole; without passing the rest of a cut line, a Read from line 110 after a 1.5 MB line was refused. Left, and said in the docstring: a read's range is still reached by reading forward from the start of the file, a notebook's JSON is parsed whole, and a `read_file` of a big file whose shown lines fall between the bounds reads the lines between them.
  - Questioned by AGT-47 (2026-11-19).

- [x] **AGT-46 · PyCharm's `read_file` of a notebook or of a `file://` URL passes unsized** · `.claude/hooks/large_reads.py:192-193, 266` · confirmed · found 2026-11-19
  - **Defect.** UNMEASURED lets every `.ipynb` through and NOT_PATHS every `://`, for both tools. Read shows a notebook's cells in its own way, but `read_file` shows a notebook as text, numbered as a file's lines, and reads a `file://` URL to a file in the project.
  - **Scenario.** The lead's `read_file` of a big notebook, or of `file://` and a big file's absolute path, returns all of it into the context.
  - **Fix.** Measure what `read_file` returns for each, then size a `file://` URL that `read_file` accepts as its path, and a notebook from its cells as `read_file` shows them, only if that text can be rebuilt from the JSON exactly. Read's notebooks, images and PDFs stay as they are. Raised by the coordinator for the user (2026-11-19), who wants it fixed now.
  - **Resolution: done** (2026-11-19, by the `developer` agent).
    - **Test:** `test_pycharms_notebook_is_sized_by_the_text_it_shows`: a notebook whose text `read_file` shows in exactly 20,000 bytes passes, one more byte is refused as "21 KB and 15 lines", and Read's notebook passes. `test_pycharms_file_url_is_sized_as_its_path`. Before the fix both failed: the reads passed. `test_a_notebook_whose_text_it_cant_rebuild_passes` passed before and after, as a guard.
    - **Measured** (the developer, 2026-11-19): `read_file` calls on files in a temporary folder of the project, removed afterwards. `read_file` refused files outside the project, library and SDK roots, the scratchpad's included. The results, now in the hook's docstring: a `file://` URL and an absolute path read the same lines as the path, `%41` wasn't decoded, and `file://localhost/` or a relative path found no file. A notebook showed as its cells' text, as the docstring lists.
    - **Cause:** UNMEASURED and NOT_PATHS were shared by both tools, while only Read's notebooks and URLs can't be sized.
    - **Fix:** for `read_file`, `read_refusal` takes `file://` off and requires an absolute path. UNMEASURED keeps images and PDFs, and a notebook passes only for Read. A notebook read by `read_file` is sized from `_notebook`'s text, through `_pycharm_returns` (`_returned`). Read's notebooks, images and PDFs, `jar://` URLs and archive entries still pass.
    - **Also covered:** images and PDFs read by `read_file` still pass, unmeasured. A notebook whose JSON doesn't parse, or without a list of cells (format 3 among them), passes: each was measured once, and the hook doesn't rebuild them.
  - Questioned by AGT-49 (2026-11-19).

- [x] **AGT-47 · `_bounded` counts the empty line after a last newline twice when the first half already holds it · follows AGT-45, generation 2** · `.claude/hooks/large_reads.py:623, 641-647` · confirmed · found 2026-11-19
  - **Defect.** `_numbered` yields the empty line after a last newline only once the file is used up. When the first half `read_file` shows ends with that line, the head holds it and the file is read to its end. `_bounded` then finds `empty` True, `_last` returns nothing, and `shown` is 1: `lower` counts a line `read_file` doesn't show.
  - **Scenario.** The test's `near_end.log` (`test_large_reads.py:683`), a file over 1 MB, with `read_file(offset=500_001, limit=368)`. The 184 items from line 500,001 are 183 lines and the empty line: 20,000 bytes, the read the test lets through without `limit`. `_bounded` adds `len('L500185: ')`, 9 bytes, and the read is refused as "over 20 KB". It takes the items from `offset` to the end to be exactly `limit // 2`, within about 10 bytes under the limit.
  - **Fix.** `_bounded` returns None when the head has read the file to its end; the deque path is then exact. The test: `read_refusal` of that call is None (`limit=366`, the neighbouring case, passes today). Authority: the module docstring ("a read that returns over 20 KB ... is refused").
  - **Resolution: done** (2026-11-19, the developer's report, written by the lead).
    - **Test:** `test_a_big_files_read_file_is_sized_only_until_it_passes_the_limit` loops over `limit` 366 and 368 on `near_end.log` from `offset=500_001`: both must pass. It failed before the fix with `AssertionError: 368`, the read refused; 366 passed.
    - **Cause:** when the first half had read the file to its end, `_bounded` added the empty line after the last newline a second time.
    - **Fix:** `_bounded` returns None when the head ended past the file's last byte (`after > end`), after putting the file back where it was; the deque path that follows is exact.
    - **Also covered:** `_read_returns` and `_sizes` never call `_bounded`, and nothing else derives the empty line again.

- [x] **AGT-48 · After a `cd` in the command line, the Bash refusal names a file as written, and the Read it suggests finds that name from the call's folder · follows AGT-34, generation 2** · `.claude/hooks/large_reads.py:352, 717` · confirmed · found 2026-11-19
  - **Defect.** `_printed` follows `cd DIR` and keeps each file as written (`printed.append((file, _sizes(path, start, stop)))`). The refusal names those files and says "read them with the Read tool's `offset` and `limit`". The command was refused, so its `cd` never ran, and Read finds the name from the call's cwd. AGT-34's **Also covered** says the Bash refusal is "not affected": it is, after a `cd`.
  - **Scenario.** `cd docs && cat README.md`, over 20 KB, is refused naming `README.md`. The lead's `Read('README.md', offset=1, limit=300)` reads the root's README.md, another file, without an error.
  - **Fix.** Name the absolute path the hook measured, at least for a file found after a `cd`, as AGT-34 did for `read_file`. Authority: AGT-34's reasoning; the `address-review` skill, step 6 (the other code path).
  - **Resolution: done** (2026-11-19, the developer's report, written by the lead).
    - **Test:** `test_a_refused_command_names_its_files_by_the_absolute_paths_read_finds`, with `cd sub && cat deep.py` and `cat half.py && cd sub && cat deep.py`. It failed before the fix: the refusal named `deep.py` as written.
    - **Cause:** `_printed` kept each file as written.
    - **Fix:** `_printed` keeps the absolute path it measured, always, as AGT-34 does for `read_file`. Two expectations now name the absolute path (`huge.log`, `one_line.json`).
    - **Also covered:** Read's refusal still names the path as given, which Read finds from the same cwd.

- [x] **AGT-49 · A refused read of a notebook sends the lead to Read with `offset` and `limit`, which the hook lets through unsized · follows AGT-46, generation 2** · `.claude/hooks/large_reads.py:311, 325-330` · confirmed · found 2026-11-19
  - **Defect.** The refusal's way on doesn't tell notebooks apart: "For a range, use the `Read` tool with `offset` and `limit`". Read of a `.ipynb` passes unsized (`unmeasured = ... (suffix == NOTEBOOK and not pycharm)`). `cat x.ipynb`, refused by the Bash check, gives the same advice.
  - **Scenario.** A notebook whose text is 40 KB is refused for `read_file`. The lead follows the advice, and Read shows the notebook's cells with their outputs, unsized. What Read returns of a notebook with `offset` and `limit` is unmeasured.
  - **Fix.** For a notebook, the refusal offers `read_file` with `offset` and a smaller `limit`, or the `analyst`, not Read. Authority: the module docstring, the refusal's ways on.
  - **Resolution: done** (2026-11-19, the developer's report, written by the lead).
    - **Test:** `test_a_refused_notebook_isnt_sent_to_read`. It failed before the fix: the refusal said "use the `Read` tool".
    - **Cause:** the refusals' ways on didn't tell notebooks apart.
    - **Fix:** a refused `read_file` of a notebook says to read fewer lines with `read_file`'s `offset` and a smaller `limit`, the `Read` tool showing a notebook unsized; a refused command printing a notebook says to print fewer lines with `head` or `sed -n`.
    - **Also covered:** the Bash refusal of `cat x.ipynb`, which gave the same Read advice.
  - Questioned by AGT-63 (2026-11-19).

- [x] **TST-579 · Tests that check exact sizes write their files with `write_text`, which writes CRLF on Windows** · `tests/unit/test_large_reads.py:78, 179, 392, 684, 691` · confirmed · found 2026-11-19
  - **Defect.** `Path.write_text(..., encoding='utf-8')` leaves `newline=None`, so each `\n` is written as `\r\n` on Windows (Python's `open` docs). These tests, and the `_big` helper, assert exact sizes of what they wrote.
  - **Scenario.** In a unit run on Windows, where the final check runs `pytest`, `near_end`'s lines are a byte longer each, so its read of exactly 20,000 bytes is refused. `short` gives "over 20 KB" where "21 KB and 2000 lines" is expected, and line 179 gives 27 KB where 25 KB is. The Windows simulation runs on macOS and can't see it.
  - **Fix.** `write_bytes`, or `write_text(..., newline='')`, in these tests and in `_big`. Authority: AGENTS.md, Running the tests (a unit test that depends on the system). The same kind of defect as TST-561.
  - **Resolution: done** (2026-11-19, the developer's report, written by the lead).
    - **Test:** a scratch pytest plugin made `Path.write_text` write `\r\n` without `newline`, as Windows does: 7 tests failed, among them `near_end`'s exact 20,000 bytes refused and `test_the_line_numbers_count_in_the_size`. After the fix, 234 of 234 passed under it.
    - **Cause:** the tests wrote the files they size with `write_text`, which translates `\n` on Windows.
    - **Fix:** one helper, `_write(path, text)`, writes the text's bytes with `write_bytes`; `_big` uses it, with an `end` parameter, and so do all 12 sized writes.
    - **Also covered:** the other byte-exact checks in `tests/unit` write with `write_bytes`, or compare text, which reads CRLF back as LF.

- [x] **AGT-50 · PyCharm's `read_file` ends a line at CRLF and at a lone CR, while the hook split lines only at LF and counted the CR** · `.claude/hooks/large_reads.py` (`_numbered`, `_last`) · measured · found 2026-11-19
  - **Defect.** The developer measured, with `read_file` on files of the project: `a\r\nbb\r\nccc\r\n` and `a\rbb\rccc\r` each showed `L1: a`, `L2: bb`, `L3: ccc` and an empty `L4: `; `dddd\r\r\n` ended two lines; 2,100 lone-CR lines showed `…2095 lines truncated…`. The lead's own `read_file` of the first two files showed the same four lines. Read showed the lone-CR file as one line.
  - **Scenario.** A CRLF file was counted a byte too long per line, so a `read_file` of exactly 20,000 bytes was refused; a lone-CR file was seen as one line, so a read of 20,001 bytes passed.
  - **Fix.** For `read_file` only, read a lone CR as a line end and count a CRLF as one byte; Read and the Bash check keep counting bytes as they are. Found by the developer while addressing AGT-47, settled by the lead.
  - **Resolution: done** (2026-11-19, the developer's report, written by the lead).
    - **Test:** `test_pycharms_read_file_ends_a_line_at_crlf_and_at_a_lone_cr[\r\n, \r]`: before the fix the CRLF case refused the exact read and the CR case let the 20,001-byte read through; a guard checks Read still counts a file of lone CRs as one line. `test_a_crlf_across_the_bytes_read_at_a_time_is_one_line_end` was refused as "21 KB and 2 lines" before the fix. The `short.log` loop gives "21 KB and 2000 lines" for LF, CRLF and CR. `test_a_big_files_lines_ended_by_a_lone_cr_are_read_back_from_its_end` reads under 60 KB for `limit=1` and a whole read.
    - **Cause:** `_numbered` and `_last` took the read tools' lines to end at LF alone; only Read does.
    - **Fix:** `read_file`'s sizing reads the file through `io.BufferedReader(_PyCharmLines(f))`, which reads a lone CR as LF, keeps the file's positions for `_bounded` and `_last`, and looks one byte ahead when a chunk ends in CR. `_shown` counts a CRLF as one byte, passed as the `size` of `_numbered` and `_last`. The measurement is in the module docstring.
    - **Also covered:** Read and the Bash check keep `len`. Whether Read's text keeps the CR is unmeasured; counting it can only over-count, by a byte per CR.
  - Questioned by AGT-62 (2026-11-19).

- [x] **AGT-52 · A commit to `main` isn't gated: the lead commits "on a branch" without asking, and the cleanup commits on `main` within the user's request** · `AGENTS.md:8-10`, `.claude/skills/cleanup-review/SKILL.md:11-12, 52` · confirmed · found 2026-11-19
  - **Defect.** The user's decision: the lead never commits to `main`. AGENTS.md gates only a push and a merge; the cleanup, which usually runs after the merge, commits as part of the user's request. Found by two reviewers.
  - **Scenario.** The user asks for a cleanup after a merge, and the lead commits on `main` unasked.
  - **Fix.** "on a branch other than `main`; a commit to `main` only when the user asks for it", and the cleanup asks for its commit when it runs on `main`. Authority: the user, 2026-11-19.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** AGENTS.md: the lead commits on a branch other than `main`, and before each review; a commit to `main` waits for the user's request. The cleanup asks first on `main`. Docs tests passed.

- [x] **TST-581 · Convergence counts only "from the second review of a branch on", and a first review with no findings has no next step** · `.claude/skills/project-code-review/SKILL.md:192-198` · confirmed · found 2026-11-19
  - **Defect.** The user's rule has no such condition: the reviews converge when a review's new findings are a few Low ones. The old step 7 said a review finding nothing makes the work ready; the move lost it. Found by two reviewers.
  - **Scenario.** A first review finds nothing, or a few Low ones: the skill forces another round, or the lead guesses.
  - **Fix.** A review with no new findings, or only a few Low ones, says the reviews look converged; the few Low ones are fixed before the user chooses ("after they are addressed I proceed to finalization"). `test_review_lookup.py`'s pinned wording follows. Authority: the user, 2026-11-19.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** step 7, in the user's words: the findings count, not the rounds; a few Low ones, the first review included, or none, say the reviews look converged, and the Low ones are fixed before the user is told. `test_review_lookup.py::test_the_wording_of_the_rules_agreed_on` checks "second review" is gone.

- [x] **TST-582 · "Gathered in one brief" contradicts probes split across runners** · `.claude/skills/project-code-review/SKILL.md:44`, `:33-35` · confirmed · found 2026-11-19
  - **Defect.** "Every other probe goes to the `runner` agent, gathered in one brief", beside "a review's probes may be split across runners, each with a port and a Designer of its own".
  - **Scenario.** One lead reads one runner, undoing the split; another reads a contradiction.
  - **Fix.** "gathered in one brief per runner". Authority: the user's decision on parallel work, 2026-11-19.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** "gathered in one brief per runner". Docs tests passed.

- [x] **TST-583 · "How a probe runs" is still written for a review, and a runner on its own port has no named way to run a probe** · `.claude/skills/live-check/SKILL.md:84-101` · confirmed · found 2026-11-19
  - **Defect.** It opens with "A scratch probe settles a review's suspicion", though `address-review` sends the developer's measurements there too; "Close the agent's Designer when the review is done" differs from `developer.md` ("when the unit is done") and `runner.md` ("unless the brief says to keep them"); it names `run_designer_script` and `execute_designer_code`, which reach only the default port (`launch_designer`'s docstring).
  - **Scenario.** A runner given a port of its own runs a probe with the session's tools and reaches another agent's Designer, or none.
  - **Fix.** "a scratch probe, a review's or one measuring for a fix"; "close it when its work is done"; on a port of its own, `SD_BRIDGE_PORT=<port>` with `client/sd_run.py`, or a fresh server. Authority: AGENTS.md, Writing docs (Name what you mean).
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** `live-check`: a probe is a review's or one measuring for a fix; close the Designer "when its work is done"; on a port of its own, `client/sd_run.py` with `SD_BRIDGE_PORT=<port>`, or a fresh server as `alone.run(..., port=...)` opens. Docs tests passed.
  - Questioned by TST-594 (2026-11-19).

- [x] **TST-584 · "It reruns only the failing tests" names no agent, and the step after the fixes is the user's alone** · `.claude/skills/live-check/SKILL.md:103-105` · confirmed · found 2026-11-19
  - **Defect.** "The runner reports the failures, the lead writes each one ..., and the developer fixes them. It reruns only the failing tests until they pass": the runner, which loads this skill, can read "It" as itself. The user's workflow also has the lead recommend another review or the suites again, by the size of the fixes.
  - **Scenario.** The runner reruns tests it was not asked to, or the lead sends the suites back without a word on a review.
  - **Fix.** "The developer reruns only the failing tests"; then the lead recommends another review or the suites again, and the user decides. Authority: the user's workflow, 2026-11-19.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** "The developer reruns only the failing tests"; the lead then tells the user which suites failed and recommends another review or those suites again, by the size of the fixes; the user decides. Docs tests passed.

- [x] **TST-585 · `address-review` has the developer add DECISIONS.md and ROADMAP.md entries once the user approves** · `.claude/skills/address-review/SKILL.md:147-148, 171-172` · confirmed · found 2026-11-19
  - **Defect.** "In your report ... propose its entry to the user, and add it once they approve", and the same for ROADMAP.md, in the skill the developer follows; its run has ended by the time the user answers, and `developer.md` leaves DECISIONS.md changes to the lead.
  - **Scenario.** An approved entry is never added, or the developer adds one unapproved.
  - **Fix.** The developer proposes in its report; the lead asks the user (AGT-51's timing) and adds what they approve. Authority: `developer.md`, Leave these to the lead.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** `address-review`: the developer proposes in its report; the lead asks at convergence, unless the next step needs the answer, and adds what the user approves; the same for ROADMAP.md. Docs tests passed.

- [x] **TST-586 · The lead checks off a reported resolution with no step that assesses it** · `.claude/skills/project-code-review/SKILL.md:233-237`, `.claude/skills/address-review/SKILL.md:119-120` · confirmed · found 2026-11-19
  - **Defect.** "The lead then checks the entry off with a resolution line": only a new problem is settled. The user: "the developer can suggest what and you assess/judge then write or reject".
  - **Scenario.** A doubtful *not a bug* is checked off as reported, and no later review rechecks it once the reviews converge.
  - **Fix.** One clause in Resolving: the lead writes a reported resolution once its evidence holds, as it settles a new problem; the next review rechecks it. Authority: the user, 2026-11-19.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** the review skill's Resolving: the lead assesses a reported resolution as it settles a new problem, writes it once its evidence holds, or sends it back; the next review rechecks it. `address-review` step 7 follows. Docs tests passed.

- [x] **AGT-53 · Several rules have more than one home** · `AGENTS.md:98, 135-137, 239-240, 303-305`, `.claude/agents/developer.md:10-11, 21-23, 80-81, 91-94`, `.claude/skills/project-code-review/SKILL.md:49-51, 178-179, 194-198`, `.claude/skills/address-review/SKILL.md:119-120, 168-170`, `DECISIONS.md:28-29` · confirmed · found 2026-11-19
  - **Defect.** Stated twice or more: convergence and the user's choice (AGENTS.md, the review skill, DECISIONS.md, which lacks "another round"); the criteria always among a brief's (AGENTS.md, `developer.md` twice, one copy without the docs tests); reading the guide first (`developer.md` twice); the lead recording its choices in PLAN.md (AGENTS.md twice); how the lead settles the developer's new problems (the review skill twice, `address-review`); only the lead writes REVIEW.md (AGENTS.md, `address-review`). Found by two reviewers.
  - **Scenario.** An edit to one copy leaves the others behind, as the copies already differ.
  - **Fix.** One home each, the others pointing to it; an agent file may keep its own copy (AGT-21's design). Authority: AGENTS.md, Keeping the docs current.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** one home each, the others pointing: convergence in the review skill's step 7; the criteria always in a brief in the `delegate` skill (`developer.md` keeps its own copy, AGT-21's design); the guide once in `developer.md`; the lead's choices in the loop paragraph; the developer's new problems in Who settles what; REVIEW.md's writer in AGENTS.md. DECISIONS.md's convergence sentence, by the lead: "the user decides: another round, or the final check" (the user's words, 2026-11-19). Docs tests passed.

- [x] **TST-587 · "The commit the last review saw" isn't always a commit, and the review log doesn't record it** · `.claude/skills/project-code-review/SKILL.md:63-64`, `.claude/skills/project-code-review/TEMPLATE.md:52-63` · confirmed · found 2026-11-19
  - **Defect.** The fifth review saw uncommitted work on top of `81b840a`; committing before a review is an example in AGENTS.md, not a step; the log's fields name no commit.
  - **Scenario.** The next review diffs from the wrong point and reviews work again, or misses it.
  - **Fix.** The lead commits before each review, and the log's heading or Scope names the commits reviewed. Authority: the user's decision on commits, 2026-11-19.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** the review skill's Scope: the lead commits before each review, and the round's diff runs between two commits, PLAN.md left out; the log's **Scope** names both; TEMPLATE.md gains the field. Docs tests passed.

- [x] **AGT-54 · AGENTS.md has every developer report reviewed, which leaves no room to group small steps** · `AGENTS.md:237-239`, `.claude/skills/project-code-review/SKILL.md:3` · confirmed · found 2026-11-19
  - **Defect.** "When it reports, the lead has the change reviewed", and the skill's description: "after each developer run". The user: "two small steps can be reviewed at once ... You assess that."
  - **Scenario.** The lead groups two small steps, against both texts, or reviews each trivially small one.
  - **Fix.** The lead has the work reviewed after a step, or a group of small steps it judges together; each step, or group, loops until its reviews converge before the next starts, and the user hears "converged" after the last. Authority: the user, 2026-11-19.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** the loop: reviewed after a step, or a group of small steps the lead judges together, each looping until it converges before the next starts, the user hearing it after the last; the review skill's step 7 and description follow. Docs tests passed.

- [x] **AGT-55 · The criteria always among a developer's make the stop for a missing criterion unreachable** · `.claude/agents/developer.md:20-27`, `AGENTS.md:303-305` · confirmed · found 2026-11-19
  - **Defect.** "At least one mechanically verifiable ... Always among them, said or not: ruff's fix and format run, lint and types passing, ...", then "If no criterion is mechanically verifiable, stop before writing code and report": lint and types are always there.
  - **Scenario.** A brief with no criterion of the unit's own ("make it right") never stops the developer.
  - **Fix.** "at least one of the unit's own (a named test passing, a scratch run exiting 0), beside these". Authority: AGENTS.md, the brief's acceptance criteria.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** "at least one of the unit's own, mechanically verifiable ... beside those always among them" (the `delegate` skill, `developer.md`); `developer.md` stops "if the brief gives no criterion of the unit's own". Docs tests passed.

- [x] **AGT-56 · "The docs tests when Markdown changed" has no home in Running the tests** · `.claude/agents/developer.md:22-23`, `AGENTS.md:155-159, 305` · confirmed · found 2026-11-19
  - **Defect.** `developer.md` cites AGENTS.md, Running the tests, which runs the docs tests only for docs changed alone; DECISIONS.md says the same.
  - **Scenario.** A change of code and Markdown together: one file runs the docs tests, the cited one doesn't say so.
  - **Fix.** One sentence in its home, wherever Step B puts the test commands: the docs tests are the tests of a Markdown change, alone or with code. Authority: the user's "all automated things", 2026-11-19; AGENTS.md, Keeping the docs current.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** `.claude/rules/docs-tests.md` (`**/*.md`): the docs tests are the tests of a Markdown change, alone or with code; AGENTS.md's Running the tests points there. Docs tests passed.

- [x] **AGT-57 · "An analyst whenever a read can be delegated" opens the list of reads the lead keeps, and "only the lines each suspicion quotes" contradicts it** · `AGENTS.md:248-253, 326-327` · confirmed · found 2026-11-19
  - **Defect.** Every read can be delegated, so the "Keep it yourself" list after it never applies; "the lead only the lines each suspicion quotes" contradicts "the read a claim depends on", and step 4's check against DECISIONS.md. "Analysts settle" uses the review skill's word for the lead's judgment.
  - **Scenario.** The lead delegates the one read a claim depends on, or skips the DECISIONS.md check.
  - **Fix.** "whenever a read isn't one of these:"; drop "only"; "analysts answer". Authority: AGENTS.md, Keep it yourself; the review skill, Who settles what.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** AGENTS.md, in the user's words: the lead reads a thing itself when it knows in advance the output will be small; when it can't tell, it asks an analyst. "Keep it yourself" keeps the lines a claim quotes; "only" dropped; "analysts answer". Docs tests passed.

- [x] **AGT-58 · `git diff --stat` leaves out a developer's new files, and shows nothing once the lead has committed** · `AGENTS.md:326` · confirmed · found 2026-11-19
  - **Defect.** "The lead reads its report and the change's size (`git diff --stat`)": with no commit given it compares the working tree with the index, without untracked files.
  - **Scenario.** The lead judges a step small, and groups it, while its new modules go unseen.
  - **Fix.** `git diff --stat <last reviewed commit>` with `git status --short`, as the review skill's Scope does. Authority: AGT-54's grouping.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** "`git diff --stat <last reviewed commit>`, with `git status --short` for the new files". Docs tests passed.

- [x] **AGT-59 · "Files outside the repository" in the stop list catches the scratchpad and `install.py`'s copies** · `AGENTS.md:242` · confirmed · found 2026-11-19
  - **Defect.** Read literally it stops the loop for a scratch script, for `install.py`'s deploy (the plugin folder, the user skill) and an agent's Designer launch, which Deploying and diagnosing and `runner.md` allow without asking.
  - **Scenario.** The lead stops the loop to ask about a scratch probe, or reads the two rules as contradicting each other.
  - **Fix.** "the user's own files outside the repository". Authority: the lead's own wording of decision 2, which the user accepted.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** "the user's own files outside the repository". Docs tests passed.
  - Questioned by TST-630 (2026-11-20).

- [x] **AGT-60 · The merge adds the DECISIONS.md and ROADMAP.md entries after the final check, which the docs tests then never run on** · `AGENTS.md:103-105` · confirmed · found 2026-11-19
  - **Defect.** "once the final check passed ... the lead first proposes ... adds what they approve, and deletes PLAN.md": the docs tests read both files (`test_guide.py`, `test_review_lookup.py`).
  - **Scenario.** An approved entry breaks a docs test and enters `main` unchecked.
  - **Fix.** The entries come at convergence, before the final check (AGT-51); only PLAN.md's deletion comes after it. Authority: DECISIONS.md, Project rules (the final check before the merge).
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** the merge paragraph: what must outlast the branch is in DECISIONS.md or ROADMAP.md before the final check; after it, the lead deletes PLAN.md. Docs tests passed.

- [x] **AGT-61 · `analyst.md`'s description claims every web fetch, though the developer fetches a page it can name** · `.claude/agents/analyst.md:3` · confirmed · found 2026-11-19
  - **Defect.** "and every web fetch or search", against `developer.md` and AGENTS.md; the description now reaches the developer, which starts analysts. AGT-22's and AGT-30's pattern, in a new sentence.
  - **Scenario.** A developer reads the description and sends a known page to an analyst, or doubts its own WebFetch.
  - **Fix.** "every web search, and the lead's web fetches". Authority: AGENTS.md, the lead never fetches; `developer.md`'s web paragraph.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** `analyst.md`'s description: "every web search, and the lead's web fetches". **Also covered:** AGENTS.md's routing row, with the same pattern. Docs tests passed.

- [x] **AGT-62 · No test guards the CRLF counting `_bounded` passes to `_last` · follows AGT-50, generation 2** · `.claude/hooks/large_reads.py:705`, `tests/unit/test_large_reads.py:754-770` · measured · found 2026-11-19
  - **Defect.** `last = _last(f, count - empty, after, _shown)`: with `_shown` dropped, every test in `test_large_reads.py` still passes. The runner's probe, in a copy of `9910caa`: 231 passed and 3 failed (the copy's missing venv) before and after the mutation.
  - **Scenario.** The runner's file, `b'x\r\n' * 399_900 + (b'p' * 386 + b'\r\n') * 100` (over 1 MB), read by `read_file(offset=100_001, limit=100)`: 19,992 bytes, let through; under the mutation, refused as "over 20 KB".
  - **Fix.** That case as a test, seen failing under the mutation and passing without it. Authority: AGENTS.md, Review your own work (would each test fail without the change it guards).
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_large_reads.py::test_a_big_files_last_lines_read_back_count_a_crlf_as_one_byte`, the runner's file and read: with `_shown` dropped from `_bounded` it failed ("over 20 KB", lower bound 20,012); unmutated it passes, the tail read exactly at 19,992 bytes.
    - **Cause:** no test reached `_bounded`'s count of a CRLF as one byte. **Fix:** the test alone. **Also covered:** the CRLF-crossing test still fails without `peek` in `_PyCharmLines.readinto`, at 8 KiB and at 128 KiB.

- [x] **TST-588 · Two of the hook's tests assume an 8 KiB buffer, which Python 3.14 raised to 128 KiB** · `tests/unit/test_large_reads.py:97-103, 701`, `tests/unit/counted_reads.py:16-26`, `.claude/hooks/large_reads.py:616` · confirmed · found 2026-11-19
  - **Defect.** CPython 3.14 raised `io.DEFAULT_BUFFER_SIZE` from 8 KiB to 128 KiB (gh-117151, commit `b1b4f96`; `Modules/_io/_iomodule.h` at `v3.14.0`). The CRLF-crossing test builds its file from it, and `Counter`'s reader and the hook's `io.BufferedReader(_PyCharmLines(f))` take the default size. The venv runs 3.12.10 today; the project accepts 3.12 or later.
  - **Scenario.** In a venv of Python 3.14: the crossing test's file becomes 131,073 bytes and is refused; each `at_most(LITTLE, ...)` check counts a first fill of 131,072 bytes against 60,000.
  - **Fix.** Give the readers a fixed size (`BLOCK`) and build the test from it. The hook's sizes stay right either way. Authority: DECISIONS.md, Project rules (Python 3.12 or later).
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** a scratch pytest plugin set the default buffer to 128 KiB on the 3.12 venv: 6 failed at `850dfd5` (the crossing test refused at "132 KB and 2 lines"; five `at_most(LITTLE)` blocks counted 131,072 or 262,144 bytes); 235 passed after the fix, and on 3.12 as is.
    - **Cause:** the hook's readers and `Counter` took Python's default buffer size, and the crossing test was built from it. **Fix:** the hook reads with `BLOCK` (8,192) in its two `open` calls and its `io.BufferedReader`; `Counter.open` mirrors `open`'s `buffering`, so a hook `open` without the size fails (5 failed before the hook passed it); the crossing test is built from the hook's `BLOCK`.

- [x] **AGT-63 · AGENTS.md sends every refused read to Read's `offset` and `limit`, notebooks included · follows AGT-49, generation 3** · `AGENTS.md:273-276` · confirmed · found 2026-11-19
  - **Defect.** "Read fewer lines with Read's `offset` and `limit`", while the hook now sends a refused notebook to `read_file`, Read showing a notebook unsized.
  - **Scenario.** The lead follows AGENTS.md over the refusal's text and reads a notebook unsized.
  - **Fix.** Generation 3, docs: narrow the sentence to "as the refusal says", which makes the claim smaller. Authority: the review skill, Follow-up chains.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** generation 3, narrowed: "Read fewer lines, as the refusal says, or ask the `analyst`"; the hook's refusal states the rest. Docs tests passed.

- [x] **AGT-64 · The hook's `assert isinstance(f, io.BufferedReader)` gives `f` an implicit `Any`** · `.claude/hooks/large_reads.py:618` · measured · found 2026-11-19
  - **Defect.** typeshed's `BufferedReader` is generic, and `isinstance` narrows `f` to `BufferedReader[Any]`: a runner's probe, `reveal_type(f)` after the assert in a copy of the hook, under the repository's `mypy.ini`, printed `Revealed type is "_io.BufferedReader[Any]"`. The hook avoids this pattern elsewhere (`_list`, `_dict`).
  - **Scenario.** No effect at runtime; mypy checks nothing through the `Any` in a function this branch changed.
  - **Fix.** `_PyCharmLines` takes a `BinaryIO` and looks a byte ahead with `read(1)` and a `seek` back, dropping the assert, or a `TypeIs[io.BufferedReader]` helper. Authority: `.claude/rules/python.md`, the most specific type that fits.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** a scratch probe, `reveal_type(f)` in a copy of the hook under `mypy.ini`: `_io.BufferedReader[Any]` before, `typing.BinaryIO` after; no unit test, mypy reporting no implicit `Any`. `test_large_reads.py`: 235 passed.
    - **Cause:** `_PyCharmLines` called `peek`, which only `BufferedReader` has, so `_returned` narrowed `f` with an assert into typeshed's generic class. **Fix:** `_PyCharmLines` takes a `BinaryIO` and looks a byte ahead with `read(1)` and a seek back; no assert. **Also covered:** the hook's other generic `isinstance` calls are inside `_dict` and `_list`.

- [x] **TST-589 · A test comment cites PLAN.md, which never enters `main`** · `tests/unit/test_agents.py:132` · confirmed · found 2026-11-19
  - **Defect.** "PLAN.md Step B part 4: ..."; the only such citation outside PLAN.md and REVIEW.md. Found by two reviewers.
  - **Scenario.** After the squash merge the comment points at a file `main` never holds.
  - **Fix.** Cite AGENTS.md, Delegating to subagents (A long run). Authority: AGENTS.md, A branch's plan.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Fix:** the comment cites AGENTS.md, Delegating to subagents (A long run). **Also covered:** no other `.py` file cites a PLAN.md section.

- [x] **AGT-65 · AGENTS.md's pointer to the suites' commands names no path** · `AGENTS.md:149, 158` · confirmed · found 2026-11-19
  - **Defect.** "The command for each run the user asks for: the `live-check` skill, The suites." The approved step: "a pointer it follows names a path it can Read"; every other moved part's pointer does. Found by two reviewers.
  - **Scenario.** A reviewer or an analyst, without the Skill tool, looks for the commands and has to find the file.
  - **Fix.** Add `.claude/skills/live-check/SKILL.md`. Authority: the approved Step B, part 1.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_agents_md_names_each_skill_with_its_path`, over every skill AGENTS.md names; it failed first (`['live-check'] == []`). **Fix:** the path at both places.
  - Note (2026-11-20): the test is now `test_agents_md_and_decisions_md_name_each_skill_with_its_path`, over DECISIONS.md too (the user, 2026-11-20).

- [x] **TST-590 · The docs-only final check is missing where the final check is given** · `AGENTS.md:148`, `.claude/skills/live-check/SKILL.md:121` · confirmed · found 2026-11-19
  - **Defect.** "The final check is both suites in full"; live-check's "**Both suites** (the final check included)". The old AGENTS.md kept the exception beside them (docs changed alone run only the docs tests, the final check included); it now lives in `.claude/rules/docs-tests.md` and DECISIONS.md only.
  - **Scenario.** A branch of docs alone: the runner, following its preloaded live-check, runs both suites instead of the docs tests. Time lost, no work at risk.
  - **Fix.** One clause at both places: docs changed alone, `.claude/rules/docs-tests.md`. Authority: the approved Step B, part 1 ("No rule changes meaning in the move").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_where_the_final_check_is_given_so_is_its_form_for_docs_alone`, failing first. **Fix:** one clause at each place, pointing to `.claude/rules/docs-tests.md`.
  - Questioned by TST-597 (2026-11-19).

- [x] **TST-591 · live-check's "The suites" states the macOS pool twice** · `.claude/skills/live-check/SKILL.md:121-125, 139-141` · confirmed · found 2026-11-19
  - **Defect.** "On macOS it runs every category in a Designer of its own, several at once ..." and again "On macOS a pool, each category in a Designer of its own, several at once ...".
  - **Scenario.** An edit to one leaves the other stale.
  - **Fix.** Drop the repeat from the second bullet. Authority: AGENTS.md, Keeping the docs current.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_the_live_check_skill_says_once_how_the_pool_runs`, failing first (count 2). **Fix:** the repeat dropped; the bullet keeps its `workers.py` pointer, which another test pins.
  - Questioned by TST-600 (2026-11-19).

- [x] **TST-592 · `address-review` keeps its own test command, without the docs tests, and a test comment says the command lives in one place** · `.claude/skills/address-review/SKILL.md:88-89`, `tests/unit/test_guide.py:466` · confirmed · found 2026-11-19
  - **Defect.** Step 4 gives `pytest tests/unit/test_x.py::test_name tests/unit/test_lint.py tests/unit/test_types.py`, though the same skill's step 5 changes Markdown, whose tests `docs-tests.md` requires; `test_guide.py:466` says the command is "once, in the rule every Python file loads ... not in AGENTS.md nor in the skill", and checks only AGENTS.md and live-check.
  - **Scenario.** A developer addressing docs findings follows step 4 literally and runs no docs tests.
  - **Fix.** Step 4 points to `.claude/rules/python.md` and `docs-tests.md` instead of its own copy; the comment says what the test checks. Authority: AGENTS.md, Keeping the docs current.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** the rules test for all Python now checks every skill, failing first on `address-review`. **Fix:** step 4 points to `.claude/rules/python.md` and `docs-tests.md`; README keeps its own commands, being for people.

- [x] **TST-593 · TEMPLATE.md's Scope example leaves PLAN.md in, and its IDs line lacks AGT · follows TST-580, generation 2** · `.claude/skills/project-code-review/TEMPLATE.md:54` and its **IDs** line · confirmed · found 2026-11-19
  - **Defect.** "`git diff <last> <this>`" without `-- . ':(exclude)PLAN.md'`, which the skill's Scope gives; the template's **IDs** line has no **AGT**, which REVIEW.md's has.
  - **Scenario.** The lead copies the logged command into the next round's brief, and the reviewer's diff prints PLAN.md; a REVIEW.md made from the template lacks the prefix.
  - **Fix.** The example ends with the exclusion; the IDs line gains AGT. Generation 2: the test of TST-580 may read the template too. Authority: TST-580.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** the diff-command test reads TEMPLATE.md too, failing first on `git diff <last> <this>`; `test_the_template_names_every_prefix_review_md_names`, failing first on AGT. **Fix:** the example ends with the exclusion; the IDs line matches REVIEW.md's (AGT, and SRV's and INS's missing paths), with `AGT-0` on the template's **Last used**, as the counter check requires; `_recreated` follows.

- [x] **TST-594 · "How a probe runs" points to an ambiguous "point 4", and two of its bullets still fit a review's probe only · follows TST-583, generation 2** · `.claude/skills/live-check/SKILL.md:86, 101-105` · confirmed · found 2026-11-19
  - **Defect.** "(the `address-review` skill, point 4)": that skill numbers two lists, and its own references name the section; "What goes in the entry" and "the agent addressing the finding writes the real test" apply only to a review's probe.
  - **Scenario.** A developer lands on "Run the tests again", or applies the entry rules to its own measurement.
  - **Fix.** Name the section (**All the findings' tests first, run together**, point 4) and mark those two bullets as a review's. Authority: AGENTS.md, Writing docs (Name what you mean).
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_a_point_of_a_skill_is_named_with_its_list`, over every skill, failing first (`skill, point 4`). **Fix:** the section named; the two bullets marked as a review's probe.

- [x] **TST-595 · The skills' description test fails on a hidden file in `.claude/skills/`** · `tests/unit/test_review_lookup.py:747` · confirmed · found 2026-11-19
  - **Defect.** `@pytest.mark.parametrize('skill', sorted(os.listdir(os.path.join(ROOT, SKILLS))))` makes a case of every name, a `.DS_Store` included.
  - **Scenario.** On this Mac, a `.DS_Store` in `.claude/skills/` (ignored by `.gitignore`) becomes a case that reads `.claude/skills/.DS_Store/SKILL.md` and errors.
  - **Fix.** List folders only, skipping names starting with `.`, as `test_constants.py` does (TST-79). Authority: TST-79's precedent.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_the_skills_are_the_folders_with_a_skill_md`, on a `tmp_path` copy of `.claude/skills/` with a `.DS_Store`, failing first. **Fix:** `_skills()` lists folders only, without hidden names, for both skill-parametrized tests. **Also covered:** the other `listdir` and `iterdir` calls in `tests/unit` filter by suffix or name.

- [x] **AGT-66 · Three pointers still send readers to AGENTS.md for rules that moved out, and the test meant to catch them can't** · `mypy.ini:18`, `ROADMAP.md:52, 118`, `tests/unit/test_guide.py:325, 328-346` · confirmed · found 2026-11-19
  - **Defect.** `mypy.ini`: "takes AGENTS.md's mark (typing)"; ROADMAP item 5's Approach: "AGENTS.md's registration note"; item 104: "(AGENTS.md: a fake standing in for a type it can't subclass)". The stale-link test scans only `.md` and `.py` files, its `MOVED_OUT` pattern has none of these forms and matches correct sentences ("AGENTS.md asks for ..."), and it reads PLAN.md, the lead's free text, while leaving REVIEW.md out.
  - **Scenario.** Whoever works on item 5 or 104, or reads the mypy setting, finds the rule gone from AGENTS.md; a PLAN.md sentence about the move fails the docs tests.
  - **Fix.** Point the three to their rule files; narrow the test to the forms the move left stale, add `mypy.ini` to what it reads, and leave PLAN.md out as REVIEW.md is. Authority: AGENTS.md, Keeping the docs current (fix notes that turn out wrong).
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** the stale-link test, failing first on the three pointers. **Fix:** they name `.claude/rules/python.md` and `install.md`; `MOVED_OUT` holds five patterns of the stale forms (all 10 the move removed and the 3 found here, none of "AGENTS.md asks for a test" or "AGENTS.md, Running the tests", a scratch check); the scan reads `.ini` and `.toml` files too and leaves PLAN.md out.
  - Questioned by AGT-72 (2026-11-19).

- [x] **AGT-67 · The docs give three triggers for loading a rule, and the measured one is wider** · `AGENTS.md:26-27`, `.claude/agents/reviewer.md:45-46`, `tests/unit/test_guide.py:289, 306`, `ROADMAP.md:24` · measured · found 2026-11-19
  - **Defect.** "its Read or Write opens", "only when its Read opens", "read or edited". Measured in subagents, 2026-11-19: a Read loads a matching rule (the reviewers' own reads); a Write does (the developer's); a Bash read does too: a runner's first command, `sed -n 1,3p tests/test_all_tools/alone.py`, brought `live-checks.md` and `python.md`, and `sed -n 1,3p mcp_server/server.py` brought `designer-code.md`; each rule came once, later matches bringing nothing; PyCharm's `read_file` doesn't load one (the developer's). Found by two reviewers.
  - **Scenario.** An agent told "only Read" re-reads a rule by hand, or one told Bash loads nothing reads a file through Bash expecting no rule.
  - **Fix.** One wording, in one home: a rule loads, once per agent, when a Read, a Write or a Bash read touches a matching file, not on PyCharm's `read_file`; the others point there. Authority: AGENTS.md ("A claim in these docs without a test is a guess").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_one_doc_says_when_a_rule_loads`, failing first on the old wordings (AGENTS.md, `reviewer.md`, ROADMAP, two in `test_guide.py`). **Fix:** one wording in AGENTS.md, the others pointing there. **Also covered:** the developer's own Bash reads loaded `live-checks.md` and `unit-tests.md`, as measured.
  - Questioned by AGT-71 (2026-11-19).

- [x] **AGT-68 · The status answer names no recipient, and AGENTS.md's long-run paragraph records neither the measurement nor the timer's end** · `.claude/agents/developer.md:105-106`, `.claude/agents/runner.md:60-61`, `AGENTS.md:259-262` · confirmed · found 2026-11-19
  - **Defect.** The approved step: "only to answer the lead (`main`)"; the files say "answer it with SendMessage". Step B part 4 was measured (PLAN.md's record, 2026-11-19): told to answer `main`, a runner did, and its answer reached the lead within seconds; the lead's question moved the runner's foreground command to the background without stopping it; a background `sleep 120` woke the lead when it ended. AGENTS.md states the protocol as unmeasured, and says nothing of stopping the timer when the run ends first.
  - **Scenario.** A lead's question that doesn't name its sender: the agent guesses `to`, and a wrong guess loses the answer. A timer left running after the run ends wakes the lead for nothing.
  - **Fix.** Name `main` in both agent files; AGENTS.md records the measurement, one timer per long run, stopped with TaskStop when the run ends first. Authority: the approved Step B, part 4.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_only_the_agents_of_long_runs_can_answer_the_lead` requires "SendMessage to `main`"; `test_agents_md_says_how_a_long_run_is_timed`; both failing first. **Fix:** both agent files name `main`; AGENTS.md's long-run paragraph has one timer per run, stopped with TaskStop when the run ends first, and the 2026-11-19 measurements.

- [x] **AGT-69 · The rule for an edited agent file covers a started agent, not a resumed one, nor a change of preloaded skills or effort** · `AGENTS.md:342-344` · confirmed · found 2026-11-19
  - **Defect.** "the lead starts it with a brief that has it read its file"; the approved step: "An agent started, or started again". The loop resumes the same developer with SendMessage for a round of fixes, and a resumed agent keeps, as far as anyone knows, the definition it was started with. AGENTS.md names instructions, tools and model, not `skills:` or `effort:`.
  - **Scenario.** A developer resumed after an edit follows the old `developer.md`, or lacks a tool the edit added.
  - **Fix.** "starts it, or resumes it with SendMessage, with a brief or message that has it read its file first"; a change of tools, model, preloaded skills or effort takes a new agent, started after the user's next message. Authority: the approved Step B, part 3.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_agents_md_says_how_an_edited_agent_file_reaches_an_agent`, failing first. **Fix:** a resumed agent gets a message that has it read its file; a change of tools, model, preloaded skills or effort takes a new agent after the user's next message.

- [x] **AGT-70 · `designer-code.md`'s paths miss the self-test's `raw_request`, which it says changes with the protocol** · `.claude/rules/designer-code.md:29` and its `paths:`, `tests/test_all_tools/common.py:147` · confirmed · found 2026-11-19
  - **Defect.** The rule says the self-test's `raw_request` speaks the bridge protocol and changes with the plugin and `core.py`; editing `tests/test_all_tools/common.py` loads only `live-checks.md`. Before the move every agent had the rule from AGENTS.md. Found by two reviewers.
  - **Scenario.** A change to `raw_request` drifts from the protocol, which only the live run shows.
  - **Fix.** Add the path to the rule and to `RULES` in `test_guide.py`. Authority: the approved Step B, part 1 ("No rule changes meaning in the move").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `RULES`' `designer-code.md` entry, failing first against the rule's paths. **Fix:** `tests/test_all_tools/common.py` added to the rule's `paths:`, and the bridge bullet names it.

- [x] **TST-596 · The counter check never checked a prefix that ends a line of the IDs, SRV among them** · `tests/unit/test_review_lookup.py` (`_counter_problems`) · confirmed · found 2026-11-19
  - **Defect.** It matched prefixes with `\*\*([A-Z]{3})\*\* `, a space required after the bold; REVIEW.md's and the template's **IDs** lines break after `**SRV**`. Found by the developer while fixing TST-593, settled by the lead by reading the header.
  - **Scenario.** A **Last used** line missing SRV, or below its highest number, passes the check.
  - **Fix.** `\s` after the bold, in a `_prefixes` helper the check and `_recreated` use.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** a new case in `test_the_counter_check_catches`; a scratch check found `['HLP']` with the old pattern and `['HLP', 'SRV']` with the new.

- [x] **AGT-71 · AGENTS.md says "a Bash read" loads a rule, wider than what loads one · follows AGT-67, generation 2** · `AGENTS.md:26-27` · measured · found 2026-11-19
  - **Defect.** "when a Read, a Write or a Bash read touches a file the rule's `paths:` match". A runner's probe, each command its first call on a file whose rule hadn't come: `grep -n "^def " install.py` brought `python.md` and `install.md`; `cd <repo> && sed -n 1,3p mcp_server/server.py` brought `designer-code.md`; `sed -n 1,3p tests/unit/conftest.py` brought `unit-tests.md`; `wc -c tests/test_all_tools/alone.py` brought none; `sed -n 1,3p ROADMAP.md | head -1` brought none. A reviewer's `grep ... | head -50` and `wc -c` brought none either.
  - **Scenario.** An agent that counted or piped a file believes its rule loaded, and skips reading it.
  - **Fix.** Narrow to what was measured: a Read, a Write, or a Bash command printing the file unpiped (`sed -n`, `grep`), and not `wc -c` or a pipe; the phrase `test_one_doc_says_when_a_rule_loads` pins follows. Generation 2. Authority: AGENTS.md ("A claim in these docs without a test is a guess").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_one_doc_says_when_a_rule_loads` pins the measured wording and catches "Bash read"; it failed first on the old AGENTS.md. **Fix:** AGENTS.md: a rule loads once per agent when a Read or a Write touches a matching file, or a Bash `sed -n` or `grep` prints its lines unpiped; a `wc -c`, a piped command and PyCharm's `read_file` load none. **Also covered:** no other doc gives a trigger.

- [x] **TST-597 · The final check restated without its docs-alone form, where TST-590's fix didn't reach · follows TST-590, generation 2** · `.claude/skills/project-code-review/SKILL.md:176`, `.claude/skills/live-check/SKILL.md:131`, `AGENTS.md:139-140, 180`, `.claude/agents/runner.md:18` · confirmed · found 2026-11-19
  - **Defect.** Step 7 offers "the final check (both suites in full: AGENTS.md, Running the tests)"; live-check: "not a final check, which stays a full run"; lighter restatements in AGENTS.md and `runner.md`.
  - **Scenario.** On a branch of docs alone, the lead following step 7 offers both suites, about 4 minutes with the user's Designer closed: TST-590's scenario, at places its fix didn't list.
  - **Fix.** Narrow, not restate: "the final check (AGENTS.md, Running the tests)", and drop "which stays a full run". Generation 2. Authority: TST-590.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_no_paragraph_says_what_the_final_check_runs_without_its_form_for_docs_alone`, failing first on 3 (live-check, step 7, `tests/test_all_tools/__main__.py`'s `--only` help). **Fix:** the two agreed places and the help. **Also covered:** AGENTS.md:140 and :180 and `runner.md`:18 left, the lighter ones the Fix didn't name, beside DECISIONS.md's same sentence (the user's).

- [x] **TST-598 · Two of a reviewer's rules stayed in the review skill** · `.claude/skills/project-code-review/SKILL.md:90-99`, `.claude/agents/reviewer.md:47-48` · confirmed · found 2026-11-19
  - **Defect.** `reviewer.md` keeps "That is no finding in itself" and the lookup, but not "In a full clone, that makes the citation a broken reference or a lost finding; say which you can tell", nor "An old resolution's commit hash may no longer resolve ... That isn't a finding either"; `reviewer.md` now says the skill needn't be read.
  - **Scenario.** A reviewer drops a citation whose lookup says the ID never existed, or reports a hash that doesn't resolve (REVIEW.md cites CPython's `b1b4f96`).
  - **Fix.** Move both sentences to `reviewer.md`'s bullet. Authority: the approved round item ("A reviewer then gets all it needs from its file and its brief").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_a_reviewer_needs_only_its_file_and_its_brief` gains the two rules, in `reviewer.md` and not in the skill; it failed first. **Fix:** both sentences in `reviewer.md`'s bullet; the skill keeps the lookup and the lead's part.

- [x] **TST-599 · "The reviewer's rules (step 3)" reads as a step of `reviewer.md`, which has none** · `.claude/skills/project-code-review/SKILL.md:131-132, 134-135, 190-191` · confirmed · found 2026-11-19
  - **Defect.** "(their rules: step 3)", "as their rules say (step 3)", "why chains grow is in the reviewer's rules (step 3)".
  - **Scenario.** The lead settling a generation-3 finding looks for a step 3 in `reviewer.md`.
  - **Fix.** Name the place: `.claude/agents/reviewer.md`, and the section (Follow-up chains, Rechecking a resolution), as `address-review` and TEMPLATE.md do. Authority: AGENTS.md, Writing docs (Name what you mean).
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_the_review_skill_names_the_reviewers_rules_by_file_and_section`, failing first on `rules: step 3` and the others; it requires each pointer to name an existing heading of `reviewer.md`. **Fix:** the three pointers name the file and the section.

- [x] **AGT-72 · ROADMAP items 98 and 99 still point to rules that moved, and the stale-link patterns miss them and over-match · follows AGT-66, generation 2** · `ROADMAP.md:116-117`, `tests/unit/test_guide.py:331-337` · confirmed · found 2026-11-19
  - **Defect.** Item 98: "(the `project-code-review` skill)" for what reviewers report, and "AGENTS.md now asks for the most specific type"; item 99: "AGENTS.md's typing paragraph gives the mark and its line". `MOVED_OUT` accepts "typing rules" but not "typing paragraph", and `mark` and `command` have no word end, so a correct "AGENTS.md marks ..." or "AGENTS.md commands ..." would fail. Found by both reviewers.
  - **Scenario.** A reader of items 98 and 99 looks in AGENTS.md or the skill for a rule that moved; the docs tests stay green.
  - **Fix.** Point both items to `.claude/rules/python.md` and `.claude/agents/reviewer.md`; `typing\s+(?:rules|paragraph)`, `mark(?:ed)?\b`, `command\b`. Generation 2. Authority: AGENTS.md, Keeping the docs current.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** the stale-link test with the widened patterns failed first on items 98 and 99 exactly; `test_the_moved_out_patterns_find_the_stale_forms_only` checks 14 samples, stale and correct, of which the old patterns got 4 wrong. **Fix:** `typing\s+(?:rules|paragraph)`, `mark(?:ed)?\b`, `command\b`, a pattern for "asks for the most specific type", one compiled pattern; items 98 and 99 repointed. **Also covered:** item 99's past-tense Why kept as history; item 98's skill pointer is fixed but pinned by no test.

- [x] **TST-600 · live-check's pointer to `workers.py` lost its subject · follows TST-591, generation 2** · `.claude/skills/live-check/SKILL.md:141-142` · confirmed · found 2026-11-19
  - **Defect.** "every tool over MCP against the real Designer (`tests/test_all_tools/workers.py`; its docstring has the rules)": with "On macOS a pool" gone, "the rules" reads as the live suite's; `workers.py` holds the pool's.
  - **Scenario.** A reader looks in `workers.py` for the live suite's rules.
  - **Fix.** "(the pool: `tests/test_all_tools/workers.py`)". Generation 2. Authority: AGENTS.md, Writing docs.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** the pin in `test_the_skills_bullet_points_at_workers_py...`, failing first in its 6 cases. **Fix:** "(the pool: `tests/test_all_tools/workers.py`)".

- [x] **TST-601 · `re.findall`'s implicit `list[Any]` in functions the round added or changed** · `tests/unit/test_agents.py:218`, `tests/unit/test_guide.py:512`, `tests/unit/test_review_lookup.py:180-185` · confirmed · found 2026-11-19
  - **Defect.** `commands = re.findall(...)`, `named = set(re.findall(...))`, and in `_counter_problems` `lines`, `counters` (`dict[Any, int]`) and the loop's `prefix, number`: typeshed types `re.findall` as `list[Any]`.
  - **Scenario.** mypy checks nothing through them (`command.endswith(...)`, `counters.get(prefix, ...)`).
  - **Fix.** Annotate the locals: `list[str]`, `set[str]`, `dict[str, int]`, `list[tuple[str, str]]`. Authority: `.claude/rules/python.md` (an implicit `Any` in a function you change is narrowed).
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** a scratch probe, mypy with `--disallow-any-expr` on the three files: the `list[Any]`, `dict[Any, int]` and `tuple[Any, Any]` reported before were gone after; none in the suite, mypy reporting no implicit `Any`. **Fix:** `commands: list[str]`, `named: set[str]`, and in `_counter_problems` typed `lines`, `used` and `entries`, `counters` inferred `dict[str, int]`. **Also covered:** the `re.findall` calls left are expressions, not locals.

- [x] **AGT-75 · The story's Adapt column understates what is specific to this project** · `docs/agent-workflow.md:176, 181-187` · confirmed · found 2026-11-19
  - **Defect.** The agent files' bodies and descriptions are about Designer (`developer.md`'s triage and Designer section, `runner.md`'s, `analyst.md`'s "Designer facts", `reviewer.md`'s GUIDE.md); the skills hold Designer probes, the self-test and GUIDE.md; live-check's How a probe runs is Designer only; the hook's READING_TOOLS and `settings.json` name PyCharm's tools; the tests import the server, `conftest.py` and helper modules the table doesn't list, and pin chosen facts, not "every rule in one home".
  - **Scenario.** Another repository keeps Designer instructions in its agents, or copies tests that fail at import.
  - **Fix.** Complete each Adapt cell; say the tests need rewriting with their helpers; narrow "every rule in one home". Authority: Step C's text.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead). Docs alone: the docs tests passed (606).
    - **Fix:** every Adapt cell names this project's specifics (AGENTS.md's Designer, PyCharm and self-test passages; the agents' descriptions, bodies, effort and commands; the skills' probes, live checks and GUIDE.md; live-check replaced whole, keeping its order and scratch probes; the hook's `READING_TOOLS`, matchers, venv); the tests row says to rewrite them, names their helpers, and that they pin chosen facts.
  - Questioned by TST-630 (2026-11-20).

- [x] **AGT-76 · Some of the story's claims rest on nothing in the repository** · `docs/agent-workflow.md:129, 144, 156, 160-161, 168-169` · confirmed · found 2026-11-19
  - **Defect.** "about 28,000 tokens" (in PLAN.md only, which dies with the branch); "The lead writes and commits while agents run" (a commit while the developer edits takes its half-done files); "Claude Code loads agent definitions then" (a mechanism; only when agents saw an edit was measured); "Load a skill fresh each time you use it" (in no setup file); "a choice of the user's, who judged such hooks too complex" (DECISIONS.md gives other words and reasons).
  - **Scenario.** Another repository copies a guess as a rule.
  - **Fix.** Cite a home, narrow or drop each; commits between developer runs; the measured behaviour, not the mechanism; give the fresh-skill rule a home in the setup or drop it; DECISIONS.md's wording. Authority: AGENTS.md ("A claim in these docs without a test is a guess").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead). Docs alone: the docs tests passed (606).
    - **Fix:** the 28,000 tokens dropped for a pointer; "The lead commits between the developer's runs" and before each review; the measured behaviour of an edited agent file, with a pointer; the fresh-skill rule given a home in AGENTS.md (Delegating to subagents, after the `delegate` paragraph), backed by Claude Code's docs (Skills, Skill content lifecycle, fetched by the developer), the story pointing there; DECISIONS.md's entry title for the write guard. **Also covered:** the two "safety net" sentences dropped; step 5 cites the review skill's Scope.

- [x] **AGT-77 · The story restates some rules wider, narrower or otherwise than their homes** · `docs/agent-workflow.md:12, 110-115, 133-134, 145, 153-154, 163-165` · confirmed · found 2026-11-19
  - **Defect.** When a rule loads: "a shell command prints it unpiped (`sed -n`, `grep`)", wider than AGENTS.md's two measured commands; "no review while the developer still edits the code under review", against AGENTS.md's "No review starts while the developer edits"; "A subagent's messages come from the lead", against "from the agent that started it"; Claude Code's cap and the saved output, against AGENTS.md's 10,000 characters, this project's setting, and the 2 KB preview; the chains' rule without its conditions (Low or Low-medium, tests or docs only); the files table's "anyone" for files the analyst and the reviewer never write, and "the lead" for DECISIONS.md's names and paths, which the developer keeps current too.
  - **Scenario.** The story, given to another repository, teaches a rule its home doesn't hold.
  - **Fix.** Point to each rule's home or copy its exact wording; where in doubt, narrow. Authority: Step C's "Reviews check it against the setup"; AGENTS.md, Keeping the docs current.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead). Docs alone: the docs tests passed (606).
    - **Fix:** each restated rule points to its home or matches it: when a rule loads, the review and the developer's edits, whose messages a subagent gets, this project's output cap, the chains' conditions, the files table's writers. **Also covered:** the hooks bullet points instead of copying figures; the user-facing-skills lesson cites AGENTS.md's rule; step 13 follows the cleanup skill; "in a line or two".
  - Questioned by TST-630 (2026-11-20).

- [x] **AGT-78 · The story tells some rules only in part** · `docs/agent-workflow.md:46-47, 62-64, 79, 101, 135-138, 157-158` · confirmed · found 2026-11-19
  - **Defect.** `/simplify` always, without "A change of docs alone skips this step"; the timer without telling the user, starting it again, or stopping it with TaskStop; the edited-agent lesson without effort, or the lead telling the user; "a cost far over what was announced" without the lead announcing cost and time before a long unit; judging without the probes the lead keeps or Not verified; convergence without the reviewers' Unspecified items.
  - **Scenario.** Another repository's lead skips what the story leaves out.
  - **Fix.** One clause each, or a pointer to the home. Authority: Step C's "What it covers".
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead). Docs alone: the docs tests passed (606).
    - **Fix:** one clause or pointer each: `/simplify` unless docs alone; the timer's telling, restarting and TaskStop; the edited-agent home; announcing cost and time; the lead's own probes and Not verified; the Unspecified items at convergence.
  - Questioned by TST-630 (2026-11-20).

- [x] **AGT-79 · The story is tied to this branch and its date, though it is to be kept current** · `docs/agent-workflow.md:5-6, 189` · confirmed · found 2026-11-19
  - **Defect.** "as it stands at the end of the `agent-delegation` branch (ROADMAP item 102, 2026-11)" and "this branch took eight", while AGENTS.md's row says the story is updated with every change to the setup.
  - **Scenario.** The next change to the setup makes the opening false; "eight" is already nine.
  - **Fix.** Drop the branch, the item and the count, or move them to a dated note. Authority: AGENTS.md's row for the story.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead). Docs alone: the docs tests passed (606).
    - **Fix:** the branch, item and date replaced by "It is updated in the change that alters the setup it tells (AGENTS.md, Keeping the docs current)"; "this branch took eight" dropped; the heading "What the setup learned".

- [x] **AGT-80 · AGENTS.md's one-place rule doesn't name the story's retelling** · `AGENTS.md:287-289, 305` · confirmed · found 2026-11-19
  - **Defect.** "Keep each fact in one place ... One repeat is deliberate", while the story retells the loop, the hooks' limits and the rules' triggers by design, and has already drifted (AGT-77, AGT-78).
  - **Scenario.** A reviewer reports the story as a second home, or an editor of a rule's home doesn't know to update it.
  - **Fix.** Name the story as a deliberate retelling that defers to the homes, preferring pointers to copied figures. Authority: AGENTS.md, Keeping the docs current.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead). Docs alone: the docs tests passed (606).
    - **Fix:** AGENTS.md, Keeping the docs current, after the one deliberate repeat: the story retells the setup by design, defers to each rule's home and prefers a pointer; the story's own paragraph says the same.

- [x] **AGT-82 · The move left pointers that no longer lead to their text** · `.claude/hooks/large_reads.py:472-475`, `tests/unit/test_large_reads.py:360-361`, `ROADMAP.md:4`, `.claude/rules/docs.md:37` · confirmed · found 2026-11-19
  - **Defect.** The web refusal the lead reads: "a fetch may return a whole page, up to 100,000 characters, into your context (AGENTS.md, Delegating to subagents)", a figure now only in the hook's docstring, and the test comment likewise; ROADMAP's "document the result as AGENTS.md describes", now `.claude/rules/docs.md`; docs.md's relative `[ROADMAP.md](ROADMAP.md)`, which resolves to `.claude/rules/ROADMAP.md`. Found by three reviewers.
  - **Scenario.** A refused lead looks in AGENTS.md for the figure; a reader finishing an item looks there for how to document it; the link is dead on GitHub.
  - **Fix.** Cite the hook's docstring, `.claude/rules/docs.md`, and `../../ROADMAP.md`. The story's stale pointers wait for its rewrite. Authority: Step D ("no pointer left to AGENTS.md for what moved").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** the stale-link test failed on the refusal, ROADMAP.md and the test comment; `test_every_relative_link_in_the_docs_leads_to_a_file` failed on docs.md's link; the web-refusal test failed against the old hook. **Fix:** the refusal and comment cite the hook's docstring, which holds the 100,000 figure; ROADMAP cites `.claude/rules/docs.md`; `../../ROADMAP.md`. **Also covered:** no other dead relative link, no other pointer for the figure.
  - Questioned by TST-607 (2026-11-19).

- [x] **AGT-83 · Lists of the project's authorities still name AGENTS.md alone** · `.claude/rules/python.md:76`, `.claude/agents/developer.md:9-10, 62`, `.claude/agents/reviewer.md:118-119`, `.claude/skills/address-review/SKILL.md:111, 142-143` · confirmed · found 2026-11-19
  - **Defect.** "Skip a fix that goes against AGENTS.md, these rules or DECISIONS.md" (in python.md "these rules" now means python.md's own); "AGENTS.md ... is your authority on the stack, the style, the tests and the docs"; "covered: the sibling, AGENTS.md, GUIDE.md or DECISIONS.md settles it"; "Cite the authority: an AGENTS.md section ..."; "a comment, docstring, AGENTS.md, GUIDE.md or README.md sentence the fix made untrue"; "A choice that a rule in AGENTS.md or the code's comments already answer stays in REVIEW.md". Found by two reviewers.
  - **Scenario.** A triage line `changing-tools.md` settles reads as "needs a decision"; a choice `docs.md` answers is proposed for DECISIONS.md, a second home.
  - **Fix.** "AGENTS.md, or the rules and skills it points to" in each list. Authority: Step D ("No rule changes meaning in the move").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_a_doc_naming_agents_md_as_an_authority_names_its_rules_and_skills_too`, failing first on the 6 lists. **Fix:** each names "a rule or skill AGENTS.md points to". **Also covered:** no other list of authorities (`git grep`).
  - Questioned by AGT-90 (2026-11-19).

- [x] **AGT-84 · The docs table still sends deploy and diagnostic facts to a section the move emptied** · `.claude/rules/docs.md:28` · confirmed · found 2026-11-19
  - **Defect.** "How to deploy changes, diagnostics an **agent** needs | **AGENTS.md**, Deploying and diagnosing", while crash diagnosis went to `live-check`, how changes reach the agents to `delegate`, the variables and the guide to `designer-code.md`. Found by two reviewers.
  - **Scenario.** A new fact about a hung quit lands in AGENTS.md beside its home in `live-check`: two homes, and AGENTS.md grows again.
  - **Fix.** "AGENTS.md, Deploying and diagnosing, or the rule or skill it points to for that work". Authority: `.claude/rules/docs.md`, one place.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** the same test's docs.md case, failing first. **Fix:** "or the rule or skill it points to for that work".

- [x] **AGT-85 · Two agent files lost a rule AGENTS.md gave every agent** · `.claude/agents/developer.md:79-80`, `.claude/agents/reviewer.md` · confirmed · found 2026-11-19
  - **Defect.** The crash procedure (Adobe's crash window closed only for a Designer an agent started) now lives only in `live-check`, which the runner preloads and `runner.md` points to; `developer.md` says only "report any crash dump it names", and the developer isn't told to load `live-check` for measurements through the session's Designer tools. "Reviews report a sentence only when it misleads, never for its style alone" is now only in `docs.md`, which a reviewer reading through `git diff` may never load.
  - **Scenario.** A developer's Designer crashes mid-measurement and the crash window stays on the user's screen (DECISIONS.md, no window of an agent's Designer in front of the user's); a reviewer reports a sentence for its style.
  - **Fix.** `developer.md`'s Designer section points to `live-check`, When a Designer crashed or hung, as `runner.md` does; `reviewer.md` carries the style rule, or points to `docs.md` by path. Authority: Step D ("No rule changes meaning in the move").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_the_rules_agents_md_gave_every_agent_reach_the_agents_whose_files_load_none`, failing first on `developer.md`. **Fix:** `developer.md`'s Designer section points to `live-check`, When a Designer crashed or hung; `reviewer.md` carries "A sentence is reported only when it misleads".

- [x] **AGT-86 · `docs.md`'s paths leave out the config files whose comments the docs tests treat as docs** · `.claude/rules/docs.md` (`paths:`), `tests/unit/test_guide.py` (`RULES`) · confirmed · found 2026-11-19
  - **Defect.** `**/*.md` and `**/*.py`, while `_repo_texts` scans `.ini` and `.toml` comments as docs (AGT-66 found a stale pointer in `mypy.ini`).
  - **Scenario.** An edit to `mypy.ini` alone loads neither Writing docs nor Keeping the docs current, which every agent had from AGENTS.md before.
  - **Fix.** Add `**/*.ini` and `**/*.toml` to the rule and to `RULES`. Authority: Step D (paths cover every file whose work needs it).
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** the rules' parse test for docs.md, failing first against `RULES`. **Fix:** `**/*.ini` and `**/*.toml` in the rule; `DOC_SUFFIXES` keeps `RULES` and the docs scan in step.

- [x] **AGT-87 · AGENTS.md keeps parts only the lead needs, now and then, and a hooks paragraph longer than the step allowed** · `AGENTS.md:60-62, 69-72, 133-137` · confirmed · found 2026-11-19
  - **Defect.** The merge (427 bytes, the lead at a branch's end) and how to create PLAN.md (the lead at a branch's start) stay in AGENTS.md; the hooks paragraph has five lines where Step D says "two or three lines". Step D: "AGENTS.md keeps only what every session and every agent needs on every task"; the user: "slim as much as possible".
  - **Scenario.** Every agent, `/simplify`'s four cleanup agents included, pays for text only the lead uses twice per branch.
  - **Fix.** The merge and PLAN.md's creation into the `delegate` skill, The lead's loop; AGENTS.md keeps reading PLAN.md first, a subagent never writing it and a reviewer never reading it; the hooks paragraph to two or three lines. Authority: Step D, items 1 and 6.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** the one-home test failed on PLAN.md's creation and the merge; the limits test on the notes left in AGENTS.md. **Fix:** PLAN.md's writing, keeping and end, and the merge, into the `delegate` skill word for word; AGENTS.md keeps reading PLAN.md first, a subagent never writing it, a reviewer never reading it; the hooks paragraph in three lines. AGENTS.md 13,898 to 12,927 bytes.
  - Questioned by AGT-89, TST-605 (2026-11-19).

- [x] **AGT-88 · A scratch probe no longer gets the rule against waiting a measured time** · `.claude/rules/waits.md` (`paths:`), `.claude/skills/live-check/SKILL.md` (How a probe runs), `.claude/agents/developer.md` · confirmed · found 2026-11-19
  - **Defect.** Every agent had "Wait for callbacks, never for measured times" from AGENTS.md; `waits.md` matches the repository's code only, and a probe or scratch script lives in the scratchpad, which no rule matches; How a probe runs and `developer.md` don't mention the rule.
  - **Scenario.** A runner writes a probe from the lead's outline with a fixed sleep, and records a fact that depends on timing.
  - **Fix.** How a probe runs points to `.claude/rules/waits.md` (the runner preloads `live-check`), and so does `developer.md`'s Designer section. Authority: Step D ("No rule changes meaning in the move").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** the same test as AGT-85, with its `waits.md` and probe assertions. **Fix:** How a probe runs gains How it waits, pointing to `.claude/rules/waits.md`; so does `developer.md`'s Designer section.
  - Questioned by TST-606 (2026-11-19).

- [x] **TST-602 · The guard against "at a cleanup" reads the files the docs table left** · `tests/unit/test_review_lookup.py:395-396` · confirmed · found 2026-11-19
  - **Defect.** `for path in ('AGENTS.md', 'DECISIONS.md'): assert 'at a cleanup' not in ...`, while the table row it guards (249c229) moved to `.claude/rules/docs.md`.
  - **Scenario.** docs.md's row reverts to "at a cleanup" and no test fails.
  - **Fix.** Add `.claude/rules/docs.md` to the tuple. Authority: Step D ("The tests that pin AGENTS.md's wording follow the text").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** in a scratch copy with docs.md's row set to "approved at a cleanup", the new guard failed and the old tuple passed. **Fix:** docs.md in the tuple.

- [x] **TST-603 · The limits test pins a dated measurement's condition, not the docstring's claim about the cap** · `tests/unit/test_large_reads.py:1161` · confirmed · found 2026-11-19
  - **Defect.** It pins "with `bashOutputMaxChars` at {cap:,}", the condition of a measurement dated 2026-11-19, and not "a successful command can't put more than 10,000 characters into the context", the claim about the setting.
  - **Scenario.** The cap changes: the test asks to rewrite the measurement's condition, making the measured result false, while the claim goes stale unseen.
  - **Fix.** Pin the claim's sentence with the cap instead. Authority: AGENTS.md ("A claim in these docs without a test is a guess").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** in a scratch copy with the claim set to 30,000, the new pin failed and the old one passed. **Fix:** the test pins "a successful command can't put more than 10,000 characters into the context".

- [x] **TST-604 · `test_a_part_moved_out_of_agents_md_has_one_home` checks less than its name** · `tests/unit/test_guide.py:509-513` · confirmed · found 2026-11-19
  - **Defect.** It checks each phrase is in the named home and not in AGENTS.md; a copy in a second rule, skill or agent file passes.
  - **Scenario.** A moved rule copied into a second home keeps the test green.
  - **Fix.** Count each phrase across the docs (the story left out, which retells by design) and expect it in its home only, or name the test for what it checks. Generation 1. Authority: Step D ("Each moved rule has one home").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** in a scratch copy with a moved phrase copied into live-check, the new test failed and the old asserts passed. **Fix:** the test counts each phrase across the Markdown docs, the story left out, and expects it in its home only.

- [x] **AGT-89 · AGENTS.md's hooks paragraph lost the notes Step D said it keeps, and README sends readers there for their limits · follows AGT-87, generation 2** · `AGENTS.md:123-125`, `tests/unit/test_large_reads.py:1151-1173`, `README.md:334-337` · confirmed · found 2026-11-19
  - **Defect.** Step D: "AGENTS.md keeps two or three lines: what the hooks refuse and note"; AGT-87's fix dropped the notes (an output of 8,000 characters or more, every 8th reading call) to fit three lines, and a test now asserts their absence; README: "The limits are in AGENTS.md, Delegating to subagents". Found by both reviewers.
  - **Scenario.** A reader looks in AGENTS.md for what counts as a large output or many reads, and finds nothing.
  - **Fix.** The notes back in the paragraph, in as few lines as fit (the lead's choice: what the hooks do over the line count, listed for the user), back in the test's shared tuple, the absence assertion dropped; README points to the docstring for every limit. Authority: Step D, item 1.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** the limits test failed first (the notes absent from AGENTS.md, README's pointer). **Fix:** AGENTS.md's hooks paragraph in four lines with both notes; README: "The limits and the rules are in the docstring of `.claude/hooks/large_reads.py`", pinned by the same test. AGENTS.md 13,088 bytes.

- [x] **AGT-90 · Two more statements of what wins, or what waits for the user, name AGENTS.md alone · follows AGT-83, generation 2** · `.claude/rules/changing-tools.md:13`, `AGENTS.md:99-100` · confirmed · found 2026-11-19
  - **Defect.** "Where it differs from AGENTS.md or this file, they win" (mcp-builder's reference shows `Dict[str, Any]` and "comprehensive docstrings", against `python.md` and `docs.md`); "Where this file waits for the user's word (the full suites, a decision), the lead waits for it before the brief", while the stop list moved to the `delegate` skill. AGT-83's Also covered missed both. Found by both reviewers.
  - **Scenario.** A developer designing a tool follows mcp-builder's docstrings over `docs.md`; a brief on a change beyond the plan omits that the user approved it.
  - **Fix.** "AGENTS.md, a rule or skill AGENTS.md points to, or this file"; "Where this file, or a rule or skill it points to, waits for the user's word"; both in `BESIDE_AGENTS_MD`. Authority: Step D ("No rule changes meaning in the move").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** two new `BESIDE_AGENTS_MD` cases, failing first. **Fix:** `changing-tools.md` and AGENTS.md name "a rule or skill AGENTS.md points to".

- [x] **TST-605 · `MOVED_OUT` has no form for the two parts AGT-87 moved · follows AGT-87, generation 2** · `tests/unit/test_guide.py:363-406` · confirmed · found 2026-11-19
  - **Defect.** PLAN.md's writing and the merge moved to the `delegate` skill without a stale-link pattern; `docs/agent-workflow.md:36` already points to AGENTS.md for how PLAN.md is written, and passes.
  - **Scenario.** A new pointer to AGENTS.md for either part goes unseen.
  - **Fix.** A pattern for each, with a correct sample the merge pattern must leave alone (`runner.md`'s "the final check before the squash merge (AGENTS.md, Running the tests)"); the story's one pointer repointed to the `delegate` skill (the lead's decision, as for its 8 earlier ones). Authority: Step D ("its `MOVED_OUT` patterns gain the moved parts' forms").
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** the stale-link test failed on the story's line 36 exactly; 5 stale and 4 correct samples (`runner.md`'s and the review skill's "squash merge (AGENTS.md, Running the tests)" among the correct). **Fix:** a pattern for PLAN.md's writing and one for the merge, anchored on the section they left; the story's pointer repointed to the `delegate` skill.

- [x] **TST-606 · No test holds the runner's preloaded `live-check`, through which the probes' rules reach it · follows AGT-88, generation 2** · `tests/unit/test_agents.py:161-171`, `.claude/agents/runner.md:7-8` · confirmed · found 2026-11-19
  - **Defect.** The test checks How a probe runs points to `waits.md`; the runner reaches it only because its file preloads `live-check`, which no test asserts.
  - **Scenario.** The preload is dropped; `runner.md` still says the skill is loaded for it, and the runner writes probes without the wait rule or the crash procedure, the test green.
  - **Fix.** Assert `live-check` among the runner's preloaded skills in that test. Authority: AGENTS.md, Review your own work.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** in a scratch copy without the runner's preload, the test failed (`'- live-check' in []`). **Fix:** the preload asserted.

- [x] **TST-607 · The relative-link test passes links that are dead on GitHub · follows AGT-82, generation 2** · `tests/unit/test_guide.py:502-511` · confirmed · found 2026-11-19
  - **Defect.** `Path(ROOT, os.path.dirname(name), target).exists()` on a case-insensitive volume passes `readme.md`, and passes ignored or outside-the-repository targets, while its comment says "as on GitHub".
  - **Scenario.** A wrong-case link stays green here and 404s on GitHub. None exists today.
  - **Fix.** Generation 2: require the normalized target among `_repo_files()` or their folders, or narrow the comment to what it checks. Authority: the test's own comment.
  - **Resolution: done** (2026-11-19: the developer's report, assessed and written by the lead).
    - **Test:** `test_a_link_leads_to_a_file_only_as_on_github`, 6 samples; the old check passed the three dead ones (wrong case, the ignored venv, outside the repository). **Fix:** a link must resolve, case-exact, to a file git lists, or one of its folders.

- [x] **AGT-91 · The Bash check follows a `cd` zsh may not run, and resolves `..` after a symlink physically** · `.claude/hooks/large_reads.py:787-789` (`_printed`), `:801-826` (`_commands`), `:853-856` (`_named`) · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** `_commands` drops the separators, so `_printed` follows a `cd` after `||` (or after `&&` when a later `;` runs the next command anyway) as if it ran. `_named` joins `link/..`, and the file is then opened physically, while zsh's `cd` reads `..` logically (CHASE_LINKS and CHASE_DOTS off). The docstring's `cd` bullet says the folder moves, without conditions.
  - **Scenario.** `true || cd sub; cat big.py`: the hook sizes `sub/big.py` (5 KB) and lets it through, while zsh prints `./big.py` (30 KB); with `; false` after it, the failed output isn't capped. `cd link/.. && cat x` is sized as the target's `../x`. Measured, not a defect: Read resolves `..` lexically (`Read('<folder>/link/../x')` returned the small file, and the hook let it through).
  - **Fix.** End the sizing at a `cd` that may not run (after `||`, or after `&&` with a later separator other than `&&`), as MOVES does; normalise a followed folder lexically (`os.path.normpath`); a test for each. Or state both limits in the docstring. Authority: the docstring's `cd` bullet; AGENTS.md, Delegating to subagents; Step A, decision 2 (a branch's own leftovers fixed in the branch).
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_a_command_is_sized_by_the_lines_it_prints[cat big.py || cd sub; cat big.py]` (350 lines, not 300), five may-not-run cases in `test_a_command_it_cant_size_passes` (each refused before the fix) and `test_a_cd_reads_dot_dot_after_a_symlink_as_zsh_does` (no refusal before). **Cause:** `_commands` dropped the separators, so a `cd` was followed whether or not it ran; a followed folder was joined, then opened physically, while zsh reads `..` logically. **Fix:** `_commands` keeps each command's separator; `_ran_before` follows a `cd` only when it opens the line, follows `;`, or follows `&&` with only `&&` after it, and otherwise the sizing ends as for MOVES; `_folder` reads `..` as zsh 5.9 does (measured 2026-11-20, the table in the docstring), a `cd` zsh refuses ending the sizing. **Also covered:** `chdir`; a printer's own path stays physical, as `cat` opens it (measured); `read_refusal` unchanged, since Read resolves `..` lexically. AGT-95 follows.
  - Note (2026-11-20): that held for Read, whose path Claude Code hands the hook already resolved, but not for `read_file`: AGT-96.
  - Questioned by AGT-95, AGT-96, AGT-98, TST-616 (2026-11-20).

- [x] **TST-608 · The hook tests' scaffolding sits in the shared `conftest.py` · follows TST-564, generation 2** · `tests/unit/conftest.py:178-243` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** `load_script`, `HookInput`, `HookResponse`, `HookCall` and `run_hook` are used only by `test_large_reads.py` (`git grep`). TST-564 put them there while `test_read_only_bash.py` shared them, and that test is gone.
  - **Scenario.** Every unit test loads 69 lines that one file needs, while that file's other helpers (`counted_reads.py`, `notebook_files.py`) are modules beside it.
  - **Fix.** Move them to a module beside the test (`tests/unit/hook_calls.py`) and import them from there; the docstrings saying "the hooks of `.claude/hooks`" name the one hook. A move: the test file's tests pass before and after. Authority: `.claude/rules/python.md`, Keep each file to its main logic.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** a move: `test_large_reads.py`'s 245 tests passed before and after. **Fix:** the five names in `tests/unit/hook_calls.py`, imported from there; their docstrings name `large_reads.py`.

- [x] **AGT-92 · `address-review` step 2 still has the developer check a false finding off** · `.claude/skills/address-review/SKILL.md:69` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** "resolve the entry as *not a bug* or *not reproducible* and check it", while step 7 has the lead check the box, and `developer.md` says the developer never writes REVIEW.md.
  - **Scenario.** A developer whose test passes before any fix follows step 2 and ticks the entry in REVIEW.md.
  - **Fix.** "report the entry's resolution as *not a bug* or *not reproducible* (step 7)". Authority: Step A, decision 3 (only the lead writes REVIEW.md); `developer.md`.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Fix:** step 2 reads "report the entry's resolution as *not a bug* or *not reproducible* (step 7)".
  - Questioned by TST-615 (2026-11-20).

- [x] **AGT-93 · The sentence after the won't-fix criteria says more than the user's words** · `.claude/skills/address-review/SKILL.md:147` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** "When a criterion fails, or the lead is unsure, the finding is fixed". Criteria 1 and 3 already send a false finding to *not a bug* and work for later to ROADMAP.md ("instead"), and the user's rule is "when unsure whether (2) holds, have it fixed".
  - **Scenario.** A proposal whose test shows the finding false is "fixed", against step 2; a proposal failing criterion 3 is fixed by one lead and proposed for ROADMAP.md by another.
  - **Fix.** "When (2) fails, or the lead is unsure whether it holds, the finding is fixed". Authority: the user, 2026-11-20.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** pinned in `test_the_users_rules_of_2026_11_20_keep_their_wording`, failing first. **Fix:** "When **Fixing it is never worth it** fails, or the lead is unsure whether it holds, the finding is fixed" (the criterion named by its label).
  - Questioned by TST-628 (2026-11-20).

- [x] **TST-609 · Local names hide the docs helpers Step E made public** · `tests/unit/test_agents.py:196`, `:201`; `tests/unit/test_guide.py:265`, `:315`, `:333`, `:336`, `:1053`; `tests/unit/test_large_reads.py:874` · confirmed · found 2026-11-20 by two reviewers (Opus, Sonnet)
  - **Defect.** `skill = item[2:]`, `agent = tmp_path / 'a.md'`, the parameter `rule: str` (four tests), a `(_, skill)` comprehension and `read = _payload(...)` hide `skill`, `agent`, `rule` and `read`, imported from `docs_text`; PyCharm reports them. Step E renamed the other clashing locals.
  - **Scenario.** A later edit calls `agent(...)` or `read(...)` in one of these tests and gets a `TypeError` from a `Path` or a dict.
  - **Fix.** Rename them (`skill_name`, `path`, `rule_name`, `call`). Authority: Step E (d); `.claude/rules/python.md` (`get_file_problems` after an edit).
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** renames: the touched tests passed before and after. **Fix:** `skill_name`, `path`, `rule_name`, `label` and `call`. **Also covered:** `scripting` shadowing an import in `test_guide.py` predates the branch and isn't a docs helper, left.

- [x] **TST-610 · No test pins the user's 2026-11-20 rules in the skills** · `.claude/skills/delegate/SKILL.md:30-31`, `:47`, `:52`, `:116`; `.claude/skills/project-code-review/SKILL.md:177-178`, `:182`; `.claude/skills/address-review/SKILL.md:134-150` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** "PLAN.md, Waiting for the user" (both skills), the won't fix in the stop list, the criteria, "the lead may propose one itself", "at once", the recap and the measured preloaded-skill sentence have no test; the same day's false-finding rule has `test_a_false_finding_gets_no_decisions_entry`.
  - **Scenario.** A later edit drops the phrase the user asked for in both skills, or the criteria drift between files, and no test fails.
  - **Fix.** `in` checks on the flattened skills, beside the existing pins, of the user's wording only. Authority: AGENTS.md ("A claim in these docs without a test is a guess").
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_the_users_rules_of_2026_11_20_keep_their_wording`, failing first on the new phrases: PLAN.md, Waiting for the user; the won't fix in the stop list; the won't-fix rules; the recap; the reviewer's model and the Opus rounds (the user, 2026-11-20). Not pinned: the measured preloaded-skill sentence, a measurement rather than the user's wording.

- [x] **AGT-94 · "A branch's own leftovers fixed in the branch" is in no skill** · `.claude/skills/delegate/SKILL.md:36-41`; `.claude/skills/address-review/SKILL.md:186`; `.claude/skills/project-code-review/SKILL.md:183` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** Step A's decision 2 lists it among what the lead decides alone. The `delegate` skill says only "The lead decides alone all but what is the user's", and two skills send every follow-up to a ROADMAP.md proposal.
  - **Scenario.** A small gap in the branch's own code is listed at convergence as a ROADMAP proposal rather than fixed.
  - **Fix.** One clause in the `delegate` skill's loop paragraph ("a leftover in the branch's own code is fixed in the branch"), pointed to from `project-code-review` step 8 and `address-review`, After a group. Authority: Step A, decision 2.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_a_leftover_in_the_branchs_own_code_is_fixed_in_the_branch`, failing first. **Fix:** the clause in the `delegate` skill's loop paragraph; `project-code-review` step 8 and `address-review`, After a group, point to it.

- [x] **TST-611 · Lowercase stale pointers that `MOVED_PARTS` caught pass both tests now** · `tests/unit/test_guide.py:363-400`, `:525-527`; `tests/unit/doc_pointers.py:24` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** The narrow `MOVED_OUT` patterns match only their sample sentences; `PART` follows only a capital or a quote, and the finder skips a lowercase name. The comments at 363-365 and 525-527 say the prose forms are `MOVED_OUT`'s.
  - **Scenario.** `(AGENTS.md, callbacks first)`, `(AGENTS.md, Working on this project: wait for callbacks)` and `(AGENTS.md, Working on this project: the `mcp-builder` paragraph)` pass both tests; the removed pattern caught all three. None is in the tree.
  - **Fix.** One generic pattern for the three lowercase parts (callbacks, navigating and checking, the `mcp-builder` paragraph), with those samples; or narrow both comments to the sample forms. Authority: Step E ("The MOVED_OUT patterns the general test can't see stay"); Step D.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** the three lowercase samples failed first. **Fix:** one `MOVED_OUT` pattern built from `doc_pointers.py`'s own grammar (`AFTER_FILE`, `TO_PART`) in place of four narrow ones; both comments narrowed to the three parts.

- [x] **TST-612 · ROADMAP item 110 gives a limit and a size that are no longer true** · `ROADMAP.md:24` · confirmed · found 2026-11-20 by two reviewers (Opus, Sonnet)
  - **Defect.** "near the 40,000-byte limit `test_guide.py` sets" and "Reached 13.9 KB"; the test now sets a 15,000-byte budget (`AGENTS_MD_BUDGET`), and AGENTS.md is 13,145 bytes.
  - **Scenario.** A reader takes the budget to be 40,000 bytes.
  - **Fix.** The budget now (15,000 bytes) and the size reached (13.1 KB), or drop both figures. Authority: `.claude/rules/docs.md` (fix notes that turn out wrong); Step D (item 110 updated to the size reached).
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Fix:** item 110 says the 40,000-byte limit was the test's then, and that AGENTS.md was 13.1 KB on 2026-11-20, within the 15,000-byte budget.

- [x] **TST-613 · ROADMAP item 111's row has 4 cells in a 6-column table** · `ROADMAP.md:180` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** Why and What's needed share one cell, and Effort is missing; every other row has 6 or 7 cells. It was added with the sixth review's record, and no review read it after.
  - **Scenario.** GitHub shows the steps under Why and leaves What's needed and Effort empty.
  - **Fix.** Split the cell at "Check it in a session on Windows" and add an Effort. Authority: ROADMAP.md's introduction (every item has an Effort).
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Fix:** the cell split at "Check it in a session on Windows", Effort S. **Also covered:** every other ROADMAP row counted against its header's columns.
  - Questioned by TST-615 (2026-11-20).

- [x] **TST-614 · The simulation's `+` exception has no test, and two docstrings leave it out** · `tests/unit/windows_simulation.py:1-6`, `:51-53`; `tests/unit/test_windows_simulation.py:1-4`; `.claude/rules/unit-tests.md:14-16` · confirmed · found 2026-11-20 by two reviewers (Opus, Sonnet)
  - **Defect.** The code leaves a `+` mode alone (`not chars & set('b+')`), and the rule says so, but no case of `WRITES` uses one. Both module docstrings say every text-mode write without a `newline` gets `\r\n`.
  - **Scenario.** `+` dropped from `set('b+')`: every case still passes. Someone writing with `'w+'` trusts the docstrings, and the simulated run writes `\n` where Windows writes `\r\n`.
  - **Fix.** Generation 1: a `w+` case expecting `b'a\n'` (or drop the rule's sentence), and both docstrings narrowed to `w`, `a` or `x` without `b` or `+`. Authority: AGENTS.md ("A claim in these docs without a test is a guess").
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** a `w+` case in `WRITES` expecting `b'a\n'`; with `+` dropped from `set('b+')` it failed (a mutation, put back). **Fix:** both module docstrings narrowed to `w`, `a` or `x` without `b` or `+`.

- [x] **HLP-207 · The answer of a removed DECISIONS.md entry lives nowhere: `_delete_function`'s unguarded inheritance calls** · `mcp_server/designer_helpers/graph_inputs.py:252-259` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** The cleanup removed "`_delete_function`'s inheritance calls have no guard" (neither call raised in any measured case; a guard would be untested code). The docstring says only that the inheritance is put back, and REVIEW.md no longer holds the finding.
  - **Scenario.** A later review sees two unguarded Designer calls and raises them again, and nothing in the repository answers it.
  - **Fix.** One clause in the docstring: neither call raised in any measured case (`function_states.py`), so it has no guard. Authority: the user, 2026-11-20 (a removed entry's fact, if still needed, lives elsewhere).
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** pinned in `test_what_a_helper_cites_for_a_measurement_states_it`, failing first. **Fix:** the docstring says neither inheritance call raised in the measured cases, so neither has a guard.

- [x] **AGT-95 · A Bash refusal sends Read to another file when a printed path holds `..` after a symlink · follows AGT-91, generation 2** · `.claude/hooks/large_reads.py` (the paths a Bash refusal names) · measured · found 2026-11-20 by the developer (Opus)
  - **Defect.** The refusal names a printed file by its joined path. `cat` opens that path physically (measured by the developer), while Read resolves `..` lexically (measured by the lead, AGT-91), so the refusal's way on, reading the file with Read, reads another file. `_printed`'s docstring says the refusal names each file by a path Read finds from any folder.
  - **Scenario.** `cat link/../x` of a 30 KB physical file is refused; Read of the named `<folder>/link/../x` returns the small lexical `x`.
  - **Fix.** Name each refused file by its real path (`os.path.realpath`), which Read finds as `cat` did; a test with the symlink case. Authority: `_printed`'s docstring. Found by the developer while fixing AGT-91.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_a_refused_file_is_named_by_the_real_path_cat_opens`: `cat link/../sub/big.py` prints the 300-line `elsewhere/sub/big.py`, and the refusal named `<project>/link/../sub/big.py`, which Read reads as the 50-line `project/sub/big.py`; failing first. **Cause:** `_printed` returned the joined path, which the OS resolves physically for `cat` and Read lexically. **Fix:** `_printed` measures and names each printed file by `os.path.realpath`; `bash_refusal`'s dedup and notebook check use it too. **Also covered:** `_folder`'s physical fallback already gives a real path; `read_file`'s refusal is AGT-96.

- [x] **AGT-96 · The hook sizes another file than `read_file` returns for a path with `..` after a symlink · follows AGT-91, generation 2** · `.claude/hooks/large_reads.py` (`_path`, `read_refusal`) · measured · found 2026-11-20 by the developer (Opus)
  - **Defect.** `_path` joins the path and the hook opens it physically, while PyCharm's `read_file` resolves `..` lexically (measured by the developer: `read_file` of `<project>/link/../x` returned the lexical `x`, `cat` the physical one). For Read, Claude Code hands the hook a path already resolved (AGT-91's measurement: the physical file was the big one, and the hook let the read through).
  - **Scenario.** Measured by the lead: with the lexical `x` 14 bytes and the physical one 32 KB, the lead's `read_file` of `zz_dots_probe/project/link/../x` was refused as "44 KB and 1801 lines". With the sizes the other way round, a big read would pass.
  - **Fix.** Normalise the joined path lexically in `_path` (`os.path.normpath`), as the tools read it, for `read_file` and Read alike; a test with the symlink case for each. Authority: AGENTS.md, Delegating to subagents (a read that returns over 20 KB is refused). Found by the developer while fixing AGT-95.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_a_dot_dot_after_a_symlink_is_read_lexically[Read]` and `[mcp__pycharm__read_file]`: a read of `project/link/../big.py` (the 300-line file beside the link) refused, one of `project/link/../sub/big.py` (50 lines) passed; both failed first, the hook sizing the file beside the link's target. Measured again by the lead after the fix: its own `read_file` of the probe's `link/../x` returned the 14-byte file, unrefused. **Cause:** `_path` joined the path, and the hook opened it physically, while Read and `read_file` read `..` lexically. **Fix:** `_path` normalises the joined path with `os.path.normpath`; the docstring says both tools read `..` lexically. **Also covered:** the Bash side stays physical on purpose (`cat` opens it so; AGT-95 names it by its real path; `_folder` follows zsh, AGT-91); `_path`'s two callers, both in `read_refusal`.

- [x] **AGT-97 · "Look converged" now names both the end of the Sonnet rounds and the end of the reviews** · `.claude/skills/project-code-review/SKILL.md:171-183`; `.claude/skills/delegate/SKILL.md:40`, `:87`; `project-code-review/SKILL.md:185-186`; `.claude/skills/address-review/SKILL.md:189`; `AGENTS.md:82`; `DECISIONS.md:27` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** Step 7 uses "looks converged" for the end of the Sonnet rounds, after which the Opus rounds run; the `delegate` skill's loop ("until the reviews look converged (the `project-code-review` skill, step 7)"), step 8, `address-review`, AGENTS.md and DECISIONS.md use the same words for the moment the user is told.
  - **Scenario.** After a compaction, the lead reloads the `delegate` skill and reads that the loop runs until the reviews look converged; a Sonnet round with a few Low findings looks converged, and the lead reports to the user without the Opus rounds.
  - **Fix.** Give the end of the Sonnet rounds its own words in step 7 (for example "the Sonnet rounds are done"), keep "converged" for the end, and have the `delegate` skill's loop name both stages. The 2026-11-19 phrase pinned by `test_the_wording_of_the_rules_agreed_on` stays as the rule for when a review counts; the pins follow the new wording. Also: the first Opus round reviews the entire branch diff against main (the user, 2026-11-20). Authority: the user, 2026-11-20 (items 11 to 13).
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** the pins in `test_the_users_rules_of_2026_11_20_keep_their_wording`, failing first on the two stages' wording; the Sonnet bullet holds no "converge"; the user's quote on the first Opus round. **Cause:** step 7 used "looks converged" for the end of the Sonnet rounds, every other file for the moment the user is told. **Fix:** step 7 in two stages, "the Sonnet rounds are done", then the Opus rounds, the first on "the entire branch diff against main" (the user, 2026-11-20), until the reviews converge; the `delegate` loop names both. **Also covered:** the other uses of "look converged" (the merge paragraph, step 8, After a group, AGENTS.md, DECISIONS.md) mean the end, unchanged; the 2026-11-19 pins pass unchanged.
  - Questioned by TST-619, AGT-100 (2026-11-20).

- [x] **AGT-98 · The hook's `cd` bullet says zsh reads `..` logically without "with zsh's default options" · follows AGT-91, generation 2** · `.claude/hooks/large_reads.py:95` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** The measurements (zsh 5.9) and `_folder` assume `CHASE_DOTS` and `CHASE_LINKS` unset; the docstring states the logical reading without that condition.
  - **Scenario.** A profile that sets either option makes `cd link/..` go the physical way, and the hook sizes another folder than the shell moves to.
  - **Fix.** Generation 2: add the condition to the bullet ("with zsh's default options, as measured"); no new check. Authority: AGENTS.md ("A claim in these docs without a test is a guess").
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Fix:** generation 2, the condition only: "With zsh's default options (`CHASE_DOTS` and `CHASE_LINKS` unset), as measured"; Claude Code's shell sets neither (`setopt`, measured 2026-11-20).

- [x] **TST-615 · AGT-92's wording and ROADMAP's table shape have no test · follows AGT-92 and TST-613, generation 2** · `.claude/skills/address-review/SKILL.md:69`; `ROADMAP.md` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** Step 2's "report the entry's resolution as *not a bug* or *not reproducible* (step 7)" has no pin, and no test counts a ROADMAP row's cells against its table's header.
  - **Scenario.** A later edit puts back "and check it", or adds a 4-cell row like item 111's, and every test passes.
  - **Fix.** An `in` check of step 2's sentence and the old one's absence; a docs test that every `| [` row of each ROADMAP table has as many cells as its header. Authority: AGENTS.md ("Every new feature or fix comes with a test").
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_a_false_finding_is_reported_for_the_lead_to_check` (failing on the skill as of `0a887d4`); `test_every_row_of_a_docs_table_has_as_many_cells_as_its_header`, widened by `/simplify` to every table of every doc (20 tables in 8 docs), failing on ROADMAP.md as of `0a887d4` ("4 of 6 cells: | [ ] | 111 |").

- [x] **TST-616 · A test row for a leading `cd` with a later `||` passes whether the `cd` is followed or the sizing ends · follows AGT-91, generation 2** · `tests/unit/test_large_reads.py:613` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** `('cd sub || true; cat big.py', None)`: `sub`'s `big.py` is small, so `None` comes out when the `cd` is followed, when the sizing wrongly ends, and on the code before AGT-91.
  - **Scenario.** `_ran_before` changed to `joins[0] in ('', ';') and '||' not in joins` ends the sizing after any leading `cd` with a later `||`, and a big print passes; no test fails.
  - **Fix.** `('cd sub || true; cat deep.py', '300 lines')`: `deep.py` is only in `sub`, so only a followed `cd` gives 300 lines. Authority: AGENTS.md, Start with the tests.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** the row `('cd sub || true; cat deep.py', '300 lines')`; with the entry's mutation of `_ran_before` it fails, where the old row passed. **Fix:** the row.

- [x] **TST-618 · The story states five things the setup's files don't** · `docs/agent-workflow.md:17`, `:40-41`, `:60-61`, `:85`, `:147-150`, `:161-162` · confirmed · found 2026-11-20 by two reviewers (Sonnet)
  - **Defect.** "Sonnet found 7, 3 of them alone" (REVIEW.md's table: 4; the story's figures don't add up to 12); step 10 puts DECISIONS.md and ROADMAP.md after the final check (the `delegate` skill: before it); the cast gives the analyst "every web search and web fetch" (the developer fetches too; `delegate`: "the lead's web fetches"); "Subagents' calls pass" next to the output cap (AGENTS.md: the cap applies in the subagents too); the lead "reruns the step's tests" (no setup file says so); a mid-run SendMessage "delivered at its next tool round" (no setup file says so).
  - **Scenario.** A copier follows the story where it differs from the setup.
  - **Fix.** "4 of them alone"; DECISIONS.md and ROADMAP.md before the final check; "every web search and the lead's web fetches"; "the hooks let subagents' calls through; the cap applies to them too"; drop the rerun clause; for SendMessage, point to the tool's own description or drop it. Authority: `.claude/rules/docs.md` (the story defers to each rule's home).
  - **Resolution: done** (2026-11-20, by the lead, who writes the story).
    - **Fix:** "4 of them alone"; DECISIONS.md and ROADMAP.md moved to step 8, before the final check; "every web search, and the lead's web fetches"; the cap "in the subagents too", the hooks letting their calls through; the rerun clause and the SendMessage delivery clause dropped. **Test:** the docs tests.
  - Questioned by TST-632 (2026-11-20).

- [x] **TST-619 · The story says the step's rounds "converge" · follows AGT-97, generation 2** · `docs/agent-workflow.md:53-54` · confirmed · found 2026-11-20 by two reviewers (Sonnet)
  - **Defect.** "repeats steps 4 to 6 until the reviews converge. The loop then goes on with the next step": the skills keep "converge" for the end of the whole-branch Opus rounds, a step's reviews being "done".
  - **Scenario.** A lead following the story reports convergence after each step, or skips the Opus rounds: AGT-97's scenario.
  - **Fix.** "until the step's reviews are done"; "converge" only for convergence. Authority: `project-code-review` step 7.
  - **Resolution: done** (2026-11-20, by the lead, who writes the story).
    - **Fix:** "until the step's reviews are done", and after the last step "Opus rounds review the entire branch until the reviews converge". **Test:** the docs tests.

- [x] **TST-620 · The story's copy table leaves out modules the copied tests import** · `docs/agent-workflow.md:212` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** `test_large_reads.py` imports `counted_reads` and `notebook_files`, and the tests and `docs_text.py` import `ROOT` from `tests/unit/conftest.py`; the row names none of them.
  - **Scenario.** A copier running `test_large_reads.py` gets an ImportError.
  - **Fix.** Add `counted_reads.py` and `notebook_files.py`, and say `conftest.py` must provide `ROOT`. Authority: the row's own claim.
  - **Resolution: done** (2026-11-20, by the lead, who writes the story).
    - **Fix:** `counted_reads.py` and `notebook_files.py` added to the row, with `conftest.py`'s `ROOT`. **Test:** the docs tests (every link of the row resolves).
  - Questioned by TST-625 (2026-11-20).

- [x] **TST-621 · REVIEW.md's "Found by." paragraph sat between the Confidence label and its bullets** · `REVIEW.md:16-26` · confirmed · found 2026-11-20 by two reviewers (Sonnet)
  - **Defect.** The lead inserted the paragraph after `**Confidence.**` and its blank line; the template has it after the Measured bullet. The label was left empty, and the bullets read as Found by's.
  - **Fix.** Move it after the Measured bullet.
  - **Resolution: done** (2026-11-20, by the lead, who writes REVIEW.md). **Fix:** the paragraph moved after the Measured bullet, as in the template. **Test:** TST-623's check of the header against the template.
  - Note (2026-11-20): the first move put the paragraph back after the label's blank line, the same place; TST-623's header check caught it, and the lead moved it after the Measured bullet.

- [x] **TST-622 · The table by model's "Real findings" counts finders its rows leave out** · `.claude/skills/project-code-review/TEMPLATE.md:62-63` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** "Real findings: the real findings they found, counted from each finding's `found ... by <who> (<model>)`", with rows per reviewing model; AGT-95 and AGT-96, `by the developer (Opus)`, are in no row, so the 13th round's Opus row would be 10 by that rule, not 8. The format of two reviewers of one model isn't given.
  - **Scenario.** The lead counts by the rule and the table's rows disagree with the title lines.
  - **Fix.** Say the table counts the round's reviewers' findings, and that another finder (the developer, the runner, the lead) is recorded on the title line only; "by two reviewers (Sonnet)" for one model. No new check. Authority: the user's items 16 to 18.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Fix:** the template counts the round's reviewers on the row's model; a finding another agent found is recorded on its title line only, in no row; `by two reviewers (Sonnet)` for one model. REVIEW.md's copies brought to the template's text by the lead. No new check, as the entry says.

- [x] **TST-623 · No test checks the table's Total row, REVIEW.md's header against the template, or the finder on new entries** · `tests/unit/test_review_lookup.py:415-466` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** The new tests pin sentences and the header row; the status table has `_status_problems` for the same kind of slip, but the Total row's sums, the template's header paragraphs in REVIEW.md, and the `by <who> (<model>)` on an entry found from 2026-11-20 on have no check.
  - **Scenario.** The lead adds a round's rows and forgets the Total, or misplaces a header paragraph (TST-621), or writes an entry without its finder; every test passes.
  - **Fix.** A test summing the table's columns against the Total row; a test that the template's **Found by.** paragraph and the Reviews by model explanation are in REVIEW.md, in the template's order; a test that every entry found from 2026-11-20 on ends with `by ... (...)`. Authority: AGENTS.md ("A claim in these docs without a test is a guess").
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_the_table_by_models_total_sums_its_rows` (failing on a copy with the Total's tokens one off) and `test_the_table_by_models_check_catches_a_slip` (four slips); `test_review_md_has_the_templates_new_paragraphs_where_the_template_puts_them` (failing on a copy with the paragraph moved; it also caught the lead's TST-621 slip on the file); `test_every_entry_found_from_2026_11_20_names_who_found_it` (failing on a copy with one finder taken off).

- [x] **AGT-99 · The whole-branch diff command keeps REVIEW.md in, and the claim's version for a whole-branch round is unsaid** · `.claude/skills/project-code-review/SKILL.md:64-76`, step 3 · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** Scope's `git diff main...<branch> -- . ':(exclude)PLAN.md'` is now the convergence round's command, and REVIEW.md is a quarter of its lines, while the reviewers read REVIEW.md as the record, not as a change (the 13th and 15th rounds left it out by hand). Step 3 quotes "each step's section of PLAN.md that the user approved", and PLAN.md changes after approval.
  - **Scenario.** An Opus round of the entire branch spends its reading on REVIEW.md's diff; a lead quotes a step as PLAN.md holds it now, with the lead's own notes in it.
  - **Fix.** `':(exclude)REVIEW.md'` in the whole-branch command, and Scope saying REVIEW.md is read as the record; step 3: each step's text as the user approved it, taken from the first commit that holds it. Authority: the review skill's own Scope; `.claude/agents/reviewer.md` (Review blind).
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** the diff-command test (every command excludes PLAN.md, the two whole-branch ones REVIEW.md too) and `test_a_step_is_quoted_as_the_user_approved_it`, both failing first. **Fix:** Scope's whole-branch commands exclude REVIEW.md, read as the record; a round's command keeps it, for the resolutions step 2 rechecks; step 3 quotes each step's text from the first commit of PLAN.md that holds it.
  - Questioned by AGT-106 (2026-11-20).

- [x] **TST-624 · The list of what a review adds, and a test's cleaned-up file, lack the table by model** · `.claude/skills/project-code-review/SKILL.md:81-83`; `tests/unit/test_review_lookup.py:755-761` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** "REVIEW.md: append or create" lists the log entry, the status table and Last used, not the table's rows (only step 6 has them); `_cleaned_up` builds a file going from the status table straight to the review log, while the cleanup now leaves the Reviews by model section, empty.
  - **Scenario.** A lead following the first list forgets the rows; the cleanup tests run on a shape the skill no longer produces.
  - **Fix.** Add the rows to the list; `_cleaned_up` keeps the section, from the template. Authority: step 6; `cleanup-review` step 6.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** the append-list pin and the cleaned-up file test, both failing first. **Fix:** the list names the table's rows (step 6); `_cleaned_up` takes the template's Status and Reviews by model sections, the latter with no rows.

- [x] **TST-625 · The copy table's test row omits that two copied tests import this project's server · follows TST-620, generation 2** · `docs/agent-workflow.md:212` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** `test_guide.py` imports `test_server`, `server_tools` and conftest's `fake_bridge`, `patch_server` and `server`; `test_agents.py`'s `_designer_tools` imports `server_tools.core`. The row says to keep them as the setup's tests.
  - **Scenario.** A copier keeps `test_guide.py` and gets an ImportError at collection.
  - **Fix.** Say those parts import this project's server and fixtures, to be rewritten. Authority: TST-620's claim; `.claude/rules/docs.md`.
  - **Resolution: done** (2026-11-20, by the lead, who writes the story).
    - **Fix:** the row says `test_guide.py`, and `_designer_tools` in `test_agents.py`, import this project's server and its test fixtures, so those parts are rewritten. **Test:** the docs tests.

- [x] **TST-626 · The story says to start DECISIONS.md empty while the copied files cite its entries · follows AGT-73, generation 2** · `docs/agent-workflow.md:211` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** "Start them empty, keeping their introductions' formats", where AGT-73's fix had the row carry over the introduction and the setup's three entries; the agent files, the `delegate` skill, AGENTS.md and `test_agents.py` cite "No agent has a write guard" and "Project rules". Step C's rewrite brought it back.
  - **Scenario.** In the new repository the readers' rules point at entries that don't exist, and reviews raise the write guard again.
  - **Fix.** Carry over the introduction and the setup's entries, each approved anew by the other project's user. Authority: AGT-73.
  - **Resolution: done** (2026-11-20, by the lead, who writes the story).
    - **Fix:** AGT-73's wording back: DECISIONS.md's introduction and the setup's entries the copied files cite, each approved anew; ROADMAP.md started empty. **Test:** the docs tests.

- [x] **TST-627 · The story's per-agent cost ranges live in no file, and REVIEW.md's table contradicts one** · `docs/agent-workflow.md:192-193` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** The developer, reviewer, analyst and runner ranges are in no repository file; the fifteenth round's reviewers averaged about 140,000 tokens and took 5 minutes, under the reviewer range.
  - **Scenario.** A copier plans around ranges the repository's own table contradicts.
  - **Fix.** Drop the ranges; point to the completion notices and the table by model. Authority: `.claude/rules/docs.md` (a pointer over a copy of figures); AGT-76.
  - **Resolution: done** (2026-11-20, by the lead, who writes the story).
    - **Fix:** the ranges dropped; the story says each agent's completion notice gives its tokens and duration, and the table by model adds them up per round until a cleanup; the whole-branch figure kept. **Test:** the docs tests.

- [x] **TST-628 · The story's won't-fix sentence says a finding is fixed when any criterion fails · follows AGT-93, generation 2** · `docs/agent-workflow.md:111` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** "When one fails, or the lead is unsure that fixing is never worth it, the finding is fixed", against `address-review` step 7 after AGT-93: only the second criterion's failing, or doubt about it, has it fixed.
  - **Scenario.** A copier "fixes" work for later, which belongs in ROADMAP.md.
  - **Fix.** As the skill says. Authority: `address-review` step 7.
  - **Resolution: done** (2026-11-20, by the lead, who writes the story).
    - **Fix:** "When fixing could be worth it, or the lead is unsure, the finding is fixed; a false one is answered 'not a bug', and work for later goes to ROADMAP.md." **Test:** the docs tests.

- [x] **TST-630 · The story's rewrite brought back five fixed misstatements, and two hook details are missing · follows AGT-74, AGT-75, AGT-77, AGT-78, AGT-59, generation 2** · `docs/agent-workflow.md:39`, `:91-93`, `:99`, `:101`, `:123`, `:149-154`, `:176-177`, `:183-185`, `:202-205`, `:208` · confirmed · found 2026-11-20 by two reviewers (Opus)
  - **Defect.** Against the fixed text at `279087c`: `/simplify` without "unless the change is docs alone", the timer without telling the user, restarting and TaskStop, no cost announced before a long unit, no Not verified, the edited agent without "a change of tools, model or effort takes a new agent" (AGT-78); "how to build a step" given to the lead, not the developer (AGT-74); DECISIONS.md "written by the lead" though agents keep names and paths, and the chain lesson without "Low or Low-medium" and "generation 3 or later" (AGT-77); copy cells understating the project's own parts (AGT-75); "the user's own work or files outside the repository" (AGT-59). Also: the output cap applies only to a successful command's output (AGENTS.md); the hook's copy row omits the IDE's tool names (`READING_TOOLS`, the matchers) and the zsh and BSD tools it was measured with.
  - **Scenario.** A copier follows the story where it says less or other than the setup.
  - **Fix.** Restore the fixed wording, or point to each rule's home (`.claude/rules/docs.md`); "a successful command's output"; the hook row adds the tool names and re-measuring the shell. Authority: those findings; Step C.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Fix:** the fixed wordings back (`/simplify` unless docs alone; Not verified; how a step is built is the developer's; "the user's own files outside the repository"; the cost announced before a long unit; DECISIONS.md's names and paths kept by the agent whose change moves them; the timer's whole rule; a change of tools, model, preloaded skills or effort takes a new agent; the chain rule's conditions; the copy cells naming this project's parts); "a successful command's output"; the hook row names `READING_TOOLS` and the matchers, and says to measure zsh and the BSD tools again. **Test:** the docs tests.

- [x] **AGT-100 · The Opus stage has no branch for a few findings with one above Low, and the model exception names only the whole-branch rounds · follows AGT-97, generation 2** · `.claude/skills/project-code-review/SKILL.md:186-190`; `.claude/skills/delegate/SKILL.md:24-26`, `:41`; `docs/agent-workflow.md:75` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** The stage branches on "more than a few" and converges on "only a few Low ones, or none"; a whole-branch round finding 2 Low-medium is in neither. The `delegate` skill passes `model: opus` for "the Opus rounds on the entire branch", not the Opus rounds on their fixes.
  - **Scenario.** A lead stalls on 2 Low-medium findings, or runs the fixes' rounds on the file's Sonnet, against the user's "keep running only opus until reviews converge".
  - **Fix.** "more than a few Low ones, or any above Low"; "the Opus rounds after the last step, on the entire branch and on its fixes"; the pins follow. Authority: the user's items 12 and 14.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** pins in `test_the_users_rules_of_2026_11_20_keep_their_wording`, failing first. **Fix:** step 7's branches say "more than a few Low ones, or any above Low"; the `delegate` skill passes `model: opus` for "the Opus rounds after the last step, on the entire branch and on its fixes". **Also covered:** the story's step 7 and review cycle.

- [x] **TST-631 · Locals assigned from `re` results stay implicitly `Any`** · `tests/unit/test_agents.py:58`, `:65`; `tests/unit/doc_pointers.py:35`; `tests/unit/test_guide.py:1050`; `tests/unit/test_review_lookup.py:419`, `:801`; `tests/unit/test_server.py:77` · confirmed · found 2026-11-20 by two reviewers (Opus)
  - **Defect.** `re.Match.group` gives `str | Any` and `re.findall` `list[Any]`; seven locals in functions the branch adds or changes keep them, so mypy checks nothing done with them.
  - **Scenario.** A wrong use of `value`, `found`, `titles` or `commands` passes mypy.
  - **Fix.** Annotate them (`str | None`, `list[str]`, `set[str]`). Authority: `.claude/rules/python.md` (look for implicit `Any`); TST-601.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `mypy --disallow-any-expr` reported the 7 locals before, only the `re` calls after (expressions, as TST-601 left them). **Fix:** the 7 annotated. **Also covered:** a sweep of the branch's added lines annotated `files` (`bash_refusal`), `targets` (`_dead_links`), `last` (`_sed`), `lines` (`_by_model_rows`), and two locals that needed a fresh annotated name. Measured: `--disallow-any-expr` doesn't report `Match.group()`'s `str | Any`, so TST-601's method misses that form; the sweep grepped for it.
  - Questioned by TST-635 (2026-11-20).

- [x] **TST-632 · The story states two things no setup file holds · follows TST-618, generation 2** · `docs/agent-workflow.md:162`, `:172-179` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** A mid-run change "reaches the running developer through SendMessage, rather than by editing the files it is editing" is in no setup file; "a skill isn't re-read ... a compaction may cut it" is listed as measured, while AGENTS.md cites Claude Code's docs for it.
  - **Scenario.** A copier takes a practice for a rule, or a documented fact for a measurement.
  - **Fix.** Drop the first; attribute the second to Claude Code's docs. Authority: `.claude/rules/docs.md`.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Fix:** the SendMessage practice dropped; the skill reload attributed to Claude Code's docs. **Test:** the docs tests.

- [x] **AGT-101 · The hook's file holds a shell command-line parser beside its answers** · `.claude/hooks/large_reads.py:787-963` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** `_commands`, `_comment`, `_named`, `_count`, the printers and `PRINTERS`, `_run`, `_ran_before`, `_folder`: about 175 of the new file's 1,000 lines parse shell, not answer a tool call.
  - **Scenario.** A reader of the hook goes through the parser to follow its five answers.
  - **Fix.** Move them to a sibling module (`.claude/hooks/command_lines.py`), imported by `_printed`; `load_script` puts `.claude/hooks` on `sys.path`; a move, the tests passing before and after. Authority: `.claude/rules/python.md`, Keep each file to its main logic.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** a move: the 248 hook tests passed before and after; `test_the_hook_fails_open_without_its_command_line_parser` (failing before the move, and with a top-level import). **Fix:** `.claude/hooks/command_lines.py` (`commands`, `PIPED`, `spans`), imported inside `_printed` and `_only_reads`, so a missing module leaves the hook failing open; `load_script` puts the script's folder on `sys.path`.
  - Questioned by AGT-103, AGT-104 (2026-11-20).

- [x] **TST-633 · The notebook fixtures type a notebook and its cells as `dict[str, object]`** · `tests/unit/notebook_files.py:7`, `:9`, `:14`, `:16` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** Records with known keys are typed `dict[str, object]`, so a misspelt key or a wrong value type passes mypy.
  - **Scenario.** A fixture writes `exection_count`, and the test checks another notebook than it means.
  - **Fix.** `Output`, `Cell` (`total=False`, `source: object` for the test that passes a non-text source) and `Notebook` TypedDicts. Authority: `.claude/rules/python.md` (a record's `dict[str, object]` where a `TypedDict` fits).
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** a scratch mypy probe: a misspelt key, a wrong value type and an extra key in a cell gave 0 errors before, 3 after. **Fix:** `Output`, `Cell` (`total=False`, `source: object`) and `Notebook` TypedDicts.

- [x] **TST-634 · ruff reaches `.claude/worktrees/`, and the posix-import test skips `.claude/hooks` · follows TST-558, generation 2** · `ruff.toml:6`; `tests/unit/test_lint.py:55-57` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** TST-558 set the rule (reach `.claude/hooks`, never `.claude/worktrees/`) for mypy only. ruff doesn't skip dot folders and nothing in the repository ignores `.claude/worktrees/` (this machine's `.git/info/exclude` does), so `test_lint.py` and `ruff check --fix .` would lint and rewrite a worktree's files in another clone; `test_no_module_imports_a_posix_only_module_at_its_top` skips every dot folder, the hook included, which also runs on Windows (ROADMAP item 111), and its comment says it covers the repository's own files.
  - **Scenario.** A worktree's unfinished file fails the main checkout's lint, or loses an import to `--fix`; a later `import fcntl` at the hook's top passes the test and breaks the hook on Windows.
  - **Fix.** `.claude/worktrees` in ruff's `extend-exclude`, with a check beside `test_mypy_reaches_the_python_files_in_hidden_folders`; the posix-import walk takes `.claude/hooks`, its comment fixed. Authority: `address-review` step 3 (the pattern everywhere).
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_ruff_skips_claude_codes_worktrees` and `test_the_posix_import_check_reads_the_hooks`, both failing first. **Fix:** `.claude/worktrees` in `ruff.toml`'s extend-exclude; the posix-import check walks the folders `mypy.ini` names (`conftest.mypy_config()`, `mypy_files()`, shared with `test_types.py`). **Also covered:** the other repository walks cover only Designer or Qt folders.

- [x] **AGT-102 · A hook comment says AGENTS.md has PLAN.md read whole** · `.claude/hooks/large_reads.py:253` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** `# the repository's own, read whole (AGENTS.md)`: AGENTS.md says to read PLAN.md before anything else, not whole.
  - **Scenario.** A maintainer takes the exemption for a rule it isn't.
  - **Fix.** Say what AGENTS.md says. Authority: `.claude/rules/docs.md`.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** a pin in the PLAN.md read test, failing first. **Fix:** the comment says AGENTS.md has PLAN.md read before anything else, and that its reads pass, whole or not.

- [x] **AGT-103 · With `PYTHONSAFEPATH` set, the hook can't import its parser and lets Bash calls through unchecked · follows AGT-101, generation 2** · `.claude/hooks/large_reads.py:437`, `:773` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** `import command_lines` relies on Python putting the script's folder first on `sys.path`; since Python 3.11, `PYTHONSAFEPATH` (or `-P`) stops that, so the import raises inside `main()`, which fails open. The single-file hook had no such dependency, and the move was to change no behaviour.
  - **Scenario.** In an environment with `PYTHONSAFEPATH=1`, the lead's `cat` of a 30 KB file runs unrefused, Bash reads go uncounted, and a big output gets no note, with nothing showing the guard is off.
  - **Fix.** Put the hook's own folder (`os.path.dirname(os.path.realpath(__file__))`) on `sys.path` before the import, or load the module by its path; a test running the hook with `PYTHONSAFEPATH=1`, `cat big.py` refused. Authority: AGENTS.md, Delegating to subagents (the hooks in every main session); the hook's docstring.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_the_hook_finds_its_parser_when_python_puts_no_script_folder_on_its_path` runs the real hook with `PYTHONSAFEPATH=1` and expects `cat big.py` refused; it exited 0 first (measured: the variable leaves the script's folder off `sys.path`). **Fix:** the hook puts its own folder (`HOOKS`, from `__file__`'s real path) first on `sys.path` at load; `PROJECT` derives from it; `load_script` no longer adds the folder, which had hidden the bug. **Also covered:** no other script imports a module from beside it; without the parser the hook still fails open.

- [x] **AGT-104 · The parser module's docstring says a hook without it lets every call through · follows AGT-101, generation 2** · `.claude/hooks/command_lines.py:6-7` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** Only `_printed` and `_only_reads` import the module, both for Bash calls; `read_refusal` and `web_refusal` never do, so a big Read and the lead's web calls are still refused without it.
  - **Scenario.** A maintainer reads that the whole hook is off without the module.
  - **Fix.** Generation 2: narrow the sentence to Bash calls, the Read and web refusals still applying. Authority: `.claude/rules/docs.md`.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Fix:** generation 2: the docstring says a hook without the module lets every Bash call through, its Read and web refusals still applying; the fail-open test's comment narrowed the same way.

- [x] **TST-635 · One more `re` result left implicitly `Any` · follows TST-631, generation 2** · `tests/unit/test_guide.py:70` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** `parts = re.split(r'(?m)^(?=# Scripting)', guide_md())` in `_parts`, which the branch changed: typeshed gives `re.split` `list[str | MaybeNone]`, so `parts` is `list[str | Any]`. TST-631's sweep grepped for `Match.group()` and missed `re.split`.
  - **Scenario.** A misspelt method on `parts[0]` passes mypy.
  - **Fix.** `parts: list[str] = re.split(...)`, and the sweep run again for `re.split` in the branch's changed functions. Authority: `.claude/rules/python.md`; TST-631.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** a scratch `reveal_type` probe: `list[str | Any]` before, `list[str]` after. **Fix:** `parts: list[str]`. **Also covered:** every `MaybeNone` return typeshed gives (`re`'s splits and groups, `configparser.get`, `zip_longest`, the std streams, `returncode`) grepped in the 33 Python files the branch changes: the locals are annotated; `test_server.py`'s `_dispatched_ops` keeps two, in a function the branch doesn't change.

- [x] **AGT-105 · The hook's docstring names a profile function as the only move it doesn't see** · `.claude/hooks/large_reads.py:115` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** `A function of the user's profile moves it unseen.` ends the list of unseen moves. A function defined earlier in the same line with the `function` keyword (`function f { cd sub }; f; cat big.py`) also moves the folder, and `setopt chase_dots` earlier in the line changes how `cd` reads `..`. `command_lines.py` follows neither; `f() { cd sub }` already ends the sizing at its `(`.
  - **Scenario.** A maintainer takes the sentence for the whole list, while a line defining its own function has `big.py` sized in the folder the line started in.
  - **Fix.** Widen the sentence rather than chase forms: a function or a shell option, from the user's profile or set earlier in the line, moves the folder unseen. Authority: `.claude/rules/docs.md`; the docstring's own list.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_a_function_or_a_shell_option_set_earlier_in_the_line_moves_the_folder_unseen`, on `_linked`: `function f { cd sub }; f; cat big.py` and `setopt chase_dots; cd link/.. && cat big.py` have the hook size the big `project/big.py` where zsh prints a small file; it failed first on its docstring pin. **Cause:** the list of unseen moves ended with a profile function alone, so it read as the whole list. **Fix:** a bullet of its own: a function or a shell option, from the user's profile or set earlier in the line, moves the folder unseen and doesn't end the sizing, with zsh 5.9's measured cases (2026-11-20). **Also covered:** the texts saying the sizing stops at "a command that may move the folder unseen", which a function is (the MOVES bullet's first sentence, `_printed`'s and `spans`' docstrings, a test comment), now say "a command of MOVES that the hook doesn't follow"; `command_lines.py`'s MOVES comment narrowed to the builtins and reserved words. No test pinned the old sentence.

- [x] **AGT-106 · A step's claim leaves out the user's later dated instructions that change it · follows AGT-99, generation 2** · `.claude/skills/project-code-review/SKILL.md:151-156`, step 3; `.claude/skills/delegate/SKILL.md`, The brief · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** Step 3 gives each step's text from the first commit of PLAN.md holding it, and the `delegate` skill's brief the text the user approved. Neither says that the user's later dated instructions changing a step join the claim, the later one standing. The whole-branch briefs added them by hand (the user's instructions of 2026-11-20, items 1 to 22).
  - **Scenario.** A lead following step 3 gives a whole-branch round only the steps' first texts. Its reviewers report the files that follow the user's later word (the reviewer's default model, the review flow) and miss one still following the earlier text.
  - **Fix.** Generation 2: step 3 adds the user's later instructions that change a step, word for word with their dates, the later one standing; the `delegate` skill's brief says so in a few words; a pin in `test_a_step_is_quoted_as_the_user_approved_it`. Authority: AGT-99; the `delegate` skill, The brief.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** pins in `test_a_step_is_quoted_as_the_user_approved_it`, failing first on step 3. **Cause:** step 3 and the `delegate` skill's brief gave only a step's first approved text; the user's later instructions went into the briefs by hand. **Fix:** step 3: the user's later instructions that change a step join it, each quoted word for word with its date, the later one standing where two texts differ; the `delegate` skill's brief says the same in a line. **Also covered:** `reviewer.md`, Review blind, retold the claim and says so too; the story (`docs/agent-workflow.md:44`, `:175`) follows, line 44 pointing to step 3. No other doc retells the claim.

- [x] **AGT-107 · The docs rule tells every agent to add new ideas to ROADMAP.md, which the other files have proposed to the user** · `.claude/rules/docs.md:39` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** `Open work lives in [ROADMAP.md](../../ROADMAP.md): check it before proposing improvements, and add new ideas there.` The `delegate` skill (The loop is the lead's), the `address-review` skill (After a group) and `developer.md` (Report) have a ROADMAP.md item proposed to the user and added once the user approves it. The sentence came from main's AGENTS.md with Step D's move, so it is in the branch's diff.
  - **Scenario.** A developer or an analyst that loaded `docs.md` writes a ROADMAP.md item itself, with no proposal and no yes from the user.
  - **Fix.** The sentence has new ideas proposed to the user, who decides each, pointing to the `address-review` skill (After a group) by its path; a pin that the old wording is gone. Authority: the `delegate` skill, The loop is the lead's; the `address-review` skill, After a group.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** pins in `test_decisions_and_roadmap_are_proposed_while_reviewing_and_addressing_never_at_a_cleanup`, failing first on `'add new ideas there'`. **Cause:** the sentence, carried from main's AGENTS.md, had any agent add ideas to ROADMAP.md itself. **Fix:** `docs.md`: new ideas are proposed to the user, who decides each; an idea goes in ROADMAP.md once they approve it, as the `address-review` skill's After a group says, with its path. **Also covered:** the docs' other ROADMAP mentions already have items proposed, only read ROADMAP.md, or sort a finding as work for later without saying who writes the item (`address-review:145`, the story's `:120-121`, both told how by After a group and the story's table).

- [x] **TST-636 · 31 questioned entries lack step 2's "Questioned by" line, and no test checks it** · `REVIEW.md`; `tests/unit/test_review_lookup.py` · confirmed · found 2026-11-20 by a reviewer (Opus)
  - **Defect.** Step 2 adds "Questioned by <new ID> (<date>)" under an old entry that a new finding questions, if the old entry is still in the file. 31 follow-ups since 2026-11-19 have none under the entry they follow (for example TST-608 under TST-564, TST-615 under AGT-92 and TST-613, AGT-103 and AGT-104 under AGT-101). No test pairs a `follows` mark with its line.
  - **Scenario.** A reader of an old entry takes its resolution as standing, not seeing that a later finding questioned it.
  - **Fix.** The lead adds the missing lines, since only the lead writes REVIEW.md; a test: every `follows X` whose X is in the file has "Questioned by <ID>" under X. Authority: the `project-code-review` skill, step 2.
  - **Resolution: done** (2026-11-20: the developer's test; the lines by the lead).
    - **Test:** `test_every_entry_a_follow_up_questions_says_so` (`_unquestioned`): every `· follows X` mark (`X and Y`, `X, Y` too) whose X is in the file needs a `Questioned by` line naming it in X's entry; a removed X is skipped. It failed first listing 30 pairs under 23 entries (AGT-99's line for AGT-106 was in already); a sample test covers the mark's forms, a removed X, a title saying "follows", a line under the wrong entry; the cleaned-up file passes it. **Fix:** the lead added the 30 lines, one per date under each entry; the test passes. The title's 31 counts follow-up marks: they sit under 24 entries.

- [x] **AGT-108 · The hook refuses a `read_file` past the end of a file over 1 MB when `limit` is 1** · `.claude/hooks/large_reads.py`, `_pycharm_returns` and `_bounded` · confirmed · found 2026-11-20 by the developer (Opus)
  - **Defect.** With `limit=1`, `half` is 0, so `itertools.islice(shown, half)` takes nothing and the lazy `shown` never skips its `first - 1` lines: the head is empty, with `head.lines == 0 == half`. In a file over BIG that sends the call to `_bounded`, which reads the file's last line back from its end and never checks that line `first` is in the file. PyCharm answers an `offset` past the last line with the error `offset exceeds file length` and no lines (measured by the lead, 2026-11-20). `_pycharm_returns`'s docstring says it returns None for a call answered with an error; it returns a size instead.
  - **Scenario.** The lead's `read_file` of a 1.03 MB file of 500,001 lines, the last one 25,000 bytes, with `offset=10000000, limit=1`, is refused (the developer's scratch run), while PyCharm would return only the error. With `limit` 2 or more, or in a file under 1 MB, the call passes.
  - **Fix.** `_pycharm_returns` returns None for an `offset` past the file's last line, as its docstring says; a test on that file, with `limit=1`. Authority: the hook's docstring (a read is refused when it returns over 20 KB).
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_read_file_from_past_the_last_line_passes_and_from_the_last_lines_is_sized`, over files under BIG and over it, with and without a last newline, at `limit` 1 and 2: an offset one past the end and `10_000_000` pass (`_returned` gives None), an offset at the 25,000-byte last line is refused (but with `limit=1` when an empty line follows it), an offset at the empty line after a last newline passes. It failed first over BIG, with no last newline and `limit=1`. **Cause:** with `limit=1`, `half` is 0, so the lazy `shown` never skips its `first - 1` lines, and over BIG `_bounded` reads the last line from the end with nothing checking that line `first` is in the file. **Fix:** `_has_line(f, number)` counts newlines from the start in BLOCK reads, only until there are enough; `_pycharm_returns` returns None when `big and not half and not _has_line(f, first)`, before `_bounded`, and when the head and tail are both empty, after the tail; its docstring names an `offset` past the last line among the calls answered with an error. A small file's read gets no extra pass. **Also covered:** `_bounded` was the only path sizing lines from the end from a starting line (`_sizes`' negative start is `tail -n`; `_read_returns` reads forward; `_last` is guarded for `count < 1`); each of the two checks seen to matter by disabling it in a copy of the hook.

- [x] **AGT-109 · The hook's docstring credits the user with facts the lead observed** · `.claude/hooks/large_reads.py:77-79` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** "A call run in the background (`run_in_background`) is never sized. Its output goes to a file, not into the context, and the notice of its end carries none (the user, 2026-11-20)." The user decided that a background call goes unsized (item 32); that its output goes to a file and its notice carries none is the lead's observation.
  - **Scenario.** A maintainer takes the notice's content for something the user stated, and doesn't re-measure it when Claude Code changes.
  - **Fix.** The attribution goes with the decision; the facts say they were seen by the lead, with the date. Also record there the measured boundary of `read_file`'s error (the twentieth review's log: `a\nb` offset 3, `a\nb\n` offset 4). Authority: `.claude/rules/docs.md`.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** pins in `test_a_command_run_in_the_background_passes` and `test_the_docstring_gives_the_ranges_pycharms_read_file_refuses`, failing first. **Cause:** one parenthetical credited the user with the decision and the lead's observation alike. **Fix:** "is never sized (the user, 2026-11-20). Its output goes to a file, not into the context, and the notice of its end carries none (seen by the lead, 2026-11-20)."; the measured list gains the first erroring offset, one past the last line, the empty line after a last newline counted (`a`, newline, `b`: offset 3; with a newline after `b`: offset 4; measured by the lead). **Also covered:** the past-the-end test already checks `last + 1` with and without a last newline.

- [x] **TST-637 · The story leaves out the move to ROADMAP.md that stops the loop and the developer rows** · `docs/agent-workflow.md:105-113`, `:60`, `:133` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** The stop list names "a won't fix that meets its three criteria" but not "a finding to move to ROADMAP.md instead of a fix", which the `delegate` skill now lists; step 8's convergence report recaps "the won't fixes the user agreed" but not the findings moved to ROADMAP.md (`project-code-review`, step 7); the files table gives REVIEW.md "a table of each round's findings, tokens and time by model", without the rows per developer run.
  - **Scenario.** A reader setting up another repository from the story asks the user at once only for a won't fix, and keeps no developer rows.
  - **Fix.** The bullet, the recap clause and "per round and per developer run", preferring pointers. Authority: `.claude/rules/docs.md` (the story updated in the change that alters the setup it tells).
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** pins in `test_a_finding_moved_to_roadmap_md_has_its_wording_and_stops_the_loop` and `test_the_table_by_model_has_the_developers_row_and_the_severities_in_its_cells`, failing first. **Fix:** the story's stop list gains "a finding to move to ROADMAP.md instead of a fix (the `address-review` skill, step 7)"; step 8 recaps "the findings they moved to ROADMAP.md"; the files table's REVIEW.md row names "a table by model of the findings, tokens and time of each round and each developer run". **Also covered:** `docs_text.story_md()` replaces three hand-written reads of the story.

- [x] **TST-638 · A test comment counts two exceptions where the test pins three** · `tests/unit/test_guide.py:913` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** "# the user, 2026-11-20: two fixed waits stay, as the exceptions the rule names." The test also pins the window-state settles (item 37).
  - **Scenario.** A maintainer takes the third pinned phrase for a stray.
  - **Fix.** Three fixed waits, the third named in the comment. Authority: the `address-review` skill, step 6.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** none, a comment. **Fix:** the comment says three fixed waits stay, the third named (the window-state facts' settles, TST-412).

- [x] **TST-639 · REVIEW.md's and the template's wordings line write `<date>` bare, which GitHub drops** · `REVIEW.md:13-14`, `.claude/skills/project-code-review/TEMPLATE.md:13-14` · confirmed · found 2026-11-20 by a reviewer (Sonnet)
  - **Defect.** "moved to ROADMAP.md (item N, the user, <date>)": GitHub's renderer drops an unknown tag, so a person reading REVIEW.md there sees "(item N, the user, )". The header's other placeholders (`<who>`, `<model>`) are in backticks, as `address-review` has this wording.
  - **Scenario.** A person reading the header on GitHub can't tell what the fifth wording holds.
  - **Fix.** The wording in backticks in both files, and `test_the_template_gives_the_wordings_the_check_accepts` following. Authority: the header's own form.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_the_template_gives_the_wordings_the_check_accepts` (each wording in backticks), `test_review_mds_header_writes_no_placeholder_github_drops` and `test_no_doc_writes_a_placeholder_github_drops` over every Markdown file (`docs_text.bare_tags`, CommonMark's open-tag form outside code), failing first. **Cause:** a placeholder of a tag's form is an HTML tag, which GitHub drops when it doesn't know it. **Fix:** the wordings in backticks in TEMPLATE.md and REVIEW.md's header. **Also covered:** the review skill's `Questioned by <new ID> (<date>)` and `Note (<date>): ...`, and the template's example `<who> (<model>)`, put in backticks; REVIEW.md's entries keep the wording they were written in, so the test reads its header only.

- [x] **AGT-110 · The hook's module docstring holds a carriage return where it means the two characters `\r`** · `.claude/hooks/large_reads.py:22` · confirmed · found 2026-11-20 by the developer (Opus)
  - **Defect.** "PyCharm's `search_regex` found no `\r` in those files": the module docstring isn't a raw string, so Python reads `\r` there as a carriage return. The source shows the two characters; `__doc__`, which the pins read, holds a CR.
  - **Scenario.** `help()` or a pin printing that sentence shows a broken line, and a pin quoting the sentence as written in the source can't match it.
  - **Fix.** Write `\\r`, or name the character in words, as the sentence before it does ("a lone CR"). Authority: the docstring's own claim.
  - **Resolution: done** (2026-11-20: the developer's report, assessed and written by the lead).
    - **Test:** `test_the_hooks_docstring_holds_no_control_character`: the hook's `__doc__` holds no control character but a newline; it failed first (`['\r'] == []`). **Cause:** the module docstring isn't a raw string, so the source's `\r` became a carriage return. **Fix:** `:22` writes `\\r`, so `__doc__` holds the two characters; the sentence gives the regex `search_regex` was given, the sentence before it naming the character in words. **Also covered:** an `ast` scan of every docstring in the repository's 260 Python files found no other control character; comments aren't parsed for escapes.
