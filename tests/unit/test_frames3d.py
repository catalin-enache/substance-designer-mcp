"""The 3D view's frames, read from its overlay's sample count at each paint (designer_helpers/frames3d.py; REVIEW.md
HLP-148): when a change shows, when the view has settled, when Designer shown again needed no new frames. And the
shot's waits: on the view's callbacks, polled every 100 ms only where none comes, never a fixed time (AGENTS.md). The
live self-test re-measures the counts (editor_panels_and_fit's frames fact)."""

import os
import re
import sys
import types
from collections.abc import Callable, Sequence
from types import SimpleNamespace
from typing import Protocol, cast
from unittest import mock

import pytest

from designer_helpers import HERE


@pytest.fixture
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    return faked_helpers


class Counts(Protocol):
    """_Counts, as these tests read it."""

    seen: list[int | None]

    def restart(self, since: int) -> int | None: ...

    def settled(self, since: int, off: bool = False) -> bool: ...

    def moved(self, since: int) -> bool: ...

    def unchanged(self, since: int) -> bool: ...

    def shown(self, since: int, asked: bool) -> bool: ...


class Frames(Protocol):
    """_Frames, as these tests read it (REVIEW.md TST-459)."""

    _counts: Counts | None
    _painted: int
    _renders_alike: Callable[..., object]

    def mark(self) -> tuple[int, int]: ...

    def settled(self, since: tuple[int, int]) -> None: ...

    def moved(self, since: tuple[int, int]) -> None: ...

    def shown(self, since: tuple[int, int]) -> None: ...

    def taking(self) -> Callable[[], bool]: ...

    def _event(self, kind: str) -> None: ...


def _counted(frames: Frames) -> Counts:
    """The counts `frames` read, once a count showed."""
    assert frames._counts is not None
    return frames._counts


def counts(helpers: types.ModuleType, *seen: int | None) -> Counts:
    """A _Counts with `seen` read at its paints."""
    read = cast(Counts, helpers._Counts())
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
    # and wheel step, 0.5 s before each retake, whatever the view did meanwhile. AGENTS.md: callbacks first, then a
    # poll every 100 ms where none exists, never a time measured here
    for part in ('shot3d', 'view3d', 'frames3d'):
        text = _source(part)
        assert not re.findall(r'_settle\(\s*(?!0\.1\b)[\w.]+\s*\)', text), part  # _tiling_spin's 100 ms polls stay
        assert 'time.sleep(' not in text, part
        for name in ('DRAW_WAIT', 'VIEW_TURN', 'DRAG_PAUSE', 'WHEEL_PAUSE'):
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
    # after a state (AGENTS.md)
    text = _source('frames3d')
    code = text[text.index('from .core') :]
    assert 'quiet' not in code and '_last' not in code  # the renders' own poll keeps its TICK


def test_one_name_for_the_3d_views_viewport_and_no_parameter_never_passed() -> None:
    # REVIEW.md HLP-156
    assert "className() == 'Alg::Gui3D::ViewportWidget'" not in _source('view3d')
    assert 'woken' not in _source('frames3d')


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

    def until(state: object, limit: float, signals: object = ()) -> bool:
        raise AssertionError('a wait')

    def render() -> str:
        done.append('render')
        return next(renders)

    vars(helpers)['_event_signal'] = lambda watched, kinds, seen=None: SimpleNamespace(fired='its signal')
    vars(helpers)['_until'] = until
    vars(helpers)['_settle'] = lambda seconds: done.append('poll %g' % seconds)
    frames = helpers._Frames(viewport, render)
    frames.settled(frames.mark())
    assert done == ['render', 'poll 0.1', 'render', 'poll 0.1', 'render', 'poll 0.1', 'render']


def _frames_seeing(helpers: types.ModuleType, exposed: bool, *coming: str) -> tuple[Frames, list[float]]:
    """A _Frames on a faked viewport whose window is `exposed` or not, and the limits its waits had: each wait sees the
    events `coming` (Paint, UpdateRequest) one by one, until its state holds."""
    label = SimpleNamespace(text=lambda: 'Samples: 8\nRender Time: 0.14 s')
    window = SimpleNamespace(isExposed=lambda: exposed, removeEventFilter=lambda spy: None)
    viewport = SimpleNamespace(
        findChildren=lambda kind: [label], removeEventFilter=lambda spy: None, windowHandle=lambda: window
    )
    seen: list[object] = []
    limits: list[float] = []

    def event_signal(watched: object, kinds: object, on: object = None) -> SimpleNamespace:
        if on is not None:  # the viewport's paints and UpdateRequests; the window's expose events have none
            seen.append(on)
        return SimpleNamespace(fired='its signal')

    def until(state: object, limit: float, signals: object = ()) -> bool:
        limits.append(limit)
        check = cast(Callable[[], bool], state)
        for kind in coming:
            if check():
                break
            cast(Callable[[str], None], seen[0])(kind)
        return check()

    vars(helpers)['_event_signal'] = event_signal
    vars(helpers)['_until'] = until
    return cast(Frames, helpers._Frames(viewport, lambda: 'a render')), limits


