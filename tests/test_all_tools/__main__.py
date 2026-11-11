"""
End-to-end self-test of every substance-designer MCP tool, over a real stdio MCP connection.

    macOS:   mcp_server/venv/bin/python tests/test_all_tools [--no-unit] [--workers N] [--only CATEGORY ...]
    Windows: mcp_server\\venv\\Scripts\\python tests\\test_all_tools

On macOS, with no Designer running that no agent started, it runs each category in a Designer started for it and
closed after it, several at once (`--workers N`; 1 runs them one after the other), with the whole unit suite beside
them (the pool's rules: workers.py); `--no-unit` leaves the unit suite out. `--only` runs the categories it
names alone, through the same pool, without the unit suite, judging the coverage of the tools they ran only. With
the user's Designer open it starts nothing and asks for it to be closed. On Windows it makes one run in one
Designer, of every category but `lifecycle`, without the unit suite: it starts Designer if none runs
(launch_designer) and leaves it open at the end, as it leaves one already running (ROADMAP item 65). Everything
that changes state happens in temporary graphs ("mcp_selftest"), removed after each category; in the user's
Designer the graph they had open in the editor is reopened. It triggers Undo/Redo only while the self-test graph is
the one in the editor (Undo acts on the document in focus), checks that exactly its own step was undone, and redoes
at once if not. "designer facts" checks the Designer behaviour GUIDE.md documents.
The 3D screenshot is skipped if no 3D View is visible in the user's Designer. Exits with code 1 if any check fails.

This file is the index: it opens the MCP session, runs the categories in order (CATEGORIES, categories.py), each on its
own preparation and cleaned up after it (category_run.py), then cleans up and prints the summary. Each category is a
folder of this package: its `async def run(ctx)` and checks in <category>/checks.py, the prepare(ctx) building what they
read in <category>/preparations.py.
None reads what another made: each gets a Ctx of its own (common.Ctx), its preparation setting what its checks read
(the graph `G`, node ids `clouds`, `slope`, `lv`, `out`, a bitmap `png`, a saved `sbs`...). Helpers, snippets and the
check record are in common.py. The summary lists each category's time.
"""

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
from typing import Any

# importable as the package test_all_tools, also when run as `python tests/test_all_tools`, where
# Python puts this folder first on sys.path: its module names (save, render...) mustn't shadow others
_HERE = os.path.dirname(os.path.abspath(__file__))
if sys.path and os.path.abspath(sys.path[0] or '.') == _HERE:
    sys.path.pop(0)
if os.path.dirname(_HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(_HERE))

from mcp.client.session import ClientSession  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

from test_all_tools import common, launch_lock, workers  # noqa: E402
from test_all_tools.categories import CATEGORIES, by_name, category_name  # noqa: E402
from test_all_tools.category_run import run_category  # noqa: E402
from test_all_tools.common import (  # noqa: E402
    BUNDLE,
    CLEAN,
    PARAMS,
    SAME_GRAPH_BACK,
    STATE,
    TEST_GRAPH,
    Call,
    Ctx,
    Step,
    agents_designers,
    check,
    crash_dumps,
    designer_here,
    editor_graph,
    end_own_designer,
    helpers_source,
    library_packages,
    new_crash_dumps,
    remove_test_snapshots,
    restore_library_packages,
    results,
    skip,
    skipped,
    summarize,
    text,
    times,
    users_designer_running,
)
from test_all_tools.lifecycle import checks as lifecycle  # noqa: E402

# what a worker's end left for the pool: its quit_designer answer, and when (workers.check_the_quits)
ENDED: dict[str, Any] = {}


