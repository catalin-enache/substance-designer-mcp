"""Runs inside Designer: who owns a node's scene item after parentItem() on its comment's item (checks.py, the designer
facts of parentItem; GUIDE.md, Designer UI), in a package of its own, opened in the editor and closed again.

The wrapper parentItem() gives is invalidated at once, which leaves the item Designer's, and the count of node items
after a garbage collection says it stayed. Before parentItem(), the comment's item is only read for finding it
(flags(), zValue(), sceneBoundingRect()). The script doesn't call topLevelItem() on it: after topLevelItem(),
parentItem() left the node's item Designer's (measured 2026-11-23). Prints `owned | before=<bool> after=<bool>`, whether
Python owns the node's item before and after parentItem(), and `node items | before=<n> after=<n>`.

ARGS: graph, the self-test's graph. Once its package is unloaded, the script selects that graph in the Explorer, which
turns the Parameters panel off the package (GUIDE.md, Designer UI), and prints `panel left | <the panel's title>`."""

import gc
from typing import TypedDict, cast

import sd
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QDockWidget, QGraphicsItem, QGraphicsScene, QGraphicsView, QMainWindow
from sd.api.qtforpythonuimgrwrapper import QtForPythonUIMgrWrapper
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import float2
from sd.api.sdgraphobjectcomment import SDGraphObjectComment
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sduimgr import SDUIMgr
from shiboken6 import Shiboken


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


def graph_scene() -> QGraphicsScene:
    """The scene of the graph view in the editor (select_items.py)."""
    cast(QApplication, QApplication.instance()).processEvents()
    dock = next(w for w in mw.findChildren(QDockWidget) if w.objectName().startswith('areaB_') and w.isVisible())
    return max(
        (v for v in dock.findChildren(QGraphicsView) if v.isVisible()), key=lambda v: v.width() * v.height()
    ).scene()


def items_at(scene: QGraphicsScene, x: float, y: float, z: float) -> list[QGraphicsItem]:
    """The selectable items of `scene` holding (x, y), at `z`."""
    return [
        i
        for i in scene.items()
        if i.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        and i.zValue() == z
        and i.sceneBoundingRect().contains(QPointF(x, y))
    ]


def node_items(scene: QGraphicsScene) -> int:
    """The count of node items: nodes are at z 0, along the y 0 row here."""
    return len(items_at(scene, -300, 0, 0.0)) + len(items_at(scene, 0, 0, 0.0))


pkg = pm.newUserPackage()
try:
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_parent_item')
    g.newNode('sbs::compositing::levels').setPosition(float2(-300, 0))
    blur = g.newNode('sbs::compositing::blur')
    blur.setPosition(float2(0, 0))
    SDGraphObjectComment.sNewAsChild(blur).setDescription('on the blur')
    editor.openResourceInEditor(g)
    scene = graph_scene()
    before = node_items(scene)
    node, comment = items_at(scene, 0, 0, 0.0)[0], items_at(scene, 2, 2, -100.0)[0]
    owned_before = Shiboken.ownedByPython(node)
    parent = comment.parentItem()
    try:
        owned_after = Shiboken.ownedByPython(node)
    finally:
        if parent is not None:  # whatever happened: a wrapper left owning the item would delete it
            Shiboken.invalidate(parent)  # the item Designer's again
    print('owned | before=%s after=%s' % (owned_before, owned_after))
    del node, comment, parent
    gc.collect()
    print('node items | before=%d after=%d' % (before, node_items(scene)))
finally:
    pm.unloadUserPackage(pkg)
    editor.setExplorerSelection(selftest)  # the panel off the package unloaded (the module docstring)
cast(QApplication, QApplication.instance()).processEvents()
print('panel left | %s' % panel.windowTitle())
