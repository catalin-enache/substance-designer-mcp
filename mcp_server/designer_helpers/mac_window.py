"""Designer's main window as macOS sees it (_MacWindow), for the 3D shot (shot3d.py), read, moved and made transparent
through the Objective-C runtime and CoreGraphics with ctypes; and the keyboard given back after a start
(give_back_activation). macOS only (_mac_window).

Measured on macOS in a Designer an agent started (2026-11-13; what the 3D view does off screen: shot3d.py):

- getMainWindow() is a page of the top-level window, native already, so asking its winId() changes nothing; the
  NSWindow of its NSView is the top-level window's.
- The window directly in front of another, in CoreGraphics' list of the windows on screen above it (normal windows,
  layer 0), is found whether it is Designer's own or another app's. orderWindow:relativeTo: puts Designer's window
  right behind either. Given the number of a window no longer on screen, closed or minimized (2026-11-14), or of one
  that doesn't exist, it puts it behind every window, as orderBack: does: so the shot asks first (lowest).
- A window covered whole by an always-on-top window (Qt's WindowStaysOnTopHint: layer 8) has no normal window in front
  of it, so none is found (2026-11-14).
- A Designer an agent starts became the active app as it started, the one the keyboard types into, taking it from the
  app in front: the user's, or another agent's Designer. launch_designer opens an app bundle hidden; a binary in
  SD_DESIGNER_APP starts shown (server_tools/lifecycle.py; REVIEW.md SRV-149, SRV-152). One that quits as the active app hands it back to the app active
  before it. Hidden (hide:), Designer makes the app active before it active again; shown again without being
  made active (unhideWithoutActivation), it stays so (2026-11-14, the front app read with lsappinfo: REVIEW.md SRV-148).
"""

import ctypes
import ctypes.util

from .core import QtGui, QtWidgets, _main_window, cast, sys
from .waits import _event_signal, _until, _unwatch

ACTIVATION_WAIT = 3.0  # s at most for Designer to be no longer the active app once hidden, then shown again: a limit
NS_VISIBLE = 2  # NSWindowOcclusionStateVisible: part of the window is on screen
NS_BELOW = -1  # NSWindowBelow, for orderWindow:relativeTo:
CG_ON_SCREEN = (1 << 0) | (1 << 4)  # kCGWindowListOptionOnScreenOnly, kCGWindowListExcludeDesktopElements
CG_ABOVE = (1 << 1) | (1 << 4)  # kCGWindowListOptionOnScreenAboveWindow, kCGWindowListExcludeDesktopElements
CF_UTF8 = 0x08000100  # kCFStringEncodingUTF8
CF_SINT64 = 4  # kCFNumberSInt64Type


