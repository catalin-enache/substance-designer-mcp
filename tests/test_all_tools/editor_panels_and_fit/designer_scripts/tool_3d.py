"""Runs inside Designer: selects the 3D view's toolbar tool ARGS['tool'] ('Camera' or 'Light', one group; '' selects
none) and, if ARGS has 'selection', sets its Selection toggle on (True) or off (False); then prints the one selected
and the toggle, TOOL=<its name> SELECTION=<True or False>."""

from typing import Any

import sd
from PySide6 import QtWidgets

ARGS: dict[str, Any] = globals()['ARGS']
mw: Any = sd.getContext().getSDApplication().getQtForPythonUIMgr().getMainWindow()  # type: ignore[no-untyped-call]
dock = next(d for d in mw.findChildren(QtWidgets.QDockWidget) if d.objectName().startswith('areaD_') and d.isVisible())
tools = {
    a.text(): a
    for bar in dock.findChildren(QtWidgets.QToolBar)
    for a in bar.actions()
    if a.text() in ('Camera', 'Light', 'Selection')
}
if ARGS['tool']:
    tools[ARGS['tool']].trigger()
    QtWidgets.QApplication.processEvents()
if 'selection' in ARGS and tools['Selection'].isChecked() != ARGS['selection']:
    tools['Selection'].trigger()
    QtWidgets.QApplication.processEvents()
selected = ','.join(name for name in ('Camera', 'Light') if tools[name].isChecked())
print('TOOL=%s SELECTION=%s' % (selected, tools['Selection'].isChecked()))
