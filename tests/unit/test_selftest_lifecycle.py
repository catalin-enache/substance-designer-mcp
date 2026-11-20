"""The live self-test's lifecycle checks (tests/test_all_tools/lifecycle/checks.py), with a fake client and no Designer: what
they take as their own, and the user's log they watch."""

import asyncio
import importlib
import json
import os
import re
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, Unpack

import pytest
from docs_text import flat
from selftest_fakes import fresh, tool_result

import project_constants
from conftest import SELFTEST_DIR, RunOptions
from project_constants import ToolArgs, agent_designer_file, agent_folder_name

if TYPE_CHECKING:  # for the checker only: each test imports the self-test's modules afresh (fresh())
    from test_all_tools.common import Ctx
    from test_all_tools.crash_watch import CrashWatch
    from test_all_tools.window_server import FrontWatch

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='no os.getuid there, and no agent folders')


def _windows_read(monkeypatch: pytest.MonkeyPatch, lifecycle: ModuleType) -> list[bool]:
    """Whether each front watch entered watches (REVIEW.md TST-458: a real one, started by the check's launch, read the
    user's active app and the windows on their screen)."""
    watching: list[bool] = []
    real = lifecycle.window_server.FrontWatch
    enter: Callable[[FrontWatch], FrontWatch] = real.__enter__

    def entered(self: 'FrontWatch') -> 'FrontWatch':
        watching.append(self.watching)
        return enter(self)

    monkeypatch.setattr(real, '__enter__', entered)
    return watching


def _no_front_watch(monkeypatch: pytest.MonkeyPatch, lifecycle: ModuleType) -> None:
    """The check's front watch made one that samples nothing: a real one reads the user's active app and the windows on
    their screen (REVIEW.md TST-458)."""
    real = lifecycle.window_server.FrontWatch
    monkeypatch.setitem(vars(lifecycle.window_server), 'FrontWatch', lambda watching=True: real(watching=False))


def _no_dumps(ports: Sequence[int] = ()) -> set[str]:
    return set()


def _no_dump_coming(ports: Sequence[int], before: set[str]) -> bool:
    """No crash handler running: the real look lists the crash handlers and the crash-dump folders (REVIEW.md
    TST-458)."""
    return False


def _no_wait(monkeypatch: pytest.MonkeyPatch) -> list['CrashWatch']:
    """The crash watch of a check run here: no 10 s wait, no real crash-dump folder (REVIEW.md TST-261). The list gets
    each one made: empty, the patch no longer reaches what the check builds."""
    module = sys.modules['test_all_tools.crash_watch']
    real = module.CrashWatch
    made: list[CrashWatch] = []

    def build() -> 'CrashWatch':
        made.append(real(wait_s=0, find=_no_dumps, sleep=lambda seconds: None, coming=_no_dump_coming))
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
    lifecycle = fresh('lifecycle.checks')
    common = lifecycle.common
    read = _windows_read(monkeypatch, lifecycle)
    _no_front_watch(monkeypatch, lifecycle)
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
    calls: list[tuple[str, ToolArgs]] = []

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        calls.append((name, args or {}))
        if name == 'launch_designer':  # the other run's, made as this launch looks: it finds that one running
            folder.mkdir(exist_ok=True)
            Path(agent_designer_file(other)).write_text(record)
            return tool_result('Designer already running on port %d: idle, 0 queued' % other)
        return tool_result('77\n')

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
    assert True not in read, 'a real front watch read the windows on screen'


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
    lifecycle = fresh('lifecycle.checks')
    common = lifecycle.common
    read = _windows_read(monkeypatch, lifecycle)
    _no_front_watch(monkeypatch, lifecycle)
    other, started = 1, 4242
    monkeypatch.setitem(vars(common), 'SHORT_TEMP', str(tmp_path))
    folder = tmp_path / agent_folder_name(other)
    monkeypatch.setitem(vars(lifecycle), 'free_port', lambda: other)
    monkeypatch.setitem(vars(lifecycle), 'designer_pids', lambda: [77, started])  # still there after the quit asked
    monkeypatch.setitem(vars(lifecycle), 'crash_dumps', lambda ports=(): set())
    watches = _no_wait(monkeypatch)
    monkeypatch.setitem(vars(lifecycle), 'users_log', lambda: None)
    monkeypatch.setitem(vars(lifecycle), 'users_settings_file', lambda: None)
    calls: list[tuple[str, ToolArgs]] = []

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        calls.append((name, args or {}))
        if name == 'launch_designer':  # recorded on the port as it starts, then no answer
            folder.mkdir(exist_ok=True)
            Path(agent_designer_file(other)).write_text(json.dumps({'pid': started, 'start': 'x', 'home': None}))
            return tool_result(answer)
        return tool_result('77\n')

    asyncio.run(lifecycle.check_launch_on_another_port(SimpleNamespace(c=c)))
    assert watches, 'the patch reaches the watch the check builds'
    quits = [args for name, args in calls if name == 'quit_designer']
    assert quits == ([{'port': other, 'wait_s': 10}] if ours else []), calls
    assert folder.is_dir()  # its process still listed: kept, as for a crash dump
    assert False in common.results['launch_designer']
    assert True not in read, 'a real front watch read the windows on screen'


