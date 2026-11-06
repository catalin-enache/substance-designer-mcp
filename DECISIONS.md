# DECISIONS.md: what is already settled

This is the memory for the whole project, for all time. `REVIEW.md` is the memory per branch, where agents that review
and agents that address findings talk to each other; its history stays in git.

Won't-fix items, project rules and not-a-bug answers that a reviewer could plausibly raise again.
A finding that contradicts an entry here is dropped, unless the entry's **Reopen if** holds; then it
is a new finding that names the entry and the evidence. Unlike an answer in `REVIEW.md`, an entry can't be questioned
any other way.

Each entry stands on its own: the decision, the reason and what would reopen it, pointing at the code,
test or doc it concerns. Entries don't cite review findings. "The user" is named only where the record
says so. Measured Designer behaviour lives in `AGENTS.md`; an entry links to it rather than repeating it.

An entry is a bold one-line decision, then the reason, then `Reopen if: <condition>.`, with who decided and
when if the user did. An entry comes from a decision of the user's, on a finding or about the project, or from a
not-a-bug or not-reproducible answer the user acknowledged at a cleanup, which also suggests entries to remove. Agents
may update the names and paths an entry points at; changing what was decided, or removing an entry, takes the user
(the `address-review` skill, **Recording decisions**).

## Project rules

