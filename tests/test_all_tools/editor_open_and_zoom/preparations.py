"""What editor_open_and_zoom's checks read: the self-test graph with a clouds_2 instance and a slope blur apart from
each other, and a frame titled 'Shape' around them (open_graph fits it)."""

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
                ],
                **ctx.G,
            },
        )
    )
    ctx.clouds = added['clouds']
    ctx.slope = added['slope']
    await prepared_call(c, 'add_frame', {'node_ids': [ctx.clouds, ctx.slope], 'title': 'Shape', **ctx.G})
