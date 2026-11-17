"""The judgements that decide whether the self-test's frames fact and window checks pass
(editor_panels_and_fit/checks.py; REVIEW.md TST-450), on recorded readings: those measured, which pass, and readings
that must fail, so that a comparison any reading satisfies would be seen."""

from types import ModuleType

import pytest
from selftest_fakes import fresh

# measured in a scratch run (2026-11-16): a pan's counts, and a viewpoint's, held at 1 while the camera turned
PAN = [8, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8]
VIEWPOINT = [8, 1, 1, 1, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8]
# FRAMES' events: whether the window was hidden before the show, and each event's (kind, count)
Events = tuple[bool, list[tuple[str, int]]]
# shown from hidden: after a pan made meanwhile, and with nothing changed (the frames fact's SHOWN and CHANGED)
AFTER_A_PAN: Events = (True, [('Paint', 8), ('UpdateRequest', 1), ('Paint', 1), ('UpdateRequest', 1), ('Paint', 2)])
UNCHANGED: Events = (True, [('Paint', 8), ('Paint', 8), ('Paint', 8)])


@pytest.fixture
def checks() -> ModuleType:
    module: ModuleType = fresh('editor_panels_and_fit.checks')
    return module


@pytest.mark.parametrize(
    'seen, restarted',
    [
        (PAN, True),
        ([8, 8, 8, 8], False),  # no restart
        ([8, 1, 2, 3], False),  # not back at rest
        ([1, 2, 8], False),  # not at rest before
        ([8, 8], False),
        (None, False),  # not printed
    ],
    ids=['a pan, measured', 'no restart', 'not back', 'not at rest before', 'two counts', 'none read'],
)
def test_a_change_counts_restarted_only_from_rest_back_to_rest(
    checks: ModuleType, seen: list[int] | None, restarted: bool
) -> None:
    assert checks._restarted(seen, 8) is restarted


@pytest.mark.parametrize(
    'seen, held',
    [(VIEWPOINT, True), (PAN, True), ([8, 1, 2, 3, 4, 5, 6, 7, 8], False), ([8, 8, 8], False)],
    ids=['a viewpoint, measured', 'a pan, its 1 read three times', 'its restart read once', 'no restart'],
)
def test_a_viewpoints_restart_is_held_only_when_read_at_two_paints_or_more(
    checks: ModuleType, seen: list[int], held: bool
) -> None:
    assert checks._held(seen, 8) is held


@pytest.mark.parametrize(
    'events, changed, shown',
    [
        (AFTER_A_PAN, True, True),
        (UNCHANGED, False, True),
        ((False, AFTER_A_PAN[1]), True, False),  # not hidden before the show
        ((True, [('Paint', 8), ('Paint', 1), ('UpdateRequest', 1)]), True, False),  # the restart before the request
        ((True, [('Paint', 1), ('UpdateRequest', 1), ('Paint', 1)]), True, False),  # the first paint not at rest
        ((True, [('Paint', 8), ('UpdateRequest', 8), ('Paint', 8)]), False, False),  # nothing changed, but asked
        ((True, [('Paint', 8)]), False, False),  # one paint
        (None, False, False),
    ],
    ids=[
        'after a pan, measured',
        'unchanged, measured',
        'not hidden before',
        'restart before the request',
        'first paint not at rest',
        'unchanged but asked',
        'one paint',
        'none read',
    ],
)
def test_a_show_from_hidden_reads_a_change_or_none_only_in_the_order_measured(
    checks: ModuleType, events: Events | None, changed: bool, shown: bool
) -> None:
    assert checks._shown(events, changed) is shown


@pytest.mark.parametrize(
    'events, changed',
    [
        (AFTER_A_PAN, True),
        ((True, [('Paint', 8), ('Paint', 1)]), True),  # no request, the second paint a restart
        ((False, [('Paint', 8), ('UpdateRequest', 1), ('Paint', 1)]), True),  # TST-439: not judged, by its name
        (UNCHANGED, False),
        ((True, [('Paint', 8), ('Paint', 8), ('UpdateRequest', 1)]), False),  # the request after the second paint
        ((True, [('UpdateRequest', 1), ('Paint', 1)]), False),  # one paint
        (None, False),
    ],
    ids=[
        'after a pan, measured',
        'a restart at the second paint',
        'not hidden before',
        'unchanged, measured',
        'asked after the second paint',
        'one paint',
        'none read',
    ],
)
def test_a_show_after_a_pan_is_told_by_its_second_paint(
    checks: ModuleType, events: Events | None, changed: bool
) -> None:
    assert checks._changed_by_its_second_paint(events) is changed


@pytest.mark.parametrize(
    'way, state, brought',
    [
        ('covered', {'order': 'main,cover'}, True),
        ('covered', {'order': 'cover,main'}, False),
        ('covered', {'order': 'main'}, False),  # the cover not listed
        ('minimized', {'minimized': 'False'}, True),
        ('minimized', {'minimized': 'True'}, False),
        ('minimized', {}, False),
        ('hidden', {'hidden': 'False'}, True),
        ('hidden', {'hidden': 'True'}, False),
        ('hidden', {}, False),
    ],
    ids=[
        'covered, ahead of its cover',
        'covered, behind it',
        'covered, its cover unlisted',
        'minimized, shown',
        'minimized still',
        'minimized, unread',
        'hidden, shown',
        'hidden still',
        'hidden, unread',
    ],
)
def test_each_way_counts_its_window_brought_on_screen_only_from_what_it_reads(
    checks: ModuleType, way: str, state: dict[str, str], brought: bool
) -> None:
    assert checks.BROUGHT_ON_SCREEN[way](state) is brought
