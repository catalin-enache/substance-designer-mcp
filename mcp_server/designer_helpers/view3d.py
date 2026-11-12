"""The 3D view set up before screenshot_designer('3d') renders it: a graph's outputs on its mesh, the mesh, the
viewpoint, the camera turned and panned, the zoom and the tiling (ROADMAP items 7 and 74). Designer's API has none of it
(sd, Designer 16), so this drives the view's own menus and widgets, as measured in a Designer an agent started
(2026-11-12; the self-test's editor_panels_and_fit checks what the tool relies on, lifecycle the first point below):

- Designer builds the 3D view's menu bar and viewport once a graph is opened (before, its dock has neither).
- The 3D view's menu bar: Scene lists the meshes (MESHES, among other entries), Camera the viewpoints (VIEWS) and
  Frame. Their actions trigger from code once the menu's aboutToShow has filled it, as the screenshot's Copy Render
  does. The camera turns to a viewpoint over a moment, and a Frame triggered at once cancels the turn, so it waits
  VIEW_TURN first.
- Zoom: wheel events on the viewport (the visible Alg::Gui3D::ViewportWidget), taken as from the mouse although the
  view is GPU-drawn: about 1.11x a step closer, 1.09x a step away, from wherever the camera is. Sent back to back,
  some are dropped, so they go WHEEL_PAUSE apart.
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
  after a drag zoomed less; so each drag is followed by DRAG_PAUSE. A mouse move with no button held, as the user's
  mouse sends over the viewport, ends a drag where it is: one after the 5th of 10 moves left orbit=[90, 0] 60 grey
  levels from Designer's Right view, and pan=[0.25, 0] at 0.099 of the view (REVIEW.md HLP-122). So while a drag
  runs, its pause included, a filter on the viewport drops every mouse event (MOUSE_EVENTS) _mouse isn't sending;
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
  a QContextMenuEvent, and a timer picks the action while the menu runs. A graph with one output makes Designer ask
  which channel to show it in, a second menu: such a graph is refused first.
- That menu is a new QMenu each time, with no parent, deleted once closed: nothing can be connected to it before it
  opens. An open menu holds the job, and with it the bridge, so a guard closes whatever popup is still open after
  MENU_GUARD ms, above any open before (the user's). An abort (a cancel, the job's timeout) raised in a Qt slot is
  dropped and raised again at the next Python line run (the plugin's _make_tracer), so the timer that picks the action
  closes its menu in a `finally`, and the guard is made of C callables only (_popup_closer). Both timers have a parent
  the function holds alone, so they go with it even when an abort lands in the `finally` that stops them: without one,
  a timer whose slot holds it outlives the function (the self-test's designer fact).
- Tiling is the 3D material's UVs > Tiling, shown in the Parameters panel by Materials > <material> > Edit properties.
  A material added to the mesh (Materials > Add) is listed as "(unused)", and isn't counted.
  Its spin box takes a value only through its own valueChanged() signal (neither setValue, Return, nor its slider's
  or editor's signals reach the material). The panel is then turned back to the graph in the editor by opening that
  graph again, once it shows the material: turned back before, the switch to the material came after.
- What is set stays: for the next shots, and in the user's 3D view.
"""

from .core import _APP, Any, APIException, SDUIMgr, _current_graph, cast, find_graph
from .editor import _process_events, _wheel
from .screenshots import _PANEL_AREAS, _3d_dock, _visible_dock

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
VIEW_TURN = 1.0  # s for the camera to turn to a viewpoint: Frame after 0.5 s kept it, at once undid it (2026-11-12)
WHEEL_PAUSE = 0.2  # s between wheel steps: sent back to back, the 3D view took 1 to 3 of 3 (2026-11-12)
MENU_GUARD = 5000  # ms the Explorer's context menu may stay open
ORBIT_ACROSS = 0.45  # degrees the camera turns a pixel dragged across (the module docstring)
ORBIT_UP = 0.35  # degrees a pixel dragged up or down
PAN_WIDTH = 356  # pixels dragged a view's width panned, at the point the camera looks at
DRAG_MOVES = 10  # mouse moves a drag is sent in: 1, 2, 10 or 40 turned the camera alike
DRAG_PAUSE = 0.2  # s after a drag, before the next one or the wheel (the module docstring)
TOOLS = ('Camera', 'Light')  # the 3D view's toolbar's tools a drag and the wheel go to, one group
# what the guard on the viewport drops during a drag unless _mouse is sending it (the module docstring)
MOUSE_EVENTS = ('MouseButtonPress', 'MouseButtonRelease', 'MouseButtonDblClick', 'MouseMove', 'Wheel')
_OWN_MOUSE = [False]  # _mouse sending an event


