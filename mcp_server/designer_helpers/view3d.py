"""The 3D view set up before screenshot_designer('3d') renders it: a graph's outputs on its mesh, the mesh, the
viewpoint, the zoom and the tiling (ROADMAP item 7). Designer's API has none of it (sd, Designer 16), so this drives the
view's own menus and widgets, as measured in a Designer an agent started (2026-11-12; the self-test's
editor_panels_and_fit checks what the tool relies on, lifecycle the first point below):

- Designer builds the 3D view's menu bar and viewport once a graph is opened (before, its dock has neither).
- The 3D view's menu bar: Scene lists the meshes (MESHES, among other entries), Camera the viewpoints (VIEWS) and
  Frame. Their actions trigger from code once the menu's aboutToShow has filled it, as the screenshot's Copy Render
  does. The camera turns to a viewpoint over a moment, and a Frame triggered at once cancels the turn, so it waits
  VIEW_TURN first.
- Zoom: wheel events on the viewport (the visible Alg::Gui3D::ViewportWidget), taken as from the mouse although the
  view is GPU-drawn: about 1.11x a step closer, 1.09x a step away, from wherever the camera is. Sent back to back,
  some are dropped, so they go WHEEL_PAUSE apart.
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


def set_3d_view(
    graph: str | None = None,
    mesh: str | None = None,
    view: str | None = None,
    zoom: int = 0,
    tiling: float | None = None,
) -> None:
    """Set up the 3D view as the user sees it too: `graph`'s outputs on the mesh, the mesh (MESHES), the viewpoint
    (VIEWS, then framed), `zoom` wheel steps closer (negative: away) and the material's tiling. The graph, the panels
    and the menu entries it needs are checked before anything changes (with mesh=, the new mesh's material once it
    shows). Prints '3D view, setting: <step>' before each change, so an abort leaves the steps it began said; an error
    after a change says what was set; then one line, '3D view: ...', of what it set."""
    from PySide6 import QtWidgets

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
    keep += [dock, bar, viewports[0]]
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
        if zoom:
            step = begin('%+d wheel steps' % zoom)
            _wheel(viewports[0], zoom, WHEEL_PAUSE)
            done.append(step)
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
        if tiling_begun:  # one landing on _set_tiling's finally's first line skipped its turn-back
            _parameters_back()
        raise
