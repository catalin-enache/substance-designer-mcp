"""Runs inside Designer: the graph's frame count and size settings. ARGS: graph."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdgraphobjectframe import SDGraphObjectFrame
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory


class Args(TypedDict):
    graph: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

p = cast(SDProperty, g.getPropertyFromId('$outputsize', SDPropertyCategory.Input))
frames = sum(isinstance(o, SDGraphObjectFrame) for o in g.getGraphObjects())
print('FRAMES=%d SIZE=%s PARENT=%d' % (frames, g.getPropertyInheritanceMethod(p).name, g.getDefaultParentSize().x))
