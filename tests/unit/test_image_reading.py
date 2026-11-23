"""The reading of image files the tools share (server_tools/image_reading.py's _open_image), through analyze_reference
and compare_to_reference's _load_reference: a file Pillow refuses is named with its reason, and a JPEG's EXIF
orientation is applied, best-effort, as Designer's bitmap node applies it, while another format is read as stored."""

import re
import struct
from pathlib import Path

import numpy as np
import pytest
from image_files import (
    DARK,
    LIGHT,
    MID,
    Format,
    broken_png,
    halves_png,
    jpeg_with_an_exif_not_tiff,
    marked_halves,
    swatch_strip,
    turned,
)
from PIL import Image, ImageCms, ImageOps
from reference_results import assert_keys, result_keys, result_line

from conftest import server


@pytest.mark.parametrize('loader', ['analyze_reference', '_load_reference'])
@pytest.mark.parametrize('case', ['too large', 'broken'])
def test_an_image_pillow_refuses_is_named_with_its_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, loader: str
) -> None:
    """Pillow raises DecompressionBombError (an Exception) over its size limit, and SyntaxError for a broken chunk in
    the pixel data: each is the tool's error, naming the file and the reason (compare_to_reference reads it with
    _load_reference)."""
    if case == 'too large':
        path, reason = halves_png(tmp_path), 'decompression bomb'
        monkeypatch.setattr(Image, 'MAX_IMAGE_PIXELS', 10)  # refused over twice this many: the image has 200
    else:
        path, reason = broken_png(tmp_path / 'broken.png'), 'broken PNG file'
    with pytest.raises(server.ToolError, match=r'cannot read .*%s: .*%s' % (re.escape(Path(path).name), reason)):
        getattr(server, loader)(path)


def test_a_photo_whose_exif_pillow_cant_read_is_read_as_loaded(tmp_path: Path) -> None:
    """The orientation is best-effort: a JPEG whose EXIF isn't TIFF data loads, and was refused as 'cannot read'. It is
    read as stored, 16x8, its left half MID."""
    path = jpeg_with_an_exif_not_tiff(tmp_path / 'photo.jpg', swatch_strip(MID, (0, 0, 0), width=8, height=8))
    data, _ = server._load_reference(path)  # Pillow fails to read this EXIF (test_pil_facts.py)
    assert data.shape == (8, 16, 4)
    np.testing.assert_allclose(data[0, [0, -1], :3], np.array([MID, (0, 0, 0)]) / 255, atol=0.02)  # a JPEG's colours
    assert 'gradientrgba: ' in server.analyze_reference(path)


@pytest.mark.parametrize(
    'error',
    [struct.error('required argument is not an integer'), TypeError('The fill character must be a unicode character')],
    ids=['struct.error', 'TypeError'],
)
def test_a_photo_whose_exif_pillow_cant_write_back_is_read_turned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """Pillow turns the pixels first, then writes the EXIF back without its orientation: an error there (these two,
    from damaged blocks: REVIEW.md SRV-232) leaves the image turned, as it is viewed."""
    turn = ImageOps.exif_transpose

    def turned_then_failing(image: Image.Image, *, in_place: bool = False) -> None:
        turn(image, in_place=True)
        raise error

    monkeypatch.setattr(ImageOps, 'exif_transpose', turned_then_failing)  # the module _open_image calls it through
    _assert_read(turned(tmp_path / 'phone.jpg', marked_halves(), 'JPEG'), 6)


@pytest.mark.parametrize('kind', ['JPEG', 'MPO'])
def test_a_jpeg_stored_rotated_is_read_as_it_is_viewed(tmp_path: Path, kind: Format) -> None:
    """A JPEG's EXIF orientation 6 turns it a quarter clockwise to be viewed, as Designer's bitmap node turns it: the
    stored left half, DARK, is then the top, and a region is taken in that view. A multi-picture JPEG (Pillow's MPO)
    too. compare_to_reference reads it the same way (_load_reference)."""
    path = turned(tmp_path / 'phone.jpg', marked_halves(), kind)
    with Image.open(path) as saved:
        assert saved.format == kind  # an MPO saved as one, not a plain JPEG
    text = server.analyze_reference(path, reference_region=(0, 10, 10, 20))
    assert result_line(text, 'phone.jpg: ') == 'phone.jpg: 10x10 pixels in reference_region [0, 10, 10, 20]'
    assert_keys(text, [(0, LIGHT)], within=0.02)
    _assert_read(path, 6)


