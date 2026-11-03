"""Runs inside Designer: how many nodes the graph has. ARGS: graph."""

from typing import Any

import sd

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

print('NODES=%d' % len(g.getNodes()))
