"""set_link_display: portals and wires, by node, by link, by fan-out and by length."""

import os
import re
import xml.etree.ElementTree as ET
from typing import cast

from .common import TEST_GRAPH, Ctx, added_id, check, text


async def run(ctx: Ctx) -> None:
    c, G, clouds, lv, stats_before = ctx.c, ctx.G, ctx.clouds, ctx.lv, ctx.stats_before
    r_ = await c('set_link_display', {'mode': 'dotted', 'from_nodes': [clouds], **G})
    check('set_link_display', 'error on bad mode', r_.is_error and 'mode must be' in text(r_), text(r_))
    r_ = await c('set_link_display', {'mode': 'portal', **G})
    check('set_link_display', 'error without a selection', r_.is_error and 'choose links' in text(r_), text(r_))
    t = text(await c('set_link_display', {'mode': 'portal', 'from_nodes': [clouds], **G}))
    check('set_link_display', 'portals from a node', 'changed to portal' in t and 'reloaded' in t, t.split(';')[0])
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
        nums(stats_before)
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
        refs and not missing,
        'refs %s, missing %s' % (refs, missing),
    )
    t = text(await c('set_link_display', {'mode': 'wire', 'from_nodes': [clouds], **G}))
    check('set_link_display', 'back to wires', 'changed to wire' in t, t.split(';')[0])
    t = text(await c('set_link_display', {'mode': 'wire', 'from_nodes': [clouds], **G}))
    check('set_link_display', 'nothing to change: no save, no reload', 'nothing to do' in t, t)
    # automatic selection, as AGENTS.md recommends: clouds feeds 3 inputs once this blend is in
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
