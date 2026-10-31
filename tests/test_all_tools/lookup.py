"""Graph lookup (same-named graphs, library graphs) and a node with several outputs (bevel)."""

from .common import DUP_GRAPH, Ctx, added_id, check, image_size, is_image, text


async def run(ctx: Ctx) -> None:
    c, G, clouds, png = ctx.c, ctx.G, ctx.clouds, ctx.png
    # --- graph lookup: same-named graphs are ambiguous; loaded library graphs aren't yours
    await c(
        'execute_designer_code',
        {
            'code': (
                'import sd\nfrom sd.api.sbs.sdsbscompgraph import SDSBSCompGraph\n'
                'pm=sd.getContext().getSDApplication().getPackageMgr()\n'
                "for _ in range(2):\n    SDSBSCompGraph.sNew(pm.newUserPackage()).setIdentifier('%s')"
            )
            % DUP_GRAPH
        },
    )
    r_ = await c('describe_graph', {'graph': DUP_GRAPH})
    check(
        'describe_graph',
        'error on two graphs with one name',
        r_.is_error and '2 open graphs are named' in text(r_),
        text(r_),
    )
    r_ = await c('describe_graph', {'graph': 'bevel'})  # bevel.sbs is loaded by now (describe_node)
    check('describe_graph', 'library graphs are not user graphs', r_.is_error and 'not found' in text(r_), text(r_))

    # --- a node with several outputs (bevel: height, normal)
    bev = added_id(
        text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'bevel', 'position': [-400, 300]}], **G}))
    )
    await c('apply_edits', {'ops': [{'op': 'connect', 'from': clouds, 'to': bev, 'input': 'input'}], **G})
    lvn = added_id(
        text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels', 'position': [-200, 300]}], **G}))
    )
    t = text(
        await c(
            'apply_edits',
            {'ops': [{'op': 'connect', 'from': bev, 'to': lvn, 'input': 'input1', 'output': 'normal'}], **G},
        )
    )
    t2 = text(await c('describe_graph', {'node_ids': [lvn], **G}))
    check('apply_edits', "connect: 'output' picks the output", 'input1<-%s.normal' % bev in t2, t2)
    r_ = await c('preview_node', {'node_id': bev, 'output': 'normal', 'max_size': 128, **G})
    check(
        'preview_node',
        'output + max_size',
        is_image(r_) and max(image_size(r_)) <= 128,
        str(image_size(r_)) if is_image(r_) else text(r_),
    )
    t = text(await c('node_stats', {'node_id': bev, 'output': 'normal', **G}))
    check(
        'node_stats', 'output picks the output', '%s instance:bevel.normal' % bev in t and 'B:' in t, t.splitlines()[0]
    )
    t = text(await c('check_tiling', {'node_id': bev, 'output': 'height', 'axis': 'horizontal', **G}))
    check('check_tiling', 'output + one axis', '.height' in t and 'Horizontal' in t and 'Vertical' not in t, t)
    r_ = await c(
        'sweep_param',
        {
            'node_id': clouds,
            'param': 'scale',
            'values': [2, 8],
            'view_node': bev,
            'output': 'normal',
            'tile_size': 64,
            **G,
        },
    )
    t = text(r_)
    check(
        'sweep_param',
        'view_node + output',
        'restored %s.scale' % clouds in t and t.count('scale = ') == 2 and any(x.type == 'image' for x in r_.content),
        t,
    )
    per_value = [l.split(': ', 1)[1] for l in t.splitlines() if l.startswith('scale = ')]
    check(
        'sweep_param',
        'a node feeding no output is recomputed per value',
        len(per_value) == 2 and per_value[0] != per_value[1],
        str(per_value),
    )
    r_ = await c(
        'compare_to_reference',
        {
            'node_id': bev,
            'output': 'normal',
            'reference_path': png,
            'reference_region': [0, 0, 32, 16],
            'tile_size': 128,
            **G,
        },
    )
    t = text(r_)
    check(
        'compare_to_reference',
        'output + reference_region',
        '.normal' in t.splitlines()[0] and '(32x16)' in t.splitlines()[0],
        t.splitlines()[0],
    )
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': bev}, {'op': 'delete', 'node': lvn}], **G})
