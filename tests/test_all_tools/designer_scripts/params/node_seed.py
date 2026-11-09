"""Runs inside Designer: a node's $randomseed, inherited (added to the graph's) and Absolute (no longer following it),
compared in pixels, within a tolerance (GUIDE.md; params.py). Everything is put back. ARGS: graph, node."""

import array
import ctypes
from typing import Any

import sd
from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdvalueint import SDValueInt

ARGS: dict[str, Any] = globals()['ARGS']
IM = SDPropertyInheritanceMethod
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


n = g.getNodeFromId(ARGS['node'])
out = n.getProperties(SDPropertyCategory.Output)[0]
gp = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)
np_ = n.getPropertyFromId('$randomseed', SDPropertyCategory.Input)
kept = (g.getPropertyValue(gp).get(), n.getPropertyInheritanceMethod(np_), n.getPropertyValue(np_).get())


def look(inherit: SDPropertyInheritanceMethod, graph_seed: int, node_seed: int) -> array.array[int]:
    n.setPropertyInheritanceMethod(np_, inherit)
    g.setPropertyValue(gp, SDValueInt.sNew(graph_seed))
    n.setPropertyValue(np_, SDValueInt.sNew(node_seed))
    g.compute()
    return pixels(n.getPropertyValue(out).get())


o = None
try:  # the output node inside the try too (REVIEW.md TST-53)
    o = g.newNode('sbs::compositing::output')
    n.newPropertyConnectionFromId(out.getId(), o, 'inputNodeOutput')
    r03 = look(IM.RelativeToParent, 0, 3)
    near = max(apart(r03, look(IM.RelativeToParent, 3, 0)), apart(r03, look(IM.RelativeToParent, 1, 2)))
    counts = apart(r03, look(IM.RelativeToParent, 0, 0))
    a0 = look(IM.Absolute, 0, 0)
    follows = apart(a0, look(IM.Absolute, 3, 0))
finally:
    if o is not None:
        g.deleteNode(o)
    n.setPropertyInheritanceMethod(np_, kept[1])
    n.setPropertyValue(np_, SDValueInt.sNew(kept[2]))
    g.setPropertyValue(gp, SDValueInt.sNew(kept[0]))
print('ADDED_WITHIN=%d VALUE_COUNTS_BY=%d ABSOLUTE_MOVES_WITH_GRAPH_BY=%d' % (near, counts, follows))
