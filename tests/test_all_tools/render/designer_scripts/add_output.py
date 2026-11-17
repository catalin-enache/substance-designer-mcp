"""Runs inside Designer: adds an output node with this identifier and prints its id after label. ARGS: graph,
identifier, label."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdvaluestring import SDValueString


class Args(TypedDict):
    graph: str
    identifier: str
    label: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

o: SDNode = g.newNode('sbs::compositing::output')
o.setAnnotationPropertyValueFromId('identifier', SDValueString.sNew(ARGS['identifier']))
print(ARGS['label'] + '=' + o.getIdentifier())
