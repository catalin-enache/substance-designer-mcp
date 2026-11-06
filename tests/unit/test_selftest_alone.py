"""tests/test_all_tools/alone.py: chosen checks of the live self-test, run on their own in an environment built for
them, the way agents see a check fail and then pass while working (AGENTS.md, Running the tests). Designer is
replaced by a fake that answers each tool by name."""

import asyncio
import importlib
import os
import sys
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
    vars(alone)['PAUSE_S'] = 0  # no Designer to wait for
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
    return int(asyncio.run(alone.run_with(c, list(checks), kw.get('needs', ()), kw.get('setup'), 'scratch')))


def test_needs_come_with_what_they_rely_on_first() -> None:
    alone = _alone()
    assert alone.resolve([]) == []
    assert alone.resolve(['graph']) == ['graph']
    assert alone.resolve(['png', 'graph']) == ['graph', 'png']
    # wire's checks read what params' set (Samples = 16): measured, a live run of 'sbs' without it failed one
    assert alone.resolve(['wired']) == ['graph', 'params', 'wired']
    assert alone.resolve(['sbs']) == ['graph', 'params', 'wired', 'png', 'sbs']


def test_an_unknown_need_is_refused_naming_the_known_ones() -> None:
    alone = _alone()
    with pytest.raises(ValueError, match=r"no_such.*'graph'"):
        alone.resolve(['no_such'])


def test_needs_are_the_suites_own_setup_steps() -> None:
    # the suite's functions themselves, not copies of them: the environment is the one the suite builds
    alone = _alone()
    from test_all_tools import bitmaps, graph_edit, params, save

    assert alone.NEEDS['graph'][1] is graph_edit.create and alone.NEEDS['wired'][1] is graph_edit.wire
    assert alone.NEEDS['params'][1] is params.run
    assert alone.NEEDS['png'][1] is bitmaps.run and alone.NEEDS['sbs'][1] is save.run


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
    monkeypatch.setitem(vars(alone), 'designer_alive', lambda: True)
    c = FakeDesigner(None)
    assert _run(alone, c) == 2 and 'launch_designer' not in c.names()


def test_a_designer_is_started_when_none_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    alone = _alone()
    monkeypatch.setitem(vars(alone), 'designer_alive', lambda: False)
    ran: list[str] = []

    async def a_check(ctx: Any) -> None:
        ran.append('check')

    c = FakeDesigner(None)
    assert _run(alone, c, a_check) == 0
    assert ran == ['check'] and 'launch_designer' in c.names()


def test_a_launch_that_fails_runs_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    alone = _alone()
    monkeypatch.setitem(vars(alone), 'designer_alive', lambda: False)
    ran: list[str] = []

    async def a_check(ctx: Any) -> None:
        ran.append('check')

    assert _run(alone, FakeDesigner(None, launch='ERROR: Designer did not start'), a_check) == 2
    assert ran == []


def test_an_agents_designer_is_used_as_it_is() -> None:
    alone = _alone()
    c = FakeDesigner(AGENTS)
    assert _run(alone, c) == 0 and 'launch_designer' not in c.names()


def test_the_guide_is_read_first_so_no_result_carries_the_reminder() -> None:
    alone = _alone()
    c = FakeDesigner(AGENTS)
    _run(alone, c)
    assert c.names()[0] == 'get_guide'


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


def test_the_checks_get_a_ctx_of_an_agents_designer() -> None:
    alone = _alone()
    seen: list[Any] = []

    async def a_check(ctx: Any) -> None:
        seen.append(ctx)

    c = FakeDesigner(AGENTS)
    _run(alone, c, a_check)
    ctx = seen[0]
    assert ctx.c is c and ctx.scratch == 'scratch' and ctx.was_running is False and 'def ' in ctx.helper_source


def test_a_check_that_raises_fails_and_the_clean_up_still_runs() -> None:
    alone = _alone()

    async def raises(ctx: Any) -> None:
        raise RuntimeError('a parse that found nothing')

    c = FakeDesigner(AGENTS)
    assert _run(alone, c, raises) == 1
    from test_all_tools.common import CLEAN

    assert ('execute_designer_code', {'code': CLEAN}) in c.calls[-4:]


def test_the_setup_runs_before_the_checks_needs_first() -> None:
    alone = _alone()
    order: list[str] = []

    async def step(ctx: Any) -> None:
        order.append('graph')

    async def setup(ctx: Any) -> None:
        order.append('setup')

    async def a_check(ctx: Any) -> None:
        order.append('check')

    alone.NEEDS['graph'] = ((), step)
    assert _run(alone, FakeDesigner(AGENTS), a_check, needs=['graph'], setup=setup) == 0
    assert order == ['graph', 'setup', 'check']


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
    assert first != second and os.path.dirname(first) == os.path.dirname(second) == str(tmp_path / 'root')
    assert os.path.isdir(first) and os.path.isdir(second)


def test_close_quits_and_removes_the_folders_once_designer_has_ended(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    alone = _alone()
    monkeypatch.setitem(vars(alone), 'SCRATCH_ROOT', str(tmp_path / 'root'))
    alone.new_scratch()
    monkeypatch.setitem(vars(alone), 'designer_alive', lambda: True)
    c = FakeDesigner(AGENTS)
    asyncio.run(alone.close_with(c))
    assert 'quit_designer' in c.names() and os.path.isdir(tmp_path / 'root')  # still running: kept
    assert c.names()[0] == 'get_guide'  # no reminder in front of what it prints
    monkeypatch.setitem(vars(alone), 'designer_alive', lambda: False)
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
