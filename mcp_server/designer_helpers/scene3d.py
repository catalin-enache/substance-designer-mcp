"""The 3D view set up for screenshot_designer('3d') (ROADMAP items 73, 74 and 131): checked first (_3d_set_up), then
set up around the render and put back after it, through Designer's own state file (state3d.py reads and edits it).
The camera, the mesh, the tiling and the environment go through the file, in one load. A graph's outputs go through
the Explorer's menu (view3d.py). Measured on macOS in Designers an agent started (Designer 16.0.7, 2026-11-25 and
2026-11-26); the self-test's facts category checks what this relies on (lifecycle the Default State File), and
editor_panels_and_fit what a call does.

A call with set-up options (_SetUp.applied):
1. Puts back a backup an earlier call left, or removes one it can't put back, and says so (state3d._state_back_up).
2. Backs up the default state file and its textures' folder (state3d.STATE_BACKUP, in Designer's version folder).
3. Saves the session's state as the default (Scene > Save Current State As Default): the base, the user's view.
   Refused when the Save didn't write the file, which a Default State File changed in Project settings since Designer
   started gives (state3d._state_default_path).
4. Writes in the file each field the call sets that the base holds otherwise, then loads it once (Scene > Reset
   Scene): the mesh by its id, the camera, the tiling of the material the mesh uses, and the environment's map by its
   URL, its rotation in turns and its exposure. A new mesh is framed as the Scene menu frames it, from the camera's
   direction, then the camera options move the camera from there. A file lacking a field the call reads is refused
   before anything changes. With nothing to write, nothing is loaded.
5. Puts a graph's outputs on the mesh: `graph`'s, or after a load the editor's graph's, when the view showed a graph's.
   `graph`'s leave Override Material on, as the Explorer's menu turns it: the call asked for those outputs.
Then the shot renders. After it, a view the call changed gets the base back, the shot's look first as before each
step: written, loaded, then relinked as in 5, a failure of the look said on the put-back's own line. Last, the backup
is put back. An error runs these too. After an abort only the backup is put back, and the view can stay as the call
left it.

What it relies on:
- The default state file is `user_view3d_settings.sbsscn` in Qt's AppDataLocation, in a folder named after Designer's
  major and minor version (`16.0`), or the user's Default State File (state3d._state_default_path). Save writes it,
  and the textures of a graph whose outputs are on the mesh into the folder beside it. With no graph's outputs there,
  Save writes no folder, and deletes one there.
- Reset Scene reads the file once it has returned, in Designer's event loop. From then until the load has ended, the
  Scene menu checks no mesh. A Save before the load has ended saved a scene without its mesh. A mesh of the user's
  own, held by its file's URL (state3d.USERS_MESH), the menu checks none of, before the load or after it. For box.fbx,
  of Designer's own resources, which loads in under a second, the load's own restart of the view, then the view
  settled, ended its load: a Save then held the mesh (2026-11-26). Two cases are neither measured nor covered
  (REVIEW.md HLP-289):
  - a slower import, which may outlast the view's restart: the wait may end before the load does;
  - the Rasterizer's accumulation antialiasing off, where the watch may see no restart (frames3d.py's module
    docstring): the wait may run to SETTLE_LIMIT, and the set-up then says the view hadn't settled.
  Covering them would take a signal of the import's end. The user called meshes of their own very unlikely
  (2026-11-25).
- Each load glides the camera from Designer's default pose to the file's, about 0.5 s, or jumps there. The view's
  sample count holds at its restart while the camera moves, and rises once it stops: waited for to the count at rest
  (_Frames.settled), 8 of 8 loads ended at the file's pose.
- After a load the view no longer follows the graph: a Save then writes no textures and deletes their folder. The
  Explorer's "View Outputs In 3D View" puts a graph's outputs on the mesh again (view3d.py). The graph the view showed
  can't be told, so the editor's graph is relinked. A graph with one output makes Designer ask which of the material's
  47 channels to show it in. A Return with no channel active did nothing (1 try), so such a graph isn't relinked, and
  the result says so.
- A load puts the AOV back to Beauty, so a call sets it back after each load. It keeps the renderer and the
  Displacement toggle. The AOV's menu lists its entries once the view has drawn on screen.
- A load turns each material's Materials > Override Material on, though the file holds it off, so a call sets it back
  after each load too. The entry is there once a graph's outputs are on the mesh. Of the 47 checkable entries of the
  3D view's menus and toolbars, the meshes, the AOVs and the renderers left out, it was the only one a load didn't
  keep (2026-11-26, a runner's probe; REVIEW.md HLP-267). The Explorer's "View Outputs In 3D View" turns it on too, so
  a call sets it back again after each relink (2026-11-26, a runner's probe; REVIEW.md HLP-291).
- Frame looks at the middle of the mesh from a distance that depends on the mesh and the viewport's aspect only
  (state3d.FRAMING). The Scene menu's switch frames the new mesh so too, the camera's direction kept, while a load of
  another mesh's id keeps the file's camera: the set-up writes the camera framed with the mesh. Measured with
  Designer's default lens: another lens wasn't.
"""

