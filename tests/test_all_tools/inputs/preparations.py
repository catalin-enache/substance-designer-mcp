"""What inputs' checks read: the self-test graph with clouds_2 -> slope blur -> levels connected (the levels node fed a
bright input: lowering its levelouthigh must lower its max), the slope blur's Samples at 16 (an expose without a
default takes it, and keeps it when removed) and Intensity at 8, and levelinlow at 0.3, which keeps the input's dark part
dark (sweeping `floor` from 0.1 to 0.9 must raise the mean by more than 0.3: 0.717 to less without them); no graph
input yet."""

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
                        'params': {'Samples': 16, 'Intensity': 8.0},
                    },
                    {
                        'op': 'add',
                        'definition': 'levels',
                        'ref': 'lv',
                        'position': [0, 0],
                        'params': {'levelinlow': [0.3] * 4},
                    },
                    {'op': 'connect', 'from': 'clouds', 'to': 'slope', 'input': 'Source'},
                    {'op': 'connect', 'from': 'slope', 'to': 'lv', 'input': 'input1'},
                ],
                **ctx.G,
            },
        )
    )
    ctx.slope = added['slope']
    ctx.lv = added['lv']
