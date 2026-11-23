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

**Last used:** PLG-45, SRV-242, HLP-253, INS-46, TST-803, AGT-125.

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
| Low | 0 | 14 |
| **Total** | **0** | **14** |

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
| 2026-11-23, step 1 (a blend's opacity input fed a colour image) | Opus (developer) | 1 | 0 | 0 | 294,817 | 17 min |
| 2026-11-23, the first review (a Sonnet round on step 1) | Sonnet | 2 | 5 [5 Low] | 5 [5 Low] | 214,679 | 6 min |
| 2026-11-23, the first review's fixes and step 2 | Opus (developer) | 1 | 0 | 0 | 134,712 | 17 min |
| 2026-11-23, the second review (a Sonnet round on the first review's fixes and step 2) | Sonnet | 2 | 5 [5 Low] | 5 [5 Low] | 275,736 | 8 min |
| 2026-11-23, the second review's fixes | Opus (developer) | 1 | 0 | 0 | 76,283 | 11 min |
| 2026-11-23, the third review (the Opus round on the entire branch) | Opus | 2 | 4 [4 Low] | 4 [4 Low] | 344,311 | 10 min |
| 2026-11-23, the third review's fixes | Opus (developer) | 1 | 0 | 0 | 35,958 | 6 min |
| 2026-11-23, set_function's description (the user's decision) | Opus (developer) | 1 | 0 | 0 | 5,030 | 1 min |
| 2026-11-23, TST-802 after the final check | Opus (developer) | 1 | 0 | 0 | 8,164 | 4 min |
| **Total** | | **12** | **14 [14 Low]** | **14 [14 Low]** | **1,389,690** | **80 min** |

## Review log

### 2026-11-23: blend-opacity-fact's first review, a Sonnet round on step 1

- **Scope:** `git diff 012e15d 2f70de1 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the live check and its Designer script; GUIDE's bullet and the check's docstring. No
  tests run, no probes: each suspicion settled by reading. Not raised, or not worth a fix:
  - naming the check in the bullet, and the bullet restating the scripting part's `colorswitch` fact: the core's
    Library node facts name no check, and the core is read without the scripting part;
  - the labels and colours written in both the script and the check: a label missing from the check fails as "no
    line", and the precedent keeps the cases in the script and the lines in the check;
  - the grey-sided lines pinning the blend's own format (`LUM8`): a change there fails loudly;
  - a fourth pixel reader among the self-test's scripts: scripts can't import each other;
  - no unit test of the script's failure path: its package is unloaded in a `finally`, as its siblings' are.
- **Unspecified:**
  - a bitmap used as a mask: whether a grey PNG computes a grey image that `opacity` reads; GUIDE says an RGB JPEG and
    a grey+alpha PNG compute RGBA8. Put to the user (2026-11-23), the lead recommending it be measured in this branch;
  - rounding in a facts check's expected values: no rule; the Grayscale Conversion line's inputs are exact 8-bit steps.
- **Not verified:** none.
- **Resolutions assessed:** none in scope.
- **Findings:** TST-790, TST-791, TST-792, TST-793, TST-794 (Low). Merged: TST-790 and TST-791 (two reviewers each). A
  few Lows: step 1's reviews are done once the developer fixes them, then an Opus round on the entire branch. No chain.
- **Suggested order:** TST-791, TST-790, TST-792, TST-793, TST-794.
- **Checked and found fine:** each colour line fails on another reading of a colour `opacity` (its mean, its alpha,
  one channel, Rec.709 luma); the line with nothing connected tells "ignored" from opacity 0; each graph's `$format`
  and `$outputsize` made Absolute, the depth in every expected line; one package per format, unloaded in a `finally`;
  the pixel decoding of 8-bit, 16-bit and 32-bit float; the labels escaped and none a prefix of another; the types;
  the bullet's place in the core by `docs.md`; the sections the docstring cites; Grayscale Conversion's mean against
  GUIDE's default weights.

### 2026-11-23: blend-opacity-fact's second review, a Sonnet round on the first review's fixes and step 2

- **Scope:** `git diff 5498536 89b83ab -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the check, `blend_cases.py` and the script; GUIDE, `set_function`'s line and their
  tests. No tests run, no probes: each suspicion settled by reading. Not raised, or not worth a fix:
  - `pngs()` typed `dict[str, str]` rather than a TypedDict of its two keys: the script can't import the type, so
    mypy can't tie the two sides;
  - whether a bitmap follows its graph's `$format` in the 16-bit and float lines: the developer's scratch run passed
    them (87 of 87), LUM16 and LUM32F for the grey PNG;
  - `SHOWN`'s "so a mask needs colorswitch off", where GUIDE also gives Grayscale Conversion, and the line carrying a
    blend's advice on every such result: the wording the user approved in step 2;
  - the check's name saying "a colour image" while it also measures grey feeds.
- **Unspecified:** a 16-bit grey PNG (I;16) and a grey+alpha PNG (LA) as masks, neither measured nor claimed; GUIDE
  says a grey+alpha PNG computes RGBA8, so the measured rule points to opacity 0. Left to the user.
- **Not verified:** none.
- **Resolutions assessed:** TST-790 to TST-794. All hold but TST-792 (TST-795) and TST-793 (TST-796).
- **Findings:** TST-795, TST-796, TST-797, TST-798, TST-799 (Low). A few Lows: the step's reviews are done once the
  developer fixes them, then an Opus round on the entire branch. The longest chains: TST-792 → TST-795 and TST-793 →
  TST-796, generation 2.
- **Suggested order:** TST-795, TST-798, TST-797, TST-796, TST-799.
- **Checked and found fine:** each line, over the new destination, failing on another reading of a colour `opacity`
  (its mean, its alpha, one channel, a bitmap read as grey, black); every feed on both sides in the three graphs; the
  labels' format and anchoring; `opacitymult`'s line; the expected mixes at 8-bit rounding, none near a `%.2f` edge;
  the PNGs' modes, folder, links and clean-up, and their paths through ARGS; the sides and feeds shared by a graph's
  blends; the `perpixel` bullet against `check_a_processors_function`; the `SHOWN` line's two pins; no other GUIDE,
  README or docstring sentence contradicted.

### 2026-11-23: blend-opacity-fact's third review, the Opus round on the entire branch

- **Scope:** `git diff main...HEAD -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'` at a667ee5, with REVIEW.md as the
  record.
- **How:** two Opus reviewers: the live checks and their script; GUIDE, `set_function`'s line and its tests. No tests
  run, no probes: each suspicion settled by reading. Not raised, or not worth a fix:
  - outside copy, "a grey image there is the opacity" measured at grey 0.5 only, which can't tell an opacity from its
    inverse, and no line reading each blend's `blendingmode` back (generation 3): no Designer reads a mask inverted by
    mode, TST-795's resolution and the scripting part say what was measured, and the developer's table shows each
    mode's `opacitymult` 0.5 blend different (DECISIONS.md, Low-value findings about the tests and docs are not
    raised);
  - "with nothing connected, the blend gave its `source`", the source white: no Designer gives white whatever the
    source;
  - the helper `grey(v)` in `functions/checks.py:472`, older than the branch, returning an RGBA pixel: a local name;
  - the bitmap op's "for references, masks and hand-painted maps" (`server_tools/edits.py:87-88`): true, and GUIDE's
    core says an RGB PNG needs Grayscale Conversion.
