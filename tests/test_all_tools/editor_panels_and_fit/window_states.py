"""Designer's main window put off screen the ways a user puts it there, read as macOS sees it, and put back: for the
checks of the 3D shot, which puts the window on screen first (REVIEW.md SRV-146). macOS only: the snippets run with the
helpers' text, through its _MacWindow. The ways:

- 'minimized': by macOS, as the window's minimize button does (getMainWindow(), a page of the top-level window, says
  isMinimized() False; the top-level says True: REVIEW.md TST-391);
- 'qt minimized': getMainWindow() minimized by Qt (showMinimized), a state of the page no user makes, which stops the
  drawing too;
- 'covered': by a window of Designer's own, a little larger, in front of it; a third window of Designer's own sits
  behind it, so the order the shot leaves can be read (REVIEW.md HLP-126);
- 'hidden': Designer hidden, as Cmd+H does.

And 'partly covered' (DRAWN): a window over all of it but a strip at the left, which leaves the view drawn; and
'covered by an always-on-top window' (ON_TOP): as 'covered', the cover staying on top of every normal window, so no
normal window is in front of Designer's (REVIEW.md HLP-130).
"""

from textwrap import dedent

WAYS = ('minimized', 'qt minimized', 'covered', 'hidden')
DRAWN = ('partly covered',)
ON_TOP = 'covered by an always-on-top window'

# the window and a line of its state, as macOS and Qt see it; `order`, Designer's own windows the checks show, front to
# back, as macOS orders them (NSApp's orderedWindows)
_WINDOW = dedent("""
    import ctypes, sys
    from PySide6 import QtCore, QtWidgets
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    mac = _MacWindow(mw)
    def order():
        windows = mac._object(mac._app, 'orderedWindows')
        at = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong)(
            ('objc_msgSend', mac._objc))
        names = {mac._window: 'main'}
        for name in ('cover', 'later', 'below'):
            widget = getattr(sys, 'mcp_selftest_' + name, None)
            if widget is not None:
                names[_MacWindow(widget)._window] = name
        listed = [at(windows, mac._objc.sel_registerName(b'objectAtIndex:'), i)
                  for i in range(mac._send(ctypes.c_ulong, windows, 'count'))]
        return ','.join(names[w] for w in listed if w in names)
    def state():
        return ('minimized=%s qt_minimized=%s top_minimized=%s hidden=%s covered=%s exposed=%s active=%s order=%s' % (
            mac.minimized(), mw.isMinimized(), mw.window().isMinimized(), mac.hidden(), mac.covered(),
            mw.windowHandle().isExposed(), mac._flag(mac._app, 'isActive'), order()))
    def window(geometry, on_top=False):
        flags = QtCore.Qt.WindowType.Window
        if on_top:
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        made = QtWidgets.QWidget(None, flags)
        made.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        made.setGeometry(geometry)
        made.show()
        return made
""")

_PUT = dedent("""
    print('BEFORE ' + state())
    if way == 'minimized':
        mac._object(mac._window, 'performMiniaturize:')
    elif way == 'qt minimized':
        mw.showMinimized()
    elif way in ('covered', 'covered by an always-on-top window'):  # ON_TOP
        sys.mcp_selftest_below = window(mw.window().frameGeometry().adjusted(100, 100, -100, -100))
        mac.show()  # in front of the one below, and of the user's windows
        # a window covered already, shown and covered again at once, stayed exposed for Qt and drawn (REVIEW.md TST-389)
        _settle(0.5)
        # from the top-level window: getMainWindow()'s geometry is the page's, in it (REVIEW.md TST-389); kept: else
        # deleted
        sys.mcp_selftest_cover = window(mw.window().frameGeometry().adjusted(-50, -50, 50, 50), way != 'covered')
        _MacWindow(sys.mcp_selftest_cover).show()  # in front: raise_() made Designer the active app
    elif way == 'partly covered':
        mac.show()  # the strip left uncovered in front of the user's windows
        _settle(0.5)
        sys.mcp_selftest_cover = window(mw.window().frameGeometry().adjusted(100, -50, 50, 50))
        _MacWindow(sys.mcp_selftest_cover).show()
    elif way == 'hidden':
        mac.hide()
    _settle(2.0)
    print('STATE ' + state())
""")

