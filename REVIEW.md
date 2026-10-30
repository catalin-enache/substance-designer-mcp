# REVIEW.md: review findings

Findings from code reviews of this repository, kept across reviews. A new review **appends** its
findings to the matching severity section and adds itself to the log; it never removes or
rewrites existing entries. An entry is checked when it is resolved: fixed, or answered (not a
bug, not reproduced, won't fix), always with a resolution line. Format and rules:
`.claude/skills/project-code-review/` (SKILL.md, TEMPLATE.md).

**Confidence.**
- *Confirmed*: the defect is visible in the code as quoted.
- *Plausible*: the code path exists, but whether it bites depends on Designer, the OS or timing.
- *Verified by hand*: checked against the code after the review, not only by the reviewer.

**IDs.** One prefix per area, numbered on: **PLG** plugin and bridge protocol, **SRV**
`mcp_server/server.py`, **HLP** `mcp_server/designer_helpers.py`, **INS** installer, uninstaller,
command-line client and example, **TST** tests and docs. A new area gets a new prefix, added here.

## Status

| Severity | Open | Resolved |
|---|---|---|
| High | 0 | 1 |
| Medium-high | 0 | 1 |
| Medium | 0 | 15 |
| Low-medium | 0 | 17 |
| Low | 0 | 68 |
| **Total** | **0** | **102** |

## Review log

### 2026-10-29: whole project at `b745872`

- **How:** five read-only reviewers, one per area: the plugin and bridge protocol; the server's
  tool layer; the code that runs inside Designer; the installer, uninstaller, command-line client
  and example; the tests and docs. Unit tests passed (135); the live self-test passed (200/200)
  just before. The top finding of each area was verified by hand. The previous review's findings
  (`open_graph`, screenshots, view zoom) were fixed in `52f4d24` and `b745872` and aren't listed.
- **Findings:** 49 (PLG-1..7, SRV-1..12, HLP-1..11, INS-1..10, TST-1..10; PLG-3 and INS-3 are
  one finding, listed once): 1 high, 1 medium-high, 13 medium, 3 low-medium, 31 low.
- **Suggested order:**
  1. PLG-1 and PLG-2 (the plugin's job runner; needs a reinstall and a Designer restart);
  2. data safety: PLG-3, HLP-1, SRV-4, INS-8, INS-1;
  3. misreported results: SRV-1, SRV-2, HLP-2, TST-1, TST-4;
  4. TST-3 (test or delete the unverified facts);
  5. the rest, as they come up.
- **Simplifications:**
  - **One shared client.** `client/sd_run.py` duplicates the server's protocol client line for
    line; AGENTS.md's "change them together" note exists only because of that. A shared module
    next to `project_constants.py` could serve the server, the CLI and the self-test.
  - **One definition lookup.** `describe_node` duplicates `_resolve_definition`.
  - **One texture dump.** `dump_node_pixels` and `sweep_param` share raw-dump code.
- **Checked and found fine:**
  - **Plugin and protocol:** binds to 127.0.0.1 only; exclusive port binding on Windows;
    `hmac.compare_digest`; a fresh 128-bit nonce per connection (no replay); token file 0600,
    written atomically; no error details before authentication; deeply nested JSON handled;
    dequeuing and cancel both under the lock.
  - **Server:** `%r` quoting of values sent to Designer, and unicode through JSON; cooking in temp
    folders, never next to the user's file; render output detection; region clamping; snapshots
    never overwrite each other; `quit_designer` refuses unsaved changes unless told to discard.
  - **Helpers:** exceptions caught as `(Exception, APIException)` everywhere; connection direction
    read correctly; inheritance used by name; `setDefaultParentSize` given pixels; enum values
    from the enumerators.
  - **Installer and uninstaller:** valid skill frontmatter; consistent `CLAUDE_CONFIG_DIR`;
    `normcase` path comparison; `claude mcp remove` run in the registered folder; ownership checks
    before deleting; the example's height maths and portal writing.
  - **Docs:** tool count (43) and README Tools table match the code; every tool named in AGENTS.md
    exists; no ROADMAP item already done; environment variables and defaults match.


### 2026-10-29: venv and Python version, from a user question, at `ec6ad79`

- **How:** the user asked how a deleted venv is restored, whether an agent in a fresh clone would
  know what to do, and which Python the venv uses. Checked against `.mcp.json`, AGENTS.md,
  README.md, `install.py` and `mcp_server/venv/pyvenv.cfg` (Python 3.12.10).
- **Resolutions assessed:** none (no review of earlier fixes).
- **Findings:** 4 low (INS-11, SRV-13, TST-11, TST-12); INS-5, already open, covers the missing
  venv's silent failure.
- **Suggested order:** together with INS-5, before the other low findings.
### 2026-10-29: branch `review-fixes` against `main`, at `5f69229`

- **How:** five read-only reviewers, one per area (plugin and protocol; `server.py`; the helpers;
  installer, uninstaller, example and config; tests and docs). They started from
  `git diff main...review-fixes`, but also read the whole files and re-assessed every resolution
  in their area, so this was close to a whole-project review (the user had asked for the diff
  only). Unit tests passed (195); the live self-test passed just before (230/230 against an open
  Designer, 236/236 from a closed one). The top finding of each area was verified by hand.
- **Resolutions assessed:** all 55. Questioned: PLG-3 (SRV-16), PLG-4 (PLG-10), PLG-5 (PLG-12),
  PLG-8 (HLP-12), PLG-9 (TST-16), SRV-3 (SRV-14), SRV-10 (SRV-15), HLP-10 (HLP-14), INS-5
  (INS-14), INS-10 (INS-12), TST-3 (TST-13, TST-15), TST-10 (TST-18). The rest hold up.
- **Findings:** 20, no regressions: 7 low-medium (PLG-10, SRV-14, SRV-15, HLP-12, HLP-13, TST-13,
  TST-14), 13 low (PLG-11..13, SRV-16, HLP-14, INS-12..15, TST-15..18). Not recorded: two notes on
  the user's own `TODO.md` (a second list beside ROADMAP.md, already out of date) and ROADMAP row 5
  (unfinished); the user keeps `TODO.md` as it is.
- **Suggested order:** HLP-12 first (it touches every normal quit), then PLG-10 and TST-13/TST-14
  (a blocked cancel; a check that can't fail; the user's clipboard), then SRV-14 and SRV-15.
- **Checked and found fine:** the abandon/start handshake under the lock, one reply per
  connection, `done` set once per job on cancel and stop; `_decode_pixels`' prefix table and
  channel order, `_alpha`, `_channel_names`; `_same_graph` used for every identifier comparison;
  every new `except` catches `APIException`; `open_graph` never sets the view transform; the
  uninstaller's snapshot regex matches the server's names; the requirements' lower bounds install
  on Python 3.10 (pillow 12, numpy 2.2: untested, as README says); README's tool count (43) and
  Tools table; no secrets or personal paths in tracked files.
### 2026-10-30: branch `review-fixes` against `main`, the diff only, at `9152176`

- **How:** five read-only reviewers, one per area, each given only its part of
  `git diff main...review-fixes` (the scope rule now in the skill). Unit tests passed (205); the
  live self-test passed just before (235/235 against an open Designer). The top finding of each
  area was verified by hand.
- **Resolutions assessed:** the 20 fixed since the last review (PLG-10..13, SRV-14..16,
  HLP-12..14, INS-12..15, TST-13..18). Questioned: SRV-14 (SRV-17), SRV-15 (SRV-19), SRV-16
  (SRV-18), HLP-12 (HLP-17, TST-19), HLP-13 (HLP-16, TST-20), HLP-14 (HLP-18), INS-12 (INS-16),
  INS-13 (INS-17), INS-14 (INS-18), TST-16 (TST-21); and two older ones, PLG-7 (PLG-14) and HLP-3
  (HLP-15). PLG-10..13, INS-15, TST-13..15, TST-17 and TST-18 hold up.
- **Findings:** 14, no regressions: 5 low-medium (SRV-17, HLP-15, HLP-16, INS-16, TST-19), 9 low
  (PLG-14, SRV-18, SRV-19, HLP-17, HLP-18, INS-17, INS-18, TST-20, TST-21).
- **Suggested order:** SRV-17 (a snapshot that can't be opened properly), HLP-16 (a premise to
  measure before relying on it), INS-16, then TST-19 with HLP-17 (both about the quit fallback).
- **Checked and found fine:** the plugin's locking (no nested acquires; every queue change under
  the lock; `release()` exactly once); one job per tick adds about 0.1 s per queued job, far below
  every wait; `_copy_sbs`' XML round trip only when a path changed, `copystat` after writing;
  SRV-15 can't start two Designers; `.mcp.json`'s quoting and `-x` on a `.exe` under Git Bash;
  `Kept` before the error branch; the example's `BaseException` clean-up re-raises the abort; the
  HLP-13 check's leftover values don't change later measurements.
### 2026-10-30: branch `review-fixes` against `main`, the diff only, at `4da1095`

- **How:** five read-only reviewers, one per area, each given only its part of
  `git diff main...review-fixes`, and told that an empty result is fine (the third pass over most
  of this code). Unit tests passed (210); the live self-test passed just before (246/246 from a
  closed Designer). The top finding of each area that had one was verified by hand.
- **Resolutions assessed:** the 14 fixed since the last review (PLG-14, SRV-17..19, HLP-15..18,
  INS-16..18, TST-19..21). Questioned: SRV-19 (SRV-20, SRV-21), TST-19 (HLP-19, TST-23), HLP-18
  (HLP-20), INS-16 (INS-19..21), HLP-16 (TST-22, TST-24). PLG-14, SRV-17, SRV-18, HLP-15, HLP-17,
  INS-17, INS-18, TST-20 and TST-21 hold up.
- **Findings:** 10, all low, no regressions: SRV-20, SRV-21, HLP-19, HLP-20, INS-19..21,
  TST-22..24. The plugin reviewer found nothing.
- **Suggested order:** TST-23 and HLP-19 together (decide what "shutdown has begun" means and
  test exactly that), INS-19..21 together, then the rest as they come up.
- **Checked and found fine:** `cancel` and `status` count the same way under the same lock;
  `_copy_sbs`' skip order; the docstrings' wait formula against `_bridge` and `QUEUE_WAIT`;
  `start()` runs once in `launch_designer`; `closing` cleared in a `finally`; a window that ignores
  Close still gets the fallback at 5 s; `give_up` measured from the `quit_designer` call; the
  example's two injection points exist once each; patched classes restored in `finally`.
### 2026-10-30: branch `review-fixes` against `main`, the diff only, at `cd809ab`

- **How:** four read-only reviewers (server, helpers, installer, tests and docs; the plugin hadn't
  changed since the last review), each given only its part of `git diff main...review-fixes`.
  Unit tests passed (214); the live self-test passed just before (249/249 from a closed Designer).
  The top finding was verified by hand.
- **Resolutions assessed:** the 10 fixed since the last review (SRV-20, SRV-21, HLP-19, HLP-20,
  INS-19..21, TST-22..24). Questioned: HLP-19 (TST-25), HLP-20 (TST-26, TST-27). The other eight
  hold up.
- **Findings:** 3, all in the self-test: 2 low-medium (TST-25, TST-26), 1 low (TST-27). The server,
  helpers and installer reviewers found nothing.
- **Suggested order:** TST-26 first (a test that can delete the user's snapshots), then TST-25 and
  TST-27.
- **Checked and found fine:** `restarted` set on every path and the timeout wording in each case;
  the restart test's clock (the old process leaves 170 s into 180; fails without SRV-19); the
  fallback's 35 s timer chain is harmless (it only ticks while the event loop runs, and acts only
  on a visible window); AGENTS.md's quit text matches the code; the installer's rollback re-raises
  the original error, and each leftover is listed once.
### 2026-10-30: branch `review-fixes` against `main`, the diff only, at `07c12c0`

- **How:** one read-only reviewer: only `tests/test_all_tools.py` had changed since the last
  review (`git diff 2c12c93 07c12c0`). Unit tests passed (214); the live self-test passed just
  before (250/250 from a closed Designer).
- **Resolutions assessed:** TST-25, TST-26, TST-27; all hold up.
- **Findings:** none. The reviewer also reported AGENTS.md as still naming `aboutToQuit` as a
  condition of the quit fallback; checked by hand, that sentence was replaced in `cd809ab` and
  AGENTS.md now says `aboutToQuit` can't serve as the signal, so it wasn't recorded.
- **Checked and found fine:** the forced quit's `aboutToQuit` marker is connected in the first
  Designer and its `normal_quit` counterpart in the relaunched one, so no slot carries over; both
  marker paths are in the run's own temporary folder; the snapshot path is parsed from
  `snapshot_graph`'s "saved: <path>" result, whatever reminder precedes it.
---

## High

- [x] **PLG-1 · A queued job can start inside the running one** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:153-155, 232-248` · confirmed · verified by hand · found 2026-10-29
  - **Defect.** `_drain` runs on a 100 ms `QTimer` and has no guard against running inside itself.
    While a script runs, anything that lets Qt process events (screenshots, the 3D capture,
    `open_graph`, the wheel zoom) could fire the timer again, and the inner `_drain` would run the
    next queued job in the middle of the current one.
  - **Scenario.** Job A (`screenshot_designer('3d')`) runs, job B is queued: B runs inside A's undo
    group and clipboard backup, clears a cancel requested for A, and on finishing sets
    `busy_since = None`, so `status` says idle and `cancel` can't stop A.
  - **Fix.** A re-entry flag set in a try/finally, or stop the timer while a job runs.
  - **Resolution: done, defensively; not reproducible in Designer** (commit `1334dcc`).
    - **Test:** a unit test calling `_drain` from inside a job failed as described (job B ran
      inside A; A no longer counted as busy). The live check "bridge queue: a queued job waits for
      the running one" (job A processes Qt events for 1.5 s while B is queued) passed against the
      old plugin.
    - **Why not:** Qt doesn't fire a timer again while that timer's own slot is still running, so
      in Designer the drain can't re-enter through the timer; only a direct call can.
    - **Fix:** a re-entry flag in `_Server._drain` (set in a try/finally), for any other caller.
      Both tests kept.

## Medium-high

- [x] **PLG-2 · After an abort, the trace hook keeps raising inside cleanup code** · `__init__.py:83-87` · logic confirmed, impact plausible · verified by hand · found 2026-10-29
  - **Defect.** Once cancelled or past its deadline, the tracer raises `ScriptAborted` every 64
    trace events and never disarms, so `finally` blocks and context-manager exits get aborted too.
  - **Scenario.** `UndoGroup.__exit__` (Python, calls `commitTransaction()`) is aborted and leaves
    an undo transaction open; the 3D screenshot's `finally` fails to restore the clipboard.
  - **Fix.** Raise once, then disarm.
  - **Resolution: not a bug** (commit `1334dcc`).
    - **Test:** a unit test with a `finally` block after a cancel passed before any change; so did
      a live "designer facts" check (a timed-out script still prints from its `finally`).
    - **Why not:** Python unsets a trace function that raises (`sys.settrace` docs), so the abort
      fires once and cleanup code runs to the end. Documented in `_make_tracer`; tests kept.

## Medium

- [x] **PLG-3 · A job can still run after its client gave up waiting** · `server.py:186`, `client/sd_run.py:70`, plugin `__init__.py:224` · confirmed (found by two reviewers; also INS-3) · found 2026-10-29
  - **Defect.** The clients stopped waiting at `(timeout or 900) + 60` s; the plugin keeps a
    queued job for `QUEUE_WAIT = 900` s regardless, though its docstring says "never run late".
  - **Scenario.** `execute_designer_code(timeout_s=120)` queued behind a 600 s script: the client
    reports "no reply" at 180 s, and at about 600 s the plugin runs it anyway, with nobody waiting.
    `sd_run.py` also showed a raw `TimeoutError` traceback.
  - **Fix.** The client sends its deadline, or waits at least as long as the plugin's queue plus
    the script; a clear client-side timeout message.
  - **Resolution: done** (commit `5f27a79`).
    - **Test:** unit tests checking the clients' wait failed: 180 s for a 120 s script, while the
      plugin keeps a queued job up to 900 s.
    - **Cause:** the clients' give-up time counted only the script's timeout, not the time a job
      can wait in the plugin's queue first.
    - **Fix:** the server's `_bridge` and `sd_run.py` wait `QUEUE_WAIT + timeout + 60`, with
      `QUEUE_WAIT` in `project_constants.py` (a unit test checks it against the plugin's own
      value); `sd_run.py` catches the timeout and prints a message. No plugin change.
  - Questioned by SRV-16 (2026-10-29).

- [x] **HLP-1 · `set_params` changes some parameters before failing on a later one** · `mcp_server/designer_helpers.py:539-554` · confirmed · verified by hand · found 2026-10-29
  - **Defect.** Each parameter was validated and set in turn, despite the comment "validate before
    changing anything" and the same claim in AGENTS.md.
  - **Scenario.** `set_params(node, {"levelinlow": [...], "blendingmode": "bogus"})` sets the first,
    then raises; the agent believes nothing changed (also `apply_edits` `set`, `add_node(params=...)`).
  - **Fix.** Look up and convert every value first, then set.
  - **Resolution: done** (commit `5f27a79`).
    - **Test:** a live check setting `levelinlow` and a bad `levelinhigh` together failed: the
      error came back, but `levelinlow` had changed to 0.60.
    - **Cause:** each value was set right after it was checked, so a bad later value left the
      earlier ones changed.
    - **Fix:** `set_params` in `designer_helpers.py` now looks up and converts every value in a
      first loop, and sets them in a second.

- [x] **HLP-2 · `set_params` reports success on a parameter driven by a graph input** · `designer_helpers.py:540-554` · confirmed · found 2026-10-29
  - **Defect.** After `expose_param` the parameter is driven by a function graph; `set_params`
    printed `old -> new` though the output follows the graph input. `sweep_param` already refuses.
  - **Fix.** Refuse, pointing to `node_id='graph'` and the input id.
  - **Resolution: done, and worse than reported** (commit `2fd025b`).
    - **Test:** a live check setting `leveloutlow` after `expose_param` failed: `set_params`
      printed a change, and `list_graph_inputs` then showed the input driving nothing
      ("drives: -"); four later checks failed because of it.
    - **Cause:** setting the value of a parameter driven by a function graph replaces the binding,
      so the parameter is cut loose from its graph input: `expose_param` is silently undone.
    - **Fix:** `set_params` checks `getPropertyGraph` while validating and refuses: "driven by
      graph input 'floor'; set that instead (set_params node_id='graph')".

- [x] **SRV-1 · `diff_graph(against='latest')` after `set_link_display` compares with the wrong snapshot** · `mcp_server/server.py:980-997, 1222-1225` · confirmed · verified by hand · found 2026-10-29
  - **Defect.** `set_link_display` writes `<stamp>-before_portals.sbs` (live graph) and, usually in
    the same second, `<stamp>-before_portals_file_on_disk.sbs` (old saved file); `_snapshots()`
    sorted by name and `.` sorts before `_`, so "latest" was the old saved file.
  - **Scenario.** With unsaved edits, `diff_graph(against='latest')` after a portal change lists
    the user's earlier edits as if the portal step made them.
  - **Fix.** Sort by time, or keep the file-on-disk copy out of "latest".
  - **Resolution: done** (commit `2fd025b`).
    - **Test:** a unit test writing both snapshots with the same timestamp failed: "latest" was
      the file-on-disk copy.
    - **Cause:** `_snapshots()` sorted by file name; with equal timestamps the labels decide, and
      `.` sorts before `_`, so `..._file_on_disk.sbs` came last.
    - **Fix:** `_snapshots()` in `server.py` sorts by modification time, then name. The
      file-on-disk copy is made with `copy2`, which keeps the older saved file's time, so the live
      graph's snapshot is the newest. `list_snapshots`' description says so.

- [x] **SRV-2 · `sweep_param` hides an error partway through a sweep** · `server.py:675-692`, `designer_helpers.py:1182-1185` · confirmed · found 2026-10-29
  - **Defect.** The helper prints `restored ...` in a `finally`; the server ignored the error
    section whenever some tiles were produced.
  - **Scenario.** `values=[0.1, 0.5, 'bogus', 0.9]` returned two tiles and "restored", with no sign
    that a value failed.
  - **Fix.** Report the error.
  - **Resolution: done** (commit `2fd025b`).
    - **Test:** a unit test (one tile, then an error, then "restored") failed: the report had the
      tile and "restored", but no error.
    - **Cause:** `sweep_param` in `server.py` only looked at the error section when no tile at all
      was produced; with some tiles it ignored it.
    - **Fix:** whenever `--- ERROR ---` is in the output, the report adds "Sweep stopped after N of
      M value(s): <last error line>".

- [x] **SRV-3 · Snapshots may lose copied bitmap resources** · `server.py:967-973` · plausible · found 2026-10-29
  - **Defect.** `saveCopyOfPackageAs` writes `copy.sbs` into a temp folder; only that file is moved
    and renamed, then the temp folder is deleted.
  - **Scenario.** A package with `import_bitmap(embed='copy')` images gives a snapshot whose bitmaps
    are missing, so "can be opened in Designer to recover anything" fails.
  - **Fix.** Write the copy straight to its final path, or move the whole folder; a self-test check
    with a copied bitmap.
  - **Resolution: done** (commit `d9acfee`).
    - **Test:** a live check takes a snapshot right after a bitmap is copied into the package and
      checks that every bitmap path in the snapshot's `.sbs` leads to a file. It failed: the paths
      were relative to the temp folder the copy was written to (`../../var/folders/...`).
    - **Cause:** Designer writes resource paths relative to where the copy is saved; the snapshot
      was saved in a temp folder and then moved, which broke every relative path, for copied and
      linked bitmaps alike.
    - **Fix:** `snapshot_graph` in `server.py` first asks for the graph's identifier, names the
      snapshot, and saves the copy straight to that path. Bitmaps are still referenced, not copied
      (the description says so), so a snapshot can't bring back a bitmap file deleted later.
  - Questioned by SRV-14 (2026-10-29).

- [x] **SRV-4 · `set_link_display` unloads without checking for unsaved changes** · `server.py:1231-1260`, `designer_helpers.py:1357-1364` · check confirmed, risk plausible · found 2026-10-29
  - **Defect.** `unload_package_file` unloaded every open package at the path without checking
    `isModified()`; the UI stays live between the save, the XML edit and the unload.
  - **Scenario.** The user edits during that window, or a second open copy was never saved: those
    changes are dropped silently.
  - **Fix.** Refuse (or save again) when a matching package is modified.
  - **Resolution: done** (commit `5f27a79`).
    - **Test:** a live check (a saved package, then an edit, then the helper's unload) failed: the
      package was unloaded and the edit lost.
    - **Cause:** `unload_package_file` unloaded every package at the path without asking whether
      it had changes made after the save.
    - **Fix:** it now refuses while a matching package `isModified()`, so `set_link_display`
      stops before the reload and the edits are kept; its description says so.

- [x] **INS-1 · The example script unloads old builds and reloads in one call** · `examples/build_dwarf_trimsheet.py:92-94, 377-390` · plausible · found 2026-10-29
  - **Defect.** The previous build may be open in an editor tab when the script unloads it and
    reloads the new file in the same call: the pattern behind the crash recorded in AGENTS.md.
  - **Fix.** Unload old builds in a separate step, or close their views first.
  - **Resolution: not reproduced** (commit `5f27a79`).
    - **Test:** five re-runs of the example with its previous build open in an editor tab.
    - **Why not:** all five built, saved and reopened; Designer kept running and wrote no crash
      dump. The recorded crash needed a new graph view being created while old ones were torn
      down, and this reload creates no view. Left as is; the self-test's INS-8 re-runs happen with
      the example's tab open, so a regression would show there.

- [x] **INS-2 · The uninstaller stops halfway on the first error** · `uninstall.py:172-178` · confirmed · found 2026-10-29
  - **Defect.** `rmtree` and `os.remove` raise instead of returning error text, with no try/except
    around each action.
  - **Scenario.** On Windows the venv's `python.exe` is locked (a running MCP server, or the
    uninstaller run with the venv's Python): a traceback, a half-deleted venv, later steps skipped,
    no "Some items were not removed" summary.
  - **Fix.** Wrap each action in `try/except OSError`; warn when `sys.prefix` is the venv.
  - **Resolution: done** (commit `d9acfee`).
    - **Test:** a unit test that makes deleting the plugin folder (the first item) raise
      `PermissionError` failed with that traceback, leaving the rest undone; a second test expected
      a warning when run with the venv's own Python and got none.
    - **Cause:** the removal loop called each action without catching `OSError`, and nothing
      looked at which Python was running.
    - **Fix:** `main()` in `uninstall.py` catches `OSError` per item, reports it as "Could not
      remove ..." and goes on, so the summary says what's left; it notes when it runs with
      `mcp_server/venv`'s Python and says to use the system Python.

- [x] **INS-4 · The generated skill's commands are quoted wrongly for a shell** · `install.py:42-43, 77-80` · spaces confirmed, Windows plausible · found 2026-10-29
  - **Defect.** `register_command` uses `subprocess.list2cmdline` (cmd quoting). Claude Code's Bash
    tool on Windows is Git Bash, where unquoted backslash paths lose their backslashes; the skill's
    uninstall line is never quoted, so it also breaks on macOS with spaces in the repo path.
  - **Fix.** `shlex.join` with forward slashes for the skill text; `list2cmdline` only for the hint
    printed in PowerShell.
  - **Resolution: done** (commit `d9acfee`).
    - **Test:** unit tests generate the skill with a repo path containing spaces (macOS) and a
      Windows backslash path, then split its commands as a POSIX shell does. Both failed: the
      uninstall path split at its spaces; the Windows paths lost their backslashes.
    - **Cause:** the skill's commands used `subprocess.list2cmdline` (Windows cmd quoting) and the
      uninstall line wasn't quoted at all, while they are run by Claude Code's Bash tool, a POSIX
      shell on every platform (Git Bash on Windows).
    - **Fix:** `shell_command()` in `install.py` (`shlex.join`, forward slashes on Windows) builds
      both commands in the skill; the installer's own printed hint keeps native quoting for the
      user's terminal.

- [x] **TST-1 · A tool whose only checks were skipped counts as covered and passing** · `tests/test_all_tools.py:52-55, 1124-1128` · confirmed · verified by hand · found 2026-10-29
  - **Defect.** `skip()` registers the tool with an empty list, and `all([])` is True.
  - **Scenario.** With your Designer running, both `quit_designer` checks are skipped, yet the run
    printed "43/43 tools covered" and exited 0.
  - **Fix.** Count a tool only with a check that ran; list skipped-only tools.
  - **Resolution: done** (commit `2fd025b`).
    - **Test:** unit tests for a `summarize()` function failed (it didn't exist; the summary was
      inline in `main()`).
    - **Cause:** `skip()` registered the tool with an empty list of results, and `all([])` is
      True, so a tool with only skipped checks counted as covered and passing.
    - **Fix:** `summarize()` in `tests/test_all_tools.py` counts a tool as covered only with a
      check that ran, and lists the rest as "only skipped"; skips alone don't fail the run, missing
      tools and failed checks do. README.md's note on the summary is updated.

- [x] **TST-2 · The export-vs-render tolerance in the test is looser than AGENTS.md says** · `AGENTS.md:67-68` (<= 3/65535) vs `tests/test_all_tools.py:945` (<= 8) · confirmed · found 2026-10-29
  - **Fix.** Tighten the check to 3, or document 8. Parallel renders differ by a few steps from
    run to run, so documenting the tolerance actually tested is likely right.
  - **Resolution: done** (commit `d9acfee`).
    - **Test:** the existing check, which now prints its measurement: max 3/65535 at 4 pixels in
      the last run.
    - **Cause:** AGENTS.md recorded one observed run (<= 3) as the rule, while the test allowed 8;
      renders computed in parallel aren't bit-identical from run to run, so 3 would be flaky.
    - **Fix:** AGENTS.md (Output) now states the tolerance the test uses (a few 1/65535 steps at a
      few pixels; the self-test allows 8) and why; the test's comment points there.

- [x] **TST-3 · Facts in AGENTS.md without a "designer facts" check** · AGENTS.md · confirmed by searching `tests/` · found 2026-10-29
  - **Defect.** Untested claims: the API inheritance numbers (`RelativeToInput 0, RelativeToParent
    1, Absolute 2`); `CopiedAndLinked`'s `XXXXXX-` prefix and temp folder before the first save;
    `tile_generator` parameter ids and `Pattern_Type` values; anisotropic noise streaks horizontal
    by default; PIL loading 16-bit grayscale PNGs as `I;16` but 16-bit RGBA as 8-bit; the
    "harmless log noise" messages; the 3D view black under widget capture.
  - **Fix.** Add checks (enum values, `describe_node` output, an import before the first save, a
    PIL round-trip unit test), or delete the claims.
  - **Resolution: done; two facts corrected** (commit `d9acfee`).
    - **Test:** a check for each fact: five live "designer facts" checks (API inheritance values;
      a `CopiedAndLinked` import before the first save; `tile_generator`'s ids and `Pattern_Type`
      enum from `describe_node`; the direction of anisotropic noise, measured on its preview; the
      log messages after `expose_param`; a grab of the 3D viewport compared with the view's own
      render) and a unit test for PIL (`tests/unit/test_pil_facts.py`, with a hand-built 16-bit
      RGBA PNG).
    - **Cause:** the facts had been observed once and written down, never checked again; two
      were off in their details.
    - **Fix:** confirmed as written: the inheritance values, the `XXXXXX-` prefix (literally six
      X's), `tile_generator`, the noise direction (steps along y 40x those along x), PIL, the log
      messages. Corrected in AGENTS.md: (1) the 3D view isn't black under widget capture but shows
      leftover content that varies between calls, so the check compares the grab with the render
      (they differ by about 80 of 255); (2) unsaved packages copy bitmaps into
      `<OS temp>/Adobe/Adobe Substance 3D Designer/`, the copies stay after the package closes, and
      a later copy of a taken name gets `1-`, `2-`... in front (the self-test now deletes its
      copy). `screenshot_designer`'s description and ROADMAP item 9 no longer say "black".
  - Questioned by TST-13, TST-15 (2026-10-29).

- [x] **PLG-8 · A forced quit at the end of a full self-test crashes Designer** · `server.py` (`quit_designer`'s `exit()` fallback), unknown trigger · confirmed twice, cause unknown · found 2026-10-29
  - **Defect.** In the last two full self-test runs that started their own Designer (19:28 and
    about 20:00 on 2026-10-29), the check "exit() fallback ends it anyway" failed: Designer logged
    a normal shutdown ("Destroy Application"), then wrote a crash dump about 3 s later; the
    process didn't go away for over 30 s, and the relaunch afterwards timed out after 240 s.
  - **Scenario.** The user's Designer won't close (a blocking dialog), so `quit_designer` falls
    back to `exit(0)`, and Designer crashes and hangs instead of quitting.
  - **What's known.** Not reproduced in short sessions: normal quits (3), forced quits on the
    current plugin (3), forced quits after using the 3D view with and without a viewport grab
    (2 + 2), all clean, gone in 4 to 7 s. The last full run that exercised this quit without a
    crash was around 17:30; checks added since: the PLG-1 queue check, HLP-3's failing function
    node, HLP-7's patch of `SDNode.setPropertyValue`, TST-3's unsaved package with a copied bitmap
    and log warning, SRV-3, HLP-4/HLP-10, and the PLG-4 plugin. A probe combining several of them
    was stopped: Claude Code's permission check blocks repeatedly crashing Designer. The newest
    dump's crashing module wasn't read (no minidump reader here).
  - **Fix.** Find the trigger: bisect the self-test (skip groups of the checks above), or read the
    dump with a minidump tool. The user decides how to go on.
  - **Resolution: done** (commit `7213140`).
    - **Test:** the reproduction is the two recorded runs, in which the self-test's "exit()
      fallback ends it anyway" check failed (Designer crashed and the relaunch timed out); Designer
      wasn't crashed again on purpose. The forced-quit check, and the final quit with a modal
      dialog open, now also require that no new crash dump appears in Designer's
      `Sentry-Crashpad/completed`. With the fix, two full runs from a closed Designer passed every
      quit check with no new dump (236/236 each).
    - **Cause:** read from the two dumps with a small minidump reader (exception, module list,
      frame-pointer walk, `atos` on Designer's binary). Both crashed identically: EXC_BAD_ACCESS at
      address 0x1b0 on a `QThreadPoolThread`, in Adobe's licence check
      (`Alg::BinaryHardeningService::runInThread` → `_runBinaryHardeningChecks` → `Eagle::...::runIC`
      → `PHAppInfoDelegateImpl::GetDeviceID` → `optional<Alg::NglUserProfile>` copy). The
      fallback's `QApplication.exit(0)` leaves the event loop, and Designer's teardown destroys the
      licensing profile while that background check is still running. None of the self-test's
      own checks was the trigger: a full run lasts long enough for the check to be running at the
      quit, while the short probes quit within seconds of starting.
    - **Fix:** the fallback after 5 s is `os._exit(0)` (`quit_designer` in `designer_helpers.py`):
      the process ends without a teardown, so no teardown race can happen, whatever runs in the
      background. Designer doesn't save its window layout on this path, which runs only when a
      window refused to close. AGENTS.md (Designer UI) records the crash and the reason.
  - Questioned by HLP-12 (2026-10-29).

- [x] **PLG-9 · Designer crashed right after a self-test run against the user's open Designer** · `tests/test_all_tools.py` (end of the run), Designer's `FileSystemWatcher` · confirmed once, cause plausible · found 2026-10-29
  - **Defect.** At 20:38 on 2026-10-29, one second after a full self-test against an
    already-running Designer ended (230/230 passed), Designer crashed: EXC_BAD_ACCESS at address 0
    on the main thread in `Alg::Core::FileSystemWatcher::onFileChanged`, delivered through
    `FileSystemWatcherMgr` from `QFileSystemWatcher`. The log has no shutdown, so it was a crash,
    not a quit.
  - **Scenario.** The user's Designer is open; the self-test unloads its packages and then deletes
    its temporary folder, and a file-change signal for one of those files reaches a watcher
    object that is already gone. The user's Designer goes down, with any unsaved work.
  - **What's known.** It was the first run with the new HLP-6 check, which opened two saved
    packages in editor views and unloaded them in the same call, the pattern AGENTS.md (Portals)
    warns about. Earlier runs unloaded packages that were never opened in a view, with no crash.
    That check now unloads in a separate call after a pause. Not reproduced or proven fixed: the
    runs since started their own Designer and quit it before deleting the folder.
  - **Fix.** Run the self-test against an open Designer a few times and watch for a dump in
    `Sentry-Crashpad/completed`; if it recurs, delete the temporary files only after Designer has
    had time to drop its watchers, or keep them.
  - **Resolution: done, as far as three runs can show** (commit `3531359`; the change itself is in
    commit `7213140`).
    - **Test:** three full self-test runs in a row against one open Designer, each followed by a
      10 s wait, a look for new dumps in `Sentry-Crashpad/completed` and a check that Designer was
      still running: 230/230 each, Designer alive, no new dump. Before the change: one run, one
      crash.
    - **Cause (likely, not proven):** the HLP-6 check unloaded two packages in the same call that
      had opened them in editor views, so Designer's watchers for their files outlived the
      teardown, and the self-test's deletion of the temporary folder fired one.
    - **Fix:** that check unloads its packages in a separate call after a short pause, as
      `set_link_display` does (AGENTS.md, Portals). If a dump like this shows up again, reopen
      with the dump's stack.
  - Questioned by TST-16 (2026-10-29).

## Low-medium

- [x] **PLG-4 · Requests are read before authentication with no total time limit, and connections are unbounded** · `__init__.py:122-131, 164` · confirmed; needs local access · found 2026-10-29
  - **Defect.** The read timeout applies per `recv`; up to 64 MiB is buffered before the auth check;
    one thread per connection, no cap.
  - **Scenario.** A local process opens many slow or large connections and exhausts Designer's
    memory or threads without knowing the token.
  - **Fix.** A total deadline, a cap on concurrent handlers, optionally `auth` before the body.
  - **Resolution: done (deadline and cap; `auth` before the body not done)** (commit `ec6ad79`).
    - **Test:** two plugin unit tests failed: a client sending one byte every 0.25 s stayed
      connected well past the read timeout, and a third connection beyond a limit of two still got
      a greeting.
    - **Cause:** `_read_request` set the timeout per `recv`, so any trickle reset it; the accept
      loop started a thread for every connection without counting them.
    - **Fix:** in the plugin, `_read_request` uses one deadline for the whole request
      (`READ_TIMEOUT`, 30 s), and the accept loop serves at most `MAX_CLIENTS` (16) connections at
      once, closing others straight away. Up to 16 x 64 MiB can still be buffered before the auth
      check; sending `auth` first would need a protocol change in every client, so it wasn't done.
      README's Security section describes the limits. Plugin reinstalled; live self-test passes.
  - Questioned by PLG-10 (2026-10-29).

- [x] **SRV-5 · Quick edits have a fixed 60 s limit for the whole batch** · `server.py:337` · plausible · found 2026-10-29
  - **Defect.** `apply_edits`, `create_graph(save_path)`, `import_bitmap` and `arrange_graph` share
    `_edit`'s 60 s limit.
  - **Scenario.** A big batch loading many library packages is aborted midway, leaving a half-built
    graph.
  - **Fix.** Scale the limit with the number of ops, or use 300 s.
  - **Resolution: done** (commit `ec6ad79`).
    - **Test:** a unit test captured the limit for a 50-op `apply_edits` batch: 60 s.
    - **Cause:** `_edit` hard-coded 60 s for every quick edit, whatever its size.
    - **Fix:** `_edit` in `server.py` allows 300 s; the limit only stops a hang, and a big batch or
      a first use of many library packages can take minutes.

- [x] **HLP-3 · `expose_param` cleanup leaves the function graph it created** · `designer_helpers.py:968-974` · plausible (needs an API failure midway) · found 2026-10-29
  - **Defect.** On failure only the new graph input is deleted; the function graph on the parameter
    stays, so `sweep_param` (and now `set_params`) refuse the parameter as driven.
  - **Fix.** Delete the property graph too if this call created it.
  - **Resolution: done** (commit `ec6ad79`).
    - **Test:** a live check runs `expose_param` with the float4 getter renamed to a function node
      type that doesn't exist, so it fails right after the function graph is created. Before the
      fix the graph input was removed but the function graph stayed (`LEFT_GRAPH=True`).
    - **Cause:** the cleanup only deleted the new graph input, not the function graph created on
      the parameter.
    - **Fix:** `expose_param` remembers whether it created the function graph and deletes it too
      (`deletePropertyGraph`) when a later step fails.
  - Questioned by HLP-15 (2026-10-30).

- [x] **PLG-10 · The connection cap also locks out `cancel` and `status`** · `plugin/.../__init__.py:176-183, 250-256` · confirmed · verified by hand · found 2026-10-29
  - **Defect.** `MAX_CLIENTS` (PLG-4) counts every connection being served, and a client waiting for
    its queued job keeps its slot for up to `QUEUE_WAIT` (900 s): `_serve` releases it only after
    `_handle` returns.
  - **Scenario.** A long script runs while 15 or more requests wait behind it (parallel tool calls,
    retries): `cancel_designer_job` is closed without a greeting ("the bridge closed the
    connection"), so the job blocking everything can't be aborted. README says the plugin answers
    `status`/`cancel` while a script runs. Questions PLG-4's resolution.
  - **Fix.** Count a connection only until it is authenticated (or release the slot before waiting
    for the job), or keep a slot or two for control commands; a unit test with the cap full of
    waiting clients.
  - **Resolution: done** (commit `e501f5c`).
    - **Test:** `test_control_commands_are_answered_while_queued_jobs_fill_the_cap` fills a cap of
      two with authenticated clients whose jobs wait in the queue: the `status` connection was
      reset ("Connection reset by peer").
    - **Cause:** a connection kept its slot until its reply was sent, which for a queued job means
      up to `QUEUE_WAIT`, though the cap exists only to stop unauthenticated connections tying the
      plugin up (PLG-4).
    - **Fix:** `_serve` passes a `release()` that `_authorised` calls once the request is
      authenticated (and `_serve` again in its `finally`, at most once in all), so the cap counts
      only connections that haven't authenticated. `status` and `cancel` get through behind
      queued jobs; PLG-4's cap test still passes. README (Security) updated; plugin reinstalled.

- [x] **SRV-14 · `set_link_display`'s copy of the saved file loses relative bitmap paths** · `mcp_server/server.py:1278-1279` · confirmed · verified by hand · found 2026-10-29
  - **Defect.** The "before portals (file on disk)" snapshot is `shutil.copy2(path, ...)` into the
    snapshot folder, but Designer writes bitmap paths relative to the `.sbs` (SRV-3's own cause).
  - **Scenario.** A package with a copied bitmap (`import_bitmap(embed='copy')`), then
    `set_link_display`: that snapshot, the only copy of the previously saved state, opens with
    missing bitmaps. Questions SRV-3's resolution, which fixed `snapshot_graph` only.
  - **Fix.** Rewrite the copy's resource paths for its new folder (or make them absolute); extend
    the SRV-3 live check to the file-on-disk copy.
  - **Resolution: done** (commit `ee9e2fc`).
    - **Test:** `test_set_link_displays_copy_of_the_saved_file_keeps_relative_paths_working` runs
      `set_link_display` on a saved `.sbs` with a relative bitmap path and a relative dependency:
      in the copy both pointed nowhere ("missing ['p.resources/XXXXXX-img.png', 'other.sbs']").
    - **Cause:** the copy was `shutil.copy2` into the snapshot folder, which keeps the bytes, so
      every path Designer wrote relative to the original folder broke.
    - **Fix:** `_copy_sbs()` in `server.py` rewrites relative `<filepath>` and `<filename>` paths
      for the copy's folder (library `sbs://` references and absolute paths left alone; another
      Windows drive gets an absolute path) and keeps the original's timestamps, so the copy still
      never sorts as the latest snapshot (SRV-1). A new live check resolves every bitmap path in
      the self-test's file-on-disk copy: all reachable.
  - Questioned by SRV-17 (2026-10-30).

