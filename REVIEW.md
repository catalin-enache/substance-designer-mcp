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

**Last used:** PLG-45, SRV-286, HLP-325, INS-51, TST-1028, AGT-134.

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
| Low-medium | 0 | 10 |
| Low | 0 | 95 |
| **Total** | **0** | **106** |

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
| 2026-11-27, step 1 (item 85), stopped: the user's Designer was open | Opus (developer) | 1 | 0 | 0 | 284,671 | 8 min |
| 2026-11-27, step 1 (item 85), resumed | Opus (developer) | 1 | 0 | 0 | 231,582 | 34 min |
| 2026-11-27, first round (step 1) | Sonnet | 3 | 14 [1 Low-medium, 13 Low] | 14 [1 Low-medium, 13 Low] | 623,690 | 11 min |
| 2026-11-27, first round (step 1) | settling | 1 | 0 | 0 | 102,740 | 3 min |
| 2026-11-27, the first round's fixes (step 1) | Opus (developer) | 1 | 0 | 0 | 103,088 | 16 min |
| 2026-11-27, second round (step 1's fixes) | Sonnet | 2 | 4 [4 Low] | 4 [4 Low] | 375,883 | 7 min |
| 2026-11-27, second round (step 1's fixes) | settling | 1 | 0 | 0 | 78,289 | 2 min |
| 2026-11-27, the second round's fixes (step 1) | Opus (developer) | 1 | 0 | 0 | 26,755 | 4 min |
| 2026-11-27, step 2 (item 88) | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 583,983 | 37 min |
| 2026-11-27, first round (step 2) | Sonnet | 3 | 11 [11 Low] | 11 [11 Low] | 671,633 | 13 min |
| 2026-11-27, first round (step 2) | settling | 3 | 0 | 0 | 311,147 | 4 min |
| 2026-11-27, the first round's fixes (step 2) | Opus (developer) | 1 | 0 | 0 | 116,011 | 18 min |
| 2026-11-27, second round (step 2's fixes) | Sonnet | 2 | 3 [3 Low] | 3 [3 Low] | 425,487 | 12 min |
| 2026-11-27, the second round's fixes (step 2) | Opus (developer) | 1 | 0 | 0 | 23,096 | 3 min |
| 2026-11-27, step 3 (item 84), stopped for two proposals | Opus (developer) | 1 | 0 | 0 | 399,003 | 16 min |
| 2026-11-27, step 3 (item 84), resumed | Opus (developer) | 1 | 1 [1 Low] | 1 [1 Low] | 272,979 | 45 min |
| 2026-11-27, first round (step 3) | Sonnet | 3 | 15 [2 Low-medium, 13 Low] | 15 [2 Low-medium, 13 Low] | 728,764 | 13 min |
| 2026-11-27, first round (step 3) | settling | 2 | 0 | 0 | 264,906 | 12 min |
| 2026-11-27, the first round's fixes (step 3) | Opus (developer) | 1 | 0 | 0 | 143,166 | 29 min |
| 2026-11-27, second round (step 3's fixes) | Sonnet | 2 | 6 [1 Low-medium, 5 Low] | 6 [1 Low-medium, 5 Low] | 464,533 | 10 min |
| 2026-11-27, second round (step 3's fixes) | settling | 2 | 0 | 0 | 260,339 | 8 min |
| 2026-11-27, the second round's fixes (step 3) | Opus (developer) | 1 | 0 | 0 | 77,067 | 16 min |
| 2026-11-27, third round (step 3's fixes) | Sonnet | 1 | 3 [3 Low] | 3 [3 Low] | 226,962 | 10 min |
| 2026-11-27, third round (step 3's fixes) | settling | 1 | 0 | 0 | 103,420 | 2 min |
| 2026-11-27, the third round's fixes (step 3) | Opus (developer) | 1 | 0 | 0 | 26,602 | 5 min |
| 2026-11-27, first Opus round (the whole branch) | Opus | 4 | 12 [1 Medium, 1 Low-medium, 10 Low] | 12 [1 Medium, 1 Low-medium, 10 Low] | 1,216,371 | 19 min |
| 2026-11-27, first Opus round (the whole branch) | settling | 3 | 0 | 0 | 437,850 | 7 min |
| 2026-11-27, the first Opus round's fixes | Opus (developer) | 1 | 1 [1 Low-medium] | 1 [1 Low-medium] | 700,389 | 73 min |
| 2026-11-27, second Opus round (the first one's fixes) | Opus | 3 | 7 [1 Low-medium, 6 Low] | 7 [1 Low-medium, 6 Low] | 779,720 | 18 min |
| 2026-11-27, second Opus round (the first one's fixes) | settling | 2 | 0 | 0 | 297,615 | 5 min |
| 2026-11-27, the second Opus round's fixes | Opus (developer) | 1 | 0 | 0 | 66,978 | 16 min |
| 2026-11-27, HLP-316's fix (the user's choice) | Opus (developer) | 1 | 0 | 0 | 86,918 | 21 min |
| 2026-11-27, third Opus round (the second one's fixes) | Opus | 2 | 4 [1 Low-medium, 3 Low] | 4 [1 Low-medium, 3 Low] | 439,423 | 10 min |
| 2026-11-27, third Opus round (the second one's fixes) | settling | 1 | 0 | 0 | 145,114 | 3 min |
| 2026-11-27, the third Opus round's fixes | Opus (developer) | 1 | 0 | 0 | 55,432 | 16 min |
| 2026-11-27, fourth Opus round (the third one's fixes) | Opus | 1 | 3 [1 Low-medium, 2 Low] | 3 [1 Low-medium, 2 Low] | 225,117 | 12 min |
| 2026-11-27, fourth Opus round (the third one's fixes) | settling | 1 | 0 | 0 | 103,337 | 4 min |
| 2026-11-27, the fourth Opus round's fixes | Opus (developer) | 1 | 0 | 0 | 24,902 | 6 min |
| 2026-11-27, HLP-321's fix (the user's choice) | Opus (developer) | 1 | 0 | 0 | 222,658 | 25 min |
| 2026-11-28, Opus round of the whole branch | Opus | 4 | 10 [1 Low-medium, 9 Low] | 10 [1 Low-medium, 9 Low] | 1,379,161 | 18 min |
| 2026-11-28, Opus round of the whole branch | settling | 2 | 0 | 0 | 192,650 | 3 min |
| 2026-11-28, the whole-branch round's fixes | Opus (developer) | 1 | 0 | 0 | 207,834 | 34 min |
| 2026-11-28, Opus round of the whole-branch round's fixes | Opus | 2 | 6 [6 Low] | 6 [6 Low] | 427,478 | 11 min |
| 2026-11-28, the last round's fixes | Opus (developer) | 1 | 0 | 0 | 38,665 | 6 min |
| 2026-11-28, the last Opus round of the whole branch | Opus | 4 | 3 [3 Low] | 3 [3 Low] | 1,312,468 | 15 min |
| 2026-11-28, the last round's fixes | Opus (developer) | 1 | 0 | 0 | 31,092 | 6 min |
| 2026-11-28, the user's answers at convergence | Opus (developer) | 1 | 0 | 0 | 47,816 | 11 min |
| 2026-11-28, Sonnet round of the user's answers | Sonnet | 1 | 2 [2 Low] | 2 [2 Low] | 144,739 | 5 min |
| 2026-11-28, the Sonnet round's fixes | Opus (developer) | 1 | 0 | 0 | 36,284 | 10 min |
| **Total** | | 79 | 106 [1 Medium, 10 Low-medium, 95 Low] | 106 [1 Medium, 10 Low-medium, 95 Low] | 15,545,807 | 692 min |

## Review log

### 2026-11-27: step 1 of branch view3d-text-shader-mesh (ROADMAP item 85, the 3D view as text)

- **Scope:** `git diff 1ac1b45 e3b9824 -- . ':(exclude)PLAN.md'`.
- **How:** three Sonnet reviewers: the production code (`mcp_server/server_tools`, `mcp_server/designer_helpers`),
  the tests (unit and live), and the docs (Markdown, docstrings, descriptions). No tests run. One runner probe, in a
  Designer of its own (port 9911): whether `_pose_said`'s `abs(at.pitch) <= 90` says "over the pole" for Designer's
  Top or Bottom. Measured: no. Designer's own Top and Bottom on Plane, Sphere and Cylinder, docked and floated, saved
  a pitch of ±89.9999966; the tool's written Top and Bottom, loaded and saved again, came back as Designer's own; the
  written matrices rounded to 32-bit floats decode to exactly ±90 (18 saved cases, 24 computed). Dropped as fine or
  not worth a fix: `_rounded`'s "2 decimals" with `%g` (it differs only for lengths of 10,000 or more); the set-up no
  longer looking up the asked mesh's own Scene entry (the `MENUS` fact checks every `MESHES` name is a Scene entry, and
  Save and Reset Scene are still looked up first); `_overrides` raising without a Materials menu (the dock refusal
  needs a built 3D view, which has one); as_text's 60 s limit (the same Save fits in a shot's budget, no evidence
  against it); `SHOWN_ALREADY`'s `float()` of a tiling said `not read` (its Plane has one material); a reflowed line
  in an untouched docstring (style); item 85's kept Note (the rows' convention). A rotation beyond ±180 set in
  Designer's panel, said and then refused when given back, was not probed: SRV-281's narrowed wording holds either way.
- **Not verified:** none.
- **Resolutions assessed:** none in scope (REVIEW.md cleaned up before the branch).
- **Findings:** TST-960 (Low-medium); SRV-281, SRV-282, HLP-295, TST-961 to TST-970 (Low). Merged: SRV-281 (code and
  docs reviewers), HLP-295 (code and docs), TST-961 (code and docs), TST-963 (docs and tests), TST-965 (docs and
  tests).
- **Suggested order:** TST-960 first (a guard for the user's screen), then the docs together (SRV-281, SRV-282,
  HLP-295, TST-961 to TST-964), then the tests (TST-965 to TST-970).
- **Checked and found fine:** `_3d_shown`'s backup, Save and put-back on every path (an error, a refused Save, an abort
  landing in the put-back, a leftover backup put back first and said); the refusal when the Default State File changed
  since Designer started; the server's refusals before the bridge (another panel, a set-up option, a crop) and the
  options that set nothing accepted; the said numbers' 32-bit round trip within the options' ranges, the rotation
  through `DEGREES_PER_TURN`; the renderer from the title's last `' - '`; the known-view check's values, each unlike
  Designer's defaults; the title check, which fixes the list of renderers and covers box.fbx; the new live checks'
  cleanup through `state_file.kept`; the older tests turned to `_mesh_shown`, not weakened; the parameter guard, which
  rests on the one literal `as_text` call in `check_the_3d_view_as_text_says_a_known_view_and_the_camera_it_drew`.

### 2026-11-27: the fixes of step 1's first round (branch view3d-text-shader-mesh)

- **Scope:** `git diff e3b9824 9137841 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the code and the tests, and the docs; each rechecked the resolutions in its area. No
  tests run. One runner probe, in a Designer of its own (port 9891), for a suspicion following HLP-295 (the narrowing
  to "hidden" leaves a minimized or covered Designer unmeasured): a known state loaded and settled on screen, then
  as_text through the tool with Designer minimized, covered by a window of Designer's own, and hidden. Measured: the
  first six lines equal `KNOWN_SAID` in all five runs (minimized and covered twice each, hidden once), and the window
  was left as it was. Settled as wrong; a note under HLP-295. Dropped as fine or not worth a fix: TST-960's count of
  failing tests (the fake replaces the names, so a call anywhere in `_3d_shown` trips the guard); `nturl2path`'s
  deprecation in Python 3.14 (the venv runs 3.12); a README line of 133 characters (style); the `urls_as_windows`
  fixture's docstring citing item 90 (a test comment, which misleads no one).
- **Not verified:** none.
- **Resolutions assessed:** all 14 rechecked. TST-967, SRV-281 and TST-962 questioned (TST-971, TST-972, SRV-283);
  the other 11 hold.
- **Findings:** TST-971, TST-972, SRV-283 and TST-973 (Low). Longest chains still growing: TST-967 → TST-971, SRV-281
  → TST-972 and TST-962 → SRV-283, generation 2 each. A few Low ones: step 1's reviews are done once they are fixed.
- **Checked and found fine:** TST-960's guard reaches every test of the fake, and the set-up never calls the guarded
  names; TST-966's fixtures patch `url2pathname`, which `state3d.py` reads at call time, and the older TST-926 tests use
  them; TST-968's refusal comes before the backup; TST-969's pattern can't match the message's fixed words; TST-970's
  test goes through `_state_changes`; SRV-282's paragraph matches `_3d_shown`; HLP-295's "hidden" in every place that
  was about the Save; TST-961, TST-963, TST-964 and TST-965 as fixed; the tool's description under 4,096 characters.

### 2026-11-27: step 2 of branch view3d-text-shader-mesh (ROADMAP item 88, the shader model)

- **Scope:** `git diff 31b49a4 d620c6b -- . ':(exclude)PLAN.md'`.
- **How:** three Sonnet reviewers: the production code, the tests, and the docs. No tests run. Three runners, each in
  a Designer of its own, for four suspicions reading couldn't settle; each settled as wrong:
  - a Save before the 3D view drew lacks the renderer plugin's section, so `shader_model=` as a Designer's first 3D
    call would be refused and as_text would say `shader_model: not read`: no (port 9921). In a fresh Designer with a
    graph open, both calls answered as asked, and the first Save, before any 3D call, held the section and the used
    material's entry. Only a test's comment says otherwise: TST-979;
  - the shader place under the GPU Pathtracer (`state3d.py`'s "each place once"): one name for the used material,
    as under the Rasterizer (port 9922);
  - the name-only edit from a base on another model (UsdPreviewSurface, a red material) against Designer's menu pick:
    0 of 52 parameters differing for OpenPBR Surface, 0 of 45 for AdobeStandardMaterial, renders pixel-identical, the
    base back after the shot (port 9922);
  - `graph=` with `shader_model=` on an unlinked view, and the relink of the editor's graph after the model's load:
    the asked model held at the render in all seven shots, UsdPreviewSurface included, and the base's after (port
    9921). The missing guard is TST-982.
  Dropped as fine or not worth a fix: tests/unit/test_state3d.py's said test comparing `said[2:6]` (the whole list is
  pinned by `test_a_saved_file_is_said_in_the_tools_own_terms`); `shader_model`'s parameter guard seen only through a
  refusal's literal (as `environment`, `mesh` and `view` are); one measurement told in several docstrings (consistent);
  `opacityMode` missing from the materials list in a set-up's Save (default-valued, renders identical, put back).
  Two reviewers wrote a diff into the scratchpad against their rules; both files were deleted.
- **Not verified:** none.
- **Resolutions assessed:** SRV-281 (questioned by HLP-296) and TST-973 (questioned by TST-976); TST-972, TST-964,
  SRV-282 and SRV-283 hold.
- **Findings:** SRV-284, HLP-296, HLP-297, TST-974 to TST-982 (Low); TST-978 the developer's. Merged: SRV-284 (code
  and docs reviewers), HLP-296 (all three), TST-974 (docs and code), TST-979 (docs and tests), TST-980 (tests and
  docs). Longest chains still growing: SRV-281 → TST-972 and → HLP-296, TST-973 → TST-976, generation 2.
- **Suggested order:** the docs together (TST-974, SRV-284, HLP-296, HLP-297, TST-975 to TST-977, TST-979), then the
  tests (TST-978, TST-980 to TST-982).
- **Checked and found fine:** tiling reads and writes as before through `PER_MATERIAL` (the same pattern once
  formatted); the shader anchor on Designer's own saved files, matching the used material's entry only; the
  several-materials refusal on `asked` before anything changes, a mesh switch skipping it as HLP-114 settled; the
  section's rules for the new field (shown already, counted, said, put back, said as text, STALE); the positional
  chain views.py → `shoot_3d` → `_3d_set_up` → `_set_up_checked`; the server's gate; the unit tests that fail
  without the change (the per-material branch, `_state_changes`, the pins, the refusals); the fixture's plugin
  section, which no test passes on only by its cut; every new live check's cleanup through `state_file.kept`.

### 2026-11-27: the fixes of step 2's first round (branch view3d-text-shader-mesh)

- **Scope:** `git diff d620c6b 6012a43 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the code and the tests, and the docs; each rechecked the resolutions in its area. No
  tests run, no probe needed. Dropped as not worth a fix: `state_file.at_the_render` without a unit test (test
  scaffolding of a live check, which fails, never passes, on a broken parse); item 83's "names both cases" where the
  STALE line names three (no reader acts differently); `held_shader`'s module (style). Two notes added under resolved
  entries: TST-978 (the shader row's load switches the mesh back too, safely) and TST-982 (only the second shot is
  checked for "no longer follows").
- **Not verified:** none.
- **Resolutions assessed:** the twelve of step 2's first round rechecked. TST-979 questioned (TST-983); the other
  eleven hold.
- **Findings:** TST-983, HLP-298 and TST-984 (Low). Merged: TST-983 (both reviewers). Longest chains still growing:
  TST-979 → TST-983, generation 2. A few Low ones: step 2's reviews are done once they are fixed.
- **Checked and found fine:** TST-978's unit test fails without the `follows` alternative and asserts its replaces
  hit; TST-981's guard fails on the old snippet, shares the existing placeholder filler, and the other names the
  snippets bind are deliberate overrides; TST-982's keyword options exist in `shoot_3d`'s signature, `LINKED=` can't
  pass on a stale textures' folder, and the check cleans up through `kept`; SRV-284, HLP-296, HLP-297, TST-974 to
  TST-977 and TST-980 as fixed; no `noqa`, `type: ignore`, `cast`, skip or sleep added.

### 2026-11-27: step 3 of branch view3d-text-shader-mesh (ROADMAP item 84, the user's own mesh)

- **Scope:** `git diff 1a24483 d110304 -- . ':(exclude)PLAN.md'`.
- **How:** three Sonnet reviewers: the production code, the tests and the committed mesh, and the docs. No tests run.
  Two runners, each in a Designer of its own (ports 9941 and 9942):
  - a corrupt `x.fbx` through the tool (measured, HLP-299): `mesh=` alone took 32 s and showed an empty view;
    with `zoom=1` or `view='Top'`, 36 s and an image of the user's own mesh (the second load's Save held the
    base's Rounded Cube); with `tiling=2`, refused after 32 s as "the 3D view's mesh uses 0 materials"; each line
    said "hadn't settled within 3 s";
  - paths written `file://` + the path (measured, HLP-300): a space, `é` in NFC and NFD, and `&` import and are
    saved back as written; `#`, `?` and a literal `%20` don't import (30 s, the Save holds no mesh). A mesh dropped
    on the view is saved as `QUrl.fromLocalFile(path).toString()`: space and `é` as written, `#`, `?` and `%` as
    `%23`, `%3F` and `%25`, and those forms import when written so;
  - the Materials menu during a load (OBJ, box.fbx, Samba, OBJ, box.fbx): as Reset Scene returns, only Default,
    unused, every time; the earlier file's materials aren't listed (HLP-304);
  - settled as wrong: box.fbx's `Default (overridden)` doesn't depend on an earlier check (the same in a fresh
    Designer, box.fbx the only load); the geometry checks see an empty scene, through the state saved at the
    render (`rendered()` is False for a corrupt file; the Samba case's `shown` is 0.0 on an empty render).
  Dropped as not worth a fix: `framed`'s Save deleting the textures' folder before the put-back's load (it needs a
  view showing a graph's outputs, a mesh file with camera or material options, and a failed relink; the user's files
  come back byte for byte from the backup); a valid import slower than 30 s while the put-back runs (very unlikely);
  an STL or PLY whose import lists no material in use (not checked live, as the docs say; HLP-299's fix makes such a
  wait say so); `framed` without a `_same_pose` skip (an extra import, no bug); every set-up looking up Camera >
  Frame (the menu has it). Settled as wrong by reading: `mesh=''` was read as none before this diff too (`mesh or
  None`, at 1a24483).
- **Not verified:** none.
- **Resolutions assessed:** SRV-281 (questioned again by HLP-301); HLP-286 and HLP-289's fixes are replaced by the
  import wait, with no regression found but HLP-299's case.
- **Findings:** HLP-299 and HLP-300 (Low-medium); SRV-285, HLP-301 to HLP-305, TST-985 to TST-992 (Low); TST-992
  the developer's. Merged: HLP-299 (all three reviewers), TST-986 (docs and code). Longest chain still growing:
  SRV-281 → HLP-296 → HLP-301, generation 3.
- **Unspecified:** a credit line for the Mixamo character in README (its License section says MIT), and a word on
  the `assets/` folder: for the user (PLAN.md, Waiting for the user).
- **Suggested order:** HLP-299 and HLP-300 first; then TST-992 (a live check failing); then the rest.
- **Checked and found fine:** the server's path handling (a name without an extension or a separator sent as given,
  `_local_path`, the extension, `isfile`, before any temporary folder); `_set_up_checked`'s refusals before anything
  changes; the material fields kept apart (`own`, `owns`) matching the old reads for presets; shown already (no
  load, no camera write; with `view`, Frame and one load); `done` set before each wait, so an error after the first
  load says what was set and puts the view back; the import wait under waits.md (the frames watch's `until`, the
  limit a safety net, every load of a user's mesh through it, the put-back's and a reload included); `_Frames.restarted`
  removed with no caller left; the committed OBJ (1000 units a side, y 0 to 1000, two objects, faces wound outward,
  both colours from the Default view); every new live check's cleanup through `state_file.kept`.

### 2026-11-27: the fixes of step 3's first round (branch view3d-text-shader-mesh)

- **Scope:** `git diff d110304 e762c53 -- . ':(exclude)PLAN.md'`.
- **How:** two Sonnet reviewers: the code and the tests, and the docs; each rechecked the resolutions in its area. No
  tests run. Two runners, each in a Designer of its own:
  - TST-992's cause (port 9951; measured, HLP-306): the viewport's size is the same read hidden, on screen and after
    each Frame (10 runs at 300 x 500 and 400 x 500, 11 more in sweeps), so an early read isn't it. Designer's Frame
    of a tall viewport follows `max(1, sin(A) / sin(A * h/w))`, where the table keeps the base distance: it matched
    18 sizes to 3 decimals (1.352 at 161 x 423, 1.518 at 156 x 423, 14.664 at 161 x 523, 1.000 at 0.44 and wider,
    and below about 0.30). At 300 x 500 the floating dock settles 300 to 358 wide between floats, so the old check
    failed in 4 of 5 runs; the tool's own `view='Top'` wrote the table's 147.780 where Designer framed 199.795 and
    224.311;
  - `graph=` after a mesh file that didn't import (port 9952; measured, HLP-307): 34 s, no dialog or new window in
    1,113 ticks, an empty render, the line "graph ...'s outputs on the mesh";
  - nine more characters (port 9952; measured, HLP-308): `"`, `<`, `>`, `^`, a backtick, `{`, `|`, `}` and `\`
    import as written, but Designer saves each as Qt's `%22` to `%5C`.
  Settled as wrong: `scene3d.py`'s "a Save holds no mesh" for a file that didn't import (the runner's earlier probe
  agrees: the second load's Save held Designer's default, a meshless file loading as Designer's defaults); no scratch
  run of the changed `IMPORTED` (the developer's three scratch runs ran the import check). Dropped as not worth a
  fix: the tool docstring's general "shoot again" beside the unimported file's own advice (the specific one wins);
  a 170-column docstring line (style).
- **Not verified:** none.
- **Resolutions assessed:** the sixteen of step 3's first round rechecked. TST-992 (questioned by HLP-306), HLP-299
  (by HLP-307), HLP-300 (by HLP-308), TST-986 (by TST-993) and TST-990 (by TST-994); the other eleven hold.
- **Findings:** HLP-306 (Low-medium); HLP-307, HLP-308, TST-993, TST-994 and TST-995 (Low). Merged: HLP-306 (code and
  docs reviewers). Longest chains still growing: five at generation 2.
- **Checked and found fine:** HLP-299's re-read after the load, every path reaching the put-back, both unit tests
  failing without the fix; HLP-300's encoding against `url2pathname`'s decoding; HLP-303's up-front read with a
  preset switch unchanged; TST-988's `first`; SRV-285, HLP-301, HLP-302, HLP-304, HLP-305, TST-985, TST-987 and
  TST-989 as fixed; no `type: ignore`, `noqa`, `cast`, skip or sleep added.

### 2026-11-27: the fixes of step 3's second round (branch view3d-text-shader-mesh)

- **Scope:** `git diff ff1e02d c985179 -- . ':(exclude)PLAN.md'`.
- **How:** one Sonnet reviewer, the whole diff (8 files, +159 -68), rechecking the six resolutions. No tests run. The
  band's start checked by arithmetic: FRAME_ANGLE is 54.43 degrees, so the law exceeds 1 only past 125.57 degrees
  (183 x 423 gives 1.0032, 186 x 423 gives 1.0). One runner (port 9971; measured, HLP-310): of `[`, `]`, `'`, `+`,
  `;`, `=`, `@`, `$`, `!`, `(`, `)`, `*`, `~`, `,` and `:`, Designer saves `[` and `]` as `%5B` and `%5D`, the others
  as written; all imported; Qt's `QUrl.fromLocalFile(path).toString()` matched the saved id in every row. Settled as
  wrong: the resolutions' missing live passes (the developer's scratch runs passed 12 of 12, twice; notes added under
  HLP-307 and HLP-308, and the counts corrected under HLP-306 and HLP-308). Dropped as not worth a fix: `_framing`
  beyond the measured range (a dock under 151 px wide for 1000 tall; the docstring says the law is measured up to 3.87
  times as tall as wide); no unit test pairing an imported mesh file with `graph=` (the live box case covers it); a
  156-column docstring line (style).
- **Not verified:** none.
- **Resolutions assessed:** the six rechecked. HLP-306 (questioned by TST-996), HLP-307 (by HLP-309) and HLP-308 (by
  HLP-310); the other three hold, and all six hold as fixes.
- **Findings:** TST-996, HLP-309 and HLP-310 (Low). Longest chains: TST-992 → HLP-306 → TST-996, HLP-299 → HLP-307 →
  HLP-309, HLP-300 → HLP-308 → HLP-310, generation 3; TST-996 and HLP-309 narrow only, HLP-310 is a defect in the
  tool's code. A few Low ones: step 3's reviews are done once they are fixed.
- **Checked and found fine:** HLP-306's law equal to the old value for every wide viewport, giving each measured tall
  size, every caller through `_framing`, the check's table from the viewport it reads; HLP-307's skips in all four
  combinations, the view put back on every path, a shot whose import ended still putting the outputs on the mesh;
  HLP-308's one-pass table against `url2pathname`'s decoding, the eight checks on `_mesh_id`; TST-993, TST-994 and
  TST-995 as fixed.

### 2026-11-27: the whole branch against main, first Opus round

- **Scope:** `git diff main...677bf40 -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'` (28 files, +2,643 -477).
- **How:** four Opus reviewers: the production code, the unit tests, the live checks and the meshes, and the docs;
  each rechecked the resolutions in its area. No tests run. Three runners, each in a Designer of its own:
  - `graph=` on a mesh of several materials (port 9981; measured, HLP-312): Designer's "View Outputs In 3D View"
    opens a second QMenu, `materialSelectionMenu`, listing the mesh's materials; no dialog or modal (210 state
    changes of a 20 ms watch); nothing picks, so `MENU_GUARD` closes it after 5 s and the call fails ("a menu was still
    open 5 s after ..."), on the OBJ in 10.2 s and on the Samba FBX in 12.3 s; `.trigger()` on an entry does nothing,
    Down then Return picks it, one material per pick, picks adding up; the relink of a view following a graph on the
    OBJ lost 5 s twice and left the view no longer following it;
  - a preset switch from a mesh file's view (port 9982; measured, HLP-311): a two-material base refused
    `mesh='Plane', tiling=4` as "uses 2 materials (first, second)"; a one-material base (`only`) took tiling 4 and
    UsdPreviewSurface into `only` while the Plane rendered `default`, untouched; a Plane loaded over that base maps to
    `default`, the file's entry left in the table, so `tiling=3` alone was refused then; a mesh file's own one
    material (`only`) took tiling 2 and UsdPreviewSurface (settled as wrong: the suspicion that a file's own material
    has no plugin entry);
  - the render after a mesh file's reload (port 9983; settled as wrong): ten shots over the Samba FBX (an orbit, an
    exposure) read 8 samples at the render each time; each load showed two restarts, the import's 2.2 to 3.7 s after
    the trigger, and the wait returned after the second reached 8.
  Settled as wrong: as_text's mesh line for a fresh Designer (a runner measured `mesh: Rounded cube`, step 2's
  round). Dropped as not worth a fix: the put-back's relink after a base whose file no longer imports (no harm, its
  line claims nothing); ending a corrupt file's wait early on Designer's log (rare, KISS); the shader check's editor
  put back outside a `finally` (nothing depends on it); a test comment's "exactly ten times" beside `alike`'s
  tolerance.
- **Not verified:** none.
- **Resolutions assessed:** all 58 rechecked by area. HLP-303 (questioned by HLP-311), TST-985 (by TST-997), HLP-310
  and HLP-306 (by HLP-314); the others hold.
- **Findings:** HLP-312 (Medium); HLP-311 (Low-medium); HLP-313, HLP-314, TST-997 to TST-1004 (Low). Merged: HLP-311
  (code and docs reviewers).
- **Decided by the user (2026-11-27):** `graph=` on a mesh of several materials puts the outputs on every material
  ("Every material", HLP-312's Fix).
- **Unspecified:** how long `facts` takes now (about a dozen new checks with mesh imports and a 35 s corrupt-file shot)
  against `categories.py`'s 196 s and `workers.py`'s start order: the final check measures it.
- **Checked and found fine:** the set-up with every option at once (the first load the mesh and light, the refusal
  after the import, Frame, the Save and the second load, the graph step last, every path reaching the put-back); a
  mesh file shown already with and without `view`; no mesh file framed as the cube; as_text on each kind of view; the
  user's file and textures' folder through as_text and an abort; the server's path handling before any temporary
  folder; the import wait and its bounded event passes; the bridge's 120 s above three 30 s imports; the three
  steps' Docs lists done; the GUIDE core (8.7 K of 14 K) and the tool's docstring (3.1 K of 4,096); every live check's
  cleanup and run order; the committed meshes as their header says.

### 2026-11-27: the fixes of the first Opus round, second Opus round

- **Scope:** `git diff dc5d1d0 e22fa6b -- . ':(exclude)PLAN.md'` (14 files, +994 -218).
- **How:** three Opus reviewers: the production code, the tests, and the docs; each rechecked the resolutions in its
  area. No tests run. Two runners, each in a Designer of its own:
  - `shader_model=` on a Scene menu's mesh whose Default has Override Material off (port 9995; measured, HLP-316,
    raised by the developer): on the Rounded Cube and the Plane, each linked and unlinked, the model was not taken
    with Override off (OpenPBR Surface in the Save at the render, the render pixel-identical to a plain shot) and
    taken with it on; the shot said "shader model AdobeStandardMaterial" either way, the off cases adding only STALE's
    general line;
  - whether Designer reuses `materialSelectionMenu` (port 9996; settled as wrong): a new menu each opening, the kept
    wrappers invalid after it closed, and three openings after the tool's shot at full opacity and clickable, so
    `unfade` giving back only the native window's look is enough.
  Dropped as not worth a fix: two materials of one name collapsing into one key (extreme for real assets); a menu
  opening after the material pick within the same action (unmeasured, unlikely); a relink failing on its second
  material said as "no longer follows" (rare); a fade error on the material menu said as the Explorer's (rare); the
  time per material for assets of tens of materials (one Explorer menu round each, unmeasured, far within 120 s for
  the assets measured); the unit fake standing in for the look's timer by its starts (an unlikely mutation); six facts
  checks failing in a Designer that had run editor_panels_and_fit's checks first (the suite gives each category a
  Designer just started; the final check runs `facts` whole); `facts/state_file.py`'s list of what the checks
  re-measure leaving out the two new facts (nothing false).
- **Not verified:** none.
- **Resolutions assessed:** HLP-311 (questioned by HLP-316 and TST-1009), HLP-313 (by HLP-317), TST-1004 (by TST-1006),
  HLP-312 and HLP-315 (by TST-1007); the others hold.
- **Findings:** HLP-316 (Low-medium); HLP-317, TST-1005 to TST-1009 (Low). Merged: HLP-316 (the developer and three
  reviewers), HLP-317 (three reviewers).
- **Unspecified:** as_text's `Override Material: on, off` line names no material, and the menu lists the overridden
  ones first (raised by three reviewers); the material menu made click-through as the Explorer's is, where DECISIONS.md
  names the Explorer's: both for the user (PLAN.md, Waiting for the user).
- **Checked and found fine:** the material menu's handling (the look started again before the pick, the Explorer's
  menu skipped while the action runs, a menu closed with none picked raising with the materials named, another menu
  left to the guard, `unfade` on every path, aborts included); `_materials_linked`; HLP-311's `_used_material`,
  `_state_edited` writing the mesh first, `meshed` and `later`; HLP-315's callers; every new test failing without its
  fix but TST-1007's two guards; both new live checks' cleanup; nothing silenced.