# the window back on screen, in front of other windows, without taking focus
_CLEAR = dedent("""
    for name in ('cover', 'later', 'below'):
        made = getattr(sys, 'mcp_selftest_' + name, None)
        if made is not None:
            made.close()
            made.deleteLater()
            delattr(sys, 'mcp_selftest_' + name)
    if mw.isMinimized():
        mw.setWindowState(mw.windowState() & ~QtCore.Qt.WindowState.WindowMinimized)
    if mac.hidden():
        mac.unhide()
    mac.show()
    _settle(1.0)
    print('STATE ' + state())
""")

_READ = dedent("""
    _settle(0.5)
    print('STATE ' + state())
""")

# the 3D view's viewport, and a drag of the helpers' own (_drag) panning it DX pixels right
_DRAG = dedent("""
    viewport = [w for w in _3d_dock(mw).findChildren(QtWidgets.QWidget)
                if w.metaObject().className() == 'Alg::Gui3D::ViewportWidget'][0]
    keep = [mw, viewport]
    _drag(viewport, QtCore.Qt.MouseButton.MiddleButton, DX, 0, [])
    _settle(0.5)
""")

# a pan of the 3D view, the render before and after compared: SAME=True when the render didn't follow it
_PANNED = dedent("""
    viewport = [w for w in _3d_dock(mw).findChildren(QtWidgets.QWidget)
                if w.metaObject().className() == 'Alg::Gui3D::ViewportWidget'][0]
    keep = [mw, viewport]
    before = _3d_render(mw)
    _drag(viewport, QtCore.Qt.MouseButton.MiddleButton, 40, 0, [])
    _settle(0.5)
    print('SAME=%s' % (_3d_render(mw) == before))
    _drag(viewport, QtCore.Qt.MouseButton.MiddleButton, -40, 0, [])
    _settle(0.3)
""")

# shoot_3d panning a quarter of the view right, saved to PATH, with DURING_THE_PAN done as the pan's first drag starts,
# as a user's click on their own window would (REVIEW.md HLP-124, HLP-130, HLP-131)
_DURING_PAN = dedent("""
    print('BEFORE ' + state())
    _first_drag = _drag
    _pending = [True]
    def _drag(*args):
        if _pending:
            _pending.pop()
            DURING_THE_PAN
            _settle(0.5)  # macOS says a window is covered about 0.07 s later: until then the view draws on
        _first_drag(*args)
    shoot_3d(PATH, pan=[0.25, 0.0])
""")
# the same shot, nothing done during it
_PAN = dedent("""
    print('BEFORE ' + state())
    shoot_3d(PATH, pan=[0.25, 0.0])
""")
# what can happen to the windows during the shot, each a line of the first snippet above: a window of Designer's own brought
# over Designer's (the cover, or a later one over a window covered already); the cover closed, or minimized
EVENTS = {
    'cover': 'sys.mcp_selftest_cover = window(mw.window().frameGeometry().adjusted(-50, -50, 50, 50)); '
    "_MacWindow(sys.mcp_selftest_cover).show(); print('covered as the pan began')",
    'later': 'sys.mcp_selftest_later = window(mw.window().frameGeometry().adjusted(-60, -60, 60, 60)); '
    "_MacWindow(sys.mcp_selftest_later).show(); print('covered by another window as the pan began')",
    'close': "sys.mcp_selftest_cover.close(); print('its cover closed as the pan began')",
    'minimize': "cover = _MacWindow(sys.mcp_selftest_cover); cover._object(cover._window, 'miniaturize:'); "
    "print('its cover minimized as the pan began')",
}


