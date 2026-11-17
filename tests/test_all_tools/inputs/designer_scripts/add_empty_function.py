"""Runs inside Designer: adds an empty function to a node's levelouthigh, and reports its nodes and the stored value.
ARGS: graph, node."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdgraph import SDGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory
from sd.api.sdvaluefloat4 import SDValueFloat4


class Args(TypedDict):
    graph: str
    node: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

n = cast(SDNode, g.getNodeFromId(ARGS['node']))
p = cast(SDProperty, n.getPropertyFromId('levelouthigh', SDPropertyCategory.Input))
n.newPropertyGraph(p, 'SDSBSFunctionGraph')
v = cast(SDValueFloat4, n.getPropertyValue(p)).get()
print(
    'EMPTY_FUNCTION nodes=%d value=%s'
    % (len(cast(SDGraph, n.getPropertyGraph(p)).getNodes()), tuple(round(x, 3) for x in (v.x, v.y, v.z, v.w)))
)
