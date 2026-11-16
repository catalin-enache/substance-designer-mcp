"""The editor: every panel's screenshot, the clipboard, open_graph fitting the whole graph, then the 3D view set up."""

import asyncio
import contextlib
import os
import re
import sys
from collections.abc import Callable, Sequence
from textwrap import dedent

from test_all_tools import common, window_server
from test_all_tools.common import (
    ABORT_AT,
    TEST_GRAPH,
    Ctx,
    check,
    clipboard_text,
    designer_script,
    helper_lines,
    is_image,
    prepared_call,
    set_clipboard_text,
    skip,
    text,
    until_job_running,
)
from test_all_tools.editor_panels_and_fit import popups, window_states
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
    grey_file,
    moved_left,
    plane_columns,
    plane_height,
    plane_middle,
    plane_width,
    say_failed,
    transitions,
    with_checker,
)
from test_all_tools.editor_panels_and_fit.retries import (
    TRIES,
    no_designer_starting,
    tries_said,
    without_others_in_front,
)
from test_all_tools.editor_panels_and_fit.window_owner import WHO
from test_all_tools.editor_panels_and_fit.window_states import at_rest

TEXT = b'mcp_selftest: the text a 3D capture puts back'
THREE_D = {'panel': '3d', 'max_size': 700}
# a plane seen from the top, framed; what a call sets stays, so the calls after pass only what they change
TOP = {'mesh': 'Plane', 'view': 'Top'}
USERS_3D_VIEW = "it would change the 3D view of the user's Designer"
# getMainWindow() minimized by Qt: the 3D shot un-minimizes it and leaves Designer's window in front, opaque
QT_MINIMIZED = 'qt minimized'


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
    applied = await with_checker(c, {**THREE_D, 'graph': VIEW3D_ADDED})
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
    # its own graph's checker: the check before it may not have run (REVIEW.md TST-386)
    slanted = await with_checker(c, {**THREE_D, 'mesh': 'Plane', 'view': 'Default', 'graph': VIEW3D_GRAPH})
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
    base = await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH, 'tiling': 1.0})
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


async def check_orbit_turns_the_camera_around_what_it_looks_at(ctx: Ctx) -> None:
    """orbit= turns the camera around the point it looks at, by Designer's own left-drags (designer_helpers/view3d.py):
    from Front, [90, 0] is Designer's own Right view and [0, 90] its Top, on a rounded cube, which Frame frames alike
    from every side. Each render is within 3 grey levels on average of that view (0.0 and 0.3 to 1.3 measured; a turn 1
    degree off the Top gave 5 or more) and nearer it than half the view beside it (Left, and Front, which differs from
    the Top by 5 alone); the degrees said are the drags', within half a degree. Two turns in one call, [90, 90] from
    Front, are [0, 90] from Right: a drag too soon after another came out wrong (REVIEW.md TST-336)."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'orbit= turns the camera', USERS_3D_VIEW)
        return
    first = await with_checker(c, {**THREE_D, 'graph': VIEW3D_GRAPH, 'mesh': 'Rounded cube', 'view': 'Front'})
    views = {
        view: await c('screenshot_designer', {**THREE_D, 'view': view}) for view in ('Front', 'Right', 'Left', 'Top')
    }
    right = await c('screenshot_designer', {**THREE_D, 'view': 'Front', 'orbit': [90, 0]})
    up = await c('screenshot_designer', {**THREE_D, 'view': 'Front', 'orbit': [0, 90]})
    both = await c('screenshot_designer', {**THREE_D, 'view': 'Front', 'orbit': [90, 90]})
    one = await c('screenshot_designer', {**THREE_D, 'view': 'Right', 'orbit': [0, 90]})
    shots = [first, *views.values(), right, up, both, one]
    if not all(is_image(r) for r in shots):
        check('screenshot_designer', 'orbit= turns the camera', False, 'a shot failed (below)')
        say_failed('orbit', *shots)
        return
    seen = {view: grey(r) for view, r in views.items()}
    for r, view, beside, way in ((right, 'Right', 'Left', 'right'), (up, 'Top', 'Front', 'up')):
        near, far = difference(grey(r), seen[view]), difference(grey(r), seen[beside])
        said = re.search(r'orbit ([\d.]+) degrees ' + way, text(r))
        check(
            'screenshot_designer',
            'orbit= from Front: 90 degrees %s is the %s view' % (way, view),
            near < min(3.0, 0.5 * far) and said is not None and abs(float(said.group(1)) - 90) <= 0.5,
            '%.2f from %s, %.2f from %s | %s' % (near, view, far, beside, text(r).strip()),
        )
    near, far = difference(grey(both), grey(one)), difference(grey(both), grey(up))
    check(
        'screenshot_designer',
        'orbit=[90, 90] from Front, two turns in one call, is [0, 90] from Right',
        near < min(3.0, 0.5 * far),
        '%.2f from [0, 90] from Right, %.2f from [0, 90] from Front | %s' % (near, far, text(both).strip()),
    )


async def check_pan_moves_the_view_and_zoom_comes_closer_to_the_middle(ctx: Ctx) -> None:
    """pan= moves the view sideways by fractions of it, measured at the point the camera looks at, by Designer's own
    middle-drags (designer_helpers/view3d.py): the plane seen from the top, that point its middle, moves a quarter of
    the view left and down for pan=[0.25, 0.25], within 0.01, as said (a rate 5 % off failed: REVIEW.md TST-335). The
    self-test's view is about 340 px wide in the default docked layout, the one the shared preferences plist carries
    (ROADMAP item 67), near PAN_WIDTH's 356: there it can't tell the rate from content following the mouse one to one,
    which only a view of another size could. A corner of the plane brought to the middle stays there as zoom comes
    closer, 4 steps (ROADMAP item 74: zoom alone comes closer only to the middle)."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'pan= moves the view', USERS_3D_VIEW)
        return
    small = await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH, 'zoom': -4})
    panned = await c('screenshot_designer', {**THREE_D, 'pan': [0.25, 0.25]})  # from where zoom left the camera
    # far enough for the plane, zoomed 4 steps closer from its corner, to stay inside the panel
    far = await c('screenshot_designer', {**THREE_D, 'view': 'Top', 'zoom': -10})
    if not all(is_image(r) for r in (small, panned, far)):
        check('screenshot_designer', 'pan= moves the view', False, 'a shot failed (below)')
        say_failed('pan', small, panned, far)
        return
    h, w = grey(small).shape
    (x0, y0), (x1, y1) = plane_middle(grey(small)), plane_middle(grey(panned))
    moved = ((x0 - x1) / w, (y1 - y0) / h)  # the plane left and down: the view right and up
    said = re.search(r'pan ([\d.]+) of the view right, ([\d.]+) up', text(panned))
    check(
        'screenshot_designer',
        'pan=[0.25, 0.25] moves the view a quarter of it right and up',
        all(0.24 <= m <= 0.26 for m in moved)
        and said is not None
        and all(abs(float(v) - 0.25) <= 0.005 for v in said.groups()),
        'the plane moved %.3f of the view left, %.3f down | %s' % (moved[0], moved[1], text(panned).strip()),
    )
    f = grey(far)
    columns, rows = plane_columns(f), plane_columns(f.T)
    corner = [round((columns[1] + 1 - w / 2) / w, 3), round((h / 2 - rows[0]) / h, 3)]  # its top right, from the middle
    closer = await c('screenshot_designer', {**THREE_D, 'pan': corner, 'zoom': 4})
    if not is_image(closer):
        check('screenshot_designer', 'zoom after pan= comes closer to the middle', False, text(closer).strip())
        return
    z = grey(closer)
    zc, zr = plane_columns(z), plane_columns(z.T)
    grown = (zr[1] - zr[0] + 1) / max(rows[1] - rows[0] + 1, 1)  # the side below the corner
    check(
        'screenshot_designer',
        'zoom after pan= comes closer to what pan brought to the middle',
        abs(zc[1] + 1 - w / 2) <= 0.05 * w
        and abs(zr[0] - h / 2) <= 0.05 * h
        and zr[1] < h - 1
        and STEP**4 * 0.95 <= grown <= STEP**4 * 1.05,  # three steps (1.37x) or five (1.69x) fail
        'the corner at column %d, row %d of %dx%d; the plane %.2fx as high (%.2f^4 = %.2f)%s; panned %s'
        % (
            zc[1] + 1,
            zr[0],
            w,
            h,
            grown,
            STEP,
            STEP**4,
            " | clipped at the panel's bottom: a lower 3D panel" if zr[1] >= h - 1 else '',
            corner,
        ),
    )


MOVES_UNDER_ANY_TOOL = dedent("""
    from PySide6 import QtCore, QtWidgets
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    dock = _3d_dock(mw)  # mw and dock held: without, the viewport's wrapper went stale during the drags
    viewport = [w for w in dock.findChildren(QtWidgets.QWidget) if w.metaObject().className() == 'Alg::Gui3D::ViewportWidget'][0]
    # Designer hidden, the view draws no frame: a move waits for its request for one (_Frames.taking; HLP-149). The
    # wheel and a middle drag change nothing under the Light tool, so the view asks for none: they go without a wait,
    # which would run its limit (REVIEW.md TST-454: 1 s each). The turn moves the light, and waits
    frames = _Frames(viewport, lambda: _3d_render(mw))
    ended = []  # how each wait ended: True as the view asked for a frame, False at its limit
    def taking():
        taken = frames.taking()
        return lambda: ended.append(taken())
    try:
        _wheel(viewport, 3)
        _drag(viewport, QtCore.Qt.MouseButton.MiddleButton, 60, 0, [])
        _drag(viewport, QtCore.Qt.MouseButton.LeftButton, 100, 0, [], taking)
    finally:
        frames.close()
    print('SENT=wheel,pan,turn')
    print('WAITS=%r' % ended)""")


