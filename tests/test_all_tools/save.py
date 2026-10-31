"""Saving: save_package, snapshots of a saved package, diff against a .sbs, copied bitmaps."""

import os
import re
from typing import cast

from .common import GRAPH_OF, TEST_GRAPH, Ctx, added_id, check, positions, text


async def run(ctx: Ctx) -> None:
    c, scratch, G, clouds, lv, png = ctx.c, ctx.scratch, ctx.G, ctx.clouds, ctx.lv, ctx.png
    # --- save (export and render: render.py)
    sbs = os.path.join(scratch, TEST_GRAPH + '.sbs')
    t = text(await c('save_package', {'graph_or_path': TEST_GRAPH, 'save_as': sbs}))
    check('save_package', 'save as', os.path.exists(sbs), t)
    r_ = await c('save_package', {'graph_or_path': TEST_GRAPH})
    t = text(r_)
    check('save_package', 'save in place', not r_.is_error and 'saved %s' % sbs in t, t)
    t = text(await c('save_package', {'graph_or_path': sbs}))
    check('save_package', 'by file path', 'saved %s' % sbs in t, t)
    state = GRAPH_OF % TEST_GRAPH + "p=g.getPackage()\nprint('STATE=%s %s' % (p.getFilePath(), p.isModified()))"
    before = text(await c('execute_designer_code', {'code': state}))
    await c('snapshot_graph', {'label': 'state check', **G})
    after = text(await c('execute_designer_code', {'code': state}))
    check(
        'snapshot_graph',
        "leaves the package's file and saved state alone",
        'STATE=%s False' % sbs in before and before == after,
        before + after,
    )
    xs = positions(text(await c('describe_graph', G)))
    await c('move_nodes', {'positions': {clouds: [xs[clouds][0] + 50, xs[clouds][1]]}, **G})
    t = text(await c('diff_graph', {'against': sbs, 'show_positions': True, **G}))
    check(
        'diff_graph',
        'against a .sbs path, with positions',
        '1 node(s) moved' in t and '~ node %s' % clouds in t and 'moved' in t,
        t,
    )
    await c('move_nodes', {'positions': {clouds: list(xs[clouds])}, **G})
    t = text(await c('import_bitmap', {'path': png, 'embed': 'copy', 'name': 'selftest_copy', **G}))
    copied = re.search(r'selftest_copy \(copy\): (.*)', t)
    check(
        'import_bitmap',
        'copy into <package>.resources, named',
        copied is not None
        and os.path.isfile(copied.group(1))
        and os.path.dirname(copied.group(1)) == os.path.join(scratch, TEST_GRAPH + '.resources')
        and os.path.basename(copied.group(1)).startswith('XXXXXX-'),
        t,
    )
    copied_node = added_id(t)
    # a snapshot keeps copied bitmaps reachable (REVIEW.md SRV-3): every bitmap file the
    # snapshot's .sbs points to exists, relative to the snapshot or absolute
    snap = text(await c('snapshot_graph', {'label': 'with copied bitmap', **G})).split('saved: ', 1)[1].strip()
    import xml.etree.ElementTree as ET

    refs = [
        cast(str, f.get('v'))
        for r in ET.parse(snap).getroot().iter('resource')
        if r.find('filepath') is not None
        for f in [cast(ET.Element, r.find('filepath'))]
    ]
    missing = [r for r in refs if not os.path.isfile(os.path.join(os.path.dirname(snap), r))]
    check(
        'snapshot_graph',
        'copied bitmaps stay reachable',
        any('selftest_copy' in r or 'XXXXXX-' in r for r in refs) and not missing,
        'refs %s, missing %s' % (refs, missing),
    )
    await c('delete_nodes', {'node_ids': [copied_node], **G})
    # measured here, before the safeguards category, for set_link_display's 'output unchanged' check
    stats_before = text(await c('node_stats', {'node_id': lv, **G}))
    ctx.sbs = sbs
    ctx.stats_before = stats_before
