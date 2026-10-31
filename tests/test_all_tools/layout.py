"""Snapshots, diffs and readable graphs: snapshot_graph, list_snapshots, diff_graph, arrange_graph,
add_frame, add_comment."""

import os
import re

from .common import TEST_GRAPH, Ctx, added_id, check, positions, text


async def run(ctx: Ctx) -> None:
    c, G, clouds, slope, lv, out = ctx.c, ctx.G, ctx.clouds, ctx.slope, ctx.lv, ctx.out
    # --- snapshots, diff, layout, frames
    t = text(await c('snapshot_graph', {'label': 'before tweak', **G}))
    check('snapshot_graph', 'saved', 'snapshot of %s saved' % TEST_GRAPH in t, t)
    snap_path = t.split('saved: ', 1)[1].strip()
    t = text(await c('list_snapshots', G))
    check('list_snapshots', 'lists it', snap_path in t, '')
    t = text(await c('list_snapshots'))
    check('list_snapshots', 'all graphs', snap_path in t, t[:200])
    r_ = await c('diff_graph', {'against': 'no such label', **G})
    check('diff_graph', 'error: unknown snapshot label', r_.is_error and 'no snapshot matching' in text(r_), text(r_))
    await c('set_params', {'node_id': lv, 'params': {'levelinhigh': [0.8] * 4}, **G})
    tmp_node = added_id(text(await c('add_node', {'definition': 'blur', **G})))
    t = text(await c('diff_graph', {'against': 'latest', **G}))
    check(
        'diff_graph',
        'sees param change + new node',
        'levelinhigh' in t and '+ node %s blur' % tmp_node in t,
        t.splitlines()[0],
    )
    t = text(await c('diff_graph', {'against': 'before tweak', **G}))
    check('diff_graph', 'by label', 'levelinhigh' in t, '')
    await c('delete_nodes', {'node_ids': [tmp_node], **G})
    await c('set_params', {'node_id': lv, 'params': {'levelinhigh': [1.0] * 4}, **G})  # undo the tweak
    t = text(await c('diff_graph', {'against': 'latest', **G}))
    check(
        'diff_graph',
        'no differences after reverting',
        'No differences' in t or 'Only node positions' in t,
        t.splitlines()[-1],
    )
    os.remove(snap_path)
    if not os.listdir(os.path.dirname(snap_path)):
        os.rmdir(os.path.dirname(snap_path))
    t = text(await c('arrange_graph', G))
    check('arrange_graph', 'columns by data flow', 'arranged' in t and 'column' in t, t)
    t = text(await c('describe_graph', G))
    x_of = {
        l.split()[0]: int(re.search(r'@\((-?\d+),', l).group(1))  # type: ignore[union-attr]  # '@(' lines match
        for l in t.splitlines()
        if '@(' in l
    }
    check('arrange_graph', 'upstream left of downstream', x_of[clouds] < x_of[slope] < x_of[lv] < x_of[out], str(x_of))
    t = text(await c('add_frame', {'node_ids': [clouds, slope], 'title': 'Shape', 'color': [0.2, 0.4, 0.8], **G}))
    check('add_frame', 'frame drawn', "frame 'Shape' around 2 node(s)" in t, t)
    t = text(await c('add_comment', {'text': 'self-test note', 'node_id': lv, **G}))
    check('add_comment', 'attached comment', 'comment added on node' in t, t)
    t = text(await c('add_comment', {'text': 'free note', 'position': [0, -300], **G}))
    check('add_comment', 'free-standing at a position', t.strip() == 'comment added', t)
    await c('add_frame', {'node_ids': [lv], 'title': 'Described', 'description': 'why this frame', **G})
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': (
                    'import sd\nfrom sd.api.sdgraphobjectframe import SDGraphObjectFrame\n'
                    'g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() '
                    "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
                    'print([o.getDescription() for o in g.getGraphObjects() if isinstance(o, SDGraphObjectFrame) '
                    "and o.getTitle()=='Described'])"
                )
                % TEST_GRAPH
            },
        )
    )
    check('add_frame', 'description stored', "['why this frame']" in t, t)
    await c('arrange_graph', {'node_ids': [clouds, slope], 'spacing': [300, 150], **G})
    xs = positions(text(await c('describe_graph', G)))
    check('arrange_graph', 'node_ids + spacing', abs(xs[slope][0] - xs[clouds][0] - 300) < 1, str(xs))
    await c('arrange_graph', G)
    t = text(await c('describe_graph', {'limit': 2, **G}))
    check('describe_graph', 'limit', re.search(r'\.\.\. \d+ more nodes', t) is not None, t.splitlines()[-1])
    t = text(await c('describe_graph', G))
    check(
        'describe_graph',
        'lists frames + comments',
        "frames: 'Shape', 'Described'" in t and 'comments: 2' in t,
        next((l for l in t.splitlines() if 'frames' in l), t.splitlines()[1]),
    )
    t = text(await c('describe_node', {'definition': 'bevel'}))
    check('describe_node', 'library slider range', 'range -1.0..1.0' in t, '')
