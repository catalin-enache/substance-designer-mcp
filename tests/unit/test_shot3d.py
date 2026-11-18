"""The helpers' side of screenshot_designer('3d') (designer_helpers/shot3d.py), with sd and PySide6 faked: Designer's
window put on screen for the shot, transparent and click-through, again before each render, and put back after, opaque
(REVIEW.md SRV-146, HLP-124 to HLP-126; DECISIONS.md), and a render identical to the one before a set-up that moved
the camera or switched the mesh taken again, then said. The live self-test checks Designer itself
(editor_panels_and_fit)."""

import contextlib
import sys
import types
from collections.abc import Callable, Iterator, Sequence
from types import FrameType, SimpleNamespace
from typing import TYPE_CHECKING, NoReturn

import pytest
from aborts import Tracer
from appkit_fakes import Notices

from conftest import View3dOptions

if TYPE_CHECKING:  # for the checker only: the types the faked helpers take; PySide6 is faked at run time
    from PySide6 import QtCore, QtWidgets

    from designer_helpers.shot3d import _Screen

MAIN = 1  # Designer's main window
OTHERS = (2, 3)  # its other windows: a floating panel, a dialog
OPAQUE = (1.0, False)  # opacity, and whether the mouse goes through it to the window under it


class Abort(BaseException):
    """The plugin's abort (ScriptAborted), raised where a cancel lands."""


class Mac:
    """_MacWindow, faked: how macOS sees Designer's window, the window in front of it while it is covered, the windows
    no longer on screen, whether Designer is the active app, each window's opacity and whether clicks go through it,
    and what was done to the windows, in order. `abort_on` names a step an abort lands on, once, before it is done.
    `slow` is how many times the main window is still seen on screen once minimized or hidden."""

    def __init__(
        self,
        minimized: bool = False,
        hidden: bool = False,
        covered: bool = False,
        above: int | None = 7,
        active: bool = False,
    ) -> None:
        self.state = {'minimized': minimized, 'hidden': hidden, 'covered': covered}
        self.window_above = above
        self.further: list[int] = []  # windows in front of it too while it is covered, front to back, further from it
        self.order = [9, 7]  # the other windows on screen, front to back: one come in front of its first cover
        self.gone: set[int] = set()  # closed or minimized: not on screen
        self.is_active = active
        self.looks: dict[int, tuple[float, bool]] = {}
        self.abort_on: str | None = None
        self.slow = 0
        self.held: dict[int, int] = {}  # holds not let go of, by window: one let go of twice would be freed
        self.done: list[str] = []
        self.notified: list[Notices] = []  # the notices made, each the waits on AppKit's notifications observe

    def notices(self, names: Sequence[str]) -> Notices:
        self.notified.append(Notices(names))
        return self.notified[-1]

    def landed(self) -> bool:
        return self.abort_on is None

    def _do(self, step: str) -> None:
        if self.abort_on is not None and step.startswith(self.abort_on):
            self.abort_on = None
            raise Abort
        self.done.append(step)

    def minimized(self) -> bool:
        return self.state['minimized']

    def hidden(self) -> bool:
        return self.state['hidden']

    def covered(self) -> bool:  # no part on screen: minimized or hidden too, as macOS says (REVIEW.md TST-397)
        return any(self.state.values())

    def active(self) -> bool:
        return self.is_active

    def in_front(self) -> list[int]:  # the windows in front of it while it is covered, front to back
        return [*self.further, self.window_above] if self.covered() and self.window_above is not None else []

    def lowest(self, numbers: list[int]) -> int | None:  # of `numbers`, the window on screen nearest the back
        found = [n for n in self.order if n in numbers and self.on_screen(n)]
        return found[-1] if found else None

    def number(self) -> int:
        return MAIN

    def on_screen(self, number: int) -> bool:  # a covered window is on screen; a minimized or hidden one isn't
        if number != MAIN:
            return number not in self.gone
        if self.slow and (self.state['minimized'] or self.state['hidden']):
            self.slow -= 1
            return True
        return not (self.state['minimized'] or self.state['hidden'])

    def windows(self, every: bool) -> list[int]:
        return [MAIN, *OTHERS] if every else [MAIN]

    def hold(self, window: int) -> None:
        self.held[window] = self.held.get(window, 0) + 1

    def let_go(self, window: int) -> None:
        assert self.held.get(window, 0) > 0, 'let go of window %d, not held' % window
        self.held[window] -= 1

    def appearance(self, window: int) -> tuple[float, bool]:
        return self.looks.get(window, OPAQUE)

    def set_appearance(self, window: int, opacity: float, through: bool) -> None:
        name = {(0.0, True): 'fade', OPAQUE: 'unfade'}.get((opacity, through), 'look %g %s' % (opacity, through))
        self._do(name if window == MAIN else '%s %d' % (name, window))
        self.looks[window] = (opacity, through)

    def show(self) -> None:  # in front, without taking focus: un-minimized and uncovered too
        self._do('show')
        self.state.update(minimized=False, covered=False)

    def unhide(self) -> None:
        self._do('unhide')
        self.state['hidden'] = False

    def hide(self) -> None:
        self._do('hide')
        self.state['hidden'] = True

    def minimize(self) -> None:
        self._do('minimize')
        self.state['minimized'] = True

    def put_below(self, number: int) -> None:
        self._do('put below %d' % number)
        self.state['covered'] = True


class Window:
    """Designer's main window as Qt sees it: minimized only when Qt itself minimized it, exposed while macOS shows it
    (never, with `shows` False), once it was put in front `shows_after` times."""

    def __init__(self, mac: Mac, qt_minimized: bool = False, shows: bool = True, shows_after: int = 0) -> None:
        self.mac = mac
        self.qt_minimized = qt_minimized
        self.shows = shows
        self.shows_after = shows_after

    def isMinimized(self) -> bool:
        return self.qt_minimized

    def windowState(self) -> int:
        return 1

    def setWindowState(self, state: 'QtCore.Qt.WindowState') -> None:
        self.mac.done.append('qt restore')
        self.qt_minimized = False

    def windowHandle(self) -> SimpleNamespace:
        def exposed() -> bool:
            shown = self.mac.done.count('show') >= self.shows_after
            return self.shows and shown and not any(self.mac.state.values())

        return SimpleNamespace(isExposed=exposed, removeEventFilter=lambda spy: None)


