"""Snapshots and diffs: snapshot_graph, list_snapshots, diff_graph, and the .sbs model they read."""

import contextlib
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator
from typing import TypedDict, cast

from mcp.server.mcpserver.exceptions import ToolError

from .core import _bridge, _checked, _helpers_call, _tool

SNAPSHOT_DIR = os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), '.sd_mcp', 'snapshots')


def _safe_name(text: str) -> str:
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', text).strip('_') or 'snapshot'


def _copy_package(graph: str | None, path: str) -> dict[str, str]:
    text = _bridge(_helpers_call('save_package_copy(%r, %r)' % (graph, path)), timeout=120)
    found = dict(re.findall(r'^(COPY|PACKAGE|PACKAGE_UID|GRAPH)=(.*)$', text, re.M))
    if 'COPY' not in found or not os.path.exists(path):
        raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'could not copy package')
    return found


@_tool()
def snapshot_graph(graph: str | None = None, label: str | None = None) -> str:
    """Save a snapshot of a graph's package (a full .sbs copy) before risky work. It doesn't
    change the open package, its file or its saved state. Compare later with diff_graph; the
    snapshot .sbs can also be opened in Designer to recover anything. Bitmaps aren't copied: the
    snapshot points to the files the package uses (its .resources folder, linked images). Snapshots live in
    ~/.sd_mcp/snapshots/<graph>/ (override with SD_SNAPSHOT_DIR), each with a note of the package it
    came from, so two packages' graphs of one name don't share them. A snapshot of an unsaved package
    also gets a UID of its own, so opened to recover it is a package of its own wherever it is saved;
    a saved package's snapshot is Designer's exact copy. A package using a graph of a never-saved package
    is refused, as in save_package."""
    # Designer writes resource paths (bitmaps) relative to the copy, so it is saved where it
    # stays: moved afterwards, those paths would point nowhere
    gid = _checked(_bridge(_helpers_call('print("GRAPH=" + find_graph(%r).getIdentifier())' % graph), timeout=60))
    gid = cast(re.Match[str], re.search(r'^GRAPH=(.*)$', gid, re.M)).group(1)  # printed, or _checked raised
    path = _new_snapshot_path(gid, label)
    with _whole_or_none(path):
        info = _copy_package(graph, path)
        if not info.get('PACKAGE'):  # unsaved: the notes tell it apart by UID only
            _fresh_uid(path)
        _note_package(path, info.get('PACKAGE'), info.get('PACKAGE_UID'))
    return 'snapshot of %s saved: %s' % (info['GRAPH'], path)


@contextlib.contextmanager
def _whole_or_none(snapshot: str) -> Iterator[None]:
    """Around writing a snapshot and its note: if any step fails (a full disk), remove what was written,
    so no snapshot is left half written or without its note, which would count for every package
    (REVIEW.md SRV-43)."""
    try:
        yield
    except BaseException:
        for leftover in (snapshot, snapshot + '.json'):
            with contextlib.suppress(OSError):
                os.remove(leftover)
        raise


# a package's own <fileUID>: a real {uuid} (each dependency's is "0"), before <dependencies>
_OWN_UID = re.compile(rb'<fileUID v="(\{[0-9a-fA-F-]{36}\})"\s*/>')


def _fresh_uid(snapshot: str) -> None:
    """Give a snapshot .sbs of an unsaved package a UID of its own (REVIEW.md SRV-42). Designer's copy
    keeps the package's (measured), and the notes tell unsaved packages apart by UID only, so such a
    snapshot opened to recover and saved anywhere looked like its unsaved original saved for the first
    time. A saved package's snapshots are told apart by file and stay exact copies. Only the UID's bytes
    change (same length; nothing else reformatted); a file without its own UID where expected is left
    alone. Designer loads it with the new UID, and a package using the original's graphs refers to it by
    file name, not UID (both measured); the note keeps the package's UID."""
    with open(snapshot, 'rb') as f:
        data = f.read()
    m = _OWN_UID.search(data)
    deps = data.find(b'<dependencies')
    if m is None or (deps != -1 and m.start() > deps):
        return
    stat = os.stat(snapshot)
    with open(snapshot, 'wb') as f:
        f.write(data[: m.start(1)] + ('{%s}' % uuid.uuid4()).encode() + data[m.end(1) :])
    # the file's date stays: re-stamping doesn't change its place among the snapshots
    os.utime(snapshot, ns=(stat.st_atime_ns, stat.st_mtime_ns))


