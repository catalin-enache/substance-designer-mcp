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
`mcp_server/server.py`, `server_tools/` and `designer_preferences.py`, **HLP** `mcp_server/designer_helpers/`, **INS** installer, uninstaller,
command-line client, example and `scripts/`, **TST** tests and docs. A new area gets a new prefix, added here.

**Last used:** PLG-45, SRV-175, HLP-187, INS-41, TST-526.

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
| Medium | 0 | 0 |
| Low-medium | 0 | 3 |
| Low | 0 | 11 |
| **Total** | **0** | **14** |

## Review log

### 2026-11-17: the appkit-notifications branch against main (ROADMAP item 101, the diff only, uncommitted)

- **How:** three reviewer subagents, one area each: the helpers (`mac_window.py`, `shot3d.py`, ROADMAP items 101 and
  107), the self-test (`common.py`'s HIDE, `window_states.py`, `checks.py`), and the unit tests (`appkit_fakes.py`,
  `test_mac_window.py`, `test_shot3d.py`, `test_waits.py`, `test_selftest_window_states.py`). No tests run. The lead
  agent settled each suspicion by reading, and one with a scratch probe in a Designer an agent started, its windows
  transparent and click-through. The probe called `miniaturize:` 3 times and `performMiniaturize:` 3 times, then
  `deminiaturize:` 5 times and `orderFrontRegardless` once. It logged the notifications with macOS's minimized flag and
  the window server's list at each:
  - `NSWindowDidMiniaturizeNotification` came first, with the window minimized and unlisted, 6 of 6. The occlusion
    change came 0.002 to 0.012 s after it.
  - `NSWindowDidDeminiaturizeNotification` came with the window no longer minimized, 6 of 6, whichever call.

  Settled as wrong, so not recorded:
  - **A hide of a window already covered whole wakes the off-screen wait on the poll only.** It isn't a defect: no
    notification says that case, the poll stays behind the notifications for it, and no docstring says otherwise
    (`_wait_unlisted`: "and every TICK ms").
  - **The facts check could show its window again mid-minimize, if the occlusion change came before
    `NSWindowDidMiniaturizeNotification`.** The probe saw the opposite order, 6 of 6, with the minimized flag already set
    at the first notification.
  - **Waits on occlusion or exposure still poll** (`window_states.py`'s `in_front()`, `until(reached)` for the covered
    ways, `EVENT_DONE['cover']`). Qt's expose events wake those: Qt exposes a window as its occlusion changes. The
    `_READ` waits on `minimized=True` and `hidden=True` follow a shot whose own wait already saw the window unlisted
    (`_wait_unlisted`), so they hold at once. Only the ROADMAP sentence claiming all of them is recorded (TST-519).
- **Not verified:** none.
- **Resolutions assessed:** none in scope; `REVIEW.md` was empty after the last cleanup.
- **Findings:** TST-515 (Low-medium); TST-516, TST-517, TST-518, TST-519, HLP-186, HLP-187 (Low). No duplicates to
  merge across reviewers; within a reviewer's report, the regex's gaps and the assertion message are one finding
  (TST-518).
