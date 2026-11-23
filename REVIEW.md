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

**Last used:** PLG-45, SRV-242, HLP-253, INS-46, TST-789, AGT-125.

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
| Low-medium | 0 | 6 |
| Low | 0 | 49 |
| **Total** | **0** | **55** |

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
| 2026-11-22, Steps 1 and 2 (Gradient Map keys, Curve points) | Opus (developer) | 1 | 1 [1 Low] | 0 | 595,301 | 52 min |
| 2026-11-22, the first review (Steps 1 and 2) | Sonnet | 3 | 11 [2 Low-medium, 9 Low] | 11 [2 Low-medium, 9 Low] | 619,179 | 12 min |
| 2026-11-22, the first review (Steps 1 and 2) | settling | 1 | 0 | 0 | 127,354 | 4 min |
| 2026-11-22, the first review's fixes | Opus (developer) | 1 | 0 | 0 | 121,784 | 22 min |
| 2026-11-22, the second review (the first review's fixes) | Sonnet | 2 | 5 [5 Low] | 5 [5 Low] | 359,016 | 8 min |
| 2026-11-22, the second review's fixes | Opus (developer) | 1 | 0 | 0 | 42,594 | 8 min |
| 2026-11-22, Step 3 (`analyze_reference`, the palette) | Opus (developer) | 1 | 0 | 0 | 376,160 | 34 min |
| 2026-11-22, the third review (Step 3) | Sonnet | 3 | 7 [1 Low-medium, 6 Low] | 7 [1 Low-medium, 6 Low] | 469,255 | 8 min |
| 2026-11-22, the third review (Step 3) | settling | 1 | 0 | 0 | 75,188 | 2 min |
| 2026-11-22, the third review's fixes, and three additions | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 163,683 | 25 min |
| 2026-11-22, the fourth review (the third review's fixes) | Sonnet | 2 | 5 [1 Low-medium, 4 Low] | 5 [1 Low-medium, 4 Low] | 304,308 | 8 min |
| 2026-11-22, the fourth review (the third review's fixes) | settling | 1 | 0 | 0 | 124,808 | 5 min |
| 2026-11-22, the fourth review's fixes | Opus (developer) | 1 | 0 | 0 | 66,443 | 12 min |
| 2026-11-22, the fifth review (the fourth review's fixes) | Sonnet | 1 | 3 [3 Low] | 3 [3 Low] | 163,304 | 8 min |
| 2026-11-22, the fifth review's fixes | Opus (developer) | 1 | 0 | 0 | 65,734 | 12 min |
| 2026-11-22, Step 4 (photo to Gradient Map) | Opus (developer) | 1 | 2 [1 Low-medium, 1 Low] | 2 [1 Low-medium, 1 Low] | 456,792 | 34 min |
| 2026-11-22, the sixth review (Step 4) | Sonnet | 2 | 5 [5 Low] | 5 [5 Low] | 363,557 | 9 min |
| 2026-11-22, the sixth review (Step 4) | settling | 1 | 0 | 0 | 140,528 | 9 min |
| 2026-11-22, the sixth review's fixes | Opus (developer) | 1 | 0 | 0 | 107,193 | 18 min |
| 2026-11-23, the seventh review (the first Opus round, the whole branch) | Opus | 4 | 9 [1 Low-medium, 8 Low] | 9 [1 Low-medium, 8 Low] | 969,971 | 14 min |
| 2026-11-23, the seventh review (the first Opus round, the whole branch) | settling | 1 | 0 | 0 | 109,294 | 3 min |
| 2026-11-23, the seventh review's fixes | Opus (developer) | 1 | 0 | 0 | 153,673 | 30 min |
| 2026-11-23, the eighth review (an Opus round on the seventh review's fixes) | Opus | 2 | 3 [3 Low] | 3 [3 Low] | 437,602 | 15 min |
| 2026-11-23, the eighth review's fixes | Opus (developer) | 1 | 0 | 0 | 51,256 | 11 min |
| 2026-11-23, the ninth review (the second Opus round, the whole branch) | Opus | 4 | 4 [4 Low] | 4 [4 Low] | 988,719 | 15 min |
| 2026-11-23, the ninth review's fixes | Opus (developer) | 1 | 0 | 0 | 70,873 | 14 min |
| **Total** | | **40** | **56 [6 Low-medium, 50 Low]** | **55 [6 Low-medium, 49 Low]** | **7,523,569** | **392 min** |

## Review log

### 2026-11-22: the first review, branch `gradient-palette`, Steps 1 and 2 (ROADMAP item 116)

- **Scope:** `git diff 40545a1 46312fa -- . ':(exclude)PLAN.md'`: Gradient Map keys and Curve points through
  `apply_edits`' `set`, their read-back, the "designer facts" check `params/designer_scripts/keys.py`, the live checks
  in `params` and `undo`, GUIDE, README and ROADMAP.
- **How:** three Sonnet reviewers: the helpers' and the server's code with `tests/unit/test_keys.py`; the live
  self-test and its unit tests; the docs and the step's approved text, point by point. No tests run. One scratch probe,
  by the runner on port 9895: 17 curves, each flagged one beside its twin (every flag off, each broken side's handle on
  its point) and its unflagged copy, on a 256 px float ramp. Flagged and twin were identical in every cell; a broken
  side facing a segment changed the output by up to 0.324, one facing none by 0; Designer's own `grunge_damas.sbs` and
  `noise_fractal_sum_base_v2.sbs` curves matched their twins. So `_shown_keys`'s per-side rule holds (TST-763 keeps
  the facts check's gap). Settled as wrong, or not worth a fix:
  - `fmt` rounds the keys to 4 decimals: a read-back set again moves a value by under 5e-5, far below an 8-bit step,
    and it is the form `fmt` gives every float;
  - an integer like `10**400` escapes `_number` as an `OverflowError`: no agent sends one, and the node is unchanged;
  - two `EASED` values lie 5e-6 from a 3-decimal boundary: the strings match the exact Bezier solution, on the one
    engine the self-test runs;
  - `interpmode` 2 and `smoothness` unmeasured, no live set of `interpmode`, and the midpoint refused outside 0..1: the
    docs give only their types and defaults, `set` of an int parameter is checked already, and the midpoint's range is
    chosen, not claimed as a fact;
  - the struct ids named in `core.py`: they pick the shape; each key is built from the parameter's own item type, as
    the step asks;
  - `functions.py`'s and `remove_graph_input`'s `_make_value` calls: a `__constant__` and a graph input are never
    arrays;
  - `_make_value`'s array branch has no unit test: it is sd code, which the live checks run;
  - the one-Undo check in `undo`, not `params`: the lead's choice, asked by the developer, as the `undo` category
    opens its graph in the editor and `params` doesn't (DECISIONS.md, "A category's preparation opens its graph in the
    editor only where its checks read the editor");
  - `set`'s result prints every key twice for a 256-key gradient: setting that many is rare, and the short form the
    step asks is `describe_graph`'s;
  - `describe_graph`'s `()` default for every array: only the atomic Gradient Map and Curve take arrays, and a graph
    input can't be one;
  - `expose`'s text doesn't say arrays are refused: its refusal says so.
- **Not verified:** none.
- **Resolutions assessed:** none (the branch's first review).
- **Findings:** HLP-250, TST-761 (Low-medium); SRV-221, TST-762, SRV-222, TST-763, HLP-251, HLP-252, TST-764,
  TST-765, TST-766 (Low). Merged: HLP-250 (two reviewers), TST-761 (two), TST-763 (three), HLP-251 (two), HLP-252
  (two). SRV-222 was the developer's suspicion too.
- **Suggested order:** HLP-250 and TST-761, then SRV-221 and TST-762 (the docs an agent reads), then the rest.
- **Unspecified** (no doc decides; for the user when the reviews converge):
  - whether a gradient position or a curve x above 1 should be refused, as now, though Designer computes it;
  - whether `set` should keep each point's `isLocked` and broken flags (HLP-251);
  - whether any tool should read a gradient of more than 16 keys (HLP-250's fix proposes `describe_graph` focused on
    the node).
- **Checked and found fine:** every key is checked before anything is built or set, each refusal names its key and
  leaves the node unchanged, a good array beside a bad one included; alpha, a midpoint, handles and an empty array
  round-trip through `fmt` and `_given_keys`; `sweep_param`'s put-back (the value read is a copy, read before the
  sweep); `faked_helpers`' plain `SD*` classes keep the older tests' `MagicMock`s working; each Step 1 question has a
  cell, each compared as an exact string; the grey-ramp checks compare all four channels at five bands; the nine
  refusal strings match what the code raises; `said`, `expect`, `near`, `CLOSE` and `described` moved unchanged; the
  `params` preparation's new nodes change no older check; the undo check fails without the change and cleans up in a
  `finally`.

### 2026-11-22: the second review, branch `gradient-palette`, the first review's fixes

- **Scope:** `git diff c9ab8da 89df52c -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the helpers', the server's and their unit tests' part; the live self-test's, its
  unit tests' and the docs' part. No tests run, no probes. Every suspicion settled by reading; the Pillow refusal of a
  multi-line `textlength` read in its source, and Adobe's sample read at its line 96. Not raised:
  `tuple[float, float]` for a point's members (they are built and compared as lists, a small gain); `categories.py`
  giving `params`' time with its server's start (the order holds either way); a GUIDE sentence's "It" (style).
- **Not verified:** none.
- **Resolutions assessed:** all 11. HLP-250, SRV-221, HLP-251, HLP-252, TST-761, TST-765 and TST-766 hold. Questioned:
  SRV-222 (SRV-223), HLP-250's docs (SRV-224), TST-764 (TST-767), TST-763 (TST-768), TST-762 (TST-769).
- **Findings:** SRV-223, SRV-224, TST-767, TST-768, TST-769: 5 Low, all generation 2. Merged: SRV-224 (two
  reviewers), TST-769 (two). The longest chains are at generation 2. A few Lows: the reviews of Steps 1 and 2 are
  done once the developer fixes them.
- **Suggested order:** SRV-223, TST-767, then the docs and comments.
- **Checked and found fine:** `count <= KEYS_SHOWN or node_ids`, and no other tool prints an array cut; the
  TypedDicts and the cast left in `_new_keys`; `compare.py`'s `_labelled` calls, which pass no short label; the new
  broken-side cells' expected strings, recomputed by hand; the focused-listing live check, the empty-list check and the
  expose clean-up, each failing without what it guards; REVIEW.md's tables.

### 2026-11-22: the third review, branch `gradient-palette`, Step 3 (ROADMAP item 119, `analyze_reference`)

- **Scope:** `git diff b605b83 a13d0be -- . ':(exclude)PLAN.md'`.
- **How:** three Sonnet reviewers: the palette's method and its unit tests; the tool's surface and the code it shares
  with `compare_to_reference` and `sweep_param`; the live check, the docs and the step's approved text, point by
  point. No tests run. Settled by reading, Pillow's and mcp's sources included, but for one runner's probe (below).
  Not worth a fix, or not a defect:
  - NEAREST sampling at an exact step of 2 keeps one phase of a 1-pixel pattern: a photo with a period equal to the
    sampling step is improbable, and averaging is ruled out by the step (it blends colours);
  - the dynamic programming's pixel weights pinned by no test: the round trip and the `polyfit` test pin the choice
    and the fit;
  - the `keys` Field's literal 64 beside `_LEVELS`; the head line giving the region's size, as `compare_to_reference`
    does;
  - the clip to 0..1 after an unconstrained least squares, and "the best one Gradient Map can do": the printed error
    is the clipped keys', and the docstrings say what the code does.
- **Not verified:** none.
- **Resolutions assessed:** none in scope (no earlier finding's fix is in this diff).
- **Findings:** SRV-225 (Low-medium); SRV-226, SRV-227, SRV-228, SRV-229, SRV-230, TST-770 (Low). Merged:
  SRV-225 (two reviewers), SRV-226 (three), SRV-228 (two), SRV-229 (two).
- **Probe:** the runner's, on Pillow 13.0.0 in the venv: `resize(..., NEAREST)` works on `I;16`, `I`, `F`, `L`, `LA`,
  `RGB`, `RGBA` and `P` with a transparency, keeping 16-bit values and only the source's own pixels; `analyze_reference`
  gave a palette for a 2048x1024 16-bit grey PNG with and without a region, and for `I`, `F`, `P` and `LA` images over
  1 MP. Not a defect.
- **Suggested order:** SRV-225, SRV-226, SRV-229, then the rest.
- **Unspecified** (for the user when the reviews converge): what `analyze_reference` does with NaN or infinite pixels
  of a float image (mode `F` TIFFs only): today a NaN gives NaN keys, and an infinite pixel may raise.
- **For later** (for the user when the reviews converge, as ROADMAP items): `_open_reference` doesn't apply a photo's
  EXIF orientation, so a phone photo stored rotated is read, and its `reference_region` taken, in the stored frame,
  for `compare_to_reference` too (not this diff).
- **Checked and found fine:** `compare_to_reference` unchanged for every mode and region, its messages included
  (`_load_reference` line by line, `_opaque` against both old sites); `_rgb` and `_to_display` identical for every
  layout; the hints, the `get_guide` gate, the `HINTS`, `_FIXED` and `_REQUIRED` rows, no other table needing one;
  README's count and rows; the end levels always held and the positions strictly increasing; `_knots`' recurrence and
  backtracking; `_fit`'s normal equations and its independent `np.interp` error; the edge cases (a flat image, one
  pixel, `keys` 1, fewer levels than keys, a grey image, a fully transparent one); the live check failing without each
  behaviour it reads; the claim's points each delivered, SRV-225 partly.

### 2026-11-22: the fourth review, branch `gradient-palette`, the third review's fixes and three additions

- **Scope:** `git diff 273c86b 31bdf96 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the palette's part (`reference.py` and its tests); the shared image code
  (`measure.py`, `compare.py`, `output.py`), the helpers' comments and their tests. No tests run. One runner's probe,
  Pillow only (SRV-232). Not raised: the `str` layouts of `_channel_names`, `_channel_summary`, `_compare_channels` and
  its `luma`, functions this branch doesn't change (`.claude/rules/python.md` asks it of a changed function); a TIFF
  turned twice on an older Pillow (the venv's Pillow 13 applies a TIFF's orientation once and drops the tag; a venv
  is built with the latest); two long docstring lines (style); GUIDE's "with its fit error" (the tool's docstring is the
  source).
- **Not verified:** none.
- **Resolutions assessed:** SRV-225, SRV-226, SRV-227, SRV-228, SRV-229, SRV-230 and TST-770. SRV-226, SRV-228,
  SRV-229, SRV-230 and TST-770 hold; SRV-227 holds, its test gap in TST-771. Questioned: SRV-225 (SRV-233, SRV-234,
  TST-771).
- **Findings:** SRV-232 (Low-medium, measured); SRV-233, SRV-234, TST-771, HLP-253 (Low). SRV-231 (the developer's)
  stays open, for the same round of fixes. The third review's "For later" EXIF item was fixed in the branch on the
  user's word (PLAN.md), which SRV-232 now follows up. The longest chain: SRV-225's, at generation 2.
- **Suggested order:** SRV-232, SRV-231, SRV-233, SRV-234, then the tests and comments.
- **Checked and found fine:** the nested fits before the clip (one key, the chosen keys, every level), and
  `np.interp`'s clamp against `_fit`'s; the finite mask joined with the opaque one, and its refusal; the 32-bit scale
  from the whole image, for a region and a sample; `compare_to_reference`, `preview_maps` and `preview_node` unchanged
  for every mode but for SRV-232; a Designer render and a map carrying no orientation; the rotated photo's test; the
  `PixelLayout` conditionals; the new tests each failing without what they guard.

### 2026-11-22: the fifth review, branch `gradient-palette`, the fourth review's fixes

- **Scope:** `git diff eadb3e0 9572684 -- . ':(exclude)PLAN.md'`.
- **How:** one Sonnet reviewer over the whole round (a small diff). No tests run, no probes. Every suspicion settled
  by reading, Pillow 13's `exif_transpose` included. Not raised: the docstring's line breaks (style). Two Unspecified
  items, decided by the lead under the user's word of 2026-11-22 ("do as you consider best for an agent ... not
  complicte the code too much"): the clip to 0..1 prints no count of the values it clipped (float references are rare,
  and the docstring says so); no tool text says a region is taken in the EXIF-oriented view (an agent picks a region
  from the photo as it views it, which is that view).
- **Not verified:** none.
- **Resolutions assessed:** SRV-231, SRV-232, SRV-233, SRV-234, TST-771, HLP-253. All hold but SRV-232, whose code holds
  and whose docs and test are questioned (SRV-235, TST-772). TST-771's docstring: a note (generation 3, a test's
  wording).
- **Findings:** SRV-235, TST-772, SRV-236 (Low). A few Lows: Step 3's reviews are done once they are fixed. The longest
  chains are at generation 2.
- **Suggested order:** SRV-236, SRV-235, TST-772.
- **Checked and found fine:** the catch-all leaves an image untouched on a failed read and turned and consistent on a
  failed write; the rotated-photo test would go red if the catch-all hid a broken rotation; the non-finite refusal
  after the cut, only for mode `F`, its count and message, its test failing if the check moved before the cut; the
  clip feeding every value printed; the reading line's fragments asserted verbatim; the new functions' types.

### 2026-11-22: the sixth review, branch `gradient-palette`, Step 4 (photo to Gradient Map)

- **Scope:** `git diff 353c668 c3910a4 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the server's code and the unit tests; the live checks, the docs and the step's
  approved text, point by point. No tests run. One reviewer read 12 lines of PLAN.md by a slip and set them aside,
  judging each claim from the code; the other ran a read-only inline Python on a Designer package, then grep. One
  runner's probe, of the developer's new problem (SRV-237). Not raised, or not worth a fix:
  - the set text's trim is 21% shorter, not "about a third": the figure was the lead's estimate, every fact it named
    moved to GUIDE once, and what stays is what the text was to keep;
  - the spike test's margin (about 2.03 against 2, by hand): it is deterministic and passes;
  - "or with it transparent" not saying how: no tool is needed for the advice;
  - `compare_to_reference`'s Rec.709 luma beside the palette's mean grey: each result names its weights;
  - the set text's ranges tied to the refusals by no test: as before the trim, and each refusal names its range.
- **Not verified:** none.
- **Resolutions assessed:** none in scope.
- **Findings:** SRV-237 (Low-medium, measured, the developer's); TST-774, TST-775, TST-776, TST-777, TST-778 (Low).
  Merged: TST-777 (two reviewers), TST-778 (two). TST-773 (the developer's) stays open for the same fixes. A few Lows:
  Step 4's reviews are done once these are fixed; then the Opus rounds on the whole branch.
- **Seen:** the runner's Designer on port 9895 crashed on quit, `mutex lock failed` in stlab's `system_timer`
  during teardown, kept alive by Adobe's crash window (ROADMAP item 95, its second sighting). The user's Designer was
  not involved.
- **Suggested order:** SRV-237, TST-774, TST-777, TST-775, then the rest.
- **Checked and found fine:** the moves verbatim, with no import circle, `MODULES` and re-exports right, every caller
  getting what it got; no Rec.709 left for the palette; `compare_to_reference` keeping `_LUMA`; the set text keeping
  the shape, ranges, defaults and read-back, each moved fact in GUIDE once; `check_designer_greys` discriminating
  Rec.601, Rec.709, Desaturation, Max and Min from the mean; the photo path's error within 0.002 of a fit error above
  0.01, which a wrong grey would miss; ROADMAP 116 and 119's notes against their code and checks; the new checks'
  clean-up.

### 2026-11-23: the seventh review, the first Opus round on the whole branch

- **Scope:** `git diff main...HEAD -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'` at 43f86e5, with REVIEW.md as the
  record.
- **How:** four Opus reviewers: item 116's code; item 119's code and the image reading; the live self-test; the docs
  and the approved text, point by point. No tests run. One runner's probe, port 9895 (SRV-238, SRV-239); its Designer
  closed cleanly. Not raised, or not worth a fix:
  - `_shown_keys` reading a plain dict: it is built from Designer's own member list, so a TypedDict there is a cast;
  - `sweep_param` naming the key but not which of its values holds it: older than the branch, for every type, and the
    agent can scan its values;
  - "which computes the same" for a broken side now in the scripting part only: a read-back set again gives the
    same curve either way;
  - `compare_to_reference` decoding a reference whole to float64: older than the branch, a change of its behaviour,
    not of this branch's work;
  - a CIELab TIFF Pillow may not convert: unverified and rare;
  - `_compare_channels` and `_channel_summary`'s `str` layouts: functions the branch doesn't change.
- **Not verified:** none.
- **Resolutions assessed:** every resolved entry whose fix is in the branch. All hold but those questioned: SRV-237
  (SRV-239), TST-777 (TST-781), TST-764 (TST-783), TST-778 (TST-780, and a note on its resolution's wording). TST-763's
  per-side claim holds through TST-768's cell, not its own (a note of the reviewer's, not a finding).
- **Findings:** SRV-238 (Low-medium, measured); SRV-239 (measured), SRV-240, TST-779, TST-780, TST-781, TST-782, TST-783,
  TST-784 (Low). Merged: SRV-238 (two reviewers), SRV-239 (two), TST-781 (two). More than a few Lows and one above:
  the developer fixes them, Opus rounds review the fixes, then the whole branch again. The longest chains are at
  generation 2.
- **Suggested order:** SRV-238, SRV-239, TST-781, TST-784, TST-783, then the rest.
- **Checked and found fine:** every shape read back taken again by `set` with the same keys; every caller of the
  changed helpers; the refusals checked before anything is built; the palette's method, nested fits and result lines;
  every image mode through the opener against main for the four tools; the errors a user's file can raise, each a
  `ToolError` naming its cause; each facts cell telling Designer's behaviour from an alternative; the tolerances; the
  clean-ups; the moved helpers; each point of the approved text delivered but for the findings above.

### 2026-11-23: the eighth review, an Opus round on the seventh review's fixes

- **Scope:** `git diff 3ce13b9 5a2437c -- . ':(exclude)PLAN.md'`.
- **How:** two Opus reviewers: the server's code and the unit tests; the live checks, GUIDE and the docs. No tests run,
  no probes: each suspicion settled by reading. Not raised, or not worth a fix:
  - a TIFF whose orientation is only in its XMP, which older Pillow versions turn too: rare, the installed Pillow is
    13, and handling it would complicate the opener;
  - Pillow's `TypeError` on a TIFF whose XMP tag has an odd type: Pillow's own, older than the branch, unverified;
  - `categories.py`'s times measured with or without the server's start, about 2 s apart: within the spread;
  - the example's docstring (`examples/build_dwarf_trimsheet.py`) repeating a GUIDE sentence, and where a check's data
    table sits;
  - `check_a_bitmap_turns_a_jpeg_by_its_orientation_and_no_other_format`'s "finds them equal" against its RMSE under
    0.01: the same sentence says a JPEG's colours are within a step or two;
  - a JPEG's mirrored orientations: folded into SRV-241's narrowing.
- **Unspecified:** where the note on 16-bit PNGs in PIL belongs ("grayscale 16-bit PNGs load in PIL as `I;16` ...
  16-bit RGBA PNGs as 8-bit"), which TST-782's fix moved out of the core: an agent reading a 16-bit PNG through the
  tools needs it. The lead's choice, under the user's word of 2026-11-22 ("do as you consider best for an agent using
  this mcp at work and to not complicte the code too much and to not add to decisions"): back in the core, Rendering
  and verifying, about 120 characters.
- **Not verified:** none.
- **Resolutions assessed:** the seventh review's 9. All hold but SRV-238 (SRV-241, TST-786, and a note on its Probe's
  wording), TST-781 (TST-785) and TST-779 (TST-786).
- **Findings:** SRV-241, TST-785, TST-786 (Low). Merged: SRV-241 (two reviewers). A few Lows: the developer fixes them,
  then an Opus round on the entire branch. The longest chain still growing: TST-777 → TST-781 → TST-785, generation 3.
- **Suggested order:** SRV-241, TST-785, TST-786.
- **Checked and found fine:** `_STORED` is the exact inverse of `exif_transpose`'s table (2, 3, 4, 5 and 7 undo
  themselves, 6 by `ROTATE_90`, 8 by `ROTATE_270`); both of Pillow's TIFF load paths end in `load_end`, which turns the
  image and drops the tag; the other resolutions of the seventh review.

### 2026-11-23: the ninth review, the second Opus round on the whole branch

- **Scope:** `git diff main...HEAD -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'` at 310b4e5, with REVIEW.md as the
  record.
- **How:** four Opus reviewers: item 116's code; item 119's code and the image reading; the live self-test; the docs
  and the approved text, point by point. No tests run, no probes: each suspicion settled by reading. Not raised, or
  not worth a fix:
  - `_opaque`'s return type as a union of two tuples: its two callers unpack it and test each item, so mypy gains
    nothing there;
  - the `# type: ignore[attr-defined]` at `params/designer_scripts/keys.py:71`: it copies main's
    `designer_helpers/core.py:296`, and its reason holds;
  - the comment at `params/checks.py:361-362` on the curve order: a test comment at generation 4, the `CHANNELS` table
    above it saying what "its channels" are (two reviewers);
  - ROADMAP item 116's Done note saying `describe_node` reads the keys back, and the bitmap op's "(50x10 computes
    64x16)" also in GUIDE's scripting part: the approved text's wording, and two places that agree;
  - the helpers' docstrings restating GUIDE facts as measured: they agree with GUIDE, a pattern of the project;
  - SRV-233's flat swatch, where every error is 0: the same result says it holds 1 of the 64 levels;
  - `output._image_size` opening a file with Pillow directly: its files are the ones `sbsrender` just wrote, with no
    orientation.
- **Unspecified:** a reference photo's embedded ICC profile, such as a phone's Display P3. The tools read the stored
  values as sRGB, as `compare_to_reference` did on main; whether Designer's bitmap node applies the profile is
  unmeasured, and no doc decides. The user, 2026-11-23: "ok leave the icc profile as it is"; `_open_image`'s
  docstring says so, citing the user, with a unit test.
- **Not verified:** none.
- **Resolutions assessed:** every resolved entry whose fix is in the branch. All hold but SRV-238 (TST-787), SRV-241
  (TST-788) and TST-786 (a note on its Also covered).
- **Findings:** SRV-242, TST-787, TST-788, TST-789 (Low). A few Lows: the reviews look converged once the developer
  fixes them. The longest chains: TST-777 → TST-781 → TST-785, generation 3, no longer growing; SRV-238 → SRV-241 →
  TST-788, generation 3.
- **Suggested order:** TST-787, TST-788, SRV-242, TST-789.
- **Checked and found fine:** every shape read back taken again by `set`, every shipped `.sbs` key within the ranges
  `set` takes (6,657 gradient midpoints, all 0); `describe_graph`'s cut and its precedence; `sweep_param`'s short
  labels; the palette's levels, knots, fit and nested errors, its edge cases (a flat image, one pixel, one key, many
  keys, equal percentiles); the opener against Pillow 13's TIFF load paths and every image mode against main; each
  facts cell telling Designer's behaviour from an alternative; the checks' clean-ups and their independence from
  earlier checks; each new GUIDE sentence against its test; each point of the approved text delivered.

---

## High

## Medium-high

## Medium

## Low-medium

- [x] **HLP-250 · A gradient of more than 16 keys can't be read by any tool, and the set text says the keys read back** · `mcp_server/designer_helpers/describe.py:130-134` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** `cur, default = fmt(value) if count <= KEYS_SHOWN else '<%d keys>' % count, ()`. The set text
    (`server_tools/edits.py:110`) says "the result and describe_graph(include_params) read them back in this shape",
    and GUIDE's core bullet says so too. Only GUIDE's scripting part names the cut.
  - **Scenario.** A user's Gradient Map holds 40 keys. `describe_graph` shows `gradientrgba = '<40 keys>'`, and no
    read-only tool gives the keys: `set`'s result prints them only as the old value of a write that replaces them. The
    agent can't change one key without `execute_designer_code`.
  - **Fix.** Show every key when `node_ids` focuses on the node, keeping the count in a whole graph's listing. Say the
    cut, and how to read every key, in the set text and GUIDE's core bullet.
  - **Resolution: done**.
    - **Test:** `test_keys.py::test_describe_graph_focused_on_the_node_shows_every_key` and the live
      `check_describe_graph_shows_every_key_of_a_node_it_focuses_on` failed on 17 keys, the focused read giving
      `'<17 keys>'`.
    - **Cause:** `describe.py` cut every listing past `KEYS_SHOWN`, a focused one too.
    - **Fix:** `count <= KEYS_SHOWN or node_ids`. The set text and GUIDE's core bullet say that past 16 keys a whole
      graph's listing gives their count, and `node_ids` on the node gives every key.
    - **Also covered:** `describe_node` shows a new node's default, which has no keys; `set`'s result gives every key
      already.
  - Questioned by SRV-224 (2026-11-22).

- [x] **TST-761 · Three documented set behaviours run in no live check: a midpoint, `[]` removing the keys, a curve's read-back set again** · `tests/test_all_tools/params/checks.py` (`check_set_gradient_keys`, `check_set_curve_points`) · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** The set text says "an optional third item is the midpoint", "[] removes them", and that the result and
    `describe_graph` read the keys back in the shape `set` takes. In the live self-test, the only set with a midpoint
    is refused (`checks.py:430`), `[]` is set only through sd in the facts script, and `check_set_curve_points` never
    sets `INVERT_READ` or `EASE_READ` again (only the gradient's read-back is, `checks.py:391-395`).
    `tests/unit/test_keys.py`'s docstring says the params checks build them in Designer.
  - **Scenario.** `_new_keys` writes `members['midpoint']` and builds an empty `SDValueArray` for `[]`. A wrong member
    id, or an empty array Designer doesn't take, passes `test_keys.py`'s fakes, and no live check fails.
  - **Fix.** In `check_set_gradient_keys`, give one key a midpoint, read back as `(..., 0.25)`, and set the read-back
    again. In `check_set_curve_points`, set the read-back again, and set `[]` on both nodes and read no keys back.
  - **Resolution: done**.
    - **Test:** three temporary mutations of the helpers, put back after: `_new_keys` skipping the midpoint made the
      result and read-back checks of `check_set_gradient_keys` fail, now that `KEYS`' middle key has midpoint 0.25;
      the curve read-back with its handles swapped made `check_set_curve_points`' new "set again unchanged" fail, for
      both read-backs; `_given_keys` refusing `[]` made the new `check_set_an_empty_list_removes_every_key` fail.
    - **Cause:** the checks never passed those values through `apply_edits`.
    - **Fix:** the checks above; the code already worked. The empty-list check runs after the sweep and the expose
      check, so the sweep still runs on real keys.

- [x] **SRV-225 · analyze_reference's two errors come with no scale and no rule for acting on them, so the agent can't tell when a mask is needed** · `mcp_server/server_tools/reference.py:149-158,196-199` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** The docstring gives "the fit error: the RMS over R, G, B (0..1) ..." and "the least error, with a key on
    every luminance level: colour that varies at one luminance, which no keys remove. A mask splits such parts off",
    and the result prints both numbers. Nothing says what either is measured against, or what a fit error near the
    least error, or a least error near the image's whole spread, means. The approved text: the error tells the agent
    "when hue varies apart from luminance and a mask is needed".
  - **Scenario.** An agent gets `fit error 0.0412` and `least error 0.0390` for a grainy photo. It can't tell whether
    5 keys are enough, whether more would help, or whether the photo holds two materials at one luminance that need a
    mask.
  - **Fix.** Print a baseline the two errors read against, such as the error of one key (the mean colour), and say in
    the docstring what holds by construction: a fit error near the least error means more keys won't help; a least
    error near the one-key error means the colour doesn't follow luminance, so a mask is needed. No threshold figure
    that no measurement gives.
  - **Resolution: done**.
    - **Test:** `test_one_keys_error_is_what_the_two_errors_read_against` and
      `test_a_least_error_at_one_keys_means_the_colour_doesnt_follow_luminance` failed: the result had no one key's
      error, and `_Palette` no `one_key`.
    - **Cause:** the result printed two errors with nothing to read them against.
    - **Fix:** `_Palette.one_key`, the RMS of each pixel from the mean colour; the result prints "one key's error X, the
      image's mean colour everywhere: what the two errors above read against", and a "reading the errors" line gives
      the two rules (a fit error near the least error: more keys won't help; a least error near one key's: the colour
      doesn't follow luminance, a mask is needed), as the tool's docstring does. No threshold figure. The module
      docstring says what holds by construction (nested least-squares fits, before the clip).
    - **Also covered:** nothing else prints these errors.
  - Questioned by SRV-233, SRV-234 and TST-771 (2026-11-22).

- [x] **SRV-232 · The new EXIF step refuses, or crashes on, photos Pillow opens and loads** · `mcp_server/server_tools/measure.py:110-122` · measured · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `ImageOps.exif_transpose(im, in_place=True)` runs inside the `try` that turns
    `(OSError, ValueError, SyntaxError, DecompressionBombError)` into "cannot read". Pillow's EXIF parser
    (`getexif()`) raises `SyntaxError` on a non-TIFF EXIF block, and its writer (`exif.tobytes()`, which the transpose
    calls after turning the pixels) raises `struct.error`, `TypeError` and `AttributeError`, outside the list.
  - **Probe** (the runner's, Pillow 13.0.0 in the venv, every file read by a plain `PILImage.open(p).load()`): a JPEG
    with JFIF dpi and `exif=b'Exif\0\0not-a-tiff-header'`, and PNG and WebP files with such an EXIF, are refused with
    "cannot read <path>: not a TIFF file"; the same JPEG without dpi loads (Pillow's own dpi step swallows the error
    and caches an empty EXIF). One byte of a valid EXIF set to 0 gave `struct.error` (offset 17) or `TypeError` (offset
    331) out of `_open_image`, shown as "Error executing tool ..." with no reason. A seeded fuzz of 4000 damaged EXIF
    blocks per format: about 6% refused and under 1% crashing. Every caller of `_open_image` has it:
    `compare_to_reference`, `analyze_reference`, `preview_maps`, `preview_node`.
  - **Scenario.** A phone or editor photo with a damaged EXIF block, which loaded before this branch, is refused, or
    gives an error with no reason.
  - **Fix.** Make the orientation best-effort: the transpose in a `try` of its own that catches any `Exception` and
    reads the image as loaded (a failure in `tobytes` leaves the pixels already turned, which is right). Unit tests
    with the probe's files: the JPEG with dpi and junk EXIF, and one byte set to 0 at offsets 17 and 331 of its
    template (`single_files.py` in the session's scratchpad holds it).
  - **Resolution: done**.
    - **Test:** `test_a_photo_whose_exif_pillow_refuses_is_read_as_loaded[not TIFF|byte 17|byte 331]`, JPEGs with dpi
      built in the test from the runner's template (`_damaged_exif_jpeg`): refused with "not a TIFF file", then a raw
      `struct.error` and a raw `TypeError`. The test also asserts that Pillow's `exif_transpose` still raises on each
      file, so a Pillow that moved the offsets fails it rather than blinding it.
    - **Cause:** the transpose ran inside the "cannot read" `try`, and Pillow's EXIF reader and writer raise outside
      its list.
    - **Fix:** `exif_transpose` in a `try` of its own catching any `Exception`, the image read as loaded; the comment
      and `_open_image`'s docstring say why.
    - **Also covered:** `_open_image` is the one opener of `compare_to_reference`, `analyze_reference`,
      `preview_maps` and `preview_node`.
  - Questioned by SRV-235 and TST-772 (2026-11-22).

- [x] **SRV-237 · The bitmap op says a node keeps the image's own size, where Designer rounds each side up to a power of 2 and stretches the image** · `mcp_server/server_tools/edits.py:91` · measured · found 2026-11-22 by the developer (Opus)
  - **Defect.** The bitmap op's text says "The node keeps the image's own size; set its `$outputsize` to change it",
    GUIDE's scripting part (about line 245) "The node's `$outputsize` is the image's own size (log2)", and the op's
    result line (`designer_helpers/edits.py:640`) "size (6, 4) (log2, the image's own; ...)". Older than this branch,
    in a file it changes.
  - **Probe** (the runner's, port 9895, through the tools): the node's `$outputsize` is Absolute and set at creation to
    each side's log2 rounded up: 50x10 gave (6, 4), 64x16 computed; 100x60 128x64; 300x200 512x256; 65x33 128x64; 63x31
    64x32; 64x64 kept. The image is stretched to that size with a bilinear filter, not padded: a red and blue halves'
    boundary moved from x 25 to 32 on the 50x10 image, with two blended pixels, and no padding colour in the export. It
    follows the image, not the graph (the graph at 256 and 2048, overridable and fixed). Setting `$outputsize`
    resamples it, up and down.
  - **Scenario.** An agent adds a 3000x2000 photo as a bitmap: the node is 4096x2048 with the photo stretched to a 2:1
    aspect, while the tool says it kept the photo's size; a texture built on it, or `compare_to_reference(aligned=True)`
    against it, works on a distorted photo.
  - **Fix.** Say what was measured in the three places (each side rounded up to a power of 2, the image stretched to
    it, `$outputsize` to change it); a live check with a 50x10 image: the size 64x16 and the blended pixels at the
    boundary.
  - **Resolution: done**.
    - **Test:** `bitmaps.check_a_bitmap_computes_at_sides_of_powers_of_2`: a 50x10 image, red and blue halves, through
      `apply_edits`' bitmap op; the result must say "size (6, 4) (log2 of each side, rounded up: the image is stretched
      to it", `node_stats` must give 64x16, and pixels 29 to 34 of row 8 must match bilinear interpolation (measured
      0.8902 and 0.1098 at the boundary, 0.1094 and 0.8906 predicted). It failed before the fix on the result line; the
      facts held.
    - **Cause:** the three texts were written from images whose sides were powers of 2.
    - **Fix:** the op's result line (`designer_helpers/edits.py`), the bitmap op's text ("each side rounded up to a
      power of 2, the image stretched to it (50x10 computes 64x16)") and GUIDE's scripting part (bilinear, not padded,
      the check named).
    - **Also covered:** "own size" and "log2, the" found nowhere else, README included; the existing 64x32 check
      still finds "size (6, 5)"; a fourth copy, `palettes.py`'s `SWATCH` comment, now points to GUIDE.
  - Questioned by SRV-239 (2026-11-23).

- [x] **SRV-238 · The opener turns PNG and TIFF files by their EXIF orientation, which Designer's bitmap node doesn't, so an aligned comparison of such a file is misaligned** · `mcp_server/server_tools/image_reading.py:28-34` · measured · found 2026-11-23 by two reviewers (Opus)
  - **Defect.** `ImageOps.exif_transpose(im, in_place=True)` turns every file with an orientation tag, for
    `compare_to_reference`, `analyze_reference`, `preview_maps` and `preview_node`.
  - **Probe** (the runner's, port 9895, a 64x32 image of red and blue halves): Designer's bitmap node applies a JPEG's
    orientation (3, 6 and 8 measured; `compare_to_reference(aligned=True)` against its own file gives 0.0000) and
    keeps a PNG's (eXIf) and a TIFF's in the stored frame: for Orientation 6, `node_stats` gives 64x32 with red on the
    left, while the reference is read 32x64, and the aligned comparison warns "aspect ratios differ" and gives R and B a
    mean abs diff of 0.5. A 180° tag would give the same differences with no warning. On main both sides read the
    stored frame.
  - **Scenario.** An agent adds a PNG that carries an orientation tag as a bitmap, builds on it, and compares the
    result with the file aligned or by a matching region: the numbers compare two frames.
  - **Fix.** Turn only a JPEG (`im.format == 'JPEG'`), as Designer does, and say so in the opener's docstring and
    GUIDE; a "designer facts" check of the three formats, and unit tests of the opener for each.
  - **Resolution: done**.
    - **Test:** `bitmaps.check_a_bitmap_turns_a_jpeg_by_its_orientation_and_no_other_format` (JPEG at 6, 3 and 8, an MPO
      at 6 saved as .jpg, a PNG with eXIf 6, a TIFF with 6: each node's frame, and `compare_to_reference(aligned=True)`
      against its own file with no aspect warning and an RMSE under 0.01) failed for the PNG and the TIFF; so did
      their unit tests in `test_image_reading.py`.
    - **Cause:** the opener ran `exif_transpose` on every format. And Pillow 13's TIFF `load_end` turns a TIFF itself,
      then drops the tag (a fact test in `test_pil_facts.py`), so main read a TIFF turned too.
    - **Fix:** only `JPEG` and `MPO` go through `exif_transpose`; a TIFF Pillow turned is turned back (`_STORED`, keyed on
      the tag gone after the load, so a Pillow that doesn't turn it reads it as stored). Measured: Designer turns an MPO
      saved as .jpg and refuses the .mpo extension. The opener's docstring, the modules' docstrings, GUIDE's Bitmaps and
      the core's Measure bullet say so.
    - **Also covered:** every place the server opens an image; `preview_maps` and `preview_node` read exported PNGs
      with no tag through `_load_8bit`.
  - Questioned by SRV-241 and TST-786 (2026-11-23).
  - Note (2026-11-23): its Probe says "On main both sides read the stored frame", and its Cause says main read a TIFF
    turned too (Pillow 13's `load_end`): on main the stored frame held for a PNG, not for a TIFF (a reviewer of the
    eighth review, Opus).
  - Questioned by TST-787 (2026-11-23).
  - Note (2026-11-23): since TST-787's fix, the live check compares each node with the image turned by hand, and
    the tools' reading of the tagged file is in the unit tests (`test_a_jpeg_is_read_turned_by_each_orientation_measured`);
    the check no longer compares a node with its own file.

## Low

- [x] **SRV-221 · The set text leaves out what a left-out alpha and midpoint become, and what interpmode's measured values do** · `mcp_server/server_tools/edits.py:105-107` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** "[[position, [r, g, b(, a)]], ...]" and "an optional third item is the midpoint, which changes nothing
    at the default interpmode 0 (it does at 1)". `_gradient_key` gives a left-out alpha 1 and midpoint 0, as a new key
    has. `interpmode` 1 eases and 3 holds each key's colour up to the next (measured, in GUIDE's scripting part only);
    GUIDE's core bullet names neither.
  - **Scenario.** An agent wanting an eased gradient sets `interpmode` 1 and every midpoint 0.5, taking it for the
    neutral value: the measured ease at 0.5 differs from the one at 0 (`params/checks.py:304-309`). An agent wanting
    flat colour bands from a palette doesn't learn that `interpmode` 3 gives them.
  - **Fix.** Add to the set text that a left-out alpha is 1 and a left-out midpoint 0, as a new key has. Add to GUIDE's
    core bullet that `interpmode` 1 eases and 3 holds each key's colour.
  - **Resolution: done**.
    - **Test:** docs only: the facts check's `interpmode` cells measure what the text now says.
    - **Fix:** the set text says a left-out alpha is 1 and a left-out midpoint 0, as a new key has. GUIDE's core bullet
      says `interpmode` is linear at 0, the default, eases at 1, and at 3 holds each key's colour up to the next.

- [x] **TST-762 · GUIDE's gradient facts: the colour-input fact says more than its cell measured and is written twice; a closing paragraph restates set's rules, with an internal name and an unmeasured figure; ROADMAP 116 names the wrong setter** · `mcp_server/GUIDE.md:73-74,484-485,489-495` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.**
    - "Fed a colour image, every pixel computed the first key's colour", in the core and the scripting part: the
      measured cell lists red first and at position 0, so it can't tell the key listed first from the lowest one.
      `.claude/rules/docs.md` keeps a fact in one place.
    - "So `apply_edits`' `set` builds each key ... `fmt` reads the keys back ... shipped gradients hold up to 256":
      the tool's behaviour belongs in its text and in the helpers' docstrings, which hold it already
      (`.claude/rules/docs.md`, the table). No test counts the 256, which `describe.py:132`'s comment repeats.
    - ROADMAP item 116 says the keys are set "with `setInputPropertyValueFromId`"; the code and the facts use
      `setPropertyValue`.
  - **Scenario.** An agent feeding a colour image through keys listed unsorted expects the first listed key's colour.
    A reviewer finds the 256 without a test.
  - **Fix.** Narrow the colour fact to what was measured, in one place with a pointer from the other. Cut the
    paragraph to a line naming the helpers. Drop the 256 or say where it was counted. Correct ROADMAP's setter.
  - **Resolution: done**.
    - **Test:** docs only (the docs tests).
    - **Fix:** the colour-input fact narrowed to what was measured ("the colour of the key at position 0, which was
      also listed first"), in the core bullet, with a pointer from the scripting part; the closing paragraph cut to a
      line naming `_given_keys` and `_shown_keys`; the 256 dropped from GUIDE and from `describe.py`'s comment;
      ROADMAP item 116 says `setPropertyValue`.
  - Questioned by TST-769 (2026-11-22).

- [x] **SRV-222 · sweep_param over keys gives every tile the same label, and `_SweepTile` doesn't allow a key list** · `mcp_server/server_tools/measure.py:197,301` · confirmed · found 2026-11-22 by a reviewer (Sonnet) and the developer (Opus)
  - **Defect.** `_labelled(im, '%s = %s' % (param, meta['value']))` cuts the label to `label[:48]`, so after
    `gradientrgba = ` only the first key shows. `_SweepTile.value: bool | int | float | str | list[bool | int | float]
    | None` and its docstring ("a vector's or colour's components read back as a list") don't cover the nested lists
    that swept keys read back as.
  - **Scenario.** Sweeping the colour of a Gradient Map's second key, every tile is labelled
    `gradientrgba = [[0.0, [1.0, 0.0, 0.0, 1.0]], [1.`: the contact sheet can't tell its tiles apart (the text lines
    still can).
  - **Fix.** Label a list value by its index in the sweep (`#1`, `#2`, ...), and widen the type and the docstring to
    nested lists.
  - **Resolution: done**.
    - **Test:** `test_pixels.py::test_a_value_too_wide_for_its_tile_is_labelled_by_its_place` failed.
    - **Cause:** a label was cut to its start, so every tile of a key sweep read the same.
    - **Fix:** `_labelled(im, label, short)` draws `short` (`<param> #N`) when the label is wider than the tile,
      measured with `textlength` (a fixed 48 characters missed narrow tiles, where a float4 already overflows).
      `_SweepTile.value` is `Json`, its docstring names nested lists, and the tool's docstring says it in a sentence.
    - **Also covered:** `compare.py`'s call of `_labelled` passes no short label, so it is unchanged.
  - Questioned by SRV-223 (2026-11-22).

- [x] **TST-763 · The facts check can't fail on three facts the docs state: a broken side acting per side, `isLocked` taken, keys kept after a reload** · `tests/test_all_tools/params/designer_scripts/keys.py:352-360` · measured · found 2026-11-22 by three reviewers (Sonnet)
  - **Defect.** GUIDE says "A side marked broken ... computes as if its handle were on the point", and
    `core._shown_keys` reads each side so. The one cell sets both flags of both keys, which can't tell per side from
    per key. The locked cell never reads its keys back, so an `isLocked` that didn't take gives the same values.
    `measure_reloaded` prints "as before" when both reads give no keys.
  - **Probe.** The runner's, in the review log: per side is how Designer computes, so the rule and `_shown_keys` hold.
    The committed check doesn't show it.
  - **Scenario.** A Designer whose broken flag acted per key would still pass the facts check, and a read-back of a
    curve with one broken side would set back a different curve.
  - **Fix.** Add cells with only key 1's `isRightBroken`, only key 2's `isLeftBroken`, and both of key 1's, each with
    its expected values. Print the locked cell's keys and expect `isLocked` on. Make the reload line fail when no keys
    are read.
  - **Resolution: done**.
    - **Test:** new facts cells, first run against wrong expectations, all failing: only the first point's right side
      broken, only the second point's left side, both sides of the first point, and two twins (each broken side's
      handle on its point, no flag). On 16 px, the first right broken equals its twin
      (`0.000 0.340 0.527 0.687 0.870 0.951 1.000`), the second left broken its twin, and both sides of the first
      point the first right alone, as the runner's probe measured. A new line reads a curve's `isLocked` and broken
      flags back as set.
    - **Fix:** those cells; the reload line prints "as before" only when keys were read. GUIDE's broken-side fact says
      per side, with the side facing no segment.
  - Questioned by TST-768 (2026-11-22).

- [x] **HLP-251 · set turns off every point's isLocked and broken flags, and only an internal docstring says so** · `mcp_server/designer_helpers/core.py` (`_shown_keys`), `mcp_server/designer_helpers/edits.py` (`_new_keys`) · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** The read-back leaves `isLocked` and the broken flags out, and `set` builds each point with all three
    False. `_shown_keys`'s docstring says so; the set text and GUIDE don't. In the two curves Designer ships that the
    probe read (TST-763), all 7 points have `isLocked` on and 12 of their 14 sides are broken.
  - **Scenario.** An agent reads a user's curve, moves one point and sets it back. What is computed is the same
    (TST-763's probe), but every point of the user's curve is now unlocked and unbroken in the curve editor.
  - **Fix.** Say it in the set text in a few words. Whether `set` should keep the flags is for the user (the review
    log, Unspecified).
  - **Resolution: done**.
    - **Test:** docs only.
    - **Fix:** the set text says `set` makes every point unlocked and unbroken, and that a broken side reads back with
      its handle on its point, which computes the same. What `set` builds is unchanged; whether it should keep the
      flags waits for the user (PLAN.md).

- [x] **HLP-252 · The new key readers hold list[Json] and dict[str, Json] where floats and known members are** · `mcp_server/designer_helpers/edits.py:245,266,269` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** `rgba: list[Json]`, `position: list[Json]` and `handles: list[list[Json]]` hold floats. `_given_keys`,
    `_gradient_key` and `_curve_point` return `dict[str, Json]`, whose members are known for each item type.
    `_shown_keys(...) -> Shown` always returns a tuple. `again = json.loads(...)`
    (`tests/test_all_tools/params/checks.py:391`) comes in as an implicit `Any`.
  - **Scenario.** mypy checks nothing more than `Json` through them: a misspelt member, or a string where a float goes,
    passes the types (`.claude/rules/python.md`, the most specific type).
  - **Fix.** `list[float]`; a `TypedDict` per item type, with a `Sequence` or a cast where `list`'s invariance meets
    `_make_value`; `-> tuple[Shown, ...]`; `again: Json`.
  - **Resolution: done**.
    - **Test:** mypy strict (`test_types.py`), passing.
    - **Fix:** TypedDicts `_GradientKey` and `_CurvePoint` (`type _GivenKey`), returned by the readers; the lists are
      `list[float]`; `_shown_keys -> tuple[Shown, ...]`; the read-back's `again: Json`, in `readings.as_json`. One cast
      stays in `_new_keys`, as a TypedDict's `items()` gives `object`; its comment says so.

- [x] **TST-764 · check_key_refusals_leave_the_graph_unchanged passes only after check_set_gradient_keys has run** · `tests/test_all_tools/params/checks.py:449` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `after == before and KEYS_READ in after`: `KEYS_READ` is on the Gradient Map only once the earlier
    check has set it, and the Curve isn't checked to hold points before the refusals.
  - **Scenario.** A scratch run of this check alone fails, though every refusal left the graph as it was. With an
    empty Curve, a refusal that cleared its points would go unseen.
  - **Fix.** Set the gradient's keys and the curve's points at the start of the check.
  - **Resolution: done**.
    - **Test:** the old check run alone: 11 checks, "the graph unchanged" failed. After the fix the same run passed 11
      of 11.
    - **Cause:** it relied on the keys an earlier check set.
    - **Fix:** it sets the gradient's keys and the curve's luminance and red points first, and requires all three in
      its read before the refusals.
  - Questioned by TST-767 (2026-11-22).
  - Questioned by TST-783 (2026-11-23).

- [x] **TST-765 · The params category's time in categories.py is from before the keys checks** · `tests/test_all_tools/categories.py:48` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `params.run,  # 15 s: set ops, inheritance and seed facts`, in a list kept slowest first, by measured
    times. The category now also runs the keys facts script, with a save and a reload, about 30 `node_stats` calls and
    a sweep.
  - **Scenario.** The categories run in this list's order, so a category placed by a stale time can start late and
    lengthen the full run.
  - **Fix.** Measure the category in a scratch run, and update its time and its place.
  - **Resolution: done**.
    - **Test:** two scratch runs of `params` whole, 45.3 s and 46.3 s with the server's start.
    - **Fix:** the time updated, and `params` moved to second place in `categories.py`, after `functions`; the category
      tests pass.

- [x] **TST-766 · Two clean-ups miss a failure** · `tests/test_all_tools/params/checks.py:466-474` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `check_expose_refuses_gradient_keys` removes nothing when an expose is wrongly accepted, so its graph
    input and the driven parameter stay for the checks after it. In `params/designer_scripts/keys.py:416-417`,
    `graph = new_graph()` runs before the `try`, so a failure in it after `newUserPackage()` leaves the package loaded.
  - **Scenario.** A regression that accepts the expose fails this check, then later checks fail on the input it left,
    which hides the cause.
  - **Fix.** Remove an input the expose made, in a `finally`. Move `new_graph()` into the `try`.

  - **Resolution: done**.
    - **Test:** the new `tests/unit/test_selftest_params.py` failed on the old check body (an expose taken left its
      input), and `test_designer_scripts.py::test_the_keys_facts_unload_their_package_when_its_graph_cant_be_made`
      failed (the package unloaded 0 times).
    - **Fix:** the expose check removes the input in a `finally` when the expose was taken; `keys.py` makes its
      package before the `try` and its graph inside it.

- [x] **SRV-223 · sweep_param's new label rule still cuts a label that fits a wide tile, clips the place on a narrow one, and raises on a value with a newline** · `mcp_server/server_tools/measure.py:200-201` · confirmed · follows SRV-222, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `shown = short if short is not None and draw.textlength(label) > im.width - 4 else label`, then
    `draw.text((4, 3), shown[:48], ...)`. A label longer than 48 characters that fits its tile is still cut to its
    start. `short` puts the place last (`<param> #N`), where a narrow tile clips it. Pillow's `textlength` raises
    "can't measure length of multiline text" for a label holding `\n` (`PIL/ImageText.py`), where `draw.text` drew it.
  - **Scenario.** `sweep_param(..., tile_size=512)` over a Gradient Map's second key labels every tile
    `gradientrgba = [[0.0, [1.0, 0.0, 0.0, 1.0]], [1.`, SRV-222's label. On a 64 px tile `levelouthigh #1` loses its
    number. Sweeping a string parameter over `'a\nb'` raises after the sweep has run and put the value back, so the
    agent gets an error and no sheet. `test_a_value_too_wide_for_its_tile_is_labelled_by_its_place` records the text
    passed to `draw.text`, and its kept label is 35 characters, so it sees none of these.
  - **Fix.** Use `short` when the label is longer than 48 characters too; put the place first (`#N <param>`); measure
    and draw the label with its newlines as spaces. Unit cases for a 512 px tile, a narrow one and a newline.
  - **Resolution: done**.
    - **Test:** `test_pixels.py::test_a_value_too_long_for_its_tile_is_labelled_by_its_place`, five cases; four failed:
      keys on a 512 px tile still cut to SRV-222's label, keys at 256 px and vectors on a 64 px tile with the place
      last, and a value holding a newline raised. The 256 px vector case kept its label.
    - **Cause:** the short label was taken only for a label wider than its tile, the 48-character cut still applied,
      the place came last, and a newline reached Pillow's `textlength`.
    - **Fix:** `_labelled` (`server_tools/measure.py`) draws `' '.join(label.splitlines())`, and takes `short` when the
      text is longer than `LABEL_CHARS` (48) or wider than the image; `sweep_param` passes `#N <param>`; its docstring
      says "too long".
    - **Also covered:** `compare.py`'s three `_labelled` calls pass no short label, so only newlines become spaces
      there, and its labels hold none.

- [x] **SRV-224 · describe_graph's own description doesn't say a key list past 16 shows its count, or that node_ids gives every key** · `mcp_server/server_tools/discovery.py:27-33` · confirmed · follows HLP-250, generation 2 · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** `include_params` "Adds, for a graph's nodes, every parameter that differs from its default ...", and
    `node_ids` is "A few nodes to focus on". The cut and the focused form are only in `apply_edits`' set text and
    GUIDE's core, though `.claude/rules/docs.md` makes a parameter's `Field` its single source.
  - **Scenario.** An agent reading only `describe_graph`'s description meets `gradientrgba = '<40 keys>'` with no word
    on how to read the keys.
  - **Fix.** One sentence in `include_params`' description: past 16 keys a list shows its count, unless `node_ids`
    focuses on the node.
  - **Resolution: done**.
    - **Test:** `test_keys.py::test_the_tools_texts_give_the_cut_describe_graph_makes` ties "past 16" in this text and
      the set text to `KEYS_SHOWN`; it failed with the constant set to 17.
    - **Fix:** `include_params`' description (`server_tools/discovery.py`): "A Gradient Map's keys or a Curve's points
      past 16 show as their count, unless node_ids focuses on the node."

- [x] **TST-767 · The refusals check's new first set matches the good array of its "good then bad" case, so a partial set goes unseen** · `tests/test_all_tools/params/checks.py:456,465` · confirmed · follows TST-764, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** The check now starts with `{'curveluminance': INVERT, 'curvered': EASE}`, and the case
    `('a good array then a bad one', {'curveluminance': INVERT, 'curvered': [[0, 'y']]}, ...)` sets the same
    `INVERT` before its bad `curvered`. Before TST-764's fix, the Curve held `EASE` there.
  - **Scenario.** A regression that sets `curveluminance` before refusing `curvered` changes nothing the check reads,
    so `after == before` holds and the check passes. That case is the only one able to show a partial set.
  - **Fix.** Start with `curveluminance: EASE` (or give the case a third value), so its good array differs from what
    the node holds.
  - **Resolution: done**.
    - **Test:** a temporary mutation of `set_params`, each value set as soon as it is checked: the check failed on "the
      graph unchanged", the good `INVERT` set before the bad `curvered` was refused.
    - **Cause:** the check's first set gave `curveluminance` the `INVERT` the "good then bad" case sets.
    - **Fix:** the Curve starts with `EASE` in both arrays, and the read before the refusals must hold `KEYS_READ` and
      `EASE_READ` per parameter; the docstring names the reason.
    - **Also covered:** no other refusal case sets two parameters at once.

- [x] **TST-768 · GUIDE says a curve side facing no segment changes nothing, and the facts cell behind it can't show it** · `mcp_server/GUIDE.md:490` · confirmed · follows TST-763, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** "a side facing no segment (the first point's left) changed nothing", from the cell built as
    `curve_key((0, 0), (0, 0), (0.5, 0), 'isLeftBroken', 'isRightBroken')`: that left handle is on its point, so
    breaking it moves nothing in any Designer. `checks.py:341-342` and `keys.py:368` say the same. The runner's probe
    of the first review measured it with the handle off its point (cells k, l and m: no change), but no committed check
    does.
  - **Scenario.** A Designer that used such a side would pass the facts check, while GUIDE says it changes nothing.
  - **Fix.** Add the cell with the first point's left handle off its point, plain and broken, both equal to `EASED`; or
    drop the clause.
  - **Resolution: done**.
    - **Test:** two new facts cells, the first point's left handle at (0.2, 0.3), off its point, plain and broken; run
      against a wrong expectation, both failed, and both measured `EASED`, as the runner's probe did.
    - **Fix:** those cells; GUIDE says the side facing no segment, its handle off its point, changed nothing, broken or
      not; the comments in `checks.py` and `keys.py` say which cell has the handle on its point.

- [x] **TST-769 · TST-762's fix makes ROADMAP 116 say Adobe's sample sets the keys with setPropertyValue, and two comments keep the old wording** · `ROADMAP.md:127` · confirmed · follows TST-762, generation 2 · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** "It is built as Adobe's sample builds it (`.../sample_sbs_graph_instance.py:66-96` ...): ..., set with
    `setPropertyValue`": the sample sets it with `setInputPropertyValueFromId('gradientrgba', sdValueArray)` (its line
    96). `tests/test_all_tools/params/checks.py:327` still says "a colour input: the first key's colour everywhere",
    and `tests/unit/test_keys.py:252` still says "shipped gradients hold up to 256 keys" and leaves out the focused
    listing.
  - **Scenario.** A reader of ROADMAP takes the sample for the setter's source; a reviewer finds the narrowed fact and
    the dropped figure again in the comments.
  - **Fix.** Say the sample sets it with `setInputPropertyValueFromId` and the tools with `setPropertyValue`, as
    `set_params` does. Narrow the comment at `checks.py:327` as GUIDE was, and cut the 256 from `test_keys.py`'s
    comment, naming the focused listing.

  - **Resolution: done**.
    - **Test:** docs and comments only (the docs tests).
    - **Fix:** ROADMAP item 116 says the sample sets the keys with `setInputPropertyValueFromId` and the tools with
      `setPropertyValue`, as `set_params` does; the comment at `checks.py:327` says the colour of the key at position
      0, which is listed first too; `test_keys.py`'s comment drops the 256 and names `node_ids` on the node.

- [x] **SRV-226 · analyze_reference cuts and samples a plain 32-bit image before it reads the image's scale, unlike compare_to_reference** · `mcp_server/server_tools/reference.py:161-172` · confirmed · found 2026-11-22 by three reviewers (Sonnet)
  - **Defect.** `_reference_pixels` divides a mode `I` image by 65535 when one of its values is over 255, else by 255
    (`compare.py:45-49`). `analyze_reference` passes it the region (`im.crop(...)`) and the sampled image
    (`im.resize(..., NEAREST)`), so the scale comes from those pixels. `compare_to_reference` converts first; its
    `_load_reference` docstring says "a plain 32-bit image's range is the whole image's", and
    `test_a_region_of_a_32_bit_image_keeps_the_whole_images_range` pins it.
  - **Scenario.** The 32-bit TIFF of that test (100 on the left, 40000 on the right) with `reference_region`
    `[0, 0, 4, 4]`: `analyze_reference` reads 100/255 = 0.392 where `compare_to_reference` reads 100/65535, so the keys
    are 257 times too bright. Mode `I` comes only from signed 16-bit and 32-bit TIFFs, so it is rare.
  - **Fix.** Decide the scale from the whole opened image (its extrema, before the cut and the sampling) and pass it
    down; a unit test with that TIFF and region.
  - **Resolution: done**.
    - **Test:** `test_a_region_of_a_32_bit_image_keeps_the_whole_images_range` (the entry's TIFF and region) and
      `test_a_sample_of_a_32_bit_image_keeps_the_whole_images_range` (a 40000 pixel NEAREST leaves out) both read
      0.3922 for 100/65535.
    - **Cause:** the 16-bit or 8-bit rule read the region's or the sample's values.
    - **Fix:** `_integer_scale(im)` (`measure.py`, from `getextrema()`) is the one rule; `analyze_reference` takes it
      from the whole opened image before the cut and the sampling, and `_reference_pixels(im, scale)` requires it.
    - **Also covered:** `output._load_8bit` (`preview_maps`, `preview_node`) had its own copy of the rule, on the whole
      image; it uses `_integer_scale` now.

- [x] **SRV-227 · When the 1st and 99th percentiles of luminance are equal, analyze_reference says the image has one luminance level** · `mcp_server/server_tools/reference.py:58,191-194` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `t = np.clip(...) if high > low else np.zeros(len(rgb))` puts every pixel on level 0, and the result
    says `keys: 1 of the 5 asked: the image has 1 of the 64 luminance levels`, with `luminance 0.4500 to 0.4500`.
  - **Scenario.** A decal on a plain background, where 98% of the opaque pixels share one luminance: the image has
    many levels, and the agent is told it has one and gets the mean colour as its only key.
  - **Fix.** Stretch over the minimum and maximum when the percentiles are equal, or say that they are; a unit test.
  - **Resolution: done**.
    - **Test:** `test_equal_percentiles_stretch_over_the_minimum_and_maximum` (990 mid, 5 dark and 5 light pixels)
      failed with one key and `luminance 0.4024 to 0.4024`.
    - **Fix:** when the two percentiles are equal, `_palette` stretches over the minimum and maximum, and the luminance
      line says so; the docstrings too.
  - Questioned by TST-771 (2026-11-22).

- [x] **SRV-228 · Three sentences of Step 3's docstrings say other than the code** · `mcp_server/server_tools/reference.py:17-18,149-151` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.**
    - The tool's docstring: "Their positions stretch the image's luminance, weighted as the result says, ...": it
      means the R, G, B weights of the result's luminance line, and reads as the keys being weighted.
    - The module docstring: "k-means and median cut ... need a seed": median cut is deterministic.
    - `tests/unit/test_reference.py:1-2`: "What the keys compute on a Gradient Map: the bitmaps check of the live
      self-test". `check_analyze_reference` only calls the tool and reads its text; nothing builds a Gradient Map.
  - **Scenario.** A maintainer weighing median cut is given a wrong reason; a reviewer looks for a Gradient Map in the
    `bitmaps` check that isn't there (Step 4's end-to-end check is still to come).
  - **Fix.** "the image's luminance (the R, G, B weights of the result's luminance line)"; "k-means needs a seed";
    narrow the test docstring to what the live check does, or name Step 4's check once it exists.
  - **Resolution: done**.
    - **Test:** docs only (the docs tests).
    - **Fix:** "the image's luminance (the R, G, B weights of the result's luminance line)"; "and k-means needs a
      seed"; `test_reference.py`'s docstring: "The tool called through MCP: the bitmaps check of the live self-test".

- [x] **SRV-229 · The reference loader lets a decompression-bomb or a PNG checksum error through as an error with no reason** · `mcp_server/server_tools/compare.py:29-37` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** `_open_reference` catches `(OSError, ValueError)`. Pillow raises `DecompressionBombError` (an
    `Exception`) from `open()` for an image over about 179 MP, and `SyntaxError` from a bad checksum of a chunk after
    the pixel data. mcp 2.x shows anything but a `ToolError` as "Error executing tool ..." with no path or reason.
  - **Scenario.** A 20000x10000 panorama given to `analyze_reference` (or `compare_to_reference`, which shares the
    loader): the agent sees only "Error executing tool analyze_reference".
  - **Fix.** Catch those two as well, with the "cannot read <path>: <reason>" message; a unit test with a lowered
    `PILImage.MAX_IMAGE_PIXELS`.
  - **Resolution: done**.
    - **Test:** `test_an_image_pillow_refuses_is_named_with_its_reason` (an image over a lowered `MAX_IMAGE_PIXELS`, a
      PNG with a broken chunk header inside its pixel data; through `analyze_reference` and `_load_reference`) and
      `test_output.py::test_preview_maps_names_a_map_pillow_refuses` raised Pillow's raw errors.
    - **Cause:** the opener caught only `OSError` and `ValueError`.
    - **Fix:** `_open_image` in `measure.py`, the one opener of both reference tools and of `_load_8bit`, catches
      `SyntaxError` and `DecompressionBombError` too, with "cannot read <path>: <reason>". Measured on Pillow 13: a bad
      checksum after the pixel data doesn't raise; a broken chunk header within it does.
    - **Also covered:** `preview_maps`' and `preview_node`'s `_load_8bit` caught nothing and now go through
      `_open_image`; `output._image_size` catches every exception already.

- [x] **SRV-230 · The changed and new pixel functions type a layout as str where only 'RGBA' or 'L' is** · `mcp_server/server_tools/compare.py:40`, `mcp_server/server_tools/measure.py:187` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `_reference_pixels -> tuple[Pixels, str]` and `_rgb(data, layout: str)`: `_rgb` takes any string but
    `'RGBA'` as grey, so a misspelt layout is silent. `tests/unit/test_reference.py` types colours as `tuple[int, ...]`
    where a 3- or 4-int tuple is.
  - **Scenario.** mypy checks nothing more than `str` there (`.claude/rules/python.md`, the most specific type).
  - **Fix.** A `Literal['RGBA', 'L']` alias in the functions the step adds or changes, the others following where mypy
    needs; the tests' colour tuples narrowed.
  - **Resolution: done**.
    - **Test:** a scratch mypy probe calling `_rgb(..., 'rgba')` passed before the fix and fails after it.
    - **Fix:** `PixelLayout = Literal['RGBA', 'L']` (`measure.py`) on `_rgb`, `_to_display`, `_reference_pixels`,
      `_load_reference` and `_compare_report`, and where mypy needed it (`_decode_pixels`, `_node_pixels`,
      `test_compare.py`'s `_report`); the tests' colours are `RGB8` and `RGBA8`.

- [x] **TST-770 · Two of analyze_reference's paths have no test that can fail: the least error with fewer keys than levels, and the region cut before the sampling** · `tests/unit/test_reference.py:111-139` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `floor = error if len(chosen) == len(positions) else _fit(t, rgb, positions)[1]`
    (`reference.py:69`): `test_colour_varying_at_one_luminance_shows_in_the_error` asks 5 keys of 3 levels, so it takes
    the first branch, and the only test reaching the second asserts `floor <= error`. No test crosses
    `reference_region` with the sampling, which the comment "cut before the sampling" relies on.
  - **Scenario.** A `floor` of 0.0, or one computed from the chosen keys, passes every test. Swapping the cut and the
    sampling reads a large image's region in the sampled image's coordinates, and every test passes.
  - **Fix.** In that test, `_palette(rgb, 2)` too, its floor the expected value and its error above it; a test of a
    region of a large image, read from the right pixels and not sampled.

  - **Resolution: done**.
    - **Test:** `test_colour_varying_at_one_luminance_shows_in_the_error` also runs `_palette(rgb, 2)`: its least error
      the analytic value, its fit error over 0.005 above it; new `test_a_region_of_a_large_image_is_cut_before_the_sampling`.
      A floor of 0.0, a floor from the chosen keys, and the cut moved after the sampling each fail them.

- [x] **SRV-231 · compare_to_reference doesn't leave a float reference's NaN or infinite pixels out, and reports NaN** · `mcp_server/server_tools/compare.py:94-103` · confirmed · found 2026-11-22 by the developer (Opus)
  - **Defect.** `_opaque` reads only alpha, so a float reference's non-finite pixels reach `_compare_report`;
    `analyze_reference` now leaves them out (the user's word, 2026-11-22, PLAN.md).
  - **Scenario.** A mode `F` TIFF reference holding one NaN: the developer's probe of `_compare_report` printed
    `nan nan (nan nan nan) ... EMD nan` and "luma distributions: different".
  - **Fix.** Refuse such a reference with a message naming how many pixels aren't finite (simpler than leaving them
    out on the aligned path, where the resize spreads a NaN into its neighbours); a unit test.
  - **Resolution: done**.
    - **Test:** `test_compare.py::test_a_reference_holding_non_finite_pixels_is_refused` failed with "DID NOT RAISE".
    - **Fix:** after the region's cut, `_load_reference` refuses a mode `F` reference holding NaN or infinite pixels,
      naming how many and suggesting a `reference_region` without them; the tool's docstring says so. `_finite` and
      `_non_finite` are shared with `analyze_reference`.

- [x] **SRV-233 · "A least error near one key's error means a mask is needed" is printed for a flat or one-material image, where no mask helps** · `mcp_server/server_tools/reference.py:170-171,232-233` · confirmed · follows SRV-225, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** The reading line and the docstring give the rule unconditionally. On a flat swatch all three errors
    are 0, and on one grainy material the least error is near one key's because the grain doesn't follow luminance:
    both meet "near", and neither needs a mask. The test asserts `one_key > 0.1`, which the text never says.
  - **Scenario.** GUIDE tells the agent to pick a flat-lit region of one material; the result then tells it a mask is
    needed.
  - **Fix.** Say that a least error near one key's means the colour doesn't follow luminance: where the image holds
    parts of different colours a mask may split them, and on one material it is its grain, which no keys remove.
  - **Resolution: done**.
    - **Test:** `test_one_keys_error_is_what_the_two_errors_read_against` asserts the new wording; it failed on the old
      reading line.
    - **Fix:** the reading line and the docstring: a least error near one key's means the colour doesn't follow
      luminance; where the image holds parts of different colours a mask may split them, and on one material it is its
      grain, which no keys remove.

- [x] **SRV-234 · A float image's values outside 0..1 break the three errors' order and the reading rule** · `mcp_server/server_tools/reference.py:81,138` · confirmed · follows SRV-225, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `one_key` is computed on the unclipped pixels, while `_fit` clips the keys to 0..1, so for a mode `F`
    image with values above 1 the fit and least errors can exceed one key's, against the module docstring's order.
  - **Scenario.** A grey float TIFF, half 0.5 and half 4.0: the keys clip to 0.5 and 1, fit and least errors about
    2.12, one key's about 1.75, and the reading line says a mask is needed where the colour follows luminance exactly.
  - **Fix.** Clip the pixels to 0..1 at the start of `_palette`, and say so in the docstring (as the keys are).
  - **Resolution: done**.
    - **Test:** `test_values_beyond_0_to_1_are_clipped_first` (a float TIFF, half 0.5 and half 4.0) failed with
      "luminance 0.5000 to 4.0000" and the errors out of order.
    - **Fix:** `_palette` clips the pixels to 0..1 first; its docstring, the module's step 1 and the tool's docstring
      say so.

- [x] **TST-771 · Two tests of the fixes: one passes only when two lumas are bit-equal, and one arm of the luminance line is pinned by none** · `tests/unit/test_reference.py:62-67,197-202` · confirmed · follows SRV-225, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `test_a_least_error_at_one_keys_means_the_colour_doesnt_follow_luminance` builds red and teal of
    equal luma (`_one_luminance` asserts only `approx`): when they are bit-equal the percentiles are equal, one level is
    held and `floor == one_key` by identity; one ulp apart, two keys fit exactly and the test fails. The luminance
    line's normal arm, "the 1st and 99th percentiles of ...", is asserted by no test (SRV-227's fix added the other).
  - **Scenario.** Another numpy build sums the luma in another order and the test fails, or passes without exercising
    the rule; a line that always said "the minimum and maximum ..." passes every test.
  - **Fix.** Give the two colours dark and light companions, as `test_colour_varying_at_one_luminance_shows_in_the_error`
    does, against an analytic value; assert the normal arm in `test_flat_swatches_give_their_colours_as_keys`.
  - **Resolution: done**.
    - **Test:** (a) the red and teal test now has 1% darker and 1% lighter pixels, so the two share a level however
      their lumas round; the least error checked against its analytic value, one key's against an independent RMS; it
      holds with teal nudged by 0, 1e-15 and 1e-12, and `floor = one_key = 0` fails it. (b)
      `test_flat_swatches_give_their_colours_as_keys` asserts "(the 1st and 99th percentiles of"; writing "the minimum
      and maximum" there fails it.
  - Note (2026-11-22): its test's docstring says "the 1st and 99th percentiles fall in those"; with 10 of 1000
    pixels each they fall between those and red and teal (indices 9.99 and 989.01). The test holds either way; narrow
    the sentence (the fifth review, generation 3).
    The sentence now says the percentiles fall between those pixels and red and teal.

- [x] **HLP-253 · A comment claims Designer computes a curve x above 1, and measure.py's docstring doesn't name the opener it now holds** · `mcp_server/designer_helpers/edits.py:291-292` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** "x above 1 is refused, though Designer computes it": no measurement isolates a curve point above 1
    (the one cell with x 1.2 also has x -0.2). The gradient's comment is backed by its cell. `measure.py`'s docstring,
    "Measuring pixels: node_stats, sweep_param, check_tiling, and the pixel decoding they share", leaves out
    `_open_image` and `_integer_scale`, which the reference tools and `output.py` use.
  - **Scenario.** A reader takes an unmeasured Designer fact from a comment; a maintainer looks for the image opener
    elsewhere.
  - **Fix.** Drop "though Designer computes it" from the curve's comment (the lead's wording in its brief); name the
    shared image reading in `measure.py`'s docstring.

  - **Resolution: done**.
    - **Test:** comments and a docstring only (the docs tests).
    - **Fix:** the curve's comment reads "x above 1 is refused, to catch a 0..255 or percent mistake (the lead's
      choice, the user, 2026-11-22)"; `measure.py`'s docstring names the shared reading of image files (`_open_image`,
      `_integer_scale`) and its users.

- [x] **SRV-235 · The opener's docstring says a damaged EXIF leaves the image as loaded, where one Pillow can't write back leaves it turned, and two module docstrings state the orientation unconditionally** · `mcp_server/server_tools/measure.py:112-115` · confirmed · follows SRV-232, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** "An EXIF block Pillow can't read or write back leaves the image as loaded", while the comment below
    says "A failure in writing the EXIF back comes after the pixels are turned, which is right": Pillow's in-place
    `exif_transpose` turns the pixels before `exif.tobytes()`. The test is named
    `test_a_photo_whose_exif_pillow_refuses_is_read_as_loaded`. `compare.py:1-2` and `reference.py:1-3` say the image is
    read "as it is viewed, its EXIF orientation applied", with no exception, and `compare.py`'s docstring doesn't list
    `_finite` and `_non_finite` among what it shares with `analyze_reference`.
  - **Scenario.** A maintainer reads that a write-back failure leaves the stored frame, and a region taken on such a
    photo comes from the turned one.
  - **Fix.** Narrow the docstring and the test's name: one Pillow can't read leaves the image as loaded, one it can't
    write back leaves it turned. "When Pillow can read its EXIF" in the two module docstrings; list the shared
    helpers.
  - **Resolution: done**.
    - **Test:** docs and test names only (the docs tests).
    - **Fix:** `_open_image`'s docstring and comment: an EXIF block Pillow can't read leaves the image as loaded, one it
      can't write back after turning the pixels leaves it turned; the two module docstrings say "when Pillow can read
      its EXIF", and compare.py's lists `_finite` and `_non_finite`; the test is two,
      `test_a_photo_whose_exif_pillow_cant_read_is_read_as_loaded` and
      `test_a_photo_whose_exif_pillow_cant_write_back_is_read_turned`.

- [x] **TST-772 · The damaged-EXIF test's offsets tie it to Pillow's EXIF writer and can't be found again, and its file builders sit in test_reference.py** · `tests/unit/test_reference.py:368-406` · confirmed · follows SRV-232, generation 2 · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** Bytes 17 and 331 of a template come from a runner's scratch script, which REVIEW.md names and which
    won't survive; the test's precondition (`pytest.raises((SyntaxError, struct.error, TypeError))` on Pillow's own
    `exif_transpose`) goes red when a Pillow upgrade accepts those blocks or moves the bytes, though the code is right,
    and nothing says how to find new ones. `_damaged_exif_jpeg` (25 lines) and `_broken_png` build image files for
    `_open_image`, not for the palette (`.claude/rules/python.md`, keep each file to its main logic).
  - **Scenario.** `pip install -U pillow` turns the suite red on a test whose code is right, and the next agent can't
    rebuild its files.
  - **Fix.** Keep the real "not TIFF" file; for the writer's errors, monkeypatch `measure.ImageOps.exif_transpose` to
    raise `struct.error` and `TypeError` after turning the image. Put the image-file builders in a module of their own
    beside the tests.
  - **Resolution: done**.
    - **Test:** the split tests pass on correct code; putting the transpose back inside the "cannot read" `try` fails
      all three.
    - **Fix:** the real "not TIFF" JPEG kept, now read as stored (16x8); the writer's errors made by patching
      `ImageOps.exif_transpose` to turn the image with Pillow's own function, then raise `struct.error`, then
      `TypeError`; the image-file builders in a new `tests/unit/image_files.py`; the template offsets gone. That a
      non-TIFF EXIF fails Pillow's orientation read is a fact test in `test_pil_facts.py`, so a Pillow that changes it
      fails under a name that says so.

- [x] **SRV-236 · compare_to_reference computes the node before it reads the reference, so a refused reference comes after Designer was used** · `mcp_server/server_tools/compare.py:261-264` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `_node_pixels(...)` (a bridge call that computes the node through a temporary output) runs before
    `_load_reference(...)`, so a missing file, an empty region or, since SRV-231, non-finite pixels are refused after
    Designer's work. Older than this branch, in a function it changes.
  - **Scenario.** An agent's typo in `reference_path` costs a compute of the node in the user's Designer, and an undo
    step, before "cannot read".
  - **Fix.** Read the reference first; a unit test that a refused reference sends nothing to Designer.

  - **Resolution: done**.
    - **Test:** `test_compare.py::test_a_refused_reference_sends_nothing_to_designer[missing|empty region|non-finite]`
      (the `sent` fixture): each failed, the node's compute sent first and its error coming instead of the refusal.
    - **Cause:** `compare_to_reference` called `_node_pixels` before `_load_reference`.
    - **Fix:** the reference is read first; the node's own `region` stays after it, as it needs the node's size.
    - **Also covered:** `node_stats` and `check_tiling` take no file; `analyze_reference` uses no Designer;
      `run_designer_script` reads its file before the bridge; `diff_graph` checks its `.sbs` path after a read-only
      bridge call, a round trip with no compute or undo step, left as it is.

- [x] **TST-773 · The check of which unit tests read a doc counts a docstring that starts with a doc's name** · `tests/unit/test_review_lookup.py:886-889` · confirmed · found 2026-11-22 by the developer (Opus)
  - **Defect.** `['"](?:AGENTS|GUIDE|README|ROADMAP|DECISIONS|REVIEW)\.md['"]` takes any quote on each side, so a
    docstring opening `"""GUIDE.md's recipe ...` matches `"GUIDE.md'`, and the test file counts as one that reads a
    doc. Older than this branch.
  - **Scenario.** The developer's `test_reference.py` docstring made `test_review_lookup` fail, as the file then had to
    be in the docs tests' command; the developer reworded the docstring to get past it.
  - **Fix.** The same quote on both sides (a back-reference), and a unit case for the docstring form.
  - **Resolution: done**.
    - **Test:** four new cases in `test_a_test_that_reads_a_doc_is_found`: `"""GUIDE.md's recipe ..."""` and a
      docstring quoting `'.claude", "rules"` must not count (both failed), `read("GUIDE.md")` and
      `os.path.join(".claude", "rules")` must.
    - **Cause:** each name was matched between any opening and any closing quote.
    - **Fix:** back-references in `DOC_TESTS`, the second string of the `.claude` form still free to use the other
      quote.
    - **Also covered:** no other regex of that form in the tests, hooks, scripts or server.

- [x] **TST-774 · The photo-to-Gradient-Map check's grey ramp is never checked to rise, so a ramp that failed passes** · `tests/test_all_tools/bitmaps/checks.py:226-241` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** The `set_function` that makes the ramp (`$pos.x`) has its result unread, and the ramp read back is
    used for both the output and the expected values, never asserted to run from near 0 to near 1.
  - **Scenario.** The ramp's function fails: a new Pixel Processor computes black, every point is key 0's colour and
    so is every expected value, and the check passes without testing the keys between.
  - **Fix.** Check the `set_function` result, and that the ramp rises from below the second key's position to above
    0.9.
  - **Resolution: done**.
    - **Test:** a scratch run with `set_function` refused by a setup passed before the fix (every point key 0's colour)
      and fails after it.
    - **Fix:** `check_photo_to_gradient_map` requires `set_function` not to be an error, and 7 ramp values rising from
      below the second key's position to above 0.9; the detail shows the ramp.
    - **Also covered:** `check_designer_greys`' expected values come from the strip's colours, not from a read.

- [x] **TST-775 · GUIDE says Grayscale Conversion takes other weights as given, from one cell** · `mcp_server/GUIDE.md:504-506` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** "Other weights are taken as given, not divided by their sum: (0.1, 0.1, 0.1, 0) gave 0.3 on white",
    beside the default (0.33, 0.33, 0.33, 0) computing the mean: the check measures one other set, summing to 0.3, and
    none summing near or above 1.
  - **Scenario.** An agent sets (0.5, 0.5, 0.5, 0) to weigh the channels equally and gets 1.5 on white, or sets
    (0.33, 0.33, 0.33, 0) itself and doesn't know whether that is the default's mean.
  - **Fix.** Measure the weights an agent would set (the default's values set explicitly, ones summing to 1 and above
    1), or narrow the sentence to the cell.
  - **Resolution: done**.
    - **Test:** new cells of `check_designer_greys` (32-bit float): (0.33, 0.33, 0.33, 0) set explicitly gives the
      mean (red 0.3333, white 1); (0.34, 0.33, 0.33, 0) gives 0.34 on red; (0.5, 0.5, 0.5, 0) gives 1.5 on white;
      (0.1, 0.1, 0.1, 0) gives 0.3 on white.
    - **Fix:** GUIDE's sentence says the default's values compute the mean, set explicitly too, and gives the other
      sets with their sums and results.

- [x] **TST-776 · The bitmaps category's time in categories.py is from before Step 4's checks** · `tests/test_all_tools/categories.py:57` · confirmed · found 2026-11-22 by a reviewer (Sonnet)
  - **Defect.** `bitmaps.run,  # 4 s: bitmap ops, compare_to_reference, analyze_reference`, in a list kept slowest
    first by measured times; the category now runs the greys and the photo to Gradient Map too.
  - **Scenario.** A category placed by a stale time can start late in the pool and lengthen the full run.
  - **Fix.** Measure the category in a scratch run, and update its comment and its place.
  - **Resolution: done**.
    - **Test:** two scratch runs of `bitmaps` whole, 28.3 s and 29.0 s with the server's start.
    - **Fix:** `categories.py` gives 29 s, placed after `facts` (35 s) and before `safeguards` (23 s).

- [x] **TST-777 · Two facts an agent using the tools needs are only in GUIDE's scripting part: Grayscale Conversion Advanced's default grey, and curveluminance on a colour input** · `mcp_server/GUIDE.md:68,78` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** The core's Measure bullet says "Grayscale Conversion at its default weights", and `search_nodes`
    offers Grayscale Conversion Advanced too, whose default is Desaturation ((max + min) / 2), only in the scripting part.
    The core's "Gradients and curves" bullet says "(`curveluminance`, and a channel's own for a colour input)", which
    reads as if `curveluminance` doesn't act on a colour input; the trim took "(on colour: R, G, B)" out of the set text.
  - **Scenario.** An agent picks the Advanced node and gets a palette placed on another grey; an agent sets only the
    red channel's curve on a colour image expecting `curveluminance` to be ignored.
  - **Fix.** Say both in the core, in a few words, making room in it (it is at about 19,961 of 20,000 characters).
  - **Resolution: done**.
    - **Test:** docs only (the docs tests, `test_guide.py`'s limit).
    - **Fix:** the core's Measure bullet: "Grayscale Conversion at its default weights (not the Advanced one, whose
      default is Desaturation)"; its Gradients bullet: "(`curveluminance`, alone on a grey input, on a colour one on R, G
      and B before each channel's own)"; the scripting part's copies are pointers. Room made by trimming four phrases;
      the core is at 19,985 of 20,000 characters.
  - Questioned by TST-781 (2026-11-23).

- [x] **TST-778 · Test helpers out of place, and one vaguer type: a test file imports another's private helpers, the greys check's data sit beside its logic, and a key's colour is tuple[float, ...]** · `tests/unit/test_image_reading.py:11` · confirmed · found 2026-11-22 by two reviewers (Sonnet)
  - **Defect.** `from test_reference import DARK, LIGHT, MID, _assert_keys, _halves, _line, _swatches`, where
    `image_files.py` is the shared home; `_Grey`, `ADVANCED`, `_desaturated` and `_advanced` in `bitmaps/checks.py`, where
    `palettes.py` holds the category's data; `Key = tuple[float, tuple[float, ...]]` (`palettes.py:58`) for a colour of
    exactly four floats.
  - **Scenario.** A change to `test_reference.py`'s helpers breaks the opener's tests; a reader of `checks.py` meets
    data before logic (`.claude/rules/python.md`, keep each file to its main logic; the most specific type).
  - **Fix.** Move the shared helpers into `image_files.py` and the greys' data into `palettes.py`; type the colour as
    four floats.
  - Questioned by TST-780 (2026-11-23).
  - Note (2026-11-23): its "no test file imports another's helpers" says more than holds: `test_keys.py:13`, new in this
    branch, imports `_described` from `test_server.py` (two reviewers of the seventh review, Opus).

  - **Resolution: done**.
    - **Test:** a move and a type: the image unit tests passed before and after (52), and so did the live greys check.
    - **Fix:** the shared colours, `swatch_strip` and `halves_png` in `tests/unit/image_files.py`; `result_line`,
      `result_keys` and `assert_keys` in a new `tests/unit/reference_results.py`; no test file imports another's
      helpers; the greys' table in `bitmaps/palettes.py` (`expected_greys`); `Key = tuple[float, Rgba]`, four floats.

- [x] **SRV-239 · For a side above 8192 px the bitmap op reports log2 14 and says the image is stretched to it, where Designer computes 8192 and shrinks it** · `mcp_server/designer_helpers/edits.py:640` · measured · follows SRV-237, generation 2 · found 2026-11-23 by two reviewers (Opus)
  - **Defect.** The result line and the op's text say "log2 of each side, rounded up: the image is stretched to it".
  - **Probe** (the runner's): a 9000x10 PNG gave `size (14, 4)` and `$outputsize` (14, 4), and computed 8192x16, the
    image shrunk to it with a 2-pixel bilinear blend at x 4095 and 4096; 8192x10 and 5000x10 gave (13, 4), as the text
    says.
  - **Scenario.** An agent adds a 45 MP photo: the result says it is stretched to 16384 px, the node computes 8192, and
    `$outputsize` 14 read back and set again is refused (above 13).
  - **Fix.** Say that a side is at most 8192 px, the image shrunk to it, in the result line, the op's text and GUIDE;
    a cell in the bitmap check.
  - **Resolution: done**.
    - **Test:** the bitmap size check gained a 9000x10 image: "size (14, 4)" and "a side computes 8192 px at most (13):
      the image is shrunk to it", 8192x16, and pixels 4093 to 4098 as measured; it failed on the result line.
    - **Fix:** the result line adds the shrink note when a side's log2 is above `MAX_SIZE_LOG2`; the op's text says
      "8192 px at most, the image stretched or shrunk to it"; GUIDE's Bitmaps gives the measurement (not called
      bilinear, which predicts no blend there).

- [x] **SRV-240 · analyze_reference doesn't say its keys and errors are for a Gradient Map at interpmode 0** · `mcp_server/server_tools/reference.py` (the tool's docstring) · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** The fit is linear between keys, the nearest key's colour outside them, which is `interpmode` 0; no
    text of the tool says so.
  - **Scenario.** An agent sets the keys on a user's Gradient Map at `interpmode` 1 (eased) and the output misses the
    printed fit error.
  - **Fix.** A few words in the docstring: the keys and the errors are for a Gradient Map at its default
    `interpmode` 0.
  - **Resolution: done**.
    - **Test:** `test_the_description_says_the_keys_are_for_interpmode_0` failed before the fix.
    - **Fix:** the docstring says the fit and the errors are a Gradient Map's at its default interpmode 0, linear
      between keys.

- [x] **TST-779 · A test comment cites PLAN.md, which the branch's last commit deletes** · `tests/unit/test_keys.py:206` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** `# "a value read can be set again" (PLAN.md): ...`.
  - **Scenario.** After the merge the comment points at a file main never has.
  - **Fix.** Cite ROADMAP item 116, or drop the parenthesis.
  - **Resolution: done**.
    - **Fix:** the comment cites ROADMAP item 116; no other `.py` file cites PLAN.md as a source.
  - Questioned by TST-786 (2026-11-23).

- [x] **TST-780 · test_keys.py types a four-float colour as tuple[float, ...]** · `tests/unit/test_keys.py:85` · confirmed · follows TST-778, generation 2 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** `def _gradient_key(position: float, colour: tuple[float, ...], ...)`, then `r, g, b, a = colour`.
  - **Scenario.** mypy checks nothing of the colour's length (`.claude/rules/python.md`, the most specific type).
  - **Fix.** Four floats, or a shared `Rgba` alias.
  - **Resolution: done**.
    - **Fix:** `tuple[float, float, float, float]`; the other `tuple[float, ...]` there are of variable length.

- [x] **TST-781 · GUIDE's core says curveluminance runs before a channel's own curve and alone on a grey input, which the facts cells can't show** · `mcp_server/GUIDE.md:78` · confirmed · follows TST-777, generation 2 · found 2026-11-23 by two reviewers (Opus)
  - **Defect.** "(`curveluminance`, alone on a grey input, on a colour one on R, G and B before each channel's own)".
    The one cell combining two arrays inverts both (`keys.py:422-425`), and an inversion applied twice gives R back in
    either order; on the grey ramp only `curvered` and `curvealpha` are measured, not `curvegreen` and `curveblue`.
    `params/checks.py:361` says the same.
  - **Scenario.** An agent sets `curveluminance` and `curvered` on a colour image, relying on the order; if Designer
    applies the red curve first, the result differs, and no check failed.
  - **Fix.** A cell that tells the order (`curveluminance` inverting and `curvered` halving, on the colour ramp), and
    `curvegreen` and `curveblue` on the grey ramp; then the sentence says what they measured.
  - **Resolution: done**.
    - **Test:** new facts cells: `curvegreen` and `curveblue` inverting on the grey ramp change nothing;
      `curveluminance` inverting with `curvered` halving on the colour ramp gave R = 1 - x/2, so `curvered` acts first,
      then `curveluminance`: the old claim had the order backwards.
    - **Fix:** the expectations, the comment in `params/checks.py` and GUIDE's core say what was measured
      ("`curvered` measured before `curveluminance`"); the scripting part points there. The order of `curvegreen` and
      `curveblue` against `curveluminance` is not claimed.
  - Questioned by TST-785 (2026-11-23).

- [x] **TST-782 · GUIDE's core is at its limit and holds notes for script writers and maintainers that belong in the scripting part** · `mcp_server/GUIDE.md` (the core) · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** The core is at about 19,985 of 20,000 characters (`test_guide.py`), the branch having filled it.
    Among its text: `node_stats`' raw-buffer details (byte order, `getPixelFormat()`, `getRowPitch()`), the abort that
    lands in a finalizer, the example's notes for whoever maintains it, and the library package calls under "In
    scripts", about 1,150 characters that an agent using only the tools doesn't need (`.claude/rules/docs.md`, the
    table).
  - **Scenario.** The next fact an agent needs can't go in the core without a trim.
  - **Fix.** Move those to the scripting part or the modules' docstrings, as `.claude/rules/docs.md` puts them. The
    Undo rules and "Several Designers side by side" stay in the core.
  - **Resolution: done**.
    - **Fix:** out of the core: the raw-buffer details (a new "Pixel buffers" bullet of the scripting part), the abort
      in a finalizer and the library package calls (scripting bullets), the example's maintainer notes (its docstring,
      with `test_guide`'s scope case for it now a test reading that file). The Undo rules and "Several Designers side
      by side" stay. The core is at 18,985 characters.

