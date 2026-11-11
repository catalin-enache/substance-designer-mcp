"""The editor: every panel's screenshot, the clipboard, then open_graph fitting the whole graph."""

import re
import sys
from textwrap import dedent

from test_all_tools.common import (
    TEST_GRAPH,
    Ctx,
    check,
    clipboard_text,
    designer_script,
    is_image,
    set_clipboard_text,
    skip,
    text,
)

TEXT = b'mcp_selftest: the text a 3D capture puts back'


async def check_the_3d_capture_puts_the_text_back(ctx: Ctx) -> None:
    """screenshot_designer('3d') goes through the clipboard (the 3D view's own Copy Render to Clipboard), then puts
    back what Qt can copy of it: its text, checked here; the rest may be lost (the user's choice: DECISIONS.md). On
    macOS, where the clipboard's text can be read and set: a capture, then the same text read back, the user's own when
    they have some: Designer backs up what is there as its job starts and restores it as it ends, later than this
    check's `finally` when the call ended first (Ctrl-C), so the check's text must not be what it backs up (REVIEW.md
    TST-256). Elsewhere only the capture is checked."""
    c = ctx.c
    users = clipboard_text() if sys.platform == 'darwin' else None
    marker = users or TEXT
    try:
        if users == b'':
            set_clipboard_text(TEXT)
        r_ = await c('screenshot_designer', {'panel': '3d', 'max_size': 700})
        if not is_image(r_) and 'not visible' in text(r_) and ctx.was_running:
            skip('screenshot_designer', '3d', "no 3D View visible in the user's Designer")
            return
        kept = users is None or clipboard_text() == marker
        check(
            'screenshot_designer',
            '3d' + (' + the text on the clipboard put back' if users is not None else ''),
            is_image(r_) and kept,
            text(r_) if not is_image(r_) else '' if kept else 'the text on the clipboard did not come back',
        )
    finally:
        if users is not None:
            set_clipboard_text(users)


async def check_an_empty_clipboard_has_mimedata(ctx: Ctx) -> None:
    """The 3D capture backs up the clipboard from mimeData(): an empty clipboard still gives an (empty) object, not
    None (REVIEW.md HLP-8). This clears the system clipboard and puts it back as the capture does, so it runs only
    where the clipboard's text can be compared before and after (macOS), and fails if the text didn't come back
    (REVIEW.md TST-14)."""
    c = ctx.c
    if sys.platform != 'darwin':
        skip(
            'designer facts',
            'an empty clipboard has mimeData (no formats), not None',
            "the clipboard's text can only be compared before and after on macOS",
        )
        return
    before = clipboard_text()
    t = text(await designer_script(c, 'editor_panels_and_fit/empty_clipboard'))
    kept = clipboard_text() == before
    check(
        'designer facts',
        'an empty clipboard has mimeData (no formats), not None; its text kept',
        'EMPTY_MIME=0' in t and kept,
        t.strip() + ('' if kept else ' | the text on the clipboard did not come back'),
    )


async def check_every_panels_screenshot(ctx: Ctx) -> None:
    for panel in ('window', 'graph', '2d', 'parameters', 'explorer', 'library', 'console'):
        r_ = await ctx.c('screenshot_designer', {'panel': panel, 'max_size': 700})
        if (
            not is_image(r_) and 'not visible' in text(r_) and ctx.was_running
        ):  # a Designer the self-test started shows them
            skip('screenshot_designer', panel, "panel not visible in the user's Designer")
        else:
            check('screenshot_designer', panel, is_image(r_), '' if is_image(r_) else text(r_))


