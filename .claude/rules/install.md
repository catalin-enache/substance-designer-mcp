---
paths:
  - "install.py"
  - "uninstall.py"
  - ".mcp.json"
---

# The installer and the registration

(AGENTS.md, Deploying and diagnosing, points here.)

**Registration is per folder, never global, for now** (README.md, "Where the tools are available"; ROADMAP item 5
will make global registration the installer's choice): this repo's committed `.mcp.json`, or
`claude mcp add --scope local` in another folder. The installer never registers; it writes a user skill (`skill_text`
in `install.py`) telling sessions elsewhere how to register, and `uninstall.py` removes the skill, the plugin, the
token, every folder's local registration and a user-scope one (only entries running this repo's `server.py`).
`.mcp.json` must not contain `${`: Claude Code expands those itself (it once rewrote a shell default away), so its
`sh -c` command uses plain `$VARS` (`tests/unit/test_mcp_json.py`).
