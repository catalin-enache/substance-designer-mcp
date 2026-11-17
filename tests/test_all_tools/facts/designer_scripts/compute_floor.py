"""Runs inside Designer: graph.compute() takes about the same time however small the graph, and with nothing changed
since the last one (checks.py; GUIDE.md, sd API). A package of its own, unloaded at the end. Prints the seconds of three
computes of a 3-node 4x4 graph (its size printed), then of one more with 60 nodes added and computed once."""

import time
from typing import cast

import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import int2
from sd.api.sdnode import SDNode
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdtexture import SDTexture
from sd.api.sdvalueint2 import SDValueInt2
from sd.api.sdvaluetexture import SDValueTexture

pm: SDPackageMgr = sd.getContext().getSDApplication().getPackageMgr()  # type: ignore[no-untyped-call]
pkg = pm.newUserPackage()


def chain(g: SDSBSCompGraph) -> SDNode:
    """uniform -> levels -> output; returns the levels node."""
    uniform: SDNode = g.newNode('sbs::compositing::uniform')
    levels: SDNode = g.newNode('sbs::compositing::levels')
    uniform.newPropertyConnectionFromId('unique_filter_output', levels, 'input1')
    levels.newPropertyConnectionFromId('unique_filter_output', g.newNode('sbs::compositing::output'), 'inputNodeOutput')
    return levels


def timed(g: SDSBSCompGraph) -> float:
    began = time.perf_counter()
    g.compute()
    return time.perf_counter() - began


try:
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier('mcp_selftest_compute_floor')
    # absolute first: a new graph's size is relative to its parent, which made this one 1024 px (REVIEW.md TST-242)
    size = cast(SDProperty, g.getPropertyFromId('$outputsize', SDPropertyCategory.Input))
    g.setPropertyInheritanceMethod(size, SDPropertyInheritanceMethod.Absolute)
    g.setInputPropertyValueFromId('$outputsize', SDValueInt2.sNew(int2(2, 2)))
    levels = chain(g)
    seconds = ' '.join('%.2f' % timed(g) for _ in range(3))
    texture = cast(
        SDValueTexture,
        levels.getPropertyValue(
            cast(SDProperty, levels.getPropertyFromId('unique_filter_output', SDPropertyCategory.Output))
        ),
    )
    pixels = cast(SDTexture, texture.get()).getSize()
    print('SMALL %dx%d %s' % (pixels.x, pixels.y, seconds))
    for _ in range(20):
        chain(g)
    timed(g)
    print('LARGER %d nodes, unchanged %.2f' % (len(g.getNodes()), timed(g)))
finally:
    pm.unloadUserPackage(pkg)
