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

**Last used:** PLG-45, SRV-249, HLP-254, INS-47, TST-836, AGT-132.

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
| Low-medium | 0 | 3 |
| Low | 0 | 13 |
| **Total** | **0** | **16** |

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
| 2026-11-24, step 1 | Opus (developer) | 1 | 0 | 0 | 268,175 | 21 min |
| 2026-11-24, step 1's round on class d | Opus (developer) | 1 | 0 | 0 | 36,089 | 8 min |
| 2026-11-24, step 1's first review | Sonnet | 2 | 2 [1 Low-medium, 1 Low] | 2 [1 Low-medium, 1 Low] | 319,691 | 6 min |
| 2026-11-24, step 1's first review's fixes | Opus (developer) | 1 | 0 | 0 | 41,206 | 8 min |
| 2026-11-24, step 1's second review (the fixes) | Sonnet | 1 | 1 [1 Low] | 1 [1 Low] | 96,598 | 3 min |
| 2026-11-24, SRV-246, steps 2 and 3 | Opus (developer) | 1 | 0 | 0 | 339,775 | 22 min |
| 2026-11-24, steps 2 and 3's first review | Sonnet | 2 | 6 [1 Low-medium, 5 Low] | 6 [1 Low-medium, 5 Low] | 394,725 | 8 min |
| 2026-11-24, steps 2 and 3's review's fixes | Opus (developer) | 1 | 0 | 0 | 57,609 | 8 min |
| 2026-11-24, the entire branch's first Opus review | Opus | 2 | 6 [6 Low] | 6 [6 Low] | 497,366 | 13 min |
| 2026-11-24, the Opus review's fixes | Opus (developer) | 1 | 0 | 0 | 38,563 | 6 min |
| 2026-11-24, INS-47 | Opus (developer) | 1 | 0 | 0 | 294,829 | 21 min |
| 2026-11-24, INS-47's Opus review | Opus | 1 | 0 | 0 | 157,382 | 9 min |
| 2026-11-24, the final check | settling | 1 | 0 | 0 | 89,777 | 19 min |
| 2026-11-24, TST-836 | Opus (developer) | 1 | 0 | 0 | 175,595 | 11 min |
| 2026-11-24, the final check, second run | settling | 1 | 0 | 0 | 57,156 | 11 min |
| **Total** | | 18 | 15 [2 Low-medium, 13 Low] | 15 [2 Low-medium, 13 Low] | 2,864,536 | 174 min |

## Review log

### 2026-11-24: guide-core-budget, step 1

- **Scope:** `git diff d753639 0895171 -- . ':(exclude)PLAN.md'`: Step 1 of the branch's plan (ROADMAP item 126), the
  core's budget test and `## Which tool for what` trimmed.
- **How:** two Sonnet reviewers, split by the core's bullets. One took the budget test, the intro and the Start, Find,
  Inspect, Safety net and Look bullets, with their tools (`discovery.py`, `views.py`, `lifecycle.py`). The other took
  the Measure, Tune, Edit, Write a function and Output bullets, the scripting sections that received text, and their
  tools (`compare.py`, `reference.py`, `image_reading.py`, `edits.py`, `output.py`), with the pointers. No tests run,
  no probes: reading settled every suspicion. Both reviewers printed a few lines of PLAN.md by mistake and said they
  set them aside.
  - Settled as not a finding: the budget test's comment claims room the core doesn't have yet. That is the planned
    state between steps; Step 2 puts the trimmed core's measured size there.
  - Not worth a fix: "as its bitmap node does" in `REFERENCE_ORIENTATION`; "A colour input gave every pixel..." not
    naming the Gradient Map, which the sentence before it names; ragged line breaks in `OPS` and `export_outputs`'
    docstring.
  - Not worth a fix, outside this diff: "two points at one x make a step" and "a point at x -0.2 computes 0" are only
    in the scripting part. Neither surprises an agent: a step is what two points at one x ask for, and `OPS` says x 0
    to 1.
