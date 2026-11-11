"""tests/test_all_tools/alone.py: chosen checks of the live self-test, run on their own in an environment built for
them, the way agents see a check fail and then pass while working (the live-check skill). Designer is
replaced by a fake that answers each tool by name."""

import asyncio
import glob
import importlib
import os
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any

import pytest

from conftest import SELFTEST_DIR


def _alone() -> Any:  # a module imported by name: PyCharm can't see its names
    """alone.py imported afresh with the self-test's modules, so each test starts with an empty check record."""
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    for name in [m for m in sys.modules if m == 'test_all_tools' or m.startswith('test_all_tools.')]:
        del sys.modules[name]
    alone = importlib.import_module('test_all_tools.alone')
    vars(sys.modules['test_all_tools.category_run'])['PAUSE_S'] = 0  # no Designer to wait for (slept in _cleaned)
    # not the real pgrep: as if one of the user's ran, so close_with never removes the real SCRATCH_ROOT (REVIEW.md
    # TST-147) and a run with no bridge is refused; a test about none running says so itself
    vars(alone)['designer_here'] = lambda: True
    vars(alone)['users_designer_running'] = lambda: True
    return alone


def _result(t: str, error: bool = False) -> Any:
    return SimpleNamespace(content=[SimpleNamespace(type='text', text=t)], is_error=error)


class FakeDesigner:
    """c(name, args) for alone's calls: designer_status answers `status` (an error when None, as with no Designer
    running), launch_designer `launch`, execute_designer_code an empty library list or the clean-up's answer."""

    def __init__(self, status: str | None, launch: str = 'Designer started in 12 s.') -> None:
        self.status, self.launch = status, launch
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, name: str, args: dict[str, Any] | None = None) -> Any:
        self.calls.append((name, args or {}))
        if name == 'designer_status':
            return _result('Designer is not reachable', True) if self.status is None else _result(self.status)
        if name == 'launch_designer':
            return _result(self.launch)
        if name == 'quit_designer':
            return _result('Designer closed.')
        if name == 'execute_designer_code':
            return _result('removed 0' if 'unloadUserPackage' in (args or {}).get('code', '') else 'LIBS=')
        return _result('ok')

    def names(self) -> list[str]:
        return [n for n, _ in self.calls]


AGENTS = 'Designer 16.0.7, idle.\nStarted by an agent: disposable, nothing in it is kept.'
USERS = "Designer 16.0.7, idle.\nNot started by an agent: it is the user's."


def _run(alone: Any, c: FakeDesigner, *checks: Any, **kw: Any) -> int:
    if kw.get('scratch'):
        return int(asyncio.run(alone.run_with(c, list(checks), kw.get('setup'), kw['scratch'])))
    with tempfile.TemporaryDirectory(prefix='alone_unit_') as scratch:  # each category gets a folder in it
        return int(asyncio.run(alone.run_with(c, list(checks), kw.get('setup'), scratch)))


def _run_own_designer(alone: Any, c: FakeDesigner, *checks: Any) -> int:
    return int(asyncio.run(alone.run_with(c, list(checks), None, 'scratch', own_designer=True)))


def _in_category(category: str, name: str, body: Any) -> Any:
    """A check of the category <category> (test_all_tools.<category>.checks), running body(ctx)."""

    async def check(ctx: Any) -> None:
        await body(ctx)

    check.__module__, check.__qualname__ = 'test_all_tools.%s.checks' % category, name
    return check


def test_checks_with_their_own_designer_get_none_started_and_no_clean_up() -> None:
    # lifecycle.run starts its Designer itself and ends it: a clean-up then reached a closed Designer, and a passing
    # run ended with exit code 2
    alone = _alone()
    vars(alone)['users_designer_running'] = lambda: False
    c = FakeDesigner(None)
    ran: list[str] = []

    async def own(ctx: Any) -> None:
        ran.append('checks')

    assert _run_own_designer(alone, c, own) == 0
    assert ran == ['checks']
    assert c.names() == ['get_guide', 'get_guide', 'designer_status']  # whose Designer runs: asked, nothing started
    assert not [f for f in alone.common.results.values() if not all(f)]


