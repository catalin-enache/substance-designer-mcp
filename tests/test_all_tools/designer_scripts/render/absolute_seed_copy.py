"""Runs inside Designer: saves a copy of the graph with its $randomseed Absolute. Changing the inheritance resets the
value, so the value goes back after it (render.py). ARGS: graph, path."""

from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdvalueint import SDValueInt

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)
prop = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)
kept = g.getPropertyValue(prop).get()
g.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
try:
    pm.saveCopyOfPackageAs(g.getPackage(), ARGS['path'])
finally:
    g.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.RelativeToParent)
    g.setPropertyValue(prop, SDValueInt.sNew(kept))
