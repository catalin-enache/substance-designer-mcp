"""Runs inside Designer: the atomic node count, APIException's base, and which side a connection is reported from.
ARGS: graph, node, source."""

from typing import TypedDict, cast

import sd
from sd.api.apiexception import APIException
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory


class Args(TypedDict):
    graph: str
    node: str
    source: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
g = cast(
    SDSBSCompGraph,
    next(r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']),
)

print('ATOMIC=%d' % len(g.getNodeDefinitions()))
print('APIEXC_BASE_ONLY=%s' % (issubclass(APIException, BaseException) and not issubclass(APIException, Exception)))
n = cast(SDNode, g.getNodeFromId(ARGS['node']))
c = n.getPropertyConnections(cast(SDProperty, n.getPropertyFromId('input1', SDPropertyCategory.Input)))[0]
queried = (
    cast(SDNode, c.getOutputPropertyNode()).getIdentifier() == ARGS['node']
    and cast(SDProperty, c.getOutputProperty()).getId() == 'input1'
)
print('QUERIED_SIDE=%s' % (queried and cast(SDNode, c.getInputPropertyNode()).getIdentifier() == ARGS['source']))