@pytest.mark.parametrize(
    ('status', 'users_running'),
    [(USERS, False), (None, True)],
    ids=['the users answering', 'one no agent recorded, not answering yet'],
)
def test_checks_with_their_own_designer_never_run_beside_the_users(status: str | None, users_running: bool) -> None:
    # REVIEW.md TST-228: own_designer ran its checks before anything asked whose Designer was open
    alone = _alone()
    vars(alone)['users_designer_running'] = lambda: users_running
    ran: list[str] = []

    async def own(ctx: Any) -> None:
        ran.append('checks')

    c = FakeDesigner(status)
    assert _run_own_designer(alone, c, own) == 2
    assert ran == [] and 'launch_designer' not in c.names()


@pytest.mark.parametrize(
    ('users_running', 'code'), [(True, 2), (False, 0)], ids=['the users running', 'none of theirs']
)
def test_checks_with_their_own_designer_on_a_port_are_refused_beside_the_users_too(
    users_running: bool, code: int
) -> None:
    # REVIEW.md TST-260: on a port, whether the user's ran was left to launch_designer, which these checks call themselves
    alone = _alone()
    vars(alone)['users_designer_running'] = lambda: users_running
    ran: list[str] = []

    async def own(ctx: Any) -> None:
        ran.append('checks')

    assert (
        int(asyncio.run(alone.run_with(FakeDesigner(None), [own], None, 'scratch', port=9901, own_designer=True)))
        == code
    )
    assert ran == ([] if users_running else ['checks'])


def test_checks_with_their_own_designer_run_beside_an_agents() -> None:
    # lifecycle.run ends one an agent started itself (check_a_designer_of_its_own)
    alone = _alone()
    ran: list[str] = []

    async def own(ctx: Any) -> None:
        ran.append('checks')

    c = FakeDesigner(AGENTS)
    assert _run_own_designer(alone, c, own) == 0
    assert ran == ['checks'] and 'launch_designer' not in c.names()


def test_checks_with_their_own_designer_still_report_a_failure() -> None:
    alone = _alone()
    vars(alone)['users_designer_running'] = lambda: False

    async def fails(ctx: Any) -> None:
        alone.common.check('t', 'x', False)

    async def raises(ctx: Any) -> None:
        raise RuntimeError('boom')

    assert _run_own_designer(alone, FakeDesigner(None), fails) == 1
    assert _run_own_designer(alone, FakeDesigner(None), raises) == 1


@pytest.mark.parametrize('kw', [{'setup': 'a setup'}])
def test_checks_with_their_own_designer_take_no_environment(kw: dict[str, Any]) -> None:
    # an environment would be built in a Designer those checks then replace
    alone = _alone()
    with pytest.raises(ValueError, match='own_designer'):
        alone.run(lambda ctx: None, own_designer=True, **kw)


def test_the_snapshots_of_a_run_on_a_port_have_no_symlink_in_their_path(tmp_path: Any) -> None:
    # macOS's temp folder is under /var, a symlink: Designer wrote a snapshot's paths to files outside it one `..` short
    # (measured: 'copied bitmaps stay reachable' failed on a port of its own, and passed with the snapshots in the home)
    real = tmp_path / 'real'
    real.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(real)
    alone = _alone()
    before = os.environ.get('TMPDIR')
    with alone.on_port(9911, str(link)):
        assert os.environ['SD_SNAPSHOT_DIR'] == os.path.join(os.path.realpath(real), 'snapshots')
        # no folder shared with a run on another port: its server's temporary files go in the run's folder
        assert os.environ['TMPDIR'] == os.path.join(os.path.realpath(real), 'tmp') and os.path.isdir(
            os.environ['TMPDIR']
        )
        assert alone.server_params(9911).env['TMPDIR'] == os.environ['TMPDIR']
    assert os.environ.get('TMPDIR') == before, 'put back afterwards'


def test_a_check_runs_after_its_own_categorys_preparation(monkeypatch: pytest.MonkeyPatch) -> None:
    # no needs: a category, or one of its checks, runs on its own preparation (category_run.py)
    alone = _alone()
    order: list[str] = []
    run = sys.modules['test_all_tools.category_run']

    async def prepare(ctx: Any) -> None:
        order.append('prepare')
        ctx.lv = '12'

    async def body(ctx: Any) -> None:
        order.append('check ' + ctx.lv)

    monkeypatch.setitem(vars(run), 'preparation', lambda step: prepare)
    assert _run(alone, FakeDesigner(AGENTS), _in_category('params', 'check_x', body)) == 0
    assert order == ['prepare', 'check 12']


