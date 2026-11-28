"""The 3D view set up for screenshot_designer('3d') (ROADMAP items 73, 74, 84, 88 and 131): checked first (_3d_set_up),
then set up around the render and put back after it, through Designer's own state file (state3d.py reads and edits
it). The camera, the mesh, the tiling, the environment and the shader model go through the file, in one load or
two (step 4). A
graph's outputs go through the Explorer's menu (view3d.py). Measured on macOS in Designers an agent started (Designer
16.0.7, 2026-11-25 and 2026-11-26); the self-test's facts category checks what this relies on (lifecycle the Default
State File), and editor_panels_and_fit what a call does.

A call with set-up options (_SetUp.applied):
1. Puts back a backup an earlier call left, or removes one it can't put back, and says so (state3d._state_back_up).
2. Backs up the default state file and its textures' folder (state3d.STATE_BACKUP, in Designer's version folder).
3. Saves the session's state as the default (Scene > Save Current State As Default): the base, the user's view.
   Refused when the Save didn't write the file, which a Default State File changed in Project settings since Designer
   started gives (state3d._state_default_path).
4. Writes in the file each field the call sets that the base holds otherwise, then loads it once (Scene > Reset
   Scene): the mesh by its id, a mesh file of the user's own by its URL (state3d.USERS_MESH), the camera, the tiling
   and the shader model of the material the mesh uses, and the environment's map by its URL, its rotation in turns and
   its exposure. A mesh of the Scene menu's uses its own material, Default, also new over a mesh file's base
   (state3d._used_material). A mesh file uses one of those the Materials menu lists in use (_in_use), as a load keeps an
   earlier mesh file's entries in the file's table (REVIEW.md HLP-322). A tiling or a shader model is written with the
   material the mesh uses held overridden: a load set Default's model only so, and the render shows a tiling or a model
   only with Override on (below). When the file held that material's Override Material off, they are written so even if
   the material holds them already, the render has Override on, the result says so (SHOWN_ON), and the put-back gives
   the user's view back (the user, 2026-11-27: "Render with Override on", then "Same as shader_model" for the tiling;
   REVIEW.md HLP-318, HLP-321). A new mesh of the Scene menu's is framed as the menu frames it, from the camera's
   direction, then the camera options move the camera from there. A file lacking a field the call reads is refused
   before anything changes. With nothing to write, nothing is loaded.
   A mesh file the base doesn't hold is loaded with the other fields, the camera and the material's fields aside. Then
   Designer's own Camera > Frame frames it, from the camera's direction. When camera options or the material's fields
   are given, a Save then gives Frame's pose and the material the file's import mapped. The camera options move the
   camera from that pose, `view` turning it first. They and the material's fields that differ from the Save, and a
   tiling or a shader model asked of a material held not overridden, are written and loaded in a second load, none when
   there is nothing. A file mapping several materials is refused only then, its materials not known before (the lead,
   2026-11-27). A `view` on a mesh file the base holds takes Frame and the second load, with a first load only for the
   light.
5. Puts a graph's outputs on the mesh: `graph`'s, on every material of a mesh of several (the user, 2026-11-27); or
   after a load the editor's graph's, when the view showed a graph's, on the materials that showed them in the base
   (state3d._materials_linked; on another mesh, every one: view3d._materials_wanted). `graph`'s leave Override
   Material on, as the Explorer's menu turns it: the call asked for those outputs.
Then the shot renders. After it, a view the call changed gets the base back, the shot's look first as before each
step: written, loaded, then relinked as in 5, a failure of the look said on the put-back's own line. Last, the backup
is put back. An error runs these too. After an abort only the backup is put back, and the view can stay as the call
left it.

The 3D view as text (_3d_shown, screenshot_designer's as_text; ROADMAP item 85) reads what a set-up reads to skip the
values shown already: the mesh the Scene menu checks (_mesh_shown), and the fields of a Save, the file backed up first
and put back after, as in steps 1 to 3. It loads nothing and leaves Designer's window as it is. It also reads the
renderer from the 3D panel's title, the AOV and the Override Material of each material the mesh uses (_shown_said).

What it relies on:
- The default state file is `user_view3d_settings.sbsscn` in Qt's AppDataLocation, in a folder named after Designer's
  major and minor version (`16.0`), or the user's Default State File (state3d._state_default_path). Save writes it,
  and the textures of a graph whose outputs are on the mesh into the folder beside it. With no graph's outputs there,
  Save writes no folder, and deletes one there.
- Reset Scene reads the file once it has returned, in Designer's event loop. From then until the load has ended, the
  Scene menu checks no mesh. A Save before the load has ended saved a scene without its mesh, and the scene then ended
  at Designer's defaults. A mesh file of the user's own, held by its URL (state3d.USERS_MESH), the menu checks none
  of, before the load or after it. Its import ends later than the view's restart and settle: the Samba FBX's, 3.5 MB,
  took 1.7 to 7.1 s, where the view had restarted by 0.25 s and settled by 0.3 s, and a Save then held no mesh
  (2026-11-27, REVIEW.md HLP-289). A load of the same file, the camera alone changed, imports it again. What marks the
  end (facts' check of a mesh file's import, on the project's OBJ, box.fbx and the Samba FBX): as Reset Scene returns,
  the Materials menu lists no material in use, only Default as unused; once the import has ended it lists the file's
  own, and a Save then holds the mesh. In two probes, 8 loads of those files from another mesh or from themselves, a
  wait looking at the view's paints alone, with no tick, saw that end each time: the view paints as the import ends.
  The 3D panel's title named the new file as its import ended, but stayed as it was for a load of the same file, so
  it marks no end there.
- A mesh file Designer can't import (random bytes as an .fbx, a broken .obj; once each, 2026-11-27) opens no dialog
  and no window. The log says "Scene import failed", the view shows nothing, the title keeps the mesh before, the
  Materials menu lists no material in use, and a Save holds no mesh. A load of one waits IMPORT_LIMIT, then says that
  the mesh file didn't import (UNIMPORTED), and with no mesh to work on, no Frame, second load, graph step or relink
  follow (REVIEW.md HLP-299, HLP-307). A shot given the .fbx took 35 s, and put the view back (once, 2026-11-27).
- Each load glides the camera from Designer's default pose to the file's, about 0.5 s, or jumps there. The view's
  sample count holds at its restart while the camera moves, and rises once it stops: waited for to the count at rest
  (_Frames.settled), 8 of 8 loads ended at the file's pose.
- After a load the view no longer follows the graph: a Save then writes no textures and deletes their folder. The
  Explorer's "View Outputs In 3D View" puts a graph's outputs on the mesh again (view3d.py), the material's shader
  model kept (2026-11-27, facts' check of the models). The graph the view showed
  can't be told, so the editor's graph is relinked. On a mesh of several materials, on those that showed outputs in
  the base: the ones whose textures its Save named, as the file's `override_existing_material` doesn't tell them
  (state3d.py; facts' check of graph= on mesh files, its relink). A graph with one output makes Designer ask which of the material's
  47 channels to show it in. A Return with no channel active did nothing (1 try), so such a graph isn't relinked, and
  the result says so.
- A load set the shader model of the material the mesh uses as follows (probes on the Plane and on a one-material
  OBJ, 2026-11-27, and a runner's on the Rounded Cube and the Plane; REVIEW.md HLP-316):
  - Default, the material of a mesh of the Scene menu's, only with the file holding it overridden
    (`override_existing_material` true). Held not overridden, the Plane loaded over the project's OBJ's state kept
    OpenPBR Surface, its tiling taken, and so did the Plane with Default's Override off, also with Override turned on
    in the menu before the load. Held overridden, one load took it: on the Plane, its Override off before; on the
    Sphere switched to; on the Plane loaded over the OBJ's state;
  - a mesh file's own material, its Override off, took it held not overridden too (a one-material OBJ's; a runner's
    in framed's second load);
  - with the material's Override Material off, the render was a plain shot's, 0.0 grey levels apart on average, the
    model held all the same. With it on, the render was 5.9 grey levels from the plain shot on average on the Plane,
    where AdobeStandardMaterial and OpenPBR Surface came 0.05 apart, and 25 on the one-material OBJ, where they came
    65.6 apart;
  - a tiling, with Default's Override off: tiling 4 was held, the render a plain shot's; with it on, 5.8 grey levels
    from it on average, on the Plane with a gradient's outputs (a runner's probe, REVIEW.md HLP-321).
  Facts' checks of a Scene menu's mesh shot over a mesh file's view and of a model or a tiling on a material with
  Override off pin that a model or a tiling written held overridden was held at the render, and that the render was
  over 1 grey level from a plain shot; the rest was measured by probes, not checked.
- A load puts the AOV back to Beauty, so a call sets it back after each load. It keeps the renderer and the
  Displacement toggle. The AOV's menu lists its entries once the view has drawn on screen.
- A load turns each material's Materials > Override Material on, though the file holds it off, so a call sets it back
  after each load too. The entry is there once a graph's outputs are on the mesh. Of the 47 checkable entries of the
  3D view's menus and toolbars, the meshes, the AOVs and the renderers left out, it was the only one a load didn't
  keep (2026-11-26, a runner's probe; REVIEW.md HLP-267). The Explorer's "View Outputs In 3D View" turns it on too, so
  a call sets it back again after each relink (2026-11-26, a runner's probe; REVIEW.md HLP-291). Those were measured
  on a mesh of the Scene menu's. A mesh file's materials list the entry with no graph's outputs too, and a load of the
  project's OBJ kept each as the file held it (probes, 2026-11-27). The menu listed no entry for Default on the Rounded
  Cube as Designer starts, the file holding it on, nor under the OBJ, the file holding it off; a Scene menu switch from
  the Plane, Default off, to the Cube turned it on in both (a runner's probe, 2026-11-27).
- The Materials menu listed the materials whose Override Material is on first, then the others (probes on the
  project's OBJ, 2026-11-27), so its order follows them: a call sets each back by the material's name (_overrides).
  Set back in the menu's order, the Plane loaded over the OBJ's state took `first`'s off on its Default, which then
  didn't show its shader model (facts' check of a Scene menu's mesh shot over a mesh file's view; REVIEW.md HLP-311,
  HLP-315).
- Frame looks at the middle of the mesh from a distance that depends on the mesh and the viewport's aspect only
  (state3d.FRAMING). The Scene menu's switch frames the new mesh so too, the camera's direction kept, while a load of
  another mesh's id keeps the file's camera: the set-up writes the camera framed with the mesh. Measured with
  Designer's default lens: another lens wasn't. Camera > Frame triggered from code after a mesh file's load frames it
  the same way: the project's OBJ, ten times the Cube, at ten times the Cube's point and distance, from the camera's
  direction and from Top (2026-11-27, facts' check of Frame on a mesh file). A Save once the view settled holds the
  framed camera.
- The 3D panel's title is `<mesh> - <renderer>`. The mesh is the Scene menu's name of it, or for a mesh of the
  user's own its file's name without the extension (`box` for Designer's box.fbx). The renderer is the one the
  Renderer menu checks: Rasterizer, GPU Pathtracer or OpenGL (2026-11-27, facts' check of the title).
- A Save made with Designer hidden holds the camera as the view last drew it on screen, so the 3D view as text doesn't
  put the window on screen (2026-11-27, facts' check of a known view: a load settled on screen, then Designer hidden).
  Minimized, or covered by a window of Designer's own, as_text read the same: the first six lines of a known state
  loaded and settled on screen, the window left as it was (one runner's probe, two runs each, 2026-11-27, not
  checked). A camera still moving with Designer hidden, a Save holds partway, measured once each on 2026-11-27:
  - a load made with Designer hidden, saved as it ended, held yaw 50.2 and distance 177.5 of the file's 75 and 161.0;
  - a drag of 40 pixels made hidden moved the point looked at 14.24 units at once, 14.30 once Designer's events had
    run, and 14.68 once the window was on screen.
  No tool moves the camera off screen: a set-up's loads run with the window on screen.
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
    re,
)
from .frames3d import SETTLE_LIMIT, _Frames, _viewport, _Waiting
from .screenshots import _3d_dock
from .state3d import (
    _PLACES,
    DEGREES_PER_TURN,
    PER_MATERIAL,
    SHADER_MODELS,
    STATE_BACKUP,
    USERS_MESH,
    VIEW_DIRECTIONS,
    Pose,
    StateField,
    StateFields,
    _camera_moved,
    _framed,
    _materials_linked,
    _mesh_id,
    _mesh_listed,
    _reframed,
    _state_back_up,
    _state_changes,
    _state_default_path,
    _state_edited,
    _state_fields,
    _state_overridden,
    _state_put_back,
    _state_resources,
    _state_said,
    _state_text,
    _state_write,
)
from .view3d import (
    MESHES,
    SETTING,
    _apply_outputs,
    _environment_maps,
    _explorer_tree,
    _material_checked,
    _materials_used,
    _menu_action,
    _set_up_checked,
)

SAVE = 'Save Current State As Default'
RESET = 'Reset Scene'
FRAME = 'Frame'  # the Camera menu's
AOV = '3dview.display.aov'  # the 3D view's AOV button's object name
AOV_LOADED = 'Beauty'  # the AOV a load shows (the module docstring)
# how close two poses are, the camera unchanged: angles in degrees, lengths relative to the distance. Designer saves its
# own camera off by up to about 3e-6 degrees (its Default view at yaw 45.0000024: REVIEW.md HLP-265), as
# state3d.CAMERA_LEVEL takes its X level
SAME_POSE = 1e-4
# s at most for the import of a mesh file a load names to end: a safety net (the Samba FBX took 1.7 to 7.1 s, 2026-11-27)
IMPORT_LIMIT = 30.0
# what a step loading a mesh file whose import didn't end within IMPORT_LIMIT says (REVIEW.md HLP-299)
UNIMPORTED = " (the mesh file didn't import within %g s: Designer's log says if it failed, read_designer_log)"
OVERRIDE = 'Override Material'  # each material's entry of the Materials menu, once a graph's outputs are on the mesh
# what a set-up says of a material whose Override Material it turned on, to show the tiling or the shader model it set
# (OWN_SAID; REVIEW.md HLP-316, HLP-321; the user, 2026-11-27: "Render with Override on", "Same as shader_model")
SHOWN_ON = 'Override Material on in %s, to show its %s'
OWN_SAID: dict[StateField, str] = {'tiling': 'tiling', 'shader': 'shader model'}  # each field of the material, said
MARKS = re.compile(r'( \((overridden|unused)\))+$')  # what the Materials menu adds after a material's name
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


def _mesh_shown(bar: QtWidgets.QMenuBar, keep: list[Kept]) -> str | None:
    """The mesh the 3D view shows, as its Scene menu checks it: one of view3d.MESHES. None when the menu checks none, as
    for a mesh of the user's own, or while a load hasn't ended (the module docstring). The set-up reads it to skip a mesh
    shown already, and the 3D view as text to name the mesh."""
    checked = _scene_checked(bar, keep)
    return next((mesh for mesh in MESHES if mesh in checked), None)


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
    end, then the view settled (_Frames.settled), SETTLE_LIMIT at most, a safety net. The count holds at its restart
    while the camera glides, so the view settles once the camera has stopped and the view has drawn it. The wait
    returns whether both ended within their limit. `listed`: whether the file's mesh is one the Scene menu lists.
    - One it lists: the load ends once the menu checks a mesh again, SETTLE_LIMIT at most. The entries checked as Reset
      Scene returns (Display UVs in 2D View, for one) aren't the mesh's.
    - A mesh file of the user's own, which the menu checks none of: once its import has ended, the Materials menu
      listing a material in use again (_materials_used), IMPORT_LIMIT at most (the module docstring; REVIEW.md HLP-283,
      HLP-289).
    Each wait looks as the view paints, and every TICK."""
    since = watched.mark()
    _menu_action(bar, keep, 'Scene', RESET).trigger()
    during = _scene_checked(bar, keep) if listed else set()

    def wait() -> bool:
        if listed:
            ended = watched.until(lambda: bool(_scene_checked(bar, keep) - during), SETTLE_LIMIT)
        else:
            ended = watched.until(lambda: bool(_materials_used(bar, keep)), IMPORT_LIMIT)
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


