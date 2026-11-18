"""Runs inside Designer: what the 3D view's environment does that screenshot_designer's environment options rely on
(designer_helpers/view3d.py), measured with code of its own:

- Environment > Edit properties shows the environment's fields in the Parameters panel, their object names ending in
  FIELDS: FIELDS= says which are missing.
- A value set in the Exposure spin box with setValue alone isn't taken: the panel shown again (turned to the graph in
  the editor, then to the environment) has the value from before (BEFORE=, SET_ONLY=). Invoking the spin box's own
  valueChanged() then takes it (COMMITTED=).
- A map's file dragged onto the 3D viewport (entered, moved, dropped) makes the Environment field signal valueChanged()
  once (SIGNALLED=, for ARGS' `second`, dropped after `first`), the same map dropped again not at all (AGAIN=), and
  `first` dropped again once (BACK=: the field still signals).
- `second` dropped alone, then entered and moved alone, with `first` shown, changes no map: neither signals (PARTIAL=).
- A Rotation Angle of 1.75 turns isn't wrapped: its Degrees spin box then reads 630 (TURNS=).
- Environment > Reset Environment puts the rotation and the exposure back to 0 (RESET=, the degrees and the exposure)
  and changes the map: `first`, the map shown before it, dropped after it signals once (RESET_MAP=).

The environment is reset after (Environment > Reset Environment), and the panel turned back to the graph in the editor,
whatever failed. ARGS: first, second: the names of two of Designer's maps."""

import os
import time
from typing import TypedDict, cast

import sd
from PySide6 import QtCore, QtGui, QtWidgets
from sd.api.qtforpythonuimgrwrapper import QtForPythonUIMgrWrapper
from sd.api.sdapplication import SDApplication, SDApplicationPath
from sd.api.sduimgr import SDUIMgr


class Args(TypedDict):
    first: str
    second: str


ARGS: Args = globals()['ARGS']
FIELDS = ('environment_texture_name', 'dome_rotation_angle', 'intensity')
app: SDApplication = sd.getContext().getSDApplication()
# sd's getQtForPythonUIMgr() has no annotations. It and getMainWindow() give None only without Designer's UI.
ui: QtForPythonUIMgrWrapper = app.getQtForPythonUIMgr()
mw = cast(QtWidgets.QMainWindow, ui.getMainWindow())
docks = mw.findChildren(QtWidgets.QDockWidget)
view3d = next(d for d in docks if d.objectName().startswith('areaD_'))
params = next(d for d in docks if d.objectName().startswith('areaC_') and d.isVisible())
bar = view3d.findChildren(QtWidgets.QMenuBar)[0]
viewport = next(
    w
    for w in view3d.findChildren(QtWidgets.QWidget)
    # className() is a str: PySide's stubs say bytes
    if cast(str, w.metaObject().className()) == 'Alg::Gui3D::ViewportWidget' and w.isVisible()
)
folder = os.path.join(app.getPath(SDApplicationPath.DefaultResourcesDir), 'view3d', 'maps')
keep: list[object] = [mw, view3d, params, bar, viewport]  # their wrappers go stale without (GUIDE.md, Designer UI)


def _settle(seconds: float) -> None:
    """Designer's events run for `seconds`: a poll's interval, where nothing says the panel built its fields."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()


def action(*path: str) -> QtGui.QAction:
    """The 3D view's menu action at `path`, each menu filled first."""
    actions = list(bar.actions())
    for i, name in enumerate(path):
        found = next(a for a in actions if a.text().replace('&', '') == name)
        keep.append(found)
        if i == len(path) - 1:
            return found
        menu = cast(QtWidgets.QMenu, found.menu())
        keep.append(menu)
        menu.aboutToShow.emit()
        QtWidgets.QApplication.processEvents()
        actions = list(menu.actions())
    raise RuntimeError('no menu path given')


def panel_back() -> None:
    """The Parameters panel turned back to the graph in the editor, by opening it again (as the helpers do)."""
    editor = ui.getCurrentGraph()
    if editor is not None:
        cast(SDUIMgr, app.getUIMgr()).openResourceInEditor(editor)
        QtWidgets.QApplication.processEvents()


def fields() -> dict[str, QtWidgets.QWidget]:
    """The environment's fields in the Parameters panel, by FIELDS' name, once Edit properties built them: 3 s at
    most. The panel is turned to the graph in the editor first, so they are built again from what the environment
    holds."""
    panel_back()
    action('Environment', 'Edit properties').trigger()
    found: dict[str, QtWidgets.QWidget] = {}
    for _ in range(30):
        _settle(0.1)
        found = {
            name: w
            for w in params.findChildren(QtWidgets.QWidget)
            for name in FIELDS
            if w.objectName().endswith('-' + name)
        }
        if len(found) == len(FIELDS) and found['intensity'].findChildren(QtWidgets.QDoubleSpinBox):
            break
    keep.extend(found.values())
    return found


