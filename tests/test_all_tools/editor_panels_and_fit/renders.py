"""What the 3D view checks measure in a render of a checker on a plane seen from the top: the plane's width, height and
middle (a square from straight above), how far it moved between two renders, and how often a row near its middle (the
most of three) turns from dark to light (twice per square: tiling 2 doubles it). And a shot that waits for the checker
on the mesh (with_checker)."""

import base64
import io
import time

import numpy as np
from mcp.types import CallToolResult
from PIL import Image as PILImage

from test_all_tools.common import Call, JsonSent, ToolArgs, is_image, text

# dark-light changes that show the checker on the mesh: with it 11 to 30, with the default material 1 at most, in each
# kind of shot the checks take (measured 2026-11-13: a rounded cube from the Front and the Top, a plane from the
# Default angle and the Top, zoomed out, a sphere)
CHECKER = 6
# s shots are retaken while the checker doesn't show, each as the one before returns: in a full run, the unit suite
# beside the workers, the 3D shots once didn't follow the camera for about 20 s, the cause unknown (REVIEW.md TST-383,
# TST-388). A limit: each shot waits for the 3D view itself (designer_helpers/frames3d.py; TST-421)
RETAKE_S = 30


def _now() -> float:
    return time.monotonic()


def grey(r: CallToolResult) -> 'np.ndarray[tuple[int, int], np.dtype[np.float64]]':
    """The result's image as grey levels 0-255, rows by columns."""
    data = next(c.data for c in r.content if c.type == 'image')
    with PILImage.open(io.BytesIO(base64.b64decode(data))) as im:
        return np.asarray(im.convert('L'), dtype=float)


def grey_file(path: str) -> 'np.ndarray[tuple[int, int], np.dtype[np.float64]]':
    """The image saved at `path` as grey levels 0-255, rows by columns, as grey() reads a result's."""
    with PILImage.open(path) as im:
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


def moved_left(
    before: 'np.ndarray[tuple[int, int], np.dtype[np.float64]]',
    after: 'np.ndarray[tuple[int, int], np.dtype[np.float64]]',
) -> float:
    """How far the plane's middle moved left from `before` to `after`, as a fraction of each render's own width: a
    tool's shot is shrunk to max_size, a render saved by shoot_3d isn't (REVIEW.md TST-396)."""
    return plane_middle(before)[0] / before.shape[1] - plane_middle(after)[0] / after.shape[1]


def transitions(a: 'np.ndarray[tuple[int, int], np.dtype[np.float64]]') -> int:
    """Dark-light changes along a row, inside the plane but 2 pixels from its edges (shaded darker), split halfway
    between its darkest and lightest; none on a row within 40 levels, which is shading, not a pattern. The most of the
    middle row and the rows 3 pixels either way: a render blends two rows of squares into one grey along their edge
    (REVIEW.md TST-395)."""
    first, last = plane_columns(a)
    middle = a.shape[0] // 2
    return max(_row_transitions(a[y, first + 2 : last - 1]) for y in (middle - 3, middle, middle + 3))


def _row_transitions(row: 'np.ndarray[tuple[int], np.dtype[np.float64]]') -> int:
    """transitions() along one row."""
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
    """The mean absolute difference in grey levels of two renders of one size. NaN for two sizes: no comparison with
    it holds, so neither a change nor its absence passes (REVIEW.md TST-540: 255 passed every "the render changed").
    min() and max() may drop a NaN: compare with the difference itself."""
    return float(np.abs(a - b).mean()) if a.shape == b.shape else float('nan')


def say_failed(what: str, *shots: CallToolResult) -> None:
    """Prints, each on a line of its own, why a shot failed, or the sizes of two images of two sizes (difference()'s
    NaN): a check's detail is cut at 150 characters (common.check; REVIEW.md TST-334)."""
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


async def with_checker(c: Call, args: ToolArgs) -> CallToolResult:
    """screenshot_designer with `args`, then retaken as the 3D view is, each retake as the shot before returns, until
    the checker shows on the mesh (CHECKER), RETAKE_S at most. What the checks measure needs the checker. Once, after a
    call that switched the mesh and applied a graph, the shots didn't follow the camera for about 20 s (RETAKE_S);
    shots after a call doing one of them wait too, as a defence. Says how many retakes it took, or that the checker
    never showed. Returns the last shot, the checker on it or not, with the first shot's text: what the call set, which
    a retake doesn't say. A shot that failed is returned at once."""
    start = _now()
    first = r = await c('screenshot_designer', args)
    again: dict[str, JsonSent] = {key: args[key] for key in ('panel', 'max_size') if key in args}
    retakes = 0
    while is_image(r) and transitions(grey(r)) < CHECKER and _now() - start < RETAKE_S:
        r = await c('screenshot_designer', again)
        retakes += 1
    if retakes:
        shown = is_image(r) and transitions(grey(r)) >= CHECKER
        print('      the checker %s on the mesh after %d retakes' % ('showed' if shown else "didn't show", retakes))
        if is_image(r):  # two checks read what the call set (REVIEW.md TST-384)
            r.content = [part for part in r.content if part.type != 'text'] + [
                part for part in first.content if part.type == 'text'
            ]
    return r
