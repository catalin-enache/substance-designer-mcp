"""Designer's main window put off screen the ways a user puts it there, read as macOS sees it, and put back: for the
checks of the 3D shot, which puts the window on screen first (REVIEW.md SRV-146). macOS only: the snippets run with the
helpers' text, through its _MacWindow.

At rest, between the checks, Designer is hidden (at_rest). The ways set up behind every window, so that nothing of
Designer's comes in front of the user's windows (the user's report, 2026-11-15: REVIEW.md SRV-149):

- 'minimized': by macOS, as the window's minimize button does (getMainWindow(), a page of the top-level window, says
  isMinimized() False; the top-level says True: REVIEW.md TST-391);
- 'qt minimized': getMainWindow() minimized by Qt (showMinimized), a state of the page no user makes, in which the
  view drew in some runs and not in others (REVIEW.md TST-420);
- 'covered': by a window of Designer's own, a little larger, right in front of it; a third window of Designer's own
  sits right behind it, so the order the shot leaves can be read (REVIEW.md HLP-126). The three behind every window:
  measured covered for macOS there, and the shot put it back behind its cover (2026-11-15);
- 'hidden': Designer hidden, as Cmd+H does;
- TWO: as 'covered', with a smaller window of Designer's own ('later') in front of it, under the cover, over its
  middle: the window directly in front of it is then not the one covering it (REVIEW.md HLP-139);
- 'transparent in front', which leaves the view drawn (DRAWN): as 'covered', then its main window brought in front of
  every window, transparent and click-through, as the 3D shot makes it (designer_helpers/shot3d.py).

Designer's windows, unhidden or un-minimized, and a window of its own just shown came up near the front (2026-11-15),
so they are made transparent first, put in their place, then made opaque (to_back, window).

The ways IN_FRONT bring opaque windows in front of the user's, as what they set up needs; the checks using them run
together, after the others (editor_panels_and_fit/checks.py, run):
- 'on screen': Designer's window in front of every window;
- 'covered in front': its cover and Designer's window in front of the user's windows, as 'covered' was before;
- 'partly covered', which leaves the view drawn (DRAWN): a window over all of it but a strip at the left;
- ON_TOP: as 'covered in front', the cover staying on top of every normal window, so no normal window is in front of
  Designer's (REVIEW.md HLP-130).
"""

from collections.abc import Callable, Sequence
from textwrap import dedent

from test_all_tools.common import Call, text
from test_all_tools.editor_panels_and_fit.window_owner import WHO

WAYS = ('minimized', 'qt minimized', 'covered', 'hidden')
DRAWN = ('partly covered', 'transparent in front')
ON_TOP = 'covered by an always-on-top window'
TWO = 'covered, a smaller window in front of it under the cover'
IN_FRONT = ('on screen', 'covered in front', 'partly covered', ON_TOP)  # ways on the user's screen (the docstring)