class Frames:
    """_Frames, faked: the waits asked of it, in `waits`, and in `log` too when given (a Mac's done). `drawing`: whether
    the view draws a next frame."""

    def __init__(self, log: list[str] | None = None, drawing: bool = True) -> None:
        self.waits: list[str] = []
        self.log = log
        self.drawing = drawing
        self.closed = False

    def _did(self, what: str) -> None:
        self.waits.append(what)
        if self.log is not None:
            self.log.append(what)

    def mark(self) -> int:
        self._did('mark')
        return len(self.waits)

    def shown(self, since: int) -> None:
        self._did('shown since %d' % since)

    def next_frame(self) -> bool:
        self._did('next frame')
        return self.drawing

    def off_screen(self) -> bool:  # read once the window was put on screen: still there
        return False

    def close(self) -> None:
        self._did('closed')


def on_screen(
    helpers: types.ModuleType, window: Window, frames: Frames | None = None
) -> contextlib.AbstractContextManager['_Screen']:
    """_on_screen for `window`, watching `frames` (a fake of its own when not given)."""
    made: contextlib.AbstractContextManager[_Screen] = helpers._on_screen(
        window, frames if frames is not None else Frames()
    )
    return made


@pytest.fixture
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    module = faked_helpers
    vars(module)['_settle'] = lambda seconds: None
    vars(module)['_event_signal'] = lambda watched, kinds, seen=None: SimpleNamespace(fired='its signal')
    vars(module)['_until'] = lambda state, limit, signals=(): state()  # a wait looking once: the state now
    return module


def waits_recorded(helpers: types.ModuleType, done: list[str]) -> None:
    """_until looking up to 10 times, each wait recorded in `done` with its limit."""

    def until(state: Callable[[], bool], limit: float, signals: Sequence[str] = ()) -> bool:
        done.append('wait %g' % limit)
        return any(state() for _ in range(10))

    vars(helpers)['_until'] = until


def _on(helpers: types.ModuleType, mac: Mac | None) -> None:
    vars(helpers)['_mac_window'] = lambda mw: mac


FRONT = (
    "Designer's window: brought in front, transparent and without taking focus, as its 3D view may not be drawn "
    'while covered'  # REVIEW.md TST-433: in some Designers launch_designer opened, a covered window's view drew
)
PUT_BACK = "Designer's window: put back behind the window that was in front of it"
SHOWN = (
    "Designer's window: shown, transparent and without taking focus, as its 3D view isn't drawn while Designer is "
    'hidden'
)
HIDDEN = "Designer's window: hidden again"
UNMINIMIZED = (
    "Designer's window: shown, transparent and without taking focus, as its 3D view isn't drawn while minimized"
)
MINIMIZED = "Designer's window: minimized again"
QT_UNMINIMIZED = "Designer's window: un-minimized, as its 3D view isn't drawn while minimized; it stays so"
LEFT = "Designer's window: left on screen, as Designer became the active app during the shot"
GONE = "Designer's window: left in front, as the window that was in front of it is no longer on screen"
NONE_IN_FRONT = "Designer's window: left in front, as no window was found in front of it"
OPAQUE_AGAIN = "Designer's window: made opaque again, as an earlier shot left it transparent"
EVERY_FADED = ['fade', 'fade 2', 'fade 3']  # a hidden Designer shows all its windows: each made transparent first
EVERY_BACK = ['unfade', 'unfade 2', 'unfade 3']


