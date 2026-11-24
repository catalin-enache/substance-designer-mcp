import json
import os

import numpy as np
import numpy.typing as npt
import pytest
from PIL import ImageDraw

from conftest import fake_bridge, server
from project_constants import Json
from server_tools import measure
from server_tools.measure import Pixels, PixelType


def _buffer(
    values: npt.ArrayLike, dtype: npt.DTypeLike, width: int, height: int, channels: int, padding: int
) -> tuple[bytes, int]:
    """Raw bytes like Designer's texture buffer: rows of pixels plus `padding` bytes per row."""
    rows = np.asarray(values, dtype=dtype).reshape(height, width * channels).view(np.uint8)
    pad = np.full((height, padding), 0xAB, dtype=np.uint8)
    return np.hstack([rows, pad]).tobytes(), rows.shape[1] + padding


@pytest.mark.parametrize(
    'fmt, dtype, scale',
    [('RGBA8', np.uint8, 255), ('RGBA16', np.uint16, 65535), ('RGBA16F', np.float16, 1), ('RGBA32F', np.float32, 1)],
)
def test_decode_rgba_skips_row_padding(fmt: str, dtype: PixelType, scale: int) -> None:
    w, h = 3, 2
    values = (np.arange(w * h * 4) * (scale // 30 if scale > 1 else 0.03)).astype(dtype)
    raw, pitch = _buffer(values, dtype, w, h, 4, padding=8)
    bpp = 4 * np.dtype(dtype).itemsize
    data, layout = server._decode_pixels(raw, {'format': fmt, 'width': w, 'height': h, 'pitch': pitch, 'bpp': bpp})
    assert layout == 'RGBA' and data.shape == (h, w, 4)
    np.testing.assert_allclose(data.ravel(), values.astype(np.float64) / scale, rtol=1e-6)


def test_decode_lum16() -> None:
    raw, pitch = _buffer([0, 65535, 32768, 1000], np.uint16, 2, 2, 1, padding=4)
    data, layout = server._decode_pixels(raw, {'format': 'LUM16', 'width': 2, 'height': 2, 'pitch': pitch, 'bpp': 2})
    assert layout == 'L' and data.shape == (2, 2, 1)
    np.testing.assert_allclose(data[:, :, 0], [[0.0, 1.0], [32768 / 65535, 1000 / 65535]])


def test_decode_unknown_format() -> None:
    with pytest.raises(server.ToolError, match='unsupported pixel format'):
        server._decode_pixels(b'\0' * 16, {'format': 'RGBA12', 'width': 1, 'height': 1, 'pitch': 16, 'bpp': 6})


def _seam(data: Pixels, axis_name: str) -> str:
    report = measure._seam_report(data, axis_name, 1 if axis_name == 'horizontal' else 0)
    return report


def test_seam_periodic_pattern_tiles() -> None:
    # triangle wave, one period across the width: every step (seam included) is the same size.
    # (A sine scores ~1.58 when its steepest part sits on the seam; see ROADMAP.)
    wave = 1 - np.abs(np.arange(64) - 32) / 32
    data = np.tile(wave, (32, 1))[:, :, None]
    report = _seam(data, 'horizontal')
    assert report.startswith('Horizontal tiling (left/right edges)') and '(ratio 1.00)' in report
    assert 'tiles seamlessly' in report


def test_seam_ramp_has_visible_seam_at_worst_row() -> None:
    data = np.tile(np.linspace(0, 1, 64), (32, 1))[:, :, None].copy()
    data[7, 0] = -1.0  # make row 7 the worst
    report = _seam(data, 'horizontal')
    assert 'VISIBLE SEAM' in report and 'at row 7' in report


def test_seam_vertical_axis() -> None:
    data = np.tile(np.linspace(0, 1, 16)[:, None], (1, 8))[:, :, None]  # ramp top to bottom
    assert 'VISIBLE SEAM' in _seam(data, 'vertical')
    assert 'tiles seamlessly' in _seam(data, 'horizontal')  # constant across x


def test_seam_flat_image() -> None:
    assert '(ratio 0.00)' in _seam(np.zeros((8, 8, 1)), 'horizontal')


# REVIEW.md SRV-8: Designer's SBSPixelFormat also has RGB*, BGR8, BGRA8 and LUMALPHA*
@pytest.mark.parametrize(
    'fmt, dtype, scale, channels, names, order',
    [
        ('RGB8', np.uint8, 255, 3, 'RGB', [0, 1, 2]),
        ('RGB16', np.uint16, 65535, 3, 'RGB', [0, 1, 2]),
        ('RGB16F', np.float16, 1, 3, 'RGB', [0, 1, 2]),
        ('RGB32F', np.float32, 1, 3, 'RGB', [0, 1, 2]),
        ('BGR8', np.uint8, 255, 3, 'RGB', [2, 1, 0]),
        ('BGRA8', np.uint8, 255, 4, 'RGBA', [2, 1, 0, 3]),
        ('LUMALPHA8', np.uint8, 255, 2, 'LA', [0, 1]),
        ('LUMALPHA16', np.uint16, 65535, 2, 'LA', [0, 1]),
        ('LUMALPHA16F', np.float16, 1, 2, 'LA', [0, 1]),
        ('LUMALPHA32F', np.float32, 1, 2, 'LA', [0, 1]),
    ],
)
def test_decode_other_channel_layouts(
    fmt: str,
    dtype: PixelType,
    scale: int,
    channels: int,
    names: str,
    order: list[int],
) -> None:
    w, h = 3, 2
    stored = (np.arange(w * h * channels) * (scale // 20 if scale > 1 else 0.04)).astype(dtype)
    raw, pitch = _buffer(stored, dtype, w, h, channels, padding=8)
    bpp = channels * np.dtype(dtype).itemsize
    data, layout = server._decode_pixels(raw, {'format': fmt, 'width': w, 'height': h, 'pitch': pitch, 'bpp': bpp})
    assert data.shape == (h, w, channels) and server._channel_names(data, layout) == names
    expected = stored.astype(np.float64).reshape(h, w, channels)[:, :, order] / scale
    np.testing.assert_allclose(data, expected, rtol=1e-6)
    assert layout == ('L' if names == 'LA' else 'RGBA')


# [1, 2, 3]: its schema refuses it (test_server.py, REVIEW.md SRV-177)
@pytest.mark.parametrize('region', [[10, 10, 5, 20], [0, 0, 0, 5], [50, 50, 60, 60]])
def test_bad_regions_are_errors(region: list[int]) -> None:
    with pytest.raises(server.ToolError):
        server._crop(np.zeros((20, 20, 1)), region, 'region')


def test_region_is_clamped_not_wrapped() -> None:
    data = np.arange(100).reshape(10, 10, 1)
    assert server._crop(data, [-5, -5, 2, 2], 'region').shape == (2, 2, 1)  # not data[-5:2] (empty)
    assert server._crop(data, [8, 8, 50, 50], 'region').shape == (2, 2, 1)


def test_sweep_reports_a_value_that_failed(monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]) -> None:
    # REVIEW.md SRV-2: tiles for the first values, then "restored" from the put-back, then the error (HLP-179)
    def bridge(code: str) -> str:
        with open(os.path.join(temp_folders[-1], '0.raw'), 'wb') as f:  # the folder the server made
            f.write(bytes([128]))
        return (
            'SWEEP={"index": 0, "value": 0.1, "width": 1, "height": 1, "pitch": 1, "bpp": 1, "format": "LUM8"}\n'
            'restored n.p to 0.5\n--- ERROR ---\nTraceback ...\nRuntimeError: bad value for p'
        )

    fake_bridge(monkeypatch, bridge)
    text = server.sweep_param('n', 'p', [0.1, 'bogus', 0.9])[0]
    assert 'RuntimeError: bad value for p' in text and 'stopped' in text


def _swept_labels(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], param: str, values: list[Json], tile_size: int
) -> list[str]:
    """The labels sweep_param draws on its tiles, one value of `values` read back per tile, each a row of `tile_size`
    px, so its tile is that wide."""

    def bridge(code: str) -> str:
        lines = []
        for i, value in enumerate(values):
            with open(os.path.join(temp_folders[-1], '%d.raw' % i), 'wb') as f:  # the folder the server made
                f.write(bytes([128] * tile_size))
            meta = {
                'index': i,
                'value': value,
                'width': tile_size,
                'height': 1,
                'pitch': tile_size,
                'bpp': 1,
                'format': 'LUM8',
            }
            lines.append('SWEEP=' + json.dumps(meta))
        return '\n'.join([*lines, 'restored n.%s to ()' % param])

    drawn: list[str] = []
    draw_text = ImageDraw.ImageDraw.text

    def text_of(self: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, fill: tuple[int, int, int]) -> None:
        drawn.append(text)  # _labelled's call: its position, its text and its colour
        draw_text(self, xy, text, fill=fill)

    fake_bridge(monkeypatch, bridge)
    monkeypatch.setattr(ImageDraw.ImageDraw, 'text', text_of)
    server.sweep_param('n', param, values, tile_size=tile_size)
    return drawn


KEYS: list[Json] = [
    [[0.0, [1.0, 0.0, 0.0, 1.0]], [1.0, [0.0, 0.0, 1.0, 1.0]]],
    [[0.0, [1.0, 0.0, 0.0, 1.0]], [1.0, [0.0, 1.0, 0.0, 1.0]]],
]
VECTORS: list[Json] = [[0.4, 0.4, 0.4, 0.4], [0.4, 0.4, 0.4, 0.5]]


@pytest.mark.parametrize(
    'param, values, tile_size, labels',
    [
        # REVIEW.md SRV-222: keys were cut to the first key, so every tile read the same
        ('gradientrgba', KEYS, 256, ['#1 gradientrgba', '#2 gradientrgba']),
        # REVIEW.md SRV-223: wide enough for its 75 characters, the label was still cut to 48
        ('gradientrgba', KEYS, 512, ['#1 gradientrgba', '#2 gradientrgba']),
        ('levelouthigh', VECTORS, 256, ['levelouthigh = [0.4, 0.4, 0.4, 0.4]', 'levelouthigh = [0.4, 0.4, 0.4, 0.5]']),
        # the place first, so a narrow tile that clips the label keeps it (REVIEW.md SRV-223)
        ('levelouthigh', VECTORS, 64, ['#1 levelouthigh', '#2 levelouthigh']),
        # Pillow refuses to measure a newline (REVIEW.md SRV-223): one is drawn as a space
        ('name', ['a\nb', 'c'], 256, ['name = a b', 'name = c']),
    ],
    ids=['keys', 'keys on a wide tile', 'vectors', 'vectors on a narrow tile', 'a newline'],
)
def test_a_value_too_long_for_its_tile_is_labelled_by_its_place(
    monkeypatch: pytest.MonkeyPatch,
    temp_folders: list[str],
    param: str,
    values: list[Json],
    tile_size: int,
    labels: list[str],
) -> None:
    assert _swept_labels(monkeypatch, temp_folders, param, values, tile_size) == labels


def _diff(a: Pixels, b: Pixels, names: str = 'RGBA', box: tuple[int, int, int, int] | None = None) -> list[str]:
    """node_stats(against=...)'s lines for a against b, both of `names`, over the whole image or `box`, at the default
    tolerance."""
    return measure._diff_lines(a, names, b, names, box or (0, 0, a.shape[1], a.shape[0]), 0.002)


def _same(names: str) -> list[str]:
    return ['%s diff: max 0.000000 at (0,0)  mean 0.000000  over 0.002: 0 px (0.00%%)' % n for n in names]


def test_identical_outputs_differ_nowhere() -> None:
    a = np.random.default_rng(1).random((3, 4, 4))
    assert _diff(a, a.copy()) == _same('RGBA')


def test_an_offset_in_one_channel_is_its_max_and_mean_at_every_pixel() -> None:
    a = np.random.default_rng(2).integers(0, 128, (4, 5, 4)) / 256  # exact in binary, so the offset is too
    b = a.copy()
    b[:, :, 1] += 0.25
    lines = _diff(a, b)
    assert lines[1] == 'G diff: max 0.250000 at (0,0)  mean 0.250000  over 0.002: 20 px (100.00%)'
    assert [lines[0], *lines[2:]] == _same('RBA')


def test_the_largest_difference_in_a_region_is_located_in_the_whole_image() -> None:
    a = np.zeros((8, 10, 4))
    b = a.copy()
    b[5, 6, 2] = 0.5  # (6,5), inside the region
    b[0, 0, 2] = 1.0  # outside it
    lines = _diff(a, b, box=(4, 3, 9, 7))  # 5x4 px from (4,3)
    assert lines[2] == 'B diff: max 0.500000 at (6,5)  mean 0.025000  over 0.002: 1 px (5.00%)'


def test_a_tie_is_located_at_the_first_pixel_in_row_order() -> None:
    a = np.zeros((4, 5, 1))
    b = a.copy()
    b[1, 3, 0] = b[2, 1, 0] = 0.5  # (3,1) comes first in row order, (1,2) in column order
    assert _diff(a, b, 'L')[0].startswith('L diff: max 0.500000 at (3,1) ')


def test_a_difference_equal_to_the_tolerance_is_not_counted() -> None:
    a = np.zeros((1, 3, 1))
    b = np.array([0.002, 0.0021, 0.001]).reshape(1, 3, 1)
    assert _diff(a, b, 'L') == ['L diff: max 0.002100 at (1,0)  mean 0.001700  over 0.002: 1 px (33.33%)']


def test_colour_with_alpha_against_colour_compares_r_g_and_b() -> None:
    a = np.zeros((2, 2, 4))
    b = np.zeros((2, 2, 3))
    b[:, :, 0] = 0.1
    lines = measure._diff_lines(a, 'RGBA', b, 'RGB', (0, 0, 2, 2), 0.002)
    assert lines == ['R diff: max 0.100000 at (0,0)  mean 0.100000  over 0.002: 4 px (100.00%)', *_same('GB')]
