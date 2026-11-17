"""Runs inside Designer: adds a graph input and an FX-Map whose pattern size reads it, the only thing that does.
ARGS: graph, input_id."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdgraph import SDGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory
from sd.api.sdtypefloat2 import SDTypeFloat2
from sd.api.sdvaluestring import SDValueString


class Args(TypedDict):
    graph: str
    input_id: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

g.newProperty(ARGS['input_id'], SDTypeFloat2.sNew(), SDPropertyCategory.Input)
fx: SDNode = g.newNode('sbs::compositing::fxmaps')
paramset = cast(SDGraph, fx.getReferencedResource()).getNodes()[0]
function = cast(
    SDGraph,
    paramset.newPropertyGraph(
        cast(SDProperty, paramset.getPropertyFromId('patternsize', SDPropertyCategory.Input)), 'SDSBSFunctionGraph'
    ),
)
get: SDNode = function.newNode('sbs::function::get_float2')
get.setInputPropertyValueFromId('__constant__', SDValueString.sNew(ARGS['input_id']))
function.setOutputNode(get, True)
print('FX=' + fx.getIdentifier())
