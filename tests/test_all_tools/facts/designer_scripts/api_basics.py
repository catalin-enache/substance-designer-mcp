"""Runs inside Designer: the atomic node count, APIException's base, and which side a connection is reported from.
ARGS: graph, node, source."""

from typing import Any

import sd
from sd.api.apiexception import APIException
from sd.api.sdproperty import SDPropertyCategory

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
g: Any = next(
    r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == ARGS['graph']
)

print('ATOMIC=%d' % len(g.getNodeDefinitions()))
print('APIEXC_BASE_ONLY=%s' % (issubclass(APIException, BaseException) and not issubclass(APIException, Exception)))
n = g.getNodeFromId(ARGS['node'])
c = n.getPropertyConnections(n.getPropertyFromId('input1', SDPropertyCategory.Input))[0]
queried = c.getOutputPropertyNode().getIdentifier() == ARGS['node'] and c.getOutputProperty().getId() == 'input1'
print('QUERIED_SIDE=%s' % (queried and c.getInputPropertyNode().getIdentifier() == ARGS['source']))
