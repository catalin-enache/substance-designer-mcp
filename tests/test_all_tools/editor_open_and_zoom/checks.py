"""The editor: open_graph's targets and zoom, screenshot_designer('graph') with crops, describe_graph's reading of the
editor's selection, the Parameters panel as setSelected selects and a package is unloaded, and parentItem() on the graph
view's items."""

import asyncio
import re
from collections.abc import Sequence

from test_all_tools.common import (
    POLL_S,
    TEST_GRAPH,
    Ctx,
    check,
    designer_script,
    expect,
    image_size,
    is_image,
    positions,
    said,
    skip,
    text,
)


async def run(ctx: Ctx) -> None:
    """open_graph targets and zoom, the graph screenshot with crops, and describe_graph of the editor's selection, with
    the Designer facts of the Parameters panel, parentItem and the selection getters."""
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
    # REVIEW.md SRV-180: '' for frame is not given, as for every optional name (SRV-147); it looked for a frame titled ''
    t = text(await c('open_graph', {'graph': TEST_GRAPH, 'node_ids': shape_nodes, 'frame': ''}))
    check('open_graph', 'an empty frame is not given: node_ids fit', 'fitted 2 node(s)' in t, t)
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
        is_image(full) and sizes is not None and image_size(full) == view_size and int(sizes.group(4)) > view_size[1],
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
    await check_describe_graph_lists_the_editors_selection(ctx)
    await check_describe_graph_refuses_a_function_graph_in_front(ctx)
    # these three last: each leaves no graph in the editor
    await check_set_selected_leaves_the_parameters_panel_alone(ctx)
    await check_parent_item_hands_a_scene_item_to_python(ctx)
    await check_what_the_selection_getters_give(ctx)


async def check_describe_graph_lists_the_editors_selection(ctx: Ctx) -> None:
    """describe_graph(selected=True) lists the nodes selected in the editor, one of the graph's two here, and names a
    frame selected too, takes the editor's graph by name, refuses another, and says when nothing is selected. The nodes
    are selected through the graph view, as a person would, since the API can't select."""
    c, G, clouds, slope = ctx.c, ctx.G, ctx.clouds, ctx.slope
    await c('open_graph', G)
    try:
        chosen = text(await designer_script(c, 'editor_open_and_zoom/select_items', nodes=[slope], frames=['Shape']))
        listed = text(await c('describe_graph', {'selected': True}))
        # REVIEW.md TST-808: one of the graph's two nodes, so that a listing of every node fails
        the_selection = set(positions(listed)) == {slope} and listed.rstrip().endswith("also selected: frame 'Shape'")
        check(
            'describe_graph',
            'selected lists only the node selected in the editor, then the frame selected too',
            the_selection,
            chosen.strip() + ' | ' + listed,
        )
        given = text(await c('describe_graph', {'selected': True, **G}))
        check('describe_graph', "selected takes the editor's graph by name", the_selection and given == listed, given)
        r_ = await c('describe_graph', {'selected': True, 'graph': 'mcp_selftest_elsewhere'})
        check(
            'describe_graph',
            'selected refuses another graph, naming the one in the editor and open_graph',
            r_.is_error
            and "which is '%s', not 'mcp_selftest_elsewhere'" % TEST_GRAPH in text(r_)
            and 'open_graph' in text(r_),
            text(r_),
        )
        r_ = await c('describe_graph', {'selected': True, 'node_ids': [clouds]})
        check('describe_graph', 'selected refuses node_ids', r_.is_error and 'takes no node_ids' in text(r_), text(r_))
    finally:
        await designer_script(c, 'editor_open_and_zoom/select_items', nodes=[], frames=[])
    t = text(await c('describe_graph', {'selected': True}))
    check(
        'describe_graph',
        'selected says in one line that nothing is selected',
        t.strip() == 'graph %s: nothing selected in the editor' % TEST_GRAPH,
        t,
    )


