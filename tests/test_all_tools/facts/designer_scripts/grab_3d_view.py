"""Runs inside Designer: saves a widget capture of the 3D view, or says there is no 3D view. ARGS: path."""

from typing import Any

import sd
from PySide6.QtWidgets import QDockWidget, QWidget

ARGS: dict[str, Any] = globals()['ARGS']

ui: Any = sd.getContext().getSDApplication().getQtForPythonUIMgr()  # type: ignore[no-untyped-call]
mw = ui.getMainWindow()
d = [d for d in mw.findChildren(QDockWidget) if d.objectName().startswith('areaD_') and d.isVisible()]
vp: list[Any] = (
    [w for w in d[0].findChildren(QWidget) if w.metaObject().className() == 'Alg::Gui3D::ViewportWidget'] if d else []
)
# on lines of their own: a traceback shows the failing line, and checks.py reads this token
if vp:
    print('SAVED=%s' % vp[0].grab().save(ARGS['path']))
else:
    print('NO_3D_VIEW')
