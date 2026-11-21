# Working with a lead agent and subagents

This is how this repository has Claude Code work on a change. One **lead** agent talks with the user and drives four
kinds of **subagents**, which research, build, review and run. This file is written for an agent asked to set up the
same way of working in another repository, with the setup files listed at the end. It is updated in the change that
alters the setup it tells (`.claude/rules/docs.md`, Keeping the docs current). Where this file and the setup's own
files differ, the setup's files win: they are the rules, and this is the story of how they fit together.

Nothing here is about this project's own domain. The setup is for changing code in any repository; only the examples
come from this one.

## The cast

| Agent | What it does | What it never does | Reads only | Reports to |
|---|---|---|---|---|
| **Lead** (the main session) | Talks with the user, writes the plan, runs the loop, settles every review finding, writes REVIEW.md, commits on the branch | Fetch or search the web; read anything of unknown size; push or merge unasked | No | The user |
| **Analyst** | Answers what needs reading across many files or the history; every web search, and the lead's web fetches | Edit, or run anything that writes | Yes | Whoever started it |
| **Reviewer** | Reads a diff against a claim and reports suspicions, each with the code quoted and what would settle it | Run tests, probe, edit, read the plan | Yes | The lead |
| **Developer** | Implements a step or fixes findings, test first, with its own test runs; may start analysts | Commit, write REVIEW.md or the plan, run the full suites | No | The lead |
| **Runner** | Runs the full suites when the user asks, a review's probes, and diagnoses a crashed or hung program | Change code or a committed file | No | The lead |

The agents are defined in [.claude/agents/](../.claude/agents/). Each agent file holds its tools, its model, its
effort and its rules. Each agent loads AGENTS.md and the user's memory index, but never the conversation: its brief
is all it knows about the task. Only the developer starts other agents, and only analysts, one level deep. A subagent
never talks to the user: where a rule says to ask the user, it reports to the lead, which asks.

## The flow, as a story

A user asks for a feature. This is what happens, from the ask to the merge.

1. **Research.** The lead starts analysts in parallel, one question each: where the code lives, what the change
   touches, what the docs already say. Each returns a short brief with `file:line` references, so the lead reasons
   without the files in its context.
2. **The plan.** The lead writes PLAN.md at the repository's root: the branch's steps, each in full detail, with its
   acceptance criteria, and a section **Waiting for the user** for the decisions that are the user's. The user reads
   the whole plan and approves it. Nothing is built before that.
3. **A step is built.** The lead briefs one developer for the step. The developer writes the tests first and watches
   them fail, then writes the code until they pass. It runs only its own tests, never a full suite. It runs
   `/simplify` on its change, with analysts as the cleanup agents, unless the change touches Markdown
   files alone (`.claude/rules/python.md`, Simplify the change before reviewing it). It reports what changed, how each test failed
   first, and the runs. The lead reads the report and the change's size (`git diff --stat`), never the diff itself,
   and commits.
4. **The step is reviewed.** The lead starts reviewers, one per area of the diff, at once. Each gets the command that
   prints its diff and the claim: the step's text as the user approved it, and the user's later instructions that
   change it, quoted whole (the `project-code-review` skill, step 3). A reviewer never sees the plan, which holds the
   lead's own account of the work, and every diff command leaves PLAN.md out. Reviewers report suspicions, never
   verdicts.
5. **Every suspicion is settled before it is written.** The lead reads the lines each one quotes. What reading can't
   settle gets a probe: the runner runs it, or the lead does when only its own session can (what its hooks do, what
   its tools return). What no probe here can check, such as another operating system, goes in the review log under
   Not verified (the `project-code-review` skill). Only what is settled as real goes in REVIEW.md, which only the lead
   writes.
6. **The findings are fixed.** The developer fixes them, test first, and reports each resolution: the test and how
   it failed, the cause, the fix, and where else the same pattern was searched. The lead checks each resolution's
   evidence, then writes it in REVIEW.md and checks the entry off.
