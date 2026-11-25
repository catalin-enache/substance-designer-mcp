"""set_link_display: portals and wires, by node, by link, by fan-out and by length."""

import json
import os
import re
import xml.etree.ElementTree as ET
from textwrap import dedent
from typing import cast

from test_all_tools.common import TEST_GRAPH, Ctx, added_id, check, designer_script, graph_in_editor, text

# every widget of Designer's watched for its destruction, then the package at PATH unloaded (the helpers'
# unload_package_file, as set_link_display's reload does): how many went within the call (IN_CALL)
UNLOAD_WATCHED = dedent("""
    from PySide6 import QtWidgets
    gone = []
    def seen(*args):
        gone.append(1)
    sys.mcp_selftest_gone = gone
    sys.mcp_selftest_watched = (seen, QtWidgets.QApplication.allWidgets())
    for w in sys.mcp_selftest_watched[1]:
        w.destroyed.connect(seen)
    unload_package_file(PATH)
    print('IN_CALL=%d' % len(gone))""")
GONE_SO_FAR = "import sys; print('GONE=%d' % len(sys.mcp_selftest_gone))"
# the slots disconnected from the widgets still there, and what the check kept in sys dropped (REVIEW.md TST-424)
GONE_DONE = dedent("""
    import sys, shiboken6
    seen, widgets = getattr(sys, 'mcp_selftest_watched', (None, []))
    for w in widgets:
        if shiboken6.isValid(w):
            w.destroyed.disconnect(seen)
    if hasattr(sys, 'mcp_selftest_watched'):
        del sys.mcp_selftest_watched
    if hasattr(sys, 'mcp_selftest_gone'):
        del sys.mcp_selftest_gone""")
# the package at PATH loaded again only if no copy of it is loaded: a refused unload left it there
LOAD_IF_GONE = dedent("""
    norm = os.path.normpath(PATH)
    if not any(os.path.normpath(p.getFilePath() or '') == norm for p in _PM.getUserPackages()):
        load_package_file(PATH)""")


async def check_an_unloads_widgets_are_gone_once_the_next_call_starts(ctx: Ctx) -> None:
    """An unload's widgets (the package's graph views) are destroyed within its call, or before the next call starts
    (deleted later by Qt, as the plugin runs Designer's event loop between two jobs), and as many by the call after:
    what lets set_link_display's reload, and the self-test's clean-ups, load in the next call with no pause (REVIEW.md
    SRV-150; measured 327 within the call, 177 before the next, none by the one after). The package is loaded again
    after, unless it is still loaded, and opened, as the reload does."""
    c = ctx.c
    sbs = os.path.join(ctx.scratch, TEST_GRAPH + '.sbs')
    seen: list[int] = []
    try:
        said = text(
            await c('execute_designer_code', {'code': ctx.helper_source + UNLOAD_WATCHED.replace('PATH', repr(sbs))})
        )
        by_next = text(await c('execute_designer_code', {'code': GONE_SO_FAR}))
        after = text(await c('execute_designer_code', {'code': GONE_SO_FAR}))
        seen = [int(m) for m in re.findall(r'(?:IN_CALL|GONE)=(\d+)', said + by_next + after)]
    finally:
        await c('execute_designer_code', {'code': GONE_DONE})
        await c('execute_designer_code', {'code': ctx.helper_source + LOAD_IF_GONE.replace('PATH', repr(sbs))})
        await c('open_graph', ctx.G)
    check(
        'designer facts',
        "an unload's widgets are destroyed within its call or before the next one starts, as many by the one after",
        len(seen) == 3 and 0 < seen[0] < seen[1] == seen[2],
        'destroyed within the unload, by the next call, by the one after: %s' % seen,
    )


