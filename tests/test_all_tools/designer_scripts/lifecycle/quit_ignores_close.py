"""Runs inside Designer: its windows ignore Close, as under a blocking dialog, for quit_designer's force-end
(lifecycle.py). ARGS: marker, a file written if the application emits aboutToQuit."""

import sys
from typing import Any, cast

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication

ARGS: dict[str, Any] = globals()['ARGS']


class _KeepOpen(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Close:
            event.ignore()
            return True
        return False


def _about_to_quit() -> None:
    with open(ARGS['marker'], 'w'):
        pass


app = cast(QApplication, QApplication.instance())
keep_open = _KeepOpen()
vars(sys)['_selftest_keep_open'] = keep_open  # outlives this script
for w in app.topLevelWidgets():
    if w.isVisible():
        w.installEventFilter(keep_open)
app.aboutToQuit.connect(_about_to_quit)
print('ignoring Close')
