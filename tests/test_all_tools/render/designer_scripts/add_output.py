"""Runs inside Designer: adds an output node with this identifier and prints its id after label. ARGS: graph,
identifier, label."""

from typing import Any

import sd
from sd.api.sdvaluestring import SDValueString

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

o = g.newNode('sbs::compositing::output')
o.setAnnotationPropertyValueFromId('identifier', SDValueString.sNew(ARGS['identifier']))
print(ARGS['label'] + '=' + o.getIdentifier())
