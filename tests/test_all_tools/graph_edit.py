"""The temporary graph and one-op edits (create_graph; apply_edits' add, connect, disconnect, move
and delete ops; execute_designer_code, describe_graph, preview_node)."""

import os
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
            r_.is_error and 'unsaved changes' in text(r_) and TEST_GRAPH in text(r_) and still,
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