class _MacWindow:
    """Designer's main window as macOS sees it, and the calls that put it on screen without making Designer the active
    app (shot3d.py), sent through the Objective-C runtime."""

    def __init__(self, mw: QtWidgets.QWidget) -> None:
        self._objc = ctypes.CDLL(ctypes.util.find_library('objc'))
        self._objc.objc_getClass.restype = ctypes.c_void_p
        self._objc.sel_registerName.restype = ctypes.c_void_p
        self._app = self._object(self._objc.objc_getClass(b'NSApplication'), 'sharedApplication')
        self._window = self._object(int(mw.winId()), 'window')  # the NSWindow of the main window's NSView

    def _send(
        self,
        result: type[ctypes.c_void_p | ctypes.c_bool | ctypes.c_ulong | ctypes.c_long | ctypes.c_double],
        receiver: int | None,
        selector: str,
        argument: int | None = None,
    ) -> bool | int | float | None:
        """objc_msgSend: `selector` sent to `receiver`, with `argument`, nil when omitted (a selector without one ignores
        it). An object or an index alike: either goes in one register of 64 bits. Returns what ctypes makes of `result`:
        an int, or None for nil (c_void_p), a bool, an int, or a float. Its callers cast the result to that type. No
        @overload says it here: typing keeps each stub it decorates, and a stub's globals are the helpers job's scope.
        The plugin drops the stubs once a job ends (REVIEW.md PLG-44), but a plugin installed before that kept the
        scope alive after the job (REVIEW.md HLP-182)."""
        prototype = ctypes.CFUNCTYPE(result, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
        send = prototype(('objc_msgSend', self._objc))
        return cast(bool | int | float | None, send(receiver, self._objc.sel_registerName(selector.encode()), argument))

    def _object(self, receiver: int | None, selector: str, argument: int | None = None) -> int | None:
        return cast(int | None, self._send(ctypes.c_void_p, receiver, selector, argument))

    def _items(self, listed: int | None) -> list[int]:
        """The objects of the NSArray `listed`; none when it is nil."""
        count = cast(int, self._send(ctypes.c_ulong, listed, 'count'))
        return [cast(int, self._object(listed, 'objectAtIndex:', i)) for i in range(count)]

    def _flag(self, receiver: int | None, selector: str) -> bool:
        return bool(self._send(ctypes.c_bool, receiver, selector))

    def minimized(self) -> bool:
        return self._flag(self._window, 'isMiniaturized')

    def hidden(self) -> bool:
        """Designer hidden, all its windows with it."""
        return self._flag(self._app, 'isHidden')

    def covered(self) -> bool:
        """No part of the window on screen: covered, or minimized, or Designer hidden."""
        return not cast(int, self._send(ctypes.c_ulong, self._window, 'occlusionState')) & NS_VISIBLE

    def active(self) -> bool:
        """Designer the active app: the one the keyboard types into."""
        return self._flag(self._app, 'isActive')

    def show(self) -> None:
        """In front of the other windows, un-minimized, without making Designer the active app."""
        self._object(self._window, 'orderFrontRegardless')

    def unhide(self) -> None:
        self._object(self._app, 'unhideWithoutActivation')

    def hide(self) -> None:
        self._object(self._app, 'hide:')

    def minimize(self) -> None:
        """Minimized into the Dock, as its minimize button does."""
        self._object(self._window, 'miniaturize:')

    def number(self) -> int:
        """The window's number, as CoreGraphics lists it."""
        return cast(int, self._send(ctypes.c_long, self._window, 'windowNumber'))

    def windows(self, every: bool) -> list[int]:
        """The main window; with `every`, each of Designer's windows (NSApp's windows, shown or not)."""
        if not every:
            return [cast(int, self._window)]
        return self._items(self._object(self._app, 'windows'))

    def hand_over_clipboard(self) -> None:
        """Reads every type on the general pasteboard back, in Designer's own process, so what Qt only promised there is
        the pasteboard's. On macOS, Qt's setMimeData promises the data: Designer hands it over when another app asks,
        and reading it here asks at once. Left promised, the text a 3D shot put back made another app's paste wait while
        Designer's main thread was busy, and was gone once Designer was killed. Measured 2026-11-16, in Designers an
        agent started (REVIEW.md HLP-181), 1 of 1 each: a paste 2 s into a 12 s job came only as the job ended, and
        after a SIGKILL nothing came; read back first, the paste came in 0.013 s, and the text was there after a
        SIGKILL. Not read back, a normal quit kept it. macOS only, as _MacWindow is."""
        self._objc.objc_autoreleasePoolPush.restype = ctypes.c_void_p
        self._objc.objc_autoreleasePoolPop.argtypes = [ctypes.c_void_p]
        pool: int | None = self._objc.objc_autoreleasePoolPush()  # each read freed at once, not at the job's end
        try:
            board = self._object(self._objc.objc_getClass(b'NSPasteboard'), 'generalPasteboard')
            for kind in self._items(self._object(board, 'types')):  # nil when empty: no items
                self._object(board, 'dataForType:', kind)
        finally:
            self._objc.objc_autoreleasePoolPop(pool)

    def hold(self, window: int) -> None:
        """Keeps `window` from being freed, even once closed, until let_go: a window Designer closes while it is held
        stays safe to message (retain)."""
        self._object(window, 'retain')

    def let_go(self, window: int) -> None:
        """Ends a hold (release): once for each hold."""
        self._object(window, 'release')

    def appearance(self, window: int) -> tuple[float, bool]:
        """`window`'s opacity (alphaValue, 0 to 1), and whether the mouse goes through it to the window under it
        (ignoresMouseEvents)."""
        return cast(float, self._send(ctypes.c_double, window, 'alphaValue')), self._flag(window, 'ignoresMouseEvents')

    def set_appearance(self, window: int, opacity: float, through: bool) -> None:
        """Sets `window`'s opacity and whether the mouse goes through it (appearance)."""
        for selector, kind, value in (
            (b'setAlphaValue:', ctypes.c_double, opacity),
            (b'setIgnoresMouseEvents:', ctypes.c_bool, through),
        ):
            prototype = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, kind)
            prototype(('objc_msgSend', self._objc))(window, self._objc.sel_registerName(selector), value)

    def in_front(self) -> list[int]:
        """The numbers of the normal windows in front of this one on screen, any app's, front to back."""
        return [window for window, layer in self._listed(CG_ABOVE, self.number()) if layer == 0]

    def lowest(self, numbers: list[int]) -> int | None:
        """Of the windows `numbers`, any app's, the one on screen nearest the back; None when none is on screen."""
        found = [window for window, _ in self._listed(CG_ON_SCREEN, 0) if window in numbers]
        return found[-1] if found else None

    def on_screen(self, number: int) -> bool:
        """Whether window `number`, any app's, is on screen: not closed, minimized or hidden."""
        return any(window == number for window, _ in self._listed(CG_ON_SCREEN, 0))

    def _listed(self, option: int, relative: int) -> list[tuple[int, int]]:
        """The windows CoreGraphics lists for `option` (relative to window `relative`), front to back: (number,
        layer)."""
        cg = ctypes.CDLL(ctypes.util.find_library('CoreGraphics'))
        cf = ctypes.CDLL(ctypes.util.find_library('CoreFoundation'))
        cg.CGWindowListCopyWindowInfo.restype = ctypes.c_void_p
        cg.CGWindowListCopyWindowInfo.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
        cf.CFArrayGetCount.restype = ctypes.c_long
        cf.CFArrayGetCount.argtypes = [ctypes.c_void_p]
        cf.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
        cf.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
        cf.CFDictionaryGetValue.restype = ctypes.c_void_p
        cf.CFDictionaryGetValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        cf.CFNumberGetValue.restype = ctypes.c_bool
        cf.CFNumberGetValue.argtypes = [ctypes.c_void_p, ctypes.c_long, ctypes.c_void_p]
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        # a c_void_p result is an int, or None for NULL
        keys: list[int | None] = [
            cf.CFStringCreateWithCString(None, name, CF_UTF8) for name in (b'kCGWindowNumber', b'kCGWindowLayer')
        ]
        windows: int | None = cg.CGWindowListCopyWindowInfo(option, relative)
        try:
            found: list[tuple[int, int]] = []
            for i in range(cf.CFArrayGetCount(windows) if windows else 0):
                info: int | None = cf.CFArrayGetValueAtIndex(windows, i)
                window, layer = ctypes.c_int64(), ctypes.c_int64()
                cf.CFNumberGetValue(cf.CFDictionaryGetValue(info, keys[0]), CF_SINT64, ctypes.byref(window))
                cf.CFNumberGetValue(cf.CFDictionaryGetValue(info, keys[1]), CF_SINT64, ctypes.byref(layer))
                found.append((window.value, layer.value))
            return found
        finally:
            if windows:
                cf.CFRelease(windows)
            for key in keys:
                cf.CFRelease(key)

    def put_below(self, number: int) -> None:
        """Right behind window `number`, any app's, when it is on screen; behind every window if it isn't (the module
        docstring)."""
        prototype = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long, ctypes.c_long)
        order = prototype(('objc_msgSend', self._objc))
        order(self._window, self._objc.sel_registerName(b'orderWindow:relativeTo:'), NS_BELOW, number)


