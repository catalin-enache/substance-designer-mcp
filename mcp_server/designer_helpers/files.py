"""Package files: snapshot copies, and saving, unloading and reloading for edits the API can't
make."""

from .core import _APP, _PM, Any, SDSBSCompGraph, _is_library_package, _same_graph, find_graph, os


def save_package_copy(identifier: str | SDSBSCompGraph | None, path: str) -> None:
    """Write a copy of the graph's package to `path` without changing the package's own file
    path or saved state (saveCopyOfPackageAs)."""
    g = find_graph(identifier)
    pkg = g.getPackage()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _PM.saveCopyOfPackageAs(pkg, path)
    print('COPY=' + path)
    print('PACKAGE=' + (pkg.getFilePath() or ''))
    print('PACKAGE_UID=' + package_uid(pkg))
    print('GRAPH=' + g.getIdentifier())


def package_uid(pkg: Any) -> str:
    """The package's UID: what tells two unsaved packages apart (no file path) when their graphs
    share a name, as every new graph is "New_Graph" (REVIEW.md SRV-34). Not mHandle, which differs
    for every Python object wrapping the same package (measured)."""
    return str(pkg.getUID() or '')


def graph_in_file(path: str, identifier: str) -> SDSBSCompGraph:
    """The graph with this identifier in the open package saved at `path`: unlike find_graph's
    identifier alone, never another package's graph of the same name (REVIEW.md SRV-34)."""
    want = os.path.normpath(path)
    for pkg in _PM.getUserPackages():
        if os.path.normpath(pkg.getFilePath() or '') == want:
            for res in pkg.getChildrenResources(True):
                if isinstance(res, SDSBSCompGraph) and res.getIdentifier() == identifier:
                    return res
    raise RuntimeError('graph %r not found in the package %s' % (identifier, path))


def package_file_of(identifier: str | SDSBSCompGraph | None, save: bool = False) -> None:
    """Report the graph's package file (for edits the API can't make); with save, save it first."""
    g = find_graph(identifier)
    pkg = g.getPackage()
    if _is_library_package(pkg):
        # with no graph given, the editor's graph can be a library one: never edit Designer's own
        # files (REVIEW.md HLP-33)
        raise RuntimeError("%s is in one of Designer's library packages; its file is not edited" % g.getIdentifier())
    path = pkg.getFilePath()
    if not path:
        raise RuntimeError('the package has never been saved; save it first (the save_package tool, save_as=...)')
    if save:
        _PM.savePackage(pkg)
    current = _APP.getQtForPythonUIMgr().getCurrentGraph()  # type: ignore[no-untyped-call]  # sd: no annotations
    print('FILE=' + path)
    print('GRAPH=' + g.getIdentifier())
    print('OPEN=' + ('1' if _same_graph(current, g) else '0'))


def unload_package_file(path: str) -> None:
    """Close every open copy of the package at `path` (its graph views are torn down when this
    call returns to Designer's event loop; load it again in a separate call)."""
    norm = os.path.normpath(path)
    matches = [p for p in _PM.getUserPackages() if os.path.normpath(p.getFilePath() or '') == norm]
    if any(p.isModified() for p in matches):
        # edited after the save that came before the file edit: never drop those changes
        raise RuntimeError(
            '%s has unsaved changes (made after it was saved for the edit); not unloading it. '
            'Save it and try again.' % path
        )
    count = 0
    for p in matches:
        _PM.unloadUserPackage(p)
        count += 1
    print('unloaded %d package(s): %s' % (count, path))


def load_package_file(path: str) -> None:
    _PM.loadUserPackage(path)
    print('loaded', path)
