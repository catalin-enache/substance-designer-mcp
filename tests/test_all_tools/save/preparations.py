"""What save's checks read: the self-test graph, never saved, with a clouds_2 instance to move, and a PNG on disk to
copy in as a bitmap."""

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
                    {'op': 'add', 'definition': 'noise_clouds_2.sbs/clouds_2', 'ref': 'clouds', 'position': [-600, 0]},
                ],
                **ctx.G,
            },
        )
    )
    ctx.clouds = added['clouds']
