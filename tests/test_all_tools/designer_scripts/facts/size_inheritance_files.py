"""Runs inside Designer: saves one graph per inheritance mode, for how a .sbs stores it (facts.py). ARGS: folder."""

import os
from typing import Any

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod

ARGS: dict[str, Any] = globals()['ARGS']
M = SDPropertyInheritanceMethod
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
os.makedirs(ARGS['folder'], exist_ok=True)
for m in (M.Absolute, M.RelativeToInput, M.RelativeToParent):
    pkg = pm.newUserPackage()
    try:
        g: Any = SDSBSCompGraph.sNew(pkg)
        g.setIdentifier('mcp_selftest_inherit_' + m.name)
        n: Any = g.newNode('sbs::compositing::blur')
        g.setPropertyInheritanceMethod(g.getPropertyFromId('$outputsize', SDPropertyCategory.Input), m)
        n.setPropertyInheritanceMethod(n.getPropertyFromId('$outputsize', SDPropertyCategory.Input), m)
        pm.savePackageAs(pkg, os.path.join(ARGS['folder'], m.name + '.sbs'))
    finally:
        pm.unloadUserPackage(pkg)
print('saved')
