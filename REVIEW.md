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

**Last used:** PLG-42, SRV-119, HLP-119, INS-27, TST-334.

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
| Low | 0 | 0 |
| **Total** | **0** | **0** |

## Review log

### 2026-11-12: branch `test-scaffolding` against main (the diff only, ROADMAP item 94)

- **How:** one reviewer read the whole diff (the `faked_helpers` fixture in `tests/unit/conftest.py` and the nine
  files using it, the 3D view's test graph built in `editor_panels_and_fit/preparations.py`, ROADMAP item 94). No tests
  were run and no probes were needed. Two suspicions came back, and reading settled both as wrong:
  - The editor's graph at the 3D checks after the first is no longer the graph they pass as `graph=`. It is now
    `VIEW3D_ADDED`, where on main it was `VIEW3D_GRAPH`. This makes the two "Parameters panel back on the graph in the
    editor" checks stronger, not weaker. `_parameters_back` reopens `_current_graph()` whatever `graph=` was, and the
    checks compare the panel with the editor's graph (`PANEL=...|EDITOR=...`). On main, those graphs were the same at
    both checks in a full run (the set-up check runs before the one that opens `VIEW3D_PLAIN`), so a turn-back to the
    Explorer's selection would also have passed. Now the two graphs differ, and the checks tell the cases apart.
  - If building the 3D graph fails, the whole category is skipped instead of one check. Dropped under **Low-value
    findings about the tests and docs are not raised**. The same preparation already adds library nodes (clouds_2,
    slope_blur) that stop the category the same way. A missing checker fails the run loudly either way, as one
    "environment is prepared" failure, and nothing reaches the user's Designer, where the build is skipped.
- **Not verified:** none.
- **Resolutions assessed:** none in scope (the file held no findings).
- **Findings:** none.
- **Checked and found fine:**
  - `APIException`, a real BaseException in six files that had a MagicMock: the helpers use it only in
    `except (Exception, APIException)` clauses, looked up at run time. On main an exception reaching one raised
    `TypeError`, which no test expected or caught, so no passing test reached one.
  - `QRectF` set after the exec in `test_fit_view`: `_fit_view_to` imports it when called.
  - The `vars(m)['X'] = v` writes are the same as `m.X = v` on a module, and none of the old direct writes is left.
  - The shared fixture matches the nine copies it replaced, and none of those copies is left in `tests/`.
  - `prepare` runs in the full run, `--only` and `alone.run`. `VIEW3D_ADDED` starts with `mcp_selftest`, so the
    clean-up unloads it.
  - The new graph doesn't conflict with the DECISIONS entry on preparations opening graphs: `prepare` doesn't open it.
  - ROADMAP item 94's text matches the diff.
  - The touched tests ran before and after the change by the agent that made it: 223 unit tests with lint and types,
    and the editor category's 35 live checks in a scratch run.

---

## High

## Medium-high

## Medium

## Low-medium

## Low