@pytest.mark.parametrize('orientation', [3, 6, 8])
def test_a_jpeg_is_read_turned_by_each_orientation_measured(tmp_path: Path, orientation: int) -> None:
    """A JPEG at each orientation the bitmaps check of orientations measures in Designer, read by the same turns,
    written by hand: the tools read each such file as its bitmap node computes it (REVIEW.md TST-787)."""
    _assert_read(turned(tmp_path / 'phone.jpg', marked_halves(), 'JPEG', orientation), orientation)


@pytest.mark.parametrize('kind', ['PNG', 'TIFF'])
def test_a_png_or_tiff_is_read_as_stored_whatever_its_orientation(tmp_path: Path, kind: Format) -> None:
    """Designer's bitmap node keeps a PNG's (eXIf) and a TIFF's orientation in the stored frame, so the opener does too:
    every tool reads its orientation as a bitmap of it does (REVIEW.md SRV-238)."""
    _assert_read(turned(tmp_path / ('tagged.' + kind.lower()), marked_halves(), kind))


@pytest.mark.parametrize('orientation', range(2, 9))
def test_a_tiff_is_turned_back_from_each_orientation_pillow_applies(tmp_path: Path, orientation: int) -> None:
    """Pillow turns a TIFF by its EXIF orientation as it loads it (test_pil_facts.py), so the opener turns it back to
    the stored frame, for each orientation: every pixel of a 6x3 image of distinct values is where it was stored."""
    stored = np.arange(6 * 3 * 3, dtype=np.uint8).reshape(3, 6, 3) * 4
    data, _ = server._load_reference(turned(tmp_path / 'tagged.tif', stored, 'TIFF', orientation))
    np.testing.assert_array_equal(np.round(data[:, :, :3] * 255), stored)


# np.rot90's quarter turns, anticlockwise, of each EXIF orientation measured: 3 a half turn, 6 a quarter clockwise,
# 8 a quarter anticlockwise. Each differs from its mirror (2, 5, 7) on marked_halves(), whose mark is in one corner
_TURNS = {3: 2, 6: -1, 8: 1}


def _assert_read(path: str, orientation: int | None = None) -> None:
    """compare_to_reference reads marked_halves() (_load_reference) turned as `orientation` says (_TURNS), or as
    stored without one: a pixel each of the mark, DARK and LIGHT, away from their edges, is where the turn puts it. A
    JPEG's colours are within a step or two."""
    stored = marked_halves()
    picked = np.zeros(stored.shape[:2], bool)
    picked[[2, 7, 5], [2, 2, 15]] = True  # the mark's middle, DARK below it, LIGHT
    turns = _TURNS[orientation] if orientation else 0
    want, at = np.rot90(stored, turns), np.rot90(picked, turns)
    data, _ = server._load_reference(path)
    assert data.shape[:2] == want.shape[:2]
    np.testing.assert_allclose(data[at][:, :3], want[at] / 255, atol=0.01)


@pytest.mark.parametrize('form', ['PNG', 'JPEG'])
def test_an_embedded_icc_profile_is_ignored(tmp_path: Path, form: str) -> None:
    """A file's ICC profile, here an XYZ one, is left as it is, and its stored values are read as they are: the user,
    2026-11-23, "ok leave the icc profile as it is" (Designer's own handling of a profile is unmeasured)."""
    stored = swatch_strip(DARK, LIGHT)
    path = str(tmp_path / ('profiled.' + form.lower()))
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('XYZ')).tobytes()
    options = {'quality': 100, 'subsampling': 0} if form == 'JPEG' else {}
    Image.fromarray(stored).save(path, form, icc_profile=profile, **options)
    with Image.open(path) as saved:
        assert saved.info.get('icc_profile') == profile  # the profile is there to be ignored
    data, _ = server._load_reference(path)
    np.testing.assert_allclose(data[:, :, :3], stored / 255, atol=0.01 if form == 'JPEG' else 0)
    keys = result_keys(server.analyze_reference(path, keys=2))
    np.testing.assert_allclose([colour[:3] for _, colour in keys], np.array([DARK, LIGHT]) / 255, atol=0.01)
