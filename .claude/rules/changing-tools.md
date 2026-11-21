---
paths:
  - "mcp_server/server_tools/**/*"
  - "mcp_server/designer_helpers/**/*"
---

# Changing the tools

(AGENTS.md, Working on this project, points here.)

**Load the `mcp-builder` skill** (`.claude/skills/mcp-builder/`: Anthropic's, from `anthropics/skills` at `ca45fc4`,
trimmed to its Python parts) before designing or changing tools (adding, merging or removing one, its parameters,
description, errors or results), and for evaluations. Where it differs from AGENTS.md, a rule or skill AGENTS.md points
to, or this file, they win. Its defaults this project doesn't follow: comprehensive API coverage and service-prefixed
names (few tools, unprefixed; node edits are `apply_edits` ops; a new capability is a parameter or op of an existing
tool where it fits, else a new tool rather than an existing one complicated with completely different logic: ROADMAP.md
"Fewer tools"); JSON results (they are compact text for agents); Pydantic input models (inputs are typed parameters).
Its code is for mcp 1.x; this server runs mcp 2.x (the note at the top of its `SKILL.md`).

**A new tool declares its four MCP hints in its registration:** `_tool()`'s `read_only`, `destructive`, `idempotent`
and `open_world`, chosen as `_tool()`'s docstring says. It also gets a row in `HINTS`, the table in
`tests/unit/test_server.py`.

**A new parameter gets its description in its annotation:** `Annotated[<its type>, Field(description='...')]`, its
default kept as the Python default, or the shared `Graph`, `Output` or `Port` of `server_tools/core.py`. What goes in
the description and what stays in the docstring: `.claude/rules/docs.md`, the table. **A tool's description stays
within what Claude Code keeps** of a tool loaded at the session's start (`CLAUDE_CODE_LIMIT`). Both are held by tests
in `tests/unit/test_server.py`.