# the window and a line of its state, as macOS and Qt see it; `order`, Designer's own windows the checks show, front to
# back, as macOS orders them (NSApp's orderedWindows)
_WINDOW = (
    dedent("""
    import ctypes, sys
    import time as _time
    from PySide6 import QtCore, QtGui, QtWidgets
    VIEW = 'Alg::Gui3D::ViewportWidget'  # the 3D view's widget
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
    def next_to(window, place, number):
        # NSWindow `window` right in front of (place 1) or behind (-1) window `number` (orderWindow:relativeTo:)
        f = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long, ctypes.c_long)
        f(('objc_msgSend', mac._objc))(window, mac._objc.sel_registerName(b'orderWindow:relativeTo:'), place, number)
    def window(geometry, name, on_top=False, place=None):
        # a window of Designer's own over `geometry`, kept as sys.mcp_selftest_<name> from before it shows, so the
        # clear closes it whatever happens next (REVIEW.md TST-460); with `place` (next_to's place and number), shown
        # transparent, placed, then made opaque: shown as it is, it came up near the front (2026-11-15)
        flags = QtCore.Qt.WindowType.Window
        if on_top:
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        made = QtWidgets.QWidget(None, flags)
        made.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        made.setGeometry(geometry)
        setattr(sys, 'mcp_selftest_' + name, made)
        if place is not None:
            made.setWindowOpacity(0.0)
        made.show()
        if place is not None:
            # Qt orders a window shown in a moment: placed before that, it went back near the front
            shown = _MacWindow(made)
            if not until(lambda: mac._flag(shown._window, 'isVisible') and shown.on_screen(shown.number())):
                raise RuntimeError("the window %s made wasn't on screen: left transparent, not placed" % name)
            next_to(shown._window, *place)
            made.setWindowOpacity(1.0)
        return made
    def fade(on, but=None):
        # Designer's windows transparent and click-through (on), as the 3D shot makes them, or opaque and clickable;
        # all but window `but`
        for w in mac.windows(True):
            if w != but:
                mac.set_appearance(w, *((0.0, True) if on else (1.0, False)))
    def to_back():
        # Designer's windows shown behind every window, transparent: unhidden or un-minimized, they came up near
        # the front (2026-11-15); the caller makes them opaque
        fade(True)
        if mac.hidden():
            mac.unhide()
        if mac.minimized():
            mac._object(mac._window, 'deminiaturize:')
        if mw.isMinimized():
            mw.setWindowState(mw.windowState() & ~QtCore.Qt.WindowState.WindowMinimized)
        if not until(shown_again):  # put back before that, they came back near the front (REVIEW.md TST-460)
            raise RuntimeError("Designer's windows weren't shown again: left transparent, not put behind")
        for w in mac.windows(True):
            if mac._flag(w, 'isVisible'):
                mac._object(w, 'orderBack:')
        mac._object(mac._window, 'orderBack:')
    def exposed():
        return mw.windowHandle().isExposed()
    def shown_again():
        # unhidden and un-minimized, macOS's and Qt's, and the 3D view's own window exposed: Qt's expose event once
        # macOS shows it, which Designer's view waits for. Moved or minimized before that, it was undone (2026-11-15)
        shown = not (mac.hidden() or mac.minimized() or mw.isMinimized())
        return shown and all(view.windowHandle().isExposed() for view in views())
    def views():
        # the 3D view's widgets, which get a hide event when Qt minimizes the page (2026-11-15)
        dock = _3d_dock(mw)
        return [w for w in dock.findChildren(QtWidgets.QWidget) if w.metaObject().className() == VIEW] if dock else []
    class _Woken(QtCore.QObject):
        # ends `loop` as an event about Designer's windows comes, so until() looks at its state at once
        def __init__(self, loop, kinds):
            super().__init__()
            self.loop, self.kinds = loop, kinds
        def eventFilter(self, obj, event):
            if event.type() in self.kinds:
                self.loop.quit()
            return False
    def until(state, limit=3.0):
        # until state() holds, looked at as each event about Designer's windows comes (expose, show, hide, window
        # state: Qt's from macOS's) and every 100 ms where none says it, at most `limit` s in case none comes. No time
        # waited after it: under load a time measured idle can be too short (REVIEW.md TST-420)
        kinds = (QtCore.QEvent.Type.Expose, QtCore.QEvent.Type.Show, QtCore.QEvent.Type.Hide,
                 QtCore.QEvent.Type.WindowStateChange)
        start = _time.monotonic()
        while not state() and _time.monotonic() - start < limit:
            loop = QtCore.QEventLoop()
            woken = _Woken(loop, kinds)
            watched = [*QtGui.QGuiApplication.allWindows(), *views()]
            for w in watched:
                w.installEventFilter(woken)
            tick = QtCore.QTimer(loop)
            tick.setSingleShot(True)
            tick.timeout.connect(loop.quit)
            tick.start(100)
            try:
                quitting = loop.exec() < 0  # Qt's quit has run: no event comes any more (REVIEW.md HLP-157)
            finally:
                for w in watched:
                    w.removeEventFilter(woken)
            if quitting:
                break
        return state()
    def hidden_view():
        # (seen, stop): seen[0] set once the 3D view gets a hide event; stop() ends the watch. Qt minimizing the page
        # sends one and changes none of its flags (2026-11-15): call it before the change
        seen = [False]
        class _Hid(QtCore.QObject):
            def eventFilter(self, obj, event):
                if event.type() == QtCore.QEvent.Type.Hide:
                    seen[0] = True
                return False
        catcher, watched = _Hid(), views()
        for w in watched:
            w.installEventFilter(catcher)
        def stop():
            for w in watched:
                w.removeEventFilter(catcher)
        return seen, stop
""")
    + WHO
)

