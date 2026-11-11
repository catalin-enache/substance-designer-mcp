"""The live self-test's lifecycle checks (tests/test_all_tools/lifecycle/checks.py), with a fake client and no Designer: what
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
    """lifecycle/checks.py imported afresh with the self-test's modules, so each test starts with an empty check record."""
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    for name in [m for m in sys.modules if m == 'test_all_tools' or m.startswith('test_all_tools.')]:
        del sys.modules[name]
    return importlib.import_module('test_all_tools.lifecycle.checks')


def _answer(out: str) -> SimpleNamespace:
    return SimpleNamespace(is_error=False, content=[SimpleNamespace(type='text', text=out)])


def _no_dumps(ports: Any = ()) -> set[str]:
    return set()


def _no_wait(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """The crash watch of a check run here: no 10 s wait, no real crash-dump folder (REVIEW.md TST-261). The list gets
    each one made: empty, the patch no longer reaches what the check builds."""
    module = sys.modules['test_all_tools.crash_watch']
    real, made = module.CrashWatch, []

    def build() -> Any:
        made.append(real(wait_s=0, find=_no_dumps, sleep=lambda seconds: None))
        return made[-1]

    monkeypatch.setitem(vars(module), 'CrashWatch', build)
    return made


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
    watches = _no_wait(monkeypatch)
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
    assert watches or recorded == 'before the launch', 'the patch reaches the watch the check builds'
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
    watches = _no_wait(monkeypatch)
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
    assert watches, 'the patch reaches the watch the check builds'
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
    source = Path(SELFTEST_DIR, 'lifecycle', 'checks.py').read_text(encoding='utf-8')
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
    # REVIEW.md TST-170: each quit check's `not designer_alive()` failed while another run's Designer ran; then
    # `not designer_here()` failed in a pool, where another worker's Designer, starting and not yet recorded, may be
    # this run's for all it can tell: each asks about the process it quit
    source = Path(SELFTEST_DIR, 'lifecycle', 'checks.py').read_text(encoding='utf-8')
    assert 'designer_alive' not in source and 'designer_here' not in source
    assert source.count('has_ended(quitting)') == 10 and source.count('quitting = own_pid()') == 10


def test_its_own_designer_is_gone_whatever_else_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    lifecycle = _lifecycle()
    common = lifecycle.common
    monkeypatch.setitem(vars(lifecycle), 'agents_designers', lambda: {common.PORT: 11, common.PORT + 1: 12})
    assert lifecycle.own_pid() == 11
    monkeypatch.setitem(vars(lifecycle), 'designer_pids', lambda: [12, 13])  # 13: one starting, unrecorded
    assert lifecycle.has_ended(11) and not lifecycle.has_ended(12)
    assert not lifecycle.has_ended(None), 'none recorded before the quit: nothing seen going'


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
    source = Path(SELFTEST_DIR, 'lifecycle', 'checks.py').read_text(encoding='utf-8')
    assert 'free_port()' not in source, 'a port taken without unused_port'
    assert 'unused_port(hold)' in source, 'the refusal check binds its port without unused_port'


AGENTS = 'idle\nStarted by an agent: disposable, nothing in it is kept.'
USERS = "idle\nNot started by an agent: it is the user's."
STARTED = 'Designer started in 7s, on port 9877: idle'


class _Designer:
    """c(name, args) for lifecycle's own preparation: designer_status answers `status` (an error when None, as with no
    Designer running), launch_designer `launch`."""

    def __init__(self, status: str | None, launch: str = STARTED, launch_error: bool = False) -> None:
        self.status, self.launch, self.launch_error = status, launch, launch_error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, name: str, args: dict[str, Any] | None = None) -> Any:
        self.calls.append((name, args or {}))
        if name == 'designer_status':
            return SimpleNamespace(
                is_error=self.status is None, content=[SimpleNamespace(type='text', text=self.status or 'no Designer')]
            )
        if name == 'launch_designer':
            return SimpleNamespace(is_error=self.launch_error, content=[SimpleNamespace(type='text', text=self.launch)])
        return _answer('Designer quit after 2s.')

    def names(self) -> list[str]:
        return [n for n, _ in self.calls]


def _prepared(lifecycle: Any, c: _Designer) -> bool:
    watch = sys.modules['test_all_tools.crash_watch'].CrashWatch(wait_s=0, find=_no_dumps, sleep=lambda seconds: None)
    ready = bool(asyncio.run(lifecycle.check_a_designer_of_its_own(SimpleNamespace(c=c, crash_watch=watch))))
    watch.settle()
    return ready


def test_lifecycle_reads_the_guide_itself_first() -> None:
    # nothing of the suite before it: every tool refuses until get_guide, and the code tools until its scripting part
    c = _Designer(None)
    assert _prepared(_lifecycle(), c)
    assert c.calls[:2] == [('get_guide', {}), ('get_guide', {'part': 'scripting'})]


def test_lifecycle_starts_a_designer_when_none_runs() -> None:
    c = _Designer(None)
    assert _prepared(_lifecycle(), c)
    assert 'launch_designer' in c.names()
    assert 'quit_designer' not in c.names()


