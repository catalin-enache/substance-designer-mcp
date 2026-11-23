"""apply_edits' set op: value types, $outputsize / $format / $randomseed and their inheritance, refusals; and
the Designer facts about inheritance and seeds those checks rely on. Then a Gradient Map's keys and a Curve's points
(ROADMAP item 116): the facts they rely on, set, read back, computed, refused, swept and not exposed."""

import re
from textwrap import dedent

from project_constants import Json
from test_all_tools.common import (
    CLOSE,
    GRAPH_OF,
    TEST_GRAPH,
    Ctx,
    Ops,
    ToolArgs,
    added_id,
    check,
    described,
    designer_script,
    expect,
    near,
    text,
)
from test_all_tools.params.readings import (
    ALL_RED,
    BANDS,
    CURVES,
    GREY_INVERTED,
    GREY_RAMP,
    RAMP,
    RED_TO_BLUE,
    as_json,
    band_values,
    colour_ramp,
    read_back,
)


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
    await check_gradient_and_curve_keys(ctx)
    await check_describe_node_shows_a_new_nodes_keys(ctx)
    await check_set_gradient_keys(ctx)
    await check_set_curve_points(ctx)
    await check_key_refusals_leave_the_graph_unchanged(ctx)
    await check_sweep_over_gradient_keys(ctx)
    await check_expose_refuses_gradient_keys(ctx)
    await check_set_an_empty_list_removes_every_key(ctx)
    await check_describe_graph_shows_every_key_of_a_node_it_focuses_on(ctx)


CURVE_KEY = (
    'SDTypeArray<sbs::compositing::curve_key>: position float2, isLocked bool, left float2, isLeftBroken bool, '
    'right float2, isRightBroken bool'
)
UNSORTED = 'value (0, 0, 1, 1) position 1 midpoint 0.5; value (1, 0, 0, 1) position 0 midpoint 0.25'
EASED = 'LUM32F 0.000 0.064 0.204 0.434 0.796 0.936 1.000'  # (0, 0) right handle (0.5, 0), (1, 1) left (0.5, 1)
FIRST_RIGHT_BROKEN = 'LUM32F 0.000 0.340 0.527 0.687 0.870 0.951 1.000'  # that ease, the first right handle unused
SECOND_LEFT_BROKEN = 'LUM32F 0.000 0.049 0.130 0.245 0.473 0.660 1.000'  # that ease, the second left handle unused
# the channels (0 for R up to 3 for A) each of a Curve's arrays acts on, on a colour input
CHANNELS = {'curveluminance': (0, 1, 2), 'curvered': (0,), 'curvegreen': (1,), 'curveblue': (2,), 'curvealpha': (3,)}


