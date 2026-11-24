"""The self-test's reading of macOS's window server: the windows on screen and the front watch launch_designer's
check uses (window_server.py; REVIEW.md SRV-149)."""

import asyncio
import ctypes
import itertools
import os
import sys
import threading
import time
from collections.abc import Callable, Iterator
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from selftest_fakes import fresh, tool_result
from test_selftest_popups import NORMAL, PID, POPUP, Server

from project_constants import ToolArgs

if TYPE_CHECKING:  # for the checker only: each test imports window_server.py afresh (fresh())
    from test_all_tools.window_server import Rect, Sample, Window

OTHER = PID + 1  # another app's process
WHOLE, LEFT, RIGHT = (0.0, 0.0, 1000.0, 800.0), (0.0, 0.0, 400.0, 800.0), (500.0, 0.0, 400.0, 800.0)  # x, y, w, h


class Bounded(Server):
    """The fake window server of test_selftest_popups, each window's bounds too: (layer, alpha, pid, rect), read by
    the keys 0 to 3."""

    def CGRectMakeWithDictionaryRepresentation(self, rect: 'Rect', out: ctypes.Array[ctypes.c_double]) -> bool:
        for i, value in enumerate(rect):
            out[i] = value  # the four doubles' array on_screen passes
        return True


@pytest.fixture
def window_server() -> ModuleType:
    return fresh('window_server')


Seen = tuple[int | None, tuple['Window', ...]]


def samples(window_server: ModuleType, *seen: Seen) -> list['Sample']:
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
    window_server: ModuleType, windows: tuple['Window', ...], covers: bool
) -> None:
    # alone on screen (another desktop, a full-screen app's space), Designer's window is in front of nothing of the
    # user's: a watch taking the frontmost window for one in front failed a run with nothing in front (2026-11-15)
    assert (window_server.covering(windows, PID) is not None) is covers


# what `lsappinfo info -only pid <front>` printed on macOS 27.2.1 (26B131), its trailing spaces included (REVIEW.md
# TST-836)
LSAPPINFO_27 = (
    '[ NULL ]  [ NULL ]  \n'
    '    bundleID=[ NULL ] \n'
    '    bundle path=[ NULL ] \n'
    '    executable path=[ NULL ] \n'
    '    pid = 2510 !cgsConnection !signalled type=[ NULL ]  flavor=[ NULL ]  Version=[ NULL ]  Arch=!!none \n'
    '\n'
)


@pytest.mark.parametrize(
    'info, pid',
    [('"pid"=1920\n', 1920), (LSAPPINFO_27, 2510), ('', None)],
    ids=['macOS 26', 'macOS 27.2.1', 'nothing printed'],
)
def test_the_active_apps_process_is_read_from_lsappinfo(window_server: ModuleType, info: str, pid: int | None) -> None:
    assert window_server.pid_of(info) == pid


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
def test_the_front_watch_samples_the_active_app_and_the_windows_on_screen(
    window_server: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md TST-426: it slept 0.3 s, a time. REVIEW.md TST-513: it then polled the samples; the real read, wrapped,
    # says when they are there
    real: Callable[[object, object, object], tuple[Window, ...]] = window_server.on_screen
    reads = itertools.count(1)
    second_kept = threading.Event()  # the third read comes once the second sample is kept

    def read(cg: object, cf: object, keys: object) -> tuple['Window', ...]:
        if next(reads) == 3:
            second_kept.set()
        return real(cg, cf, keys)

    monkeypatch.setitem(vars(window_server), 'on_screen', read)
    with window_server.FrontWatch() as watch:
        assert second_kept.wait(30), 'the watch kept %d samples in 30 s' % len(watch.samples)
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
    window_server: ModuleType, windows: tuple['Window', ...], shows: bool
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
    assert window_server.covering(windows, PID) is not None
    assert window_server.covering(windows, PID, over=OTHER) is None
    assert window_server.covering(windows, PID, over=third) is not None


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
    windows: tuple['Window', ...],
    shows: bool | None,
) -> None:
    # REVIEW.md TST-445: the HLP-160 check skipped when either reading was missing, so a broken reader made it a skip in
    # every run
    assert window_server.active_shows_a_window(active, windows) is shows


