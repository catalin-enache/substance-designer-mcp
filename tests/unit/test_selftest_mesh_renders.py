"""What facts' checks of mesh files measure in a render (facts/mesh_renders.py), on made-up images (REVIEW.md
TST-990)."""

import math
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
from image_files import RGB8, png
from selftest_fakes import fresh

BACKGROUND = (33, 33, 33)  # the 3D view's dark background
RED, BLUE = (204, 51, 51), (51, 51, 204)  # the project's OBJ's two materials, as its .mtl gives them


@pytest.fixture
def renders() -> ModuleType:
    return fresh('facts.mesh_renders')


def saved(tmp_path: Path, name: str, size: tuple[int, int], boxes: list[tuple[int, int, int, int, RGB8]]) -> str:
    """A render of `size` (width, height) on the background, each box (x0, y0, x1, y1, colour) drawn on it; its path."""
    a = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    a[:, :] = BACKGROUND
    for x0, y0, x1, y1, colour in boxes:
        a[y0:y1, x0:x1] = colour
    return png(tmp_path / (name + '.png'), a)


def test_a_mesh_shown_is_the_share_of_pixels_off_the_background(renders: ModuleType, tmp_path: Path) -> None:
    empty = saved(tmp_path, 'empty', (20, 10), [])
    mesh = saved(tmp_path, 'mesh', (20, 10), [(0, 5, 10, 10, (200, 200, 200))])  # a quarter of the pixels
    # below the top-left pixel, the background's: 24 levels from it, uncounted, and 26, counted (REVIEW.md TST-994)
    faint = saved(tmp_path, 'faint', (20, 10), [(0, 5, 20, 10, (57, 57, 57))])
    just_over = saved(tmp_path, 'just_over', (20, 10), [(0, 5, 20, 10, (59, 59, 59))])
    assert (renders.shown(empty), renders.shown(mesh), renders.shown(faint)) == (0.0, 0.25, 0.0)
    assert renders.shown(just_over) == 0.5


def test_the_two_materials_are_the_shares_of_red_and_of_blue_pixels(renders: ModuleType, tmp_path: Path) -> None:
    both = saved(tmp_path, 'both', (10, 10), [(0, 0, 5, 10, RED), (5, 0, 7, 10, BLUE), (7, 0, 10, 10, (128, 128, 128))])
    assert renders.coloured(both) == (0.5, 0.2)
    grey = saved(tmp_path, 'grey', (10, 10), [(0, 0, 10, 10, (180, 150, 130))])  # red above blue by 50, under COLOURED
    assert renders.coloured(grey) == (0.0, 0.0)


def test_two_renders_are_apart_by_their_mean_grey_difference_and_of_two_sizes_by_nothing(
    renders: ModuleType, tmp_path: Path
) -> None:
    one = saved(tmp_path, 'one', (10, 10), [])
    two = saved(tmp_path, 'two', (10, 10), [(0, 0, 5, 10, (133, 133, 133))])  # half the pixels 100 levels lighter
    other = saved(tmp_path, 'other', (12, 10), [])
    assert renders.apart(one, one) == 0.0 and renders.apart(one, two) == 50.0
    assert math.isnan(renders.apart(one, other))  # no comparison holds: neither apart nor alike (REVIEW.md TST-540)
