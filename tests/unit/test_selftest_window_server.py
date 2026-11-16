"""The self-test's reading of macOS's window server: the windows on screen and the front watch launch_designer's
check uses (window_server.py; REVIEW.md SRV-149)."""

import ctypes
import os
import sys
import time
from types import ModuleType
from typing import cast

import pytest
from selftest_fakes import fresh
from test_selftest_popups import NORMAL, PID, POPUP, Server

OTHER = PID + 1  # another app's process
WHOLE, LEFT, RIGHT = (0.0, 0.0, 1000.0, 800.0), (0.0, 0.0, 400.0, 800.0), (500.0, 0.0, 400.0, 800.0)  # x, y, w, h


class Bounded(Server):
    """The fake window server of test_selftest_popups, each window's bounds too: (layer, alpha, pid, rect), read by
    the keys 0 to 3."""

    def CGRectMakeWithDictionaryRepresentation(
        self, rect: tuple[float, float, float, float], out: ctypes.Array[ctypes.c_double]
    ) -> bool:
        for i, value in enumerate(rect):
            out[i] = value  # the four doubles' array on_screen passes
        return True


@pytest.fixture
def window_server() -> ModuleType:
    return cast(ModuleType, fresh('window_server'))


Seen = tuple[int | None, tuple[tuple[int, float, int, tuple[float, float, float, float]], ...]]


# window_server.Sample, a NamedTuple, by its fields (at, active, windows): each test reads a fresh module's
Sampled = tuple[float, int | None, tuple[tuple[int, float, int, tuple[float, float, float, float]], ...]]


def samples(window_server: ModuleType, *seen: Seen) -> list[Sampled]:
    """One sample a second, each (the active app, the windows on screen front to back)."""
    return [window_server.Sample(float(i), active, windows) for i, (active, windows) in enumerate(seen)]


def test_the_windows_on_screen_are_read_front_to_back_with_their_bounds(window_server: ModuleType) -> None:
    server = Bounded((NORMAL, 1.0, OTHER, WHOLE), (POPUP, 0.5, PID, LEFT))
    library = cast(ctypes.CDLL, server)
    assert window_server.on_screen(library, library, [0, 1, 2, 3]) == (
        (NORMAL, 1.0, OTHER, WHOLE),
        (POPUP, 0.5, PID, LEFT),
    )
    assert server.released == ['the list']


def test_no_list_is_no_window(window_server: ModuleType) -> None:
    server = Bounded(listed=False)
    library = cast(ctypes.CDLL, server)
    assert window_server.on_screen(library, library, [0, 1, 2, 3]) == () and server.released == []


@pytest.mark.parametrize(
    'windows, covers',
    [
        (((NORMAL, 1.0, PID, LEFT), (NORMAL, 1.0, OTHER, WHOLE)), True),
        (((NORMAL, 1.0, PID, LEFT), (NORMAL, 1.0, OTHER, RIGHT)), False),
        (((NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, LEFT)), False),
        (((NORMAL, 0.0, PID, WHOLE), (NORMAL, 1.0, OTHER, WHOLE)), False),
        (((NORMAL, 1.0, PID, WHOLE), (NORMAL, 0.0, OTHER, WHOLE)), False),
        (((NORMAL, 1.0, PID, WHOLE), (NORMAL, 1.0, PID, LEFT)), False),
        (((POPUP, 1.0, PID, WHOLE), (NORMAL, 1.0, OTHER, WHOLE)), False),
        (((NORMAL, 1.0, PID, LEFT),), False),
    ],
    ids=[
        "over another app's",
        "beside another app's",
        "behind another app's",
        'transparent',
        "over another app's transparent one",
        'over its own',
        'at popup level',
        'alone on screen',
    ],
)
def test_a_window_counts_in_front_only_over_another_apps_window_it_overlaps(
    window_server: ModuleType, windows: tuple[tuple[int, float, int, tuple[float, ...]], ...], covers: bool
) -> None:
    # alone on screen (another desktop, a full-screen app's space), Designer's window is in front of nothing of the
    # user's: a watch taking the frontmost window for one in front failed a run with nothing in front (2026-11-15)
    assert window_server.in_front_of_another(windows, PID) is covers


def test_the_active_apps_process_is_read_from_lsappinfo(window_server: ModuleType) -> None:
    assert window_server.pid_of('"pid"=1920\n') == 1920
    assert window_server.pid_of('') is None


