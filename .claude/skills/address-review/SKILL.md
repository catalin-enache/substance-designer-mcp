---
name: address-review
description: 'Use when asked to fix, address or work through findings in REVIEW.md (one entry, a group, or "the next items"), or when the user decides on a finding. Each finding is handled test first: a test that fails and so confirms the bug, then the fix, then the test passing; a finding whose test passes without a fix is answered as false. Either way the entry is checked off in REVIEW.md with a resolution line; what the user decides, if a reviewer could raise it again, goes in DECISIONS.md.'
---

# Addressing review findings

`REVIEW.md` (repo root, tracked in git) holds the findings; its format is the `project-code-review`
skill's `TEMPLATE.md`. This skill is how to resolve them. The test-first rule itself is in
AGENTS.md ("Fix issues test first"); this is the procedure. `REVIEW.md` is the memory per branch: agents that review
and agents that address findings talk through it, as in a PR review.

## Pick the work

- **Read `DECISIONS.md` (repo root) first:** it holds what is already settled. If a finding or its fix
  goes against an entry, don't make the change: tell the user which decision it contradicts, with the evidence if its
  **Reopen if** now holds, and ask.
- An ID cited somewhere but missing from `REVIEW.md` was usually removed by a cleanup;
  `python3 scripts/review_lookup.py <ID>` gets the entry from git.
- Take the entries the user names, or the open ones in the review log's suggested order, most
  severe first. Group related entries (same file, same cause) and handle them one by one.
- Read each entry, and the code at its location, before writing anything. The location may have
  moved since the review; find it by the quoted code.

## Show the plan first

Before changing anything, show the user the plan, one finding at a time: the finding in plain words, then how you plan
to fix or answer it. Say where a measurement could change the plan. Then wait for the user's answer, unless they have
already said to go ahead without one.

## For each finding

1. **Reproduce it with a test that fails.**
    - Pure-Python logic (server, installer, CLI, test infrastructure): a unit test in `tests/unit`.
    - Anything that depends on Designer (helpers, plugin behaviour inside Designer, sd API facts):
      a check in the live self-test (`tests/test_all_tools/`, in its category's module), even when a unit test also
      covers it. A unit test can take a path Designer never does.
    - Run it and **read the failure**. It must fail *because of the bug*: compare the failure with
      the entry's scenario. A test that fails for another reason (a typo, a broken query, a wrong
      fixture) proves nothing. Fix the test, run it again, and if in doubt run it against the old
      code once more (`git stash push <file>`, run, `git stash pop`).
2. **If the test passes before any change, the finding is false** (not a bug, or not
   reproducible). Don't change the code to "fix" it:
    - keep the test as a guard;
    - write down why it doesn't happen, with the evidence (the passing test, the docs or
      behaviour that explain it);
    - resolve the entry as *not a bug* or *not reproducible* and check it.

   If the code path is real but can't be triggered, a small defensive change is fine; say so.
3. **Fix the code**, as small as it can be, in the style of the code around it. Two things first,
   because skipping them is what made findings come back round after round (the chains in
   REVIEW.md: the seed chain HLP-22 → … ran 18 findings deep, one case per round):
    - **Measure before fixing on Designer's behaviour.** When the fix depends on how Designer
      behaves (inheritance, seeds, function graphs, shutdown, the UI), first measure every case the
      code distinguishes in one "designer facts" probe (the node and the graph, each inheritance
      mode, with and without a render override...), record the measured table in AGENTS.md, then
      write the fix for that table. Never fix the one case in the finding and leave the next case
      for the next review.
    - **Fix the pattern, not the instance.** Search for every other place with the same pattern:
      the other callers of the helper, the same check or message elsewhere, the sibling tool or
      parameter (HLP-31 fixed `'graph'` in two tools; HLP-41 later found eight more). Fix each one
      that has the defect, with its test, and list what you searched and what you found under **Also covered** in the
      resolution, so the next reviewer can see the scope.
4. **Run the test again: it must pass.** Then run both suites in full, since a fix can break
   something else (a change to docs alone runs less: AGENTS.md, Running the tests):
    - `mcp_server/venv/bin/python -m pytest` (unit tests);
    - `mcp_server/venv/bin/python tests/test_all_tools` (live self-test).
      Plugin changes only reach Designer after `install.py` and a Designer restart: `quit_designer`, `launch_designer` for one an
      agent started, and say that you did; ask the user to save, close and reopen their own (AGENTS.md, the rules).
