"""Finding and understanding nodes and graphs: describe_graph, describe_node, search_nodes."""

import html
import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from typing import Annotated, TypedDict, cast

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from .core import Graph, _bridge, _checked, _helpers_call, _tool
from .functions import NO_PARAMETER, NODE_OR_FUNCTION


@_tool(read_only=True, destructive=False, idempotent=True, open_world=False)
def describe_graph(
    graph: Graph = None,
    node_ids: Annotated[
        list[str] | None,
        Field(
            description="A few nodes to focus on, the graph's or the function's (ids that name no node are listed as "
            'not found).'
        ),
    ] = None,
    include_params: Annotated[
        bool,
        Field(
            description="Adds, for a graph's nodes, every parameter that differs from its default, and each one driven "
            "by a graph input or a function (`param <- graph input 'x'`, `param <- a function`); a function with no "
            "output node drives nothing and is noted beside the parameter's value; an FX-Map's inner functions are "
            "listed too. A function's nodes always show their constant. A Gradient Map's keys or a Curve's points "
            'past 16 show as their count, unless node_ids focuses on the node.'
        ),
    ] = False,
    limit: Annotated[int, Field(description='Caps how many nodes are listed (the rest are counted).')] = 400,
    node_id: Annotated[
        str | None,
        Field(
            description="Lists this node's function instead of the graph: a Pixel or Value Processor's own, or with "
            "parameter any parameter's."
        ),
    ] = None,
    parameter: Annotated[
        str | None,
        Field(
            description="With node_id, the parameter whose function is listed (default: a Pixel Processor's "
            "perpixel, a Value Processor's function)."
        ),
    ] = None,
    function: Annotated[
        str | None,
        Field(
            description="Lists a function graph of the graph's package instead, by identifier, after its inputs. Not "
            'with node_id.'
        ),
    ] = None,
) -> str:
    """List a graph's nodes: id, type (atomic name or instance:<library graph>), position,
    an output node's identifier, label and usage, and incoming connections (`input<-sourceNodeId.output`); and, but
    focused on node_ids, its package's function graphs, each with its inputs and its output's type. With node_id or function, it lists a
    function's nodes instead, in the same form, each with its constant and its output's types, and the output node. A
    node's function also says each input value (#name) it reads and what feeds it, so that one left reading another
    type, or nothing, shows."""
    if node_id and function:
        raise ToolError(NODE_OR_FUNCTION + ', not both.')
    if parameter and function:
        raise ToolError(NO_PARAMETER)
    if parameter and not node_id:
        raise ToolError("parameter is a node's: give node_id too.")
    if node_id or function:
        call = 'describe_function(%r, %r, %r, %r, %r, %d)' % (
            graph,
            node_id or None,
            parameter or None,
            function or None,
            node_ids,
            limit,
        )
    else:
        call = 'describe_graph(%r, %r, %r, %d)' % (graph, node_ids, include_params, limit)
    return _checked(_bridge(_helpers_call(call), timeout=60))


@_tool(read_only=True, destructive=False, idempotent=True, open_world=False)
def describe_node(
    definition: Annotated[
        str,
        Field(
            description="Atomic name ('levels', 'blend', 'sbs::compositing::normal'), library package "
            "'<file>[/<graph id>]' as found in Designer's packages folder or a subfolder ('tile_generator', "
            "'hbao.sbs/hbao', 'materials/pbr/bricks_001'), or a function node's definition ('sbs::function::add', or "
            "'add' as a function's listing gives it; a name another node has too, such as 'pow', gives that node, "
            'then names the function node).'
        ),
    ],
) -> str:
    """Show a node type's connectors and parameters (ids, types, labels, defaults, enum values). For a function node,
    every type each input and its output take."""
    return _checked(_bridge(_helpers_call('describe_node(%r)' % definition), timeout=60))


