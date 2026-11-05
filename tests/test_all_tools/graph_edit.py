"""The temporary graph and one-op edits (create_graph; apply_edits' add, connect, disconnect, move
and delete ops; execute_designer_code, describe_graph, preview_node)."""

import os
import re
import time
from textwrap import dedent

from .common import SAVED_GRAPH, TEST_GRAPH, Ctx, added_id, check, designer_script, is_image, skip, text


async def create(ctx: Ctx) -> None:
    """Creates the self-test graph and its first nodes (clouds -> slope blur -> levels -> output)."""
    c, scratch, helper_source = ctx.c, ctx.scratch, ctx.helper_source
    # --- build a temporary graph with the edit tools
    t = text(await c('create_graph', {'name': TEST_GRAPH, 'size_log2': 9}))
    check('create_graph', '512 px', '(512 px)' in t, t)
    saved_sbs = os.path.join(scratch, SAVED_GRAPH + '.sbs')
    t = text(await c('create_graph', {'name': SAVED_GRAPH, 'save_path': saved_sbs, 'size_log2': 8}))
    check('create_graph', 'save_path writes the .sbs', os.path.isfile(saved_sbs), t)
    G = {'graph': TEST_GRAPH}
    await c('open_graph', {'graph': TEST_GRAPH})  # so you can watch the nodes appear
    r_ = await c('diff_graph', {'against': 'saved', **G})
    check('diff_graph', 'error: never saved', r_.is_error and 'never been saved' in text(r_), text(r_))
    r_ = await c('diff_graph', {'against': 'latest', 'graph': SAVED_GRAPH})
    check('diff_graph', 'error: no snapshots yet', r_.is_error and 'no snapshots of' in text(r_), text(r_))
    t = text(
        await c(
            'apply_edits',
            {'ops': [{'op': 'add', 'definition': 'noise_clouds_2.sbs/clouds_2', 'params': {'scale': 4}}], **G},
        )
    )
    check('apply_edits', 'add: library + param', 'instance:clouds_2' in t and '-> 4' in t, t)
    clouds = added_id(t)
    slope = added_id(
        text(
            await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'slope_blur.sbs/slope_blur_grayscale_2'}], **G})
        )
    )
    t = text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels'}], **G}))
    check('apply_edits', 'add: atomic', 'levels' in t, t.splitlines()[0])
    lv = added_id(t)
    out = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'output'}], **G})))
    r_ = await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'not_a_real_node'}], **G})
    check('apply_edits', 'add: error on unknown type', r_.is_error and 'neither an atomic' in text(r_), '')
    # a bad param refuses the whole add, and says so: the node isn't left behind (REVIEW.md HLP-30)
    before = text(await designer_script(c, 'shared/count_nodes', graph=TEST_GRAPH))
    r_ = await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels', 'params': {'levelinhigh': 0.5}}], **G})
    after = text(await designer_script(c, 'shared/count_nodes', graph=TEST_GRAPH))
    # if removing it fails too, both errors are reported (REVIEW.md HLP-37)
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helper_source
                + (
                    dedent("""
                        g = find_graph(%r); had = {n.getIdentifier() for n in g.getNodes()}
                        real = SDSBSCompGraph.deleteNode
                        def failing(self, node):
                            raise RuntimeError('delete failed on purpose')
                        SDSBSCompGraph.deleteNode = failing
                        try:
                            add_node(%r, 'levels', None, {'levelinhigh': 0.5})
                        except Exception as e:
                            print('ERROR=' + str(e))
                        finally:
                            # it is SDGraph's: leave no copy behind (TST-73)
                            del SDSBSCompGraph.deleteNode
                            for n in [n for n in g.getNodes() if n.getIdentifier() not in had]:
                                g.deleteNode(n)
                    """)
                )
                % (TEST_GRAPH, TEST_GRAPH)
            },
        )
    )
    check(
        'apply_edits',
        'add: a failed removal is reported with the error that caused it',
        'expects 4' in t and 'delete failed on purpose' in t,
        t.strip()[-200:],
    )
    check(
        'apply_edits',
        'add: a bad param leaves no node behind, and says so',
        r_.is_error and 'expects 4' in text(r_) and 'not added' in text(r_) and before == after and 'NODES=' in before,
        text(r_).strip()[-120:] + ' | ' + before.strip() + ' -> ' + after.strip(),
    )
    ctx.G = G
    ctx.clouds = clouds
    ctx.slope = slope
    ctx.lv = lv
    ctx.out = out