async def check_gradient_and_curve_keys(ctx: Ctx) -> None:
    """What set's keys rely on (params/designer_scripts/keys.py, which says how it reads them): their types; a new node
    has no keys and its arrays no default, and a new key's handles are at (0, 0); setPropertyValue takes any array and
    keeps the keys in the order given, and a value read is a copy, as is the one set; what keys compute on a grey ramp
    in 32-bit float, a curve key's flags included; and the keys after a save and a reload (GUIDE.md, Gradient Map keys
    and Curve points)."""
    c = ctx.c
    t = text(await designer_script(c, 'params/keys'))
    expect(
        t,
        'gradient and curve keys',
        {
            'gradientrgba': 'SDTypeArray<sbs::compositing::gradient_key_rgba>: value ColorRGBA, position float, '
            'midpoint float',
            **dict.fromkeys(CURVES, CURVE_KEY),
            'a new gradient': 'gradientrgba none, default None | interpmode int 0 | smoothness float 0.5',
            'a new curve': ' | '.join('%s none, default None' % pid for pid in CURVES),
            'a new sbs::compositing::gradient_key_rgba': 'value (0, 0, 0, 1) position 0 midpoint 0',
            'a new sbs::compositing::curve_key': 'position (0, 0) isLocked False left (0, 0) isLeftBroken False '
            'right (0, 0) isRightBroken False',
            'two keys set unsorted, read back': UNSORTED,
            'a value read, after a set': UNSORTED,
            'that value set again': UNSORTED,
            'a value read, changed': 'the node reads ' + UNSORTED,
            'the array set, changed after': 'the node reads value (1, 0, 0, 1) position 0 midpoint 0',
            # Designer converts an array of another item type, raising nothing: set builds the parameter's own
            'an array of curve_key set on gradientrgba': 'reads value (0, 0, 0, 1) position 0 midpoint 0',
            'an array of float set on gradientrgba': 'reads none',
            'an empty array set on a gradient with a key': 'reads none',
            "a curve's flags set, read back": 'reads position (0, 0) isLocked True left (0, 0) isLeftBroken False '
            'right (0.5, 0) isRightBroken True; position (1, 1) isLocked False left (0.5, 1) isLeftBroken True '
            'right (1, 1) isRightBroken False',
            # no keys: the input, as a grey colour; one key: its colour everywhere
            'gradient, no keys': 'RGBA32F ' + ' '.join('%s/%s/%s/1.000' % (v, v, v) for v in RAMP),
            'gradient, one key, red at 0.5': ALL_RED,
            # sorted by position, each key's colour exact at its position
            'gradient, red at 0, green at 1/3, blue at 1, given blue, red, green': 'RGBA32F 1.000/0.000/0.000/1.000 '
            '0.400/0.600/0.000/1.000 0.000/1.000/0.000/1.000 0.000/0.800/0.200/1.000 0.000/0.500/0.500/1.000 '
            '0.000/0.300/0.700/1.000 0.000/0.000/1.000/1.000',
            # two keys at one position: the first listed is used, the other never shows
            'gradient, red then green at 0.4, blue at 1': 'RGBA32F 1.000/0.000/0.000/1.000 1.000/0.000/0.000/1.000 '
            '1.000/0.000/0.000/1.000 0.889/0.000/0.111/1.000 0.556/0.000/0.444/1.000 0.333/0.000/0.667/1.000 '
            '0.000/0.000/1.000/1.000',
            'gradient, green then red at 0.4, blue at 1': 'RGBA32F 0.000/1.000/0.000/1.000 0.000/1.000/0.000/1.000 '
            '0.000/1.000/0.000/1.000 0.000/0.889/0.111/1.000 0.000/0.556/0.444/1.000 0.000/0.333/0.667/1.000 '
            '0.000/0.000/1.000/1.000',
            # outside the keys, the nearest key's colour
            'gradient, red at 0.2, blue at 0.8': 'RGBA32F 1.000/0.000/0.000/1.000 1.000/0.000/0.000/1.000 '
            '0.778/0.000/0.222/1.000 0.556/0.000/0.444/1.000 0.222/0.000/0.778/1.000 0.000/0.000/1.000/1.000 '
            '0.000/0.000/1.000/1.000',
            'gradient, red at 0, blue at 1': RED_TO_BLUE,
            # at interpmode 0, the default, a midpoint changes nothing; at 1 it does; 3 holds each key's colour
            **{'gradient, red at 0, blue at 1, midpoints %s' % m: RED_TO_BLUE for m in ('0.25', '0.5', '1')},
            'gradient, red at 0, blue at 1, interpmode 1, midpoints 0': 'RGBA32F 1.000/0.000/0.000/1.000 '
            '0.896/0.000/0.104/1.000 0.741/0.000/0.259/1.000 0.550/0.000/0.450/1.000 0.259/0.000/0.741/1.000 '
            '0.104/0.000/0.896/1.000 0.000/0.000/1.000/1.000',
            'gradient, red at 0, blue at 1, interpmode 1, midpoints 0.5': 'RGBA32F 1.000/0.000/0.000/1.000 '
            '0.960/0.000/0.040/1.000 0.874/0.000/0.126/1.000 0.729/0.000/0.271/1.000 0.417/0.000/0.583/1.000 '
            '0.191/0.000/0.809/1.000 0.000/0.000/1.000/1.000',
            'gradient, red at 0, blue at 1, interpmode 3, midpoints 0': 'RGBA32F '
            + ' '.join(['1.000/0.000/0.000/1.000'] * 6 + ['0.000/0.000/1.000/1.000']),
            # a colour beyond 0..1 is kept, alpha interpolated
            'gradient, (2, -1, 0.5, 0.5) at 0, blue at 1': 'RGBA32F 2.000/-1.000/0.500/0.500 1.600/-0.800/0.600/0.600 '
            '1.333/-0.667/0.667/0.667 1.067/-0.533/0.733/0.733 0.667/-0.333/0.833/0.833 0.400/-0.200/0.900/0.900 '
            '0.000/0.000/1.000/1.000',
            # a key below 0 makes every pixel the last key's colour; one above 1 is taken
            'gradient, red at -0.1, blue at 1.1': 'RGBA32F ' + ' '.join(['0.000/0.000/1.000/1.000'] * 7),
            'gradient, red at 0, blue at 1.5': 'RGBA32F 1.000/0.000/0.000/1.000 0.867/0.000/0.133/1.000 '
            '0.778/0.000/0.222/1.000 0.689/0.000/0.311/1.000 0.556/0.000/0.444/1.000 0.467/0.000/0.533/1.000 '
            '0.333/0.000/0.667/1.000',
            # grayscale: the mean of the colour's R, G and B; a colour input: everywhere the colour of the key at position
            # 0, which is listed first too
            'gradient, red at 0, white at 1, colorswitch off': 'LUM32F 0.333 0.467 0.556 0.644 0.778 0.867 1.000',
            'gradient, red at 0, blue at 1, on the colour ramp': ALL_RED,
            'curve, no keys': GREY_RAMP,
            # a key made from its position alone has its handles at (0, 0), which bend the curve
            'curve, (0, 1) and (1, 0) from their points alone': 'LUM32F 1.000 0.072 0.029 0.011 0.002 0.000 0.000',
            # handles on their points: straight lines, sorted by x
            'curve, (0, 1) and (1, 0), handles on their points': GREY_INVERTED,
            'curve, (1, 0) and (0, 1), handles on their points': GREY_INVERTED,
            # handles are absolute points: an ease in and out. isLocked changes nothing computed; a side marked broken
            # computes as if its handle were on the point: both keys' both sides, the straight line
            'curve, (0, 0) right (0.5, 0), (1, 1) left (0.5, 1)': EASED,
            'curve, (0, 0) right (0.5, 0), (1, 1) left (0.5, 1), locked': EASED,
            'curve, (0, 0) right (0.5, 0), (1, 1) left (0.5, 1), broken': GREY_RAMP,
            # each side on its own: the first point's right handle as if on its point, then the second's left. The first
            # point's left faces no segment: off its point, used or broken, it changes nothing (the two cells below), so
            # both of that point's sides give what its right side gives
            "curve, (0, 0) right (0.5, 0), (1, 1) left (0.5, 1), the first point's right side broken": FIRST_RIGHT_BROKEN,
            "curve, (0, 0) right (0.5, 0), (1, 1) left (0.5, 1), the second point's left side broken": SECOND_LEFT_BROKEN,
            'curve, (0, 0) right (0.5, 0), (1, 1) left (0.5, 1), both sides of the first point broken': FIRST_RIGHT_BROKEN,
            'curve, (0, 0) right on its point, (1, 1) left (0.5, 1)': FIRST_RIGHT_BROKEN,
            'curve, (0, 0) right (0.5, 0), (1, 1) left on its point': SECOND_LEFT_BROKEN,
            'curve, (0, 0) left (0.2, 0.3) right (0.5, 0), (1, 1) left (0.5, 1)': EASED,
            'curve, (0, 0) left (0.2, 0.3) right (0.5, 0), (1, 1) left (0.5, 1), its left side broken': EASED,
            'curve, (0, 0), (0.5, 1), (1, 0) on their points': 'LUM32F 0.000 0.400 0.667 0.933 0.667 0.400 0.000',
            'curve, (0.5, 0.25) alone, on its point': 'LUM32F ' + ' '.join(['0.250'] * 7),
            # two points at one x: a step, each side of it the point given on that side
            'curve, (0, 0), (0.5, 0) then (0.5, 1), (1, 1)': 'LUM32F 0.000 0.000 0.000 0.000 1.000 1.000 1.000',
            'curve, (0, 0), (0.5, 1) then (0.5, 0), (1, 1)': 'LUM32F 0.000 0.400 0.667 0.933 0.333 0.600 1.000',
            'curve, (0, -1) and (1, 2)': 'LUM32F -1.000 -0.400 0.000 0.400 1.000 1.400 2.000',
            'curve, (0.2, 0) and (0.8, 1)': 'LUM32F 0.000 0.000 0.222 0.444 0.778 1.000 1.000',
            # a point below x 0: pixel 0 computes 0, off the line through the points (0.143)
            'curve, (-0.2, 0) and (1.2, 1)': 'LUM32F 0.000 0.286 0.381 0.476 0.619 0.714 0.857',
            # on a grey input only curveluminance acts, the four others not; on a colour one, each array on its
            # channels, and curvered before curveluminance (the order measured with it alone)
            **{'curve, grey ramp, %s inverts' % pid: GREY_RAMP for pid in CURVES if pid != 'curveluminance'},
            **{'curve, colour ramp, %s inverts' % pid: colour_ramp(*CHANNELS[pid]) for pid in CURVES},
            'curve, colour ramp, curveluminance and curvered invert': colour_ramp(1, 2),
            # R is 1 - x / 2: curvered halves it first, then curveluminance inverts it (REVIEW.md TST-781)
            'curve, colour ramp, curveluminance inverts and curvered halves': 'RGBA32F 1.000/1.000/1.000/0.000 '
            '0.900/0.800/0.800/0.200 0.833/0.667/0.667/0.333 0.766/0.533/0.533/0.467 0.667/0.333/0.333/0.667 '
            '0.600/0.200/0.200/0.800 0.500/0.000/0.000/1.000',
            'gradientrgba after a save and a reload': 'as before',
            'curveluminance after a save and a reload': 'as before',
        },
    )


