"""What a 3D render shows of a mesh file of the user's own, for facts' checks of mesh files (ROADMAP item 84): its
pixels against the background, its two materials' colours, and its difference from another render."""

import numpy as np
from PIL import Image as PILImage

BACKGROUND = 25  # grey levels a mesh's pixel differs from the background by, at least
COLOURED = 60  # levels a red pixel's red is above its blue, or a blue pixel's blue above its red, at least


def _rgb(path: str) -> 'np.ndarray[tuple[int, int, int], np.dtype[np.float64]]':
    """The render saved at `path`, its R, G and B 0-255, rows by columns."""
    with PILImage.open(path) as im:
        return np.asarray(im.convert('RGB'), dtype=float)


def shown(path: str) -> float:
    """The share of the render's pixels a mesh covers: those whose grey differs from the top-left pixel's, the
    background's, by BACKGROUND levels or more."""
    grey = _rgb(path).mean(axis=2)
    return float((np.abs(grey - grey[0, 0]) >= BACKGROUND).mean())


def coloured(path: str) -> tuple[float, float]:
    """The share of the render's pixels that are red, and of those that are blue (COLOURED): the project's OBJ's two
    materials, `first` and `second` (assets/meshes/two_materials_box.mtl)."""
    rgb = _rgb(path)
    red, blue = rgb[..., 0], rgb[..., 2]
    return float((red - blue >= COLOURED).mean()), float((blue - red >= COLOURED).mean())


def apart(a: str, b: str) -> float:
    """The mean difference in grey levels of two renders; NaN for two sizes, so that no comparison holds."""
    one, two = _rgb(a).mean(axis=2), _rgb(b).mean(axis=2)
    return float(np.abs(one - two).mean()) if one.shape == two.shape else float('nan')
