"""The 3D view's frames, read from its overlay's sample count at each paint (designer_helpers/frames3d.py; REVIEW.md
HLP-148): when a change shows, when the view has settled, when Designer shown again needed no new frames. And the
shot's waits: on the view's callbacks, polled every 100 ms only where none comes, never a fixed time (`.claude/rules/waits.md`). The
live self-test re-measures the counts (editor_panels_and_fit's frames fact)."""

import os
import re
import sys
import types
from collections.abc import Callable, Sequence
from types import SimpleNamespace
from typing import TYPE_CHECKING, Literal, NoReturn, cast
from unittest import mock

import pytest

from designer_helpers import HERE

if TYPE_CHECKING:  # for the checker only: the types the faked helpers take; PySide6 is faked at run time
    from designer_helpers.frames3d import _Counts, _Frames


@pytest.fixture
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    return faked_helpers


def _counted(frames: '_Frames') -> '_Counts':
    """The counts `frames` read, once a count showed."""
    assert frames._counts is not None
    return frames._counts


def counts(helpers: types.ModuleType, *seen: int | None) -> '_Counts':
    """A _Counts with `seen` read at its paints."""
    read: _Counts = helpers._Counts()
    read.seen.extend(seen)
    return read


@pytest.mark.parametrize(
    'texts, count',
    [
        (['', 'Samples: 8\nRender Time: 0.33 s', '', ''], 8),
        (['Samples: 143\nRender Time: 4.95 s'], 143),
        (['', 'Render Time: 0.09 s', ''], None),  # Display > Samples off
        ([], None),
    ],
    ids=['rasterizer', 'pathtracer', 'samples not displayed', 'no label'],
)
def test_the_count_is_read_from_the_overlay(helpers: types.ModuleType, texts: list[str], count: int | None) -> None:
    assert helpers._samples(texts) == count


def test_the_count_waited_for_is_the_rasterizers_whole_accumulation(helpers: types.ModuleType) -> None:
    # the GPU Pathtracer counts on: its render is taken at the Rasterizer's whole accumulation (the user's choice)
    assert helpers.SAMPLES == 8


@pytest.mark.parametrize(
    'seen',
    [(1, 2, 3, 4), (4, 1, 2, 3, 4)],
    ids=['a label left at 1 as Designer was hidden mid-accumulation', 'an accumulation ending at 4'],
)
def test_an_accumulation_ending_below_samples_settles_once_the_view_is_off_screen(
    helpers: types.ModuleType, seen: tuple[int, ...]
) -> None:
    # REVIEW.md HLP-148: the material check's dialog showed Designer, the material restarted the count, and Designer
    # was hidden at 1: its next shot took that label for no count, and its waits compared renders. A count below
    # SAMPLES at rest says the view stopped there, not that it shows no count. HLP-151: off screen, which Qt's expose
    # events say, not quiet for a poll's interval, a time
    read = counts(helpers, *seen)
    assert not read.settled(0, off=False)
    assert read.settled(0, off=True)


def test_a_view_off_screen_that_never_restarted_hasnt_settled(helpers: types.ModuleType) -> None:
    assert not counts(helpers).settled(0, off=True)


def test_a_change_settles_once_the_count_restarted_and_came_back(helpers: types.ModuleType) -> None:
    # a pan, measured: the first paint after it still reads the count before (a paint reads the frame before it)
    read = counts(helpers, 8, 1, 2, 3, 4, 5, 6, 7)
    assert read.restart(0) == 1 and not read.settled(0)
    read.seen.append(8)
    assert read.settled(0)


def test_a_turn_has_moved_once_the_count_rises_after_its_restart(helpers: types.ModuleType) -> None:
    # a viewpoint or Frame: the count stays at 1 while the camera turns, Designer's own transition
    read = counts(helpers, 8, 1, 1, 1, 1)
    assert not read.moved(0)
    read.seen.append(2)
    assert read.moved(0) and not read.settled(0)


def test_only_paints_since_the_mark_count(helpers: types.ModuleType) -> None:
    # a restart and return of an earlier step say nothing of the next one
    read = counts(helpers, 1, 4, 8, 8)
    assert read.settled(0)
    assert read.restart(3) is None and not read.settled(3) and not read.moved(3)


def test_designer_shown_again_with_nothing_changed_needs_no_new_frames(helpers: types.ModuleType) -> None:
    # measured: the paints as the window comes on screen read 8, 8 (and 8); the second says the first frame restarted
    # nothing
    read = counts(helpers, 8)
    assert not read.unchanged(0)
    read.seen.append(8)
    assert read.unchanged(0)


@pytest.mark.parametrize(
    'asked, shown',
    [(False, True), (True, False)],
    ids=['nothing asked', 'the engine asked for a frame'],
)
def test_designer_shown_again_is_current_after_two_paints_once_the_engine_asked_for_none(
    helpers: types.ModuleType, asked: bool, shown: bool
) -> None:
    # measured (REVIEW.md HLP-151): with nothing changed, three paints reading 8 and no UpdateRequest, in 5 of 5 shows;
    # a change made while the window was off screen, its UpdateRequest come while hidden, as the shot's moves wait for
    # (taken), then the show: an UpdateRequest or a restart by the second paint, in 9 of 9. No quiet spell is waited for
    read = counts(helpers, 8, 8)
    assert read.shown(0, asked) is shown