def test_the_users_log_is_the_one_read_designer_log_finds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-156: SD_DESIGNER_LOG was ignored, so the check watched another file
    lifecycle = fresh('lifecycle.checks')
    log = tmp_path / 'my.log'
    log.write_text('a line\n')
    monkeypatch.setenv('SD_DESIGNER_LOG', str(log))
    assert lifecycle.users_log() == (str(log), len('a line\n'))


def test_no_users_log_is_no_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-156: where the user never opened Designer there is no log, and none appearing is the log left alone
    lifecycle = fresh('lifecycle.checks')
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
    lifecycle = fresh('lifecycle.checks')
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
    lifecycle = fresh('lifecycle.checks')
    common = lifecycle.common
    monkeypatch.setitem(vars(lifecycle), 'agents_designers', lambda: {common.PORT: 11, common.PORT + 1: 12})
    assert lifecycle.own_pid() == 11
    monkeypatch.setitem(vars(lifecycle), 'designer_pids', lambda: [12, 13])  # 13: one starting, unrecorded
    assert lifecycle.has_ended(11) and not lifecycle.has_ended(12)
    assert not lifecycle.has_ended(None), 'none recorded before the quit: nothing seen going'


@pytest.mark.parametrize(
    'listed, sent',
    [([12], ['SIGTERM']), ([11, 12], ['SIGTERM', 'SIGKILL'])],
    ids=["its own ended, another run's up", 'its own still running at the end of the wait'],
)
def test_ending_the_runs_designer_forces_only_its_own(
    monkeypatch: pytest.MonkeyPatch, listed: list[int], sent: list[str]
) -> None:
    # REVIEW.md TST-170: after its SIGTERM, end_own_designer sent SIGKILL if any Designer still ran, another run's too.
    # Its wait is the server's _exited, which lists Designers as the server does: the processes are given there
    # (REVIEW.md TST-457: given to common, they reached nothing, and the SIGKILL had no test)
    import signal

    from conftest import patch_server

    lifecycle = fresh('lifecycle.checks')
    common = lifecycle.common
    Path(agent_designer_file(common.PORT)).write_text(json.dumps({'pid': 11, 'start': 'at 11', 'home': None}))
    patch_server(monkeypatch, '_process_start', lambda pid: 'at 11')
    patch_server(monkeypatch, '_designer_pids', lambda: listed)  # after its SIGTERM
    patch_server(monkeypatch, '_exit_watch', lambda pid: SimpleNamespace(wait=lambda limit: False))  # its limit
    signals: list[tuple[int, int]] = []
    monkeypatch.setattr(os, 'kill', lambda pid, sig: signals.append((pid, sig)))
    common.end_own_designer()
    assert signals == [(11, getattr(signal, name)) for name in sent]