async def output_fields(ctx: Ctx) -> None:
    """Names and tags output nodes with apply_edits, on a graph of its own: every other check counts this one's outputs."""
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

    # closed, so the one edit left unsaved doesn't count in later checks of unsaved packages
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


async def wire(ctx: Ctx) -> None:
    """Connects the nodes and checks the other one-off edit tools on them."""
    c, was_running, G, clouds, slope, lv, out = ctx.c, ctx.was_running, ctx.G, ctx.clouds, ctx.slope, ctx.lv, ctx.out
    linked = []
    for a, b, port in [
        (clouds, slope, 'Source'),
        (clouds, slope, 'Effect'),
        (slope, lv, 'input1'),
        (lv, out, 'inputNodeOutput'),
    ]:
        t = text(await c('apply_edits', {'ops': [{'op': 'connect', 'from': a, 'to': b, 'input': port}], **G}))
        linked.append('-> %s.%s' % (b, port) in t)
    check('apply_edits', 'connect: 4 links', all(linked), str(linked))
    r_ = await c('apply_edits', {'ops': [{'op': 'connect', 'from': clouds, 'to': lv, 'input': 'nope'}], **G})
    check('apply_edits', 'connect: error on bad port', r_.is_error and 'connectors:' in text(r_), text(r_))
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': (
                    dedent("""\
                        import sd
                        from sd.api.sdvaluestring import SDValueString
                        g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]
                        n=g.getNodeFromId('%s'); n.setAnnotationPropertyValueFromId('identifier', SDValueString.sNew('height'))
                        print('output named height')""")
                )
                % (TEST_GRAPH, out),
                'undo_label': 'self-test: name output',
            },
        )
    )
    check('execute_designer_code', 'sd API call', 'output named height' in t, t)
    r_ = await c('execute_designer_code', {'code': 'raise ValueError("boom")'})
    check('execute_designer_code', 'error traceback', 'ValueError: boom' in text(r_), '')
    t = text(await c('execute_designer_code', {'code': 'while True: pass', 'timeout_s': 2}))
    check('execute_designer_code', 'timeout', 'ScriptAborted: timed out' in t, '')
    # an abort landing in a Python finalizer (every sd API object has a __del__ calling release())
    # was dropped and the script ran on to the end: before the fix, 3 of 6 runs of this loop in
    # Designer ignored a 1 s timeout (REVIEW.md PLG-25). Several runs, since where it lands varies
    finalizer_loop = dedent("""\
        import time
        class Obj:
            def __init__(self):
                self.h = 1
            def release(self):
                self.h = None
            def __del__(self):
                if self.h:
                    self.release()
        end = time.monotonic() + 5
        while time.monotonic() < end:
            o = Obj()
        print('RAN TO THE END')""")
    # and one whose __del__ raises an ordinary error: its "Exception ignored" report ran traced and the
    # abort landed there, dropped for good (REVIEW.md PLG-26)
    raising_loop = finalizer_loop.replace(
        '        if self.h:\n            self.release()', "        raise ValueError('x')"
    )
    runs = []
    for code in [finalizer_loop] * 6 + [raising_loop] * 4:
        started = time.monotonic()
        t = text(await c('execute_designer_code', {'code': code, 'timeout_s': 1}))
        runs.append(('ScriptAborted: timed out' in t, 'RAN TO THE END' in t, round(time.monotonic() - started, 1)))
    # PySide reports an exception raised in a slot through sys.excepthook, and emit() returns: an
    # abort landing in a slot was dropped there (REVIEW.md PLG-29)
    slot_loop = dedent("""\
        import time
        from PySide6.QtCore import QObject, Signal
        class Emitter(QObject):
            fired = Signal()
        def slot():
            a = 1
            b = 2
            c = a + b
            d = c * 2
            return d - 1
        e = Emitter()
        e.fired.connect(slot)
        end = time.monotonic() + 5
        while time.monotonic() < end:
            e.fired.emit()
        print('RAN TO THE END')""")
    for _ in range(4):
        started = time.monotonic()
        t = text(await c('execute_designer_code', {'code': slot_loop, 'timeout_s': 1}))
        runs.append(('ScriptAborted: timed out' in t, 'RAN TO THE END' in t, round(time.monotonic() - started, 1)))
    check(
        'execute_designer_code',
        'a timeout stops loops with finalizers (raising ones too) and with Qt slots, every time',
        all(aborted and not finished and took < 4 for aborted, finished, took in runs),
        str(runs),
    )
    # the abort fires once (Python unsets a trace function that raises), so cleanup code
    # such as UndoGroup committing its transaction runs to the end (REVIEW.md PLG-2)
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': (
                    dedent("""\
                        try:
                            while True:
                                pass
                        finally:
                            total = 0
                            for i in range(20000):
                                total += i
                            print('CLEANUP DONE', total)""")
                ),
                'timeout_s': 1,
            },
        )
    )
    check(
        'designer facts',
        'an aborted script still finishes its cleanup',
        'ScriptAborted: timed out' in t and 'CLEANUP DONE 199990000' in t,
        t[-200:],
    )
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': dedent("""\
                    import sd
                    pm = sd.getContext().getSDApplication().getPackageMgr()
                    print('MODIFIED=%%s' %% any(p.isModified() for p in pm.getUserPackages() if any(r.getIdentifier() == %r for r in p.getChildrenResources(False))))""")
                % TEST_GRAPH
            },
        )
    )
    if was_running:
        # a regression here would close the user's Designer: only on our own instance
        skip('quit_designer', 'refuses with unsaved changes', 'Designer was already running (yours)')
    elif 'MODIFIED=True' in t:  # otherwise quit_designer could really close Designer
        r_ = await c('quit_designer')
        still = not (await c('designer_status')).is_error
        check(
            'quit_designer',
            'refuses with unsaved changes',
            r_.is_error and 'unsaved changes' in text(r_) and '[%s]' % TEST_GRAPH in text(r_) and still,
            text(r_),
        )
    else:
        skip('quit_designer', 'refuses with unsaved changes', 'self-test package not reported as modified')
    t = text(
        await c(
            'apply_edits',
            {
                'ops': [
                    {'op': 'move', 'node': clouds, 'position': [-600, 0]},
                    {'op': 'move', 'node': slope, 'position': [-300, 0]},
                    {'op': 'move', 'node': lv, 'position': [0, 0]},
                    {'op': 'move', 'node': out, 'position': [300, 0]},
                ],
                **G,
            },
        )
    )
    check('apply_edits', 'move: 4 moved', t.count('moved') == 4, '')
    await c('open_graph', {'graph': TEST_GRAPH})  # fit the view to the nodes so far
    t = text(await c('describe_graph', {'include_params': True, **G}))
    check('describe_graph', 'links + params', 'Effect<-%s' % clouds in t and 'Samples = 16' in t, t.splitlines()[0])
    r_ = await c('preview_node', {'node_id': slope, **G})
    check('preview_node', 'intermediate node', is_image(r_), '' if is_image(r_) else text(r_))
    t = text(await c('apply_edits', {'ops': [{'op': 'disconnect', 'node': slope, 'input': 'Effect'}], **G}))
    check('apply_edits', 'disconnect: one link', 'removed 1' in t, t)
    tmp = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur'}], **G})))
    t = text(await c('apply_edits', {'ops': [{'op': 'delete', 'node': tmp}], **G}))
    check('apply_edits', 'delete: one node', 'deleted %s blur' % tmp in t, t)