7. **The review cycle** (below) repeats steps 4 to 6 until the step's reviews are done. The loop then goes on with
   the next step of the plan. After the last one, Opus rounds review the entire branch and the fixes of their
   findings until the reviews converge.
8. **Convergence.** The lead tells the user that the reviews converged: the totals, the most severe findings, the
   decisions it took alone, the decisions waiting for the user, the won't fixes the user agreed along the way, and the
   findings they moved to ROADMAP.md.
   The user decides: another round, or the final check. What must outlast the branch goes into DECISIONS.md or
   ROADMAP.md now, as the user approves it, before the final check: the merge takes the branch's whole tree.
9. **The final check.** On the user's word, the runner runs the full suites, then reruns each failing test alone, as
   it needs. One that passes alone failed at random: it counts as passed, and the lead lists
   it in ROADMAP.md, or counts it again there, before the merge (DECISIONS.md, Project rules). Any other failure goes in REVIEW.md like
   any finding, and is fixed the same way.
10. **The merge.** The lead deletes PLAN.md in the branch's last commit, and the branch is squashed into `main` on
    the user's word.
11. **The cleanup.** Later, and only when the user asks, REVIEW.md's resolved entries are removed. Git keeps them,
    and a script finds any of them again by its ID.

## The review cycle

The user and the lead agreed on this cycle after comparing the two models as reviewers (below). A few Low findings
means about 5 to 7 at most. The rules are in step 7 of the review skill,
[project-code-review](../.claude/skills/project-code-review/SKILL.md).

1. **For each step of the plan, or a group of small steps:** a Sonnet round reviews the step's diff. The developer
   fixes the findings, and a Sonnet round reviews those fixes. This repeats until a Sonnet round finds only a few Low
   findings, or none. The developer fixes those few, and the loop goes on with the next step.
2. **After the last step:** an Opus round reviews the entire branch diff against `main`, all the work of the branch.
3. **If it finds more than a few Low findings, or any above Low,** the developer fixes them, and Opus rounds review the
   fixes until one finds only a few Low findings, or none. Those are fixed, and an Opus round reviews the entire branch
   again.
4. **The reviews converge** when an Opus round of the entire branch finds only a few Low findings, or none. The first
   such round counts. The developer fixes those few, and the lead tells the user.

The reviewer's agent file names Sonnet, its default. The lead passes `model: opus` on the Agent call for the Opus
rounds, and for any run the user asks to have on Opus.

**Why two models.** In a whole-branch review, each area went to an Opus reviewer and a Sonnet reviewer with the same
brief, and every suspicion was settled. Of 12 real findings, Opus found 8, 5 of them alone; Sonnet found 7, 4 of them
alone. Opus alone found the one defect in code and two contradictions in the rules' text. Sonnet alone found a fact a
cleanup had lost. The two used about the same tokens, and Sonnet was faster and costs less per token. So the cheaper
model reviews each step, and the stronger one reviews the whole work at the end.

## Who decides what

**The developer decides how it implements its unit** (`.claude/agents/developer.md`). A change to the plan, even a
slight one, it reports to the lead.

The lead decides alone everything that isn't the user's, records each choice and its reason in PLAN.md, and lists them
when it reports convergence. That covers a change the developer proposes within what the branch delivers, a finding's
severity, whether a finding is real, the order of the work, a fix's scope, where a fact goes in the docs, and fixing
the branch's own leftovers in the branch rather than proposing them for later.

**The loop stops for the user** only for:

- a change to what the branch delivers that a user would see, beyond the plan;
- anything touching the user's own work, or the user's own files outside the repository;
- the full suites, the merge or a push;
- a change of an agent's model, or a cost far over what the lead announced. Before a long or expensive unit, the lead
  tells the user what it will cost, how long it will take and what comes back (AGENTS.md, Delegating to subagents);
- a won't fix that meets its three criteria (below);
- a finding to move to ROADMAP.md instead of a fix (the `address-review` skill, step 7);
- any other decision of the user's that blocks the next step.

