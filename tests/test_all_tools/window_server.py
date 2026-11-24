"""macOS's window server as the self-test reads it from its own process, through ctypes and lsappinfo: CoreGraphics'
list of the windows on screen, front to back, each with its layer, opacity and process, and the active app. The
popups' watch (editor_panels_and_fit/popups.py) and the front watch here use it. macOS only.

The front watch is for what the self-test does on the user's screen: a Designer launch_designer starts, and every
editor_panels_and_fit check up to the window checks set up off screen, must neither make Designer the active app nor
bring a window of its in front of the other apps' windows (REVIEW.md SRV-149, TST-473). A thread samples both every
FRONT_EVERY s meanwhile. The Designer's process may be known only once the call returns, so each sample keeps what it
saw, and stayed_off_screen (the launch's) and stayed_behind (those checks') read the samples for that process after. A window counts as in front only over a window of another app it overlaps (covering): alone
on screen, as on a desktop the user has no window on, it is in front of nothing of theirs. fronts_said gives each
stretch in front a line, up to FRONTS_SAID of them: its window, the one it covered and that one's process, and the
checks recorded around its start. The watch names each app as a normal window of its first shows, since one may have
quit by the time the check reports.
"""

import ctypes
import ctypes.util
import itertools
import re
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import NamedTuple

CG_ON_SCREEN = (1 << 0) | (1 << 4)  # kCGWindowListOptionOnScreenOnly, kCGWindowListExcludeDesktopElements
CF_UTF8 = 0x08000100  # kCFStringEncodingUTF8
CF_SINT64 = 4  # kCFNumberSInt64Type
CF_DOUBLE = 13  # kCFNumberDoubleType
# what a sample reads of each window, in order
KEYS = (b'kCGWindowLayer', b'kCGWindowAlpha', b'kCGWindowOwnerPID', b'kCGWindowBounds')
# a sampling, not a wait for a state: the shorter it is, the briefer a window the watch sees (REVIEW.md TST-456)
FRONT_EVERY = 0.05  # s between a front watch's samples
FRONTS_SAID = 10  # the stretches in front fronts_said says, the others counted

Rect = tuple[float, float, float, float]  # a window's bounds on screen: x, y, width, height
Window = tuple[int, float, int, Rect]  # a window on screen: (layer, opacity, process, bounds); layer 0: normal


class Sample(NamedTuple):
    """What a front watch saw at one moment."""

    at: float  # time.monotonic(), once the windows were read (REVIEW.md TST-503)
    active: int | None  # the active app's process; None when it couldn't be read
    windows: tuple[Window, ...]  # on screen, front to back


class Front(NamedTuple):
    """A stretch of a front watch's samples in which a window of a process was in front of another app's (fronts)."""

    at: float  # its first sample's time.monotonic()
    lasted: float  # s, until the sample after its last
    window: Window  # the process's window in front, at its first sample
    covered: Window  # the other app's window it covered then


def libraries() -> tuple[ctypes.CDLL, ctypes.CDLL]:
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
    cg.CGRectMakeWithDictionaryRepresentation.restype = ctypes.c_bool
    cg.CGRectMakeWithDictionaryRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    return cg, cf


def on_screen(cg: ctypes.CDLL, cf: ctypes.CDLL, keys: Sequence[int]) -> tuple[Window, ...]:
    """The windows on screen, front to back; none when the window server returned no list. `keys`: the dictionary
    keys KEYS names, created by the caller."""
    listed: int | None = cg.CGWindowListCopyWindowInfo(CG_ON_SCREEN, 0)  # a CFArrayRef, None for NULL
    if not listed:
        return ()
    try:
        seen: list[Window] = []
        for i in range(cf.CFArrayGetCount(listed)):
            info: int | None = cf.CFArrayGetValueAtIndex(listed, i)  # a CFDictionaryRef
            layer, alpha, owner = ctypes.c_int64(), ctypes.c_double(), ctypes.c_int64()
            cf.CFNumberGetValue(cf.CFDictionaryGetValue(info, keys[0]), CF_SINT64, ctypes.byref(layer))
            cf.CFNumberGetValue(cf.CFDictionaryGetValue(info, keys[1]), CF_DOUBLE, ctypes.byref(alpha))
            cf.CFNumberGetValue(cf.CFDictionaryGetValue(info, keys[2]), CF_SINT64, ctypes.byref(owner))
            rect = (ctypes.c_double * 4)()  # a CGRect: origin, then size
            cg.CGRectMakeWithDictionaryRepresentation(cf.CFDictionaryGetValue(info, keys[3]), rect)
            seen.append((layer.value, alpha.value, owner.value, (rect[0], rect[1], rect[2], rect[3])))
        return tuple(seen)
    finally:
        cf.CFRelease(listed)