- **The full suites run only when the user asks; while working, only the tests added or modified run, always with lint
  and types, a live check in a scratch run.** The full suites took about 12 minutes (PLAN.md, measured), longer than
  the work they checked. No agent starts a whole run of either suite on its own, not for TDD, not after a fix, not
  between reviews: when a review finds nothing, it says the work is ready, and the user asks for the final check (both
  suites in full, before merging into `main`) when they say the work is done. Lint and types (`test_lint.py`,
  `test_types.py`) run with every test run, whichever tests it has. TDD stays: a new or changed live self-test check, which lives in
  the suite as a function its category's `run(ctx)` calls, is seen failing and then passing by calling that same
  function from a scratch script (`tests/test_all_tools/alone.py`, or one written from zero where it falls short), in
  an environment built for it, with a fresh MCP server, in a Designer an
  agent started; the few checks a scratch run can't prove wait for the full run (AGENTS.md lists them). A check proven
  that way can still pass or fail in the suite because of state earlier categories
  left; the user accepts that the full run is what shows it. When the final check fails, the failing tests run on
  their own until they pass (a live check in a scratch run), and then the user asks for the suites that failed again.
  When only unit tests failed, the live self-test runs again only if the fixes touch code it reaches (AGENTS.md lists
  it); its pass is for the code as it was. (The user's choice, 2026-11-06.) Docs changed alone run the doc tests instead (AGENTS.md, Running the tests).
  Only the agent changing the code runs tests; a review runs none, and judges the tests by reading them, its lead
  agent checking in Designer with scratch probes what reading can't settle.
  A change not having run the full suites, before the user asks for them, is not a finding; a branch merged without
  them passing is.
  Reopen if: the full suites become fast enough to run after every change, or a break found only in the full run cost
  more than the time saved. (The user's decision, 2026-11-06.)

- **Only the current and next versions of Designer are supported.** README says older versions aren't, and the plugin's
  manifest asks for 16.0.0, so code needn't work on an older Designer or its older Python.
  Reopen if: the user wants older versions supported. (The user's decision, 2026-11-03.)

- **A Designer the user opened is theirs; one an agent started is disposable.** The tools never end the user's: `quit_designer`
  refuses, and the agent asks them to save, close and reopen it, or to open it if a task needs it. A user wanting a material already
  has Designer open, so an agent only starts one for tests or work on this project, and ends it however works, force included,
  dropping what is unsaved (`server_tools/lifecycle.py`). The user's decision, 2026-11-05.
  Reopen if: the user changes the rule.

## Security

- **Only the client is authenticated, not the plugin.** A program running as the same user could read
  the owner-only token file anyway, so mutual authentication helps only against another user account
  on the same machine, and scripts carry no secrets. It would also mean a protocol change in the
  plugin, the server, `sd_run.py` and the self-test together (README, Security;
  `test_clients_never_send_the_token`). Agreed with the user, 2026-10-29.
  Reopen if: scripts start carrying secrets, or the bridge becomes reachable from another machine.
- **The plugin reads a whole request before checking its signature.** The signature is inside the request, and code
  runs only after it checks out. Anything reaching the bridge is already on the user's machine (it listens on
  `127.0.0.1`), so the worst a program without the token can do is make Designer hold about 1 GiB for up to 30 s
  (16 connections, 64 MiB each). Checking first would change the protocol in the plugin, the server, `sd_run.py` and the
  self-test together. The user's decision, 2026-11-04.
  Reopen if: the bridge becomes reachable from another machine.

## Library packages

- **`execute_designer_code` and `run_designer_script` aren't checked for edits to a library graph.**
  On purpose: the tools refuse such edits (`_graph_to_edit`, `designer_helpers/core.py`), and a person's
  or agent's own code is not checked (`AGENTS.md`, Environment facts).
  Reopen if: the user wants scripts restricted.
- **A definition naming a function or another resource isn't told apart from a graph**
  (`designer_helpers/describe.py`). The suggested fix would remove what works for bitmaps and SVGs. What
  remains is a cryptic error, with nothing changed, on an id `search_nodes` never prints. Agreed with the
  user, 2026-11-02.
  Reopen if: such an id starts changing something, or `search_nodes` starts printing such ids.
- **A definition's graph part can't leave its package. Not a bug.** `findResourceFromUrl` looks inside the
  package it is called on; relative, absolute and `sbs://` paths found nothing when measured. Not checked:
  what `newInstanceNode` does with a folder named as the graph.
  Reopen if: the live check "a definition's graph stays in its package" fails, or there is new evidence.
- **Loading and then unloading a package that is already a dependency loses nothing.** Not reproduced: measured
  on Designer 16, it goes back to being a dependency, the instance still resolves, the graph computes and nothing
  is marked modified. Not measured: the same check's path comparison on Windows. The self-test's subfolder check
  (`tests/test_all_tools/safeguards.py`) now runs only in a Designer it started, so neither case reaches the
  user's session.
  Reopen if: that check runs in the user's Designer again, or an unload is seen to lose work.
- **`preview_node` and `node_stats` count as reads on a library graph.** Their temporary output node can leave the package
  marked modified, with its content unchanged, so closing Designer may ask about it. Saving is refused for library packages,
  so the way out is for the user to close Designer without saving it, after saving what they want to keep. The user's decision, 2026-11-04.
  Reopen if: a read is seen to change a library graph's content.

## Snapshots and saving

- **Only a snapshot of an unsaved package gets a fresh UID** (`_fresh_uid`, `server_tools/snapshots.py`).
  A saved package's snapshots, told apart by file, stay Designer's exact copies. The user chose this out
  of three options: re-stamp every snapshot, only unsaved packages', or none and accept the limit.
  Reopen if: the user changes the choice, or snapshots of saved packages get mixed up.
- **Only the files that hold the user's work are written all-or-nothing by our code:** snapshots and `set_link_display`'s
  `.sbs`. The installer's `SKILL.md`, the example's generated `.sbs` and `node_stats`' temporary buffer aren't, because
  they can be recreated. Designer's own saves and exports aren't ours to control. This is about one file being
  half-written, not about a command that makes several changes. The user's decision, 2026-11-04.
  Reopen if: a tool starts writing the user's work another way.

## Function graphs and inputs

- **`drives:` and `remove_graph_input`'s refusal differ on purpose.** `drives:` says what has an effect
  today; the refusal also counts a function with no effect today, since a later edit could connect it
  (`designer_helpers/graph_inputs.py`).
  Reopen if: the user changes the rule.
- **`_delete_function`'s inheritance calls have no guard** (`designer_helpers/graph_inputs.py`). Not
  reproduced: neither call raised in any measured case, and a guard would be untested code.
  Reopen if: a case that raises is measured.

## Bridge and quitting

- **`stop()`'s `shutdown()` before `close()` is only a defence.** Not reproduced as a bound port: on macOS, with
  that line removed, `close()` alone woke the blocked `accept()` and the port could be bound at once. The line is
  for platforms where `close()` doesn't do that; none was measured.
  Reopen if: `test_stop_answers_queued_clients_and_frees_the_port` fails, or a port stays bound on another platform.
- **A Designer the user opens during `launch_designer`'s wait can be recorded as the agent's.** It takes a Designer that
  crashes while starting and the user opening their own within the same wait, and limiting the record to a process started
  within seconds of the launch isn't worth it for that (`_remember_started`, `server_tools/lifecycle.py`). The user's
  decision, 2026-11-05.
  Reopen if: it is seen to happen, or `launch_designer` starts being used for the user's own work.

## Output, pixels, screenshots, the graph view, example

- **An unconnected output node computes an image and is exported.** Not reproduced as a skipped output. The
  branch in `export_outputs` naming an output that computed no image is only a defence.
  Reopen if: the check in `tests/test_all_tools/render.py` (`mcp_empty`) fails.
- **An empty clipboard gives empty mime data, not `None`.** Not reproduced as a bug: measured by a live check,
  and Qt documents `None` only for a platform without that clipboard mode. The `None` check in
  `designer_helpers/screenshots.py` is only a defence.
  Reopen if: the "designer facts" check on the empty clipboard fails.
- **The self-test's empty-clipboard check loses no clipboard data, as far as measured.** Not reproduced: live on
  macOS the clipboard came back intact. The check clears the real clipboard, so it runs only where it can compare
  before and after (macOS, skipped elsewhere), and it fails if the clipboard didn't come back. Data Qt can't copy
  wasn't tried specifically.
  Reopen if: that comparison fails, or data is seen to be lost.
- **Why `open_graph`'s wheel steps once did nothing is unknown, and isn't being chased.** It happened in one self-test
  run of four. Not reproduced: 200 wheel steps and 40 fits in a fresh Designer gave no stuck step, idle and under
  load. `_fit_view_to` no longer reports such a view as fitted, and gives the view's size and whether Designer's
  window is active, so a later occurrence explains itself (`test_a_view_ignoring_the_wheel_isnt_reported_as_fitted`).
  It stays a result, not an error, since the graph is open either way.
  Reopen if: it happens again; that output is the evidence to start from.
- **The example's unload and reload in one call is left as it is** (`examples/build_dwarf_trimsheet.py`). Not
  reproduced: five re-runs with the previous build open in a tab caused no crash. The recorded crash needed a
  new graph view being created while old ones were torn down, and this reload creates none.
  Reopen if: a crash dump points at this reload.
- **Renaming an existing output warns; it isn't refused.** Designer updates only the graphs open during the rename. One that
  was closed computes black, with no error, and the tools can't see it. So `apply_edits`' result tells the agent to tell the
  user, naming the repair (`set_output_tags`; `AGENTS.md`, Output nodes). The user chose this over refusing a rename or only
  documenting it, 2026-11-04.
  Reopen if: the user changes the choice, or the tools become able to see the graphs a rename would break.
