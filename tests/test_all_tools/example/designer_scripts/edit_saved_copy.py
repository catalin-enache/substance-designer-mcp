"""Runs inside Designer: saves a copy of the package, loads it and edits it, leaving a modified decoy open. ARGS:
graph, path."""

from typing import Any

import sd

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

pm.saveCopyOfPackageAs(g.getPackage(), ARGS['path'])
copy: Any = pm.loadUserPackage(ARGS['path'])
copy.getChildrenResources(False)[0].newNode('sbs::compositing::blur')
print('DECOY_MODIFIED=%s' % copy.isModified())