@pytest.mark.parametrize(
    'exposed, coming, taken',
    [
        (True, ('Paint',), True),
        (True, ('UpdateRequest',), False),  # asked for, not drawn yet
        (False, ('UpdateRequest',), True),
        (False, (), False),
    ],
    ids=['on screen, drawn', 'on screen, only asked for', 'off screen, asked for', 'off screen, nothing'],
)
def test_a_move_is_taken_once_the_view_draws_on_screen_or_asks_for_a_frame_off_screen(
    helpers: types.ModuleType, exposed: bool, coming: tuple[str, ...], taken: bool
) -> None:
    # REVIEW.md HLP-149: off screen the view draws no frame, and next_frame returned at once, so drags and wheel steps
    # went back to back, and some were lost. Measured hidden: each drag is followed by one UpdateRequest, and drags
    # sent each after it came out as drags 0.2 s apart (the frames fact re-measures it)
    frames, limits = _frames_seeing(helpers, exposed, *coming)
    assert frames.taking()() is taken
    assert limits == [helpers.NO_RESTART]


def _frames_counting(
    helpers: types.ModuleType, exposed: bool, coming: Sequence[tuple[str, int | None]], shows: str = 'Samples: 8'
) -> tuple[Frames, list[float]]:
    """A _Frames whose overlay reads `shows` as it is made, on a faked viewport `exposed` or not, and the limits its
    waits had: the events `coming` (kind, the count the overlay shows as it comes, None for none) are given one by one
    while a wait's state doesn't hold. An 'Off' takes the window off screen, as covering it does."""
    shown = [shows]
    on_screen = [exposed]
    label = SimpleNamespace(text=lambda: shown[0])
    window = SimpleNamespace(isExposed=lambda: on_screen[0], removeEventFilter=lambda spy: None)
    viewport = SimpleNamespace(
        findChildren=lambda kind: [label], removeEventFilter=lambda spy: None, windowHandle=lambda: window
    )
    seen: list[Callable[[str], None]] = []
    limits: list[float] = []
    left = list(coming)

    def event_signal(watched: object, kinds: object, on: Callable[[str], None] | None = None) -> SimpleNamespace:
        if on is not None:  # the viewport's paints and UpdateRequests; the window's expose events have none
            seen.append(on)
        return SimpleNamespace(fired='its signal')

    def until(state: Callable[[], bool], limit: float, signals: object = ()) -> bool:
        limits.append(limit)
        while left and not state():
            kind, count = left.pop(0)
            if kind == 'Off':
                on_screen[0] = False
                continue
            shown[0] = '' if count is None else 'Samples: %d' % count
            seen[0](kind)
        return state()

    vars(helpers)['_event_signal'] = event_signal
    vars(helpers)['_until'] = until
    return cast(Frames, helpers._Frames(viewport, lambda: 'a render')), limits


def _paints(*counts: int) -> list[tuple[str, int]]:
    return [('Paint', n) for n in counts]


def test_a_step_waits_for_its_restart_then_for_the_count_back(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-428: _Frames' waits were tested only through _Counts
    frames, limits = _frames_counting(helpers, True, _paints(8, 1, 2, 3, 4, 5, 6, 7, 8))
    frames.settled(frames.mark())
    assert limits == [helpers.NO_RESTART, helpers.SETTLE_LIMIT]
    assert _counted(frames).settled(0)


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
    # one 0.06 s after it, a tiling one 0.71 s into set_3d_view)
    frames, limits = _frames_counting(helpers, False, [('UpdateRequest', 8)])
    looked = helpers._until
    held: list[bool] = []

    def until(state: Callable[[], bool], limit: float, signals: object = ()) -> bool:
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
    watched: list[tuple[object, tuple[str, ...]]] = []
    woken: list[list[object]] = []

    def event_signal(on: object, kinds: tuple[str, ...], seen: object = None) -> SimpleNamespace:
        watched.append((on, tuple(kinds)))
        return SimpleNamespace(fired=tuple(kinds))

    def until(state: object, limit: float, signals: object = ()) -> bool:
        woken.append(list(cast(list[object], signals)))
        return True

    vars(helpers)['_event_signal'] = event_signal
    vars(helpers)['_until'] = until
    frames = helpers._Frames(viewport, lambda: 'a render')
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
    coming = [('Paint', 8), ('UpdateRequest', 8), *_paints(1, 2, 3, 4, 5, 6, 7, 8)]
    frames, limits = _frames_counting(helpers, True, coming)
    frames.shown(frames.mark())
    assert limits == [helpers.SETTLE_LIMIT] and _counted(frames).seen == [8, 1, 2, 3, 4, 5, 6, 7, 8]


def _comparing(frames: Frames) -> list[object]:
    """The renders' comparisons `frames` runs (_renders_alike), recorded instead of run."""
    compared: list[object] = []
    frames._renders_alike = lambda *args, **kw: compared.append((args, kw))
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
    helpers: types.ModuleType, coming: list[tuple[str, int]], seen: list[int]
) -> None:
    # REVIEW.md HLP-163: off screen nothing says the turn ended, and its waits ran NO_RESTART, then SETTLE_LIMIT. The
    # set-up looks again after the turn, which brings the window back and waits for the view there (view3d.py)
    frames, _ = _frames_counting(helpers, True, coming)
    frames.moved(frames.mark())
    assert _counted(frames).seen == seen, _counted(frames).seen


