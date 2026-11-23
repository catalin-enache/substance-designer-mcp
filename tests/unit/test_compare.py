import re
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
from image_files import png, tiff_32, tiff_float
from PIL import Image

from conftest import server
from server_tools.compare import _compare_report
from server_tools.measure import PixelLayout, Pixels, Values


def _rgba(color: list[float], w: int = 8, h: int = 8) -> npt.NDArray[np.float64]:
    a = np.zeros((h, w, 4))
    a[:, :] = color
    return a


def _report(
    node: Pixels, node_layout: PixelLayout, ref: Pixels, ref_layout: PixelLayout, aligned: bool = False
) -> tuple[str, Values | None]:
    lines, diff = _compare_report(node, node_layout, ref, ref_layout, aligned)
    return '\n'.join(lines), diff


def test_load_reference_modes(tmp_path: Path) -> None:
    Image.new('RGB', (4, 2), (255, 0, 51)).save(tmp_path / 'rgb.png')
    data, layout = server._load_reference(str(tmp_path / 'rgb.png'))
    assert layout == 'RGBA' and data.shape == (2, 4, 4)
    np.testing.assert_allclose(data[0, 0], [1, 0, 0.2, 1])
    Image.fromarray(np.full((3, 3), 32768, np.uint16)).save(tmp_path / 'gray16.png')
    data, layout = server._load_reference(str(tmp_path / 'gray16.png'))
    assert layout == 'L' and abs(data[0, 0, 0] - 32768 / 65535) < 1e-9  # 16-bit precision kept
    Image.new('L', (3, 3), 51).save(tmp_path / 'gray8.png')
    assert server._load_reference(str(tmp_path / 'gray8.png'))[0][0, 0, 0] == pytest.approx(0.2)
    Image.new('F', (3, 3), 0.25).save(tmp_path / 'float.tif')
    assert server._load_reference(str(tmp_path / 'float.tif'))[0][0, 0, 0] == pytest.approx(0.25)


def test_load_reference_region_and_errors(tmp_path: Path) -> None:
    a = np.zeros((10, 20), np.uint8)
    a[2:4, 5:9] = 255
    path = png(tmp_path / 'm.png', a)
    data, _ = server._load_reference(path, [5, 2, 9, 4])
    assert data.shape == (2, 4, 1) and data.min() == 1
    with pytest.raises(server.ToolError, match='is empty'):
        server._load_reference(path, [30, 30, 40, 40])
    with pytest.raises(server.ToolError, match='cannot read'):
        server._load_reference(str(tmp_path / 'missing.png'))


def test_a_region_of_a_32_bit_image_keeps_the_whole_images_range(tmp_path: Path) -> None:
    # a plain 'I' image is 16-bit when any of its values is over 255: a dark region of it is too
    a = np.full((4, 8), 100, np.int32)
    a[:, 4:] = 40000
    data, _ = server._load_reference(tiff_32(tmp_path / 'i32.tif', a), (0, 0, 4, 4))
    assert data[0, 0, 0] == pytest.approx(100 / 65535)


def test_a_reference_holding_non_finite_pixels_is_refused(tmp_path: Path) -> None:
    # REVIEW.md SRV-231: a float reference's NaN gave NaN statistics and "luma distributions: different"
    values = np.full((4, 8), 0.5, np.float32)
    values[0, 0], values[1, 1] = np.nan, np.inf
    path = tiff_float(tmp_path / 'float.tif', values)
    with pytest.raises(server.ToolError, match=r'the reference holds 2 non-finite pixels \(NaN or infinite\)'):
        server._load_reference(path)
    data, _ = server._load_reference(path, (2, 2, 8, 4))  # a region without them
    assert np.isfinite(data).all()


@pytest.mark.parametrize(
    ('name', 'region', 'refusal'),
    [('missing.tif', None, 'cannot read'), ('ref.tif', (30, 30, 40, 40), 'is empty'), ('ref.tif', None, 'non-finite')],
    ids=['missing', 'empty region', 'non-finite'],
)
def test_a_refused_reference_sends_nothing_to_designer(
    tmp_path: Path, sent: list[str], name: str, region: tuple[int, int, int, int] | None, refusal: str
) -> None:
    """REVIEW.md SRV-236: the node was computed in Designer, through a temporary output, before the reference was read
    and refused. The reference file holds a NaN: an empty region is refused before it."""
    values = np.full((4, 8), 0.5, np.float32)
    values[0, 0] = np.nan
    tiff_float(tmp_path / 'ref.tif', values)
    with pytest.raises(server.ToolError, match=refusal):
        server.compare_to_reference('n', str(tmp_path / name), reference_region=region)
    assert sent == []