5. **Update the docs** the change touches, as AGENTS.md's "Keeping the docs current" table says:
   tool docstrings, AGENTS.md facts, README.md. Add a new sentence only when an agent or a user
   needs it to act, and make it say exactly what its check measures, no more. Every claim is
   something the next review audits against its test: a third of the links in REVIEW.md's
   chains were "the sentence says more than the check".
6. **Review your own fix as a reviewer would, and repeat until nothing is left.** Before calling
   the finding done, step back and read the whole change (code, test, docs) as the next review
   will, not as its author. Things the reviews here kept finding in fixes that were "done":
    - the fix covers the case in the finding but not its neighbours (the node as well as the graph,
      the other parameter, the other code path, the same unguarded pattern a few lines away);
    - the test passes without the fix: state an earlier check left, a value that was already there,
      a comparison that any rule would satisfy, hashes of data that differs run to run;
    - the test leaves state behind for later checks, or cleans up only when every step succeeds (no `finally`);
    - an older test no longer guards what it was written for, because the fix changed the order;
    - a comment, docstring, AGENTS.md or README.md sentence the fix made untrue, a name or path in DECISIONS.md it made stale, or a new
      sentence that claims more than the test measures.
      Adjust what you find, then step back and review the adjusted change the same way, again and
      again, until a fresh look finds nothing a reviewer could report. Only then go on.
      When a sentence claims more than its test measures, prefer narrowing the sentence to writing a
      stronger test, unless the extra claim is something an agent needs in order to act. For an entry
      marked generation 3 or later (`project-code-review`, Follow-up chains), narrowing the claim is
      the fix. Don't add a new check for it.
7. **Mark the entry in `REVIEW.md`:**
    - check its box: `- [ ]` becomes `- [x]`;
    - add a resolution under it: **Resolution: done**, *not a bug*, *not reproducible* or *won't
      fix*. It starts with one of these wordings, and details can follow. Don't record a commit: branches are squashed into main, so a hash stops resolving. It answers:
        - **Test:** which test reproduced it (or showed it doesn't happen), and how it failed;
        - **Cause** (when fixed): why the code failed, the root cause rather than the symptom (for
          example "each value was set right after it was checked, so a bad later value left the
          earlier ones changed");
        - **Fix** (when fixed): how it was fixed, what changed and where;
        - **Also covered** (when fixed): the same pattern searched for elsewhere, where, and what
          was found (fixed too, or not affected and why);
        - **Why not** (when false): why it doesn't happen, with the evidence;
    - update the status table (open and resolved counts per severity). *Won't fix* needs the user's agreement; ask
      before using it, then record it (below).

## Recording decisions

`REVIEW.md` is the memory per branch, where reviewers can still question an answer. `DECISIONS.md` is the memory for
the whole project, where they can't, so only what is settled goes there, and only what a reviewer could plausibly
raise again:

- **What the user decides goes in now:** their answer when asked to decide on a finding, or what they say about one
  unprompted: won't fix, a rule to follow from now on, one option out of several, how something should
  work. It can come with a fix: a rule chosen over closing a finding as won't fix is both. Give the reason
  the user gave or agreed to, and the date.
- **A false finding stays in `REVIEW.md` for now:** a *not a bug* or *not reproducible* answer you reached alone, also
  when a defensive change came with it. The `cleanup-review` skill proposes the ones worth keeping, and they move
  when the user acknowledges them.

For what goes in:

- **Add it** in the same change as the `REVIEW.md` resolution, in the section it belongs to, in the format
  that file's introduction gives.
- **Names and paths are yours to keep current:** when a change renames or moves the code or test an entry points at,
  update the entry. Changing what was decided, or removing an entry, takes the user. Never leave two entries that
  contradict each other.
- **If the user gave no reopen condition,** propose one in the entry and show them the entry, so they can
  correct it.
- **An ordinary fix doesn't go in:** the code, its test and `REVIEW.md` record it.

## After a group

- Report to the user per finding: the test, how it failed, the fix, and the result; say plainly
  which findings were false and why.
- Commit only when the user asks (AGENTS.md), with `REVIEW.md` and any `DECISIONS.md` change in the same
  commit as the fixes they record.
- New problems found along the way go into `REVIEW.md` as new entries (the `project-code-review`
  skill's rules: append, the next free ID, update the header's **Last used**), not silently fixed.