@pytest.mark.parametrize('label', ['Render Time: 0.09 s', ''], ids=['Display > Samples off', 'never drawn'])
def test_with_no_count_shown_a_step_off_screen_takes_no_render_and_ends_once_the_view_asks_for_a_frame(
    helpers: types.ModuleType, label: str
) -> None:
    # REVIEW.md HLP-163: off screen each render is the view's last frame, so they are all alike, and each step's
    # comparison ran NO_RESTART; the view's UpdateRequest says it took the step, as where a count shows (HLP-158).
    # HLP-170: a view that never drew gives no render off screen, and set_3d_view raised after switching the mesh
    shown = SimpleNamespace(text=lambda: label)
    window = SimpleNamespace(isExposed=lambda: False, removeEventFilter=lambda spy: None)
    viewport = SimpleNamespace(
        findChildren=lambda kind: [shown], removeEventFilter=lambda spy: None, windowHandle=lambda: window
    )
    events: list[Callable[[str], None]] = []
    limits: list[float] = []
    states: list[tuple[bool, bool]] = []

    def event_signal(watched: object, kinds: object, seen: Callable[[str], None] | None = None) -> SimpleNamespace:
        if seen is not None:
            events.append(seen)
        return SimpleNamespace(fired='its signal')

    def until(state: Callable[[], bool], limit: float, signals: object = ()) -> bool:
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
    frames = helpers._Frames(viewport, render)
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

    def until(state: Callable[[], bool], limit: float, signals: object = ()) -> bool:
        exposed[0] = True  # shown meanwhile: the window's expose event wakes the wait
        done.append('wait, ended %s' % state())
        return state()

    def render() -> str:
        done.append('render')
        return next(renders)

    vars(helpers)['_event_signal'] = lambda watched, kinds, seen=None: SimpleNamespace(fired='its signal')
    vars(helpers)['_until'] = until
    vars(helpers)['_settle'] = lambda seconds: done.append('poll')
    frames = helpers._Frames(viewport, render)
    frames.settled(frames.mark())
    assert done == ['wait, ended True', 'render', 'poll', 'render', 'poll', 'render'], done


def test_a_moves_update_request_delivered_before_its_wait_began_ends_the_wait(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-164, measured: off screen the view asks for a frame once a move. Delivered while the move's own
    # events ran, it came before a mark taken as the wait began, and the wait ran NO_RESTART: the first of 60 moves
    frames, _ = _frames_seeing(helpers, False)  # nothing comes during the wait
    taken = frames.taking()
    frames._event('UpdateRequest')  # as the move's events ran
    assert taken() is True


def test_on_screen_a_frame_drawn_while_a_moves_events_ran_doesnt_end_its_wait(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-164's fix, measured in its scratch run: counted from before the move, a frame of the accumulation
    # going on, drawn as the move's events ran, ended the wait, and zoom=-3 lost one of its wheel steps
    frames, _ = _frames_seeing(helpers, True)  # nothing comes during the wait
    taken = frames.taking()
    frames._event('Paint')  # as the move's events ran
    assert taken() is False


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
        def __init__(self, seen: object) -> None:
            self.fired, self.seen = 'its signal', seen

    spies: list[weakref.ref[Spy]] = []

    def event_signal(watched: object, kinds: object, seen: object = None) -> Spy:
        spy = Spy(seen)
        spies.append(weakref.ref(spy))
        return spy

    vars(helpers)['_event_signal'] = event_signal
    gc.disable()
    try:
        frames = helpers._Frames(viewport, lambda: 'a render')
        gone = weakref.ref(frames)
        del frames
        assert gone() is None and [spy() for spy in spies] == [None, None]
    finally:
        gc.enable()
