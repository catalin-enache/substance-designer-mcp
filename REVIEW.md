# REVIEW.md: review findings

Findings from code reviews of this repository, kept across several reviews as a file in the project. How many is
the user's choice, most likely the life of a feature branch; the history stays in git for good.

This file is the **memory per branch**. Agents that review and agents that address findings talk through it, as
in a PR review: a finding is raised, then fixed or answered with why not, so the next reviewers know what was
settled and don't raise it again. Once the branch is merged it can be cleaned up. `DECISIONS.md` is the memory for
the whole project.

A new review **appends** its findings to the matching severity section and adds itself to the log; it never removes
or rewrites existing entries. An entry is checked when it is resolved, always with a resolution line that starts
with one of these wordings: done, not a bug, not reproducible, won't fix. Format and rules:
`.claude/skills/project-code-review/` (SKILL.md, TEMPLATE.md).

**Confidence.**

- *Confirmed*: the lead agent read the code and the defect is visible in it, as quoted.
- *Measured*: reading couldn't settle it, and the lead agent's scratch probe in Designer showed it (the entry gives
  the probe and what it measured; the `project-code-review` skill). A finding is one or the other, never a guess.

**IDs.** One prefix per area, numbered on: **PLG** plugin and bridge protocol, **SRV**
`mcp_server/server.py` and `server_tools/`, **HLP** `mcp_server/designer_helpers/`, **INS** installer, uninstaller,
command-line client and example, **TST** tests and docs. A new area gets a new prefix, added here.

**Last used:** PLG-42, SRV-105, HLP-101, INS-27, TST-281.

A new finding takes the next number for its area, and whoever writes it updates this line in the same edit. Only a
new finding raises it, and a cleanup leaves it as it is. Nothing lowers a committed number; dropping a finding before
committing it undoes its change.

**Findings no longer here.** Only the user starts a cleanup of this file (the `cleanup-review` skill). An ID
cited elsewhere but missing here was usually removed by one, which isn't a dangling reference.
`python3 scripts/review_lookup.py HLP-56` prints the whole entry, from this file or its git history, from any folder
of the repo. If it can't, it says why: the ID never existed, a squash lost it, or the clone is shallow.

## Status

| Severity | Open | Resolved |
|---|---|---|
| High | 0 | 0 |
| Medium-high | 0 | 0 |
| Medium | 0 | 5 |
| Low-medium | 0 | 12 |
| Low | 0 | 52 |
| **Total** | **0** | **69** |

## Review log

### 2026-11-10: the branch `faster-test-runs` against `main` (the diff only)

- **How:** five reviewers (subagents, reading only), one per area: A the pool, the launch lock and the entry point;
  B how a category runs, the list of categories and the preparations; C the plugin, `lifecycle` and the crash dumps;
  D the tools' code and the checks that moved; E the docs. **Stopped early, at the user's request:** each reported
  what it had and what it hadn't read (**Not read**, below). No tests run. The lead agent checked every report against
  the code and against the 40 logs kept of the runs made on this branch, and probed what reading couldn't settle in
  one Designer an agent started (port 47311, closed afterwards, its folder removed):
  - `compute_floor.py`'s graph: relative to its parent, 1024 × 1024, 0.92 0.91 0.91 s; graphs made absolute at 4 × 4,
    32 × 32 and 1024 × 1024: 0.91 to 0.94 s each (TST-242).
  - facts' 3D capture on facts' own preparation: `NO_3D_VIEW` and "3D View menu bar not found"; after one
    `open_graph`, both calls work (TST-229).
  - The order of jobs in the plugin, a first job posting a Qt event and sleeping, a second saying whether the event
    had been delivered when it started: delivered in 160 trials of 160 (the first job started by the wake or by the
    timer, 30 ms and 250 ms long, the second queued behind it or sent after its answer; the second started as little
    as 0.4 ms after the first ended).
  - The clipboard after a Designer quits right after a 3D capture (`quit_designer`, as a worker ends its own): the
    same types, sizes and text hash before and after the quit.

  Settled as wrong, and not recorded:
  - *The plugin can start a job before the events the job before it posted are delivered, so "two never run back to
    back without Qt's event loop between them" doesn't hold* (C): not reproduced, the third probe.
  - *The clipboard is lost when the Designer that captured the 3D view quits seconds later* (D): not reproduced, the
    fourth probe.
  - *The 0.9 s of `graph.compute()` may hold only for a Designer in the background* (D): the first probe ran with
    Designer the active app.
  - *A start mark can end before Designer has written `session.instancePID`, so the hand-over check skips in some
    runs* (A): the check ran and passed in every full run kept; none skipped it.
  - *GUIDE.md still cites "the self-test's busier" graph* (E): the same sentence and the same check as on main, a
    past observation.
  - *`layout`'s "upstream left of downstream" holds before `arrange_graph` runs* (B): the same state as on main.
- **Not verified:** `test_the_port_is_bound_again_while_another_connection_uses_it_as_its_own`
  (`tests/unit/test_plugin.py:992`, new) binds the plugin's port while an outgoing connection holds it; on Windows the
  plugin binds with `SO_EXCLUSIVEADDRUSE`, which Microsoft documents as refusing that, and the file has no Windows
  skip, so the test probably fails there (C). No Windows machine here (ROADMAP item 18); running that test and
  `test_stop_answers_queued_clients_and_frees_the_port` on Windows would settle it.
- **Resolutions assessed:** none: REVIEW.md held no findings. Decisions whose code is in the diff: the two paths
  DECISIONS.md updated exist, and the checks its entries name still exist and still test what they say (the subfolder
  check only where the run started Designer, `mcp_empty`, the empty clipboard, "a definition's graph stays in its
  package"). "The full suites run only when the user asks" gives as its reason about 12 minutes and state earlier
  categories left; the branch measures 3.4 minutes and no category sees another's state. Whether its "Reopen if"
  (fast enough to run after every change) holds is the user's to judge: not raised as a finding.
- **Findings:** 23, all generation 1: PLG-34 to PLG-36, TST-228 to TST-247; Low-medium 7, Low 16. Found by more
  than one reviewer and merged: TST-229 (B, D), TST-231's move check (B, D), TST-232 (A, C, E), TST-236 (A, C),
  TST-241 (B, D), TST-247 (D, E).
- **Dropped because of a decision:**
  - "Low-value findings about the tests and docs are not raised": the pool's ports aren't reserved, so a port
    `lifecycle` picks later can be a pending worker's (A, C); `lifecycle`'s worker killed while its record is aside;
    the pool's parent killed, leaving workers, Designers and folders; `spawn` raising mid-schedule; a unit test
    reaching `one_run()` unfaked, whose `finally` can end the agent's Designer on the default port; `_cleaned`
    printing CLEAN's answer without checking it; a failed library listing giving exit code 1, not 2; a server dying
    mid-category ending `alone.run` in a traceback; the hand-over check's folder kept whenever a later dump appears.
  - "A Designer the user opened is theirs; one an agent started is disposable": the first worker going on after a
    failed start; a worker's end ending another run's Designer on a colliding port.
  - "Linux is not a target": `finish()`'s last branch is reachable only there (that it is dead on macOS and Windows is
    TST-237).
- **Suggested order:** TST-228 first (the user's Designer); TST-229 and TST-231 (checks that no longer measure);
  TST-230; the docs an agent acts on (TST-232 to TST-234); PLG-34 to PLG-36 together (one `install.py` and one
  restart of the Designer); then the rest.
- **Simplifications:** the same facts are now in several places, and one has drifted already (TST-232): the Windows
  run (AGENTS.md, README, the live-check skill, ROADMAP item 65), the pool's rules (the skill, PLAN.md step 6,
  `workers.py`'s docstring), "four at once by default" (five places). The skill could keep a line and point at
  `workers.py`'s docstring, as it does for `alone.py`.
- **Seen outside the diff, for the user to place:** `screenshot_designer('3d')` doesn't put the clipboard back
  exactly. In the fourth probe the clipboard held rich text (HTML 285, RTF 203, utf8 9, ut16 22 bytes) and came back
  as HTML 285, text 9, ut16 20: the RTF data gone, the text and the HTML kept (measured once; `_save_3d_render`,
  `designer_helpers/screenshots.py`, copies the formats Qt names). README (line 307) says it "puts back whatever was
  on your clipboard". The self-test's "3d + clipboard kept" passes all the same: when the fingerprints differ it
  measures again around a second capture, which finds the already reduced clipboard unchanged. Near the decision "The
  self-test's empty-clipboard check loses no clipboard data, as far as measured" ("Data Qt can't copy wasn't tried
  specifically"), though that entry is about another check. Also seen: in a Designer still on its Home screen that
  tool answers "3D View menu bar not found", not that the panel isn't visible.
- **Checked and found fine:**
  - *The user's Designer:* `choose` refuses whenever a Designer runs that no agent recorded, and when the listing
    fails; a worker ends only the process recorded on its own port; `_clean_up` ends nothing and deletes only the
    folders of ports the pool chose, where no recorded Designer runs and no dump is held; `own_pid` and `has_ended`
    look only at the process recorded for the run's port.
  - *Results:* a worker that crashed or wrote no results is one failed check; `merge` neither loses nor doubles;
    the parent judges tool coverage over all workers; the unit suite's exit code reaches the pool's.
  - *The scheduler and the lock:* slots, the exclusive group and solo hold; both sides of the lock write before they
    read, so neither misses the other; `held(own=...)` ignores its own mark; both of `lifecycle`'s windows release on
    return and on raise. The guards against a real run under pytest hold.
  - *`run_category`:* a preparation or a check that raises is a failed check, the next check still runs, the
    clean-up is in a `finally`. Every `ctx` name a category's checks read is set by its preparation.
  - *The plugin:* the emit from a client's thread only posts an event; no wake can be lost (`idle` and `put` under
    one lock, the timer behind it); `_drain` isn't re-entered; `PROTOCOL` rightly stays 2; each new test fails without
    its code.
  - *The fix for nodes at (0, 0):* right in `layout.py` and `snapshots.py` for every consumer (`_select_links`,
    `_diff_models`); no other reader of `<gpos>` in `mcp_server/`, `client/` or `examples/`; the two unit tests and
    the two live checks fail without it.
  - *The moves and the splits:* `graph_edit.py` against its three modules and `editor.py` against its two: bodies
    identical; `check(` and `skip(` calls equal per module but for the checks added; every `check_` function awaited
    once; no check of `lifecycle` lost.
  - *The docs:* the three commands in AGENTS.md, `--workers` and `--no-unit` and their defaults, `alone.run`'s
    parameters and exit codes in the skill, `CLIPBOARD` and `SOLO` as the skill gives them, the ROADMAP items PLAN.md
    cites, items 63 and 64 done in the code, no reference left to the removed items 53 to 56, 58, 61, 62.
- **Not read** (the reviewers were stopped): `params`, `bitmaps`, `discovery`, `script_runner` and
  `graph_edit_output_fields` checks against their state (only counted or diffed); `inputs/checks.py` past line 60 and
  `safeguards/checks.py` from about line 840; most Designer scripts; `tests/unit/test_selftest_summary.py`'s new tests
  one by one, `test_selftest_lifecycle.py` past line 275, `test_selftest_safety.py` and `test_designer_scripts.py`
  beyond their changed lines; `alone.py` against the pool's lock; whether unit tests outside these areas touch real
  shared state beside the pool; whether a category's clean-up runs on Ctrl-C; PLAN.md's measured figures and its
  unchanged text; README outside the self-test parts.
- **Decided by the user (2026-11-10), on what this review left to them:**
  - The clipboard the 3D capture doesn't put back exactly ("Seen outside the diff", above): fixed on this branch,
    as HLP-96.
  - The decision "The full suites run only when the user asks": the rule stays; only its reason is brought up to
    date, as TST-248.
  - PLG-34 to PLG-36: fixed on this branch, with one `install.py` run and one restart of a Designer an agent started
    for all three (the user's Designer loads the new plugin when they next open it).
  - TST-237: the unreachable code is removed, not kept for ROADMAP item 65.

### 2026-11-10: the uncommitted fix of HLP-96 (the diff against HEAD, new files included)

- **How:** one reviewer (a subagent, reading only) over the whole uncommitted diff: the fix, its checks, the docs, and
  AGENTS.md's paragraph on PyCharm's tools. No tests run. The lead agent settled each report by reading and with
  scratch probes, the user's clipboard saved before each and put back after:
  - writing an item with no types, on a pasteboard of its own in a process of its own: no error, the item is
    dropped and the others are written;
  - in a Designer an agent started (port 47311): data Designer put on the clipboard through Qt (an app's own type
    and text) before a 3D capture reads back through Designer's Qt intact after it, the same types natively;
  - what Qt lists for RTF alone (`text/html`, 505 bytes: converted, the RTF not listed), RTF and plain text
    (`text/html` and `text/plain`), and a real 2 × 2 PNG (`application/x-qt-image` with no data).

  Settled as wrong, and not recorded: *Designer's own node copy may not paste after the capture's native restore*
  (Qt reads back data it put there intact: the second probe); *an item whose types are all unreadable makes the
  write fail or throw* (the first probe).
- **Not verified:** none.
- **Resolutions assessed:** HLP-96: the fix holds for what it measured; questioned by HLP-97 (the read has no
  deadline), HLP-98 (a failed write-back), TST-249 (README says more than the code) and TST-253 (the second capture
  the entry's Fix kept was dropped).
- **Findings:** HLP-97 (Medium), HLP-98, HLP-99, TST-249 to TST-254 (Low); generation 2 where they follow HLP-96, 1
  otherwise.
- **Suggested order:** HLP-97 first (Designer's main thread, the user's clipboard), with HLP-98 and HLP-99 in the
  same file; then TST-250, whose new wording the guide needs, and the rest.
- **Checked and found fine:** the ctypes calls (each `objc_msgSend` cast to its method's signature, NSUInteger and
  BOOL, bytes with NUL bytes passed with their length, the pool drained in a `finally`, `string_at` copying before
  it drains); loading the part does nothing but define names, on Windows too; in `_save_3d_render` a missing dock
  or action, and a failing read, raise before the clipboard is touched; off macOS the behaviour is HEAD's; the checks
  fail on HEAD's code and restore the user's clipboard on every path; the unit tests use a pasteboard of their own;
  no other code backs up the clipboard through Qt; AGENTS.md's PyCharm paragraph matches what the tools did.
- **Decided by the user (2026-11-10), after this review:** the native backup is withdrawn; the 3D capture puts back
  the clipboard's text, through Qt as before, and says so (HLP-96's resolution, DECISIONS.md). HLP-97 to TST-254 are
  resolved with it.

### 2026-11-10: found while addressing the branch review's findings

- **How:** not a review: the lead agent, addressing TST-229 to TST-248, PLG-34 to PLG-36, in scratch runs and probes
  in Designers an agent started (ports 47311 and 47312, all closed afterwards).
- **Findings:** HLP-100 (Medium, generation 1), measured.
- **Also measured:** what TST-234 is about: the raise in `UNDO_REDO`, not the active app (its resolution).

### 2026-11-10: the branch `faster-test-runs` against `main` again (the diff only)

- **How:** five reviewers (subagents, reading only), one per area: A1 the pool, the launch lock, the entry point,
  `alone` and how a category runs; A2 the tools' code, the plugin and the checks changed since the last review; A3 the
  docs against the code; B1 the categories the last review didn't read (`params`, `bitmaps`, `discovery`,
  `script_runner`, `graph_edit_output_fields`, all of `inputs` and `safeguards`); B2 the unit tests and real state,
  Ctrl-C, and `alone` against the pool's lock. No tests run. The lead agent settled each report by reading, and with
  two probes:
  - in Designers an agent started (port 47311, three in turn, each just started; closed afterwards, its folder removed,
    no crash dump): `_home_screen()` and `screenshot_designer('3d')` before any graph was opened; `export_outputs` of an
    output node added right after the node feeding it was measured (HLP-101);
  - in plain Python: the two safety guards' own functions over the files they no longer read (TST-255).
- **Not verified:** none.
- **Resolutions assessed:** all 35, their fixes being in the diff. Questioned: HLP-96 (TST-256), HLP-100 (HLP-101,
  TST-259), PLG-36 (PLG-37), TST-228 (TST-260), TST-229 (TST-258, TST-266), TST-230 (TST-264), TST-233 and TST-234
  (TST-266), TST-236 (TST-257), TST-237 (TST-262), TST-244 (TST-261). The others hold: each test they name exists and
  would fail without its fix (read), and the docs they changed match the code. The decisions whose code is in the
  diff: the code and checks they name exist.
- **Findings:** 14: HLP-101 (Medium, measured), TST-255 (Low-medium), PLG-37 and TST-256 to TST-266 (Low); generation
  2 where they follow an entry, 1 otherwise. Found by more than one reviewer and merged: TST-257 (A1, A2), TST-260 (A1,
  B2), TST-261 (A1, A3), TST-265 (A1, A3), TST-266 (A3, B1, B2).
- **Settled as wrong, and not recorded:**
  - *A failing 3D grab makes facts raise, so its last checks never run* (A2): main's behaviour, which TST-117 kept on
    purpose ("the run failed"); the failure is reported (`script facts/grab_3d_view ran`), and no run has seen the
    grab fail.
  - *A Ctrl-C may keep `run_category`'s clean-up from reaching Designer* (B2): the same on main; on macOS every run is
    in a Designer an agent started ("A Designer the user opened is theirs; one an agent started is disposable").
  - The first review's "in a Designer still on its Home screen that tool answers '3D View menu bar not found'" was
    wrong: the probe found no Home screen in a Designer just started, and that same answer (TST-266).
- **Dropped because of a decision:**
  - "Low-value findings about the tests and docs are not raised": `lifecycle` killed between creating the lock and
    writing its name, leaving a lock no worker's end removes; `changing()`'s 300 s deadline letting a quit into a
    `lifecycle` window longer than that; a dump in `lifecycle`'s folder written after its own settle, which
    `check_the_quits` leaves to it; `choose()` not catching a failed process listing (A1); workers left waiting up to
    300 s in `held` after the pool's parent is killed (B2; the first review dropped "the pool's parent killed").
  - The same rule: README and PLAN.md give 3.2 minutes, PLAN.md's goal 3.4, DECISIONS.md 3.5, each "about" and within
    the 194 to 213 s measured (A3).
- **Suggested order:** HLP-101 first (a wrong result of a tool); TST-256 (the user's clipboard); TST-255 (guards that
  keep library loads out of the user's Designer); TST-257 to TST-260 (results misreported or checks measuring less);
  then the rest. TST-262 asks the user to confirm TST-237's choice for more code.
- **Longest chains still growing:** HLP-96 → TST-256 and HLP-100 → HLP-101, TST-259: generation 2.
- **Checked and found fine:**
  - *`--only`:* an unknown name is refused with the list (exit code 2) before anything starts; a name given twice runs
    once; `--only lifecycle` runs no start checks; `CLIPBOARD` and `SOLO` hold among the chosen; coverage is judged
    over the chosen categories' tools, and a full run still fails on a tool no category exercised; exit codes 0 or 1
    from the pool, 2 for a refusal, `--workers` below 1, an unknown name, `--only` off macOS.
  - *The lock:* `Gate.worker_ended` runs for every worker that ends, removing its own mark and only a lock naming it;
    `held()` writes its holder; `changing()` keeps its mark at its deadline; the TST-235 tests fail without their
    fixes.
  - *The categories the last review didn't read:* no check reads state an earlier category used to leave; the
    set-then-read checks compare against values unlike the library's defaults (read from its `.sbs` files); each moved
    body is main's but for its imports, `ctx.png` (each reader makes its own) and `overridable=True` (render's
    preparation sets it); every script's `ARGS` match its caller's; temporary nodes and inputs are removed in a
    `finally`.
  - *The plugin:* the accept thread starts last; `WeakMethod` holds the bound `_drain`; `stop()` disconnects both
    signals; an emit after `stop()` is answered by its drain of the queue; both new tests fail without their fixes.
  - *HLP-100's second compute:* only when the temporary output's first compute gave none, so a node with no texture
    still raises, after one more compute (about 0.9 s).
  - *Unit tests and real state:* none ends a process or touches `/tmp/sd_mcp_*`, the clipboard, Designer's settings,
    the token or the record folder; the real `pgrep` only reads, and the tests whose result depends on it patch it;
    the plugin's tests bind ephemeral ports. (TST-261, TST-263 and TST-264 are the exceptions found.)
  - *Ctrl-C:* the `finally`s of `run_category`, `run()`, `held` and `changing`, and `lifecycle`'s put-back record, run
    on `CancelledError` (every broad catch is `except Exception`); Designers start in sessions of their own, so the
    signal doesn't reach them.
  - *The docs:* README's commands work as written; each row of the categories table matches its category (some leave
    tools out, none says something false); GUIDE.md's Undo, log-noise and compute bullets match the code and the checks
    measuring them; AGENTS.md's `--only` line; DECISIONS.md's reworded reason.
