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

- *Confirmed*: the defect is visible in the code as quoted.
- *Plausible*: the code path exists, but whether it bites depends on Designer, the OS or timing.
- *Verified by hand*: checked against the code after the review, not only by the reviewer.

**IDs.** One prefix per area, numbered on: **PLG** plugin and bridge protocol, **SRV**
`mcp_server/server.py` and `server_tools/`, **HLP** `mcp_server/designer_helpers/`, **INS** installer, uninstaller,
command-line client and example, **TST** tests and docs. A new area gets a new prefix, added here.

**Last used:** PLG-31, SRV-72, HLP-82, INS-26, TST-145.

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
| Medium | 0 | 2 |
| Low-medium | 0 | 4 |
| Low | 0 | 3 |
| **Total** | **0** | **9** |

## Review log

### 2026-11-04: branch `output-node-fields` against `main`, the diff only, working tree included

- **How:** two read-only reviewers, one on the code under `mcp_server/`, one on the tests and docs. Unit tests: 651 passed. Live self-test, run before this review: 473 of 475. Its 2 failures were one mistake in the new `output_fields` check, which passed `graph` to `save_package` instead of `graph_or_path`, so the save went to another package. The test is corrected in the working tree and the self-test **not yet run again**, so the saved tag's form and the diff against the saved file are still unconfirmed live.
- **Resolutions assessed:** none in scope; the file held no findings. No decision in `DECISIONS.md` is touched, and no finding was dropped for contradicting one.
- **Findings:** 8: 1 medium (TST-141), 4 low-medium (HLP-81, SRV-71, TST-142, TST-143), 3 low (SRV-72, TST-144, TST-145). SRV-71 and TST-144 each found by both reviewers. All are generation 1. No defect found that changes or loses a user's work; HLP-81 is the one that might, and it is unmeasured.
- **Suggested order:** HLP-81 first, since measuring it may change the design; then TST-141 and TST-142 with TST-143, in one self-test run; then SRV-71, SRV-72, TST-144 and TST-145.
- **Checked and found fine:** the pre-check and the run decide tags or params by the same test; a ref is judged by its newest definition; `graph`, `''`, deleted nodes and refs not yet defined are refused before the new branch can misread them; `fullmatch` refuses a trailing newline; the name check runs before an `add`'s node exists and before a `set` writes anything; library graphs are refused by `_graph_to_edit` first; the API calls match Designer's stubs; every name in `_USAGES` is spelled as in the library; only `render.py` depends on the shared graph's output being called `height`, and `undo.py` restores it in every branch.

---

## High

## Medium-high

## Medium

- [x] **TST-141 · The Undo check on an output's name can pass when nothing was renamed or nothing was put back** · `tests/test_all_tools/undo.py` · confirmed · verified by hand · found 2026-11-04
  - **Defect.** `undone = "identifier='undo_me'" not in text(await c('describe_graph', G))` is all it measures: the rename isn't confirmed first, and the old name isn't confirmed after. It also covers `identifier` only, though `label` and `usages` are set through the same API, `usages` with an array value, and the comment above it speaks of "the annotations".
  - **Scenario.** The `set` is refused, so Undo reverts the previous step instead, the `delete` of the blur node above it: `undo_me` is absent and the check passes, with a stray node back in the shared graph, and no Redo as the `add` check above it has. An Undo leaving `output` or an empty name passes too. Reading through `describe_graph` also skips the `processEvents` AGENTS.md asks for after Undo.
  - **Fix.** Set all three fields; assert the new values before Undo and the old ones after, reading after a `processEvents`; Redo if Undo hit another step. Found by the tests reviewer; the second reviewer found the `identifier`-only part.
  - **Resolution: done.** Test: a check of a check, so no failing run came first; the live run now passes with each state read. Cause: the check only looked for the new name being absent. Fix: `tests/test_all_tools/undo.py` sets all three fields, confirms them before Undo and confirms the old name with no tag after it, reading after a `processEvents`, and calls Redo if Undo hit another step. Also covered: the other Undo checks in that file already read the state on both sides.

