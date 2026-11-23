"""Reading image files, for the tools that take one: the reference tools (compare.py, reference.py) and preview_maps
(output.py). _open_image loads a file at its own pixel size, in the orientation its docstring gives, and _integer_scale
gives an integer grey image's range. For the reference tools, _reference_pixels turns the image into pixels 0..1,
_opaque and _finite pick the pixels they read, and _non_finite says how many are left out."""

import os

import numpy as np
import numpy.typing as npt
from mcp.server.mcpserver.exceptions import ToolError
from PIL import ExifTags, Image as PILImage, ImageOps, TiffImagePlugin

from .measure import PixelLayout, Pixels, Values

# the formats Pillow reads whose EXIF orientation Designer's bitmap node applies ("designer facts", the bitmaps check of
# orientations): a JPEG, and a multi-picture JPEG saved as .jpg
_TURNED = ('JPEG', 'MPO')
# what turns an image back to its stored frame from each EXIF orientation: the inverse of exif_transpose's turn
_STORED = {
    2: PILImage.Transpose.FLIP_LEFT_RIGHT,
    3: PILImage.Transpose.ROTATE_180,
    4: PILImage.Transpose.FLIP_TOP_BOTTOM,
    5: PILImage.Transpose.TRANSPOSE,
    6: PILImage.Transpose.ROTATE_90,
    7: PILImage.Transpose.TRANSVERSE,
    8: PILImage.Transpose.ROTATE_270,
}


def _open_image(path: str) -> PILImage.Image:
    """The image file at `path`, loaded at its own pixel size, in the orientation measured of Designer's bitmap node:
    - a JPEG (Pillow's JPEG or MPO, the multi-picture JPEG some phones save) is turned as its EXIF orientation says, as
      a bitmap node of it turns it, so a phone photo stored rotated comes out upright and a region of it is taken in
      that view;
    - a PNG and a TIFF are read as stored, whatever their orientation, as Designer keeps them (REVIEW.md SRV-238);
    - another format is read as stored, its bitmap node's orientation unmeasured.
    A bitmap node also rounds each side up to a power of 2 and stretches the image, which the opener doesn't (GUIDE.md's
    scripting part, Bitmaps). An embedded ICC profile is ignored, and the stored values are read as they are: the user,
    2026-11-23, "ok leave the icc profile as it is" (test_image_reading.py). Pillow turns a TIFF as it loads it, so a TIFF it turned is turned back
    (test_pil_facts.py). A JPEG's EXIF block Pillow can't read leaves it as loaded, and one it can't write back after
    turning the pixels leaves it turned. A file Pillow can't read is an error naming it and the reason: a broken or
    unknown file (OSError, ValueError, SyntaxError from a broken PNG chunk), or one over Pillow's size limit
    (DecompressionBombError, an Exception of its own)."""
    path = os.path.abspath(os.path.expanduser(path))
    try:
        im = PILImage.open(path)
        tiff = im if isinstance(im, TiffImagePlugin.TiffImageFile) else None
        orientation = tiff.tag_v2.get(ExifTags.Base.Orientation) if tiff else None
        im.load()
    except (OSError, ValueError, SyntaxError, PILImage.DecompressionBombError) as e:
        raise ToolError('cannot read %s: %s' % (path, e)) from e
    # Pillow 13 turns a TIFF as it loads it, then deletes the tag: the tag gone is the sign, so a Pillow of the range
    # requirements.txt allows that doesn't turn it reads it as stored, unturned
    if tiff and orientation in _STORED and ExifTags.Base.Orientation not in tiff.tag_v2:
        return im.transpose(_STORED[orientation])
    if im.format not in _TURNED:
        return im
    try:
        ImageOps.exif_transpose(im, in_place=True)
    except Exception:
        # The orientation is best-effort, on a damaged block of a file that loads (REVIEW.md SRV-232). Pillow's EXIF
        # reader raises before turning anything (SyntaxError), so the image is read as loaded. Its writer raises
        # after the pixels are turned (struct.error, TypeError), so the image is read turned, as it is viewed.
        pass
    return im


def _integer_scale(im: PILImage.Image) -> float | None:
    """What an integer grey image's values are divided by to give 0..1: 65535 for a 16-bit one (modes I;16), and for a
    plain 32-bit one (mode I) when a value of it is over 255, else 255. None for an image of another mode."""
    if not im.mode.startswith('I'):
        return None
    return 65535.0 if im.mode.startswith('I;16') or np.max(im.getextrema()) > 255 else 255.0


def _reference_pixels(im: PILImage.Image, scale: float | None) -> tuple[Pixels, PixelLayout]:
    """Image -> (pixels 0..1 as (H, W, C) floats, 'RGBA' or 'L'; a grayscale image with alpha
    is 'L' with alpha as a second channel). PIL reads 16-bit RGBA PNGs as 8-bit; 16-bit grayscale
    and float (mode F) keep their precision. An integer grey image's values are divided by `scale`: _integer_scale of
    the image `im` is, or was cut or sampled from (None for another mode)."""
    if im.mode in ('I', 'I;16', 'I;16B', 'I;16L', 'F'):
        a = np.array(im).astype(np.float64)
        if scale:
            a /= scale
        return a[:, :, None], 'L'
    if im.mode in ('1', 'L'):
        return np.array(im.convert('L')).astype(np.float64)[:, :, None] / 255.0, 'L'
    if im.mode in ('LA', 'La'):
        return np.array(im.convert('LA')).astype(np.float64) / 255.0, 'L'
    return np.array(im.convert('RGBA')).astype(np.float64) / 255.0, 'RGBA'


def _alpha(data: Pixels) -> Values | None:
    """The alpha channel of decoded pixels (4 channels, or 'L' with alpha), or None."""
    return data[:, :, -1] if data.shape[2] in (2, 4) else None


def _opaque(ref: Pixels) -> tuple[npt.NDArray[np.bool_] | None, str | None]:
    """The reference's opaque pixels (alpha 0.5 or more) and the line saying what share of it is left out, or (None,
    None) when no pixel is transparent. A fully transparent reference is an error."""
    alpha = _alpha(ref)
    if alpha is None or not (alpha < 0.5).any():
        return None, None
    mask = alpha >= 0.5
    if not mask.any():
        raise ToolError('the reference is fully transparent')
    return mask, 'ignoring %.1f%% transparent reference pixels' % (100 - 100 * mask.mean())


def _finite(data: Pixels) -> tuple[npt.NDArray[np.bool_], int]:
    """The pixels of `data` whose values are all finite numbers, and how many are not (NaN or infinite)."""
    finite = np.isfinite(data).all(axis=2)
    return finite, int(finite.size - finite.sum())


def _non_finite(count: int) -> str:
    """'<count> non-finite pixel(s) (NaN or infinite)', as the reference tools say it."""
    return '%d non-finite %s (NaN or infinite)' % (count, 'pixels' if count > 1 else 'pixel')
