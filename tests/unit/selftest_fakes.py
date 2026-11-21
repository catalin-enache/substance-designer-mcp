"""Fakes that the self-test's unit tests share. None of them needs Designer. The module holds:

- fresh(name): a module of the self-test, imported afresh with the others.
- tool_result(text, error): a stand-in for a CallToolResult.
- code_of(args): the code in a tool call's arguments.
- FakeCall: the type of a fake of the self-test's tool call.
- Designer: a fake Designer that gives every call the same answer.
- FakeRun, OpenGate and Done: the scheduler's processes and gate.
- pool() and its helpers: the pool with every process faked.

The last three serve test_selftest_pool.py."""

import importlib
import json
import os
import sys
import time
from collections.abc import Awaitable, Callable, Collection, Iterable
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, Protocol, TypedDict, Unpack, cast, runtime_checkable

import pytest

from conftest import SELFTEST_DIR
from project_constants import ToolArgs

if TYPE_CHECKING:  # for the checker only: fresh() imports the self-test's modules afresh, test by test
    from test_all_tools.workers import Gating, Process, WorkerResults, _Start


# A fake of the self-test's tool call, `c(name, args)`, answering with what stands for a CallToolResult
FakeCall = Callable[[str, ToolArgs | None], Awaitable[SimpleNamespace]]


def fresh(name: str) -> ModuleType:  # a module imported by name: PyCharm can't see its names
    """A module of the self-test imported afresh with all of them, so each test starts with an empty check record."""
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    for loaded in [m for m in sys.modules if m == 'test_all_tools' or m.startswith('test_all_tools.')]:
        del sys.modules[loaded]
    return importlib.import_module('test_all_tools.' + name)


def tool_result(text: str, error: bool = False) -> SimpleNamespace:
    """What stands for a CallToolResult: one text, and whether the tool failed."""
    return SimpleNamespace(content=[SimpleNamespace(type='text', text=text)], is_error=error)


def code_of(args: ToolArgs | None) -> str:
    """The code passed in a tool call's arguments (execute_designer_code's `code`), or '' without one."""
    return cast(str, (args or {}).get('code', ''))


class FakeRun:
    """Processes that end when told; a log of what started and when."""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.running: dict[str, int | None] = {}
        self.answering: set[str] = set()
        self.ticks = 0
        self.plan: dict[int, list[str]] = {}  # tick -> names ending then
        self.at_once: list[set[str]] = []

    def start(self, name: str) -> 'Process':
        self.started.append(name)
        self.running[name] = None
        run = self

        class Process:
            def poll(self) -> int | None:
                return run.running[name]

        return Process()

    def sleep(self, seconds: float) -> None:
        self.ticks += 1
        self.at_once.append({n for n, code in self.running.items() if code is None})
        for name in self.plan.get(self.ticks, []):
            self.running[name] = 0
        if self.ticks > 500:
            raise AssertionError('never ends')


class OpenGate:
    def __init__(self) -> None:
        self.begun: list[str] = []
        self.ended: list[str] = []
        self.ends: list[str] = []  # the workers that ended (Gate.worker_ended)
        self.locked = False

    def try_begin(self, name: str) -> bool:
        if self.locked:
            return False
        self.begun.append(name)
        return True

    def end(self, name: str) -> None:
        self.ended.append(name)

    def worker_ended(self, name: str) -> None:
        self.ends.append(name)


class Designer:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls: list[str] = []

    async def __call__(self, name: str, args: ToolArgs | None = None) -> SimpleNamespace:  # a CallToolResult
        self.calls.append(name)
        return tool_result(self.answer)


class Done:
    def __init__(self, code: int = 0) -> None:
        self.code = code

    def wait(self) -> int:
        return self.code


@runtime_checkable
class _Gate(Protocol):
    """The gate run_pool passes the scheduler: launch_lock.Gate, imported afresh with the pool, so no class to name."""

    def env(self) -> dict[str, str]: ...


class _ScheduleOptions(TypedDict, total=False):
    """workers.schedule's keyword arguments after `start`, which run_pool passes."""

    answering: Callable[[str], bool]
    gate: 'Gating'
    exclusive: Collection[str]
    solo: Collection[str]
    sleep: Callable[[float], None]
    on_end: Callable[[str], None]


