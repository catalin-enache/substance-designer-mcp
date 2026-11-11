"""Runs inside Designer: an output node's first usage. ARGS: graph, node."""

from typing import Any

import sd

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

n = g.getNodeFromId(ARGS['node'])
u = n.getAnnotationPropertyValueFromId('usages').get()[0].get()
print('USAGE=%s %s %s' % (u.getName(), u.getComponents(), u.getColorSpace()))
