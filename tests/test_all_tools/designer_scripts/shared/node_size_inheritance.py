"""Runs inside Designer: a node's $outputsize inheritance and value; relative_to_input then sets it back to that. ARGS:
graph, node, relative_to_input (optional)."""

from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

n = g.getNodeFromId(ARGS['node'])
p = n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)
print('INHERIT=%s VALUE=%s' % (n.getPropertyInheritanceMethod(p).name, n.getPropertyValue(p).get()))
if ARGS.get('relative_to_input'):
    n.setPropertyInheritanceMethod(p, SDPropertyInheritanceMethod.RelativeToInput)