from .core import (
    APIException,
    Callable,
    Iterator,
    Kept,
    NamedTuple,
    QtCore,
    QtGui,
    QtWidgets,
    SDSBSCompGraph,
    Sequence,
    _current_graph,
    _main_window,
    _menu,
    _qt_app,
    cast,
    contextlib,
    os,
)
from .frames3d import SETTLE_LIMIT, _Frames, _viewport, _Waiting
from .screenshots import _3d_dock
from .state3d import (
    _PLACES,
    FRAMING,
    STATE_BACKUP,
    Pose,
    StateField,
    StateFields,
    _camera_moved,
    _framed,
    _mesh_listed,
    _reframed,
    _state_back_up,
    _state_changes,
    _state_default_path,
    _state_edited,
    _state_fields,
    _state_put_back,
    _state_resources,
    _state_text,
    _state_write,
)
from .view3d import (
    SETTING,
    _apply_outputs,
    _environment_maps,
    _explorer_tree,
    _material_checked,
    _menu_action,
    _set_up_checked,
)

SAVE = 'Save Current State As Default'
RESET = 'Reset Scene'
AOV = '3dview.display.aov'  # the 3D view's AOV button's object name
AOV_LOADED = 'Beauty'  # the AOV a load shows (the module docstring)
# how close two poses are, the camera unchanged: angles in degrees, lengths relative to the distance. Designer saves its
# own camera off by up to about 3e-6 degrees (its Default view at yaw 45.0000024: REVIEW.md HLP-265), as
# state3d.CAMERA_LEVEL takes its X level
SAME_POSE = 1e-4
OVERRIDE = 'Override Material'  # each material's entry of the Materials menu, once a graph's outputs are on the mesh
SAID = '3D view: '


def _version_folder() -> str:
    """Designer's version folder: its major and minor version, in Qt's AppDataLocation."""
    base = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.AppDataLocation)
    return os.path.join(base, '.'.join(QtCore.QCoreApplication.applicationVersion().split('.')[:2]))


def _scene_checked(bar: QtWidgets.QMenuBar, keep: list[Kept]) -> set[str]:
    """The entries the 3D view's Scene menu checks: the mesh shown, among others."""
    menu = _menu(_menu_action(bar, keep, 'Scene'))
    keep.append(menu)
    menu.aboutToShow.emit()
    return {a.text() for a in menu.actions() if a.isCheckable() and a.isChecked()}


def _state_save(bar: QtWidgets.QMenuBar, keep: list[Kept]) -> None:
    """Scene > Save Current State As Default: the session's state written as the default state file."""
    _menu_action(bar, keep, 'Scene', SAVE).trigger()


