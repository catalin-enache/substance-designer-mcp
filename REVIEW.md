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

**Last used:** PLG-45, SRV-244, HLP-254, INS-46, TST-826, AGT-132.

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
| Low-medium | 0 | 2 |
| Low | 0 | 27 |
| **Total** | **0** | **29** |

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
| 2026-11-23, step 1 (describe_graph(selected=True)) | Opus (developer) | 1 | 0 | 0 | 418,055 | 35 min |
| 2026-11-23, the first review (a Sonnet round on step 1) | Sonnet | 3 | 8 [2 Low-medium, 6 Low] | 8 [2 Low-medium, 6 Low] | 456,591 | 12 min |
| 2026-11-23, the first review's fixes | Opus (developer) | 1 | 0 | 0 | 108,321 | 15 min |
| 2026-11-23, the second review (a Sonnet round on the first review's fixes) | Sonnet | 2 | 2 [2 Low] | 2 [2 Low] | 303,039 | 10 min |
| 2026-11-23, the second review's fixes | Opus (developer) | 1 | 0 | 0 | 15,759 | 2 min |
| 2026-11-23, the third review (the Opus round on the entire branch) | Opus | 3 | 4 [4 Low] | 4 [4 Low] | 506,319 | 13 min |
| 2026-11-23, the third review's fixes | Opus (developer) | 1 | 0 | 0 | 30,533 | 4 min |
| 2026-11-23, step 2 (setSelected and the Parameters panel) | Opus (developer) | 1 | 0 | 0 | 273,438 | 19 min |
| 2026-11-23, step 2b (the panel left on an unloaded package) | Opus (developer) | 1 | 0 | 0 | 116,336 | 18 min |
| 2026-11-23, step 3 (ROADMAP item 127, a blend of a grey image and a colour one) | Opus (developer) | 1 | 0 | 0 | 273,944 | 18 min |
| 2026-11-23, step 4 (the user's rules on ROADMAP proposals and KISS) | Opus (developer) | 1 | 0 | 0 | 170,463 | 7 min |
| 2026-11-23, the fourth review (a Sonnet round on steps 2 to 4) | Sonnet | 3 | 7 [7 Low] | 7 [7 Low] | 478,117 | 7 min |
| 2026-11-23, the fourth review's fixes | Opus (developer) | 1 | 0 | 0 | 65,311 | 6 min |
| 2026-11-23, the fifth review (the Opus round on the entire branch) | Opus | 4 | 8 [8 Low] | 8 [8 Low] | 668,516 | 10 min |
| 2026-11-23, the fifth review's fixes | Opus (developer) | 1 | 0 | 0 | 86,635 | 9 min |
| **Total** | | **25** | **29 [2 Low-medium, 27 Low]** | **29 [2 Low-medium, 27 Low]** | **3,971,377** | **185 min** |

## Review log

### 2026-11-23: the first review, a Sonnet round on step 1

- **Scope:** `git diff b5eedcb aaedcfe -- . ':(exclude)PLAN.md'` (step 1, `describe_graph(selected=True)`).
- **How:** three Sonnet reviewers: the server, the helper and their unit tests; the live checks and the Designer
  scripts; the docs and the approved text, point by point. No tests run, no probes. Settled as wrong, or not raised:
  - the "no graph in the editor" fact failing when the category runs whole, after the self-test graph was opened in
    the editor many times, or in the user's Designer with their graph open: the developer's two scratch runs of the
    whole category passed it (25 checks), and in them the self-test graph, loaded and in the editor before the facts
    script, left no view once the script's package closed (one graph view at a time, measured);
  - the Home screen: it is current only after a fresh start, before any graph opens (GUIDE.md:628-629), so it takes
    the no-graph path (TST-809);
  - the scene items' z values and the lookup by a point in GUIDE: they are how the check finds an item, kept in its
    script's docstring, not a fact the tool relies on;
  - `select_items.py` and `selection_facts.py` each holding the item lookup: scripts import no siblings, and the facts
    check measures that each item found selects what it should;
  - the selection dropped by opening another graph, said in the core and the scripting part: the core's line is what
    an agent using only the tools needs.
- **Unspecified:** beyond the approved text, and documented in the `Field` description or unit-tested: a selection of
  frames, comments or pins with no node says "no node selected in the editor, only ..."; pins are named; `parameter`
  is refused with `selected`. For the user, when the reviews converge.
- **Not verified:** none.
- **Resolutions assessed:** none (no earlier entries).
- **Findings:** TST-807, TST-808 (Low-medium); TST-809, TST-810, SRV-243, HLP-254, TST-811, TST-812 (Low). No chains.
- **Suggested order:** TST-808, TST-809, TST-807, TST-810, SRV-243, HLP-254, TST-811, TST-812.
- **Checked and found fine:** each approved behaviour delivered (nothing selected, the objects line, the graph given
  and another refused, the refusals with `node_ids`, `node_id` and `function` before Designer, the editor's current
  graph read); the refusals' order, ahead of the getters, which raise once no graph view is left; the non-deprecated
  getters; the call string and the unit tests failing without their code; the fixture reaching the helper's local
  imports; the facts telling None from empty, a Dot as a node, frames, comments and pins as objects, a link in neither,
  the editor's view read rather than the oldest; the clean-up in `finally`, and each new check run alone; the 100 ms
  poll and its limit against `.claude/rules/waits.md`; the scripts' Qt calls other than `parentItem()`; GUIDE.md:597-602
  agreeing with the new bullet; README's Tools table and category row; no `Any` in the new code.

### 2026-11-23: the second review, a Sonnet round on the first review's fixes

- **Scope:** `git diff 2edd3ee ecca294 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the helper, the server and the unit tests; the live checks, the Designer scripts and
  the docs. No tests run, no probes. Settled as wrong, or not raised:
  - GUIDE's `parentItem()` rule too narrow, if `topLevelItem()` also hands the node's item over: the developer
    measured `topLevelItem()` alone leaving it Designer's (its report of the first review's fixes);
  - "still in the graph" in GUIDE's `parentItem()` bullet as unseen: the developer's step-1 report saw it (node items
    from 2 to 1 after `gc.collect()`, the node still in the graph);
  - `selection_facts.py` picking a lingering view of `parent_item_facts.py`'s closed graph: the developer's last
    scratch run of the whole category, in its final order, passed (29 checks);
  - SRV-243's "within CLAUDE_CODE_LIMIT", which the limit's test can't see (it measures the docstring, not the input
    schema): no effect on a user; `_MORE_HINT`'s default text unpinned on the whole-graph path: unchanged there.
- **Unspecified:** none.
- **Not verified:** none.
- **Resolutions assessed:** TST-807 to TST-812, SRV-243 and HLP-254. All hold; SRV-243 questioned by SRV-244 and
  TST-807 by TST-813, each for wording.
- **Findings:** SRV-244, TST-813 (Low). A few Lows: once the developer fixes them, step 1's reviews are done, and the
  Opus round on the entire branch follows. The longest chains: SRV-243 → SRV-244 and TST-807 → TST-813, generation 2.
- **Suggested order:** TST-813, SRV-244.
- **Checked and found fine:** `_more`'s `hint` through its two callers and the server's call strings; the unit tests'
  two fixtures, the new test running the real `describe_graph`; the `parentItem` check's guard (one wrapper per item,
  invalidated in a `finally`, the package unloaded) and its failing on a deleted item; the function-graph check's
  clean-up and its failing on leftover state; the no-graph refusal after the poll; the narrowed and strengthened facts
  against Designer's stub; the category's time and place; ROADMAP item 32's note; the table's sums.

### 2026-11-23: the third review, the Opus round on the entire branch

- **Scope:** `git diff main...HEAD -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'` at fcb7b6e, with REVIEW.md as the
  record. ROADMAP items 126 and 127, added on the user's word, left out.
- **How:** three Opus reviewers: the server, the helpers and the unit tests; the live checks and the Designer scripts;
  the docs and the approved text, point by point. No tests run, no probes. Not raised, or not worth a fix:
  - `check_describe_graph_lists_the_editors_selection`'s docstring, "selected through the graph view, as a person
    would": `setSelected` isn't a click (GUIDE.md:599-601), but nothing is misled;
  - a library graph in the editor read when named by `graph`, which `find_graph` refuses by name: a read, and
    `_library_refusal`'s text says read tools work on a library graph in focus.
  New evidence for the second review's settled lingering view: `link_display`'s designer fact measures an unload's
  widgets gone before the next call starts.
- **Unspecified:** none new (the first review's three stand, for the user).
- **Not verified:** whether `Shiboken.invalidate()` keeps the item on Windows (TST-817's fix skips the check in the
  user's Designer instead).
- **Resolutions assessed:** all ten. All hold; TST-812 questioned by TST-815, TST-810 by TST-816, TST-807 by TST-817.
- **Findings:** TST-814, TST-815, TST-816, TST-817 (Low). A few Lows: the reviews look converged once the developer
  fixes them. The longest chains: TST-807 → TST-813, TST-817; TST-810 → TST-816; TST-812 → TST-815; SRV-243 → SRV-244;
  generation 2.
- **Suggested order:** TST-817, TST-816, TST-815, TST-814.
- **Checked and found fine:** the new path end to end (refusals before Designer, the call string, the helper's
  refusal order against the measured facts, single-line errors through `_checked`); `_more`'s default text unchanged
  and `describe_graph`'s `hint` last with a default, no caller affected; each unit test failing without its code;
  each live check failing without what it guards, its clean-up and its running alone; the pool's conditions (no
  clipboard, focus or timing); the scripts' Qt calls and the `invalidate` guard's order; every point of the approved
  text, the core line, the `Field` and the docstring, README's rows; no contradiction with GUIDE or DECISIONS.md.

### 2026-11-23: the fourth review, a Sonnet round on steps 2 to 4

- **Scope:** `git diff df6f956 eacf48a -- . ':(exclude)PLAN.md'` (steps 2 and 2b, the Parameters panel; step 3, ROADMAP
  item 127; step 4, the user's rules on ROADMAP proposals and KISS).
- **How:** three Sonnet reviewers, one per step group; the user's KISS rule (2026-11-23) given for judging. No tests
  run, no probes. Not worth a fix, by that rule, or settled:
  - the panel check's one event pass over a panel left on an unloaded graph, in a run in the user's Designer: no
    worse than `CLEAN`, which leaves it there for good, and 21 trials crashed nothing;
  - the three scripts taking the first `areaC_` dock, not the visible one: only in a layout no run has seen
    (DECISIONS.md, Low-value findings);
  - `setExplorerSelection` of a graph already selected possibly not turning the panel: the developer's scratch run of
    the whole category in `run()`'s order passed (45 checks), and each check alone;
  - no positive control of the panel's title for a frame or a comment: the node's and the Dot's were seen by the
    developer's click probe;
  - the blend checks' shared failure detail cut at 150 characters, and `TYPE_CASES`' `str` where a `Literal` fits:
    a failure message only, and the precedent's same typing;
  - no unit test pinning the two new rules' text: the rules are docs, and a pin of a skill section's name holds no
    behaviour;
  - `categories.py`'s 16 s and 50 s comments not counting the new checks: dated figures, within their spread.
- **Unspecified:** a step tried on the spot that changes what the branch delivers: settled by the stop list (AGT-127).
- **Not verified:** none.
- **Resolutions assessed:** none in scope.
- **Findings:** AGT-126 to AGT-129, TST-819 to TST-821 (Low). A few Lows: step 2 to 4's reviews are done once the
  developer fixes them; then the Opus round on the entire branch.
- **Suggested order:** TST-821, TST-820, AGT-126, AGT-127, AGT-129, AGT-128, TST-819.
- **Checked and found fine:** the panel checks failing without what they guard, their clean-up in `finally` and
  `CLEAN`, the `graph` argument at every call site; each blend comparison telling Designer's behaviour from the
  alternatives (grey promoted to colour, opaque black, a source ignored), the float precision of the `!=` sides, the
  memo by `ctx.scratch` and each check running alone, the precedent still guarding what it did; the GUIDE core
  untouched; the two rules' quotes exact and dated, each rule in one home, AGENTS.md within its budget.

### 2026-11-23: the fifth review, the Opus round on the entire branch (steps 1 to 4)

- **Scope:** `git diff main...HEAD -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'` at d773437, with REVIEW.md as the
  record.
- **How:** four Opus reviewers: the server, the helpers and the unit tests; the live checks and the Designer scripts;
  GUIDE, README and ROADMAP; the project's rules (AGENTS.md, `.claude/`, `docs/`). The user's KISS rule given for
  judging. No tests run, no probes. Not worth a fix, by that rule, or settled:
  - `describe_graph(selected=True)`'s header counting the whole graph's nodes and frames: `node_ids`' own behaviour,
    as the approved text asks (the first review's note);
  - `set_link_display`'s reload leaving the panel on the unloaded package: older behaviour, and 21 trials crashed
    nothing;
  - the panel title read after an unload not telling an emptied panel from a stale one, the new order of the panel
    and getters scripts in the user's Designer (an unload's widgets go before the next call, `link_display`'s fact),
    `blend_opacity.py`'s packages, the `cleared` case's one event pass;
  - ROADMAP item 127's "`opacity` connected or not" for two feeds, GUIDE's "link of a LUM16 grey source into" read as
    an input: generation-2 wording that changes nothing anyone does;
  - AGENTS.md's "won't make the code complex" for the user's "over complex", `address-review`'s repeated "instead", a
    developer run's new problem with no log entry of its own, a random failure's ROADMAP row (a standing decision).
- **Unspecified:** none new.
- **Not verified:** none.
- **Resolutions assessed:** all 21 in scope. All hold; AGT-126 questioned by AGT-131, TST-811 by TST-825.
- **Findings:** TST-822 to TST-826, AGT-130 to AGT-132 (Low): eight one-line or wording fixes, none in the tools' code.
  The lead judges the reviews converged: "about 5 to 7" Lows, and these are each a line. The longest chains:
  TST-807 → TST-813, TST-817; AGT-126 → AGT-131; TST-811 → TST-825; generation 2.
- **Suggested order:** TST-824, TST-826, TST-822, TST-825, TST-823, AGT-130, AGT-131, AGT-132.
- **Checked and found fine:** the approved step 1 point by point; `_more` and `describe_graph`'s `hint` with their
  callers; each unit test and live check failing without what it guards; the panel checks, the `parentItem` skip and
  the user's graph restored in their Designer; the blend comparisons and the memo; the waits; every GUIDE sentence's
  check and "seen" mark; README's rows; the rules' quotes exact, one home each, the pointers resolving, AGENTS.md at
  14,091 of 15,000 bytes.

---

## High

## Medium-high

## Medium

## Low-medium

- [x] **TST-807 · The parentItem() crash measured on a graph view's items is only in a test script's docstring, not in GUIDE** · `tests/test_all_tools/editor_open_and_zoom/designer_scripts/select_items.py:8` · confirmed · found 2026-11-23 by two reviewers (Sonnet)
  - **Defect.** "Never parentItem(): called on a node's comment, it handed the node's item to Python, which deleted it
    with its wrapper (measured 2026-11-23: the node left the view, and a later deletion crashed Designer)." GUIDE.md
    has no `parentItem`. Its scripting part (GUIDE.md:599-601) shows `setSelected(True)` on a node's scene item, and
    `.claude/rules/docs.md` puts Designer and PySide pitfalls there.
  - **Scenario.** An agent writing Qt code walks from a node's comment item to its node with `parentItem()`: the node
    leaves the view, and a later garbage collection can crash the user's Designer.
  - **Fix.** A line in GUIDE's scripting part (Designer UI): don't call `parentItem()` on a graph view's scene items,
    with what it did. Its "designer facts" check measures the ownership handed over
    (`shiboken6.Shiboken.ownedByPython`) in a way that can't crash the run. If no such check is found, report it:
    whether the line goes in without a check is the user's.
  - **Resolution: done**.
    - **Test:** `check_parent_item_hands_a_scene_item_to_python`, with `designer_scripts/parent_item_facts.py`, in a
      package of its own: `parentItem()` on a node's comment item turns the node item's `ownedByPython` from False to
      True, and `Shiboken.invalidate()` on that wrapper in a `finally` leaves both node items in the view. Its first
      version, which called `topLevelItem()` first, read False: that order keeps the hand-over from happening
      (measured once, in the script's docstring as why nothing is called first).
    - **Fix:** a GUIDE scripting bullet (Designer UI): never call `parentItem()` on the graph view's scene items, with
      the hand-over and `invalidate` checked, and the deletion and the crash marked "seen 2026-11-23", as GUIDE.md:598
      marks what was seen. `select_items.py` points to GUIDE.
  - Questioned by TST-813 (2026-11-23).
  - Questioned by TST-817 (2026-11-23).
  - Note (2026-11-23): `checks.py:156`'s "# last: it leaves no graph in the editor" marks only the getters' check;
    `check_parent_item_hands_a_scene_item_to_python` before it leaves none either, which nothing after it depends on
    today (a reviewer of the third review, Opus).

- [x] **TST-808 · The live check selects every node of its graph, so it can't tell the selection from the whole graph** · `tests/test_all_tools/editor_open_and_zoom/checks.py:166` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** `select_items` gets `nodes=[clouds, slope]`, and the check wants
    `set(positions(listed)) == {clouds, slope}`. The prepared graph has exactly those two nodes
    (`preparations.py:9-31`: `create_graph`, two `add` ops, a frame).
  - **Scenario.** A helper that listed every node once anything is selected passes the check; only the "nothing
    selected" case tells them apart. The user's case, one node of several, is never read live.
  - **Fix.** Select one node (`slope`) and the frame, and require `slope` listed and `clouds` not.
  - **Resolution: done**.
    - **Test:** `check_describe_graph_lists_the_editors_selection` selects `slope` and the frame 'Shape' and requires
      `{slope}` listed. With `describe_selected` made to list every node once anything is selected (a scratch
      change, reverted), "selected lists only the node selected" and "takes the editor's graph by name" failed in a
      scratch run on port 9895: clouds was listed too.
    - **Fix:** the check itself.
    - **Also covered:** the frame's `setSelected` selected none of the nodes inside it (only slope reported).

## Low

- [x] **TST-809 · No live check of the refusals for no graph in the editor and a function graph in front** · `tests/test_all_tools/editor_open_and_zoom/checks.py:153` · confirmed · found 2026-11-23 by two reviewers (Sonnet)
  - **Defect.** The approved step: "no graph in the editor, the Home screen, or a function graph in front: refused
    plainly". `describe_selected` raises for both (`describe.py:158`, and the `isinstance` refusal after it), and only
    `tests/unit/test_describe_selected.py`'s faked UI manager reaches them. AGENTS.md asks a live check for what
    depends on Designer.
  - **Scenario.** `_current_graph()` or the getters behave in Designer otherwise than the fake does, and an agent gets a
    traceback where the tool should refuse plainly.
  - **Fix.** After `check_what_the_selection_getters_give`'s poll, which leaves no graph in the editor, call
    `describe_graph(selected=True)` and require the plain refusal. The function graph in front only if cheap (the
    package needs a function graph); otherwise say what covers it: the unit test, and GUIDE.md:606-607's checked fact
    that `openResourceInEditor` makes a function graph the current graph.
  - **Resolution: done**.
    - **Test:** after `check_what_the_selection_getters_give`'s poll, `describe_graph(selected=True)` must give "No
      graph is open in Designer's editor, ..."; the new `check_describe_graph_refuses_a_function_graph_in_front`
      makes a function graph with `set_function`, puts it in front with `open_graph(function=...)`, requires "is not a
      compositing graph", and reopens the graph in a `finally`. With both refusals taken out of the helper (a scratch
      change), the first gave `APIException: SDApiError.InvalidArgument` and the second "graph selection_probe:
      nothing selected in the editor".
    - **Fix:** the checks themselves.
  - Note (2026-11-23): `check_describe_graph_refuses_a_function_graph_in_front` leaves the function graph `selection_probe`
    in the self-test graph's package; no later check reads it, and `CLEAN` unloads the package (a reviewer of the third
    review, Opus).

- [x] **TST-810 · GUIDE's new selection facts, a check's label and a script's docstring say more than the checks measure** · `mcp_server/GUIDE.md:615-620` · confirmed · found 2026-11-23 by two reviewers (Sonnet)
  - **Defect.**
    - "Each is an `SDArray`": `selection_facts.py`'s `read()` prints `sorted(...)` of the items, which tells an
      empty array from None but not its type.
    - "`getCurrentGraphSelection()` is the deprecated name of the first": no check calls it (Designer's stub marks it
      deprecated).
    - "Opening another gives that graph's": `mcp_selftest_selection_other` never has a selection, so the read can't tell
      that graph's selection from none. The check's label (`checks.py:240`) says "another opened has its own".
    - `selection_facts.py:4` and `:64` say the getters are read "before any event is processed"; `read(..., scene())`
      runs `processEvents()` in `scene()` first for the three which-graph cases.
  - **Scenario.** A reader takes the unmeasured parts as measured; a later change breaks one and no check fails.
  - **Fix.** Narrow each to what is measured (or select a node in the other graph and require it, for the third).
  - **Resolution: done**.
    - **Test:** the 'another graph opened' case now has a node selected in that graph (`..._other scene=1
      nodes=['uniform']`), passing in the scratch run; "the first opened again" still reads `nodes=[]`.
    - **Fix:** GUIDE says "empty, not None" instead of `SDArray`, and the deprecated getter as the sd API's marking
      (`sd/api/qtforpythonuimgrwrapper.py`); `selection_facts.py`'s docstrings no longer say "before any event is
      processed" for the cases that open a graph.
  - Questioned by TST-816 (2026-11-23).

- [x] **SRV-243 · selected says "nothing selected" when only a link is selected, and the parameter's description doesn't say links aren't read** · `mcp_server/server_tools/discovery.py:62` · confirmed · found 2026-11-23 by two reviewers (Sonnet)
  - **Defect.** GUIDE.md:616: "A selected link is in neither" getter, measured by the 'a link' case. With only a link
    selected, `describe.py:182` prints `graph X: nothing selected in the editor`. The `Field` description names "the
    frames, comments and pins selected too", and nothing an agent reads says links aren't reported.
  - **Scenario.** The user selects the wire they mean and asks "why is this dark"; the agent is told nothing is
    selected.
  - **Fix.** A clause in the `Field` description: a selected link isn't reported (within `CLAUDE_CODE_LIMIT`).
  - **Resolution: done**.
    - **Test:** `test_server.py::test_selected_says_a_selected_link_is_not_read` failed on the description without
      the clause.
    - **Fix:** the `Field` description adds "; a selected link isn't read"; the description limits' tests pass.
  - Questioned by SRV-244 (2026-11-23).

- [x] **HLP-254 · A capped selection's last line says "filter node_ids", which selected refuses** · `mcp_server/designer_helpers/describe.py:184` · confirmed · found 2026-11-23 by two reviewers (Sonnet)
  - **Defect.** `describe_selected` ends in `describe_graph(g, node_ids, include_params, limit)`, whose `_more`
    (`core.py:397`) prints `'... %d more nodes (raise limit or filter node_ids)'`.
  - **Scenario.** `describe_graph(selected=True, limit=5)` with 10 nodes selected; the agent follows "filter node_ids"
    with `selected=True` and is refused.
  - **Fix.** A hint that fits the selection, such as "raise limit" only, for `selected`.
  - **Resolution: done**.
    - **Test:** `test_describe_selected.py::test_a_capped_selection_says_to_raise_limit_not_to_filter_node_ids` runs
      the real `describe_graph` on faked nodes, 3 selected and limit 1; it failed with "... 2 more nodes (raise limit
      or filter node_ids)".
    - **Fix:** `_more(nodes, limit, hint=_MORE_HINT)` in `core.py`, passed on by `describe_graph(..., hint=...)`;
      `describe_selected` passes `hint='raise limit'`.
    - **Also covered:** `describe_functions.py:66` keeps the default, where `node_ids` is valid; `search_nodes`'
      "refine the query or raise limit" names its own parameters only.

- [x] **TST-811 · categories.py still gives editor_open_and_zoom 4 s, which its new checks made slower** · `tests/test_all_tools/categories.py:61` · confirmed · found 2026-11-23 by two reviewers (Sonnet)
  - **Defect.** `editor_open_and_zoom.run,  # 4 s: open_graph, ... describe_graph(selected)`: the branch added to the
    comment and kept the time. The category now builds a package, runs three scripts and polls for a view to go; the
    developer's scratch run took 12.2 s, its server's start included.
  - **Scenario.** The pool's order, slowest first, is read from these comments; this one is out by a factor of three.
  - **Fix.** The time measured in a scratch run, dated like the newer comments, and the row moved to its place in
    the order.
  - **Resolution: done**.
    - **Test:** docs only (a comment): two scratch runs of the category, 15.5 s and 16.7 s with their server's start.
    - **Fix:** `# 16 s (2026-11-23, two scratch runs, with their server's start: 15.5 s, 16.7 s)`, in `facts`'s dated
      form, the row moved between `link_display` (16 s) and `inputs` (15 s). README's category row and the module
      docstring name the new checks.
  - Questioned by TST-825 (2026-11-23).

- [x] **TST-812 · ROADMAP item 32 is checked with its Approach still naming the deprecated getter** · `ROADMAP.md:45` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** "from `getQtForPythonUIMgr().getCurrentGraphSelection()` (the sd API has it, per graph view too)";
    the code reads `getCurrentGraphSelectedNodes()` and `getCurrentGraphSelectedObjects()`, the current view only,
    and the item has no Done note, as most checked items do.
  - **Scenario.** A reader of the checked item looks for the deprecated getter in the code.
  - **Fix.** A "Done 2026-11-23: ..." note naming the getters used, pointing to GUIDE.md, Designer UI.
  - Questioned by TST-815 (2026-11-23).

  - **Resolution: done**.
    - **Test:** docs only (the docs tests).
    - **Fix:** item 32's "Done 2026-11-23" note names the two getters used and points to GUIDE.md, Designer UI, The
      editor's selection.

- [x] **SRV-244 · describe_graph's docstring says selected lists what the user selected, where links aren't read and frames, comments and pins are only named** · `mcp_server/server_tools/discovery.py:73` · confirmed · follows SRV-243, generation 2 · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** "With selected, it lists what the user selected in the editor, or says nothing is." SRV-243's fix put
    "a selected link isn't read" in the `Field` description; the docstring, which an agent reads first, still says the
    tool lists what was selected.
  - **Scenario.** With only a link selected, an agent reading the docstring expects the link listed and gets "nothing
    selected".
  - **Fix.** Wording only (generation 2): the nodes selected, as the `Field` says.
  - **Resolution: done**.
    - **Test:** docs only (wording, generation 2): the docs tests and `test_server.py`.
    - **Fix:** "With selected, it lists the nodes the user selected in the editor, or says none is."
    - **Also covered:** GUIDE.md:47, README.md's Tools table, `describe_selected`'s docstring and the check's already
      say "nodes".

- [x] **TST-813 · parent_item_facts.py's docstring says nothing else is called on the comment's item before parentItem(), where its lookup calls three methods on it** · `tests/test_all_tools/editor_open_and_zoom/designer_scripts/parent_item_facts.py:5` · confirmed · follows TST-807, generation 2 · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** "Nothing else is called on the comment's item first: after topLevelItem() on it, parentItem() left
    the node's item Designer's". `items_at` (lines 39-46), run by `node_items` and the comment's lookup (lines 65-66)
    before `parentItem()`, calls `flags()`, `zValue()` and `sceneBoundingRect()` on every scene item, the comment's
    included.
  - **Scenario.** A maintainer trusts that the hand-over was measured on an untouched item, and reads the
    `topLevelItem()` effect as one of any earlier call.
  - **Fix.** Say which calls precede `parentItem()` here, and that `topLevelItem()` first was the one that kept the
    hand-over from happening.

  - **Resolution: done**.
    - **Test:** docs only (wording, generation 2): the docs tests.
    - **Fix:** the docstring names what is called on the comment's item before `parentItem()` (`flags()`, `zValue()`,
      `sceneBoundingRect()`, to find it), and says the script calls no `topLevelItem()` on it, after which
      `parentItem()` left the node's item Designer's.
    - **Also covered:** no other copy of the sentence; GUIDE's bullet makes no `topLevelItem()` claim.

- [x] **TST-814 · The unit tests' never() blames "no compositing graph in the editor", where two of its three tests have a graph in front** · `tests/unit/test_describe_selected.py:37` · confirmed · found 2026-11-23 by two reviewers (Opus)
  - **Defect.** `raise AssertionError("read with no compositing graph in the editor, where Designer's getters raise")`
    is the getters' fake in `test_another_graph_is_refused_naming_the_one_in_the_editor` (a compositing graph in
    front) and `test_a_function_graph_in_the_editor_is_refused_before_the_getters`, where the getters don't raise
    (GUIDE.md, The editor's selection: they raise once no graph view is left).
  - **Scenario.** A change reads the getters before the graph name's check; the test fails pointing at a cause its
    own set-up doesn't have.
  - **Fix.** A message that says what went wrong without a cause, such as "the selection read before a refusal".
  - **Resolution: done**.
    - **Test:** the file's tests pass with the new message (a message only, seen when a test fails).
    - **Fix:** `never()` raises `AssertionError('the selection read before a refusal')`.
    - **Also covered:** `run()`'s comment above the last two checks says each leaves no graph in the editor (the note
      under TST-807).

- [x] **TST-815 · ROADMAP item 32's Done note says both getters replace the deprecated one** · `ROADMAP.md:46` · confirmed · follows TST-812, generation 2 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** "it reads the getters that replace that deprecated one, `getCurrentGraphSelectedNodes()` and
    `getCurrentGraphSelectedObjects()`". Designer's stub (`sd/api/qtforpythonuimgrwrapper.py`) names only
    `getCurrentGraphSelectedNodes` in its deprecation notice, and GUIDE.md:617 says "in favour of the first".
  - **Scenario.** A reader takes the old getter for one that also gave frames and comments; two docs disagree.
  - **Fix.** Wording only (generation 2): the first replaces it, the second is the objects' getter.
  - **Resolution: done**.
    - **Test:** docs only (wording, generation 2): the docs tests.
    - **Fix:** the note reads `getCurrentGraphSelectedNodes()`, "which replaces that deprecated getter", and
      `getCurrentGraphSelectedObjects()`.

- [x] **TST-816 · GUIDE says getCurrentGraph() gives None with no graph in the editor, which the check reads only once the view is gone** · `mcp_server/GUIDE.md:621` · confirmed · follows TST-810, generation 2 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** "With no graph in the editor, `getCurrentGraph()` gives None. Once Designer's event loop has removed
    the closed graph's view (`getGraphViewIDCount()` 0), both getters raise". The check requires
    `'CURRENT=None VIEWS=0'` (`checks.py:284`); the poll's earlier reads, while the view lingers, are dropped.
  - **Scenario.** A script reads `getCurrentGraph()` in the call that unloaded the editor's graph, or the next, and
    trusts None there.
  - **Fix.** Wording only (generation 2): None once the view is gone, as measured.
  - **Resolution: done**.
    - **Test:** docs only (wording, generation 2): the docs tests.
    - **Fix:** "Once the editor's graph is closed and Designer's event loop has removed its view
      (`getGraphViewIDCount()` 0), `getCurrentGraph()` gives None and both getters raise ..." : the one condition the
      check reads.

- [x] **TST-817 · The parentItem() facts check runs in the user's own Designer, in a run there (Windows)** · `tests/test_all_tools/editor_open_and_zoom/checks.py:155` · confirmed · follows TST-807, generation 2 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** `await check_parent_item_hands_a_scene_item_to_python(ctx)` runs whatever `ctx.was_running`, which
    `__main__.py:124` sets for a run in a Designer the user opened. The check makes the call GUIDE says never to make
    (GUIDE.md, Designer UI), guarded by `Shiboken.invalidate()`, measured on macOS only.
  - **Scenario.** On Windows the hand-over or `invalidate` behaves otherwise, and the user's Designer, with their
    unsaved work, crashes on a later garbage collection.
  - **Fix.** Skip it when `ctx.was_running`, as `editor_panels_and_fit/checks.py:90` does; every Designer the
    self-test starts still measures it.

  - **Resolution: done**.
    - **Test:** `tests/unit/test_selftest_check_setups.py::test_the_parent_item_facts_run_only_in_a_designer_the_self_test_started`,
      parametrized on `was_running` as TST-258's test is, on `selftest_fakes.Designer`: in the user's Designer it
      failed with `AssertionError: ['run_designer_script']`, the script run there.
    - **Cause:** the check had no `ctx.was_running` guard, unlike `editor_panels_and_fit/checks.py:90`.
    - **Fix:** the check starts with a skip when `ctx.was_running`, its reason saying `parentItem()` is never called
      in the user's Designer; every Designer the self-test starts still runs it.
    - **Also covered:** the category's other checks call only `setSelected`, `scene.items()`, the sd API and
      `set_function` in the user's Designer, never `parentItem()`, a synthetic key event or a click.

- [x] **AGT-126 · KISS has no way to close a review finding about a very unlikely case, and collides with the won't fix route** · `.claude/skills/project-code-review/SKILL.md:166` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** AGENTS.md now says "Don't address very extreme cases that won't likely happen and need complex code"
    (Keep it simple). The review skills still settle a suspicion only as right or wrong (`project-code-review` step 4),
    and a real finding left unfixed because "the fix costs far more than the harm" is a won't fix, the user's
    decision, with a DECISIONS.md entry (`address-review` step 7). The user said such cases "dont have to go into a
    decision".
  - **Scenario.** A reviewer raises a real but very unlikely case whose fix needs complex code: the lead either stops
    the loop for the user and adds an entry, or drops it with no wording to record it.
  - **Fix.** The lead's settling, step 4: a real suspicion that is such a case is not written as a finding; the review
    log names it as not worth a fix (AGENTS.md, Keep it simple). `address-review`'s won't fix criterion on cost points
    to it. No won't fix, no DECISIONS.md entry, no question to the user.
  - **Resolution: done**.
    - **Test:** docs only: the docs tests.
    - **Fix:** `project-code-review` step 4: "A real suspicion that is a very unlikely case whose fix needs complex code
      isn't written as a finding: the review log names it as not worth a fix (AGENTS.md, Keep it simple)."
      `address-review` step 7's criterion on cost points to it; TEMPLATE.md's How field names suspicions "settled as
      wrong or not worth a fix".
  - Questioned by AGT-131 (2026-11-23).

- [x] **AGT-127 · The delegate skill says a ROADMAP proposal waits for convergence, where a finding to move is asked at once** · `.claude/skills/delegate/SKILL.md:71` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** "Such a proposal waits for the report that the reviews converged", said of every stage, "addressing
    findings" included; the same skill's stop list (lines 53-54), `address-review` step 7 and `project-code-review`
    step 7 ask a finding to move to ROADMAP.md at once, and step 8 allows "at once when the next step needs it".
    Also, a step tried on the spot may change what the branch delivers, which the stop list sends to the user first;
    the new paragraph doesn't say so.
  - **Scenario.** The lead holds a finding for ROADMAP until convergence; it stays open, against the convergence
    report's "none is still open".
  - **Fix.** A proposal that isn't a finding waits for the convergence report; a finding to move is asked at once; a
    step that changes what the branch delivers waits for the user's word (the stop list).
  - **Resolution: done**.
    - **Test:** docs only: the docs tests.
    - **Fix:** the rule says a step that changes what the branch delivers waits for the user's word first; a proposal
      that isn't a finding waits for the convergence report; a finding to move to ROADMAP.md is asked at once.
    - **Also covered:** `docs/agent-workflow.md`'s retelling the same.

- [x] **AGT-128 · Four lines still invite a ROADMAP proposal without the new rule's condition** · `.claude/rules/docs.md:44` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.**
    - `.claude/rules/docs.md:44`: "Propose new ideas to the user, who decides each one." (pinned by
      `test_review_lookup.py`, AGT-107);
    - `address-review:148-149`, won't fix criterion: "Work worth doing one day is a ROADMAP.md item instead";
    - `docs/agent-workflow.md:133-134`: "it isn't work for later, which is a ROADMAP item instead";
    - `.claude/agents/developer.md:124`: "what the lead should propose to the user ...: a ROADMAP.md item".
  - **Scenario.** An agent reads one of them, not the `delegate` rule, and proposes an item the branch could take on.
  - **Fix.** Each says "the branch can't take on", or points to the rule; the pinned sentence and its test together.
  - **Resolution: done**.
    - **Test:** `test_review_lookup.py::test_decisions_and_roadmap_are_proposed_while_reviewing_and_addressing_never_at_a_cleanup`'s
      pin changed to the new sentence, seen failing on the old one, then passing.
    - **Fix:** docs.md "Propose the ideas the branch can't take on to the user"; `address-review`'s won't fix criterion
      "Work worth doing one day that the branch can't take on"; `docs/agent-workflow.md` "when the branch can't take
      it on"; `developer.md:124` "a ROADMAP.md item the branch can't take on" (reaches agents started after the
      user's next message).

- [x] **AGT-129 · address-review says a choice made in the user's name never goes in DECISIONS.md, stronger than the user's words** · `.claude/skills/address-review/SKILL.md:179` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** "A choice the lead or the developer makes in the user's name, of how to do something, never goes
    there." The user: such choices "dont have to go into a decision", and an entry "should be proposed wisely and only
    if it has a real weight"; the sentence before allows one with real weight.
  - **Scenario.** A choice of real weight, which a reviewer would raise again, gets no entry.
  - **Fix.** Wording only: such a choice doesn't go there by itself, only as an entry of real weight, as above.
  - **Resolution: done**.
    - **Test:** docs only: the docs tests.
    - **Fix:** such a choice "is proposed as an entry only with that weight", pointing to AGENTS.md, Keep it simple.

- [x] **TST-819 · docs/agent-workflow.md's setup list and DECISIONS.md rows leave out the new rules** · `docs/agent-workflow.md:228` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** The AGENTS.md row of "Setting it up in another repository" lists the paragraphs to keep (tests first,
    the review of one's own work, PLAN.md, REVIEW.md), not the new "Keep it simple", which the retold text at
    lines 109-110 points to; the DECISIONS.md rows (lines 139, 147) don't say an entry needs real weight.
  - **Scenario.** A copy into another repository leaves a pointer to a paragraph it never copied.
  - **Fix.** The KISS paragraph in the row's list; a clause on real weight at the DECISIONS.md row.
  - **Resolution: done**.
    - **Test:** docs only: the docs tests.
    - **Fix:** the AGENTS.md row lists Keep it simple; the DECISIONS.md row says "with real weight".

- [x] **TST-820 · GUIDE's "21 trials" doesn't say they ran on macOS, in a Designer an agent started** · `mcp_server/GUIDE.md:620` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** "The crash above didn't recur in 21 trials (2026-11-23), with the panel left on a graph, a Dot or a
    node of an unloaded package." The trials were the developer's, on macOS, in its own Designer; the self-test runs in
    the user's Designer on Windows.
  - **Scenario.** A reader takes the trials as covering the user's Designer on Windows.
  - **Fix.** Wording only: where the trials ran.
  - **Resolution: done**.
    - **Test:** docs only (wording): the docs tests.
    - **Fix:** "21 trials on macOS, in a Designer an agent started (2026-11-23)".

- [x] **TST-821 · GUIDE's blend fact says a source of the other type "blends as black", where the check measures a transparent black for a grey source** · `mcp_server/GUIDE.md:544` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** "Its `source` blends as black:", then "a grey `source` 0.3 over a colour `destination` ... gave what a
    colour `uniform` (0, 0, 0, 0) gives there". An opaque black colour source in `copy` gives black, not the
    destination, so "as black" holds only for a colour source over a grey destination. ROADMAP item 127's Done note
    repeats it ("blends as black ... So ... gave the `destination`") and drops "in a 32-bit float graph". The
    "red and dotted" sentence (line 551) gives no case: the demo's LUM16 grey into an RGBA8 colour destination, and a
    solid link once the destination was grey.
  - **Scenario.** An agent expects black from a grey noise over a colour background in `copy`, and gets the
    background.
  - **Fix.** Wording only: the source blends as nothing, a grey one as a colour (0, 0, 0, 0), a colour one as a grey 0;
    the Done note the same, with the float graph; the link sentence with its case. Item 126's Approach names the
    core line item 127's note says waits for it.

  - **Resolution: done**.
    - **Test:** docs only (wording): the docs tests, against `check_a_blend_of_a_grey_image_and_a_colour_one`
      (grey_over_colour == clear_over_colour, colour_over_grey == black_over_grey).
    - **Fix:** "Its `source` blends as a zero of that type"; the link sentence names its case (a LUM16 grey into an
      RGBA8 colour destination red and dotted, solid once the destination was grey, seen once, in a demo); item 127's
      Done note the same, "in a 32-bit float graph"; item 126's Approach names the core line item 127 waits for.
    - **Also covered:** "blends as" and "red and dotted" are nowhere else.

- [x] **TST-822 · The unit tests' raising fake is typed as returning None, and the getter fakes as returning object** · `tests/unit/test_describe_selected.py:38` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** `def never() -> None:` always raises; the other raising fakes in `tests/unit` are `NoReturn`
    (`test_lifecycle_env.py:74`). `in_editor`'s `nodes` and `objects` are `Callable[[], object]`, standing in for
    getters the stubs type `Optional[SDArray[...]]`.
  - **Scenario.** None at run time; mypy checks less than is known (`.claude/rules/python.md`, the most specific type).
  - **Fix.** `NoReturn`, and `Callable[[], Sequence[object] | None]`.
  - **Resolution: done**.
    - **Test:** typing only: the file's tests with lint and types.
    - **Fix:** `def never() -> NoReturn`; `nodes` and `objects` typed `Callable[[], Sequence[object] | None]`.

- [x] **TST-823 · The self-review's stopping point, "nothing a reviewer could report", pulls against Keep it simple** · `AGENTS.md:58` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** "Fix what you find and look again, until a fresh look finds nothing a reviewer could report."
    (`address-review:118` the same.) Reviewers report what reading doesn't disprove, very unlikely cases included,
    which Keep it simple, two lines below, says not to address.
  - **Scenario.** A developer covers a very unlikely neighbouring case with complex code because a reviewer could
    report it.
  - **Fix.** "... nothing a reviewer could report that is worth a fix (Keep it simple)", in both places.
  - **Resolution: done**.
    - **Test:** docs only: the docs tests, AGENTS.md at 14,139 of 15,000 bytes.
    - **Fix:** "nothing a reviewer could report that is worth a fix (Keep it simple)" in AGENTS.md and
      `address-review` step 6; no other copy.

- [x] **TST-824 · The blend check's "differs" half passes when the line it compares with is missing** · `tests/test_all_tools/facts/checks.py:101` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** `got['grey_over_colour'] == got['clear_over_colour'] != got['colour_over_colour']`, and line 108's
    `!= got['grey_over_grey']`: `said` returns "no line ..." for a missing label, which differs from any line.
  - **Scenario.** A key renamed in `blend_opacity.py` but not in `blend_cases.by_types`: the checks still pass, no
    longer measuring "Each differed from the blend of a source 0.3 of the destination's type".
  - **Fix.** Require every compared line present (each starting `blend `).
  - **Resolution: done**.
    - **Test:** scratch runs on port 9895, the check alone, with `blend_opacity.py`'s `colour_over_colour` and
      `grey_over_grey` labels renamed for the run: the old check passed (exit 0), the new one failed 48 checks (exit 1);
      restored, 49 passed (exit 0); the same after `/simplify`'s change.
    - **Fix:** both checks begin with `present`, `NO_LINE not in told`; `common.NO_LINE` is the note `said()` builds
      for a missing label.
    - **Also covered:** the only other `said()` result compared with `!=`, the opacity check's `apart`, isn't blind: a
      missing `half` or `zero` fails its own equality.

- [x] **TST-825 · categories.py's comment and run()'s docstring leave out the category's new facts checks** · `tests/test_all_tools/categories.py:55` · confirmed · follows TST-811, generation 2 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** The comment lists "the selection getters' and parentItem's Designer facts", not the Parameters panel's;
    `editor_open_and_zoom/checks.py:26`'s `run()` docstring names none of the three facts checks.
  - **Scenario.** A reader looks there for where the panel facts are measured.
  - **Fix.** Wording only (generation 2): the missing names.
  - **Resolution: done**.
    - **Test:** docs only (wording, generation 2): the docs tests and the self-test's source tests.
    - **Fix:** the comment and `run()`'s docstring name the Designer facts of the Parameters panel, the selection
      getters and `parentItem`.

- [x] **TST-826 · GUIDE says setExplorerSelection "leaves the editor as it is", where the check reads only the editor's graph** · `mcp_server/GUIDE.md:620` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** "`setExplorerSelection` of a graph still loaded turns the panel to it and leaves the editor as it
    is". The check's case reads `editor=mcp_selftest_panel scene=0`, with nothing selected before or after; lines
    614-615 already say "while the editor keeps its graph".
  - **Scenario.** A reader trusts that a selection survives the call; `screenshot_designer('3d', graph=...)` makes it
    (`view3d.py:381`), and `describe_graph(selected=True)` afterwards could say nothing is selected.
  - **Fix.** Wording only: "keeps the graph in the editor", or a pointer to the bullet above.
  - **Resolution: done**.
    - **Test:** docs only (wording): the docs tests.
    - **Fix:** "turns the panel to it and keeps the graph in the editor".

- [x] **AGT-130 · The ROADMAP rule leaves out the user's bar on what gets proposed at all** · `.claude/skills/delegate/SKILL.md:64` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** The rule's exits are two: done in the branch, or proposed for a valid reason. The user: "Only bring
    the idea to me if it actually makes much sense"; no line carries it.
  - **Scenario.** An idea of little worth, too far from the branch, reaches the user at convergence.
  - **Fix.** One sentence with the quote: such an idea is proposed only if it makes much sense; one that doesn't is
    neither done nor proposed (AGENTS.md, Keep it simple).
  - **Resolution: done**.
    - **Test:** docs only: the docs tests.
    - **Fix:** "Such an idea is proposed only if it makes much sense (the user, 2026-11-23: "Only bring the idea to me if
      it actually makes much sense"). An idea that doesn't is neither done nor proposed (AGENTS.md, Keep it simple)."

- [x] **AGT-131 · A case named not worth a fix isn't passed to the next round's reviewers, who raise it again** · `.claude/skills/project-code-review/SKILL.md:161` · confirmed · follows AGT-126, generation 2 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** Step 3's brief passes "the review log's notes on what was found fine", and `reviewer.md:36` reads the
    same; AGT-126's not-worth-a-fix names are neither (settled-as-wrong ones neither, before the branch).
  - **Scenario.** The Opus round raises again what a Sonnet round named not worth a fix; this round's briefs had to
    add it by hand.
  - **Fix.** Both say "found fine, settled as wrong or named not worth a fix" (`reviewer.md` reaches reviewers started
    after the user's next message).
  - **Resolution: done**.
    - **Test:** docs only: the docs tests.
    - **Fix:** `project-code-review` step 3 and `reviewer.md`'s Before reviewing pass what earlier reviews "found fine,
      settled as wrong or named not worth a fix" (`reviewer.md` reaches reviewers started after the user's next
      message).

- [x] **AGT-132 · address-review's lead line still sends every decision of the user's to DECISIONS.md** · `.claude/skills/address-review/SKILL.md:173` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** "**What the user decides goes in, if a reviewer could raise it again:** ... won't fix, a rule to
    follow from now on, one option out of several, how something should work", ahead of the new "An entry is
    proposed only when it has real weight"; `.claude/rules/docs.md:32`'s row sends "the user's won't fix, rule or
    choice" there with no weight, where `docs/agent-workflow.md:148` now says "with real weight".
  - **Scenario.** The lead reads the bold lead first and proposes an entry for a minor choice.
  - **Fix.** The lead line says "with real weight (below)", and docs.md's row too.

  - **Resolution: done**.
    - **Test:** docs only: the docs tests.
    - **Fix:** the lead line "What the user decides goes in, if a reviewer could raise it again, with real weight
      (below)"; docs.md's DECISIONS.md row "with real weight".
