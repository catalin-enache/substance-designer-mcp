"""Runs inside Designer: collapses the Explorer's row of the package holding a graph, the graph's row then hidden, and
clears the Explorer's selection. ARGS: graph."""

from typing import TypedDict, cast

import sd
from PySide6 import QtWidgets
from sd.api.qtforpythonuimgrwrapper import QtForPythonUIMgrWrapper
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdapplication import SDApplication
from sd.api.sduimgr import SDUIMgr


class Args(TypedDict):
    graph: str


ARGS: Args = globals()['ARGS']
app: SDApplication = sd.getContext().getSDApplication()  # type: ignore[no-untyped-call]
pm = app.getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)
# sd's getQtForPythonUIMgr() has no annotations. It and getMainWindow() give None only without Designer's UI.
ui: QtForPythonUIMgrWrapper = app.getQtForPythonUIMgr()  # type: ignore[no-untyped-call]
mw = cast(QtWidgets.QMainWindow, ui.getMainWindow())
explorer = next(
    d for d in mw.findChildren(QtWidgets.QDockWidget) if d.objectName().startswith('areaA_') and d.isVisible()
)
tree = next(v for v in explorer.findChildren(QtWidgets.QTreeView) if v.objectName() == 'mTreeView')
cast(SDUIMgr, app.getUIMgr()).setExplorerSelection(g)
QtWidgets.QApplication.processEvents()
package = tree.selectionModel().selectedRows()[0].parent()
tree.collapse(package)
tree.clearSelection()
QtWidgets.QApplication.processEvents()
print('COLLAPSED=%s' % (package.isValid() and not tree.isExpanded(package)))
