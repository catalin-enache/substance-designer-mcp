"""What link_display's checks read: the self-test graph saved as mcp_selftest.sbs, holding a linked bitmap whose file
exists, with clouds_2 -> slope blur -> levels -> output connected (clouds feeding one input: a check adds two more),
every node apart from the others (a link's length is measured), the levels node at (0, 0): Designer writes no position
for a node there, and longer_than skipped its links (ROADMAP item 63); node_stats of the levels node, measured now: the
links' display must leave what it computes unchanged; and the graph open in the editor, as a user has it."""

import os

from test_all_tools.common import TEST_GRAPH, Ctx, prepared_call, refs


async def prepare(ctx: Ctx) -> None:
    c = ctx.c
    await prepared_call(c, 'create_graph', {'name': TEST_GRAPH, 'size_log2': 9})
    ctx.G = {'graph': TEST_GRAPH}
    from PIL import Image

    ctx.png = os.path.join(ctx.scratch, 'selftest_bitmap.png')
    Image.new('RGB', (64, 32), (200, 100, 50)).save(ctx.png)
    added = refs(
        await prepared_call(
            c,
            'apply_edits',
            {
                'ops': [
                    {
                        'op': 'add',
                        'definition': 'noise_clouds_2.sbs/clouds_2',
                        'ref': 'clouds',
                        'position': [-600, 0],
                    },
                    {
                        'op': 'add',
                        'definition': 'slope_blur.sbs/slope_blur_grayscale_2',
                        'ref': 'slope',
                        'position': [-300, 0],
                    },
                    {'op': 'add', 'definition': 'levels', 'ref': 'lv', 'position': [0, 0]},
                    {'op': 'add', 'definition': 'output', 'ref': 'out', 'position': [300, 0]},
                    {'op': 'bitmap', 'path': ctx.png, 'position': [-600, 300]},
                    {'op': 'connect', 'from': 'clouds', 'to': 'slope', 'input': 'Source'},
                    {'op': 'connect', 'from': 'slope', 'to': 'lv', 'input': 'input1'},
                    {'op': 'connect', 'from': 'lv', 'to': 'out', 'input': 'inputNodeOutput'},
                ],
                **ctx.G,
            },
        )
    )
    ctx.clouds = added['clouds']
    ctx.lv = added['lv']
    sbs = os.path.join(ctx.scratch, TEST_GRAPH + '.sbs')
    await prepared_call(c, 'save_package', {'graph_or_path': TEST_GRAPH, 'save_as': sbs})
    ctx.stats_before = await prepared_call(c, 'node_stats', {'node_id': ctx.lv, **ctx.G})
    await prepared_call(c, 'open_graph', ctx.G)
