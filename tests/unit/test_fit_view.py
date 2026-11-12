"""_fit_view_to (designer_helpers): what it reports when the zoom can't reach the area, with a fake view
(REVIEW.md HLP-56). Designer's own smallest zoom is checked live (editor_open_and_zoom/checks.py)."""

import sys
import types
from typing import Any, cast
from unittest import mock

import pytest


class Rect:
    def __init__(self, x: float, y: float, w: float, h: float) -> None:
        self.x, self.y, self.w, self.h = x, y, w, h

    def width(self) -> float:
        return self.w

    def height(self) -> float:
        return self.h

    def center(self) -> None:
        return None

    def left(self) -> float:
        return self.x

    def top(self) -> float:
        return self.y

    def right(self) -> float:
        return self.x + self.w

    def bottom(self) -> float:
        return self.y + self.h


def fit(
    faked_helpers: types.ModuleType,
    capsys: pytest.CaptureFixture[str],
    zoom: float,
    step: float,
    seen: tuple[float, float, float, float] = (0, 0, 10, 10),
) -> str:
    """The output of a fit of a 1000-wide area (with padding, 100 % would be 700 / 1140 or so) in a view at `zoom`,
    each wheel notch multiplying the zoom by `step` in or dividing by it out (1: the view ignores them)."""
    module = faked_helpers
    fake = cast(mock.MagicMock, sys.modules['PySide6'])  # the one fake every sd and PySide6 module is (conftest)
    fake.QRectF = Rect
    state = {'zoom': zoom}
    view = mock.MagicMock()
    view.transform.return_value.m11.side_effect = lambda: state['zoom']
    view.viewport.return_value.width.return_value = 700
    view.viewport.return_value.height.return_value = 500
    view.mapToScene.return_value.boundingRect.return_value = Rect(*seen)

    def wheel(_: Any, notches: int) -> None:
        state['zoom'] *= step**notches

    vars(module)['_wheel_zoom'] = wheel
    vars(module)['_graph_view'] = lambda mw: view
    vars(module)['_same_graph'] = lambda a, b: True
    vars(module)['_current_graph'] = lambda: None
    vars(module)['_process_events'] = lambda n=10: None
    vars(module)['_fit_area'] = lambda g, n, f, r: (0.0, 0.0, 1000.0, 1000.0, 'rect')
    fake.QApplication.activeWindow.return_value = None
    module._fit_view_to(mock.MagicMock())
    return capsys.readouterr().out


def test_a_working_wheel_fits(faked_helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    out = fit(faked_helpers, capsys, 1.0, 1.2, seen=(-500, -500, 2000, 2000))
    assert out.startswith('fitted rect: zoom ') and 'could not' not in out


def test_a_view_ignoring_the_wheel_isnt_reported_as_fitted(
    faked_helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # seen once in a self-test run: "fitted rect: zoom 383%" with a cap of 100 %, the area out of view
    out = fit(faked_helpers, capsys, 3.83, 1.0)
    assert out.startswith('could not fit rect') and 'fitted' not in out and 'zoom 383%' in out
    assert '700x500' in out and 'active' in out  # what a later occurrence needs to explain itself


def test_a_view_ignoring_the_wheel_but_already_small_enough_fits(
    faked_helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    out = fit(faked_helpers, capsys, 0.2, 1.0, seen=(-500, -500, 4000, 4000))
    assert out.startswith('fitted rect: zoom 20%')


def test_an_area_in_view_at_the_smallest_zoom_is_fitted_though_its_padding_isnt(
    faked_helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-59: compared with the padded area, this said "could not fit" with the whole area in view.
    # 700x500 at 48 %: 1458 x 1041 units in view, the 1000 x 1000 area inside them, its padded 1140 not
    out = fit(faked_helpers, capsys, 0.48, 1.0, seen=(-229, -20, 1458, 1041))
    assert out.startswith('fitted rect: zoom 48%') and 'could not' not in out


def test_an_area_in_view_with_the_zoom_stuck_above_the_cap_says_so(
    faked_helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # the docstring promises at most 100 %: the area is in view, but the wheel steps did nothing (HLP-59)
    out = fit(faked_helpers, capsys, 3.83, 1.0, seen=(-50, -50, 1100, 1100))
    assert out.startswith('fitted rect, above 100 % (the view ignored the zoom steps;') and 'zoom 383%' in out
    assert '700x500' in out and 'active' in out
