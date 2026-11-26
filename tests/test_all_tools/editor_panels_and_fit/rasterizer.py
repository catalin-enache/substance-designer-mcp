"""The Rasterizer's settings for the 3D zoom's check of them (checks.py): set through Renderer > Edit settings, the
Rasterizer's page of the Parameters panel, then the panel turned back to the graph in the editor by opening it again,
once it shows the page. Run inline with the helpers' text. Measured (2026-11-21, a Designer an agent started): the
page lists "Samples" (a spin box) and "Enable rasterizer accumulation antialiasing" (a checkable button), neither
with an object name; reading both and turning the panel back took 0.25 s. A spin box of the Parameters panel takes a
value only through its own valueChanged() (measured 2026-11-12 on the 3D material's Tiling). The shot itself never
reads them (REVIEW.md HLP-215, the user's decision)."""

import re
from textwrap import dedent

DEFAULT_VALUES = (('Samples', '8.0'), ('antialiasing', 'True'))  # Designer's defaults, as _SET prints them
_DEFAULTS = 'RASTERIZER samples=%s aa=%s' % tuple(value for _, value in DEFAULT_VALUES)
# what _SET prints at Designer's defaults before its set; once it set a value; and after a put-back to the defaults
DEFAULTS_BEFORE = _DEFAULTS + ' before'
SET = re.compile(r'^RASTERIZER .* after', re.M)
DEFAULTS_SET = _DEFAULTS + ' after'

# Sets __KIND__ ('samples' or 'aa') to __WANTED__ on the Rasterizer's page, Designer's window on screen as a shot has
# it, only from __FROM__: any other value is left as it is (NOT_AS_READ). Prints the values before and after
# (RASTERIZER samples=.. aa=..)
_SET = dedent("""
    from PySide6 import QtCore, QtWidgets
    mw = _main_window()
    dock = _3d_dock(mw)
    bar = dock.findChildren(QtWidgets.QMenuBar)[0]
    params = _visible_dock(mw, _PANEL_AREAS['parameters'])
    keep = [mw, dock, bar, params]
    def controls():
        # the Samples spin box and the antialiasing button, each the first of its kind after its label; None for one
        # not found
        label, samples, aa = None, None, None
        for w in params.findChildren(QtWidgets.QWidget):
            if isinstance(w, QtWidgets.QLabel) and w.isVisible():
                label = w.text()
            elif label == 'Samples' and samples is None and isinstance(w, QtWidgets.QAbstractSpinBox):
                samples = w
            elif label == 'Enable rasterizer accumulation antialiasing' and aa is None and isinstance(
                w, QtWidgets.QPushButton
            ) and w.isCheckable():
                aa = w
        return samples, aa
    def commit(spin, value):
        spin.setValue(value)
        QtCore.QMetaObject.invokeMethod(spin, 'valueChanged', QtCore.Qt.ConnectionType.DirectConnection)
        _process_events()
    def setting():
        if not _until(lambda: None not in controls(), SETTLE_LIMIT):
            raise RuntimeError("the Parameters panel's Rasterizer page showed no Samples or no antialiasing")
        samples, aa = controls()
        keep.extend([samples, aa])
        def said():
            return 'RASTERIZER samples=%r aa=%r' % (samples.value(), aa.isChecked())
        print(said() + ' before')
        now = samples.value() if __KIND__ == 'samples' else aa.isChecked()
        if now != __FROM__:
            raise RuntimeError('NOT_AS_READ: %s is %r, not %r' % (__KIND__, now, __FROM__))
        if __KIND__ == 'samples':
            commit(samples, float(__WANTED__))
        elif now != __WANTED__:
            aa.click()
            _process_events()
        return said() + ' after'
    frames = _frames_of(mw, _viewport(dock))
    try:
        with _on_screen(mw, frames):
            shown = params.windowTitle()
            try:
                _menu_action(bar, keep, 'Renderer', 'Edit settings').trigger()
                print(setting())
            finally:  # once it shows the page: turned back before, the switch to the page came after
                _until(lambda: params.windowTitle() != shown, SETTLE_LIMIT, [params.windowTitleChanged])
                editor = _current_graph()
                if editor is not None:
                    _ui_mgr().openResourceInEditor(editor)
                    _process_events()
    finally:
        frames.close()
""")

# The overlay's count as each render is taken (RENDER_COUNT), read from its labels as _Frames.count reads them
COUNTED = dedent("""
    from PySide6 import QtWidgets
    _first_render = _3d_render
    def _3d_render(mw):
        labels = _viewport(_3d_dock(mw)).findChildren(QtWidgets.QLabel)
        print('RENDER_COUNT %s' % _samples([label.text() for label in labels]))
        return _first_render(mw)
""")


def off_defaults(said: str, when: str = 'before') -> str:
    """What a set's reply `said` read `when` ('before' the case's set, or 'after' its put-back), when that wasn't
    Designer's defaults: each setting off its default, with the value read, or that the page wasn't read, with the
    reply's end (REVIEW.md TST-680, TST-683)."""
    at = {'before': 'before the case', 'after': 'after the put-back'}[when]
    read = re.search(r'^RASTERIZER samples=(\S+) aa=(\S+) %s' % when, said, re.M)
    if read is None:
        return "the Rasterizer's page wasn't read %s: %s" % (at, said.strip()[-120:])
    off = [
        '%s %s (%s by default)' % (setting, value, default)
        for (setting, default), value in zip(DEFAULT_VALUES, read.groups(), strict=True)
        if value != default
    ]
    return "not at Designer's defaults %s: %s" % (at, ', '.join(off))


def set_rasterizer(kind: str, wanted: float | bool, from_value: float | bool) -> str:
    """The snippet setting `kind` ('samples' or 'aa') to `wanted` on the Rasterizer's page, only from `from_value`
    (_SET)."""
    code = _SET.replace('__KIND__', repr(kind)).replace('__WANTED__', repr(wanted))
    return code.replace('__FROM__', repr(from_value))
