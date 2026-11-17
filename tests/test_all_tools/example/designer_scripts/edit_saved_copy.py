"""Runs inside Designer: saves a copy of the package, loads it and edits it, leaving a modified decoy open. ARGS:
graph, path."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdpackagemgr import SDPackageMgr


class Args(TypedDict):
    graph: str
    path: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

pm.saveCopyOfPackageAs(g.getPackage(), ARGS['path'])
copy = pm.loadUserPackage(ARGS['path'])
cast(SDSBSCompGraph, copy.getChildrenResources(False)[0]).newNode('sbs::compositing::blur')
print('DECOY_MODIFIED=%s' % copy.isModified())