async def check_describe_graph_refuses_a_function_graph_in_front(ctx: Ctx) -> None:
    """describe_graph(selected=True) refuses plainly with a function graph of the package in the editor, which
    openResourceInEditor makes the current graph (GUIDE.md, Designer UI)."""
    c, G = ctx.c, ctx.G
    await c('set_function', {'function': 'selection_probe', 'expression': '1.0', **G})
    try:
        await c('open_graph', {'function': 'selection_probe', **G})
        r_ = await c('describe_graph', {'selected': True})
        check(
            'describe_graph',
            'selected refuses plainly with a function graph in the editor',
            r_.is_error
            and "The graph open in Designer's editor (selection_probe) is not a compositing graph" in text(r_),
            text(r_),
        )
    finally:
        await c('open_graph', G)


# What parameters_panel_facts.py prints for each case, after `<case> | `
PANEL_GRAPH = 'mcp_selftest_panel'
PANEL_OTHER = PANEL_GRAPH + '_other'


def _shown(scene: int, panel: str) -> str:
    """A case's line: the script's graph stays in the editor throughout."""
    return 'editor=%s scene=%d panel=%s' % (PANEL_GRAPH, scene, panel)


WHAT_THE_PANEL_SHOWS = {
    'the graph opened': _shown(0, PANEL_GRAPH),
    'from the graph, a node': _shown(1, PANEL_GRAPH),
    'from the graph, a dot': _shown(1, PANEL_GRAPH),
    'from the graph, a frame': _shown(1, PANEL_GRAPH),
    'from the graph, a comment': _shown(1, PANEL_GRAPH),
    'from the graph, cleared': _shown(0, PANEL_GRAPH),
    'the other graph selected in the Explorer': _shown(0, PANEL_OTHER),
    'from the other graph, a node': _shown(1, PANEL_OTHER),
    'from the other graph, a dot': _shown(1, PANEL_OTHER),
    'from the other graph, a frame': _shown(1, PANEL_OTHER),
    'from the other graph, a comment': _shown(1, PANEL_OTHER),
    'from the other graph, cleared': _shown(0, PANEL_OTHER),
}


async def check_set_selected_leaves_the_parameters_panel_alone(ctx: Ctx) -> None:
    """setSelected on a node's, a Dot's, a frame's and a comment's scene item, and clearSelection(), leave the
    Parameters panel on what it showed, and unloading a package leaves the panel on its graph (GUIDE.md, Designer UI).
    The script reads the panel in a package of its own, from the panel on the graph in the editor, then from the panel
    on another graph, which the Explorer's selection turns it to. It unloads the package with its graph in the editor,
    which leaves no graph there. Then it selects the self-test's graph in the Explorer, which turns the panel to it."""
    c = ctx.c
    t = text(await designer_script(c, 'editor_open_and_zoom/parameters_panel_facts', graph=TEST_GRAPH))
    expect(
        t,
        'setSelected and clearSelection() leave the Parameters panel as it was (GUIDE.md, Designer UI)',
        WHAT_THE_PANEL_SHOWS,
    )
    expect(
        t,
        'unloading a package leaves the Parameters panel on its graph, and setExplorerSelection of a graph still loaded '
        'turns it to that graph (GUIDE.md, Designer UI)',
        {'the package unloaded': 'panel=%s' % PANEL_GRAPH, 'panel left': TEST_GRAPH},
    )


def _panel_left(t: str, script: str) -> None:
    """The script's line `panel left | <title>`: once it has unloaded its package, it selects the self-test's graph in
    the Explorer, which turns the Parameters panel off that package, as the Parameters panel check measures (GUIDE.md,
    Designer UI)."""
    left = said(t, 'panel left')
    check('self-test', '%s leaves the Parameters panel on the self-test graph' % script, left == TEST_GRAPH, left)


async def check_parent_item_hands_a_scene_item_to_python(ctx: Ctx) -> None:
    """parentItem() on a node's comment item in the graph view hands the node's item to Python, in a package of the
    script's own (GUIDE.md, Designer UI). Skipped in the user's Designer."""
    c = ctx.c
    if ctx.was_running:
        skip(
            'designer facts',
            "parentItem() on a node's comment item",
            "parentItem() is never called in the user's Designer: its guard is measured only on macOS, in Designers the "
            'self-test started',
        )
        return
    t = text(await designer_script(c, 'editor_open_and_zoom/parent_item_facts', graph=TEST_GRAPH))
    expect(
        t,
        "parentItem() on a node's comment item makes the node's item Python's (ownedByPython), and Shiboken.invalidate "
        'at once leaves the item in the view (GUIDE.md, Designer UI)',
        {'owned': 'before=False after=True', 'node items': 'before=2 after=2'},
    )
    _panel_left(t, 'parent_item_facts.py')


