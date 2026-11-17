"""Runs inside Designer: what Designer does with an output node's identifier and usage tags on its own."""

from typing import cast

import sd
from sd.api.apiexception import APIException
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdtypeusage import SDTypeUsage
from sd.api.sdusage import SDUsage
from sd.api.sdvaluearray import SDValueArray
from sd.api.sdvaluestring import SDValueString
from sd.api.sdvalueusage import SDValueUsage

new_string = SDValueString.sNew
new_array = SDValueArray.sNew
new_array_type = SDTypeUsage.sNew
new_usage_value = SDValueUsage.sNew
new_usage = SDUsage.sNew


def ident(node: SDNode) -> str:
    return str(cast(SDValueString, node.getAnnotationPropertyValueFromId('identifier')).get())


pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
pkg = pm.newUserPackage()
try:
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_output_facts')
    a: SDNode = g.newNode('sbs::compositing::output')
    b: SDNode = g.newNode('sbs::compositing::output')
    print('DEFAULTS=%s,%s' % (ident(a), ident(b)))

    a.setAnnotationPropertyValueFromId('identifier', new_string('same'))
    b.setAnnotationPropertyValueFromId('identifier', new_string('same'))
    print('DUPLICATES_KEPT=%s' % (ident(a) == ident(b) == 'same'))

    b.setAnnotationPropertyValueFromId('identifier', new_string('../a b.c'))
    print('REWRITTEN=%s' % ident(b))
    for allowed in ('1abc', 'a-b', 'A_b9'):
        b.setAnnotationPropertyValueFromId('identifier', new_string(allowed))
        print('KEPT %s=%s' % (allowed, ident(b) == allowed))

    tags = cast(SDValueArray, new_array(new_array_type(), 0))
    tags.pushBack(cast(SDValueUsage, new_usage_value(new_usage('not a usage/', 'XYZ', 'nope'))))
    a.setAnnotationPropertyValueFromId('usages', tags)
    usages = cast(SDValueArray, a.getAnnotationPropertyValueFromId('usages')).get()
    read = cast(SDUsage, cast(SDValueUsage, usages.getItem(0)).get())
    print(
        'USAGE_UNCHECKED=%s'
        % ((read.getName(), read.getComponents(), read.getColorSpace()) == ('not a usage/', 'XYZ', 'nope'))
    )

    levels: SDNode = g.newNode('sbs::compositing::levels')
    try:
        levels.setAnnotationPropertyValueFromId('identifier', new_string('x'))
        print('OTHER_NODE_RAISES=False')
    except APIException:
        print('OTHER_NODE_RAISES=True')
finally:
    pm.unloadUserPackage(pkg)
