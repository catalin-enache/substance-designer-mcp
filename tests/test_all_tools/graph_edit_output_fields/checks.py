"""Naming and tagging output nodes with apply_edits, on a graph of their own."""

import os
import re
from textwrap import dedent

from test_all_tools.common import TEST_GRAPH, Ctx, check, text


async def run(ctx: Ctx) -> None:
    """Names and tags output nodes with apply_edits, on a graph of its own."""
    c, scratch = ctx.c, ctx.scratch
    name = TEST_GRAPH + '_outputs'
    G = {'graph': name}
    sbs = os.path.join(scratch, name + '.sbs')
    await c('create_graph', {'name': name, 'save_path': sbs, 'size_log2': 4})
    t = text(
        await c(
            'apply_edits',
            {
                'ops': [
                    {'op': 'add', 'definition': 'uniform', 'ref': 'u'},
                    {
                        'op': 'add',
                        'definition': 'output',
                        'ref': 'o',
                        'identifier': 'base',
                        'label': 'Base Colour',
                        'usage': 'basecolor',
                    },
                    {'op': 'connect', 'from': 'u', 'to': 'o', 'input': 'inputNodeOutput'},
                    {'op': 'add', 'definition': 'output', 'ref': 'p', 'position': [0, 300]},
                    {'op': 'connect', 'from': 'u', 'to': 'p', 'input': 'inputNodeOutput'},
                ],
                **G,
            },
        )
    )
    o_id, p_id = re.search(r"ref 'o' = (\d+)", t), re.search(r"ref 'p' = (\d+)", t)
    check(
        'apply_edits',
        'add: an output named and tagged, with no warning about renaming',
        bool(o_id and p_id) and 'applied 5 op' in t and 'Tell the user' not in t,
        t,
    )
    first, second = o_id.group(1) if o_id else '', p_id.group(1) if p_id else ''
    described = text(await c('describe_graph', G))
    check(
        'describe_graph',
        "shows an output's identifier, label and usage",
        "identifier='base' label='Base Colour' usage=baseColor" in described and 'usage=none' in described,
        described,
    )
    t = text(
        await c(
            'apply_edits', {'ops': [{'op': 'set', 'node': second, 'identifier': 'rough', 'usage': 'roughness'}], **G}
        )
    )
    described = text(await c('describe_graph', G))
    check(
        'apply_edits',
        'set: an existing output renamed and tagged, and the result says to tell the user',
        "identifier='rough' usage=roughness" in described and "Tell the user: output 'output' was renamed 'rough'" in t,
        t,
    )
    t = text(await c('apply_edits', {'ops': [{'op': 'set', 'node': second, 'identifier': 'rough'}], **G}))
    check('apply_edits', 'set: the name it already has, no warning', 'Tell the user' not in t, t)

    nodes_before = len(re.findall(r'^\d+ ', described, re.M))
    for what, ops, said in [
        (
            "add: another output's identifier",
            [{'op': 'add', 'definition': 'output', 'identifier': 'BASE'}],
            'already has',
        ),
        ("set: another output's identifier", [{'op': 'set', 'node': second, 'identifier': 'base'}], 'already has'),
        ('add: a file path as identifier', [{'op': 'add', 'definition': 'output', 'identifier': '../x'}], 'file name'),
        (
            'add: an identifier on another node',
            [{'op': 'add', 'definition': 'levels', 'identifier': 'x'}],
            'only an output',
        ),
    ]:
        r_ = await c('apply_edits', {'ops': ops, **G})
        after = text(await c('describe_graph', G))
        check(
            'apply_edits',
            what + ' is refused, nothing added or changed',
            r_.is_error
            and said in text(r_)
            and len(re.findall(r'^\d+ ', after, re.M)) == nodes_before
            and "identifier='rough'" in after,
            text(r_),
        )

    exported = os.path.join(scratch, 'output_fields')
    t = text(await c('export_outputs', {'output_dir': exported, **G}))
    names = sorted(os.listdir(exported)) if os.path.isdir(exported) else []
    check('export_outputs', 'files take the identifiers an op gave', names == ['base.png', 'rough.png'], t)

    await c('save_package', {'graph_or_path': sbs})
    with open(sbs, encoding='utf-8') as f:
        saved = f.read()
    check(
        'apply_edits',
        "an output's tag reaches the file, with its colour space",
        re.search(r'<usage><components v="RGBA"/><name v="baseColor"/><colorspace v="sRGB"/></usage>', saved)
        is not None,
        saved[:200],
    )
    await c(
        'apply_edits',
        {'ops': [{'op': 'set', 'node': first, 'identifier': 'albedo', 'label': 'Albedo', 'usage': 'diffuse'}], **G},
    )
    t = text(await c('diff_graph', {'against': 'saved', **G}))
    check(
        'diff_graph',
        'shows an output renamed, relabelled and retagged',
        all(
            '~ node %s output: %s' % (first, change) in t
            for change in (
                'identifier base -> albedo',
                'label Base Colour -> Albedo',
                'usage baseColor (RGBA, sRGB) -> diffuse (RGBA, sRGB)',
            )
        ),
        t,
    )

    # by a ref added in the same batch: the run has to find the new node, as the pre-check only reasons about it
    t = text(
        await c(
            'apply_edits',
            {
                'ops': [
                    {'op': 'add', 'definition': 'output', 'ref': 'q', 'position': [0, 600]},
                    {'op': 'set', 'node': 'q', 'identifier': 'by_ref', 'label': 'Bâse', 'usage': '$matte'},
                    {'op': 'set', 'node': 'q', 'label': ''},
                ],
                **G,
            },
        )
    )
    described = text(await c('describe_graph', G))
    check(
        'apply_edits',
        'set: by a ref of the same batch, $ usages kept, an empty label clears, no warning about renaming',
        "identifier='by_ref' usage=$matte" in described and 'Tell the user' not in t,
        t + described,
    )
    t = text(await c('apply_edits', {'ops': [{'op': 'set', 'node': second, 'label': 'Bâse'}], **G}))
    described = text(await c('describe_graph', G))
    check('apply_edits', 'set: a label outside ASCII is kept', "label='Bâse'" in described, t + described)

    # another node that exists: the pre-check reads its definition, on a fake only until here
    library = re.search(
        r"ref 'l' = (\d+)",
        text(
            await c(
                'apply_edits', {'ops': [{'op': 'add', 'definition': 'clouds_2', 'ref': 'l', 'position': [0, 900]}], **G}
            )
        ),
    )
    uniform = re.search(r'^(\d+) uniform ', described, re.M)
    for what, node in (('an atomic node', uniform), ('a library node', library)):
        r_ = await c(
            'apply_edits', {'ops': [{'op': 'set', 'node': node.group(1) if node else '?', 'identifier': 'x'}], **G}
        )
        check(
            'apply_edits',
            'set: an identifier on %s is refused' % what,
            r_.is_error and 'only an output' in text(r_),
            text(r_),
        )

    # one name twice in a batch: refused when the op runs, so the first stays, and the error says what was added
    r_ = await c(
        'apply_edits',
        {
            'ops': [
                {'op': 'add', 'definition': 'output', 'ref': 'd1', 'identifier': 'twice', 'position': [300, 600]},
                {'op': 'add', 'definition': 'output', 'ref': 'd2', 'identifier': 'Twice', 'position': [300, 900]},
            ],
            **G,
        },
    )
    described = text(await c('describe_graph', G))
    check(
        'apply_edits',
        'add: one name twice in a batch stops at the second, and says the first was added',
        r_.is_error
        and 'already has' in text(r_)
        and 'ops 0-0 were applied' in text(r_)
        and "(ref 'd1')" in text(r_)
        and described.count("identifier='twice'") == 1
        and "identifier='Twice'" not in described,
        text(r_),
    )

    # closed: the one edit left unsaved goes with it
    await c(
        'execute_designer_code',
        {
            'code': dedent("""\
                import sd
                pm = sd.getContext().getSDApplication().getPackageMgr()
                for p in list(pm.getUserPackages()):
                    if any(r.getIdentifier() == %r for r in p.getChildrenResources(False)):
                        pm.unloadUserPackage(p)""")
            % name,
            'undo_label': 'self-test: close the outputs graph',
        },
    )
