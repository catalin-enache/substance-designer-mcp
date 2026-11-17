"""Runs inside Designer: gives a node's levelouthigh a function reading stub_in, with no output node. ARGS: graph,
node."""

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


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

n = cast(SDNode, g.getNodeFromId(ARGS['node']))
function = n.newPropertyGraph(
    cast(SDProperty, n.getPropertyFromId('levelouthigh', SDPropertyCategory.Input)), 'SDSBSFunctionGraph'
)
get: SDNode = cast(SDGraph, function).newNode('sbs::function::get_float4')
get.setInputPropertyValueFromId('__constant__', SDValueString.sNew('stub_in'))
