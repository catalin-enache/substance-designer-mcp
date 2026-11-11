"""Readable graphs: arrange_graph, add_frame, add_comment, set_link_display (a file-level edit:
snapshot, save, edit the .sbs, reload).

Designer's own UI portals are Dot nodes (`passthrough`): a transmitter given an ID (`<userId v="p1"/>` on its
`compNode`) and a receiver that picks it in its Input Portal field, stored as an ordinary connection from the
transmitter with the display flag (seen once by hand, Designer 16.0.7; to the API a plain connection). A Dot node has no
ID property ("designer facts"); set_link_display sets the flag on any connection, without Dots.

The reload is three separate bridge calls because, back to back, Designer once crashed (a null call in PySide from its
own `node_align_tools` plugin, which adds a toolbar to each new graph view, while the old views were being torn down);
returning to Designer's event loop between the steps lets the teardown finish.
"""

import contextlib
import os
import re
import shutil
import tempfile
import time
import xml.etree.ElementTree as ET
from typing import cast

from mcp.server.mcpserver.exceptions import ToolError

from .core import _bridge, _checked, _edit, _helpers_call, _tool
from .snapshots import _new_snapshot_path, _note_package, _v, _whole_or_none, _xml_graph, snapshot_graph


@_tool()
def arrange_graph(
    graph: str | None = None, node_ids: list[str] | None = None, spacing: list[float] | None = None
) -> str:
    """Tidy a graph: left-to-right columns by data flow, ordered to reduce crossing links,
    outputs in the last column. Only positions change (connections are never touched).
    node_ids: arrange just these nodes, from their current top-left (an id that names no node is
    refused, nothing moved). spacing: [dx, dy]
    (default [200, 150]). One undo step."""
    return _edit(
        'arrange_graph(%r, %r, %r)' % (graph, node_ids, tuple(spacing or (200.0, 150.0))), 'Claude: arrange graph'
    )


@_tool()
def add_frame(
    node_ids: list[str],
    title: str,
    graph: str | None = None,
    color: list[float] | None = None,
    description: str | None = None,
) -> str:
    """Draw a titled frame around nodes (e.g. one per section of a material). color: [r, g, b(, a)]
    0..1. description: text shown in the frame. One undo step."""
    return _edit(
        'add_frame(%r, %r, %r, %r, %r)' % (graph, node_ids, title, color, description), 'Claude: add frame ' + title
    )


@_tool()
def add_comment(
    text: str, graph: str | None = None, node_id: str | None = None, position: list[float] | None = None
) -> str:
    """Add a comment to a graph: attached to node_id, or free-standing at position [x, y].
    One undo step."""
    return _edit('add_comment(%r, %r, %r, %r)' % (graph, text, node_id, position), 'Claude: add comment')


_DISPLAY: dict[str, str | None] = {'portal': '1', 'wire': None}


