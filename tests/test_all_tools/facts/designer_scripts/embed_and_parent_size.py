"""Runs inside Designer: bitmaps can't be embedded, and setDefaultParentSize takes pixels (checks.py).
ARGS: graph, png."""

from typing import Any

import sd
from sd.api.apiexception import APIException
from sd.api.sdbasetypes import int2
from sd.api.sdresource import EmbedMethod
from sd.api.sdresourcebitmap import SDResourceBitmap

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)
try:
    SDResourceBitmap.sNewFromFile(g.getPackage(), ARGS['png'], EmbedMethod.BinaryEmbedded)
    print('EMBED=ok')
except APIException as e:
    print('EMBED=' + str(e))
saved = g.getDefaultParentSize()
g.setDefaultParentSize(int2(256, 256))
print('PARENT=%d' % g.getDefaultParentSize().x)
g.setDefaultParentSize(saved)
