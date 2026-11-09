---
name: project-code-review
description: Use when asked to review this repository (the whole project or an area of it) and record the findings in REVIEW.md. Covers splitting the review by area, verifying findings, and writing them in the template's format (severity sections, one checkbox entry each, appended, never replacing earlier findings). Fixing findings is the address-review skill.
---

# Project code review

Findings live in `REVIEW.md` in the repo root, tracked in git. Its format is
[TEMPLATE.md](TEMPLATE.md) in this folder: read it before writing anything. The built-in
`code-review` skill reviews a diff (uncommitted changes, a branch, a PR); use this skill for a
review of code that isn't a diff, and whenever findings are to be recorded in `REVIEW.md`.

`REVIEW.md` is the **memory per branch**: reviewers and the agents addressing findings talk through it, as in a PR
review, so it usually lasts as long as a branch. `DECISIONS.md` is the memory for the whole project.

**A review runs no tests,** neither the unit tests nor the live self-test: reviewers read the code and the tests and
assess them. Tests are run only by the agent that changes the code, at the points AGENTS.md (Running the tests) sets. A review
through the built-in `/code-review` runs none either, and when its findings are to be recorded, suspicions it can't
settle by reading are settled as in step 4 before anything goes in `REVIEW.md`.
Whether a test fails without its fix and passes with it is judged by reading it, or, where reading can't settle it,
with a scratch probe (below); never by running the test.

**Every finding is settled before it is written, none recorded as a guess.** Reviewer subagents only report
suspicions: they read, quote the code and say what would settle each one, and they don't probe Designer. The lead agent
(the one running this skill) assesses every report and settles each suspicion as right or wrong, by reading the code,
or, where reading can't settle it (whether a defect bites in Designer, whether a test or a fix holds up there), with a
**scratch probe**: temporary code of its own, run in Designer. Only suspicions settled as right go in `REVIEW.md`.
Reviewers don't probe for now (ROADMAP item 48 will give each one a Designer of its own) because the tools reach a single Designer (one `SD_BRIDGE_PORT` per session), and probes
sharing it get in each other's way: a cancel drops every queued job, graphs with the same name are refused as
ambiguous, one probe's leftovers change what another measures, and a crash or a quit ends everyone's work.
- **Where it runs:** one Designer an agent started (`launch_designer`), never the user's, with the probes run one at a
  time. If the user's Designer is open, ask them to close it: a probe's leftovers or crash would land in their work.
  Close the agent's
  Designer when the review is done (GUIDE.md, the rules).
- **What it touches:** a new package of its own, with a graph name no other probe uses, unloaded at the end, never the
  user's packages; GUIDE.md's rules apply (no Undo, no hot reload of the plugin).
- **Where the code lives:** outside the repo (the session's scratchpad or a temp folder), run with
  `run_designer_script`, `execute_designer_code` or `client/sd_run.py`, and deleted afterwards. The session's own tools
  run the server and helpers as they were when the session connected: a probe of the branch's changes to
  `server_tools/` or the helpers goes through a fresh server (an MCP session of its own, as `alone.py` opens) or after
  `/mcp` reconnects. `client/sd_run.py` sends only the probe's own code.
- **Outside Designer:** a suspicion about pure-Python code that reading can't settle gets a scratch probe too, plain
  Python run from the scratchpad, with the same rules (not a test, never committed). It is not a test and is
  never committed: the agent addressing the finding writes the real test.
- **What goes in the entry:** the probe in short and what it measured, in the scenario, so the agent addressing the
  finding can start its test from it.

**Not verified is only for what can't be checked here,** never a way around a probe. If a scratch probe could check a
suspicion, the lead agent writes it and runs it: the suspicion becomes a finding or is dropped. Only when a limitation makes that
impossible (another OS, a race that won't reproduce on demand, hardware or a Designer version that isn't here) does it
go in the review log's entry under **Not verified**, not in a section of findings: the suspicion, what was tried, the
limitation, and what would check it. Code that is long or tedious to probe is not a limitation.

## Scope

- **"This branch against main"** (or any branch against another) means **only the diff**:
  `git diff main...<branch>`, the changed lines and what they directly affect. Give reviewers the
  diff hunks, not whole files to sweep for unrelated issues, and re-assess (step 2) only the
  REVIEW.md resolutions whose fix is in that diff.
- **A whole-project review**, or an area of it, only when the user asks for that.

## REVIEW.md: append or create

- **If `REVIEW.md` exists:** keep everything in it. Append each new finding at the end of the
  severity section it belongs to (High, Medium-high, Medium, Low-medium, Low), add an entry to
  the review log and update the status table and the header's **Last used**. Never delete, reorder or rewrite existing entries. Only
  the user starts a cleanup of `REVIEW.md`, by asking for one explicitly (the `cleanup-review` skill);
  never truncate it on your own.
- **If it doesn't exist:** create it from [TEMPLATE.md](TEMPLATE.md) (keep the explanations and
  the five severity sections, drop the example entries), restore its **Last used** from git history
  (**Numbering a new finding**), then add the findings the same way.

