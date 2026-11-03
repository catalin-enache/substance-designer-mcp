"""Runs inside Designer: saves a copy of the package with a node's $randomseed Absolute; it goes back after. ARGS:
graph, node, path."""

from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdvalueint import SDValueInt

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

n = g.getNodeFromId(ARGS['node'])
p = n.getPropertyFromId('$randomseed', SDPropertyCategory.Input)
was, kept = n.getPropertyInheritanceMethod(p), n.getPropertyValue(p).get()
try:
    n.setPropertyInheritanceMethod(p, SDPropertyInheritanceMethod.Absolute)
    pm.saveCopyOfPackageAs(g.getPackage(), ARGS['path'])
finally:
    n.setPropertyInheritanceMethod(p, was)
    n.setPropertyValue(p, SDValueInt.sNew(kept))
