---
name: delegate
description: Use in this repository before starting or resuming an agent (the Agent tool, or SendMessage), as the lead or as the developer starting an analyst, and before continuing the loop from PLAN.md (a session's start, a compaction) or while the lead runs it. Says which agent does what, the lead's loop (writing PLAN.md, what stops it for the user, an agent that stops to ask, a long run's timer, what comes back, the merge), what the brief gives the agent (the objective, the read set, the precedents, a developer's acceptance criteria, the Designer it may use, a reviewer's claim), since the brief is its only context about the task, and how a changed agent file reaches the agents.
---

# Delegating: which agent, the lead's loop, the brief

AGENTS.md, Delegating to subagents, says who reports to whom, what the lead reads itself and what its hooks
refuse. This skill holds the rest: which agent does what, the lead's loop from PLAN.md to the merge, what a brief
holds, and how a changed agent file reaches the agents.

## Which agent for what

| Agent | What to give it |
|---|---|
| `analyst` | A question whose answer means reading across many files or the git history: where something lives, how a flow works, what a change would touch, why a line is there. It returns a brief with `file:line` references. Every web search, and the lead's web fetches: documentation on the web (Claude Code's, Designer's, a library's). Also a conclusion of the lead's to check (below) |
| `reviewer` | An area or a diff to review, through the `project-code-review` skill |
| `developer` | A unit of implementation with a run-observe-adjust loop: a step of PLAN.md named in the brief, part of a ROADMAP item, REVIEW.md findings, or the fixes a failed final check needs. One runs at a time: two would edit the same files (the user, 2026-11-19) |
| `runner` | The full suites once the user asks for them (the final check), chosen categories the user asks for, a review's probes (the `project-code-review` skill), and a Designer that crashed or hung |

**The `analyst` and the `reviewer` only read, by their instructions:** their files say which commands their Bash may
run, and no hook enforces it (DECISIONS.md, No agent has a write guard).

**Pass `model` on an Agent call only when the user asks for another model for that run** (the user, 2026-11-20). The
user asked for one already: the Opus rounds after the last step, on the entire branch and on its fixes (the
`project-code-review` skill, step 7). Otherwise the agent's file decides. The models are the user's choice of cost, so a
change of an agent's default model is proposed to the user first.

## The lead's loop

**PLAN.md** (AGENTS.md, Working on this project) may not be there yet. If it isn't, research the branch's work first,
with analysts, and write it in steps, each in full detail, with what is done, what is left and, in a section Waiting
for the user, the decisions waiting. The user reads the whole plan and approves it before the developer starts: the loop runs only after that. Keep it
current: a step done, a risk found, and the lead's choices (**The loop is the lead's**, below). PLAN.md is the
branch's memory and dies with the branch (the user, 2026-11-19). It may be committed on the branch, but never enters
`main`.

**The loop is the lead's** (the user, 2026-11-19). The developer implements a step of PLAN.md, or REVIEW.md findings.
The lead has the work reviewed after a step, or after a group of small steps it judges together, and gives the
developer the findings it writes, round after round. Sonnet rounds review each step, or group, until the step's reviews
are done, before the next starts. After the last step, Opus rounds review the entire branch and the fixes of their
findings until the reviews look converged (the `project-code-review` skill, step 7). The user hears that the reviews
converged then. The lead decides alone all but what is the user's, and records each choice and its reason in PLAN.md.
One of its own decisions: a leftover in the branch's own code is fixed in the branch (the user, 2026-11-19). What
stops the loop for the user:

- a change to what the branch delivers: a tool, parameter or behaviour a user sees, beyond the plan;
- anything touching the user's Designer or the user's own files outside the repository;
- the full suites, the merge or a push;
- a change of the agents' models, or a cost far over what the lead announced;
- a won't fix that meets the `address-review` skill's criteria (step 7), since its finding stays open until the user
  answers (the user, 2026-11-20);
- a finding to move to ROADMAP.md instead of a fix (the `address-review` skill, step 7), since it stays open until the
  user answers (the user, 2026-11-20);
- any other decision of the user's that blocks the next step.

In doubt whether a decision is its own, the lead asks the user at once. A decision of the user's that doesn't block the
next step waits in PLAN.md, Waiting for the user: a DECISIONS.md entry, a ROADMAP.md item. The lead asks them together when it
tells the user the reviews converged, and adds what the user approves. Independent agents start in one message. During
the loop, analysts answer what needs reading across many files and do the developer's research, but add no detail to a
step. No review starts while the developer edits.

