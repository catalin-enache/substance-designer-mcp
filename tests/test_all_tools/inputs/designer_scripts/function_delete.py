"""Runs inside Designer: deletes the function on a node's levelinmid. ARGS: graph, node."""

from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

n = g.getNodeFromId(ARGS['node'])
n.deletePropertyGraph(n.getPropertyFromId('levelinmid', SDPropertyCategory.Input))
print('function removed')
