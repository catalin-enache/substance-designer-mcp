"""Runs inside Designer: the graph's frame count and size settings. ARGS: graph."""

from typing import Any

import sd
from sd.api.sdgraphobjectframe import SDGraphObjectFrame
from sd.api.sdproperty import SDPropertyCategory

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

p = g.getPropertyFromId('$outputsize', SDPropertyCategory.Input)
frames = sum(isinstance(o, SDGraphObjectFrame) for o in g.getGraphObjects())
print('FRAMES=%d SIZE=%s PARENT=%d' % (frames, g.getPropertyInheritanceMethod(p).name, g.getDefaultParentSize().x))
