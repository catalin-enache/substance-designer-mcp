"""Runs inside Designer: saves a widget capture of the 3D view, or says there is no 3D view. ARGS: path."""

from typing import TypedDict, cast

import sd
from PySide6.QtWidgets import QDockWidget, QMainWindow, QWidget
from sd.api.qtforpythonuimgrwrapper import QtForPythonUIMgrWrapper


class Args(TypedDict):
    path: str


ARGS: Args = globals()['ARGS']

ui: QtForPythonUIMgrWrapper = sd.getContext().getSDApplication().getQtForPythonUIMgr()  # type: ignore[no-untyped-call]
mw = cast(QMainWindow, ui.getMainWindow())  # None only without Designer's UI
d = [d for d in mw.findChildren(QDockWidget) if d.objectName().startswith('areaD_') and d.isVisible()]
# className() is a str: PySide's stubs say bytes
vp: list[QWidget] = (
    [w for w in d[0].findChildren(QWidget) if cast(str, w.metaObject().className()) == 'Alg::Gui3D::ViewportWidget']
    if d
    else []
)
# on lines of their own: a traceback shows the failing line, and checks.py reads this token
if vp:
    print('SAVED=%s' % vp[0].grab().save(ARGS['path']))
else:
    print('NO_3D_VIEW')