def _overrides(bar: QtWidgets.QMenuBar, keep: list[Kept]) -> dict[str, QtGui.QAction]:
    """Each material's Override Material entry in the 3D view's Materials menu, in the menu's order, by the material's
    name as the menu gives it, its marks left out (MARKS). A mesh of the Scene menu's shows none before a graph's
    outputs were on it, and the menu lists the materials overridden first (the module docstring)."""
    menu = _menu(_menu_action(bar, keep, 'Materials'))
    keep.append(menu)
    menu.aboutToShow.emit()
    _qt_app().processEvents()
    found: dict[str, QtGui.QAction] = {}
    for action in menu.actions():
        submenu = cast(QtWidgets.QMenu | None, action.menu())  # a QMenu, or None: PySide's stubs say QObject
        if submenu is None:
            continue
        keep += [action, submenu]
        submenu.aboutToShow.emit()
        _qt_app().processEvents()
        for entry in submenu.actions():
            if entry.isCheckable() and entry.text().replace('&', '') == OVERRIDE:
                keep.append(entry)
                found[MARKS.sub('', action.text())] = entry
    return found


def _overrides_back(bar: QtWidgets.QMenuBar, keep: list[Kept], overridden: dict[str, bool], watched: _Frames) -> bool:
    """Each material's Override Material set back to `overridden`, by its name, after a load or a relink turned it on
    (the module docstring), each change waited for on `watched`; nothing when each is on. A material `overridden`
    doesn't name, of a mesh switched, is left as it is. Returns whether the view settled after each, True with nothing
    to wait for (REVIEW.md HLP-292). By name, as the menu lists the materials overridden first (REVIEW.md HLP-315)."""
    settled = True
    if all(overridden.values()):
        return settled
    for name, action in _overrides(bar, keep).items():
        if name in overridden and action.isChecked() != overridden[name]:
            with _Waiting(watched) as waiting:
                action.trigger()
            settled = waiting.settled and settled
    return settled


