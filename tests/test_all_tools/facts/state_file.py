"""The 3D view's own state file (`.sbsscn`, ROADMAP item 131), for facts' state file checks: the Designer code they
send, and the file read and edited by its text. Each check runs only in a Designer an agent started on macOS, which
has a home of its own (`CFFIXED_USER_HOME`). It skips in the user's Designer and off macOS, where the self-test's
Designer writes the user's own AppData (REVIEW.md TST-890). Nothing reads, writes or removes a state file outside that
home: `_sf_path`, which gives every path the checks use, refuses first.

What the checks re-measure, as measured on macOS in Designers an agent started (Designer 16.0.7, 2026-11-25):

- Scene > Save Current State As Default writes `user_view3d_settings.sbsscn` in Qt's AppDataLocation, in a folder
  named after Designer's major and minor version (`16.0`): in the Designer's own home, where the user's is in theirs.
  Once a graph's outputs are on the mesh, it also writes their textures as PNG files, into
  `user_view3d_settings_resources/` beside it. Scene > Reset Scene loads the file. Neither shows a window or a dialog
  nor adds an undo step, the Designer hidden.
- Reset Scene reads the file after it returns, in Designer's event loop: a file written right after the trigger is the
  one loaded. The Scene menu checks no mesh as the trigger returns, read at once, and a mesh again once the load has
  ended. A mesh of the user's own, Designer's box.fbx by its file:// URL, it checks none of, as the trigger returns or
  once the view settled. Its load restarts the view, and a Save once the view settled holds that mesh: the restart,
  then the view settled, mark its load's end.
- The format, its version and the fields the set-up sets, as designer_helpers/state3d.py reads and edits them, which
  these checks run. One field edited loads alone, and a section left out comes back at Designer's defaults. The
  environment's rotation is in turns and its intensity is the Exposure, as Environment > Edit properties shows them.
- Designer's Frame, each view's direction and each mesh's point and distance at two aspects, against the poses
  `view=` writes (state3d._framed; state_camera.py). Each mesh picked in the Scene menu is held by its id in the table
  (state3d.FRAMING).
- A mesh picked in the Scene menu is framed as Frame frames it, the camera's direction kept, docked and wider than
  tall, as `mesh=` writes it; while a load of another mesh's id keeps the file's camera.
- A map of Designer's own dropped on the 3D view is saved as the URL the set-up writes (view3d._environment_maps), and
  copied nowhere beside the state file.
- What a 3D shot with a set-up puts back: the user's view, Override Material off and the AOV included, the default
  file and folder byte for byte or none where there were none, a backup an earlier call left, put back first or
  removed; and a file missing the camera refused, nothing written (designer_helpers/scene3d.py).
- A load turning the camera from AWAY to GLIDES_TO (state_camera.py) glides it there: a Save once the load has ended,
  while the view's sample count holds at its restart, holds another camera than the file's. The count rises once the
  camera has stopped (frames3d.py, `_Counts.moved`), and a Save then holds the file's camera. A load whose camera is
  the session's leaves it where it is.
- After a load, the view no longer follows the graph. The load leaves the folder of the textures a Save wrote before;
  a Save then writes none, and deletes the folder. Opening another graph, then that one, puts its outputs on the mesh
  again.
- A load puts the 3D view's AOV back to Beauty. With the GPU Pathtracer set, the file saved with the Rasterizer, it
  keeps the session's renderer and Displacement toggle.
- A load turns the material's Materials > Override Material on, though the file holds it off
  (`override_existing_material`, which a Save writes as the menu shows it), a graph's outputs on the mesh.

Measured on 2026-11-25 and not checked here, with the later check that pins each where the branch has one:
- the file holds a Displacement toggle (`rs-adobe_displacementenabled`), which a load with the GPU Pathtracer set
  left as the session had it;
- a minimized and a covered Designer, like a hidden one, showed nothing at a Save or a Reset Scene (once each);
- a Save before the load had ended saved a scene without its mesh, and the scene then ended at Designer's defaults;
- the URL each of the 34 maps a drop saved, the two that check drops among them (2026-11-26);
- Materials > Override Material missing while no graph's outputs were on the mesh: a graph open in a Designer just
  started, the mesh's material, Default, held no such entry (once, 2026-11-26);
- the user's Default State File, `preferences/view3d/stateSaveFileUrl` in `user_project.sbsprj`: the 3D view starts
  from it (lifecycle's check of the Default State File pins Save and Reset Scene using it, a graph's textures beside
  it);
- a load of a camera at pitch 89, 90, 100, -100 and 180, and at yaw 200, read back as written (once each);
- where a glide starts, and whether a camera turned glides at all, varied. Files built on another Designer's state
  started each glide near Designer's default pose (about 10 loads). A camera this Designer had saved, about 20 units
  from the session's, it jumped to (1 load), and so it did to a pose at yaw 180 (2 loads). On 2026-11-26, 7 of 8
  loads, the session's own camera among them, glided from near Designer's Default view; one to yaw 40, pitch 10
  jumped (designer_helpers/scene3d.py waits for the count's rise either way).

The checks keep the Designer's own file as they found it (`kept`): its file and folder are copied aside first, and put
back at the end, after the state saved first is loaded again, by state3d.py's own backup. A Designer that had none is
left with none. A backup a 3D shot left there is removed, before and after: no other check meets it.
"""

