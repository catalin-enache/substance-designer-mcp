"""Runs inside Designer: bitmaps can't be embedded, and setDefaultParentSize takes pixels (checks.py).
ARGS: graph, png."""

from typing import TypedDict, cast

import sd
from sd.api.apiexception import APIException
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import int2
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdresource import EmbedMethod
from sd.api.sdresourcebitmap import SDResourceBitmap


class Args(TypedDict):
    graph: str
    png: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
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
