"""Finding and understanding nodes and graphs: describe_graph, describe_node, search_nodes."""

import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from typing import TypedDict, cast

from .core import _bridge, _checked, _helpers_call, _tool


@_tool()
def describe_graph(
    graph: str | None = None, node_ids: list[str] | None = None, include_params: bool = False, limit: int = 400
) -> str:
    """List a graph's nodes: id, type (atomic name or instance:<library graph>), position and
    incoming connections (`input<-sourceNodeId.output`). `graph` is the graph identifier
    (default: the graph open in Designer's UI). `include_params` adds every parameter that
    differs from its default, and each one driven by a graph input or a function
    (`param <- graph input 'x'`, `param <- a function`); a function with no output node drives nothing
    and is noted beside the parameter's value; an FX-Map's inner functions are listed too. Use `node_ids` to focus on a few nodes (ids that
    name no node are listed as not found); `limit` caps how many nodes are listed (the rest are
    counted)."""
    return _checked(
        _bridge(_helpers_call('describe_graph(%r, %r, %r, %d)' % (graph, node_ids, include_params, limit)), timeout=60)
    )


@_tool()
def describe_node(definition: str) -> str:
    """Show a node type's connectors and parameters (ids, types, labels, defaults, enum values).
    `definition`: atomic name ('levels', 'blend', 'sbs::compositing::normal') or library package
    '<file>[/<graph id>]' as found in Designer's packages folder or a subfolder ('tile_generator',
    'hbao.sbs/hbao', 'materials/pbr/bricks_001')."""
    return _checked(_bridge(_helpers_call('describe_node(%r)' % definition), timeout=60))


class _LibraryEntry(TypedDict):
    file: str
    graph: str
    label: str
    category: str
    description: str
    hidden: bool
    url: str  # the graph with its groups: what findResourceFromUrl needs (measured; REVIEW.md SRV-56)


class _LibraryIndex(TypedDict, total=False):
    entries: list[_LibraryEntry]
    atomic: list[str]
    pkg_dir: str


_LIBRARY_CACHE: _LibraryIndex = {}


def _graphs_in(element: ET.Element, groups: tuple[str, ...] = ()) -> Iterator[tuple[str, ET.Element]]:
    """(the graph's path through its groups, the graph) for every graph under element."""
    for child in element:
        ident = child.find('identifier')
        name = cast(str, ident.get('v')) if ident is not None else None
        if child.tag == 'graph':
            if name is not None:
                yield '/'.join((*groups, name)), child
        else:
            yield from _graphs_in(child, (*groups, name) if child.tag == 'group' and name else groups)


def _raise(error: OSError) -> None:
    raise error


def _library_index() -> _LibraryIndex:
    """Scan Designer's library packages once: graph id, label, category, description."""
    if 'entries' in _LIBRARY_CACHE:
        return _LIBRARY_CACHE
    lines = _checked(_bridge(_helpers_call('list_atomic()'), timeout=60)).splitlines()
    resources = next(l.split('=', 1)[1] for l in lines if l.startswith('RESOURCES_DIR='))
    atomic = [l.split('=', 1)[1] for l in lines if l.startswith('ATOMIC=')]
    pkg_dir = os.path.join(resources, 'packages')
    entries: list[_LibraryEntry] = []
    # with its subfolders: 30 of Designer 16's packages are ready-made materials in materials/pbr
    files = sorted(
        os.path.relpath(os.path.join(folder, name), pkg_dir).replace(os.sep, '/')
        for folder, _, names in os.walk(pkg_dir, onerror=_raise)  # os.walk would swallow it (REVIEW.md SRV-57)
        for name in names
        if name.endswith('.sbs')
    )
    for file_name in files:
        try:
            root = ET.parse(os.path.join(pkg_dir, file_name)).getroot()
        except ET.ParseError:
            continue
        for url, g in _graphs_in(root):
            attrs = g.find('attributes')

            def attr(tag: str) -> str:
                el = attrs.find(tag) if attrs is not None else None  # noqa: B023 (called in this iteration only)
                return cast(str, el.get('v')) if el is not None else ''  # .sbs value elements carry v

            entries.append(
                {
                    'file': file_name,
                    'graph': url.rsplit('/', 1)[-1],
                    'url': url,
                    'label': attr('label'),
                    'category': attr('category'),
                    'description': attr('description'),
                    'hidden': (attr('hideInLibrary') or '0') == '1',
                }
            )
    _LIBRARY_CACHE.update({'entries': entries, 'atomic': atomic, 'pkg_dir': pkg_dir})
    return _LIBRARY_CACHE


@_tool()
def search_nodes(query: str, limit: int = 30, include_hidden: bool = False) -> str:
    """Find node types by name, label, category or description, across atomic nodes and
    Designer's whole library of compositing graphs (not just loaded packages; not its function graphs),
    its ready-made materials included.
    include_hidden: also the graphs Designer hides from its library (helpers, some materials); when
    nothing else matches, the result says how many of those do. Results show the `definition`
    to pass to describe_node and to apply_edits' add op. Words in the query must all match."""
    index = _library_index()
    words = [w.lower() for w in query.split()]

    def matches(text: str) -> bool:
        text = text.lower()
        return all(w in text for w in words)

    q = query.lower().strip()

    def rank(name: str) -> int:
        # exact name, then name prefix, then all words in the name, then description-only hits
        name = name.lower()
        return 0 if name == q else 1 if name.startswith(q) else 2 if matches(name) else 3

    out: list[tuple[int, str]] = []
    for a in index['atomic']:
        short = a.replace('sbs::compositing::', '')
        if matches(short + ' ' + a):
            out.append((rank(short), 'atomic   %-28s definition=%r' % (short, short)))
    hidden = 0
    for e in index['entries']:
        haystack = ' '.join((e['file'], e['graph'], e['label'], e['category'], e['description']))
        if e['hidden'] and not include_hidden:
            hidden += matches(haystack)
            continue
        if matches(haystack):
            base = e['file'][:-4]
            definition = base if e['url'] == base.rsplit('/', 1)[-1] else '%s/%s' % (e['file'], e['url'])
            desc = re.sub(r'<[^>]+>', ' ', e['description'] or '').replace('\n', ' ')
            desc = re.sub(r'\s+', ' ', desc).strip()
            name = e['label'] or e['graph']
            out.append(
                (
                    min(rank(name), rank(e['graph'])),
                    'library  %-28s definition=%r  [%s]%s'
                    % (name, definition, e['category'], ('  ' + desc[:90]) if desc else ''),
                )
            )
    if not out:
        # not "no match" for what Designer ships, only hides from its library (REVIEW.md SRV-55). Only here: half
        # its graphs are hidden, so next to results this came on 24 of 25 queries (SRV-58)
        also = ' %d hidden graph(s) match too: include_hidden=True' % hidden if hidden else ''
        return 'No node types match %r.%s' % (query, also)
    lines = [line for _, line in sorted(out, key=lambda item: item[0])]
    more = '' if len(lines) <= limit else '\n... %d more (refine the query or raise limit)' % (len(lines) - limit)
    return '\n'.join(lines[:limit]) + more
