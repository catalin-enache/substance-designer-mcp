"""The editor: opening graphs, the Home screen, fitting the view, create_graph, move_nodes."""

from .core import (
    _APP,
    _PM,
    Any,
    APIException,
    SDApplicationPath,
    SDProperty,
    SDPropertyCategory,
    SDSBSCompGraph,
    SDUIMgr,
    Sequence,
    _current_graph,
    _same_graph,
    cast,
    find_graph,
    node_kind,
    os,
)
from .edits import _node
from .layout import _nodes_bbox
from .screenshots import _PANEL_AREAS, _graph_view, _visible_dock


def _process_events(n: int = 10) -> None:
    from PySide6 import QtWidgets

    for _ in range(n):
        cast(QtWidgets.QApplication, QtWidgets.QApplication.instance()).processEvents()


def _fit_graph_view() -> bool:
    """Trigger the graph view's own 'Fit in view (selection)' (F): it fits the user's selection, or
    the whole graph when nothing is selected. Returns False if the action can't be found. Not used
    by open_graph, which fits all nodes by wheel zoom (REVIEW.md HLP-32); the self-test measures it."""
    from PySide6 import QtWidgets

    mw = _APP.getQtForPythonUIMgr().getMainWindow()  # type: ignore[no-untyped-call]  # sd: no annotations
    dock = _visible_dock(mw, _PANEL_AREAS['graph'])
    if dock is None:
        return False
    for bar in dock.findChildren(QtWidgets.QToolBar):
        for action in bar.actions():
            if action.text() == 'Fit in view (selection)':
                action.trigger()
                _process_events()
                return True
    return False


def _home_screen() -> tuple[Any, Any, Any] | None:  # Qt widgets: Any, see screenshots._visible_dock
    """Designer's window is a stack: the main window (panels) and the Home screen. While Home
    is showing, every panel counts as invisible. Returns (stack, home page, its 'Close home
    screen' button), or None. Keep all three referenced while using the button, or PySide
    reports it as already deleted."""
    from PySide6 import QtWidgets

    for top in cast(QtWidgets.QApplication, QtWidgets.QApplication.instance()).topLevelWidgets():
        if isinstance(top, QtWidgets.QStackedWidget) and top.isVisible():
            page = top.currentWidget()
            for button in page.findChildren(QtWidgets.QAbstractButton) if page is not None else []:
                if button.objectName() == 'close_btn':
                    return top, page, button
    return None


def _visible_panels() -> int:
    from PySide6 import QtWidgets

    count = 0
    for d in cast(QtWidgets.QApplication, QtWidgets.QApplication.instance()).allWidgets():
        try:
            count += isinstance(d, QtWidgets.QDockWidget) and d.objectName().startswith('area') and d.isVisible()
        except RuntimeError:  # a wrapper whose widget is gone (AGENTS.md, Designer UI)
            pass
    return count


def leave_home_screen() -> None:
    home = _home_screen()
    if home is None:
        return
    stack, page, button = home
    before = _visible_panels()  # 0 while Home shows (AGENTS.md; measured here, REVIEW.md TST-64)
    button.click()  # Designer's own "Close home screen"
    _process_events()
    if stack.currentWidget() is page:
        raise RuntimeError("could not close Designer's Home screen")
    print('closed the Home screen; panels visible: %d before, %d after' % (before, _visible_panels()))


def _fit_area(
    g: SDSBSCompGraph, node_ids: list[str] | None = None, frame: str | None = None, rect: Sequence[float] | None = None
) -> tuple[float, float, float, float, str]:
    """(x, y, w, h) in graph units: a frame (by title), the nodes' bounding box, or rect."""
    if frame is not None:
        from sd.api.sdgraphobjectframe import SDGraphObjectFrame

        frames = [o for o in g.getGraphObjects() if isinstance(o, SDGraphObjectFrame)]
        found = [f for f in frames if f.getTitle() == frame] or [
            f for f in frames if f.getTitle().lower() == str(frame).lower()
        ]
        if len(found) != 1:
            raise RuntimeError(
                '%s frame titled %r; frames: %s'
                % ('more than one' if found else 'no', frame, ', '.join(repr(f.getTitle()) for f in frames) or 'none')
            )
        pos, size = found[0].getPosition(), found[0].getSize()
        return pos.x, pos.y, size.x, size.y, 'frame %r' % found[0].getTitle()
    if node_ids:
        nodes, (left, top, right, bottom) = _nodes_bbox(g, node_ids)
        return left, top, right - left, bottom - top, '%d node(s)' % len(nodes)
    x, y, w, h = (float(v) for v in cast(Sequence[float], rect))  # the callers pass one of the three
    if w <= 0 or h <= 0:
        raise RuntimeError('rect is [x, y, width, height] with a positive width and height')
    return x, y, w, h, 'rect'


