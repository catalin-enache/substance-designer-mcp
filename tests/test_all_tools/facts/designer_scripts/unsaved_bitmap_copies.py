"""Runs inside Designer: where a CopiedAndLinked bitmap goes before a package's first save, twice (checks.py).
ARGS: png."""

import os
from typing import TypedDict

import sd
from PySide6.QtCore import QDir
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdresource import EmbedMethod
from sd.api.sdresourcebitmap import SDResourceBitmap


class Args(TypedDict):
    png: str


ARGS: Args = globals()['ARGS']
print('TEMP=%s' % QDir.tempPath())  # Designer's own: launch_designer gives each Designer it starts one
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
for _ in range(2):
    pkg = pm.newUserPackage()
    try:
        SDSBSCompGraph.sNew(pkg).setIdentifier('mcp_selftest_unsaved_copy')
        res = SDResourceBitmap.sNewFromFile(pkg, ARGS['png'], EmbedMethod.CopiedAndLinked)
        path = res.getFilePath()
    finally:
        pm.unloadUserPackage(pkg)
    print('COPY=%s STAYS=%s' % (path, os.path.isfile(path)))