def test_a_window_on_screen_is_left_as_it_is(helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    mac = Mac()
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['shot'] and capsys.readouterr().out == ''


def test_a_minimized_window_is_shown_transparent_without_focus_and_minimized_again(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # the user's choice (DECISIONS.md): the user sees nothing of it; Qt doesn't see macOS minimize it, so macOS is asked
    mac = Mac(minimized=True)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['fade', 'show', 'shot', 'minimize', 'unfade']
    assert capsys.readouterr().out.splitlines() == [UNMINIMIZED, MINIMIZED]
    assert mac.minimized() and mac.appearance(MAIN) == OPAQUE


def test_a_window_qt_minimized_is_restored_by_qt_brought_in_front_and_left_so(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # Designer's renderer follows the Qt state of getMainWindow(), a page: stale though macOS shows it (REVIEW.md
    # TST-391). Restored by Qt alone, a plain shot's render was the view's last frame; brought in front too, it drew
    mac = Mac()
    _on(helpers, mac)
    with on_screen(helpers, Window(mac, qt_minimized=True)):
        mac.done.append('shot')
    assert mac.done == ['qt restore', 'show', 'shot']
    assert capsys.readouterr().out.splitlines() == [QT_UNMINIMIZED]


def test_a_covered_window_is_brought_in_front_transparent_and_put_back_behind_the_window_in_front_of_it(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-126: right behind the window that was in front of it, not behind every window; opaque once there
    mac = Mac(covered=True, above=7)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['fade', 'show', 'shot', 'put below 7', 'unfade']
    assert capsys.readouterr().out.splitlines() == [FRONT, PUT_BACK]


def test_a_covered_window_with_no_window_found_in_front_is_left_in_front(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-130: no normal window in front of it (an always-on-top window covered it): sending it to the back
    # would put the front-most normal window behind every window
    mac = Mac(covered=True, above=None)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['fade', 'show', 'shot', 'unfade']
    assert capsys.readouterr().out.splitlines() == [FRONT, NONE_IN_FRONT]


def test_a_covered_window_whose_window_in_front_went_off_screen_is_left_in_front(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-130: the user closed or minimized it during the shot; put behind it, Designer's window would go
    # behind every window (measured: mac_window.py)
    mac = Mac(covered=True, above=7)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
        mac.gone.add(7)
    assert mac.done == ['fade', 'show', 'shot', 'unfade']
    assert capsys.readouterr().out.splitlines() == [FRONT, GONE]


def test_a_covered_window_goes_back_behind_its_cover_once_the_user_raised_the_window_in_front_of_it(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-139: window 5 covered it, and 7 was in front of it, under 5. The user's click on 7, through
    # Designer's transparent window, brought 7 in front: put right behind 7 alone, Designer's window would show over 5
    mac = Mac(covered=True, above=7)
    mac.further, mac.order = [5], [5, 7]
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
        mac.order = [7, 5]
    assert mac.done == ['fade', 'show', 'shot', 'put below 5', 'unfade']
    assert capsys.readouterr().out.splitlines() == [FRONT, PUT_BACK]


def test_a_covered_window_goes_back_behind_its_cover_once_the_window_in_front_of_it_closed(
    helpers: types.ModuleType,
) -> None:
    # REVIEW.md HLP-139: the user closed 7, its close button reached through Designer's window; 5 still covers it
    mac = Mac(covered=True, above=7)
    mac.further, mac.order = [5], [5, 7]
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
        mac.gone.add(7)
    assert mac.done == ['fade', 'show', 'shot', 'put below 5', 'unfade']


def test_an_abort_while_the_window_in_front_is_looked_for_leaves_nothing_to_put_back(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-130: the window wasn't moved yet, so nothing is put back and nothing said of it
    mac = Mac(covered=True)

    def aborted() -> list[int]:
        raise Abort

    vars(mac)['in_front'] = aborted
    _on(helpers, mac)
    with pytest.raises(Abort), on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert mac.done == []
    assert capsys.readouterr().out.splitlines() == [FRONT]


@pytest.mark.parametrize(
    'way, step',
    [
        *[('covered', step) for step in ('fade', 'show', 'put below', 'unfade')],
        *[('minimized', step) for step in ('fade', 'show', 'minimize', 'unfade')],
        *[('hidden', step) for step in ('fade', 'unhide', 'show', 'hide', 'unfade')],
    ],
)
def test_an_abort_anywhere_in_the_shot_leaves_every_window_opaque_and_clickable(
    helpers: types.ModuleType, way: str, step: str
) -> None:
    # a transparent window left behind would look to the user as if Designer were gone: whatever step the abort lands
    # on, the handler that runs after it (untraced: the plugin's _make_tracer) gives every window its look back
    mac = Mac(**{way: True})
    mac.abort_on = step
    _on(helpers, mac)
    with pytest.raises(Abort), on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert mac.landed(), 'no abort landed on ' + step
    assert all(mac.appearance(window) == OPAQUE for window in (MAIN, *OTHERS)), mac.done
    assert not any(mac.held.values()), 'held: %s' % mac.held  # each hold let go of, once


@pytest.mark.parametrize('way', ['minimized', 'covered', 'hidden'])
def test_an_abort_at_any_event_of_the_shot_leaves_the_window_where_it_was_found_and_opaque_once_there(
    helpers: types.ModuleType, way: str
) -> None:
    # REVIEW.md HLP-180: the plugin raises its abort at a traced event, then stops tracing. Landed in put_back before its
    # step, it skipped the step, and the handler only gave the windows their look back: the window stayed on the user's
    # screen, opaque. Landed in the wait for it off screen, the look came back while it was still on screen. Each step
    # of the fake Mac stands for one AppKit call, untraced like Qt's window: an abort lands before it or after it
    from aborts import at_each_event

    mac = Mac(**{way: True})
    _on(helpers, mac)
    window = Window(mac)
    off = {'minimized': 'minimize', 'covered': 'put below', 'hidden': 'hide'}[way]

    def run() -> None:
        with on_screen(helpers, window):
            mac.done.append('shot')

    def fresh() -> None:
        vars(mac).update(vars(Mac(**{way: True})))

    for where in at_each_event(run, ('designer_helpers', __file__), fresh, untraced=(Mac, Window)):
        assert mac.state[way], '%s: %s' % (where, mac.done)
        # an observer of AppKit's notifications left, its callback freed, would crash Designer (ROADMAP item 101)
        assert all(n.closed or not n.opened for n in mac.notified), '%s: %s' % (where, mac.done)
        assert all(mac.appearance(w) == OPAQUE for w in (MAIN, *OTHERS)), '%s: %s' % (where, mac.done)
        if 'show' in mac.done:  # shown: its look given back only once it was put back; a step done again after is
            # harmless (the handler runs put_back again)
            since = mac.done[len(mac.done) - 1 - mac.done[::-1].index('show') :]
            first_look = since.index('unfade') if 'unfade' in since else len(since)
            assert any(step.startswith(off) for step in since[:first_look]), '%s: %s' % (where, mac.done)
        assert sum(mac.held.values()) <= 1, (
            '%s: at most one hold left, as an abort between it and its record leaks it' % where
        )


def test_the_windows_are_made_transparent_each_once(helpers: types.ModuleType) -> None:
    # a window shown again during the shot is transparent already: its look before stays the one recorded first
    mac = Mac(hidden=True)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)) as screen:
        mac.state['hidden'] = True
        screen.again()
    assert mac.done == [*EVERY_FADED, 'unhide', 'show', 'unhide', 'show', 'hide', *EVERY_BACK]


@pytest.mark.parametrize(
    'way, back',
    [
        ('minimized', ['shot', 'minimize', 'wait 3', 'unfade']),
        ('hidden', ['shot', 'hide', 'wait 3', *EVERY_BACK]),  # REVIEW.md TST-402
    ],
)
def test_a_window_put_back_off_screen_is_made_opaque_only_once_off_screen(
    helpers: types.ModuleType, way: str, back: list[str]
) -> None:
    # opaque while still on screen, as macOS minimizes or hides it, the user would see it: the wait looks until the
    # window server no longer lists it (slow: twice more)
    mac = Mac(**{way: True})
    mac.slow = 2
    _on(helpers, mac)
    waits_recorded(helpers, mac.done)
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert mac.done[-len(back) :] == back and mac.slow == 0


@pytest.mark.parametrize(
    'off, done, said',
    [
        ('', ['unfade', 'shot'], []),
        ('minimized', ['unfade', 'fade', 'show', 'shot', 'minimize', 'unfade'], [UNMINIMIZED, MINIMIZED]),
        ('covered', ['unfade', 'fade', 'show', 'shot', 'put below 7', 'unfade'], [FRONT, PUT_BACK]),
        ('hidden', ['unfade', *EVERY_FADED, 'unhide', 'show', 'shot', 'hide', *EVERY_BACK], [SHOWN, HIDDEN]),
    ],
    ids=['on screen', 'minimized', 'covered', 'hidden'],
)
def test_a_window_an_earlier_shot_left_transparent_is_made_opaque_first(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], off: str, done: list[str], said: list[str]
) -> None:
    # REVIEW.md TST-407: made opaque before it is brought on screen, so the look recorded for after the shot is opaque
    mac = Mac(**({off: True} if off else {}))
    mac.looks[MAIN] = (0.0, True)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert mac.done == done and mac.appearance(MAIN) == OPAQUE
    assert capsys.readouterr().out.splitlines() == [OPAQUE_AGAIN, *said]


def test_an_abort_while_a_window_left_transparent_is_made_opaque_still_leaves_it_opaque_and_clickable(
    helpers: types.ModuleType,
) -> None:
    # REVIEW.md HLP-135: opaque_first's change is recorded nowhere, so only the handler doing it again finishes it
    mac = Mac()
    mac.looks[MAIN] = (0.0, True)
    mac.abort_on = 'unfade'
    _on(helpers, mac)
    with pytest.raises(Abort), on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert mac.landed() and mac.appearance(MAIN) == OPAQUE, mac.done


def test_a_window_covered_again_during_the_shot_goes_back_behind_the_window_that_covered_it_first(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-131: the user's click on another window during the shot leaves that one in front, and Designer's
    # behind the window that covered it before
    mac = Mac(covered=True, above=7)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)) as screen:
        mac.state['covered'], mac.window_above = True, 9
        screen.again()
    assert mac.done == ['fade', 'show', 'show', 'put below 7', 'unfade']
    assert capsys.readouterr().out.splitlines()[-1] == PUT_BACK


def test_a_window_covered_again_after_its_first_cover_went_off_screen_goes_back_behind_the_later_one(
    helpers: types.ModuleType,
) -> None:
    mac = Mac(covered=True, above=7)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)) as screen:
        mac.gone.add(7)
        mac.state['covered'], mac.window_above = True, 9
        screen.again()
    assert mac.done == ['fade', 'show', 'show', 'put below 9', 'unfade']


def test_a_hidden_designer_is_shown_transparent_without_focus_and_hidden_again_after(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    mac = Mac(hidden=True)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert mac.done == [*EVERY_FADED, 'unhide', 'show', 'shot', 'hide', *EVERY_BACK]
    assert capsys.readouterr().out.splitlines() == [SHOWN, HIDDEN]
    assert set(mac.held) == {MAIN, *OTHERS} and not any(mac.held.values())  # each window held while transparent


class LateUnhide(Mac):
    """A hidden Designer whose unhide takes as its events run (`events_run`), `runs` times after the call, as macOS
    does: brought in front before that, the window goes back behind the active app's window as it takes (REVIEW.md
    HLP-160)."""

    def __init__(self, runs: int) -> None:
        super().__init__(hidden=True)
        self.runs = runs
        self.pending: int | None = None  # the runs of the events left before the unhide takes, once asked
        self.early = False  # brought in front while the unhide hadn't taken

    def unhide(self) -> None:
        self._do('unhide')
        self.pending = self.runs

    def show(self) -> None:
        self.early = self.early or self.state['hidden']
        super().show()

    def events_run(self) -> None:
        if self.pending is None:
            return
        if self.pending > 0:
            self.pending -= 1
            return
        self.pending = None
        self.state.update(hidden=False, covered=self.early)


def test_a_hidden_designer_is_brought_in_front_once_macos_says_its_unhide_took(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-160: brought in front at once, the window went back behind the active app's window as the unhide
    # took, and the view drew nothing more, 5 of 5; brought in front once macOS no longer said Designer hidden, it
    # stayed in front, 5 of 5 (2026-11-16)
    mac = LateUnhide(runs=3)
    _on(helpers, mac)

    def until(state: Callable[[], bool], limit: float, signals: Sequence[str] = ()) -> bool:  # Designer's events run
        mac.done.append('wait %g' % limit)
        for _ in range(10):
            mac.events_run()
            if state():
                return True
        return False

    vars(helpers)['_until'] = until
    with on_screen(helpers, Window(mac)):
        assert not mac.covered(), 'in front at the shot'
        mac.done.append('shot')
    assert not mac.early, 'brought in front only once the unhide took'
    unhide = mac.done.index('unhide')
    assert mac.done[unhide + 1 : unhide + 3] == ['wait %g' % helpers.ON_SCREEN_WAIT, 'show']


OFF_SCREEN = ('NSWindowDidMiniaturizeNotification', 'NSWindowDidChangeOcclusionStateNotification')


@pytest.mark.parametrize(
    'way, notified',
    [
        ('minimized', [OFF_SCREEN]),
        ('hidden', [('NSApplicationDidUnhideNotification',), OFF_SCREEN]),
        ('covered', []),
    ],
)
def test_the_waits_on_macos_showing_or_putting_away_the_window_are_woken_by_appkits_notifications(
    helpers: types.ModuleType, way: str, notified: list[tuple[str, ...]]
) -> None:
    # ROADMAP item 101: no Qt callback says Designer unhidden, nor its window off screen once minimized or hidden
    # (REVIEW.md HLP-173). AppKit's notifications do, as measured (shot3d.py's module docstring). Designer hidden came
    # while the window server still listed the window: not observed
    mac = Mac(**{way: True})
    _on(helpers, mac)
    woken: list[list[str]] = []

    def until(state: Callable[[], bool], limit: float, signals: Sequence[str] = ()) -> bool:
        woken.append(list(signals))
        return bool(state())

    vars(helpers)['_until'] = until
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert [n.names for n in mac.notified] == notified
    assert all(n.opened == n.closed == 1 for n in mac.notified), 'each opened and closed once'
    assert all([n.fired] in woken for n in mac.notified)


def test_a_minimized_window_of_a_hidden_designer_is_minimized_and_designer_hidden_again(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-393: both at once
    mac = Mac(minimized=True, hidden=True)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert mac.done == [*EVERY_FADED, 'unhide', 'show', 'shot', 'minimize', 'hide', *EVERY_BACK]
    assert capsys.readouterr().out.splitlines() == [UNMINIMIZED, MINIMIZED, HIDDEN]


@pytest.mark.parametrize('way', ['minimized', 'covered', 'hidden', 'qt minimized'])
def test_the_view_is_waited_for_once_the_window_is_on_screen(helpers: types.ModuleType, way: str) -> None:
    # REVIEW.md TST-393: a render at once may still be the last frame; HLP-148: its paints since the window was shown
    # say when it drew what changed meanwhile, not a fixed time
    mac = Mac(**({} if way == 'qt minimized' else {way: True}))
    _on(helpers, mac)
    frames = Frames(log=mac.done)
    with on_screen(helpers, Window(mac, qt_minimized=way == 'qt minimized'), frames):
        mac.done.append('shot')
    shot = mac.done.index('shot')
    assert mac.done[0] == 'mark' and 'show' in mac.done[:shot] and mac.done[shot - 1] == 'shown since 1'


def test_a_window_on_screen_isnt_waited_for(helpers: types.ModuleType) -> None:
    mac = Mac()
    _on(helpers, mac)
    frames = Frames()
    with on_screen(helpers, Window(mac), frames):
        mac.done.append('shot')
    assert frames.waits == ['mark']


def test_a_window_still_not_on_screen_is_refused_and_put_back(helpers: types.ModuleType) -> None:
    mac = Mac(covered=True)
    _on(helpers, mac)
    refused = pytest.raises(RuntimeError, match=r"the 3D view isn't drawn: Designer's window isn't on screen")
    with refused, on_screen(helpers, Window(mac, shows=False)):
        mac.done.append('shot')
    assert mac.done == ['fade', 'show', 'show', 'put below 7', 'unfade']  # put in front again once (HLP-145)


@pytest.mark.parametrize('way', ['minimized', 'covered', 'hidden'])
def test_a_window_not_yet_on_screen_after_a_while_is_put_in_front_again_once(
    helpers: types.ModuleType, way: str
) -> None:
    # REVIEW.md HLP-145: a hidden Designer's window, transparent, shown again, stayed covered for macOS in 3 of 14 runs
    # in a Designer just started, until put in front again (measured 3 of 3); refused, the shot asked for the user.
    # HLP-173: it was put in front again after 0.5 s, a time measured here; since HLP-160's wait for the unhide, none of
    # 60 waits needed it, so it comes only once the wait's limit, a safety net, has passed
    mac = Mac(**{way: True})
    _on(helpers, mac)
    waits_recorded(helpers, mac.done)
    with on_screen(helpers, Window(mac, shows_after=2)):
        mac.done.append('shot')
    shown = [i for i, step in enumerate(mac.done[: mac.done.index('shot')]) if step == 'show']
    assert len(shown) == 2
    assert mac.done[shown[0] + 1 : shown[1]] == ['wait %g' % helpers.ON_SCREEN_WAIT]
    assert mac.done[shown[1] + 1] == 'wait %g' % helpers.ON_SCREEN_WAIT
    assert not hasattr(helpers, 'SHOW_AGAIN')


def test_a_shot_that_fails_still_puts_the_window_back(helpers: types.ModuleType) -> None:
    mac = Mac(hidden=True)
    _on(helpers, mac)
    with pytest.raises(RuntimeError, match='the render failed'), on_screen(helpers, Window(mac)):
        raise RuntimeError('the render failed')
    assert mac.done == [*EVERY_FADED, 'unhide', 'show', 'hide', *EVERY_BACK]


@pytest.mark.parametrize(
    'off, done, said',
    [
        (
            'covered',
            ['shot', 'fade', 'show', 'put below 9', 'unfade'],
            "Designer's window: brought in front again, transparent, as another window covered it during the shot",
        ),
        (
            'minimized',
            ['shot', 'fade', 'show', 'minimize', 'unfade'],
            "Designer's window: shown again, transparent, as it was minimized during the shot",
        ),
        (
            'hidden',
            ['shot', *EVERY_FADED, 'unhide', 'show', 'hide', *EVERY_BACK],
            "Designer's window: shown again, transparent, as Designer was hidden during the shot",
        ),
    ],
)
def test_a_window_put_off_screen_during_the_shot_is_put_on_screen_again(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], off: str, done: list[str], said: str
) -> None:
    # REVIEW.md HLP-124: the user clicked their own window back in front while the shot ran, or minimized or hid Designer
    mac = Mac(above=9)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)) as screen:
        mac.done.append('shot')
        mac.state[off] = True
        screen.again()
    assert mac.done == done
    assert capsys.readouterr().out.splitlines()[0] == said


def test_a_window_on_screen_is_left_as_it_is_when_looked_at_again(helpers: types.ModuleType) -> None:
    mac = Mac()
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)) as screen:
        screen.again()
    assert mac.done == []


