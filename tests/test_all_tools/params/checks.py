"""apply_edits' set op: value types, $outputsize / $format / $randomseed and their inheritance, refusals; and
the Designer facts about inheritance and seeds those checks rely on."""

import re
from textwrap import dedent

from test_all_tools.common import GRAPH_OF, TEST_GRAPH, Ctx, added_id, check, designer_script, text


async def run(ctx: Ctx) -> None:
    c, G, clouds, slope, lv = ctx.c, ctx.G, ctx.clouds, ctx.slope, ctx.lv
    t = text(
        await c(
            'apply_edits', {'ops': [{'op': 'set', 'node': slope, 'params': {'Samples': 16, 'Intensity': 8.0}}], **G}
        )
    )
    check('apply_edits', 'set: int + float', '-> 16' in t and '-> 8.0' in t, t)
    t = text(await c('apply_edits', {'ops': [{'op': 'set', 'node': lv, 'params': {'levelinlow': [0.3] * 4}}], **G}))
    check('apply_edits', 'set: float4', '(0.3, 0.3, 0.3, 0.3)' in t, t)
    # 10, not the 9 the graph was made with, so the check sees a change (REVIEW.md TST-60)
    t = text(
        await c('apply_edits', {'ops': [{'op': 'set', 'node': 'graph', 'params': {'$outputsize': [10, 10]}}], **G})
    )
    check('apply_edits', 'set: graph $outputsize', '-> (10, 10)' in t, t)
    await c('apply_edits', {'ops': [{'op': 'set', 'node': 'graph', 'params': {'$outputsize': [9, 9]}}], **G})
    # a node's $outputsize: made Absolute and taking effect (GUIDE.md, Graph size; TST-60)
    t = text(await c('apply_edits', {'ops': [{'op': 'set', 'node': lv, 'params': {'$outputsize': [7, 7]}}], **G}))
    inherit = text(await designer_script(c, 'shared/node_size_inheritance', graph=TEST_GRAPH, node=lv))
    size = text(await c('node_stats', {'node_id': lv, **G}))
    check(
        'apply_edits',
        "set: a node's $outputsize is made Absolute and takes effect",
        'INHERIT=Absolute' in inherit and 'x: 7, y: 7' in inherit and '128x128' in size,
        inherit.strip() + ' | ' + size.splitlines()[0] if size else inherit,
    )
    await designer_script(
        c, 'shared/node_size_inheritance', graph=TEST_GRAPH, node=lv, relative_to_input=True
    )  # back as it was (its value resets)
    # on an overridable graph it is refused (it would quietly make the size fixed), pointing
    # to set_graph_size, and the graph stays overridable (REVIEW.md HLP-22)
    await c('set_graph_size', {'size_log2': 9, 'overridable': True, **G})
    r_ = await c('apply_edits', {'ops': [{'op': 'set', 'node': 'graph', 'params': {'$outputsize': [10, 10]}}], **G})
    still = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + dedent("""\
                    from sd.api.sdproperty import SDPropertyCategory
                    p = g.getPropertyFromId('$outputsize', SDPropertyCategory.Input)
                    print('INHERIT=' + str(g.getPropertyInheritanceMethod(p)).split('.')[-1])""")
            },
        )
    )
    check(
        'apply_edits',
        'set: graph $outputsize on an overridable graph: refused, still overridable',
        r_.is_error and 'set_graph_size' in text(r_) and 'INHERIT=RelativeToParent' in still,
        text(r_).strip()[-120:] + ' | ' + still.strip(),
    )
    await c('set_graph_size', {'size_log2': 9, 'overridable': False, **G})
    # the graph's other $ parameters follow its parent too, and a value set while they do
    # changes nothing, so the set op makes them Absolute (REVIEW.md HLP-24); measured on a
    # generator that inherits the graph's format
    fact = text(await designer_script(c, 'params/graph_format', graph=TEST_GRAPH, set_16_bits=True))
    check(
        'designer facts',
        'an inherited graph $format ignores its value (GUIDE.md)',
        'FORMAT=RGBA8' in fact and 'INHERIT=RelativeToParent' in fact,
        fact.strip(),
    )
    t = text(
        await c(
            'apply_edits', {'ops': [{'op': 'set', 'node': 'graph', 'params': {'$format': '16_bits_per_channel'}}], **G}
        )
    )
    fmt16 = text(await designer_script(c, 'params/graph_format', graph=TEST_GRAPH))
    check(
        'apply_edits',
        'set: graph $format takes effect (made Absolute)',
        'FORMAT=RGBA16' in fmt16 and 'INHERIT=Absolute' in fmt16,
        t.strip() + ' | ' + fmt16.strip(),
    )
    # later checks run on a graph like a new one: $format follows its parent again (REVIEW.md TST-35)
    back = text(await designer_script(c, 'params/graph_format_restore', graph=TEST_GRAPH))
    check(
        'self-test',
        'the graph $format check puts the graph back as it was',
        'INHERIT=RelativeToParent' in back,
        back.strip(),
    )
    # the graph's $randomseed is different: one that follows its parent is exposed in a
    # .sbsar (an Absolute one isn't) and its value still counts, so the set op leaves its
    # inheritance (REVIEW.md HLP-25; sbsar_info checks the exposure: render/checks.py)
    fact = text(await designer_script(c, 'params/graph_seed_effect', graph=TEST_GRAPH, node=clouds))
    check(
        'designer facts',
        "an inherited graph $randomseed's value changes the output (GUIDE.md)",
        'DIFFERS=True REPEATS=True INHERIT=RelativeToParent' in fact,
        fact.strip(),
    )
    # graph.compute() computes what feeds an output node, and in a fresh graph not a node that
    # feeds none (GUIDE.md; REVIEW.md TST-64). In this graph a lone node did come back computed,
    # so the fact is measured in a package of its own
    fact = text(await designer_script(c, 'params/compute_fresh_graph'))
    check(
        'designer facts',
        'graph.compute() computes what feeds an output, in a fresh graph only that (GUIDE.md)',
        'ALONE_COMPUTED=False FED_COMPUTED=True' in fact,
        fact.strip(),
    )
    # a node's seed: inherited, its value is added to the graph's; Absolute, it no longer follows
    # the graph's seed (nor a .sbsar's), so the set op leaves it inherited (REVIEW.md HLP-27).
    # Pixels compared with a tolerance: two computes of one setting differ by a step or two
    fact = text(await designer_script(c, 'params/node_seed', graph=TEST_GRAPH, node=clouds))
    m = re.search(r'ADDED_WITHIN=(\d+) VALUE_COUNTS_BY=(\d+) ABSOLUTE_MOVES_WITH_GRAPH_BY=(\d+)', fact)
    check(
        'designer facts',
        "a node's $randomseed: inherited it's added to the graph's; Absolute it no longer follows it (GUIDE.md)",
        m is not None and int(m.group(1)) <= 8 and int(m.group(2)) > 8 and int(m.group(3)) <= 8,
        fact.strip(),
    )
    t = text(await c('apply_edits', {'ops': [{'op': 'set', 'node': clouds, 'params': {'$randomseed': 7}}], **G}))
    still = text(await designer_script(c, 'params/seed_state', graph=TEST_GRAPH, node=clouds))
    check(
        'apply_edits',
        "set: a node's $randomseed keeps following the graph's",
        'INHERIT=RelativeToParent VALUE=7' in still,
        t.strip() + ' | ' + still.strip(),
    )
    # and one already Absolute stays Absolute, on a node and on the graph: the set op never
    # changes a seed's inheritance (GUIDE.md; REVIEW.md HLP-29, TST-57)
    for seed_node, node_id in ((clouds, clouds), ('', 'graph')):
        kept = re.search(
            r'VALUE=(-?\d+)', text(await designer_script(c, 'params/seed_state', graph=TEST_GRAPH, node=seed_node))
        )
        await designer_script(c, 'params/seed_state', graph=TEST_GRAPH, node=seed_node, absolute=True)
        t = text(await c('apply_edits', {'ops': [{'op': 'set', 'node': node_id, 'params': {'$randomseed': 4}}], **G}))
        still = text(await designer_script(c, 'params/seed_state', graph=TEST_GRAPH, node=seed_node))
        check(
            'apply_edits',
            'set: an Absolute $randomseed stays Absolute (%s)' % ('node' if node_id != 'graph' else 'graph'),
            'INHERIT=Absolute VALUE=4' in still,
            t.strip() + ' | ' + still.strip(),
        )
        # back as it was: inherited, then the value (changing the inheritance resets it)
        await designer_script(
            c, 'params/seed_state', graph=TEST_GRAPH, node=seed_node, restore=int(kept.group(1)) if kept else 0
        )
    await c('apply_edits', {'ops': [{'op': 'set', 'node': clouds, 'params': {'$randomseed': 0}}], **G})
    # 5: a value params/graph_seed_effect.py never set, so the check sees the set op write it (REVIEW.md TST-37)
    t = text(await c('apply_edits', {'ops': [{'op': 'set', 'node': 'graph', 'params': {'$randomseed': 5}}], **G}))
    still = text(await designer_script(c, 'params/seed_state', graph=TEST_GRAPH))
    check(
        'apply_edits',
        'set: graph $randomseed keeps following its parent (stays exposed)',
        'INHERIT=RelativeToParent VALUE=5' in still,
        t.strip() + ' | ' + still.strip(),
    )
    r_ = await c('apply_edits', {'ops': [{'op': 'set', 'node': lv, 'params': {'levelinlow': [1, 2]}}], **G})
    check('apply_edits', 'set: error on bad length', r_.is_error and 'expects 4' in text(r_), text(r_))
    before = text(await designer_script(c, 'shared/node_size_inheritance', graph=TEST_GRAPH, node=lv))
    r_ = await c('apply_edits', {'ops': [{'op': 'set', 'node': lv, 'params': {'$outputsize': 11}}], **G})
    after = text(await designer_script(c, 'shared/node_size_inheritance', graph=TEST_GRAPH, node=lv))
    check(
        'apply_edits',
        'set: rejected value changes nothing (not even inheritance)',
        r_.is_error and 'expects 2' in text(r_) and 'INHERIT=' in before and before == after,
        before + after,
    )
    # every value is checked before any is set (REVIEW.md HLP-1): levelinlow stays at 0.3
    r_ = await c(
        'apply_edits',
        {'ops': [{'op': 'set', 'node': lv, 'params': {'levelinlow': [0.6] * 4, 'levelinhigh': [1, 2]}}], **G},
    )
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + dedent("""\
                    from sd.api.sdproperty import SDPropertyCategory
                    n = g.getNodeFromId(%r)
                    print('LOW=%%.2f' %% n.getPropertyValue(n.getPropertyFromId('levelinlow', SDPropertyCategory.Input)).get().x)""")
                % lv
            },
        )
    )
    check(
        'apply_edits',
        'set: a bad later value changes nothing',
        r_.is_error and 'expects 4' in text(r_) and 'LOW=0.30' in t,
        text(r_)[-120:] + ' / ' + t.strip(),
    )
    r_ = await c('apply_edits', {'ops': [{'op': 'set', 'node': slope, 'params': {'Samples': 16.5}}], **G})
    check(
        'apply_edits', 'set: error on a fractional integer', r_.is_error and 'not a whole number' in text(r_), text(r_)
    )
    tmp_u = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'uniform'}], **G})))
    r_ = await c('apply_edits', {'ops': [{'op': 'set', 'node': tmp_u, 'params': {'outputcolor': [1, 0.5]}}], **G})
    check('apply_edits', 'set: error on a 2-value colour', r_.is_error and 'expects a colour' in text(r_), text(r_))
    t = text(await c('apply_edits', {'ops': [{'op': 'set', 'node': tmp_u, 'params': {'colorswitch': 'false'}}], **G}))
    check('apply_edits', "set: bool from the string 'false'", '-> False' in t, t)
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': tmp_u}], **G})
