"""Runs inside Designer: saves one graph per inheritance mode, for how a .sbs stores it (checks.py). ARGS: folder."""

import os
from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sbs.sdsbscompnode import SDSBSCompNode
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod


class Args(TypedDict):
    folder: str


ARGS: Args = globals()['ARGS']
M = SDPropertyInheritanceMethod
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
os.makedirs(ARGS['folder'], exist_ok=True)
for m in (M.Absolute, M.RelativeToInput, M.RelativeToParent):
    pkg = pm.newUserPackage()
    try:
        g = SDSBSCompGraph.sNew(pkg)
        g.setIdentifier('mcp_selftest_inherit_' + m.name)
        n = cast(SDSBSCompNode, g.newNode('sbs::compositing::blur'))
        g.setPropertyInheritanceMethod(
            cast(SDProperty, g.getPropertyFromId('$outputsize', SDPropertyCategory.Input)), m
        )
        n.setPropertyInheritanceMethod(
            cast(SDProperty, n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)), m
        )
        pm.savePackageAs(pkg, os.path.join(ARGS['folder'], m.name + '.sbs'))
    finally:
        pm.unloadUserPackage(pkg)
    pkg = pm.newUserPackage()
    try:
        inner = SDSBSCompGraph.sNew(pkg)
        inner.setIdentifier('mcp_selftest_inherit_inner')
        uniform: SDNode = inner.newNode('sbs::compositing::uniform')
        uniform.newPropertyConnectionFromId(
            'unique_filter_output', inner.newNode('sbs::compositing::output'), 'inputNodeOutput'
        )
        outer = SDSBSCompGraph.sNew(pkg)
        outer.setIdentifier('mcp_selftest_inherit_outer')
        instance = cast(SDSBSCompNode, outer.newInstanceNode(inner))
        size = cast(SDProperty, instance.getPropertyFromId('$outputsize', SDPropertyCategory.Input))
        print('instance default %s' % instance.getPropertyInheritanceMethod(size).name)
        instance.setPropertyInheritanceMethod(size, m)
        pm.savePackageAs(pkg, os.path.join(ARGS['folder'], 'instance_%s.sbs' % m.name))
    finally:
        pm.unloadUserPackage(pkg)
print('saved')
