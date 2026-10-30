# TODO.md: direction check (2026-10-29)

A step back from the review fixes: is this project heading the right way as an MCP for
Substance Designer? Notes to look at later; anything we decide to do moves into
[ROADMAP.md](ROADMAP.md).

## Verdict

The direction is mostly right, but the work has drifted from making materials towards working on
the project itself.

## What's right (keep)

- **The architecture.** A tiny, generic plugin that runs code, with all the logic in the server:
  tools change without restarting Designer. The live `sd` API means no `pysbs` licence.
- **The tools that measure.** `preview_node`, `node_stats`, `sweep_param`, `check_tiling` and
  `compare_to_reference` let the agent see and measure what it builds instead of guessing. This
  is what sets the project apart.
- **AGENTS.md.** Verified Designer facts (enum values, inheritance numbers, which connector
  reports a connection, Undo hazards), re-checked by the self-test.
- **Safety for the user's work.** One undo step per edit, snapshots and diffs, refusing to quit
  with unsaved changes.

## Where it's drifting

1. **Little real material work so far.** In 2 days: 38 commits, tools went from 23 to 43, but only
   one material was built (the dwarf trim sheet). The last ~15 commits are review fixes,
   installer/uninstaller, renaming, registration and process skills. REVIEW.md is 762 lines; the
   only example is 554.
2. **The roadmap is mostly polish.** `compare_maps`, render engine flags, portals without a
   reload and large-graph paging are fine, but none came from "I tried to make X and got stuck".
3. **Many tools, several overlapping.** `add_node`, `connect`, `set_params`, `disconnect`,
   `move_nodes` and `delete_nodes` all duplicate `apply_edits`. Claude Code defers loading tool
   schemas, so it costs little there; other MCP clients load all 43, and more choices make it
   harder for the agent to pick the right one.
4. **The biggest gaps sit in "Later":**
   - Function graph / Pixel Processor editing (ROADMAP #9): most advanced materials need it.
   - `get_selection`: lets the user say "fix this node", which is how artists work.
   - `material_report`: one call that answers "is this material correct?"
5. **The process is heavy for a 2-day-old tool.** A test with every change, a severity-ranked
   review log and two review skills suit a mature library; here they slow down finding out what
   the tool should do.

## Next steps

- [ ] **Pause infrastructure work.** Finish the `review-fixes` branch and stop there; the 6 open
  low findings in REVIEW.md can wait.
- [ ] **Use it on 3–4 different real tasks:**
  - [ ] a tileable material from a photo reference;
  - [ ] changing an existing graph we didn't build;
  - [ ] a stylized material;
  - [ ] one that needs a Pixel Processor.

  Note every point where the agent fell back to `execute_designer_code`, guessed, or needed the
  user. That list should become the roadmap.
- [ ] **Look at the other Designer MCP now** (ROADMAP #6:
  [matthieuhuguet/substance-designer-mcp](https://github.com/matthieuhuguet/substance-designer-mcp)).
  Compare its tools with ours, and check that ours still covers ground it doesn't. Verify any
  facts it states before relying on them.
- [ ] **Add `get_selection`, then start on function graph editing;** let the real tasks decide
  what comes after.
- [ ] **Consider cutting tools:** keep `apply_edits` as the way to edit, and drop the single-edit
  tools or make them thin aliases. If they go, update README's Tools table, the self-test and the
  unit tests that check every tool is covered.