**An agent that stops to ask** (the developer's triage, a missing criterion, a change to the plan, a decision only the
user can take) ends with its report. The lead brings back the answer with SendMessage to that agent, which goes on with
its context: a new agent would have only its brief (the Agent tool's description). A round of fixes resumes the same
developer while its context helps; a new step starts a new one.

**A long run** of the developer or the runner gets a timer: one background command per run, started with the run,
which ends after about 20 minutes. When the timer ends and the run is still going, the lead asks the agent for its
status with SendMessage, tells the user, and starts the timer again. When the run ends first, the lead stops the timer
with TaskStop. The developer and the runner have SendMessage only to answer that question, to `main`, in a line or two,
then go on. Measured 2026-11-19: a runner told to answer `main` did, and its answer reached the lead within seconds.
The lead's question moved the runner's foreground command to the background without stopping it. A background
`sleep 120` woke the lead when it ended.

**What comes back is evidence, not a verdict:**

- a claim like "every other tool does X" is a hypothesis: count the cases before it changes anything;
- to trust a conclusion, ask two analysts the same question with the same prompt, at the same time. Agreement is a
  complete result, and a disagreement is settled by measuring it. To cover more ground, split the scope across them
  instead;
- the developer runs `/simplify` and its tests on its own change (`.claude/rules/python.md`, **Simplify the change
  before reviewing it**). The lead reads its report and the change's size, not the diff:
  `git diff --stat <last reviewed commit>`, with `git status --short` for the new files. The reviewers read the diff,
  and the lead the lines each suspicion quotes (the `project-code-review` skill).

**The merge** into `main` is a squash, on the user's word, once the final check passed. A squash takes the branch's
whole tree. So what must outlast the branch is in DECISIONS.md or ROADMAP.md before the final check: the lead proposes
it when the reviews look converged and adds what the user approves (**The loop is the lead's**, above). After the
final check, the lead lists or counts each test that failed at random in ROADMAP.md, with the docs tests run (the
`live-check` skill, When the final check fails), and deletes PLAN.md in the branch's last commit.

## The brief

**The brief is the agent's only context about the task.** Don't paste what AGENTS.md says: the agent has it, as the
session last loaded it, so add only the rules edited since (How changes reach the agents, below). Give it what only
the conversation holds:

- the objective: one outcome;
- the read set: the files it needs;
- every precedent by path. A precedent no file can be cited for doesn't exist: don't assert it;
- for the developer, acceptance criteria: at least one of the unit's own, mechanically verifiable (a named test
  passing, a scratch run exiting 0), beside those always among them: ruff's fix and format run, lint and types
  passing, `/simplify` run on code and the tests run again after its fixes, and the docs tests when Markdown, a
  comment or a docstring changed (`.claude/rules/docs-tests.md`);
- the Designer it may use: a port of its own (`alone.run(..., port=...)`), or the lead's promise to stay off that
  Designer until it reports. Two agents never drive one Designer;
- for a review, or a check of the lead's own conclusion: the code and the claim, never a verdict or the lead's
  confidence. A reviewer handed a conclusion tends to confirm it. For a step of PLAN.md, or a group of steps, the
  claim is the text the user approved, with the user's later dated instructions that change it, quoted (the
  `project-code-review` skill, step 3).

## How changes reach the agents

**How changes reach the agents** (`.claude/agents/*.md`): a new or edited agent file reached the agents started
after the user's next message, not those started before that message. Measured in the 2026-11-18 session,
Claude Code 2.1.326: a reviewer started 85 s after its new file was written got "Agent type 'reviewer' not found",
and an analyst and a reviewer started 2 to 4 minutes after their files were edited had the old tools. Claude Code's
docs (sub-agents, Write subagent files) say instead that the next delegation uses the new definition. `/agents`
only prints that its wizard was removed (the user ran it, 2026-11-18). So when only an agent's instructions changed,
the lead starts it, or resumes it with SendMessage, with a brief or message that has it read its file
(`.claude/agents/<name>.md`) from disk first and follow it. A change of its tools, model, preloaded skills or effort
takes a new agent, started after the user's next message, and the lead tells the user so in one line.
An edited skill's text, unlike an agent file, reaches an agent that preloads it (`skills:`) started in the same
turn: a marker line added to `live-check` was in a runner's context, quoted without a tool call (measured
2026-11-20). AGENTS.md reaches an agent as
the session last loaded it, not as edited since: three reviewers got the text from before the session's latest
edits, which a compaction had loaded (measured 2026-11-19). After editing AGENTS.md, put what a new rule says in the
brief of the agents started before the session loads it again.
