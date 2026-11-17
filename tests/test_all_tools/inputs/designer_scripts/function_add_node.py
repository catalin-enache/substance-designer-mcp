"""Runs inside Designer: adds a node to the function on a node's levelinmid. ARGS: graph, node."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdgraph import SDGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory


class Args(TypedDict):
    graph: str
    node: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

n = cast(SDNode, g.getNodeFromId(ARGS['node']))
function = n.getPropertyGraph(cast(SDProperty, n.getPropertyFromId('levelinmid', SDPropertyCategory.Input)))
cast(SDGraph, function).newNode('sbs::function::const_float1')
print('extra node')