- **Suggested order:** TST-515 first: two older tests no longer fail on the bugs they guard. Then HLP-186 and HLP-187
  (the helpers), TST-516 and TST-517 (the facts check), and TST-518 and TST-519 (the tests' texts and ROADMAP).
- **Checked and found fine:**
  - **ctypes:** `NOTICE`'s five pointers; `CF_AT_ONCE` a `CFIndex` (`c_long`, 64 bits on macOS); `in_dll(...).value`,
    AppKit's exported `NSString`; the observer key `id(self)`; the `NSWindow` prefix picking each name's sender.
  - **Lifetimes:** `_Notices` holds its callback, relay and `cf`, with no cycle back to itself; nothing outlives a wait.
  - **Abort safety:** every landing point in `_notified`, against the plugin's tracer. The unit tests land an abort at
    each traced event and fail without the second close. The shot's abort test also fails without it.
  - **Order:** no Designer event runs between a change (`unhide`, `hide`, `minimize`) and `open()`, and `_until` reads
    the state first.
  - **Windows:** nothing at import fails there; the waits run only with a `_MacWindow`.
  - **The snippets:** every name they use comes from the helpers' text, and nothing rebinds it. The connections go with
    each relay. Designer ends hidden, and `at_rest` follows each try. The steps run transparent and click-through. The
    check's place in `run()`, inside the front watch, holds: the watch judges only windows above opacity 0.
  - **The unit tests:** the new ones fail without their change. The TST-428 spies test, the TST-470 order test and
    `_code_lines` hold.
  - **Types:** no explicit `Any` in the diff; `object` only where a value is stored or compared.


### 2026-11-17: the appkit-notifications branch against main, second review (the diff only, uncommitted)

- **How:** three reviewer subagents, one area each: the helpers (`mac_window.py`, `shot3d.py`), the self-test
  (`window_states.py`, `checks.py`, `common.py`'s HIDE), and the unit tests with ROADMAP (`appkit_fakes.py`,
  `window_fakes.py`, `test_mac_window.py`, `test_shot3d.py`, `test_waits.py`, `test_selftest_window_states.py`). No
  tests run. The lead agent settled each suspicion by reading, and two with scratch probes, one at a time, in a Designer
  an agent started:
  - `_CLEAR`'s windows made opaque once its wait for the hidden flag wakes, on `NSApplicationDidHideNotification`. The
    probe sampled the window server's list every millisecond or so from the self-test's process (`window_server.py`)
    around 10 runs of `_CLEAR`: 6 woken by `HIDDEN`, 4 polled. After the main window was put on screen, no window of
    Designer's was listed above opacity 0 once the wait woke. After 'transparent in front', two were listed opaque for
    about 30 ms. They were opaque before `_CLEAR` restored anything: the closed cover and window under, behind every
    other app's window. Both waits woke about 17 ms after the hide, on Qt's events, so the branch's wake changes
    nothing there. Settled as wrong.
  - `in_front()` counting a window that was in front of Designer's before the show: recorded (TST-522).
- **Settled as wrong, so not recorded:**
  - `_Notices` relies on the ctypes prototypes `_MacWindow.notices` sets: its only caller sets them, so no current path
    is affected.
  - `_NOTIFIED` counting no cover during its changes: a cover then can't be told apart from what the check measures
    (TST-523's Fix).
  - The `_CLEAR` suspicion above.
- **Not verified:** none.
- **Resolutions assessed:** all 8 in scope.
  - Hold: TST-515, TST-518, HLP-186, HLP-187. TST-517's check and tests hold.
  - TST-516 and TST-520 are questioned by TST-521: TST-520's change left `in_front()` unguarded.
  - TST-520 is also questioned by TST-522, TST-523 and TST-524.
  - TST-517 and TST-519 are questioned by TST-525: a copy of the counts missed, two ROADMAP sentences.
- **Findings:** TST-521, TST-522 (Low-medium); TST-523, TST-524, TST-525, TST-526 (Low). TST-521 and TST-524 were each
  found by two reviewers.
- **Suggested order:** TST-522 first: it can fail the facts check in a final run with nothing in the way. Then TST-521
  (its test), TST-524 and TST-523 (the counts and the wake), TST-526 (the fakes), and TST-525 (texts).
- **Chains:** the longest still growing is TST-516 → TST-520 → TST-521, TST-522, TST-523, TST-524, at generation 2.
- **Checked and found fine:**
  - **The helpers:** `NOTICE` and the AddObserver prototypes; a NOTICE instance passed, so no temporary thunk; the
    thunk can't be freed in a dispatch; every abort landing point in `_notified`; each wait bounded, the state read
    first; the senders; `_bring` and `_wait_off_screen` lost no case.
  - **The self-test:** `until` and `woken_until` return a value on every path; `first()`'s slot is connected before
    `_until`'s own; the dropped results of `_wait_unhidden` and the un-minimize wait in `_NOTIFIED` turn into "in the
    way" at the next `in_front()`; `below` is registered before it shows; the detail strings and docstrings of the
    window-under and not-drawn facts match the code.
  - **The unit tests:** TST-520's cases each fail without their part (the reviewer traced them by hand, as the
    addressing agent's scratch mutations did); the abort tests fail without the second close; nothing depends on the OS
    without a `skipif`; no explicit `Any`.

---

## High

## Medium-high

## Medium

## Low-medium

- [x] **TST-515 · Two older tests no longer fail on the regressions they guard** · `tests/unit/test_mac_window.py:257-273`,
  `tests/unit/test_selftest_window_states.py:592-596` · confirmed · found 2026-11-17
  - **Defect.** Both tests lost what made them fail on their bug.
    - The HLP-166 test (`test_the_show_is_waited_for_until_macos_says_designer_is_shown_not_until_its_window_is_exposed`)
      no longer sets up a window covered whole (`isExposed=lambda: False`). The faked `_APP` then gives a `MagicMock`
      main window, whose `isExposed()` is truthy.
    - The TST-460 check keeps only the `return`s that have a value
      (`if isinstance(n, ast.Return) and n.value`), and no longer pins `until`'s last statement. A bare `return` is
      what TST-460's bug was.
  - **Scenario.**
    - `_wait_unhidden`'s state changed back to read Qt's exposure, such as `not mac.hidden() and
      _main_window().window().windowHandle().isExposed()`, still passes the HLP-166 test (`held == [True, True]`). Before,
      the unexposed handle made it fail.
    - `until()` given `if names: _notified(...); return` passes the TST-460 check. `_CLEAR`'s `hidden = until(mac.hidden,
      names=HIDDEN)` then reads `None`, and every `if not until(..., names=...)` raises, which only a live run would show.
  - **Fix.**
    - Put back, in the HLP-166 test, a main window whose handle says unexposed (the `_APP` stand-in, `isExposed=lambda:
      False`).
    - Assert that every `ast.Return` in `until` has a value that calls `woken_until(state, limit, `, and that `until`'s
      last statement is such a `Return`.
  - **Resolution: done.**
    - **Test:** scratch mutations brought each bug back: `_wait_unhidden`'s state reading the main window's exposure,
      and `until()`'s `names` branch ending in a bare `return`. Both tests passed with the bug back before the fix, and
      fail with it after.
    - **Cause:** adapting the tests to the new waits, the HLP-166 test lost its covered main window (the faked `_APP`
      then gives a `MagicMock`, whose `isExposed()` is truthy), and the TST-460 check left out the `return`s without a
      value.
    - **Fix:** the HLP-166 test's main window is covered whole again: its top-level window's handle says unexposed, and
      any other read of them raises. The TST-460 check asserts that every `return` of `until()`, a bare one included,
      calls `woken_until(state, limit, `, and that its last statement is a `return`.
    - **Also covered:** the other older tests the branch adapted, TST-428's spies test and TST-470's order test, still
      fail on their bugs (the review log); no other older test lost set-up.

- [x] **TST-521 · No unit test runs the facts check's `in_front()` any more, so TST-516's bug could come back unseen** ·
  follows TST-520, generation 2 · `tests/test_all_tools/editor_panels_and_fit/window_states.py:546-548`,
  `tests/unit/test_selftest_window_states.py:668-679` · confirmed · found 2026-11-17
  - **Defect.** TST-520 moved TST-516's wait and count into `_WINDOW`'s `uncovered`, and TST-516's test now calls
    `uncovered` directly. `_NOTIFIED`'s `in_front()` (`uncovered(mac, others)`, then `others.extend(in_front_of(mac))`)
    runs in no unit test. `_steps`, the only unit test reading `_NOTIFIED`, reads only its `first(...)` calls. Found by
    two reviewers.
  - **Scenario.** `in_front()` put back as before TST-516 (`mac.show()`, then `others.extend(in_front_of(mac))`), or one
    of its four calls dropped before a minimize or a hide. Every unit test still passes, and so does a live run with
    nothing in the way. TST-515's pattern: an older test no longer guards what it was written for.
  - **Fix.** Run `_NOTIFIED`'s `in_front()` through `_defined` on a faked screen covered whole
    (`Screen(cover=True).main`) and assert it counts one in the way. Pin with ast that an `in_front()` call comes before
    each `first(...)` whose change is a minimize or a hide. Then correct TST-516's note.
  - **Resolution: done.**
    - **Test:** `test_the_facts_checks_window_brought_in_front_counts_only_what_is_still_in_the_way` runs `in_front()`
      on a faked screen (`window_fakes.Screen`) through `_defined`, which defines a snippet's functions, here
      `notified()`'s.
      `test_the_facts_check_brings_designers_window_in_front_before_each_minimize_and_hide` reads `_NOTIFIED` with ast.
      Both passed on the code, which had no bug here. On scratch mutations they failed: `in_front()` put back as before
      TST-516 failed the first (the cover not counted), and one `in_front()` dropped before the hide failed the second.
    - **Fix:** the two tests. They, not TST-516's note's test, guard `in_front()`.

- [x] **TST-522 · The facts check's `in_front()` counts a window that was in front of Designer's before the show, from
  CoreGraphics' late list** · follows TST-520, generation 2 · `tests/test_all_tools/editor_panels_and_fit/window_states.py:546-548`
  · measured · found 2026-11-17
  - **Defect.** `in_front()` reads `in_front_of(mac)` right after `uncovered(mac, others)`. `uncovered`'s wait returns at
    once when the window isn't covered. Right after `orderFrontRegardless`, CoreGraphics still lists the old order:
    TST-520 measured it, 3 of 3, and left the windows in front unlisted after `_UNDER`'s last `uncovered` for that
    reason. Its Also covered missed `in_front()`, which reads them at the same moment.
  - **Scenario.** The review's probe, in a Designer an agent started: a window of Designer's own, at opacity 0 and not
    one the checks make, over part of its main window and in front of it. Then `uncovered(mac, others)`, then
    `in_front_of(mac)` at once, 3 times. That window was listed in front 2 of 3 times, no longer listed a moment later,
    and `uncovered` counted nothing. An unhidden Designer goes behind the active app's window (REVIEW.md HLP-166), so a
    window of the user's over part of Designer's main window is counted in the way. If that happens in every try, the
    facts check fails, saying "a window in the way in each of 3 tries", with nothing in the way.
  - **Fix.** List the windows in front only once the order has settled. For example, `uncovered` waits until the window
    is on screen, not covered and with nothing in front (`not in_front_of(window)`, as `_PUT`'s `front` does); what is
    still in the way when the wait runs out is counted. `in_front()` then reads nothing more.
  - **Resolution: done.**
    - **Test:** `test_the_facts_checks_window_brought_in_front_counts_only_what_is_still_in_the_way` with a window only
      on CoreGraphics' late list (`Screen(late=[99])`) failed: `[99]` counted. Its other cases, a window still in front,
      a cover and nothing, passed before and after. In the scratch run, a window of Designer's own, transparent and
      click-through, over part of its main window and in front of it before each `in_front()` (scratch only), failed
      the facts check: "a window in the way in each of 3 tries", every reading otherwise True.
    - **Cause:** `in_front()` listed the windows in front right after the show, from a list that still gave the order
      before it, once `uncovered`'s wait had held at once.
    - **Fix:** `uncovered` waits until the window is on screen, not covered and with no window listed in front of it,
      and counts one in the way when the wait runs out. `in_front()` reads nothing more. In the scratch run, with the
      same window, the facts check passes in one try. `_UNDER`'s last `uncovered` no longer needs its comment on the
      late list: the wait now covers it.
    - **Also covered:** every `in_front_of` read in the snippets. `_PUT`'s `front` waits until none is listed. `_HITS`
      and `_UNDER`'s readings list them after a `_settle`, and `_PANNED` after `_PUT`'s wait. None reads right after a
      show.

## Low

- [x] **TST-516 · The facts check's IN_FRONT count can't see what would spoil its readings, and `in_front()` drops its
  wait's result** · `tests/test_all_tools/editor_panels_and_fit/window_states.py:531-534` · confirmed · found 2026-11-17
  - **Defect.**
    - `in_front()` counts the windows in front of Designer's right after `mac.show()` (`orderFrontRegardless`).
      `_MacWindow.in_front` keeps only normal windows (layer 0), so none can be in front then, and the count is 0
      whatever covers the window.
    - What would spoil a reading isn't counted: a window above layer 0 over all of Designer's window, or a locked screen.
      Such a cover keeps the window counted covered, so a hide changes no occlusion and no notification comes.
    - `until(lambda: mac.on_screen(number) and not mac.covered())` returns False then, and the snippet ignores it.
  - **Scenario.** Another app's always-on-top window covers Designer's window whole during the check. The reading is
    `hidden=none` with `IN_FRONT 0`, so `without_others_in_front` doesn't take it again, and `tries_said` says nothing.
    The check fails in a final run, with no reason given.
  - **Fix.** In `in_front()`, count the window as covered when the wait ran out with the window still covered (for
    example `others.append(-1)` when `mac.covered()`), so the reading is taken again and the detail says a window was in
    the way.
  - **Resolution: done.**
    - **Test:** `test_the_facts_checks_window_still_covered_once_brought_in_front_reads_as_in_the_way` runs the
      snippet's `in_front()` with fakes. With the window still covered it failed (nothing counted). The case with the
      window uncovered passed, and passes.
    - **Cause:** the count was the only sign of a cover, taken where no cover can be listed, and the wait's result,
      which said the window was still covered, was dropped.
    - **Fix:** `in_front()` counts the window as in the way when it is still covered once its wait ends, so
      `without_others_in_front` takes the reading again and `tries_said` says a window was in the way. The facts check
      passes in its scratch run, with nothing in the way.
    - **Also covered:** `in_front()` runs before each minimize and hide; the unhide needs no front. HITS sees a window in
      the way through its click reading (`another(...)`). UNDER, an older check outside this branch, counts the windows
      in front right after a show too: the same blind spot, left as it is and proposed to the user.
  - Note (2026-11-17): the user asked for UNDER's blind spot to be fixed: TST-520. Its fix moved the wait and the count
    into `uncovered` (`_WINDOW`), which `in_front()` now calls. This entry's test is now
    `test_a_window_still_covered_once_brought_in_front_reads_as_one_in_the_way`.
  - Questioned by TST-521 (2026-11-17).

- [x] **TST-517 · The facts check measures the un-minimize through a call the self-test's waits on it don't follow** ·
  `tests/test_all_tools/editor_panels_and_fit/window_states.py:540` · measured · found 2026-11-17
  - **Defect.** `first(UNMINIMIZED, mac.show, lambda: not mac.minimized())` un-minimizes with `orderFrontRegardless`. The
    self-test's waits on `UNMINIMIZED` follow `deminiaturize:` (`to_back`, `_CLEAR`). The shot un-minimizes with `show()`
    but doesn't wait on `UNMINIMIZED`. So the fact `shot3d.py`'s docstring gives for the self-test's waits ("came with
    macOS no longer saying the window minimized") is re-measured on another path.
  - **Scenario.** Measured (the review log's probe): with `deminiaturize:` too, the notification came with the window no
    longer minimized, 5 of 5. So nothing is wrong today. A macOS update changing `deminiaturize:`'s order would go unseen
    by the check while the self-test's waits followed it.
  - **Fix.** Un-minimize with `deminiaturize:` in that step, the call the waits follow.
  - **Resolution: done.**
    - **Test:** the facts check's un-minimize step read with ast: the step called `mac.show`. Now
      `test_the_facts_check_reads_each_notification_after_the_call_the_waits_on_it_follow`, over each reading's
      notifications and call, with `test_the_self_tests_waits_follow_the_calls_the_facts_check_reads_after` for the
      waits' side. A scratch mutation back to `mac.show` fails it.
    - **Cause:** the check followed the shot's calls, while the waits on `UNMINIMIZED` are the self-test's.
    - **Fix:** the step calls `deminiaturize:`. `shot3d.py`'s docstring gives the counts for both calls, and the check's
      docstring says which it makes. The facts check passes in its scratch run.
    - **Also covered:** the same pattern in the minimize. The shot's wait on `OFF_SCREEN` follows `miniaturize:`, and
      the self-test's minimized way's (`_PUT`) follows `performMiniaturize:`; the check measured the first only.
      The same test failed on it (its `performMiniaturize:` case). The check now reads both (`minimized_by_button`),
      and passes in its scratch run. The test also pins the readings after `unhideWithoutActivation` and `hide:`. The review's probe measured both calls, 3 of 3 each, and
      `shot3d.py`'s counts are updated.
  - Questioned by TST-525 (2026-11-17).

- [x] **TST-518 · Two texts in the new unit tests say more than the tests check** · `tests/unit/test_waits.py:119-122`,
  `tests/unit/test_shot3d.py:628` · confirmed · found 2026-11-17
  - **Defect.**
    - `test_waits.py`: `NOTIFIED`'s comment names "the helpers' waits on them (mac_window.py)", and the pattern accepts
      `_until_notified(` and `_notified(`. But `MACOS_FLAG` (`\b_?until\(`) never matches a line calling
      `_until_notified(`, and no `_notified(` line reads a flag. So those alternatives never decide anything, and only
      `names=` does. `MACOS_FLAG`'s comment says `_MacWindow.hidden` and `.minimized`, but the pattern sees them only on
      a variable named `mac`, in a call spelled `until(` or `_until(`. `names=()` passes, though it observes nothing.
    - `test_shot3d.py`: `'each observed during its wait only'` is the message of an assertion that counts one open and
      one close (`n.opened == n.closed == 1`), not that the wait ran between them. The order is checked in
      `test_mac_window.py`, through `_until_notified`.
  - **Scenario.** A reader takes the guard to cover the helpers' waits and any `_MacWindow` variable, and the shot's test
    to check the order. Neither does.
  - **Fix.** Narrow the texts: `NOTIFIED` to `names=` given a non-empty value, its comment to what it then accepts;
    `MACOS_FLAG`'s comment to the variable and the calls it sees; the assertion's message to "each opened and closed
    once".
  - **Resolution: done.**
    - **Test:** a scratch check: the old `NOTIFIED` accepted `until(lambda: mac.hidden(), names=())`, the new one
      refuses it, and both accept `names=HIDDEN`.
    - **Fix:** `NOTIFIED` is `names=` given one of `mac_window.py`'s four tuples, by name; its comment says so. `MACOS_FLAG`'s
      comment names the variable and the calls it sees, and that the helpers' waits don't match it. The module
      docstring's sentence says the same. The shot's assertion message says "each opened and closed once".
    - **Also covered:** ROADMAP item 101's sentence on the guard: narrowed alike (TST-519).

- [x] **TST-519 · ROADMAP items 101 and 107 say more than the code does** · `ROADMAP.md:81`, `ROADMAP.md:140` · confirmed
  · found 2026-11-17
  - **Defect.**
    - Item 101 says `NSApplicationDidHideNotification` "isn't observed", then that the self-test's waits use it.
    - Item 101 says "The self-test's waits for Designer hidden or shown again, and for its window minimized, shown again
      or off screen, look as these come too". `_READ`'s waits on `minimized=True` and `hidden=True` (`checks.py:1432`)
      and `until(reached)` don't. They hold at once, after a shot's or a way's own wait, but the sentence claims them.
    - Item 107 says "On macOS the 3D view draws nothing while Designer's window is off screen". `shot3d.py`'s docstring
      records a covered window drawing in some Designers that `open` started (6 of 6 tries; REVIEW.md TST-433).
  - **Scenario.** A reader of the ROADMAP takes `NSApplicationDidHideNotification` for unused, every self-test wait on
    these states for woken by AppKit, and covered windows for never drawn.
  - **Fix.** "so the shot's wait for the window off screen doesn't observe it"; "the self-test's waits after it hides,
    shows or minimizes Designer itself"; "draws nothing while Designer's window is minimized or Designer hidden, and may
    not while it is covered".
  - **Resolution: done.**
    - **Test:** none: ROADMAP text.
    - **Fix:** the three sentences as suggested. Also the guard's sentence (TST-518), and "no Python runs" (HLP-187).
  - Questioned by TST-525 (2026-11-17).

- [x] **HLP-186 · `center` in `_Notices` is an implicit `Any`** · `mcp_server/designer_helpers/mac_window.py:80`, `:86` ·
  confirmed · found 2026-11-17
  - **Defect.** `center = self._cf.CFNotificationCenterGetLocalCenter()` takes the result of a call through a `CDLL`,
    which mypy types `Any` and doesn't report (AGENTS.md: look for those yourself). `close()` passes the same call's
    result straight on.
  - **Scenario.** mypy checks nothing about `center`. `_listed` in the same file annotates the same kind of result
    (`windows: int | None = ...`, "a c_void_p result is an int, or None for NULL").
  - **Fix.** `center: int | None = self._cf.CFNotificationCenterGetLocalCenter()` in `open()`, and the same local in
    `close()`.
  - **Resolution: done.**
    - **Test:** none committed: `test_types.py`'s mypy passes before and after, as an implicit `Any` isn't reported.
      mypy's `--disallow-any-expr` flags line 80's call, but also every other ctypes call in the file (221), so reading
      settled it.
    - **Cause:** a call through a `CDLL` returns `Any` for mypy, and the new local wasn't annotated as `_listed`'s is.
    - **Fix:** `center: int | None` in `open()` and `close()`, with `_listed`'s comment.
    - **Also covered:** the other functions the branch adds in `mac_window.py` hold no other untyped ctypes result:
      `notices()` casts `in_dll(...).value`, and `NOTICE(...)` is typed.

- [x] **HLP-187 · `_Notices`' docstring says no Python runs as a notification comes, which holds only while no Python
  slot is connected** · `mcp_server/designer_helpers/mac_window.py:66-68` · confirmed · found 2026-11-17
  - **Defect.** "The callback is the signal's own emit, so no Python runs as a notification comes, and no abort can land
    there". The callback emits `fired`, and whatever is connected to it runs then. The shot's waits connect only Qt's own
    `loop.quit`. The facts check's `first()` (`window_states.py`, `_NOTIFIED`) connects a Python lambda, through
    `_notified`.
  - **Scenario.** An abort can land in that lambda: PySide reports it, and the plugin's hooks raise it again at the next
    traced event, so nothing is lost. But a reader building a wait on `_Notices` with a Python slot would take the
    sentence as a guarantee.
  - **Fix.** "... so no Python runs as a notification comes while only Qt's own slots are connected to `fired`, as in
    the shot's waits".
  - **Resolution: done.**
    - **Test:** none: a docstring.
    - **Fix:** the sentence now holds "while only Qt's own slots are connected to `fired`, as in the shot's waits".
    - **Also covered:** ROADMAP item 101 said the same: narrowed alike. `waits.py`'s "no Python runs in a slot" is about
      `_until`'s own connections, and holds.

- [x] **TST-520 · Two more facts count only normal windows in front, so a cover above them spoils the reading
  unseen** · `tests/test_all_tools/editor_panels_and_fit/window_states.py` (`_UNDER`, `_PANNED`) · measured · found
  2026-11-17
  - **Defect.** TST-516's blind spot, in two older facts. Each counts the windows in front of the window it reads, and
    `_MacWindow.in_front` keeps only normal windows (layer 0). A window above them, or a locked screen, isn't counted.
    - The window-under fact (`_UNDER`) counts right after it brings the window it reads in front, where no normal
      window can be. A cover makes that window read covered alone and under the transparent main window.
    - The not-drawn fact (`_PANNED`) counts before and during its pan. A cover over Designer's window stops the drawing
      of a way that should leave the view drawn: on screen, partly covered, transparent in front.
  - **Scenario.** A scratch run put an always-on-top window of Designer's own (floating level) over its main window.
    The window-under fact read `alone=True opaque=True transparent=True`, and the not-drawn fact `on screen True,
    partly covered True`. Each counted `IN_FRONT 0`, so neither reading was taken again, and nothing said why.
  - **Resolution: done.**
    - **Test:**
      - `test_the_window_under_fact_counts_a_cover_no_window_list_shows_as_one_in_the_way` runs `_UNDER` on a faked
        screen (`tests/unit/window_fakes.py`). With a cover over every window it failed: `IN_FRONT 0`. Two more
        cases, a cover that comes after the reading alone and one that goes after it, each fail without one of the
        two calls to `uncovered` (scratch mutations). Two cases passed before the change and pass after: nothing in
        the way, and macOS counting the transparent window as covering, which isn't taken again.
      - `test_a_way_that_leaves_the_view_drawn_still_covered_once_put_reads_as_one_in_the_way` runs `panned(way)`'s
        count. It failed for the three drawn ways with Designer's window covered: nothing counted. The ways covered on
        purpose (minimized, covered) and a drawn way not covered count nothing, before and after.
      - In the scratch run, the old snippets failed as in the scenario.
    - **Cause:** as TST-516: the count was the only sign of a cover, and it can't list one above the normal windows.
    - **Fix:**
      - `uncovered(window, others)` in `_WINDOW` brings a window in front of every normal window. It waits until macOS
        no longer says the window covered, through the helpers' `_until_notified`, woken by the window's occlusion
        notification (`OFF_SCREEN`). Still covered, it counts one in the way. `_UNDER` calls it after its first reading and after its last. The
        facts check's `in_front()` now calls it too.
      - `_PANNED` counts one in the way when a way that leaves the view drawn (`_PUT`'s `on_screen`) finds Designer's
        window covered once put there.
      - The not-drawn fact's detail now says "a window in the way" rather than "another app in front", since a cover
        or a locked screen counts too.
      - In the scratch run, before and after `/simplify`, with the cover, the window-under fact says "a window in the way in each of 3 tries". The
        not-drawn fact says "a window in the way in each try: on screen, partly covered". With nothing in the way, the
        window-under fact, the AppKit facts check and both halves of the not-drawn fact pass, in one try each. With the
        transparent reading made opaque (scratch only), the window-under fact fails once and says nothing of a window
        in the way.
    - **Also covered:**
      - After the window-under fact's last reading, the windows in front aren't listed. Right after the show,
        CoreGraphics still listed the main window in front of the window under it, 3 of 3, while AppKit's order had it
        behind. A first version listed them there and counted the main window in every try of the clean run.
      - The click fact (`_HITS`) sees a cover through its click reading, which reaches a window at any level
        (TST-417's note). The facts check is TST-516.
  - Questioned by TST-521, TST-522, TST-523 and TST-524 (2026-11-17).

- [x] **TST-523 · The not-drawn fact's count during the pan doesn't count a cover** · follows TST-520, generation 2 ·
  `tests/test_all_tools/editor_panels_and_fit/window_states.py:426` · confirmed · found 2026-11-17
  - **Defect.** `_PANNED` counts the windows in front twice, before the pan and after its first drag, as TST-417 has
    each reading do. TST-520 added the cover (`[-1] if way in on_screen and mac.covered()`) to the first count only.
    The second is `others += in_front_of(mac)`.
  - **Scenario.** The screen locks, or a window above every normal one comes over Designer's, during the pan of a way
    that leaves the view drawn. The view stops drawing, so `SAME=True`, with `IN_FRONT 0`: the way isn't read again,
    and nothing says why. The window is narrow: a cover that comes within the pan and stays.
  - **Fix.** The same term in the second count. The facts check (`_NOTIFIED`) counts nothing during its changes, and
    isn't part of this: a cover then can't be told apart from what that check measures.
  - **Resolution: done.**
    - **Test:** `test_a_way_that_leaves_the_view_drawn_still_covered_reads_as_one_in_the_way_at_each_count` runs both of
      the pan's counts. The second (`others += in_front_of(mac)`) failed for the three drawn ways with Designer's
      window covered. In the scratch run, an always-on-top window coming right after the first count (scratch only)
      failed the not-drawn fact's half in front of the user's windows with no retry and no reason: "render unchanged
      by a pan: on screen True, partly covered True".
    - **Cause:** TST-520 added the cover to the first count only.
    - **Fix:** both counts call `in_the_way()`, defined in `_PANNED`. In the scratch run, the same cover is said: "a
      window in the way in each try: on screen, partly covered".

- [x] **TST-524 · `uncovered` waits on `OFF_SCREEN` for a window becoming visible, which nothing measures** · follows
  TST-520, generation 2 · `tests/test_all_tools/editor_panels_and_fit/window_states.py:85-94`,
  `mcp_server/designer_helpers/mac_window.py:41-43` · confirmed · found 2026-11-17
  - **Defect.** `uncovered` waits for `on_screen(number) and not covered()` after `orderFrontRegardless`, woken by
    `OFF_SCREEN`. Its comment says "woken by its occlusion changes". The facts check reads `OFF_SCREEN` only after a
    minimize or a hide, so that direction is unmeasured. ROADMAP item 101 says the facts check "re-measures the
    notifications observed". `OFF_SCREEN`'s own comment calls it the notifications of the window unlisted, measured
    for the shot's waits. Found by two reviewers.
  - **Scenario.** The occlusion notification comes before `occlusionState` changes, or not at all for a window brought
    in front: the wait then ends on `_until`'s 100 ms poll, and nothing says so. A maintainer trimming `OFF_SCREEN` to
    what the shot needs would do the same silently. The wait stays correct either way.
  - **Fix.** Measure it: a reading in `_NOTIFIED` with Designer's window covered whole by a window of its own, then
    `first(OFF_SCREEN, mac.show, lambda: not mac.covered())`, added to `READINGS` and its waits test. Or narrow the
    comment to what is measured.
  - **Resolution: done.**
    - **Test:** `READINGS` gained `('OFF_SCREEN', 'mac.show')`. Its case failed: no reading of it. The waits-side test
      now also pins `uncovered`'s `window.show()` and `_until_notified(window, ..., OFF_SCREEN)`. The facts check's
      expected readings gained `uncovered=True`, which it lacked in the scratch run.
    - **Fix:** the facts check puts Designer's main window behind every window, under a window of its own covering it
      whole, waits until macOS says it covered, then reads `first(OFF_SCREEN, mac.show, lambda: not mac.covered())` and
      closes the cover. It read `uncovered=True` in 4 of 4 scratch runs, one try each. `shot3d.py`'s docstring records
      it with the other counts. `OFF_SCREEN`'s comment says what each use looks for.

- [x] **TST-525 · Texts on the branch say more than the code does, or other than what it does** · follows TST-519,
  generation 2 · `ROADMAP.md:81`, `ROADMAP.md:140`, `tests/unit/test_shot3d.py:611-615`,
  `tests/test_all_tools/editor_panels_and_fit/window_states.py:531-532` · confirmed · found 2026-11-17
  - **Defect.**
    - ROADMAP item 101: "The self-test's waits after it hides, shows or minimizes Designer itself look as these come
      too". Two hide waits observe no notification. `_HIDDEN_MID_ZOOM` waits `until(lambda: not exposed())`, and the
      frames check waits `_until(frames.off_screen, SETTLE_LIMIT, [frames._exposed.fired])`. Qt's expose events wake
      both.
    - ROADMAP item 107: "Item 101 makes those waits callbacks". No wait is named before it.
    - `test_shot3d.py`'s comment copies the counts: the window minimized "3 of 3", its occlusion changed "after a
      minimize 3 of 3". `shot3d.py`'s docstring says 6 of 6 and 9 of 9 since TST-517 updated it.
    - `_NOTIFIED`'s comment: the notifications are "each made to come from rest (Designer hidden)". Only the first
      starts from rest. The minimize, un-minimize and hide steps start with Designer shown and its window in front.
  - **Scenario.** A reader takes every hide wait for one woken by AppKit, trusts counts that are out of date, or
    misjudges what each reading measured.
  - **Fix.** Narrow each text, as generation 2 allows: "The self-test's waits on macOS's hidden or minimized flag, and on
    the window unlisted once minimized"; "Item 101 wakes the shot's unhide and off-screen waits on AppKit's
    notifications"; a pointer to `shot3d.py`'s docstring instead of the copied counts; "made to come in turn, from rest
    (Designer hidden) at the start".
  - **Resolution: done.**
    - **Test:** none: texts.
    - **Fix:**
      - Item 101 names the self-test's waits it covers: for macOS's hidden or minimized flag after the self-test's own
        hide, show or minimize, for the window unlisted once it minimizes it, and for the window no longer covered once
        it brings it in front. That leaves out `_HIDDEN_MID_ZOOM`'s and the frames check's waits on exposure, and
        `_READ`, which follows a shot.
      - Item 107: "Item 101 wakes the shot's unhide and off-screen waits on AppKit's notifications".
      - `test_shot3d.py`'s comment, and `test_mac_window.py`'s copy of one count, point to `shot3d.py`'s docstring.
      - `_NOTIFIED`'s comment: "made to come in turn, from rest (Designer hidden) at the start".

- [x] **TST-526 · The unit tests of AppKit's notifications can't see the callback CoreFoundation is given, nor
  `_until_notified`'s `signals`** · `tests/unit/appkit_fakes.py:36-41`, `tests/unit/test_mac_window.py:150-167` ·
  confirmed · found 2026-11-17
  - **Defect.**
    - The faked center checks only `callback is not None` and records nothing of it.
    - Every unit test calls `_until_notified` without `signals`. Only HIDE (`common.py`) and ADD_MATERIAL
      (`checks.py`) pass one (`[spy.fired]`), and no unit test runs them.
  - **Scenario.**
    - `open()` passes a temporary `NOTICE(self.fired.emit)` instead of the held `self._callback`. The callback is freed
      after the call, and the next notification would crash Designer. A callback that doesn't emit `fired` passes too.
      Every unit test passes either way.
    - `[fired, *signals]` changed to `[fired]`. HIDE's wake on Qt's expose event is lost, and the wait ends on the poll.
      Every unit test passes.
  - **Fix.** The faked center records the callback. A test asserts that it is `made._callback`, calls it with five
    ints, and asserts that the relay's `emit` got them. In the wake test, pass an extra signal and assert
    `signals == [fired, extra]`.
  - **Resolution: done.**
    - **Test:** `test_corefoundation_is_given_the_callback_the_notices_hold_and_it_relays_what_comes`: the faked center
      now records each callback. The test asserts each is `made._callback`, calls it with five pointers, and asserts
      the relay's `emit` got them. The wake test now passes a signal and asserts it follows `fired`. Both passed on the
      code. On scratch mutations they failed: a `NOTICE(self.fired.emit)` made for the call in `open()`, and
      `[fired, *signals]` changed to `[fired]`.
    - **Fix:** the tests, and `Center.callbacks` in `appkit_fakes.py`.
