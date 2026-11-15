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


def test_every_render_line_is_read_in_order(window_states: ModuleType) -> None:
    # the window's state as each render of a shot was read: all of them, not only the last
    printed = (
        'RENDER covered=False opacity=0 through=True\n'
        "Designer's window: brought in front again\n"
        '  RENDER covered=True opacity=0 through=True\n'
        'STATE covered=True opacity=1 through=False\n'
    )
    assert window_states.renders(printed) == [
        {'covered': 'False', 'opacity': '0', 'through': 'True'},
        {'covered': 'True', 'opacity': '0', 'through': 'True'},
    ]


@pytest.mark.parametrize(
    'event, said, after, seen',
    [
        # a window brought over Designer's: the shot brought it in front again, and said so
        (
            'cover',
            "Designer's window: brought in front again, transparent, as another window covered it during the shot\n",
            {},
            True,
        ),
        ('cover', '', {}, False),
        # REVIEW.md TST-416: said without ', transparent' when Designer is the active app at that look
        (
            'cover',
            "Designer's window: brought in front again, as another window covered it during the shot\n",
            {},
            True,
        ),
        (
            'later',
            "Designer's window: brought in front again, as another window covered it during the shot\n",
            {},
            True,
        ),
        (
            'later',
            "Designer's window: brought in front again, transparent, as another window covered it during the shot\n",
            {},
            True,
        ),
        ('later', "Designer's window: put back behind the window that was in front of it\n", {}, False),
        # TWO's smaller window raised: in front of the cover after the shot, which TWO put in front of it
        ('raise', '', {'order': 'later,cover,main,below'}, True),
        ('raise', '', {'order': 'cover,later,main,below'}, False),
        # the cover closed or minimized: off screen after the shot, as CoreGraphics lists it
        ('close', '', {'cover_on_screen': 'False'}, True),
        ('close', '', {'cover_on_screen': 'True'}, False),
        ('minimize', '', {'cover_on_screen': 'False'}, True),
        ('minimize', '', {'cover_on_screen': 'True'}, False),
        ('minimize', '', {}, False),  # not read: not seen
        (None, '', {}, True),  # no event
    ],
)
def test_an_event_during_a_shot_is_seen_to_have_happened_only_by_its_effect(
    window_states: ModuleType, event: str | None, said: str, after: dict[str, str], seen: bool
) -> None:
    # REVIEW.md TST-415: an event that did nothing left the put-back check passing on the put-back it was made to catch
    assert window_states.event_seen(event, said, after) is seen


def test_every_event_has_a_way_to_be_seen(window_states: ModuleType) -> None:
    # REVIEW.md TST-415: a new event the check can't see would pass whatever it did
    assert set(window_states.SEEN_BY) == set(window_states.EVENTS)


@pytest.mark.parametrize(
    'printed, clear',
    [
        ('HITS opaque=main transparent=main through=cover\nIN_FRONT 0\n', True),
        ('HITS opaque=another transparent=another through=another\nIN_FRONT 1\n', False),
        ('IN_FRONT 2\nIN_FRONT 0\n', True),  # the last reading counts
        ('HITS opaque=main transparent=main through=cover\n', False),  # not read: not clear
    ],
)
def test_a_reading_is_clear_only_when_no_window_was_found_in_front(
    window_states: ModuleType, printed: str, clear: bool
) -> None:
    # REVIEW.md TST-417: another app's window in front of the window read changes the reading; that try is taken again
    assert window_states.nothing_in_front(printed) is clear


MADE_OPAQUE = "Designer's window: made opaque at once, as Designer became the active app during the shot\n"


@pytest.mark.parametrize(
    'said, off, after, activated',
    [
        (MADE_OPAQUE, {'active': 'False'}, {'active': 'False'}, True),  # made the active app, then left
        (LEFT_UP, {'active': 'False'}, {'active': 'True'}, True),
        ('', {'active': 'False'}, {'active': 'True'}, True),  # focus lost, nothing said
        ('', {'active': 'False'}, {'active': 'False'}, False),
        ('', {'active': 'True'}, {'active': 'True'}, False),  # the active app already as the shot began: not judged
        ('', {}, {'active': 'True'}, False),  # not read before the shot
    ],
)
def test_designer_made_the_active_app_during_a_shot_is_told_from_the_shot_and_the_states(
    window_states: ModuleType, said: str, off: dict[str, str], after: dict[str, str], activated: bool
) -> None:
    # REVIEW.md TST-418: such a way is taken again; a shot that makes Designer the active app itself does it each time
    assert window_states.activated(said, off, after) is activated


@pytest.mark.parametrize(
    'name',
    [
        'check_the_3d_view_isnt_drawn_while_designers_window_is_off_screen',
        'check_a_click_goes_through_designers_window_once_transparent_and_click_through',
        'check_a_window_under_designers_transparent_window_counts_as_visible',
        'check_a_3d_shot_puts_designers_window_on_screen_without_taking_focus',
    ],
)
def test_the_window_checks_the_pool_disturbed_read_while_no_designer_starts(name: str) -> None:
    # REVIEW.md TST-417: the windows a Designer of the pool brings as it starts, and the activation it hands over,
    # came in bursts longer than the retries; holding the pool's launch lock, none starts or quits meanwhile
    import ast
    from pathlib import Path

    path = Path(__file__).parents[1] / 'test_all_tools' / 'editor_panels_and_fit' / 'checks.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    check = next(node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef) and node.name == name)
    held = [
        node
        for node in ast.walk(check)
        if isinstance(node, ast.With)
        and any('no_designer_starting' in ast.unparse(item.context_expr) for item in node.items)
    ]
    assert held, '%s reads windows without holding the launch lock' % name
    # the readings inside it: the snippets that read windows, or the shots
    inside = ast.unparse(held[0])
    assert any(call in inside for call in ('without_others_in_front(', "'screenshot_designer'")), inside[:200]
