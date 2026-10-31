"""Snapshots and diffs: snapshot_graph, list_snapshots, diff_graph, and the .sbs model they read."""

import os
import re
import shutil
import tempfile
import time
import xml.etree.ElementTree as ET
from typing import TypedDict, cast

from mcp.server.mcpserver.exceptions import ToolError

from .core import _bridge, _checked, _helpers_call, _tool

SNAPSHOT_DIR = os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), '.sd_mcp', 'snapshots')


def _safe_name(text: str) -> str:
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', text).strip('_') or 'snapshot'


def _copy_package(graph: str | None, path: str) -> dict[str, str]:
    text = _bridge(_helpers_call('save_package_copy(%r, %r)' % (graph, path)), timeout=120)
    found = dict(re.findall(r'^(COPY|PACKAGE|GRAPH)=(.*)$', text, re.M))
    if 'COPY' not in found or not os.path.exists(path):
        raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'could not copy package')
    return found


@_tool()
def snapshot_graph(graph: str | None = None, label: str | None = None) -> str:
    """Save a snapshot of a graph's package (a full .sbs copy) before risky work. It doesn't
    change the open package, its file or its saved state. Compare later with diff_graph; the
    snapshot .sbs can also be opened in Designer to recover anything. Bitmaps aren't copied: the
    snapshot points to the files the package uses (its .resources folder, linked images). Snapshots live in
    ~/.sd_mcp/snapshots/<graph>/ (override with SD_SNAPSHOT_DIR)."""
    # Designer writes resource paths (bitmaps) relative to the copy, so it is saved where it
    # stays: moved afterwards, those paths would point nowhere
    gid = _checked(_bridge(_helpers_call('print("GRAPH=" + find_graph(%r).getIdentifier())' % graph), timeout=60))
    gid = cast(re.Match[str], re.search(r'^GRAPH=(.*)$', gid, re.M)).group(1)  # printed, or _checked raised
    path = _new_snapshot_path(gid, label)
    info = _copy_package(graph, path)
    return 'snapshot of %s saved: %s' % (info['GRAPH'], path)


_SNAPSHOT_NAME = re.compile(r'^\d{8}-\d{6}(?:_\d+)?(?:-(.*))?\.sbs$')


def _new_snapshot_path(graph_id: str, label: str | None = None) -> str:
    """<SNAPSHOT_DIR>/<graph>/<YYYYmmdd-HHMMSS>[_n][-label].sbs, never overwriting one taken in
    the same second."""
    folder = os.path.join(SNAPSHOT_DIR, _safe_name(graph_id))
    os.makedirs(folder, exist_ok=True)
    stamp, tail = time.strftime('%Y%m%d-%H%M%S'), ('-' + _safe_name(label) if label else '') + '.sbs'
    path, n = os.path.join(folder, stamp + tail), 1
    while os.path.exists(path):
        n += 1
        path = os.path.join(folder, '%s_%d%s' % (stamp, n, tail))
    return path


def _snapshots(graph_id: str) -> list[str]:
    folder = os.path.join(SNAPSHOT_DIR, _safe_name(graph_id))
    if not os.path.isdir(folder):
        return []
    # oldest first by when the content was written: names alone misorder two snapshots taken in
    # the same second (set_link_display's live graph and its copy2 of the older saved file)
    paths = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.sbs')]
    return sorted(paths, key=lambda p: (os.stat(p).st_mtime_ns, p))


@_tool()
def list_snapshots(graph: str | None = None) -> str:
    """List saved snapshots, newest last (by when their content was written; set_link_display's
    copy of the saved file counts from when that file was saved). graph: graph identifier
    (default: all graphs)."""
    graphs = [_safe_name(graph)] if graph else (sorted(os.listdir(SNAPSHOT_DIR)) if os.path.isdir(SNAPSHOT_DIR) else [])
    lines: list[str] = []
    for gid in graphs:
        for path in _snapshots(gid):
            lines.append('%s  %s' % (gid, path))
    return '\n'.join(lines) if lines else 'No snapshots%s.' % (' for ' + graph if graph else '')


def _found(el: ET.Element, path: str) -> ET.Element:
    """el.find(path), typed as found: for an element the .sbs format always has, or one checked
    just before. A missing one still fails as it did, on the attribute access that follows."""
    return cast(ET.Element, el.find(path))


def _v(el: ET.Element, path: str) -> str:
    """el.find(path).get('v') for such an element (the format always gives it a v)."""
    return cast(str, _found(el, path).get('v'))


