"""Runs inside Designer: what a node computes at the largest absolute $outputsize values (checks.py). A package of its
own, unloaded at the end. Prints one SIZE line per value."""

from typing import Any

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import int2
from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdvalueint2 import SDValueInt2

pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
pkg = pm.newUserPackage()
try:
    g: Any = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_largest_size')
    n: Any = g.newNode('sbs::compositing::uniform')
    out: Any = g.newNode('sbs::compositing::output')
    n.newPropertyConnectionFromId('unique_filter_output', out, 'inputNodeOutput')
    prop = n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)
    n.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
    for log2 in (13, 14, 15):
        n.setPropertyValue(prop, SDValueInt2.sNew(int2(log2, log2)))
        g.compute()
        texture = n.getPropertyValue(n.getPropertyFromId('unique_filter_output', SDPropertyCategory.Output)).get()
        print('SIZE %d %d' % (log2, texture.getSize().x))
finally:
    pm.unloadUserPackage(pkg)
