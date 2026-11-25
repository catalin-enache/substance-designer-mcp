"""Runs inside Designer, sent by sd_run outside any undo group: Designer's history as the rollback of a failed call reads
and waits on it (mcp_server/designer_rollback.py, imported as it is now). Two packages of its own, each with a graph
named starting mcp_selftest, and a step in each, named with a tag as the server's calls' steps are (project_constants.py,
new_tag). The Undo dropdown is read right after each step's group commits, before any event is processed. Then the
script's last step is undone through the history manager's undo() slot, as the rollback does, only while it is the
dropdown's top: otherwise the script raises, naming the top step, and undoes nothing. The undo is waited for in a
QEventLoop limited by a 60 s timer and woken by the rollback's own filter on both dropdowns. The packages are unloaded
after. Prints, as JSON:
- NAMES=<the two names given>;
- AT_COMMIT=<the top step's name after each commit>;
- TOP_TWO=<the two newest names after both>;
- WOKEN=<whether Qt says the slot was called, the times the loop woke, the limit still running once the undo landed,
  the Redo top>."""

import json
import os
import sys

import sd
from PySide6.QtCore import QEventLoop, QTimer
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdhistoryutils import SDHistoryUtils
from sd.api.sdpackage import SDPackage
from sd.api.sdpackagemgr import SDPackageMgr

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), *['..'] * 4)
MCP_SERVER = os.path.join(ROOT, 'mcp_server')

# The files as they are now, not as a run before had them. What sys.modules held under their names is put back after.
found = {name: sys.modules.pop(name, None) for name in ('designer_rollback', 'project_constants')}
sys.path.insert(0, MCP_SERVER)
sys.path.insert(0, ROOT)
try:
    import designer_rollback

    from project_constants import new_tag
finally:
    sys.path.remove(ROOT)
    sys.path.remove(MCP_SERVER)
    for name, module in found.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module

history = designer_rollback.history()
if history is None:
    raise RuntimeError("no Undo and Redo dropdowns of Designer's history found")
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
packages: list[SDPackage] = []
names: list[str] = []
at_commit: list[str | None] = []
try:
    graphs: list[SDSBSCompGraph] = []
    for which in ('a', 'b'):
        packages.append(pm.newUserPackage())
        graph = SDSBSCompGraph.sNew(packages[-1])
        graph.setIdentifier('mcp_selftest_history_' + which)
        graphs.append(graph)
    for graph in graphs:
        names.append('self-test: a step in %s%s' % (graph.getIdentifier(), new_tag()))
        with SDHistoryUtils.UndoGroup(names[-1]):
            graph.newNode('sbs::compositing::uniform')
        at_commit.append(designer_rollback._top(history.undo))
    print('NAMES=' + json.dumps(names))
    print('AT_COMMIT=' + json.dumps(at_commit))
    print('TOP_TWO=' + json.dumps([action.text() for action in history.undo.actions()][:2]))
    top = designer_rollback._top(history.undo)
    if top != names[-1]:  # an undo only of a top step of the script's own (the live-check skill, How a probe runs)
        raise RuntimeError("the top step is %r, not the script's last" % top)
    loop = QEventLoop()
    woken = designer_rollback._Changed(loop)
    limit = QTimer()
    limit.setSingleShot(True)
    limit.timeout.connect(loop.quit)
    for menu in (history.undo, history.redo):
        menu.installEventFilter(woken)
    try:
        limit.start(60000)
        called = history.slot.invoke(history.manager)
        wakes = 0
        while called and designer_rollback._top(history.redo) != names[-1] and limit.isActive():
            if loop.exec(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents) < 0:
                break
            wakes += 1
        redo_top = designer_rollback._top(history.redo)
        said = {'called': called, 'wakes': wakes, 'limit_running': limit.isActive(), 'redo_top': redo_top}
        print('WOKEN=' + json.dumps(said))
    finally:
        limit.stop()
        for menu in (history.undo, history.redo):
            menu.removeEventFilter(woken)
finally:
    for package in packages:
        pm.unloadUserPackage(package)
    # Drops `history`, with the toolbar's button and action wrappers it holds, before this job's scope goes. A function
    # defined here would keep that scope, in a cycle, until Python's cyclic collector runs.
    del history
