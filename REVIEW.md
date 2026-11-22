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

**Last used:** PLG-45, SRV-220, HLP-249, INS-46, TST-760, AGT-125.

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
| Medium | 0 | 1 |
| Low-medium | 0 | 8 |
| Low | 0 | 117 |
| **Total** | **0** | **126** |

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
| 2026-11-21, Step 1 (function graph facts) | Opus (developer) | 1 | 0 | 0 | 398,252 | 30 min |
| 2026-11-21, Step 1's review | Sonnet | 2 | 5 [5 Low] | 5 [5 Low] | 322,116 | 8 min |
| 2026-11-21, Step 1's review's fixes | Opus (developer) | 1 | 0 | 0 | 90,345 | 10 min |
| 2026-11-21, Step 2 (the compiler) | Opus (developer) | 1 | 0 | 0 | 412,973 | 37 min |
| 2026-11-21, Step 2's safety test fix | Opus (developer) | 1 | 0 | 0 | 3,747 | 1 min |
| 2026-11-21, Step 2's review | Sonnet | 2 | 7 [1 Low-medium, 6 Low] | 7 [1 Low-medium, 6 Low] | 386,346 | 11 min |
| 2026-11-21, Step 2's review's fixes | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 177,452 | 25 min |
| 2026-11-21, Step 2's fixes' review | Sonnet | 2 | 7 [7 Low] | 7 [7 Low] | 395,210 | 12 min |
| 2026-11-21, the last of Step 2's fixes | Opus (developer) | 1 | 0 | 0 | 66,653 | 11 min |
| 2026-11-21, Step 3 (`set_function`) | Opus (developer) | 1 | 0 | 0 | 474,010 | 38 min |
| 2026-11-21, Step 3's review | Sonnet | 3 | 17 [2 Low-medium, 15 Low] | 17 [2 Low-medium, 15 Low] | 588,752 | 10 min |
| 2026-11-21, Step 3's review | settling | 2 | 0 | 0 | 245,583 | 6 min |
| 2026-11-21, Step 3's review's fixes | Opus (developer) | 1 | 0 | 0 | 174,432 | 34 min |
| 2026-11-22, Step 3's fixes' review | Sonnet | 2 | 7 [7 Low] | 7 [7 Low] | 479,212 | 11 min |
| 2026-11-22, the last of Step 3's fixes | Opus (developer) | 1 | 0 | 0 | 58,475 | 12 min |
| 2026-11-22, Step 3b (value connections) | Opus (developer) | 1 | 0 | 0 | 417,343 | 30 min |
| 2026-11-22, Step 3b's review | Sonnet | 2 | 7 [1 Medium, 1 Low-medium, 5 Low] | 7 [1 Medium, 1 Low-medium, 5 Low] | 387,316 | 10 min |
| 2026-11-22, Step 3b's review's fixes | Opus (developer) | 1 | 0 | 0 | 118,176 | 19 min |
| 2026-11-22, Step 3b's undo unit test fix | Opus (developer) | 1 | 0 | 0 | 22,762 | 2 min |
| 2026-11-22, Step 3b's fixes' review | Sonnet | 2 | 5 [5 Low] | 5 [5 Low] | 349,176 | 10 min |
| 2026-11-22, the last of Step 3b's fixes | Opus (developer) | 1 | 0 | 0 | 58,512 | 11 min |
| 2026-11-22, Step 4 (function graphs of the package) | Opus (developer) | 1 | 0 | 0 | 545,996 | 42 min |
| 2026-11-22, Step 4's review | Sonnet | 3 | 12 [2 Low-medium, 10 Low] | 12 [2 Low-medium, 10 Low] | 555,863 | 10 min |
| 2026-11-22, Step 4's review's fixes | Opus (developer) | 1 | 0 | 0 | 185,355 | 25 min |
| 2026-11-22, Step 4's fixes' review | Sonnet | 2 | 6 [6 Low] | 6 [6 Low] | 422,751 | 10 min |
| 2026-11-22, the last of Step 4's fixes | Opus (developer) | 1 | 0 | 0 | 87,044 | 14 min |
| 2026-11-22, Step 5 (sampling, extra inputs) | Opus (developer) | 1 | 0 | 0 | 542,648 | 46 min |
| 2026-11-22, Step 5's review | Sonnet | 3 | 6 [1 Low-medium, 5 Low] | 6 [1 Low-medium, 5 Low] | 542,534 | 10 min |
| 2026-11-22, Step 5's review's fixes | Opus (developer) | 1 | 0 | 0 | 154,056 | 25 min |
| 2026-11-22, Step 5's fixes' review | Sonnet | 2 | 5 [5 Low] | 5 [5 Low] | 346,013 | 7 min |
| 2026-11-22, the last of Step 5's fixes | Opus (developer) | 1 | 0 | 0 | 85,210 | 17 min |
| 2026-11-22, Step 6 (reading function graphs) | Opus (developer) | 1 | 0 | 0 | 623,644 | 45 min |
| 2026-11-22, Step 6's review | Sonnet | 3 | 11 [11 Low] | 11 [11 Low] | 573,081 | 10 min |
| 2026-11-22, Step 6's review's fixes | Opus (developer) | 1 | 0 | 0 | 129,338 | 24 min |
| 2026-11-22, Step 6's fixes' review | Sonnet | 2 | 4 [4 Low] | 4 [4 Low] | 370,811 | 9 min |
| 2026-11-22, the last of Step 6's fixes | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 40,583 | 7 min |
| 2026-11-22, the first Opus round on the whole branch | Opus | 4 | 12 [1 Low-medium, 11 Low] | 12 [1 Low-medium, 11 Low] | 1,225,127 | 18 min |
| 2026-11-22, the first Opus round's fixes | Opus (developer) | 1 | 0 | 0 | 473,878 | 48 min |
| 2026-11-22, the first Opus round's fixes' review | Opus | 3 | 2 [2 Low] | 2 [2 Low] | 471,559 | 13 min |
| 2026-11-22, SRV-213, SRV-214 and the test lesson | Opus (developer) | 1 | 0 | 0 | 76,131 | 17 min |
| 2026-11-22, SRV-214's `$pos` narrowed | Opus (developer) | 1 | 0 | 0 | 9,319 | 20 min |
| 2026-11-22, the materials-from-a-photo table | Opus (developer) | 1 | 0 | 0 | 30,845 | 9 min |
| 2026-11-22, the second Opus round on the whole branch | Opus | 4 | 6 [6 Low] | 6 [6 Low] | 1,221,562 | 16 min |
| 2026-11-22, the second Opus round's fixes | Opus (developer) | 1 | 0 | 0 | 92,390 | 19 min |
| 2026-11-22, the user's answers at convergence | Opus (developer) | 1 | 0 | 0 | 71,975 | 19 min |
| 2026-11-22, the convergence answers' review | Sonnet | 2 | 5 [5 Low] | 5 [5 Low] | 316,946 | 7 min |
| 2026-11-22, the convergence answers' fixes | Opus (developer) | 1 | 0 | 0 | 39,616 | 8 min |
| 2026-11-22, ROADMAP item 125 | Opus (developer) | 1 | 0 | 0 | 2,595 | 1 min |
| **Total** | | **75** | **126 [1 Medium, 8 Low-medium, 117 Low]** | **126 [1 Medium, 8 Low-medium, 117 Low]** | **14,863,713** | **834 min** |

## Review log

### 2026-11-21: Step 1 of ROADMAP item 9 (the `functions` category's designer facts)

- **Scope:** `git diff 516548c c8de09b -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers. One took `functions/checks.py`, `definitions.py`, the category's wiring, README and
  ROADMAP items 116 and 117. The other took `function_nodes.py` and GUIDE.md's new bullet (lines 263-301). No tests
  were run and no probe was needed: the lead settled every suspicion by reading the lines it quotes. Settled as wrong:
  - only 79 of the 85 definitions are pinned: Step 2 replaces `INPUTS` with the compiler's own table, which a check
    compares with `getDefinitions()` whole;
  - four of `vector4`'s nine type pairs are never connected: every pair whose sizes add up was run (two for
    `vector3`, three for `vector4`), and so were sizes too few and too many. The compiler builds only exact sums;
  - vacuous passes when the script prints nothing: the count check fails then. A missing failure detail is only a
    debugging aid;
  - every replacement is made on a node never computed: what was measured holds. Whether a function replaced after a
    compute computes again is the tool's case, and Step 3's live checks replace one after a first compute;
  - RelativeToParent with an offset not measured: that offset is from the graph too, so "Only Absolute gives it a
    size of its own" holds;
  - a package made before the `try`, and helpers like `facts`' own: the existing scripts do the same, `common.CLEAN`
    unloads a package named `mcp_selftest...`, and Designer scripts can't import each other.
- **Not verified:** none.
- **Resolutions assessed:** none (no earlier entries on this branch).
- **Findings:** TST-695 to TST-699, 5 Low. TST-695 and TST-698 merge both reviewers' reports.
- **Suggested order:** TST-695 first, as its outcome decides which result types Step 3 accepts. Then TST-696,
  TST-697, TST-698 and TST-699.
- **Checked and found fine:**
  - every label the checks expect matches a line the scripts print, and a missing line fails;
  - the replacement and size checks read back non-default values (`$randomseed` 7, an Absolute 3,3, sizes of 8, 16,
    64 and 128 px);
  - each script unloads its package once, in a `finally`;
  - the category uses no other category's code, sits in `CATEGORIES` by its time and has its README row;
  - ROADMAP items 116 and 117 claim nothing untrue about the code.

### 2026-11-21: Step 2 of ROADMAP item 9 (the expression compiler)

- **Scope:** `git diff 27f995c ac640b7 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers. One read `mcp_server/function_compiler.py` in full and traced its nodes against the
  table by hand. The other took the unit tests, the `functions` category's changes, `sys.path`, `ruff.toml` and
  GUIDE.md's new lines. No tests were run and no probe was needed: the lead settled every suspicion by reading the
  lines it quotes. Settled as wrong:
  - a ColorRGBA graph input refused while `expose` reads one with `get_float4`: the compiler takes function types, and
    Step 3's read call gives each input's function type through `expose`'s own getters (`_GETTERS`), so the compiler
    never sees a ColorRGBA;
  - the table comparison has no unit test and was never seen failing: the developer's scratch mutation run (`add`
    changed, `pow2` removed) failed it, naming both, and the real table passed it;
  - the 85 transcribed definitions can't be confirmed by reading: `check_the_function_definitions` passed on them in
    the developer's scratch run;
  - a name bound to a literal builds a constant at each use: on purpose, said in the module docstring and pinned by
    the tests;
  - `OverflowError` on a huge int, `RecursionError` on deep nesting, a `$5` inside a comment refused: inputs no agent
    writes.
- **Not verified:** none.
- **Resolutions assessed:** TST-699 holds (`parsing.py` still checks the shape, and its unit test still feeds the five
  wrong shapes).
- **Findings:** TST-700 (Low-medium), TST-701 to TST-704, SRV-187 and SRV-188 (Low). TST-700, TST-704 and SRV-187
  merge both reviewers' reports.
- **Suggested order:** TST-700 first: its measurements may change what the compiler builds, and SRV-187 rests on
  `mul`'s. Then SRV-187, SRV-188, TST-704, TST-701, TST-702 and TST-703.
- **Unspecified** (for the user): `$time`, `$depth` and `$number` are floats from Adobe's page alone, unmeasured, and
  `$depth` and `$number` are an FX-Map's, yet they compile in any function.
- **Checked and found fine:**
  - the broadcast, `mulscalar` in both orders, `atan2(y, x)`, `clamp`, `length`, `normalize`, the casts, `ifelse`,
    literals, comparisons, vectors and swizzles all build types the table lists, and vectors add up exactly (traced by
    hand);
  - no node is left unused, and the output node is the last;
  - columns hold after `$` is rewritten;
  - the unit tests' expectations are hand-written trees and full messages, not the compiler's own output;
  - `check_atan2` and `check_system_variables` fail on a swap, a wrong unit or a wrong type, and run inside the
    script's `finally`.

### 2026-11-21: Step 2's fixes (TST-700 to TST-704, SRV-187, SRV-188, and `$depth` and `$number` refused)

- **Scope:** `git diff 21b8b06 d08d410 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers. One took the compiler and its unit tests. The other took the `functions` category,
  `common.py`, `render/checks.py`, `test_selftest_check_setups.py` and GUIDE.md. No tests were run and no probe was
  needed: the lead settled every suspicion by reading the lines it quotes. Both reviewers counted the shipped
  `$depth` and `$number` reads again. The reviewer who scanned `packages/` and `internal/` only found 297 `$number`,
  where the whole bundle has 299. Every one sits in an FX-Map graph. TST-705 is rated Low, where its reviewer said
  Low-medium. Designer's maths nodes are its standard ones: `atan2` and `cartesian` were measured in radians. And
  Step 3's live checks compute the step's own example end to end (`sub` of a float2, `dot`, `max` and `sqrt`).
- **Not verified:** none.
- **Resolutions assessed:** SRV-187, SRV-188, TST-701, TST-702, TST-703 and TST-699 hold. TST-700 holds for what it
  lists, and TST-705 to TST-708 follow it (generation 2). TST-704 holds, and TST-710 follows it (generation 2).
  SRV-190 follows SRV-188 (generation 2). Notes were added under TST-700 (the cell count) and TST-701 (branches with
  no unit case).
- **Findings:** TST-705 to TST-710 and SRV-190, 7 Low. The longest chain still growing is TST-700's, at generation 2.
- **Suggested order:** TST-705, TST-706 and TST-707, which add cells in one scratch run. Then TST-708, TST-710,
  SRV-190, SRV-189 and TST-709.
- **Unspecified** (for the user, with the convergence report):
  - `/` of two ints truncates in Designer (7 by 2 gives 3) where Python's `/` gives 3.5. The compiler builds it
    silently;
  - shipped packages read variables the grammar doesn't list: `$normalformat`, `$pixelratio` and `$physicalsize`.
    `$depthpow2` is an FX-Map's;
  - the six negative-int cells hold macOS values, with no platform branch.
- **Checked and found fine:**
  - `mulscalar` is built for every float-vector `*`, traced in nine forms;
  - the hints no longer grow a value into a vector;
  - the columns hold after `dedent`;
  - every negative int the compiler can see is refused, `0 - i` being the documented run-time case;
  - the 42 labels match their expected keys, and the 8-bit rounding is robust;
  - every module of the self-test imports `__init__.py` before using the path.

### 2026-11-21: Step 3 of ROADMAP item 9 (the `set_function` tool)

- **Scope:** `git diff 74a7efc 382d071 -- . ':(exclude)PLAN.md'`.
- **How:** three Sonnet reviewers: the server side, the Designer helper, the live checks. No tests were run. To
  settle:
  - an analyst read Designer's shipped packages for how a Value Processor's value reaches a parameter;
  - a runner probed on its own Designer (port 9895): a function on `$format` and on `$outputsize` through
    `set_function`, and whether the API can wire a Value Processor into a node's input value.

  The runner found, and the lead read its code:
  - `$format`'s function is ignored at the default inheritance (RelativeToInput) and works at Absolute;
  - `$outputsize`'s `int2(5, 5)` gives 2048 px at the default (an offset) and 32 px at Absolute, and `int2(15, 15)`
    computes 8192 px, refused by nothing;
  - `newProperty('#x', SDTypeFloat, Input)` on a blend makes a connectable input value. A name without `#` gets one
    added. The Value Processor connects into it, and a `get_float1` of `#x` on `opacitymult` reads its 0.25, then its
    0.75.

  Settled as wrong or dropped:
  - `1e999`, as in Step 2: no agent writes it;
  - whether a Value Processor has a `perpixel` or a Pixel Processor a `function`: no source suggests either;
  - the library refusal living in `safeguards`, not `functions`: the project's pattern for library rows;
  - `results.built`'s plural wording: right for every expression it reads.
- **Not verified:** none.
- **Resolutions assessed:** none in this diff.
- **Findings:** HLP-225 and TST-719 (Low-medium), and 15 Low: HLP-226 to HLP-230, SRV-191, SRV-192 and TST-711 to
  TST-718. TST-719 waits on the user: whether value connections join this branch.
- **Suggested order:** HLP-225, then the helper's HLP-226 to HLP-230, the server's SRV-191 and SRV-192, the docs'
  TST-711, then the checks TST-712 to TST-718. TST-719 after the user's answer.
- **Unspecified** (for the user): whether `set_function`'s result should name a graph input that its replacement
  leaves driving nothing.
- **Checked and found fine:**
  - the result types against each target;
  - each graph input's type reaching the compiler;
  - the call strings' escaping, `inf` aside;
  - the one undo group;
  - the library refusal at the read;
  - the rollback for each kind of target;
  - the moved shared pieces, which change nothing for `expose`, `set` or the processors;
  - the replace-after-compute check reading new pixels;
  - each refusal's expected text;
  - the category's independence.

### 2026-11-22: Step 3's fixes (HLP-225 to HLP-230, SRV-191, SRV-192, TST-711 to TST-718)

- **Scope:** `git diff fb466b2 c173aa8 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the code, and the checks with the docs. No tests were run and no probe was needed:
  the lead settled every suspicion by reading the lines it quotes. Settled as wrong or dropped:
  - `_made_absolute` failing silently: the inheritance call raised in no case ever measured (HLP-207), and `set`
    swallows it the same way;
  - Redo shown only as "a function": a partial Redo of one undo group isn't realistic;
  - the checks' order inside `functions.run` and the bases of `CATEGORIES`' times: no wrong result either way;
  - `sweep.py` making `$randomseed` Absolute while it sweeps: outside the diff, and put back after.
- **Not verified:** none.
- **Resolutions assessed:** HLP-226, HLP-227, HLP-229, SRV-191, SRV-192 and TST-711 to TST-718 hold. HLP-225,
  HLP-228, HLP-230 and TST-716 hold for what they list, with follow-ups at generation 2: SRV-194 and TST-723,
  TST-721, HLP-231 and TST-720, and TST-722.
- **Findings:** HLP-231, SRV-193, SRV-194 and TST-720 to TST-723, 7 Low. SRV-194 and TST-720 merge both reviewers'
  reports. The longest chains still growing are at generation 2.
- **Suggested order:** HLP-231, SRV-193 and SRV-194 (messages and docstrings), then TST-720 to TST-723.
- **Checked and found fine:**
  - `set`'s behaviour after its block moved into `_made_absolute`;
  - the size refusal for literal and bound sizes;
  - the result lines;
  - the rollback at each statement of the build;
  - the re-check with the graph and package;
  - `converted`'s guard, which loses no hint the compiler gave;
  - the undo check restoring exactly the first function;
  - each refusal's own compare;
  - the `$` facts and their GUIDE bullet.

### 2026-11-22: Step 3b of ROADMAP item 9 (value connections)

- **Scope:** `git diff bfd5406 11f7691 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the code, and the checks with the docs. No tests were run and no probe was needed:
  the lead settled every suspicion by reading the lines it quotes. HLP-232's Designer side, whether the connection
  survives the source's type change, is left to its fix: either way the read must check. Dropped:
  - the `converted` hint `(#v).x` where `#v.x` would do: valid, and misleads nobody;
  - a graph input whose id starts with `#`: no tool makes one;
  - a hand-made `#` input of a colour type refused against a float4 source: none seen;
  - a stray `#name` left when a later step of the same op fails: the batch's own rule, earlier ops stay;
  - the leftovers the value checks leave on the blend: no later check reads them.
- **Not verified:** none.
- **Resolutions assessed:** TST-719 holds for its drive. HLP-232 and TST-724 follow it (generation 2).
- **Findings:** HLP-232 (Medium), TST-724 (Low-medium), TST-725 to TST-729 (Low). TST-724 and TST-725 merge both
  reviewers' reports.
- **Suggested order:** HLP-232, TST-724, TST-725, then TST-726 to TST-729.
- **Checked and found fine:**
  - the comment rule in every position a `#` can take, with the columns kept;
  - `_input_value`'s refusals, all before `newProperty`;
  - the read's values merged into `inputs`;
  - the unload by UID, with each failure point unloading once;
  - each check passing alone;
  - the expected lines against the printed ones.

### 2026-11-22: Step 3b's fixes (HLP-232, TST-724 to TST-729)

- **Scope:** `git diff be5a0e7 763e8d8 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the code, and the checks with the docs. No tests were run and no probe was needed:
  the lead settled every suspicion by reading the lines it quotes. SRV-196 is rated Low, where one reviewer said
  Low-medium: the safe fix is narrowing the sentence, which its generation prefers. Dropped:
  - `drives` compared in Designer's connection order: no instability is known;
  - a graph input whose id starts with `#`, which now raises a `KeyError`: as before, no tool makes one;
  - the preparation's `lout` and `bout`: kept on purpose, a node feeding an output (HLP-100).
- **Not verified:** none.
- **Resolutions assessed:** TST-724, TST-726, TST-728 and TST-729 hold. HLP-232, TST-725 and TST-727 hold for what
  they list, with follow-ups at generation 2: SRV-195, SRV-196 and TST-730; TST-731; TST-732.
- **Findings:** SRV-195, SRV-196, TST-730, TST-731 and TST-732, 5 Low. SRV-196 merges both reviewers' reports.
- **Suggested order:** SRV-196, SRV-195, TST-731, TST-730, TST-732.
- **Checked and found fine:**
  - the type check on its three routes, with no valid drive refused;
  - `_End` and `_Target` kept in step by the existing test;
  - the re-check's whole-dict compare;
  - the float2 drive, the nine types and the reload's 0.3-then-0.75 read;
  - the undo check's read having no undo step of its own;
  - each check passing alone.

### 2026-11-22: Step 4 of ROADMAP item 9 (function graphs of the package)

- **Scope:** `git diff 090c90f 0c3a93c -- . ':(exclude)PLAN.md'`.
- **How:** three Sonnet reviewers: the compiler, the server with its Designer helper, and the checks with the docs.
  No tests were run and no probe was needed: the lead settled every suspicion by reading the lines it quotes, and
  where Designer's behaviour is open, the fix measures it. Dropped:
  - what Designer does with a function graph calling itself: the compiler refuses it before anything is built;
  - two function graphs of one identifier in folders: no tool makes a folder;
  - a leftover instance node making a false recursion refusal: only after a failure while deleting old nodes;
  - the state read per refusal costing about 6 s: it tells which refusal changed what.
- **Not verified:** none.
- **Resolutions assessed:** none in this diff.
- **Findings:** HLP-233 and TST-733 (Low-medium), and 10 Low: HLP-234 to HLP-237, SRV-197, SRV-198 and TST-734 to
  TST-737. TST-733, TST-734 and TST-735 merge two reviewers' reports.
- **Suggested order:** HLP-233, TST-733 (measurements, one scratch run), then HLP-234 to HLP-237, SRV-197, SRV-198,
  then TST-734 to TST-737.
- **Checked and found fine:**
  - recursion detection, direct, through others, and diamonds;
  - a built-in winning over a function graph of its name;
  - argument checking, by input id;
  - the name rules keeping calls and names apart;
  - the rollback of a new function graph at each statement;
  - the library refusal on both new paths;
  - the re-check of the whole target;
  - the tool's description within `CLAUDE_CODE_LIMIT`;
  - each GUIDE sentence of "Function graphs of the package" against its fact, apart from TST-733's;
  - the pixels no uncalled function graph could give.

### 2026-11-22: Step 4's fixes (HLP-233 to HLP-237, SRV-197, SRV-198, TST-733 to TST-737)

