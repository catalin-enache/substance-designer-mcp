# REVIEW.md: review findings

Findings from code reviews of this repository, kept across reviews. A new review **appends** its
findings to the matching severity section and adds itself to the log; it never removes or
rewrites existing entries. An entry is checked when it is resolved: fixed, or answered (not a
bug, not reproduced, won't fix), always with a resolution line. Format and rules:
`.claude/skills/project-code-review/` (SKILL.md, this template).

**Confidence.**
- *Confirmed*: the defect is visible in the code as quoted.
- *Plausible*: the code path exists, but whether it bites depends on Designer, the OS or timing.
- *Verified by hand*: checked against the code after the review, not only by the reviewer.

**IDs.** One prefix per area, numbered on: **PLG** plugin and bridge protocol, **SRV**
`mcp_server/server.py` and `server_tools/`, **HLP** `mcp_server/designer_helpers/`, **INS** installer, uninstaller,
command-line client and example, **TST** tests and docs. A new area gets a new prefix, added here.

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

<!-- One entry per review, newest last. -->

### YYYY-MM-DD: <scope, e.g. whole project> at `<commit>`

- **How:** <who reviewed which areas; read-only; test results at the time>.
- **Resolutions assessed:** <earlier resolved entries checked; which hold up, and which were
  questioned (by which new ID)>.
- **Findings:** <IDs added, with counts per severity; duplicates merged>.
- **Suggested order:** <optional: which findings to address first, and why>.
- **Simplifications:** <optional: worthwhile refactors that aren't defects>.
- **Checked and found fine:** <what was examined and holds, so the next review needn't redo it>.

---

## High

<!-- Each finding is one list item starting with a checkbox. Unchecked = open. -->

- [ ] **ID · One-line title of the defect** · `path/to/file.py:line-line` · confirmed | plausible (· verified by hand) · found YYYY-MM-DD
  - **Defect.** What is wrong, in one or two sentences, quoting the code where it helps.
  - **Scenario.** Concrete inputs or state, and what goes wrong for the user or the agent.
  - **Fix.** The suggested fix.

- [x] **ID · Title of a resolved finding** · `path:line` · confirmed · found YYYY-MM-DD
  - **Defect.** …
  - **Scenario.** …
  - **Fix.** …
  - **Resolution: done | not a bug | not reproduced | won't fix** (commit `abc1234`).
    <!-- A finding that questions an earlier resolution adds "· follows ID, generation N" to its
         title line (SKILL.md, Follow-up chains). -->

    - **Test:** the test that reproduced it, and how it failed (or showed it doesn't happen).
    - **Cause:** why the code failed: the root cause, not the symptom. (When fixed.)
    - **Fix:** how it was fixed: what changed, and where. (When fixed.)
    - **Also covered:** the same pattern searched for elsewhere, and what was found. (When fixed.)
    - **Why not:** why it doesn't happen, with the evidence. (When false.)

## Medium-high

## Medium

## Low-medium

## Low