def test_ending_the_runs_designer_waits_for_its_exit_not_a_fixed_time(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-421: 5 s after its SIGTERM, whatever the process did
    import signal
    import time

    from conftest import patch_server

    lifecycle = fresh('lifecycle.checks')
    common = lifecycle.common
    Path(agent_designer_file(common.PORT)).write_text(json.dumps({'pid': 11, 'start': 'at 11', 'home': None}))
    patch_server(monkeypatch, '_process_start', lambda pid: 'at 11')
    sent: list[tuple[int, int]] = []
    waited: list[tuple[int, float]] = []
    monkeypatch.setattr(os, 'kill', lambda pid, sig: sent.append((pid, sig)))

    def exited(pid: int, limit: float) -> bool:
        waited.append((pid, limit))
        return True

    patch_server(monkeypatch, '_exited', exited)
    monkeypatch.setattr(time, 'sleep', lambda seconds: pytest.fail('a fixed wait of %g s' % seconds))
    common.end_own_designer()
    assert sent == [(11, signal.SIGTERM)] and waited == [(11, common.END_WAIT_S)]


@pytest.mark.parametrize('outcome', [2, 3, FileNotFoundError(2, 'No such file', 'pgrep')], ids=['2', '3', 'no pgrep'])
@pytest.mark.parametrize('helper', ['designer_pids', 'designer_alive'])
def test_a_failing_pgrep_is_an_error_not_no_designer(
    monkeypatch: pytest.MonkeyPatch, helper: str, outcome: int | Exception
) -> None:
    # REVIEW.md INS-27: designer_pids read only pgrep's output, so a failure was "none running", and
    # check_launch_on_another_port's finally removed a running Designer's folders
    import subprocess

    lifecycle = fresh('lifecycle.checks')
    common = lifecycle.common
    monkeypatch.setattr(sys, 'platform', 'darwin')
    seen: list[list[str]] = []

    def run(cmd: list[str], **kw: Unpack[RunOptions]) -> subprocess.CompletedProcess[str]:
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

    lifecycle = fresh('lifecycle.checks')
    common = lifecycle.common
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, '', ''))
    assert common.designer_pids() == [] and common.designer_alive() is False


def test_the_lifecycle_checks_take_a_port_no_other_run_holds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-172: another run's Designer still starting is recorded, and has its folder, but listens nowhere yet:
    # a port that binds isn't free of it
    lifecycle = fresh('lifecycle.checks')
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
        self.calls: list[tuple[str, ToolArgs]] = []

    async def __call__(self, name: str, args: ToolArgs | None = None) -> SimpleNamespace:  # a CallToolResult
        self.calls.append((name, args or {}))
        if name == 'designer_status':
            return tool_result(self.status or 'no Designer', error=self.status is None)
        if name == 'launch_designer':
            return tool_result(self.launch, error=self.launch_error)
        return tool_result('Designer quit after 2s.')

    def names(self) -> list[str]:
        return [n for n, _ in self.calls]


def _prepared(lifecycle: ModuleType, c: _Designer) -> bool:
    watch: CrashWatch = sys.modules['test_all_tools.crash_watch'].CrashWatch(
        wait_s=0, find=_no_dumps, sleep=lambda seconds: None, coming=_no_dump_coming
    )
    ready = bool(asyncio.run(lifecycle.check_a_designer_of_its_own(SimpleNamespace(c=c, crash_watch=watch))))
    watch.settle()
    return ready


def test_lifecycle_reads_the_guide_itself_first() -> None:
    # nothing of the suite before it: every tool refuses until get_guide, and the code tools until its scripting part
    c = _Designer(None)
    assert _prepared(fresh('lifecycle.checks'), c)
    assert c.calls[:2] == [('get_guide', {}), ('get_guide', {'part': 'scripting'})]


