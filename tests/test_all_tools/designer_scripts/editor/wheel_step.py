"""Runs inside Designer: one wheel step on the graph view, for the zoom it continues from (editor.py)."""

from typing import Any, cast

import sd
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QDockWidget, QGraphicsView

ui: Any = sd.getContext().getSDApplication().getQtForPythonUIMgr()  # type: ignore[no-untyped-call]
mw = ui.getMainWindow()
d = next(w for w in mw.findChildren(QDockWidget) if w.objectName().startswith('areaB_') and w.isVisible())


def area(view: QGraphicsView) -> int:
    return view.width() * view.height()


v: QGraphicsView = max((x for x in d.findChildren(QGraphicsView) if x.isVisible()), key=area)
vp = v.viewport()
c = QPointF(vp.width() / 2, vp.height() / 2)
before = v.transform().m11()
QApplication.sendEvent(
    vp,
    QWheelEvent(
        c,
        QPointF(vp.mapToGlobal(c.toPoint())),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    ),
)
cast(QApplication, QApplication.instance()).processEvents()
print('STEP=%.4f' % (v.transform().m11() / before))
