"""Runs inside Designer: a re-stamped snapshot loads with its new UID, and a package using a re-stamped graph still
finds it. ARGS: snapshot, snapshot_uid, user, dependency, dependency_uid."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdpackage import SDPackage
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdresource import SDResource


class Args(TypedDict):
    snapshot: str
    snapshot_uid: str
    user: str
    dependency: str
    dependency_uid: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]

loaded: list[SDPackage] = []
try:
    loaded.append(pm.loadUserPackage(ARGS['snapshot']))
    print('SNAP_LOADS_NEW=%s' % (loaded[-1].getUID() == ARGS['snapshot_uid']))
    loaded.append(pm.loadUserPackage(ARGS['user']))
    ug = cast(SDSBSCompGraph, loaded[-1].findResourceFromUrl('mcp_selftest_uid_user'))
    ref: SDResource | None = next(n.getReferencedResource() for n in ug.getNodes())
    pkg = ref.getPackage() if ref else None
    print(
        'DEP_FOUND=%s'
        % (pkg is not None and pkg.getFilePath() == ARGS['dependency'] and pkg.getUID() == ARGS['dependency_uid'])
    )
finally:
    for p in loaded:
        pm.unloadUserPackage(p)