_PUT = dedent("""
    print('BEFORE ' + state())
    if not hasattr(sys, 'mcp_selftest_looks'):  # each window's look, put back by _CLEAR; each held till then
        sys.mcp_selftest_looks = {w: mac.appearance(w) for w in mac.windows(True)}
        for w in sys.mcp_selftest_looks:
            mac.hold(w)
    # from the top-level window: getMainWindow()'s geometry is the page's, in it (REVIEW.md TST-389)
    frame = mw.window().frameGeometry()
    if way in ('on screen', 'covered in front', 'partly covered', 'covered by an always-on-top window'):  # IN_FRONT
        # in front of the user's windows, opaque, as these ways need: on their screen
        if mac.hidden():
            mac.unhide()
            # shown in front before the unhide took, it came up behind the active app's window
            until(lambda: shown_again() and exposed())
        if way in ('covered in front', 'covered by an always-on-top window'):  # ON_TOP
            window(frame.adjusted(100, 100, -100, -100), 'below')
        mac.show()  # in front of the one below, and of the user's windows
        # a window covered already, shown and covered again at once, stayed exposed for Qt and drawn (REVIEW.md TST-389):
        # covered again once Qt said it shown (TST-421: half a second)
        until(exposed)
        if way != 'on screen':
            # always on top for ON_TOP alone: over the transparent way's window, mac.show() can't bring it in front
            # (REVIEW.md TST-401); kept: else deleted
            on_top = way == 'covered by an always-on-top window'
            over = frame.adjusted(100, -50, 50, 50) if way == 'partly covered' else frame.adjusted(-50, -50, 50, 50)
            window(over, 'cover', on_top)  # 'partly covered': a strip at the left left uncovered
            _MacWindow(sys.mcp_selftest_cover).show()  # in front: raise_() made Designer the active app
    elif way == 'hidden':
        if not mac.hidden():  # at rest it is (at_rest)
            to_back()
            mac.hide()
            if not until(lambda: mac.hidden() and not exposed()):  # REVIEW.md TST-460
                raise RuntimeError("Designer wasn't hidden: its windows left transparent")
            fade(False)
    else:  # behind every window: never in front of the user's (REVIEW.md SRV-149's report)
        to_back()
        if way == 'minimized':
            mac._object(mac._window, 'performMiniaturize:')
            # opaque only once off screen: as macOS's animation runs, the window flies to the Dock at the opacity it
            # has (REVIEW.md TST-472, measured: about 0.55 s); it is listed off screen once in the Dock
            number = mac.number()
            if not until(lambda: mac.minimized() and not mac.on_screen(number)):
                raise RuntimeError("Designer's window wasn't minimized: its windows left transparent")
        elif way == 'qt minimized':
            seen, stop = hidden_view()
            mw.showMinimized()
            until(lambda: seen[0])
            stop()
        elif way in ('covered', 'transparent in front'):
            window(frame.adjusted(100, 100, -100, -100), 'below', place=(-1, mac.number()))
            window(frame.adjusted(-50, -50, 50, 50), 'cover', place=(1, mac.number()))
        elif way == 'covered, a smaller window in front of it under the cover':  # TWO
            window(frame.adjusted(100, 100, -100, -100), 'below', place=(-1, mac.number()))
            window(frame.adjusted(300, 300, -300, -300), 'later', place=(1, mac.number()))
            later = _MacWindow(sys.mcp_selftest_later).number()
            window(frame.adjusted(-50, -50, 50, 50), 'cover', place=(1, later))
        if way == 'transparent in front':  # its main window in front, transparent and click-through, as the shot does
            mac.show()
            fade(False, but=mac.windows(False)[0])
        else:
            fade(False)
    on_screen = ('on screen', 'partly covered', 'transparent in front')  # each drawn
    drawn = lambda: exposed() and not mac.covered()
    # in front: no window of another app's in front of it, as the readings after it need (REVIEW.md TST-417)
    front = lambda: drawn() and not in_front_of(mac)
    # the covered ways, as macOS says it: in some Designers `open` started, Qt kept a covered window exposed (REVIEW.md
    # SRV-152, TST-433)
    covered = mac.covered
    reached = {
        'minimized': lambda: mac.minimized() and not exposed(),
        'qt minimized': mw.isMinimized,  # Qt still says exposed: the top-level window is on screen (2026-11-15)
        'hidden': lambda: mac.hidden() and not exposed(),
    }.get(way, front if way in ('on screen', 'transparent in front') else drawn if way in on_screen else covered)
    until(reached)  # REVIEW.md TST-420: it was 2 s whatever the way
    print('STATE ' + state())
""")

