"""The 3D view set up before screenshot_designer('3d') renders it: a graph's outputs on its mesh, the mesh, the
viewpoint, the camera turned and panned, the zoom, the tiling and the environment (ROADMAP items 7, 73 and 74).
Designer's API has none of it
(sd, Designer 16), so this drives the view's own menus and widgets, as measured in a Designer an agent started
(2026-11-12; the self-test's editor_panels_and_fit checks what the tool relies on, lifecycle the first point below):

- Designer builds the 3D view's menu bar and viewport once a graph is opened (before, its dock has neither).
- The 3D view's menu bar: Scene lists the meshes (MESHES, among other entries), Camera the viewpoints (VIEWS) and
  Frame. Their actions trigger from code once the menu's aboutToShow has filled it, as the screenshot's Copy Render
  does. Scene checks the mesh the view shows: the mesh step reads the action of the mesh asked, and skips a mesh
  checked already. The camera turns to a viewpoint over a moment, and a Frame triggered at once cancels the turn, so
  Frame waits for the turn to end (_Frames.moved: frames3d.py).
- Zoom: wheel events on the viewport (the visible Alg::Gui3D::ViewportWidget), taken as from the mouse although the
  view is GPU-drawn: about 1.11x a step closer, 1.09x a step away, from wherever the camera is. Sent back to back,
  some are dropped, so each waits for the view to take the one before (_Frames.taking: frames3d.py).
- The camera's position and angles are in none of its properties (Camera > Edit properties shows its lens, clip
  planes and exposure; the Scene Browser's Camera the same), so orbit and pan are Designer's own navigation: mouse
  drags on the viewport, taken as from the mouse, in any number of moves. A left-drag turns the camera around the
  point it looks at (the mesh's middle after a view), ORBIT_ACROSS degrees a pixel across and ORBIT_UP up or down:
  from Front, 200 px gave Designer's own Left view exactly and 257 px its Top. The mouse right turns the camera left,
  the mouse down raises it. A middle-drag pans: the content follows the mouse, the point looked at moving a view's
  width every PAN_WIDTH pixels, either way, whatever the zoom; nearer parts move more (Designer's default 35 mm lens,
  other lenses not measured). Both rates held in viewports of 124x362, 338x362, 419x443, 627x253 and 325x583 px,
  measured by probes, on a display of pixel ratio 1 (not measured on another); what the self-test's one size leaves
  unchecked: its pan check's docstring. A drag is whole pixels: what is said set is what the drags
  carry, and a value that isn't 0 but rounds to no pixel is refused, as it would be said and not done (REVIEW.md
  HLP-121).
  A drag sent too soon after another undoes it, or part of it: a pan 0.02 s after a pan left the first undone (0.05 s
  later, both taken), two turns sent back to back came out wrong (0.1 s apart, as two calls), and wheel steps right
  after a drag zoomed less. Sent once the view drew a frame after it, both were taken (frames3d.py), so each drag is
  followed by a wait for that frame; off screen, where the view draws none, for its request for one (_Frames.taking;
  REVIEW.md HLP-149). A mouse move with no button held, as the user's
  mouse sends over the viewport, ends a drag where it is: one after the 5th of 10 moves left orbit=[90, 0] 60 grey
  levels from Designer's Right view, and pan=[0.25, 0] at 0.099 of the view (REVIEW.md HLP-122). So while a drag
  runs, its wait included, a filter on the viewport drops every mouse event (MOUSE_EVENTS) _mouse isn't sending;
  the filter goes when the drag ends, or with the drag's frame, after an abort.
- The toolbar's Camera and Light tools are one group: under Light, neither drags nor the wheel move the camera (the
  wheel's zoom was said and not done: REVIEW.md HLP-120), so orbit, pan and zoom select the Camera tool and put the
  Light tool back after. Selection, a toggle beside them, changes nothing a drag does: the camera turned alike, the
  Parameters panel kept.
  An abort landing where a drag's button is released, or where the Light tool is selected again, skips that; the
  abort's handler, run untraced, does it then.
- A graph's outputs reach the mesh as Designer switches to the graph (Preferences > Graph > Common, "View outputs in 3D
  view when opening a graph"), so outputs added to the graph open in the editor don't until it switches again, and
  opening that graph again doesn't apply them either. The Explorer's "View Outputs In 3D View" does, but only from its
  context menu: the action triggered by itself does nothing. So the graph is selected in the Explorer
  (setExplorerSelection, which the user sees, and which expands a collapsed package), the menu opened on its row with
  a QContextMenuEvent, and a timer picks the action while the menu runs, as soon as the menu shows: the action is
  there, enabled, at the first look (three menus, 2 to 6 ms after the event; 2026-11-15). A graph with one output
  makes Designer ask which channel to show it in, a second menu: such a graph is refused first.
- That menu is a new QMenu each time, with no parent, deleted once closed: nothing can be connected to it before it
  opens. It shows above every app's windows, also while the 3D shot keeps Designer's own transparent: picked after
  100 ms, it was on screen for 240 ms; made transparent by a timer at 0 ms as it opens, for 0, 9 and 0 ms (three
  shots, a watch of the window server's list from another process, 2026-11-14). So the timer makes it transparent
  first, then picks its action; the self-test watches it (REVIEW.md HLP-134). On macOS it makes the menu
  click-through too (the user's choice: DECISIONS.md): whether a click reaches a menu that is only transparent
  couldn't be measured without clicking on the user's screen. Click-through, the menu's action is still picked
  (2026-11-14). A menu closed by something else
  between the fade and the pick was deleted by the Explorer as usual, but its window stayed, hidden, transparent and
  click-through (a scratch run closing it so; the self-test's final check met it, 2026-11-14). So on macOS the fade
  holds the menu's window, and once the menu closed gives it its look back (REVIEW.md HLP-146). Twice in full runs
  something closed the menu before its action was picked, and the shot was refused (2026-11-15). What closed it wasn't
  found: another Designer an agent starts, started and quit while a menu was held open, closed nothing. So a menu
  closed before its pick, or never seen open, is opened again, MENU_TRIES times at most (REVIEW.md HLP-147). An open
  menu holds the job, and with it the bridge, so a guard closes whatever popup is still open after MENU_GUARD ms,
  above any open before (the user's). An abort (a cancel, the job's timeout) raised in a Qt slot is dropped and
  raised again at the next Python line run (the plugin's _make_tracer), so the timer that picks the action closes its
  menu in a `finally`, and the guard is made of C callables only (_popup_closer). The timers have a parent the
  function holds alone, so they go with it even when an abort lands in the `finally` that stops them: without one, a
  timer whose slot holds it outlives the function (the self-test's designer fact).
- Tiling is the 3D material's UVs > Tiling, shown in the Parameters panel by Materials > <material> > Edit properties.
  A material added to the mesh (Materials > Add) is listed as "(unused)", and isn't counted.
  Its spin box takes a value only through its own valueChanged() signal (neither setValue, Return, nor its slider's
  or editor's signals reach the material). The panel is then turned back to the graph in the editor by opening that
  graph again, once it shows the material: turned back before, the switch to the material came after.
- The environment, the light around the mesh, is shown in the Parameters panel by Environment > Edit properties, and
  turned back as after the tiling (measured 2026-11-18; the self-test's designer fact checks the fields, the commit,
  the map's signals, a drop or an enter and a move alone, the unwrapped rotation and the reset). Its fields are found
  by the end of their object name, after a '-' (the numbers before change):
  - `intensity`: Exposure, one spin box, 0 by default.
  - `dome_rotation_angle`: Rotation Angle, two spin boxes, Turns then Degrees. A value isn't wrapped: 1.75 turns
    stays 630 degrees.
  - `environment_texture_name`: the map, with no editor in the panel (0 px high; its menu offers only a reset).
  A spin box takes a value as Tiling's does, only through its own valueChanged(). A map is set by a drag of its file
  onto the viewport, as from the Library's 3D view > HDRI environments, which lists Designer's own maps
  (_environment_maps). The drag is entered, moved, then dropped: a drop alone, or an enter and a move, did nothing. It
  is taken with Designer hidden too, though the drop reads as not accepted. The Environment field then signals
  valueChanged() at once, within the drop, unless the map was the one shown, which changes nothing and signals
  nothing. So when no signal comes, another map is dropped, then the one asked for again, each to be signalled:
  dropped back to back, the second stays (the renders matched to 0.0 grey levels). The view then restarted nothing
  within NO_RESTART (watched once), so the step doesn't wait for it: the render after is the one before (the
  self-test's shown-already check; REVIEW.md HLP-201). A drop keeps the rotation and the exposure. Environment > Reset Environment puts the rotation and the exposure back to 0, and changes the map.
- What is set stays: for the next shots, and in the user's 3D view.
"""

