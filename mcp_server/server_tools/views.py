"""Looking: preview_node, screenshot_designer, open_graph."""

import io
import os
import shutil
import tempfile

from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image as PILImage

from .core import _bridge, _checked, _helpers_call, _output_note_in, _tool, _with_undo
from .output import _load_8bit

# screenshot_designer('3d', zoom=...): wheel steps either way (their size: designer_helpers/view3d.py)
ZOOM_STEPS = 30


@_tool()
def preview_node(
    node_id: str, graph: str | None = None, output: str | None = None, max_size: int = 512
) -> list[str | Image]:
    """Compute the graph in Designer and return the image produced by one node (any node, not
    just outputs). Get node ids from describe_graph. `output` picks a connector on multi-output
    nodes (default: the one tagged base colour, else the first; the result says which). `graph` defaults to the graph open in Designer's UI."""
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
        note = _output_note_in(text)
        return [Image(data=buf.getvalue(), format='png'), *([note] if note else [])]
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@_tool()
def screenshot_designer(
    panel: str = 'window',
    max_size: int = 1000,
    crop: list[float] | None = None,
    graph: str | None = None,
    mesh: str | None = None,
    view: str | None = None,
    zoom: int = 0,
    tiling: float | None = None,
) -> list[str | Image]:
    """Capture Designer's own UI (never other apps): panel = window, graph, 2d, 3d, explorer,
    parameters, library or console. Shows what the user sees (node layout, 2D view, properties).
    'graph' is the node view alone (no title bar or toolbars); open_graph(frame=... / node_ids=...)
    zooms it to a section first. '3d' returns the 3D view's own render (material on the mesh);
    it goes through the clipboard: its text is put back, anything else on it may be lost. Inside 'window' the
    3D area doesn't show the render.
    '3d' can set up the view first and says what it set (stopped partway, the steps it began); it stays set, for
    later shots and in the user's view:
    graph puts that graph's outputs on the mesh, selecting it in the Explorer (outputs added to the graph open
    in the editor don't reach it by themselves; one with fewer than two outputs is refused:
    preview_node shows one); mesh is one of the 3D view's Scene menu (Plane, Sphere, Rounded cube...); view:
    Default, Front, Right, Back, Left, Top or Bottom, then framed; zoom: wheel steps from where the camera is
    (after view, from the framed view), about 1.1x closer each (negative: away); tiling: how often the material
    repeats on the mesh (the user's Parameters panel then shows the graph in the editor).
    crop: [left, top, right, bottom] as fractions 0-1 of the panel, applied before max_size.
    An image costs about width x height / 750 tokens (1000 x 700 is about 930), so keep
    max_size small and crop to what you need."""
    if crop is not None and (
        len(crop) != 4 or not all(0.0 <= float(v) <= 1.0 for v in crop) or not (crop[0] < crop[2] and crop[1] < crop[3])
    ):
        raise ToolError('crop is [left, top, right, bottom] as fractions 0-1, with left < right and top < bottom')
    options = {'graph': graph, 'mesh': mesh, 'view': view, 'zoom': zoom or None, 'tiling': tiling}
    given = [name for name, value in options.items() if value not in (None, '')]
    if given and panel != '3d':
        raise ToolError("%s: these set up the 3D view, so they go with panel='3d'" % ', '.join(given))
    if not -ZOOM_STEPS <= zoom <= ZOOM_STEPS:
        raise ToolError('zoom is -%d to %d wheel steps (positive: closer), not %r' % (ZOOM_STEPS, ZOOM_STEPS, zoom))
    if tiling is not None and not tiling > 0:
        raise ToolError('tiling is how often the material repeats on the mesh: more than 0, not %r' % tiling)
    tmp_dir = tempfile.mkdtemp(prefix='sd_shot_')
    out_path = os.path.join(tmp_dir, 'shot.png')
    call = 'save_screenshot(%r, %r)' % (panel, out_path)
    if given:
        call = 'set_3d_view(%r, %r, %r, %r, %r); %s' % (graph or None, mesh, view, zoom, tiling, call)
    try:
        text = _bridge(_helpers_call(call), timeout=120 if given else 60)
        set_up = [line for line in text.splitlines() if line.startswith('3D view: ')]
        begun = [line for line in text.splitlines() if line.startswith('3D view, setting: ')]
        # an error after the set-up, or partway (an abort: the steps it began): the user's 3D view changed all the same
        said = ''.join('\n' + line for line in set_up or begun)
        if not os.path.exists(out_path):
            raise ToolError((text.strip().splitlines()[-1] if text.strip() else 'screenshot failed') + said)
        im = PILImage.open(out_path).convert('RGB')
        if crop is not None:
            w, h = im.size
            box = (round(crop[0] * w), round(crop[1] * h), round(crop[2] * w), round(crop[3] * h))
            if box[2] - box[0] < 1 or box[3] - box[1] < 1:
                raise ToolError('crop %r is less than a pixel of the %dx%d panel%s' % (crop, w, h, said))
            im = im.crop(box)
        im.thumbnail((max_size, max_size))
        buf = io.BytesIO()
        im.save(buf, format='PNG')
        return [Image(data=buf.getvalue(), format='png'), *set_up]
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
    close). Prints the zoom and the visible area in graph units; "could not fit" instead of "fitted" when the
    view can't show the whole area (Designer's zoom stops at 5 %)."""
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