import contextlib
import os
import re
import shutil
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator, Callable
from textwrap import dedent
from typing import TYPE_CHECKING, NamedTuple

import designer_helpers
from test_all_tools.common import Ctx, text
from test_all_tools.facts.state_camera import turned

if TYPE_CHECKING:  # for the checker: the part as the helpers hold it
    from designer_helpers import state3d
else:
    state3d = designer_helpers.standalone('state3d')

NAME = 'user_view3d_settings.sbsscn'
NUMBER = re.compile(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?')

# Designer's side, its functions defined after the helpers' text (ctx.helper_source), which they call
STATE = dedent("""
    import contextlib
    import os
    import shutil
    from PySide6 import QtCore, QtGui, QtWidgets


    def _sf_path():
        base = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.AppDataLocation)
        version = '.'.join(QtCore.QCoreApplication.applicationVersion().split('.')[:2])
        path = os.path.join(base, version, 'user_view3d_settings.sbsscn')
        home = os.environ.get('CFFIXED_USER_HOME', '')
        if not home or not path.startswith(os.path.join(home, '')):
            raise RuntimeError("the state file %s isn't in the Designer's own home %r: not touched" % (path, home))
        return path


    def _sf_bar():
        # the 3D view's menu bar, and what keeps its wrappers
        mw = _main_window()
        dock = _3d_dock(mw)
        bar = dock.findChildren(QtWidgets.QMenuBar)[0]
        return bar, [mw, dock, bar]


    def _sf_action(*path):
        bar, keep = _sf_bar()
        return _menu_action(bar, keep, *path), keep


    def _sf_menu(*path):
        action, keep = _sf_action(*path)
        action.trigger()


    def _sf_override(on=None):
        # Materials > the mesh's material > Override Material, set to `on` first unless None: checked or not
        bar, keep = _sf_bar()
        action = _overrides(bar, keep)[0]
        if on is not None and action.isChecked() != on:
            action.trigger()
            _process_events()
        return action.isChecked()


    def _sf_save():
        path = _sf_path()
        _sf_menu('Scene', 'Save Current State As Default')
        return path


    def _sf_checked(menu_name):
        menu, keep = _sf_action(menu_name)
        menu = menu.menu()
        keep.append(menu)
        menu.aboutToShow.emit()
        return [a.text() for a in menu.actions() if a.isCheckable() and a.isChecked()]


    def _sf_meshes():
        # the meshes the Scene menu checks (view3d.MESHES), its other entries left out: Display UVs in 2D View, for one,
        # may be on throughout (REVIEW.md TST-958)
        return [m for m in _sf_checked('Scene') if m in MESHES]


    def _sf_load(then=None, mid=None):
        # mid: a Save once the load has ended (the count restarted, the Scene menu checking a mesh again), copied there
        mw = _main_window()
        frames = _frames_of(mw, _viewport(_3d_dock(mw)))

        def restarted():  # since the mark below
            return frames._counts is not None and frames._counts.restart(since[0]) is not None

        try:
            with _on_screen(mw, frames):
                since = frames.mark()
                _sf_menu('Scene', 'Reset Scene')
                if then is not None:
                    then()
                if mid is not None:
                    ended = frames.until(lambda: restarted() and bool(_sf_meshes()), SETTLE_LIMIT)
                    if ended:
                        shutil.copyfile(_sf_save(), mid)
                    print('MID_SAVED=%s' % ended)
                print('LOADED=%s' % (frames.moved(since) and restarted()))
        finally:
            frames.close()


    def _sf_picked(frames, mesh):
        # the mesh picked in the Scene menu, which frames it, waited for on the watch `frames`; one shown already, picked
        # again, changes nothing
        picked, keep = _sf_action('Scene', mesh)
        if not picked.isChecked():
            with _Waiting(frames):
                picked.trigger()


    def _sf_switched(frames, screen, mesh):
        # the mesh picked (_sf_picked), no Frame; then saved, the path returned
        _sf_picked(frames, mesh)
        return _sf_save()


    def _sf_framed(frames, screen, mesh, view=None):
        # Designer's own framing, on the watch `frames`, Designer's window on screen (`screen`, _on_screen's): the mesh
        # picked (_sf_picked), then the view picked in the Camera menu, its turn waited for, then Frame; then saved, the
        # path returned
        _sf_picked(frames, mesh)
        if view is not None:
            since = frames.mark()
            _sf_menu('Camera', view)
            frames.moved(since)  # Frame at once cancels the turn
            screen.again()
        with _Waiting(frames):
            _sf_menu('Camera', 'Frame')
        return _sf_save()


    @contextlib.contextmanager
    def _sf_on_screen():
        # Designer's window on screen, as a 3D shot puts it, and the watch of the 3D view's frames: (frames, screen)
        mw = _main_window()
        frames = _frames_of(mw, _viewport(_3d_dock(mw)))
        try:
            with _on_screen(mw, frames) as screen:
                yield frames, screen
        finally:
            frames.close()


    def _sf_aov(pick=None):
        # the 3D view's AOVs checked, `pick` picked first unless None: listed once the view has drawn (ROADMAP item 81)
        mw = _main_window()
        dock = _3d_dock(mw)
        button = next(b for b in dock.findChildren(QtWidgets.QToolButton) if b.objectName() == '3dview.display.aov')
        menu = button.menu() or button.defaultAction().menu()
        keep = [mw, dock, button, menu]
        menu.aboutToShow.emit()
        _process_events()
        if pick is not None:
            next(a for a in menu.actions() if a.text() == pick).trigger()
            _process_events()
        return [a.text() for a in menu.actions() if a.isCheckable() and a.isChecked()]


    def _sf_drop(name):
        # Designer's map `name` dragged onto the middle of the 3D viewport, as from its Library: entered, moved, dropped
        viewport = _viewport(_3d_dock(_main_window()))
        folder = os.path.join(_APP.getPath(SDApplicationPath.DefaultResourcesDir), 'view3d', 'maps')
        path = next(os.path.join(folder, f) for f in os.listdir(folder) if os.path.splitext(f)[0] == name)
        data = QtCore.QMimeData()
        data.setUrls([QtCore.QUrl.fromLocalFile(path)])
        at = QtCore.QPoint(viewport.width() // 2, viewport.height() // 2)
        link, none, plain = (
            QtCore.Qt.DropAction.LinkAction, QtCore.Qt.MouseButton.NoButton, QtCore.Qt.KeyboardModifier.NoModifier
        )
        for event in (
            QtGui.QDragEnterEvent(at, link, data, none, plain),
            QtGui.QDragMoveEvent(at, link, data, none, plain),
            QtGui.QDropEvent(QtCore.QPointF(at), link, data, none, plain),
        ):
            QtWidgets.QApplication.sendEvent(viewport, event)


    def _sf_environment_shown():
        # Environment > Edit properties: the Rotation Angle's degrees and the Exposure, as the Parameters panel shows
        # them once it built them, printed; then the panel turned back to the graph in the editor
        mw = _main_window()
        params = _visible_dock(mw, _PANEL_AREAS['parameters'])
        keep = [mw, params]

        def spins(name):  # the spin boxes of the field whose object name ends in -`name`, Turns then Degrees
            fields = [w for w in params.findChildren(QtWidgets.QWidget) if w.objectName().endswith('-' + name)]
            keep.extend(fields)
            return fields[0].findChildren(QtWidgets.QDoubleSpinBox) if fields else []

        try:
            _sf_menu('Environment', 'Edit properties')
            _until(lambda: len(spins('dome_rotation_angle')) == 2 and bool(spins('intensity')), SETTLE_LIMIT)
            print('DEGREES=%r' % spins('dome_rotation_angle')[1].value())
            print('EXPOSURE=%r' % spins('intensity')[0].value())
        finally:
            editor = _current_graph()
            if editor is not None:
                _ui_mgr().openResourceInEditor(editor)
                _process_events()


    def _sf_sized(size):
        # the 3D panel floated and sized (width, height) so its viewport has another aspect; None: docked again. The
        # viewport's size printed. Only with Designer hidden, as the self-test keeps it at rest: a floating panel would
        # show on the user's screen otherwise
        mw = _main_window()
        mac = _mac_window(mw)
        if size is not None and mac is not None and not mac.hidden():
            raise RuntimeError("Designer isn't hidden: its floating 3D panel would show on the user's screen")
        dock = _3d_dock(mw)
        dock.setFloating(size is not None)
        if size is not None:
            dock.resize(*size)
        _process_events()
        viewport = _viewport(dock)
        print('VIEWPORT=%d,%d' % (viewport.width(), viewport.height()))
    """)
LOADED_THEN_SAVED = dedent("""
    _sf_load()
    _sf_save()""")
# the 3D panel docked, its viewport's size printed, then the state file loaded
DOCKED_THEN_LOADED = dedent("""
    _sf_sized(None)
    _sf_load()""")
# a load with a Save before its glide ended, copied to %r, then a Save once it has
MID_LOADED_THEN_SAVED = dedent("""
    _sf_load(mid=%r)
    _sf_save()""")
# Reset Scene, then at once the file at %r copied over the state file, before Designer's event loop runs
WRITTEN_AFTER_THE_TRIGGER = dedent("""
    _sf_load(then=lambda: shutil.copyfile(%r, _sf_path()))
    _sf_save()""")
# what a 3D shot sets up, saved as it renders, copied to %r (the shot then puts the view and the file back)
SET_UP_THEN_SAVED = dedent("""
    _sf_render = _3d_render
    def _3d_render(mw):
        shutil.copyfile(_sf_save(), %r)
        return _sf_render(mw)
    shoot_3d(%r, None, 'Sphere', None, 0, 2.5, None, None, 'airport', 90, 1.5)""")
# each view of Designer's own on the Plane, in the 3D panel as it is, framed and saved, each copied to the path given
VIEWED = dedent("""
    with _sf_on_screen() as (_frames, _screen):
        for _view, _path in %r:
            shutil.copyfile(_sf_framed(_frames, _screen, 'Plane', _view), _path)""")
# each mesh set up by __SAVED__ in the 3D panel sized to each size given (None: docked), saved and copied to the path
# given
_SIZED = dedent("""
    try:
        for _size, _meshes in %r:
            _sf_sized(_size)  # with Designer hidden: before its window is put on screen
            with _sf_on_screen() as (_frames, _screen):
                for _mesh, _path in _meshes:
                    shutil.copyfile(__SAVED__(_frames, _screen, _mesh), _path)
    finally:
        _sf_sized(None)""")
FRAMED = _SIZED.replace('__SAVED__', '_sf_framed')  # each mesh framed by Designer's own Frame
SWITCHED = _SIZED.replace('__SAVED__', '_sf_switched')  # each mesh picked in the Scene menu, with no Frame
# each map named dropped on the 3D view, then the state saved: the URL it holds printed, the one _environment_maps gives,
# and the files beside the state file
DROPPED = dedent("""
    _sf_maps = _environment_maps()
    for _name in %r:
        _sf_drop(_name)
        _text = _state_text(_sf_save())
        _folder = _state_resources(_sf_path())
        print('DROPPED=%%s|%%s|%%s|%%s' %% (
            _name,
            _state_fields(_text, ['environment'])['environment'],
            _sf_maps[_name],
            sorted(os.listdir(_folder)) if os.path.isdir(_folder) else [],
        ))""")
# the 3D view's AOV, `%r` picked first unless None, Designer's window on screen for the view to list its AOVs
AOV_SHOWN = dedent("""
    with _sf_on_screen():
        print('AOV=%%s' %% _sf_aov(%r))""")
# the 3D view's AOV read, then Beauty, Designer's own, picked again
AOV_READ_BACK = dedent("""
    with _sf_on_screen():
        print('AOV=%s' % _sf_aov())
        _sf_aov('Beauty')""")
# Designer's own box.fbx (its resources' python/tests/assets), a mesh of the user's own: its path
BOX_PATH = dedent("""
    _sf_box = os.path.join(_APP.getPath(SDApplicationPath.DefaultResourcesDir), 'python', 'tests', 'assets', 'box.fbx')
    print('BOX=%s' % (_sf_box if os.path.isfile(_sf_box) else ''))""")
# Reset Scene, Designer's window on screen: the Scene menu's checked entries as it returns and once the view settled
# after it (_Frames.settled), then the state saved
LOADED_SETTLED = dedent("""
    with _sf_on_screen() as (_frames, _screen):
        _since = _frames.mark()
        _sf_menu('Scene', 'Reset Scene')
        print('AT_TRIGGER=%r' % _sf_meshes())
        print('RESTARTED=%s' % _frames.restarted(_since))
        print('SETTLED=%s' % _frames.settled(_since))
        print('AFTER=%r' % _sf_meshes())
    _sf_save()""")
# a graph's outputs computed, so that the textures Save writes are its outputs'
COMPUTED_THEN_SAVED = dedent("""
    find_graph(%r).compute()
    _process_events()
    _sf_save()""")

# Save, then Reset Scene, the Designer as it is (hidden at rest in the self-test): the file written where printed, what
# shows and the undo list before and after each, then the load's start and end, the Scene menu checking no mesh, then
# one again
ENTRIES = dedent("""
    mw = _main_window()
    mac = _mac_window(mw)
    app = QtWidgets.QApplication.instance()
    viewport = _viewport(_3d_dock(mw))
    _sf_held = []  # the undo dropdown's wrappers: a menu read through a dropped one reads as deleted


    def _sf_shown():
        windows = sorted(
            '%s:%s' % (type(w).__name__, w.objectName() or w.windowTitle()) for w in app.topLevelWidgets() if w.isVisible()
        )
        state = None if mac is None else (mac.hidden(), mac.minimized(), mac.covered())
        return windows, app.activeModalWidget() is None, app.activePopupWidget() is None, state


    def _sf_undo():
        for w in app.allWidgets():
            if isinstance(w, QtWidgets.QToolButton) and w.objectName() == 'undo-button':
                action = w.defaultAction()
                menu = action.menu()
                _sf_held.extend([w, action, menu])
                return [a.text() for a in menu.actions()] if menu is not None else []
        return []


    path = _sf_path()
    os.remove(path)  # the state saved first is kept aside by the check
    shown, undo = _sf_shown(), _sf_undo()
    _sf_save()
    print('SAVED=%s' % os.path.isfile(path))
    print('SAVE_SHOWED_NOTHING=%s' % (_sf_shown() == shown))
    spy = _event_signal(viewport, ('UpdateRequest',))
    try:
        _sf_menu('Scene', 'Reset Scene')
        # the load begun: the Scene menu checking no mesh, read as the trigger returns, as the set-up reads it
        # (REVIEW.md TST-903, TST-943); ended: one again
        print('LOAD_BEGAN=%s' % (not _sf_meshes()))
        print('RESET_SHOWED_NOTHING=%s' % (_sf_shown() == shown))
        print('LOADED=%s' % _until(lambda: bool(_sf_meshes()), SETTLE_LIMIT, [spy.fired]))
    finally:
        _unwatch(viewport, spy)
    print('LOAD_SHOWED_NOTHING=%s' % (_sf_shown() == shown))
    print('NO_UNDO_STEP=%s' % (bool(undo) and _sf_undo() == undo))
    home = os.environ.pop('CFFIXED_USER_HOME')  # as off macOS: no home of its own, nothing written in this job
    try:
        _sf_path()
        print('REFUSED_WITH_NO_HOME=False')
    except RuntimeError:
        print('REFUSED_WITH_NO_HOME=True')
    finally:
        os.environ['CFFIXED_USER_HOME'] = home
    print('PATH=%s' % path)
    print('HOME=%s' % os.environ.get('CFFIXED_USER_HOME', ''))
    print('VERSION=%s' % QtCore.QCoreApplication.applicationVersion())
    print('SHOWN=%s' % (shown,))""")
ENTRIES_SAID = (
    'SAVED',
    'SAVE_SHOWED_NOTHING',
    'RESET_SHOWED_NOTHING',
    'LOAD_BEGAN',
    'LOADED',
    'LOAD_SHOWED_NOTHING',
    'NO_UNDO_STEP',
    'REFUSED_WITH_NO_HOME',
)
# once the view has drawn, the AOV button's menu lists its actions (ROADMAP item 81): a load first draws it. The
# renderer, the Displacement toggle and the AOV are put back, unless the switch back to the renderer fails
VIEW_SETTINGS = dedent("""
    def _sf_displacement(want=None):
        dock = _3d_dock(_main_window())
        button = next(b for b in dock.findChildren(QtWidgets.QToolButton) if b.text() == 'Displacement')
        if want is not None and button.isChecked() != want:
            button.click()
        return button.isChecked()


    def _sf_renderer(name):  # waited for until the 3D panel's title names it
        _sf_menu('Renderer', name)
        dock = _3d_dock(_main_window())
        return _until(lambda: dock.windowTitle().endswith(' - ' + name), SETTLE_LIMIT, [dock.windowTitleChanged])


    _sf_load()
    aov, renderer, displacement = _sf_aov(), _sf_checked('Renderer'), _sf_displacement()
    try:
        print('AOV_SET=%s' % _sf_aov('Material roughness'))
        _sf_load()
        print('AOV_LOADED=%s' % _sf_aov())
        # the file as saved: the session's renderer and toggle then changed, and the file loaded again
        print('RENDERER_SAVED=%s' % renderer)
        print('DISPLACEMENT_SAVED=%s' % displacement)
        _sf_renderer('GPU Pathtracer')
        print('RENDERER_SET=%s' % _sf_checked('Renderer'))
        print('DISPLACEMENT_SET=%s' % _sf_displacement(not displacement))
        _sf_load()
        print('RENDERER_LOADED=%s' % _sf_checked('Renderer'))
        print('DISPLACEMENT_LOADED=%s' % _sf_displacement())
    finally:
        # kept's last load puts back the shadows and the environment as background, which the GPU Pathtracer changes
        renderer_back = _sf_renderer(renderer[0] if renderer else 'Rasterizer')
        print('PUT_BACK=%s' % (renderer_back and _sf_displacement(displacement) == displacement))
        _sf_aov(aov[0] if aov else 'Beauty')""")
VIEW_SETTINGS_SAID = (
    'AOV_SET',
    'AOV_LOADED',
    'RENDERER_SAVED',
    'DISPLACEMENT_SAVED',
    'RENDERER_SET',
    'DISPLACEMENT_SET',
    'RENDERER_LOADED',
    'DISPLACEMENT_LOADED',
    'PUT_BACK',
)

LIGHT_ON = r'(<name>Point Light 1</name>.*?<is_enabled>)false(</is_enabled>)'
# the scene's entities, the camera's kept: the environment's and the lights' left out
LIGHTS = r'(<entities>\s*<size>)\d+(</size>).*?(<_1 prefix="_">\s*<name>Default Camera</name>)'
CAMERA_ONLY = r'\g<1>1\2\n\t\t\t\t\3'


class Kept(NamedTuple):
    path: str  # the state file, where Designer writes it
    base: str  # the state saved first, its text


async def in_designer(ctx: Ctx, body: str) -> str:
    """Runs `body` in Designer after the helpers and STATE; its text."""
    return text(await ctx.c('execute_designer_code', {'code': ctx.helper_source + STATE + body}))


def printed(t: str, key: str) -> str | None:
    """The value printed on a line of its own as `key=value` in `t`; None when not printed."""
    found = re.search(r'^%s=(.*)$' % re.escape(key), t, re.M)
    return found.group(1).strip() if found else None


def pair(t: str, key: str) -> tuple[float, float]:
    """The two numbers printed as `key=1,2.5` in `t`; raises unless two are."""
    numbers = [float(v) for v in (printed(t, key) or '').split(',') if v]
    if len(numbers) != 2:
        raise RuntimeError('%s= printed %r, not two numbers' % (key, printed(t, key)))
    return numbers[0], numbers[1]


def backup(path: str) -> str:
    """The 3D shot's backup of the state file `path`: in its folder, Designer's version folder (scene3d.py)."""
    return os.path.join(os.path.dirname(path), state3d.STATE_BACKUP)


@contextlib.asynccontextmanager
async def kept(ctx: Ctx) -> AsyncIterator[Kept]:
    """The Designer's own state file and textures copied aside, then the current state saved (the base). At the end,
    the base and its textures are written back and loaded, then the file and folder found are put back, or removed
    when there were none, whatever the load did. Raises before anything is copied or written when Designer gives no
    state file in its own home (`_sf_path`; REVIEW.md TST-890), and at the end when the base didn't load back
    (TST-897)."""
    # STATE alone: _sf_path calls none of the helpers, and refuses a state file outside the Designer's own home
    t = text(await ctx.c('execute_designer_code', {'code': STATE + "print('PATH=' + _sf_path())"}))
    path = printed(t, 'PATH')
    if not path:
        raise RuntimeError('Designer gave no state file in its own home: %s' % t.strip()[-300:])
    aside = os.path.join(ctx.scratch, 'state_file_aside')
    shutil.rmtree(aside, ignore_errors=True)
    found, base = os.path.join(aside, 'found'), os.path.join(aside, 'base')
    # a 3D shot's backup left in the Designer's own home: a check's, which no other check meets (scene3d.py)
    shots = backup(path)
    shutil.rmtree(shots, ignore_errors=True)
    state3d._state_back_up(path, found)
    saved = await in_designer(ctx, '_sf_save()')
    if not os.path.isfile(path):
        raise RuntimeError('the state file was not saved: %s' % saved.strip()[-300:])
    state3d._state_back_up(path, base)
    try:
        yield Kept(path, state3d._state_text(path))
    finally:
        try:
            shutil.rmtree(shots, ignore_errors=True)
            state3d._state_put_back(base)
            loaded = await in_designer(ctx, '_sf_load()')
        finally:
            state3d._state_put_back(found)
        if printed(loaded, 'LOADED') != 'True':
            raise RuntimeError("the state saved first didn't load back: %s" % loaded.strip()[-300:])


def fields(content: str | ET.Element) -> dict[str, str]:
    """Each leaf element's text by its path, a repeated tag numbered from its second (`entities/_5/name`)."""
    out: dict[str, str] = {}

    def walk(element: ET.Element, at: str) -> None:
        children = list(element)
        if not children:
            out[at] = (element.text or '').strip()
        seen: dict[str, int] = {}
        for child in children:
            seen[child.tag] = seen.get(child.tag, 0) + 1
            walk(child, at + '/' + child.tag + ('' if seen[child.tag] == 1 else '#%d' % seen[child.tag]))

    walk(ET.fromstring(content) if isinstance(content, str) else content, '')
    return out


def _alike(a: str, b: str) -> bool:
    """The same text, its numbers within 1e-4 of each other, relative to the larger of 1 and the number: a camera loaded
    differs from the one written by float rounding (measured: 1e-7)."""
    if a == b:
        return True
    left, right = NUMBER.findall(a), NUMBER.findall(b)
    if not left or len(left) != len(right) or NUMBER.sub('#', a) != NUMBER.sub('#', b):
        return False
    return all(abs(float(x) - float(y)) <= 1e-4 * max(1.0, abs(float(x))) for x, y in zip(left, right, strict=True))


def differing(a: str, b: str) -> list[str]:
    """The paths of the fields two state files hold differently, or only one of them holds."""
    one, two = fields(a), fields(b)
    return [k for k in sorted(set(one) | set(two)) if k not in one or k not in two or not _alike(one[k], two[k])]


def edited(content: str, pattern: str, replacement: str) -> str:
    """`content` with the one match of `pattern` (a regex, `.` matching newlines too) replaced; raises unless it
    matches exactly once."""
    out, n = re.subn(pattern, replacement, content, flags=re.S)
    if n != 1:
        raise RuntimeError('%r matched %d times in the state file' % (pattern, n))
    return out


def not_loaded(changed: list[str], written: str, after: str, follows: str | None) -> list[str]:
    """The fields of `written` that the state saved after its load holds otherwise. Those matching `follows` are left
    out, but for the fields `changed` by the edit (REVIEW.md TST-889: the mesh's id follows the mesh)."""
    return [p for p in differing(written, after) if p in changed or not (follows and re.search(follows, p))]


def entity(content: str, name: str) -> dict[str, str]:
    """The fields of the scene's entity `name` (`Point Light 1`), by their path inside it; empty when there is none."""
    for item in ET.fromstring(content).findall('database/scene/entities/*'):
        if item.findtext('name') == name:
            return fields(item)
    return {}


class Edit(NamedTuple):
    """A field the set-up edits, edited alone in a state file."""

    name: str
    edit: Callable[[str], str]  # the state file's text to the text with the field edited; raises when it has none
    follows: str | None = None  # a regex of the paths of the fields that follow it in the state saved after the load


AIRPORT = 'sd-3dview-maps://airport.exr'  # Designer's airport map, as the file names it

ONE_FIELD = [
    Edit('environment rotation', lambda s: state3d._state_edited(s, {'rotation': 0.125})),
    Edit('environment exposure', lambda s: state3d._state_edited(s, {'exposure': 1.5})),
    Edit('tiling', lambda s: state3d._state_edited(s, {'tiling': 2.5}), r'/custom_uvs_tiling$'),
    # the map's four places (state3d.py)
    Edit(
        'environment map',
        lambda s: state3d._state_edited(s, {'environment': AIRPORT}),
        r'/material/parameters/(environment|panorama)$',
    ),
    Edit(
        'mesh',
        lambda s: state3d._state_edited(s, {'mesh': 'sphere'}),
        r'^/database/(scene/external_scenes|material_mapping_table|selection)/',
    ),
    Edit('camera', turned, r'/(near|far)_clip_plane$'),
]


# Override Material turned off, then the state saved, then loaded: the menu's entry at each, and whether the file saved
# holds it off (designer_helpers/scene3d.py, _overrides_back). The entry is there once a graph's outputs are on the mesh
OVERRIDE_LOADED = dedent("""
    print('OFF=%s' % _sf_override(False))
    _sf_save()
    print('SAVED_OFF=%s' % ('<override_existing_material>false</override_existing_material>' in _state_text(_sf_path())))
    _sf_load()
    print('OVERRIDDEN=%s' % _sf_override())""")
