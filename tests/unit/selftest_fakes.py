"""Fakes the self-test's pool tests share (test_selftest_pool.py, test_selftest_workers.py): the self-test's modules
imported afresh, a Designer answering every call alike, the scheduler's processes and gate, and the pool with every
process faked (pool). No Designer."""

import importlib
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from conftest import SELFTEST_DIR


def fresh(name: str) -> Any:  # a module imported by name: PyCharm can't see its names
    """A module of the self-test imported afresh with all of them, so each test starts with an empty check record."""
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    for loaded in [m for m in sys.modules if m == 'test_all_tools' or m.startswith('test_all_tools.')]:
        del sys.modules[loaded]
    return importlib.import_module('test_all_tools.' + name)


class FakeRun:
    """Processes that end when told; a log of what started and when."""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.running: dict[str, int | None] = {}
        self.answering: set[str] = set()
        self.ticks = 0
        self.plan: dict[int, list[str]] = {}  # tick -> names ending then
        self.at_once: list[set[str]] = []

    def start(self, name: str) -> Any:
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

    async def __call__(self, name: str, args: dict[str, Any] | None = None) -> Any:
        self.calls.append(name)
        return SimpleNamespace(is_error=False, content=[SimpleNamespace(type='text', text=self.answer)])


class Done:
    def __init__(self, code: int = 0) -> None:
        self.code = code

    def wait(self) -> int:
        return self.code


def pool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, write: Any, unit: Any = None) -> Any:
    """workers with every process faked: each worker writes what write(name, folder, port) returns as its results."""
    workers = fresh('workers')
    monkeypatch.setitem(vars(workers), 'ports', lambda count: list(range(5001, 5001 + count)))
    monkeypatch.setitem(vars(workers), 'agents_designers', dict)
    monkeypatch.setitem(vars(workers), 'agent_folder', lambda port: str(tmp_path / ('agent_%d' % port)))

    def crash_dumps(ports: Any = (), run_port: bool = True) -> set[str]:
        assert not run_port, "the pool's parent has no Designer on the default port (REVIEW.md TST-280)"
        return dumps_in(tmp_path, ports)

    monkeypatch.setitem(vars(workers), 'crash_dumps', crash_dumps)
    monkeypatch.setattr(workers.tempfile, 'mkdtemp', lambda prefix: str(tmp_path / 'root'))
    os.makedirs(tmp_path / 'root')
    waits: list[float] = []
    monkeypatch.setitem(vars(workers), 'sleep', waits.append)
    workers.waits = waits
    started: list[str] = []

    gates: list[Any] = []

    def schedule(names: list[str], slots: int, start: Any, **kw: Any) -> dict[str, int]:
        # what run_pool must pass on (REVIEW.md TST-268): these have defaults or do nothing when left out
        assert kw['exclusive'] == workers.CLIPBOARD and kw['solo'] == workers.SOLO
        gates.append(kw['gate'])
        codes = {}
        for name in names:
            started.append(name)
            proc = start(name)
            codes[name] = proc.wait()
        return codes

    monkeypatch.setitem(vars(workers), 'schedule', schedule)

    def popen(command: list[str], env: dict[str, str], **kwargs: Any) -> Done:
        name = command[command.index('--worker') + 1]
        folder = os.path.dirname(command[command.index('--results') + 1])
        assert gates and {key: env.get(key) for key in gates[-1].env()} == gates[-1].env(), (
            'the lock: in its environment'
        )
        for own in ('SD_SNAPSHOT_DIR', 'TMPDIR'):  # each worker's, in its folder (REVIEW.md TST-274)
            assert os.path.realpath(env[own]).startswith(os.path.realpath(folder) + os.sep), (own, env[own])
        started.append('--first ' + name if '--first' in command else name)
        Path(folder, name + '.log').write_text('PASS  t  check of %s\n' % name)
        part = write(name, folder, int(env['SD_BRIDGE_PORT']))
        if part is not None:
            Path(command[command.index('--results') + 1]).write_text(json.dumps(part))
        return Done(0 if part is not None else 2)

    monkeypatch.setattr(workers.subprocess, 'Popen', popen)
    monkeypatch.setitem(vars(workers), 'start_unit', unit or (lambda folder: unit_log(folder, 0)))
    workers.started = started
    return workers


def dumps_in(root: Path, ports: Any) -> set[str]:
    """common.crash_dumps over the fake agent folders: the completed reports in agent_<port>/home."""
    return {str(p) for port in ports for p in (root / ('agent_%d' % port)).glob('home/**/completed/*')}


def unit_log(folder: str, code: int) -> Done:
    Path(folder, 'unit.log').write_text('%s in 61.25s\n' % ('1 failed, 9 passed' if code else '10 passed'))
    return Done(code)


def part(name: str, quit: str | None = 'Designer quit after 2s.') -> dict[str, Any]:
    return {
        'tools': ['t'],
        'results': {'t': [True]},
        'skipped': [],
        'times': {name: 1.0},
        'quit': None if name == 'lifecycle' else quit,
        'quit_at': None if name == 'lifecycle' else time.time(),  # just now: the pool waits from it
    }
