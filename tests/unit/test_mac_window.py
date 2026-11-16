"""A Designer just started giving the keyboard back (designer_helpers/mac_window.py's give_back_activation; REVIEW.md
SRV-148), with sd and PySide6 faked."""

import sys
import types
from collections.abc import Callable, Sequence
from types import SimpleNamespace

import pytest

GIVEN = 'gave the keyboard back to the app in front before it'


class App:
    """_MacWindow, faked: whether Designer is the active app, and what was done, in order. Hiding Designer makes the
    app active before it active again (measured: mac_window.py), unless it `stays` the active app."""

    def __init__(self, active: bool, stays: bool = False, hidden: bool = False) -> None:
        self.is_active = active
        self.stays = stays
        self.is_hidden = hidden
        self.done: list[str] = []

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
    vars(faked_helpers)['_event_signal'] = lambda window, kinds, seen=None: SimpleNamespace(fired='its signal')
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


def test_the_hide_and_the_show_are_waited_for_on_qts_callbacks_not_a_fixed_time(helpers: types.ModuleType) -> None:
    # REVIEW.md SRV-150: 1.0 s after the hide and 1.0 s after the show, whatever macOS did (AGENTS.md: callbacks, never
    # a time measured here)
    def fixed(seconds: float) -> None:
        raise AssertionError('a fixed wait of %g s' % seconds)

    waited: list[tuple[bool, float, list[object]]] = []

    def until(state: Callable[[], object], limit: float, signals: Sequence[object] = ()) -> bool:
        waited.append((bool(state()), limit, list(signals)))
        return bool(state())

    watched: list[tuple[object, tuple[str, ...]]] = []
    removed: list[object] = []
    spy = SimpleNamespace(fired='the Expose signal')
    handle = SimpleNamespace(isExposed=lambda: True, removeEventFilter=removed.append)

    def event_signal(window: object, kinds: Sequence[str], seen: object = None) -> SimpleNamespace:
        watched.append((window, tuple(kinds)))
        return spy

    vars(helpers)['_settle'] = fixed
    vars(helpers)['_until'] = until
    vars(helpers)['_event_signal'] = event_signal
    mac = App(active=True)
    _on(helpers, mac)
    top = SimpleNamespace(windowHandle=lambda: handle)
    vars(helpers)['_APP'] = SimpleNamespace(
        getQtForPythonUIMgr=lambda: SimpleNamespace(getMainWindow=lambda: SimpleNamespace(window=lambda: top))
    )
    helpers.give_back_activation()
    qt = sys.modules['PySide6'].QtGui
    assert waited == [
        (True, helpers.ACTIVATION_WAIT, [qt.QGuiApplication.instance().applicationStateChanged]),  # no longer active
        (True, helpers.ACTIVATION_WAIT, ['the Expose signal']),  # on screen again
    ]
    assert watched == [(handle, ('Expose',))]
    assert removed == [spy]  # REVIEW.md TST-428: the spy is removed


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
    # exposes it (REVIEW.md HLP-160, measured): the wait for its exposure then ran ACTIVATION_WAIT, a limit as its time
    held: list[bool] = []

    def until(state: Callable[[], object], limit: float, signals: Sequence[object] = ()) -> bool:
        held.append(bool(state()))
        return held[-1]

    handle = SimpleNamespace(isExposed=lambda: False, removeEventFilter=lambda spy: None)  # covered whole
    top = SimpleNamespace(windowHandle=lambda: handle)
    vars(helpers)['_until'] = until
    vars(helpers)['_APP'] = SimpleNamespace(
        getQtForPythonUIMgr=lambda: SimpleNamespace(getMainWindow=lambda: SimpleNamespace(window=lambda: top))
    )
    mac = Unhides(active=True)
    _on(helpers, mac)
    helpers.give_back_activation()
    assert mac.done == ['hide', 'unhide'] and held == [True, True], (mac.done, held)