- **Unspecified:** a warning when `apply_edits`' `connect` wires a colour image into a blend's `opacity`, which
  bypasses `set_function`'s line; no doc decides. For the user.
- **Not verified:** none.
- **Resolutions assessed:** TST-790 to TST-799. All hold; TST-795 has the generation-3 gaps above (TST-801 and what
  was not raised).
- **Findings:** TST-800, TST-801, TST-802, TST-803 (Low). A few Lows: the reviews look converged once the developer
  fixes them. The longest chain: TST-792 → TST-795 → TST-801, generation 3.
- **Suggested order:** TST-801, TST-800, TST-803, TST-802.
- **Checked and found fine:** each GUIDE claim against a line that fails on the obvious alternatives (grey and colour
  types, a Pixel Processor on and off, both PNGs, Grayscale Conversion of three images, alpha 0.5 against a channel or
  the mean); the `apart` guard; the modes pinned to the blend's own enum; `$format` and `$outputsize` Absolute, one
  compute per graph; each package unloaded in a `finally`; the bitmaps linked, with no temp copy; no clipboard, editor
  or wait in the check; the pixel decoder; the expected mixes away from a two-decimal edge; the casts; the `SHOWN` line
  against step 2 and GUIDE, both pinned whole; `node_stats` naming the format as the core says; README needing no
  change.

