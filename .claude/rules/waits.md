---
paths:
  - "mcp_server/**/*.py"
  - "plugin/**/*.py"
  - "client/**/*.py"
  - "examples/**/*.py"
  - "tests/**/*.py"
  - "scripts/**/*.py"
  - "designer_preferences.py"
---

# Waiting for Designer, Qt or the OS

(AGENTS.md, Working on this project, points here.)

**Wait for callbacks, never for measured times.** Code that waits for Designer, Qt or the OS waits for the callback
that says the thing happened. That covers the tools, the helpers and the tests, for things like a window shown, the 3D
view drawn, a menu open or a process gone. A callback can be a Qt signal, an event seen by an event filter, or a
notification of the API.
- **Hunt for one** when you don't know of any, before writing a wait. Look at the object's signals, at the events an
  event filter logs as the thing happens, at what its widgets show (a label, a count), and at the API.
- **Poll the state every 100 ms** only where no callback exists.
- **Give either wait a limit,** so it ends if the callback never comes. The limit is a safety net, never the time the
  wait is expected to take.
- **Never wait a time measured here:** no fixed sleep, and no margin after a state. Another machine, or the same one
  under another load, takes longer or shorter.
- **The exceptions the user chose** (the user, 2026-11-20):
  - the 30 ms between two jobs, `WAKE_DELAY_MS` in the plugin, for which no callback was found (DECISIONS.md, "No job
    starts sooner than 30 ms after the one before ended");
  - the 300 ms before an older plugin's quit closes Designer's windows, where no reply callback exists to wait on
    (`mcp_server/designer_helpers/quit.py`; REVIEW.md SRV-151);
  - the 0.5 s and 1 s the self-test's click and window-under facts wait after a window is shown or its look is set,
    before they read what macOS reports: they time macOS's covered state on purpose
    (`tests/test_all_tools/editor_panels_and_fit/window_states.py`; REVIEW.md TST-412).

Measuring what Designer does in each case still comes first (AGENTS.md, Start with the tests): what happens, not how
long it takes.
