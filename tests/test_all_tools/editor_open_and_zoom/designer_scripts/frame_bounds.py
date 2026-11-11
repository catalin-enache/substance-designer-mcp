"""Runs inside Designer: the corners of the frame titled Shape. ARGS: graph."""

from typing import Any

import sd
from sd.api.sdgraphobjectframe import SDGraphObjectFrame

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

f = next(o for o in g.getGraphObjects() if isinstance(o, SDGraphObjectFrame) and o.getTitle() == 'Shape')
p, s = f.getPosition(), f.getSize()
print('FRAME=%d,%d,%d,%d' % (p.x, p.y, p.x + s.x, p.y + s.y))