- [x] **SRV-15 · `launch_designer` waits out a Designer that exits instead of starting one** · `mcp_server/server.py:1379-1404` · confirmed path, plausible in practice · found 2026-10-29
  - **Defect.** `running = _designer_running()` is checked once before the wait; if that process
    exits during the wait, nothing is started, and the error still says Designer "is already
    running".
  - **Scenario.** A Designer that is shutting down, or hung after a crash (PLG-8's symptom: the
    process stayed over 30 s): `launch_designer()` waits the full `wait_s`, then reports a running
    Designer that no longer exists. Questions SRV-10's resolution.
  - **Fix.** In the loop, when the process is gone, launch then; a unit test where
    `_designer_running` turns False.
  - **Resolution: done** (commit `ee9e2fc`).
    - **Test:** `test_launch_starts_designer_when_the_running_one_exits_during_the_wait` (the
      process is there at first, then gone): "Designer is already running, but its bridge did not
      answer within 60s", and nothing was started.
    - **Cause:** the process was looked for once, before the wait.
    - **Fix:** while waiting, each failed status check looks for the process again; once it is
      gone, `launch_designer` starts Designer and goes on waiting for the new one. Docstring
      updated.
  - Questioned by SRV-19 (2026-10-30).

- [x] **HLP-12 · The `os._exit` fallback is armed on every quit, so it can cut off a normal shutdown** · `mcp_server/designer_helpers.py:732-733` · confirmed · verified by hand · found 2026-10-29
  - **Defect.** `QTimer.singleShot(5000, lambda: os._exit(0))` runs whether or not the windows
    closed. If Designer's normal shutdown is still processing events at 5 s, the process is killed
    mid-shutdown: settings and layout unsaved, log and crash reporter cut off. The old `exit(0)`
    did no such harm.
  - **Scenario.** A normal `quit_designer` whose shutdown takes longer than 5 s (normal quits were
    measured at 4 to 7 s before the process was gone). The self-test checks only "gone, no dump",
    so it wouldn't notice. Questions PLG-8's resolution.
  - **Fix.** Fire the fallback only if a top-level window is still visible (or cancel it on
    `aboutToQuit`); a live check that a plain quit reaches Designer's "Destroy Application" log line.
  - **Resolution: done** (commit `e501f5c`).
    - **Test:** a live check gives the final normal quit a slow shutdown: an `aboutToQuit` handler
      that keeps processing events for 7 s, then writes a marker file. Before the fix the marker
      never appeared ("the process was ended under it"): `os._exit` fired at 5 s mid-shutdown.
    - **Cause:** the fallback timer was armed on every quit and fired whatever state Designer was
      in; any shutdown step processing events after 5 s let it run.
    - **Fix:** `quit_designer` in `designer_helpers.py` ends the process only if a top-level window
      is still visible and `aboutToQuit` hasn't been emitted, so only a quit that was refused is
      forced. The slow shutdown now finishes (quit in 8 s); the forced quit and the quit with a
      modal dialog still pass, with no crash dump. AGENTS.md (Designer UI) says so.
  - Questioned by HLP-17, TST-19 (2026-10-30).

