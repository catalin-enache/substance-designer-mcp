import numpy as np
import pytest

from conftest import server


def _buffer(values, dtype, width, height, channels, padding):
    """Raw bytes like Designer's texture buffer: rows of pixels plus `padding` bytes per row."""
    rows = np.asarray(values, dtype=dtype).reshape(height, width * channels).view(np.uint8)
    pad = np.full((height, padding), 0xAB, dtype=np.uint8)
    return np.hstack([rows, pad]).tobytes(), rows.shape[1] + padding


@pytest.mark.parametrize('fmt, dtype, scale', [('RGBA8', np.uint8, 255), ('RGBA16', np.uint16, 65535),
                                               ('RGBA16F', np.float16, 1), ('RGBA32F', np.float32, 1)])
def test_decode_rgba_skips_row_padding(fmt, dtype, scale):
    w, h = 3, 2
    values = (np.arange(w * h * 4) * (scale // 30 if scale > 1 else 0.03)).astype(dtype)
    raw, pitch = _buffer(values, dtype, w, h, 4, padding=8)
    bpp = 4 * np.dtype(dtype).itemsize
    data, layout = server._decode_pixels(raw, {'format': fmt, 'width': w, 'height': h, 'pitch': pitch, 'bpp': bpp})
    assert layout == 'RGBA' and data.shape == (h, w, 4)
    np.testing.assert_allclose(data.ravel(), values.astype(np.float64) / scale, rtol=1e-6)


def test_decode_lum16():
    raw, pitch = _buffer([0, 65535, 32768, 1000], np.uint16, 2, 2, 1, padding=4)
    data, layout = server._decode_pixels(raw, {'format': 'LUM16', 'width': 2, 'height': 2, 'pitch': pitch, 'bpp': 2})
    assert layout == 'L' and data.shape == (2, 2, 1)
    np.testing.assert_allclose(data[:, :, 0], [[0, 1], [32768 / 65535, 1000 / 65535]])


def test_decode_unknown_format():
    with pytest.raises(server.ToolError, match='unsupported pixel format'):
        server._decode_pixels(b'\0' * 16, {'format': 'RGBA12', 'width': 1, 'height': 1, 'pitch': 16, 'bpp': 6})


def _seam(data, axis_name):
    return server._seam_report(data, axis_name, 1 if axis_name == 'horizontal' else 0)


def test_seam_periodic_pattern_tiles():
    # triangle wave, one period across the width: every step (seam included) is the same size.
    # (A sine scores ~1.58 when its steepest part sits on the seam; see ROADMAP.)
    wave = 1 - np.abs(np.arange(64) - 32) / 32
    data = np.tile(wave, (32, 1))[:, :, None]
    report = _seam(data, 'horizontal')
    assert report.startswith('Horizontal tiling (left/right edges)') and '(ratio 1.00)' in report
    assert 'tiles seamlessly' in report


def test_seam_ramp_has_visible_seam_at_worst_row():
    data = np.tile(np.linspace(0, 1, 64), (32, 1))[:, :, None].copy()
    data[7, 0] = -1.0                                           # make row 7 the worst
    report = _seam(data, 'horizontal')
    assert 'VISIBLE SEAM' in report and 'at row 7' in report


def test_seam_vertical_axis():
    data = np.tile(np.linspace(0, 1, 16)[:, None], (1, 8))[:, :, None]   # ramp top to bottom
    assert 'VISIBLE SEAM' in _seam(data, 'vertical')
    assert 'tiles seamlessly' in _seam(data, 'horizontal')     # constant across x


def test_seam_flat_image():
    assert '(ratio 0.00)' in _seam(np.zeros((8, 8, 1)), 'horizontal')
