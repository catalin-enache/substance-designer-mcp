"""Runs inside Designer: adds a free comment far from every node. ARGS: graph."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import float2
from sd.api.sdgraphobjectcomment import SDGraphObjectComment
from sd.api.sdpackagemgr import SDPackageMgr


class Args(TypedDict):
    graph: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

note = SDGraphObjectComment.sNew(g)
note.setPosition(float2(2500, -1500))
note.setDescription('far away')
print('COMMENT=ok')