---

## High

## Medium-high

## Medium

## Low-medium

## Low

- [x] **TST-790 · A colour opacity's "gave the destination" is measured against a black destination only, which can't tell it from black** · `tests/test_all_tools/facts/designer_scripts/blend_opacity.py:102-103` · confirmed · found 2026-11-23 by two reviewers (Sonnet)
  - **Defect.** `link(uniform(g, (1, 1, 1, 1), colour_sides), n, 'source')` and
    `link(uniform(g, (0, 0, 0, 1), colour_sides), n, 'destination')`: every colour line expects black
    (`mixed('8', 0, *rgba)`), and GUIDE's bullet says a colour image "gave the `destination`, as opacity 0".
  - **Scenario.** A Designer that computes black for a colour `opacity` input passes every line, and GUIDE still tells
    an agent its destination comes through.
  - **Fix.** A line whose destination isn't black, such as (0.2, 0.4, 0.6, 1), with a colour `opacity`, giving that
    destination; or the bullet narrowed to black.
  - **Resolution: done**.
    - **Test:** every line's destination is (0.2, 0.4, 0.6, 1), or grey 0.2 with grey sides, each mix computed by
      `blend_cases.over`. On the old script the colour lines failed on black where (0.2, 0.4, 0.6, 1) was expected, and
      the grey ones on the mix over black (0.50 where 0.60 was expected).
    - **Cause:** a black destination can't tell "gave the destination" from black.
    - **Fix:** the destinations in `blend_opacity.py`; every colour feed now gives the destination.

- [x] **TST-791 · GUIDE's bullet and the check's docstring claim every colour in every graph, where the 16-bit, float and grey-sided lines measure two colours or one** · `mcp_server/GUIDE.md:186-188` · confirmed · found 2026-11-23 by two reviewers (Sonnet)
  - **Defect.** GUIDE: "A colour image there gave the `destination`, as opacity 0, at every colour measured, alpha 0.5
    included, in 8-bit, 16-bit and float graphs." The docstring (`facts/checks.py:46-51`): "at each colour of COLOURS,
    alpha 0.5 included. So with grey sides too, and in 16-bit and float graphs." The 16-bit and float graphs measure
    `COLOURS[:2]` (grey 0.5 and white, opaque), the grey sides one colour and the Pixel Processor, and the Pixel
    Processor is measured in 8-bit only. "float" is `hdr_high_precision`, 32-bit, not `hdr_low_precision`'s 16F.
  - **Scenario.** An agent takes a red mask, or alpha 0.5, in a 16-bit or a 16F graph as measured.
  - **Fix.** The 16-bit and float graphs over every colour of `COLOURS` (cheap), or the bullet and the docstring
    narrowed to what is measured; "32-bit float" either way, unless 16F is measured too. The docstring's "So" goes.
  - **Resolution: done**.
    - **Test:** `check_a_blend_opacity_fed_a_colour_image` expects every feed in all three graphs (8-bit, 16-bit, 32-bit
      float), each with colour sides and grey sides (`facts/blend_cases.py`, `expected_lines`). On the old script: 84
      checks, 78 failed, 57 of them "no line" for the cells it never measured.
    - **Cause:** the 16-bit and float graphs ran three feeds and the grey sides four, and GUIDE and the docstring
      generalised from them.
    - **Fix:** the script builds every feed, both sides, in the three graphs. The core's bullet claims no formats; the
      scripting part's new bullet, A blend's opacity, lists the cases and says "32-bit float". The docstring points to
      GUIDE, its "So" gone.
    - **Also covered:** the Pixel Processor's lines and the grey sides are measured in every graph too.

