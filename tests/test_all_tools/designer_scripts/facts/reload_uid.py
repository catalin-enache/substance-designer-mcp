"""Runs inside Designer: a re-stamped snapshot loads with its new UID, and a package using a re-stamped graph still
finds it. ARGS: snapshot, snapshot_uid, user, dependency, dependency_uid."""

from typing import Any

import sd

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]

loaded: list[Any] = []
try:
    loaded.append(pm.loadUserPackage(ARGS['snapshot']))
    print('SNAP_LOADS_NEW=%s' % (loaded[-1].getUID() == ARGS['snapshot_uid']))
    loaded.append(pm.loadUserPackage(ARGS['user']))
    ug = loaded[-1].findResourceFromUrl('mcp_selftest_uid_user')
    ref = next(n.getReferencedResource() for n in ug.getNodes())
    pkg = ref.getPackage() if ref else None
    print(
        'DEP_FOUND=%s'
        % (pkg is not None and pkg.getFilePath() == ARGS['dependency'] and pkg.getUID() == ARGS['dependency_uid'])
    )
finally:
    for p in loaded:
        pm.unloadUserPackage(p)
