"""Exposed inputs and graph size: set_graph_size, apply_edits' expose op, list_graph_inputs,
remove_graph_input, and parameters driven by functions."""

import os
import re
from textwrap import dedent
from typing import Any

from .common import GRAPH_OF, TEST_GRAPH, Ctx, added_id, check, designer_script, helpers_source, text


async def run(ctx: Ctx) -> None:
    c, G, slope, lv = ctx.c, ctx.G, ctx.slope, ctx.lv
    # --- exposed inputs and graph size
    t = text(await c('set_graph_size', {'size_log2': 9, 'overridable': True, **G}))
    check('set_graph_size', 'overridable 512', 'overridable, default 512 px' in t, t)
    await c('snapshot_graph', {'label': 'overridable size', **G})
    t = text(await c('set_graph_size', {'size_log2': 9, 'overridable': False, **G}))
    check('set_graph_size', 'fixed 512', 'size: fixed' in t, t)
    t = text(await c('diff_graph', {'against': 'overridable size', **G}))
    check(
        'diff_graph',
        'size labels (fixed is absolute)',
        '~ graph outputsize: (default: relative to parent) -> 9 9 (absolute)' in t,
        t,
    )
    await c('set_graph_size', {'size_log2': 9, 'overridable': True, **G})  # render checks need it
    t = text(
        await c(
            'apply_edits',
            {
                'ops': [
                    {
                        'op': 'expose',
                        'node': lv,
                        'param': 'leveloutlow',
                        'input_id': 'floor',
                        'label': 'Floor',
                        'default': [0.25] * 4,
                        'min': 0,
                        'max': 1,
                    }
                ],
                **G,
            },
        )
    )
    check('apply_edits', 'expose: float4 with range', "graph input 'floor'" in t, t)
    t = text(await c('apply_edits', {'ops': [{'op': 'expose', 'node': slope, 'param': 'Samples'}], **G}))
    check('apply_edits', 'expose: int, defaults to current value', "'Samples'" in t and 'default 16' in t, t)
    # a failure after the function graph was created leaves no function graph behind
    # (REVIEW.md HLP-3): the getter for float4 renamed to a type that doesn't exist
    helpers_src = helpers_source()
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helpers_src
                + (
                    dedent("""
                        set_params(%r, %r, {'levelinhigh': [0.8] * 4})
                        _GETTERS['float4'] = 'get_no_such_type'
                        try:
                            expose_param(%r, %r, 'levelinhigh', input_id='broken')
                        except (Exception, APIException) as e:
                            print('FAILED', type(e).__name__)
                        g = find_graph(%r); n = g.getNodeFromId(%r)
                        p = n.getPropertyFromId('levelinhigh', SDPropertyCategory.Input)
                        print('LEFT_GRAPH=%%s LEFT_INPUT=%%s VALUE=%%.2f' %% (n.getPropertyGraph(p) is not None, g.getPropertyFromId('broken', SDPropertyCategory.Input) is not None, n.getPropertyValue(p).get().x))
                        set_params(%r, %r, {'levelinhigh': [1.0] * 4})""")
                )
                % (TEST_GRAPH, lv, TEST_GRAPH, lv, TEST_GRAPH, lv, TEST_GRAPH, lv)
            },
        )
    )
    # ...and the parameter keeps the value it had (adding the graph reset it; REVIEW.md HLP-21)
    check(
        'apply_edits',
        'expose: a failure midway leaves nothing behind',
        'FAILED' in t and 'LEFT_GRAPH=False LEFT_INPUT=False VALUE=0.80' in t,
        t.strip()[-160:],
    )
    # and when the parameter already had an empty function graph, which is reused, a
    # failure leaves no half-made get node in it (REVIEW.md HLP-15)
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helpers_src
                + (
                    dedent("""
                        g = find_graph(%r); n = g.newNode('sbs::compositing::levels')
                        p = n.getPropertyFromId('levelinhigh', SDPropertyCategory.Input)
                        n.newPropertyGraph(p, 'SDSBSFunctionGraph')
                        cls = type(n.getPropertyGraph(p))
                        real = cls.setOutputNode
                        def _fails(*a, **k):
                            raise RuntimeError('fails on purpose')
                        cls.setOutputNode = _fails
                        try:
                            try:
                                expose_param(%r, n.getIdentifier(), 'levelinhigh', input_id='broken_reused')
                            except (Exception, APIException) as e:
                                print('FAILED', type(e).__name__)
                        finally:
                            cls.setOutputNode = real
                        fg = n.getPropertyGraph(p)
                        print('LEFT_NODES=%%d LEFT_INPUT=%%s' %% (len(fg.getNodes()) if fg is not None else 0, g.getPropertyFromId('broken_reused', SDPropertyCategory.Input) is not None))
                        g.deleteNode(n)""")
                )
                % (TEST_GRAPH, TEST_GRAPH)
            },
        )
    )
    check(
        'apply_edits',
        'expose: a failure on a reused empty function graph leaves no node in it',
        'FAILED' in t and 'LEFT_NODES=0 LEFT_INPUT=False' in t,
        t.strip()[-160:],
    )
    # setting a driven parameter would change only a hidden constant (REVIEW.md HLP-2)
    r_ = await c('apply_edits', {'ops': [{'op': 'set', 'node': lv, 'params': {'leveloutlow': [0.5] * 4}}], **G})
    check(
        'apply_edits',
        'set: refuses a parameter driven by a graph input',
        r_.is_error and "driven by graph input 'floor'" in text(r_),
        text(r_),
    )
    r_ = await c(
        'apply_edits', {'ops': [{'op': 'expose', 'node': lv, 'param': 'leveloutlow', 'input_id': 'floor'}], **G}
    )
    check(
        'apply_edits', 'expose: error on duplicate input', r_.is_error and 'already has an input' in text(r_), text(r_)
    )
    t = text(await c('list_graph_inputs', G))
    check(
        'list_graph_inputs',
        'inputs + users',
        'floor (float4)' in t and "label='Floor'" in t and '%s.leveloutlow' % lv in t and 'Samples' in t,
        t,
    )
    await c(
        'apply_edits',
        {
            'ops': [
                {
                    'op': 'expose',
                    'node': slope,
                    'param': 'Intensity',
                    'input_id': 'slope_amount',
                    'group': 'Shape',
                    'step': 0.5,
                    'min': 0,
                    'max': 20,
                }
            ],
            **G,
        },
    )
    t = text(await c('list_graph_inputs', G))
    line = next((l for l in t.splitlines() if l.startswith('slope_amount')), '')
    check('apply_edits', 'expose: group + step', "group='Shape'" in line and 'step=0.5' in line, line)
    await c('remove_graph_input', {'input_id': 'slope_amount', **G})
    await c('apply_edits', {'ops': [{'op': 'expose', 'node': lv, 'param': 'levelinmid', 'input_id': 'mid'}], **G})
    await designer_script(c, 'inputs/function_add_node', graph=TEST_GRAPH, node=lv)
    r_ = await c('remove_graph_input', {'input_id': 'mid', **G})
    still = 'mid (float4)' in text(await c('list_graph_inputs', G))
    check(
        'remove_graph_input',
        'refuses while a larger function reads it',
        r_.is_error and 'read inside the functions' in text(r_) and still,
        text(r_),
    )

    # an empty function graph on a parameter drives nothing (REVIEW.md HLP-13, HLP-16),
    # measured: adding one resets the stored value to its default and the output follows
    # that value; a set op then sets the value (which deletes the empty graph) and the
    # output follows again
    def stats_max(text_: str) -> float | None:
        m = re.search(r'^\w: min [0-9.]+  max ([0-9.]+)', text_, re.M)
        return float(m.group(1)) if m else None

    max_default = stats_max(text(await c('node_stats', {'node_id': lv, **G})))
    await c('apply_edits', {'ops': [{'op': 'set', 'node': lv, 'params': {'levelouthigh': [0.5, 0.5, 0.5, 1]}}], **G})
    max_half = stats_max(text(await c('node_stats', {'node_id': lv, **G})))
    empty_fn = text(await designer_script(c, 'inputs/add_empty_function', graph=TEST_GRAPH, node=lv))
    max_empty = stats_max(text(await c('node_stats', {'node_id': lv, **G})))
    check(
        'designer facts',
        'adding a function graph resets the stored value; the output follows the stored value',
        'EMPTY_FUNCTION nodes=0 value=(1.0, 1.0, 1.0, 1.0)' in empty_fn
        and max_half is not None
        and max_default is not None
        and max_half < max_default - 0.3
        and max_empty is not None
        and abs(max_empty - max_default) < 0.002,  # render noise (TST-22)
        'max %s at 1.0, %s at 0.5, %s with an empty graph added; %s'
        % (max_default, max_half, max_empty, empty_fn.strip()),
    )
    t = text(await c('describe_graph', {'node_ids': [lv], 'include_params': True, **G}))
    r_ = await c(
        'apply_edits', {'ops': [{'op': 'set', 'node': lv, 'params': {'levelouthigh': [0.5, 0.5, 0.5, 1]}}], **G}
    )
    kept = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + dedent("""\
                    from sd.api.sdproperty import SDPropertyCategory
                    n = g.getNodeFromId(%r)
                    print('GRAPH_KEPT=%%s' %% (n.getPropertyGraph(n.getPropertyFromId('levelouthigh', SDPropertyCategory.Input)) is not None))""")
                % lv
            },
        )
    )
    max_set = stats_max(text(await c('node_stats', {'node_id': lv, **G})))
    check(
        'apply_edits',
        'set: an empty function graph is not "driven": the value is set and drives the output',
        not r_.is_error
        and 'levelouthigh <-' not in t
        and 'GRAPH_KEPT=False' in kept
        and max_set is not None
        and max_half is not None
        and abs(max_set - max_half) < 0.002,
        '%s | %s | max %s' % (text(r_).strip()[-80:], kept.strip(), max_set),
    )
    # sweep_param and the expose op agree (they use the same test, REVIEW.md TST-20)
    await designer_script(c, 'inputs/add_empty_function', graph=TEST_GRAPH, node=lv)
    r_sweep = await c(
        'sweep_param', {'node_id': lv, 'param': 'levelouthigh', 'values': [[0.4] * 4, [0.6] * 4], 'tile_size': 64, **G}
    )
    await designer_script(c, 'inputs/add_empty_function', graph=TEST_GRAPH, node=lv)
    r_expose = await c(
        'apply_edits',
        {'ops': [{'op': 'expose', 'node': lv, 'param': 'levelouthigh', 'input_id': 'empty_fn_check'}], **G},
    )
    await c('remove_graph_input', {'input_id': 'empty_fn_check', **G})
    check(
        'sweep_param',
        'an empty function graph is not "driven" for sweep_param and the expose op',
        not r_sweep.is_error and not r_expose.is_error,
        (text(r_sweep) if r_sweep.is_error else '') + (text(r_expose) if r_expose.is_error else '') or 'both ran',
    )
    # a driven parameter shows its source, not the constant it hides (REVIEW.md HLP-9)
    t = text(await c('describe_graph', {'node_ids': [lv], 'include_params': True, **G}))
    check(
        'describe_graph',
        'driven parameters show what drives them',
        "leveloutlow <- graph input 'floor'" in t and 'levelinmid <- a function' in t,
        t,
    )
    r_ = await c('apply_edits', {'ops': [{'op': 'expose', 'node': lv, 'param': 'levelinmid', 'input_id': 'mid2'}], **G})
    check(
        'apply_edits',
        'expose: refuses a parameter driven by a function',
        r_.is_error and 'already driven by a function' in text(r_),
        text(r_),
    )
    # sweeping either kind of driven parameter would delete what drives it
    for param, driver in (('leveloutlow', 'graph input'), ('levelinmid', 'function')):
        r_ = await c('sweep_param', {'node_id': lv, 'param': param, 'values': [[0.4] * 4, [0.6] * 4], **G})
        check(
            'sweep_param',
            'refuses a parameter driven by a %s' % driver,
            r_.is_error and 'is driven by a graph input or function' in text(r_),
            text(r_),
        )
    # a function with nodes but no output node drives nothing (designer facts), yet setting the
    # value would delete it, so the tools leave it alone and say what it is
    stub = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels'}], **G})))
    try:
        await c(
            'apply_edits', {'ops': [{'op': 'expose', 'node': stub, 'param': 'levelinlow', 'input_id': 'stub_in'}], **G}
        )
        await designer_script(c, 'inputs/function_no_output', graph=TEST_GRAPH, node=stub)

        t = text(await c('describe_graph', {'node_ids': [stub], 'include_params': True, **G}))
        check(
            'describe_graph',
            'a function with no output node is not shown as what drives the value',
            len(re.findall(r'^\s+levelouthigh\b', t, re.M)) == 1
            and 'no output node' in t
            and 'levelouthigh <-' not in t,
            t,
        )
        attempts: dict[str, tuple[str, dict[str, Any]]] = {
            'set': (
                'apply_edits',
                {'ops': [{'op': 'set', 'node': stub, 'params': {'levelouthigh': [0.5] * 4}}], **G},
            ),
            'expose': (
                'apply_edits',
                {'ops': [{'op': 'expose', 'node': stub, 'param': 'levelouthigh', 'input_id': 'stub_other'}], **G},
            ),
            'sweep': (
                'sweep_param',
                {'node_id': stub, 'param': 'levelouthigh', 'values': [[0.4] * 4, [0.6] * 4], **G},
            ),
        }
        count_nodes = (
            GRAPH_OF % TEST_GRAPH
            + dedent("""\
                from sd.api.sdproperty import SDPropertyCategory
                n = g.getNodeFromId(%r)
                print('STUB_NODES=%%d' %% len(n.getPropertyGraph(n.getPropertyFromId('levelouthigh', SDPropertyCategory.Input)).getNodes()))""")
            % stub
        )
        for what, (tool, args) in attempts.items():
            r_ = await c(tool, args)
            left = text(await c('execute_designer_code', {'code': count_nodes}))
            check(
                tool,
                '%s: says a function with no output node drives nothing, and keeps it' % what,
                r_.is_error
                and 'no output node' in text(r_)
                and 'drives nothing' in text(r_)
                and 'STUB_NODES=1' in left,
                '%s | %s' % (text(r_), left.strip()),
            )
        line = next((l for l in text(await c('list_graph_inputs', G)).splitlines() if l.startswith('stub_in')), '')
        check(
            'list_graph_inputs',
            'a function with no output node is not listed as driven',
            '%s.levelinlow' % stub in line and 'levelouthigh' not in line,
            line,
        )
        r_ = await c('remove_graph_input', {'input_id': 'stub_in', **G})
        left = text(await c('execute_designer_code', {'code': count_nodes}))
        check(
            'remove_graph_input',
            'refuses while a function with no output node reads it, and keeps it',
            r_.is_error
            and 'levelouthigh' in text(r_)
            and 'no effect on the output today' in text(r_)
            and 'STUB_NODES=1' in left,
            '%s | %s' % (text(r_), left.strip()),
        )
        # a get node only counts as driving when it is connected to the function's output: here
        # stub_wired goes through an add node, and stub_orphan is connected to nothing
        await c(
            'apply_edits',
            {
                'ops': [
                    {'op': 'expose', 'node': stub, 'param': 'levelinmid', 'input_id': 'stub_wired'},
                    {'op': 'expose', 'node': stub, 'param': 'levelinhigh', 'input_id': 'stub_orphan'},
                ],
                **G,
            },
        )
        await designer_script(c, 'inputs/function_with_unconnected_get', graph=TEST_GRAPH, node=stub)
        lines = text(await c('list_graph_inputs', G)).splitlines()
        wired = next((l for l in lines if l.startswith('stub_wired')), '')
        orphan = next((l for l in lines if l.startswith('stub_orphan')), '')
        check(
            'list_graph_inputs',
            'drives: a connected get node counts, an unconnected one does not',
            wired.count('%s.leveloutlow' % stub) == 1
            and '%s.levelinmid' % stub in wired
            and '%s.levelinhigh' % stub in orphan
            and 'leveloutlow' not in orphan,
            '%s / %s' % (wired, orphan),
        )
        r_ = await c('remove_graph_input', {'input_id': 'stub_orphan', **G})
        kept = text(await c('list_graph_inputs', G))
        check(
            'remove_graph_input',
            'refuses while an unconnected get node names the input',
            r_.is_error and 'leveloutlow' in text(r_) and 'stub_orphan' in kept,
            text(r_),
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': stub}], **G})
        for input_id in ('stub_in', 'stub_wired', 'stub_orphan'):
            await c('remove_graph_input', {'input_id': input_id, **G})
    await designer_script(c, 'inputs/function_delete', graph=TEST_GRAPH, node=lv)
    t = text(await c('remove_graph_input', {'input_id': 'mid', **G}))
    check('remove_graph_input', 'removes once nothing reads it', 'removed graph input mid' in t, t)
    # an FX-Map's functions read the graph's inputs too (measured on a copy of brick_1: the output follows such an
    # input, and changes when it is removed; REVIEW.md HLP-71)
    t = text(await designer_script(c, 'inputs/fxmap_reads_input', graph=TEST_GRAPH, input_id='fx_in'))
    fx = re.search(r'FX=(\d+)', t)
    try:
        line = next((l for l in text(await c('list_graph_inputs', G)).splitlines() if l.startswith('fx_in')), '')
        check('list_graph_inputs', "drives: an FX-Map's function counts", fx is not None and fx.group(1) in line, line)
        t = text(await c('describe_graph', {'node_ids': [fx.group(1)] if fx else [], 'include_params': True, **G}))
        check('describe_graph', "an FX-Map's function shows", "patternsize <- graph input 'fx_in'" in t, t)
        check(
            'describe_graph', 'an FX-Map is named, not a blank instance', ' fxmaps @' in t and 'instance: @' not in t, t
        )
        r_ = await c('remove_graph_input', {'input_id': 'fx_in', **G})
        still = 'fx_in' in text(await c('list_graph_inputs', G))
        check(
            'remove_graph_input',
            "refuses while an FX-Map's function reads it, and keeps it",
            r_.is_error and fx is not None and fx.group(1) in text(r_) and still,
            text(r_),
        )
    finally:
        if fx:
            await c('apply_edits', {'ops': [{'op': 'delete', 'node': fx.group(1)}], **G})
        await c('remove_graph_input', {'input_id': 'fx_in', **G})
    # deleting a function on $outputsize switches its inheritance (designer facts): an unbound or rolled back one keeps
    # both, and so the size it had
    sized = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels'}], **G})))
    try:
        await c('apply_edits', {'ops': [{'op': 'set', 'node': sized, 'params': {'$outputsize': [5, 5]}}], **G})
        await c(
            'apply_edits',
            {
                'ops': [
                    {'op': 'expose', 'node': sized, 'param': '$outputsize', 'input_id': 'size_in', 'default': [3, 3]}
                ],
                **G,
            },
        )
        await c('remove_graph_input', {'input_id': 'size_in', **G})
        t = text(await designer_script(c, 'shared/node_size_inheritance', graph=TEST_GRAPH, node=sized))
        check(
            'remove_graph_input',
            '$outputsize keeps its inheritance and value when unbound',
            'INHERIT=Absolute' in t and 'x: 3, y: 3' in t,
            t,
        )
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': helpers_src
                    + dedent("""
                        _GETTERS['int2'] = 'get_no_such_type'
                        try:
                            expose_param(%r, %r, '$outputsize', input_id='broken_size')
                        except (Exception, APIException) as e:
                            print('FAILED', type(e).__name__)
                    """)
                    % (TEST_GRAPH, sized)
                },
            )
        )
        after = text(await designer_script(c, 'shared/node_size_inheritance', graph=TEST_GRAPH, node=sized))
        check(
            'apply_edits',
            'expose: a failure midway leaves $outputsize as it was, inheritance included',
            'FAILED' in t and 'INHERIT=Absolute' in after and 'x: 3, y: 3' in after,
            t.strip()[-100:] + ' | ' + after.strip(),
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': sized}], **G})
        await c('remove_graph_input', {'input_id': 'size_in', **G})
    # a function reading a name that is no graph input isn't reported as one, and a name Designer provides isn't
    # called broken (REVIEW.md HLP-72, HLP-79, HLP-80)
    for name, missing in (('no_such_input', True), ('$sizelog2', False), ('$tiling', False), ('#opacity', False)):
        gone = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels'}], **G})))
        try:
            await designer_script(c, 'inputs/function_reads_missing_input', graph=TEST_GRAPH, node=gone, name=name)
            t = text(await c('describe_graph', {'node_ids': [gone], 'include_params': True, **G}))
            check(
                'describe_graph',
                'a function reading %s says what it reads' % name,
                'levelinhigh <- a function reading %r' % name in t
                and ('not an input of this graph' in t) == missing
                and 'graph input' not in t,
                t,
            )
            for tool, args in (
                ('apply_edits', {'ops': [{'op': 'set', 'node': gone, 'params': {'levelinhigh': [0.5] * 4}}], **G}),
                ('sweep_param', {'node_id': gone, 'param': 'levelinhigh', 'values': [[0.4] * 4, [0.6] * 4], **G}),
                (
                    'apply_edits',
                    {'ops': [{'op': 'expose', 'node': gone, 'param': 'levelinhigh', 'input_id': 'stray'}], **G},
                ),
            ):
                r_ = await c(tool, args)
                refusal = text(r_)
                check(
                    tool,
                    'a function reading %s: refused, with advice that can work' % name,
                    r_.is_error
                    and repr(name) in refusal
                    and ('not an input of this graph' in refusal) == missing
                    and ('delete it first' in refusal) == missing
                    and "node 'graph'" not in refusal
                    and 'node_id="graph"' not in refusal
                    and 'remove its graph input' not in refusal,
                    refusal,
                )
        finally:
            await c('apply_edits', {'ops': [{'op': 'delete', 'node': gone}], **G})
    # a processor's function is the processor's program, not a binding, even as one get (REVIEW.md HLP-77)
    t = text(await designer_script(c, 'inputs/processors_read_input', graph=TEST_GRAPH, input_id='proc_in'))
    procs = re.search(r'PROCESSORS=(\d+),(\d+)', t)
    try:
        r_ = await c('remove_graph_input', {'input_id': 'proc_in', **G})
        kept = text(await c('list_graph_inputs', G))
        check(
            'remove_graph_input',
            "refuses while a processor's function is one get of it, and keeps it",
            r_.is_error
            and procs is not None
            and '%s.function' % procs.group(1) in text(r_)
            and '%s.perpixel' % procs.group(2) in text(r_)
            and 'proc_in' in kept,
            text(r_),
        )
    finally:
        if procs:
            await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in procs.groups()], **G})
        await c('remove_graph_input', {'input_id': 'proc_in', **G})
    # a function on the graph's own parameter reads inputs too; the API can't reach it, so the saved file is read
    # (REVIEW.md HLP-76)
    base_sbs = os.path.join(ctx.scratch, 'graph_parameter_function.sbs')
    base_graph = TEST_GRAPH + '_base_function'
    B = {'graph': base_graph}
    t = text(await designer_script(c, 'inputs/graph_parameter_function', identifier=base_graph, path=base_sbs))
    try:
        check(
            'designer facts',
            "a function on a graph's own $outputsize drives it",
            'GRAPH_SIZE input 3,3 8 px, input 5,5 32 px' in t,
            t,
        )
        line = next((l for l in text(await c('list_graph_inputs', B)).splitlines() if l.startswith('size_in')), '')
        check(
            'list_graph_inputs',
            "drives: a function on the graph's own parameter counts",
            'graph.outputsize' in line,
            line,
        )
        r_ = await c('remove_graph_input', {'input_id': 'size_in', **B})
        still = 'size_in' in text(await c('list_graph_inputs', B))
        check(
            'remove_graph_input',
            "refuses while a function on the graph's own parameter reads it, and keeps it",
            r_.is_error and 'graph.outputsize' in text(r_) and still,
            text(r_),
        )
    finally:
        await designer_script(c, 'shared/unload_packages', paths=[base_sbs])
    # an enum parameter: the int input's value must fit before anything is deleted (REVIEW.md HLP-73)
    blend = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blend'}], **G})))
    try:
        await c(
            'apply_edits',
            {'ops': [{'op': 'expose', 'node': blend, 'param': 'blendingmode', 'input_id': 'mode_in'}], **G},
        )
        await c('apply_edits', {'ops': [{'op': 'set', 'node': 'graph', 'params': {'mode_in': 99}}], **G})
        r_ = await c('remove_graph_input', {'input_id': 'mode_in', **G})
        t = text(await c('describe_graph', {'node_ids': [blend], 'include_params': True, **G}))
        check(
            'remove_graph_input',
            "refuses when an enum parameter can't keep the input's value, changing nothing",
            r_.is_error and 'nothing was changed' in text(r_) and "blendingmode <- graph input 'mode_in'" in t,
            '%s | %s' % (text(r_), t),
        )
        await c('apply_edits', {'ops': [{'op': 'set', 'node': 'graph', 'params': {'mode_in': 5}}], **G})
        t = text(await c('remove_graph_input', {'input_id': 'mode_in', **G}))
        check('remove_graph_input', 'an enum parameter keeps a value that fits', 'removed graph input mode_in' in t, t)
        t = text(await c('describe_graph', {'node_ids': [blend], 'include_params': True, **G}))
        check(
            'remove_graph_input',
            'the enum parameter holds that value',
            re.search(r'blendingmode = .*\b(5|max)\b', t),
            t,
        )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': blend}], **G})
        await c('remove_graph_input', {'input_id': 'mode_in', **G})
    r_ = await c(
        'sweep_param',
        {'node_id': 'graph', 'param': 'floor', 'values': [[0.1] * 4, [0.9] * 4], 'view_node': lv, 'tile_size': 96, **G},
    )
    means = [float(m) for m in re.findall(r'L [0-9.]+\.\.[0-9.]+ \(mean ([0-9.]+)\)', text(r_))]
    check('sweep_param', 'graph input changes output', len(means) == 2 and means[1] > means[0] + 0.3, text(r_))
    t = text(await c('remove_graph_input', {'input_id': 'Samples', **G}))
    check('remove_graph_input', 'unbinds + keeps value', 'kept value 16' in t and 'removed graph input' in t, t)
