"""Runs inside Designer: gives a node's leveloutlow a function reading stub_wired twice through an add node, its
output, plus a get node of stub_orphan connected to nothing (inputs.py). ARGS: graph, node."""

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
fg = n.newPropertyGraph(n.getPropertyFromId('leveloutlow', SDPropertyCategory.Input), 'SDSBSFunctionGraph')


def get(name: str) -> Any:
    k = fg.newNode('sbs::function::get_float4')
    k.setInputPropertyValueFromId('__constant__', SDValueString.sNew(name))
    return k


add = fg.newNode('sbs::function::add')
get('stub_wired').newPropertyConnectionFromId('unique_filter_output', add, 'a')
get('stub_wired').newPropertyConnectionFromId('unique_filter_output', add, 'b')
get('stub_orphan')
fg.setOutputNode(add, True)
