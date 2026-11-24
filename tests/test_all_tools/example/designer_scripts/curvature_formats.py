"""Runs inside Designer: for each curvature_smooth of the graph, the node feeding it, that node's inversedy as 0 or 1,
and the curvature's normal_format, a line each. ARGS: graph."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sddefinition import SDDefinition
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory
from sd.api.sdvaluebool import SDValueBool
from sd.api.sdvalueenum import SDValueEnum


class Args(TypedDict):
    graph: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

for n in g.getNodes():
    ref = n.getReferencedResource()
    if ref is None or ref.getIdentifier() != 'curvature_smooth':
        continue
    fmt = cast(SDValueEnum, n.getInputPropertyValueFromId('normal_format')).get()
    for link in n.getPropertyConnections(cast(SDProperty, n.getPropertyFromId('input', SDPropertyCategory.Input))):
        fed = cast(SDNode, link.getInputPropertyNode())  # the other node (GUIDE.md, connections from the queried side)
        inversedy = cast(SDValueBool, fed.getInputPropertyValueFromId('inversedy')).get()
        print(
            'CURVATURE fed by %s inversedy=%d normal_format=%d'
            % (cast(SDDefinition, fed.getDefinition()).getId(), inversedy, fmt)
        )