@pytest.mark.parametrize(
    'off, done',
    [
        ('hidden', [*EVERY_FADED, 'unhide', 'show', *EVERY_BACK]),
        ('covered', ['fade', 'show', 'unfade']),
        ('minimized', ['fade', 'show', 'unfade']),  # REVIEW.md TST-402: not minimized again from under the user
    ],
)
def test_a_designer_the_user_made_the_active_app_during_the_shot_is_left_on_screen(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], off: str, done: list[str]
) -> None:
    # REVIEW.md HLP-125: the user switched to Designer: hiding it, or sending it back, takes it away; opaque again
    mac = Mac(**{off: True})
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)):
        mac.is_active = True
    assert mac.done == done
    assert capsys.readouterr().out.splitlines()[-1] == LEFT


OPAQUE_AT_ONCE = "Designer's window: made opaque at once, as Designer became the active app during the shot"


@pytest.mark.parametrize('off', ['minimized', 'covered', 'hidden'])
@pytest.mark.parametrize('look', ['between', 'again'], ids=['before a set-up step', 'before a render'])
def test_designer_made_the_active_app_during_the_shot_is_made_opaque_at_once_and_left_up(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], off: str, look: str
) -> None:
    # REVIEW.md HLP-136: left transparent, the user who switched to Designer would see no window, and a click would go
    # through it to the app under it, which would take Designer's place
    mac = Mac(**{off: True})
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)) as screen:
        mac.is_active = True
        getattr(screen, look)()
        seen = dict(mac.looks)
        mac.done.append('shot')
    assert set(seen.values()) == {OPAQUE} and not any(mac.held.values())
    assert mac.done[-1] == 'shot'  # left up: nothing done after the shot
    assert capsys.readouterr().out.splitlines()[-2:] == [OPAQUE_AT_ONCE, LEFT]


