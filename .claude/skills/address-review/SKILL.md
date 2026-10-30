---
name: address-review
description: Use when asked to fix, address or work through findings in REVIEW.md (one entry, a group, or "the next items"). Each finding is handled test first: a test that fails and so confirms the bug, then the fix, then the test passing; a finding whose test passes without a fix is answered as false. Either way the entry is checked off in REVIEW.md with a resolution line.
---

# Addressing review findings

`REVIEW.md` (repo root, tracked in git) holds the findings; its format is the `project-code-review`
skill's `TEMPLATE.md`. This skill is how to resolve them. The test-first rule itself is in
AGENTS.md ("Fix issues test first"); this is the procedure.

## Pick the work

- Take the entries the user names, or the open ones in the review log's suggested order, most
  severe first. Group related entries (same file, same cause) and handle them one by one.
- Read each entry, and the code at its location, before writing anything. The location may have
  moved since the review; find it by the quoted code.

## For each finding

1. **Reproduce it with a test that fails.**
   - Pure-Python logic (server, installer, CLI, test infrastructure): a unit test in `tests/unit`.
   - Anything that depends on Designer (helpers, plugin behaviour inside Designer, sd API facts):
     a check in the live self-test (`tests/test_all_tools.py`), even when a unit test also covers
     it. A unit test can take a path Designer never does.
   - Run it and **read the failure**. It must fail *because of the bug*: compare the failure with
     the entry's scenario. A test that fails for another reason (a typo, a broken query, a wrong
     fixture) proves nothing. Fix the test, run it again, and if in doubt run it against the old
     code once more (`git stash push <file>`, run, `git stash pop`).
2. **If the test passes before any change, the finding is false** (not a bug, or not
   reproducible). Don't change the code to "fix" it:
   - keep the test as a guard;
   - write down why it doesn't happen, with the evidence (the passing test, the docs or
     behaviour that explain it);
   - resolve the entry as *not a bug* or *not reproduced* and check it.
   If the code path is real but can't be triggered, a small defensive change is fine; say so.
3. **Fix the code**, as small as it can be, in the style of the code around it.
4. **Run the test again: it must pass.** Then run both suites in full, since a fix can break
   something else:
   - `mcp_server/venv/bin/python -m pytest` (unit tests);
   - `mcp_server/venv/bin/python tests/test_all_tools.py` (live self-test).
   Plugin changes only reach Designer after `install.py` and a Designer restart; ask the user
   before restarting (`quit_designer`, `launch_designer`).
5. **Update the docs** the change touches, as AGENTS.md's "Keeping the docs current" table says:
   tool docstrings, AGENTS.md facts, README.md.
6. **Mark the entry in `REVIEW.md`:**
   - check its box: `- [ ]` becomes `- [x]`;
   - add a resolution under it: **Resolution: done**, *not a bug*, *not reproduced* or *won't
     fix*, then the commit (`uncommitted on <branch>` until it is committed). It answers:
     - **Test:** which test reproduced it (or showed it doesn't happen), and how it failed;
     - **Cause** (when fixed): why the code failed, the root cause rather than the symptom (for
       example "each value was set right after it was checked, so a bad later value left the
       earlier ones changed");
     - **Fix** (when fixed): how it was fixed, what changed and where;
     - **Why not** (when false): why it doesn't happen, with the evidence;
   - update the status table (open and resolved counts per severity).
   *Won't fix* needs the user's agreement; ask before using it.

## After a group

- Report to the user per finding: the test, how it failed, the fix, and the result; say plainly
  which findings were false and why.
- Commit only when the user asks (AGENTS.md), with `REVIEW.md` in the same commit as the fixes
  it records. A commit can't contain its own hash, so the resolutions say "uncommitted on
  `<branch>`" until then; afterwards replace that with the hash, and commit the updated
  `REVIEW.md` with the next change (or on its own, if the user asks).
- New problems found along the way go into `REVIEW.md` as new entries (the `project-code-review`
  skill's rules: append, next free ID), not silently fixed.