from .core import (
    _APP,
    APIException,
    Callable,
    Kept,
    QtCore,
    QtGui,
    QtWidgets,
    SDApplicationPath,
    SDSBSCompGraph,
    Sequence,
    _current_graph,
    _main_window,
    _menu,
    _qt_app,
    _ui_mgr,
    cast,
    find_graph,
    os,
    sys,
)
from .editor import _process_events, _wheel
from .frames3d import _Frames, _frames_of, _viewport, _Waiting
from .mac_window import _MacWindow
from .screenshots import _PANEL_AREAS, _3d_dock, _visible_dock
from .shot3d import _on_screen
from .waits import _settle

MESHES = (
    'Cube',
    'Cylinder',
    'Plane',
    'Plane (hi-res)',
    'Sphere',
    'Cloth',
    'Mat ball',
    'Rounded cube',
    'Rounded cylinder',
    'Sphere 2 tiles',
    'Torus',
)
VIEWS = ('Default', 'Front', 'Right', 'Back', 'Left', 'Top', 'Bottom')
VIEW_OUTPUTS = 'View Outputs In 3D View'
MENU_GUARD = 5000  # ms the Explorer's context menu may stay open
MENU_TRIES = 3  # times the Explorer's context menu is opened when something closes it before its action is picked
# a flag's interval (_drop_map): it never runs out within a call, its timeout connected to nothing
FLAG_MS = 24 * 3600 * 1000
SETTING = '3D view, setting: '  # a step said before its change (set_3d_view's docstring); the server collects these
ORBIT_ACROSS = 0.45  # degrees the camera turns a pixel dragged across (the module docstring)
ORBIT_UP = 0.35  # degrees a pixel dragged up or down
PAN_WIDTH = 356  # pixels dragged a view's width panned, at the point the camera looks at
DRAG_MOVES = 10  # mouse moves a drag is sent in: 1, 2, 10 or 40 turned the camera alike
TOOLS = ('Camera', 'Light')  # the 3D view's toolbar's tools a drag and the wheel go to, one group
# what the guard on the viewport drops during a drag unless _mouse is sending it (the module docstring)
MOUSE_EVENTS = ('MouseButtonPress', 'MouseButtonRelease', 'MouseButtonDblClick', 'MouseMove', 'Wheel')
_OWN_MOUSE = [False]  # _mouse sending an event
# _drag's record of a drag's button held down: (button, x, y), where the drag releases it. set_3d_view's handler of an
# abort releases what it finds there.
Pressed = list[tuple[QtCore.Qt.MouseButton, float, float]]


def _menu_action(bar: QtWidgets.QMenuBar, keep: list[Kept], *path: str) -> QtGui.QAction:
    """The action at `path` in the 3D view's menu bar (a menu, its submenus, the action), each menu filled first.
    `keep` holds the wrappers, which go stale once no Python reference is left (GUIDE.md, Designer UI)."""
    app = _qt_app()
    actions = list(bar.actions())
    for i, name in enumerate(path):
        found = [a for a in actions if a.text().replace('&', '') == name]
        if not found:
            raise RuntimeError("the 3D view's %s has no %r" % (' > '.join(path[:i]) or 'menu bar', name))
        action = found[0]
        keep.append(action)
        if i == len(path) - 1:
            return action
        menu = cast(QtWidgets.QMenu | None, action.menu())  # a QMenu, or None: PySide's stubs say QObject
        if menu is None:
            raise RuntimeError("the 3D view's %r is no menu" % ' > '.join(path[: i + 1]))
        keep.append(menu)
        menu.aboutToShow.emit()
        app.processEvents()
        actions = list(menu.actions())
    raise RuntimeError('no menu path given')


def _material(bar: QtWidgets.QMenuBar, keep: list[Kept]) -> str:
    """The name of the material the mesh uses in the 3D view's Materials menu ('Default (overridden)'), one Designer
    lists as unused not counted; refused for a mesh using several, as tiling= would set one of them."""
    menu = _menu(_menu_action(bar, keep, 'Materials'))
    keep.append(menu)
    menu.aboutToShow.emit()
    _process_events()
    materials = [a for a in menu.actions() if a.menu() is not None and a.text() and '(unused)' not in a.text()]
    keep += materials
    names = [a.text().replace('&', '') for a in materials]
    if len(names) != 1:
        raise RuntimeError(
            "the 3D view's mesh has %d materials%s; tiling= sets the material of a mesh with one"
            % (len(names), ': ' + ', '.join(names) if names else '')
        )
    return names[0]


def _row_point(tree: QtWidgets.QTreeView, row: QtCore.QModelIndex, graph: str) -> QtCore.QPoint:
    """The middle of the graph's `row` in the Explorer's tree, scrolled into view. Refused unless the row is there under
    that point: the context menu opens for whatever row lies there, and would apply another graph."""
    tree.scrollTo(row)
    _process_events()
    at = tree.visualRect(row).center()
    if not tree.viewport().rect().contains(at) or tree.indexAt(at) != row:
        raise RuntimeError("graph %s's row isn't showing in the Explorer (a filter?)" % graph)
    return at


