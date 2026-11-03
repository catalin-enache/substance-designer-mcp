"""Runs inside Designer: closes the open packages saved at these paths. ARGS: paths."""

from typing import Any

import sd

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]

for p in list(pm.getUserPackages()):
    if (p.getFilePath() or '') in ARGS['paths']:
        pm.unloadUserPackage(p)