def windows_now() -> tuple[Window, ...]:
    """The windows on screen now, front to back (on_screen)."""
    cg, cf = libraries()
    keys: list[int] = [cf.CFStringCreateWithCString(None, name, CF_UTF8) for name in KEYS]
    try:
        return on_screen(cg, cf, keys)
    finally:
        for key in keys:
            cf.CFRelease(key)


def shows_a_window(windows: Sequence[Window], pid: int) -> bool:
    """Whether process `pid` has a normal window (layer 0) in `windows`, at an opacity above 0."""
    return any(layer == 0 and alpha > 0 and owner == pid for layer, alpha, owner, _ in windows)


def active_shows_a_window(active: int | None, windows: Sequence[Window]) -> bool | None:
    """Whether the active app, process `active`, has a normal window in `windows` (shows_a_window); None when that
    can't be told: no active app read, or no window listed, which a desktop never has (its menu bar's)."""
    if active is None or not windows:
        return None
    return shows_a_window(windows, active)


def pid_of(info: str) -> int | None:
    """The process in what `lsappinfo info -only pid` printed; None when there is none. macOS 26 printed "pid"=1234,
    macOS 27.2.1 pid = 1234 (REVIEW.md TST-836)."""
    m = re.search(r'\bpid"?\s*=\s*(\d+)', info)
    return int(m.group(1)) if m else None


