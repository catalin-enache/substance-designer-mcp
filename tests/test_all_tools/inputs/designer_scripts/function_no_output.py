"""Runs inside Designer: gives a node's levelouthigh a function reading stub_in, with no output node. ARGS: graph,
node."""

from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdvaluestring import SDValueString

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

n = g.getNodeFromId(ARGS['node'])
get = n.newPropertyGraph(n.getPropertyFromId('levelouthigh', SDPropertyCategory.Input), 'SDSBSFunctionGraph').newNode(
    'sbs::function::get_float4'
)
get.setInputPropertyValueFromId('__constant__', SDValueString.sNew('stub_in'))
