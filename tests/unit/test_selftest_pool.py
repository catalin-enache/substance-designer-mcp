"""The live self-test as a pool (workers.py): each category in a Designer of its own, started for it and closed
after it, `--workers N` of them at once, the next starting as soon as one ends (tests/test_all_tools/workers.py);
lifecycle first, holding a lock while no other Designer may start (launch_lock.py); one wait for crash dumps at the
end. No Designer: processes, ports and sessions are fakes."""

import asyncio
import inspect
import json
import os
import sys
import time
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fake_defaults import FakeDefaults
from selftest_fakes import Designer, Done, FakeRun, OpenGate, fresh, part, pool, unit_log

import designer_preferences
import project_constants
from conftest import SELFTEST_DIR

REAL_POPEN = __import__('subprocess').Popen  # before any test replaces it


@pytest.fixture(autouse=True)
def no_real_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test here starts a process: a real run would start Designers (and, from the unit suite inside it, this test
    again). A test faking the workers' processes replaces Popen itself."""

    def refused(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('a unit test started a process: %s' % (args[0] if args else kwargs))

    import subprocess

    monkeypatch.setattr(subprocess, 'Popen', refused)


# --- the lock on launches (launch_lock.py)


def test_without_a_pool_the_lock_holds_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    # a scratch run or one run: nothing else of the run starts Designers
    lock = fresh('launch_lock')
    for name in (lock.LOCK_ENV, lock.CHANGING_ENV):
        monkeypatch.delenv(name, raising=False)
    with lock.held(), lock.changing('facts'):
        pass


def test_the_lock_waits_for_the_changes_in_flight_and_is_gone_after(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lock = fresh('launch_lock')
    gate = lock.Gate(str(tmp_path))
    monkeypatch.setattr(os, 'environ', {**os.environ, **gate.env()})
    assert gate.try_begin('render')  # a Designer starting, not answering yet
    seen: list[str] = []

    def sleep(seconds: float) -> None:
        seen.append('waited')
        gate.end('render')  # it answers

    with lock.held(sleep=sleep):
        assert os.path.exists(gate.lock) and seen == ['waited']
        assert not gate.try_begin('facts'), 'no Designer starts while it holds'
        assert os.listdir(gate.changing) == [], 'a refused start leaves no mark'
    assert not os.path.exists(gate.lock)
    assert gate.try_begin('facts')


def test_the_lock_never_waits_for_the_start_of_the_worker_holding_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # seen live: lifecycle takes the lock before its own launch, and the pool clears its start's mark only once its
    # Designer answers: waiting for that mark, it waited out the whole timeout (300 s)
    lock = fresh('launch_lock')
    gate = lock.Gate(str(tmp_path))
    monkeypatch.setattr(os, 'environ', {**os.environ, **gate.env()})
    assert gate.try_begin('lifecycle')
    with lock.held(own='lifecycle', sleep=lambda s: pytest.fail('waited for its own start')):
        pass


def test_a_designer_quitting_waits_for_the_lock_and_marks_itself_meanwhile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lock = fresh('launch_lock')
    gate = lock.Gate(str(tmp_path))
    monkeypatch.setattr(os, 'environ', {**os.environ, **gate.env()})
    Path(gate.lock).write_text('')
    waits: list[str] = []

    def sleep(seconds: float) -> None:
        waits.append('waited')
        assert os.listdir(gate.changing) == [], 'no mark while it waits: the lock would wait for it'
        os.remove(gate.lock)  # lifecycle's window ends

    with lock.changing('undo', sleep=sleep):
        assert waits == ['waited'] and os.listdir(gate.changing) == ['undo']
    assert os.listdir(gate.changing) == []


def test_the_lock_gives_up_waiting_after_its_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # a Designer that never answers mustn't hold lifecycle forever: its check then says what it found
    lock = fresh('launch_lock')
    gate = lock.Gate(str(tmp_path))
    monkeypatch.setattr(os, 'environ', {**os.environ, **gate.env()})
    assert gate.try_begin('render')
    clock = iter(range(0, 1000, 100))
    with lock.held(timeout_s=250, sleep=lambda s: None, clock=lambda: next(clock)):
        pass
    assert not os.path.exists(gate.lock)


def test_the_lock_names_its_holder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-235: the pool removes the lock of a worker that ended holding it, and only that worker's
    lock = fresh('launch_lock')
    gate = lock.Gate(str(tmp_path))
    monkeypatch.setattr(os, 'environ', {**os.environ, **gate.env()})
    with lock.held(own='lifecycle', sleep=lambda s: None):
        assert Path(gate.lock).read_text() == 'lifecycle'


def test_a_worker_ended_leaves_no_mark_and_no_lock_of_its_own(tmp_path: Path) -> None:
    # REVIEW.md TST-235: killed inside a window (a SIGKILL, its Python crashing), its finally never ran
    lock = fresh('launch_lock')
    gate = lock.Gate(str(tmp_path))
    Path(gate.lock).write_text('lifecycle')
    for name in ('render', 'lifecycle'):
        Path(gate.changing, name).write_text('')
    gate.worker_ended('render')
    assert os.path.exists(gate.lock), "another worker's lock stays"
    assert os.listdir(gate.changing) == ['lifecycle']
    gate.worker_ended('lifecycle')
    assert not os.path.exists(gate.lock) and os.listdir(gate.changing) == []


def test_a_quit_waits_for_the_lock_no_longer_than_its_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-235: a lock nobody removes held every quit, and so the pool, for ever
    lock = fresh('launch_lock')
    gate = lock.Gate(str(tmp_path))
    monkeypatch.setattr(os, 'environ', {**os.environ, **gate.env()})
    Path(gate.lock).write_text('lifecycle')
    clock = iter(range(0, 10_000, 100))
    with lock.changing('render', sleep=lambda s: None, timeout_s=250, clock=lambda: next(clock)):
        assert os.listdir(gate.changing) == ['render']
    assert os.listdir(gate.changing) == []


# --- the scheduler


def _schedule(workers: Any, run: FakeRun, names: list[str], slots: int, gate: Any = None, **kw: Any) -> Any:
    return workers.schedule(
        names,
        slots,
        start=run.start,
        answering=lambda name: name in run.answering,
        gate=gate or OpenGate(),
        exclusive=kw.get('exclusive', set()),
        solo=kw.get('solo', set()),
        sleep=run.sleep,
    )


def test_a_pool_starts_the_next_one_as_soon_as_any_ends() -> None:
    # not batches: the slot a short one frees is taken at once (workers.py)
    workers = fresh('workers')
    run = FakeRun()
    run.plan = {1: ['b'], 5: ['a', 'c'], 6: ['d']}
    codes = _schedule(workers, run, ['a', 'b', 'c', 'd'], 2)
    assert codes == {'a': 0, 'b': 0, 'c': 0, 'd': 0}
    assert run.started == ['a', 'b', 'c', 'd']
    assert run.at_once[0] == {'a', 'b'} and run.at_once[1] == {'a', 'c'}, 'c took the slot b freed'
    assert max(len(names) for names in run.at_once) <= 2


def test_one_slot_runs_them_one_after_the_other() -> None:
    workers = fresh('workers')
    run = FakeRun()
    run.plan = {1: ['a'], 2: ['b'], 3: ['c']}
    _schedule(workers, run, ['a', 'b', 'c'], 1)
    assert all(len(names) <= 1 for names in run.at_once) and run.started == ['a', 'b', 'c']


def test_the_categories_using_the_clipboard_never_run_at_once() -> None:
    workers = fresh('workers')
    run = FakeRun()
    run.plan = {3: ['facts'], 4: ['x'], 6: ['editor_a', 'y'], 7: ['editor_b']}
    _schedule(
        workers,
        run,
        ['facts', 'editor_a', 'x', 'y', 'editor_b'],
        3,
        exclusive={'facts', 'editor_a', 'editor_b'},
    )
    for names in run.at_once:
        assert len(names & {'facts', 'editor_a', 'editor_b'}) <= 1, names
    assert run.started[:3] == ['facts', 'x', 'y'], 'the others start meanwhile, in their order'


def test_the_pool_goes_on_when_a_worker_dies_holding_the_lock(tmp_path: Path) -> None:
    # REVIEW.md TST-235: lifecycle killed inside a window left launch.lock; no start was allowed again, and schedule
    # never returned
    workers = fresh('workers')
    gate = sys.modules['test_all_tools.launch_lock'].Gate(str(tmp_path))
    run = FakeRun()
    run.plan = {3: ['lifecycle'], 6: ['a']}

    def sleep(seconds: float) -> None:
        FakeRun.sleep(run, seconds)
        if run.ticks == 1:
            Path(gate.lock).write_text('lifecycle')  # its window, which it never ends: it dies at tick 3
            Path(gate.changing, 'lifecycle').write_text('')

    codes = workers.schedule(
        ['lifecycle', 'a'], 1, start=run.start, answering=lambda n: False, gate=gate, exclusive=set(), sleep=sleep
    )
    assert codes == {'lifecycle': 0, 'a': 0} and run.started == ['lifecycle', 'a']
    assert not os.path.exists(gate.lock) and os.listdir(gate.changing) == []


def test_nothing_starts_while_the_lock_is_held_and_each_start_ends_when_it_answers() -> None:
    workers = fresh('workers')
    run = FakeRun()

    class LockingGate(OpenGate):
        def try_begin(self, name: str) -> bool:
            began = super().try_begin(name)
            if name == 'lifecycle':
                self.locked = True  # it takes the lock as it starts (launch_lock.held)
            return began

    gate = LockingGate()

    def sleep(seconds: float) -> None:
        FakeRun.sleep(run, seconds)
        if run.ticks == 2:
            run.answering.add('lifecycle')
        if run.ticks == 3:
            gate.locked = False  # its window ends
        if run.ticks == 5:
            run.running['lifecycle'] = run.running['b'] = 0

    workers.schedule(
        ['lifecycle', 'b'],
        2,
        start=run.start,
        answering=lambda name: name in run.answering,
        gate=gate,
        exclusive=set(),
        sleep=sleep,
    )
    assert run.started == ['lifecycle', 'b']
    assert run.at_once[:3] == [{'lifecycle'}] * 3 and run.at_once[3] == {'lifecycle', 'b'}, 'b waited for the lock'
    assert gate.ended[0] == 'lifecycle', 'its start ended once it answered'
    assert set(gate.ended) == {'lifecycle', 'b'}, 'one ended by exiting counts too'


def test_lifecycle_starts_first_and_the_categories_follow_in_their_listed_order() -> None:
    workers = fresh('workers')
    categories = sys.modules['test_all_tools.categories']
    names = workers.names()
    assert names[0] == 'lifecycle'
    assert names[1:] == [categories.category_name(step) for step in categories.CATEGORIES]


# --- choosing


@pytest.mark.parametrize(
    'asked, platform, users, expected',
    [
        (None, 'darwin', False, 'AT_ONCE'),
        (2, 'darwin', False, 2),
        (1, 'darwin', False, 1),
        (None, 'win32', False, 0),  # one run: no Designer counts as an agent's on Windows yet (ROADMAP item 18)
        (None, 'darwin', True, 'refused'),  # the user's Designer: they are asked to close it
        (4, 'darwin', 'no listing', 'refused'),  # can't tell whose may be running: as with the user's
    ],
)
def test_a_pool_of_at_once_unless_asked_off_macos_or_with_the_users_designer(
    monkeypatch: pytest.MonkeyPatch, asked: Any, platform: str, users: Any, expected: Any
) -> None:
    workers = fresh('workers')
    common = sys.modules['test_all_tools.common']

    def users_running() -> bool:
        if users == 'no listing':
            raise common.NoListing("Designer's processes couldn't be listed")
        return bool(users)

    monkeypatch.setitem(vars(workers), 'users_designer_running', users_running)
    monkeypatch.setattr(sys, 'platform', platform)
    if expected == 'refused':
        with pytest.raises(workers.Refused, match='close'):
            workers.choose(asked)
    else:
        assert workers.choose(asked) == (workers.AT_ONCE if expected == 'AT_ONCE' else expected)


def test_at_once_alone_holds_the_default_number(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # ROADMAP item 68: the number was written in choose, in --help and in the docs; workers.AT_ONCE holds it alone, read
    # by choose and --help, and run_pool has no default of its own (REVIEW.md TST-282)
    index = fresh('__main__')
    monkeypatch.setitem(vars(index.workers), 'AT_ONCE', 7)
    monkeypatch.setitem(vars(index.workers), 'users_designer_running', lambda: False)
    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert index.workers.choose(None) == 7
    with pytest.raises(SystemExit) as ended:
        index.main(['--help'])
    assert ended.value.code == 0 and '(default 7)' in ' '.join(capsys.readouterr().out.split())
    assert inspect.signature(index.workers.run_pool).parameters['slots'].default is inspect.Parameter.empty


def test_the_index_runs_a_pool_one_run_off_macos_and_nothing_next_to_the_users_designer(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    index = fresh('__main__')
    ran: list[Any] = []

    def choose(asked: Any) -> int:
        if asked == 9:
            raise index.workers.Refused('Your Designer is open: close it, then run the self-test again.')
        return 0 if asked == 7 else asked or 4

    monkeypatch.setitem(vars(index.workers), 'choose', choose)

    def run_pool(slots: int, unit: bool = True) -> int:
        ran.append((slots, unit))
        return 0

    monkeypatch.setitem(vars(index.workers), 'run_pool', run_pool)
    monkeypatch.setitem(vars(index), 'one_run', lambda **kw: ran.append(('one', kw)))
    for argv, expected in (([], (4, True)), (['--no-unit'], (4, False)), (['--workers', '2'], (2, True))):
        ran.clear()
        with pytest.raises(SystemExit) as ended:
            index.main(argv)
        assert ended.value.code == 0 and ran == [expected]
    ran.clear()
    index.main(['--workers', '7'])  # as choose says off macOS
    assert ran == [('one', {})]
    ran.clear()
    with pytest.raises(SystemExit) as ended:
        index.main(['--workers', '9'])
    assert ended.value.code == 2 and ran == [] and 'close it' in capsys.readouterr().out


def test_a_run_hides_the_designer_it_started_before_any_category() -> None:
    import ast
    from pathlib import Path

    # nothing of it on the user's screen: every category's checks passed with Designer hidden (common.HIDE)
    path = Path(__file__).parents[1] / 'test_all_tools' / '__main__.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    run = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'run')
    source = ast.unparse(run)
    launch, hide, steps = (
        source.index(part) for part in ("'launch_designer'", 'hide_designer(', 'run_steps(ctx, steps)')
    )
    assert launch < hide < steps
    guard = next(n for n in ast.walk(run) if isinstance(n, ast.If) and 'hide_designer(' in ast.unparse(n))
    assert ast.unparse(guard.test) == 'not was_running', "never the user's"


# --- a worker: one category in a Designer of its own


def test_a_worker_runs_its_category_and_writes_its_results_with_its_quit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    index = fresh('__main__')
    categories = sys.modules['test_all_tools.categories']
    seen: dict[str, Any] = {}

    async def run(scratch: str, steps: Any = None, worker: Any = None, first: bool = False) -> list[str]:
        seen.update(steps=steps, worker=worker, first=first)
        index.check('t', 'a check', True)
        index.times['render'] = 1.5
        index.ENDED.update(quit='Designer quit after 2s.', quit_at=12.5)
        return ['t', 'u']  # u: a tool another worker covers

    monkeypatch.setitem(vars(index), 'run', run)
    monkeypatch.setitem(vars(index), 'agents_designers', dict)  # none recorded on its port: nothing to end
    monkeypatch.setitem(vars(index), 'crash_dumps', lambda ports=(): set())
    path = tmp_path / 'render.json'
    with pytest.raises(SystemExit) as ended:
        index.main(['--worker', 'render', '--results', str(path), '--first'])
    assert ended.value.code == 0
    render = categories.CATEGORIES[[categories.category_name(s) for s in categories.CATEGORIES].index('render')]
    assert seen == {'steps': [render], 'worker': 'render', 'first': True}
    assert json.loads(path.read_text()) == {
        'tools': ['t', 'u'],
        'results': {'t': [True]},
        'skipped': [],
        'times': {'render': 1.5},
        'quit': 'Designer quit after 2s.',
        'quit_at': 12.5,
        'forced_in_shutdown': [],  # lifecycle's normal closes forced during their shutdown (REVIEW.md TST-293)
    }


def test_a_worker_closes_its_designer_when_no_lock_holds_and_leaves_the_crash_dumps_to_the_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # one wait for crash dumps, at the end of the pool, not 10 s after each of 22 quits (workers.check_the_quits)
    index = fresh('__main__')
    monkeypatch.setattr(sys, 'platform', 'darwin')  # the pool's: on Windows there is no worker (REVIEW.md TST-269)
    order: list[str] = []
    lock = sys.modules['test_all_tools.launch_lock']

    class Changing:
        def __init__(self, name: str) -> None:
            order.append('wait for the lock: ' + name)

        def __enter__(self) -> None:
            pass

        def __exit__(self, *exc: object) -> None:
            order.append('done')

    monkeypatch.setitem(vars(lock), 'changing', Changing)
    monkeypatch.setitem(vars(index), 'new_crash_dumps', lambda *a, **k: pytest.fail('waited for crash dumps'))
    c = Designer('Designer quit after 2s.')
    c.calls = order  # one record, so the quit is seen inside the lock's window (REVIEW.md TST-239)
    asyncio.run(index.finish(SimpleNamespace(c=c), worker='render'))
    assert order == ['wait for the lock: render', 'quit_designer', 'done']
    assert index.ENDED['quit'] == 'Designer quit after 2s.' and 'quit_at' in index.ENDED
    assert 'quit_designer' not in index.results, 'the pool checks it, with the crash dumps'


# --- the pool's run


def test_the_pool_runs_every_category_once_and_prints_one_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    workers = pool(monkeypatch, tmp_path, lambda name, folder, port: part(name))
    assert workers.run_pool(3) == 0
    assert workers.slots == 3, 'run_pool passes its count on to schedule (REVIEW.md TST-287)'
    out = capsys.readouterr().out
    names = workers.names()
    assert sorted(n.removeprefix('--first ') for n in workers.started[::2]) == sorted(names), 'each one, once'
    assert all('check of %s' % name in out for name in names)
    # the run's start checks (get_guide, the Home screen) once, in the first category started, not lifecycle
    assert [n for n in workers.started if n.startswith('--first')] == ['--first ' + names[1]]
    # each worker's check, each category's quit (not lifecycle's: it ends its own), the unit suite's, the run's
    # count of quits forced during their shutdown, and (macOS) Designer's preferences as before the run
    checks = 2 * len(names) + (2 if sys.platform == 'darwin' else 1)
    assert 'checks passed: %d/%d' % (checks, checks) in out
    assert 'quit_designer' in out and not (tmp_path / 'root').exists()


def test_one_wait_for_crash_dumps_at_the_end_and_each_dump_fails_its_category_only(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    def write(name: str, folder: str, port: int) -> Mapping[str, object]:
        if name == 'render':  # its Designer crashed on its way out
            dumps = tmp_path / ('agent_%d' % port) / 'home' / 'Sentry-Crashpad' / 'completed'
            os.makedirs(dumps)
            (dumps / 'late.dmp').write_text('')
        return part(name)

    workers = pool(monkeypatch, tmp_path, write)
    assert workers.run_pool(4) == 1
    assert len(workers.looked) == 1, 'one wait, after the last quit'
    out = capsys.readouterr().out
    assert "FAIL  quit_designer          closes render's Designer, which left no crash dump" in out
    assert "PASS  quit_designer          closes facts's Designer, which left no crash dump" in out
    assert workers.common.results['quit_designer'].count(False) == 1
    kept = [p.name for p in tmp_path.glob('agent_*')]
    assert len(kept) == 1, 'only the folder holding a crash dump is kept, to read'


@pytest.mark.parametrize('name', ['lifecycle', 'undo'])
def test_a_dump_in_a_workers_folder_is_never_one_outside_the_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, name: str
) -> None:
    # REVIEW.md TST-236: lifecycle's dumps and those of a worker without results were left out of `placed`, so they also
    # failed "no new crash dump outside the run"; lifecycle's own watch reports its dumps, and a worker without results
    # gets a check naming them
    def write(worker: str, folder: str, port: int) -> Mapping[str, object] | None:
        if worker == name:
            dumps = tmp_path / ('agent_%d' % port) / 'home' / 'Sentry-Crashpad' / 'completed'
            os.makedirs(dumps)
            (dumps / 'crash.dmp').write_text('')
            return None if worker == 'undo' else part(worker)
        return part(worker)

    workers = pool(monkeypatch, tmp_path, write)
    workers.run_pool(4)
    out = capsys.readouterr().out
    assert 'no new crash dump outside the run' not in out
    if name == 'undo':
        assert "FAIL  quit_designer          undo's Designer left no crash dump" in out


def _forced(how: str) -> str:
    """quit_designer's words for a quit forced after 31 s: `how` is one of project_constants' QUIT_FORCED_*."""
    return 'Designer quit after 31s (%s; its log stopped at "[INFO][IPC] Remove PID").' % how


def test_a_quit_forced_before_its_close_took_or_none_fails_that_categorys_check(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # a quit forced during its own shutdown, every window closed, passes: not this check's to fail (ROADMAP item 69)
    quits = {
        'render': _forced(project_constants.QUIT_FORCED_NOT_CLOSED),
        'measure': _forced(project_constants.QUIT_FORCED_IN_SHUTDOWN + ': its close had taken'),
        'facts': None,
    }
    workers = pool(
        monkeypatch, tmp_path, lambda name, folder, port: part(name, quits.get(name, 'Designer quit after 2s.'))
    )
    assert workers.run_pool(4) == 1
    out = capsys.readouterr().out
    assert "FAIL  quit_designer          closes render's Designer, which left no crash dump" in out
    assert "FAIL  quit_designer          closes facts's Designer, which left no crash dump" in out
    assert "PASS  quit_designer          closes measure's Designer, which left no crash dump" in out


@pytest.mark.parametrize('count, passes', [(2, True), (3, False)])
def test_more_than_two_quits_forced_during_their_shutdown_fail_the_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, count: int, passes: bool
) -> None:
    # REVIEW.md TST-288: each passes its own check (DECISIONS.md, Bridge and quitting); more than the two seen at once
    # (ROADMAP item 69) is a pattern, such as a task every Designer leaves in Qt's thread pool
    forced = ['render', 'measure', 'params'][:count]
    workers = pool(
        monkeypatch,
        tmp_path,
        lambda name, folder, port: part(
            name, _forced(project_constants.QUIT_FORCED_IN_SHUTDOWN) if name in forced else 'Designer quit after 2s.'
        ),
    )
    assert workers.run_pool(4) == (0 if passes else 1)
    out = capsys.readouterr().out
    line = [l for l in out.splitlines() if 'quits forced during their shutdown' in l]
    assert len(line) == 1 and line[0].startswith('PASS' if passes else 'FAIL') and all(n in line[0] for n in forced)


def test_a_forced_quits_designer_folder_is_kept_to_read_its_log(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md SRV-106: the log naming where its shutdown stopped is in that folder
    ports: dict[str, int] = {}

    def write(name: str, folder: str, port: int) -> Mapping[str, object]:
        ports[name] = port
        return part(
            name, _forced(project_constants.QUIT_FORCED_IN_SHUTDOWN) if name == 'render' else 'Designer quit after 2s.'
        )

    workers = pool(monkeypatch, tmp_path, write)
    for port in range(5001, 5001 + len(workers.names())):
        os.makedirs(tmp_path / ('agent_%d' % port))
    workers.run_pool(4)
    kept = list(tmp_path.glob('agent_*'))
    assert len(kept) == 1 and 'kept, its quit was forced or sampled: %s' % kept[0] in capsys.readouterr().out
    assert kept[0].name == 'agent_%d' % ports['render'], "render's (REVIEW.md TST-294)"


def test_a_quit_ending_while_sampled_passes_and_keeps_its_folder(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md SRV-115: a shutdown hanging past its wait that ended while its threads were sampled: a normal close, its
    # sample a hang's evidence (ROADMAP item 70)
    ports: dict[str, int] = {}

    def write(name: str, folder: str, port: int) -> Mapping[str, object]:
        ports[name] = port
        sampled = 'Designer quit after 32s. %s /tmp/sd_mcp_1_%d/threads_42.sample.txt' % (
            project_constants.QUIT_SAMPLED,
            port,
        )
        return part(name, sampled if name == 'render' else 'Designer quit after 2s.')

    workers = pool(monkeypatch, tmp_path, write)
    for port in range(5001, 5001 + len(workers.names())):
        os.makedirs(tmp_path / ('agent_%d' % port))
    workers.run_pool(4)
    out = capsys.readouterr().out
    assert [k.name for k in tmp_path.glob('agent_*')] == ['agent_%d' % ports['render']]
    assert "PASS  quit_designer          closes render's Designer, which left no crash dump" in out
    # whole, where the check's detail is cut: the sample's path with it (REVIEW.md TST-314)
    assert (
        "render's quit whole: Designer quit after 32s. %s /tmp/sd_mcp_1_%d/threads_42.sample.txt"
        % (
            project_constants.QUIT_SAMPLED,
            ports['render'],
        )
        in out
    )


def test_lifecycles_quits_forced_during_their_shutdown_count_and_keep_its_folder(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-293: lifecycle's own normal closes pass on such a quit too, and item 69 was first seen in one
    ports: dict[str, int] = {}

    def write(name: str, folder: str, port: int) -> Mapping[str, object]:
        ports[name] = port
        if name == 'lifecycle':
            return {**part(name), 'forced_in_shutdown': ['closes the Designer it started, with a modal dialog open']}
        return part(
            name,
            _forced(project_constants.QUIT_FORCED_IN_SHUTDOWN)
            if name in ('render', 'measure')
            else 'Designer quit after 2s.',
        )

    workers = pool(monkeypatch, tmp_path, write)
    for port in range(5001, 5001 + len(workers.names())):
        os.makedirs(tmp_path / ('agent_%d' % port))
    assert workers.run_pool(4) == 1
    out = capsys.readouterr().out
    line = [l for l in out.splitlines() if 'quits forced during their shutdown' in l]
    assert len(line) == 1 and line[0].startswith('FAIL') and 'lifecycle: closes the Designer it started' in line[0]
    assert {p.name for p in tmp_path.glob('agent_*')} == {
        'agent_%d' % ports[n] for n in ('lifecycle', 'render', 'measure')
    }


def test_a_worker_without_results_fails_the_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    workers = pool(monkeypatch, tmp_path, lambda name, folder, port: None if name == 'undo' else part(name))
    assert workers.run_pool(4) == 1
    assert 'worker undo reports its results' in capsys.readouterr().out


@pytest.mark.parametrize('code', [0, 1])
def test_the_unit_suite_is_one_check_of_the_pool(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, code: int
) -> None:
    workers = pool(monkeypatch, tmp_path, lambda name, folder, port: part(name), unit=lambda f: unit_log(f, code))
    assert workers.run_pool(4) == code
    out = capsys.readouterr().out
    assert '===== unit tests (exit code %d) =====' % code in out
    assert ('PASS' if code == 0 else 'FAIL') + '  unit tests' in out
    assert '61.2 s  unit tests' in out or '61.3 s  unit tests' in out


def test_the_pool_without_the_unit_suite_starts_no_pytest(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    def unit(folder: str) -> Done:
        raise AssertionError('no unit suite asked for')

    workers = pool(monkeypatch, tmp_path, lambda name, folder, port: part(name), unit=unit)
    assert workers.run_pool(4, unit=False) == 0
    assert 'unit tests' not in capsys.readouterr().out


def test_each_worker_gets_the_lock_and_a_port_and_folders_of_its_own(tmp_path: Path) -> None:
    workers = fresh('workers')
    lock = sys.modules['test_all_tools.launch_lock']
    gate = lock.Gate(str(tmp_path))
    env = workers.worker_env(5001, str(tmp_path / 'render'), gate)
    assert env['SD_BRIDGE_PORT'] == '5001' and env[lock.LOCK_ENV] == gate.lock
    assert env[lock.CHANGING_ENV] == gate.changing
    assert env['TMPDIR'].startswith(os.path.realpath(tmp_path / 'render'))


# --- lifecycle holds the lock over its two windows


def test_lifecycle_holds_the_lock_from_its_launch_to_the_hand_over_and_with_its_record_aside(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle = fresh('lifecycle.checks')
    lock = sys.modules['test_all_tools.launch_lock']
    events: list[str] = []

    class Held:
        def __enter__(self) -> None:
            events.append('lock')

        def __exit__(self, *exc: object) -> None:
            events.append('unlock')

    monkeypatch.setitem(vars(lock), 'held', lambda **kw: Held())

    async def step(name: str, ok: Any = None) -> Any:
        events.append(name)
        return ok

    monkeypatch.setitem(vars(lifecycle), 'check_a_designer_of_its_own', lambda ctx: step('own Designer', True))
    for name in (
        'check_a_designer_sharing_the_temp_folder_hands_over',
        'check_the_3d_view_waits_for_a_graph',
        'check_launch_on_another_port',
        'check_launch_refuses_a_port_another_program_holds',
        'check_quitting_and_starting_again',
    ):
        monkeypatch.setitem(vars(lifecycle), name, lambda ctx, name=name: step(name))
    monkeypatch.setitem(
        vars(sys.modules['test_all_tools.crash_watch']), 'CrashWatch', lambda: SimpleNamespace(settle=lambda: None)
    )
    asyncio.run(lifecycle.run(SimpleNamespace(crash_watch=None)))
    assert events[:4] == ['lock', 'own Designer', 'check_a_designer_sharing_the_temp_folder_hands_over', 'unlock']
    source = Path(SELFTEST_DIR, 'lifecycle', 'checks.py').read_text(encoding='utf-8')
    aside = source[source.index('os.replace(record, kept)') - 200 : source.index('os.replace(kept, record)')]
    assert "launch_lock.held(own='lifecycle')" in aside, (
        'no Designer starts while its record is aside: it would be refused'
    )


# --- no unit test starts a real run


def test_under_pytest_a_real_process_start_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    # twice, while this was written, a test reaching the real run_pool started Designers, and the unit suite inside
    # that run this test again: the workers' one way to start a process refuses the real Popen under pytest
    workers = fresh('workers')
    monkeypatch.setattr(workers.subprocess, 'Popen', REAL_POPEN)
    with pytest.raises(RuntimeError, match='unit test'):
        workers.spawn([sys.executable, '-c', 'pass'])  # harmless, were it started
    source = Path(SELFTEST_DIR, 'workers.py').read_text(encoding='utf-8')
    assert source.count('subprocess.Popen(') == 1, 'every process the pool starts goes through spawn()'


def test_under_pytest_the_index_never_opens_a_real_session() -> None:
    index = fresh('__main__')
    with pytest.raises(RuntimeError, match='unit test'):
        asyncio.run(index.run('scratch'))


def test_a_worker_that_closed_its_designer_ends_nothing_else_and_removes_its_scratch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # seen live: with the other workers' Designers starting (none recorded yet: maybe this run's), it tried to end its
    # own again and left its scratch folder; a worker knows its Designer: the one recorded on its port
    index = fresh('__main__')
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    monkeypatch.setattr(index.tempfile, 'mkdtemp', lambda prefix: str(scratch))

    async def run(scratch: str, steps: Any = None, worker: Any = None, first: bool = False) -> list[str]:
        return []

    monkeypatch.setitem(vars(index), 'run', run)
    monkeypatch.setitem(vars(index), 'designer_here', lambda: True)  # other workers' Designers
    monkeypatch.setitem(vars(index), 'agents_designers', lambda: {index.common.PORT + 1: 123})
    monkeypatch.setitem(vars(index), 'end_own_designer', lambda: pytest.fail('ended a Designer'))
    monkeypatch.setitem(vars(index), 'crash_dumps', lambda ports=(): set())
    with pytest.raises(SystemExit):
        index.one_run(worker='undo', results_file=str(tmp_path / 'undo.json'))
    assert not scratch.exists()


def test_undo_and_redo_raise_and_activate_their_window_first() -> None:
    # beside another Designer (a pool's), Undo of an output's fields did nothing, 8 times in 8, until the window was
    # raised and activated first; then 8 in 8 passed (REVIEW.md TST-234)
    common = fresh('common')
    snippet = common.UNDO_REDO
    assert snippet.index('mw.activateWindow()') < snippet.index('QTimer.singleShot(0, acts[0].trigger)')
    assert snippet.index('mw.raise_()') < snippet.index('mw.activateWindow()')


def test_a_second_holder_waits_for_the_first_to_release_the_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # two holders: one releasing mustn't end the other's window
    lock = fresh('launch_lock')
    gate = lock.Gate(str(tmp_path))
    monkeypatch.setattr(os, 'environ', {**os.environ, **gate.env()})
    Path(gate.lock).write_text('')  # lifecycle holds it
    waits: list[str] = []

    def sleep(seconds: float) -> None:
        waits.append('waited')
        os.remove(gate.lock)  # lifecycle's window ends

    with lock.held(own='undo', sleep=sleep):
        assert waits == ['waited'] and os.path.exists(gate.lock)
    assert not os.path.exists(gate.lock)


def test_a_solo_category_runs_with_no_other_designer_of_the_run() -> None:
    # undo: beside the others (starting, closing their Home screen, lifecycle's own launches) its Undo failed in 3 pool
    # runs of 4, and 8 times in 8 beside one idle Designer (categories.SOLO)
    workers = fresh('workers')
    run = FakeRun()
    run.plan = {2: ['a'], 4: ['b'], 5: ['c'], 8: ['undo']}
    _schedule(workers, run, ['a', 'undo', 'b', 'c'], 3, solo={'undo'})
    assert run.started == ['a', 'b', 'c', 'undo'], 'last, once the others have ended'
    for names in run.at_once:
        assert 'undo' not in names or names == {'undo'}, names
    categories = sys.modules['test_all_tools.categories']
    assert frozenset({'undo'}) == categories.SOLO


# --- REVIEW.md TST-238: the pool's parts no test reached


@pytest.mark.parametrize('listing', ['one still running', 'the listing fails'])
def test_the_folders_are_kept_while_a_designer_of_the_run_may_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, listing: str
) -> None:
    # never a folder deleted under a running Designer: deleting one crashed Designer twice (REVIEW.md PLG-9)
    workers = pool(monkeypatch, tmp_path, lambda name, folder, port: part(name))
    for port in range(5001, 5001 + len(workers.names())):
        (tmp_path / ('agent_%d' % port)).mkdir()

    def agents() -> dict[int, int]:
        if listing == 'the listing fails':
            raise RuntimeError('pgrep exit code 2')
        return {5002: 123}

    monkeypatch.setitem(vars(workers), 'agents_designers', agents)
    workers.run_pool(4)
    out = capsys.readouterr().out
    kept = sorted(p.name for p in tmp_path.glob('agent_*'))
    assert (tmp_path / 'root').is_dir() and 'folders kept, a Designer of the run may still be open' in out
    if sys.platform == 'darwin':  # where the plist is
        preferences = next(line for line in out.splitlines() if PREFERENCES in line)
        assert preferences.startswith('FAIL'), "nothing could put them back, or that can't be told: %s" % preferences
    if listing == 'one still running':
        assert kept == ['agent_5002'], 'only the folder of the one still running'
    else:
        assert len(kept) == len(workers.names()) and "the workers' Designers can't be listed" in out


def test_a_new_dump_outside_the_workers_folders_fails_a_check_of_its_own(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    workers = pool(monkeypatch, tmp_path, lambda name, folder, port: part(name))
    calls: list[int] = []

    def dumps(ports: Any = (), run_port: bool = True) -> set[str]:
        calls.append(1)
        return set() if len(calls) == 1 else {str(tmp_path / 'shared' / 'completed' / 'x.dmp')}  # after the start

    monkeypatch.setitem(vars(workers), 'crash_dumps', dumps)
    assert workers.run_pool(4) == 1
    assert 'FAIL  self-test              no new crash dump outside the run' in capsys.readouterr().out


def test_a_report_uploaded_during_the_run_is_no_new_dump(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-351: the user's Designer's report, waiting for its upload as the run started, moved to completed/
    workers = pool(monkeypatch, tmp_path, lambda name, folder, port: part(name))
    calls: list[int] = []

    def dumps(ports: Collection[int] = (), run_port: bool = True) -> set[str]:
        calls.append(1)
        return {str(tmp_path / 'user' / 'Sentry-Crashpad' / ('pending' if len(calls) == 1 else 'completed') / 'x.dmp')}

    monkeypatch.setitem(vars(workers), 'crash_dumps', dumps)
    assert workers.run_pool(4) == 0
    assert 'no new crash dump outside the run' not in capsys.readouterr().out


@pytest.mark.parametrize('waiting', [False, True], ids=['completed', 'pending'])
def test_a_workers_folder_holding_a_crash_dump_is_told(tmp_path: Path, waiting: bool) -> None:
    # kept to be read; a report waiting for its upload is one too (REVIEW.md TST-351)
    workers = fresh('workers')
    crashpad = tmp_path.joinpath(
        'agent', 'home', 'Library', 'Application Support', 'Adobe', 'Adobe Substance 3D Designer'
    )
    folder = crashpad / 'Sentry-Crashpad' / ('pending' if waiting else 'completed')
    folder.mkdir(parents=True)
    assert not workers._holds_a_crash_dump(str(tmp_path / 'agent'))
    (folder / 'x.dmp').write_text('')
    assert workers._holds_a_crash_dump(str(tmp_path / 'agent'))


def test_a_port_answers_once_something_listens_on_it() -> None:
    import socket

    workers = fresh('workers')
    with socket.socket() as listening:
        listening.bind(('127.0.0.1', 0))
        listening.listen(1)
        port = listening.getsockname()[1]
        assert workers.answering(port)
    assert not workers.answering(port)


@pytest.mark.parametrize('count', ['0', '-1'])
def test_workers_below_one_are_refused_before_anything_starts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], count: str
) -> None:
    index = fresh('__main__')
    monkeypatch.setitem(vars(index.workers), 'choose', lambda asked: pytest.fail('went on to choose'))
    with pytest.raises(SystemExit) as ended:
        index.main(['--workers', count])
    assert ended.value.code == 2 and '--workers takes 1 or more' in capsys.readouterr().err


# --- --only: chosen categories through the pool (__main__.py)


def test_only_runs_the_named_categories_through_the_pool_without_the_unit_suite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = fresh('__main__')
    asked: list[tuple[int, bool, Any]] = []
    monkeypatch.setitem(vars(index.workers), 'choose', lambda workers: workers or 4)

    def run_pool(slots: int, unit: bool = True, only: Any = None) -> int:
        asked.append((slots, unit, only))
        return 0

    monkeypatch.setitem(vars(index.workers), 'run_pool', run_pool)
    with pytest.raises(SystemExit) as ended:
        index.main(['--only', 'layout', 'bridge'])
    assert ended.value.code == 0
    assert asked == [(4, False, ['layout', 'bridge'])], 'the unit suite left out by default (the user, 2026-11-10)'


def test_only_refuses_a_name_that_is_no_category_and_lists_them(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    index = fresh('__main__')
    monkeypatch.setitem(vars(index.workers), 'choose', lambda workers: pytest.fail('went on to choose'))
    with pytest.raises(SystemExit) as ended:
        index.main(['--only', 'layout', 'no_such'])
    err = capsys.readouterr().err
    assert ended.value.code == 2 and 'no_such' in err and 'layout' in err and 'lifecycle' in err


def test_only_is_refused_where_there_is_no_pool(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # off macOS there is one run of every category (ROADMAP item 65): none of only the named ones
    index = fresh('__main__')
    monkeypatch.setitem(vars(index.workers), 'choose', lambda workers: 0)
    monkeypatch.setitem(vars(index), 'one_run', lambda *a, **k: pytest.fail('ran every category'))
    with pytest.raises(SystemExit) as ended:
        index.main(['--only', 'layout'])
    assert ended.value.code == 2 and '--only' in capsys.readouterr().out


def test_a_pool_of_chosen_categories_starts_only_those_in_the_pools_order(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    workers = pool(monkeypatch, tmp_path, lambda name, folder, port: part(name))
    assert workers.run_pool(4, unit=False, only=['layout', 'facts']) == 0
    assert workers.started == ['facts', '--first facts', 'layout', 'layout'], (
        'in their listed order, the start checks in the first'
    )
    assert '2 categories' in capsys.readouterr().out


def test_a_pool_of_chosen_categories_judges_the_coverage_of_their_tools_only(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # every worker lists all the server's tools; the others' categories didn't run, so their tools aren't missing
    def write(name: str, folder: str, port: int) -> Mapping[str, object]:
        return {**part(name), 'tools': ['t', 'u']}

    workers = pool(monkeypatch, tmp_path, write)
    assert workers.run_pool(4, unit=False, only=['layout']) == 0
    out = capsys.readouterr().out
    assert 'NOT covered' not in out and 'coverage of every tool: a full run' in out
    full = pool(monkeypatch, tmp_path / 'full', write)
    assert full.run_pool(4, unit=False) == 1, "a full run still fails on a tool no category exercised ('u')"


def test_the_start_checks_go_to_a_category_that_starts_before_the_one_kept_for_last(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md TST-265: undo comes before script_runner in the order, and SOLO starts it after every other
    workers = pool(monkeypatch, tmp_path, lambda name, folder, port: part(name))
    assert workers.run_pool(4, unit=False, only=['undo', 'script_runner']) == 0
    assert [n for n in workers.started if n.startswith('--first')] == ['--first script_runner']
    alone = pool(monkeypatch, tmp_path / 'alone', lambda name, folder, port: part(name))
    assert alone.run_pool(4, unit=False, only=['undo']) == 0
    assert [n for n in alone.started if n.startswith('--first')] == ['--first undo'], 'with nothing else to take them'


def test_the_wait_for_crash_dumps_counts_from_the_last_quit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-268: a dump comes seconds after its Designer quits, so the wait is from the last one to quit
    def write(name: str, folder: str, port: int) -> Mapping[str, object]:
        return {**part(name), 'quit_at': time.time() - (100 if name == 'facts' else 0)}

    workers = pool(monkeypatch, tmp_path, write)
    started = time.time()
    assert workers.run_pool(4, unit=False, only=['layout', 'facts']) == 0
    [(_, until, _)] = workers.looked
    assert started + workers.CRASH_WAIT_S - 1 < until < time.time() + workers.CRASH_WAIT_S + 1


def test_the_wait_for_crash_dumps_compares_with_the_dumps_there_before_the_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-437: the fake wait dropped `before`, so nothing checked what it compares with
    old = tmp_path / 'agent_5001' / 'home' / 'Sentry-Crashpad' / 'completed' / 'old.dmp'
    os.makedirs(old.parent)
    old.write_text('')

    def write(name: str, folder: str, port: int) -> Mapping[str, object]:
        return {**part(name), 'quit_at': time.time()}

    workers = pool(monkeypatch, tmp_path, write)
    workers.run_pool(4, unit=False, only=['layout', 'facts'])
    [(_, _, before)] = workers.looked
    assert before == {str(old)}


def test_a_pool_of_lifecycle_alone_has_no_first_category(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    workers = pool(monkeypatch, tmp_path, lambda name, folder, port: part(name))
    assert workers.run_pool(4, unit=False, only=['lifecycle']) == 0
    assert workers.started == ['lifecycle', 'lifecycle'], 'no --first: the start checks need a category of their own'


# --- Designer's preferences plist, as before the run once its Designers ended (ROADMAP item 67)

PREFERENCES = "Designer's preferences are as before the run, once its Designers ended"
_MACOS = pytest.mark.skipif(sys.platform != 'darwin', reason='the plist is macOS only')


def _the_line(out: str) -> str:
    return next(line for line in out.splitlines() if PREFERENCES in line)


@_MACOS
@pytest.mark.parametrize('put_back', [True, False], ids=['put back', 'left changed'])
def test_the_pool_checks_designers_preferences_are_as_before_it(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    defaults: FakeDefaults,
    put_back: bool,
) -> None:
    defaults.domain = {
        'session.mainWindow.state': b'the user',
        'session.instancePID': 10,
        'session.lastSession.files': [],
    }

    def write(name: str, folder: str, port: int) -> dict[str, object]:
        if not put_back:  # as agents' Designers may leave it, nothing having put it back
            defaults.domain['session.instancePID'] = port
            defaults.domain['session.graph.thumbnail_mode.%s' % name] = 1
            defaults.domain.pop('session.lastSession.files', None)  # a key removed (REVIEW.md TST-358)
        return part(name)

    workers = pool(monkeypatch, tmp_path, write)
    assert workers.run_pool(4) == (0 if put_back else 1)
    out = capsys.readouterr().out
    if put_back:
        assert 'PASS  self-test              %s | 0 values changed, 0 keys added' % PREFERENCES in out, out
    else:
        n = len(workers.names())
        line = _the_line(out)
        # the counts first: a check's detail is cut at 150 characters (REVIEW.md TST-361)
        assert (
            line.startswith('FAIL') and '| 2 values changed, %d keys added (changed: session.instancePID, ' % n in line
        )
        # and every key whole, on lines of their own
        assert '      values changed: session.instancePID, session.lastSession.files' in out, out
        added = ', '.join(sorted('session.graph.thumbnail_mode.%s' % name for name in workers.names()))
        assert '      keys added: %s' % added in out, out


@_MACOS
@pytest.mark.parametrize('unread', ['the file', 'the copy kept'])
def test_the_preferences_check_fails_when_the_run_couldnt_read_them_as_it_started(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    defaults: FakeDefaults,
    unread: str,
) -> None:
    # REVIEW.md TST-372: with nothing to compare the file with, the check can't pass
    defaults.domain = {'session.mainWindow.state': b'the user'}
    outside: list[int] = []
    if unread == 'the file':
        defaults.fail['export'] = 'defaults export: exit code 1'
    else:  # kept for a Designer outside the run (REVIEW.md TST-357), and unopenable as the run starts
        with designer_preferences.saved(lambda: False, ended=False):
            pass
        outside.append(78)

        def opening(file: str, mode: str = 'r', encoding: str | None = None) -> object:
            if file == designer_preferences.saved_file():
                raise PermissionError(13, 'Permission denied')
            return open(file, mode, encoding=encoding)

        monkeypatch.setitem(vars(designer_preferences), 'open', opening)  # the module's own name, before the builtin

    def write(name: str, folder: str, port: int) -> dict[str, object]:
        defaults.fail.clear()  # readable again once the run started
        monkeypatch.delitem(vars(designer_preferences), 'open', raising=False)
        outside.clear()
        return part(name)

    workers = pool(monkeypatch, tmp_path, write)
    monkeypatch.setitem(vars(workers), 'designer_pids', lambda: list(outside))
    assert workers.run_pool(4) == 1
    line = _the_line(capsys.readouterr().out)
    why = 'defaults export: exit code 1' if unread == 'the file' else "the copy kept couldn't be read ([Errno 13]"
    assert line.startswith('FAIL') and "| they couldn't be read as the run started: %s" % why in line, line


@_MACOS
def test_the_preferences_check_skips_once_the_users_designer_ran_during_the_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, defaults: FakeDefaults
) -> None:
    # the file may hold the user's own changes then, which quit_designer leaves (designer_preferences.py)
    def write(name: str, folder: str, port: int) -> dict[str, object]:
        defaults.domain['changed by %s' % name] = 1
        _users_log(defaults, time.time() + 5)
        return part(name)

    workers = pool(monkeypatch, tmp_path, write)
    assert workers.run_pool(4) == 0
    out = capsys.readouterr().out
    assert "SKIP  self-test              %s | the user's Designer ran during the run" % PREFERENCES in out, out


@_MACOS
def test_the_preferences_check_still_fails_with_a_users_log_from_before_the_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, defaults: FakeDefaults
) -> None:
    # REVIEW.md TST-358: the user's machine always has their log; only one written during the run skips the check
    _users_log(defaults, time.time() - 3600)

    def write(name: str, folder: str, port: int) -> dict[str, object]:
        defaults.domain['changed by %s' % name] = 1
        return part(name)

    workers = pool(monkeypatch, tmp_path, write)
    assert workers.run_pool(4) == 1
    assert _the_line(capsys.readouterr().out).startswith('FAIL')


def _users_log(defaults: FakeDefaults, at: float) -> None:
    log = defaults.users_data / '16.0' / 'log.txt'
    log.parent.mkdir(exist_ok=True)
    log.write_text('the user opened theirs\n')
    os.utime(log, (at, at))


@_MACOS
@pytest.mark.parametrize('whose', ['the run', 'another'])
def test_the_preferences_check_with_a_designer_still_running(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, whose: str
) -> None:
    # one of the run's: nothing could put the file back, a failure; another's (an alone.run Designer kept open): the
    # put-back waits for its end, so the check can't tell
    workers = pool(monkeypatch, tmp_path, lambda name, folder, port: part(name))
    monkeypatch.setitem(vars(workers), 'agents_designers', lambda: {5001: 77} if whose == 'the run' else {9500: 78})
    monkeypatch.setitem(vars(workers), 'designer_pids', lambda: [77] if whose == 'the run' else [78])
    workers.run_pool(4)
    line = _the_line(capsys.readouterr().out)
    if whose == 'the run':
        assert line.startswith('FAIL') and "the run's Designers still run, on ports [5001]" in line, line
    else:
        assert line.startswith('SKIP') and 'a Designer outside the run runs (78)' in line, line


@_MACOS
def test_a_copy_left_from_before_the_run_is_put_back_before_the_pool_reads_the_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, defaults: FakeDefaults
) -> None:
    # agents' Designers that ended outside the tools left a copy and their change: put back as the run starts, as its
    # first launch would, and said
    defaults.domain = {'session.mainWindow.state': b'the user'}
    with designer_preferences.saved(lambda: False, ended=False):
        pass
    defaults.domain['session.mainWindow.state'] = b'a crashed agent'

    def write(name: str, folder: str, port: int) -> dict[str, object]:
        designer_preferences.put_back(lambda: False, ended=True)  # as each worker's quit_designer does, once none runs
        return part(name)

    workers = pool(monkeypatch, tmp_path, write)
    assert workers.run_pool(4) == 0
    out = capsys.readouterr().out
    assert "Designer's preferences put back from their copy: 1 value put back." in out
    assert defaults.domain == {'session.mainWindow.state': b'the user'}


@_MACOS
def test_a_copy_too_old_to_put_back_is_dropped_before_the_pool_reads_the_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, defaults: FakeDefaults
) -> None:
    # REVIEW.md TST-367, TST-368: the run's first launch would drop it (past LEFTOVER_HOURS, the user may have worked
    # since) and save the file as it is, which the run's last quit puts back: so the file is what the run should leave
    defaults.domain = {'session.mainWindow.state': b'the user'}
    with designer_preferences.saved(lambda: False, ended=False):
        pass
    old = time.time() - (designer_preferences.LEFTOVER_HOURS + 1) * 3600
    os.utime(designer_preferences.saved_file(), (old, old))
    defaults.domain['session.mainWindow.state'] = b'a crashed agent, or the user since'

    def write(name: str, folder: str, port: int) -> dict[str, object]:
        with designer_preferences.saved(lambda: False, ended=False):  # as each worker's launch_designer does
            pass
        designer_preferences.put_back(lambda: False, ended=True)  # and its quit_designer, once none runs
        return part(name)

    workers = pool(monkeypatch, tmp_path, write)
    assert workers.run_pool(4) == 0
    assert 'PASS' in _the_line(capsys.readouterr().out)
    assert defaults.domain == {'session.mainWindow.state': b'a crashed agent, or the user since'}, (
        'dropped, not put back'
    )


@_MACOS
def test_the_check_compares_with_the_file_once_the_users_designer_ran_since_the_copy(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, defaults: FakeDefaults
) -> None:
    # REVIEW.md TST-367: an alone.run Designer open (its copy C0 kept), and the user opened and closed theirs since: the
    # run's first launch saves the file again, which the run's last quit puts back, not C0
    defaults.domain = {'session.mainWindow.state': b'the user'}
    with designer_preferences.saved(lambda: False, ended=False):
        pass
    made = time.time() - 60
    os.utime(designer_preferences.saved_file(), (made, made))
    defaults.domain['session.instancePID'] = 9500  # the outside Designer's
    _users_log(defaults, made + 30)
    defaults.domain['session.mainWindow.state'] = b"the user's new layout"
    outside = [78]
    launches: list[str] = []

    def write(name: str, folder: str, port: int) -> dict[str, object]:
        launches.append(name)
        with designer_preferences.saved(lambda: True, ended=False):  # each worker's launch: another Designer runs
            pass
        outside.clear()  # the outside one quit meanwhile; then, as each worker's quit_designer does once none runs
        designer_preferences.put_back(lambda: False, ended=True)
        return part(name)

    workers = pool(monkeypatch, tmp_path, write)
    monkeypatch.setitem(vars(workers), 'designer_pids', lambda: list(outside))
    assert workers.run_pool(4) == 0
    assert launches and 'PASS' in _the_line(capsys.readouterr().out)
    assert defaults.domain == {'session.mainWindow.state': b"the user's new layout", 'session.instancePID': 9500}


@_MACOS
def test_the_check_compares_with_the_copy_kept_for_a_designer_outside_the_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, defaults: FakeDefaults
) -> None:
    # REVIEW.md TST-357: an alone.run Designer open as the run starts (its copy C0 kept, the file F1 its own), quit
    # during the run: the run's last quit puts C0 back, which is the file as before any agent's Designer
    defaults.domain = {'session.mainWindow.state': b'the user'}
    with designer_preferences.saved(lambda: False, ended=False):
        pass
    defaults.domain['session.instancePID'] = 9500  # the outside Designer's
    outside = [78]

    def write(name: str, folder: str, port: int) -> dict[str, object]:
        outside.clear()  # quit meanwhile; then, as each worker's quit_designer does once none runs
        designer_preferences.put_back(lambda: False, ended=True)
        return part(name)

    workers = pool(monkeypatch, tmp_path, write)
    monkeypatch.setitem(vars(workers), 'designer_pids', lambda: list(outside))
    assert workers.run_pool(4) == 0
    assert 'PASS' in _the_line(capsys.readouterr().out)
    assert defaults.domain == {'session.mainWindow.state': b'the user'}


def test_the_wait_for_crash_dumps_lasts_while_one_may_come_looked_at_every_poll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # REVIEW.md SRV-151: it slept 10 s after the last quit whatever happened; it waits while a Designer's crash handler
    # runs with no dump yet (common.dumps_may_come), until `until` at most
    workers = fresh('workers')
    looks = iter([True, True, True, False])
    asked: list[tuple[list[int], set[str], bool]] = []

    def may_come(ports: Sequence[int], before: set[str], run_port: bool = True) -> bool:
        asked.append((list(ports), before, run_port))
        return next(looks)

    slept: list[float] = []
    monkeypatch.setitem(vars(workers), 'dumps_may_come', may_come)
    monkeypatch.setitem(vars(workers), 'sleep', slept.append)
    workers.wait_for_dumps([5001, 5002], {'a.dmp'}, time.time() + 60)
    assert slept == [workers.POLL_S] * 3
    assert asked[0] == ([5001, 5002], {'a.dmp'}, False), "the parent's: no Designer on the default port"
    slept.clear()
    monkeypatch.setitem(vars(workers), 'dumps_may_come', lambda ports, before, run_port=True: True)
    workers.wait_for_dumps([5001], set(), time.time() - 1)  # past its limit: no wait
    assert slept == []
