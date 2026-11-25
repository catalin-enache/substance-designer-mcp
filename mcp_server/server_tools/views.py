"""Looking: preview_node, screenshot_designer, open_graph."""

import io
import os
import shutil
import tempfile
from typing import Annotated

from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image as PILImage
from pydantic import Field

from .core import (
    XY,
    Four,
    Graph,
    NoneIfEmpty,
    Output,
    _bridge,
    _checked,
    _helpers_call,
    _output_note_in,
    _tool,
    _with_undo,
)
from .functions import NO_PARAMETER
from .output import _load_8bit

# screenshot_designer('3d', zoom=...): wheel steps either way (their size: designer_helpers/view3d.py)
ZOOM_STEPS = 30
# screenshot_designer('3d', environment_rotation=..., environment_exposure=...): degrees and Exposure either way, the
# tool's own limits (Designer's fields: designer_helpers/view3d.py)
ENVIRONMENT_ROTATION = 180
ENVIRONMENT_EXPOSURE = 10
# the lines of a 3D shot that come beside its image, in the order printed: what was done to Designer's window, what was
# set up, and a render that may not have followed the set-up (designer_helpers/shot3d.py)
WINDOW = "Designer's window: "
NOTES = (WINDOW, '3D view: ', '3D render: ')


@_tool(read_only=False, destructive=False, idempotent=True, open_world=False)
def preview_node(
    node_id: Annotated[str, Field(description="The node's id: get node ids from describe_graph.")],
    graph: Graph = None,
    output: Output = None,
    max_size: Annotated[
        int, Field(description="The image's longest side in pixels, at most (a larger image is scaled down).")
    ] = 512,
) -> list[str | Image]:
    """Compute the graph in Designer and return the image produced by one node (any node, not
    just outputs).
    The call may add a temporary output node and delete it, within one undo step."""
    tmp_dir = tempfile.mkdtemp(prefix='sd_preview_')
    out_path = os.path.join(tmp_dir, 'node.png')
    try:
        # Wrapped in an undo step because a temporary output node may be added and removed
        text = _bridge(
            _with_undo(
                _helpers_call('save_node_output(%r, %r, %r, %r)' % (node_id, out_path, graph, output)),
                'Claude: preview node',
                edit=False,  # its step, a temporary node added and removed, changes nothing (core.py, SessionStep)
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


# a 3D shot that may be the view's last frame (the docstring): ROADMAP item 83
@_tool(read_only=False, destructive=False, idempotent=False, open_world=False)
def screenshot_designer(
    panel: Annotated[
        str,
        Field(
            description="window, graph, 2d, 3d, explorer, parameters, library or console. 'graph' is the node view "
            "alone (no title bar or toolbars). '3d' returns the 3D view's own render (material on the mesh). Inside "
            "'window' the 3D area doesn't show the render."
        ),
    ] = 'window',
    max_size: Annotated[
        int, Field(description="The image's longest side in pixels, at most (a larger image is scaled down).")
    ] = 1000,
    crop: Annotated[
        NoneIfEmpty[Four],
        Field(description='[left, top, right, bottom] as fractions 0-1 of the panel, applied before max_size.'),
    ] = None,
    graph: Annotated[
        str | None,
        Field(
            description="Puts that graph's outputs on the mesh, selecting it in the Explorer (outputs added to the "
            "graph open in the editor don't reach it by themselves; one with fewer than two outputs is refused: "
            'preview_node shows one).'
        ),
    ] = None,
    mesh: Annotated[
        str | None, Field(description="One of the 3D view's Scene menu (Plane, Sphere, Rounded cube...).")
    ] = None,
    view: Annotated[
        str | None, Field(description='Default, Front, Right, Back, Left, Top or Bottom, then framed.')
    ] = None,
    zoom: Annotated[
        int,
        Field(
            description='Wheel steps from where the camera is then, about 1.1x closer each (negative: away), so after '
            'pan it comes closer to what is in the middle.'
        ),
    ] = 0,
    tiling: Annotated[
        float | None,
        Field(
            description="How often the material repeats on the mesh (the user's Parameters panel then shows the graph "
            'in the editor).'
        ),
    ] = None,
    orbit: Annotated[
        NoneIfEmpty[XY],
        Field(
            description='[right, up] degrees the camera turns around the point it looks at (from Front, [90, 0] is '
            'Right, [0, 20] a low angle from above).'
        ),
    ] = None,
    pan: Annotated[
        NoneIfEmpty[XY],
        Field(
            description='[right, up] the camera moves sideways, in fractions of the view at that point (nearer parts '
            'move more).'
        ),
    ] = None,
    environment: Annotated[
        str | None,
        Field(
            description="One of Designer's environment maps (its Library's HDRI environments, such as "
            'studio_white_soft_light or studio_black_soft_light; an unknown name lists them).'
        ),
    ] = None,
    environment_rotation: Annotated[
        float | None,
        Field(
            description='The angle in degrees the environment is set to around the mesh, -180 to 180 (not added to '
            'the angle before, unlike orbit). Set it to see relief lit from the side.'
        ),
    ] = None,
    environment_exposure: Annotated[
        float | None,
        Field(description="The environment's Exposure, -10 to 10, higher brighter (Designer starts at 0)."),
    ] = None,
) -> list[str | Image]:
    """Capture Designer's own UI (never other apps). Shows what the user sees (node layout, 2D view, properties).
    open_graph(frame=... / node_ids=...) zooms the graph panel to a section first.
    '3d' goes through the clipboard: its text is put back, anything else on it may be lost. The 3D view draws only while Designer's window is on screen: on macOS '3d'
    puts a minimized, covered or hidden window there for the shot, transparent so the user doesn't see it, never
    taking focus, then puts it back as it was, and says so. It is left up if the user switched to Designer during
    the shot and Designer is still the app in front as it ends. Tell the user when the result says it left Designer's
    window up or in front. After a set-up that moved the camera, switched the
    mesh, or changed the tiling or the light, a render identical to the one before is said, and so is a 3D view that
    hadn't settled within 3 s: shoot again with no set-up (pan, orbit and zoom move from where the camera is).
    A 3D shot that doesn't show what the call set (the mesh, the view, the material) may be the view's last frame
    too. Shoot again with no set-up before judging it.
    '3d' can set up the view first with graph, mesh, view, orbit, pan, zoom, tiling and the light, and says what it set
    (stopped partway, the steps it began); it stays set, for later shots and in the user's view.
    Each wheel step waits for the 3D view to be at rest, then for its sign of taking the step; each drag waits for its
    sign. A step without them ends the camera's moves there: the result says which, and how long it waited. When a
    wheel step isn't sent, or the view hadn't settled within 3 s after a step, or hadn't by the render since the window
    came back with no step restarting it, the result also gives the view's count if below 8 (off screen, as last
    drawn) and what may hold it there: still refining, or the Rasterizer's Samples below 8 or its accumulation
    antialiasing off (Renderer > Edit settings). A shot where nothing of this happens says nothing of the count.
    The light (environment, environment_rotation, environment_exposure) goes through the Parameters panel, as tiling
    does.
    An image costs about width x height / 750 tokens (1000 x 700 is about 930), so keep
    max_size small and crop to what you need."""
    if crop is not None and (not all(0.0 <= v <= 1.0 for v in crop) or not (crop[0] < crop[2] and crop[1] < crop[3])):
        raise ToolError('crop is [left, top, right, bottom] as fractions 0-1, with left < right and top < bottom')
    options = {
        'graph': graph,
        'mesh': mesh,
        'view': view,
        'zoom': zoom or None,
        'tiling': tiling,
        'orbit': orbit if orbit and any(orbit) else None,  # 0 both ways: nothing to set, as zoom=0
        'pan': pan if pan and any(pan) else None,
        'environment': environment,
        # values Designer's fields are set to, 0 included: unlike a turn, pan or zoom of 0, not nothing to do
        'environment_rotation': environment_rotation,
        'environment_exposure': environment_exposure,
    }
    given = [name for name, value in options.items() if value not in (None, '')]
    if given and panel != '3d':
        raise ToolError("%s: these set up the 3D view, so they go with panel='3d'" % ', '.join(given))
    if not -ZOOM_STEPS <= zoom <= ZOOM_STEPS:
        raise ToolError('zoom is -%d to %d wheel steps (positive: closer), not %r' % (ZOOM_STEPS, ZOOM_STEPS, zoom))
    if tiling is not None and not tiling > 0:
        raise ToolError('tiling is how often the material repeats on the mesh: more than 0, not %r' % tiling)
    if orbit is not None and not (abs(orbit[0]) <= 180 and abs(orbit[1]) <= 90):
        raise ToolError(
            'orbit is [right, up] in degrees, -180 to 180 and -90 to 90 (negative: left, down), not %r' % list(orbit)
        )
    if pan is not None and not all(abs(v) <= 1 for v in pan):
        raise ToolError(
            'pan is [right, up] in fractions of the view, each -1 to 1 (negative: left, down), not %r' % list(pan)
        )
    if environment_rotation is not None and not abs(environment_rotation) <= ENVIRONMENT_ROTATION:
        raise ToolError(
            'environment_rotation is in degrees, -%d to %d, not %r'
            % (ENVIRONMENT_ROTATION, ENVIRONMENT_ROTATION, environment_rotation)
        )
    if environment_exposure is not None and not abs(environment_exposure) <= ENVIRONMENT_EXPOSURE:
        raise ToolError(
            "environment_exposure is the environment's Exposure, -%d to %d (Designer starts at 0), not %r"
            % (ENVIRONMENT_EXPOSURE, ENVIRONMENT_EXPOSURE, environment_exposure)
        )
    tmp_dir = tempfile.mkdtemp(prefix='sd_shot_')
    out_path = os.path.join(tmp_dir, 'shot.png')
    call = 'save_screenshot(%r, %r)' % (panel, out_path)
    if panel == '3d':  # Designer's window on screen through the set-up and the render (designer_helpers/shot3d.py)
        setup = (  # '': none
            *(out_path, graph or None, mesh or None, view or None, zoom, tiling, options['orbit'], options['pan']),
            *(environment or None, environment_rotation, environment_exposure),
        )
        call = 'shoot_3d(%s)' % ', '.join(map(repr, setup))
    try:
        text = _bridge(_helpers_call(call), timeout=120 if given else 60)
        lines = text.splitlines()
        window = [line for line in lines if line.startswith(WINDOW)]
        set_up = [line for line in lines if line.startswith('3D view: ')]
        begun = [line for line in lines if line.startswith('3D view, setting: ')]
        # an error after the set-up, or partway (an abort: the steps it began): the user's 3D view changed all the same,
        # and their window too
        said = ''.join('\n' + line for line in window + (set_up or begun))
        if not os.path.exists(out_path):
            raise ToolError((text.strip().splitlines()[-1] if text.strip() else 'screenshot failed') + said)
        im = PILImage.open(out_path).convert('RGB')
        if crop is not None:
            w, h = im.size
            box = (round(crop[0] * w), round(crop[1] * h), round(crop[2] * w), round(crop[3] * h))
            if box[2] - box[0] < 1 or box[3] - box[1] < 1:
                raise ToolError('crop %r is less than a pixel of the %dx%d panel%s' % (list(crop), w, h, said))
            im = im.crop(box)
        im.thumbnail((max_size, max_size))
        buf = io.BytesIO()
        im.save(buf, format='PNG')
        return [Image(data=buf.getvalue(), format='png'), *[line for line in lines if line.startswith(NOTES)]]
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@_tool(read_only=False, destructive=False, idempotent=True, open_world=False)
def open_graph(
    graph: Annotated[str, Field(description='The graph identifier.')],
    node_id: Annotated[
        str | None, Field(description="Centres the view on one node (Designer's own focus, zoomed in close).")
    ] = None,
    node_ids: Annotated[
        list[str] | None, Field(description='Fits the view to these nodes (their bounding box).')
    ] = None,
    frame: Annotated[str | None, Field(description="Fits the view to a frame, by the frame's title.")] = None,
    rect: Annotated[
        NoneIfEmpty[Four], Field(description='Fits the view to [x, y, width, height] in graph units.')
    ] = None,
    function: Annotated[
        str | None,
        Field(
            description="Opens a function graph of the graph's package instead, by identifier: node_id, node_ids, "
            'frame and rect then name its nodes and frames.'
        ),
    ] = None,
    parameter: Annotated[
        str | None,
        Field(
            description="A node's function on this parameter: refused, as Designer's editor opens the node's graph "
            'instead; describe_graph lists it.'
        ),
    ] = None,
) -> str:
    """Open a graph in Designer's graph editor (so the user and screenshot_designer see it;
    closes Designer's Home screen if it is showing). By default the whole graph is fitted in
    view. To look at one section, fit the view to a frame, to node_ids or to rect, with a little padding and
    at most 100 % zoom; it zooms in Designer's own wheel steps (1.2x), so the view may show up
    to one step more than the area. Or centre it on node_id. Prints the zoom and the visible area in graph units; "could not fit" instead of "fitted" when the
    view can't show the whole area (Designer's zoom stops at 5 %). With function, it opens a function graph of the
    package the same way. A node's function can't be opened (Designer's editor opens the node's graph instead):
    describe_graph lists it."""
    if parameter:  # with node_id or without, as either would be refused next (REVIEW.md SRV-206)
        raise ToolError(
            NO_PARAMETER
            if function
            else "Designer's editor can't open a node's function: openResourceInEditor opens the node's graph "
            'instead. describe_graph(graph=%r, node_id=%s, parameter=%r) lists its nodes, or the user opens it in '
            'Designer.' % (graph, repr(node_id) if node_id else "<the node's id>", parameter)
        )
    chosen = [
        name
        for name, value in (('node_id', node_id), ('node_ids', node_ids), ('frame', frame), ('rect', rect))
        if value not in (None, '', [])
    ]
    if len(chosen) > 1:
        raise ToolError('choose one of node_id, node_ids, frame or rect (got %s)' % ', '.join(chosen))
    return _checked(
        # '' or [] is no choice, as above: sent as one, frame='' was looked for as a title (REVIEW.md SRV-180)
        _bridge(
            _helpers_call(
                'open_graph(%r, %r, %r, %r, %r, %r)'
                % (graph, node_id or None, node_ids or None, frame or None, rect, function or None)
            ),
            timeout=60,
        )
    )
