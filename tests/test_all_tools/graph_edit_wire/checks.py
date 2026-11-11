"""One-op edits on the self-test graph: apply_edits' connect, disconnect, move and delete ops;
execute_designer_code, describe_graph, preview_node."""

import re
import time
from textwrap import dedent

from test_all_tools.common import TEST_GRAPH, Ctx, added_id, check, is_image, text


async def run(ctx: Ctx) -> None:
    """Connects the nodes and checks the other one-off edit tools on them."""
    c, G, clouds, slope, lv, out = ctx.c, ctx.G, ctx.clouds, ctx.slope, ctx.lv, ctx.out
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
    # read back: "moved" is printed from the request (REVIEW.md TST-231)
    placed = text(await c('describe_graph', G))
    at = {
        n: (x, y) for n, (x, y) in zip((clouds, slope, lv, out), ((-600, 0), (-300, 0), (0, 0), (300, 0)), strict=True)
    }
    check(
        'apply_edits',
        'move: 4 moved',
        t.count('moved') == 4
        and all(re.search(r'^\s*%s .*@\(%d,%d\)' % (n, x, y), placed, re.M) for n, (x, y) in at.items()),
        placed[:300],
    )
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
