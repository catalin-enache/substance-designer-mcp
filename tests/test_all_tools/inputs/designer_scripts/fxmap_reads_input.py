"""Runs inside Designer: adds a graph input and an FX-Map whose pattern size reads it, the only thing that does.
ARGS: graph, input_id."""

from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdtypefloat2 import SDTypeFloat2
from sd.api.sdvaluestring import SDValueString

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

g.newProperty(ARGS['input_id'], SDTypeFloat2.sNew(), SDPropertyCategory.Input)
fx = g.newNode('sbs::compositing::fxmaps')
paramset = fx.getReferencedResource().getNodes()[0]
function = paramset.newPropertyGraph(
    paramset.getPropertyFromId('patternsize', SDPropertyCategory.Input), 'SDSBSFunctionGraph'
)
get = function.newNode('sbs::function::get_float2')
get.setInputPropertyValueFromId('__constant__', SDValueString.sNew(ARGS['input_id']))
function.setOutputNode(get, True)
print('FX=' + fx.getIdentifier())
