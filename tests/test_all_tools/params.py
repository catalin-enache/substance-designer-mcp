"""set_params: value types, $outputsize / $format / $randomseed and their inheritance, refusals; and
the Designer facts about inheritance and seeds those checks rely on."""

import re

from .common import GRAPH_OF, INHERIT, PIXELS, TEST_GRAPH, Ctx, added_id, check, text


async def run(ctx: Ctx) -> None:
    c, G, clouds, slope, lv = ctx.c, ctx.G, ctx.clouds, ctx.slope, ctx.lv
    t = text(await c('set_params', {'node_id': slope, 'params': {'Samples': 16, 'Intensity': 8.0}, **G}))
    check('set_params', 'int + float', '-> 16' in t and '-> 8.0' in t, t)
    t = text(await c('set_params', {'node_id': lv, 'params': {'levelinlow': [0.3] * 4}, **G}))
    check('set_params', 'float4', '(0.3, 0.3, 0.3, 0.3)' in t, t)
    # 10, not the 9 the graph was made with, so the check sees a change (REVIEW.md TST-60)
    t = text(await c('set_params', {'node_id': 'graph', 'params': {'$outputsize': [10, 10]}, **G}))
    check('set_params', 'graph $outputsize', '-> (10, 10)' in t, t)
    await c('set_params', {'node_id': 'graph', 'params': {'$outputsize': [9, 9]}, **G})
    # a node's $outputsize: made Absolute and taking effect (AGENTS.md, Graph size; TST-60)
    t = text(await c('set_params', {'node_id': lv, 'params': {'$outputsize': [7, 7]}, **G}))
    inherit = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
    size = text(await c('node_stats', {'node_id': lv, **G}))
    check(
        'set_params',
        "a node's $outputsize is made Absolute and takes effect",
        'INHERIT=Absolute' in inherit and 'x: 7, y: 7' in inherit and '128x128' in size,
        inherit.strip() + ' | ' + size.splitlines()[0] if size else inherit,
    )
    await c(
        'execute_designer_code',
        {
            'code': INHERIT % (TEST_GRAPH, lv)
            + (
                '\nfrom sd.api.sdproperty import SDPropertyInheritanceMethod as IM\n'
                'n.setPropertyInheritanceMethod(p, IM.RelativeToInput)'
            )
        },
    )  # back as it was (its value resets)
    # on an overridable graph it is refused (it would quietly make the size fixed), pointing
    # to set_graph_size, and the graph stays overridable (REVIEW.md HLP-22)
    await c('set_graph_size', {'size_log2': 9, 'overridable': True, **G})
    r_ = await c('set_params', {'node_id': 'graph', 'params': {'$outputsize': [10, 10]}, **G})
    still = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + (
                    'from sd.api.sdproperty import SDPropertyCategory\n'
                    "p = g.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
                    "print('INHERIT=' + str(g.getPropertyInheritanceMethod(p)).split('.')[-1])"
                )
            },
        )
    )
    check(
        'set_params',
        'graph $outputsize on an overridable graph: refused, still overridable',
        r_.is_error and 'set_graph_size' in text(r_) and 'INHERIT=RelativeToParent' in still,
        text(r_).strip()[-120:] + ' | ' + still.strip(),
    )
    await c('set_graph_size', {'size_log2': 9, 'overridable': False, **G})
    # the graph's other $ parameters follow its parent too, and a value set while they do
    # changes nothing, so set_params makes them Absolute (REVIEW.md HLP-24); measured on a
    # generator that inherits the graph's format
    FORMAT_OF = GRAPH_OF % TEST_GRAPH + (
        'from sd.api.sdproperty import SDPropertyCategory\n'
        'from sd.api.sdvalueenum import SDValueEnum\n'
        "p = g.getPropertyFromId('$format', SDPropertyCategory.Input)\n"
        '%s\n'
        "u = g.newNode('sbs::compositing::uniform'); o = g.newNode('sbs::compositing::output')\n"
        "u.newPropertyConnectionFromId('unique_filter_output', o, 'inputNodeOutput')\n"
        'try:\n    g.compute()\n'
        "    t = u.getPropertyValue(u.getPropertyFromId('unique_filter_output', SDPropertyCategory.Output)).get()\n"
        "    print('FORMAT=' + str(t.getPixelFormat()).split('.')[-1])\n"
        'finally:\n    g.deleteNode(u); g.deleteNode(o)\n'  # no stray output if it fails (REVIEW.md TST-49)
        "print('INHERIT=' + str(g.getPropertyInheritanceMethod(p)).split('.')[-1])"
    )
    fact = text(
        await c(
            'execute_designer_code',
            {
                'code': FORMAT_OF
                % ("g.setPropertyValue(p, SDValueEnum.sFromValueId(p.getType().getId(), '16_bits_per_channel'))")
            },
        )
    )
    check(
        'designer facts',
        'an inherited graph $format ignores its value (AGENTS.md)',
        'FORMAT=RGBA8' in fact and 'INHERIT=RelativeToParent' in fact,
        fact.strip(),
    )
    t = text(await c('set_params', {'node_id': 'graph', 'params': {'$format': '16_bits_per_channel'}, **G}))
    fmt16 = text(await c('execute_designer_code', {'code': FORMAT_OF % ''}))
    check(
        'set_params',
        'graph $format takes effect (made Absolute)',
        'FORMAT=RGBA16' in fmt16 and 'INHERIT=Absolute' in fmt16,
        t.strip() + ' | ' + fmt16.strip(),
    )
    # later checks run on a graph like a new one: $format follows its parent again (REVIEW.md TST-35)
    back = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + (
                    'from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n'
                    'from sd.api.sdvalueenum import SDValueEnum\n'
                    "p = g.getPropertyFromId('$format', SDPropertyCategory.Input)\n"
                    "g.setPropertyValue(p, SDValueEnum.sFromValueId(p.getType().getId(), '8_bits_per_channel'))\n"
                    'g.setPropertyInheritanceMethod(p, IM.RelativeToParent)\n'
                    "print('INHERIT=' + str(g.getPropertyInheritanceMethod(p)).split('.')[-1])"
                )
            },
        )
    )
    check(
        'self-test',
        'the graph $format check puts the graph back as it was',
        'INHERIT=RelativeToParent' in back,
        back.strip(),
    )
    # the graph's $randomseed is different: one that follows its parent is exposed in a
    # .sbsar (an Absolute one isn't) and its value still counts, so set_params leaves its
    # inheritance (REVIEW.md HLP-25; sbsar_info checks the exposure further down)
    SEED_OF = (
        GRAPH_OF % TEST_GRAPH
        + PIXELS
        + (
            'from sd.api.sdproperty import SDPropertyCategory\n'
            'from sd.api.sdvalueint import SDValueInt\n'
            "p = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
            "n = g.getNodeFromId('%s'); out = n.getProperties(SDPropertyCategory.Output)[0]\n"
            'def look(seed):\n'
            '    g.setPropertyValue(p, SDValueInt.sNew(seed)); g.compute()\n'
            '    return pixels(n.getPropertyValue(out).get())\n'
            'o = None\n'
            'try:\n'  # no stray output for later checks if a step fails (REVIEW.md TST-38, TST-53)
            "    o = g.newNode('sbs::compositing::output')\n"
            "    n.newPropertyConnectionFromId(out.getId(), o, 'inputNodeOutput')\n"
            '    looks = [look(s) for s in (0, 3, 3)]\n'
            'finally:\n'
            '    if o is not None:\n        g.deleteNode(o)\n'
            "print('DIFFERS=%%s REPEATS=%%s INHERIT=%%s' %% (apart(looks[0], looks[1]) > 8, apart(looks[1], looks[2]) <= 8, "
            "str(g.getPropertyInheritanceMethod(p)).split('.')[-1]))"
        )
        % clouds
    )
    fact = text(await c('execute_designer_code', {'code': SEED_OF}))
    check(
        'designer facts',
        "an inherited graph $randomseed's value changes the output (AGENTS.md)",
        'DIFFERS=True REPEATS=True INHERIT=RelativeToParent' in fact,
        fact.strip(),
    )
    # graph.compute() computes what feeds an output node, and in a fresh graph not a node that
    # feeds none (AGENTS.md; REVIEW.md TST-64). In this graph a lone node did come back computed,
    # so the fact is measured in a package of its own
    fact = text(
        await c(
            'execute_designer_code',
            {
                'code': (
                    'import sd\nfrom sd.api.sdproperty import SDPropertyCategory\n'
                    'pm = sd.getContext().getSDApplication().getPackageMgr()\npkg = pm.newUserPackage()\n'
                    'try:\n'
                    '    g = sd.api.sbs.sdsbscompgraph.SDSBSCompGraph.sNew(pkg)\n'
                    '    tex = lambda n: (lambda v: v.get() if v is not None else None)(\n'
                    '        n.getPropertyValue(n.getProperties(SDPropertyCategory.Output)[0]))\n'
                    "    fed = g.newNode('sbs::compositing::uniform'); lone = g.newNode('sbs::compositing::uniform')\n"
                    "    o = g.newNode('sbs::compositing::output')\n"
                    "    fed.newPropertyConnectionFromId('unique_filter_output', o, 'inputNodeOutput')\n"
                    '    g.compute()\n'
                    "    print('ALONE_COMPUTED=%s FED_COMPUTED=%s' % (tex(lone) is not None, tex(fed) is not None))\n"
                    'finally:\n    pm.unloadUserPackage(pkg)'
                )
            },
        )
    )
    check(
        'designer facts',
        'graph.compute() computes what feeds an output, in a fresh graph only that (AGENTS.md)',
        'ALONE_COMPUTED=False FED_COMPUTED=True' in fact,
        fact.strip(),
    )
    # a node's seed: inherited, its value is added to the graph's; Absolute, it no longer follows
    # the graph's seed (nor a .sbsar's), so set_params leaves it inherited (REVIEW.md HLP-27).
    # Pixels compared with a tolerance: two computes of one setting differ by a step or two
    fact = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + PIXELS
                + (
                    'from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n'
                    'from sd.api.sdvalueint import SDValueInt\n'
                    "n = g.getNodeFromId('%s'); out = n.getProperties(SDPropertyCategory.Output)[0]\n"
                    "gp = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                    "np_ = n.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                    'kept = (g.getPropertyValue(gp).get(), n.getPropertyInheritanceMethod(np_), n.getPropertyValue(np_).get())\n'
                    'def look(inherit, graph_seed, node_seed):\n'
                    '    n.setPropertyInheritanceMethod(np_, inherit)\n'
                    '    g.setPropertyValue(gp, SDValueInt.sNew(graph_seed)); n.setPropertyValue(np_, SDValueInt.sNew(node_seed))\n'
                    '    g.compute(); return pixels(n.getPropertyValue(out).get())\n'
                    'o = None\n'
                    'try:\n'  # the output node inside the try too (REVIEW.md TST-53)
                    "    o = g.newNode('sbs::compositing::output')\n"
                    "    n.newPropertyConnectionFromId(out.getId(), o, 'inputNodeOutput')\n"
                    '    r03 = look(IM.RelativeToParent, 0, 3)\n'
                    '    near = max(apart(r03, look(IM.RelativeToParent, 3, 0)), apart(r03, look(IM.RelativeToParent, 1, 2)))\n'
                    '    counts = apart(r03, look(IM.RelativeToParent, 0, 0))\n'
                    '    a0 = look(IM.Absolute, 0, 0)\n'
                    '    follows = apart(a0, look(IM.Absolute, 3, 0))\n'
                    'finally:\n'
                    '    if o is not None:\n        g.deleteNode(o)\n'
                    '    n.setPropertyInheritanceMethod(np_, kept[1]); n.setPropertyValue(np_, SDValueInt.sNew(kept[2]))\n'
                    '    g.setPropertyValue(gp, SDValueInt.sNew(kept[0]))\n'
                    "print('ADDED_WITHIN=%%d VALUE_COUNTS_BY=%%d ABSOLUTE_MOVES_WITH_GRAPH_BY=%%d' %% (near, counts, follows))"
                )
                % clouds
            },
        )
    )
    m = re.search(r'ADDED_WITHIN=(\d+) VALUE_COUNTS_BY=(\d+) ABSOLUTE_MOVES_WITH_GRAPH_BY=(\d+)', fact)
    check(
        'designer facts',
        "a node's $randomseed: inherited it's added to the graph's; Absolute it no longer follows it (AGENTS.md)",
        m is not None and int(m.group(1)) <= 8 and int(m.group(2)) > 8 and int(m.group(3)) <= 8,
        fact.strip(),
    )
    t = text(await c('set_params', {'node_id': clouds, 'params': {'$randomseed': 7}, **G}))
    still = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + (
                    "from sd.api.sdproperty import SDPropertyCategory\nn = g.getNodeFromId('%s')\n"
                    "p = n.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                    "print('INHERIT=%%s VALUE=%%s' %% (n.getPropertyInheritanceMethod(p).name, n.getPropertyValue(p).get()))"
                )
                % clouds
            },
        )
    )
    check(
        'set_params',
        "a node's $randomseed keeps following the graph's",
        'INHERIT=RelativeToParent VALUE=7' in still,
        t.strip() + ' | ' + still.strip(),
    )
    # and one already Absolute stays Absolute, on a node and on the graph: set_params never
    # changes a seed's inheritance (AGENTS.md; REVIEW.md HLP-29, TST-57)
    SEED_INHERIT = GRAPH_OF % TEST_GRAPH + (
        'from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n'
        'from sd.api.sdvalueint import SDValueInt\n'
        "n = %s; p = n.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
        "%s\nprint('INHERIT=%%s VALUE=%%s' %% (n.getPropertyInheritanceMethod(p).name, n.getPropertyValue(p).get()))"
    )
    for target, node_id in (("g.getNodeFromId('%s')" % clouds, clouds), ('g', 'graph')):
        kept = re.search(
            r'VALUE=(-?\d+)', text(await c('execute_designer_code', {'code': SEED_INHERIT % (target, '')}))
        )
        await c(
            'execute_designer_code', {'code': SEED_INHERIT % (target, 'n.setPropertyInheritanceMethod(p, IM.Absolute)')}
        )
        t = text(await c('set_params', {'node_id': node_id, 'params': {'$randomseed': 4}, **G}))
        still = text(await c('execute_designer_code', {'code': SEED_INHERIT % (target, '')}))
        check(
            'set_params',
            'an Absolute $randomseed stays Absolute (%s)' % ('node' if node_id != 'graph' else 'graph'),
            'INHERIT=Absolute VALUE=4' in still,
            t.strip() + ' | ' + still.strip(),
        )
        # back as it was: inherited, then the value (changing the inheritance resets it)
        await c(
            'execute_designer_code',
            {
                'code': SEED_INHERIT
                % (
                    target,
                    (
                        'n.setPropertyInheritanceMethod(p, IM.RelativeToParent); n.setPropertyValue(p, SDValueInt.sNew(%s))'
                        % (kept.group(1) if kept else 0)
                    ),
                )
            },
        )
    await c('set_params', {'node_id': clouds, 'params': {'$randomseed': 0}, **G})
    # 5: a value SEED_OF never set, so the check sees set_params write it (REVIEW.md TST-37)
    t = text(await c('set_params', {'node_id': 'graph', 'params': {'$randomseed': 5}, **G}))
    still = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + (
                    'from sd.api.sdproperty import SDPropertyCategory\n'
                    "p = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                    "print('INHERIT=%s VALUE=%s' % (str(g.getPropertyInheritanceMethod(p)).split('.')[-1], g.getPropertyValue(p).get()))"
                )
            },
        )
    )
    check(
        'set_params',
        'graph $randomseed keeps following its parent (stays exposed)',
        'INHERIT=RelativeToParent VALUE=5' in still,
        t.strip() + ' | ' + still.strip(),
    )
    r_ = await c('set_params', {'node_id': lv, 'params': {'levelinlow': [1, 2]}, **G})
    check('set_params', 'error on bad length', r_.is_error and 'expects 4' in text(r_), text(r_))
    before = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
    r_ = await c('set_params', {'node_id': lv, 'params': {'$outputsize': 11}, **G})
    after = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
    check(
        'set_params',
        'rejected value changes nothing (not even inheritance)',
        r_.is_error and 'expects 2' in text(r_) and 'INHERIT=' in before and before == after,
        before + after,
    )
    # every value is checked before any is set (REVIEW.md HLP-1): levelinlow stays at 0.3
    r_ = await c('set_params', {'node_id': lv, 'params': {'levelinlow': [0.6] * 4, 'levelinhigh': [1, 2]}, **G})
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + (
                    "from sd.api.sdproperty import SDPropertyCategory\nn=g.getNodeFromId('%s')\n"
                    "print('LOW=%%.2f' %% n.getPropertyValue(n.getPropertyFromId('levelinlow', SDPropertyCategory.Input)).get().x)"
                )
                % lv
            },
        )
    )
    check(
        'set_params',
        'a bad later value changes nothing',
        r_.is_error and 'expects 4' in text(r_) and 'LOW=0.30' in t,
        text(r_)[-120:] + ' / ' + t.strip(),
    )
    r_ = await c('set_params', {'node_id': slope, 'params': {'Samples': 16.5}, **G})
    check('set_params', 'error on a fractional integer', r_.is_error and 'not a whole number' in text(r_), text(r_))
    tmp_u = added_id(text(await c('add_node', {'definition': 'uniform', **G})))
    r_ = await c('set_params', {'node_id': tmp_u, 'params': {'outputcolor': [1, 0.5]}, **G})
    check('set_params', 'error on a 2-value colour', r_.is_error and 'expects a colour' in text(r_), text(r_))
    t = text(await c('set_params', {'node_id': tmp_u, 'params': {'colorswitch': 'false'}, **G}))
    check('set_params', "bool from the string 'false'", '-> False' in t, t)
    await c('delete_nodes', {'node_ids': [tmp_u], **G})
