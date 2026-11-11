"""Runs inside Designer: what Designer does with an output node's identifier and usage tags on its own."""

from typing import Any

import sd
from sd.api.apiexception import APIException
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdtypeusage import SDTypeUsage
from sd.api.sdusage import SDUsage
from sd.api.sdvaluearray import SDValueArray
from sd.api.sdvaluestring import SDValueString
from sd.api.sdvalueusage import SDValueUsage

new_string: Any = SDValueString.sNew
new_array: Any = SDValueArray.sNew
new_array_type: Any = SDTypeUsage.sNew
new_usage_value: Any = SDValueUsage.sNew
new_usage: Any = SDUsage.sNew


def ident(node: Any) -> str:
    return str(node.getAnnotationPropertyValueFromId('identifier').get())


pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
pkg: Any = pm.newUserPackage()
try:
    g: Any = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_output_facts')
    a: Any = g.newNode('sbs::compositing::output')
    b: Any = g.newNode('sbs::compositing::output')
    print('DEFAULTS=%s,%s' % (ident(a), ident(b)))

    a.setAnnotationPropertyValueFromId('identifier', new_string('same'))
    b.setAnnotationPropertyValueFromId('identifier', new_string('same'))
    print('DUPLICATES_KEPT=%s' % (ident(a) == ident(b) == 'same'))

    b.setAnnotationPropertyValueFromId('identifier', new_string('../a b.c'))
    print('REWRITTEN=%s' % ident(b))
    for allowed in ('1abc', 'a-b', 'A_b9'):
        b.setAnnotationPropertyValueFromId('identifier', new_string(allowed))
        print('KEPT %s=%s' % (allowed, ident(b) == allowed))

    tags: Any = new_array(new_array_type(), 0)
    tags.pushBack(new_usage_value(new_usage('not a usage/', 'XYZ', 'nope')))
    a.setAnnotationPropertyValueFromId('usages', tags)
    read = a.getAnnotationPropertyValueFromId('usages').get().getItem(0).get()
    print(
        'USAGE_UNCHECKED=%s'
        % ((read.getName(), read.getComponents(), read.getColorSpace()) == ('not a usage/', 'XYZ', 'nope'))
    )

    levels: Any = g.newNode('sbs::compositing::levels')
    try:
        levels.setAnnotationPropertyValueFromId('identifier', new_string('x'))
        print('OTHER_NODE_RAISES=False')
    except APIException:
        print('OTHER_NODE_RAISES=True')
finally:
    pm.unloadUserPackage(pkg)