- [x] **HLP-13 · An empty function graph counts as "driven" in three places, but not in `expose_param`** · `mcp_server/designer_helpers.py:134-142, 572-579, 1199-1206` vs `993-995` · plausible · found 2026-10-29
  - **Defect.** `set_params`, `sweep_param` and `describe_graph` treat any property graph as driving
    the value; `expose_param` checks `len(existing.getNodes())`.
  - **Scenario.** A parameter is left with an empty function graph (a failed HLP-3 cleanup, or one
    emptied in the UI): `set_params` refuses "driven by a function" while `expose_param` accepts it.
  - **Fix.** One `_driving_graph(node, prop)` that ignores a graph with no nodes, used in all four.
  - **Resolution: done** (commit `d1b7f29`).
    - **Test:** a live check puts an empty function graph on a levels parameter and sets it:
      without the fix, "levelouthigh is driven by a function; set that instead".
    - **Cause:** three places asked only whether a property graph existed; `expose_param` alone
      asked whether it had nodes.
    - **Fix:** `_driving_graph()` in `designer_helpers.py` returns a function graph only when it has
      nodes; `set_params`, `sweep_param`, `describe_graph` and `expose_param` all use it. The value
      is set and `describe_graph` shows it, not `<- a function`.
  - Questioned by HLP-16, TST-20 (2026-10-30).