def _state_saved(bar: QtWidgets.QMenuBar, keep: list[Kept], path: str) -> str:
    """The session's state saved (_state_save), the text of `path` returned. Raises unless the Save wrote `path`:
    Designer saves the Default State File it started with, so one changed in Project settings since takes a restart
    (REVIEW.md HLP-268)."""
    before = _modified(path)
    _state_save(bar, keep)
    if _modified(path) in (None, before):
        raise RuntimeError(
            "Scene > %s didn't write %s, the 3D view's default state file: Designer saves the Default State File it "
            'started with, so a Default State File changed in Project settings since takes a restart of Designer. '
            "The file Designer started with now holds the session's state" % (SAVE, path)  # REVIEW.md HLP-274
        )
    return _state_text(path)


def _modified(path: str) -> int | None:
    """When the file at `path` was last written, in ns; None when there is none."""
    try:
        return os.stat(path).st_mtime_ns
    except FileNotFoundError:
        return None


def _state_load(bar: QtWidgets.QMenuBar, keep: list[Kept], watched: _Frames, listed: bool = True) -> Callable[[], bool]:
    """Reset Scene, the state file loaded. Returns the wait for the load, run once the change is recorded: the load's
    end, a mesh checked in the Scene menu again, then the view settled (_Frames.settled), each SETTLE_LIMIT at most, a
    safety net. The count holds at its restart while the camera glides, so the view settles once the camera has
    stopped and the view has drawn it. The wait returns whether both ended within their limit. The entries checked as
    Reset Scene returns (Display UVs in 2D View, for one) aren't the mesh's. `listed`: whether the file's mesh is one
    the Scene menu lists. One of the user's own the menu checks none of, so the load's own restart of the view, up to
    SETTLE_LIMIT, stands for its end, within what the module docstring measured (REVIEW.md HLP-286, HLP-289)."""
    since = watched.mark()
    _menu_action(bar, keep, 'Scene', RESET).trigger()
    during = _scene_checked(bar, keep)

    def wait() -> bool:
        if listed:
            ended = watched.until(lambda: bool(_scene_checked(bar, keep) - during), SETTLE_LIMIT)
        else:
            ended = watched.restarted(since)
        return watched.settled(since) and ended

    return wait


def _aov_menu(dock: QtWidgets.QDockWidget, keep: list[Kept]) -> QtWidgets.QMenu | None:
    """The 3D view's AOV menu, filled; None when its toolbar has no AOV button."""
    buttons = [b for b in dock.findChildren(QtWidgets.QToolButton) if b.objectName() == AOV]
    if not buttons:
        return None
    menu = buttons[0].menu() or _menu(buttons[0].defaultAction())
    keep += [buttons[0], menu]
    menu.aboutToShow.emit()
    _qt_app().processEvents()
    return menu


def _aov_shown(dock: QtWidgets.QDockWidget, keep: list[Kept]) -> str | None:
    """The AOV the 3D view shows; None when its menu lists none, the view not drawn yet."""
    menu = _aov_menu(dock, keep)
    checked = [a.text() for a in menu.actions() if a.isChecked()] if menu is not None else []
    return checked[0] if checked else None


def _aov_back(dock: QtWidgets.QDockWidget, keep: list[Kept], aov: str | None, watched: _Frames) -> bool:
    """The AOV `aov` shown again after a load put it back to Beauty (AOV_LOADED), waited for on `watched`; nothing
    when it is shown, or `aov` is None. Returns whether the view settled after it, True with nothing to wait for
    (REVIEW.md HLP-292)."""
    menu = _aov_menu(dock, keep) if aov not in (None, AOV_LOADED) else None
    for action in menu.actions() if menu is not None else []:
        if action.text() == aov and not action.isChecked():
            with _Waiting(watched) as waiting:
                action.trigger()
            return waiting.settled
    return True


def _overrides(bar: QtWidgets.QMenuBar, keep: list[Kept]) -> list[QtGui.QAction]:
    """Each material's Override Material entry in the 3D view's Materials menu, in the menu's order: none seen before a
    graph's outputs were on the mesh."""
    menu = _menu(_menu_action(bar, keep, 'Materials'))
    keep.append(menu)
    menu.aboutToShow.emit()
    _qt_app().processEvents()
    found: list[QtGui.QAction] = []
    for action in menu.actions():
        submenu = cast(QtWidgets.QMenu | None, action.menu())  # a QMenu, or None: PySide's stubs say QObject
        if submenu is None:
            continue
        keep += [action, submenu]
        submenu.aboutToShow.emit()
        _qt_app().processEvents()
        found += [a for a in submenu.actions() if a.isCheckable() and a.text().replace('&', '') == OVERRIDE]
    keep += found
    return found