# the window back at rest: Designer hidden, its windows opaque and clickable, never shown on the way (REST). Not hidden,
# the windows are left transparent and click-through, and NOT_HIDDEN printed (REVIEW.md TST-460, TST-474)
_CLEAR = dedent("""
    for name in ('cover', 'later', 'below'):
        made = getattr(sys, 'mcp_selftest_' + name, None)
        if made is not None:
            made.close()
            made.deleteLater()
            delattr(sys, 'mcp_selftest_' + name)
    fade(True)
    if mw.isMinimized():
        mw.setWindowState(mw.windowState() & ~QtCore.Qt.WindowState.WindowMinimized)
    if mac.minimized():
        mac._object(mac._window, 'deminiaturize:')
    until(lambda: not (mac.minimized() or mw.isMinimized()))  # macOS's animation: 0.63 s (2026-11-15)
    if not mac.hidden():
        mac.hide()
    hidden = until(mac.hidden)
    for w, look in getattr(sys, 'mcp_selftest_looks', {}).items():  # as _PUT found them
        if hidden:  # opaque on the user's screen otherwise (REVIEW.md TST-474)
            mac.set_appearance(w, *look)
        mac.let_go(w)
    if hasattr(sys, 'mcp_selftest_looks'):
        del sys.mcp_selftest_looks
    # opaque once hidden, one left transparent with no put before it too; not hidden, left transparent and click-through
    # rather than opaque on the user's screen (REVIEW.md TST-460)
    fade(not hidden)
    if not hidden:
        print("NOT_HIDDEN Designer wasn't hidden: its windows left transparent and click-through")
    print('STATE ' + state())
""")

_READ = dedent("""
    until(lambda: EXPECTED)
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
        if found in names:
            return names[found]
        # neither Designer's nor its cover: a window in the way, between them or at another level, so the reading is
        # taken again, as one with a window in front (REVIEW.md TST-419)
        others.append(found)
        return 'another(%s)' % who(found)
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
    below = window(mw.window().frameGeometry().adjusted(100, 100, -100, -100), 'below')
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
        del sys.mcp_selftest_below  # closed here: the clear would close it again
    print('UNDER ' + ' '.join(seen))
    print('IN_FRONT %d' % len(set(others)))
""")

# the 3D view's viewport, and a drag of the helpers' own (_drag) panning it DX pixels right
_DRAG = dedent("""
    viewport = [w for w in _3d_dock(mw).findChildren(QtWidgets.QWidget)
                if w.metaObject().className() == 'Alg::Gui3D::ViewportWidget'][0]
    keep = [mw, viewport]
    frames = _Frames(viewport, lambda: _3d_render(mw))
    try:  # off screen the view draws no frame: the drag waits for its request for one (_Frames.taking; REVIEW.md HLP-149)
        _drag(viewport, QtCore.Qt.MouseButton.MiddleButton, DX, 0, [], frames.taking)
    finally:
        frames.close()
""")

