"""Runs inside Designer: saves a copy of the package with this graph $randomseed stored; the value goes back after.
ARGS: graph, seed, path."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory
from sd.api.sdvalueint import SDValueInt


class Args(TypedDict):
    graph: str
    seed: int
    path: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

p = cast(SDProperty, g.getPropertyFromId('$randomseed', SDPropertyCategory.Input))
kept = cast(SDValueInt, g.getPropertyValue(p)).get()
g.setPropertyValue(p, SDValueInt.sNew(ARGS['seed']))
try:
    pm.saveCopyOfPackageAs(g.getPackage(), ARGS['path'])
finally:
    g.setPropertyValue(p, SDValueInt.sNew(kept))
