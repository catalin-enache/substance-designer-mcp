"""What undo's checks read: the self-test graph, in the editor and focused (Undo acts on the document in focus: its
checks skip otherwise), with an output identified `height`, no label, no usage (one Undo must bring those fields
back)."""

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
                    {'op': 'add', 'definition': 'output', 'ref': 'out', 'position': [300, 0], 'identifier': 'height'},
                ],
                **ctx.G,
            },
        )
    )
    ctx.out = added['out']
    await prepared_call(c, 'open_graph', {'graph': TEST_GRAPH})