@_tool()
def set_link_display(
    graph: str | None = None,
    mode: str = 'portal',
    from_nodes: list[str] | None = None,
    fanout_at_least: int | None = None,
    longer_than: float | None = None,
    links: list[list[str]] | None = None,
) -> str:
    """Show connections as portals (hidden wires with a symbol at each end) or as normal wires, to
    reduce wire clutter. Pick links by any of: from_nodes (all outgoing links of these nodes),
    fanout_at_least (all links from outputs that feed at least N inputs), longer_than (links
    longer than this distance in graph units; nodes are ~96 wide), links ([[to_node, input], ...]).
    mode: 'portal' or 'wire'. Designer's API can't do this, so the tool first takes a snapshot of
    the graph and copies the package's saved file (both in the snapshot folder), then saves the
    package, edits the .sbs and reloads it (the package's undo history is reset; the graph is
    reopened). If no selected link would change, nothing is saved or reloaded. If the package is
    edited again before the reload, the reload is refused and those edits are kept. The package
    must have been saved to a file once, and is refused while it uses a graph of a never-saved package,
    as in save_package."""
    if mode not in _DISPLAY:
        raise ToolError("mode must be 'portal' or 'wire'")
    if not (from_nodes or fanout_at_least or longer_than or links):
        raise ToolError('choose links with from_nodes, fanout_at_least, longer_than or links')
    text = _bridge(_helpers_call('package_file_of(%r)' % graph), timeout=120)
    info = dict(re.findall(r'^(FILE|GRAPH|OPEN)=(.*)$', text, re.M))
    if 'FILE' not in info:
        raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'could not find the package file')
    path, gid = info['FILE'], info['GRAPH']
    # Before anything is written: a snapshot of the live graph, and a copy of the file on disk,
    # which saving below replaces
    snap = snapshot_graph(gid, 'before ' + mode + 's')
    live = snap.split('saved: ', 1)[1].strip()
    if os.path.exists(path):
        on_disk = _new_snapshot_path(gid, 'before %ss (file on disk)' % mode)
        with _whole_or_none(on_disk):  # nothing half written or without its note (SRV-43)
            _copy_sbs(path, on_disk)  # a saved file: keeps its UID, the notes tell it apart by file (SRV-42)
            _note_package(on_disk, path)
    chosen, selected, total = _select_links(
        _xml_graph(ET.parse(live).getroot(), gid, live), mode, from_nodes, fanout_at_least, longer_than, links
    )
    if not chosen:
        return (
            '0 of %d selected link(s) changed to %s in %s (of %d links in the graph); nothing to do, '
            'package not saved or reloaded.' % (selected, mode, gid, total)
        )
    _checked(_bridge(_helpers_call('package_file_of(%r, save=True)' % gid), timeout=120))
    tree = ET.parse(path)
    picked, selected, total = _select_links(
        _xml_graph(tree.getroot(), gid, path), mode, from_nodes, fanout_at_least, longer_than, links
    )
    for c in picked:
        dt = c.find('displayType')
        value = _DISPLAY[mode]
        if value is None:
            c.remove(cast(ET.Element, dt))  # picked for 'wire' only when it has one (_select_links)
        else:
            if dt is None:
                dt = ET.SubElement(c, 'displayType')
            dt.set('v', value)
    _replace_file(tree, path, live)
    _reload_package_file(path, live)
    reopen = ''
    if info.get('OPEN') == '1':
        try:
            # through the file: by name alone another package's tab of this name could open (SRV-34)
            _checked(_bridge(_helpers_call('open_graph(graph_in_file(%r, %r))' % (path, gid)), timeout=60))
        except ToolError as e:
            reopen = ' WARNING: could not reopen %s: %s.' % (gid, e)

    return (
        '%d of %d selected link(s) changed to %s in %s (of %d links in the graph); package saved and '
        'reloaded.%s %s' % (len(picked), selected, mode, gid, total, reopen, snap)
    )


def _copy_sbs(src: str, dst: str) -> None:
    """Copy a saved .sbs to another folder so it still opens with its bitmaps and dependencies:
    Designer writes their paths relative to the .sbs, so those are rewritten for the new folder
    (library references such as sbs://... and the ?himself marker are left alone). Keeps the original's timestamps, as
    shutil.copy2 does, so this copy never sorts as the latest snapshot (REVIEW.md SRV-1, SRV-14)."""
    tree = ET.parse(src)
    changed = False
    for element in list(tree.getroot().iter('filepath')) + list(tree.getroot().iter('filename')):
        value = element.get('v') or ''
        if not value or '://' in value or value.startswith('?') or os.path.isabs(value):
            continue  # ?himself: the package's own graphs (REVIEW.md SRV-17)
        target = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(src)), value))
        try:
            new = os.path.relpath(target, os.path.dirname(os.path.abspath(dst)))
        except ValueError:  # another drive on Windows
            new = target
        element.set('v', new.replace(os.sep, '/'))
        changed = True
    if changed:
        tree.write(dst, encoding='UTF-8', xml_declaration=True)
        shutil.copystat(src, dst)
    else:
        shutil.copy2(src, dst)


RELOAD_SETTLE_S = 0.5


