"""Runs inside Designer: adds a free comment far from every node. ARGS: graph."""

from typing import Any

import sd
from sd.api.sdbasetypes import float2
from sd.api.sdgraphobjectcomment import SDGraphObjectComment

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

note: Any = SDGraphObjectComment.sNew(g)
note.setPosition(float2(2500, -1500))
note.setDescription('far away')
print('COMMENT=ok')
