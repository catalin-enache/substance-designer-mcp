"""Runs inside Designer: gives a node a relative $outputsize of 1, 1 and reports it. ARGS: graph, node."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sbs.sdsbscompnode import SDSBSCompNode
from sd.api.sdbasetypes import int2
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdvalueint2 import SDValueInt2


class Args(TypedDict):
    graph: str
    node: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

n = cast(SDSBSCompNode, g.getNodeFromId(ARGS['node']))
p = cast(SDProperty, n.getPropertyFromId('$outputsize', SDPropertyCategory.Input))
n.setPropertyInheritanceMethod(p, SDPropertyInheritanceMethod.RelativeToParent)
n.setPropertyValue(p, SDValueInt2.sNew(int2(1, 1)))
v = cast(SDValueInt2, n.getPropertyValue(p)).get()
print('INHERIT=%s VALUE=%d,%d' % (n.getPropertyInheritanceMethod(p).name, v.x, v.y))