# the keys and points the set checks give, and what describe_graph reads back of them
KEYS: Json = [[0, [1, 0, 0]], [0.5, [0.2, 0.6, 0.2, 1], 0.25], [1, [0, 0, 1, 1]]]
KEYS_READ = '((0.0, (1.0, 0.0, 0.0, 1.0)), (0.5, (0.2, 0.6, 0.2, 1.0), 0.25), (1.0, (0.0, 0.0, 1.0, 1.0)))'
INVERT: Json = [[0, 1], [1, 0]]
INVERT_READ = '((0.0, 1.0), (1.0, 0.0))'
EASE: Json = [[[0, 0], [0, 0], [0.5, 0]], [[1, 1], [0.5, 1], [1, 1]]]
EASE_READ = '(((0.0, 0.0), (0.0, 0.0), (0.5, 0.0)), ((1.0, 1.0), (0.5, 1.0), (1.0, 1.0)))'


async def check_describe_node_shows_a_new_nodes_keys(ctx: Ctx) -> None:
    """describe_node shows a new Gradient Map's and Curve's arrays as the empty list of keys they hold, in the shape set
    takes, each of its array type."""
    c = ctx.c
    for definition, pids in (('gradient', ('gradientrgba',)), ('curve', CURVES)):
        t = text(await c('describe_node', {'definition': definition}))
        shown = [re.search(r'^\s+%s\s+SDTypeArray<\S+>.* default=(.*)$' % pid, t, re.M) for pid in pids]
        defaults = [m.group(1) if m else 'not listed' for m in shown]
        check(
            'describe_node',
            "%s's keys: none, as set takes them" % definition,
            defaults == ['()'] * len(pids),
            str(defaults),
        )


