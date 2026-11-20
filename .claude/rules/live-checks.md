---
paths:
  - "tests/test_all_tools/**/*"
---

# Live checks

(AGENTS.md, Working on this project, points here.)

**Live checks while working: a scratch run.** A new or changed check is seen failing, then passing, on its own in an
environment built for it, with `alone.run` from a script in the session's scratchpad, never through a run of the whole
suite. **Load the `live-check` skill before writing or running a live check, and for the final check:**
`.claude/skills/live-check/SKILL.md` has `alone.run`, the order, what a scratch run can't prove, what to do when the
final check fails, and the suites.
