---
name: address-review
description: 'Use when asked to fix, address or work through findings in REVIEW.md (one entry, a group, or "the next items"), or when the user decides on a finding. Each finding is handled test first: a test that fails and so confirms the bug (a live self-test check in a scratch run, never the whole suite), then the fix, then the test passing; a finding whose test passes without a fix is answered as false. Either way the lead checks the entry off in REVIEW.md with the resolution reported, once its evidence holds; what the user decides, if a reviewer could raise it again, goes in DECISIONS.md.'
---

# Addressing review findings

`REVIEW.md` (repo root, tracked in git) holds the findings; its format is the `project-code-review`
skill's `TEMPLATE.md`. This skill is how to resolve them. The test-first rule itself is in
AGENTS.md ("Start with the tests, always (TDD)"); this is the procedure. `REVIEW.md` is the memory per branch: the lead
writes it from the reviewers' and the developer's reports, as in a PR review.

## Pick the work

- **Read `DECISIONS.md` (repo root) first:** it holds what is already settled. If a finding or its fix
  goes against an entry, don't make the change: tell the user which decision it contradicts, with the evidence if its
  **Reopen if** now holds, and ask.
- An ID cited somewhere but missing from `REVIEW.md` was usually removed by a cleanup;
  `python3 scripts/review_lookup.py <ID>` gets the entry from git.