- [x] **TST-13 · The "harmless log messages" fact check can't fail** · `tests/test_all_tools.py:812-813` · confirmed · verified by hand · found 2026-10-29
  - **Defect.** It requires `' 0 matching lines' not in t`, but the header is `... (0 matching
    lines, showing 0)`: a `(`, not a space, precedes the count, so the condition is always true.
    Against a long-running Designer, earlier messages would satisfy it anyway.
  - **Scenario.** Designer stops logging the messages AGENTS.md calls harmless noise; the check
    still passes. Questions TST-3's resolution.
  - **Fix.** Parse the count (`\((\d+) matching`) and require at least one new line since this
    run's own `expose_param`.
  - **Resolution: done, and it hid a wrong search** (commit `e501f5c`).
    - **Test:** the rewritten check counts both messages before and after an `expose_param` made
      right there. It failed: "No output node defined" went from 18 to 19, but the second message
      stayed at 0.
    - **Cause:** two faults hid each other. The old condition compared against a header it could
      never match, so it always passed; and its search text "Get nodes don't have a variable name"
      never matched either, because Designer logs `Some <b>Get</b> nodes don't have a variable
      name`, with HTML tags.
    - **Fix:** the check parses the counts from the headers and requires both to grow; it searches
      for "nodes don't have a variable name". Live: 18 to 19 and 2 to 3. The fact in AGENTS.md was
      right.

- [x] **TST-14 · The HLP-8 clipboard check clears your clipboard without checking it came back** · `tests/test_all_tools.py:1048-1057` · plausible · found 2026-10-29
  - **Defect.** It calls `cb.clear()` on the real clipboard and restores a `QMimeData` copy of its
    formats, on every platform and with the user's own Designer running, but never compares
    before and after as the `3d` check does with `clipboard_fingerprint()`.
  - **Scenario.** Data Qt can't copy (lazily provided or private formats) is lost silently. README
    says the clipboard check runs on macOS only, which no longer holds.
  - **Fix.** macOS only and inside the same fingerprint comparison, or skip it when Designer was
    already running; README to match.
  - **Resolution: done; no loss reproduced** (commit `ee9e2fc`).
    - **Test:** the check now compares `clipboard_fingerprint()` before and after and fails if the
      clipboard didn't come back. Live on macOS it came back intact (passes), so the data loss
      wasn't reproduced; the guard is what was missing.
    - **Cause:** the HLP-8 fact needs an empty clipboard, so it clears the system clipboard, and
      it was added without the before/after comparison the `3d` check has.
    - **Fix:** it runs only where the clipboard can be compared (macOS; skipped elsewhere), inside
      that comparison. README's "the clipboard check runs on macOS only" holds again. The restore
      copies formats as `screenshot_designer('3d')` does, so a lossy restore would show in both.

- [x] **SRV-17 · `_copy_sbs` rewrites Designer's `?himself` dependency as a file path** · `mcp_server/server.py` (`_copy_sbs`) · confirmed · verified by hand · found 2026-10-30
  - **Defect.** Only values with `://` or absolute paths are skipped, so `<filename v="?himself"/>`,
    the dependency a package uses for instances of its own graphs, becomes `../../.../?himself`.
    Designer writes this marker (its own library packages, such as `3d_functions.sbs`, have it).
  - **Scenario.** A package with an instance of one of its own graphs, then `set_link_display`: the
    "file on disk" snapshot opens with those instances unresolved. Questions SRV-14's resolution.
  - **Fix.** Skip values starting with `?` (or rewrite only paths whose target exists next to the
    original); add `?himself` to the unit test.
  - **Resolution: done** (commit `780f468`).
    - **Test:** the `_copy_sbs` unit test now includes a `<filename v="?himself"/>` dependency: it
      came out as `../../project/?himself`.
    - **Cause:** only `://` values and absolute paths were skipped; `?himself` is neither.
    - **Fix:** `_copy_sbs` leaves values starting with `?` alone; its docstring says so.

- [x] **HLP-15 · `expose_param` leaves a half-made `get` node in a reused empty function graph** · `mcp_server/designer_helpers.py` (`expose_param`) · plausible · found 2026-10-30
  - **Defect.** When the parameter already has an empty function graph, `expose_param` reuses it; if
    a step after `fg.newNode(get)` fails, only the new input is deleted (`created_graph` is False), so
    the graph keeps a node reading a deleted input and now counts as "driven" (HLP-13).
  - **Scenario.** An exposure that fails midway on such a parameter: `set_params` and `expose_param`
    then refuse it as driven by a function. A gap in HLP-3's resolution, noted after the
    2026-10-29 review and reported again here.
  - **Fix.** On failure delete the `get` node it added (or the whole property graph, since it was
    empty before).
  - **Resolution: done** (commit `4da1095`).
    - **Test:** a live check gives a fresh levels node an empty function graph, makes its
      `setOutputNode` fail, and runs `expose_param`: `LEFT_NODES=1`.
    - **Cause:** the clean-up deleted the function graph only if this call created it.
    - **Fix:** a reused graph loses the `get` node added to it (`fg.deleteNode(get)`).

- [x] **HLP-16 · HLP-13's premise is untested: does Designer ignore an empty function graph?** · `mcp_server/designer_helpers.py` (`_driving_graph`), `tests/test_all_tools.py` (HLP-13 check) · plausible · found 2026-10-30
  - **Defect.** `_driving_graph` treats a graph with no nodes as driving nothing, so the stored
    constant counts; the live check only sees that `set_params` doesn't refuse, never that the
    output follows the new value.
  - **Scenario.** If Designer ignores the constant while any property graph exists, `set_params`
    and `sweep_param` now report changes the output doesn't show. Questions HLP-13's resolution.
  - **Fix.** In the check, measure the node (`node_stats`) before and after `set_params`; if the
    output doesn't change, treat an empty graph as driving after all (or delete it before setting).
  - **Resolution: not a bug; the premise holds, now measured** (commit `780f468`).
    - **Test:** a live "designer facts" check on a levels node: max 0.976 at `levelouthigh` 1.0,
      0.492 at 0.5; adding an empty function graph brings it back to 0.976, because adding the graph
      reset the stored value to its default (it reads back as 1.0); `set_params` to 0.5 then deletes
      the empty graph and the output is 0.492 again. A first version of the check, which set the
      value with the graph already there, measured nothing: setting a value deletes the graph.
    - **Why not:** the output always follows the stored value, and the API can't produce an empty
      graph beside a stored value it ignores (adding the graph resets the value, setting the value
      removes the graph), so treating an empty graph as not driving is right. The three facts are
      in AGENTS.md (sd API gotchas, exposing a parameter).
  - Questioned by TST-22, TST-24 (2026-10-30).

- [x] **INS-16 · The installer's folder swap has no rollback, and leftovers aren't uninstalled** · `install.py` (`install_plugin`) · plausible · verified by hand · found 2026-10-30
  - **Defect.** If `os.rename(dst, old)` fails (Windows: a handle open in the folder), `<name>.new`
    stays beside the plugin; if `os.rename(new, dst)` fails, there is no plugin at `dst`, only
    `.new` and `.old`; `rmtree(old, ignore_errors=True)` can leave a partial `.old` silently. Both
    hold a full plugin, so Designer could load two with the same module name, and `uninstall.py`
    knows neither. Questions INS-12's resolution.
  - **Fix.** Roll back on failure (rename `old` back, remove `new`, re-raise), report a leftover
    `.old`, and have the uninstaller remove our `.new`/`.old` (ownership checked).
  - **Resolution: done** (commit `780f468`).
    - **Test:** `test_a_failed_swap_rolls_back` makes the first or the second rename fail: a
      `<name>.new` stayed beside the plugin, or there was no plugin at all; and
      `test_removes_leftover_copies_of_the_plugin`: the uninstaller left our `.new`/`.old` copies.
    - **Cause:** the swap had no failure handling, and the uninstaller only knew the plugin's name.
    - **Fix:** `install_plugin` renames the old plugin back if the swap fails, removes the new copy
      and re-raises; a leftover `.old` that can't be deleted is reported; leftover `.new`/`.old`
      folders that aren't ours stop the installer instead of being deleted. `uninstall.py` removes
      our `.new` and `.old` copies (ownership checked).
  - Questioned by INS-19, INS-20, INS-21 (2026-10-30).

- [x] **TST-19 · The HLP-12 check never reaches the `aboutToQuit` guard** · `tests/test_all_tools.py` (slow-shutdown check) · confirmed · verified by hand · found 2026-10-30
  - **Defect.** The test connects its slow handler to `aboutToQuit` before `quit_designer` connects
    its flag, and Qt calls slots in connection order, so the flag is still empty when the fallback
    fires; the process survives only because no window is visible by then.
  - **Scenario.** Remove `not shutting_down` from the guard and the check still passes, though
    AGENTS.md documents that half. Questions HLP-12's resolution (its test).
  - **Fix.** Connect the slow handler after `quit_designer` has connected its own (a short
    `QTimer.singleShot`), and show a small window inside it, so only the `aboutToQuit` guard can
    keep the process alive.
  - **Resolution: done** (commit `4da1095`).
    - **Test:** the slow-shutdown check now shows a window from its `aboutToQuit` handler, so "a
      window is visible" holds at 5 s and only the "shutdown has begun" test can keep the process
      alive. Before the fix the handler was killed.
    - **Cause:** the guard's flag came from an `aboutToQuit` slot connected after the test's, so it
      was set too late; the test passed only because no window was visible.
    - **Fix:** `quit_designer` also marks the shutdown as begun once every window accepted its
      Close (none visible after `close_windows`), which doesn't depend on slot order. A first
      attempt, "the main event loop has returned" (`QThread.loopLevel() == 0` in an `aboutToQuit`
      slot), failed live: in Designer the level isn't 0 there.
  - Questioned by HLP-19, TST-23 (2026-10-30).

- [x] **TST-25 · The HLP-19 fact check passes whether or not Designer quits by itself** · `tests/test_all_tools.py` (HLP-19 check) · confirmed · verified by hand · found 2026-10-30
  - **Defect.** The "prompt" is created inside the close loop, so it isn't in the list
    `close_windows` iterates, stays visible, and `closed_all` is never set: the fallback forces the
    process at about 5 s. `took < 30` and "no crash dump" hold either way (`os._exit` writes none),
    so AGENTS.md's "gone in 2 s" is untested; the comment's "about 35 s" is wrong too. Questions
    HLP-19's resolution.
  - **Fix.** Tell a normal quit from a forced one (a marker written from an `aboutToQuit` slot,
    which `os._exit` never reaches, or `took` well under 5 s); correct the comment.
  - **Resolution: done** (commit `07c12c0`).
    - **Test:** the check now also requires a marker written from an `aboutToQuit` slot, which
      only a quit by itself emits; a new "designer facts" check shows the forced quit (`os._exit`)
      writes none. Live: forced quit, no marker; quit with the prompt showing, marker written, gone
      after 2 s. The comment no longer says "about 35 s".
    - **Cause:** the old check accepted any exit under 30 s without a crash dump, which the
      fallback's forced exit at about 5 s also gives.

