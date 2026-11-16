---
name: cleanup-review
description: Use only when the user explicitly asks to clean up or truncate REVIEW.md. Removes resolved findings and old review log entries so the file stops costing context, and keeps every removed finding findable in git history. It moves nothing to DECISIONS.md or ROADMAP.md. Never run it on your own initiative or as part of a review or a fix.
---

# Cleaning up REVIEW.md

`REVIEW.md` is the memory per branch, where reviewers and the agents addressing findings talk to each other.
`DECISIONS.md` is the memory for the whole project. A cleanup usually comes once the branch is merged and no further
reviews are needed, with every finding addressed, questioned ones included. Git history becomes the archive. The
rule in AGENTS.md still stands: **only the user starts a cleanup, by asking for one explicitly.** A large file is no
reason to start one; you may mention its size.

A cleanup moves nothing to `DECISIONS.md` or `ROADMAP.md`. What belongs in either was proposed to the user, and added
once they approved it, during the reviews and while the findings were addressed (the `project-code-review` and
`address-review` skills). A cleanup only removes.

`scripts/review_lookup.py` reads the current file first. For a finding not there, it finds the newest commit that
added or removed it, which is the cleanup, and reads the commit before that. So a removed finding stays findable only
if that earlier commit, on main, has it. The steps below protect that.

## Before removing anything

1. **Check that every finding is committed on main.** `git status --short REVIEW.md` must print nothing, and
   any branch that added findings must already be merged. A finding added and removed on a branch that is then
   squashed never reaches main's history, and the lookup would say it never existed. A branch holding only the
   cleanup is fine. If anything is unmerged or uncommitted, stop and tell the user.

## Removing

2. **Keep the whole header unchanged.** The header ends before `## Status`. It includes the pointer to the lookup and the
   **Last used** line (`tests/unit/test_review_lookup.py` checks both, the line against git history). New findings
   raise that line; a cleanup leaves it as it is, because a number used twice would make the lookup return the wrong entry.
3. **Remove** every checked entry with its resolution and notes, and the review log's entries. Git history keeps them. Add no log
   entry for the cleanup itself: the file would grow with every cleanup.
4. **Keep** the five severity sections, even when empty, and every open entry word for word, including its
   `follows <ID>` mark. Also keep any log entry that gives a suggested order for those open findings.
5. **Update the status table:** set every Resolved count to 0, because the table counts only what is in the file, and the
   resolved entries are gone. Open counts don't change. `tests/unit/test_review_lookup.py` checks the table against the entries.

## Leave alone

- **The IDs cited in code, tests and docs.** They stay, and the lookup resolves them. Don't rewrite them or copy
  them into an index.
- **`DECISIONS.md` and `ROADMAP.md`.**
- **Git history.** Never rebase, filter or force-push away the commits that hold the old file: they are the archive.

## Checking

6. **Before committing,** confirm that every open finding is still there, that **Last used** hasn't changed, and that every removed ID is in
   `git show HEAD:REVIEW.md`. Run the tests that validate the docs (AGENTS.md, Running the tests).
7. **Commit only if the user asks** (AGENTS.md), with only the changes to `REVIEW.md` in that commit.
   The lookup can't find a removal that isn't committed.
8. **After the commit,** run `python3 scripts/review_lookup.py <ID>` for the first and last IDs you removed, each of which
   must print its whole entry, and for an ID that never existed, which must say so. If the cleanup was on a branch,
   run these again once it is on main.
9. **Report:** the file's size before and after, the entries removed and left open, and the lookup results, or that
   they are still to run because nothing is committed yet.