def spin(shown: dict[str, QtWidgets.QWidget], name: str, index: int = 0) -> QtWidgets.QDoubleSpinBox:
    """The `index`-th spin box of the field `name` among the fields `shown`."""
    box = shown[name].findChildren(QtWidgets.QDoubleSpinBox)[index]
    keep.append(box)
    return box


def commit(box: QtWidgets.QDoubleSpinBox, value: float) -> None:
    """`value` set in the spin box `box` and taken through its own valueChanged()."""
    box.setValue(value)
    QtCore.QMetaObject.invokeMethod(
        box,
        'valueChanged',
        QtCore.Qt.ConnectionType.DirectConnection,  # type: ignore[call-overload]
    )
    QtWidgets.QApplication.processEvents()


signals: list[None] = []  # the Environment field's valueChanged(), counted
watched: list[QtWidgets.QWidget] = []  # the field counted, disconnected after


def count() -> None:
    signals.append(None)


def watch(field: QtWidgets.QWidget) -> None:
    """The Environment field's valueChanged() counted: the field's own signal, which PySide's stubs don't know,
    connected by its signature."""
    watched.append(field)
    QtCore.QObject.connect(field, QtCore.SIGNAL('valueChanged()'), count)


def disconnect() -> None:
    """The field counted disconnected: no function of this script left connected (REVIEW.md HLP-150)."""
    while watched:
        QtCore.QObject.disconnect(watched.pop(), QtCore.SIGNAL('valueChanged()'), count)


def drop(name: str, kinds: tuple[str, ...] = ('enter', 'move', 'drop')) -> int:
    """The map `name`'s file dragged onto the middle of the 3D viewport: entered, moved, dropped, or only the events
    `kinds` names. Returns how many times the field watched signalled within it."""
    before = len(signals)
    path = next(os.path.join(folder, f) for f in os.listdir(folder) if os.path.splitext(f)[0] == name)
    data = QtCore.QMimeData()
    data.setUrls([QtCore.QUrl.fromLocalFile(path)])
    keep.append(data)
    at = QtCore.QPoint(viewport.width() // 2, viewport.height() // 2)
    link, none, plain = (
        QtCore.Qt.DropAction.LinkAction,
        QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    events: dict[str, QtCore.QEvent] = {
        'enter': QtGui.QDragEnterEvent(at, link, data, none, plain),
        'move': QtGui.QDragMoveEvent(at, link, data, none, plain),
        'drop': QtGui.QDropEvent(QtCore.QPointF(at), link, data, none, plain),
    }
    for kind in kinds:
        QtWidgets.QApplication.sendEvent(viewport, events[kind])
    return len(signals) - before


try:
    shown = fields()
    print('FIELDS=missing %s' % sorted(set(FIELDS) - set(shown)))
    box = spin(shown, 'intensity')
    print('BEFORE=%g' % box.value())
    box.setValue(1.5)
    QtWidgets.QApplication.processEvents()
    print('SET_ONLY=%g' % spin(fields(), 'intensity').value())  # shown again
    commit(spin(fields(), 'intensity'), 1.5)
    print('COMMITTED=%g' % spin(fields(), 'intensity').value())  # shown again
    watch(fields()['environment_texture_name'])
    drop(ARGS['first'])
    print('SIGNALLED=%d' % drop(ARGS['second']))
    print('AGAIN=%d' % drop(ARGS['second']))
    print('BACK=%d' % drop(ARGS['first']))  # REVIEW.md TST-546: the field still signals a change
    print('PARTIAL=%d %d' % (drop(ARGS['second'], ('drop',)), drop(ARGS['second'], ('enter', 'move'))))
    disconnect()  # before the panel is built again, which may delete the field
    commit(spin(fields(), 'dome_rotation_angle'), 1.75)  # Turns
    print('TURNS=%g' % spin(fields(), 'dome_rotation_angle', 1).value())  # Degrees, shown again
    action('Environment', 'Reset Environment').trigger()
    QtWidgets.QApplication.processEvents()
    shown = fields()
    print('RESET=%g %g' % (spin(shown, 'dome_rotation_angle', 1).value(), spin(shown, 'intensity').value()))
    watch(shown['environment_texture_name'])
    print('RESET_MAP=%d' % drop(ARGS['first']))
finally:
    disconnect()
    action('Environment', 'Reset Environment').trigger()
    QtWidgets.QApplication.processEvents()
    panel_back()
