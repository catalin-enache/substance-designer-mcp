"""The live self-test's lifecycle checks (tests/test_all_tools/lifecycle.py), with a fake client and no Designer: what
they take as their own, and the user's log they watch."""

import asyncio
import importlib
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import project_constants
from conftest import SELFTEST_DIR
from project_constants import agent_designer_file, agent_folder_name

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='no os.getuid there, and no agent folders')


def _lifecycle() -> Any:  # a module imported by name: PyCharm can't see its names
    """lifecycle.py imported afresh with the self-test's modules, so each test starts with an empty check record."""
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    for name in [m for m in sys.modules if m == 'test_all_tools' or m.startswith('test_all_tools.')]:
        del sys.modules[name]
    return importlib.import_module('test_all_tools.lifecycle')


def _answer(out: str) -> SimpleNamespace:
    return SimpleNamespace(is_error=False, content=[SimpleNamespace(type='text', text=out)])


@pytest.mark.parametrize('recorded', ['before the launch', 'by the launch'])
def test_the_check_on_another_port_never_quits_a_designer_it_didnt_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], recorded: str
) -> None:
    # REVIEW.md TST-154: it took whatever record its free port had as its own second Designer, and quit it and removed
    # its folder: here another run's, still starting there (recorded, not listening yet, so the port looks free), or
    # recorded there just before this launch, which then finds it running
    lifecycle = _lifecycle()
    common = lifecycle.common
    other = 1  # a port no real agent folder is named for
    theirs = 4242
    record = json.dumps({'pid': theirs, 'start': 'x', 'home': None})
    if recorded == 'before the launch':
        Path(agent_designer_file(other)).write_text(record)
    monkeypatch.setitem(vars(common), 'SHORT_TEMP', str(tmp_path))
    folder = tmp_path / agent_folder_name(other)
    if recorded == 'before the launch':
        folder.mkdir()
    monkeypatch.setitem(vars(lifecycle), 'free_port', lambda: other)
    monkeypatch.setitem(vars(lifecycle), 'designer_pids', lambda: [77, theirs])
    monkeypatch.setitem(vars(lifecycle), 'crash_dumps', lambda ports=(): set())
    monkeypatch.setitem(vars(lifecycle), 'new_crash_dumps', lambda before, wait_s=10, ports=(): set())
    monkeypatch.setitem(vars(lifecycle), 'users_log', lambda: None)
    monkeypatch.setitem(vars(lifecycle), 'users_settings_file', lambda: None)
    calls: list[tuple[str, dict[str, Any]]] = []

    async def c(name: str, args: dict[str, Any] | None = None) -> SimpleNamespace:
        calls.append((name, args or {}))
        if name == 'launch_designer':  # the other run's, made as this launch looks: it finds that one running
            folder.mkdir(exist_ok=True)
            Path(agent_designer_file(other)).write_text(record)
            return _answer('Designer already running on port %d: idle, 0 queued' % other)
        return _answer('77\n')

    asyncio.run(lifecycle.check_launch_on_another_port(SimpleNamespace(c=c)))
    assert not [args for name, args in calls if name == 'quit_designer'], calls
    assert folder.is_dir() and os.path.exists(agent_designer_file(other))
    # the check that says why, by name (REVIEW.md TST-173: an earlier check of the fake's answers always failed)
    said = (
        'finds a port no Designer an agent started is recorded for'
        if recorded == 'before the launch'
        else ('starts a second Designer on another port')
    )
    assert re.search(r'^FAIL  launch_designer +%s' % re.escape(said), capsys.readouterr().out, re.M)


NOT_ANSWERING = (
    ' did not answer within 240s. It may be showing a dialog, or the %s plugin did not load (check the Designer log). '
    'If it needs longer, call this with a larger wait_s.' % project_constants.PLUGIN
)


