"""Runs inside Designer: what an empty clipboard's mimeData is. The clipboard is put back (checks.py)."""

from typing import cast

from PySide6 import QtCore, QtWidgets

app = cast(QtWidgets.QApplication, QtWidgets.QApplication.instance())
cb = app.clipboard()
orig = cb.mimeData()
backup = QtCore.QMimeData()
for f in orig.formats():
    backup.setData(f, orig.data(f))
try:
    cb.clear()
    app.processEvents()
    m = cb.mimeData()
    print('EMPTY_MIME=%s' % ('None' if m is None else len(m.formats())))
finally:
    cb.setMimeData(backup)
    app.processEvents()