async def run(
    scratch: str, steps: list[Step] = CATEGORIES, worker: str | None = None, first: bool = False
) -> list[str]:
    """The steps over one MCP session, or one worker's category of a pool (workers.py), in a Designer of its own; the
    server's tools. The run's start checks (the guide, the Home screen) run in one run, or in the pool's `first`."""
    if os.environ.get('PYTEST_CURRENT_TEST'):  # it would start a server and a Designer: tests replace run()
        raise RuntimeError('a unit test reached a real run of the self-test: fake run()')
    async with stdio_client(PARAMS) as (r, w), ClientSession(r, w) as s:
        init = await s.initialize()
        c: Call = lambda name, args=None: s.call_tool(name, args or {})  # noqa: E731 (typed by Call)
        tools = sorted(t.name for t in (await s.list_tools()).tools)
        print('server instructions: %d chars; tools: %d\n' % (len(init.instructions or ''), len(tools)))
        if worker == 'lifecycle':  # it starts from a Designer of its own and ends with none (lifecycle/checks.py)
            ctx = Ctx(c=c, s=s, scratch=scratch, helper_source=helpers_source(), was_running=False)
            await run_steps(ctx, [lifecycle.run], isolated=False)
            return tools
        start_checks = worker is None or first
        if start_checks:
            await check_the_guide(c, init.instructions or '')
        else:
            await c('get_guide')  # tools refuse until it is called
            await c('get_guide', {'part': 'scripting'})  # the code tools until this one is
        helper_source = helpers_source()  # sent ahead of snippets that call the helpers
        # a worker's Designer is its own, decided by the parent (workers.py)
        was_running = STATE['was_running'] = False if worker else await already_running(c)
        t = text(await c('launch_designer', {'wait_s': 240}))
        if not start_checks:
            if 'Designer started in' not in t or 'ERROR' in t:
                check('self-test', '%s: its Designer started' % worker, False, t)
                return tools
        else:
            await check_the_start(c, t, was_running, helper_source)
        user_graph = await editor_graph(c)
        libs_before = await library_packages(c)
        await c('execute_designer_code', {'code': CLEAN})
        ctx = Ctx(c=c, s=s, scratch=scratch, helper_source=helper_source, was_running=was_running)
        try:
            await run_steps(ctx, steps)
        finally:
            print('\ncleanup:', text(await c('execute_designer_code', {'code': CLEAN})).strip())
            # the library packages the run loaded, in a separate call (graph views from the test
            # graph are torn down first); the user's own stay (REVIEW.md TST-30)
            time.sleep(0.5)
            await restore_library_packages(c, libs_before)
            remove_test_snapshots()
            if user_graph and user_graph != TEST_GRAPH:
                t = text(await c('execute_designer_code', {'code': SAME_GRAPH_BACK}))
                check('open_graph', 'the self-test puts your graph back in the editor', 'SAME=True' in t, t.strip())
            await finish(ctx, worker)
    return tools


async def check_the_guide(c: Call, instructions: str) -> None:
    """The guide: short instructions point to get_guide(); tools refuse until it is called, and work after."""
    check(
        'get_guide',
        'instructions fit (4,096 chars), guide on first use',
        len(instructions) < 4096 and 'Right before your first Designer tool call' in instructions,
        '%d chars' % len(instructions),
    )
    res = await c('list_snapshots', {'graph': 'no_such_graph'})
    check(
        'get_guide',
        'a tool refuses before it is called',
        bool(res.is_error) and 'get_guide()' in text(res),
        text(res),
    )
    with open(os.path.join(BUNDLE, 'mcp_server', 'GUIDE.md'), encoding='utf-8') as f:
        core, _, scripting = f.read().partition('\n# Scripting')
    t = text(await c('get_guide'))
    check(
        'get_guide',
        'returns the core of GUIDE.md, asks to confirm',
        t.startswith(core.rstrip('\n')) and 'tell the user' in t.splitlines()[-1],
        '%d chars' % len(t),
    )
    t = text(await c('list_snapshots', {'graph': 'no_such_graph'}))
    check('get_guide', 'the tool works afterwards', t == 'No snapshots for no_such_graph.', t)
    t = text(await c('get_guide', {'part': 'scripting'}))  # the code tools refuse until it is read
    check(
        'get_guide',
        'returns the scripting part of GUIDE.md, asks to confirm',
        scripting.strip() in t and 'tell the user' in t.splitlines()[-1],
        '%d chars' % len(t),
    )


async def check_the_start(c: Call, t: str, was_running: bool, helper_source: str) -> None:
    """launch_designer's answer `t`, and the Home screen, measurable only right after a fresh start."""
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
                'while the Home screen shows, no panel is visible (GUIDE.md)',
                m is not None and m.group(1) == '0' and int(m.group(2)) > 0,
                t,
            )


async def finish(ctx: Ctx, worker: str | None) -> None:
    """The end of a run, after its clean-up: a worker closes its Designer once no lock holds (launch_lock), the pool
    checking the quit with the crash dumps, after one wait at its end (ENDED). One run happens only on Windows, where
    Designer is left open; on macOS every run is a worker (REVIEW.md TST-237: one run ending with lifecycle is in git,
    for ROADMAP item 65)."""
    if sys.platform == 'win32':
        skip('quit_designer', 'closes Designer', "no Designer counts as an agent's on Windows yet (ROADMAP item 18)")
    elif worker:
        with launch_lock.changing(worker):
            ENDED['quit'] = text(await ctx.c('quit_designer', {'wait_s': 30}))
        ENDED['quit_at'] = time.time()


async def already_running(c: Call) -> bool:
    """Whether a Designer was running before the run: the user's (a Designer still starting counts too: it is the
    user's), or one answering on PORT. Not another run's, on its own port (REVIEW.md TST-170)."""
    return users_designer_running() or not (await c('designer_status')).is_error


