# Substance Designer MCP: install guide

Lets Claude Code (or any MCP client) drive a running **Adobe Substance 3D Designer**:
run Python with the full `sd` API inside Designer, build/modify graphs, and render
the result with Designer's own `sbscooker` / `sbsrender`. No Automation Toolkit
(`pysbs`) is needed.

Tested with Designer 16.0.7 on macOS. Windows uses the same code; the paths below
are the Windows defaults.

## What's in this folder

```
substance-designer-mcp/
├── install.py                 one-step installer (macOS + Windows)
├── plugin/sd_bridge/          Designer plugin (runs inside Designer)
├── mcp_server/                MCP server (server.py), designer_helpers.py (code it sends
│                              into Designer for inspection/previews), requirements.txt
├── client/sd_run.py           tiny CLI to run a script in Designer without MCP
├── examples/                  build_dwarf_trimsheet.py (full example graph)
├── tests/test_all_tools.py    end-to-end self-test of every MCP tool
├── INSTRUCTIONS.md            this file
└── AGENTS.md                  notes for the AI agent using these tools
```

How it fits together:

```
Claude Code ──stdio──> mcp_server/server.py ──TCP 127.0.0.1:9877──> sd_bridge plugin (inside Designer)
                               └──> sbscooker / sbsrender (Designer's command-line tools)
```

## Tools provided

| Tool | What it does |
|---|---|
| `designer_status` | Bridge state, Designer version, open packages and graphs |
| `cancel_designer_job` | Aborts the script running in Designer |
| `launch_designer` | Starts Designer if it isn't running and waits for the bridge |
| `screenshot_designer` | Image of Designer's window or one panel (graph, 2D view, 3D view, properties…). Only Designer is captured, never other apps. The 3D view uses Designer's own render and briefly uses the clipboard, then restores what was on it |
| `save_package` | Saves an open package, optionally under a new path |
| `export_outputs` | Exports a graph's outputs straight from Designer (current, unsaved state) |
| `describe_node` | A node type's connectors, parameters, types, defaults and enum values |
| `describe_graph` | A graph's nodes, connections and (optionally) non-default parameters |
| `preview_node` | Computes the graph and returns any node's image |
| `search_nodes` | Finds node types across built-in nodes and Designer's whole library |
| `open_graph` | Opens a graph in Designer's editor, optionally centred on a node |
| `create_graph`, `move_nodes` | New empty graph; reposition nodes |
| `add_node`, `set_params`, `connect`, `disconnect`, `delete_nodes` | Quick graph edits without writing a script (one undo step each) |
| `execute_designer_code` | Runs Python inside Designer (one undo step per call, timeout 120 s by default) |
| `run_designer_script` | Runs a `.py` file inside Designer (one undo step per call, timeout 600 s by default) |
| `sbsar_info` | Lists a package's graphs, exposed inputs and outputs |
| `render_sbs` | Cooks a `.sbs` and exports outputs. Optional graph, outputs, parameter values, size and file format |
| `preview_maps` | Returns rendered PNGs side by side as an image |

The server also sends `AGENTS.md` to the agent as its instructions (and as resource
`designer://agents-guide`). Keep AGENTS.md next to `mcp_server/`.

## Requirements

