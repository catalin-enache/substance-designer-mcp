"""Screenshots of Designer's panels, the 3D view's own render included."""

from .core import _APP, Any, cast
from .editor import _home_screen

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


# Qt widgets are Any in signatures: annotations are evaluated when the helpers load, and a unit test
# (test_quit_fallback) loads them with a stand-in PySide6 that has no widget classes
def _visible_dock(mw: Any, prefix: str) -> Any:
    from PySide6 import QtWidgets

    for d in mw.findChildren(QtWidgets.QDockWidget):
        if d.objectName().startswith(prefix) and d.isVisible():
            return d
    return None


def _save_3d_render(mw: Any, out_path: str) -> tuple[int, int]:
    """The 3D view is GPU-drawn, so QWidget.grab() returns black. Use the view's own
    Camera > 'Copy Render to Clipboard' (the renderer's image, never screen pixels) and put
    the user's clipboard back afterwards."""
    import time

    from PySide6 import QtCore, QtWidgets

    app = cast(QtWidgets.QApplication, QtWidgets.QApplication.instance())  # Designer's own: always there
    dock = _visible_dock(mw, _PANEL_AREAS['3d'])
    if dock is None:
        raise RuntimeError(
            'the 3D View panel is not visible in Designer'
            + (" (it's showing its Home screen; open_graph closes it)" if _home_screen() is not None else '')
        )
    bars = dock.findChildren(QtWidgets.QMenuBar)
    if not bars:
        raise RuntimeError('3D View menu bar not found')
    # Keep Python references alive: Designer rebuilds these menus and stale wrappers raise
    keep: list[Any] = []
    copy_action = None
    for top in list(bars[0].actions()):
        if top.text().replace('&', '') != 'Camera':
            continue
        menu = cast(QtWidgets.QMenu, top.menu())  # the Camera menu
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
    original = clipboard.mimeData()
    backup = QtCore.QMimeData()
    for fmt in original.formats() if original is not None else []:  # None where Qt has no clipboard
        backup.setData(fmt, original.data(fmt))
    try:
        clipboard.clear()
        copy_action.trigger()
        image = None
        for _ in range(100):
            app.processEvents()
            image = clipboard.image()
            if not image.isNull():
                break
            time.sleep(0.05)
        if image is None or image.isNull():
            raise RuntimeError('the 3D view did not produce a render (is a material shown?)')
        if not image.save(out_path):
            raise RuntimeError('could not save the 3D render')
        return image.width(), image.height()
    finally:
        clipboard.setMimeData(backup)
        app.processEvents()


def _graph_view(mw: Any) -> Any:
    """The graph editor's node view (a QGraphicsView in the graph dock; its scene coordinates
    are graph units), or None. The dock's title bar and toolbars are not part of it. The
    caller keeps `mw` (the main window) referenced while using the view, or PySide reports
    its wrappers as already deleted."""
    from PySide6 import QtWidgets

    dock = _visible_dock(mw, _PANEL_AREAS['graph'])
    if dock is None:
        return None
    views = [v for v in dock.findChildren(QtWidgets.QGraphicsView) if v.isVisible()]
    return max(views, key=lambda v: v.width() * v.height()) if views else None


def save_screenshot(panel: str, out_path: str) -> None:
    """Render one of Designer's own widgets to PNG with QWidget.grab(), or the 3D view via its
    own render. Screen/window grabs are deliberately not used: on macOS they copy whatever
    covers Designer, i.e. other apps. 'graph' is the node view alone, without the dock's
    title bar and toolbars."""
    from PySide6 import QtWidgets

    mw = _APP.getQtForPythonUIMgr().getMainWindow()  # type: ignore[no-untyped-call]  # sd: no annotations
    if panel == '3d':
        width, height = _save_3d_render(mw, out_path)
        print('3d render %dx%d (clipboard restored)' % (width, height))
        return
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
    cast(QtWidgets.QApplication, QtWidgets.QApplication.instance()).processEvents()
    pixmap = widget.grab()
    if not pixmap.save(out_path):
        raise RuntimeError('could not save screenshot')
    current = _APP.getQtForPythonUIMgr().getCurrentGraph()  # type: ignore[no-untyped-call]  # sd: no annotations
    print(
        '%s %dx%d | graph in editor: %s'
        % (panel, pixmap.width(), pixmap.height(), current.getIdentifier() if current else None)
    )
