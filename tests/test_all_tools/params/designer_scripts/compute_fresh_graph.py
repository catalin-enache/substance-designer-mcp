"""Runs inside Designer: in a fresh graph, graph.compute() computes what feeds an output and not a node that doesn't
(checks.py). In a package of its own, closed again."""

from typing import cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdtexture import SDTexture
from sd.api.sdvaluetexture import SDValueTexture

pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()


def texture(node: SDNode) -> SDTexture | None:
    value = cast(SDValueTexture | None, node.getPropertyValue(node.getProperties(SDPropertyCategory.Output)[0]))
    return value.get() if value is not None else None


pkg = pm.newUserPackage()
try:
    g = SDSBSCompGraph.sNew(pkg)
    fed: SDNode = g.newNode('sbs::compositing::uniform')
    lone: SDNode = g.newNode('sbs::compositing::uniform')
    output: SDNode = g.newNode('sbs::compositing::output')
    fed.newPropertyConnectionFromId('unique_filter_output', output, 'inputNodeOutput')
    g.compute()
    print('ALONE_COMPUTED=%s FED_COMPUTED=%s' % (texture(lone) is not None, texture(fed) is not None))
finally:
    pm.unloadUserPackage(pkg)
