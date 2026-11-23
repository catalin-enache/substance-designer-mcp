---
name: project-code-review
description: Use to review this repository and record the findings in REVIEW.md, after a step of the lead's loop, or a group of small steps (the `delegate` skill), or when the user asks for a review of the whole project or an area of it. Covers splitting the review by area, verifying findings, and writing them in the template's format (severity sections, one checkbox entry each, appended, never replacing earlier findings). Fixing findings is the address-review skill.
---

# Project code review

Findings live in `REVIEW.md` in the repo root, tracked in git. Its format is
[TEMPLATE.md](TEMPLATE.md) in this folder: read it before writing anything. The built-in
`code-review` skill reviews a diff (uncommitted changes, a branch, a PR); use this skill for a
review of code that isn't a diff, and whenever findings are to be recorded in `REVIEW.md`.

`REVIEW.md` is the **memory per branch**: the lead writes it from the reviewers' and the developer's reports, as in a
PR review, so it usually lasts as long as a branch. `DECISIONS.md` is the memory for the whole project.

**A review runs no tests,** neither the unit tests nor the live self-test: reviewers read the code and the tests and
assess them. Tests are run by the agent that changes the code and, for the final check, by the `runner` agent, at the
points AGENTS.md (Running the tests) sets. A review
through the built-in `/code-review` runs none either, and when its findings are to be recorded, suspicions it can't
settle by reading are settled as in step 4 before anything goes in `REVIEW.md`.
Whether a test fails without its fix and passes with it is judged by reading it, or, where reading can't settle it,
with a scratch probe (below); never by running the test.

**Every finding is settled before it is written, none recorded as a guess.** Reviewer subagents only report
suspicions: they read, quote the code and say what would settle each one, and they don't probe Designer. The lead agent
(the one running this skill) assesses every report and settles each suspicion as right or wrong, by reading the code,
or, where reading can't settle it (whether a defect bites in Designer, whether a test or a fix holds up there), with a
**scratch probe**: temporary code written for it, run in Designer (**Who settles what** says who writes and runs it).
Only suspicions settled as right go in `REVIEW.md`.
Reviewers don't probe: the lead agent settles every suspicion anyway, so it would have to read each reviewer's probe
closely and often run it again (ROADMAP item 48, won't do). Probes sharing a Designer get in each other's way: a cancel
drops every queued job, graphs with the same name are refused as ambiguous, one probe's leftovers change what another
measures, and a crash or a quit ends everyone's work. So a Designer runs one probe at a time. On macOS, a review's
probes may be split across runners, each with a port and a Designer of its own, as the self-test's pool runs its
categories (the user, 2026-11-19).
**Who settles what** (the user, 2026-11-19). In a review, this list decides who probes, over AGENTS.md's
"Keep it yourself":

- **The lead agent keeps the judgment:** whether a suspicion is a defect, its severity, and whether DECISIONS.md
  settles it. It reads the lines each suspicion quotes itself.
- **It also keeps the probes only the main session can run:** what its hooks do, what its own tools return to it,
  such as Read's output or a TaskStop, and what a subagent is given or can do. Only the lead can start an agent for
  such a probe: the runner has no Agent tool.
- **Every other probe goes to the `runner` agent,** gathered in one brief per runner (the `delegate` skill, Which
  agent for what). The
  lead writes each probe or gives its outline: what to build, what to measure, which result settles it. Each Designer
  runs one probe at a time (above). The runner returns the code of each probe it wrote from an outline,
  with what each probe measured. The lead reads that code, then what it measured, before settling the suspicion: the
  reason reviewers don't probe applies to the runner's probes too.
- **The developer settles nothing here.** When it addresses a finding, its failing test checks the finding again
  (the `address-review` skill, step 2). A new problem it reports is settled as a reviewer's suspicion is. If the lead
  and the developer disagree, they debate it (SendMessage), then the lead writes it or rejects it.

**How a probe runs,** whoever runs it, is in the `live-check` skill, which the runner loads.

**Not verified is only for what can't be checked here,** never a way around a probe. If a scratch probe could check a
suspicion, the lead agent has it run (**Who settles what**): the suspicion becomes a finding or is dropped. Only when a limitation makes that
impossible (another OS, a race that won't reproduce on demand, hardware or a Designer version that isn't here) does it
go in the review log's entry under **Not verified**, not in a section of findings: the suspicion, what was tried, the
limitation, and what would check it. Code that is long or tedious to probe is not a limitation.

## Scope

- **A round of the lead's loop** reviews the change since the last review. The lead commits before each review, so
  the round's diff runs between two commits: `git diff <last> <this> -- . ':(exclude)PLAN.md'`, from the commit the
  last review saw to the one made for this review. The review log's **Scope** names both (TEMPLATE.md). The lead may
  group small consecutive steps of PLAN.md into one review, so that a review is neither bloated nor trivially small:
  it judges the size (the user, 2026-11-19).
- **"This branch against main"** (or any branch against another) means **only the diff**:
  `git diff main...<branch> -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`, the changed lines and what they directly
  affect. With the branch checked out,
  `git diff $(git merge-base main HEAD) -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'` and `git status --short` add
  its uncommitted work and new files. REVIEW.md is read as the record (step 1), not as a change: in the whole
  branch's diff it would be the whole file. A round's diff keeps it, as its newly checked entries are the resolutions
  step 2 rechecks.
- Either way, each reviewer's brief names the command that prints its diff, and the reviewer reads the diff from it:
  no pasted hunks, and no whole files to sweep for unrelated issues. Every diff command leaves PLAN.md out, and a
  PLAN.md that `git status --short` lists is never read (`.claude/agents/reviewer.md`, Review blind). Only the
  REVIEW.md resolutions whose fix is in that diff are rechecked (step 2).
- **A whole-project review**, or an area of it, only when the user asks for that.

## REVIEW.md: append or create

- **If `REVIEW.md` exists:** keep everything in it. Append each new finding at the end of the
  severity section it belongs to (High, Medium-high, Medium, Low-medium, Low), add an entry to
  the review log and the round's rows to the table under `## Reviews by model` (step 6), and update the status table
  and the header's **Last used**. Never delete, reorder or rewrite existing entries. Only
  the user starts a cleanup of `REVIEW.md`, by asking for one explicitly (the `cleanup-review` skill);
  never truncate it on your own.
- **If it doesn't exist:** create it from [TEMPLATE.md](TEMPLATE.md) (keep the explanations and
  the five severity sections, drop the example entries), restore its **Last used** from git history
  (**Numbering a new finding**), then add the findings the same way.

