"""Runs inside Designer: a $randomseed's inheritance and value, on a node or (with no node) the graph; absolute makes
it Absolute first, restore makes it inherited and sets this value. ARGS: graph, node (optional), absolute
(optional), restore (optional)."""

from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM
from sd.api.sdvalueint import SDValueInt

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

n = g.getNodeFromId(ARGS['node']) if ARGS.get('node') else g
p = n.getPropertyFromId('$randomseed', SDPropertyCategory.Input)
if ARGS.get('absolute'):
    n.setPropertyInheritanceMethod(p, IM.Absolute)
if 'restore' in ARGS:
    n.setPropertyInheritanceMethod(p, IM.RelativeToParent)
    n.setPropertyValue(p, SDValueInt.sNew(ARGS['restore']))
print('INHERIT=%s VALUE=%s' % (n.getPropertyInheritanceMethod(p).name, n.getPropertyValue(p).get()))