def active_app() -> int | None:
    """The active app's process, as lsappinfo says; None when it can't be read."""
    try:
        front = subprocess.run(['lsappinfo', 'front'], capture_output=True, text=True, timeout=5).stdout.strip()
        info = subprocess.run(
            ['lsappinfo', 'info', '-only', 'pid', front], capture_output=True, text=True, timeout=5
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return pid_of(info)


class FrontWatch:
    """While inside it, a thread samples the active app and the windows on screen every FRONT_EVERY s (`samples`), and
    names each app as a normal window of its first shows at an opacity above 0 (`names`: process_name). Off macOS
    (`watching` False) it samples nothing."""

    def __init__(self, watching: bool = True) -> None:
        self.watching = watching
        self.samples: list[Sample] = []
        self.names: dict[int, str] = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, daemon=True)

    def __enter__(self) -> 'FrontWatch':
        if self.watching:
            self._thread.start()
        return self

    def __exit__(
        self, kind: type[BaseException] | None, value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        self._stop.set()
        if self.watching:
            self._thread.join()

    def _watch(self) -> None:
        cg, cf = libraries()
        keys: list[int] = [cf.CFStringCreateWithCString(None, name, CF_UTF8) for name in KEYS]
        try:
            while not self._stop.is_set():
                active = active_app()
                windows = on_screen(cg, cf, keys)
                # timed as the windows were read, which said() places among the checks (REVIEW.md TST-503)
                self.samples.append(Sample(time.monotonic(), active, windows))
                for _, _, owner, _ in _shown(windows):
                    if owner not in self.names:
                        self.names[owner] = process_name(owner)
                self._stop.wait(FRONT_EVERY)
        finally:
            for key in keys:
                cf.CFRelease(key)


def _shown(windows: Sequence[Window]) -> list[Window]:
    """The normal windows (layer 0) of `windows` at an opacity above 0: those that can cover or be covered."""
    return [window for window in windows if window[0] == 0 and window[1] > 0]


def _overlap(a: Rect, b: Rect) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def covering(windows: Sequence[Window], pid: int, over: int | None = None) -> tuple[Window, Window] | None:
    """The first normal window (layer 0) of process `pid`, at an opacity above 0, in front of a normal window of another
    process, at an opacity above 0, that it overlaps (covering some of it), with that window; None when there is none.
    With `over`, only that process's windows count. `windows` front to back."""
    shown = _shown(windows)
    for i, window in enumerate(shown):
        if window[2] != pid:
            continue
        for below in shown[i + 1 :]:
            other = below[2]
            if other != pid and (over is None or other == over) and _overlap(window[3], below[3]):
                return window, below
    return None


def fronts(samples: Sequence[Sample], pid: int, active_only: bool = False) -> list[Front]:
    """The stretches of `samples` in which a window of process `pid` was in front of another app's, as stayed_behind
    counts them: while `pid` isn't the active app, each sample until the next. With `active_only`, only in front of the
    active app's windows, while one was read."""
    found: list[Front] = []
    going = False  # whether the sample before counted in front
    for here, after in itertools.pairwise(samples):
        pair = None
        if here.active != pid and (here.active is not None or not active_only):
            pair = covering(here.windows, pid, here.active if active_only else None)
        if pair is None:
            going = False
        elif going:  # the stretch goes on
            found[-1] = found[-1]._replace(lasted=found[-1].lasted + after.at - here.at)
        else:
            found.append(Front(here.at, after.at - here.at, *pair))
            going = True
    return found


def stayed_behind(samples: Sequence[Sample], pid: int, active_only: bool = False) -> tuple[bool, str]:
    """Whether process `pid` was never the active app and never had a window in front of another app's over `samples`
    (covering), and a check's detail. With `active_only`, only the active app's windows count, the ones the
    user works in: a Designer started from its binary came up behind them, but over the other apps' (2026-11-15). No
    check passes it since launch_designer opens Designer hidden (REVIEW.md SRV-152). Each sample counts
    until the next. False with fewer than two samples, with none listing a window of `pid` at an opacity above 0, or
    none reading the active app: such a watch can't tell (REVIEW.md TST-405, TST-441). Its windows above layer 0 (a splash fading out, measured) are said, not
    judged."""
    active = sum(after.at - here.at for here, after in itertools.pairwise(samples) if here.active == pid)
    front = sum(stretch.lasted for stretch in fronts(samples, pid, active_only))
    listed = sum(any(owner == pid and alpha > 0 for _, alpha, owner, _ in s.windows) for s in samples)
    read = sum(s.active is not None for s in samples)
    above = [
        (layer, alpha)
        for s in samples
        for layer, alpha, owner, _ in s.windows
        if owner == pid and layer > 0 and alpha > 0
    ]
    return (
        len(samples) >= 2 and listed > 0 and read > 0 and active == 0.0 and front == 0.0,
        'the active app %.2f s, its window in front of %s %.2f s; %d samples, %d listing its windows, %d reading the '
        'active app (REVIEW.md TST-468); above the normal windows: %s'
        % (
            active,
            "the active app's" if active_only else "another app's",
            front,
            len(samples),
            listed,
            read,
            '%d samples, at layer %s' % (len(above), ', '.join(str(n) for n in sorted({lay for lay, _ in above})))
            if above
            else 'none',
        ),
    )


def process_name(pid: int) -> str:
    """The name of process `pid`, as ps gives it; 'gone' once it has ended, or when ps can't be run."""
    try:
        name = subprocess.run(['ps', '-o', 'comm=', '-p', str(pid)], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return 'gone'
    return name.strip() or 'gone'


def _place(window: Window) -> str:
    x, y, width, height = window[3]
    return '(%.0f, %.0f) %.0f x %.0f' % (x, y, width, height)


def said(front: Front, start: float, marks: Sequence[tuple[float, str]], names: Mapping[int, str]) -> str:
    """`front` in a line: when it began (s after `start`) and how long it lasted, its window and the window it covered,
    with that one's process, and the checks recorded around its start. `marks`: each check's time.monotonic() and name, in order
    (common.checked). `names`: the processes' names the watch read (FrontWatch.names); ps names one it didn't."""
    before = [name for at, name in marks if at <= front.at]
    after = [name for at, name in marks if at > front.at]
    parts = (['after check "%s"' % before[-1]] if before else []) + (['before check "%s"' % after[0]] if after else [])
    around = ' and '.join(parts) or 'with no check recorded'
    other = front.covered[2]
    return 'at %.2f s, for %.2f s: its window at %s, opacity %.2f, over the window of process %d (%s) at %s, %s' % (
        front.at - start,
        front.lasted,
        _place(front.window),
        front.window[1],
        other,
        names.get(other) or process_name(other),
        _place(front.covered),
        around,
    )


def fronts_said(
    samples: Sequence[Sample], pid: int, marks: Sequence[tuple[float, str]], names: Mapping[int, str]
) -> list[str]:
    """The stretches in which a window of process `pid` was in front of another app's (fronts), a line each (said), the
    first FRONTS_SAID of them, then how many more."""
    found = fronts(samples, pid)
    lines = [said(front, samples[0].at, marks, names) for front in found[:FRONTS_SAID]]
    if len(found) > FRONTS_SAID:
        lines.append('and %d more' % (len(found) - FRONTS_SAID))
    return lines


def stayed_off_screen(samples: Sequence[Sample], pid: int) -> tuple[bool, str]:
    """Whether process `pid` was never the active app and no window of its was on screen at an opacity above 0, at any
    of `samples`, and a check's detail: a Designer launch_designer starts hidden (REVIEW.md SRV-152). False with fewer
    than two samples, none listing any window, or none reading the active app: such a watch can't tell (REVIEW.md
    TST-441)."""
    active = sum(s.active == pid for s in samples)
    shown = sum(any(owner == pid and alpha > 0 for _, alpha, owner, _ in s.windows) for s in samples)
    seeing = sum(bool(s.windows) for s in samples)
    read = sum(s.active is not None for s in samples)
    return (
        len(samples) >= 2 and seeing > 0 and read > 0 and active == 0 and shown == 0,
        'the active app at %d samples, a window of its on screen at %d; %d samples, %d listing any window, %d reading '
        'the active app' % (active, shown, len(samples), seeing, read),
    )
