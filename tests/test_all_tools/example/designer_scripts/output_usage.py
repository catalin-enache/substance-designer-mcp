"""Runs inside Designer: an output node's first usage. ARGS: graph, node."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdusage import SDUsage
from sd.api.sdvaluearray import SDValueArray
from sd.api.sdvalueusage import SDValueUsage


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
usages = cast(SDValueArray, n.getAnnotationPropertyValueFromId('usages')).get()
u = cast(SDUsage, cast(SDValueUsage, usages[0]).get())
print('USAGE=%s %s %s' % (u.getName(), u.getComponents(), u.getColorSpace()))
