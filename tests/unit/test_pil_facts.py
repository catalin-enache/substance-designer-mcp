"""AGENTS.md, Rendering and verifying (REVIEW.md TST-3): how PIL loads Designer's 16-bit PNGs.
Grayscale stays 16-bit ('I;16'); RGBA comes back as 8 bits per channel, so exact values need
node_stats. Measured with the Pillow in mcp_server/venv."""
import struct
import zlib

import numpy as np
from PIL import Image


def _png_rgba16(path, pixels):
    """A 16-bit RGBA PNG (Pillow can't write one), pixels: uint16 array (H, W, 4)."""
    h, w, _ = pixels.shape
    raw = b''.join(b'\x00' + row.astype('>u2').tobytes() for row in pixels)

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 16, 6, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def test_16bit_grayscale_png_loads_as_I16(tmp_path):
    path = tmp_path / 'gray16.png'
    Image.fromarray(np.full((2, 2), 40000, np.uint16)).save(path)
    im = Image.open(path)
    assert im.mode == 'I;16' and im.getpixel((0, 0)) == 40000


def test_16bit_rgba_png_loads_as_8bit(tmp_path):
    path = tmp_path / 'rgba16.png'
    _png_rgba16(str(path), np.full((2, 2, 4), [40000, 1000, 65535, 65535], np.uint16))
    im = Image.open(path)
    assert im.mode == 'RGBA'
    assert im.getpixel((0, 0)) == (40000 >> 8, 1000 >> 8, 255, 255)   # only the high byte survives
