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

**Last used:** PLG-45, SRV-186, HLP-224, INS-46, TST-693, AGT-123.

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
| 2026-11-21, item 40's step (the tool annotations) | Opus (developer) | 1 | 0 | 0 | 161,497 | 8 min |
| 2026-11-21, the review of the whole branch | Opus | 1 | 2 [2 Low] | 2 [2 Low] | 157,367 | 9 min |
| **Total** | | **2** | **2 [2 Low]** | **2 [2 Low]** | **318,864** | **17 min** |

## Review log

### 2026-11-21: the tool-annotations branch, the whole branch against main

- **Scope:** `git diff main...9557376 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`: ROADMAP item 40, the step and
  the branch alike.
- **How:** one Opus reviewer, the claim being item 40's text and the user's words of 2026-11-21, told to report only
  what has real value (the user, 2026-11-21, against over-complicating). The lead chose one round for the whole branch,
  the step being the branch. No tests run; all settled by reading.
- **Findings:** SRV-185, SRV-186, Low, both in the lead's texts, fixed by the lead. Every hint matched the tool's code.
- **Dropped, of low value:** the four temporary-node reads' clause leaves out the modified flag, which DECISIONS.md,
  Library packages, records for a library graph only, and no live check measures it on a user's package: a clause
  claiming it would need one, for a case a user rarely meets. `HINTS`' type allows None, which its own check already
  refuses.
- **Checked and found fine:** a tool can't be registered without hints unnoticed (required keywords; a bare
  `server.tool()` reads None); all 35 decorators match `HINTS`; the docstring clause matches `_with_node_texture`;
  the ROADMAP rows' e3e7823 holds the same code as the run's commit.

---

## High

## Medium-high

## Medium

## Low-medium

## Low

- [x] **SRV-185 · The two code tools say `open_world=True`, against item 40's "False throughout", and nothing records why** · `mcp_server/server_tools/scripting.py` (`execute_designer_code`, `run_designer_script`); DECISIONS.md, Tool annotations · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** The item says `openWorldHint=False` throughout, as the server talks only to the local Designer; the
    lead set True on the two code tools, as their code can reach anything, but DECISIONS.md's entry and `_tool`'s
    docstring ("which judge the user's work") don't say so.
  - **Fix.** Record the reason where the hints are decided.
  - **Resolution: done**, by the lead: DECISIONS.md's entry says `openWorldHint` is False except on the two code
    tools, and why; `_tool`'s docstring now points at the entry without saying what the hints judge.

- [x] **SRV-186 · DECISIONS.md's reading of read-only would make `open_graph` and `screenshot_designer` read-only** · DECISIONS.md, Tool annotations · confirmed · found 2026-11-21 by a reviewer (Opus)
  - **Defect.** "`readOnlyHint` marks a tool that leaves the user's graphs, packages and files as they were": both
    tools do, changing only the editor's graph, the view or the clipboard, yet the table marks them not read-only.
  - **Scenario.** An agent adding a tool that only moves a view follows the sentence and marks it read-only.
  - **Fix.** Say a read-only tool also changes nothing else a user sees.
  - **Resolution: done**, by the lead: "and changes nothing else a user sees, such as Designer's view, the editor's
    current graph or the clipboard".
