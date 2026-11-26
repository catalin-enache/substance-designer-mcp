"""The editor: every panel's screenshot, the clipboard, open_graph fitting the whole graph, then the 3D view set up."""

import asyncio
import contextlib
import os
import re
import sys
from collections.abc import Callable
from textwrap import dedent

from mcp.types import CallToolResult

from test_all_tools import common, window_server
from test_all_tools.common import (
    ABORT_AT,
    TEST_GRAPH,
    Ctx,
    ToolArgs,
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
from test_all_tools.editor_panels_and_fit import popups, rasterizer, window_states
from test_all_tools.editor_panels_and_fit.preparations import (
    CHECKER_OPS,
    VIEW3D_ADDED,
    VIEW3D_EMPTY,
    VIEW3D_GRAPH,
    VIEW3D_PLAIN,
)
from test_all_tools.editor_panels_and_fit.printed import (
    Printed,
    is_asks_hidden,
    is_counts,
    is_events,
    is_pairs,
    read_value,
)
from test_all_tools.editor_panels_and_fit.renders import (
    USERS_PLANE_TOP,
    difference,
    grey,
    grey_file,
    moved_left,
    plane_columns,
    plane_height,
    plane_middle,
    plane_width,
    say_failed,
    say_renders,
    transitions,
    users_checker,
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
THREE_D: dict[str, str | int] = {'panel': '3d', 'max_size': 700}
# a plane seen from the top, framed, the checker's graph on it: each call starts from the view the user left, so each
# passes all it sets (designer_helpers/scene3d.py)
PLANE_TOP: ToolArgs = {'mesh': 'Plane', 'view': 'Top'}
TOP: ToolArgs = {**PLANE_TOP, 'graph': VIEW3D_GRAPH}
USERS_3D_VIEW = "it would change the 3D view of the user's Designer"
# getMainWindow() minimized by Qt: the 3D shot un-minimizes it and leaves Designer's window in front, opaque
QT_MINIMIZED = 'qt minimized'


# how much closer a plane seen from the top shows a zoom step, closer and away: the tool's documented x1.11 and x1.1,
# the camera at 0.9 of its distance or 1.1 of it, not state3d's constants, which they check (REVIEW.md TST-919)
STEP, STEP_AWAY = 1 / 0.9, 1 / 1.1
# the plane from the top, 4 steps away, then panned a quarter of the framed view right: the plane moves a quarter of
# that view left, which the zoom makes this fraction of the view (designer_helpers/state3d.py, _camera_moved's order)
SMALL: ToolArgs = {**TOP, 'zoom': -4}
PANNED = 0.25 * STEP_AWAY**4
# how far off a pan the plane shows may be: 2.9 % of PANNED, 1.7 px of the 342 px render; a pan rate 5 %
# off fails (REVIEW.md TST-919; measured 0.0012 off at most, 2026-11-26)
PAN_OFF = 0.005


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
    before = await c('screenshot_designer', {**THREE_D, **PLANE_TOP, 'tiling': 1.0})
    await prepared_call(c, 'apply_edits', {'graph': VIEW3D_ADDED, 'ops': CHECKER_OPS})
    after = await c('screenshot_designer', {**THREE_D, **PLANE_TOP, 'tiling': 1.0})
    applied = await with_checker(c, {**THREE_D, **PLANE_TOP, 'graph': VIEW3D_ADDED})
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
    a square."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'view= turns the camera', USERS_3D_VIEW)
        return
    # its own graph's checker: the check before it may not have run (REVIEW.md TST-386)
    slanted = await with_checker(c, {**THREE_D, **TOP, 'view': 'Default'})
    above = await with_checker(c, {**THREE_D, **TOP})
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
    """tiling repeats the material on the mesh; zoom comes closer (or goes away) by steps of x1.11 (x1.1: STEP and
    STEP_AWAY), from the framed view after view=, each within 5 %, which tells the steps' count."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'zoom and tiling', USERS_3D_VIEW)
        return
    base = await with_checker(c, {**THREE_D, **TOP, 'tiling': 1.0})
    tiled = await with_checker(c, {**THREE_D, **TOP, 'tiling': 2.0})
    closer = await with_checker(c, {**THREE_D, **TOP, 'zoom': 3})
    away = await with_checker(c, {**THREE_D, **TOP, 'zoom': -3})
    shots = [base, tiled, closer, away]
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
        'zoom=3 comes closer, 1.11x a step',
        not clipped and STEP**3 * 0.95 <= ratio <= STEP**3 * 1.05,  # two steps (1.23x) or four (1.52x) fail
        'the plane %d px wide, then %d: %.2fx (%.3f^3 = %.2f)%s'
        % (far, near, ratio, STEP, STEP**3, " | clipped at the panel's edge: a narrower 3D panel" if clipped else ''),
    )
    smaller = plane_width(grey(away)) / max(far, 1)
    check(
        'screenshot_designer',
        'zoom=-3 goes away, 1.1x a step',
        STEP_AWAY**3 * 0.95 <= smaller <= STEP_AWAY**3 * 1.05,  # two steps (0.83x) or four (0.68x) fail
        'the plane %.2fx as wide (%.3f^3 = %.2f)' % (smaller, STEP_AWAY, STEP_AWAY**3),
    )


async def check_orbit_turns_the_camera_around_what_it_looks_at(ctx: Ctx) -> None:
    """orbit= turns the camera around the point it looks at (designer_helpers/state3d.py): from Front, [90, 0] is
    Designer's own Right view and [0, 90] its Top, on a rounded cube, which Frame frames alike from every side. Each
    render is within 3 grey levels on average of that view and nearer it than half the view beside it (Left, and Front,
    which differs from the Top by 5 alone); the degrees said are the ones given. Two turns in one call, [90, 90] from
    Front, are [0, 90] from Right (REVIEW.md TST-336)."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'orbit= turns the camera', USERS_3D_VIEW)
        return
    cube = {**THREE_D, 'graph': VIEW3D_GRAPH, 'mesh': 'Rounded cube'}
    views = {view: await with_checker(c, {**cube, 'view': view}) for view in ('Front', 'Right', 'Left', 'Top')}
    right = await with_checker(c, {**cube, 'view': 'Front', 'orbit': [90, 0]})
    up = await with_checker(c, {**cube, 'view': 'Front', 'orbit': [0, 90]})
    both = await with_checker(c, {**cube, 'view': 'Front', 'orbit': [90, 90]})
    one = await with_checker(c, {**cube, 'view': 'Right', 'orbit': [0, 90]})
    shots = [*views.values(), right, up, both, one]
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
            near < 3.0 and near < 0.5 * far and said is not None and float(said.group(1)) == 90,
            '%.2f from %s, %.2f from %s | %s' % (near, view, far, beside, text(r).strip()),
        )
    near, far = difference(grey(both), grey(one)), difference(grey(both), grey(up))
    check(
        'screenshot_designer',
        'orbit=[90, 90] from Front, two turns in one call, is [0, 90] from Right',
        near < 3.0 and near < 0.5 * far,
        '%.2f from [0, 90] from Right, %.2f from [0, 90] from Front | %s' % (near, far, text(both).strip()),
    )


async def check_pan_moves_the_view_and_zoom_comes_closer_to_the_middle(ctx: Ctx) -> None:
    """pan= moves the view sideways by fractions of it, measured at the point the camera looks at, then zoom= moves the
    camera away or closer (designer_helpers/state3d.py): the plane seen from the top, that point its middle, moves a
    quarter of the framed view left and down for pan=[0.25, 0.25], which zoom=-4 then makes a quarter / 1.1^4 of the
    view, within PAN_OFF (a rate 5 % off fails: REVIEW.md TST-335, TST-919), as said. A corner of the plane that pan
    brings to the middle stays there as zoom comes closer, 4 steps from where it was (ROADMAP item 74: zoom alone
    comes closer only to the middle)."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'pan= moves the view', USERS_3D_VIEW)
        return
    small = await with_checker(c, {**THREE_D, **TOP, 'zoom': -4})
    panned = await with_checker(c, {**THREE_D, **TOP, 'pan': [0.25, 0.25], 'zoom': -4})
    # far enough for the plane, zoomed 4 steps closer from its corner, to stay inside the panel
    far = await with_checker(c, {**THREE_D, **TOP, 'zoom': -10})
    if not all(is_image(r) for r in (small, panned, far)):
        check('screenshot_designer', 'pan= moves the view', False, 'a shot failed (below)')
        say_failed('pan', small, panned, far)
        return
    h, w = grey(small).shape
    (x0, y0), (x1, y1) = plane_middle(grey(small)), plane_middle(grey(panned))
    moved = ((x0 - x1) / w, (y1 - y0) / h)  # the plane left and down: the view right and up
    want = PANNED  # a quarter of the framed view, then 4 steps away
    said = re.search(r'pan ([\d.]+) of the view right, ([\d.]+) up', text(panned))
    check(
        'screenshot_designer',
        'pan=[0.25, 0.25] moves the view a quarter of it right and up',
        all(abs(m - want) <= PAN_OFF for m in moved)
        and said is not None
        and all(float(v) == 0.25 for v in said.groups()),
        'the plane moved %.4f of the view left, %.4f down (%.4f wanted) | %s'
        % (moved[0], moved[1], want, text(panned).strip()),
    )
    f = grey(far)
    columns, rows = plane_columns(f), plane_columns(f.T)
    # its top right, from the middle, in fractions of the framed view: the view at zoom=-10 is 1.1^10 as wide
    corner = [
        round((columns[1] + 1 - w / 2) / w / STEP_AWAY**10, 3),
        round((h / 2 - rows[0]) / h / STEP_AWAY**10, 3),
    ]
    closer = await with_checker(c, {**THREE_D, **TOP, 'pan': corner, 'zoom': -6})  # 4 steps closer than far
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
        and STEP_AWAY**-4 * 0.95 <= grown <= STEP_AWAY**-4 * 1.05,  # three steps or five fail
        'the corner at column %d, row %d of %dx%d; the plane %.2fx as high (1.1^4 = %.2f)%s; panned %s'
        % (
            zc[1] + 1,
            zr[0],
            w,
            h,
            grown,
            STEP_AWAY**-4,
            " | clipped at the panel's bottom: a lower 3D panel" if zr[1] >= h - 1 else '',
            corner,
        ),
    )


# each move with no view=, from the user's view, and the same move from view='Top', which frames the Plane as the user's
# view is (USERS_PLANE_TOP); the last, a mesh switched, framed as Frame does, keeping the camera's direction
FROM_THE_USERS: tuple[tuple[str, ToolArgs], ...] = (
    ('pan=[0.25, 0]', {'pan': [0.25, 0.0]}),
    ('zoom=3', {'zoom': 3}),
    ('orbit=[0, -45]', {'orbit': [0.0, -45.0]}),
    ("mesh='Sphere' and zoom=2", {'mesh': 'Sphere', 'zoom': 2}),
)


async def check_orbit_pan_and_zoom_start_from_the_users_own_view(ctx: Ctx) -> None:
    """With no view=, orbit, pan and zoom move the camera from the user's own view (designer_helpers/scene3d.py; REVIEW.md
    TST-920): the user's view VIEW3D_GRAPH's checker on a Plane from the Top, framed, through the menus (users_checker),
    each move gives the render the same move gives from view='Top', within 3 grey levels on average and less than half
    as far as from the user's view unmoved. A mesh switched with a zoom gives that of view='Top' on the new mesh: the
    switch frames it, its direction kept. How far each move goes is the checks' from view='Top' above: the plane framed
    fills most of the render, and a pan takes part of it out. After the shots, the view shows the editor's graph's
    outputs again: no reply says otherwise, and a Save writes their textures (REVIEW.md TST-941)."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', "orbit, pan and zoom from the user's own view", USERS_3D_VIEW)
        return
    await prepared_call(c, 'open_graph', {'graph': VIEW3D_GRAPH})  # the editor's graph, relinked after each load
    base = await users_checker(c, ctx.helper_source, THREE_D)
    replies: list[str] = []
    for what, move in FROM_THE_USERS:
        moved = await with_checker(c, {**THREE_D, **move})
        replies.append(said := text(moved))
        framed = await with_checker(c, {**THREE_D, 'mesh': 'Plane', 'view': 'Top', **move})
        name = "%s with no view= moves the camera from the user's own view" % what
        if not all(is_image(r) for r in (base, moved, framed)):
            check('screenshot_designer', name, False, 'a shot failed (below)')
            say_failed(what, base, moved, framed)
            continue
        near, far = difference(grey(moved), grey(framed)), difference(grey(moved), grey(base))
        check(
            'screenshot_designer',
            name,
            near < 3.0 and near < 0.5 * far,
            "%.2f from the move from view='Top', %.2f from the user's view | %s" % (near, far, said.strip()[-120:]),
        )
    # REVIEW.md TST-941: the moves' shots, with no graph=, put the editor's graph's outputs back on the mesh after each
    # load: a Save then writes their textures
    t = text(await c('execute_designer_code', {'code': ctx.helper_source + SAVED_TEXTURES}))
    textures = read_value(t, 'TEXTURES')
    check(
        'screenshot_designer',
        "a set-up shot puts the editor's graph's outputs back on the mesh after its loads",
        isinstance(textures, list)
        and 'default_baseColor.png' in textures
        and not any('no longer follows' in r for r in replies),
        'textures a Save writes after the shots: %r | %s' % (textures, ' / '.join(replies)[-150:]),
    )


