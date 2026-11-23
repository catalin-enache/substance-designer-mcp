"""analyze_reference's result read, for the tests of the palette and of the reading of image files (test_reference.py,
test_image_reading.py): one of its lines, its keys, and the keys checked against the colours wanted."""

import json

import pytest
from image_files import RGB8


def result_line(text: str, start: str) -> str:
    """The one line of the result `text` that starts with `start`."""
    found = [line for line in text.splitlines() if line.startswith(start)]
    assert len(found) == 1, (start, text)
    return found[0]


def result_keys(text: str) -> list[tuple[float, list[float]]]:
    """The keys of the result's gradientrgba line, as set takes them: each its position and its colour's numbers,
    checked to be so before they are given typed (REVIEW.md TST-789)."""
    parsed: object = json.loads(result_line(text, 'gradientrgba: ').split(': ', 1)[1])
    assert isinstance(parsed, list), parsed
    keys = []
    for key in parsed:
        assert isinstance(key, list) and len(key) == 2, key
        position, colour = key
        assert isinstance(position, int | float) and isinstance(colour, list), key
        assert all(isinstance(value, int | float) for value in colour), key
        keys.append((float(position), [float(value) for value in colour]))
    return keys


def assert_keys(text: str, expected: list[tuple[float, RGB8]], within: float = 1e-4) -> None:
    """The result's keys are these positions and 8-bit colours, alpha 1, to the 4 decimals it prints, or `within`
    (a JPEG's colours are within a step or two)."""
    keys = result_keys(text)
    assert len(keys) == len(expected), text
    for (position, colour), (want_position, want_colour) in zip(keys, expected, strict=True):
        assert position == pytest.approx(want_position, abs=1e-4), text
        assert colour == pytest.approx([*(c / 255 for c in want_colour), 1], abs=within), text