async def run(ctx: Ctx) -> None:
    await check_an_unloads_widgets_are_gone_once_the_next_call_starts(ctx)
    c, G, clouds, lv, stats_before = ctx.c, ctx.G, ctx.clouds, ctx.lv, ctx.stats_before
    r_ = await c('set_link_display', {'mode': 'dotted', 'from_nodes': [clouds], **G})
    check('set_link_display', 'error on bad mode', r_.is_error and 'mode must be' in text(r_), text(r_))
    r_ = await c('set_link_display', {'mode': 'portal', **G})
    check('set_link_display', 'error without a selection', r_.is_error and 'choose links' in text(r_), text(r_))
    t = text(await c('set_link_display', {'mode': 'portal', 'from_nodes': [clouds], **G}))
    check('set_link_display', 'portals from a node', 'changed to portal' in t and 'reloaded' in t, t.split(';')[0])
    # the package reloads under a graph open in the editor, as a user has it, and the graph goes back there (REVIEW.md
    # TST-267: the views' tear-down and the reopen, which no check reached)
    back = await graph_in_editor(c)
    check(
        'set_link_display',
        'the graph open in the editor is back after the reload',
        back == TEST_GRAPH and 'could not reopen' not in t,
        'in the editor: %r; %s' % (back, t.split(';')[-1]),
    )
    t = text(await c('diff_graph', {'against': 'latest', **G}))
    check(
        'set_link_display',
        'diff shows display only',
        'shown as portal' in t and '0 added, 0 removed' in t,
        t.splitlines()[0],
    )
    stats_after = text(await c('node_stats', {'node_id': lv, **G}))

    # the same numbers within render noise, not the same text (two computes differ by a step or
    # two, enough to flip a printed digit; REVIEW.md TST-61)
    def nums(t_: str) -> list[float]:
        return [float(x) for x in re.findall(r'(?:min|max|mean|std) (-?[0-9.]+)', t_)]

    check(
        'set_link_display',
        'output unchanged',
        bool(nums(stats_before))
        and len(nums(stats_after)) == len(nums(stats_before))
        and max(abs(a - b) for a, b in zip(nums(stats_after), nums(stats_before), strict=False)) < 0.002,
        stats_after,
    )
    snap_dir = os.path.join(
        os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), '.sd_mcp', 'snapshots'), TEST_GRAPH
    )
    check(
        'set_link_display',
        'copies the saved file before saving over it',
        any(f.endswith('before_portals_file_on_disk.sbs') for f in os.listdir(snap_dir)),
        str(os.listdir(snap_dir)),
    )
    # and that copy's bitmap paths still lead to the files (REVIEW.md SRV-14)
    on_disk = [os.path.join(snap_dir, f) for f in os.listdir(snap_dir) if f.endswith('before_portals_file_on_disk.sbs')]
    refs = [cast(str, f.get('v')) for f in ET.parse(on_disk[0]).getroot().iter('filepath')] if on_disk else []
    missing = [r for r in refs if not os.path.isfile(os.path.join(snap_dir, r))]
    check(
        'set_link_display',
        "the saved file's copy keeps its bitmaps reachable",
        bool(refs) and not missing,
        'refs %s, missing %s' % (refs, missing),
    )
    t = text(await c('set_link_display', {'mode': 'wire', 'from_nodes': [clouds], **G}))
    check('set_link_display', 'back to wires', 'changed to wire' in t, t.split(';')[0])
    t = text(await c('set_link_display', {'mode': 'wire', 'from_nodes': [clouds], **G}))
    check('set_link_display', 'nothing to change: no save, no reload', 'nothing to do' in t, t)
    # automatic selection, as GUIDE.md recommends: clouds feeds 3 inputs once this blend is in
    tb = added_id(
        text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blend', 'position': [-400, -300]}], **G}))
    )
    for port in ('source', 'destination'):
        await c('apply_edits', {'ops': [{'op': 'connect', 'from': clouds, 'to': tb, 'input': port}], **G})
    t = text(await c('set_link_display', {'mode': 'portal', 'fanout_at_least': 3, **G}))
    check(
        'set_link_display',
        'fanout_at_least=3 to portals',
        '3 of 3 selected link(s) changed to portal' in t,
        t.split(';')[0],
    )
    t = text(await c('set_link_display', {'mode': 'wire', 'fanout_at_least': 3, **G}))
    check(
        'set_link_display',
        'fanout_at_least=3 back to wires',
        '3 of 3 selected link(s) changed to wire' in t,
        t.split(';')[0],
    )
    t = text(await c('set_link_display', {'mode': 'portal', 'links': [[lv, 'input1']], **G}))
    check(
        'set_link_display',
        'links=[[node, input]] to portal',
        '1 of 1 selected link(s) changed to portal' in t,
        t.split(';')[0],
    )
    t = text(await c('set_link_display', {'mode': 'wire', 'links': [[lv, 'input1']], **G}))
    check(
        'set_link_display',
        'links=[[node, input]] back to wire',
        '1 of 1 selected link(s) changed to wire' in t,
        t.split(';')[0],
    )
    # one of them into the levels node, at (0, 0), where Designer writes no position (ROADMAP item 63)
    t = text(await c('set_link_display', {'mode': 'portal', 'longer_than': 1, **G}))
    counts = re.search(r'(\d+) of (\d+) selected link\(s\) changed to portal in \S+ \(of (\d+) links', t)
    check(
        'set_link_display',
        'longer_than=1 picks every link',
        counts is not None and counts.group(1) == counts.group(2) == counts.group(3),
        t.split(';')[0],
    )
    await c('set_link_display', {'mode': 'wire', 'longer_than': 1, **G})
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': tb}], **G})
    await check_a_reload_clears_no_step_of_the_undo_history(ctx)
    await check_undo_edits_names_a_reloads_steps_as_designers_own(ctx)


