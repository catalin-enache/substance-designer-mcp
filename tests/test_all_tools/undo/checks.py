"""One tool call = one undo step (acts only while the self-test graph is in the editor). Each Undo and Redo is sent
through Designer's Edit menu and read back with describe_graph until the graph shows it (edit_menu.py); one that fails
says why, and an Undo that fired and never showed is followed by a Redo putting back the step it hit."""

import re
from textwrap import dedent

from test_all_tools.common import TEST_GRAPH, Ctx, added_id, check, designer_script, text
from test_all_tools.undo.edit_menu import (
    fields_back,
    nodes_gone,
    nodes_listed,
    put_back,
    read_left_armed,
    recorded,
    send,
)


async def run(ctx: Ctx) -> None:
    # in a pool it runs last, alone (categories.SOLO: beside the others its Undo failed)
    try:
        await check_one_undo_removes_an_added_node(ctx)
        await check_one_undo_puts_an_outputs_fields_back(ctx)
        await check_one_undo_reverts_a_whole_code_run(ctx)
    finally:  # after the last clean-up, or a check that raised before its send read the action (REVIEW.md TST-690)
        await read_left_armed(ctx.c)


async def check_one_undo_removes_an_added_node(ctx: Ctx) -> None:
    """apply_edits' add is one undo step: one Undo removes the node it added, and Redo restores it. The node is deleted
    after it."""
    c, G = ctx.c, ctx.G
    ub = added_id(
        text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [0, 400]}], **G}))
    )
    undo = await send(c, G, 'Undo', nodes_gone(ub))
    if recorded(undo, 'apply_edits', 'add: one Undo removes the added node'):
        recorded(await send(c, G, 'Redo', nodes_listed(ub)), 'apply_edits', 'add: Redo restores it')
    await put_back(c, G, undo)
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': ub}], **G})


async def check_one_undo_puts_an_outputs_fields_back(ctx: Ctx) -> None:
    """apply_edits' set of an output's identifier, label and usage is one undo step: one Undo puts the three back. An
    output's annotations aren't parameters, so nothing else shows that Undo reaches them. Each state is read, so a
    refused set can't pass here by Undo reverting something else. The output is as prepared again after it
    (undo/designer_scripts/as_prepared.py)."""
    c, G = ctx.c, ctx.G
    changed = "identifier='undo_me' label='Undo' usage=roughness"
    name = "set: one Undo puts an output's fields back"
    await c(
        'apply_edits',
        {'ops': [{'op': 'set', 'node': ctx.out, 'identifier': 'undo_me', 'label': 'Undo', 'usage': 'roughness'}], **G},
    )
    was_set = changed in text(await c('describe_graph', G))
    check('apply_edits', "set: an output's fields, before the Undo", was_set, '')
    if was_set:
        undo = await send(c, G, 'Undo', fields_back)
        recorded(undo, 'apply_edits', name)
        await put_back(c, G, undo)
    else:
        check('apply_edits', name, False, "no Undo sent: the set wasn't applied")
    await designer_script(c, 'undo/as_prepared', graph=TEST_GRAPH, node=ctx.out)


async def check_one_undo_reverts_a_whole_code_run(ctx: Ctx) -> None:
    """execute_designer_code's run is one undo step: one Undo removes both nodes a run added, and Redo restores them.
    The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    t = text(
        await c(
            'execute_designer_code',
            {
                'undo_label': 'self-test: two nodes',
                'code': (
                    dedent("""\
                        import sd
                        from sd.api.sdbasetypes import float2
                        g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]
                        ids=[]
                        for i in range(2):
                            n=g.newNode('sbs::compositing::blur'); n.setPosition(float2(200*i, 500)); ids.append(n.getIdentifier())
                        print('IDS=' + ','.join(ids))""")
                )
                % TEST_GRAPH,
            },
        )
    )
    # no match raises AttributeError, which the run's except reports (REVIEW.md TST-63)
    two = re.search(r'IDS=(\d+),(\d+)', t).groups()  # type: ignore[union-attr]
    tool = 'execute_designer_code'
    undo = await send(c, G, 'Undo', nodes_gone(*two))
    if recorded(undo, tool, 'one Undo reverts the whole run'):
        recorded(await send(c, G, 'Redo', nodes_listed(*two)), tool, 'one Redo restores it')
    await put_back(c, G, undo)
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in list(two)], **G})
