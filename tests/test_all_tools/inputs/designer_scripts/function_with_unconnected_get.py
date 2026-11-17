"""Runs inside Designer: gives a node's leveloutlow a function reading stub_wired twice through an add node, its
output, plus a get node of stub_orphan connected to nothing (checks.py). ARGS: graph, node."""

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
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)
n = cast(SDNode, g.getNodeFromId(ARGS['node']))
fg = cast(
    SDGraph,
    n.newPropertyGraph(
        cast(SDProperty, n.getPropertyFromId('leveloutlow', SDPropertyCategory.Input)), 'SDSBSFunctionGraph'
    ),
)


def get(name: str) -> SDNode:
    k: SDNode = fg.newNode('sbs::function::get_float4')
    k.setInputPropertyValueFromId('__constant__', SDValueString.sNew(name))
    return k


add: SDNode = fg.newNode('sbs::function::add')
get('stub_wired').newPropertyConnectionFromId('unique_filter_output', add, 'a')
get('stub_wired').newPropertyConnectionFromId('unique_filter_output', add, 'b')
get('stub_orphan')
fg.setOutputNode(add, True)
