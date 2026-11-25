"""The live self-test's categories, each a folder of this package (<category>/checks.py holds its run(ctx) and checks,
<category>/preparations.py the prepare(ctx) building what they read, <category>/designer_scripts/ the scripts only it
runs), in the order they run: the one list the index (__main__.py) and the pool (workers.py) read. No category requires another:
each runs on its own preparation, on a Ctx of its own, and is cleaned up after (category_run.py). A new
category is a folder, imported here and added to CATEGORIES, in its place by its time. lifecycle isn't listed: it
starts and ends Designers of its own, and runs apart (workers.py starts it first)."""

from test_all_tools.batch import checks as batch
from test_all_tools.bitmaps import checks as bitmaps
from test_all_tools.bridge import checks as bridge
from test_all_tools.common import Step
from test_all_tools.discovery import checks as discovery
from test_all_tools.editor_open_and_zoom import checks as editor_open_and_zoom
from test_all_tools.editor_panels_and_fit import checks as editor_panels_and_fit
from test_all_tools.example import checks as example
from test_all_tools.facts import checks as facts
from test_all_tools.functions import checks as functions
from test_all_tools.graph_edit_create import checks as graph_edit_create
from test_all_tools.graph_edit_output_fields import checks as graph_edit_output_fields
from test_all_tools.graph_edit_wire import checks as graph_edit_wire
from test_all_tools.inputs import checks as inputs
from test_all_tools.layout import checks as layout
from test_all_tools.link_display import checks as link_display
from test_all_tools.lookup import checks as lookup
from test_all_tools.measure import checks as measure
from test_all_tools.params import checks as params
from test_all_tools.render import checks as render
from test_all_tools.safeguards import checks as safeguards
from test_all_tools.save import checks as save
from test_all_tools.script_runner import checks as script_runner
from test_all_tools.undo import checks as undo

# in the pool's order (SOLO's start last), slowest first, so a pool's last ones are short (measured 2026-11-10, each
# category's preparation, checks and clean-up: a run's summary lists them); one run (Windows) runs them in this order too
CATEGORIES: list[Step] = [
    # 425 s (2026-11-23, two full runs, 4 Designers side by side: 425.3 s, 425.9 s; 420.2 s alone, 2026-11-21): every
    # panel's screenshot, the clipboard, fitting the whole graph, the 3D view set up
    editor_panels_and_fit.run,
    # 136 s (2026-11-22, two scratch runs, with their server's start: 150.0 s, 122.7 s): function graphs' Designer facts,
    # set_function, function graphs of the package, sampling images, the tools reading functions
    functions.run,
    # 88 s (2026-11-24, two scratch runs, with their server's start: 88.2 s, 87.6 s): node_stats, sweep_param,
    # check_tiling, read_designer_log
    measure.run,
    # 50 s (2026-11-23, two scratch runs, with their server's start: 53.8 s, 46.7 s): Designer facts GUIDE.md relies on
    facts.run,
    # 46 s (2026-11-22, two scratch runs, with their server's start: 45.3 s, 46.3 s): set ops, inheritance and seed
    # facts, a Gradient Map's keys and a Curve's points
    params.run,
    # 39 s (2026-11-23, two scratch runs, with their server's start: 39.1 s, 39.0 s): bitmap ops, their sizes and
    # orientations, compare_to_reference, analyze_reference, the greys of a colour image, a photo's palette on a Gradient
    # Map
    bitmaps.run,
    render.run,  # 35 s: export_outputs, sbsar_info, render_sbs, preview_maps
    # 30 s (2026-11-25, two scratch runs, with their server's start: 20.6 s, 39.6 s): set_link_display, its reload's
    # steps in Designer's undo history and in undo_edits' refusal
    link_display.run,
    # 30 s (2026-11-25, two scratch runs in a Designer just started, with their server's start: 31.0 s, 28.5 s):
    # apply_edits, the rollback of a failed call (apply_edits, create_graph, sweep_param and the code tools, a cancel and
    # a job queued during it, a timeout falling in or after the code), undo_edits (a step redone included), Designer's
    # undo history
    batch.run,
    safeguards.run,  # 23 s: refusals and failure paths
    graph_edit_wire.run,  # 21 s: connect/move/disconnect/delete ops, execute_designer_code, describe_graph, preview_node
    # 16 s (2026-11-23, two scratch runs, with their server's start: 15.5 s, 16.7 s): open_graph,
    # screenshot_designer('graph') and crops, describe_graph(selected=True), the Designer facts of the Parameters panel,
    # the selection getters and parentItem
    editor_open_and_zoom.run,
    inputs.run,  # 15 s: set_graph_size, expose ops, list_graph_inputs, remove_graph_input
    bridge.run,  # 11 s: designer_status, cancel_designer_job, bridge security and queue, sd_run.py
    example.run,  # 10 s: examples/build_dwarf_trimsheet.py
    lookup.run,  # 6 s: same-named and library graphs; a node with several outputs
    discovery.run,  # 5 s: search_nodes, describe_node
    graph_edit_create.run,  # 3 s: create_graph, add ops
    layout.run,  # 2 s: snapshot_graph, list_snapshots, diff_graph, arrange_graph, add_frame, add_comment
    save.run,  # 2 s: save_package, snapshots of a saved package, copied bitmaps
    graph_edit_output_fields.run,  # 2 s: naming and tagging output nodes, on a graph of their own
    undo.run,  # 13 s (2026-11-22, two scratch runs: 14.2 s, 12.1 s): one tool call = one undo step
    script_runner.run,  # 1 s: run_designer_script
]
# never two at once in a pool (workers.py): they use the machine's one clipboard (the 3D capture goes through it), and
# only they do (tests/unit/test_selftest_categories.py)
CLIPBOARD: frozenset[str] = frozenset({'facts', 'editor_panels_and_fit'})
# last in a pool, with no other Designer of the run: beside the others (starting, closing their Home screen, lifecycle's
# own launches) Undo of an output's fields failed in 3 pool runs of 4, and 8 times in 8 beside one idle Designer until
# its window was raised and activated first (common.UNDO_REDO). In the 2026-11-20 final check that Undo failed with
# `undo` run last and alone, no other Designer running: an Undo is now read back until the graph shows it, and sent
# again only when its action never fired (undo/edit_menu.py). Whether `undo` still needs to run alone wasn't measured
SOLO: frozenset[str] = frozenset({'undo'})


def category_name(step: Step) -> str:
    """A step's name: its category's folder (test_all_tools.<category>.checks), with the function's name unless it is
    the whole category (`run`)."""
    parts = step.__module__.split('.')
    module = parts[-2] if parts[-1] == 'checks' and len(parts) > 2 else parts[-1]
    return module if step.__qualname__ == 'run' else '%s.%s' % (module, step.__qualname__)


def by_name(name: str) -> Step:
    """The category of that name (category_name); KeyError for another."""
    return {category_name(step): step for step in CATEGORIES}[name]
