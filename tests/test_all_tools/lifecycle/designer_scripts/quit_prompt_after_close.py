"""Runs inside Designer: closing the main window shows another window, as a prompt would: accepting its close, for
Designer quitting once the quit helper has closed both, and refusing it, for the helper seeing that it doesn't (checks.py). ARGS:
prompt_marker, a file that gets whether the window shows; normal_quit, a file written if the application emits
aboutToQuit; refuse, whether the prompt ignores Close."""

import sys
from typing import Any, cast

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QLabel

ARGS: dict[str, Any] = globals()['ARGS']


class _Refuse(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Close:
            event.ignore()
            return True
        return False


class _PromptAfterClose(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Close:
            prompt = QLabel('sd_mcp self-test: a prompt after closing')
            if ARGS['refuse']:
                prompt.installEventFilter(refuse)
            vars(sys)['_selftest_prompt'] = prompt  # outlives this handler
            prompt.show()
            with open(ARGS['prompt_marker'], 'w') as f:
                f.write(str(prompt.isVisible()))
        return False


def _about_to_quit() -> None:
    with open(ARGS['normal_quit'], 'w'):
        pass


app = cast(QApplication, QApplication.instance())
refuse = _Refuse()
prompt_filter = _PromptAfterClose()
vars(sys)['_selftest_prompt_filters'] = (refuse, prompt_filter)  # outlive this script
app.aboutToQuit.connect(_about_to_quit)
for w in app.topLevelWidgets():
    if w.isVisible() and cast(str, w.metaObject().className()) == 'QStackedWidget':
        w.installEventFilter(prompt_filter)
