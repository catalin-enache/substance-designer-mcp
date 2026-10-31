"""apply_edits: several edits in one call."""

from .core import Any, APIException, SDSBSCompGraph, find_graph
from .editor import move_nodes
from .edits import add_node, connect, delete_nodes, disconnect, import_bitmap, set_params
from .graph_inputs import expose_param

# the fields of each op kind that name a node: a ref, a node id, or 'graph' where listed in _GRAPH_OK
_NODE_FIELDS: dict[str, tuple[str, ...]] = {
    'add': (),
    'bitmap': (),
    'set': ('node',),
    'connect': ('from', 'to'),
    'disconnect': ('node',),
    'move': ('node',),
    'delete': ('node',),
    'expose': ('node',),
}
_GRAPH_OK = {'set'}  # the graph's own parameters, as _target allows


def _check_batch(g: SDSBSCompGraph, ops: list[dict[str, Any]]) -> None:
    """Refuse the batch before any op runs when an op's kind is unknown, a ref isn't text, or a node
    it names is neither a ref defined by an earlier add/bitmap op, 'graph' (set only), nor a node of
    g; a node an earlier delete op removes counts as gone."""
    refs: dict[str, str] = {}  # ref -> what it stands for while checking ('ref:<name>', unique)
    deleted: dict[str, int] = {}  # node id or 'ref:<name>' -> the op that deletes it
    for i, op in enumerate(ops):
        kind = op.get('op') if isinstance(op, dict) else None
        if not isinstance(kind, str) or kind not in _NODE_FIELDS:
            raise RuntimeError('op %d: unknown op %r (%s); nothing was applied' % (i, kind, ', '.join(_NODE_FIELDS)))
        for field in _NODE_FIELDS[kind]:
            value = op.get(field)
            if kind in _GRAPH_OK and value == 'graph':
                continue
            if isinstance(value, str) and value in refs:
                key = refs[value]
            elif value not in (None, '') and g.getNodeFromId(str(value)) is not None:
                key = str(value)
            else:
                raise RuntimeError(
                    'op %d (%s): node %r not found in graph %s; nothing was applied'
                    % (i, kind, value, g.getIdentifier())
                )
            if key in deleted:
                raise RuntimeError(
                    'op %d (%s): node %r was deleted by op %d; nothing was applied' % (i, kind, value, deleted[key])
                )
            if kind == 'delete':
                deleted[key] = i
        ref = op.get('ref')
        if kind in ('add', 'bitmap') and ref not in (None, ''):
            if not isinstance(ref, str):
                raise RuntimeError('op %d (%s): ref must be a string, not %r; nothing was applied' % (i, kind, ref))
            if ref == 'graph':  # it names the graph in a set op; the run would read it as the node
                raise RuntimeError("op %d (%s): ref 'graph' is reserved; nothing was applied" % (i, kind))
            refs[ref] = 'ref:%s:%d' % (ref, i)  # a ref reused later names the newer node


def apply_edits(identifier: str | SDSBSCompGraph | None, ops: list[dict[str, Any]]) -> None:
    """Run a list of edit operations in order. 'ref' names a node added earlier in the batch;
    node fields accept a ref, a node id, or 'graph' (set only). Every node the batch names is
    checked before any op runs (_check_batch); after that, stops at the first failing op."""
    g = find_graph(identifier)
    _check_batch(g, ops)
    gid = g  # the object, so every op edits this graph even if another has the same name
    refs: dict[str, str] = {}

    def node(value: Any) -> Any:
        return refs.get(value, value)

    for i, op in enumerate(ops):
        kind = op.get('op')
        nodes_before = g.getNodes().getSize()
        try:
            if kind == 'add':
                new_id = add_node(gid, op['definition'], op.get('position'), op.get('params'))
                if op.get('ref'):
                    refs[op['ref']] = new_id
                    print('  ref %r = %s' % (op['ref'], new_id))
            elif kind == 'bitmap':
                new_id = import_bitmap(gid, op['path'], op.get('embed', 'link'), op.get('position'), op.get('name'))
                if op.get('ref'):
                    refs[op['ref']] = new_id
                    print('  ref %r = %s' % (op['ref'], new_id))
            elif kind == 'set':
                set_params(gid, node(op['node']), op['params'])
            elif kind == 'connect':
                connect(gid, node(op['from']), node(op['to']), op['input'], op.get('output'))
            elif kind == 'disconnect':
                disconnect(gid, node(op['node']), op['input'])
            elif kind == 'move':
                move_nodes(gid, {node(op['node']): op['position']})
            elif kind == 'delete':
                delete_nodes(gid, [node(op['node'])])
            elif kind == 'expose':
                expose_param(
                    gid,
                    node(op['node']),
                    op['param'],
                    op.get('input_id'),
                    op.get('label'),
                    op.get('default'),
                    op.get('min'),
                    op.get('max'),
                    op.get('step'),
                    op.get('group'),
                )
            else:  # _check_batch refused it already; kept so every path through the loop is defined
                raise RuntimeError('unknown op %r (add, bitmap, set, connect, disconnect, move, delete, expose)' % kind)
        except (Exception, APIException) as e:
            done = 'ops 0-%d were applied' % (i - 1) if i else 'no earlier op was applied'
            # an add can fail after creating its node (in setting its params): say so only then
            added = kind in ('add', 'bitmap') and g.getNodes().getSize() > nodes_before
            raise RuntimeError(
                'op %d (%s) failed: %s. %s%s; Ctrl+Z on this graph reverts the whole '
                'batch.' % (i, kind, e, done, ' (its node was added before the failure)' if added else '')
            ) from e
    print('applied %d op(s); refs: %s' % (len(ops), refs))