- **Not verified:** none.
- **Resolutions assessed:** none; REVIEW.md had no entries.
- **Findings:** SRV-245 (Low-medium), TST-827 (Low).
- **Suggested order:** both in one developer round, SRV-245 first.
- **Checked and found fine:**
  - every other sentence deleted from the core is held by a docstring, a `Field`, the scripting part or the remaining
    core, where the agent who needs it reads (both reviewers' tables, deletion by deletion);
  - `launch_designer`'s new last sentence agrees with the guide's Rules, AGENTS.md and DECISIONS.md, "A Designer the
    user opened is theirs";
  - the wrong "how many match" is gone, and `search_nodes`' docstring matches the code (`discovery.py:226-227`, `:280`);
  - `describe_graph`'s `selected` Field is backed by the `editor_open_and_zoom` checks (`checks.py:315-346`);
  - `screenshot_designer`'s two added sentences are true of `shot3d.py:332-344` and ROADMAP item 83;
  - `REFERENCE_ORIENTATION` is true of `_open_image`;
  - the `interpmode`, colour-input and curve-array claims in `OPS` match `params/checks.py:308-330`, `:361-368`, and
    the palette recipe and "Its default is Desaturation" match `bitmaps/palettes.py:115`;
  - no stale pointer, repo-wide, to the moved text;
  - the budget test fails without the trim (19,981 > 14,000), and every changed tool description is under 4,096.

### 2026-11-24: guide-core-budget, step 1's fixes

- **Scope:** `git diff 0895171 de40d85 -- . ':(exclude)PLAN.md'`: the fixes of SRV-245 and TST-827, and REVIEW.md.
- **How:** one Sonnet reviewer, rechecking both resolutions. No tests run, no probes: the lead settled the one
  suspicion by reading the cells of `tests/test_all_tools/params/designer_scripts/keys.py:290-324`. The reviewer saw
  PLAN.md's text in a grep's output and said it set it aside.
- **Not verified:** none.
- **Resolutions assessed:** SRV-245 holds, and is questioned by SRV-246 for the sentence's scope only. TST-827 holds.
- **Findings:** SRV-246 (Low, follows SRV-245, generation 2). The longest chain still growing: SRV-245 → SRV-246,
  generation 2.
- **Suggested order:** SRV-246 first, in the next developer run.
- **Checked and found fine:**
  - folding the scripting part's bullet into its pointer lost nothing: each of the pointer's four topics is in `OPS`;
  - both new tests fail without their fixes: "first listed" is nowhere else in the repo, and before TST-827's fix a
    full stop followed "**enum values**";
  - `_given_keys` and `_new_keys` keep the keys in the order given (`designer_helpers/edits.py:211-259`), so "the
    first listed" holds for the `set` path at `interpmode` 0;
  - no other sentence was made untrue, and REVIEW.md's status table, counters and totals add up.

### 2026-11-24: guide-core-budget, steps 2 and 3

- **Scope:** `git diff 09941a3 a2920df -- . ':(exclude)PLAN.md'`: Steps 2 and 3 of the branch's plan (the rest of
  the core trimmed, item 127's line, ROADMAP items 126 and 127), with SRV-246's fix.
- **How:** two Sonnet reviewers. One took the core's intro, Rules, what was Undo and timeouts, and Environment facts,
  with the scripting sections that received their text and their tools (`lifecycle.py`, `log.py`, `layout.py`,
  `scripting.py`). The other took First sd pitfalls, Library node facts with item 127's line, what was Rendering and
  verifying, `tests/unit/test_guide.py`, `OPS` and ROADMAP.md, and rechecked SRV-246. No tests run, no probes: the
  lead settled every suspicion by reading. Both reviewers saw a few lines of PLAN.md in grep output and said they set
  them aside.
  - Settled as not a finding: Step 2's "The heading stays" for Undo and timeouts was not followed. The lead chose to
    delete the section during the step: the server's instructions name Undo among the rules, which stay in Rules,
    and nothing was left under the heading.
  - Settled as not a finding: row 57's fact is in `export_outputs`' docstring only, with a pointer from
    `render_sbs`', where the approved step named both. `.claude/rules/docs.md` keeps each fact in one place and links
    to it; the lead accepted the developer's departure. The pointer's "its" is not misleading enough to fix.
  - Not worth a fix: the `overridable` Field's "a fixed size isn't exposed, so size overrides are ignored" and the
    `size_log2` Field's "a graph's non-zero relative offset applies on top" have no live check. They were untested in
    the old guide too, the approved plan holds that a move needs no new test, and an agent rendering a graph with a
    non-zero relative offset is rare.
  - Fine: the `Timeout` alias in `scripting.py` follows `Graph`, `Output` and `Port`, and gives the same schema.
  - Outside the diff, for the user: `examples/build_dwarf_trimsheet.py:628` sets `curvature_smooth`'s
    `normal_format=0 if NORMAL_OPENGL else 1`. The developer's probe showed `describe_node` giving DirectX=0 and
    OpenGL=1 there, and the example's normals are OpenGL (line 625, `inversedy=NORMAL_OPENGL`). PLAN.md holds it.
- **Not verified:** none.
- **Resolutions assessed:** SRV-246 holds: its cells set no `interpmode`, and its test fails on the old wording.
- **Findings:** TST-828, TST-829, TST-830, TST-831 (two reviewers), TST-832: 5 Low. The longest chain still growing:
  SRV-245 → SRV-246, generation 2, now closed.
- **Suggested order:** all five in one developer round.
- **Checked and found fine:**
  - the core still gives every rule `INSTRUCTIONS` promises (the bridge token, Undo, the user's Designer, the agent's
    Designer, snapshots, never hot-reloading), and every fact cut from Rules is in a docstring;
  - "Tell the user" is in `set_link_display`'s docstring and in `apply_edits`' `ops` and result;
  - the 15-minute drop matches the plugin (`QUEUE_WAIT = 900`); the trace hook and `BaseException` sentences moved
    word for word;
  - "Undo from a script", the log rows, the Several Designers rows and the crash-dump bullet claim what the old text
    did;
  - rows 34 to 42, 47 and 51 to 58 are held where their readers look; rows 44 and 48 are `describe_node`'s output,
    which `facts/checks.py:435-457` and `render/checks.py:379-385` also read;
  - item 127's line is true of `facts/checks.py:84-118`, and its test fails without it;
  - the budget comment's figures, ROADMAP items 126 and 127, and `GUIDE_SECTIONS`, `SCRIPTING_SECTIONS` and
    `MOVED` match the guide; no older test was weakened or made blind;
  - the updated pointers (`common.py:321`, `test_lifecycle_env.py:2042`, `SKILL.md:150`, `DECISIONS.md:158`,
    `test_pil_facts.py:1`, ROADMAP item 17) are right.

### 2026-11-24: guide-core-budget, the entire branch against main (Opus)

- **Scope:** `git diff main...a2fc05d -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`, the whole branch.
- **How:** two Opus reviewers, with the plan's text as the user approved it. One took `mcp_server/GUIDE.md` and
  `tests/unit/test_guide.py`; the other the tools' descriptions in `mcp_server/server_tools/`, `tests/test_all_tools/`,
  the other unit tests, ROADMAP.md, DECISIONS.md and the `live-check` skill. No tests run, no probes: the lead settled
  every suspicion by reading. One reviewer wrote a stray 554-byte file in the lead's scratchpad by a redirect, and
  said so; the lead removed it.
  - Not worth a fix: `tests/test_all_tools/facts/checks.py:1` ("Designer facts GUIDE.md relies on") and `:416` ("the
    remaining GUIDE.md facts") also describe checks of `describe_node`'s output (`Pattern_Type`, `normal_format`),
    which the guide no longer states. Those checks still guard what an agent reads, so nothing misleads.
  - Not worth a fix: ROADMAP item 17's approach names "`export_outputs`' and `render_sbs`' docstrings", one fact in
    two places, in a plan for later; `compare_to_reference`'s "against the matching region" no longer marks `region`
    as the parameter, but reads right.
  - Not worth a fix, older than the branch: `render_sbs`' `size_log2` Field says a .sbs renders "at the graph's
    default parent size", while a package whose graphs differ renders at 256 px, with a note in the result
    (`output.py:152-156`), which tells the agent.
- **Not verified:** none.
- **Resolutions assessed:** SRV-245, SRV-246, TST-827, TST-828, TST-829, TST-830, TST-831 and TST-832 hold. TST-832's
  fix left the core's figure stale (TST-833), and TST-831's sweep missed item 6's "see GUIDE.md" (TST-834).
- **Findings:** TST-833 (two reviewers), TST-834, SRV-247, SRV-248, TST-835, SRV-249: 6 Low. The reviews look
  converged: an Opus round of the entire branch found only a few Low ones. Longest chains: TST-832 → TST-833 and
  TST-831 → TST-834, generation 2.
- **Suggested order:** all six in one developer round.
- **Checked and found fine:**
  - every sentence deleted from `main`'s core is held where its reader looks, apart from TST-835 and SRV-249;
  - what stays in the core reads whole; the scripting part's received text is in the sections the plan names, with no
    copies, apart from SRV-248;
  - every changed description is true of the code and its checks, apart from SRV-247, and nothing it said on `main`
    is lost; each is under 4,096 characters;
  - `REFERENCE_ORIENTATION` and `Timeout` are the one shared text and parameter;
  - every "GUIDE.md, <label>" pointer in the repo names a label the guide has; nothing names a removed section;
  - the new tests each fail without what they guard; no older assertion was dropped but `len(core) < 20000`, which the
    budget test replaces; `GUIDE_SECTIONS`, `SCRIPTING_SECTIONS` and `MOVED` match the guide.

### 2026-11-24: guide-core-budget, INS-47's fix (Opus)

- **Scope:** `git diff 7b86d7f 3187e02 -- . ':(exclude)PLAN.md'`: the fix of INS-47 alone, on the user's word
  (2026-11-24, "fix in this branch then an opus review just for that fix").
- **How:** one Opus reviewer. No tests run, no probes: reading settled everything.
- **Not verified:** none.
- **Resolutions assessed:** INS-47 holds: the example check reads the pairing from the saved and reloaded graph and
  fails on the old line; the fact check's limits (> 0.505, < 0.495) sit between the measured 0.5100 and 0.4873, and a
  flat or ignored result fails; the GUIDE.md line claims the four pairings measured, in the core.
- **Findings:** none. Two slips in REVIEW.md's own record, corrected by the lead: INS-47's Cause said "a ridge along
  X" for the vertical ridge, and the table by model hadn't counted INS-47 in the Sonnet round of steps 2 and 3 that
  found it.
- **Checked and found fine:** the example has no other node that reads normals; `curvature_formats.py` follows its
  category's precedents and `test_selftest_safety.py`'s rules; the fact check deletes its 7 nodes in a `finally`; the
  core's 7,885 characters and ROADMAP item 126's note hold.

---

## High

## Medium-high

## Medium

## Low-medium

- [x] **SRV-245 · "Of two keys at one position, the first listed shows" left where a tools-only agent won't read it** · `mcp_server/server_tools/edits.py:105-118` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** Step 1 deleted the core's bullet on gradients and curves. It moved the facts an agent meets through
    `apply_edits`' `set` into `OPS`, but not this one. `git grep "first listed"` finds it only in the scripting part's
    "A gradient computes" (`mcp_server/GUIDE.md:453`), which only an agent about to run code reads.
  - **Scenario.** An agent wanting a hard edge in a Gradient Map sets `gradientrgba` to `[[0.5, red], [0.5, blue]]`
    with `apply_edits`. The first listed key shows and the other never does
    (`tests/test_all_tools/params/checks.py:296-303`), with no error, and nothing the agent read told it so.
  - **Fix.** One sentence in `OPS`' `set` paragraph, beside `interpmode`: "Of two keys at one position, the first
    listed shows." The scripting part's bullet stays, as the measured record.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_guide.py::test_apply_edits_says_which_of_two_gradient_keys_at_one_position_shows`
      failed before the fix: the sentence wasn't in `apply_edits`' `ops`. It also requires 'first listed' to be out of
      the scripting part, so that the fact stays in one place.
    - **Cause:** the round that moved class d facts into `OPS` took `interpmode` 3 and the colour input, and left this
      one in the scripting part, which an agent using only the tools never reads.
    - **Fix:** "Of two keys at one position, the first listed shows." in `OPS`' `set` paragraph
      (`mcp_server/server_tools/edits.py`), after the `interpmode` sentence. Unlike the entry's suggested fix, the
      scripting part's bullet is folded into its pointer to `ops` ("the midpoints, the `interpmode`s, two keys at one
      position and a colour image fed"). The fact is then in one place (`.claude/rules/docs.md`), and the `params`
      check of keys stays its measured record (`tests/test_all_tools/params/checks.py:296-303`).
    - **Also covered:** every fact Step 1 moved was checked again for one left where its reader won't look: the class d
      facts (the palette recipe, `interpmode` 3, the colour input and the curve arrays are now in the tools'
      descriptions), the class e graph ambiguity (in `find_graph`'s refusal, met exactly when it applies), and the
      scripting part's pointers into the docstrings (each names text that exists). None else was found.
  - Questioned by SRV-246 (2026-11-24).

- [x] **INS-47 · The example tells `curvature_smooth` its normals are DirectX, while it feeds OpenGL ones** · `examples/build_dwarf_trimsheet.py:627-629` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The example builds its normals with `inversedy=NORMAL_OPENGL` (line 625), and `NORMAL_OPENGL = True`
    (line 103): atomic `normal` with `inversedy=True` gives OpenGL normals (GUIDE.md, Library node facts). It then sets
    `curvature_smooth`'s `normal_format=0 if NORMAL_OPENGL else 1`. The developer's probe of this branch showed
    `describe_node` giving `curvature_smooth`'s `normal_format` as DirectX=0, OpenGL=1, so the example passes the
    opposite of what it feeds. Since the first commit; found outside the branch's diff, and fixed in the branch on the
    user's word (2026-11-24).
  - **Scenario.** The example's curvature is computed from normals read with their green channel flipped, so the worn
    edges and cavities it drives come out wrong along one axis of the trim sheet.
  - **Fix.** `normal_format=1 if NORMAL_OPENGL else 0`, after measuring what `curvature_smooth` gives for each format
    on normals of known handedness, with a test that fails on the old line.
  - **Resolution: done**.
    - **Test:** `tests/test_all_tools/example/checks.py::check_the_curvature_takes_the_format_of_its_normals` failed in
      a scratch run on the old line ("CURVATURE fed by sbs::compositing::normal inversedy=1 normal_format=0"), and
      passed after the fix. The new "designer facts" check
      `tests/test_all_tools/facts/checks.py::check_curvature_smooth_takes_the_format_of_its_normals` measures the
      pairing: held to the old line's assumption it gave 4 FAIL, with the measured pairing 5 PASS. The final scratch
      run, the fact check and the whole `example.run`: 21 checks, 0 failed.
    - **Cause:** the example builds OpenGL normals (`inversedy=True`) and gave `curvature_smooth` `normal_format=0`,
      which is DirectX in that node's enum. Measured on a horizontal ridge: format 1 after `inversedy=True` and 0
      after `False` read it convex (0.51); the other pairings read it concave (0.4873). A vertical ridge, its profile along X, read 0.51 in all four. So every horizontal ridge and groove of the example came out inside out.
    - **Fix:** `normal_format=1 if NORMAL_OPENGL else 0` (`examples/build_dwarf_trimsheet.py:627-630`). The measured
      fact is a line in GUIDE.md's core, Library node facts, after the atomic `normal` line: an agent using only the
      tools wires `curvature_smooth` after a `normal` too. The core is 7,885 characters; the budget comment and ROADMAP
      item 126 say so. Designer's 3D view, before and after, from one camera: the raised diamonds and plaques get an
      even worn rim on all four sides, and the horizontal joints read as dark cavities like the vertical ones; the
      lead looked at the shots and the curvature maps.
    - **Also covered:** `git grep -i` for `normal_format`, `inversedy`, "normal format", `directx`, `opengl`,
      `curvature`, `hbao` and `'normal'` across `mcp_server/`, the self-test, GUIDE.md and README: this was the only
      place where a normal's format feeds a node that reads normals.

- [x] **TST-836 · The self-test reads no active app on macOS 27.2.1: `pid_of` expects `"pid"=N`, and `lsappinfo` prints `pid = N`** · `tests/test_all_tools/window_server.py:126-129` · measured · found 2026-11-24 by the runner (Sonnet)
  - **Defect.** `pid_of` matches `r'"pid"\s*=\s*(\d+)'`. On macOS 27.2.1 (26B131), `lsappinfo info -only pid <front>`
    prints `pid = 2510 !cgsConnection !signalled type=[ NULL ] ...`, with no quotes, so `active_app()` returns None
    every time. `test_pid_of` (`tests/unit/test_selftest_window_server.py:99`) feeds only the old `"pid"=1920`.
  - **Scenario.** The final check of this branch failed on 4 checks, each failing again alone: the unit test
    `test_the_front_watch_samples_the_active_app_and_the_windows_on_screen` ("lsappinfo names the active app"), and
    three live checks that read the active app: `lifecycle`'s "starts Designer hidden" ("0 reading the active app"),
    and `editor_panels_and_fit`'s 3D shot with Designer hidden ("the active app None") and its window checks off
    screen ("0 reading the active app"). The lead read the new output itself. The branch touches neither file.
  - **Fix.** `pid_of` reads both layouts, with a unit test of the real new output; the live checks of `lifecycle` and
    `editor_panels_and_fit` in a scratch run; then both full suites again.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_selftest_window_server.py::test_the_active_apps_process_is_read_from_lsappinfo`,
      parametrized over the old layout, the real output of macOS 27.2.1 (`LSAPPINFO_27`) and nothing printed. Its
      `macOS 27.2.1` case failed before the fix (`assert None == 2510`), and so did
      `test_the_front_watch_samples_the_active_app_and_the_windows_on_screen`. The three live checks had failed in the
      final check and again alone.
    - **Cause:** `pid_of` accepted only the quoted key, `"pid"=N`; macOS 27.2.1 prints `pid = N`, so `active_app()`
      returned None at every sample.
    - **Fix:** `pid_of` matches `\bpid"?\s*=\s*(\d+)` (`tests/test_all_tools/window_server.py`). In `lsappinfo info
      -only pid`, only that line names a pid; `\b` keeps a key such as `ppid` out. The docstring names the layout of
      each macOS: 26 printed `"pid"=1234`, 27.2.1 `pid = 1234` (installed 2026-11-23, by `softwareupdate --history`).
      The scratch run of `lifecycle` and `editor_panels_and_fit` passed 197 of 197, every window check reading the
      active app at each sample, with no crash dump.
    - **Also covered:** every subprocess call and `os.popen`, `QProcess`, `osascript` and `NSRunningApplication` in
      `tests/test_all_tools`, `mcp_server`, `plugin`, `client` and the scripts: only `window_server.py` parses
      `lsappinfo`, and `undo/edit_menu.py` reads the front app through it. The other macOS outputs parsed (`ps -o
      field=`, `lsof -Fn`, `pgrep`, `defaults read`) have fixed formats and no failing check.

## Low

- [x] **TST-827 · "the slider range" in the core's Find bullet points at nothing** · `mcp_server/GUIDE.md:33-34` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The bullet now reads "`describe_node` for connector ids, parameter types, **enum values**. Never guess
    ids or enum numbers; pick values inside the slider range." Step 1 cut "library slider ranges and descriptions"
    from it, so the core no longer says which tool gives a range. Only `describe_node`'s docstring says it does, for a
    library node.
  - **Scenario.** An agent reading the core is told to stay inside "the slider range", and not where to find one.
  - **Fix.** Name it again in the bullet, shortly, for example "**enum values** and, for a library node, slider
    ranges".
  - **Resolution: done**.
    - **Test:** `tests/unit/test_guide.py::test_the_core_names_the_tool_that_gives_the_slider_range_it_asks_for`
      failed before the fix: no sentence of the core's `## Which tool for what` named `describe_node` with slider
      ranges.
    - **Cause:** Step 1 moved "library slider ranges and descriptions" into `describe_node`'s docstring and left the
      core's "the slider range" without the tool that gives it.
    - **Fix:** the Find bullet reads "`describe_node` for connector ids, parameter types, **enum values**, library
      slider ranges." (`mcp_server/GUIDE.md`), 23 characters more in the core.
    - **Also covered:** the whole core grepped for sentences that lost what they refer to after the trim (recipe,
      palette, `reference_region`, `interpmode`, gradient, curve, slider, selection, 1/65535, EXIF, orientation,
      `describe_node`, `search_nodes`, "below", "above", "see"). Only the slider range was left dangling.

- [x] **SRV-246 · `OPS`' "Of two keys at one position, the first listed shows" reads as true in every `interpmode`, measured only at 0** · `mcp_server/server_tools/edits.py:108-109` · confirmed · follows SRV-245, generation 2 · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** SRV-245's fix put the sentence right after "...eases at 1, where they act, and at 3 holds each key's
    colour up to the next." The cells that measure it, 'gradient, red then green at 0.4, blue at 1' and its reverse
    (`tests/test_all_tools/params/designer_scripts/keys.py:296-303`), set no `interpmode` and no midpoint, so they
    measure only the default, 0. The cells at `interpmode` 1 and 3 (`keys.py:314-324`) have two keys, at 0 and 1.
  - **Scenario.** An agent reads the sentence as holding at `interpmode` 1 or 3 too, which nothing measures.
  - **Fix.** Narrow the sentence to what is measured, for example "At `interpmode` 0, of two keys at one position,
    the first listed shows." The address-review skill prefers that to a new check, as no agent needs duplicate keys
    for a hard edge at 3, which holds each key's colour already.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_guide.py::test_apply_edits_says_which_of_two_gradient_keys_at_one_position_shows` now
      requires "At interpmode 0, of two keys at one position, the first listed shows." and "At interpmode 0, a colour
      input gave every pixel the colour of the key at position 0" in `ops`. It failed on the old wording, on its first
      assertion.
    - **Cause:** SRV-245's sentence followed the one on `interpmode` 0, 1 and 3, so it read as true in all three,
      while its cells set no `interpmode`.
    - **Fix:** both sentences of `OPS` (`mcp_server/server_tools/edits.py`) start "At interpmode 0".
    - **Also covered:** the next sentence, "A colour input gave...", had the same pattern: its cell, 'on the colour
      ramp' (`keys.py:337`), sets no `interpmode` either. It is narrowed and tested too. The scripting part's "A
      gradient computes" is left as it is: it sits under its own "Measured on a 16 px ramp" lead, with `interpmode`'s
      default named above it.

- [x] **TST-828 · The scripting part's "Library graphs in a script" lost "and its subfolders"** · `mcp_server/GUIDE.md:114-118` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The old Environment facts bullet said library graphs are `.sbs` files "in Designer's `packages` folder
    **and its subfolders**". Step 2 deleted it as a duplicate of "Library graphs in a script", which says only "they are
    in `app.getPath(SDApplicationPath.DefaultResourcesDir)/packages`". The deleted row 24 also said that loaded
    library packages count as user packages, as the API has no library flag (`_is_library_package`'s docstring,
    `mcp_server/designer_helpers/core.py`).
  - **Scenario.** A script loads `packages/<name>.sbs`, or globs the top level of `packages`, to find a ready-made
    material, and finds nothing: 30 of Designer 16's packages are in subfolders. A script that loops over
    `getUserPackages()` to save or unload meets the library ones too. Only the scripting part reaches that agent.
  - **Fix.** In the bullet: "in `.../packages` and its subfolders", and that loaded ones count as user packages.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_guide.py::test_the_scripting_part_says_where_library_graphs_are_and_how_loaded_ones_count`
      requires "...`/packages` and its subfolders" and "A loaded library package is among `getUserPackages()` too" in
      `## sd API gotchas`. It failed on its first assertion before the fix.
    - **Cause:** Step 2 deleted the Environment facts bullet as a copy of "Library graphs in a script", but only the
      deleted bullet said "and its subfolders" and how loaded library packages count.
    - **Fix:** the bullet says both, with "the API has no flag for it". The evidence: `_is_library_package`'s docstring
      and the self-test's `LIBRARY_PACKAGES` snippet (`tests/test_all_tools/common.py:253`), which lists library
      packages through `getUserPackages()`.
    - **Also covered:** the other rows Step 2 deleted were reread against their sources; none lost a fact only the
      scripting part's readers need.

- [x] **TST-829 · A self-test comment says "the guide" holds what is now in `read_designer_log`'s docstring** · `tests/test_all_tools/facts/checks.py:486` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The comment reads "the guide says no more of the first than that it may be logged, REVIEW.md TST-246".
    Step 2 moved the harmless log noise from the core into `read_designer_log`'s docstring
    (`mcp_server/server_tools/log.py:101-103`). The step's list of pointers didn't name this one.
  - **Scenario.** A maintainer reading the check looks for the sentence in GUIDE.md and finds it nowhere.
  - **Fix.** "`read_designer_log`'s docstring says no more of the first than...".
  - **Resolution: done**.
    - **Test:** none: no test reads pointers into GUIDE.md, a choice of the plan the user approved.
    - **Cause:** Step 2's list of pointers missed this comment.
    - **Fix:** the comment says "read_designer_log's docstring says no more of the first than that it may be logged".
    - **Also covered:** `git grep -n -i -E "the guide (says|describes|states|records|has|holds|gives)|GUIDE\.md
      (says|describes|states|records|has|holds|gives)|(in|as) the guide\b"`, and every "GUIDE" mention in
      `tests/test_all_tools`, `mcp_server`, `plugin`, `client`, `examples` and `scripts`. The other hits
      (`facts/checks.py:47`, `:90`, `:121`, `DECISIONS.md:303`) name facts still in GUIDE.md.

- [x] **TST-830 · No test holds the server's promise that the core gives the rules that protect the user's work** · `tests/unit/test_guide.py:839` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `INSTRUCTIONS` (`mcp_server/server_tools/core.py:100-102`) says the core holds "the rules that protect
    the user's work (Undo, the bridge token, quitting Designer, snapshots)". Of the Rules section, only "Never
    hot-reload" is tested (`test_the_hot_reload_rule_is_among_the_rules`); the plugin and token names are tested in the
    whole guide only (`tests/unit/test_constants.py:51-58`).
  - **Scenario.** This branch added a budget that pushes the next change of the core to cut. A cut that drops the Undo
    rule, the rule on the user's Designer or the snapshot rule fails no test, and every session loses it.
  - **Fix.** One assertion per promised rule in `section(core, "## Rules that protect the user's work")`: the bridge
    token, never triggering Undo, the user's Designer and the agent's, `snapshot_graph`.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_guide.py::test_the_core_gives_the_rules_the_servers_instructions_promise` asserts
      `INSTRUCTIONS`' promise, then five rules in the core's Rules: the bridge token, never triggering Undo, the user's
      Designer, the agent's disposable one, and `snapshot_graph`. It passes on the guide as it is, since the finding is
      a missing guard. A scratch script removed each rule from GUIDE.md in turn, in a `finally` that put the file
      back: each of the five runs failed, naming the rule removed.
    - **Cause:** of the Rules, only "Never hot-reload" was pinned, so a cut for the budget could drop a promised rule
      silently.
    - **Fix:** the test.
    - **Also covered:** `GUIDE_NOT_READ` makes the same promise ("it has the rules that protect the user's work"), and
      the same test guards it.

- [x] **TST-831 · ROADMAP item 36 points at GUIDE.md's Rendering and verifying, which is gone** · `ROADMAP.md:56` · confirmed · found 2026-11-24 by two reviewers (Sonnet)
  - **Defect.** Item 36 says "the 256 px default GUIDE.md describes (Rendering and verifying)". Step 2 deleted the
    section. Its facts are now in `_sbsar_default_log2`'s docstring (`mcp_server/server_tools/output.py:225-226`) and
    `render_sbs`' `size_log2` Field. The old row 54's "here and in other Substance apps" is now nowhere, and only item
    36 needs it.
  - **Scenario.** Whoever takes item 36 looks for the section and finds nothing.
  - **Fix.** Point item 36 at those two places, and keep "in other Substance apps" in the item's own words.
  - **Resolution: done**.
    - **Test:** none: no test reads pointers into GUIDE.md, a choice of the plan the user approved.
    - **Cause:** Step 2 removed `## Rendering and verifying` without sweeping ROADMAP.md for pointers into it.
    - **Fix:** item 36 names "the 256 px default sbscooker writes, at which a .sbsar renders here and in other
      Substance apps unless a size is set", with `_sbsar_default_log2`'s docstring and `render_sbs`' `size_log2`.
    - **Also covered:** checked item 49's "(GUIDE.md, Several Designers)" now points at `server_tools/lifecycle.py`'s
      docstring. Every `GUIDE.md, X` and `GUIDE.md (X` pointer in ROADMAP.md, DECISIONS.md, README.md, `docs/`, the
      skills, the rules, the agent files and AGENTS.md names a section or label GUIDE.md has, and the names removed
      from the guide are found nowhere else.
  - Questioned by TST-834 (2026-11-24).

- [x] **TST-832 · The core's `tile_generator` line speaks of "the same seed" and a "per-tile random mask" it no longer names** · `mcp_server/GUIDE.md:83` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The line reads "`Offset` is the row offset. The same seed and layout twice give a matching per-tile
    random mask." Before Step 2 it followed a list naming `Offset_Random_Seed` and `Luminance_Variation-Contrast`
    ("random luminance per tile"), which gave "the seed" and "the mask" their meaning.
  - **Scenario.** An agent wanting two matching masks can't tell which seed the sentence means.
  - **Fix.** Name the seed and what gives the per-tile values, shortly, or delete the sentence if no evidence says
    which seed was meant.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_guide.py::test_the_core_names_the_seed_and_the_values_of_matching_tile_masks` requires
      the line naming `Offset_Random_Seed` and `Luminance_Variation-Contrast` in the core's Library node facts. It
      failed on the old line, and again on a temporary revert after `/simplify` changed the test.
    - **Cause:** Step 2 deleted the list of `tile_generator`'s parameters, which gave "the seed" and "the mask" their
      meaning.
    - **Fix:** "The same layout and `Offset_Random_Seed` twice give a matching per-tile random mask, with
      `Luminance_Variation-Contrast` on the second." (69 characters more in the core). The evidence for the seed:
      `examples/build_dwarf_trimsheet.py:602-605` does exactly this ("Same layout/seed twice"), its `seed` passed to
      `Offset_Random_Seed`, and the second call adds `luminance_random`, which is `Luminance_Variation-Contrast`.
    - **Also covered:** the core's other kept fragments were reread for words leaning on deleted text: `bevel`'s line
      names its parameter, and the blend lines name their inputs.
  - Questioned by TST-833 (2026-11-24).

- [x] **TST-833 · The core's size is given as 7,534 characters, where it is 7,603** · `ROADMAP.md:28` · confirmed · follows TST-832, generation 2 · found 2026-11-24 by two reviewers (Opus)
  - **Defect.** Item 126's Done note says "the core went from 19,981 characters to 7,534", and the budget test's
    comment (`tests/unit/test_guide.py:217-218`) says "7,534 characters on 2026-11-24". TST-832's fix added 69
    characters and updated neither: the core is 7,603.
  - **Scenario.** Whoever reads the note or the comment takes the branch's result as 7,534 characters, while every
    session reads 7,603.
  - **Fix.** The core's final size in both, measured as `len(_parts()[0])`; "about 30 lines" still holds.
  - **Resolution: done**.
    - **Test:** none: no test reads the figure; the budget test guards the cap, not its comment's number.
    - **Cause:** TST-832's fix added 69 characters and TST-835's 64, and neither updated the figure.
    - **Fix:** the budget comment and item 126's Done note say 7,667, the core's final size, measured as
      `len(_parts()[0])`, after every other fix of the round. "About 30 lines of 200" still holds.
    - **Also covered:** `git grep "7,534\|7,603"` outside REVIEW.md and PLAN.md finds nothing.

- [x] **TST-834 · ROADMAP item 6 says "see GUIDE.md" for the wrong third-party blend table the guide no longer holds** · `ROADMAP.md:47` · confirmed · follows TST-831, generation 2 · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** Item 6 reads "(a public SD MCP's blend-mode table was wrong, see GUIDE.md)". Step 2 moved that
    sentence, row 41, into the comment at `tests/test_all_tools/facts/blend_cases.py:31-32`. TST-831's sweep looked
    for `GUIDE.md, X` and `GUIDE.md (X` only.
  - **Scenario.** A reader of item 6 looks in GUIDE.md for the evidence and finds nothing.
  - **Fix.** Point the item at `tests/test_all_tools/facts/blend_cases.py`, and sweep for other "see GUIDE.md" forms.
  - **Resolution: done**.
    - **Test:** none: no test reads pointers into GUIDE.md, a choice of the plan the user approved.
    - **Cause:** TST-831's sweep looked for `GUIDE.md, X` and `GUIDE.md (X` only.
    - **Fix:** item 6 says "see `tests/test_all_tools/facts/blend_cases.py`".
    - **Also covered:** `git grep -n -i -E "see (the )?GUIDE|see \`GUIDE|GUIDE\.md\)"` finds no other "see GUIDE.md";
      each bare "(GUIDE.md)" it lists names a fact the guide holds, checked one by one.

- [x] **TST-835 · The core no longer routes an agent to `read_designer_log`** · `mcp_server/GUIDE.md:21-58` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `main`'s Environment facts said "Plugin tracebacks land in Designer's log (`read_designer_log`; ...).
    Read it when the bridge misbehaves or a plugin change doesn't seem to load." Step 2 moved row 28 into
    `read_designer_log`'s own docstring and deleted row 26, so the core names the tool nowhere. An agent reads that
    docstring only once it has picked the tool, and no error message points to the log.
  - **Scenario.** An agent working in a user's project meets a bridge that misbehaves. Nothing it read sends it to
    the log.
  - **Fix.** One line of routing in `## Which tool for what`, for example "**Diagnose:** `read_designer_log` when the
    bridge misbehaves." The docstring keeps the detail.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_guide.py::test_the_core_routes_a_misbehaving_bridge_to_the_log` requires
      "**Diagnose:** `read_designer_log`" in the core's `## Which tool for what`. It failed before the fix.
    - **Cause:** Step 2 moved row 28 into `read_designer_log`'s docstring and deleted row 26, so the core named the
      tool nowhere.
    - **Fix:** "- **Diagnose:** `read_designer_log` when the bridge misbehaves." after **Output** (64 characters).
      The docstring keeps the detail.
    - **Also covered:** the core's other routing lines name every other tool `main`'s core named, but
      `launch_designer`, on purpose, and `view_node`, a parameter now in its `Field`.

- [x] **SRV-247 · `export_outputs`' docstring says its textures are within a few 1/65535 steps of the cooked render, measured on one height map** · `mcp_server/server_tools/output.py:55-56` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** "Its textures are within a few 1/65535 steps of the cooked render (render_sbs) at a few pixels." The
    only check, `tests/test_all_tools/render/checks.py:142-156`, compares `height.png` alone, allowing 8/65535. ROADMAP
    item 17 records two renders of one .sbsar differing "up to ~850 in AO". `main`'s core put item 17 beside the
    sentence; Step 1 moved that hint into a maintainer comment (`output.py:44`), so the docstring states the claim more
    firmly than the core did.
  - **Scenario.** An agent compares an exported AO map with `render_sbs`' and, seeing about 1% of difference, decides
    one of them is wrong.
  - **Fix.** Narrow the sentence to what is measured, with no new check, as the address-review skill prefers: for
    example that a height map was within a few 1/65535 steps at a few pixels.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_guide.py::test_export_outputs_says_which_map_was_measured_against_the_cooked_render`
      requires "An exported height map was within a few 1/65535 steps of the cooked render" in `export_outputs`'
      description, and "Its textures are within" gone. It failed on the old wording.
    - **Cause:** Step 1 moved the claim into the docstring as "Its textures", while its only check compares
      `height.png` alone.
    - **Fix:** the docstring (`mcp_server/server_tools/output.py`) says "An exported height map was within a few
      1/65535 steps of the cooked render (render_sbs) at a few pixels."
    - **Also covered:** `git grep "1/65535 steps"` finds no other copy; the check's comment, pointing at the docstring,
      still holds.

- [x] **SRV-248 · Grayscale Conversion Advanced's default, Desaturation, is stated in two places** · `mcp_server/server_tools/reference.py:182` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `analyze_reference`'s docstring says "(not the Advanced one, whose default is Desaturation)", and the
    scripting part's "The greys of a colour image" says "Its default is Desaturation" (`mcp_server/GUIDE.md:414-416`).
    On `main` the default was in the core alone, and the scripting part pointed to it. `.claude/rules/docs.md` keeps
    each fact in one place.
  - **Scenario.** A Designer that changes the default, which `bitmaps/palettes.py:115` would catch, needs two edits,
    and one may be missed.
  - **Fix.** The measured value stays in the scripting part's list. The docstring's aside says only "(not Grayscale
    Conversion Advanced)": what the agent does is the same.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_guide.py::test_the_default_of_grayscale_conversion_advanced_is_given_once` requires
      "(not Grayscale Conversion Advanced)" in `analyze_reference`'s description with no "Desaturation" there, and
      "Its default is Desaturation." in the scripting part's `## sd API gotchas`. It failed on its first assertion.
    - **Cause:** Step 1 moved the palette recipe into the docstring together with the measured default.
    - **Fix:** `reference.py`'s aside says "(not Grayscale Conversion Advanced)".
    - **Also covered:** no other tool description names Desaturation or the Advanced node
      (`mcp_server/server_tools/*.py`, `mcp_server/designer_helpers/*.py`).

- [x] **SRV-249 · `designer_status`' docstring doesn't say that library packages the tools loaded are listed among the user packages** · `mcp_server/server_tools/lifecycle.py:140-143` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** The listing loops over `getUserPackages()` (`lifecycle.py:166-169`). `describe_node` and `add` load
    library packages with `loadUserPackage` (`designer_helpers/describe.py:224-228`), and `_unload_new_packages`
    unloads only packages with no file (`describe.py:430-438`), so the library ones stay listed. `main`'s core said
    that loaded library packages count as user packages (row 24). Step 2 deleted it as maintainer detail, and TST-828
    put it back in the scripting part only.
  - **Scenario.** After a `describe_node('tile_generator')`, `designer_status` lists `.../packages/tile_generator.sbs`
    among the open user packages. The agent tells the user that package is theirs, or picks a graph in it and the
    edit is refused.
  - **Fix.** One clause in the docstring: library packages the tools loaded are listed too, their file in Designer's
    packages folder.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_guide.py::test_designer_status_says_the_library_packages_the_tools_loaded_are_listed`
      requires "library packages the tools loaded, their file in Designer's packages folder" in `designer_status`'
      description. It failed before the fix.
    - **Cause:** the listing loops over `getUserPackages()`, which keeps the library packages `describe_node` and
      `add` load, and Step 2 deleted row 24, which said so.
    - **Fix:** the docstring ends "The user packages include the library packages the tools loaded, their file in
      Designer's packages folder."
    - **Also covered:** the self-test's `LIBRARY_PACKAGES` snippet (`tests/test_all_tools/common.py:253`) lists them
      the same way; the scripting part's TST-828 sentence gives the API side.