def _renderer_shown(dock: QtWidgets.QDockWidget) -> str | None:
    """The renderer the 3D view draws with, as its panel's title, `<mesh> - <renderer>`, ends (the module docstring).
    None for a title of another form."""
    title = dock.windowTitle()
    return title.rsplit(' - ', 1)[1] if ' - ' in title else None


def _in_use(bar: QtWidgets.QMenuBar, keep: list[Kept]) -> list[str]:
    """The names of the materials the mesh uses, as the Materials menu lists them in use (view3d._materials_used), their
    marks left out (MARKS): those state3d._used_material takes for a mesh file (REVIEW.md HLP-322)."""
    return [MARKS.sub('', name) for name in _materials_used(bar, keep)]


def _shown_said(bar: QtWidgets.QMenuBar, keep: list[Kept], dock: QtWidgets.QDockWidget, base: str) -> list[str]:
    """What the 3D view shows, a line each: the fields of the state file `base`, a Save's text, the mesh as the Scene
    menu checks it (state3d._state_said, _mesh_shown); then the renderer (_renderer_shown), the AOV (_aov_shown) and
    the Override Material of each material the mesh uses (_in_use), by its name as the Materials menu gives it, on or
    off in the menu's order (_overrides): `Override Material: Body on, Joints off`. An earlier mesh file's materials,
    which the menu lists unused, are left out (the user, 2026-11-28: "Name them"). A line nothing gives is left out."""
    in_use = _in_use(bar, keep)
    said = _state_said(base, _mesh_shown(bar, keep), in_use)
    renderer = _renderer_shown(dock)
    aov = _aov_shown(dock, keep)
    overridden = [
        '%s %s' % (name, 'on' if action.isChecked() else 'off')
        for name, action in _overrides(bar, keep).items()
        if name.replace('&', '') in in_use  # the menu's names in use drop an & (view3d._materials_used)
    ]
    said += ['renderer: ' + renderer] if renderer is not None else []
    said += ['AOV: ' + aov] if aov is not None else []
    said += ['Override Material: ' + ', '.join(overridden)] if overridden else []
    return said


