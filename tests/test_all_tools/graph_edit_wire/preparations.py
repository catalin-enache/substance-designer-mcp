"""What graph_edit_wire's checks read: the self-test graph with the four nodes it connects (a clouds_2 instance, a
slope blur with Source and Effect, a levels node, an output), unconnected, placed where Designer puts them (the move
check moves them to positions of its own), and the slope blur's Samples at 16, which describe_graph must show."""

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
                    {'op': 'add', 'definition': 'noise_clouds_2.sbs/clouds_2', 'ref': 'clouds'},
                    {
                        'op': 'add',
                        'definition': 'slope_blur.sbs/slope_blur_grayscale_2',
                        'ref': 'slope',
                        'params': {'Samples': 16},
                    },
                    {'op': 'add', 'definition': 'levels', 'ref': 'lv'},
                    {'op': 'add', 'definition': 'output', 'ref': 'out'},
                ],
                **ctx.G,
            },
        )
    )
    ctx.clouds = added['clouds']
    ctx.slope = added['slope']
    ctx.lv = added['lv']
    ctx.out = added['out']
