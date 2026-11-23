"""Runs inside Designer: what the UI manager's selection getters give (checks.py, the designer facts of the editor's
selection), in a package of its own, opened in the editor and closed again. Each case selects scene items of the graph
view as select_items.py does (setSelected, as the API can't select), then reads getCurrentGraphSelectedNodes() and
getCurrentGraphSelectedObjects() at once, before any event is processed; the cases opening a graph read once its events
are. One line per case:
`CASE=<name> current=<the editor's graph> scene=<items selected> nodes=<their kinds> objects=<their classes>`. The
editor is left with no graph, which checks.py reads once the graph's view is gone.

ARGS: graph, the self-test's graph. Once its package is unloaded, the script selects that graph in the Explorer, which
turns the Parameters panel off the package without opening a graph in the editor (GUIDE.md, Designer UI), and prints
`panel left | <the panel's title>`."""

from typing import TypedDict, cast

import sd
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QDockWidget, QGraphicsItem, QGraphicsScene, QGraphicsView, QMainWindow
from sd.api.qtforpythonuimgrwrapper import QtForPythonUIMgrWrapper
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import float2
from sd.api.sdgraphobjectcomment import SDGraphObjectComment
from sd.api.sdgraphobjectframe import SDGraphObjectFrame
from sd.api.sdgraphobjectpin import SDGraphObjectPin
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sduimgr import SDUIMgr


class Args(TypedDict):
    graph: str


ARGS: Args = globals()['ARGS']
app = sd.getContext().getSDApplication()
pm: SDPackageMgr = app.getPackageMgr()
# sd's getQtForPythonUIMgr() has no annotations; it, getUIMgr() and getMainWindow() give None only without Designer's UI
ui: QtForPythonUIMgrWrapper = app.getQtForPythonUIMgr()
editor = cast(SDUIMgr, app.getUIMgr())
mw = cast(QMainWindow, ui.getMainWindow())  # kept referenced while its view is used (GUIDE.md, Designer UI)
panel = next(w for w in mw.findChildren(QDockWidget) if w.objectName().startswith('areaC_'))
selftest = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)


def scene() -> QGraphicsScene:
    """The scene of the graph view in the editor, found again each time: opening another graph makes a new view."""
    cast(QApplication, QApplication.instance()).processEvents()
    dock = next(w for w in mw.findChildren(QDockWidget) if w.objectName().startswith('areaB_') and w.isVisible())
    views = [v for v in dock.findChildren(QGraphicsView) if v.isVisible()]
    return max(views, key=lambda v: v.width() * v.height()).scene()


def highest_then_smallest(i: QGraphicsItem) -> tuple[float, float]:
    rect = i.sceneBoundingRect()
    return i.zValue(), -rect.width() * rect.height()


def item_at(s: QGraphicsScene, x: float, y: float, z: float | None = None) -> QGraphicsItem:
    """The selectable item holding (x, y), at `z` if given, the highest in z, then the smallest (select_items.py)."""
    held = [
        i
        for i in s.items()
        if i.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        and (z is None or i.zValue() == z)
        and i.sceneBoundingRect().contains(QPointF(x, y))
    ]
    assert held, 'no item at %s,%s' % (x, y)
    return max(held, key=highest_then_smallest)


def kind(n: SDNode) -> str:
    definition = n.getDefinition()
    return definition.getId().split('::')[-1] if definition is not None else '?'


def read(case: str, s: QGraphicsScene) -> None:
    """Prints the case's line: what the getters give, read at once, and what `s` selects."""
    current = ui.getCurrentGraph()
    nodes, objects = ui.getCurrentGraphSelectedNodes(), ui.getCurrentGraphSelectedObjects()
    print(
        'CASE=%s current=%s scene=%d nodes=%s objects=%s'
        % (
            case,
            current.getIdentifier() if current else None,
            len(s.selectedItems()),
            None if nodes is None else sorted(kind(n) for n in nodes),
            None if objects is None else sorted(type(o).__name__ for o in objects),
        )
    )


def select(case: str, *points: tuple[float, float], z: float | None = None) -> None:
    """Selects the items at `points`, at `z` if given, alone, then reads the getters."""
    s = scene()
    s.clearSelection()
    for x, y in points:
        item_at(s, x, y, z).setSelected(True)
    read(case, s)


pkg = pm.newUserPackage()
try:
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_selection')
    made: dict[str, SDNode] = {}
    for name, x, y in [('uniform', -400, 0), ('levels', -200, 0), ('blur', 0, 0), ('passthrough', -300, 300)]:
        made[name] = g.newNode('sbs::compositing::' + name)
        made[name].setPosition(float2(x, y))
    made['uniform'].newPropertyConnectionFromId('unique_filter_output', made['levels'], 'input1')
    frame = SDGraphObjectFrame.sNew(g)
    frame.setTitle('Empty')
    frame.setPosition(float2(-700, -400))
    frame.setSize(float2(200, 150))
    SDGraphObjectComment.sNew(g).setPosition(float2(300, -300))
    SDGraphObjectComment.sNewAsChild(made['blur']).setDescription('on the blur')
    SDGraphObjectPin.sNew(g).setPosition(float2(300, 300))
    other = SDSBSCompGraph.sNew(pkg)
    other.setIdentifier('mcp_selftest_selection_other')
    other.newNode('sbs::compositing::uniform').setPosition(float2(0, 0))
    editor.openResourceInEditor(g)
    select('none')
    select('two nodes', (-400, 0), (-200, 0))
    select('a dot', (-300, 300))
    select('a frame', (-698, -398))
    select('a comment', (302, -298))
    select("a node's comment", (2, 2), z=-100)
    select('a pin', (300, 300))
    select('a link', (-300, 0))
    select('one node', (-400, 0))
    editor.openResourceInEditor(g)  # the graph in the editor, opened again
    read('the same graph opened again', scene())
    editor.openResourceInEditor(other)
    read('another graph opened', scene())
    select('a node selected in it', (0, 0))
    editor.openResourceInEditor(g)
    read('the first opened again', scene())
finally:
    pm.unloadUserPackage(pkg)
    editor.setExplorerSelection(selftest)  # the panel off the package unloaded (the module docstring)
cast(QApplication, QApplication.instance()).processEvents()
print('panel left | %s' % panel.windowTitle())