def test_lifecycle_starts_a_designer_when_none_runs() -> None:
    c = _Designer(None)
    assert _prepared(fresh('lifecycle.checks'), c)
    assert 'launch_designer' in c.names()
    assert 'quit_designer' not in c.names()


def test_lifecycle_replaces_a_designer_an_agent_started_by_one_of_its_own() -> None:
    # whatever earlier checks left in it is gone, and the one running is the last started (the hand-over check's need)
    c = _Designer(AGENTS)
    assert _prepared(fresh('lifecycle.checks'), c)
    assert c.names().index('quit_designer') < c.names().index('launch_designer')


def test_lifecycle_never_touches_a_designer_no_agent_started(capsys: pytest.CaptureFixture[str]) -> None:
    c = _Designer(USERS)
    assert not _prepared(fresh('lifecycle.checks'), c)
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
    assert not _prepared(fresh('lifecycle.checks'), _Designer(None, launch, error))
    assert 'FAIL' in capsys.readouterr().out


@pytest.mark.parametrize('prepared', [True, False])
def test_lifecycle_prepares_before_its_first_check_and_stops_if_it_cant(prepared: bool) -> None:
    lifecycle = fresh('lifecycle.checks')
    order: list[str] = []

    async def prepare(ctx: 'Ctx') -> bool:
        order.append('prepare')
        return prepared

    async def first_check(ctx: 'Ctx') -> None:
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

    lifecycle = fresh('lifecycle.checks')
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
        flat(run[at : at + 50])
        for at in calls
        if run.rfind('watch.step(', 0, at) < max(run.rfind('check(', 0, at), run.rfind('check(\n', 0, at))
    ]
    assert len(calls) >= 8 and not unwatched, unwatched


