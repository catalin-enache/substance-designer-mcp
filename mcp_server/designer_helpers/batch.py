"""apply_edits: several edits in one call."""

from .core import Any, APIException, SDSBSCompGraph, find_graph
from .editor import move_nodes
from .edits import add_node, connect, delete_nodes, disconnect, import_bitmap, set_params
from .graph_inputs import expose_param


def apply_edits(identifier: str | SDSBSCompGraph | None, ops: list[dict[str, Any]]) -> None:
    """Run a list of edit operations in order. 'ref' names a node added earlier in the batch;
    node fields accept a ref, a node id, or 'graph'. Stops at the first failing op."""
    g = find_graph(identifier)
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
            else:
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
