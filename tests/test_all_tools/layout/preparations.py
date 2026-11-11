"""What layout's checks read: the self-test graph, never saved (a snapshot of an unsaved package gets a UID of its
own), with clouds_2 -> slope blur -> levels -> output connected (arrange_graph orders them by the flow), every
parameter at its default (levelinhigh 1.0, which a check changes and puts back), no frame and no comment."""

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
                    {'op': 'add', 'definition': 'output', 'ref': 'out', 'position': [300, 0]},
                    {'op': 'connect', 'from': 'clouds', 'to': 'slope', 'input': 'Source'},
                    {'op': 'connect', 'from': 'slope', 'to': 'lv', 'input': 'input1'},
                    {'op': 'connect', 'from': 'lv', 'to': 'out', 'input': 'inputNodeOutput'},
                ],
                **ctx.G,
            },
        )
    )
    ctx.clouds = added['clouds']
    ctx.slope = added['slope']
    ctx.lv = added['lv']
    ctx.out = added['out']
