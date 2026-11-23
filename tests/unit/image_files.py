"""Image files for the tests of the reading the reference tools share (image_reading.py's _open_image, compare.py's
_load_reference, analyze_reference): files Pillow writes from 8-bit, 32-bit or float pixels, files of each format
with an EXIF orientation, and files Pillow refuses or reads only in part; the framing of a PNG chunk, for PNGs written byte by
byte; and strips of flat swatches of known colours. For their tests (test_image_reading.py, test_reference.py,
test_compare.py, test_pil_facts.py)."""

import struct
import zlib
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt
from PIL import ExifTags, Image

RGB8 = tuple[int, int, int]  # a colour as 8-bit values
RGBA8 = tuple[int, int, int, int]
# three flat colours of distinct luminance, darkest first. The luminance is Designer's grey, the mean of R, G and B, as
# its Grayscale Conversion gives it at its default (GUIDE.md, The greys of a colour image)
DARK: RGB8 = (40, 20, 10)
MID: RGB8 = (200, 80, 40)
LIGHT: RGB8 = (240, 230, 180)


def swatch_strip(*colours: RGB8 | RGBA8, width: int = 10, height: int = 10) -> npt.NDArray[np.uint8]:
    """A strip of flat swatches, one per colour, side by side."""
    return np.concatenate([np.full((height, width, len(c)), c, np.uint8) for c in colours], axis=1)


def marked_halves() -> npt.NDArray[np.uint8]:
    """Two 10x10 halves, DARK on the left and LIGHT on the right, with a MID 5x5 mark in the top-left corner: unlike
    the halves alone, it differs from its mirror top to bottom, so a turn can't pass for its mirror (REVIEW.md
    TST-787)."""
    pixels = swatch_strip(DARK, LIGHT)
    pixels[:5, :5] = MID
    return pixels


def halves_png(tmp_path: Path) -> str:
    """An image of two halves, DARK on the left, LIGHT on the right, each 10x10, as halves.png in `tmp_path`."""
    return png(tmp_path / 'halves.png', swatch_strip(DARK, LIGHT))


def png(path: Path, pixels: npt.NDArray[np.uint8]) -> str:
    """The 8-bit pixels (H, W), (H, W, 3) or (H, W, 4) as a PNG."""
    Image.fromarray(pixels).save(path)
    return str(path)


def tiff_32(path: Path, values: npt.NDArray[np.int32]) -> str:
    """A plain 32-bit grey image (Pillow's mode I) as a TIFF."""
    Image.fromarray(values, 'I').save(path)
    return str(path)


def tiff_float(path: Path, values: npt.NDArray[np.float32]) -> str:
    """A float grey image (Pillow's mode F) as a TIFF."""
    Image.fromarray(values, 'F').save(path)
    return str(path)


Format = Literal['JPEG', 'MPO', 'PNG', 'TIFF']  # the formats turned() writes, by Pillow's names


def turned(path: Path, pixels: npt.NDArray[np.uint8], kind: Format, orientation: int = 6) -> str:
    """The pixels in Pillow's format `kind` (JPEG, MPO, PNG or TIFF) with an EXIF orientation, 6 by default: turned by
    6 to be viewed, the stored left column is the top row. A JPEG is at full quality with no chroma subsampling, so
    flat colours stay within a step or two; an MPO is the multi-picture JPEG some phones save, as .jpg."""
    exif = Image.Exif()
    exif[ExifTags.Base.Orientation] = orientation
    image = Image.fromarray(pixels)
    if kind == 'MPO':
        image.save(path, kind, exif=exif, quality=100, subsampling=0, save_all=True, append_images=[image.copy()])
    elif kind == 'JPEG':
        image.save(path, kind, exif=exif, quality=100, subsampling=0)
    else:
        image.save(path, kind, exif=exif)
    return str(path)


def jpeg_with_an_exif_not_tiff(path: Path, pixels: npt.NDArray[np.uint8]) -> str:
    """The pixels as a JPEG with dpi whose EXIF block isn't TIFF data: the image loads, and Pillow's EXIF reader raises
    SyntaxError ('not a TIFF file') when the orientation is read (REVIEW.md SRV-232)."""
    Image.fromarray(pixels).save(path, 'JPEG', exif=b'Exif\x00\x00not-a-tiff-header', dpi=(72, 72))
    return str(path)


def png_chunk(kind: bytes, data: bytes) -> bytes:
    """A PNG chunk: its length, its kind, its data and their CRC."""
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def broken_png(path: Path) -> str:
    """A 16x16 PNG whose pixel data goes on in a chunk with a broken header, which Pillow's load raises SyntaxError
    for."""
    raw = zlib.compress(b''.join(b'\x00' + bytes([row] * 48) for row in range(16)))
    header = png_chunk(b'IHDR', struct.pack('>IIBBBBB', 16, 16, 8, 2, 0, 0, 0))
    half = len(raw) // 2
    path.write_bytes(
        b'\x89PNG\r\n\x1a\n'
        + header
        + png_chunk(b'IDAT', raw[:half])
        + png_chunk(b'ID\x00T', raw[half:])
        + png_chunk(b'IEND', b'')
    )
    return str(path)