def test_a_window_put_on_screen_again_while_the_user_is_in_designer_isnt_made_transparent(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-136: the user, in Designer, minimized it meanwhile: shown again as it is, which they see
    mac = Mac(minimized=True)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)) as screen:
        mac.is_active = True
        screen.again()
        mac.state['minimized'] = True
        del mac.done[:]
        screen.again()
        assert mac.done == ['show'] and mac.appearance(MAIN) == OPAQUE
    assert capsys.readouterr().out.splitlines() == [  # REVIEW.md TST-409: made opaque once, said once
        UNMINIMIZED,
        OPAQUE_AT_ONCE,
        "Designer's window: shown again, as it was minimized during the shot",
        LEFT,
    ]


def test_nothing_is_said_when_designer_becomes_the_active_app_with_no_window_made_transparent(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-409: "made opaque at once" would tell an agent the user's window had been invisible
    mac = Mac()
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)) as screen:
        mac.is_active = True
        screen.again()
    assert mac.done == [] and capsys.readouterr().out == ''


def test_a_user_in_designer_as_the_shot_began_who_left_and_came_back_sees_its_window_at_once(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-138: Designer the active app as the shot began; the user went to an app whose window covers it,
    # then came back to Designer: transparent, they would see that app through it, their clicks going to it
    mac = Mac(covered=True, active=True)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)) as screen:
        mac.is_active = False
        screen.again()
        mac.state['covered'] = True
        screen.again()
        mac.is_active = True
        screen.between()
        seen = mac.appearance(MAIN)
    assert seen == OPAQUE and not any(step.startswith('put below') for step in mac.done)
    assert capsys.readouterr().out.splitlines()[-2:] == [OPAQUE_AT_ONCE, LEFT]


