"""Finding and understanding nodes and graphs: describe_graph, describe_node, search_nodes."""

import os
import re
import xml.etree.ElementTree as ET
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
    (`param <- graph input 'x'`, `param <- a function`). Use `node_ids` to focus on a few nodes; `limit` caps how many
    nodes are listed (the rest are counted)."""
    return _checked(
        _bridge(_helpers_call('describe_graph(%r, %r, %r, %d)' % (graph, node_ids, include_params, limit)), timeout=60)
    )


@_tool()
def describe_node(definition: str) -> str:
    """Show a node type's connectors and parameters (ids, types, labels, defaults, enum values).
    `definition`: atomic name ('levels', 'blend', 'sbs::compositing::normal') or library package
    '<file>[/<graph id>]' as found in Designer's packages folder ('tile_generator', 'hbao.sbs/hbao')."""
    return _checked(_bridge(_helpers_call('describe_node(%r)' % definition), timeout=60))


class _LibraryEntry(TypedDict):
    file: str
    graph: str
    label: str
    category: str
    description: str
    hidden: bool


class _LibraryIndex(TypedDict, total=False):
    entries: list[_LibraryEntry]
    atomic: list[str]
    pkg_dir: str


_LIBRARY_CACHE: _LibraryIndex = {}


def _library_index() -> _LibraryIndex:
    """Scan Designer's library packages once: graph id, label, category, description."""
    if 'entries' in _LIBRARY_CACHE:
        return _LIBRARY_CACHE
    lines = _checked(_bridge(_helpers_call('list_atomic()'), timeout=60)).splitlines()
    resources = next(l.split('=', 1)[1] for l in lines if l.startswith('RESOURCES_DIR='))
    atomic = [l.split('=', 1)[1] for l in lines if l.startswith('ATOMIC=')]
    pkg_dir = os.path.join(resources, 'packages')
    entries: list[_LibraryEntry] = []
    for file_name in sorted(os.listdir(pkg_dir)):
        if not file_name.endswith('.sbs'):
            continue
        try:
            root = ET.parse(os.path.join(pkg_dir, file_name)).getroot()
        except ET.ParseError:
            continue
        for g in root.iter('graph'):
            ident = g.find('identifier')
            if ident is None:
                continue
            attrs = g.find('attributes')

            def attr(tag: str) -> str:
                el = attrs.find(tag) if attrs is not None else None  # noqa: B023 (called in this iteration only)
                return cast(str, el.get('v')) if el is not None else ''  # .sbs value elements carry v

            entries.append(
                {
                    'file': file_name,
                    'graph': cast(str, ident.get('v')),
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
    Designer's whole node library (not just loaded packages). Results show the `definition`
    to pass to add_node / describe_node. Words in the query must all match."""
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
    for e in index['entries']:
        if e['hidden'] and not include_hidden:
            continue
        haystack = ' '.join((e['file'], e['graph'], e['label'], e['category'], e['description']))
        if matches(haystack):
            base = e['file'][:-4]
            definition = base if e['graph'] == base else '%s/%s' % (e['file'], e['graph'])
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
        return 'No node types match %r.' % query
    lines = [line for _, line in sorted(out, key=lambda item: item[0])]
    more = '' if len(lines) <= limit else '\n... %d more (refine the query or raise limit)' % (len(lines) - limit)
    return '\n'.join(lines[:limit]) + more
