"""Measuring: node_stats, sweep_param, check_tiling and read_designer_log."""

import os
import re

from .common import GRAPH_OF, INHERIT, PLUGIN, TEST_GRAPH, Ctx, added_id, check, text


async def run(ctx: Ctx) -> None:
    c, G, clouds, slope, lv = ctx.c, ctx.G, ctx.clouds, ctx.slope, ctx.lv
    # --- pixel statistics
    t = text(await c('node_stats', {'node_id': lv, 'points': [[0, 0]], 'region': [0, 0, 64, 64], **G}))
    check(
        'node_stats', 'stats + region + point', 'min' in t and 'pixel (0,0)' in t and 'region' in t, t.splitlines()[0]
    )
    uni = added_id(
        text(
            await c(
                'apply_edits',
                {'ops': [{'op': 'add', 'definition': 'uniform', 'params': {'outputcolor': [0.2, 0.4, 0.6, 0.8]}}], **G},
            )
        )
    )
    t = text(await c('node_stats', {'node_id': uni, 'points': [[1, 1]], **G}))
    check('node_stats', 'exact known colour', 'R=0.2000, G=0.4000, B=0.6000, A=0.8000' in t, t.splitlines()[-1])
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': uni}], **G})

    # --- parameter sweep, tiling, log
    before = text(await c('describe_graph', {'node_ids': [clouds], 'include_params': True, **G}))
    r_ = await c(
        'sweep_param',
        {'node_id': clouds, 'param': 'scale', 'values': [1, 4, 16], 'view_node': slope, 'tile_size': 128, **G},
    )
    sweep_text = text(r_)
    images = [x for x in r_.content if x.type == 'image']
    after = text(await c('describe_graph', {'node_ids': [clouds], 'include_params': True, **G}))
    check(
        'sweep_param',
        '3 values + image',
        len(images) == 1 and sweep_text.count('scale = ') == 3,
        sweep_text.splitlines()[0],
    )
    check('sweep_param', 'original restored', 'restored' in sweep_text and before == after, '')
    before = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
    t = text(await c('sweep_param', {'node_id': lv, 'param': '$outputsize', 'values': [[7, 7], [8, 8]], **G}))
    after = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
    check(
        'sweep_param',
        '$outputsize takes effect and is restored',
        '(128x128)' in t and '(256x256)' in t and before == after,
        t + before + after,
    )
    # changing a parameter's inheritance resets its value to the default (AGENTS.md), so a sweep
    # of one that isn't Absolute must put the inheritance back before the value (REVIEW.md HLP-26)
    RELATIVE_SIZE = GRAPH_OF % TEST_GRAPH + (
        'from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n'
        'from sd.api.sdvalueint2 import SDValueInt2\nfrom sd.api.sdbasetypes import int2\n'
        "n = g.getNodeFromId('%s'); p = n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
        'n.setPropertyInheritanceMethod(p, IM.RelativeToParent)\n'
        'n.setPropertyValue(p, SDValueInt2.sNew(int2(1, 1)))\n'
        '%s\n'
        'v = n.getPropertyValue(p).get()\n'
        "print('INHERIT=%%s VALUE=%%d,%%d' %% (n.getPropertyInheritanceMethod(p).name, v.x, v.y))"
    )
    # each switch on its own, on a node and on the graph (REVIEW.md TST-42)
    fact = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + (
                    'from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n'
                    'from sd.api.sdvalueint import SDValueInt\nfrom sd.api.sdvalueint2 import SDValueInt2\n'
                    'from sd.api.sdbasetypes import int2\n'
                    'def resets(target, pid, value, read, start):\n'
                    '    p = target.getPropertyFromId(pid, SDPropertyCategory.Input); was = target.getPropertyInheritanceMethod(p)\n'
                    '    kept = target.getPropertyValue(p)\n'
                    '    seen = []\n'
                    '    try:\n'  # put back even if a call fails, for the later checks (REVIEW.md TST-46)
                    '        for there, back in ((start, IM.Absolute), (IM.Absolute, start)):\n'
                    '            target.setPropertyInheritanceMethod(p, there); target.setPropertyValue(p, value)\n'
                    '            target.setPropertyInheritanceMethod(p, back); seen.append(read(target.getPropertyValue(p).get()))\n'
                    '    finally:\n'
                    '        target.setPropertyInheritanceMethod(p, was); target.setPropertyValue(p, kept)\n'
                    '    return seen\n'
                    "n = g.getNodeFromId('%s')\n"
                    "print('NODE_SIZE=%%s' %% resets(n, '$outputsize', SDValueInt2.sNew(int2(1, 1)), lambda v: (v.x, v.y), IM.RelativeToParent))\n"
                    "print('GRAPH_SEED=%%s' %% resets(g, '$randomseed', SDValueInt.sNew(5), lambda v: v, IM.RelativeToParent))"
                )
                % lv
            },
        )
    )
    # neither switch keeps the value set (1, 1 / 5), and back to inherited gives the default
    # (REVIEW.md TST-45)
    kept_any = re.search(r'\(1, 1\)|SEED=\[[^]]*\b5\b', fact)
    default_back = re.search(r'NODE_SIZE=\[\([^)]*\), \(0, 0\)\]', fact) and re.search(r'GRAPH_SEED=\[-?\d+, 0\]', fact)
    check(
        'designer facts',
        "changing a parameter's inheritance doesn't keep its value, either way, node or graph (AGENTS.md)",
        default_back and not kept_any,
        fact.strip(),
    )
    await c('execute_designer_code', {'code': RELATIVE_SIZE % (lv, '')})
    t = text(await c('sweep_param', {'node_id': lv, 'param': '$outputsize', 'values': [[7, 7]], **G}))
    after = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
    check(
        'sweep_param',
        'a relative $outputsize comes back with its offset',
        'INHERIT=RelativeToParent' in after and 'VALUE=x: 1, y: 1' in after,
        t.splitlines()[-1] + ' | ' + after.strip(),
    )
    await c(
        'execute_designer_code',
        {
            'code': INHERIT % (TEST_GRAPH, lv)
            + (
                '\nfrom sd.api.sdproperty import SDPropertyInheritanceMethod as IM\n'
                'n.setPropertyInheritanceMethod(p, IM.RelativeToInput)'
            )
        },
    )  # back as before
    r_ = await c('sweep_param', {'node_id': lv, 'param': 'nope', 'values': [1], **G})
    check('sweep_param', 'error on bad param', r_.is_error and 'not a parameter' in text(r_), text(r_))
    t = text(await c('check_tiling', {'node_id': clouds, **G}))
    check('check_tiling', 'tileable noise passes both axes', t.count('tiles seamlessly') == 2, t)
    grad = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'gradient_linear_1'}], **G})))
    r_ = await c('check_tiling', {'node_id': grad, 'axis': 'diagonal', **G})
    check('check_tiling', 'error on bad axis', r_.is_error and 'axis must be' in text(r_), text(r_))
    t = text(await c('check_tiling', {'node_id': grad, 'axis': 'vertical', **G}))
    check('check_tiling', 'vertical gradient has a seam', 'VISIBLE SEAM' in t, t.splitlines()[-1])
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': grad}], **G})
    t = text(await c('read_designer_log', {'contains': PLUGIN, 'lines': 5}))
    check('read_designer_log', 'finds bridge start', 'listening on' in t, t.splitlines()[0])
    # a warning of our own, so the filter has something to find (REVIEW.md TST-4)
    marker = 'mcp self-test warning %d' % os.getpid()
    await c('execute_designer_code', {'code': 'import sd\nsd.getContext().getLogger().warning(%r)' % marker})
    t = text(await c('read_designer_log', {'errors_only': True, 'lines': 400}))
    found = t.splitlines()[1:]
    check(
        'read_designer_log',
        'errors_only filter',
        any(marker in l for l in found) and all(('[ERROR]' in l or '[WARNING]' in l) for l in found),
        t.splitlines()[0],
    )
    t = text(await c('read_designer_log', {'lines': 5, 'since_last_start': False}))
    check('read_designer_log', 'whole log', 'log.txt' in t, t.splitlines()[0])