- Take the entries named (by the user, or by the lead's brief), or the open ones in the review log's suggested order,
  most severe first. Group related entries (same file, same cause). The findings worked on together share their test runs
  (**All the findings' tests first, run together**, below): each finding gets its own test and its own fix, but not runs of its own.
- Read each entry, and the code at its location, before writing anything. The location may have
  moved since the review; find it by the quoted code.

## Show the plan first

Before changing anything, show the user the plan, one finding at a time: the finding in plain words, then how you plan
to fix or answer it. Say where a measurement could change the plan. Then wait for the user's answer, unless they have
already said to go ahead without one. During the lead's loop this step is skipped: by the developer, whose brief is the
plan, and by the lead fixing findings itself, since the loop runs without asking (the `project-code-review` skill, step
7). It applies when the user asks for findings to be fixed outside the loop.

## All the findings' tests first, run together

The full suites never run while findings are addressed: they run only when the user asks (AGENTS.md, Running the
tests). Each finding's tests run on their own instead: unit tests by name, live checks in a scratch run, an
environment you build for them (the `live-check` skill). All the findings being
addressed in one go (the ones the user named, or the batch in the plan) are handled together:

1. **Write every finding's test first** (step 1 below, for each finding), and no fix yet.
2. **Review the tests before running them,** as a reviewer would (step 6's list applies to tests too): would each one
   fail on the bug, or would it pass on state an earlier check left, a value already there, a comparison any rule
   satisfies? Does it clean up when a step fails?
3. **One failing run for all of them:** every finding's unit tests in one command, with lint and types, and every
   finding's live checks in one scratch script (`alone.run` first; load the `live-check` skill). Read each failure (steps 1 and 2). A test that passes, or fails for
   another reason, was written wrong, unless the finding is false (step 2): fix it and run again, before any fix.
4. **Measure with a scratch probe** what a fix needs measured in Designer first (step 3): temporary code of your own,
   in the same Designer, as the `live-check` skill's **How a probe runs** says. What it measures goes in
   GUIDE.md or the module's docstring, as the table in `.claude/rules/docs.md` says, with a "designer facts" check, run in the scratch run like the others.
5. **Fix everything** (step 3 for each finding), then run the same unit tests and scratch script again (step 4), until
   every test passes.

## For each finding

1. **Reproduce it with a test that fails.**
    - Pure-Python logic (server, installer, CLI, test infrastructure): a unit test in `tests/unit`.
    - Anything that depends on Designer (helpers, plugin behaviour inside Designer, sd API facts):
      a check in the live self-test (`tests/test_all_tools/`, in its category's `checks.py`), even when a unit test also
      covers it. A unit test can take a path Designer never does.
    - Run it, in the group's failing run (a live check in its scratch run), and **read the failure**. It must fail
      *because of the bug*: compare the failure with the entry's scenario. A test that fails for another reason (a typo,
      a broken query, a wrong fixture) proves nothing. Fix the test and run it again, still before the fix
      (**All the findings' tests first, run together**, point 3).
2. **If the test passes before any change, and it would see the bug, the finding is false** (not a bug, or not
   reproducible). First read the test against the entry's scenario: one that can't see the bug is a wrong test, not a
   false finding (**All the findings' tests first, run together**, point 3). Don't change the code to "fix" it:
    - keep the test as a guard;
    - write down why it doesn't happen, with the evidence (the passing test, the docs or
      behaviour that explain it);
    - report the entry's resolution as *not a bug* or *not reproducible* (step 7).

   If the code path is real but can't be triggered, a small defensive change is fine; say so.
3. **Fix the code**, as small as it can be, in the style of the code around it. Two things first,
   because skipping them is what made findings come back round after round (the chains in
   REVIEW.md: the seed chain HLP-22 → … ran 18 findings deep, one case per round):
    - **Measure before fixing on Designer's behaviour.** When the fix depends on how Designer
      behaves (inheritance, seeds, function graphs, shutdown, the UI), first measure every case the
      code distinguishes (the node and the graph, each inheritance mode, with and without a render override...) in one
      scratch probe (**All the findings' tests first, run together**, point 4), record the measured table in
      GUIDE.md or the module's docstring, as the table in `.claude/rules/docs.md` says, with its "designer facts" check, then write the fix for that table. Never fix the one case in the finding and leave the next case
      for the next review.
    - **Fix the pattern, not the instance.** Search for every other place with the same pattern:
      the other callers of the helper, the same check or message elsewhere, the sibling tool or
      parameter (HLP-31 fixed `'graph'` in two tools; HLP-41 later found eight more). Fix each one
      that has the defect, with its test, and list what you searched and what you found under **Also covered** in the
      resolution, so the next reviewer can see the scope.
4. **Run the tests again: they must pass.** Only the tests added or modified for the group's findings, and the unit
   tests that read the source of the files the fixes change (`.claude/rules/python.md`), never the whole suites, which
   run only when the user asks (AGENTS.md, Running the tests):
    - the unit tests by name, always with lint and types, and the docs tests with any change of Markdown, a comment
      or a docstring: the commands are in `.claude/rules/python.md` and `.claude/rules/docs-tests.md`;
    - the live checks in the group's scratch script. Plugin changes only reach Designer after `install.py` and a
      restart of the Designer the scratch runs use, which an agent started: `alone.close()`, and the next run starts
      one (the `live-check` skill); say that you did.

   A scratch run proves a check in its own environment; if the full run the user asks for later shows it failing
   there, and failing alone too (the `live-check` skill, When the final check fails), the finding is open again. The lead unchecks it and adds a note under its resolution saying what failed (the
   entry's earlier text stays). The developer fixes it, and the lead adds the new resolution below the note.
5. **Update the docs** the change touches, as the "Keeping the docs current" table of `.claude/rules/docs.md` says:
   tool docstrings and parameters' descriptions, GUIDE.md facts, README.md. Add a new sentence only when an agent or a
   user needs it to act, and make it say exactly what its check measures, no more. Every claim is
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
    - a comment, a docstring, a parameter's description, or a sentence of AGENTS.md, a rule or skill AGENTS.md points
      to, GUIDE.md or README.md that the fix made untrue, a name or path in DECISIONS.md it made stale, or a new
      sentence that claims more than the test measures.
      Adjust what you find, then step back and review the adjusted change the same way, again and
      again, until a fresh look finds nothing a reviewer could report. Only then go on.
      When a sentence claims more than its test measures, prefer narrowing the sentence to writing a
      stronger test, unless the extra claim is something an agent needs in order to act. For an entry
      marked generation 3 or later (`.claude/agents/reviewer.md`, Follow-up chains), narrowing the claim is
      the fix. Don't add a new check for it.
7. **Report the resolution, for the lead to assess and write in `REVIEW.md`** (the `project-code-review` skill,
   Resolving). Once it holds, the lead checks the box (`- [ ]` becomes `- [x]`) and adds the resolution under it.
    - The resolution: **Resolution: done**, *not a bug*, *not reproducible*, *won't fix* or *moved to ROADMAP.md*.
      It starts with one of these wordings, and details can follow. Don't record a commit: branches are squashed into main, so a hash stops resolving. It answers:
        - **Test:** which test reproduced it (or showed it doesn't happen), and how it failed (a live check: in its
          scratch run);
        - **Cause** (when fixed): why the code failed, the root cause rather than the symptom (for
          example "each value was set right after it was checked, so a bad later value left the
          earlier ones changed");
        - **Fix** (when fixed): how it was fixed, what changed and where;
        - **Also covered** (when fixed): the same pattern searched for elsewhere, where, and what
          was found (fixed too, or not affected and why);
        - **Why not** (when false): why it doesn't happen, with the evidence;
    - The lead updates the status table (open and resolved counts per severity).
    - **Won't fix is the user's decision** (the user, 2026-11-20). The developer may propose one in its report, and
      the lead may propose one itself. The lead judges every proposal, its own included, against these criteria,
      which must all hold:
        - **The finding is real,** settled by reading or a probe. A false finding is *not a bug* or *not
          reproducible* instead.
        - **Fixing it is never worth it, not just "not now".** One of these applies:
            - the fix costs far more than the harm: a rare defect with a small effect, against much more code, a new
              moving part or slower runs;
            - the fix goes against a choice of the user's;
            - it can't be fixed from this project: it is Designer's or Claude Code's own behaviour, and stating the
              limit where agents read it is all that can be done.
        - **It isn't work for later.** Work worth doing one day is a ROADMAP.md item instead, which closes the finding
          (**Moved to ROADMAP.md**, below).

      When **Fixing it is never worth it** fails, or the lead is unsure whether it holds, the finding is fixed, or moved
      to ROADMAP.md (below). A fix closes it for good, while a won't fix adds a DECISIONS.md entry that every later
      review checks. When all hold,
      the lead tells the user at once, and the loop stops until they answer (the `delegate` skill, The loop is the
      lead's), since the finding stays open. The lead uses *won't fix* only once the user agrees, then records it
      (below).
    - **Moved to ROADMAP.md is the user's decision too** (the user, 2026-11-20). It closes a real finding whose fix is
      work worth doing one day, outside the branch's scope. A leftover in the branch's own code is fixed in the branch
      instead (the `delegate` skill, The loop is the lead's). The developer may propose the item in its report, and the
      lead may propose one itself. The lead asks the user at once, as for a won't fix, since the finding stays open
      until they answer. Once the user approves the item, the lead adds it to ROADMAP.md, citing the finding's ID, so
      `scripts/review_lookup.py` finds the entry after a cleanup. Then the lead checks the entry with
      `**Resolution: moved to ROADMAP.md** (item N, the user, <date>)`.

## Recording decisions

`REVIEW.md` is the memory per branch, where reviewers can still question an answer. `DECISIONS.md` is the memory for
the whole project, where they can't, so only what is settled goes there, and only what a reviewer could plausibly
raise again:

- **What the user decides goes in, if a reviewer could raise it again:** their answer when asked to decide on a
  finding, or what they say about one unprompted: won't fix, a rule to follow from now on, one option out of several,
  how something should work. A choice that AGENTS.md, a rule or skill AGENTS.md points to, or the code's comments
  already answer stays in `REVIEW.md` and the code. It can come with a fix: a rule chosen over closing a finding as
  won't fix is both. Keep the entry to the decision, the reason the user gave or agreed to in a few words, the date
  and the reopen condition. A cleanup of `REVIEW.md` moves nothing to `DECISIONS.md`, so this is the time.
- **A false finding stays in `REVIEW.md` only** (the user, 2026-11-20). A *not a bug* or *not reproducible* answer is
  a review's finding that didn't hold, not a decision, so it gets no `DECISIONS.md` entry. If a reviewer raises it
  again after a cleanup, the test kept as its guard (step 2) is the evidence that settles it again.

For what goes in:

- **Add it** in the section it belongs to, in the format that file's introduction gives.
- **Names and paths are yours to keep current:** when a change renames or moves the code or test an entry points at,
  update the entry. Changing what was decided, or removing an entry, takes the user. Never leave two entries that
  contradict each other.
- **If the user gave no reopen condition,** propose one in the entry and show them the entry, so they can
  correct it.
- **An ordinary fix doesn't go in:** the code, its test and `REVIEW.md` record it.

## After a group

- Report per finding its resolution (step 7) and the result (a live check: in its scratch run); say plainly which
  findings were false and why.
- The lead commits (AGENTS.md), with `REVIEW.md` in the same commit as the fixes it records.
- New problems found along the way are reported with their evidence, not silently fixed. The lead settles each (the
  `project-code-review` skill, Who settles what), then writes it as a new entry (that skill's rules: append, the next
  free ID, the header's **Last used**) or rejects it. Every developer run gets a row in the table by model, with its
  cost, and its new findings count there (TEMPLATE.md, Reviews by model).
- Work for later that isn't a finding (a follow-up, an idea): propose it to the user for `ROADMAP.md` in your report.
  A leftover in the branch's own code is reported for a fix in the branch instead (the `delegate` skill, The loop is
  the lead's). The lead asks the user about the proposals when the reviews look converged, unless the next step needs
  the answer first (the `delegate` skill, The loop is the lead's), and adds what they approve. A cleanup
  of `REVIEW.md` moves nothing there.
