"""Runs inside Designer: a $randomseed's inheritance and value, on a node or (with no node) the graph; absolute makes
it Absolute first, restore makes it inherited and sets this value. ARGS: graph, node (optional), absolute
(optional), restore (optional)."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sbs.sdsbscompnode import SDSBSCompNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod as IM
from sd.api.sdvalueint import SDValueInt


class _Graph(TypedDict):
    graph: str


class Args(_Graph, total=False):
    node: str
    absolute: bool
    restore: int


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

n = cast(SDSBSCompNode, g.getNodeFromId(ARGS['node'])) if ARGS.get('node') else g
p = cast(SDProperty, n.getPropertyFromId('$randomseed', SDPropertyCategory.Input))
if ARGS.get('absolute'):
    n.setPropertyInheritanceMethod(p, IM.Absolute)
if 'restore' in ARGS:
    n.setPropertyInheritanceMethod(p, IM.RelativeToParent)
    n.setPropertyValue(p, SDValueInt.sNew(ARGS['restore']))
print('INHERIT=%s VALUE=%s' % (n.getPropertyInheritanceMethod(p).name, cast(SDValueInt, n.getPropertyValue(p)).get()))