async def check_the_camera_moves_under_the_light_tool_too(ctx: Ctx) -> None:
    """Under the 3D view's Light tool neither the wheel nor a drag moves the camera (a designer fact: zoom= said it
    zoomed, REVIEW.md HLP-120; its snippet says what it sent: TST-335, TST-336), so zoom and pan move it under the
    Camera tool, and the Light tool is selected again after; the Camera tool is put back for the checks after."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'zoom and pan under the Light tool', USERS_3D_VIEW)
        return
    try:
        base = await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})
        light = text(await designer_script(c, 'editor_panels_and_fit/tool_3d', tool='Light'))
        sent = text(await c('execute_designer_code', {'code': ctx.helper_source + MOVES_UNDER_ANY_TOOL}))
        wheeled = await c('screenshot_designer', THREE_D)
        zoomed = await c('screenshot_designer', {**THREE_D, 'view': 'Top', 'zoom': 3})
        after_zoom = text(await designer_script(c, 'editor_panels_and_fit/tool_3d', tool=''))
        panned = await c('screenshot_designer', {**THREE_D, 'view': 'Top', 'pan': [0.25, 0]})
        after_pan = text(await designer_script(c, 'editor_panels_and_fit/tool_3d', tool=''))
    finally:
        await designer_script(c, 'editor_panels_and_fit/tool_3d', tool='Camera')
    shots = [base, wheeled, zoomed, panned]
    if not all(is_image(r) for r in shots):
        check('screenshot_designer', 'zoom and pan under the Light tool', False, 'a shot failed (below)')
        say_failed('the Light tool', *shots)
        return
    side, edges, after = plane_width(grey(base)), plane_columns(grey(base)), plane_columns(grey(wheeled))
    check(
        'designer facts',
        "under the 3D view's Light tool neither the wheel nor a drag moves the camera",
        'TOOL=Light' in light
        and 'SENT=wheel,pan,turn' in sent
        and all(abs(a - b) <= 2 for a, b in zip(edges, after, strict=True)),
        'the plane from column %d to %d, then %d to %d after 3 wheel steps, a pan and a turn | %s'
        % (*edges, *after, light.strip()),
    )
    waits = _read(sent, 'WAITS')
    check(
        'self-test',
        'the moves under the Light tool wait only for a frame the view asks for, none to its limit',
        isinstance(waits, list) and bool(waits) and all(ended is True for ended in waits),
        'how each wait ended (True: the view asked for a frame; False: its limit): %s' % (waits,),
    )
    if 'SENT=wheel,pan,turn' not in sent:  # a check's detail is cut at 150 characters (REVIEW.md TST-341)
        print(
            '      the moves under the Light tool: %s'
            % ' / '.join(line.strip() for line in sent.strip().splitlines()[-3:])
        )
    ratio = plane_width(grey(zoomed)) / max(side, 1)
    check(
        'screenshot_designer',
        'zoom= comes closer under the Light tool too, then selects it again',
        STEP**3 * 0.95 <= ratio <= STEP**3 * 1.05 and 'TOOL=Light' in after_zoom,
        'the plane %.2fx as wide (%.2f^3 = %.2f) | %s' % (ratio, STEP, STEP**3, after_zoom.strip()),
    )
    # its right edge: its left one goes out of view (the plane wider than half the view), every point of it moving alike
    moved = (plane_columns(grey(base))[1] - plane_columns(grey(panned))[1]) / grey(base).shape[1]
    check(
        'screenshot_designer',
        'pan= moves the view under the Light tool too, then selects it again',
        0.24 <= moved <= 0.26 and 'TOOL=Light' in after_pan,
        'the plane moved %.3f of the view left | %s' % (moved, after_pan.strip()),
    )


async def check_a_drag_turns_the_camera_alike_with_selection_on(ctx: Ctx) -> None:
    """With the 3D view's Selection toggle on, orbit= turns the camera and pan= moves the view as with it off, and the
    Parameters panel keeps what it showed (a designer fact: the tool leaves the toggle as the user set it,
    designer_helpers/view3d.py; REVIEW.md TST-336). The turn is nearer the Right view than half the Front, so it
    can't pass on a mesh that looks alike from both, such as a plane edge-on (TST-339); the toggle is off again after,
    as in a Designer just started."""
    c = ctx.c
    if ctx.was_running:
        skip('designer facts', 'drags with Selection on', USERS_3D_VIEW)
        return
    try:
        front = await with_checker(c, {**THREE_D, 'graph': VIEW3D_GRAPH, 'mesh': 'Rounded cube', 'view': 'Front'})
        right = await c('screenshot_designer', {**THREE_D, 'view': 'Right'})
        panel = text(await designer_script(c, 'editor_panels_and_fit/parameters_panel'))
        selection = text(await designer_script(c, 'editor_panels_and_fit/tool_3d', tool='', selection=True))
        turned = await c('screenshot_designer', {**THREE_D, 'view': 'Front', 'orbit': [90, 0]})
        small = await with_checker(c, {**THREE_D, **TOP, 'zoom': -4})
        panned = await c('screenshot_designer', {**THREE_D, 'pan': [0.25, 0]})
        panel_after = text(await designer_script(c, 'editor_panels_and_fit/parameters_panel'))
    finally:
        await designer_script(c, 'editor_panels_and_fit/tool_3d', tool='', selection=False)
    shots = [front, right, turned, small, panned]
    if not all(is_image(r) for r in shots):
        check('designer facts', 'drags with Selection on', False, 'a shot failed (below)')
        say_failed('Selection', *shots)
        return
    near, far = difference(grey(turned), grey(right)), difference(grey(turned), grey(front))
    moved = moved_left(grey(small), grey(panned))
    check(
        'designer facts',
        "with the 3D view's Selection toggle on, a turn and a pan come out alike and the Parameters panel is kept",
        'SELECTION=True' in selection and near < min(3.0, 0.5 * far) and 0.24 <= moved <= 0.26 and panel == panel_after,
        '%.2f from Right, %.2f from Front; panned %.3f | %s | %s (was %s)'
        % (near, far, moved, selection.strip(), panel_after.strip(), panel.strip()),
    )


# the user's mouse, simulated: after a drag's 5th move, a move with no button held at the viewport's corner, sent by
# itself, not by the helpers' _mouse (whose events the drag's guard lets through); the drags find _mouse by name
HOVER_IN_A_DRAG = dedent("""
    from PySide6 import QtCore, QtGui, QtWidgets
    _own_mouse = _mouse
    _moves = [0]
    def _mouse(viewport, kind, x, y, button, buttons):
        _own_mouse(viewport, kind, x, y, button, buttons)
        if kind == QtCore.QEvent.Type.MouseMove and buttons != QtCore.Qt.MouseButton.NoButton:
            _moves[0] += 1
            if _moves[0] == 5:
                at = QtCore.QPointF(5.0, 5.0)
                none = QtCore.Qt.MouseButton.NoButton
                hover = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseMove, at, QtCore.QPointF(viewport.mapToGlobal(at.toPoint())),
                                          none, none, QtCore.Qt.KeyboardModifier.NoModifier)
                QtWidgets.QApplication.sendEvent(viewport, hover)
                print('HOVERED')
    set_3d_view(None, None, VIEW, 0, None, ORBIT, PAN)""")


async def check_the_users_mouse_doesnt_stop_a_turn_or_pan(ctx: Ctx) -> None:
    """A move of the user's mouse over the 3D view in a drag, with no button held, ended Designer's drag: the turn or
    pan stopped partway and was said as done (REVIEW.md HLP-122: orbit=[90, 0] 60.27 from the Right view, pan=[0.25, 0]
    0.099 of the view). With one sent mid-drag, outside the tool's own mouse events, orbit=[90, 0] from Front is still
    the Right view and pan=[0.25, 0] still moves the view a quarter."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', "the user's mouse in a drag", USERS_3D_VIEW)
        return
    first = await with_checker(c, {**THREE_D, 'graph': VIEW3D_GRAPH, 'mesh': 'Rounded cube', 'view': 'Front'})
    right = await c('screenshot_designer', {**THREE_D, 'view': 'Right'})
    turn = 'VIEW, ORBIT, PAN = %r, %r, %r\n' % ('Front', [90.0, 0.0], None)
    turned_said = text(await c('execute_designer_code', {'code': ctx.helper_source + turn + HOVER_IN_A_DRAG}))
    turned = await c('screenshot_designer', THREE_D)
    small = await with_checker(c, {**THREE_D, **TOP, 'zoom': -4})
    pan = 'VIEW, ORBIT, PAN = %r, %r, %r\n' % (None, None, [0.25, 0.0])
    panned_said = text(await c('execute_designer_code', {'code': ctx.helper_source + pan + HOVER_IN_A_DRAG}))
    panned = await c('screenshot_designer', THREE_D)
    shots = [first, right, turned, small, panned]
    if not all(is_image(r) for r in shots):
        check('screenshot_designer', "the user's mouse in a drag", False, 'a shot failed (below)')
        say_failed("the user's mouse in a drag", *shots)
        return
    near, far = difference(grey(turned), grey(right)), difference(grey(turned), grey(first))
    check(
        'screenshot_designer',
        "the user's mouse moving in a drag doesn't stop orbit=",
        'HOVERED' in turned_said and near < min(3.0, 0.5 * far),
        '%.2f from Right, %.2f from Front | %s' % (near, far, turned_said.strip()[-90:]),
    )
    moved = moved_left(grey(small), grey(panned))
    check(
        'screenshot_designer',
        "the user's mouse moving in a drag doesn't stop pan=",
        'HOVERED' in panned_said and 0.24 <= moved <= 0.26,
        'the plane moved %.3f of the view left | %s' % (moved, panned_said.strip()[-90:]),
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
    r = await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH, 'tiling': 1.0})
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
    before = await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH, 'tiling': 1.0})
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
    # the dialog unhides a hidden Designer, which then stayed over the user's windows (2026-11-15): Designer's windows
    # and the dialog transparent meanwhile, then Designer hidden again and its windows opaque (window_states, at rest),
    # whatever raises meanwhile (REVIEW.md TST-425); not hidden, left transparent, and NOT_HIDDEN said (TST-478)
    mac = _mac_window(mw)
    hidden = mac is not None and mac.hidden()
    def fade_it():
        dialog = QtWidgets.QApplication.activeModalWidget()
        if dialog is None:
            fader.start(0)
        else:
            dialog.setWindowOpacity(0.0)
    fader = QtCore.QTimer(); fader.setSingleShot(True); fader.timeout.connect(fade_it)
    def name_it():  # Materials > Add asks a name, in a dialog of its own: named as it opens
        dialog = QtWidgets.QApplication.activeModalWidget()
        if isinstance(dialog, QtWidgets.QInputDialog):
            dialog.setTextValue('mcp_selftest_material'); dialog.accept()
        elif dialog is not None:
            dialog.close()
        else:
            timer.start(0)
    timer = QtCore.QTimer(); timer.setSingleShot(True); timer.timeout.connect(name_it)
    menu = _menu_action(bar, keep, 'Materials').menu(); keep.append(menu)
    def materials():
        menu.aboutToShow.emit(); _process_events()
        return [a.text() for a in menu.actions() if a.menu() is not None and a.text()]
    try:
        if hidden:
            for w in mac.windows(True):
                mac.set_appearance(w, 0.0, True)
            fader.start(0)
        timer.start(0)
        _menu_action(bar, keep, 'Materials', 'Add').trigger()
        for _ in range(30):  # nothing says it was added (TST-421): looked at every 100 ms, never inside a wait's own loop
            if 'mcp_selftest_material (unused)' in materials():  # materials() runs Designer's events itself
                break
            _settle(0.1)
    finally:
        timer.stop(); fader.stop()
        if hidden:
            top = mw.window()  # held: a handle taken through a wrapper dropped at once is deleted (REVIEW.md TST-432)
            handle = top.windowHandle()
            spy = _event_signal(handle, ('Expose',))
            try:
                mac.hide()
                _until(lambda: mac.hidden() and not handle.isExposed(), 3.0, [spy.fired])  # off screen again
            finally:
                handle.removeEventFilter(spy)
                if mac.hidden():  # opaque on the user's screen otherwise (REVIEW.md TST-478, as _CLEAR: TST-474)
                    for w in mac.windows(True):
                        mac.set_appearance(w, 1.0, False)
            print('HIDDEN AGAIN=%s' % mac.hidden())
            if not mac.hidden():
                print("NOT_HIDDEN Designer wasn't hidden again: its windows left transparent and click-through")
    print('MATERIALS=%r' % materials())""")


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
    window_states.stopped_if_shown(added)  # its windows transparent on screen: no shot after it (REVIEW.md TST-478)
    r = await c('screenshot_designer', {**THREE_D, 'tiling': 2.0})
    check(
        'screenshot_designer',
        "tiling= isn't stopped by a material the mesh doesn't use",
        'mcp_selftest_material (unused)' in added
        and (sys.platform != 'darwin' or 'HIDDEN AGAIN=True' in added)  # REVIEW.md TST-425: was printed, never judged
        and is_image(r)
        and 'tiling 2 ' in text(r),
        '%s | %s' % (added.strip()[-160:], text(r)),
    )


# a shot's window put on screen and back (_on_screen) with Designer hidden, aborted at the first of __LINES__ it reaches
# (common.ABORT_AT). The windows' looks are given back by the snippet, only once Designer is hidden again, so none shows
# opaque on the user's screen whatever the abort left
SHOT_ABORTED = dedent("""
    mw = _APP.getQtForPythonUIMgr().getMainWindow(); keep = [mw]
    mac = _mac_window(mw)
    frames = _Frames(_viewport(_3d_dock(mw)), lambda: _3d_render(mw))
    looks, first = _Screen.unfade, _Screen.opaque_first
    screens = []
    _Screen.unfade = lambda self: screens.append(self)
    _Screen.opaque_first = lambda self: None
    def shot():
        with _on_screen(mw, frames):
            pass
    try:
        print('HIDDEN_BEFORE=%s' % mac.hidden())
        _aborted_at(__LINES__, shot)
        print('HIDDEN_AFTER=%s' % mac.hidden())
    finally:
        _Screen.unfade, _Screen.opaque_first = looks, first
        frames.close()
        if not mac.hidden():
            mac.hide()
        if screens:  # its looks back once off screen
            screens[0]._wait_off_screen()
            looks(screens[0])
