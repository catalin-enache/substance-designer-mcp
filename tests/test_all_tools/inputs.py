"""Exposed inputs and graph size: set_graph_size, expose_param, list_graph_inputs,
remove_graph_input, and parameters driven by functions."""

import re

from .common import GRAPH_OF, TEST_GRAPH, Ctx, check, helpers_source, text


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
            'expose_param',
            {
                'node_id': lv,
                'param': 'leveloutlow',
                'input_id': 'floor',
                'label': 'Floor',
                'default': [0.25] * 4,
                'min': 0,
                'max': 1,
                **G,
            },
        )
    )
    check('expose_param', 'float4 with range', "graph input 'floor'" in t, t)
    t = text(await c('expose_param', {'node_id': slope, 'param': 'Samples', **G}))
    check('expose_param', 'int, defaults to current value', "'Samples'" in t and 'default 16' in t, t)
    # a failure after the function graph was created leaves no function graph behind
    # (REVIEW.md HLP-3): the getter for float4 renamed to a type that doesn't exist
    helpers_src = helpers_source()
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helpers_src
                + (
                    "\nset_params(%r, %r, {'levelinhigh': [0.8] * 4})\n"
                    "_GETTERS['float4'] = 'get_no_such_type'\n"
                    "try:\n    expose_param(%r, %r, 'levelinhigh', input_id='broken')\nexcept (Exception, APIException) as e:\n"
                    "    print('FAILED', type(e).__name__)\n"
                    'g = find_graph(%r); n = g.getNodeFromId(%r)\n'
                    "p = n.getPropertyFromId('levelinhigh', SDPropertyCategory.Input)\n"
                    "print('LEFT_GRAPH=%%s LEFT_INPUT=%%s VALUE=%%.2f' %% (n.getPropertyGraph(p) is not None, "
                    "g.getPropertyFromId('broken', SDPropertyCategory.Input) is not None, n.getPropertyValue(p).get().x))\n"
                    "set_params(%r, %r, {'levelinhigh': [1.0] * 4})"
                )
                % (TEST_GRAPH, lv, TEST_GRAPH, lv, TEST_GRAPH, lv, TEST_GRAPH, lv)
            },
        )
    )
    # ...and the parameter keeps the value it had (adding the graph reset it; REVIEW.md HLP-21)
    check(
        'expose_param',
        'a failure midway leaves nothing behind',
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
                    "\ng = find_graph(%r); n = g.newNode('sbs::compositing::levels')\n"
                    "p = n.getPropertyFromId('levelinhigh', SDPropertyCategory.Input)\n"
                    "n.newPropertyGraph(p, 'SDSBSFunctionGraph')\ncls = type(n.getPropertyGraph(p))\n"
                    'real = cls.setOutputNode\n'
                    "def _fails(*a, **k):\n    raise RuntimeError('fails on purpose')\n"
                    'cls.setOutputNode = _fails\n'
                    'try:\n'
                    "    try:\n        expose_param(%r, n.getIdentifier(), 'levelinhigh', input_id='broken_reused')\n"
                    "    except (Exception, APIException) as e:\n        print('FAILED', type(e).__name__)\n"
                    'finally:\n    cls.setOutputNode = real\n'
                    'fg = n.getPropertyGraph(p)\n'
                    "print('LEFT_NODES=%%d LEFT_INPUT=%%s' %% (len(fg.getNodes()) if fg is not None else 0, "
                    "g.getPropertyFromId('broken_reused', SDPropertyCategory.Input) is not None))\n"
                    'g.deleteNode(n)'
                )
                % (TEST_GRAPH, TEST_GRAPH)
            },
        )
    )
    check(
        'expose_param',
        'a failure on a reused empty function graph leaves no node in it',
        'FAILED' in t and 'LEFT_NODES=0 LEFT_INPUT=False' in t,
        t.strip()[-160:],
    )
    # setting a driven parameter would change only a hidden constant (REVIEW.md HLP-2)
    r_ = await c('set_params', {'node_id': lv, 'params': {'leveloutlow': [0.5] * 4}, **G})
    check(
        'set_params',
        'refuses a parameter driven by a graph input',
        r_.is_error and "driven by graph input 'floor'" in text(r_),
        text(r_),
    )
    r_ = await c('expose_param', {'node_id': lv, 'param': 'leveloutlow', 'input_id': 'floor', **G})
    check('expose_param', 'error on duplicate input', r_.is_error and 'already has an input' in text(r_), text(r_))
    t = text(await c('list_graph_inputs', G))
    check(
        'list_graph_inputs',
        'inputs + users',
        'floor (float4)' in t and "label='Floor'" in t and '%s.leveloutlow' % lv in t and 'Samples' in t,
        t,
    )
    await c(
        'expose_param',
        {
            'node_id': slope,
            'param': 'Intensity',
            'input_id': 'slope_amount',
            'group': 'Shape',
            'step': 0.5,
            'min': 0,
            'max': 20,
            **G,
        },
    )
    t = text(await c('list_graph_inputs', G))
    line = next((l for l in t.splitlines() if l.startswith('slope_amount')), '')
    check('expose_param', 'group + step', "group='Shape'" in line and 'step=0.5' in line, line)
    await c('remove_graph_input', {'input_id': 'slope_amount', **G})
    await c('expose_param', {'node_id': lv, 'param': 'levelinmid', 'input_id': 'mid', **G})
    extra = (
        GRAPH_OF % TEST_GRAPH
        + (
            "from sd.api.sdproperty import SDPropertyCategory\nn=g.getNodeFromId('%s')\n"
            "p=n.getPropertyFromId('levelinmid', SDPropertyCategory.Input)\n"
        )
        % lv
    )
    await c(
        'execute_designer_code',
        {'code': extra + "n.getPropertyGraph(p).newNode('sbs::function::const_float1')\nprint('extra node')"},
    )
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
    # that value; set_params then sets the value (which deletes the empty graph) and the
    # output follows again
    def stats_max(text_: str) -> float | None:
        m = re.search(r'^\w: min [0-9.]+  max ([0-9.]+)', text_, re.M)
        return float(m.group(1)) if m else None

    probe = (
        GRAPH_OF % TEST_GRAPH
        + (
            "from sd.api.sdproperty import SDPropertyCategory\nn=g.getNodeFromId('%s')\n"
            "p=n.getPropertyFromId('levelouthigh', SDPropertyCategory.Input)\n"
        )
        % lv
    )
    max_default = stats_max(text(await c('node_stats', {'node_id': lv, **G})))
    await c('set_params', {'node_id': lv, 'params': {'levelouthigh': [0.5, 0.5, 0.5, 1]}, **G})
    max_half = stats_max(text(await c('node_stats', {'node_id': lv, **G})))
    empty_fn = text(
        await c(
            'execute_designer_code',
            {
                'code': probe
                + (
                    "n.newPropertyGraph(p, 'SDSBSFunctionGraph')\n"
                    "print('EMPTY_FUNCTION nodes=%d value=%s' % (len(n.getPropertyGraph(p).getNodes()), "
                    'tuple(round(x, 3) for x in (lambda v: (v.x, v.y, v.z, v.w))(n.getPropertyValue(p).get()))))'
                )
            },
        )
    )
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
    r_ = await c('set_params', {'node_id': lv, 'params': {'levelouthigh': [0.5, 0.5, 0.5, 1]}, **G})
    kept = text(
        await c(
            'execute_designer_code', {'code': probe + "print('GRAPH_KEPT=%s' % (n.getPropertyGraph(p) is not None))"}
        )
    )
    max_set = stats_max(text(await c('node_stats', {'node_id': lv, **G})))
    check(
        'set_params',
        'an empty function graph is not "driven": the value is set and drives the output',
        not r_.is_error
        and 'levelouthigh <-' not in t
        and 'GRAPH_KEPT=False' in kept
        and max_set is not None
        and max_half is not None
        and abs(max_set - max_half) < 0.002,
        '%s | %s | max %s' % (text(r_).strip()[-80:], kept.strip(), max_set),
    )
    # sweep_param and expose_param agree (they use the same test, REVIEW.md TST-20)
    await c('execute_designer_code', {'code': probe + "n.newPropertyGraph(p, 'SDSBSFunctionGraph')"})
    r_sweep = await c(
        'sweep_param', {'node_id': lv, 'param': 'levelouthigh', 'values': [[0.4] * 4, [0.6] * 4], 'tile_size': 64, **G}
    )
    await c('execute_designer_code', {'code': probe + "n.newPropertyGraph(p, 'SDSBSFunctionGraph')"})
    r_expose = await c('expose_param', {'node_id': lv, 'param': 'levelouthigh', 'input_id': 'empty_fn_check', **G})
    await c('remove_graph_input', {'input_id': 'empty_fn_check', **G})
    check(
        'sweep_param',
        'an empty function graph is not "driven" for sweep_param and expose_param',
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
    r_ = await c('expose_param', {'node_id': lv, 'param': 'levelinmid', 'input_id': 'mid2', **G})
    check(
        'expose_param',
        'refuses a parameter driven by a function',
        r_.is_error and 'already driven by a function' in text(r_),
        text(r_),
    )
    await c('execute_designer_code', {'code': extra + "n.deletePropertyGraph(p)\nprint('function removed')"})
    t = text(await c('remove_graph_input', {'input_id': 'mid', **G}))
    check('remove_graph_input', 'removes once nothing reads it', 'removed graph input mid' in t, t)
    r_ = await c(
        'sweep_param',
        {'node_id': 'graph', 'param': 'floor', 'values': [[0.1] * 4, [0.9] * 4], 'view_node': lv, 'tile_size': 96, **G},
    )
    means = [float(m) for m in re.findall(r'L [0-9.]+\.\.[0-9.]+ \(mean ([0-9.]+)\)', text(r_))]
    check('sweep_param', 'graph input changes output', len(means) == 2 and means[1] > means[0] + 0.3, text(r_))
    t = text(await c('remove_graph_input', {'input_id': 'Samples', **G}))
    check('remove_graph_input', 'unbinds + keeps value', 'kept value 16' in t and 'removed graph input' in t, t)