class _LibraryEntry(TypedDict):
    file: str
    graph: str
    label: str
    category: str
    description: str
    hidden: bool
    url: str  # the graph with its groups: what findResourceFromUrl needs (measured; REVIEW.md SRV-56)


class _FunctionEntry(TypedDict):
    """One of Designer's function nodes (sbs::function::*), as its module describes it."""

    definition: str  # 'sbs::function::add'
    label: str
    description: str


class _LibraryIndex(TypedDict, total=False):
    entries: list[_LibraryEntry]
    atomic: list[str]
    functions: list[_FunctionEntry]
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


def _flat(description: str) -> str:
    """A description of Designer's, its HTML tags taken out, then its entities read as the characters they stand for
    (REVIEW.md HLP-246), on one line."""
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', description or ''))).strip()


def _raise(error: OSError) -> None:
    raise error


def _library_index() -> _LibraryIndex:
    """Scan Designer's library packages once: graph id, label, category, description."""
    if 'entries' in _LIBRARY_CACHE:
        return _LIBRARY_CACHE
    lines = _checked(_bridge(_helpers_call('list_atomic()'), timeout=60)).splitlines()
    resources = next(l.split('=', 1)[1] for l in lines if l.startswith('RESOURCES_DIR='))
    atomic = [l.split('=', 1)[1] for l in lines if l.startswith('ATOMIC=')]
    functions: list[_FunctionEntry] = [
        {'definition': d, 'label': label, 'description': description}
        for d, label, description in (l.split('=', 1)[1].split('\t', 2) for l in lines if l.startswith('FUNCTION='))
    ]
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
    _LIBRARY_CACHE.update({'entries': entries, 'atomic': atomic, 'functions': functions, 'pkg_dir': pkg_dir})
    return _LIBRARY_CACHE


@_tool(read_only=True, destructive=False, idempotent=True, open_world=False)
def search_nodes(
    query: Annotated[str, Field(description='Words in the query must all match.')],
    limit: Annotated[int, Field(description='Caps how many results are listed (the rest are counted).')] = 30,
    include_hidden: Annotated[
        bool, Field(description='Also the graphs Designer hides from its library (helpers, some materials).')
    ] = False,
) -> str:
    """Find node types by name, label, category or description, across atomic nodes,
    Designer's whole library of compositing graphs (not just loaded packages; not its function graphs),
    its ready-made materials included, and Designer's function nodes (sbs::function::*). When nothing else matches, the
    result says how many hidden graphs do. Results show the `definition` to pass to describe_node and, but a function
    node's, to apply_edits' add op."""
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
            desc = _flat(e['description'])
            name = e['label'] or e['graph']
            out.append(
                (
                    min(rank(name), rank(e['graph'])),
                    'library  %-28s definition=%r  [%s]%s'
                    % (name, definition, e['category'], ('  ' + desc[:90]) if desc else ''),
                )
            )
    for f in index['functions']:
        short = f['definition'].removeprefix('sbs::function::')
        if matches(' '.join((short, f['definition'], f['label'], f['description']))):
            desc = _flat(f['description'])
            out.append(
                (
                    min(rank(short), rank(f['label'])),
                    'function %-28s definition=%r  [%s]%s'
                    % (short, f['definition'], f['label'], ('  ' + desc[:90]) if desc else ''),
                )
            )
    if not out:
        # not "no match" for what Designer ships, only hides from its library (REVIEW.md SRV-55). Only here: half
        # its graphs are hidden, so next to results this came on 24 of 25 queries (SRV-58)
        also = ' %d hidden graph(s) match too: include_hidden=True' % hidden if hidden else ''
        return 'No node types match %r.%s' % (query, also)

    def rank_of(item: tuple[int, str]) -> int:
        return item[0]

    lines = [line for _, line in sorted(out, key=rank_of)]
    more = '' if len(lines) <= limit else '\n... %d more (refine the query or raise limit)' % (len(lines) - limit)
    return '\n'.join(lines[:limit]) + more
