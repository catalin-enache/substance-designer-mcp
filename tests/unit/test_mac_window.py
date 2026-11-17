"""A Designer just started giving the keyboard back (designer_helpers/mac_window.py's give_back_activation; REVIEW.md
SRV-148), and the waits woken by AppKit's notifications (ROADMAP item 101), with sd and PySide6 faked."""

import sys
import types
from collections.abc import Callable, Sequence
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from appkit_fakes import Center, Notices

if TYPE_CHECKING:  # for the checker only: the types the faked helpers take; PySide6 is faked at run time
    from PySide6 import QtCore

    from designer_helpers.mac_window import _Notices

GIVEN = 'gave the keyboard back to the app in front before it'
UNHIDDEN = 'NSApplicationDidUnhideNotification'


class App:
    """_MacWindow, faked: whether Designer is the active app, what was done, in order, and the notices made (Notices).
    Hiding Designer makes the app active before it active again (measured: mac_window.py), unless it `stays` the
    active app."""

    def __init__(self, active: bool, stays: bool = False, hidden: bool = False) -> None:
        self.is_active = active
        self.stays = stays
        self.is_hidden = hidden
        self.done: list[str] = []
        self.notified: list[Notices] = []

    def notices(self, names: Sequence[str]) -> Notices:
        self.notified.append(Notices(names))
        return self.notified[-1]

    def active(self) -> bool:
        return self.is_active

    def hidden(self) -> bool:
        return self.is_hidden

    def hide(self) -> None:
        self.done.append('hide')
        self.is_active = self.stays

    def unhide(self) -> None:
        self.done.append('unhide')


@pytest.fixture
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    vars(faked_helpers)['_settle'] = lambda seconds: None
    vars(faked_helpers)['_until'] = lambda state, limit, signals=(): bool(state())
    # the Qt object relaying CoreFoundation's callback: its signal's emit is the callback (mac_window.py's _Notices)
    vars(faked_helpers)['_relay'] = lambda: SimpleNamespace(fired=SimpleNamespace(emit=lambda *sent: None))
    return faked_helpers


def _on(helpers: types.ModuleType, mac: App | None) -> None:
    vars(helpers)['_mac_window'] = lambda mw: mac


