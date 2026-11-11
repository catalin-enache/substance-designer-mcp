"""Runs inside Designer: whether the graph's $randomseed changes a node's pixels and repeats, within a tolerance
(GUIDE.md), and its inheritance. A temporary output, removed even if it fails (REVIEW.md TST-38, TST-53). ARGS:
graph, node."""

import array
import ctypes
from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdvalueint import SDValueInt

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)


def pixels(t: Any) -> array.array[int]:
    """Only 8- and 16-bit integer formats, where a tolerance in steps means something (REVIEW.md TST-54, TST-56)."""
    fmt = str(t.getPixelFormat()).split('.')[-1]
    if not fmt.endswith(('8', '16')):
        raise RuntimeError('pixels(): %s is not an 8- or 16-bit integer format' % fmt)
    w, h, pitch, bpp = t.getSize().x, t.getSize().y, t.getRowPitch(), t.getBytesPerPixel()
    raw = ctypes.string_at(t.getPixelBufferAddress(), pitch * h)
    rows = b''.join(raw[y * pitch : y * pitch + w * bpp] for y in range(h))
    return array.array('H' if fmt.endswith('16') else 'B', rows)


def apart(a: array.array[int], b: array.array[int]) -> int:
    return max(abs(x - y) for x, y in zip(a, b, strict=False))


p = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)
n = g.getNodeFromId(ARGS['node'])
out = n.getProperties(SDPropertyCategory.Output)[0]


def look(seed: int) -> array.array[int]:
    g.setPropertyValue(p, SDValueInt.sNew(seed))
    g.compute()
    return pixels(n.getPropertyValue(out).get())


o = None
try:
    o = g.newNode('sbs::compositing::output')
    n.newPropertyConnectionFromId(out.getId(), o, 'inputNodeOutput')
    looks = [look(s) for s in (0, 3, 3)]
finally:
    if o is not None:
        g.deleteNode(o)
inherit = str(g.getPropertyInheritanceMethod(p)).split('.')[-1]
print('DIFFERS=%s REPEATS=%s INHERIT=%s' % (apart(looks[0], looks[1]) > 8, apart(looks[1], looks[2]) <= 8, inherit))
