"""Refusals and failure paths: no unload of unsaved changes, bad node ids, failed restores in
sweep_param, Designer library packages, two open graphs with one name."""

import os
import re
import time
from collections.abc import Callable
from textwrap import dedent
from typing import Any

from .common import TEST_GRAPH, Ctx, added_id, check, designer_script, helpers_source, skip, text

# what the refusal for Designer's library packages says to do (designer_helpers/core.py)
LIBRARY_WAY = (
    "With it in focus in Designer's editor (the user opens it; open_graph can't reach it), read tools work with "
    'no graph given, and snapshot_graph with no graph keeps a copy'
)


async def run(ctx: Ctx) -> None:
    c, scratch, was_running, G, lv = ctx.c, ctx.scratch, ctx.was_running, ctx.G, ctx.lv
    await check_outputsize_above_log2_is_refused(ctx)
    # the reload behind set_link_display never unloads a package with unsaved changes
    # (REVIEW.md SRV-4): a saved package, then an edit, then the helper's unload
    helpers = helpers_source()
    unsaved_sbs = os.path.join(scratch, 'unsaved_check.sbs')
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helpers
                + (
                    dedent("""
                        from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
                        pkg = _PM.newUserPackage()
                        g = SDSBSCompGraph.sNew(pkg)
                        g.setIdentifier('mcp_selftest_unsaved')
                        _PM.savePackageAs(pkg, %r)
                        g.newNode('sbs::compositing::blur')
                        try:
                            unload_package_file(%r)
                        except RuntimeError as e:
                            print('REFUSED', e)
                        still = [p for p in _PM.getUserPackages() if (p.getFilePath() or '') == %r]
                        print('STILL_OPEN=%%d' %% len(still))
                        for p in still:
                            _PM.unloadUserPackage(p)
                    """)
                )
                % (unsaved_sbs, unsaved_sbs, unsaved_sbs)
            },
        )
    )
    check(
        'set_link_display',
        'never unloads unsaved changes',
        'REFUSED' in t and 'unsaved' in t and 'STILL_OPEN=1' in t,
        t.strip()[-200:],
    )
    # apply_edits checks every node a batch names before running any op: a bad id, 'graph' where a
    # node is needed, or a ref used before its add changes nothing, not even the ops before it (as
    # delete_nodes and move_nodes did for several ids, REVIEW.md HLP-4 and HLP-31, and HLP-41)
    # each case's first op changes a fresh probe node visibly (a move, or the delete in the delete-then-use
    # case), which describe_graph shows (its position, or the node gone), so
    # a batch applied up to the bad op shows as a change; one "before" per case, so one failure
    # doesn't fail the cases after it (REVIEW.md TST-86)
    first = {'op': 'move', 'position': [100, 100]}
    cases: tuple[tuple[str, Callable[[str], list[dict[str, Any]]], str], ...] = (
        (
            'a bad id',
            lambda p: [{**first, 'node': p}, {'op': 'set', 'node': 'no_such_node', 'params': {}}],
            "node 'no_such_node' not found",
        ),
        (
            'a bad id to delete',
            lambda p: [{**first, 'node': p}, {'op': 'delete', 'node': 'no_such_node'}],
            "node 'no_such_node' not found",
        ),
        (
            "'graph' as a node to delete",
            lambda p: [{**first, 'node': p}, {'op': 'delete', 'node': 'graph'}],
            "node 'graph' not found",
        ),
        (
            "'graph' as a node to move",
            lambda p: [{**first, 'node': p}, {'op': 'move', 'node': 'graph', 'position': [0, 0]}],
            "node 'graph' not found",
        ),
        (
            "'graph' as a connect source",
            lambda p: [{**first, 'node': p}, {'op': 'connect', 'from': 'graph', 'to': p, 'input': 'input1'}],
            "node 'graph' not found",
        ),
        (
            "'graph' as a connect target",
            lambda p: [{**first, 'node': p}, {'op': 'connect', 'from': p, 'to': 'graph', 'input': 'input1'}],
            "node 'graph' not found",
        ),
        (
            "'graph' to disconnect",
            lambda p: [{**first, 'node': p}, {'op': 'disconnect', 'node': 'graph', 'input': 'input1'}],
            "node 'graph' not found",
        ),
        ('an unknown op', lambda p: [{**first, 'node': p}, {'op': 'bogus', 'node': p}], "unknown op 'bogus'"),
        (
            'a ref used before its add',
            lambda p: [
                {**first, 'node': p},
                {'op': 'set', 'node': 'later', 'params': {}},
                {'op': 'add', 'definition': 'blur', 'ref': 'later'},
            ],
            "node 'later' not found",
        ),
        # a node an earlier op of the batch deletes is gone by the time a later op uses it (REVIEW.md HLP-42)
        (
            'a node an earlier op deletes',
            lambda p: [{'op': 'delete', 'node': p}, {**first, 'node': p}],
            'deleted by op 0',
        ),
        (
            'a node deleted twice',
            lambda p: [{**first, 'node': p}, {'op': 'delete', 'node': p}, {'op': 'delete', 'node': p}],
            'deleted by op 1',
        ),
        (
            'a ref deleted, then used',
            lambda p: [
                {**first, 'node': p},
                {'op': 'add', 'definition': 'blur', 'ref': 'x'},
                {'op': 'delete', 'node': 'x'},
                {'op': 'set', 'node': 'x', 'params': {}},
            ],
            'deleted by op 2',
        ),
        # an op kind or a ref that isn't text gets the batch's own refusal (REVIEW.md HLP-43)
        (
            'a ref that is not text',
            lambda p: [{**first, 'node': p}, {'op': 'add', 'definition': 'blur', 'ref': 1}],
            'ref must be a string',
        ),
        ('an op kind that is not text', lambda p: [{**first, 'node': p}, {'op': ['set'], 'node': p}], 'unknown op'),
        # 'graph' names the graph, never a ref: the check and the run would read it differently (REVIEW.md HLP-44)
        (
            'a ref named graph',
            lambda p: [
                {**first, 'node': p},
                {'op': 'add', 'definition': 'blur', 'ref': 'graph'},
                {'op': 'delete', 'node': 'graph'},
                {'op': 'set', 'node': 'graph', 'params': {}},
            ],
            "ref 'graph' is reserved",
        ),
        # a position that isn't two numbers: the add created its node before reading it, and left it
        # (REVIEW.md HLP-46); a move failed partway
        (
            'a malformed position in an add op',
            lambda p: [{**first, 'node': p}, {'op': 'add', 'definition': 'blur', 'position': [100]}],
            'position',
        ),
        (
            'a malformed position in a bitmap op',
            lambda p: [{**first, 'node': p}, {'op': 'bitmap', 'path': '/no/such.png', 'position': 'left'}],
            'position',
        ),
        # numbers float() reads but no position can be: the node was placed, then its print failed
        # (REVIEW.md HLP-51)
        (
            'a position that is not a finite number',
            lambda p: [{**first, 'node': p}, {'op': 'add', 'definition': 'blur', 'position': ['nan', 0]}],
            'position',
        ),
        (
            'an infinite position in a move op',
            lambda p: [{**first, 'node': p}, {'op': 'move', 'node': p, 'position': [0, '1e400']}],
            'position',
        ),
        (
            'a malformed position in a move op',
            lambda p: [{**first, 'node': p}, {'op': 'move', 'node': p, 'position': [1, 'x']}],
            'position',
        ),
        # only 'graph' names the graph; an empty node isn't one (REVIEW.md HLP-45)
        (
            'an empty node in a set op',
            lambda p: [{**first, 'node': p}, {'op': 'set', 'node': '', 'params': {}}],
            "node '' not found",
        ),
    )

    def node_ids(t: str) -> set[str]:
        return {l.split()[0] for l in t.splitlines() if l.split() and l.split()[0].isdigit()}

    for name, ops, bad in cases:
        r_had = await c('describe_graph', {'limit': 1000, **G})
        # a failed describe gives no ids: then the cleanup deletes the probe only, not the whole graph
        # (REVIEW.md TST-89)
        had = None if r_had.is_error else node_ids(text(r_had))
        probe = added_id(
            text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [900, 900]}], **G}))
        )
        try:
            graph_before = text(await c('describe_graph', {'include_params': True, **G}))
            r_ = await c('apply_edits', {'ops': ops(probe), **G})
            graph_after = text(await c('describe_graph', {'include_params': True, **G}))
            check(
                'apply_edits',
                '%s: refused before any op runs, nothing changed' % name,
                r_.is_error and bad in text(r_) and 'nothing was applied' in text(r_) and graph_after == graph_before,
                text(r_).strip()[-150:],
            )
        finally:
            # the probe, and whatever a broken pre-check let a batch add
            r_now = await c('describe_graph', {'limit': 1000, **G})
            new = node_ids(text(r_now)) - had if had is not None and not r_now.is_error else {probe}
            await c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in sorted(new)], **G})
    # nor for the tools that need a node: a clear refusal, nothing changed (REVIEW.md HLP-41)
    refused = "node 'graph' not found"

    def comments(t: str) -> int:
        m = re.search(r'comments: (\d+)', t)
        return int(m.group(1)) if m else 0

    r_ = await c(
        'apply_edits',
        {'ops': [{'op': 'expose', 'node': 'graph', 'param': '$randomseed', 'input_id': 'hlp41_probe'}], **G},
    )
    t = text(await c('list_graph_inputs', G))
    check(
        'apply_edits',
        "expose: node 'graph' is refused, no graph input left",
        r_.is_error and refused in text(r_) and 'hlp41_probe' not in t,
        text(r_).strip()[-100:],
    )
    if 'hlp41_probe' in t:
        await c('remove_graph_input', {'input_id': 'hlp41_probe', **G})
    for tool, args in (
        ('preview_node', {'node_id': 'graph'}),
        ('node_stats', {'node_id': 'graph'}),
        ('open_graph', {'node_id': 'graph'}),
    ):
        r_ = await c(tool, {**args, 'graph': TEST_GRAPH})
        check(tool, "node_id 'graph' is refused", r_.is_error and refused in text(r_), text(r_).strip()[-120:])
    comments_before = comments(text(await c('describe_graph', G)))
    r_ = await c('add_comment', {'text': 'hlp41', 'node_id': 'graph', **G})
    after = comments(text(await c('describe_graph', G)))
    check(
        'add_comment',
        "node_id 'graph' is refused, no comment added",
        r_.is_error and refused in text(r_) and after == comments_before,
        text(r_).strip()[-100:] + ' | comments %d -> %d' % (comments_before, after),
    )
    r_ = await c('sweep_param', {'node_id': ctx.clouds, 'param': 'scale', 'values': [7], 'view_node': 'graph', **G})
    check('sweep_param', "view_node 'graph' is refused", r_.is_error and refused in text(r_), text(r_).strip()[-120:])
    # an empty node_id is no name for the graph either, as in apply_edits' set op (REVIEW.md HLP-45)
    r_ = await c('sweep_param', {'node_id': '', 'param': 'scale', 'values': [7], 'view_node': ctx.clouds, **G})
    check(
        'sweep_param',
        'an empty node_id is refused, not read as the graph',
        r_.is_error and "node '' not found" in text(r_),
        text(r_).strip()[-120:],
    )
    # a failed restore in sweep_param still restores the inheritance and keeps the first
    # error (REVIEW.md HLP-7): setPropertyValue made to fail when it puts the original back
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helpers
                + (
                    dedent("""
                        from sd.api.sdnode import SDNode
                        from sd.api.sdproperty import SDPropertyInheritanceMethod
                        g = find_graph(%r); n = g.getNodeFromId(%r)
                        p = n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)
                        before = n.getPropertyInheritanceMethod(p).name; orig = n.getPropertyValue(p).get()
                        real = SDNode.setPropertyValue
                        def failing(self, prop, value):
                            v = value.get()
                            if prop.getId() == '$outputsize' and (v.x, v.y) == (orig.x, orig.y):
                                raise RuntimeError('restore failed on purpose')
                            return real(self, prop, value)
                        SDNode.setPropertyValue = failing
                        try:
                            sweep_param(%r, %r, '$outputsize', [[10, 10]], %r, None, None)
                        except Exception as e:
                            print('ERROR=' + str(e))
                        finally:
                            SDNode.setPropertyValue = real
                            real(n, p, n.getPropertyValue(p).__class__.sNew(orig))
                        print('INHERIT before=%%s after=%%s' %% (before, n.getPropertyInheritanceMethod(p).name))
                        n.setPropertyInheritanceMethod(p, getattr(SDPropertyInheritanceMethod, before))""")
                )
                % (TEST_GRAPH, lv, TEST_GRAPH, lv, os.path.join(scratch, 'sweep_restore'))
            },
        )
    )
    inh = re.search(r'INHERIT before=(\w+) after=(\w+)', t)
    check(
        'sweep_param',
        'a failed restore still restores the inheritance',
        'restore failed on purpose' in t and inh is not None and inh.group(1) == inh.group(2),
        t.strip()[-200:],
    )
    # and the other way round: the inheritance goes back first (HLP-26), so when that fails the
    # value must still come back (REVIEW.md TST-41); a relative size with offset 1 to tell
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helpers
                + (
                    dedent("""
                        from sd.api.sdnode import SDNode
                        from sd.api.sdproperty import SDPropertyInheritanceMethod as IM
                        from sd.api.sdvalueint2 import SDValueInt2
                        from sd.api.sdbasetypes import int2
                        g = find_graph(%r); n = g.getNodeFromId(%r)
                        p = n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)
                        before = n.getPropertyInheritanceMethod(p)
                        n.setPropertyInheritanceMethod(p, IM.RelativeToParent); n.setPropertyValue(p, SDValueInt2.sNew(int2(1, 1)))
                        owner = next(k for k in type(n).__mro__ if 'setPropertyInheritanceMethod' in k.__dict__)
                        real = owner.setPropertyInheritanceMethod
                        def failing(self, prop, method):
                            if prop.getId() == '$outputsize' and method == IM.RelativeToParent:
                                raise RuntimeError('inheritance restore failed on purpose')
                            return real(self, prop, method)
                        owner.setPropertyInheritanceMethod = failing
                        try:
                            sweep_param(%r, %r, '$outputsize', [[10, 10]], %r, None, None)
                        except Exception as e:
                            print('ERROR=' + str(e))
                        finally:
                            owner.setPropertyInheritanceMethod = real
                            v = n.getPropertyValue(p).get(); print('VALUE=%%d,%%d' %% (v.x, v.y))
                            n.setPropertyInheritanceMethod(p, before)
                            n.setPropertyValue(p, SDValueInt2.sNew(int2(0, 0)))""")
                )
                % (TEST_GRAPH, lv, TEST_GRAPH, lv, os.path.join(scratch, 'sweep_restore2'))
            },
        )
    )
    check(
        'sweep_param',
        'a failed inheritance restore still puts the value back',
        'inheritance restore failed on purpose' in t and 'VALUE=1,1' in t,
        t.strip()[-200:],
    )
    # a Designer library package is never chosen for saving (REVIEW.md HLP-10): by its path,
    # or as the graph in the editor; nothing is saved here, only the lookup is asked
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helpers
                + (
                    dedent("""
                        lib = next(p for p in _PM.getUserPackages() if _is_library_package(p))
                        for how in ('path', 'editor'):
                            try:
                                if how == 'path':
                                    pkg, _ = _package_of(lib.getFilePath())
                                else:
                                    _current_graph = lambda: lib.getChildrenResources(False)[0]
                                    pkg, _ = _package_of(None)
                                print(how.upper() + '=CHOSEN' if _is_library_package(pkg) else how.upper() + '=OTHER')
                            except RuntimeError as e:
                                print(how.upper() + '=REFUSED', e)
                    """)
                )
            },
        )
    )
    check(
        'save_package',
        'never picks a Designer library package',
        'PATH=REFUSED' in t and 'EDITOR=REFUSED' in t,
        t.strip()[-200:],
    )
    # and the refusal doesn't suggest save_as, which is refused too (REVIEW.md HLP-14), and
    # says to have the graph open first, since snapshot_graph can't find a library graph by
    # name (HLP-18)
    check(
        'save_package',
        'the library refusal points to a way that works',
        'save_as' not in t and LIBRARY_WAY in t,
        t.strip()[-200:],
    )
    # ...and that way works: a library graph open in the editor, snapshot_graph with no graph
    # (REVIEW.md HLP-20). Only in a Designer the self-test started: there is no API to close
    # the library graph's tab again, so it isn't left in yours (TST-27)
    if was_running:
        skip(
            'save_package',
            'a package in a subfolder of the library folder is a library package',
            'it loads and unloads a library package, which may be in use in your Designer',
        )
        skip(
            'snapshot_graph',
            'snapshots a library graph open in the editor, with no graph given',
            "it opens a library graph in an editor tab, which can't be closed again from code",
        )
    else:
        # a package in a subfolder of `packages` is Designer's own too, and refused by name (REVIEW.md HLP-57). Loaded
        # and unloaded here, so not in your Designer, where that package may be in use (TST-111)
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': helpers
                    + (
                        dedent("""
                            from sd.api.sdapplication import SDApplicationPath as _Paths
                            root = os.path.join(_APP.getPath(_Paths.DefaultResourcesDir), 'packages')
                            path = next(os.path.join(d, f) for d, _, fs in sorted(os.walk(root)) if d != root for f in sorted(fs) if f.endswith('.sbs'))
                            had = [p for p in _PM.getUserPackages() if p.getFilePath() == path]
                            pkg = had[0] if had else _PM.loadUserPackage(path)
                            try:
                                print('SUBFOLDER=' + os.path.relpath(path, root))
                                print('LIBRARY=' + str(_is_library_package(pkg)))
                                name = next(r.getIdentifier() for r in pkg.getChildrenResources(True) if isinstance(r, SDSBSCompGraph))
                                try:
                                    find_graph(name)
                                    print('BY_NAME=found')
                                except RuntimeError as e:
                                    print('BY_NAME=' + str(e))
                            finally:
                                if not had:
                                    _PM.unloadUserPackage(pkg)
                        """)
                    )
                },
            )
        )
        check(
            'save_package',
            'a package in a subfolder of the library folder is a library package',
            os.sep in t.split('SUBFOLDER=')[-1].splitlines()[0] and 'LIBRARY=True' in t and LIBRARY_WAY in t,
            t.strip()[-300:],
        )
        # the refusal says open_graph can't open it, so the user does (below, code stands in for the user):
        # each tool refuses by name, with that same way (ROADMAP item 27). bevel.sbs is loaded by now
        # (describe_node)
        for tool, args in (('open_graph', {'graph': 'bevel'}), ('snapshot_graph', {'graph': 'bevel', 'label': 'x'})):
            r_ = await c(tool, args)
            check(
                tool,
                'refuses a library graph by name, saying what works',
                r_.is_error and LIBRARY_WAY in text(r_),
                text(r_).strip()[-200:],
            )
            if not r_.is_error and 'saved: ' in text(r_):  # a regression: don't leave its snapshot behind
                wrong = text(r_).split('saved: ', 1)[1].strip().splitlines()[0]
                for leftover in (wrong, wrong + '.json'):
                    if os.path.isfile(leftover):
                        os.remove(leftover)
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': helpers
                    + (
                        dedent("""
                            lib = next(p for p in _PM.getUserPackages() if _is_library_package(p))
                            lg = next(r for r in lib.getChildrenResources(False) if isinstance(r, SDSBSCompGraph))
                            _APP.getUIMgr().openResourceInEditor(lg)
                            _process_events()
                            print('LIBRARY_GRAPH=' + lg.getIdentifier())""")
                    )
                },
            )
        )
        lib_graph = re.search(r'LIBRARY_GRAPH=(\S+)', t)
        lib_snapshot = await c('snapshot_graph', {'label': 'library graph check'})
        check(
            'snapshot_graph',
            'snapshots a library graph open in the editor, with no graph given',
            lib_graph is not None and not lib_snapshot.is_error and 'saved: ' in text(lib_snapshot),
            text(lib_snapshot).strip()[-150:],
        )
        # no tool edits it: Designer would take the edit, and graphs using it would see it (REVIEW.md HLP-55).
        # Every call goes to the editor's graph, the library one
        lib_state = dedent("""\
            import sd
            g = sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()
            print('STATE', g.getIdentifier(), len(g.getNodes()), g.getPackage().isModified())""")
        state = text(await c('execute_designer_code', {'code': lib_state}))
        edits: list[tuple[str, dict[str, Any]]] = [
            ('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels'}]}),
            ('arrange_graph', {}),
            ('add_frame', {'node_ids': ['1'], 'title': 'x'}),
            ('add_comment', {'text': 'x', 'position': [0, 0]}),
            ('set_graph_size', {'size_log2': 9}),
            ('remove_graph_input', {'input_id': 'x'}),
            ('sweep_param', {'node_id': '1', 'param': 'x', 'values': [1]}),
        ]
        for tool, edit in edits:
            r_ = await c(tool, edit)
            check(
                tool, 'refuses a library graph in the editor', r_.is_error and LIBRARY_WAY in text(r_), text(r_)[-200:]
            )
        lib_after = text(await c('execute_designer_code', {'code': lib_state}))
        check(
            'apply_edits',
            'a library graph in the editor stays as it was',
            'STATE' in state and 'False' in state and state == lib_after,
            state + ' -> ' + lib_after,
        )
        # reading it still works, with no graph given
        r_ = await c('describe_graph', {})
        check('describe_graph', 'reads a library graph in the editor', not r_.is_error, text(r_)[:120])
        r_ = await c('export_outputs', {'output_dir': os.path.join(scratch, 'library_export')})  # REVIEW.md SRV-53
        check(
            'export_outputs',
            'exports a library graph in the editor',
            # with no graph given it could be any graph, so the result names it (REVIEW.md SRV-54)
            not r_.is_error and lib_graph is not None and "of graph '%s'" % lib_graph.group(1) in text(r_),
            text(r_)[:200],
        )
        # and set_link_display's file step refuses it: the edit would go into Designer's install
        # folder (REVIEW.md HLP-33)
        # save=False: the refusal comes first, and a regression must not save a library file (TST-69)
        t = text(await c('execute_designer_code', {'code': helpers + '\npackage_file_of(None, save=False)'}))
        check(
            'set_link_display',
            "never edits a library graph's file",
            'ERROR' in t and 'library' in t and LIBRARY_WAY in t,
            t.strip()[-150:],
        )
        # delete only this snapshot, and its folder only if nothing else is in it: the user may
        # have snapshots of a graph with the same name (REVIEW.md TST-26)
        if not lib_snapshot.is_error and 'saved: ' in text(lib_snapshot):
            lib_snap = text(lib_snapshot).split('saved: ', 1)[1].strip().splitlines()[0]
            for leftover in (lib_snap, lib_snap + '.json'):  # the snapshot and its package note
                if os.path.isfile(leftover):
                    os.remove(leftover)
            if os.path.isdir(os.path.dirname(lib_snap)) and not os.listdir(os.path.dirname(lib_snap)):
                os.rmdir(os.path.dirname(lib_snap))
        await c('open_graph', G)
    # a package using a never-saved one: Designer would open a modal dialog and wait for a person, so the tools refuse
    # first (REVIEW.md SRV-60). The tools are called only once the helper refuses, which guards a broken helper; a save
    # path without its call would still open the dialog here, so run the unit tests first (test_unsaved_dependency.py;
    # TST-116). Two packages of the self-test's own, unloaded by CLEAN
    host_sbs, dep_sbs = os.path.join(scratch, 'uses_unsaved.sbs'), os.path.join(scratch, 'was_unsaved.sbs')
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helpers
                + (
                    dedent("""
                        dep = SDSBSCompGraph.sNew(_PM.newUserPackage())
                        dep.setIdentifier('mcp_selftest_dep')
                        host = SDSBSCompGraph.sNew(_PM.newUserPackage())
                        host.setIdentifier('mcp_selftest_host')
                        _PM.savePackageAs(host.getPackage(), %r)
                        host.newInstanceNode(dep)
                        try:
                            _refuse_unsaved_dependencies(host.getPackage())
                            print('NOT_REFUSED')
                        except RuntimeError as e:
                            print('REFUSES=' + str(e))
                    """)
                )
                % host_sbs
            },
        )
    )
    refuses = 'REFUSES=' in t
    check('save_package', 'finds a dependency never saved', refuses and "'mcp_selftest_dep'" in t, t.strip()[-200:])
    if refuses:
        host = {'graph': 'mcp_selftest_host'}
        calls: list[tuple[str, dict[str, Any]]] = [
            ('save_package', {'graph_or_path': 'mcp_selftest_host'}),
            ('snapshot_graph', {**host, 'label': 'unsaved dependency'}),
            ('diff_graph', {**host, 'against': 'saved'}),
            ('set_link_display', {**host, 'from_nodes': ['1']}),
        ]
        for tool, args in calls:
            r_ = await c(tool, args)
            check(tool, 'refuses a dependency never saved', r_.is_error and 'never saved' in text(r_), text(r_)[-250:])
        folder = os.path.join(
            os.environ.get('SD_SNAPSHOT_DIR') or os.path.expanduser('~/.sd_mcp/snapshots'), 'mcp_selftest_host'
        )
        if os.path.isdir(folder) and not os.listdir(folder):
            os.rmdir(folder)
        # and what the refusal says to do works
        await c('save_package', {'graph_or_path': 'mcp_selftest_dep', 'save_as': dep_sbs})
        r_ = await c('save_package', {'graph_or_path': 'mcp_selftest_host'})
        check(
            'save_package',
            'saves once the dependency has a file',
            not r_.is_error and 'saved' in text(r_),
            text(r_)[-200:],
        )
    # what can be measured with no save, and only in a Designer the self-test started, since a closed package stays
    # loaded behind the scenes (REVIEW.md HLP-67, HLP-68): each state's refusal, or none
    if not was_running:
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': helpers
                    + (
                        dedent("""
                            def refused(pkg):
                                try:
                                    _refuse_unsaved_dependencies(pkg)
                                    return 'SAVES'
                                except RuntimeError as e:
                                    return str(e)
                            def graph(name, pkg=None):
                                p = pkg or _PM.newUserPackage()
                                g = SDSBSCompGraph.sNew(p)
                                g.setIdentifier(name)
                                return p, g
                            own, a = graph('mcp_selftest_own_a')
                            b = graph('mcp_selftest_own_b', own)[1]
                            a.newInstanceNode(b)
                            print('OWN=' + refused(own))
                            dep, dg = graph('mcp_selftest_closed')
                            host, hg = graph('mcp_selftest_closed_host')
                            n = hg.newInstanceNode(dg)
                            print('OPEN=' + refused(host))
                            _PM.unloadUserPackage(dep)
                            print('CLOSED=' + refused(host))
                            hg.deleteNode(n)
                            print('DELETED=' + refused(host))
                            for p in (own, host):
                                _PM.unloadUserPackage(p)
                        """)
                    )
                },
            )
        )
        check('save_package', 'a package instancing its own graph has no such dependency', 'OWN=SAVES' in t, t[-300:])
        check(
            'save_package',
            'an open dependency is told by name',
            "save_package('mcp_selftest_closed', save_as=...)" in t,
            t[-400:],
        )
        closed = re.search(r'CLOSED=(.*)', t)
        check(
            'save_package',
            'a closed dependency is told to delete the nodes',
            closed is not None and 'delete the nodes' in closed.group(1) and 'save_package(' not in closed.group(1),
            closed.group(1) if closed else t[-300:],
        )
        check('save_package', 'deleting the node removes the dependency', 'DELETED=SAVES' in t, t[-200:])
        # a dependency whose file is gone has a path and no package: not refused, and it saves with no dialog (measured)
        gone_dep, gone_host = os.path.join(scratch, 'gone_dep.sbs'), os.path.join(scratch, 'gone_host.sbs')
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': helpers
                    + (
                        dedent("""
                            dep = SDSBSCompGraph.sNew(_PM.newUserPackage())
                            dep.setIdentifier('mcp_selftest_gone')
                            _PM.savePackageAs(dep.getPackage(), %r)
                            host = SDSBSCompGraph.sNew(_PM.newUserPackage())
                            host.setIdentifier('mcp_selftest_gone_host')
                            host.newInstanceNode(dep)
                            _PM.savePackageAs(host.getPackage(), %r)
                            for g in (host, dep):
                                _PM.unloadUserPackage(g.getPackage())
                            os.remove(%r)
                            pkg = _PM.loadUserPackage(%r)
                            print('DEPS=%%s' %% [(os.path.basename(d.getFilePath()), d.getPackage()) for d in pkg.getDependencies()])
                            _refuse_unsaved_dependencies(pkg)
                            print('NOT_REFUSED')
                            _PM.unloadUserPackage(pkg)
                        """)
                    )
                    % (gone_dep, gone_host, gone_dep, gone_host)
                },
            )
        )
        check(
            'save_package',
            'a dependency with its file gone has no package and is not refused',
            "DEPS=[('gone_dep.sbs', None)]" in t and 'NOT_REFUSED' in t,
            t[-250:],
        )
        # the refusal's second route, for a dependency no name reaches (REVIEW.md HLP-67): two graphs of one name, the
        # dependency put in focus by code standing in for the user, then save_package with no graph, as the message
        # says. Only once the refusal gives that route, so the host's save can't open a dialog
        same_sbs, host2_sbs = os.path.join(scratch, 'same_name_dep.sbs'), os.path.join(scratch, 'same_name_host.sbs')
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': helpers
                    + (
                        dedent("""
                            name = 'mcp_selftest_same_name'
                            dep = SDSBSCompGraph.sNew(_PM.newUserPackage())
                            dep.setIdentifier(name)
                            host = SDSBSCompGraph.sNew(_PM.newUserPackage())
                            host.setIdentifier(name)
                            _PM.savePackageAs(host.getPackage(), %r)
                            host.newInstanceNode(dep)
                            _APP.getUIMgr().openResourceInEditor(host)
                            _process_events()
                            try:
                                _refuse_unsaved_dependencies(host.getPackage())
                            except RuntimeError as e:
                                print('ROUTE=' + str(e))
                            print('UID=' + dep.getPackage().getUID())
                            _APP.getUIMgr().openResourceInEditor(dep)
                            _process_events()
                            print('FOCUS=' + str(_same_graph(_current_graph(), dep)))
                        """)
                    )
                    % host2_sbs
                },
            )
        )
        route = (
            "in focus in Designer's editor" in t
            and 'with no graph' in t
            and 'save_package(' not in t.split('ROUTE=')[-1].split('UID=')[0]
        )
        check('save_package', 'one name for both: the refusal gives the in-focus route', route, t[-400:])
        check('save_package', 'that route: code can put the dependency in focus', 'FOCUS=True' in t, t[-100:])
        if route and 'FOCUS=True' in t:
            r_ = await c('save_package', {'save_as': same_sbs})
            check(
                'save_package',
                'that route: no graph, save_as saves the dependency',
                not r_.is_error and os.path.isfile(same_sbs),
                text(r_)[-200:],
            )
            r_ = await c('save_package', {'graph_or_path': host2_sbs})
            check(
                'save_package',
                'that route: then the host saves',
                not r_.is_error and 'saved' in text(r_),
                text(r_)[-200:],
            )
            await c('open_graph', G)
    # two open graphs with one name, in different packages: each helper must act on the graph
    # it was given, not on any graph with that name (REVIEW.md HLP-6)
    dup_a, dup_b = os.path.join(scratch, 'dup_a.sbs'), os.path.join(scratch, 'dup_b.sbs')
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helpers
                + (
                    dedent("""
                        from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
                        made = []
                        for path in (%r, %r):
                            pkg = _PM.newUserPackage()
                            g = SDSBSCompGraph.sNew(pkg)
                            g.setIdentifier('mcp_selftest_dup')
                            n = g.newNode('sbs::compositing::blur')
                            _PM.savePackageAs(pkg, path)
                            made.append((pkg, g, n))
                            _APP.getUIMgr().openResourceInEditor(g)
                            _process_events()
                        (pa, ga, na), (pb, gb, nb) = made
                        package_file_of(ga)
                        # B is in the editor, A isn't
                        open_graph(ga, node_id=na.getIdentifier())
                        open_graph(gb, node_id=nb.getIdentifier())
                        cur = _current_graph()
                        print('FOCUS_B=%%s' %% (cur.getPackage().getUID() == pb.getUID()))
                    """)
                )
                % (dup_a, dup_b)
            },
        )
    )
    # unloaded in a separate call, after Designer's event loop has run: both were open in
    # editor views, and an unload in the same call as the opening risks a crash (GUIDE.md,
    # Portals; after an unload in one call, Designer crashed once as the test ended, PLG-9)
    time.sleep(0.5)
    await designer_script(c, 'shared/unload_packages', paths=[dup_a, dup_b])
    found = ' | '.join(l for l in t.splitlines() if l.startswith(('OPEN=', 'FOCUS_B=', 'sd.api.')))
    check('open_graph', 'two graphs with one name: the given one is focused', 'FOCUS_B=True' in t, found)
    check(
        'set_link_display', 'two graphs with one name: only the one in the editor counts as open', 'OPEN=0' in t, found
    )
    # the same with a copy of one file (a snapshot of a saved package opened to recover): both share
    # its UID, so they must be told apart by file (REVIEW.md HLP-53)
    orig, copy = os.path.join(scratch, 'same_uid_orig.sbs'), os.path.join(scratch, 'same_uid_copy.sbs')
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helpers
                + (
                    dedent("""
                        from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
                        pkg = _PM.newUserPackage()
                        g = SDSBSCompGraph.sNew(pkg)
                        g.setIdentifier('mcp_selftest_same_uid')
                        n = g.newNode('sbs::compositing::blur')
                        _PM.savePackageAs(pkg, %r)
                        _PM.saveCopyOfPackageAs(pkg, %r)
                        cp = _PM.loadUserPackage(%r)
                        cg = cp.findResourceFromUrl("mcp_selftest_same_uid")
                        print('SAME_UID=%%s' %% (cp.getUID() == pkg.getUID()))
                        _APP.getUIMgr().openResourceInEditor(cg)
                        _process_events()
                        print('FOUND_COPY=%%s' %% (find_graph('mcp_selftest_same_uid').getPackage().getFilePath() == %r))
                        package_file_of(g)
                        # the copy is in the editor, the original isn't
                        open_graph(g, node_id=n.getIdentifier())
                        print('FOCUS_ORIG=%%s' %% (_current_graph().getPackage().getFilePath() == %r))
                    """)
                )
                % (orig, copy, copy, copy, orig)
            },
        )
    )
    time.sleep(0.5)  # unloaded in a separate call, as above
    await designer_script(c, 'shared/unload_packages', paths=[orig, copy])
    found = ' | '.join(
        l for l in t.splitlines() if l.startswith(('SAME_UID=', 'FOUND_COPY=', 'OPEN=', 'FOCUS_', 'sd.'))
    )
    check(
        'apply_edits',
        'a copy of a file in the editor is found, not the original with its UID',
        'SAME_UID=True' in t and 'FOUND_COPY=True' in t,
        found,
    )
    check('set_link_display', 'a copy of the file in the editor: the original is not open', 'OPEN=0' in t, found)
    check(
        'open_graph', 'a copy of the file in the editor: the original given is focused', 'FOCUS_ORIG=True' in t, found
    )


