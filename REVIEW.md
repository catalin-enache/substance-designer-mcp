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

**Last used:** PLG-45, SRV-186, HLP-224, INS-46, TST-694, AGT-124.

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
| Low-medium | 0 | 0 |
| Low | 0 | 2 |
| **Total** | **0** | **2** |

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
| 2026-11-21, item 38's step (parameter descriptions) | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 331,208 | 22 min |
| 2026-11-21, the review of the whole branch | Opus | 1 | 1 [1 Low] | 1 [1 Low] | 184,998 | 11 min |
| 2026-11-21, the review's fixes (AGT-124), and the descriptions' indentation | Opus (developer) | 1 | 0 | 0 | 154,555 | 8 min |
| **Total** | | **3** | **2 [2 Low]** | **2 [2 Low]** | **670,761** | **41 min** |

## Review log

### 2026-11-21: the parameter-descriptions branch, the whole branch against main

- **Scope:** `git diff main...5636d56 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`: ROADMAP item 38's step, the
  four temporary-node reads' hints, and ROADMAP items 9 and 115.
- **How:** one Opus reviewer, the claim being the step's text as the user approved it and the user's words of
  2026-11-21 on the hints and on items 9 and 115, told to report only what has real value. The lead chose one round
  for the whole branch, the step being the branch. No tests run; all settled by reading.
- **Findings:** TST-694, Low, in the lead's ROADMAP text, fixed by the lead. AGT-124's pattern in two more places, a
  note under it.
- **Not a finding:** item 38's own row still gives its old approach; the lead checks it with a Done note before the
  final check.
- **Checked and found fine:** every split kept its meaning, rules across parameters staying in the docstrings; the
  new texts against the code (`max_size`, `tile_size`, `lines`, `limit`, `file_format`, `name`, `port`, `spacing`);
  the shared `Graph`, `Output` and `Port`; the two new tests read the real listing; `_PINNED`; the four reads' hints
  and `_tool()`'s note; the docs.
- **Converged:** one Low finding, the first Opus round of the whole branch.

---

## High

## Medium-high

## Medium

## Low-medium

## Low

- [x] **AGT-124 · The developer's triage names a tool's docstring but not its parameters' descriptions** · `.claude/agents/developer.md` (the list of layers a unit touches) · confirmed · found 2026-11-21 by the developer (Opus)
  - **Defect.** "the tool, in `mcp_server/server_tools/`, and its docstring;": a parameter's meaning is now in its
    annotation's `Field(description=...)` (`.claude/rules/docs.md`, the table), which the line doesn't name.
  - **Scenario.** A developer triaging a change of a parameter lists the docstring only, and leaves the parameter's
    description stale.
  - **Fix.** Name the parameters' descriptions beside the docstring.
  - Note (2026-11-21): the same list, naming docstrings only, is in `.claude/skills/address-review/SKILL.md`
    (step 5: "tool docstrings, GUIDE.md facts, README.md") and `.claude/agents/developer.md` ("the modules'
    docstrings"), found by a reviewer (Opus). The fix covers all three.
  - **Resolution: done**, by the developer: `developer.md`'s triage names "its docstring and its parameters'
    descriptions", its docs line "the parameters' descriptions", and `address-review`'s step 5 "tool docstrings and
    parameters' descriptions". **Also covered:** `git grep -i docstring` over `.claude` and `docs`, and "its
    docstring", "tool docstrings", "tool's docstring" in README.md, AGENTS.md, GUIDE.md and ROADMAP.md. The same list
    was in `reviewer.md`, Cite the authority, and in `address-review`'s step 6, both fixed. Where Designer facts go
    (`analyst.md`, `address-review`, `live-check`) is another list, left as it is.

- [x] **TST-694 · ROADMAP item 9 says a tool of its own costs only the sessions that use it, true only with tool search** · ROADMAP.md, item 9 · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "a tool of its own costs only the sessions that use it": when tools load at the session's start, every
    tool's description costs every session.
  - **Fix.** Narrow the sentence to tool search.
  - **Resolution: done**, by the lead: "when tools load through tool search, Claude Code's default on current models".
