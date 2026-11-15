"""Designer's popups as macOS's window server lists them, watched from the self-test's own process while a tool call
runs: a thread samples CoreGraphics' list of the windows on screen (about 3,000 times a second, measured) and keeps
the times a window of one process was there at popup level or above, at an opacity above 0. It counts the samples
that listed any window of that process, so a watch that sees none of them isn't taken for one that saw no popup
(REVIEW.md TST-405): through a 3D shot of Designer's minimized window, 12,460 samples of 12,626 listed one of
Designer's (2026-11-14). For the 3D shot's
Explorer menu, which otherwise showed during a shot of a window made transparent (REVIEW.md HLP-134). macOS only,
through ctypes, as designer_helpers/mac_window.py reads the same list inside Designer. And that menu's look read
inside Designer, as its action is picked (menu_look).
"""

import ctypes
import ctypes.util
import threading
import time
from textwrap import dedent
from types import TracebackType

POPUP_LAYER = 100  # a window's layer: 0 for normal windows, 101 for popup menus (NSPopUpMenuWindowLevel)
CG_ON_SCREEN = (1 << 0) | (1 << 4)  # kCGWindowListOptionOnScreenOnly, kCGWindowListExcludeDesktopElements
CF_UTF8 = 0x08000100  # kCFStringEncodingUTF8
CF_SINT64 = 4  # kCFNumberSInt64Type
CF_DOUBLE = 13  # kCFNumberDoubleType


# shoot_3d with graph=, the Explorer's menu's look as macOS sees its window, as the menu's action is picked
# (MENU opacity=... through=...)
_MENU_LOOK = dedent("""
    _real_pick = _MenuPick.pick
    def _pick(self, menu):
        if menu is not None and menu is not self.before:
            seen = _MacWindow(menu)
            print('MENU opacity=%g through=%s' % seen.appearance(seen.windows(False)[0]))
        return _real_pick(self, menu)
    _MenuPick.pick = _pick
    shoot_3d(PATH, graph=GRAPH)
""")


def menu_look(path: str, graph: str) -> str:
    """shoot_3d(path, graph=graph), printing the Explorer's menu's look as macOS sees its window as its action is
    picked (MENU opacity=... through=...). Run with the helpers' text."""
    return _MENU_LOOK.replace('PATH', repr(path)).replace('GRAPH', repr(graph))


# shoot_3d with graph=, the Explorer's menu closed as soon as the shot's fade made it transparent, before its action
# is picked, as something else may close it (REVIEW.md HLP-146): what the shot said (SHOT ...), then the look of the
# menu's window as macOS sees it (MENU_AFTER opacity=... through=...). The Explorer deletes the menu as it closes, and
# its window was seen to stay: held here, so it stays safe to read
_CLOSED_EARLY = dedent("""
    from PySide6 import QtCore
    _real_fade = _MenuPick.fade
    _faded = []
    def _fade(self, menu):
        done = _real_fade(self, menu)
        if done:
            seen = _MacWindow(menu)
            seen.hold(seen.windows(False)[0])
            _faded.append(seen)
            QtCore.QTimer.singleShot(0, menu.close)
        return done
    _MenuPick.fade = _fade
    try:
        shoot_3d(PATH, graph=GRAPH)
        print('SHOT taken')
    except RuntimeError as e:
        print('SHOT refused: %s' % str(e).splitlines()[0])
    for seen in _faded:
        window = seen.windows(False)[0]
        print('MENU_AFTER opacity=%g through=%s' % seen.appearance(window))
        seen.let_go(window)
""")


def closed_early(path: str, graph: str) -> str:
    """shoot_3d(path, graph=graph), the Explorer's menu closed as the shot's fade makes it transparent (REVIEW.md
    HLP-146), printing what the shot said (SHOT ...) and the look of the menu's window after it (MENU_AFTER ...). Run
    with the helpers' text."""
    return _CLOSED_EARLY.replace('PATH', repr(path)).replace('GRAPH', repr(graph))


def shown_ms(times: list[float]) -> float:
    """How long popups were seen, in ms: from the first sample that showed one to the last; 0 when none did."""
    return (times[-1] - times[0]) * 1000 if times else 0.0


def _libraries() -> tuple[ctypes.CDLL, ctypes.CDLL]:
    """CoreGraphics and CoreFoundation, their functions typed."""
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
    return cg, cf


def _seen(cg: ctypes.CDLL, cf: ctypes.CDLL, keys: list[int], pid: int) -> tuple[bool, bool]:
    """Whether the list of the windows on screen holds a window of process `pid`, and whether one of them is at popup
    level or above with an opacity above 0. `keys`: the dictionary keys kCGWindowLayer, kCGWindowAlpha and
    kCGWindowOwnerPID."""
    listed = cg.CGWindowListCopyWindowInfo(CG_ON_SCREEN, 0)
    there = shown = False
    try:
        for i in range(cf.CFArrayGetCount(listed) if listed else 0):
            info = cf.CFArrayGetValueAtIndex(listed, i)
            layer, owner, alpha = ctypes.c_int64(), ctypes.c_int64(), ctypes.c_double()
            cf.CFNumberGetValue(cf.CFDictionaryGetValue(info, keys[0]), CF_SINT64, ctypes.byref(layer))
            cf.CFNumberGetValue(cf.CFDictionaryGetValue(info, keys[1]), CF_DOUBLE, ctypes.byref(alpha))
            cf.CFNumberGetValue(cf.CFDictionaryGetValue(info, keys[2]), CF_SINT64, ctypes.byref(owner))
            if owner.value == pid:
                there = True
                shown = shown or (layer.value >= POPUP_LAYER and alpha.value > 0)
        return there, shown
    finally:
        if listed:
            cf.CFRelease(listed)


class PopupWatch:
    """While inside it, samples the window server's list and keeps the times (`times`, monotonic seconds) a popup of
    process `pid` was on screen; `samples` counts the samples taken, `listed` those that listed a window of `pid`."""

    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.samples = 0
        self.listed = 0
        self.times: list[float] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, daemon=True)

    def __enter__(self) -> 'PopupWatch':
        self._thread.start()
        return self

    def __exit__(
        self, kind: type[BaseException] | None, value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        self._stop.set()
        self._thread.join()

    @property
    def shown_ms(self) -> float:
        return shown_ms(self.times)

    def _watch(self) -> None:
        cg, cf = _libraries()
        names = (b'kCGWindowLayer', b'kCGWindowAlpha', b'kCGWindowOwnerPID')
        keys: list[int] = [cf.CFStringCreateWithCString(None, name, CF_UTF8) for name in names]
        try:
            while not self._stop.is_set():
                there, shown = _seen(cg, cf, keys, self.pid)
                if shown:
                    self.times.append(time.monotonic())
                self.listed += there
                self.samples += 1
        finally:
            for key in keys:
                cf.CFRelease(key)
