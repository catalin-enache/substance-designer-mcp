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

**Last used:** PLG-45, SRV-251, HLP-255, INS-47, TST-841, AGT-132.

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
| Low | 0 | 8 |
| **Total** | **0** | **8** |

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
| 2026-11-24, node-stats-against step 1 | Opus (developer) | 1 | 0 | 0 | 266,977 | 22 min |
| 2026-11-24, step 1's choice 10 (grey with alpha refused) | Opus (developer) | 1 | 0 | 0 | 7,133 | 3 min |
| 2026-11-24, round 1 (step 1) | Sonnet | 2 | 3 [3 Low] | 3 [3 Low] | 271,351 | 7 min |
| 2026-11-24, round 1's fixes | Opus (developer) | 1 | 0 | 0 | 27,546 | 4 min |
| 2026-11-24, round 2 (the entire branch) | Opus | 2 | 4 [4 Low] | 4 [4 Low] | 267,290 | 8 min |
| 2026-11-24, round 2's fixes | Opus (developer) | 1 | 0 | 0 | 36,790 | 11 min |
| 2026-11-24, `against` naming `node_id` itself (the user's decision) | Opus (developer) | 1 | 0 | 0 | 22,847 | 5 min |
| 2026-11-24, round 3 (round 2's fixes and `against` naming `node_id`) | Opus | 1 | 1 [1 Low] | 1 [1 Low] | 170,240 | 8 min |
| 2026-11-24, round 3's fix | Opus (developer) | 1 | 0 | 0 | 4,337 | 1 min |
| **Total** | | **11** | **8 [8 Low]** | **8 [8 Low]** | **1,074,511** | **69 min** |

## Review log

### 2026-11-24: node-stats-against, round 1 (step 1 of PLAN.md, ROADMAP item 50)

- **Scope:** `git diff 87846c1 dba5c0d -- . ':(exclude)PLAN.md'`: `node_stats(against=..., against_output=...,
  tolerance=...)`, its unit tests, its live checks (category `measure`) and its docs.
- **How:** two Sonnet reviewers: one on `mcp_server/server_tools` and `tests/unit`, one on `tests/test_all_tools`,
  README.md, ROADMAP.md and GUIDE.md. No tests run, no probes: every suspicion was settled by reading. Settled as wrong
  or not worth a fix:
  - the refusal message's "an rgba_split node" naming no node that exists: Designer's library has `rgba_split.sbs`
    (`Contents/Resources/packages/`, beside the `noise_clouds_2.sbs` the tests use);
  - grey with alpha against colour refused, beyond the approved "refused when they share none": the lead's choice,
    made after step 1's `/simplify` and told to the user, since comparing A alone would read as a match;
  - `tolerance` reaching `_diff_lines` unguarded by a unit test: the live check with `tolerance` 0.3 (0 px over) fails
    if it doesn't;
  - RGBA against a 3-channel RGB through the tool, and one bridge call only without `against`, untested: not worth a
    fix (the pure function covers the channel matching, and the output without `against` is pinned unchanged);
  - the live `against_output` call not showing the output reaches the second node: it only repeats the unit tests'
    guard (`_pixels_bridge` routes by the output the dump call names; DECISIONS.md, Low-value findings about the
    tests and docs are not raised).
- **Not verified:** none.
- **Resolutions assessed:** none in scope.
- **Findings:** TST-837, TST-838, TST-839: 3 Low.
- **Suggested order:** any; all three are small.
- **Checked and found fine:** the diff maths against the approved text (regions and their `x0, y0`, ties in row order,
  strictly over the tolerance, channels by name); the output without `against` byte for byte as before, and the
  parsers of other categories (`stats_max`, `pixel_values`, the format on line 1) untouched; the fake bridge's
  `PIXELS=` metadata and note as the helper prints them; the negative-tolerance refusal before Designer; each live
  check failing without its code, the four uniforms deleted in `finally`, the check's place in `run`; `measure/parsing.py`'s
  regex against the server's format string; README, GUIDE.md's Measure bullet and ROADMAP item 50 against the code;
  GUIDE.md's reload check rightly unchanged (`against` compares nodes of one graph).

### 2026-11-24: node-stats-against, round 2 (the entire branch against main)

- **Scope:** `git diff main...node-stats-against -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'` at 55a0f14.
- **How:** two Opus reviewers: one on `mcp_server/server_tools` and `tests/unit` (with the helpers the diff calls),
  one on `tests/test_all_tools`, README.md, ROADMAP.md and GUIDE.md. No tests run, no probes: every suspicion was
  settled by reading. Not worth a fix: twice the peak memory with `against` (two float64 images), which only very
  large outputs come near. A note, not an entry: TST-839's Also covered said more than holds (under TST-839).
- **Not verified:** none.
- **Resolutions assessed:** TST-837, TST-838 and TST-839 hold (TST-839's record corrected by a note).
- **Findings:** HLP-255, SRV-250, TST-840, TST-841: 4 Low. The longest chain still growing: TST-839's note,
  generation 2.
- **Unspecified:** `against` may name `node_id` itself, comparing two outputs of one node (the live check does), while
  its description says "Another node of the same graph": the user's call, in PLAN.md's Waiting for the user.
- **Checked and found fine:** clean-up when the second read or a refusal fails after the first read (each
  `_node_pixels` removes its folder, the helper its temporary output node; only the first read's undo step stays, as
  the docstring says); a region checked before the second compute; channel indices equal once the layouts are; the
  `_crop` to `_crop_box` change equivalent; each unit and live check failing on the plausible wrong code; the parsing
  helpers against the real text (the SDK's `Error executing tool node_stats: ` prefix included); the docs against the
  code.

### 2026-11-24: node-stats-against, round 3 (round 2's fixes, and `against` naming `node_id` itself)

- **Scope:** `git diff 55a0f14 28f4f09 -- . ':(exclude)PLAN.md'`: round 2's fixes, and the user's decision that
  `against` may name `node_id` itself to compare two of its outputs (description, docs, a unit test and an
  `rgba_split` live check).
- **How:** one Opus reviewer on the whole diff. No tests run, no probes: settled by reading. Not reported again: the
  new `rgba_split` check's detail cut before its pixel count, the same cut TST-839's note judged not worth a fix.
  Settled by the user's words: "if they are of the same type" is what the size and grey-or-colour refusals give
  (two colour outputs of different meanings still compare, as two nodes' do).
- **Not verified:** none.
- **Resolutions assessed:** HLP-255, SRV-250, TST-840 and TST-841 hold.
- **Findings:** SRV-251: 1 Low.
- **Checked and found fine:** the `rgba_split` check failing on each plausible wrong code (the second read with
  `output` or the default, the outputs swapped, one read reused) and cleaning up in `finally`; the fake bridge's
  lookup by node and output letting no wrong server pass; HLP-255's message reaching `preview_node`, `node_stats`,
  `check_tiling`, `compare_to_reference` and `sweep_param` unchanged; measure's 88 s in the slowest-first order; the
  docs, descriptions and GUIDE's core (7,973 characters) against the code.

---

## High

## Medium-high

## Medium

## Low-medium

## Low

- [x] **TST-837 · A test case's comment cites PLAN.md and reads as the opposite of what it checks** · `tests/unit/test_default_output.py:274` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** The `grey with alpha against colour` case carries `# they share A alone, which was compared (PLAN.md
    choice 10)`. "Which was compared" reads as what the case expects, though it asserts a refusal, and PLAN.md is
    deleted in the branch's last commit, so the pointer dangles after the merge.
  - **Scenario.** A maintainer reading the case takes it that LA against RGBA compares A, then looks for a PLAN.md
    that isn't there.
  - **Fix.** State the fact without the pointer, such as `# shares A with RGBA, still refused: one is grey, the other
    colour`.
  - **Resolution: done**.
    - **Test:** none: a comment only.
    - **Cause:** the comment told the case's history, not what it checks, and pointed at the branch's plan.
    - **Fix:** the case's comment reads `# shares A with RGBA, still refused: one is grey, the other colour`.
    - **Also covered:** `PLAN.md` searched in the server, the helpers, the tests, the client, the plugin and
      `scripts/`: no other pointer from code to the branch's plan (`docs_text.py` and `test_guide.py` name it as a
      file of the workflow).

- [x] **TST-838 · No test sees `against` read from another graph than `node_id`** · `tests/unit/test_default_output.py:172-175`, `mcp_server/server_tools/measure.py:228` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `_dumped` drops the dump call's graph (`node, _, _, output = ast.literal_eval(...)`), so no unit test
    fails if the second `_node_pixels(against, graph, against_output, 'node_stats')` loses its `graph`. The live
    check can't see it either: the measure category opens its graph in the UI (`measure/checks.py:50`), and
    `find_graph(None)` defaults to the graph shown in the UI (`designer_helpers/core.py:117-127`).
  - **Scenario.** A refactor passes `None` for the second node's graph. Every test passes, and a user comparing nodes
    of a graph that isn't the one shown gets "node X not found" for `against`, or another graph's node.
  - **Fix.** Have `_dumped` return the graph too, and assert in an `against` test that both dump calls name the graph
    passed.
  - **Resolution: done** (a missing guard, not a live bug).
    - **Test:** `test_node_stats_against_reads_both_nodes_in_the_graph_given` asserts the dump calls
      `[('1', 'g', 'o1'), ('2', 'g', 'o2')]`. It failed with the second `_node_pixels` given `None` for its graph
      (`('2', None, 'o2') != ('2', 'g', 'o2')`), and passes with the code restored.
    - **Cause:** the fake bridge's `_dumped` dropped the graph, and the helpers default to the graph shown in the UI.
    - **Fix:** `_dumped` returns `(node, graph, output)`, and `_pixels_bridge` returns the calls it got, in order.
    - **Also covered:** the other callers of `_node_pixels` (`compare_to_reference`, `check_tiling`, node_stats' first
      call) read one node each with the tool's own `graph`, passed straight through.

- [x] **TST-839 · A failing `against` live check shows neither the diff lines nor the whole refusal** · `tests/test_all_tools/measure/checks.py:311-348` · confirmed · found 2026-11-24 by a reviewer (Sonnet)
  - **Defect.** `common.check` prints `detail.strip()[:150]` (`common.py:74`). The first three `against` checks pass
    the whole result `t`, whose header and four stats lines fill the 150 characters, so a FAIL shows no `against` or
    `diff:` line. The two refusal checks pass `text(r_)`, about 165 characters, so the second size or format can be cut
    off too.
  - **Scenario.** The check fails in a full run, and its line shows only the stats: whoever reads the log must run it
    again to learn what the comparison returned.
  - **Fix.** Pass the part each check parses: the lines from `against ` on, and the refusal's end (for example
    `text(r_)[-150:]`).
  - **Resolution: done**.
    - **Test:** a scratch run of `check_node_stats_against` with all five checks made to fail: before the fix, the FAIL
      lines showed the header and stats only, and the size refusal lost its second size; after it, they show the
      `against` and R `diff:` lines, the whole size refusal and both formats. Restored, the run exits 0 (6 checks).
    - **Cause:** the checks passed the whole result, or the refusal with the client's `Error executing tool
      node_stats: ` prefix, to a detail `common.check` cuts at 150 characters.
    - **Fix:** `measure/parsing.py`'s `compared(t)` (the result from its `against` line on) and `refusal(t)` (the
      error without the prefix) give the five checks' details.
    - **Also covered:** the other node_stats checks of `measure/checks.py` already pass the line they parse. A failure
      in B or A of the "against itself" check is still cut, which a detail per channel would fix: not worth it.
  - Note (2026-11-24, round 2, generation 2): the Also covered says more than holds. The `stats + region + point`
    check, older than this branch, passes only the header as its detail though it checks three other lines, and the
    cut reaches G too in the "against itself" check, and G, B and A in the "R 0.2 higher" one. Not worth a fix, as
    above.

- [x] **HLP-255 · With `against`, "output not found" doesn't say which node lacks the output** · `mcp_server/designer_helpers/describe.py:381-384` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `_with_node_texture` raises `'output %r not found; outputs: %s'` without the node, and
    `node_stats` reads two nodes now. The "node not found" and "produced no texture" errors name theirs.
  - **Scenario.** `node_stats('1', output='height', against='2', against_output='height')`, where node 2 has no
    `height`: the agent gets `output 'height' not found; outputs: [...]` and may take it for node 1's.
  - **Fix.** Name the node in the message, such as `output 'height' not found on node 2; outputs: [...]`.
  - **Resolution: done**.
    - **Test:** `test_an_output_the_node_lacks_is_refused_naming_the_node` (`tests/unit/test_default_output.py`)
      failed on the old message and passes. The live check "against an output its node lacks: refused, naming that
      node" (`check_node_stats_against`, `against_output: 'nope'`) failed in a scratch run with `output 'nope' not
      found; outputs: ['unique_filter_output']`, and passes in two scratch runs of the whole measure category.
    - **Cause:** the message named the output and the node's outputs, not the node, unambiguous only while a call read
      one node.
    - **Fix:** `_with_node_texture` raises `'output %r not on node %s; outputs: %s'` with the node's identifier, the
      connect op's wording (`edits.py:508`).
    - **Also covered:** the fix reaches every caller of `_with_node_texture`: `preview_node`, `dump_node_pixels`
      (`node_stats`, `check_tiling`, `compare_to_reference`) and `sweep_param`'s view node. The other errors on these
      paths already name their node ("produced no texture", "not found in graph", "is not a parameter of").

- [x] **SRV-250 · `points`' description doesn't say whose pixels it samples, now printed after the `against` lines** · `mcp_server/server_tools/measure.py:182` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `points` reads `'[[x, y], ...] pixel values to sample.'`, and its `pixel (x,y)` lines follow the
    `against` section. They are `node_id`'s values only (the approved choice 5), which neither the description nor
    the docstring says.
  - **Scenario.** An agent passes `points` with `against` to see the second node's values, and reads the first
    node's.
  - **Fix.** A few words in the description, such as "pixel values of node_id's output to sample".
  - **Resolution: done**.
    - **Test:** `test_node_stats_against_comes_after_the_channel_lines_and_before_the_points` samples (1,0), where the
      two nodes differ, and expects node 1's value. It failed with the code changed to sample the `against` node
      (`R=0.2000` for `R=0.0000`), and passes with it restored.
    - **Cause:** the description didn't say whose values `points` reads.
    - **Fix:** `points` reads "[[x, y], ...] pixel values of node_id's output to sample."
    - **Also covered:** `region`'s description said "to restrict the stats" only, and now adds "and the comparison
      with against", as the docstring and a unit test already had it.

- [x] **TST-840 · `_dumped` passes on `ast.literal_eval`'s implicit `Any`** · `tests/unit/test_default_output.py:175` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `node, _, graph, output = ast.literal_eval(...)` is typed only by the function's return annotation,
    against `.claude/rules/python.md` (Typing: an implicit `Any`, such as `json.loads`'s result).
  - **Scenario.** No defect hides behind it today: a changed call shape fails at the unpacking. A later edit typed
    by the `Any` would pass mypy unchecked.
  - **Fix.** `cast(tuple[str, str, str | None, str | None], ast.literal_eval(...))`, as `tests/unit/test_server.py`
    does.
  - **Resolution: done**.
    - **Test:** none can fail on it: mypy doesn't report an implicit `Any`. Settled by reading.
    - **Fix:** `_dumped` casts `ast.literal_eval(...)` to `tuple[str, str, str | None, str | None]`.
    - **Also covered:** no other `literal_eval` in the branch's diff.

- [x] **TST-841 · The measure category's recorded time predates its new checks** · `tests/test_all_tools/categories.py:62` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** `measure.run,  # 9 s: ...` stands in a list kept slowest first by measured times (`categories.py:33`).
    The branch adds five `node_stats` calls of two reads each, about ten `graph.compute()` of about 0.9 s (GUIDE.md,
    the compute's cost), so the category likely takes 15 s or more, above `inputs` (15 s).
  - **Scenario.** The pool starts measure later than its time warrants, and its end is less balanced. No result is
    wrong.
  - **Fix.** Measure the category's time as the list's other figures were, and update its figure and place.
  - **Resolution: done**.
    - **Test:** two scratch runs of the whole measure category, with their server's start: 88.2 s and 87.6 s. A third,
      timed line by line (91.3 s), put `check_node_stats_against` at about 4.5 s: the 9 s on record was out of date
      before this branch, from checks added since 2026-11-10.
    - **Fix:** `categories.py` records `# 88 s (2026-11-24, two scratch runs, with their server's start: 88.2 s,
      87.6 s)`, and measure moved to third, after `functions` (136 s) and before `facts` (50 s).
    - **Also covered:** no other doc holds measure's figure. Other undated figures in the list may be as stale;
      measuring them is outside this finding.

- [x] **SRV-251 · The docstring counts one undo step per node, but a node compared with itself takes two** · `mcp_server/server_tools/measure.py:218` · confirmed · found 2026-11-24 by a reviewer (Opus)
  - **Defect.** The docstring ends "one undo step per node measured", written when `against` meant another node.
    `node_stats` reads `node_id` (line 219) and `against` (line 234) through two `_node_pixels` calls, each in its
    own undo group, so `against` naming `node_id` itself, now documented, takes two steps for one node.
  - **Scenario.** `node_stats(split, output='R', against=split, against_output='G')` on a node feeding no output
    leaves two "Claude: node stats" entries in Designer's history where the docstring promises one.
  - **Fix.** "One undo step per output read". The line before it (215, 146 characters) is unwrapped since the last
    edit: wrap it in the same change.
  - **Resolution: done**.
    - **Test:** none can fail on a docstring: settled by reading. Each read is one `_node_pixels` call in its own undo
      group, so a call with `against` takes two steps, whether it names another node or `node_id` itself.
    - **Fix:** node_stats' docstring ends "one undo step per output read", its lines rewrapped within 120 characters.
    - **Also covered:** no other docstring or doc of the repository counts undo steps per node; `check_tiling` and
      `compare_to_reference` read one output each and still say "within one undo step".
