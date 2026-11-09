# REVIEW.md: review findings

Findings from code reviews of this repository, kept across several reviews as a file in the project. How many is
the user's choice, most likely the life of a feature branch; the history stays in git for good.

This file is the **memory per branch**. Agents that review and agents that address findings talk through it, as
in a PR review: a finding is raised, then fixed or answered with why not, so the next reviewers know what was
settled and don't raise it again. Once the branch is merged it can be cleaned up. `DECISIONS.md` is the memory for
the whole project.

A new review **appends** its findings to the matching severity section and adds itself to the log; it never removes
or rewrites existing entries. An entry is checked when it is resolved, always with a resolution line that starts
with one of these wordings: done, not a bug, not reproducible, won't fix. Format and rules:
`.claude/skills/project-code-review/` (SKILL.md, TEMPLATE.md).

**Confidence.**

- *Confirmed*: the lead agent read the code and the defect is visible in it, as quoted.
- *Measured*: reading couldn't settle it, and the lead agent's scratch probe in Designer showed it (the entry gives
  the probe and what it measured; the `project-code-review` skill). A finding is one or the other, never a guess.

**IDs.** One prefix per area, numbered on: **PLG** plugin and bridge protocol, **SRV**
`mcp_server/server.py` and `server_tools/`, **HLP** `mcp_server/designer_helpers/`, **INS** installer, uninstaller,
command-line client and example, **TST** tests and docs. A new area gets a new prefix, added here.

**Last used:** PLG-33, SRV-105, HLP-95, INS-27, TST-227.

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
| Medium | 0 | 3 |
| Low-medium | 0 | 8 |
| Low | 0 | 32 |
| **Total** | **0** | **43** |

## Review log

### 2026-11-09: branch `optimize-agents` against `main` (the diff only)

- **How:** three independent reviewers on Opus, reading only (no tests run, no Designer): the guide gates and their
  tests; whether the split of AGENTS.md lost or changed anything; references, skills and rules. The lead agent settled
  every report by reading, plus one scratch probe in a Designer an agent started (`apply_edits` `add` of a `uniform` with
  `$outputsize` `[1024,1024]`: TST-205). Settled as wrong: the gate tracking one server process and not the agent that
  has the guide in context is no defect, as the texts say "called" and `_session` says per process, so it needs no
  probe; a `/mcp` reconnect refusing again is the gate working. Outside the diff: address-review's citation of "Fix issues test
  first", absent from `main` too.
- **Not verified:** none.
- **Resolutions assessed:** none in scope (the file held no entries).
- **Findings:** 10 added: Medium TST-203, TST-204, TST-205; Low-medium SRV-101, TST-206; Low SRV-102, TST-207, TST-208,
  TST-209, TST-210. Merged: SRV-101 (three reviewers), TST-206 and TST-209 (two each). No chain: all generation 1.
- **Suggested order:** TST-204, TST-205 and TST-203 first (an agent acts wrongly or does damage without any error), then
  SRV-101, then the rest; most are one-line doc edits.
- **Checked and found fine:** every tool goes through `_tool` but `get_guide`; the only `gated=False` is
  `cancel_designer_job`; `scripting=True` is on exactly the two tools taking caller code; every other MCP session in the
  self-test reads the guide first or only cancels; removing `_nesting` loses nothing (only `set_link_display` nests,
  under the same gate); the flags only go from False to True; the new tests would fail without what they guard; the
  removed reminder tests guarded behaviour that no longer exists; the diff in `plugin/` and `designer_helpers/` is
  comments and docstrings only; DECISIONS.md changed in paths only; skill and rule frontmatter is valid; apart from
  TST-207's and TST-210's wording, the moved text is verbatim.

### 2026-11-09: branch `optimize-agents` against `main` (the diff only), second review

- **How:** three independent reviewers on Opus, reading only (no tests run, no Designer): the gates and the `$outputsize`
  refusal; what the moved documents lost or changed; skills, rules and the tests that read the docs. The lead agent
  settled every report by reading, plus two scratch probes through a fresh server in a Designer an agent started, closed
  afterwards: numbers sent as strings, a graph input bound to `$outputsize`, `size_log2` above 13 and a 16384 px bitmap.
  Settled as wrong: "13 may refuse a bitmap's legitimate 14", as a linked 16384 px image reads (14, 14) and computes
  8192x8192; TST-209's "no test can fail on one" being imprecise, as its four comments are fixed and a guard on their
  old wording would pin names that no longer exist.
- **Not verified:** whether 13 is also the ceiling on another compute engine. The probes ran on this Designer's active
  engine, and the `sd` API has no call to switch it (only a colour management engine). What would check it: the fact
  script run with the engine switched by hand in the UI.
- **Resolutions assessed:** all 11. SRV-101 and TST-209 hold; TST-211 holds. Questioned: TST-203 and TST-210 (TST-215),
  TST-204 (TST-212), TST-205 (HLP-83, HLP-84, HLP-85, TST-213, TST-214), SRV-102 (SRV-103), TST-206 (TST-216), TST-207
  (TST-218), TST-208 (TST-217).
- **Findings:** 13 added: Low-medium HLP-83, HLP-84, TST-212, TST-213; Low SRV-103, HLP-85, TST-214 to TST-220. Merged:
  TST-215's heading, TST-216 and TST-218 (two reviewers each); HLP-84 (two reviewers). Longest chain: generation 2, and
  none reaches generation 3. Note added under TST-205 for a leftover in its check.
- **Suggested order:** HLP-83, HLP-84 and HLP-85 together (one limit, shared by every path that sets a size), then
  TST-212 and TST-213, then the rest; most are one-line doc edits. TST-217's change to DECISIONS.md's introduction goes
  beyond names and paths, so it needs the user's word.
