# Substance Designer MCP

Lets Claude Code (or any MCP client) drive a running **Adobe Substance 3D Designer**: run
Python with the full `sd` API inside Designer, build and edit graphs, preview and measure any
node, take screenshots of Designer's panels (including the 3D view), expose parameters, and
render or export the results. No Automation Toolkit (`pysbs`) needed.

Tested with Designer 16.0.7 on macOS. Windows uses the same code with Windows default paths,
but hasn't been tested yet. How the pieces fit together: [How it works](#how-it-works).

**Documents:** this README is for people (what it does, install, configure, troubleshoot).
[AGENTS.md](AGENTS.md) is for the AI agent (which tool when, workflow, Designer pitfalls); the
server sends it to the agent automatically. Each tool's exact parameters are in its description
in `mcp_server/server.py`.

## What you can ask for

Once installed, ask Claude things like "build a trim sheet for this reference", "why does this
node look wrong?", "expose the wear amount and render three variations", or "show me the
material in the 3D view". [examples/build_dwarf_trimsheet.py](examples/build_dwarf_trimsheet.py)
is a full example: a 2048² stone + wood trim sheet built entirely through this bridge.

## How it works

There are two programs, plus Designer's own command-line tools:

```
 Claude Code (MCP client)
      │  MCP over stdio: tool calls in, text and images back
      ▼
 MCP server ─ mcp_server/server.py + designer_helpers.py
 (a separate Python 3.10+ process in mcp_server/venv, started by Claude Code)
      │                                         │
      │  JSON over TCP 127.0.0.1:9877            │  runs as needed
      │  (token-signed request: code, timeout)   ▼
      ▼                                     sbscooker / sbsrender
 sd_bridge plugin                           (Designer's command-line tools:
 (inside Designer, in Designer's Python)     .sbs → .sbsar → image files)
      │  runs the code on Designer's main thread
      ▼
 Designer's own Python API (`sd`): graphs, nodes, parameters, rendering, UI
```

| Part | Runs where | What it does |
|---|---|---|
| **sd_bridge plugin** (`plugin/sd_bridge`) | Inside Designer, loaded at startup | A small, generic script runner. It listens on `127.0.0.1:9877`, checks that each request is signed with the secret token, queues the Python code it receives, runs it on Designer's main thread (the only place the `sd` API may be used), and sends back the printed output or the error. It also enforces timeouts, answers `status` / `cancel` while a script runs, and knows nothing about MCP or the individual tools. |
| **MCP server** (`mcp_server/server.py`) | Its own process, started by Claude Code | Defines the 43 tools Claude sees. Its instructions to Claude are one short paragraph saying to call `get_guide()` first, which returns the full [AGENTS.md](AGENTS.md) (MCP clients cut long instructions; Claude Code at 4,096 characters). Each tool does one or more of: send Python code to the plugin (most tools), run Designer's command-line tools (`render_sbs`, `sbsar_info`), or do the work itself outside Designer (decoding pixels, building preview images, comparing `.sbs` files, reading the log, editing files for portals). |
| **Designer helpers** (`mcp_server/designer_helpers.py`) | Sent to Designer with each request | The library of functions that actually do the work inside Designer: describing nodes, editing graphs, computing previews, layout, exposing inputs and so on. It's re-sent with every call, so updating it never needs a Designer restart. |
| **sbscooker / sbsrender** | Separate processes | Designer's own tools for compiling a saved `.sbs` into `.sbsar` and rendering its outputs, independently of the open Designer. |
| **CLI client** (`client/sd_run.py`) | Your terminal | The same connection to the plugin without MCP, for running scripts by hand. |
| `install.py`, `tests/` | Your terminal | Installation, the end-to-end self-test, and unit tests that need no Designer (`tests/unit`). |

**One tool call, step by step** (`preview_node`, "show me this node's image"):

1. Claude calls the tool; the MCP server builds a small Python program: the helpers plus a call
   to the preview function, wrapped in a single undo step.
2. The server sends it to the plugin, signed with the token, with a timeout.
3. The plugin queues it, and Designer's main thread runs it: the graph is computed and the node's
   pixels are written to a temporary file.