class _MenuPick:
    """What _menu_once's look does in one try, while the Explorer's context menu runs, and what went wrong, said
    after. `before` is the popup open before the menu, maybe the user's: never taken for it."""

    def __init__(self, action: str, before: QtWidgets.QWidget | None) -> None:
        self.action = action
        self.before = before
        self.menus = 0  # menus pick found open
        self.disabled = False  # the action found disabled
        self.picked = False  # the action triggered in one
        self.faded = False  # a menu made transparent by fade
        self.closed = False  # a menu pick found closed already, by something else
        self.fade_error: str | None = None  # why fade raised, the menu closed then (REVIEW.md HLP-153)
        self.held: tuple[_MacWindow, int] | None = None  # on macOS, that menu's window, held till unfade

    def pick(self, menu: QtWidgets.QMenu | None) -> bool:
        """In the menu opened since, trigger the action if enabled and close the menu, even when the trigger raises
        (an abort: the module docstring): True. A menu closed already by something else is left: True too. No such
        menu yet (None, or `before`): False, so its timer looks again."""
        if menu is None or menu is self.before:
            return False
        # closed as fade made it transparent, by something else (REVIEW.md HLP-147); one closed before the look is
        # one that didn't open, the look picking in the slot that fades
        if not menu.isVisible():
            self.closed = True
            return True
        self.menus += 1
        try:
            for action in menu.actions():
                if action.text().replace('&', '') == self.action:
                    self.disabled = not action.isEnabled()
                    if not self.disabled:
                        self.picked = True
                        action.trigger()
        finally:
            menu.close()
        return True

    def fade(self, menu: QtWidgets.QMenu | None) -> bool:
        """Makes the menu opened since transparent, so it doesn't show over the user's windows while the 3D shot keeps
        Designer's own transparent (the module docstring), and on macOS click-through: True. No such menu yet (None,
        or `before`): False, so its timer looks again. Raising, it says why in fade_error first (REVIEW.md HLP-153)."""
        try:
            return self._fade(menu)
        except BaseException as e:
            self.fade_error = '%s: %s' % (type(e).__name__, e)
            raise

    def _fade(self, menu: QtWidgets.QMenu | None) -> bool:
        if menu is None or menu is self.before:
            return False
        if sys.platform == 'darwin':  # held first: the Explorer deletes the menu as it closes, not its window
            mac = _MacWindow(menu)
            window = mac.windows(False)[0]
            mac.hold(window)
            self.held = (mac, window)
        menu.setWindowOpacity(0.0)
        # measured there only: it sets the menu window's ignoresMouseEvents, and the action is still picked
        if sys.platform == 'darwin':
            menu.windowHandle().setFlag(QtCore.Qt.WindowType.WindowTransparentForInput, True)
        self.faded = True
        return True

    def unfade(self) -> None:
        """Once the menu closed: makes the window of the menu fade made transparent opaque and clickable again, and
        ends its hold (macOS). The window of a menu closed before its action was picked stayed transparent and
        click-through (REVIEW.md HLP-146). Cut short by an abort, it can run again: the look is set again, and the
        hold, forgotten just before it ends, ends once. An abort landing between the two leaves the hold: a closed
        window kept, where ending it twice could free it while Designer uses it (REVIEW.md HLP-177)."""
        if self.held is None:
            return
        mac, window = self.held
        mac.set_appearance(window, 1.0, False)
        self.held = None
        mac.let_go(window)

    def closed_early(self) -> bool:
        """Whether no menu was looked in: none opened, or something else closed it first (REVIEW.md HLP-147). A menu
        that couldn't be made transparent isn't opened again."""
        return not self.menus and self.fade_error is None

    def what(self, held: bool) -> str | None:
        """What went wrong with this try's menu, said after "the Explorer's menu for graph X"; None once its action
        was picked. `held`: the guard had to close a menu."""
        if self.fade_error is not None:
            return "couldn't be made transparent (%s), and was closed" % self.fade_error
        if self.picked:
            return None
        if self.menus:
            return ('had %r disabled' if self.disabled else 'had no %r') % self.action
        if held:  # open, and nothing picked: closed by the guard (REVIEW.md HLP-153: said not to have opened)
            return 'was still open %d s after it opened, and was closed with nothing picked' % (MENU_GUARD // 1000)
        if self.closed or self.faded:  # opened, then closed by something else before the pick (REVIEW.md HLP-146)
            return 'closed before its action was picked'
        return "didn't open"

    def failure(self, graph: str, held: bool, tries: int = 1, earlier: Sequence[str] = ()) -> str | None:
        """Why the outputs of `graph` may not be on the mesh, or None; `held`: the guard had to close a menu; `tries`:
        the tries made, whether their menu opened or not, this one the last; `earlier`: what went wrong in the tries before, each try's `what`."""
        what = self.what(held)
        if what is not None:
            whats = [*earlier, what]
            if len(set(whats)) > 1:  # REVIEW.md HLP-153: said with the last try's reason alone
                return "the Explorer's menu for graph %s: %s (%d tries)" % (graph, ', then '.join(whats), tries)
            each = ', in each of %d tries' % tries if tries > 1 else ''
            return "the Explorer's menu for graph %s %s%s" % (graph, what, each)
        if held:
            return (
                'a menu was still open %d s after %r (Designer asking something more?), and was closed unanswered'
                % (
                    MENU_GUARD // 1000,
                    self.action,
                )
            )
        return None


def _popup_closer(
    active: Callable[[], QtWidgets.QWidget | None], before: QtWidgets.QWidget | None
) -> Callable[[], None]:
    """Closes the popups open above `before` (None: any), at most 5. Made of C callables only, so no Python frame runs
    for an abort to land in (the module docstring). `active` is QApplication.activePopupWidget; it can run once."""
    import collections
    import functools
    import itertools
    import operator

    return functools.partial(
        collections.deque(maxlen=0).extend,
        map(operator.methodcaller('close'), itertools.islice(iter(active, before), 5)),
    )


def _explorer_tree(mw: QtWidgets.QMainWindow, keep: list[Kept]) -> QtWidgets.QTreeView:
    """The Explorer's tree, which graph= goes through; refused when the Explorer isn't visible."""
    explorer = _visible_dock(mw, _PANEL_AREAS['explorer'])
    if explorer is None:
        raise RuntimeError("graph= goes through the Explorer panel, which isn't visible (Windows > Explorer)")
    trees = [v for v in explorer.findChildren(QtWidgets.QTreeView) if v.objectName() == 'mTreeView']
    if not trees:
        raise RuntimeError("the Explorer's tree wasn't found")
    keep += [explorer, trees[0]]
    return trees[0]


def _apply_outputs(tree: QtWidgets.QTreeView, graph: SDSBSCompGraph, keep: list[Kept]) -> None:
    """The Explorer's "View Outputs In 3D View" for `graph`, from its context menu on the Explorer's `tree` (the module
    docstring). A menu closed before its action was picked, by something else, is opened again, MENU_TRIES times at
    most (REVIEW.md HLP-147)."""
    _ui_mgr().setExplorerSelection(graph)
    _process_events()
    rows = tree.selectionModel().selectedRows()
    if len(rows) != 1:
        raise RuntimeError(
            "graph %s wasn't selected in the Explorer (%d rows are)" % (graph.getIdentifier(), len(rows))
        )
    at = _row_point(tree, rows[0], graph.getIdentifier())
    tried, earlier = 0, []
    while True:
        tried += 1
        state, held = _menu_once(tree, at, keep)
        if held or not state.closed_early() or tried == MENU_TRIES:
            break
        earlier.append(cast(str, state.what(held)))  # closed early: something went wrong
    failure = state.failure(graph.getIdentifier(), held, tried, earlier)
    if failure:
        raise RuntimeError(failure)


def _menu_once(tree: QtWidgets.QTreeView, at: QtCore.QPoint, keep: list[Kept]) -> tuple[_MenuPick, bool]:
    """The Explorer's context menu opened once at `at` on `tree`, and its action picked while it runs: what the pick
    found, and whether the guard had to close a menu. An abort raised at the look's call, or at its first line, comes
    before any of the look runs: the menu then stays as it opened until the guard closes it, MENU_GUARD at most
    (REVIEW.md HLP-177)."""
    app = QtWidgets.QApplication
    before = app.activePopupWidget()  # a popup already open, maybe the user's: left alone
    keep.append(before)
    state = _MenuPick(VIEW_OUTPUTS, before)

    def look() -> None:
        # the menu made transparent as it opens, then its action picked at once: there at the first look (measured).
        # No `try:` inside this one: an abort raised at a `try:` line escapes the `try` around it in the same function
        # (measured on Python 3.12 and Designer's 3.13; REVIEW.md HLP-177)
        try:
            menu = app.activePopupWidget()
            menu = menu if isinstance(menu, QtWidgets.QMenu) else None
            keep.append(menu)
            if not state.fade(menu):
                timers[0].start(0)
                return
            state.pick(menu)
        except BaseException:
            # closed at once, not left open over the user's windows (REVIEW.md HLP-153): a menu fade couldn't make
            # transparent, and one an abort left open before its fade or as pick closed it, here untraced (REVIEW.md
            # HLP-177). A popup open before it, maybe the user's, is left. Found again, not the menu found above: one
            # closed already may be deleted, and anything but the abort raised here would end the abort (the plugin
            # takes up only its own after a slot)
            left = app.activePopupWidget()
            if left is not None and left is not before:
                left.close()
            raise

    def put_back() -> None:
        for timer in timers:  # neither may act later, on a menu of the user's
            timer.stop()
        state.unfade()  # the menu closed: its window opaque and clickable again

    # the timers' parent, held by this frame alone: they go with it once nothing keeps the frame (an abort's traceback
    # does, so the handler below stops them too)
    owner = QtCore.QObject()
    timers: list[QtCore.QTimer] = []
    try:
        try:  # from the first timer on: an abort landing as the second starts must stop the first
            # the look, at once: the menu transparent as it opens; the guard: an open menu holds this job, and the
            # bridge
            for run, after in ((look, 0), (_popup_closer(app.activePopupWidget, before), MENU_GUARD)):
                timers.append(QtCore.QTimer(owner))
                timers[-1].setSingleShot(True)
                timers[-1].timeout.connect(run)
                timers[-1].start(after)
            viewport = tree.viewport()
            event = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Reason.Mouse, at, viewport.mapToGlobal(at))
            app.sendEvent(viewport, event)  # returns once the menu has closed
            held = not timers[1].isActive()  # the guard ran
        finally:
            put_back()
    except BaseException:
        # the plugin raises an abort at a traced line, then stops tracing: landed in the put-back, it skipped the rest
        # of it. Here, untraced, it is done again: both steps can be (REVIEW.md HLP-177)
        put_back()
        raise
    return state, held


