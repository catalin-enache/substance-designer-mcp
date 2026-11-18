"""What the 3D view checks measure in a render (editor_panels_and_fit/renders.py), on made-up images."""

import asyncio
import base64
import io
import math
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest
from PIL import Image as PILImage
from selftest_fakes import FakeCall, fresh, tool_result

from project_constants import Json, ToolArgs

BACKGROUND = 33.0


def _checker(
    squares: int, size: int = 80, left: int = 10, width: int = 48
) -> 'np.ndarray[tuple[int, int], np.dtype[np.float64]]':
    """A dark background with a plane `width` columns wide from `left`, a checker of `squares` per side on it."""
    a = np.full((size, size), BACKGROUND)
    cell = width / squares
    for y in range(left, left + width):
        for x in range(left, left + width):
            a[y, x] = 220.0 if (int((x - left) / cell) + int((y - left) / cell)) % 2 else 20.0
    return a


@pytest.fixture
def renders() -> ModuleType:
    return fresh('editor_panels_and_fit.renders')


def test_the_planes_width_is_what_differs_from_the_background(renders: ModuleType) -> None:
    assert renders.plane_width(_checker(8)) == 48
    assert renders.plane_width(np.full((20, 20), BACKGROUND)) == 0


def test_the_planes_height_is_measured_on_the_rows(renders: ModuleType) -> None:
    a = np.full((80, 80), BACKGROUND)
    a[10:30, 5:65] = 200.0  # 60 wide, 20 high: a plane seen at a slant
    assert (renders.plane_width(a), renders.plane_height(a)) == (60, 20)


def test_a_checker_twice_as_fine_has_about_twice_the_transitions(renders: ModuleType) -> None:
    coarse, fine = renders.transitions(_checker(8)), renders.transitions(_checker(16))
    assert coarse == 7 and fine == 15


def test_a_middle_row_on_the_edge_between_two_rows_of_squares_still_counts_the_checker(renders: ModuleType) -> None:
    # REVIEW.md TST-395: a render blends the two rows of squares into one grey along their edge (a 442x345 render's
    # middle row read 160 to 171 grey levels there, the rows around it 15 transitions)
    a = _checker(8)
    a[40, 10:58] = 165.0
    assert renders.transitions(a) == 7


def _plane_at(left: int, width: int = 850, plane: int = 250) -> 'np.ndarray[tuple[int, int], np.dtype[np.float64]]':
    a = np.full((300, width), BACKGROUND)
    a[50:250, left : left + plane] = 200.0
    return a


def test_a_planes_move_is_measured_as_a_fraction_of_each_renders_width(renders: ModuleType) -> None:
    # REVIEW.md TST-396: a tool's shot is shrunk to max_size, a render saved by shoot_3d isn't; a quarter of an 850
    # pixel render measured 0.196 against a shot shrunk to 700
    before, after = _plane_at(300), _plane_at(300 - 212)  # moved a quarter of 850 left
    shot = PILImage.fromarray(before.astype(np.uint8))
    shot.thumbnail((700, 700))
    small = np.asarray(shot, dtype=float)
    assert renders.moved_left(before, after) == pytest.approx(0.25, abs=0.002)
    assert renders.moved_left(small, after) == pytest.approx(0.25, abs=0.005)


def test_shading_on_a_plain_plane_is_no_pattern(renders: ModuleType) -> None:
    a = np.full((40, 40), BACKGROUND)
    a[5:35, 5:35] = 170.0 + np.tile(np.arange(30) % 3, (30, 1))  # a few levels of noise
    assert renders.transitions(a) == 0


def test_grey_reads_the_image_of_a_tool_result(renders: ModuleType) -> None:
    buf = io.BytesIO()
    PILImage.fromarray(_checker(8).astype(np.uint8)).save(buf, format='PNG')
    result = SimpleNamespace(content=[SimpleNamespace(type='image', data=base64.b64encode(buf.getvalue()).decode())])
    assert renders.plane_width(renders.grey(result)) == 48


def test_the_difference_of_two_renders(renders: ModuleType) -> None:
    a = _checker(8)
    assert renders.difference(a, a.copy()) == 0.0
    assert renders.difference(a, _checker(16)) > 20
    # two sizes: NaN, which no comparison passes (REVIEW.md TST-540: 255 passed every "the render changed"; TST-544: a
    # value from 2 to 3 passed the test's own comparisons)
    assert math.isnan(renders.difference(a, a[:-1]))


def _shot(a: 'np.ndarray[tuple[int, int], np.dtype[np.float64]]') -> SimpleNamespace:  # a CallToolResult
    """A screenshot_designer result holding the image `a`."""
    buf = io.BytesIO()
    PILImage.fromarray(a.astype(np.uint8)).save(buf, format='PNG')
    return SimpleNamespace(
        content=[SimpleNamespace(type='image', data=base64.b64encode(buf.getvalue()).decode())], is_error=False
    )