def _mac_window(mw: QtWidgets.QMainWindow) -> _MacWindow | None:
    """Designer's main window as macOS sees it; None elsewhere."""
    return _MacWindow(mw) if sys.platform == 'darwin' else None


def _wait_unhidden(mac: _MacWindow, handle: QtGui.QWindow, limit: float) -> bool:
    """Waits, at most `limit` s, for macOS to no longer say Designer is hidden once it was unhidden: looked at as Qt's
    expose events for `handle`, the main window's, come, and every TICK ms. Returns whether macOS said so. The unhide
    takes as Designer's events run (shot3d.py's module docstring; REVIEW.md HLP-160). The window's exposure is no sign
    of it: the window can come back behind the active app's, and once covered whole Qt no longer exposes it (REVIEW.md
    HLP-166)."""
    spy = _event_signal(handle, ('Expose',))
    try:
        return _until(lambda: not mac.hidden(), limit, [spy.fired])
    finally:
        _unwatch(handle, spy)


def give_back_activation(started_hidden: bool = False) -> None:
    """Gives the keyboard back to the app in front before Designer, if Designer is the active app: Designer hidden, then
    shown without being made active (the module docstring). Left hidden when it was hidden, or `started_hidden`:
    becoming the active app unhides a hidden Designer (measured 2026-11-16: REVIEW.md SRV-161), so a Designer opened
    hidden reads shown by then. For launch_designer, once a Designer it started answers, in case that Designer became
    the active app anyway: one started hidden doesn't (REVIEW.md SRV-148, SRV-152, SRV-149). Each step is waited for on
    Qt's callbacks, ACTIVATION_WAIT at most: the hide until Designer is no longer the active app (Qt's
    applicationStateChanged), the show until macOS no longer says Designer is hidden (_wait_unhidden; REVIEW.md
    SRV-150, HLP-166).
    Prints what it did; nothing when Designer isn't the active app, or elsewhere than macOS."""
    mw = _main_window()
    mac = _mac_window(mw)
    if mac is None or not mac.active():
        return
    app = cast(QtGui.QGuiApplication, QtGui.QGuiApplication.instance())  # Designer's own: always there
    # hidden while active: not seen, as becoming the active app unhides Designer (REVIEW.md SRV-161), a defence;
    # test_a_designer_started_hidden_that_became_the_active_app_stays_hidden builds that state
    hidden = mac.hidden()
    mac.hide()  # the app active before it becomes active again
    _until(lambda: not mac.active(), ACTIVATION_WAIT, [app.applicationStateChanged])
    if hidden or started_hidden:
        print(
            'gave the keyboard back to the app in front before it, %s'
            % ('still hidden' if hidden else 'hidden again, as it was started')
            if not mac.active()
            else 'still the active app after it was hidden'
        )
        return
    top = mw.window()  # the top-level window: getMainWindow() is a page of it
    # held: a handle taken through a wrapper dropped at once is deleted by the next line (REVIEW.md SRV-155)
    handle = top.windowHandle()
    mac.unhide()
    _wait_unhidden(mac, handle, ACTIVATION_WAIT)
    print(
        'gave the keyboard back to the app in front before it'
        if not mac.active()
        else 'still the active app after it was hidden and shown again'
    )