def _overrides_back(bar: QtWidgets.QMenuBar, keep: list[Kept], overridden: list[bool], watched: _Frames) -> bool:
    """Each material's Override Material set back to `overridden` after a load or a relink turned it on (the module
    docstring), in the Materials menu's order, each change waited for on `watched`; nothing when each is on. Returns
    whether the view settled after each, True with nothing to wait for (REVIEW.md HLP-292)."""
    settled = True
    if all(overridden):
        return settled
    for action, on in zip(_overrides(bar, keep), overridden, strict=False):  # a mesh switched may have others
        if action.isChecked() != on:
            with _Waiting(watched) as waiting:
                action.trigger()
            settled = waiting.settled and settled
    return settled


def _relinked(tree: QtWidgets.QTreeView | None, keep: list[Kept]) -> str:
    """The editor's graph's outputs put on the mesh again after a load (the module docstring): '' once they are,
    else what the set-up says: why not, in brackets."""
    g = _current_graph()
    if not isinstance(g, SDSBSCompGraph):
        why = 'no graph is open in the editor'
    # the Explorer's menu takes a graph with no outputs, and puts nothing on the mesh (HLP-282)
    elif not (outputs := len(g.getOutputNodes())):
        why = 'graph %s in the editor has no outputs to show' % g.getIdentifier()
    elif outputs == 1:
        why = (
            'graph %s in the editor has one output: Designer would ask which channel of the material to show it in'
            % g.getIdentifier()
        )
    elif tree is None:
        why = "graph %s in the editor: the Explorer panel isn't visible (Windows > Explorer)" % g.getIdentifier()
    else:
        try:
            _apply_outputs(tree, g, keep)
            return ''
        except (Exception, APIException) as e:  # the sd API's error is a BaseException too
            why = 'graph %s in the editor: %s' % (g.getIdentifier(), e)
    # the view followed the graph it showed, which may not be the editor's (REVIEW.md HLP-288)
    return ' (it no longer follows the graph it showed: %s)' % why


WAYS = (('right', 'left'), ('up', 'down'))  # [right, up]'s values said, positive and negative


def _directions(values: tuple[float, float], unit: str) -> str:
    """[right, up] said, each value that isn't 0 with its direction, to 3 digits, `unit` after the first value:
    '90 degrees right, 30.1 up'."""
    said: list[str] = []
    for value, ways in zip(values, WAYS, strict=True):
        if value:
            said.append('%.3g%s %s' % (abs(value), '' if said else unit, ways[value < 0]))
    return ', '.join(said)


def _camera_said(view: str | None, orbit: tuple[float, float], pan: tuple[float, float], zoom: int) -> str:
    """The camera's options, as said: 'view Top, framed, orbit 30 degrees right, +2 zoom steps'."""
    said = ['view %s, framed' % view] if view is not None else []
    said += ['orbit ' + _directions(orbit, ' degrees')] if any(orbit) else []
    said += ['pan ' + _directions(pan, ' of the view')] if any(pan) else []
    said += ['%+d zoom steps' % zoom] if zoom else []
    return ', '.join(said)


def _environment_said(name: str | None, rotation: float | None, exposure: float | None) -> str:
    """The environment set, as said: 'environment studio, rotation 90 degrees, exposure 1', with what is given."""
    said = [name] if name is not None else []
    said += ['rotation %g degrees' % rotation] if rotation is not None else []
    said += ['exposure %g' % exposure] if exposure is not None else []
    return 'environment ' + ', '.join(said)


