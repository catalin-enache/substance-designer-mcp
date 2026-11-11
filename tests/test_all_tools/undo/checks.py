"""One tool call = one undo step (acts only while the self-test graph is in the editor)."""

import re
from textwrap import dedent

from test_all_tools.common import NODE_EXISTS, TEST_GRAPH, UNDO_REDO, Ctx, added_id, check, skip, text


async def run(ctx: Ctx) -> None:
    # in a pool it runs last, alone (categories.SOLO: beside the others its Undo failed)
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
    # an output's annotations too: not parameters, so nothing else shows that Undo reaches them. Each state is read, so
    # a refused set can't pass here by Undo reverting something else
    changed = "identifier='undo_me' label='Undo' usage=roughness"
    await c(
        'apply_edits',
        {'ops': [{'op': 'set', 'node': ctx.out, 'identifier': 'undo_me', 'label': 'Undo', 'usage': 'roughness'}], **G},
    )
    was_set = changed in text(await c('describe_graph', G))
    check('apply_edits', "set: an output's fields, before the Undo", was_set, '')
    t = text(await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Undo')})) if was_set else ''
    if 'SCHEDULED' not in t:
        skip(
            'apply_edits',
            "set: one Undo puts an output's fields back",
            'not applied, self-test graph not in focus or Undo unavailable (%s)' % t,
        )
    else:
        await c(
            'execute_designer_code',
            {'code': 'from PySide6.QtWidgets import QApplication; QApplication.processEvents()'},
        )
        after = text(await c('describe_graph', G))
        back = "identifier='height' usage=none" in after and 'undo_me' not in after
        if not back:  # Undo hit some other step: put it back at once
            await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Redo')})
        check('apply_edits', "set: one Undo puts an output's fields back", back, after)
    await c('apply_edits', {'ops': [{'op': 'set', 'node': ctx.out, 'identifier': 'height'}], **G})
    t = text(
        await c(
            'execute_designer_code',
            {
                'undo_label': 'self-test: two nodes',
                'code': (
                    dedent("""\
                        import sd
                        from sd.api.sdbasetypes import float2
                        g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]
                        ids=[]
                        for i in range(2):
                            n=g.newNode('sbs::compositing::blur'); n.setPosition(float2(200*i, 500)); ids.append(n.getIdentifier())
                        print('IDS=' + ','.join(ids))""")
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