def test_checks_of_one_category_share_one_preparation_and_two_categories_get_one_each(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    alone = _alone()
    order: list[str] = []
    run = sys.modules['test_all_tools.category_run']

    def preparation(step: Any) -> Any:
        async def prepare(ctx: Any) -> None:
            order.append('prepare ' + step.__module__.split('.')[1])

        return prepare

    async def body(ctx: Any) -> None:
        order.append('check in ' + os.path.basename(ctx.scratch))

    monkeypatch.setitem(vars(run), 'preparation', preparation)
    checks = [_in_category('params', 'a', body), _in_category('params', 'b', body), _in_category('facts', 'c', body)]
    assert _run(alone, FakeDesigner(AGENTS), *checks, scratch=str(tmp_path)) == 0
    assert order == ['prepare params', 'check in params', 'check in params', 'prepare facts', 'check in facts']


def test_a_preparation_that_fails_gives_exit_code_2_and_runs_no_check(monkeypatch: pytest.MonkeyPatch) -> None:
    alone = _alone()
    ran: list[str] = []
    run = sys.modules['test_all_tools.category_run']

    async def prepare(ctx: Any) -> None:
        raise run.common.Unprepared('create_graph: refused')

    async def body(ctx: Any) -> None:
        ran.append('check')

    monkeypatch.setitem(vars(run), 'preparation', lambda step: prepare)
    c = FakeDesigner(AGENTS)
    assert _run(alone, c, _in_category('params', 'run', body)) == 2
    assert ran == [] and ('execute_designer_code', {'code': run.common.CLEAN}) in c.calls


def test_the_users_designer_is_refused_and_nothing_runs() -> None:
    alone = _alone()
    ran: list[str] = []

    async def a_check(ctx: Any) -> None:
        ran.append('check')

    c = FakeDesigner(USERS)
    assert _run(alone, c, a_check) == 2
    assert ran == [] and 'launch_designer' not in c.names() and 'execute_designer_code' not in c.names()


def test_a_designer_still_starting_is_refused_too(monkeypatch: pytest.MonkeyPatch) -> None:
    # a process with no bridge yet: whose it is can't be told, so it counts as the user's, as in the suite
    alone = _alone()
    monkeypatch.setitem(vars(alone), 'users_designer_running', lambda: True)
    c = FakeDesigner(None)
    assert _run(alone, c) == 2 and 'launch_designer' not in c.names()


def test_a_designer_is_started_when_none_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    alone = _alone()
    monkeypatch.setitem(vars(alone), 'users_designer_running', lambda: False)
    ran: list[str] = []

    async def a_check(ctx: Any) -> None:
        ran.append('check')

    c = FakeDesigner(None)
    assert _run(alone, c, a_check) == 0
    assert ran == ['check'] and 'launch_designer' in c.names()


def test_a_launch_that_fails_runs_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    alone = _alone()
    monkeypatch.setitem(vars(alone), 'users_designer_running', lambda: False)
    ran: list[str] = []

    async def a_check(ctx: Any) -> None:
        ran.append('check')

    assert _run(alone, FakeDesigner(None, launch='ERROR: Designer did not start'), a_check) == 2
    assert ran == []


def test_an_agents_designer_is_used_as_it_is() -> None:
    alone = _alone()
    c = FakeDesigner(AGENTS)
    assert _run(alone, c) == 0 and 'launch_designer' not in c.names()


def test_both_parts_of_the_guide_are_read_first_so_no_tool_is_refused() -> None:
    alone = _alone()
    c = FakeDesigner(AGENTS)
    _run(alone, c)
    assert c.names()[0] == 'get_guide'
    assert c.calls[1] == ('get_guide', {'part': 'scripting'}), 'the code tools refuse until it is read'


def test_a_failing_check_gives_exit_code_1_and_passing_ones_0() -> None:
    alone = _alone()
    from test_all_tools import common

    async def fails(ctx: Any) -> None:
        common.check('tool', 'a check that fails', False)

    async def passes(ctx: Any) -> None:
        common.check('tool', 'a check that passes', True)

    assert _run(alone, FakeDesigner(AGENTS), passes) == 0
    alone = _alone()
    from test_all_tools import common  # noqa: F811 (afresh, with the new module's record)

    assert _run(alone, FakeDesigner(AGENTS), passes, fails) == 1


def test_a_run_here_leaves_no_folder_in_the_temp_folder() -> None:
    # REVIEW.md TST-263: each call left an alone_unit_* folder behind, a plain pytest run after run
    alone = _alone()

    async def a_check(ctx: Any) -> None:
        pass

    before = set(glob.glob(os.path.join(tempfile.gettempdir(), 'alone_unit_*')))
    assert _run(alone, FakeDesigner(AGENTS), a_check) == 0
    assert set(glob.glob(os.path.join(tempfile.gettempdir(), 'alone_unit_*'))) == before


def test_the_checks_get_a_ctx_of_an_agents_designer() -> None:
    alone = _alone()
    seen: list[Any] = []

    async def a_check(ctx: Any) -> None:
        seen.append(ctx)

    c = FakeDesigner(AGENTS)
    scratch = tempfile.mkdtemp(prefix='alone_unit_')
    _run(alone, c, a_check, scratch=scratch)
    ctx = seen[0]
    assert ctx.c is c and ctx.was_running is False and 'def ' in ctx.helper_source
    assert os.path.dirname(ctx.scratch) == scratch, "a folder of its category's own, in the run's"
    shutil.rmtree(scratch)


def test_a_check_that_raises_fails_and_the_clean_up_still_runs() -> None:
    alone = _alone()

    async def raises(ctx: Any) -> None:
        raise RuntimeError('a parse that found nothing')

    c = FakeDesigner(AGENTS)
    assert _run(alone, c, raises) == 1
    from test_all_tools.common import CLEAN

    assert ('execute_designer_code', {'code': CLEAN}) in c.calls[-4:]


def test_the_setup_runs_before_the_checks_after_the_preparation(monkeypatch: pytest.MonkeyPatch) -> None:
    alone = _alone()
    order: list[str] = []

    async def step(ctx: Any) -> None:
        order.append('prepare')

    async def setup(ctx: Any) -> None:
        order.append('setup')

    async def body(ctx: Any) -> None:
        order.append('check')

    monkeypatch.setitem(vars(sys.modules['test_all_tools.category_run']), 'preparation', lambda s: step)
    assert _run(alone, FakeDesigner(AGENTS), _in_category('params', 'run', body), setup=setup) == 0
    assert order == ['prepare', 'setup', 'check']


def test_a_setup_that_fails_skips_the_checks_and_still_cleans_up() -> None:
    alone = _alone()
    from test_all_tools import common

    ran: list[str] = []

    async def setup(ctx: Any) -> None:
        common.check('tool', 'the environment', False)

    async def a_check(ctx: Any) -> None:
        ran.append('check')

    c = FakeDesigner(AGENTS)
    assert _run(alone, c, a_check, setup=setup) == 2
    assert ran == [] and ('execute_designer_code', {'code': common.CLEAN}) in c.calls


def test_a_setup_that_raises_skips_the_checks_too() -> None:
    alone = _alone()
    ran: list[str] = []

    async def setup(ctx: Any) -> None:
        raise RuntimeError('no graph')

    async def a_check(ctx: Any) -> None:
        ran.append('check')

    assert _run(alone, FakeDesigner(AGENTS), a_check, setup=setup) == 2 and ran == []


def test_each_run_gets_a_fresh_folder_inside_one_root(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    # never deleted while Designer runs (deleting the suite's crashed Designer twice: __main__.py); close() does it
    alone = _alone()
    monkeypatch.setitem(vars(alone), 'SCRATCH_ROOT', str(tmp_path / 'root'))
    first, second = alone.new_scratch(), alone.new_scratch()
    assert first != second and os.path.dirname(first) == os.path.dirname(second) == alone.scratch_root()
    assert alone.scratch_root().startswith(str(tmp_path / 'root') + os.sep)  # a folder per port in the root
    assert os.path.isdir(first) and os.path.isdir(second)


def test_close_quits_and_removes_the_folders_once_designer_has_ended(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    alone = _alone()
    monkeypatch.setitem(vars(alone), 'SCRATCH_ROOT', str(tmp_path / 'root'))
    alone.new_scratch()
    monkeypatch.setitem(vars(alone), 'designer_here', lambda: True)
    c = FakeDesigner(AGENTS)
    asyncio.run(alone.close_with(c))
    assert 'quit_designer' in c.names() and os.path.isdir(tmp_path / 'root')  # still running: kept
    assert c.names()[0] == 'get_guide'  # or quit_designer would be refused
    monkeypatch.setitem(vars(alone), 'designer_here', lambda: False)
    asyncio.run(alone.close_with(FakeDesigner(AGENTS)))
    assert not os.path.exists(tmp_path / 'root')


def test_close_leaves_the_users_designer_alone() -> None:
    # quit_designer refuses one no agent started anyway; close() doesn't even ask it
    alone = _alone()
    c = FakeDesigner(USERS)
    asyncio.run(alone.close_with(c))
    assert 'quit_designer' not in c.names()


def test_its_own_tool_calls_dont_count_as_the_suites_checks() -> None:
    # alone.py calls launch_designer, quit_designer and designer_status to manage its Designer: counted, they would
    # hide a tool the suite itself stopped checking (test_server.py, the coverage tests)
    from conftest import selftest_check_sources, selftest_sources

    assert 'alone.py' in selftest_sources() and 'alone.py' not in selftest_check_sources()
    assert set(selftest_check_sources()) == set(selftest_sources()) - {'alone.py'}


async def named_check(ctx: Any) -> None:
    """A check at module level, as a category's functions are."""


def test_each_check_is_announced_with_its_module(capsys: pytest.CaptureFixture[str]) -> None:
    # several categories in one call each print 'run': the module says which one the PASS and FAIL lines below belong to
    alone = _alone()
    _run(alone, FakeDesigner(AGENTS), named_check)
    assert 'alone: test_selftest_alone.named_check\n' in capsys.readouterr().out


def test_a_port_goes_to_the_fresh_server_and_to_the_checks(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    # ROADMAP item 49: the server, the requests the checks send themselves (raw_request, sd_run) and the snapshots go
    # with the port, so runs on their own ports, in Designers of their own, don't meet
    alone = _alone()
    from test_all_tools import common

    monkeypatch.delenv('SD_BRIDGE_PORT', raising=False)
    monkeypatch.delenv('SD_SNAPSHOT_DIR', raising=False)
    monkeypatch.setenv('SD_MCP_TEST_MARKER', 'here')
    port_before, params_before = common.PORT, common.PARAMS
    assert alone.server_params(None) is common.PARAMS
    with alone.on_port(9901, str(tmp_path)):
        # a second client's server too (common.cancel_from_second_client)
        assert common.PARAMS.env is not None and common.PARAMS.env['SD_BRIDGE_PORT'] == '9901'
        params = alone.server_params(9901)
        assert (params.command, params.args) == (common.PARAMS.command, common.PARAMS.args)
        assert params.env is not None and params.env['SD_BRIDGE_PORT'] == '9901'
        assert params.env['SD_SNAPSHOT_DIR'] == os.path.join(str(tmp_path), 'snapshots')
        # a variable stdio_client's minimal environment lacks (REVIEW.md TST-157: HOME is in it)
        assert params.env['SD_MCP_TEST_MARKER'] == 'here', 'not the minimal environment stdio_client gives otherwise'
        assert common.PORT == 9901 and os.environ['SD_BRIDGE_PORT'] == '9901'
    assert port_before == common.PORT
    assert common.PARAMS is params_before
    assert 'SD_BRIDGE_PORT' not in os.environ and 'SD_SNAPSHOT_DIR' not in os.environ


@pytest.mark.parametrize('port', [80, 65536])
def test_a_port_out_of_range_is_refused_before_anything_starts(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch, port: int
) -> None:
    alone = _alone()
    monkeypatch.setitem(vars(alone), 'SCRATCH_ROOT', str(tmp_path / 'root'))
    with pytest.raises(ValueError, match='port must be a number from 1024 to 65535'):
        alone.run(port=port)
    with pytest.raises(ValueError, match='port must be a number from 1024 to 65535'):
        alone.close(port=port)
    assert not os.path.exists(tmp_path / 'root')


def test_with_a_port_a_designer_running_elsewhere_doesnt_stop_it(monkeypatch: pytest.MonkeyPatch) -> None:
    # it may be on a port of its own: launch_designer, on the run's port, tells them apart (and refuses the user's)
    alone = _alone()
    monkeypatch.setitem(vars(alone), 'users_designer_running', lambda: True)
    c = FakeDesigner(None)
    assert int(asyncio.run(alone.run_with(c, [], None, 'scratch', port=9901))) == 0
    assert 'launch_designer' in c.names()
    refused = FakeDesigner(None, launch='ERROR: a Designer no agent started is running (process 11, on port 9877)')
    assert int(asyncio.run(alone.run_with(refused, [], None, 'scratch', port=9901))) == 2


def test_close_asks_quit_designer_when_the_status_fails() -> None:
    # REVIEW.md SRV-82: a Designer still running a plugin of the older bridge protocol fails designer_status, but
    # quit_designer ends one an agent started from its record alone (and refuses any other by itself)
    alone = _alone()
    c = FakeDesigner(None)
    asyncio.run(alone.close_with(c))
    assert 'quit_designer' in c.names()


def test_the_close_tests_never_remove_the_real_scratch_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-147, the same pattern: close_with asks designer_here (the real pgrep) and, with none running,
    # removes SCRATCH_ROOT, the real folder of the scratch runs; a test that sets neither reached it
    alone = _alone()
    removed: list[str] = []
    monkeypatch.setattr(shutil, 'rmtree', lambda path, **kw: removed.append(path))
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, '', ''))  # none runs
    asyncio.run(alone.close_with(FakeDesigner(USERS)))
    assert not [path for path in removed if str(path).startswith(alone.SCRATCH_ROOT)], removed


def test_the_suites_server_listens_for_the_suites_port(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-153: with SD_BRIDGE_PORT exported, common.PORT followed it but the server, started with
    # stdio_client's minimal environment, took 9877, so the checks read another port's record
    monkeypatch.setenv('SD_BRIDGE_PORT', '9900')
    try:
        _alone()  # the self-test's modules imported afresh, with the variable set
        from test_all_tools import common

        assert common.PORT == 9900
        assert common.PARAMS.env is not None and common.PARAMS.env['SD_BRIDGE_PORT'] == '9900'
    finally:  # no later test imports them with this port
        for name in [m for m in sys.modules if m == 'test_all_tools' or m.startswith('test_all_tools.')]:
            del sys.modules[name]


def test_another_runs_designer_doesnt_stop_a_run_on_the_servers_port(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-170: a Designer an agent started on another port (alone.run(port=...) leaves it open) was refused
    # as "running but not answering yet", which never resolves
    alone = _alone()
    monkeypatch.setitem(vars(alone), 'users_designer_running', lambda: False)  # it is another run's
    c = FakeDesigner(None)
    assert _run(alone, c) == 0 and 'launch_designer' in c.names()


def test_closing_a_port_removes_only_that_ports_folders(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-170: close_with removed the root of every run's folder, another port's run's included
    alone = _alone()
    root = tmp_path / 'root'
    monkeypatch.setitem(vars(alone), 'SCRATCH_ROOT', str(root))
    mine, theirs = root / 'port_9901' / 'run_a', root / 'port_9902' / 'run_b'
    mine.mkdir(parents=True)
    theirs.mkdir(parents=True)
    monkeypatch.setitem(vars(alone), 'designer_here', lambda: False)  # none on 9901 any more
    with alone.on_port(9901, str(tmp_path)):
        asyncio.run(alone.close_with(FakeDesigner(AGENTS)))
    assert not mine.exists() and theirs.is_dir()


def test_a_failing_process_listing_keeps_the_folders_and_starts_nothing(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md INS-27: Designer's processes that can't be listed are not "none running"
    alone = _alone()
    from test_all_tools import common

    def fails() -> bool:
        raise common.NoListing("Designer's processes couldn't be listed (pgrep exit code 2)")

    root = tmp_path / 'root'
    monkeypatch.setitem(vars(alone), 'SCRATCH_ROOT', str(root))
    alone.new_scratch()
    for name in ('designer_here', 'users_designer_running'):
        monkeypatch.setitem(vars(alone), name, fails)
    asyncio.run(alone.close_with(FakeDesigner(AGENTS)))
    assert os.path.isdir(alone.scratch_root())
    c = FakeDesigner(None)
    assert _run(alone, c) == 2 and 'launch_designer' not in c.names()


class LeavesALibrary(FakeDesigner):
    """A Designer whose clean-up fails: a library package the category loaded is still there after it."""

    def __init__(self) -> None:
        super().__init__(AGENTS)
        self.listed = 0

    async def __call__(self, name: str, args: dict[str, Any] | None = None) -> Any:
        if name == 'execute_designer_code' and 'unloadUserPackage' not in (args or {}).get('code', ''):
            self.calls.append((name, args or {}))
            self.listed += 1
            return _result('LIBS=' if self.listed == 1 else 'LIBS=/library/noise.sbs')
        return await super().__call__(name, args)


def test_a_clean_up_that_fails_is_exit_code_2_though_every_check_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-238: only a passing clean-up was ever tested
    alone = _alone()
    monkeypatch.setitem(vars(sys.modules['test_all_tools.category_run']), 'preparation', lambda step: None)
    ran: list[str] = []

    async def passes(ctx: Any) -> None:
        ran.append('check')
        alone.common.check('t', 'x', True)

    assert _run(alone, LeavesALibrary(), _in_category('params', 'run', passes)) == 2
    assert ran == ['check'], "prepared, so the exit code is the clean-up's"