def _3d_shown() -> list[str]:
    """The 3D view as text (_shown_said), read from a Save of the session's state as the default state file. The file
    and its textures' folder are backed up first and put back after, a leftover backup dealt with and said first, as a
    set-up does (the module docstring). Nothing is loaded, and Designer's window stays as it is. Refused when the 3D
    View panel isn't visible or built (screenshots._3d_dock), and when the Save didn't write the file (_state_saved)."""
    folder = _version_folder()
    path, aside = _state_default_path(folder), os.path.join(folder, STATE_BACKUP)
    mw = _main_window()
    keep: list[Kept] = [mw]
    dock = _3d_dock(mw)  # refused unless it has its menu bar
    bar = dock.findChildren(QtWidgets.QMenuBar)[0]
    keep += [dock, bar]
    leftover = _state_back_up(path, aside)
    if leftover is not None:
        print(SAID + leftover)
    try:
        try:
            base = _state_saved(bar, keep, path)
        finally:
            _state_put_back(aside)
    except BaseException:
        # the plugin raises an abort at a traced line, then stops tracing: landed on the put-back, it skipped it. Here,
        # untraced, it is put back, unless it was (as screenshots._3d_render puts the clipboard back: REVIEW.md HLP-171)
        _state_put_back(aside)
        raise
    return _shown_said(bar, keep, dock, base)