- [x] **TST-783 · The sweep-over-keys check relies on keys an earlier check left, and checks only one value's read-back** · `tests/test_all_tools/params/checks.py:508-519` · confirmed · follows TST-764, generation 2 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** `before` is read from the Gradient Map as the earlier checks left it, never asserted to be
    `KEYS_READ`; only the second value's read-back is asserted, though the docstring says "each read back".
  - **Scenario.** Run alone, the Gradient Map has no keys: a put-back that cleared them passes (`'' == ''`), and a first
    tile that kept the old keys passes too.
  - **Fix.** Set `KEYS` at the start and require them in `before`; assert the first value's read-back too.
  - **Resolution: done**.
    - **Test:** run alone before the fix, the check passed with no keys before or after.
    - **Fix:** it sets `KEYS` first, requires `before == KEYS_READ`, and asserts both values' read-backs.

- [x] **TST-784 · GUIDE says the photo's own grey through the levels "gives the photo back within the fit error", which holds for the part the palette read** · `mcp_server/GUIDE.md:65-70` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** The keys, the range and the fit error are computed on the `reference_region` (and the sample, the
    opaque and finite pixels), which the same bullet tells the agent to give.
  - **Scenario.** An agent compares the whole photo, shading included, and sees a larger error than the one printed.
  - **Fix.** "gives back the part read (its `reference_region`) within the fit error".

  - **Resolution: done**.
    - **Fix:** GUIDE's core: "That gives back the part read (its `reference_region`) within the fit error".

