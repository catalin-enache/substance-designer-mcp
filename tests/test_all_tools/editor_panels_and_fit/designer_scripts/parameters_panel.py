"""Runs inside Designer: the visible Parameters panel's title (the graph or node it shows) and the graph in the editor,
printed as PANEL=...|EDITOR=...."""

from typing import cast

import sd
from PySide6 import QtWidgets
from sd.api.qtforpythonuimgrwrapper import QtForPythonUIMgrWrapper

# sd's getQtForPythonUIMgr() has no annotations. It and getMainWindow() give None only without Designer's UI.
ui: QtForPythonUIMgrWrapper = sd.getContext().getSDApplication().getQtForPythonUIMgr()
mw = cast(QtWidgets.QMainWindow, ui.getMainWindow())
panels = [d for d in mw.findChildren(QtWidgets.QDockWidget) if d.objectName().startswith('areaC_') and d.isVisible()]
editor = ui.getCurrentGraph()
print(
    'PANEL=%s|EDITOR=%s'
    % (panels[0].windowTitle() if panels else None, editor.getIdentifier() if editor is not None else None)
)
