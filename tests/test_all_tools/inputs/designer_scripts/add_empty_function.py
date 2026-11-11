"""Runs inside Designer: adds an empty function to a node's levelouthigh, and reports its nodes and the stored value.
ARGS: graph, node."""

from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

n = g.getNodeFromId(ARGS['node'])
p = n.getPropertyFromId('levelouthigh', SDPropertyCategory.Input)
n.newPropertyGraph(p, 'SDSBSFunctionGraph')
v = n.getPropertyValue(p).get()
print(
    'EMPTY_FUNCTION nodes=%d value=%s'
    % (len(n.getPropertyGraph(p).getNodes()), tuple(round(x, 3) for x in (v.x, v.y, v.z, v.w)))
)