# The front watch's stretches in front, said in full: two final runs failed on a Designer window 0.07 s in front of
# another app's, and the check said only that total (2026-11-17)
BEHIND = (OTHER, ((NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, LEFT)))
OVER = (OTHER, ((NORMAL, 1.0, PID, LEFT), (NORMAL, 1.0, OTHER, WHOLE)))
OVER_RIGHT = (OTHER, ((NORMAL, 0.5, PID, RIGHT), (NORMAL, 1.0, OTHER, WHOLE)))


def test_the_stretches_in_front_name_the_window_and_the_one_it_covered(window_server: ModuleType) -> None:
    # a stretch keeps its first sample's windows (REVIEW.md TST-505); the last sample counts for nothing
    seen = samples(window_server, BEHIND, OVER, OVER_RIGHT, BEHIND, OVER_RIGHT, BEHIND, OVER)
    assert window_server.fronts(seen, PID) == [
        window_server.Front(1.0, 2.0, (NORMAL, 1.0, PID, LEFT), (NORMAL, 1.0, OTHER, WHOLE)),
        window_server.Front(4.0, 1.0, (NORMAL, 0.5, PID, RIGHT), (NORMAL, 1.0, OTHER, WHOLE)),
    ]
    assert "in front of another app's 3.00 s" in window_server.stayed_behind(seen, PID)[1], 'the stretches add up'


@pytest.mark.parametrize(
    'marks, around',
    [
        ([(0.5, 'a: one'), (1.0, 'a: two'), (2.5, 'b: three')], 'after check "a: two" and before check "b: three"'),
        ([(2.5, 'b: three')], 'before check "b: three"'),
        ([(0.5, 'a: one')], 'after check "a: one"'),
        ([], 'with no check recorded'),
    ],
    ids=['between two', 'before the first', 'after the last', 'none'],
)
def test_a_stretch_in_front_is_said_with_both_windows_and_the_checks_around_it(
    window_server: ModuleType, monkeypatch: pytest.MonkeyPatch, marks: list[tuple[float, str]], around: str
) -> None:
    monkeypatch.setitem(vars(window_server), 'process_name', lambda pid: pytest.fail('named again: %d' % pid))
    front = window_server.Front(1.0, 0.07, (NORMAL, 0.5, PID, LEFT), (NORMAL, 1.0, OTHER, WHOLE))
    assert window_server.said(front, 0.25, marks, {OTHER: 'Terminal'}) == (
        'at 0.75 s, for 0.07 s: its window at (0, 0) 400 x 800, opacity 0.50, over the window of process %d (Terminal) '
        'at (0, 0) 1000 x 800, %s' % (OTHER, around)
    )


