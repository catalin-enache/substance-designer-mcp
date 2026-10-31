import os
import re
from typing import Any, cast

import numpy as np
import numpy.typing as npt
import pytest

from conftest import patch_server, server


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
def test_decode_rgba_skips_row_padding(fmt: str, dtype: type[np.generic], scale: int) -> None:
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


def _seam(data: npt.NDArray[Any], axis_name: str) -> str:
    report: str = server._seam_report(data, axis_name, 1 if axis_name == 'horizontal' else 0)
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
    fmt: str, dtype: type[np.generic], scale: int, channels: int, names: str, order: list[int]
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


@pytest.mark.parametrize('region', [[10, 10, 5, 20], [0, 0, 0, 5], [50, 50, 60, 60], [1, 2, 3]])
def test_bad_regions_are_errors(region: list[int]) -> None:
    with pytest.raises(server.ToolError):
        server._crop(np.zeros((20, 20, 1)), region, 'region')


def test_region_is_clamped_not_wrapped() -> None:
    data = np.arange(100).reshape(10, 10, 1)
    assert server._crop(data, [-5, -5, 2, 2], 'region').shape == (2, 2, 1)  # not data[-5:2] (empty)
    assert server._crop(data, [8, 8, 50, 50], 'region').shape == (2, 2, 1)


def test_sweep_reports_a_value_that_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-2: tiles for the first values, then an error, then "restored" from the finally
    def fake_bridge(code: str, path: str | None = None, timeout: float | None = None) -> str:
        out_dir = cast(re.Match[str], re.search(r"(/[^'\\]*sd_sweep_\w+)", code)).group(1)
        with open(os.path.join(out_dir, '0.raw'), 'wb') as f:
            f.write(bytes([128]))
        return (
            'SWEEP={"index": 0, "value": 0.1, "width": 1, "height": 1, "pitch": 1, "bpp": 1, "format": "LUM8"}\n'
            'restored n.p to 0.5\n--- ERROR ---\nTraceback ...\nRuntimeError: bad value for p'
        )

    patch_server(monkeypatch, '_bridge', fake_bridge)
    text = server.sweep_param('n', 'p', [0.1, 'bogus', 0.9])[0]
    assert 'RuntimeError: bad value for p' in text and 'stopped' in text
