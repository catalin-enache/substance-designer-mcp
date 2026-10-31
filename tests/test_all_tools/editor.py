"""The editor and screenshots: open_graph (focus, frames, fitting) and screenshot_designer."""

import re
from collections.abc import Sequence

from .common import GRAPH_OF, TEST_GRAPH, Ctx, check, clipboard_fingerprint, image_size, is_image, skip, text


async def open_and_zoom(ctx: Ctx) -> None:
    """open_graph targets and zoom, and the graph screenshot with crops."""
    c, G, clouds, slope = ctx.c, ctx.G, ctx.clouds, ctx.slope
    # --- editor + screenshots
    t = text(await c('open_graph', {'graph': TEST_GRAPH, 'node_id': slope}))
    check('open_graph', 'open + focus', 'focused node' in t, t)
    r_ = await c('open_graph', {'graph': 'no_such_graph'})
    check('open_graph', 'error on unknown graph', r_.is_error and 'not found' in text(r_), '')

    def visible(t: str) -> tuple[int | None, list[int] | None]:
        m = re.search(r'zoom (\d+)%, visible (-?\d+),(-?\d+) to (-?\d+),(-?\d+)', t)
        return (int(m.group(1)), [int(v) for v in m.groups()[1:]]) if m else (None, None)

    def contains(box: list[int] | None, points: Sequence[tuple[float, float]]) -> bool:
        return (
            box is not None and bool(points) and all(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in points)
        )

    t = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + (
                    'from sd.api.sdgraphobjectframe import SDGraphObjectFrame\n'
                    "f=[o for o in g.getGraphObjects() if isinstance(o, SDGraphObjectFrame) and o.getTitle()=='Shape'][0]\n"
                    "p,s=f.getPosition(),f.getSize()\nprint('FRAME=%d,%d,%d,%d' % (p.x, p.y, p.x+s.x, p.y+s.y))"
                )
            },
        )
    )
    # no match raises AttributeError, which the run's except reports (REVIEW.md TST-63)
    fx0, fy0, fx1, fy1 = [int(v) for v in re.search(r'FRAME=(-?\d+),(-?\d+),(-?\d+),(-?\d+)', t).groups()]  # type: ignore[union-attr]
    t = text(await c('open_graph', {'graph': TEST_GRAPH, 'frame': 'shape'}))  # title, any case
    zoom, box = visible(t)
    check(
        'open_graph',
        'frame fits in view',
        "fitted frame 'Shape'" in t and zoom is not None and zoom <= 100 and contains(box, [(fx0, fy0), (fx1, fy1)]),
        t,
    )
    shape_nodes = [clouds, slope]
    points = [
        (float(x), float(y))
        for x, y in re.findall(
            r'^\d+ \S+ @\((-?[\d.]+),(-?[\d.]+)\)',
            text(await c('describe_graph', {'node_ids': shape_nodes, **G})),
            re.M,
        )
    ]
    t = text(await c('open_graph', {'graph': TEST_GRAPH, 'node_ids': shape_nodes}))
    zoom, box = visible(t)
    check(
        'open_graph',
        'node_ids fit their bounding box',
        'fitted 2 node(s)' in t and len(points) == 2 and contains(box, points),
        t,
    )
    t = text(await c('open_graph', {'graph': TEST_GRAPH, 'rect': [0, 0, 10, 10]}))
    zoom, box = visible(t)
    check(
        'open_graph',
        'rect, zoom capped at 100%',
        zoom is not None and 100 / 1.2 <= zoom <= 100 and contains(box, [(0, 0), (10, 10)]),
        t,
    )
    # the fit zooms through Designer's own wheel handling, so the user's next wheel step
    # continues from the fitted zoom (setting the view's transform directly made it jump)
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': (
                    'import sd\nfrom PySide6.QtWidgets import QApplication, QGraphicsView, QDockWidget\n'
                    'from PySide6.QtGui import QWheelEvent\nfrom PySide6.QtCore import QPoint, QPointF, Qt\n'
                    'mw=sd.getContext().getSDApplication().getQtForPythonUIMgr().getMainWindow()\n'
                    "d=[w for w in mw.findChildren(QDockWidget) if w.objectName().startswith('areaB_') and w.isVisible()][0]\n"
                    'v=max((x for x in d.findChildren(QGraphicsView) if x.isVisible()), key=lambda x: x.width()*x.height())\n'
                    'vp=v.viewport(); c=QPointF(vp.width()/2, vp.height()/2); before=v.transform().m11()\n'
                    'QApplication.sendEvent(vp, QWheelEvent(c, QPointF(vp.mapToGlobal(c.toPoint())), QPoint(0,0), QPoint(0,120), '
                    'Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False))\n'
                    "QApplication.processEvents(); print('STEP=%.4f' % (v.transform().m11() / before))"
                )
            },
        )
    )
    step = re.search(r'STEP=([\d.]+)', t)
    check(
        'open_graph',
        'a wheel step after a fit continues from the fitted zoom',
        step is not None and abs(float(step.group(1)) - 1.2) < 0.01,
        t.strip(),
    )
    r_ = await c('open_graph', {'graph': TEST_GRAPH, 'node_id': slope, 'frame': 'Shape'})
    check(
        'open_graph',
        'refuses two view targets at once',
        r_.is_error and 'choose one of' in text(r_) and 'node_id, frame' in text(r_),
        text(r_),
    )
    r_ = await c('open_graph', {'graph': TEST_GRAPH, 'node_ids': ['graph']})
    check(
        'open_graph',
        'node_ids never means the graph itself',
        r_.is_error and "node 'graph' not found" in text(r_),
        text(r_),
    )
    r_ = await c('open_graph', {'graph': TEST_GRAPH, 'frame': 'no such frame'})
    check('open_graph', 'error on unknown frame lists the frames', r_.is_error and "'Shape'" in text(r_), text(r_))
    # 'graph' captures the node view alone (no title bar, no toolbars); crop takes a part of it
    full = await c('screenshot_designer', {'panel': 'graph', 'max_size': 4000})
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': (
                    'from PySide6.QtWidgets import QApplication, QGraphicsView, QDockWidget\n'
                    'def graph_dock(w):\n'  # a dead wrapper raises, now or on its children: skip it (AGENTS.md, Designer UI)
                    "    try:\n        return isinstance(w, QDockWidget) and w.objectName().startswith('areaB_') and w.isVisible() \\\n"
                    '            and bool(w.findChildren(QGraphicsView))\n'
                    '    except RuntimeError:\n        return False\n'
                    'd=[w for w in QApplication.instance().allWidgets() if graph_dock(w)][0]\n'
                    'v=max((x for x in d.findChildren(QGraphicsView) if x.isVisible()), key=lambda x: x.width()*x.height())\n'
                    "r=v.devicePixelRatioF()\nprint('VIEW=%d,%d DOCK=%d,%d' % (round(v.width()*r), round(v.height()*r), "
                    'round(d.width()*r), round(d.height()*r)))'
                )
            },
        )
    )
    sizes = re.search(r'VIEW=(\d+),(\d+) DOCK=(\d+),(\d+)', t)
    view_size = (int(sizes.group(1)), int(sizes.group(2))) if sizes else None
    check(
        'screenshot_designer',
        'graph is the node view, without toolbars',
        is_image(full) and sizes and image_size(full) == view_size and int(sizes.group(4)) > view_size[1],
        '%s vs %s' % (image_size(full) if is_image(full) else text(full), t.strip()[-120:]),
    )
    part = await c('screenshot_designer', {'panel': 'graph', 'max_size': 4000, 'crop': [0, 0, 0.5, 0.25]})
    check(
        'screenshot_designer',
        'crop',
        is_image(part)
        and view_size is not None
        and image_size(part) == (round(view_size[0] * 0.5), round(view_size[1] * 0.25)),
        str(image_size(part)) if is_image(part) else text(part),
    )
    r_ = await c('screenshot_designer', {'panel': 'graph', 'crop': [0, 0, 0.0001, 1]})
    check(
        'screenshot_designer',
        'error on a crop under a pixel',
        r_.is_error and 'less than a pixel' in text(r_),
        text(r_),
    )
    r_ = await c('screenshot_designer', {'panel': 'graph', 'crop': [0.5, 0, 0.2, 1]})
    check('screenshot_designer', 'error on a bad crop', r_.is_error and 'left < right' in text(r_), text(r_))