def test_designer_the_active_app_gives_it_back_to_the_app_before_it(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # it became the active app as it started, taking the keyboard: hidden, then shown without being made active
    mac = App(active=True)
    _on(helpers, mac)
    helpers.give_back_activation()
    assert mac.done == ['hide', 'unhide']
    assert capsys.readouterr().out.splitlines() == [GIVEN]


def test_designer_not_the_active_app_is_left_as_it_is(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    mac = App(active=False)
    _on(helpers, mac)
    helpers.give_back_activation()
    assert mac.done == [] and capsys.readouterr().out == ''


def test_off_macos_nothing_is_done(helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    _on(helpers, None)
    helpers.give_back_activation()
    assert capsys.readouterr().out == ''


def test_designer_still_the_active_app_after_is_said(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    mac = App(active=True, stays=True)
    _on(helpers, mac)
    helpers.give_back_activation()
    assert mac.done == ['hide', 'unhide']
    assert capsys.readouterr().out.splitlines() == ['still the active app after it was hidden and shown again']


def test_the_hide_and_the_show_are_waited_for_on_callbacks_not_a_fixed_time(helpers: types.ModuleType) -> None:
    # REVIEW.md SRV-150: 1.0 s after the hide and 1.0 s after the show, whatever macOS did (AGENTS.md: callbacks, never
    # a time measured here). The show is woken by AppKit's notification that Designer was unhidden, which came with
    # macOS no longer saying it hidden (shot3d.py's module docstring; ROADMAP item 101): Qt's expose events came before
    # the unhide took in one probe and after it in another (REVIEW.md HLP-160)
    def fixed(seconds: float) -> None:
        raise AssertionError('a fixed wait of %g s' % seconds)

    # each wait's signals: the faked app's applicationStateChanged, then the fake notices' `fired`
    waited: list[tuple[bool, float, list[QtCore.SignalInstance | str]]] = []

    def until(state: Callable[[], bool], limit: float, signals: Sequence['QtCore.SignalInstance | str'] = ()) -> bool:
        waited.append((bool(state()), limit, list(signals)))
        return bool(state())

    vars(helpers)['_settle'] = fixed
    vars(helpers)['_until'] = until
    mac = App(active=True)
    _on(helpers, mac)
    helpers.give_back_activation()
    qt = sys.modules['PySide6'].QtGui
    assert waited == [
        (True, helpers.ACTIVATION_WAIT, [qt.QGuiApplication.instance().applicationStateChanged]),  # no longer active
        (True, helpers.ACTIVATION_WAIT, ['notified of ' + UNHIDDEN]),  # shown again
    ]
    assert [(n.names, n.opened, n.closed) for n in mac.notified] == [((UNHIDDEN,), 1, 1)]  # observed, then no more


class Observed:
    """_MacWindow, faked for a wait on AppKit's notifications: its notices are real (_Notices), on the faked `center`,
    each name a number of its own, sent by Designer, or by its window for an NSWindow one."""

    APP, WINDOW = 21, 22

    def __init__(self, helpers: types.ModuleType, center: Center) -> None:
        self.helpers = helpers
        self.center = center
        self.made: list[_Notices] = []

    def notices(self, names: Sequence[str]) -> '_Notices':
        sent = [(10 + i, self.WINDOW if name.startswith('NSWindow') else self.APP) for i, name in enumerate(names)]
        made: _Notices = self.helpers._Notices(self.center, sent)
        self.made.append(made)
        return made


NAMES = (UNHIDDEN, 'NSWindowDidChangeOcclusionStateNotification')


def test_a_wait_on_appkits_notifications_is_woken_by_them_while_it_observes_them(helpers: types.ModuleType) -> None:
    # ROADMAP item 101: no Qt callback says Designer was unhidden, nor its window off screen (REVIEW.md HLP-173)
    center = Center()
    seen: list[tuple[float, list[object], dict[int, list[tuple[int, int | None]]]]] = []

    def until(state: Callable[[], bool], limit: float, signals: Sequence[object] = ()) -> bool:
        seen.append((limit, list(signals), {k: list(v) for k, v in center.observers.items()}))
        return bool(state())

    vars(helpers)['_until'] = until
    mac = Observed(helpers, center)
    assert helpers._until_notified(mac, lambda: True, 2.0, NAMES)
    assert len(seen) == 1 and len(mac.made) == 1
    limit, signals, observers = seen[0]
    assert limit == 2.0 and signals == [mac.made[0].fired]
    assert list(observers.values()) == [[(10, Observed.APP), (11, Observed.WINDOW)]]
    assert center.observers == {}, 'observed after the wait'
    assert helpers._until_notified(mac, lambda: False, 2.0, NAMES) is False, "the wait's result, not held"
    # REVIEW.md TST-526: the signals given wake it too, after AppKit's notifications
    helpers._until_notified(mac, lambda: True, 2.0, NAMES, ['expose'])
    assert seen[-1][1] == [mac.made[-1].fired, 'expose'], seen[-1]


def test_corefoundation_is_given_the_callback_the_notices_hold_and_it_relays_what_comes(
    helpers: types.ModuleType,
) -> None:
    # REVIEW.md TST-526: a callback made for the call and not held is freed after it, and the next notification would
    # crash Designer; one that doesn't emit `fired` wakes no wait. The callback is called as CoreFoundation does: the
    # center, the observer, the name, the sender and the user info, five pointers
    center = Center()
    relayed: list[tuple[object, ...]] = []
    vars(helpers)['_relay'] = lambda: SimpleNamespace(fired=SimpleNamespace(emit=lambda *sent: relayed.append(sent)))
    made = Observed(helpers, center).notices(NAMES)
    made.open()
    try:
        assert len(center.callbacks) == 2 and all(c is made._callback for c in center.callbacks), center.callbacks
        made._callback(1, 2, 3, 4, 5)
        assert relayed == [(1, 2, 3, 4, 5)], relayed
    finally:
        made.close()


def test_an_abort_at_any_event_of_a_wait_on_appkits_notifications_leaves_no_observer(helpers: types.ModuleType) -> None:
    # an observer left once its callback is freed: the next notification would crash Designer. The plugin raises its
    # abort at a traced event, once, then stops tracing (REVIEW.md HLP-180): landed on the removal after the wait, it
    # skips it. Center stands for CoreFoundation: in a file of its own, it isn't traced, as Qt isn't
    from aborts import at_each_event

    center = Center()
    observed: list[bool] = []  # whether the wait ran while observing, in each run that reached it

    def until(state: Callable[[], bool], limit: float, signals: Sequence[object] = ()) -> bool:
        observed.append(bool(center.observers))
        return bool(state())

    vars(helpers)['_until'] = until
    mac = Observed(helpers, center)

    def run() -> None:
        helpers._until_notified(mac, lambda: True, 2.0, NAMES)

    landed = []
    for where in at_each_event(run, ('designer_helpers', __file__), center.observers.clear):
        assert center.observers == {}, where
        landed.append(where)
    assert landed and observed and all(observed)


def test_no_window_handle_is_taken_through_a_wrapper_dropped_at_once() -> None:
    # REVIEW.md SRV-155, TST-432 (measured in Designer, 2026-11-15): the handle of `mw.window().windowHandle()` read
    # "already deleted" a line later, in 4 of 4 fresh calls, as PySide drops the top-level widget's wrapper it was taken
    # through; held, it stayed valid. Once a wrapper was held elsewhere it stayed valid too, so no live fact pins it.
    # give_back_activation raised there, leaving the Designer it hid hidden, and HIDE never hid one
    import os
    import re

    from conftest import ROOT

    chained = re.compile(r'\.window\(\)\.windowHandle\(\)')
    found = []
    for folder in ('mcp_server', 'plugin', 'client', 'examples', os.path.join('tests', 'test_all_tools')):
        for top, dirs, files in os.walk(os.path.join(ROOT, folder)):
            dirs[:] = [d for d in dirs if d not in ('venv', '__pycache__')]
            for name in files:
                if name.endswith('.py'):
                    with open(os.path.join(top, name), encoding='utf-8') as f:
                        found += ['%s:%d' % (name, i) for i, line in enumerate(f, 1) if chained.search(line)]
    assert found == []


def test_a_designer_started_hidden_that_became_the_active_app_stays_hidden(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md SRV-152: launch_designer opens Designer hidden; shown again, it would come on the user's screen
    mac = App(active=True, hidden=True)
    _on(helpers, mac)
    helpers.give_back_activation()
    assert mac.done == ['hide']
    assert capsys.readouterr().out.splitlines() == [
        'gave the keyboard back to the app in front before it, still hidden'
    ]


def test_a_designer_started_hidden_that_activation_showed_is_hidden_again(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md SRV-161, measured 2026-11-16: activating a hidden Designer unhides it, so give_back_activation read it
    # shown, hid it, then showed it again on the user's screen
    mac = App(active=True, hidden=False)
    _on(helpers, mac)
    helpers.give_back_activation(started_hidden=True)
    assert mac.done == ['hide']
    assert capsys.readouterr().out.splitlines() == [
        'gave the keyboard back to the app in front before it, hidden again, as it was started'
    ]


class Unhides(App):
    """App, whose hide() and unhide() also hide and show it, as macOS says (isHidden)."""

    def hide(self) -> None:
        super().hide()
        self.is_hidden = True

    def unhide(self) -> None:
        super().unhide()
        self.is_hidden = False


def test_the_show_is_waited_for_until_macos_says_designer_is_shown_not_until_its_window_is_exposed(
    helpers: types.ModuleType,
) -> None:
    # REVIEW.md HLP-166: an unhidden window goes behind the active app's window, and once covered whole, Qt no longer
    # exposes it (REVIEW.md HLP-160, measured): the wait for its exposure then ran ACTIVATION_WAIT, a limit as its time.
    # The wait reads macOS's flag, which Unhides sets as it unhides. The main window here is covered whole: a wait that
    # read its exposure would never hold (REVIEW.md TST-515)
    held: list[bool] = []

    def until(state: Callable[[], bool], limit: float, signals: Sequence['QtCore.SignalInstance | str'] = ()) -> bool:
        held.append(bool(state()))
        return held[-1]

    handle = SimpleNamespace(isExposed=lambda: False)  # covered whole; any other read of it raises
    top = SimpleNamespace(windowHandle=lambda: handle)
    vars(helpers)['_until'] = until
    vars(helpers)['_APP'] = SimpleNamespace(
        getQtForPythonUIMgr=lambda: SimpleNamespace(getMainWindow=lambda: SimpleNamespace(window=lambda: top))
    )
    mac = Unhides(active=True)
    _on(helpers, mac)
    helpers.give_back_activation()
    assert mac.done == ['hide', 'unhide'] and held == [True, True], (mac.done, held)