- Substance 3D Designer 14.1 or newer (the plugin uses PySide6 and the `sd` API)
- Python **3.10+** on the machine (only for the MCP server; the plugin uses Designer's own Python)
- Claude Code (`claude` command) if you want automatic registration

## Install

Copy this folder wherever you want to keep it, for example `~/Tools/substance-designer-mcp`
or `C:\Tools\substance-designer-mcp`. The MCP server's environment is created inside it,
so pick a permanent location.

### macOS

```bash
cd ~/Tools/substance-designer-mcp
python3 install.py
```

### Windows (PowerShell)

```powershell
cd C:\Tools\substance-designer-mcp
py -3 install.py
```

If `py` isn't available, use the full path to a Python 3.10+ `python.exe`.

### What the installer does

1. Copies `plugin/sd_bridge` into Designer's user plugin folder:
   - macOS: `~/Documents/Adobe/Adobe Substance 3D Designer/python/sduserplugins/`
   - Windows: `%USERPROFILE%\Documents\Adobe\Adobe Substance 3D Designer\python\sduserplugins\`

   If your Documents folder is redirected (OneDrive, for example), check
   **Edit > Preferences > Projects > Python > Plugin paths** in Designer, then pass
   that folder: `python install.py --plugins-dir "<that folder>"`.
2. Creates `mcp_server/venv` and installs `mcp`, `pillow` and `numpy`.
3. Runs `claude mcp add --scope user substance-designer -- <venv python> <server.py>`.
   Use `--no-register` to skip this step; the installer then prints the command so you
   can run it yourself or adapt it for another MCP client.

### After installing

1. **Restart Substance Designer.** The plugin loads at startup. Don't also load it
   from Tools > Plugin Manager: a second copy can't open the port, and it just logs
   a note and stays inactive.
2. Check the Designer console (Windows > Console) for
   `[sd_bridge] listening on 127.0.0.1:9877`.
3. **Restart Claude Code**, then run `claude mcp list`. It should show
   `substance-designer: ... ✔ Connected`.

## Manual install (without install.py)

1. Copy `plugin/sd_bridge` (the folder containing `pluginInfo.json`) into the
   plugin folder listed above.
2. Create a venv and install the requirements:
   ```bash
   python3 -m venv mcp_server/venv                                     # Windows: py -3 -m venv mcp_server\venv
   mcp_server/venv/bin/pip install -r mcp_server/requirements.txt      # Windows: mcp_server\venv\Scripts\pip ...
   ```
3. Register it:
   ```bash
   claude mcp add --scope user substance-designer -- <abs path to venv python> <abs path to mcp_server/server.py>
   ```

## Self-test

With Designer running, check that every tool works end to end (about a minute):

```bash
mcp_server/venv/bin/python tests/test_all_tools.py        # macOS
mcp_server\venv\Scripts\python tests\test_all_tools.py   # Windows
```

It talks to the server over a real MCP connection, builds a temporary graph
(`mcp_selftest`), checks every tool including error cases, then removes the graph and
reopens whatever graph you had open. It never triggers Undo, and it doesn't touch your
packages. The 3D screenshot check is skipped if no 3D View is visible, and the clipboard
check runs only on macOS. It exits with code 0 when everything passes and 1 otherwise.

Run it after installing, after updating the server or plugin, and after a Designer update.

## Configuration (optional environment variables)

| Variable | Default | Used by |
|---|---|---|
| `SD_DESIGNER_BIN_DIR` | macOS: `/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app/Contents/MacOS`; Windows: `C:\Program Files\Adobe\Adobe Substance 3D Designer` | MCP server, to find `sbscooker` / `sbsrender` |
| `SD_DESIGNER_APP` | macOS: `/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app`; Windows: `C:\Program Files\Adobe\Adobe Substance 3D Designer\Adobe Substance 3D Designer.exe` | MCP server, for `launch_designer` |
| `SD_BRIDGE_PORT` | `9877` | plugin, MCP server and CLI client (set the same value for all three) |

To pass variables to the MCP server, add them when registering:
`claude mcp add --scope user -e SD_DESIGNER_BIN_DIR="D:\Adobe\Designer" substance-designer -- ...`

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
- Every request must include the secret in `~/.sd_bridge_token` (Windows:
  `%USERPROFILE%\.sd_bridge_token`). The plugin creates this file on first run, with
  owner-only permissions on macOS.
- Anything that can read that file can run code inside Designer. To rotate it, delete
  the file and restart Designer.
- Changes made by `execute_designer_code`, `run_designer_script` and the quick edit tools
  form one undo step each ("Claude: ..."). Undo history is per document, so Ctrl+Z with that
  graph in focus reverts a whole run.
- To turn the bridge off, disable it in Tools > Plugin Manager, or delete the
  `sd_bridge` folder from the plugin directory.

## Uninstall

```bash
claude mcp remove substance-designer -s user
```
Then delete the `sd_bridge` folder from the plugin directory, `~/.sd_bridge_token`,
and this folder.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No bridge token found` | The plugin has never run. Restart Designer and check the console. |
| `Designer is not reachable` | Designer isn't running, or the plugin failed to load. Check the Designer log. |
| Bridge accepts connections but never answers | The plugin code was replaced while running (for example by a hot reload). Restart Designer. |
| `Address already in use` in the Designer log | The plugin was loaded twice, or another app uses port 9877. Restart Designer, or change `SD_BRIDGE_PORT`. |
| `sbscooker/sbsrender not found` | Set `SD_DESIGNER_BIN_DIR` (see Configuration). |
| MCP shows `Failed to connect` | Run `<venv python> mcp_server/server.py` by hand to see the error. Usually the Python version is too old or the venv is missing. |

Designer log file:
- macOS: `~/Library/Application Support/Adobe/Adobe Substance 3D Designer/<version>/log.txt`
- Windows: under `%LOCALAPPDATA%\Adobe\Adobe Substance 3D Designer\` (version subfolder). The
  same messages also appear in Designer's Console window.

## Credits

The `open_graph` editor calls (`openResourceInEditor`, `focusGraphNode`), node-type
listing via `getNodeDefinitions()` and the validate-before-`newNode` safeguard were learned from
[matthieuhuguet/substance-designer-mcp](https://github.com/matthieuhuguet/substance-designer-mcp)
(MIT). No code was copied; this project's implementation is independent.