# a pan of the 3D view, the render before and after compared: SAME=True when the render didn't follow it
_PANNED = dedent("""
    viewport = [w for w in _3d_dock(mw).findChildren(QtWidgets.QWidget)
                if w.metaObject().className() == 'Alg::Gui3D::ViewportWidget'][0]
    keep = [mw, viewport]
    others = in_front_of(mac)
    before = _3d_render(mw)
    frames = _Frames(viewport, lambda: _3d_render(mw))
    try:  # each drag taken: its frame drawn, or off screen the view's request for one (_Frames.taking; REVIEW.md HLP-149)
        _drag(viewport, QtCore.Qt.MouseButton.MiddleButton, 40, 0, [], frames.taking)
        others += in_front_of(mac)
        print('SAME=%s' % (_3d_render(mw) == before))
        print('IN_FRONT %d' % len(set(others)))
        _drag(viewport, QtCore.Qt.MouseButton.MiddleButton, -40, 0, [], frames.taking)
    finally:
        frames.close()
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
            # what it did, as macOS says it: a window covered about 0.07 s later, until then drawn on (REVIEW.md TST-421)
            until(lambda: DONE)
        _first_drag(*args)
    shoot_3d(PATH, pan=[0.25, 0.0])
""")
# shoot_3d zooming ZOOM wheel steps, saved to PATH, Designer hidden at the first step, as a click on the user's own
# window covers Designer's during a shot: the steps after it are sent while the view draws no frame (REVIEW.md HLP-149)
_HIDDEN_MID_ZOOM = dedent("""
    print('BEFORE ' + state())
    _first_wheel = _wheel
    def _wheel(viewport, notches, taking=None):
        _hid = []
        def _taking():  # before each notch; what it returns runs after it
            taken = taking() if taking is not None else None
            def _after():
                if not _hid:
                    _hid.append(True)
                    mac.hide()
                    until(lambda: not exposed())
                    print('HIDDEN_AT_THE_FIRST_STEP exposed=%s' % exposed())
                if taken is not None:
                    taken()
            return _after
        _first_wheel(viewport, notches, _taking)
    shoot_3d(PATH, zoom=ZOOM)
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
    'cover': "window(mw.window().frameGeometry().adjusted(-50, -50, 50, 50), 'cover'); "
    "_MacWindow(sys.mcp_selftest_cover).show(); print('covered as the pan began')",
    'later': "window(mw.window().frameGeometry().adjusted(-60, -60, 60, 60), 'later'); "
    "_MacWindow(sys.mcp_selftest_later).show(); print('covered by another window as the pan began')",
    'close': "sys.mcp_selftest_cover.close(); print('its cover closed as the pan began')",
    'minimize': "cover = _MacWindow(sys.mcp_selftest_cover); cover._object(cover._window, 'miniaturize:'); "
    "print('its cover minimized as the pan began')",
    # TWO's smaller window brought in front, as a click on it through Designer's transparent window does
    'raise': "_MacWindow(sys.mcp_selftest_later).show(); print('the window in front of it raised as the pan began')",
}
# what each event did, as macOS says it, which the pan waits for: Designer's window covered, its cover off screen, the
# smaller window in front of it
_GONE = 'not _MacWindow(sys.mcp_selftest_cover).on_screen(_MacWindow(sys.mcp_selftest_cover).number())'
EVENT_DONE = {
    'cover': 'mac.covered()',  # macOS's: Qt kept a covered window exposed in some Designers (REVIEW.md TST-433)
    'later': 'mac.covered()',
    'close': _GONE,
    'minimize': _GONE,
    'raise': '_MacWindow(sys.mcp_selftest_later).number() in mac.in_front()',
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
    """Puts Designer's window off screen `way` (WAYS, DRAWN, TWO, IN_FRONT); prints its state before (BEFORE) and after
    (STATE)."""
    return _WINDOW + 'way = %r\n' % way + _PUT


def _clear() -> str:
    """Puts it back at rest, whatever way it went off: Designer hidden, its windows opaque and clickable, the windows
    the checks made closed; prints its state (STATE). When the hide doesn't take, the windows are left transparent and
    click-through, and NOT_HIDDEN is printed."""
    return _WINDOW + _CLEAR


async def at_rest(c: Call, helper_source: str) -> None:
    """Puts it back at rest in Designer (_clear, the helpers' text, `helper_source`, before it): the one way the checks
    do it, as it raises when Designer couldn't be hidden (stopped_if_shown)."""
    stopped_if_shown(text(await c('execute_designer_code', {'code': helper_source + _clear()})))


def stopped_if_shown(printed: str) -> None:
    """Raises, ending the category's run, when `printed` says Designer couldn't be hidden (NOT_HIDDEN). Its windows
    were left transparent and click-through on screen, and the next 3D shot would take them for ones an earlier shot
    left so and make them opaque where they are, maybe in front of the user's windows (shot3d.py, opaque_first;
    REVIEW.md TST-478)."""
    if 'NOT_HIDDEN' in printed:
        raise RuntimeError("Designer wasn't hidden again, its windows transparent: no check runs in it after this")


def read(expected: str = 'True') -> str:
    """Prints its state (STATE) once `expected` holds, a condition on it (showing, in_order), 3 s at most: macOS said
    a window was sent behind another about 0.1 s later, and a job run at once read it in front. By default, at once."""
    return _WINDOW + _READ.replace('EXPECTED', expected)


def showing(*fields: str) -> str:
    """read()'s condition: the state line shows each of `fields` (name=value, as STATE prints them)."""
    return 'all(f in state().split() for f in %r)' % (fields,)


def in_order(pairs: Sequence[tuple[str, str]]) -> str:
    """read()'s condition: in the state's order, the first of each of `pairs` in front of the second (ahead)."""
    return (
        'all(a in order().split(",") and b in order().split(",") and order().split(",").index(a) < '
        'order().split(",").index(b) for a, b in %r)' % (list(pairs),)
    )


def panned(way: str | None) -> str:
    """Pans the 3D view with Designer's window off screen `way` (WAYS, DRAWN; None: 'on screen', in front of other
    windows: REVIEW.md TST-390), as no tool does it: the helpers' own drag, the render read before and after
    (SAME=...), the state (STATE); then puts the window back."""
    off = put(way if way is not None else 'on screen')
    return off + _PANNED + _CLEAR


def hits() -> str:
    """Puts Designer's window covered in front of the user's windows, then in front of its cover, and prints the window
    a click at its middle would reach with the window opaque, transparent, and transparent and click-through (HITS
    opaque=main ...; no click is made); then puts it back."""
    return put('covered in front') + _HITS + _CLEAR


def under() -> str:
    """Puts Designer's window on screen, in front of the user's windows, as a window of a hidden Designer isn't shown.
    Then prints whether a window of Designer's own counts as covered: alone in front, then whole under its main window,
    the main window opaque, then transparent and click-through (UNDER alone=... opaque=... transparent=...); then makes
    it opaque again."""
    return put('on screen') + _UNDER


def put_and_drag(way: str, pixels: int) -> str:
    """Puts the window off screen `way`, then pans the 3D view `pixels` right with the helpers' own drag, which the view
    may not draw: the change a plain shot must show (REVIEW.md TST-393, TST-420, TST-433)."""
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
    None: nothing. Prints the window's state first (BEFORE). The windows made stay for at_rest."""
    pan = _DURING_PAN if event is not None else _PAN
    done = EVENT_DONE[event] if event else 'True'
    return _WINDOW + pan.replace('DURING_THE_PAN', EVENTS[event] if event else '').replace('DONE', done).replace(
        'PATH', repr(path)
    )


def hidden_mid_zoom(path: str, zoom: int) -> str:
    """shoot_3d zooming `zoom` wheel steps, saved to `path`, Designer hidden at the first step (HIDDEN_AT_THE_FIRST_STEP
    exposed=...); prints the window's state first (BEFORE). The shot puts it back hidden."""
    return _WINDOW + _HIDDEN_MID_ZOOM.replace('PATH', repr(path)).replace('ZOOM', str(zoom))


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
