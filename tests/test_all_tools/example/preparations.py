"""What example's checks read: a graph named mcp_selftest, any content, to switch the editor to off the trim sheet."""

from test_all_tools.common import TEST_GRAPH, Ctx, prepared_call


async def prepare(ctx: Ctx) -> None:
    c = ctx.c
    await prepared_call(c, 'create_graph', {'name': TEST_GRAPH, 'size_log2': 9})
    ctx.G = {'graph': TEST_GRAPH}