# the 3D view's state saved, the default state file and its folder backed up where a shot finds a leftover first and
# put back after: the textures Save wrote beside the file
SAVED_TEXTURES = dedent("""
    import os
    mw = _main_window()
    bar = _3d_dock(mw).findChildren(QtWidgets.QMenuBar)[0]
    keep = [mw, bar]
    path, aside = _state_default_path(_version_folder()), os.path.join(_version_folder(), STATE_BACKUP)
    _state_back_up(path, aside)
    try:
        _state_saved(bar, keep, path)  # refused unless the Save wrote the file there (scene3d.py)
        resources = _state_resources(path)
        print('TEXTURES=%r' % (sorted(os.listdir(resources)) if os.path.isdir(resources) else None))
    finally:
        _state_put_back(aside)""")


async def check_an_editors_graph_with_no_outputs_is_said_not_to_be_followed(ctx: Ctx) -> None:
    """The view showing VIEW3D_GRAPH's outputs, then a graph with none opened in the editor, which leaves the view as
    it is: a set-up shot's load unlinks the view, the editor's graph isn't put on the mesh, and the shot says so
    (designer_helpers/scene3d.py, _relinked; REVIEW.md HLP-282: measured, the Explorer's menu took it and put nothing
    there, and nothing was said). The editor is back on VIEW3D_GRAPH after, its outputs on the mesh."""
    c = ctx.c
    name = "a set-up shot says the 3D view follows no graph once the editor's graph has no outputs"
    if ctx.was_running:
        skip('screenshot_designer', name, USERS_3D_VIEW)
        return
    await prepared_call(c, 'open_graph', {'graph': VIEW3D_GRAPH})  # its outputs on the mesh
    await prepared_call(c, 'create_graph', {'name': VIEW3D_EMPTY, 'size_log2': 4})
    try:
        await prepared_call(c, 'open_graph', {'graph': VIEW3D_EMPTY})
        r = await c('screenshot_designer', {**THREE_D, 'orbit': [30, 0]})
    finally:
        await prepared_call(c, 'open_graph', {'graph': VIEW3D_GRAPH})
    said = 'it no longer follows the graph it showed: graph %s in the editor has no outputs to show' % VIEW3D_EMPTY
    check('screenshot_designer', name, is_image(r) and said in text(r), text(r).strip()[-250:])


async def check_a_set_up_shot_on_a_view_following_a_graph_leaves_override_material_off(ctx: Ctx) -> None:
    """The view showing VIEW3D_GRAPH's outputs, Override Material turned off: a set-up shot leaves it off. The relink
    after each load, the Explorer's View Outputs In 3D View, turns it on by itself (designer_helpers/scene3d.py;
    REVIEW.md HLP-291: measured, it ended on). Override Material on again after, as Designer starts it."""
    c = ctx.c
    name = 'a set-up shot on a view following a graph leaves Override Material off, as the user had it'
    if ctx.was_running:
        skip('screenshot_designer', name, USERS_3D_VIEW)
        return

    async def override(on: bool | None) -> Printed:
        return read_value(
            text(await c('execute_designer_code', {'code': ctx.helper_source + OVERRIDE % (on,)})), 'OVERRIDE'
        )

    await prepared_call(c, 'open_graph', {'graph': VIEW3D_GRAPH})  # the editor's graph, relinked after each load
    await c('execute_designer_code', {'code': ctx.helper_source + USERS_PLANE_TOP % VIEW3D_GRAPH})  # on the mesh
    try:
        off = await override(False)
        r = await c('screenshot_designer', {**THREE_D, 'orbit': [30, 0]})
        after = await override(None)
    finally:
        await override(True)
    check(
        'screenshot_designer',
        name,
        is_image(r) and off == [False] and after == [False],
        'turned off %r, after the shot %r | %s' % (off, after, text(r).strip()[-200:]),
    )


# each material's Override Material in the 3D view's Materials menu set to the value given first, unless None, then
# printed in the menu's order
OVERRIDE = dedent("""
    mw = _main_window()
    bar = _3d_dock(mw).findChildren(QtWidgets.QMenuBar)[0]
    keep = [mw, bar]
    on = %r
    for action in _overrides(bar, keep):
        if on is not None and action.isChecked() != on:
            action.trigger()
    _process_events()
    print('OVERRIDE=%%r' %% [action.isChecked() for action in _overrides(bar, keep)])""")


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
    scene = [('Scene', m) for m in MESHES + (SAVE, RESET)]  # the state file's Save and load too
    for path in scene + [('Camera', v) for v in VIEWS + ('Frame',)]:
        try:
            _menu_action(dock.findChildren(QtWidgets.QMenuBar)[0], keep, *path) if dock else None
        except RuntimeError:
            missing.append(' > '.join(path))
    print('MISSING=%r' % missing if dock else 'NO_3D_VIEW')""")


async def check_the_3d_views_menus_have_the_meshes_and_views(ctx: Ctx) -> None:
    """The meshes screenshot_designer offers, and the entries that save and load the 3D view's state file, are in the
    3D view's Scene menu (designer_helpers/view3d.py MESHES, scene3d.py SAVE and RESET); the views and Frame, whose
    framing the view table holds, in its Camera menu (state3d.py; facts' check of Designer's Frame): looked up, nothing
    triggered, so this runs in the user's Designer too (REVIEW.md TST-315)."""
    t = text(await ctx.c('execute_designer_code', {'code': ctx.helper_source + MENUS}))
    if 'NO_3D_VIEW' in t and ctx.was_running:
        skip(
            'designer facts',
            "the 3D view's menus have its meshes and views",
            "no 3D View visible in the user's Designer",
        )
        return
    check('designer facts', "the 3D view's menus have its meshes and views", 'MISSING=[]' in t, t.strip()[-300:])