- **Scope:** `git diff 106b43e e968deb -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the code, and the checks with the docs. No tests were run and no probe was needed:
  the lead settled every suspicion by reading the lines it quotes. TST-738 is rated Low, where one reviewer said
  Low-medium: the unit test and the raw API's measurement cover it, and only the tool's path through Designer is
  unchecked. Dropped:
  - a ColorRGBA input restated as a float4, remade with no note: no function graph has been seen with such an input;
  - `defining` tested by truthiness in some places and `is not None` in others: the name is never empty;
  - `$tiling` inside a function graph equal to the default: plausible, and misleads nobody;
  - `$time` inside a function graph unmeasured: GUIDE already says `$time` isn't measured.
- **Not verified:** none.
- **Resolutions assessed:** HLP-235, HLP-237, SRV-197, SRV-198, TST-734, TST-736 and TST-737 hold. HLP-233, HLP-234,
  HLP-236, TST-733 and TST-735 hold for what they list, with follow-ups at generation 2: TST-738, HLP-238, HLP-239,
  TST-739, and TST-740 and TST-741. A note under TST-735 corrects its count of lines.
- **Findings:** HLP-238, HLP-239 and TST-738 to TST-741, 6 Low. TST-738 merges both reviewers' reports.
- **Suggested order:** TST-738, TST-740 (Designer's side), then HLP-238, HLP-239, TST-739, TST-741.
- **Checked and found fine:**
  - `_set_inputs`' scan, traced over nine changes: it keeps the longest prefix wanted that the inputs hold, in order;
  - the read-back, exact on ids and types;
  - left-out inputs as None on both paths;
  - the messages in both modes;
  - the reload really re-reading the package;
  - the "no output node" reply taken as a state, which no line passes on;
  - the baseline check of the refusals.

### 2026-11-22: Step 5 of ROADMAP item 9 (sampling images, a processor's extra inputs)

- **Scope:** `git diff 0cee554 2b552d1 -- . ':(exclude)PLAN.md'`.
- **How:** three Sonnet reviewers: the compiler, the server with its Designer helpers, and the checks with the docs.
  No tests were run. The lead measured one suspicion: `ast.parse` accepts
  `sample(0, p, filter='bilinear', filter='bilinear')`, its keywords `['filter', 'filter']` (SRV-200). The lead
  settled the rest by reading the lines they quote. Dropped:
  - a dead `else` in a test's lambda: it misleads nobody;
  - `_later_image` on a processor listing no `input`: every processor lists one;
  - the size of `functions/checks.py`: no rule limits it;
  - the rule naming a processor's input images, stated in four places: the compiler, the helper, the server's note
    and GUIDE each check it for their own caller.
- **Not verified:** none.
- **Resolutions assessed:** none in this diff.
- **Findings:** SRV-199 (Low-medium), and 5 Low: SRV-200, HLP-240 and TST-742 to TST-744. SRV-199 and TST-743 merge
  two reviewers' reports.
- **Suggested order:** SRV-199, SRV-200, HLP-240, then TST-743, TST-744, TST-742.
- **Checked and found fine:**
  - no check passes whatever the tool does;
  - item 31's rebuilt Z is a real test: a constant Z near 1 fails it.

### 2026-11-22: Step 5's fixes (SRV-199, SRV-200, HLP-240, TST-742 to TST-744)

- **Scope:** `git diff 1750019 a1c5377 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the code, and the checks with the docs. No tests were run and no probe was needed:
  the lead settled every suspicion, and the developer's three new problems, by reading the lines they quote. Where
  Designer's behaviour is open (SRV-201), the fix measures it. Dropped:
  - an FX-Map's inner function reaching a sampling function graph gets no note (the developer, and both reviewers):
    `set_function` can't reach an FX-Map's inner node (HLP-239), and whether an FX-Map's function can sample an
    image is unmeasured. TST-745 narrows GUIDE's claim to match;
  - an int literal above 2^31 outside a sample: no agent writes one in a Designer function, and it is outside this
    diff;
  - "F is called from P.perpixel" also when P reaches F through other function graphs: the guidance is right;
  - `_image_inputs`' changed pattern with no test row: no processor lists `input:0`;
  - `reaching` returned unused into `set_function_resource`'s target (the developer): a few names more in one reply;
  - `categories.py`'s 121 s for `functions` (the developer): a few calls more don't move its place, and the final
    check's run shows the times.
- **Not verified:** none.
- **Resolutions assessed:**
  - SRV-199, SRV-200, HLP-240 and TST-744 hold;
  - TST-742 holds for what it lists, with a follow-up at generation 2: TST-745;
  - TST-743 holds, with follow-ups at generation 2: TST-746 and TST-747. A note under it corrects which check failed
    first;
  - a note under SRV-199 records the function graph its check leaves.
- **Findings:** SRV-201 and TST-745 to TST-748, 5 Low.
- **Suggested order:** SRV-201 (measure first), TST-746, TST-747, TST-748, TST-745.
- **Longest chains still growing:** TST-742 → TST-745 and TST-743 → TST-746, TST-747, at generation 2.
- **Checked and found fine:**
  - the four modes along y, recomputed by hand from the ramp's values;
  - index 39 of 40 reading `input:39`, which rules out a limit at 32;
  - `_unsampled`'s notes against each check's expected text, with the order text for each case;
  - `/simplify`'s cleanups changing no behaviour: `_no_images`, `_images`, `_joined`, `chosen` and the order of
    `sampled.add`;
  - the types, with no new `# type: ignore` or `# noqa`;
  - no text left of the old refusal of an index beyond the node's inputs;
  - REVIEW.md's counts and totals.

### 2026-11-22: Step 6 of ROADMAP item 9 (reading function graphs)

- **Scope:** `git diff d8851f6 fdd44a9 -- . ':(exclude)PLAN.md'`.
- **How:** three Sonnet reviewers: the server tools, the Designer helpers, and the checks with the docs. No tests were
  run and no probe was needed: the lead settled every suspicion, and the developer's two, by reading the lines they
  quote. Where Designer's behaviour is open (HLP-241, TST-750, TST-752), the fix measures it. Dropped:
  - `#name` lines for a get node feeding no output: rare, and the node list shows its connections;
  - `_node_function_read` and `_function_graph_read` repeating parts of `_driving_graph` and `_resource`: cosmetic,
    and `/simplify` weighed them;
  - after `open_graph(function=...)`, a tool left without `graph=` refuses the function graph in the editor: its
    refusal says to pass `graph=`;
  - `search_nodes` matching a description's raw HTML, and 'function' matching all 85: as for the library and the
    atomic nodes before;
  - `apply_edits`' add of an `sbs::function` id: refused, with nothing changed;
  - each `openResourceInEditor` adding a view (the developer): `open_graph` did so before this branch. A ROADMAP item
    is proposed to the user.
- **Unspecified:** `open_graph`'s `node_id` centres the view on a node, a Pixel Processor too, while in
  `describe_graph` and `set_function` it names the node's function. The lead recommends leaving it: the Fields say
  so, and `open_graph(parameter=...)` is refused with the way on.
- **Not verified:** none.
- **Resolutions assessed:** HLP-237, TST-740 and TST-741 hold after this step's changes to their code.
- **DECISIONS.md:** "A definition naming a function or another resource isn't told apart from a graph": its Reopen if
  doesn't hold. `search_nodes` now prints function nodes' definitions, which `describe_node` handles, not function
  graph resources.
- **Findings:** 11 Low: SRV-202 to SRV-204, HLP-241 to HLP-244 and TST-749 to TST-752. SRV-202 and SRV-204 merge
  three reviewers' reports, and HLP-241, HLP-244 and TST-750 two.
- **Suggested order:** HLP-241, HLP-244, HLP-242, SRV-202, SRV-204, SRV-203, HLP-243, then TST-750 and TST-752
  (measurements), TST-751, TST-749.
- **Checked and found fine:**
  - every bullet of the step's text delivered;
  - `describe_graph`'s refusals, made before Designer, with exact texts in their unit tests;
  - `function_differs`: a node-by-node comparison from the output node, one to one;
  - the moves into `core.py`, which give a compositing graph's `describe_graph` the same lines;
  - `node_kind`, `_node` and `_graph_node`, and the fit helpers' wider types, unchanged for compositing callers;
  - the parts' imports and their order in `PARTS`;
  - `list_atomic`'s guard against a function graph in the editor;
  - the undo check's constants against `_function_graphs_line`;
  - the tools' descriptions within `CLAUDE_CODE_LIMIT`.

### 2026-11-22: Step 6's fixes (SRV-202 to SRV-204, HLP-241 to HLP-244, TST-749 to TST-752)

- **Scope:** `git diff 68f45b6 f9543ab -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the code, and the checks with the docs. No tests were run and no probe was needed:
  the lead settled every suspicion by reading the lines it quotes, and checked that Designer ships `pow.sbs`
  (SRV-205). Dropped:
  - TST-752's two shots differing for another reason, such as noise or another widget grabbed: the developer's Step 6
    probe grabbed the view and saw the function graph's nodes, and the check's editor line says which graph is
    current;
  - no unit test for `describe_node`'s function-node branch: it is helper code, which its live check reaches;
  - the comment above `NODE_OR_FUNCTION` naming two of the three tools sharing it, and three long lines: they mislead
    nobody.
- **Not verified:** none.
- **Resolutions assessed:**
  - SRV-203, HLP-241, HLP-243, TST-749, TST-750, TST-751 and TST-752 hold;
  - SRV-202, SRV-204, HLP-242 and HLP-244 hold for what they list, with follow-ups at generation 2: SRV-206, SRV-205,
    TST-753 and HLP-245;
  - a note under HLP-241 records its test's dead setup.
- **Findings:** SRV-205, SRV-206, HLP-245 and TST-753, 4 Low.
- **Suggested order:** SRV-205, SRV-206, HLP-245, TST-753.
- **Longest chains still growing:** SRV-202 → SRV-206, SRV-204 → SRV-205, HLP-242 → TST-753 and HLP-244 → HLP-245,
  at generation 2.
- **Checked and found fine:**
  - HLP-244's split: `_target_of` keeps its refusals in their order, and each new helper's two callers use all it
    returns;
  - `describe_node`'s fallback hides no real "not found", and unloads its temporary package on return;
  - TST-751's code job: a real comparison of every definition's inputs, types and output with `compiler_table()`;
  - the tests of SRV-202, HLP-241 and HLP-242, each failing on the old code;
  - the joined script's load order, and no import cycle among the server modules;
  - no new `Any`, `# type: ignore`, `# noqa` or `cast`;
  - REVIEW.md's counts and totals.

### 2026-11-22: the first Opus round on the whole branch

- **Scope:** `git diff main...8c13564 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`.
- **How:** four Opus reviewers: the compiler, the server tools with README and ROADMAP, the Designer helpers, and the
  live self-test with GUIDE. No probe was needed. The lead ran `test_library_refusal.py`, which fails at HEAD
  (TST-754), and settled the rest by reading the lines they quote. Where Designer's behaviour is open (HLP-247,
  SRV-208, SRV-212), the fix measures it. Dropped:
  - callers through other function graphs when an output type changes: each function graph rebuilt names its own
    callers in turn;
  - the undo check of `set_function` without a `try`, as the older undo checks are, and the function-graph undo
    check missing from two parametrized unit tests: generation 3, with no claim to narrow;
  - `in_the_editor()`'s ten `processEvents()`: it mirrors `open_graph`'s own `_process_events(10)`, so it measures
    what the tool sees, and a stale read can only fail;
  - the `functions` category's leftovers in the self-test's package: `common.CLEAN` unloads it, and no later check
    reads them;
  - "any parameter's" in `set_function`'s docs while curves and gradients are refused: no function can be made there
    (HLP-244's measurement);
  - an empty function graph deleted by a failed build's rollback, the re-check ignoring the inputs' order, and
    callers in other packages: rare, or beyond the tools' reach;
  - `describe.py:70`'s docstring: generation 3, a maintainer's docstring 20 lines above the `if` that shows it
    (DECISIONS.md, Low-value findings);
  - `compiled()` and `refused()` taking `images` and `defining` in another order: cosmetic.
- **Not verified:** none.
- **Resolutions assessed:** every resolution in the four areas holds. Follow-ups: SRV-207 (generation 3), TST-756,
  HLP-248 and TST-757 (generation 2). A note under TST-746 records one more curve made before a `try`.
- **Findings:** TST-754 (Low-medium), and 11 Low: SRV-207 to SRV-212, HLP-247, HLP-248 and TST-755 to TST-757.
  TST-754 merges two reviewers' reports.
- **Suggested order:** TST-754, HLP-247, SRV-212 and SRV-208 (measurements), SRV-210, TST-756, TST-755, TST-757,
  SRV-207, SRV-211, HLP-248, SRV-209, and HLP-246, open from Step 6.
- **Longest chain still growing:** SRV-202 → SRV-206 → SRV-207, at generation 3.
- **Checked and found fine:**
  - no expression compiles to a wrong type, node or argument order, against GUIDE's facts for `sub`, `div`, `mod`,
    `pow`, `lerp`, `cartesian`, the comparisons, `ifelse`, `mulscalar`, the vectors, `atan2`, `clamp`, the swizzles
    and the sample's mode;
  - each argument evaluated once, every built node feeding the output, and the columns through `$`, `#`, dedent and
    non-ASCII text;
  - no expression text reaching Designer as code;
  - every server refusal made before `_edit`, the reads changing nothing, and one `_edit`, one undo group, per call;
  - the write-path helpers going through `_graph_to_edit`, a function graph's replacement deleting the old nodes only
    after the output node moves, and the helpers' load order on Python 3.13;
  - each GUIDE sentence against its "designer facts" cell or check, and every part of `functions` cleaning up its
    package;
  - README's count of 36 tools, its rows, and ROADMAP item 117;
  - no new `Any`, `# type: ignore`, `# noqa` or loose `cast`;
  - the user's DRY instruction: the undo step, `_made_absolute`, `_parameter`, `_take_back_function` and the others
    shared, each fitting its callers, apart from SRV-211.

### 2026-11-22: the first Opus round's fixes (TST-754, SRV-207 to SRV-212, HLP-246 to HLP-248, TST-755 to TST-757)

- **Scope:** `git diff 18e5bf3 64cf1d9 -- . ':(exclude)PLAN.md'`.
- **How:** three Opus reviewers: the compiler with the server tools, the Designer helpers, and the live self-test with
  the docs. No tests were run and no probe was needed: the lead settled every suspicion, and the developer's three, by
  reading the lines they quote. Dropped:
  - a lone `#vv`, a typo of the node's `#v`, now refused with "stands alone" in place of the message listing the
    node's input values: the message is true, and the expression is refused either way;
  - `search_nodes` matching a description's raw HTML while it shows the text unescaped (the developer and two
    reviewers): older than the branch, and rare, as Step 6's review found;
  - `_short_description`, older than the branch, gluing words across tags and keeping newlines (the developer), and
    `html.unescape` decoding a legacy entity written without its semicolon: no description is known to suffer;
  - the misleading messages a Designer whose definitions come back None would give: Designer 16 gives them all;
  - item 9's Done note's "lists that one": ambiguous, not misleading;
  - the entities check relying on `mask_to_paths`, marked deprecated: it would fail loudly;
  - a bevel probe's flat height (the developer): outside the unit.
- **Not verified:** none.
- **Resolutions assessed:** all 13 hold. SRV-208, SRV-210 and SRV-212 hold for what they list, with follow-ups at
  generation 2: SRV-213, and SRV-214. A note under HLP-248 records a fake its fix left unused.
- **Findings:** SRV-213 and SRV-214, 2 Low. A few Lows, so the developer fixes them and an Opus round reviews the
  whole branch again.
- **Suggested order:** SRV-213, SRV-214.
- **Longest chain still growing:** SRV-202 → SRV-206 → SRV-207 has stopped. SRV-210 → SRV-213 and SRV-208, SRV-212 →
  SRV-214 are at generation 2.
- **Checked and found fine:**
  - SRV-210's refusal of a lone `#name` can't fire on a valid expression, and keeps syntax errors first;
  - `list_atomic` prints the same atomic ids in the same order;
  - the `html` import reaching the helpers through `core.py`, and `PARTS` unchanged;
  - HLP-247's check reading the library package the instance uses, and failing if Designer ever changes it;
  - HLP-246's checks failing on `&lt;`, over all 85 definitions;
  - each new check cleaning up on failure, and none passing on an earlier check's state;
  - REVIEW.md's counts and totals.

### 2026-11-22: the second Opus round on the whole branch

- **Scope:** `git diff main...575e566 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`.
- **How:** four Opus reviewers: the compiler, the server tools with README and ROADMAP, the Designer helpers, and the
  live self-test with GUIDE and the rules the branch changed. No probe was needed. The lead compiled `7 / 2`, `i / j`
  and `int(7) / 2` (SRV-216), and settled the rest by reading the lines they quote. Dropped:
  - `sample(1.0, ...)` told to "write a whole number": generation 3, and the message's own examples show `1`;
  - `_value_before`'s hint in a function graph's expression without "and a function graph has none": still true;
  - a `$` inside a comment written without its space, refused by the `$` rule first: too rare;
  - `describe_node('instance:<id>')` refused, `_new_instance`'s docstring, `_resource`'s unguarded `getType()`, and
    `_driving_graph` taking a raising `getPropertyGraph` as no function: older than the branch, or never seen;
  - the leftovers in the self-test's package, dropped in earlier rounds.
- **Unspecified, for the user:** whether the compiler refuses `$pos` outside a Pixel Processor's function, as it does
  `$depth` and `$number`, in place of the Field's warning. And, beside the waiting question on `node_id`,
  `describe_graph(node_id=<a blend>)` is refused without naming `node_ids`.
- **Asked of the user:** which more items move into "Materials from a photo": 13 and 33 (the lead recommends both),
  and 50 (the lead recommends not). 75, 76, 80 and 87 move on the user's word.
- **Not verified:** none.
- **Resolutions assessed:** every resolution in the four areas holds. Follow-ups: SRV-215 (generation 2) and TST-758
  (generation 3).
- **Findings:** 6 Low: SRV-215, SRV-216, SRV-217, HLP-249, TST-758 and AGT-125. A few Lows: the reviews converge
  once the developer fixes them.
- **Suggested order:** TST-758, SRV-216, SRV-215, HLP-249, AGT-125, SRV-217.
- **Longest chain still growing:** SRV-208, SRV-212 → SRV-214 → TST-758, at generation 3.
- **Checked and found fine:**
  - no expression accepted and built wrong, and nothing refused that the grammar documents;
  - every server refusal before the bridge, one `_edit` per call, and repr'd, checked values only in the call strings;
  - every write path through `_graph_to_edit`, instance nodes only of the package's own function graphs, and every
    refusal in the helpers before the first change;
  - each live check failing without its code, cleaning up on failure, and reading no earlier check's state;
  - the four rule texts the user approved agreeing with each other, and AGENTS.md within its budget;
  - README's 36 tools, and every moved ROADMAP item's number and text kept;
  - no new `Any`, `# type: ignore`, `# noqa`, skip or wait.

### 2026-11-22: the user's answers at convergence

