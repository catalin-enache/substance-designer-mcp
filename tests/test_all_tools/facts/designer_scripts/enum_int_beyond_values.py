"""Runs inside Designer: an int on an enum parameter is accepted whatever it is, and one beyond the enum's values can't
be read back. In a package of its own, closed again."""

from typing import cast

import sd
from sd.api.apiexception import APIException
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory as C
from sd.api.sdvalueenum import SDValueEnum
from sd.api.sdvalueint import SDValueInt

pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
pkg = pm.newUserPackage()
try:
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_enum_int')
    n: SDNode = g.newNode('sbs::compositing::blend')
    p = cast(SDProperty, n.getPropertyFromId('blendingmode', C.Input))
    n.setPropertyValue(p, SDValueInt.sNew(5))
    # Which class reads back isn't measured: the enum's value or the int set. get() gives an int on both.
    print('ENUM_5=%d' % cast(SDValueEnum | SDValueInt, n.getPropertyValue(p)).get())
    n.setPropertyValue(p, SDValueInt.sNew(99))
    print('ACCEPTED_99')
    try:
        print('READ_99=%d' % cast(SDValueEnum | SDValueInt, n.getPropertyValue(p)).get())
    except APIException:
        print('READ_99_RAISES')
finally:
    pm.unloadUserPackage(pkg)