## Findings no longer in REVIEW.md

An ID cited in code, tests or docs but missing from `REVIEW.md` was usually removed by a cleanup. That alone isn't a
dangling reference, so don't report it. When you need the entry, run `python3 scripts/review_lookup.py HLP-56`, from
any folder of the repo. It prints the entry whether it is still in the file or was removed. If it can't, it says why:
the ID never existed, a squash lost it, or the clone is shallow. In a full clone, that makes the citation a broken
reference or a lost finding; say which you can tell.

An old resolution's commit hash may no longer resolve, because branches are squashed into main. That isn't a
finding either, and new resolutions don't record one.

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

1. **Read the existing `REVIEW.md`**, if there is one, before reviewing any code. If it
   doesn't exist, create it as **REVIEW.md: append or create** says, with its counters restored.
   Otherwise read every entry, open and resolved, and note down for yourself what is already
   known, so nothing is reported twice:
   - each finding: its ID, title and location, whether it is open or resolved, and for resolved
     ones how (done, and the cause and fix; not a bug or not reproducible, and why not);
   - the review log's "checked and found fine" notes, which needn't be redone.
   Use these notes when judging findings:
   - **Open** finding seen again: not a new entry; at most a note under the existing one if
     there is something new to add (another scenario, a better location).
   - **Done** finding: report it only if the bug is back (a regression), as a new entry that
     names the old ID and what brought it back.
   - **Not a bug / not reproducible** finding: don't raise the same finding again. Questioning its answer,
     with a reason or new evidence, is step 2.
2. **Assess the resolved entries in scope** (yourself, by reading, and with a scratch probe where reading can't settle
   it, as in step 4) (all of them for a whole-project review; for a branch, those whose fix is in the diff): does each resolution hold up?
   - **Done:** does the fix address the cause it names, or only the symptom? Read the code at the
     fix and check, by reading it, that the test it names exists, would fail without the fix, and would pass with it. A live
     check is seen failing and passing in the addressing agent's scratch run, which the resolution reports; don't report
     it as not yet run in the whole suite, which runs only when the user asks (DECISIONS.md, Project rules). Is
     the fix reasonable in scope (not too broad, nothing it should also have covered left out)?
     Check its **Also covered** list (address-review, step 3): a place with the same pattern that
     the list misses is the follow-up finding; one the list explains needs no new entry.
   - **Not a bug / not reproducible:** is the "why not" convincing, and is its evidence still true
     of the current code (the guard test still there and still testing it, read as above, the behaviour it relies on
     unchanged)?
   - **Won't fix:** does the reason still apply? An answer also in `DECISIONS.md` follows the next point instead.
   - **Decisions** whose code is in scope: does the entry's **Reopen if** hold now, and do the code and
     tests it names still exist? A condition that holds is a finding; a name that went stale is a Low one. Don't
     reargue the reason: that is what an answer still in `REVIEW.md` is open to, not an entry here.
   If a resolution isn't satisfactory, don't uncheck or rewrite the old entry: add a new finding
   (next free ID, in the severity it deserves) that names the old ID and says what is wrong with
   the resolution, and add one line under the old entry, if it is still in the file: "Questioned by <new ID> (<date>)". Give
   the reviewers these assessments too, so they look at the questioned fixes. Follow-up findings
   have their own rules: see **Follow-up chains** below.
