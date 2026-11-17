"""Runs inside Designer: a Value Processor and a Pixel Processor whose whole function is one get of this input.
ARGS: graph, input_id."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdgraph import SDGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory
from sd.api.sdtypefloat4 import SDTypeFloat4
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

g.newProperty(ARGS['input_id'], SDTypeFloat4.sNew(), SDPropertyCategory.Input)
ids = []
for definition, param in (('valueprocessor', 'function'), ('pixelprocessor', 'perpixel')):
    node: SDNode = g.newNode('sbs::compositing::' + definition)
    ids.append(node.getIdentifier())
    function = cast(
        SDGraph,
        node.newPropertyGraph(
            cast(SDProperty, node.getPropertyFromId(param, SDPropertyCategory.Input)), 'SDSBSFunctionGraph'
        ),
    )
    get: SDNode = function.newNode('sbs::function::get_float4')
    get.setInputPropertyValueFromId('__constant__', SDValueString.sNew(ARGS['input_id']))
    function.setOutputNode(get, True)
print('PROCESSORS=' + ','.join(ids))
