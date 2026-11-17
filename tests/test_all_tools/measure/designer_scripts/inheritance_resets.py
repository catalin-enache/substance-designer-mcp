"""Runs inside Designer: changing a parameter's inheritance doesn't keep its value, each switch on its own, on a node
and on the graph (GUIDE.md; checks.py). Everything is put back. ARGS: graph, node."""

from collections.abc import Callable
from typing import TypedDict, TypeVar, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sbs.sdsbscompnode import SDSBSCompNode
from sd.api.sdbasetypes import int2
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdvalue import SDValue
from sd.api.sdvalueint import SDValueInt
from sd.api.sdvalueint2 import SDValueInt2

V = TypeVar('V', bound=SDValue)  # the class of the value set, which the value read back has too
R = TypeVar('R')  # what resets()' read makes of it


class Args(TypedDict):
    graph: str
    node: str


ARGS: Args = globals()['ARGS']
IM = SDPropertyInheritanceMethod
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)


def resets(
    target: SDSBSCompNode | SDSBSCompGraph,
    pid: str,
    value: V,
    read: Callable[[V], R],
    start: SDPropertyInheritanceMethod,
) -> list[R]:
    p = cast(SDProperty, target.getPropertyFromId(pid, SDPropertyCategory.Input))
    was = target.getPropertyInheritanceMethod(p)
    kept = cast(SDValue, target.getPropertyValue(p))
    seen: list[R] = []
    try:  # put back even if a call fails, for the later checks (REVIEW.md TST-46)
        for there, back in ((start, IM.Absolute), (IM.Absolute, start)):
            target.setPropertyInheritanceMethod(p, there)
            target.setPropertyValue(p, value)
            target.setPropertyInheritanceMethod(p, back)
            seen.append(read(cast(V, target.getPropertyValue(p))))
    finally:
        target.setPropertyInheritanceMethod(p, was)
        target.setPropertyValue(p, kept)
    return seen


n = cast(SDSBSCompNode, g.getNodeFromId(ARGS['node']))
print(
    'NODE_SIZE=%s'
    % resets(n, '$outputsize', SDValueInt2.sNew(int2(1, 1)), lambda v: ((s := v.get()).x, s.y), IM.RelativeToParent)
)
print('GRAPH_SEED=%s' % resets(g, '$randomseed', SDValueInt.sNew(5), lambda v: v.get(), IM.RelativeToParent))