""")


async def check_an_abort_putting_a_shots_window_back_still_hides_designer_again(ctx: Ctx) -> None:
    """An abort landing on a 3D shot's step putting Designer's window back, here hiding Designer again, still hides it
    (REVIEW.md HLP-180: the handler after it gave the windows their look back where they were, and left Designer shown
    on the user's screen). The abort is the plugin's, raised by a tracer of the check's at that line. macOS only, where
    the shot puts the window on screen."""
    c = ctx.c
    name = "an abort putting a shot's window back still hides Designer again"
    if sys.platform != 'darwin' or ctx.was_running:
        skip('screenshot_designer', name, 'macOS only, in a Designer the self-test started, hidden at rest')
        return
    lines = helper_lines(ctx.helper_source, r'^\s+mac\.hide\(\)$')
    code = SHOT_ABORTED.replace('__LINES__', repr(lines))
    t = text(await c('execute_designer_code', {'code': ctx.helper_source + ABORT_AT + code}))
    read = ' '.join(re.findall(r'^(?:HIDDEN_\w+=\w+|ABORTED)$', t, re.M))
    check(
        'screenshot_designer',
        name,
        len(lines) == 1 and read == 'HIDDEN_BEFORE=True ABORTED HIDDEN_AFTER=True',
        '%s | %d lines | %s' % (read, len(lines), t.strip()[-200:]),
    )


# the 3D view's overlay count read at each of its paints, and its UpdateRequests (the view asking for a frame), by a spy
# of the snippet's own (designer_helpers/frames3d.py): at rest; through a pan and a viewpoint, Designer's window on
# screen as a shot puts it; with Display > Samples off, a pan drawn after; then as the window comes on screen from
# hidden, once right after a pan made while hidden and once with nothing changed; then what each pan brings while
# Designer is hidden again. Each time Qt stops exposing the window while it is read on screen is recorded (COVERS), and
# so is the window's state where a wait on screen ran out (STATES; REVIEW.md TST-444). The snippet runs after WHO
# (window_owner.py)
FRAMES = dedent("""
    import contextlib
    from PySide6 import QtCore, QtWidgets
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    dock = _3d_dock(mw)
    bar = dock.findChildren(QtWidgets.QMenuBar)[0]
    viewport = _viewport(dock)
    labels = viewport.findChildren(QtWidgets.QLabel)
    keep = [mw, dock, bar, viewport] + labels
    count = lambda: _samples([label.text() for label in labels])
    read = []  # (kind, the count read), each event
    spy = _event_signal(viewport, ('Paint', 'UpdateRequest'), lambda kind: read.append((kind, count())))
    frames = _Frames(viewport, lambda: _3d_render(mw))
    mac = _mac_window(mw)
    handle = mw.windowHandle()
    reading = []  # the stretch read with the window on screen, while it is (watched)
    covers = []  # each time Qt stopped exposing the window during one: the stretch, macOS's covered, the windows in front

    def unexposed(kind):
        if reading and not handle.isExposed():
            covers.append((reading[-1], mac.covered(), [who(n) for n in mac.in_front()]))
    exposed = _event_signal(handle, ('Expose',), unexposed)

    @contextlib.contextmanager
    def watched(stretch):  # entered once the window is on screen (_on_screen's own wait)
        reading.append(stretch)
        try:
            yield
        finally:
            reading.pop()

    states = []  # where a wait on screen ran out: the part, and the window's state then

    def state(part):
        states.append((part, dict(exposed=handle.isExposed(), hidden=mac.hidden(), minimized=mac.minimized(),
                                  covered=mac.covered(), in_front=[who(n) for n in mac.in_front()])))
    MIDDLE = QtCore.Qt.MouseButton.MiddleButton
    rest = count()
    paints = lambda events: [n for kind, n in events if kind == 'Paint']
    pan = lambda dx: _drag(viewport, MIDDLE, dx, 0, [])

    def back(seen):
        return any(n is not None and n < rest for n in seen) and seen[-1] == rest

    def after(change, part, done=lambda events: False):
        start = len(read)
        change()
        if not _until(lambda: done(read[start:]) or back(paints(read[start:])), 3.0, [spy.fired]):
            state(part)
        return paints(read[start:])

    try:
        print('REST=%r' % rest)
        with _on_screen(mw, frames), watched('pan, viewpoint, samples'):
            print('PAN=%r' % after(lambda: pan(30), 'pan'))
            print('VIEW=%r' % after(lambda: _menu_action(bar, keep, 'Camera', 'Front').trigger(), 'viewpoint'))
            display = _menu_action(bar, keep, 'Display', 'Samples')
            display.trigger()  # off: the label changes at the next frame
            try:
                after(lambda: pan(10), 'samples off', lambda events: len(paints(events)) > 0 and count() is None)
                print('OFF=%r' % count())
            finally:
                display.trigger()
                after(lambda: pan(-10), 'samples on', lambda events: count() == rest)
        def asked_since(start):
            return any(kind == 'UpdateRequest' for kind, _ in read[start:])
        for case in ('CHANGED', 'UNCHANGED', 'TAKEN'):
            if case == 'CHANGED':
                pan(-30)  # hidden: the view draws no frame; shown at once after
            elif case == 'TAKEN':  # as the shot's moves are: its UpdateRequest waited for (taken), then shown at once
                start = len(read)
                pan(30)
                _until(lambda: asked_since(start), 1.0, [spy.fired])
            hidden = mac.hidden()
            start = len(read)
            with _on_screen(mw, frames), watched('shown, ' + case.lower()):
                # Designer's own restart and return, whenever the shot's wait ended
                if case != 'UNCHANGED' and not _until(lambda: back(paints(read[start:])), 3.0, [spy.fired]):
                    state('shown, ' + case.lower())
            print('SHOWN_%s=%r' % (case, (hidden, read[start:start + 16])))
        print('COVERS=%r' % covers)
        print('STATES=%r' % states)
        hidden, asked, stretch = mac.hidden(), [], len(read)
        for dx in (30, 30, 30, -30, -30, -30):  # hidden again: what each pan brings while the view draws nothing
            start = len(read)
            pan(dx)
            _until(lambda: any(kind == 'UpdateRequest' for kind, _ in read[start:]), 1.0, [spy.fired])
            asked.append(tuple(kind for kind, _ in read[start:]))
        print('HIDDEN_ASKS=%r' % ((hidden, asked),))
        print('HIDDEN_PAINTS=%d' % len(paints(read[stretch:])))  # each pan's, up to the last one's UpdateRequest
    finally:
        viewport.removeEventFilter(spy)
        handle.removeEventFilter(exposed)
        frames.close()""")


def _read(said: str, name: str) -> object:
    """The value a snippet printed as NAME=<repr>, or None."""
    import ast

    found = re.search(r'^%s=(.*)$' % name, said, re.M)
    return ast.literal_eval(found.group(1)) if found else None


def _shown(events: object, changed: bool) -> bool:
    """FRAMES' events as the window came on screen from hidden: after a change, the first paint reading 8, then an
    UpdateRequest, then a paint reading a restart; with nothing changed, two paints or more, each reading 8, and no
    UpdateRequest."""
    if not (isinstance(events, tuple) and events[0] is True and isinstance(events[1], list)):
        return False
    seen: list[tuple[str, int | None]] = events[1]
    paints = [n for kind, n in seen if kind == 'Paint']
    if not changed:
        return len(paints) >= 2 and all(n == 8 for n in paints) and all(kind == 'Paint' for kind, _ in seen)
    asked = [i for i, (kind, _) in enumerate(seen) if kind == 'UpdateRequest']
    restart = [i for i, (kind, n) in enumerate(seen) if kind == 'Paint' and n is not None and n < 8]
    return paints[:1] == [8] and bool(asked) and bool(restart) and asked[0] < restart[0]


def _changed_by_its_second_paint(events: object) -> bool:
    """FRAMES' events as the window came on screen: by the second paint, an UpdateRequest came or that paint read a
    restart (below 8); with nothing changed, neither (_shown)."""
    if not (isinstance(events, tuple) and isinstance(events[1], list)):
        return False
    seen: list[tuple[str, int | None]] = events[1]
    paints = [i for i, (kind, _) in enumerate(seen) if kind == 'Paint']
    if len(paints) < 2:
        return False
    second = seen[paints[1]][1]
    return any(kind == 'UpdateRequest' for kind, _ in seen[: paints[1]]) or (second is not None and second < 8)


def _restarted(seen: object, rest: object) -> bool:
    """FRAMES' counts read after a change: `rest`, the count at rest, then a restart (below 8), then back to it."""
    return (
        isinstance(seen, list)
        and len(seen) >= 3
        and seen[0] == rest
        and any(n is not None and n < 8 for n in seen[1:])
        and seen[-1] == rest
    )


def _held(seen: object, rest: object) -> bool:
    """FRAMES' counts read after a viewpoint: restarted (_restarted), the lowest count read at two paints or more, held
    while the camera turns."""
    return isinstance(seen, list) and _restarted(seen, rest) and seen.count(min(n for n in seen if n is not None)) >= 2


async def check_the_3d_views_frames_say_when_it_has_drawn(ctx: Ctx) -> None:
    """The 3D view's paints, its UpdateRequests and its overlay's sample count, what screenshot_designer('3d') waits on
    instead of fixed times (designer_helpers/frames3d.py; REVIEW.md HLP-148): 8 at rest; restarted by a pan and a
    viewpoint, the first paint after each still reading the count before, the viewpoint's restart held while the
    camera turns, then back to 8; no count with Display > Samples off; and as Designer's window comes on screen from
    hidden, right after a pan made meanwhile an UpdateRequest then a restart, with nothing changed only paints reading
    8; Designer hidden, an UpdateRequest after each pan and no paint, what a move off screen waits for (_Frames.taking;
    REVIEW.md HLP-149). macOS only (the window hidden and shown through _MacWindow), in a Designer the self-test
    started.

    Read again, once, when another window covered Designer's while it was read on screen. The view then draws nothing
    more, so the reading measures nothing of it (REVIEW.md TST-444). Read while no worker of the pool starts or quits
    its Designer (no_designer_starting: REVIEW.md TST-417, TST-453, TST-467)."""
    c = ctx.c
    what = "the 3D view's overlay counts its samples, restarted by each change"
    if ctx.was_running or sys.platform != 'darwin':
        skip('designer facts', what, USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    with no_designer_starting():
        for last in (False, True):
            await c('screenshot_designer', {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})
            said = text(await c('execute_designer_code', {'code': ctx.helper_source + WHO + FRAMES}))
            covers = _read(said, 'COVERS')
            if not covers:
                break
            # printed whole, as a check's detail is cut: (the stretch, macOS's covered, the windows in front of it)
            print('      covered while read on screen%s: %r' % ('' if last else ', read again', covers))
    rest, pan, view = (_read(said, name) for name in ('REST', 'PAN', 'VIEW'))
    check(
        'designer facts',
        what,
        rest == 8 and _restarted(pan, rest) and _held(view, rest),
        'at rest %r; a pan %r; a viewpoint %r' % (rest, pan, view),
    )
    states = _read(said, 'STATES')
    if states:  # printed whole, as a check's detail is cut: the window's state where a wait ran out (REVIEW.md TST-444)
        shot = [line for line in said.splitlines() if line.startswith("Designer's window: ")]
        print('      where a wait on screen ran out: %r; the show: %s' % (states, ' / '.join(shot)))
    check(
        'designer facts',
        'with Display > Samples off, the overlay shows no count',
        'OFF=None' in said,
        said.strip().splitlines()[-1] if 'OFF=' not in said else 'OFF=%r' % _read(said, 'OFF'),
    )
    changed, unchanged = _read(said, 'SHOWN_CHANGED'), _read(said, 'SHOWN_UNCHANGED')
    check(
        'designer facts',
        'shown from hidden, the 3D view asks for a frame and restarts after a pan made meanwhile, and does neither '
        'with nothing changed',
        _shown(changed, True) and _shown(unchanged, False),
        '(hidden before, events) after a pan %r; with nothing changed %r' % (changed, unchanged),
    )
    taken = _read(said, 'SHOWN_TAKEN')
    check(
        'designer facts',
        # whether Designer was hidden before the show, and the pan's UpdateRequest came before it, isn't judged
        # (REVIEW.md TST-439)
        'shown after a pan, the 3D view asks for a frame or restarts by its second paint (what _Frames.shown tells a '
        'change from none by: REVIEW.md HLP-151)',
        _changed_by_its_second_paint(taken),
        '(hidden before, events) %r' % (taken,),
    )
    hidden_asks = _read(said, 'HIDDEN_ASKS')
    each = hidden_asks[1] if isinstance(hidden_asks, tuple) and hidden_asks[0] is True else []
    check(
        'designer facts',
        "Designer hidden, the 3D view asks for a frame after each pan, and draws none up to the last one's ask",
        len(each) == 6
        and all('UpdateRequest' in kinds and 'Paint' not in kinds for kinds in each)
        and 'HIDDEN_PAINTS=0' in said,  # REVIEW.md TST-429: a paint after a pan's ask fell in no slice
        '(hidden, the events after each pan) %r; paints over the stretch: %r'
        % (hidden_asks, _read(said, 'HIDDEN_PAINTS')),
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


async def check_the_3d_view_isnt_drawn_while_designers_window_is_off_screen(ctx: Ctx, in_front: bool = False) -> None:
    """While macOS has Designer's window minimized or hidden, the 3D view's render stays the last frame it drew: a pan by
    the helpers' own drag leaves it identical. Covered by a window of Designer's own, it is said, not judged: in
    Designers launch_designer opened (`open`), the pan changed it in some, as Qt kept the window exposed, and left it in
    others, 6 of 6 tries each, in two Designers (REVIEW.md SRV-152, TST-433, 2026-11-15). What decides it isn't known.
    With the window covered, then made transparent and click-through and brought in front, the pan changes it. A page
    Qt minimized isn't
    measured: nothing says when its view stops drawing, which some runs saw and others didn't (the user's choice,
    REVIEW.md TST-420). macOS minimizing the window leaves getMainWindow()'s isMinimized() False, the top-level
    window's True, and the window not exposed (designer facts: designer_helpers/shot3d.py, REVIEW.md SRV-146,
    TST-391). With `in_front`, the two ways in front of the user's windows instead: on screen and partly covered, the
    pan changes it too; run() runs them with the other checks that need a window there. A drawn way with a window of
    another app found in front of Designer's is taken again (without_others_in_front), and the ways are read while no
    Designer of the run starts or quits (no_designer_starting: REVIEW.md TST-417). macOS only, in a Designer the
    self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip('designer facts', "the 3D view isn't drawn off screen", USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH, 'zoom': -4})
    seen: dict[str, str] = {}
    states: dict[str, dict[str, str]] = {}
    unclear = []  # drawn ways with another app's window in front in every try
    off_screen = [way for way in window_states.WAYS if way != QT_MINIMIZED]
    ways = [None, 'partly covered'] if in_front else [*off_screen, 'transparent in front']
    with no_designer_starting():
        for way in ways:
            drawn_way = way is None or way in window_states.DRAWN
            t, _ = await without_others_in_front(ctx, window_states.panned(way), TRIES if drawn_way else 1)
            if drawn_way and not window_states.nothing_in_front(t):
                unclear.append(way or 'on screen')
            m = re.search(r'SAME=(\w+)', t)
            seen[way or 'on screen'] = m.group(1) if m else t.strip().splitlines()[-1] if t.strip() else '?'
            states[way or 'on screen'] = window_states.states(t.split('SAME=')[0]).get('STATE', {})
    said = '%srender unchanged by a pan: %s' % (
        'another app in front in each try: %s; ' % ', '.join(unclear) if unclear else '',
        ', '.join('%s %s' % item for item in seen.items()),
    )
    if in_front:
        check(
            'designer facts',
            "the 3D view's render is drawn while Designer's window is on screen or partly covered",
            [seen[way] for way in ('on screen', 'partly covered')] == ['False', 'False'] and not unclear,
            said,
        )
        return
    still = [way for way in off_screen if way != 'covered']  # its last frame: minimized, hidden
    off = [way for way in still if seen[way] == 'True']  # covered: said, not judged (REVIEW.md TST-433)
    # REVIEW.md TST-401: the transparent way as set up, in front of its cover, not merely drawn
    transparent = states['transparent in front']
    set_up = (transparent.get('opacity'), transparent.get('through'), transparent.get('covered')) == (
        '0',
        'True',
        'False',
    ) and window_states.ahead(transparent.get('order', ''), 'main', 'cover')
    check(
        'designer facts',
        "the 3D view's render is drawn while Designer's window is transparent in front, not minimized or hidden",
        off == still and seen['transparent in front'] == 'False' and set_up and not unclear,
        said,
    )
    print(
        '      covered: %s'
        % {'False': 'drawn, Qt keeping the window exposed', 'True': 'not drawn'}.get(seen['covered'], seen['covered'])
    )
    if not set_up:  # a check's detail is cut at 150 characters (REVIEW.md TST-334)
        print('      transparent in front: %s' % ' '.join('%s=%s' % item for item in transparent.items()))
    minimized = states['minimized']
    check(
        'designer facts',
        "macOS minimizing Designer's window: getMainWindow() not minimized for Qt, the top-level window minimized",
        minimized.get('minimized') == 'True'
        and minimized.get('qt_minimized') == 'False'
        and minimized.get('top_minimized') == 'True'
        and minimized.get('exposed') == 'False',
        ' '.join('%s=%s' % item for item in minimized.items()) or 'no state read',
    )


async def check_a_click_goes_through_designers_window_once_transparent_and_click_through(ctx: Ctx) -> None:
    """Designer's window in front of another window: a click at its middle would reach it opaque, and transparent too,
    but the window under it once also click-through (ignoresMouseEvents), as the 3D shot makes it (designer facts:
    designer_helpers/shot3d.py). Asked of macOS (NSWindow's windowNumberAtPoint): no click is made. A reading with a
    window of another app found in front of Designer's is taken again (without_others_in_front), and read while no
    Designer of the run starts or quits (no_designer_starting: REVIEW.md TST-417). macOS only, in a Designer the
    self-test started."""
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'designer facts',
            "a click goes through Designer's window once transparent and click-through",
            "it would move the user's Designer window" if ctx.was_running else 'macOS only',
        )
        return
    with no_designer_starting():
        t, tried = await without_others_in_front(ctx, window_states.hits())
    m = re.search(r'HITS (.*)', t)
    seen = m.group(1) if m else (t.strip().splitlines() or ['?'])[-1]
    check(
        'designer facts',
        "a click on Designer's window reaches it opaque or transparent, the window under it once also click-through",
        window_states.nothing_in_front(t) and seen == 'opaque=main transparent=main through=cover',
        seen + tries_said(t, tried),
    )


async def check_a_window_under_designers_transparent_window_counts_as_visible(ctx: Ctx) -> None:
    """A window of Designer's own, shown alone in front of its main window first, then whole under it, counts as covered
    for macOS (occlusionState) with the main window opaque, and as visible with it transparent and click-through, as
    the 3D shot makes it: the shot doesn't tell the apps under it that their windows are covered (designer facts:
    designer_helpers/shot3d.py; REVIEW.md HLP-141). A window never shown read covered either way, so the reading alone
    in front comes first (REVIEW.md TST-412). A reading with a window of another app found in front of the window it
    reads is taken again (without_others_in_front), and read while no worker of the pool starts or quits its Designer
    (no_designer_starting: REVIEW.md TST-417, TST-467). macOS only, in a Designer the self-test started."""
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'designer facts',
            "a window under Designer's transparent window counts as visible",
            "it would move the user's Designer window" if ctx.was_running else 'macOS only',
        )
        return
    with no_designer_starting():
        t, tried = await without_others_in_front(ctx, window_states.under())
    m = re.search(r'UNDER (.*)', t)
    seen = m.group(1) if m else (t.strip().splitlines() or ['?'])[-1]
    check(
        'designer facts',
        "a window under Designer's window: visible alone, covered under it opaque, visible under it transparent and "
        'click-through',
        window_states.nothing_in_front(t) and seen == 'alone=False opaque=True transparent=False',
        seen + tries_said(t, tried),
    )


POPUP_MS = 20  # ms Designer's popups may be on screen during a 3D shot: about a frame at 60 Hz; 9 ms the most measured


async def check_a_3d_shot_with_graph_keeps_the_explorers_menu_off_the_screen(ctx: Ctx) -> None:
    """screenshot_designer('3d', graph=...) applies the graph's outputs through the Explorer's context menu, a popup
    above every window (designer_helpers/view3d.py). With Designer's window minimized, the shot otherwise invisible, a
    watch of the window server's list (popups.py) sees Designer's popups on screen at an opacity above 0 for at most
    POPUP_MS (REVIEW.md HLP-134: 240 ms). macOS only, in a Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d with graph=: the Explorer's menu off the screen",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})
    pid = int(text(await c('execute_designer_code', {'code': "print(__import__('os').getpid())"})).strip())
    try:
        await c('execute_designer_code', {'code': ctx.helper_source + window_states.put('minimized')})
        with popups.PopupWatch(pid) as watch:
            r = await c('screenshot_designer', {**THREE_D, 'graph': VIEW3D_GRAPH})
    finally:
        await at_rest(c, ctx.helper_source)
    check(
        'screenshot_designer',
        "3d with graph=, Designer's window minimized: the Explorer's menu on screen at most %d ms" % POPUP_MS,
        # REVIEW.md TST-405: samples that listed a window of Designer's, so the watch could see its popups
        is_image(r) and watch.listed > 100 and watch.shown_ms <= POPUP_MS,
        "popups on screen for %.0f ms, in %d of %d samples, %d listing Designer's windows"
        % (watch.shown_ms, len(watch.times), watch.samples, watch.listed),
    )
    if not is_image(r):
        print('      the shot: %s' % ' / '.join(text(r).strip().splitlines()[-3:]))


async def check_a_3d_shot_with_graph_makes_the_explorers_menu_click_through(ctx: Ctx) -> None:
    """screenshot_designer('3d', graph=...) makes the Explorer's context menu it opens transparent and click-through
    (designer_helpers/view3d.py): a click the user makes at its place goes to the window under it, as through
    Designer's window (the user's choice: DECISIONS.md), and its action is still picked: the shot is taken. Read inside
    Designer as the menu's action is picked, through shoot_3d, the helper the tool calls, Designer's window minimized.
    macOS only, in a Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d with graph=: the Explorer's menu click-through",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    path = os.path.join(ctx.scratch, 'menu.png')
    try:
        await c('execute_designer_code', {'code': ctx.helper_source + window_states.put('minimized')})
        t = text(await c('execute_designer_code', {'code': ctx.helper_source + popups.menu_look(path, VIEW3D_GRAPH)}))
    finally:
        await at_rest(c, ctx.helper_source)
    looks = re.findall(r'MENU (opacity=\S+ through=\S+)', t)
    check(
        'screenshot_designer',
        "3d with graph=: the Explorer's menu transparent and click-through as its action is picked, the shot taken",
        looks == ['opacity=0 through=True'] and '3d render ' in t,
        'the menu: %s' % (', '.join(looks) or (t.strip().splitlines() or ['?'])[-1]),
    )


async def check_an_explorers_menu_closed_before_its_pick_is_said_so_and_gets_its_look_back(ctx: Ctx) -> None:
    """screenshot_designer('3d', graph=...) whose Explorer's menu is closed by something else in every try, once the
    shot made it transparent and click-through, before its action is picked: the shot says so, not that the menu didn't
    open, and gives each menu's window its look back, opaque and clickable (REVIEW.md HLP-146: the Explorer deleted the
    menu, and its window stayed transparent and click-through). Through shoot_3d, each menu closed by the snippet as
    the fade made it transparent. macOS only, in a Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d with graph=: an Explorer's menu closed before its pick",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    path = os.path.join(ctx.scratch, 'closed_early.png')
    try:
        t = text(
            await c('execute_designer_code', {'code': ctx.helper_source + popups.closed_early(path, VIEW3D_GRAPH)})
        )
    finally:
        await at_rest(c, ctx.helper_source)
    m = re.search(r'SHOT (.*)', t)
    said = m.group(1) if m else '?'
    tries = re.search(r'in each of (\d+) tries', said)
    looks = re.findall(r'MENU_AFTER (.*)', t)
    check(
        'screenshot_designer',
        "3d with graph=: an Explorer's menu closed before its action is picked in every try is said so, and each gets "
        'its look back',
        'closed before its action was picked' in said
        and tries is not None
        and looks == ['opacity=1 through=False'] * int(tries.group(1)),
        '%s; the menus after: %s' % (said, ', '.join(looks) or 'not read'),
    )


async def check_wheel_steps_sent_as_designers_window_goes_off_screen_are_all_taken(ctx: Ctx) -> None:
    """screenshot_designer('3d', zoom=...) whose window goes off screen during its wheel steps, as a click on the user's
    own window covers Designer's during a shot, zooms as far as the same zoom undisturbed (REVIEW.md HLP-149: off
    screen the view draws no frame, the wait for the next one returned at once, and the steps went back to back, as
    the frames fact measured some lost). Designer hidden at the first step, through shoot_3d. macOS only, in a Designer
    the self-test started."""
    c = ctx.c
    what = "3d with zoom=: the wheel steps sent as Designer's window goes off screen are all taken"
    if ctx.was_running or sys.platform != 'darwin':
        skip('screenshot_designer', what, USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    zoom = 6
    await c('screenshot_designer', {**THREE_D, **TOP})
    # through shoot_3d too, saved alike: a tool's shot is shrunk to max_size, a render saved by shoot_3d isn't
    # (REVIEW.md TST-423)
    alike = os.path.join(ctx.scratch, 'undisturbed_zoom.png')
    said = text(await c('execute_designer_code', {'code': ctx.helper_source + 'shoot_3d(%r, zoom=%d)' % (alike, zoom)}))
    await c('screenshot_designer', {**THREE_D, **TOP})  # framed again
    path = os.path.join(ctx.scratch, 'hidden_mid_zoom.png')
    try:
        t = text(
            await c('execute_designer_code', {'code': ctx.helper_source + window_states.hidden_mid_zoom(path, zoom)})
        )
    finally:
        await at_rest(c, ctx.helper_source)
    hidden = 'HIDDEN_AT_THE_FIRST_STEP exposed=False' in t
    if not (os.path.exists(alike) and os.path.exists(path)):
        check('screenshot_designer', what, False, 'a shot failed (below)')
        print('      undisturbed: %s' % ' / '.join(said.strip().splitlines()[-3:]))
        print('      hidden at the first step: %s' % ' / '.join(t.strip().splitlines()[-3:]))
        return
    apart = difference(grey_file(alike), grey_file(path))
    check(
        'screenshot_designer',
        what,
        hidden and apart < 1.0,
        'hidden at the first step: %s; mean difference from the same zoom undisturbed %.2f grey levels'
        % (hidden, apart),
    )


async def check_an_explorers_menu_closed_before_its_pick_is_opened_again(ctx: Ctx) -> None:
    """screenshot_designer('3d', graph=...) whose Explorer's menu is closed by something else in the first try, before
    its action is picked, opens it again and takes the shot, the graph's outputs applied (REVIEW.md HLP-147: one
    close refused the whole shot; twice in a full run, by something not found). The closed menu's window gets its look
    back. Through shoot_3d, the menu closed by the snippet as the fade made it transparent. macOS only, in a Designer
    the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d with graph=: an Explorer's menu closed once before its pick",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    path = os.path.join(ctx.scratch, 'closed_once.png')
    try:
        t = text(
            await c(
                'execute_designer_code',
                {'code': ctx.helper_source + popups.closed_early(path, VIEW3D_GRAPH, tries=1)},
            )
        )
    finally:
        await at_rest(c, ctx.helper_source)
    m = re.search(r'SHOT (.*)', t)
    said = m.group(1) if m else '?'
    looks = re.findall(r'MENU_AFTER (.*)', t)
    applied = "graph %s's outputs on the mesh" % VIEW3D_GRAPH in t  # the set-up's line: what it set
    check(
        'screenshot_designer',
        "3d with graph=: an Explorer's menu closed before its pick is opened again, and the outputs applied",
        said == 'taken' and applied and os.path.exists(path) and looks == ['opacity=1 through=False'],
        '%s; applied: %s; the closed menu after: %s' % (said, applied, ', '.join(looks) or 'not read'),
    )


SHOWN = {
    'minimized': "Designer's window: shown, transparent and without taking focus, as its 3D view isn't drawn while "
    'minimized',
    'qt minimized': "Designer's window: un-minimized, as its 3D view isn't drawn while minimized; it stays so",
    'covered': "Designer's window: brought in front, transparent and without taking focus, as its 3D view may not be "
    'drawn while covered',
    'hidden': "Designer's window: shown, transparent and without taking focus, as its 3D view isn't drawn while "
    'Designer is hidden',
}
# the state each way leaves after the shot: as it was (the user's choice: DECISIONS.md), but for a page Qt minimized,
# which no user does, in a window macOS shows. A hidden Designer reads covered whatever the order (REVIEW.md TST-422),
# so the covered way's put-back is judged not hidden too (TST-438)
AFTER = {
    'minimized': (('minimized', 'True'),),
    'qt minimized': (('qt_minimized', 'False'),),
    'covered': (('covered', 'True'), ('hidden', 'False')),
    'hidden': (('hidden', 'True'),),
}


async def check_a_3d_shot_puts_designers_window_on_screen_without_taking_focus(
    ctx: Ctx, in_front: bool = False
) -> None:
    """screenshot_designer('3d') with Designer's window minimized, covered or hidden (window_states) puts it on screen
    first, without making Designer the active app, so its render follows the pan: the plane moves a quarter of the
    view from where a shot on screen just before showed it (REVIEW.md SRV-146: that shot came back, the view's last
    frame). It says what it did, and puts the window back as it was, opaque and clickable (DECISIONS.md): a minimized
    window minimized again, a covered one sent back behind, a hidden Designer hidden again. A page Qt minimized stays
    un-minimized. The covered window goes back right behind the window in front of it, not behind
    every window: Designer's own window behind it stays behind it (REVIEW.md HLP-126). For the covered way the plane's
    move alone doesn't show the window was brought in front: in some Designers launch_designer opened, Qt kept a
    covered window exposed and its view drew (REVIEW.md TST-433), so where the window is at each render is judged by
    check_a_3d_shot_keeps_designers_window_transparent_and_click_through_while_off_screen. Focus is judged from the state
    just before the shot, when Designer wasn't the active app then (window_states.focus; REVIEW.md TST-392, TST-418).
    A way in which Designer became the active app during the shot is taken again, up to TRIES times: the pool's other
    Designers can hand it activation, and a shot that makes it the active app itself does so each time
    (window_states.activated). So a defect seen in fewer tries passes; what each try taken again said of the active app
    is printed (REVIEW.md TST-464). The ways are shot while no worker of the pool starts or quits its Designer
    (no_designer_starting: REVIEW.md TST-417, TST-467). The page Qt minimized runs only with `in_front`: the shot leaves Designer's window in front of
    the user's, opaque (2026-11-15), so run() runs it with the other checks that need a window there. macOS only, in a
    Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d with Designer's window off screen",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})
    with no_designer_starting():
        for way in [way for way in window_states.WAYS if (way == QT_MINIMIZED) == in_front]:
            tried = 0
            retaken: list[str] = []  # what each try taken again said: what a pass leaves out (REVIEW.md TST-464)
            while tried < TRIES:
                tried += 1
                # the frame a stale shot repeats
                base = await c('screenshot_designer', {**THREE_D, 'view': 'Top', 'zoom': -4})
                put = text(await c('execute_designer_code', {'code': ctx.helper_source + window_states.put(way)}))
                try:
                    # the pan alone: set up with the zoom, it comes before it, and the zoom shrinks it
                    # (view3d.py's order)
                    r = await c('screenshot_designer', {**THREE_D, 'pan': [0.25, 0.0]})
                    after = window_states.states(
                        text(
                            await c(
                                'execute_designer_code',
                                {
                                    'code': ctx.helper_source
                                    + window_states.read(window_states.showing(*('%s=%s' % f for f in AFTER[way])))
                                },
                            )
                        )
                    )
                finally:
                    await at_rest(c, ctx.helper_source)
                before, off = window_states.states(put).get('BEFORE', {}), window_states.states(put).get('STATE', {})
                state = after.get('STATE', {})
                shot = is_image(base) and is_image(r)
                if not (shot and window_states.activated(text(r), off, state)):  # REVIEW.md TST-418
                    break
                said = [line.strip() for line in text(r).splitlines() if 'active app' in line]
                retaken.append(
                    'try %d: active before %s, after %s; %s'
                    % (tried, off.get('active'), state.get('active'), ' | '.join(said) or 'the shot said nothing of it')
                )
            what = "3d with Designer's window %s: put on screen without taking focus" % way
            if not shot:
                check('screenshot_designer', what, False, 'a shot failed (below)')
                say_failed(way, base, r)
                continue
            moved = moved_left(grey(base), grey(r))
            kept = window_states.focus(off, state)
            activated = window_states.activated(text(r), off, state)
            ok = (
                0.24 <= moved <= 0.26
                and SHOWN[way] in text(r)
                and all(state.get(key) == value for key, value in AFTER[way])
                and (state.get('opacity'), state.get('through')) == ('1', 'False')
                and (way != 'covered' or state.get('order') == off.get('order') == 'cover,main,below')
                and kept is not False
                and not activated
            )
            tries = '; %d tries' % tried if tried > 1 else ''
            check('screenshot_designer', what, ok, 'the plane moved %.3f of the view left%s' % (moved, tries))
            for reading in retaken:
                print('      taken again, ' + reading)
            if kept is None:
                print("      focus not judged: Designer was the active app before the shot, or its state wasn't read")
            if activated:
                print('      Designer became the active app during the shot in each of %d tries' % tried)
            if not ok:  # a check's detail is cut at 150 characters (REVIEW.md TST-334)
                for label, seen in (('before', before), ('off screen', off), ('after the shot', state)):
                    print('      %s: %s' % (label, ' '.join('%s=%s' % item for item in seen.items()) or 'not read'))
                lines = [line for line in text(r).splitlines() if line.startswith("Designer's window: ")]
                print("      the shot's lines about the window: %s" % (' / '.join(lines) or 'none'))


# Designer's window on screen, left transparent and click-through, as by a shot cut off midway
LEFT_TRANSPARENT = 'left transparent by an earlier shot'
LEAVE_TRANSPARENT = 'mac.set_appearance(mac.windows(False)[0], 0.0, True)\n'
OPAQUE_AGAIN = "Designer's window: made opaque again, as an earlier shot left it transparent"
AFTER_KEYS = ('opacity', 'through', 'faded')  # the window's state after the shot the check reads


def _anywhere(state: dict[str, str]) -> bool:
    """BROUGHT_ON_SCREEN's judgement for a window on screen already: none."""
    return True


# each way's window brought on screen as a render is read (a RENDER line): Designer's main window ahead of its cover,
# un-minimized, Designer no longer hidden (REVIEW.md TST-433)
BROUGHT_ON_SCREEN: dict[str, Callable[[dict[str, str]], bool]] = {
    'covered': lambda one: window_states.ahead(one.get('order', ''), 'main', 'cover'),
    'minimized': lambda one: one.get('minimized') == 'False',
    'hidden': lambda one: one.get('hidden') == 'False',
}
SET_UP_STEP = '3D view, setting: '  # a set-up step's line, said as it begins


async def check_a_3d_shot_keeps_designers_window_transparent_and_click_through_while_off_screen(
    ctx: Ctx, in_front: bool = False
) -> None:
    """While screenshot_designer('3d') reads the renders of Designer's window minimized, covered or hidden
    (window_states), the window is on screen (BROUGHT_ON_SCREEN), transparent and click-through. For a hidden Designer,
    every window of its
    own is, as it shows them all (REVIEW.md TST-403). After the shot every window is opaque and clickable again (the
    user's choice: DECISIONS.md). A window on screen that an earlier shot left transparent is made opaque first, and
    said. The renders aren't judged when the shot says Designer became the active app, which makes its windows
    opaque; the state after the shot still is (REVIEW.md TST-410). Read as each render is read, through
    shoot_3d, the helper the tool calls. With `in_front`, the window left transparent instead: on screen, in front of
    the user's windows, and made opaque by the shot; run() runs it with the other checks that need a window there.
    macOS only, in a Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d with Designer's window off screen: transparent and click-through while rendered",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})
    path = os.path.join(ctx.scratch, 'transparent.png')
    for way in (LEFT_TRANSPARENT,) if in_front else ('minimized', 'covered', 'hidden'):
        await c('screenshot_designer', {**THREE_D, 'view': 'Top'})  # framed again: each case pans
        on_screen = window_states.put('on screen') + LEAVE_TRANSPARENT  # in front of the user's windows
        off = on_screen if way == LEFT_TRANSPARENT else window_states.put(way)
        try:
            await c('execute_designer_code', {'code': ctx.helper_source + off})
            t = text(await c('execute_designer_code', {'code': ctx.helper_source + window_states.rendered(path)}))
            after = window_states.states(
                text(await c('execute_designer_code', {'code': ctx.helper_source + window_states.read()}))
            )
        finally:
            await at_rest(c, ctx.helper_source)
        seen = window_states.renders(t)
        state = after.get('STATE', {})
        # transparent and click-through as each render is read, and not covered for macOS: brought in front once the
        # unhide took, no window is in front of it (REVIEW.md HLP-160, TST-446). Brought on screen, as Designer's own
        # windows and macOS's state say it: in some Designers launch_designer opened, Qt kept a covered window exposed
        # and its view drew, so the renders can't tell (REVIEW.md TST-433)
        brought = BROUGHT_ON_SCREEN.get(way, _anywhere)
        placed = sum(bool(brought(one)) for one in seen)
        covers = sorted({one.get('covered') for one in seen}, key=str)
        looks = sorted({(one.get('opacity'), one.get('through')) for one in seen}, key=str)
        during = ('1', 'False') if way == LEFT_TRANSPARENT else ('0', 'True')
        # REVIEW.md TST-403: Designer's windows not opaque and clickable, of all of them: every one for a hidden
        # Designer, as it shows them all; none after the shot
        fadings = {(one.get('faded'), one.get('windows')) for one in seen}
        faded = {'hidden': {(n, n) for _, n in fadings}, LEFT_TRANSPARENT: {('0', n) for _, n in fadings}}.get(
            way, {('1', n) for _, n in fadings}
        )
        # REVIEW.md TST-410: Designer made the active app during the shot (the pool handing activation over as a
        # Designer quits, or a click: TST-399) makes its windows opaque, so the renders aren't judged
        switched = window_states.MADE_OPAQUE in t or window_states.LEFT_UP in t
        ok = (
            switched
            or (
                len(seen) >= 2  # before the pan and after it, and any taken again (REVIEW.md TST-404)
                and placed == len(seen)
                and (way == LEFT_TRANSPARENT or covers == ['False'])
                and looks == [during]
                and fadings == faded
                and (way != LEFT_TRANSPARENT or OPAQUE_AGAIN in t)
            )
        ) and (state.get('opacity'), state.get('through'), state.get('faded')) == ('1', 'False', '0')
        what = "3d with Designer's window %s: %s at each render, opaque and clickable after" % (
            way,
            'opaque' if way == LEFT_TRANSPARENT else 'on screen, transparent and click-through',
        )
        check(
            'screenshot_designer',
            what,
            ok,
            # the state after first, the one thing judged once Designer became the active app (REVIEW.md TST-414)
            'after: %s; %s%d renders, %d brought on screen, (opacity, through) at them: %s, (faded, windows): %s, '
            'covered: %s'
            % (
                ' '.join('%s=%s' % (k, state.get(k)) for k in AFTER_KEYS),
                'renders not judged, as Designer became the active app; ' if switched else '',
                len(seen),
                placed,
                looks,
                sorted(fadings, key=str),
                covers,
            ),
        )
        if not ok:  # a check's detail is cut at 150 characters (REVIEW.md TST-334)
            lines = [line for line in t.splitlines() if line.startswith(("Designer's window: ", 'RENDER'))]
            print("      the shot's lines: %s" % (' / '.join(lines) or ' / '.join(t.strip().splitlines()[-3:])))


async def check_a_3d_shot_makes_designers_window_opaque_at_once_once_designer_is_the_active_app(ctx: Ctx) -> None:
    """screenshot_designer('3d') with Designer's window minimized, Designer becoming the active app as the set-up
    starts, makes the window opaque and clickable at once, says so, renders it so and leaves it up: left transparent,
    the user who switched to Designer would see no window, and a click would go through it to the app under it
    (REVIEW.md HLP-136). Designer is the active app as the helpers see it (window_states.switched), so the user's
    keyboard stays where it is. Through shoot_3d, the helper the tool calls. macOS only, in a Designer the self-test
    started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            '3d with Designer made the active app during the shot: its window opaque at once',
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})
    path = os.path.join(ctx.scratch, 'switched.png')
    await c('screenshot_designer', {**THREE_D, 'view': 'Top'})  # framed again: the shot pans
    try:
        await c('execute_designer_code', {'code': ctx.helper_source + window_states.put('minimized')})
        t = text(await c('execute_designer_code', {'code': ctx.helper_source + window_states.switched(path)}))
        after = window_states.states(
            text(await c('execute_designer_code', {'code': ctx.helper_source + window_states.read()}))
        ).get('STATE', {})
    finally:
        await at_rest(c, ctx.helper_source)
    seen = [(one.get('opacity'), one.get('through')) for one in window_states.renders(t)]
    ok = (
        len(seen) >= 2  # before the set-up, transparent; after it, any taken again included
        and seen[0] == ('0', 'True')
        and set(seen[1:]) == {('1', 'False')}
        # before the set-up's first step, not only before the next render (REVIEW.md TST-409)
        and window_states.MADE_OPAQUE in t
        and SET_UP_STEP in t
        and t.index(window_states.MADE_OPAQUE) < t.index(SET_UP_STEP)
        and (after.get('minimized'), after.get('opacity'), after.get('through')) == ('False', '1', 'False')
    )
    check(
        'screenshot_designer',
        '3d, Designer made the active app as the set-up starts: the window opaque at once, rendered so, left up',
        ok,
        '(opacity, through) at the renders: %s; said: %s; after: minimized=%s opacity=%s'
        % (seen, window_states.MADE_OPAQUE in t, after.get('minimized'), after.get('opacity')),
    )
    if not ok:
        lines = [line for line in t.splitlines() if line.startswith(("Designer's window: ", '3D view'))]
        print("      the shot's lines: %s" % (' / '.join(lines) or ' / '.join(t.strip().splitlines()[-3:])))


# shoot_3d with a pan, the image removed
PAN = dedent("""
    import os, tempfile
    out = os.path.join(tempfile.mkdtemp(prefix='mcp_selftest_'), 'shot.png')
    shoot_3d(out, pan=[0.25, 0.0])
    os.remove(out)
    os.rmdir(os.path.dirname(out))
""")
# Designer's window left as it is by the shot: no _MacWindow, as elsewhere than macOS
AS_IT_IS = '_mac_window = lambda mw: None\n'


async def check_a_render_that_didnt_follow_a_pan_is_said(ctx: Ctx) -> None:
    """A render identical to the one before a pan is said, after its retakes (designer_helpers/shot3d.py, STALE; REVIEW.md
    SRV-146): with Designer's window minimized and left so, the render is the view's last frame (covered, it was drawn
    in some Designers launch_designer opened: REVIEW.md TST-433). On screen the pan changes the render, and nothing is
    said: Designer's QImage compares pixels. macOS only (the window minimized through _MacWindow), in a Designer the
    self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d: a render that didn't follow a pan",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH, 'zoom': -4})
    # on screen as the shot puts it: a window over Designer's would leave the render stale (REVIEW.md TST-390)
    on = text(await c('execute_designer_code', {'code': ctx.helper_source + PAN}))
    try:
        put = window_states.put('minimized')
        off = text(await c('execute_designer_code', {'code': ctx.helper_source + put + AS_IT_IS + PAN}))
    finally:
        await at_rest(c, ctx.helper_source)
    said_on, said_off = ('3D render: identical' in t for t in (on, off))
    check(
        'screenshot_designer',
        "3d: a render that didn't follow a pan is said; one that did isn't",
        said_off and not said_on and 'pan 0.25 of the view right' in off,
        'said with the window minimized: %s; on screen: %s' % (said_off, said_on),
    )
    if not said_off or said_on:  # a check's detail is cut at 150 characters (REVIEW.md TST-334)
        for label, t in (('on screen', on), ('minimized', off)):
            print('      %s: %s' % (label, ' / '.join(t.strip().splitlines()[-3:])))


NOT_JUDGED = 'Designer became the active app during the shot, which leaves its window up (REVIEW.md TST-399)'


async def check_a_window_covered_during_a_3d_shot_is_put_in_front_again(ctx: Ctx) -> None:
    """A window brought over Designer's as screenshot_designer('3d')'s pan begins, as a user's click on their own window
    would, is seen before the render: Designer's window comes in front again, without taking focus, and the render
    follows the pan, the plane moving a quarter of the view (REVIEW.md HLP-124: the render was the view's last frame,
    and nothing was said). It goes back behind that window after. When Designer became the active app during the shot,
    which brings its windows in front and leaves them up, only the pan is judged (REVIEW.md TST-399). Through shoot_3d,
    the helper the tool calls, to bring the window over during the shot. macOS only, in a Designer the self-test
    started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d with a window brought over Designer's during the shot",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})
    base = await c('screenshot_designer', {**THREE_D, 'view': 'Top', 'zoom': -4})
    path = os.path.join(ctx.scratch, 'covered_during_pan.png')
    try:
        # on screen first, as a window the user is looking at: from hidden, the shot hides Designer again, and a hidden
        # Designer reads covered whatever the order (REVIEW.md TST-422)
        await c('execute_designer_code', {'code': ctx.helper_source + window_states.put('on screen')})
        t = text(
            await c('execute_designer_code', {'code': ctx.helper_source + window_states.during_pan(path, 'cover')})
        )
        after = window_states.states(
            text(
                await c(
                    'execute_designer_code',
                    {'code': ctx.helper_source + window_states.read(window_states.in_order([('cover', 'main')]))},
                )
            )
        )
    finally:
        await at_rest(c, ctx.helper_source)
    what = "3d with a window brought over Designer's during the shot: in front again, the render following the pan"
    if not (is_image(base) and os.path.exists(path)):
        check('screenshot_designer', what, False, 'a shot failed (below)')
        say_failed('before the pan', base)
        print('      the pan: %s' % ' / '.join(t.strip().splitlines()[-3:]))
        return
    moved = moved_left(grey(base), grey_file(path))
    state = after.get('STATE', {})
    # Designer made the active app meanwhile brings its windows in front, and is left up: only the pan is judged then
    judged = not window_states.became_active(t, window_states.states(t).get('BEFORE', {}), state)
    behind = state.get('hidden') == 'False' and window_states.ahead(state.get('order', ''), 'cover', 'main')
    ok = 0.24 <= moved <= 0.26 and (not judged or (window_states.AGAIN in t and behind))
    check('screenshot_designer', what, ok, 'the plane moved %.3f of the view left' % moved)
    if not judged:
        print('      put-back not judged: ' + NOT_JUDGED)
    if not ok:  # a check's detail is cut at 150 characters (REVIEW.md TST-334)
        lines = [line for line in t.splitlines() if line.startswith(("Designer's window: ", '3D render: ', 'covered'))]
        print("      the shot's lines: %s" % (' / '.join(lines) or 'none'))
        print('      after the shot: %s' % (' '.join('%s=%s' % item for item in state.items()) or 'not read'))


# where a shot puts back Designer's window, covered at its start, by what became of the windows meanwhile: the way it
# was covered, what happens as the pan begins (window_states.EVENTS), what is expected, the put-back lines it may say,
# and Designer's windows each pair lists, the first in front of the second after the shot. A normal window coming in
# front of Designer's meanwhile (another worker's Designer opening, in the full run) is then the one in front: the
# window goes back behind it, still not behind every window, which the order shows (REVIEW.md HLP-130)
BEHIND = 'put back behind the window that was in front of it'
GONE = 'left in front, as the window that was in front of it is no longer on screen'
NONE_FOUND = 'left in front, as no window was found in front of it'
STAYS = 'left in front, or behind a window come in front of it meanwhile'
PUT_BACK = {
    # behind every window, as it is set up (window_states): nothing on the user's screen
    'covered, nothing done during the shot': (
        'covered',
        None,
        'put back behind its cover',
        (BEHIND,),
        (('cover', 'main'), ('main', 'below')),
    ),
    'covered again during the shot': (
        'covered',
        'later',
        'put back behind its first cover',
        (BEHIND,),
        (('cover', 'main'), ('main', 'below')),
    ),
    'its cover closed during the shot': ('covered', 'close', STAYS, (GONE, BEHIND), (('main', 'below'),)),
    'its cover minimized during the shot': ('covered', 'minimize', STAYS, (GONE, BEHIND), (('main', 'below'),)),
    window_states.ON_TOP: (window_states.ON_TOP, None, STAYS, (NONE_FOUND, BEHIND), (('main', 'below'),)),
    # REVIEW.md HLP-139: behind its cover, not only behind the window that was directly in front of it
    'covered, the smaller window in front of it raised during the shot': (
        window_states.TWO,
        'raise',
        'put back behind its cover and that window',
        (BEHIND,),
        (('cover', 'main'), ('later', 'main'), ('main', 'below')),
    ),
}
# the cases in front of the user's windows, run with the other checks that need a window there (run): a window brought
# over Designer's, which the shot keeps in front of every window, or raised there; its cover closed or minimized; a
# cover always on top. Set up 'covered', behind every window, the cover-closed and cover-minimized cases accept either
# put-back: once the cover is gone, a window of another app's in front of Designer's is put back behind (BEHIND), and
# only with none is the window left in front (GONE; REVIEW.md TST-435)
PUT_BACK_IN_FRONT = frozenset(PUT_BACK) - {'covered, nothing done during the shot'}


async def check_a_covered_window_goes_back_behind_its_cover_or_stays_in_front_once_the_cover_is_gone(
    ctx: Ctx, in_front: bool = False
) -> None:
    """Designer's window, covered as screenshot_designer('3d') starts, goes back right behind the window that covered
    it, also when another window comes over it during the shot (REVIEW.md HLP-131: it went back behind that later
    window, in front of its cover). When that cover is closed or minimized during the shot, it stays in front, or goes
    back behind a window of another app's in front of it, which the way set up behind every window has (both accepted:
    REVIEW.md TST-435). It stays in front when no normal window covered it (an always-on-top window), unless a normal
    window came in front of it meanwhile: behind a window off screen, or sent to the back, it went behind every window
    (REVIEW.md HLP-130). Read in the
    order of Designer's own windows, a window of its own behind it. It goes back behind its cover, not only behind the
    window directly in front of it, when that window is raised during the shot (REVIEW.md HLP-139). Each case's event
    is seen to have happened (window_states.SEEN_BY: REVIEW.md TST-415). Not judged when Designer became the active
    app during the shot, which leaves its window up (REVIEW.md TST-399). Through shoot_3d, to act on the windows
    during the shot. Only the case set up behind every window runs, or with `in_front` the cases in front of the user's
    windows (PUT_BACK_IN_FRONT), which run() runs with the other checks that need a window there. macOS only, in a
    Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d with Designer's window covered: put back behind its cover, or left in front once it is gone",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})
    for case, (way, event, expected, said, pairs) in PUT_BACK.items():
        if (case in PUT_BACK_IN_FRONT) != in_front:
            continue
        await c('screenshot_designer', {**THREE_D, 'view': 'Top'})  # framed again: each case pans
        path = os.path.join(ctx.scratch, 'put_back.png')
        try:
            await c('execute_designer_code', {'code': ctx.helper_source + window_states.put(way)})
            t = text(
                await c('execute_designer_code', {'code': ctx.helper_source + window_states.during_pan(path, event)})
            )
            after = window_states.states(
                text(
                    await c(
                        'execute_designer_code',
                        {'code': ctx.helper_source + window_states.read(window_states.in_order(pairs))},
                    )
                )
            )
        finally:
            await at_rest(c, ctx.helper_source)
        order = after.get('STATE', {}).get('order', '')
        put_back = [one for one in said if ("Designer's window: " + one) in t]
        state = after.get('STATE', {})
        judged = not window_states.became_active(t, window_states.states(t).get('BEFORE', {}), state)
        # REVIEW.md TST-415: an event that did nothing would pass on the put-back it was made to catch
        happened = window_states.event_seen(event, t, state)
        # a hidden Designer still lists its windows' order (REVIEW.md TST-438): a put-back that hid it would pass
        shown = state.get('hidden') == 'False'
        ok = not judged or (
            happened and bool(put_back) and shown and all(window_states.ahead(order, a, b) for a, b in pairs)
        )
        what = "3d with Designer's window %s: %s" % (case, expected)
        seen = (put_back[0] if put_back else 'not said') if judged else 'not judged: ' + NOT_JUDGED
        event_said = '' if happened else '%s not seen to happen; ' % event
        check('screenshot_designer', what, ok, '%s%s; order after: %s' % (event_said, seen, order))
        if not ok:  # a check's detail is cut at 150 characters (REVIEW.md TST-334)
            lines = [one for one in t.splitlines() if one.startswith(("Designer's window: ", 'cover', 'its cover'))]
            print("      the shot's lines: %s" % ' / '.join(lines or t.strip().splitlines()[-3:]))


async def check_a_refused_3d_set_up_leaves_designers_window_as_it_was(ctx: Ctx) -> None:
    """screenshot_designer('3d') refusing a set-up the 3D view rules out (an orbit of less than a pixel's drag) refuses
    before it puts Designer's window on screen: a minimized window stays minimized, and nothing is said of it
    (REVIEW.md HLP-127). macOS only, in a Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d: a refused set-up leaves Designer's window as it was",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})
    try:
        await c('execute_designer_code', {'code': ctx.helper_source + window_states.put('minimized')})
        r = await c('screenshot_designer', {**THREE_D, 'orbit': [0.2, 0.0]})
        after = window_states.states(
            text(await c('execute_designer_code', {'code': ctx.helper_source + window_states.read()}))
        )
    finally:
        await at_rest(c, ctx.helper_source)
    minimized = after.get('STATE', {}).get('minimized')
    check(
        'screenshot_designer',
        "3d: a set-up the view rules out is refused before Designer's window changes",
        not is_image(r)
        and 'less than one pixel' in text(r)
        and "Designer's window" not in text(r)
        and minimized == 'True',
        'refused: %s; minimized after: %s' % (not is_image(r), minimized),
    )
    if is_image(r) or "Designer's window" in text(r):
        print('      the result: %s' % ' / '.join(text(r).strip().splitlines()))


async def check_a_plain_3d_shot_shows_a_change_made_while_designers_window_was_off_screen(
    ctx: Ctx, in_front: bool = False
) -> None:
    """A plain screenshot_designer('3d'), nothing set up, of Designer's window minimized, covered or hidden shows the
    3D view as it was changed off screen (a pan by the helpers' own drag, which the view doesn't draw there): the shot
    is the one taken on screen afterwards, and differs from the one before the change (REVIEW.md TST-393: the commonest
    call, with no comparison to tell a stale render). Its covered case can't tell a shot that brought the window in front
    from one that didn't where Qt keeps a covered window exposed, as in some Designers launch_designer opened (REVIEW.md
    TST-433): check_a_3d_shot_keeps_designers_window_transparent_and_click_through_while_off_screen judges where the
    window is at each render. The page Qt minimized runs only with `in_front`, as in
    check_a_3d_shot_puts_designers_window_on_screen_without_taking_focus. macOS only, in a Designer the self-test
    started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d, nothing set up, with Designer's window off screen",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH, 'zoom': -4})
    for way in [way for way in window_states.WAYS if (way == QT_MINIMIZED) == in_front]:
        await at_rest(c, ctx.helper_source)  # at rest, hidden
        base = await c('screenshot_designer', THREE_D)
        try:
            await c('execute_designer_code', {'code': ctx.helper_source + window_states.put_and_drag(way, 40)})
            plain = await c('screenshot_designer', THREE_D)
        finally:
            await at_rest(c, ctx.helper_source)
        later = await c('screenshot_designer', THREE_D)
        await c('execute_designer_code', {'code': ctx.helper_source + window_states.drag(-40)})
        what = "3d, nothing set up, with Designer's window %s: the view as changed off screen" % way
        if not (is_image(base) and is_image(plain) and is_image(later)):
            check('screenshot_designer', what, False, 'a shot failed (below)')
            say_failed(way, base, plain, later)
            continue
        changed, same = difference(grey(base), grey(plain)), difference(grey(plain), grey(later))
        check(
            'screenshot_designer',
            what,
            changed > 1 and same < 0.5,
            'differs from the view before by %.2f grey levels, from one on screen after by %.2f' % (changed, same),
        )


# set_3d_view turning the camera to Front, Designer's window as window_states.put left it
VIEWPOINT_SET = "set_3d_view(None, None, 'Front')\n"
PUT_BACK_AS = {'hidden': ('hidden', 'True'), 'minimized': ('minimized', 'True')}  # each way, after the set-up


async def check_a_viewpoint_set_off_screen_is_turned_with_designers_window_on_screen(ctx: Ctx) -> None:
    """set_3d_view setting a viewpoint with Designer hidden or its window minimized shows the window, transparent and
    click-through, for the camera's turn and Frame, as the 3D shot does, then puts it back as it was: off screen the
    view draws no frame, and nothing says when the turn ended (designer_helpers/frames3d.py; REVIEW.md HLP-158, the
    user's choice). The view is then at that viewpoint: a plain shot after it is the one view='Front' takes. macOS
    only, in a Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "set_3d_view(view=) with Designer's window off screen",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})
    for way, (key, value) in PUT_BACK_AS.items():
        await c('screenshot_designer', {**THREE_D, 'view': 'Top'})  # from Top again: each case turns to Front
        try:
            await c('execute_designer_code', {'code': ctx.helper_source + window_states.put(way)})
            t = text(
                await c('execute_designer_code', {'code': ctx.helper_source + VIEWPOINT_SET + window_states.read()})
            )
        finally:
            await at_rest(c, ctx.helper_source)
        plain = await c('screenshot_designer', THREE_D)
        front = await c('screenshot_designer', {**THREE_D, 'view': 'Front'})
        what = "set_3d_view(view=) with Designer's window %s: turned with the window on screen, transparent" % way
        if not (is_image(plain) and is_image(front)):
            check('screenshot_designer', what, False, 'a shot failed (below)')
            say_failed(way, plain, front)
            continue
        state = window_states.states(t).get('STATE', {})
        shown = "Designer's window: shown, transparent" in t
        apart = difference(grey(plain), grey(front))
        check(
            'screenshot_designer',
            what,
            shown and state.get(key) == value and '3D view: view Front, framed' in t and apart < 0.5,
            'shown: %s; %s=%s after; the view %.2f grey levels from view=Front' % (shown, key, state.get(key), apart),
        )
        if not shown or state.get(key) != value:  # a check's detail is cut at 150 characters (REVIEW.md TST-334)
            print("      set_3d_view's lines: %s" % ' / '.join(t.strip().splitlines()[-4:]))


# Designer hidden, at rest: its window brought on screen as a 3D shot does (_on_screen), then read once macOS no
# longer says Designer is hidden: (whether macOS said so, the windows in front of it, the times Qt stopped exposing the
# window once it had). Run after WHO (window_owner.py)
SHOWN_FROM_HIDDEN = dedent("""
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    frames = _Frames(_viewport(_3d_dock(mw)), lambda: _3d_render(mw))
    mac = _mac_window(mw)
    handle = mw.windowHandle()
    exposed, lost = [False], [0]  # exposed once, then no longer: covered
    def seen(kind):
        if handle.isExposed():
            exposed[0] = True
        elif exposed[0]:
            lost[0] += 1
    spy = _event_signal(handle, ('Expose',), seen)
    try:
        print('HIDDEN_BEFORE=%r' % mac.hidden())
        with _on_screen(mw, frames):
            unhidden = _until(lambda: not mac.hidden(), 3.0, [spy.fired])
            print('SHOT=%r' % ((unhidden, [who(n) for n in mac.in_front()], lost[0]),))
    finally:
        handle.removeEventFilter(spy)
        frames.close()""")


async def check_a_hidden_designers_window_is_brought_in_front_for_a_3d_shot_once_its_unhide_took(ctx: Ctx) -> None:
    """A 3D shot brings a hidden Designer's window in front once macOS no longer says Designer is hidden: no normal
    window is in front of it then (designer_helpers/shot3d.py; REVIEW.md HLP-160). Brought in front before that, the
    window went behind the active app's window as the unhide took, in some runs. Judged only while the active app shows
    a window, which Designer's could go behind; when no window or no active app can be read, it fails, as that can't be
    told. Taken again, up to TRIES times, while a window is in front: a window of the user's, raised by a click through
    Designer's click-through window, reads as the defect (REVIEW.md TST-445). It fails only if every try finds one, so
    a defect seen in fewer tries passes; what each try taken again read is printed (REVIEW.md TST-464). Read while no
    worker of the pool starts or quits its Designer (no_designer_starting: REVIEW.md TST-417, TST-453, TST-467). macOS
    only, in a Designer the self-test started."""
    what = "3d with Designer hidden: no normal window in front of its window once Designer's unhide took"
    if ctx.was_running or sys.platform != 'darwin':
        skip('screenshot_designer', what, USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    with no_designer_starting():
        active = window_server.active_app()
        windows = window_server.windows_now()
        shows = window_server.active_shows_a_window(active, windows)
        if shows is None:
            check(
                'screenshot_designer',
                what,
                False,
                "can't tell: the active app %r, %d windows read" % (active, len(windows)),
            )
            return
        if not shows:
            skip('screenshot_designer', what, "the active app shows no window that Designer's could go behind")
            return
        tried, before, read = 0, None, None
        retaken: list[str] = []  # what each try taken again read: what a pass leaves out (REVIEW.md TST-464)
        while tried < TRIES:
            tried += 1
            said = text(await ctx.c('execute_designer_code', {'code': ctx.helper_source + WHO + SHOWN_FROM_HIDDEN}))
            before, read = _read(said, 'HIDDEN_BEFORE'), _read(said, 'SHOT')
            if not (isinstance(read, tuple) and read[1]):  # no window in front, or nothing read: judged at once
                break
            retaken.append(
                'try %d: hidden before %r; (unhidden, the windows in front of it, exposed no longer) %r'
                % (tried, before, read)
            )
    check(
        'screenshot_designer',
        what,
        before is True and read == (True, [], 0),
        'hidden before: %r; (unhidden, the windows in front of it, exposed no longer) %r; %d tries'
        % (before, read, tried),
    )
    for reading in retaken:
        print('      taken again, ' + reading)


# The 3D view's count before any shot, then a 3D shot as screenshot_designer('3d') takes it (shoot_3d), saved to PATH,
# the renders' comparisons it ran counted: (the count before, the comparisons, the count after)
FIRST_SHOT = dedent("""
    from PySide6 import QtWidgets
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    dock = _3d_dock(mw)  # held: without, the viewport's wrapper went stale
    viewport = _viewport(dock)
    def shows():
        return _samples([label.text() for label in viewport.findChildren(QtWidgets.QLabel)])
    before = shows()
    compared = []
    alike = _Frames._renders_alike
    def counted(self, *args, **kw):
        compared.append(1)
        return alike(self, *args, **kw)
    _Frames._renders_alike = counted
    try:
        shoot_3d(PATH)
    finally:
        _Frames._renders_alike = alike
    print('FIRST_SHOT=%r' % ((before, len(compared), shows()),))""")


# set_3d_view with no move, off screen, in a Designer whose 3D view never drew: the count the overlay showed first
# (COUNT_BEFORE), then the mesh set up, Sphere, then Plane; no graph's outputs, which a later check puts on the mesh
# itself
NEVER_DREW = dedent("""
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    watch = _Frames(_viewport(_3d_dock(mw)), lambda: None)
    print('COUNT_BEFORE=%r' % (watch.count(),))
    watch.close()
    set_3d_view(mesh='Sphere')
    set_3d_view(mesh='Plane')""")


async def check_set_3d_view_sets_up_a_view_that_never_drew(ctx: Ctx) -> None:
    """set_3d_view with no move, off screen, in a Designer launch_designer opened hidden, whose 3D view never drew: the
    mesh is switched to Sphere, then to Plane, and the steps' waits take no render, which such a view doesn't give
    (designer_helpers/frames3d.py; REVIEW.md HLP-170: it raised "the 3D view did not produce a render" after switching
    the mesh). Skipped when a count shows before: the view drew already. run() takes it before any 3D shot. macOS
    only, in a Designer the self-test started."""
    what = 'set_3d_view sets the mesh up off screen in a Designer whose 3D view never drew'
    if ctx.was_running or sys.platform != 'darwin':
        skip('screenshot_designer', what, USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    r = await ctx.c('execute_designer_code', {'code': ctx.helper_source + NEVER_DREW})
    said = text(r)
    if 'COUNT_BEFORE=None' not in said and 'COUNT_BEFORE=' in said:
        skip('screenshot_designer', what, 'the 3D view drew before: its overlay shows a count')
        return
    check(
        'screenshot_designer',
        what,
        not r.is_error and '3D view: Sphere' in said and '3D view: Plane' in said,
        said.strip()[-200:],
    )


async def check_the_first_3d_shot_in_a_designer_opened_hidden_waits_on_the_views_count(ctx: Ctx) -> None:
    """The first 3D shot in a Designer launch_designer opened hidden waits on the 3D view's count, comparing no renders,
    though the overlay showed no count before it: the view hadn't drawn (designer_helpers/frames3d.py; REVIEW.md
    HLP-162: made then, the shot's watch compared renders for the whole shot). Skipped when a count shows before the
    shot: the view drew already. run() takes it before any other 3D shot. macOS only, in a Designer the self-test
    started."""
    what = "3d: the first shot in a Designer opened hidden waits on the view's count, comparing no renders"
    if ctx.was_running or sys.platform != 'darwin':
        skip('screenshot_designer', what, USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    path = os.path.join(ctx.scratch, 'first_shot.png')
    said = text(
        await ctx.c('execute_designer_code', {'code': ctx.helper_source + FIRST_SHOT.replace('PATH', repr(path))})
    )
    read = _read(said, 'FIRST_SHOT')
    if isinstance(read, tuple) and read[0] is not None:
        skip('screenshot_designer', what, 'the 3D view drew before: its overlay shows a count, %r' % (read[0],))
        return
    check(
        'screenshot_designer',
        what,
        isinstance(read, tuple) and read[1] == 0 and read[2] is not None,
        '(the count before, the renders compared, the count after) %r; %s' % (read, said.strip()[-200:]),
    )


# A watch of the 3D view's frames dropped without close(), the cyclic collector off: (whether the watch is gone,
# whether its spy on the viewport is gone)
FRAMES_DROPPED = dedent("""
    import gc
    import weakref
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    dock = _3d_dock(mw)  # held: without, the viewport's wrapper went stale
    gc.disable()
    try:
        frames = _Frames(_viewport(dock), lambda: None)
        gone, spy = weakref.ref(frames), weakref.ref(frames._spy)
        del frames
        print('DROPPED=%r' % ((gone() is None, spy() is None),))
    finally:
        gc.enable()
        gc.collect()  # what a cycle held, freed for the checks after""")


async def check_a_watch_of_the_3d_views_frames_dropped_without_close_goes_at_once(ctx: Ctx) -> None:
    """A watch of the 3D view's frames (_Frames) dropped without close(), as an abort can leave it, goes at once, with
    its spy on the viewport, though the cyclic collector is off: nothing it holds holds it (designer_helpers/frames3d.py;
    REVIEW.md HLP-165: its spy's callback held it, and the viewport ran the spy's Python filter at each paint until a
    collection). In a Designer the self-test started."""
    what = "a watch of the 3D view's frames dropped without close() goes at once, with its spy on the viewport"
    if ctx.was_running:
        skip('screenshot_designer', what, USERS_3D_VIEW)
        return
    said = text(await ctx.c('execute_designer_code', {'code': ctx.helper_source + FRAMES_DROPPED}))
    read = _read(said, 'DROPPED')
    check(
        'screenshot_designer',
        what,
        read == (True, True),
        '(the watch gone, its spy gone) %r; %s' % (read, said.strip()[-200:]),
    )


# a shot's window (_on_screen), each try: a pan, Designer hidden as soon as the count reads 3 or less, or back at 8
# when that was missed, then the window shown again as before a render (_Screen.again); the pans go right then left,
# so the camera ends where it began
SHOWN_FROM_LOWER = dedent("""
    from PySide6 import QtCore
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    dock = _3d_dock(mw)  # held: without, the viewport's wrapper went stale
    viewport = _viewport(dock)
    mac = _MacWindow(mw)
    frames = _Frames(viewport, lambda: _3d_render(mw))
    read = []  # each try: (the count as Designer was hidden, the count as the show's wait ended)
    try:
        with _on_screen(mw, frames) as screen:
            for i in range(6):
                since = frames.mark()[0]
                _drag(viewport, QtCore.Qt.MouseButton.MiddleButton, 20 if i % 2 == 0 else -20, 0, [], frames.taking)
                def low():  # or back at rest: a try that missed the low count ends at once (REVIEW.md TST-463)
                    counts = frames._counts
                    shown = [n for n in counts.seen[since:] if n is not None] if counts else []
                    restarted = counts is not None and counts.restart(since) is not None
                    return restarted and (shown[-1] <= 3 or shown[-1] >= counts.target)
                _until(low, SETTLE_LIMIT, [frames._spy.fired])
                hidden_at = frames.count()
                mac.hide()
                _until(frames.off_screen, SETTLE_LIMIT, [frames._exposed.fired])
                screen.again()
                read.append((hidden_at, frames.count()))
    finally:
        frames.close()
    print('READ=%r' % read)""")


async def check_a_3d_shots_window_shown_again_mid_accumulation_waits_for_the_count_at_rest(ctx: Ctx) -> None:
    """A 3D shot's window gone off screen while its view accumulated, the count left lower, then shown again before a
    render: the show's wait ends once the count is back at rest, 8, not at two paints reading the lower count
    (designer_helpers/frames3d.py; REVIEW.md HLP-167: 1 show in 5 ended there, at 1). 6 tries, Designer hidden once
    the count read 3 or less, the count read just before the hide; judged on the tries hidden so, at least 3. A try
    whose count was back at 8 first (one of 6, 2026-11-16) is hidden then, and not judged (REVIEW.md TST-463). macOS
    only, in a Designer the self-test started."""
    what = 'a 3D shot shown again after its window went off screen mid-accumulation waits for the count at rest'
    if ctx.was_running or sys.platform != 'darwin':
        skip('screenshot_designer', what, USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    await ctx.c('screenshot_designer', {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})  # the view drawn, at rest
    said = text(await ctx.c('execute_designer_code', {'code': ctx.helper_source + SHOWN_FROM_LOWER}))
    read = _read(said, 'READ')
    lower = [shown for hid, shown in read if isinstance(hid, int) and hid <= 3] if isinstance(read, list) else []
    check(
        'screenshot_designer',
        what,
        len(lower) >= 3 and all(shown == 8 for shown in lower),
        '(the count as Designer was hidden, the count as the wait ended), each try: %r' % (read,)
        if read is not None
        else said.strip()[-200:],
    )


async def check_set_3d_view_moves_the_camera_as_a_3d_shots_set_up_does(ctx: Ctx) -> None:
    """set_3d_view run on its own with a move puts Designer's window on screen for it, and the view comes
    out as the 3D shot's own set-up leaves it: a pan of two drags, from Top (designer_helpers/view3d.py; REVIEW.md
    HLP-168: off screen the same pan came out 68.5 grey levels away in 1 run of 2; on screen it repeated exactly). The
    viewpoint is set in a call of its own, which shows the window for its turn, so the pan's call says whether the
    window was put on screen for the pan. 2 tries. macOS only, in a Designer the self-test started."""
    c = ctx.c
    what = "set_3d_view's pan, run on its own, comes out as a 3D shot's, the window put on screen for it"
    if ctx.was_running or sys.platform != 'darwin':
        skip('screenshot_designer', what, USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    await with_checker(c, {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})
    pan = [0.2, 0.1]
    tries: list[tuple[float, bool]] = []
    for _ in range(2):
        shot = await c('screenshot_designer', {**THREE_D, 'view': 'Top', 'pan': pan})
        await c('execute_designer_code', {'code': ctx.helper_source + "set_3d_view(view='Top')"})
        said = text(await c('execute_designer_code', {'code': ctx.helper_source + 'set_3d_view(pan=%r)' % pan}))
        alone = await c('screenshot_designer', THREE_D)
        if not (is_image(shot) and is_image(alone)):
            check('screenshot_designer', what, False, 'a shot failed (below)')
            say_failed("set_3d_view's pan", shot, alone)
            return
        tries.append((round(difference(grey(shot), grey(alone)), 2), "Designer's window: " in said))
    check(
        'screenshot_designer',
        what,
        all(apart <= 0.5 and shown for apart, shown in tries),
        '(grey levels apart, the window put on screen for the pan) each try: %r' % tries,
    )


SHOWN_MESH = dedent("""
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    print('SHOWN=%s' % _mesh_shown(mw, [mw]))
""")


async def check_the_3d_views_scene_menu_checks_the_mesh_shown(ctx: Ctx) -> None:
    """The 3D view's Scene menu checks the mesh the view shows: after Sphere, then Plane, each is the one checked
    (designer facts: shot3d.py's _mesh_shown reads it, to tell a mesh switched from the one shown; REVIEW.md TST-391).
    In a Designer the self-test started."""
    c = ctx.c
    if ctx.was_running:
        skip('designer facts', "the 3D view's Scene menu checks the mesh shown", USERS_3D_VIEW)
        return
    seen: list[str] = []
    for mesh in ('Sphere', 'Plane'):
        await c('screenshot_designer', {**THREE_D, 'mesh': mesh})
        t = text(await c('execute_designer_code', {'code': ctx.helper_source + SHOWN_MESH}))
        m = re.search(r'SHOWN=(.*)', t)
        seen.append(m.group(1).strip() if m else (t.strip().splitlines() or ['nothing printed'])[-1])
    check(
        'designer facts',
        "the 3D view's Scene menu checks the mesh it shows",
        seen == ['Sphere', 'Plane'],
        'checked after Sphere, then Plane: %s' % ', '.join(seen),
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


# Designer's main thread held until the check has pasted (__FLAG__ made), __LIMIT__ s at most: Designer's events don't
# run meanwhile, so a paste only Designer's process can answer waits for the job's end
HELD_UNTIL_PASTED = dedent("""
    import os, time
    POLL_S = 0.1
    deadline = time.monotonic() + __LIMIT__
    while not os.path.exists(__FLAG__) and time.monotonic() < deadline:
        time.sleep(POLL_S)
    print('PASTED_MEANWHILE=%s' % os.path.exists(__FLAG__))
""")
PASTE_LIMIT = 15  # s, a safety net: a paste the pasteboard answers took 0.02 s (REVIEW.md HLP-181)


async def check_the_text_a_3d_capture_puts_back_can_be_pasted_while_designer_is_busy(ctx: Ctx) -> None:
    """The text a 3D capture puts back is the pasteboard's at once, not left for Designer's process to hand over when
    asked: pasted while a job holds Designer's main thread, it comes before the job's end (REVIEW.md HLP-181: the
    paste waited for the job, and the text was gone once that Designer was killed). On macOS, where the clipboard's
    text can be read; the user's own text is the marker when they have some, as in check_the_3d_capture_puts_the_text_back
    (REVIEW.md TST-256)."""
    c = ctx.c
    name = 'the text a 3D capture puts back can be pasted while Designer is busy'
    if sys.platform != 'darwin' or ctx.was_running:
        skip('screenshot_designer', name, 'macOS only, in a Designer the self-test started (the job holds Designer)')
        return
    users = clipboard_text()
    marker = users or TEXT
    flag = os.path.join(ctx.scratch, 'pasted')
    try:
        if users == b'':
            set_clipboard_text(TEXT)
        r_ = await c('screenshot_designer', {'panel': '3d', 'max_size': 200})
        code = HELD_UNTIL_PASTED.replace('__FLAG__', repr(flag)).replace('__LIMIT__', str(PASTE_LIMIT))
        job = asyncio.create_task(c('execute_designer_code', {'code': code}))
        await until_job_running(PASTE_LIMIT)
        pasted = await asyncio.to_thread(clipboard_text)  # the pasteboard's text, or asked of Designer, held
        with open(flag, 'w'):
            pass
        t = text(await job)
        check(
            'screenshot_designer',
            name,
            is_image(r_) and pasted == marker and 'PASTED_MEANWHILE=True' in t,
            '%s | the text %s' % (t.strip()[-80:] or text(r_)[:200], 'came back' if pasted == marker else 'differs'),
        )
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.remove(flag)
        set_clipboard_text(users)


async def check_every_panels_screenshot(ctx: Ctx) -> None:
    for panel in ('window', 'graph', '2d', 'parameters', 'explorer', 'library', 'console'):
        r_ = await ctx.c('screenshot_designer', {'panel': panel, 'max_size': 700})
        if (
            not is_image(r_) and 'not visible' in text(r_) and ctx.was_running
        ):  # a Designer the self-test started shows them
            skip('screenshot_designer', panel, "panel not visible in the user's Designer")
        else:
            check('screenshot_designer', panel, is_image(r_), '' if is_image(r_) else text(r_))


async def check_designer_stayed_behind(ctx: Ctx, samples: Sequence[window_server.Sample]) -> None:
    """Over every check up to the window checks off screen (`samples`, the front watch run() kept, sampled every
    FRONT_EVERY s or so: window_server.py; REVIEW.md TST-471, TST-473), no normal window of Designer's (layer 0) at an
    opacity above 0 was seen in front of another app's window it overlaps, and Designer was never seen the active app;
    its windows above the normal ones, the Explorer's menus, are said, not judged
    (window_server.stayed_behind): the window checks set up their ways behind every window (window_states), and the
    shot keeps its window transparent while it is in front (the user's report: REVIEW.md SRV-149). The checks that need
    a window in front of the user's run after them, unwatched (run). macOS only, in a Designer the self-test
    started."""
    name = (
        "every check up to the window checks off screen leaves Designer's windows behind the other apps', and Designer"
        ' not the active app'
    )
    if ctx.was_running or sys.platform != 'darwin':
        skip('self-test', name, USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    pid = int(text(await ctx.c('execute_designer_code', {'code': 'import os; print(os.getpid())'})).strip())
    behind, said = window_server.stayed_behind(samples, pid)
    check('self-test', name, behind, said)


async def check_the_self_tests_hide_hides_designer(ctx: Ctx) -> None:
    """HIDE, the hide every Designer the self-test starts gets once it answers, runs, and Designer is hidden after it
    (REVIEW.md TST-432: it took the top-level window's handle through `mw.window()` in one expression, which a line
    later read "Internal C++ object (PySide6.QtGui.QWindow) already deleted", and every Designer the self-test started
    stayed on the user's screen). run() hides Designer just before it, so the hide itself isn't measured: that needs
    Designer shown first (REVIEW.md TST-434). macOS only, in a Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'execute_designer_code',
            "the self-test's HIDE runs, and Designer is hidden after it",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    hidden = text(await c('execute_designer_code', {'code': ctx.helper_source + common.HIDE}))
    check(
        'execute_designer_code',
        "the self-test's HIDE runs, and Designer is hidden after it",
        'HIDDEN=True' in hidden,
        hidden.strip()[-150:],
    )


async def check_the_minimized_way_shows_none_of_designers_windows_as_its_window_flies_to_the_dock(ctx: Ctx) -> None:
    """The window checks' 'minimized' way keeps Designer's windows transparent until its window is off screen: none on
    screen at an opacity above 0 while macOS's minimize animation runs, the window server's list sampled from the
    self-test's process all along, at every layer (popups.PopupWatch; REVIEW.md TST-472: made opaque at once, the
    window flew to the Dock at opacity 1 for about 0.55 s, 6 of 6). macOS only, in a Designer the self-test
    started."""
    c = ctx.c
    what = "the 'minimized' way shows none of Designer's windows as its window flies to the Dock"
    if ctx.was_running or sys.platform != 'darwin':
        skip('self-test', what, USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    await c('screenshot_designer', {**THREE_D, **TOP, 'graph': VIEW3D_GRAPH})  # the 3D view there, as the way needs
    pid = int(text(await c('execute_designer_code', {'code': "print(__import__('os').getpid())"})).strip())
    try:
        with popups.PopupWatch(pid, 0) as watch:
            put = text(await c('execute_designer_code', {'code': ctx.helper_source + window_states.put('minimized')}))
    finally:
        await at_rest(c, ctx.helper_source)
    state = window_states.states(put).get('STATE', {})
    check(
        'self-test',
        what,
        state.get('minimized') == 'True' and watch.listed > 0 and watch.times == [],
        "%d samples, %d listing a window of Designer's, %d with one on screen at an opacity above 0; minimized %s"
        % (watch.samples, watch.listed, len(watch.times), state.get('minimized')),
    )


async def run(ctx: Ctx) -> None:
    """Every panel's screenshot, the clipboard, fitting the whole graph, then the 3D view set up, then the window
    checks: all those up to the window checks off screen watched for a window of Designer's in front of the user's
    (check_designer_stayed_behind; REVIEW.md TST-471), then those that need a window there, together."""
    c, helper_source, was_running = ctx.c, ctx.helper_source, ctx.was_running
    if not was_running:
        # our own instance, so its layout doesn't matter: show the console (hidden by default)
        await designer_script(c, 'editor_panels_and_fit/show_console')
        if sys.platform == 'darwin':  # at rest: hidden, nothing of Designer's on the user's screen (window_states)
            await at_rest(c, helper_source)
    # watched from the first check on, the window checks off screen included: nothing of Designer's comes in front of
    # the user's windows; the 3D checks before the window checks put the window on screen too (REVIEW.md TST-471)
    watched = sys.platform == 'darwin' and not was_running
    with window_server.FrontWatch(watching=watched) as front:
        await check_the_self_tests_hide_hides_designer(ctx)
        await check_set_3d_view_sets_up_a_view_that_never_drew(ctx)  # before any 3D shot
        await check_the_first_3d_shot_in_a_designer_opened_hidden_waits_on_the_views_count(
            ctx
        )  # before any other 3D shot
        await check_every_panels_screenshot(ctx)
        await check_the_3d_capture_puts_the_text_back(ctx)
        await check_an_empty_clipboard_has_mimedata(ctx)
        await check_the_text_a_3d_capture_puts_back_can_be_pasted_while_designer_is_busy(ctx)
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
            'execute_designer_code',
            {'code': helper_source + VIEW_SELECT % ('view.scene().clearSelection()', TEST_GRAPH)},
        )
        # last: they open a graph of their own in the editor, where the checks above need the self-test graph
        await check_outputs_added_to_the_open_graph_reach_the_3d_view_once_applied(ctx)
        await check_a_view_turns_the_camera(ctx)
        await check_the_3d_view_zooms_and_tiles(ctx)
        await check_orbit_turns_the_camera_around_what_it_looks_at(ctx)
        await check_pan_moves_the_view_and_zoom_comes_closer_to_the_middle(ctx)
        await check_the_camera_moves_under_the_light_tool_too(ctx)
        await check_a_drag_turns_the_camera_alike_with_selection_on(ctx)
        await check_the_users_mouse_doesnt_stop_a_turn_or_pan(ctx)
        await check_graph_finds_its_row_in_a_collapsed_package(ctx)
        await check_a_set_up_checks_what_it_needs_first_and_says_what_it_set(ctx)
        await check_opening_the_editors_graph_again_leaves_the_outputs_on_the_mesh(ctx)
        await check_a_material_the_mesh_doesnt_use_doesnt_stop_tiling(ctx)
        await check_an_abort_putting_a_shots_window_back_still_hides_designer_again(ctx)
        await check_the_3d_views_frames_say_when_it_has_drawn(ctx)
        await check_a_hidden_designers_window_is_brought_in_front_for_a_3d_shot_once_its_unhide_took(ctx)
        await check_a_watch_of_the_3d_views_frames_dropped_without_close_goes_at_once(ctx)
        await check_a_3d_shots_window_shown_again_mid_accumulation_waits_for_the_count_at_rest(ctx)
        await check_set_3d_view_moves_the_camera_as_a_3d_shots_set_up_does(ctx)
        await check_the_minimized_way_shows_none_of_designers_windows_as_its_window_flies_to_the_dock(ctx)
        await check_a_timer_goes_with_the_parent_its_function_held(ctx)
        await check_the_3d_view_isnt_drawn_while_designers_window_is_off_screen(ctx)
        await check_a_3d_shot_with_graph_keeps_the_explorers_menu_off_the_screen(ctx)
        await check_a_3d_shot_with_graph_makes_the_explorers_menu_click_through(ctx)
        await check_an_explorers_menu_closed_before_its_pick_is_said_so_and_gets_its_look_back(ctx)
        await check_an_explorers_menu_closed_before_its_pick_is_opened_again(ctx)
        await check_wheel_steps_sent_as_designers_window_goes_off_screen_are_all_taken(ctx)
        await check_a_3d_shot_puts_designers_window_on_screen_without_taking_focus(ctx)
        await check_a_3d_shot_keeps_designers_window_transparent_and_click_through_while_off_screen(ctx)
        await check_a_render_that_didnt_follow_a_pan_is_said(ctx)
        await check_a_covered_window_goes_back_behind_its_cover_or_stays_in_front_once_the_cover_is_gone(ctx)
        await check_a_refused_3d_set_up_leaves_designers_window_as_it_was(ctx)
        await check_a_plain_3d_shot_shows_a_change_made_while_designers_window_was_off_screen(ctx)
        await check_a_viewpoint_set_off_screen_is_turned_with_designers_window_on_screen(ctx)
        await check_the_3d_views_scene_menu_checks_the_mesh_shown(ctx)  # watched too (REVIEW.md TST-473)
    await check_designer_stayed_behind(ctx, front.samples)
    # then, together, those that need a window in front of the user's: what they measure can't be set up off screen
    await check_the_3d_view_isnt_drawn_while_designers_window_is_off_screen(ctx, in_front=True)
    await check_a_click_goes_through_designers_window_once_transparent_and_click_through(ctx)
    await check_a_window_under_designers_transparent_window_counts_as_visible(ctx)
    await check_a_3d_shot_puts_designers_window_on_screen_without_taking_focus(ctx, in_front=True)
    await check_a_3d_shot_keeps_designers_window_transparent_and_click_through_while_off_screen(ctx, in_front=True)
    await check_a_3d_shot_makes_designers_window_opaque_at_once_once_designer_is_the_active_app(ctx)
    await check_a_window_covered_during_a_3d_shot_is_put_in_front_again(ctx)
    await check_a_covered_window_goes_back_behind_its_cover_or_stays_in_front_once_the_cover_is_gone(ctx, in_front=True)
    await check_a_plain_3d_shot_shows_a_change_made_while_designers_window_was_off_screen(ctx, in_front=True)