def _settle(seconds: float) -> None:
    """Let Designer process its events for a while (the 3D view redraws, a menu runs)."""
    import time

    from PySide6 import QtWidgets

    app = cast(QtWidgets.QApplication, QtWidgets.QApplication.instance())
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def _menu_action(bar: Any, keep: list[Any], *path: str) -> Any:
    """The action at `path` in the 3D view's menu bar (a menu, its submenus, the action), each menu filled first.
    `keep` holds the wrappers, which go stale once no Python reference is left (GUIDE.md, Designer UI)."""
    from PySide6 import QtWidgets

    app = cast(QtWidgets.QApplication, QtWidgets.QApplication.instance())
    actions = list(bar.actions())
    for i, name in enumerate(path):
        found = [a for a in actions if a.text().replace('&', '') == name]
        if not found:
            raise RuntimeError("the 3D view's %s has no %r" % (' > '.join(path[:i]) or 'menu bar', name))
        action = found[0]
        keep.append(action)
        if i == len(path) - 1:
            return action
        menu = action.menu()
        if menu is None:
            raise RuntimeError("the 3D view's %r is no menu" % ' > '.join(path[: i + 1]))
        keep.append(menu)
        menu.aboutToShow.emit()
        app.processEvents()
        actions = list(menu.actions())
    raise RuntimeError('no menu path given')


def _material(bar: Any, keep: list[Any]) -> str:
    """The name of the material the mesh uses in the 3D view's Materials menu ('Default (overridden)'), one Designer
    lists as unused not counted; refused for a mesh using several, as tiling= would set one of them."""
    menu = _menu_action(bar, keep, 'Materials').menu()
    keep.append(menu)
    menu.aboutToShow.emit()
    _process_events()
    materials = [a for a in menu.actions() if a.menu() is not None and a.text() and '(unused)' not in a.text()]
    keep += materials
    names = [cast(str, a.text().replace('&', '')) for a in materials]
    if len(names) != 1:
        raise RuntimeError(
            "the 3D view's mesh has %d materials%s; tiling= sets the material of a mesh with one"
            % (len(names), ': ' + ', '.join(names) if names else '')
        )
    return names[0]


def _row_point(tree: Any, row: Any, graph: str) -> Any:
    """The middle of the graph's `row` in the Explorer's tree, scrolled into view. Refused unless the row is there under
    that point: the context menu opens for whatever row lies there, and would apply another graph."""
    tree.scrollTo(row)
    _process_events()
    at = tree.visualRect(row).center()
    if not tree.viewport().rect().contains(at) or tree.indexAt(at) != row:
        raise RuntimeError("graph %s's row isn't showing in the Explorer (a filter?)" % graph)
    return at


class _MenuPick:
    """What _apply_outputs' pick timer does while the Explorer's context menu runs, and what went wrong, said after.
    `before` is the popup open before the menu, maybe the user's: never taken for it."""

    def __init__(self, action: str, before: Any) -> None:
        self.action = action
        self.before = before
        self.menus = 0  # menus pick found open
        self.disabled = False  # the action found disabled
        self.picked = False  # the action triggered in one

    def pick(self, menu: Any) -> bool:
        """In the menu opened since, trigger the action if enabled and close the menu, even when the trigger raises
        (an abort: the module docstring): True. No such menu yet (None, or `before`): False, so its timer looks
        again."""
        if menu is None or menu is self.before:
            return False
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

    def failure(self, graph: str, held: bool) -> str | None:
        """Why the outputs of `graph` may not be on the mesh, or None; `held`: the guard had to close a menu."""
        if not self.picked:
            return "the Explorer's menu for graph %s %s" % (
                graph,
                ('had %r disabled' if self.disabled else 'had no %r') % self.action if self.menus else "didn't open",
            )
        if held:
            return (
                'a menu was still open %d s after %r (Designer asking something more?), and was closed unanswered'
                % (
                    MENU_GUARD // 1000,
                    self.action,
                )
            )
        return None


