"""One tool call = one undo step. Each Undo and Redo is triggered only while the self-test graph is in the editor, and
while the top step of its dropdown is named as the check's call names its step (edit_menu.send). Each is sent through
Designer's Edit menu and read back with describe_graph until the graph shows it (edit_menu.py); one that fails says
why, and an Undo that fired and never showed is followed by a Redo putting back the step it hit."""

import re
from textwrap import dedent

from test_all_tools.common import TEST_GRAPH, Ctx, Ops, ToolArgs, added_id, check, designer_script, refs, text
from test_all_tools.undo.edit_menu import (
    fields_back,
    function_graph_nodes,
    input_values,
    nodes_gone,
    nodes_listed,
    perpixel_driver,
    put_back,
    read_left_armed,
    recorded,
    send,
)

# the labels the tools give the steps of the checks' calls (server_tools/edits.py, functions.py): each Undo and Redo
# is sent for its call's label (edit_menu.send)
ONE_EDIT, TWO_EDITS = 'Claude: apply 1 edits', 'Claude: apply 2 edits'
FUNCTION_LABEL = 'Claude: set function graph undo_fn'  # each set_function on the function graph undo_fn


async def run(ctx: Ctx) -> None:
    # in a pool it runs last, alone (categories.SOLO: beside the others its Undo failed)
    try:
        await check_one_undo_removes_an_added_node(ctx)
        await check_one_undo_puts_an_outputs_fields_back(ctx)
        await check_one_undo_reverts_a_whole_code_run(ctx)
        await check_one_undo_reverts_a_set_function(ctx)
        await check_one_undo_reverts_a_function_graph(ctx)
        await check_one_undo_reverts_a_set_of_gradient_keys(ctx)
        await check_one_undo_reverts_a_connect_into_a_new_input_value(ctx)
    finally:  # after the last clean-up, or a check that raised before its send read the action (REVIEW.md TST-690)
        await read_left_armed(ctx.c)


async def check_one_undo_removes_an_added_node(ctx: Ctx) -> None:
    """apply_edits' add is one undo step: one Undo removes the node it added, and Redo restores it. The node is deleted
    after it."""
    c, G = ctx.c, ctx.G
    ub = added_id(
        text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [0, 400]}], **G}))
    )
    undo = await send(c, G, 'Undo', nodes_gone(ub), ONE_EDIT)
    if recorded(undo, 'apply_edits', 'add: one Undo removes the added node'):
        recorded(await send(c, G, 'Redo', nodes_listed(ub), ONE_EDIT), 'apply_edits', 'add: Redo restores it')
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
        undo = await send(c, G, 'Undo', fields_back, ONE_EDIT)
        recorded(undo, 'apply_edits', name)
        await put_back(c, G, undo)
    else:
        check('apply_edits', name, False, "no Undo sent: the set wasn't applied")
    await designer_script(c, 'undo/as_prepared', graph=TEST_GRAPH, node=ctx.out)


