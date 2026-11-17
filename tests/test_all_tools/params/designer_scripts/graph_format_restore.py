"""Runs inside Designer: puts the graph's $format back: 8 bits, relative to parent. ARGS: graph."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdtype import SDType
from sd.api.sdvalueenum import SDValueEnum


class Args(TypedDict):
    graph: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

p = cast(SDProperty, g.getPropertyFromId('$format', SDPropertyCategory.Input))
g.setPropertyValue(p, SDValueEnum.sFromValueId(cast(SDType, p.getType()).getId(), '8_bits_per_channel'))
g.setPropertyInheritanceMethod(p, SDPropertyInheritanceMethod.RelativeToParent)
print('INHERIT=' + str(g.getPropertyInheritanceMethod(p)).split('.')[-1])
