# Substance Designer MCP

Lets Claude Code (or any MCP client) drive a running **Adobe Substance 3D Designer**: run
Python with the full `sd` API inside Designer, build and edit graphs, preview and measure any
node, take screenshots of Designer's panels (including the 3D view), expose parameters, and
render or export the results. No Automation Toolkit (`pysbs`) needed.

Tested with Designer 16.0.7 on macOS. Windows uses the same code with Windows default paths,
but hasn't been tested yet.

```
Claude Code ──stdio──> mcp_server/server.py ──TCP 127.0.0.1:9877──> sd_bridge plugin (inside Designer)
                               └──> sbscooker / sbsrender (Designer's command-line tools)
```

**Documents:** this README is for people (what it does, install, configure, troubleshoot).
[AGENTS.md](AGENTS.md) is for the AI agent (which tool when, workflow, Designer pitfalls); the
server sends it to the agent automatically. Each tool's exact parameters are in its description
in `mcp_server/server.py`.

## What you can ask for

Once installed, ask Claude things like "build a trim sheet for this reference", "why does this
node look wrong?", "expose the wear amount and render three variations", or "show me the
material in the 3D view". [examples/build_dwarf_trimsheet.py](examples/build_dwarf_trimsheet.py)
is a full example: a 2048² stone + wood trim sheet built entirely through this bridge.

## Tools (29)

