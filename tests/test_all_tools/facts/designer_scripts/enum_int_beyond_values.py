"""Runs inside Designer: an int on an enum parameter is accepted whatever it is, and one beyond the enum's values can't
be read back. In a package of its own, closed again."""

from typing import Any

import sd
from sd.api.apiexception import APIException
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdproperty import SDPropertyCategory as C
from sd.api.sdvalueint import SDValueInt

pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
pkg = pm.newUserPackage()
try:
    g: Any = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_enum_int')
    n = g.newNode('sbs::compositing::blend')
    p = n.getPropertyFromId('blendingmode', C.Input)
    n.setPropertyValue(p, SDValueInt.sNew(5))
    print('ENUM_5=%d' % n.getPropertyValue(p).get())
    n.setPropertyValue(p, SDValueInt.sNew(99))
    print('ACCEPTED_99')
    try:
        print('READ_99=%d' % n.getPropertyValue(p).get())
    except APIException:
        print('READ_99_RAISES')
finally:
    pm.unloadUserPackage(pkg)
