"""Runs inside Designer: changing a parameter's inheritance doesn't keep its value, each switch on its own, on a node
and on the graph (GUIDE.md; measure.py). Everything is put back. ARGS: graph, node."""

from collections.abc import Callable
from typing import Any

import sd
from sd.api.sdbasetypes import int2
from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdvalue import SDValue
from sd.api.sdvalueint import SDValueInt
from sd.api.sdvalueint2 import SDValueInt2

ARGS: dict[str, Any] = globals()['ARGS']
IM = SDPropertyInheritanceMethod
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)


def resets(
    target: Any, pid: str, value: SDValue, read: Callable[[Any], Any], start: SDPropertyInheritanceMethod
) -> Any:
    p = target.getPropertyFromId(pid, SDPropertyCategory.Input)
    was = target.getPropertyInheritanceMethod(p)
    kept = target.getPropertyValue(p)
    seen = []
    try:  # put back even if a call fails, for the later checks (REVIEW.md TST-46)
        for there, back in ((start, IM.Absolute), (IM.Absolute, start)):
            target.setPropertyInheritanceMethod(p, there)
            target.setPropertyValue(p, value)
            target.setPropertyInheritanceMethod(p, back)
            seen.append(read(target.getPropertyValue(p).get()))
    finally:
        target.setPropertyInheritanceMethod(p, was)
        target.setPropertyValue(p, kept)
    return seen


n = g.getNodeFromId(ARGS['node'])
print(
    'NODE_SIZE=%s' % resets(n, '$outputsize', SDValueInt2.sNew(int2(1, 1)), lambda v: (v.x, v.y), IM.RelativeToParent)
)
print('GRAPH_SEED=%s' % resets(g, '$randomseed', SDValueInt.sNew(5), lambda v: v, IM.RelativeToParent))