# the user's own 3D view made a Plane seen from the top, by Designer's menus as the user would make it: Scene > Plane,
# Camera > Top, then Frame, Designer's window on screen for the camera's turn
async def check_a_tiling_on_a_material_with_no_pattern_is_said_to_change_nothing(ctx: Ctx) -> None:
    """The user's own view a Plane from the Top, VIEW3D_PLAIN in the editor and so its outputs on the mesh (one colour,
    built by the preparation): the render at tiling 2 is the render at tiling 1 (designer facts), and the 3D shot's
    line on a render identical after a set-up names that case (designer_helpers/shot3d.py, STALE; REVIEW.md HLP-202:
    it said only that the view may not have been drawn). A shot at tiling 2 comes first, its put-back loading the
    user's view once: after a view set through the menus, the first load changed one pixel by one grey level, so that
    shot's render wasn't identical (measured 2026-11-26; a second load changed none). In a Designer the self-test
    started."""
    c = ctx.c
    fact = 'a tiling changes nothing a material with no pattern shows'
    name = 'a render identical after a tiling is said to be one on a material with no pattern'
    if ctx.was_running:
        skip('designer facts', fact, USERS_3D_VIEW)
        skip('screenshot_designer', name, USERS_3D_VIEW)
        return
    await c('execute_designer_code', {'code': ctx.helper_source + USERS_PLANE_TOP % None})
    await prepared_call(c, 'open_graph', {'graph': VIEW3D_PLAIN})  # built by the preparation: its outputs on the mesh
    await c('screenshot_designer', {**THREE_D, 'tiling': 2.0})  # the user's view loaded once (the docstring)
    before = await c('screenshot_designer', THREE_D)
    after = await c('screenshot_designer', {**THREE_D, 'tiling': 2.0})
    if not (is_image(before) and is_image(after)):
        check('designer facts', fact, False, 'a shot failed (below)')
        check('screenshot_designer', name, False, 'a shot failed (below)')
        say_failed(fact, before, after)
        return
    seen_before = grey(before)
    apart = difference(seen_before, grey(after))
    plain = transitions(seen_before)  # no pattern: VIEW3D_PLAIN's outputs reached the mesh (REVIEW.md TST-556)
    check(
        'designer facts',
        fact,
        apart == 0 and plain <= 2,
        'the renders at tiling 1 and 2: %.2f grey levels apart; %d dark-light changes at tiling 1' % (apart, plain),
    )
    check(
        'screenshot_designer',
        name,
        'a tiling changes nothing on a material with no pattern' in text(after),
        text(after).strip()[-160:],
    )


# a 3D shot of graph %r with the Explorer taken as hidden, then one failing once after the set-up's load, each saved to
# %r
EXPLORER_HIDDEN = dedent("""
    _shown = _visible_dock
    def _visible_dock(mw, prefix):
        return None if prefix == _PANEL_AREAS['explorer'] else _shown(mw, prefix)
    shoot_3d(%r, %r, 'Sphere')""")
FAILING_ONCE = dedent("""
    _failing, _real_overrides_back = [True], _overrides_back
    def _overrides_back(bar, keep, overridden, watched):
        if _failing:
            _failing.pop()
            raise RuntimeError('taken as failing after the load')
        return _real_overrides_back(bar, keep, overridden, watched)
    shoot_3d(%r, None, 'Sphere')""")
# then an abort (the plugin's is a BaseException) as the graph's outputs are applied, after the mesh changed
ABORTED = dedent("""
    class _Abort(BaseException):
        pass
    def _apply_outputs(tree, g, keep):
        raise _Abort('an abort as the outputs are applied')
    shoot_3d(%r, %r, 'Sphere')""")