- [x] **TST-792 · GUIDE's bullet doesn't say `opacity` is the blend's input connector, nor that "is the opacity" was measured with `opacitymult` at its default** · `mcp_server/GUIDE.md:186` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** "Atomic `blend`, measured in copy mode: a grey image into `opacity` is the opacity." GUIDE names the
    parameter `opacitymult` elsewhere, and the core is read without the scripting part's connectors line, the only
    place that says `opacity` is an input. The check leaves `opacitymult` at 1.
  - **Scenario.** An agent looks for a parameter `opacity` to set, or takes a grey input as the opacity whatever
    `opacitymult` is.
  - **Fix.** "a grey image into its `opacity` input is the opacity, `opacitymult` at its default (1)", or as short.
  - **Resolution: done**.
    - **Test:** the script prints each graph's first blend's `opacitymult`, expected `1`; written first expecting 0.5,
      the three lines failed, then passed.
    - **Fix:** GUIDE's core: "Atomic `blend`'s `opacity` input, `opacitymult` at 1, its default: a grey image there is
      the opacity."
  - Questioned by TST-795 (2026-11-23).

- [x] **TST-793 · GUIDE's bullet doesn't say "a colour image" is the image's type, a grey-looking one included, where set_function's result calls the same image grey** · `mcp_server/GUIDE.md:186-188` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** The bullet says "a colour image" and "a grey image", never that this is the image's type (RGBA or LUM,
    as `node_stats` names it), colours with R = G = B included, which the check measures ((0.5, 0.5, 0.5, 1), white).
    `set_function`'s result for a Pixel Processor's float with `colorswitch` on reads "colorswitch is on: the float is
    grey." (`mcp_server/server_tools/functions.py:137`).
  - **Scenario.** An agent builds a Pixel Processor mask, reads "the float is grey", and feeds it into `opacity`, as in
    the demo this branch came from.
  - **Fix.** The bullet says it is the type, as `node_stats` names it, R = G = B included. Rewording `set_function`'s
    line changes a tool's output: the user's word first (asked 2026-11-23).
  - **Resolution: done**.
    - **Test:** docs; the check's lines for (0.5, 0.5, 0.5, 1) and white give the destination.
    - **Fix:** GUIDE's core: "A colour one gave the `destination`, as opacity 0, also with R = G = B. Grey and colour
      are the image's type, LUM or RGBA, as `node_stats` names its format." `set_function`'s line (the user, 2026-11-23,
      PLAN.md step 2): "colorswitch is on: the output is a colour image, the float in R, G and B. A blend's opacity
      reads a colour image as 0, so a mask needs colorswitch off."; `test_set_function.py` and the live
      `check_set_function_computes_known_pixels` failed on the old line first.
    - **Also covered:** the scripting part's `perpixel` bullet ("a float its value in R, G and B, alpha 1", which
      `check_a_processors_function` measures), the functions check's docstring and the unit test's id. `set_function`'s
      tool description, "a float (grey) or a float4 (colour)", is left as it is: a change of a tool's description beyond
      the user's word, put to the user.
  - Questioned by TST-796 (2026-11-23).