async def check_set_gradient_keys(ctx: Ctx) -> None:
    """set gives a Gradient Map its keys, one with a midpoint: the result and describe_graph(include_params) read them
    back in the shape set takes, the midpoint included, a node with none lists none, set takes that read back again
    unchanged, and the grey ramp through it computes each key's colour on its band, the bands between keys halfway
    (8-bit, so within a step; the midpoint changes nothing at interpmode 0)."""
    c, G, node = ctx.c, ctx.G, ctx.gradient
    before = read_back(await described(ctx, [node]), 'gradientrgba')
    check('apply_edits', 'set: a Gradient Map with no keys lists none', before == '', before)
    t = text(await c('apply_edits', {'ops': [{'op': 'set', 'node': node, 'params': {'gradientrgba': KEYS}}], **G}))
    check('apply_edits', "set: a Gradient Map's keys, its result", '-> %s' % KEYS_READ in t, t)
    shown = read_back(await described(ctx, [node]), 'gradientrgba')
    check('describe_graph', "include_params: a Gradient Map's keys, as set takes them", shown == KEYS_READ, shown)
    t = text(
        await c('apply_edits', {'ops': [{'op': 'set', 'node': node, 'params': {'gradientrgba': as_json(shown)}}], **G})
    )
    check(
        'apply_edits', "set: a Gradient Map's keys read back, set again unchanged", '%s -> %s' % (shown, shown) in t, t
    )
    stats, got = await band_values(ctx, node)
    want: list[list[float]] = [[1, 0, 0, 1], [0.6, 0.3, 0.1, 1], [0.2, 0.6, 0.2, 1], [0.1, 0.3, 0.6, 1], [0, 0, 1, 1]]
    keyed = len(got) == 5 and all(near(g, w) for g, w in zip(got, want, strict=True))
    check('apply_edits', "set: a Gradient Map's keys, computed on the grey ramp", keyed and '512x512' in stats, stats)


