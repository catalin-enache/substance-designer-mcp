"""Runs inside Designer: what a rename of an output does to a graph using it through an instance: in the same package,
in another open one, after saving and reloading both, and when that graph was closed during the rename. Prints each
one's connector, link and first computed pixel. ARGS: folder."""

import ctypes
import os
from typing import TypedDict, cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import ColorRGBA
from sd.api.sdnode import SDNode
from sd.api.sdpackage import SDPackage
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory
from sd.api.sdtexture import SDTexture
from sd.api.sdvaluecolorrgba import SDValueColorRGBA
from sd.api.sdvaluestring import SDValueString
from sd.api.sdvaluetexture import SDValueTexture


class Args(TypedDict):
    folder: str


ARGS: Args = globals()['ARGS']
new_string = SDValueString.sNew
new_color = SDValueColorRGBA.sNew
pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()
HOST = 'mcp_selftest_rename_host'


def host_in(pkg: SDPackage) -> SDSBSCompGraph:
    return cast(SDSBSCompGraph, pkg.findResourceFromUrl(HOST))


def node_in(g: SDSBSCompGraph, node_id: str) -> SDNode:
    return cast(SDNode, g.getNodeFromId(node_id))


def instance_in(g: SDSBSCompGraph, source: SDSBSCompGraph) -> SDNode:
    return cast(SDNode, g.newInstanceNode(source))


def source_graph(pkg: SDPackage) -> tuple[SDSBSCompGraph, SDNode]:
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_rename_source')
    uniform: SDNode = g.newNode('sbs::compositing::uniform')
    uniform.setInputPropertyValueFromId('outputcolor', new_color(ColorRGBA(0.25, 0.5, 0.75, 1.0)))
    out: SDNode = g.newNode('sbs::compositing::output')
    out.setAnnotationPropertyValueFromId('identifier', new_string('base'))
    uniform.newPropertyConnectionFromId('unique_filter_output', out, 'inputNodeOutput')
    return g, out


def host_graph(pkg: SDPackage, source: SDSBSCompGraph) -> tuple[SDSBSCompGraph, str, str]:
    """The host graph and its instance's and levels node's ids: source.base -> levels -> an output."""
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier(HOST)
    instance = instance_in(g, source)
    levels: SDNode = g.newNode('sbs::compositing::levels')
    instance.newPropertyConnectionFromId('base', levels, 'input1')
    out: SDNode = g.newNode('sbs::compositing::output')
    levels.newPropertyConnectionFromId('unique_filter_output', out, 'inputNodeOutput')
    return g, instance.getIdentifier(), levels.getIdentifier()


def rename(out: SDNode) -> None:
    out.setAnnotationPropertyValueFromId('identifier', new_string('albedo'))


def report(case: str, g: SDSBSCompGraph, instance_id: str, levels_id: str) -> None:
    instance, levels = node_in(g, instance_id), node_in(g, levels_id)
    connectors = [p.getId() for p in instance.getProperties(SDPropertyCategory.Output)]
    links = [
        cast(SDProperty, c.getInputProperty()).getId()
        for prop in levels.getProperties(SDPropertyCategory.Input)
        if prop.isConnectable()
        for c in levels.getPropertyConnections(prop)
    ]
    g.compute()
    value = cast(
        SDValueTexture | None,
        levels.getPropertyValue(
            cast(SDProperty, levels.getPropertyFromId('unique_filter_output', SDPropertyCategory.Output))
        ),
    )
    pixel = (
        ctypes.string_at(cast(SDTexture, value.get()).getPixelBufferAddress(), 4).hex()
        if value and value.get()
        else 'none'
    )
    print('%s connectors=%s link=%s pixel=%s' % (case, ','.join(connectors), ','.join(links), pixel))


folder = os.path.realpath(ARGS['folder'])
os.makedirs(folder, exist_ok=True)
try:
    # the same package
    pkg = pm.newUserPackage()
    source, out = source_graph(pkg)
    host, instance_id, levels_id = host_graph(pkg, source)
    report('BEFORE', host, instance_id, levels_id)
    rename(out)
    report('SAME_PACKAGE', host, instance_id, levels_id)
    pm.unloadUserPackage(pkg)

    # another package, open during the rename; then saved and reloaded
    source_pkg = pm.newUserPackage()
    source, out = source_graph(source_pkg)
    pm.savePackageAs(source_pkg, os.path.join(folder, 'open_source.sbs'))
    host_pkg = pm.newUserPackage()
    host, instance_id, levels_id = host_graph(host_pkg, source)
    host_path = os.path.join(folder, 'open_host.sbs')
    pm.savePackageAs(host_pkg, host_path)
    rename(out)
    report('OTHER_PACKAGE', host, instance_id, levels_id)
    pm.savePackage(source_pkg)
    pm.savePackage(host_pkg)
    pm.unloadUserPackage(host_pkg)
    pm.unloadUserPackage(source_pkg)
    host_pkg = pm.loadUserPackage(host_path)
    report('RELOADED', host_in(host_pkg), instance_id, levels_id)
    pm.unloadUserPackage(host_pkg)

    # the graph using it is closed during the rename, so nothing open can follow it
    source_pkg = pm.newUserPackage()
    source, out = source_graph(source_pkg)
    pm.savePackageAs(source_pkg, os.path.join(folder, 'closed_source.sbs'))
    host_pkg = pm.newUserPackage()
    host, instance_id, levels_id = host_graph(host_pkg, source)
    host_path = os.path.join(folder, 'closed_host.sbs')
    pm.savePackageAs(host_pkg, host_path)
    pm.unloadUserPackage(host_pkg)
    rename(out)
    pm.savePackage(source_pkg)
    host_pkg = pm.loadUserPackage(host_path)
    report('CLOSED', host_in(host_pkg), instance_id, levels_id)
    print('CLOSED_MARKED_MODIFIED=%s' % host_pkg.isModified())

    # the two ways back: the old name again, with that graph open
    host = host_in(host_pkg)
    out.setAnnotationPropertyValueFromId('identifier', new_string('base'))
    report('REPAIRED_BY_OLD_NAME', host, instance_id, levels_id)
    pm.unloadUserPackage(host_pkg)

    # or a new instance wired from the new name, after the same break again
    rename(out)
    pm.savePackage(source_pkg)
    host_pkg = pm.loadUserPackage(host_path)
    host = host_in(host_pkg)
    report('BROKEN_AGAIN', host, instance_id, levels_id)
    fresh = instance_in(host, source)
    fresh.newPropertyConnectionFromId('albedo', node_in(host, levels_id), 'input1')
    report('REPAIRED_BY_NEW_INSTANCE', host, fresh.getIdentifier(), levels_id)
finally:
    for p in pm.getUserPackages():
        path = p.getFilePath()
        if not path or os.path.dirname(os.path.realpath(path)) == folder:
            ids = [r.getIdentifier() for r in p.getChildrenResources(False)]
            if not path and not any(i.startswith('mcp_selftest_rename') for i in ids):
                continue
            pm.unloadUserPackage(p)