### 2026-11-27: the fixes of the second Opus round, third Opus round

- **Scope:** `git diff e22fa6b f9eb277 -- . ':(exclude)PLAN.md'` (10 files, +311 -85).
- **How:** two Opus reviewers: the code and the tests, and the docs. No tests run. One runner (port 9997; settled as
  wrong): the Materials menu's Override checks and the file's `override_existing_material` agreed in all 27 rows of 14
  Saves (the Rounded Cube as started, the Plane with and without a graph's outputs and with Default off, the OBJ with
  `first` on, off and linked, the Plane over the OBJ's state) for every material with a menu entry; the menu lists none
  for Default on the Rounded Cube as Designer starts (the file holds it true) and none under the OBJ (the file holds it
  false, and the OBJ refuses `shader_model=` anyway); a switch from the Plane with Default off to the Cube turned it
  back on in both. Dropped as not worth a fix: `_state_overridden` refusing after `begin()` (every file measured holds
  the element; one put-back load at worst); SHOWN_ON said beside UNIMPORTED for a base whose file no longer imports (an
  extreme case); a material whose file name and menu name differ (they matched for every asset measured); the fake's
  `loaded_materials` turning every material on at a load (no later check depends on it).
- **Not verified:** none.
- **Resolutions assessed:** HLP-316 holds for every path it names, not for a model held already (HLP-318); HLP-317,
  TST-1005 to TST-1009 hold; HLP-316's docs questioned by HLP-319, TST-1010 and HLP-320.
- **Findings:** HLP-318 (Low-medium); HLP-319, HLP-320, TST-1010 (Low). Merged: HLP-318 (both reviewers). Longest
  chain still growing: HLP-303 → HLP-311 → HLP-316 → HLP-318, generation 4 (a defect in the tool's code).
- **Decided by the lead, by the user's choice:** a model held already but hidden by Override off isn't shown already,
  so HLP-318's fix turns Override on for it too ("Render with Override on" names every shot with `shader_model=`).
- **Unspecified:** a shot with `shader_model=` compared with a plain shot mixes Override's own effect into the
  difference, where comparing two models doesn't; no doc says so.
- **Checked and found fine:** `_state_overridden`'s regex inside the used material's entry; `_material_name`;
  `turned_on` (each name once, SHOWN_ON once, after the graph step); the put-back clearing `turned_on` before its load
  and relink; every new unit test failing without its fix; the new live check's cleanup; README and GUIDE still true.

### 2026-11-27: the fixes of the third Opus round, fourth Opus round

- **Scope:** `git diff f9eb277 7779e7c -- . ':(exclude)PLAN.md'` (7 files, +113 -69).
- **How:** one Opus reviewer, the whole diff. No tests run, no probe needed for its findings. Dropped as not worth a fix:
  `framed`'s "when they differ" said of the camera too (it is written whenever a camera option is given; generation 5,
  changes nothing anyone does); "in both" at `scene3d.py:107` (the menu and the file, as the log says); `graph=` with a
  held model and Override off taking a load before the graph step turns Override on anyway (time, no wrong result,
  KISS); the live check's fallback to OpenPBR when a Save names no Default (it can't pass falsely).
- **Not verified:** none.
- **Resolutions assessed:** HLP-318, HLP-319, HLP-320 and TST-1010 hold; HLP-318's docs questioned by SRV-286.
- **Findings:** SRV-286 and TST-1011 (Low). A few Low ones: the Opus rounds on the fixes are done once they are fixed;
  an Opus round of the whole branch follows.
- **Outside scope, probed (port 9998; measured, HLP-321):** on the Plane with a pattern graph's outputs, a tiling of 4
  rendered 5.8 grey levels apart from a plain shot on average with Default's Override on, and pixel-identical with it
  off, the result saying "tiling 4" and STALE's line, which doesn't name Override; the user then chose (2026-11-27,
  "Same as shader_model") that `tiling=` turns Override on as `shader_model=` does.
