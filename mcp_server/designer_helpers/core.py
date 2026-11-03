"""Imports, the application and package manager, graph lookup and value formatting (first: the
other parts use these)."""

# `X as X`: the other parts import these from here (mypy counts only explicit re-exports); the parts
# share one namespace, so each name is imported once, here
import math
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
from sd.api.sdresourcefolder import SDResourceFolder as SDResourceFolder
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
    """Whether the package's file is one of Designer's own: anywhere under the library folder Designer
    reports (30 of Designer 16's are in subfolders; REVIEW.md HLP-57), both paths resolved. The API has no
    flag for it. Library packages loaded for describe_node/add_node count as user packages too."""
    file = pkg.getFilePath()
    if not file:
        return False
    lib = os.path.normcase(
        os.path.realpath(os.path.join(_APP.getPath(SDApplicationPath.DefaultResourcesDir), 'packages'))
    )
    try:
        return os.path.commonpath([lib, os.path.normcase(os.path.realpath(file))]) == lib
    except ValueError:  # another drive on Windows
        return False


def _library_refusal(reason: str) -> RuntimeError:
    """The one refusal for Designer's library packages, on every path, with what does work: by name,
    open_graph and snapshot_graph refuse too, and an edit is refused anyway (ROADMAP item 27, REVIEW.md
    HLP-58). In focus: with no graph given, the tools take the graph in focus, whichever it is."""
    return RuntimeError(
        "%s. With it in focus in Designer's editor (the user opens it; open_graph can't reach it), read tools "
        'work with no graph given, and snapshot_graph with no graph keeps a copy' % reason
    )


def _same_graph(a: SDGraph | None, b: SDGraph | None) -> bool:
    """True when a and b are the same graph: the same identifier in the same package (two open
    packages can each have a graph with one name). Packages are told apart by file: copies of one
    file (a snapshot of a saved package opened to recover, a duplicate) share its UID (measured;
    REVIEW.md HLP-53). Only two packages that were never saved are told apart by UID."""
    if a is None or b is None or a.getIdentifier() != b.getIdentifier():
        return False
    pa, pb = a.getPackage(), b.getPackage()
    fa, fb = pa.getFilePath() or '', pb.getFilePath() or ''
    if fa or fb:
        return bool(fa and fb) and os.path.normcase(os.path.normpath(fa)) == os.path.normcase(os.path.normpath(fb))
    return bool(pa.getUID()) and pa.getUID() == pb.getUID()


def _package_name(pkg: SDPackage) -> str:
    """A package as the agent can match it: its file, or for one never saved its UID, as list_snapshots
    and designer_status name it (REVIEW.md SRV-45)."""
    return pkg.getFilePath() or '(an unsaved package, UID %s)' % pkg.getUID()


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
        if any(
            r.getIdentifier() == identifier and isinstance(r, SDSBSCompGraph)
            for p in _PM.getUserPackages()
            if _is_library_package(p)
            for r in p.getChildrenResources(True)
        ):
            raise _library_refusal(
                "No open user graph is named %r; a loaded Designer library graph is, and tools don't find those "
                'by name or edit them' % identifier
            )
        raise RuntimeError('Graph %r not found in open user packages.' % identifier)
    for g in matches:
        if _same_graph(g, current):
            return g
    raise RuntimeError(
        '%d open graphs are named %r (packages: %s); open the one you mean in Designer '
        'or close the others.' % (len(matches), identifier, ', '.join(_package_name(g.getPackage()) for g in matches))
    )


def _graph_to_edit(identifier: str | SDSBSCompGraph | None = None) -> SDSBSCompGraph:
    """find_graph for the helpers that change a graph: with no graph given, the editor's graph can be a
    library one. Designer takes the edit, and every package using that graph sees it (measured; REVIEW.md
    HLP-55). Helpers that only read, and snapshots, use find_graph."""
    g = find_graph(identifier)
    if _is_library_package(g.getPackage()):
        raise _library_refusal("Graph %r belongs to Designer's library, and tools don't edit it" % g.getIdentifier())
    return g


