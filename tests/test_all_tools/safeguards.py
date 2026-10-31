"""Refusals and failure paths: no unload of unsaved changes, bad node ids, failed restores in
sweep_param, Designer library packages, two open graphs with one name."""

import os
import re
import time
from collections.abc import Callable
from typing import Any

from .common import TEST_GRAPH, Ctx, added_id, check, helpers_source, skip, text


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
    # says to open the graph first, since snapshot_graph can't find a library graph by
    # name (HLP-18)
    check(
        'save_package',
        'the library refusal points to a way that works',
        'save_as' not in t and 'open it in the editor' in t and 'snapshot_graph with no graph' in t,
        t.strip()[-200:],
    )
    # ...and that way works: a library graph open in the editor, snapshot_graph with no graph
    # (REVIEW.md HLP-20). Only in a Designer the self-test started: there is no API to close
    # the library graph's tab again, so it isn't left in yours (TST-27)
    if was_running:
        skip(
            'snapshot_graph',
            'snapshots a library graph open in the editor, with no graph given',
            "it opens a library graph in an editor tab, which can't be closed again from code",
        )
    else:
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
        r_ = await c('snapshot_graph', {'label': 'library graph check'})
        check(
            'snapshot_graph',
            'snapshots a library graph open in the editor, with no graph given',
            lib_graph is not None and not r_.is_error and 'saved: ' in text(r_),
            text(r_).strip()[-150:],
        )
        # and set_link_display's file step refuses it: the edit would go into Designer's install
        # folder (REVIEW.md HLP-33)
        # save=False: the refusal comes first, and a regression must not save a library file (TST-69)
        t = text(await c('execute_designer_code', {'code': helpers + '\npackage_file_of(None, save=False)'}))
        check(
            'set_link_display', "never edits a library graph's file", 'ERROR' in t and 'library' in t, t.strip()[-150:]
        )
        # delete only this snapshot, and its folder only if nothing else is in it: the user may
        # have snapshots of a graph with the same name (REVIEW.md TST-26)
        if not r_.is_error and 'saved: ' in text(r_):
            lib_snap = text(r_).split('saved: ', 1)[1].strip().splitlines()[0]
            if os.path.isfile(lib_snap):
                os.remove(lib_snap)
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
