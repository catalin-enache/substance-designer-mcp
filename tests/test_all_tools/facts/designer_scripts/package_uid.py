"""Runs inside Designer: a package's UID through saves, a loaded copy and a snapshot copy, and whether its wrappers'
handles differ; leaves the files for reload_uid. ARGS: folder."""

import os
import re
import shutil
from typing import Any

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]


def file_uid(name: str) -> str:
    with open(os.path.join(d, name)) as f:
        found = re.search(r'<fileUID v="([^"]+)"', f.read())
    if found is None:
        raise RuntimeError('no <fileUID> in %s' % name)
    return found.group(1)


d = ARGS['folder']
os.makedirs(d, exist_ok=True)
pkg: Any = pm.newUserPackage()
g: Any = SDSBSCompGraph.sNew(pkg)
g.setIdentifier('mcp_selftest_uid')
loaded: list[Any] = []
try:
    u0 = pkg.getUID()
    pm.savePackageAs(pkg, os.path.join(d, 'A.sbs'))
    u1 = pkg.getUID()
    pm.savePackageAs(pkg, os.path.join(d, 'B.sbs'))
    u2 = pkg.getUID()
    f = file_uid('B.sbs')
    shutil.copy(os.path.join(d, 'B.sbs'), os.path.join(d, 'C.sbs'))
    loaded.append(pm.loadUserPackage(os.path.join(d, 'C.sbs')))
    u3 = loaded[-1].getUID()
    print('SAME_UID=%s' % (u0 == u1 == u2 == f == u3))
    # a snapshot copy keeps it too (SRV-42); and a package using this one's graph, for reload_uid
    pm.saveCopyOfPackageAs(pkg, os.path.join(d, 'S.sbs'))
    print('COPY_KEEPS_UID=%s' % (file_uid('S.sbs') == u0))
    user: Any = pm.newUserPackage()
    loaded.append(user)
    ug: Any = SDSBSCompGraph.sNew(user)
    ug.setIdentifier('mcp_selftest_uid_user')
    ug.newInstanceNode(g)
    pm.savePackageAs(user, os.path.join(d, 'D.sbs'))
    # both wrappers alive at once: a freed one's address can be reused by the next
    w1, w2 = g.getPackage(), g.getPackage()
    print('HANDLES_DIFFER=%s' % (w1.mHandle != w2.mHandle))
finally:
    for p in [pkg, *loaded]:
        pm.unloadUserPackage(p)