def test_at_most_ten_stretches_in_front_are_said_and_the_others_counted(
    window_server: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(vars(window_server), 'process_name', lambda pid: 'Terminal')  # the watch didn't name it
    seen = samples(window_server, *([OVER, BEHIND] * 12))
    said = window_server.fronts_said(seen, PID, [], {})
    assert len(said) == 11 and said[0].startswith('at 0.00 s, for 1.00 s:') and said[-1] == 'and 2 more', said
    assert '(Terminal)' in said[0], said[0]


def test_each_check_and_skip_is_recorded_with_its_time() -> None:
    common = fresh('common')
    before = time.monotonic()
    common.check('tool', 'a check', True)
    common.skip('tool', 'a skip', 'why')
    after = time.monotonic()
    assert [label for _, label in common.checked] == ['tool: a check', 'tool: a skip']
    assert all(before <= at <= after for at, _ in common.checked)


def test_the_stayed_behind_check_prints_each_stretch_in_front_whole(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # a check's detail is cut at 150 characters (common.check): the lines come after it, each whole
    editor = fresh('editor_panels_and_fit.checks')
    common = sys.modules['test_all_tools.common']
    monkeypatch.setattr(sys, 'platform', 'darwin')
    common.checked.extend([(0.5, 'a: one'), (1.5, 'b: two')])

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        return tool_result(str(PID))

    watch = editor.window_server.FrontWatch(watching=False)
    watch.samples[:] = samples(editor.window_server, BEHIND, OVER, BEHIND)
    watch.names[OTHER] = 'Terminal'
    asyncio.run(editor.check_designer_stayed_behind(SimpleNamespace(c=c, was_running=False), watch))
    out = capsys.readouterr().out
    assert common.results['self-test'] == [False]
    assert (
        '\n      in front at 1.00 s, for 1.00 s: its window at (0, 0) 400 x 800, opacity 1.00, over the window of process '
        '%d (Terminal) at (0, 0) 1000 x 800, after check "a: one" and before check "b: two"\n' % OTHER in out
    ), out


@pytest.mark.skipif(sys.platform == 'win32', reason="ps is macOS's, as the window server's list is")
def test_a_process_is_named_as_ps_gives_it_and_gone_once_it_ended(window_server: ModuleType) -> None:
    assert 'python' in window_server.process_name(os.getpid()).lower()
    assert window_server.process_name(2**22 + 1) == 'gone'  # an ID no process has: macOS's stay below 100000


def _fake_watch(
    window_server: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    windows: Callable[[object, object, object], tuple['Window', ...]],
    active: Callable[[], int | None],
) -> None:
    """A front watch's readings faked: `windows(cg, cf, keys)` for the windows on screen, `active()` for the active app,
    and CoreFoundation's string keys."""
    library = SimpleNamespace(CFStringCreateWithCString=lambda *args: 1, CFRelease=lambda key: None)
    monkeypatch.setitem(vars(window_server), 'libraries', lambda: (library, library))
    monkeypatch.setitem(vars(window_server), 'on_screen', windows)
    monkeypatch.setitem(vars(window_server), 'active_app', active)


def test_the_front_watch_names_each_app_once_as_one_of_its_windows_first_shows(
    window_server: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # the check reports once the watch is over, minutes later: by then another Designer of the pool may have quit, and
    # ps would no longer name it
    named: list[int] = []
    third_kept = threading.Event()  # the fourth read comes once the third sample is kept (REVIEW.md TST-506)

    def name(pid: int) -> str:
        named.append(pid)
        return 'app %d' % pid

    def lists() -> Iterator[tuple['Window', ...]]:
        shown = ((NORMAL, 1.0, OTHER, WHOLE), (NORMAL, 1.0, PID, LEFT))
        # a popup's process and one whose window is transparent, neither ever showing a normal window (TST-514)
        yield (NORMAL, 1.0, OTHER, WHOLE), (POPUP, 1.0, PID + 3, LEFT), (NORMAL, 0.0, PID + 2, WHOLE)
        yield shown
        yield shown
        third_kept.set()
        yield from itertools.repeat(shown)

    reads = lists()
    _fake_watch(window_server, monkeypatch, lambda cg, cf, keys: next(reads), lambda: OTHER)
    monkeypatch.setitem(vars(window_server), 'process_name', name)
    with window_server.FrontWatch() as watch:
        assert third_kept.wait(30), 'the watch kept %d samples in 30 s' % len(watch.samples)
    # a popup or a transparent window covers nothing: an app is named only as a normal window of its shows
    assert named == [OTHER, PID] and watch.names == {OTHER: 'app %d' % OTHER, PID: 'app %d' % PID}


def test_a_samples_time_is_taken_once_its_windows_are_read(
    window_server: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md TST-503: the time came before the two lsappinfo runs (10 ms here) and the windows' read, so a check
    # recorded meanwhile placed a stretch one check early
    order: list[str] = []
    read = threading.Event()

    def windows(cg: object, cf: object, keys: object) -> tuple['Window', ...]:
        order.append('windows')
        read.set()
        return ()

    def now() -> float:
        order.append('time')
        return 0.0

    def active() -> None:
        order.append('active app')

    _fake_watch(window_server, monkeypatch, windows, active)
    monkeypatch.setitem(vars(window_server), 'time', SimpleNamespace(monotonic=now))
    with window_server.FrontWatch():
        assert read.wait(30), 'the watch never read the windows in 30 s'
    assert order[:3] == ['active app', 'windows', 'time'], order