**When in doubt** whether a decision is its own, the lead asks the user at once. A decision of the user's that blocks
nothing waits in PLAN.md's Waiting for the user, and the lead asks it at convergence with the others.

**A won't fix is the user's decision.** The developer or the lead may propose one. The lead judges it against three
criteria, which must all hold: the finding is real; fixing it is never worth it, not just "not now", because the fix
costs far more than the harm, goes against a choice of the user's, or can't be made from this project; and it isn't
work for later, which is a ROADMAP item instead. When fixing could be worth it, or the lead is unsure, the finding
is fixed; a false one is answered "not a bug", and work for later outside the branch goes to ROADMAP.md, which closes
the finding once the user approves the item (the `address-review` skill, step 7). When all hold, the lead asks the user at once, since the finding stays open meanwhile.

**A false finding is no decision.** A finding that turns out not to hold is answered "not a bug" or "not reproducible"
in REVIEW.md, with the test kept as its guard. It never goes in DECISIONS.md.

## The files, and what each remembers

| File | What it remembers | Who writes it | How long it lives |
|---|---|---|---|
| PLAN.md | The branch's steps, what is done and left, the lead's decisions, what waits for the user | The lead | The branch: deleted in its last commit |
| REVIEW.md | Every finding of the branch's reviews, with its resolution and who found it on which model; the review log; a table by model of the findings, tokens and time of each round and each developer run | The lead, from the reports | Until the user asks for a cleanup; then git |
| DECISIONS.md | What is settled for the whole project that a reviewer could raise again: the user's won't fixes, rules and choices | The lead, with the user's approval; the names and paths an entry points at, the agent whose change renames or moves them | For good |
| ROADMAP.md | Work for later, ideas, items needing another machine | The lead, with the user's approval | For good, items checked when done |
| AGENTS.md | What every session and every agent needs, and pointers to the rest | Any change that alters a rule | For good, kept small |
| Agent files | Each agent's tools, model, effort and own rules | Changes to the setup | For good |
| Skills | Procedures only some work needs: the loop, a review, fixing findings, a cleanup, the test runs | Changes to the setup | For good |
| Path-scoped rules | Rules only some files need, loaded when an agent reads such a file | Changes to the setup | For good |
| Hooks | The lead's guards against large reads and web calls | Changes to the setup | For good |

[AGENTS.md](../AGENTS.md) is loaded whole into every session and every subagent, so every agent pays for each byte of
it. Here it went from 39.9 KB to 13.1 KB without losing a rule. Rules only some files need moved to
[.claude/rules/](../.claude/rules/), procedures only some work needs moved to skills, and the hook's rules moved to
its docstring. Each move was checked word for word by a script, tests pin that each rule has one home, and a test
keeps AGENTS.md under a byte budget.

## Keeping the lead's context clear

The lead's context is the scarce resource: it holds the conversation with the user for the whole branch.

- **It reads a thing itself only when it knows the output will be small:** a tiny file, a few known lines, an output
  capped in the call (`head`, `--stat`, a count). When it can't tell the size in advance, it asks an analyst. An
  analyst for a tiny read costs more than it saves. Monitor's events count too (AGENTS.md, Delegating to subagents).
- **It reads reports, not diffs.** The developer's report and the change's size are enough to commit; the reviewers
  read the diff.
- **It never fetches or searches the web.** An analyst does, and returns only the answer.
- **Hooks enforce it** in the main session: [.claude/hooks/large_reads.py](../.claude/hooks/large_reads.py), with
  [.claude/settings.json](../.claude/settings.json). They refuse a read that would return over 20 KB, a shell command
  that would print over 20 KB of files, and the lead's web calls, each with the ways on. They add a note to a large
  output and to every 8th reading call of a turn. The settings cap a successful command's output, in the subagents
  too. The hooks let subagents' calls through.
