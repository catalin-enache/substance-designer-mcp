"""Chosen checks of the live self-test, run on their own in an environment built for them: how an agent sees a check
fail and then pass while working, without a run of the whole suite, which runs only when the user asks (AGENTS.md,
Running the tests). From a scratch script, with `tests` on sys.path:

    from test_all_tools import alone, params
    raise SystemExit(alone.run(params.check_<what>, needs=['graph']))  # or a whole category: params.run

A check is a function of its category's module, `async def check_<what>(ctx: Ctx)`, that the category's `run(ctx)`
calls: this calls the same function, never a copy. It runs in a Designer an agent started, never the user's: it starts
one if none runs, keeps it open for the next runs, and `alone.close()` ends it. `needs` builds the environment with the
suite's own setup steps (NEEDS), each with the ones it relies on; `setup(ctx)` adds anything else, its graphs named
starting `mcp_selftest`: the clean-up unloads every package holding one. Each check prints
PASS or FAIL as in the suite. Exit code: 0 every check passed, 1 a check failed, 2 the environment couldn't be built
(the user's Designer, a launch or a setup that failed) or cleaned up.
"""

import asyncio
import os
import shutil
import tempfile
import time
import traceback
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import cast

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

from test_all_tools import bitmaps, common, graph_edit, params, save
from test_all_tools.common import (
    CLEAN,
    PARAMS,
    TEST_GRAPH,
    Call,
    Ctx,
    designer_alive,
    helpers_source,
    library_packages,
    restore_library_packages,
    text,
)

Step = Callable[[Ctx], Awaitable[None]]

# need: (the needs it relies on, the suite's own step that builds it), in the order the suite runs them
NEEDS: dict[str, tuple[tuple[str, ...], Step]] = {
    'graph': ((), graph_edit.create),  # the self-test graph: clouds -> slope blur -> levels -> output (ctx.G and ids)
    'params': (('graph',), params.run),  # its parameters as params' checks leave them (Samples = 16...)
    'wired': (('params',), graph_edit.wire),  # its connections as later categories find them (the output `height`)
    'png': (('graph',), bitmaps.run),  # a bitmap node from an imported PNG (ctx.png)
    'sbs': (('wired', 'png'), save.run),  # the graph saved (ctx.sbs, ctx.stats_before)
}
# every run's folder is made in here; never deleted while Designer runs (deleting the suite's crashed Designer
# twice: __main__.py), so close() removes it once Designer has ended
SCRATCH_ROOT = os.path.join(tempfile.gettempdir(), 'sd_mcp_selftest_alone')
PAUSE_S = 0.5  # between the clean-up's calls, so graph views are torn down first (as __main__.py)


def resolve(needs: Iterable[str]) -> list[str]:
    """The needs with every need they rely on, each once, in NEEDS' order; ValueError for one NEEDS lacks."""
    wanted: set[str] = set()

    def add(need: str) -> None:
        if need not in NEEDS:
            raise ValueError('unknown need %r: the known ones are %s' % (need, sorted(NEEDS)))
        if need not in wanted:
            wanted.add(need)
            for before in NEEDS[need][0]:
                add(before)

    for need in needs:
        add(need)
    return [need for need in NEEDS if need in wanted]


def new_scratch() -> str:
    """A fresh folder for one run, inside SCRATCH_ROOT."""
    os.makedirs(SCRATCH_ROOT, exist_ok=True)
    return tempfile.mkdtemp(prefix='run_', dir=SCRATCH_ROOT)


def _failures() -> int:
    return sum(not ok for oks in common.results.values() for ok in oks)


async def _own_designer(c: Call) -> str | None:
    """None once a Designer an agent started is running (started now if none was), else why not."""
    status = await c('designer_status')
    if not status.is_error:
        if 'Started by an agent' in text(status):
            return None
        return "the Designer running is the user's: ask them to close it (this never runs in their Designer)"
    if designer_alive():  # no bridge yet: whose it is can't be told, so it counts as the user's, as in the suite
        return 'a Designer is running but not answering yet: wait and run again, or ask the user'
    t = text(await c('launch_designer', {'wait_s': 240}))
    return None if 'Designer started in' in t and 'ERROR' not in t else 'launch_designer: ' + t.strip()