def _panel_field(
    params: QtWidgets.QDockWidget, name: str, what: str, keep: list[Kept], spins: int = 1
) -> QtWidgets.QWidget:
    """The field `name` of the Parameters panel `params` once the panel built it, with at least `spins` spin boxes. A
    field is found by its object name, or by the end of it after a '-' (the environment's: the module docstring).
    Refused after 3 s, `what` naming the field."""
    fields: list[QtWidgets.QWidget] = []
    for _ in range(30):  # the panel builds its fields over a few event loops
        _settle(0.1)
        fields = [
            w
            for w in params.findChildren(QtWidgets.QWidget)
            if w.objectName() == name or w.objectName().endswith('-' + name)
        ]
        if fields and len(fields[0].findChildren(QtWidgets.QDoubleSpinBox)) >= spins:
            keep.append(fields[0])
            return fields[0]
    if fields:  # REVIEW.md HLP-191: a bare IndexError named no field
        found = len(fields[0].findChildren(QtWidgets.QDoubleSpinBox))
        raise RuntimeError('%s has no spin box %d in the Parameters panel (it has %d)' % (what, spins, found))
    raise RuntimeError("%s wasn't found in the Parameters panel" % what)


def _panel_spin(
    params: QtWidgets.QDockWidget, name: str, what: str, keep: list[Kept], index: int = 0
) -> QtWidgets.QDoubleSpinBox:
    """The `index`-th spin box of the field `name` of the Parameters panel `params` (_panel_field), in the order the
    panel made them."""
    spin = _panel_field(params, name, what, keep, index + 1).findChildren(QtWidgets.QDoubleSpinBox)[index]
    keep.append(spin)
    return spin


def _tiling_spin(params: QtWidgets.QDockWidget, keep: list[Kept]) -> QtWidgets.QDoubleSpinBox:
    """The 3D material's Tiling spin box in the Parameters panel `params`, once Edit properties has shown it there."""
    return _panel_spin(params, '$tiling', "the 3D material's Tiling", keep)


def _commit(spin: QtWidgets.QDoubleSpinBox, value: float, what: str) -> None:
    """`value` set in the Parameters panel's `spin` and taken through the spin box's own valueChanged(), with no
    argument: QDoubleSpinBox's valueChanged(double) doesn't take it (the module docstring); Designer's events then run.
    Refused when the spin box has no such signal, `what` naming its field."""
    spin.setValue(value)
    # PySide takes the name as str (its stubs say bytes, which it refuses); False: no such signal, nothing taken
    if not QtCore.QMetaObject.invokeMethod(
        spin,
        'valueChanged',
        QtCore.Qt.ConnectionType.DirectConnection,  # type: ignore[call-overload]
    ):
        raise RuntimeError("%s didn't take %g: its spin box has no valueChanged()" % (what, value))
    _process_events()


def _commit_change(
    find: Callable[[], QtWidgets.QDoubleSpinBox], value: float, what: str, watched: _Frames
) -> tuple[float, tuple[int, int] | None]:
    """`value` committed to the Parameters panel's spin box that `find` gives (_commit), unless it shows the value
    already: the panel shows the values set, so it would change nothing the view draws, and a wait for it would run to
    its limit (REVIEW.md HLP-195). Returns the value the spin box shows, and the mark on `watched` taken right before
    the commit, to wait from (REVIEW.md HLP-192); None with no commit. The value is read from the spin box `find` gives
    again when Designer rebuilt the panel within the commit, deleting the first: it is taken all the same (REVIEW.md
    HLP-198). If that second look refuses, the refusal is raised again with "...; <what> committed to <value>, not
    read back" (REVIEW.md HLP-200)."""
    spin = find()
    if spin.value() == value:
        return value, None
    since = watched.mark()
    _commit(spin, value, what)
    try:
        return spin.value(), since
    except RuntimeError:  # PySide's "Internal C++ object ... already deleted"
        try:
            return find().value(), since
        except (Exception, APIException) as e:  # the sd API's error is a BaseException too
            # committed all the same: said, as an error after a change says what was set (REVIEW.md HLP-200)
            raise RuntimeError('%s; %s committed to %g, not read back' % (e, what, value)) from e


def _parameters_back() -> str | None:
    """The Parameters panel turned back to the graph in the editor (the module docstring), said: 'the Parameters panel
    back on g'. None with no graph in the editor: the panel is left on what it shows."""
    current = _current_graph()
    if current is None:
        return None
    _ui_mgr().openResourceInEditor(current)
    _process_events()
    return 'the Parameters panel back on %s' % current.getIdentifier()


def _switched(params: QtWidgets.QDockWidget, shown: str) -> None:
    """Waits, up to 1 s, for the Parameters panel `params` to show something else than `shown`, its title before
    Edit properties: Designer switches it to the 3D material over a few event loops, so turned back before that (an
    abort landing early), it showed the material all the same."""
    for _ in range(10):
        if params.windowTitle() != shown:
            return
        _settle(0.1)


def _with_set(error: BaseException, said: str) -> RuntimeError:
    """`error` again, followed by what was set before it: 'error; tiling 2 set'. An error after a change says what was
    set (set_3d_view's docstring)."""
    return RuntimeError('%s; %s set' % (error, said))


