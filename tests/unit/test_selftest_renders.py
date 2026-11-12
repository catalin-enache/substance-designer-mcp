"""What the 3D view checks measure in a render (editor_panels_and_fit/renders.py), on made-up images."""

import base64
import io
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from PIL import Image as PILImage
from selftest_fakes import fresh

BACKGROUND = 33.0


def _checker(squares: int, size: int = 80, left: int = 10, width: int = 48) -> Any:
    """A dark background with a plane `width` columns wide from `left`, a checker of `squares` per side on it."""
    a = np.full((size, size), BACKGROUND)
    cell = width / squares
    for y in range(left, left + width):
        for x in range(left, left + width):
            a[y, x] = 220.0 if (int((x - left) / cell) + int((y - left) / cell)) % 2 else 20.0
    return a


@pytest.fixture
def renders() -> Any:
    return fresh('editor_panels_and_fit.renders')


def test_the_planes_width_is_what_differs_from_the_background(renders: Any) -> None:
    assert renders.plane_width(_checker(8)) == 48
    assert renders.plane_width(np.full((20, 20), BACKGROUND)) == 0


def test_the_planes_height_is_measured_on_the_rows(renders: Any) -> None:
    a = np.full((80, 80), BACKGROUND)
    a[10:30, 5:65] = 200.0  # 60 wide, 20 high: a plane seen at a slant
    assert (renders.plane_width(a), renders.plane_height(a)) == (60, 20)


def test_a_checker_twice_as_fine_has_about_twice_the_transitions(renders: Any) -> None:
    coarse, fine = renders.transitions(_checker(8)), renders.transitions(_checker(16))
    assert coarse == 7 and fine == 15


def test_shading_on_a_plain_plane_is_no_pattern(renders: Any) -> None:
    a = np.full((40, 40), BACKGROUND)
    a[5:35, 5:35] = 170.0 + np.tile(np.arange(30) % 3, (30, 1))  # a few levels of noise
    assert renders.transitions(a) == 0


def test_grey_reads_the_image_of_a_tool_result(renders: Any) -> None:
    buf = io.BytesIO()
    PILImage.fromarray(_checker(8).astype(np.uint8)).save(buf, format='PNG')
    result = SimpleNamespace(content=[SimpleNamespace(type='image', data=base64.b64encode(buf.getvalue()).decode())])
    assert renders.plane_width(renders.grey(result)) == 48


def test_the_difference_of_two_renders(renders: Any) -> None:
    a = _checker(8)
    assert renders.difference(a, a.copy()) == 0.0
    assert renders.difference(a, _checker(16)) > 20
    assert renders.difference(a, a[:-1]) == 255.0


def _shot(a: Any) -> Any:
    """A screenshot_designer result holding the image `a`."""
    buf = io.BytesIO()
    PILImage.fromarray(a.astype(np.uint8)).save(buf, format='PNG')
    return SimpleNamespace(
        content=[SimpleNamespace(type='image', data=base64.b64encode(buf.getvalue()).decode())], is_error=False
    )


def test_a_failed_shot_is_said_whole_on_a_line_of_its_own(renders: Any, capsys: pytest.CaptureFixture[str]) -> None:
    # REVIEW.md TST-334: a check's detail is cut at 150 characters, which hid why a shot failed
    error = 'Error executing tool screenshot_designer: RuntimeError: ' + 'why it failed, ' * 20
    failed = SimpleNamespace(content=[SimpleNamespace(type='text', text=error + '\nits last line')], is_error=True)
    renders.say_failed('the set-up check', _shot(_checker(8)), failed)
    assert capsys.readouterr().out == '      the set-up check: shot 2 of 2 failed: %s / its last line\n' % error.strip()


def test_two_shots_of_two_sizes_are_said(renders: Any, capsys: pytest.CaptureFixture[str]) -> None:
    # the other way difference() gives 255.0
    renders.say_failed('the set-up check', _shot(_checker(8)), _shot(_checker(8)[:-1]))
    assert capsys.readouterr().out == '      the set-up check: the shots are of two sizes: 80x80, 80x79 px\n'


def test_shots_that_worked_say_nothing(renders: Any, capsys: pytest.CaptureFixture[str]) -> None:
    renders.say_failed('the set-up check', _shot(_checker(8)), _shot(_checker(16)))
    assert capsys.readouterr().out == ''