@pytest.mark.parametrize(
    'answer, ours',
    [('Designer' + NOT_ANSWERING, True), ('Designer is already running, but its bridge' + NOT_ANSWERING, False)],
    ids=['its own launch, never answering', 'one already running there, not answering'],
)
def test_the_check_on_another_port_ends_the_designer_its_own_launch_left(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: str, ours: bool
) -> None:
    # REVIEW.md TST-187: a launch that started a Designer, recorded on the check's free port, and timed out was not the
    # check's to quit, so a regression there left a Designer open on a random port after the run; one that was already
    # running there (another run's) still isn't the check's
    lifecycle = _lifecycle()
    common = lifecycle.common
    other, started = 1, 4242
    monkeypatch.setitem(vars(common), 'SHORT_TEMP', str(tmp_path))
    folder = tmp_path / agent_folder_name(other)
    monkeypatch.setitem(vars(lifecycle), 'free_port', lambda: other)
    monkeypatch.setitem(vars(lifecycle), 'designer_pids', lambda: [77, started])  # still there after the quit asked
    monkeypatch.setitem(vars(lifecycle), 'crash_dumps', lambda ports=(): set())
    monkeypatch.setitem(vars(lifecycle), 'new_crash_dumps', lambda before, wait_s=10, ports=(): set())
    monkeypatch.setitem(vars(lifecycle), 'users_log', lambda: None)
    monkeypatch.setitem(vars(lifecycle), 'users_settings_file', lambda: None)
    calls: list[tuple[str, dict[str, Any]]] = []

    async def c(name: str, args: dict[str, Any] | None = None) -> SimpleNamespace:
        calls.append((name, args or {}))
        if name == 'launch_designer':  # recorded on the port as it starts, then no answer
            folder.mkdir(exist_ok=True)
            Path(agent_designer_file(other)).write_text(json.dumps({'pid': started, 'start': 'x', 'home': None}))
            return _answer(answer)
        return _answer('77\n')

    asyncio.run(lifecycle.check_launch_on_another_port(SimpleNamespace(c=c)))
    quits = [args for name, args in calls if name == 'quit_designer']
    assert quits == ([{'port': other, 'wait_s': 10}] if ours else []), calls
    assert folder.is_dir()  # its process still listed: kept, as for a crash dump
    assert False in common.results['launch_designer']


def test_the_users_log_is_the_one_read_designer_log_finds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-156: SD_DESIGNER_LOG was ignored, so the check watched another file
    lifecycle = _lifecycle()
    log = tmp_path / 'my.log'
    log.write_text('a line\n')
    monkeypatch.setenv('SD_DESIGNER_LOG', str(log))
    assert lifecycle.users_log() == (str(log), len('a line\n'))


def test_no_users_log_is_no_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-156: where the user never opened Designer there is no log, and none appearing is the log left alone
    lifecycle = _lifecycle()
    monkeypatch.delenv('SD_DESIGNER_LOG', raising=False)
    monkeypatch.setenv('HOME', str(tmp_path))
    assert lifecycle.users_log() is None


def test_the_agent_folders_are_named_in_one_place() -> None:
    # REVIEW.md TST-156: the folder was spelled out four times, beside common.SHORT_TEMP and agent_folder_name
    source = Path(SELFTEST_DIR, 'lifecycle.py').read_text(encoding='utf-8')
    assert "'/tmp" not in source and 'sd_mcp_%d' not in source


def test_the_self_test_reads_start_times_as_the_server_does() -> None:
    # REVIEW.md SRV-92: end_own_designer compared its own ps text with the record's; one reading, the server's
    source = Path(SELFTEST_DIR, 'common.py').read_text(encoding='utf-8')
    assert 'lstart' not in source and '_process_start' in source


@pytest.mark.parametrize(
    'pids, agents, users, here',
    [
        ([11], {}, True, True),  # unrecorded: the user's, or one still starting
        ([12], {9902: 12}, False, False),  # another run's, on its own port
        ([11, 12], {9877: 11, 9902: 12}, False, True),  # this run's, beside another run's
        ([11, 12], {9902: 12}, True, True),  # the user's, beside another run's
    ],
)
def test_the_suite_tells_its_designers_from_other_runs(
    monkeypatch: pytest.MonkeyPatch, pids: list[int], agents: dict[int, int], users: bool, here: bool
) -> None:
    # REVIEW.md TST-170: designer_alive() is any Designer on the machine, which the suite took for the user's or the
    # run's own; another run's, on its own port, is neither
    lifecycle = _lifecycle()
    common = lifecycle.common
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setitem(vars(common), 'PORT', 9877)
    monkeypatch.setitem(vars(common), 'designer_pids', lambda: list(pids))
    monkeypatch.setitem(vars(common), 'agents_designers', lambda: dict(agents))
    assert common.users_designer_running() == users
    assert common.designer_here() == here


def test_the_quit_checks_ask_about_the_runs_designer_only() -> None:
    # REVIEW.md TST-170: each quit check's `not designer_alive()` failed while another run's Designer ran
    source = Path(SELFTEST_DIR, 'lifecycle.py').read_text(encoding='utf-8')
    assert 'designer_alive' not in source and source.count('not designer_here()') == 7


