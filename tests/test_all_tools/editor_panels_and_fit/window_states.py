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

And TWO: as 'covered', with a smaller window of Designer's own ('later') in front of it, under the cover, over its
middle: the window directly in front of it is then not the one covering it (REVIEW.md HLP-139).

And the ways that leave the view drawn (DRAWN): 'partly covered', a window over all of it but a strip at the left;
'transparent in front', as 'covered', then made transparent and click-through and brought in front, as the 3D shot
does (designer_helpers/shot3d.py). And 'covered by an always-on-top window' (ON_TOP): as 'covered', the cover staying
on top of every normal window, so no normal window is in front of Designer's (REVIEW.md HLP-130).
"""

from collections.abc import Callable
from textwrap import dedent

WAYS = ('minimized', 'qt minimized', 'covered', 'hidden')
DRAWN = ('partly covered', 'transparent in front')
ON_TOP = 'covered by an always-on-top window'
TWO = 'covered, a smaller window in front of it under the cover'

# the window and a line of its state, as macOS and Qt see it; `order`, Designer's own windows the checks show, front to
# back, as macOS orders them (NSApp's orderedWindows)
_WINDOW = dedent("""
    import ctypes, sys
    from PySide6 import QtCore, QtWidgets
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    mac = _MacWindow(mw)
    def listed(selector):
        windows = mac._object(mac._app, selector)
        at = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong)(
            ('objc_msgSend', mac._objc))
        return [at(windows, mac._objc.sel_registerName(b'objectAtIndex:'), i)
                for i in range(mac._send(ctypes.c_ulong, windows, 'count'))]
    def order():
        names = {mac._window: 'main'}
        for name in ('cover', 'later', 'below'):
            widget = getattr(sys, 'mcp_selftest_' + name, None)
            if widget is not None:
                names[_MacWindow(widget)._window] = name
        return ','.join(names[w] for w in listed('orderedWindows') if w in names)
    def state():
        every = listed('windows')  # NSApp's, read here, not through the _MacWindow.windows the shot uses (TST-411)
        cover = getattr(sys, 'mcp_selftest_cover', None)
        # CoreGraphics', as NSApp's orderedWindows still lists a window closed or minimized (REVIEW.md TST-415)
        cover_on_screen = None if cover is None else _MacWindow(cover).on_screen(_MacWindow(cover).number())
        return (
            'minimized=%s qt_minimized=%s top_minimized=%s hidden=%s covered=%s exposed=%s active=%s order=%s '
            'opacity=%g through=%s windows=%d faded=%d cover_on_screen=%s' % (
                mac.minimized(), mw.isMinimized(), mw.window().isMinimized(), mac.hidden(), mac.covered(),
                mw.windowHandle().isExposed(), mac._flag(mac._app, 'isActive'), order(),
                *mac.appearance(mac.windows(False)[0]), len(every),
                sum(mac.appearance(w) != (1.0, False) for w in every), cover_on_screen))
    def in_front_of(window):
        # the windows in front of `window` (a _MacWindow), any app's, but those the checks made (REVIEW.md TST-417)
        widgets = [getattr(sys, 'mcp_selftest_' + name, None) for name in ('cover', 'later', 'below')]
        made = {_MacWindow(widget).number() for widget in widgets if widget is not None}
        return [number for number in window.in_front() if number not in made]
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
    if not hasattr(sys, 'mcp_selftest_looks'):  # each window's look, put back by _CLEAR; each held till then
        sys.mcp_selftest_looks = {w: mac.appearance(w) for w in mac.windows(True)}
        for w in sys.mcp_selftest_looks:
            mac.hold(w)
    if way == 'minimized':
        mac._object(mac._window, 'performMiniaturize:')
    elif way == 'qt minimized':
        mw.showMinimized()
    elif way in ('covered', 'covered by an always-on-top window', 'transparent in front'):  # ON_TOP
        sys.mcp_selftest_below = window(mw.window().frameGeometry().adjusted(100, 100, -100, -100))
        mac.show()  # in front of the one below, and of the user's windows
        # a window covered already, shown and covered again at once, stayed exposed for Qt and drawn (REVIEW.md TST-389)
        _settle(0.5)
        # from the top-level window: getMainWindow()'s geometry is the page's, in it (REVIEW.md TST-389); kept: else
        # deleted
        # always on top for ON_TOP alone: over the transparent way's window, mac.show() can't bring it in front
        # (REVIEW.md TST-401)
        on_top = way == 'covered by an always-on-top window'
        sys.mcp_selftest_cover = window(mw.window().frameGeometry().adjusted(-50, -50, 50, 50), on_top)
        _MacWindow(sys.mcp_selftest_cover).show()  # in front: raise_() made Designer the active app
        if way == 'transparent in front':
            _settle(0.5)
            mac.set_appearance(mac.windows(False)[0], 0.0, True)
            mac.show()
    elif way == 'covered, a smaller window in front of it under the cover':  # TWO
        sys.mcp_selftest_below = window(mw.window().frameGeometry().adjusted(100, 100, -100, -100))
        mac.show()
        _settle(0.5)
        sys.mcp_selftest_later = window(mw.window().frameGeometry().adjusted(300, 300, -300, -300))
        _MacWindow(sys.mcp_selftest_later).show()
        sys.mcp_selftest_cover = window(mw.window().frameGeometry().adjusted(-50, -50, 50, 50))
        _MacWindow(sys.mcp_selftest_cover).show()
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
    for w, look in getattr(sys, 'mcp_selftest_looks', {}).items():  # as _PUT found them
        mac.set_appearance(w, *look)
        mac.let_go(w)
    if hasattr(sys, 'mcp_selftest_looks'):
        del sys.mcp_selftest_looks
    mac.set_appearance(mac.windows(False)[0], 1.0, False)  # one left transparent with no put before it too
    mac.show()
    _settle(1.0)
    print('STATE ' + state())