- **Checked and found fine:** `model_shown` at its two sites (the first load on `meshed`, `framed`'s Save), a model held
  with Override on still taking no load (a unit row, and `SHOWN_ALREADY` after a check that turns every Override back
  on), a model held with Override off written overridden, said and put back on every path; the new test cases failing
  without the fix; the several-materials refusal still before `model_shown`; nothing silenced.

### 2026-11-28: the whole branch against main, Opus round after the fixes

- **Scope:** `git diff main...3eccaac -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'` (29 files, +3,917 -623).
- **How:** four Opus reviewers: the production code, the unit tests, the live checks and the meshes, and the docs;
  each rechecked the resolutions in its area. No tests run. Two runners, each in a Designer of its own:
  - a mesh file over another mesh file's view (port 9999; measured, HLP-322): over the two-material OBJ, `mesh=<a
    one-material OBJ>` with `tiling=2` or `shader_model=` was refused as "uses 3 materials (first, only, second)", and
    the reverse too; the mapping table held `['first', 'only', 'second']` after either load;
  - the put-back of a model and a tiling written with Override off (port 9990; settled as wrong): after
    `shader_model='AdobeStandardMaterial'` and after `tiling=4` on the Plane with Default's Override off, a Save held the
    user's OpenPBR Surface and tiling 1, still after Override was turned on, and a plain render matched the baseline
    (0.000); the controls with Override on the same. The live check pins only Override after the put-back: TST-1020.
  Dropped as not worth a fix: the KeyError in `check_a_scene_menus_mesh_shot...`'s `judged` when the OBJ missed its
  30 s import (DECISIONS.md, Low-value findings); `_state_overridden`'s refusal without a unit test (every file measured
  holds the element once); the fake's Scene menu not following a preset loaded over a mesh file's base, and the fake
  listing Default's Override entry for a preset with no outputs (no test passes wrongly; the fake's docstring says so).
  The code reviewer found no defect in the production code.
- **Not verified:** none.
- **Resolutions assessed:** all 85 rechecked by area. SRV-286 (questioned by TST-1012), HLP-312 (by TST-1013), HLP-321
  (by TST-1014), TST-999 (by TST-1016), TST-1008 (by TST-1019), HLP-316 (by TST-1020; a note added for its unit test's
  rename); the others hold.
- **Findings:** HLP-322 (Low-medium); TST-1012 to TST-1020 (Low).
- **Checked and found fine:** the set-up with every option at once and every path writing a material's fields, Override
  on or off, with the put-back, errors and aborts; the material menu answered per material and the relink by textures;
  as_text on each kind of view; the user's file and textures' folder; the server; the waits; the tool's description
  read alone (3.26 K of 4,096); the module docstrings, README, GUIDE (8,688 of 14,000) consistent with each other; the
  user's three decisions reflected in the code, the Fields and ROADMAP; the committed meshes; the run order and cleanup
  of every live check.

### 2026-11-28: the fixes of the whole-branch round, an Opus round

- **Scope:** `git diff 3eccaac ba784cc -- . ':(exclude)PLAN.md'` (9 files, +313 -83).
- **How:** two Opus reviewers: the code and the tests, and the docs. No tests run, no probe needed. Dropped as not worth
  a fix: item 90's clause not naming the "(overridden)" mark's use in the set-back (generation 3, changes nothing
  anyone does); **Per material**'s "one the user had off is turned on", narrower than the code, which also turns on a
  new mesh file's own material (narrower, not false); `_shown_said`'s docstring not naming the materials in use it now
  passes; `graph=` over another mesh file's view possibly meeting a material menu that lists the earlier file's unused
  materials too (unmeasured: extra menu rounds and outputs on unused materials until the put-back, no wrong render).
- **Not verified:** none.
- **Resolutions assessed:** HLP-322 (questioned by HLP-323 and HLP-324), TST-1012 (by TST-1021), TST-1011 (by
  TST-1023); TST-1013 to TST-1020 hold.
- **Findings:** HLP-323, HLP-324, TST-1021 to TST-1024 (Low). A few Low ones: the Opus rounds on the fixes are done
  once they are fixed.
- **Checked and found fine:** every caller passing `in_use` at the right moment (after the import's end and Frame), and
  every one relying on `()`; a Scene menu's mesh on `default`; the several-materials refusal naming the new file's own;
  each threading of `in_use` needed by a unit test; the live check pinning when the menu is read; ROADMAP's rules and
  rows 84, 85 and 90 against the code.

### 2026-11-28: the whole branch against main, the last Opus round

- **Scope:** `git diff main...d6355aa -- . ':(exclude)PLAN.md' ':(exclude)REVIEW.md'`, the changes since 3eccaac read most
  closely.
- **How:** four Opus reviewers: the production code, the unit tests, the live checks and the meshes, and the docs; each
  rechecked the resolutions in its area. No tests run, no probe needed. The docs reviewer found nothing to report; the
  live checks' reviewer found nothing that would fail the final check. Dropped as not worth a fix: two mesh files whose
  materials share a name (Blender's default `Material`), one loaded over the other, possibly refused (unmeasured; a
  refusal only, never a wrong render, refused before HLP-322 too, and the table names no mesh to tell them apart: KISS);
  the several-materials check's dicts keyed by `str` (their keys come from a literal dict two lines above); the
  refusal's names carrying the menu's marks in `_material_checked` and not in `_used_material` (cosmetic, as on main);
  `_overrides`' keys for a material named with `&` (unmeasured, extreme); a symlinked Default State File put back as a
  file (on main, very unlikely); `OVERRIDE`'s comment narrower than the facts (not false where it matters).
- **Not verified:** none.
- **Resolutions assessed:** all 101 rechecked by area. HLP-323 (questioned by HLP-325), TST-1024 (by TST-1025), HLP-322
  (by TST-1026); the others hold. HLP-304 gets a note: HLP-322's probe measured an earlier file's materials listed
  "(unused)" once the import ended, after HLP-304 saw them unlisted as Reset Scene returned.
- **Findings:** HLP-325, TST-1025 and TST-1026 (Low). **The reviews look converged:** an Opus round of the entire branch
  found only a few Low ones.
- **Unspecified:** as_text's `Override Material` line, already the user's question, may also carry an earlier mesh
  file's unused materials over another file's view (`_overrides` walks them; unmeasured).
- **Checked and found fine:** the code as it ends, every path writing a material's fields with its put-back, errors and
  aborts, as_text, the user's file byte for byte, no new popup or dialog; the docs as they end, consistent with the code
  and the user's three decisions; the live checks' order, cleanup, waits and skips; the unit fakes against the
  measurements; the GUIDE core (8,688 of 14,000) and the tool's description (3.26 K of 4,096).

### 2026-11-28: the user's answers at convergence, a Sonnet round

- **Scope:** `git diff 9013466 f28117d -- . ':(exclude)PLAN.md'` (6 files, +59 -14).
- **How:** one Sonnet reviewer, on the developer's change made from the user's two answers: as_text's Override line
  naming the materials in use ("Name them"), DECISIONS.md's click-through entry naming the material menu ("Extend the
  entry"). No tests run, no probe needed. Dropped as not worth a fix: two materials of one name in the menu collapsing
  into one key (named in the second Opus round already, and older than the change); a material named with `&` shown
  as the menu escapes it (extreme). Found harmless: `_in_use` now read before `_mesh_shown` (two menu reads, nothing
  shared).
- **Not verified:** none.
- **Resolutions assessed:** none in scope.
- **Findings:** TST-1027, TST-1028 (Low). A few Low ones: the reviews stay converged once they are fixed.
- **Unspecified:** none new; the second Opus round's "as_text's `Override Material: on, off` line names no material" is
  decided by the user ("Name them").
- **Checked and found fine:** the filter against `_in_use`'s names (marks and `&` dropped); a Scene menu's mesh listing
  Default in use; the docstrings, the Field and ROADMAP item 85's row against the user's choice; DECISIONS.md's
  sentence added alone, the rest word for word, and true of `view3d.py`; every changed unit test failing without the
  change; the other readers of the as_text output (`SHOWN_ALREADY`, the put-back check, the known-view check,
  `state_file.at_the_render`, `SHOWN_TEXT`) unaffected; the new live expectation put back on failure and skipped in a
  user's Designer.

---

## High

## Medium-high

## Medium

- [x] **HLP-312 · `graph=` on a mesh of several materials fails: Designer's material menu is left unanswered** · `mcp_server/designer_helpers/view3d.py` (`_apply_outputs`) · measured · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** On a mesh of two or more materials, "View Outputs In 3D View" opens a second menu,
    `materialSelectionMenu`, listing the mesh's materials (a runner, port 9981: the OBJ's `first` and `second`, the
    Samba FBX's two). Nothing picks, so `MENU_GUARD` closes it after 5 s and the call fails with "a menu was still open
    5 s after 'View Outputs In 3D View' (Designer asking something more?)". The relink of a view following a graph on
    such a mesh loses 5 s each time (the set-up's and the put-back's) and leaves the view no longer following it.
  - **Scenario.** The use item 84 is for: `mesh=<the user's asset>, graph=<its material>`. Real assets often have
    several materials, both committed test meshes do, and the call fails every time.
  - **Fix.** The user's choice (2026-11-27, "Every material"): answer the menu once per material, so the outputs go
    on every material of the mesh, as on a preset. Measured: `.trigger()` on an entry does nothing; Down (index + 1
    times) then Return picks it; one material per pick, picks adding up (each material then `override_existing_material`
    true, its textures in the resources' folder). The relink restores the materials that showed outputs in the base.
    The `graph` Field, the docstrings (the material menu beside the one-output channel menu); live checks on the OBJ
    and the Samba FBX (both colours replaced, every material overridden), and the relink case.
  - **Resolution: done** (2026-11-27).
    - **Test:** `test_designers_menu_of_the_materials_is_answered_once_per_material` (got `[[], []]`), the menu made
      transparent as it opens, closed with none picked, the materials given and wanted, and
      `test_a_relink_puts_the_outputs_back_on_the_materials_that_showed_them` (got `[None, None]`); live,
      `check_graph_puts_its_outputs_on_every_material_of_a_mesh_file` (the OBJ and the relink) and the Samba case of
      `check_a_3d_shot_shows_a_mesh_file_framed_by_designers_frame`, each failing with "a menu was still open 5 s".
    - **Cause:** the look timer had fired before the trigger, so nothing ran in Designer's nested menu loop to answer
      `materialSelectionMenu`.
    - **Fix:** `_MenuPick` answers `MATERIAL_MENU` (`setActiveAction`, then Return), once per material, the Explorer's
      menu opened again for each; `_apply_outputs(..., materials=())`, every material when none are given; the
      relink puts the outputs back on the materials whose textures the base's Save names (`_materials_linked`;
      `override_existing_material` measured unreliable for it); another menu opening is left to the guard.
    - **Also covered:** the snippets wrapping these helpers (SETTLED, ABORTED, the check-setups fake).
  - Questioned by TST-1007 (2026-11-27)
  - Questioned by TST-1013 (2026-11-28)

## Low-medium

- [x] **TST-960 · Nothing fails if as_text brings Designer's window on screen** · `tests/test_all_tools/facts/checks.py:714-742` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** The design and DECISIONS.md keep an agent's Designer off the user's screen, and as_text "leaves
    Designer's window as it is". The live check reads `HIDDEN` only before the call (in `loaded`) and after it, and the
    unit test (`tests/unit/test_view3d_helpers.py:1837-1840`) asserts only `designer.triggered() == [SAVE]` and no load.
    A `_3d_shown` that put the window on screen for its Save, then hid it again, passes both.
  - **Scenario.** A later change wraps `_3d_shown` in `_on_screen` "so the Save holds the current state". Every test
    stays green, and a transparent Designer window comes up on the user's screen at each as_text, in each run of the
    `facts` category too, which no front watch covers.
  - **Fix.** A unit test with `_on_screen` and `_Screen` replaced in `vars(helpers)` by functions that raise, then
    `_3d_shown()`.
  - **Resolution: done** (2026-11-27).
    - **Test:** `test_the_text_never_puts_designers_window_on_screen`; the `Designer` fake now replaces `_on_screen`
      and `_Screen` with functions that raise, after asserting both names exist. With `with _on_screen(mw, None):
      pass` added to `_3d_shown`, 9 of the 10 text tests failed ("Designer's window put on screen"); the tenth, the
      hidden-panel refusal, raises before that point.
    - **Cause:** no test watched the window during the call.
    - **Fix:** the guard in the fake (`tests/unit/test_view3d_helpers.py`).
    - **Also covered:** the set-up's tests use the same fake, and the set-up never calls `_on_screen`.

- [x] **HLP-299 · A mesh file that doesn't import is framed and loaded again, and said as a view that hadn't settled within 3 s** · `mcp_server/designer_helpers/scene3d.py` (`framed`, `_unsettled`) · measured · found 2026-11-27 by three reviewers (Sonnet)
  - **Defect.** `framed` runs whatever the first load's wait returned (`load_settled = framed(size) and
    load_settled`): after an import that never ended within `IMPORT_LIMIT`, it triggers Frame, Saves a state holding
    no mesh and loads it again. `_unsettled` always names `SETTLE_LIMIT` (3 s), and the tool's docstring advises
    "shoot again with the same set-up".
  - **Scenario.** Measured (a runner, port 9941, a corrupt `x.fbx`): with `zoom=1` or `view='Top'` the shot took 36 s
    and showed the user's own mesh, the line only "hadn't settled within 3 s"; with `tiling=2` it was refused after
    32 s as "the 3D view's mesh uses 0 materials". An agent shoots again and waits again.
  - **Fix.** Skip Frame and the second load when the import didn't end; say that the mesh file didn't import within
    30 s, and that Designer's log says it failed (`read_designer_log`); have `_unsettled` name the limit the wait
    used; the tool's docstring says not to shoot again for it. A unit row of `test_a_step_whose_view_never_settled_says_so`
    for a mesh file.
  - **Resolution: done** (2026-11-27).
    - **Test:** `test_a_mesh_file_that_doesnt_import_is_said_so_and_neither_framed_nor_loaded_again` (the mesh alone,
      a zoom, a tiling) and `test_a_put_back_of_a_mesh_file_that_doesnt_import_says_so`; live,
      `check_a_mesh_file_that_doesnt_import_is_said_so` (a corrupt .fbx with `zoom=1` and `tiling=2`). Before the
      fix, Frame was triggered and the line said "hadn't settled within 3 s"; live, the tiling was refused as "uses
      0 materials".
    - **Cause:** `framed()` ran whatever the first load's wait returned, and `_unsettled` always named `SETTLE_LIMIT`.
    - **Fix:** after a mesh file's load, `imported()` reads the Materials menu again; with nothing in use, Frame and
      the second load are skipped and the line says `UNIMPORTED` ("the mesh file didn't import within 30 s:
      Designer's log says if it failed, read_designer_log"); the tool's docstring says shooting again won't help.
    - **Also covered:** the put-back's load of a base holding a mesh file that no longer imports says the same.
  - Questioned by HLP-307 (2026-11-27)

- [x] **HLP-300 · A mesh path holding `#`, `?` or a literal `%XX` never imports** · `mcp_server/designer_helpers/state3d.py` (`_mesh_id`) · measured · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `_mesh_id` writes `'file://' + path` unencoded, and Designer reads the id as a URL: `#` starts a
    fragment, `?` a query, `%20` decodes to a space. Measured (a runner, port 9942): those three don't import (30 s,
    a Save holding no mesh); a space, `é` in NFC and NFD, and `&` do, saved back as written. A mesh dropped on the
    view is saved as `QUrl.fromLocalFile(path).toString()`: `#`, `?` and `%` as `%23`, `%3F` and `%25`, which import
    when written so. `state3d.py`'s "saved back as written" is said of every path.
  - **Scenario.** A user's `Asset #2.fbx` waits 30 s and shows nothing.
  - **Fix.** Encode `%`, `#` and `?` as Qt does (`%` first), so the id is Designer's own form and a dropped mesh reads
    as shown already; `_mesh_said` decodes it back; a live case with a `#` path; the docstring says which characters
    are encoded.
  - **Resolution: done** (2026-11-27).
    - **Test:** a `test_state3d` row, `/Users/u/Asset #2?/50%41 off.fbx` held as
      `file:///Users/u/Asset %232%3F/50%2541 off.fbx` and said back; live, the OBJ copied into a folder named
      `mesh #2`. Before the fix the id came back unencoded, and live the import never ended.
    - **Fix:** `_mesh_id` encodes `%` first, then `#` and `?`; `_mesh_said`'s `url2pathname` decodes them; the
      docstring says what was measured.
    - **Also covered:** a row with a space, `é` and `&` pins that they stay as written.
  - Questioned by HLP-308 (2026-11-27)

