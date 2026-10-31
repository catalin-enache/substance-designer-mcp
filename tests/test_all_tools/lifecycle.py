"""Quitting and starting Designer, at the end of a run in a Designer the self-test started (nothing of
yours can be lost there): quit_designer's fallback and slow shutdowns, launch_designer again."""

import os
import subprocess
import sys
import time
from pathlib import Path

from .common import Ctx, check, crash_dumps, designer_alive, new_crash_dumps, text


async def run(ctx: Ctx) -> None:
    c, scratch = ctx.c, ctx.scratch
    # our own instance: nothing of the user's can be lost. First make the window
    # ignore Close (as a blocking dialog would): quit_designer must time out, then
    # its fallback ends Designer anyway, without a crash (REVIEW.md PLG-8: the
    # earlier exit() fallback crashed Designer's teardown, twice)
    dumps_before = crash_dumps()
    forced_marker = os.path.join(scratch, 'forced_quit_about_to_quit')
    await c(
        'execute_designer_code',
        {
            'code': (
                'import sys\nfrom PySide6.QtCore import QObject, QEvent\nfrom PySide6.QtWidgets import QApplication\n'
                'class _KeepOpen(QObject):\n    def eventFilter(self, obj, event):\n'
                '        if event.type() == QEvent.Type.Close:\n            event.ignore()\n            return True\n'
                '        return False\n'
                'sys._selftest_keep_open = _KeepOpen()\n'
                'for w in QApplication.instance().topLevelWidgets():\n'
                '    if w.isVisible(): w.installEventFilter(sys._selftest_keep_open)\n'
                "QApplication.instance().aboutToQuit.connect(lambda: open(%r, 'w').close())\n"
                "print('ignoring Close')"
            )
            % forced_marker
        },
    )
    r_ = await c('quit_designer', {'discard_unsaved': True, 'wait_s': 2})
    check(
        'quit_designer',
        'times out when the window stays open',
        r_.is_error and 'still running after 2s' in text(r_),
        text(r_),
    )
    deadline = time.time() + 30
    while time.time() < deadline and not (await c('designer_status')).is_error:
        time.sleep(1)
    time.sleep(3)
    gone = (await c('designer_status')).is_error
    if sys.platform != 'win32':
        gone = (
            gone
            and subprocess.run(
                ['pgrep', '-f', 'MacOS/Adobe Substance 3D Designer( |$)'], capture_output=True
            ).returncode
            != 0
        )
    new_dumps = new_crash_dumps(dumps_before)
    check(
        'quit_designer',
        'fallback ends it anyway, without a crash',
        gone and not new_dumps,
        'gone=%s, new crash dumps: %s' % (gone, sorted(new_dumps)),
    )
    # ...through os._exit, which never emits aboutToQuit: what tells a forced quit from a
    # normal one in the check below (REVIEW.md TST-25)
    check(
        'designer facts',
        'a forced quit (os._exit) never emits aboutToQuit',
        gone and not os.path.exists(forced_marker),
        'marker written: %s' % os.path.exists(forced_marker),
    )
    t = text(await c('launch_designer', {'wait_s': 240}))
    check('launch_designer', 'starts again after a quit', 'Designer started in' in t and 'ERROR' not in t, t)
    prompt_marker = os.path.join(scratch, 'prompt_shown')
    # a window shown while the main window closes (a prompt appearing then) doesn't keep
    # Designer alive: it quits once its main window has closed (REVIEW.md HLP-19, measured).
    # A quit by itself emits aboutToQuit, which writes a marker; the fallback's os._exit
    # (here at about 5 s, as the prompt stays visible) never does (REVIEW.md TST-25)
    normal_quit = os.path.join(scratch, 'quit_normally')
    await c(
        'execute_designer_code',
        {
            'code': (
                'import sys\nfrom PySide6.QtCore import QObject, QEvent, QTimer\n'
                'from PySide6.QtWidgets import QApplication, QLabel\n'
                'def _prompt():\n'
                "    sys._selftest_prompt = QLabel('sd_mcp self-test: a prompt after closing')\n"
                '    sys._selftest_prompt.show()\n'
                'class _PromptAfterClose(QObject):\n    def eventFilter(self, obj, event):\n'
                '        if event.type() == QEvent.Type.Close:\n            _prompt()\n'
                "            open(%r, 'w').write(str(sys._selftest_prompt.isVisible()))\n"
                '        return False\n'
                'sys._selftest_prompt_filter = _PromptAfterClose()\n'
                "QApplication.instance().aboutToQuit.connect(lambda: open(%r, 'w').close())\n"
                'for w in QApplication.instance().topLevelWidgets():\n'
                "    if w.isVisible() and w.metaObject().className() == 'QStackedWidget':\n"
                '        w.installEventFilter(sys._selftest_prompt_filter)'
            )
            % (prompt_marker, normal_quit)
        },
    )
    dumps_before, quit_started = crash_dumps(), time.time()
    await c('quit_designer', {'discard_unsaved': True, 'wait_s': 2})
    while time.time() - quit_started < 60 and designer_alive():
        time.sleep(1)
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
    check('launch_designer', 'starts again after a forced quit', 'Designer started in' in t and 'ERROR' not in t, t)
    # a slow normal shutdown must be left to finish, not killed by the os._exit
    # fallback: 7 s of work in the window's close handler (HLP-17), then 7 s in an
    # aboutToQuit handler (HLP-12) that shows a window, so only the fallback's
    # "every window had closed" test can keep the process alive (TST-19, TST-23).
    # Both keep processing events past the fallback's 5 s. No modal dialog here: with
    # one open as well, Designer once didn't go on to quit and stayed without a window
    # (REVIEW.md HLP-23; not reproduced on demand: hiding the main window instead of
    # closing it still quits in 2 s)
    slow_close = os.path.join(scratch, 'slow_close_finished')
    slow_marker = os.path.join(scratch, 'slow_shutdown_finished')
    await c(
        'execute_designer_code',
        {
            'code': (
                'import sys, time\nfrom PySide6.QtCore import QObject, QEvent\n'
                'from PySide6.QtWidgets import QApplication, QLabel\n'
                'def _busy(seconds):\n    started = time.time()\n'
                '    while time.time() - started < seconds:\n'
                '        QApplication.processEvents()\n        time.sleep(0.05)\n'
                'class _SlowClose(QObject):\n    def eventFilter(self, obj, event):\n'
                "        if event.type() == QEvent.Type.Close and not getattr(self, 'done', False):\n"
                "            self.done = True\n            _busy(7)\n            open(%r, 'w').close()\n"
                '        return False\n'
                'def _slow_shutdown():\n'
                "    sys._selftest_label = QLabel('sd_mcp self-test: slow shutdown')\n"
                "    sys._selftest_label.show()\n    _busy(7)\n    open(%r, 'w').close()\n"
                'sys._selftest_slow_close = _SlowClose()\n'
                'for w in QApplication.instance().topLevelWidgets():\n'
                "    if w.isVisible() and w.metaObject().className() == 'QStackedWidget':\n"
                '        w.installEventFilter(sys._selftest_slow_close)\n'
                'sys._selftest_slow_shutdown = _slow_shutdown\n'
                'QApplication.instance().aboutToQuit.connect(_slow_shutdown)'
            )
            % (slow_close, slow_marker)
        },
    )
    dumps_before = crash_dumps()
    t = text(await c('quit_designer', {'discard_unsaved': True}))
    gone = (await c('designer_status')).is_error
    new_dumps = new_crash_dumps(dumps_before)  # a dump is written seconds later (REVIEW.md TST-17)
    closed, finished = os.path.exists(slow_close), os.path.exists(slow_marker)
    check(
        'quit_designer',
        'a slow close handler is left to finish',
        closed,
        'its 7 s close handler finished'
        if closed
        else 'the close handler did not finish: the process was ended under it',
    )
    check(
        'quit_designer',
        'a slow shutdown with a window showing is left to finish',
        finished and 'Designer quit after' in t and gone and not new_dumps,
        ('its 7 s aboutToQuit handler finished' if finished else 'the aboutToQuit handler did not finish')
        + ' | '
        + t.strip()[-80:],
    )
    t = text(await c('launch_designer', {'wait_s': 240}))
    check('launch_designer', 'starts again after a slow quit', 'Designer started in' in t and 'ERROR' not in t, t)
    # the realistic blocker: a modal dialog (its own event loop) must not stop quitting
    await c(
        'execute_designer_code',
        {
            'code': (
                'from PySide6.QtCore import QTimer\nfrom PySide6.QtWidgets import QMessageBox\n'
                "QTimer.singleShot(0, lambda: QMessageBox.information(None, 'sd_mcp self-test', "
                "'A modal dialog; quit_designer must still close Designer.'))"
            )
        },
    )
    time.sleep(1)
    modal = text(
        await c(
            'execute_designer_code',
            {
                'code': (
                    'from PySide6.QtWidgets import QApplication\n'
                    "print('MODAL=' + type(QApplication.instance().activeModalWidget()).__name__)"
                )
            },
        )
    )
    dumps_before = crash_dumps()
    t = text(await c('quit_designer', {'discard_unsaved': True}))
    gone = (await c('designer_status')).is_error
    new_dumps = new_crash_dumps(dumps_before)
    check(
        'quit_designer',
        'closes the Designer it started, with a modal dialog open, without a crash',
        'MODAL=QMessageBox' in modal and 'Designer quit after' in t and gone and not new_dumps,
        modal + t + (' new crash dumps: %s' % sorted(new_dumps) if new_dumps else ''),
    )
