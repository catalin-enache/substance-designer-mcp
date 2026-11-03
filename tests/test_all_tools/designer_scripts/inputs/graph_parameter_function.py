"""Runs inside Designer: a saved package whose graph's own $outputsize is a function reading an input, which the API
can't make, so the .sbs is edited (AGENTS.md, the file-level edit pattern), then loaded and left open. Prints the size
it gives at two values of the input, which ends at 3,3. ARGS: identifier, path."""

import xml.etree.ElementTree as ET
from typing import Any

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import int2
from sd.api.sdproperty import SDPropertyCategory as C
from sd.api.sdtypeint2 import SDTypeInt2
from sd.api.sdvalueint2 import SDValueInt2
from sd.api.sdvaluestring import SDValueString

ARGS: dict[str, Any] = globals()['ARGS']
pm = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]

pkg = pm.newUserPackage()
g: Any = SDSBSCompGraph.sNew(pkg)
g.setIdentifier(ARGS['identifier'])
g.setPropertyValue(g.newProperty('size_in', SDTypeInt2.sNew(), C.Input), SDValueInt2.sNew(int2(3, 3)))
uniform = g.newNode('sbs::compositing::uniform')
uniform.newPropertyConnectionFromId('unique_filter_output', g.newNode('sbs::compositing::output'), 'inputNodeOutput')
function = uniform.newPropertyGraph(uniform.getPropertyFromId('$outputsize', C.Input), 'SDSBSFunctionGraph')
get = function.newNode('sbs::function::get_integer2')
get.setInputPropertyValueFromId('__constant__', SDValueString.sNew('size_in'))
function.setOutputNode(get, True)
pm.savePackageAs(pkg, ARGS['path'])
pm.unloadUserPackage(pkg)

tree = ET.parse(ARGS['path'])
graph: Any = next(tree.getroot().iter('graph'))
parameters: Any = next(p for p in graph.find('compNodes').iter('parameters') if p.find('parameter') is not None)
moved: Any = next(p for p in parameters if p.find('name').get('v') == 'outputsize')
parameters.remove(moved)
base: Any = graph.find('baseParameters')
for old in list(base):
    if old.find('name').get('v') == 'outputsize':
        base.remove(old)
new = ET.SubElement(base, 'parameter')
ET.SubElement(new, 'name').set('v', 'outputsize')
ET.SubElement(new, 'relativeTo').set('v', '0')
ET.SubElement(new, 'paramValue').append(moved.find('paramValue')[0])
tree.write(ARGS['path'])

loaded: Any = pm.loadUserPackage(ARGS['path'])
g = loaded.findResourceFromUrl(ARGS['identifier'])
source = next(n for n in g.getNodes() if n.getDefinition().getId() == 'sbs::compositing::uniform')
size_in = g.getPropertyFromId('size_in', C.Input)


def pixels() -> int:
    g.compute()
    value: Any = source.getPropertyValue(source.getPropertyFromId('unique_filter_output', C.Output))
    return int(value.get().getSize().x)


low = pixels()
g.setPropertyValue(size_in, SDValueInt2.sNew(int2(5, 5)))
high = pixels()
g.setPropertyValue(size_in, SDValueInt2.sNew(int2(3, 3)))
print('GRAPH_SIZE input 3,3 %d px, input 5,5 %d px' % (low, high))