async def check_outputsize_above_log2_is_refused(ctx: Ctx) -> None:
    """$outputsize is log2, so a pixel count is a mistake that Designer takes silently (it computes 8192 px): every path
    that sets a size refuses above 13, a real size below 0 too, and 13 itself works. On graphs of its own, left for
    CLEAN."""
    c = ctx.c
    O, S, name = '$outputsize', '$outputsize', TEST_GRAPH + '_sizes'
    G = {'graph': name}
    await c('create_graph', {'name': name, 'size_log2': 9})

    async def refused(what: str, tool: str, args: dict[str, Any], says: str = 'log2 of the size') -> None:
        res = await c(tool, args)
        check(O, what, bool(res.is_error) and says in text(res), text(res))

    def add(size: list[int]) -> dict[str, Any]:
        return {'ops': [{'op': 'add', 'definition': 'uniform', 'ref': 'u', 'params': {S: size}}], **G}

    def set_op(target: str, params: dict[str, Any]) -> dict[str, Any]:
        return {'ops': [{'op': 'set', 'node': target, 'params': params}], **G}

    async def computed(target: str) -> str:
        return text(await c('node_stats', {'node_id': target, **G}))

    await refused('add refuses a pixel count', 'apply_edits', add([1024, 1024]))
    node = added_id(text(await c('apply_edits', add([5, 5]))))
    await refused('set refuses above 13', 'apply_edits', set_op(node, {S: [14, 14]}))
    await refused('set refuses one axis above 13', 'apply_edits', set_op(node, {S: [5, 1024]}))
    await refused('set refuses numbers sent as strings', 'apply_edits', set_op(node, {S: ['1024', '1024']}))
    await refused('set on the graph refuses', 'apply_edits', set_op('graph', {S: [1024, 1024]}))
    # set makes it Absolute, where a value below 0 computes 1 px on that axis
    await refused('add refuses a negative size', 'apply_edits', add([-1, -1]))
    await refused('set refuses a negative size', 'apply_edits', set_op(node, {S: [-1, -1]}))
    await refused('set refuses a negative axis', 'apply_edits', set_op(node, {S: [-3, 5]}))
    await refused(
        'sweep_param refuses a negative size', 'sweep_param', {'node_id': node, 'param': S, 'values': [[-1, -1]], **G}
    )
    await refused(
        'sweep_param refuses a later bad value, as an error',
        'sweep_param',
        {'node_id': node, 'param': S, 'values': [[5, 5], [1024, 1024]], **G},
    )
    await refused(
        'sweep_param refuses a pixel count', 'sweep_param', {'node_id': node, 'param': S, 'values': [[1024, 1024]], **G}
    )
    t = await computed(node)
    check(O, 'a refusal leaves the size as it was', '32x32' in t, t)
    t = text(await c('describe_graph', G))
    check(O, "a refusal leaves the graph's size as it was", '$outputsize (log2): 9 x 9' in t, t)

    # a graph input bound to it: an offset while the node's size is inherited, refused above 13 all the same
    bound = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'uniform', 'ref': 'b'}], **G})))
    expose = {'op': 'expose', 'node': bound, 'param': S, 'input_id': 'mcp_size'}
    offset = 'a log2 offset'
    await refused(
        "expose's default refuses a pixel count",
        'apply_edits',
        {'ops': [{**expose, 'default': [1024, 1024]}], **G},
        says=offset,
    )
    t = text(await c('list_graph_inputs', G))
    check(O, 'a refused expose adds no input', 'mcp_size' not in t, t)
    res = await c('apply_edits', {'ops': [{**expose, 'default': [0, 0]}], **G})
    check(O, 'an offset of 0 can be exposed', not res.is_error, text(res))
    await refused(
        'set on a bound input refuses', 'apply_edits', set_op('graph', {'mcp_size': [1024, 1024]}), says=offset
    )
    await refused(
        'set on a bound input refuses strings', 'apply_edits', set_op('graph', {'mcp_size': ['14', '14']}), says=offset
    )
    await refused(
        'sweep_param on a bound input refuses',
        'sweep_param',
        {'node_id': 'graph', 'param': 'mcp_size', 'view_node': bound, 'values': [[1, 1], [1024, 1024]], **G},
        says=offset,
    )
    res = await c('apply_edits', set_op('graph', {'mcp_size': [1, 1]}))
    check(O, 'a bound input takes a small offset', not res.is_error, text(res))
    t = await computed(bound)
    check(O, 'a bound input is an offset from the graph', '1024x1024' in t, t)
    res = await c('apply_edits', set_op('graph', {'mcp_size': [-2, -2]}))
    check(O, 'a bound input takes a negative offset', not res.is_error, text(res))
    t = await computed(bound)
    check(O, 'a negative offset makes it smaller', '128x128' in t, t)
    # the refusal for a driven size sends the agent to that input, so it says what the input means
    # worded for any function driving it: a hand-written one reaches the same refusal (REVIEW.md HLP-94)
    bound_offset = 'a graph input bound to it is a log2 offset'
    await refused(
        'set on a driven size says its input is an offset',
        'apply_edits',
        set_op(bound, {S: [11, 11]}),
        says=bound_offset,
    )
    await refused(
        'sweep_param on a driven size says its input is an offset',
        'sweep_param',
        {'node_id': bound, 'param': S, 'values': [[11, 11]], **G},
        says=bound_offset,
    )

    # bound to a node at Absolute the value is a size, so the size's wording and lower limit
    fixed = added_id(text(await c('apply_edits', add([5, 5]))))
    fixed_input = {'op': 'expose', 'node': fixed, 'param': S, 'input_id': 'mcp_fixed'}
    await refused(
        "expose's default on an Absolute node refuses a negative size",
        'apply_edits',
        {'ops': [{**fixed_input, 'default': [-1, -1]}], **G},
    )
    res = await c('apply_edits', {'ops': [{**fixed_input, 'default': [2, 2]}], **G})
    check(O, 'an Absolute node can be exposed', not res.is_error, text(res))
    await refused('a size input refuses above 13', 'apply_edits', set_op('graph', {'mcp_fixed': [14, 14]}))
    await refused('a size input refuses a negative size', 'apply_edits', set_op('graph', {'mcp_fixed': [-1, -1]}))
    res = await c('apply_edits', set_op(fixed, {S: [3, 3]}))
    check(
        O,
        'a driven Absolute size is not called an offset',
        bool(res.is_error) and 'is driven by' in text(res) and 'log2 offset' not in text(res),
        text(res),
    )

    # bound to the graph's own $outputsize, which only the saved file shows
    base = TEST_GRAPH + '_sizes_base'
    await designer_script(
        c, 'shared/graph_parameter_function', identifier=base, path=os.path.join(ctx.scratch, base + '.sbs')
    )
    base_set = {'ops': [{'op': 'set', 'node': 'graph', 'params': {'size_in': [1024, 1024]}}], 'graph': base}
    saved_text = "as last saved it drives $outputsize of the graph it belongs to; save that graph's package"
    await refused("an input bound to the graph's own size refuses", 'apply_edits', base_set, says=saved_text)

    # an instance's parameter that only binds a $outputsize inside its graph
    inner, outer = TEST_GRAPH + '_sizes_inner', TEST_GRAPH + '_sizes_outer'
    await c('create_graph', {'name': inner, 'size_log2': 9})
    source = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'uniform'}], 'graph': inner})))
    sink = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'output'}], 'graph': inner})))
    await c(
        'apply_edits',
        {
            'ops': [
                {'op': 'connect', 'from': source, 'to': sink, 'input': 'inputNodeOutput'},
                {'op': 'expose', 'node': source, 'param': S, 'input_id': 'size_in', 'default': [0, 0]},
            ],
            'graph': inner,
        },
    )
    made = dedent("""\
        import sd
        from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
        pm=sd.getContext().getSDApplication().getPackageMgr()
        inner=[r for p in pm.getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]
        outer=SDSBSCompGraph.sNew(inner.getPackage()); outer.setIdentifier('%s')
        print('ID='+outer.newInstanceNode(inner).getIdentifier())""") % (inner, outer)
    instance = text(await c('execute_designer_code', {'code': made})).split('ID=')[1].split()[0]
    Outer = {'graph': outer}
    instance_set = {'op': 'set', 'node': instance}
    await refused(
        "set on an instance's parameter bound to a size refuses",
        'apply_edits',
        {'ops': [{**instance_set, 'params': {'size_in': [1024, 1024]}}], **Outer},
        says=offset,
    )
    await refused(
        "sweep_param on an instance's parameter bound to a size refuses",
        'sweep_param',
        {'node_id': instance, 'param': 'size_in', 'values': [[1024, 1024]], **Outer},
        says=offset,
    )
    res = await c('apply_edits', {'ops': [{**instance_set, 'params': {'size_in': [1, 1]}}], **Outer})
    check(O, "an instance's parameter takes a small offset", not res.is_error, text(res))
    t = text(await c('node_stats', {'node_id': instance, **Outer}))
    check(O, "an instance's parameter is an offset inside its graph", '1024x1024' in t, t)
    exposed = {'op': 'expose', 'node': instance, 'param': 'size_in', 'input_id': 'mcp_outer'}
    await refused(
        "expose's default on an instance's parameter bound to a size refuses",
        'apply_edits',
        {'ops': [{**exposed, 'default': [1024, 1024]}], **Outer},
        says=offset,
    )
    res = await c('apply_edits', {'ops': [{**exposed, 'default': [1, 1]}], **Outer})
    check(O, "expose's default on an instance's parameter takes a small offset", not res.is_error, text(res))

    # a refused sweep_param must not touch a saved package
    saved = TEST_GRAPH + '_sizes_saved'
    await c('create_graph', {'name': saved, 'save_path': os.path.join(ctx.scratch, saved + '.sbs'), 'size_log2': 9})
    saved_node = added_id(
        text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'uniform', 'ref': 'u'}], 'graph': saved}))
    )
    await c('save_package', {'graph_or_path': saved})
    modified = (
        dedent("""\
        import sd
        pm=sd.getContext().getSDApplication().getPackageMgr()
        print('MODIFIED', [p.isModified() for p in pm.getUserPackages()
            if any(r.getIdentifier()=='%s' for r in p.getChildrenResources(False))])""")
        % saved
    )
    t = text(await c('execute_designer_code', {'code': modified}))
    check(O, 'the saved package starts unmodified', 'MODIFIED [False]' in t, t)
    await refused(
        'sweep_param refuses on a saved package',
        'sweep_param',
        {'node_id': saved_node, 'param': S, 'values': [[1024, 1024]], 'graph': saved},
    )
    t = text(await c('execute_designer_code', {'code': modified}))
    check(O, 'a refused sweep_param leaves a saved package unmodified', 'MODIFIED [False]' in t, t)

    # the two tools that take size_log2 report 2**size_log2, which is not what 14 computes
    for size in (14, -1):
        await refused(
            'create_graph refuses %d' % size, 'create_graph', {'name': TEST_GRAPH + '_toolarge', 'size_log2': size}
        )
    res = await c('describe_graph', {'graph': TEST_GRAPH + '_toolarge'})
    check(O, 'a refused create_graph makes no graph', bool(res.is_error) and 'open graphs' not in text(res), text(res))
    for overridable in (False, True):
        for size in (14, -1):
            await refused(
                'set_graph_size refuses %d (overridable=%s)' % (size, overridable),
                'set_graph_size',
                {'size_log2': size, 'overridable': overridable, **G},
            )
    t = text(await c('describe_graph', G))
    check(O, "a refused set_graph_size leaves the graph's size", '$outputsize (log2): 9 x 9' in t, t)
    res = await c('set_graph_size', {'size_log2': 13, 'overridable': False, **G})
    check(O, 'set_graph_size accepts 13', not res.is_error and '8192 px' in text(res), text(res))

    await c('set_graph_size', {'size_log2': 11, 'overridable': True, **G})
    t = text(await c('describe_graph', G))
    check(O, 'an overridable graph shows an offset of 0', '$outputsize (log2): 0 x 0' in t, t)

    res = await c('apply_edits', set_op(node, {S: [13, 13]}))
    check(O, '13 is accepted', not res.is_error, text(res))
    t = await computed(node)
    check(O, '13 computes 8192 px', '8192x8192' in t, t)