def test_a_failed_shot_is_said_whole_on_a_line_of_its_own(
    renders: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-334: a check's detail is cut at 150 characters, which hid why a shot failed
    error = 'Error executing tool screenshot_designer: RuntimeError: ' + 'why it failed, ' * 20
    failed = tool_result(error + '\nits last line', error=True)
    renders.say_failed('the set-up check', _shot(_checker(8)), failed)
    assert capsys.readouterr().out == '      the set-up check: shot 2 of 2 failed: %s / its last line\n' % error.strip()


def test_two_shots_of_two_sizes_are_said(renders: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    # the other way difference() says two sizes: it gives NaN
    renders.say_failed('the set-up check', _shot(_checker(8)), _shot(_checker(8)[:-1]))
    assert capsys.readouterr().out == '      the set-up check: the shots are of two sizes: 80x80, 80x79 px\n'


def test_shots_that_worked_say_nothing(renders: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    renders.say_failed('the set-up check', _shot(_checker(8)), _shot(_checker(16)))
    assert capsys.readouterr().out == ''


def _plain(size: int = 80) -> 'np.ndarray[tuple[int, int], np.dtype[np.float64]]':
    """The plane with nothing on it: the 3D view before a graph's material shows on the mesh."""
    a = np.full((size, size), BACKGROUND)
    a[10:58, 10:58] = 150.0
    return a


def _said(shot: SimpleNamespace, line: str) -> SimpleNamespace:
    """`shot` with `line` as its text, after its image, as screenshot_designer gives what it set."""
    shot.content.append(SimpleNamespace(type='text', text=line))
    return shot


Calls = list[tuple[str, ToolArgs | None]]


def _shots_in_turn(
    monkeypatch: pytest.MonkeyPatch, shots: list[SimpleNamespace]
) -> tuple[FakeCall, Calls, list[float]]:
    """A fake tool call giving `shots` in turn, the last again once they run out, the calls it got, and the pauses
    asked of asyncio.sleep, which returns at once."""
    calls: Calls = []
    pauses: list[float] = []

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        calls.append((name, args))
        return shots.pop(0) if len(shots) > 1 else shots[0]

    async def no_pause(seconds: float) -> None:
        pauses.append(seconds)

    # setitem: PyCharm can't resolve 'sleep' through asyncio's star re-export of asyncio.tasks (AGENTS.md, PyCharm)
    monkeypatch.setitem(vars(asyncio), 'sleep', no_pause)
    return c, calls, pauses


ARGS: dict[str, Json] = {'panel': '3d', 'max_size': 700, 'mesh': 'Rounded cube', 'graph': 'g', 'view': 'Front'}


def test_a_shot_is_taken_again_until_the_checker_shows_on_the_mesh(
    renders: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-383, TST-388: in a full run the 3D shots once didn't follow the camera for about 20 s, the cause
    # unknown. TST-421: retaken a second apart, so that the retakes last (TST-386); now as each shot returns, each
    # waiting for the 3D view itself (frames3d.py), until RETAKE_S have passed
    c, calls, pauses = _shots_in_turn(monkeypatch, [_shot(_plain()), _shot(_plain()), _shot(_checker(8))])
    r = asyncio.run(renders.with_checker(c, ARGS))
    assert renders.transitions(renders.grey(r)) >= renders.CHECKER and pauses == []
    assert calls == [('screenshot_designer', ARGS)] + [('screenshot_designer', {'panel': '3d', 'max_size': 700})] * 2
    assert 'the checker showed on the mesh after 2 retakes' in capsys.readouterr().out


def test_a_retaken_shot_keeps_the_text_of_what_the_call_set(
    renders: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md TST-384: a retake says nothing of what was set, and two checks read it
    first = _said(_shot(_plain()), "3D view: Plane, graph g's outputs on the mesh, view Top, framed")
    c, _calls, _pauses = _shots_in_turn(monkeypatch, [first, _said(_shot(_checker(8)), '')])
    r = asyncio.run(renders.with_checker(c, ARGS))
    assert renders.transitions(renders.grey(r)) >= renders.CHECKER
    assert renders.text(r).strip() == "3D view: Plane, graph g's outputs on the mesh, view Top, framed"


def test_a_shot_with_the_checker_at_once_is_taken_once(
    renders: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    edge = _shot(_checker(7))  # exactly CHECKER changes: the checker shows (TST-386)
    assert renders.transitions(renders.grey(edge)) == renders.CHECKER
    for shot in (_shot(_checker(8)), edge):
        c, calls, pauses = _shots_in_turn(monkeypatch, [shot])
        asyncio.run(renders.with_checker(c, ARGS))
        assert calls == [('screenshot_designer', ARGS)] and pauses == [] and capsys.readouterr().out == ''


def test_a_shot_waits_for_the_checker_only_so_long(
    renders: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    c, calls, _pauses = _shots_in_turn(monkeypatch, [_shot(_plain())])
    now = [0.0]

    async def a_second_a_shot(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        now[0] += 1.0
        return await c(name, args)

    monkeypatch.setitem(vars(renders), '_now', lambda: now[0])
    r = asyncio.run(renders.with_checker(a_second_a_shot, ARGS))
    assert renders.transitions(renders.grey(r)) == 0 and len(calls) == renders.RETAKE_S  # the first, then retakes
    retakes = renders.RETAKE_S - 1
    assert "the checker didn't show on the mesh after %d retakes" % retakes in capsys.readouterr().out


def test_a_shot_that_failed_isnt_taken_again(renders: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    failed = tool_result('Error executing tool', error=True)
    c, calls, _pauses = _shots_in_turn(monkeypatch, [failed])
    assert asyncio.run(renders.with_checker(c, ARGS)) is failed and len(calls) == 1
