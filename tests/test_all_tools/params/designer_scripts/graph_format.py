"""Runs inside Designer: what a generator computes at under the graph's $format; set_16_bits sets the value first. A
temporary uniform and output, removed even if it fails (REVIEW.md TST-49). ARGS: graph, set_16_bits (optional)."""

from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdvalueenum import SDValueEnum

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

p = g.getPropertyFromId('$format', SDPropertyCategory.Input)
if ARGS.get('set_16_bits'):
    g.setPropertyValue(p, SDValueEnum.sFromValueId(p.getType().getId(), '16_bits_per_channel'))
u = g.newNode('sbs::compositing::uniform')
o = g.newNode('sbs::compositing::output')
u.newPropertyConnectionFromId('unique_filter_output', o, 'inputNodeOutput')
try:
    g.compute()
    t = u.getPropertyValue(u.getPropertyFromId('unique_filter_output', SDPropertyCategory.Output)).get()
    print('FORMAT=' + str(t.getPixelFormat()).split('.')[-1])
finally:
    g.deleteNode(u)
    g.deleteNode(o)
print('INHERIT=' + str(g.getPropertyInheritanceMethod(p)).split('.')[-1])