- **Scope:** `git diff 3f1f8dc 4aed3a6 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the code with its unit tests, and the live check with GUIDE and ROADMAP. No probe was
  needed: the lead settled every suspicion by reading the lines it quotes, and one reviewer's counts in Designer's
  shipped packages. Dropped: the compiler's `Kind` and the helpers' `_Kind` as two copies of one `Literal`, which
  `plain()`'s test compares; two lines over 120 characters, which ruff doesn't check.
- **Note on Step 2's fixes' log:** its Unspecified item says shipped packages read `$physicalsize`. None does
  (counted 2026-11-22); item 123 says so, and SRV-220 has it checked first.
- **Not verified:** none.
- **Resolutions assessed:** none in this diff.
- **Findings:** 5 Low: SRV-218 to SRV-220, TST-759 and TST-760. A few Lows: the developer fixes them, then the final
  check.
- **Checked and found fine:**
  - the `$pos` refusal: it reaches every direct read (a swizzle, a call's argument, a binding) and fires nowhere
    `$pos` is the pixel's;
  - `kind` passed for every node target, and none for a function graph;
  - each new unit test failing without its code, and each live row failing without the refusal;
  - the negative-int comment, in the user's words;
  - ROADMAP's 116 rows, none lost or doubled.

---

## High

## Medium-high

## Medium

- [x] **HLP-232 · A `#name` keeps the type it was made with, while its source's type changes** · `mcp_server/designer_helpers/edits.py:381-405`, `mcp_server/designer_helpers/functions.py:115`, `:128`, `mcp_server/server_tools/functions.py:156` · confirmed · follows TST-719, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `_input_value` types a new `#name` from the source's output when `connect` runs. A Value Processor
    without a function gives a float (GUIDE). The read gives the compiler each `#` value's own type, never its
    source's. And nothing checks a Value Processor's new type against the `#` values it drives.
  - **Scenario.**
    1. One `apply_edits` batch adds a Value Processor and connects it into a blend's `#v`. `#v` is made a float.
    2. `set_function` gives the processor `float4(...)`.
    3. `set_function` on `opacitymult` with `#v` compiles cleanly as a float.
  - **Resolution: done**.
    - **Test:** unit tests in `tests/unit/test_set_function.py`:
      - a `#v` fed a float4 is refused, naming both types;
      - a parameter's function reading an unconnected `#v` is refused;
      - only the names the expression reads are checked;
      - a Value Processor refuses a result unlike a value it drives;
      - a processor's result says an unconnected `#name` reads 0.
  - Questioned by SRV-195, SRV-196 and TST-730 (2026-11-22).

      In `check_value_connection_refusals`: the processor given a float4 while it drives the float2 `#p`, `#p` fed a
      float4 after the processor changed outside the tools, and `#p` after a disconnect. Each built in the first
      scratch run, and the blend read 0.
    - **Cause:** a `#name` keeps the type it was made with, the read gave only that type, and nothing compared the
      source's type or a Value Processor's new one.
    - **Fix:** the read gives `fed` (what feeds each `#name`, through `_other_end`) and `drives` (what a Value
      Processor's output feeds). `_value_refusal` and `_unconnected` check the names the function reads, and the
      build's re-check covers both. Measured first, in `check_input_values`: the connection stays when the source's
      type changes, and `#c` stays a float. An unconnected `#name` makes `opacitymult` compute 1, and reads 0 in a
      Pixel Processor and in a Value Processor. So it is refused in a parameter's function and noted in a processor's
      (the developer's choice, which the lead accepts).
    - **Also covered:** a function built before a later disconnect, or before a type change in Designer's own UI,
      stays wrong until `set_function` runs on it again. Seeing that would take reading the function graphs, which
      is Step 6's.

    Designer computes the parameter wrongly, raising nothing. An unconnected `#name` (after a `disconnect`) is
    read just as silently.
  - **Fix.** At the read, take each `#` value's type from what is connected into it, and refuse a `#name` whose
    source gives another type, naming both. Say when a `#name` has nothing connected. For a Value Processor, refuse
    a result type that differs from a `#` value it drives.

## Low-medium

- [x] **TST-700 · The compiler relies on what nodes compute, which no check measures** · `mcp_server/GUIDE.md:273-274`, `mcp_server/function_compiler.py:456`, `tests/test_all_tools/functions/designer_scripts/function_nodes.py:308-326` · confirmed · found 2026-11-21 by two reviewers (Sonnet)
  - **Defect.** The table checks types, not what a node computes. The compiler relies on several things no check
    measures:
    - `vector2`'s order: `componentsin` as x, `componentslast` as y. GUIDE.md:274 says so for `atan2`, but
      `check_atan2` feeds a `const_float2`, and the vector cells are `vector3` and `vector4` only;
    - `sub`'s and `div`'s operand order, `pow`'s and `%`'s against Python's;
    - `lr`, `lreq`, `gt` and `gteq` as `<`, `<=`, `>` and `>=`;
    - `ifelse` taking `ifpath` when the condition is true;
    - `lerp`'s `x`, `cartesian`'s (rho, theta) in radians;
    - `mul` of two vectors componentwise, and the casts' rounding;
    - `ivector*` and `iswizzle*` order.
  - **Scenario.** If one of them differs, every expression using it compiles cleanly and computes a wrong value. An
    example is every `float2(f, g)` with `vector2`'s inputs swapped. Designer raises nothing, and the unit tests
    encode the same assumption.
  - **Fix.** A "designer facts" check in `functions` computing each node with asymmetric constants against the value
    Python gives, such as `sub(0.7, 0.2)`, `lr(0.2, 0.7)` and `vector2(0.1, 0.2)`. Where Designer differs, the compiler
    follows it. GUIDE.md says what is measured.
  - Questioned by TST-705, TST-706, TST-707 and TST-708 (2026-11-21).

  - **Resolution: done**.
    - **Test:** `check_what_nodes_compute`, the `computed` part of `function_nodes.py`, 43 cells against Python's
      values. It failed first with no part (40 "no line"). Then 3 cells failed on negative ints: `-7 % 3`, `-7 / 2` and
      `toint1(-1.7)`.
    - **Cause:** the compiler assumed Python's meaning for every node, and Designer's function ints act as unsigned
      (measured on macOS): `tofloat(-7)` reads huge, `lr(-1, 1)` is false, `neg(3)` is 0, `div(7, -2)` and
      `mod(-7, 3)` are 0, and `toint1` of a negative is 0.
    - **Fix:** the lead chose (2026-11-21) to refuse what the compiler can see, and to record the rest:
      - a negative int literal, a folded one included, is refused, naming the float form;
      - unary minus on an int is refused, naming `-float(i)`;
      - GUIDE.md's "What nodes compute" says what was measured, and that ints must stay at 0 or above. Six cells hold
        Designer's negative-int values.

      Every other node agrees with Python: the vector and swizzle orders, int and float, `sub`, `div`, `pow`, float
      `mod` (floor), `lerp`'s `x`, the six comparisons, `and`, `or`, `not`, `ifelse`, `cartesian` in radians, `mul`
      componentwise, `mulscalar`, and `toint1` truncating a positive.
    - **Also covered:** the comparisons' labels come from the compiler's `COMPARISONS`, so mapping an operator to
      another definition fails the check. Windows isn't measured.
  - Note (2026-11-21): the check has 42 cells, not 43 (Step 2's fixes' review). The gaps it leaves are TST-705 to
    TST-708.

- [x] **HLP-225 · A function on `$format` or `$outputsize` is ignored, or read as an offset, and no size is checked** · `mcp_server/designer_helpers/functions.py:94-97`, `:145` · measured · found 2026-11-21 by two reviewers (Sonnet)
  - **Defect.** `set_function` gives any parameter its function, with none of the rules `apply_edits`' `set` applies to
    `$` parameters. The runner measured, on a levels node in a 64 px graph:
    - `int(1)` on `$format` at the default inheritance (RelativeToInput) built "1 function node" and left the format
      at RGBA8. At Absolute it worked;
    - `int2(5, 5)` on `$outputsize` at the default gave 2048 px, an offset, where at Absolute it gave 32 px;
    - `int2(15, 15)` at Absolute computed 8192 px, refused by nothing. `set` refuses 15 ("log2 of the size in
      pixels ... 13 is 8192 px, the largest").
  - **Scenario.** An agent sets a node's size or format from an expression. The result line says the function was
    built, and the node computes at another size, or its format doesn't change.
  - **Fix.** As `set` does, reusing its code: make `$format` and `$outputsize` Absolute when they get a function, and
    refuse a constant size outside 0 to 13 with `set`'s own message. A size computed from graph inputs can't be
    checked before it runs, so the result line says the value is a log2 size.
  - **Resolution: done**.
    - **Test:** the live `check_set_function_on_a_dollar_parameter` failed: `int2(2, 2)` gave 64x64 (an offset),
      `int(1)` left RGBA8, `int2(15, 15)` was built at 8192 px. Four unit tests failed too: Absolute after the output
      moves, `$randomseed` left alone, 15 refused before anything is built, and the result line. A "designer facts"
      check, `check_a_function_on_a_dollar_parameter`, measures that a function on `$outputsize` at the default
      inheritance gives an offset and one on `$format` is ignored, and that both take effect once made Absolute after
      the build.
    - **Cause:** the tool gave `$` parameters their function without `set`'s rules.
    - **Fix:** `set`'s block moved into `_made_absolute` (`designer_helpers/edits.py`), which `set_params` and
      `set_function` both call after a successful build. A constant size goes through the existing
      `_refuse_bad_size`, with `set`'s own message. The result line says the parameter is Absolute now and its value
      a log2 size.
  - Questioned by SRV-194 and TST-723 (2026-11-22).

- [x] **TST-719 · The Value Processor check doesn't drive another node's parameter** · `tests/test_all_tools/functions/checks.py:418-437` · measured · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** The step's text asks for "a Value Processor whose result drives another node's parameter". The check
    reads the processor's own value. The runner measured how the drive works: `newProperty('#x', SDTypeFloat, Input)`
    on the receiving node, the Value Processor connected into `#x`, and the parameter's function a `get_float1` of
    `#x`. The blend read 0.25, then 0.75 as the Value Processor changed. The tools can't build that today: no op makes
    an input value, and the grammar can't read `#x`.
  - **Scenario.** A Value Processor's function, set by the tool, drives nothing, and nothing shows it can.
  - **Fix.** The user's choice (asked 2026-11-21): value connections in this branch, or the check narrowed and value
    connections in ROADMAP.md.
  - **Resolution: done**. Step 3b, on the user's choice (2026-11-22: "Add them now (Recommended)").
    - **Test:** `check_set_function_on_a_value_processor` drives a blend's opacity through the tools, reading 0.25,
      then 0.75 as the processor's function changes. It failed before the fix ("input '#v' not on node").
    - **Cause:** no op made an input value, and the grammar couldn't read `#x`.
    - **Fix:** `apply_edits`' `connect` into a `#name` makes the input value, typed from the source's output
      (`_input_value`, `designer_helpers/edits.py`), and refuses a bad name, an image source and a value of another
      type. The compiler reads `#name` with the getter of its type, and `set_function`'s read lists the node's `#`
      values.
    - **Also covered:** a Pixel Processor reading `#w`, the refusals, and a "designer facts" check
      (`check_input_values`): a value survives a save and a reload, and a mismatch is accepted silently.
  - Questioned by HLP-232 and TST-724 (2026-11-22).

- [x] **TST-724 · "Typed from the source" is measured and tested for float only** · `tests/test_all_tools/functions/checks.py:499-531`, `:563-612`, `tests/test_all_tools/functions/designer_scripts/function_nodes.py:818-876`, `mcp_server/GUIDE.md:341-343` · confirmed · follows TST-719, generation 2 · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** `_VALUE_TYPES` takes nine types, and the `ops` text says an input value is "made with the output's
    type". The only value the tool makes in any check is a float. The facts make a float2 `#v` directly, never
    connected or read. The unit test mocks the source as a float and doesn't assert what `newProperty` receives.
  - **Scenario.** A regression making every value a float passes every check. A float2 or int drive then computes
    wrongly, silently.
  - **Fix.** A float2 drive in the refusals check (`pair` into a fresh `#p`, then `#p.y` read at 0.4). A unit
    assertion of the type `newProperty` receives. Measure the other types before GUIDE says they work, or narrow
    the sentence.
  - **Resolution: done**.
    - **Test:** a float2 drive through the tools (`pair` into a new `#p`, made a float2, `#p.y` read at 0.4), a unit
      assertion that `newProperty` gets the output's own type, and facts making an input value of each of the nine
      types. They passed at once: the code was right, and these checks now guard it.
    - **Fix:** GUIDE.md names the nine measured types.

- [x] **HLP-233 · Replacing a function graph's inputs deletes and remakes later ones that could stay** · `mcp_server/designer_helpers/functions.py:403-414`, `mcp_server/server_tools/functions.py:264-277` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `_set_inputs` keeps only the inputs' common leading part. `[uv, k, x]` becoming `[uv, x]` deletes `k`
    and also deletes and remakes `x`, and with it every call's connection into `x`. Deleting `k` alone gives the
    right order, since Designer lists inputs in the order made. With `inputs` left out, an input whose Designer type
    differs from its function type (a ColorRGBA read as a float4) compares unequal, and is remade silently, with no
    note.
  - **Scenario.** An agent drops one input, and every later input's callers lose their connection. The note then
    tells it to rebuild each caller, hand-made ones included.
  - **Fix.** Keep an input when it equals the next one wanted, delete it otherwise, then make the rest (the
    reviewer's scan, shorter than today's). Measure that a later input's connection survives a middle one's
    deletion. With `inputs` left out, keep the inputs as they are.
  - **Resolution: done**.
    - **Test:** `test_the_build_keeps_each_input_that_is_the_next_one_wanted` failed on its "middle one dropped" and
      "first one dropped" cases (`x` made again). `test_inputs_left_out_reach_the_build_as_none_to_keep_them` failed:
      the build was given `('tint', 'float4')`. Measured in the `resources` part: deleting `b` keeps a call's
      connection into `c`.
    - **Cause:** only the inputs' common leading part was kept, and left-out inputs reached the build in the
      compiler's types.
    - **Fix:** `_set_inputs` keeps each input that is the next one wanted. Left-out inputs reach the build as None,
      which leaves them as Designer has them.
  - Questioned by TST-738 (2026-11-22).

- [x] **TST-733 · The facts a call relies on are measured for few cases** · `tests/test_all_tools/functions/designer_scripts/function_nodes.py:1099-1182`, `mcp_server/GUIDE.md:369-390`, `:70` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.**
    - inputs of ten types are made, but only float and float2 inputs are read in a body or passed by a call;
    - a call's output type is read for float4 and float only;
    - only `$pos` is read inside a function graph, though the grammar takes `$size`, `$sizelog2`, `$tiling` and
      `$time` there;
    - the inputs' order after a save and a reload isn't read, though a call passes its arguments by that order;
    - "an input left unconnected reads 0" rests on a float;
    - "any expression of the package" calls one, measured in a Pixel Processor and another function graph only.
  - **Scenario.** A function graph with an int or bool input, or reading `$size`, or two inputs of one type after a
    reload, computes a wrong value silently.
  - **Fix.** Cells in the `resources` part: an int and a bool input read and passed, a call's bool and int output,
    `$size`, `$sizelog2` and `$tiling` read inside a called function graph, the inputs' order after the reload, a
    vector input left unconnected, and a call from a Value Processor or a parameter's function. Or narrow each
    sentence to what holds.
  - **Resolution: done**.
    - **Test:** cells in the `resources` part, one scratch run: 19 failed first ("no line"), then 54 passed.
    - **Fix:** measured:
      - int and bool inputs read in a body and passed by a call;
      - a call giving a bool and an int;
      - `$size`, `$sizelog2` and `$tiling` inside a function graph;
      - a float3 input left unconnected reading (0, 0, 0);
      - calls from a Value Processor and from a blend's `opacitymult`;
      - the inputs' order kept after a reload;
      - the ids `Uv`, `_k`, `k_`, `a1` and `x_2` kept as given.
  - Questioned by TST-739 (2026-11-22).

      GUIDE.md says "measured with float, float2, int and bool inputs", and names the output types and the size
      measured.

- [x] **SRV-199 · Redefining a function graph so it samples more images tells its callers nothing** · `mcp_server/server_tools/functions.py:300-310`, `mcp_server/function_compiler.py:30` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** `_set_resource`'s `changed` compares the inputs and the output only, though `before` holds the
    samples too. A function graph redefined to sample an image index its callers' processors have nothing connected
    to is built with no note. The compiler's docstring says such a sample is "checked at its calls", but the calls
    were checked when they were built, against the old samples.
  - **Scenario.** A function graph called from a Pixel Processor with one image is redefined to `sample(1, $pos)`.
    The result says nothing, and the processor reads (0, 0, 0, 0) where the agent expects its second image.
  - **Fix.** When the samples widen, a note naming each caller and the input it has nothing connected to, as the
    note for changed inputs does. The compiler's docstring says what is checked, and where.
  - **Resolution: done**.
    - **Test:** `test_a_function_graph_sampling_an_input_its_callers_lack_says_so` failed with no lines, and
      `test_the_read_gives_each_nodes_function_reaching_the_function_graph_with_its_images` with a KeyError for
      `reaching`. Live, `check_set_function_samples_two_inputs` redefines `second` to `sample(2, uv)` and checks the
      note for both callers.
    - **Cause:** the result compared the inputs and the output only, and the read gave no caller's images.
    - **Fix:**
      - the read (`_callers`, `designer_helpers/functions.py`) returns `reaching`: each node's function that calls
        the graph, directly or through others, with that node's images;
      - `_unsampled_by_callers` (`server_tools/functions.py`) names the callers before the input's note, and tells a
        parameter's function that calls the graph to get another function;
      - the compiler's docstring says what is checked, and where.
    - **Also covered:** the note comes whenever the graph samples an input a caller lacks, not only when the samples
      widen. An FX-Map's inner function isn't walked (the review log of Step 5's fixes).
  - Note (2026-11-22): `check_set_function_samples_two_inputs` leaves the function graph `second` in the package,
    now sampling `input:2`. Its callers are deleted, and no later check reads it.

- [x] **TST-754 · A unit test fails on the branch: `describe_function` reads through `find_graph` unlisted** · `tests/unit/test_library_refusal.py:143-165`, `mcp_server/designer_helpers/describe_functions.py:59` · measured · found 2026-11-22 by two reviewers (Opus)
  - **Defect.** `test_every_helper_either_edits_through_the_check_or_only_reads` requires every top-level helper
    calling `find_graph` to be listed as a read or an edit. Step 6's `describe_function` calls it and isn't listed.
    The test file wasn't touched after Step 4, so no developer ran it since (measured: it fails at HEAD).
  - **Scenario.** The final check's unit suite fails, and the merge waits on it.
  - **Fix.** List `describe_function` among the reads. Then find every unit test that reads the source of a file this
    branch changed, beyond the test files it touched, run them by name, and fix what fails.
  - **Resolution: done**.
    - **Test:** `test_every_helper_either_edits_through_the_check_or_only_reads` failed at HEAD: "Extra items in the
      left set: 'describe_function'".
    - **Cause:** Step 6's `describe_function` calls `find_graph` unlisted, and each developer ran only the test files
      it touched.
    - **Fix:** `describe_function` is listed among the reads.
    - **Also covered:** the unit tests reading the source of a file this branch changed passed at HEAD (1353) and
      after the fixes: those reading `designer_helpers.source()` or its parts (`test_designer_helpers`,
      `test_put_backs`, `test_shot3d`, `test_frames3d`), those running the joined helpers through their fixtures
      (`test_batch_fields`, `test_default_output`, `test_export_outputs`, `test_fit_view`, `test_same_graph`,
      `test_mac_window`, `test_quit_helper`, `test_unsaved_dependency`, `test_view3d_helpers`), `test_bridge`,
      `test_waits`, `test_constants`, `test_windows_simulation`, `test_designer_scripts`, `test_plugin`,
      `test_view3d`, and every `test_selftest_*` file.

## Low

- [x] **TST-695 · A Pixel Processor's result is measured for four types only** · `tests/test_all_tools/functions/designer_scripts/function_nodes.py:334-345`, `mcp_server/GUIDE.md:288-291` · confirmed · found 2026-11-21 by two reviewers (Sonnet)
  - **Defect.** `measure_processors` computes a float, a float2, a float4 and an int (`const_int1`) as `perpixel`'s
    result. `getTypes()` lists only float4, yet a float computes grey, so what `perpixel` takes shows only per type.
    GUIDE's "a float2 or an int computes black either way" rests on `const_int1` alone. A float3, a bool and int2 to
    int4 are never computed.
  - **Scenario.** Step 3 decides which result types it accepts. A float3 is the natural type for a colour: refusing
    it may be needless, and accepting it would be a guess.
  - **Fix.** Add cells for a float3, a bool and int2 to int4, with `colorswitch` on and off. Expect their lines in
    `check_a_processors_function`, and say in GUIDE.md what each computes.
  - **Resolution: done**.
    - **Test:** `check_a_processors_function` expects lines for a float3, a bool and int2 to int4, with `colorswitch`
      on and off. The developer's scratch run failed all 10 ("no line") before the cells existed. A guess of colour
      for a float3 then failed on the measured black.
    - **Cause:** the cases covered four of `perpixel`'s result types.
    - **Fix:** the cells in `function_nodes.py`'s processors part. GUIDE.md says a float2, a float3, a bool or an int
      to int4 computes black, raising nothing, and only a float or a float4 makes a value.
    - **Also covered:** both `colorswitch` modes for each type.

- [x] **TST-696 · "A connection of the wrong type is made anyway" isn't measured** · `tests/test_all_tools/functions/designer_scripts/function_nodes.py:135-140`, `mcp_server/GUIDE.md:273-275`, `tests/test_all_tools/functions/checks.py:124-126` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** `connects()` returns `'connected'` whenever `link()` doesn't raise, and never reads the connection
    back. Designer's `newPropertyConnectionFromId` can return None without raising (`sd/api/sdnode.py:248-250` in
    Designer's app). The pixels can't tell either: a float2 (0.2, 0.4) plus an unconnected float2 `b` gives the same
    (0.2, 0.4) as plus a connected float.
  - **Scenario.** If Designer drops the connection silently, GUIDE's bold sentence is untrue, and an agent writing
    `sd` code reasons from a connection that isn't there.
  - **Fix.** Read the connection back for the float into `add`'s float2 `b` and into `samplecol`'s `pos` (the number
    of connections on that input), and expect it. Or narrow GUIDE.md and the docstring to "raises nothing".
  - **Resolution: done**.
    - **Test:** the expected lines read `raised nothing, 1 connection` for the three wrong-type connections and both
      inputs of the nine vector cells. 12 lines failed while `connects()` printed `connected` without reading back.
    - **Cause:** `connects()` took "didn't raise" for "connected".
    - **Fix:** `connects()` counts the target input's connections after linking. Every one reads exactly 1, and
      GUIDE.md adds that the input then holds that one connection.
    - **Also covered:** the vector cells, which go through the same `connects()`.

- [x] **TST-697 · GUIDE's new bullet says more than its checks measure, and one line reads as contradicting another** · `mcp_server/GUIDE.md:272`, `:281-282`, `:288-290`, `:297` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.**
    - 281-282, "`swizzle2` to `swizzle4` take an int2 to int4, one index per component": only `swizzle2` (2, 0) is
      computed; `swizzle3` and `swizzle4` are checked by their types only;
    - 288, "`perpixel` lists float4": read only while its function has no output node;
    - 272, "an operator's first connection settles its inputs and output": only a first connection into `a` is
      measured;
    - 289-290, "(RGBA8)" and "(LUM8)": read in an 8-bit graph, with `$format` inherited;
    - 297, "`deletePropertyGraph`, then `newPropertyGraph`" doesn't say on `perpixel`. Lines 250-252 say
      `deletePropertyGraph` resets a `$` parameter's inheritance, while this bullet says an Absolute `$outputsize` is
      kept.
  - **Scenario.** An agent writing `sd` code relies on a sentence no check holds, and a Designer that changes it goes
    unseen.
  - **Fix.** Narrow each sentence to what was measured, or add the cell where it is one line (`swizzle3`, `perpixel`'s
    types after `setOutputNode`). Say "on `perpixel`" on line 297.
  - **Resolution: done**.
    - **Test:** new expected lines for a first connection into `b`, `swizzle3` (2, 0, 1) and `swizzle4`
      (3, 2, 1, 0) computed, and `perpixel`'s types read once its output node is a float, in both modes. Each failed
      first, as a missing line.
    - **Cause:** sentences written from fewer cases than they name.
    - **Fix:** the cells above, giving (z, x, y), (w, z, y, x) and float4 in every state. GUIDE.md narrowed to "an
      `add`'s first connection", "(RGBA8 in an 8-bit graph)" and "(LUM8 in an 8-bit graph)", and says
      `deletePropertyGraph` on `perpixel` left the `$outputsize` inheritance as it was, unlike a `$` parameter's own
      function.
    - **Also covered:** the bullet's other sentences were rechecked against the checks by the developer.

- [x] **TST-698 · The functions checks' docstrings and comments say what doesn't hold** · `tests/test_all_tools/functions/checks.py:1-2`, `:29`, `:95`, `:216-217` · confirmed · found 2026-11-21 by two reviewers (Sonnet)
  - **Defect.**
    - "the plan's compiler" (lines 29 and 95) names PLAN.md, which is deleted with the branch;
    - the module docstring says "Each script works in a package of its own and closes it", but `definitions.py`
      makes none;
    - `check_replacing_a_function` says the replacements keep "its other parameters", but only `$randomseed` and an
      Absolute `$outputsize` are read back, and `colorswitch` stays at its default.
  - **Scenario.** After the merge, a reader looks for a plan that no longer exists, or trusts a replacement to keep a
    parameter no check reads.
  - **Fix.** Name ROADMAP item 9 instead of the plan, say "each script that makes a package closes it", and name the
    two parameters.
  - **Resolution: done**. Docstrings and comments only, so no failing test.
    - **Fix:** "ROADMAP item 9's compiler" in both places, "Each script that makes a package closes it", and the
      replacement check's docstring names `$randomseed` and the Absolute `$outputsize`.

- [x] **TST-699 · The definitions' JSON is typed without a check** · `tests/test_all_tools/functions/checks.py:101` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** `printed: dict[str, Definition] = json.loads(...)` states a shape no code checks.
    `.claude/rules/python.md` takes parsed JSON as `object` until it is checked.
  - **Scenario.** If the script's output changes shape, the check fails with a `KeyError` or `TypeError` in a
    comprehension, not on a check line that says what was wrong.
  - **Fix.** Load it as `object` and check its shape explicitly, failing a check that names what was wrong.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_selftest_check_setups.py::test_definitions_of_another_shape_fail_a_check_that_says_what_is_wrong`
      feeds the check JSON of other shapes. Its 4 first cases raised before the fix: an `AttributeError` and three
      `KeyError`s. A fifth, `connectable: 1`, was added with the fix.
    - **Cause:** the parsed JSON was given its type without a check.
    - **Fix:** `tests/test_all_tools/functions/parsing.py` holds the `TypedDict`s and `definitions_in()`, which checks
      the shape with pydantic's `TypeAdapter` in strict mode. A wrong shape fails a check naming where and what, such
      as `sbs::function::add.inputs.0.connectable: Input should be a valid boolean`.

- [x] **TST-701 · The definitions comparison's failure line hides the table's side** · `tests/test_all_tools/functions/checks.py:64-70` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** The detail prints the names that differ, then the first one's whole Designer and table entries.
    `common.check` cuts a detail at 150 characters (`common.py:76`), so the table's entry, and most of Designer's, are
    cut off for any definition with two inputs or more. A passing line ends with an empty `differ:`.
  - **Scenario.** A Designer whose definitions changed, the case the check exists for, fails it naming the definition
    but not what changed.
  - **Fix.** Print the first difference in short form (the input id and the two type lists), and nothing when none
    differ.
  - **Resolution: done**.
    - **Test:** a unit test in `tests/unit/test_selftest_check_setups.py`. Its 4 cases failed on the long detail.
    - **Cause:** the detail printed whole entries, which `common.check` cuts at 150 characters.
    - **Fix:** `parsing.difference()` gives the first difference in short, such as "add: input b: Designer
      int,...,float4; the table int,float; also pow2", and a passing line prints none.
  - Note (2026-11-21): `difference()`'s `inputs:`, `connectable`, `outputs:` and "not in the table" branches have no
    unit case. Read and found right, generation 2, so a note (Step 2's fixes' review).

- [x] **TST-702 · `sys.path` is set in four places** · `tests/test_all_tools/__init__.py:8-11`, `tests/test_all_tools/common.py:25-26`, `:45`, `tests/test_all_tools/render/checks.py:243` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** The package's `__init__.py` now puts the root and `mcp_server` on `sys.path`. Every module of the
    package imports it first, so `common.py`'s two inserts (with their `noqa: E402`) and `render/checks.py`'s run-time
    insert of `mcp_server` repeat it.
  - **Scenario.** A reader of `common.py` takes it as what makes `project_constants` importable, the confusion
    `test_a_module_imports_first_in_a_fresh_interpreter` was written against.
  - **Fix.** Keep `__init__.py` as the one place. Remove the other inserts, and the `noqa` marks they needed.
  - **Resolution: done**. A refactor.
    - **Test:** `test_a_module_imports_first_in_a_fresh_interpreter`, and `render.run` in the developer's scratch run,
      pass before and after.
    - **Fix:** `common.py`'s two inserts and their `noqa: E402` are gone, its imports joined the top block and
      `BUNDLE = ROOT` comes from `project_constants`. `render/checks.py` lost its run-time insert and the imports only
      it used.

- [x] **TST-703 · GUIDE gives an unmeasured fact as measured** · `mcp_server/GUIDE.md:279` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** "`$depth` and `$number` are an FX-Map's" follows "which aren't measured;" and names no source. Adobe's
    page is its only source.
  - **Scenario.** An agent takes it as measured.
  - **Fix.** "Adobe's page says `$depth` and `$number` are an FX-Map's".
  - **Resolution: done**.
    - **Test:** unit tests that `$depth` and `$number * 2` are refused, seen failing first.
    - **Fix:** on the user's word (2026-11-21), the compiler refuses `$depth` and `$number`, saying each is an FX-Map's
      variable. GUIDE.md says Adobe's page lists them under the FX-Map and Designer's shipped packages read them only
      in FX-Map graphs (an analyst's count, which the lead repeated: 6 and 299). `$time` is marked unmeasured, and
      `check_system_variables` reads only the four it measures.

- [x] **TST-704 · The compiler's unit tests cover less than their docstrings claim** · `tests/unit/test_function_compiler.py:1-3`, `:22`, `:50-52`, `mcp_server/function_compiler.py:10`, `:595` · confirmed · found 2026-11-21 by two reviewers (Sonnet)
  - **Defect.** The file's docstring claims "each construct of the grammar and each refusal". No test reaches:
    - `_converted`'s parenthesised hint (`v2 + (v3 * 2)`);
    - `iswizzle2` to `iswizzle4`;
    - a name bound to a number used in two contexts in one expression;
    - a variable called as a function (`$pos(f)`);
    - `_where`'s column after a non-ASCII character;
    - `_broadcast`'s one shared `vector2`, which the tree string prints twice either way.
  - Questioned by TST-710 (2026-11-21).
  - Questioned by TST-757 (2026-11-22).

    And `compiled()`, which checks every compiled function, never checks that a vector's two inputs add up to its
    size. The table can't: `vector3` lists a float or a float2 on both inputs.
  - **Scenario.** A change that breaks one of these passes the tests.
  - **Fix.** A one-line case for each, a node count where sharing matters, and a size check in `compiled()` for every
    `vector*` and `ivector*` node.
  - **Resolution: done**.
    - **Test:** cases for `iswizzle2` to `iswizzle4`, the parenthesised hint `v2 + (v3 * 2)`, a number used in two
      contexts, `$pos(f)`, a column after `é`, and `c / f`'s node count with its shared `vector2`. `compiled()` checks
      that every vector's inputs add up to its size. They passed before any code change: the finding was missing
      coverage, not a defect.
    - **Fix:** the docstrings claim only what the tests cover.

- [x] **SRV-187 · `v * 2` builds `mul` with a constant vector, where the step says `mulscalar`** · `mcp_server/function_compiler.py:408-417`, `tests/unit/test_function_compiler.py:68`, `:103` · confirmed · found 2026-11-21 by two reviewers (Sonnet)
  - **Defect.** `_float_and_vector` sees only built nodes, so a literal takes the vector's type: `$pos * 2` builds
    `mul(get_float2, const_float2(2, 2))`. Step 2's text says a vector times or divided by a float uses `mulscalar`,
    and its later change keeps `mulscalar` for `*`. `v / 2` builds `div` with a `const_float2`, which the later change
    allows (a float broadcast in `/`).
  - **Scenario.** The value is the same only if `mul` of two vectors is componentwise, which no check measures
    (TST-700). The step's own example `$pos * 2 - 1` depends on it.
  - **Fix.** A literal with a vector in `*` builds `mulscalar` with a `const_float1`, in both orders, as a built float
    does.
  - **Resolution: done**.
    - **Test:** `$pos * 2`, `2 * v3` and `k = 2; $pos * k` expected `mulscalar`, and failed on `mul` with a
      `const_float2`.
    - **Cause:** `_float_and_vector` saw only built nodes.
    - **Fix:** `_scalar_and_vector` takes a number too. `*` with a float vector builds `mulscalar(v, const_float1)` in
      both orders, and `+ - /` still give a number the vector's type.

- [x] **SRV-188 · Some refusal messages mislead, and leading spaces are refused** · `mcp_server/function_compiler.py:249-271`, `:553-560`, `:571-592`, `tests/unit/test_function_compiler.py:347-366` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.**
    - `length(f)`, `normalize(f)` and `dot(f, g)` on floats say "write float2(f, f)". That compiles, and computes
      √2·|f| or 2·f·g;
    - a mix's hint depends on the operand order: `min(v2, f)` says "write float2(f, f)", and `min(f, v2)` says "write
      v2.x";
    - `int(2.5)` says "`2.5` must be an int here", without saying a literal isn't cast;
    - an expression that starts with a space, or indented multi-line text, is refused as "unexpected indent", since
      `ast.parse` gets the raw text.
  - **Scenario.** An agent follows the hint and gets a clean compile with a wrong value, or is refused for pasted
    indentation.
  - **Fix.** No hint, or `abs(f)`, for `dot`, `length` and `normalize` of a scalar. One hint whatever the order. A
    message saying to write `2` or `int(f)` for a literal. Dedent and strip the text before parsing, keeping the
    columns right.
  - **Resolution: done**.
    - **Test:** 13 cases, which failed first:
      - the float2 hint on `length(f)`, `normalize(f)` and `dot(f, g)`;
      - hints depending on the operand order (`min(f, v2)`, `v3 + v2`, `i2 + v3`);
      - `int(2.5)`;
      - indented text: `'  f + foo'`, a multi-line indent, `'  f + )'`, each with its column.
    - **Fix:**
      - `_nearest` takes only types no larger than the value's, so no hint grows a value into a vector;
      - `_mix` converts both sides to one type whatever their order;
      - a non-int number says "write a whole number";
      - `textwrap.dedent` runs before parsing, and `_place`, where every column is formatted, adds the indent back.
  - Questioned by SRV-190 (2026-11-21).

- [x] **SRV-189 · The refusal of `-b` lists an int among what `-` takes** · `mcp_server/function_compiler.py`, `tests/unit/test_function_compiler.py:366` · confirmed · found 2026-11-21 by the developer (Opus)
  - **Defect.** `-b` on a bool says "`b` is a bool, where `-b` takes an int, float, float2, float3 or float4". That
    list is the table's `neg` inputs, but unary minus on an int is now refused (TST-700).
  - **Scenario.** An agent negates an int, as the message allows, and is refused.
  - **Fix.** Leave the int out of the types the message lists for unary minus.
  - **Resolution: done**.
    - **Test:** the `-b` case failed on "takes an int, float…".
    - **Fix:** `_negated` refuses an int first, then checks the value against `FLOATS`: "`b` is a bool, where `-b`
      takes a float, float2, float3 or float4".

- [x] **TST-705 · The maths functions the compiler builds aren't computed by any check** · `tests/test_all_tools/functions/designer_scripts/function_nodes.py:576-667`, `tests/test_all_tools/functions/checks.py:255-322`, `mcp_server/GUIDE.md:297-306` · confirmed · follows TST-700, generation 2 · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** `check_what_nodes_compute` measures the orders, the comparisons, `ifelse`, `lerp`, `cartesian` and
    `mul`. The other atomic functions the compiler builds are computed by no check: `abs`, `ceil`, `cos`, `dot`,
    `exp`, `floor`, `log`, `log2`, `max`, `min`, `rand`, `sin`, `sqrt`, `tan`, `neg` of a float. Neither are `sub`,
    `div`, `mod`, `pow`, `min` and `max` on vectors, nor `toint2` to `toint4`.
  - **Scenario.** If `log` were log10, or a vector `sub` weren't componentwise, an expression would compile cleanly
    and compute a wrong value.
  - **Fix.** A cell for each in `computed`, with asymmetric constants against Python's value, such as `sqrt` of 0.25,
    `sin` of π/6, `floor` and `ceil` of -0.3, `min` and `max` with the larger value second, a float2 `sub` and `div`,
    and `dot` of (0.2, 0.5) and (0.5, 0.4). GUIDE.md lists what is measured. `rand` is checked only for its range.
  - **Resolution: done**.
    - **Test:** cells in the `computed` part, written first with Python's values. The scratch run failed 31 checks
      ("no line") before the script had them.
    - **Fix:** with the cells, every one matched Python:
      - `abs`, `sqrt`, `sin`, `cos` and `tan` in radians, `exp`, `log` (natural: 1.5 gives 0.40, where log10 gives
        0.18) and `log2`;
      - `floor` and `ceil` of -0.3, `neg` of a float, `min` and `max` with the larger second, `dot`;
      - `sub`, `div`, `mod`, `pow`, `min` and `max` of two float2, and `toint2` to `toint4`;
      - `rand` within its range.

      GUIDE.md lists what is measured.

- [x] **TST-706 · Two int cells carry a 0 where a missing component also gives 0** · `tests/test_all_tools/functions/designer_scripts/function_nodes.py:606`, `:615`, `tests/test_all_tools/functions/checks.py:274`, `:278` · confirmed · follows TST-700, generation 2 · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** The `ivector4` cell joins (1, 2) and (3, 0), and the `iswizzle4` cell reads index 3 of (1, 2, 3, 0).
    A missing or dropped component also computes 0 (GUIDE.md), so a wrong order or a dropped input passes.
  - **Scenario.** `int4(i2, j2)` drops its last component, and the check still passes.
  - **Fix.** A distinct non-zero fourth component, with the divisor raised (such as 8) so no value reaches 1.
  - **Resolution: done**.
    - **Test:** the `ivector4` and `iswizzle4` cells use (1, 2, 3, 5) over 10. They failed first ("no line"), then
      passed at 0.10 0.20 0.30 0.50 and 0.50 0.30 0.20 0.10.

- [x] **TST-707 · Cells that expect `false` can't tell it from a node that computes nothing** · `tests/test_all_tools/functions/designer_scripts/function_nodes.py:653-664`, `tests/test_all_tools/functions/checks.py:305`, `:307`, `:315` · confirmed · follows TST-700, generation 2 · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** A condition is read as `ifelse(condition, 1, 0)`, and an unconnected or failed condition also reads 0.
    `lr` of the ints -1 and 1, `not true` and `and true, false` have no true twin on the same node. `noteq` has only a
    true cell.
  - **Scenario.** A node whose condition never computes passes as false. GUIDE's "`lr` of -1 and 1 is false" rests on
    such a cell.
  - **Fix.** The twins: `lr` of the ints 1 and 2 (true), `not false`, `and true, true`, and `noteq` 0.7 and 0.7
    (false).
  - **Resolution: done**.
    - **Test:** the twins `lr` of the ints 1 and 2, `not false`, `and true, true`, and `noteq` 0.7 and 0.7. They
      failed first ("no line"), then passed.

- [x] **TST-708 · The unsigned-int sentences say more than the six cells measure** · `mcp_server/GUIDE.md:304-306`, `tests/test_all_tools/functions/checks.py:311-313`, `mcp_server/function_compiler.py:21`, `:188` · confirmed · follows TST-700, generation 2 · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** "ints act as unsigned" is a model two of its cells contradict: `neg` of 3 gives 0 and `toint1` of a
    negative gives 0, where wrapping would give a huge value. No cell has an int result that goes negative, yet GUIDE
    says a negative int computes a wrong value. A comment says -7 "reads back huge", where the cell shows only 5 or
    more. "(measured on macOS)" names no CPU.
  - **Scenario.** An agent reasons from "unsigned" and predicts values Designer doesn't give.
  - **Fix.** Say what the six cells show: a negative int computes a wrong value, as in these cases, measured on macOS
    arm64. The compiler's messages and docstrings say "Designer computes negative ints wrongly" instead of "as
    unsigned". Optionally add a `sub` of the ints 2 and 5 cell.
  - **Resolution: done**.
    - **Test:** the unit tests' expected messages say "which Designer computes wrongly", and failed 7 times on "as
      unsigned". A cell for the int `sub` of 2 and 5 was written first with Python's 0.20, failed on 1.00, and holds
      Designer's 1.00: a negative result computed wrongly as the function runs.
    - **Fix:** the messages, the module docstring, the check's comment and GUIDE.md say a negative int computes a
      wrong value, measured on macOS arm64, and list the cells. `WRONGLY` replaces `UNSIGNED`, and the 4294967289 note
      is gone.

- [x] **TST-709 · The `functions` category's time in `CATEGORIES` is Step 1's** · `tests/test_all_tools/categories.py:50` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** "6 s (2026-11-21, a scratch run)" was measured in Step 1. Since then the category has gained the
    `atan2`, `variables` and `computed` parts, 42 more Pixel Processors. `CATEGORIES` is ordered slowest first by these
    figures.
  - **Scenario.** The pool starts the category later than its time warrants.
  - **Fix.** Measure it in a scratch run after TST-705 to TST-707, and update the figure and its place.
  - **Resolution: done**.
    - **Test:** four timed scratch runs of `functions.run`: 10.0, 10.3, 10.3 and 10.3 s, the checks alone.
    - **Fix:** `CATEGORIES` says "10 s (2026-11-21, two scratch runs)", between `example` (10 s) and `measure`
      (9 s).

- [x] **TST-710 · `compiled()` doesn't check a constant's shape, and negative literals in float contexts are untested** · `tests/unit/test_function_compiler.py:30-31`, `:36-55`, `:105` · confirmed · follows TST-704, generation 2 · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** `compiled()` checks only that a constant exists where the definition has a `__constant__`, not its
    size or kind against the table. `tree()` prints a 1-tuple like a scalar, so a `swizzle1` emitting `(0,)` passes.
    Only `-2` alone tests a negative literal in a float context. `$pos * -1`, `float2(-1, 2)`, `1 if b else -1` and
    `abs(-3)` aren't tested.
  - **Scenario.** A constant of the wrong shape reaches Step 3's build, or the negative-int refusal reaches a float
    context, and no unit test fails.
  - **Fix.** In `compiled()`, assert a constant's size and kind against the table's `__constant__` type. Add a few
    negative literals in float contexts that must compile.
  - **Resolution: done**.
    - **Test:** `compiled()` checks each constant's shape against the table's `__constant__` type, through a `shape()`
      of its own. A scratch mutation making `swizzle1` emit `(0,)` failed it. `$pos * -1`, `float2(-1, 2)`,
      `1 if b else -1` and `abs(-3)` must compile. They passed before any change, as coverage.

- [x] **SRV-190 · "write a whole number" misleads for a whole float literal** · `mcp_server/function_compiler.py:624-629`, `tests/unit/test_function_compiler.py:408-409` · confirmed · follows SRV-188, generation 2 · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** `int2(1.0, 2.0)` or `int(2.0)` says "`1.0` must be an int here: write a whole number", though 1.0 is
    one. The refusal is about the written form.
  - **Scenario.** An agent retries the same text, or takes it for a bug.
  - **Fix.** Write "write it without a decimal point, such as `2`".
  - **Resolution: done**.
    - **Test:** `int(2.0)`, `int2(1.0, 2.0)`, `int(2.5)` and `int2(1.5, 2)` failed on "write a whole number".
    - **Fix:** "write it without a decimal point, such as `2`".
    - **Also covered:** `/simplify` found that this hint raised `OverflowError` on `int(1e999)`, and suggested `-2`
      for `int(-2.5)`, which is refused next. Tests for both failed first. Both now say "compute it in floats".

- [x] **HLP-226 · Parts of the build run outside the `try` whose rollback leaves the old function** · `mcp_server/designer_helpers/functions.py:143-147`, `:164-165` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** `newPropertyGraph` has made the graph, and reset the stored value, before `old = _nodes(fg)` and
    `function['nodes']` run outside the `try`. The old nodes are deleted after the `try`, so a failure there leaves
    the new function with old nodes left over, reported as a failed build.
  - **Scenario.** A key mismatch between the server's and the helper's `function`, or a failing delete, leaves the
    user's graph half changed, against the module docstring's promise.
  - **Fix.** Read `function['nodes']` and `function['output']` before `newPropertyGraph`, and put `_nodes(fg)` inside
    the `try`. Say in the docstring what a failure after the output's move leaves, or delete the old nodes inside the
    `try`.
  - **Resolution: done**.
    - **Test:** two unit tests failed: `newPropertyGraph` ran before a missing field was read, and nothing was rolled
      back when `getNodes` raised.
    - **Fix:** `nodes` and `output` are read first, and `newPropertyGraph` and `_nodes(fg)` run inside the `try`. The
      module docstring says what a failure while deleting the old nodes leaves.

- [x] **HLP-227 · `_take_back_function`'s docstring is untrue for `expose_param`** · `mcp_server/designer_helpers/graph_inputs.py:258-274` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** It says `existing` is None when the build "took an empty one that drove nothing: that graph is
    deleted". `expose_param` passes `getPropertyGraph`'s raw value, so an empty graph it reused isn't None there,
    and only the added node is deleted. Only `set_function` maps an empty graph to None.
  - **Scenario.** A reader changes one caller trusting the docstring, and the other's rollback changes.
  - **Fix.** Say that each caller decides what `existing` is, naming both, or pass the same thing from both.
  - **Resolution: done**.
    - **Fix:** a docstring only, saying what each caller passes as `existing`.

- [x] **HLP-228 · Types say less than is known, across the helper and the server** · `mcp_server/designer_helpers/functions.py:53`, `:71`, `mcp_server/server_tools/functions.py:12`, `tests/unit/test_set_function.py` · confirmed · found 2026-11-21 by two reviewers (Sonnet)
  - **Defect.**
    - The helper's `_Target.kind` is a `str`, where the server's is `Literal['perpixel', 'function', 'parameter']`;
    - `_FunctionNode.constant` copies the compiler's `Constant` union by hand;
    - the test that keeps the two sides in step compares key names only;
    - the server imports the compiler's private `_a`.
  - **Scenario.** A drift in a value's type, or in `_a`, goes unseen (`.claude/rules/python.md`, the most specific
    type).
  - **Fix.** `kind` as a `Literal`, the test comparing the annotations' values too, and `_a` made public or written
    locally.
  - **Resolution: done**.
    - **Test:** a comparison of the two sides' annotation values, and a check that the server imports no private name
      from the compiler. Both failed first.
    - **Fix:** the helper's `kind` is a `Literal`, and the compiler's `_a` and `_converted` are public, as
      `with_article` and `converted`.
  - Questioned by TST-721 (2026-11-22).

- [x] **HLP-229 · The build's re-check doesn't compare the graph** · `mcp_server/designer_helpers/functions.py:137-142` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** With `graph=None`, the read and the build each take the editor's current graph. The re-check compares
    the node, the parameter and the types, not which graph.
  - **Scenario.** The user switches to a duplicate of the graph (same node ids) between the two calls, and the
    function is built there.
  - **Fix.** The read prints the graph's identifier in the target, and the re-check compares it.
  - **Resolution: done**.
    - **Test:** a unit test with a `FakeGraph` failed (`KeyError: 'graph'`).
    - **Fix:** the target carries the graph and its package, so the re-check refuses another graph.

- [x] **HLP-230 · Refusals of a driven parameter don't know `set_function`** · `mcp_server/designer_helpers/edits.py:177`, `mcp_server/designer_helpers/sweep.py:50-51`, `mcp_server/server_tools/edits.py:97`, `mcp_server/GUIDE.md:246-251` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** `set` says a parameter "is driven by a function; set that instead (a set op on node 'graph')", OPS says
    "set the graph input instead", and `sweep_param` says "sweep the graph input instead". For a function, which
    `set_function` now makes, none of these can be followed. GUIDE's table says the tools refuse a parameter with a
    function, and `set_function` replaces one.
  - **Scenario.** An agent builds a function with `set_function`, then tries `set` on it, and is told to do something
    impossible.
  - **Fix.** Where the driver isn't a plain graph input, the messages and the OPS sentence say "or replace the
    function with `set_function`". GUIDE's two table rows add that `set_function` replaces it.
  - **Resolution: done**.
    - **Test:** the `inputs` checks of `set`, `expose`, `sweep_param`, a function with no output node, a function
      reading a non-input name, and `remove_graph_input` require `set_function` in the message, and a new one covers
      `set` on a function: 19 failed. The plain graph-input case asserts `set_function` is not named.
    - **Fix:** five messages, in `edits.py`, `sweep.py` and `graph_inputs.py`, the OPS sentence and GUIDE's two table
      rows. Behaviour is unchanged.
  - Questioned by HLP-231 and TST-720 (2026-11-22).

- [x] **SRV-191 · The grammar description doesn't say what `$pos`, `$size` and `$sizelog2` hold** · `mcp_server/server_tools/functions.py:17-31` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** `expression`'s description lists the variables and their types only. Their meaning is measured, but
    it is in GUIDE.md's `# Scripting`, which an agent using the tool doesn't read.
  - **Scenario.** An agent assumes `$pos.y` is 0 at the bottom and gets the image flipped.
  - **Fix.** One clause: `$pos` is the pixel's centre over the size, y 0 at the top row; `$size` in pixels;
    `$sizelog2` its log2.
  - **Resolution: done**.
    - **Fix:** `expression`'s description says what `$pos` (the pixel's centre over the size, y from the top row),
      `$size` (in pixels) and `$sizelog2` hold, as `check_system_variables` measures.

- [x] **SRV-192 · A parameter's type refusal doesn't name the fix, and refuses `'1'` on an int parameter** · `mcp_server/server_tools/functions.py` (`_refusal`) · measured · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** The last branch says "<node>.<param> takes a float4, and the expression gives a float". The compiler's
    own mismatches, and the float3 refusal, name the cast. The runner measured `set_function('1', lv, '$format')`:
    refused, "takes an int ... and the expression gives a float. Nothing was built", without saying to write
    `int(1)`.
  - **Scenario.** An agent gives an int or enum parameter a number and is refused without the way on.
  - **Fix.** Name the form to write, from the compiler's hints: `int(...)` for an int, `float4(x, x, x, x)` or a
    swizzle for a vector.
  - **Resolution: done**.
    - **Test:** four unit tests failed.
    - **Fix:** the refusal names the form to write through the compiler's `converted`: `int(c)`, `float4(c, c, c, c)`
      or `c.x`. A guard keeps `converted` from turning a vector into a larger one.

- [x] **TST-711 · README says the expression is checked "before anything reaches Designer"** · `README.md:48` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** `set_function` reads the target from Designer first. The tool's docstring and the guide say "before
    anything is built".
  - **Fix.** "before anything is built".
  - **Resolution: done**.
    - **Fix:** "before anything is built".

- [x] **TST-712 · The undo check covers a first build, not a replacement** · `tests/test_all_tools/undo/checks.py:102-123`, `tests/test_all_tools/undo/edit_menu.py:65-67` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** The step says the tool replaces the function in one undo step. The check gives a function-less Pixel
    Processor its first function. It never covers the old nodes' deletion and the output node's move. Its
    `describe_graph` line is the same for the old function and the new one.
  - **Scenario.** An Undo that reverted only part of a replacement would pass.
  - **Fix.** Replace a function, Undo once, and read the function's node count and output: the first function's.
    Redo gives the second's.
  - **Resolution: done**.
    - **Test:** the undo check builds `$time` (one get node), replaces it with `float4($pos, 0, 1)`, and one Undo must
      bring back the function reading `$time`. `edit_menu.perpixel_driver` reads which function is there. Redo brings
      the second back.

- [x] **TST-713 · The new undo check has no unit test** · `tests/unit/test_selftest_undo.py` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** Every other undo check is in the parametrized tests: why a check fails, the pass path, a failed read,
    and no Qt events (TST-641, TST-661). `check_one_undo_reverts_a_set_function` is in none.
  - **Scenario.** A change that makes it pass when the Undo removed the node instead of the function goes unseen.
  - **Fix.** Add it to the four parametrizations, with a case where the node is gone, which must fail.
  - **Resolution: done**.
    - **Test:** the undo check is in the four parametrizations, with a pass path and three cases that must fail: the
      node gone, the new function left, no function. They failed on the old check.

- [x] **TST-714 · The `colorswitch`-off result lines have no live check** · `mcp_server/server_tools/functions.py:59-64`, `tests/test_all_tools/functions/checks.py:371-397` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** Every live check runs with `colorswitch` on. The two "off" lines, and the tool's read of
    `colorswitch` in that state, are never seen through the tool.
  - **Fix.** One Pixel Processor with `colorswitch` off: a float4 (0.2, 0.4, 0.6, 0.8) reads 0.4, and the line says
    off.
  - **Resolution: done**.
    - **Test:** `check_set_function_with_colorswitch_off`: 0.5 reads 0.5, and the float4 (0.2, 0.4, 0.6, 0.8) reads 0.4,
      both result lines checked. Seen failing on a mutation that read `colorswitch` as on.

- [x] **TST-715 · "Keeps the node's connections and other parameters" is read on one node** · `tests/test_all_tools/functions/checks.py:400-415` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** The check reads the Pixel Processor's output connection and `$randomseed` only. An Absolute
    `$outputsize`, which GUIDE lists, isn't read, and no parameter's or Value Processor's function is replaced.
  - **Fix.** Give the Pixel Processor an Absolute `$outputsize` and read it after. Replace the levels node's function a
    second time and read its connection and another parameter.
  - **Resolution: done**.
    - **Test:** the graph is 16 px, and the Pixel Processor Absolute at 8 px. The check reads its connection,
      `$randomseed`, `$outputsize` and its size (8x8), and the levels node's input and `levelinhigh`. Seen failing on a
      mutation without the Absolute size (16x16).

- [x] **TST-716 · The refusal checks miss a case and can't tell one from another** · `tests/test_all_tools/functions/checks.py:455-494` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.**
    - The "parameters of type ... cannot take a function" refusal (no getter) has no case;
    - the connector case gets the message a missing parameter gets, so it can't tell which it reached;
    - one before-and-after compare covers all eight refusals, and its detail doesn't name the refusal.
  - **Fix.** A no-getter case, a connector case whose result tells it apart (or a name saying it can't), and a
    compare per refusal.
  - **Resolution: done**.
    - **Test:** a no-getter case (a curve's `curveluminance`). The connector case failed before its message was
      changed. Each refusal is compared with its own read: `describe_graph` for a refusal in Designer, the node's
      pixels for the server's.
    - **Fix:** the connector refusal says the id "is an input connector of node ..., not a parameter".
  - Questioned by TST-722 (2026-11-22).

- [x] **TST-717 · The preparation relies on the uniform's default colour** · `tests/test_all_tools/functions/preparations.py:21` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** The `black` uniform sets no `outputcolor`, and the levels check's values depend on it being black.
  - **Fix.** `'params': {'outputcolor': [0, 0, 0, 1]}`.
  - **Resolution: done**.
    - **Fix:** the black uniform sets `outputcolor` [0, 0, 0, 1].

- [x] **TST-718 · `undo`'s time in `CATEGORIES` is stale** · `tests/test_all_tools/categories.py:60` · confirmed · found 2026-11-21 by a reviewer (Sonnet)
  - **Defect.** "1 s" predates the two sends and the Redo this step added. `undo` runs alone, last, so its time adds
    to the run.
  - **Fix.** Time `undo.run` in a scratch run and update the figure.
  - **Resolution: done**.
    - **Fix:** `undo` is 5 s (a 6.3 s scratch run, 1.5 s of it an empty run's).

- [x] **HLP-231 · The messages that offer `set_function` say it four ways, and one offers it where it can't reach** · `mcp_server/designer_helpers/graph_inputs.py:109-113`, `:172`, `:208-213`, `:482-483`, `mcp_server/designer_helpers/edits.py:197-198`, `mcp_server/designer_helpers/sweep.py:59` · confirmed · follows HLP-230, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.**
    - `remove_graph_input` offers `set_function` for every function reading the input, including an FX-Map's inner
      function and the graph's own parameter's, which `set_function` can't reach;
    - the messages say "replace it", "replace the function", "edit the function" and "edit those", and the tool only
      replaces;
    - `expose`'s message now names `set_function` for a plain binding too, the case HLP-230 meant to leave as it was.
  - **Scenario.** An agent told to fix an FX-Map's function with `set_function` can't. Another reads "edit" and
    expects the function's other nodes to survive.
  - **Fix.** One wording, "replace the function with `set_function`", from one small helper beside `_driver_text`.
    It is offered only for a plain `node.param` function, and `expose`'s plain-binding case stays as it was.
  - **Resolution: done**.
    - **Test:** the `inputs` checks require "replace the function with set_function" in the `set`, `expose`, `sweep`,
      no-output-node, no-input and `remove_graph_input` refusals, and require no `set_function` for three cases:
      `expose` on a parameter bound to a graph input, and `remove_graph_input` while an FX-Map's function or the
      graph's own parameter's function reads the input. 21 failed first.
    - **Fix:** `_REPLACE`, the one wording, beside `_driver_text`. `_replacing(*refs)` gives it to
      `remove_graph_input` only when `set_function` reaches every ref. `expose`'s plain-binding case is back as it
      was.

- [x] **SRV-193 · A float3 given to a colour or float4 parameter is refused without a hint** · `mcp_server/server_tools/functions.py` (`_refusal`) · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** SRV-192's guard keeps `converted` from widening a float3 into a float4, so the parameter refusal names
    no fix. The Pixel Processor's float3 refusal names `float4(c, 1)`.
  - **Scenario.** `float3(1, 0, 0)` on a uniform's `outputcolor` is refused, and the agent isn't told to write
    `float4(c, 1)`.
  - **Fix.** The same `float4(c, 1)` hint for a float3 where a float4 is taken.
  - **Resolution: done**.
    - **Test:** a unit case, a float3 for a colour, failed.
    - **Fix:** `_refusal` names `float4(c, 1)` for a float3 where a float4 is taken.

- [x] **SRV-194 · The tool says a `$` parameter is made Absolute "so that its function takes effect", measured for two** · `mcp_server/server_tools/functions.py:135`, `mcp_server/designer_helpers/edits.py:73-88` · confirmed · follows HLP-225, generation 2 · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** `check_a_function_on_a_dollar_parameter` measures `$outputsize` and `$format` only. `_made_absolute`
    also switches `$pixelsize`, `$pixelratio` and `$tiling`, where no check shows a function is ignored while
    inherited, or kept once Absolute.
  - **Scenario.** An agent trusts the reason given for the other three. If a function works there inherited, the node
    is detached from its parent for nothing.
  - **Fix.** Narrow the docstring (generation 2): the reason is measured for `$outputsize` and `$format`, and the
    others are made Absolute as `set` makes them.
  - **Resolution: done**.
    - **Test:** the result line's two unit cases failed first.
    - **Fix:** the tool's, `_made_absolute`'s and the helper module's docstrings give the reason (an offset, or
      ignored, while inherited) for `$outputsize` and `$format` only. The others are made Absolute as `set` makes
      them, and the result line says "is Absolute now, as apply_edits' set makes it".

- [x] **TST-720 · GUIDE says `set_function` replaces a function with no output node, which no check runs** · `mcp_server/GUIDE.md:250` · confirmed · follows HLP-230, generation 2 · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** The function-state table's row "Nodes, no output node" now says `set_function` replaces it. The
    `inputs` checks only look for the word in the refusals, and no unit test gives `_driving_graph` such a graph.
  - **Scenario.** The table tells an agent the refusals' alternative works there, and nothing has run it.
  - **Fix.** In `inputs`, where the stub exists: `set_function` on the stub's parameter, then its driver and the
    function's node count read back. Or narrow the row.
  - **Resolution: done**.
    - **Test:** in `inputs`, `set_function` on the stub's `levelouthigh`, then `STUB_NODES=3` and
      `levelouthigh <- a function` read back. It passed on the code as it was, so it was seen failing on a mutation
      that kept the old nodes (4).

- [x] **TST-721 · `test_set_function.py`'s target is typed `dict[str, Json]`** · `tests/unit/test_set_function.py:22`, `:31`, `:77`, `:124`, `:223`, `:245`, `:410` · confirmed · follows HLP-228, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `target()`, changed in this diff, and the helpers and tests that take it use `dict[str, Json]` where
    the server's `_Target` fits, which forces casts such as `str(read['parameter'])`.
  - **Fix.** Type them with `_Target`, and `INPUTS` with `_Typed` (`.claude/rules/python.md`).
  - **Resolution: done**.
    - **Fix:** `target()`, `INPUTS` and the tests' helpers are typed with the server's `_Target` and `_Typed`. Typing
      only; mypy strict passes.

- [x] **TST-722 · A refusal's pixel compare passes if its baseline read failed** · `tests/test_all_tools/functions/checks.py:584`, `:607`, `tests/test_all_tools/functions/results.py:45-47` · confirmed · follows TST-716, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `all_near(got, want)` is True for an empty `want`. A baseline `node_stats` that returned an error gives
    `{}`, and every later compare passes.
  - **Fix.** `all_near` is False for an empty `want`, or the baselines are checked for their points once.
  - **Resolution: done**.
    - **Test:** `tests/unit/test_selftest_functions.py`, which failed for an empty `want`.
    - **Fix:** `all_near` is False when nothing is wanted.

- [x] **TST-723 · `measure_dollar` rebuilds the compute-and-print loop `computed()` gives** · `tests/test_all_tools/functions/designer_scripts/function_nodes.py:715-741`, `:191`, `:196-199` · confirmed · follows HLP-225, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** The new part copies `computed(g, cells, read)`'s loop and `format_and_pixel`'s format read, against
    the user's instruction to reuse, not copy.
  - **Fix.** A `Cells` list and a `read` through `computed()`, and a small `pixel_format(n)` beside
    `format_and_pixel`.
  - **Resolution: done**.
    - **Fix:** `measure_dollar` goes through `computed(g, cells, read)`, and `pixel_format()` serves it and
      `format_and_pixel`. The facts check printed the same 4 lines before and after.

- [x] **TST-725 · No check that one Undo reverts a connect into a new `#name`** · `mcp_server/designer_helpers/edits.py:398`, `tests/test_all_tools/undo/checks.py` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** The connect now calls `newProperty`. No undo check covers a made property, so "Ctrl+Z on this graph
    reverts the whole batch" is unmeasured for it.
  - **Scenario.** If Undo removes the connection and keeps `#v`, `set_function` still reads `#v`, unconnected.
  - **Fix.** An undo check: connect a Value Processor into a fresh `#name`, one Undo, then read back that the link
    and `#name` are gone (or say in GUIDE that `#name` stays). Then Redo.
  - **Resolution: done**.
    - **Test:** `check_one_undo_reverts_a_connect_into_a_new_input_value` in `undo`. It reads the node's input values
      through `set_function`'s refusal of a missing `#name`, a read with no undo step of its own. One Undo removes the
      connection and the `#u` it made, and Redo brings both back. It passed at once, and GUIDE.md records it.
  - Questioned by TST-731 (2026-11-22).

- [x] **TST-726 · GUIDE's Input values bullet says more than its checks** · `mcp_server/GUIDE.md:340-353`, `tests/test_all_tools/functions/checks.py:~419` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.**
    - "made `opacitymult` 1, its default": 1 is also its maximum, so a clamped wrong value reads the same;
    - "a float `#x` read with `get_float2` gave neither its value nor zeros": the expected pixel has alpha 0, where
      its label says "(x, y, 0, 1)";
    - "a name the node lacks reads 0" is measured in a Pixel Processor only;
    - "`savePackageAs`, as `save_package` saves": `save_package` without a path calls `savePackage`.
  - **Fix.** Narrow each to what is measured, and fix the label.
  - **Resolution: done**.
    - **Fix:** GUIDE.md narrowed: a mismatch makes `opacitymult` "compute 1, not the value"; the `get_float2` case
      gives the measured (0, 1, 0, 0), and its label says "in a vector4 with (0, 1)"; a missing name reads 0 in a
      Pixel Processor; the save is `savePackageAs`, "what `save_package` calls given a path".

- [x] **TST-727 · Two helpers this step added are rebuilt beside them** · `tests/test_all_tools/functions/checks.py:527`, `:621`, `tests/test_all_tools/functions/designer_scripts/function_nodes.py:378-379`, `:773-779` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `checks.py:527` and `:621` rebuild `describe_graph` inline where `described(ctx, [...])` does it,
    and the local name shadows the import. `measure_processors` builds its Value Processor where
    `value_processor()` would, against the user's instruction to reuse.
  - **Fix.** Call `described()` and `value_processor()`.
  - **Resolution: done**.
    - **Fix:** `described()` replaces the two rebuilt reads, and the shadowing local is renamed.
      `value_processor()` sets an output node that `measure_processors`' cell must not have, so the shared step is
      `function_graph()`, used by all five places that made a function graph.
  - Questioned by TST-732 (2026-11-22).

- [x] **TST-728 · The reload's lines crash instead of printing when the fact fails** · `tests/test_all_tools/functions/designer_scripts/function_nodes.py:879-905` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** If the reload loses `#x`, `prop()` gives None and `listing` raises, so the check fails as "no line"
    rather than on the fact. Nor does the script show the reload re-read the file: a kept package would give the
    same lines.
  - **Fix.** Guard None and print the fact. Change the Value Processor after the save without saving, then read the
    saved value after the reload.
  - **Resolution: done**.
    - **Fix:** `reloaded` prints one "lost" line instead of raising when the blend, its `#x` or the processor's
      constant is missing. After the save, the constant becomes 0.3 unsaved, so the 0.75 read after the reload shows
      the file was read. The guard is shown by reading: no lost part was reproduced.

- [x] **TST-729 · The preparation's `vout` is read by no check** · `tests/test_all_tools/functions/preparations.py:3`, `:20-21` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** The Value Processor's output node served the removed `VALUE_OF` read. The preparation holds the
    minimum its checks read (the `live-check` skill).
  - **Fix.** Drop `vout`, its connection and its docstring line.
  - **Resolution: done**.
    - **Fix:** `vout`, its connection and its docstring line are gone.

- [x] **SRV-195 · The drive refusal's remedy doesn't lift it, and one docstring sentence misleads** · `mcp_server/server_tools/functions.py:155-166`, `:196` · confirmed · follows HLP-232, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** A Value Processor that drives a float `#p` and is given a float2 is told "give a float, or connect the
    processor into another #name". Connecting it into `#q` makes `#q` a float too, while `#p` is still driven, so the
    refusal comes back. Only a `disconnect` lifts it, and nothing says so. The tool's docstring says a Value
    Processor's output takes "the type of the input values it drives", which reads as a conversion the tool doesn't
    make.
  - **Scenario.** An agent following the message loops.
  - **Fix.** The drive refusal names the disconnect (`apply_edits`' disconnect of `<node>.#name`), or the type to
    give. The tool text says to give a processor its function before connecting it. The docstring says a processor
    that drives input values must give their type.
  - **Resolution: done**.
    - **Test:** the unit expectation of the drive refusal naming the disconnect failed first. A live check gives
      `pair` a float4 after the named disconnect, and it builds: the remedy lifts the refusal.
    - **Fix:** the refusal ends "give a float, or disconnect 12.#v first (an apply_edits disconnect op on node '12',
      input '#v')". The docstring says a Value Processor that drives input values must give their type, and to give
      it its function before connecting it.

- [x] **SRV-196 · "It reads 0" is measured by results a function not evaluated also gives** · `mcp_server/server_tools/functions.py:170-177`, `mcp_server/GUIDE.md:348-349`, `:360`, `tests/test_all_tools/functions/checks.py:430-436` · confirmed · follows HLP-232, generation 2 · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** The four measured lines read black in a Pixel Processor and 0.00 in a Value Processor. A Pixel
    Processor whose function gives no usable result computes black too, and a fresh Value Processor holds 0. So the
    measurement can't tell a getter reading 0 from a function dropped, and `opacitymult` reading the same unconnected
    `#u` computes 1, its default, not 0. Only a float `#name` is measured, and a Value Processor only when never
    connected.
  - **Scenario.** An agent told "it reads 0" writes `1 - #u` in a processor and expects 1.
  - **Fix.** Narrow the result line, the docstring and GUIDE to "has nothing connected: the function computes no
    value from it". Or measure it, with `#u + 0.5` cells (0.5 if it reads 0) and keep whichever holds.
  - **Resolution: done**.
    - **Test:** `+ 0.5` cells in `check_input_values`, read 0.5 each: a Pixel Processor reading `#nope`, `#u` never
      connected and `#e` after a disconnect, and a Value Processor reading `#u` never connected and `#e` after a
      disconnect. A float `#name` with nothing connected does read 0. A unit test failed first: the line claimed "it
      reads 0" for a float2.
    - **Fix:** the line says "it reads 0." for a float `#name` only, and "connect a value into it first" for another
      type. GUIDE.md gives the evidence and says other types aren't measured.
    - **Also covered:** the parameter's refusal claimed "computes no value" for every type. It now says only that
      nothing is connected, and how to connect.

- [x] **TST-730 · Two unit tests can't see what their comments name** · `tests/unit/test_set_function.py:402`, `:117-165` · confirmed · follows HLP-232, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `assert read['drives'] == []` for a parameter would hold without the `kind == 'function'` guard: the
    fake's connections iterate as empty. And no test changes `fed` or `drives` to show the build's re-check covers
    them.
  - **Fix.** Give the parameter case a `#`-connected output, and add a re-check case changing `fed`.
  - **Resolution: done**.
    - **Test:** the fake gives every connector a `#`-connected end, so the parameter's `drives` would be non-empty
      without the guard. The re-check test is parametrized over `colorswitch`, `fed` and `drives`. Both pass: the code
      was right, and the tests now see what their comments name.

- [x] **TST-731 · The undo check's read of the input values gives `''` on a failed read** · `tests/test_all_tools/undo/edit_menu.py:70-75`, `tests/test_all_tools/undo/checks.py:52-53` · confirmed · follows TST-725, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `input_values` returns `''` when the reply has no "its input values are", so a failed read after the
    Undo passes "one Undo removes the #name it made". The module's docstring says a read that fails fails the check,
    the rule TST-652 and TST-655 set.
  - **Fix.** Return None unless the reply has one of the two known endings, and fail naming a read that matched
    neither. A unit case with an error reply.
  - **Resolution: done**.
    - **Test:** `test_the_input_value_check_fails_naming_a_read_of_the_values_that_failed`. Before the fix, an error
      reply after the Undo passed "one Undo removes the #name it made".
    - **Fix:** `input_values` returns the names listed, `''` for "nor any other", or "a read failed: <reply>", which
      the three checks pass as their detail.

- [x] **TST-732 · TST-727's pattern is left in two places** · `tests/test_all_tools/functions/designer_scripts/function_nodes.py:441-446`, `tests/test_all_tools/functions/checks.py:491-497` · confirmed · follows TST-727, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `replaced_graph` makes a function graph without `function_graph()`, and
    `check_set_function_keeps_the_nodes_connections_and_parameters` has a local `described` that shadows the import
    and rebuilds its read.
  - **Fix.** Call `function_graph(pp, 'perpixel')` and `described(ctx, [...])`.
  - **Resolution: done**.
    - **Fix:** `replaced_graph` calls `function_graph(pp, 'perpixel')`, and the keeps-connections check calls
      `described(ctx, nodes)`. A refactor: `functions` passed before and after.

- [x] **HLP-234 · A failed build's rollback puts the inputs back, not the callers' connections** · `mcp_server/designer_helpers/functions.py:5-9`, `:14-17`, `:422-458` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `_set_inputs` runs before the nodes are built. A failure after it deletes `k` remakes `k` with no
    connection, while the docstrings say a failure leaves the old function as it was. `take_back` swallows every
    exception, so an input of a type `_new_type` lacks raises `KeyError` there and leaves the inputs half restored.
  - **Fix.** Set the inputs after the output node moves (the body's `get_*` nodes name inputs by string), or narrow
    the docstrings to what the rollback restores.
  - **Resolution: done**.
    - **Test:** `test_the_inputs_are_set_once_the_output_node_moved` and
      `test_a_failed_build_leaves_..._as_they_were` failed first.
    - **Fix:** the inputs are set after `_built_beside`, so a failed build leaves them as they were, and the rollback
      no longer restores them. The docstrings say what a failure after the output node moves leaves.
  - Questioned by HLP-238 (2026-11-22).

- [x] **HLP-235 · A function graph's input ids aren't read back after they are made** · `mcp_server/designer_helpers/functions.py:403-414`, `:443-444` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** The identifier is checked after creation, the inputs not: `newProperty`'s result is dropped. If
    Designer renamed an id (`Uv`, `_k`, `k_` are unmeasured), the body would read an input that doesn't exist, 0.
  - **Fix.** Read the inputs back after `_set_inputs`, and refuse with the rollback if they differ.
  - **Resolution: done**.
    A defensive change: every id tried was kept as given (TST-733's cells).
    - **Test:** the "an input renamed" cases failed: nothing was raised.
    - **Fix:** `_set_inputs` reads the inputs back and raises if they differ, and a new function graph is deleted.

- [x] **HLP-236 · The callers note misses an FX-Map's functions** · `mcp_server/designer_helpers/functions.py:239-252` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `_callers` sweeps function graphs and nodes' parameter functions, not `_fx_map_functions`, which
    `_input_users` sweeps. A call from an FX-Map's inner function loses its connection unnamed.
  - **Fix.** Add `_fx_map_functions` to the sweep, or narrow "names what calls it".
  - **Resolution: done**.
    - **Test:** the read test failed, missing `G/9/3.opacity`.
    - **Fix:** `_callers` also sweeps `_fx_map_functions`.
  - Questioned by HLP-239 (2026-11-22).

- [x] **HLP-237 · One function graph that can't be read breaks `set_function` on every node of its package** · `mcp_server/designer_helpers/functions.py:192`, `:220-235` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `_target_of` reads every function graph of the package. `getTypes()` can return None (Designer's
    stub), and iterating it raises, so one such graph makes `set_function` fail on an unrelated Pixel Processor.
  - **Fix.** Treat a failed read, or None, as "no output of one type".
  - **Resolution: done**.
    - **Test:** `test_a_function_graph_whose_output_types_cant_be_read_reads_as_no_output` failed: a `TypeError` for
      None, an `APIException` for a raising read.
    - **Fix:** either reads as "no output of one type".

- [x] **SRV-197 · Messages in a function graph's expression still speak of input values** · `mcp_server/function_compiler.py:3`, `:238-242`, `:392-394`, `:405-406`, `:558-568`, `:603-615` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `#x = 1` in a function graph says "`#x` is an input value of the node", and a misplaced `#` speaks of
    input values: a function graph has none. "Unknown function" lists the graph being defined among what the
    package has. The arity message is written twice, and the module docstring names `compile_expression`'s old
    signature.
  - **Fix.** Function-graph wording when `defining` is set, the defined graph left out of the list, one arity
    message, and the docstring updated.
  - **Resolution: done**.
    - **Test:** three compiler cases failed: a bound `#x`, `f#x`, and the unknown-function list naming the graph
      being defined.
    - **Fix:** function-graph wording when `defining` is set, the graph being defined left out of the list, one
      `_arity` message, and the module docstring updated.

- [x] **SRV-198 · An agent can't give an existing function graph no inputs** · `mcp_server/server_tools/functions.py:255`, `:265` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `inputs={}` reads as "left out", so `paint(uv, k)` can't become `paint()`. The description doesn't
    say so, and why `{}` means left out (that a client sends `{}` for an empty field) is unmeasured.
  - **Fix.** Measure what Claude Code sends for an omitted optional dict. If it omits it, `{}` means none. Otherwise
    say how to get none.
  - **Resolution: done**.
    Documented: what Claude Code sends for an omitted dict couldn't be measured here, as its MCP log records tool
    names, not arguments.
    - **Fix:** the behaviour stays. The `inputs` description says that left out or `{}`, a function graph keeps the
      inputs it has, a new one gets none, and one with none is made under another identifier.

- [x] **TST-734 · Behaviours true by reading have no test** · `tests/unit/test_function_compiler.py:570-690`, `tests/unit/test_set_function.py`, `mcp_server/designer_helpers/functions.py:443` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** No test pins that an input named like a function graph doesn't shadow a call, that a diamond (A and B
    both calling C) isn't refused with `defining` set, the "it has no inputs" message, the "Designer named the
    function graph" guard, or a rollback after `newProperty` raises. The `package` fixture's fake getter
    (`'get_' + type_id`) isn't the real one.
  - **Fix.** A test each.
  - **Resolution: done**.
    - **Test:** tests for an input named like a function graph, a diamond of calls, "it has no inputs", the "Designer
      named" guard and a failed `newProperty`. They pass: true by reading, now guarded. The `package` fixture uses the
      real `_typed`, which showed the old fake's `get_float` should be `get_float1`.

- [x] **TST-735 · One undo step for a function graph is claimed and not checked** · `README.md` (Tools row), `mcp_server/server_tools/functions.py:1-4`, `:276`, `mcp_server/GUIDE.md:94` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** README, the module docstring and GUIDE say a call is one undo step. For `function=`, it makes a
    resource and changes its inputs, other objects than a node's function. Only the developer's scratch probe,
    uncommitted, shows one Undo reverts it.
  - **Fix.** An undo check in `undo`: a function graph made, one Undo, gone, Redo, back; then replaced with other
    inputs, one Undo, the old inputs and nodes.
  - **Resolution: done**.
    - **Test:** `check_one_undo_reverts_a_function_graph` in `undo`. It reads the function graph through
      `set_function`'s refusal of a call, which builds nothing (`edit_menu.function_graph`, `send` and `put_back`
      taking a reader). On a server mutated to build outside an undo group, both Undo lines failed. With the real
      code it passed, 7 checks, and in the whole `undo` category. Unit tests in `test_selftest_undo.py`.
  - Note (2026-11-22): the check records 6 lines, not 7 (Step 4's fixes' review).
  - Questioned by TST-740 and TST-741 (2026-11-22).

- [x] **TST-736 · The "package unchanged" compare passes if its baseline read failed** · `tests/test_all_tools/functions/checks.py:913`, `:953` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** Nothing checks `before` holds `FUNCTION_GRAPH` lines. A snippet that raises returns the same
    traceback every time, and all eight refusals pass (TST-722's pattern).
  - **Fix.** Check the baseline holds its lines before comparing.
  - **Resolution: done**.
    - **Test:** with `FUNCTION_GRAPHS` broken, the new baseline check fails and so do all eight refusals, which equal
      tracebacks would have passed.
    - **Fix:** the baseline must hold the `shade`, `wrap` and `RESOURCES` lines.

- [x] **TST-737 · A comment and a parameter say more than the code does** · `tests/test_all_tools/functions/checks.py:885-886`, `tests/test_all_tools/functions/results.py:29-35` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** The comment says the state read includes the package's modified state, which `FUNCTION_GRAPHS`
    never reads. `function_built`'s `functions` parameter is passed by no caller.
  - **Fix.** Drop both.
  - **Resolution: done**.
    - **Fix:** the comment no longer claims the modified state, and the unused parameter is gone.

- [x] **HLP-238 · The module docstring misdescribes a failure after the output node moves** · `mcp_server/designer_helpers/functions.py:8-9`, `:484-490` · confirmed · follows HLP-234, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** With the inputs set last, a failure while deleting the old nodes, or inside `_set_inputs`, leaves an
    existing function graph with the new body and its inputs as they were, or half set. The docstring says it
    leaves "the new function working", and the error the agent sees says neither.
  - **Fix.** Make the docstring say what is left. Optionally a clause in the read-back's error saying the new
    function stays.
  - **Resolution: done**.
    - **Fix:** the module docstring says what a failure after the output node moves leaves: while the old nodes are
      deleted, the inputs as they were; while the inputs are set, the new function with the inputs set so far, or a
      new function graph deleted. A failure in `_set_inputs` on an existing graph says "paint keeps its new function,
      and the inputs set so far", pinned by
      `test_an_input_not_made_leaves_an_existing_function_graph_with_its_new_function`.

- [x] **HLP-239 · Two messages still can't be followed or misname a function graph's input** · `mcp_server/designer_helpers/functions.py:246-260`, `mcp_server/server_tools/functions.py:~281-287`, `mcp_server/function_compiler.py:507` · confirmed · follows HLP-236, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** The callers note now names an FX-Map's inner functions (`G/9/3.opacity`) and says "give each its
    function again with set_function", which can't reach an FX-Map's inner node. `_input` still says "graph input"
    in a function graph's expression.
  - **Fix.** For an FX-Map's caller, say to edit it in Designer or tell the user. "an input" when `defining` is set.
  - **Resolution: done**.
    - **Test:** `test_a_call_from_an_fx_map_is_named_for_the_user_to_set_in_designer`, the read test and
      `test_a_function_graphs_input_no_function_reads_is_called_its_input` failed first.
    - **Fix:** `_callers` gives an FX-Map's inner callers apart (`fx_map_callers`), which the result names on a line
      of their own, for the user to set in Designer. `_input` says "input" in a function graph's expression.

- [x] **TST-738 · No live check drops a middle or first input through `set_function`** · `tests/test_all_tools/functions/checks.py:895-909` · confirmed · follows HLP-233, generation 2 · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** The only live drop is of the last input, where the old rule and the new keep the same. The new scan
    reads inputs after a sibling's deletion, which only a fake has run. GUIDE says the connections into the others
    stay, measured on the raw API for a middle deletion.
  - **Fix.** Through the tool: `paint(uv, k, x)` called with all three connected, `k` dropped, and the pixels still
    reading `uv` and `x`. Then the first input dropped too.
  - **Resolution: done**.
    - **Test:** `check_dropping_a_function_graphs_input_keeps_the_calls_connections_into_the_others`: `drop(a, b, c)`
      called with all three connected, then `b` dropped, then `a`. With the old prefix scan put back, the call lost
      its connection into `c` (0.0). With the current scan it passes: the scan works through the tool.

- [x] **TST-739 · Two of TST-733's facts pass on what a failed call also gives** · `tests/test_all_tools/functions/designer_scripts/function_nodes.py:1228-1240`, `tests/test_all_tools/functions/checks.py:539-541`, `mcp_server/GUIDE.md:382-385` · confirmed · follows TST-733, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** The unconnected float3 cell expects `0.00 0.00 0.00 1.00`, what a Pixel Processor gives for a result
    it can't show. And the calls from a Value Processor and a parameter's function call `half()`, with no input,
    while GUIDE says a call "computes `fn` with the values connected" there.
  - **Fix.** A marker in the float3 body, such as `+ 0.25`, and `half` given an input connected in both contexts. Or
    narrow the sentences.
  - **Resolution: done**.
    - **Test:** the float3 body is `v + 0.25`, read 0.25 each, and `half(x)` is `x * 0.5` with 0.6 connected in a
      Value Processor and in a blend's `opacitymult`, read 0.30. The old cells gave `0.00 0.00 0.00 1.00` and 0.50.
      GUIDE.md's sentence holds as it stands.

- [x] **TST-740 · The undo check of a function graph sees its inputs, not its nodes** · `tests/test_all_tools/undo/checks.py:174-209`, `tests/test_all_tools/undo/edit_menu.py:80-93` · confirmed · follows TST-735, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** The reader tells the inputs, "no output node" and "unknown function" apart, never the nodes. An Undo
    that put the inputs back and kept the new nodes would pass, while README and the docstrings say a whole call is
    one undo step.
  - **Fix.** After an Undo or Redo has landed, read the function graph's node count and output node too, as the
    refusals check's `FUNCTION_GRAPHS` snippet does. Or narrow the claims to what the check shows.
  - **Resolution: done**.
    - **Test:** the undo check reads the function graph's node count and output node after each landed Undo and Redo,
      with one code job after the landing (`edit_menu.function_graph_nodes`). On a server setting the inputs outside
      the build's undo step, the inputs line passed and the nodes line failed. Its unit test failed before the reads.
      GUIDE.md and the check's docstring say inputs and nodes.

- [x] **TST-741 · The undo unit test's function-graph case never reaches an Undo** · `tests/unit/test_selftest_undo.py:631-638` · confirmed · follows TST-735, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `test_no_check_runs_qts_events_or_reads_a_node_by_code`'s function-graph case builds the fake
    without `values`. The reader matches none of its states, the check fails at once and sends nothing, and the
    assertion holds trivially.
  - **Fix.** Build the fake with the function graph's states, as the other new tests do.
  - **Resolution: done**.
    - **Fix:** the function-graph case left the parametrized test, and
      `test_the_function_graph_check_reads_its_undo_and_redo_with_set_functions_refusal` pins it with the function
      graph's states: two Undos, two Redos, the nodes reads, and no Qt events.

- [x] **SRV-200 · A repeated `filter=` or `wrap=` adds its mode twice** · `mcp_server/function_compiler.py:727-740` · measured · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `_sample` adds `words[value]` for each keyword, and `ast.parse` accepts a keyword given twice
    (measured: `sample(0, p, filter='bilinear', filter='bilinear')` parses, its keywords `['filter', 'filter']`).
  - **Scenario.** `sample(0, $pos, filter='bilinear', filter='bilinear')` gives the mode 2: nearest and clamped,
    which the expression never asked for, with no error.
  - **Fix.** Refuse a keyword given twice, at its column.
  - **Resolution: done**.
    - **Test:** two rows in `test_each_mistake_in_a_sample_is_refused`, failing with "DID NOT RAISE".
    - **Cause:** `ast.parse` accepts a repeated keyword, and `_sample` added each one's mode.
    - **Fix:** `_sample` refuses a repeat at its column: "`filter='bilinear'` gives filter a second time: give
      filter= and wrap= once each".
    - **Also covered:** `sample` is the only call that takes keywords.

- [x] **HLP-240 · `connect` into `input:0` is told to connect a later input first** · `mcp_server/designer_helpers/edits.py:426` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `_later_image` matches `input:\d+`, so `input:0` and `input:01` count as a processor's later input
    images, which no processor lists: its inputs are `input`, `input:1`, `input:2`...
  - **Scenario.** `connect` into a Pixel Processor's `input:0` is refused with "connect an image into input:1
    first", which can never make `input:0` listed.
  - **Fix.** Match `input:[1-9]\d*`, with a unit test row for `input:0`.
  - **Resolution: done**.
    - **Test:** rows for `input:0` and `input:01` in `test_connect_names_the_input_image_to_connect_first`, which got
      the processor's sentence.
    - **Cause:** `_later_image` matched `input:\d+`.
    - **Fix:** it matches `input:[1-9]\d*`.
    - **Also covered:** `_image_inputs` (`edits.py`), the only other such pattern, changed the same way.

- [x] **TST-742 · GUIDE's sampling and input-image facts say more than their checks measure** · `mcp_server/GUIDE.md:404-406`, `:416-426`, `tests/test_all_tools/functions/checks.py:647` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.**
    - "A processor's input images" states each fact for "a Pixel or Value Processor", measured on a Pixel Processor
      only.
    - The mode's bits are measured at x -0.1, 0.3, 0.7 and 1.1 only, while the sentence covers both axes.
    - The comment at `checks.py:647` says "as no image is sampled", which Step 5's sampling made untrue.
  - **Scenario.** An agent relies on a Value Processor listing `input:1` as a Pixel Processor does, or on clamp
    along y, which no check has seen.
  - **Fix.** Narrow each sentence to what was measured, or add the cells: a Value Processor's later inputs, the y
    axis. Correct the comment.
  - **Resolution: done**.
    - **Test:** new cells, which passed on their first run, as they measure Designer:
      - in `image_inputs`, each fact for a Pixel and a Value Processor, and 40 inputs connected;
      - in `sampling`, each mode along y, and index 39 of 40.
    - **Fix:** GUIDE.md says "along x, then along y", that index 39 of 40 reads `input:39`, and that `input:40` is
      listed after 40 connections. The comment at `checks.py:647` is corrected.
  - Questioned by TST-745 (2026-11-22).

- [x] **TST-743 · Three of the tools' paths have no live check** · `mcp_server/server_tools/functions.py:249-260`, `mcp_server/designer_helpers/edits.py:423-431` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** Unit tests with fakes, or the raw API's facts, cover these, never the tools through Designer:
    - `set_function`'s note for a sampled index with nothing connected below a connected one, and for an input
      disconnected before the call;
    - a Value Processor's `input:1` connected with `apply_edits` and read with `sample(1, ...)`;
    - several image connects into one processor in one `apply_edits` call, each needing the input the one before
      made listed.
  - **Scenario.** A change breaking any of them through Designer passes every check.
  - **Fix.** A live cell for each, in the `sampling` or `image_inputs` part.
  - **Resolution: done**.
    - **Test:** two live checks, whose first run failed on the old refusal:
      - `check_set_function_samples_an_input_with_nothing_connected` connects three images in one `apply_edits`
        call, disconnects `input:1` before the call, checks the notes for `input:1` and `input:5`, and reads a pixel
        of `input:2` alone;
      - `check_set_function_samples_in_a_value_processor` connects a Value Processor's `input` and `input:1` in one
        call, and `sample(1, ...)` reads the normal map's R.
    - **Fix:** checks only.
  - Note (2026-11-22): only `check_set_function_samples_an_input_with_nothing_connected` failed first, on the old
    refusal. `check_set_function_samples_in_a_value_processor` covers a path that worked before.
  - Questioned by TST-746 and TST-747 (2026-11-22).

- [x] **TST-744 · The filter and wrap check drops `set_function`'s result** · `tests/test_all_tools/functions/checks.py:1170` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `check_set_function_samples_with_each_filter_and_wrap` awaits `set_function` and never reads what it
    returns. A refused expression leaves the node's old function, and the check fails only on the pixels.
  - **Scenario.** A compiler change refusing `wrap='clamp'` shows as wrong pixels, so the reader looks for a sampling
    bug.
  - **Fix.** Check that each call set the function, as the other checks do.
  - **Resolution: done**.
    - **Test:** the check compares each result with `built(...)`. It first failed on an expected text leaving out
      "deleted the 40 nodes it replaced", which shows it compares the whole line.
    - **Fix:** `built()` compiles `before` with `images`, and the second pack passes `before=`.
  - Questioned by TST-756 (2026-11-22).

- [x] **SRV-201 · Any index up to 2^31 - 1 is built, on a fact measured to index 5** · `mcp_server/function_compiler.py:277`, `:743-744`, `mcp_server/server_tools/functions.py:263` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.**
    - The compiler builds a sample of any index up to `INT_MAX`, "the largest index `__constant__`, an int2,
      holds", and the note says it reads (0, 0, 0, 0). With nothing connected, only index 5 of 2 inputs was
      measured. Neither the bound nor a large index's reading is.
    - An index above the bound is refused with "write a whole number", which it already is.
    - `_unsampled` reads `images[index]` for a negative index read back from a function graph made in Designer.
      With no image connected, that raises `IndexError` after the function is built.
  - **Scenario.** `sample(2147483647, $pos)` is built and the note says it reads (0, 0, 0, 0). If Designer reads
    something else, or fails, the note is wrong about what Designer does.
  - **Fix.** Measure a large index in a facts cell, such as 70 and 2^31 - 1, with Designer still answering after.
    Bound the index to what holds, and name the bound in the refusal. Skip negative indices in `_unsampled`.
  - **Resolution: done**.
    - **Test:** a row for `sample(2147483648, $pos)` in `test_each_mistake_in_a_sample_is_refused` failed on the
      generic "write a whole number". A `samplecol` of index -1 in
      `test_the_read_gives_the_input_images_a_function_graph_samples` failed, giving `[-1, 0, 2]` for `[0, 2]`. Four
      new cells in `check_sampling_an_image`, with its "answers after" line, failed first with "no line".
    - **Cause:** the bound was unmeasured, and its refusal didn't name it. `_sampled` kept a negative index read back
      from a function graph made in Designer, so `_unsampled` read `images[-1]`.
    - **Fix:** measured on a Pixel Processor with only `input` connected:
      - `__constant__` holds (2147483647, 0), and (2147483648, 0) wraps around to (-2147483648, 0);
      - samples of index 70, 2147483647 and -1 read (0, 0, 0, 0), and Designer answers after them.

      The compiler refuses an index above 2147483647, naming it and the wrap. `_sampled`
      (`designer_helpers/functions.py`) leaves out a negative index. GUIDE.md's "Sampling an image" gives the table.
    - **Also covered:** the skip sits in `_sampled`, which feeds the parameter-function refusal and both notes. So a
      function graph whose only sample is -1 is built when a parameter's function calls it. The lead dropped that
      case, and the note listing every input before a large index ("input to input:69"): a function graph made in
      Designer with index -1 is unlikely, and the long note is true.

- [x] **TST-745 · GUIDE's "Sampling an image" says more than its checks measure** · `mcp_server/GUIDE.md:402-416`, `tests/test_all_tools/functions/designer_scripts/function_nodes.py:1344-1346` · confirmed · follows TST-742, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.**
    - The mode is "measured ... along x, then along y" for `__constant__`, but only `samplecol` was measured along y.
    - The section's first sentence says "a Pixel or Value Processor", while every bullet below it was measured on a
      Pixel Processor. A Value Processor's cells are index 0 and 1, at the default mode.
    - "a function graph's result says so of each node calling it" leaves out an FX-Map's inner nodes, which
      `reaching` doesn't walk.
    - `measure_sampling`'s docstring still says only "Each mode at XS of the top row".
  - **Scenario.** An agent relies on `samplelum`'s clamp along y, or on a note for an FX-Map calling the function
    graph, which no check has seen.
  - **Fix.** At generation 2, narrow each sentence to what was measured, and name the y and 40-input cells in the
    docstring.
  - **Resolution: done**. Narrowed, at generation 2, with no new checks.
    - **Fix:** GUIDE.md's "Sampling an image" opens on a Pixel Processor. It says the mode was measured along x with
      both nodes and along y with `samplecol`, and a Value Processor's index 0 and 1 nearest and repeating. The callers'
      note covers each node whose own function calls the graph, directly or through others, and leaves out an FX-Map's
      inner nodes. `measure_sampling`'s docstring names the y, 40-input and large-index cells.

- [x] **TST-746 · Two checks make their second sampler before their `try`** · `tests/test_all_tools/functions/checks.py:1247-1250`, `:1363-1366` · confirmed · follows TST-743, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `check_set_function_samples_two_inputs` and `check_set_function_samples_an_input_with_nothing_connected`
    call `sampler` twice and read `added['pp']` before the `try`. When the first call is refused, `refs()` gives
    `{}`, and the `KeyError` skips the `finally`.
  - **Scenario.** The three-image `apply_edits` call is refused. The bare sampler's Pixel Processor and output stay
    in the self-test graph for the checks after it.
  - **Fix.** Open the `try` before the second `sampler`, and read the nodes inside it.
  - **Resolution: done**.
    - **Test:** `test_a_sampling_check_deletes_its_second_sampler_when_the_first_is_refused`
      (`tests/unit/test_selftest_functions.py`) runs both checks on a fake refusing the first `apply_edits`. It failed
      with no delete sent.
    - **Cause:** the second `sampler` and the first's node were read before the `try`.
    - **Fix:** both checks make the second sampler inside the `try`.
    - **Also covered:** the other five `sampler` uses make one sampler each.
  - Note (2026-11-22): `check_set_function_refusals_leave_the_graph_unchanged` adds its curve before its `try` too.
    No later check reads it.

- [x] **TST-747 · The new checks print the head of a result whose tail they check** · `tests/test_all_tools/functions/checks.py:1277-1296`, `:1369-1375` · confirmed · follows TST-743, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `check()` prints the first 150 characters of its detail (`common.py:75`). These checks pass the
    whole result and compare its end: the notes after the build line.
  - **Scenario.** A failing note prints only the build line, and the reader reruns the check to see the note.
  - **Fix.** Pass the result's last 150 characters, as the older refusal checks do (`text(r)[-150:]`).
  - **Resolution: done**.
    - **Test:** `test_a_sampling_checks_failure_shows_the_notes_it_compares` failed on the fake: the details printed
      the build line, not the note.
    - **Cause:** the checks passed the whole result, and `check()` prints its first 150 characters.
    - **Fix:** the notes run 160 to 250 characters, so a tail would cut their start. Each check prints the line it
      compares: the last line for an `endswith`, the caller's own line, or the first line that differs (`differing`,
      `results.py`).
    - **Also covered:** no other check of the category passes a whole result while comparing its end.

- [x] **TST-748 · Three test comments cite a decision that leaves with the branch** · `tests/test_all_tools/functions/checks.py:1357`, `tests/test_all_tools/functions/results.py:106`, `tests/unit/test_set_function.py:348` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** Each comment cites "the lead's decision, 2026-11-22" for building a sample of an input with nothing
    connected. That decision is recorded only in PLAN.md, which the branch's last commit deletes.
  - **Scenario.** After the merge, a reader follows the citation and finds nothing.
  - **Fix.** Cite GUIDE.md's "Sampling an image", which states the behaviour, or a DECISIONS.md entry if the user
    approves one.
  - **Resolution: done**. The three comments cite "GUIDE.md, Sampling an image". A comment fix, with no test.

- [x] **SRV-202 · `open_graph`'s refusal of `parameter` points at a call that is refused too** · `mcp_server/server_tools/views.py:287-292` · confirmed · found 2026-11-22 by three reviewers (Sonnet)
  - **Defect.** The refusal names `describe_graph(node_id=%r, parameter=%r)` whatever was given. Without `node_id`
    it names `describe_graph(node_id=None, ...)`, which `describe_graph` refuses ("give node_id too"). With
    `function`, it speaks of a node's function, where `describe_graph` and `set_function` say a function graph has no
    parameter (`NO_PARAMETER`).
  - **Scenario.** `open_graph(graph='g', parameter='perpixel')` tells the agent to call
    `describe_graph(node_id=None, parameter='perpixel')`, which is refused in turn.
  - **Fix.** Check `parameter` as `describe_graph` does first, sharing its refusals, with a unit row for each.
  - **Resolution: done**.
    - **Test:** `test_open_graph_refuses_a_parameter_with_no_node_as_describe_graph_does` (`test_server.py`), two
      rows, failed on the editor refusal naming `describe_graph(node_id=None, ...)`.
    - **Cause:** `open_graph` refused any `parameter` with its editor message.
    - **Fix:** `parameter_refusal(node_id, parameter, function)` (`server_tools/functions.py`), shared by
      `describe_graph` and `open_graph`, says "a function graph has none" or "give node_id too". The editor message
      comes only for a `parameter` with a `node_id`.
    - **Also covered:** `set_function` keeps its own branch, which adds "Nothing was built".
  - Questioned by SRV-206 (2026-11-22).

- [x] **SRV-203 · The docs say `set_function` builds every function node `search_nodes` lists** · `mcp_server/server_tools/discovery.py:108`, `:203`, `README.md:88`, `mcp_server/designer_helpers/editor.py:367`, `tests/unit/test_search.py:43` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `list_atomic` lists the module's 85 definitions, which the docstrings call "the function nodes
    set_function builds". The compiler never builds `while`, `sequence`, `passthrough`, `set` or `isdefined`.
  - **Scenario.** An agent finds `sequence` with `search_nodes` and writes an expression for it, which the compiler
    refuses.
  - **Fix.** Say "Designer's function nodes (`sbs::function::*`)", and keep the list whole: `describe_graph` shows
    what a hand-made function holds.
  - **Resolution: done**. A narrowing, with no test of its own: `search_nodes`' and `_FunctionEntry`'s docstrings,
    README's Tools row, `list_atomic`'s comment and `test_search.py`'s say "Designer's function nodes
    (`sbs::function::*`)". The list stays whole.

- [x] **SRV-204 · A function's listing gives node kinds `describe_node` refuses, and ignores `include_params` unsaid** · `mcp_server/designer_helpers/core.py` (`node_kind`), `mcp_server/server_tools/discovery.py:26`, `:69-78` · confirmed · found 2026-11-22 by three reviewers (Sonnet)
  - **Defect.**
    - `describe_graph(function=...)` lists kinds such as `add` and `get_float2`, without `sbs::function::`, and
      `describe_node('add')` answers "neither an atomic node nor a library package".
    - `include_params` changes nothing in a function's listing, whose node lines always carry their constants, and
      its Field doesn't say so.
  - **Scenario.** An agent copies a kind from a function's listing into `describe_node` and is refused, or passes
    `include_params=True` expecting more.
  - **Fix.** `describe_node` tries `sbs::function::<name>` before refusing, or the docstring says how a kind maps to
    its definition. The `include_params` Field says it applies to a graph's nodes.
  - **Resolution: done**.
    - **Test:** `describe_node('lr')` in `check_describe_node_and_search_nodes_know_the_function_nodes` failed first
      with "neither an atomic node nor a library package".
    - **Fix:** a name that is no atomic node and no library package is described as `sbs::function::<name>` when the
      module has it, as its Field says. `include_params`' Field says it is for a graph's nodes, and that a function's
      nodes always show their constant: a narrowing.
  - Questioned by SRV-205 (2026-11-22).

- [x] **HLP-241 · The `sbs::function` module is read in two places, neither guarding a missing label or description** · `mcp_server/designer_helpers/editor.py:368-373`, `mcp_server/designer_helpers/describe.py:276-281` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** sd's stub lets `getLabel()` and `getDescription()` return None. `list_atomic` joins them, and
    `_describe_function_node` passes the description to `re.sub`, both unguarded. The server's
    `_flat(description or '')` assumes None can come.
  - **Scenario.** On a Designer whose module has one definition without a description, `list_atomic` raises, and
    every `search_nodes` call fails, not only for function nodes. Designer 16's 85 have both (the live check).
  - **Fix.** One helper in `core.py` reading the module's definitions, with `or ''` on both texts, used by both.
  - **Resolution: done**.
    - **Test:** `test_a_function_node_with_no_label_or_description_is_listed` and `..._is_described`
      (`tests/unit/test_function_reads.py`) failed first with an `AttributeError` in `list_atomic` and a `TypeError`
      in `re.sub`.
    - **Cause:** both readers took `getLabel()` and `getDescription()` raw, which sd's stub lets be None.
    - **Fix:** one reader, `_function_definitions()` in `core.py`, gives each definition with `label or ''` and
      `description or ''`, for `list_atomic` and `describe_node`. Measured: none of Designer 16's 85 has a None or
      empty one (`check_the_function_definitions`).
    - **Also covered:** the helpers' other `getLabel` and `getDescription` calls were guarded already.
  - Note (2026-11-22): `tests/unit/test_function_reads.py:45` still fakes `getDefinitionFromId`, which the fix
    no longer calls. No test depends on it.
  - Note (2026-11-22): the dead setup is removed, with the last of Step 6's fixes.
  - Questioned by HLP-248 (2026-11-22).

- [x] **HLP-242 · `describe_graph`'s function graphs line drops silently on an error, and has no cap** · `mcp_server/designer_helpers/describe.py:86-91` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** An error reading one function graph leaves the line out for all of them, with nothing said. The line
    ignores `limit` and `node_ids`, and comes with every `describe_graph`.
  - **Scenario.** A package holds one function graph that can't be read (HLP-237's kind): the agent sees no line and
    takes it that the package has none. A package with dozens adds a long line to every focused `describe_graph`.
  - **Fix.** On an error, say the function graphs weren't read, with the error. Leave the line out when `node_ids`
    is given, or cap it.
  - **Resolution: done**.
    - **Test:** `test_a_function_graphs_line_that_fails_says_so` (no line printed) and
      `test_a_description_focused_on_nodes_leaves_the_function_graphs_out` (the line present) failed first, and so
      did the live line "a description focused on node_ids leaves the function graphs out".
    - **Cause:** the error was swallowed, and the line came with every call.
    - **Fix:** the line comes only without `node_ids`, and an error prints "function graphs of the package: not read
      (<error>)". The tool's docstring and GUIDE.md say "of a whole graph".
    - **Also covered:** `describe_graph`'s `$outputsize` and frames lines, older than this branch, skip an error the
      same way, and were left.
  - Questioned by TST-753 (2026-11-22).

- [x] **HLP-243 · Two helper docstrings say what the code doesn't** · `mcp_server/designer_helpers/core.py:396-398`, `mcp_server/designer_helpers/__init__.py:14` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `_type_ids` says "None when there is no property, or the types can't be read", and returns `[]`.
    The package's docstring says "nothing else depends on the order", while `describe_functions` evaluates
    `functions`' types at load and must follow it.
  - **Scenario.** A caller tests `_type_ids(...) is None`, or a reader reorders `PARTS` and breaks the helpers' load.
  - **Fix.** Say `[]`, and name the order `describe_functions` needs.
  - **Resolution: done**. A narrowing, with no test of its own: `_type_ids` says `[]`, and the package's docstring
    says `describe_functions` follows `functions`, whose types it reads at load. `test_designer_helpers`' order test
    guards the order.

- [x] **HLP-244 · `describe_graph` refuses a function on a parameter `set_function` can't build, in `set_function`'s words** · `mcp_server/designer_helpers/functions.py:192` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** `describe_function` reaches its target through `_target_of`, `set_function`'s, which refuses a
    parameter of a type no getter reads: "parameters of type X cannot take a function from this tool".
    `describe_graph`'s Field says "any parameter's". The developer reported it too.
  - **Scenario.** A function made in Designer on such a parameter can't be listed, and the read is refused as if it
    were a write.
  - **Fix.** The read lists any parameter's function. Or the Field and the message say what the read covers.
  - **Resolution: done**.
    - **Test:** `check_describe_graph_lists_a_parameter_set_function_refuses`, on a curve's `curveluminance`, failed
      first with "parameters of type SDTypeArray<sbs::compositing::curve_key> cannot take a function from this tool".
    - **Cause:** the read reached its target through `_target_of`, which carries `set_function`'s refusal.
    - **Fix:** `_function_parameter` (the node, its parameter, the function's kind) and `_input_values` (the input
      values and their feeds) came out of `_target_of`, which keeps the refusal and uses both. The read uses them
      without it. Measured: `newPropertyGraph` gives None on a curve's five curves and a gradient's `gradientrgba`, so
      no function can be made there through the API.
    - **Also covered:** `set_function` still refuses such a parameter, checked live.
  - Questioned by HLP-245 (2026-11-22).

- [x] **TST-749 · `search_nodes`' parsing of function nodes has no unit test** · `mcp_server/server_tools/discovery.py:153-156` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `_library_index` splits each `FUNCTION=` line into three fields. `test_search.py` puts entries in the
    cache directly, and `test_library_subfolders.py`'s fake reply has no `FUNCTION=` line, so only the live check
    reaches the parsing.
  - **Scenario.** A change to the split, or a line with an empty description, breaks `search_nodes` with no unit
    test failing.
  - **Fix.** A `FUNCTION=` line, and one with an empty description, in `test_library_subfolders.py`'s fake reply,
    found by `search_nodes`.
  - **Resolution: done**. Coverage, which passed on the code as it was:
    `test_search_finds_the_function_nodes_list_atomic_reads` (`test_library_subfolders.py`) puts two `FUNCTION=`
    lines in the fake reply, one with an empty description, and `search_nodes` finds both.

- [x] **TST-750 · Some paths of the new reads have no live check** · `mcp_server/designer_helpers/describe_functions.py:30-34`, `:80-87`, `mcp_server/designer_helpers/describe.py:276-279` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.**
    - No check describes a Value Processor's function (`_FUNCTION_OF['function']`).
    - "an empty function", the state of a new processor, is never shown.
    - `describe_node` of an unknown `sbs::function` id is never called. Whether `getDefinitionFromId` returns None,
      as the code assumes, or raises, is unmeasured.
  - **Scenario.** A break in any of them passes every check. An unknown id gives a bare API error in place of the
    message.
  - **Fix.** A cell for each, measuring what Designer gives for the unknown id.
  - **Resolution: done**. Coverage, which passed on the code as it was:
    - `check_describe_graph_shows_a_value_processors_function_and_says_when_there_is_none` shows a Value Processor's
      function, a new processor's "no function" and "an empty function";
    - `describe_node('sbs::function::no_such')` is refused naming `search_nodes`.

    Measured: a new Pixel Processor's `perpixel` has no function, and `newPropertyGraph` then gives an empty one.
    `getDefinitionFromId` of an unknown id gives None, though the fix no longer calls it.

- [x] **TST-751 · The function nodes' check compares two definitions, and its search depends on the library** · `tests/test_all_tools/functions/checks.py:1556-1572` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** GUIDE.md says `describe_node` gives "every type each of their inputs takes", and the check compares
    `add` and `samplecol` only. `search_nodes('lower than')` finds `lr` only while fewer than 30 entries of its rank
    or better hold both words, so a larger library pushes it past the default limit.
  - **Scenario.** A definition whose types `describe_node` misreads passes. A larger library fails the search with a
    result that looks complete.
  - **Fix.** Compare every definition of `compiler_table()`, or narrow GUIDE's sentence. Pass a larger `limit`.
  - **Resolution: done**. Coverage, which passed on the code as it was: one code job runs `describe_node`'s helper
    on all 85 definitions of `compiler_table()`, each compared with `parsing.described_differs`. The searches pass
    `limit=1000`.

- [x] **TST-752 · Nothing checks that `screenshot_designer` sees an opened function graph** · `tests/test_all_tools/functions/checks.py` (`check_open_graph_opens_a_function_graph`), `mcp_server/GUIDE.md:50-52` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** The step says `open_graph` opens a function graph "so the user and `screenshot_designer` see it".
    The checks show it current in the editor with its panel titled, never a screenshot of it.
  - **Scenario.** The graph view doesn't draw a function graph where `screenshot_designer('graph')` grabs, and an
    agent shows the user a stale picture.
  - **Fix.** Take `screenshot_designer('graph')` after the open, and check it differs from the compositing graph's.
    Or narrow GUIDE's sentence.
  - **Resolution: done**. Coverage, which passed on the code as it was: `check_open_graph_opens_a_function_graph`
    takes a shot of the graph after `open_graph`, then one after `open_graph(function=...)`, which must differ. They
    do, so GUIDE.md's sentence stands.

- [x] **SRV-205 · `describe_node` of `pow` or `passthrough`, as a function's listing names them, describes another node** · `mcp_server/designer_helpers/describe.py:232-243`, `mcp_server/designer_helpers/core.py:303` · confirmed · follows SRV-204, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** The fallback to `sbs::function::<name>` comes only when no atomic node and no library package has the
    name. Designer ships `pow.sbs`, and `passthrough` is also the compositing Dot node, while both are function nodes
    `set_function` builds. A function's listing gives their kind without its module.
  - **Scenario.** After `pow(#a, 2.0)`, `describe_graph` lists a node of kind `pow`, and `describe_node('pow')`
    describes the library graph `pow.sbs`.
  - **Fix.** At generation 2, narrow the Field and the docstring: a kind that also names an atomic node or a library
    package needs its full id. Or end that answer with a line naming the function node of the same name.
  - **Resolution: done**.
    - **Test:** a cell in `check_describe_node_and_search_nodes_know_the_function_nodes` calls `describe_node('pow')`
      and `describe_node('passthrough')`. Each answer starts with the other node (`library node pow`, `atomic node
      sbs::compositing::passthrough`) and must end with "<name> is a function node's kind too:
      describe_node('sbs::function::<name>') describes that one". Both failed first, with no such line.
    - **Cause:** the fallback came only when no atomic node or library package had the name.
    - **Fix:** `describe_node` (`designer_helpers/describe.py`) looks up `sbs::function::<name>` once. It describes
      the function node when nothing else has the name, and adds the line after an atomic or library answer. The
      Field and the docstring say so.
    - **Also covered:** both clashes, a library package and an atomic node.

- [x] **SRV-206 · `open_graph(parameter=...)` without `node_id` sends the agent to the next refusal** · `mcp_server/server_tools/views.py:288-297`, `mcp_server/server_tools/functions.py:139-148`, `tests/unit/test_server.py:720` · confirmed · follows SRV-202, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `open_graph` gives the shared "parameter is a node's: give node_id too" first. With `node_id`
    added, it is refused again: Designer's editor can't open a node's function.
  - **Scenario.** `open_graph(graph='g', parameter='perpixel')`, then `open_graph(graph='g', node_id='7',
    parameter='perpixel')`: two refusals, the first pointing at the second.
  - **Fix.** In `open_graph`, take the shared message only with `function`. For `parameter` alone, give the editor
    refusal, naming `describe_graph` with the node to give. Change the unit row to match.
  - **Resolution: done**.
    - **Test:** `test_open_graph_refuses_a_parameter_with_no_node_in_one_answer` (`test_server.py`): its "no node" row
      failed first, with "give node_id too".
    - **Cause:** `open_graph` took `describe_graph`'s "give node_id too" for a `parameter` alone.
    - **Fix:** `open_graph` gives `NO_PARAMETER` only with `function`. For a `parameter` alone it gives the editor
      refusal, naming `describe_graph(node_id=<the node's id>, parameter=...)`. The shared `parameter_refusal` is
      gone, as the two tools now refuse differently, and `NO_PARAMETER` stays shared.
    - **Also covered:** `describe_graph`'s refusals are unchanged, and their unit rows pass.
  - Questioned by SRV-207 (2026-11-22).

- [x] **HLP-245 · `describe_graph` says "no function" when reading the function fails** · `mcp_server/designer_helpers/describe_functions.py:85-90`, `tests/test_all_tools/functions/checks.py:1748-1764` · confirmed · follows HLP-244, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** An error from `getPropertyGraph` is caught and printed as "<id>.<parameter> has no function". The
    curve's check, `check_describe_graph_lists_a_parameter_set_function_refuses`, sees only that line, so it shows
    the read doesn't refuse, not that it lists a function. That no function can be made on such a parameter is
    stated only in REVIEW.md.
  - **Scenario.** A parameter whose function can't be read is reported as having none, and the agent builds over a
    function it never saw.
  - **Fix.** Say the function couldn't be read, with the error. Narrow the check's docstring to what it shows.
  - **Resolution: done**.
    - **Test:** `test_a_nodes_function_that_cant_be_read_says_so` (`test_function_reads.py`), `getPropertyGraph`
      raising, failed first with "7.leveloutlow has no function".
    - **Cause:** the read's error was caught and printed as no function.
    - **Fix:** `_node_function_read` prints "<id>.<parameter>: its function couldn't be read (<error>)". The curve
      check's docstring says only what it shows: the read doesn't refuse, and says the parameter has no function. The
      curve's read doesn't raise in Designer: the check still gets "has no function".

- [x] **TST-753 · HLP-242's focus check passes on any text holding the node's id, and README still names the line always** · `tests/test_all_tools/functions/checks.py:1801-1807`, `README.md:89` · confirmed · follows HLP-242, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `ctx.pp in t` holds for any text with that number in it, such as "13 nodes" or "not found: 3", so a
    focus that listed nothing passes. README's Inspecting row says `describe_graph` gives "a graph's nodes and its
    package's function graphs", while the line now comes only for a whole graph.
  - **Scenario.** `describe_graph(node_ids=[...])` lists no node and the check passes. A reader of README expects the
    line in a focused description.
  - **Fix.** Check the node's own line, with `positions(t)` (`common.py`). Say "a whole graph's" in README.
  - **Resolution: done**. The focus line requires `list(positions(t)) == [ctx.pp]`. It passes on the code, which
    lists the node: a check made stronger can't be seen failing without breaking the code. README's Inspecting row
    says "a graph's nodes, and for a whole graph its package's function graphs", a narrowing.

- [x] **HLP-246 · Function nodes' descriptions keep their HTML entities** · `mcp_server/server_tools/discovery.py:142-144`, `mcp_server/designer_helpers/describe.py:291` · confirmed · found 2026-11-22 by the developer (Opus)
  - **Defect.** `_flat` and `_describe_function_node` strip a description's tags but leave its entities, so
    `search_nodes` and `describe_node` show `lr`'s as "...lower than second entry: A&lt;B" (Step 6's last scratch
    run).
  - **Scenario.** An agent reads `&lt;`, `&gt;` or `&amp;` in a function node's description.
  - **Fix.** `html.unescape` after the tags are stripped, in both places. `_short_description` (`describe.py:217`,
    older than this branch) strips tags the same way: check it too.
  - **Resolution: done**.
    - **Test:** these failed first, with `A&lt;B` or `&gt;`:
      - `test_a_function_node_is_found_by_its_description_or_its_label`, and two tests in `test_function_reads.py`;
      - live, lr's `search_nodes` line and every function node's `describe_node` text;
      - `check_a_parameters_description_shows_the_characters_its_entities_stand_for` (`discovery`), on
        `paths_tools.sbs/mask_to_paths`' threshold.
    - **Cause:** the descriptions' tags were stripped and their entities kept.
    - **Fix:** `html.unescape` after the tags are stripped, in the server's `_flat` and the helpers'
      `_describe_function_node` and `_short_description`.
    - **Also covered:** `_short_description`, older than this branch: four library packages hold entities in their
      parameters' descriptions.

- [x] **SRV-207 · `open_graph`'s refusal of a node's function names a `describe_graph` call without its graph** · `mcp_server/server_tools/views.py:288-295` · confirmed · follows SRV-206, generation 3 · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** The refusal suggests `describe_graph(node_id=..., parameter=...)`, leaving out the `graph` that
    `open_graph` requires. Copied as it is, it reads the node of the graph in the editor.
  - **Scenario.** With another graph in the editor, the suggested call answers "not found", or another node's
    function.
  - **Fix.** At generation 3, the message alone: name `graph=%r` in it, with its unit row's text. No new check.
  - **Resolution: done**. The message alone, at generation 3.
    - **Test:** `test_open_graph_refuses_a_nodes_function_before_designer` and the "no node" row of
      `test_open_graph_refuses_a_parameter_with_no_node_in_one_answer` failed first. The live check's expected text
      follows.
    - **Fix:** the refusal names `describe_graph(graph=%r, node_id=..., parameter=...)`.
    - **Also covered:** no other refusal suggests a call without its graph.

- [x] **SRV-208 · The grammar lists `rand` with neither its argument nor what it gives** · `mcp_server/server_tools/functions.py:44-45` · confirmed · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** `EXPRESSION` writes `lerp(a, b, x)`, `atan2(y, x)` and `clamp(x, low, high)`, and only `rand` for a
    function that takes one float, which GUIDE's scripting part measured as "a value from 0 to 0.1" for 0.1. Whether
    it varies from pixel to pixel is unmeasured.
  - **Scenario.** An agent writes `rand()` and gets only the count, or `rand(1)` expecting noise across the pixels.
  - **Fix.** Measure `rand(1)` over a Pixel Processor's pixels, then write `rand(max)` and what it gives in the Field.
  - **Resolution: done**.
    - **Test:** the `computed` part reads `rand(1)` at 16 pixels, and `check_what_nodes_compute` wants more than 8
      distinct values (15 measured). A measurement, passing on its first run.
    - **Fix:** the Field says `rand(max) (from 0 to max, varying from pixel to pixel)`, and GUIDE.md's "What nodes
      compute" gives the measure. A probe on 256 px gave 0.004 to 0.996, `rand(0.5)` half of each, the same at a
      second compute.
  - Questioned by SRV-214 (2026-11-22).

- [x] **SRV-209 · ROADMAP's items 9 and 116 say what the branch changed** · `ROADMAP.md:46`, `:48` · confirmed · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** Item 9 is unchecked. It says `open_graph` would reach a node's function, which Designer's editor
    can't open, and that a processor's second input couldn't be added through the API, which `connect` now does once
    `input` is connected. Item 116, added by this branch, cites `designer_helpers/edits.py:129`, which has moved.
  - **Scenario.** A reader of ROADMAP takes item 9 as still to do, and follows item 116's line to the wrong code.
  - **Fix.** Check item 9, with a Done note naming both outcomes. Name `_make_value`'s refusal in item 116 instead
    of a line.
  - **Resolution: done**. Docs only, the docs tests passing. Item 9 is checked, its Done note saying that
    `open_graph` refuses a node's function, which `describe_graph` lists, and that `connect` reaches `input:1` once
    `input` is connected. Item 116 names `_make_value`'s refusal in place of a line.

- [x] **SRV-210 · A `#word` comment without a space gives a message that blames another line, or none** · `mcp_server/function_compiler.py:399-405`, `:428-436`, `:514-521`, `tests/unit/test_function_compiler.py:560-561` · confirmed · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** A `#` followed by a letter is an input value's name. The hint "a comment starts with `# `" comes only
    when the `#` follows a name, a number or a `.`. At a line's start, or after a space, `#word` becomes an input
    value, and the refusal names something else.
  - **Scenario.** `x = f * 2\nx\n#done` is refused with "line 2, column 1: `x` gives a value before the last
    statement", and `f * 2  #twice` with "invalid syntax", neither naming the comment. Nothing is built wrong.
  - **Fix.** Add the hint to the refusals a lone `#name` statement leads to, and to a syntax error at a `#` followed
    by a letter, with their unit rows.
  - **Resolution: done**.
    - **Test:** rows in `test_each_mistake_with_an_input_value_is_refused` (`f * 2  #twice`, `x = f * 2\nx\n#done`,
      `#done\nf * 2` and others) and `test_a_comment_without_its_space_in_a_function_graphs_expression_is_named`
      failed first, with "invalid syntax" and no hint, or with the line before blamed.
    - **Cause:** a `#word` at a line's start or after a space was read as an input value, and only a `#` after a name,
      a number or a `.` got the comment hint.
    - **Fix:** a syntax error adds "`#twice` reads as an input value's name: a comment starts with `# `" for the first
      such `#name` on its line. A lone `#name` statement, among several, naming no input value, is refused before
      compiling: "`#done` stands alone and reads as an input value's name, which the node lacks: a comment starts
      with `# `". `COMMENT` is one constant for the three hints.
    - **Also covered:** `SIGILS` and `NO_VALUES` carried the hint already.
  - Questioned by SRV-213 (2026-11-22).
  - Questioned by SRV-215 (2026-11-22).

- [x] **SRV-211 · One list-joining helper is written in the compiler and again in the server** · `mcp_server/function_compiler.py:319-321`, `mcp_server/server_tools/functions.py:299-301` · confirmed · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** `_listed(t)` is `with_article(_joined(t, 'or'))`, written out twice, against the user's DRY
    instruction (2026-11-21).
  - **Scenario.** A change to one wording misses the other.
  - **Fix.** Make the compiler's joining helper public, as `with_article` is, define `_listed` from it, and import it
    in the server.
  - **Resolution: done**. A refactor: `function_compiler.joined_with(items, word)` is public, `_listed` is
    `with_article(joined_with(types, 'or'))`, and the server's three calls import it. The compiler's and the server's
    tests pass before and after.

- [x] **SRV-212 · `$pos` and the other variables are described for every function, measured in a Pixel Processor's** · `mcp_server/server_tools/functions.py:36`, `mcp_server/GUIDE.md:291-296`, `:386` · confirmed · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** The compiler takes `$pos`, `$size`, `$sizelog2`, `$tiling` and `$time` in a Value Processor's
    function and in a parameter's, and `EXPRESSION` describes `$pos` as "the pixel's centre over the size" for all.
    GUIDE measures them in a Pixel Processor, and in a function graph called from one, only.
  - **Scenario.** An agent drives a blend's `opacitymult` with `$pos.x`, expecting a ramp, and gets whatever Designer
    gives a parameter's function.
  - **Fix.** Measure `$pos` and `$size` in a Value Processor's function and a parameter's, then say what each gives
    there, or narrow the Field to a Pixel Processor.
  - **Resolution: done**. The claim narrowed, with measured values.
    - **Test:** `check_system_variables` and the `variables` part read them, passing on their first run.
    - **Fix:** measured: in a Value Processor's function, `$pos` reads (0, 0) and `$size` the graph's size; in a
      blend's `opacitymult`, `$pos` reads 0 and `$size` the size. `EXPRESSION` says `$pos` is the pixel's centre in a
      Pixel Processor's function and the function graphs it calls, and (0, 0) in a Value Processor's or a
      parameter's. GUIDE.md's Variables gives the values.
  - Questioned by SRV-214 (2026-11-22).

- [x] **HLP-247 · A `#name` input value on an instance node is unmeasured, a library graph's instance included** · `mcp_server/designer_helpers/edits.py:391-415` · confirmed · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** `_input_value` makes `#name` with `newProperty`, measured on a blend, a Pixel Processor and a Value
    Processor. An instance node's inputs mirror the graph it references, and no check made one there.
  - **Scenario.** An agent connects a Value Processor into a `bevel` node's `#v`, the main use of value connections.
    The `newProperty` may work on the node, raise a bare API error, or reach the library graph, which GUIDE says the
    tools never change.
  - **Fix.** Measure it on an instance of a library graph: the node's inputs, the library graph's, and whether its
    package reads as modified. Then say it in GUIDE.md, or refuse it with a message.
  - **Resolution: not a bug**. Measured, with no refusal needed.
    - **Test:** `check_a_value_connection_into_a_library_graphs_instance`, a "designer facts" check through the tools,
      passed on its first run: it measures behaviour that was right already.
    - **Why not:** a connect into `#v` on an instance of `contrast_luminosity_grayscale` makes `#v` on the node only.
      The library graph has no `#v`, its package isn't modified, and `Luminosity` reading `#v` follows the processor
      (0 at 0, 0.302 at 0.3). A probe on `bevel` gave the same. GUIDE.md's Input values says so.

- [x] **HLP-248 · `getDefinitions()` of the function module isn't guarded against None** · `mcp_server/designer_helpers/core.py` (`_function_definitions`) · confirmed · follows HLP-241, generation 2 · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** sd's stub lets `getDefinitions()` return None, as `getTypes()` does. HLP-241's reader guards each
    definition's label and description, not the list. Designer 16 gives all 85.
  - **Scenario.** On a Designer whose module gives None, every `describe_node` and `search_nodes` fails.
  - **Fix.** `or []` on the list, in the same reader.
  - **Resolution: done**.
    - **Test:** `test_a_module_giving_no_definitions_lists_no_function_node` and
      `test_a_graph_giving_no_node_definitions_lists_no_atomic_node` failed first with "'NoneType' object is not
      iterable".
    - **Cause:** sd's `getDefinitions()` and `getNodeDefinitions()` return None on `NoErrorOutputParamNotSet`.
    - **Fix:** `_function_definitions` iterates `found or []`, and `atomic_definition_ids` (`edits.py`)
      `g.getNodeDefinitions() or []`. `list_atomic` reuses `atomic_definition_ids`.
    - **Also covered:** `describe_node` and the `add` op read through `atomic_definition_ids` too.
  - Note (2026-11-22): `tests/unit/test_put_backs.py:236` still fakes `getNodeDefinitions`, which the fix's
    `atomic_definition_ids` patch makes unused. No test depends on it.

- [x] **TST-755 · Two search tests can't see what their names say** · `tests/unit/test_search.py:103-114` · confirmed · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** `test_a_function_nodes_exact_name_ranks_first` searches `add`, which no other entry holds, so any rank
    passes. `test_a_function_node_is_found_by_its_description_or_its_label` finds `sample color` through the name and
    the description, so dropping the label from the search passes every test.
  - **Scenario.** A function node's rank, or its label's part in the search, breaks with no test failing.
  - **Fix.** An entry ranked below `add` that holds "add", and a query only a label holds. Or names saying what the
    tests show.
  - **Resolution: done**. Coverage, passing on the code as it was: the fixture gains `Add Noise`, a library entry
    listed before the function nodes, so `add` must rank first by name, and `samplelum`, labelled "Sample Gray", which
    `sample gray` finds by its label alone.

- [x] **TST-756 · The check that a replacement keeps the node's connections never reads the replacements' results** · `tests/test_all_tools/functions/checks.py:766-792` · confirmed · follows TST-744, generation 2 · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** `check_set_function_keeps_the_nodes_connections_and_parameters` drops the results of its two
    replacing `set_function` calls. `describe_graph` shows "<- a function" for any function, so `before == after`
    holds whether or not anything was replaced. It is the one check replacing a parameter's function that has an
    output node.
  - **Scenario.** `set_function` stops replacing a parameter's function that has one, and the check passes.
  - **Fix.** Check that each replacing call built, by its result or by the pixels after.
  - **Resolution: done**. Coverage, at generation 2: each replacing call's result must start with
    `built(..., before=...)`, which now compiles `before` with the same `inputs`.

- [x] **TST-757 · The compiler tests' docstring says every compiled function is checked whole, and two aren't** · `tests/unit/test_function_compiler.py:1-3`, `:630-631`, `:652-653` · confirmed · follows TST-704, generation 2 · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** The loop test and the diamond test call `compile_expression` directly, not `compiled()`.
  - **Scenario.** A wrong node in a function graph's call goes unseen there, as the docstring says it can't.
  - **Fix.** Call `compiled()` in both, or narrow the sentence.
  - **Resolution: done**. Narrowed, at generation 2: the docstring says the loop and diamond tests read only the
    calls' tree.

- [x] **SRV-213 · The comment hint of a syntax error can name the node's own input value** · `mcp_server/function_compiler.py:462` · confirmed · follows SRV-210, generation 2 · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** `_value_before` takes the first `#` and a letter on the error's line, without checking whether it
    names one of the node's input values.
  - **Scenario.** With `#v` connected, `#v * 2  #double` is refused with "`#v`, at column 1, reads as an input
    value's name: a comment starts with `# `", which names the input value read on purpose and never `#double`. Any
    syntax error on a line reading `#v` gets that hint.
  - **Fix.** Skip the node's own input values, as `_refuse_a_lone_value` does, with unit rows for both cases.
  - **Resolution: done**.
    - **Test:** three rows in `test_each_mistake_with_an_input_value_is_refused` failed first: `#v * 2  #double` and
      `#v * (1 2)` got the hint about `#v`, and `f *  # see #now` got one about `#now`, inside a real comment.
    - **Cause:** `_value_before` took the first `#` and a letter anywhere on the error's line, the node's own input
      values and the line's comment included.
    - **Fix:** `_value_before` passes over the node's input values, as `_refuse_a_lone_value` does, and scans only the
      line's code. `_code(line)` gives the part before the comment, and `_statements` uses it too.
    - **Also covered:** the case inside a real comment, which `/simplify` found and a probe confirmed.

- [x] **SRV-214 · The new sentences on `rand` and `$pos` say more than their cells measure** · `mcp_server/server_tools/functions.py:38`, `:47`, `mcp_server/GUIDE.md:295`, `tests/test_all_tools/functions/designer_scripts/function_nodes.py:607-617`, `:753` · confirmed · follows SRV-208 and SRV-212, generation 2 · found 2026-11-22 by two reviewers (Opus)
  - **Defect.**
    - `EXPRESSION` says `rand` varies "from pixel to pixel" for every function, measured in a Pixel Processor only.
    - The blend's cells read `$pos` through an 8-bit pixel unshifted, so "reads 0 in a parameter's function" is
      measured as "0 or less".
    - `rand of 0.1` is read unshifted too, so nothing guards "from 0 to max".
  - **Scenario.** An agent drives a blend's `opacitymult` with `rand(1)` expecting noise across the pixels, or writes
    `$pos.x + 0.5` there expecting 0.5.
  - **Fix.** At generation 2, narrow `rand`'s sentence to a Pixel Processor's function. Shift the blend's and the
    `rand` cells, a line each, so a negative reads, or narrow their sentences.
  - **Resolution: done**. Narrowed, at generation 2.
    - **Test:** the blend's `$pos` cells read `$pos.x + 0.5` and `$pos.y + 0.5`, and `rand of 0.1, then x + 0.5`
      wants 0.50 to 0.60. In Designers just started, `$pos.y + 0.5` read 0.00 in 2 of 11 runs; every other read gave
      0.50, and `rand`'s 0.56.
    - **Fix:** `EXPRESSION` says `rand` varies from pixel to pixel in a Pixel Processor's function, and that in a
      parameter's function `$pos` isn't the pixel's (0, or below 0 at random): use it in a Pixel Processor's.
      GUIDE.md's Variables gives the counts. The blend cells pass on 0.50 at most, so they hold on both outcomes seen
      and fail if Designer ever gives the pixel's position there.
  - Questioned by TST-758 (2026-11-22).

- [x] **SRV-215 · A comment without its space still blames another line when it parses as more than a name** · `mcp_server/function_compiler.py:479-487`, `:12-14` · confirmed · follows SRV-210, generation 2 · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** `_refuse_a_lone_value` catches a lone `#name` only. With `#` read as `_`, `#half-res` parses as a
    subtraction, `#scale and bias` as a `BoolOp` and `#TODO: tune` as an annotated assignment. The module docstring
    says a refusal names such a name where a comment may have been meant.
  - **Scenario.** `x = f * 2\nx\n#half-res` is refused with "line 2, column 1: `x` gives a value before the last
    statement", which is SRV-210's scenario with a hyphen.
  - **Fix.** At generation 2, narrow the docstring to the lone name and the syntax error. Or refuse a statement
    starting with a `#name` the node lacks, if that stays small, with unit rows.
  - **Resolution: done**. The wider refusal stayed small.
    - **Test:** rows in `test_each_mistake_with_an_input_value_is_refused` (`#half-res`, `#scale and bias`,
      `#TODO: tune`, `#scale = 2`) failed first, blaming another line or giving `_bind`'s false "is an input value of
      the node". `test_a_statement_led_by_the_nodes_own_input_value_compiles` guards the node's own `#v`.
    - **Cause:** the refusal caught a lone `#name` only, while a comment of more words parses as a subtraction, a
      `BoolOp`, an annotation or an assignment.
    - **Fix:** `_refuse_a_leading_value` refuses any statement of several led by a `#name` the node lacks:
      "`#half` starts its statement and reads as an input value's name, ...: a comment starts with `# `". `#x = 1;
      0.5` in a function graph now gets it too. `VALUE_NAME` is the one pattern, shared with `_value_before`.

- [x] **SRV-216 · `EXPRESSION` says `7 / 2` is 3, and it gives 3.5** · `mcp_server/server_tools/functions.py:45` · measured · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** Number literals compile as floats where nothing says otherwise. Measured: `7 / 2` builds `div` of two
    `const_float1`, while `i / j` of two int inputs and `int(7) / 2` build an int `div`.
  - **Scenario.** An agent reads the tool's description and expects `7 / 2` to give 3.
  - **Fix.** An example that truncates, such as `int(7) / 2` or `i / j` of two ints.
  - **Resolution: done**.
    - **Test:** `test_the_grammars_truncating_example_divides_ints` compiles the example `EXPRESSION` gives. It failed
      first: `7 / 2` built a float `div`.
    - **Fix:** `EXPRESSION` says "/ of two ints truncates (int(7) / 2 is 3)".

- [x] **SRV-217 · ROADMAP text the branch made untrue** · `ROADMAP.md:114-115`, `:123`, `:129`, `:151` · confirmed · found 2026-11-22 by a reviewer (Opus)
  - **Defect.**
    - Item 86 says `screenshot_designer` "keeps its shot in a temp folder"; the tool deletes the folder when the
      call ends (`views.py:217`, `:248-249`).
    - The new table's intro says items 78, 82 and 86 follow the 3D view section's rules and call them "the rules
      above". Item 86 changes no set-up of the 3D view, and its text doesn't say it.
    - Item 115 says item 9's tool "can then set the functions that drive a Quadrant's parameters", while
      `set_function` can't reach an FX-Map's inner node (HLP-239).
    - Item 16 still counts 35 tools.
  - **Scenario.** Someone planning item 86 looks for the shot's file. Someone planning item 115 leaves out the work
    that would let `set_function` reach an FX-Map's nodes.
  - **Fix.** Item 86: the shot is written to a temp folder and deleted. The intro names 78 and 82 only. Item 115:
    `set_function` first needs a way to name an FX-Map's inner node. Item 16: 36.
  - **Resolution: done**. Docs only, the docs tests passing: item 86 says the shot is written to a temp folder and
    deleted when the call ends; item 115 says `set_function` first needs a way to name an FX-Map's inner node
    (HLP-239); item 16 counts 36 tools; the table's intro names only the items that follow the 3D view's rules.

- [x] **HLP-249 · A `cast` hides the None `newPropertyGraph` may give** · `mcp_server/designer_helpers/functions.py:472`, `mcp_server/designer_helpers/graph_inputs.py:133` · confirmed · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** `cast(SDGraph, node.newPropertyGraph(...))` takes a result sd's stub types `Optional`, and Designer
    gives None on a curve's or a gradient's parameters (HLP-244). Today `_target_of` refuses those first, and a
    string parameter is unmeasured.
  - **Scenario.** A parameter that has a getter but gives None makes `set_function` fail with "'NoneType' object has
    no attribute 'getNodes'". Nothing changes in the graph.
  - **Fix.** Refuse with a message naming the parameter when the result is None, in both places.
  - **Resolution: done**.
    - **Test:** `test_a_parameter_newpropertygraph_makes_no_function_on_is_refused_naming_it` and
      `test_expose_refuses_a_parameter_newpropertygraph_makes_no_function_on` (`test_set_function.py`) failed first
      with "'NoneType' object has no attribute ...".
    - **Cause:** `cast(SDGraph, node.newPropertyGraph(...))` hid the None sd's stub allows.
    - **Fix:** `_new_function_graph` (`graph_inputs.py`) refuses with "`<node>.<parameter>` takes no function:
      Designer's newPropertyGraph made none", for `set_function` and `expose_param`. The take-backs leave nothing.
    - **Also covered:** these are the only two `newPropertyGraph` calls.

- [x] **TST-758 · `$pos` in a parameter's function: the sentences say more than the cells measure, which may fail at random** · `mcp_server/GUIDE.md:295-297`, `mcp_server/server_tools/functions.py:38-39`, `tests/test_all_tools/functions/checks.py:356-361`, `tests/test_all_tools/functions/designer_scripts/function_nodes.py:606-619` · confirmed · follows SRV-214, generation 3 · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** The cells read `$pos.c + 0.5` through an 8-bit blend and pass at 0.50 or less, so they can't tell 0
    from a negative, nor a negative from NaN. GUIDE says "x read 0 in every run" and "below 0", and the Field "0, or
    below 0 at random". A value 0 in most runs and not in others looks unset, and an unset value can be positive.
  - **Scenario.** In the full run, an unset `$pos.y` reads 0.002 or more and the check fails. An agent reads "0, or
    below 0" and relies on it.
  - **Fix.** At generation 3, narrow: the Field says only that `$pos` isn't the pixel's there, and to use it in a
    Pixel Processor's; GUIDE says what was read. The cells assert only that the read isn't the pixel's position.
  - **Resolution: done**. Narrowed, at generation 3, with no new check: the cells read `$pos.x` and `$pos.y` in a
    blend's `opacitymult` and pass when neither is the pixel's (0.69, 0.31), whatever else they read. `EXPRESSION`
    says only that `$pos` isn't the pixel's in a parameter's function, and to use it in a Pixel Processor's, and
    GUIDE.md says what the check measures. A fresh Designer and the same one: 12 checks, exit 0, twice.

- [x] **AGT-125 · The test lesson missed two statements of the rule, and one kind of test reading the source** · `README.md:299`, `.claude/skills/live-check/SKILL.md:138`, `.claude/rules/python.md:24-28` · confirmed · found 2026-11-22 by a reviewer (Opus)
  - **Defect.** README says "While working, run the tests you added or changed", and the `live-check` skill says the
    developer "reruns only the failing tests". Both contradict the widened rule. `python.md`'s list of where to find
    the tests reading a change's source leaves out `repo_files()` (`test_constants.py`).
  - **Scenario.** A fix after a failed final check edits a helper and skips `test_library_refusal.py`, as in TST-754.
  - **Fix.** Add the widening to both, pointing to `.claude/rules/python.md`, and `repo_files()` to its list.
  - **Resolution: done**. Docs only, the docs tests passing: README.md and the `live-check` skill add the unit tests
    reading the source of the files changed, pointing to `.claude/rules/python.md`, whose list gains `repo_files()`
    (`tests/unit/docs_text.py`).

- [x] **SRV-218 · `describe_graph`'s new hint leads back to the same refusal** · `mcp_server/designer_helpers/describe_functions.py:84-86` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** "describe the node in its graph with node_ids=['3']" answers a call that has `node_id`, and any call
    with `node_id` goes to `describe_function`, where `node_ids` only focuses the function's nodes.
  - **Scenario.** The agent adds `node_ids=['3']`, keeps `node_id='3'`, and gets the same refusal.
  - **Fix.** Name the call: `describe_graph` with `node_ids=['3']` and no `node_id`, with its unit test's text.
  - **Resolution: done**.
    - **Test:** `test_describing_a_node_with_no_function_of_its_own_names_node_ids`, with the new text, failed first.
    - **Fix:** the hint says "or describe the node in its graph: describe_graph(node_ids=['3']), with no node_id".

- [x] **SRV-219 · The `$pos` refusal's way round, through a function graph, is said only in GUIDE's scripting part** · `mcp_server/server_tools/functions.py:38-41`, `mcp_server/GUIDE.md:296-299` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** A function graph reading `$pos`, called from a Value Processor's or a parameter's function, compiles
    and builds: `Resource` carries no flag for `$pos`, as it does `samples`. `EXPRESSION`, which an agent reads, says
    `$pos` is refused there. No test shows the call is taken.
  - **Scenario.** An agent puts its `$pos` maths in a function graph and calls it from a blend's `opacitymult`,
    getting a value that isn't the pixel's, with no word.
  - **Fix.** One clause in `EXPRESSION`, and a compiler unit test of such a call compiling. Refusing the call, with
    `$pos` tracked through calls as `samples` is, is a ROADMAP item if the user wants it.
  - **Resolution: done**. Coverage and docs: `test_a_call_to_a_function_graph_reading_pos_compiles_wherever_it_is`,
    over a Value Processor's and a parameter's function, shows the call taken. `EXPRESSION` says "a function graph
    reading it, called from those, isn't checked", and so does `compile_expression`'s docstring. Refusing the call is
    a question for the user.

- [x] **SRV-220 · ROADMAP's items 115, 123 and 124 leave out what is known** · `ROADMAP.md` (items 115, 123, 124) · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.**
    - Item 115: FX-Map nodes' parameters read `$pos` in most shipped FX-Maps (`switch` 117 times, `opacity` 9 in the
      packages), and the compiler now refuses `$pos` in a parameter's function. The shipped packages also read
      `$depthpow2`, named nowhere.
    - Item 123: no shipped package reads `$physicalsize`, whose name came from a review's claim that was wrong, and the
      item says to measure what it gives, not whether it exists.
    - Item 124: its figures come from one agent probe recorded only in PLAN.md, which leaves with the branch. And
      `open_graph`'s `node_id` focuses `views[0]`, the oldest view, if views pile up.
  - **Scenario.** Item 115 is planned without lifting the `$pos` refusal for FX-Map parameters, and then refused on
    their most common variable.
  - **Fix.** Item 115: lifting the `$pos` refusal for an FX-Map's parameters, and `$depthpow2` with `$depth` and
    `$number`. Item 123: first check that `$physicalsize` exists. Item 124: the figures as one probe of
    2026-11-22, and `views[0]` to check.
  - **Resolution: done**. ROADMAP only, 116 rows before and after: item 115 also lifts the `$pos` refusal for an
    FX-Map node's parameters, with the review's counts, and adds `$depthpow2` (2 reads in the shipped packages); item
    123 first checks that `$physicalsize` exists; item 124 gives its figures as one probe of 2026-11-22, and names
    `open_graph`'s `views[0]` to check.

- [x] **TST-759 · No test sends `$pos` through `set_function` into a function graph's expression** · `tests/unit/test_function_compiler.py`, `mcp_server/server_tools/functions.py:333` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** GUIDE and the compiler's docstring say `set_function` takes `$pos` in a function graph's expression.
    The only test calls the compiler with `kind=None`, and `_set_resource` passes no `kind` untested.
  - **Scenario.** A change passing a kind from `_set_resource` refuses `$pos` in every function graph, and no test
    fails.
  - **Fix.** A unit test of `set_function('$pos.x', function=...)` being built.
  - **Resolution: done**. Coverage: `test_a_function_graphs_expression_reads_pos` sends `set_function('$pos.x',
    function='paint')` through the server's fakes, built and compiled with no kind.

- [x] **TST-760 · The Value Processor's `$pos` row can't see that its graph stayed unchanged** · `tests/test_all_tools/functions/checks.py:1630-1636` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** With no node to read pixels from, the row compares the whole graph's `describe_graph`, which shows a
    Value Processor's function as "<- a function" whatever it holds. The label says the graph is unchanged.
  - **Scenario.** None today: the refusal is raised before any call reaches Designer, and the row's error half fails
    without it. The label claims more than the row reads.
  - **Fix.** Compare `describe_graph(node_id=ctx.vp)`, which lists the function's nodes, before and after.
  - **Resolution: done**. Coverage: the refusals check's state holds the whole graph's `describe_graph` and
    `describe_graph(node_id=ctx.vp)`, so every row guards the Value Processor's function. Scratch run: 16 checks,
    exit 0, twice.
