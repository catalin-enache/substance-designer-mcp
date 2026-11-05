"""Runs inside Designer: 7 s of work in the main window's close handler, then 7 s in an aboutToQuit handler that shows
a window, for quit_designer, which must leave both to finish within its wait (lifecycle.py). ARGS: slow_close and
slow_marker, files written when each one finishes."""

import sys
import time
from typing import Any, cast

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QLabel

ARGS: dict[str, Any] = globals()['ARGS']


def _busy(seconds: float) -> None:
    started = time.time()
    while time.time() - started < seconds:
        QApplication.processEvents()
        time.sleep(0.05)


class _SlowClose(QObject):
    done = False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Close and not self.done:
            self.done = True
            _busy(7)
            with open(ARGS['slow_close'], 'w'):
                pass
        return False


def _slow_shutdown() -> None:
    label = QLabel('sd_mcp self-test: slow shutdown')
    vars(sys)['_selftest_label'] = label  # outlives this handler
    label.show()
    _busy(7)
    with open(ARGS['slow_marker'], 'w'):
        pass


app = cast(QApplication, QApplication.instance())
slow_close = _SlowClose()
vars(sys)['_selftest_slow_close'] = slow_close  # these outlive this script
vars(sys)['_selftest_slow_shutdown'] = _slow_shutdown
for w in app.topLevelWidgets():
    if w.isVisible() and cast(str, w.metaObject().className()) == 'QStackedWidget':
        w.installEventFilter(slow_close)
app.aboutToQuit.connect(_slow_shutdown)