def _popup_closer(active: Any, before: Any) -> Any:
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


def _explorer_tree(mw: Any, keep: list[Any]) -> Any:
    """The Explorer's tree, which graph= goes through; refused when the Explorer isn't visible."""
    from PySide6 import QtWidgets

    explorer = _visible_dock(mw, _PANEL_AREAS['explorer'])
    if explorer is None:
        raise RuntimeError("graph= goes through the Explorer panel, which isn't visible (Windows > Explorer)")
    trees = [v for v in explorer.findChildren(QtWidgets.QTreeView) if v.objectName() == 'mTreeView']
    if not trees:
        raise RuntimeError("the Explorer's tree wasn't found")
    keep += [explorer, trees[0]]
    return trees[0]


def _apply_outputs(tree: Any, graph: Any, keep: list[Any]) -> None:
    """The Explorer's "View Outputs In 3D View" for `graph`, from its context menu on the Explorer's `tree` (the module
    docstring)."""
    from PySide6 import QtCore, QtGui, QtWidgets

    app = QtWidgets.QApplication
    cast(SDUIMgr, _APP.getUIMgr()).setExplorerSelection(graph)  # Designer runs with its UI
    _process_events()
    rows = tree.selectionModel().selectedRows()
    if len(rows) != 1:
        raise RuntimeError(
            "graph %s wasn't selected in the Explorer (%d rows are)" % (graph.getIdentifier(), len(rows))
        )
    at = _row_point(tree, rows[0], graph.getIdentifier())
    before = app.activePopupWidget()  # a popup already open, maybe the user's: left alone
    keep.append(before)
    state = _MenuPick(VIEW_OUTPUTS, before)

    def pick() -> None:
        menu = app.activePopupWidget()
        menu = menu if isinstance(menu, QtWidgets.QMenu) else None
        keep.append(menu)
        if not state.pick(menu):
            timers[0].start(100)

    # the timers' parent, held by this frame alone: they go with it, whatever an abort lets run of the finally below
    owner = QtCore.QObject()
    timers: list[Any] = []
    try:  # from the first timer on: an abort landing as the second starts must stop the first
        # the guard: an open menu holds this job, and with it the bridge
        for run, after in ((pick, 100), (_popup_closer(app.activePopupWidget, before), MENU_GUARD)):
            timers.append(QtCore.QTimer(owner))
            timers[-1].setSingleShot(True)
            timers[-1].timeout.connect(run)
            timers[-1].start(after)
        viewport = tree.viewport()
        event = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Reason.Mouse, at, viewport.mapToGlobal(at))
        app.sendEvent(viewport, event)  # returns once the menu has closed
        held = not timers[1].isActive()  # the guard ran
    finally:
        for timer in timers:  # neither may act later, on a menu of the user's
            timer.stop()
    failure = state.failure(graph.getIdentifier(), held)
    if failure:
        raise RuntimeError(failure)


def _tiling_spin(params: Any, keep: list[Any]) -> Any:
    """The 3D material's Tiling spin box in the Parameters panel `params`, once Edit properties has shown it there."""
    from PySide6 import QtWidgets

    for _ in range(30):  # the panel builds its fields over a few event loops
        _settle(0.1)
        fields = [w for w in params.findChildren(QtWidgets.QWidget) if w.objectName() == '$tiling']
        spins = fields[0].findChildren(QtWidgets.QDoubleSpinBox) if fields else []
        if spins:
            keep.append(spins[0])
            return spins[0]
    raise RuntimeError("the 3D material's Tiling wasn't found in the Parameters panel")


def _parameters_back() -> str:
    """The Parameters panel turned back to the graph in the editor (the module docstring); what it shows."""
    current = _current_graph()
    if current is None:
        return "the Parameters panel shows the 3D material's properties"
    cast(SDUIMgr, _APP.getUIMgr()).openResourceInEditor(current)
    _process_events()
    return 'the Parameters panel back on %s' % current.getIdentifier()


def _switched(params: Any, shown: str) -> None:
    """Waits, up to 1 s, for the Parameters panel `params` to show something else than `shown`, its title before
    Edit properties: Designer switches it to the 3D material over a few event loops, so turned back before that (an
    abort landing early), it showed the material all the same."""
    for _ in range(10):
        if params.windowTitle() != shown:
            return
        _settle(0.1)


