"""
End-to-end self-test of every substance-designer MCP tool, over a real stdio MCP connection.

    macOS:   mcp_server/venv/bin/python tests/test_all_tools
    Windows: mcp_server\\venv\\Scripts\\python tests\\test_all_tools

If Designer isn't running, the test starts it (launch_designer) and closes it again at the end
(quit_designer); a Designer that was already running is left open. Everything that changes state happens in a
temporary graph ("mcp_selftest") that is removed at the end; the graph you had open in the
editor is reopened. It triggers Undo/Redo only while the self-test graph is the one in the editor
(Undo acts on the document in focus), checks that exactly its own step was undone, and redoes at
once if not. "designer facts" checks the Designer behaviour AGENTS.md documents.
The 3D screenshot is skipped if no 3D View is visible. Exits with code 1 if any check fails.

This file is the index: it opens the MCP session, runs the categories in CATEGORIES in order, then
cleans up and prints the summary. Each category is a module of this folder with an
`async def run(ctx)` (or two functions, where its checks are split around another category's).
They share one graph, so they run in this order only: `ctx` (common.Ctx) carries what an earlier one made for
the later ones (the graph `G`, its node ids `clouds`, `slope`, `lv`, `out`, the bitmap `png`, the
saved `sbs`...). Helpers, snippets and the check record are in common.py.
"""

import asyncio
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
from collections.abc import Awaitable, Callable

# importable as the package test_all_tools, also when run as `python tests/test_all_tools`, where
# Python puts this folder first on sys.path: its module names (save, render...) mustn't shadow others
_HERE = os.path.dirname(os.path.abspath(__file__))
if sys.path and os.path.abspath(sys.path[0] or '.') == _HERE:
    sys.path.pop(0)
if os.path.dirname(_HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(_HERE))

from mcp.client.session import ClientSession  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

from test_all_tools import (  # noqa: E402
    batch,
    bitmaps,
    bridge,
    discovery,
    editor,
    example,
    facts,
    graph_edit,
    inputs,
    layout,
    lifecycle,
    link_display,
    lookup,
    measure,
    params,
    render,
    safeguards,
    save,
    script_runner,
    undo,
)
from test_all_tools.common import (  # noqa: E402
    BUNDLE,
    CLEAN,
    PARAMS,
    SAME_GRAPH_BACK,
    STATE,
    TEST_GRAPH,
    Call,
    Ctx,
    check,
    crash_dumps,
    designer_alive,
    editor_graph,
    helpers_source,
    library_packages,
    new_crash_dumps,
    restore_library_packages,
    results,
    skip,
    skipped,
    summarize,
    text,
)

# In the order they run; each one may rely on what the ones before it left in the graph and in ctx
CATEGORIES: list[Callable[[Ctx], Awaitable[None]]] = [
    bridge.run,  # designer_status, cancel_designer_job, bridge security and queue, sd_run.py
    discovery.run,  # search_nodes, describe_node
    graph_edit.create,  # create_graph, add ops: the self-test graph and its nodes
    params.run,  # set ops, inheritance and seed facts
    graph_edit.wire,  # connect/move/disconnect/delete ops, execute_designer_code, describe_graph, preview_node
    bitmaps.run,  # bitmap ops, compare_to_reference
    measure.run,  # node_stats, sweep_param, check_tiling, read_designer_log
    batch.run,  # apply_edits
    inputs.run,  # set_graph_size, expose ops, list_graph_inputs, remove_graph_input
    layout.run,  # snapshot_graph, list_snapshots, diff_graph, arrange_graph, add_frame, add_comment
    facts.run,  # Designer facts AGENTS.md relies on
    lookup.run,  # same-named and library graphs; a node with several outputs
    editor.open_and_zoom,  # open_graph, screenshot_designer('graph') and crops
    undo.run,  # one tool call = one undo step
    editor.panels_and_fit,  # every panel's screenshot, the clipboard, fitting the whole graph
    save.run,  # save_package, snapshots of a saved package, copied bitmaps
    safeguards.run,  # refusals and failure paths
    link_display.run,  # set_link_display
    render.run,  # export_outputs, sbsar_info, render_sbs, preview_maps
    example.run,  # examples/build_dwarf_trimsheet.py
    script_runner.run,  # run_designer_script
]


