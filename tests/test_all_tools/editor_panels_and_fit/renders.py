"""What the 3D view checks measure in a render of a checker on a plane seen from the top: the plane's width, height and
middle (a square from straight above), and how often its middle row turns from dark to light (twice per square: tiling
2 doubles it)."""

import base64
import io

import numpy as np
from mcp.types import CallToolResult
from PIL import Image as PILImage

from test_all_tools.common import is_image, text


def grey(r: CallToolResult) -> 'np.ndarray[tuple[int, int], np.dtype[np.float64]]':
    """The result's image as grey levels 0-255, rows by columns."""
    data = next(c.data for c in r.content if c.type == 'image')
    with PILImage.open(io.BytesIO(base64.b64decode(data))) as im:
        return np.asarray(im.convert('L'), dtype=float)


def plane_columns(a: 'np.ndarray[tuple[int, int], np.dtype[np.float64]]') -> tuple[int, int]:
    """The first and last column that differ from the background (its top-left pixel) by more than 25 levels."""
    cols = np.where((np.abs(a - a[0, 0]) > 25).any(axis=0))[0]
    return (int(cols.min()), int(cols.max())) if len(cols) else (0, -1)


def plane_width(a: 'np.ndarray[tuple[int, int], np.dtype[np.float64]]') -> int:
    first, last = plane_columns(a)
    return last - first + 1


def plane_height(a: 'np.ndarray[tuple[int, int], np.dtype[np.float64]]') -> int:
    """The plane_width of the rows: from the first to the last row that differ from the background."""
    return plane_width(a.T)


def plane_middle(a: 'np.ndarray[tuple[int, int], np.dtype[np.float64]]') -> tuple[float, float]:
    """The middle of the plane's bounding box: (column, row)."""
    columns, rows = plane_columns(a), plane_columns(a.T)
    return (columns[0] + columns[1]) / 2, (rows[0] + rows[1]) / 2


def transitions(a: 'np.ndarray[tuple[int, int], np.dtype[np.float64]]') -> int:
    """Dark-light changes along the middle row, inside the plane but 2 pixels from its edges (shaded darker), split
    halfway between its darkest and lightest; none on a row within 40 levels, which is shading, not a pattern."""
    first, last = plane_columns(a)
    row = a[a.shape[0] // 2, first + 2 : last - 1]
    if row.size < 2:
        return 0
    lo, hi = float(np.min(row)), float(np.max(row))
    if hi - lo < 40:
        return 0
    light = row > (lo + hi) / 2
    return int(np.count_nonzero(light[1:] != light[:-1]))


def difference(
    a: 'np.ndarray[tuple[int, int], np.dtype[np.float64]]', b: 'np.ndarray[tuple[int, int], np.dtype[np.float64]]'
) -> float:
    """The mean absolute difference in grey levels of two renders of one size; 255 for two sizes."""
    return float(np.abs(a - b).mean()) if a.shape == b.shape else 255.0


def say_failed(what: str, *shots: CallToolResult) -> None:
    """Prints, each on a line of its own, why a shot failed, or the sizes of two images of two sizes (difference()'s
    255.0): a check's detail is cut at 150 characters (common.check; REVIEW.md TST-334)."""
    for i, r in enumerate(shots, 1):
        if not is_image(r):
            print(
                '      %s: shot %d of %d failed: %s'
                % (what, i, len(shots), ' / '.join(line.strip() for line in text(r).strip().splitlines()))
            )
    sizes = {'%dx%d' % grey(r).shape[::-1] for r in shots if is_image(r)}
    if len(shots) == 2 and len(sizes) == 2:
        print(
            '      %s: the shots are of two sizes: %s px'
            % (what, ', '.join('%dx%d' % grey(r).shape[::-1] for r in shots))
        )
