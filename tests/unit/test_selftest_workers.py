"""tests/test_all_tools/workers.py's parts the pool is built of: ports, a worker's environment, merging the workers'
results and the unit suite's start. The pool itself, and a worker's end: test_selftest_pool.py. No Designer: processes, ports and sessions are replaced by fakes."""

import inspect
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from selftest_fakes import fresh

from conftest import SELFTEST_DIR


def _workers() -> Any:
    return fresh('workers')


# --- ports and folders


def test_the_ports_are_distinct_and_free_of_other_runs() -> None:
    workers = _workers()
    # free of other runs: the ports no Designer an agent started is recorded on (REVIEW.md TST-274)
    lifecycle = sys.modules['test_all_tools.lifecycle.checks']
    assert inspect.signature(workers.ports).parameters['take'].default is lifecycle.unused_port
    taken = iter([5001, 5001, 5002, 5003, 5003, 5004])
    assert workers.ports(4, take=lambda: next(taken)) == [5001, 5002, 5003, 5004]
    with pytest.raises(RuntimeError, match='port'):
        workers.ports(2, take=lambda: 0)


def test_a_worker_gets_its_port_and_snapshots_by_their_real_path(tmp_path: Path) -> None:
    # the snapshots under a symlink (macOS's temp folder) leave the paths in them one `..` short (ROADMAP item 57)
    workers = _workers()
    real = tmp_path / 'real'
    real.mkdir()
    (tmp_path / 'link').symlink_to(real)
    env = workers.worker_env(5001, str(tmp_path / 'link'))
    assert env['SD_BRIDGE_PORT'] == '5001'
    assert env['SD_SNAPSHOT_DIR'] == os.path.join(os.path.realpath(real), 'snapshots')
    assert env['PATH'] == os.environ['PATH']  # the rest of the environment, which stdio_client wouldn't pass
    # no folder shared with another worker: its scratch and its server's temporary files go in a temp folder of its own
    assert env['TMPDIR'] == os.path.join(os.path.realpath(real), 'tmp') and os.path.isdir(env['TMPDIR'])


# --- one summary


def _part(tools: list[str], results: dict[str, list[bool]], skipped: list[Any], times: dict[str, float]) -> Any:
    return {'tools': tools, 'results': results, 'skipped': skipped, 'times': times}


def test_the_results_merge_into_one_summary() -> None:
    workers = _workers()
    parts = {
        'shard1': _part(
            ['a', 'b'], {'a': [True], 'x': [True]}, [['x', 'one']], {'graph_edit_create': 2.0, 'facts': 70.0}
        ),
        'shard2': _part(['a', 'b'], {'a': [False], 'b': [True]}, [], {'graph_edit_create': 3.0, 'bridge': 10.0}),
    }
    tools, results, skipped, times = workers.merge(parts)
    assert tools == ['a', 'b']
    assert results == {'a': [True, False], 'x': [True], 'b': [True]}
    assert skipped == [('x', 'one')]
    assert times == {'graph_edit_create': 3.0, 'facts': 70.0, 'bridge': 10.0}


def test_a_worker_without_results_fails_the_run() -> None:
    workers = _workers()
    _, results, _, _ = workers.merge({'shard1': _part(['a'], {'a': [True]}, [], {}), 'shard2': None})
    assert results['self-test'] == [False]


# --- the unit suite beside the workers


def test_the_unit_suite_runs_whole_from_the_repository_in_a_temp_folder_of_its_own(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workers = _workers()
    seen: dict[str, Any] = {}

    def popen(command: list[str], **kwargs: Any) -> str:
        seen.update(command=command, **kwargs)
        return 'process'

    monkeypatch.setattr(workers.subprocess, 'Popen', popen)
    folder = tmp_path / 'unit'
    folder.mkdir()
    assert workers.start_unit(str(folder)) == 'process'
    assert seen['command'] == [sys.executable, '-m', 'pytest', '-q']  # no test ids: the whole suite (AGENTS.md)
    assert seen['cwd'] == os.path.dirname(os.path.dirname(SELFTEST_DIR))
    assert seen['env']['TMPDIR'] == os.path.join(os.path.realpath(folder), 'tmp')  # no folder shared with a worker
    assert os.path.isdir(seen['env']['TMPDIR'])
    assert seen['stdout'].name == str(folder / 'unit.log')
