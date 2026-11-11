"""What bitmaps' checks read: the self-test graph, empty (its checks add the bitmap nodes themselves)."""

from test_all_tools.common import TEST_GRAPH, Ctx, prepared_call


async def prepare(ctx: Ctx) -> None:
    c = ctx.c
    await prepared_call(c, 'create_graph', {'name': TEST_GRAPH, 'size_log2': 9})
    ctx.G = {'graph': TEST_GRAPH}
