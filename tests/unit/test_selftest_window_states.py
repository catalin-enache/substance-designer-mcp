"""What the self-test's 3D window checks read of Designer's window (editor_panels_and_fit/window_states.py): the
state lines its snippets print, and whether a shot left Designer not the active app, judged only where it can be
(REVIEW.md TST-392)."""

from types import ModuleType
from typing import cast

import pytest
from selftest_fakes import fresh


@pytest.fixture
def window_states() -> ModuleType:
    return cast(ModuleType, fresh('editor_panels_and_fit.window_states'))


def test_focus_is_kept_while_designer_stays_not_the_active_app(window_states: ModuleType) -> None:
    assert window_states.focus({'active': 'False'}, {'active': 'False'}) is True


def test_focus_is_taken_when_the_shot_made_designer_the_active_app(window_states: ModuleType) -> None:
    assert window_states.focus({'active': 'False'}, {'active': 'True'}) is False


@pytest.mark.parametrize('after', ['True', 'False'])
def test_focus_isnt_judged_when_designer_was_the_active_app_before(window_states: ModuleType, after: str) -> None:
    # TST-392: a shot can't be seen taking focus Designer already had; hiding it again would read as not taking it
    assert window_states.focus({'active': 'True'}, {'active': after}) is None


@pytest.mark.parametrize('before, after', [({}, {'active': 'False'}), ({'active': 'False'}, {})])
def test_focus_isnt_judged_without_both_states(
    window_states: ModuleType, before: dict[str, str], after: dict[str, str]
) -> None:
    assert window_states.focus(before, after) is None


@pytest.mark.parametrize(
    'first, second, ahead',
    [('cover', 'main', True), ('main', 'below', True), ('below', 'main', False), ('later', 'main', False)],
)
def test_a_window_is_ahead_of_the_windows_listed_after_it(
    window_states: ModuleType, first: str, second: str, ahead: bool
) -> None:
    # REVIEW.md HLP-130, HLP-131: the order Designer's windows are left in; one not listed is ahead of none
    assert window_states.ahead('cover,main,below', first, second) is ahead


LEFT_UP = "Designer's window: left on screen, as Designer became the active app during the shot\n"


@pytest.mark.parametrize(
    'said, before, after, became',
    [
        (LEFT_UP, {'active': 'False'}, {'active': 'True'}, True),
        (LEFT_UP, {}, {}, True),  # said so, whatever was read
        ('', {'active': 'False'}, {'active': 'True'}, True),  # activation brought its windows in front: nothing said
        ('', {'active': 'True'}, {'active': 'True'}, False),  # the active app already
        ('', {'active': 'False'}, {'active': 'False'}, False),
        ('', {}, {'active': 'True'}, False),  # not read before: as the tool, judged
    ],
)
def test_designer_becoming_the_active_app_during_a_shot_is_told_apart(
    window_states: ModuleType, said: str, before: dict[str, str], after: dict[str, str], became: bool
) -> None:
    # REVIEW.md TST-399: the window's put-back can't be judged then; the tool leaves the window up, as decided
    assert window_states.became_active(said, before, after) is became


def test_the_last_state_line_of_each_kind_is_read(window_states: ModuleType) -> None:
    printed = (
        'BEFORE minimized=False active=False\n'
        '  STATE minimized=True order=main\n'
        "Designer's window: un-minimized\n"
        'STATE minimized=False order=cover,main,below\n'
    )
    assert window_states.states(printed) == {
        'BEFORE': {'minimized': 'False', 'active': 'False'},
        'STATE': {'minimized': 'False', 'order': 'cover,main,below'},
    }