def test_designer_shown_again_after_a_change_waits_for_it(helpers: types.ModuleType) -> None:
    # measured: a pan or a graph's outputs changed while hidden: the second paint reads 1
    read = counts(helpers, 8, 1)
    assert not read.unchanged(0) and not read.settled(0) and not read.shown(0, True)
    read.seen += [2, 3, 4, 5, 6, 7, 8]
    assert read.settled(0) and read.shown(0, True)


def test_a_paint_without_a_count_says_nothing(helpers: types.ModuleType) -> None:
    # the label rebuilt, or emptied, at one paint
    read = counts(helpers, None, 1, None, 8)
    assert read.restart(0) == 1 and read.settled(0)


def test_a_count_left_climbing_by_the_step_before_isnt_taken_for_the_next_steps_restart(
    helpers: types.ModuleType,
) -> None:
    # REVIEW.md HLP-159: a mark taken mid-accumulation (moved() returns at about 2) read the count left over as the
    # next step's restart, so moved() ended at its next paint while the camera still turned
    read = counts(helpers, 8, 1, 1, 2)  # a viewpoint's turn, moved at 2
    mark = len(read.seen)
    read.seen += [3, 4]  # its accumulation going on, the next step's change not shown yet
    assert read.restart(mark) is None and not read.moved(mark)
    read.seen += [1, 1]  # the next step's restart: a drop from the count before it
    assert read.restart(mark) == mark + 2 and not read.moved(mark)
    read.seen.append(2)
    assert read.moved(mark)


