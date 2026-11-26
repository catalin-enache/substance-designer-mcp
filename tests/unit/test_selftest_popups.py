"""The self-test's watch of Designer's popups on screen (editor_panels_and_fit/popups.py; REVIEW.md HLP-134)."""

import ctypes
import os
import sys
import threading
import time
from types import ModuleType, SimpleNamespace
from typing import Protocol, cast

import pytest
from selftest_fakes import fresh


@pytest.fixture
def popups() -> ModuleType:
    return fresh('editor_panels_and_fit.popups')


def test_popups_are_seen_from_the_first_sample_showing_one_to_the_last_of_the_longest_spell(popups: ModuleType) -> None:
    assert popups.shown_ms([]) == 0.0
    assert popups.shown_ms([[2.0]]) == 0.0  # one sample: seen, for less than a sample's time
    assert popups.shown_ms([[2.0, 2.004, 2.009]]) == pytest.approx(9.0)
    assert popups.shown_ms([[2.0, 2.003], [3.197, 3.2, 3.21]]) == pytest.approx(13.0)


def test_two_glimpses_far_apart_are_two_spells_on_screen(popups: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-953, measured: a graph= shot on a linked view opens two Explorer menus, the step's and the
    # put-back's relink; a glimpse of each, 1.2 s apart, read as 1197 ms on screen. Whether each sample shows a popup,
    # in turn, then none does; a time taken at each sample showing one
    shown = [True, False, True, True]
    times = iter([2.0, 3.197, 3.2])
    done = threading.Event()

    def seen(*args: object) -> tuple[bool, bool]:
        if not shown:
            done.set()
        return True, shown.pop(0) if shown else False

    monkeypatch.setitem(vars(popups), '_seen', seen)
    cf = SimpleNamespace(CFStringCreateWithCString=lambda *args: 1, CFRelease=lambda key: None)
    monkeypatch.setitem(vars(popups), 'libraries', lambda: (None, cf))
    monkeypatch.setitem(vars(popups), 'time', SimpleNamespace(monotonic=lambda: next(times)))
    with popups.PopupWatch(PID) as watch:
        assert done.wait(10)  # a safety net: the watch's thread takes the samples at once
    assert watch.spells == [[2.0], [3.197, 3.2]] and watch.shown_ms == pytest.approx(3.0)  # the second spell


@pytest.mark.skipif(sys.platform != 'darwin', reason="the window server's list is macOS's")
@pytest.mark.parametrize('layer', [None, 0], ids=['popups', 'every window: REVIEW.md TST-472'])
def test_the_watch_samples_the_window_list_and_sees_no_popup_of_a_process_with_none(
    popups: ModuleType, layer: int | None
) -> None:
    # this test's own process has no window at all. Looked at every 0.1 s until it has sampled, 10 s at most: a fixed
    # sleep sampled as fast as the window server answered, which a loaded machine slows (REVIEW.md TST-469)
    with popups.PopupWatch(os.getpid(), *(() if layer is None else (layer,))) as watch:
        deadline = time.monotonic() + 10
        while watch.samples <= 10 and time.monotonic() < deadline:
            time.sleep(0.1)
    assert watch.samples > 10 and watch.listed == 0 and watch.times == [] and watch.shown_ms == 0.0


PID = 42
POPUP, NORMAL = 101, 0  # window layers


# a window as Server lists it: (layer, alpha, pid), and its bounds for test_selftest_window_server's Bounded
FakeWindow = tuple[int, float, int] | tuple[int, float, int, tuple[float, float, float, float]]


class _Number(Protocol):
    value: int | float  # a ctypes number's value: a c_int64's or a c_double's here


class _ByRef(Protocol):
    """ctypes.byref()'s result, as CFNumberGetValue writes through it. Typeshed's _CArgObject names no attribute."""

    _obj: _Number  # the ctypes number it points at


class Server:
    """CoreGraphics and CoreFoundation as _seen calls them, faked: the window server's list of windows, each a
    (layer, alpha, pid) read by its index (the keys 0, 1 and 2); no list at all when `listed` is False."""

    def __init__(self, *windows: FakeWindow, listed: bool = True) -> None:
        self.windows = windows
        self.listed = listed
        self.released: list[str] = []

    # the list's reference is a string here, 'the list'
    def CGWindowListCopyWindowInfo(self, option: int, relative: int) -> str | None:
        return 'the list' if self.listed else None

    def CFArrayGetCount(self, listed: str) -> int:
        return len(self.windows)

    def CFArrayGetValueAtIndex(self, listed: str, i: int) -> FakeWindow:
        return self.windows[i]

    def CFDictionaryGetValue(self, info: FakeWindow, key: int) -> int | float | tuple[float, float, float, float]:
        return info[key]

    def CFNumberGetValue(self, number: int | float, kind: int, out: _ByRef) -> bool:
        out._obj.value = number  # the ctypes value byref() points at
        return True

    def CFRelease(self, ref: str) -> None:
        self.released.append(ref)


@pytest.mark.parametrize(
    'windows, seen',
    [
        (((POPUP, 1.0, PID),), (True, True)),
        (((POPUP, 0.0, PID),), (True, False)),
        (((NORMAL, 1.0, PID),), (True, False)),
        (((POPUP, 1.0, PID + 1),), (False, False)),
        (((NORMAL, 0.0, PID), (POPUP, 0.5, PID)), (True, True)),
        ((), (False, False)),
    ],
    ids=['a popup shown', 'a popup transparent', 'a normal window', "another app's popup", 'the second', 'none'],
)
def test_a_sample_says_whether_the_list_holds_a_window_of_the_process_and_a_popup_of_its_shown(
    popups: ModuleType, windows: tuple[tuple[int, float, int], ...], seen: tuple[bool, bool]
) -> None:
    # REVIEW.md TST-405: a watch that sees no window of Designer's can't tell a popup on screen from none
    server = Server(*windows)
    library = cast(ctypes.CDLL, server)
    assert popups._seen(library, library, [0, 1, 2], PID) == seen
    assert server.released == ['the list']


def test_no_list_is_no_window_seen(popups: ModuleType) -> None:
    server = Server(listed=False)
    library = cast(ctypes.CDLL, server)
    assert popups._seen(library, library, [0, 1, 2], PID) == (False, False) and server.released == []