def _note_package(snapshot: str, file_path: str | None, uid: str | None = None) -> None:
    """Next to a snapshot, the package it came from: its file (when saved) and its UID (what tells
    two unsaved packages apart). Graphs are found by identifier, and every new graph is
    "New_Graph" (REVIEW.md SRV-34)."""
    st = os.stat(snapshot)  # as written: a snapshot saved over since no longer matches (REVIEW.md SRV-47)
    with open(snapshot + '.json', 'w', encoding='utf-8') as f:
        json.dump(
            {
                'package': os.path.abspath(file_path) if file_path else '',
                'uid': uid or '',
                'size': st.st_size,
                'mtime_ns': st.st_mtime_ns,
            },
            f,
        )


def _changed_since(snapshot: str) -> bool:
    """Whether a snapshot's file changed after it was written (opened in Designer and saved in place):
    then it holds the user's edits, not the state it recorded (REVIEW.md SRV-47). A note without the size
    and time (taken before they were kept) can't tell: not changed."""
    try:
        with open(snapshot + '.json', encoding='utf-8') as f:
            note = json.load(f)
        st = os.stat(snapshot)
    except (OSError, ValueError):
        return False
    if 'size' not in note or 'mtime_ns' not in note:
        return False
    return bool(note['size'] != st.st_size or note['mtime_ns'] != st.st_mtime_ns)


def _from_package(snapshot: str, file_path: str | None, uid: str | None) -> bool:
    """Whether a snapshot came from this package, from its note (the file and UID the package had then):
    a note naming a file counts only for that file; a note without one (an unsaved package) counts for
    a package with its UID, saved since or not. A snapshot of an unsaved package opened to recover has a
    UID of its own (_fresh_uid, SRV-42), wherever it is saved later; one taken before that kept the package's, so a
    package whose file is in the snapshot folder is still excluded (SRV-38, SRV-40). The UID is the file's <fileUID>, kept by saving and shared by
    a copy of the file loaded again (measured; SRV-36). No note (taken before notes were kept): any
    package. Every case: tests/unit/test_snapshots.py, _NOTE_CASES."""
    try:
        with open(snapshot + '.json', encoding='utf-8') as f:
            note = json.load(f)
    except (OSError, ValueError):
        return True
    noted = note.get('package') or ''
    if noted:
        return bool(file_path) and noted == os.path.abspath(cast(str, file_path))
    recovered = bool(file_path) and os.path.abspath(cast(str, file_path)).startswith(
        os.path.join(os.path.abspath(SNAPSHOT_DIR), '')
    )
    return bool(uid) and note.get('uid') == uid and not recovered


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


def _others(graph_id: str, package: tuple[str | None, str | None]) -> str:
    """For a refusal: whether this graph has snapshots from other packages (another file, a Save As
    since, a copy), which diff_graph takes by path (REVIEW.md SRV-39)."""
    every = _snapshots(graph_id)
    saved_over = [p for p in every if _from_package(p, *package) and _changed_since(p)]  # its own (SRV-50)
    others = len(every) - len(_snapshots(graph_id, package)) - len(saved_over)  # not its own (SRV-41)
    parts = (['%d from other packages, e.g. before a Save As' % others] if others else []) + (
        ["%d of this package's own, saved over since taken" % len(saved_over)] if saved_over else []
    )
    return ' (%s: list_snapshots shows them; diff against one by its path)' % '; '.join(parts) if parts else ''