def test_a_show_after_an_accumulation_left_lower_ends_once_it_reaches_the_target(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-159's rule: going on from where it was left (Designer hidden mid-accumulation) is no drop, so no
    # restart; the count reaching the target says the view is at rest
    read = counts(helpers, 8, 1, 2, 3)
    mark = len(read.seen)
    read.seen += [4, 5, 6, 7]
    assert not read.shown(mark, True)
    read.seen.append(8)
    assert read.shown(mark, True)


def test_a_show_from_a_count_left_lower_isnt_ended_by_two_paints_reading_it(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-167: measured, 1 show in 5 drew two paints reading the count left lower (1) before any
    # UpdateRequest; "unchanged and not asked" ended the wait there, and the render was the first sample's
    read = counts(helpers, 8, 1)
    mark = len(read.seen)
    read.seen += [1, 1]
    assert not read.shown(mark, False)
    read.seen += [2, 3, 4, 5, 6, 7, 8]
    assert read.shown(mark, False)
    # from a count at rest, two paints restarting nothing still say nothing changed while off screen
    assert counts(helpers, 1, 8, 8, 8).shown(2, False)


def test_a_view_gone_off_screen_at_the_paint_reading_its_restart_has_settled(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-158: that paint reads the count of the frame before it, the restart's, so the change was drawn; a
    # frame more was required, and the wait ran SETTLE_LIMIT
    assert counts(helpers, 8, 1).settled(0, off=True)


def _source(part: str) -> str:
    with open(os.path.join(HERE, part + '.py'), encoding='utf-8') as f:
        return f.read()


def test_the_3d_shot_waits_on_the_view_not_a_fixed_time() -> None:
    # REVIEW.md HLP-148: 0.5 s after the window came on screen, 0.5 to 1.0 s after each step, 0.2 s after each drag
    # and wheel step, 0.5 s before each retake, whatever the view did meanwhile. `.claude/rules/waits.md`: callbacks first, then a
    # poll every 100 ms where none exists, never a time measured here
    for part in ('shot3d', 'view3d', 'scene3d', 'frames3d'):  # REVIEW.md TST-922: the set-up's steps, scene3d's
        text = _source(part)
        assert not re.findall(r'_settle\(\s*(?!0\.1\b)[\w.]+\s*\)', text), (
            part
        )  # a poll every 100 ms, where no callback exists, may stay
        assert 'time.sleep(' not in text, part
        for name in ('DRAW_WAIT', 'VIEW_TURN'):
            assert name not in text, (part, name)
    render = _source('screenshots')
    body = render[render.index('def _3d_render') : render.index('def _graph_view')]
    assert 'time.sleep(' not in body and '_until(' in body and 'dataChanged' in body, 'the clipboard, a callback'


def test_a_wait_is_woken_by_its_callbacks_and_looks_every_100_ms_otherwise(helpers: types.ModuleType) -> None:
    text = _source('waits')
    body = text[text.index('def _until') :]
    assert helpers.TICK == 100
    for needed in ('QEventLoop', '.exec(', '.connect(', 'start(TICK)', 'start(int(limit * 1000))'):
        assert needed in body, needed


def test_a_wait_ends_once_qts_quit_has_run(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-157: once QCoreApplication.exit() has run, QEventLoop.exec() returns -1 at once, processing no
    # event, so no timer fires: the wait ran on, calling state() without end (measured: 6.3 million calls in 3 s)
    qt = cast(mock.MagicMock, sys.modules['PySide6']).QtCore  # the one MagicMock every PySide6 module is (conftest)
    qt.QEventLoop.return_value.exec.return_value = -1
    qt.QTimer.return_value.isActive.return_value = True  # the limit's timer, which never fires then
    looks: list[int] = []

    def state() -> bool:
        looks.append(1)
        if len(looks) > 100:
            raise AssertionError('the wait ran on after the quit')
        return False

    assert helpers._until(state, 1.0) is False
    assert len(looks) <= 3, len(looks)


def test_a_wait_runs_no_python_in_a_slot(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-150: `look`, a Python slot, was connected to the signals given and disconnected in the finally; an
    # abort landing in it is raised again at the finally's first line, which skipped the disconnects, and `look` stayed
    # connected to the clipboard's dataChanged until Designer restarted. Connected to the loop's own quit, every one,
    # the state looked at in the wait's frame, an abort lands there and the finally runs whole
    text = _source('waits')
    body = text[text.index('def _until') :]
    assert re.findall(r'\.connect\(([\w.]+)\)', body) == ['loop.quit'] * 3
    assert 'while not state() and end.isActive():' in body


def test_no_wait_ends_on_a_quiet_spell() -> None:
    # REVIEW.md HLP-151: nothing drawn or asked for during TICK ended an accumulation and a show: a time measured here
    # after a state (`.claude/rules/waits.md`)
    text = _source('frames3d')
    code = text[text.index('from .core') :]
    assert 'quiet' not in code and '_last' not in code  # the renders' own poll keeps its TICK


def test_one_name_for_the_3d_views_viewport_and_no_parameter_never_passed() -> None:
    # REVIEW.md HLP-156
    assert "className() == 'Alg::Gui3D::ViewportWidget'" not in _source('view3d')
    assert 'woken' not in _source('frames3d')


def _frames(helpers: types.ModuleType, viewport: SimpleNamespace, render: Callable[[], str]) -> '_Frames':
    """helpers._Frames(viewport, render), on a faked viewport, with renders faked by strings."""
    frames: _Frames = helpers._Frames(viewport, render)
    return frames


def test_with_no_count_shown_renders_are_compared_between_polls_never_in_a_wait(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-148: taken in a wait's slot, each render ran Designer's events itself, a wait inside the wait; a
    # check's shot then held the bridge until its 120 s timeout
    done: list[str] = []
    renders = iter(['A', 'A', 'B', 'B'])
    label = SimpleNamespace(text=lambda: 'Render Time: 0.09 s')  # Display > Samples off
    window = SimpleNamespace(isExposed=lambda: True, removeEventFilter=lambda spy: None)  # on screen
    viewport = SimpleNamespace(
        findChildren=lambda kind: [label], removeEventFilter=lambda spy: None, windowHandle=lambda: window
    )

    def until(state: Callable[[], bool], limit: float, signals: Sequence[str] = ()) -> NoReturn:
        raise AssertionError('a wait')

    def render() -> str:
        done.append('render')
        return next(renders)

    vars(helpers)['_event_signal'] = lambda watched, kinds, seen=None: SimpleNamespace(fired='its signal')
    vars(helpers)['_until'] = until
    vars(helpers)['_settle'] = lambda seconds: done.append('poll %g' % seconds)
    frames = _frames(helpers, viewport, render)
    frames.settled(frames.mark())
    assert done == ['render', 'poll 0.1', 'render', 'poll 0.1', 'render', 'poll 0.1', 'render']


def test_a_wait_for_a_state_looks_at_each_of_the_views_events_within_its_limit(helpers: types.ModuleType) -> None:
    # a load's end (scene3d.py): looked at as the view paints, asks for a frame or is exposed, within a safety net
    label = SimpleNamespace(text=lambda: 'Samples: 8')
    window = SimpleNamespace(isExposed=lambda: True, removeEventFilter=lambda spy: None)
    viewport = SimpleNamespace(
        findChildren=lambda kind: [label], removeEventFilter=lambda spy: None, windowHandle=lambda: window
    )
    made: list[str] = []
    waited: list[tuple[float, list[str]]] = []

    def event_signal(watched: SimpleNamespace, kinds: Sequence[str], on: object = None) -> SimpleNamespace:
        made.append(','.join(kinds))
        return SimpleNamespace(fired='%s fired' % made[-1])

    def until(state: Callable[[], bool], limit: float, signals: Sequence[str] = ()) -> bool:
        waited.append((limit, list(signals)))
        return state()

    vars(helpers)['_event_signal'] = event_signal
    vars(helpers)['_until'] = until
    frames = _frames(helpers, viewport, lambda: 'a render')
    assert frames.until(lambda: True, 2.5) is True and frames.until(lambda: False, 3.0) is False
    assert waited == [
        (2.5, ['Paint,UpdateRequest fired', 'Expose fired']),
        (3.0, ['Paint,UpdateRequest fired', 'Expose fired']),
    ]


# an event the faked view gives, and the count its overlay then shows, None for none; a Wait's seconds in its place
Event = tuple[Literal['Paint', 'UpdateRequest', 'Off', 'Wait'], int | None]


def _frames_counting(
    helpers: types.ModuleType,
    exposed: bool,
    coming: Sequence[Event],
    shows: str = 'Samples: 8',
    on_screen: list[bool] | None = None,
    made: bool = False,
) -> tuple['_Frames', list[float]]:
    """A _Frames whose overlay reads `shows` as it is made, on a faked viewport `exposed` or not, and the limits its
    waits had: the events `coming` (kind, the count the overlay shows as it comes, None for none) are given one by one
    while a wait's state doesn't hold. An 'Off' takes the window off screen, as covering it does. A ('Wait', s) holds
    the events after it back from a wait whose limit is under s seconds, which ends first. `on_screen`, when
    given, holds whether the window is on screen, for the test to change. `made`: by _frames_of, as the shot makes
    it."""
    shown = [shows]
    on_screen = on_screen if on_screen is not None else [exposed]
    label = SimpleNamespace(text=lambda: shown[0])
    window = SimpleNamespace(isExposed=lambda: on_screen[0], removeEventFilter=lambda spy: None)
    viewport = SimpleNamespace(
        findChildren=lambda kind: [label], removeEventFilter=lambda spy: None, windowHandle=lambda: window
    )
    seen: list[Callable[[str], None]] = []
    limits: list[float] = []
    left = list(coming)

    def event_signal(
        watched: SimpleNamespace, kinds: Sequence[str], on: Callable[[str], None] | None = None
    ) -> SimpleNamespace:
        if on is not None:  # the viewport's paints and UpdateRequests; the window's expose events have none
            seen.append(on)
        return SimpleNamespace(fired='its signal')

    def until(state: Callable[[], bool], limit: float, signals: Sequence[str] = ()) -> bool:
        limits.append(limit)
        while left and not state():
            kind, count = left.pop(0)
            if kind == 'Wait':  # its seconds in the count's place
                assert count is not None
                if limit < count:  # a shorter wait ends first: the events after it come to a longer one
                    left.insert(0, (kind, count))
                    break
                continue
            if kind == 'Off':
                on_screen[0] = False
                continue
            assert kind in ('Paint', 'UpdateRequest'), kind  # a parametrize row escapes Event's check (TST-950)
            shown[0] = '' if count is None else 'Samples: %d' % count
            seen[0](kind)
        return state()

    vars(helpers)['_event_signal'] = event_signal
    vars(helpers)['_until'] = until
    if made:
        made_by: _Frames = helpers._frames_of('mw', viewport)
        return made_by, limits
    return _frames(helpers, viewport, lambda: 'a render'), limits


def _paints(*counts: int) -> list[Event]:
    return [('Paint', n) for n in counts]


BELOW = (  # the count, where it was read ('' on screen, ' when last drawn' off screen), and what may hold it there
    ", its sample count at %d%s, below 8: it may still have been refining, or the Rasterizer's Samples may be set below"
    ' 8 or its accumulation antialiasing off (Renderer > Edit settings)'
)
LAST_DRAWN = ' when last drawn'


def _no_panel(helpers: types.ModuleType) -> None:
    def reached(*args: object) -> NoReturn:
        raise AssertionError('the Parameters panel reached')

    for name in ('_3d_dock', '_visible_dock', '_menu_action'):
        vars(helpers)[name] = reached


@pytest.mark.parametrize('exposed, where', [(True, ''), (False, LAST_DRAWN)], ids=['on screen', 'off screen'])
def test_what_may_hold_the_count_below_8_is_said_once_a_watch(
    helpers: types.ModuleType, exposed: bool, where: str
) -> None:
    # one result may say the count of several steps: the causes once, the count each time (/simplify, HLP-215)
    frames, _ = _frames_counting(helpers, exposed, [], 'Samples: 4')
    assert [frames.below_rest(), frames.below_rest()] == [
        BELOW % (4, where),
        ', its sample count at 4%s, below 8' % where,
    ]


def test_a_settle_stuck_below_8_ends_unsettled_and_reaches_no_panel(helpers: types.ModuleType) -> None:
    _no_panel(helpers)
    frames, _ = _frames_counting(helpers, True, _paints(4, 1, 2, 3, 4), 'Samples: 4', made=True)
    assert frames.settled(frames.mark()) is False


@pytest.mark.parametrize(
    'exposed, shows, said',
    [
        (True, 'Samples: 4', BELOW % (4, '')),
        (True, 'Samples: 1', BELOW % (1, '')),
        (True, 'Samples: 8', ''),
        (True, 'Render Time: 0.09 s', ''),  # no count shown
        # REVIEW.md TST-679, measured (2026-11-21): off screen at a refused step, the count reads as last drawn, 4 and 1
        (False, 'Samples: 4', BELOW % (4, LAST_DRAWN)),
        (False, 'Samples: 1', BELOW % (1, LAST_DRAWN)),
        (False, 'Samples: 8', ''),
    ],
    ids=['samples 4', 'antialiasing off', 'at rest', 'no count', 'off screen', 'off screen at 1', 'off screen at rest'],
)
def test_a_count_below_8_names_what_may_hold_it_there(
    helpers: types.ModuleType, exposed: bool, shows: str, said: str
) -> None:
    # HLP-215: the result names the count seen and the possible causes, claiming neither (the user, 2026-11-21). Off
    # screen too: the result then hung on the window's state at the stop (REVIEW.md TST-679)
    frames, _ = _frames_counting(helpers, exposed, [], shows)
    assert frames.below_rest() == said


def test_a_view_restarted_again_after_settling_is_settled_once_its_latest_restart_counted_back(
    helpers: types.ModuleType,
) -> None:
    # ROADMAP item 112, measured when the zoom was wheel steps, each from the view at rest: the step before's restart
    # and its count back at the target were read since the mark the set-up's wait took before the zoom. The render was
    # taken at the last step's first frame, one sample: 2.09 grey levels from the view at rest at a checker's edges
    restarted_twice = counts(helpers, 8, 8, 1, 2, 3, 4, 5, 6, 7, 8, 8, 1)
    assert not restarted_twice.settled(0)
    restarted_twice.seen.extend([2, 3, 4, 5, 6, 7, 8])
    assert restarted_twice.settled(0)


def test_a_step_restarting_the_view_twice_waits_for_the_count_back_after_the_last(helpers: types.ModuleType) -> None:
    frames, limits = _frames_counting(helpers, True, _paints(2, 3, 4, 5, 6, 7, 8))
    since = frames.mark()  # before the step, as the set-up takes it
    # what the step's waits read: its first restart counted back, then its last restart
    read = [8, 1, 2, 3, 4, 5, 6, 7, 8, 8, 1]
    _counted(frames).seen.extend(read)
    frames._painted += len(read)
    frames.settled(since)
    assert _counted(frames).seen[len(read) :] == [2, 3, 4, 5, 6, 7, 8], 'the last move counted back, to the target'
    assert limits == [helpers.NO_RESTART, helpers.SETTLE_LIMIT]


def test_a_step_waits_for_its_restart_then_for_the_count_back(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-428: _Frames' waits were tested only through _Counts
    frames, limits = _frames_counting(helpers, True, _paints(8, 1, 2, 3, 4, 5, 6, 7, 8))
    frames.settled(frames.mark())
    assert limits == [helpers.NO_RESTART, helpers.SETTLE_LIMIT]
    assert _counted(frames).settled(0)


@pytest.mark.parametrize(
    'coming, settled',
    [
        (_paints(8, 1, 2, 3, 4, 5, 6, 7, 8), True),
        ([], True),  # no restart: the step changed nothing the view shows
        (_paints(8, 1, 2, 3), False),  # its net reached, the count not back
    ],
    ids=['back at rest', 'nothing changed', 'not back within the limit'],
)
def test_a_settle_says_whether_the_view_settled(helpers: types.ModuleType, coming: list[Event], settled: bool) -> None:
    # REVIEW.md HLP-214: the waits' results were dropped, and the render followed whether the count came back or not
    frames, _ = _frames_counting(helpers, True, coming)
    assert frames.settled(frames.mark()) is settled


@pytest.mark.parametrize(
    'coming, moved', [(_paints(8, 1, 1, 2, 3), True), (_paints(8, 1, 1, 1), False)], ids=['turned', 'still turning']
)
def test_a_turn_says_whether_it_ended(helpers: types.ModuleType, coming: list[Event], moved: bool) -> None:
    frames, _ = _frames_counting(helpers, True, coming)
    assert frames.moved(frames.mark()) is moved


@pytest.mark.parametrize(
    'coming, step, restarted, undrawn',
    [
        (_paints(4, 5, 6, 7, 8), None, False, False),  # the look's count went on to rest
        (_paints(4, 5), None, False, True),  # not yet: the render follows the look
        (_paints(4, 5), 'settled', True, False),  # a step restarted the view: its own wait's result is the step's
        (_paints(4, 5), 'moved', True, False),
        (_paints(4, 5), 'settled', False, True),  # a step that changed nothing: the view may still draw from the look
        (_paints(4, 5), 'moved', False, True),
    ],
    ids=[
        'the look drew it',
        'the render next',
        'a step restarted the view',
        'a turn restarted it',
        'a step changed nothing',
        'a turn changed nothing',
    ],
)
def test_a_look_that_ended_at_its_limit_is_recorded_until_a_step_restarts_the_view(
    helpers: types.ModuleType, coming: list[Event], step: str | None, restarted: bool, undrawn: bool
) -> None:
    # REVIEW.md HLP-214: the look's wait ended at its limit, and the shot said nothing. HLP-222: said at every look, also
    # before a step whose own wait then settled the view
    frames, _ = _frames_counting(helpers, True, coming, shows='Samples: 3')  # left lower off screen
    since = frames.mark()
    _counted(frames).seen.append(3)
    frames._painted += 1
    frames.shown(since)
    if step is not None:
        since = frames.mark()
        if restarted:  # a paint reading a count below the one before: the view restarted
            _counted(frames).seen.append(1)
            frames._painted += 1
        getattr(frames, step)(since)
    assert frames.undrawn is undrawn


@pytest.mark.parametrize(
    'after, asked, undrawn',
    [
        ([8, 8], 0, False),
        ([8, 8], 1, True),  # a frame asked for, the count read still the one before: what changed isn't drawn
        ([1, 2, 3, 4, 5, 6, 7, 8], 1, False),
    ],
    ids=['nothing changed', 'a frame asked for, the count stale', 'restarted and back'],
)
def test_a_look_that_ended_at_its_limit_isnt_said_once_the_view_drew_what_changed(
    helpers: types.ModuleType, after: list[int], asked: int, undrawn: bool
) -> None:
    # HLP-222's open case, measured when the zoom was wheel steps (forced, 3 of 3): a look ending at its limit, then a
    # step with no sign; during its wait the view drew what changed, and the render, said not settled, matched a plain
    # shot right after. The look's own read, its paints since, is read again as the render asks
    frames, _ = _frames_counting(helpers, True, [], shows='Samples: 8')
    since = frames.mark()
    frames.shown(since)
    assert frames.undrawn  # no paint yet: the look ended at its limit
    frames._asked += asked
    for count in after:
        _counted(frames).seen.append(count)
        frames._painted += 1
    assert frames.undrawn is undrawn


@pytest.mark.parametrize('step', ['settled', 'moved'])
def test_with_no_count_shown_a_steps_renders_compared_end_the_looks_record(
    helpers: types.ModuleType, step: str
) -> None:
    frames, _ = _frames_counting(helpers, True, [], shows='')
    compared = _comparing(frames)  # recorded, not run: no render alike
    frames.shown(frames.mark())
    assert frames.undrawn
    getattr(frames, step)(frames.mark())
    assert (frames.undrawn, len(compared)) == (False, 2)


def test_a_loads_restart_coming_after_no_restart_is_waited_for(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-286: a load of a mesh the Scene menu doesn't list, nothing but the view marking its end, began
    # drawing 2 s on: settled() alone takes no restart within NO_RESTART for a step that changed nothing
    late: list[Event] = [('Wait', 2), *_paints(8, 1, 2, 3, 4, 5, 6, 7, 8)]
    alone, _ = _frames_counting(helpers, True, late)
    assert alone.settled(alone.mark()) and _counted(alone).seen == []  # ended before the load drew a frame
    frames, limits = _frames_counting(helpers, True, late)
    since = frames.mark()
    assert frames.restarted(since) and frames.settled(since)
    assert limits[0] == helpers.SETTLE_LIMIT and _counted(frames).seen[-1] == 8, (limits, _counted(frames).seen)


def test_a_load_that_never_restarts_the_view_says_so(helpers: types.ModuleType) -> None:
    frames, limits = _frames_counting(helpers, True, [])
    assert frames.restarted(frames.mark()) is False and limits == [helpers.SETTLE_LIMIT]


@pytest.mark.parametrize(
    'exposed, coming, shows, waited',
    [
        (False, [('Wait', 2), ('UpdateRequest', 8)], 'Samples: 8', True),  # no paint off screen
        (True, [], '', False),  # no count to read: settled() then compares renders
    ],
    ids=['off screen', 'no count shown'],
)
def test_a_loads_restart_is_its_frame_asked_off_screen_and_isnt_waited_for_with_no_count(
    helpers: types.ModuleType, exposed: bool, coming: list[Event], shows: str, waited: bool
) -> None:
    frames, limits = _frames_counting(helpers, exposed, coming, shows)
    assert frames.restarted(frames.mark())
    assert limits == ([helpers.SETTLE_LIMIT] if waited else [])


def test_a_step_that_restarts_nothing_waits_no_further(helpers: types.ModuleType) -> None:
    frames, limits = _frames_counting(helpers, True, [])
    frames.settled(frames.mark())
    assert limits == [helpers.NO_RESTART]


def test_a_step_left_lower_ends_once_the_view_is_off_screen(helpers: types.ModuleType) -> None:
    # HLP-151: the label left at 3 by Designer hidden mid-accumulation; the view draws nothing more
    frames, limits = _frames_counting(helpers, False, _paints(8, 1, 2, 3))
    frames.settled(frames.mark())
    assert limits == [helpers.NO_RESTART, helpers.SETTLE_LIMIT]
    # the restart's paint, then off screen: it reads the restart's frame, so the change was drawn (REVIEW.md HLP-158)
    assert _counted(frames).seen == [8, 1]


def test_off_screen_a_step_ends_once_the_view_asks_for_a_frame(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-158: off screen the view draws no paint, so the wait for a restart always ran NO_RESTART, a limit
    # used as the wait's time; the view's UpdateRequest says it took the step (measured hidden: a mesh switch brought
    # one 0.06 s after it, a tiling one 0.71 s into its step)
    frames, limits = _frames_counting(helpers, False, [('UpdateRequest', 8)])
    looked = helpers._until
    held: list[bool] = []

    def until(state: Callable[[], bool], limit: float, signals: Sequence[str] = ()) -> bool:
        held.append(looked(state, limit, signals))
        return held[-1]

    vars(helpers)['_until'] = until
    frames.settled(frames.mark())
    assert held and all(held), (held, limits)


def test_the_waits_are_woken_as_the_view_goes_off_screen(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-158: settled() ends off screen as Qt's expose events say; woken only by the viewport's paints and
    # UpdateRequests, going off screen was seen at the next tick
    label = SimpleNamespace(text=lambda: 'Samples: 8')
    window = SimpleNamespace(isExposed=lambda: True, removeEventFilter=lambda spy: None)
    viewport = SimpleNamespace(
        findChildren=lambda kind: [label], removeEventFilter=lambda spy: None, windowHandle=lambda: window
    )
    watched: list[tuple[SimpleNamespace, tuple[str, ...]]] = []  # the stand-ins watched: the viewport, its window
    woken: list[list[tuple[str, ...]]] = []  # each wait's signals: the fake spies' `fired`, their kinds

    def event_signal(
        on: SimpleNamespace, kinds: Sequence[str], seen: Callable[[str], None] | None = None
    ) -> SimpleNamespace:
        watched.append((on, tuple(kinds)))
        return SimpleNamespace(fired=tuple(kinds))

    def until(state: Callable[[], bool], limit: float, signals: Sequence[tuple[str, ...]] = ()) -> bool:
        woken.append(list(signals))
        return True

    vars(helpers)['_event_signal'] = event_signal
    vars(helpers)['_until'] = until
    frames = _frames(helpers, viewport, lambda: 'a render')
    frames.settled(frames.mark())
    frames.moved(frames.mark())
    assert (window, ('Expose',)) in watched, watched
    assert woken and all(('Expose',) in signals for signals in woken), woken


def test_a_show_with_nothing_changed_ends_at_its_second_paint(helpers: types.ModuleType) -> None:
    # HLP-151, measured: three paints reading 8 and no UpdateRequest; the wait no longer waits for a quiet spell
    frames, limits = _frames_counting(helpers, True, _paints(8, 8, 8))
    frames.shown(frames.mark())
    assert limits == [helpers.SETTLE_LIMIT] and _counted(frames).seen == [8, 8]


def test_a_show_after_a_change_waits_for_its_restart_and_return(helpers: types.ModuleType) -> None:
    # measured: an UpdateRequest right after the first paint, then the restart
    frames, limits = _frames_counting(
        helpers, True, [('Paint', 8), ('UpdateRequest', 8), *_paints(1, 2, 3, 4, 5, 6, 7, 8)]
    )
    frames.shown(frames.mark())
    assert limits == [helpers.SETTLE_LIMIT] and _counted(frames).seen == [8, 1, 2, 3, 4, 5, 6, 7, 8]


def _comparing(frames: '_Frames') -> list[tuple[Callable[[], bool], bool]]:
    """The renders' comparisons `frames` runs (_renders_alike): what each was given, recorded instead of run."""
    compared: list[tuple[Callable[[], bool], bool]] = []

    def alike(ended: Callable[[], bool], changed: bool = True) -> None:
        compared.append((ended, changed))

    vars(frames)['_renders_alike'] = alike
    return compared


def test_a_count_first_shown_once_the_view_has_drawn_is_read_from_then_on(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-162, measured: in a Designer opened hidden, the overlay's labels are empty until the 3D view first
    # draws, and a label read as a paint arrives shows the frame before's. _Frames, made before, decided once that no
    # count shows, and compared renders through the whole shot
    frames, limits = _frames_counting(helpers, True, [('Paint', None), *_paints(1, 2, 3, 4, 5, 6, 7, 8)], shows='')
    compared = _comparing(frames)
    frames.shown(frames.mark())
    assert compared == [] and frames._counts is not None, (compared, limits)
    assert _counted(frames).seen == [None, 1, 2, 3, 4, 5, 6, 7, 8]


def test_a_show_with_no_count_at_the_paint_after_the_views_first_frame_compares_renders(
    helpers: types.ModuleType,
) -> None:
    # Display > Samples off: the second paint reads the label of the first frame, which shows none (REVIEW.md HLP-162)
    frames, _ = _frames_counting(helpers, True, [('Paint', None)] * 3, shows='')
    compared = _comparing(frames)
    frames.shown(frames.mark())
    assert len(compared) == 1 and frames._painted == 2 and frames._counts is None, (compared, frames._painted)


def test_a_show_ends_once_the_window_goes_off_screen_again(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-163: shown()'s state ignored the window: off screen again meanwhile, it ran SETTLE_LIMIT, and the
    # shot went on with the window off screen (_Screen._bring brings it back)
    frames, _ = _frames_counting(helpers, True, [*_paints(8, 1), ('Off', 1), *_paints(2, 3)])
    frames.shown(frames.mark())
    assert _counted(frames).seen == [8, 1], _counted(frames).seen


@pytest.mark.parametrize(
    'coming, seen',
    [([('Off', 8), *_paints(1, 2)], []), ([*_paints(1), ('Off', 1), *_paints(1, 2)], [1])],
    ids=['before its restart', 'after its restart'],
)
def test_a_turns_wait_ends_once_the_window_goes_off_screen(
    helpers: types.ModuleType, coming: list[Event], seen: list[int]
) -> None:
    # REVIEW.md HLP-163: off screen nothing says the turn ended, and its waits ran NO_RESTART, then SETTLE_LIMIT. The
    # facts checks' turn looks again after it, which brings the window back (facts/state_file.py, _sf_framed)
    frames, _ = _frames_counting(helpers, True, coming)
    frames.moved(frames.mark())
    assert _counted(frames).seen == seen, _counted(frames).seen


@pytest.mark.parametrize('label', ['Render Time: 0.09 s', ''], ids=['Display > Samples off', 'never drawn'])
def test_with_no_count_shown_a_step_off_screen_takes_no_render_and_ends_once_the_view_asks_for_a_frame(
    helpers: types.ModuleType, label: str
) -> None:
    # REVIEW.md HLP-163: off screen each render is the view's last frame, so they are all alike, and each step's
    # comparison ran NO_RESTART; the view's UpdateRequest says it took the step, as where a count shows (HLP-158).
    # HLP-170: a view that never drew gives no render off screen, and the set-up raised after switching the mesh
    shown = SimpleNamespace(text=lambda: label)
    window = SimpleNamespace(isExposed=lambda: False, removeEventFilter=lambda spy: None)
    viewport = SimpleNamespace(
        findChildren=lambda kind: [shown], removeEventFilter=lambda spy: None, windowHandle=lambda: window
    )
    events: list[Callable[[str], None]] = []
    limits: list[float] = []
    states: list[tuple[bool, bool]] = []

    def event_signal(
        watched: SimpleNamespace, kinds: Sequence[str], seen: Callable[[str], None] | None = None
    ) -> SimpleNamespace:
        if seen is not None:
            events.append(seen)
        return SimpleNamespace(fired='its signal')

    def until(state: Callable[[], bool], limit: float, signals: Sequence[str] = ()) -> bool:
        # what the wait's state said before the UpdateRequest, then after it (REVIEW.md HLP-176: a state that ends at
        # once or never would pass on the limits alone)
        limits.append(limit)
        before = state()
        if not before:
            events[0]('UpdateRequest')
        states.append((before, state()))
        return state()

    def render() -> str:
        raise RuntimeError('the 3D view did not produce a render (is a material shown?)')

    vars(helpers)['_event_signal'] = event_signal
    vars(helpers)['_until'] = until
    frames = _frames(helpers, viewport, render)
    frames.settled(frames.mark())  # a step: ended by its UpdateRequest
    frames.moved(frames.mark())  # a turn: ends at once off screen, the look after it brings the window back
    assert limits == [helpers.NO_RESTART, helpers.NO_RESTART], limits
    assert states == [(False, True), (True, True)], states


def test_with_no_count_shown_a_step_whose_window_comes_on_screen_during_its_wait_compares_renders_there(
    helpers: types.ModuleType,
) -> None:
    # REVIEW.md HLP-176: the user shows Designer during a step's wait off screen, before its UpdateRequest. The wait's
    # state, an UpdateRequest off screen, could no longer hold: it ran its whole limit, then compared no render
    exposed = [False]
    done: list[str] = []
    renders = iter(['A', 'B', 'B'])
    label = SimpleNamespace(text=lambda: 'Render Time: 0.09 s')  # Display > Samples off
    window = SimpleNamespace(isExposed=lambda: exposed[0], removeEventFilter=lambda spy: None)
    viewport = SimpleNamespace(
        findChildren=lambda kind: [label], removeEventFilter=lambda spy: None, windowHandle=lambda: window
    )

    def until(state: Callable[[], bool], limit: float, signals: Sequence[str] = ()) -> bool:
        exposed[0] = True  # shown meanwhile: the window's expose event wakes the wait
        done.append('wait, ended %s' % state())
        return state()

    def render() -> str:
        done.append('render')
        return next(renders)

    vars(helpers)['_event_signal'] = lambda watched, kinds, seen=None: SimpleNamespace(fired='its signal')
    vars(helpers)['_until'] = until
    vars(helpers)['_settle'] = lambda seconds: done.append('poll')
    frames = _frames(helpers, viewport, render)
    frames.settled(frames.mark())
    assert done == ['wait, ended True', 'render', 'poll', 'render', 'poll', 'render'], done


def test_frames_dropped_without_close_go_at_once_with_their_filters(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-165: the viewport's spy held _Frames through its callback, and _Frames held the spy, a cycle freed
    # only when the cyclic collector runs: after an abort skipping close(), the viewport's Python filter ran at each
    # paint meanwhile
    import gc
    import weakref

    label = SimpleNamespace(text=lambda: 'Samples: 8')
    window = SimpleNamespace(isExposed=lambda: True, removeEventFilter=lambda spy: None)
    viewport = SimpleNamespace(
        findChildren=lambda kind: [label], removeEventFilter=lambda spy: None, windowHandle=lambda: window
    )

    class Spy:  # the filter, holding its callback, as the real one's class closes over it
        def __init__(self, seen: Callable[[str], None] | None) -> None:
            self.fired, self.seen = 'its signal', seen

    spies: list[weakref.ref[Spy]] = []

    def event_signal(watched: SimpleNamespace, kinds: Sequence[str], seen: Callable[[str], None] | None = None) -> Spy:
        spy = Spy(seen)
        spies.append(weakref.ref(spy))
        return spy

    vars(helpers)['_event_signal'] = event_signal
    gc.disable()
    try:
        frames = _frames(helpers, viewport, lambda: 'a render')
        gone = weakref.ref(frames)
        del frames
        assert gone() is None and [spy() for spy in spies] == [None, None]
    finally:
        gc.enable()