def _xml_graph(root: ET.Element, graph_id: str, where: str) -> ET.Element:
    """The <graph> element with this identifier in a parsed .sbs."""
    g = next(
        (x for x in root.iter('graph') if x.find('identifier') is not None and _v(x, 'identifier') == graph_id), None
    )
    if g is None:
        raise ToolError('graph %r not found in %s' % (graph_id, where))
    return g


# How a .sbs stores a size parameter's inheritance (<relativeTo>). The file's numbers differ from
# the sd API's SDPropertyInheritanceMethod (input 0, parent 1, absolute 2); measured in Designer 16
# and re-checked by the self-test ("designer facts"). The default isn't stored at all: relative to
# parent for a graph, relative to input for a node.
_RELATIVE_TO: dict[str | None, str] = {'0': 'absolute', '1': 'relative to parent', '2': 'relative to input'}


class _NodeModel(TypedDict):
    kind: str
    params: dict[str, str]
    links: set[tuple[str, str]]  # (input, source node[.output])
    display: dict[tuple[str, str], str]  # link -> 'portal' or 'wire'
    pos: str | None


class _GraphModel(TypedDict):
    nodes: dict[str, _NodeModel]
    inputs: dict[str, str | None]
    size: dict[str, str]


def _graph_model(sbs_path: str, graph_id: str) -> _GraphModel:
    """Parse one graph of a .sbs into comparable dicts."""
    root = ET.parse(sbs_path).getroot()
    g = _xml_graph(root, graph_id, sbs_path)

    def value_of(param: ET.Element) -> str:
        pv = param.find('paramValue')
        if pv is None or not len(pv):
            return ''
        el = pv[0]
        return 'function' if el.tag == 'dynamicValue' else (el.get('v') or '')

    nodes: dict[str, _NodeModel] = {}
    for n in _found(g, 'compNodes') if g.find('compNodes') is not None else []:
        uid = _v(n, 'uid')
        impl = n.find('compImplementation')
        kind = '?'
        if impl is not None and len(impl):
            el = impl[0]
            if el.tag == 'compFilter':
                kind = _v(el, 'filter')
            elif el.tag == 'compInstance':
                path = _v(el, 'path') if el.find('path') is not None else ''
                kind = 'instance:' + re.sub(r'^pkg:///|\?.*$', '', path)
            elif el.tag == 'compOutputBridge':
                kind = 'output'
            elif el.tag == 'compInputBridge':
                kind = 'input'
        # atomic and library (instance) nodes store parameters the same way
        params = {_v(prm, 'name'): value_of(prm) for prm in (impl.iter('parameter') if impl is not None else [])}
        links: set[tuple[str, str]] = set()
        display: dict[tuple[str, str], str] = {}
        conns = n.find('connections')
        for c in conns if conns is not None else []:
            out = c.find('connRefOutput')
            # which output of the source matters: bevel.height and bevel.normal are different links
            src = _v(c, 'connRef') + ('.' + cast(str, out.get('v')) if out is not None else '')
            key = (_v(c, 'identifier'), src)
            links.add(key)
            dt = c.find('displayType')
            display[key] = 'portal' if dt is not None and dt.get('v') == '1' else 'wire'
        pos = n.find('GUILayout/gpos')
        nodes[uid] = {
            'kind': kind,
            'params': params,
            'links': links,
            'display': display,
            'pos': pos.get('v') if pos is not None else '',
        }
    inputs: dict[str, str | None] = {}
    for pi in g.iter('paraminput'):
        dv = pi.find('defaultValue')
        inputs[_v(pi, 'identifier')] = dv[0].get('v') if dv is not None and len(dv) else ''
    size: dict[str, str] = {}
    for prm in _found(g, 'baseParameters') if g.find('baseParameters') is not None else []:
        rel = prm.find('relativeTo')
        size[_v(prm, 'name')] = '%s (%s)' % (
            value_of(prm),
            _RELATIVE_TO.get(
                rel.get('v') if rel is not None else '', 'relativeTo %s' % (rel.get('v') if rel is not None else '?')
            ),
        )
    size.setdefault('outputsize', '(default: relative to parent)')
    for opt in g.iter('option'):
        if opt.find('name') is not None and _v(opt, 'name') == 'defaultParentSize':
            size['defaultParentSize'] = _v(opt, 'value')
    return {'nodes': nodes, 'inputs': inputs, 'size': size}


