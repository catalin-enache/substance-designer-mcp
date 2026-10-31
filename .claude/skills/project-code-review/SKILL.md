---
name: project-code-review
description: Use when asked to review this repository (the whole project or an area of it) and record the findings in REVIEW.md. Covers splitting the review by area, verifying findings, and writing them in the template's format (severity sections, one checkbox entry each, appended, never replacing earlier findings). Fixing findings is the address-review skill.
---

# Project code review

Findings live in `REVIEW.md` in the repo root, tracked in git. Its format is
[TEMPLATE.md](TEMPLATE.md) in this folder: read it before writing anything. The built-in
`code-review` skill reviews a diff (uncommitted changes, a branch, a PR); use this skill for a
review of code that isn't a diff, and whenever findings are to be recorded in `REVIEW.md`.

## Scope

- **"This branch against main"** (or any branch against another) means **only the diff**:
  `git diff main...<branch>`, the changed lines and what they directly affect. Give reviewers the
  diff hunks, not whole files to sweep for unrelated issues, and re-assess (step 2) only the
  REVIEW.md resolutions whose fix is in that diff.
- **A whole-project review**, or an area of it, only when the user asks for that.

## REVIEW.md: append or create

- **If `REVIEW.md` exists:** keep everything in it. Append each new finding at the end of the
  severity section it belongs to (High, Medium-high, Medium, Low-medium, Low), add an entry to
  the review log and update the status table. Never delete, reorder or rewrite existing entries.
- **If it doesn't exist:** create it from [TEMPLATE.md](TEMPLATE.md) (keep the explanations and
  the five severity sections, drop the example entries), then add the findings the same way.

## Reviewing

1. **Read the existing `REVIEW.md` first**, if there is one, before reviewing any code. If it
   doesn't exist, create it from TEMPLATE.md (keep the explanations, drop the example entries).
   Otherwise read every entry, open and resolved, and note down for yourself what is already
   known, so nothing is reported twice:
   - each finding: its ID, title and location, whether it is open or resolved, and for resolved
     ones how (done, and the cause and fix; not a bug or not reproduced, and why not);
   - the last number used for each ID prefix;
   - the review log's "checked and found fine" notes, which needn't be redone.
   Use these notes when judging findings:
   - **Open** finding seen again: not a new entry; at most a note under the existing one if
     there is something new to add (another scenario, a better location).
   - **Done** finding: report it only if the bug is back (a regression), as a new entry that
     names the old ID and what brought it back.
   - **Not a bug / not reproduced** finding: don't report it again unless there is new evidence
     that answers its "why not"; then a new entry that names the old ID and the evidence.
2. **Assess the resolved entries in scope** (all of them for a whole-project review; for a branch, those whose fix is in the diff): does each resolution hold up?
   - **Done:** does the fix address the cause it names, or only the symptom? Read the code at the
     fix and check that the test it names exists, would fail without the fix, and passes now. Is
     the fix reasonable in scope (not too broad, nothing it should also have covered left out)?
   - **Not a bug / not reproduced:** is the "why not" convincing, and is its evidence still true
     of the current code (the guard test still there and passing, the behaviour it relies on
     unchanged)?
   - **Won't fix:** does the reason still apply?
   If a resolution isn't satisfactory, don't uncheck or rewrite the old entry: add a new finding
   (next free ID, in the severity it deserves) that names the old ID and says what is wrong with
   the resolution, and add one line under the old entry: "Questioned by <new ID> (<date>)". Give
   the reviewers these assessments too, so they look at the questioned fixes. Follow-up findings
   have their own rules: see **Follow-up chains** below.
3. **Split the work by area** and give each reviewer (a subagent, read-only) one area: the files
   to read in full, AGENTS.md as context, what to look for (correctness, data safety, security,
   misreported results, docs that contradict the code), and the report format: severity, file and
   line, one-sentence defect, concrete scenario, suggested fix, confidence. Reviewers must quote
   the code for every finding and drop what they can't support. Give each reviewer the notes from
   steps 1 and 2 for its area (known findings with their status and resolution, and what was found
   fine), with the same rules, so they don't report them again.
4. **Verify** at least the most severe finding of each area against the code yourself, and mark
   those "verified by hand". Merge duplicates (one entry; mention that two reviewers found it),
   and check every finding against the notes from steps 1 and 2 once more before writing it.
5. **Write** each new finding as one entry in its severity section, after the entries already
   there, using the next free ID for its area. Five severities, from high to low: **High,
   Medium-high, Medium, Low-medium, Low**. Never delete, reorder or rewrite existing entries; if a
   new finding changes the picture of an old one, add a note under the old entry.
6. **Log the review**: append an entry to the review log (date, scope, commit, how, resolutions
   assessed and which were questioned, findings added, suggested order, simplifications, what was
   checked and found fine), and update the
   status table.
7. Report the totals and the most severe new findings to the user; the file has the rest.

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