def _set_tiling(params: Any, bar: Any, value: float, keep: list[Any]) -> str:
    """The 3D material's tiling, through the Parameters panel `params`, which is turned back to the graph in the editor
    once it shows the material, even when setting the tiling fails (the module docstring); what was set."""
    from PySide6 import QtCore

    shown = params.windowTitle()
    try:  # Edit properties included: an abort landing as it is triggered, or right after
        _menu_action(bar, keep, 'Materials', _material(bar, keep), 'Edit properties').trigger()
        spin = _tiling_spin(params, keep)
        spin.setValue(value)
        # the spin box's own valueChanged(), no argument: QDoubleSpinBox's valueChanged(double) doesn't commit. PySide
        # takes the name as str (its stubs say bytes, which it refuses); False: no such signal, nothing committed
        if not QtCore.QMetaObject.invokeMethod(
            spin,
            'valueChanged',
            QtCore.Qt.ConnectionType.DirectConnection,  # type: ignore[call-overload]
        ):
            raise RuntimeError("the 3D material's Tiling didn't take %g: its spin box has no valueChanged()" % value)
        _process_events()
        tiling = spin.value()
    finally:
        _switched(params, shown)
        panel = _parameters_back()
    return 'tiling %g (%s)' % (tiling, panel)


def _navigation_tools(dock: Any, keep: list[Any]) -> tuple[Any, Any]:
    """The 3D view's toolbar's Camera and Light tools: drags and the wheel move the camera under the Camera tool alone
    (the module docstring)."""
    from PySide6 import QtWidgets

    found = {a.text(): a for bar in dock.findChildren(QtWidgets.QToolBar) for a in bar.actions() if a.text() in TOOLS}
    for name in TOOLS:
        if name not in found:
            raise RuntimeError("the 3D view's toolbar has no %s tool" % name)
    keep += found.values()
    return found['Camera'], found['Light']


def _tool_back(light: Any, switched: bool) -> None:
    """The Light tool selected again if it was before the Camera tool was (`switched`) and isn't now."""
    if switched and not light.isChecked():
        light.trigger()
        _process_events()


WAYS = (('right', 'left'), ('up', 'down'))  # [right, up]'s values said, positive and negative


def _directions(values: list[float], unit: str) -> str:
    """[right, up] said, each value that isn't 0 with its direction, to 3 digits, `unit` after the first value:
    '90 degrees right, 30.1 up'."""
    said: list[str] = []
    for value, ways in zip(values, WAYS, strict=True):
        if value:
            said.append('%.3g%s %s' % (abs(value), '' if said else unit, ways[value < 0]))
    return ', '.join(said)