- [x] **SRV-241 · The opener's docstrings and GUIDE say a file is read as its bitmap node computes it, which was measured for the orientation of a JPEG, a PNG and a TIFF only** · `mcp_server/server_tools/image_reading.py:2,29` · confirmed · follows SRV-238, generation 2 · found 2026-11-23 by two reviewers (Opus)
  - **Defect.** "_open_image loads a file as a bitmap node of it computes" (`image_reading.py:2`), "loaded as a bitmap
    node of it computes in Designer" (`:29`), "read as a bitmap node of it computes" (`compare.py:1-2`,
    `reference.py:1-3`), "The reference tools read a file as its bitmap node computes it" (`GUIDE.md:70-71`), and the
    same in `test_image_reading.py:80` and `bitmaps/checks.py:290`. What was measured is the orientation: a JPEG at 3,
    6 and 8 and an MPO at 6 turned, a PNG and a TIFF at 6 as stored. A bitmap node also rounds each side up to a power
    of 2 and stretches the image (SRV-237), which the opener doesn't. A JPEG's mirrored orientations (2, 4, 5 and 7),
    and a WebP or an AVIF, were not measured; the opener reads a WebP and an AVIF as stored.
  - **Scenario.** An agent takes `analyze_reference`'s or `compare_to_reference`'s reading of a 50x10 photo for the
    node's, which computes 64x16 with the photo stretched; or trusts a WebP's orientation to match its node.
  - **Fix.** Narrow each copy to what was measured: a JPEG (an MPO too) turned by its EXIF orientation, as a bitmap
    node turns it; a PNG and a TIFF read as stored, as Designer keeps them; another format read as stored; the
    `reference_region` taken in that frame, in the file's own pixels.
  - **Resolution: done**.
    - **Test:** none new (narrowing, generation 2): `bitmaps.check_a_bitmap_turns_a_jpeg_by_its_orientation_and_no_other_format`
      measures what the text now says, 7 of 7 in a scratch run on port 9893.
    - **Fix:** `_open_image`'s docstring states the rule once, as a list: a JPEG or an MPO turned by its EXIF
      orientation, as a bitmap node turns it; a PNG and a TIFF read as stored, as Designer keeps them; another format
      read as stored, its node's orientation unmeasured; the image in the file's own pixels, where a bitmap node also
      rounds each side up to a power of 2. The module docstrings of `image_reading.py`, `compare.py` and `reference.py`
      point to it. GUIDE's core, Measure, names the formats and says a `reference_region` is in the file's own pixels.
    - **Also covered:** GUIDE's scripting part, Bitmaps, keeps only what the node does and points to the core;
      `bitmaps/checks.py:290` and `test_image_reading.py:80` now say "orientation"; a grep for "as viewed", "in that
      view" and "the tools read it so" found only text about JPEGs or one check's frame.
  - Questioned by TST-788 (2026-11-23).

