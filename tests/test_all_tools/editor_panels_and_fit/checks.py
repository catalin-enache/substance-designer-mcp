"""The editor: every panel's screenshot, the clipboard, open_graph fitting the whole graph, then the 3D view set up."""

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
    prepared_call,
    set_clipboard_text,
    skip,
    text,
)
from test_all_tools.editor_panels_and_fit.preparations import (
    CHECKER_OPS,
    PLAIN_OPS,
    VIEW3D_ADDED,
    VIEW3D_GRAPH,
    VIEW3D_PLAIN,
)
from test_all_tools.editor_panels_and_fit.renders import (
    difference,
    grey,
    plane_columns,
    plane_height,
    plane_width,
    say_failed,
    transitions,
)

TEXT = b'mcp_selftest: the text a 3D capture puts back'
THREE_D = {'panel': '3d', 'max_size': 700}
# a plane seen from the top, framed; what a call sets stays, so the calls after pass only what they change
TOP = {'mesh': 'Plane', 'view': 'Top'}
USERS_3D_VIEW = "it would change the 3D view of the user's Designer"
# the 3D view's zoom per wheel step, closer and away (designer_helpers/view3d.py): three away measured 0.75-0.78x
STEP, STEP_AWAY = 1.11, 0.917


async def check_outputs_added_to_the_open_graph_reach_the_3d_view_once_applied(ctx: Ctx) -> None:
    """Designer puts a graph's outputs on the 3D view's mesh as it switches to the graph, so outputs added to the graph
    once open don't reach it by themselves (ROADMAP item 7: a cobblestone material built so left the default material on
    the cube): measured as a fact; screenshot_designer(graph=...) puts them there."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'graph= puts the outputs of the graph on the mesh', USERS_3D_VIEW)
        return
    await prepared_call(c, 'create_graph', {'name': VIEW3D_ADDED, 'size_log2': 9})
    await prepared_call(c, 'open_graph', {'graph': VIEW3D_ADDED})
    before = await c('screenshot_designer', {**THREE_D, **TOP, 'tiling': 1.0})
    await prepared_call(c, 'apply_edits', {'graph': VIEW3D_ADDED, 'ops': CHECKER_OPS})
    after = await c('screenshot_designer', THREE_D)
    applied = await c('screenshot_designer', {**THREE_D, 'graph': VIEW3D_ADDED})
    shots = [before, after, applied]
    if not all(is_image(r) for r in shots):
        check('screenshot_designer', 'graph= puts the outputs of the graph on the mesh', False, 'a shot failed (below)')
        say_failed('graph= puts the outputs of the graph on the mesh', *shots)
        return
    unchanged = difference(grey(before), grey(after))
    check(
        'designer facts',
        "outputs added to the graph open in the editor don't reach the 3D view",
        unchanged < 2,
        'mean difference %.1f grey levels' % unchanged,
    )
    seen = transitions(grey(applied))
    check(
        'screenshot_designer',
        'graph= puts the outputs of the graph on the mesh',
        seen >= 6 and transitions(grey(after)) <= 2 and VIEW3D_ADDED in text(applied),
        '%d dark-light changes across the plane, %d before | %s' % (seen, transitions(grey(after)), text(applied)),
    )


async def check_a_view_turns_the_camera(ctx: Ctx) -> None:
    """view= turns the camera to that viewpoint: a plane seen from the Default angle is wider than high, from the Top
    a square. Designer's Frame cancels the camera's turn if it comes at once (designer_helpers/view3d.py): from the
    Default angle, view='Top' left the plane as it was."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'view= turns the camera', USERS_3D_VIEW)
        return
    slanted = await c('screenshot_designer', {**THREE_D, 'mesh': 'Plane', 'view': 'Default'})
    above = await c('screenshot_designer', {**THREE_D, 'view': 'Top'})
    if not (is_image(slanted) and is_image(above)):
        check('screenshot_designer', 'view= turns the camera', False, text(slanted) + ' | ' + text(above))
        return
    shapes = [plane_height(grey(r)) / max(plane_width(grey(r)), 1) for r in (slanted, above)]
    check(
        'screenshot_designer',
        'view= turns the camera: Default slanted, Top straight down',
        shapes[0] < 0.85 and 0.9 <= shapes[1] <= 1.1,
        'the plane %.2f as high as wide from Default, %.2f from the Top' % tuple(shapes),
    )


