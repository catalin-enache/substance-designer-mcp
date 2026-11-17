"""Runs inside Designer: saves a copy of the graph with its $randomseed Absolute. Changing the inheritance resets the
value, so the value goes back after it (checks.py). ARGS: graph, path."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdvalueint import SDValueInt


class Args(TypedDict):
    graph: str
    path: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)
prop = cast(SDProperty, g.getPropertyFromId('$randomseed', SDPropertyCategory.Input))
kept = cast(SDValueInt, g.getPropertyValue(prop)).get()
g.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
try:
    pm.saveCopyOfPackageAs(g.getPackage(), ARGS['path'])
finally:
    g.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.RelativeToParent)
    g.setPropertyValue(prop, SDValueInt.sNew(kept))