""")

_READ = dedent("""
    _settle(0.5)
    print('STATE ' + state())
""")

# the window a click at the middle of Designer's window would reach (NSWindow's windowNumberAtPoint; no click is made),
# the window in front of its cover: opaque, transparent, transparent and click-through (HITS ...)
_HITS = dedent("""
    class NSPoint(ctypes.Structure):
        _fields_ = [('x', ctypes.c_double), ('y', ctypes.c_double)]
    at = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, NSPoint, ctypes.c_long)(
        ('objc_msgSend', mac._objc))
    middle = mw.window().frameGeometry().center()
    height = QtWidgets.QApplication.primaryScreen().geometry().height()  # macOS counts up from the bottom
    names = {mac.number(): 'main', _MacWindow(sys.mcp_selftest_cover).number(): 'cover'}
    def hit():
        found = at(mac._objc.objc_getClass(b'NSWindow'),
                   mac._objc.sel_registerName(b'windowNumberAtPoint:belowWindowWithWindowNumber:'),
                   NSPoint(middle.x(), height - middle.y()), 0)
        return names.get(found, 'another')
    mac.show()
    _settle(0.5)
    seen, others = [], []
    try:
        for name, look in (('opaque', (1.0, False)), ('transparent', (0.0, False)), ('through', (0.0, True))):
            mac.set_appearance(mac.windows(False)[0], *look)
            _settle(0.5)
            seen.append('%s=%s' % (name, hit()))
            others += in_front_of(mac)
    finally:
        mac.set_appearance(mac.windows(False)[0], 1.0, False)
    print('HITS ' + ' '.join(seen))
    print('IN_FRONT %d' % len(set(others)))
