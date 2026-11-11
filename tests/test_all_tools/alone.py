"""Chosen checks of the live self-test, run on their own in an environment built for them: how an agent sees a check
fail and then pass while working, without a run of the whole suite, which runs only when the user asks (AGENTS.md,
Running the tests). From a scratch script, with `tests` on sys.path:

    from test_all_tools import alone
    from test_all_tools.params import checks as params
    raise SystemExit(alone.run(params.check_<what>))  # or a whole category: params.run

A check is a function of its category's checks.py (<category>/checks.py), `async def check_<what>(ctx: Ctx)`, that the
category's `run(ctx)` calls: this calls the same function, never a copy. It runs in a Designer an agent started, never
the user's: it starts one if none runs, keeps it open for the next runs, and `alone.close()` ends it. Each category's
checks run as in the suite (category_run.py): on a Ctx of their own, after the category's own preparation
(<category>/preparations.py), then cleaned up; checks of several categories run category by category, in the order
given. `setup(ctx)` adds anything else, after the preparation, its graphs named starting `mcp_selftest`: the clean-up
unloads every package holding one. Each check prints PASS or FAIL as in the suite. Exit code: 0 every check passed, 1
a check failed, 2 the environment couldn't be built (the user's Designer, a launch, a preparation or a setup that
failed) or cleaned up. `own_designer=True` is for checks that start and
end their Designer themselves (`alone.run(lifecycle.run, own_designer=True)`): none is started for them or cleaned up,
and they are refused when the Designer on the port is the user's, or none answers there and one no agent recorded
runs.

`port=` runs it all on another bridge port (ROADMAP item 49): the fresh server, the Designer it starts there and its
folders, the requests checks send themselves (`common.raw_request`, `common.sd_run`), the snapshots and the runs'
folders (SCRATCH_ROOT/port_<port>) are the port's own; `alone.close(port=...)` ends that one and removes that
port's runs' folders (its Designer's folders in /tmp stay until uninstall.py).
Runs side by side still share Designer's preferences plist, so the hand-over check skips after another run's launch,
and every run's crash-dump checks also watch the user's crash-dump folder. A run of `lifecycle` puts its Designer's
record aside for a while, and meanwhile any launch_designer on the machine refuses: none beside another run, the full
one included; nor `facts` or `editor_panels_and_fit` beside another run of either, for the machine's one clipboard
(`categories.CLIPBOARD` keeps them apart only inside a pool).
"""

import asyncio
import contextlib
import os
import shutil
import tempfile
import traceback
from collections.abc import Awaitable, Callable, Iterator, Sequence
from typing import cast

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from test_all_tools import common
from test_all_tools.category_run import category_of, run_category
from test_all_tools.common import (
    CLEAN,
    PARAMS,
    Call,
    Ctx,
    NoListing,
    Step,
    designer_here,
    helpers_source,
    remove_test_snapshots,
    text,
    users_designer_running,
)

# every run's folder is made in here, in a folder per port (scratch_root); never deleted while that port's Designer runs
# (deleting the suite's crashed Designer twice: __main__.py), so close() removes it once that Designer has ended
SCRATCH_ROOT = os.path.join(tempfile.gettempdir(), 'sd_mcp_selftest_alone')


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
    snapshots and the server's temp folder (TMPDIR) in the run's folder, so runs on other ports share none, by its
    real path: macOS's temp folder is under a symlink, which leaves the paths Designer writes in a snapshot one `..`
    short; all put back afterwards."""
    if port is None:
        yield
        return
    saved = {name: os.environ.get(name) for name in ('SD_BRIDGE_PORT', 'SD_SNAPSHOT_DIR', 'TMPDIR')}
    port_before, params_before = common.PORT, common.PARAMS
    os.environ['SD_BRIDGE_PORT'] = str(port)
    os.environ['SD_SNAPSHOT_DIR'] = os.path.join(os.path.realpath(scratch), 'snapshots')
    os.environ['TMPDIR'] = os.path.join(os.path.realpath(scratch), 'tmp')  # the server's, apart from other ports' runs
    os.makedirs(os.environ['TMPDIR'], exist_ok=True)
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
    environment as it is now, on_port's included (stdio_client passes a minimal one unless
    StdioServerParameters.env is set, and SD_BRIDGE_PORT reached the server only then)."""
    if port is None:
        return PARAMS
    return StdioServerParameters(command=PARAMS.command, args=PARAMS.args, env=dict(os.environ))