async def run_steps(ctx: Ctx, steps: list[Step], isolated: bool = True) -> None:
    """Each step a category, run on its own (category_run.run_category: a fresh Ctx, its own preparation, cleaned up
    after); a category that raises or can't be prepared is a failed check, and the next one still runs. isolated=False:
    awaited as it is, for lifecycle, which replaces the run's Designer (nothing to clean up after it). Anything else
    raising (the clean-up: no bridge) skips the steps after it, but the run's own clean-up still runs and the run ends
    with its summary, this as a failure (REVIEW.md TST-63, TST-152); the whole traceback printed, and its last line in
    the check (TST-67). Each step's time goes to `times`, also when it raises."""
    try:
        for step in steps:
            started = time.perf_counter()
            try:
                if isolated:
                    await run_category(ctx.fresh(category_name(step)), [step])
                else:
                    await step(ctx)
            finally:
                times[category_name(step)] = time.perf_counter() - started
    except Exception:
        print(traceback.format_exc())
        check('self-test', 'the run reaches its end', False, traceback.format_exc().strip().splitlines()[-1])


def main(argv: list[str] | None = None) -> None:
    """A pool of `--workers N` (workers.choose), of the categories `--only` names, one run off macOS, or one worker of a
    pool (--worker, from workers.py)."""
    parser = argparse.ArgumentParser(prog='tests/test_all_tools', description='The live self-test of every tool.')
    parser.add_argument(
        '--workers',
        type=int,
        metavar='N',
        help='categories at once, each in a Designer of its own (default %d)' % workers.AT_ONCE,
    )
    parser.add_argument(
        '--no-unit',
        action='store_true',
        help='leave out the unit suite that otherwise runs beside the categories (alone, it is `pytest`)',
    )
    parser.add_argument(
        '--only',
        nargs='+',
        metavar='CATEGORY',
        help='those categories alone, through the pool (macOS), without the unit suite; the final check stays a full run',
    )
    parser.add_argument('--worker', choices=workers.names(), help=argparse.SUPPRESS)
    parser.add_argument('--results', help=argparse.SUPPRESS)
    parser.add_argument('--first', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.workers is not None and args.workers < 1:
        parser.error('--workers takes 1 or more')
    unknown = [name for name in args.only or [] if name not in workers.names()]
    if unknown:
        parser.error('--only: no category %s; the categories: %s' % (', '.join(unknown), ', '.join(workers.names())))
    if args.worker:
        one_run(worker=args.worker, results_file=args.results, first=args.first)
        return
    try:
        slots = workers.choose(args.workers)
    except workers.Refused as e:
        print(e)
        sys.exit(2)
    if args.only and not slots:
        print('--only runs through the pool, which is macOS only (ROADMAP item 65): nothing run')
        sys.exit(2)
    if args.only:
        sys.exit(workers.run_pool(slots, unit=False, only=args.only))
    if slots:
        sys.exit(workers.run_pool(slots, unit=not args.no_unit))
    one_run()


def one_run(worker: str | None = None, results_file: str | None = None, first: bool = False) -> None:
    """One run in one Designer: the whole suite, or a worker's category (written to results_file too)."""
    steps: list[Step] = (
        CATEGORIES if worker is None else [lifecycle.run] if worker == 'lifecycle' else [by_name(worker)]
    )
    scratch = tempfile.mkdtemp(prefix='sd_mcp_selftest_')
    try:
        tools = asyncio.run(run(scratch, steps, worker, first))
    finally:
        dumps_before = crash_dumps()  # just before the clean-up it is about (REVIEW.md TST-21)

        # a worker's Designer is the one recorded on its port: the pool's others start beside it, unrecorded at first
        def own_here() -> bool:
            return common.PORT in agents_designers()

        here = own_here if worker else designer_here
        if not STATE['was_running'] and here() and sys.platform != 'win32':
            end_own_designer()
        # asked after the end: the run's own, just ended, no longer keeps it (REVIEW.md TST-192); another run's
        # Designer never opened it (REVIEW.md TST-170)
        if here():
            # deleting it while Designer ran crashed Designer twice, in its own file watcher, and
            # couldn't be reproduced on demand (REVIEW.md PLG-9, PLG-18): leave it to the OS
            print('scratch folder left for the OS to clear, since Designer is running:', scratch)
        else:
            shutil.rmtree(scratch, ignore_errors=True)
    if STATE['was_running']:
        # and the user's Designer must still be running, with no new crash dump, a little after the
        # run's end (REVIEW.md PLG-9, TST-16; the scratch folder is no longer deleted then, TST-43)
        new_dumps = new_crash_dumps(dumps_before)
        alive = designer_here()
        check(
            'self-test',
            'your Designer is still running after the run, with no crash dump',
            alive and not new_dumps,
            'running=%s, new crash dumps: %s' % (alive, sorted(new_dumps)),
        )
    # a worker covers the tools of its part: the parent judges the coverage of them all (workers.py)
    summary, ok = summarize(tools if worker is None else sorted(set(tools) & set(results)), results, skipped, times)
    print('\n' + summary)
    if results_file:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({'tools': tools, 'results': results, 'skipped': skipped, 'times': times, **_ended()}, f)
    sys.exit(0 if ok else 1)


def _ended() -> dict[str, Any]:
    return {'quit': ENDED.get('quit'), 'quit_at': ENDED.get('quit_at')}


if __name__ == '__main__':
    main()
