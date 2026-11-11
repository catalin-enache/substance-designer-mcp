"""What render's checks read: the self-test graph saved as mcp_selftest.sbs (the cooked .sbsar is named after it),
the saved file and the live graph alike, with clouds_2 -> slope blur -> levels -> an output identified `height`
(clouds the only source of randomness, its seed inherited), the graph's seed at 5, inherited, its size overridable,
512 px by default (renders override it), and the levels node's leveloutlow exposed as the float4 input `floor`
(rendering it at 0.1 and 0.9 must differ: levelinlow 0.3 keeps the input's dark part dark)."""

import os

from test_all_tools.common import TEST_GRAPH, Ctx, prepared_call, refs


async def prepare(ctx: Ctx) -> None:
    c = ctx.c
    await prepared_call(c, 'create_graph', {'name': TEST_GRAPH, 'size_log2': 9})
    ctx.G = {'graph': TEST_GRAPH}
    added = refs(
        await prepared_call(
            c,
            'apply_edits',
            {
                'ops': [
                    {'op': 'add', 'definition': 'noise_clouds_2.sbs/clouds_2', 'ref': 'clouds', 'position': [-600, 0]},
                    {
                        'op': 'add',
                        'definition': 'slope_blur.sbs/slope_blur_grayscale_2',
                        'ref': 'slope',
                        'position': [-300, 0],
                    },
                    {
                        'op': 'add',
                        'definition': 'levels',
                        'ref': 'lv',
                        'position': [0, 0],
                        'params': {'levelinlow': [0.3] * 4},
                    },
                    {'op': 'add', 'definition': 'output', 'ref': 'out', 'position': [300, 0], 'identifier': 'height'},
                    {'op': 'connect', 'from': 'clouds', 'to': 'slope', 'input': 'Source'},
                    {'op': 'connect', 'from': 'slope', 'to': 'lv', 'input': 'input1'},
                    {'op': 'connect', 'from': 'lv', 'to': 'out', 'input': 'inputNodeOutput'},
                    {'op': 'set', 'node': 'graph', 'params': {'$randomseed': 5}},
                    {
                        'op': 'expose',
                        'node': 'lv',
                        'param': 'leveloutlow',
                        'input_id': 'floor',
                        'label': 'Floor',
                        'default': [0.25] * 4,
                        'min': 0,
                        'max': 1,
                    },
                ],
                **ctx.G,
            },
        )
    )
    ctx.clouds = added['clouds']
    await prepared_call(c, 'set_graph_size', {'size_log2': 9, 'overridable': True, **ctx.G})
    ctx.sbs = os.path.join(ctx.scratch, TEST_GRAPH + '.sbs')
    await prepared_call(c, 'save_package', {'graph_or_path': TEST_GRAPH, 'save_as': ctx.sbs})
