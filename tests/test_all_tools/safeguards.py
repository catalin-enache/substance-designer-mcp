"""Refusals and failure paths: no unload of unsaved changes, bad node ids, failed restores in
sweep_param, Designer library packages, two open graphs with one name."""

import os
import re
import time
from collections.abc import Callable
from typing import Any

from .common import TEST_GRAPH, Ctx, added_id, check, helpers_source, skip, text

# what the refusal for Designer's library packages says to do (designer_helpers/core.py)
LIBRARY_WAY = (
    "With it in focus in Designer's editor (the user opens it; open_graph can't reach it), read tools work with "
    'no graph given, and snapshot_graph with no graph keeps a copy'
)


async def run(ctx: Ctx) -> None:
    c, scratch, was_running, G, lv = ctx.c, ctx.scratch, ctx.was_running, ctx.G, ctx.lv
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
                    '\nfrom sd.api.sbs.sdsbscompgraph import SDSBSCompGraph\n'
                    "pkg = _PM.newUserPackage()\ng = SDSBSCompGraph.sNew(pkg)\ng.setIdentifier('mcp_selftest_unsaved')\n"
                    "_PM.savePackageAs(pkg, %r)\ng.newNode('sbs::compositing::blur')\n"
                    "try:\n    unload_package_file(%r)\nexcept RuntimeError as e:\n    print('REFUSED', e)\n"
                    "still = [p for p in _PM.getUserPackages() if (p.getFilePath() or '') == %r]\n"
                    "print('STILL_OPEN=%%d' %% len(still))\n"
                    'for p in still:\n    _PM.unloadUserPackage(p)\n'
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
                    '\nfrom sd.api.sdnode import SDNode\nfrom sd.api.sdproperty import SDPropertyInheritanceMethod\n'
                    "g = find_graph(%r); n = g.getNodeFromId(%r)\np = n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
                    'before = n.getPropertyInheritanceMethod(p).name; orig = n.getPropertyValue(p).get()\n'
                    'real = SDNode.setPropertyValue\n'
                    'def failing(self, prop, value):\n'
                    '    v = value.get()\n'
                    "    if prop.getId() == '$outputsize' and (v.x, v.y) == (orig.x, orig.y):\n"
                    "        raise RuntimeError('restore failed on purpose')\n"
                    '    return real(self, prop, value)\n'
                    'SDNode.setPropertyValue = failing\n'
                    "try:\n    sweep_param(%r, %r, '$outputsize', [[10, 10]], %r, None, None)\n"
                    "except Exception as e:\n    print('ERROR=' + str(e))\n"
                    'finally:\n    SDNode.setPropertyValue = real\n'
                    '    real(n, p, n.getPropertyValue(p).__class__.sNew(orig))\n'
                    "print('INHERIT before=%%s after=%%s' %% (before, n.getPropertyInheritanceMethod(p).name))\n"
                    'n.setPropertyInheritanceMethod(p, getattr(SDPropertyInheritanceMethod, before))'
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
                    '\nfrom sd.api.sdnode import SDNode\nfrom sd.api.sdproperty import SDPropertyInheritanceMethod as IM\n'
                    'from sd.api.sdvalueint2 import SDValueInt2\nfrom sd.api.sdbasetypes import int2\n'
                    "g = find_graph(%r); n = g.getNodeFromId(%r)\np = n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
                    'before = n.getPropertyInheritanceMethod(p)\n'
                    'n.setPropertyInheritanceMethod(p, IM.RelativeToParent); n.setPropertyValue(p, SDValueInt2.sNew(int2(1, 1)))\n'
                    "owner = next(k for k in type(n).__mro__ if 'setPropertyInheritanceMethod' in k.__dict__)\n"
                    'real = owner.setPropertyInheritanceMethod\n'
                    'def failing(self, prop, method):\n'
                    "    if prop.getId() == '$outputsize' and method == IM.RelativeToParent:\n"
                    "        raise RuntimeError('inheritance restore failed on purpose')\n"
                    '    return real(self, prop, method)\n'
                    'owner.setPropertyInheritanceMethod = failing\n'
                    "try:\n    sweep_param(%r, %r, '$outputsize', [[10, 10]], %r, None, None)\n"
                    "except Exception as e:\n    print('ERROR=' + str(e))\n"
                    'finally:\n    owner.setPropertyInheritanceMethod = real\n'
                    "    v = n.getPropertyValue(p).get(); print('VALUE=%%d,%%d' %% (v.x, v.y))\n"
                    '    n.setPropertyInheritanceMethod(p, before)\n'
                    '    n.setPropertyValue(p, SDValueInt2.sNew(int2(0, 0)))'
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
                    '\nlib = next(p for p in _PM.getUserPackages() if _is_library_package(p))\n'
                    "for how in ('path', 'editor'):\n"
                    '    try:\n'
                    "        if how == 'path':\n            pkg, _ = _package_of(lib.getFilePath())\n"
                    '        else:\n            _current_graph = lambda: lib.getChildrenResources(False)[0]\n'
                    '            pkg, _ = _package_of(None)\n'
                    "        print(how.upper() + '=CHOSEN' if _is_library_package(pkg) else how.upper() + '=OTHER')\n"
                    "    except RuntimeError as e:\n        print(how.upper() + '=REFUSED', e)\n"
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
                        '\nfrom sd.api.sdapplication import SDApplicationPath as _Paths\n'
                        "root = os.path.join(_APP.getPath(_Paths.DefaultResourcesDir), 'packages')\n"
                        "path = next(os.path.join(d, f) for d, _, fs in sorted(os.walk(root)) if d != root for f in sorted(fs) if f.endswith('.sbs'))\n"
                        'had = [p for p in _PM.getUserPackages() if p.getFilePath() == path]\n'
                        'pkg = had[0] if had else _PM.loadUserPackage(path)\n'
                        'try:\n'
                        "    print('SUBFOLDER=' + os.path.relpath(path, root))\n"
                        "    print('LIBRARY=' + str(_is_library_package(pkg)))\n"
                        '    name = next(r.getIdentifier() for r in pkg.getChildrenResources(True) if isinstance(r, SDSBSCompGraph))\n'
                        '    try:\n'
                        '        find_graph(name)\n'
                        "        print('BY_NAME=found')\n"
                        '    except RuntimeError as e:\n'
                        "        print('BY_NAME=' + str(e))\n"
                        'finally:\n'
                        '    if not had:\n'
                        '        _PM.unloadUserPackage(pkg)\n'
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
                        '\nlib = next(p for p in _PM.getUserPackages() if _is_library_package(p))\n'
                        'lg = next(r for r in lib.getChildrenResources(False) if isinstance(r, SDSBSCompGraph))\n'
                        '_APP.getUIMgr().openResourceInEditor(lg)\n_process_events()\n'
                        "print('LIBRARY_GRAPH=' + lg.getIdentifier())"
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
        lib_state = (
            'import sd\ng = sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()\n'
            "print('STATE', g.getIdentifier(), len(g.getNodes()), g.getPackage().isModified())"
        )
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
    # two open graphs with one name, in different packages: each helper must act on the graph
    # it was given, not on any graph with that name (REVIEW.md HLP-6)
    dup_a, dup_b = os.path.join(scratch, 'dup_a.sbs'), os.path.join(scratch, 'dup_b.sbs')
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helpers
                + (
                    '\nfrom sd.api.sbs.sdsbscompgraph import SDSBSCompGraph\n'
                    'made = []\n'
                    'for path in (%r, %r):\n'
                    '    pkg = _PM.newUserPackage()\n    g = SDSBSCompGraph.sNew(pkg)\n'
                    "    g.setIdentifier('mcp_selftest_dup')\n    n = g.newNode('sbs::compositing::blur')\n"
                    '    _PM.savePackageAs(pkg, path)\n    made.append((pkg, g, n))\n'
                    '    _APP.getUIMgr().openResourceInEditor(g)\n    _process_events()\n'
                    '(pa, ga, na), (pb, gb, nb) = made\n'
                    'package_file_of(ga)\n'  # B is in the editor, A isn't
                    'open_graph(ga, node_id=na.getIdentifier())\n'
                    'open_graph(gb, node_id=nb.getIdentifier())\n'
                    'cur = _current_graph()\n'
                    "print('FOCUS_B=%%s' %% (cur.getPackage().getUID() == pb.getUID()))\n"
                )
                % (dup_a, dup_b)
            },
        )
    )
    # unloaded in a separate call, after Designer's event loop has run: both were open in
    # editor views, and an unload in the same call as the opening risks a crash (AGENTS.md,
    # Portals; after an unload in one call, Designer crashed once as the test ended, PLG-9)
    time.sleep(0.5)
    await c(
        'execute_designer_code',
        {
            'code': (
                'import sd\npm = sd.getContext().getSDApplication().getPackageMgr()\n'
                'for p in list(pm.getUserPackages()):\n'
                "    if (p.getFilePath() or '') in (%r, %r):\n        pm.unloadUserPackage(p)\n"
            )
            % (dup_a, dup_b)
        },
    )
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
                    '\nfrom sd.api.sbs.sdsbscompgraph import SDSBSCompGraph\n'
                    'pkg = _PM.newUserPackage()\ng = SDSBSCompGraph.sNew(pkg)\n'
                    "g.setIdentifier('mcp_selftest_same_uid')\nn = g.newNode('sbs::compositing::blur')\n"
                    '_PM.savePackageAs(pkg, %r)\n_PM.saveCopyOfPackageAs(pkg, %r)\n'
                    'cp = _PM.loadUserPackage(%r)\ncg = cp.findResourceFromUrl("mcp_selftest_same_uid")\n'
                    "print('SAME_UID=%%s' %% (cp.getUID() == pkg.getUID()))\n"
                    '_APP.getUIMgr().openResourceInEditor(cg)\n_process_events()\n'
                    "print('FOUND_COPY=%%s' %% (find_graph('mcp_selftest_same_uid').getPackage().getFilePath() == %r))\n"
                    'package_file_of(g)\n'  # the copy is in the editor, the original isn't
                    'open_graph(g, node_id=n.getIdentifier())\n'
                    "print('FOCUS_ORIG=%%s' %% (_current_graph().getPackage().getFilePath() == %r))\n"
                )
                % (orig, copy, copy, copy, orig)
            },
        )
    )
    time.sleep(0.5)  # unloaded in a separate call, as above
    await c(
        'execute_designer_code',
        {
            'code': (
                'import sd\npm = sd.getContext().getSDApplication().getPackageMgr()\n'
                'for p in list(pm.getUserPackages()):\n'
                "    if (p.getFilePath() or '') in (%r, %r):\n        pm.unloadUserPackage(p)\n"
            )
            % (orig, copy)
        },
    )
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
