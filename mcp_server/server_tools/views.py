"""Looking: preview_node, screenshot_designer, open_graph."""

import io
import os
import shutil
import tempfile

from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image as PILImage

from .core import _bridge, _checked, _helpers_call, _tool, _with_undo
from .output import _load_8bit


@_tool()
def preview_node(node_id: str, graph: str | None = None, output: str | None = None, max_size: int = 512) -> Image:
    """Compute the graph in Designer and return the image produced by one node (any node, not
    just outputs). Get node ids from describe_graph. `output` picks a connector on multi-output
    nodes (default: first). `graph` defaults to the graph open in Designer's UI."""
    tmp_dir = tempfile.mkdtemp(prefix='sd_preview_')
    out_path = os.path.join(tmp_dir, 'node.png')
    try:
        # Wrapped in an undo step because a temporary output node may be added and removed
        text = _bridge(
            _with_undo(
                _helpers_call('save_node_output(%r, %r, %r, %r)' % (node_id, out_path, graph, output)),
                'Claude: preview node',
            ),
            '<preview_node>',
            300,
        )
        if not os.path.exists(out_path):
            # Keep only the final error line(s) from Designer's traceback
            raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'preview failed')
        im = _load_8bit(out_path)
        im.thumbnail((max_size, max_size))
        buf = io.BytesIO()
        im.save(buf, format='PNG')
        return Image(data=buf.getvalue(), format='png')
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@_tool()
def screenshot_designer(panel: str = 'window', max_size: int = 1000, crop: list[float] | None = None) -> Image:
    """Capture Designer's own UI (never other apps): panel = window, graph, 2d, 3d, explorer,
    parameters, library or console. Shows what the user sees (node layout, 2D view, properties).
    'graph' is the node view alone (no title bar or toolbars); open_graph(frame=... / node_ids=...)
    zooms it to a section first. '3d' returns the 3D view's own render (material on the mesh);
    the user's clipboard is restored afterwards. Inside 'window' the 3D area doesn't show the render.
    crop: [left, top, right, bottom] as fractions 0-1 of the panel, applied before max_size.
    An image costs about width x height / 750 tokens (1000 x 700 is about 930), so keep
    max_size small and crop to what you need."""
    if crop is not None and (
        len(crop) != 4 or not all(0.0 <= float(v) <= 1.0 for v in crop) or not (crop[0] < crop[2] and crop[1] < crop[3])
    ):
        raise ToolError('crop is [left, top, right, bottom] as fractions 0-1, with left < right and top < bottom')
    tmp_dir = tempfile.mkdtemp(prefix='sd_shot_')
    out_path = os.path.join(tmp_dir, 'shot.png')
    try:
        text = _bridge(_helpers_call('save_screenshot(%r, %r)' % (panel, out_path)), timeout=60)
        if not os.path.exists(out_path):
            raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'screenshot failed')
        im = PILImage.open(out_path).convert('RGB')
        if crop is not None:
            w, h = im.size
            box = (round(crop[0] * w), round(crop[1] * h), round(crop[2] * w), round(crop[3] * h))
            if box[2] - box[0] < 1 or box[3] - box[1] < 1:
                raise ToolError('crop %r is less than a pixel of the %dx%d panel' % (crop, w, h))
            im = im.crop(box)
        im.thumbnail((max_size, max_size))
        buf = io.BytesIO()
        im.save(buf, format='PNG')
        return Image(data=buf.getvalue(), format='png')
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@_tool()
def open_graph(
    graph: str,
    node_id: str | None = None,
    node_ids: list[str] | None = None,
    frame: str | None = None,
    rect: list[float] | None = None,
) -> str:
    """Open a graph in Designer's graph editor (so the user and screenshot_designer see it;
    closes Designer's Home screen if it is showing). By default the whole graph is fitted in
    view. To look at one section, fit the view to a frame (its title), to node_ids (their
    bounding box) or to rect ([x, y, width, height] in graph units), with a little padding and
    at most 100 % zoom; it zooms in Designer's own wheel steps (1.2x), so the view may show up
    to one step more than the area. node_id centres the view on one node (Designer's own focus, zoomed in
    close). Prints the zoom and the visible area in graph units."""
    chosen = [
        name
        for name, value in (('node_id', node_id), ('node_ids', node_ids), ('frame', frame), ('rect', rect))
        if value not in (None, '', [])
    ]
    if len(chosen) > 1:
        raise ToolError('choose one of node_id, node_ids, frame or rect (got %s)' % ', '.join(chosen))
    if rect is not None and len(rect) != 4:
        raise ToolError('rect is [x, y, width, height] in graph units')
    return _checked(
        _bridge(_helpers_call('open_graph(%r, %r, %r, %r, %r)' % (graph, node_id, node_ids, frame, rect)), timeout=60)
    )