def pool(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    write: Callable[[str, str, int], 'WorkerResults | None'],
    unit: Callable[[str], Done] | None = None,
) -> ModuleType:
    """workers with every process faked: each worker writes what write(name, folder, port) returns as its results."""
    workers = fresh('workers')
    monkeypatch.setitem(vars(workers), 'ports', lambda count: list(range(5001, 5001 + count)))
    monkeypatch.setitem(vars(workers), 'agents_designers', dict)
    monkeypatch.setitem(vars(workers), 'designer_pids', list)  # none left running at the end
    monkeypatch.setitem(vars(workers), 'agent_folder', lambda port: str(tmp_path / ('agent_%d' % port)))

    def crash_dumps(ports: Collection[int] = (), run_port: bool = True) -> set[str]:
        assert not run_port, "the pool's parent has no Designer on the default port (REVIEW.md TST-280)"
        return dumps_in(tmp_path, ports)

    monkeypatch.setitem(vars(workers), 'crash_dumps', crash_dumps)
    monkeypatch.setattr(workers.tempfile, 'mkdtemp', lambda prefix: str(tmp_path / 'root'))
    os.makedirs(tmp_path / 'root')
    waits: list[float] = []
    monkeypatch.setitem(vars(workers), 'sleep', waits.append)
    vars(workers)['waits'] = waits
    looked: list[tuple[list[int], float, set[str]]] = []  # each wait for crash dumps: its ports, until when, before

    def wait_for_dumps(ports: Collection[int], before: set[str], until: float) -> None:
        looked.append((sorted(ports), until, set(before)))

    monkeypatch.setitem(vars(workers), 'wait_for_dumps', wait_for_dumps)
    vars(workers)['looked'] = looked
    started: list[str] = []
    envs: dict[str, dict[str, str]] = {}

    gates: list[_Gate] = []

    def schedule(
        names: list[str], slots: int, start: Callable[[str], Done], **kw: 'Unpack[_ScheduleOptions]'
    ) -> dict[str, int]:
        # what run_pool must pass on (REVIEW.md TST-268): these have defaults or do nothing when left out
        assert kw['exclusive'] == workers.CLIPBOARD and kw['solo'] == workers.SOLO
        vars(workers)['slots'] = slots  # its count, read by the test that gives one (REVIEW.md TST-287)
        gate = kw['gate']
        assert isinstance(gate, _Gate), gate
        gates.append(gate)
        codes = {}
        for name in names:
            started.append(name)
            proc = start(name)
            codes[name] = proc.wait()
            kw['on_end'](name)
        return codes

    monkeypatch.setitem(vars(workers), 'schedule', schedule)

    def popen(command: list[str], **kwargs: 'Unpack[_Start]') -> Done:
        env = kwargs['env']
        name = command[command.index('--worker') + 1]
        folder = os.path.dirname(command[command.index('--results') + 1])
        assert gates and {key: env.get(key) for key in gates[-1].env()} == gates[-1].env(), (
            'the lock: in its environment'
        )
        for own in ('SD_SNAPSHOT_DIR', 'TMPDIR'):  # each worker's, in its folder (REVIEW.md TST-274)
            assert os.path.realpath(env[own]).startswith(os.path.realpath(folder) + os.sep), (own, env[own])
        started.append('--first ' + name if '--first' in command else name)
        envs[name] = env
        Path(folder, name + '.log').write_text('PASS  t  check of %s\n' % name)
        part = write(name, folder, int(env['SD_BRIDGE_PORT']))
        if part is None:
            return Done(2)
        Path(command[command.index('--results') + 1]).write_text(json.dumps(part))
        return Done(0 if all(all(oks) for oks in part['results'].values()) else 1)  # as a worker's one_run exits

    monkeypatch.setattr(workers.subprocess, 'Popen', popen)
    monkeypatch.setitem(vars(workers), 'start_unit', unit or (lambda folder: unit_log(folder, 0)))
    vars(workers)['started'] = started
    vars(workers)['envs'] = envs  # each worker's environment, as it started: before write() runs
    return workers


def dumps_in(root: Path, ports: Iterable[int]) -> set[str]:
    """common.crash_dumps over the fake agent folders: the completed reports in agent_<port>/home."""
    return {str(p) for port in ports for p in (root / ('agent_%d' % port)).glob('home/**/completed/*')}


def unit_log(folder: str, code: int) -> Done:
    Path(folder, 'unit.log').write_text('%s in 61.25s\n' % ('1 failed, 9 passed' if code else '10 passed'))
    return Done(code)


def part(name: str, quit: str | None = 'Designer quit after 2s.') -> 'WorkerResults':
    return {
        'tools': ['t'],
        'results': {'t': [True]},
        'skipped': [],
        'times': {name: 1.0},
        'quit': None if name == 'lifecycle' else quit,
        'quit_at': None if name == 'lifecycle' else time.time(),  # just now: the pool waits from it
        'forced_in_shutdown': [],
    }
