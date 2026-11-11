"""Measuring: node_stats, sweep_param, check_tiling and read_designer_log."""

import os
import re
from textwrap import dedent
from typing import Any

from mcp.types import CallToolResult

from test_all_tools.common import PLUGIN, TEST_GRAPH, Ctx, added_id, check, designer_script, is_image, refs, text


def _a_feeding_pair(G: dict[str, str]) -> dict[str, Any]:
    """apply_edits' arguments: a fresh gradient feeding a fresh normal."""
    return {
        'ops': [
            {'op': 'add', 'definition': 'gradient_linear_1', 'ref': 'up', 'position': [-600, 900]},
            {'op': 'add', 'definition': 'normal', 'ref': 'down', 'position': [-300, 900]},
            {'op': 'connect', 'from': 'up', 'to': 'down', 'input': 'input1'},
        ],
        **G,
    }


def _its_nodes(result: CallToolResult) -> tuple[str, str]:
    added = refs(text(result))
    return added['up'], added['down']


async def check_an_output_added_right_after_the_node_feeding_it_was_measured(ctx: Ctx) -> None:
    """With the graph open in the editor and an output node in it: export_outputs of an output node added right after
    the node feeding it was measured said "computed no image" (REVIEW.md HLP-101, seen in the first trials in a
    Designer just started: this runs first in `run`, as nothing has been computed yet). Fresh nodes for each."""
    c, G = ctx.c, ctx.G
    first = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'output'}], **G})))
    opened = await c('open_graph', G)
    name = 'an output added right after the node feeding it was measured, the graph open'
    if opened.is_error or 'opened' not in text(opened):
        check('export_outputs', name, False, 'the graph did not open: ' + text(opened))
        return
    wrong = []
    for trial in range(3):
        up, down = _its_nodes(await c('apply_edits', _a_feeding_pair(G)))
        measured = text(await c('node_stats', {'node_id': up, 'points': [[0, 0]], **G}))
        if 'pixel (0,0)' not in measured:
            wrong.append('the node feeding it: ' + measured)
        identifier = 'just_added_%d' % trial
        out = refs(
            text(
                await c(
                    'apply_edits',
                    {
                        'ops': [
                            {'op': 'add', 'definition': 'output', 'ref': 'o', 'identifier': identifier},
                            {'op': 'connect', 'from': down, 'to': 'o', 'input': 'inputNodeOutput'},
                        ],
                        **G,
                    },
                )
            )
        )['o']
        t = text(
            await c(
                'export_outputs',
                {'output_dir': os.path.join(ctx.scratch, 'just_added'), 'outputs': [identifier], **G},
            )
        )
        if identifier + '.png' not in t:
            wrong.append(t.strip())
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in (out, down, up)], **G})
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': first}], **G})
    check('export_outputs', name, not wrong, '; '.join(wrong))


async def check_a_node_measured_right_after_the_one_feeding_it(ctx: Ctx) -> None:
    """With the graph open in the editor and an output node in it, as the user works: a node measured right after the
    node feeding it was. node_stats, preview_node and sweep_param's view, which compute a node through a temporary
    output, said "produced no texture (are its inputs connected?)" (REVIEW.md HLP-100; measured: never without an output
    node in the graph). A fresh pair of nodes for each, so a retry can't pass it. Without
    the graph open, or the node feeding it measured, that state isn't reached: a failure (REVIEW.md TST-259). The tools
    compute twice when the first gives no texture, so the last one runs the helper's steps with one compute: that the
    plugin lets Designer settle between jobs, which was the cause (REVIEW.md PLG-38)."""
    c, G = ctx.c, ctx.G
    # its own output node: measure's graph has none, and with none it never happened
    out = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'output'}], **G})))
    opened = await c('open_graph', G)
    if opened.is_error or 'opened' not in text(opened):
        check('open_graph', 'the graph opens, for a node measured right after the one feeding it', False, text(opened))
        return

    async def feeding_it_measured(up: str) -> str:
        """Empty when the node feeding it was measured, else what went wrong."""
        t = text(await c('node_stats', {'node_id': up, 'points': [[0, 0]], **G}))
        return '' if 'pixel (0,0)' in t else 'the node feeding it: %s; ' % t

    up, down = _its_nodes(await c('apply_edits', _a_feeding_pair(G)))
    before = await feeding_it_measured(up)
    t = text(await c('node_stats', {'node_id': down, 'points': [[256, 256]], **G}))
    check(
        'node_stats',
        'a node right after the one feeding it, the graph open',
        not before and 'pixel (256,256)' in t,
        before + t,
    )
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': up}, {'op': 'delete', 'node': down}], **G})

    up, down = _its_nodes(await c('apply_edits', _a_feeding_pair(G)))
    before = await feeding_it_measured(up)  # the measure seen to bring it on every time
    r_ = await c('preview_node', {'node_id': down, **G})
    check(
        'preview_node',
        'a node right after the one feeding it, the graph open',
        not before and is_image(r_),
        before + ('' if is_image(r_) else text(r_)),
    )
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': up}, {'op': 'delete', 'node': down}], **G})

    up, down = _its_nodes(await c('apply_edits', _a_feeding_pair(G)))
    before = await feeding_it_measured(up)
    r_ = await c('sweep_param', {'node_id': down, 'param': 'intensity', 'values': [1, 5], 'view_node': down, **G})
    check(
        'sweep_param',
        'its view right after the node feeding it was measured, the graph open',
        not before and any(x.type == 'image' for x in r_.content) and not r_.is_error,
        before + text(r_)[:300],
    )
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in (up, down)], **G})

    up, down = _its_nodes(await c('apply_edits', _a_feeding_pair(G)))
    before = await feeding_it_measured(up)
    one_compute = dedent("""
        g = find_graph(%r)
        node = g.getNodeFromId(%r)
        out = list(node.getProperties(SDPropertyCategory.Output))[0]
        temp = g.newNode('sbs::compositing::output')
        node.newPropertyConnectionFromId(out.getId(), temp, 'inputNodeOutput')
        try:
            g.compute()
            value = node.getPropertyValue(out)
            print('TEXTURE=%%s' %% (value is not None and value.get() is not None))
        finally:
            g.deleteNode(temp)
    """) % (G['graph'], down)
    t = text(await c('execute_designer_code', {'code': ctx.helper_source + '\n' + one_compute}))
    check(
        'execute_designer_code',
        'a job right after the node feeding it was measured: one compute gives the texture (the plugin waits)',
        not before and 'TEXTURE=True' in t,
        before + t.strip()[-300:],
    )
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in (up, down, out)], **G})