def test_a_normal_close_forced_during_its_shutdown_is_recorded_for_the_pool(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-293: the pool counts lifecycle's too, and keeps its folder, from what its worker reports
    import project_constants

    lifecycle = fresh('lifecycle.checks')
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


def _samples() -> ModuleType:  # a module imported by name: PyCharm can't see its names
    fresh('lifecycle.checks')  # the self-test's folder on sys.path, its modules afresh
    return importlib.import_module('test_all_tools.lifecycle.samples')


# in the format macOS's sample writes, its heaviest calls first (measured 2026-11-11, a Designer stuck in its shutdown);
# the calls shortened, and the lighter sibling made up
SAMPLE = """Call graph:
    820 Thread_1140019   DispatchQueue_1: com.apple.main-thread  (serial)
    + 820 start  (in dyld) + 6992  [0x18c8384e4]
    +   820 main  (in Adobe Substance 3D Designer) + 12432  [0x1044142e0]
    +     820 (anonymous namespace)::destroyApplication(Pfx::Applications::Designer::Application*&, std::unique_ptr<Alg::CrashReporter>*)  (in Adobe Substance 3D Designer) + 1312  [0x104411a20]
    +       820 QCoreApplication::~QCoreApplication()  (in QtCore) + 128  [0x11996049c]
    +         820 QThreadPool::waitForDone(QDeadlineTimer)  (in QtCore) + 44  [0x119af21cc]
    +           500 QWaitCondition::wait(QMutex*, QDeadlineTimer)  (in QtCore) + 108  [0x119af6ad4]
    +           ! 500 __psynch_cvwait  (in libsystem_kernel.dylib) + 8  [0x18cbc350c]
    +           320 QThreadPoolPrivate::reset()  (in QtCore) + 10  [0x119af1000]
    820 Thread_1140040
    + 820 start_wqthread  (in libsystem_pthread.dylib) + 8  [0x18cbfec10]
"""


def _main_thread_sample(*calls: str) -> str:
    """A sample in macOS's format whose main thread holds `calls`, each called by the one before it."""
    lines = ['Call graph:', '    820 Thread_1   DispatchQueue_1: com.apple.main-thread  (serial)']
    lines += [
        '    +%s820 %s  (in Designer) + 8  [0x1000]' % (' ' * (1 + 2 * depth), call) for depth, call in enumerate(calls)
    ]
    return '\n'.join(lines) + '\n'


def test_the_main_threads_heaviest_calls_are_read_from_a_sample() -> None:
    # REVIEW.md TST-310: a failing check says where the main thread waited, as the pool may delete the file
    samples = _samples()
    assert samples.main_thread(SAMPLE, 3) == (
        'QWaitCondition::wait < QThreadPool::waitForDone < QCoreApplication::~QCoreApplication'
    ), 'its heaviest path, deepest first, not the lighter sibling, the next thread, system calls or arguments'
    assert samples.main_thread('Call graph:\n    820 Thread_1\n') == 'no main thread in the sample'


# Designer's main thread at its shutdown's steps before the pool's wait, all inside destroyApplication (measured
# 2026-11-16, lifecycle/hold_thread_pool held, sampled from the windows' close on), its frames between shortened
TEARDOWN = '(anonymous namespace)::destroyApplication(Pfx::Applications::Designer::Application*&)'
# stopping Adobe's sign-in (REVIEW.md TST-400: seen in a full run)
SIGNING_OUT = _main_thread_sample(
    'start',
    'main',
    TEARDOWN,
    'Pfx::Editor::Components::Ngl::Component::~Component()',
    'adobe::ngl::internal::NglSSOHandler::Stop()',
)
# a file watcher's wait for macOS's file events, as the render engine is deleted (REVIEW.md TST-400): the six deepest
# calls as the 2026-11-16 full run's check printed them, their callers as the probe measured them
WATCHING_FILES = _main_thread_sample(
    'start',
    'main',
    TEARDOWN,
    'Alg::Core::ComponentsTable::clear(QRecursiveMutex&)',
    'Pfx::DataRendering::EngineComponent::~EngineComponent()',
    'QCoreApplication::processEvents(QFlags<QEventLoop::ProcessEventsFlag>, int)',
    'QObject::event(QEvent*)',
    'QFileSystemWatcher::addPath(QString const&)',
    'QFileSystemWatcher::addPaths(QList<QString> const&)',
    'QFseventsFileSystemWatcherEngine::addPaths(QList<QString> const&, QList<QString>*, QList<QString>*)',
    'FSEventStreamFlushSync',
    'f2d_flush_rpc',
)
RUNNING = _main_thread_sample(
    'start', 'main', 'QApplication::exec()', 'QEventLoop::exec(QFlags<QEventLoop::ProcessEventsFlag>)', '_CFRunLoopRun'
)


@pytest.mark.parametrize(
    'stacks, shutting_down',
    [(SAMPLE, True), (SIGNING_OUT, True), (WATCHING_FILES, True), (RUNNING, False), ('', False)],
    ids=['the pool', 'the sign-in stop', 'a file watcher', 'running', 'no sample'],
)
def test_a_sample_shows_designer_anywhere_in_its_teardown(stacks: str, shutting_down: bool) -> None:
    # REVIEW.md TST-400: any of the teardown's steps, not only the waits seen so far, can hold the main thread when sampled
    assert _samples().in_shutdown(stacks) is shutting_down


def test_the_file_watchers_sample_reads_as_the_full_run_printed_it() -> None:
    # REVIEW.md TST-400: the fixture is the sample that failed, not one made up to pass
    assert _samples().main_thread(WATCHING_FILES) == (
        'f2d_flush_rpc < FSEventStreamFlushSync < QFseventsFileSystemWatcherEngine::addPaths'
        ' < QFileSystemWatcher::addPaths < QFileSystemWatcher::addPath < QObject::event'
    )


def test_a_result_naming_a_sample_gives_its_text_and_where_the_main_thread_was(tmp_path: Path) -> None:
    samples = _samples()
    path = tmp_path / 'forced_quit_11.sample.txt'
    path.write_text(SAMPLE)
    result = 'Designer quit after 9s (forced; its log could not be read). %s %s' % (
        project_constants.QUIT_SAMPLED,
        path,
    )
    stacks, detail = samples.sampled(result)
    # its calls only: check() prints 150 characters, which they fill (REVIEW.md TST-312)
    assert stacks == SAMPLE and detail == samples.main_thread(SAMPLE)
    path.unlink()
    assert samples.sampled(result) == ('', result), 'gone: the result itself'
    assert samples.sampled('Designer quit after 2s.') == ('', 'Designer quit after 2s.')


# names as macOS's sample writes them, made up: an AppKit category method, a lambda's call operator, a const member of a
# template, the C library's exit; under exit, a kernel wait, then a lighter callee of exit after it
CALLS = """    820 Thread_1   DispatchQueue_1: com.apple.main-thread  (serial)
    + 820 start  (in dyld) + 1  [0x1]
    +   820 -[NSApplication(NSAppleEventHandling) _handleAEQuit]  (in AppKit) + 2  [0x2]
    +     820 std::__1::__function::__func<Foo::bar()::$_0, void ()>::operator()()  (in Designer) + 3  [0x3]
    +       820 Foo<decltype(x)>::f() const  (in Designer) + 4  [0x4]
    +         820 exit  (in libsystem_c.dylib) + 5  [0x5]
    +           600 __psynch_cvwait  (in libsystem_kernel.dylib) + 6  [0x6]
    +           220 __cxa_finalize_ranges  (in libsystem_c.dylib) + 7  [0x7]
"""


def test_the_main_threads_calls_keep_their_names_and_the_c_librarys() -> None:
    # REVIEW.md TST-311: only a call's trailing arguments go, an Objective-C method whole; the C library's calls (exit
    # handlers) stay, the kernel's waits go; a lighter callee after the path's last call isn't on it
    assert _samples().main_thread(CALLS, 10) == (
        'exit < Foo<decltype(x)>::f < std::__1::__function::__func<Foo::bar()::$_0, void ()>::operator() < '
        '-[NSApplication(NSAppleEventHandling) _handleAEQuit] < start'
    )


def test_the_second_client_looks_at_the_bridge_off_the_event_loop() -> None:
    # REVIEW.md TST-426: job_running, a blocking socket call, ran on the asyncio loop sending the job's own call
    import inspect

    common = importlib.import_module('test_all_tools.common')
    assert 'await until_job_running(limit)' in inspect.getsource(common.cancel_from_second_client)
    assert 'await asyncio.to_thread(job_running, token)' in inspect.getsource(common.until_job_running)


def test_the_modal_dialog_poll_stops_once_the_dialog_is_seen() -> None:
    # REVIEW.md TST-426: it slept POLL_S after finding the dialog too, a margin after the state
    with open(os.path.join(SELFTEST_DIR, 'lifecycle', 'checks.py'), encoding='utf-8') as f:
        text = f.read()
    poll = text[text.index("deadline, modal = time.monotonic() + 30, ''") :][:600]
    assert re.search(r"if 'MODAL=QMessageBox' in modal:\s+break", poll), poll
    assert 'await asyncio.sleep(POLL_S)' in poll and 'time.sleep(POLL_S)' not in poll


def test_the_launch_check_judges_designer_started_off_screen() -> None:
    # REVIEW.md SRV-152: a launch starts Designer hidden, so no window of its is on screen to be behind anything
    with open(os.path.join(SELFTEST_DIR, 'lifecycle', 'checks.py'), encoding='utf-8') as f:
        text = f.read()
    assert 'window_server.stayed_off_screen(front.samples, second)' in text
    assert 'stayed_behind(front.samples, second' not in text
