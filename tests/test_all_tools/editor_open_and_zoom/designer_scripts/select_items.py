"""Runs inside Designer: selects nodes and frames of the graph in the editor through its graph view's scene items, as a
person's click would, since the API can't select (GUIDE.md, Designer UI). ARGS: nodes (ids) and frames (titles); none
of either clears the selection. Prints the count of scene items selected.

An item is found by a point it holds, the highest in z first (measured: nodes, Dots and pins are at 0, a link at -64,
frames and comments at -100), so a node's centre finds its own item before the frame's around it. A frame is found by
a point just inside its top-left corner. selection_facts.py measures that each item so found is the one selected.
Never parentItem() (GUIDE.md, Designer UI)."""

from typing import TypedDict, cast

import sd
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QDockWidget, QGraphicsItem, QGraphicsView, QMainWindow
from sd.api.qtforpythonuimgrwrapper import QtForPythonUIMgrWrapper
from sd.api.sdgraphobjectframe import SDGraphObjectFrame


class Args(TypedDict):
    nodes: list[str]
    frames: list[str]


ARGS: Args = globals()['ARGS']
# sd's getQtForPythonUIMgr() has no annotations. It and getMainWindow() give None only without Designer's UI.
ui: QtForPythonUIMgrWrapper = sd.getContext().getSDApplication().getQtForPythonUIMgr()
mw = cast(QMainWindow, ui.getMainWindow())  # kept referenced while its view is used (GUIDE.md, Designer UI)
g = ui.getCurrentGraph()
assert g is not None, 'no graph in the editor'
dock = next(w for w in mw.findChildren(QDockWidget) if w.objectName().startswith('areaB_') and w.isVisible())


def area(view: QGraphicsView) -> int:
    return view.width() * view.height()


scene = max((v for v in dock.findChildren(QGraphicsView) if v.isVisible()), key=area).scene()
items = [i for i in scene.items() if i.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable]


def highest_then_smallest(i: QGraphicsItem) -> tuple[float, float]:
    rect = i.sceneBoundingRect()
    return i.zValue(), -rect.width() * rect.height()


def item_at(x: float, y: float) -> QGraphicsItem:
    """The selectable item holding (x, y), the highest in z, then the smallest."""
    held = [i for i in items if i.sceneBoundingRect().contains(QPointF(x, y))]
    assert held, 'no item at %s,%s' % (x, y)
    return max(held, key=highest_then_smallest)


scene.clearSelection()
for node_id in ARGS['nodes']:
    node = g.getNodeFromId(node_id)
    assert node is not None, 'no node %s' % node_id
    position = node.getPosition()
    item_at(position.x, position.y).setSelected(True)
for title in ARGS['frames']:
    frame = next(o for o in g.getGraphObjects() if isinstance(o, SDGraphObjectFrame) and o.getTitle() == title)
    corner = frame.getPosition()
    item_at(corner.x + 2, corner.y + 2).setSelected(True)
print('SELECTED=%d' % len(scene.selectedItems()))