def shown_3d() -> None:
    """screenshot_designer('3d', as_text=True): prints the 3D view as text (_3d_shown), a line each."""
    for line in _3d_shown():
        print(line)


def _relinked(tree: QtWidgets.QTreeView | None, keep: list[Kept], materials: Sequence[str]) -> str:
    """The editor's graph's outputs put on the mesh again after a load (the module docstring), on `materials` when
    Designer asks which (view3d._apply_outputs): '' once they are, else what the set-up says: why not, in brackets."""
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
            _apply_outputs(tree, g, keep, materials)
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


def _unsettled(settled: bool, watched: _Frames, imported: bool = True) -> str:
    """What a set-up step adds to what it says when its wait for the 3D view ended at its limit, not on the view at
    rest: the render may be of a view still drawing (REVIEW.md HLP-214), and what may hold its count below 8
    (`watched`'s below_rest; REVIEW.md HLP-215). '' when the wait ended on the view. When the step's load waited
    IMPORT_LIMIT for a mesh file that didn't import (`imported` False), that instead (UNIMPORTED; REVIEW.md
    HLP-299)."""
    if not imported:
        return UNIMPORTED % IMPORT_LIMIT
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
    switched, the tiling, the light or the shader model given), so a 3D shot takes a render before it to compare with
    (shot3d.py). A mesh file given counts, whether the view shows it or not: only the base's Save tells."""

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
    shader_model: str | None = None,
) -> _SetUp:
    """The 3D view's set-up checked, changing nothing: what the arguments rule out, the graph, the panel and the menu
    entries it needs, a mesh using several materials with `tiling` or `shader_model` (view3d._material_checked), and the
    state file's path; refused here (shoot_3d calls it before it puts Designer's window on screen: REVIEW.md HLP-127).
    A mesh file the call loads has its several materials refused once loaded (the module docstring, step 4).
    Returns it, to run around the render (_SetUp.applied, the module docstring's steps).
    Through the state file's loads (the module docstring, step 4): the mesh (view3d.MESHES), framed as the Scene menu
    frames it, or a mesh file's absolute path, framed by Frame, with a second load of the camera options and the
    material's fields that differ from a Save after it, and of a tiling or a shader model on a material whose Override
    Material is off, which the set-up turns on (the module docstring, step 4); the camera at `view`
    (state3d.VIEW_DIRECTIONS, framed), then turned `orbit` [right, up] degrees around the point it looks at, moved `pan`
    [right, up] fractions of the view sideways and `zoom` steps closer (negative: away), from the user's view or the
    framing; the material's tiling; the environment: one of Designer's maps (view3d._environment_maps), its rotation in
    degrees and its exposure; the material's shader model (state3d.SHADER_MODELS). Then `graph`'s outputs on every
    material of the mesh, unless a mesh file the call loads didn't import.

    It prints '3D view, setting: <step>' before each change, so an abort leaves the steps it began said, and an error
    after a change says what was set. Then it prints '3D view: ...' lines: a backup put back or removed first, what it
    set, and once the view is put back, that it was, with a graph not relinked. `between` runs before each step: the 3D
    shot's look, which puts Designer's window on screen again if it went off (shot3d.py; REVIEW.md HLP-136). Each step
    waits for the 3D view to take it on `watched`, the shot's watch of its frames (frames3d.py; REVIEW.md HLP-148)."""
    g = _set_up_checked(graph, mesh, view, environment, shader_model)
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
    # the Materials menu: each set-up reads its Override Material entries (_overrides; REVIEW.md HLP-276). Frame: a
    # mesh file of the user's own takes it
    for entry in (('Scene', SAVE), ('Scene', RESET), ('Materials',), ('Camera', FRAME)):
        _menu_action(bar, keep, *entry)  # there; looked up again as it is used
    # the fields asked, as the state file holds them: the mesh by its id, or a mesh file by its URL, unless the Scene
    # menu checks it already (_mesh_shown, which the 3D view as text reads too; a mesh file's the base tells), the map
    # by its URL, the rotation in turns
    asked = StateFields()
    if mesh is not None and mesh != _mesh_shown(bar, keep):
        asked['mesh'] = _mesh_id(mesh)
    if environment is not None:
        asked['environment'] = _environment_maps()[environment]
    if environment_rotation is not None:
        asked['rotation'] = environment_rotation / DEGREES_PER_TURN
    if environment_exposure is not None:
        asked['exposure'] = environment_exposure
    own = StateFields()  # the fields asked of the material the mesh uses: a mesh file's import maps its own
    if tiling is not None:
        own['tiling'] = tiling
    if shader_model is not None:
        own['shader'] = SHADER_MODELS[shader_model]
    owns: list[StateField] = [n for n in PER_MATERIAL if n in own]
    shown_own = ' and '.join(OWN_SAID[name] for name in owns)  # what a material turned on shows (SHOWN_ON)
    # refused for a mesh using several materials; with a new mesh, the new one's: a preset has one, a mesh file is
    # checked once imported (REVIEW.md HLP-114, HLP-127; the lead, 2026-11-27)
    if 'mesh' not in asked and own:
        _material_checked(bar, keep)
    writes_camera = camera or 'mesh' in asked  # moved, or framed for a new mesh
    reads: list[StateField] = [n for n in _PLACES if n in asked or (writes_camera and n in ('camera', 'mesh'))]
    # each option set through the state file, as said
    light = [_environment_said(environment, environment_rotation, environment_exposure)] if lit else []
    said = [mesh] if mesh is not None else []
    said += [_camera_said(view, turn, move, zoom)] if camera else []
    said += ['tiling %g' % tiling] if tiling is not None else []
    said += light
    said += ['shader model ' + shader_model] if shader_model is not None else []
    first = [mesh, *light] if mesh is not None else light  # what a mesh file's first load sets (REVIEW.md TST-988)

    @contextlib.contextmanager
    def applied(between: Callable[[], None] | None, watched: _Frames) -> Iterator[bool]:
        """The set-up's steps, then the render (the `with` block), then the view put back: the module docstring.
        Yields whether the steps changed what the view shows: a field written that the base held otherwise, the camera
        moved or the mesh switched included. A graph may be what is shown already, so it doesn't count (shoot_3d's
        retakes)."""
        done: list[str] = []
        touched = False  # the session's view changed: the base loaded back after
        base, linked, aov = '', False, None  # the user's state, whether it showed a graph's outputs, and its AOV
        showed: list[str] = []  # the materials that showed them (state3d._materials_linked)
        overridden: dict[str, bool] = {}  # each material's Override Material, as the user had it, by its name
        turned_on: list[str] = []  # the materials whose Override Material the set-up turned on (SHOWN_ON)

        def rendered() -> dict[str, bool]:
            """Each material's Override Material as the set-up's loads and relinks leave it: the user's, but on in those
            it turned on."""
            return {**overridden, **dict.fromkeys(turned_on, True)}

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
            shows the user's AOV again and sets each material's Override Material back as rendered() gives it: a load
            puts the AOV back to Beauty, and turns Override Material on. The wait returns whether the view settled after the
            load and after each of these."""
            listed = _mesh_listed(content)  # REVIEW.md HLP-283, HLP-287
            _state_write(path, content)
            loaded = _state_load(bar, keep, watched, listed)

            def wait() -> bool:
                settled = loaded()
                shown = _aov_back(dock, keep, aov, watched)
                set_back = _overrides_back(bar, keep, rendered(), watched)
                return settled and shown and set_back  # each wait said (REVIEW.md HLP-292)

            return wait

        def in_use() -> list[str]:
            """The materials the mesh shown uses, by name, with a field of the material asked (_in_use): read before
            each load, so a mesh file the call loaded gives its own."""
            return _in_use(bar, keep) if own else []

        def written(content: str, fields: StateFields) -> str:
            """`content` with `fields` written (state3d._state_edited). With a tiling or a shader model, the material
            the mesh uses held overridden, and left so for the render when it wasn't, its name in turned_on (the module
            docstring, step 4)."""
            used = in_use()
            content = _state_edited(content, fields, used)
            if not any(name in fields for name in PER_MATERIAL):
                return content
            content, name = _state_overridden(content, used)
            turned_on.extend([name] if name is not None else [])
            return content

        def own_changes(content: str, held: StateFields) -> StateFields:
            """The fields asked of the material the mesh of `content` uses that differ from `held`, what it holds. All
            of them when it is held not overridden, though it holds them: shown only with Override on, they are shown
            so (written; the user's choice, "Render with Override on", for every shot with a model, then "Same as
            shader_model" for a tiling; REVIEW.md HLP-318, HLP-321)."""
            if own and _state_overridden(content, in_use())[1] is not None:
                return own.copy()
            return _state_changes(held, own)

        def imported(content: str) -> bool:
            """Whether the mesh of `content`, just loaded, imported: one the Scene menu lists, or a mesh file whose
            materials the Materials menu lists in use (_state_load; REVIEW.md HLP-299)."""
            return _mesh_listed(content) or bool(_materials_used(bar, keep))

        def framed(size: tuple[float, float]) -> bool:
            """Designer's own Frame on the mesh shown, a mesh file of the user's own; then, from a Save, the camera
            options from Frame's pose and the material's fields asked, in the material the mesh uses, written and
            loaded when they differ from it (own_changes; the module docstring). Each change waited for after the
            shot's look. Returns whether the view settled after each. Refused when a field of the material is asked and
            the mesh uses several (MATERIALS_USED, state3d._used_material)."""
            if between is not None:
                between()
            with _Waiting(watched) as waiting:
                _menu_action(bar, keep, 'Camera', FRAME).trigger()
            if not (camera or own):
                return waiting.settled
            text = _state_saved(bar, keep, path)
            names: list[StateField] = ['camera', *owns]
            held = _state_fields(text, names, in_use())
            second = own_changes(text, held)
            if camera:
                at = held['camera']
                if view is not None:
                    at = Pose(at.target, *VIEW_DIRECTIONS[view], at.distance)
                second['camera'] = _camera_moved(at, size, turn, move, zoom)
            if not second:
                return waiting.settled
            if between is not None:
                between()
            return loading(written(text, second))() and waiting.settled

        def relinked() -> str:
            """The editor's graph relinked (_relinked), then Override Material set back as rendered() gives it, which the
            relink turns on (the module docstring; REVIEW.md HLP-291). Returns what _relinked says."""
            unlinked = _relinked(tree, keep, showed)
            if not unlinked:
                _overrides_back(bar, keep, rendered(), watched)
            return unlinked

        def put_back() -> None:
            """The view put back, if the call changed it: the shot's look first, then the base written and loaded, the
            AOV set back, the editor's graph relinked and Override Material set back after it, said on the put-back's
            own line, with a failure of the look.
            Then the backup put back, whatever happened before."""
            turned_on.clear()  # the user's Override Material again, a shader model's material's included
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
                    unsettled = _unsettled(settled, watched, imported(base))
                    unlinked = relinked() if linked else ''
                    print(SAID + 'put back as it was' + unsettled + unlinked + looked)
            finally:
                _state_put_back(aside)

        leftover = _state_back_up(path, aside)
        if leftover is not None:
            print(SAID + leftover)
        try:
            try:
                base = _state_saved(bar, keep, path)
                linked = os.path.isdir(_state_resources(path))  # Save writes textures only for a graph on the mesh
                showed = _materials_linked(base, _state_resources(path))
                held = _state_fields(base, reads)  # a file lacking a field read is refused before anything changes
                aov = _aov_shown(dock, keep)
                overridden = {name: action.isChecked() for name, action in _overrides(bar, keep).items()}
                changes = _state_changes(held, asked)  # the fields written: those the user's view holds otherwise
                shown = changes.get('mesh', held.get('mesh', ''))
                size = (float(viewport.width()), float(viewport.height()))
                # a mesh file of the user's own, new or given a view, is framed by Designer's own Frame once loaded, and
                # the camera options and the material's fields are written after it (framed; the module docstring)
                framing = shown.startswith(USERS_MESH) and ('mesh' in changes or view is not None)
                new_file = framing and 'mesh' in changes  # its materials are read once it has imported (framed)
                meshed = base  # the base, its mesh written below for a preset's own material
                if not new_file:  # the base holds the mesh's materials: several refused here (REVIEW.md HLP-303)
                    if 'mesh' in changes:  # a preset's own once its id is written (state3d._used_material; HLP-311)
                        meshed = _state_edited(base, {'mesh': changes['mesh']})
                    held.update(_state_fields(meshed, owns, in_use()))
                if not framing:
                    changes.update(own_changes(meshed, held))
                    if camera or 'mesh' in changes:
                        start = held['camera']
                        if view is not None:
                            at = _framed(shown, view, size)
                        elif 'mesh' in changes:  # framed as the Scene menu's switch frames it (the module docstring)
                            at = _reframed(start, shown, size)
                        else:
                            at = start
                        at = _camera_moved(at, size, turn, move, zoom)
                        if not _same_pose(at, start):
                            changes['camera'] = at
                changed = bool(changes) or framing
                load_settled = True  # the loads' and Frame's waits, said once with the relink's (REVIEW.md HLP-292)
                ok = True  # the mesh imported; with none, nothing to frame or to put outputs on (REVIEW.md HLP-299)
                if said:
                    step = begin(', '.join(said), changed)
                    # one shown already restarts nothing, and the wait would run to its limit (REVIEW.md HLP-195)
                    content = written(base, changes) if changes else ''
                    loaded = loading(content) if content else None
                    # before its wait: an error there says the step was set (REVIEW.md HLP-200); for a mesh file's first
                    # load, what it sets, the rest once framed (REVIEW.md TST-988)
                    done.append(', '.join(first or said) if framing else step)
                    if loaded is not None:
                        load_settled = loaded()
                        ok = imported(content)
                    if framing and ok:
                        load_settled = framed(size) and load_settled
                        done[-1] = step
                    done[-1] += _unsettled(load_settled, watched, ok)
                if g is not None and ok:  # with no mesh, its outputs aren't said to be on it (REVIEW.md HLP-307)
                    step = begin("graph %s's outputs on the mesh" % g.getIdentifier())
                    with _Waiting(watched) as waiting:
                        g.compute()  # its outputs ready for the mesh
                        _apply_outputs(cast(QtWidgets.QTreeView, tree), g, keep)  # found above, as g was given
                        done.append(step)  # before its wait (REVIEW.md HLP-200)
                    done[-1] += _unsettled(waiting.settled, watched)
                # after the load: the shot shows the outputs, not their textures' copies
                elif changed and linked and ok:
                    with _Waiting(watched) as waiting:
                        unlinked = relinked()
                        waiting.needed = not unlinked  # not relinked: nothing changed, so no restart to wait for
                    done[-1] += unlinked
                    if load_settled:  # said once: a load that hadn't settled said so
                        done[-1] += _unsettled(waiting.settled, watched)
                done += [SHOWN_ON % (name, shown_own) for name in turned_on]
                print(SAID + ', '.join(done))
            except (Exception, APIException) as e:  # the sd API's error is a BaseException too
                if not done:
                    raise
                raise RuntimeError('%s; the 3D view was already set: %s' % (e, ', '.join(done))) from e
            yield changed
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

    return _SetUp(applied, camera or bool(asked) or bool(own))
