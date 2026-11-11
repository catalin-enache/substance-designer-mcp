"""What params' checks read: the self-test graph at 512 px (its size set to 10 must change it) with a clouds_2
instance (its seed's effect is computed), a slope blur (an int Samples, a float Intensity) and a levels node (a float4
levelinlow), unconnected, every parameter, inheritance and seed at a new node's default."""

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
                    {'op': 'add', 'definition': 'levels', 'ref': 'lv', 'position': [0, 0]},
                ],
                **ctx.G,
            },
        )
    )
    ctx.clouds = added['clouds']
    ctx.slope = added['slope']
    ctx.lv = added['lv']