def _unsettled(settled: bool, watched: _Frames) -> str:
    """What a set-up step adds to what it says when its wait for the 3D view ended at its limit, not on the view at
    rest: the render may be of a view still drawing (REVIEW.md HLP-214), and what may hold its count below 8
    (`watched`'s below_rest; REVIEW.md HLP-215). '' when the wait ended on the view."""
    if settled:
        return ''
    return " (the 3D view hadn't settled within %g s after it%s)" % (SETTLE_LIMIT, watched.below_rest())


def _same_pose(a: Pose, b: Pose) -> bool:
    """Whether two poses are one: the camera unchanged."""
    near = SAME_POSE * max(1.0, a.distance)
    return (
        abs((a.yaw - b.yaw + 180.0) % 360.0 - 180.0) <= SAME_POSE  # across the turn: Back near 180 or -180 (HLP-273)
        and abs(a.pitch - b.pitch) <= SAME_POSE
        and abs(a.distance - b.distance) <= near
        and all(abs(x - y) <= near for x, y in zip(a.target, b.target, strict=True))
    )


class _SetUp(NamedTuple):
    """A set-up _3d_set_up checked: `applied(between, watched)` sets it up around the render, then puts it back
    (_3d_set_up). `may_change`: whether it may change what the view shows, known before it runs (the camera, the mesh
    switched, the tiling or the light given), so a 3D shot takes a render before it to compare with (shot3d.py)."""

    applied: Callable[[Callable[[], None] | None, _Frames], contextlib.AbstractContextManager[bool]]
    may_change: bool