- [x] **TST-785 · GUIDE's core no longer says curveluminance acts on R, G and B of a colour input, and its "measured before" reads two ways** · `mcp_server/GUIDE.md:78-79` · confirmed · follows TST-781, generation 3 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** "(`curveluminance` alone acts on a grey input; on a colour one each array acts on its channels,
    `curvered` measured before `curveluminance`)". "each array acts on its channels" drops what TST-777's fix said and
    the cells measure, that `curveluminance` acts on R, G and B; "`curvered` measured before `curveluminance`" can
    read as the order of the measurements rather than the order Designer applies the curves in.
  - **Scenario.** An agent sets `curveluminance` on a colour image expecting it to act on a luminance alone, or reads
    the order backwards and gets the red channel's curve applied to the wrong values.
  - **Fix.** Wording only (generation 3: narrowing is the fix, no new check): "(on a grey input only `curveluminance`
    acts; on a colour one `curveluminance` acts on R, G and B, each other array on its own channel, and `curvered`
    acts before `curveluminance`)".
  - **Resolution: done**.
    - **Test:** docs only (the docs tests, `test_guide.py`'s limit).
    - **Fix:** GUIDE's core has the entry's sentence, wording only (generation 3).
    - **Also covered:** no other copy of the order sentence: `params/checks.py`'s comment was narrowed by TST-781's fix,
      and the scripting part points to the core.

- [x] **TST-786 · Two new tests of the opener check less than they say, their parameters are typed loosely, and a test comment quotes words ROADMAP item 116 doesn't hold** · `tests/unit/test_pil_facts.py:62` · confirmed · follows SRV-238, generation 2 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.**
    - `test_pillow_turns_a_tiff_by_its_orientation_as_it_loads_it_and_drops_the_tag`:
      `image.getpixel((0, 0)) == image.getpixel((31, 0)) == (255, 255, 255)  # the left half, now the top` holds in the
      stored frame too, where columns 0 to 31 of the top row are the white half; only the size shows the turn.
    - The MPO case of `test_a_jpeg_stored_rotated_is_read_as_it_is_viewed` never asserts that Pillow opens the file as
      `MPO`, so a save that wrote a plain JPEG would pass as the MPO case.
    - `kind: str` in both tests and in `image_files.turned` (`image_files.py:52`), for four formats, and
      `options: dict[str, object]` for Pillow's save options (`.claude/rules/python.md`, the most specific type).
    - `test_keys.py:205`: `# "a value read can be set again" (ROADMAP item 116)`, words the item doesn't hold. This
      point questions TST-779's resolution.
  - **Scenario.** The pixel check passes on an image Pillow never turned; the MPO case tests a JPEG twice; a misspelt
    format passes mypy; a reader looks for the quote in ROADMAP.md and doesn't find it.
  - **Fix.** A pixel that differs between the two frames; `format == 'MPO'` asserted for the MPO case; a `Literal` of
    the four formats, and the save options typed (a TypedDict, or keyword arguments); the comment in its own words,
    citing ROADMAP item 116.
  - Note (2026-11-23): `test_image_reading.py:28-31`, `test_an_image_pillow_refuses_is_named_with_its_reason`, types its
    parametrized `case` and `loader` as `str`, the pattern this fix narrowed for `kind`; its Also covered doesn't name it. A
    test leftover at generation 3, left as it is (a reviewer of the ninth review, Opus).

  - **Resolution: done**.
    - **Test:** the TIFF fact's pixel check is now a black image with one white pixel at (5, 0), required at (31, 5)
      after Pillow's turn, with (5, 0) black; the MPO case asserts `Image.open(path).format == kind`. In a scratch
      run, both failed on what they guard against: a frame Pillow didn't turn, and a plain JPEG saved the same way.
    - **Fix:** `Format = Literal['JPEG', 'MPO', 'PNG', 'TIFF']` in `image_files.py`, for `turned` and both tests' `kind`;
      the save options as keyword arguments in three plain calls; `test_keys.py`'s comment in its own words, citing
      ROADMAP item 116.
    - **Also covered:** the live check's `ORIENTED` is typed with the same four formats (it can't import the unit
      tests' helpers), and its saves are the same three calls; it ran 7 of 7 before and after `/simplify`.

- [x] **SRV-242 · analyze_reference's module docstring says each level's point sits at its pixels' mean position, where the darkest and the brightest are put at 0 and 1** · `mcp_server/server_tools/reference.py:11-12` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** "2. That range is cut into _LEVELS levels. Each level holding pixels gives a point: its pixels' mean
    position and mean colour." Line 81: `positions[[0, -1]] = 0, 1  # the darkest level holds the pixels at 0, the
    brightest those at 1`. The tool's own docstring has it right.
  - **Scenario.** A maintainer reading the method expects the first key at level 0's mean position, about 0.004, and
    finds it at 0.
  - **Fix.** "its pixels' mean position (0 for the darkest level, 1 for the brightest) and mean colour".
  - **Resolution: done**.
    - **Test:** docs only (the docs tests).
    - **Fix:** step 2 says "its pixels' mean position (0 for the darkest level, 1 for the brightest) and mean colour".

- [x] **TST-787 · The orientation check's image is the same flipped top to bottom, so it can't tell a rotation from its mirror** · `tests/test_all_tools/bitmaps/checks.py:296-297` · confirmed · follows SRV-238, generation 2 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** `image = Image.new('RGB', (64, 32), (0, 0, 255))`, then `image.paste((255, 0, 0), (0, 0, 32, 32))`:
    every column is one colour, so each orientation measured gives the same pixels as its mirrored twin in Pillow's
    `exif_transpose` table: 6 (`ROTATE_270`) and 5 (`TRANSPOSE`), 8 (`ROTATE_90`) and 7 (`TRANSVERSE`), 3
    (`ROTATE_180`) and 2 (`FLIP_LEFT_RIGHT`). GUIDE's scripting part ("3, 6 and 8 measured") and `_open_image`'s
    docstring rest on it.
  - **Scenario.** A Designer that applied orientation 6 as a transpose passes the check, and a portrait phone photo
    then compares upside down against its node in `compare_to_reference(aligned=True)`.
  - **Fix.** A mark that differs from its vertical flip, such as a green 8x8 corner pasted after the red; seen failing
    in a scratch run with an image tagged 5 where 6 is expected (or 7 for 8), then passing with the right tags.
  - **Resolution: done**.
    - **Test:** the check's image gains a green 8x8 mark in its top-left corner, and `ORIENTED` gives each row the turn
      its node must show (3 a half turn, 6 a quarter clockwise, 8 a quarter anticlockwise, none for the PNG and the
      TIFF); each node is compared, aligned, with the image turned by hand. In a scratch run on port 9893, tagged 5
      where 6 is expected and 7 where 8 is, both rows failed; with the right tags, 7 of 7: Designer rotates, it doesn't
      mirror.
    - **Fix:** the mark, and the expectation set by the table rather than by the file's tag. The tools' reading of each
      tagged file now rests on the unit tests below, and the check's docstring says so.
    - **Also covered:** `test_image_reading.py`'s turned images were the same halves, and a JPEG tagged 5 where 6 was
      meant passed them (a scratch probe). They now use `image_files.marked_halves()`, with an oracle written by hand
      (`np.rot90` from a `_TURNS` table, not `exif_transpose`); the new
      `test_a_jpeg_is_read_turned_by_each_orientation_measured` (3, 6 and 8) fails when tagged 5, 7 and 2 instead. The
      TIFF tests already used asymmetric images.

- [x] **TST-788 · GUIDE's core says a reference_region is "in the file's own pixels", which reads as the stored frame of a rotated JPEG** · `mcp_server/GUIDE.md:72` · confirmed · follows SRV-241, generation 3 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** "The reference tools turn a JPEG (an MPO too) by its EXIF orientation, as its bitmap node does. They read
    any other format as stored, a PNG and a TIFF as Designer keeps them. A `reference_region` is in the file's own
    pixels." SRV-241's fix said "the `reference_region` taken in that frame, in the file's own pixels", and
    `_open_image`'s docstring says a region of a phone photo stored rotated "is taken in that view".
  - **Scenario.** An agent gives a `reference_region` in the stored frame of a 4032x3024 JPEG tagged 6, which the
    tools read 3024x4032: the region covers another part of the photo, or is clamped at its edge.
  - **Fix.** Wording only (generation 3: narrowing is the fix, no new check): the region is in the image as the tools
    read it, turned, at the file's own pixel size.
  - **Resolution: done**.
    - **Test:** docs only (the docs tests, `test_guide.py`'s limit: the core at 19,265 characters).
    - **Fix:** GUIDE's core: "A `reference_region` is in the image as the tools read it, turned, at the file's own pixel
      size." Wording only (generation 3).
    - **Also covered:** `image_reading.py`'s module docstring and `_open_image`'s say "at its own pixel size";
      `compare.py` and `reference.py` point to `_open_image`, "its reference_region taken in the image it returns".

- [x] **TST-789 · result_keys returns json.loads's implicit Any under a declared type** · `tests/unit/reference_results.py:17-21` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** `keys = json.loads(...)`, `assert isinstance(keys, list)`, then
    `return [(position, colour) for position, colour in keys]` under `-> list[tuple[float, list[float]]]`: only the
    outer list is checked. `.claude/rules/python.md` asks for `object` on parsed JSON before it is checked, and to look
    for `json.loads`'s implicit `Any`, which mypy doesn't report.
  - **Scenario.** A keys line of another shape reaches the tests typed as keys, and mypy checks nothing of it.
  - **Fix.** The parsed value as `object`, each key's position and colour checked before it is returned.

  - **Resolution: done**.
    - **Test:** `test_the_keys_line_of_another_shape_is_refused`, four malformed lines: 3 failed before the fix, two
      returned unchecked and one raising a `TypeError` instead of an `AssertionError`.
    - **Fix:** `result_keys` types the parsed JSON as `object`, checks each key (a number and a list of numbers) and
      returns floats; its callers pass.
    - **Also covered:** `palettes.py`'s own parser of the line converts every value with `float()` as it unpacks each key,
      so a wrong shape raises there.
