"""Imports, the application and package manager, graph lookup and value formatting (first: the
other parts use these)."""

# `X as X`: the other parts import these from here (mypy counts only explicit re-exports); the parts
# share one namespace, so each name is imported once, here
import os as os
from collections.abc import Callable as Callable, Sequence as Sequence
from typing import Any as Any, cast as cast

import sd
from sd.api.apiexception import APIException as APIException
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph as SDSBSCompGraph
from sd.api.sbs.sdsbscompnode import SDSBSCompNode as SDSBSCompNode
from sd.api.sdapplication import SDApplication, SDApplicationPath as SDApplicationPath
from sd.api.sdconnection import SDConnection
from sd.api.sddefinition import SDDefinition as SDDefinition
from sd.api.sdgraph import SDGraph as SDGraph
from sd.api.sdnode import SDNode as SDNode
from sd.api.sdpackage import SDPackage as SDPackage
from sd.api.sdpackagemgr import SDPackageMgr
from sd.api.sdproperty import SDProperty as SDProperty, SDPropertyCategory as SDPropertyCategory
from sd.api.sdtexture import SDTexture as SDTexture
from sd.api.sdtype import SDType as SDType
from sd.api.sdtypeenum import SDTypeEnum as SDTypeEnum
from sd.api.sduimgr import SDUIMgr as SDUIMgr
from sd.api.sdvalue import SDValue as SDValue
from sd.api.sdvaluetexture import SDValueTexture as SDValueTexture

_APP: SDApplication = sd.getContext().getSDApplication()  # type: ignore[no-untyped-call]  # sd: no annotations
_PM: SDPackageMgr = _APP.getPackageMgr()


def _current_graph() -> SDGraph | None:
    try:
        ui = _APP.getQtForPythonUIMgr()  # type: ignore[no-untyped-call]  # sd: no annotations
        return cast(SDGraph | None, ui.getCurrentGraph())
    except (Exception, APIException):
        return None


def _is_library_package(pkg: SDPackage) -> bool:
    """Library packages loaded for describe_node/add_node count as user packages too."""
    lib = os.path.normcase(os.path.join(_APP.getPath(SDApplicationPath.DefaultResourcesDir), 'packages'))
    return os.path.normcase(os.path.dirname(pkg.getFilePath() or '')) == lib


def _same_graph(a: SDGraph | None, b: SDGraph | None) -> bool:
    """True when a and b are the same graph: the same identifier in the same package (two open
    packages can each have a graph with one name)."""
    return (
        a is not None
        and b is not None
        and a.getIdentifier() == b.getIdentifier()
        and a.getPackage().getUID() == b.getPackage().getUID()
    )


def find_graph(identifier: str | SDSBSCompGraph | None = None) -> SDSBSCompGraph:
    """Compositing graph by identifier among the user's open packages (library packages
    excluded); default: the graph shown in the UI. A graph object is returned as is, so a batch
    keeps editing the graph it started on. Several open graphs with the same identifier (every
    new graph is "New_Graph") are ambiguous unless one of them is open in the UI."""
    if isinstance(identifier, SDSBSCompGraph):
        return identifier
    current = _current_graph()
    if not identifier:
        if current is None:
            raise RuntimeError('No graph identifier given and no graph is open in the UI.')
        if not isinstance(current, SDSBSCompGraph):
            raise RuntimeError(
                'The graph open in the UI (%s) is not a compositing graph; pass graph=<id>.' % current.getIdentifier()
            )
        return current
    matches = [
        r
        for p in _PM.getUserPackages()
        if not _is_library_package(p)
        for r in p.getChildrenResources(True)
        if r.getIdentifier() == identifier and isinstance(r, SDSBSCompGraph)
    ]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise RuntimeError('Graph %r not found in open user packages.' % identifier)
    for g in matches:
        if _same_graph(g, current):
            return g
    raise RuntimeError(
        '%d open graphs are named %r (packages: %s); open the one you mean in Designer '
        'or close the others.'
        % (len(matches), identifier, ', '.join(g.getPackage().getFilePath() or 'never saved' for g in matches))
    )


def fmt(value: SDValue | None) -> Any:
    """Compact, printable form of an SDValue."""
    if value is None:
        return None
    try:
        x = value.get()  # type: ignore[attr-defined]  # every concrete SDValue has get()
    except (Exception, APIException):
        return '<%s>' % type(value).__name__
    for attrs in (('x', 'y', 'z', 'w'), ('r', 'g', 'b', 'a')):
        if hasattr(x, attrs[0]):
            vals = tuple(getattr(x, a) for a in attrs if hasattr(x, a))
            return tuple(round(v, 4) if isinstance(v, float) else v for v in vals)
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, (bool, int, str)):
        return x
    return '<%s>' % type(x).__name__


def node_kind(node: SDNode) -> str:
    ref = node.getReferencedResource()
    if ref is not None:
        return 'instance:' + ref.getIdentifier()
    return cast(SDDefinition, node.getDefinition()).getId().replace('sbs::compositing::', '')


def _other_end(connection: SDConnection) -> tuple[SDNode, SDProperty]:
    # getPropertyConnections(prop) reports the queried side as "Output" and the
    # other node as "Input", whatever the data-flow direction. A connection always has both ends.
    return cast(SDNode, connection.getInputPropertyNode()), cast(SDProperty, connection.getInputProperty())
