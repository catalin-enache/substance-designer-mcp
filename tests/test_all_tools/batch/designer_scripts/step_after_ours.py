"""Runs inside Designer, sent by sd_run outside any undo group: a call's undo step that failed, then a step of Designer's
own on top of it (an API call outside a group is a step of its own), then the rollback of the call
(mcp_server/designer_rollback.py, imported as it is now), the call's step named with a tag as the server's are
(project_constants.py, new_tag). It must leave both, as the step on top isn't the call's.
Prints STATE=<the rollback's state>, ADDED=<the call's node> <the other step's node> and LEFT=<1 or 0 for each: still in
the graph>."""

import os
import sys
from typing import cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdhistoryutils import SDHistoryUtils
from sd.api.sdpackagemgr import SDPackageMgr

GRAPH = 'mcp_selftest'  # common.TEST_GRAPH
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

pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == GRAPH),
)
label = 'self-test: a failed call' + new_tag()
ids: list[str] = []
try:
    with SDHistoryUtils.UndoGroup(label):
        ids.append(g.newNode('sbs::compositing::uniform').getIdentifier())
        raise RuntimeError('the call failed')
except RuntimeError:
    ids.append(g.newNode('sbs::compositing::blur').getIdentifier())  # outside any group: a step of its own, on top
    print('STATE=' + designer_rollback.roll_back(label, 60))
print('ADDED=' + ' '.join(ids))
print('LEFT=' + ' '.join('1' if g.getNodeFromId(i) is not None else '0' for i in ids))