""")

# whether a window of Designer's own counts as covered for macOS: in front of its main window first, as the reading
# with nothing over it (REVIEW.md TST-412), then whole under it, the main window opaque, then transparent and
# click-through, as the 3D shot makes it (UNDER alone=... opaque=... transparent=...)
_UNDER = dedent("""
    below = window(mw.window().frameGeometry().adjusted(100, 100, -100, -100))
    _MacWindow(below).show()
    _settle(1.0)
    seen = ['alone=%s' % _MacWindow(below).covered()]
    others = in_front_of(_MacWindow(below))
    mac.show()
    _settle(1.0)
    try:
        for name, look in (('opaque', (1.0, False)), ('transparent', (0.0, True))):
            mac.set_appearance(mac.windows(False)[0], *look)
            _settle(1.0)
            seen.append('%s=%s' % (name, _MacWindow(below).covered()))
            others += in_front_of(mac)
    finally:
        mac.set_appearance(mac.windows(False)[0], 1.0, False)
        below.close()
        below.deleteLater()
    print('UNDER ' + ' '.join(seen))
    print('IN_FRONT %d' % len(set(others)))
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
    others = in_front_of(mac)
    before = _3d_render(mw)
    _drag(viewport, QtCore.Qt.MouseButton.MiddleButton, 40, 0, [])
    _settle(0.5)
    others += in_front_of(mac)
    print('SAME=%s' % (_3d_render(mw) == before))
    print('IN_FRONT %d' % len(set(others)))
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
# the same shot, the window's state printed as each render is read (RENDER)
_RENDERED = dedent("""
    _real_render = _3d_render
    def _3d_render(mw):
        print('RENDER ' + state())
        return _real_render(mw)
    shoot_3d(PATH, pan=[0.25, 0.0])
""")
# the same shot, Designer the active app from the set-up's start on, as the helpers see it (_MacWindow.active rebound:
# the user's keyboard stays where it is), the window's state printed as each render is read (RENDER; REVIEW.md HLP-136)
_SWITCHED = dedent("""
    _active = []
    _MacWindow.active = lambda self: bool(_active)
    _real_set_up = _3d_set_up
    def _3d_set_up(*args):
        run = _real_set_up(*args)
        def started(*given):
            _active.append(True)
            run(*given)
        return started
    _real_render = _3d_render
    def _3d_render(mw):
        print('RENDER ' + state())
        return _real_render(mw)
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
    # TWO's smaller window brought in front, as a click on it through Designer's transparent window does
    'raise': "_MacWindow(sys.mcp_selftest_later).show(); print('the window in front of it raised as the pan began')",
}
# what a shot says once Designer became the active app during it: its windows made opaque at once, and left up if
# Designer is still the active app as it ends (shot3d.py)
MADE_OPAQUE = "Designer's window: made opaque at once, as Designer became the active app during the shot"
LEFT_UP = "Designer's window: left on screen, as Designer became the active app during the shot"
# what a shot says when a window brought over Designer's during it made it bring the window in front again: the start
# of the line, which says ', transparent' only when Designer isn't the active app at that look (REVIEW.md TST-416)
AGAIN = "Designer's window: brought in front again"
# how each event is seen to have happened, from what the shot said and the window's state after it (STATE): an event
# that did nothing would leave a check passing on the put-back it was made to catch (REVIEW.md TST-415). A window
# brought over Designer's makes the shot bring Designer's window in front again, and say so (AGAIN). TWO's smaller
# window raised is in front of the cover, which TWO puts in front of it. The cover closed or minimized is off screen,
# as CoreGraphics lists it.
SEEN_BY: dict[str, Callable[[str, dict[str, str]], bool]] = {
    'cover': lambda said, after: AGAIN in said,
    'later': lambda said, after: AGAIN in said,
    'close': lambda said, after: after.get('cover_on_screen') == 'False',
    'minimize': lambda said, after: after.get('cover_on_screen') == 'False',
    'raise': lambda said, after: ahead(after.get('order', ''), 'later', 'cover'),
}


def put(way: str) -> str:
    """Puts Designer's window off screen `way` (WAYS, DRAWN, ON_TOP, TWO); prints its state before (BEFORE) and after
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


def hits() -> str:
    """Puts Designer's window covered, then in front of its cover, and prints the window a click at its middle would
    reach with the window opaque, transparent, and transparent and click-through (HITS opaque=main ...; no click is
    made); then puts it back."""
    return put('covered') + _HITS + _CLEAR


def under() -> str:
    """Prints whether a window of Designer's own counts as covered: alone in front, then whole under its main window,
    the main window opaque, then transparent and click-through (UNDER alone=... opaque=... transparent=...); then makes
    it opaque again."""
    return _WINDOW + _UNDER


def put_and_drag(way: str, pixels: int) -> str:
    """Puts the window off screen `way`, then pans the 3D view `pixels` right with the helpers' own drag, the view not
    drawn: the change a plain shot must show (REVIEW.md TST-393)."""
    return put(way) + _DRAG.replace('DX', str(pixels))


def drag(pixels: int) -> str:
    """Pans the 3D view `pixels` right with the helpers' own drag, the window as it is."""
    return _WINDOW + _DRAG.replace('DX', str(pixels))


def rendered(path: str) -> str:
    """shoot_3d panning a quarter of the view right, saved to `path`, printing the window's state as each render is read
    (RENDER lines)."""
    return _WINDOW + _RENDERED.replace('PATH', repr(path))


def switched(path: str) -> str:
    """rendered(path), Designer the active app from the set-up's start on, as the helpers see it: the user's switch to
    Designer during the shot, without taking the keyboard from the app the user is in (RENDER lines)."""
    return _WINDOW + _SWITCHED.replace('PATH', repr(path))


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
    return LEFT_UP in said or (before.get('active') == 'False' and after.get('active') == 'True')


def activated(said: str, off: dict[str, str], after: dict[str, str]) -> bool:
    """Whether Designer became the active app during a shot that said `said`: the shot says it saw so (MADE_OPAQUE,
    LEFT_UP), or Designer is the active app after it (`after`) and wasn't just before it (`off`, focus). The pool's
    other Designers can hand it activation; a shot that makes it the active app itself does so each time (REVIEW.md
    TST-418)."""
    return MADE_OPAQUE in said or LEFT_UP in said or focus(off, after) is False


def nothing_in_front(printed: str) -> bool:
    """Whether a reading found no window in front of the window it read but those the checks made (the last IN_FRONT
    line its snippet printed is 0); False when none was printed. Another app's window there, one of the pool's other
    Designers or the user's, changes the reading (REVIEW.md TST-417)."""
    found = [line.split()[1] for line in printed.splitlines() if line.strip().startswith('IN_FRONT ')]
    return bool(found) and found[-1] == '0'


def event_seen(event: str | None, said: str, after: dict[str, str]) -> bool:
    """Whether `event` (EVENTS), done during a shot, is seen to have happened, in what the shot said (`said`) or in
    the window's state after it (`after`: STATE), as SEEN_BY says; True for no event."""
    return event is None or SEEN_BY[event](said, after)


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


def renders(t: str) -> list[dict[str, str]]:
    """The window's state as each render was read (the RENDER lines rendered() prints), in order."""
    return [
        dict(pair.split('=', 1) for pair in line.strip().split()[1:])
        for line in t.splitlines()
        if line.strip().startswith('RENDER ')
    ]


def focus(before: dict[str, str], after: dict[str, str]) -> bool | None:
    """Whether Designer is still not the active app after a shot (the user's keyboard left where it was); None when
    that can't be judged: Designer was the active app before, or a state wasn't read (REVIEW.md TST-392). A hidden
    Designer the shot made active is left shown (shot3d.py), which its own state after shows."""
    if before.get('active') != 'False' or 'active' not in after:
        return None
    return after['active'] == 'False'
