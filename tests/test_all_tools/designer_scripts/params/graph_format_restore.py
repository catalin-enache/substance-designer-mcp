"""Runs inside Designer: puts the graph's $format back: 8 bits, relative to parent. ARGS: graph."""

from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdvalueenum import SDValueEnum

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

p = g.getPropertyFromId('$format', SDPropertyCategory.Input)
g.setPropertyValue(p, SDValueEnum.sFromValueId(p.getType().getId(), '8_bits_per_channel'))
g.setPropertyInheritanceMethod(p, SDPropertyInheritanceMethod.RelativeToParent)
print('INHERIT=' + str(g.getPropertyInheritanceMethod(p)).split('.')[-1])
