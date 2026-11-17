"""Runs inside Designer: gives a node's levelinhigh a function whose output reads this name, which is no graph input.
ARGS: graph, node, name."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdgraph import SDGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory
from sd.api.sdvaluestring import SDValueString


class Args(TypedDict):
    graph: str
    node: str
    name: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

n = cast(SDNode, g.getNodeFromId(ARGS['node']))
function = cast(
    SDGraph,
    n.newPropertyGraph(
        cast(SDProperty, n.getPropertyFromId('levelinhigh', SDPropertyCategory.Input)), 'SDSBSFunctionGraph'
    ),
)
get: SDNode = function.newNode('sbs::function::get_float4')
get.setInputPropertyValueFromId('__constant__', SDValueString.sNew(ARGS['name']))
function.setOutputNode(get, True)