- [x] **TST-26 · The HLP-20 check deletes the whole snapshot folder of a library graph's name** · `tests/test_all_tools.py` (HLP-20 check) · confirmed · verified by hand · found 2026-10-30
  - **Defect.** It removes `<snapshot dir>/<identifier>` for the first library graph found, a name
    not unique to the test, so the user's own snapshots of a graph with that name would go too.
    Questions HLP-20's resolution.
  - **Fix.** Delete only the snapshot file the result names, then the folder only if it is empty.
  - **Resolution: done** (commit `07c12c0`).
    - **Fix:** the check deletes only the snapshot file its result names, and the folder only if
      nothing else is in it; live, the folder (the check's own) was removed as empty.

## Low

- [x] **PLG-5 · `stop()` may keep the port bound and leaves queued clients hanging** · `__init__.py:250-256` · queued clients confirmed, port plausible · found 2026-10-29
  - **Defect.** The socket is closed without `shutdown()`, so a blocked `accept()` may keep the port;
    queued jobs are never failed, so their clients hang up to 900 s.
  - **Fix.** `shutdown` before `close`, then fail every queued job.
  - **Resolution: done for queued clients; the port half not reproduced** (commit `e13ee76`).
    - **Test:** `test_stop_answers_queued_clients_and_frees_the_port` queues a job with nothing
      draining, then calls `stop()`: the client got no reply (it would have waited out
      `QUEUE_WAIT`, 900 s). With the `shutdown()` line removed again, the accept thread still
      ended and the port could be bound at once: on macOS `close()` alone wakes a blocked
      `accept()`.
    - **Cause:** `stop()` closed the listening socket and stopped the timer, but left queued jobs
      in the queue, so nothing ever set their `done` events.
    - **Fix:** `stop()` answers every queued job with "Designer is closing; the script was not
      run". It also calls `shutdown()` before `close()`, a defensive line for platforms where
      `close()` doesn't wake `accept()`.
  - Questioned by PLG-12 (2026-10-29).

- [x] **PLG-6 · Only the client is authenticated** · `server.py:139-155`, `sd_run.py:23-41` · confirmed · found 2026-10-29
  - **Defect.** While Designer is closed, any process on port 9877 receives the full script and can
    return a made-up reply (the token stays safe).
  - **Fix.** Mutual authentication (the plugin also signs a client nonce), or document as accepted.
  - **Resolution: won't fix, documented as accepted** (commit `e13ee76`; agreed with the user 2026-10-29).
    - **Why not:** a squatter running as the same user could read the owner-only token file
      anyway, so mutual authentication only helps against another user account on the same
      machine; scripts carry no secrets, and the token stays safe either way
      (`test_clients_never_send_the_token`). Mutual authentication would mean an extra round trip
      and a protocol change in the plugin, the server, `sd_run.py` and the self-test together.
    - **Docs:** README, Security, says only the client is authenticated and why that is accepted.

- [x] **PLG-7 · `status` counts abandoned jobs as queued** · `__init__.py:185` · confirmed · found 2026-10-29
  - **Fix.** Keep a separate count of live jobs.
  - **Resolution: done** (commit `e13ee76`).
    - **Test:** `test_status_does_not_count_abandoned_jobs` lets a job time out in the queue while
      nothing drains it: status said "idle, 1 queued".
    - **Cause:** status reported `jobs.qsize()`, and an abandoned job stays in the queue until
      `_drain` skips it.
    - **Fix:** status counts only the queued jobs not marked abandoned, under the lock. Plugin
      reinstalled and Designer restarted.
  - Questioned by PLG-14 (2026-10-30).

- [x] **SRV-6 · `sbsar_info` ignores `sbsrender`'s return code** · `server.py:1561-1562` · confirmed · found 2026-10-29
  - **Defect.** Errors come back as a normal result.
  - **Fix.** Raise a ToolError on a non-zero return code.
  - **Resolution: done** (commit `b48fb86`).
    - **Test:** a unit test with `sbsrender info` exiting 1 and an error on stderr: `sbsar_info`
      returned the error text as a normal result instead of failing.
    - **Cause:** the return code was never looked at; stderr was the fallback output.
    - **Fix:** `sbsar_info` raises "sbsrender info failed (exit N): <error>" on a non-zero exit.

- [x] **SRV-7 · `set_link_display` messages report wrong counts** · `server.py:1229-1230, 1248-1249` · confirmed · found 2026-10-29
  - **Defect.** They always say "N of N selected" or "0 of 0".
  - **Fix.** Return the number selected before the "already in this mode" filter.
  - **Resolution: done** (commit `b48fb86`).
    - **Test:** a unit test asking `_select_links` for the selected count (2 selected, 1 already a
      portal) failed: the function returned only the links to change and the total.
    - **Cause:** the count of selected links was dropped once links already in the wanted mode
      were filtered out, so the messages printed the changed count twice ("N of N", "0 of 0").
    - **Fix:** `_select_links` returns (to change, selected, total) and both messages use the
      selected count; live, "nothing to change" now says "0 of 1 selected link(s)".

- [x] **SRV-8 · Pixel decoding mishandles 3-channel, BGR and luminance-alpha formats** · `server.py:504-512` · plausible · found 2026-10-29
  - **Defect.** `RGB16` reads as one channel; BGR and LUMALPHA formats are mishandled or refused.
  - **Scenario.** `node_stats`, `check_tiling`, `compare_to_reference` on such a texture (an imported
    JPG, for example).
  - **Fix.** Parse the channel prefix explicitly; swap B and R for BGR.
  - **Resolution: not reproduced; decoder fixed defensively** (commit `02e485c`).
    - **Test:** `test_decode_other_channel_layouts` feeds all ten missing `SBSPixelFormat` names to
      `_decode_pixels`. Before the fix, `RGB*` and `BGR8` failed with "cannot reshape array of size
      18 into shape (2,3,1)", and `BGRA8` and `LUMALPHA*` were refused as unsupported. A new live
      check ("designer facts: imported JPG and grey+alpha PNG compute as RGBA8") shows the review's
      scenario doesn't happen: Designer computes an imported RGB JPG, RGB PNG and grey+alpha PNG as
      `RGBA8`, and no output in another layout has been seen.
    - **Why not:** Designer's compute converts imported bitmaps to `RGBA*` or `LUM*`, the two
      layouts the decoder already handled.
    - **Fix (defensive):** `_decode_pixels` reads the channel prefix from a table (`LUMALPHA`,
      `LUM`, `RGBA`, `BGRA`, `RGB`, `BGR`), swaps B and R back, and keeps 3 colour channels or
      grey + alpha; `_channel_names` gives `node_stats` and `sweep_param` the right channel
      letters. AGENTS.md (Pixel precision) records the fact.

- [x] **SRV-9 · `compare_to_reference` drops alpha from a grayscale+alpha reference** · `server.py:750` · confirmed · found 2026-10-29
  - **Defect.** `LA` is converted to `L`, though transparent reference pixels are documented as ignored.
  - **Fix.** Treat `LA` like RGBA for the mask.
  - **Resolution: done** (commit `663354a`).
    - **Test:** `test_compare_ignores_transparent_pixels_of_a_grayscale_alpha_reference` (half
      opaque grey, half transparent black, against a grey node): no "ignoring 50.0% transparent"
      line, and a luma shift of -0.251 from the black pixels.
    - **Cause:** `_load_reference` converted `LA` to `L`, dropping alpha, and the masks only read
      alpha from an `RGBA` layout.
    - **Fix:** an `LA` reference stays layout `L` with alpha as a second channel; a new `_alpha()`
      gives the alpha of either layout, used for the mask and the histogram.

- [x] **SRV-10 · `launch_designer` relaunches whenever the status check fails** · `server.py:1311-1323` · plausible · found 2026-10-29
  - **Defect.** It launches even when Designer runs but is busy, or its plugin failed to load.
  - **Fix.** Check the process is running before launching.
  - **Resolution: done** (commit `02e485c`).
    - **Test:** `test_launch_waits_for_a_running_designer_instead_of_starting_another` (a Designer
      process exists, the bridge doesn't answer): "started a second Designer" (`open -a` was
      called; on Windows `os.startfile` opens another instance).
    - **Cause:** `launch_designer` took any failed status check as "not running", without
      looking for the process.
    - **Fix:** if `_designer_running()` finds a process, `launch_designer` doesn't start Designer.
      It waits for the bridge and reports "Designer already running" (leaving the Home screen
      alone), or says "Designer is already running, but its bridge did not answer within Ns",
      naming a dialog or a failed plugin load as likely causes. Docstring updated.
  - Questioned by SRV-15 (2026-10-29).

- [x] **SRV-11 · `run_designer_script` reads the script without an encoding** · `server.py:234` · confirmed · found 2026-10-29
  - **Scenario.** A UTF-8 script fails on a cp1252 Windows locale.
  - **Fix.** `encoding='utf-8'`; `errors='replace'` for `_run_tool` output.
  - **Resolution: done** (commit `02e485c`).
    - **Test:** `test_scripts_and_tool_output_are_read_as_utf8_whatever_the_locale` runs the server
      in a Latin-1 locale with UTF-8 mode off (standing in for cp1252): the script's `'→ é ✓'`
      reached Designer garbled ("SCRIPT_BAD"), and a tool's UTF-8 output came back as
      `'â\x86\x92 â\x9c\x93'`. On real cp1252 some bytes raise `UnicodeDecodeError` instead.
      The live self-test now runs a script printing `→ é ✓` and checks it arrives intact.
    - **Cause:** `open(path)` and `subprocess.run(text=True)` use the locale's encoding.
    - **Fix:** `run_designer_script` opens the file as UTF-8, and `_run_tool` decodes output as
      UTF-8 with `errors='replace'`.

- [x] **SRV-12 · Raw exceptions instead of clear errors in edge cases** · `server.py` · confirmed · found 2026-10-29
  - **Defect.** `preview_maps` on a folder without PNGs or with an unknown name; `_select_links` on a
    graph without `compNodes`; `set_link_display` reopening a graph whose identifier is ambiguous
    after a successful edit (reported as a failure).
  - **Fix.** Guard each and return a ToolError (a warning for the reopen).
  - **Resolution: done** (commit `663354a`).
    - **Test:** `test_preview_maps_explains_what_is_missing` (no PNGs: `ValueError: max() iterable
      argument is empty`; unknown name and missing folder: `FileNotFoundError`),
      `test_links_of_a_graph_without_nodes` (`TypeError: 'NoneType' object is not iterable`),
      `test_set_link_display_reports_success_when_the_reopen_fails` (the edited, reloaded package
      came back as the reopen's ToolError).
    - **Cause:** none of these paths checked its input: `preview_maps` listed and opened files
      blindly, `_select_links` iterated `find('compNodes')`, which is None for a graph without
      nodes, and the reopen's error escaped after the edit had succeeded.
    - **Fix:** `preview_maps` says "not a folder", "no .png files in ..." or "no map called 'x'
      ...; there are: ..."; `_select_links` uses `findall('compNodes/compNode')`; a failed reopen
      becomes "WARNING: could not reopen <graph>: <why>" in the success message.

- [x] **HLP-4 · `delete_nodes` and `move_nodes` stop halfway on a bad id** · `designer_helpers.py:623-629, 882-887` · confirmed · found 2026-10-29
  - **Defect.** Ids are resolved one at a time, so earlier ones are already applied.
  - **Fix.** Resolve all ids first.
  - **Resolution: done** (commit `6911082`).
    - **Test:** two live checks with a valid id and a missing one failed: `delete_nodes` deleted the
      valid node before raising, so the follow-up `move_nodes` check had nothing left to move.
    - **Cause:** each id was looked up and acted on in the same loop.
    - **Fix:** both look up every id first, then delete or move.

- [x] **HLP-5 · `apply_edits` says "its node was added" when the definition failed** · `designer_helpers.py:1128-1131` · confirmed · found 2026-10-29
  - **Fix.** Record whether the node was created before deciding the message.
  - **Resolution: done** (commit `b48fb86`).
    - **Test:** live, `apply_edits` with an `add` of a definition that doesn't exist (and params)
      said "(its node was added before the failure)". Two self-test checks now cover it: a bad
      definition gets no such note, an `add` whose params fail does.
    - **Cause:** the note was decided from the op's fields (an `add` with params and no ref), not
      from whether a node was created.
    - **Fix:** `apply_edits` counts the graph's nodes before each op and adds the note only when
      an `add` or `bitmap` op failed after the count went up.

- [x] **HLP-6 · Two places match graphs by identifier only, not by package** · `designer_helpers.py:852-857, 1354` · confirmed; matters only with duplicate names · found 2026-10-29
  - **Defect.** The `open_graph` node_id path and `package_file_of`'s `OPEN=` line.
  - **Fix.** Compare `getPackage().getUID()` too.
  - **Resolution: done** (commit `e13ee76`).
    - **Test:** two live checks with two saved packages, each holding a graph named
      `mcp_selftest_dup`, B in the editor. `package_file_of(A)` printed `OPEN=1`.
      `open_graph(B, node_id=...)` raised `APIException: SDApiError.Undefined`, because the first
      view showing that name belonged to A.
    - **Cause:** both places compared identifiers only; `find_graph` alone also compared package
      UIDs.
    - **Fix:** one `_same_graph()` (identifier and package UID), used by `find_graph`, by
      `open_graph`'s choice of view, and by `package_file_of`'s `OPEN=` line.

- [x] **HLP-7 · A failed restore in `sweep_param` skips restoring the inheritance** · `designer_helpers.py:1181-1185` · confirmed · found 2026-10-29
  - **Defect.** The original error is also replaced by the restore error.
  - **Fix.** Nested try/finally.
  - **Resolution: done** (commit `6911082`).
    - **Test:** a live check sweeps `$outputsize` with `SDNode.setPropertyValue` made to fail when
      it puts the original value back; the inheritance stayed Absolute instead of RelativeToInput.
    - **Cause:** the value and the inheritance were restored one after the other in the same
      `finally`, so a failure in the first skipped the second.
    - **Fix:** the inheritance is restored in an inner `finally`, so it goes back either way; the
      first error is still the one raised.

- [x] **HLP-8 · An empty clipboard can break the 3D screenshot** · `designer_helpers.py:336-340` · plausible · found 2026-10-29
  - **Defect.** `mimeData()` returning `None` fails before the render starts.
  - **Fix.** Treat `None` as no formats.
  - **Resolution: not reproduced; guarded defensively** (commit `02e485c`).
    - **Test:** a new live check ("designer facts: an empty clipboard has mimeData (no formats),
      not None") clears the clipboard and restores it, the way the 3D capture does: `mimeData()`
      returned an empty object (`EMPTY_MIME=0`), so the backup loop runs zero times.
    - **Why not:** Qt documents `QClipboard.mimeData()` as null only when the platform lacks
      that clipboard mode, and the global clipboard exists on macOS and Windows.
    - **Fix (defensive):** one line, the backup loop skips a `None` (`original.formats() if
      original is not None else []`).

- [x] **HLP-9 · `describe_graph(include_params=True)` shows a driven parameter's hidden constant** · `designer_helpers.py:124-131` · confirmed · found 2026-10-29
  - **Fix.** Print "driven by input X" (`_plain_binding` has the id).
  - **Resolution: done** (commit `663354a`).
    - **Test:** live check "describe_graph: driven parameters show what drives them" on the
      self-test's levels node (`leveloutlow` exposed as `floor`, `levelinmid` driven by a larger
      function): neither line appeared; the hidden constants were listed, or nothing when the
      constant equalled the default.
    - **Cause:** `include_params` printed `getPropertyValue`, the constant stored beside a function
      graph, which Designer ignores while the function drives the value.
    - **Fix:** a parameter with a function graph prints `param <- graph input 'x'` (via
      `_plain_binding`) or `param <- a function` instead of a value; the docstring says so.

- [x] **HLP-10 · Library packages are not excluded on two paths** · `designer_helpers.py:411-419, 30-44` · confirmed; unlikely · found 2026-10-29
  - **Defect.** `save_package` by path could overwrite a library `.sbs` in Designer's install folder;
    with no identifier, a library graph open in the editor can be edited.
  - **Fix.** Skip library packages in `_package_of`; optionally refuse editing a library graph.
  - **Resolution: done** (commit `6911082`).
    - **Test:** a live check asks `_package_of` (the lookup behind `save_package`, nothing saved)
      for a loaded library package by its path, and with a library graph as the editor's graph:
      both returned the library package.
    - **Cause:** `_package_of` matched any user package, and Designer counts the library packages
      it loads as user packages.
    - **Fix:** `_package_of` refuses a library package either way ("one of Designer's library
      packages; not saving over it"), so `save_package` can't overwrite Designer's install folder.
      Editing a library graph in memory is still possible; only saving is refused.
  - Questioned by HLP-14 (2026-10-29).

- [x] **HLP-11 · An enum value given as a numeric string is rejected** · `designer_helpers.py:493-497` · confirmed · found 2026-10-29
  - **Defect.** `"3"` is refused, although int parameters accept strings.
  - **Fix.** Also accept `str(ev.get()) == str(value)`.
  - **Resolution: done** (commit `663354a`).
    - **Test:** live check "set_params: enum value as a numeric string" (`blendingmode: '3'`):
      "RuntimeError: blendingmode: '3' is not one of copy=0, ...".
    - **Cause:** the enum match compared the value with the enumerator's id and its number, so a
      string matched only an id.
    - **Fix:** a string that equals the enumerator's number (`'3'`, spaces ignored) matches too;
      the `set_params` docstring lists `'5'` beside `'max'` and `5`.

- [x] **INS-5 · `.mcp.json` trusts `CLAUDE_PROJECT_DIR`** · `.mcp.json` · plausible · found 2026-10-29
  - **Defect.** If it points at a subfolder the server fails to start (the git fallback runs only
    when it is empty); a missing venv gives only "failed to connect".
  - **Fix.** Fall back unless the venv exists there; print a hint when the venv is missing.
  - **Resolution: done** (commit `3c6c6a1`).
    - **Test:** two unit tests running the `.mcp.json` command failed: with `CLAUDE_PROJECT_DIR`
      set to the repo's `examples/` the server didn't start, and with no venv anywhere it said only
      "cannot execute: No such file or directory".
    - **Cause:** the command used `CLAUDE_PROJECT_DIR` whenever it was set, without checking for
      the venv there, and never checked that the venv exists before `exec`.
    - **Fix:** the command falls back to the git root (or the current folder) unless the venv is
      in `CLAUDE_PROJECT_DIR`, and without a venv prints "no Python environment in ...; run
      python3 install.py" to stderr, which `/mcp` shows. README's Troubleshooting has the symptom.
  - Questioned by INS-14 (2026-10-29).

- [x] **INS-6 · The uninstaller says "Removed" for an old plugin it left alone** · `uninstall.py:105-108` · confirmed · found 2026-10-29
  - **Fix.** Check ownership in `plan()`; have `remove_old_plugin` return a status.
  - **Resolution: done** (commit `6911082`).
    - **Test:** a unit test with someone else's `sd_bridge` folder: it was listed under "Will
      remove" and printed as removed.
    - **Cause:** the ownership check happened only inside the removal, after the plan was shown.
    - **Fix:** `install.is_old_plugin()` decides in `plan()`; a foreign folder is listed as "not
      touched".

- [x] **INS-7 · `--remove-snapshots` deletes the whole snapshot folder** · `uninstall.py:137-138` · confirmed; opt-in · found 2026-10-29
  - **Scenario.** `SD_SNAPSHOT_DIR` points at a shared folder, which is wiped.
  - **Fix.** Delete only the snapshots the server wrote, or refuse a folder with other content.
  - **Resolution: done** (commit `6911082`).
    - **Test:** a unit test with a snapshot and an unrelated `notes.txt` in the folder: both were
      deleted.
    - **Cause:** `shutil.rmtree` on the whole folder.
    - **Fix:** `remove_snapshots()` deletes only files named like the server's snapshots, then the
      folders left empty.

- [x] **INS-8 · Re-running the example discards edits** · `examples/build_dwarf_trimsheet.py:92-94` · confirmed · found 2026-10-29
  - **Defect.** It unloaded any package with a graph named `dwarf_trimsheet`, saved or not.
  - **Scenario.** A "Save As" copy being edited loses its edits.
  - **Fix.** Skip modified packages and packages at another path, with a warning.
  - **Resolution: done** (commit `5f27a79`).
    - **Test:** two live checks (an edited copy of the graph saved elsewhere; unsaved edits to the
      previous build) failed against the old script: both were unloaded and the edits lost.
    - **Cause:** the script unloaded every package with a graph named `GRAPH_ID`, whatever its
      path and whether it had unsaved changes.
    - **Fix:** it now unloads only the previous build at `OUT_SBS`, refuses while that has unsaved
      changes, and leaves other packages open with a note. AGENTS.md's Example section says so.

- [x] **INS-9 · `pillow` and `numpy` are unpinned** · `mcp_server/requirements.txt` · plausible · found 2026-10-29
  - **Scenario.** A later install picks up an incompatible major version (now 13.0.0 and 2.5.4).
  - **Fix.** Upper bounds or a constraints file.
  - **Resolution: done** (commit `e13ee76`).
    - **Test:** `test_every_requirement_has_a_tested_range` failed with "requirements without a
      tested range: ['pillow', 'numpy']".
    - **Cause:** only `mcp` had bounds.
    - **Fix:** `pillow>=10.0,<14` and `numpy>=1.26,<3`. The upper bounds stop the next major
      version; the lower bounds still install on Python 3.10 (README's minimum), since recent
      numpy needs 3.11. A comment names the tested versions (mcp 2.3.0, pillow 13.0.0, numpy 2.5.4,
      Python 3.12). README points to the file.

- [x] **INS-10 · The installer never removes files dropped from the plugin** · `install.py:152` · plausible · found 2026-10-29
  - **Defect.** `copytree(dirs_exist_ok=True)` keeps stale modules importable.
  - **Fix.** Remove the plugin folder (ours by name) before copying.
  - **Resolution: done** (commit `6911082`).
    - **Test:** a unit test with a stale `old_module.py` in the installed plugin: it survived a
      re-install.
    - **Cause:** `copytree(dirs_exist_ok=True)` only adds and replaces.
    - **Fix:** the installer removes the installed plugin folder first (ours by name), then copies.
  - Questioned by INS-12 (2026-10-29).

- [x] **TST-4 · The `read_designer_log(errors_only)` check can't fail** · `tests/test_all_tools.py:478-479` · confirmed · found 2026-10-29
  - **Defect.** It passed on an empty result (`all([])`; "0 matching lines" contains "matching line").
  - **Fix.** Create an error first, then expect at least one line.
  - **Resolution: done** (commit `2fd025b`).
    - **Test:** the check is the test here: it passed on an empty log, so it couldn't catch a
      broken filter.
    - **Cause:** `all()` over no lines is True, and the header "0 matching lines" contains
      "matching line".
    - **Fix:** the check first writes its own warning to Designer's log
      (`sd.getContext().getLogger().warning`) and must find it among the filtered lines.

- [x] **TST-5 · The self-test doesn't check that it reopened your graph** · `tests/test_all_tools.py:1071-1073` · plausible · found 2026-10-29
  - **Defect.** With duplicate graph names the reopen is refused as ambiguous, yet "reopened your
    graph" is printed; the view's zoom and position change either way.
  - **Fix.** Reopen by package path and identifier; check the result.
  - **Resolution: done** (commit `663354a`).
    - **Test:** a new live check "open_graph: the self-test puts your graph back in the editor",
      run with two unsaved graphs named `tst5_dup` open and the second in the editor: "2 open
      graphs are named 'tst5_dup' (packages: never saved, never saved)", while the old code
      printed "reopened your graph" regardless.
    - **Cause:** the run remembered the user's graph by identifier only and reopened it by name,
      without checking the result.
    - **Fix:** the start of the run keeps the graph object itself (in Designer's `sys`); the end
      reopens that object with `openResourceInEditor` (without the fit to the whole graph that `open_graph` does)
      and checks the editor's graph has the same package UID and identifier.

- [x] **TST-6 · `apply_edits` docstring and op test lag the code** · `server.py:620` · confirmed · found 2026-10-29
  - **Defect.** The `expose` op lacks `step` and `group`; the unit test reads the op list from the
    docstring, so an op added only in the helpers escapes it.
  - **Fix.** Document the fields; read op names from the dispatcher.
  - **Resolution: done** (commit `cc49eaf`).
    - **Test:** `test_apply_edits_docstring_lists_every_op_and_field` reads each op and the fields
      its branch reads from the helpers' dispatcher and compares them with the docstring. It failed
      with "apply_edits 'expose': fields ['default', 'group', 'input_id', 'label', 'max', 'min',
      'step'] not in the docstring", and on `bitmap`'s `position` and `name`, written without the
      `"field"?:` form the other lines use.
    - **Cause:** the op list was kept by hand in the docstring, and the op test read that list,
      so the code and the test could drift apart unnoticed.
    - **Fix:** the docstring lists every field (`step`, `group` added); `_dispatched_ops()` in
      `test_server.py` takes op names and fields from the dispatcher, for this test and for the
      "every op runs live" test. The live `expose` op now passes `step` and `group` too, and a new
      check reads them back from `list_graph_inputs`.

- [x] **TST-7 · README's Uninstall section omits the user-scope registration** · `README.md:265-268` · confirmed · found 2026-10-29
  - **Fix.** One clause: a user-scope registration of this server is removed too.
  - **Resolution: done** (commit `cc49eaf`).
    - **Test:** `test_user_scope_registration_of_this_server_is_removed` (`test_uninstall.py`)
      already covered the behaviour; only the README lagged.
    - **Fix:** README's Uninstall section adds "plus a user-scope registration (`--scope user`)
      if there is one".

- [x] **TST-8 · README overstates what the unit tests cover** · `README.md:206` · confirmed · found 2026-10-29
  - **Defect.** "The clients' protocol": `sd_run.py`'s handshake is only tested live.
  - **Fix.** A unit test of `sd_run.send` against the fake plugin, or reword.
  - **Resolution: done** (commit `cc49eaf`).
    - **Test:** `test_both_clients_speak_the_plugins_protocol` runs code and a status request with
      `sd_run.send` and with the server's `_send` against the plugin's real server (Qt replaced).
      It passed at once: the client works, and the finding was the missing coverage, which this
      test adds. Until now `_send` had only been tested against a fake listener, and `sd_run.send`
      only live.
    - **Fix:** the test above; README now says "both clients' protocol (the MCP server's and
      `client/sd_run.py`'s, against that plugin server)".

- [x] **TST-9 · The size-inheritance check can leave packages open** · `tests/test_all_tools.py:632-641` · plausible · found 2026-10-29
  - **Defect.** Its `inherit_*` packages stay open if a call fails midway; the cleanup only matches
    `mcp_selftest*`.
  - **Fix.** Add them to the cleanup, or try/finally.
  - **Resolution: done** (commit `6911082`).
    - **Test:** a unit test checks that every graph the self-test creates is named `mcp_selftest...`
      and that the cleanup matches that prefix; it failed on `inherit_*`.
    - **Cause:** the cleanup listed four exact names; the inheritance check used others.
    - **Fix:** those graphs are `mcp_selftest_inherit_*`, and the cleanup closes every package
      with a graph whose name starts with `mcp_selftest`.

- [x] **TST-10 · Facts repeated in several places** · AGENTS.md, README.md, server.py · confirmed · found 2026-10-29
  - **Defect.** The 4,096-character limit (AGENTS.md twice, README.md, server.py); "29 atomic
    nodes" (AGENTS.md twice).
  - **Fix.** Keep each in one place and link to it.
  - **Resolution: done** (commit `cc49eaf`).
    - **Test:** `test_facts_are_stated_once_in_the_docs` counts `4,096` and the number 29 in
      AGENTS.md and README.md. Against the old docs: "'4,096' appears 3 times", "'\\b29\\b'
      appears 2 times".
    - **Cause:** each fact was restated where it was mentioned rather than linked.
    - **Fix:** the limit stays in AGENTS.md's Working on this project (the rule for agents), and
      the intro and README point there. The atomic node count stays in the sd API gotchas;
      "Which tool for what" says "the atomic nodes". `server.py` keeps its comment beside the
      constant, where the measurement is recorded.
  - Questioned by TST-18 (2026-10-29).

- [x] **INS-11 · The installer doesn't say which Python the venv uses** · `install.py:166-174` · confirmed · found 2026-10-29
  - **Defect.** The venv is made with whatever Python runs `install.py`; nothing reports which.
  - **Scenario.** Two machines run different Pythons; a problem on one can't be matched to it, and
    "3.10+" (README) has only ever been tested on 3.12.
  - **Fix.** Print the venv's Python version in step 2.
  - **Resolution: done** (commit `3c6c6a1`).
    - **Test:** a unit test expected the version on the installer's step-2 line; it wasn't there.
    - **Cause:** nothing asked the venv's Python for its version.
    - **Fix:** `install.py` runs `<venv python> --version` and prints it in step 2.

- [x] **SRV-13 · No tool reports the server's Python and library versions** · `server.py` (`designer_status`) · confirmed · found 2026-10-29
  - **Defect.** `designer_status` reports Designer's version and the bridge, not the MCP server's
    own Python, `mcp`, `pillow` and `numpy` versions (unpinned, INS-9).
  - **Fix.** Add one line with those versions to `designer_status`.
  - **Resolution: done** (commit `3c6c6a1`).
    - **Test:** a unit test expected "MCP server: Python <version>, mcp ..., pillow ..., numpy ..."
      in `designer_status`; it wasn't there.
    - **Cause:** `designer_status` only reported Designer's side.
    - **Fix:** `_server_versions()` in `server.py` (`platform`, `importlib.metadata`) adds that line.

- [x] **TST-11 · AGENTS.md doesn't say a fresh clone needs `install.py`** · `AGENTS.md` (Working on this project) · confirmed · found 2026-10-29
  - **Defect.** It mentions `install.py` only for re-installing after plugin changes.
  - **Scenario.** In a fresh clone (or after deleting the venv) the server fails with "failed to
    connect", and an agent has nothing pointing it at the installer.
  - **Fix.** One line: a fresh clone or a deleted venv needs `python3 install.py` first.
  - **Resolution: done** (commit `3c6c6a1`).
    - **Test:** none (documentation); INS-5's test covers the message an agent now sees.
    - **Cause:** the installer was documented for people (README) but not for agents.
    - **Fix:** AGENTS.md, Working on this project: a fresh clone or a deleted venv needs
      `python3 install.py` first, then a `/mcp` reconnect; `designer_status` shows the versions.

- [x] **TST-12 · README's "Python 3.10+" was never tested** · `README.md:104` · confirmed · found 2026-10-29
  - **Defect.** 3.10 is the minimum `install.py` accepts; the tests have only run on 3.12.
  - **Fix.** Say "3.10+ required; tested with 3.12", so the tested version is visible.
  - **Resolution: done** (commit `3c6c6a1`).
    - **Test:** none (documentation).
    - **Cause:** the requirement gave the installer's minimum without saying what was tested.
    - **Fix:** README's Requirements: 3.10 is the minimum the installer accepts, the tests run on
      3.12, and the installer and `designer_status` show the Python in use.

- [x] **PLG-11 · `status` can answer "bad request" when a job ends at the wrong moment** · `plugin/.../__init__.py:210` · plausible · found 2026-10-29
  - **Defect.** `busy_since` is read twice outside the lock while `_drain` sets it to None; a job
    ending between the two reads gives `float - None`, caught as `bad request`.
  - **Fix.** Read it once, under the lock with the queue count.
  - **Resolution: done** (commit `d1b7f29`).
    - **Test:** `test_status_while_a_job_ends_is_not_a_bad_request` clears `busy_since` from inside
      the clock call, as the main thread would: `TypeError: unsupported operand type(s) for -:
      'float' and 'NoneType'`.
    - **Cause:** `busy_since` was read once for the check and again for the subtraction.
    - **Fix:** `status` reads it once into a local.

- [x] **PLG-12 · A job queued just after `stop()` still waits out `QUEUE_WAIT`** · `plugin/.../__init__.py:251-252, 298-306` · confirmed code, plausible scenario · found 2026-10-29
  - **Defect.** `stop()` empties the queue once; a handler already reading its request puts its job
    in afterwards, and `_authorised` never checks `running`. Questions PLG-5's scope.
  - **Fix.** Under the lock, refuse with "closing" when not running before `jobs.put`; set
    `running = False` under the same lock.
  - **Resolution: done** (commit `d1b7f29`).
    - **Test:** `test_a_job_arriving_after_stop_is_answered_at_once` sends an authenticated job
      after `stop()`: it waited out `QUEUE_WAIT` and got "Designer was busy for 1s".
    - **Cause:** `_authorised` queued jobs without checking `running`, so a job could land in the
      queue after `stop()` had emptied it.
    - **Fix:** the check of `running` and the `put` happen under the lock, and `stop()` clears
      `running` under the same lock: a late job gets "Designer is closing" at once.

- [x] **PLG-13 · Queued jobs run back to back without returning to Qt's event loop** · `plugin/.../__init__.py:268-283` · plausible · found 2026-10-29
  - **Defect.** One timer tick runs every queued job. AGENTS.md (Portals) and PLG-9 rely on the event
    loop running between two bridge calls (unload, then load); queued together, they wouldn't.
  - **Fix.** Run one job per tick (return after `done.set()`).
  - **Resolution: done** (commit `d1b7f29`).
    - **Test:** `test_one_job_per_timer_tick` queues two jobs and calls `_drain` once: both ran.
    - **Cause:** `_drain` looped until the queue was empty.
    - **Fix:** `_drain` returns after one job, so Designer's event loop runs before the next
      (abandoned jobs are still skipped in the same tick). PLG-1's test now drains twice.

- [x] **SRV-16 · Two docstrings still give the old client wait** · `mcp_server/server.py:236, 246` · confirmed · found 2026-10-29
  - **Defect.** `execute_designer_code` and `run_designer_script` say the call "stops waiting after
    about 16 minutes"; since PLG-3 it waits `QUEUE_WAIT + (timeout or 900) + 60` (26 to 31 min).
  - **Fix.** State the formula.
  - **Resolution: done** (commit `d1b7f29`).
    - **Test:** none (documentation).
    - **Fix:** both docstrings say the call stops waiting about 16 minutes after a `timeout_s=0`
      script starts, and that a queued script can wait up to 15 minutes before it starts.
  - Questioned by SRV-18 (2026-10-30).

- [x] **HLP-14 · HLP-10's refusal suggests `save_as`, which is refused too** · `mcp_server/designer_helpers.py:441-443, 448-453` · confirmed · found 2026-10-29
  - **Defect.** `_package_of` refuses a library package before `save_package` looks at `save_as`, so
    "save a copy with save_as instead" fails the same way, though saving elsewhere is safe.
    Questions HLP-10's resolution.
  - **Fix.** Refuse only when saving over the library file; a live check for the `save_as` case.
  - **Resolution: done, by rewording** (commit `d1b7f29`).
    - **Test:** the HLP-10 live check now also requires that the refusal doesn't suggest `save_as`
      and names `snapshot_graph`; without the fix it failed ("save a copy with save_as instead").
    - **Cause:** the message offered a way out that `_package_of` refuses too.
    - **Fix:** the refusal stays, since `savePackageAs` would re-point the loaded library package
      itself (AGENTS.md: it changes the package's path); the message says so and points to
      `snapshot_graph` for a copy.
  - Questioned by HLP-18 (2026-10-30).

- [x] **INS-12 · The installer deletes the plugin folder without an ownership check, before copying** · `install.py:169-171` · confirmed order, plausible failure · verified by hand · found 2026-10-29
  - **Defect.** `shutil.rmtree(dst)` runs for any folder with the plugin's name, while
    `uninstall.py` leaves a non-matching one alone (`is_our_plugin`); and a failing `copytree`
    after the delete leaves no plugin at all. Questions INS-10's resolution.
  - **Fix.** Check ownership first; copy to `dst + '.new'`, then swap.
  - **Resolution: done** (commit `d1b7f29`).
    - **Test:** `test_leaves_someone_elses_plugin_folder_alone` (a folder with the plugin's name and
      another `pluginInfo.json`: deleted) and `test_a_failed_copy_keeps_the_installed_plugin` (a
      copy failing midway: the previous install was gone).
    - **Cause:** the installer decided by name only, and deleted before copying.
    - **Fix:** `install_plugin()` in `install.py` refuses a folder that isn't ours (the uninstaller
      now uses the same `install.is_our_plugin`), copies to `<name>.new`, then swaps it in; a
      failing copy leaves the installed plugin as it was. Two INS-10-era tests now start from a
      real install.
  - Questioned by INS-16 (2026-10-30).

- [x] **INS-13 · The example no longer closes an unsaved package left by a failed run** · `examples/build_dwarf_trimsheet.py:96-101` · plausible · found 2026-10-29
  - **Defect.** Since INS-8 only the build at `OUT_SBS` is unloaded; a run that fails before its
    first save leaves an unsaved `dwarf_trimsheet` package that every later run keeps, and the tools
    refuse the graph name as ambiguous.
  - **Fix.** Unload the script's own package when the build fails before it is saved.
  - **Resolution: done** (commit `d1b7f29`).
    - **Test:** a live check runs the example with a failure injected before its first save, then
      counts unsaved packages with its graph: without the fix one was left, and five later checks
      failed with "2 open graphs are named 'mcp_selftest_trimsheet'".
    - **Cause:** INS-8 narrowed the clean-up to the build at `OUT_SBS`, and nothing closed the
      package of a run that failed before saving.
    - **Fix:** `build()` wraps the build; on any failure (the bridge's abort too, re-raised) before
      the package was saved, it unloads its own package and says so.
  - Questioned by INS-17 (2026-10-30).

- [x] **INS-14 · `.mcp.json`'s missing-venv message is wrong on Windows** · `.mcp.json:8` · plausible · found 2026-10-29
  - **Defect.** With `sh` on PATH (Git's `usr\bin`), the check `[ -x mcp_server/venv/bin/python ]`
    fails on a Windows venv (`Scripts\python.exe`) and says "run python3 install.py", which can't
    help. Questions INS-5's resolution for Windows.
  - **Fix.** Accept `venv/Scripts/python.exe` too, or say that Windows registers per folder.
  - **Resolution: done** (commit `d1b7f29`).
    - **Test:** `test_a_windows_venv_is_used` runs the command in a folder with
      `mcp_server/venv/Scripts/python.exe`: "no Python environment".
    - **Cause:** the command knew only the POSIX venv layout.
    - **Fix:** it accepts `venv/bin/python` or `venv/Scripts/python.exe`, for `CLAUDE_PROJECT_DIR`
      too, and the message gives the Windows installer command as well.
  - Questioned by INS-18 (2026-10-30).

- [x] **INS-15 · The uninstaller reports the snapshot folder removed when it stays** · `uninstall.py:100-113, 162` · confirmed · found 2026-10-29
  - **Defect.** `remove_snapshots` returns None, so "Removed graph snapshots: <dir>" is printed even
    when other files (a shared folder, a `.DS_Store`) keep the folder. Follows INS-7.
  - **Fix.** Return a note when the folder is kept.
  - **Resolution: done** (commit `d1b7f29`).
    - **Test:** `test_a_kept_snapshot_folder_is_reported_as_kept` (a shared folder with another
      file): "Removed graph snapshots: <dir>".
    - **Cause:** `remove_snapshots` returned nothing either way.
    - **Fix:** it returns a `Kept` note when the folder stays, printed as "Removed graph snapshots:
      <dir> (the snapshots were deleted; folder kept, other files are in it)".

- [x] **TST-15 · The `CopiedAndLinked` check doesn't test the facts TST-3 added** · `tests/test_all_tools.py:775-779` · confirmed · found 2026-10-29
  - **Defect.** AGENTS.md says the copy goes to `<OS temp>/Adobe/Adobe Substance 3D Designer/`,
    stays after the package closes, and later copies get `1-`; the check only tests "under the temp
    folder" and deletes the copy only `if os.path.isfile(...)`. Questions TST-3's resolution.
  - **Fix.** Assert the folder and that the copy is still there after the unload, or trim the claim.
  - **Resolution: done; the facts hold** (commit `d1b7f29`).
    - **Test:** the check now copies the same file from two unsaved packages and requires the
      folder `<OS temp>/Adobe/Adobe Substance 3D Designer/`, both copies still there after their
      packages closed, and the second numbered (`1-XXXXXX-...`, an earlier leftover's number
      allowed). It passes: AGENTS.md was right; only the check was weaker than the claim.
    - **Fix:** both copies are deleted afterwards.

- [x] **TST-16 · No automated check guards against PLG-9** · `tests/test_all_tools.py` (`main()`, the `was_running` path) · confirmed · found 2026-10-29
  - **Defect.** Crash dumps are compared only on the self-started quit paths; against an open
    Designer (PLG-9's scenario) nothing looks for a dump after the scratch folder is deleted.
  - **Fix.** When Designer was already running, note the dumps before the clean-up, wait about 10 s
    after it, and fail on a new dump or an unreachable Designer.
  - **Resolution: done** (commit `d1b7f29`).
    - **Test:** a new "self-test" check: when the run used the user's open Designer, `main()` notes
      the crash dumps before deleting the scratch folder, then polls for new ones for 10 s and
      requires Designer still running. It passed in both runs against an open Designer; it can
      only show a failure when the crash recurs.
  - Questioned by TST-21 (2026-10-30).

- [x] **TST-17 · The modal-quit dump check waits exactly as long as a dump took to appear** · `tests/test_all_tools.py:1442` · plausible · found 2026-10-29
  - **Defect.** PLG-8 saw the dump about 3 s after shutdown; the check sleeps 3 s, so a slower dump
    is missed.
  - **Fix.** Poll for about 10 s.
  - **Resolution: done** (commit `d1b7f29`).
    - **Test:** none that can fail on demand (it needs a slow crash).
    - **Fix:** `new_crash_dumps()` polls for up to 10 s; both quit checks use it instead of a fixed
      3 s wait.

- [x] **TST-18 · ROADMAP still repeats the atomic node count** · `ROADMAP.md:28`, `tests/unit/test_guide.py:56-61` · confirmed · found 2026-10-29
  - **Defect.** TST-10's guard counts only AGENTS.md and README.md; ROADMAP.md says "the 29 atomic
    nodes".
  - **Fix.** "the atomic nodes" in ROADMAP; include ROADMAP.md in the guard.
  - **Resolution: done** (commit `d1b7f29`).
    - **Test:** the TST-10 guard now counts ROADMAP.md too and failed: "'\\b29\\b' appears 2 times".
    - **Fix:** ROADMAP item 10 says "the atomic nodes".

- [x] **PLG-14 · `cancel` counts abandoned jobs that `status` no longer counts** · `plugin/.../__init__.py` (`_control`) · confirmed · verified by hand · found 2026-10-30
  - **Defect.** Since PLG-7 `status` skips abandoned jobs, but `cancel` still reports every job it
    drains as "queued dropped".
  - **Scenario.** `status` says "0 queued", then `cancel` says "queued dropped: 1".
  - **Fix.** Count only jobs not marked abandoned; extend PLG-7's test with a cancel.
  - **Resolution: done** (commit `4da1095`).
    - **Test:** `test_cancel_does_not_count_abandoned_jobs`: "queued dropped: 1" for an abandoned job.
    - **Fix:** `cancel` counts only jobs not marked abandoned. Plugin reinstalled.

- [x] **SRV-18 · The SRV-16 docstrings still give the wrong wait** · `mcp_server/server.py` (`execute_designer_code`, `run_designer_script`) · confirmed · verified by hand · found 2026-10-30
  - **Defect.** They say the call stops waiting "about 16 minutes of running" after a `timeout_s=0`
    script starts; `_bridge` waits `QUEUE_WAIT + 900 + 60` from sending, so a script that starts
    at once is waited on for about 31 minutes. Questions SRV-16's resolution.
  - **Fix.** "about 31 minutes after the call is sent (up to 15 of them in the queue)", or the formula.
  - **Resolution: done** (commit `4da1095`).
    - **Test:** none (documentation).
    - **Fix:** both docstrings give the client's wait as it is counted, from sending: 15 minutes
      (the queue) + `timeout_s` (15 minutes if 0) + 1 minute, about 31 minutes for 0.

- [x] **SRV-19 · After a restart, `launch_designer` gives the new Designer only what's left of `wait_s`** · `mcp_server/server.py` (`launch_designer`) · confirmed · found 2026-10-30
  - **Defect.** `started` isn't reset when the old process is gone and a new one is started, so the
    new one may get seconds, and "Designer started in Ns" counts the wait for the old one. Follows
    SRV-15.
  - **Fix.** Reset `started` in the restart branch.
  - **Resolution: done** (commit `4da1095`).
    - **Test:** `test_a_restarted_designer_gets_the_whole_wait`: "Designer started in 150s", counting
      the wait for the old process.
    - **Fix:** `launch_designer` resets its clock when it starts a new Designer.
  - Questioned by SRV-20, SRV-21 (2026-10-30).

- [x] **HLP-17 · The HLP-12 guard can still cut off shutdown work done before `aboutToQuit`** · `mcp_server/designer_helpers.py` (`quit_designer`) · plausible · found 2026-10-30
  - **Defect.** Work in a close handler that processes events while the window is still visible
    (before `aboutToQuit`) passes both conditions, so the 5 s fallback still fires inside it; the
    "Destroy Application" check HLP-12 suggested was never added. Questions HLP-12's resolution.
  - **Fix.** A live check that a plain quit logs "Destroy Application"; optionally set the flag from
    a close-event filter, so the fallback fires only when the Close was really ignored.
  - **Resolution: done** (commit `4da1095`).
    - **Test:** a live check delays the window's Close by 7 s of event processing: before the fix
      the fallback killed Designer inside the close handler.
    - **Cause:** the fallback only knew "a window is visible", which is true while a close handler
      is still working.
    - **Fix:** `close_windows` marks the close as in progress; the fallback waits while it is, up to
      about 35 s, then decides. The "Destroy Application" log check wasn't added: the slow-close
      check reproduces the case directly.

- [x] **HLP-18 · The library refusal points to `snapshot_graph`, which can't reach a library graph by name** · `mcp_server/designer_helpers.py` (`_package_of`) · confirmed · verified by hand · found 2026-10-30
  - **Defect.** `snapshot_graph` goes through `find_graph`, which skips library packages, so it works
    only with the library graph open in the editor; the check only looks for the word. Questions
    HLP-14's resolution.
  - **Fix.** Say "open it in the editor, then snapshot_graph", or let the copy accept a library package.
  - **Resolution: done** (commit `4da1095`).
    - **Test:** the library-refusal check also requires "open it in the editor": it failed.
    - **Fix:** the message says to open the graph in the editor, then `snapshot_graph`.
  - Questioned by HLP-20 (2026-10-30).

- [x] **INS-17 · The example creates its package outside the clean-up's `try`** · `examples/build_dwarf_trimsheet.py` (`Builder.__init__`) · plausible · found 2026-10-30
  - **Defect.** `newUserPackage()`, the graph and its size are set up in `Builder.__init__`, before
    `build()`'s `try`, so a failure there leaves the unsaved package INS-13 meant to close.
    Questions INS-13's scope.
  - **Fix.** Create the package inside the `try`, or guard the end of `__init__`.
  - **Resolution: done** (commit `4da1095`).
    - **Test:** the failing-example live check runs a second injection, inside `Builder.__init__`
      right after the package is created: `UNSAVED_LEFT=1`, and five later checks failed on the
      duplicate name.
    - **Fix:** `Builder.__init__` unloads its new package if setting up the graph fails.

- [x] **INS-18 · The Windows-venv test runs on Windows, where it can't work** · `tests/unit/test_mcp_json.py` (`test_a_windows_venv_is_used`) · plausible · found 2026-10-30
  - **Defect.** It runs a shebang script named `python.exe` through `sh`; its sh-based neighbours are
    skipped on win32, this one isn't.
  - **Fix.** The same `skipif(sys.platform == 'win32')`.
  - **Resolution: done** (commit `4da1095`).
    - **Test:** none here (it would need Windows).
    - **Fix:** the test is skipped on win32, like its sh-based neighbours.

- [x] **TST-20 · The HLP-13 check names `expose_param` but tests only `set_params` and `describe_graph`** · `tests/test_all_tools.py` (HLP-13 check) · confirmed · found 2026-10-30
  - **Defect.** `expose_param` and `sweep_param` also moved to `_driving_graph`, unchecked.
  - **Fix.** Sweep and expose the same parameter in the check (then remove the input), or reword.
  - **Resolution: done** (commit `4da1095`).
    - **Test:** the HLP-13 check now also sweeps and exposes the parameter with an empty function
      graph on it; both run (it passes, as `_driving_graph` is shared).

- [x] **TST-21 · Crash-dump checks always wait 10 s, and TST-16 blames any crash on the clean-up** · `tests/test_all_tools.py` (`new_crash_dumps`, `main()`) · confirmed · found 2026-10-30
  - **Defect.** A passing check waits the full 10 s (about +17 s per run from a closed Designer);
    `main()` takes `dumps_before` before the whole run, so a crash anywhere is reported as "survives
    the clean-up".
  - **Fix.** Note the dumps just before the clean-up; consider a shorter wait once no dump came.
  - **Resolution: done** (commit `4da1095`).
    - **Test:** none that can fail on demand.
    - **Fix:** `main()` notes the crash dumps just before the clean-up, so the check is about the
      clean-up only. The 10 s wait stays: dumps appeared about 3 s after a crash, and a shorter wait
      would miss slow ones.

- [x] **SRV-20 · `launch_designer` can now take up to twice `wait_s`, undocumented** · `mcp_server/server.py` (`launch_designer`) · confirmed · verified by hand · found 2026-10-30
  - **Defect.** Since SRV-19 a restarted Designer gets its own `wait_s`, so the call can last about
    twice as long, and a timeout still says "did not answer within <wait_s>s".
  - **Fix.** Say so in the docstring (and in the timeout message).
  - **Resolution: done** (commit `cd809ab`).
    - **Test:** none (documentation and a message).
    - **Fix:** the docstring says a restarted Designer gets its own `wait_s`, so the call can take
      up to about twice `wait_s`; the timeout says "within <wait_s>s of being started" then.

- [x] **SRV-21 · SRV-19's test doesn't test "late in the wait"** · `tests/unit/test_lifecycle_env.py` (`test_a_restarted_designer_gets_the_whole_wait`) · confirmed · found 2026-10-30
  - **Defect.** Its comment says the old process goes away after ~170 s; the fake clock puts it at
    about 90 s, so the case the finding described (the budget running out first) isn't covered.
  - **Fix.** About 33 `True`s, and expect the old code's `ToolError` there; or correct the comment.
  - **Resolution: done** (commit `cd809ab`).
    - **Test:** the old process now leaves at about 175 s of 180; against `server.py` from before
      SRV-19 the test fails with "Designer did not answer within 180s", the case the finding meant.

- [x] **HLP-19 · Once every window has closed, a window appearing later is never forced** · `mcp_server/designer_helpers.py` (`quit_designer`, `close_windows`) · plausible · found 2026-10-30
  - **Defect.** `close_windows` marks the shutdown as begun when no window is visible, and the
    fallback then returns for good; a prompt Designer showed after that, before `aboutToQuit`,
    would no longer be ended at 5 s (the server still reports it after `wait_s`). An intended trade
    for TST-19, not stated in the comment.
  - **Fix.** State the trade-off; or, when only `close_windows` set the flag, look once more at
    the give-up time and force then.
  - **Resolution: not reproduced; the fallback looks again until the give-up time anyway** (commit `cd809ab`).
    - **Test:** a live check shows a window from the main window's Close handler (it reads back as
      visible) and quits: Designer was gone after 2 s, so a window shown after everything closed
      doesn't keep it alive. Now a "designer facts" check; AGENTS.md says so.
    - **Why not:** Designer quits once its main window has closed, whatever else is showing.
    - **Fix (defensive):** while every window had closed, the fallback keeps looking every second
      and forces a window still visible about 35 s after the quit, instead of returning for good.
  - Questioned by TST-25 (2026-10-30).

- [x] **HLP-20 · The library refusal should say `snapshot_graph` with no `graph` argument** · `mcp_server/designer_helpers.py` (`_package_of`) · plausible · verified by hand · found 2026-10-30
  - **Defect.** Only `snapshot_graph()` with no identifier reaches the editor's library graph;
    `snapshot_graph(graph='bevel')` goes through `find_graph`, which skips library packages. No
    check snapshots a library graph open in the editor. Questions HLP-18's resolution.
  - **Fix.** "open it in the editor, then snapshot_graph with no graph"; a live check that does it.
  - **Resolution: done** (commit `cd809ab`).
    - **Test:** the refusal check now requires "snapshot_graph with no graph" (it failed), and a new
      live check snapshots a library graph opened in the editor with no `graph` argument: it works
      (the snapshot is deleted again).
    - **Fix:** the message says "open it in the editor, then call snapshot_graph with no graph".
  - Questioned by TST-26, TST-27 (2026-10-30).

- [x] **INS-19 · A failing rollback rename skips removing the new copy** · `install.py` (`install_plugin`) · plausible · verified by hand · found 2026-10-30
  - **Defect.** If `os.rename(old, dst)` itself raises in the `except`, `rmtree(new)` never runs:
    no plugin, full copies at `.new` and `.old`, and nothing saying where the old plugin is.
    Questions INS-16's resolution.
  - **Fix.** The rollback rename in its own `try`, `rmtree(new)` in a `finally`, and a note naming
    `<name>.old` when it couldn't be moved back.
  - **Resolution: done** (commit `cd809ab`).
    - **Test:** `test_a_failed_rollback_still_removes_the_new_copy_and_says_where_the_old_one_is`
      (the rollback rename fails too): `<name>.new` was left and nothing named `.old`.
    - **Fix:** the rollback rename has its own `try`; the new copy is removed in a `finally`; a
      failed rollback prints where the previous plugin is.

- [x] **INS-20 · A partly deleted `.old` stops later installs with a misleading message** · `install.py` (`install_plugin`), `uninstall.py` (`plan`) · plausible · found 2026-10-30
  - **Defect.** If `rmtree(old)` removes `pluginInfo.json` but not everything, later installs exit
    with "not this project's", and the uninstaller skips the folder without a word.
  - **Fix.** The uninstaller reports a leftover that isn't ours; the refusal mentions it may be a
    partly deleted copy.
  - **Resolution: done** (commit `cd809ab`).
    - **Test:** `test_reports_a_leftover_copy_that_isnt_ours` (uninstaller, a partly deleted
      `.old`): nothing was printed; and `test_refuses_a_leftover_copy_that_isnt_ours` expects the
      installer to mention a partly deleted copy: it didn't.
    - **Fix:** the uninstaller lists such a folder as "not this project's plugin (or a partly
      deleted copy); left as it is"; the installer's refusal says "or is a partly deleted copy".

- [x] **INS-21 · Two of INS-16's behaviours have no test** · `tests/unit/test_install.py` · confirmed · verified by hand · found 2026-10-30
  - **Defect.** The refusal of a foreign `<name>.new`/`.old` and the "could not remove" note are in
    the code but no test reaches them. Questions INS-16's resolution.
  - **Fix.** A test with a foreign `<name>.new` (exit, folder kept) and one with `rmtree` patched to
    do nothing (the note).
  - **Resolution: done** (commit `cd809ab`).
    - **Test:** `test_refuses_a_leftover_copy_that_isnt_ours` (a foreign `<name>.new`: exit, folder
      kept) and `test_reports_an_old_copy_it_could_not_remove` (`rmtree` patched to do nothing: the
      note). The second passed at once: the code worked; it had no test.

- [x] **TST-22 · The HLP-16 check compares rendered maxima exactly** · `tests/test_all_tools.py` (HLP-16 check) · plausible · found 2026-10-30
  - **Defect.** `max_empty == max_default` and `max_set == max_half` on 4-decimal values from a
    16-bit chain; parallel renders differ by a few 1/65535 (AGENTS.md), so one pixel could flip it.
  - **Fix.** Compare within about 0.002.
  - **Resolution: done** (commit `cd809ab`).
    - **Test:** none that fails on demand (render noise).
    - **Fix:** the two comparisons allow 0.002, which still separates 0.976 from 0.492.

- [x] **TST-23 · The `aboutToQuit` half of the quit guard is still never exercised** · `tests/test_all_tools.py` (slow-shutdown checks), `AGENTS.md` (Designer UI) · confirmed · verified by hand · found 2026-10-30
  - **Defect.** `close_windows` sets the flag as soon as the 7 s close handler returns, before
    `aboutToQuit`, so deleting the `aboutToQuit` connection would still pass; AGENTS.md documents
    that condition. Questions TST-19's resolution.
  - **Fix.** Drop the `aboutToQuit` connection as redundant (and its words in AGENTS.md), or add a
    case `close_windows` can't see.
  - **Resolution: done, by removal** (commit `cd809ab`).
    - **Fix:** the `aboutToQuit` connection is gone from `quit_designer`: its slots run in
      connection order, so it couldn't be relied on, and "every window has closed" covers it. The
      slow-shutdown check (a window shown from an earlier-connected `aboutToQuit` slot) now tests
      exactly that signal; AGENTS.md no longer mentions `aboutToQuit` as a condition.

- [x] **TST-24 · AGENTS.md says setting a value deletes "the function graph"; only an empty one was tested** · `AGENTS.md` (sd API gotchas) · confirmed · found 2026-10-30
  - **Defect.** The check sees an empty graph go after `set_params`; nothing sets a value raw on a
    parameter with a non-empty graph. Questions HLP-16's resolution (its documentation).
  - **Fix.** Narrow it to "an empty function graph", or measure `setPropertyValue` on an exposed
    parameter.
  - **Resolution: done** (commit `cd809ab`).
    - **Fix:** AGENTS.md says setting a value deletes an *empty* function graph (measured with
      `set_params`; not checked for a graph with nodes).

- [x] **TST-27 · The HLP-20 check leaves a library graph's tab open** · `tests/test_all_tools.py` (HLP-20 check) · plausible · found 2026-10-30
  - **Defect.** It opens a library graph in the editor and only switches back to the test graph, so
    against the user's open Designer the tab stays after the run (nothing is changed in it).
  - **Fix.** Close that view afterwards, in a separate call after the event loop has run.
  - **Resolution: done, by skipping against an open Designer** (commit `07c12c0`).
    - **Fix:** Designer's UI API has no call to close an editor tab, so the check runs only in a
      Designer the self-test started (closed at the end) and is skipped, with the reason, in yours.