async def check_set_curve_points(ctx: Ctx) -> None:
    """set gives a Curve its points: [x, y] alone joined by straight lines (the ramp inverted), handles as absolute
    points (an ease from 0 to 1, below the line at 0.25 and above it at 0.75), each read back in the shape set takes and
    set again unchanged; curvered, which a grey input ignores, is read back too."""
    c, G, node = ctx.c, ctx.G, ctx.curve
    ops: Ops = [{'op': 'set', 'node': node, 'params': {'curveluminance': INVERT, 'curvered': EASE}}]
    t = text(await c('apply_edits', {'ops': ops, **G}))
    check(
        'apply_edits', "set: a Curve's points, its result", '-> %s' % INVERT_READ in t and '-> %s' % EASE_READ in t, t
    )
    d = await described(ctx, [node])
    shown = (read_back(d, 'curveluminance'), read_back(d, 'curvered'))
    check('describe_graph', "include_params: a Curve's points, as set takes them", shown == (INVERT_READ, EASE_READ), d)
    again: Ops = [
        {'op': 'set', 'node': node, 'params': {'curveluminance': as_json(shown[0]), 'curvered': as_json(shown[1])}}
    ]
    t = text(await c('apply_edits', {'ops': again, **G}))
    unchanged = all('%s -> %s' % (points, points) in t for points in shown)
    check('apply_edits', "set: a Curve's points read back, set again unchanged", unchanged, t)
    stats, got = await band_values(ctx, node)
    inverted = len(got) == 5 and all(near(g, [1 - band]) for g, band in zip(got, BANDS, strict=True))
    check('apply_edits', "set: a Curve's points [x, y], computed: straight lines", inverted, stats)
    await c('apply_edits', {'ops': [{'op': 'set', 'node': node, 'params': {'curveluminance': EASE}}], **G})
    _, got = await band_values(ctx, node)
    ease = [values[0] for values in got]
    eased = len(ease) == 5 and ease[0] <= CLOSE and ease[1] < 0.2 and ease[3] > 0.8 and ease[4] >= 1 - CLOSE
    check('apply_edits', "set: a Curve's handles, computed: absolute points", eased, str(ease))