def test_a_designer_never_active_nor_in_front_stayed_behind(window_server: ModuleType) -> None:
    # its window behind the other app's all along, and its splash fading out above them once (measured)
    seen = samples(
        window_server,
        (OTHER, ((NORMAL, 1.0, OTHER, WHOLE),)),
        (OTHER, ((NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, LEFT))),
        (OTHER, ((POPUP, 0.5, PID, LEFT), (NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, LEFT))),
        (OTHER, ((NORMAL, 1.0, PID, LEFT),)),  # alone on screen: in front of nothing of another app's
    )
    ok, said = window_server.stayed_behind(seen, PID)
    assert ok, said
    assert said.startswith("the active app 0.00 s, its window in front of another app's 0.00 s; 4 samples, 3 listing")
    assert said.endswith('above the normal windows: 1 samples, at layer 101')


@pytest.mark.parametrize(
    'seen, active, front',
    [
        (
            ((PID, ((NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, LEFT))), (OTHER, ((NORMAL, 1.0, PID, LEFT),))),
            '1.00',
            '0.00',
        ),
        (
            ((OTHER, ((NORMAL, 1.0, PID, LEFT), (NORMAL, 1.0, OTHER, WHOLE))), (OTHER, ((NORMAL, 1.0, PID, LEFT),))),
            '0.00',
            '1.00',
        ),
    ],
    ids=['the active app', 'its window in front'],
)
def test_a_designer_the_active_app_or_in_front_didnt_stay_behind(
    window_server: ModuleType,
    seen: tuple[Seen, ...],
    active: str,
    front: str,
) -> None:
    ok, said = window_server.stayed_behind(samples(window_server, *seen), PID)
    assert not ok
    assert said.startswith("the active app %s s, its window in front of another app's %s s" % (active, front))


@pytest.mark.parametrize(
    'seen',
    [
        ((OTHER, ((NORMAL, 1.0, OTHER, WHOLE),)), (OTHER, ((NORMAL, 1.0, OTHER, WHOLE),))),
        ((OTHER, ((NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, LEFT))),),
        (),
        (
            (None, ((NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, RIGHT))),
            (None, ((NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, RIGHT))),
        ),
    ],
    ids=[
        'none of its windows listed',
        'one sample',
        'none',
        'the active app never read',
    ],  # the last: REVIEW.md TST-441
)
def test_a_watch_that_cant_tell_isnt_taken_for_one_that_stayed_behind(
    window_server: ModuleType, seen: tuple[Seen, ...]
) -> None:
    # REVIEW.md TST-405: a watch that never saw the process's windows can't tell them behind from not there
    assert window_server.stayed_behind(samples(window_server, *seen), PID)[0] is False


def test_stayed_behinds_detail_says_how_many_samples_read_the_active_app(window_server: ModuleType) -> None:
    # REVIEW.md TST-468: TST-441's "say how many did" held for stayed_off_screen only; a watch that never read the
    # active app failed with a detail of zeros, which reads as a pass
    unread = (None, ((NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, RIGHT)))
    ok, said = window_server.stayed_behind(samples(window_server, unread, unread), PID)
    assert not ok and '0 reading the active app' in said, said


@pytest.mark.skipif(sys.platform != 'darwin', reason="the window server's list is macOS's")
def test_the_front_watch_samples_the_active_app_and_the_windows_on_screen(window_server: ModuleType) -> None:
    # REVIEW.md TST-426: it slept 0.3 s, a time; the samples are looked at every 100 ms, 30 s at most
    deadline = time.monotonic() + 30
    with window_server.FrontWatch() as watch:
        while len(watch.samples) < 2 and time.monotonic() < deadline:
            time.sleep(0.1)
    assert len(watch.samples) >= 2
    # a locked screen or a session without one may name no active app at some samples
    assert any(isinstance(s.active, int) for s in watch.samples), 'lsappinfo names the active app'
    assert all(owner != os.getpid() for s in watch.samples for _, _, owner, _ in s.windows), 'this process has none'


@pytest.mark.parametrize(
    'windows, shows',
    [
        (((NORMAL, 1.0, OTHER, WHOLE),), True),
        (((NORMAL, 0.0, OTHER, WHOLE),), False),
        (((POPUP, 1.0, OTHER, WHOLE),), False),
        (((NORMAL, 1.0, PID, WHOLE),), False),
        ((), False),
    ],
    ids=['a normal window', 'a transparent one', 'at popup level', "another app's", 'none'],
)
def test_an_app_shows_a_window_when_one_of_its_normal_windows_is_on_screen_opaque(
    window_server: ModuleType, windows: tuple[tuple[int, float, int, tuple[float, ...]], ...], shows: bool
) -> None:
    # REVIEW.md HLP-160: the shot's unhide check judges only while the active app shows a window Designer's could go
    # behind
    assert window_server.shows_a_window(windows, OTHER) is shows


