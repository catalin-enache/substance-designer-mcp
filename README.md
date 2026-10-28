# Substance Designer MCP

Lets Claude Code (or any MCP client) drive a running **Adobe Substance 3D Designer**: run
Python with the full `sd` API inside Designer, build and edit graphs, preview any node, take
screenshots of Designer's panels (including the 3D view), and render or export the results.
No Automation Toolkit (`pysbs`) needed. Works on macOS; Windows support is written but untested.

```
Claude Code ──stdio──> mcp_server/server.py ──TCP 127.0.0.1:9877──> sd_bridge plugin (inside Designer)
                               └──> sbscooker / sbsrender (Designer's command-line tools)
```

- **[INSTRUCTIONS.md](INSTRUCTIONS.md)**: install (macOS + Windows), the 23 tools, configuration,
  security, self-test, troubleshooting.
- **[AGENTS.md](AGENTS.md)**: notes for the AI agent using the tools (also served as the MCP
  server's instructions).
- **[examples/build_dwarf_trimsheet.py](examples/build_dwarf_trimsheet.py)**: a full generator
  for a 2048² stone + wood trim sheet.

Quick start:

```bash
python3 install.py                              # copies the plugin, creates the venv, registers with Claude Code
# restart Designer, then:
mcp_server/venv/bin/python tests/test_all_tools.py   # end-to-end self-test
```

## License

MIT, see [LICENSE](LICENSE). Not affiliated with or endorsed by Adobe; Substance 3D Designer is a trademark of Adobe.
