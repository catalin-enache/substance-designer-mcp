"""Saving packages (never a Designer library package) and exporting outputs."""

from .core import (
    _PM,
    APIException,
    SDNode,
    SDPackage,
    SDPropertyCategory,
    SDSBSCompGraph,
    SDValueTexture,
    _is_library_package,
    cast,
    find_graph,
    os,
)


def _package_of(identifier: str | None) -> tuple[SDPackage, SDSBSCompGraph | None]:
    """The package to save: never one of Designer's own library packages, which saving would
    overwrite in Designer's install folder."""
    pkg: SDPackage | None
    g: SDSBSCompGraph | None
    if not identifier:
        g = find_graph(None)
        pkg = g.getPackage()
    else:
        pkg = g = None
        for p in _PM.getUserPackages():
            if os.path.normpath(p.getFilePath() or '') == os.path.normpath(os.path.expanduser(identifier)):
                pkg = p
                break
        if pkg is None:
            g = find_graph(identifier)
            pkg = g.getPackage()
    if _is_library_package(pkg):
        raise RuntimeError(
            "%s is one of Designer's library packages; not saving it (saving it elsewhere "
            'would re-point the loaded library itself); to keep a copy, open it in the editor, then '
            'call snapshot_graph with no graph' % pkg.getFilePath()
        )
    return pkg, g


def save_package(identifier: str | None = None, path: str | None = None) -> None:
    """identifier: a graph identifier or a package file path (default: graph open in the UI)."""
    pkg, _ = _package_of(identifier)
    if path:
        path = os.path.abspath(os.path.expanduser(path))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _PM.savePackageAs(pkg, path)
        print('saved package as', path)
    else:
        if not pkg.getFilePath():
            raise RuntimeError('package was never saved; pass a path')
        _PM.savePackage(pkg)
        print('saved', pkg.getFilePath())


def _output_ident(node: SDNode, i: int) -> str:
    try:
        # an SDValueString; a None fails into the except below
        return cast(str, node.getAnnotationPropertyValueFromId('identifier').get())  # type: ignore[union-attr]
    except (Exception, APIException):
        return 'output_%d' % i


def export_outputs(
    identifier: str | SDSBSCompGraph | None, out_dir: str, names: list[str] | None = None, ext: str = 'png'
) -> None:
    """Compute the graph in Designer and save each output node's texture as <identifier>.<ext>."""
    g = find_graph(identifier)
    out_dir = os.path.abspath(os.path.expanduser(out_dir))
    os.makedirs(out_dir, exist_ok=True)
    every = [(_output_ident(node, i), node) for i, node in enumerate(g.getOutputNodes())]
    outputs = [(ident, node) for ident, node in every if not names or ident in names]
    # two outputs with one name would write one file, and the first would be lost (REVIEW.md HLP-34);
    # names differing only in case too, on the usual macOS and Windows file systems (HLP-36)
    idents = [ident for ident, _ in outputs]
    folded = [ident.lower() for ident in idents]
    twice = sorted({ident for ident in idents if folded.count(ident.lower()) > 1})
    if twice:
        raise RuntimeError(
            'several output nodes are named %s (file names ignore case); give each its own '
            'identifier' % ', '.join(twice)
        )
    g.compute()
    saved = []
    for ident, node in outputs:
        for prop in node.getProperties(SDPropertyCategory.Output):
            value = cast(SDValueTexture | None, node.getPropertyValue(prop))
            texture = value.get() if value is not None else None
            if texture is None:
                continue
            path = os.path.join(out_dir, '%s.%s' % (ident, ext))
            texture.save(path)
            size = texture.getSize()
            saved.append('%s  %dx%d %s' % (os.path.basename(path), size.x, size.y, texture.getPixelFormat()))
    if not saved:
        # a typo-only request: say which outputs there are (REVIEW.md HLP-36)
        raise RuntimeError(
            'no outputs exported (names %r; the outputs: %s)'
            % (names, ', '.join(sorted(i for i, _ in every)) or 'none')
        )
    print('exported %d file(s) to %s:' % (len(saved), out_dir))
    print('\n'.join(saved))
    missing = [n for n in (names or []) if n not in idents]
    if missing:  # a typo in outputs= would otherwise go unnoticed (REVIEW.md HLP-34)
        print('no output named %s (the outputs: %s)' % (', '.join(missing), ', '.join(sorted(i for i, _ in every))))