async def check_the_3d_view_zooms_and_tiles(ctx: Ctx) -> None:
    """tiling repeats the material on the mesh; zoom comes closer (or goes away) by wheel steps of about 1.1x, from the
    framed view after view=, else from where the camera is; what a call sets stays for the next (each passes only what
    it changes); and the Parameters panel, which Designer turns to the 3D material to set its tiling, is back on the
    graph in the editor."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'zoom and tiling', USERS_3D_VIEW)
        return
    base = await c('screenshot_designer', {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH, 'tiling': 1.0})
    tiled = await c('screenshot_designer', {**THREE_D, 'tiling': 2.0})
    closer = await c('screenshot_designer', {**THREE_D, 'view': 'Top', 'zoom': 3})
    back = await c('screenshot_designer', {**THREE_D, 'zoom': -3})  # from the camera closer was left at
    away = await c('screenshot_designer', {**THREE_D, 'view': 'Top', 'zoom': -3})
    shots = [base, tiled, closer, back, away]
    if not all(is_image(r) for r in shots):
        check('screenshot_designer', 'zoom and tiling', False, 'a shot failed (below)')
        say_failed('zoom and tiling', *shots)
        return
    once, twice = transitions(grey(base)), transitions(grey(tiled))
    check(
        'screenshot_designer',
        'tiling=2 repeats the material twice as often',
        once >= 6 and 1.6 <= twice / once <= 2.4,
        '%d dark-light changes across the plane at tiling 1, %d at 2' % (once, twice),
    )
    near, far = plane_width(grey(closer)), plane_width(grey(base))
    ratio = near / max(far, 1)
    edges = plane_columns(grey(closer))
    clipped = edges[0] == 0 or edges[1] == grey(closer).shape[1] - 1  # wider than the panel: the width stops growing
    check(
        'screenshot_designer',
        'zoom=3 comes closer, about 1.1x a step',
        not clipped and STEP**3 * 0.95 <= ratio <= STEP**3 * 1.05,  # two steps (1.23x) or four (1.52x) fail
        'the plane %d px wide, then %d: %.2fx (%.2f^3 = %.2f)%s'
        % (far, near, ratio, STEP, STEP**3, " | clipped at the panel's edge: a narrower 3D panel" if clipped else ''),
    )
    smaller = plane_width(grey(away)) / max(far, 1)
    check(
        'screenshot_designer',
        'zoom=-3 goes away, about 1.09x a step',
        STEP_AWAY**3 * 0.95 <= smaller <= STEP_AWAY**3 * 1.05,  # two steps (0.84x) or four (0.71x) fail
        'the plane %.2fx as wide (%.3f^3 = %.2f)' % (smaller, STEP_AWAY, STEP_AWAY**3),
    )
    kept = plane_width(grey(back)) / max(near, 1)  # from the framed view instead: 0.56x
    tiles = transitions(grey(back))
    check(
        'screenshot_designer',
        'without view=, zoom counts from where the camera is; the tiling stays',
        STEP_AWAY**3 * 0.95 <= kept <= STEP_AWAY**3 * 1.05 and 1.6 <= tiles / max(once, 1) <= 2.4,
        'the plane %.2fx as wide as closer left it; %d dark-light changes, %d at tiling 1' % (kept, tiles, once),
    )
    panel = text(await designer_script(c, 'editor_panels_and_fit/parameters_panel'))
    m = re.search(r'PANEL=(.*)\|EDITOR=(.*)', panel)
    check(
        'screenshot_designer',
        'tiling= leaves the Parameters panel on the graph in the editor',
        m is not None and m.group(1) == m.group(2),
        panel.strip(),
    )


async def check_graph_finds_its_row_in_a_collapsed_package(ctx: Ctx) -> None:
    """graph= opens the Explorer's context menu on the graph's row, which a collapsed package hides: selecting the graph
    in the Explorer (setExplorerSelection) expands its package, and a row that still isn't showing is refused
    (designer_helpers/view3d.py, _row_point)."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'graph= finds its row in a collapsed package', USERS_3D_VIEW)
        return
    collapsed = text(await designer_script(c, 'editor_panels_and_fit/collapse_package', graph=VIEW3D_GRAPH))
    r = await c('screenshot_designer', {**THREE_D, 'graph': VIEW3D_GRAPH})
    check(
        'screenshot_designer',
        'graph= finds its row in a collapsed package',
        'COLLAPSED=True' in collapsed and is_image(r) and "graph %s's outputs" % VIEW3D_GRAPH in text(r),
        collapsed.strip() + ' | ' + text(r),
    )


