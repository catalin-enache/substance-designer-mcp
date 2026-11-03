"""Runs inside Designer: the sizes of the graph view and its dock, in device pixels (editor.py)."""

from typing import cast

from PySide6.QtWidgets import QApplication, QDockWidget, QGraphicsView, QWidget


def graph_dock(w: QWidget) -> bool:
    # a dead wrapper raises, now or on its children: skip it (AGENTS.md, Designer UI)
    try:
        return (
            isinstance(w, QDockWidget)
            and w.objectName().startswith('areaB_')
            and w.isVisible()
            and bool(w.findChildren(QGraphicsView))
        )
    except RuntimeError:
        return False


d = next(w for w in cast(QApplication, QApplication.instance()).allWidgets() if graph_dock(w))


def area(view: QGraphicsView) -> int:
    return view.width() * view.height()


v: QGraphicsView = max((x for x in d.findChildren(QGraphicsView) if x.isVisible()), key=area)
r = v.devicePixelRatioF()
print(
    'VIEW=%d,%d DOCK=%d,%d' % (round(v.width() * r), round(v.height() * r), round(d.width() * r), round(d.height() * r))
)