- **Checked and found fine:** gate coverage and logic (flags set only after the guide is read, an unknown part sets none,
  `get_guide('scripting')` alone doesn't open the core gate); the split at the one `# Scripting` heading; the refusal runs
  before anything is set, leaves no node behind and is reached by `expose`'s `default` (measured); `sweep_param`'s restore
  doesn't go through it; `live-check`'s named functions, needs and exit codes exist as stated; the docs-only command
  covers every test reading a doc; the size caps measure what they say; every "below" and section reference in the core
  resolves; maintainer facts all have a home in their modules.

### 2026-11-09: branch `optimize-agents` against `main` (the diff only), third review

- **How:** three independent reviewers on Opus, reading only: the code; the moved documents; skills, rules and the tests
  that read the docs. The user's two full suites ran alongside: the unit suite passed (967), and the live self-test
  passed 558 of 559, its one failure being the installed plugin one comment behind the repo (the citation this branch
  repointed), cured by `install.py` and seen passing in a run of the bridge category. The lead agent settled every report
  by reading, plus scratch probes through a fresh server in a Designer an agent started, after the suite ended, closed
  afterwards. Settled as wrong: "instance nodes inherit from the graph, not their input", as a fresh hbao and blur_hq are
  relative to input and compute 512 px from a 512 px input on a 2048 px graph (only a Pixel Processor doesn't: TST-221);
  "two computes differ by 2/65535" needing the core, as `node_stats` prints four decimals; "a frozen thread reads as idle"
  needing the core, as `designer_status`' listing waits on that thread; AGENTS.md's table row below TST-220's omitting
  an agent writing `sd` code, as the code tools are tools. Dropped as hypothetical: `DOC_TESTS` not seeing a test reading
  only a skill, as no such test exists and the pattern is on `main` too.
- **Not verified:** none new; the second review's note on another compute engine stands.
- **Resolutions assessed:** the 13 of the second review. Hold: HLP-83, TST-212, TST-214, TST-215, TST-216, TST-217,
  TST-218, TST-220. Questioned: HLP-84 (HLP-87), HLP-85 (HLP-86, HLP-89), SRV-103 (SRV-104), TST-213 (TST-221), TST-219
  (TST-224). Earlier ones questioned again: TST-205 (HLP-88), TST-203 (TST-222), TST-210 (TST-226).
- **Findings:** 11 added: Low-medium HLP-86; Low SRV-104, HLP-87, HLP-88, HLP-89, TST-221 to TST-226. Merged: HLP-86 (two
  reviewers). Longest chain still growing: generation 3 (TST-205 → HLP-85 → HLP-86, HLP-89; SRV-102 → SRV-103 → SRV-104;
  TST-205 → HLP-84 → HLP-87; TST-205 → TST-213 → TST-221, narrowed only). Note: the live gate check leaves
  `builtins._mcp_gate_ran = 0` in the Designer it uses, which no later check reads.
- **Suggested order:** HLP-86 first (the refusal's advice reproduces what it refuses), then HLP-87, HLP-88, HLP-89 and
  SRV-104 with it, then the docs. A fix to the code means both suites again before merging.
- **Checked and found fine:** every call of `_make_value` and every other place that sets a size; the helper parts'
  new names; no legitimate value refused; `mcp_selftest_sizes` isn't opened in the editor and later scans filter by file or
  identifier; every citation repointed in the diff resolves; `REVIEW.md`'s counters and table; both full suites apart from
  the plugin copy above.

### 2026-11-09: branch `optimize-agents` against `main` (the diff only, working tree), fourth review

- **How:** three independent reviewers on Opus, reading only, on the uncommitted fixes of the third review too. The lead
  agent settled every report by reading, plus one scratch probe through a fresh server in a Designer an agent started,
  closed afterwards. Settled as wrong: an FX-Map following the graph, as a fresh `fxmaps` is relative to input like every
  atomic node with an image input but the Pixel Processor (the Value Processor is too, and computes no image); the two
  refusal texts' unmeasured clauses, all measured true: at Absolute 0 computes 1 px, and on a relative-to-input levels fed
  512 px an offset of 0 computes 512, 1 gives 1024, -1 gives 256 and 5 gives 8192. Dropped under DECISIONS.md, Low-value
  findings: the crash-dump sentence naming no folder for the user's Designer (generation 3, docs). Outside the diff: a
  refused `add` on a saved package leaves it modified (measured), the path of every bad parameter of `add`, which this
  branch didn't change.
- **Not verified:** none new; the second review's note on another compute engine stands.
- **Resolutions assessed:** the 11 of the third review. Hold: HLP-87, HLP-88, TST-222 to TST-226. Questioned: HLP-86
  (HLP-90), HLP-89 (HLP-91, HLP-92). Earlier one questioned again: TST-220 (TST-227). Notes added under SRV-104 and TST-221.
- **Findings:** 4 added: Low-medium HLP-90; Low HLP-91, HLP-92, TST-227. No duplicates. Longest chain still growing:
  generation 4 (TST-205 → HLP-85 → HLP-86 → HLP-90, and HLP-89 → HLP-91, HLP-92), in the tools' code.
- **Suggested order:** HLP-90 first, then TST-227; for HLP-91 and HLP-92 narrowing the claim is enough (the reach of both
  is a graph a person built by hand).
- **Checked and found fine:** `_agent_guide`'s heading search gives the core and scripting byte for byte as before; every
  refusal comes before any change; every caller of `_make_value`; the moved script's callers; `REVIEW.md`'s counters,
  generations and "Questioned by" lines.

### 2026-11-09: branch `optimize-agents` against `main` (the diff only, working tree), fifth review

- **How:** three independent reviewers on Opus, reading only, on the uncommitted fixes of the third and fourth reviews
  too: the size refusal's code; the guide split, the gates and the moved documents; the tests, skills and rules. The
  lead agent settled every report by reading, plus one scratch probe through a fresh server in a Designer an agent
  started, closed afterwards. Settled as wrong: `getReferencedResource()` raising on an instance whose package is gone,
  as it returns `None` (measured: a `.sbs` whose referenced package was renamed away loads, `describe_graph` works, `set`
  of a `$` parameter works, and a parameter the missing graph defined is "no parameter"). Dropped under DECISIONS.md,
  Low-value findings: the sentence on what generators and filters inherit having no live check (generation 4, docs), and
  the clause "closing it does nothing" lost from the hidden main window's note, which changes nothing anyone does.
- **Not verified:** none new; the second review's note on another compute engine stands.
- **Resolutions assessed:** the 4 of the fourth review. Holds: TST-227. Each fix holds for its own case, and its neighbours
  are questioned: HLP-90 (HLP-94), HLP-91 (HLP-93), HLP-92 (HLP-95). Earlier ones assessed: TST-221, TST-222 and TST-226
  hold; SRV-104 questioned again (SRV-105).
- **Findings:** 4 added, all Low: SRV-105, HLP-93, HLP-94, HLP-95. Merged: HLP-94 (two reviewers). Longest chain still
  growing: generation 5 (TST-205 → HLP-85 → HLP-86 → HLP-90 → HLP-94, and HLP-89 → HLP-91 → HLP-93, HLP-92 → HLP-95), in
  the tools' code. HLP-93, HLP-94 and HLP-95 need a graph or function built outside the tools. Note: in
  `check_outputsize_above_log2_is_refused` the default `says='log2 of the size'` also matches the offset's wording; the
  negative-value siblings on the same paths still tell the two apart.
- **Suggested order:** HLP-93's `expose` half first (the one silent 8192 px left, a single call), then HLP-94; HLP-95, SRV-105
  and HLP-93's outward half can be settled by narrowing the text. A fix to the code means both suites again before merging.
- **Checked and found fine:** the joined parts' name order and imports; a `$` or non-int2 property and a non-instance node
  return before the guard reads anything; `_graph_parameter_reads` on a never-saved package; every refusal before any
  change; `_agent_guide` against the real file (one heading, no fence, no CR) and the gates' every path; every sentence on
  `$outputsize` in the core against the helpers; main's `AGENTS.md` compared sentence by sentence; the moved script's
  callers; every graph of the size check left for `CLEAN` and no later category disturbed by them; every name the skills and
  rules cite.

---

## High

## Medium-high

## Medium

- [x] **TST-203 · The inheritance numbers left the guide while it still recommends hand-editing the .sbs** · `mcp_server/GUIDE.md:272-281` · confirmed · found 2026-11-09
  - **Defect.** The scripting part says of the file-level edit pattern "Use it for other things the API can't do: ... edit the .sbs XML", but the fact that the API's and the file's numbers differ ("API ... RelativeToInput 0, RelativeToParent 1, Absolute 2. A .sbs `<relativeTo>`: 0 absolute, 1 relative to parent, 2 relative to input") now sits only in a comment in `server_tools/snapshots.py:242-245`.
  - **Scenario.** A scripting agent uses the pattern to make a parameter Absolute and writes `<relativeTo v="2"/>`, the API's number for Absolute. The file reads 2 as relative to input, so the parameter silently inherits, with no error.
  - **Fix.** Put the one-line fact back in the scripting part, next to the pattern, and drop the `SDPropertyInheritanceMethod` case from `test_what_only_a_maintainer_needs_lives_with_the_code` in `tests/unit/test_guide.py`.
  - **Resolution: done.** **Test:** `test_the_file_level_pattern_comes_with_the_inheritance_numbers`, failed as the scripting part had no numbers. **Cause:** step 3 of the plan moved them as maintainer-only, though the file-level pattern stayed. **Fix:** the bullet is back in the scripting part, after Portals; the case pinning it out of the guide is gone. **Also covered:** the other facts moved out of the guide: none is needed to hand-edit a file.
  - Questioned by TST-215 (2026-11-09).
  - Questioned by TST-222 (2026-11-09).

- [x] **TST-204 · AGENTS.md's pointer to the safety rules doesn't cover work on the bridge, the token or the plugin** · `AGENTS.md:3-5` · confirmed · found 2026-11-09
  - **Defect.** The rules that were auto-loaded ("Never print, log or send the bridge token", "Never hot-reload" the plugin, "Never trigger Undo" on the user's graphs) are now behind "read it before writing code that runs inside Designer", while `AGENTS.md:144` names the token file with no warning.
  - **Scenario.** A contributor debugging the bridge or `client/sd_run.py` works through Bash, never calls a gated tool, and writes nothing that "runs inside Designer" by their reading: they may `cat` or log the token, or send `importlib.reload` through `sd_run.py -c` to the user's Designer.
  - **Fix.** Widen the pointer: read the guide's rules before touching the bridge, the token or the plugin, or running anything against Designer.
  - **Resolution: done.** **Test:** `test_agents_md_asks_for_the_rules_before_touching_the_bridge`, failed on the old sentence. **Cause:** the pointer described only code running inside Designer. **Fix:** AGENTS.md now asks for the rules before touching the bridge, the token or the plugin, or running anything against Designer. **Also covered:** the token file named at AGENTS.md's plugin bullet: the pointer at the top covers it, and the fact stays in one place.
  - Questioned by TST-212 (2026-11-09).

- [x] **TST-205 · Nothing a tools-only agent reads says `$outputsize` is log2 or that positions are node centres** · `mcp_server/GUIDE.md:240,251`, `mcp_server/server_tools/edits.py:48-56` · measured · found 2026-11-09
  - **Defect.** "**Graph size** is log2 (`$outputsize` 11 = 2048)" and "Node positions are node **centres**" moved to the scripting part, which an agent using only the tools is told it can skip, and the `apply_edits` `set` text and the `position` fields state neither.
  - **Scenario.** Probe: an `apply_edits` `add` of a `uniform` with `$outputsize` `[1024,1024]` is accepted with no warning, and `node_stats` reports 8192x8192 RGBA8. An agent thinking in pixels silently builds the largest texture Designer makes; nodes placed by their top-left corner land half a node off.
  - **Fix.** Move both facts to the core's First sd pitfalls, or state them in the `set` and `position` texts (one place), and consider refusing an `$outputsize` value that can't be a log2 size.
  - **Resolution: done.** **Test:** live `safeguards.check_outputsize_above_log2_is_refused` failed in its scratch run (add, set, one axis and `sweep_param` all accepted; 32x8192 after them), and `test_a_tools_only_agent_is_told_the_units`. **Measured:** `facts.check_the_largest_output_size`: 13, 14 and 15 all compute 8192 px, so 13 is the ceiling. **Cause:** the units were only in the scripting part, and nothing checked the value. **Fix:** at the user's choice, docs plus a refusal: `_make_value` refuses an `$outputsize` above 13, on any axis; the core's First sd pitfalls and the `apply_edits` text state log2 and centres. **Also covered:** `_make_value` is the one path of `add`, `set` and `sweep_param`, graph or node; `create_graph`, `set_graph_size` and `render_sbs` take a parameter named `size_log2`, so the unit is stated and they don't have this defect.
  - Questioned by HLP-83, HLP-84, HLP-85, TST-213 and TST-214 (2026-11-09).
  - Note (2026-11-09): `check_outputsize_above_log2_is_refused` adds its first node outside the `try`, so if that `add` isn't refused an 8192 px uniform stays in the self-test graph. No later check depends on it.
  - Questioned by HLP-88 (2026-11-09).

## Low-medium

- [x] **SRV-101 · The texts describing the guide still say one call returns all of it** · `mcp_server/server_tools/core.py:75-77`, `mcp_server/server_tools/guide.py:12,25-27`, `mcp_server/GUIDE.md:63-64`, `AGENTS.md:3-5`, `README.md:12-14` · confirmed · found 2026-11-09
  - **Defect.** `INSTRUCTIONS` says `get_guide()` "is the full guide, with the rules ... and the sd API pitfalls"; its result ends "End of the Designer guide (%d characters, complete)"; AGENTS.md lists the `sd` API as served by `get_guide()`. Also: the docstring's "the other tools refuse" and GUIDE.md's "until then they refuse", right after `cancel_designer_job`, read as if the one tool that never refuses did; and in README "the server sends it to the agent automatically" now has AGENTS.md as its antecedent.
  - **Scenario.** A contributor writing helpers calls `get_guide()`, sees "complete" and misses the sd API part: the gate on the code tools doesn't cover helper edits. An agent trying to stop a runaway script reads that cancel refuses.
  - **Fix.** "It is the core of the guide ... and the first sd pitfalls"; "End of the core of the Designer guide"; "every tool but cancel_designer_job refuses"; "those two refuse"; say which call serves the sd API part; in README, "the server serves the guide through `get_guide`".
  - **Resolution: done.** **Test:** `test_the_texts_say_which_part_of_the_guide_a_call_returns` and `test_get_guide_returns_the_core_of_the_guide_file`, failed on the old texts. **Cause:** the texts were written when one call returned everything. **Fix:** `INSTRUCTIONS`, the result's last line, the docstring, GUIDE.md, AGENTS.md and README now say which part, and name the exception for `cancel_designer_job`. **Also covered:** every mention of `get_guide` in AGENTS.md, GUIDE.md, README.md and the tool descriptions.

- [x] **TST-206 · The typing rules for all Python are only in a skill that live-check work reaches** · `.claude/skills/live-check/SKILL.md:83-96` · confirmed · found 2026-11-09
  - **Defect.** "every name in an annotation there must exist at runtime (... never only under `if TYPE_CHECKING:`)", "no `from __future__ import annotations`" for the helpers and the plugin, and the opposite rule for the standalone scripts, moved to the skill; AGENTS.md and `.claude/rules/` don't mention them, and no unit test names `TYPE_CHECKING` or `__future__`.
  - **Scenario.** A contributor editing a helper imports a type only under `TYPE_CHECKING`. By the guide's own statement that Designer's Python 3.13 evaluates annotations when a `def` runs, that raises `NameError` in the joined helper script, which every helper-backed tool sends.
  - **Fix.** One line in AGENTS.md, Running the tests, or a pointer from `.claude/rules/changing-tools.md`.
  - **Resolution: done.** **Test:** `test_the_typing_rules_are_where_every_python_change_sees_them`, failed as AGENTS.md had neither rule. **Cause:** they went with The suites into the skill. **Fix:** the rules moved to AGENTS.md, Running the tests; the skill points there. **Also covered:** the rest of The suites concerns the suites themselves.
  - Questioned by TST-216 (2026-11-09).

- [x] **HLP-83 · Numbers sent as strings pass the `$outputsize` refusal** · follows TST-205, generation 2 · `mcp_server/designer_helpers/edits.py:98` · measured · found 2026-11-09
  - **Defect.** The refusal tests `isinstance(v, (int, float)) and v > 13`, but `as_int` then converts strings with `int(v)`, so a string gets past the check and becomes the number.
  - **Scenario.** Probe: `apply_edits` `set` of a uniform's `$outputsize` to `['1024', '1024']` is accepted (`(0, 0) -> (1024, 1024)`) and `node_stats` reports 8192x8192, the silent result TST-205 closed.
  - **Fix.** Compare after the conversion, so `as_int(v) > 13` for each value, and add the string case to `check_outputsize_above_log2_is_refused`.
  - **Resolution: done.** **Test:** `set refuses numbers sent as strings` in `safeguards.check_outputsize_above_log2_is_refused`, failed in its scratch run (`(5, 5) -> (1024, 1024)`). **Cause:** the check looked at the raw value, before `as_int` converts it. **Fix:** `_make_value` checks `as_int` of each value, after the length checks. **Also covered:** a string on a bound input (HLP-85's check).

- [x] **HLP-84 · `create_graph` and `set_graph_size` report sizes Designer doesn't compute** · follows TST-205, generation 2 · `mcp_server/designer_helpers/editor.py:312-313`, `mcp_server/designer_helpers/graph_inputs.py:441-447` · measured · found 2026-11-09
  - **Defect.** Both accept any `size_log2` and print `2**size_log2` (`print('size: fixed %d px' % 2**size_log2)`), though the fact TST-205 added says nothing above 13 computes larger. TST-205's **Also covered** cleared them because the unit is in the name, which doesn't touch the ceiling.
  - **Scenario.** Probe: `create_graph(size_log2=14)` prints "16384 px" and a uniform in it computes 8192x8192; `set_graph_size(14, overridable=False)` prints "fixed 16384 px", and with `overridable=True` "default 16384 px", both computing 8192. An agent tells the user the material is 16K. `set_graph_size(1024, overridable=False)` prints a 309-digit number with no error.
  - **Fix.** Refuse a `size_log2` above 13 in both tools, with one limit shared with `_make_value`; say so in their docstrings.
  - **Resolution: done.** **Test:** `create_graph refuses 14` and `-1`, `set_graph_size refuses 14` and `-1`, both `overridable` values, and `a refused set_graph_size leaves the graph's size`, failed in the scratch run ("created graph ... (16384 px)"; -1 printed "0 px"), and `test_the_size_tools_state_the_largest_size`. **Cause:** neither tool checked the range and both print `2**size_log2`. **Fix:** `_refuse_bad_size_log2` (`designer_helpers/core.py`) refuses outside 0 to 13 before anything changes, one limit shared with `_make_value`; both docstrings and the core state it. **Also covered:** a negative value, which printed 0 px or raised a `TypeError`. `render_sbs`' `size_log2` goes to `sbsrender`, not Designer: not measured, not changed, and it reports no size of its own.
  - Questioned by HLP-87 (2026-11-09).

- [x] **TST-212 · AGENTS.md's pointer to the rules doesn't reach the hot-reload rule** · follows TST-204, generation 2 · `AGENTS.md:5`, `mcp_server/GUIDE.md:91-92` · confirmed · found 2026-11-09
  - **Defect.** AGENTS.md says "Read its rules before touching the bridge, the token or the plugin", and the guide uses "the rules" for its section `## Rules that protect the user's work`, but "**Never hot-reload the sd_claude_bridge_kve plugin**" is in `## Undo, timeouts, plugin lifecycle`.
  - **Scenario.** A contributor debugging the plugin reads the Rules section as told, finds nothing about reloading, and sends `importlib.reload` through `client/sd_run.py` to the user's Designer, breaking the bridge until the user restarts it.
  - **Fix.** Move the hot-reload bullet into `## Rules that protect the user's work`, leaving no copy behind.
  - **Resolution: done.** **Test:** `test_the_hot_reload_rule_is_among_the_rules`, failed as the bullet was in another section. **Cause:** the pointer named the rules, and this one sat under Undo. **Fix:** the bullet moved to `## Rules that protect the user's work`; the section it left is now `## Undo and timeouts`, as no plugin lifecycle remained there. **Also covered:** the other rules TST-204 listed (token, Undo) were already in that section.

- [x] **TST-213 · The core says `$outputsize` is log2 of the size without saying that holds only at Absolute** · follows TST-205, generation 2 · `mcp_server/GUIDE.md:117-118,245-247` · measured · found 2026-11-09
  - **Defect.** The core has "`$outputsize` is log2 of the size in pixels (11 is 2048 px...)", while "relative to parent or input, `$outputsize` is a log2 offset" and "Generators inherit the graph size; filters inherit from their input" stayed in the scripting part, which a tools-only agent is told it can skip.
  - **Scenario.** Probe, on a 512 px graph: `expose` of a uniform's `$outputsize` with `default` `[5, 5]`, read as 32 px, computes 8192x8192; an input of `[1, 1]` computes 1024, not 2 px. `describe_graph` after `set_graph_size(11)` prints `$outputsize (log2): 0 x 0` for a graph computing 2048 px, which reads as 1 px.
  - **Fix.** Say it in the core once: log2 of the size at Absolute (what `set` makes it), an offset while inherited; generators follow the graph, filters their input. Take it out of the scripting part.
  - **Resolution: done.** **Test:** `test_the_core_says_when_outputsize_is_an_offset`, failed on the old sentence, and live `a bound input is an offset from the graph` and `an overridable graph shows an offset of 0`. **Cause:** the split moved the conditions to the scripting part and only the unit came back. **Fix:** the core states Absolute, the offset and what generators and filters inherit; the scripting part no longer does. **Also covered:** the `apply_edits` text concerns `set`, which makes it Absolute, so it stays true.
  - Questioned by TST-221 (2026-11-09).

- [x] **HLP-86 · The size refusal gives the wrong unit where the value is an offset, and following it reproduces the silent 8192 px** · follows HLP-85, generation 3 · `mcp_server/designer_helpers/core.py:220`, `mcp_server/designer_helpers/graph_inputs.py:349-356`, `mcp_server/designer_helpers/edits.py:124` · measured · found 2026-11-09
  - **Defect.** A bound input and `expose`'s `default` on an inherited `$outputsize` are offsets, but the refusal always says "log2 of the size in pixels (11 is 2048 px...)".
  - **Scenario.** Probe, 512 px graph, a uniform's `$outputsize` exposed as `p_in`: `set` of `[1024, 1024]` is refused with that text; an agent obeying it sends `[11, 11]`, which is accepted and computes 8192x8192 with no error, where it wanted 2048.
  - **Fix.** On these two paths say the value is added to the graph's log2 size while the node inherits (0 keeps the size), and assert the wording in `check_outputsize_above_log2_is_refused`.
  - **Resolution: done.** **Test:** in `safeguards.check_outputsize_above_log2_is_refused`, `says` for a bound input and `expose`'s default, failed in its scratch run on the "log2 of the size" text. **Cause:** one wording for a value that is sometimes an offset. **Fix:** `_refuse_bad_size(..., inherited)` picks between the size's and the offset's wording, from the inheritance of each `$outputsize` the input binds (a new `_inherits_size`) and of `expose`'s node; `_make_value` takes `inherited`. **Also covered:** a node at Absolute bound to an input keeps the size's wording and lower limit (live, `a size input refuses...`); a larger offset that is still below 13 stays accepted, as what it computes depends on the inherited size.
  - Questioned by HLP-90 (2026-11-09).

- [x] **HLP-90 · The refusal for a driven `$outputsize` sends the agent to a graph input without saying it is an offset** · follows HLP-86, generation 4 · `mcp_server/designer_helpers/edits.py:159`, `mcp_server/designer_helpers/sweep.py:45`, `mcp_server/GUIDE.md:120-121` · confirmed · found 2026-11-09
  - **Defect.** HLP-86 gave the offset wording only to values above 13; the earlier "is driven by %s; set that instead" names the input with no unit, and no tool shows a node's inheritance.
  - **Scenario.** On a 512 px graph, an agent wanting 2048 px sends `set` of an exposed uniform's `$outputsize` `[11, 11]`, is sent to the input, sets it to `[11, 11]`, and gets 8192x8192 with no error (HLP-86's probe).
  - **Fix.** In both refusals, for an inherited `$outputsize`, add that the input is a log2 offset (0 keeps the size), and say in the core's bullet that a graph input bound to it is too.
  - **Resolution: done.** **Test:** `set on a driven size says its input is an offset` and its `sweep_param` twin, failed in the scratch run on the old text, and `test_the_core_says_when_outputsize_is_an_offset`. **Cause:** HLP-86 changed only the refusal above 13, and this one comes first. **Fix:** both refusals add, through `_offset_note`, that the input is a log2 offset while the node inherits; the core says a graph input bound to it is one too. **Also covered:** a node at Absolute isn't called an offset (live); a function that isn't a plain binding keeps its own refusal.
  - Questioned by HLP-94 (2026-11-09).

## Low

- [x] **SRV-102 · A guide that can't be read still opens the gate and reports itself complete** · `mcp_server/server_tools/core.py:57-65`, `mcp_server/server_tools/guide.py:17-27` · confirmed · found 2026-11-09
  - **Defect.** `_agent_guide` returns `'GUIDE.md not found in mcp_server/.'` on `OSError`, and `get_guide` then sets the flag and appends "End of the Designer guide (%d characters, complete)".
  - **Scenario.** With `mcp_server/GUIDE.md` missing or unreadable, `get_guide()` says 35 characters are complete, asks the agent to confirm a reading that didn't happen, and every tool opens with no rule read.
  - **Fix.** Raise `ToolError` from `get_guide` and leave the flags alone, saying to restore the file; only the resource falls back to a message. A unit test with `GUIDE_MD` patched to a missing path.
  - **Resolution: done.** **Test:** `test_a_guide_that_cant_be_read_is_refused_and_opens_nothing` (both parts) and `test_a_guide_without_its_scripting_part_opens_nothing`, failed as the flags were set. **Cause:** `_agent_guide` returned an error as if it were the guide. **Fix:** it raises `ToolError` saying to restore the file, before any flag is set; the resource alone falls back to the message. **Also covered:** a file without the Scripting heading, which served 0 characters as complete.
  - Questioned by SRV-103 (2026-11-09).

- [x] **TST-207 · Scopes of what was measured were dropped with the evidence, so claims say more than the checks show** · `mcp_server/GUIDE.md:167-168,216-218,227-228,248-249`, `mcp_server/designer_helpers/graph_inputs.py:236` · confirmed · found 2026-11-09
  - **Defect.** "float4 and enum parameters" lost that an enum on an instance node was never measured; "relative to parent on an instance node" lost "`$outputsize` measured" (`facts.py:196` checks only that one); "**Changing a parameter's inheritance doesn't keep its value**" lost "measured on a node's `$outputsize` and the graph's `$randomseed`"; "caused no crash in five tries" became "caused no crash". `graph_inputs.py:236` still cites GUIDE.md for "all six", which GUIDE.md no longer states.
  - **Scenario.** A contributor relies on one of these for a parameter nobody measured and skips the measurement AGENTS.md asks for.
  - **Fix.** Keep each short scope; a scope isn't evidence. Have `graph_inputs.py:236` cite `facts/function_states.py`.
  - **Resolution: done.** **Test:** `test_a_claim_keeps_the_scope_it_was_measured_on` (four cases) and `test_what_a_helper_cites_for_a_measurement_states_it`, failed on the shortened text. **Cause:** step 4 treated scopes as evidence. **Fix:** the four scopes are back; `graph_inputs.py` cites the script that measures it. **Also covered:** the other notes stripped in step 4 (pixel values, stress counts, "the self-test checks") state no scope.
  - Questioned by TST-218 (2026-11-09).

- [x] **TST-208 · address-review sends every measured Designer fact to GUIDE.md, against AGENTS.md's new table row** · `.claude/skills/address-review/SKILL.md:48,79` · confirmed · found 2026-11-09
  - **Defect.** "What it measures goes in GUIDE.md" and "record the measured table in GUIDE.md", while `AGENTS.md`'s table now sends what only a tool's maintainer needs to the module's docstring.
  - **Scenario.** A fixer measures how `quit_designer` behaves internally and writes it in GUIDE.md, which every Designer session pays for, undoing the split.
  - **Fix.** "In GUIDE.md or the module's docstring, as AGENTS.md's table says", at both places.
  - **Resolution: done.** **Test:** `test_address_review_sends_a_measured_fact_where_the_table_says`, failed with no such wording. **Cause:** the skill predates the table row. **Fix:** both places now defer to AGENTS.md's table. **Also covered:** step 5 of the skill already did.
  - Questioned by TST-217 (2026-11-09).

- [x] **TST-209 · Four comments still cite AGENTS.md for rules that moved to the live-check skill** · `tests/unit/test_selftest_safety.py:97,249`, `tests/unit/test_selftest_summary.py:162`, `tests/test_all_tools/common.py:386` · confirmed · found 2026-11-09
  - **Defect.** They cite "(AGENTS.md)" or "(AGENTS.md, the self-test)" for the library-load, `dedent`, `check_` and `designer_scripts` rules; AGENTS.md has neither "dedent" nor "designer_scripts".
  - **Scenario.** Someone following the citation finds nothing there.
  - **Fix.** "(the live-check skill)" at all four, as `lifecycle.py` and `test_selftest_alone.py` already say.
  - **Resolution: done.** **Test:** none, as these are comments only and no test can fail on one. **Cause:** the rules moved to the skill after these were last repointed. **Fix:** all four cite the live-check skill. **Also covered:** a search for AGENTS.md citations of `dedent`, `designer_scripts` and the `check_` rule.

- [x] **TST-210 · Small text defects left by the moves** · `mcp_server/GUIDE.md:112-113,301-304`, `mcp_server/server_tools/lifecycle.py:30-31` · confirmed · found 2026-11-09
  - **Defect.** "in its home" no longer resolves, as the core's Several Designers never says "home"; `## First sd pitfalls` has no blank line before it; lifecycle's "The plugin's status answer comes from another thread: measured with a timer slot sleeping in a loop." lost what was measured; GUIDE's Quitting repeats "ends only a Designer an agent started" from the rules, and the socket explanation is both in lifecycle's docstring and at `_own_temp`.
  - **Scenario.** An agent looking for a crash dump of a Designer it started has no folder to look in.
  - **Fix.** Name the folder or say "its own folder (Several Designers)"; add the blank line; restore "a main thread frozen outside a job reads as idle" in the docstring; keep each fact once.
  - **Resolution: done.** **Test:** `test_small_text_defects_stay_fixed`, failed on the old text. **Cause:** leftovers of the moves. **Fix:** the crash-dump folder is named, the blank line is back, lifecycle's docstring says what was measured, Quitting no longer repeats the rule, and `_own_temp` points to the module docstring. **Also covered:** other "below" and section references, checked in the review.
  - Questioned by TST-215 (2026-11-09).
  - Questioned by TST-226 (2026-11-09).

- [x] **TST-211 · The gate broke a unit test that runs the server in a subprocess** · `tests/unit/test_lifecycle_env.py:281` · confirmed · found 2026-11-09
  - **Defect.** `test_scripts_and_tool_output_are_read_as_utf8_whatever_the_locale` calls `run_designer_script` in a fresh process, where conftest's fixture doesn't mark the guide as read, so the tool refused.
  - **Scenario.** The final unit run fails on a test unrelated to the guide; it wasn't in the tests run for the gate.
  - **Fix.** Mark both parts read in that subprocess.
  - **Resolution: done.** **Test:** the test itself, failing with the refusal while these findings were addressed. **Cause:** the gate changed what a tool does before the guide is read, and this is the one test with session state of its own. **Fix:** it marks both parts read. **Also covered:** every `import server` in a subprocess and every `call_tool` under `tests/unit`: no other runs a gated tool.

- [x] **SRV-103 · An empty guide file still opens the gate and reports itself complete** · follows SRV-102, generation 2 · `mcp_server/server_tools/core.py:68-70`, `mcp_server/server_tools/guide.py:24-28` · confirmed · found 2026-11-09
  - **Defect.** `core, heading, scripting = text.partition('\n# Scripting')` followed by `return core.rstrip('\n') + '\n'` serves a blank core as a guide, so SRV-102's cause, a guide not read counting as read, survives for this input.
  - **Scenario.** With a 0-byte or blank `mcp_server/GUIDE.md` (an interrupted write, a bad merge), `get_guide()` says "1 characters, complete" and every tool opens with no rule read.
  - **Fix.** `if not core.strip(): raise ToolError(restore % 'is empty')`, with a unit test next to `test_a_guide_without_its_scripting_part_opens_nothing`.
  - **Resolution: done.** **Test:** `test_a_guide_without_its_core_opens_nothing` (empty, blank, only a scripting part), failed as the flag was set. **Cause:** only a missing file or heading was treated as no guide. **Fix:** `_agent_guide` raises `ToolError` when the part before the Scripting heading is blank, for the resource too, which only says so. **Also covered:** `get_guide('scripting')` on those files, refused by the same check.
  - Questioned by SRV-104 (2026-11-09).

- [x] **HLP-85 · A graph input bound to `$outputsize` takes any value** · follows TST-205, generation 2 · `mcp_server/designer_helpers/edits.py:98,154-157`, `mcp_server/server_tools/edits.py:93` · measured · found 2026-11-09
  - **Defect.** The check tests `prop.getId() == '$outputsize'`, so a value set on the input bound to it isn't seen, and the refusal for a driven parameter sends the agent to exactly that input. TST-205's "`_make_value` is the one path" doesn't hold for it.
  - **Scenario.** Probe, on a 512 px graph, a uniform's `$outputsize` exposed as `size_probe`: `set` on `graph` of `[1024, 1024]` is accepted and computes 8192x8192; `[1, 1]` computes 1024 and `[-2, -2]` 128, so the input is an offset.
  - **Fix.** Refuse above 13 when the graph input drives a `$outputsize` (`_input_users` knows the bindings), or say in the guide and the `apply_edits` text that such an input isn't checked.
  - **Resolution: done.** **Test:** `set on a bound input refuses`, its string case and `sweep_param on a bound input refuses`, failed in the scratch run (`graph.mcp_size: (0, 0) -> (1024, 1024)`). **Cause:** the check looks at the parameter's own id, and a graph input has its own. **Fix:** `_refuse_large_size_on_input` (`graph_inputs.py`), called by `set_params` and, before any value is set, by `sweep_param`, refuses above 13 for an int2 input that only binds a `$outputsize`. **Also covered:** an input read through other function nodes isn't a size, so it stays unchecked; `render_sbs(params=...)` goes to `sbsrender`, not measured and not changed.
  - Questioned by HLP-86 and HLP-89 (2026-11-09).

- [x] **TST-214 · The live refusal check skips the graph's `set`, which the resolution claims** · follows TST-205, generation 2 · `tests/test_all_tools/safeguards.py:838-875` · confirmed · found 2026-11-09
  - **Defect.** `check_outputsize_above_log2_is_refused` exercises `add`, a node's `set` and `sweep_param`; TST-205's resolution says "graph or node", but no check sets a fixed-size graph's `$outputsize` too high, and none passes `expose`'s `default`.
  - **Scenario.** A later change that checks only a node's value leaves the graph's path unguarded and the check still passes. The `expose` path was refused when probed, but nothing keeps it so.
  - **Fix.** Add both cases to the check.
  - **Resolution: done.** **Test:** the additions themselves: `set on the graph refuses` and `expose's default refuses a pixel count` passed before any change, as these paths were already refused and only unguarded. **Cause:** the check stopped at the node's paths. **Fix:** both cases are in the check, and the whole check moved to a graph of its own (left for `CLEAN`), which also ends the leftover in TST-205's note. **Also covered:** a refused `expose` adds no input; a refused `create_graph` makes no graph.

- [x] **TST-215 · Two leftovers of the moves** · follows TST-203 and TST-210, generation 2 · `mcp_server/GUIDE.md:287-291`, `mcp_server/server_tools/lifecycle.py:257-262` · confirmed · found 2026-11-09
  - **Defect.** The inheritance numbers restored by TST-203 are the first bullet under `## Designer UI (Qt)`, though the fix asked for them "next to the pattern" (Portals, the last bullet of `## sd API gotchas`). `_own_home`'s docstring repeats the module docstring's "the preferences plist stays shared (each Designer writes its `session.instancePID` there)", which TST-210 removed at `_own_temp`.
  - **Scenario.** Someone looking under sd API gotchas doesn't find the numbers, and a later edit of the Qt section may separate them from the pattern. The repeated fact can go stale in one place.
  - **Fix.** Move the bullet above `## Designer UI (Qt)`; have `_own_home` point to the module docstring.
  - **Resolution: done.** **Test:** `test_the_file_level_pattern_comes_with_the_inheritance_numbers` and `test_small_text_defects_stay_fixed`, failed on the section and on the second copy. **Cause:** the bullet went after the Qt heading; `_own_home` wasn't looked at with `_own_temp`. **Fix:** the bullet ends `## sd API gotchas`; `_own_home` points to the module docstring. **Also covered:** no other function in `lifecycle.py` repeats the plist fact.

- [x] **TST-216 · A rule for the server's code remains only in the live-check skill** · follows TST-206, generation 2 · `.claude/skills/live-check/SKILL.md:89,105` · confirmed · found 2026-11-09
  - **Defect.** "A string of several lines is written `dedent("""...""")`" is checked on "the self-test's and the server's modules", and "Tests that read source text match whitespace-tolerantly" applies to every unit test, but neither is in AGENTS.md or `.claude/rules/`. TST-206's "the rest of The suites concerns the suites themselves" misses them.
  - **Scenario.** A contributor changing `server_tools/` loads `mcp-builder`, not `live-check`, joins a multi-line snippet with `\n`, and `test_selftest_safety.py`, not among the tests run while working, fails only at the final check.
  - **Fix.** One line in AGENTS.md, Running the tests, or in `.claude/rules/changing-tools.md`.
  - **Resolution: done.** **Test:** `test_the_rules_for_all_python_are_where_every_python_change_sees_them`, failed as AGENTS.md had neither. **Cause:** they went into the skill with The suites. **Fix:** a **Strings of code** paragraph in AGENTS.md, Running the tests; the skill points there, as does the citation in `test_selftest_safety.py`. **Also covered:** the mypy tips, which only explain a failure the type check already reports, stay in the skill.

- [x] **TST-217 · Two more places say measured facts all live in GUIDE.md** · follows TST-208, generation 2 · `DECISIONS.md:13`, `.claude/skills/live-check/SKILL.md:92` · confirmed · found 2026-11-09
  - **Defect.** "Measured Designer behaviour lives in `GUIDE.md`" and "re-measure the Designer behaviour GUIDE.md states: add one with each new fact" predate AGENTS.md's table row sending what only a maintainer needs to the module's docstring; TST-208's **Also covered** lists only address-review.
  - **Scenario.** An agent writing a decision about a measured `quit_designer` behaviour links to GUIDE.md, where the fact no longer is.
  - **Fix.** "`GUIDE.md` or the module's docstring" at both. DECISIONS.md's introduction isn't a name or a path, so that half needs the user's word.
  - **Resolution: done.** **Test:** `test_no_doc_says_every_measured_fact_is_in_the_guide`, failed on both. **Cause:** the sentences predate the table row. **Fix:** both now say the guide or the module's docstring; the user approved the change to DECISIONS.md's introduction. **Also covered:** a search for "lives in" and "GUIDE.md states" in the docs and skills.

- [x] **TST-218 · The instance-node scope still says more than was measured** · follows TST-207, generation 2 · `mcp_server/GUIDE.md:231-232`, `mcp_server/designer_helpers/graph_inputs.py:236`, `tests/unit/test_guide.py:351,365` · confirmed · found 2026-11-09
  - **Defect.** `facts/function_states.py` measures the six parameters on a levels node and only `$outputsize` on an instance node. The guide's "relative to parent on an instance node, `$outputsize` only" turns not measured into doesn't happen, and the docstring's "measured on all six and an instance node" reads as all six on both.
  - **Scenario.** A scripting agent deletes a function on an instance's `$format` and skips restoring its inheritance, relying on "only".
  - **Fix.** "`$outputsize` measured" in the guide; "all six on a levels node, `$outputsize` on an instance node" in the docstring; update the two pinned strings. Narrowing the claim is the whole fix.
  - **Resolution: done.** **Test:** `test_a_claim_keeps_the_scope_it_was_measured_on` and `test_what_a_helper_cites_for_a_measurement_states_it`, changed to the narrower wording, failed on the old text. **Cause:** "only" replaced "measured", and the docstring dropped which node. **Fix:** the claim is narrowed in both, and no check added (a follow-up on wording). **Also covered:** the other three scopes of TST-207 name what was measured.

- [x] **TST-219 · Two doc tests compare unflattened text** · `tests/unit/test_guide.py:229,244` · confirmed · found 2026-11-09
  - **Defect.** `assert fact in _live_check_skill() and fact not in _agents_md()` and its twin compare raw text, though the same file has `_flat` and the live-check skill asks for whitespace-tolerant matching.
  - **Scenario.** A rewrap of AGENTS.md fails the test with no real change; a hard rule copied into the skill across a line break passes the `not in` half, which is what the test exists to catch.
  - **Fix.** Wrap the documents in `_flat` in both tests.
  - **Resolution: done.** **Test:** none seen failing: both tests pass the same on today's text, as the change only widens what they can see. **Cause:** they predate `_flat` in that file. **Fix:** both documents go through `_flat`. **Also covered:** a search of `tests/unit/test_guide.py` for other raw `in _agents_md()` and `in _live_check_skill()` comparisons; what remains is single-line text at a fixed place.
  - Questioned by TST-224 (2026-11-09).

- [x] **TST-220 · AGENTS.md's table doesn't say what goes in the core and what in the scripting part** · `AGENTS.md:117` · confirmed · found 2026-11-09
  - **Defect.** The row sends every usage fact to "`mcp_server/GUIDE.md`, in the matching section", with no test between the two parts, while the row below it gives one for module docstrings.
  - **Scenario.** The next contributor files a fact a tools-only agent needs under the sd gotchas, which is how TST-203 and TST-205 came about, or adds raw-API detail to the part every session pays for.
  - **Fix.** Add to the row: "the core if an agent using only the tools needs it, otherwise under `# Scripting`".
  - **Resolution: done.** **Test:** `test_agents_md_says_which_part_of_the_guide_a_fact_goes_in`, failed as the row had no criterion. **Cause:** the row predates the two parts. **Fix:** the row says the core if an agent using only the tools needs it, otherwise under `# Scripting`. **Also covered:** the row below already has its own test.
  - Questioned by TST-227 (2026-11-09).

- [x] **SRV-104 · SRV-103's cause survives for a blank scripting part and a file starting with the heading** · follows SRV-103, generation 3 · `mcp_server/server_tools/core.py:66-79` · confirmed · found 2026-11-09
  - **Defect.** `text.partition('\n# Scripting')` can't see a heading at byte 0, and `return heading.lstrip('\n') + scripting` serves a part with no body; `except OSError` doesn't catch `UnicodeDecodeError`.
  - **Scenario.** A bad merge leaves `'# GUIDE.md\n...\n# Scripting\n'`: `get_guide('scripting')` says "12 characters, complete" and opens the code tools. Invalid UTF-8 gives the agent no restore message, and the resource raises instead of saying so.
  - **Fix.** Refuse a scripting part with no body, match the heading at any line start (`(?m)^# Scripting`), catch `UnicodeDecodeError` as well, with those inputs in the unit tests.
  - **Resolution: done.** **Test:** `test_a_guide_without_its_core_opens_nothing` (a file starting with the heading), `test_a_scripting_part_with_no_text_opens_nothing` and `test_a_guide_that_isnt_text_opens_nothing`, failed. **Cause:** the split looked for a newline before the heading, and only `OSError` counted as unreadable. **Fix:** `_agent_guide` finds the heading at any line start, refuses a scripting part with no text after its heading and catches `UnicodeDecodeError`. **Also covered:** the resource says so on the same inputs.
  - Note (2026-11-09): the resource says so for a blank core and a file that isn't text; a scripting part with no text it serves as it is, which is harmless, so "on the same inputs" above is too broad.
  - Questioned by SRV-105 (2026-11-09).

- [x] **HLP-87 · A negative `$outputsize` at Absolute is accepted and computes 1 px** · follows HLP-84, generation 3 · `mcp_server/designer_helpers/core.py:223-226`, `mcp_server/designer_helpers/edits.py:124` · measured · found 2026-11-09
  - **Defect.** `_refuse_large_size` checks only the upper bound, while `_refuse_bad_size_log2` refuses below 0.
  - **Scenario.** Probe: `set` of a uniform's `$outputsize` to `[-1, -1]` is accepted and computes 1x1; `[-3, 5]` computes 1x32. An agent wanting half the size, thinking offset, gets 1 px, as `set` makes it Absolute.
  - **Fix.** Refuse negatives on the paths that make it Absolute (`add`, `set`, `sweep_param`), not in `_make_value` as a whole: `expose`'s `default` goes through it too and a negative offset is valid there.
  - **Resolution: done.** **Test:** `add`, `set` and `sweep_param` `refuses a negative size`, and a negative axis, failed in the scratch run (`(-1, -1)` accepted, 1x1). **Cause:** only the upper bound was checked. **Fix:** `_refuse_bad_size` refuses below 0 unless the value is an offset; `_refuse_bad_size_log2` merged into it, and the `apply_edits` text says it. **Also covered:** a bound input and `expose`'s default on an inherited node take a negative offset (live: `[-2, -2]` computes 128 px on 512 px).

- [x] **HLP-88 · `sweep_param`'s size refusal comes after state has changed, and a later bad value is no error** · follows TST-205, generation 2 · `mcp_server/designer_helpers/sweep.py:56-64` · measured · found 2026-11-09
  - **Defect.** `_make_value` runs per value inside the loop, after the inheritance was switched to Absolute; only the bound-input path checks up front.
  - **Scenario.** Probe, on a saved package: `isModified()` False, a `sweep_param` refused on `[[1024, 1024]]`, then `isModified()` True. `[[5, 5], [1024, 1024]]` computes the first value and returns "Sweep stopped after 1 of 2 value(s)" with `is_error` false, unlike the bound-input path.
  - **Fix.** Build every value before the inheritance switch and set from those, with a two-value node case in the check and an `isModified` check.
  - **Resolution: done.** **Test:** `sweep_param refuses a later bad value, as an error` and `a refused sweep_param leaves a saved package unmodified`, failed in the scratch run (`MODIFIED [True]`). **Cause:** each value was built inside the loop, after the inheritance was switched. **Fix:** `sweep_param` builds every value before changing anything. **Also covered:** a wrong value of any other parameter is now refused up front as well; "Sweep stopped" remains for a failure while computing.

- [x] **HLP-89 · An input bound to the graph's own `$outputsize` isn't checked** · follows HLP-85, generation 3 · `mcp_server/designer_helpers/graph_inputs.py:342-344,353` · measured · found 2026-11-09
  - **Defect.** The guard uses `_input_users(g, plain_only=True)`, whose plain branch skips `_graph_parameter_reads`, and HLP-85's **Also covered** doesn't mention it.
  - **Scenario.** Probe with `inputs/graph_parameter_function`: `set` on `graph` of `size_in` to `[1024, 1024]` is accepted and a uniform in it computes 8192x8192.
  - **Fix.** Also read `_graph_parameter_reads(g, False)` in the guard (its refs end `.outputsize`), with that case in a live check.
  - **Resolution: done.** **Test:** `an input bound to the graph's own size refuses`, failed in the scratch run (`(3, 3) -> (1024, 1024)`). **Cause:** the guard read only the nodes' bindings. **Fix:** `_refuse_bad_size_on_input` also reads `_graph_parameter_reads(g, True, plain_only=True)` (the new `plain_only`: a function that is only that read), as last saved. **Also covered:** a function doing more than the read isn't a size, so it stays unchecked, as for a node; `designer_scripts/inputs/graph_parameter_function.py` moved to `shared/`, two modules now running it.
  - Questioned by HLP-91 and HLP-92 (2026-11-09).

- [x] **TST-221 · "Filters inherit from their input" isn't true of a Pixel Processor** · follows TST-213, generation 3 · `mcp_server/GUIDE.md:119-120` · measured · found 2026-11-09
  - **Defect.** The core's unqualified sentence, moved there by TST-213, doesn't hold for the Pixel Processor.
  - **Scenario.** Probe, 2048 px graph, a 512 px uniform fed in: fresh levels, transformation, hbao and blur_hq are relative to input and compute 512 px, but a `pixelprocessor` is relative to parent and computes 2048 px. A tools-only agent expects 512.
  - **Fix.** Narrow the sentence: "filters inherit from their input; a Pixel Processor from the graph". Update the pinned string; no new check (generation 3).
  - **Resolution: done.** **Test:** `test_the_core_says_when_outputsize_is_an_offset`, changed to the narrower text, failed on the old sentence. **Cause:** the sentence came back to the core without the exception. **Fix:** the sentence names the Pixel Processor; no new check (generation 3).
  - Note (2026-11-09): **Also covered:** the sentence is the only statement of it; ROADMAP item 9's "designer facts" check for the Pixel Processor remains open work.

- [x] **TST-222 · "The default isn't stored (... input for a node)" is false for an instance with no input** · follows TST-203, generation 2 · `mcp_server/GUIDE.md:288-289`, `mcp_server/server_tools/snapshots.py:242-245` · measured · found 2026-11-09
  - **Defect.** The sentence covers every node, but `facts/size_inheritance_files.py` measures only `blur`.
  - **Scenario.** Probe, an instance of a graph with no inputs in a saved `.sbs`: fresh it is relative to parent and nothing is stored; Absolute stores `0`, relative to input `2`. An agent removing `<relativeTo>` on it expecting relative to input gets parent.
  - **Fix.** "The node's own default isn't stored: relative to input on a blur, relative to parent on an instance with no input", at both places.
  - **Resolution: done.** **Test:** `test_the_file_level_pattern_comes_with_the_inheritance_numbers`, failed on the old text, and a new "designer facts" check in `facts.py`, passing on a true fact. **Cause:** measured on a blur and stated for every node. **Fix:** the guide and the comment in `snapshots.py` say a node's default is its own; `facts/size_inheritance_files.py` also saves an instance. **Also covered:** the graph's default was already measured.

- [x] **TST-223 · The live-check skill and AGENTS.md disagree on a fix touching only `mcp_server/GUIDE.md`** · `.claude/skills/live-check/SKILL.md:76-79`, `AGENTS.md:85-86` · confirmed · found 2026-11-09
  - **Defect.** The skill says the live suite runs again if a fix touches `mcp_server/`, which now holds the guide, while AGENTS.md says docs changed alone never need it.
  - **Scenario.** A doc test fails at the final check, the fix edits only `GUIDE.md`, and the agent following the skill tells the user the 11-minute suite must run again.
  - **Fix.** "`mcp_server/` (not GUIDE.md alone, which is docs: AGENTS.md, Running the tests)".
  - **Resolution: done.** **Test:** `test_the_skill_doesnt_call_a_guide_only_fix_code`, failed. **Cause:** the list predates the guide's move under `mcp_server/`. **Fix:** the list excepts GUIDE.md alone. **Also covered:** AGENTS.md's Running the tests is the only other statement of it.

- [x] **TST-224 · Two more doc tests compare unflattened text** · follows TST-219, generation 2 · `tests/unit/test_guide.py:115,478` · confirmed · found 2026-11-09
  - **Defect.** `assert fact in core and fact not in scripting, fact` and `assert fact not in _guide_md()` compare raw text, and TST-219's search covered only `_agents_md()` and `_live_check_skill()`.
  - **Scenario.** A fact copied across a line break passes the `not in` half, which is what these tests are for.
  - **Fix.** Flatten both, as the neighbouring tests do. Nothing else.
  - **Resolution: done.** **Test:** none seen failing: both pass the same on today's text, the change only widening what they see. **Cause:** older than `_flat`. **Fix:** both are flattened. **Also covered:** a search of `tests/unit/test_guide.py` for `not in` over raw text in these helpers.

- [x] **TST-225 · The skill-discovery test accepts a description that breaks the YAML** · `tests/unit/test_guide.py:213` · confirmed · found 2026-11-09
  - **Defect.** `description: '.*alone\.run.*'` matches a lone apostrophe inside the single-quoted value, which is invalid YAML.
  - **Scenario.** A rewording writes `can't`; the frontmatter stops parsing and the skill loses its description, while the test passes.
  - **Fix.** Replace each `.*` with `(?:[^']|'')*`.
  - **Resolution: done.** **Test:** none in the repo, as it is a test's own pattern; in a scratch run the old pattern accepted a sample with a lone apostrophe and the new one refused it. **Cause:** `.*` matches an apostrophe. **Fix:** each `.*` is `(?:[^']|'')*`. **Also covered:** the only such pattern in the file.

- [x] **TST-226 · Where the crash dumps are is only in the scripting part** · follows TST-210, generation 2 · `mcp_server/GUIDE.md:310-312` · confirmed · found 2026-11-09
  - **Defect.** TST-210 named the folder, but in a bullet of the part a tools-only agent is told it can skip, against AGENTS.md's new table row.
  - **Scenario.** An agent using only the tools sees Designer crash and can't say where the dump is.
  - **Fix.** Move the crash-dump sentence to the core's Several Designers.
  - **Resolution: done.** **Test:** `test_a_tools_only_agent_is_told_where_the_crash_dumps_are`, failed. **Cause:** it stayed in the Quitting bullet of the scripting part. **Fix:** moved to the core's Several Designers. **Also covered:** nothing else in that bullet concerns a tools-only agent, per the third review's assessment.

- [x] **HLP-91 · An instance node's parameter that binds `$outputsize` inside its graph isn't checked** · follows HLP-89, generation 4 · `mcp_server/designer_helpers/edits.py:162-164`, `mcp_server/designer_helpers/sweep.py:48-49`, `mcp_server/designer_helpers/graph_inputs.py:358-368` · measured · found 2026-11-09
  - **Defect.** The guard runs only for the `graph` target and looks only at the bindings in that graph.
  - **Scenario.** Probe: graph A exposes a uniform's `$outputsize` as `size_in`, graph B holds an instance of A at 512 px; `set` of the instance's `size_in` to `[1024, 1024]` is accepted and computes 8192x8192. `add` instances only library graphs, so this needs an instance a person made.
  - **Fix.** Say in the helper's docstring and HLP-89's limits that an instance's parameters aren't checked, or run the guard against the referenced graph.
  - **Resolution: done.** **Test:** `set on an instance's parameter bound to a size refuses` and its `sweep_param` twin, failed in the scratch run (`(0, 0) -> (1024, 1024)`, 8192x8192). **Cause:** the guard ran only on the graph target. **Fix:** `_refuse_bad_size_on_input` takes the target: a graph, or an instance node, whose parameter it checks against the graph it references; `set_params` and `sweep_param` call it for any target. **Also covered:** only that one level, as the docstring says: an instance inside the referenced graph isn't followed; a node that isn't an instance references no compositing graph and is skipped.
  - Questioned by HLP-93 (2026-11-09).

- [x] **HLP-92 · A stale saved file can refuse a value and say the input drives the size** · follows HLP-89, generation 4 · `mcp_server/designer_helpers/graph_inputs.py:369` · confirmed · found 2026-11-09
  - **Defect.** The binding on the graph's own `$outputsize` is read from the file as last saved, so one removed since then still counts, and the refusal states it as fact.
  - **Scenario.** A person removes that function in the UI without saving; a `set` of the now unrelated input to `[1024, 1024]` is refused with "(it drives $outputsize)". The tools can't make or remove that function.
  - **Fix.** Add "as last saved" to the refusal's text for this owner.
  - **Resolution: done.** **Test:** `an input bound to the graph's own size refuses`, now requiring "as last saved", failed in the scratch run. **Cause:** the refusal stated what the file says as if it were the current graph, and the API can't read it. **Fix:** the refusal for this owner says "as last saved" and to save the package if that has changed, which refreshes what it reads. **Also covered:** nothing else refuses on this reading.
  - Questioned by HLP-95 (2026-11-09).

- [x] **TST-227 · AGENTS.md's criterion for the core doesn't fit the pitfalls a test keeps there** · follows TST-220, generation 2 · `AGENTS.md:122`, `tests/unit/test_guide.py:112-115` · confirmed · found 2026-11-09
  - **Defect.** The row says the core is for what "an agent using only the tools needs", but `test_the_pitfalls_everyone_hits_are_in_the_core` requires raw-API facts such as `APIException` deriving from `BaseException` there.
  - **Scenario.** A contributor applying the row moves that bullet and the unit test fails, or can't tell why another raw-API pitfall belongs among the first ones.
  - **Fix.** Add the exception to the row: "... or if every script hits it on the first try".
  - **Resolution: done.** **Test:** `test_agents_md_says_which_part_of_the_guide_a_fact_goes_in`, changed to the new row, failed on the old text. **Cause:** the row named only the tools-only reader. **Fix:** the row adds what every script hits on the first try. **Also covered:** `test_the_pitfalls_everyone_hits_are_in_the_core` is the only test pinning such facts in the core.

- [x] **HLP-93 · An instance's parameter bound to a size is unchecked through `expose` and through the graph input bound to it** · follows HLP-91, generation 5 · `mcp_server/designer_helpers/graph_inputs.py:105-106,376-380`, `mcp_server/designer_helpers/edits.py:159-163` · measured · found 2026-11-09
  - **Defect.** HLP-91's guard runs for `set` and `sweep_param` on the instance's parameter. `expose_param`'s `default` goes through `_make_value`, which only looks at a property whose id is `$outputsize`, and a graph input bound to the instance's parameter has the ref `inst.size_in`, which `if ref.endswith('.$outputsize')` drops. HLP-91's **Also covered** names only an instance inside the referenced graph.
  - **Scenario.** Probe: graph A exposes a uniform's `$outputsize` as `size_in` and an instance of A sits in graph B at 512 px. `expose` of the instance's `size_in` with `default` `[1024, 1024]` is accepted and `node_stats` reports 8192x8192. `set` on `size_in` is then refused with "is driven by graph input 'outer_in'; set that instead" and no unit, and `set` of `outer_in` to `[2048, 2048]` is accepted, still 8192x8192: the refusal sends the agent to the unguarded input, HLP-85's pattern. `add` instances only library graphs, so this needs an instance a person made.
  - **Fix.** One call in `expose_param`, `_refuse_bad_size_on_input(node, prop, [default])`, when a default is given. For the outward direction, either follow a plain binding onto an instance's parameter one level, or say in `_refuse_bad_size_on_input`'s docstring that such an input isn't checked.
  - **Resolution: done.** **Test:** `expose's default on an instance's parameter bound to a size refuses`, failed in the scratch run (`exposed ... default (1024, 1024)`), and a small default still accepted. **Cause:** HLP-91 added the guard to `set` and `sweep_param` only. **Fix:** `expose_param` calls `_refuse_bad_size_on_input` when a default is given, before anything changes. The outward half is documented, at the user's choice (DECISIONS.md, Function graphs and inputs): `_refuse_bad_size_on_input`'s docstring says an input bound to an instance's parameter isn't checked. **Also covered:** the guard returns at once for a `$` or non-int2 parameter and for a node that isn't an instance, so no other `expose` changes.

- [x] **HLP-94 · The offset note also goes on a function that isn't an input** · follows HLP-90, generation 5 · `mcp_server/designer_helpers/edits.py:159-162`, `mcp_server/designer_helpers/sweep.py:50-54`, `mcp_server/designer_helpers/graph_inputs.py:358-362` · confirmed · found 2026-11-09
  - **Defect.** `_offset_note` tests only `prop.getId() == '$outputsize' and _inherits_size(node, prop)`. `_refuse_no_input` returns at once when `_plain_binding(fg) is None`, so a function with an output that isn't a single read reaches the `raise` and gets "that input is a log2 offset". HLP-90's **Also covered** ("a function that isn't a plain binding keeps its own refusal") doesn't match the code.
  - **Scenario.** A hand-written `get size_in + (1,1)` on an inherited `$outputsize`: `set` says "is driven by a function; set that instead ...; while this node inherits its size, that input is a log2 offset (0 keeps the size, 1 doubles it)". No input is named, and in this function 0 adds one step. `sweep_param` says the same. Only a function built outside the tools reaches it.
  - **Fix.** Add the note only when `_plain_binding(driven) is not None`, at both places, for example by passing `driven` to `_offset_note`.
  - **Resolution: done.** **Test:** `set on a driven size says its input is an offset` and its `sweep_param` twin, now requiring the new wording, failed in the scratch run. **Cause:** the note was worded for the plain binding, but no check limits it to one. **Fix:** at the user's choice of a text change over a code change, the note now says "a graph input bound to it is a log2 offset", which holds whatever function drives the size; it no longer points at "that input". **Also covered:** both refusals share `_offset_note`. This corrects HLP-90's **Also covered**, as a hand-written function does get the note.

- [x] **HLP-95 · After HLP-91, "save the package" can name the wrong package** · follows HLP-92, generation 5 · `mcp_server/designer_helpers/graph_inputs.py:381-382` · confirmed · found 2026-11-09
  - **Defect.** On an instance target the file read is the referenced graph's package, while the text says only "save the package if that has changed". HLP-92's **Also covered** predates that reach.
  - **Scenario.** An instance of a graph from another package whose saved file is stale: the agent saves the package it is editing, the file read doesn't change, and the same refusal comes back.
  - **Fix.** Name the graph in the text ("save the package of %s if that has changed", `graph.getIdentifier()`).
  - **Resolution: done.** **Test:** `an input bound to the graph's own size refuses`, now requiring the new wording, failed in the scratch run. **Cause:** the text was written when the file read was always the current graph's. **Fix:** the text says "of the graph it belongs to; save that graph's package if that has changed", in words alone rather than the fix's named graph, as the user asked for a text change. **Also covered:** this is the only refusal on this reading.

- [x] **SRV-105 · The guide's restore message says every tool refuses, when only the code tools do** · follows SRV-104, generation 4 · `mcp_server/server_tools/core.py:58-59,75` · confirmed · found 2026-11-09
  - **Defect.** `'mcp_server/GUIDE.md %s: restore it (git checkout), then call get_guide again; the tools refuse until then.'` is shared by the three failures, but with `has no scripting part` `get_guide()` still serves the core and opens every tool but the two code ones.
  - **Scenario.** A file with a core and no scripting part: `get_guide('scripting')` raises this text while the other tools keep working, so an agent may stop work it could go on with.
  - **Fix.** Narrow the text: drop "the tools refuse until then", or say "the code tools" in the scripting case. No test pins the sentence, and narrowing it is the whole fix.
  - **Resolution: done.** **Test:** `test_a_scripting_part_with_no_text_opens_nothing`, now asserting the claim is gone, failed on the old text. **Cause:** one sentence shared by failures that close different tools. **Fix:** the sentence is dropped; the message says what is wrong and to restore the file and call `get_guide` again. **Also covered:** all three failures share that text.