async def run(scratch: str) -> list[str]:
    async with stdio_client(PARAMS) as (r, w), ClientSession(r, w) as s:
        init = await s.initialize()
        c: Call = lambda name, args=None: s.call_tool(name, args or {})  # noqa: E731 (typed by Call)
        tools = sorted(t.name for t in (await s.list_tools()).tools)
        print('server instructions: %d chars; tools: %d\n' % (len(init.instructions or ''), len(tools)))
        # --- the guide: short instructions point to get_guide(); a reminder until it is called
        instructions = init.instructions or ''
        check(
            'get_guide',
            'instructions fit (4,096 chars), guide on first use',
            len(instructions) < 4096 and 'Right before your first Designer tool call' in instructions,
            '%d chars' % len(instructions),
        )
        t = text(await c('list_snapshots', {'graph': 'no_such_graph'}))
        check(
            'get_guide', 'reminder before it is called', t.startswith('NOTE: the Designer guide has not been read'), t
        )
        with open(os.path.join(BUNDLE, 'AGENTS.md'), encoding='utf-8') as f:
            agents_md = f.read()
        t = text(await c('get_guide'))
        check(
            'get_guide',
            'returns all of AGENTS.md, asks to confirm',
            t.startswith(agents_md) and 'tell the user' in t.splitlines()[-1],
            '%d chars' % len(t),
        )
        t = text(await c('list_snapshots', {'graph': 'no_such_graph'}))
        check('get_guide', 'no reminder afterwards', t == 'No snapshots for no_such_graph.', t)
        helper_source = helpers_source()  # sent ahead of snippets that call the helpers
        was_running = STATE['was_running'] = not (await c('designer_status')).is_error
        t = text(await c('launch_designer', {'wait_s': 240}))
        check(
            'launch_designer',
            'already running' if was_running else 'started from closed',
            ('already running' if was_running else 'Designer started in') in t and 'ERROR' not in t,
            t,
        )
        if was_running:
            skip(
                'designer facts',
                'while the Home screen shows, no panel is visible',
                'Home shows only after a fresh start, and Designer was already running',
            )
        else:
            # Home can't be shown again once closed, so this is measured on the start itself (REVIEW.md TST-64)
            m = re.search(r'panels visible: (\d+) before, (\d+) after', t)
            panels = text(
                await c('execute_designer_code', {'code': helper_source + "\nprint('PANELS=%d' % _visible_panels())"})
            )
            if m is None and 'closed the Home screen' not in t and re.search(r'PANELS=[1-9]', panels):
                # this Designer started without its Home screen (panels visible, nothing to close): nothing
                # to measure (REVIEW.md TST-70); with no panel visible, Home wasn't closed: a failure (TST-71)
                skip('designer facts', 'while the Home screen shows, no panel is visible', 'no Home screen at start')
            else:
                check(
                    'designer facts',
                    'while the Home screen shows, no panel is visible (AGENTS.md)',
                    m is not None and m.group(1) == '0' and int(m.group(2)) > 0,
                    t,
                )
        user_graph = await editor_graph(c)
        libs_before = await library_packages(c)
        await c('execute_designer_code', {'code': CLEAN})
        ctx = Ctx(c=c, s=s, scratch=scratch, helper_source=helper_source, was_running=was_running)
        try:
            for category in CATEGORIES:
                await category(ctx)
        except Exception:
            # an unexpected answer (a parse that found nothing) skips the checks after it, but the
            # clean-up still runs and the run ends with its summary, this as a failure (REVIEW.md TST-63);
            # the whole traceback printed, and its last line in the check (TST-67)
            print(traceback.format_exc())
            check('self-test', 'the run reaches its end', False, traceback.format_exc().strip().splitlines()[-1])
        finally:
            print('\ncleanup:', text(await c('execute_designer_code', {'code': CLEAN})).strip())
            # the library packages the run loaded, in a separate call (graph views from the test
            # graph are torn down first); the user's own stay (REVIEW.md TST-30)
            time.sleep(0.5)
            await restore_library_packages(c, libs_before)
            shutil.rmtree(
                os.path.join(
                    os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), '.sd_mcp', 'snapshots'),
                    TEST_GRAPH,
                ),
                ignore_errors=True,
            )
            if user_graph and user_graph != TEST_GRAPH:
                t = text(await c('execute_designer_code', {'code': SAME_GRAPH_BACK}))
                check('open_graph', 'the self-test puts your graph back in the editor', 'SAME=True' in t, t.strip())
            if was_running:
                skip('quit_designer', 'closes Designer', 'Designer was already running, so it is left open')
            else:
                await lifecycle.run(ctx)
    return tools


def main() -> None:
    scratch = tempfile.mkdtemp(prefix='sd_mcp_selftest_')
    try:
        tools = asyncio.run(run(scratch))
    finally:
        dumps_before = crash_dumps()  # just before the clean-up it is about (REVIEW.md TST-21)
        if designer_alive():
            # deleting it while Designer ran crashed Designer twice, in its own file watcher, and
            # couldn't be reproduced on demand (REVIEW.md PLG-9, PLG-18): leave it to the OS
            print('scratch folder left for the OS to clear, since Designer is running:', scratch)
        else:
            shutil.rmtree(scratch, ignore_errors=True)
    if STATE['was_running']:
        # and the user's Designer must still be running, with no new crash dump, a little after the
        # run's end (REVIEW.md PLG-9, TST-16; the scratch folder is no longer deleted then, TST-43)
        new_dumps = new_crash_dumps(dumps_before)
        alive = designer_alive()
        check(
            'self-test',
            'your Designer is still running after the run, with no crash dump',
            alive and not new_dumps,
            'running=%s, new crash dumps: %s' % (alive, sorted(new_dumps)),
        )
    summary, ok = summarize(tools, results, skipped)
    print('\n' + summary)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
