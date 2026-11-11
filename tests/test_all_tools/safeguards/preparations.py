"""What safeguards' checks read: the self-test graph with a clouds_2 instance (a `scale` to sweep; adding it loads
the library package noise_clouds_2.sbs, which the library refusals need) and a levels node (an $outputsize to sweep),
and bevel.sbs loaded (a library graph refused by name, where the run started Designer)."""

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
                    {'op': 'add', 'definition': 'levels', 'ref': 'lv', 'position': [0, 0]},
                ],
                **ctx.G,
            },
        )
    )
    ctx.clouds = added['clouds']
    ctx.lv = added['lv']
    await prepared_call(c, 'describe_node', {'definition': 'bevel'})  # loads bevel.sbs, and leaves it loaded