def _snapshots(graph_id: str, package: tuple[str | None, str | None] | None = None) -> list[str]:
    """A graph's snapshots, oldest first; with package (file path, UID), that package's only, leaving
    out one saved over since it was taken (REVIEW.md SRV-47: it is no longer a snapshot of it)."""
    folder = os.path.join(SNAPSHOT_DIR, _safe_name(graph_id))
    if not os.path.isdir(folder):
        return []
    # oldest first by when the content was written: names alone misorder two snapshots taken in
    # the same second (set_link_display's live graph and its copy2 of the older saved file)
    paths = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.sbs')]
    if package is not None:
        paths = [p for p in paths if _from_package(p, *package) and not _changed_since(p)]
    return sorted(paths, key=lambda p: (os.stat(p).st_mtime_ns, p))


@_tool()
def list_snapshots(graph: str | None = None) -> str:
    """List saved snapshots, newest last (by when their content was written; set_link_display's
    copy of the saved file counts from when that file was saved), each with the package it came
    from. A snapshot opened in Designer and saved in place since is marked as changed (one whose note records
    its size and time: taken by this version); diff_graph's
    'latest' and labels skip it (diff against it by its path). graph: graph identifier (default: all graphs)."""
    graphs = [_safe_name(graph)] if graph else (sorted(os.listdir(SNAPSHOT_DIR)) if os.path.isdir(SNAPSHOT_DIR) else [])
    lines: list[str] = []
    for gid in graphs:
        for path in _snapshots(gid):
            try:
                with open(path + '.json', encoding='utf-8') as f:
                    note = json.load(f)
                # unsaved packages told apart by their UID (REVIEW.md SRV-37)
                package = note.get('package') or '(an unsaved package, UID %s)' % (note.get('uid') or '?')
            except (OSError, ValueError):
                package = '(package not noted)'
            changed = (
                "  (changed since it was taken: opened and saved in place; not used for 'latest' or labels)"
                if _changed_since(path)
                else ''
            )
            lines.append('%s  %s  from %s%s' % (gid, path, package, changed))
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


def _function_value(function: ET.Element) -> str:
    """A function graph on a parameter, comparable: 'function (reads 'a', 'b') <digest>' of what it computes, where its
    nodes sit left out, and 'no output' in the brackets for one with no output node, which drives nothing (AGENTS.md)."""
    root = function.find('rootnode')
    parts = [root.get('v', '') if root is not None else '']
    reads: set[str] = set()
    for node in function.iter('paramNode'):
        parts.extend(ET.canonicalize(ET.tostring(c), strip_text=True) for c in node if c.tag != 'GUILayout')
        if node.find('function') is not None and _v(node, 'function').startswith('get_'):
            reads.update(c.get('v', '') for c in node.iter('constantValueString'))
    digest = hashlib.sha1('\n'.join(parts).encode('utf-8')).hexdigest()[:8]
    notes = ([] if root is not None else ['no output']) + (
        ['reads ' + ', '.join(map(repr, sorted(reads)))] if reads else []
    )
    return 'function %s%s' % ('(%s) ' % ', '.join(notes) if notes else '', digest)


# A node's parameters whose value means something else at another inheritance (REVIEW.md SRV-69)
_INHERITING_PARAMETERS = {'outputsize', 'format', 'pixelsize', 'pixelratio', 'tiling', 'randomseed'}


