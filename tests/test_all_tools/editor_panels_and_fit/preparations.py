"""What editor_panels_and_fit's checks read: the self-test graph in the editor (no Home screen; the selection is read
from its view), with nodes spread apart and a frame around two of them: fitting the view to one item must leave a node
out of view, and fitting the whole graph must show every frame whole."""

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
                ],
                **ctx.G,
            },
        )
    )
    ctx.clouds = added['clouds']
    ctx.slope = added['slope']
    await prepared_call(c, 'add_frame', {'node_ids': [ctx.clouds, ctx.slope], 'title': 'Shape', **ctx.G})
    await prepared_call(c, 'open_graph', {'graph': TEST_GRAPH})