def test_lifecycle_replaces_a_designer_an_agent_started_by_one_of_its_own() -> None:
    # whatever earlier checks left in it is gone, and the one running is the last started (the hand-over check's need)
    c = _Designer(AGENTS)
    assert _prepared(_lifecycle(), c)
    assert c.names().index('quit_designer') < c.names().index('launch_designer')


def test_lifecycle_never_touches_a_designer_no_agent_started(capsys: pytest.CaptureFixture[str]) -> None:
    c = _Designer(USERS)
    assert not _prepared(_lifecycle(), c)
    assert 'quit_designer' not in c.names() and 'launch_designer' not in c.names()
    assert 'FAIL' in capsys.readouterr().out


@pytest.mark.parametrize(
    'launch, error',
    [
        ('Designer already running on port 9877: idle', False),  # one no agent started, still starting when asked
        ('Port 9877 is held by another program', True),
    ],
)
def test_lifecycle_runs_nothing_without_a_designer_it_just_started(
    capsys: pytest.CaptureFixture[str], launch: str, error: bool
) -> None:
    assert not _prepared(_lifecycle(), _Designer(None, launch, error))
    assert 'FAIL' in capsys.readouterr().out


@pytest.mark.parametrize('prepared', [True, False])
def test_lifecycle_prepares_before_its_first_check_and_stops_if_it_cant(prepared: bool) -> None:
    lifecycle = _lifecycle()
    order: list[str] = []

    async def prepare(ctx: Any) -> bool:
        order.append('prepare')
        return prepared

    async def first_check(ctx: Any) -> None:
        order.append('first check')
        raise RuntimeError('stop here')

    vars(lifecycle)['check_a_designer_of_its_own'] = prepare
    vars(lifecycle)['check_a_designer_sharing_the_temp_folder_hands_over'] = first_check
    ctx = SimpleNamespace(c=_Designer(None), scratch='scratch')
    if prepared:
        with pytest.raises(RuntimeError, match='stop here'):
            asyncio.run(lifecycle.run(ctx))
        assert order == ['prepare', 'first check']
    else:
        asyncio.run(lifecycle.run(ctx))
        assert order == ['prepare']


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


def test_lifecycle_waits_for_crash_dumps_once_not_after_each_quit() -> None:
    """new_crash_dumps waits 10 s after each quit with no dump: eight of them were about 80 s of lifecycle, the longest
    worker. Its checks go through one CrashWatch (crash_watch.watching_crashes), settled once at the end of run()."""
    source = Path(SELFTEST_DIR, 'lifecycle', 'checks.py').read_text(encoding='utf-8')
    assert not re.search(r'\bnew_crash_dumps\b', source)
    run = source[source.index('async def run(ctx: Ctx)') :]
    assert re.search(r'with\s+watching_crashes\(ctx\)', run)


def test_every_quit_lifecycle_makes_is_a_watched_step() -> None:
    """REVIEW.md TST-236: a dump is given to the latest step started before it was written, so a quit with no step of
    its own had its dump reported under the quit before it. Every quit that ends a Designer (one with arguments: the
    refused one ends none) and the launch ending one not answering start a step of their own (watch.step()) after the
    last check."""
    source = Path(SELFTEST_DIR, 'lifecycle', 'checks.py').read_text(encoding='utf-8')
    run = source[source.index('async def check_a_designer_of_its_own(') :]  # REVIEW.md TST-257: its quit too
    calls = [m.start() for m in re.finditer(r"c\(\s*'quit_designer',", run)]
    ending = run.index("'Ended a Designer an agent started'")
    calls.append(run.rindex("c('launch_designer'", 0, ending))
    # that launch ends a Designer whose shutdown the phase began: a crash in it is that step's (REVIEW.md TST-257)
    shutdown = run.rindex("'lifecycle/hold_thread_pool'", 0, calls[-1])
    assert run.rfind('watch.step(', 0, shutdown) > run.rfind('check(', 0, shutdown)
    unwatched = [
        run[at : at + 50].replace('\n', ' ')
        for at in calls
        if run.rfind('watch.step(', 0, at) < max(run.rfind('check(', 0, at), run.rfind('check(\n', 0, at))
    ]
    assert len(calls) >= 8 and not unwatched, unwatched


def test_a_normal_close_forced_during_its_shutdown_is_recorded_for_the_pool(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-293: the pool counts lifecycle's too, and keeps its folder, from what its worker reports
    import project_constants

    lifecycle = _lifecycle()
    common = lifecycle.common
    monkeypatch.setitem(vars(common), 'forced_in_shutdown', [])
    hung = 'Designer quit after 31s (%s: every window had closed; its log stopped at "[INFO][IPC] Remove PID").' % (
        project_constants.QUIT_FORCED_IN_SHUTDOWN
    )
    not_closed = 'Designer quit after 31s (%s; its log stopped at "x").' % project_constants.QUIT_FORCED_NOT_CLOSED
    assert common.normal_close('Designer quit after 2s.', 'a') and common.forced_in_shutdown == []
    assert common.normal_close(hung, 'the modal close') and common.forced_in_shutdown == ['the modal close']
    assert not common.normal_close(not_closed, 'b') and common.forced_in_shutdown == ['the modal close']
    assert '[INFO][IPC] Remove PID' in capsys.readouterr().out, 'printed whole'
