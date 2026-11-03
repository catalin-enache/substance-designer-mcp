"""Runs inside Designer: saves a copy of the package with this graph $randomseed stored; the value goes back after.
ARGS: graph, seed, path."""

from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdvalueint import SDValueInt

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

p = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)
kept = g.getPropertyValue(p).get()
g.setPropertyValue(p, SDValueInt.sNew(ARGS['seed']))
try:
    pm.saveCopyOfPackageAs(g.getPackage(), ARGS['path'])
finally:
    g.setPropertyValue(p, SDValueInt.sNew(kept))
