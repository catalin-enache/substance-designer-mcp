"""Runs inside Designer: saves a copy of the graph's package, loads that and saves a copy of it. ARGS: graph, first, second."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdpackagemgr import SDPackageMgr


class Args(TypedDict):
    graph: str
    first: str
    second: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

pm.saveCopyOfPackageAs(g.getPackage(), ARGS['first'])
copy = pm.loadUserPackage(ARGS['first'])
try:
    pm.saveCopyOfPackageAs(copy, ARGS['second'])
finally:
    pm.unloadUserPackage(copy)
