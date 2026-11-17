"""Runs inside Designer: what a node computes at the largest absolute $outputsize values (checks.py). A package of its
own, unloaded at the end. Prints one SIZE line per value."""

from typing import cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sbs.sdsbscompnode import SDSBSCompNode
from sd.api.sdbasetypes import int2
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdtexture import SDTexture
from sd.api.sdvalueint2 import SDValueInt2
from sd.api.sdvaluetexture import SDValueTexture

pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
pkg = pm.newUserPackage()
try:
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_largest_size')
    n = cast(SDSBSCompNode, g.newNode('sbs::compositing::uniform'))
    out: SDNode = g.newNode('sbs::compositing::output')
    n.newPropertyConnectionFromId('unique_filter_output', out, 'inputNodeOutput')
    prop = cast(SDProperty, n.getPropertyFromId('$outputsize', SDPropertyCategory.Input))
    n.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
    for log2 in (13, 14, 15):
        n.setPropertyValue(prop, SDValueInt2.sNew(int2(log2, log2)))
        g.compute()
        output = cast(SDProperty, n.getPropertyFromId('unique_filter_output', SDPropertyCategory.Output))
        texture = cast(SDTexture, cast(SDValueTexture, n.getPropertyValue(output)).get())
        print('SIZE %d %d' % (log2, texture.getSize().x))
finally:
    pm.unloadUserPackage(pkg)