def put(way: str) -> str:
    """Puts Designer's window off screen `way` (WAYS, DRAWN, ON_TOP); prints its state before (BEFORE) and after
    (STATE)."""
    return _WINDOW + 'way = %r\n' % way + _PUT


def clear() -> str:
    """Puts it back on screen, whatever way it went off, and prints its state (STATE)."""
    return _WINDOW + _CLEAR


def read() -> str:
    """Prints its state (STATE), half a second on: macOS says a window was sent behind another about 0.1 s later, and
    a job run at once read it in front."""
    return _WINDOW + _READ


def panned(way: str | None) -> str:
    """Pans the 3D view with Designer's window off screen `way` (WAYS, DRAWN; None: put on screen, in front of other
    windows, first: REVIEW.md TST-390), as no tool does it: the helpers' own drag, the render read before and after
    (SAME=...), the state (STATE); then puts the window back."""
    off = put(way) if way is not None else clear()
    return off + _PANNED + _CLEAR


def put_and_drag(way: str, pixels: int) -> str:
    """Puts the window off screen `way`, then pans the 3D view `pixels` right with the helpers' own drag, the view not
    drawn: the change a plain shot must show (REVIEW.md TST-393)."""
    return put(way) + _DRAG.replace('DX', str(pixels))


def drag(pixels: int) -> str:
    """Pans the 3D view `pixels` right with the helpers' own drag, the window as it is."""
    return _WINDOW + _DRAG.replace('DX', str(pixels))


def during_pan(path: str, event: str | None) -> str:
    """shoot_3d panning a quarter of the view right, saved to `path`, with `event` (EVENTS) done as the pan begins;
    None: nothing. Prints the window's state first (BEFORE). The windows made stay for clear()."""
    pan = _DURING_PAN if event is not None else _PAN
    return _WINDOW + pan.replace('DURING_THE_PAN', EVENTS[event] if event else '').replace('PATH', repr(path))


def became_active(said: str, before: dict[str, str], after: dict[str, str]) -> bool:
    """Whether Designer became the active app during a shot: the shot said it left the window up for that, or Designer
    is the active app after the shot (`after`) and wasn't before it (`before`: during_pan's BEFORE line). Activating
    Designer brings its windows in front, and the shot then leaves its window up (shot3d.py; DECISIONS.md), so the
    put-back can't be judged. In the full run another Designer may hand activation over as it quits, and a click would
    do the same (REVIEW.md TST-399)."""
    left_up = "Designer's window: left on screen, as Designer became the active app during the shot" in said
    return left_up or (before.get('active') == 'False' and after.get('active') == 'True')


def ahead(order: str, first: str, second: str) -> bool:
    """Whether window `first` is in front of `second` in a state line's `order` (front to back); False when either
    isn't listed."""
    names = order.split(',')
    return first in names and second in names and names.index(first) < names.index(second)


def states(t: str) -> dict[str, dict[str, str]]:
    """The window's state lines a snippet printed: {'BEFORE' or 'STATE': {'minimized': 'True', ...}}, the last of
    each."""
    found: dict[str, dict[str, str]] = {}
    for line in t.splitlines():
        head, _, rest = line.strip().partition(' ')
        if head in ('BEFORE', 'STATE'):
            found[head] = dict(pair.split('=', 1) for pair in rest.split())
    return found


def focus(before: dict[str, str], after: dict[str, str]) -> bool | None:
    """Whether Designer is still not the active app after a shot (the user's keyboard left where it was); None when
    that can't be judged: Designer was the active app before, or a state wasn't read (REVIEW.md TST-392). A hidden
    Designer the shot made active is left shown (shot3d.py), which its own state after shows."""
    if before.get('active') != 'False' or 'active' not in after:
        return None
    return after['active'] == 'False'
