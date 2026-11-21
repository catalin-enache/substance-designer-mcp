"""Runs inside Designer: puts an output node back as undo's preparation made it, identifier `height`, no label and no
usage, whatever an Undo that failed left (apply_edits can't clear a usage). ARGS: graph, node."""

from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdtypeusage import SDTypeUsage
from sd.api.sdvaluearray import SDValueArray
from sd.api.sdvaluestring import SDValueString


class Args(TypedDict):
    graph: str
    node: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)
n = g.getNodeFromId(ARGS['node'])
if n is None:  # a failed check (common.designer_script)
    raise RuntimeError('no node %s in %s' % (ARGS['node'], ARGS['graph']))
n.setAnnotationPropertyValueFromId('identifier', SDValueString.sNew('height'))
n.setAnnotationPropertyValueFromId('label', SDValueString.sNew(''))
n.setAnnotationPropertyValueFromId('usages', SDValueArray.sNew(SDTypeUsage.sNew(), 0))
print('AS_PREPARED')
