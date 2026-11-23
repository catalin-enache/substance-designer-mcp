"""Runs inside Designer: what the Parameters panel shows as scene items of the graph view are selected with
setSelected, and once their package is unloaded (checks.py, the designer facts of the Parameters panel), in a package of
its own. ARGS: graph, the self-test's graph, which the script turns the panel to at the end.

Items are selected as select_items.py selects them, since the API can't select (GUIDE.md, Designer UI). Each case
reads the panel's title after one processEvents() pass. A probe reading it in the next call, after Designer's own event
loop had run, read the same (measured 2026-11-23). The title is what the panel shows: a graph's identifier for a graph
(screenshots.py, the docks). The cases run twice:
- from the panel showing the graph in the editor;
- from the panel showing the package's other graph, which the Explorer's selection turns it to. From there, a switch to
  the item selected and a switch back to the editor's graph both show.

One line per case: `<name> | editor=<the editor's graph> scene=<items selected> panel=<the panel's title>`. Then the
script opens its graph again and unloads its package: the panel stays on that graph, and the script prints `the package
unloaded | panel=<the panel's title>`. It then selects the self-test's graph in the Explorer, which turns the panel to
it, and prints `panel left | <the panel's title>`. Never parentItem() (GUIDE.md, Designer UI)."""

from typing import TypedDict, cast

import sd
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QDockWidget, QGraphicsItem, QGraphicsScene, QGraphicsView, QMainWindow
from sd.api.qtforpythonuimgrwrapper import QtForPythonUIMgrWrapper
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import float2
from sd.api.sdgraphobjectcomment import SDGraphObjectComment
from sd.api.sdgraphobjectframe import SDGraphObjectFrame
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
mw = cast(QMainWindow, ui.getMainWindow())  # kept referenced while its docks are used (GUIDE.md, Designer UI)
selftest = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)
panel = next(w for w in mw.findChildren(QDockWidget) if w.objectName().startswith('areaC_'))


def scene() -> QGraphicsScene:
    """The scene of the graph view in the editor (select_items.py)."""
    dock = next(w for w in mw.findChildren(QDockWidget) if w.objectName().startswith('areaB_') and w.isVisible())
    views = [v for v in dock.findChildren(QGraphicsView) if v.isVisible()]
    return max(views, key=lambda v: v.width() * v.height()).scene()


def highest_then_smallest(i: QGraphicsItem) -> tuple[float, float]:
    rect = i.sceneBoundingRect()
    return i.zValue(), -rect.width() * rect.height()


def item_at(s: QGraphicsScene, x: float, y: float) -> QGraphicsItem:
    """The selectable item holding (x, y), the highest in z, then the smallest (select_items.py)."""
    held = [
        i
        for i in s.items()
        if i.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable and i.sceneBoundingRect().contains(QPointF(x, y))
    ]
    assert held, 'no item at %s,%s' % (x, y)
    return max(held, key=highest_then_smallest)


def settle() -> None:
    """One processEvents() pass."""
    cast(QApplication, QApplication.instance()).processEvents()


def read(case: str) -> None:
    """Prints the case's line after one processEvents() pass."""
    settle()
    current = ui.getCurrentGraph()
    print(
        '%s | editor=%s scene=%d panel=%s'
        % (case, current.getIdentifier() if current else None, len(scene().selectedItems()), panel.windowTitle())
    )


def cases(start: str) -> None:
    """Selects a node, a Dot, a frame and a comment, each alone, then none, reading the panel after each."""
    for what, x, y in [('a node', -200, 0), ('a dot', -300, 300), ('a frame', -698, -398), ('a comment', 302, -298)]:
        s = scene()
        s.clearSelection()
        item_at(s, x, y).setSelected(True)
        read('%s, %s' % (start, what))
    scene().clearSelection()
    read('%s, cleared' % start)


pkg = pm.newUserPackage()
try:
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_panel')
    g.newNode('sbs::compositing::levels').setPosition(float2(-200, 0))
    g.newNode('sbs::compositing::passthrough').setPosition(float2(-300, 300))
    frame = SDGraphObjectFrame.sNew(g)
    frame.setTitle('Empty')
    frame.setPosition(float2(-700, -400))
    frame.setSize(float2(200, 150))
    SDGraphObjectComment.sNew(g).setPosition(float2(300, -300))
    other = SDSBSCompGraph.sNew(pkg)
    other.setIdentifier('mcp_selftest_panel_other')
    editor.openResourceInEditor(g)
    read('the graph opened')
    cases('from the graph')
    editor.setExplorerSelection(other)
    read('the other graph selected in the Explorer')
    cases('from the other graph')
    editor.openResourceInEditor(g)  # the panel on the graph in the editor as its package is unloaded
finally:
    pm.unloadUserPackage(pkg)
    settle()
    unloaded = panel.windowTitle()
    editor.setExplorerSelection(selftest)  # the panel off the package unloaded (the module docstring)
settle()
print('the package unloaded | panel=%s' % unloaded)
print('panel left | %s' % panel.windowTitle())
