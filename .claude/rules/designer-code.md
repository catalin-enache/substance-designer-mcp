---
paths:
  - "mcp_server/**/*"
  - "plugin/**/*"
  - "client/**/*"
  - "project_constants.py"
  - "designer_preferences.py"
  - "tests/test_all_tools/common.py"
---

# The server, the helpers, the plugin and the bridge

How the code that reaches Designer is laid out, and how a change reaches it (AGENTS.md, Deploying and diagnosing,
points here). How they fit together: README.md, How it works.

- **How changes reach Designer:** `server.py`, `server_tools/`, `designer_helpers/`, `designer_rollback.py` and
  `designer_preferences.py` changes take effect when the MCP server restarts. The server reads the helpers and the
  rollback once. It sends the helpers with the calls that use them, and the rollback with each call it wraps in an
  undo step and with `undo_edits`. The user reconnects in `/mcp`, or test with a fresh MCP client such
  as the self-test. **Plugin** changes must be copied into Designer's plugin folder (re-run `install.py`; paths in
  README.md, Install) and need a **Designer restart**: for a Designer an agent started, `quit_designer` then
  `launch_designer` without asking (say that you did); for the user's, ask them to save, close and reopen it.
- **The helpers** (`mcp_server/designer_helpers/`) are parts joined into one script (README.md, How it works). A part
  imports what it uses from other parts (`from .core import find_graph`), for PyCharm and readers; `part_source()` drops
  those lines. `tests/unit/test_designer_helpers.py` fails on a missing, extra or misplaced import, a name no part
  defines, and a part file not in `PARTS`. Code needing the helpers' text takes it from `designer_helpers.source()`,
  never from one file. A part that takes only the standard library's names from the others (`state3d`) also runs
  outside Designer, as a module of its own: `designer_helpers.standalone()`, for its unit tests and the self-test's
  checks of it.
- **The server** (`mcp_server/server.py`) only starts it and re-exports the names of `mcp_server/server_tools/`, one
  module per area (`core` holds the bridge and the `_tool` decorator; a new module goes into `MODULES` in its
  `__init__.py`). Its unit tests patch a name with `patch_server` (`.claude/rules/unit-tests.md`).
- The server (`server_tools/core.py`) loads the guide from `mcp_server/GUIDE.md`: keep it there. Its
  instructions (`INSTRUCTIONS` in `server_tools/core.py`) must stay under 4,096 characters, and every tool but
  `cancel_designer_job` refuses to run until `get_guide()` has been called in the session, and the two code tools until
  `get_guide('scripting')` has too (unit tests check them).
- **The bridge protocol** is defined in the plugin's docstring. `server_tools/core.py`, `client/sd_run.py` and the
  self-test's `raw_request` (`tests/test_all_tools/common.py`) all speak it: change them together with the plugin,
  and raise `BRIDGE_PROTOCOL` (`project_constants.py`) and the plugin's `PROTOCOL` with any change to it. Its messages' types (`Request`,
  `Reply`, `Greeting`) are defined once, in `project_constants.py`; the plugin, which can't import it, has its own
  `Reply` and reads requests as plain JSON.
- **The plugin's name** (`sd_claude_bridge_kve`, also its folder names and the token file
  `~/.sd_claude_bridge_kve_token`) is defined once, in `project_constants.py`; the plugin takes it from its own folder.
  To rename: change `PLUGIN` there, rename both `plugin/<name>` folders, update README.md, GUIDE.md and this file, and
  add the old name to `install.py`'s clean-up of old copies. `tests/unit/test_constants.py` fails on anything missed.
- Environment variables `SD_DESIGNER_BIN_DIR`, `SD_DESIGNER_APP`, `SD_DESIGNER_LOG`, `SD_SNAPSHOT_DIR`,
  `SD_BRIDGE_PORT`: README.md, Configuration. A port change must reach the plugin (Designer's environment) and the
  server alike.
