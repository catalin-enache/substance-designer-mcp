"""Runs inside Designer: gives a node's levelinhigh a function whose output reads this name, which is no graph input.
ARGS: graph, node, name."""

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
function = n.newPropertyGraph(n.getPropertyFromId('levelinhigh', SDPropertyCategory.Input), 'SDSBSFunctionGraph')
get = function.newNode('sbs::function::get_float4')
get.setInputPropertyValueFromId('__constant__', SDValueString.sNew(ARGS['name']))
function.setOutputNode(get, True)