- [x] **HLP-306 · The view table frames a tall viewport closer than Designer's Frame does** · `mcp_server/designer_helpers/state3d.py` (`_framing`) · measured · follows TST-992, generation 2 · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** `_framing` scales the distance by `sin(A) / sin(A / max(1, w/h))`, 1 for every tall viewport.
    Designer's Frame of a tall one follows `max(1, sin(A) / sin(A * h/w))` (a runner, port 9951, 18 sizes matched to 3
    decimals): farther by 1.0 to 14.7 times where w/h is between about 0.30 and 0.44, the base distance outside it.
    So `view=` and a preset mesh switch write a pose nearer than Designer's own Frame there (`view='Top'` on the Plane
    wrote 147.780 where Designer framed 199.795 and 224.311). It is older than the branch (item 74's table); TST-992
    moved the check off the band and recorded it as not understood.
  - **Scenario.** A user's narrow, tall 3D dock (a viewport of 160 x 423): a shot with `view=` is framed 1.35 times
    closer than Designer's Frame, the mesh cut off.
  - **Fix.** Model it in `_framing` (wide viewports unchanged); unit rows from the runner's table; the check back on a
    size in the band, computing the table from the viewport it reads; the docstrings' "taller ones kept FRAMING's" and
    "Not understood, not modelled" replaced by the measurement.
  - **Resolution: done** (2026-11-27).
    - **Test:** `test_a_tall_viewport_is_framed_as_designers_frame_frames_it` (`test_state3d.py`), the runner's 13
      sizes and 256 x 423: the 7 rows in the band failed (a ratio of 1.0); live, the framing check back on 300 x 500
      failed twice at a 161 x 423 viewport (the Cube at 244.698 where the table said 180.992).
    - **Cause:** `_framing` scaled by `sin(A) / sin(A / max(1, w/h))`, 1 for every tall viewport.
    - **Fix:** one law, `distance * max(1.0, sin(A) / sin(A * h / w))`: the old value for a wide viewport, FRAMING's
      outside the band for a tall one; the docstrings give the measurement and its range (up to 3.87 times as tall
      as wide).
    - **Also covered:** `_framed` and `_reframed` both go through `_framing`; the live check passed four times at 161
      x 423 after the fix.
  - Note (2026-11-27): the test holds 13 rows in all, the runner's 12 and 256 x 423.
  - Questioned by TST-996 (2026-11-27)
  - Questioned by HLP-314 (2026-11-27)

- [x] **HLP-311 · A preset `mesh=` with `tiling=` or `shader_model=` reads the replaced mesh's materials** · `mcp_server/designer_helpers/scene3d.py:665-669` · measured · follows HLP-303, generation 2 · found 2026-11-27 by two reviewers (Opus)
  - **Defect.** For a preset switch `new_file` is False, so `held.update(_state_fields(base, owns))` reads the base's
    mesh's material. A runner (port 9982): over a two-material OBJ, `mesh='Plane', tiling=4` is refused as "the 3D
    view's mesh uses 2 materials (first, second)"; over a one-material OBJ (`only`), tiling 4 and UsdPreviewSurface go
    into `only` while the Plane renders `default`, untouched, and the shot says they were set; a Plane loaded over that
    base maps to `default`, the file's entry left in the table, so a later `tiling=3` on the Plane alone is refused. The
    comment (`:535-536`), `_3d_set_up`'s docstring and the `tiling` and `shader_model` Fields say the mesh asked is
    checked. The refusal for a preset base was on main already (HLP-114's "a mesh switch skips the refusal").
  - **Scenario.** The user's view shows their own asset; the agent follows GUIDE's advice, `mesh='Plane', tiling=2`,
    and is refused about a mesh it didn't ask for, with no way round it, since each call starts from the user's view.
  - **Fix.** A preset's material fields go to its own material, `default` (measured: a preset maps to `default` after
    a switch from a preset, HLP-280, and from a mesh file); a mesh file's come from its own import's Save, as now; a
    preset shown with stale entries of a file in the table reads `default` too. Unit rows for each base; a live case
    over the OBJ; the comment, docstring and Fields.
  - **Resolution: done** (2026-11-27).
    - **Test:** `test_a_mesh_of_the_scene_menus_uses_default_whatever_else_the_mapping_table_holds`,
      `test_the_material_fields_written_with_a_mesh_are_those_of_the_material_it_uses`, four rows of a Scene menu's
      mesh asked over a mesh file and one with a file's entries left, each refused or writing into `only` before the
      fix; live, `check_a_scene_menus_mesh_shot_over_a_mesh_files_view_takes_the_material_settings_in_its_own`.
    - **Cause:** `_used_material` read the mapping table for any mesh, and the set-up read the base's mesh.
    - **Fix:** `_used_material` gives `DEFAULT_MATERIAL` for a Scene menu's mesh; `_state_edited` writes the mesh first,
      so the material fields land in the material of the mesh written; measured, a load sets a material's shader
      model only if the view used that material with its Override on, so after a switch from a mesh file a shader
      model goes in a second load from a Save.
    - **Also covered:** the several-materials refusal kept for mesh files (its tests moved onto one); HLP-315.
  - Questioned by HLP-316 (2026-11-27)
  - Questioned by TST-1009 (2026-11-27)

- [x] **HLP-315 · Override Material was set back by the menu's position, which turned Default's off** · `mcp_server/designer_helpers/scene3d.py` (`_overrides_back`) · measured · found 2026-11-27 by the developer (Opus)
  - **Defect.** `_overrides_back` set each material's Override back by its place in the Materials menu, which lists
    the materials whose Override is on first, then the others (measured, port 9991): after a load over a mesh of
    several materials, the order changed and a fresh Designer's Default was turned off.
  - **Scenario.** A shot over the user's multi-material view leaves another material's Override as it wasn't.
  - **Fix.** Set each back by the material's name.
  - **Resolution: done** (2026-11-27).
    - **Test:** `test_override_material_is_set_back_on_each_material_by_its_name_whatever_the_menus_order` and
      `test_override_material_is_read_by_the_materials_name_its_marks_left_out`; live, the "over" case of the HLP-311
      check failed in a fresh Designer until the set-back went by name.
    - **Fix:** `_overrides` returns `{material name: action}`, the menu's marks stripped (`MARKS`), and
      `_overrides_back` sets each back by name; `_shown_said`, `state_file._sf_override` and the OVERRIDE snippet with it.
  - Questioned by TST-1007 (2026-11-27)

- [x] **HLP-316 · `shader_model=` doesn't take on a material whose Override Material is off, and the shot says it set it** · `mcp_server/designer_helpers/scene3d.py` (`loading`, `reloaded`) · measured · follows HLP-311, generation 3 · found 2026-11-27 by the developer and three reviewers (Opus)
  - **Defect.** A load sets a material's shader model only if the view used that material with its Override Material
    on (the developer's probe); the set-up writes the model in a load whatever the used material's Override. A runner
    (port 9995): on the Rounded Cube and the Plane, linked and unlinked, with Default's Override off the model wasn't
    taken (OpenPBR Surface at the render, the render pixel-identical to a plain shot), and the shot said "shader model
    AdobeStandardMaterial", only STALE's general line beside it. `scene3d.py:75-80` states the rule for every
    material, but a mesh file's own material (`only`, listed without "(overridden)") took the model in `framed`'s
    second load (port 9982).
  - **Scenario.** The user turned Override Material off to see the material's own look; `shader_model=` is said to be
    set, and the render and as_text show the old model.
  - **Fix.** Measure first whether turning the used material's Override on for the load, then back off as
    `_overrides_back` does, keeps the model; if it does, do that. If it doesn't, stop and report: refusing or saying it
    is the user's choice. Narrow `scene3d.py:75-80` and `state3d.py:41-42` to what was measured (which materials,
    which loads, probes or checks).
  - Note (2026-11-27): the developer measured on the Plane, Default's Override off: Override turned on in the menu
    before the load, the model wasn't taken; the file holding Default overridden, it was taken and kept once Override
    was set back off, but the render then matched a plain shot (the model shows only while Override is on). The docs
    were narrowed to that. The user's choice (2026-11-27, "Render with Override on"): for a shot with `shader_model=`,
    the used material's Override Material is on, as `graph=` leaves it, the user's put back with the view; the result
    says it turned Override on.
  - **Resolution: done** (2026-11-27).
    - **Test:** `test_a_shader_model_on_a_material_with_override_off_renders_overridden_then_gives_it_back_off` (not
      linked; a graph relinked), the one-load switch from a mesh file, a new mesh file's own material written overridden,
      and two `test_state3d` tests of `_state_overridden`, each failing before; live,
      `check_a_shader_model_on_a_material_with_override_off_renders_it_overridden` (the Plane with STATE_GRAPH's outputs and
      Default's Override off): before the fix the Save at the render held OpenPBR, not overridden.
    - **Cause:** a load sets a material's model only when the file holds that material overridden, and the model shows only
      while Override is on (measured, port 9991: the Plane with Default off, a switch to the Sphere, the Plane over the
      OBJ's state, a one-material OBJ).
    - **Fix:** the user's choice: `_state_overridden` holds the used material overridden in the load that writes the model;
      Override stays on for the render and the line says so ("Override Material on in <material>, to show the shader
      model"); the put-back gives the user's Override back; the second load (`later`, `reloaded`) is gone.
    - **Also covered:** a mesh file's own material, overridden in `framed`'s second load; the `shader_model` Field.
  - Questioned by HLP-318 (2026-11-27)
  - Questioned by HLP-319 (2026-11-27)
  - Questioned by HLP-320 (2026-11-27)
  - Questioned by TST-1010 (2026-11-27)
  - Note (2026-11-27): its live check is renamed `check_a_tiling_or_a_shader_model_on_a_material_with_override_off_renders_it_overridden`
    by HLP-321's fix.
  - Questioned by TST-1020 (2026-11-28)
  - Note (2026-11-28): its unit test is renamed
    `test_a_material_setting_on_a_material_with_override_off_renders_overridden_then_gives_it_back_off` by
    HLP-321's fix.

- [x] **HLP-318 · A model the material holds already is never shown with Override on** · `mcp_server/designer_helpers/scene3d.py:733` · confirmed · follows HLP-316, generation 4 · found 2026-11-27 by two reviewers (Opus)
  - **Defect.** `_state_changes` drops `shader` when it equals the model held, `written` turns Override on only when
    `shader` is written, and `framed` returns before `written` when nothing differs (`:668-675`). So a model held
    already, with the used material's Override off, is neither written nor shown: no load, Override left off, the
    render the user's plain look (HLP-316 measured the model shows only with Override on), the result "shader model
    ..." with no SHOWN_ON line. The `shader_model` Field and step 4 say one off is turned on for the render.
  - **Scenario.** The Plane with Default's Override off, at OpenPBR: `shader_model='OpenPBR Surface'` renders without
    Override while AdobeStandardMaterial and UsdPreviewSurface render with it, so an agent comparing the three compares
    Override (5.9 grey levels on the Plane, the probe's mean) more than the models (0.05). The same for
    `mesh=<a one-material file>, shader_model='OpenPBR Surface'`, the import's model.
  - **Fix.** By the user's choice ("Render with Override on"): when `shader_model=` is given and the used material is
    held not overridden, write it overridden (the model with it) in the first load, and in `framed`'s second load, so
    the render shows it and SHOWN_ON is said; a model held with Override on stays shown already, with no load. Unit rows
    for both scenarios; `check_values_a_3d_set_up_finds_shown_already_take_no_wait` keeps its no-load case if its
    view's Default is held overridden (confirm).
  - **Resolution: done** (2026-11-27).
    - **Test:** the HLP-316 unit test with the model held already (not linked, relinked) failed with no load at all, and
      the new mesh file's test asked its import's model failed with no second load; live, the HLP-316 check's new case (the
      model the view holds, read from a Save) failed with Default not overridden at the render.
    - **Cause:** `_state_changes` drops a model equal to the one held, and only a model written is held overridden.
    - **Fix:** `model_shown(content, fields)` puts the model back into the fields when the used material is held not
      overridden, at the first load and in `framed`'s second load, so it is written overridden and SHOWN_ON said; a model
      held with Override on still takes no load (`check_values_a_3d_set_up_finds_shown_already_take_no_wait`: no load).
  - Questioned by SRV-286 (2026-11-27)

- [x] **HLP-321 · `tiling=` doesn't show on a material whose Override Material is off** · `mcp_server/designer_helpers/scene3d.py` (`written`, `turned_on`) · measured · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** A runner (port 9998): on the Plane with a pattern graph's outputs, `tiling=4` rendered pixel-identical to
    a plain shot with Default's Override off (5.8 grey levels apart on average with it on); the result said "tiling 4"
    and STALE's line, whose causes don't name Override. As for a shader model (HLP-316), Designer renders the mesh's own
    material while Override is off.
  - **Scenario.** The user turned Override off; `tiling=2` is said set, the render is unchanged, and STALE says to shoot
    again, which won't help.
  - **Fix.** The user's choice (2026-11-27, "Same as shader_model"): a shot with `tiling=` turns the used material's
    Override on for the render when it was off, writes it held overridden with the tiling, says so (SHOWN_ON), and puts
    the user's Override back with the view; a tiling held already with Override off is written too, as HLP-318 did for
    the model. The `tiling` Field, the docstrings and ROADMAP's rules with it; unit rows and a live case (a pattern
    graph's outputs, Override off).
  - **Resolution: done** (2026-11-27).
    - **Test:** the tiling rows of the parametrized unit tests (a material with Override off, overridden already, a new
      mesh file's own material, a tiling and a model together) failed before the fix, 13 of 17 with the old `scene3d.py`
      put back; live, the HLP-316 check, renamed `check_a_tiling_or_a_shader_model_on_a_material_with_override_off_renders_it_overridden`
      and moved onto a gradient graph (`PATTERN_GRAPH`, STATE_GRAPH being a uniform colour), failed in its tiling case
      (`overridden=False, tiling='float(4)'` at the render), then passed (renders 9.2 to 10.9 grey levels from a plain
      shot on average).
    - **Fix:** the user's choice: `written` holds the used material overridden for any field of `PER_MATERIAL`;
      `own_changes` writes every field asked of a material held not overridden; SHOWN_ON reads "Override Material on in
      <material>, to show its tiling", "shader model", or both; the `tiling` Field, the docstrings and ROADMAP's rules.
    - **Also covered:** 35 facts and 19 editor_panels_and_fit checks touching a tiling, a shader model or Override passed
      in fresh Designers, before and after `/simplify`.
  - Questioned by TST-1014 (2026-11-28)

- [x] **HLP-322 · A mesh file over another mesh file's view counts both files' materials, so tiling= and shader_model= are refused** · `mcp_server/designer_helpers/state3d.py` (`_used_material`) · measured · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** `_used_material` counts every id in `material_mapping_table`. A runner (port 9999): importing a mesh file
    over a view showing another mesh file keeps the old file's entries beside the new file's (`['first', 'only',
    'second']`, both directions); `mesh=<a one-material OBJ>, tiling=2` over the two-material OBJ was refused as "the 3D
    view's mesh uses 3 materials (first, only, second)", and so were `shader_model=` and the reverse. HLP-311 measured
    the same for a Scene menu's mesh, which `_mesh_listed` now short-cuts.
  - **Scenario.** The user's view shows their asset; an agent compares a second asset with a tiling, and is refused about
    materials of a mesh it didn't ask for, though the new file has one.
  - **Fix.** Find the materials the new mesh file uses in the loaded state (measured first: the Materials menu's
    materials in use once the import ended, by name, or what the table's entries say of their mesh), not every id in the
    table; the runner's probe (`scratchpad/probe/run_probe.py`) is the start of the live case.
  - **Resolution: done** (2026-11-28).
    - **Test:** `test_a_mesh_file_loaded_over_another_uses_the_materials_the_menu_lists_in_use` (test_state3d), a tiling over
      another file's view taken (a file shown already and one the call loads), the reverse refused naming its own two, and
      as_text reading the tiling there (test_view3d_helpers): 5 failed before ("uses 3 materials (first, only, second)");
      live, `check_a_tiling_on_a_mesh_file_over_another_ones_view_is_set_in_its_own_material` failed in its 3 cases, then
      passed (`only` at tiling 2 at the render; the reverse refused as "uses 2 materials (first, second)").
    - **Cause:** `_used_material` counted every id of `material_mapping_table`, which keeps the earlier file's entries; the
      table's entries name no mesh, but the Materials menu marks the earlier file's materials "(unused)" (measured, port
      9991, both directions).
    - **Fix:** `_used_material(content, in_use=())` keeps the ids whose material's name the menu lists in use
      (`_material_named`), passed through `_located`, `_state_fields`, `_state_edited`, `_state_overridden` and
      `_state_said`; `scene3d._in_use` reads the menu where it is needed; a Scene menu's mesh still goes to `default`.
    - **Also covered:** the same miscount refused a tiling on a mesh file shown already, and as_text said `tiling: not read`
      there.
  - Questioned by HLP-323 (2026-11-28)
  - Questioned by HLP-324 (2026-11-28)
  - Questioned by TST-1026 (2026-11-28)

## Low

- [x] **SRV-281 · as_text says its values can be given back to the options, but a user's mesh or map is said as a path or URL they refuse** · `mcp_server/server_tools/views.py:166-169` · confirmed · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** The Field says the values are "named and given as these options take them", and GUIDE.md:36-37,
    `_state_said`'s and `_said_float`'s docstrings (`state3d.py:314-317,385-392`) and ROADMAP item 85's row say so too.
    A user's mesh is said as its path (`_mesh_said`) and a map not of Designer's own as its URL (`_map_said`), which
    `mesh=` and `environment=` refuse (`view3d.py:374-375`). A field it can't read says `not read: ...`, any of the
    renderer, AOV and Override Material lines may be missing, and "these options" has no antecedent in the Field.
  - **Scenario.** An agent reads `mesh: /Users/u/box.fbx`, passes it to `mesh=` and is refused "unknown mesh".
  - **Fix.** Narrow the wording, no code: the Field names the five options (`mesh`, `tiling`, `environment`,
    `environment_rotation`, `environment_exposure`), says a value they take reads as shown already when given back,
    that a user's own mesh or map is said by its path or URL, that a field it can't read says why, and that a line may
    be missing. The same in the docstrings, the guide and the row.
  - **Resolution: done** (2026-11-27).
    - **Test:** none new: the behaviour is pinned by `test_a_mesh_the_scene_menu_checks_none_of_is_said_*` and
      `test_a_map_not_of_designers_own_is_said_by_its_url`; the docs tests passed.
    - **Fix:** the Field names the five options, says a value given back reads as shown already, that a mesh or map of
      the user's own is said by its path or URL, that a field it can't read says why, and that the last three lines
      are left out where Designer gives none.
    - **Also covered:** the same narrowing in `_said_float`'s and `_state_said`'s docstrings, GUIDE.md's Look bullet
      and item 85's row.
  - Questioned by TST-972 (2026-11-27)
  - Questioned by HLP-296 (2026-11-27)

- [x] **SRV-282 · The docstring puts as_text mid-paragraph: the shot's count note, the clipboard and the window sentences read as as_text's** · `mcp_server/server_tools/views.py:173-199` · confirmed · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** "With as_text, '3d' instead says what the 3D view shows..." is followed by "When the view hadn't
    settled within 3 s after a step... the result also gives the view's count", which as_text never gives. The earlier
    sentences say unconditionally that "'3d' goes through the clipboard" and puts a minimized, covered or hidden window
    on screen; as_text does neither. The leftover-backup line, which comes first in as_text's answer
    (`test_a_leftover_backup_is_put_back_before_the_text_and_said`), isn't named.
  - **Scenario.** An agent looks for a staleness note or a window line in a text answer, or tells the user Designer's
    window was brought up.
  - **Fix.** A short paragraph of its own for as_text, after the shot's paragraphs: no render, no clipboard, the window
    left as it is, a leftover backup put back and said first.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only; the docs tests passed.
    - **Fix:** as_text has a paragraph of its own at the end of the docstring: no render, no clipboard, the window left
      as it is, a leftover backup put back or removed before the Save and said first.

- [x] **HLP-295 · "A Save off screen holds the camera drawn on screen" is measured only for a hidden Designer** · `mcp_server/designer_helpers/scene3d.py:69` · confirmed · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** The module docstring, `_3d_shown`'s docstring, ROADMAP item 85's row and the facts check's fact say
    "off screen", which DECISIONS.md uses for minimized, covered and hidden together. The facts check measures only a
    window hidden (`check_the_3d_view_as_text_says_a_known_view_and_the_camera_it_drew`).
  - **Scenario.** The user minimizes Designer while an agent works, as users do; as_text's camera line would be wrong
    if a minimized window's Save held another camera, and the docs say it doesn't.
  - **Fix.** Measure a minimized window too in the facts check, and a covered one if the self-test's window helpers
    give it with no new scaffolding. If minimizing in `facts` needs more than that, narrow the wording to "hidden".
  - **Resolution: done** (2026-11-27).
    - **Test:** the renamed facts check passed in a scratch run.
    - **Fix:** narrowed to "hidden": minimizing from `facts` needs new scaffolding (the minimize and restore helpers
      belong to `editor_panels_and_fit`, and the shot's `_Screen` minimizes a window again at its put-back).
      `scene3d.py`'s docstring says hidden and that a window minimized or covered wasn't measured; the facts check's
      fact reads "a Save made with Designer hidden holds the camera..."; item 85's row drops the claim.
  - Note (2026-11-27): a runner probe measured as_text with Designer minimized and covered by a window of
    Designer's own, after a known state settled on screen: the text was the known one each time (twice each). The
    docstring's "A window minimized or covered wasn't measured" can say so instead. Done with the second round's
    fixes: `scene3d.py`'s docstring records it as measured by one probe, not checked.

- [x] **TST-961 · README names only a shot with a set-up as refused after the Default State File setting changed** · `README.md:418-421` · confirmed · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** "until then a shot with a set-up is refused, once Designer's own Save has written the session's state
    to the file it started with". `_3d_shown` goes through `_state_saved` too, so as_text is refused the same way
    (`test_a_save_that_didnt_write_the_default_state_file_refuses_the_text`).
  - **Scenario.** A person whose as_text fails after changing the setting finds no word for it.
  - **Fix.** "a shot with a set-up, or `as_text`, is refused".
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only; the docs tests passed.
    - **Fix:** "a shot with a set-up, or `as_text`, is refused".

- [x] **TST-962 · GUIDE's as_text sentence leaves "there" pointing at the panel's title, and names only the Save** · `mcp_server/GUIDE.md:573-575` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** "`as_text` reads the view through a Save of that file, the file put back after, and the renderer from
    the 3D panel's title. What Designer does there, measured: ..." "There" meant the state file and now follows the
    title. The mesh comes from the Scene menu, and the AOV and Override Material from their menus.
  - **Scenario.** An agent looking for the state file's measurements reads them as the title's.
  - **Fix.** One line and the path, as docs.md wants for the guide, placed after the "measured" pointer; or the mesh,
    AOV and Override Material named with their menus.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only; the docs tests passed.
    - **Fix:** the as_text sentence follows the "measured" pointer: "from that file and from the 3D view's menus and
      title (how: `scene3d.py`, `_3d_shown`)".
  - Questioned by SRV-283 (2026-11-27)

- [x] **TST-963 · Item 85's row says as_text is the same before and after a shot, but the check leaves the camera out** · `ROADMAP.md:114` · confirmed · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** "`as_text` before and after a shot the same": the put-back check compares the lines without
    `camera: ` (`not line.startswith('camera: ')`), as its docstring says. The row also repeats the measured facts
    (the title's form, the renderers, a Save off screen) whose home is `scene3d.py` and `state3d.py`, which it points
    to already.
  - **Scenario.** A reader takes the camera line's put-back as checked live.
  - **Fix.** "the same, the camera aside"; leave the measured facts to the pointer.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only; the docs tests passed.
    - **Fix:** the row says "the same, the camera aside", and leaves the measured facts to its `scene3d.py` and
      `state3d.py` pointer.

- [x] **TST-964 · The 3D view section's rules don't say a new value is said by as_text** · `ROADMAP.md:71-102` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** Each new 3D value follows the section's rules. A new value now has to be said by as_text too, or
    listed in item 85's Not said. `assert_never` in `_field_said` forces that only for a new `StateField`, not for a
    value a menu or the toolbar holds (item 81's AOV pick).
  - **Scenario.** Item 81 adds the AOV pick without a line in the text, and nothing says it should have one.
  - **Fix.** A bullet: "Said as text: `_shown_said` / `_field_said`, or listed in item 85's Not said".
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only; the docs tests passed.
    - **Fix:** a bullet after "Said as it goes": a new value gets a line in the 3D view as text (`_shown_said`, or
      `_field_said` for a field of the file), or is listed in item 85's Not said.

- [x] **TST-965 · A comment says "the light at Designer's defaults" over values unlike them** · `tests/unit/test_selftest_check_setups.py:214` · confirmed · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** `SHOWN_TEXT` holds tiling 1.5, rotation 108 and exposure 0.7; Designer's defaults are 1, 0 and 0. The
    values are unlike the defaults on purpose, so the test can fail; the comment is left from the old fake.
  - **Scenario.** A reader "fixes" the values to the defaults, and the test can no longer fail on a reader that says
    them.
  - **Fix.** "the Plane, a light unlike Designer's defaults".
  - **Resolution: done** (2026-11-27).
    - **Test:** a comment only; the docs tests passed.
    - **Fix:** "a light unlike Designer's defaults, so that a reader saying them fails the test".

- [x] **TST-966 · Two new unit tests assume POSIX paths from `url2pathname`, TST-926's pattern** · `tests/unit/test_state3d.py:618` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `('file:///Users/u/my%20box.fbx', '/Users/u/my box.fbx')` and `test_view3d_helpers.py:1892`'s
    `'mesh: /Users/u/box.fbx'` go through `_mesh_said`'s `urllib.request.url2pathname`, which is `nturl2path`'s on
    Windows. TST-926 fixed the same in a sibling test.
  - **Scenario.** A unit run on Windows fails both (ROADMAP item 18).
  - **Fix.** Patch `url2pathname` to `urllib.parse.unquote` in both, as TST-926 did, and add a case through
    `nturl2path.url2pathname` for `file:///C:/Users/me/box.fbx`.
  - **Resolution: done** (2026-11-27).
    - **Test:** the two tests as committed, run with `url2pathname` set to `nturl2path`'s, both failed
      (`'mesh: \\Users\\u\\my box.fbx' != '/Users/u/...'`).
    - **Cause:** `_mesh_said` reads the URL with the platform's `url2pathname`.
    - **Fix:** two conftest fixtures, `urls_as_posix` and `urls_as_windows`, used by both tests, and
      `test_a_windows_mesh_url_is_said_as_windows_reads_it` (`file:///C:/Users/me/my%20box.fbx` as
      `C:\Users\me\my box.fbx`). All pass under the Windows reading too.
    - **Also covered:** TST-926's two older copies in `test_state3d.py` use the fixtures now.

- [x] **TST-967 · An implicit `Any` from `ast.literal_eval` in a new live check** · `tests/test_all_tools/facts/checks.py:462` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `said = [ast.literal_eval(...) for line in ...]` is `list[Any]`, so the comparisons after it go
    unchecked (`.claude/rules/python.md`, implicit `Any`).
  - **Scenario.** A change of what `SHOWN=` prints breaks the comparison and mypy can't tell.
  - **Fix.** `said: list[list[str]]`, or `list[object]` as line 684 does.
  - **Resolution: done** (2026-11-27).
    - **Test:** none possible: mypy doesn't report an implicit `Any`.
    - **Fix:** the parse is typed `object`, then narrowed with one `isinstance`.
    - **Also covered:** the `TITLE=` parse was typed `list[object]` already.
  - Questioned by TST-971 (2026-11-27)

- [x] **TST-968 · as_text's refusal with the 3D View panel hidden has no test** · `tests/unit/test_view3d_helpers.py:1832` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `_3d_shown`'s docstring says it is refused when the 3D View panel isn't visible or built. No test
    builds `Designer(helpers, hidden=('3d',))` and calls `_3d_shown`; only the shot's refusal is tested (line 797).
  - **Scenario.** `_3d_dock` moved after `_state_back_up` leaves a backup on a refusal, and the next call says "put
    back first"; nothing fails.
  - **Fix.** A unit test with `hidden=('3d',)`: `RuntimeError`, nothing triggered, no file left.
  - **Resolution: done** (2026-11-27).
    - **Test:** `test_the_text_is_refused_with_the_3d_view_panel_hidden_before_anything_is_saved` (`RuntimeError`,
      nothing triggered, no file or backup left). With `_3d_dock` moved after `_state_back_up`, it failed on the
      `sd_mcp_3d_view_backup/path` file left behind.
    - **Fix:** the test.

- [x] **TST-969 · The refusal test's pattern can't tell whether `view` is named** · `tests/unit/test_view3d.py:325` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `match=r'as_text .*\b%s\b' % option` matches the fixed words "3D view" of the message
    (`views.py:285`) for `option == 'view'`. Three as_text tests also take `temp_folders` and never read it.
  - **Scenario.** The message stops naming `view` and the test still passes.
  - **Fix.** `match=r'it takes no .*\b%s\b' % option`; drop the unused `temp_folders`, or assert it stays empty.
  - **Resolution: done** (2026-11-27).
    - **Test:** with the message no longer naming `view`, the `[view]` case failed ("it takes no ").
    - **Fix:** the pattern is `it takes no .*\b<option>\b`; `temp_folders` is dropped from the two tests that never
      read it, and the read test asserts it stays empty.

- [x] **TST-970 · The said-number test copies the set-up's comparison instead of calling it** · `tests/unit/test_state3d.py:656-658` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** The contract is "given back to the tool, the value is the one shown already (`_state_changes`)", but
    the test hard-codes the 360 and the 32-bit comparison.
  - **Scenario.** `_state_changes` changes how it compares; the test still passes while a value given back reads as a
    change.
  - **Fix.** Assert `_state_changes(_state_fields(content, [field]), {field: float(said) / divisor}) == {}`, with the
    divisor from `DEGREES_PER_TURN`.
  - **Resolution: done** (2026-11-27).
    - **Test:** with `_state_changes` comparing the tiling exactly, the new test failed (`{'tiling': 2.3} != {}`);
      the old one passed there.
    - **Fix:** the test asserts `_state_changes(_state_fields(content, [field]), asked) == {}`, the rotation through
      `DEGREES_PER_TURN`, parametrized by field (its tag from `_PLACES`, its option from `SAID_AS`).

- [x] **TST-971 · The live check's `said` is still `list[Any]` after TST-967's fix** · `tests/test_all_tools/facts/checks.py:462-464` · confirmed · follows TST-967, generation 2 · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `last: object = ast.literal_eval(...)`, then `said = last if isinstance(last, list) else []`: mypy
    narrows `object` through `isinstance(x, list)` to `list[Any]`, so the items stay unchecked, the implicit `Any`
    TST-967 named.
  - **Scenario.** `SHOWN=` prints items of another type and `said[:5] == RENDERED_SAID` goes on unchecked by mypy.
  - **Fix.** `said = [str(v) for v in last] if isinstance(last, list) else []`, so `said` is `list[str]`.
  - **Resolution: done** (2026-11-27).
    - **Test:** none can fail: mypy doesn't report an implicit `Any`. A temporary `reveal_type(said)` gave
      `list[Any]` before the fix and `list[str]` after it.
    - **Cause:** narrowing `object` with `isinstance(x, list)` gives `list[Any]`.
    - **Fix:** `said = [str(v) for v in last] if isinstance(last, list) else []`, and the detail is `' / '.join(said)`.
    - **Also covered:** the check's `TITLE=` parse is `list[object]`, compared whole.

- [x] **TST-972 · GUIDE's Look bullet says as_text gives the mesh, tiling and light "as those options take them", after options it doesn't take** · `mcp_server/GUIDE.md:35-37` · confirmed · follows SRV-281, generation 2 · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** "Those options" follows `mesh='Plane'`, `view='Top'` and `tiling=2`: the light's options are named
    nowhere in the bullet, and as_text never says `view`. The camera, the renderer, the AOV and Override Material go
    unnamed, and the sentence copies what the `as_text` Field holds (docs.md: the Field is the single source).
    `state3d.py:2`'s "the fields said in screenshot_designer's own terms" says more than the code too: a user's own mesh
    or map is said by its path or URL, the camera by its pose.
  - **Scenario.** An agent wanting the camera's pose or the renderer reads "It gives the mesh, the tiling and the light"
    and takes a screenshot instead.
  - **Fix.** The bullet keeps "What the 3D view shows, with no image: `screenshot_designer('3d', as_text=True)`." and
    leaves the lines to the Field; `state3d.py:2` says "under the names of screenshot_designer's options where one sets
    them".
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only; the docs tests passed.
    - **Fix:** the Look bullet keeps "What the 3D view shows, with no image: `screenshot_designer('3d', as_text=True)`."
      and leaves the lines to the Field; `state3d.py`'s opening says "the fields said under the names of
      screenshot_designer's options where one sets them".

- [x] **TST-973 · ROADMAP item 90 doesn't list what as_text relies on, measured only on macOS** · `ROADMAP.md` (item 90) · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** Item 90 lists the names the 3D view's set-up drives, measured only on macOS. as_text adds the 3D
    panel's title (`<mesh> - <renderer>`) and the Renderer menu's names, measured only by a macOS facts check, and item
    90 names neither.
  - **Scenario.** The Windows work of item 90 checks the listed names and misses as_text's renderer line.
  - **Fix.** Name as_text, the panel's title and the renderers in item 90's row.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only; the docs tests passed.
    - **Fix:** item 90's row says as_text (item 85) adds the 3D panel's title, `<mesh> - <renderer>`, and the Renderer
      menu's names, measured only on macOS.
  - Questioned by TST-976 (2026-11-27)

- [x] **SRV-283 · The tool's as_text paragraph says the view is read from the Save alone** · `mcp_server/server_tools/views.py:202` · confirmed · follows TST-962, generation 2 · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** "It reads the view from a Save of the default 3D state file, then puts the user's file back." Only the
    file's fields come from the Save; the mesh comes from the Scene menu, the renderer from the panel's title, the AOV
    and Override Material from their menus: TST-962's defect, in the paragraph SRV-282's fix wrote.
  - **Scenario.** A reader of the description takes the mesh line for the file's, which differs from the Scene menu's
    while a load hasn't ended.
  - **Fix.** "It saves the session's state to the default 3D state file to read it, then puts the user's file back."
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only; the docs tests passed.
    - **Fix:** "It saves the session's state to the default 3D state file to read it, then puts the user's file back."

- [x] **SRV-284 · The `shader_model` Field hangs its refusal on UsdPreviewSurface, and dates Blender's model to no version** · `mcp_server/server_tools/views.py:163-169` · confirmed · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** "AdobeStandardMaterial, OpenPBR Surface (Designer's default) or UsdPreviewSurface (refused for a mesh
    using more than one material)": the refusal is for any model, but reads as the last name's, and the sentence has
    two parentheticals (docs.md). "Blender's Principled BSDF is based on OpenPBR Surface" holds since Blender 4.0
    (the manual's source, 4.0 to 5.4); before it, the page named the Disney model.
  - **Scenario.** An agent with a two-material mesh tries `shader_model='AdobeStandardMaterial'` and is refused; or
    hands off to Blender 3.x and matches OpenPBR Surface.
  - **Fix.** "Refused for a mesh using more than one material." as a sentence of its own, as `tiling`'s Field does;
    "Since Blender 4.0, its Principled BSDF is based on OpenPBR Surface."
  - **Resolution: done** (2026-11-27).
    - **Test:** the description only; `test_server.py`'s guards passed.
    - **Fix:** "Refused for a mesh using more than one material." is a sentence of its own; "Since Blender 4.0, its
      Principled BSDF is based on OpenPBR Surface."

- [x] **HLP-296 · `_state_said`'s docstring and the as_text Field leave out two shader cases** · `mcp_server/designer_helpers/state3d.py:422-429` · confirmed · follows SRV-281, generation 2 · found 2026-11-27 by three reviewers (Sonnet)
  - **Defect.** "A field the file holds other than once is said not read, with why, and so is the tiling of a mesh
    using several materials": the shader model of such a mesh is said not read too (a unit test pins it). A model the
    Materials menu lacks is said as the file holds it (`_shader_said`), which `shader_model=` refuses, so the claim
    that a value given back reads as shown already doesn't hold for it: SRV-281's pattern.
  - **Scenario.** An agent reads `shader_model: usd::Other` from a file of another Designer version, gives it back,
    and is refused.
  - **Fix.** "and so are the tiling and the shader model of a mesh using several materials"; name the model the
    menu lacks, said as the file's name, among the docstring's and the as_text Field's exceptions.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only; both cases were pinned already (`test_a_shader_model_the_menu_lacks_is_said_as_the_file_holds_it`,
      and the several-materials case of `test_a_field_that_cant_be_read_is_said_with_why_and_the_others_are_read`).
    - **Fix:** `_state_said`'s docstring says a model the Materials menu lacks is said by its name in the file, which
      `shader_model=` refuses, and "so are the tiling and the shader model of a mesh using several materials"; the
      as_text Field names the same exception.
    - **Also covered:** every "shown already" claim searched; `_said_float`'s is about numbers, item 85's row only
      its own lines.
  - Questioned by HLP-301 (2026-11-27)

- [x] **HLP-297 · `state3d.py`'s docstring calls two lists "the materials list"** · `mcp_server/designer_helpers/state3d.py:29-31` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** The shader is in "that material's entry of the renderer plugin's materials list", then its
    parameters follow "in that entry and in the materials list", the second being `/database/materials/materials`.
    The `ONE_FIELD` comment (`tests/test_all_tools/facts/state_file.py:709-712`) says the same.
  - **Scenario.** A reader looks for the parameters in the plugin's list only.
  - **Fix.** "in the file's own materials list (`/database/materials/materials`)", in both places.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** the sentence went with TST-980's narrowing; the measurement, under "Measured, not checked", names the
      renderer plugin's list and the file's own materials list (`/database/materials/materials`), as the row's
      comment does.

- [x] **TST-974 · GUIDE says `shader_model` shows the material "as the app it is headed for renders it"** · `mcp_server/GUIDE.md:36` · confirmed · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** Nothing compares a render with another app's. Designer's Rasterizer under OpenPBR Surface is not
    Blender's render, and UsdPreviewSurface rendered as OpenPBR Surface did. The Field is the parameter's source.
  - **Scenario.** An agent tells the user "this is how it will look in Blender" after a shot with `shader_model=`.
  - **Fix.** "`shader_model` renders the material under another shader model", the rest left to the Field.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only; the docs tests passed.
    - **Fix:** "`shader_model` renders the material under another shader model", the rest left to the Field.

- [x] **TST-975 · The 3D view section's rules and item 83's row don't follow the shader model** · `ROADMAP.md:72,103` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** Line 72 lists "the camera, the mesh, the tiling and the light"; line 103 says the STALE check's
    "cases today are a pan and an exposure", and a shader model change is a third; nothing says a field of the
    material goes in `PER_MATERIAL`, found by the material's id and refused for a mesh using several. Item 83's row
    lists the set-ups the STALE line names without the shader model, and names a tiling on a patternless material as
    the one change the render can't show, where UsdPreviewSurface against OpenPBR Surface is a second.
  - **Scenario.** Item 82 (real-world scale, a material's field) is built without `PER_MATERIAL` and its anchor
    silently fails to match.
  - **Fix.** Add the shader model to both lists; a bullet for `PER_MATERIAL`; item 83's row names the shader model
    and the second case for its "Measure first".
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** the section's first paragraph lists the shader model; a **Per material** rule (`PER_MATERIAL`, the
      material's id, refused for several materials before anything changes); the STALE cases "a pan, an exposure
      and a shader model"; item 83's row names the shader model, both can't-show cases, and the model change in
      its Measure first.

- [x] **TST-976 · ROADMAP item 90 doesn't list `shader_model=` and the names it relies on** · `ROADMAP.md` (item 90) · confirmed · follows TST-973, generation 2 · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** Item 90's call stops at `environment_exposure=...`; the Materials submenu's model names and the saved
    definitions (`SHADER_MODELS`) are measured only on macOS.
  - **Scenario.** The Windows work checks the listed names and misses the shader model's.
  - **Fix.** Add `shader_model=...` and those names to item 90's row.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** item 90's call lists `shader_model=...` and item 88, and its row the menu's model names and the
      definitions' names (`state3d.SHADER_MODELS`), measured only on macOS.

- [x] **TST-977 · Item 88's row states the render measurement more broadly than it was made** · `ROADMAP.md` (item 88) · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** "the Rasterizer rendered UsdPreviewSurface within a grey level of OpenPBR Surface,
    AdobeStandardMaterial up to 92 levels apart": the record (`shot3d.py:87-89`) is two materials, once each, 92 and
    16 levels, the levels a maximum; the GPU Pathtracer wasn't measured, and `state3d.py`'s "Not measured" doesn't
    say so. `editor_panels_and_fit/checks.py:1946`'s comment reads as contradicting itself.
  - **Scenario.** A reader takes 92 levels as a bound for any material, or the Pathtracer as measured.
  - **Fix.** "two materials, once each, at most 92 and 16 grey levels"; the Pathtracer's render under "Not measured";
    the comment reworded. `state3d.py`'s "a file saved with the GPU Pathtracer set holds each place once" can add
    that the shader's place was measured so on 2026-11-27 (a runner's probe).
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** item 88's row: "on two materials, once each ... at most 92 and 16 grey levels apart", the Pathtracer's
      render not measured; `state3d.py`'s GPU Pathtracer line adds the shader's place (a runner's probe,
      2026-11-27), and "Not measured" the Pathtracer's render under each model; the STALE case's comment reworded.

- [x] **TST-978 · The `ONE_FIELD` mesh row fails after another category left a mesh of another size** · `tests/test_all_tools/facts/state_file.py` (`ONE_FIELD`, the mesh row) · measured · found 2026-11-27 by the developer (Opus)
  - **Defect.** Going from the Plane to the Sphere changes the camera's near and far clip planes, which the row's
    `follows` doesn't cover. Seen in the developer's first scratch run after the code, where `editor_panels_and_fit`
    had left the Plane in the same Designer.
  - **Scenario.** A combined `alone` run of `editor_panels_and_fit` then `facts` fails the row. The pool gives each
    category a Designer of its own, so a full run doesn't.
  - **Fix.** Add `|/(near|far)_clip_plane$` to that row's `follows`.
  - **Resolution: done** (2026-11-27).
    - **Test:** `test_a_mesh_loaded_may_move_the_cameras_clip_planes` (`tests/unit/test_selftest_state_file.py`)
      failed, the clip planes left as not loaded; live, with the Plane loaded first, the mesh row failed with
      `differing after the load [.../far_clip_plane, .../near_clip_plane]`.
    - **Cause:** the camera's automatic clip planes follow the mesh's size: Plane to Sphere moves both.
    - **Fix:** the mesh row's `follows` gains `|/(near|far)_clip_plane$`.
    - **Also covered:** the camera row tolerates the clip planes already; no other row switches the mesh.
  - Note (2026-11-27): "no other row switches the mesh" is imprecise: the shader row's load switches the Sphere
    back to the base's mesh. It is safe, as the file it writes holds the base mesh's own clip planes.

- [x] **TST-979 · A test's comment and the fixture's docstrings say a Save before the 3D view drew lacks the renderer plugin's section** · `tests/unit/test_state3d.py:390` · measured · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** "a file saved before the 3D view drew holds no renderer plugin's section": a runner's probe (port
    9921) found the first Save of a fresh Designer with a graph open, before any 3D call, holding the section and the
    used material's entry. The module docstring still calls the fixture "a state file a Designer just started
    saved", now hand-augmented with that section (`tests/unit/test_selftest_state_file.py:5-7`).
  - **Scenario.** A reader adds a refusal or a draw-first step for a case that doesn't happen.
  - **Fix.** Reword the comment (the fixture's own Save left the section out) and the docstrings.
  - **Resolution: done** (2026-11-27).
    - **Test:** comments and docstrings only.
    - **Fix:** the comment says the file is "of another layout"; `test_selftest_state_file.py`'s, `test_state3d.py`'s
      and `test_view3d_helpers.py`'s texts say the fixture was edited by hand, its plugin section cut to its
      material's entry.
  - Questioned by TST-983 (2026-11-27)

- [x] **TST-980 · The `ONE_FIELD` shader row permits its parameters to change but never requires it** · `tests/test_all_tools/facts/state_file.py:713-718` · confirmed · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** The row's `follows` covers every material's `parameters/`, so it passes whether or not any changes.
    `state3d.py:31-32`, `facts/state_file.py:48` and the row's comment say "that material's parameters follow it".
  - **Scenario.** Designer stops converting the parameters on a load of the name alone; the check still passes and
    the docs still say they follow.
  - **Fix.** Assert some `parameters/` path differs after the load, or narrow the sentences to "a load of the name
    alone sets the model".
  - **Resolution: done** (2026-11-27).
    - **Test:** none: the claim narrowed instead (no agent needs it).
    - **Fix:** `state3d.py` says "A load with the name alone edited sets the model"; the measurement (55 to 118 paths
      changed, once each) moved under "Measured, not checked"; `facts/state_file.py` and the row's comment say the
      parameters "may change"; item 88's row drops them.

- [x] **TST-981 · The `MODELS_PICKED` snippet's loop variable shadows a helper** · `tests/test_all_tools/facts/state_file.py:401` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `for _model, _picked, _relinked in %r:` rebinds `_relinked`, `scene3d._relinked`, a function of the
    joined helpers. Nothing in the loop calls it today.
  - **Scenario.** A later edit of the loop calls the relink helper and gets a string.
  - **Fix.** Rename the variable (`_after_relink`).
  - **Resolution: done** (2026-11-27).
    - **Test:** `test_no_snippets_loop_rebinds_a_helpers_name` (`tests/unit/test_selftest_safety.py`), which fills
      each snippet's placeholders and compares its loop and `with` targets with the helpers' top-level names,
      failed on `[('facts/state_file.py', '_relinked')]`.
    - **Cause:** the loop variable rebound `scene3d._relinked`.
    - **Fix:** renamed `_after_relink`.
    - **Also covered:** `EXPLORER_HIDDEN`'s `_shown` and `SHOWN_ALREADY`'s `_counted` rebound helpers too, renamed
      `_real_visible_dock` and `_counting`; overrides by `def` or assignment are deliberate and left out.

- [x] **TST-982 · The live checks load only AdobeStandardMaterial, and never put a graph's outputs on the mesh after the model's load** · `tests/test_all_tools/facts/state_file.py:350` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `SET_UP_THEN_SAVED`, the `ONE_FIELD` row, `KNOWN`, `EVERY_SET_UP` and the STALE case set
    AdobeStandardMaterial; UsdPreviewSurface is only a menu pick. `SET_UP_THEN_SAVED` passes no graph, so neither
    `graph=`'s outputs nor the editor's graph's relink follows a model's load in a check. A runner's probe found both
    hold today (seven shots, the asked model at the render).
  - **Scenario.** A Designer where putting a graph's outputs on the mesh resets the material's model: the likeliest
    call, `graph=` with `shader_model=`, renders under the wrong one, and nothing fails.
  - **Fix.** The shot-as-it-renders check takes a `graph=` and runs for UsdPreviewSurface as well, reading the model
    at the render.
  - **Resolution: done** (2026-11-27).
    - **Test:** `check_a_3d_shots_set_up_is_designers_state_as_it_renders` makes two shots: `graph=` with
      AdobeStandardMaterial, then UsdPreviewSurface alone with the view showing the graph, so the editor's graph
      is relinked after the load; at each render it requires the model in the Save and in the text, the textures
      written, and no "no longer follows". Under a scratch-only sabotage (outputs put on the mesh picking OpenPBR
      Surface again), its three lines failed.
    - **Fix:** the test; no product code changed.
  - Note (2026-11-27): only the second shot's text is checked for "no longer follows"; the first shot's isn't.

- [x] **TST-983 · TST-979's fix describes the fixture's edit and the test's case wrongly** · `tests/unit/test_state3d.py:390` · confirmed · follows TST-979, generation 2 · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** "the material's entry in the renderer plugin's section removed": the case removes only the
    definition's `<name>` (`MODEL % OPENPBR`), or moves it out of the section with `stray`; the entry stays.
    `tests/unit/test_selftest_state_file.py:5-7` says "of its renderer plugin's section only its material's entry is
    kept", but the section was added by hand (19 lines inserted, none deleted, in d620c6b).
  - **Scenario.** A reader adds a case for a missing entry, thinking this one covers it, or looks for the rest of a
    section the fixture never held.
  - **Fix.** "the definition's `<name>` removed from the material's entry (`stray`: moved out of the section)"; "a
    renderer plugin's section added by hand with its material's entry, as a later Save wrote it".
  - **Resolution: done** (2026-11-27).
    - **Test:** comments and docstrings only.
    - **Fix:** the case's comment reads "the definition's <name> removed from the material's entry (`stray`: moved
      out of the section)"; the fixture's docstring says the renderer plugin's section was added with its
      material's entry, as a later Save wrote it.
    - **Also covered:** the other two "edited by hand" mentions only point to that docstring.

- [x] **HLP-298 · `state3d.py`'s "55 to 118 paths for each of the three models" names no base** · `mcp_server/designer_helpers/state3d.py:78-80` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** A load of a model's name onto a base already on it changes nothing, so "for each of the three
    models" needs the base each was loaded onto; the line gives none, and nothing else holds the figures.
  - **Scenario.** A reader can't reproduce the figure, or tell what was compared.
  - **Fix.** Name the base of each count, as the developer's measurement had it; if it wasn't recorded, drop the
    range: "changed that material's parameters with it, in both lists (once each, 2026-11-27)".
  - **Resolution: done** (2026-11-27).
    - **Test:** docstring only.
    - **Fix:** each count with its base, from the developer's probe's printed output: each load onto the state the
      one before left, 118 paths from OpenPBR Surface to AdobeStandardMaterial, 55 from there to UsdPreviewSurface,
      66 from there back to OpenPBR Surface (once each, 2026-11-27).

- [x] **TST-984 · `SET_UP_THEN_SAVED`'s comment lists its placeholders out of the template's order** · `tests/test_all_tools/facts/state_file.py:341-345` · confirmed · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** "what a 3D shot to %r with the options %r sets up, saved as it renders, copied to %r": the template
    takes the copy first (`shutil.copyfile(_saved, %r)`), then the shot and the options (`shoot_3d(%r, **%r)`).
  - **Scenario.** A new caller fills it in the comment's order and gets a runtime error.
  - **Fix.** Write the comment in the template's order.
  - **Resolution: done** (2026-11-27).
    - **Test:** comment only.
    - **Fix:** the comment lists the copy, then the shot, then the options, as the template takes them.
    - **Also covered:** `MODELS_PICKED`, the file's only other template with several placeholders, was in order.

- [x] **SRV-285 · The `mesh` Field says a file is framed by Designer's Frame, but one the view shows already keeps the user's camera** · `mcp_server/server_tools/views.py:113-115` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** "or the path of a mesh file (...), framed as Designer's Frame frames it": a file the view shows
    already is neither loaded nor framed without `view` (`test_a_mesh_file_shown_already_is_neither_loaded_nor_framed`).
  - **Scenario.** An agent expects a framed shot of the user's asset and gets the user's own camera.
  - **Fix.** "a file the view shows already keeps the user's camera".
  - **Resolution: done** (2026-11-27).
    - **Test:** the description only.
    - **Fix:** "framed as Designer's Frame frames it, unless the view shows it already".

- [x] **HLP-301 · as_text still says a mesh of the user's own is said by its path "instead", though `mesh=` takes it now** · `mcp_server/server_tools/views.py:182` · confirmed · follows HLP-296, generation 3 · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** "A mesh or map of the user's own is said by its path or URL instead": the path is an exception only
    for the map now; `mesh=` takes the path, and given back it reads as shown already (`check_a_mesh_file_shown_already_takes_no_load_and_the_3d_view_as_text_says_its_path`).
    The same in `_state_said`'s docstring (`state3d.py:441`) and item 85's row.
  - **Scenario.** An agent doesn't give the path back, thinking `mesh=` refuses it.
  - **Fix.** Narrow it, as generation 3 may: "a map not of Designer's own is said by its URL instead", in the three
    places.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** narrowed to "a map not of Designer's own is said by its URL instead", in the as_text description,
      `_state_said`'s docstring and item 85's row.

- [x] **HLP-302 · Sentences step 3 left behind** · `mcp_server/designer_helpers/scene3d.py:469-473` · confirmed · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** `_3d_set_up`'s docstring says several materials are refused "here", which a mesh file the call loads
    now is after its load; ROADMAP's **Per material** bullet says "before anything changes", the exception only in
    "Checked first"; `frames3d.py:72` and `:107` give `SETTLE_LIMIT` as each wait's limit, where an import's is
    `IMPORT_LIMIT`; item 131's row lists "a mesh of the user's own framed as the cube"; item 84's row says "a file the
    view shows already is neither loaded nor framed", not so with `view`.
  - **Scenario.** A reader of each takes the old rule as current.
  - **Fix.** One clause each.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** `_3d_set_up`'s docstring, ROADMAP's **Per material** bullet (pointing to Checked first's exception),
      `frames3d.py`'s docstring and `SETTLE_LIMIT` comment (naming `IMPORT_LIMIT`), item 131's row ("since item
      84, framed by Designer's Frame") and item 84's row ("unless `view` is given").

- [x] **HLP-303 · A mesh file shown already with `view` is framed before its several-materials refusal** · `mcp_server/designer_helpers/scene3d.py:649` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `framing = shown.startswith(USERS_MESH) and ('mesh' in changes or view is not None)`; the up-front
    check `_state_fields(base, owns)` sits in `if not framing:`. With the file shown already and `view` given, its
    materials are in the base, yet Frame moves the camera first and the refusal comes from `framed()`.
  - **Scenario.** `mesh=<the OBJ the view shows>, view='Top', tiling=2`: the camera moves, then the call is refused
    and the view put back, where ROADMAP's rule says refused before anything changes.
  - **Fix.** Read `_state_fields(base, owns)` before anything when `'mesh' not in changes`; a unit test with
    `view='Top'` expecting only the Save.
  - **Resolution: done** (2026-11-27).
    - **Test:** the shown-already refusal's unit test, parametrized with `view` None and `Top`; the `Top` row failed,
      Frame triggered before the refusal.
    - **Fix:** unless a new mesh file comes (`new_file`), the base's material fields are read before anything
      changes; a preset switch still reads the base's material.
  - Questioned by HLP-311 (2026-11-27)

- [x] **HLP-304 · `view3d.py` says a mesh file's materials stay listed as unused after another mesh's load** · `mcp_server/designer_helpers/view3d.py:41` · measured · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** A runner (port 9941) loaded the OBJ, box.fbx, the Samba FBX, the OBJ and box.fbx in turn: as Reset
    Scene returned, the menu listed only Default, unused, each time; the earlier file's materials weren't listed.
    `scene3d.py:50` says so.
  - **Scenario.** A reader filters out "unused" entries that never come.
  - **Fix.** Drop or correct the sentence.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** the sentence dropped.
  - Note (2026-11-28): HLP-322's probe measured an earlier mesh file's materials listed "(unused)" once the
    import ended; HLP-304 saw them unlisted as Reset Scene returned. `view3d.py` records both.

- [x] **HLP-305 · `_set_up_checked`'s docstring reads as accepting a path that is no file** · `mcp_server/designer_helpers/view3d.py:383-385` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** "unless the mesh is a file's absolute path, and no file's then": the code refuses a path that is no
    file ("no such mesh file").
  - **Scenario.** A reader thinks a missing file passes the check.
  - **Fix.** Two plain sentences.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** two sentences: a mesh the Scene menu lacks is taken as a mesh file's absolute path, and refused
      unless a file is there.

- [x] **TST-985 · README's sentence on a mesh file says more than the tests show, in a bullet a person with the symptom won't read** · `README.md:424-426` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** "read where it is, never changed": no check compares the mesh files; "Designer's log says why": the
    log measured says "Scene import failed"; and the symptom (an empty, slow shot) sits in the security bullet, not
    in Troubleshooting.
  - **Scenario.** A person with an empty shot finds nothing in Troubleshooting.
  - **Fix.** A Troubleshooting row with what was measured (Designer logs "Scene import failed", the wait ends at
    30 s, HLP-299's line); drop "never changed", or keep "read where it is" only.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** the 3D paragraph keeps "A mesh file of yours is read where it is."; a Troubleshooting row: the shot
      says `didn't import within 30 s` and shows no mesh, the log says `Scene import failed` with the importer's
      error, and shooting again won't help.
  - Questioned by TST-997 (2026-11-27)

- [x] **TST-986 · Item 90 doesn't list what a mesh file relies on, measured only on macOS** · `ROADMAP.md` (item 90) · confirmed · found 2026-11-27 by two reviewers (Sonnet)
  - **Defect.** `_mesh_id` writes `file://` + `os.path.abspath`'s path, which on Windows gives `file://C:\...`, where
    Designer's form there is `file:///C:/...` (step 1's Windows test); the import's end on the Materials menu and
    Frame after a mesh file's load are measured only on macOS too. Item 84's and item 90's rows name none of them.
  - **Scenario.** The Windows work misses the mesh file's URL.
  - **Fix.** Add the three to item 90's row.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** item 90's row adds the URL form (Windows' `file:///C:/...` against what `abspath` gives there), the
      import's end on the Materials menu, and Frame after the load.
  - Questioned by TST-993 (2026-11-27)

- [x] **TST-987 · Two comments cite "the plan's choice", which ends with the branch** · `tests/test_all_tools/facts/checks.py:765` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** PLAN.md is deleted with the branch; the same at `tests/unit/test_view3d_helpers.py:1957`.
  - **Scenario.** A reader looks for a plan that isn't there.
  - **Fix.** "the user, 2026-11-27" (step 3's approved framing).
  - **Resolution: done** (2026-11-27).
    - **Test:** comments only.
    - **Fix:** both say "the user, 2026-11-27".

- [x] **TST-988 · A unit test pins an error saying a refused tiling was set** · `tests/unit/test_view3d_helpers.py:1530-1545` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `'...; the 3D view was already set: %s, %s' % (mine, said)` with `said = 'tiling 2'`: the tiling was
    refused, never set, and the view put back. The step's `done` entry holds the whole step.
  - **Scenario.** The user is told the tiling was set.
  - **Fix.** For a step refused after its first load, `done` names only what was set (the mesh), and the pins follow.
  - **Resolution: done** (2026-11-27).
    - **Test:** the refusal test, given `environment_exposure=1.0` too, expects "already set: <mesh>, environment
      exposure 1"; it failed, the code naming the whole step.
    - **Fix:** a mesh file's step records the mesh and the light until `framed()` succeeds, then the whole step.

- [x] **TST-989 · The import check's docstring claims what it doesn't measure** · `tests/test_all_tools/facts/checks.py` (`check_a_mesh_files_import_ends_once_the_materials_menu_lists_its_materials`) · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** "The Samba FBX's import outlasts the view's restart and settle, so a load of a mesh file waits for its
    materials": `IMPORTED` waits for the materials first; nothing shows the import outlasting the settle.
  - **Scenario.** A reader takes the old wait's failure as checked live.
  - **Fix.** "measured once (scene3d.py); not checked here".
  - **Resolution: done** (2026-11-27).
    - **Test:** a docstring only.
    - **Fix:** it says the outlasting import was measured once (scene3d.py) and isn't checked there.

- [x] **TST-990 · `mesh_renders.py` has no unit test, and `IMPORTED`'s first read passes events first** · `tests/test_all_tools/facts/mesh_renders.py` · measured · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `shown`, `coloured` and `apart` and their thresholds have no test on made-up images, where
    `tests/unit/test_selftest_renders.py` tests `editor_panels_and_fit`'s own. `IMPORTED` reads the Materials menu as
    Reset Scene returns through `_materials_used`, which runs `_process_events()` first; a runner (port 9941) saw
    box.fbx's and the OBJ's import end within one more event pass, so that read is one pass from passing on the
    wrong state. TST-896 and TST-943 pin no event pass before such a read for `ENTRIES`.
  - **Scenario.** Under load, the read sees the import ended and the check fails at random.
  - **Fix.** Unit tests of the three on made-up images; the first read without an event pass, pinned as `ENTRIES`'s is.
  - **Resolution: done** (2026-11-27).
    - **Test:** `tests/unit/test_selftest_mesh_renders.py` tests `shown`, `coloured` and `apart` on made-up images
      (it passed: no bug, no test); `test_the_import_check_reads_the_materials_menu_right_as_the_trigger_returns_with_no_event_pass`
      failed first.
    - **Fix:** `IMPORTED` reads the menu with `_sf_used()`, with no event pass, as Reset Scene returns.
  - Questioned by TST-994 (2026-11-27)

- [x] **TST-991 · The new shot check's options table is typed looser than it is** · `tests/test_all_tools/facts/checks.py:811` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `options: dict[str, dict[str, object]]` where each value is a tool's arguments (`ToolArgs`, imported
    there).
  - **Scenario.** A wrong argument's type goes unchecked by mypy.
  - **Fix.** `dict[str, ToolArgs]`.
  - **Resolution: done** (2026-11-27).
    - **Test:** types only; mypy passed.
    - **Fix:** `dict[str, ToolArgs]`.

- [x] **TST-992 · `check_designers_frame_gives_the_view_tables_poses` fails on the Cube framed from Bottom in a tall panel** · `tests/test_all_tools/facts/checks.py` (`check_designers_frame_gives_the_view_tables_poses`) · measured · found 2026-11-27 by the developer (Opus)
  - **Defect.** "A panel taller than wide": the Cube from Bottom (pitch -90) framed at 244.698 where the table says
    180.992, in a 161x423 viewport; the other ten meshes pass. It failed in every scratch run of step 3, and at its
    HEAD with step 3's change stashed.
  - **Scenario.** The final check's live run fails.
  - **Fix.** Find out whether it fails on `main` too (a worktree of main), then fix the check or the table, as what
    Designer does says.
  - **Resolution: done** (2026-11-27).
    - **Test:** it fails on `main` too: a worktree of main in a fresh Designer gave 244.698 against 180.992.
    - **Cause:** not understood. At a floating 300 x 500 (a viewport of 159 to 161 x 423), each mesh from any view
      framed 1.35 to 1.41 times farther (4 runs); at 159 x 623, 186 to 306 x 423, and once 214 x 423, Designer
      framed as the table. A quirk of that size, not of the aspect.
    - **Fix:** the check's tall panel is 400 x 500 (a viewport of 256 x 423), framed as the table in every run; the
      quirk is recorded in `state3d.py` under "Not understood, not modelled".
  - Questioned by HLP-306 (2026-11-27)

- [x] **HLP-307 · `graph=` after a mesh file that didn't import still runs, and says the outputs went on the mesh** · `mcp_server/designer_helpers/scene3d.py:700-706` · measured · follows HLP-299, generation 2 · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** HLP-299's fix skips Frame and the second load, not the graph step. A runner (port 9952): `mesh=<a
    corrupt .fbx>, graph=<two outputs>` took 34 s, opened no dialog, rendered an empty view, and said "<path> (the mesh
    file didn't import within 30 s: ...), graph ...'s outputs on the mesh".
  - **Scenario.** An agent reads that the outputs are on the mesh and judges an empty render.
  - **Fix.** Skip the graph step when the mesh file didn't import, as Frame is.
  - **Resolution: done** (2026-11-27).
    - **Test:** `test_a_graphs_outputs_arent_put_on_a_mesh_file_that_didnt_import`, with `graph=` and with the view
      following the editor's graph; it failed ("graph g's outputs on the mesh"); live, the unimportable file's shot
      with `graph=` failed the same way.
    - **Fix:** the graph step and the relink after the load are skipped when the mesh file didn't import.
    - **Also covered:** the relink guard, pinned by the no-graph row.
  - Note (2026-11-27): the live check passed after the fix (12 of 12 in the developer's scratch run, twice).
  - Questioned by HLP-309 (2026-11-27)

- [x] **HLP-308 · `_mesh_id` encodes three characters where Designer saves twelve encoded** · `mcp_server/designer_helpers/state3d.py` (`_mesh_id`) · measured · follows HLP-300, generation 2 · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** A runner (port 9952): a path holding `"`, `<`, `>`, `^`, a backtick, `{`, `|`, `}` or `\` imports when
    written as is, but Designer saves its id as `QUrl.fromLocalFile(path).toString()` gives it (`%22`, `%3C`, `%3E`,
    `%5E`, `%60`, `%7B`, `%7C`, `%7D`, `%5C`), so the id written never equals the one saved. The docstrings say the
    other characters "stay as written". The `USERS_MESH` comment (`state3d.py:144-146`) and item 84's row say the
    plain path; eight places in `tests/test_all_tools/facts/checks.py` build `USERS_MESH + path` where `_mesh_id` exists.
  - **Scenario.** The user's view shows `my|mesh.fbx`; a shot with `mesh=` that path reloads and frames it again,
    the user's camera lost, where it should read as shown already.
  - **Fix.** Encode the twelve characters Qt does (`%`, `#`, `?` and these nine), unit rows for each, the docstrings
    and the comment, item 84's row pointing at `_mesh_id`, the checks through `_mesh_id`.
  - **Resolution: done** (2026-11-27).
    - **Test:** a `test_state3d` row, `a"<>^`{|}\b.obj` held as `a%22%3C%3E%5E%60%7B%7C%7D%5Cb.obj` and said back
      (it failed); live, the OBJ in a folder `mesh #2|`, the id saved at the render compared with `_mesh_id`'s
      (it failed: `%7C` saved where `|` was written).
    - **Fix:** `state3d.URL_ESCAPES`, one translation table over the twelve characters; the docstrings, the
      `USERS_MESH` comment and item 84's row say which, measured.
    - **Also covered:** the nine places in `facts/checks.py` building `USERS_MESH + path` go through `_mesh_id`.
  - Note (2026-11-27): eight places in `facts/checks.py` moved onto `_mesh_id`, not nine (one used it already); the
    live check passed after the fix (12 of 12, twice).
  - Questioned by HLP-310 (2026-11-27)

- [x] **TST-993 · Item 90's row cites "step 1", states Designer's Windows form as known, and runs no `facts` on Windows** · `ROADMAP.md` (item 90) · confirmed · follows TST-986, generation 2 · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** "Designer's form on Windows (`file:///C:/...`, step 1's Windows test)": step 1 is a step of the plan,
    gone with the branch; the test (`test_a_windows_mesh_url_is_said_as_windows_reads_it`) reads a made-up fixture,
    not a form seen from Designer; the row's Approach runs only `editor_panels_and_fit` on Windows, where every mesh
    file check is in `facts`.
  - **Scenario.** Whoever takes up item 90 can't find "step 1", takes the form as measured, and never runs the mesh
    file's checks.
  - **Fix.** Name the test; "Qt's form, not yet seen from Designer"; add `facts` to the Approach.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** the row names `test_a_windows_mesh_url_is_said_as_windows_reads_it`, says Qt's form on Windows is
      not yet seen from Designer, and adds `facts` to the Approach (its checks need a Designer with a home of its
      own there first, REVIEW.md TST-890).

- [x] **TST-994 · The `faint` row of the `shown` unit test never reaches the threshold it names** · `tests/unit/test_selftest_mesh_renders.py:41` · confirmed · follows TST-990, generation 2 · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** The box covers the whole image, the top-left pixel included, and `shown` compares each pixel with
    `grey[0, 0]`: every difference is 0, for any `BACKGROUND` of 1 or more.
  - **Scenario.** `BACKGROUND` lowered to 1 still passes.
  - **Fix.** Paint `faint` below the top-left only (a difference under 25, uncounted), and a row just over 25 that
    counts.
  - **Resolution: done** (2026-11-27).
    - **Test:** with `BACKGROUND` set to 1, the old row gave 0.0 and the new one 0.5 (a scratch run).
    - **Fix:** `faint` is painted below the top-left only, 24 levels off and uncounted; a `just_over` row 26 levels
      off is counted.

- [x] **TST-995 · `test_selftest_mesh_renders.py`'s boxes take a colour of any length** · `tests/unit/test_selftest_mesh_renders.py:29` · confirmed · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** `list[tuple[int, int, int, int, tuple[int, ...]]]`, where the colour is always three channels and
    `RGB8` exists in `tests/unit/image_files.py`.
  - **Scenario.** A colour of two channels goes unchecked by mypy.
  - **Fix.** `RGB8`.
  - **Resolution: done** (2026-11-27).
    - **Test:** types only; mypy passed.
    - **Fix:** `saved()`'s boxes typed with `RGB8`.

- [x] **TST-996 · Two comments give the framing band wider than the law** · `tests/unit/test_state3d.py:238-239` · confirmed · follows HLP-306, generation 3 · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** "Farther where FRAME_ANGLE x the height over the width is past 90 degrees and below 180": the law
    exceeds 1 only past 180 - 54.43 = 125.57 degrees (the test's own 161 x 323, at 109 degrees, expects 1.0).
    `tests/test_all_tools/facts/checks.py:1256-1257` says the check's viewport, "159 to 214 x 423", is in the band,
    which ends near 183 wide at 423 tall. `test_state3d.py:700` still says "% first", where one `str.translate` makes
    the order moot.
  - **Scenario.** A reader adds a row at 100 degrees expecting farther.
  - **Fix.** Narrow only: "past 180 degrees minus FRAME_ANGLE (125.6)"; "159 to 214 x 423, mostly in the band (up to
    about 183 wide)"; drop "% first".
  - **Resolution: done** (2026-11-27).
    - **Test:** comments only, narrowed as generation 3 allows.
    - **Fix:** "past 180 degrees minus FRAME_ANGLE (125.6) and below 180"; "159 to 214 x 423: mostly in the band (up to
      about 183 wide)"; "% first" dropped.

- [x] **HLP-309 · `scene3d.py`'s docstrings list only Frame and the second load as skipped after a file that didn't import** · `mcp_server/designer_helpers/scene3d.py:57-60` · confirmed · follows HLP-307, generation 3 · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** "no Frame and no second load follow (REVIEW.md HLP-299). Nothing more is done": HLP-307 skips the
    graph step and the relink too. `_3d_set_up`'s docstring says "Then `graph`'s outputs on the mesh" with no
    condition.
  - **Scenario.** A maintainer concludes `graph=` still runs on a failed import, HLP-307's defect.
  - **Fix.** Narrow only: "no Frame, second load, graph step or relink follow"; drop "Nothing more is done"; the
    condition in `_3d_set_up`'s docstring.
  - **Resolution: done** (2026-11-27).
    - **Test:** docstrings only, narrowed as generation 3 allows.
    - **Fix:** "no Frame, second load, graph step or relink follow (REVIEW.md HLP-299, HLP-307)", "Nothing more is done"
      dropped; `_3d_set_up`'s docstring: "unless a mesh file the call loads didn't import".

- [x] **HLP-310 · Designer saves `[` and `]` encoded, and `URL_ESCAPES` leaves them** · `mcp_server/designer_helpers/state3d.py` (`URL_ESCAPES`) · measured · follows HLP-308, generation 3 · found 2026-11-27 by a reviewer (Sonnet)
  - **Defect.** A runner (port 9971): of fifteen more characters, Designer saves `[` and `]` as `%5B` and `%5D` (Qt's
    form), the others as written; all imported. A path holding either never reads as shown already. A defect in the
    tool's code, so the fix isn't held to narrowing.
  - **Scenario.** The user's view shows `asset [v2].fbx`; a shot with `mesh=` that path reloads and reframes it, the
    user's camera lost.
  - **Fix.** Add `[` and `]` to `URL_ESCAPES` (fourteen), a unit row, and the docstrings' list.
  - **Resolution: done** (2026-11-27).
    - **Test:** the encoded row of `test_a_mesh_given_is_held_by_an_id_said_back_as_given` with `[` and `]` failed
      (`_mesh_id` gave them as written); with them out of `URL_ESCAPES` again, the row fails, so it guards the fix.
    - **Fix:** `URL_ESCAPES` takes `[` and `]`; the module docstring lists them among the encoded characters and the
      thirteen others measured among those saved as written.
    - **Also covered:** a row pins those thirteen as written; no other place lists the escapes.
  - Questioned by HLP-314 (2026-11-27)

- [x] **HLP-313 · `scene3d.py` says a mesh file always takes a Save and a second load** · `mcp_server/designer_helpers/scene3d.py:20-23` · confirmed · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** "Then a Save gives Frame's pose ... written and loaded in a second load" and (`:480-481`) "framed by
    Frame with a second load": `framed()` returns after Frame when no camera or material option is given, and skips
    the second load when nothing differs, as the approved step says ("a second load only when they are given").
  - **Scenario.** A maintainer counts two loads and a Save for `mesh=<file>` alone.
  - **Fix.** "when camera options or the material's fields are given", in both.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** "when camera options or the material's fields are given", in both places.
  - Questioned by HLP-317 (2026-11-27)

- [x] **HLP-314 · `state3d.py` files facts only probes measured under "pinned by those checks"** · `mcp_server/designer_helpers/state3d.py:10-21` · confirmed · follows HLP-310, generation 4 · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** The heading says the facts below it are "measured ... and pinned by those checks", but the URL
    characters beyond `#`, `|` and a space, and the 18 tall viewports (`:68-73`; the live check uses one size), were
    measured by runners' probes only.
  - **Scenario.** After a Designer update a maintainer relies on `facts` to catch a changed encoding, and nothing fails.
  - **Fix.** Narrow only: "(`#`, `|` and a space checked live; the others measured by probes, not checked)", and the
    same for the viewports, or move them under "Measured, not checked".
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only, narrowed as generation 4 allows.
    - **Fix:** "`#`, `|` and a space are checked live; the others were measured by runners' probes, not checked"; the
      tall viewports "a runner's probe, not checked".

- [x] **TST-997 · README's Troubleshooting row takes every 30 s timeout for a file Designer can't import** · `README.md:474` · confirmed · follows TST-985, generation 2 · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** "Designer couldn't import the file. ... Shooting again won't help: export the mesh again": the tool says
    only that the import didn't end within 30 s; a large valid asset may take longer.
  - **Scenario.** A person re-exports a large asset for nothing and finds no "Scene import failed" in the log.
  - **Fix.** "Designer didn't import the file within 30 s. If its log says `Scene import failed`, export it again or in
    another format; if not, the import takes longer than the shot waits."
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** the row says the file didn't import within 30 s, and tells the two cases apart by the log.

- [x] **TST-998 · Two unit-test module docstrings weren't updated for the branch** · `tests/unit/test_view3d_helpers.py:1-5` · confirmed · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** "the camera, the mesh, the tiling and the environment written in one load" leaves out the shader model,
    the 3D view as text and a mesh file's two loads; `tests/unit/test_view3d.py:1` lists items 7, 73, 74 and 85, not 84
    and 88.
  - **Scenario.** A reader looks elsewhere for the shader model's and a mesh file's tests.
  - **Fix.** One clause each.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only.
    - **Fix:** both module docstrings name items 84 and 88, the shader model, mesh files and as_text.

- [x] **TST-999 · Step 3's unit tests assume POSIX paths for a mesh file** · `tests/unit/test_view3d_helpers.py:34` · confirmed · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** `showing()` builds `'<id>file://%s</id>' % path`, and seven tests expect `'file://' + mine`; on Windows
    `tmp_path` is `C:\...`, which `_mesh_id` encodes (`\` as `%5C`), so none matches. `tests/unit/test_view3d.py:166`
    expects `mesh: no such file: /...`. TST-966's pattern; `test_windows_simulation.py` keeps `os.path` POSIX.
  - **Scenario.** A unit run on Windows fails 11 cases (ROADMAP item 18).
  - **Fix.** Build the expected ids with `state3d._mesh_id(path)`, in `showing()` too; match the refusal with
    `re.escape(os.path.join(os.getcwd(), 'gone.fbx'))`.
  - **Resolution: done** (2026-11-27).
    - **Test:** not seen failing here (no Windows); `test_windows_simulation` passes.
    - **Fix:** `showing()` and the expectations build the id with `state3d._mesh_id`; the refusal matches
      `re.escape(os.path.join(os.getcwd(), mesh))`.
  - Questioned by TST-1016 (2026-11-28)

- [x] **TST-1000 · Two containers in the new test helpers are typed looser than they are** · `tests/unit/test_selftest_safety.py:301` · confirmed · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** `bound: list[ast.AST]` holds only expressions (`list[ast.expr]`); `tests/unit/test_selftest_check_setups.py:264`'s
    `shots: list[tuple[str, dict[str, object]]]` and its `given` are shoot_3d's keyword arguments (`View3dOptions`).
  - **Scenario.** A wrong key goes unchecked by mypy.
  - **Fix.** `list[ast.expr]`; the fake as `def shoot(path: str, **shown: Unpack[View3dOptions]) -> None`.
  - **Resolution: done** (2026-11-27).
    - **Test:** types only; mypy passed.
    - **Fix:** `list[ast.expr]`; the fake `shoot(path, **shown: Unpack[View3dOptions])`, `given: View3dOptions`.

- [x] **TST-1001 · The put-back check looks for a leftover backup only after an as_text call that clears it** · `tests/test_all_tools/facts/checks.py:1467-1495` · confirmed · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** `first` (as_text), the shot, then `again` (as_text), then `not os.path.exists(state_file.backup(...))`:
    `_state_back_up` puts back or removes a leftover before its own backup, so a backup the shot left is consumed by
    `again`, and one the first as_text left by the shot. On main only `AOV_READ_BACK` came between the shot and that
    test.
  - **Scenario.** A shot that leaves its backup passes the check.
  - **Fix.** Record whether the backup exists right after each of the three calls, and test each.
  - **Resolution: done** (2026-11-27).
    - **Test:** a test-strength fix: it passed before and after.
    - **Fix:** whether a backup exists is recorded right after each of the three calls, and each is tested.

- [x] **TST-1002 · box.fbx's geometry isn't checked by pixels** · `tests/test_all_tools/facts/checks.py:879` · confirmed · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** `bool(box) and rendered('box', box) and tiling == {'tiling': 2.0} and linked`: the approved step names
    box.fbx among the meshes whose geometry shows by pixels; a black or framed-off render passes.
  - **Scenario.** A box.fbx shot renders nothing visible, and the check passes on the Save.
  - **Fix.** `and mesh_renders.shown(shots['box']) > 0.01` (a runner measured 0.334 for box.fbx, 0.0 for an empty
    view).
  - **Resolution: done** (2026-11-27).
    - **Test:** a test-strength fix: it passed before and after (`box_shown` 0.087 in a fresh run).
    - **Fix:** `box_shown > 0.01`.

- [x] **TST-1003 · The record `IMPORTED` prints is typed `dict[str, str | None]`** · `tests/test_all_tools/facts/state_file.py:617` · confirmed · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** Its four keys are known (`AT_TRIGGER`, `ENDED`, `IMPORTED`, `SETTLED`), and `imported_as`
    (`facts/checks.py:684`) and the `read` tuple (`:717`) use them.
  - **Scenario.** A mistyped key fails the check at run time instead of mypy.
  - **Fix.** A TypedDict.
  - **Resolution: done** (2026-11-27).
    - **Test:** a scratch mypy run flags `said['IMPORTD']` now.
    - **Fix:** a `state_file.Imported` TypedDict, used by `imported_as` and `read`.

- [x] **TST-1004 · `state_file.MESHES` names a folder, where the snippet's `MESHES` is the Scene menu's list** · `tests/test_all_tools/facts/state_file.py:432` · confirmed · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** `MESHES = os.path.join(BUNDLE, 'assets', 'meshes')`, while the STATE snippet in the same file reads
    `if m in MESHES`, view3d's list; the docstring's "(the project's OBJ, Designer's box.fbx and the user's Samba FBX
    (MESHES))" fits neither.
  - **Scenario.** A reader of `_sf_meshes` takes the test for a match on the assets' path.
  - **Fix.** Rename the constant (`MESH_FILES`), and "(view3d.MESHES)" in the docstring.
  - **Resolution: done** (2026-11-27).
    - **Test:** a rename only.
    - **Fix:** `MESH_FILES`; the docstring says the Scene menu "checks none of its meshes (view3d.MESHES)".
  - Questioned by TST-1006 (2026-11-27)

- [x] **HLP-317 · The docs count one load, or two, where the code does otherwise** · `mcp_server/designer_helpers/scene3d.py:506-512` · confirmed · follows HLP-313, generation 2 · found 2026-11-27 by three reviewers (Opus)
  - **Defect.** `_3d_set_up`'s docstring says "In one load of the state file: ... the material's shader model", which a
    switch from a mesh file now takes in a second load; `scene3d.py:3` ("in one load"), `ROADMAP.md:74` ("the call's one
    load") and `tests/unit/test_view3d_helpers.py:1-7` ("the shader model written in one load", and a mesh file "then
    written in a second load") say the same; `scene3d.py:25-28` says the second load comes when material fields are
    given, where `framed` skips it when they equal the import's.
  - **Scenario.** A maintainer builds a new per-material field into the first load only, or expects two loads.
  - **Fix.** Narrow only: drop "one", or point to the module docstring's step 4; "in a second load, of what differs from
    the Save"; the test module's docstring with it.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only, narrowed.
    - **Fix:** "in one load or two (step 4)"; step 4's material fields "that differ from the Save ... none when nothing
      differs"; `_3d_set_up`'s docstring and ROADMAP.md:74 point to step 4; the test module's docstring "written in its
      loads".

- [x] **TST-1005 · HLP-315's fix never cites HLP-315** · `tests/unit/test_view3d_helpers.py:670` · confirmed · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** The comment cites "HLP-311: set back by name", as does `:1945`; `_overrides_back` (`scene3d.py:326`)
    cites only HLP-292.
  - **Scenario.** A reader follows HLP-311 to a preset's material and misses the set-back's own entry.
  - **Fix.** Cite HLP-315 there and in `_overrides_back`'s docstring.
  - **Resolution: done** (2026-11-27).
    - **Test:** comments only.
    - **Fix:** the two test comments and `_overrides_back`'s docstring cite HLP-315.

- [x] **TST-1006 · `facts/state_file.py`'s docstring still labels three meshes `MESH_FILES`** · `tests/test_all_tools/facts/state_file.py:16-17` · confirmed · follows TST-1004, generation 2 · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** "the project's OBJ, Designer's box.fbx and the user's Samba FBX (MESH_FILES)": `MESH_FILES` is
    `assets/meshes`, and box.fbx is Designer's (`BOX_PATH`).
  - **Scenario.** A reader looks for box.fbx in the assets' folder.
  - **Fix.** "(OBJ, SAMBA; box.fbx: BOX_PATH)", or drop the parenthetical.
  - **Resolution: done** (2026-11-27).
    - **Test:** a docstring only.
    - **Fix:** "(OBJ, SAMBA; box.fbx: BOX_PATH)".

- [x] **TST-1007 · Two guards the fixes added have no unit test that fails without them** · `mcp_server/designer_helpers/view3d.py:233` · confirmed · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** `_fade`'s `or menu in self.seen` (HLP-312): the fake hands the look the material menu at its first run
    in the action, so no test has a look find the Explorer's menu again first; deleted, every test passes.
    `_overrides_back`'s `if name in overridden` (`scene3d.py:335`, HLP-315): the fake lists the base's names after
    every load, so no test reaches a material the base doesn't name; without the guard, a preset view with Override off
    switched to a mesh file raises `KeyError`.
  - **Scenario.** A refactor drops either guard and the unit suite stays green.
  - **Fix.** A unit row whose action loop runs the look on the Explorer's menu first, then on the material menu (one
    pick, one hold); a fake hook that makes a load list new names, a base of `{'Default': False}` (no error, Default set
    back, the new names left as they are).
  - **Resolution: done** (2026-11-27).
    - **Test:** `test_the_explorers_menu_found_again_as_the_action_runs_is_neither_faded_nor_picked_again` (without
      the guard the Explorer's menu was faded and held twice) and
      `test_override_material_of_a_material_the_base_doesnt_name_is_left_as_a_load_lists_it` (without the guard
      `KeyError: 'only'`), each seen failing with its guard removed.
    - **Fix:** the tests; the fake's `loaded_materials` lets a load list new names.

- [x] **TST-1008 · The relink check's verdict hangs on a 3 s settle it doesn't need, and its detail leaves the cause out** · `tests/test_all_tools/facts/checks.py:1032` · confirmed · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** `said == imported_as(OBJ_MATERIALS) and ...`: `imported_as` requires `'SETTLED': 'True'`, bounded by
    SETTLE_LIMIT, where the relink needs only the import ended with both materials; the detail line omits `said`.
    `:782` (the Frame check) has the same gate.
  - **Scenario.** In the full run beside the unit suite, the OBJ's view takes over 3 s to count back; the check fails
    with good materials in its line and no cause: a test failing at random.
  - **Fix.** Gate on `said['ENDED'] == 'True'` and the materials imported, and put `said` in the detail; the same at
    `:782`.
  - **Resolution: done** (2026-11-27).
    - **Test:** a robustness fix: not seen failing here (it needs a slow view).
    - **Fix:** `ended_with(said, materials)` waives only the settle; it gates the relink check, the Frame check and
      `check_a_3d_shot_puts_a_mesh_file_the_user_showed_back` (the same pattern), each detail printing `said`; the
      import check keeps the full `imported_as`.
  - Questioned by TST-1019 (2026-11-28)

- [x] **TST-1009 · Moving a test onto a mesh file dropped its mesh line** · `tests/unit/test_state3d.py:822` · confirmed · follows HLP-311, generation 3 · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** `assert said[2:6] == SAID[2:6]` (it was `said[:1] + said[2:6] == SAID[:1] + SAID[2:6]`): the test,
    named "...the others are read", no longer checks the mesh line is read when the tiling can't be.
  - **Scenario.** A change that drops the mesh line when the tiling fails passes.
  - **Fix.** Restore the mesh line, as the file's path `_mesh_said` gives: it undoes the fix's weakening, no check added
    beyond what the test held before.
  - **Resolution: done** (2026-11-27).
    - **Test:** it passes on the current code: it restores what the earlier fix weakened.
    - **Fix:** `assert said[0] == 'mesh: /Users/u/box.obj'`, with `urls_as_posix`.

- [x] **HLP-319 · Step 4, `_state_overridden` and a test comment state the load rule for every material** · `mcp_server/designer_helpers/scene3d.py:19-20` · confirmed · follows HLP-316, generation 4 · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** "as a load set it only so" (step 4), "A load set a material's shader model only so"
    (`state3d.py:313-314`) and `tests/unit/test_state3d.py:521`: the bullet below step 4 (`scene3d.py:85-86`) records a
    mesh file's own material, its Override off, taking the model held not overridden.
  - **Scenario.** A maintainer thinks a mesh file's material needs the flag to take the model, when it needs it to show.
  - **Fix.** Narrow only: "as a load set Default's model only so, and the render shows a model only with Override on".
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only, narrowed.
    - **Fix:** "as a load set Default's model only so, and the render shows a model only with Override on", in
      step 4, `_state_overridden`'s docstring and the test comment.

- [x] **HLP-320 · The wording HLP-316's fix wrote says more, or less, than was measured** · `mcp_server/designer_helpers/scene3d.py:85-91` · confirmed · follows HLP-316, generation 4 · found 2026-11-27 by two reviewers (Opus)
  - **Defect.** The figures (0.0, 5.9, 0.05, 25, 65.6 grey levels) are means (`mesh_renders.apart`) but aren't said so,
    beside item 88's maxima; "the OBJ" there is the probe's one-material OBJ, two lines after "the project's OBJ"; the
    bullet doesn't say which claims its two facts checks pin (held overridden, it took; a render over 1 level from
    plain) and which probes alone measured; `state3d.py:42` says "the fixture's Default" of the category Designer's own
    Save. Also: the new live check's label "the model shown" (`tests/test_all_tools/facts/checks.py:1116`), which
    Override alone satisfies; `framed`'s docstring (`scene3d.py:654-658`) and item 84's row "written and loaded" where
    the load is skipped when nothing differs; `scene3d.py:30`, "with no first", false with a light option;
    `scene3d.py:101-104` citing only HLP-311 for the set-back by name; `tests/unit/test_view3d_helpers.py:1991`'s "the
    new ones left on", the fake's, not Designer's.
  - **Scenario.** A reader takes a mean for a maximum, or the wrong OBJ, or a probe's figure for a checked one.
  - **Fix.** Narrow only: "on average", "a one-material OBJ's", "the rest measured by probes, not checked", "the
    session's Default", "the model held", "when they differ", the light named, HLP-315 cited, "the fake's".
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only, narrowed.
    - **Fix:** "on average", "a one-material OBJ's", which claims the checks pin and which probes measured,
      "the session's Default", "the model held", "when they differ", "a first load only for the light", HLP-315 cited,
      "as the fake's load turns each on"; the runner's port-9997 fact recorded beside the set-back.

- [x] **TST-1010 · ROADMAP item 88 still says a load of the name alone sets the model** · `ROADMAP.md:123` · confirmed · follows HLP-316, generation 4 · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** "Measured: a load of the name alone sets the model", and its Note "loading it sets it": HLP-316
    measured a load of the name alone keeping OpenPBR on Default held not overridden. `tests/test_all_tools/facts/state_file.py:51`
    ("One edited alone loads it") is true of its check's base only.
  - **Scenario.** A reader of the Done record takes the one-field load as unconditional.
  - **Fix.** Narrow only: "... sets the model of a material held overridden (scene3d.py)".
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only, narrowed.
    - **Fix:** "sets the model of a material held overridden (`scene3d.py`)" in item 88's row and Note;
      `facts/state_file.py`: "the base's Default held overridden".

- [x] **SRV-286 · The docs still say a shader model the view holds is shown already** · `mcp_server/server_tools/views.py:182-183` · confirmed · follows HLP-318, generation 5 · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** The as_text Field ("given back to it, the value reads as shown already"), `_state_said`'s docstring
    (`state3d.py:509-511`), `_3d_set_up`'s docstring (`scene3d.py:528-530`, "that differ from a Save"), item 84's row
    (`ROADMAP.md:121`, "of what differs from the Save after Frame"), the set-up rules (`ROADMAP.md:86`, "a field the
    user's state holds already isn't written"), a test comment (`tests/unit/test_state3d.py:845`) and the shown-already
    check's docstring (`editor_panels_and_fit/checks.py:856-858`): HLP-318's fix writes a model held already when the
    used material's Override is off.
  - **Scenario.** On the Plane with Default's Override off, as_text says `shader_model: OpenPBR Surface`; given back,
    the shot loads, turns Override on and renders unlike the user's view, where the Field promised shown already.
  - **Fix.** Narrow only: name the exception in each place ("but a shader model on a material whose Override Material is
    off, which the set-up turns on (scene3d.py, step 4)"); "its Default held overridden" in the check's docstring.
  - **Resolution: done** (2026-11-27).
    - **Test:** docs only, narrowed.
    - **Fix:** HLP-318's exception named in the as_text Field, `_state_said`, `_3d_set_up`, ROADMAP.md:86, item 84's
      row and the test comment; the shown-already check's docstring says "its Default held overridden".
  - Questioned by TST-1012 (2026-11-28)

- [x] **TST-1011 · The new Override check keys its dicts by `str` where the two cases are known** · `tests/test_all_tools/facts/checks.py:1116-1129` · confirmed · found 2026-11-27 by a reviewer (Opus)
  - **Defect.** `shown`, `copies`, `shots`, `models`, `printed` and `after` are keyed by `'new'` and `'held'` only.
  - **Scenario.** A mistyped case key goes unchecked by mypy.
  - **Fix.** `Case = Literal['new', 'held']` and `dict[Case, ...]`.
  - **Resolution: done** (2026-11-27).
    - **Test:** types only; mypy passed.
    - **Fix:** `OverrideCase = Literal['new', 'held']` for the check's dicts.
  - Questioned by TST-1023 (2026-11-28)

- [x] **TST-1012 · Item 85's row still promises every value given back reads as shown already** · `ROADMAP.md` (item 85) · confirmed · follows SRV-286, generation 6 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** "so that a value given back reads as shown already": a tiling or a shader model on a material whose
    Override is off is written and Override turned on (HLP-318, HLP-321). Item 131's row also says "loads it with one
    Reset Scene" and lists the shader model among what isn't controlled yet.
  - **Scenario.** A reader of the Done record expects no load for a value given back.
  - **Fix.** Narrow only: add the exception, or drop the clause; the same for item 131's two phrases.
  - **Resolution: done** (2026-11-28).
    - **Test:** docs only, narrowed.
    - **Fix:** item 85 names the exception; item 131 says when a second Reset Scene comes and drops the shader model
      from "not controlled yet".
  - Questioned by TST-1021 (2026-11-28)

- [x] **TST-1013 · Item 90 doesn't list Designer's material menu, which `graph=` relies on** · `ROADMAP.md` (item 90) · confirmed · follows HLP-312, generation 2 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** `graph=` on a mesh of several materials finds `materialSelectionMenu` by its object name and picks an
    entry with `setActiveAction` and Return (`view3d.py`), measured only on macOS; the Materials menu's "(overridden)"
    mark (`scene3d.MARKS`) too. Item 90 names neither.
  - **Scenario.** The Windows work misses them, and `graph=` on a multi-material asset fails there after 5 s.
  - **Fix.** One clause in item 90's row.
  - **Resolution: done** (2026-11-28).
    - **Test:** docs only.
    - **Fix:** item 90 names the Materials menu's marks and `graph=`'s `materialSelectionMenu`, both measured only on
      macOS.

- [x] **TST-1014 · The 3D view section's rules don't say a material's field is written overridden** · `ROADMAP.md:82-99` · confirmed · follows HLP-321, generation 2 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** **Per material** gives the place and the refusal; the code holds the material overridden for any
    `PER_MATERIAL` field, keeps a material it turned on, on until the put-back (`rendered()`), and says it through
    `OWN_SAID` (a new field without an entry raises `KeyError`). **Put back** says Override is set back after each load,
    with no exception.
  - **Scenario.** Item 82 (real-world scale, a material's field) is built by these rules and inherits Override on
    unknowingly, its missing `OWN_SAID` entry found by a failing test.
  - **Fix.** Add the rule to **Per material** and the exception to **Put back**.
  - **Resolution: done** (2026-11-28).
    - **Test:** docs only.
    - **Fix:** **Per material** adds the field written overridden and said through `OWN_SAID`; **Put back** the exception
      of a material the set-up turned on.

- [x] **TST-1015 · Three branches of a mesh file's framing have no unit test that fails without them** · `mcp_server/designer_helpers/scene3d.py:682-700` · confirmed · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** `framed`'s two `between()` calls (the shot's look before Frame and before the second load), `elif
    changed and linked and ok:` (`:795`) and `yield changed` (`:808`): deleting the first two, or turning `changed` into
    `changes` in the last two, leaves every unit test passing. `changed` differs only for a mesh file shown already with
    `view`, whose one test uses `linked=False` and ignores the result.
  - **Scenario.** Frame runs with Designer's window off screen (HLP-136, HLP-264), or the view stops following the user's
    graph, or STALE is never compared, and nothing fails.
  - **Fix.** A mesh-file row in the `between` test; a `linked=True` case of the view-on-a-shown-file test asserting the
    relink after the second load and `set_up(...) is True`.
  - **Resolution: done** (2026-11-28).
    - **Test:** `test_a_mesh_files_framing_runs_the_shots_look_before_frame_and_before_its_second_load`, and the
      view-on-a-shown-file test parametrized by linked (the relink after the load, `set_up(...) is True`); each of the four
      mutations the entry names made them fail, the code restored after.
    - **Fix:** the tests.

- [x] **TST-1016 · A helper test assumes a POSIX absolute path** · `tests/unit/test_view3d_helpers.py:2182` · confirmed · follows TST-999, generation 2 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** `('/nowhere/mine.obj', r'^no such mesh file: /nowhere/mine\.obj$')`: since Python 3.13, `ntpath.isabs`
    takes a path with one leading slash as not absolute, so on Windows `_set_up_checked` refuses it as "unknown mesh".
  - **Scenario.** A unit run on Windows with Python 3.13 or later fails it (ROADMAP item 18).
  - **Fix.** `str(tmp_path / 'gone.obj')`, matched with `re.escape`.
  - **Resolution: done** (2026-11-28).
    - **Test:** not seen failing here (no Windows).
    - **Fix:** `GONE = os.path.abspath('/nowhere/mine.obj')`, matched with `re.escape`.

- [x] **TST-1017 · Three new tests type a `StateFields` record as `dict[str, object]`** · `tests/unit/test_view3d_helpers.py:2392` · confirmed · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** The `field` parameters at `:2392`, `:2418` and `:2441`, and `OWN_SAID` at `:2382` (inferred
    `dict[str, str]`, production's `dict[StateField, str]`).
  - **Scenario.** A wrong field name goes unchecked by mypy.
  - **Fix.** `'StateFields'` (imported under `TYPE_CHECKING`, beside `Pose`), and `dict[StateField, str]`.
  - **Resolution: done** (2026-11-28).
    - **Test:** types only; mypy passed.
    - **Fix:** `'StateFields'` and `dict['StateField', str]`; a `said_as(field)` helper.

- [x] **TST-1018 · The title check reads box.fbx's title without waiting for its import** · `tests/test_all_tools/facts/checks.py:1283-1291` · confirmed · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** `'_sf_load()\n' + state_file.TITLES`: `_sf_load` waits for the view's restart and the camera's stop,
    where the title names a new file as its import ends (`scene3d.py:64-65`); TITLES' first renderer wait already holds
    for the `Sphere - Rasterizer` the sphere row left.
  - **Scenario.** Under the pool's load, box.fbx's import ends after the camera stops, the first box row reads `Sphere -
    Rasterizer`, and the fact fails at random.
  - **Fix.** Load box.fbx through `state_file.imported`, which waits for the Materials menu, then run TITLES.
  - **Resolution: done** (2026-11-28).
    - **Test:** a race not reproducible on demand; the check passes in the scratch runs.
    - **Fix:** box.fbx loaded through `state_file.imported`, which waits for the import's end, then TITLES; its load in the
      detail.

- [x] **TST-1019 · The import check's four facts still hang on a 3 s settle they don't claim** · `tests/test_all_tools/facts/checks.py:732` · confirmed · follows TST-1008, generation 2 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** `said == imported_as(materials)` requires `SETTLED='True'` for the OBJ, box.fbx, the Samba FBX and its
    reload, where neither the check's docstring nor `state_file.py`'s list claims a settle; TST-1008 kept it there.
  - **Scenario.** In the full run, a loaded machine keeps the Samba FBX's view under 8 samples for 3 s after the import,
    and a fact about the import fails at random.
  - **Fix.** `ended_with` for the four facts; the shot's own "hadn't settled" check stays.
  - **Resolution: done** (2026-11-28).
    - **Test:** a robustness fix; the check passes in the scratch runs.
    - **Fix:** the four facts use `ended_with`; the shot's own "hadn't settled" check stays.

- [x] **TST-1020 · The Override check pins only Override after the put-back, not the model and tiling** · `tests/test_all_tools/facts/checks.py:1113-1194` · confirmed · follows HLP-316, generation 5 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** `after[case]` and the `back` check read the Override menu only; a runner (port 9990) measured the
    user's model and tiling given back too, but nothing pins them, and the unit fake doesn't model the load rule.
  - **Scenario.** A change to the put-back leaves the shot's model in the user's material (it shows once they turn
    Override on), and the check passes.
  - **Fix.** A Save after each call, read with `saved_materials`, expecting the user's model and tiling.
  - **Resolution: done** (2026-11-28).
    - **Test:** with the put-back mutated to reload the shot's own state, Override was still off after each call (the old
      check would pass) and the new read failed; the code restored.
    - **Fix:** a Save after each call, read with `saved_materials`: Default back off with the user's model and tiling.

- [x] **HLP-323 · A material named with `&` matches no name the menu lists, so its mesh is refused as using 0 materials** · `mcp_server/designer_helpers/state3d.py:291` · confirmed · follows HLP-322, generation 2 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** `_used_material` keeps the ids whose file name is in `in_use`; `in_use` comes from `_materials_used`,
    which strips every `&` (`a.text().replace('&', '')`), while `_material_named` gives the file's name with its `&`.
    A material named `A&B` matches none, and nothing is left.
  - **Scenario.** A one-material asset whose material is `Wood&Metal`, with `tiling=2`: refused as "the 3D view's mesh
    uses 0 materials", and as_text says `tiling: not read`; before HLP-322's fix it was taken.
  - **Fix.** KISS: when the menu's names match none, keep every id as before (`used = [...] or ids`).
  - **Resolution: done** (2026-11-28).
    - **Test:** `test_a_material_named_otherwise_in_the_menu_is_found_among_every_one_the_table_maps` (a material `A&amp;B`,
      `in_use=['AB']`) failed with "uses 0 materials", then passed.
    - **Cause:** `_materials_used` drops every `&` of the menu's text, `_material_named` keeps the file's.
    - **Fix:** `used = [...] or ids`: when the menu's names match none, every id counts, as before HLP-322.
  - Questioned by HLP-325 (2026-11-28)

- [x] **HLP-324 · HLP-322's measured fact is worded loosely and recorded twice** · `mcp_server/designer_helpers/state3d.py:30-33` · confirmed · follows HLP-322, generation 2 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** "each holding the material's id alone": each entry holds `material_instance_id` and `asset_material_id`
    (the fixture); what was measured is that the entries name no mesh. The menu's "(unused)" mark on an earlier file's
    materials is recorded both there and in `view3d.py:53-54`.
  - **Scenario.** A maintainer wonders whether `asset_material_id` tells the meshes apart, or corrects one copy only.
  - **Fix.** "its entries naming no mesh"; the menu half in view3d.py (which reads the menu), state3d.py pointing to it.
  - **Resolution: done** (2026-11-28).
    - **Test:** docs only.
    - **Fix:** "its entries naming no mesh"; the "(unused)" fact kept in view3d.py only, state3d.py pointing to it.

- [x] **TST-1021 · Item 131's row overstates when a second Reset Scene comes and what is written** · `ROADMAP.md` (item 131) · confirmed · follows TST-1012, generation 7 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** "(a mesh file the call loads, a second after Designer's Frame: item 84)": `framed` takes no second load
    without camera options or a material's field; "writes in it each field the call sets that the base holds
    otherwise": a tiling or a model on a material with Override off is written anyway.
  - **Scenario.** A reader expects two loads for every mesh file, and no write for a value held already.
  - **Fix.** Narrow only: "(a mesh file the call loads may take a second, after Designer's Frame: item 84)"; drop "that
    the base holds otherwise".
  - **Resolution: done** (2026-11-28).
    - **Test:** docs only, narrowed.
    - **Fix:** "(a mesh file the call loads may take a second, after Designer's Frame: item 84)"; "that the base holds
      otherwise" dropped.

- [x] **TST-1022 · A test comment states the refusal the test no longer expects** · `tests/unit/test_view3d_helpers.py:2380` · confirmed · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** "the reverse, refused as the 3 materials of both files", two lines above `match=r"^the 3D view's mesh
    uses 2 materials \(first, second\)"`.
  - **Scenario.** A reader takes the comment for the refusal expected.
  - **Fix.** "the reverse (REVIEW.md HLP-322)".
  - **Resolution: done** (2026-11-28).
    - **Test:** a comment only.
    - **Fix:** "the reverse (REVIEW.md HLP-322)".

- [x] **TST-1023 · Three live checks key their dicts by `str` where the cases are known** · `tests/test_all_tools/facts/checks.py:995-1019` · confirmed · follows TST-1011, generation 2 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** The new over-another check's `names`, `copies`, `shots`, `printed` and `shot(case: str, ...)` (cases
    `'new'` and `'shown'`); the same at `:855` (`'user'`, `'obj'`, `'top'`, `'samba'`, `'box'`) and `:1070` (`'obj'`,
    `'relink'`), from earlier in the branch.
  - **Scenario.** A mistyped case key goes unchecked by mypy.
  - **Fix.** A `Literal` per check, as `OverrideCase` does.
  - **Resolution: done** (2026-11-28).
    - **Test:** types only; mypy passed.
    - **Fix:** `OverAnotherCase`, `FramedCase`, `EveryMaterialCase`, and `OverObjCase` for the same pattern in the
      Scene-menu-over-a-file check.

- [x] **TST-1024 · An implicit `Any` in the Designer fake** · `tests/unit/test_view3d_helpers.py:967` · confirmed · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** `ids = re.findall(...)` is `list[Any]`.
  - **Scenario.** The fake's ids go unchecked by mypy.
  - **Fix.** `ids: list[str]`, as `state3d.py:288` does.
  - **Resolution: done** (2026-11-28).
    - **Test:** types only.
    - **Fix:** `ids: list[str]`.
  - Questioned by TST-1025 (2026-11-28)

- [x] **HLP-325 · A mesh of two materials, one named with `&`, skips the several-materials refusal** · `mcp_server/designer_helpers/state3d.py:293` · confirmed · follows HLP-323, generation 3 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** `used = [u for u in ids if _material_named(content, u) in in_use] or ids` compares the menu's names,
    `&` dropped, with the file's, `&` kept; HLP-323's fallback covers only no match. For a mesh file of `A&B` and `C`,
    `in_use` is `['AB', 'C']`, `used` is `['C']`, and the call isn't refused; over another file's view, a one-material
    `A&B` matches none and every id counts again (HLP-322's refusal back).
  - **Scenario.** `tiling=2` on such an asset goes into `C` only, said set, part of the mesh unchanged.
  - **Fix.** Compare with `&` dropped on both sides (`_material_named(content, u).replace('&', '') in in_use`); a unit row.
  - **Resolution: done** (2026-11-28).
    - **Test:** `test_a_mesh_file_of_two_materials_one_named_with_an_ampersand_is_refused_as_using_two` ("DID NOT RAISE"
      before) and `test_a_material_named_with_an_ampersand_over_another_mesh_files_view_is_the_one_in_use` ("uses 3
      materials" before), then passing; HLP-323's row now pins only the fallback (a name matching none).
    - **Fix:** `_material_named(content, u).replace('&', '') in in_use`, the fallback kept.

- [x] **TST-1025 · `re.findall` gives `list[Any]` in self-test functions the branch added or changed** · `tests/test_all_tools/facts/checks.py:809` · confirmed · follows TST-1024, generation 2 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** `looks` (`every_material`), `shown` and `linked` (`facts/state_file.py:674-675`, `at_the_render`, whose
    `bool` return is then `Any`), `said` (`editor_panels_and_fit/checks.py:870`) and `shown` (`:2493`).
  - **Scenario.** A changed printed format goes unchecked by mypy.
  - **Fix.** `list[str]`, as `state3d.py:288` does.
  - **Resolution: done** (2026-11-28).
    - **Test:** types only; mypy passed.
    - **Fix:** `list[str]` on the five results; eight more unannotated ones are in functions the branch didn't change.

- [x] **TST-1026 · No unit test guards the Materials menu's mark stripped, or the materials compared by name** · `tests/unit/test_view3d_helpers.py:957-968` · confirmed · follows HLP-322, generation 2 · found 2026-11-28 by a reviewer (Opus)
  - **Defect.** In the fixtures a material in use never carries "(overridden)" and its name always equals its id, so
    `_in_use` returning the menu's names unstripped, or `_used_material` comparing ids with `in_use`, passes every unit
    test; Designer lists box.fbx's material as `Default (overridden)`, id `default`.
  - **Scenario.** A later edit drops either part; `mesh=<box.fbx>, tiling=2` over the OBJ's view is refused as "uses 3
    materials (default, first, second)", and nothing fails.
  - **Fix.** One row: a mesh file mapping `default` beside the stale `first` and `second`, `in_use = ['Default
    (overridden)']`, the tiling expected in `default`.
  - **Resolution: done** (2026-11-28).
    - **Test:** `test_a_tiling_on_a_mesh_file_of_default_over_another_ones_view_goes_in_default_as_the_menu_names_it`
      passes, and failed under each of the two mutations ("uses 3 materials (default, first, second)"), the code restored.
    - **Fix:** the test.

- [x] **TST-1027 · No live check reads the named Override line on a mesh whose materials are all in use** · `tests/test_all_tools/facts/checks.py:1061-1069` · confirmed · found 2026-11-28 by a reviewer (Sonnet)
  - **Defect.** The new `named` expectation reads the line only for a one-material file over the two-material OBJ's
    view (`Override Material: only (on|off)`). The user's example, a mesh of several materials in use (`Body on, Joints
    off`), and a Scene menu's mesh (`Default`) are pinned by unit tests alone, whose fake replaces `_overrides` and
    `_materials_used`.
  - **Scenario.** For a mesh of two materials, Designer's menu gives names `_materials_used` doesn't match (a mark, an
    escape), and the line for the user's own case drops a material, with every check green.
  - **Fix.** In checks that already read as_text, expect the line on a view of the two-material OBJ (`first` and
    `second`, each `on` or `off`, in either order) and on a Scene menu's mesh (`Override Material: Default on` or
    `off`); no new check where one fits.
  - **Resolution: done** (2026-11-28).
    - **Test:** the two-material OBJ's as_text in
      `check_a_mesh_file_shown_already_takes_no_load_and_the_3d_view_as_text_says_its_path` (one Override line, `first`
      and `second` each `on` or `off`, in either order, nothing else) and the Plane's SHOWN= at the render in
      `check_a_tiling_or_a_shader_model_on_a_material_with_override_off_renders_it_overridden` (`Override Material:
      Default on`); with `_shown_said` alone put back as before the change, the OBJ case failed ("Override Material: off,
      off") and the three Plane cases failed; on the code, all passed ("first off, second off").
    - **Fix:** the two expectations, in checks that already read the text; no new check.

- [x] **TST-1028 · No unit test pins the Override line left out when the menu lists no material in use** · `mcp_server/designer_helpers/scene3d.py:392-399` · confirmed · found 2026-11-28 by a reviewer (Sonnet)
  - **Defect.** With `in_use == []` (an import not ended, or a file that doesn't import), the filter keeps nothing and
    the line is left out, where it listed every material before the change and where `_state_said` falls back to every
    material (`or ids`); no test holds that case.
  - **Scenario.** A later change says every material when none are in use, printing an earlier file's unused ones
    again, and the unit suite stays green.
  - **Fix.** One row in `test_override_material_is_said_for_the_materials_the_mesh_uses_alone`: `in_use=[]`, no
    `Override Material:` line.
  - **Resolution: done** (2026-11-28).
    - **Test:** the row "none in use: no line" (`in_use=[]`) of
      `test_override_material_is_said_for_the_materials_the_mesh_uses_alone`, failing against a scratch "every material
      when none are in use" variant of `_shown_said`, passing on the code.
    - **Fix:** the row; the test parametrized by the Override lines it expects.
