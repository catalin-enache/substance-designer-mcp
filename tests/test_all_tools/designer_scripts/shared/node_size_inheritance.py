"""Runs inside Designer: a node's $outputsize inheritance and value; relative_to_input then sets it back to that. ARGS:
graph, node, relative_to_input (optional)."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sbs.sdsbscompnode import SDSBSCompNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdvalueint2 import SDValueInt2


class _Node(TypedDict):
    graph: str
    node: str


class Args(_Node, total=False):
    relative_to_input: bool


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

n = cast(SDSBSCompNode, g.getNodeFromId(ARGS['node']))
p = cast(SDProperty, n.getPropertyFromId('$outputsize', SDPropertyCategory.Input))
print('INHERIT=%s VALUE=%s' % (n.getPropertyInheritanceMethod(p).name, cast(SDValueInt2, n.getPropertyValue(p)).get()))
if ARGS.get('relative_to_input'):
    n.setPropertyInheritanceMethod(p, SDPropertyInheritanceMethod.RelativeToInput)
