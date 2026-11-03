"""Runs inside Designer: shows the Console panel through the Windows menu."""

from typing import cast

from PySide6.QtWidgets import QApplication, QMenu

for w in cast(QApplication, QApplication.instance()).allWidgets():
    if isinstance(w, QMenu) and w.title() == '&Windows':
        w.aboutToShow.emit()
        for a in w.actions():
            if a.text() == 'Console' and not a.isChecked():
                a.trigger()
        break
QApplication.processEvents()
