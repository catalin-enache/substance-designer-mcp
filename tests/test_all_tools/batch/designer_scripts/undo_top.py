"""Runs inside Designer, sent by sd_run outside any undo group: the newest step of the toolbar's Undo dropdown, as the
rollback reads it (mcp_server/designer_rollback.py, imported as it is now), and the self-test graph's node count.
Prints TOP=<the step's name as JSON, null with none> and NODES=<the count>."""

import json
import os
import sys
from typing import cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdpackagemgr import SDPackageMgr

GRAPH = 'mcp_selftest'  # common.TEST_GRAPH
MCP_SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), *['..'] * 4, 'mcp_server')

# The file as it is now, not as a run before had it. What sys.modules held under its name is put back after.
found = sys.modules.pop('designer_rollback', None)
sys.path.insert(0, MCP_SERVER)
try:
    import designer_rollback
finally:
    sys.path.remove(MCP_SERVER)
    if found is None:
        sys.modules.pop('designer_rollback', None)
    else:
        sys.modules['designer_rollback'] = found

history = designer_rollback.history()
if history is None:
    raise RuntimeError("no Undo and Redo dropdowns of Designer's history found")
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == GRAPH),
)
print('TOP=' + json.dumps(designer_rollback._top(history.undo)))
print('NODES=%d' % len(g.getNodes()))
del history  # the toolbar's wrappers it holds, before this job's scope goes (history_facts.py)
