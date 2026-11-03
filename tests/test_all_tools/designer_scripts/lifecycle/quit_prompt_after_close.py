"""Runs inside Designer: closing the main window shows another window, as a prompt would, for the fact that Designer
still quits (lifecycle.py). ARGS: prompt_marker, a file that gets whether the window shows; normal_quit, a file
written if the application emits aboutToQuit."""

import sys
from typing import Any, cast

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QLabel

ARGS: dict[str, Any] = globals()['ARGS']


class _PromptAfterClose(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Close:
            prompt = QLabel('sd_mcp self-test: a prompt after closing')
            vars(sys)['_selftest_prompt'] = prompt  # outlives this handler
            prompt.show()
            with open(ARGS['prompt_marker'], 'w') as f:
                f.write(str(prompt.isVisible()))
        return False


def _about_to_quit() -> None:
    with open(ARGS['normal_quit'], 'w'):
        pass


app = cast(QApplication, QApplication.instance())
prompt_filter = _PromptAfterClose()
vars(sys)['_selftest_prompt_filter'] = prompt_filter  # outlives this script
app.aboutToQuit.connect(_about_to_quit)
for w in app.topLevelWidgets():
    if w.isVisible() and cast(str, w.metaObject().className()) == 'QStackedWidget':
        w.installEventFilter(prompt_filter)