def test_designer_made_the_active_app_then_left_during_the_shot_is_put_back(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-136: made opaque at once, then the user went back to another app: put back as it was found
    mac = Mac(minimized=True)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)) as screen:
        mac.is_active = True
        screen.again()
        mac.is_active = False
    assert mac.done == ['fade', 'show', 'unfade', 'minimize'] and mac.minimized()
    assert capsys.readouterr().out.splitlines() == [UNMINIMIZED, OPAQUE_AT_ONCE, MINIMIZED]


def test_a_designer_already_the_active_app_before_the_shot_stays_transparent_during_it(
    helpers: types.ModuleType,
) -> None:
    # REVIEW.md HLP-136: the user didn't switch to it during the shot
    mac = Mac(covered=True, active=True)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)) as screen:
        screen.between()
        screen.again()
        assert mac.appearance(MAIN) == (0.0, True)


def test_a_window_covered_while_designer_was_already_the_active_app_is_put_back(helpers: types.ModuleType) -> None:
    # one of Designer's own windows over it, Designer in front: the user didn't take it up during the shot
    mac = Mac(covered=True, active=True)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['fade', 'show', 'shot', 'put below 7', 'unfade']


def test_off_macos_the_window_is_left_as_it_is(helpers: types.ModuleType) -> None:
    # not measured elsewhere: the shot is taken as before
    mac = Mac()
    _on(helpers, None)
    with on_screen(helpers, Window(mac, qt_minimized=True)) as screen:
        mac.done.append('shot')
        screen.again()
    assert mac.done == ['shot']


def test_designers_window_is_asked_of_macos_only_on_macos(
    helpers: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md TST-393: elsewhere the Objective-C runtime isn't there to ask
    monkeypatch.setattr(sys, 'platform', 'win32')
    assert helpers._mac_window(object()) is None


class Render:
    """A 3D render (a QImage): equal to another of the same name, as QImage compares pixels."""

    def __init__(self, name: str, saved: list[str]) -> None:
        self.name = name
        self._saved = saved

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Render) and other.name == self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def save(self, path: str) -> bool:
        self._saved.append('%s to %s' % (self.name, path))
        return True

    def width(self) -> int:
        return 4

    def height(self) -> int:
        return 3


class Shot:
    """shoot_3d's Designer, faked: the renders it gives in turn (the last one again once they run out), the mesh shown,
    and what happened, in order, the frames' waits included. The set-up's checks are the real argument checks
    (_set_up_checked); `refused` is raised by the rest of them. `drawing`: whether the view draws a next frame."""

    def __init__(
        self,
        helpers: types.ModuleType,
        *renders: str,
        mesh: str = 'Plane',
        refused: str | None = None,
        drawing: bool = True,
    ) -> None:
        self.events: list[str] = []
        self.frames = Frames(log=self.events, drawing=drawing)
        self.saved: list[str] = []
        renders_left = [Render(name, self.saved) for name in renders]
        checked = vars(helpers)['_set_up_checked']

        def render(mw: 'QtWidgets.QMainWindow') -> Render:
            r = renders_left.pop(0) if len(renders_left) > 1 else renders_left[0]
            self.events.append('render ' + r.name)
            return r

        self.screen = SimpleNamespace(again=lambda: self.events.append('again'), between=lambda: None)
        # what the set-up was given to run before each step, and the frames to wait on
        self.given: tuple[Callable[[], None] | None, Frames | None] | None = None

        @contextlib.contextmanager
        def on_screen(mw: 'QtWidgets.QMainWindow', frames: Frames) -> Iterator[SimpleNamespace]:
            assert frames is self.frames
            self.events.append('on screen')
            yield self.screen
            self.events.append('put back')

        def set_up(  # shoot_3d passes every argument, in order: graph, mesh, view, zoom, tiling, orbit, pan
            *args: *tuple[
                str | None, str | None, str | None, int, float | None, Sequence[float] | None, Sequence[float] | None
            ],
        ) -> Callable[[Callable[[], None] | None, Frames | None], None]:
            checked(*args[:3])
            if refused:
                raise RuntimeError(refused)

            def run(between: Callable[[], None] | None, frames: Frames | None) -> None:
                self.given = (between, frames)
                self.events.append('set up %r' % (args,))

            return run

        vars(helpers)['_3d_render'] = render
        vars(helpers)['_on_screen'] = on_screen
        vars(helpers)['_3d_dock'] = lambda mw: object()
        vars(helpers)['_viewport'] = lambda dock: 'the viewport'
        vars(helpers)['_Frames'] = lambda viewport, render: self.frames
        vars(helpers)['_mesh_shown'] = lambda mw, keep: mesh
        vars(helpers)['_3d_set_up'] = set_up
        vars(helpers)['find_graph'] = lambda name: SimpleNamespace(
            getIdentifier=lambda: name, getOutputNodes=lambda: [object()] * (1 if name == 'one' else 2)
        )


STALE = (
    '3D render: identical to the render before the set-up, though the set-up moved the camera or switched the mesh. '
    'The 3D view may not have been drawn. Shoot again with no set-up before judging it: pan, orbit and zoom move the '
    'camera from where it is. With no mesh in view, a pan or zoom changes nothing'
)


