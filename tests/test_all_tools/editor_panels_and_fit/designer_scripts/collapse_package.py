"""Runs inside Designer: collapses the Explorer's row of the package holding a graph, the graph's row then hidden, and
clears the Explorer's selection. ARGS: graph."""

from typing import Any, cast

import sd
from PySide6 import QtWidgets
from sd.api.sduimgr import SDUIMgr

ARGS: dict[str, Any] = globals()['ARGS']
app: Any = sd.getContext().getSDApplication()  # type: ignore[no-untyped-call]
pm = app.getPackageMgr()
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)
mw: Any = app.getQtForPythonUIMgr().getMainWindow()
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
