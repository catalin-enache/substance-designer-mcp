"""Screenshots of Designer's panels, the 3D view's own render included."""

from .core import QtCore, QtGui, QtWidgets, _main_window, _menu, _qt_app, _ui
from .editor import _home_screen
from .mac_window import _mac_window
from .waits import _until

RENDER_LIMIT = 5.0  # s at most for Copy Render to Clipboard to put the render there: a safety net

PANELS = ('window', 'graph', '2d', '3d', 'explorer', 'parameters', 'library', 'console')
# Dock titles change with content ("dwarf_trimsheet", "Blend"), but their object names are stable
_PANEL_AREAS = {
    'explorer': 'areaA_',
    'graph': 'areaB_',
    'parameters': 'areaC_',
    '3d': 'areaD_',
    '2d': 'areaE_',
    'console': 'areaF_',
    'library': 'areaG_',
}


def _visible_dock(mw: QtWidgets.QMainWindow, prefix: str) -> QtWidgets.QDockWidget | None:
    for d in mw.findChildren(QtWidgets.QDockWidget):
        if d.objectName().startswith(prefix) and d.isVisible():
            return d
    return None


def _3d_dock(mw: QtWidgets.QMainWindow) -> QtWidgets.QDockWidget:
    """The 3D View's dock; refused when it isn't visible, or not built yet: Designer builds its menu bar and viewport
    once a graph is opened (REVIEW.md HLP-115)."""
    dock = _visible_dock(mw, _PANEL_AREAS['3d'])
    if dock is None:
        raise RuntimeError(
            'the 3D View panel is not visible in Designer'
            + (" (it's showing its Home screen; open_graph closes it)" if _home_screen() is not None else '')
        )
    if not dock.findChildren(QtWidgets.QMenuBar):
        raise RuntimeError("the 3D view isn't built yet: Designer builds it once a graph is opened (open_graph)")
    return dock


def _3d_render(mw: QtWidgets.QMainWindow) -> QtGui.QImage:
    """The 3D view's render, a QImage. The 3D view is GPU-drawn, so a QWidget.grab() of its viewport is leftover black
    or grey blocks, varying between calls. Use the view's own Camera > 'Copy Render to Clipboard' (the renderer's image,
    never screen pixels; its last frame while Designer's window is off screen: shot3d.py), then put back what Qt can
    copy of the user's clipboard: its text; the rest may be lost (DECISIONS.md, the user's choice). On macOS the text is
    then handed over to the pasteboard (mac_window.py, _MacWindow.hand_over_clipboard). The render is read once the clipboard
    says it changed (its dataChanged), at most RENDER_LIMIT."""
    app = _qt_app()
    dock = _3d_dock(mw)
    bars = dock.findChildren(QtWidgets.QMenuBar)
    if not bars:
        raise RuntimeError('3D View menu bar not found')
    # Keep Python references alive: Designer rebuilds these menus and stale wrappers raise
    keep: list[QtGui.QAction | QtWidgets.QMenu] = []
    copy_action = None
    for top in list(bars[0].actions()):
        if top.text().replace('&', '') != 'Camera':
            continue
        menu = _menu(top)  # the Camera menu
        keep += [top, menu]
        menu.aboutToShow.emit()  # menus are populated lazily
        app.processEvents()
        for action in menu.actions():
            if action.text().replace('&', '') == 'Copy Render to Clipboard':
                copy_action = action
                keep.append(action)
    if copy_action is None:
        raise RuntimeError("3D View has no 'Camera > Copy Render to Clipboard' action")

    clipboard = app.clipboard()
    mac = _mac_window(mw)
    original = clipboard.mimeData()
    saved = [(fmt, original.data(fmt)) for fmt in original.formats()] if original is not None else []  # None: none
    put = [False]

    def put_back() -> None:  # a QMimeData of its own each time: the clipboard takes it, and frees the one before
        backup = QtCore.QMimeData()
        for fmt, data in saved:
            backup.setData(fmt, data)
        clipboard.setMimeData(backup)
        if mac is not None:  # the pasteboard's at once, not Designer's to hand over when asked (REVIEW.md HLP-181)
            mac.hand_over_clipboard()
        put[0] = True

    try:
        try:
            clipboard.clear()
            copy_action.trigger()
            _until(lambda: not clipboard.image().isNull(), RENDER_LIMIT, [clipboard.dataChanged])
            image = clipboard.image()
            if image.isNull():
                raise RuntimeError('the 3D view did not produce a render (is a material shown?)')
            return image
        finally:
            put_back()
            app.processEvents()
    except BaseException:
        # the plugin raises an abort at a traced line, then stops tracing; landed on the `finally`'s first line, it
        # skipped the put-back. Here, untraced, it is put back unless it was: at worst twice, the same text (REVIEW.md
        # HLP-171)
        if not put[0]:
            put_back()
        raise


def _graph_view(mw: QtWidgets.QMainWindow) -> QtWidgets.QGraphicsView | None:
    """The graph editor's node view (a QGraphicsView in the graph dock; its scene coordinates
    are graph units), or None. The dock's title bar and toolbars are not part of it. The
    caller keeps `mw` (the main window) referenced while using the view, or PySide reports
    its wrappers as already deleted."""
    dock = _visible_dock(mw, _PANEL_AREAS['graph'])
    if dock is None:
        return None
    views = [v for v in dock.findChildren(QtWidgets.QGraphicsView) if v.isVisible()]

    def area(view: QtWidgets.QGraphicsView) -> int:
        return view.width() * view.height()

    return max(views, key=area) if views else None


def save_screenshot(panel: str, out_path: str) -> None:
    """Render one of Designer's own widgets to PNG with QWidget.grab(); not the 3D view, which shoot_3d renders.
    Screen/window grabs are deliberately not used: on macOS they copy whatever
    covers Designer, i.e. other apps. 'graph' is the node view alone, without the dock's
    title bar and toolbars."""
    mw = _main_window()
    if panel == '3d':
        raise RuntimeError("the 3D view is shot by shoot_3d, which puts Designer's window on screen first (shot3d.py)")
    widget: QtWidgets.QWidget
    if panel == 'window':
        widget = mw
    else:
        prefix = _PANEL_AREAS.get(panel)
        if prefix is None:
            raise RuntimeError('unknown panel %r; use one of %s' % (panel, ', '.join(PANELS)))
        docks = [
            d for d in mw.findChildren(QtWidgets.QDockWidget) if d.objectName().startswith(prefix) and d.isVisible()
        ]
        if not docks:
            if _home_screen() is not None:
                raise RuntimeError('Designer is showing its Home screen, which hides the panels; open_graph closes it')
            raise RuntimeError('panel %r is not visible in Designer (open it via the Windows menu)' % panel)
        widget = docks[0]
        if panel == 'graph':
            widget = _graph_view(mw) or widget
    _qt_app().processEvents()
    pixmap = widget.grab()
    if not pixmap.save(out_path):
        raise RuntimeError('could not save screenshot')
    current = _ui().getCurrentGraph()
    print(
        '%s %dx%d | graph in editor: %s'
        % (panel, pixmap.width(), pixmap.height(), current.getIdentifier() if current else None)
    )
