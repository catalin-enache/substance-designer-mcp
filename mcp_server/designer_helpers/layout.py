"""Readable graphs: arrange_graph, add_frame, add_comment."""

from .core import SDDefinition, SDNode, SDPropertyCategory, SDSBSCompGraph, Sequence, _other_end, cast, find_graph
from .edits import _node

_NODE_SIZE = 96.0  # graph-view size of a node; positions are node centres


def _nodes_bbox(g: SDSBSCompGraph, node_ids: Sequence[str]) -> tuple[list[SDNode], tuple[float, float, float, float]]:
    """The nodes (never the graph itself, which _target allows for parameters) and their
    bounding box (left, top, right, bottom) in graph units."""
    nodes = []
    for i in node_ids:
        node = g.getNodeFromId(str(i)) if i not in (None, '') else None
        if node is None:
            raise RuntimeError('node %r not found in graph %s' % (i, g.getIdentifier()))
        nodes.append(node)
    if not nodes:
        raise RuntimeError('no node ids given')
    half = _NODE_SIZE / 2.0
    xs = [n.getPosition().x for n in nodes]
    ys = [n.getPosition().y for n in nodes]
    return nodes, (min(xs) - half, min(ys) - half, max(xs) + half, max(ys) + half)


def _links(g: SDSBSCompGraph, nodes: list[SDNode]) -> set[tuple[str, str]]:
    """(upstream_id, downstream_id) pairs between the given nodes."""
    ids = {n.getIdentifier() for n in nodes}
    pairs = set()
    for n in nodes:
        for prop in n.getProperties(SDPropertyCategory.Input):
            if not prop.isConnectable():
                continue
            for c in n.getPropertyConnections(prop):
                other, _ = _other_end(c)
                if other.getIdentifier() in ids:
                    pairs.add((other.getIdentifier(), n.getIdentifier()))
    return pairs


def arrange_graph(
    identifier: str | SDSBSCompGraph | None,
    node_ids: list[str] | None = None,
    spacing: Sequence[float] = (200.0, 150.0),
) -> None:
    """Layered left-to-right layout by data flow. Only positions change, never connections.
    With node_ids, only those nodes are arranged, starting at their current top-left corner."""
    from sd.api.sdbasetypes import float2

    g = find_graph(identifier)
    nodes = list(g.getNodes())
    if node_ids:
        wanted = {str(i) for i in node_ids}
        nodes = [n for n in nodes if n.getIdentifier() in wanted]
    if not nodes:
        raise RuntimeError('no nodes to arrange')
    by_id = {n.getIdentifier(): n for n in nodes}
    pairs = _links(g, nodes)
    preds = {i: [a for a, b in pairs if b == i] for i in by_id}
    succs = {i: [b for a, b in pairs if a == i] for i in by_id}
    # layer = longest path from a source (iterative, cycle-safe)
    layer = dict.fromkeys(by_id, 0)
    for _ in range(len(by_id)):
        changed = False
        for a, b in pairs:
            if layer[b] < layer[a] + 1:
                layer[b] = layer[a] + 1
                changed = True
        if not changed:
            break
    # outputs go to the last column
    last = max(layer.values())
    for i, n in by_id.items():
        if cast(SDDefinition, n.getDefinition()).getId() == 'sbs::compositing::output':
            layer[i] = last
    columns: dict[int, list[str]] = {}
    for i in sorted(by_id, key=lambda i: (by_id[i].getPosition().y, by_id[i].getPosition().x)):
        columns.setdefault(layer[i], []).append(i)
    # barycentre ordering to reduce crossings: a few sweeps in both directions
    order = {i: k for col in columns.values() for k, i in enumerate(col)}
    for sweep in range(4):
        keys = sorted(columns) if sweep % 2 == 0 else sorted(columns, reverse=True)
        for L in keys:
            neigh = preds if sweep % 2 == 0 else succs

            def bary(i: str) -> float:
                ns = neigh[i]  # noqa: B023 (bary is used by this iteration's sort only)
                return sum(order[j] for j in ns) / len(ns) if ns else order[i]

            columns[L].sort(key=bary)
            for k, i in enumerate(columns[L]):
                order[i] = k
    xs = [n.getPosition().x for n in nodes]
    ys = [n.getPosition().y for n in nodes]
    x0, y0 = min(xs), min(ys)
    dx, dy = spacing
    tallest = max(len(c) for c in columns.values())
    for L, col in columns.items():
        top = y0 + (tallest - len(col)) * dy / 2.0  # centre each column vertically
        for k, i in enumerate(col):
            by_id[i].setPosition(float2(x0 + L * dx, top + k * dy))
    print(
        'arranged %d node(s) into %d column(s), %d link(s); spacing %dx%d'
        % (len(nodes), len(columns), len(pairs), dx, dy)
    )


def add_frame(
    identifier: str | SDSBSCompGraph | None,
    node_ids: list[str],
    title: str,
    color: Sequence[float] | None = None,
    description: str | None = None,
    margin: float = 40.0,
) -> None:
    from sd.api.sdbasetypes import ColorRGBA, float2
    from sd.api.sdgraphobjectframe import SDGraphObjectFrame

    g = find_graph(identifier)
    nodes, (left, top, right, bottom) = _nodes_bbox(g, node_ids)
    left, right = left - margin, right + margin
    top, bottom = top - margin - 30.0, bottom + margin  # room for the title bar
    frame = SDGraphObjectFrame.sNew(g)
    frame.setTitle(title)
    frame.setPosition(float2(left, top))
    frame.setSize(float2(right - left, bottom - top))
    if color:
        c = list(color) + [1.0] * (4 - len(color))
        frame.setColor(ColorRGBA(*map(float, c[:4])))
    if description:
        frame.setDescription(description)
    print(
        'frame %r around %d node(s) at (%d, %d) size %dx%d' % (title, len(nodes), left, top, right - left, bottom - top)
    )


def add_comment(
    identifier: str | SDSBSCompGraph | None,
    text: str,
    node_id: str | None = None,
    position: Sequence[float] | None = None,
) -> None:
    from sd.api.sdbasetypes import float2
    from sd.api.sdgraphobjectcomment import SDGraphObjectComment

    g = find_graph(identifier)
    if node_id:
        comment = SDGraphObjectComment.sNewAsChild(_node(g, node_id))
    else:
        comment = SDGraphObjectComment.sNew(g)
        if position:
            comment.setPosition(float2(float(position[0]), float(position[1])))
    comment.setDescription(text)
    print('comment added' + (' on node %s' % node_id if node_id else ''))


def graph_objects_summary(g: SDSBSCompGraph) -> tuple[list[str], int]:
    from sd.api.sdgraphobjectcomment import SDGraphObjectComment
    from sd.api.sdgraphobjectframe import SDGraphObjectFrame

    frames: list[str] = []
    comments = 0
    for obj in g.getGraphObjects():
        if isinstance(obj, SDGraphObjectFrame):
            frames.append(obj.getTitle())
        elif isinstance(obj, SDGraphObjectComment):
            comments += 1
    return frames, comments