@pytest.mark.skipif(sys.platform != 'darwin', reason="the window server's list is macOS's")
def test_the_windows_on_screen_now_are_read_with_their_owners(window_server: ModuleType) -> None:
    windows = window_server.windows_now()
    assert isinstance(windows, tuple)
    assert windows, 'a desktop lists its menu bar at least: a reader that failed lists nothing (REVIEW.md TST-445)'
    assert all(owner != os.getpid() for _, _, owner, _ in windows), 'this process has none'


def test_off_macos_the_front_watch_samples_nothing(window_server: ModuleType) -> None:
    with window_server.FrontWatch(watching=False) as watch:
        assert watch.samples == []
    assert watch.samples == []


def test_over_one_app_only_that_apps_windows_count(window_server: ModuleType) -> None:
    # launch_designer's: a Designer starting comes up behind the active app's window, over the others' (2026-11-15)
    third = OTHER + 1
    windows = ((NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, LEFT), (NORMAL, 1.0, third, WHOLE))
    assert window_server.in_front_of_another(windows, PID)
    assert not window_server.in_front_of_another(windows, PID, over=OTHER)
    assert window_server.in_front_of_another(windows, PID, over=third)


def test_behind_the_active_app_counts_only_its_windows(window_server: ModuleType) -> None:
    third = OTHER + 1
    seen = samples(
        window_server,
        (OTHER, ((NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, LEFT), (NORMAL, 1.0, third, WHOLE))),
        (OTHER, ((NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, LEFT), (NORMAL, 1.0, third, WHOLE))),
    )
    assert not window_server.stayed_behind(seen, PID)[0], "in front of another app's"
    ok, said = window_server.stayed_behind(seen, PID, active_only=True)
    assert ok and "in front of the active app's 0.00 s" in said, said


@pytest.mark.parametrize(
    'seen, off',
    [
        (((OTHER, ((NORMAL, 1.0, OTHER, WHOLE),)), (OTHER, ((NORMAL, 1.0, OTHER, WHOLE),))), True),
        (
            ((OTHER, ((NORMAL, 1.0, OTHER, WHOLE),)), (OTHER, ((NORMAL, 0.4, PID, LEFT), (NORMAL, 1.0, OTHER, WHOLE)))),
            False,
        ),
        (((OTHER, ((NORMAL, 1.0, OTHER, WHOLE),)), (PID, ((NORMAL, 1.0, OTHER, WHOLE),))), False),
        (((OTHER, ()), (OTHER, ())), False),
        (((OTHER, ((NORMAL, 1.0, OTHER, WHOLE),)),), False),
        (((None, ((NORMAL, 1.0, OTHER, WHOLE),)), (None, ((NORMAL, 1.0, OTHER, WHOLE),))), False),
    ],
    ids=[
        'none of its windows',
        'one of its windows on screen',
        'the active app',
        'a watch listing nothing',
        'one sample',
        'the active app never read',  # REVIEW.md TST-441: lsappinfo failing at every sample
    ],
)
def test_a_designer_started_hidden_shows_no_window_and_never_becomes_the_active_app(
    window_server: ModuleType, seen: tuple[Seen, ...], off: bool
) -> None:
    # REVIEW.md SRV-152: a launch now starts Designer hidden; a watch listing no window at all can't tell
    assert window_server.stayed_off_screen(samples(window_server, *seen), PID)[0] is off


@pytest.mark.parametrize(
    'active, windows, shows',
    [
        (PID, ((NORMAL, 1.0, PID, WHOLE),), True),
        (PID, ((NORMAL, 1.0, OTHER, WHOLE),), False),
        (None, ((NORMAL, 1.0, PID, WHOLE),), None),  # no active app read
        (PID, (), None),  # no window read: a reader that failed, as a desktop always has its menu bar's
    ],
    ids=['its window listed', "only another app's", 'no active app read', 'no window read'],
)
def test_whether_the_active_app_shows_a_window_is_unknown_when_either_reading_is_missing(
    window_server: ModuleType,
    active: int | None,
    windows: tuple[tuple[int, float, int, tuple[float, ...]], ...],
    shows: bool | None,
) -> None:
    # REVIEW.md TST-445: the HLP-160 check skipped when either reading was missing, so a broken reader made it a skip in
    # every run
    assert window_server.active_shows_a_window(active, windows) is shows
