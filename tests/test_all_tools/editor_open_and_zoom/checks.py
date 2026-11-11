"""The editor: open_graph's targets and zoom, and screenshot_designer('graph') with crops."""

import re
from collections.abc import Sequence

from test_all_tools.common import (
    TEST_GRAPH,
    Ctx,
    check,
    designer_script,
    image_size,
    is_image,
    text,
)


async def run(ctx: Ctx) -> None:
    """open_graph targets and zoom, and the graph screenshot with crops."""
    c, G, clouds, slope = ctx.c, ctx.G, ctx.clouds, ctx.slope
    # --- editor + screenshots
    t = text(await c('open_graph', {'graph': TEST_GRAPH, 'node_id': slope}))
    check('open_graph', 'open + focus', 'focused node' in t, t)
    r_ = await c('open_graph', {'graph': 'no_such_graph'})
    check('open_graph', 'error on unknown graph', r_.is_error and 'not found' in text(r_), '')

    def visible(t: str) -> tuple[int | None, list[int] | None]:
        m = re.search(r'zoom (\d+)%, visible (-?\d+),(-?\d+) to (-?\d+),(-?\d+)', t)
        return (int(m.group(1)), [int(v) for v in m.groups()[1:]]) if m else (None, None)

    def contains(box: list[int] | None, points: Sequence[tuple[float, float]]) -> bool:
        return (
            box is not None and bool(points) and all(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in points)
        )

    t = text(await designer_script(c, 'editor_open_and_zoom/frame_bounds', graph=TEST_GRAPH))
    # no match raises AttributeError, which the run's except reports (REVIEW.md TST-63)
    fx0, fy0, fx1, fy1 = [int(v) for v in re.search(r'FRAME=(-?\d+),(-?\d+),(-?\d+),(-?\d+)', t).groups()]  # type: ignore[union-attr]
    t = text(await c('open_graph', {'graph': TEST_GRAPH, 'frame': 'shape'}))  # title, any case
    zoom, box = visible(t)
    check(
        'open_graph',
        'frame fits in view',
        "fitted frame 'Shape'" in t and zoom is not None and zoom <= 100 and contains(box, [(fx0, fy0), (fx1, fy1)]),
        t,
    )
    shape_nodes = [clouds, slope]
    points = [
        (float(x), float(y))
        for x, y in re.findall(
            r'^\d+ \S+ @\((-?[\d.]+),(-?[\d.]+)\)',
            text(await c('describe_graph', {'node_ids': shape_nodes, **G})),
            re.M,
        )
    ]
    t = text(await c('open_graph', {'graph': TEST_GRAPH, 'node_ids': shape_nodes}))
    zoom, box = visible(t)
    check(
        'open_graph',
        'node_ids fit their bounding box',
        'fitted 2 node(s)' in t and len(points) == 2 and contains(box, points),
        t,
    )
    t = text(await c('open_graph', {'graph': TEST_GRAPH, 'rect': [0, 0, 10, 10]}))
    zoom, box = visible(t)
    check(
        'open_graph',
        'rect, zoom capped at 100%',
        zoom is not None and 100 / 1.2 <= zoom <= 100 and contains(box, [(0, 0), (10, 10)]),
        t,
    )
    # the fit zooms through Designer's own wheel handling, so the user's next wheel step
    # continues from the fitted zoom (setting the view's transform directly made it jump)
    t = text(await designer_script(c, 'editor_open_and_zoom/wheel_step'))
    step = re.search(r'STEP=([\d.]+)', t)
    check(
        'open_graph',
        'a wheel step after a fit continues from the fitted zoom',
        step is not None and abs(float(step.group(1)) - 1.2) < 0.01,
        t.strip(),
    )
    # an area too big for Designer's smallest zoom (5 %) isn't reported as fitted (REVIEW.md HLP-56)
    t = text(await c('open_graph', {'graph': TEST_GRAPH, 'rect': [0, 0, 100000, 100000]}))
    zoom, box = visible(t)
    check(
        'open_graph',
        "says when an area doesn't fit",
        'could not fit rect' in t and 'fitted' not in t and zoom == 5 and not contains(box, [(0, 0), (100000, 100000)]),
        t,
    )
    # an area in view at that zoom is fitted, though its padding wouldn't be (HLP-59)
    width = 0.95 * (box[2] - box[0]) if box else 0.0
    t = text(await c('open_graph', {'graph': TEST_GRAPH, 'rect': [0, 0, width, 10]}))
    zoom, box = visible(t)
    check(
        'open_graph',
        'an area in view at the smallest zoom counts as fitted',
        'fitted rect' in t and zoom == 5 and contains(box, [(0, 0), (width, 10)]),
        t,
    )
    r_ = await c('open_graph', {'graph': TEST_GRAPH, 'node_id': slope, 'frame': 'Shape'})
    check(
        'open_graph',
        'refuses two view targets at once',
        r_.is_error and 'choose one of' in text(r_) and 'node_id, frame' in text(r_),
        text(r_),
    )
    r_ = await c('open_graph', {'graph': TEST_GRAPH, 'node_ids': ['graph']})
    check(
        'open_graph',
        'node_ids never means the graph itself',
        r_.is_error and "node 'graph' not found" in text(r_),
        text(r_),
    )
    r_ = await c('open_graph', {'graph': TEST_GRAPH, 'frame': 'no such frame'})
    check('open_graph', 'error on unknown frame lists the frames', r_.is_error and "'Shape'" in text(r_), text(r_))
    # 'graph' captures the node view alone (no title bar, no toolbars); crop takes a part of it
    full = await c('screenshot_designer', {'panel': 'graph', 'max_size': 4000})
    t = text(await designer_script(c, 'editor_open_and_zoom/graph_view_size'))
    sizes = re.search(r'VIEW=(\d+),(\d+) DOCK=(\d+),(\d+)', t)
    view_size = (int(sizes.group(1)), int(sizes.group(2))) if sizes else None
    check(
        'screenshot_designer',
        'graph is the node view, without toolbars',
        is_image(full) and sizes and image_size(full) == view_size and int(sizes.group(4)) > view_size[1],
        '%s vs %s' % (image_size(full) if is_image(full) else text(full), t.strip()[-120:]),
    )
    part = await c('screenshot_designer', {'panel': 'graph', 'max_size': 4000, 'crop': [0, 0, 0.5, 0.25]})
    check(
        'screenshot_designer',
        'crop',
        is_image(part)
        and view_size is not None
        and image_size(part) == (round(view_size[0] * 0.5), round(view_size[1] * 0.25)),
        str(image_size(part)) if is_image(part) else text(part),
    )
    r_ = await c('screenshot_designer', {'panel': 'graph', 'crop': [0, 0, 0.0001, 1]})
    check(
        'screenshot_designer',
        'error on a crop under a pixel',
        r_.is_error and 'less than a pixel' in text(r_),
        text(r_),
    )
    r_ = await c('screenshot_designer', {'panel': 'graph', 'crop': [0.5, 0, 0.2, 1]})
    check('screenshot_designer', 'error on a bad crop', r_.is_error and 'left < right' in text(r_), text(r_))