async def check_undo_edits_names_a_reloads_steps_as_designers_own(ctx: Ctx) -> None:
    """A call, then set_link_display, whose reload leaves steps of Designer's own on top of it, untagged: undo_edits()
    undoes nothing, and names them as Designer's own, from set_link_display's reload (REVIEW.md SRV-265). The node added
    for it is deleted, and the links go back to wires, after."""
    c, G = ctx.c, ctx.G
    added = added_id(
        text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [300, 900]}], **G}))
    )
    try:
        t = text(await c('set_link_display', {'mode': 'portal', 'from_nodes': [ctx.clouds], **G}))
        r_ = await c('undo_edits', {})
        said = text(r_)
        check(
            'undo_edits',
            "a reload's steps on top of a call: nothing undone, named as Designer's own, from set_link_display",
            'reloaded' in t
            and r_.is_error
            and 'Nothing undone' in said
            and "Designer's own steps of set_link_display's reload" in said,
            said.strip()[-300:],
        )
    finally:
        await c('set_link_display', {'mode': 'wire', 'from_nodes': [ctx.clouds], **G})
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': added}], **G})


async def check_a_reload_clears_no_step_of_the_undo_history(ctx: Ctx) -> None:
    """set_link_display's reload keeps the steps of Designer's one Undo history, its own added on top: the two steps
    made just before it are still listed after it, a call's on the graph reloaded and one's on a graph of another
    package (link_display/designer_scripts/undo_steps.py reads the Undo dropdown, which lists the newest 25;
    REVIEW.md TST-844, TST-849). The node added for it is deleted, and the links go back to wires, after."""
    c, G = ctx.c, ctx.G
    await c('create_graph', {'name': TEST_GRAPH + '_history', 'size_log2': 4})
    added = added_id(
        text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [0, 900]}], **G}))
    )
    try:
        before = _steps(text(await designer_script(c, 'link_display/undo_steps')))
        t = text(await c('set_link_display', {'mode': 'portal', 'from_nodes': [ctx.clouds], **G}))
        after = _steps(text(await designer_script(c, 'link_display/undo_steps')))
        # the two newest: this check's apply_edits on the graph reloaded, then its create_graph in another package
        check(
            'designer facts',
            "set_link_display's reload clears no step of the Undo history, its own package's included, and adds its "
            'own on top',
            'reloaded' in t
            and len(before) >= 2
            and all(step in after for step in before[:2])
            and after[0] != before[0],
            '%s | before %s | after %s' % (t.split(';')[0], before[:2], after[:6]),
        )
    finally:
        await c('set_link_display', {'mode': 'wire', 'from_nodes': [ctx.clouds], **G})
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': added}], **G})


def _steps(t: str) -> list[str]:
    """undo_steps.py's step names, newest first, or [] if it printed none."""
    found = re.search(r'^STEPS=(.*)$', t, re.M)
    steps: list[str] = json.loads(found.group(1)) if found else []
    return steps