MENUS = dedent("""
    from PySide6 import QtWidgets
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    dock = _visible_dock(mw, _PANEL_AREAS['3d'])
    keep = [mw, dock]
    missing = []
    for path in [('Scene', m) for m in MESHES] + [('Camera', v) for v in VIEWS + ('Frame',)]:
        try:
            _menu_action(dock.findChildren(QtWidgets.QMenuBar)[0], keep, *path) if dock else None
        except RuntimeError:
            missing.append(' > '.join(path))
    print('MISSING=%r' % missing if dock else 'NO_3D_VIEW')""")


async def check_the_3d_views_menus_have_the_meshes_and_views(ctx: Ctx) -> None:
    """The meshes and viewpoints screenshot_designer offers are in the 3D view's Scene and Camera menus, with Frame
    (designer_helpers/view3d.py, MESHES and VIEWS): looked up, nothing triggered, so this runs in the user's Designer
    too (REVIEW.md TST-315)."""
    t = text(await ctx.c('execute_designer_code', {'code': ctx.helper_source + MENUS}))
    if 'NO_3D_VIEW' in t and ctx.was_running:
        skip(
            'designer facts',
            "the 3D view's menus have its meshes and views",
            "no 3D View visible in the user's Designer",
        )
        return
    check('designer facts', "the 3D view's menus have its meshes and views", 'MISSING=[]' in t, t.strip()[-300:])


async def check_opening_the_editors_graph_again_leaves_the_outputs_on_the_mesh(ctx: Ctx) -> None:
    """tiling= turns the Parameters panel back by opening the graph in the editor again, which doesn't put that graph's
    outputs on the mesh (designer_helpers/view3d.py; REVIEW.md TST-315): with a plain graph in the editor, graph= and
    tiling= leave the checker of graph= on the mesh."""
    c = ctx.c
    if ctx.was_running:
        skip('designer facts', "opening the editor's graph again doesn't put its outputs on the mesh", USERS_3D_VIEW)
        return
    await prepared_call(c, 'create_graph', {'name': VIEW3D_PLAIN, 'size_log2': 9})
    await prepared_call(c, 'apply_edits', {'graph': VIEW3D_PLAIN, 'ops': PLAIN_OPS})
    await prepared_call(c, 'open_graph', {'graph': VIEW3D_PLAIN})
    r = await c('screenshot_designer', {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH, 'tiling': 1.0})
    seen = transitions(grey(r)) if is_image(r) else 0
    check(
        'designer facts',
        "opening the editor's graph again doesn't put its outputs on the mesh",
        seen >= 6 and 'back on %s' % VIEW3D_PLAIN in text(r),
        '%d dark-light changes across the plane | %s' % (seen, text(r)),
    )


# set_3d_view with the Parameters panel taken as hidden, then with the Tiling field failing at once, before the panel
# shows the material, as an abort landing in its first poll would (REVIEW.md HLP-111)
PARAMETERS_HIDDEN = dedent("""
    _shown = _visible_dock
    def _visible_dock(mw, prefix):
        return None if prefix == _PANEL_AREAS['parameters'] else _shown(mw, prefix)
    set_3d_view(None, 'Sphere', None, 0, 2.0)""")
TILING_FAILING = dedent("""
    def _tiling_spin(params, keep):
        raise RuntimeError("the 3D material's Tiling taken as failing")
    set_3d_view(None, 'Sphere', None, 0, 2.0)""")
# then an abort (the plugin's is a BaseException) as the graph's outputs are applied, after the mesh changed
ABORTED = dedent("""
    class _Abort(BaseException):
        pass
    def _apply_outputs(tree, g, keep):
        raise _Abort('an abort as the outputs are applied')
    set_3d_view(%r, 'Plane')""")


