"""GUIDE.md, Rendering and verifying (REVIEW.md TST-3): how PIL loads Designer's 16-bit PNGs.
Grayscale stays 16-bit ('I;16'); RGBA comes back as 8 bits per channel, so exact values need
node_stats. And what the image opener (image_reading.py's _open_image) relies on: the failed EXIF read a test of it
uses (REVIEW.md SRV-232), and Pillow turning a TIFF by its orientation as it loads it. Measured with the Pillow in
mcp_server/venv."""

import struct
import zlib
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
from image_files import jpeg_with_an_exif_not_tiff, png_chunk, turned
from PIL import ExifTags, Image, ImageOps, TiffImagePlugin


def _png_rgba16(path: str, pixels: npt.NDArray[np.uint16]) -> None:
    """A 16-bit RGBA PNG (Pillow can't write one), pixels: uint16 array (H, W, 4)."""
    h, w, _ = pixels.shape
    raw = b''.join(b'\x00' + row.astype('>u2').tobytes() for row in pixels)
    with open(path, 'wb') as f:
        f.write(
            b'\x89PNG\r\n\x1a\n'
            + png_chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 16, 6, 0, 0, 0))
            + png_chunk(b'IDAT', zlib.compress(raw))
            + png_chunk(b'IEND', b'')
        )


def test_16bit_grayscale_png_loads_as_I16(tmp_path: Path) -> None:
    path = tmp_path / 'gray16.png'
    Image.fromarray(np.full((2, 2), 40000, np.uint16)).save(path)
    im = Image.open(path)
    assert im.mode == 'I;16' and im.getpixel((0, 0)) == 40000


def test_16bit_rgba_png_loads_as_8bit(tmp_path: Path) -> None:
    path = tmp_path / 'rgba16.png'
    _png_rgba16(str(path), np.full((2, 2, 4), [40000, 1000, 65535, 65535], np.uint16))
    im = Image.open(path)
    assert im.mode == 'RGBA'
    assert im.getpixel((0, 0)) == (40000 >> 8, 1000 >> 8, 255, 255)  # only the high byte survives


def test_an_exif_block_that_isnt_tiff_data_fails_pillows_orientation_read(tmp_path: Path) -> None:
    """test_image_reading.py's photo whose EXIF Pillow can't read relies on it. If this fails, Pillow came to read such a
    block: that test then reaches no failed read, so give it a block Pillow refuses."""
    path = jpeg_with_an_exif_not_tiff(tmp_path / 'photo.jpg', np.zeros((8, 16, 3), np.uint8))
    with pytest.raises(SyntaxError, match='not a TIFF file'):
        ImageOps.exif_transpose(Image.open(path))


def test_pillow_turns_a_tiff_by_its_orientation_as_it_loads_it_and_drops_the_tag(tmp_path: Path) -> None:
    """The opener turns a TIFF back to its stored frame when Pillow has turned it, which the tag gone after the load
    shows (image_reading.py). If this fails, Pillow changed how it loads a TIFF: the opener's turn back needs another
    sign."""
    stored = np.zeros((32, 64, 3), np.uint8)
    stored[0, 5] = 255  # one white pixel, at x 5 of the top row
    image = Image.open(turned(tmp_path / 'tagged.tif', stored, 'TIFF'))
    assert isinstance(image, TiffImagePlugin.TiffImageFile)
    assert image.size == (32, 64) and image.tag_v2.get(ExifTags.Base.Orientation) == 6  # turned already, tag kept
    image.load()
    # a quarter clockwise, the white pixel goes to (31, 5); in the stored frame, (31, 5) is black and (5, 0) white
    assert image.getpixel((31, 5)) == (255, 255, 255) and image.getpixel((5, 0)) == (0, 0, 0)
    assert ExifTags.Base.Orientation not in image.tag_v2
