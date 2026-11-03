"""Runs inside Designer: a Value Processor and a Pixel Processor whose whole function is one get of this input.
ARGS: graph, input_id."""

from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdtypefloat4 import SDTypeFloat4
from sd.api.sdvaluestring import SDValueString

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

g.newProperty(ARGS['input_id'], SDTypeFloat4.sNew(), SDPropertyCategory.Input)
ids = []
for definition, param in (('valueprocessor', 'function'), ('pixelprocessor', 'perpixel')):
    node = g.newNode('sbs::compositing::' + definition)
    ids.append(node.getIdentifier())
    function = node.newPropertyGraph(node.getPropertyFromId(param, SDPropertyCategory.Input), 'SDSBSFunctionGraph')
    get = function.newNode('sbs::function::get_float4')
    get.setInputPropertyValueFromId('__constant__', SDValueString.sNew(ARGS['input_id']))
    function.setOutputNode(get, True)
print('PROCESSORS=' + ','.join(ids))