async def check_a_set_up_checks_what_it_needs_first_and_says_what_it_set(ctx: Ctx) -> None:
    """A panel the set-up needs is checked before anything changes: the Parameters panel taken as hidden, the mesh
    stays as it was. An error after a change says what was set, and the Parameters panel, turned to the 3D material,
    goes back to the graph in the editor all the same, once the panel shows the material: the Tiling field failing
    before it does (REVIEW.md HLP-107, HLP-111). An abort after a change prints what was set, and the job still ends
    as an abort (HLP-113)."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'a set-up checks what it needs first, and says what it set', USERS_3D_VIEW)
        return
    before = await c('screenshot_designer', {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH, 'tiling': 1.0})
    hidden = text(await c('execute_designer_code', {'code': ctx.helper_source + PARAMETERS_HIDDEN}))
    after = await c('screenshot_designer', THREE_D)
    changed = difference(grey(before), grey(after)) if is_image(before) and is_image(after) else 255.0
    check(
        'screenshot_designer',
        'a panel the set-up needs is checked before anything changes',
        'Parameters panel' in hidden and changed < 2,
        '%s | the render changed %.1f grey levels' % (hidden.strip().splitlines()[-1:], changed),
    )
    say_failed('a panel the set-up needs is checked before anything changes', before, after)
    failed = text(await c('execute_designer_code', {'code': ctx.helper_source + TILING_FAILING}))
    panel = text(await designer_script(c, 'editor_panels_and_fit/parameters_panel'))
    m = re.search(r'PANEL=(.*)\|EDITOR=(.*)', panel)
    check(
        'screenshot_designer',
        'an error after a change says what was set; the Parameters panel back on the graph in the editor',
        'the 3D view was already set: Sphere' in failed and m is not None and m.group(1) == m.group(2),
        '%s | %s' % (failed.strip().splitlines()[-1:], panel.strip()),
    )
    aborted = text(await c('execute_designer_code', {'code': ctx.helper_source + ABORTED % VIEW3D_GRAPH}))
    check(
        'screenshot_designer',
        'an abort after a change says what was set, and goes on as an abort',
        '3D view, setting: Plane' in aborted
        and "3D view, setting: graph %s's outputs on the mesh" % VIEW3D_GRAPH in aborted
        and '_Abort: an abort as the outputs are applied' in aborted,
        ' | '.join(line for line in aborted.splitlines() if '3D view' in line or 'Abort' in line)[-300:],
    )


ADD_MATERIAL = dedent("""
    from PySide6 import QtCore, QtWidgets
    mw = _APP.getQtForPythonUIMgr().getMainWindow(); keep = [mw]
    bar = _3d_dock(mw).findChildren(QtWidgets.QMenuBar)[0]; keep.append(bar)
    def name_it():  # Materials > Add asks a name, in a dialog of its own
        dialog = QtWidgets.QApplication.activeModalWidget()
        if isinstance(dialog, QtWidgets.QInputDialog):
            dialog.setTextValue('mcp_selftest_material'); dialog.accept()
        elif dialog is not None:
            dialog.close()
    timer = QtCore.QTimer(); timer.setSingleShot(True); timer.timeout.connect(name_it); timer.start(500)
    _menu_action(bar, keep, 'Materials', 'Add').trigger()
    _settle(1.0)
    timer.stop()
    menu = _menu_action(bar, keep, 'Materials').menu(); keep.append(menu); menu.aboutToShow.emit(); _process_events()
    print('MATERIALS=%r' % [a.text() for a in menu.actions() if a.menu() is not None and a.text()])""")


async def check_a_material_the_mesh_doesnt_use_doesnt_stop_tiling(ctx: Ctx) -> None:
    """tiling= sets the material the mesh uses: one added to it (Materials > Add), which Designer lists as unused, isn't
    counted (REVIEW.md HLP-114; that with mesh= the new mesh's materials count is a unit test's, every preset mesh having
    one)."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', "tiling= isn't stopped by a material the mesh doesn't use", USERS_3D_VIEW)
        return
    await c('screenshot_designer', {**THREE_D, 'mesh': 'Sphere', 'view': 'Default', 'graph': VIEW3D_GRAPH})
    added = text(await c('execute_designer_code', {'code': ctx.helper_source + ADD_MATERIAL}))
    r = await c('screenshot_designer', {**THREE_D, 'tiling': 2.0})
    check(
        'screenshot_designer',
        "tiling= isn't stopped by a material the mesh doesn't use",
        'mcp_selftest_material (unused)' in added and is_image(r) and 'tiling 2 ' in text(r),
        '%s | %s' % (added.strip()[-160:], text(r)),
    )


