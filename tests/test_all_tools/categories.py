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
    # 40 s (2026-11-12, a scratch run: 46 s with its server's start): every panel's screenshot, the clipboard, fitting
    # the whole graph, the 3D view set up
    editor_panels_and_fit.run,
    render.run,  # 35 s: export_outputs, sbsar_info, render_sbs, preview_maps
    facts.run,  # 35 s: Designer facts GUIDE.md relies on
    safeguards.run,  # 23 s: refusals and failure paths
    graph_edit_wire.run,  # 21 s: connect/move/disconnect/delete ops, execute_designer_code, describe_graph, preview_node
    link_display.run,  # 16 s: set_link_display
    inputs.run,  # 15 s: set_graph_size, expose ops, list_graph_inputs, remove_graph_input
    params.run,  # 15 s: set ops, inheritance and seed facts
    bridge.run,  # 11 s: designer_status, cancel_designer_job, bridge security and queue, sd_run.py
    example.run,  # 10 s: examples/build_dwarf_trimsheet.py
    measure.run,  # 9 s: node_stats, sweep_param, check_tiling, read_designer_log
    lookup.run,  # 6 s: same-named and library graphs; a node with several outputs
    discovery.run,  # 5 s: search_nodes, describe_node
    editor_open_and_zoom.run,  # 4 s: open_graph, screenshot_designer('graph') and crops
    bitmaps.run,  # 4 s: bitmap ops, compare_to_reference
    graph_edit_create.run,  # 3 s: create_graph, add ops
    layout.run,  # 2 s: snapshot_graph, list_snapshots, diff_graph, arrange_graph, add_frame, add_comment
    save.run,  # 2 s: save_package, snapshots of a saved package, copied bitmaps
    graph_edit_output_fields.run,  # 2 s: naming and tagging output nodes, on a graph of their own
    batch.run,  # 1 s: apply_edits
    undo.run,  # 1 s: one tool call = one undo step
    script_runner.run,  # 1 s: run_designer_script
]
# never two at once in a pool (workers.py): they use the machine's one clipboard (the 3D capture goes through it), and
# only they do (tests/unit/test_selftest_categories.py)
CLIPBOARD: frozenset[str] = frozenset({'facts', 'editor_panels_and_fit'})
# last in a pool, with no other Designer of the run: beside the others (starting, closing their Home screen, lifecycle's
# own launches) Undo of an output's fields failed in 3 pool runs of 4, and 8 times in 8 beside one idle Designer until
# its window was raised and activated first (common.UNDO_REDO)
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