- [x] **HLP-82 · `quit_designer`'s fallback can't force a Designer stuck in its final teardown, and blames a dialog** · `mcp_server/designer_helpers/quit.py`, `mcp_server/server_tools/lifecycle.py` · confirmed · verified by hand · found 2026-11-04
  - **Defect.** The fallback is a `QTimer.singleShot`, which needs Designer's event loop, and in this state the loop and Python have already gone. So "about 35 s after the quit, a Designer still running with every window closed is forced" doesn't hold here. This reopens the decision "Forcing a Designer still running with every window closed is only a defence, with no on-demand test", whose **Reopen if** includes "a quit is seen to leave Designer running again". The error also says "it may be showing a dialog", when none was open.
  - **Scenario.** Seen once on 2026-11-04, in a Designer running only scratch packages, no self-test running. The log got as far as `Destroy Application`. `sample` showed the main thread in `QCoreApplication::~QCoreApplication` -> `QThreadPool::waitForDone`, and a pooled thread in `Alg::BinaryHardeningService::runInThread` -> `_runBinaryHardeningChecks` (Adobe's licence check), at about 300% CPU. `quit_designer` failed after 60 s, and the process was still running over two minutes later, with no windows and the bridge gone, until it was killed by hand. The quits before it this session and those in the self-test run after it worked. The 60 s and the rest of the timing are this one run's; not reproduced on demand.
  - **Fix.** A guard outside Qt's event loop, for example a daemon thread started with the quit that calls `os._exit(0)` at the give-up time, if Python threads still run that late; measure that first. Otherwise `quit_designer`'s server side, which sees the process from outside, could end it after its wait, for a Designer it asked to quit with nothing unsaved. Change the message to say which it saw. Belongs with ROADMAP item 23.
  - **Resolution: done**, the user's rule (2026-11-05): a Designer an agent started is disposable, and one the user opened is never ended. Test: reproduced on demand before any fix by a Python task held in Qt's global thread pool, with the same stack, so the hang has a live check (`designer_scripts/lifecycle/hold_thread_pool.py`); unit tests in `test_lifecycle_env.py`. Cause: the fallback ran on Qt's event loop in Python, gone by then. Fix: `launch_designer` records the process it started, with its start time, in a file next to the bridge token (the temp folder depends on how the server was started, a live run showed); `quit_designer` closes that one and past its wait force-ends it from the server, and refuses any other; `designer_status` says which it is. The fallback in `designer_helpers/quit.py` and `test_quit_fallback.py` are deleted, and with them ROADMAP item 23. An earlier fix that judged from Designer's log whether a process was stuck was dropped before committing: a review showed it could end the wrong Designer. Also covered: `launch_designer` ends an agent's Designer not answering, and for the user's gives the process ID and the command; ROADMAP item 25's state table. Not covered: Windows, where every Designer counts as the user's.

## Low-medium

- [x] **HLP-81 · Renaming an existing output may break what uses it, and nothing says so** · `mcp_server/designer_helpers/edits.py` (`set_output_tags`), `mcp_server/server_tools/edits.py` · plausible · found 2026-11-04
  - **Defect.** The `set` op's `identifier` renames the output, and AGENTS.md says an instance's connector ids equal the referenced graph's identifiers. What happens to a link from such a connector was never measured, and neither the result nor the description mentions it.
  - **Scenario.** Graph A's output `base` feeds graph B through an instance, `A.base -> levels`. `{"op": "set", "node": "<A's output>", "identifier": "albedo"}` reports success, and `diff_graph` on A shows only the rename, while B's link may be gone or dangling.
  - **Fix.** Measure it with two graphs in a "designer facts" check and record the fact in AGENTS.md. If links break, say so in the description, and warn when an open graph has an instance of this one.
  - Note (2026-11-04), measured (`facts/rename_output_instance.py`, recorded in AGENTS.md): a graph open during the rename follows it, in the same package or another, also after saving and reloading, pixels unchanged. One closed during the rename keeps connector `base`, its link stays, and it computes black (`407fbfff` before, `00000000` after), with no error and not marked as modified. Whether to warn or refuse is the user's to decide, so this stays open. Not measured: how to repair such a graph, and a rename done by hand in Designer.
  - **Resolution: done**, a warning, the user's choice (2026-11-04) over refusing a rename or only documenting it. Test: `test_renaming_an_existing_output_tells_the_agent_to_tell_the_user` failed with `TypeError: unexpected keyword argument 'warn_rename'`; live checks that a rename of an output from an earlier call says "Tell the user", and that a new output, one from the same batch and the name it already has don't. Cause: Designer updates only what is open; a closed graph can't follow, and the tools can't see it. Fix: `set_output_tags` prints the warning, naming the repair; a rule in AGENTS.md's Rules that protect the user's work; `apply_edits`' description. Measured too: a new instance wired from the new name repairs it, renaming back with that graph open doesn't (`facts/rename_output_instance.py`). Not measured: a rename by hand in Designer. Also covered: the add op can't reach this, as nothing can be using a new output; a rename done in the user's own code gets no warning.

- [x] **SRV-71 · `apply_edits`' description says the wrong thing about when a bad output field is refused, and other docs lag the change** · `mcp_server/server_tools/edits.py`, `snapshots.py`, `discovery.py`, `mcp_server/designer_helpers/batch.py`, `ROADMAP.md` · confirmed · verified by hand · found 2026-11-04
  - **Defect.** "Other mistakes (a missing field, a wrong connector or parameter id, a bad value) show only when their op runs", yet a bad identifier, a non-text label, a bad usage, or these fields with `params` refuse the whole batch before any op runs (`_check_output_fields`). AGENTS.md sends readers to this description for exactly that distinction.
  - **Scenario.** An agent reads that a bad value stops the batch partway and expects the earlier ops applied, when nothing was. The `set` line also shows `"params": {...}` as required next to the new fields, and following it literally is refused with "give params or ..., not both". "Prints old -> new" doesn't hold for the new fields, and the colour space chosen for a usage isn't mentioned.
  - **Fix.** One sentence naming these refusals; `"params"?` on that line; say what is chosen for a usage. Also name the output fields in `diff_graph`'s and `describe_graph`'s descriptions and `_check_batch`'s docstring, and fix ROADMAP item 47's title (`add` op only) and its "the `set` op only reaches input parameters". Found by both reviewers.
  - **Resolution: done.** Test: none of its own beyond `test_apply_edits_docstring_lists_every_op_and_field`, since these are sentences. Fix: `apply_edits`' description names these refusals in its checked-first sentence, shows `"params"?`, says what a usage is given, and limits "Prints old -> new" to params; `diff_graph`'s and `describe_graph`'s descriptions and `_check_batch`'s docstring name the output fields; ROADMAP item 47 reads as done. Also covered: the live run showed `export_outputs` already refuses two outputs with one name, so "would overwrite each other" in the description and two comments now says that instead.

- [x] **TST-142 · `output_fields` weakens the older check that `quit_designer` refuses unsaved changes** · `tests/test_all_tools/graph_edit.py` (`output_fields`, and `wire`'s `TEST_GRAPH in text(r_)`) · confirmed · verified by hand · found 2026-11-04
  - **Defect.** `output_fields` ends with an unsaved edit, so its package is still modified when `wire` checks the refusal, and `'mcp_selftest'` is a substring of that package's path and graph id. This run's log shows both listed: `never saved [mcp_selftest]; .../mcp_selftest_outputs.sbs`.
  - **Scenario.** A regression makes the quit check miss never-saved packages. Before this change the check would fail; now quit still refuses, because of the outputs package, and the substring still matches.
  - **Fix.** Assert `'[%s]' % TEST_GRAPH in text(r_)`, and close the package at the end of `output_fields`, since nothing later uses it.
  - **Resolution: done.** Test: a check of a check, so no failing run came first; the log now shows `unsaved changes in 1 package(s): never saved [mcp_selftest]`, the outputs package no longer among them. Fix: the check in `wire` asks for `'[mcp_selftest]'`, and `output_fields` closes its package when it ends. Also covered: the run's `finally` still closes it if a check before that raises.

- [x] **TST-143 · Several cases of the output fields never reach Designer** · `tests/test_all_tools/graph_edit.py` (`output_fields`), `tests/unit/test_batch_fields.py`, `tests/unit/test_sbs.py` · confirmed · found 2026-11-04
  - **Defect.** The unit tests stop at `_check_batch` or call `set_output_tags` on fakes, and don't run the `apply_edits` dispatcher, while AGENTS.md asks for a live run of anything that depends on Designer.
  - **Scenario.** With no live run, or none at all: a `set` by a ref added in the same batch; a `set` on an existing atomic or library node that isn't an output (`found.getDefinition().getId()` runs only on a MagicMock); two `add` ops naming one identifier in one batch, where the first stays applied; an empty or non-ASCII label and the usage `$matte`, which a unit test accepts; a diff from no tag to a tag (`usage (default) -> normal`), the common flow. Whether any of them misbehaves is unknown.
  - **Fix.** Add them to `output_fields`' list, and one case to `test_a_diff_shows_an_output_renamed_or_retagged`.
  - **Resolution: done.** Test: all of these pass live, so none showed a defect. Fix: `output_fields` adds a `set` by a ref of the same batch, `$matte`, an empty and a non-ASCII label, an identifier on an existing atomic and library node, and one name twice in a batch, where the first stays and the error names it; `test_a_diff_shows_an_output_renamed_or_retagged` adds no tag or label becoming one. Also covered: the list in the entry, nothing else found on the same path.

## Low

- [x] **SRV-72 · A usage also overwrites the tag's components and colour space, and no tool shows that** · `mcp_server/designer_helpers/edits.py` (`set_output_tags`), `mcp_server/server_tools/snapshots.py` (`_output_tags`), `mcp_server/designer_helpers/describe.py` (`_output_tags_text`) · confirmed · found 2026-11-04
  - **Defect.** `SDUsage.sNew(name, 'RGBA', 'sRGB' if name in _SRGB_USAGES else 'Linear')` writes all three, but `diff_graph` and `describe_graph` read only the name.
  - **Scenario.** The example tags roughness `('roughness', 'R', 'Linear')`. A `set` with `"usage": "roughness"` rewrites it to `RGBA`, and `diff_graph` reports no change.
  - **Fix.** Include components and colour space in `_output_tags`, for example `usage roughness (R, Linear) -> roughness (RGBA, Linear)`, and in `describe_graph` where they aren't the defaults.
  - **Resolution: done.** Test: a new case of `test_a_diff_shows_an_output_renamed_or_retagged`, one name from `R` to `RGBA`, failed with `assert [] == [...]`, no line at all. Cause: `_output_tags` kept only the usage's name. Fix: it keeps components and colour space: `usage roughness (R, Linear) -> roughness (RGBA, Linear)`. `describe_graph` still shows the name only, which is what an agent acts on. Also covered: only `_graph_model` reads these.

- [x] **TST-144 · "Every tag of Designer's own graphs is RGBA" is false and has no check** · `mcp_server/designer_helpers/edits.py` (comment in `set_output_tags`), `AGENTS.md` (Output nodes) · confirmed · found 2026-11-04
  - **Defect.** `# RGBA as in every tag of Designer's own graphs` and "Its own graphs' tags are `RGBA`, whatever the map holds, nearly all with no colour space". Of the 2078 `<usage>` tags in the install's `packages/*.sbs`: 2061 RGBA with no colour space, 10 RGB, 5 RGBA with one, 2 A. `facts/output_annotations.py` doesn't measure any of this.
  - **Scenario.** A reader takes `RGBA` as the only form, while `rust_weathering_material.sbs` has an RGB `specular`.
  - **Fix.** Say "nearly every" in both, and add a "designer facts" check reading the library files as text, with no package load, so the library-package rule isn't touched; or delete the sentence from AGENTS.md. Found by both reviewers.
  - **Resolution: done.** Test: none, as the claim is gone rather than checked. Fix: the comment in `set_output_tags` says "nearly every", and the sentence is deleted from AGENTS.md, since no agent needs it to act. Also covered: no other place states it.

- [x] **TST-145 · The characters an identifier may use aren't checked against Designer** · `mcp_server/designer_helpers/batch.py` (`_check_output_fields`), `mcp_server/designer_helpers/edits.py` (`set_output_tags`), `tests/test_all_tools/designer_scripts/facts/output_annotations.py` · confirmed · verified by hand · found 2026-11-04
  - **Defect.** `[A-Za-z0-9_-]+` allows a leading digit and `-`, while the fact check measures only `../a b.c` being rewritten and the live checks use plain names. `set_output_tags` also reports the name asked for, not what was stored.
  - **Scenario.** If a later Designer rewrites `-`, then `a-b` is stored as `a_b`, the result still says `a-b`, and the duplicate check compared the old text. Not a bug today: a one-off probe on Designer 16 during this work kept `1abc` and `a-b` as given, but no check in the self-test holds that.
  - **Fix.** Add `1abc` and `a-b` to `facts/output_annotations.py`. Reading the name back isn't needed unless that check fails.
  - **Resolution: done.** Test: `facts/output_annotations.py` sets `1abc`, `a-b` and `A_b9` and reads each back; all three stay on Designer 16. Fix: that check, so a later Designer rewriting them fails the self-test. No read-back in the code: nothing shows it is needed.
