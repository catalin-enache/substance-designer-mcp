"""Runs inside Designer: the graph in the editor, the count of graph views, and what the UI manager's selection getters
give or raise (checks.py, the designer facts of the editor's selection, once its graph is closed)."""

from collections.abc import Callable
from typing import cast

import sd
from sd.api.apiexception import APIException
from sd.api.qtforpythonuimgrwrapper import QtForPythonUIMgrWrapper
from sd.api.sduimgr import SDUIMgr

app = sd.getContext().getSDApplication()
# sd's getQtForPythonUIMgr() has no annotations; it and getUIMgr() give None only without Designer's UI
ui: QtForPythonUIMgrWrapper = app.getQtForPythonUIMgr()
print('CURRENT=%s VIEWS=%d' % (ui.getCurrentGraph(), cast(SDUIMgr, app.getUIMgr()).getGraphViewIDCount()))
getters: dict[str, Callable[[], object]] = {
    'getCurrentGraphSelectedNodes': ui.getCurrentGraphSelectedNodes,
    'getCurrentGraphSelectedObjects': ui.getCurrentGraphSelectedObjects,
}
for name, getter in getters.items():
    try:
        print('%s=gave %r' % (name, getter()))
    except APIException as e:
        print('%s=raised %r' % (name, e))