def test_the_set_up_is_given_the_screens_look_before_each_step(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-136: a set-up runs for seconds; the user switching to Designer meanwhile sees its window at once.
    # HLP-158 (the user's choice, 2026-11-16): a window gone off screen meanwhile is put back on screen before the next
    # step, as before a render, so a camera's turn is watched on screen
    shot = Shot(helpers, 'A', 'B')
    helpers.shoot_3d('out.png', pan=[0.25, 0.0])
    assert shot.given == (shot.screen.again, shot.frames)  # and the shot's watch of the view's frames


def test_a_render_identical_after_a_pan_is_taken_again_until_it_differs(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-148: each retake once the view drew another frame, not a fixed time after the last
    shot = Shot(helpers, 'A', 'A', 'A', 'B')
    helpers.shoot_3d('out.png', pan=[0.25, 0.0])
    assert shot.events == [
        'on screen',
        'again',
        'render A',  # before the set-up
        'set up (None, None, None, 0, None, None, [0.25, 0.0])',
        'again',
        'render A',
        'next frame',
        'again',
        'render A',
        'next frame',
        'again',
        'render B',
        'put back',
        'closed',
    ]
    assert shot.saved == ['B to out.png']
    assert capsys.readouterr().out.splitlines() == ["3d render 4x3 (the clipboard's text put back)"]


def test_a_render_still_identical_after_the_retakes_is_said(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-128: a set-up sent again would move the camera again
    shot = Shot(helpers, 'A')
    helpers.shoot_3d('out.png', orbit=[90.0, 0.0])
    assert shot.events.count('render A') == 2 + helpers.RETAKES
    assert shot.saved == ['A to out.png']
    assert capsys.readouterr().out.splitlines()[-1] == STALE


def test_a_render_identical_while_the_view_draws_no_frame_isnt_taken_again(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-148: off screen, or at rest, it draws none: a retake would read the same frame
    shot = Shot(helpers, 'A', drawing=False)
    helpers.shoot_3d('out.png', pan=[0.25, 0.0])
    assert shot.events[-5:] == ['again', 'render A', 'next frame', 'put back', 'closed']
    assert capsys.readouterr().out.splitlines()[-1] == STALE


@pytest.mark.parametrize(
    'options',
    [{'zoom': 2}, {'pan': [0.0, 0.1]}, {'orbit': [0.0, -5.0]}, {'mesh': 'Sphere'}],
    ids=['zoom', 'pan', 'orbit', 'another mesh'],
)
def test_a_set_up_that_moves_the_camera_or_switches_the_mesh_is_compared(
    helpers: types.ModuleType, options: View3dOptions
) -> None:
    shot = Shot(helpers, 'A', 'B')
    helpers.shoot_3d('out.png', **options)
    assert shot.events[2] == 'render A' and shot.saved == ['B to out.png']


@pytest.mark.parametrize(
    'options',
    [{'graph': 'g'}, {'view': 'Top'}, {'tiling': 2.0}, {'mesh': 'Plane'}, {}],
    ids=['graph', 'view', 'tiling', 'the mesh shown', 'nothing'],
)
def test_a_shot_that_needs_no_comparison_takes_one_render(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], options: View3dOptions
) -> None:
    # a view or a graph may be what is shown already: an identical render is no sign of a stale one
    shot = Shot(helpers, 'A')
    helpers.shoot_3d('out.png', **options)
    assert [e for e in shot.events if e.startswith('render')] == ['render A']
    assert not [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D render: ')]


def test_without_options_nothing_is_set_up(helpers: types.ModuleType) -> None:
    shot = Shot(helpers, 'A')
    helpers.shoot_3d('out.png')
    assert shot.events == ['on screen', 'again', 'render A', 'put back', 'closed']


@pytest.mark.parametrize(
    'options, said',
    [
        ({'mesh': 'Teapot'}, "unknown mesh 'Teapot'"),
        ({'view': 'Diagonal'}, "unknown view 'Diagonal'"),
        ({'graph': 'one'}, 'graph one has one output'),
    ],
)
def test_a_set_up_refused_doesnt_touch_the_window(helpers: types.ModuleType, options: View3dOptions, said: str) -> None:
    # refused before anything changes, the user's window included
    shot = Shot(helpers, 'A')
    with pytest.raises(RuntimeError, match=said):
        helpers.shoot_3d('out.png', **options)
    assert shot.events == []


def test_a_set_up_refused_by_what_designer_shows_doesnt_touch_the_window(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-127: set_3d_view's own checks (an orbit of less than a pixel, a panel not shown...) come first too
    refused = "orbit's 0.2 degrees right is less than one pixel's drag, 0.45 degrees: it would do nothing"
    shot = Shot(helpers, 'A', refused=refused)
    with pytest.raises(RuntimeError, match='less than one pixel'):
        helpers.shoot_3d('out.png', orbit=[0.2, 0.0])
    assert shot.events == []


def test_a_3d_view_not_shown_is_refused_before_the_window_changes(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-393: the docstring's promise
    shot = Shot(helpers, 'A')

    def not_shown(mw: 'QtWidgets.QMainWindow') -> NoReturn:
        raise RuntimeError('the 3D View panel is not visible')

    vars(helpers)['_3d_dock'] = not_shown
    with pytest.raises(RuntimeError, match='3D View panel is not visible'):
        helpers.shoot_3d('out.png')
    assert shot.events == []


@pytest.mark.parametrize('way', ['minimized', 'covered', 'hidden'])
def test_each_spy_on_the_windows_expose_events_is_removed(helpers: types.ModuleType, way: str) -> None:
    # REVIEW.md TST-428: the Expose spies of _wait_on_screen and _wait_off_screen were installed and never seen removed.
    # _wait_off_screen observes AppKit's notifications since (ROADMAP item 101): each closed, a test of its own
    installed: list[SimpleNamespace] = []
    removed: list[SimpleNamespace] = []

    def event_signal(
        watched: SimpleNamespace, kinds: Sequence[str], seen: Callable[[str], None] | None = None
    ) -> SimpleNamespace:
        spy = SimpleNamespace(fired='its signal')
        installed.append(spy)
        return spy

    class Watched(Window):
        def windowHandle(self) -> SimpleNamespace:
            handle = super().windowHandle()
            handle.removeEventFilter = removed.append
            return handle

    vars(helpers)['_event_signal'] = event_signal
    mac = Mac(**{way: True})
    _on(helpers, mac)
    with on_screen(helpers, Watched(mac)):
        mac.done.append('shot')
    assert installed and sorted(map(id, removed)) == sorted(map(id, installed))


class Covering(Frames):
    """Frames, whose wait once the window is on screen sees it covered again, `times` times: the user's click on a
    window of their own under Designer's click-through window raises theirs as the view draws."""

    def __init__(self, mac: Mac, times: int) -> None:
        super().__init__(log=mac.done)
        self.mac = mac
        self.times = times

    def shown(self, since: int) -> None:
        super().shown(since)
        if self.times:
            self.times -= 1
            self.mac.state['covered'] = True

    def off_screen(self) -> bool:
        return self.mac.covered()


def test_a_window_covered_again_as_the_view_drew_is_brought_in_front_again(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-163: shown()'s wait ends as the window goes off screen; the shot went on with it off screen, and its
    # render was the view's last frame, said nowhere
    mac = Mac(covered=True)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac), Covering(mac, 1)):
        mac.done.append('shot')
    before = mac.done[: mac.done.index('shot')]
    assert [step for step in before if step == 'show' or step.startswith('shown')] == [
        'show',
        'shown since 1',
        'show',
        'shown since 3',
    ], mac.done
    assert capsys.readouterr().out.splitlines() == [
        FRONT,
        "Designer's window: brought in front again, transparent, as another window covered it during the shot",
        PUT_BACK,
    ]


def test_a_window_covered_again_each_time_the_view_drew_is_refused_and_put_back(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-163: brought back at most BRINGS times, then refused, as a window that never comes on screen is
    mac = Mac(covered=True)
    _on(helpers, mac)
    refused = pytest.raises(RuntimeError, match=r"the 3D view isn't drawn: Designer's window went off screen again")
    with refused, on_screen(helpers, Window(mac), Covering(mac, 99)):
        mac.done.append('shot')
    assert 'shot' not in mac.done and mac.done.count('show') == helpers.BRINGS, mac.done
    assert mac.done[-2:] == ['put below 7', 'unfade'], mac.done


def _render_fakes(helpers: types.ModuleType, put: 'list[QtCore.QMimeData | str]') -> None:
    """_3d_render's Qt faked: a clipboard holding the user's text, whose setMimeData appends to `put`, and the 3D view's
    Camera menu with Copy Render to Clipboard."""
    qt = sys.modules['PySide6']
    image = SimpleNamespace(isNull=lambda: False)
    clipboard = SimpleNamespace(
        mimeData=lambda: SimpleNamespace(formats=lambda: ['text/plain'], data=lambda fmt: b"the user's text"),
        clear=lambda: None,
        image=lambda: image,
        setMimeData=put.append,
        dataChanged='its signal',
    )
    qt.QtWidgets.QApplication.instance.return_value = SimpleNamespace(
        clipboard=lambda: clipboard, processEvents=lambda: None
    )
    copy = SimpleNamespace(text=lambda: 'Copy Render to Clipboard', trigger=lambda: None)
    menu = SimpleNamespace(aboutToShow=SimpleNamespace(emit=lambda: None), actions=lambda: [copy])
    camera = SimpleNamespace(text=lambda: 'Camera', menu=lambda: menu)
    bar = SimpleNamespace(actions=lambda: [camera])
    vars(helpers)['_3d_dock'] = lambda mw: SimpleNamespace(findChildren=lambda kind: [bar])
    vars(helpers)['_until'] = lambda state, limit, signals=(): True
    vars(helpers)['_mac_window'] = lambda mw: None  # the real one reads the machine's clipboard through AppKit


def test_the_users_text_put_back_after_a_render_is_handed_to_the_pasteboard_at_once(
    faked_helpers: types.ModuleType,
) -> None:
    # REVIEW.md HLP-181: on macOS Qt only promises what setMimeData puts there, and Designer hands it over when another
    # app asks: a paste waited while Designer was busy, and the text was gone once Designer was killed
    helpers = faked_helpers
    done: list[QtCore.QMimeData | str] = []  # the mime data put back, then 'handed over'
    _render_fakes(helpers, done)
    vars(helpers)['_mac_window'] = lambda mw: SimpleNamespace(hand_over_clipboard=lambda: done.append('handed over'))
    helpers._3d_render('the main window')
    assert len(done) == 2 and done[1] == 'handed over', done


def test_an_abort_landing_on_the_renders_put_back_of_the_clipboard_still_puts_the_users_text_back(
    faked_helpers: types.ModuleType,
) -> None:
    # REVIEW.md HLP-171: the plugin raises its abort at a traced line; landed on the `finally`'s first line, it skipped
    # the put-back, and the render stayed on the user's clipboard instead of their text
    import ast

    import designer_helpers

    helpers = faked_helpers
    put: list[QtCore.QMimeData | str] = []
    _render_fakes(helpers, put)
    tree = ast.parse(designer_helpers.source())
    render = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_3d_render')
    finally_first = next(n for n in ast.walk(render) if isinstance(n, ast.Try) and n.finalbody).finalbody[0].lineno

    def tracer(frame: FrameType, event: str, arg: object) -> Tracer | None:
        if frame.f_code.co_name != '_3d_render':
            return None
        if event == 'line' and frame.f_lineno == finally_first:
            raise Abort  # the plugin's tracer raises so; Python then stops tracing (sys.settrace)
        return tracer

    sys.settrace(tracer)
    try:
        with pytest.raises(Abort):
            helpers._3d_render('the main window')
    finally:
        sys.settrace(None)
    assert len(put) >= 1, "the user's clipboard wasn't put back"


class TakenUp(Covering):
    """Covering, the user making Designer the active app as the view draws: they switched to it, then covered it."""

    def shown(self, since: int) -> None:
        super().shown(since)
        self.mac.is_active = True


def test_a_window_put_on_screen_again_within_one_look_once_the_user_is_in_designer_is_made_opaque_first(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-172: the bring called itself without between(): nothing more was faded, its line said no
    # ", transparent", and the windows the first bring faded stayed transparent while the user was in Designer
    mac = Mac(covered=True)
    _on(helpers, mac)
    with on_screen(helpers, Window(mac), TakenUp(mac, 1)):
        assert mac.appearance(MAIN) == OPAQUE, 'left transparent, the user in Designer'
        mac.done.append('shot')
    assert capsys.readouterr().out.splitlines()[:3] == [
        FRONT,
        OPAQUE_AT_ONCE,
        "Designer's window: brought in front again, as another window covered it during the shot",
    ]
