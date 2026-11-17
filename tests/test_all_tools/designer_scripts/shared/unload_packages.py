"""Runs inside Designer: closes the open packages saved at these paths. ARGS: paths."""

from typing import TypedDict

import sd
from sd.api.sdpackagemgr import SDPackageMgr


class Args(TypedDict):
    paths: list[str]


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()

for p in list(pm.getUserPackages()):
    if (p.getFilePath() or '') in ARGS['paths']:
        pm.unloadUserPackage(p)