def _drags(
    option: str, values: list[float], steps: tuple[float, float], unit: str
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


def _orbit_drags(orbit: list[float]) -> tuple[list[tuple[int, int]], list[float]]:
    """The left-drags turning the camera orbit[0] degrees right and orbit[1] up, and the degrees they turn: the mouse
    left turns it right, the mouse down raises it (the module docstring)."""
    return _drags('orbit', orbit, (ORBIT_ACROSS, -ORBIT_UP), ' degrees')


def _pan_drags(pan: list[float], width: int, height: int) -> tuple[list[tuple[int, int]], list[float]]:
    """The middle-drags moving a `width` x `height` view pan[0] of its width right and pan[1] of its height up, and the
    fractions they move it: the content follows the mouse, a view's width every PAN_WIDTH pixels either way (the module
    docstring)."""
    return _drags('pan', pan, (1 / PAN_WIDTH, -width / (height * PAN_WIDTH)), ' of the view')


def _mouse(viewport: Any, kind: Any, x: float, y: float, button: Any, buttons: Any) -> None:
    """One mouse event at (x, y) in `viewport`, as Designer takes them from the mouse, marked as sent here while it is
    (_OWN_MOUSE), so the guard of a drag lets it through (_mouse_guard)."""
    from PySide6 import QtCore, QtGui, QtWidgets

    at = QtCore.QPointF(x, y)
    held = QtCore.Qt.KeyboardModifier.NoModifier
    event = QtGui.QMouseEvent(kind, at, QtCore.QPointF(viewport.mapToGlobal(at.toPoint())), button, buttons, held)
    _OWN_MOUSE[0] = True
    try:
        QtWidgets.QApplication.sendEvent(viewport, event)
    finally:
        _OWN_MOUSE[0] = False
    _process_events(2)


def _mouse_guard() -> Any:
    """An event filter, for a viewport while a drag runs, dropping every mouse event (MOUSE_EVENTS) _mouse isn't
    sending: the user's mouse moving over it would end the drag (the module docstring)."""
    from PySide6 import QtCore

    kinds = {getattr(QtCore.QEvent.Type, name) for name in MOUSE_EVENTS}

    class MouseGuard(QtCore.QObject):
        def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
            return not _OWN_MOUSE[0] and event.type() in kinds

    return MouseGuard()


def _release(viewport: Any, button: Any, x: float, y: float) -> None:
    """`button` released at (x, y) in `viewport`."""
    from PySide6 import QtCore

    _mouse(viewport, QtCore.QEvent.Type.MouseButtonRelease, x, y, button, QtCore.Qt.MouseButton.NoButton)


def _drag(viewport: Any, button: Any, dx: int, dy: int, pressed: list[Any]) -> None:
    """A drag with `button` from the middle of `viewport`, dx and dy pixels (right, down), in DRAG_MOVES moves, then
    released, even when a move fails, and DRAG_PAUSE for Designer to take it; a guard on the viewport drops the user's
    mouse from before the press to after the pause (_mouse_guard). `pressed` holds (button, x, y), where it is
    released, from before the press to after the release: an abort skipping the release finds it there (set_3d_view's
    handler). The guard, held by this frame alone, goes with it after an abort that skips its removal."""
    from PySide6 import QtCore

    x, y = viewport.width() / 2.0, viewport.height() / 2.0
    end = (button, x + dx, y + dy)
    guard = _mouse_guard()
    viewport.installEventFilter(guard)
    try:
        pressed.append(end)
        try:
            _mouse(viewport, QtCore.QEvent.Type.MouseButtonPress, x, y, button, button)
            for i in range(1, DRAG_MOVES + 1):
                at = (x + dx * i / DRAG_MOVES, y + dy * i / DRAG_MOVES)
                _mouse(viewport, QtCore.QEvent.Type.MouseMove, *at, QtCore.Qt.MouseButton.NoButton, button)
        finally:
            _release(viewport, *end)
            pressed.remove(end)
        _settle(DRAG_PAUSE)
    finally:
        viewport.removeEventFilter(guard)


def set_3d_view(
    graph: str | None = None,
    mesh: str | None = None,
    view: str | None = None,
    zoom: int = 0,
    tiling: float | None = None,
    orbit: list[float] | None = None,
    pan: list[float] | None = None,
) -> None:
    """Set up the 3D view as the user sees it too: `graph`'s outputs on the mesh, the mesh (MESHES), the viewpoint
    (VIEWS, then framed), the camera turned `orbit` [right, up] degrees around the point it looks at and moved `pan`
    [right, up] fractions of the view sideways, `zoom` wheel steps closer (negative: away), in that order, and the
    material's tiling. The graph, the panels, the menu entries and the tools it needs are checked before anything
    changes (with mesh=, the new mesh's material once it shows). Prints '3D view, setting: <step>' before each change,
    so an abort leaves the steps it began said; an error after a change says what was set; then one line,
    '3D view: ...', of what it set."""
    from PySide6 import QtCore, QtWidgets

    if mesh is not None and mesh not in MESHES:
        raise RuntimeError('unknown mesh %r; the 3D view has %s' % (mesh, ', '.join(MESHES)))
    if view is not None and view not in VIEWS:
        raise RuntimeError('unknown view %r; the 3D view has %s' % (view, ', '.join(VIEWS)))
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
    mw = _APP.getQtForPythonUIMgr().getMainWindow()  # type: ignore[no-untyped-call]  # sd: no annotations
    keep: list[Any] = [mw]
    dock = _3d_dock(mw)
    bars = dock.findChildren(QtWidgets.QMenuBar)
    viewports = [
        w for w in dock.findChildren(QtWidgets.QWidget) if w.metaObject().className() == 'Alg::Gui3D::ViewportWidget'
    ]
    if not bars or not viewports:
        raise RuntimeError("the 3D View's menu bar or viewport wasn't found")
    bar = bars[0]
    viewport = viewports[0]
    keep += [dock, bar, viewport]
    orbit_drags, turned = _orbit_drags(orbit) if orbit else ([], [])
    pan_drags, panned = _pan_drags(pan, viewport.width(), viewport.height()) if pan else ([], [])
    moving = bool(orbit_drags or pan_drags or zoom)
    camera: Any = None  # the toolbar's tools, looked up only when a drag or the wheel goes to the viewport
    light: Any = None
    if moving:
        camera, light = _navigation_tools(dock, keep)
    tree = _explorer_tree(mw, keep) if g is not None else None
    params = None
    if tiling is not None:
        params = _visible_dock(mw, _PANEL_AREAS['parameters'])
        if params is None:
            raise RuntimeError("tiling= goes through the Parameters panel, which isn't visible (Windows > Parameters)")
        keep.append(params)
    needed: list[tuple[str, ...]] = [('Scene', mesh)] if mesh is not None else []
    if view is not None:
        needed += [('Camera', view), ('Camera', 'Frame')]
    if tiling is not None:  # with mesh=, the new mesh's material, read as it shows (_set_tiling)
        needed.append(('Materials',) if mesh is not None else ('Materials', _material(bar, keep), 'Edit properties'))
    for path in needed:
        _menu_action(bar, keep, *path)  # there; looked up again as it is used, after the mesh may have changed
    done: list[str] = []
    tiling_begun = False  # an abort's handler then turns the Parameters panel back
    switched = False  # the Light tool was selected, the Camera tool selected for the drags and the wheel
    pressed: list[Any] = []  # a drag's button down: (button, x, y)

    def begin(step: str) -> str:
        """Says the step before its change: no abort can land between a change and its record (REVIEW.md HLP-119)."""
        print('3D view, setting: ' + step)
        return step

    try:
        if mesh is not None:
            step = begin(mesh)
            _menu_action(bar, keep, 'Scene', mesh).trigger()
            _settle(0.5)
            done.append(step)
        if g is not None:
            step = begin("graph %s's outputs on the mesh" % g.getIdentifier())
            g.compute()  # its outputs ready for the mesh
            _apply_outputs(tree, g, keep)
            _settle(1.0)
            done.append(step)
        if view is not None:
            step = begin('view %s, framed' % view)
            _menu_action(bar, keep, 'Camera', view).trigger()
            _settle(VIEW_TURN)  # Frame at once cancels the camera's turn
            _menu_action(bar, keep, 'Camera', 'Frame').trigger()
            _settle(0.3)
            done.append(step)
        if moving:
            switched = light.isChecked()  # read before the change: an abort landing on it finds nothing changed
            try:
                if switched:
                    camera.trigger()
                    _process_events()
                if orbit_drags:
                    step = begin('orbit ' + _directions(turned, ' degrees'))
                    for dx, dy in orbit_drags:
                        _drag(viewport, QtCore.Qt.MouseButton.LeftButton, dx, dy, pressed)
                    done.append(step)
                if pan_drags:
                    step = begin('pan ' + _directions(panned, ' of the view'))
                    for dx, dy in pan_drags:
                        _drag(viewport, QtCore.Qt.MouseButton.MiddleButton, dx, dy, pressed)
                    done.append(step)
                if zoom:
                    step = begin('%+d wheel steps' % zoom)
                    _wheel(viewport, zoom, WHEEL_PAUSE)
                    done.append(step)
            finally:
                _tool_back(light, switched)
        if tiling is not None:
            begin('tiling %g' % tiling)
            tiling_begun = True
            done.append(_set_tiling(params, bar, tiling, keep))
        print('3D view: ' + ', '.join(done))
        _settle(0.5)
    except (Exception, APIException) as e:  # the sd API's error is a BaseException too
        if not done:
            raise
        raise RuntimeError('%s; the 3D view was already set: %s' % (e, ', '.join(done))) from e
    except BaseException:  # an abort (the plugin's ScriptAborted): its steps said as begun; this handler runs untraced
        for button, x, y in pressed:  # one landing on a drag's finally skipped its release
            _release(viewport, button, x, y)
        if light is not None:  # or the Light tool's way back
            _tool_back(light, switched)
        if tiling_begun:  # one landing on _set_tiling's finally's first line skipped its turn-back
            _parameters_back()
        raise