async def run_with(
    c: Call,
    checks: Sequence[Step],
    needs: Iterable[str],
    setup: Step | None,
    scratch: str,
    s: ClientSession | None = None,
) -> int:
    """The checks, over the MCP session c (s, for the few checks that read ctx.s), in an environment built by needs
    and setup; the exit code as the module says."""
    steps = resolve(needs)
    await c('get_guide')  # tool results carry a reminder until it is called, and checks compare results
    refusal = await _own_designer(c)
    if refusal:
        print('alone: nothing run: %s' % refusal)
        return 2
    libs_before = await library_packages(c)
    print('alone: before: %s' % text(await c('execute_designer_code', {'code': CLEAN})).strip())
    # only bridge.py's checks read ctx.s; with no session (unit tests) they fail at once
    ctx = Ctx(c=c, s=cast(ClientSession, s), scratch=scratch, helper_source=helpers_source(), was_running=False)
    code = 2  # until the environment is built
    try:
        before = _failures()
        try:
            for need in steps:
                print('alone: setup %s' % need)
                await NEEDS[need][1](ctx)
            if setup is not None:
                print('alone: setup (custom)')
                await setup(ctx)
            built = _failures() == before
        except Exception:
            print(traceback.format_exc())
            built = False
        if not built:
            print('alone: the environment could not be built; no check run')
        else:
            before = _failures()
            for check in checks:
                # the module too: several categories in one call would each print 'run'
                print('alone: %s.%s' % (check.__module__.split('.')[-1], check.__qualname__))
                try:
                    await check(ctx)
                except Exception:
                    print(traceback.format_exc())
                    last = traceback.format_exc().strip().splitlines()[-1]
                    common.check('alone', 'the check reaches its end', False, last)
            code = 1 if _failures() > before else 0
    finally:
        before = _failures()
        print('alone: clean-up: %s' % text(await c('execute_designer_code', {'code': CLEAN})).strip())
        time.sleep(PAUSE_S)
        await restore_library_packages(c, libs_before)
        if _failures() > before:
            print('alone: the clean-up failed: the Designer may hold leftovers; close() ends it')
            code = 2
    return code


async def close_with(c: Call) -> int:
    """Ends a Designer an agent started, then removes the runs' folders once no Designer runs."""
    await c('get_guide')  # no reminder in front of what it prints
    status = await c('designer_status')
    if not status.is_error and 'Started by an agent' in text(status):
        print('alone: %s' % text(await c('quit_designer')).strip())
    elif not status.is_error:
        print("alone: the Designer running is the user's: left open")
    if not designer_alive():
        shutil.rmtree(SCRATCH_ROOT, ignore_errors=True)
    return 0


async def _session(job: Callable[[Call, ClientSession], Awaitable[int]]) -> int:
    """job over a fresh MCP server (common.PARAMS), so changes to server_tools/ and the helpers are in it."""
    async with stdio_client(PARAMS) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        c: Call = lambda name, args=None: s.call_tool(name, args or {})  # noqa: E731 (typed by Call)
        return await job(c, s)


def run(*checks: Step, needs: Iterable[str] = (), setup: Step | None = None) -> int:
    """Run the checks on their own (the module docstring); returns the exit code and prints a summary."""
    needs = list(needs)
    resolve(needs)  # an unknown need, before anything starts
    scratch = new_scratch()
    code = asyncio.run(_session(lambda c, s: run_with(c, checks, needs, setup, scratch, s)))
    shutil.rmtree(
        os.path.join(
            os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), '.sd_mcp', 'snapshots'),
            TEST_GRAPH,
        ),
        ignore_errors=True,
    )
    ran = sum(len(oks) for oks in common.results.values())
    print(
        '\nalone: exit code %d (0 passed, 1 a check failed, 2 no environment or no clean-up); %d checks, %d failed, '
        '%d skipped; folder %s' % (code, ran, _failures(), len(common.skipped), scratch)
    )
    return code


def close() -> int:
    """End the Designer the runs used (only if an agent started it) and remove the runs' folders."""
    return asyncio.run(_session(lambda c, s: close_with(c)))