async def run(ctx: Ctx) -> None:
    c, G, clouds, slope, lv = ctx.c, ctx.G, ctx.clouds, ctx.slope, ctx.lv
    await check_an_output_added_right_after_the_node_feeding_it_was_measured(ctx)
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
    # the original differs from the default, which describe_graph doesn't list: a sweep that put the default back
    # instead would pass otherwise (REVIEW.md TST-231)
    check(
        'sweep_param',
        'original restored',
        'restored' in sweep_text and before == after and re.search(r'scale = 4\b', before) is not None,
        before[-200:],
    )
    before = text(await designer_script(c, 'shared/node_size_inheritance', graph=TEST_GRAPH, node=lv))
    t = text(await c('sweep_param', {'node_id': lv, 'param': '$outputsize', 'values': [[7, 7], [8, 8]], **G}))
    after = text(await designer_script(c, 'shared/node_size_inheritance', graph=TEST_GRAPH, node=lv))
    check(
        'sweep_param',
        '$outputsize takes effect and is restored',
        '(128x128)' in t and '(256x256)' in t and before == after,
        t + before + after,
    )
    # changing a parameter's inheritance resets its value to the default (GUIDE.md), so a sweep
    # of one that isn't Absolute must put the inheritance back before the value (REVIEW.md HLP-26)
    # each switch on its own, on a node and on the graph (REVIEW.md TST-42)
    fact = text(await designer_script(c, 'measure/inheritance_resets', graph=TEST_GRAPH, node=lv))
    # neither switch keeps the value set (1, 1 / 5), and back to inherited gives the default
    # (REVIEW.md TST-45)
    kept_any = re.search(r'\(1, 1\)|SEED=\[[^]]*\b5\b', fact)
    default_back = re.search(r'NODE_SIZE=\[\([^)]*\), \(0, 0\)\]', fact) and re.search(r'GRAPH_SEED=\[-?\d+, 0\]', fact)
    check(
        'designer facts',
        "changing a parameter's inheritance doesn't keep its value, either way, node or graph (GUIDE.md)",
        default_back and not kept_any,
        fact.strip(),
    )
    await designer_script(c, 'measure/relative_size', graph=TEST_GRAPH, node=lv)
    t = text(await c('sweep_param', {'node_id': lv, 'param': '$outputsize', 'values': [[7, 7]], **G}))
    after = text(await designer_script(c, 'shared/node_size_inheritance', graph=TEST_GRAPH, node=lv))
    check(
        'sweep_param',
        'a relative $outputsize comes back with its offset',
        'INHERIT=RelativeToParent' in after and 'VALUE=x: 1, y: 1' in after,
        t.splitlines()[-1] + ' | ' + after.strip(),
    )
    await designer_script(
        c, 'shared/node_size_inheritance', graph=TEST_GRAPH, node=lv, relative_to_input=True
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
    await c(
        'execute_designer_code',
        {
            'code': dedent("""\
                import sd
                sd.getContext().getLogger().warning(%r)""")
            % marker
        },
    )
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
    await check_a_node_measured_right_after_the_one_feeding_it(ctx)
