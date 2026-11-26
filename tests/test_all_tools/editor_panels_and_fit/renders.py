"""What the 3D view checks measure in a render of a checker on a plane seen from the top: the plane's width, height and
middle (a square from straight above), how far it moved between two renders, and how often a row near its middle (the
most of three) turns from dark to light (twice per square: tiling 2 doubles it). And a shot that waits for the checker
on the mesh (with_checker), and the user's own view set to show it (users_checker)."""

import base64
import io
import os
import time
from textwrap import dedent

import numpy as np
from mcp.types import CallToolResult
from PIL import Image as PILImage

from test_all_tools.common import Call, ToolArgs, is_image, text
from test_all_tools.editor_panels_and_fit.preparations import VIEW3D_GRAPH

# dark-light changes that show the checker on the mesh: with it 11 to 30, with the default material 1 at most, in each
# kind of shot the checks take (measured 2026-11-13: a rounded cube from the Front and the Top, a plane from the
# Default angle and the Top, zoomed out, a sphere)
CHECKER = 6
# s shots are retaken while the checker doesn't show, each as the one before returns: in a full run, the unit suite
# beside the workers, the 3D shots once didn't follow the camera for about 20 s, the cause unknown (REVIEW.md TST-383,
# TST-388). A limit: each shot waits for the 3D view itself (designer_helpers/frames3d.py; TST-421)
RETAKE_S = 30

# the user's own view set through the 3D view's menus, as a user sets it, Designer's window on screen as a 3D shot puts
# it: the outputs of graph %r on the mesh (None: as they are), then a Plane from the Top, framed. A set-up shot leaves no
# view of its own: each call starts from the view the user left, and puts it back (designer_helpers/scene3d.py)
USERS_PLANE_TOP = dedent("""
    mw = _main_window()
    bar = _3d_dock(mw).findChildren(QtWidgets.QMenuBar)[0]
    keep = [mw, bar]
    frames = _frames_of(mw, _viewport(_3d_dock(mw)))
    shown = %r
    try:
        with _on_screen(mw, frames) as screen:
            if shown is not None:
                g = find_graph(shown)
                with _Waiting(frames):
                    g.compute()  # its outputs ready for the mesh
                    _apply_outputs(_explorer_tree(mw, keep), g, keep)
            plane = _menu_action(bar, keep, 'Scene', 'Plane')
            if not plane.isChecked():  # checked, it is shown already, and picked again it restarts nothing
                with _Waiting(frames):
                    plane.trigger()
            since = frames.mark()
            _menu_action(bar, keep, 'Camera', 'Top').trigger()
            frames.moved(since)  # Frame at once cancels the turn
            screen.again()
            with _Waiting(frames):
                _menu_action(bar, keep, 'Camera', 'Frame').trigger()
    finally:
        frames.close()""")


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


def say_renders(*renders: tuple[str, str]) -> None:
    """Prints, for each render saved, given as (name, path), on a line of its own: its plane's width in the render's
    width, which gives its zoom, its mean grey and its path. A render with no plane edge (plane_columns: no column 25
    levels from its corner) is all plane or all background: its mean grey tells which. For a check that failed: a
    check's detail is cut at 150 characters (common.check), and the renders stay with its scratch folder
    (__main__.one_run). A render not saved is said so, with its path (REVIEW.md TST-688)."""
    for name, path in renders:
        if not os.path.exists(path):
            print('      %s: not saved: %s' % (name, path))
            continue
        a = grey_file(path)
        width = plane_width(a)
        plane = (
            'the plane %d px wide of %d' % (width, a.shape[1]) if width else 'no plane edge in its %d px' % a.shape[1]
        )
        print('      %s: %s, mean grey %.1f: %s' % (name, plane, a.mean(), path))


async def with_checker(c: Call, args: ToolArgs) -> CallToolResult:
    """screenshot_designer with `args`, then retaken with them, each retake as the shot before returns, until the
    checker shows on the mesh (CHECKER), RETAKE_S at most: each call starts from the view the user left, so a retake
    sets the view up again (designer_helpers/scene3d.py). What the checks measure needs the checker. Once, after a call
    that switched the mesh and applied a graph, the shots didn't follow the camera for about 20 s (RETAKE_S). Says how
    many retakes it took, or that the checker never showed. Returns the last shot, the checker on it or not. A shot
    that failed is returned at once."""
    start = _now()
    r = await c('screenshot_designer', args)
    retakes = 0
    while is_image(r) and transitions(grey(r)) < CHECKER and _now() - start < RETAKE_S:
        r = await c('screenshot_designer', args)
        retakes += 1
    if retakes:
        shown = is_image(r) and transitions(grey(r)) >= CHECKER
        print('      the checker %s on the mesh after %d retakes' % ('showed' if shown else "didn't show", retakes))
    return r


async def users_checker(c: Call, helpers: str, shot: ToolArgs) -> CallToolResult:
    """The user's own view, for the checks that change it or shoot it with nothing set up: VIEW3D_GRAPH's checker on a
    Plane from the Top, framed, set through the 3D view's menus (USERS_PLANE_TOP, run with the helpers' text `helpers`).
    Returns the shot `shot`, with nothing set up, retaken until the checker shows (with_checker)."""
    await c('execute_designer_code', {'code': helpers + USERS_PLANE_TOP % VIEW3D_GRAPH})
    return await with_checker(c, shot)