- [x] **TST-794 · The blend check's constants and helpers open facts/checks.py, which held only checks and run** · `tests/test_all_tools/facts/checks.py:22-43` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** `HALF`, `COLOURS`, `PP_ON`, `PP_OFF`, `listed`, `image` and `mixed` serve one check and sit above every
    check of the file. `.claude/rules/python.md`: "Keep each file to its main logic".
  - **Scenario.** A reader of the facts checks meets one check's line formatting first.
  - **Fix.** A module beside it, imported by the check (`facts/preparations.py` and `bitmaps/palettes.py` are the
    precedents).

  - **Resolution: done**.
    - **Test:** a move: the check's scratch run passed 22 of 22 before and after it.
    - **Fix:** the constants and helpers in `tests/test_all_tools/facts/blend_cases.py`, in `bitmaps/palettes.py`'s
      shape; `facts/checks.py` keeps the check and its table of feeds.

- [x] **TST-795 · GUIDE's core bullet and set_function's line no longer say the blend was measured in copy mode, so they claim every blend mode** · `mcp_server/GUIDE.md:186-187` · confirmed · follows TST-792, generation 2 · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** "Atomic `blend`'s `opacity` input, `opacitymult` at 1, its default: a grey image there is the opacity.
    A colour one gave the `destination`, as opacity 0": TST-792's fix replaced "measured in copy mode". `SHOWN[(True,
    'float')]` (`mcp_server/server_tools/functions.py:138-139`) says "A blend's opacity reads a colour image as 0", no
    mode either. `blend_opacity.py`'s `blend()` sets `blendingmode` copy only.
  - **Scenario.** An agent masks a multiply or add blend with a Pixel Processor, taking the rule as measured for its
    mode.
  - **Fix.** Generation 2: measure the other modes, or narrow both texts to copy. Measuring keeps the line the user
    approved: each `blendingmode`, fed a grey 0.5 and a colour image, against the same mode with nothing connected and
    `opacitymult` 0.5 and 0, which needs no formula per mode; the texts then say what that shows.
  - **Resolution: done**, by measuring.
    - **Test:** in the 8-bit graph, each `blendingmode` blends (0.7, 0.5, 0.3, 1) over (0.2, 0.4, 0.6, 1) with
      `opacity` fed a grey uniform 0.5, a colour uniform (0.5, 0.5, 0.5, 1), and nothing connected at `opacitymult` 0.5
      and 0: the grey one must equal the 0.5 one, the colour one the 0 one, which is the destination, the 0.5 and 0
      blends differing. The modes come from the blend's own enum and must equal `blend_cases.MODES`. On the old script:
      118 checks, 36 failed, the 24 mode lines among them as "no line".
    - **Cause:** TST-792's fix dropped "measured in copy mode", and only copy was measured.
    - **Fix:** measured in all 12 modes (copy, add, substract, multiply, addsub, max, min, switch, divide, overlay,
      screen, softlight), each as copy: GUIDE's core says "in every `blendingmode`", the scripting part's bullet says
      what was measured. A grey other than 0.5 is measured in copy only.
    - **Also covered:** `SHOWN`'s line holds for every mode, unchanged.
  - Questioned by TST-801 (2026-11-23).

- [x] **TST-796 · A functions check's label still calls a Pixel Processor's colour output grey** · `tests/test_all_tools/functions/checks.py:761` · confirmed · follows TST-793, generation 2 · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** `"a Pixel Processor's float: the pixels are Z, grey"`, over `want = {(x, y): [normal(x, y)[2]] * 3 +
    [1.0] ...}`, an RGBA image. TST-793's Also covered names the docstring and the unit test's id, not this label.
  - **Scenario.** A failure message, and a reader of the check, meet the word TST-793 removed.
  - **Fix.** Wording only: "the pixels are Z in R, G and B, alpha 1".
  - **Resolution: done**, wording only: "a Pixel Processor's float: the pixels are Z in R, G and B, alpha 1", passing
    in the scratch run.

- [x] **TST-797 · GUIDE's core bullet leaves to inference that a grey PNG's bitmap works as a mask as it is** · `mcp_server/GUIDE.md:188-190` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** "The bitmap of an 8-bit grey PNG is LUM. For a mask, turn `colorswitch` off, or add Grayscale
    Conversion." Step 2 asks that the bullet say whether a grey PNG works directly; only the scripting part says so.
  - **Scenario.** An agent reading only the core adds a Grayscale Conversion its grey PNG doesn't need.
  - **Fix.** A clause, such as "The bitmap of an 8-bit grey PNG is LUM, a mask as it is."
  - **Resolution: done**, wording only: GUIDE's core says "The bitmap of an 8-bit grey PNG is LUM, a mask as it is.",
    on the check's lines for that PNG.

- [x] **TST-798 · "add Grayscale Conversion" is measured on a colour uniform only, not on the two images the bullet gives it for** · `tests/test_all_tools/facts/checks.py:38` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** The only line is `'Grayscale Conversion of a colour uniform (0.2, 0.4, 0.6, 1)': (0.4, (0.4,))`. GUIDE's
    core gives the advice for a Pixel Processor's float with `colorswitch` on and an RGB PNG's bitmap.
  - **Scenario.** An agent follows it in the demo's own case, a Pixel Processor with `colorswitch` on then Grayscale
    Conversion: a chain never measured.
  - **Fix.** Two feeds: Grayscale Conversion of the Pixel Processor with `colorswitch` on, and of the RGB PNG's bitmap,
    each expecting the grey 0.5 mix; or the sentence narrowed.
  - **Resolution: done**.
    - **Test:** Grayscale Conversion of a Pixel Processor's float 0.5 with `colorswitch` on, and of the RGB PNG's bitmap,
      each expected to give the grey 0.5 mix in the three graphs with both sides; their 12 lines failed as "no line"
      on the old script, then computed LUM 0.50 and the mix.
    - **Fix:** the two feeds; `converted` takes any builder; the scripting part lists the three inputs measured.

- [x] **TST-799 · blend_cases.py's module docstring calls both PNGs grey, one of which the check measures as a colour image** · `tests/test_all_tools/facts/blend_cases.py:2` · confirmed · found 2026-11-23 by a reviewer (Sonnet)
  - **Defect.** "the two grey PNGs saved for it": one is mode L, the other an RGB PNG, which computes RGBA. `pngs()`'s
    own docstring has it right.
  - **Scenario.** A reader takes both for grey images, the confusion TST-793 closed in GUIDE.
  - **Fix.** "a grey PNG (mode L) and an RGB PNG of grey pixels".

  - **Resolution: done**, wording only: "a grey PNG (mode L) and an RGB PNG whose R, G and B are equal".
    - **Also covered:** GUIDE's scripting bullet said "an RGB PNG of grey pixels"; it now says "whose R, G and B are
      equal" in both its lists.

- [x] **TST-800 · GUIDE's core gives "turn `colorswitch` off" right after the RGB PNG's bitmap, which has a `colorswitch` of its own, never measured** · `mcp_server/GUIDE.md:189-190` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** "A Pixel Processor's float with `colorswitch` on, its default, is RGBA, and so is the bitmap of an RGB
    PNG. [...] For a mask, turn `colorswitch` off, or add Grayscale Conversion." The atomic bitmap node has a
    `colorswitch` parameter (Designer's own packages store it on their bitmap nodes); the check sets it on a Pixel
    Processor and a uniform only.
  - **Scenario.** An agent masks a blend with a user's RGB PNG, turns the bitmap's `colorswitch` off, and gets the
    destination still, or a result nobody measured.
  - **Fix.** Name the node: "turn a Pixel Processor's `colorswitch` off" (the uniform's is in the scripting part), or
    measure the bitmap's.
  - **Resolution: done**, wording only: "For a mask, turn a Pixel Processor's `colorswitch` off, or add Grayscale
    Conversion." A bitmap's `colorswitch` is neither measured nor claimed.

- [x] **TST-801 · The mode lines compare an 8-bit grey 0.5, stored as 127 or 128, with an exact `opacitymult` 0.5, at two decimals** · `tests/test_all_tools/facts/checks.py:63-76` · confirmed · follows TST-795, generation 3 · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** `apart and got['grey'] == got['half']`, both computed in the 8-bit graph (`blend_opacity.py`,
    `MODES_GRAPH = '8-bit'`): the grey uniform's 0.5 is 127/255 or 128/255, `opacitymult`'s exact, so a channel may
    differ by an 8-bit step, which changes a `%.2f` string when it falls by an edge.
  - **Scenario.** The check fails on another engine (the live suite runs on Windows too) with Designer's behaviour
    unchanged, where the facts checks are to fail only when a Designer update changes a fact.
  - **Fix.** Generation 3, no new check: the mode blends in the 32-bit float graph, where 0.5 is exact on both paths,
    and GUIDE's "in an 8-bit graph" changed to match.
  - **Resolution: done**.
    - **Test:** no new check (generation 3): the same mode lines, read in the 32-bit float graph; on the old script the
      ids line and the 24 mode checks failed as "no line 'float, ...'", which shows only where they were measured. The
      8-bit lines had passed on this engine: the defect is a risk on another, not reproducible here.
    - **Cause:** the 8-bit graph quantises the grey uniform's 0.5, where `opacitymult`'s is exact.
    - **Fix:** `MODES_GRAPH = 'float'` in the script, with the reason; GUIDE's scripting bullet says "in a 32-bit float
      graph", the docstrings "the float graph". The 12 modes pass there, each colour image giving the destination.
    - **Also covered:** no other text says 8-bit for the mode blends.

- [x] **TST-802 · categories.py's time for facts wasn't re-measured after the check added three computes and about 380 nodes** · `tests/test_all_tools/categories.py:50` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** `facts.run,  # 35 s: Designer facts GUIDE.md relies on`, in a list ordered slowest first, `bitmaps` at
    39 s and `render` at 35 s before it.
  - **Scenario.** `facts` now takes longer than those, and the pool's order and the comment are off.
  - **Fix.** Re-time `facts` and update the comment, and its place if it moved.
  - **Resolution: done**.
    - **Test:** timed as the dated comments around it: two scratch runs of `facts.run` with their server's start,
      53.8 s and 46.7 s, each 186 checks passing (the final check's 53.5 s was taken under its load). The unit tests
      reading `categories.py` pass with the new order.
    - **Fix:** `# 50 s (2026-11-23, two scratch runs, with their server's start: 53.8 s, 46.7 s)`, and `facts.run` moved
      second, after `functions` (136 s), before `params` (46 s).

- [x] **TST-803 · Three of blend_cases.py's types are vaguer than what is known** · `tests/test_all_tools/facts/blend_cases.py:52` · confirmed · found 2026-11-23 by a reviewer (Opus)
  - **Defect.** `by_mode(...) -> dict[str, str]`, a record of four fixed keys (`grey`, `colour`, `half`, `zero`) read
    by key in `checks.py:63-76`; `Feeds = dict[str, tuple[float, tuple[float, ...]]]`, whose fed image is empty, one
    value or four (`:14`); `listed(values: tuple[float, ...])`, called with an `Rgba` only (`:69`).
    `.claude/rules/python.md`, the most specific type.
  - **Scenario.** A misspelt key or a fed image of another length passes mypy.
  - **Fix.** A TypedDict for `by_mode`'s record, `tuple[()] | tuple[float] | Rgba` for the fed image, `Rgba` for
    `listed`.

  - **Resolution: done**, types only: `ModeBlends`, a TypedDict of `grey`, `colour`, `half` and `zero`, for `by_mode`;
    `Feeds` with `tuple[()] | tuple[float] | Rgba` for the fed image; `listed(values: Rgba)`. mypy strict passes.
