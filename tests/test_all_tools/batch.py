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
    # the error names the node the batch had already added, so a retry needn't duplicate it (REVIEW.md SRV-35)
    left = [
        l.split()[0] for l in text(await c('describe_graph', G)).splitlines() if ' levels @' in l and l.split()[0] != lv
    ]
    check(
        'apply_edits',
        'a failed batch names the nodes it added',
        len(left) == 1 and "%s (ref 'x')" % left[0] in text(r_),
        text(r_).strip()[-200:] + ' | ' + str(left),
    )
    # a node the batch added and then deleted isn't listed as added when a later op fails (REVIEW.md HLP-52)
    r_ = await c(
        'apply_edits',
        {
            'ops': [
                {'op': 'add', 'definition': 'blur', 'ref': 'gone'},
                {'op': 'delete', 'node': 'gone'},
                {'op': 'set', 'node': lv, 'params': {'nope': 1}},
            ],
            **G,
        },
    )
    check(
        'apply_edits',
        'a failed batch leaves out a node it already deleted',
        r_.is_error and 'ops 0-1 were applied' in text(r_) and 'added:' not in text(r_),
        text(r_).strip()[-200:],
    )
    # positions as numeric strings work, as main's float() conversion allowed (REVIEW.md HLP-50)
    t = text(
        await c(
            'apply_edits',
            {'ops': [{'op': 'add', 'definition': 'blur', 'ref': 's', 'position': ['100', '-200.5']}], **G},
        )
    )
    string_pos = re.search(r"'s': '(\d+)'", t)
    try:
        check('apply_edits', 'add: a position as numeric strings', 'added' in t and '@(100,-200)' in t, t.strip()[:120])
    finally:
        if string_pos:
            await c('apply_edits', {'ops': [{'op': 'delete', 'node': string_pos.group(1)}], **G})
    # a node added without a ref is named too (REVIEW.md HLP-49)
    had = {
        l.split()[0] for l in text(await c('describe_graph', G)).splitlines() if l.split() and l.split()[0].isdigit()
    }
    r_ = await c(
        'apply_edits',
        {'ops': [{'op': 'add', 'definition': 'blur'}, {'op': 'set', 'node': lv, 'params': {'nope': 1}}], **G},
    )
    new = [
        l.split()[0]
        for l in text(await c('describe_graph', G)).splitlines()
        if l.split() and l.split()[0].isdigit() and l.split()[0] not in had
    ]
    try:
        check(
            'apply_edits',
            'a failed batch names a node added without a ref',
            r_.is_error and len(new) == 1 and new[0] in text(r_).strip().splitlines()[-1],
            text(r_).strip()[-200:] + ' | ' + str(new),
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in new], **G})
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
    # a ref reused after its first node is deleted names the new node: the pre-check's tracking of
    # deleted nodes (REVIEW.md HLP-42) doesn't refuse it
    r_ = await c(
        'apply_edits',
        {
            'ops': [
                {'op': 'add', 'definition': 'blur', 'ref': 'r', 'position': [900, 900]},
                {'op': 'delete', 'node': 'r'},
                {'op': 'add', 'definition': 'blur', 'ref': 'r', 'position': [900, 900]},
                {'op': 'move', 'node': 'r', 'position': [950, 900]},
                {'op': 'delete', 'node': 'r'},
            ],
            **G,
        },
    )
    check(
        'apply_edits', 'a ref reused after a delete names the new node', 'applied 5 op(s)' in text(r_), text(r_)[-150:]
    )
    # an enum value as a numeric string, like int parameters accept (REVIEW.md HLP-11)
    r_ = await c('apply_edits', {'ops': [{'op': 'set', 'node': batch_blend, 'params': {'blendingmode': '3'}}], **G})
    check('apply_edits', 'set: enum value as a numeric string', not r_.is_error, text(r_))
    t = text(await c('describe_graph', G))
    x_ids = [l.split()[0] for l in t.splitlines() if ' levels ' in l and l.split()[0] != lv]
    await c(
        'apply_edits',
        {
            'ops': [
                {'op': 'delete', 'node': n}
                for n in x_ids + [batch_blend] + [l.split()[0] for l in t.splitlines() if ' uniform ' in l]
            ],
            **G,
        },
    )
    # a field the op doesn't take refuses the whole batch: a typo reported success, the node somewhere else and its
    # parameters unset (REVIEW.md HLP-62)
    before = text(await c('execute_designer_code', {'code': COUNT_NODES}))
    r_ = await c(
        'apply_edits',
        {
            'ops': [
                {'op': 'add', 'definition': 'levels'},
                {'op': 'add', 'definition': 'levels', 'postion': [999, 999]},
            ],
            **G,
        },
    )
    after = text(await c('execute_designer_code', {'code': COUNT_NODES}))
    check(
        'apply_edits',
        'refuses a field the op does not take, nothing added',
        r_.is_error and "unknown field 'postion'" in text(r_) and 'position' in text(r_) and after == before,
        text(r_)[-200:],
    )
