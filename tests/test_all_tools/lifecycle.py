"""Quitting and starting Designer, at the end of a run in a Designer the self-test started: it is disposable. Force-ending
one that stays, what is left to finish, refusing a Designer no agent started, launch_designer again."""

import os
import time
from pathlib import Path
from textwrap import dedent

from project_constants import agent_designer_file

from .common import Ctx, check, crash_dumps, designer_alive, designer_script, new_crash_dumps, text

CLOSE_WINDOWS_ONLY = dedent("""\
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    def close_windows():
        for w in QApplication.instance().topLevelWidgets():
            if w.isVisible():
                w.close()
    QTimer.singleShot(300, close_windows)""")


async def run(ctx: Ctx) -> None:
    c, scratch = ctx.c, ctx.scratch

    # a Designer no agent started is the user's: with the record gone this one counts as that, and nothing reaches it
    record = agent_designer_file()
    check('launch_designer', 'records the Designer it started', os.path.exists(record), record)
    if not os.path.exists(record):
        return  # nothing below can run, and the run's clean-up reports the Designer left open
    kept = record + '.kept'
    os.replace(record, kept)
    try:
        status = text(await c('designer_status'))
        r_ = await c('quit_designer')
        time.sleep(2)
        refused = r_.is_error and 'ask the user to save, close and reopen' in text(r_)
        alive = not (await c('designer_status')).is_error
    finally:
        os.replace(kept, record)
    check('quit_designer', 'refuses a Designer no agent started, and it stays open', refused and alive, text(r_))
    check('designer_status', 'says when no agent started it', 'Not started by an agent' in status, status)
    status = text(await c('designer_status'))
    check('designer_status', 'says when an agent started it', 'Started by an agent' in status, status)

    # unsaved changes in an agent's Designer are dropped, and it says so
    await c('create_graph', {'name': 'mcp_selftest_unsaved_at_quit', 'size_log2': 4})
    await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels'}], 'graph': 'mcp_selftest_unsaved_at_quit'})
    dumps_before = crash_dumps()
    t = text(await c('quit_designer', {'wait_s': 30}))
    check(
        'quit_designer',
        "closes an agent's Designer with unsaved changes, dropping them",
        'discarding unsaved changes' in t and 'Designer quit after' in t and 'forced' not in t and not designer_alive(),
        t,
    )
    check('quit_designer', 'a normal close leaves no crash dump', not new_crash_dumps(dumps_before), t)
    t = text(await c('launch_designer', {'wait_s': 240}))
    check('launch_designer', 'starts again after a quit', 'Designer started in' in t and 'ERROR' not in t, t)

    # windows ignoring Close, as under a blocking dialog: past its wait it is forced, with no aboutToQuit
    dumps_before = crash_dumps()
    forced_marker = os.path.join(scratch, 'forced_quit_about_to_quit')
    await designer_script(c, 'lifecycle/quit_ignores_close', marker=forced_marker)
    t = text(await c('quit_designer', {'wait_s': 2}))
    new_dumps = new_crash_dumps(dumps_before)
    check(
        'quit_designer',
        'forces one whose window stays open, without a crash',
        'forced' in t and not designer_alive() and not new_dumps and not os.path.exists(forced_marker),
        '%s; new crash dumps: %s' % (t, sorted(new_dumps)),
    )
    t = text(await c('launch_designer', {'wait_s': 240}))
    check('launch_designer', 'starts again after a forced quit', 'Designer started in' in t and 'ERROR' not in t, t)

    # stuck at the very end of its shutdown, where nothing inside Designer can act (REVIEW.md HLP-82)
    dumps_before = crash_dumps()
    held = text(await designer_script(c, 'lifecycle/hold_thread_pool'))
    t = text(await c('quit_designer', {'wait_s': 15}))
    new_dumps = new_crash_dumps(dumps_before)
    check(
        'quit_designer',
        'forces one stuck in its shutdown, without a crash',
        'HELD=True' in held and 'forced' in t and not designer_alive() and not new_dumps,
        held + t,
    )
    t = text(await c('launch_designer', {'wait_s': 240}))
    check('launch_designer', 'starts again after a stuck shutdown', 'Designer started in' in t and 'Ended' not in t, t)

    # the same, found by launch_designer: an agent's Designer not answering isn't waited for
    await designer_script(c, 'lifecycle/hold_thread_pool')
    await c('execute_designer_code', {'code': CLOSE_WINDOWS_ONLY})
    deadline = time.time() + 30
    while time.time() < deadline and not (await c('designer_status')).is_error:
        time.sleep(1)
    t = text(await c('launch_designer', {'wait_s': 240}))
    check(
        'launch_designer',
        "ends an agent's Designer not answering, and starts a new one",
        'Ended a Designer an agent started' in t and 'Designer started in' in t,
        t,
    )

    # a window shown while the main window closes (a prompt appearing then) doesn't keep Designer alive: it quits once
    # its main window has closed (REVIEW.md HLP-19, measured). A quit by itself emits aboutToQuit, which writes a marker
    prompt_marker = os.path.join(scratch, 'prompt_shown')
    normal_quit = os.path.join(scratch, 'quit_normally')
    await designer_script(c, 'lifecycle/quit_prompt_after_close', prompt_marker=prompt_marker, normal_quit=normal_quit)
    dumps_before, quit_started = crash_dumps(), time.time()
    await c('quit_designer', {'wait_s': 60})
    took = time.time() - quit_started
    new_dumps = new_crash_dumps(dumps_before)
    check(
        'designer facts',
        'Designer quits once its main window closes, even with another window shown',
        os.path.exists(prompt_marker)
        and Path(prompt_marker).read_text() == 'True'
        and os.path.exists(normal_quit)
        and not designer_alive()
        and not new_dumps,
        'prompt shown: %s; quit by itself (aboutToQuit): %s; gone after %.0f s, new crash dumps: %s'
        % (
            Path(prompt_marker).read_text() if os.path.exists(prompt_marker) else 'no',
            os.path.exists(normal_quit),
            took,
            sorted(new_dumps),
        ),
    )
    t = text(await c('launch_designer', {'wait_s': 240}))
    check('launch_designer', 'starts again', 'Designer started in' in t and 'ERROR' not in t, t)

    # wait_s is respected: 7 s in the window's close handler, then 7 s in an aboutToQuit handler, left to finish
    slow_close = os.path.join(scratch, 'slow_close_finished')
    slow_marker = os.path.join(scratch, 'slow_shutdown_finished')
    await designer_script(c, 'lifecycle/quit_slow_shutdown', slow_close=slow_close, slow_marker=slow_marker)
    dumps_before = crash_dumps()
    t = text(await c('quit_designer', {'wait_s': 40}))
    new_dumps = new_crash_dumps(dumps_before)
    finished = os.path.exists(slow_close) and os.path.exists(slow_marker)
    check(
        'quit_designer',
        'a slow shutdown within its wait is left to finish',
        finished and 'Designer quit after' in t and 'forced' not in t and not designer_alive() and not new_dumps,
        '%s; both handlers finished: %s' % (t, finished),
    )
    t = text(await c('launch_designer', {'wait_s': 240}))
    check('launch_designer', 'starts again after a slow quit', 'Designer started in' in t and 'ERROR' not in t, t)

    # the realistic blocker: a modal dialog (its own event loop) must not stop quitting
    await designer_script(c, 'lifecycle/modal_dialog')
    time.sleep(1)
    modal = text(
        await c(
            'execute_designer_code',
            {
                'code': dedent("""\
                    from PySide6.QtWidgets import QApplication
                    print('MODAL=' + type(QApplication.instance().activeModalWidget()).__name__)""")
            },
        )
    )
    dumps_before = crash_dumps()
    t = text(await c('quit_designer', {'wait_s': 30}))
    gone = (await c('designer_status')).is_error
    new_dumps = new_crash_dumps(dumps_before)
    check(
        'quit_designer',
        'closes the Designer it started, with a modal dialog open, without a crash',
        'MODAL=QMessageBox' in modal and 'Designer quit after' in t and 'forced' not in t and gone and not new_dumps,
        modal + t + (' new crash dumps: %s' % sorted(new_dumps) if new_dumps else ''),
    )