FIT_MAX_ZOOM = 1.0  # 100 %: a node at its normal size, never larger
FIT_PADDING = 0.05  # of the fitted area, on every side


def _wheel_zoom(view: Any, notches: int) -> None:
    """Zoom the graph view by mouse-wheel notches (positive: in), through Designer's own wheel
    handling. Designer keeps its own zoom level besides the view's transform: setting the
    transform directly (fitInView, scale) leaves that level stale, and the user's next wheel
    step jumps from it. Wheel events keep the two in step (Designer 16: 1.2x per notch)."""
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication

    viewport = view.viewport()
    centre = QPointF(viewport.width() / 2.0, viewport.height() / 2.0)
    event = QWheelEvent(
        centre,
        QPointF(viewport.mapToGlobal(centre.toPoint())),
        QPoint(0, 0),
        QPoint(0, 120 if notches > 0 else -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    for _ in range(abs(notches)):
        QApplication.sendEvent(viewport, event)
        _process_events(2)


def _whole_graph_rect(g: SDSBSCompGraph) -> tuple[float, float, float, float, str] | None:
    """(x, y, w, h, description) around every node, frame and free comment of g (a comment has a
    position but no size; one attached to a node sits with it), or None for an empty graph."""
    from sd.api.sdgraphobjectcomment import SDGraphObjectComment
    from sd.api.sdgraphobjectframe import SDGraphObjectFrame

    nodes = list(g.getNodes())
    frames = [o for o in g.getGraphObjects() if isinstance(o, SDGraphObjectFrame)]
    comments = [o for o in g.getGraphObjects() if isinstance(o, SDGraphObjectComment) and o.getParent() is None]
    boxes = [
        (o.getPosition().x, o.getPosition().y, o.getPosition().x + 1, o.getPosition().y + 1) for o in comments
    ]  # REVIEW.md HLP-39
    if nodes:
        boxes.append(_nodes_bbox(g, [n.getIdentifier() for n in nodes])[1])
    for f in frames:
        pos, size = f.getPosition(), f.getSize()
        boxes.append((pos.x, pos.y, pos.x + size.x, pos.y + size.y))
    if not boxes:
        return None
    left, top = min(b[0] for b in boxes), min(b[1] for b in boxes)
    right, bottom = max(b[2] for b in boxes), max(b[3] for b in boxes)
    return (
        left,
        top,
        right - left,
        bottom - top,
        'the whole graph (%d node(s), %d frame(s), %d comment(s))' % (len(nodes), len(frames), len(comments)),
    )


def _fit_view_to(
    g: SDSBSCompGraph,
    node_ids: list[str] | None = None,
    frame: str | None = None,
    rect: Sequence[float] | None = None,
    what: str | None = None,
) -> None:
    """Fit the graph view to part of g, zooming only with wheel notches (see _wheel_zoom): the
    largest zoom, at most FIT_MAX_ZOOM, at which the area fits; then pan to its centre. The
    view found is whichever graph view is visible, so first make sure the editor's current
    graph is g (same identifier and package)."""
    from PySide6.QtCore import QRectF

    current = _current_graph()
    if (
        current is None
        or current.getIdentifier() != g.getIdentifier()
        or current.getPackage().getUID() != g.getPackage().getUID()
    ):
        raise RuntimeError(
            'the graph in the editor is %s, not %s; not fitting the wrong view'
            % (current.getIdentifier() if current is not None else 'none', g.getIdentifier())
        )
    x, y, w, h, area_name = _fit_area(g, node_ids, frame, rect)
    what = what or area_name
    # keeps the view's wrappers alive
    mw = _APP.getQtForPythonUIMgr().getMainWindow()  # type: ignore[no-untyped-call]  # sd: no annotations
    view = _graph_view(mw)
    if view is None:
        raise RuntimeError('the graph view is not visible in Designer')
    pad = max(w, h) * FIT_PADDING + 20.0
    area = QRectF(x - pad, y - pad, w + 2 * pad, h + 2 * pad)
    viewport = view.viewport()
    target = min(FIT_MAX_ZOOM, viewport.width() / area.width(), viewport.height() / area.height())

    def zoom() -> float:
        return cast(float, view.transform().m11())

    for _ in range(80):  # out until it fits (a stuck zoom ends the loop)
        before = zoom()
        if before <= target * 1.001:
            break
        _wheel_zoom(view, -1)
        if zoom() == before:
            break
    for _ in range(80):  # in while the next notch still fits
        before = zoom()
        _wheel_zoom(view, 1)
        if zoom() > target * 1.001:
            _wheel_zoom(view, -1)
            break
        if zoom() == before:
            break
    view.centerOn(area.center())  # panning leaves the zoom level alone
    _process_events()
    seen = view.mapToScene(viewport.rect()).boundingRect()
    print(
        'fitted %s: zoom %d%%, visible %d,%d to %d,%d'
        % (what, round(zoom() * 100), seen.left(), seen.top(), seen.right(), seen.bottom())
    )


def open_graph(
    identifier: str | SDSBSCompGraph | None,
    node_id: str | None = None,
    node_ids: list[str] | None = None,
    frame: str | None = None,
    rect: Sequence[float] | None = None,
) -> None:
    """Open a graph in Designer's graph editor; fit the view to a frame, nodes or a rectangle,
    or centre it on one node; by default fit the whole graph."""
    g = find_graph(identifier)
    leave_home_screen()  # otherwise the graph opens behind it
    ui = cast(SDUIMgr, _APP.getUIMgr())  # Designer runs with its UI
    ui.openResourceInEditor(g)
    _process_events()
    print('opened', g.getIdentifier())
    if node_ids or frame is not None or rect is not None:
        _fit_view_to(g, node_ids, frame, rect)
        return
    if not node_id:
        # every node and frame, by wheel zoom: Designer's own "Fit in view (selection)" fits only the
        # user's selection when there is one (REVIEW.md HLP-32). The graph is open whatever the fit
        # does, so a failed fit is reported, not raised (HLP-35)
        current = _current_graph()
        if not _same_graph(current, g):
            # the open didn't do what was asked: an error, not a fit to report (REVIEW.md HLP-38)
            raise RuntimeError(
                'the graph in the editor is %s, not %s, after opening it'
                % (current.getIdentifier() if current is not None else 'none', g.getIdentifier())
            )
        area = _whole_graph_rect(g)
        if area:
            try:
                _fit_view_to(g, rect=area[:4], what=area[4])
            except (Exception, APIException) as e:
                print('could not fit the view: %s' % e)
    if node_id:
        node = _node(g, node_id)  # never the graph: focusGraphNode with it crashed Designer (REVIEW.md HLP-41)
        views = [ui.getGraphViewIDAt(i) for i in range(ui.getGraphViewIDCount())]
        views = [v for v in views if _same_graph(ui.getGraphFromGraphViewID(v), g)]
        if not views:
            raise RuntimeError('graph opened but no graph view shows it')
        ui.focusGraphNode(views[0], node)
        _process_events()
        print('focused node %s %s' % (node.getIdentifier(), node_kind(node)))


def create_graph(name: str, save_path: str | None = None, size_log2: int = 11) -> None:
    """New package with one compositing graph (fixed output size 2^size_log2)."""
    from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
    from sd.api.sdbasetypes import int2
    from sd.api.sdproperty import SDPropertyInheritanceMethod
    from sd.api.sdvalueint2 import SDValueInt2

    pkg = _PM.newUserPackage()
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier(name)
    prop = cast(SDProperty, g.getPropertyFromId('$outputsize', SDPropertyCategory.Input))  # every graph has it
    g.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
    g.setPropertyValue(prop, SDValueInt2.sNew(int2(size_log2, size_log2)))
    print('created graph %s (%d px)' % (name, 2**size_log2))
    if save_path:
        save_path = os.path.abspath(os.path.expanduser(save_path))
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        _PM.savePackageAs(pkg, save_path)
        print('saved package as', save_path)


def move_nodes(identifier: str | SDSBSCompGraph | None, positions: dict[str, Sequence[float]]) -> None:
    from sd.api.sdbasetypes import float2

    g = find_graph(identifier)
    moves = [(nid, _node(g, nid), x, y) for nid, (x, y) in positions.items()]  # all found first
    for nid, node, x, y in moves:
        node.setPosition(float2(float(x), float(y)))
        print('moved %s to (%d, %d)' % (nid, x, y))


def list_atomic() -> None:
    g = _current_graph()
    if not isinstance(g, SDSBSCompGraph):  # a function graph lists sbs::function::* instead
        g = None
    tmp = None
    if g is None:
        tmp = _PM.newUserPackage()
        g = SDSBSCompGraph.sNew(tmp)
    try:
        ids = sorted(d.getId() for d in g.getNodeDefinitions())
        print('RESOURCES_DIR=' + _APP.getPath(SDApplicationPath.DefaultResourcesDir))
        for i in ids:
            print('ATOMIC=' + i)
    finally:
        if tmp is not None:
            _PM.unloadUserPackage(tmp)