def _replace_file(tree: 'ET.ElementTree[ET.Element]', path: str, snapshot: str) -> None:
    """Write the edited .sbs next to the user's file, then put it in place. A symlinked file is resolved
    first, so the file it points to is the one replaced and the link stays (REVIEW.md SRV-48). A file with one
    name is replaced by a rename, in one step, so it is either the one just saved or the edited one, never half
    written (a full disk; SRV-46); its permission bits are kept, not its owner, ACLs or Finder tags. A file that
    still has other hard-linked names after Designer's save is written into in place instead, from the complete
    temporary file, so those names get the edit too and it stays the same file (SRV-51); if that write fails it
    may be left half written, the temporary file is kept and the error names it. Once that write is done, a
    temporary file that can't be removed just stays (SRV-52). On any other file error, creating the temporary
    file included (SRV-49), the file isn't changed and the error says so, with the snapshot taken before."""
    real = os.path.realpath(path)
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix='.' + os.path.basename(real) + '.', suffix='.tmp', dir=os.path.dirname(real))
        os.close(fd)
        tree.write(tmp, encoding='UTF-8', xml_declaration=True)
        if os.stat(real).st_nlink > 1:
            edited, tmp = tmp, None  # from here on a failure keeps it: the file may be half written
            try:
                shutil.copyfile(edited, real)
            except OSError as e:
                raise ToolError(
                    'could not write the edited package into %s (%s): it has other hard-linked names, so it is '
                    'written in place and may be incomplete now. The edited package is %s (copy it over %s), and '
                    'the snapshot taken before is %s' % (path, e, edited, path, snapshot)
                ) from e
            with contextlib.suppress(OSError):  # the edit is in: the reload must still run (SRV-52)
                os.remove(edited)
            return
        shutil.copymode(real, tmp)
        os.replace(tmp, real)
    except BaseException as e:
        if tmp is not None:
            with contextlib.suppress(OSError):
                os.remove(tmp)
        if not isinstance(e, OSError):
            raise
        raise ToolError(
            'could not write the edited package (%s); %s is unchanged, as saved just before, and the '
            'snapshot taken before is %s' % (e, path, snapshot)
        ) from e


def _reload_package_file(path: str, snapshot: str | None = None) -> None:
    """Unload, load, and (by the caller) reopen as separate bridge calls with pauses between,
    so Designer's event loop finishes tearing down the old graph views before new ones are made.
    Done back to back, Designer once crashed: its own node_align_tools plugin (Python, PySide)
    was called for a destroyed view while the reopened graph's view was being created."""
    _checked(_bridge(_helpers_call('unload_package_file(%r)' % path), timeout=180))
    time.sleep(RELOAD_SETTLE_S)
    try:
        _checked(_bridge(_helpers_call('load_package_file(%r)' % path), timeout=180))
    except ToolError as e:
        # the package is closed by now: say so, and where its files are (REVIEW.md SRV-29)
        raise ToolError(
            '%s. The package was closed in Designer and could not be opened again: the edited file '
            'is %s%s; open it by hand (File > Open).'
            % (e, path, ', the snapshot taken before is %s' % snapshot if snapshot else '')
        ) from e
    time.sleep(RELOAD_SETTLE_S)


def _select_links(
    g: ET.Element,
    mode: str,
    from_nodes: list[str] | None = None,
    fanout_at_least: int | None = None,
    longer_than: float | None = None,
    links: list[list[str]] | None = None,
) -> tuple[list[ET.Element], int, int]:
    """(the <connection> elements of a <graph> that the selection picks and that would change
    display mode, how many it picks in all, the total number of links). Only the graph's own
    links count (a node's <connections>), not those inside function graphs on its parameters."""
    nodes = {_v(n, 'uid'): n for n in g.findall('compNodes/compNode')}

    def pos(uid: str) -> list[float] | None:
        """A node's position; None for a node not in this graph. Designer writes no <gpos> for a node at (0, 0)."""
        if uid not in nodes:
            return None
        gp = nodes[uid].find('GUILayout/gpos')
        return [float(v) for v in cast(str, gp.get('v')).split()[:2]] if gp is not None else [0.0, 0.0]

    # (downstream uid, connection element, source uid, source output)
    conns: list[tuple[str, ET.Element, str, str | None]] = []
    for uid, n in nodes.items():
        for c in n.findall('connections/connection'):
            out = c.find('connRefOutput')
            conns.append((uid, c, _v(c, 'connRef'), out.get('v') if out is not None else ''))
    fanout: dict[tuple[str, str | None], int] = {}
    for _, _, src, output in conns:
        fanout[(src, output)] = fanout.get((src, output), 0) + 1
    wanted_links = {(str(a), str(b)) for a, b in (links or [])}
    chosen: list[ET.Element] = []
    selected = 0
    for down, c, src, output in conns:
        port = _v(c, 'identifier')
        pick = (
            (from_nodes and src in {str(x) for x in from_nodes})
            or (fanout_at_least and fanout[(src, output)] >= fanout_at_least)
            or ((down, port) in wanted_links)
        )
        if not pick and longer_than:
            a, b = pos(src), pos(down)
            pick = a is not None and b is not None and ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 > longer_than
        dt = c.find('displayType')
        current = dt.get('v') if dt is not None else None
        if pick:
            selected += 1
            if current != _DISPLAY[mode]:
                chosen.append(c)
    return chosen, selected, len(conns)