def _in_properties(
    params: QtWidgets.QDockWidget,
    show: Callable[[], None],
    setting: Callable[[], tuple[str, bool]],
    properties: str,
) -> tuple[str, bool]:
    """`setting` run once `show` turned the Parameters panel `params` to `properties` (a menu's Edit properties).
    The panel is turned back to the graph in the editor once it shows them, even when `show` or `setting` fails (the
    module docstring). Returns what `setting` returns: what it set, with what the panel then shows ('tiling 2 (the
    Parameters panel back on g)', or with no graph in the editor 'tiling 2 (the Parameters panel shows the 3D
    material's properties)'), and whether it changed what the view shows. An error turning the panel back once
    `setting` returned is raised again with what it set (REVIEW.md HLP-204). One after `setting` failed keeps
    `setting`'s error, which may say what was set, with the turn-back's after it (REVIEW.md HLP-206)."""
    shown = params.windowTitle()
    said: str | None = None
    failed: Exception | APIException | None = None  # the setting's own error
    try:  # `show` included: an abort landing as Edit properties is triggered, or right after
        show()
        said, changed = setting()
    except (Exception, APIException) as e:  # the sd API's error is a BaseException too
        failed = e
        raise
    finally:
        try:
            _switched(params, shown)
            panel = _parameters_back()
        except (Exception, APIException) as e:
            if said is not None:
                raise _with_set(e, said) from e
            if failed is not None:
                raise RuntimeError('%s; and turning the Parameters panel back failed: %s' % (failed, e)) from e
            raise
    return '%s (%s)' % (said, panel or 'the Parameters panel shows ' + properties), changed


def _set_tiling(
    params: QtWidgets.QDockWidget, bar: QtWidgets.QMenuBar, value: float, keep: list[Kept], watched: _Frames
) -> tuple[str, bool]:
    """The 3D material's tiling, through the Parameters panel `params`, which is turned back to the graph in the editor
    once it shows the material, even when setting the tiling fails (_in_properties); what was set, and whether it
    changed (a tiling shown already isn't committed: _commit_change). Its change is waited for on `watched`, and an
    error in that wait says the tiling was set."""

    def setting() -> tuple[str, bool]:
        shown, since = _commit_change(lambda: _tiling_spin(params, keep), value, "the 3D material's Tiling", watched)
        said = 'tiling %g' % shown
        if since is not None:
            try:
                watched.settled(since)
            except (Exception, APIException) as e:  # the sd API's error is a BaseException too
                raise _with_set(e, said) from e
        return said, since is not None

    return _in_properties(
        params,
        lambda: _menu_action(bar, keep, 'Materials', _material(bar, keep), 'Edit properties').trigger(),
        setting,
        "the 3D material's properties",
    )


def _environment_maps() -> dict[str, str]:
    """Designer's own environment maps, which its Library lists under 3D view > HDRI environments: each file's name
    without its extension, to its path, in alphabetical order whatever the case."""
    folder = os.path.join(_APP.getPath(SDApplicationPath.DefaultResourcesDir), 'view3d', 'maps')
    names = sorted(os.listdir(folder), key=str.lower)
    return {os.path.splitext(name)[0]: os.path.join(folder, name) for name in names}


def _environment_said(name: str | None, rotation: float | None, exposure: float | None) -> str:
    """The environment set, as said: 'environment studio, rotation 90 degrees, exposure 1', with what is given."""
    said = [name] if name is not None else []
    said += ['rotation %g degrees' % rotation] if rotation is not None else []
    said += ['exposure %g' % exposure] if exposure is not None else []
    return 'environment ' + ', '.join(said)


