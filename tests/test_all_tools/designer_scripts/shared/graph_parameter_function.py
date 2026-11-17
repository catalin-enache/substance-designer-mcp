"""Runs inside Designer: a saved package whose graph's own $outputsize is a function reading an input, which the API
can't make, so the .sbs is edited (GUIDE.md, the file-level edit pattern), then loaded and left open. Prints the size
it gives at two values of the input, which ends at 3,3. ARGS: identifier, path."""

import xml.etree.ElementTree as ET
from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import int2
from sd.api.sddefinition import SDDefinition
from sd.api.sdgraph import SDGraph
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory as C
from sd.api.sdresource import SDResource
from sd.api.sdtexture import SDTexture
from sd.api.sdtypeint2 import SDTypeInt2
from sd.api.sdvalueint2 import SDValueInt2
from sd.api.sdvaluestring import SDValueString
from sd.api.sdvaluetexture import SDValueTexture


class Args(TypedDict):
    identifier: str
    path: str


ARGS: Args = globals()['ARGS']
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()


def property_of(owner: SDNode | SDResource, pid: str, category: C) -> SDProperty:
    return cast(SDProperty, owner.getPropertyFromId(pid, category))


def child(element: ET.Element, tag: str) -> ET.Element:
    """The first `tag` element under `element`."""
    return cast(ET.Element, element.find(tag))


pkg = pm.newUserPackage()
g = SDSBSCompGraph.sNew(pkg)
g.setIdentifier(ARGS['identifier'])
g.setPropertyValue(cast(SDProperty, g.newProperty('size_in', SDTypeInt2.sNew(), C.Input)), SDValueInt2.sNew(int2(3, 3)))
uniform = g.newNode('sbs::compositing::uniform')
uniform.newPropertyConnectionFromId('unique_filter_output', g.newNode('sbs::compositing::output'), 'inputNodeOutput')
function = cast(
    SDGraph,
    uniform.newPropertyGraph(property_of(uniform, '$outputsize', C.Input), 'SDSBSFunctionGraph'),
)
get = function.newNode('sbs::function::get_integer2')
get.setInputPropertyValueFromId('__constant__', SDValueString.sNew('size_in'))
function.setOutputNode(get, True)
pm.savePackageAs(pkg, ARGS['path'])
pm.unloadUserPackage(pkg)

# The elements looked for are in the file this script has just saved. A missing one raises, which fails the script.
tree = ET.parse(ARGS['path'])
graph = next(tree.getroot().iter('graph'))
parameters = next(p for p in child(graph, 'compNodes').iter('parameters') if p.find('parameter') is not None)
moved = next(p for p in parameters if child(p, 'name').get('v') == 'outputsize')
parameters.remove(moved)
base = child(graph, 'baseParameters')
for old in list(base):
    if child(old, 'name').get('v') == 'outputsize':
        base.remove(old)
new = ET.SubElement(base, 'parameter')
ET.SubElement(new, 'name').set('v', 'outputsize')
ET.SubElement(new, 'relativeTo').set('v', '0')
ET.SubElement(new, 'paramValue').append(child(moved, 'paramValue')[0])
tree.write(ARGS['path'])

loaded = pm.loadUserPackage(ARGS['path'])
g = cast(SDSBSCompGraph, loaded.findResourceFromUrl(ARGS['identifier']))
source: SDNode = next(
    n for n in g.getNodes() if cast(SDDefinition, n.getDefinition()).getId() == 'sbs::compositing::uniform'
)
size_in = property_of(g, 'size_in', C.Input)


def pixels() -> int:
    g.compute()
    value = cast(
        SDValueTexture,
        source.getPropertyValue(property_of(source, 'unique_filter_output', C.Output)),
    )
    return int(cast(SDTexture, value.get()).getSize().x)


low = pixels()
g.setPropertyValue(size_in, SDValueInt2.sNew(int2(5, 5)))
high = pixels()
g.setPropertyValue(size_in, SDValueInt2.sNew(int2(3, 3)))
print('GRAPH_SIZE input 3,3 %d px, input 5,5 %d px' % (low, high))
