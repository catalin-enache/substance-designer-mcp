"""Runs inside Designer: every property of a Dot node, for the fact that it has no ID (facts.py). In a package of its
own, closed again."""

from typing import Any

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdproperty import SDPropertyCategory as C

pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
pkg = pm.newUserPackage()
try:
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_dot')
    n: Any = g.newNode('sbs::compositing::passthrough')
    ids = sorted(p.getId() for cat in (C.Annotation, C.Input, C.Output) for p in n.getProperties(cat))
    print('DOT_PROPS=' + ','.join(ids))
finally:
    pm.unloadUserPackage(pkg)
