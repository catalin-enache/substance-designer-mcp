"""Runs inside Designer: gives a node a relative $outputsize of 1, 1 and reports it. ARGS: graph, node."""

from typing import Any

import sd
from sd.api.sdbasetypes import int2
from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdvalueint2 import SDValueInt2

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

n = g.getNodeFromId(ARGS['node'])
p = n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)
n.setPropertyInheritanceMethod(p, SDPropertyInheritanceMethod.RelativeToParent)
n.setPropertyValue(p, SDValueInt2.sNew(int2(1, 1)))
v = n.getPropertyValue(p).get()
print('INHERIT=%s VALUE=%d,%d' % (n.getPropertyInheritanceMethod(p).name, v.x, v.y))
