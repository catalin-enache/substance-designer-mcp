"""Runs inside Designer: where a CopiedAndLinked bitmap goes before a package's first save, twice (facts.py).
ARGS: png."""

import os
from typing import Any

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdresource import EmbedMethod
from sd.api.sdresourcebitmap import SDResourceBitmap

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
for _ in range(2):
    pkg = pm.newUserPackage()
    try:
        SDSBSCompGraph.sNew(pkg).setIdentifier('mcp_selftest_unsaved_copy')
        res: Any = SDResourceBitmap.sNewFromFile(pkg, ARGS['png'], EmbedMethod.CopiedAndLinked)
        path = res.getFilePath()
    finally:
        pm.unloadUserPackage(pkg)
    print('COPY=%s STAYS=%s' % (path, os.path.isfile(path)))