async def check_a_set_up_checks_what_it_needs_first_and_says_what_it_set(ctx: Ctx) -> None:
    """A panel the set-up needs is checked before anything changes: the Explorer taken as hidden with graph=, the
    user's view stays as it was. An error after a change says what was set, and the user's view is put back: a render
    after it is the one before (REVIEW.md HLP-107). An abort after a change prints what was set, and the job still
    ends as an abort (HLP-113)."""
    c = ctx.c
    if ctx.was_running:
        skip('screenshot_designer', 'a set-up checks what it needs first, and says what it set', USERS_3D_VIEW)
        return
    shot = os.path.join(ctx.scratch, 'set_up_refused.png')
    before = await c('screenshot_designer', THREE_D)  # the user's view
    code = ctx.helper_source + EXPLORER_HIDDEN % (shot, VIEW3D_GRAPH)
    hidden = text(await c('execute_designer_code', {'code': code}))
    after = await c('screenshot_designer', THREE_D)
    changed = difference(grey(before), grey(after)) if is_image(before) and is_image(after) else 255.0
    check(
        'screenshot_designer',
        'a panel the set-up needs is checked before anything changes',
        'Explorer panel' in hidden and SET_UP_STEP not in hidden and changed < 2 and not os.path.exists(shot),
        '%s | the render changed %.1f grey levels' % (hidden.strip().splitlines()[-1:], changed),
    )
    say_failed('a panel the set-up needs is checked before anything changes', before, after)
    failed = text(await c('execute_designer_code', {'code': ctx.helper_source + FAILING_ONCE % shot}))
    back = await c('screenshot_designer', THREE_D)
    apart = difference(grey(before), grey(back)) if is_image(before) and is_image(back) else 255.0
    check(
        'screenshot_designer',
        'an error after a change says what was set, and the view is put back',
        'the 3D view was already set: Sphere' in failed
        and '3D view: put back as it was' in failed
        and apart < 2
        and not os.path.exists(shot),
        '%s | the render after it %.1f grey levels off the one before' % (failed.strip().splitlines()[-1:], apart),
    )
    aborted = text(await c('execute_designer_code', {'code': ctx.helper_source + ABORTED % (shot, VIEW3D_GRAPH)}))
    check(
        'screenshot_designer',
        'an abort after a change says what was set, and goes on as an abort',
        '3D view, setting: Sphere' in aborted
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
                # off screen again: macOS says it hidden (AppKit's notification), Qt that the window isn't exposed
                _until_notified(mac, lambda: mac.hidden() and not handle.isExposed(), 3.0, HIDDEN, [spy.fired])
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
    """tiling= sets the material the mesh uses: one added (Materials > Add), which Designer lists as unused and the state
    file maps no part of the mesh to, isn't counted (REVIEW.md HLP-114, HLP-280): the checker on a plane from the top,
    the material added, repeats twice as often at tiling 2 as at 1. The material stays (that with mesh= the new mesh's
    materials count is a unit test's, every preset mesh having one)."""
    c = ctx.c
    name = "tiling= isn't stopped by a material the mesh doesn't use, and tiles the one it uses"
    if ctx.was_running:
        skip('screenshot_designer', name, USERS_3D_VIEW)
        return
    added = text(await c('execute_designer_code', {'code': ctx.helper_source + ADD_MATERIAL}))
    window_states.stopped_if_shown(added)  # its windows transparent on screen: no shot after it (REVIEW.md TST-478)
    base = await with_checker(c, {**THREE_D, **TOP, 'tiling': 1.0})
    tiled = await with_checker(c, {**THREE_D, **TOP, 'tiling': 2.0})
    if not (is_image(base) and is_image(tiled)):
        check('screenshot_designer', name, False, 'a shot failed (below)')
        say_failed(name, base, tiled)
        return
    once, twice = transitions(grey(base)), transitions(grey(tiled))
    check(
        'screenshot_designer',
        name,
        'mcp_selftest_material (unused)' in added
        and (sys.platform != 'darwin' or 'HIDDEN AGAIN=True' in added)  # REVIEW.md TST-425: was printed, never judged
        and once >= 6
        and 1.6 <= twice / once <= 2.4,
        '%d dark-light changes across the plane at tiling 1, %d at 2 | %s' % (once, twice, added.strip()[-120:]),
    )


# two of Designer's environment maps: one soft light on black, and a white studio in hard sunlight
DARK, BRIGHT = 'studio_black_soft_light', 'studio_white_hard_sunlight'


async def check_the_environment_turns_brightens_and_changes_the_light(ctx: Ctx) -> None:
    """environment= sets one of Designer's maps on the 3D view; environment_rotation= its angle and
    environment_exposure= its Exposure, through the state file (designer_helpers/scene3d.py). On a sphere from the Front, under a map with one soft light (DARK): turned 90 degrees, the render
    changes (the angle set, not added: the state file holds it, as facts' check of its units shows; REVIEW.md SRV-181,
    TST-551); at exposure 2 it is brighter; under another map (BRIGHT) it changes. Each call starts from the user's
    view, so each passes the whole light: the values a view shows already are
    check_values_a_3d_set_up_finds_shown_already_take_no_wait's."""
    c = ctx.c
    name = 'environment, environment_rotation and environment_exposure set the light'
    if ctx.was_running:
        skip('screenshot_designer', name, USERS_3D_VIEW)
        return
    # each shot from the user's view, so each passes all it sets; one shot, not with_checker's: its count of the
    # checker's squares is for a plane from the top
    sphere = {**THREE_D, 'mesh': 'Sphere', 'view': 'Front', 'graph': VIEW3D_GRAPH}

    def lit(name: str, rotation: float, exposure: float) -> ToolArgs:
        return {**sphere, 'environment': name, 'environment_rotation': rotation, 'environment_exposure': exposure}

    first = await c(
        'screenshot_designer',
        {**sphere, 'environment': DARK, 'environment_rotation': 0.0, 'environment_exposure': 0.0},
    )
    turned = await c('screenshot_designer', lit(DARK, 90.0, 0.0))
    brighter = await c('screenshot_designer', lit(DARK, 90.0, 2.0))
    other = await c('screenshot_designer', lit(BRIGHT, 90.0, 2.0))
    shots = [first, turned, brighter, other]
    if not all(is_image(r) for r in shots):
        check('screenshot_designer', name, False, 'a shot failed (below)')
        say_failed(name, *shots)
        return
    greys = {id(r): grey(r) for r in shots}  # each shot decoded once

    def sized(a: CallToolResult, b: CallToolResult) -> bool:
        """Whether two of the shots are of one size; their sizes said when not."""
        if greys[id(a)].shape != greys[id(b)].shape:
            say_failed(name, a, b)
            return False
        return True

    def apart(a: CallToolResult, b: CallToolResult) -> float:
        """difference() of two of the shots: NaN for two sizes, said."""
        sized(a, b)
        return difference(greys[id(a)], greys[id(b)])

    moved = apart(first, turned)
    check(
        'screenshot_designer',
        'environment_rotation turns the light: the render changes',
        moved >= 3,
        'mean difference %.1f grey levels, turned 90 degrees' % moved,
    )
    # two sizes: NaN, as difference() gives (REVIEW.md TST-544: the background's share of the image changes)
    gained = float(greys[id(brighter)].mean() - greys[id(turned)].mean()) if sized(brighter, turned) else float('nan')
    check(
        'screenshot_designer',
        'environment_exposure 2 brightens the render',
        gained >= 3,
        '%+.1f grey levels on average from exposure 0' % gained,
    )
    changed = apart(brighter, other)
    check(
        'screenshot_designer',
        'environment changes the map: the render changes',
        changed >= 5,
        'mean difference %.1f grey levels from %s to %s' % (changed, DARK, BRIGHT),
    )
    said = [line for line in text(first).splitlines() if line.startswith('3D view: ')]
    check(
        'screenshot_designer',
        'the environment set is said, with nothing of the Parameters panel',
        bool(said)
        and 'environment %s, rotation 0 degrees, exposure 0' % DARK in said[0]
        and 'Parameters panel' not in text(first),
        ' / '.join(said)[-200:],
    )


# a 3D shot, saved by shoot_3d, setting the whole light on a sphere from the Front, with nothing after its load: the
# relink after it skipped, the put-back's done (REVIEW.md HLP-192); and the view as it settled after the shot's render,
# saved as the put-back's load begins: its sample count back at rest. The shot renders the view before its set-up too,
# so the put-back's load is the one after the second render
SETTLED = dedent("""
    _real_relinked, _relinks = _relinked, []
    def _relinked(tree, keep):
        _relinks.append(True)
        return ' (not relinked: the check)' if len(_relinks) == 1 else _real_relinked(tree, keep)
    _shot_render, _shot_load, _rendered = _3d_render, _state_load, []
    def _3d_render(mw):
        _rendered.append(True)
        return _shot_render(mw)
    def _state_load(bar, keep, watched, *rest):
        if len(_rendered) > 1:  # the put-back's load, after the shot's own render
            watched.until(watched._resting, SETTLE_LIMIT)
            _shot_render(_main_window()).save(%r)
        return _shot_load(bar, keep, watched, *rest)
    shoot_3d(%r, mesh='Sphere', view='Front', environment=%r, environment_rotation=90.0, environment_exposure=2.0)""")


async def check_a_3d_shot_setting_the_light_renders_the_view_once_it_settled(ctx: Ctx) -> None:
    """A 3D shot setting the map, the rotation and the exposure renders the view once the load that sets them is
    drawn: the shot matches the view as it settled after it, before the view is put back. Nothing follows the load here
    (SETTLED), so its wait is the last before the render (REVIEW.md HLP-192, TST-932). Measured 2026-11-26: 0.00 grey
    levels apart; with the settle wait left out, 0.50. In a Designer the self-test started."""
    c = ctx.c
    name = 'a 3D shot setting the map, the rotation and the exposure renders the view once it settled'
    if ctx.was_running:
        skip('screenshot_designer', name, USERS_3D_VIEW)
        return
    path, after = os.path.join(ctx.scratch, 'whole_light.png'), os.path.join(ctx.scratch, 'settled.png')
    t = text(await c('execute_designer_code', {'code': ctx.helper_source + SETTLED % (after, path, BRIGHT)}))
    if not (os.path.exists(path) and os.path.exists(after)):
        check('screenshot_designer', name, False, 'a shot failed (below)')
        print('      %s: %s' % (name, ' / '.join(t.strip().splitlines()[-3:])))
        return
    apart = difference(grey_file(path), grey_file(after))
    check(
        'screenshot_designer',
        name,
        apart < 0.1 and 'environment %s, rotation 90 degrees, exposure 2' % BRIGHT in t,
        'mean difference %.3f grey levels from the view settled after | %s' % (apart, t.strip()[-120:]),
    )


# a plain 3D shot, then one given the values the view shows (the mesh the Scene menu checks, the rest read from a Save,
# the default state file kept aside meanwhile), its set-up's waits on the 3D view's frames counted (WAITS=), and its
# loads (LOADS=)
SHOWN_ALREADY = dedent("""
    import os
    folder = %r
    mw = _main_window()
    bar = _3d_dock(mw).findChildren(QtWidgets.QMenuBar)[0]
    keep = [mw, bar]
    mesh = [m for m in _scene_checked(bar, keep) if m in MESHES][0]
    path, aside = _state_default_path(_version_folder()), os.path.join(_version_folder(), STATE_BACKUP)
    _state_back_up(path, aside)
    try:
        _state_save(bar, keep)
        f = _state_fields(_state_text(path), ['tiling', 'environment', 'rotation', 'exposure'])
    finally:
        _state_put_back(aside)
    shown = dict(
        mesh=mesh,
        tiling=f['tiling'],
        environment=os.path.splitext(f['environment'].split('://')[-1])[0],
        environment_rotation=f['rotation'] * 360,
        environment_exposure=f['exposure'],
    )
    print('SHOWN=%%r' %% (shown,))
    shoot_3d(os.path.join(folder, 'plain.png'))
    _waits, _loads = [], []
    _settled, _loaded = _Frames.settled, _state_load
    def _counted(self, *args, **kw):
        _waits.append(args)
        return _settled(self, *args, **kw)  # its result read since REVIEW.md HLP-214 (TST-678)
    def _state_load(bar, keep, watched, *rest):
        _loads.append(True)
        return _loaded(bar, keep, watched, *rest)
    _Frames.settled = _counted
    try:
        shoot_3d(os.path.join(folder, 'again.png'), **shown)
    finally:
        _Frames.settled = _settled
    print('WAITS=' + str(len(_waits)))
    print('LOADS=' + str(len(_loads)))""")


async def check_values_a_3d_set_up_finds_shown_already_take_no_wait(ctx: Ctx) -> None:
    """The mesh the 3D view shows, and the tiling, the map, the environment's rotation and exposure its state file
    holds, given to a shot, are said set, with no load and no wait on the 3D view's frames: set again, they restarted
    nothing, so their waits ran to their limit (REVIEW.md HLP-195: 1.0 s for the mesh, 1.5 s for the tiling, measured;
    HLP-192 for the environment; HLP-201: 0.95 s for the map). Having changed nothing, the shot loads nothing back
    after its render (designer_helpers/scene3d.py), and its render is the plain shot's: taken with no wait, it isn't
    one the view was still drawing. In a Designer the self-test started."""
    c = ctx.c
    name = 'values a 3D set-up finds shown already are said set, with no wait'
    if ctx.was_running:
        skip('screenshot_designer', name, USERS_3D_VIEW)
        return
    t = text(await c('execute_designer_code', {'code': ctx.helper_source + SHOWN_ALREADY % ctx.scratch}))
    # the line of what was set: the mesh, the tiling, then the environment, nothing after
    said = re.findall(
        r'^3D view: [^,]+, tiling [\d.e-]+, environment [\w ]+, rotation [\d.e-]+ degrees, exposure [\d.e-]+$', t, re.M
    )
    waits = re.search(r'^WAITS=(\d+)$', t, re.M)
    loads = re.search(r'^LOADS=(\d+)$', t, re.M)
    paths = [os.path.join(ctx.scratch, f) for f in ('plain.png', 'again.png')]
    apart = difference(grey_file(paths[0]), grey_file(paths[1])) if all(map(os.path.exists, paths)) else float('nan')
    check(
        'screenshot_designer',
        name,
        waits is not None
        and waits.group(1) == '0'
        and loads is not None
        and loads.group(1) == '0'
        and len(said) == 1
        and apart == 0
        and '3D view: put back' not in t,
        'waits: %s; loads: %s; %d of 1 line said; the renders %.2f grey levels apart | %s'
        % (waits and waits.group(1), loads and loads.group(1), len(said), apart, ' '.join(t.split())[-250:]),
    )


# a shot's window put on screen and back (_on_screen) with Designer hidden, aborted at the first of __LINES__ it reaches
# (common.ABORT_AT). The windows' looks are given back by the snippet, only once Designer is hidden again, so none shows
# opaque on the user's screen whatever the abort left
SHOT_ABORTED = dedent("""
    mw = _APP.getQtForPythonUIMgr().getMainWindow(); keep = [mw]
    mac = _mac_window(mw)
    frames = _frames_of(mw, _viewport(_3d_dock(mw)))
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
# so is the window's state where a wait on screen ran out (STATES; REVIEW.md TST-444). Each pan is the self-test's own
# (window_states.PAN_OF_ITS_OWN). The snippet runs after WHO (window_owner.py)
FRAMES = window_states.PAN_OF_ITS_OWN + dedent("""
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
    frames = _frames_of(mw, viewport)
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
    rest = count()
    paints = lambda events: [n for kind, n in events if kind == 'Paint']
    pan = lambda dx: _ws_drag(viewport, dx)  # sent, no wait: each part waits for what it reads

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


def _shown(events: Printed, changed: bool) -> bool:
    """FRAMES' events as the window came on screen from hidden: after a change, the first paint reading 8, then an
    UpdateRequest, then a paint reading a restart; with nothing changed, two paints or more, each reading 8, and no
    UpdateRequest."""
    if not (isinstance(events, tuple) and events[0] is True and is_events(events[1])):
        return False
    seen = events[1]
    paints = [n for kind, n in seen if kind == 'Paint']
    if not changed:
        return len(paints) >= 2 and all(n == 8 for n in paints) and all(kind == 'Paint' for kind, _ in seen)
    asked = [i for i, (kind, _) in enumerate(seen) if kind == 'UpdateRequest']
    restart = [i for i, (kind, n) in enumerate(seen) if kind == 'Paint' and n is not None and n < 8]
    return paints[:1] == [8] and bool(asked) and bool(restart) and asked[0] < restart[0]


def _changed_by_its_second_paint(events: Printed) -> bool:
    """FRAMES' events as the window came on screen: by the second paint, an UpdateRequest came or that paint read a
    restart (below 8); with nothing changed, neither (_shown)."""
    if not (isinstance(events, tuple) and is_events(events[1])):
        return False
    seen = events[1]
    paints = [i for i, (kind, _) in enumerate(seen) if kind == 'Paint']
    if len(paints) < 2:
        return False
    second = seen[paints[1]][1]
    return any(kind == 'UpdateRequest' for kind, _ in seen[: paints[1]]) or (second is not None and second < 8)


def _restarted(seen: Printed, rest: Printed) -> bool:
    """FRAMES' counts read after a change: `rest`, the count at rest, then a restart (below 8), then back to it."""
    return (
        is_counts(seen)
        and len(seen) >= 3
        and seen[0] == rest
        and any(n is not None and n < 8 for n in seen[1:])
        and seen[-1] == rest
    )


def _held(seen: Printed, rest: Printed) -> bool:
    """FRAMES' counts read after a viewpoint: restarted (_restarted), the lowest count read at two paints or more, held
    while the camera turns."""
    # _restarted is true only for a list. is_counts tells the checker so.
    return _restarted(seen, rest) and is_counts(seen) and seen.count(min(n for n in seen if n is not None)) >= 2


async def check_the_3d_views_frames_say_when_it_has_drawn(ctx: Ctx) -> None:
    """The 3D view's paints, its UpdateRequests and its overlay's sample count, what screenshot_designer('3d') waits on
    instead of fixed times (designer_helpers/frames3d.py; REVIEW.md HLP-148): 8 at rest; restarted by a pan and a
    viewpoint, the first paint after each still reading the count before, the viewpoint's restart held while the
    camera turns, then back to 8; no count with Display > Samples off; and as Designer's window comes on screen from
    hidden, right after a pan made meanwhile an UpdateRequest then a restart, with nothing changed only paints reading
    8; Designer hidden, an UpdateRequest after each pan and no paint, what a settle off screen waits for (REVIEW.md
    HLP-149, HLP-158). Each pan is the self-test's own (window_states.PAN_OF_ITS_OWN). macOS only (the window hidden and shown through _MacWindow), in a Designer the self-test
    started.

    Each reading starts from the user's view at Top on a Plane (USERS_PLANE_TOP), which Camera > Front then turns: at
    Front already, it redraws nothing, and a second reading failed (REVIEW.md TST-951, measured).

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
            # the camera at Top, which Camera > Front then turns: at Front already, it redraws nothing (REVIEW.md TST-951)
            await c('execute_designer_code', {'code': ctx.helper_source + USERS_PLANE_TOP % None})
            await c('screenshot_designer', THREE_D)  # the view drawn, at rest
            said = text(await c('execute_designer_code', {'code': ctx.helper_source + WHO + FRAMES}))
            covers = read_value(said, 'COVERS')
            if not covers:
                break
            # printed whole, as a check's detail is cut: (the stretch, macOS's covered, the windows in front of it)
            print('      covered while read on screen%s: %r' % ('' if last else ', read again', covers))
    rest, pan, view = (read_value(said, name) for name in ('REST', 'PAN', 'VIEW'))
    check(
        'designer facts',
        what,
        rest == 8 and _restarted(pan, rest) and _held(view, rest),
        'at rest %r; a pan %r; a viewpoint %r' % (rest, pan, view),
    )
    states = read_value(said, 'STATES')
    if states:  # printed whole, as a check's detail is cut: the window's state where a wait ran out (REVIEW.md TST-444)
        shot = [line for line in said.splitlines() if line.startswith("Designer's window: ")]
        print('      where a wait on screen ran out: %r; the show: %s' % (states, ' / '.join(shot)))
    check(
        'designer facts',
        'with Display > Samples off, the overlay shows no count',
        'OFF=None' in said,
        said.strip().splitlines()[-1] if 'OFF=' not in said else 'OFF=%r' % read_value(said, 'OFF'),
    )
    changed, unchanged = read_value(said, 'SHOWN_CHANGED'), read_value(said, 'SHOWN_UNCHANGED')
    check(
        'designer facts',
        'shown from hidden, the 3D view asks for a frame and restarts after a pan made meanwhile, and does neither '
        'with nothing changed',
        _shown(changed, True) and _shown(unchanged, False),
        '(hidden before, events) after a pan %r; with nothing changed %r' % (changed, unchanged),
    )
    taken = read_value(said, 'SHOWN_TAKEN')
    check(
        'designer facts',
        # whether Designer was hidden before the show, and the pan's UpdateRequest came before it, isn't judged
        # (REVIEW.md TST-439)
        'shown after a pan, the 3D view asks for a frame or restarts by its second paint (what _Frames.shown tells a '
        'change from none by: REVIEW.md HLP-151)',
        _changed_by_its_second_paint(taken),
        '(hidden before, events) %r' % (taken,),
    )
    hidden_asks = read_value(said, 'HIDDEN_ASKS')
    each = hidden_asks[1] if is_asks_hidden(hidden_asks) else []
    check(
        'designer facts',
        "Designer hidden, the 3D view asks for a frame after each pan, and draws none up to the last one's ask",
        len(each) == 6
        and all('UpdateRequest' in kinds and 'Paint' not in kinds for kinds in each)
        and 'HIDDEN_PAINTS=0' in said,  # REVIEW.md TST-429: a paint after a pan's ask fell in no slice
        '(hidden, the events after each pan) %r; paints over the stretch: %r'
        % (hidden_asks, read_value(said, 'HIDDEN_PAINTS')),
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
    """While macOS has Designer's window minimized or hidden, the 3D view's render stays the last frame it drew: a pan
    of the self-test's own (window_states.PAN_OF_ITS_OWN) leaves it identical. Covered by a window of Designer's own,
    it is said, not judged: in
    Designers launch_designer opened (`open`), the pan changed it in some, as Qt kept the window exposed, and left it in
    others, 6 of 6 tries each, in two Designers (REVIEW.md SRV-152, TST-433, 2026-11-15). What decides it isn't known.
    With the window covered, then made transparent and click-through and brought in front, the pan changes it. A page
    Qt minimized isn't
    measured: nothing says when its view stops drawing, which some runs saw and others didn't (the user's choice,
    REVIEW.md TST-420). macOS minimizing the window leaves getMainWindow()'s isMinimized() False, the top-level
    window's True, and the window not exposed (designer facts: designer_helpers/shot3d.py, REVIEW.md SRV-146,
    TST-391). With `in_front`, the two ways in front of the user's windows instead: on screen and partly covered, the
    pan changes it too; run() runs them with the other checks that need a window there. A drawn way with a window of
    another app found in front of Designer's is taken again (without_others_in_front), and so is one with Designer's
    window still covered for macOS once put there: a window above every normal one, or a locked screen (REVIEW.md
    TST-520). The ways are read while no Designer of the run starts or quits (no_designer_starting: REVIEW.md
    TST-417). macOS only, in a Designer the self-test started."""
    if ctx.was_running or sys.platform != 'darwin':
        skip('designer facts', "the 3D view isn't drawn off screen", USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    await users_checker(ctx.c, ctx.helper_source, THREE_D)
    seen: dict[str, str] = {}
    states: dict[str, dict[str, str]] = {}
    unclear = []  # drawn ways with a window in the way in every try: another app's in front, or a cover (TST-520)
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
        'a window in the way in each try: %s; ' % ', '.join(unclear) if unclear else '',
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


async def check_appkits_notifications_come_once_designers_window_changed(ctx: Ctx) -> None:
    """AppKit's notifications that wake the 3D shot's waits and the self-test's come once what each wait looks at has
    changed, Designer's windows transparent and click-through, as the shot makes them (designer facts:
    designer_helpers/mac_window.py, UNHIDDEN, OFF_SCREEN, UNMINIMIZED and HIDDEN; ROADMAP item 101):

    - Designer unhidden, once macOS no longer says it hidden;
    - its window's occlusion changed, once macOS no longer says it covered, after the window was shown in front of a
      window of Designer's own covering it whole (as uncovered waits for it: REVIEW.md TST-524);
    - the first of its window minimized or its occlusion changed, once the window server no longer lists the window,
      after a minimize (miniaturize:, as the shot does, and performMiniaturize:, as the self-test's minimized way does)
      and after a hide;
    - the window shown again by deminiaturize:, as the self-test's waits follow it, once macOS no longer says it
      minimized;
    - Designer hidden, once macOS says it hidden.

    Taken again while a window of another app is in front of Designer's, or Designer's window is still covered once
    brought in front (without_others_in_front; REVIEW.md TST-516), and read while no
    worker of the pool starts or quits its Designer (no_designer_starting: REVIEW.md TST-417). macOS only, in a
    Designer the self-test started."""
    what = "AppKit's notifications come once Designer is hidden or unhidden, or its window minimized or shown again"
    if ctx.was_running or sys.platform != 'darwin':
        skip('designer facts', what, "it would hide the user's Designer" if ctx.was_running else 'macOS only')
        return
    with no_designer_starting():
        t, tried = await without_others_in_front(ctx, window_states.notified())
    m = re.search(r'NOTIFIED (.*)', t)
    seen = m.group(1) if m else (t.strip().splitlines() or ['?'])[-1]
    check(
        'designer facts',
        what,
        window_states.nothing_in_front(t)
        and seen
        == 'unhidden=True uncovered=True minimized=True unminimized=True minimized_by_button=True hidden=True '
        'hidden_flag=True',
        seen + tries_said(t, tried),
    )


async def check_a_window_under_designers_transparent_window_counts_as_visible(ctx: Ctx) -> None:
    """A window of Designer's own, shown alone in front of its main window first, then whole under it, counts as covered
    for macOS (occlusionState) with the main window opaque, and as visible with it transparent and click-through, as
    the 3D shot makes it: the shot doesn't tell the apps under it that their windows are covered (designer facts:
    designer_helpers/shot3d.py; REVIEW.md HLP-141). A window never shown read covered either way, so the reading alone
    in front comes first (REVIEW.md TST-412). A reading with a window of another app found in front of the window it
    reads is taken again (without_others_in_front), and read while no worker of the pool starts or quits its Designer
    (no_designer_starting: REVIEW.md TST-417, TST-467). So is a reading where the window under stays covered once
    brought in front of every normal window, after the first reading or the last: a window above them, or a locked
    screen, covers it (REVIEW.md TST-520). macOS only, in a Designer the self-test started."""
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
    POPUP_MS in one go (REVIEW.md HLP-134: 240 ms). Each spell of samples showing one counts on its own: on a view
    following a graph, the put-back's relink opens the menu a second time (REVIEW.md TST-953). macOS only, in a
    Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d with graph=: the Explorer's menu off the screen",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await c('screenshot_designer', THREE_D)  # the view drawn
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
        "popups on screen for %.0f ms at the longest of %d spells, in %d of %d samples, %d listing Designer's windows"
        % (watch.shown_ms, len(watch.spells), len(watch.times), watch.samples, watch.listed),
    )
    if not is_image(r):
        print('      the shot: %s' % ' / '.join(text(r).strip().splitlines()[-3:]))


async def check_a_3d_shot_with_graph_makes_the_explorers_menu_click_through(ctx: Ctx) -> None:
    """screenshot_designer('3d', graph=...) makes the Explorer's context menu it opens transparent and click-through
    (designer_helpers/view3d.py): a click the user makes at its place goes to the window under it, as through
    Designer's window (the user's choice: DECISIONS.md), and its action is still picked: the shot is taken. Read inside
    Designer as the menu's action is picked, through shoot_3d, the helper the tool calls, Designer's window minimized.
    When the view showed a graph's outputs before the shot, the put-back opens the menu again for the editor's graph
    (designer_helpers/scene3d.py), and that menu is so too. macOS only, in a Designer the self-test started."""
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
        bool(looks) and set(looks) == {'opacity=0 through=True'} and '3d render ' in t,
        'the menu: %s' % (', '.join(looks) or (t.strip().splitlines() or ['?'])[-1]),
    )


async def check_an_explorers_menu_closed_before_its_pick_is_said_so_and_gets_its_look_back(ctx: Ctx) -> None:
    """screenshot_designer('3d', graph=...) whose Explorer's menu is closed by something else in every try, once the
    shot made it transparent and click-through, before its action is picked: the shot says so, not that the menu didn't
    open, and gives each menu's window its look back, opaque and clickable (REVIEW.md HLP-146: the Explorer deleted the
    menu, and its window stayed transparent and click-through). Through shoot_3d, each menu closed by the snippet as
    the fade made it transparent. When the view showed a graph's outputs before the shot, the put-back's relink opens
    menus of its own, closed the same way (designer_helpers/scene3d.py). macOS only, in a Designer the self-test
    started."""
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
        and len(looks) >= int(tries.group(1))
        and set(looks) == {'opacity=1 through=False'},
        '%s; the menus after: %s' % (said, ', '.join(looks) or 'not read'),
    )


def _say(what: str, reply: str, *marks: str) -> None:
    """Prints under a failed check what the tool said in `reply` about `what` (_said_by_the_tool)."""
    print('      %s, the tool said: %s' % (what, ' / '.join(_said_by_the_tool(reply, *marks))))


def _said_by_the_tool(reply: str, *marks: str) -> list[str]:
    """The 3D shot's lines in a shot's `reply` ('3D view:', '3D render:'), and those starting with one of `marks`."""
    starts = ('3D view:', '3D render:', *(mark.split()[0] for mark in marks))
    return [line for line in reply.splitlines() if line.startswith(starts)] or ['nothing']


def _steps(ratio: float) -> int | None:
    """The zoom steps closer, 0 to 6, a plane `ratio` times as wide as at the start shows, STEP each within 5 %; None
    for none."""
    return next((k for k in range(7) if STEP**k * 0.95 <= ratio <= STEP**k * 1.05), None)


async def check_an_on_screen_3d_zoom_held_below_8_samples_names_the_rasterizers_settings(ctx: Ctx) -> None:
    """screenshot_designer('3d', zoom=...) on screen, with the Rasterizer's Samples at 4, then its accumulation
    antialiasing off, each holding the overlay's count below 8 (4, then 1, as designer_helpers/frames3d.py's docstring
    says): the zoom is done through the state file, 3 steps closer, and the view never settles at 8. The result names
    the count it saw, after a step or after the render, and what may hold it there, the Rasterizer's settings among
    them (Renderer > Edit settings), and has no STALE line (REVIEW.md HLP-215, the user's decision). The count at the render is 4, then 1. Each setting is
    changed only from Designer's default, and put back, in a finally, only from the value set. macOS only, in a
    Designer the self-test started."""
    c = ctx.c
    cases = (  # the name, the setting, its value for the case and its default, the count it holds the view at
        ("3d with zoom= and the Rasterizer's Samples at 4: zoomed, the settings named", 'samples', 4.0, 8.0, 4),
        ("3d with zoom= and the Rasterizer's antialiasing off: zoomed, the settings named", 'aa', False, True, 1),
    )
    if ctx.was_running or sys.platform != 'darwin':
        for name, *_ in cases:
            skip('screenshot_designer', name, USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    zoom = 3
    for name, kind, wanted, before, held in cases:
        # set only from its default, put back only from the value set: no other value is changed
        code = ctx.helper_source + rasterizer.set_rasterizer(kind, wanted, before)
        t = text(await c('execute_designer_code', {'code': code}))
        try:
            if rasterizer.DEFAULTS_BEFORE not in t:
                check('screenshot_designer', name, False, rasterizer.off_defaults(t))
                continue
            at_start = os.path.join(ctx.scratch, 'raster_%s_start.png' % kind)
            zoomed = os.path.join(ctx.scratch, 'raster_%s_zoom.png' % kind)
            set_up = 'mesh=%r, view=%r, graph=%r' % (TOP['mesh'], TOP['view'], TOP['graph'])
            framed = 'shoot_3d(%r, %s)' % (at_start, set_up)  # where the zoom starts
            started = text(await c('execute_designer_code', {'code': ctx.helper_source + framed}))
            code = ctx.helper_source + rasterizer.COUNTED + 'shoot_3d(%r, %s, zoom=%d)' % (zoomed, set_up, zoom)
            said = text(await c('execute_designer_code', {'code': code}))
            if not all(os.path.exists(path) for path in (at_start, zoomed)):
                failed = ' / '.join((started + '\n' + said).strip().splitlines()[-2:])
                check('screenshot_designer', name, False, 'a shot failed: %s' % failed)
                continue
            ratio = plane_width(grey_file(zoomed)) / max(plane_width(grey_file(at_start)), 1)
            counts = re.findall(r'^RENDER_COUNT (\S+)', said, re.M)
            # any count below 8: off screen, one last drawn mid-accumulation reads lower than the case's (REVIEW.md TST-681)
            # said of a step, or of the render once the window came back: with its antialiasing off, each paint reads 1,
            # which no step reads as a restart (frames3d.py)
            unsettled = re.search(
                r"hadn't settled within [\d.]+ s after (?:it|Designer's window came back on screen), its sample count at "
                r'(\d+)',
                said,
            )
            named = unsettled is not None and int(unsettled[1]) < 8 and '(Renderer > Edit settings)' in said
            stale = '3D render: identical' in said  # STALE (REVIEW.md HLP-212)
            zoomed_named = named and not stale and _steps(ratio) == zoom and counts[-1:] == [str(held)]
            check(
                'screenshot_designer',
                name,
                zoomed_named,
                'the settings named: %s; STALE: %s; the plane %.2fx; the count at the render: %s'
                % (named, stale, ratio, ','.join(counts) or 'not read'),
            )
            if not zoomed_named:
                _say('the start', started)
                _say('the zoom', said)
                say_renders(('the start', at_start), ('zoomed', zoomed))
        finally:
            code = ctx.helper_source + rasterizer.set_rasterizer(kind, before, wanted)
            back = text(await c('execute_designer_code', {'code': code}))
            await at_rest(c, ctx.helper_source)
            # the snippet's own lines, which no other line holding ' after' passes for, and its line says the values it
            # left (REVIEW.md TST-677, TST-683)
            if rasterizer.SET.search(t) and rasterizer.DEFAULTS_SET not in back:
                check('screenshot_designer', name, False, rasterizer.off_defaults(back, 'after'))


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
    await c('screenshot_designer', THREE_D)  # the view drawn
    with no_designer_starting():
        for way in [way for way in window_states.WAYS if (way == QT_MINIMIZED) == in_front]:
            tried = 0
            retaken: list[str] = []  # what each try taken again said: what a pass leaves out (REVIEW.md TST-464)
            while tried < TRIES:
                tried += 1
                # the frame a stale shot repeats
                base = await c('screenshot_designer', {**THREE_D, **SMALL})
                put = text(await c('execute_designer_code', {'code': ctx.helper_source + window_states.put(way)}))
                try:
                    # the pan comes before the zoom, which shrinks it (PANNED)
                    r = await c('screenshot_designer', {**THREE_D, **TOP, 'zoom': -4, 'pan': [0.25, 0.0]})
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
                abs(moved - PANNED) <= PAN_OFF
                and SHOWN[way] in text(r)
                and all(state.get(key) == value for key, value in AFTER[way])
                and (state.get('opacity'), state.get('through')) == ('1', 'False')
                and (way != 'covered' or state.get('order') == off.get('order') == 'cover,main,below')
                and kept is not False
                and not activated
            )
            tries = '; %d tries' % tried if tried > 1 else ''
            check(
                'screenshot_designer',
                what,
                ok,
                'the plane moved %.4f of the view left, %.4f wanted%s' % (moved, PANNED, tries),
            )
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
PUT_BACK_STEP = SET_UP_STEP + 'the 3D view as it was'  # the put-back's, said as it begins


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
    await c('screenshot_designer', THREE_D)  # the view drawn
    path = os.path.join(ctx.scratch, 'transparent.png')
    for way in (LEFT_TRANSPARENT,) if in_front else ('minimized', 'covered', 'hidden'):
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
    keyboard stays where it is. Then Designer made the active app at the shot's own render, after the set-up: made
    opaque before the put-back's load (REVIEW.md HLP-264). Through shoot_3d, the helper the tool calls. macOS only, in a
    Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            '3d with Designer made the active app during the shot: its window opaque at once',
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await c('screenshot_designer', THREE_D)  # the view drawn
    path = os.path.join(ctx.scratch, 'switched.png')
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
    # Designer made the active app at the shot's own render, after the set-up: made opaque before the put-back's load
    # (REVIEW.md HLP-264: the windows stayed transparent through it)
    path = os.path.join(ctx.scratch, 'switched_at_the_render.png')
    try:
        await c('execute_designer_code', {'code': ctx.helper_source + window_states.put('minimized')})
        t = text(
            await c('execute_designer_code', {'code': ctx.helper_source + window_states.switched_at_the_render(path)})
        )
    finally:
        await at_rest(c, ctx.helper_source)
    back = t.find(PUT_BACK_STEP)
    ok = window_states.MADE_OPAQUE in t and back != -1 and t.index(window_states.MADE_OPAQUE) < back
    check(
        'screenshot_designer',
        "3d, Designer made the active app at the shot's render: the window opaque before the 3D view is put back",
        ok,
        'said opaque at %d, the put-back begun at %d' % (t.find(window_states.MADE_OPAQUE), back),
    )
    if not ok:
        lines = [line for line in t.splitlines() if line.startswith(("Designer's window: ", '3D view'))]
        print("      the shot's lines: %s" % (' / '.join(lines) or ' / '.join(t.strip().splitlines()[-3:])))


# a 3D shot with the set-up SET_UP, its render deleted
SHOT_WITH = dedent("""
    import os, tempfile
    out = os.path.join(tempfile.mkdtemp(prefix='mcp_selftest_'), 'shot.png')
    shoot_3d(out, **SET_UP)
    os.remove(out)
    os.rmdir(os.path.dirname(out))
""")
# Designer's window left as it is by the shot: no _MacWindow, as elsewhere than macOS
AS_IT_IS = '_mac_window = lambda mw: None\n'
# each set-up whose stale render is said: what, its values shot on screen, then shot minimized, and its said line
STALE_SET_UPS = (
    ('a pan', {'pan': [0.25, 0.0]}, {'pan': [0.25, 0.0]}, 'pan 0.25 of the view right'),
    # the user's ask (2026-11-18): the light settled as the camera is; each a change from the value before
    ('an exposure change', {'environment_exposure': 1.0}, {'environment_exposure': 2.0}, 'environment exposure 2'),
)


async def check_a_render_that_didnt_follow_a_set_up_is_said(ctx: Ctx) -> None:
    """A render identical to the one before a pan, or before an exposure change, is said, after its retakes
    (designer_helpers/shot3d.py, STALE; REVIEW.md SRV-146): with Designer's window minimized and left so, the render is
    the view's last frame (covered, it was drawn in some Designers launch_designer opened: REVIEW.md TST-433). On
    screen the change changes the render, and nothing is said: Designer's QImage compares pixels. macOS only (the window
    minimized through _MacWindow), in a Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        for what, _, _, _ in STALE_SET_UPS:
            skip(
                'screenshot_designer',
                "3d: a render that didn't follow %s" % what,
                USERS_3D_VIEW if ctx.was_running else 'macOS only',
            )
        return
    await users_checker(c, ctx.helper_source, THREE_D)
    for what, on_screen, minimized, said in STALE_SET_UPS:
        # on screen as the shot puts it: a window over Designer's would leave the render stale (REVIEW.md TST-390)
        code = ctx.helper_source + 'SET_UP = %r\n' % on_screen + SHOT_WITH
        on = text(await c('execute_designer_code', {'code': code}))
        try:
            put = window_states.put('minimized')
            code = ctx.helper_source + put + AS_IT_IS + 'SET_UP = %r\n' % minimized + SHOT_WITH
            off = text(await c('execute_designer_code', {'code': code}))
        finally:
            await at_rest(c, ctx.helper_source)
        said_on, said_off = ('3D render: identical' in t for t in (on, off))
        check(
            'screenshot_designer',
            "3d: a render that didn't follow %s is said; one that did isn't" % what,
            said_off and not said_on and said in off,
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
    base = await with_checker(c, {**THREE_D, **SMALL})
    path = os.path.join(ctx.scratch, 'covered_during_pan.png')
    set_up = "mesh='Plane', view='Top', zoom=-4, graph=%r, pan=[0.25, 0.0]" % VIEW3D_GRAPH
    try:
        # on screen first, as a window the user is looking at: from hidden, the shot hides Designer again, and a hidden
        # Designer reads covered whatever the order (REVIEW.md TST-422)
        await c('execute_designer_code', {'code': ctx.helper_source + window_states.put('on screen')})
        t = text(
            await c(
                'execute_designer_code',
                {'code': ctx.helper_source + window_states.during_pan(path, 'cover', set_up)},
            )
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
    ok = abs(moved - PANNED) <= PAN_OFF and (not judged or (window_states.AGAIN in t and behind))
    check('screenshot_designer', what, ok, 'the plane moved %.4f of the view left, %.4f wanted' % (moved, PANNED))
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
    await c('screenshot_designer', THREE_D)  # the view drawn
    for case, (way, event, expected, said, pairs) in PUT_BACK.items():
        if (case in PUT_BACK_IN_FRONT) != in_front:
            continue
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
    """screenshot_designer('3d') refusing a set-up the 3D view rules out (a mesh it doesn't have) refuses before it
    puts Designer's window on screen: a minimized window stays minimized, and nothing is said of it
    (REVIEW.md HLP-127). macOS only, in a Designer the self-test started."""
    c = ctx.c
    if ctx.was_running or sys.platform != 'darwin':
        skip(
            'screenshot_designer',
            "3d: a refused set-up leaves Designer's window as it was",
            USERS_3D_VIEW if ctx.was_running else 'macOS only',
        )
        return
    await c('screenshot_designer', THREE_D)  # the view drawn
    try:
        await c('execute_designer_code', {'code': ctx.helper_source + window_states.put('minimized')})
        r = await c('screenshot_designer', {**THREE_D, 'mesh': 'Teapot', 'orbit': [30, 0]})
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
        and "unknown mesh 'Teapot'" in text(r)
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
    3D view as it was changed off screen (a pan of the self-test's own, which the view doesn't draw there): the shot
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
    await users_checker(c, ctx.helper_source, THREE_D)
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


# Designer hidden, at rest: its window brought on screen as a 3D shot does (_on_screen), then read once macOS no
# longer says Designer is hidden: (whether macOS said so, the windows in front of it, the times Qt stopped exposing the
# window once it had). Run after WHO (window_owner.py)
SHOWN_FROM_HIDDEN = dedent("""
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    frames = _frames_of(mw, _viewport(_3d_dock(mw)))
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
            unhidden = _wait_unhidden(mac, 3.0)
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
            before, read = read_value(said, 'HIDDEN_BEFORE'), read_value(said, 'SHOT')
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
    read = read_value(said, 'FIRST_SHOT')
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
    read = read_value(said, 'DROPPED')
    check(
        'screenshot_designer',
        what,
        read == (True, True),
        '(the watch gone, its spy gone) %r; %s' % (read, said.strip()[-200:]),
    )


# a shot's window (_on_screen), each try: a pan of the self-test's own (window_states.PAN_OF_ITS_OWN), Designer hidden
# as soon as the count reads 3 or less, or back at 8 when that was missed, then the window shown again as before a
# render (_Screen.again); the pans go right then left, so the camera ends where it began
SHOWN_FROM_LOWER = window_states.PAN_OF_ITS_OWN + dedent("""
    from PySide6 import QtCore
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    dock = _3d_dock(mw)  # held: without, the viewport's wrapper went stale
    viewport = _viewport(dock)
    mac = _MacWindow(mw)
    frames = _frames_of(mw, viewport)
    read = []  # each try: (the count as Designer was hidden, the count as the show's wait ended)
    try:
        with _on_screen(mw, frames) as screen:
            for i in range(6):
                since = frames.mark()[0]
                _ws_pan(viewport, 20 if i % 2 == 0 else -20)
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
    await ctx.c('screenshot_designer', THREE_D)  # the view drawn, at rest
    said = text(await ctx.c('execute_designer_code', {'code': ctx.helper_source + SHOWN_FROM_LOWER}))
    read = read_value(said, 'READ')
    lower = [shown for hid, shown in read if isinstance(hid, int) and hid <= 3] if is_pairs(read) else []
    check(
        'screenshot_designer',
        what,
        len(lower) >= 3 and all(shown == 8 for shown in lower),
        '(the count as Designer was hidden, the count as the wait ended), each try: %r' % (read,)
        if read is not None
        else said.strip()[-200:],
    )


# the meshes whose Scene action is checked, read as the set-up's mesh step reads the action of the mesh asked
# a 3D shot given a mesh, saved to %r, the meshes the Scene menu checks printed at each render (SHOWN=), before the
# shot puts the view back
SHOWN_MESH = dedent("""
    _shown_render = _3d_render
    def _3d_render(mw):
        bar = _3d_dock(mw).findChildren(QtWidgets.QMenuBar)[0]
        keep = [mw, bar]
        print('SHOWN=%%s' %% ', '.join(m for m in MESHES if _menu_action(bar, keep, 'Scene', m).isChecked()))
        return _shown_render(mw)
    shoot_3d(%r, mesh=%r)""")


async def check_the_3d_views_scene_menu_checks_the_mesh_shown(ctx: Ctx) -> None:
    """The 3D view's Scene menu checks the mesh the view shows: as a shot given Sphere, then one given Plane, renders,
    each is the one checked (designer facts: scene3d.py reads the action of the mesh asked, and writes no mesh shown
    already; REVIEW.md TST-391, HLP-195, HLP-199). In a Designer the self-test started."""
    c = ctx.c
    if ctx.was_running:
        skip('designer facts', "the 3D view's Scene menu checks the mesh shown", USERS_3D_VIEW)
        return
    seen: list[str] = []
    for mesh in ('Sphere', 'Plane'):
        path = os.path.join(ctx.scratch, 'shown_mesh.png')
        t = text(await c('execute_designer_code', {'code': ctx.helper_source + SHOWN_MESH % (path, mesh)}))
        shown = re.findall(r'^SHOWN=(.*)$', t, re.M)  # before the set-up, then as the shot renders
        seen.append(shown[-1].strip() if shown else (t.strip().splitlines() or ['nothing printed'])[-1])
    check(
        'designer facts',
        "the 3D view's Scene menu checks the mesh it shows",
        seen == ['Sphere', 'Plane'],
        'checked as each shot rendered, given Sphere, then Plane: %s' % ', '.join(seen),
    )


async def check_the_3d_view_refuses_what_it_cant_show(ctx: Ctx) -> None:
    """A mesh or view the 3D view's menus don't have, an environment map Designer doesn't have, and a graph with one
    output (Designer would ask which channel to show it in), are refused before anything changes, so these run in the
    user's Designer too."""
    c = ctx.c
    t = text(await c('screenshot_designer', {**THREE_D, 'mesh': 'Teapot'}))
    check('screenshot_designer', 'an unknown mesh is refused, naming the meshes', 'Teapot' in t and 'Torus' in t, t)
    t = text(await c('screenshot_designer', {**THREE_D, 'environment': 'Studio'}))
    check(
        'screenshot_designer',
        "an environment map Designer doesn't have is refused, naming its maps",
        "unknown environment 'Studio'" in t and DARK in t and 'corsica_beach' in t,
        t[-150:],
    )
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


async def check_designer_stayed_behind(ctx: Ctx, watch: window_server.FrontWatch) -> None:
    """Over every check up to the window checks off screen (`watch`'s samples, the front watch run() kept, sampled every
    FRONT_EVERY s or so: window_server.py; REVIEW.md TST-471, TST-473), no normal window of Designer's (layer 0) at an
    opacity above 0 was seen in front of another app's window it overlaps, and Designer was never seen the active app;
    its windows above the normal ones, the Explorer's menus, are said, not judged
    (window_server.stayed_behind): the window checks set up their ways behind every window (window_states), and the
    shot keeps its window transparent while it is in front (the user's report: REVIEW.md SRV-149). The checks that need
    a window in front of the user's run after them, unwatched (run). Up to FRONTS_SAID stretches in front are printed
    whole after the check, each with the checks recorded around its start, the others counted
    (window_server.fronts_said). macOS only, in a Designer the self-test started."""
    name = (
        "every check up to the window checks off screen leaves Designer's windows behind the other apps', and Designer"
        ' not the active app'
    )
    if ctx.was_running or sys.platform != 'darwin':
        skip('self-test', name, USERS_3D_VIEW if ctx.was_running else 'macOS only')
        return
    pid = int(text(await ctx.c('execute_designer_code', {'code': 'import os; print(os.getpid())'})).strip())
    behind, said = window_server.stayed_behind(watch.samples, pid)
    check('self-test', name, behind, said)
    for line in window_server.fronts_said(watch.samples, pid, common.checked, watch.names):  # a detail is cut
        print('      in front %s' % line)


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
    await c('screenshot_designer', THREE_D)  # the 3D view there, as the way needs
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
        await check_orbit_pan_and_zoom_start_from_the_users_own_view(ctx)
        await check_an_editors_graph_with_no_outputs_is_said_not_to_be_followed(ctx)
        await check_a_set_up_shot_on_a_view_following_a_graph_leaves_override_material_off(ctx)
        await check_graph_finds_its_row_in_a_collapsed_package(ctx)
        await check_a_set_up_checks_what_it_needs_first_and_says_what_it_set(ctx)
        await check_a_tiling_on_a_material_with_no_pattern_is_said_to_change_nothing(ctx)  # on its plain graph
        await check_values_a_3d_set_up_finds_shown_already_take_no_wait(ctx)
        await check_a_material_the_mesh_doesnt_use_doesnt_stop_tiling(ctx)
        await check_the_environment_turns_brightens_and_changes_the_light(ctx)
        await check_a_3d_shot_setting_the_light_renders_the_view_once_it_settled(ctx)
        await check_an_abort_putting_a_shots_window_back_still_hides_designer_again(ctx)
        await check_the_3d_views_frames_say_when_it_has_drawn(ctx)
        await check_a_hidden_designers_window_is_brought_in_front_for_a_3d_shot_once_its_unhide_took(ctx)
        await check_appkits_notifications_come_once_designers_window_changed(ctx)
        await check_a_watch_of_the_3d_views_frames_dropped_without_close_goes_at_once(ctx)
        await check_a_3d_shots_window_shown_again_mid_accumulation_waits_for_the_count_at_rest(ctx)
        await check_the_minimized_way_shows_none_of_designers_windows_as_its_window_flies_to_the_dock(ctx)
        await check_a_timer_goes_with_the_parent_its_function_held(ctx)
        await check_the_3d_view_isnt_drawn_while_designers_window_is_off_screen(ctx)
        await check_a_3d_shot_with_graph_keeps_the_explorers_menu_off_the_screen(ctx)
        await check_a_3d_shot_with_graph_makes_the_explorers_menu_click_through(ctx)
        await check_an_explorers_menu_closed_before_its_pick_is_said_so_and_gets_its_look_back(ctx)
        await check_an_explorers_menu_closed_before_its_pick_is_opened_again(ctx)
        await check_an_on_screen_3d_zoom_held_below_8_samples_names_the_rasterizers_settings(ctx)
        await check_a_3d_shot_puts_designers_window_on_screen_without_taking_focus(ctx)
        await check_a_3d_shot_keeps_designers_window_transparent_and_click_through_while_off_screen(ctx)
        await check_a_render_that_didnt_follow_a_set_up_is_said(ctx)
        await check_a_covered_window_goes_back_behind_its_cover_or_stays_in_front_once_the_cover_is_gone(ctx)
        await check_a_refused_3d_set_up_leaves_designers_window_as_it_was(ctx)
        await check_a_plain_3d_shot_shows_a_change_made_while_designers_window_was_off_screen(ctx)
        await check_the_3d_views_scene_menu_checks_the_mesh_shown(ctx)  # watched too (REVIEW.md TST-473)
    await check_designer_stayed_behind(ctx, front)
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