- **Not read:** `lifecycle/checks.py` outside its quits, its lock windows and the hand-over check;
  `test_selftest_pool.py` lines 60 to 290 and 420 to 540 in detail; README and GUIDE.md outside their changed parts.

### 2026-11-11: the branch `faster-test-runs` against `main`, third round (the diff only)

- **How:** three reviewers (subagents, reading only): R1 the last round's fixes (commits for HLP-101 to TST-266, item
  48); R2 what the earlier rounds didn't read of the pool and `lifecycle` (all of `lifecycle/checks.py`, the scheduler,
  `test_selftest_pool.py`); R3 the categories no round had compared check by check with their preparations. No tests
  run. The lead agent settled each report by reading, and with two probes in Designers an agent started (port 47311,
  each just started, closed afterwards, its folder removed, no crash dump):
  - HLP-100's second compute removed in a scratch copy of the repo: `measure.run` whole, 5 Designers; the check on its
    own, 5 Designers; and `check_every_panels_screenshot` alone on the real code;
  - `link_display`'s preparation, the graph then opened, the whole category, the editor's graph read after each call,
    3 Designers (TST-267).
- **Not verified:** `test_a_worker_gets_its_port_and_snapshots_by_their_real_path` (`tests/unit/test_selftest_workers.py:35`)
  calls `symlink_to`, which on Windows needs a privilege, so it may raise `OSError` there (R2). No Windows machine here
  (ROADMAP item 18); running that test on Windows would settle it.
- **Resolutions assessed:** all 49, by the three reviewers for their areas, R1 going through the last 14 one by one.
  Questioned: HLP-100, HLP-101 and TST-229 (TST-270). The others hold.
- **Findings:** 4: TST-267 (Low-medium), TST-268 to TST-270 (Low). **No defect in the tools' code this round, and
  nothing that can touch the user's work.** Found by more than one reviewer and merged: TST-270 (R1, R2, R3).
- **Settled as wrong, and not recorded:**
  - *The move to `run`'s end made HLP-100's check blind, its first trials used up by the new check before it* (R1, R3):
    with the second compute removed, its `node_stats`, `preview_node` and `sweep_param` checks failed in 5 whole runs of
    5. The check still guards the fix.
  - *`check_every_panels_screenshot` fails on `console` when run alone, `show_console` being in `run`* (R1): run alone in
    a Designer just started, it passed, the console's panel included.
- **Dropped because of a decision:** "Low-value findings about the tests and docs are not raised": `_clean_up`
  deleting the folder of a Designer that wasn't recorded; a `ps` failure making a recorded Designer look like the user's;
  a worker with no time limit (R2). Follow-up chains: `undo`'s three skips on `'SCHEDULED' not in t`, main's behaviour:
  the only fix would add a check, at generation 3 of TST-229 → TST-258 (R3).
- **Suggested order:** TST-267 first (the state a user works in), then TST-268 and TST-269; TST-270 only narrows
  sentences.
- **Longest chain still growing:** HLP-96/HLP-100 → HLP-101, TST-259 → TST-270, generation 3, comments and test names
  only: the fix narrows them. Reviews are converging: round one 23 findings, round two 14, this one 4, none of them in
  the tools.
- **Checked and found fine:**
  - *The last round's fixes:* `export_outputs` re-reads every output after the second compute; `_refusal(c, None)`
    doesn't refuse beside other runs' recorded Designers; `first` with only `lifecycle` or only solo categories; the
    handlers TST-262 removed were unreachable; TST-256's marker can't pass on a capture that restored nothing; every test
    the 14 resolutions name fails without its fix (read); the fakes in `test_export_outputs.py` and
    `test_selftest_check_setups.py` answer in the real formats. With the graph open, no later check of `measure` reads
    differently: the first check deletes its output node.
  - *`lifecycle` beside other workers:* `has_ended` and `own_pid` read only the process recorded on its port; the user's
    log and preferences compared before and after can't be moved by a worker, each having its own home and `choose`
    refusing the user's Designer; crash steps look only at its own port, the ports it lists and the shared folder.
  - *The scheduler and the lock:* slots, `exclusive`, `solo`, the gate and a worker ending early hold; no path that
    never ends was found; `merge`, `summarize`, the unit check and the exit code agree.
  - *The 15 categories against their preparations:* bodies identical to main's but for imports and the additions
    recorded; every script's arguments match its caller's (compared with `ast`); no check on an empty list or a value
    already there; `render`'s seeds, `save`'s bitmap references, `layout`'s spacing and `link_display`'s fan-out are
    prepared.
- **Not read:** `lifecycle/designer_scripts/`; the bodies of seven `facts` scripts whose moves are comment-only;
  `examples/build_dwarf_trimsheet.py` beyond its header and save code; run logs.

### 2026-11-11: the branch `faster-test-runs` against `main`, a full review (the whole diff)

- **How:** at the user's request, the whole diff again, every changed file read whatever earlier rounds covered. Five
  reviewers (subagents, reading only): F1 the pool and the test infrastructure; F2 the code that ships (tools, helpers,
  plugin); F3 `lifecycle`, `bridge`, `undo`, `safeguards`, `inputs`, `params`, `bitmaps`, `discovery`, `script_runner`; F4
  the other categories; F5 the docs. No tests run. The lead agent settled each report by reading, and with these probes,
  one at a time, in Designers an agent started (port 47311, each just started, closed afterwards, its folder removed, no
  crash dump) or in plain Python:
  - HLP-100's check, with its second compute removed in a scratch copy of the repo, with the plugin's wake on and off,
    5 Designers each (PLG-38);
  - the end of a run's "your graph back" step after a second read of the editor's graph, and without one (TST-271);
  - `params`, `inputs`, `bitmaps` and `safeguards` with their graph open, then also with an output node in it, 2
    Designers each;
  - 8 outputs at 4096 px, the process's memory before and after reading every texture;
  - which thread frees a stopped server, with the plugin's unit-test fakes (PLG-39);
  - 2.3 million local connections to a port nobody listens on (`workers.answering`).
- **Not verified:** a stale wake (F2). A job B reaching an idle bridge posts a wake; the timer takes B first; C arrives
  while B runs, so it gets no wake; when B ends, B's wake, queued ahead of whatever B posted, starts C at once, which is the
  case of PLG-13. The path is in the code; it needs a timer tick between a post and its delivery with two clients at once,
  a race that can't be brought on demand. It depends on what PLG-38 decides for the wake.
- **Resolutions assessed:** all 53. Questioned: HLP-100 and HLP-101 (PLG-38), PLG-36 (PLG-39), TST-258 (TST-276), TST-267
  (TST-271), TST-268 (TST-274). The others hold.
- **Findings:** 9: PLG-38 (Medium, measured), TST-271 and TST-272 (Low-medium), PLG-39 and TST-273 to TST-277 (Low).
  Found by more than one reviewer and merged: TST-276 (F1, F4, F5).
- **Settled as wrong, and not recorded:**
  - *`export_outputs` now holds every output's texture until the last is saved, so peak memory grows with the outputs*
    (F2): reading 8 textures at 4096 px left the process's memory where it was (1290 MB before and after).
  - *`workers.answering` can report true with nothing listening, a connection meeting itself* (F1): 2.3 million tries,
    none connected.
  - *`params`, `inputs`, `bitmaps` and `safeguards` no longer run with their graph open, so a defect that needs a view
    open passes* (F3): with it open, then also with an output node in it, 213 of 213 checks each time, in 4 Designers.
    Nothing differs in what they measure; opening it would add coverage of that state only.
  - *`FAR_COMMENT_INSIDE`'s `all()` passes on an empty list; render's "put the seed back as it was"* (F4): the same code
    and state as on main, not changed by the branch.
- **Dropped because of a decision:** "Low-value findings about the tests and docs are not raised": `graph_edit_wire`'s
  `took < 4` beside other Designers, never seen failing (F4); PLAN.md's status figures (F5); `spawn` raising, a worker with
  no time limit, the first worker going on after a failed start (F1). "The 3D screenshot puts back only the clipboard's
  text": the two clipboard checks keeping only the text (F4).