- **A long run gets a timer:** one background command per run, which ends after about 20 minutes. When it ends and
  the run is still going, the lead asks the agent for its status with SendMessage, tells the user, and starts the timer
  again. When the run ends first, the lead stops the timer with TaskStop. The agent answers in a line or two and goes
  on (the `delegate` skill). From outside, a long silent run and a runaway one look the same.

## Working in parallel

- Independent agents start in one message: analysts on separate questions, reviewers on separate areas.
- **One developer at a time.** Two would edit the same files.
- No review starts while the developer edits.
- A round of fixes resumes the same developer while its context helps. A new step starts a new one.

## What the setup learned, as rules worth copying

- **Blind reviews.** The claim is the approved text and the user's later word on it, quoted whole to every reviewer,
  never the lead's view of how well it went. A reviewer handed a conclusion tends to confirm it. The plan is left out
  of every diff command: a reviewer once saw it through `git diff main...HEAD`.
- **Settle before writing, and cheaply.** Reading settles most suspicions. A mutation probe (break the code in a copy,
  run the tests) shows a test that guards nothing. A probe in the lead's own session settles what only it can see:
  one showed that a tool read `..` after a symlink lexically while the hook sized the physical file.
- **Measure the tools, don't guess.** What was measured here, with Claude Code at the end of 2026:
  - a path-scoped rule loads when a Read or a Write touches a matching file, or a shell `cat`, `head`, `tail`, `sed -n`
    or `grep` prints its lines unpiped; a `wc -c`, a piped command and an IDE's own read tool load none; after a compaction, the next such
    read loads the rule again;
  - an edited agent file reaches only the agents started after the user's next message, so a brief has the agent read
    its file from disk; an edited skill preloaded by an agent reaches one started in the same turn;
  - a subagent's SendMessage to `main` reaches the lead within seconds, and a background `sleep` wakes it.
- **A change of an agent's tools, model, preloaded skills or effort takes a new agent,** and the lead tells the user
  so (the `delegate` skill, How changes reach the agents).
- **Load a skill again when its file may have changed, or after a compaction.** Claude Code's docs say a loaded skill
  keeps the text as it was loaded, and that a compaction may cut it short or drop it (AGENTS.md, Delegating to
  subagents).
- **Tests catch the lead's own slips.** A wrong total in REVIEW.md's status table was refused by the test that counts
  its entries.
- **Follow-up chains shrink when late fixes narrow claims.** A finding of the third generation or later of a chain,
  Low or Low-medium and only about tests or docs, is fixed by making the claim smaller, never by a new check
  (`.claude/agents/reviewer.md`, Follow-up chains). The reviews here went 22, 14, then 7 findings before converging.
- **Compare models before choosing one,** with the same brief and every suspicion settled, then count per model.
- **Commits are the safety net.** The lead commits on the branch before each review and after each round of fixes. No
  agent has a write guard, so a mistaken write lands on committed work at worst.
- **Keep what the product's own agents read apart.** In this repository, the docs an agent reads to use the product
  were left untouched by all of this, and that work is mostly started from other folders.

