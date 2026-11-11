"""Runs inside Designer: hides Designer's own window, the visible QStackedWidget, and shows another top-level window, for
the quit helper's judgement of a close without Designer's own window (checks.py). Prints HIDDEN=<own windows hidden>."""

import sys
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QStackedWidget, QWidget

app = cast(QApplication, QApplication.instance())
own = [w for w in app.topLevelWidgets() if w.isVisible() and isinstance(w, QStackedWidget)]
for w in own:
    w.hide()
other = QWidget(None, Qt.WindowType.Tool)
other.show()
vars(sys)['_selftest_other_window'] = other  # kept alive
print('HIDDEN=%d' % len(own))
