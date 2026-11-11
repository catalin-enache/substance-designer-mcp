# Substance Designer MCP

Lets Claude Code (or any MCP client) drive a running **Adobe Substance 3D Designer**: run
Python with the full `sd` API inside Designer, build and edit graphs, preview and measure any
node, take screenshots of Designer's panels (including the 3D view), expose parameters, and
render or export the results. No Automation Toolkit (`pysbs`) needed.

Tested with Designer 16.0.7 on macOS. Windows uses the same code with Windows default paths,
but hasn't been tested yet. How the pieces fit together: [How it works](#how-it-works).

**Documents:** this README is for people (what it does, install, configure, troubleshoot).
[mcp_server/GUIDE.md](mcp_server/GUIDE.md) is for the AI agent driving Designer (which tool when, workflow, Designer
pitfalls), [AGENTS.md](AGENTS.md) for an agent changing this project; the
server serves the guide to the agent through `get_guide`. Each tool's exact parameters are in its description
in `mcp_server/server_tools/`.

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
 MCP server ─ mcp_server/server.py + server_tools/ + designer_helpers/
 (a separate Python 3.10+ process in mcp_server/venv, started by Claude Code)
      │                                         │
      │  JSON over TCP 127.0.0.1:9877            │  runs as needed
      │  (token-signed request: code, timeout)   ▼
      ▼                                     sbscooker / sbsrender
 sd_claude_bridge_kve plugin                (Designer's command-line tools:
 (inside Designer, in Designer's Python)     .sbs → .sbsar → image files)
      │  runs the code on Designer's main thread
      ▼
 Designer's own Python API (`sd`): graphs, nodes, parameters, rendering, UI
```

| Part | Runs where | What it does |
|---|---|---|
| **sd_claude_bridge_kve plugin** (`plugin/sd_claude_bridge_kve`) | Inside Designer, loaded at startup | A small, generic script runner. It listens on `127.0.0.1:9877`, checks that each request is signed with the secret token, queues the Python code it receives, runs it on Designer's main thread (the only place the `sd` API may be used), and sends back the printed output or the error. It also enforces timeouts, answers `status` / `cancel` while a script runs, and knows nothing about MCP or the individual tools. |
| **MCP server** (`mcp_server/server.py`, the entry point; the code in `mcp_server/server_tools/`) | Its own process, started by Claude Code | Defines the 35 tools Claude sees, one module per area (`core.py`: configuration, the bridge connection and the tool decorator; `edits.py`, `views.py`, `output.py`...: the tools). Its instructions to Claude are one short paragraph (MCP clients cut long ones; the limit is in [AGENTS.md](AGENTS.md), Working on this project): leave the Designer tools alone unless you ask for Designer work, and right before the first Designer tool call, call `get_guide()`, which returns the core of [mcp_server/GUIDE.md](mcp_server/GUIDE.md) (`get_guide('scripting')`, the sd API and Qt part, before writing raw code). Sessions started for other things never load the guide. Each tool does one or more of: send Python code to the plugin (most tools), run Designer's command-line tools (`render_sbs`, `sbsar_info`), or do the work itself outside Designer (decoding pixels, building preview images, comparing `.sbs` files, reading the log, editing files for portals). |
| **Designer helpers** (`mcp_server/designer_helpers/`) | Sent to Designer with each request | The library of functions that actually do the work inside Designer: describing nodes, editing graphs, computing previews, layout, exposing inputs and so on. One file per area (`edits.py`, `editor.py`, `screenshots.py`...), joined into one script in the order of `PARTS` in its `__init__.py`, so they share one namespace. Each part imports what it uses from the others (`from .core import ...`) so editors see where names come from; those lines are dropped when the parts are joined. It's re-sent with every call, so updating it never needs a Designer restart. |
| **sbscooker / sbsrender** | Separate processes | Designer's own tools for compiling a saved `.sbs` into `.sbsar` and rendering its outputs, independently of the open Designer. |
| **CLI client** (`client/sd_run.py`) | Your terminal | The same connection to the plugin without MCP, for running scripts by hand. |
| `scripts/review_lookup.py` | Your terminal | Finds a code review finding by its ID, in `REVIEW.md` or its git history. Used by the review skills. |
| `install.py`, `uninstall.py`, `tests/` | Your terminal | Installation (including the Claude Code skill that tells sessions in other folders about the server), clean removal, the end-to-end self-test (on macOS several worker processes at once, each with a Designer and an MCP server of its own: `tests/test_all_tools/workers.py`), and unit tests that need no Designer (`tests/unit`). |

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
  libraries (`mcp`, `numpy`, `pillow`, with tested version ranges in
  `mcp_server/requirements.txt`); the plugin needs nothing beyond what Designer ships.

**When the API can't do something.** A few things aren't reachable through Designer's Python API,
for example showing a connection as a portal. For those, the server edits the saved `.sbs` file
directly and reloads it in Designer, after keeping a snapshot of the graph and a copy of your
saved file (details: [mcp_server/GUIDE.md](mcp_server/GUIDE.md), Portals).

## Tools (35)

| Area | Tools |
|---|---|
| Connection | `get_guide` (the agent guide: its core, which Claude reads before its first Designer tool call and confirms; with `part='scripting'`, the sd API and Qt pitfalls, before writing raw code, confirmed too), `designer_status`, `launch_designer` (starts Designer and waits for it; with `port`, another one side by side on macOS, which `designer_status` and `quit_designer` reach by the same `port`), `quit_designer` (closes one an agent started, dropping unsaved changes; refuses one you opened), `cancel_designer_job`, `read_designer_log` (with `port`, the log of that Designer: each one an agent starts on macOS writes its own) |
| Finding nodes | `search_nodes` (built-in nodes and Designer's library of compositing graphs, its ready-made materials included, the ones it hides on request), `describe_node` (parameters, types, ranges, descriptions, dropdown values) |
| Inspecting | `describe_graph`, `list_graph_inputs`, `preview_node` (image of any node), `node_stats` (exact pixel numbers), `check_tiling` (does it tile seamlessly?), `compare_to_reference` (how far a node's tones are from a reference image, in numbers) |
| Tuning | `sweep_param` (try several values of a parameter side by side; the original value is restored) |
| Safety | `snapshot_graph`, `list_snapshots`, `diff_graph` (what changed vs the saved file or a snapshot) |
| Readability | `arrange_graph` (tidy layout by data flow), `add_frame`, `add_comment`, `set_link_display` (show wires as portals to hide clutter; saves and reloads the package after a snapshot) |
| Viewing | `screenshot_designer` (window, graph, 2D view, 3D view, panels; only Designer is captured, never other apps), `open_graph` (open a graph, fitted whole, zoomed to a frame, nodes or rectangle, or centred on a node) |
| Editing | `apply_edits` (add nodes and image files, set parameters, name and tag output nodes, connect, disconnect, move, delete, expose parameters as graph inputs: one or many edits per call, one undo step; a typo'd node id changes nothing), `create_graph`, `set_graph_size` |
| Controls | `remove_graph_input` (exposing a parameter is `apply_edits`' `expose` op) |
| Scripting | `execute_designer_code`, `run_designer_script` (with timeout and `args`) |
| Output | `save_package`, `export_outputs` (straight from Designer), `sbsar_info`, `render_sbs` (parameters, size, PNG/EXR…), `preview_maps` |

Every change Claude makes through these tools is **one undo step** in Designer ("Claude: …"),
so Ctrl+Z with that graph in focus reverts it. Undo history is per document. Two exceptions:
`set_link_display` reloads the package, which clears its undo history (a snapshot is kept
instead), and `quit_designer` ends only a Designer an agent started, dropping its unsaved changes; yours it refuses, and asks you to save, close and reopen it. Before bigger
changes to your graphs, Claude can take a snapshot and afterwards show you exactly what changed.

## Requirements

- Substance 3D Designer 16 (tested on 16.0.7, which bundles Python 3.13). Older versions aren't supported.
- Python **3.10+** (only for the MCP server; the plugin uses Designer's own Python). 3.10 is the
  minimum the installer accepts; the tests run on 3.12. The installer and `designer_status` show
  which Python the server uses. `install.py` and `uninstall.py` start on an older `python3` (a stock
  Mac's is 3.9): the installer then says it needs 3.10+, and the uninstaller works.
- Claude Code (`claude` command), or any MCP client

## Install

Put this folder somewhere permanent (the server's Python environment is created inside it),
for example `~/Tools/substance-designer-mcp` or `C:\Tools\substance-designer-mcp`, then:

```bash
python3 install.py          # macOS
py -3 install.py            # Windows (PowerShell); or the full path to a Python 3.10+ python.exe
```

The installer:

1. Copies `plugin/sd_claude_bridge_kve` into Designer's user plugin folder:
   - macOS: `~/Documents/Adobe/Adobe Substance 3D Designer/python/sduserplugins/`
   - Windows: `%USERPROFILE%\Documents\Adobe\Adobe Substance 3D Designer\python\sduserplugins\`

   If your Documents folder is redirected (OneDrive, for example), check
   **Edit > Preferences > Projects > Python > Plugin paths** in Designer and pass that folder:
   `python install.py --plugins-dir "<that folder>"`.

   The plugin used to be called `sd_bridge` (token `~/.sd_bridge_token`). If that old copy is
   there and is this project's, the installer removes it and its token, since two copies
   loaded together fight over the port.
2. Creates `mcp_server/venv` and installs `mcp`, `pillow` and `numpy`.
3. Does **not** register the server globally: it prints how to register it per folder (see
   **Where the tools are available** below).
4. Adds a small Claude Code skill, `~/.claude/skills/substance-designer/SKILL.md` (in
   `$CLAUDE_CONFIG_DIR/skills` if you set that), so sessions in other folders know the server
   exists and offer to enable it there. `--no-skill` skips it. A `substance-designer` skill you
   wrote yourself is left alone.

**After updating this folder** (`git pull`), re-run the installer and restart Designer: the
plugin and the server must be the same version. A server newer than the plugin says the two speak
different bridge protocols and sends nothing; an older one gets "invalid token" for every request.

Then:

1. **Restart Substance Designer** (the plugin loads at startup). Don't also load it from
   Tools > Plugin Manager; a second copy can't open the port and stays inactive.
2. Check Designer's console (Windows > Console) for `[sd_claude_bridge_kve] v8 listening on 127.0.0.1:9877`.
3. **Start `claude` in this folder** and approve `substance-designer` when asked (once). Then
   `claude mcp list` here shows `substance-designer: … ✔ Connected`.

### Where the tools are available

The server is never registered globally, so sessions in other folders don't start it or spend
context on it:

- **This folder:** the committed [`.mcp.json`](.mcp.json) registers it for Claude Code started
  here or in any subfolder (it runs `sh`, so macOS and Linux). Claude Code asks once to approve
  it; `claude mcp reset-project-choices` resets that choice.
- **Another folder** (for example a material project): run this there once, with this folder's
  absolute paths (the installer prints the exact command):
  ```bash
  claude mcp add --scope local substance-designer -- <this folder>/mcp_server/venv/bin/python <this folder>/mcp_server/server.py
  ```
  `--scope local` keeps it to that folder and to you. On Windows use this form in this folder
  too (`mcp_server\venv\Scripts\python.exe`), since `.mcp.json` needs `sh`.

  You don't have to remember this: the installer's skill is visible in every folder (only its
  one-line description, a few dozen tokens). Ask for Designer work in a folder without the
  server and Claude offers to run the command, then asks you to restart with `claude --continue`
  (new MCP servers load when a session starts).

<details>
<summary>Manual install (without install.py)</summary>

1. Copy `plugin/sd_claude_bridge_kve` (the folder containing `pluginInfo.json`) into the plugin folder above.
2. Create the environment:
   ```bash
   python3 -m venv mcp_server/venv                                  # Windows: py -3 -m venv mcp_server\venv
   mcp_server/venv/bin/pip install -r mcp_server/requirements.txt   # Windows: mcp_server\venv\Scripts\pip ...
   ```
3. Registration: as in **Where the tools are available**.
</details>

## Self-test

Check every tool end to end against the real Designer. On macOS it runs each category of checks (below) in a Designer
started for it and closed after it, several at once (how many: `--help`), with the unit tests (`pytest`) beside them,
their result one line of its summary: about 3.2 minutes for both, 10.5 one at a time. With a Designer of yours open
it starts nothing and asks you to close it first: they would share its settings. On Windows it is one run in one
Designer, without the unit tests: it starts Designer if none runs and leaves it open at the end, as it leaves yours.

### Running it

From the repository's folder, once `install.py` has made `mcp_server/venv`, with no Designer of yours open (macOS).
The rows that run the unit tests also need their packages, which `install.py` doesn't install:
`mcp_server/venv/bin/pip install -r mcp_server/requirements-dev.txt` (pytest, mypy and ruff).

| To run | Command |
|---|---|
| Both suites, the check before merging into `main` | `mcp_server/venv/bin/python tests/test_all_tools` |
| The live checks alone, without the unit tests | `mcp_server/venv/bin/python tests/test_all_tools --no-unit` |
| Another number of Designers at once (1: one after the other) | `mcp_server/venv/bin/python tests/test_all_tools --workers 2` |
| Chosen categories (below), without the unit tests | `mcp_server/venv/bin/python tests/test_all_tools --only render measure` |
| The unit tests alone | `mcp_server/venv/bin/python -m pytest` |
| Every option | `mcp_server/venv/bin/python tests/test_all_tools --help` |
| Windows: one run of every category but `lifecycle` | `mcp_server\venv\Scripts\python tests\test_all_tools` |

Each Designer takes about 2 GB after a run, and took up to about 11 GB after a heavy compute; four side by side ran
on a 64 GB Mac: with less memory, run fewer at once (`--workers 2`).

`--only` takes one name or more, from the table below; an unknown name is refused with the list. It runs those
categories the same way, each in a Designer of its own, to check one area quickly; it judges only the tools they use,
so before merging, run everything. At the end it prints each category's lines, then one summary: the tools covered,
the checks passed and skipped, and the time per category. Exit code 0: every check that ran passed; 1: a check failed,
or, in a full run, a tool no check exercised; 2: nothing was run (a Designer of yours open, an unknown name, `--only` on Windows).

### The categories

| Category | What it checks |
|---|---|
| `lifecycle` | Quitting and starting Designer, also forced, on other ports, in Designers of its own (the longest, about 3 minutes) |
| `render` | Output: `export_outputs`, `sbsar_info`, `render_sbs` (seeds, sizes, formats) and `preview_maps` |
| `facts` | The Designer behaviour the agent guide relies on, so a Designer update that changes it shows up |
| `safeguards` | Refusals and failure paths: unsaved changes never unloaded, bad node ids, failed restores |
| `graph_edit_wire` | One-op edits: `apply_edits`' connect, disconnect, move and delete |
| `link_display` | `set_link_display`: portals and wires, by node, by link, by fan-out and by length |
| `inputs` | Exposed inputs and graph size: `set_graph_size`, the expose op, `list_graph_inputs`, `remove_graph_input` |
| `params` | `apply_edits`' set op: value types, `$outputsize`, `$format`, `$randomseed` and their inheritance |
| `bridge` | The connection: `designer_status`, `cancel_designer_job`, the bridge's security and job queue, the command-line client |
| `example` | README's full example, the trim sheet, built from a renamed copy |
| `measure` | Measuring: `node_stats`, `sweep_param`, `check_tiling` and `read_designer_log` |
| `lookup` | Finding a graph (same-named graphs, library graphs) and a node with several outputs |
| `discovery` | Finding nodes: `search_nodes` and `describe_node` |
| `editor_open_and_zoom` | The editor: `open_graph`'s targets and zoom, `screenshot_designer('graph')` with crops |
| `bitmaps` | Bitmaps: `apply_edits`' bitmap op and `compare_to_reference` |
| `editor_panels_and_fit` | The editor: every panel's screenshot, the clipboard, `open_graph` fitting the whole graph |
| `graph_edit_create` | `create_graph` and `apply_edits`' add op |
| `layout` | Snapshots, diffs and readable graphs: `snapshot_graph`, `list_snapshots`, `diff_graph`, `arrange_graph` |
| `save` | Saving: `save_package`, snapshots of a saved package, a diff against a `.sbs`, copied bitmaps |
| `graph_edit_output_fields` | Naming and tagging output nodes with `apply_edits` |
| `batch` | Several edits in one `apply_edits` call |
| `undo` | One tool call is one undo step |
| `script_runner` | `run_designer_script` |

A few never run beside some others, `--only` included: `undo` runs last, alone, and `facts` and
`editor_panels_and_fit` never at the same time (both use the clipboard).

### What it checks


It builds temporary graphs (`mcp_selftest`), checks every tool including error cases, and removes
them; in your Designer (Windows) it reopens the graph you had open. It doesn't touch your packages. Its files go in a
temporary folder (`sd_mcp_selftest_...`), deleted once its Designer has closed. On Windows, where Designer stays open,
it is left and its path printed: deleting it while Designer ran crashed Designer twice. Delete it
once Designer is closed (the system may clear old temporary files itself, but don't count on it). To check that
one change is one undo step it triggers Undo and Redo, but only while its own graph is the one
in the editor; it skips that check otherwise. It also re-checks the Designer behaviour the
agent notes rely on ("designer facts"), so a Designer update that changes it shows up, and it
checks the Security promises below (unsigned and wrongly signed requests refused, not
reachable from the network, private token file), the command-line client, that the plugin Designer loaded matches
this repo (re-run `install.py` if not), and that the example trim sheet still builds (a renamed
copy, so a trim sheet you have open is never touched). The screenshot of a panel not visible in your Designer (Windows) is skipped; the clipboard checks run
on macOS only: they use your clipboard for a few seconds, then put your text back (only the text). Exit code 0 means everything that ran passed; the summary lists tools whose checks
were all skipped (`quit_designer` on Windows) instead of counting them as
covered. Run it after installing, after updates, and
after a Designer update (`--no-unit` where the unit tests' packages aren't installed). To run chosen checks on their own, in an environment built for them (how agents see a check
fail and then pass while changing it), see `tests/test_all_tools/alone.py` (`.claude/skills/live-check/`).

### Unit tests (no Designer needed)

`tests/unit` tests everything that can run outside
Designer: the plugin's server and authentication (with Qt replaced), both clients' protocol
(the MCP server's and `client/sd_run.py`'s, against that plugin server),
pixel decoding, image comparison, the tiling metric, `.sbs` parsing, diffing and portal
selection, render command building, search ranking, the installer, launch/quit edge cases,
environment variables and log reading. It also checks that this README lists every tool and that
the self-test exercises every tool and parameter and passes every `apply_edits` op, runs mypy (strict,
`mypy.ini`) over every Python file, checking the code that runs inside Designer against
Designer's own `sd` API and PySide6 stubs when Designer is installed, and runs Ruff
(`ruff.toml`): lint rules, and every file formatted. While working, run the tests you added or changed, always with
the lint and type checks; run them all as the final check, before merging into `main`, except for a change of docs
alone, which runs the docs tests (AGENTS.md, Running the tests):

```bash
mcp_server/venv/bin/pip install -r mcp_server/requirements-dev.txt   # pytest, mypy and ruff
mcp_server/venv/bin/ruff check --fix . && mcp_server/venv/bin/ruff format .   # lint and format
mcp_server/venv/bin/python -m pytest tests/unit/test_x.py::test_name tests/unit/test_lint.py tests/unit/test_types.py   # while working
mcp_server/venv/bin/python -m pytest   # all of them (on macOS the self-test runs them too: Running it, above)
```

### Working in PyCharm

The repo's `.idea` marks the source roots, excludes `mcp_server/venv`,
sets pytest as the test runner, and switches on PyCharm's built-in Ruff integration. Its source roots
include Designer's own `sd` and PySide6 folders at the default macOS install location, since the venv
doesn't have them. With Designer elsewhere, add yours under Settings → Project Structure, or PyCharm reports
those imports as errors: adding them as interpreter paths isn't enough for PySide6, whose stubs PyCharm
then doesn't read (measured: 14 of `QtWidgets`' 193 classes found). The rest is per user (not in git), so do this once:

1. **Interpreter:** choose `mcp_server/venv/bin/python` (Settings → Python → Interpreter). Ruff
   then runs the venv's `ruff` with `ruff.toml`.
2. **Settings → Python → External Tools** (or search for "External Tools"): configure Ruff and
   tick **Formatting** and **Import optimizer**, so PyCharm's Reformat Code and Optimize Imports
   use Ruff instead of PyCharm's own formatter.
3. **Settings → Tools → Actions on Save**: tick **Reformat code** and **Optimize imports**.

To check it, change a `'quote'` to `"quote"` and press ⌥⌘L (Code → Reformat File): Ruff turns it
back to single quotes. Lint fixes beyond imports (such as `raise ... from e`) show as warnings with
a quick fix (⌥⏎), or apply them all with `ruff check --fix .`.

## Configuration (optional environment variables)

| Variable | Default | Used for |
|---|---|---|
| `SD_DESIGNER_BIN_DIR` | macOS: `/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app/Contents/MacOS`; Windows: `C:\Program Files\Adobe\Adobe Substance 3D Designer` | finding `sbscooker` / `sbsrender` |
| `SD_DESIGNER_APP` | macOS: `/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app`; Windows: `C:\Program Files\Adobe\Adobe Substance 3D Designer\Adobe Substance 3D Designer.exe` | `launch_designer` (on macOS the .app, whose own binary it starts) |
| `SD_DESIGNER_LOG` | newest `log.txt` in Designer's settings folder (see Troubleshooting) | `read_designer_log` |
| `SD_SNAPSHOT_DIR` | `~/.sd_mcp/snapshots` | where `snapshot_graph` keeps snapshots (one folder per graph, each snapshot noting its package; safe to delete, except a snapshot you opened and saved in place, which may hold your work: `list_snapshots` marks those taken by this version) |
| `SD_BRIDGE_PORT` | `9877` | plugin, MCP server and CLI client (set the same value for all three; the plugin reads it from Designer's environment, so start Designer from a shell where it is set, or set it system-wide; `launch_designer` sets it for the Designer it starts, and on macOS a temp folder and home of its own) |

Set them in your shell before starting `claude`, add an `"env": {...}` block to your own copy of
the `.mcp.json` entry, or pass them when registering a folder:
`claude mcp add --scope local -e SD_DESIGNER_BIN_DIR="D:\Adobe\Designer" substance-designer -- ...`

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
- Every request must be signed with the secret in `~/.sd_claude_bridge_kve_token` (Windows:
  `%USERPROFILE%\.sd_claude_bridge_kve_token`): the plugin sends a random challenge and the client answers
  with an HMAC of it, the port it connected to and the request itself. So the secret never crosses the
  connection, and a program posing as the plugin (while Designer is closed, or on another port a tool is
  pointed at) can't pass the answer on to a real plugin to run code of its own.
- Only the client proves it knows the secret, not the plugin. So a program listening where a tool
  connects (port 9877 while Designer is closed, or another port given to a tool) would receive the
  next script and could send back a made-up reply. This is accepted: a program running as you could read the token file anyway, so only
  another user account on the same machine gains anything, and scripts carry no secrets.
- The plugin creates the token on first run, owner-only on macOS (it also tightens an existing
  file's permissions), and replaces an empty or truncated one. Anything that can read that file
  can run code inside Designer. To rotate it, delete the file and restart Designer.
- Requests are size- and time-limited (a whole request must arrive within 30 s, and at most 16
  connections that haven't authenticated yet are served at once, which bounds the memory and
  threads they can take; `status` and `cancel` still get through behind queued jobs). That cap is
  not a lock against other local programs: one holding 16 idle connections turns other clients away
  until it stops. A request is checked against its signature before it is even parsed, so an
  unsigned one costs Designer only its bytes. Malformed requests get no details back, only the last 8 million characters of a
  script's output come back, and on Windows the port is bound exclusively so a second program can't share it.
- Screenshots only ever capture Designer's own panels. The 3D view uses Designer's own render
  through the clipboard, then puts back its text; anything else on it (an image, formatting, copied files) may
  be lost.
- To turn the bridge off, disable it in Tools > Plugin Manager or delete the `sd_claude_bridge_kve`
  folder from the plugin directory.

## Uninstall

```bash
python3 uninstall.py --dry-run   # macOS; Windows: py -3 uninstall.py --dry-run. Shows what it would remove
python3 uninstall.py             # lists it again, asks, then removes it (--yes to skip the question)
```

It removes the `sd_claude_bridge_kve` plugin from Designer's plugin folder (and the old `sd_bridge`
one), `~/.sd_claude_bridge_kve_token`, the skill, `mcp_server/venv`, and this server's registration in
every folder where you ran `claude mcp add --scope local`, plus a user-scope registration
(`--scope user`) if there is one (found in Claude Code's
`~/.claude.json`, removed with `claude mcp remove` in each folder). A plugin, skill or
registration with the same name that isn't this project's is reported and left alone. Your graph
snapshots (`~/.sd_mcp/snapshots`) stay unless you pass `--remove-snapshots`; even then, a
snapshot taken by this version that you opened in Designer and saved in place stays (it may hold your
work), and is listed; older snapshots can't be told apart and are deleted. Pass
`--plugins-dir` if you installed with it. It also removes what `launch_designer` left for the
Designers an agent started: their records (`~/.sd_claude_bridge_kve_agent_designer_<port>.json`) and
their folders (`/tmp/sd_mcp_<user ID>_<port>/`, each one's settings, log and crash dumps).
While any Designer runs, or when that can't be told (its processes couldn't be listed, or not on
macOS), those folders are kept and listed instead, since one an agent started uses its own. Then
restart Designer and delete this folder.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `substance-designer` fails to connect in `/mcp`; its log says "no Python environment" | The venv is missing (a fresh clone, or it was deleted): run `python3 install.py`, then reconnect in `/mcp`. |
| `No bridge token found` | The plugin has never run. Restart Designer and check its console. |
| `Designer is not reachable` | Designer isn't running, or the plugin failed to load. Check the Designer log. |
| Every call returns `invalid token`, or says the plugin `speaks another bridge protocol` | The plugin and the server are different versions (for example after `git pull`): re-run `install.py`, restart Designer and reconnect `/mcp`. |
| `This Designer wasn't started by an agent` | The tools never close a Designer you opened. Save, close and reopen it yourself. |
| `Designer ... did not answer` and it may be stuck closing | If its windows closed but the process stayed, end it in Activity Monitor, or with the `kill` command the message gives. On Windows, in Task Manager. Nothing is lost then. If its windows are open, save and close it as usual: ending it would lose unsaved work. |
| Bridge accepts connections but never answers | The plugin code was replaced while running (for example by a hot reload). Restart Designer. |
| `Address already in use` in the Designer log | The plugin was loaded twice, or another app uses port 9877. Restart Designer, or change `SD_BRIDGE_PORT`. |
| `sbscooker/sbsrender not found` | Set `SD_DESIGNER_BIN_DIR`. |
| MCP shows `Failed to connect` | Run `<venv python> mcp_server/server.py` by hand to see the error (usually Python too old or the venv missing). |
| New tools don't show up in Claude Code | Reconnect `substance-designer` in `/mcp`, or restart Claude Code. |

Designer log (every plugin traceback ends up here; Claude can read it with `read_designer_log`):
- macOS: `~/Library/Application Support/Adobe/Adobe Substance 3D Designer/<version>/log.txt`; a Designer an agent
  started (`launch_designer`) writes its own, under `/tmp/sd_mcp_<user ID>_<port>/home/Library/Application Support/...`,
  with its crash dumps and settings
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