def _node_params(impl: ET.Element, value_of: Callable[[ET.Element], str]) -> dict[str, str]:
    """A node's parameters by a key of their own: same-named ones of a gradient's or curve's keys, or of an FX-Map's
    inner nodes, mustn't overwrite each other. A key is 'name', 'array[index] name' or 'paramset <uid> name', the uid
    being what describe_graph prints for the inner node. Arrays also give their number of cells, an FX-Map a digest of
    its wiring."""
    params: dict[str, str] = {}

    def read(element: ET.Element, prefix: str) -> None:
        for prm in element.findall('parameters/parameter'):
            value = value_of(prm)
            rel = prm.find('relativeTo')
            if _v(prm, 'name') in _INHERITING_PARAMETERS and rel is not None:
                value += ' (%s)' % _RELATIVE_TO.get(cast(str, rel.get('v')), 'relativeTo %s' % rel.get('v'))
            params[prefix + _v(prm, 'name')] = value
        for array in element.findall('paramsArrays/paramsArray'):
            name = prefix + _v(array, 'name')
            cells = array.findall('paramsArrayCells/paramsArrayCell')
            params[name + ' cells'] = str(len(cells))
            for index, cell in enumerate(cells):
                read(cell, '%s[%d] ' % (name, index))

    for implementation in impl:
        read(implementation, '')
    for graph in impl.iter('paramsGraph'):
        node_of = {_v(n, 'data'): _v(n, 'uid') for n in graph.findall('paramsGraphNodes/paramsGraphNode')}
        for data in graph.findall('paramsGraphDatas/paramsGraphData'):
            read(data, '%s %s ' % (_v(data, 'type'), node_of.get(_v(data, 'uid'), _v(data, 'uid'))))
        root = graph.find('rootnode')
        wiring = sorted(
            ET.canonicalize(ET.tostring(c), strip_text=True)
            for n in graph.findall('paramsGraphNodes/paramsGraphNode')
            for c in n
            if c.tag != 'GUILayout'
        )
        text = '\n'.join([root.get('v', '') if root is not None else '', *wiring])
        params['FX-Map wiring'] = hashlib.sha1(text.encode('utf-8')).hexdigest()[:8]
    return params


def _graph_model(sbs_path: str, graph_id: str) -> _GraphModel:
    """Parse one graph of a .sbs into comparable dicts."""
    root = ET.parse(sbs_path).getroot()
    g = _xml_graph(root, graph_id, sbs_path)

    def value_of(param: ET.Element) -> str:
        pv = param.find('paramValue')
        if pv is None or not len(pv):
            return ''
        el = pv[0]
        if el.tag == 'dynamicValue':
            return _function_value(el)
        # a resource's path names the package's own id, which differs after a reload: no change to the graph
        return re.sub(r'\?dependency=\d+$', '', el.get('v') or '')

    output_names = {_v(b, 'uid'): _v(b, 'identifier') for b in g.iter('outputBridging')}
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
        params = _node_params(impl, value_of) if impl is not None else {}
        links: set[tuple[str, str]] = set()
        display: dict[tuple[str, str], str] = {}
        conns = n.find('connections')
        for c in conns if conns is not None else []:
            out = c.find('connRefOutput')
            # which output of the source matters: bevel.height and bevel.normal are different links. By name where
            # the file has one, a library node's; an atomic node's has only its uid (REVIEW.md SRV-59)
            output = cast(str, out.get('v')) if out is not None else None
            src = _v(c, 'connRef') + ('.' + output_names.get(output, output) if output is not None else '')
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
    'latest' (this package's newest snapshot), a snapshot label (this package's), or a .sbs path (any
    snapshot: after a Save As, the earlier file's snapshots count as another package's). The live graph is read
    without modifying it, so a package using a graph of a never-saved package is refused, as in save_package.
    Positions are only counted unless show_positions=True."""
    tmp_dir = tempfile.mkdtemp(prefix='sd_diff_')
    try:
        info = _copy_package(graph, os.path.join(tmp_dir, 'live.sbs'))
        gid = info['GRAPH']
        package = (info.get('PACKAGE'), info.get('PACKAGE_UID'))  # this package's snapshots only
        if against == 'saved':
            ref = info.get('PACKAGE')
            if not ref or not os.path.exists(ref):
                raise ToolError('the package has never been saved; diff against a snapshot instead')
        elif against == 'latest':
            snaps = _snapshots(gid, package)
            if not snaps:
                raise ToolError(
                    'no snapshots of %s for this package; take one with snapshot_graph%s' % (gid, _others(gid, package))
                )
            ref = snaps[-1]
        elif against.endswith('.sbs'):
            ref = os.path.abspath(os.path.expanduser(against))
        else:
            matches = [
                p
                for p in _snapshots(gid, package)
                if (_SNAPSHOT_NAME.match(os.path.basename(p)) or [None, None])[1] == _safe_name(against)
            ]
            if not matches:
                raise ToolError(
                    'no snapshot matching %r for this package; see list_snapshots%s' % (against, _others(gid, package))
                )
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