def _3d_set_up(
    graph: str | None = None,
    mesh: str | None = None,
    view: str | None = None,
    zoom: int = 0,
    tiling: float | None = None,
    orbit: Sequence[float] | None = None,
    pan: Sequence[float] | None = None,
    environment: str | None = None,
    environment_rotation: float | None = None,
    environment_exposure: float | None = None,
) -> _SetUp:
    """The 3D view's set-up checked, changing nothing: what the arguments rule out, the graph, the panel and the menu
    entries it needs, a mesh using several materials with `tiling` (view3d._material_checked), and the state file's
    path; refused here (shoot_3d calls it before it puts Designer's window on screen: REVIEW.md HLP-127). Returns it,
    to run around the render (_SetUp.applied, the module docstring's steps).
    In one load of the state file: the mesh (view3d.MESHES), framed as the Scene menu frames it; the camera at `view`
    (state3d.VIEW_DIRECTIONS, framed), then turned `orbit` [right, up] degrees around the point it looks at, moved
    `pan` [right, up] fractions of the view sideways and `zoom` steps closer (negative: away), from the user's view or
    the framing; the material's tiling; the environment: one of Designer's maps (view3d._environment_maps), its
    rotation in degrees and its exposure. Then `graph`'s outputs on the mesh.

    It prints '3D view, setting: <step>' before each change, so an abort leaves the steps it began said, and an error
    after a change says what was set. Then it prints '3D view: ...' lines: a backup put back or removed first, what it
    set, and once the view is put back, that it was, with a graph not relinked. `between` runs before each step: the 3D
    shot's look, which puts Designer's window on screen again if it went off (shot3d.py; REVIEW.md HLP-136). Each step
    waits for the 3D view to take it on `watched`, the shot's watch of its frames (frames3d.py; REVIEW.md HLP-148)."""
    g = _set_up_checked(graph, mesh, view, environment)
    lit = environment is not None or environment_rotation is not None or environment_exposure is not None
    turn = (float(orbit[0]), float(orbit[1])) if orbit else (0.0, 0.0)
    move = (float(pan[0]), float(pan[1])) if pan else (0.0, 0.0)
    camera = view is not None or any(turn) or any(move) or bool(zoom)
    folder = _version_folder()
    path, aside = _state_default_path(folder), os.path.join(folder, STATE_BACKUP)
    mw = _main_window()
    keep: list[Kept] = [mw]
    dock = _3d_dock(mw)  # refused unless it has its menu bar
    bar = dock.findChildren(QtWidgets.QMenuBar)[0]
    viewport = _viewport(dock)  # refused when there is none
    keep += [dock, bar, viewport]
    # the Explorer's tree: graph= goes through it, refused when the Explorer isn't visible; a relink too, if it shows
    tree: QtWidgets.QTreeView | None = None
    try:
        tree = _explorer_tree(mw, keep)
    except RuntimeError:
        if g is not None:
            raise
    # the Materials menu: each set-up reads its Override Material entries (_overrides; REVIEW.md HLP-276)
    for entry in (('Scene', SAVE), ('Scene', RESET), ('Materials',)):
        _menu_action(bar, keep, *entry)  # there; looked up again as it is used
    # the fields asked, as the state file holds them: the mesh by its id, unless the Scene menu checks it as shown
    # already, the map by its URL, the rotation in turns
    asked = StateFields()
    if mesh is not None and not _menu_action(bar, keep, 'Scene', mesh).isChecked():
        asked['mesh'] = FRAMING[mesh][0]
    if tiling is not None:
        # refused for a mesh using several materials; with a new mesh, the new one's, one each (REVIEW.md HLP-114,
        # HLP-127)
        if 'mesh' not in asked:
            _material_checked(bar, keep)
        asked['tiling'] = tiling
    if environment is not None:
        asked['environment'] = _environment_maps()[environment]
    if environment_rotation is not None:
        asked['rotation'] = environment_rotation / 360.0
    if environment_exposure is not None:
        asked['exposure'] = environment_exposure
    writes_camera = camera or 'mesh' in asked  # moved, or framed for a new mesh
    reads: list[StateField] = [n for n in _PLACES if n in asked or (writes_camera and n in ('camera', 'mesh'))]
    # each option set through the state file, as said
    said = [mesh] if mesh is not None else []
    said += [_camera_said(view, turn, move, zoom)] if camera else []
    said += ['tiling %g' % tiling] if tiling is not None else []
    said += [_environment_said(environment, environment_rotation, environment_exposure)] if lit else []

    @contextlib.contextmanager
    def applied(between: Callable[[], None] | None, watched: _Frames) -> Iterator[bool]:
        """The set-up's steps, then the render (the `with` block), then the view put back: the module docstring.
        Yields whether the steps changed what the view shows: a field written that the base held otherwise, the camera
        moved or the mesh switched included. A graph may be what is shown already, so it doesn't count (shoot_3d's
        retakes)."""
        done: list[str] = []
        touched = False  # the session's view changed: the base loaded back after
        base, linked, aov = '', False, None  # the user's state, whether it showed a graph's outputs, and its AOV
        overridden: list[bool] = []  # each material's Override Material, as the user had it

        def begin(step: str, changing: bool = True) -> str:
            """Says the step before its change: no abort can land between a change and its record (REVIEW.md
            HLP-119). `between` runs first. `changing`: whether the step may change the view, which then gets the base
            back after the render."""
            nonlocal touched
            if between is not None:
                between()
            print(SETTING + step)
            touched = touched or changing
            return step

        def loading(content: str) -> Callable[[], bool]:
            """`content` written as the state file, then loaded (_state_load). Returns the load's wait, which then
            shows the user's AOV and Override Material again: a load puts the AOV back to Beauty, and turns Override
            Material on. The wait returns whether the view settled after the load and after each of these."""
            listed = _mesh_listed(content)  # REVIEW.md HLP-283, HLP-287
            _state_write(path, content)
            loaded = _state_load(bar, keep, watched, listed)

            def wait() -> bool:
                settled = loaded()
                shown = _aov_back(dock, keep, aov, watched)
                set_back = _overrides_back(bar, keep, overridden, watched)
                return settled and shown and set_back  # each wait said (REVIEW.md HLP-292)

            return wait

        def relinked() -> str:
            """The editor's graph relinked (_relinked), then Override Material set back, which the relink turns on (the
            module docstring; REVIEW.md HLP-291). Returns what _relinked says."""
            unlinked = _relinked(tree, keep)
            if not unlinked:
                _overrides_back(bar, keep, overridden, watched)
            return unlinked

        def put_back() -> None:
            """The view put back, if the call changed it: the shot's look first, then the base written and loaded, the
            AOV set back, the editor's graph relinked and Override Material set back after it, said on the put-back's
            own line, with a failure of the look.
            Then the backup put back, whatever happened before."""
            try:
                if touched:
                    looked = ''
                    try:  # the shot's look first, as before each step (REVIEW.md HLP-264)
                        if between is not None:
                            between()
                    except (Exception, APIException) as e:  # said, the user's view loaded all the same (HLP-272)
                        looked = ' (the look before it failed: %s)' % e
                    print(SETTING + 'the 3D view as it was')
                    settled = loading(base)()
                    unlinked = relinked() if linked else ''
                    print(SAID + 'put back as it was' + _unsettled(settled, watched) + unlinked + looked)
            finally:
                _state_put_back(aside)

        leftover = _state_back_up(path, aside)
        if leftover is not None:
            print(SAID + leftover)
        try:
            try:
                base = _state_saved(bar, keep, path)
                linked = os.path.isdir(_state_resources(path))  # Save writes textures only for a graph on the mesh
                held = _state_fields(base, reads)  # a file lacking a field read is refused before anything changes
                aov = _aov_shown(dock, keep)
                overridden = [action.isChecked() for action in _overrides(bar, keep)]
                changes = _state_changes(held, asked)  # the fields written: those the user's view holds otherwise
                if writes_camera:
                    size = (float(viewport.width()), float(viewport.height()))
                    start = held['camera']
                    shown = asked.get('mesh', held['mesh'])
                    if view is not None:
                        at = _framed(shown, view, size)
                    elif 'mesh' in asked:  # framed as the Scene menu's switch frames it (the module docstring)
                        at = _reframed(start, shown, size)
                    else:
                        at = start
                    at = _camera_moved(at, size, turn, move, zoom)
                    if not _same_pose(at, start):
                        changes['camera'] = at
                load_settled = True  # the load's wait, said once with the relink's (REVIEW.md HLP-292)
                if said:
                    step = begin(', '.join(said), bool(changes))
                    # one shown already restarts nothing, and the wait would run to its limit (REVIEW.md HLP-195)
                    loaded = loading(_state_edited(base, changes)) if changes else None
                    done.append(step)  # before its wait: an error there says the step was set (REVIEW.md HLP-200)
                    if loaded is not None:
                        load_settled = loaded()
                        done[-1] += _unsettled(load_settled, watched)
                if g is not None:
                    step = begin("graph %s's outputs on the mesh" % g.getIdentifier())
                    with _Waiting(watched) as waiting:
                        g.compute()  # its outputs ready for the mesh
                        _apply_outputs(cast(QtWidgets.QTreeView, tree), g, keep)  # found above, as g was given
                        done.append(step)  # before its wait (REVIEW.md HLP-200)
                    done[-1] += _unsettled(waiting.settled, watched)
                elif changes and linked:  # after the load: the shot shows the outputs, not their textures' copies
                    with _Waiting(watched) as waiting:
                        unlinked = relinked()
                        waiting.needed = not unlinked  # not relinked: nothing changed, so no restart to wait for
                    done[-1] += unlinked
                    if load_settled:  # said once: a load that hadn't settled said so
                        done[-1] += _unsettled(waiting.settled, watched)
                print(SAID + ', '.join(done))
            except (Exception, APIException) as e:  # the sd API's error is a BaseException too
                if not done:
                    raise
                raise RuntimeError('%s; the 3D view was already set: %s' % (e, ', '.join(done))) from e
            yield bool(changes)
        except (Exception, APIException) as e:
            try:
                put_back()
            except (Exception, APIException) as back:  # said after the error that came first, not in its place
                raise RuntimeError('%s; and putting the 3D view back failed: %s' % (e, back)) from back
            raise
        except BaseException:  # an abort: the backup put back, the view left as it is (the module docstring)
            _state_put_back(aside)
            raise
        put_back()

    return _SetUp(applied, camera or bool(asked))
