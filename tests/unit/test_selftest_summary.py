"""The live self-test's summary (REVIEW.md TST-1): a tool counts as covered only when it had a
check that ran; one whose checks were all skipped is listed, not counted."""

import asyncio
import importlib
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from conftest import SELFTEST_DIR, selftest_sources


def _selftest() -> Any:  # a module imported by name: PyCharm can't see its names
    """The self-test's index (tests/test_all_tools/__main__.py), imported afresh with all its modules,
    so each test starts with an empty check record."""
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    for name in [m for m in sys.modules if m == 'test_all_tools' or m.startswith('test_all_tools.')]:
        del sys.modules[name]
    return importlib.import_module('test_all_tools.__main__')


def test_skipped_only_tools_are_not_counted_as_covered() -> None:
    summary, ok = _selftest().summarize(['a', 'b', 'c'], {'a': [True], 'b': []}, [('b', 'closes Designer')])
    assert '1/3 tools covered' in summary
    assert "only skipped: ['b']" in summary and "NOT covered: ['c']" in summary
    assert not ok  # c has no check at all


def test_skips_alone_do_not_fail_the_run() -> None:
    # quit_designer is always skipped while your own Designer runs; that is reported, not a failure
    summary, ok = _selftest().summarize(['a', 'b'], {'a': [True, True], 'b': []}, [('b', 'x')])
    assert ok and '1/2 tools covered' in summary and "only skipped: ['b']" in summary
    assert 'checks passed: 2/2; skipped: 1; tools with failures: none' in summary


def _step(module: str, name: str, raises: bool = False, body: Any = None) -> Any:
    """A step as the index runs it: a coroutine function known by its module and name."""

    async def step(ctx: Any) -> None:
        if raises:
            raise ValueError('it stopped here')
        if body is not None:
            await body(ctx)

    step.__module__, step.__qualname__ = 'test_all_tools.%s.checks' % module, name
    return step


def _clock(monkeypatch: pytest.MonkeyPatch, *readings: float) -> None:
    """time.perf_counter answering these readings in turn; asyncio's own clock is time.monotonic."""
    answers = iter(readings)
    monkeypatch.setattr(time, 'perf_counter', lambda: next(answers))


def test_each_step_is_timed_under_its_category_name(monkeypatch: pytest.MonkeyPatch) -> None:
    # `run` is the whole category, named by its folder (<category>/checks.py); another function of it
    # (a check run on its own) keeps its name
    selftest = _selftest()
    _clock(monkeypatch, 10.0, 12.5, 20.0, 21.0)
    steps = [_step('params', 'run'), _step('lifecycle', 'check_x')]
    asyncio.run(selftest.run_steps(SimpleNamespace(), steps, isolated=False))
    assert selftest.times == {'params': 2.5, 'lifecycle.check_x': 1.0}


def _result(t: str) -> Any:
    return SimpleNamespace(content=[SimpleNamespace(type='text', text=t)], is_error=False)