4. The plugin replies with whatever the program printed (here, the image's size and format).
5. The server reads the temporary file, turns the pixels into a PNG, and returns it to Claude.

**Why it's split this way**

- **The plugin stays tiny and stable.** Every tool lives in the server, so new or improved tools
  only need the MCP connection restarted (`/mcp` in Claude Code), not Designer. The plugin only
  changes for connection-level features, like the timeout/cancel support.
- **Designer stays responsive.** Designer runs plugin code on its UI thread, so anything heavy
  that doesn't need the `sd` API (image decoding, statistics, file comparison) happens in the
  server process instead.
- **It doesn't depend on Designer's Python.** The server uses its own Python environment and
  libraries (`mcp`, `numpy`, `pillow`); the plugin needs nothing beyond what Designer ships.

**When the API can't do something.** A few things aren't reachable through Designer's Python API,
for example showing a connection as a portal. For those, the server edits the saved `.sbs` file
directly and reloads it in Designer, after keeping a snapshot of the graph and a copy of your
saved file (details: [AGENTS.md](AGENTS.md), Portals).

## Tools (43)

| Area | Tools |
|---|---|
| Connection | `get_guide` (the full agent guide; Claude calls it first and confirms), `designer_status`, `launch_designer` (starts Designer and waits for it), `quit_designer` (closes it; refuses while there are unsaved changes), `cancel_designer_job`, `read_designer_log` |
| Finding nodes | `search_nodes` (built-in nodes and Designer's whole library), `describe_node` (parameters, types, ranges, descriptions, dropdown values) |
| Inspecting | `describe_graph`, `list_graph_inputs`, `preview_node` (image of any node), `node_stats` (exact pixel numbers), `check_tiling` (does it tile seamlessly?), `compare_to_reference` (how far a node's tones are from a reference image, in numbers) |
| Tuning | `sweep_param` (try several values of a parameter side by side; the original value is restored) |
| Safety | `snapshot_graph`, `list_snapshots`, `diff_graph` (what changed vs the saved file or a snapshot) |
| Readability | `arrange_graph` (tidy layout by data flow), `add_frame`, `add_comment`, `set_link_display` (show wires as portals to hide clutter; saves and reloads the package after a snapshot) |
| Viewing | `screenshot_designer` (window, graph, 2D view, 3D view, panels; only Designer is captured, never other apps), `open_graph` (open a graph, centred on a node) |
| Editing | `add_node`, `import_bitmap` (image file as a Bitmap node), `set_params`, `connect`, `disconnect`, `move_nodes`, `delete_nodes`, `apply_edits` (many edits at once), `create_graph`, `set_graph_size` |
| Controls | `expose_param`, `remove_graph_input` (turn node parameters into graph inputs) |
| Scripting | `execute_designer_code`, `run_designer_script` (with timeout) |
| Output | `save_package`, `export_outputs` (straight from Designer), `sbsar_info`, `render_sbs` (parameters, size, PNG/EXR…), `preview_maps` |

Every change Claude makes through these tools is **one undo step** in Designer ("Claude: …"),
so Ctrl+Z with that graph in focus reverts it. Undo history is per document. Two exceptions:
`set_link_display` reloads the package, which clears its undo history (a snapshot is kept
instead), and `quit_designer(discard_unsaved=True)` drops unsaved changes for good. Before bigger
changes to your graphs, Claude can take a snapshot and afterwards show you exactly what changed.

## Requirements

- Substance 3D Designer 16 (tested on 16.0.7; 14.1 or newer should work, untested)
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
3. Registers the server with Claude Code (user scope). If it is already registered, it leaves
   that registration (and any `-e` variables you added) as it is. With `--no-register` it prints
   the command instead, so you can run it yourself or adapt it for another MCP client.

**After updating this folder** (`git pull`), re-run the installer and restart Designer: the
plugin and the server must be the same version (an older plugin answers every request with
"invalid token").

Then:

1. **Restart Substance Designer** (the plugin loads at startup). Don't also load it from
   Tools > Plugin Manager; a second copy can't open the port and stays inactive.
2. Check Designer's console (Windows > Console) for `[sd_bridge] v3 listening on 127.0.0.1:9877`.
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

Check every tool end to end against the real Designer (about two minutes). If Designer isn't
running, the self-test starts it and closes it again at the end; if it is running, it's left open:

```bash
mcp_server/venv/bin/python tests/test_all_tools.py        # macOS
mcp_server\venv\Scripts\python tests\test_all_tools.py   # Windows
```

It builds a temporary graph (`mcp_selftest`), checks every tool including error cases, removes
the graph and reopens the graph you had open. It doesn't touch your packages. To check that
one change is one undo step it triggers Undo and Redo, but only while its own graph is the one
in the editor; it skips that check otherwise. It also re-checks the Designer behaviour the
agent notes rely on ("designer facts"), so a Designer update that changes it shows up, and it
checks the Security promises below (unsigned, wrongly signed and old-style requests refused, not
reachable from the network, private token file), the command-line client, that the plugin Designer loaded matches
this repo (re-run `install.py` if not), and that the example trim sheet still builds (a renamed
copy, so a trim sheet you have open is never touched). The 3D screenshot check is skipped if no 3D View is visible; the clipboard check runs
on macOS only. Exit code 0 means everything passed. Run it after installing, after updates, and
after a Designer update.

**Unit tests (no Designer needed).** `tests/unit` tests everything that can run outside
Designer: the plugin's server and authentication (with Qt replaced), the clients' protocol,
pixel decoding, image comparison, the tiling metric, `.sbs` parsing, diffing and portal
selection, render command building, search ranking, the installer, launch/quit edge cases,
environment variables and log reading. It also checks that this README lists every tool and that
the self-test exercises every tool, parameter and `apply_edits` op. Run them after any change:

```bash
mcp_server/venv/bin/pip install pytest
mcp_server/venv/bin/python -m pytest
```

## Configuration (optional environment variables)

| Variable | Default | Used for |
|---|---|---|
| `SD_DESIGNER_BIN_DIR` | macOS: `/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app/Contents/MacOS`; Windows: `C:\Program Files\Adobe\Adobe Substance 3D Designer` | finding `sbscooker` / `sbsrender` |
| `SD_DESIGNER_APP` | macOS: `/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app`; Windows: `C:\Program Files\Adobe\Adobe Substance 3D Designer\Adobe Substance 3D Designer.exe` | `launch_designer` |
| `SD_DESIGNER_LOG` | newest `log.txt` in Designer's settings folder (see Troubleshooting) | `read_designer_log` |
| `SD_SNAPSHOT_DIR` | `~/.sd_mcp/snapshots` | where `snapshot_graph` keeps snapshots (one folder per graph; safe to delete) |
| `SD_BRIDGE_PORT` | `9877` | plugin, MCP server and CLI client (set the same value for all three; the plugin reads it from Designer's environment, so start Designer from a shell where it is set, or set it system-wide) |

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
- Every request must be signed with the secret in `~/.sd_bridge_token` (Windows:
  `%USERPROFILE%\.sd_bridge_token`): the plugin sends a random challenge and the client answers
  with an HMAC of it, so the secret itself never crosses the connection, and a program posing as
  the plugin while Designer is closed learns nothing it can reuse.
- The plugin creates the token on first run, owner-only on macOS (it also tightens an existing
  file's permissions), and replaces an empty or truncated one. Anything that can read that file
  can run code inside Designer. To rotate it, delete the file and restart Designer.
- Requests are size- and time-limited, malformed ones get no details back, and on Windows the
  port is bound exclusively so a second program can't share it.
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
| Every call returns `invalid token` | The plugin and the server are different versions (for example after `git pull`): re-run `install.py` and restart Designer. |
| Bridge accepts connections but never answers | The plugin code was replaced while running (for example by a hot reload). Restart Designer. |
| `Address already in use` in the Designer log | The plugin was loaded twice, or another app uses port 9877. Restart Designer, or change `SD_BRIDGE_PORT`. |
| `sbscooker/sbsrender not found` | Set `SD_DESIGNER_BIN_DIR`. |
| MCP shows `Failed to connect` | Run `<venv python> mcp_server/server.py` by hand to see the error (usually Python too old or the venv missing). |
| New tools don't show up in Claude Code | Reconnect `substance-designer` in `/mcp`, or restart Claude Code. |

Designer log (every plugin traceback ends up here; Claude can read it with `read_designer_log`):
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