# (what is refused, the params set, what the refusal starts with)
REFUSALS: list[tuple[str, dict[str, Json], str]] = [
    ('not a list', {'gradientrgba': 0.5}, 'gradientrgba takes a list of keys'),
    ('a position above 1', {'gradientrgba': [[0, [1, 0, 0]], [1.5, [0, 0, 1]]]}, 'gradientrgba[1]: position is'),
    ('a colour of 2 numbers', {'gradientrgba': [[0, [1, 0]]]}, 'gradientrgba[0]: colour is'),
    ('a midpoint above 1', {'gradientrgba': [[0, [1, 0, 0], 2]]}, 'gradientrgba[0]: midpoint is'),
    ('a key of 4 items', {'gradientrgba': [[0, [1, 0, 0], 0.5, 1]]}, 'gradientrgba[0]: a key is'),
    ('a point of 1 number', {'curveluminance': [[0, 1], [1]]}, 'curveluminance[1]: a point is'),
    ('an x below 0', {'curveluminance': [[-0.2, 0]]}, 'curveluminance[0]: x is'),
    ('a handle not [x, y]', {'curveluminance': [[[0, 0], [0, 0], [0.5, 'a']]]}, 'curveluminance[0]: the right'),
    ('a good array then a bad one', {'curveluminance': INVERT, 'curvered': [[0, 'y']]}, 'curvered[0]: y is'),
]


async def check_key_refusals_leave_the_graph_unchanged(ctx: Ctx) -> None:
    """Each mistake in keys or points is refused, naming the key, before anything is set: the Gradient Map and the
    Curve, given keys and points first, read back as before, a good array beside a bad one included. The Curve starts
    with EASE in both arrays, so that case's good INVERT, set by a partial set, would show (REVIEW.md TST-767)."""
    c, G = ctx.c, ctx.G
    ops: Ops = [
        {'op': 'set', 'node': ctx.gradient, 'params': {'gradientrgba': KEYS}},
        {'op': 'set', 'node': ctx.curve, 'params': {'curveluminance': EASE, 'curvered': EASE}},
    ]
    await c('apply_edits', {'ops': ops, **G})
    before = await described(ctx, [ctx.gradient, ctx.curve])
    for what, params, said in REFUSALS:
        node = ctx.gradient if 'gradientrgba' in params else ctx.curve
        r_ = await c('apply_edits', {'ops': [{'op': 'set', 'node': node, 'params': params}], **G})
        check('apply_edits', 'set: keys refused, %s' % what, r_.is_error and said in text(r_), text(r_)[-150:])
    after = await described(ctx, [ctx.gradient, ctx.curve])
    held = [read_back(before, pid) for pid in ('gradientrgba', 'curveluminance', 'curvered')] == [
        KEYS_READ,
        EASE_READ,
        EASE_READ,
    ]
    check('apply_edits', 'set: keys refused, the graph unchanged', held and after == before, after)


async def check_set_an_empty_list_removes_every_key(ctx: Ctx) -> None:
    """set of [] removes every key of a Gradient Map and every point of a Curve, given some first: the result says ()
    and describe_graph lists none, as a new node has."""
    c, G = ctx.c, ctx.G
    ops: Ops = [
        {'op': 'set', 'node': ctx.gradient, 'params': {'gradientrgba': KEYS}},
        {'op': 'set', 'node': ctx.curve, 'params': {'curveluminance': INVERT}},
    ]
    await c('apply_edits', {'ops': ops, **G})
    emptied: Ops = [
        {'op': 'set', 'node': ctx.gradient, 'params': {'gradientrgba': []}},
        {'op': 'set', 'node': ctx.curve, 'params': {'curveluminance': []}},
    ]
    t = text(await c('apply_edits', {'ops': emptied, **G}))
    said = '%s -> ()' % KEYS_READ in t and '%s -> ()' % INVERT_READ in t
    d = await described(ctx, [ctx.gradient, ctx.curve])
    listed = read_back(d, 'gradientrgba') + read_back(d, 'curveluminance')
    check('apply_edits', 'set: [] removes every key and point', said and listed == '', t + ' | ' + listed)