Each finding is one entry starting with a checkbox: unchecked while open, checked once fixed or answered (not a bug,
not reproducible, won't fix, moved to ROADMAP.md), with a resolution line giving the evidence, and no commit hash
(branches are squashed into main).

## Findings no longer in REVIEW.md

An ID cited in code, tests or docs but missing from `REVIEW.md` was usually removed by a cleanup. That alone isn't a
dangling reference, so don't report it. When you need the entry, run `python3 scripts/review_lookup.py HLP-56`, from
any folder of the repo. It prints the entry whether it is still in the file or was removed. If it can't, it says why:
the ID never existed, a squash lost it, or the clone is shallow. `.claude/agents/reviewer.md` (Before reviewing) says
what a reviewer reports of that, and of an old resolution's commit hash that no longer resolves. New resolutions
record no commit hash, because branches are squashed into main.

## Numbering a new finding

The **Last used** line in `REVIEW.md`'s header holds the last number for each prefix. Take the next one for the
finding's area, and update that line in the same edit as the entry. A new prefix starts at 1 and is added to
the header's **IDs** and to that line. Go by the line, not by the entries: a cleanup removes most of them, and a
reused number would make the lookup above return the wrong entry. Only adding a finding raises the line, and a cleanup
leaves it as it is. Nothing lowers a committed number; dropping a finding before committing it undoes its change.
`tests/unit/test_review_lookup.py` fails unless the line equals the highest number ever used for each prefix: in
the file, or in its git history as an entry or on this line.

**Two branches can pick the same number.** Both edit that one line, so the branch that merges second gets a git conflict,
even for different prefixes. That branch recalculates: it goes on from the counters merged in main, renumbers the
findings it added, and adjusts every reference to them, in `REVIEW.md`, code, tests and docs. Main's findings keep
their numbers. A reference may use the same ID as one of main's for a different finding, so take the ones to change
from what this branch added, before merging main: `git diff main...HEAD`.

**If `REVIEW.md` is missing,** a new file from the template starts every counter at 0, and going on from there would
reuse numbers. Before writing any finding, run `python3 scripts/review_lookup.py --last-used` and put what it prints in
the new file's **Last used**; a prefix it leaves out stays at 0. Only what was committed counts. In a shallow clone it
refuses, because the history isn't there, so stop and tell the user. That test file also fails while `REVIEW.md` is
missing, which says the file has to come back.

## Reviewing

**Read `DECISIONS.md` (repo root) first, then `REVIEW.md`.** `DECISIONS.md` holds what is settled for the whole
project. A finding that contradicts an entry there isn't reported unless the entry's **Reopen if** holds; then it is
a new finding that names the decision by its title and gives the evidence. Name any finding dropped this way in one
line of the review log, with the decision's title. An answer in `REVIEW.md` can be questioned (step 2); an entry in
`DECISIONS.md` can't, beyond its **Reopen if**. A review never edits or removes a decision on its own (**Resolving**, below).

1. **The reviewers read the existing `REVIEW.md`** before reviewing any code, so that nothing is reported twice, as
   their rules say (`.claude/agents/reviewer.md`, Before reviewing). If it doesn't exist, the lead creates it first, as
   **REVIEW.md: append or create** says, with its counters restored.
2. **The reviewers recheck the resolved entries in scope** by reading (all of them for a whole-project review; for a
   branch or a round, those whose fix is in the diff), as their rules say (`.claude/agents/reviewer.md`, Rechecking a
   resolution), and the lead settles what they report as in step 4. If a resolution isn't satisfactory, don't uncheck
   or rewrite the old entry: add a new finding (next free ID, in the severity it deserves) that names the old ID and
   says what is wrong with the resolution, and add one line under the old entry, if it is still in the file:
   `Questioned by <new ID> (<date>)`. Follow-up findings have their own rules: see **Follow-up chains** below.
3. **Split the work by area** and start one reviewer per area as the `reviewer` agent. Its file,
   `.claude/agents/reviewer.md`, holds its tools and its own rules: that it only reads, what it may run, what it reads
   first, what it looks for, how it rechecks a resolution, rates a finding and marks a follow-up's generation, and how
   it reports. The brief doesn't send it to this skill. Give each reviewer:
   - its area: the files to read in full, or for a branch or a round the command that prints its diff (**Scope**);
   - for a step of PLAN.md, or a group of steps, each step's text as the user approved it, taken from the first commit
     of PLAN.md that holds it, and quoted whole and word for word. PLAN.md changes after the approval, and the lead's
     notes join the step there. The user's later instructions that change a step join it, each quoted word for word
     with its date. Where two texts differ, the later one stands. The brief gives the user's approved text and later
     instructions, never the lead's account or its view of how well it was done. The reviewer still never opens PLAN.md, which holds that account and the decisions the lead
     took alone. A step that does less than its text promises is a finding like any other, which the lead settles
     (step 4);
   - `mcp_server/GUIDE.md` as context. AGENTS.md is loaded for it already: the brief adds only what the `delegate`
     skill says;
   - what to look for beyond its rules, if anything;
   - the findings in its area, by ID, whose resolutions it rechecks (step 2), and the review log's notes on what was
     found fine, settled as wrong or named not worth a fix, so it doesn't report them again;
   - the generation of each finding that questions a resolution (**Follow-up chains**).
4. **Settle every suspicion yourself** (**Every finding is settled before it is written**, above), the developer's
   new problems included (**Who settles what**): read the lines each one quotes; probe those reading can't settle, as
   **Who settles what** says. Mark each finding *confirmed* or *measured*, drop the ones settled as wrong (the review log's entry says
   which, and why), and put the ones a limitation keeps from being checked under **Not verified**. A real suspicion
   that is a very unlikely case whose fix needs complex code isn't written as a finding: the review log names it as not
   worth a fix (AGENTS.md, Keep it simple). Merge duplicates
   into one entry, its title line naming both reviewers and their models, and check every finding against
   `DECISIONS.md` and the `REVIEW.md` entries it touches once more before writing it.
5. **Write** each new finding as one entry in its severity section, after the entries already
   there, using the next free ID for its area (**Numbering a new finding**). Five severities, from high to low: **High,
   Medium-high, Medium, Low-medium, Low**. Its title line ends with who found it and the model that agent ran on
   (TEMPLATE.md, **Found by.**): a reviewer; for a new problem, the developer, or the runner whose probe found it; or
   the lead itself. Never delete, reorder or rewrite existing entries; if a
   new finding changes the picture of an old one, add a note under the old entry.
6. **Log the review**: append an entry to the review log (date, scope, how, resolutions
   assessed and which were questioned, findings added, suggested order, simplifications, what was
   checked and found fine), add the round's rows to the table under `## Reviews by model`, and update its **Total** row
   (TEMPLATE.md; the user, 2026-11-20). Then update the status table.
7. **Go on with the loop** (the `delegate` skill, The loop is the lead's): give the new findings to the developer, then review
   its fixes, without asking the user. What counts is the findings, not the number of review rounds. A few Low
   findings is about 5 to 7 at most. The reviews run in this flow (the user, 2026-11-20):
   - **For each step, or group of small steps:** the developer implements it, and a Sonnet round reviews the step's
     diff, every reviewer on its file's model. The developer fixes the findings, and a Sonnet round reviews the fixes,
     until a Sonnet round's new findings are only a few Low ones, or none. The developer fixes those few. The step's
     reviews are then done, and the loop goes on with the next step.
   - **After the last step:** an Opus round, the lead passing `model: opus` on each Agent call, reviews "the entire
     branch diff against main". When it finds more than a few Low ones, or any above Low, the developer fixes them,
     and Opus rounds review the fixes until one finds only a few Low ones, or none, which the developer fixes. Then an
     Opus round reviews the entire branch again. When that round finds more than a few Low ones, or any above Low, the
     Opus rounds on its fixes run again, then a round of the entire branch.
   - **The reviews converge** when an Opus round of the entire branch finds only a few Low ones, or none, the first
     such round included: a review whose new findings are only a few Low ones, the first review included, says the
     reviews look converged, and so does a review with no findings (the user, 2026-11-19). The developer fixes those
     few. Then the lead tells the user the reviews converged, with the totals and the most severe findings, and from
     PLAN.md the decisions waiting and those it took alone, which the user agrees with or not. It also recaps the won't
     fixes the user agreed during the loop, and the findings they moved to ROADMAP.md: each was asked at once (the
     `address-review` skill, step 7), so none is still open.

   The user decides: another round, or the final check (AGENTS.md, Running the tests) and then the squash merge.
8. **Propose to the user** what the review brings up for later and for good, in the report saying the reviews look
   converged, or at once when the next step needs it (the `delegate` skill, The loop is the lead's). Until then it
   waits in PLAN.md, Waiting for the user:
   - a `ROADMAP.md` item for each simplification or follow-up worth doing later that the branch can't take on (the
     `delegate` skill, What looks like a ROADMAP proposal). A leftover in the branch's own code is fixed in the branch
     instead (the `delegate` skill, The loop is the lead's);
   - a `DECISIONS.md` entry only for a decision of the user's that would stop reviewers raising the same finding
     again, never for a false finding (the `address-review` skill, Recording decisions);
   - the reviewers' **Unspecified** items, what no doc decides (`.claude/agents/reviewer.md`): the user decides each,
     or leaves it open. The review log lists them.

   Add each once the user approves it. A cleanup of `REVIEW.md` moves nothing to either file (the `cleanup-review`
   skill), so this is the time.

## Follow-up chains

A finding that questions a resolution starts or extends a chain, and why chains grow is in the reviewer's rules
(`.claude/agents/reviewer.md`, Follow-up chains). Before 2a107b3, the seed chain HLP-22 → HLP-24 → HLP-25 → TST-39 →
TST-40 → TST-44 → TST-48 ran seven generations, and the library-refusal message HLP-10 → HLP-14 → HLP-18 → HLP-20 →
TST-26 → TST-27 ran six. So those rules mark each such finding with its generation, and limit what a late one's fix
may do. The lead settles and writes what the reviewers report by those rules:

- the mark in the finding's title line (TEMPLATE.md), and its **Fix** within what its generation allows, saying so;
- a leftover in a test that no later check depends on as a note under the entry whose fix added that test
  (`Note (<date>): ...`), mentioned in the review log, never as an entry. Notes aren't open work;
- in the review log, the longest chain still growing and its generation, so the user can see whether reviews are
  converging.

## Resolving

Fixing or answering findings is the `address-review` skill (`.claude/skills/address-review/`):
test first, then the fix, which the developer reports. The lead assesses each reported resolution as it settles a new
problem (step 4). Once its evidence holds, the lead writes the resolution line, checks the entry off and updates the
status table. After each developer run, the lead adds its row to the table under `## Reviews by model` and updates
the **Total** row (TEMPLATE.md, Reviews by model). A resolution whose evidence doesn't hold goes back to the developer.
The next review rechecks it (step 2).

When the user decides on a finding during a review, or you ask them to, record it in `DECISIONS.md` as
that skill's **Recording decisions** says.
