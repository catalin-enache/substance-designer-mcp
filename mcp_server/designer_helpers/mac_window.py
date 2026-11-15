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
- A Designer an agent starts becomes the active app as it starts, the one the keyboard types into, taking it from the
  app in front: the user's, or another agent's Designer. One that quits as the active app hands it back to the app
  active before it. Hidden (hide:), Designer makes the app active before it active again; shown again without being
  made active (unhideWithoutActivation), it stays so (2026-11-14, the front app read with lsappinfo: REVIEW.md SRV-148).
"""

import ctypes
import ctypes.util

from .core import _APP, Any, cast, sys
from .view3d import _settle

NS_VISIBLE = 2  # NSWindowOcclusionStateVisible: part of the window is on screen
NS_BELOW = -1  # NSWindowBelow, for orderWindow:relativeTo:
CG_ON_SCREEN = (1 << 0) | (1 << 4)  # kCGWindowListOptionOnScreenOnly, kCGWindowListExcludeDesktopElements
CG_ABOVE = (1 << 1) | (1 << 4)  # kCGWindowListOptionOnScreenAboveWindow, kCGWindowListExcludeDesktopElements
CF_UTF8 = 0x08000100  # kCFStringEncodingUTF8
CF_SINT64 = 4  # kCFNumberSInt64Type


class _MacWindow:
    """Designer's main window as macOS sees it, and the calls that put it on screen without making Designer the active
    app (shot3d.py), sent through the Objective-C runtime."""

    def __init__(self, mw: Any) -> None:  # Any: a Qt widget (screenshots.py: Qt widgets are Any in signatures)
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
    ) -> object:
        """objc_msgSend: `selector` sent to `receiver`, with nil as its argument (a selector without one ignores it)."""
        prototype = ctypes.CFUNCTYPE(result, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
        send = prototype(('objc_msgSend', self._objc))
        return cast(object, send(receiver, self._objc.sel_registerName(selector.encode()), None))

    def _object(self, receiver: int | None, selector: str) -> int | None:
        return cast(int | None, self._send(ctypes.c_void_p, receiver, selector))

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
        listed = self._object(self._app, 'windows')
        prototype = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong)
        at = prototype(('objc_msgSend', self._objc))
        count = cast(int, self._send(ctypes.c_ulong, listed, 'count'))
        return [cast(int, at(listed, self._objc.sel_registerName(b'objectAtIndex:'), i)) for i in range(count)]

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
        keys = [cf.CFStringCreateWithCString(None, name, CF_UTF8) for name in (b'kCGWindowNumber', b'kCGWindowLayer')]
        windows = cg.CGWindowListCopyWindowInfo(option, relative)
        try:
            found: list[tuple[int, int]] = []
            for i in range(cf.CFArrayGetCount(windows) if windows else 0):
                info = cf.CFArrayGetValueAtIndex(windows, i)
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


def _mac_window(mw: Any) -> _MacWindow | None:  # Any: a Qt widget (screenshots.py: Qt widgets are Any in signatures)
    """Designer's main window as macOS sees it; None elsewhere."""
    return _MacWindow(mw) if sys.platform == 'darwin' else None


def give_back_activation() -> None:
    """Gives the keyboard back to the app in front before Designer, if Designer is the active app: Designer hidden, then
    shown without being made active (the module docstring). For launch_designer, once a Designer it started answers,
    since one becomes the active app as it starts (REVIEW.md SRV-148). Prints what it did; nothing when Designer isn't
    the active app, or elsewhere than macOS."""
    mac = _mac_window(_APP.getQtForPythonUIMgr().getMainWindow())  # type: ignore[no-untyped-call]  # sd: no annotations
    if mac is None or not mac.active():
        return
    mac.hide()  # the app active before it becomes active again
    _settle(1.0)
    mac.unhide()
    _settle(1.0)
    print(
        'gave the keyboard back to the app in front before it'
        if not mac.active()
        else 'still the active app after it was hidden and shown again'
    )
