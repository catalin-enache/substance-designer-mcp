"""The menus the set-up drives (scene3d.py): the 3D view's own, and the Explorer's, which puts a graph's outputs on
the mesh (ROADMAP items 7 and 73); and what the set-up's arguments rule out. Designer's API has none of it (sd, Designer
16), so this drives the menus and widgets, as measured in a Designer an agent started (2026-11-12; the self-test's
editor_panels_and_fit checks what the tool relies on, lifecycle the first point below). The camera, the mesh, the
tiling and the environment go through the view's state file (scene3d.py, state3d.py).

- Designer builds the 3D view's menu bar and viewport once a graph is opened (before, its dock has neither).
- The 3D view's menu bar: Scene lists the meshes (MESHES, among other entries), Camera the viewpoints (VIEWS) and
  Frame. Their actions trigger from code once the menu's aboutToShow has filled it, as the screenshot's Copy Render
  does. Scene checks the mesh the view shows: the set-up reads the action of the mesh asked, and changes nothing for
  a mesh checked already.
- A graph's outputs reach the mesh as Designer switches to the graph (Preferences > Graph > Common, "View outputs in 3D
  view when opening a graph"), so outputs added to the graph open in the editor don't until it switches again. The
  Explorer's "View Outputs In 3D View" does, but only from its context menu: the action triggered by itself does
  nothing. So the graph is selected in the Explorer (setExplorerSelection, which the user sees, and which expands a
  collapsed package), the menu opened on its row with a QContextMenuEvent, and a timer picks the action while the
  menu runs, as soon as the menu shows: the action is there, enabled, at the first look (three menus, 2 to 6 ms after
  the event; 2026-11-15). A graph with one output makes Designer ask which channel to show it in, a second menu: such
  a graph is refused first.
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
- The Materials menu lists each material of the view, one Materials > Add added as "(unused)": the material the mesh
  uses is the one not so marked (_material_checked).
- Designer's own environment maps are the files of its resources' `view3d/maps` folder, which its Library lists under
  3D view > HDRI environments (_environment_maps).
- What a shot sets is put back after its render (scene3d.py).
"""

from .core import (
    _APP,
    Callable,
    Kept,
    QtCore,
    QtGui,
    QtWidgets,
    SDApplicationPath,
    SDSBSCompGraph,
    Sequence,
    _menu,
    _qt_app,
    _ui_mgr,
    cast,
    find_graph,
    os,
    sys,
)
from .editor import _process_events
from .mac_window import _MacWindow
from .screenshots import _PANEL_AREAS, _visible_dock
from .state3d import FRAMING, MAP_SCHEME, MATERIALS_USED, VIEW_DIRECTIONS

MESHES = tuple(FRAMING)  # the 3D view's Scene menu's meshes, in its order
VIEWS = tuple(VIEW_DIRECTIONS)  # its Camera menu's views
VIEW_OUTPUTS = 'View Outputs In 3D View'
MENU_GUARD = 5000  # ms the Explorer's context menu may stay open
MENU_TRIES = 3  # times the Explorer's context menu is opened when something closes it before its action is picked
SETTING = '3D view, setting: '  # a step said before its change (scene3d._3d_set_up); the server collects these


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


def _material_checked(bar: QtWidgets.QMenuBar, keep: list[Kept]) -> None:
    """Refused unless the mesh uses one material in the 3D view's Materials menu, one Designer lists as unused not
    counted (MATERIALS_USED): tiling= would set one of them."""
    menu = _menu(_menu_action(bar, keep, 'Materials'))
    keep.append(menu)
    menu.aboutToShow.emit()
    _process_events()
    used = [a for a in menu.actions() if a.menu() is not None and a.text() and '(unused)' not in a.text()]
    keep += used
    if len(used) != 1:
        names = [a.text().replace('&', '') for a in used]
        raise RuntimeError(MATERIALS_USED % (len(used), ' (%s)' % ', '.join(names) if names else ''))


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


def _environment_maps() -> dict[str, str]:
    """Designer's own environment maps (the module docstring): each file's name without its extension, to the URL the
    state file names the map by (state3d.MAP_SCHEME and the file's name), in alphabetical order whatever the case."""
    folder = os.path.join(_APP.getPath(SDApplicationPath.DefaultResourcesDir), 'view3d', 'maps')
    names = sorted(os.listdir(folder), key=str.lower)
    return {os.path.splitext(name)[0]: MAP_SCHEME + name for name in names}


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