async def check_one_undo_reverts_a_whole_code_run(ctx: Ctx) -> None:
    """execute_designer_code's run is one undo step: one Undo removes both nodes a run added, and Redo restores them.
    The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    label = 'self-test: two nodes'
    t = text(
        await c(
            'execute_designer_code',
            {
                'undo_label': label,
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
    undo = await send(c, G, 'Undo', nodes_gone(*two), label)
    if recorded(undo, tool, 'one Undo reverts the whole run'):
        recorded(await send(c, G, 'Redo', nodes_listed(*two), label), tool, 'one Redo restores it')
    await put_back(c, G, undo)
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in list(two)], **G})


# what describe_graph says drives the Pixel Processor's perpixel: the function before, $time read alone, then the new one
BEFORE, NEW = "a function reading '$time'", 'a function'


async def check_one_undo_reverts_a_set_function(ctx: Ctx) -> None:
    """set_function's replacement of a function is one undo step: one Undo brings back the function before, whole, the
    node kept, and Redo the new one. describe_graph tells them apart: the one before is one get node, its output,
    reading $time (BEFORE); the new one is several (NEW). An Undo reverting only part of the replacement leaves more
    nodes, or no output. The node is deleted after it."""
    c, G = ctx.c, ctx.G
    added = text(
        await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'pixelprocessor', 'position': [0, 600]}], **G})
    )
    pp = added_id(added)
    tool = 'set_function'
    await c('set_function', {'expression': '$time', 'node_id': pp, **G})
    await c('set_function', {'expression': 'float4($pos, 0, 1)', 'node_id': pp, **G})
    described: ToolArgs = {**G, 'node_ids': [pp], 'include_params': True}
    replaced = perpixel_driver(text(await c('describe_graph', described))) == NEW
    check(tool, 'a function replaced, before the Undo', replaced, '')
    if replaced:
        label = 'Claude: set function of %s.perpixel' % pp
        undo = await send(c, described, 'Undo', lambda d: nodes_listed(pp)(d) and perpixel_driver(d) == BEFORE, label)
        if recorded(undo, tool, 'one Undo brings back the function before, the node kept'):
            redo = await send(c, described, 'Redo', lambda d: perpixel_driver(d) == NEW, label)
            recorded(redo, tool, 'Redo brings back the new one')
        await put_back(c, described, undo)
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': pp}], **G})


async def check_one_undo_reverts_a_connect_into_a_new_input_value(ctx: Ctx) -> None:
    """apply_edits' connect into a #name the node lacks is one undo step: one Undo removes the connection and the
    input value #u it made, and Redo brings both back. describe_graph shows the connection; set_function's refusal of
    a #name the node lacks lists its input values. The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    ops: Ops = [
        {'op': 'add', 'definition': 'valueprocessor', 'ref': 'vp', 'position': [0, 800]},
        {'op': 'add', 'definition': 'blend', 'ref': 'bl', 'position': [200, 800]},
    ]
    added = refs(text(await c('apply_edits', {'ops': ops, **G})))
    vp, bl = added['vp'], added['bl']
    tool = 'apply_edits'
    link = '#u<-%s.unique_filter_output' % vp
    described: ToolArgs = {**G, 'node_ids': [bl]}
    try:
        await c('apply_edits', {'ops': [{'op': 'connect', 'from': vp, 'to': bl, 'input': '#u'}], **G})
        linked = link in text(await c('describe_graph', described))
        made = await input_values(c, G, bl)
        connected = linked and made == '#u'
        check(tool, 'connect into a new #name, before the Undo', connected, made)
        if connected:
            undo = await send(c, described, 'Undo', lambda d: nodes_listed(bl)(d) and link not in d, ONE_EDIT)
            if recorded(undo, tool, 'connect into a new #name: one Undo removes the connection'):
                left = await input_values(c, G, bl)
                check(tool, 'connect into a new #name: one Undo removes the #name it made', left == '', left)
                redo = await send(c, described, 'Redo', lambda d: link in d, ONE_EDIT)
                if recorded(redo, tool, 'connect into a new #name: Redo brings the connection back'):
                    back = await input_values(c, G, bl)
                    check(tool, 'connect into a new #name: Redo brings the #name back', back == '#u', back)
            await put_back(c, described, undo)
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})


# what describe_graph of the self-test graph says of undo_fn among its package's function graphs: made with the input k,
# given m too. UNDO_FN starts both: without it, the package has none
ONE_INPUT, TWO_INPUTS, UNDO_FN = 'undo_fn(k float) -> float', 'undo_fn(k float, m float) -> float', 'undo_fn('
# undo_fn's nodes, as edit_menu.function_graph_nodes reads them: none, k * 0.5's, k + m's (REVIEW.md TST-740)
NO_NODES, MADE_NODES, REPLACED_NODES = 'none', '3 nodes, output mul', '3 nodes, output add'


def nodes_are(name: str, said: str, want: str) -> None:
    """Checks `name`: the nodes function_graph_nodes `said` are `want`."""
    check('set_function', name, said == want, said[-150:])


