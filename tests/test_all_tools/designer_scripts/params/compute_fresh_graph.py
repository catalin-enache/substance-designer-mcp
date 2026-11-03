"""Runs inside Designer: in a fresh graph, graph.compute() computes what feeds an output and not a node that doesn't
(params.py). In a package of its own, closed again."""

from typing import Any

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdnode import SDNode
from sd.api.sdproperty import SDPropertyCategory

pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]


def texture(node: SDNode) -> Any:
    value: Any = node.getPropertyValue(node.getProperties(SDPropertyCategory.Output)[0])
    return value.get() if value is not None else None


pkg = pm.newUserPackage()
try:
    g = SDSBSCompGraph.sNew(pkg)
    fed: Any = g.newNode('sbs::compositing::uniform')
    lone: Any = g.newNode('sbs::compositing::uniform')
    output: Any = g.newNode('sbs::compositing::output')
    fed.newPropertyConnectionFromId('unique_filter_output', output, 'inputNodeOutput')
    g.compute()
    print('ALONE_COMPUTED=%s FED_COMPUTED=%s' % (texture(lone) is not None, texture(fed) is not None))
finally:
    pm.unloadUserPackage(pkg)