- **Suggested order:** PLG-38 first, which takes the user: the wake is what the rest of this branch's timing rests on.
  TST-271 next (TST-267's fix broke the Windows run's end), TST-272 (a user's first run), then the rest.
- **Longest chain still growing:** TST-258 → TST-276, generation 3, docstrings only: the fix narrows them.
- **Checked and found fine:**
  - *The plugin:* no wake is lost (`idle` and `put` under one lock, the timer behind it); no job inside another; `stop()`
    answers queued clients and frees the port; `PROTOCOL` stays 2; the abort tracer doesn't land in `_on_wake`.
  - *The tools:* `.compute()` occurs only in the two functions with a retry; nodes at (0, 0) read in the only two
    places that read `<gpos>`; `export_outputs`' result text on its no-output, typo and duplicate-name paths.
  - *The pool:* `merge`, `summarize`, the unit check, `--only`'s coverage and the exit codes agree; slots, `exclusive`,
    `solo` and a refused gate hold; `choose` refuses an unrecorded Designer; `end_own_designer`, `own_here`, `_clean_up` and
    `close_with` act only on recorded ports and processes; `spawn` and `run` refuse under pytest.
  - *The categories, every check read:* each moved body is main's but for the additions recorded; every `ctx` name read is
    set by a preparation; every script's arguments match its caller's; every skip is gated on `was_running` or the platform.
  - *The docs:* README's commands and exit codes, all 23 category rows, GUIDE.md's changed bullets, AGENTS.md's commands,
    the live-check skill against the code, PLAN.md's steps and decisions, ROADMAP's changed rows, all 388 added comment and
    docstring lines of the self-test. (TST-272 and TST-276 are the exceptions.)
- **Not read:** run logs; README and GUIDE.md outside their changed parts; PLAN.md's measured figures.

### 2026-11-11: the branch `faster-test-runs` against `main`, a second full review (the whole diff)

- **How:** the whole diff again, every changed file read, by five reviewers (subagents, reading only), split as in the
  first full review: F1 the pool and the test infrastructure; F2 the code that ships; F3 `lifecycle`, `bridge` and the
  safety categories; F4 the other categories; F5 the docs. No tests run. The lead agent settled each report by reading,
  and with one probe in two Designers an agent started, one after the other (port 47311, each just started, closed
  afterwards, its folder removed, no crash dump), on plugin v6: 100 short jobs one after the other, the time each took;
  a job sent 50 ms into one of 0.3 s, the gap between them, 5 times; and one compute of a node queued 150 ms into the
  measure of the node feeding it, 5 times. Twice.
- **Not verified:** the stale wake (the first full review's log): its precondition, a job the poll takes before the
  wake's timer fires, now happens on the path PLG-40 measured; what the stale timer then does to the next job wasn't
  measured, a race that can't be brought on demand. PLG-40's fix would remove it.
- **Resolutions assessed:** all 62. Questioned: PLG-38 (PLG-40), TST-260 and TST-266 (TST-279), TST-265 (TST-278). The
  others hold, PLG-39, TST-271, TST-273 and TST-274 among them.
- **Findings:** 4: PLG-40 (Low-medium, measured), TST-278 to TST-280 (Low). Found by more than one reviewer and merged:
  PLG-40 (F2, F3, F5).
- **Settled as wrong, and not recorded:**
  - *PLG-39's `_retired` keeps the Qt objects until Python ends, after Designer's QApplication, which may crash Designer
    at quit* (F2): every Designer an agent started on plugin v6 today quit normally, more than 20, with no crash dump.
  - *`check_compute_takes_a_fixed_time`'s name claims a fixed time; the check asserts a floor* (F4): the name is the
    fixed cost per compute GUIDE.md describes ("about 0.9 s however small the graph"), which the check asserts as a floor.
- **Dropped because of a decision:** Follow-up chains, generation 3, a fix that would only add a check: no unit test
  sees `run_pool` pass `answering` on (F1). "The plugin waits 30 ms before a job reaching an idle bridge": whether 30 ms
  holds under the pool's load is the full run's to show (F3, F4). "The 3D screenshot puts back only the clipboard's
  text": the 3D capture check with an empty clipboard (F4). "Low-value findings": `Ctx`'s comment on the nodes'
  connections, a docs follow-up at generation 4 (F4).
- **Suggested order:** PLG-40 (its fix makes the decision's wait hold); then TST-278 to TST-280.
- **Longest chain still growing:** HLP-100 → PLG-38 → PLG-40, generation 3, in the plugin's code.
- **Checked and found fine:**
  - *The plugin:* wakes are never lost or doubled (a wake during the wait restarts it); `stop()` racing an emit is
    harmless (a late drain finds an empty queue); no job starts inside another; the waker and its timer live on the main
    thread; `_retired` keeps only them, not the server, so PLG-36 holds.
  - *The pool:* the scheduler, the lock, the results, `_clean_up`, `spawn` and `run()` under pytest, `alone`'s
    environment and exit codes, the fakes' formats.
  - *The categories:* every check's body is main's but for the recorded additions; every Designer script matches main's
    or was read in full; every script's arguments match its caller's (with `ast`); the strings of code sent to Designer
    (escapes, the helpers' names); every skip gated; no list or count passing empty but the one settled as main's; each
    preparation builds what its checks read.
  - *The docs:* README's commands, prerequisites, exit codes and categories; AGENTS.md; GUIDE.md's changed bullets; the
    live-check skill's names; DECISIONS.md's paths, and no entry citing a review finding; ROADMAP's changed rows;
    PLAN.md's steps.
- **Not read:** run logs; README and GUIDE.md outside their changed parts.

### 2026-11-11: the branch `faster-test-runs` against `main`, a third full review (the whole diff)

- **How:** the whole diff again, every changed file read, by five reviewers (subagents, reading only), split as in the
  earlier full reviews (F1 the pool, F2 the code that ships, F3 `lifecycle` and the safety categories, F4 the other
  categories, F5 the docs), the plugin's v7 minimum read most closely. No tests run. Every report was settled by reading;
  no probe was needed.
- **Not verified:** none.
- **Resolutions assessed:** all 66. Questioned: PLG-40 (PLG-41, PLG-42), PLG-39, TST-265 and TST-279 (TST-281). The
  others hold; PLG-40's bridge check fails without the minimum and holds with it (F3, by reading the timers).
- **Findings:** 3, all Low: PLG-41 (in the plugin's code), PLG-42 (the decision's wording against v7, for the user),
  TST-281 (sentences and test names). Found by more than one reviewer and merged: PLG-42 (F2, F3, F5), TST-281 (F1, F2,
  F4, F5). Two categories' reviewers (F3, F4) found nothing in their checks.
- **Settled as wrong, and not recorded:** none.
- **Dropped because of a decision:** "Low-value findings about the tests and docs are not raised": PLAN.md's dated "logs
  'No output node defined' only in a graph with one" (F5); `categories.py`'s pointer to PLAN.md step 5 for the times
  (F5); a Designer the user opens during a pool, crashing, failing "outside the run" (F1); a test's comment "quit_designer
  is always skipped while your own Designer runs", still true on Windows (F1); `check_the_guide` and `check_the_start`
  in the index, a style point (F1).
- **Suggested order:** PLG-42 first, which takes the user and decides how PLG-41 is fixed; then TST-281.
- **Longest chain still growing:** HLP-100 → PLG-38 → PLG-40 → PLG-41, PLG-42, generation 4, in the plugin. The rounds:
  23, 14, 4, 9, 4, now 3 findings; none a wrong result of a tool.
- **Checked and found fine:**
  - *The plugin, v7:* a wake restarting a timer `later` set only pushes the start back; `later` restarting the wake's
    timer sets it to the minimum; a timer firing early is checked again; no job starves, starts twice or runs off the
    main thread; `ended` is read and written on the main thread only; `draining` comes before the minimum, so a drain
    inside a job neither defers nor starts anything; a cancelled or abandoned job during the wait is skipped; `stop()`
    against a late wake is harmless; no lock taken in a new order.
  - *The pool:* the scheduler, the lock, the results and exit codes, `_clean_up`, `choose`, the crash folders
    (TST-280's `run_port=False` on both calls), the fakes against the real formats; every named test fails without its fix.
  - *The categories:* every check of all 23 against its preparation and main: no state from another category, no
    comparison against a value already there, no list or count passing empty but main's, every skip gated, every
    script's arguments matching; the 30 ms minimum breaks no timed check (`took < 4`, `lifecycle`'s `took < 30` s,
    `bridge`'s other timings).
  - *The docs:* README's commands, prerequisites, exit codes and 23 rows; AGENTS.md; GUIDE.md's changed bullets; the
    skills; DECISIONS.md's paths and tests; ROADMAP's changed rows; PLAN.md's steps and decisions; every added comment and
    docstring of the self-test.
- **Not read:** run logs; README and GUIDE.md outside their changed parts.

---

## High

## Medium-high

## Medium

- [x] **HLP-96 · `screenshot_designer('3d')` puts the clipboard back without its RTF data, and the self-test's check can't see it** · `mcp_server/designer_helpers/screenshots.py:65-87`, `tests/test_all_tools/editor_panels_and_fit/checks.py:30-46`, `README.md:307` · measured · found 2026-11-10
  - **Defect.** The 3D capture goes through the clipboard: `_save_3d_render` copies `original.data(fmt)` for each
    of `original.formats()` into a `QMimeData`, clears the clipboard, copies the render and, in a `finally`,
    `clipboard.setMimeData(backup)`. Not every format comes back. The self-test's "3d + clipboard kept" compares
    `clipboard_fingerprint()` before and after, and when they differ ("the user may have copied something
    meanwhile") measures again around a second capture, which finds the clipboard the first one already reduced
    unchanged, and passes. README says the tool "puts back whatever was on your clipboard".
  - **Scenario.** Measured once, in the review's fourth probe (a Designer an agent started, facts' preparation, the
    graph opened, one `screenshot_designer('3d')`): the clipboard held HTML 285, RTF 203, utf8 9 and ut16 22 bytes
    before, and HTML 285, text 9 and ut16 20 after; the text's hash unchanged. Whoever copied formatted text before
    an agent took a 3D screenshot pastes it unformatted where the format came from RTF. The self-test's check passes
    in every run kept.
  - **Fix.** Decided by the user (2026-11-10): fixed on this branch. First measure why, with scratch probes: which
    formats Qt lists for that clipboard and which it fails to put back (the macOS names behind RTF), and with other
    clipboards (an image, files, text alone). Then make the backup restore every format it read, or, for formats Qt
    can't carry, say so in the tool's result and README rather than promise it. The check: a format missing after
    the first capture fails, whatever the second shows; the second capture stays only for a clipboard whose content
    changed meanwhile. Seen failing, then passing, in a scratch run; a unit test for any pure-Python part. Near the
    decision "The self-test's empty-clipboard check loses no clipboard data, as far as measured", which is about
    another check and isn't touched.
  - **Resolution: done**, as the Fix's second way: the limit stated, not removed. Worse than the entry measured:
    probed on five clipboards, Qt's backup lost rich text's RTF, an image (back as a 0-byte TIFF), all but one item
    of two copied files and an app's own type; plain text and HTML were kept. The user chose (2026-11-10) to keep
    that backup and say so: they don't mind losing their clipboard when an agent needs it, as long as the text comes
    back (DECISIONS.md, "The 3D screenshot puts back only the clipboard's text; the rest may be lost").
    - **Test:** `check_the_3d_capture_puts_the_text_back` (`editor_panels_and_fit/checks.py`) puts a known text on
      the clipboard, captures, and reads the same text back (a capture that put nothing back would leave the render
      there); the user's text put back afterwards. Passed in its scratch run with
      `check_an_empty_clipboard_has_mimedata`, now a function of its own that compares the clipboard's text, not a
      fingerprint of every type. The old check couldn't see a loss: when the fingerprints differed it measured again
      around a second capture, which found the clipboard the first had reduced unchanged.
    - **Cause:** the backup goes through Qt's `QMimeData`, which on macOS carries only the formats it converts.
    - **Fix:** the tool's description (`server_tools/views.py`), its result line and README now say the text is put
      back and anything else may be lost; `common.clipboard_fingerprint` became `clipboard_text` and
      `set_clipboard_text`. Tried first and withdrawn at the user's choice: a native backup of every item and type
      (`designer_helpers/pasteboard.py`, ctypes on the Objective-C runtime), which put everything back but ran native
      code in the user's Designer, reading every type with no deadline (HLP-97 and the findings after it).
    - **Also covered:** every `mimeData()`, `setMimeData` and `.clipboard()` in `mcp_server/`, `plugin/`, `client/`,
      `examples/` and `tests/`: only `_save_3d_render` and the empty-clipboard fact's script back up the clipboard,
      both through Qt, both covered by the decision. The decision "The self-test's empty-clipboard check loses no
      clipboard data, as far as measured" had its "Reopen if" met (data was seen lost through that backup): at the
      user's decision it is replaced by the one above.
  - Questioned by HLP-97, HLP-98, TST-249 and TST-253 (2026-11-10).
  - Questioned by TST-256 (2026-11-10).

- [x] **HLP-97 · The 3D capture reads every type of the user's clipboard on Designer's main thread, with no deadline or size limit · follows HLP-96, generation 2** · `mcp_server/designer_helpers/pasteboard.py:80-96`, `mcp_server/designer_helpers/screenshots.py:70, 91-96` · measured · found 2026-11-10
  - **Defect.** `pasteboard_read` calls `dataForType:` for every type of every item. That call waits for the
    clipboard's owner when the data is provided on request (a type macOS derives, a promise). Qt's backup asked only
    for the few types it converts, and for none of an image. The read runs on Designer's main thread, inside a
    native call that a cancel or the script's timeout can't interrupt, and nothing limits the bytes it copies.
  - **Scenario.** Measured while fixing HLP-96: with the clipboard's owner alive but not answering (the check's own
    process, waiting for Designer), Designer's read of rich text waited until the call timed out (60 s, `views.py`).
    The same happens if the app the user copied from hangs. The bridge then gives up, but the job goes on: when the
    read returns, the capture runs and its `finally` writes the clipboard it read over whatever the user copied
    since. Not measured: a large clipboard (a big spreadsheet range, a layer of an image editor, hundreds of files in
    Finder), whose owner then renders every representation, possibly hundreds of MB, copied twice.
  - **Fix.** Read on a worker thread with a deadline (the ctypes calls release the GIL) and a cap on the total size;
    past either, refuse the capture before `clipboard.clear()`, saying the clipboard couldn't be saved (nothing is
    lost then). The same deadline for the self-test's reads. A probe first: whether `NSPasteboard` may be read off the
    main thread from Designer, and how long a large clipboard takes.
  - **Resolution: done:** the native reading it is about was removed at the user's choice (HLP-96's resolution): the
    capture reads the clipboard through Qt again, as before this branch.

- [x] **HLP-100 · `node_stats` and `preview_node` say a connected node "produced no texture" right after a node upstream of it was measured, its graph open in the editor** · `mcp_server/designer_helpers/describe.py:259-295` (`_with_node_texture`) · measured · found 2026-11-10
  - **Defect.** `_with_node_texture` computes, attaches a temporary output when the node has no texture, computes
    again, and otherwise raises "node %s produced no texture (are its inputs connected?)". With the graph open in the
    editor, once a node upstream has been measured the same way (its own temporary output attached, then deleted),
    the downstream node's second compute gives no texture the first time.
  - **Scenario.** Probes in a Designer an agent started (port 47311), on facts' preparation (the graph open):
    `gradient_linear_1` connected into `normal` with `apply_edits`, then `node_stats` of the gradient, or
    `preview_node` of it, then `node_stats` of the normal: "produced no texture" 3 times in 3, `preview_node` of the
    normal failing after it too; with nothing measured first, 2 of 2 fine; a second try works. The graph not open
    (the same preparation without `open_graph`): fine. The same steps in raw code (`execute_designer_code`, the
    helper's sequence) didn't reproduce it (5 of 5 fine, one first compute timed out), so the cause is in what differs
    and wasn't found. An agent is told the inputs aren't connected when they are, in the state the user works in.
    Seen as facts' "normal inversedy=True is OpenGL" failing once TST-229 opened the graph. `sweep_param` uses the
    same helper (not measured).
  - **Fix.** Measure what differs from the raw sequence (the tool's undo group, the helper's graph lookup, the
    editor's own compute after the deletion), then fix it there (a compute after processing events, if that is what
    it needs); a live check: a node measured right after its upstream node, the graph open.
  - **Resolution: done.**
    - **Test:** `check_a_node_measured_right_after_the_one_feeding_it` (`tests/test_all_tools/measure/checks.py`): the
      graph open with an output node of its own, a fresh gradient → normal pair for each tool, the upstream node
      measured with `node_stats` first. In scratch runs before the fix: `node_stats` failed 2 times in 2 ("produced no
      texture"), `preview_node` 1 in 2; `sweep_param`'s view never failed (it sets the parameter before each compute)
      and stays as a guard.
    - **Cause, measured:** probes in a Designer an agent started (port 47311). With the graph open, it happened 4
      times in 4 when the graph held an output node (fed or not), never without one, so `measure`'s graph (none)
      didn't show it and facts' did. The helper called through `execute_designer_code` behaved like the tool, so the
      tool's path wasn't the cause. In the helper's own steps, after `node_stats` of the upstream node: the compute
      with the temporary output attached gave no texture 3 times in 3, and one more compute gave it 9 times in 9
      (processing Qt's events first not needed). Not every time: in facts' graph and later in `measure`'s the first
      compute gave one.
    - **Fix:** `_with_node_texture` (`designer_helpers/describe.py`) computes once more when the temporary output's
      first compute gave none, only then. Its docstring and GUIDE.md (sd API, `graph.compute()`) say so. After it, in
      scratch runs in fresh Designers: the check passed 3 times in 3, and facts' "normal inversedy=True is OpenGL"
      passed.
    - **Also covered:** `_with_node_texture` is the one place that attaches a temporary output; every tool computing a
      node goes through it (`node_stats`, `check_tiling`, `compare_to_reference`, `preview_node`, `sweep_param`).
    - **No "designer facts" check:** one of the raw behaviour (the first compute none, the next one) was tried in
      facts and in `measure`: the first compute gave a texture all 3 times, so it would only skip. The tools' check
      above is what fails without the second compute.
  - Questioned by HLP-101 and TST-259 (2026-11-10).
  - Questioned by TST-270 (2026-11-11).
  - Questioned by PLG-38 (2026-11-11).

- [x] **HLP-101 · `export_outputs` says a connected output node "computed no image" right after the node feeding it was measured · follows HLP-100, generation 2** · `mcp_server/designer_helpers/save_export.py:88-97` · measured · found 2026-11-10
  - **Defect.** `export_outputs` computes the graph once (`g.compute()`) and reads each output node's texture; one
    with none goes in `no_image` ("never seen: an unconnected output still computes one"). HLP-100 measured that the
    first compute after an output node is attached can give no texture, right after another node was measured with the
    graph open, and fixed it in `_with_node_texture` alone; its **Also covered** lists the tools that compute a node
    through a temporary output, not `export_outputs`, which computes output nodes just added the same way.
  - **Scenario.** Probe in Designers an agent started (port 47311), on `measure`'s preparation with an output node of
    its own and the graph opened; each trial a fresh `gradient_linear_1` → `normal` pair, `node_stats` of the gradient
    or not, then `apply_edits` adding an output node fed by the normal, then `export_outputs`. In a Designer just
    started, the first two trials (the gradient measured) answered "exported 1 file(s) ... computed no image, not
    exported: probe_new0" (then probe_new1); the next three exported it, and so did all six in another Designer just
    started (three without the measure first, then three with it). 2 of 11 in all, both right after the measure, the
    first two trials in their Designer. An agent is told an output fed by a working node computes nothing; asking for
    that output alone, it gets "no outputs exported".
  - **Fix.** When an output gave no texture, compute once more, only then, as `_with_node_texture` does (sharing that
    rule if it fits); the comment then says what was measured. A live check: an output node added right after the node
    feeding it was measured, the graph open, then exported, seen failing first; it failed only in a Designer just
    started, so the check may need that, or several fresh pairs as HLP-100's check uses.
  - **Resolution: done.**
    - **Test:** `check_an_output_added_right_after_the_node_feeding_it_was_measured` (`measure/checks.py`, first in its
      `run`, where nothing has been computed yet): in scratch runs each in a Designer just started, it failed in 2 of 6
      ("no outputs exported ... computed no image"). `tests/unit/test_export_outputs.py`: a second compute when the first
      gave no image, and the message after two, failed; one compute when it gave one is the guard.
    - **Cause:** as HLP-100's, measured there, not explained: the compute can give no texture to an output node just
      attached, right after another node was measured; `export_outputs` read the outputs after one compute.
    - **Fix:** `export_outputs` (`designer_helpers/save_export.py`) computes once more when an output gave none, only
      then; its docstring says so. After it, the check passed in 8 of 8 Designers just started.
    - **Also covered:** every `.compute()` in `mcp_server/`, `client/`, `examples/` and `plugin/`: the only other is
      `_with_node_texture`, which has it. GUIDE.md's `graph.compute()` bullet already says to compute again.
  - Questioned by TST-270 (2026-11-11).
  - Questioned by PLG-38 (2026-11-11).

- [x] **PLG-38 · The plugin's wake is what brings on the "no texture" of HLP-100 and HLP-101: the retries mask it, and neither entry found the cause · follows HLP-100, generation 2** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:448-451`, `mcp_server/designer_helpers/describe.py:262-266, 287`, `mcp_server/designer_helpers/save_export.py:82-85, 101-104`, `mcp_server/GUIDE.md` (`graph.compute()`) · measured · found 2026-11-11
  - **Defect.** This branch added `_Waker` (PLAN.md, step 3): a job reaching an idle bridge starts at once instead of at
    the next 100 ms tick of the timer, about 85 ms less per call. Calls now start right after the one before. HLP-100's
    resolution found what brings it on but not why, and HLP-101's says "measured there, not explained"; both retry around
    it, and GUIDE.md and the docstrings present it as how `compute()` behaves.
  - **Scenario.** Probe: a scratch copy of the repo with `_with_node_texture`'s second compute removed;
    `check_a_node_measured_right_after_the_one_feeding_it` on `measure`'s preparation, in Designers just started (port
    47311), 5 with the wake and 5 with it off (`m._server.waker.wake.disconnect()` from a setup, the 100 ms timer doing the
    work). With the wake: 5 runs of 5 failed ("produced no texture"), `sweep_param` 5 of 5, `preview_node` 4 of 5. With it off:
    0 runs of 5, 15 checks of 15 passing. Not measured: which of
    Designer's own steps needs the gap, how long a gap is enough, or any other tool that reads state right after a call
    (the final check passed, retries included). HLP-101's check wasn't run this way (it fails 1 run in 3, too rare for
    so few).
  - **Fix.** The user's decision, weighing about 85 ms per call: (a) keep the wake and the retries, and correct what they
    say about the cause (docstrings, GUIDE.md, PLAN.md); (b) remove the wake, and the retries with it if they are then
    not needed; (c) delay the wake a few ms (to measure: how few). A probe of the chosen one in fresh Designers.
  - **Resolution: done.** The user's choice (2026-11-11): (c), wait a little; DECISIONS.md, "The plugin waits 30 ms
    before a job reaching an idle bridge".
    - **Measured first:** HLP-100's check with the retry removed, the wake delayed by a timer from a setup, 5 Designers
      just started each: 0 ms failed 4 runs of 5, 5 ms 4 of 5, 20 ms and 50 ms none of 5. 30 ms chosen, for a margin.
    - **Test:** `test_the_wake_lets_designer_settle_before_it_drains` (`tests/unit/test_plugin.py`) failed (no wait); a
      check in `measure`'s `check_a_node_measured_right_after_the_one_feeding_it`, "one compute gives the texture", which
      runs the helper's steps with one compute and no retry, failed 3 runs of 3 on the plugin as it was (`TEXTURE=False`);
      `bridge`'s check, now `check_a_job_sent_when_idle_starts_after_the_wakes_wait` (median between the wait and the
      wait + 30 ms), failed (median 1 ms).
    - **Cause:** the plugin started a job about 1 ms after the one before; Designer evidently needs a moment after a job,
      for what wasn't found.
    - **Fix:** plugin v6: `_Waker` starts a single-shot timer of `WAKE_DELAY_MS` (30) on the wake, which runs the drain;
      `stop()` stops it. `install.py` run; the Designers an agent started load it, the user's at its next start. After it,
      in Designers just started: `bridge`, `link_display` and `render` 96 of 96 (median 33 ms); HLP-100's check 3 of 3 and
      HLP-101's 3 of 3; with both retries removed in a scratch copy, 5 of 5 and 6 of 6.
    - **Also:** the retries stay as a defence, their docstrings giving the cause; GUIDE.md's sentence asking scripts to
      compute again is gone (a script runs in one job); PLAN.md, step 3, and README's `v6`. The stale wake under **Not
      verified** in the review log isn't touched by the wait.
  - Questioned by PLG-40 (2026-11-11).

## Low-medium

- [x] **TST-228 · `alone.run(..., own_designer=True)` runs its checks without asking whose Designer is open** · `tests/test_all_tools/alone.py:157-170` · confirmed · found 2026-11-10
  - **Defect.** With `own_designer=True` the checks run before `_own_designer()`, the only place `alone` refuses a
    Designer the user opened: `if own_designer: for check in checks: ... await check(ctx) ... return`, and only after
    it `refusal = await _own_designer(c, port)`. The flag is new on this branch. `lifecycle.run`, which it is for,
    guards itself (`check_a_designer_of_its_own`); `alone` doesn't, though its docstring says "It runs in a Designer
    an agent started, never the user's".
  - **Scenario.** The user's Designer is open and an agent passes the flag, with no `port=`, to anything but
    `lifecycle.run`, say `alone.run(bridge.run, own_designer=True)`: the checks run in the user's Designer (graphs
    created, code run), and no clean-up follows. `test_checks_with_their_own_designer_get_none_started_and_no_clean_up`
    pins that not even `designer_status` is asked (`c.names() == ['get_guide', 'get_guide']`).
  - **Fix.** In the `own_designer` branch, refuse when a Designer answers that no agent started, or one runs that
    isn't answering yet (as `_own_designer` tells them apart), or take the flag only for steps of `lifecycle`; a unit
    test with the user's Designer answering.
  - **Resolution: done.**
    - **Test:** `test_checks_with_their_own_designer_never_run_beside_the_users` (`tests/unit/test_selftest_alone.py`),
      the user's Designer answering and one no agent recorded not answering yet: both ran the check, exit code 0
      instead of 2. `test_checks_with_their_own_designer_run_beside_an_agents` keeps the case lifecycle needs.
    - **Cause:** the `own_designer` branch returned before `_own_designer()`, the only place whose Designer runs was
      asked.
    - **Fix:** `_refusal()` (`alone.py`) tells the user's Designer apart, as `_own_designer` did, without starting one;
      both paths use it, so `own_designer` runs nothing beside the user's (exit code 2). The docstrings say so.
    - **Also covered:** `test_checks_with_their_own_designer_get_none_started_and_no_clean_up` now expects the
      `designer_status` call. `lifecycle.run` in a scratch run with the flag, in a Designer an agent started: 39 of 39.
  - Questioned by TST-260 (2026-11-10).

- [x] **TST-229 · The facts check of the 3D view's widget capture is skipped in every run since the categories prepare themselves** · `tests/test_all_tools/facts/checks.py:405-411`, `tests/test_all_tools/facts/preparations.py` · measured · found 2026-11-10
  - **Defect.** facts' preparation never opens its graph in the editor, so its Designer, just started, still shows
    the Home screen and has no 3D view. The check then skips on any answer that isn't an image, under one label:
    `if 'NO_3D_VIEW' in t or not is_image(render): skip(F, 'widget capture of the 3D view is not the render', 'no 3D
    View visible in Designer')`. PLAN.md (line 265) records it as normal: "one skip (no 3D view)".
  - **Scenario.** The run logs kept from this branch: the check passed in the 7 runs from before step 5 (its graph
    opened by earlier categories in the same Designer) and was skipped in all 10 full runs since, so the final check
    no longer measures that GUIDE.md fact. Probe (facts' own `prepare(ctx)` in a Designer just started, then the check's two
    calls): `grab_3d_view` printed `NO_3D_VIEW` and `screenshot_designer('3d')` answered "RuntimeError: 3D View menu
    bar not found"; after one `open_graph` of the graph, `SAVED=True` and an image. (Two reviewers.)
  - **Fix.** Open the graph in facts' preparation, as `editor_panels_and_fit/preparations.py` does, and skip only on
    `NO_3D_VIEW` or "not visible": any other answer that isn't an image fails the check. Correct PLAN.md's line.
  - Note (2026-11-10): in TST-241's side-by-side runs the check passed once, in a Designer reused from earlier calls
    (its Home screen closed by then), and was skipped in two started for the run: as this entry says.
  - **Resolution: done.**
    - **Test:** the check itself (`facts/checks.py`): on facts' preparation as it was, in a Designer just started, it
      now failed (`NO_3D_VIEW` / "3D View menu bar not found") instead of skipping.
    - **Cause:** facts' preparation never opened its graph, so a Designer just started had no 3D view; the check
      skipped on any answer that wasn't an image.
    - **Fix:** facts' preparation opens its graph (`open_graph`); the check skips only in the user's Designer
      (`ctx.was_running`) when the 3D view isn't visible, and fails on anything else that isn't an image. Scratch
      run, fresh Designer: passed (mean difference 110 of 255). PLAN.md's "one skip (no 3D view)" now says why.
    - **Also covered:** the graph open in the editor made facts' normal-map check fail: HLP-100, a defect of the
      tools, recorded. That check no longer raises (`KeyError`), so the rest of facts runs.
  - Note (2026-11-10): HLP-100 fixed; facts' normal-map check passes on this preparation.
  - Questioned by TST-258 and TST-266 (2026-11-10).
  - Questioned by TST-270 (2026-11-11).

- [x] **TST-230 · Unit tests remove the self-test graph's snapshots from the real snapshot folder** · `tests/test_all_tools/category_run.py:113-121`, `tests/test_all_tools/common.py:537-540` · confirmed · found 2026-11-10
  - **Defect.** `_cleaned` ends every category with `remove_test_snapshots()`, which removes
    `<SD_SNAPSHOT_DIR or ~/.sd_mcp/snapshots>/mcp_selftest`. Every unit test that reaches `run_category` over a fake
    Designer runs it on the real environment: in `test_selftest_preparations.py` only
    `test_the_clean_up_removes_the_self_test_graphs_snapshots` sets `SD_SNAPSHOT_DIR` (line 185); the tests of
    `test_selftest_alone.py` that run a category and `_isolated_run` in `test_selftest_summary.py` don't, and
    `conftest.py` has no fixture for it. On main only the real runs removed that folder.
  - **Scenario.** A live run on the default snapshot folder (a scratch run without `port=`, or the one run on
    Windows, beside which AGENTS.md says to run `pytest`) loses its graph's snapshots mid-run when those unit tests
    run: the checks of `layout`, `save`, `inputs` and `link_display` that read them fail for no reason of their own.
    The pool's workers have a folder of their own and aren't reached; no user's snapshot is either, as the folder is
    the self-test graph's.
  - **Fix.** An autouse fixture in `conftest.py` pointing `SD_SNAPSHOT_DIR` at a temp folder, and a test like
    `test_the_close_tests_never_remove_the_real_scratch_folder` (no `rmtree` outside the temp folder).
  - **Resolution: done.**
    - **Test:** `test_no_unit_test_cleans_up_the_real_snapshot_folder` (`tests/unit/test_selftest_preparations.py`):
      the clean-up of a category run over a fake removed `~/.sd_mcp/snapshots/mcp_selftest`.
    - **Cause:** no fixture pointed `SD_SNAPSHOT_DIR` away from the real folder.
    - **Fix:** `conftest.py`'s autouse fixture sets `SD_SNAPSHOT_DIR` to a temp folder of its own for every test.
    - **Also covered:** the tests that read `SD_SNAPSHOT_DIR` (`test_uninstall.py`, `test_lifecycle_env.py`,
      `test_selftest_workers.py`, `test_selftest_alone.py`, `test_snapshots.py`, `test_link_display.py`,
      `test_guide.py`) set or remove it themselves: all pass.
  - Questioned by TST-264 (2026-11-10).

- [x] **TST-231 · Three preparations leave a check with nothing to tell apart** · `tests/test_all_tools/facts/preparations.py:26-37`, `tests/test_all_tools/measure/preparations.py:18`, `tests/test_all_tools/graph_edit_wire/preparations.py:18-27` · confirmed · found 2026-11-10
  - **Defect.** The assertions are main's; the state they measure got simpler, so each passes whatever the code does:
    - facts, "a graph's model is the same after a save and a reload" (`facts/checks.py:243-256`): the prepared graph
      has no stored parameter, no graph input and no function graph, so the model's parameters and inputs are empty
      on both sides and no function digest (`_function_value`) goes through the round trip, which is what the check
      was added for. On main the graph had the input `floor` driving a parameter, and several parameters set. Only
      the bitmap's path is still compared.
    - measure, `sweep_param` "original restored" (`measure/checks.py:30-44`): clouds is added with no `scale`, and
      `describe_graph(include_params)` lists only what differs from the default, so a sweep that put the default
      back instead of the original passes. On main the original was 4. The sweep's `view_node`, the slope blur, is
      also connected to nothing now.
    - graph_edit_wire, "move: 4 moved" (`graph_edit_wire/checks.py:131-144`): the preparation adds the four nodes at
      exactly the positions the check moves them to, and `move_nodes` prints "moved" from the request, not from a
      read-back. On main the nodes were added without positions. (Two reviewers.)
  - **Scenario.** A regression in the function digest's stability through a save, in `sweep_param`'s restore, or in
    the `move` op passes the final check.
  - **Fix.** facts' preparation: a parameter set on the levels node and one `expose`. measure's: `'params':
    {'scale': 4}` on clouds and a `connect` into the slope blur. graph_edit_wire's: the nodes added without positions
    (nothing else in the category reads them), or `describe_graph`'s positions compared after the move.
  - **Resolution: done.**
    - **Test:** the three checks made to fail on a preparation with nothing to tell apart, in one scratch run on the
      preparations as they were (fresh Designer): facts' round trip now also requires a value, the input `floor` and
      a function reading it in the compared model (failed: "compared: False"); measure's "original restored" requires
      the original `scale = 4` (failed); graph_edit_wire's move reads the positions back with `describe_graph`
      (passed there, the nodes already where it moves them: the finding's point).
    - **Cause:** the preparations made the measured state simpler than the checks' main state.
    - **Fix:** facts' preparation sets `levelinhigh` on the levels node and exposes `leveloutlow` as `floor`;
      measure's sets clouds' `scale` to 4 and connects it into the slope blur; graph_edit_wire's adds its nodes where
      Designer places them. Scratch run, fresh Designer: the three pass.
    - **Also covered:** the other checks of the three categories in the same run: all pass but HLP-100's.

- [x] **TST-232 · The entry point's docstring, README and the live-check skill say false things about `--workers 1` and about Windows** · `tests/test_all_tools/__main__.py:4-10`, `README.md:194-195`, `.claude/skills/live-check/SKILL.md:105-106` · confirmed · found 2026-11-10
  - **Defect.** (a) `__main__.py`'s docstring: "`--workers 1` makes it one run, which never includes it" (the unit
    suite), its usage line offering `[--no-unit | --workers 1]` as alternatives. The code: `choose(1)` returns 1
    (`workers.py:91`, `return asked or 4`) and `main` calls `run_pool(slots, unit=not args.no_unit)`: a pool of one at
    a time, the unit suite beside it. README (line 192) and PLAN.md have it right. (b) The same docstring ("One run
    starts Designer if it isn't running ... and closes it again at the end"), README ("On Windows it is one run in one
    Designer ...: a Designer it started is closed again at the end") and the skill ("it starts Designer if none runs
    and closes it again; ... and the checks that quit Designer are skipped", which contradicts itself). One run
    happens only on Windows now, where `finish` skips the quit (`__main__.py:213-214`) and `one_run` ends no Designer
    (`sys.platform != 'win32'`, line 311). ROADMAP item 65 has it right.
  - **Scenario.** An agent asked for the live suite alone in one Designer reads the docstring, runs `--workers 1` and
    gets the unit suite too, over 10 minutes. A person on Windows expects Designer closed and finds it open with the
    scratch folder left, and the next run takes that Designer for theirs.
  - **Fix.** The docstring: `--workers 1` runs the categories one after the other, the unit suite still beside them;
    one run is off macOS only and leaves the Designer it started open on Windows. The same in README and the skill,
    or the Windows behaviour kept in ROADMAP item 65 alone, with links. (Three reviewers.)
  - **Resolution: done.** Docs only. `__main__.py`'s docstring: `[--no-unit] [--workers N]`, `--workers 1` runs the
    categories one after the other with the unit suite still beside them, one run is on Windows, where Designer is
    left open. README's Self-test and the live-check skill say the same of Windows.

- [x] **TST-233 · The live-check skill's account of what a scratch run shows is the old design's** · `.claude/skills/live-check/SKILL.md:50-53, 68-76, 79-80` · confirmed · found 2026-11-10
  - **Defect.** Three places.
    - Lines 50-53 (new): between a scratch run and the full run "only what other categories leave outside the
      self-test's graphs (the editor, the clipboard, Designer's settings) differs". Lines 79-80 (left as they were):
      for a check failing only in the suite, "build the state the earlier categories left into its environment". In
      the pool no category runs in another's Designer. What differs is which Designer is the active app (`undo`
      failed in 3 pool runs of 4 for that: `categories.py:61-64`), the load of the other Designers and the unit suite
      on the checks of a time, and a Designer just started (TST-229 is one).
    - Lines 68-76, "What a scratch run can't prove": it names "the user's graph back in the editor" and "in a
      Designer that was already running, that it still runs with no new crash dump", which no run on macOS reaches
      (the pool refuses with the user's Designer open; no run log kept has the first check), and tool coverage as
      `__main__.py`'s, now judged by the pool. It omits what only a real pool run shows: `workers.check_the_quits`,
      the `unit tests` check, the launch lock, `SOLO` and `CLIPBOARD`.
  - **Scenario.** An agent adds a check that depends on focus, on a time or on a Designer just started, sees it pass
    in a scratch run and calls it proven; when the final check fails, the skill sends it to rebuild state from
    categories that never ran in that Designer. An agent changing `check_the_quits` finds nothing saying a scratch run
    can't prove it.
  - **Fix.** Lines 50-53 and 79-80: name the active app, the load and a Designer just started; a check failing only
    in the full run is run beside other Designers (`port=`) or in a Designer just started. Lines 68-76: what the
    pool's parent checks, and that the two "your Designer" checks run only in one run in the user's Designer (Windows
    today).
  - **Resolution: done.** Docs only (the live-check skill): what differs in the full run (other Designers starting,
    quitting and working beside it, the unit suite, a Designer just started); a check failing only there runs beside
    other Designers (`port=`) or in a Designer just started; "What a scratch run can't prove" lists the run's start
    checks (in the first category started), what the pool's parent checks (`check_the_quits`, the coverage over all
    workers, `unit tests`, the lock, `CLIPBOARD`, `SOLO`), and the two checks only a run in the user's Designer has.
  - Questioned by TST-266 (2026-11-10).

- [x] **TST-234 · GUIDE.md's Undo recipe lacks what this branch measured: Undo needs its Designer to be the active app** · `mcp_server/GUIDE.md:83-86` · confirmed · found 2026-11-10
  - **Defect.** The branch measured that Undo of an output's fields did nothing 8 times in 8 with another Designer in
    front, and worked once the main window was raised and activated (PLAN.md, step 6;
    `tests/test_all_tools/common.py:214-218`). The guide's recipe for triggering Undo ("schedule them with
    `QTimer.singleShot(0, action.trigger)` ... and call `QApplication.processEvents()`") says nothing of it. The fact
    lives in PLAN.md, a comment and a unit test of the snippet's text
    (`test_undo_and_redo_make_their_designer_the_active_app_first`); no "designer facts" check measures it (AGENTS.md,
    Keeping the docs current).
  - **Scenario.** An agent follows the guide's recipe while another app or a second Designer is in front: Undo does
    nothing, with no error.
  - **Fix.** Measure how far it goes first (another kind of edit; an app in front that isn't Designer), then one
    clause in the Undo bullet (raise and activate the main window first) and a facts check.
  - **Resolution: done,** with what was measured changing the picture. Probes in Designers an agent started
    (ports 47311 and 47312, the user's front app put back after each): with Finder in front, Undo of an added node
    and of an output's fields worked without the raise, 2 of 2 each; with another Designer in front, in a reused
    Designer, 4 of 4 runs of `undo` without the raise passed; in a Designer just started, 1 of 3 failed ("one Undo
    puts an output's fields back"); with the raise, 4 of 4 passed. The raise leaves the other Designer in front
    (its process frontmost before and after), so "only while its Designer is the active app" wasn't what it needs.
    - **Fix:** GUIDE.md's Undo bullet: raise and activate the main window first; in a Designer just started, with
      another Designer in front, Undo of an output's fields sometimes did nothing without it, and it leaves the other
      app in front. The same reason, without "the active app", in `common.py`, `categories.py`, `workers.py`,
      `undo/checks.py`, the live-check skill, PLAN.md and the two unit tests' comments
      (`test_undo_and_redo_raise_and_activate_their_window_first`, renamed). `SOLO` stays.
    - **No "designer facts" check:** the failure without the raise came 1 time in 3, so a check of it would be flaky;
      the recipe itself is what `undo`'s checks run (`UNDO_REDO`), and they pass.
  - Questioned by TST-266 (2026-11-10).

- [x] **TST-255 · Two safety guards still read the old flat layout, so the categories' scripts and modules are outside them** · `tests/unit/test_selftest_safety.py:95-102, 236-252` · confirmed · found 2026-11-10
  - **Defect.** `test_no_script_loads_a_library_package` takes the scripts as `name.startswith('designer_scripts' +
    os.sep)`, and the dedent rule its modules as `os.sep not in name` (`_dedent_rule_sources`; also
    `test_the_dedent_rule_reads_every_module_of_both`, so that one can't notice). On main every script was in
    `designer_scripts/` and every category a module at the top; this branch moved them to
    `<category>/designer_scripts/` and `<category>/checks.py`, `preparations.py`. The script guard now reads the 4
    scripts of `designer_scripts/shared/` out of 53; the dedent rule leaves out the 63 files of the categories'
    packages. The branch rewrote the same file's grouping test for the new layout, not these filters.
  - **Scenario.** A category's script that loads a library package (the live-check skill forbids it: in the Windows
    one run it would load one into the user's Designer), or a category's snippet joined with `\n`, passes the unit
    suite. Probe (plain Python, the guards' own functions over the files they no longer read): no violation today, 0
    of 53 scripts, 0 of 63 modules.
  - **Fix.** The script guard takes every path with a `designer_scripts` folder in it, the dedent rule every module
    outside those folders, and the "every module" test requires each category's `checks.py`; each seen failing on a
    planted file first.
  - **Resolution: done.**
    - **Test:** `test_the_guards_read_the_scripts_of_every_category` (read 4 scripts of 53) and
      `test_the_dedent_rule_reads_every_module_of_both` (no category's `checks.py`) failed.
    - **Cause:** both filters were written for the layout before the categories became packages.
    - **Fix:** `_is_a_script` (`test_selftest_safety.py`) takes any path with a `designer_scripts` folder in it; the
      dedent rule reads everything else. A planted script loading a library package in a category's folder and a planted
      joined snippet in a category's module each failed their guard. Today's files break neither.
    - **Also covered:** `os.sep not in`, `startswith('designer_scripts'` and listings of the self-test's folder in
      `tests/unit`: the others list the categories' folders themselves.

- [x] **TST-267 · `set_link_display` is never run with its graph open in the editor, the state a user works in** · `tests/test_all_tools/link_display/preparations.py:12-53`, `tests/test_all_tools/link_display/checks.py:17`, `mcp_server/server_tools/layout.py:131-138` · measured · found 2026-11-11
  - **Defect.** The preparation creates and saves the graph and never opens it, and `create_graph` opens no view, so
    `package_file_of` prints `OPEN=0` (`files.py`: `'1' if _same_graph(current, g) else '0'`) and neither the views'
    tear-down nor `if info.get('OPEN') == '1': ... open_graph(graph_in_file(...))` is reached by any live check. The
    self-test's only reads of `OPEN` assert `OPEN=0` (`safeguards/checks.py`); the only `OPEN=1` is a fake, in
    `tests/unit/test_link_display.py`, of a reopen that fails. On main, earlier categories opened this graph; whether it was still the current one at this point wasn't measured.
  - **Scenario.** A regression in the reopen, in the pauses GUIDE.md's Portals bullet asks for ("back to back, Designer
    once crashed while tearing down the old views") or in `_same_graph`'s true case passes the final check. Probe (three
    Designers just started, port 47311): `link_display`'s preparation, `open_graph`, then the whole category: 15 of 15
    each time, the editor's graph `mcp_selftest` after each of the 12 calls, no "could not reopen", no crash dump. So the
    tool works in that state, and nothing checks it.
  - **Fix.** `open_graph` as the preparation's last call; in the check of the first portals, `'could not reopen' not in t`
    and the editor's graph read back as the self-test graph.
  - **Resolution: done.**
    - **Test:** a check in `link_display/checks.py`, "the graph open in the editor is back after the reload": on the
      preparation as it was, it failed in a scratch run ("in the editor: ''").
    - **Cause:** the preparation never opened the graph, so the views' tear-down and the reopen weren't reached.
    - **Fix:** the preparation opens the graph last. Scratch runs in three Designers just started: 16 of 16 each, no crash
      dump. With the reopen in `layout.py` removed, the check failed the same way.
  - Questioned by TST-271 (2026-11-11).

- [x] **TST-271 · TST-267's check overwrites the graph the run keeps to put back in the user's editor · follows TST-267, generation 2** · `tests/test_all_tools/link_display/checks.py:21`, `tests/test_all_tools/common.py:239-243, 245-255, 496-503`, `tests/test_all_tools/__main__.py:121, 134-136` · measured · found 2026-11-11
  - **Defect.** `editor_graph` isn't only a read: `CURRENT_GRAPH` does `sys._selftest_user_graph = g`, the object
    `SAME_GRAPH_BACK` reopens at the end of the run. The new check calls it (`back = await editor_graph(c)`), with
    `mcp_selftest` in the editor. Its failure message also says "at the start".
  - **Scenario.** One run on Windows, in the user's Designer: the start records their graph, `link_display` replaces the
    record with the self-test's, the clean-up unloads that package, and at the end "the self-test puts your graph back in
    the editor" reopens a graph that is gone. Probe (port 47311; a second graph as the user's): with a second read before
    the clean-up, `SAME_GRAPH_BACK` ended in a traceback, the user's graph not reopened; without it, as on main,
    `SAME=True current=probe_users_graph`. On macOS `user_graph` is `''`, so nothing runs.
  - **Fix.** A read of the identifier that stores nothing, for the check; a unit test that the check's call doesn't assign
    `_selftest_user_graph`.
  - **Resolution: done.**
    - **Test:** `test_only_the_runs_start_records_the_users_graph` (`tests/unit/test_selftest_summary.py`): `link_display`
      called `editor_graph`.
    - **Fix:** `common.graph_in_editor`, with `GRAPH_IN_EDITOR`, which keeps nothing; the check uses it. `link_display`
      in a scratch run: as above, 16 of 16 in that category.

- [x] **TST-272 · README's main self-test command fails after a plain install: it now runs the unit suite, which needs packages `install.py` doesn't install** · `README.md:199, 203, 207, 265`, `install.py:264`, `tests/test_all_tools/workers.py:145, 348` · confirmed · found 2026-11-11
  - **Defect.** "From the repository's folder, once `install.py` has made `mcp_server/venv`, ..." then
    `mcp_server/venv/bin/python tests/test_all_tools`, and "Run it after installing, after updates". `install.py` installs
    `requirements.txt` (mcp, pillow, numpy); `pytest` is in `requirements-dev.txt`, first mentioned at line 285. On macOS
    that command now also runs `[sys.executable, '-m', 'pytest', '-q']`.
  - **Scenario.** A user installs and runs the command README gives: every live check passes, `unit tests` fails with "No
    module named pytest", and the run exits 1. On main the same command ran only the live suite. The round-two note
    "README's commands work as written" holds only for a venv with the dev packages.
  - **Fix.** README: those rows need `pip install -r mcp_server/requirements-dev.txt`; a check after installing is
    `--no-unit`.
  - **Resolution: done.** Docs only: README says the rows that run the unit tests need `requirements-dev.txt`, and a
    check after installing without them is `--no-unit`.

- [x] **PLG-40 · The plugin's 30 ms wait isn't a floor: its 100 ms poll still starts jobs sooner, and a job queued behind another starts about 1 ms after it · follows PLG-38, generation 3** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:17-19, 320-324, 468-496`, `DECISIONS.md:157-162`, `PLAN.md:176-178`, `mcp_server/designer_helpers/describe.py:266-268`, `mcp_server/designer_helpers/save_export.py:84-85`, `tests/test_all_tools/bridge/checks.py:214-246` · measured · found 2026-11-11
  - **Defect.** Two timers start jobs and don't know of each other: `self.timer.timeout.connect(self._drain)` every 100
    ms, and the waker's single-shot `delay`. `_drain` takes whatever is queued. A job reaching an idle bridge starts at
    whichever fires first; a job queued behind another gets no wake and starts at the overdue poll as the other ends. The
    plugin's docstring ("after a 30 ms wait"), the decision ("rather than starting it at once or at the next poll"), PLAN.md
    and the helpers ("it now waits first") say more. `bridge`'s check bounds the median of 20 calls only, and its second
    check ("a job the wake starts") may be started by the poll. The decision also says "the wait keeps most of that",
    meaning most of the 85 ms saved.
  - **Scenario.** Probe on plugin v6, two Designers just started: 100 short jobs one after the other, 3 and 10 started
    before 28 ms (the fastest 1.6 ms), the median 33 ms; a job sent 50 ms into one of 0.3 s started 0.8 to 1.7 ms after it
    ended, 10 times in 10. Measured harmless where PLG-38 saw harm: one compute of a node queued 150 ms into the measure
    of the node feeding it gave its texture 10 times in 10. So the tools' results stand, the retries behind them; what a
    claim promises doesn't, for jobs after a short one and for parallel calls (an agent's tool calls in one turn run at
    once).
  - **Fix.** Make the wait a floor: `_drain` notes when a job ends and, called sooner than `WAKE_DELAY_MS` after it,
    starts `delay` for the rest and returns; the poll, a stale wake and a queued job then all wait. A unit test of that
    rule; `bridge`'s check bounding the fastest call too (Qt's coarse timers may fire a little early: a bound just under
    the wait). Or narrow the claims to "up to 30 ms". The decision's wording is the user's.
  - **Resolution: done.**
    - **Test:** `test_no_job_starts_sooner_than_the_wait_after_the_one_before` (`tests/unit/test_plugin.py`): "started
      within the wait"; `bridge`'s check now measures, by Designer's clock, the time between the starts of 20 jobs and
      between a job of 0.3 s and one queued behind it: on plugin v6 it failed twice in 2 (fastest 2.1 and 5.6 ms; behind
      7.7 and 12.4 ms).
    - **Cause:** two timers start jobs, and only the wake's waited.
    - **Fix:** plugin v7: `_drain` notes when each job ends and, called sooner than `WAKE_DELAY_MS` after it, whoever
      called it, starts the waker's timer for the rest (`_Waker.later`) and returns; the wake's own 30 ms wait stays
      (`_Waker._wait`), so the decision's words hold. A stale wake's drain checks the same, which covers the review log's
      **Not verified** case. `install.py` run. After it, in three Designers just started: `bridge` and the two `measure`
      checks of HLP-100 and HLP-101, 43 of 43 each time (fastest 30.7 ms between starts, 30.8 ms behind a long job).
    - **Also:** the plugin's docstrings, PLAN.md, README's `v7`; two unit tests that drained twice in a row now wait it
      out. The decision's wording ("the wait keeps most of that") is the user's to change.
  - Questioned by PLG-41 and PLG-42 (2026-11-11).

## Low

- [x] **PLG-34 · A job can be queued while its client is told "bad request": the accept thread starts before the waker exists** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:307-310, 443-445` · confirmed · found 2026-11-10
  - **Defect.** `_Server.__init__` starts the accept thread (`self.thread.start()`) and only then sets `self.waker =
    _Waker(self._drain)`. `_authorised` puts the job in the queue and then calls `self.waker.wake.emit()`. An emit
    that raises (no `waker` yet) is caught by `_handle`'s `except Exception: reply = _fail('bad request')`, the job
    already queued: the timer runs it at its next tick.
  - **Scenario.** A `run` request served between those two statements as Designer starts: the client is told "bad
    request" while its script runs, and an agent that retries applies the edit twice. The window is two adjacent
    statements on the main thread, so it is very unlikely; the order is wrong all the same.
  - **Fix.** Create the waker and the timer before starting the accept thread; a unit test that the thread starts
    last.
  - Note (2026-11-10): decided by the user, fixed on this branch together with PLG-35 and PLG-36: one `install.py`
    run and one restart of a Designer an agent started for the three; the user's Designer loads the new plugin when
    they next open it.
  - **Resolution: done.**
    - **Test:** `test_the_accept_thread_starts_once_the_waker_and_the_timer_exist` (`tests/unit/test_plugin.py`): the
      thread started with neither (`[(False, False)]`).
    - **Cause:** `_Server.__init__` started the accept thread before making the waker and the timer.
    - **Fix:** the thread starts last.
    - **Also covered:** with PLG-35 and PLG-36, one `install.py` run and a restart of the Designer an agent started
      (port 47311; the user's Designer loads it when they next open it): bridge's checks in a scratch run, 37 of 37,
      the wake's included.

- [x] **PLG-35 · `_drain`'s comment on what stops a job starting inside another describes the plugin before the wake** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:455-459` · confirmed · found 2026-11-10
  - **Defect.** "Qt doesn't fire this timer again while its own slot runs, even when the script processes events ...,
    so this only guards against any other caller of _drain". A job reaching an idle bridge now runs inside
    `_Waker._on_wake`, not the timer's slot: Qt does fire the timer while such a script processes events, and a wake
    can arrive inside a job the timer started. `self.draining` is what stops both now. The tests cover it
    (`test_a_job_never_starts_inside_the_running_one`; the live check "a queued job waits for the running one", whose
    pumping job the wake starts).
  - **Scenario.** A maintainer trusting the comment weakens the flag; a queued job then starts inside a running one.
  - **Fix.** Reword it: both callers, and the flag is what stops a job starting inside another.
  - Note (2026-11-10): decided by the user, fixed on this branch with PLG-34 (its note).
  - **Resolution: done.** The comment names both callers, the timer and the wake, and says the flag is what stops a job
    starting inside another (`test_a_job_never_starts_inside_the_running_one`).

- [x] **PLG-36 · The server and its waker hold each other, so a stopped server is freed only by a later garbage collection** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:279-282, 310` · confirmed · found 2026-11-10
  - **Defect.** `self.waker = _Waker(self._drain)` and, in `_Waker.__init__`, `self.drain = drain`: the server holds
    the waker and the waker a bound method of the server. `stop()` only disconnects the signal, so after
    `uninitializeSDPlugin` sets `_server = None` the `_Server`, its `QTimer` and the `_Waker` live on until Python's
    cyclic collector runs, at a time and on a thread of its choosing. Whether that has done harm wasn't measured.
  - **Scenario.** The plugin unloaded or reloaded in Designer's plugin manager: the old Qt objects are destroyed
    later, perhaps off the main thread.
  - **Fix.** In `stop()`, drop the waker's hold (`self.waker.drain = lambda: None`), or have `_Waker` hold the server
    weakly; a unit test that a stopped server is freed without a collection.
  - Note (2026-11-10): decided by the user, fixed on this branch with PLG-34 (its note).
  - **Resolution: done.**
    - **Test:** `test_a_stopped_server_is_freed_without_a_garbage_collection` (collector off: the server lived on),
      and `test_stop_disconnects_the_wake`, now also asserting the timer's slot is gone (it was kept).
    - **Cause:** the waker held the server's `_drain`, and the timer's connection did too, past `stop()`.
    - **Fix:** `_Waker` holds `drain` weakly (`weakref.WeakMethod`; a wake after the server is gone does nothing), and
      `stop()` disconnects the timer as it does the wake.
    - **Also covered:** the timer, the same pattern; no other object the server holds keeps a reference to it.
  - Questioned by PLG-37 (2026-11-10).
  - Questioned by PLG-39 (2026-11-11).

- [x] **TST-235 · The pool never ends if `lifecycle`'s worker dies while it holds the launch lock** · `tests/test_all_tools/launch_lock.py:84-87, 104-109`, `tests/test_all_tools/workers.py:174-190` · confirmed · found 2026-11-10
  - **Defect.** The lock file is removed only by its holder's `finally` (`held`). `changing()` waits for it with no
    deadline (`while True: ... if not os.path.exists(lock): break`), and `schedule` retries `gate.try_begin` for ever
    and clears only start marks.
  - **Scenario.** `lifecycle`'s worker is killed inside one of its two windows (a SIGKILL, a crash of its Python):
    `launch.lock` stays. Every worker reaching its end waits in `changing()`, no pending category starts, and
    `schedule` never returns: no summary, Designers left open, until whoever runs it gives up. A worker killed inside
    `changing()` leaves its mark the same way, which costs `lifecycle`'s next `held()` its 300 s. No run has seen
    either.
  - **Fix.** When a worker ends, `schedule` ends its mark whatever its state, and removes the lock if that worker
    held it (the holder's name written into the lock file); `changing()` gets a deadline, as `held()` has.
  - **Resolution: done.**
    - **Test:** `test_the_pool_goes_on_when_a_worker_dies_holding_the_lock` (`tests/unit/test_selftest_pool.py`):
      "never ends"; `test_the_lock_names_its_holder`, `test_a_worker_ended_leaves_no_mark_and_no_lock_of_its_own`,
      `test_a_quit_waits_for_the_lock_no_longer_than_its_timeout`: failed (no name, no method, no deadline).
    - **Cause:** only the holder's `finally` removed the lock and its marks, and `changing()` had no deadline.
    - **Fix:** `held()` writes its holder's name in the lock; `schedule` calls `Gate.worker_ended(name)` as each
      worker ends, whatever ended it, removing its mark and the lock if it held it; `changing()` waits 300 s at most,
      as `held()` does, then quits all the same and says so.
    - **Also covered:** a worker killed inside `changing()` leaves no mark either (the same call).

- [x] **TST-236 · A crash dump can be reported under the wrong check** · `tests/test_all_tools/workers.py:243-259`, `tests/test_all_tools/lifecycle/checks.py:524-597`, `tests/test_all_tools/common.py:337-339` · confirmed · found 2026-11-10
  - **Defect.** Two places. `check_the_quits` collects the new dumps of every port, `lifecycle`'s included
    (`crash_dumps(sorted(port_of.values()))`), but skips `lifecycle` and any worker without results before filling
    `placed` (`if name == LIFECYCLE or part is None: continue`): their dumps fail "no new crash dump outside the run",
    and `lifecycle`'s own watch has failed a check for the same dump already. In `lifecycle`, the three forced quits
    after "stuck in its shutdown" (a busy Designer, a frozen one, one not answering) have no `watch.step()`, and
    `CrashWatch.settle` gives a dump to the latest step started before it (`self.steps[max(started or looking)]`):
    one written in those phases fails "forces one stuck in its shutdown, without a crash".
  - **Scenario.** A Designer of `lifecycle`'s crashes: the summary shows two failures for one dump, one saying it is
    outside the run; or the failure names a quit that didn't crash, and whoever reads it looks in the wrong place.
  - **Fix.** `check_the_quits`: place the dumps by folder for every name in `port_of`, leaving out only the quit
    check for `lifecycle` and for a worker without results. `lifecycle`: a `watch.step()` with a held check for each
    of those quits. (Two reviewers found the first.)
  - **Resolution: done.**
    - **Test:** `test_a_dump_in_a_workers_folder_is_never_one_outside_the_run` (lifecycle's folder, and a worker
      without results): both failed "no new crash dump outside the run"; `test_every_quit_lifecycle_makes_is_a_watched_step`
      (`tests/unit/test_selftest_lifecycle.py`) found the three quits with no step.
    - **Cause:** `check_the_quits` skipped those workers before placing their dumps; the three quits had no
      `watch.step()`.
    - **Fix:** every worker's dumps are placed by folder; lifecycle's are left to its own watch, a worker without
      results gets a check naming them. The two forced quits and the launch ending a Designer not answering each
      start a step, their checks held (`watch.check`). `lifecycle` whole in a scratch run: 39 of 39.
  - Questioned by TST-257 (2026-11-10).

- [x] **TST-237 · Code for one run in a Designer the self-test started is unreachable on macOS and Windows, yet tested and described as live** · `tests/test_all_tools/__main__.py:113, 137, 209-223` · confirmed · found 2026-11-10
  - **Defect.** On macOS `main` always takes the pool or refuses, so `finish(worker=None)` runs only on Windows,
    where its first branch returns: its `elif was_running:` and its `else:` (the run ends with `lifecycle`) are
    reached on neither. `dumps_at_start` is computed (line 113), passed (137) and never read by `finish`.
    `test_one_run_ends_with_lifecycle_as_before` (`tests/unit/test_selftest_workers.py:126`) sets `sys.platform` to
    `'darwin'` with `worker=None`, which `main` can't produce; its module's docstring says "one run (off macOS) ending
    with lifecycle", `categories.py` (line 6) "one run ends with it", `test_selftest_summary.py` (line 293)
    "lifecycle: from the finally, own Designer only".
  - **Scenario.** A reader takes it that one run still ends with `lifecycle` somewhere, and that a worker compares
    crash dumps from its start; a change to those branches is "tested" by a test of a state that can't happen.
  - **Fix.** Remove the branches, the parameter and the test, or keep them marked as waiting for ROADMAP item 65;
    correct the three sentences.
  - Note (2026-11-10): decided by the user: removed (the `elif was_running:` and `else:` of `finish`, `dumps_at_start`,
    `test_one_run_ends_with_lifecycle_as_before`), the three sentences corrected; git keeps them if ROADMAP item 65
    needs them back. A refactor of unreachable code: the existing tests of `__main__.py` run before and after.
  - **Resolution: done.** As decided: `finish`'s `elif was_running:` and `else:` removed, with `dumps_at_start` and
    `test_one_run_ends_with_lifecycle_as_before`; its docstring says one run is Windows only; the sentences in
    `test_selftest_workers.py`, `categories.py` and `test_selftest_summary.py` corrected. A refactor: `__main__.py`'s
    tests (`test_selftest_workers.py`, `test_selftest_summary.py`, `test_selftest_pool.py`) pass before and after.
  - Questioned by TST-262 (2026-11-10).

- [x] **TST-238 · New behaviour with no unit test** · `tests/test_all_tools/workers.py:145-151, 258-259, 348-362`, `tests/test_all_tools/__main__.py:280-281`, `tests/test_all_tools/category_run.py:113-121`, `tests/test_all_tools/alone.py:177-180`, `tests/test_all_tools/common.py:479` · confirmed · found 2026-11-10
  - **Defect.** No test in `tests/unit` reaches: `_clean_up` keeping the folders when a Designer is still recorded on
    a chosen port, or when the listing raises (the pool's tests always give `agents_designers` none); the check "no
    new crash dump outside the run"; `workers.answering`; the refusal of `--workers` below 1; a clean-up that fails
    (`_cleaned` returning False, and `alone`'s exit code 2 for it: the only assertion is `ran.prepared and
    ran.cleaned` where all passes); `common.script_path` (`test_designer_scripts._run` builds the path itself).
  - **Scenario.** The first is the rule that a folder isn't deleted under a running Designer: `set(chosen) - left`
    turned round passes every test. So does `_cleaned` always returning True, or `alone` ignoring `ran.cleaned`.
  - **Fix.** One pool test with `agents_designers` returning a chosen port (the folders kept, the line printed), one
    with a dump in the shared folder, one for `--workers 0`; a fake Designer whose clean-up fails, asserting `cleaned
    is False` and exit code 2; `_run` calling `common.script_path`.
  - **Resolution: done.** Tests of code that already worked, each seen failing with the code it guards broken in a
    temporary copy: `test_the_folders_are_kept_while_a_designer_of_the_run_may_run` (one still recorded, the listing
    failing; failed with `set(chosen) - left` turned round), `test_a_new_dump_outside_the_workers_folders_fails_a_check_of_its_own`
    (failed with that check removed), `test_a_port_answers_once_something_listens_on_it`,
    `test_workers_below_one_are_refused_before_anything_starts` (failed without the refusal),
    `test_a_category_whose_clean_up_fails_says_so` and `test_a_clean_up_that_fails_is_exit_code_2_though_every_check_passed`
    (failed with `_cleaned` always True, and with `alone` ignoring `ran.cleaned`); `test_designer_scripts._run` takes
    the path from `common.script_path`.

- [x] **TST-239 · Three unit tests can't fail for what their names say** · `tests/unit/test_selftest_pool.py:381-405`, `tests/unit/test_selftest_preparations.py:212-222`, `tests/unit/test_selftest_categories.py:33-43` · confirmed · found 2026-11-10
  - **Defect.**
    - `test_a_worker_closes_its_designer_when_no_lock_holds_and_leaves_the_crash_dumps_to_the_pool`: the fake
      `Changing` records in `order`, the fake Designer in `c.calls`, and the assertion compares them apart
      (`c.calls == ['quit_designer'] and order == ['wait for the lock: render', 'done']`). `quit_designer` moved
      before or after the `with launch_lock.changing(worker):` block still passes, so what decision 11 needs is
      unguarded.
    - `test_no_category_uses_another_categorys_code` looks for `test_all_tools.<name>` and `from ..<name>`. `from
      test_all_tools import params` and `from .. import params` have neither, and the first is the form the code
      uses (`bridge/checks.py:20`).
    - `test_no_category_requires_another` and `test_no_shards_each_category_runs_in_a_designer_of_its_own` assert
      only that removed names are absent (`not hasattr(categories, 'REQUIRES')` ...): they fail only if someone adds
      those exact names again.
  - **Scenario.** A quit outside the lock, or a category importing another's code, passes the unit suite.
  - **Fix.** The fake Designer appends to `order`: `['wait for the lock: render', 'quit_designer', 'done']`. The
    names after `from test_all_tools import` and `from .. import` parsed too (or `ast`), a planted import seen
    reported. The last two deleted: `test_selftest_preparations.py` and the pool's tests check those rules.
  - **Resolution: done.** The quit test keeps one record, so it requires `['wait for the lock: render',
    'quit_designer', 'done']`. The import test parses imports (`ast`): `test_every_form_of_import_of_another_category_is_seen`
    plants five forms, of which the old scan missed `from test_all_tools import params` and `from .. import params`.
    `test_no_category_requires_another` and `test_no_shards_each_category_runs_in_a_designer_of_its_own` removed.

- [x] **TST-240 · `test_selftest_alone.py` kept two things from the old `alone`** · `tests/unit/test_selftest_alone.py:28, 451, 454` · confirmed · found 2026-11-10
  - **Defect.** Line 28 sets `vars(alone)['PAUSE_S'] = 0`, but `PAUSE_S` moved to `category_run.py` (line 29, slept
    in `_cleaned`): every alone test that runs a category sleeps 0.5 s. Lines 451 and 454 call `alone.run_with(c, [],
    (), None, 'scratch', port=9901)`, the old signature (checks, needs, setup, scratch): it now binds `setup=()`,
    `scratch=None`, `s='scratch'`, and passes only because there are no checks.
  - **Scenario.** Some seconds of sleeping in the unit suite; with one check, that call would call a tuple.
  - **Fix.** `PAUSE_S` zeroed on `test_all_tools.category_run` in `_alone()`; `run_with(c, [], None, 'scratch',
    port=9901)`.
  - **Resolution: done.** `_alone()` zeroes `PAUSE_S` on `category_run`, where it is slept (the file's tests: 0.65 s);
    the two calls take `run_with`'s signature, `(c, [], None, 'scratch', port=9901)`.

- [x] **TST-241 · `CLIPBOARD` keeps `editor_open_and_zoom` apart from the categories that use the clipboard, though it never touches it** · `tests/test_all_tools/categories.py:58-60` · confirmed · found 2026-11-10
  - **Defect.** "never two at once in a pool (workers.py): they use the machine's one clipboard" over
    `frozenset({'facts', 'editor_open_and_zoom', 'editor_panels_and_fit'})`. `editor_open_and_zoom` calls only
    `screenshot_designer('graph')` (a widget grab), `open_graph` and three scripts. The clipboard is used by the 3D
    capture (`facts/checks.py:409`, `editor_panels_and_fit/checks.py:31`) and by `empty_clipboard.py`. `workers.py`
    (line 10) and PLAN.md (line 243) repeat it.
  - **Scenario.** The pool holds a category back for a reason the code doesn't have, and three places state it.
  - **Fix.** Take it out of the set (a full run shows whether it then disturbs anything), or state the real reason if
    there is one. (Two reviewers.)
  - **Resolution: done.**
    - **Test:** `test_the_clipboard_group_is_the_categories_that_use_the_clipboard`
      (`tests/unit/test_selftest_categories.py`) finds the categories whose code takes a 3D screenshot, reads Qt's
      clipboard or uses the self-test's clipboard helpers, and requires `CLIPBOARD` to be exactly those. It failed
      before the change (`editor_open_and_zoom` in the group, using none). It replaces the assertion in
      `test_selftest_pool.py` that only repeated the set. Whether the category does harm beside the others, its wheel
      steps and fits being the likeliest to suffer when another Designer takes the front: scratch runs side by side,
      each category in a Designer started for it and closed after it, as in the pool, `editor_open_and_zoom` on one
      port beside `facts` on another three times and beside `editor_panels_and_fit` three times (the pool never runs
      those two together). All six passed, its 16 checks each time.
    - **Cause:** the group listed both `editor_` categories; only `editor_panels_and_fit` takes a 3D screenshot.
    - **Fix:** `CLIPBOARD` is `facts` and `editor_panels_and_fit`; its comment says why and points at the test.
    - **Also covered:** the same sentence in `workers.py`'s docstring, PLAN.md (step 6) and the live-check skill,
      all corrected. The full run, with the pool's own scheduling, is the final check's.

- [x] **TST-242 · The compute-floor check says "a 3-node 4x4 graph"; its graph is 1024 × 1024** · `tests/test_all_tools/facts/designer_scripts/compute_floor.py:33`, `tests/test_all_tools/facts/checks.py:68-81`, `mcp_server/GUIDE.md:218-219` · measured · found 2026-11-10
  - **Defect.** The script sets `$outputsize` to (2, 2) without making it absolute
    (`g.setInputPropertyValueFromId('$outputsize', SDValueInt2.sNew(int2(2, 2)))`), on a new graph, whose size is
    relative to its parent. The check's name and the guide ("measured: a 3-node 4×4 graph and a 63-node one") call it
    4×4. The check also asserts less than it says: its name is "takes a fixed time" and its docstring "a larger
    graph, unchanged, no less", the comparison only a floor (`min(...) > 0.5`).
  - **Scenario.** Probe (the script's graph, in a Designer just started): inheritance `RelativeToParent`, the
    computed texture 1024 x 1024, three computes 0.92, 0.91, 0.91 s. The fact itself holds: graphs made absolute at
    4 × 4, 32 × 32 and 1024 × 1024 took 0.91 to 0.94 s for each of three computes, Designer being the active app. So
    the guide's advice stands, and its "4×4" isn't what the check measures.
  - **Fix.** Set the inheritance to Absolute before the value (as `create_graph` and `other_kinds()` in
    `function_states.py` do), print the texture's size in the `SMALL` line and assert it; name the check for what it
    asserts, a floor. `states()` and `fx_map()` in `function_states.py` set (4, 4) the same way, as on main.
  - **Resolution: done.** `compute_floor.py` makes the graph's size absolute before setting it and prints the computed
    texture's size, which the check requires (`SMALL 4x4`); the check's name and docstring say what it asserts, a
    floor over 0.5 s. Scratch run: `SMALL 4x4 0.93 0.92 0.91 / LARGER 63 nodes, unchanged 0.91`. GUIDE.md's "4×4" is
    now what is measured. `states()` and `fx_map()` in `function_states.py` set (4, 4) relative as on main, and claim
    no size: unchanged.

- [x] **TST-243 · Sentences in docstrings and comments left from the old design, or saying more than the code** · `tests/test_all_tools/categories.py:3`, `tests/test_all_tools/bridge/checks.py:214-218`, `tests/test_all_tools/graph_edit_output_fields/checks.py:11, 200`, `tests/test_all_tools/facts/checks.py:85` · confirmed · found 2026-11-10
  - **Defect.**
    - `categories.py:3` "the one list the index (__main__.py) and alone.py read", and the same in
      `tests/unit/test_selftest_categories.py` (lines 1-2, 18): `alone.py` imports only `common` and `category_run`;
      the readers are `__main__.py` and `workers.py`.
    - `bridge/checks.py:214-218`: "A job queued behind a running one still waits for the poll (the queue checks in
      run())". Those checks assert only that the second job starts after the first ends; what shows no wake for a
      queued job is the unit test `test_a_job_queued_behind_another_waits_for_the_timer`.
    - `graph_edit_output_fields/checks.py:11` "every other check counts this one's outputs" and line 200 "doesn't
      count in later checks of unsaved packages": no other category shares its Designer now.
    - `facts/checks.py:85`: the old path `designer_scripts/facts/function_states.py`.
  - **Scenario.** A reader follows a sentence to code that isn't there.
  - **Fix.** Correct each.
  - **Resolution: done.** Docs only: each sentence corrected (`categories.py` and its test: the index and the pool read
    the list; `bridge/checks.py` points at the plugin's unit test for a queued job; graph_edit_output_fields' two
    sentences about other checks gone; `facts/designer_scripts/function_states.py`).

- [x] **TST-244 · "Keep each file to its main logic" in the files this branch touched** · `tests/test_all_tools/common.py:293-358, 549-560`, `tests/unit/test_selftest_pool.py:36, 371`, `tests/unit/test_selftest_workers.py:18, 116`, `tests/unit/test_selftest_summary.py:94-96` · confirmed · found 2026-11-10
  - **Defect.** `common.py`, "what every category shares", holds `CrashWatch`, `_WatchedStep` and
    `watching_crashes`, about 80 lines only `lifecycle/checks.py` uses. `_fresh` and `_Designer` are copied in
    `test_selftest_pool.py` and `test_selftest_workers.py`, and the pool's fakes sit inside the 695-line test file.
    `_isolated_run` replaces `PAUSE_S` and `preparation` with `vars(run)[...] = ...`, not `monkeypatch.setitem`, so
    nothing puts them back; it does no harm only because every self-test test file imports the package afresh.
  - **Scenario.** The rule AGENTS.md gained on this branch isn't followed by the branch's own files.
  - **Fix.** A `crash_watch.py` beside `common.py` (it has a test file of its own already); the shared fakes in a
    module beside the tests; `monkeypatch.setitem(vars(run), ...)`.
  - **Resolution: done.** Moves, the existing tests passing before and after: `CrashWatch`, `_WatchedStep` and
    `watching_crashes` in `tests/test_all_tools/crash_watch.py` (it looks `common` up when called, so tests still
    replace `common.check`); the pool's shared fakes in `tests/unit/selftest_fakes.py`, used by both pool test files
    (the `_Designer` left in `test_selftest_workers.py` was unused since TST-237); `_isolated_run` patches through
    `monkeypatch.setitem`.
  - Questioned by TST-261 (2026-11-10).

- [x] **TST-245 · README, ROADMAP item 42 and the live-check skill's description still describe the old run** · `README.md:204-217, 239`, `ROADMAP.md:67`, `.claude/skills/live-check/SKILL.md:3` · confirmed · found 2026-11-10
  - **Defect.** README's Self-test section: "removes the graph and reopens the graph you had open", the scratch
    folder "deleted at the end, except when Designer stays open", "(`quit_designer` when your own Designer is
    running)". On macOS the run refuses with the user's Designer open, so none of it happens there, and on Windows
    `quit_designer` is skipped always. Line 239 still gives `pytest` as "all of them, before merging", with no word
    that `tests/test_all_tools` runs it on macOS. ROADMAP item 42: "A run against an open Designer leaves its
    `sd_mcp_selftest_...` folder behind". The skill's description, the text every session's list of skills shows:
    "Covers alone.run and its needs", a parameter that is gone.
  - **Scenario.** A person following both README sections runs the unit suite twice; an agent looks for `needs=`.
  - **Fix.** Scope those sentences to Windows, where the run is in the user's Designer; point line 239 at the
    Self-test section; "Covers alone.run, each category's own preparation, ...".
  - **Resolution: done.** Docs only: README's Self-test (the graph reopened and the folder left: in your Designer, on
    Windows; `quit_designer` skipped on Windows; the `pytest` line points at the Self-test section), ROADMAP item 42
    (a run on Windows leaves its folder), the skill's description (each category's own preparation).

- [x] **TST-246 · The guide's new qualifier on the harmless log messages is checked in one direction only** · `mcp_server/GUIDE.md:108-109`, `tests/test_all_tools/facts/checks.py:376-404` · confirmed · found 2026-11-10
  - **Defect.** The guide now says "No output node defined" is logged "in a graph with an output node". The check
    counts both messages before and after one exposure in facts' graph, which has an output node, and asserts both
    rise. That none is logged without an output node is only in a comment ("measured 2026-11-10: none without one").
  - **Scenario.** A Designer update that logs it in every graph leaves the sentence wrong and the check passing.
  - **Fix.** The smaller claim in the guide (it may also log "No output node defined"), or a second exposure in a
    graph with no output node, asserting that count stays.
  - **Resolution: done,** by narrowing the claim: GUIDE.md says exposing an input may also log "No output node
    defined", and the check's comment no longer claims none without an output node. The check unchanged: both
    counts rise in facts' graph (passed in the scratch run).

- [x] **TST-247 · PLAN.md gives 7 computes and 30 checks for `function_states`; the code has 9 and 29** · `PLAN.md:23, 168` · confirmed · found 2026-11-10
  - **Defect.** "7 computes instead of 54" and "7 computes, the 30 checks unchanged". The script computes 9 times
    (`tests/test_all_tools/facts/designer_scripts/function_states.py`: lines 131, 142 and 146 in `states()`; 278, 283
    and 303 in `other_kinds()`; three `grey_of` in `fx_map()`), and `check_function_graph_states` records 29 checks
    (4 + 1 + 1 + 22 + 1).
  - **Scenario.** A reader checking the plan's saving against the code finds neither figure.
  - **Fix.** "9 computes" and "the 29 checks". (Two reviewers.)
  - **Resolution: done.** Docs only: PLAN.md says 9 computes and 29 checks, in both places.

- [x] **TST-248 · DECISIONS.md's reason for running the full suites only when the user asks is out of date** · `DECISIONS.md:23-43` · confirmed · found 2026-11-10
  - **Defect.** The entry "The full suites run only when the user asks" gives as its reason that they "took about 12
    minutes (PLAN.md, measured)", and says a check proven in a scratch run "can still pass or fail in the suite
    because of state earlier categories left". This branch measured both suites in 3.4 minutes with four at once
    (10.5 one at a time: PLAN.md, README), and no category sees another's state; what differs from a scratch run is
    which Designer is the active app, the load of the others and a Designer just started (TST-233).
  - **Scenario.** A reader weighs the rule on figures and a cause that no longer hold.
  - **Fix.** Decided by the user (2026-11-10): the rule stays as it is; only its reason is updated, to the times
    measured now and what can differ between a scratch run and the full run. Its "Reopen if" and what it decides are
    left unchanged. Docs only: the doc tests, with lint and types.
  - **Resolution: done,** as decided: the reason gives the 12 minutes as when this was decided and the 3.5 (10.5 one
    at a time) measured now, and what can differ in the full run (other Designers beside it, the unit suite, a
    Designer just started) instead of state left by earlier categories. What it decides and its "Reopen if"
    unchanged. Docs only: the doc tests.

- [x] **HLP-98 · A write-back that fails leaves the user's clipboard empty, and nothing says so · follows HLP-96, generation 2** · `mcp_server/designer_helpers/pasteboard.py:100-136`, `mcp_server/designer_helpers/screenshots.py:91-96`, `tests/test_all_tools/editor_panels_and_fit/checks.py` (the three `finally: put(users)`) · confirmed · found 2026-11-10
  - **Defect.** `pasteboard_write` calls `clearContents` first and raises only after `writeObjects:` returns NO, so a
    failed write leaves the clipboard empty, the saved copy only in memory; in `_save_3d_render` that `RuntimeError`
    then replaces the tool's result, the render saved, with no word that the clipboard was lost. In the self-test,
    `put(users)` is a subprocess with a 30 s timeout: if it fails, the user's clipboard is gone with the process. An
    item whose types are all unreadable doesn't cause it (measured: it is dropped, the rest written); what makes
    `writeObjects:` return NO wasn't found.
  - **Scenario.** A write-back that fails: the user's clipboard is empty, and the agent's error doesn't say so.
  - **Fix.** The error names the loss ("your clipboard could not be put back"); in the self-test, a restore that
    fails writes the saved clipboard to a file and prints its path. A unit test of the failing write with
    `writeObjects:` replaced.
  - **Resolution: done:** the native write-back it is about was removed at the user's choice (HLP-96's resolution).

- [x] **HLP-99 · A clipboard type whose name has no UTF-8 form would crash Designer** · `mcp_server/designer_helpers/pasteboard.py:89` · confirmed · found 2026-11-10
  - **Defect.** `name = ctypes.string_at(_pb_send(kind, 'UTF8String')).decode('utf-8')`: `UTF8String` can return
    NULL, `_pb_send` makes it 0, and `ctypes.string_at(0)` reads address 0, which crashes the process: here the
    user's Designer.
  - **Scenario.** A type name that can't be encoded (an unpaired surrogate) is unlikely, but the cost is Designer's
    unsaved work.
  - **Fix.** Skip a type whose name comes back as 0; a unit test with `_pb_send` returning 0 for `UTF8String`.
  - **Resolution: done:** `pasteboard.py`, where the call was, was removed at the user's choice (HLP-96's resolution).

- [x] **TST-249 · README's "puts your clipboard back as it was" says more than the code does · follows HLP-96, generation 2** · `README.md:307` · confirmed · found 2026-11-10
  - **Defect.** The write-back is a new clipboard holding the same data: its change count moves on (a password
    manager's "clear after N seconds", which watches it, may leave the password there), clipboard history apps see
    the render and the restored item, data an app provided on request comes back as plain data, and types that
    couldn't be read are left out (`pasteboard_read`'s docstring).
  - **Scenario.** A user who copied a password expects the password manager to clear it; it may not.
  - **Fix.** "puts back what your clipboard held (its data; a password manager may then not clear it, and anything
    copied during the capture is lost)", or measure each case first.
  - **Resolution: done:** README now says the capture puts back the clipboard's text and anything else may be lost
    (Security), and that the self-test's clipboard checks put back only the user's text.

- [x] **TST-250 · The guide's line on Qt's clipboard says "no RTF", but Qt converts RTF to HTML; the facts check's fixtures don't show it** · `mcp_server/GUIDE.md:326-329`, `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_qt_sees_only_the_formats_it_converts`), `tests/test_all_tools/editor_panels_and_fit/clipboards.py:16-28` · measured · found 2026-11-10
  - **Defect.** The check's "rich text" already carries `public.html`, so the `text/html` it sees is the HTML it
    was given, and its "image" is 16 bytes of a PNG header and 8 of a TIFF one, which no decoder can read.
  - **Scenario.** Probe: RTF alone is listed by Qt as `text/html`, 505 bytes (converted; the RTF itself not
    listed); RTF and plain text as `text/html` and `text/plain`; a real 2 × 2 PNG as `application/x-qt-image` with
    no data. So the image fact holds, and "no RTF" reads as if the formatting were dropped.
  - **Fix.** The facts check adds RTF alone and a real PNG; the guide: "rich text as `text/html` (converted from
    its RTF, which isn't listed)".
  - **Resolution: done:** the guide's line and its facts check were removed with the native backup (HLP-96's
    resolution); what Qt's backup loses is in DECISIONS.md, measured in HLP-96's resolution.

- [x] **TST-251 · The empty-clipboard fact is now measured only where no code relies on it, and clears the user's clipboard to do so** · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_an_empty_clipboard_has_mimedata`) · confirmed · found 2026-11-10
  - **Defect.** Its docstring: "Off macOS the 3D capture backs up the clipboard from mimeData()". On macOS the
    capture no longer calls `mimeData()`, and the check is skipped off macOS. DECISIONS.md's "An empty clipboard gives
    empty mime data, not None" (Reopen if: that check fails) rests on it.
  - **Scenario.** Every run clears and restores the user's clipboard for a fact no macOS code uses.
  - **Fix.** Say that it measures Qt on macOS in place of the Windows path, or drop it, which takes the user for the
    decision that names it.
  - **Resolution: done:** on macOS the capture backs up through `mimeData()` again, so the empty-clipboard fact is again
    one the code relies on there; the check compares the clipboard's text before and after.

- [x] **TST-252 · `test_by_default_it_is_the_general_pasteboard` can't fail** · `tests/unit/test_pasteboard.py:62-65` · confirmed · found 2026-11-10
  - **Defect.** It asserts `pasteboard._pb_general() == general`, `general` being the same call. The default of
    `pasteboard_read()` and `pasteboard_write()` (`pasteboard or _pb_general()`) is never exercised.
  - **Scenario.** The default changed to another pasteboard passes.
  - **Fix.** Replace `_pb_general` with a function returning a pasteboard of the test's own and call
    `pasteboard_read()` with no argument; or remove the test.
  - **Resolution: done:** `tests/unit/test_pasteboard.py` was removed with the native backup (HLP-96's resolution).

- [x] **TST-253 · The check of the 3D capture dropped the second capture HLP-96's Fix kept, and the resolution doesn't say so · follows HLP-96, generation 2** · `tests/test_all_tools/editor_panels_and_fit/checks.py` (`check_the_3d_capture_puts_the_clipboard_back`), `README.md:215-216` · confirmed · found 2026-11-10
  - **Defect.** HLP-96's Fix: "the second capture stays only for a clipboard whose content changed meanwhile". The
    check has no second capture: something the user copies while it runs makes it fail, and its `finally` puts the
    user's earlier clipboard over the new copy. The docstring says "something copied while it runs is lost"; README
    only "they use your clipboard for a few seconds and put it back".
  - **Scenario.** A user copying during the run loses that copy and sees a failed check that isn't a defect.
  - **Fix.** Record the change and its reason in HLP-96's resolution (a note); README: don't copy while the
    self-test runs.
  - **Resolution: done:** the check now puts a known text on the clipboard and reads it back, so there is no second
    capture to keep; README says the clipboard checks put test text on the clipboard for a few seconds and put back
    only the user's text.

- [x] **TST-254 · What Qt's backup lost is written in seven places, in different words, one of them wrong** · `mcp_server/designer_helpers/pasteboard.py:3-6`, `mcp_server/designer_helpers/screenshots.py:34-36`, `tests/test_all_tools/editor_panels_and_fit/checks.py`, `clipboards.py:1-3`, `designer_scripts/empty_clipboard.py:1-2`, `mcp_server/GUIDE.md:326-329`, `DECISIONS.md` (the empty-clipboard entry) · confirmed · found 2026-11-10
  - **Defect.** AGENTS.md wants each fact in one place, and DECISIONS.md's preface that an entry link to measured
    behaviour rather than repeat it. The copies differ: `pasteboard.py` "an image as an empty TIFF ... plain text and
    HTML came back", `screenshots.py` "loses an image, rich text's RTF, a second file", DECISIONS.md "lost images,
    rich text's formatting and all but one of several files": the formatting came back as HTML in what was measured.
  - **Scenario.** A reader takes the wrong version.
  - **Fix.** The measured list in `pasteboard.py`'s docstring only, the others linking to it; DECISIONS.md's wording
    corrected, which takes the user.
  - **Resolution: done:** the list of what Qt's backup loses is in DECISIONS.md (and HLP-96's resolution); the capture's
    docstring and the check link to it, and the other copies went with the native backup.

- [x] **TST-256 · The 3D capture's check puts the user's text back before Designer's own restore, which can then write the test's text over it · follows HLP-96, generation 2** · `tests/test_all_tools/editor_panels_and_fit/checks.py:22-45`, `mcp_server/designer_helpers/screenshots.py:66-88` · confirmed · found 2026-11-10
  - **Defect.** The check saves the user's text, puts `TEXT` on the clipboard, calls `screenshot_designer('3d')` and
    puts the user's text back in a `finally`. Inside Designer, `_save_3d_render` backs up the clipboard when its job
    starts (holding `TEXT` then) and writes that back in its own `finally`, after up to 5 s waiting for the render.
    When the call ends on the client's side first, the check's `finally` runs while the job still runs.
  - **Scenario.** Ctrl-C during the capture (a scratch run, or the full run, whose workers get the signal too), or
    the bridge's timeout: the call is cancelled, the check puts back the user's text, and Designer, in a session of its
    own and not interrupted, ends the job by putting `TEXT` back. The user's clipboard then holds "mcp_selftest: the
    text a 3D capture puts back". DECISIONS.md, "The 3D screenshot puts back only the clipboard's text": "The
    self-test's clipboard checks keep only the user's text too." Read, not probed: the order is in the code.
  - **Fix.** When the user's clipboard has text, use it as the check's marker, never replacing it (a capture that put
    nothing back leaves the render, not that text); put `TEXT` only when it had none.
  - **Resolution: done.**
    - **Test:** `test_a_capture_cancelled_on_the_clients_side_can_only_put_the_users_text_back`
      (`tests/unit/test_selftest_check_setups.py`): the clipboard held the check's text when the job would back it up.
      `test_the_3d_capture_check_still_tells_a_capture_that_put_nothing_back` guards that the check can still fail.
    - **Cause:** the check replaced the user's text with its own before Designer's job backed the clipboard up.
    - **Fix:** the user's own text is the marker when they have some; `TEXT` goes on the clipboard only when it held
      none (`editor_panels_and_fit/checks.py`). README's sentence no longer says test text is put there. `measure` and
      this category in a scratch run: 35 of 35.
    - **Also covered:** every `set_clipboard_text`: only this check and its `finally`.

- [x] **TST-257 · Two of `lifecycle`'s quits can still have a crash reported under another step, and the TST-236 test can't see them · follows TST-236, generation 2** · `tests/test_all_tools/lifecycle/checks.py:420, 582-593`, `tests/unit/test_selftest_lifecycle.py:407-420` · confirmed · found 2026-11-10
  - **Defect.** `CrashWatch.settle` gives a dump to the latest step started before it was written. (a) The launch that
    ends an agent's Designer not answering starts its step (`step = watch.step()  # it ends that Designer`) after
    `hold_thread_pool`, `CLOSE_WINDOWS_ONLY` and up to 30 s waiting for the shutdown; the stuck-shutdown quit above it
    starts its step before `hold_thread_pool`. (b) `check_a_designer_of_its_own` quits an agent's Designer (`await
    c('quit_designer', {'wait_s': 30})`) before any step: its dump, written about 3 s later during the launch that
    follows, is in the first step's `before`. The unit test scans only from `async def run(ctx: Ctx)` on, and accepts
    a step anywhere after the last check.
  - **Scenario.** (a) Designer crashes in its stuck shutdown: the failure reads "forces one with a frozen main thread,
    within the limit of its close", a quit that didn't crash (TST-236's own scenario). (b) In a scratch run, where
    `alone` keeps its Designer between runs, that quit crashes: no check fails. (In a pool `lifecycle`'s port is fresh
    and that quit never happens.)
  - **Fix.** (a) `step = watch.step()` before `hold_thread_pool`; (b) a step and a held check around that quit; the
    unit test reading the whole module.
  - **Resolution: done.**
    - **Test:** `test_every_quit_lifecycle_makes_is_a_watched_step` now reads from `check_a_designer_of_its_own` on and
      requires that launch's step before its shutdown starts: it failed on (a), and on (b) with a planted quit before
      its step.
    - **Cause:** TST-236's step was placed by the quit's call, not where its phase begins, and its test started at `run`.
    - **Fix:** (a) the step before `hold_thread_pool`; (b) a step and a held check, "closes the agent's Designer it
      replaces, without a crash". `lifecycle` whole in a scratch run, started beside an agent's Designer on its port so
      that quit happens: 46 of 46.

- [x] **TST-258 · `editor_panels_and_fit` still skips its screenshots on any "not visible", in a Designer the self-test started · follows TST-229, generation 2** · `tests/test_all_tools/editor_panels_and_fit/checks.py:33-35, 78-81`, `README.md:262` · confirmed · found 2026-11-10
  - **Defect.** `if not is_image(r_) and 'not visible' in text(r_): skip('screenshot_designer', '3d', 'no 3D View
    visible in Designer')`, and the panel loop the same (`'panel not visible in Designer'`). TST-229 made facts' 3D
    check skip only in the user's Designer (`ctx.was_running`), since a Designer the self-test started shows its views
    once its graph is open; its **Also covered** didn't look at the other skips. On macOS every run is in a Designer
    the self-test started, this preparation opens the graph and the console is shown first (`show_console`); the final
    check skipped none.
  - **Scenario.** A regression in `_visible_dock`, or `open_graph` no longer showing the editor, makes every panel
    "not visible": the screenshots skip in every run, and the final check passes.
  - **Fix.** Skip only when `ctx.was_running`, as facts does; README's "The 3D screenshot check is skipped if no 3D
    View is visible" then says in whose Designer.
  - **Resolution: done.**
    - **Test:** `test_a_view_not_visible_is_a_skip_only_in_the_users_designer`, for the 3D capture and the panels: in a
      Designer the self-test started, both skipped.
    - **Cause:** TST-229 narrowed facts' skip alone.
    - **Fix:** both skip only when `ctx.was_running`; the panel loop moved into `check_every_panels_screenshot`, so a
      test can reach it. README says in whose Designer. Scratch run: no skip.
    - **Also covered:** every read of `'not visible'` in the self-test: facts' (TST-229's) and one that checks
      `open_graph`'s answer, which skips nothing.
  - Questioned by TST-276 (2026-11-11).

- [x] **TST-259 · HLP-100's live check doesn't check the state it is about · follows HLP-100, generation 2** · `tests/test_all_tools/measure/checks.py:18, 38, 46, 57` · confirmed · found 2026-11-10
  - **Defect.** `await c('open_graph', G)` and each upstream `await c('node_stats', {'node_id': up, ...})` are called
    and their answers never read. HLP-100's resolution: never seen without the graph open and an output node in it,
    and even then not every time.
  - **Scenario.** `open_graph` fails, or the upstream measure gives an error (no temporary output attached and
    deleted): the three checks pass in a state where the defect never shows.
  - **Fix.** Fail the check when `open_graph` didn't open the graph, and require the upstream measure's pixel.
  - **Resolution: done.**
    - **Test:** `test_the_check_of_a_node_measured_after_its_upstream_fails_when_its_state_isnt_reached` (`open_graph`
      failing, the upstream measure failing): all three checks passed.
    - **Fix:** a graph that didn't open fails the check and measures nothing; each result requires the upstream
      measure's pixel. `check_an_output_added_right_after_the_node_feeding_it_was_measured` (HLP-101) does the same.

- [x] **TST-260 · With `port=`, `alone.run(..., own_designer=True)` runs beside the user's Designer and ends with exit code 1, not 2 · follows TST-228, generation 2** · `tests/test_all_tools/alone.py:127-133, 167-172` · confirmed · found 2026-11-10
  - **Defect.** `_refusal` asks whether the user's Designer runs only without a port (`users = port is None and
    users_designer_running()`), its comment relying on `launch_designer` refusing next to it. The `own_designer`
    branch never calls `launch_designer`: with a port and nothing answering there, `_refusal` gives `(None, False)`
    and the checks run.
  - **Scenario.** The user's Designer open, an agent runs the live-check skill's form, `alone.run(lifecycle.run,
    own_designer=True, port=9901)`: `check_a_designer_of_its_own`'s launch is refused, one check fails, exit code 1
    ("a check failed"), against `run_with`'s docstring ("they are refused beside the user's Designer as the others
    are") and TST-228's resolution ("exit code 2"). Nothing reaches the user's Designer; the agent is told its code
    failed.
  - **Fix.** In the `own_designer` branch, ask `users_designer_running()` whatever the port; a unit test with a port
    and the user's Designer running.
  - **Resolution: done.**
    - **Test:** `test_checks_with_their_own_designer_on_a_port_are_refused_beside_the_users_too`: the checks ran, exit
      code 0 instead of 2.
    - **Cause:** the port's case was left to `launch_designer`, which the `own_designer` path never calls for them.
    - **Fix:** that path asks whatever the port (`_refusal(c, None)`, `alone.py`). A Designer of another run still
      starting, not yet recorded, refuses too: run again.
  - Questioned by TST-279 (2026-11-11).

- [x] **TST-261 · TST-244's moves left tests patching what is no longer read, and a copy of the fakes · follows TST-244, generation 2** · `tests/unit/test_selftest_lifecycle.py:63, 113, 400`, `tests/unit/test_selftest_pool.py:542-544`, `tests/unit/test_selftest_workers.py:1-3, 16-23, 110-111` · confirmed · found 2026-11-10
  - **Defect.** `watching_crashes` moved to `crash_watch.py`, where it builds its own module's `CrashWatch()`; the
    tests still patch `vars(common)['CrashWatch']` (`functools.partial(common.CrashWatch, wait_s=0,
    find=_no_dumps)`), which nothing reads now. The docstring at line 400 still names `common.watching_crashes`.
    `test_selftest_workers.py` doesn't use `selftest_fakes` (TST-244's resolution: "used by both pool test files"): it
    keeps its own `_fresh`, and `_index()`, under a "one run, off macOS" heading, is used by no test.
  - **Scenario.** The three cases of the two tests of `check_launch_on_another_port` that reach its
    `watch.step(ports=[other])` (the fourth returns before it) get the real watch: it waits its 10 s and reads the real
    crash-dump folders, the user's `~/Library/Application Support/Adobe/Adobe Substance 3D Designer/Sentry-Crashpad`
    included. About 30 s added to the unit suite, and a dump the user's Designer writes then shows in the tests'
    output. The pool test's patch does nothing either (no step there, so no wait). The tests still pass, so "passing
    before and after the move" couldn't see it.
  - **Fix.** Patch `crash_watch`'s `CrashWatch`, with a `sleep` that fails the test, so a wait shows; `fresh` from
    `selftest_fakes` in `test_selftest_workers.py`, `_index` and its heading removed; the docstring corrected.
  - **Resolution: done.** Tests only.
    - **Test:** the three cases took 10 s each; now 0.0x s. `_no_wait` (`test_selftest_lifecycle.py`) lists each watch it
      builds and the tests assert one was: pointed at the old module, they failed.
    - **Cause:** the move left the patches on `common`, which the moved `watching_crashes` doesn't read.
    - **Fix:** the patches are on `crash_watch` (also `test_selftest_pool.py`); `_prepared` gives
      `check_a_designer_of_its_own` a quiet watch, since it now has one; `test_selftest_workers.py` uses
      `selftest_fakes.fresh`, `_index` and its heading gone, its docstring corrected.
    - **Also covered:** every `'CrashWatch'` patch and `common.watching_crashes` in `tests/unit`.

- [x] **TST-262 · `one_run`'s code for a run with no worker on macOS is unreachable, yet tested as live · follows TST-237, generation 2** · `tests/test_all_tools/__main__.py:223-226, 251-258, 321-323, 336-339`, `tests/unit/test_selftest_summary.py:382, 421, 453` · confirmed · found 2026-11-10
  - **Defect.** `one_run()` with no worker runs only on Windows (on macOS `main` takes the pool or refuses). There,
    `end_own_designer()` is guarded off (`sys.platform != 'win32'`), and `designer_here()` is `designer_alive()`, whose
    Windows branch raises no `NoListing`, so `designer_here_or_unknown`'s `except` and the `except NoListing` after
    the run never run; `already_running`, reached only with no worker, tells another run's Designer apart by
    `users_designer_running()`, which on Windows is any Designer. `test_another_runs_designer_isnt_taken_for_the_users`,
    `test_a_failing_process_listing_at_the_end_keeps_the_folder_and_the_summary` and
    `test_the_scratch_folder_goes_once_the_runs_own_designer_is_ended` run them with no worker on macOS, a state `main`
    can't produce. TST-237 removed `finish`'s branches of the same kind, at the user's decision, and named no other
    place.
  - **Scenario.** As TST-237's: a change to these branches is "tested" by tests of a state that can't happen, and a
    reader takes them as live.
  - **Fix.** As the user decided for TST-237: removed with their tests, git keeping them for ROADMAP item 65; or kept
    and marked as waiting for it, if the user prefers for this code.
  - Note (2026-11-11): the Fix above says more than is dead. Most of this path is live: `end_own_designer()` and
    `here()` for a worker, `designer_here` and `already_running` on Windows. What can never run is the two `except
    NoListing`.
  - **Resolution: done.** The user's decision (2026-11-11): the dead parts removed. A refactor of unreachable code: the
    tests of `__main__.py` pass before and after.
    - **Fix:** `designer_here_or_unknown` and the `except NoListing` after the run removed (`__main__.py`), with
      `test_a_failing_process_listing_at_the_end_keeps_the_folder_and_the_summary`, which only they could pass.
      `test_another_runs_designer_isnt_taken_for_the_users` now calls what is live (`designer_here`,
      `users_designer_running`), and `test_the_scratch_folder_goes_once_the_runs_own_designer_is_ended` ends a worker's;
      each failed with its old defect put back. Git keeps the handlers if ROADMAP item 65 needs them.

- [x] **TST-263 · `test_selftest_alone.py` leaves a folder in the system's temp folder at nearly every test** · `tests/unit/test_selftest_alone.py:68-70` · confirmed · found 2026-11-10
  - **Defect.** `scratch = kw.get('scratch') or tempfile.mkdtemp(prefix='alone_unit_')  # each category gets a folder
    in it`, never removed. On main `_run` passed `'scratch'`.
  - **Scenario.** Each `pytest` run while working adds a folder per call, with a folder per category in it: 448
    `alone_unit_*` folders in this machine's temp folder now. In the pool the unit suite's temp folder goes with the
    run; a plain `pytest` keeps them.
  - **Fix.** `tmp_path` passed in, or a `TemporaryDirectory`.
  - **Resolution: done.** Tests only.
    - **Test:** `test_a_run_here_leaves_no_folder_in_the_temp_folder`: a new `alone_unit_*` folder after the call.
    - **Fix:** `_run` uses a `TemporaryDirectory`.
    - **Also covered:** every `mkdtemp` in `tests/unit`: patched, or removed by its test. The 448 counted in the review
      had gone by the next day; those the runs before this fix left were deleted.

- [x] **TST-264 · The test of TST-230's fixture fails without it only when `SD_SNAPSHOT_DIR` isn't set · follows TST-230, generation 2** · `tests/unit/test_selftest_preparations.py:196-206` · confirmed · found 2026-11-10
  - **Defect.** It checks the clean-up against `~/.sd_mcp/snapshots` alone (`real =
    os.path.realpath(os.path.join(os.path.expanduser('~'), '.sd_mcp', 'snapshots'))`); its comment says
    "~/.sd_mcp/snapshots, or SD_SNAPSHOT_DIR as the test run found it".
  - **Scenario.** With `SD_SNAPSHOT_DIR` set in the environment (README, Configuration) and the fixture removed, the
    clean-up removes `$SD_SNAPSHOT_DIR/mcp_selftest`, and the test passes.
  - **Fix.** The real folder as the run found it (read by `conftest.py` before its fixture sets the variable), or the
    comment narrowed to `~/.sd_mcp/snapshots`.
  - **Resolution: done.** Tests only. `REAL_SNAPSHOT_DIR` (`conftest.py`) is the folder as the run found it, read before
    the fixture sets the variable, and the test checks against it. **Test:** with `SD_SNAPSHOT_DIR` set and the fixture
    removed, it now fails.

- [x] **PLG-37 · "A wake after the server is gone does nothing" has no test · follows PLG-36, generation 2** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:287-290` · confirmed · found 2026-11-10
  - **Defect.** `_on_wake`: `drain = self.drain()`, then `if drain is not None:  # None: the server is gone`, the
    behaviour PLG-36's resolution states. `test_a_stopped_server_is_freed_without_a_garbage_collection` checks that
    the server is freed, not a wake after it.
  - **Scenario.** A change to `_on_wake` calling the dead reference raises in Designer's event loop when a wake comes
    after the plugin stopped, and no test fails.
  - **Fix.** A unit test: the waker kept, the server freed with the collector off, `_on_wake()` called, nothing raised
    and nothing run; or, if no wake can reach it after `stop()` (which disconnects the signal), the comment calling the
    branch a defence.
  - **Resolution: done.** A test only: the plugin is unchanged, so no reinstall. **Test:**
    `test_a_wake_after_the_server_is_gone_does_nothing` (`tests/unit/test_plugin.py`); it passes on the code as it is,
    and fails with the guard removed (`TypeError`).

- [x] **TST-265 · README's "Running it" and the pool's docs say three things that aren't so** · `README.md:209, 214-215`, `tests/test_all_tools/workers.py:12, 288`, `PLAN.md:187, 243`, `.claude/skills/live-check/SKILL.md:72, 104` · confirmed · found 2026-11-10
  - **Defect.**
    - README's commands table: "Windows: one run of every category". `one_run()` runs `CATEGORIES`, which leaves
      `lifecycle` out (`categories.py`), so quitting and starting Designer are never checked there.
    - "Exit code 0: every check that ran passed; 1: a check failed". A full run also exits 1 on a tool no check
      exercised (`summarize`: `not failed and not missing`; `test_selftest_pool.py`, "a full run still fails on a tool
      no category exercised"), with no FAIL line, only "NOT covered" in the summary.
    - "The run's start checks ... run once, in the first category started (`--first`)". `first = next((name for name
      in order if name != LIFECYCLE), None)` takes the first in the categories' order: with `--only undo
      script_runner`, `undo`, which `SOLO` starts last. The checks still run in a Designer just started; the sentence
      is what is false.
  - **Scenario.** A tester on Windows (ROADMAP item 18) takes the quits as checked; whoever added a tool without a
    check looks for a failed check that isn't there.
  - **Fix.** README: "every category but `lifecycle`", and "1: a check failed, or (a full run) a tool no check
    exercised". `first`: the first category not in `SOLO`, the solo one only when it runs alone; or the sentences say
    "in one category".
  - **Resolution: done.**
    - **Test:** `test_the_start_checks_go_to_a_category_that_starts_before_the_one_kept_for_last`: `--first` went to
      `undo`.
    - **Fix:** `first` is the first category not in `SOLO`, the solo one only with nothing else (`workers.py`). "The
      first category to start after `lifecycle`" in `workers.py`, the live-check skill and PLAN.md. README: every
      category but `lifecycle` on Windows, and exit code 1 also for a tool no check exercised in a full run.
  - Questioned by TST-278 (2026-11-11).
  - Questioned by TST-281 (2026-11-11).

- [x] **TST-266 · Comments and the live-check skill that say something false · follows TST-229, TST-233 and TST-234, generation 2** · `.claude/skills/live-check/SKILL.md:36, 53-54`, `tests/test_all_tools/facts/preparations.py:54`, `tests/test_all_tools/common.py:215-217`, `tests/test_all_tools/params/checks.py:92-94`, `tests/test_all_tools/alone.py:25-26` · confirmed, the first measured · found 2026-11-10
  - **Defect.**
    - The skill ("a Designer just started for the category (its Home screen closed only by what the preparation
      opens)") and facts' preparation (at its `open_graph`: "its 3D view: a Designer just started shows only its Home
      screen"): `launch_designer` closes the Home screen when it starts Designer (`leave_home_screen()`,
      `server_tools/lifecycle.py:729`). Probe: in three Designers `alone` had just started (port 47311), before any
      graph was opened, `_home_screen()` was None, and `screenshot_designer('3d')` answered "3D View menu bar not found"
      in the two asked. What such a Designer lacks is a graph open in the editor.
    - `UNDO_REDO`'s comment: "(8 in 8 in pool runs, 1 in 3 in scratch runs; with it 4 in 4)". PLAN.md (step 6) and
      `categories.py`: 8 in 8 beside one idle Designer; 3 pool runs in 4.
    - `params/checks.py`: "sbsar_info checks the exposure further down": it is in `render/checks.py`, on render's own
      graph.
    - `alone.py`'s docstring, on runs side by side, names the preferences plist and the crash-dump folder; it leaves
      out `lifecycle`'s record put aside, during which "any launch_designer on the machine refuses"
      (`lifecycle/checks.py:451`): a scratch run of `lifecycle` makes the starts of every other run refuse, a pool's
      included. The skill (line 36): "so runs go side by side".
  - **Scenario.** An agent whose check fails only in a Designer just started looks for the Home screen, or opens a
    graph "to close Home", and misses the editor's state; a reader takes 8 in 8 as the pool's rate; a reader looks for
    the exposure check in `params`; an agent runs `lifecycle` in a scratch run during the user's final check, and the
    pool's starts are refused.
  - **Fix.** Each sentence corrected: no graph open, so no 3D view yet, until the preparation opens one; the figures
    as PLAN.md gives them; `render/checks.py`; no scratch run of `lifecycle` beside another run.
  - **Resolution: done.** Comments and docs only: the skill and facts' preparation (no graph open, so no 3D view yet),
    `UNDO_REDO`'s figures as PLAN.md gives them, `render/checks.py` in `params/checks.py`, and `alone.py`'s docstring and
    the skill on `lifecycle` beside another run.
  - Questioned by TST-279 (2026-11-11).

- [x] **TST-268 · The pool's unit tests can't see what `run_pool` wires in** · `tests/unit/selftest_fakes.py:112-118, 122-130, 155`, `tests/unit/test_selftest_pool.py:427, 501, 625`, `tests/test_all_tools/workers.py:246, 308, 320-322` · confirmed · found 2026-11-11
  - **Defect.** The fake `schedule(names, slots, start, **kw)` swallows `gate`, `exclusive` and `solo`; the fake `popen`
    reads only `env['SD_BRIDGE_PORT']`; `part()` gives every worker `'quit_at': time.time()`, so all quits are at once.
    `test_each_worker_gets_the_lock_and_a_port_and_folders_of_its_own` calls `worker_env` itself, and
    `test_a_solo_category_runs_with_no_other_designer_of_the_run` runs `schedule` itself and compares the constant.
    Nothing checks that `run_pool` passes them on, though `worker_env`'s `gate` and `schedule`'s `solo` have defaults.
  - **Scenario.** `worker_env(port_of[name], folder)` without the gate: `launch_lock._paths()` is None and `held()` does
    nothing, neither of `lifecycle`'s windows is held, and the hand-over check may only skip. `solo=SOLO` removed: `undo`
    runs beside the others, the failure it exists to prevent. `max(quits)` become `min(quits)`: the wait for crash dumps
    can end before the last worker's. Every unit test passes in each case (read).
  - **Fix.** The fake `schedule` asserts `solo`, `exclusive` and that the gate's `env()` is what the workers got; the fake
    `popen` asserts the lock's two variables are in `env`; one test with two `quit_at` values seconds apart.
  - **Resolution: done.** Tests only.
    - **Test:** the fake `schedule` asserts `exclusive` and `solo`, the fake `popen` that the gate's variables reach the
      worker (`selftest_fakes.py`), and `test_the_wait_for_crash_dumps_counts_from_the_last_quit` gives two quits 100 s
      apart. In `run_pool` as it is they pass; with the gate left out, `solo` left out, `exclusive` empty or `min(quits)`,
      each failed.
  - Questioned by TST-274 (2026-11-11).

- [x] **TST-269 · A unit test of a worker's quit fails on Windows** · `tests/unit/test_selftest_pool.py:368-393`, `tests/test_all_tools/__main__.py:214-219` · confirmed · found 2026-11-11
  - **Defect.** `test_a_worker_closes_its_designer_when_no_lock_holds_and_leaves_the_crash_dumps_to_the_pool` doesn't set
    `sys.platform`, and `finish` takes `if sys.platform == 'win32': skip(...)` before `elif worker:`.
  - **Scenario.** `pytest` on Windows, as AGENTS.md says to run it there: no quit happens, so `order == [...]` fails.
    Two neighbouring test files carry a `pytestmark` skip on `win32`; this one has none.
  - **Fix.** `monkeypatch.setattr(sys, 'platform', 'darwin')` in the test.
  - **Resolution: done.** Tests only; no Windows machine here, so `sys.platform` was set to `win32` around the tests by a
    scratch pytest plugin. **Test:** that test failed. **Fix:** it sets `sys.platform` to `darwin`.
    - **Also covered:** that plugin over `test_selftest_pool.py`, `test_selftest_workers.py`, `test_selftest_summary.py`,
      `test_selftest_categories.py`, `test_selftest_preparations.py` and `test_selftest_check_setups.py`: two more failed,
      `test_another_runs_designer_isnt_taken_for_the_users` and `test_the_scratch_folder_goes_once_the_runs_own_designer_is_ended`,
      and got the same line.

- [x] **TST-270 · Comments and a test's name that say something false · follows HLP-100, HLP-101 and TST-229, generation 3** · `tests/test_all_tools/measure/checks.py:79, 118, 240`, `tests/test_all_tools/facts/designer_scripts/grab_3d_view.py:16`, `tests/test_all_tools/lifecycle/checks.py:458`, `tests/unit/test_selftest_pool.py:257, 755` · confirmed, the second measured · found 2026-11-11
  - **Defect.**
    - `measure/checks.py:240`, `# last: it opens the graph in the editor`: since HLP-101 `run` opens it first.
    - `measure/checks.py:79` ("sweep_param's view, the same helper, never did") and `:118` ("a guard: never seen failing
      (the sweep sets the parameter before each compute)"), as HLP-100's resolution says. Probe: with the second compute
      removed in a scratch copy, its `sweep_param` check failed in 10 runs of 10, on its own and in whole runs (in one of them, the measure
      of the node feeding it failed first).
    - `grab_3d_view.py:16`, "checks.py skips its check on this token": since TST-229 it skips only in the user's Designer,
      and fails otherwise.
    - `lifecycle/checks.py:458`, `# nothing below can run, and the run's clean-up reports the Designer left open`: in a
      worker `own_here()` is false with the record gone, so nothing reports it but the failed check above it.
    - `test_lifecycle_starts_first_and_the_categories_follow_slowest_first` and the message `'slowest first, the start
      checks in the first'`: `names()` is built from `CATEGORIES`, so no order can fail; "slowest" is only comments there.
  - **Scenario.** A reader takes `sweep_param`'s check for one that can't fail, or looks for a clean-up report that
    doesn't come.
  - **Fix.** Generation 3, so the sentences get smaller and nothing is added: delete the `last:` reason; say the sweep's
    check fails without the second compute; cut the clause in `grab_3d_view.py`; `# nothing below can run: the check
    above says so`; the test named for "in their listed order" and the message without "slowest first".
  - **Resolution: done.** Comments, a docstring and a test's name only, nothing added: the `last:` reason deleted; `sweep_param`'s
    view named with the other two and "never seen failing" deleted (`measure/checks.py`); "reads this token" in
    `grab_3d_view.py`, and the same in `test_a_failing_3d_grab_does_not_read_as_no_3d_view`'s docstring; `lifecycle`'s
    comment narrowed; the test named for "in their listed order", its neighbour's message too.

- [x] **PLG-39 · A stopped server can still be freed off the main thread, the scenario PLG-36 was about · follows PLG-36, generation 2** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:528-532`, `tests/unit/test_plugin.py:1164-1180` · measured · found 2026-11-11
  - **Defect.** With the cycle gone, the server, its `QTimer` and its `_Waker` die wherever the last reference drops.
    `uninitializeSDPlugin` does `_server.stop()` and `_server = None` and joins nothing, while each `_serve` thread holds
    the server through its bound method. The test joins the accept thread first, so it doesn't take that order.
  - **Scenario.** Probe with the unit tests' fake Qt: a client being served, then `stop()` and the reference dropped, a
    `weakref.finalize` recording the thread: a `_serve` thread 25 times in 25 (with no client: the main thread 40 in 40).
    In Designer that is `~QTimer` and `~_Waker` on a Python thread, at plugin unload or quit, which Qt documents as unsafe
    for an object that may be handling events. Whether it did harm wasn't measured (no hot reload of the plugin in a
    Designer: GUIDE.md).
  - **Fix.** Keep `timer` and `waker` alive at module level after `stop()`, or `deleteLater()` them on the main thread; a
    test without the join, whose fake records the thread.
  - **Resolution: done.**
    - **Test:** `test_a_stopped_servers_qt_objects_are_never_freed_by_another_thread` (`tests/unit/test_plugin.py`), a
      client being served as the plugin unloads: "freed by ['Thread-3 (_serve)']".
    - **Fix:** `uninitializeSDPlugin` keeps the stopped server's timer and waker (`_retired`). With PLG-38, in the same
      plugin v6.
  - Questioned by TST-281 (2026-11-11).

- [x] **TST-273 · `test_a_job_reaching_an_idle_bridge_wakes_the_main_thread` can fail with nothing wrong** · `tests/unit/test_plugin.py:1081-1089, 1099-1100`, `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:449-451` · confirmed · found 2026-11-11
  - **Defect.** `_queue` returns once `jobs.qsize()` has grown, but the plugin emits after the put, outside the lock:
    `self.jobs.put(...)`, then `if idle: self.waker.wake.emit()`. `assert wake.emitted == 1` can run between them. The same
    gap lets the last assertion of `..._waits_for_the_timer` pass before a wrong emit lands.
  - **Scenario.** The unit suite beside four Designers (ROADMAP item 64 was a plugin test flaky under that load).
  - **Fix.** Poll for `wake.emitted` with a deadline.
  - **Resolution: done.** Tests only: `_soon` polls for the emit; where no emit is due, the test waits 50 ms before
    asserting it stayed at 1. A race, so not seen failing; read against the code.

- [x] **TST-274 · Two of the pool's unit tests can't see what they are named for · follows TST-268, generation 2** · `tests/unit/test_selftest_workers.py:22-27`, `tests/test_all_tools/workers.py:97, 308`, `tests/unit/selftest_fakes.py:127-138`, `tests/unit/test_selftest_pool.py:503-510` · confirmed · found 2026-11-11
  - **Defect.** `test_the_ports_are_distinct_and_free_of_other_runs` always passes its own `take`, so the default
    (`unused_port`) that keeps ports free of other runs is never reached. And TST-268's fake `popen` checks only the gate's
    variables: nothing sees that `run_pool` gives each worker its own folder (`worker_env(port_of[name], folder, gate)`).
  - **Scenario.** `folder` changed to `root`, or the default `take` to `free_port`: every unit test passes. All workers then
    share `SD_SNAPSHOT_DIR` and `TMPDIR` (one category's `remove_test_snapshots` under another; the shared temp folder ROADMAP
    item 59 ties to Designer crashes), or a worker can take a port another run's Designer is recorded on.
  - **Fix.** The fake `popen` requires `SD_SNAPSHOT_DIR` and `TMPDIR` inside its worker's folder; the port test renamed, or
    asserting the default.
  - **Resolution: done.** Tests only: the fake `popen` requires `SD_SNAPSHOT_DIR` and `TMPDIR` inside the worker's folder;
    the port test asserts that `ports` takes `unused_port` by default. With the folders given as the pool's root, or the
    default changed, they failed.

- [x] **TST-275 · Render's preparation sets two parameters no check reads** · `tests/test_all_tools/render/preparations.py:28` · confirmed · found 2026-11-11
  - **Defect.** `'params': {'Samples': 16, 'Intensity': 8.0}`, carried over from main's `params` category. `render/checks.py`
    names neither, and the docstring doesn't mention them; the live-check skill asks a preparation for "the minimum it
    reads".
  - **Scenario.** Samples at twice the library's default (8), in a category that computes and renders that graph many
    times; the cost wasn't measured.
  - **Fix.** Remove both, in a scratch run of `render`.
  - **Resolution: done.** The two parameters removed from `render`'s preparation; `render` in a scratch run: as above
    (96 of 96 with `bridge` and `link_display`).

- [x] **TST-276 · Docstrings that say something false · follows TST-258, generation 3** · `tests/test_all_tools/__main__.py:17`, `tests/test_all_tools/common.py:553`, `tests/test_all_tools/facts/checks.py:69`, `tests/test_all_tools/graph_edit_create/checks.py:10` · confirmed · found 2026-11-11
  - **Defect.**
    - `__main__.py`: "The 3D screenshot is skipped if no 3D View is visible": since TST-229 and TST-258, only in the user's
      Designer.
    - `summarize`: "(quit_designer while your own Designer runs)": `finish` skips it on Windows whoever started Designer, and
      never on macOS.
    - `facts/checks.py`: "`graph.compute()` takes about 0.9 s whatever the graph": PLAN.md measures about 1.7 s for a 40-blur
      graph at 2048; GUIDE.md and ROADMAP item 60 say "however small".
    - `graph_edit_create`: "its first nodes (clouds -> slope blur -> levels -> output)": nothing is connected there since
      the split.
  - **Scenario.** An agent sees a 3D-view failure on macOS and looks for a broken skip, or takes 0.9 s as a compute's cost.
  - **Fix.** Generation 3, so the sentences get smaller: "in the user's Designer"; "(`quit_designer` on Windows)"; "at least
    about 0.9 s"; "its first nodes".
  - **Resolution: done.** Docstrings only, each narrowed as the Fix says.

- [x] **TST-277 · A DECISIONS.md entry cites a review finding, against the file's own rule** · `DECISIONS.md:12, 169` · confirmed · found 2026-11-11
  - **Defect.** Line 12: "Entries don't cite review findings." The entry on the 3D screenshot, added on this branch:
    "(measured 2026-11-10, REVIEW.md HLP-96)".
  - **Scenario.** REVIEW.md is cleaned up once the branch merges, leaving a pointer in a file meant to stand on its own.
  - **Fix.** Drop "REVIEW.md HLP-96", keeping the date: a pointer, which agents may update, not what was decided.
  - **Resolution: done.** "REVIEW.md HLP-96" dropped from the entry, the date kept.

- [x] **TST-278 · `run_pool`'s docstring gives the exit code README was corrected for · follows TST-265, generation 2** · `tests/test_all_tools/workers.py:273` · confirmed · found 2026-11-11
  - **Defect.** "Its exit code: 0 every check passed, 1 otherwise". A full run exits 1 with every check passed when a tool
    went unexercised (`summarize`: `not failed and not missing`); TST-265 corrected README and named no other place.
  - **Scenario.** A reader of `workers.py` sees exit code 1 with no FAIL line and nothing there saying why.
  - **Fix.** "0 every check passed and, in a full run, every tool was exercised; 1 otherwise".
  - **Resolution: done.** Docstring only, as the Fix says.

- [x] **TST-279 · `alone`'s docstring and the live-check skill say more than `alone` does about running beside others · follows TST-260 and TST-266, generation 3** · `tests/test_all_tools/alone.py:17-19, 25-28, 170`, `.claude/skills/live-check/SKILL.md:36` · confirmed · found 2026-11-11
  - **Defect.**
    - "they too never run while the user's Designer is open", and the comment "never beside the user's": `_refusal`
      returns at `if 'Started by an agent' in text(status): return None, True` before asking whether the user's runs. With
      an agent's Designer answering on the port and the user's open elsewhere, `alone.run(lifecycle.run, own_designer=True,
      port=...)` runs: its launch is refused beside the user's, exit code 1, nothing reaching their Designer.
      `test_checks_with_their_own_designer_run_beside_an_agents` pins that case.
    - Runs "go side by side, except a scratch run of `lifecycle`": a scratch run of `facts` or `editor_panels_and_fit`
      shares the machine's one clipboard with any other run's, which `categories.CLIPBOARD` keeps apart only inside a pool.
  - **Scenario.** An agent takes the docstring at its word, or runs a clipboard check beside another run's.
  - **Fix.** Generation 3, so the sentences get smaller: refused "when the Designer on the port is the user's, or none
    answers there and one no agent recorded runs"; and "nor `facts` or `editor_panels_and_fit` beside another run of
    either".
  - **Resolution: done.** Docs only: `alone.py`'s docstring and comment and the live-check skill narrowed as the Fix
    says.
  - Questioned by TST-281 (2026-11-11).

- [x] **TST-280 · The pool also watches the crash folder of the default port, which none of its Designers uses** · `tests/test_all_tools/workers.py:247, 286`, `tests/test_all_tools/common.py:268-274` · confirmed · found 2026-11-11
  - **Defect.** `crash_dumps(ports)` always adds `PORT` (`for port in (PORT, *ports)`), and the pool's parent calls it
    with its workers' ports: so it also watches `agent_folder(9877)`, against `crash_dumps`' own "never another run's
    beside it" (REVIEW.md TST-155).
  - **Scenario.** `choose` lets a pool run beside a Designer an agent started, such as one a scratch run keeps open on
    9877; if that one crashes during the pool, the run fails "no new crash dump outside the run".
  - **Fix.** A keyword leaving `PORT` out, used by `workers.py`; a pool unit test with a new dump in that folder.
  - **Resolution: done.**
    - **Test:** `test_crash_dumps_include_those_of_the_runs_own_designers` with `run_port=False` (a `TypeError`), and the
      pool's fake `crash_dumps` refusing to be called with the default port: 16 pool tests failed.
    - **Fix:** `crash_dumps(ports, run_port=True)`; the pool's parent passes `run_port=False` both times.

- [x] **PLG-41 · The plugin's minimum wait reads the queue outside the lock, so a job queued in that instant starts without it · follows PLG-40, generation 4** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:483-488` · confirmed · found 2026-11-11
  - **Defect.** `_drain` decides whether to wait with `if self.ended is not None and not self.jobs.empty():`, outside
    `self.lock`, and takes the job later under it. A client's thread putting a job between the two (under the lock, in
    `_authorised`) gets it started at once, however soon after the last job ended.
  - **Scenario.** A job ends; within 30 ms the poll or a stale wake calls `_drain` with an empty queue, so it doesn't
    wait; a client queues a job before `_drain` takes the lock; that job starts within the 30 ms PLG-38 measured harm in.
    A window of a few bytecodes, so rare; the tools' retries stay behind it.
  - **Fix.** Decide inside `with self.lock:`, just before `get_nowait()`; or wait whenever the last job ended under 30 ms
    ago, the queue empty or not (a timer firing on an empty queue costs nothing). A unit test where the lock's first
    `__enter__` puts a job first.
  - **Resolution: done.**
    - **Test:** `test_a_job_queued_as_the_drain_looks_still_waits` (`tests/unit/test_plugin.py`): a lock whose first
      `__enter__` queues a job, as a client winning it: "started within the wait".
    - **Fix:** plugin v8: `_drain` decides under the lock, just before taking the job. After it, in three Designers just
      started: `bridge` and the two `measure` checks of HLP-100 and HLP-101, 43 of 43 each time (at least 30.6 ms between
      starts, 31.9 ms behind a long job).

- [x] **PLG-42 · The decision says a job reaching an idle bridge always waits 30 ms and is never started at the next poll; v7 waits only 30 ms after the job before · follows PLG-40, generation 4** · `DECISIONS.md:157`, `REVIEW.md` (PLG-40's resolution), `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:483-488` · confirmed · found 2026-11-11
  - **Defect.** The decision: "The plugin waits 30 ms before a job reaching an idle bridge, rather than starting it at
    once or at the next poll." PLG-40's resolution: "the wake's own 30 ms wait stays, so the decision's words hold". In
    v7, after a pause longer than 30 ms, `rest <= 0`, so the 100 ms poll starts a job at its next tick, from 0 to 30 ms
    after it arrived, while the wake's timer is still pending; `test_a_drain_long_after_the_last_job_starts_the_next_at_once`
    pins that.
  - **Scenario.** Harmless for Designer: the measured cause is the time since the job before, which v7 keeps. But the
    decision's first sentence is false for any call after a pause, and the next reviewer to measure it will raise it.
  - **Fix.** The user's decision: (a) reword the decision to what the measurement supports, "no job starts sooner than
    30 ms after the one before ended", and let the wake wait only for the rest of that, so a call after a pause starts at
    once; or (b) keep the words, with the poll leaving a job alone while the wake's timer is pending.
  - **Resolution: done,** as the user chose (2026-11-11): (a). DECISIONS.md's entry now reads "No job starts sooner than
    30 ms after the one before ended, whatever starts it; a call after a pause starts at once", its "keeps most of
    that" replaced by what was measured (about 30 ms per call one after the other, instead of the poll's 85).
    - **Test:** `test_a_wake_after_a_pause_starts_the_job_at_once`, with no job before and with one a second before: the
      wake started a 30 ms wait instead.
    - **Fix:** plugin v8: the wake runs `drain` at once again; the wait is only `_drain`'s minimum after the job before
      (`later`). `install.py` run. Live as PLG-41's. The plugin's docstrings, PLAN.md (`bridge`'s check renamed
      `check_no_job_starts_within_the_wait_after_the_one_before`) and README's `v8`.

- [x] **TST-281 · Sentences and test names that say more than the code · follows PLG-39, PLG-40, TST-265 and TST-279, generation 4** · `tests/unit/test_plugin.py` (`test_a_stopped_servers_qt_objects_are_never_freed_by_another_thread`, `test_a_drain_long_after_the_last_job_starts_the_next_at_once`), `tests/unit/test_selftest_pool.py:481` (`test_the_unit_suite_runs_beside_the_pool_as_one_check`), `tests/test_all_tools/bridge/checks.py:234, 261`, `tests/test_all_tools/alone.py:162-165`, `tests/test_all_tools/workers.py:75`, `tests/test_all_tools/categories.py:32`, `tests/test_all_tools/common.py:447` · confirmed · found 2026-11-11
  - **Defect.**
    - The Qt-objects test can only see the timer: the fake waker is held by its own `delay` timer's slot (`_FakeSignal`
      keeps the bound `_on_wake`), so it is freed only by a collection, kept or not.
    - "a drain long after the last job": no job ran before it (`ended` is `None`).
    - "the unit suite runs beside the pool": the fake `start_unit` returns a finished process and nothing records when it
      was started, so starting it after the pool would pass.
    - `bridge`: "started about 1 ms after it ended (PLG-40)" is v6's, and the check now asserts the opposite; "a job the
      wake starts runs on Qt's main thread": the poll may start it, as the comment above says.
    - `run_with`'s docstring: "they are refused beside the user's Designer as the others are", the sentence TST-279
      narrowed in the module's docstring and comment.
    - "in the order they start" (`workers.names`, `categories.py`): `SOLO`'s `undo`, listed before `script_runner`, starts
      last.
    - `Ctx.png`: "a PNG imported as a bitmap node": `lookup` and `save` only write it or copy it in.
  - **Scenario.** A reader takes each at its word.
  - **Fix.** Generation 4, so each gets smaller and nothing is added: the Qt-objects test says it checks the timer; the
    other two tests renamed ("with no job before", "as one check"); "on plugin v6"; "a job started on an idle bridge";
    `run_with` pointing at the module docstring; "in the pool's order (`SOLO`'s start last)"; "a PNG the preparation
    wrote".
  - **Resolution: done.** Names, comments and docstrings only, each narrowed as the Fix says: the Qt-objects test
    watches the timer and is named for it; `test_a_drain_long_after_...` became `test_a_wake_after_a_pause_starts_the_job_at_once`
    (PLG-42), with a job before as well as none; `test_the_unit_suite_is_one_check_of_the_pool`; `bridge`'s comment
    ("on plugin v6") and its main-thread check's name; `run_with`'s docstring; "the pool's order (`SOLO`'s start last)";
    `Ctx.png`.