async def check_one_undo_reverts_a_function_graph(ctx: Ctx) -> None:
    """set_function's `function` is one undo step (REVIEW.md TST-735): one Undo removes the function graph undo_fn it
    made, and Redo brings it back; given the input m too, one Undo brings back its inputs and nodes before, and Redo
    the new ones. describe_graph of the self-test graph names the package's function graphs with their inputs, which
    each Undo and Redo is read with. Once each has shown, describe_graph's `function` reads undo_fn's nodes
    (edit_menu.function_graph_nodes; REVIEW.md TST-740). undo_fn stays in the package, which the clean-up unloads."""
    c, G = ctx.c, ctx.G
    tool = 'set_function'

    async def nodes() -> str:
        return await function_graph_nodes(c, G, 'undo_fn')

    await c('set_function', {'expression': 'k * 0.5', 'function': 'undo_fn', 'inputs': {'k': 'float'}, **G})
    said = text(await c('describe_graph', G))
    made = ONE_INPUT in said
    check(tool, 'a function graph made, before the Undo', made, said[-150:])
    if made:
        undo = await send(c, G, 'Undo', lambda d: UNDO_FN not in d, FUNCTION_LABEL)
        if recorded(undo, tool, 'a function graph made: one Undo removes it'):
            nodes_are('a function graph made: one Undo removes its nodes too', await nodes(), NO_NODES)
            redo = await send(c, G, 'Redo', lambda d: ONE_INPUT in d, FUNCTION_LABEL)
            if recorded(redo, tool, 'a function graph made: Redo brings it back'):
                nodes_are('a function graph made: Redo brings back its nodes too', await nodes(), MADE_NODES)
        await put_back(c, G, undo)
    inputs = {'k': 'float', 'm': 'float'}
    await c('set_function', {'expression': 'k + m', 'function': 'undo_fn', 'inputs': inputs, **G})
    said = text(await c('describe_graph', G))
    replaced = TWO_INPUTS in said
    check(tool, 'a function graph given another input, before the Undo', replaced, said[-150:])
    if replaced:
        undo = await send(c, G, 'Undo', lambda d: ONE_INPUT in d, FUNCTION_LABEL)
        if recorded(undo, tool, 'a function graph given another input: one Undo brings back its inputs before'):
            before = 'a function graph given another input: one Undo brings back its nodes before too'
            nodes_are(before, await nodes(), MADE_NODES)
            redo = await send(c, G, 'Redo', lambda d: TWO_INPUTS in d, FUNCTION_LABEL)
            if recorded(redo, tool, 'a function graph given another input: Redo brings back the new ones'):
                new = 'a function graph given another input: Redo brings back the new nodes too'
                nodes_are(new, await nodes(), REPLACED_NODES)
        await put_back(c, G, undo)


# what describe_graph(include_params) reads of the Gradient Map's keys and the Curve's points the keys check sets: as
# added, then as the set changes them
KEYS_BEFORE = 'gradientrgba = ((0.0, (1.0, 0.0, 0.0, 1.0)), (1.0, (0.0, 0.0, 1.0, 1.0)))'
POINTS_BEFORE = 'curveluminance = ((0.0, 1.0), (1.0, 0.0))'
KEYS_AFTER = 'gradientrgba = ((0.0, (0.0, 1.0, 0.0, 1.0)), (0.5, (1.0, 1.0, 1.0, 1.0)), (1.0, (0.0, 0.0, 0.0, 1.0)))'
POINTS_AFTER = 'curveluminance = ((0.0, 0.0), (1.0, 1.0))'


async def check_one_undo_reverts_a_set_of_gradient_keys(ctx: Ctx) -> None:
    """apply_edits' set of a Gradient Map's keys and of a Curve's points, two set ops of one call, is one undo step: one
    Undo brings back the keys and the points the add gave, and Redo the new ones. describe_graph(include_params) reads
    both. The nodes are deleted after it."""
    c, G = ctx.c, ctx.G
    ops: Ops = [
        {
            'op': 'add',
            'definition': 'gradient',
            'ref': 'gm',
            'position': [0, 1000],
            'params': {'gradientrgba': [[0, [1, 0, 0]], [1, [0, 0, 1]]]},
        },
        {
            'op': 'add',
            'definition': 'curve',
            'ref': 'cv',
            'position': [200, 1000],
            'params': {'curveluminance': [[0, 1], [1, 0]]},
        },
    ]
    t = text(await c('apply_edits', {'ops': ops, **G}))
    added = refs(t)
    tool = 'apply_edits'
    try:
        if not {'gm', 'cv'} <= set(added):  # an add refused its keys: no node is left for it
            check(tool, 'set of keys and points, before the Undo', False, t[-150:])
            return
        gm, cv = added['gm'], added['cv']
        described: ToolArgs = {**G, 'node_ids': [gm, cv], 'include_params': True}
        changes: Ops = [
            {'op': 'set', 'node': gm, 'params': {'gradientrgba': [[0, [0, 1, 0]], [0.5, [1, 1, 1]], [1, [0, 0, 0]]]}},
            {'op': 'set', 'node': cv, 'params': {'curveluminance': [[0, 0], [1, 1]]}},
        ]
        await c('apply_edits', {'ops': changes, **G})
        said = text(await c('describe_graph', described))
        changed = KEYS_AFTER in said and POINTS_AFTER in said
        check(tool, 'set of keys and points, before the Undo', changed, said[-150:])
        if changed:
            undo = await send(c, described, 'Undo', lambda d: KEYS_BEFORE in d and POINTS_BEFORE in d, TWO_EDITS)
            if recorded(undo, tool, 'set: one Undo brings back the keys and points before'):
                redo = await send(c, described, 'Redo', lambda d: KEYS_AFTER in d and POINTS_AFTER in d, TWO_EDITS)
                recorded(redo, tool, 'set: Redo brings back the new keys and points')
            await put_back(c, described, undo)
    finally:
        if added:
            await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in added.values()], **G})