3. **Split the work by area** and give each reviewer (a subagent, changing nothing in the repo) one area: the files
   to read in full, AGENTS.md and `mcp_server/GUIDE.md` as context, what to look for (correctness, data safety, security,
   misreported results, docs that contradict the code), that they run no tests and don't probe Designer (above), and the report format: severity, file and
   line, one-sentence defect, concrete scenario, suggested fix, and whether reading settles it or what would (a
   probe's outline: what to build, what to measure, what result would prove it). Reviewers must quote
   the code for every finding, and drop only what reading disproves: a suspicion reading can't settle is reported,
   with its probe's outline, never dropped for lack of proof (the lead agent settles it, step 4). A defect that recurs (the same
   pattern in several places) is **one** finding listing every location, not one finding per round:
   reviewers search for the other instances before reporting. Give each reviewer the notes from
   steps 1 and 2 for its area (known findings with their status and resolution, and what was found
   fine), with the same rules, so they don't report them again. Tell each reviewer to read
   `DECISIONS.md` and apply the rule above, and that an ID missing from `REVIEW.md` isn't a finding in
   itself (**Findings no longer in REVIEW.md**).
4. **Settle every suspicion yourself** (**Every finding is settled before it is written**, above): read the
   code at each one; probe in Designer, one at a time, those reading can't settle. Mark each finding *confirmed* or
   *measured*, drop the ones settled as wrong (the review log's entry says which, and why), and put the ones a
   limitation keeps from being checked under **Not verified**. Merge duplicates (one entry; mention that two reviewers
   found it), and check every finding against `DECISIONS.md` and the notes from steps 1 and 2 once more before
   writing it.
5. **Write** each new finding as one entry in its severity section, after the entries already
   there, using the next free ID for its area (**Numbering a new finding**). Five severities, from high to low: **High,
   Medium-high, Medium, Low-medium, Low**. Never delete, reorder or rewrite existing entries; if a
   new finding changes the picture of an old one, add a note under the old entry.
6. **Log the review**: append an entry to the review log (date, scope, how, resolutions
   assessed and which were questioned, findings added, suggested order, simplifications, what was
   checked and found fine), and update the
   status table.
7. Report the totals and the most severe new findings to the user; the file has the rest. A review that finds
   nothing new says so: the work is then ready for the final check (both suites in full), which runs only when the user
   asks for it (AGENTS.md, Running the tests).

## Follow-up chains

Every fix here adds a test and often a sentence in the docs. The next review then finds the test
weaker than the sentence, or a leftover in the test, and the fix for that adds another test and
another sentence. Left alone, this runs round after round on wording and test precision long after
the code defects are gone. Before 2a107b3, the seed chain HLP-22 → HLP-24 → HLP-25 → TST-39 →
TST-40 → TST-44 → TST-48 ran seven generations, and the library-refusal message
HLP-10 → HLP-14 → HLP-18 → HLP-20 → TST-26 → TST-27 ran six. So:

- **Mark the chain.** A finding that questions a resolution puts `follows <old ID>, generation N`
  in its title line (the old entry's own generation plus one; a finding that follows none is
  generation 1).
- **Generation 3 or later, Low or Low-medium, and only about tests or docs** (a check that measures
  less than its sentence says, a stale comment, a docstring that says too much): the suggested fix
  makes the claim smaller. Delete or narrow the sentence, or drop the extra assertion. It never
  adds a check or makes one stronger. Say so in the entry's **Fix**.
- **A leftover in a test that no later check depends on** (a temporary node, a value not put back)
  isn't an entry. Add a note under the entry whose fix added that test ("Note (<date>): ...") and
  mention it in the review log. Notes aren't open work.
- **A defect in the tools' code** (a wrong or misreported result, lost or changed user work, a
  hang, a security hole, a broken install) is always an entry, at any generation.
- In the review log, give the longest chain still growing and its generation, so the user can see
  whether reviews are converging.

## Resolving

Fixing or answering findings is the `address-review` skill (`.claude/skills/address-review/`):
test first, then the fix, then the entry checked off with a resolution line and the status table
updated.

When the user decides on a finding during a review, or you ask them to, record it in `DECISIONS.md` as
that skill's **Recording decisions** says.