**Costs.** Each agent's completion notice gives its tokens and duration, and REVIEW.md's table by model adds them up
per review round and per developer run until a cleanup (the `project-code-review` skill's TEMPLATE.md). Here a whole-branch review in four areas cost about a million tokens per model.

## Setting it up in another repository

Copy these files and adapt them. Keep the rules that are about the setup; replace those about this project.

| File | What to change |
|---|---|
| [AGENTS.md](../AGENTS.md) | Keep the opening's commit rule; in Working on this project, the tests first, the review of one's own work and the paragraphs on PLAN.md and REVIEW.md; Running the tests, with its two stages; Delegating to subagents; and Deploying and diagnosing's pointer for an edited agent file. Replace the project's own rules and pointers, here those about the product, its guide, the IDE's tools and the live self-test, and list the new project's rules |
| [.claude/agents/](../.claude/agents/) | The tools each agent may use (drop this project's own: here the IDE's and the product's), the models and effort, the commands each may run. Their descriptions and bodies hold this project's parts too: where the analyst looks, what the reviewer cites and hunts for, the developer's triage of a new tool and its section on the product, the runner's sections on what it runs and on diagnosing the product |
| [delegate](../.claude/skills/delegate/SKILL.md) | Little: it is about the setup. Its passages about the product: the program a developer's brief lets it use, the user's program among what stops the loop, the runner's diagnosis of a program that crashed or hung, and the tools a developer's criteria name (the linter, lint and types) |
| [project-code-review](../.claude/skills/project-code-review/SKILL.md) and its [TEMPLATE.md](../.claude/skills/project-code-review/TEMPLATE.md) | The finding prefixes, one per area of the new project; the probes in the product and the live checks; the product's guide as a reviewer's context; the unit tests it names; the examples from this project's reviews |
| [address-review](../.claude/skills/address-review/SKILL.md), [cleanup-review](../.claude/skills/cleanup-review/SKILL.md) | The test commands and the kinds of tests; `address-review`'s live checks, its probes in the product and the facts it records in the product's guide; the examples |
| [live-check](../.claude/skills/live-check/SKILL.md) | Rewrite it for the new project's integration tests, suites and probes: most of it is about the product and its live self-test. Keep the sections the copied files point to, or change their pointers with the names: The suites (AGENTS.md, `runner.md`), How a probe runs (the review skills), When the final check fails (`developer.md`), and the one on a program that crashed or hung (`developer.md`, `runner.md`). Keep its order, fail then pass, and a probe as scratch code outside the repository, never committed. The runner preloads it |
| [.claude/rules/](../.claude/rules/) | Write the new project's rules, each with the `paths:` of the files it is for, and list them in AGENTS.md. Keep the parts the copied files point to: `python.md`'s Simplify the change before reviewing it, `docs.md`'s Keeping the docs current and Writing docs and comments, and `docs-tests.md`, the tests that check the docs and the changes they run on |
| [large_reads.py](../.claude/hooks/large_reads.py) with its parser [command_lines.py](../.claude/hooks/command_lines.py), and [settings.json](../.claude/settings.json) | The Python the hooks run with (here the project's venv, in `settings.json`'s commands); the IDE's tools the hook counts as reading calls (`READING_TOOLS`), which `settings.json`'s matchers name too; the commands it counts as reads (`PYTHONS`, `LOOKUP`); the limits, if wanted. How it sizes a command line was measured in zsh with macOS's BSD `cat`, `head`, `tail` and `sed` (its docstring): measure it again where the new project's shell or tools differ |
| [review_lookup.py](../scripts/review_lookup.py) | Nothing: it finds a removed finding in git's history by its ID |
| [DECISIONS.md](../DECISIONS.md), [ROADMAP.md](../ROADMAP.md) | DECISIONS.md: carry over its introduction and the setup's entries the copied files cite (the two stages of tests, the low-value findings not raised, no write guard), each approved anew by the other project's user. ROADMAP.md: start it empty, keeping its introduction's format |
| The tests: [test_agents.py](../tests/unit/test_agents.py), [test_guide.py](../tests/unit/test_guide.py), [test_large_reads.py](../tests/unit/test_large_reads.py), [test_review_lookup.py](../tests/unit/test_review_lookup.py), with [docs_text.py](../tests/unit/docs_text.py), [doc_pointers.py](../tests/unit/doc_pointers.py), [hook_calls.py](../tests/unit/hook_calls.py), [counted_reads.py](../tests/unit/counted_reads.py) and [notebook_files.py](../tests/unit/notebook_files.py) | Keep the tests of the setup (agent files, pointers, one home per rule, the budget, the hooks, REVIEW.md's counters); drop those of this project's docs; `tests/unit/conftest.py` must provide `ROOT`, the repository's root, which they import; `test_guide.py`, and `_designer_tools` in `test_agents.py`, also import this project's server and its test fixtures, so rewrite those parts |

Then hand an agent in the new repository this file, those files, and the user's own way of working, and have it write
the first PLAN.md: the setup itself is the first branch.
