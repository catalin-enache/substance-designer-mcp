"""Runs inside Designer: saves a copy of the graph's package, loads that and saves a copy of it. ARGS: graph, first, second."""

from typing import Any

import sd

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

pm.saveCopyOfPackageAs(g.getPackage(), ARGS['first'])
copy: Any = pm.loadUserPackage(ARGS['first'])
try:
    pm.saveCopyOfPackageAs(copy, ARGS['second'])
finally:
    pm.unloadUserPackage(copy)
