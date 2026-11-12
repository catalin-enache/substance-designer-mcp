"""Runs inside Designer: the visible Parameters panel's title (the graph or node it shows) and the graph in the editor,
printed as PANEL=...|EDITOR=...."""

from typing import Any

import sd
from PySide6 import QtWidgets

ui: Any = sd.getContext().getSDApplication().getQtForPythonUIMgr()  # type: ignore[no-untyped-call]
mw = ui.getMainWindow()
panels = [d for d in mw.findChildren(QtWidgets.QDockWidget) if d.objectName().startswith('areaC_') and d.isVisible()]
editor = ui.getCurrentGraph()
print(
    'PANEL=%s|EDITOR=%s'
    % (panels[0].windowTitle() if panels else None, editor.getIdentifier() if editor is not None else None)
)