def _diff_models(old: _GraphModel, new: _GraphModel, show_positions: bool) -> tuple[str, list[str]]:
    out: list[str] = []
    on, nn = old['nodes'], new['nodes']
    added = [i for i in nn if i not in on]
    removed = [i for i in on if i not in nn]
    for i in added:
        out.append('+ node %s %s' % (i, nn[i]['kind']))
    for i in removed:
        out.append('- node %s %s' % (i, on[i]['kind']))
    moved = 0
    va: str | None  # parameter values, then graph inputs (None: absent)
    vb: str | None
    for i in (i for i in nn if i in on):
        a, b = on[i], nn[i]
        for name in sorted(set(a['params']) | set(b['params'])):
            va, vb = a['params'].get(name, '(default)'), b['params'].get(name, '(default)')
            if va != vb:
                out.append('~ node %s %s: %s %s -> %s' % (i, b['kind'], name, va, vb))
        for port, src in sorted(b['links'] - a['links']):
            out.append('~ node %s %s: link %s <- %s added' % (i, b['kind'], port, src))
        for port, src in sorted(a['links'] - b['links']):
            out.append('~ node %s %s: link %s <- %s removed' % (i, b['kind'], port, src))
        for key in sorted(a['links'] & b['links']):
            if a['display'].get(key) != b['display'].get(key):
                out.append(
                    '~ node %s %s: link %s <- %s shown as %s (was %s)'
                    % (i, b['kind'], key[0], key[1], b['display'].get(key), a['display'].get(key))
                )
        if a['pos'] != b['pos']:
            moved += 1
            if show_positions:
                out.append('~ node %s %s: moved %s -> %s' % (i, b['kind'], a['pos'], b['pos']))
    for name in sorted(set(old['inputs']) | set(new['inputs'])):
        va, vb = old['inputs'].get(name), new['inputs'].get(name)
        if va is None:
            out.append('+ graph input %s = %s' % (name, vb))
        elif vb is None:
            out.append('- graph input %s' % name)
        elif va != vb:
            out.append('~ graph input %s: %s -> %s' % (name, va, vb))
    for name in sorted(set(old['size']) | set(new['size'])):
        if old['size'].get(name) != new['size'].get(name):
            out.append('~ graph %s: %s -> %s' % (name, old['size'].get(name), new['size'].get(name)))
    summary = '%d added, %d removed, %d changed line(s), %d node(s) moved' % (
        len(added),
        len(removed),
        len([l for l in out if l.startswith('~') and ': moved ' not in l]),
        moved,
    )
    return summary, out


@_tool()
def diff_graph(graph: str | None = None, against: str = 'saved', show_positions: bool = False) -> str:
    """Show what changed in a graph: nodes added/removed, parameter changes, links
    added/removed, exposed inputs and size. against: 'saved' (the package's file on disk),
    'latest' (newest snapshot), a snapshot label, or a .sbs path. The live graph is read
    without modifying it. Positions are only counted unless show_positions=True."""
    tmp_dir = tempfile.mkdtemp(prefix='sd_diff_')
    try:
        info = _copy_package(graph, os.path.join(tmp_dir, 'live.sbs'))
        gid = info['GRAPH']
        if against == 'saved':
            ref = info.get('PACKAGE')
            if not ref or not os.path.exists(ref):
                raise ToolError('the package has never been saved; diff against a snapshot instead')
        elif against == 'latest':
            snaps = _snapshots(gid)
            if not snaps:
                raise ToolError('no snapshots for %s; take one with snapshot_graph' % gid)
            ref = snaps[-1]
        elif against.endswith('.sbs'):
            ref = os.path.abspath(os.path.expanduser(against))
        else:
            matches = [
                p
                for p in _snapshots(gid)
                if (_SNAPSHOT_NAME.match(os.path.basename(p)) or [None, None])[1] == _safe_name(against)
            ]
            if not matches:
                raise ToolError('no snapshot matching %r; see list_snapshots' % against)
            ref = matches[-1]
        if not os.path.isfile(ref):
            raise ToolError('no such file: %s' % ref)  # REVIEW.md SRV-30
        try:
            reference = _graph_model(ref, gid)
        except ET.ParseError as e:
            raise ToolError('%s is not a readable .sbs (%s)' % (ref, e)) from e
        summary, lines = _diff_models(reference, _graph_model(os.path.join(tmp_dir, 'live.sbs'), gid), show_positions)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    head = '%s (live) vs %s: %s' % (gid, ref, summary)
    if lines:
        return head + '\n' + '\n'.join(lines)
    moved_only = not summary.endswith(' 0 node(s) moved')
    return head + (
        '\nOnly node positions differ (show_positions=True lists them).' if moved_only else '\nNo differences.'
    )