# a timer started in a function and never stopped, its slot holding it as pick holds its timers, with no parent, then
# with a parent made in that function and held by it alone; each counted after the function returned
TIMER_AFTER_ITS_FUNCTION = dedent("""
    import weakref
    from PySide6 import QtCore
    def started(parented):
        owner = QtCore.QObject()
        timers = [QtCore.QTimer(owner) if parented else QtCore.QTimer()]
        count = [0]
        timers[0].timeout.connect(lambda: (timers, count.__setitem__(0, count[0] + 1)))
        timers[0].start(20)
        _settle(0.2)
        return count, count[0], weakref.ref(timers[0])
    after = []
    for parented in (False, True):
        count, then, timer = started(parented)
        _settle(0.3)
        after.append(count[0] - then)
        try:
            timer() and timer().stop()  # one that lived on, stopped now
        except RuntimeError:  # its C++ object gone with its parent
            pass
    print('FIRED_AFTER: no parent %d, a parent held by the function %d' % tuple(after))""")


async def check_a_timer_goes_with_the_parent_its_function_held(ctx: Ctx) -> None:
    """A timer never stopped outlives the function that started it when its slot holds it, as _apply_outputs' pick
    holds its timers; given a parent that function made and held alone, it goes with the function, whatever runs of its
    finally (designer_helpers/view3d.py; REVIEW.md HLP-118)."""
    if ctx.was_running:
        skip(
            'designer facts',
            'a timer goes with the parent its function held',
            "it would start a timer in the user's Designer",
        )
        return
    t = text(await ctx.c('execute_designer_code', {'code': ctx.helper_source + TIMER_AFTER_ITS_FUNCTION}))
    m = re.search(r'no parent (\d+), a parent held by the function (\d+)', t)
    check(
        'designer facts',
        'a timer goes with the parent its function held; with none, it outlives the function',
        m is not None and int(m.group(1)) > 0 and int(m.group(2)) == 0,
        t.strip()[-200:],
    )


async def check_the_3d_view_refuses_what_it_cant_show(ctx: Ctx) -> None:
    """A mesh or view the 3D view's menus don't have, and a graph with one output (Designer would ask which channel to
    show it in), are refused before anything changes, so these run in the user's Designer too."""
    c = ctx.c
    t = text(await c('screenshot_designer', {**THREE_D, 'mesh': 'Teapot'}))
    check('screenshot_designer', 'an unknown mesh is refused, naming the meshes', 'Teapot' in t and 'Torus' in t, t)
    t = text(await c('screenshot_designer', {**THREE_D, 'view': 'Diagonal'}))
    check('screenshot_designer', 'an unknown view is refused, naming the views', 'Diagonal' in t and 'Bottom' in t, t)
    t = text(await c('screenshot_designer', {**THREE_D, 'graph': TEST_GRAPH}))  # its one output (preparations.py)
    check(
        'screenshot_designer',
        'a graph with one output is refused: Designer would ask which channel',
        'one output' in t and 'preview_node' in t,
        t,
    )


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
    """Every panel's screenshot, the clipboard, fitting the whole graph, then the 3D view set up."""
    c, helper_source, was_running = ctx.c, ctx.helper_source, ctx.was_running
    if not was_running:
        # our own instance, so its layout doesn't matter: show the console (hidden by default)
        await designer_script(c, 'editor_panels_and_fit/show_console')
    await check_every_panels_screenshot(ctx)
    await check_the_3d_capture_puts_the_text_back(ctx)
    await check_an_empty_clipboard_has_mimedata(ctx)
    await check_the_3d_view_refuses_what_it_cant_show(ctx)
    await check_the_3d_views_menus_have_the_meshes_and_views(ctx)
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
    # last: they open a graph of their own in the editor, where the checks above need the self-test graph
    await check_outputs_added_to_the_open_graph_reach_the_3d_view_once_applied(ctx)
    await check_a_view_turns_the_camera(ctx)
    await check_the_3d_view_zooms_and_tiles(ctx)
    await check_graph_finds_its_row_in_a_collapsed_package(ctx)
    await check_a_set_up_checks_what_it_needs_first_and_says_what_it_set(ctx)
    await check_opening_the_editors_graph_again_leaves_the_outputs_on_the_mesh(ctx)
    await check_a_material_the_mesh_doesnt_use_doesnt_stop_tiling(ctx)
    await check_a_timer_goes_with_the_parent_its_function_held(ctx)
