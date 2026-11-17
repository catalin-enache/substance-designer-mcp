"""Runs inside Designer: saves a copy of the package with a node's $randomseed Absolute; it goes back after. ARGS:
graph, node, path."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sbs.sdsbscompnode import SDSBSCompNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdvalueint import SDValueInt


class Args(TypedDict):
    graph: str
    node: str
    path: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

n = cast(SDSBSCompNode, g.getNodeFromId(ARGS['node']))
p = cast(SDProperty, n.getPropertyFromId('$randomseed', SDPropertyCategory.Input))
was, kept = n.getPropertyInheritanceMethod(p), cast(SDValueInt, n.getPropertyValue(p)).get()
try:
    n.setPropertyInheritanceMethod(p, SDPropertyInheritanceMethod.Absolute)
    pm.saveCopyOfPackageAs(g.getPackage(), ARGS['path'])
finally:
    n.setPropertyInheritanceMethod(p, was)
    n.setPropertyValue(p, SDValueInt.sNew(kept))
