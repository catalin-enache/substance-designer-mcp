"""What measure's checks read: the self-test graph at 512 px with a clouds_2 instance (a `scale` to sweep, set to 4, not
its default, so a sweep putting the default back shows; a tileable output), a levels node computing at least 64 px
(unconnected, relative to the graph) with an $outputsize to sweep, and a slope blur fed by the clouds, to view a sweep
on."""

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
                    {
                        'op': 'add',
                        'definition': 'noise_clouds_2.sbs/clouds_2',
                        'ref': 'clouds',
                        'position': [-600, 0],
                        'params': {'scale': 4},
                    },
                    {
                        'op': 'add',
                        'definition': 'slope_blur.sbs/slope_blur_grayscale_2',
                        'ref': 'slope',
                        'position': [-300, 0],
                    },
                    {'op': 'add', 'definition': 'levels', 'ref': 'lv', 'position': [0, 0]},
                    {'op': 'connect', 'from': 'clouds', 'to': 'slope', 'input': 'Source'},
                ],
                **ctx.G,
            },
        )
    )
    ctx.clouds = added['clouds']
    ctx.slope = added['slope']
    ctx.lv = added['lv']
