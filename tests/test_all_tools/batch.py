"""Batch edits: apply_edits."""

import re

from .common import Ctx, check, text


async def run(ctx: Ctx) -> None:
    c, G, slope, lv, COUNT_NODES = ctx.c, ctx.G, ctx.slope, ctx.lv, ctx.COUNT_NODES
    # --- batch edits
    t = text(
        await c(
            'apply_edits',
            {
                'ops': [
                    {
                        'op': 'add',
                        'definition': 'uniform',
                        'ref': 'u',
                        'position': [-300, 300],
                        'params': {'colorswitch': False, 'outputcolor': [0.5, 0.5, 0.5, 1]},
                    },
                    {'op': 'add', 'definition': 'blend', 'ref': 'b', 'params': {'blendingmode': 'multiply'}},
                    {'op': 'connect', 'from': 'u', 'to': 'b', 'input': 'source'},
                    {'op': 'connect', 'from': slope, 'to': 'b', 'input': 'destination'},
                    {'op': 'move', 'node': 'b', 'position': [0, 300]},
                    {'op': 'set', 'node': 'b', 'params': {'opacitymult': 0.5}},
                    {'op': 'disconnect', 'node': 'b', 'input': 'destination'},
                    {
                        'op': 'expose',
                        'node': 'b',
                        'param': 'opacitymult',
                        'input_id': 'batch_opacity',
                        'max': 1,
                        'step': 0.05,
                        'group': 'Batch',
                    },
                ],
                **G,
            },
        )
    )
    check(
        'apply_edits',
        '8 ops with refs',
        'applied 8 op(s)' in t and 'removed 1 connection(s) into' in t and "graph input 'batch_opacity'" in t,
        t.splitlines()[-1],
    )
    line = next((l for l in text(await c('list_graph_inputs', G)).splitlines() if l.startswith('batch_opacity')), '')
    check('apply_edits', 'expose op passes step and group', "group='Batch'" in line and 'step=0.05' in line, line)
    await c('remove_graph_input', {'input_id': 'batch_opacity', **G})
    # no match raises AttributeError, which the run's except reports (REVIEW.md TST-63)
    batch_blend = re.search(r"'b': '(\d+)'", t).group(1)  # type: ignore[union-attr]
    r_ = await c(
        'apply_edits',
        {
            'ops': [
                {'op': 'add', 'definition': 'levels', 'ref': 'x'},
                {'op': 'connect', 'from': 'x', 'to': batch_blend, 'input': 'nope'},
            ],
            **G,
        },
    )
    check('apply_edits', 'stops at failing op', r_.is_error and 'op 1 (connect) failed' in text(r_), text(r_))
    # the "its node was added" note only when a node really was (REVIEW.md HLP-5)
    r_ = await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'not_a_real_node', 'params': {'a': 1}}], **G})
    check(
        'apply_edits',
        'a bad definition is not reported as added',
        r_.is_error and 'op 0 (add) failed' in text(r_) and 'its node was added' not in text(r_),
        text(r_),
    )
    # an add whose params fail now leaves no node at all, and says so (REVIEW.md HLP-30)
    before = text(await c('execute_designer_code', {'code': COUNT_NODES}))
    r_ = await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels', 'params': {'nope': 1}}], **G})
    after = text(await c('execute_designer_code', {'code': COUNT_NODES}))
    check(
        'apply_edits',
        'an add whose params failed leaves no node, and says so',
        r_.is_error and 'not added' in text(r_) and 'its node was added' not in text(r_) and before == after,
        text(r_),
    )
    # an enum value as a numeric string, like int parameters accept (REVIEW.md HLP-11)
    r_ = await c('set_params', {'node_id': batch_blend, 'params': {'blendingmode': '3'}, **G})
    check('set_params', 'enum value as a numeric string', not r_.is_error, text(r_))
    t = text(await c('describe_graph', G))
    x_ids = [l.split()[0] for l in t.splitlines() if ' levels ' in l and l.split()[0] != lv]
    await c(
        'delete_nodes',
        {'node_ids': x_ids + [batch_blend] + [l.split()[0] for l in t.splitlines() if ' uniform ' in l], **G},
    )