async def check_sweep_over_gradient_keys(ctx: Ctx) -> None:
    """sweep_param tries keys, one tile per value, each read back (as JSON gives it, lists), then puts back the keys
    there were (a value read is a copy: the keys facts check): the Gradient Map is given KEYS first, so the keys put
    back are some (REVIEW.md TST-783)."""
    c, G, node = ctx.c, ctx.G, ctx.gradient
    await c('apply_edits', {'ops': [{'op': 'set', 'node': node, 'params': {'gradientrgba': KEYS}}], **G})
    before = read_back(await described(ctx, [node]), 'gradientrgba')
    values: Json = [[[0, [1, 0, 0]], [1, [0, 0, 1]]], [[0, [0, 1, 0]], [1, [1, 1, 1]]]]
    args: ToolArgs = {'node_id': node, 'param': 'gradientrgba', 'values': values, 'tile_size': 64, **G}
    r_ = await c('sweep_param', args)
    t = text(r_)
    after = read_back(await described(ctx, [node]), 'gradientrgba')
    each = [
        'gradientrgba = [[0.0, [1.0, 0.0, 0.0, 1.0]], [1.0, [0.0, 0.0, 1.0, 1.0]]]',
        'gradientrgba = [[0.0, [0.0, 1.0, 0.0, 1.0]], [1.0, [1.0, 1.0, 1.0, 1.0]]]',
    ]
    tried = t.count('gradientrgba = ') == 2 and all(value in t for value in each)
    check(
        'sweep_param',
        'gradient keys: each tried, then put back',
        not r_.is_error and tried and before == KEYS_READ and after == before,
        '%s | before %s, after %s' % (t, before, after),
    )


async def check_expose_refuses_gradient_keys(ctx: Ctx) -> None:
    """An expose op refuses an array parameter: no function can drive it (REVIEW.md HLP-244), and no graph input is
    made."""
    c, G = ctx.c, ctx.G
    ops: Ops = [{'op': 'expose', 'node': ctx.gradient, 'param': 'gradientrgba'}]
    r_ = await c('apply_edits', {'ops': ops, **G})
    try:
        inputs = text(await c('list_graph_inputs', G))
        refused = r_.is_error and 'cannot be exposed' in text(r_) and 'gradientrgba' not in inputs
        check('apply_edits', 'expose: gradient keys refused, no input made', refused, text(r_)[-150:] + ' | ' + inputs)
    finally:
        if not r_.is_error:  # an expose taken would leave its input driving gradientrgba for the checks after
            await c('remove_graph_input', {'input_id': 'gradientrgba', **G})


async def check_describe_graph_shows_every_key_of_a_node_it_focuses_on(ctx: Ctx) -> None:
    """describe_graph(include_params) shows a parameter of more than 16 keys as their count in a whole graph's listing,
    and every key when node_ids focuses on its node. The Gradient Map added for it is deleted after it."""
    c, G = ctx.c, ctx.G
    ramp = [i / 16 for i in range(17)]  # each key's position, and its grey
    many: Json = [[v, [v, v, v]] for v in ramp]
    ops: Ops = [{'op': 'add', 'definition': 'gradient', 'position': [0, 700], 'params': {'gradientrgba': many}}]
    node = added_id(text(await c('apply_edits', {'ops': ops, **G})))
    try:
        whole = text(await c('describe_graph', {'include_params': True, **G}))
        check(
            'describe_graph',
            'include_params: 17 keys in a whole graph, their count',
            "'<17 keys>'" in whole,
            whole[-150:],
        )
        focused = read_back(await described(ctx, [node]), 'gradientrgba')
        every = '%r' % (tuple((v, (v, v, v, 1.0)) for v in ramp),)
        check(
            'describe_graph',
            'include_params: 17 keys of a node focused on, every one',
            focused == every,
            focused[-150:],
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': node}], **G})