class FakeDesigner:
    """c(name, args): the library packages listed as none, the clean-up answered, any other tool 'ok'."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def __call__(self, name: str, args: dict[str, Any] | None = None) -> Any:
        code = (args or {}).get('code', '')
        common = sys.modules['test_all_tools.common']
        self.calls.append('clean-up' if name == 'execute_designer_code' and code == common.CLEAN else name)
        return _result('removed 0' if 'unloadUserPackage' in code else 'LIBS=')


def _isolated_run(
    monkeypatch: pytest.MonkeyPatch, selftest: Any, tmp_path: Path, steps: list[Any], prepare: Any = None
) -> FakeDesigner:
    """run_steps over a fake Designer, every category's preparation `prepare` (none when omitted); both put back after
    the test (REVIEW.md TST-244)."""
    c = FakeDesigner()
    run = sys.modules['test_all_tools.category_run']
    monkeypatch.setitem(vars(run), 'PAUSE_S', 0)
    monkeypatch.setitem(vars(run), 'preparation', lambda step: prepare)
    ctx = selftest.Ctx(c=c, s=None, scratch=str(tmp_path), helper_source='h', was_running=False)
    asyncio.run(selftest.run_steps(ctx, steps))
    return c


def test_each_category_runs_on_a_ctx_of_its_own_after_its_own_preparation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # no category sees what another prepared or left (category_run.py); each is cleaned up after it
    selftest = _selftest()
    seen: list[tuple[str, Any]] = []

    async def prepare(ctx: Any) -> None:
        ctx.G = {'graph': 'mcp_selftest'}
        seen.append(('prepare', ctx))

    async def body(ctx: Any) -> None:
        seen.append(('check', ctx))

    c = _isolated_run(
        monkeypatch, selftest, tmp_path, [_step('params', 'run', body=body), _step('facts', 'run', body=body)], prepare
    )
    assert [what for what, _ in seen] == ['prepare', 'check', 'prepare', 'check']
    assert seen[0][1] is seen[1][1] and seen[2][1] is seen[3][1] and seen[1][1] is not seen[3][1]
    assert [os.path.basename(ctx.scratch) for _, ctx in seen[1::2]] == ['params', 'facts']
    assert c.calls.count('clean-up') == 2


def test_a_category_that_raises_fails_and_the_next_one_still_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # each prepares its own environment: one stopping early leaves the next one nothing to miss
    selftest = _selftest()
    ran: list[str] = []

    async def body(ctx: Any) -> None:
        ran.append('params')

    _isolated_run(
        monkeypatch, selftest, tmp_path, [_step('facts', 'run', raises=True), _step('params', 'run', body=body)]
    )
    assert ran == ['params'] and selftest.results['self-test'].count(False) == 1
    assert set(selftest.times) == {'facts', 'params'}


def test_a_failed_preparation_stops_only_its_category(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    selftest = _selftest()
    ran: list[str] = []
    common = sys.modules['test_all_tools.common']

    async def prepare(ctx: Any) -> None:
        if os.path.basename(ctx.scratch) == 'facts':
            raise common.Unprepared('apply_edits: refused')

    async def body(ctx: Any) -> None:
        ran.append(os.path.basename(ctx.scratch))

    steps = [_step('facts', 'run', body=body), _step('params', 'run', body=body)]
    _isolated_run(monkeypatch, selftest, tmp_path, steps, prepare)
    assert ran == ['params'] and selftest.results['self-test'].count(False) == 1


def test_the_summary_lists_the_times_slowest_first_with_their_total() -> None:
    summary, ok = _selftest().summarize(['a'], {'a': [True]}, [], {'params': 2.5, 'facts': 96.04, 'bridge': 10.0})
    assert ok
    lines = summary.splitlines()
    start = lines.index('time per category, slowest first (total 108.5 s):')
    assert [l.split() for l in lines[start + 1 :]] == [
        ['96.0', 's', 'facts'],
        ['10.0', 's', 'bridge'],
        ['2.5', 's', 'params'],
    ]


def test_a_run_with_no_times_prints_none() -> None:
    summary, _ = _selftest().summarize(['a'], {'a': [True]}, [])
    assert 'time per category' not in summary


def test_the_run_prints_the_times_it_recorded(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # the record reaches the summary main() prints, not only run_steps' dictionary
    selftest = _selftest()
    selftest.times['facts'] = 96.0
    selftest.results['a'] = [True]
    selftest.STATE['was_running'] = False
    monkeypatch.setattr(selftest.asyncio, 'run', lambda coroutine: (coroutine.close(), ['a'])[1])
    monkeypatch.setitem(vars(selftest), 'designer_here', lambda: False)
    monkeypatch.setitem(vars(selftest), 'crash_dumps', set)
    with pytest.raises(SystemExit):
        selftest.one_run()
    assert 'time per category, slowest first (total 96.0 s):' in capsys.readouterr().out


def test_a_failed_check_fails_the_run() -> None:
    summary, ok = _selftest().summarize(['a'], {'a': [True, False]}, [])
    assert not ok and 'tools with failures: a' in summary


def test_cleanup_covers_every_graph_the_self_test_creates() -> None:
    # REVIEW.md TST-9: the size-inheritance check's 'inherit_*' graphs weren't matched by CLEAN,
    # so they stayed open if the check failed midway
    import re

    src = '\n'.join(selftest_sources().values())
    created = [n for n in re.findall(r"setIdentifier\('([^']*)'", src) if n != '%s']  # '%s' is DUP_GRAPH
    assert created and all(name.startswith('mcp_selftest') for name in created), created
    assert ".startswith('mcp_selftest')" in _selftest().CLEAN


def test_a_check_that_is_not_a_bool_is_counted() -> None:
    # REVIEW.md TST-29: check() stored the condition as given; `refs and not missing` with no refs is
    # [], and summarize()'s sum then raised TypeError, so no summary was printed
    selftest = _selftest()  # imported afresh: no checks recorded yet
    selftest.check('tool', 'empty list', [])
    selftest.check('tool', 'none', None)
    text, ok = selftest.summarize(['tool'], selftest.results, [])
    assert not ok and 'checks passed: 0/2' in text


def test_a_bridge_error_in_the_library_clean_up_is_a_failed_check_not_a_crash() -> None:
    # REVIEW.md TST-33: an error answer there raised AttributeError in the self-test's finally,
    # skipping the rest of its clean-up (the snapshots, putting the user's graph back, the quit)
    import asyncio
    from types import SimpleNamespace

    selftest = _selftest()

    async def bridge_error(name: str, args: dict[str, Any] | None = None) -> SimpleNamespace:
        return SimpleNamespace(content=[SimpleNamespace(type='text', text='Error executing tool: bridge busy')])

    asyncio.run(selftest.restore_library_packages(bridge_error, []))
    assert selftest.results['self-test'] == [False]


@pytest.mark.parametrize('designer_running', [True, False])
def test_the_scratch_folder_is_only_deleted_once_designer_is_closed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, designer_running: bool
) -> None:
    # REVIEW.md PLG-18 (and PLG-9): deleting it while Designer ran crashed Designer twice, in its file
    # watcher; with a Designer still running it is left in the OS temp folder, and the path printed
    selftest = _selftest()
    scratch = tmp_path / 'sd_mcp_selftest_x'
    scratch.mkdir()
    (scratch / 'graph.sbs').write_text('x')
    monkeypatch.setattr(tempfile, 'mkdtemp', lambda prefix: str(scratch))

    async def run(scratch: str, *args: Any) -> list[str]:
        selftest.STATE['was_running'] = designer_running
        return []

    monkeypatch.setitem(vars(selftest), 'run', run)
    monkeypatch.setitem(vars(selftest), 'designer_here', lambda: designer_running)
    monkeypatch.setitem(vars(selftest), 'new_crash_dumps', lambda before, wait_s=10: set())
    with pytest.raises(SystemExit):
        selftest.one_run()
    assert scratch.exists() == designer_running
    assert (str(scratch) in capsys.readouterr().out) == designer_running


def test_a_bridge_error_reading_the_library_packages_at_the_start_is_a_failed_check() -> None:
    # REVIEW.md TST-51: this ran before the try/finally, unguarded, so an error answer ended the run
    # with no summary and a Designer the self-test started was never quit
    import asyncio
    from types import SimpleNamespace

    selftest = _selftest()

    async def bridge_error(name: str, args: dict[str, Any] | None = None) -> SimpleNamespace:
        return SimpleNamespace(content=[SimpleNamespace(type='text', text='Error executing tool: bridge busy')])

    assert asyncio.run(selftest.library_packages(bridge_error)) is None
    assert selftest.results['self-test'] == [False]
    asyncio.run(selftest.restore_library_packages(bridge_error, None))  # then skipped, not a crash
    assert selftest.skipped == [('self-test', 'leaves the library packages loaded as it found them')]


def test_a_bridge_error_reading_the_editors_graph_at_the_start_is_a_failed_check() -> None:
    # REVIEW.md TST-59: this parse ran before the try/finally, unguarded, like TST-51's
    import asyncio
    from types import SimpleNamespace

    selftest = _selftest()

    async def bridge_error(name: str, args: dict[str, Any] | None = None) -> SimpleNamespace:
        return SimpleNamespace(content=[SimpleNamespace(type='text', text='Error executing tool: bridge busy')])

    assert asyncio.run(selftest.editor_graph(bridge_error)) == ''
    assert selftest.results['self-test'] == [False]


def test_only_the_runs_start_records_the_users_graph() -> None:
    # REVIEW.md TST-271: editor_graph keeps the graph it reads, for the end of the run to put back in the user's editor;
    # link_display's check called it with the self-test's graph there, which the clean-up then unloaded
    selftest = _selftest()
    callers = sorted(
        name
        for name, source in selftest_sources().items()
        if name != 'common.py' and re.search(r'\beditor_graph\(', source)
    )
    assert callers == ['__main__.py']
    assert '_selftest_user_graph' not in selftest.common.GRAPH_IN_EDITOR, 'a read for checks keeps nothing'


def test_every_category_function_is_run() -> None:
    # REVIEW.md TST-74: the coverage scans read every module of the folder, so a category function left
    # out of CATEGORIES would count as covering its tools, parameters and ops while it never runs
    import inspect
    import pkgutil

    selftest = _selftest()
    package = sys.modules['test_all_tools']
    run = set(selftest.CATEGORIES) | {selftest.lifecycle.run}  # lifecycle: a worker of its own (workers.py)
    defined: set[Any] = set()
    # every module of every category's folder (<category>/checks.py and its helpers), not the Designer scripts
    found = [
        info.name
        for info in pkgutil.walk_packages(package.__path__, 'test_all_tools.')
        if info.name.count('.') == 2 and '.designer_scripts' not in info.name
    ]
    assert len({name.split('.')[1] for name in found}) == len(run), found
    for name in found:
        module = importlib.import_module(name)
        source = inspect.getsource(module)
        defined |= {
            f
            for f in vars(module).values()
            if inspect.iscoroutinefunction(f)
            and f.__module__ == module.__name__
            # a check of its own, check_<what>(ctx), runs when a category function of its module awaits it
            # (the live-check skill); alone.py runs it on its own too
            and not (f.__name__.startswith('check_') and re.search(r'await\s+%s\(' % f.__name__, source))
            # a category's preparation: category_run.py runs it before the category
            and not (name.endswith('.preparations') and f.__name__ == 'prepare')
        }
    assert defined, 'no category functions found'
    missing = sorted('%s.%s' % (f.__module__.split('.')[1], f.__name__) for f in defined - run)
    assert not missing, 'category functions not in CATEGORIES (never run): %s' % missing


def _run_designer_script(reply: str, is_error: bool = False) -> list[bool]:
    """The checks recorded under run_designer_script by one designer_script call with this reply."""
    _selftest()
    common = importlib.import_module('test_all_tools.common')
    common.results.pop('run_designer_script', None)
    result = SimpleNamespace(content=[SimpleNamespace(type='text', text=reply)], is_error=is_error)

    async def call(name: str, args: dict[str, Any] | None = None) -> Any:
        return result

    assert asyncio.run(common.designer_script(call, 'facts/a_script', graph='g')) is result
    return list(common.results.pop('run_designer_script', []))


def test_a_script_that_raises_fails_the_run() -> None:
    """A traceback shows the failing source line, and its output token with it, so a check reading that token can
    pass having measured nothing (REVIEW.md TST-117, TST-125): the failure is recorded where it happens."""
    assert _run_designer_script('NODES=3\n\n--- ERROR ---\nTraceback (most recent call last):\n') == [False]
    assert _run_designer_script('no such file', is_error=True) == [False]


def test_a_script_that_runs_adds_no_check() -> None:
    assert _run_designer_script('NODES=3\n') == []


def test_a_failed_script_shows_its_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Setup scripts discard their result, so this is the only place it shows (REVIEW.md TST-132)."""
    trace = 'Traceback (most recent call last):\n  File "%s", line 3\nValueError: the real reason' % ('/long/path' * 30)
    assert _run_designer_script('\n--- ERROR ---\n' + trace) == [False]
    printed = capsys.readouterr().out
    fail_line = next(l for l in printed.splitlines() if l.startswith('FAIL'))
    assert 'ValueError: the real reason' in fail_line
    assert trace in printed


