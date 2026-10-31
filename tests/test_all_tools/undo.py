"""One tool call = one undo step (acts only while the self-test graph is in the editor)."""

import re

from .common import NODE_EXISTS, TEST_GRAPH, UNDO_REDO, Ctx, added_id, check, skip, text


async def run(ctx: Ctx) -> None:
    c, G = ctx.c, ctx.G
    # --- one tool call = one undo step (only acts while the self-test graph is in the editor)
    ub = added_id(
        text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [0, 400]}], **G}))
    )
    t = text(await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Undo')}))
    if 'SCHEDULED' not in t:
        skip('apply_edits', 'add: one undo step', 'self-test graph not in focus or Undo unavailable (%s)' % t.strip())
    else:
        gone = 'EXISTS=False' in text(await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, ub)}))
        if not gone:
            # Undo hit some other step: put it back at once
            await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Redo')})
            await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, ub)})
        check('apply_edits', 'add: one Undo removes the added node', gone, '')
        if gone:
            await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Redo')})
            back = 'EXISTS=True' in text(await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, ub)}))
            check('apply_edits', 'add: Redo restores it', back, '')
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': ub}], **G})
    t = text(
        await c(
            'execute_designer_code',
            {
                'undo_label': 'self-test: two nodes',
                'code': (
                    'import sd\nfrom sd.api.sdbasetypes import float2\n'
                    'g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() '
                    "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\nids=[]\n"
                    "for i in range(2):\n    n=g.newNode('sbs::compositing::blur'); n.setPosition(float2(200*i, 500)); ids.append(n.getIdentifier())\n"
                    "print('IDS=' + ','.join(ids))"
                )
                % TEST_GRAPH,
            },
        )
    )
    # no match raises AttributeError, which the run's except reports (REVIEW.md TST-63)
    two = re.search(r'IDS=(\d+),(\d+)', t).groups()  # type: ignore[union-attr]
    t = text(await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Undo')}))
    if 'SCHEDULED' not in t:
        skip('execute_designer_code', 'one undo step', 'self-test graph not in focus or Undo unavailable')
    else:
        states = [
            ('EXISTS=True' in text(await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, i)})))
            for i in two
        ]
        if any(states):
            await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Redo')})
        check('execute_designer_code', 'one Undo reverts the whole run', not any(states), str(states))
        if not any(states):
            await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Redo')})
            states = [
                ('EXISTS=True' in text(await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, i)})))
                for i in two
            ]
            check('execute_designer_code', 'one Redo restores it', all(states), str(states))
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in list(two)], **G})