def test_ending_the_runs_designer_forces_only_its_own(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-170: after its SIGTERM, end_own_designer sent SIGKILL if any Designer still ran, another run's too
    import signal
    import time

    from conftest import patch_server

    lifecycle = _lifecycle()
    common = lifecycle.common
    Path(agent_designer_file(common.PORT)).write_text(json.dumps({'pid': 11, 'start': 'at 11', 'home': None}))
    patch_server(monkeypatch, '_process_start', lambda pid: 'at 11')
    monkeypatch.setitem(vars(common), 'designer_pids', lambda: [12])  # 11 ended on SIGTERM; another run's is up
    monkeypatch.setitem(vars(common), 'designer_alive', lambda: True)
    sent: list[tuple[int, int]] = []
    monkeypatch.setattr(os, 'kill', lambda pid, sig: sent.append((pid, sig)))
    monkeypatch.setattr(time, 'sleep', lambda seconds: None)
    common.end_own_designer()
    assert sent == [(11, signal.SIGTERM)]


@pytest.mark.parametrize('outcome', [2, 3, FileNotFoundError(2, 'No such file', 'pgrep')], ids=['2', '3', 'no pgrep'])
@pytest.mark.parametrize('helper', ['designer_pids', 'designer_alive'])
def test_a_failing_pgrep_is_an_error_not_no_designer(
    monkeypatch: pytest.MonkeyPatch, helper: str, outcome: int | Exception
) -> None:
    # REVIEW.md INS-27: designer_pids read only pgrep's output, so a failure was "none running", and
    # check_launch_on_another_port's finally removed a running Designer's folders
    import subprocess

    lifecycle = _lifecycle()
    common = lifecycle.common
    monkeypatch.setattr(sys, 'platform', 'darwin')
    seen: list[list[str]] = []

    def run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
        seen.append(cmd)
        if isinstance(outcome, Exception):
            raise outcome
        return subprocess.CompletedProcess(cmd, outcome, '', 'pgrep: cannot allocate memory')

    monkeypatch.setattr(subprocess, 'run', run)
    with pytest.raises(OSError, match="Designer's processes couldn't be listed"):
        getattr(common, helper)()
    assert seen and seen[0][-1] == project_constants.DESIGNER_PROCESS  # the server's pattern, not a copy


def test_pgrep_finding_nothing_is_no_designer(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    lifecycle = _lifecycle()
    common = lifecycle.common
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, '', ''))
    assert common.designer_pids() == [] and common.designer_alive() is False


def test_the_lifecycle_checks_take_a_port_no_other_run_holds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-172: another run's Designer still starting is recorded, and has its folder, but listens nowhere yet:
    # a port that binds isn't free of it
    lifecycle = _lifecycle()
    monkeypatch.setitem(vars(lifecycle.common), 'SHORT_TEMP', str(tmp_path))
    Path(agent_designer_file(1)).write_text('{}')  # recorded
    (tmp_path / agent_folder_name(2)).mkdir()  # its folder made
    offered = iter([1, 2, 3])
    assert lifecycle.unused_port(lambda: next(offered)) == 3
    assert lifecycle.unused_port(lambda: 1) == 0  # ten tries, none free


def test_every_port_the_lifecycle_checks_take_goes_through_unused_port() -> None:
    # REVIEW.md TST-172: the refusal check bound port 0 and the hand-over check took free_port(), neither looking for
    # another run's record or folder there
    source = Path(SELFTEST_DIR, 'lifecycle.py').read_text(encoding='utf-8')
    assert 'free_port()' not in source, 'a port taken without unused_port'
    assert 'unused_port(hold)' in source, 'the refusal check binds its port without unused_port'


def test_ending_the_runs_designer_survives_a_failing_ps(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md SRV-97: the server's _process_start now raises when ps fails; end_own_designer runs in main()'s
    # finally, so that must end in a line, not a traceback without the summary
    from conftest import patch_server, server

    lifecycle = _lifecycle()
    common = lifecycle.common
    Path(agent_designer_file(common.PORT)).write_text(json.dumps({'pid': 11, 'start': 'at 11', 'home': None}))

    def fails(pid: int) -> str:
        raise server._NoListing("the start of process 11 couldn't be read")

    patch_server(monkeypatch, '_process_start', fails)
    common.end_own_designer()
    assert "couldn't be read" in capsys.readouterr().out