def test_a_raising_lifecycle_check_is_a_failed_check_not_the_end_of_the_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-152: lifecycle.run was awaited bare in run()'s finally, so an unexpected answer (one more line to
    # unpack, a record that isn't JSON) ended the run with a traceback and no summary; it goes through run_steps, as
    # the categories do
    selftest = _selftest()
    source = Path(SELFTEST_DIR, '__main__.py').read_text(encoding='utf-8')
    assert not re.search(r'await\s+lifecycle\.run\(', source), 'awaited outside run_steps'
    assert re.search(r'run_steps\(\s*ctx,\s*\[lifecycle\.run\],\s*isolated=False\s*\)', source)

    async def raises(ctx: Any) -> None:
        raise ValueError('too many values to unpack (expected 2)')

    asyncio.run(selftest.run_steps(SimpleNamespace(), [raises], isolated=False))
    assert selftest.results['self-test'] == [False]
    assert 'too many values to unpack' in capsys.readouterr().out


def test_another_runs_designer_isnt_taken_for_the_users(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-170: with another run's Designer open on its own port (any Designer on the machine counted), a run
    # took itself for one in the user's Designer
    selftest = _selftest()
    common = sys.modules['test_all_tools.common']
    monkeypatch.setattr(sys, 'platform', 'darwin')  # on Windows nothing is recorded (REVIEW.md TST-269)
    monkeypatch.setitem(vars(common), 'designer_pids', lambda: [12])
    monkeypatch.setitem(vars(common), 'agents_designers', lambda: {9902: 12})
    monkeypatch.setitem(vars(common), 'PORT', 9877)
    monkeypatch.setitem(vars(common), 'designer_alive', lambda: True)  # any Designer: another run's is up
    assert common.designer_here() is False and common.users_designer_running() is False

    async def no_designer_here(name: str, args: dict[str, Any] | None = None) -> SimpleNamespace:
        return SimpleNamespace(is_error=True, content=[SimpleNamespace(type='text', text='Designer is not reachable')])

    assert asyncio.run(selftest.already_running(no_designer_here)) is False
    source = Path(SELFTEST_DIR, '__main__.py').read_text(encoding='utf-8')
    assert 'designer_alive' not in source and re.search(r'already_running\(c\)', source)


def test_the_scratch_folder_goes_once_the_runs_own_designer_is_ended(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md TST-192: whether a Designer ran was asked before end_own_designer() ended the run's own, and that
    # answer kept the folder "since Designer is running"
    selftest = _selftest()
    monkeypatch.setattr(sys, 'platform', 'darwin')  # the pool's: on Windows there is no worker (REVIEW.md TST-269)
    scratch = tmp_path / 'sd_mcp_selftest_x'
    scratch.mkdir()
    monkeypatch.setattr(tempfile, 'mkdtemp', lambda prefix: str(scratch))
    up = [True]  # the worker's own, left open by a failed check

    async def run(scratch: str, *args: Any) -> list[str]:
        selftest.STATE['was_running'] = False
        return []

    monkeypatch.setitem(vars(selftest), 'run', run)
    monkeypatch.setitem(vars(selftest), 'agents_designers', lambda: {selftest.common.PORT: 1} if up[0] else {})
    monkeypatch.setitem(vars(selftest), 'end_own_designer', lambda: up.__setitem__(0, False))
    monkeypatch.setitem(vars(selftest), 'crash_dumps', lambda ports=(): set())
    with pytest.raises(SystemExit):
        selftest.one_run(worker='undo', results_file=str(tmp_path / 'undo.json'))
    assert not up[0] and not scratch.exists(), 'kept for the Designer just ended'


def test_a_workers_results_carry_its_quits_forced_during_their_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-293: what lifecycle's normal closes recorded (common.normal_close), for the pool to count
    selftest = _selftest()
    monkeypatch.setitem(vars(selftest.common), 'forced_in_shutdown', ['the modal close'])
    assert selftest._ended()['forced_in_shutdown'] == ['the modal close']