def _drop(viewport: QtWidgets.QWidget, path: str) -> None:
    """The file `path` dragged onto the middle of the 3D `viewport`, as from the Library: entered, moved, dropped (the
    module docstring)."""
    data = QtCore.QMimeData()
    data.setUrls([QtCore.QUrl.fromLocalFile(path)])
    at = QtCore.QPoint(viewport.width() // 2, viewport.height() // 2)
    link = QtCore.Qt.DropAction.LinkAction
    none, plain = QtCore.Qt.MouseButton.NoButton, QtCore.Qt.KeyboardModifier.NoModifier
    app = QtWidgets.QApplication
    app.sendEvent(viewport, QtGui.QDragEnterEvent(at, link, data, none, plain))
    app.sendEvent(viewport, QtGui.QDragMoveEvent(at, link, data, none, plain))
    app.sendEvent(viewport, QtGui.QDropEvent(QtCore.QPointF(at), link, data, none, plain))


def _drop_map(viewport: QtWidgets.QWidget, field: QtWidgets.QWidget, name: str) -> bool:
    """Designer's environment map `name` (_environment_maps) dropped on the 3D `viewport`, and taken; whether the map
    changed: taken at its first drop. Dropped again after another, it was the one shown, and the view shows it as
    before. The Environment
    `field` of the Parameters panel signals each change of map (valueChanged()), within the drop. With no signal, the
    map was the one shown, or the drop wasn't taken: Designer's smallest other map is dropped, as Designer loads it
    within the drop, then `name` again, each to be signalled (the module docstring). Refused otherwise: when the other
    map isn't taken, and when `name` isn't taken back after it, saying the other is shown; and before any drop when the
    field has no valueChanged().

    The signal starts a flag, a timer of the drop's own: a C++ slot, so no Python runs as it comes, and a disconnect an
    abort skips leaves no function connected (REVIEW.md HLP-150). The flags' parent is held by this frame alone, and
    their connections go with it."""
    # the field's own signal, looked up first: without it no flag would ever start, though each drop changes the map
    # (REVIEW.md HLP-189)
    if field.metaObject().indexOfSignal('valueChanged()') < 0:
        raise RuntimeError('the Environment field has no valueChanged() signal, which says a map was taken')
    maps = _environment_maps()
    owner = QtCore.QObject()

    def dropped(map_name: str) -> bool:
        """The map `map_name` dropped: whether the field signalled a change within the drop."""
        flag = QtCore.QTimer(owner)
        flag.setSingleShot(True)
        flag.setInterval(FLAG_MS)
        # the field's own signal, which PySide's stubs don't know: connected by its signature
        QtCore.QObject.connect(field, QtCore.SIGNAL('valueChanged()'), flag, QtCore.SLOT('start()'))
        _drop(viewport, maps[map_name])
        return flag.isActive()

    if dropped(name):
        return True
    other = min((n for n in maps if n != name), key=lambda n: os.path.getsize(maps[n]))
    # said before its drop, as set_3d_view's steps are: an abort right after leaves the 3D view on it (REVIEW.md HLP-191)
    print(SETTING + 'environment %s first, then %s again' % (other, name))
    if not dropped(other):
        raise RuntimeError('the 3D view took no environment map dropped on it')
    if not dropped(name):
        raise RuntimeError("the 3D view didn't take %s again: it shows %s" % (name, other))
    return False


def _set_environment(
    params: QtWidgets.QDockWidget,
    bar: QtWidgets.QMenuBar,
    viewport: QtWidgets.QWidget,
    name: str | None,
    rotation: float | None,
    exposure: float | None,
    keep: list[Kept],
    watched: _Frames,
) -> tuple[str, bool]:
    """The 3D view's environment, through the Parameters panel `params` as Environment > Edit properties shows it:
    Designer's map `name` dropped on `viewport` (_drop_map), then the rotation in degrees and the exposure, each given
    or None. Each change is waited for on `watched` from right before it (_commit_change): one wait from before the
    first ended before the last was drawn, the view back at rest between them (REVIEW.md HLP-192). The panel is turned
    back to the graph in the editor once it shows the environment, even when a step fails
    (_in_properties). Returns what was set, the values as the spin boxes then show them, and whether it changed what the
    view shows: a map changed, or a value committed; an error after a change says what was set (REVIEW.md HLP-193)."""

    def setting() -> tuple[str, bool]:
        name_set: str | None = None
        rotation_set: float | None = None
        exposure_set: float | None = None
        changed = False  # what the view shows: a map changed, or a value committed
        try:
            if name is not None:
                field = _panel_field(params, 'environment_texture_name', 'the Environment field', keep, spins=0)
                with _Waiting(watched) as waiting:
                    # asked again, the map shown is dropped back after another: the view restarts nothing, and the
                    # wait would run to its limit (REVIEW.md HLP-201)
                    waiting.needed = changed = _drop_map(viewport, field, name)
                    name_set = name  # before its wait: an error there says the map was set (REVIEW.md HLP-200)
            if rotation is not None:
                turned = "the environment's Rotation Angle"
                rotation_set, committed = _commit_change(  # said before its wait
                    lambda: _panel_spin(params, 'dome_rotation_angle', turned, keep, 1), rotation, turned, watched
                )  # Degrees
                if committed is not None:
                    changed = True
                    watched.settled(committed)
            if exposure is not None:
                brightened = "the environment's Exposure"
                exposure_set, committed = _commit_change(
                    lambda: _panel_spin(params, 'intensity', brightened, keep), exposure, brightened, watched
                )
                if committed is not None:
                    changed = True
                    watched.settled(committed)
        except (Exception, APIException) as e:  # the sd API's error is a BaseException too
            if (name_set, rotation_set, exposure_set) == (None, None, None):
                raise
            raise _with_set(e, _environment_said(name_set, rotation_set, exposure_set)) from e
        return _environment_said(name_set, rotation_set, exposure_set), changed

    return _in_properties(
        params,
        lambda: _menu_action(bar, keep, 'Environment', 'Edit properties').trigger(),
        setting,
        "the environment's properties",
    )


def _navigation_tools(dock: QtWidgets.QDockWidget, keep: list[Kept]) -> tuple[QtGui.QAction, QtGui.QAction]:
    """The 3D view's toolbar's Camera and Light tools: drags and the wheel move the camera under the Camera tool alone
    (the module docstring)."""
    found = {a.text(): a for bar in dock.findChildren(QtWidgets.QToolBar) for a in bar.actions() if a.text() in TOOLS}
    for name in TOOLS:
        if name not in found:
            raise RuntimeError("the 3D view's toolbar has no %s tool" % name)
    keep += found.values()
    return found['Camera'], found['Light']


def _tool_back(light: QtGui.QAction, switched: bool) -> None:
    """The Light tool selected again if it was before the Camera tool was (`switched`) and isn't now."""
    if switched and not light.isChecked():
        light.trigger()
        _process_events()


WAYS = (('right', 'left'), ('up', 'down'))  # [right, up]'s values said, positive and negative


def _directions(values: Sequence[float], unit: str) -> str:
    """[right, up] said, each value that isn't 0 with its direction, to 3 digits, `unit` after the first value:
    '90 degrees right, 30.1 up'."""
    said: list[str] = []
    for value, ways in zip(values, WAYS, strict=True):
        if value:
            said.append('%.3g%s %s' % (abs(value), '' if said else unit, ways[value < 0]))
    return ', '.join(said)


def _drags(
    option: str, values: Sequence[float], steps: tuple[float, float], unit: str
) -> tuple[list[tuple[int, int]], list[float]]:
    """The drags (dx, dy: right, down) carrying `values`, [right, up], `steps` what a pixel dragged left and up carries,
    [right, up] (REVIEW.md HLP-123), and the [right, up] they carry; a value that isn't 0 but rounds to no pixel is
    refused (the module docstring)."""
    pixels = [round(-values[0] / steps[0]), round(-values[1] / steps[1])]
    for value, pixel, step, ways in zip(values, pixels, steps, WAYS, strict=True):
        if value and not pixel:
            raise RuntimeError(
                "%s's %g%s %s is less than one pixel's drag, %.3g%s: it would do nothing"
                % (option, abs(value), unit, ways[value < 0], abs(step), unit)
            )
    drags = [d for d in ((pixels[0], 0), (0, pixels[1])) if d != (0, 0)]
    return drags, [-pixels[0] * steps[0], -pixels[1] * steps[1]]


def _orbit_drags(orbit: Sequence[float]) -> tuple[list[tuple[int, int]], list[float]]:
    """The left-drags turning the camera orbit[0] degrees right and orbit[1] up, and the degrees they turn: the mouse
    left turns it right, the mouse down raises it (the module docstring)."""
    return _drags('orbit', orbit, (ORBIT_ACROSS, -ORBIT_UP), ' degrees')


def _pan_drags(pan: Sequence[float], width: int, height: int) -> tuple[list[tuple[int, int]], list[float]]:
    """The middle-drags moving a `width` x `height` view pan[0] of its width right and pan[1] of its height up, and the
    fractions they move it: the content follows the mouse, a view's width every PAN_WIDTH pixels either way (the module
    docstring)."""
    return _drags('pan', pan, (1 / PAN_WIDTH, -width / (height * PAN_WIDTH)), ' of the view')


def _mouse(
    viewport: QtWidgets.QWidget,
    kind: QtCore.QEvent.Type,
    x: float,
    y: float,
    button: QtCore.Qt.MouseButton,
    buttons: QtCore.Qt.MouseButton,
) -> None:
    """One mouse event at (x, y) in `viewport`, as Designer takes them from the mouse, marked as sent here while it is
    (_OWN_MOUSE), so the guard of a drag lets it through (_mouse_guard)."""
    at = QtCore.QPointF(x, y)
    held = QtCore.Qt.KeyboardModifier.NoModifier
    event = QtGui.QMouseEvent(kind, at, QtCore.QPointF(viewport.mapToGlobal(at.toPoint())), button, buttons, held)
    _OWN_MOUSE[0] = True
    try:
        QtWidgets.QApplication.sendEvent(viewport, event)
    finally:
        _OWN_MOUSE[0] = False
    _process_events(2)


def _mouse_guard() -> QtCore.QObject:
    """An event filter, for a viewport while a drag runs, dropping every mouse event (MOUSE_EVENTS) _mouse isn't
    sending: the user's mouse moving over it would end the drag (the module docstring)."""
    kinds: set[QtCore.QEvent.Type] = {getattr(QtCore.QEvent.Type, name) for name in MOUSE_EVENTS}

    class MouseGuard(QtCore.QObject):
        def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
            return not _OWN_MOUSE[0] and event.type() in kinds

    return MouseGuard()


def _release(viewport: QtWidgets.QWidget, button: QtCore.Qt.MouseButton, x: float, y: float) -> None:
    """`button` released at (x, y) in `viewport`."""
    _mouse(viewport, QtCore.QEvent.Type.MouseButtonRelease, x, y, button, QtCore.Qt.MouseButton.NoButton)


def _drag(
    viewport: QtWidgets.QWidget,
    button: QtCore.Qt.MouseButton,
    dx: int,
    dy: int,
    pressed: Pressed,
    taking: Callable[[], Callable[[], bool]] | None = None,
) -> None:
    """A drag with `button` from the middle of `viewport`, dx and dy pixels (right, down), in DRAG_MOVES moves, then
    released, even when a move fails. `taking`, when given, runs before the press and returns the wait for Designer to
    take the drag, run after the release (_Frames.taking: a frame of the 3D view drawn once the drag's events ran;
    off screen, an UpdateRequest since the press). A guard on the viewport drops the user's mouse from before the press to the end of that wait
    (_mouse_guard). `pressed` holds (button, x, y), where it is
    released, from before the press to after the release: an abort skipping the release finds it there (set_3d_view's
    handler). The guard, held by this frame alone, goes with it after an abort that skips its removal."""
    x, y = viewport.width() / 2.0, viewport.height() / 2.0
    end = (button, x + dx, y + dy)
    guard = _mouse_guard()
    viewport.installEventFilter(guard)
    try:
        taken = taking() if taking is not None else None
        pressed.append(end)
        try:
            _mouse(viewport, QtCore.QEvent.Type.MouseButtonPress, x, y, button, button)
            for i in range(1, DRAG_MOVES + 1):
                at = (x + dx * i / DRAG_MOVES, y + dy * i / DRAG_MOVES)
                _mouse(viewport, QtCore.QEvent.Type.MouseMove, *at, QtCore.Qt.MouseButton.NoButton, button)
        finally:
            _release(viewport, *end)
            pressed.remove(end)
        if taken is not None:
            taken()
    finally:
        viewport.removeEventFilter(guard)


def _set_up_checked(
    graph: str | None, mesh: str | None, view: str | None, environment: str | None = None
) -> SDSBSCompGraph | None:
    """The graph `graph` names (None without one), once what the arguments alone rule out is refused: a mesh or view
    the 3D view's menus don't have (MESHES, VIEWS), an environment map Designer doesn't have (_environment_maps), and a
    graph with fewer than two outputs. Nothing in Designer's UI is looked at or changed."""
    if mesh is not None and mesh not in MESHES:
        raise RuntimeError('unknown mesh %r; the 3D view has %s' % (mesh, ', '.join(MESHES)))
    if view is not None and view not in VIEWS:
        raise RuntimeError('unknown view %r; the 3D view has %s' % (view, ', '.join(VIEWS)))
    if environment is not None and environment not in (maps := _environment_maps()):
        raise RuntimeError('unknown environment %r; Designer has %s' % (environment, ', '.join(maps)))
    g = find_graph(graph) if graph else None
    if g is not None:
        outputs = len(g.getOutputNodes())
        if not outputs:
            raise RuntimeError('graph %s has no outputs to show' % g.getIdentifier())
        if outputs == 1:
            raise RuntimeError(
                'graph %s has one output: Designer would ask which channel of the material to show it in; '
                'preview_node shows it' % g.getIdentifier()
            )
    return g


class _SetUp:
    """A set-up _3d_set_up checked: called with `between` and `frames`, it runs its steps (its `run`) and returns whether
    it changed what the view shows. `may_change`: whether it may, known before it runs (the camera moved, the mesh
    switched, the tiling or the light given), so a 3D shot takes a render before it to compare with (shot3d.py)."""

    def __init__(self, run: Callable[[Callable[[], None] | None, _Frames | None], bool], may_change: bool) -> None:
        self.run = run
        self.may_change = may_change

    def __call__(self, between: Callable[[], None] | None, frames: _Frames | None = None) -> bool:
        return self.run(between, frames)


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
    """set_3d_view checked, changing nothing: what the arguments rule out, the graph, the panels, the menu entries and
    the tools it needs, an orbit or pan of less than a pixel's drag; refused here (shoot_3d calls it before it puts
    Designer's window on screen: REVIEW.md HLP-127). Returns its steps, to run: set_3d_view's docstring. Given a
    watch, they run `between`, when given, before each step and after the viewpoint's turn, before Frame: the 3D
    shot's look whether the user made Designer the active app, which also puts the window on screen again if it went
    off screen (shot3d.py; REVIEW.md HLP-136, HLP-158, HLP-163). The shot gives its watch of the view's frames and its
    look, and keeps the window on screen itself (REVIEW.md HLP-174). Run without a watch, as set_3d_view runs them, the
    steps of a set-up that moves the camera, puts a graph's outputs on the mesh or switches the mesh run with the
    window on screen, transparent (_on_screen; REVIEW.md HLP-168, HLP-196, HLP-197), its own look in place of
    `between`. In any other set-up, only the viewpoint's turn and Frame do: off screen nothing says the turn ended
    (frames3d.py; REVIEW.md HLP-158). Each step waits for the 3D view to take it on the watch of its frames they are
    given, or on one of their own (frames3d.py; REVIEW.md HLP-148)."""
    g = _set_up_checked(graph, mesh, view, environment)
    lit = environment is not None or environment_rotation is not None or environment_exposure is not None
    mw = _main_window()
    keep: list[Kept] = [mw]
    dock = _3d_dock(mw)
    bars = dock.findChildren(QtWidgets.QMenuBar)
    if not bars:
        raise RuntimeError("the 3D View's menu bar wasn't found")
    bar = bars[0]
    viewport = _viewport(dock)  # refused when there is none
    keep += [dock, bar, viewport]
    orbit_drags, turned = _orbit_drags(orbit) if orbit else ([], [])
    pan_drags, panned = _pan_drags(pan, viewport.width(), viewport.height()) if pan else ([], [])
    moving = bool(orbit_drags or pan_drags or zoom)
    # the toolbar's tools, looked up only when a drag or the wheel goes to the viewport
    camera: QtGui.QAction | None = None
    light: QtGui.QAction | None = None
    if moving:
        camera, light = _navigation_tools(dock, keep)
    tree = _explorer_tree(mw, keep) if g is not None else None
    params = None
    # the options set through the Parameters panel, as given
    paneled = [
        name + '='
        for name, value in (
            ('tiling', tiling),
            ('environment', environment),
            ('environment_rotation', environment_rotation),
            ('environment_exposure', environment_exposure),
        )
        if value is not None
    ]
    if paneled:
        params = _visible_dock(mw, _PANEL_AREAS['parameters'])
        if params is None:
            *rest, last = paneled
            options, verb = ('%s and %s' % (', '.join(rest), last), 'go') if rest else (last, 'goes')
            raise RuntimeError(
                "%s %s through the Parameters panel, which isn't visible (Windows > Parameters)" % (options, verb)
            )
        keep.append(params)
    needed: list[tuple[str, ...]] = [('Scene', mesh)] if mesh is not None else []
    if view is not None:
        needed += [('Camera', view), ('Camera', 'Frame')]
    if tiling is not None:  # with mesh=, the new mesh's material, read as it shows (_set_tiling)
        needed.append(('Materials',) if mesh is not None else ('Materials', _material(bar, keep), 'Edit properties'))
    if lit:
        needed.append(('Environment', 'Edit properties'))
    for entry in needed:
        _menu_action(bar, keep, *entry)  # there; looked up again as it is used, after the mesh may have changed
    # what runs whole on screen when run on its own (run); a mesh checked in the Scene menu is shown already
    switching = mesh is not None and not _menu_action(bar, keep, 'Scene', mesh).isChecked()
    on_screen = moving or g is not None or switching

    def run(between: Callable[[], None] | None, frames: _Frames | None) -> bool:
        """The set-up's steps (steps). Given `frames`, the watch of a caller keeping the window on screen (the
        shot's), they run on it, `between` before each. Run on its own, with no `frames`, a set-up that moves the
        camera, puts a graph's outputs on the mesh or switches the mesh runs whole with Designer's window on screen,
        transparent and click-through, as a 3D shot sets up (_on_screen; set_3d_view's docstring). Before each step,
        the look that puts the window on screen again runs instead of `between`. Any other set-up runs off screen, but
        for a viewpoint's turn, `between` before each step. Returns whether it changed what the view shows (steps)."""
        if frames is not None:
            return steps(between, frames, True)
        watched = _frames_of(mw, viewport)
        try:
            if not on_screen:
                return steps(between, watched, False)
            with _on_screen(mw, watched) as screen:
                # before each step, the window put on screen again if it went off
                return steps(screen.again, watched, True)
        finally:
            watched.close()

    def steps(between: Callable[[], None] | None, watched: _Frames, kept: bool) -> bool:
        """The set-up's steps, checked by _3d_set_up, `between` run before each. Each waits for the 3D view to take
        it on `watched`, the caller's watch of its frames or run's own (frames3d.py; REVIEW.md HLP-174). `kept`:
        whether Designer's window is kept on screen meanwhile, by the caller (the shot's) or by run; if not, a
        viewpoint's turn puts it on screen itself. Returns whether it changed what the view shows: the camera moved,
        the mesh switched, the tiling or the light changed (a value committed, a map taken at its first drop). A view
        or a graph may be what is shown already, so they don't count (shoot_3d's retakes)."""
        done: list[str] = []
        changed = False
        panel_begun = False  # the tiling or the environment begun: an abort's handler turns the Parameters panel back
        switched = False  # the Light tool was selected, the Camera tool selected for the drags and the wheel
        pressed: Pressed = []  # a drag's button down: _drag's own record

        def begin(step: str) -> str:
            """Says the step before its change: no abort can land between a change and its record (REVIEW.md
            HLP-119). `between` runs first."""
            if between is not None:
                between()
            print(SETTING + step)
            return step

        try:
            if mesh is not None:
                step = begin(mesh)
                picked = _menu_action(bar, keep, 'Scene', mesh)
                with _Waiting(watched) as waiting:
                    # checked, it is shown already: picked again, it restarts nothing, and the wait would run to its
                    # limit (REVIEW.md HLP-195)
                    waiting.needed = changed = not picked.isChecked()
                    if changed:
                        picked.trigger()
                    done.append(step)  # before its wait: an error there says the step was set (REVIEW.md HLP-200)
            if g is not None:
                step = begin("graph %s's outputs on the mesh" % g.getIdentifier())
                with _Waiting(watched):
                    g.compute()  # its outputs ready for the mesh
                    # the Explorer's tree was found above, as g was given
                    _apply_outputs(cast(QtWidgets.QTreeView, tree), g, keep)
                    done.append(step)  # before its wait (REVIEW.md HLP-200)
            if view is not None:
                step = begin('view %s, framed' % view)

                # off screen nothing says the camera's turn ended (frames3d.py): set up on its own, the window is
                # shown for it, transparent, as the 3D shot shows it; in a shot it is on screen already, looked at
                # before each step (`between`; REVIEW.md HLP-158, the user's choice)
                def turn(look: Callable[[], None] | None) -> None:
                    since = watched.mark()
                    _menu_action(bar, keep, 'Camera', view).trigger()
                    done.append('view %s' % view)  # before the waits: an error there says it (REVIEW.md HLP-200)
                    watched.moved(since)  # Frame at once cancels the camera's turn
                    # off screen meanwhile, moved() ended there: the look puts the window on screen again and
                    # waits for the view to settle there, which it does once the turn ends (REVIEW.md HLP-163)
                    if look is not None:
                        look()
                    with _Waiting(watched):
                        _menu_action(bar, keep, 'Camera', 'Frame').trigger()
                        done[-1] = step  # framed

                if kept:
                    turn(between)
                else:
                    with _on_screen(mw, watched) as screen:
                        turn(screen.again)
            if camera is not None and light is not None:  # moving: looked up above
                switched = light.isChecked()  # read before the change: an abort landing on it finds none
                # each option's moves are marked after its look (begin), which may put the window on screen again
                # and wait for the view's restart: from a mark before it, that restart ended the moves' wait
                # (REVIEW.md HLP-161). The last option's mark is the one waited from
                try:
                    if switched:
                        camera.trigger()
                        _process_events()
                    changed = True  # moving: a drag or a wheel step follows
                    if orbit_drags:
                        step = begin('orbit ' + _directions(turned, ' degrees'))
                        since = watched.mark()
                        for dx, dy in orbit_drags:
                            _drag(viewport, QtCore.Qt.MouseButton.LeftButton, dx, dy, pressed, watched.taking)
                        done.append(step)
                    if pan_drags:
                        step = begin('pan ' + _directions(panned, ' of the view'))
                        since = watched.mark()
                        for dx, dy in pan_drags:
                            _drag(viewport, QtCore.Qt.MouseButton.MiddleButton, dx, dy, pressed, watched.taking)
                        done.append(step)
                    if zoom:
                        step = begin('%+d wheel steps' % zoom)
                        since = watched.mark()
                        _wheel(viewport, zoom, watched.taking)
                        done.append(step)
                finally:
                    _tool_back(light, switched)
                watched.settled(since)
            if tiling is not None:
                begin('tiling %g' % tiling)
                panel_begun = True
                # the Parameters panel was found above, as tiling was given; its change is waited for in the step
                said, tiled = _set_tiling(cast(QtWidgets.QDockWidget, params), bar, tiling, keep, watched)
                done.append(said)
                changed |= tiled
            if lit:
                light_set = (environment, environment_rotation, environment_exposure)
                begin(_environment_said(*light_set))
                panel_begun = True
                # the Parameters panel was found above, as the environment was given; each change is waited for
                # in the step, from right before it (REVIEW.md HLP-192)
                panel = cast(QtWidgets.QDockWidget, params)
                said, lit_changed = _set_environment(panel, bar, viewport, *light_set, keep, watched)
                done.append(said)
                changed |= lit_changed
            print('3D view: ' + ', '.join(done))
            return changed
        except (Exception, APIException) as e:  # the sd API's error is a BaseException too
            if not done:
                raise
            raise RuntimeError('%s; the 3D view was already set: %s' % (e, ', '.join(done))) from e
        except (
            BaseException
        ):  # an abort (the plugin's ScriptAborted): its steps said as begun; this handler runs untraced
            for button, x, y in pressed:  # one landing on a drag's finally skipped its release
                _release(viewport, button, x, y)
            if light is not None:  # or the Light tool's way back
                _tool_back(light, switched)
            if panel_begun:  # one landing on _set_tiling's or _set_environment's finally skipped its turn-back
                _parameters_back()
            raise

    return _SetUp(run, moving or switching or tiling is not None or lit)


def set_3d_view(
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
) -> None:
    """Set up the 3D view as the user sees it too: `graph`'s outputs on the mesh, the mesh (MESHES), the viewpoint
    (VIEWS, then framed), the camera turned `orbit` [right, up] degrees around the point it looks at and moved `pan`
    [right, up] fractions of the view sideways, `zoom` wheel steps closer (negative: away), in that order, the
    material's tiling, then the environment: one of Designer's maps (_environment_maps), its rotation in degrees and its
    exposure. The graph, the panels, the menu entries and the tools it needs are checked before anything
    changes (with mesh=, the new mesh's material once it shows). Prints '3D view, setting: <step>' before each change,
    so an abort leaves the steps it began said; an error after a change says what was set; then one line,
    '3D view: ...', of what it set. Where the view shows no count (Display > Samples off), each step's wait on screen
    compares renders, taken through the clipboard: only the user's clipboard text is put back, as for a 3D screenshot
    (DECISIONS.md; REVIEW.md HLP-152). Off screen it takes none (REVIEW.md HLP-170).
    The whole set-up runs with Designer's window on screen, transparent and click-through, as a 3D screenshot sets up
    (_on_screen), when it does any of these (the user's choices; DECISIONS.md):
    - orbit, pan or zoom: off screen, the same moves came out differently between runs (frames3d.py; REVIEW.md
      HLP-168);
    - graph: off screen, the Explorer's menu unhid a hidden Designer and left it up (REVIEW.md HLP-196);
    - a mesh switch: off screen, its step ends before the view took the switch, and a tiling set after it, in the same
      call or the next, had its field deleted as it was set (REVIEW.md HLP-197).
    Otherwise only a viewpoint's turn runs on screen (_3d_set_up)."""
    _3d_set_up(  # checked first, the window not changed yet
        graph, mesh, view, zoom, tiling, orbit, pan, environment, environment_rotation, environment_exposure
    )(None, None)