# What selection_facts.py prints for each case, after `current=` (the graph in the editor)
GRAPH = 'mcp_selftest_selection'
WHAT_IS_SELECTED = {
    'none': '%s scene=0 nodes=[] objects=[]' % GRAPH,
    'two nodes': "%s scene=2 nodes=['levels', 'uniform'] objects=[]" % GRAPH,
    'a dot': "%s scene=1 nodes=['passthrough'] objects=[]" % GRAPH,
    'a frame': "%s scene=1 nodes=[] objects=['SDGraphObjectFrame']" % GRAPH,
    'a comment': "%s scene=1 nodes=[] objects=['SDGraphObjectComment']" % GRAPH,
    "a node's comment": "%s scene=1 nodes=[] objects=['SDGraphObjectComment']" % GRAPH,
    'a pin': "%s scene=1 nodes=[] objects=['SDGraphObjectPin']" % GRAPH,
    'a link': '%s scene=1 nodes=[] objects=[]' % GRAPH,
}
WHICH_GRAPH = {
    'the same graph opened again': "%s scene=1 nodes=['uniform'] objects=[]" % GRAPH,
    'another graph opened': '%s_other scene=0 nodes=[] objects=[]' % GRAPH,
    'a node selected in it': "%s_other scene=1 nodes=['uniform'] objects=[]" % GRAPH,
    'the first opened again': '%s scene=0 nodes=[] objects=[]' % GRAPH,
}


async def check_what_the_selection_getters_give(ctx: Ctx) -> None:
    """The UI manager's selection getters, as describe_graph(selected=True) relies on them (GUIDE.md, Designer UI), read
    in a package of the script's own, which it closes: the editor is left with no graph, read once its view is gone,
    with the tool's refusal in that state."""
    c = ctx.c
    t = text(await designer_script(c, 'editor_open_and_zoom/selection_facts', graph=TEST_GRAPH))
    _panel_left(t, 'selection_facts.py')
    # the closed graph's view goes when Designer's own event loop runs, between calls, one or two calls later
    # (measured), and the getters give empty arrays till then. Nothing signals it inside a call: read every POLL_S
    for _ in range(30):  # a safety net, not the reads expected
        no_graph = text(await designer_script(c, 'editor_open_and_zoom/no_graph_selection'))
        if 'VIEWS=0' in no_graph:
            break
        await asyncio.sleep(POLL_S)
    lines = {m.group(1): m.group(2) for m in re.finditer(r'^CASE=(.+?) current=(.*)$', t, re.M)}
    for expected, what in (
        (
            WHAT_IS_SELECTED,
            'the selection getters give the nodes selected, a Dot too, and the frames, comments and pins, at once '
            'after setSelected; empty, not None, when nothing is; a selected link in neither (GUIDE.md, Designer UI)',
        ),
        (
            WHICH_GRAPH,
            "the selection read is the editor's graph's: the same graph opened again keeps it, another opened gives "
            'its own, and the first opened again has lost it (GUIDE.md, Designer UI)',
        ),
    ):
        wrong = [case for case, line in expected.items() if lines.get(case) != line]
        check('designer facts', what, not wrong, 'differ: %s | %s' % (wrong, t.strip()))
    check(
        'designer facts',
        'with no graph in the editor and no graph view left, the selection getters raise APIException (GUIDE.md, '
        'Designer UI)',
        'CURRENT=None VIEWS=0' in no_graph
        and all(
            re.search(r'^%s=raised APIException\(.*InvalidArgument' % getter, no_graph, re.M)
            for getter in ('getCurrentGraphSelectedNodes', 'getCurrentGraphSelectedObjects')
        ),
        no_graph.strip(),
    )
    # REVIEW.md TST-809: the tool's refusal in that state, read live
    r_ = await c('describe_graph', {'selected': True})
    check(
        'describe_graph',
        'selected refuses plainly with no graph in the editor',
        r_.is_error and "No graph is open in Designer's editor, so nothing is selected there." in text(r_),
        text(r_),
    )