def test_identical_images() -> None:
    rng = np.random.default_rng(1)
    a = rng.random((16, 16, 4))
    a[:, :, 3] = 1
    text, diff = _report(a, 'RGBA', a.copy(), 'RGBA', aligned=True)
    assert 'luma distributions: close (EMD 0.000' in text
    assert diff is not None
    assert 'mean abs diff 0.0000' in text and np.max(diff) == 0
    assert 'x*1.000 +0.000' in text


def test_shift_and_contrast_are_measured_and_fixable() -> None:
    rng = np.random.default_rng(2)
    node = rng.random((32, 32, 1)) * 0.5 + 0.25  # mean ~0.5, narrow range
    m = node.mean()
    ref = (node - m) * 1.5 + m + 0.1  # brighter, more contrast
    text, diff = _report(node, 'L', ref, 'L')
    assert diff is None and 'pixel by pixel' not in text
    luma = next(l for l in text.splitlines() if 'contrast x' in l)
    assert 'mean +0.100' in luma and 'contrast x1.50' in luma
    assert 'luma: x*1.500 %+.3f' % (0.1 - 0.5 * m) in text  # gain and bias that map node onto ref
    assert '(EMD 0.1' in text and 'different' in text


def test_colour_vs_grayscale_compares_luma_only() -> None:
    text, _ = _report(_rgba([1, 0, 0, 1]), 'RGBA', np.full((8, 8, 1), 0.2126), 'L')
    rows = [l.split()[0] for l in text.splitlines() if 'contrast x' in l]
    assert rows == ['luma'] and 'EMD 0.000' in text


def test_colour_channels_reported() -> None:
    text, _ = _report(_rgba([0.2, 0.4, 0.6, 1]), 'RGBA', _rgba([0.3, 0.4, 0.5, 1]), 'RGBA')
    assert [l.split()[0] for l in text.splitlines()[1:5]] == ['R', 'G', 'B', 'luma']
    assert 'mean +0.100' in text.splitlines()[1] and 'mean -0.100' in text.splitlines()[3]


def test_transparent_reference_pixels_ignored() -> None:
    ref = _rgba([0.5, 0.5, 0.5, 1])
    ref[:, :4] = [1, 1, 1, 0]  # left half transparent and white
    text, _ = _report(_rgba([0.5, 0.5, 0.5, 1]), 'RGBA', ref, 'RGBA')
    assert 'ignoring 50.0% transparent reference pixels' in text and 'EMD 0.000' in text
    with pytest.raises(server.ToolError, match='fully transparent'):
        _report(_rgba([0.5] * 4), 'RGBA', _rgba([1, 1, 1, 0]), 'RGBA')


def test_aligned_resizes_reference_and_warns_on_aspect() -> None:
    node = np.zeros((8, 8, 1))
    node[:, 4:] = 1
    ref = np.zeros((32, 32, 1))
    ref[:, 16:] = 1  # same picture, 4x larger
    text, diff = _report(node, 'L', ref, 'L', aligned=True)
    assert 'reference resized to 8x8' in text and 'mean abs diff 0.0000' in text and 'WARNING' not in text
    assert diff is not None and diff.shape == (8, 8)
    text, _ = _report(node, 'L', np.zeros((8, 16, 1)), 'L', aligned=True)
    assert 'WARNING: aspect ratios differ' in text


def test_emd_is_in_value_units() -> None:
    x = np.linspace(0, 1, 1000)
    assert server._emd(x, x + 0.1) == pytest.approx(0.1)


def test_histogram_tile_size() -> None:
    im = server._histogram_tile(np.random.default_rng(0).random(500), np.full(500, 0.5), 200, 120)
    assert im.size == (200, 120)


def test_compare_ignores_transparent_pixels_of_a_grayscale_alpha_reference(tmp_path: Path) -> None:
    # REVIEW.md SRV-9: an 'LA' reference was converted to 'L', so its transparent pixels counted
    a = np.zeros((4, 8, 2), np.uint8)
    a[:, :4] = (128, 255)  # left half opaque mid-grey
    a[:, 4:] = (0, 0)  # right half transparent black
    Image.fromarray(a, 'LA').save(tmp_path / 'la.png')
    ref, layout = server._load_reference(str(tmp_path / 'la.png'))
    lines, _ = server._compare_report(np.full((4, 8, 1), 128 / 255), 'L', ref, layout)
    text = '\n'.join(lines)
    assert 'ignoring 50.0% transparent reference pixels' in text
    assert re.search(r'^luma .*\+0\.000', text, re.M), text
