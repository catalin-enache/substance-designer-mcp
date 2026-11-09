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

`port=` runs it all on another bridge port (ROADMAP item 49): the fresh server, the Designer it starts there and its
folders, the requests checks send themselves (`common.raw_request`, `common.sd_run`), the snapshots and the runs'
folders (SCRATCH_ROOT/port_<port>) are the port's own; `alone.close(port=...)` ends that one and removes that
port's runs' folders (its Designer's folders in /tmp stay until uninstall.py).
Runs side by side still share Designer's preferences plist, so the hand-over check skips after another run's launch,
and every run's crash-dump checks also watch the user's crash-dump folder.
"""

import asyncio
import contextlib
import os
import shutil
import tempfile
import time
import traceback
from collections.abc import Awaitable, Callable, Iterable, Iterator, Sequence
from typing import cast

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from test_all_tools import bitmaps, common, graph_edit, params, save
from test_all_tools.common import (
    CLEAN,
    PARAMS,
    TEST_GRAPH,
    Call,
    Ctx,
    NoListing,
    designer_here,
    helpers_source,
    library_packages,
    restore_library_packages,
    text,
    users_designer_running,
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
# every run's folder is made in here, in a folder per port (scratch_root); never deleted while that port's Designer runs
# (deleting the suite's crashed Designer twice: __main__.py), so close() removes it once that Designer has ended
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


def scratch_root(port: int | None = None) -> str:
    """The folder of the runs on `port` (common.PORT when omitted), inside SCRATCH_ROOT: a close on one port removes
    its own runs' folders, never another port's (REVIEW.md TST-170)."""
    return os.path.join(SCRATCH_ROOT, 'port_%d' % (common.PORT if port is None else port))


def new_scratch(port: int | None = None) -> str:
    """A fresh folder for one run on `port`, inside scratch_root(port)."""
    root = scratch_root(port)
    os.makedirs(root, exist_ok=True)
    return tempfile.mkdtemp(prefix='run_', dir=root)


def _failures() -> int:
    return sum(not ok for oks in common.results.values() for ok in oks)


def _checked_port(port: int | None) -> None:
    if port is not None and (isinstance(port, bool) or not 1024 <= port <= 65535):
        raise ValueError('port must be a number from 1024 to 65535, not %r' % (port,))


@contextlib.contextmanager
def on_port(port: int | None, scratch: str) -> Iterator[None]:
    """With a port: SD_BRIDGE_PORT, for the server and the clients the checks start (sd_run), common.PORT, for
    raw_request, and common.PARAMS, for a second client's server (cancel_from_second_client), set to it, and the
    snapshots in the run's folder; all put back afterwards."""
    if port is None:
        yield
        return
    saved = {name: os.environ.get(name) for name in ('SD_BRIDGE_PORT', 'SD_SNAPSHOT_DIR')}
    port_before, params_before = common.PORT, common.PARAMS
    os.environ['SD_BRIDGE_PORT'] = str(port)
    os.environ['SD_SNAPSHOT_DIR'] = os.path.join(scratch, 'snapshots')
    common.PORT, common.PARAMS = port, server_params(port)
    try:
        yield
    finally:
        common.PORT, common.PARAMS = port_before, params_before
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def server_params(port: int | None) -> StdioServerParameters:
    """The fresh server's: common.PARAMS (this process's environment when it was imported); with a port, the whole
    environment as it is now, on_port's included (stdio_client's minimal one didn't reach SD_BRIDGE_PORT: PLAN.md,
    section 2)."""
    if port is None:
        return PARAMS
    return StdioServerParameters(command=PARAMS.command, args=PARAMS.args, env=dict(os.environ))


async def _own_designer(c: Call, port: int | None = None) -> str | None:
    """None once a Designer an agent started is running (started now if none was), else why not."""
    status = await c('designer_status')
    if not status.is_error:
        if 'Started by an agent' in text(status):
            return None
        return "the Designer running is the user's: ask them to close it (this never runs in their Designer)"
    # no bridge yet: one no agent recorded may be the user's, still starting, as in the suite; another run's, on its own
    # port, isn't (REVIEW.md TST-170). With a port, launch_designer tells them apart, and refuses to start one next to
    # the user's
    try:
        users = port is None and users_designer_running()
    except NoListing as e:  # can't tell whose may be running: not started next to it (REVIEW.md INS-27)
        return str(e)
    if users:
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
    port: int | None = None,
) -> int:
    """The checks, over the MCP session c (s, for the few checks that read ctx.s), in an environment built by needs
    and setup, the server on `port` if given; the exit code as the module says."""
    steps = resolve(needs)
    await c('get_guide')  # tools refuse until it is called
    await c('get_guide', {'part': 'scripting'})  # the code tools refuse until this one is
    refusal = await _own_designer(c, port)
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
    """Ends a Designer an agent started on common.PORT, then removes that port's runs' folders once no Designer may be
    on it (another run's, on its own port, doesn't count)."""
    await c('get_guide')  # or quit_designer would be refused
    status = await c('designer_status')
    # one that doesn't answer (an older plugin's protocol, REVIEW.md SRV-82) is asked too: quit_designer ends one an
    # agent started from its record, and refuses any other by itself
    if status.is_error or 'Started by an agent' in text(status):
        print('alone: %s' % text(await c('quit_designer')).strip())
    else:
        print("alone: the Designer running is the user's: left open")
    try:
        here = designer_here()
    except NoListing as e:  # can't tell: kept (REVIEW.md INS-27)
        print('alone: %s: the folders are kept' % e)
        here = True
    if not here:
        shutil.rmtree(scratch_root(), ignore_errors=True)
        with contextlib.suppress(OSError):  # the root too, once no port has folders left in it
            os.rmdir(SCRATCH_ROOT)
    return 0


async def _session(job: Callable[[Call, ClientSession], Awaitable[int]], port: int | None = None) -> int:
    """job over a fresh MCP server (server_params), so changes to server_tools/ and the helpers are in it."""
    async with stdio_client(server_params(port)) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        c: Call = lambda name, args=None: s.call_tool(name, args or {})  # noqa: E731 (typed by Call)
        return await job(c, s)


def run(*checks: Step, needs: Iterable[str] = (), setup: Step | None = None, port: int | None = None) -> int:
    """Run the checks on their own (the module docstring); returns the exit code and prints a summary."""
    needs = list(needs)
    resolve(needs)  # an unknown need, before anything starts
    _checked_port(port)
    scratch = new_scratch(port)
    with on_port(port, scratch):
        code = asyncio.run(_session(lambda c, s: run_with(c, checks, needs, setup, scratch, s, port), port))
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


def close(port: int | None = None) -> int:
    """End the Designer the runs used (only if an agent started it), on `port` if given, and remove that port's runs'
    folders once no Designer may be on it."""
    _checked_port(port)
    with on_port(port, scratch_root(port)):
        return asyncio.run(_session(lambda c, s: close_with(c), port))
