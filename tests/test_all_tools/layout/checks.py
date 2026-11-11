"""Snapshots, diffs and readable graphs: snapshot_graph, list_snapshots, diff_graph, arrange_graph,
add_frame, add_comment."""

import os
import re
from textwrap import dedent

from test_all_tools.common import GRAPH_OF, TEST_GRAPH, Ctx, added_id, check, positions, text


async def run(ctx: Ctx) -> None:
    c, G, clouds, slope, lv, out = ctx.c, ctx.G, ctx.clouds, ctx.slope, ctx.lv, ctx.out
    # --- snapshots, diff, layout, frames
    t = text(await c('snapshot_graph', {'label': 'before tweak', **G}))
    check('snapshot_graph', 'saved', 'snapshot of %s saved' % TEST_GRAPH in t, t)
    snap_path = t.split('saved: ', 1)[1].strip()
    # the package is still unsaved here, so its snapshot has a UID of its own: opened in Designer, it isn't
    # its package (REVIEW.md SRV-42; a saved package's keeps the UID: save/checks.py). Loaded and unloaded in
    # one call, so no second graph of this name is ever open between calls
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + dedent("""\
                    pm = sd.getContext().getSDApplication().getPackageMgr()
                    snap = pm.loadUserPackage(%r)
                    try:
                        print('SNAPSHOT_UID_DIFFERS=%%s' %% (snap.getUID() != g.getPackage().getUID()))
                    finally:
                        pm.unloadUserPackage(snap)""")
                % snap_path
            },
        )
    )
    check(
        'snapshot_graph', 'a snapshot loads with a UID of its own', 'SNAPSHOT_UID_DIFFERS=True' in t, t.strip()[-150:]
    )
    t = text(await c('list_snapshots', G))
    check('list_snapshots', 'lists it', snap_path in t, '')
    t = text(await c('list_snapshots'))
    check('list_snapshots', 'all graphs', snap_path in t, t[:200])
    r_ = await c('diff_graph', {'against': 'no such label', **G})
    check('diff_graph', 'error: unknown snapshot label', r_.is_error and 'no snapshot matching' in text(r_), text(r_))
    await c('apply_edits', {'ops': [{'op': 'set', 'node': lv, 'params': {'levelinhigh': [0.8] * 4}}], **G})
    tmp_node = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur'}], **G})))
    t = text(await c('diff_graph', {'against': 'latest', **G}))
    check(
        'diff_graph',
        'sees param change + new node',
        'levelinhigh' in t and '+ node %s blur' % tmp_node in t,
        t.splitlines()[0],
    )
    t = text(await c('diff_graph', {'against': 'before tweak', **G}))
    check('diff_graph', 'by label', 'levelinhigh' in t, '')
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': tmp_node}], **G})
    # undo the tweak
    await c('apply_edits', {'ops': [{'op': 'set', 'node': lv, 'params': {'levelinhigh': [1.0] * 4}}], **G})
    t = text(await c('diff_graph', {'against': 'latest', **G}))
    check(
        'diff_graph',
        'no differences after reverting',
        'No differences' in t or 'Only node positions' in t,
        t.splitlines()[-1],
    )
    os.remove(snap_path)
    # a change inside a function shows, the loss of its output node by name (REVIEW.md SRV-63)
    fn_node = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels'}], **G})))
    try:
        await c(
            'apply_edits',
            {'ops': [{'op': 'expose', 'node': fn_node, 'param': 'levelinlow', 'input_id': 'diff_in'}], **G},
        )
        await c('snapshot_graph', {'label': 'function kept', **G})
        same = text(await c('diff_graph', {'against': 'function kept', **G}))
        check('diff_graph', 'a function nothing changed compares equal', 'levelinlow' not in same, same)
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + dedent("""\
                    from sd.api.sdproperty import SDPropertyCategory
                    fg = g.getNodeFromId(%r).getPropertyGraph(g.getNodeFromId(%r).getPropertyFromId('levelinlow', SDPropertyCategory.Input))
                    fg.setOutputNode(fg.getNodes()[0], False)""")
                % (fn_node, fn_node)
            },
        )
        t = text(await c('diff_graph', {'against': 'function kept', **G}))
        check('diff_graph', 'a function losing its output node shows', 'levelinlow' in t and 'no output' in t, t)
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': fn_node}], **G})
        await c('remove_graph_input', {'input_id': 'diff_in', **G})
    if os.path.isfile(snap_path + '.json'):  # its note of the package (REVIEW.md SRV-34)
        os.remove(snap_path + '.json')
    if not os.listdir(os.path.dirname(snap_path)):
        os.rmdir(os.path.dirname(snap_path))
    # an id that names no node is refused, nothing moved (REVIEW.md HLP-47)
    before = text(await c('describe_graph', G))
    r_ = await c('arrange_graph', {'node_ids': [clouds, slope, 'no_such_node'], **G})
    after = text(await c('describe_graph', G))
    check(
        'arrange_graph',
        'an unknown id is refused, nothing moved',
        r_.is_error and "node 'no_such_node' not found" in text(r_) and before == after,
        text(r_).strip()[-120:],
    )
    # describe_graph says which ids it didn't find, instead of dropping them (REVIEW.md HLP-47)
    t = text(await c('describe_graph', {'node_ids': [clouds, 'no_such_node'], **G}))
    check(
        'describe_graph',
        'an unknown id in node_ids is named',
        'not found: no_such_node' in t and '%s instance:' % clouds in t,
        t.strip()[-150:],
    )
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
                'code': GRAPH_OF % TEST_GRAPH
                + dedent("""\
                    from sd.api.sdgraphobjectframe import SDGraphObjectFrame
                    print([o.getDescription() for o in g.getGraphObjects() if isinstance(o, SDGraphObjectFrame) and o.getTitle() == 'Described'])""")
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
    await check_a_move_from_the_origin_shows_both_positions(ctx)


async def check_a_move_from_the_origin_shows_both_positions(ctx: Ctx) -> None:
    """Designer writes no position for a node at (0, 0): diff_graph read none there, and a move from it showed as
    'moved  -> ...' (ROADMAP item 63)."""
    c, G = ctx.c, ctx.G
    node = added_id(
        text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [0, 0]}], **G}))
    )
    try:
        await c('snapshot_graph', {'label': 'at the origin', **G})
        await c('apply_edits', {'ops': [{'op': 'move', 'node': node, 'position': [150, 75]}], **G})
        t = text(await c('diff_graph', {'against': 'at the origin', 'show_positions': True, **G}))
        moved = next((l for l in t.splitlines() if l.startswith('~ node %s' % node)), t)
        check(
            'diff_graph',
            'a move from (0, 0) shows both positions',
            re.search(r'~ node %s blur: moved 0 0 0 -> 150 75 0' % node, t) is not None,
            moved,
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': node}], **G})
