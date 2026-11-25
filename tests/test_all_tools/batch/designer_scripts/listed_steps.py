"""Runs inside Designer, sent by sd_run outside any undo group: how many steps the toolbar's Undo dropdown lists, as
undo_edits reads it (mcp_server/designer_rollback.py, imported as it is now). A package of its own, with a graph named
starting mcp_selftest, and one more step in it than designer_rollback.LISTED, each named with a tag as the server's
calls' steps are (project_constants.py, new_tag). The dropdown is read, then its top step is undone with the shared
function every undo goes through (undo_steps), and the dropdown is read again. The package is unloaded after. Prints,
as JSON, LISTED=<the most the code counts on, the steps listed before and after the undo, whether the first step made
was listed before and after it, and the undo's state>."""

import json
import os
import sys

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdhistoryutils import SDHistoryUtils
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
package = pm.newUserPackage()
try:
    graph = SDSBSCompGraph.sNew(package)
    graph.setIdentifier('mcp_selftest_listed')
    names = ['self-test: listed step %d%s' % (i, new_tag()) for i in range(designer_rollback.LISTED + 1)]
    for name in names:
        with SDHistoryUtils.UndoGroup(name):
            graph.newNode('sbs::compositing::uniform')
    before = [action.text() for action in history.undo.actions()]
    undone, state = designer_rollback.undo_steps(history, [names[-1]], 60)
    after = [action.text() for action in history.undo.actions()]
    said = {
        'most': designer_rollback.LISTED,
        'before': len(before),
        'after': len(after),
        'first_before': names[0] in before,
        'first_after': names[0] in after,
        'state': state,
    }
    print('LISTED=' + json.dumps(said))
finally:
    pm.unloadUserPackage(package)
    del history  # the toolbar's wrappers it holds, before this job's scope goes (history_facts.py)