async def _refusal(c: Call, port: int | None) -> tuple[str | None, bool]:
    """(why not, when a Designer the user opened may be running, else None; whether one an agent started answers)."""
    status = await c('designer_status')
    if not status.is_error:
        if 'Started by an agent' in text(status):
            return None, True
        return "the Designer running is the user's: ask them to close it (this never runs in their Designer)", False
    # no bridge yet: one no agent recorded may be the user's, still starting, as in the suite; another run's, on its own
    # port, isn't (REVIEW.md TST-170). With a port, launch_designer tells them apart, and refuses to start one next to
    # the user's
    try:
        users = port is None and users_designer_running()
    except NoListing as e:  # can't tell whose may be running: not started next to it (REVIEW.md INS-27)
        return str(e), False
    if users:
        return 'a Designer is running but not answering yet: wait and run again, or ask the user', False
    return None, False


async def _own_designer(c: Call, port: int | None = None) -> str | None:
    """None once a Designer an agent started is running (started now if none was), else why not."""
    refusal, answering = await _refusal(c, port)
    if refusal or answering:
        return refusal
    t = text(await c('launch_designer', {'wait_s': 240}))
    return None if 'Designer started in' in t and 'ERROR' not in t else 'launch_designer: ' + t.strip()


async def run_with(
    c: Call,
    checks: Sequence[Step],
    setup: Step | None,
    scratch: str,
    s: ClientSession | None = None,
    port: int | None = None,
    own_designer: bool = False,
) -> int:
    """The checks, over the MCP session c (s, for the few checks that read ctx.s), each category's on its own
    preparation and setup, the server on `port` if given; the exit code as the module says. With own_designer the
    checks start and end their Designer themselves: none is started for them and none is left to clean up; _refusal
    decides whether they run, as for the others (the module docstring)."""
    await c('get_guide')  # tools refuse until it is called
    await c('get_guide', {'part': 'scripting'})  # the code tools refuse until this one is
    # only bridge/checks.py's checks read ctx.s; with no session (unit tests) they fail at once
    ctx = Ctx(c=c, s=cast(ClientSession, s), scratch=scratch, helper_source=helpers_source(), was_running=False)
    before = _failures()
    if own_designer:
        # none started for them, and refused beside the user's as far as _refusal tells it: a check not of lifecycle would
        # run in it (REVIEW.md TST-228, TST-279).
        # Asked whatever the port: launch_designer, which tells them apart there, is these checks' own (TST-260)
        refusal, _ = await _refusal(c, None)
        if refusal:
            print('alone: nothing run: %s' % refusal)
            return 2
        for check in checks:
            _announce(check)
            try:
                await check(ctx)
            except Exception:
                print(traceback.format_exc())
                last = traceback.format_exc().strip().splitlines()[-1]
                common.check('alone', 'the check reaches its end', False, last)
        return 1 if _failures() > before else 0
    refusal = await _own_designer(c, port)
    if refusal:
        print('alone: nothing run: %s' % refusal)
        return 2
    print('alone: before: %s' % text(await c('execute_designer_code', {'code': CLEAN})).strip())
    code = 0
    for category, its_checks in _by_category(checks):
        ran = await run_category(ctx.fresh(category), its_checks, setup, announce=_announce)
        if not ran.prepared:
            print('alone: the environment of %s could not be built; none of its checks run' % category)
        if not ran.cleaned:
            print('alone: the clean-up failed: the Designer may hold leftovers; close() ends it')
        if not (ran.prepared and ran.cleaned):
            code = 2
    return code or (1 if _failures() > before else 0)


def _announce(check: Step) -> None:
    # the category too: several categories in one call would each print 'run'
    print('alone: %s.%s' % (category_of(check), check.__qualname__))


def _by_category(checks: Sequence[Step]) -> list[tuple[str, list[Step]]]:
    """The checks grouped by category, in the order each category first comes."""
    groups: dict[str, list[Step]] = {}
    for check in checks:
        groups.setdefault(category_of(check), []).append(check)
    return list(groups.items())


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


def run(*checks: Step, setup: Step | None = None, port: int | None = None, own_designer: bool = False) -> int:
    """Run the checks on their own (the module docstring); returns the exit code and prints a summary. own_designer:
    checks that start and end their Designer themselves (lifecycle.run); they take no setup."""
    if own_designer and setup is not None:
        raise ValueError('own_designer: the environment would be built in a Designer those checks replace')
    _checked_port(port)
    scratch = new_scratch(port)
    with on_port(port, scratch):
        code = asyncio.run(_session(lambda c, s: run_with(c, checks, setup, scratch, s, port, own_designer), port))
        remove_test_snapshots()
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