async def run(ctx: Ctx) -> None:
    """Every panel's screenshot, the clipboard, then fitting the whole graph."""
    c, helper_source, was_running = ctx.c, ctx.helper_source, ctx.was_running
    if not was_running:
        # our own instance, so its layout doesn't matter: show the console (hidden by default)
        await designer_script(c, 'editor_panels_and_fit/show_console')
    await check_every_panels_screenshot(ctx)
    await check_the_3d_capture_puts_the_text_back(ctx)
    await check_an_empty_clipboard_has_mimedata(ctx)
    r_ = await c('screenshot_designer', {'panel': 'foo'})
    check('screenshot_designer', 'error on bad panel', r_.is_error and "unknown panel 'foo'" in text(r_), text(r_))
    # (after the screenshot checks: run before them, these left a graph dock being deleted that the
    # screenshot check's widget scan met; what Designer rebuilds there wasn't pinned down)
    # by default the whole graph is fitted, even with nodes selected (Designer's own "Fit in view
    # (selection)" fits only the selection), and the result says what it fitted (REVIEW.md HLP-32)
    VIEW_SELECT = dedent("""
        from PySide6.QtWidgets import QGraphicsItem
        mw = _APP.getQtForPythonUIMgr().getMainWindow(); view = _graph_view(mw)
        items = [i for i in view.scene().items() if i.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable]
        %s
        _process_events()
        g = find_graph(%r); seen = view.mapToScene(view.viewport().rect()).boundingRect()
        inside = [seen.contains(n.getPosition().x, n.getPosition().y) for n in g.getNodes()]
        from sd.api.sdgraphobjectframe import SDGraphObjectFrame
        # frames whole, titles included (HLP-35)
        frames = [o for o in g.getGraphObjects() if isinstance(o, SDGraphObjectFrame)]
        framed = [seen.contains(f.getPosition().x, f.getPosition().y) and seen.contains(
            f.getPosition().x + f.getSize().x, f.getPosition().y + f.getSize().y) for f in frames]
        print('SELECTED=%%d INSIDE=%%d/%%d FRAMES=%%d/%%d' %% (len(view.scene().selectedItems()), sum(inside), len(inside),
              sum(framed), len(framed)))""")
    # first the fact behind it (GUIDE.md, Designer UI): F fits the selection, or everything
    # when nothing is selected
    f_sel = text(
        await c(
            'execute_designer_code',
            {
                'code': helper_source
                + VIEW_SELECT
                % (
                    dedent("""\
                        items[0].setSelected(True) if items else None
                        _fit_graph_view()"""),
                    TEST_GRAPH,
                )
            },
        )
    )
    f_none = text(
        await c(
            'execute_designer_code',
            {
                'code': helper_source
                + VIEW_SELECT
                % (
                    dedent("""\
                        view.scene().clearSelection()
                        _fit_graph_view()"""),
                    TEST_GRAPH,
                )
            },
        )
    )
    m_sel = re.search(r'SELECTED=(\d+) INSIDE=(\d+)/(\d+)', f_sel)
    m_none = re.search(r'SELECTED=(\d+) INSIDE=(\d+)/(\d+)', f_none)
    check(
        'designer facts',
        '"Fit in view (selection)" fits the selection, or everything when none (GUIDE.md)',
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
                + VIEW_SELECT
                % (
                    dedent("""\
                        items[0].setSelected(True) if items else None
                        _fit_graph_view()"""),
                    TEST_GRAPH,
                )
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
                    dedent("""
                        def _fit_view_to(*a, **k):
                            raise RuntimeError('the graph view is not visible in Designer')
                        open_graph(%r)""")
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
            {
                'code': helper_source
                + (
                    dedent("""
                        _current_graph = lambda: None
                        open_graph(%r)""")
                )
                % TEST_GRAPH
            },
        )
    )
    check(
        'open_graph',
        'another graph in the editor after the open is an error',
        'ERROR' in t and 'the graph in the editor is' in t,
        t.strip()[-150:],
    )
    # a free comment far from the nodes is fitted too (REVIEW.md HLP-39)
    t = text(await designer_script(c, 'editor_panels_and_fit/far_comment', graph=TEST_GRAPH))
    fitted = text(await c('open_graph', {'graph': TEST_GRAPH}))
    seen = text(
        await c(
            'execute_designer_code',
            {
                'code': helper_source
                + (
                    dedent("""
                        mw = _APP.getQtForPythonUIMgr().getMainWindow(); view = _graph_view(mw)
                        seen = view.mapToScene(view.viewport().rect()).boundingRect()
                        from sd.api.sdgraphobjectcomment import SDGraphObjectComment
                        g = find_graph(%r)
                        notes = [o for o in g.getGraphObjects() if isinstance(o, SDGraphObjectComment) and o.getDescription() == 'far away']
                        print('FAR_COMMENT_INSIDE=%%s' %% all(seen.contains(o.getPosition().x, o.getPosition().y) for o in notes))
                        for o in notes:
                            g.deleteGraphObject(o)""")
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
