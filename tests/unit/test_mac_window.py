"""A Designer just started giving the keyboard back (designer_helpers/mac_window.py's give_back_activation; REVIEW.md
SRV-148), with sd and PySide6 faked."""

import types

import pytest

GIVEN = 'gave the keyboard back to the app in front before it'


class App:
    """_MacWindow, faked: whether Designer is the active app, and what was done, in order. Hiding Designer makes the
    app active before it active again (measured: mac_window.py), unless it `stays` the active app."""

    def __init__(self, active: bool, stays: bool = False) -> None:
        self.is_active = active
        self.stays = stays
        self.done: list[str] = []

    def active(self) -> bool:
        return self.is_active

    def hide(self) -> None:
        self.done.append('hide')
        self.is_active = self.stays

    def unhide(self) -> None:
        self.done.append('unhide')


@pytest.fixture
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    vars(faked_helpers)['_settle'] = lambda seconds: None
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