| Area | Tools |
|---|---|
| Connection | `designer_status`, `launch_designer` (starts Designer and waits for it), `cancel_designer_job` |
| Finding nodes | `search_nodes` (built-in nodes and Designer's whole library), `describe_node` (parameters, types, dropdown values) |
| Inspecting | `describe_graph`, `list_graph_inputs`, `preview_node` (image of any node), `node_stats` (exact pixel numbers) |
| Viewing | `screenshot_designer` (window, graph, 2D view, 3D view, panels; only Designer is captured, never other apps), `open_graph` (open a graph, centred on a node) |
| Editing | `add_node`, `set_params`, `connect`, `disconnect`, `move_nodes`, `delete_nodes`, `apply_edits` (many edits at once), `create_graph`, `set_graph_size` |
| Controls | `expose_param`, `remove_graph_input` (turn node parameters into graph inputs) |
| Scripting | `execute_designer_code`, `run_designer_script` (with timeout) |
| Output | `save_package`, `export_outputs` (straight from Designer), `sbsar_info`, `render_sbs` (parameters, size, PNG/EXR…), `preview_maps` |

Every change Claude makes through these tools is **one undo step** in Designer ("Claude: …"),
so Ctrl+Z with that graph in focus reverts it. Undo history is per document.

## Requirements

- Substance 3D Designer 14.1 or newer
- Python **3.10+** (only for the MCP server; the plugin uses Designer's own Python)
- Claude Code (`claude` command) for automatic registration, or any MCP client

## Install

Put this folder somewhere permanent (the server's Python environment is created inside it),
for example `~/Tools/substance-designer-mcp` or `C:\Tools\substance-designer-mcp`, then:

```bash
python3 install.py          # macOS
py -3 install.py            # Windows (PowerShell); or the full path to a Python 3.10+ python.exe
```

The installer:

1. Copies `plugin/sd_bridge` into Designer's user plugin folder:
   - macOS: `~/Documents/Adobe/Adobe Substance 3D Designer/python/sduserplugins/`
   - Windows: `%USERPROFILE%\Documents\Adobe\Adobe Substance 3D Designer\python\sduserplugins\`

   If your Documents folder is redirected (OneDrive, for example), check
   **Edit > Preferences > Projects > Python > Plugin paths** in Designer and pass that folder:
   `python install.py --plugins-dir "<that folder>"`.
2. Creates `mcp_server/venv` and installs `mcp`, `pillow` and `numpy`.
3. Registers the server with Claude Code (user scope). With `--no-register` it prints the
   command instead, so you can run it yourself or adapt it for another MCP client.

Then:

1. **Restart Substance Designer** (the plugin loads at startup). Don't also load it from
   Tools > Plugin Manager; a second copy can't open the port and stays inactive.
2. Check Designer's console (Windows > Console) for `[sd_bridge] v2 listening on 127.0.0.1:9877`.
3. **Restart Claude Code** and run `claude mcp list`: it should show `substance-designer: … ✔ Connected`.

<details>
<summary>Manual install (without install.py)</summary>

1. Copy `plugin/sd_bridge` (the folder containing `pluginInfo.json`) into the plugin folder above.
2. Create the environment:
   ```bash
   python3 -m venv mcp_server/venv                                  # Windows: py -3 -m venv mcp_server\venv
   mcp_server/venv/bin/pip install -r mcp_server/requirements.txt   # Windows: mcp_server\venv\Scripts\pip ...
   ```
3. Register it:
   ```bash
   claude mcp add --scope user substance-designer -- <abs path to venv python> <abs path to mcp_server/server.py>
   ```
</details>

## Self-test

With Designer running, check every tool end to end (about a minute):

```bash
mcp_server/venv/bin/python tests/test_all_tools.py        # macOS
mcp_server\venv\Scripts\python tests\test_all_tools.py   # Windows
```

It builds a temporary graph (`mcp_selftest`), checks every tool including error cases, removes
the graph and reopens the graph you had open. It never triggers Undo and doesn't touch your
packages. The 3D screenshot check is skipped if no 3D View is visible; the clipboard check runs
on macOS only. Exit code 0 means everything passed. Run it after installing, after updates, and
after a Designer update.

## Configuration (optional environment variables)

| Variable | Default | Used for |
|---|---|---|
| `SD_DESIGNER_BIN_DIR` | macOS: `/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app/Contents/MacOS`; Windows: `C:\Program Files\Adobe\Adobe Substance 3D Designer` | finding `sbscooker` / `sbsrender` |
| `SD_DESIGNER_APP` | macOS: `/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app`; Windows: `C:\Program Files\Adobe\Adobe Substance 3D Designer\Adobe Substance 3D Designer.exe` | `launch_designer` |
| `SD_BRIDGE_PORT` | `9877` | plugin, MCP server and CLI client (set the same value for all three) |

Pass them when registering: `claude mcp add --scope user -e SD_DESIGNER_BIN_DIR="D:\Adobe\Designer" substance-designer -- ...`

## Using it without MCP

```bash
python client/sd_run.py my_script.py          # run a file inside Designer
python client/sd_run.py -c "print('hello')"   # run a snippet
python client/sd_run.py long.py --timeout 60  # abort after 60 s
python client/sd_run.py --status              # idle / running
python client/sd_run.py --cancel              # abort the running script
```

## Security

- The plugin only listens on `127.0.0.1`, so other machines can't reach it.
- Every request must carry the secret in `~/.sd_bridge_token` (Windows:
  `%USERPROFILE%\.sd_bridge_token`), created by the plugin on first run (owner-only on macOS).
  Anything that can read that file can run code inside Designer. To rotate it, delete the file
  and restart Designer.
- Screenshots only ever capture Designer's own panels. The 3D view uses Designer's own render
  through the clipboard and puts back whatever was on your clipboard.
- To turn the bridge off, disable it in Tools > Plugin Manager or delete the `sd_bridge`
  folder from the plugin directory.

## Uninstall

```bash
claude mcp remove substance-designer -s user
```

Then delete the `sd_bridge` folder from the plugin directory, `~/.sd_bridge_token`, and this folder.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No bridge token found` | The plugin has never run. Restart Designer and check its console. |
| `Designer is not reachable` | Designer isn't running, or the plugin failed to load. Check the Designer log. |
| Bridge accepts connections but never answers | The plugin code was replaced while running (for example by a hot reload). Restart Designer. |
| `Address already in use` in the Designer log | The plugin was loaded twice, or another app uses port 9877. Restart Designer, or change `SD_BRIDGE_PORT`. |
| `sbscooker/sbsrender not found` | Set `SD_DESIGNER_BIN_DIR`. |
| MCP shows `Failed to connect` | Run `<venv python> mcp_server/server.py` by hand to see the error (usually Python too old or the venv missing). |
| New tools don't show up in Claude Code | Reconnect `substance-designer` in `/mcp`, or restart Claude Code. |

Designer log (every plugin traceback ends up here):
- macOS: `~/Library/Application Support/Adobe/Adobe Substance 3D Designer/<version>/log.txt`
- Windows: under `%LOCALAPPDATA%\Adobe\Adobe Substance 3D Designer\` (version subfolder).
  The same messages appear in Designer's Console window.

## Credits

The `open_graph` editor calls (`openResourceInEditor`, `focusGraphNode`), node-type listing via
`getNodeDefinitions()` and the validate-before-`newNode` safeguard were learned from
[matthieuhuguet/substance-designer-mcp](https://github.com/matthieuhuguet/substance-designer-mcp)
(MIT). No code was copied; this project's implementation is independent.

## License

MIT, see [LICENSE](LICENSE). Not affiliated with or endorsed by Adobe; Substance 3D Designer is
a trademark of Adobe.