async def panels_and_fit(ctx: Ctx) -> None:
    """Every panel's screenshot, the clipboard, then fitting the whole graph."""
    c, helper_source, was_running = ctx.c, ctx.helper_source, ctx.was_running
    if not was_running:
        # our own instance, so its layout doesn't matter: show the console (hidden by default)
        await c(
            'execute_designer_code',
            {
                'code': (
                    'from PySide6.QtWidgets import QApplication, QMenu\n'
                    'for w in QApplication.instance().allWidgets():\n'
                    "    if isinstance(w, QMenu) and w.title() == '&Windows':\n"
                    '        w.aboutToShow.emit()\n'
                    '        for a in w.actions():\n'
                    "            if a.text() == 'Console' and not a.isChecked(): a.trigger()\n"
                    '        break\nQApplication.processEvents()'
                )
            },
        )
    for panel in ('window', 'graph', '2d', 'parameters', 'explorer', 'library', 'console'):
        r_ = await c('screenshot_designer', {'panel': panel, 'max_size': 700})
        if not is_image(r_) and 'not visible' in text(r_):
            skip('screenshot_designer', panel, 'panel not visible in Designer')
        else:
            check('screenshot_designer', panel, is_image(r_), '' if is_image(r_) else text(r_))
    before = clipboard_fingerprint()
    r_ = await c('screenshot_designer', {'panel': '3d', 'max_size': 700})
    if not is_image(r_) and 'not visible' in text(r_):
        skip('screenshot_designer', '3d', 'no 3D View visible in Designer')
    else:
        same = before is None or clipboard_fingerprint() == before
        if not same:
            # the user may have copied something meanwhile: measure again around a second capture
            before = clipboard_fingerprint()
            r_ = await c('screenshot_designer', {'panel': '3d', 'max_size': 700})
            same = clipboard_fingerprint() == before
        check(
            'screenshot_designer',
            '3d' + (' + clipboard kept' if before else ''),
            is_image(r_) and same,
            '' if is_image(r_) else text(r_),
        )
    # the 3D capture backs up the clipboard from mimeData(): an empty clipboard still gives
    # an (empty) object, not None (REVIEW.md HLP-8). This clears the system clipboard and
    # restores it as the capture does, so it runs only where the clipboard can be
    # compared before and after (macOS), and fails if it didn't come back (REVIEW.md TST-14)
    if clipboard_fingerprint() is None:
        skip(
            'designer facts',
            'an empty clipboard has mimeData (no formats), not None',
            'the clipboard can only be compared before and after on macOS',
        )
    else:
        before = clipboard_fingerprint()
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': (
                        'from PySide6 import QtCore, QtWidgets\napp = QtWidgets.QApplication.instance()\ncb = app.clipboard()\n'
                        'orig = cb.mimeData()\nbackup = QtCore.QMimeData()\n'
                        'for f in orig.formats():\n    backup.setData(f, orig.data(f))\n'
                        'try:\n    cb.clear()\n    app.processEvents()\n    m = cb.mimeData()\n'
                        "    print('EMPTY_MIME=%s' % ('None' if m is None else len(m.formats())))\n"
                        'finally:\n    cb.setMimeData(backup)\n    app.processEvents()'
                    )
                },
            )
        )
        kept = clipboard_fingerprint() == before
        check(
            'designer facts',
            'an empty clipboard has mimeData (no formats), not None; clipboard kept',
            'EMPTY_MIME=0' in t and kept,
            t.strip() + ('' if kept else ' | the clipboard did not come back'),
        )
    r_ = await c('screenshot_designer', {'panel': 'foo'})
    check('screenshot_designer', 'error on bad panel', r_.is_error and "unknown panel 'foo'" in text(r_), text(r_))
    # (after the screenshot checks: run before them, these left a graph dock being deleted that the
    # screenshot check's widget scan met; what Designer rebuilds there wasn't pinned down)
    # by default the whole graph is fitted, even with nodes selected (Designer's own "Fit in view
    # (selection)" fits only the selection), and the result says what it fitted (REVIEW.md HLP-32)
    VIEW_SELECT = (
        '\nfrom PySide6.QtWidgets import QGraphicsItem\n'
        'mw = _APP.getQtForPythonUIMgr().getMainWindow(); view = _graph_view(mw)\n'
        'items = [i for i in view.scene().items() if i.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable]\n'
        '%s\n_process_events()\n'
        'g = find_graph(%r); seen = view.mapToScene(view.viewport().rect()).boundingRect()\n'
        'inside = [seen.contains(n.getPosition().x, n.getPosition().y) for n in g.getNodes()]\n'
        'from sd.api.sdgraphobjectframe import SDGraphObjectFrame\n'  # frames whole, titles included (HLP-35)
        'frames = [o for o in g.getGraphObjects() if isinstance(o, SDGraphObjectFrame)]\n'
        'framed = [seen.contains(f.getPosition().x, f.getPosition().y) and seen.contains(\n'
        '    f.getPosition().x + f.getSize().x, f.getPosition().y + f.getSize().y) for f in frames]\n'
        "print('SELECTED=%%d INSIDE=%%d/%%d FRAMES=%%d/%%d' %% (len(view.scene().selectedItems()), sum(inside), len(inside),\n"
        '      sum(framed), len(framed)))'
    )
    # first the fact behind it (AGENTS.md, Designer UI): F fits the selection, or everything
    # when nothing is selected
    f_sel = text(
        await c(
            'execute_designer_code',
            {
                'code': helper_source
                + VIEW_SELECT % ('items[0].setSelected(True) if items else None\n_fit_graph_view()', TEST_GRAPH)
            },
        )
    )
    f_none = text(
        await c(
            'execute_designer_code',
            {'code': helper_source + VIEW_SELECT % ('view.scene().clearSelection()\n_fit_graph_view()', TEST_GRAPH)},
        )
    )
    m_sel = re.search(r'SELECTED=(\d+) INSIDE=(\d+)/(\d+)', f_sel)
    m_none = re.search(r'SELECTED=(\d+) INSIDE=(\d+)/(\d+)', f_none)
    check(
        'designer facts',
        '"Fit in view (selection)" fits the selection, or everything when none (AGENTS.md)',
        m_sel is not None
        and m_none is not None
        and m_sel.group(1) != '0'
        and m_sel.group(2) != m_sel.group(3)
        and m_none.group(1) == '0'
        and m_none.group(2) == m_none.group(3),
        f_sel.strip() + ' | ' + f_none.strip(),
    )
    # the view first zoomed onto the selection (part of the graph out of view), so the check sees
    # open_graph bring the rest back (REVIEW.md TST-68), frames included (HLP-35)
    zoomed = text(
        await c(
            'execute_designer_code',
            {
                'code': helper_source
                + VIEW_SELECT % ('items[0].setSelected(True) if items else None\n_fit_graph_view()', TEST_GRAPH)
            },
        )
    )
    t = text(await c('open_graph', {'graph': TEST_GRAPH}))
    seen = text(await c('execute_designer_code', {'code': helper_source + VIEW_SELECT % ('', TEST_GRAPH)}))
    mz = re.search(r'INSIDE=(\d+)/(\d+)', zoomed)
    m = re.search(r'SELECTED=(\d+) INSIDE=(\d+)/(\d+) FRAMES=(\d+)/(\d+)', seen)
    check(
        'open_graph',
        'fits the whole graph even with nodes selected',
        mz is not None
        and mz.group(1) != mz.group(2)
        and m is not None
        and int(m.group(1)) >= 1
        and m.group(2) == m.group(3)
        and m.group(4) == m.group(5)
        and int(m.group(5)) >= 1,
        zoomed.strip() + ' -> ' + seen.strip() + ' | ' + t.strip()[-80:],
    )
    # a fit that fails doesn't fail the open: it is reported (REVIEW.md HLP-35)
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helper_source
                + (
                    "\ndef _fit_view_to(*a, **k):\n    raise RuntimeError('the graph view is not visible in Designer')\n"
                    'open_graph(%r)'
                )
                % TEST_GRAPH
            },
        )
    )
    check(
        'open_graph',
        'a fit that fails is reported, not an error',
        'ERROR' not in t and 'opened' in t and 'not visible' in t,
        t.strip()[-150:],
    )
    # ...but another graph in the editor is an error: the open didn't do what was asked (HLP-38)
    t = text(
        await c(
            'execute_designer_code',
            {'code': helper_source + ('\n_current_graph = lambda: None\nopen_graph(%r)') % TEST_GRAPH},
        )
    )
    check(
        'open_graph',
        'another graph in the editor after the open is an error',
        'ERROR' in t and 'the graph in the editor is' in t,
        t.strip()[-150:],
    )
    # a free comment far from the nodes is fitted too (REVIEW.md HLP-39)
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + (
                    'from sd.api.sdgraphobjectcomment import SDGraphObjectComment\nfrom sd.api.sdbasetypes import float2\n'
                    "note = SDGraphObjectComment.sNew(g); note.setPosition(float2(2500, -1500)); note.setDescription('far away')\n"
                    "print('COMMENT=ok')"
                )
            },
        )
    )
    fitted = text(await c('open_graph', {'graph': TEST_GRAPH}))
    seen = text(
        await c(
            'execute_designer_code',
            {
                'code': helper_source
                + (
                    '\nmw = _APP.getQtForPythonUIMgr().getMainWindow(); view = _graph_view(mw)\n'
                    'seen = view.mapToScene(view.viewport().rect()).boundingRect()\n'
                    'from sd.api.sdgraphobjectcomment import SDGraphObjectComment\ng = find_graph(%r)\n'
                    "notes = [o for o in g.getGraphObjects() if isinstance(o, SDGraphObjectComment) and o.getDescription() == 'far away']\n"
                    "print('FAR_COMMENT_INSIDE=%%s' %% all(seen.contains(o.getPosition().x, o.getPosition().y) for o in notes))\n"
                    'for o in notes:\n    g.deleteGraphObject(o)'
                )
                % TEST_GRAPH
            },
        )
    )
    check(
        'open_graph',
        'a free comment far from the nodes is fitted too',
        'COMMENT=ok' in t and 'FAR_COMMENT_INSIDE=True' in seen,
        fitted.strip()[-100:] + ' | ' + seen.strip()[-60:],
    )
    await c(
        'execute_designer_code', {'code': helper_source + VIEW_SELECT % ('view.scene().clearSelection()', TEST_GRAPH)}
    )