def _refuse_unsaved_dependencies(pkg: SDPackage) -> None:
    """Before any save of pkg. A package using a graph of a never-saved one makes savePackage, savePackageAs and
    saveCopyOfPackageAs open a modal "Save Dependency" file dialog on Designer's main thread: the call waits for a
    person, and a timer calling reject() didn't close it (measured; REVIEW.md SRV-60). A saved dependency, even one with
    unsaved changes or itself using an unsaved package, opens none (measured), so only direct, never-saved ones count."""
    advice: list[str] = []
    open_packages = {p.getUID() for p in _PM.getUserPackages()}
    for dependency in pkg.getDependencies():
        if dependency.getFilePath():
            continue
        used = dependency.getPackage()
        graphs = (
            [r for r in used.getChildrenResources(True) if isinstance(r, SDSBSCompGraph)] if used is not None else []
        )
        what = ', '.join(repr(g.getIdentifier()) for g in graphs) or 'a graph'
        if used is not None:
            what += ' (UID %s)' % used.getUID()
        reached = next((g for g in graphs if _found_by_name(g)), None)
        if used is None or used.getUID() not in open_packages:
            # closed while in use: it stays a dependency, the dialog opens, and deleting the node ends it (measured).
            # No package with no path wasn't seen: a file gone has a path, and saves with no dialog (measured)
            advice.append(
                "%s is in a package closed since, so no tool can save it: delete the nodes using it, or the user saves it from Designer's dialog."
                % what
            )
        elif reached is not None:
            advice.append('%s: save it first, save_package(%r, save_as=...).' % (what, reached.getIdentifier()))
        else:  # every new graph is "New_Graph": the name finds another graph, or is ambiguous (REVIEW.md HLP-67)
            advice.append(
                "%s: save it first; its name finds another graph, so with it in focus in Designer's editor (the user opens it), save_package with no graph and save_as=...."
                % what
            )
    if advice:
        raise RuntimeError(
            '%s uses a graph of a package never saved; Designer would open a dialog asking where to save it and wait for a person, so nothing was saved. %s'
            % (_package_name(pkg), ' '.join(advice))
        )


def _found_by_name(g: SDSBSCompGraph) -> bool:
    """Whether g's name, given to a tool, finds g and not another graph of that name."""
    try:
        return _same_graph(find_graph(g.getIdentifier()), g)
    except RuntimeError:
        return False


def _default_output(node: SDNode, outputs: list[str]) -> tuple[str, str]:
    """(the output to use when none is named, how to say which). The one tagged base colour, else the first: a
    material's first is `diffuse`, black on a metal, so the first can read as a broken node (REVIEW.md HLP-65, HLP-66).
    By its usage tag, not its name: a custom package can call it anything, and a name proves nothing. The tag is on the
    output nodes of the graph an instance refers to (measured); an atomic node has none."""
    listed = ', '.join(outputs)
    try:
        for out in node.getReferencedResource().getOutputNodes():  # type: ignore[union-attr]  # caught below
            ident = out.getAnnotationPropertyValueFromId('identifier')
            tags = out.getAnnotationPropertyValueFromId('usages')
            if ident is None or tags is None:
                continue
            array = tags.get()  # an SDValueArray of SDValueUsage
            names = [array.getItem(i).get().getName().lower() for i in range(array.getSize())]
            name = ident.get()  # an SDValueString
            if 'basecolor' in names and name in outputs:
                return name, "'%s', tagged base colour, of %d (%s)" % (name, len(outputs), listed)
    except (Exception, APIException):
        pass  # not a graph's instance (an atomic node, a bitmap resource), or no such annotation
    return outputs[0], "'%s', the first of %d (%s)" % (outputs[0], len(outputs), listed)


def _output_note(how: str) -> str:
    """What a tool says when it picked one of several outputs: server_tools.core reads it back from this text."""
    return 'no output given: %s; pass output to pick another' % how


def _position(value: Any, what: str = 'position') -> tuple[float, float]:
    """[x, y] as two numbers, checked before anything is created or moved: read after, a bad one
    left the new node (or comment) behind (REVIEW.md HLP-46)."""
    if isinstance(value, (list, tuple)) and len(value) == 2 and not any(isinstance(v, bool) for v in value):
        try:  # numbers, or numeric strings as float() reads them (REVIEW.md HLP-50)
            xy = float(value[0]), float(value[1])
        except (TypeError, ValueError):
            pass
        else:  # not 'nan', 'inf', '1e400': Designer would take them, the print after wouldn't (HLP-51)
            if all(math.isfinite(v) and abs(v) < 1e30 for v in xy):
                return xy
    raise RuntimeError('%s must be [x, y], two numbers, not %r' % (what, value))


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
