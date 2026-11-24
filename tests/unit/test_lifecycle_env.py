"""launch/quit paths that can't be produced safely with a real Designer, designer_status,
environment-variable overrides (README, Configuration), log filtering and the missing-tools message."""

import contextlib
import errno
import io
import json
import os
import plistlib
import re
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace
from typing import IO, NoReturn, Protocol, TypedDict, Unpack

import pytest
from fake_defaults import FakeDefaults, lock_held

import designer_preferences
import project_constants
import server_tools
from conftest import (
    REAL_BIND_ERROR,
    REAL_DESIGNER_PIDS,
    REAL_DESIGNER_RUNNING,
    REAL_EXIT_WATCH,
    REAL_FOUND_LAUNCHED,
    REAL_OWN_HOME,
    REAL_OWN_TEMP,
    REAL_PLUGIN_PATHS,
    REAL_PROCESS_START,
    REAL_SAMPLE,
    REAL_SHORT_TEMP,
    ROOT,
    DumpOptions,
    RunOptions,
    fake_bridge,
    patch_server,
    server,
)
from designer_preferences import Plist
from project_constants import PLUGIN, PLUGIN_PACKAGE_DIR, Reply, Request, read_agent_record

# The tests that depend on the system say so, and skip elsewhere (REVIEW.md TST-508; test_windows_simulation.py)
# a test setting the platform to macOS or Linux: that platform's code takes fcntl and os.getuid
_SETS_UNIX = pytest.mark.skipif(
    sys.platform == 'win32', reason='sets the platform to macOS or Linux, whose code needs fcntl and os.getuid'
)
_RECORDED = pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded there')
# each platform, the ones whose code a Windows host can't run marked (REVIEW.md TST-510)
_EACH_PLATFORM = [pytest.param('darwin', marks=_SETS_UNIX), pytest.param('linux', marks=_SETS_UNIX), 'win32']
# a test ending an agent's Designer it recorded: _force_end takes signal.SIGKILL (REVIEW.md TST-509)
_FORCE_ENDS = pytest.mark.skipif(
    sys.platform == 'win32', reason='ends a recorded Designer with signal.SIGKILL; Windows records none, and lacks it'
)


class _Send(Protocol):
    """core._send's signature, which the fakes of _send below have."""

    def __call__(self, request: Request, wait: float, port: int | None = None) -> Reply: ...


def _no_bridge(request: Request, wait: float, port: int | None = None) -> NoReturn:
    raise server.ToolError('Designer is not reachable.')


class _FakeProcess:
    """What subprocess.Popen returns, as launch_designer uses it."""

    def __init__(self, pid: int) -> None:
        self.pid = pid

    def wait(self, timeout: float | None = None) -> int:
        return 0


class _PopenArgs(TypedDict, total=False):
    """The keyword arguments launch_designer passes to subprocess.Popen (lifecycle._opened and _started)."""

    env: dict[str, str]
    stdin: int
    stdout: int
    stderr: int | io.BufferedRandom  # DEVNULL, or the temporary file `open`'s errors go to
    cwd: str
    start_new_session: bool
    creationflags: int


class _Popen(Protocol):
    """A fake subprocess.Popen, called as launch_designer calls it."""

    def __call__(self, cmd: list[str], **kw: Unpack[_PopenArgs]) -> _FakeProcess: ...


def _popen(
    started: list[list[str]],
    entry: Callable[[list[str]], list[str]] = lambda cmd: cmd,
    pid: int = 77,
    processes: '_Processes | None' = None,
) -> _Popen:
    """A fake subprocess.Popen: each start appends entry(cmd) to started, its keyword arguments to started_with, and
    its process ID to processes.pids when `processes` is given."""

    def popen(cmd: list[str], **kw: Unpack[_PopenArgs]) -> _FakeProcess:
        started.append(entry(cmd))
        _started_with.append(kw)
        if processes is not None:
            processes.pids.append(pid)
        return _FakeProcess(pid)

    return popen


_started_with: list[_PopenArgs] = []


@pytest.fixture(autouse=True)
def _no_starts_left() -> Iterator[None]:
    _started_with.clear()
    yield
    _started_with.clear()


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    # a sleep passes at once on a clock of the test's own, so a wait to a deadline ends as it would
    clock = [time.monotonic()]
    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(time, 'sleep', lambda s: clock.__setitem__(0, clock[0] + s))


def test_launch_reports_missing_app(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_designer_running', lambda: False)
    monkeypatch.setenv('SD_DESIGNER_APP', '/no/such/Designer.app')
    with pytest.raises(server.ToolError, match='Designer not found'):
        server.launch_designer()


def test_launch_times_out_when_the_bridge_never_answers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    started: list[list[str]] = []
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_designer_running', lambda: False)
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))  # exists
    monkeypatch.setattr(subprocess, 'Popen', _popen(started))
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError, match='did not answer within 30s') as raised:
        server.launch_designer(wait_s=30)
    assert started, 'Designer was never started'
    # REVIEW.md SRV-80: a retry with the same wait may never finish, and a larger one works
    assert 'If it needs longer, call this with a larger wait_s' in str(raised.value)


def test_launch_waits_for_a_running_designer_instead_of_starting_another(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-10: a running Designer whose bridge doesn't answer (still starting, a dialog,
    # the plugin failed to load) was launched again: a second instance on Windows
    started: list[list[str]] = []
    home: list[str] = []
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_designer_running', lambda: True)
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', _popen(started))

    def home_screen(code: str) -> str:
        home.append(code)
        return ''

    fake_bridge(monkeypatch, home_screen)
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError) as error:
        server.launch_designer(wait_s=30)
    assert not started, 'started a second Designer'
    assert 'already running' in str(error.value) and 'did not answer within 30s' in str(error.value)
    # once it answers: reported as already running, and its Home screen is left alone
    answers: Iterator[Exception | Reply] = iter([server.ToolError('not yet'), {'ok': True, 'output': 'idle'}])

    def bridge_comes_up(request: Request, wait: float, port: int | None = None) -> Reply:
        a = next(answers)
        if isinstance(a, Exception):
            raise a
        return a

    patch_server(monkeypatch, '_send', bridge_comes_up)
    monkeypatch.setattr(time, 'time', lambda: 0)
    assert server.launch_designer(wait_s=30).startswith('Designer already running')
    assert not started and not home


def test_a_closed_designer_is_left_for_the_user_to_open(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md SRV-81: it told agents to start Designer, and one an agent starts is disposable, whoever then works in it
    token = tmp_path / 'token'
    token.write_text('not the real one')
    patch_server(monkeypatch, 'TOKEN_FILE', str(token))

    def refused(address: tuple[str, int], timeout: float) -> NoReturn:
        raise ConnectionRefusedError

    monkeypatch.setattr(socket, 'create_connection', refused)
    with pytest.raises(server.ToolError) as raised:
        server._send({'cmd': 'status'}, wait=1)
    message = str(raised.value)
    assert 'Designer is not reachable: if it is closed, ask the user to open it' in message
    assert 'Start Designer' not in message


def test_quit_when_not_running(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_designer_running', lambda: False)
    assert server.quit_designer() == 'Designer is not running.'


def _refused(request: Request, wait: float, port: int | None = None) -> Reply:
    # what the plugin answers a client whose token it rejects (README Troubleshooting: a plugin and
    # server from different versions)
    return {'ok': False, 'output': '', 'error': 'invalid token'}


@pytest.mark.parametrize(
    'call',
    [
        lambda: server.designer_status(),
        lambda: server.launch_designer(wait_s=30),
        lambda: server.cancel_designer_job(),
    ],
    ids=['designer_status', 'launch_designer', 'cancel_designer_job'],
)
def test_a_refused_control_request_is_reported_as_an_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, call: Callable[[], str]
) -> None:
    # REVIEW.md SRV-33: the reply's output was read without checking ok, so a refusal read as an
    # answer (a running job, "already running: ", an empty cancel); launch_designer must not start
    # or wait for another Designer either
    started: list[list[str]] = []
    patch_server(monkeypatch, '_send', _refused)
    patch_server(monkeypatch, '_designer_running', lambda: True)
    fake_bridge(monkeypatch, lambda code: 'closing Designer')
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', _popen(started))
    with pytest.raises(server.ToolError, match='invalid token'):
        call()
    assert not started


def _import_server_with(env: dict[str, str]) -> list[str]:
    code = (
        'import sys; sys.path.insert(0, %r); import server; '
        'print(server.SNAPSHOT_DIR); print(server.PORT); print(server.SBSRENDER)'
    ) % os.path.join(ROOT, 'mcp_server')
    out = subprocess.run([sys.executable, '-c', code], env={**os.environ, **env}, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout.splitlines()


def test_environment_overrides(tmp_path: Path) -> None:
    fake = tmp_path / ('sbsrender.exe' if sys.platform == 'win32' else 'sbsrender')
    fake.write_text('')
    snap_dir, port, render = _import_server_with(
        {'SD_SNAPSHOT_DIR': str(tmp_path / 'snaps'), 'SD_BRIDGE_PORT': '9999', 'SD_DESIGNER_BIN_DIR': str(tmp_path)}
    )
    assert (snap_dir, port, render) == (str(tmp_path / 'snaps'), '9999', str(fake))


def test_every_component_reads_the_port_variable() -> None:
    # a port change must be made for the plugin and the server alike (README, Configuration)
    for path in (
        os.path.join(PLUGIN_PACKAGE_DIR, '__init__.py'),
        os.path.join(ROOT, 'mcp_server', 'server_tools', 'core.py'),
        os.path.join(ROOT, 'client', 'sd_run.py'),
    ):
        with open(path) as f:
            assert "os.environ.get('SD_BRIDGE_PORT'" in f.read(), path


LOG = (
    """old run [ERROR] stale error
[INFO] Python SDK Version 1.0
[INFO] [%s] v2 listening on 127.0.0.1:9877
[WARNING] something odd
[ERROR] Traceback (most recent call last)
[INFO] ready"""
    % PLUGIN
)


def test_read_log_from_sd_designer_log(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log = tmp_path / 'log.txt'
    log.write_text(LOG)
    monkeypatch.setenv('SD_DESIGNER_LOG', str(log))

    def body(t: str) -> list[str]:
        return t.splitlines()[1:]

    assert body(server.read_designer_log()) == LOG.splitlines()[1:]  # since the last start
    assert body(server.read_designer_log(since_last_start=False)) == LOG.splitlines()
    assert body(server.read_designer_log(errors_only=True)) == [
        '[WARNING] something odd',
        '[ERROR] Traceback (most recent call last)',
    ]
    assert body(server.read_designer_log(contains=PLUGIN.upper())) == [
        '[INFO] [%s] v2 listening on 127.0.0.1:9877' % PLUGIN
    ]
    assert server.read_designer_log(lines=1).startswith('%s (5 matching lines, showing 1)' % log)
    monkeypatch.setenv('SD_DESIGNER_LOG', str(tmp_path / 'missing.txt'))
    with pytest.raises(server.ToolError, match='log not found'):
        server.read_designer_log()


def test_render_tools_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_server(monkeypatch, 'SBSRENDER', None)
    calls: tuple[Callable[[], str], ...] = (
        lambda: server_tools.output.render_sbs('x.sbs', '/tmp/out'),
        lambda: server_tools.output.sbsar_info('x.sbs'),
    )
    for call in calls:
        with pytest.raises(server.ToolError, match='SD_DESIGNER_BIN_DIR'):
            call()


def test_scripts_and_tool_output_are_read_as_utf8_whatever_the_locale(tmp_path: Path) -> None:
    # REVIEW.md SRV-11: run_designer_script read the file in the locale's encoding (cp1252 on
    # many Windows machines), and _run_tool decoded sbsrender's output the same way. A Latin-1
    # locale with UTF-8 mode off stands in for cp1252 here.
    script = tmp_path / 's.py'
    script.write_text("print('→ é ✓')\n", encoding='utf-8')
    probe = (
        dedent("""\
            import sys; sys.path.insert(0, %r); sys.path.insert(0, %r)
            import server, server_tools.scripting
            server._session.update(guide_read=True, scripting_read=True)  # or the tool refuses
            # where the tool looks it up
            server_tools.scripting._bridge = lambda code, path=None, timeout=None: code
            sent = server.run_designer_script(%r)
            print('SCRIPT_OK' if "print('→ é ✓')" in sent else 'SCRIPT_BAD')
            r = server._run_tool([sys.executable, '-c', "import sys; sys.stdout.buffer.write('→ ✓'.encode())"], 30)
            print('TOOL_OK' if r.stdout == '→ ✓' else 'TOOL_BAD %%r' %% r.stdout)
        """)
    ) % (os.path.join(ROOT, 'mcp_server'), ROOT, str(script))
    env = dict(os.environ, LC_ALL='en_US.ISO8859-1', PYTHONIOENCODING='utf-8')
    env.pop('PYTHONUTF8', None)
    out = subprocess.run(
        [sys.executable, '-X', 'utf8=0', '-c', probe],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env,
        cwd=str(tmp_path),
    )
    assert 'SCRIPT_OK' in out.stdout and 'TOOL_OK' in out.stdout, out.stdout + out.stderr


def test_launch_starts_designer_when_the_running_one_exits_during_the_wait(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-15: the process was looked for once; when that Designer (shutting down, or hung
    # after a crash) went away during the wait, nothing was started and the error still said
    # "already running"
    started: list[list[str]] = []
    processes = iter([True, True, False])  # there at first, then gone
    patch_server(monkeypatch, '_designer_running', lambda: next(processes, False))
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', _popen(started))

    def bridge(request: Request, wait: float, port: int | None = None) -> Reply:
        if not started:
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    patch_server(monkeypatch, '_send', bridge)
    fake_bridge(monkeypatch, lambda code: '')
    clock = iter(range(0, 1000, 5))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    assert server.launch_designer(wait_s=60).startswith('Designer started in')
    assert len(started) == 1


def test_a_restarted_designer_gets_the_whole_wait(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-19: after the old process went away late in the wait, the new Designer got
    # only what was left of wait_s, and "started in" counted the wait for the old one
    started: list[int] = []  # the clock's time at each start
    now = [0]
    processes = iter([True] + [True] * 33 + [False])  # the old one goes away at ~175 s of 180 (SRV-21)
    patch_server(monkeypatch, '_designer_running', lambda: next(processes, False))
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))

    def stamped(cmd: list[str], **kw: Unpack[_PopenArgs]) -> _FakeProcess:
        started.append(now[0])
        _started_with.append(kw)
        return _FakeProcess(77)

    monkeypatch.setattr(subprocess, 'Popen', stamped)

    def clock() -> int:
        now[0] += 5
        return now[0]

    monkeypatch.setattr(time, 'time', clock)

    def bridge(request: Request, wait: float, port: int | None = None) -> Reply:
        if not started or now[0] < started[0] + 60:  # the new one needs 60 s to come up
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    patch_server(monkeypatch, '_send', bridge)
    fake_bridge(monkeypatch, lambda code: '')
    text = server.launch_designer(wait_s=180)
    match = re.search(r'started in (\d+)s', text)
    assert match is not None, text
    seconds = int(match.group(1))
    assert seconds <= 90, text  # timed from the restart, not the first call


def test_designer_status_reports_the_servers_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-13: the server's own Python and library versions
    import platform

    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': 'bridge idle'})
    fake_bridge(monkeypatch, lambda code: 'Designer 16.0.7')
    text = server.designer_status()
    assert 'MCP server: Python %s' % platform.python_version() in text
    assert 'mcp ' in text and 'pillow ' in text and 'numpy ' in text


def test_designer_status_answers_while_a_job_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-22: the package listing queued behind the running job, so the status call
    # waited up to ~31 minutes although the plugin knew at once that it was busy
    patch_server(
        monkeypatch,
        '_send',
        lambda request, wait, port=None: {'ok': True, 'output': '%s v3: running for 412.0s, 0 queued' % server.PLUGIN},
    )
    queued: list[str] = []

    def package_list(code: str) -> str:
        queued.append(code)
        return 'packages'

    fake_bridge(monkeypatch, package_list)
    text = server.designer_status()
    assert 'running for 412.0s' in text and not queued and 'package list' in text


# --- launch_designer's states (ROADMAP item 25), one test per row:
#
# | Process | Bridge | launch_designer does | Test |
# |---|---|---|---|
# | not running | - | starts it, remembers it, closes Home | test_launch_state_not_running |
# | not running | never answers | says so after wait_s | test_launch_times_out_when_the_bridge_never_answers |
# | running | answers | says it runs, starts nothing | test_launch_state_answering |
# | the user's | answers later | waits, starts nothing | test_launch_waits_for_a_running_designer_instead_of_starting_another |
# | the user's | never answers | ends nothing, gives the ID and the command | test_launch_state_users_not_answering |
# | exits during the wait | - | starts one, with the whole wait | test_launch_starts_designer_when_the_running_one_exits_during_the_wait, test_a_restarted_designer_gets_the_whole_wait |
# | two of the user's | never answers | ends neither, gives both IDs | test_launch_state_second_instance |
# | an agent's, past the startup limit | not answering | ends it, starts one | test_launch_state_agents_not_answering |
# | an agent's, younger | answers later | waits, ends nothing | test_launch_state_agents_still_starting |
# | an agent's, younger | never answers | ends nothing, says a later call will | test_launch_state_agents_too_slow_for_this_wait |
# | an agent's, passing the limit during the wait | not answering | ends it, starts one | test_launch_ends_an_agents_passing_the_limit |
# | an agent's, past the limit, can't be ended | not answering | stops, gives the command | test_launch_stops_at_an_agents_it_cant_end |
#
# Who started it, and closing it: the tests after those.


class _Processes:
    """Designer's processes, with their start times, and the signals they got."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *pids: int, ends_on: int = signal.SIGTERM) -> None:
        self.pids = list(pids)
        self.signals: list[tuple[int, int]] = []
        self.ends_on = ends_on
        patch_server(monkeypatch, '_designer_pids', lambda: list(self.pids))
        patch_server(monkeypatch, '_designer_running', lambda: bool(self.pids))
        patch_server(monkeypatch, '_process_start', lambda pid: 'started %d' % pid if pid in self.pids else None)
        monkeypatch.setattr(os, 'kill', self.kill)

    def kill(self, pid: int, sig: int) -> None:
        self.signals.append((pid, sig))
        if sig == self.ends_on:
            self.pids.remove(pid)


def _an_agent_started(
    pid: int, start: str | None = None, age: float = 0, port: int | None = None, home: str | None = None
) -> None:
    """Recorded `age` seconds ago, on `port` (the server's by default), with `home`: launch_designer waits for one
    younger than STARTUP_LIMIT."""
    record = server.agent_designer_file(server.PORT if port is None else port)
    Path(record).write_text(json.dumps({'pid': pid, 'start': start or 'started %d' % pid, 'home': home}))
    os.utime(record, (time.time() - age, time.time() - age))


def _record_reads(monkeypatch: pytest.MonkeyPatch, then_gone: bool = False) -> list[int]:
    """The ports whose record is read from now on, in order (ROADMAP item 106). With `then_gone`, each record is removed
    once read, as another server's quit removes it."""
    read_record: Callable[[int], tuple[bytes, float] | None] = server._read_record
    reads: list[int] = []

    def read(port: int) -> tuple[bytes, float] | None:
        reads.append(port)
        found = read_record(port)
        if then_gone:
            Path(server.agent_designer_file(port)).unlink(missing_ok=True)
        return found

    patch_server(monkeypatch, '_read_record', read)
    return reads


def _launch_fakes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[list[str]]:
    started: list[list[str]] = []
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', _popen(started))
    fake_bridge(monkeypatch, lambda code: '')
    return started


def _answers_once_started(started: list[list[str]]) -> _Send:
    def bridge(request: Request, wait: float, port: int | None = None) -> Reply:
        if not started:
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    return bridge


@_RECORDED
def test_launch_state_not_running(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    home: list[str] = []
    processes = _Processes(monkeypatch)

    def bridge(code: str) -> str:
        home.append(code)
        return ''

    monkeypatch.setattr(subprocess, 'Popen', _popen(started, processes=processes))
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    fake_bridge(monkeypatch, bridge)
    assert server.launch_designer(wait_s=30).startswith('Designer started in')
    assert len(started) == 1 and home and 'leave_home_screen' in home[0]
    assert server._agent_designer(server.PORT) == 77, 'it remembers the one it started'


@pytest.mark.parametrize(
    'bundle, give_back',
    [(True, 'give_back_activation(started_hidden=True)'), (False, 'give_back_activation()')],
    ids=['an app bundle, opened hidden', 'a binary'],
)
@_SETS_UNIX
def test_a_designer_started_gives_the_keyboard_back_once_its_home_screen_is_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, bundle: bool, give_back: str
) -> None:
    # REVIEW.md SRV-148: it became the active app as it started, the user's keyboard in it. SRV-161: one opened hidden
    # is left hidden, as activating it unhides it
    monkeypatch.setattr(sys, 'platform', 'darwin')
    started = _launch_fakes(monkeypatch, tmp_path)
    if not bundle:
        binary = tmp_path / 'Designer'
        binary.write_text('')
        monkeypatch.setenv('SD_DESIGNER_APP', str(binary))
    calls: list[str] = []
    processes = _Processes(monkeypatch)

    said = {
        'leave_home_screen()': 'closed the Home screen',
        give_back: 'gave the keyboard back to the app in front before it',
    }

    def bridge(code: str) -> str:
        call = code.strip().splitlines()[-1]  # the helpers' source comes first
        calls.append(call)
        return said[call] + '\n'

    monkeypatch.setattr(subprocess, 'Popen', _popen(started, processes=processes))
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    fake_bridge(monkeypatch, bridge)
    result = server.launch_designer(wait_s=30)
    assert calls == ['leave_home_screen()', give_back]
    assert '(closed the Home screen; gave the keyboard back to the app in front before it)' in result


@_RECORDED
def test_a_user_opening_one_at_the_same_moment_doesnt_confuse_the_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # the record is the process it started itself, so another appearing at the same moment can't be taken for it
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch)

    def begin(cmd: list[str], **kw: Unpack[_PopenArgs]) -> _FakeProcess:
        started.append(cmd)
        processes.pids.extend([78, 77])
        return _FakeProcess(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    server.launch_designer(wait_s=30)
    assert server._agent_designer(server.PORT) == 77


def test_a_launch_timing_out_whose_processes_cant_be_listed_still_says_what_to_do(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-171: the timeout's advice lists Designer's processes for their IDs; that listing failing replaced the
    # whole message, the bridge not answering and what to ask the user, with the listing's error
    started = _launch_fakes(monkeypatch, tmp_path)
    _Processes(monkeypatch, 11)
    patch_server(monkeypatch, '_send', _no_bridge)
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    listed: Callable[[int, dict[int, int] | None], tuple[list[int], list[int]]] = server._sorted_out

    def sorted_out(port: int, agents: dict[int, int] | None = None) -> tuple[list[int], list[int]]:
        if sys._getframe(1).f_code.co_name == '_how_to_end':
            raise server._NoListing("Designer's processes couldn't be listed (pgrep exit code 3: fork failed)")
        return listed(port, agents)

    patch_server(monkeypatch, '_sorted_out', sorted_out)
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    message = str(raised.value)
    assert 'did not answer within 30s' in message and 'ask the user to end it in Activity Monitor' in message, message
    assert 'If they are open, ask the user to save and close it' in message and not started, message


def test_launch_state_answering(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': 'idle'})
    assert server.launch_designer().startswith('Designer already running')
    assert not started


def test_launch_state_users_not_answering(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    patch_server(monkeypatch, '_send', _no_bridge)
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    message = str(raised.value)
    assert 'did not answer within 30s' in message and 'kill 11' in message and 'kill -9 11' in message
    assert 'Activity Monitor' in message and not processes.signals and not started
    # REVIEW.md SRV-76: it may be working normally, with unsaved work
    assert message.index('If its windows have closed') < message.index('kill 11')
    assert 'If they are open, ask the user to save and close it' in message


def test_launch_state_second_instance(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11, 12)
    patch_server(monkeypatch, '_send', _no_bridge)
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    assert '11' in str(raised.value) and '12' in str(raised.value) and 'which' in str(raised.value)
    assert not processes.signals and not started


@_RECORDED
def test_launch_state_agents_not_answering(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    # REVIEW.md HLP-82: an agent's Designer is disposable, so it isn't waited for
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1)

    monkeypatch.setattr(subprocess, 'Popen', _popen(started, processes=processes))
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    text = server.launch_designer(wait_s=30)
    assert processes.signals == [(11, signal.SIGTERM)] and len(started) == 1
    assert 'Ended' in text and 'Designer started in' in text and server._agent_designer(server.PORT) == 77


def test_launch_state_agents_still_starting(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    # REVIEW.md SRV-75: a retry, or a second session, mustn't kill a Designer that is only slow to start
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    calls: list[int] = []

    def answers_on_the_third(request: Request, wait: float, port: int | None = None) -> Reply:
        calls.append(1)
        if len(calls) < 3:
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    patch_server(monkeypatch, '_send', answers_on_the_third)
    assert server.launch_designer(wait_s=30).startswith('Designer already running')
    assert not processes.signals and not started and server._agent_designer(server.PORT) == 11
    assert '%d s after it started' % server.STARTUP_LIMIT in server.launch_designer.__doc__


def test_launch_state_agents_too_slow_for_this_wait(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    patch_server(monkeypatch, '_send', _no_bridge)
    now = time.time()
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(time, 'time', lambda: now + next(clock))
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    message = str(raised.value)
    assert 'calling this again' in message and 'kill' not in message and 'Activity Monitor' not in message
    assert not processes.signals and not started


@_RECORDED
def test_launch_ends_an_agents_passing_the_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, age=server.STARTUP_LIMIT - 20)

    monkeypatch.setattr(subprocess, 'Popen', _popen(started, processes=processes))
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    now = time.time()
    clock = iter(range(0, 10000, 10))
    monkeypatch.setattr(time, 'time', lambda: now + next(clock))
    text = server.launch_designer(wait_s=1000)
    assert processes.signals == [(11, signal.SIGTERM)] and len(started) == 1
    assert 'Ended' in text and 'Designer started in' in text and server._agent_designer(server.PORT) == 77


@_FORCE_ENDS
def test_launch_stops_at_an_agents_it_cant_end(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    # REVIEW.md SRV-79: it said a later call would end it, right after failing to, and tried again at every poll
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11, ends_on=-1)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1)
    patch_server(monkeypatch, '_send', _no_bridge)
    with pytest.raises(server.ToolError, match=r'could not be ended; ask the user to run `kill -9 11`'):
        server.launch_designer(wait_s=30)
    assert processes.signals == [(11, signal.SIGTERM), (11, signal.SIGKILL)] and not started


@_FORCE_ENDS
def test_launch_says_it_ended_one_even_if_the_new_one_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    _launch_fakes(monkeypatch, tmp_path)
    _Processes(monkeypatch, 11)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1)
    patch_server(monkeypatch, '_send', _no_bridge)
    monkeypatch.setenv('SD_DESIGNER_APP', '/no/such/Designer.app')
    with pytest.raises(server.ToolError, match=r'(?s)Ended .*Designer not found'):
        server.launch_designer(wait_s=30)


# --- crash uploads: off in the Designer it starts (DECISIONS.md, the user's choice; server_tools/lifecycle.py)

# homes of their own only there: elsewhere these settings would be the user's (REVIEW.md TST-343)
_HOMES_OF_THEIR_OWN = pytest.mark.skipif(sys.platform == 'win32', reason='no home of its own there')
CRASHPAD_SETTINGS = struct.pack('<IIIIq16s', 0x43506473, 1, 1, 0, 1794501016, b'client id 16 byt')  # uploads on


def _crashpad_settings(home: Path, content: bytes | None = CRASHPAD_SETTINGS) -> Path:
    """The Crashpad settings of the Designer started with `home`, as Designer leaves them once started (uploads on)."""
    path = Path(server._designer_data_dir(str(home))) / 'Sentry-Crashpad' / 'settings.dat'
    # Windows' data folder ignores the home: the user's real one, never written here (REVIEW.md TST-343)
    assert path.is_relative_to(home), path
    path.parent.mkdir(parents=True)
    if content is not None:
        path.write_bytes(content)
    return path


def test_crash_settings_are_planted_only_under_the_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-343: off macOS the data folder ignores the home: the helper wrote into the user's real one there
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'appdata'))
    with pytest.raises(AssertionError):
        _crashpad_settings(tmp_path / 'home')
    assert not (tmp_path / 'appdata').exists()


def _launch_with_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    home: Path | None,
    home_screen: Exception | None = None,
    refuses: bool = False,
    at_start: Callable[[], None] = lambda: None,
) -> str:
    """launch_designer starting one with `home` (None: none of its own, as off macOS), which then answers (with a
    refusal when `refuses`); leaving its Home screen raises `home_screen` when given; `at_start` runs as its process
    starts."""
    started = _launch_fakes(monkeypatch, tmp_path)
    if home_screen is not None:

        def fails(code: str) -> str:
            raise home_screen

        fake_bridge(monkeypatch, fails)
    processes = _Processes(monkeypatch)

    def begin(cmd: list[str], **kw: Unpack[_PopenArgs]) -> _FakeProcess:
        at_start()
        started.append(cmd)
        processes.pids.append(77)
        return _FakeProcess(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_own_home', lambda port: None if home is None else str(home))
    answers = _answers_once_started(started)
    patch_server(monkeypatch, '_send', _refusing(answers) if refuses else answers)
    said = server_tools.lifecycle.launch_designer(wait_s=30)
    return said


def _refusing(answers: _Send) -> _Send:
    """A plugin that refuses once it answers, as with another token (core._control: _Refused)."""

    def bridge(request: Request, wait: float, port: int | None = None) -> Reply:
        answers(request, wait)  # not reachable until then
        return {'ok': False, 'error': 'invalid token'}

    return bridge


@_HOMES_OF_THEIR_OWN
def test_launch_turns_crash_uploads_off_in_the_designer_it_starts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    settings = _crashpad_settings(tmp_path / 'home')
    said = _launch_with_home(monkeypatch, tmp_path, tmp_path / 'home')
    assert said.startswith('Designer started in') and 'upload' not in said
    after = settings.read_bytes()
    assert struct.unpack_from('<I', after, 8)[0] == 0, 'uploads off'
    assert after[:8] + after[12:] == CRASHPAD_SETTINGS[:8] + CRASHPAD_SETTINGS[12:], 'the rest as Crashpad wrote it'


@_HOMES_OF_THEIR_OWN
@pytest.mark.parametrize(
    'content, why',
    [
        (None, 'No such file'),
        (b'not crashpad settings, 40 bytes long, at all', "isn't Crashpad's settings"),
        # another version may have another layout: its bit 0 at offset 8 needn't be uploads (REVIEW.md SRV-122)
        (struct.pack('<IIIIq16s', 0x43506473, 2, 1, 0, 1794501016, b'client id 16 byt'), 'version 2'),
    ],
    ids=['missing', 'not Crashpad', 'another version'],
)
def test_launch_says_when_crash_uploads_couldnt_be_turned_off(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, content: bytes | None, why: str
) -> None:
    settings = _crashpad_settings(tmp_path / 'home', content)
    said = _launch_with_home(monkeypatch, tmp_path, tmp_path / 'home')
    assert said.startswith('Designer started in')
    # a sentence of its own after the plugin's status, which ends with no stop (REVIEW.md SRV-121)
    assert ': idle. Its crash reports may still be uploaded to Adobe' in said and why in said, said
    assert content is None or settings.read_bytes() == content, 'a file not known is left as it is'


def test_launch_touches_no_crash_settings_without_a_home_of_its_own(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # off macOS, or the user's home: their own Designer's settings are never changed
    patch_server(monkeypatch, '_designer_data_dir', lambda home=None: pytest.fail('crash settings read: %r' % home))
    said = _launch_with_home(monkeypatch, tmp_path, None)
    assert said.startswith('Designer started in') and 'upload' not in said


@_HOMES_OF_THEIR_OWN
def test_launch_turns_crash_uploads_off_before_leaving_the_home_screen(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-120: leaving it failed (a bridge timeout), and the next call found it already running
    settings = _crashpad_settings(tmp_path / 'home')
    with pytest.raises(server.ToolError):
        _launch_with_home(monkeypatch, tmp_path, tmp_path / 'home', server.ToolError('timed out'))
    assert struct.unpack_from('<I', settings.read_bytes(), 8)[0] == 0, 'uploads off'


@_RECORDED
@pytest.mark.parametrize('answers_at_once', [True, False], ids=['answering', 'waited for'])
def test_launch_turns_crash_uploads_off_in_an_agents_designer_already_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, answers_at_once: bool
) -> None:
    # REVIEW.md SRV-120: started by an earlier call that stopped waiting (a short wait_s), it answers only now: found
    # answering, or waited for as one already running, it gets them off too
    settings = _crashpad_settings(tmp_path / 'home')
    started = _launch_fakes(monkeypatch, tmp_path)
    _Processes(monkeypatch, 11)
    _an_agent_started(11, home=str(tmp_path / 'home'))
    calls: list[int] = []

    def answers(request: Request, wait: float, port: int | None = None) -> Reply:
        calls.append(1)
        if not answers_at_once and len(calls) < 3:
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    patch_server(monkeypatch, '_send', answers)
    said = server.launch_designer(wait_s=30)
    assert said.startswith('Designer already running') and 'upload' not in said and not started, said
    after = settings.read_bytes()
    assert struct.unpack_from('<I', after, 8)[0] == 0, 'uploads off'
    assert after[:8] + after[12:] == CRASHPAD_SETTINGS[:8] + CRASHPAD_SETTINGS[12:], 'the rest as Crashpad wrote it'


@_RECORDED
def test_launch_says_when_an_agents_designer_already_running_keeps_crash_uploads_on(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _launch_fakes(monkeypatch, tmp_path)
    _Processes(monkeypatch, 11)
    _an_agent_started(11, home=str(tmp_path / 'home'))  # its settings missing
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': 'idle'})
    said = server.launch_designer()
    assert said.startswith('Designer already running')
    assert ': idle. Its crash reports may still be uploaded to Adobe' in said and 'No such file' in said, said


@_HOMES_OF_THEIR_OWN
def test_a_designer_it_started_refusing_gets_crash_uploads_off_too(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-123: a refusal is an answer, raised: Designer has turned them on
    settings = _crashpad_settings(tmp_path / 'home')
    with pytest.raises(server._Refused, match='invalid token') as refused:
        _launch_with_home(monkeypatch, tmp_path, tmp_path / 'home', refuses=True)
    assert struct.unpack_from('<I', settings.read_bytes(), 8)[0] == 0, 'uploads off'
    assert 'upload' not in str(refused.value)


@_RECORDED
@pytest.mark.parametrize('settings_there', [True, False], ids=['turned off', 'missing'])
def test_an_agents_designer_refusing_gets_crash_uploads_off_too(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, settings_there: bool
) -> None:
    # REVIEW.md SRV-123: found refusing at once (another token, another protocol)
    settings = _crashpad_settings(tmp_path / 'home', CRASHPAD_SETTINGS if settings_there else None)
    _launch_fakes(monkeypatch, tmp_path)
    _Processes(monkeypatch, 11)
    _an_agent_started(11, home=str(tmp_path / 'home'))
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': False, 'error': 'invalid token'})
    with pytest.raises(server._Refused, match='invalid token') as refused:
        server.launch_designer()
    if settings_there:
        assert struct.unpack_from('<I', settings.read_bytes(), 8)[0] == 0, 'uploads off'
        assert 'upload' not in str(refused.value)
    else:
        said = str(refused.value)
        assert 'invalid token. Its crash reports may still be uploaded to Adobe' in said and 'No such file' in said, (
            said
        )


@_HOMES_OF_THEIR_OWN
def test_the_users_designer_already_running_keeps_its_crash_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # no record: the user's, whose settings are never changed, even where a home of its own would be
    settings = _crashpad_settings(tmp_path / 'home')
    _launch_fakes(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_own_home', lambda port: str(tmp_path / 'home'))
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': 'idle'})
    said = server.launch_designer()
    assert said.startswith('Designer already running') and 'upload' not in said
    assert settings.read_bytes() == CRASHPAD_SETTINGS


def _uploads(settings: Path) -> int:
    """Bit 0 of the options in Crashpad's settings at `settings`: 1 while uploads are on."""
    return int(struct.unpack_from('<I', settings.read_bytes(), 8)[0] & 1)


@_HOMES_OF_THEIR_OWN
@pytest.mark.parametrize('closes', [True, False], ids=['closes', 'forced'])
def test_quit_turns_crash_uploads_off_before_closing_an_agents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, closes: bool
) -> None:
    # REVIEW.md SRV-124: the call that started it may have stopped waiting, so no launch turned them off; a crash in
    # its quit would be uploaded
    settings = _crashpad_settings(tmp_path / 'home')
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, home=str(tmp_path / 'home'))
    asked = _closes(monkeypatch)
    at_the_close: list[int] = []
    at_the_end: list[int] = []
    bridge = server._bridge
    force_end = server._force_end

    def close(
        code: str,
        path: str | None = None,
        timeout: float | None = None,
        wait: float | None = None,
        port: int | None = None,
    ) -> str:
        at_the_close.append(_uploads(settings))
        said: str = bridge(code, path, timeout, wait, port)
        return said

    def end(pid: int, port: int, seen: bytes) -> bool:
        at_the_end.append(_uploads(settings))
        return bool(force_end(pid, port, seen))

    patch_server(monkeypatch, '_bridge', close)
    patch_server(monkeypatch, '_force_end', end)
    if closes:
        monkeypatch.setattr(time, 'sleep', lambda seconds: processes.pids.clear())
    said = server.quit_designer(wait_s=2)
    assert 'Designer quit after' in said and 'upload' not in said and asked, said
    assert at_the_close == [0] and at_the_end == ([] if closes else [0]), (at_the_close, at_the_end)


@_HOMES_OF_THEIR_OWN
def test_quit_says_when_crash_uploads_couldnt_be_turned_off(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, home=str(tmp_path / 'home'))  # its settings missing
    _closes(monkeypatch)
    monkeypatch.setattr(time, 'sleep', lambda seconds: processes.pids.clear())
    said = server.quit_designer()
    assert 'Its crash reports may still be uploaded to Adobe' in said and 'Designer quit after' in said, said


SAMPLED = ' Its threads, sampled first: /tmp/sd_mcp_501_9877/threads_11.sample.txt'


@_HOMES_OF_THEIR_OWN
def test_a_quit_that_cant_end_its_designer_says_its_crash_reports_may_be_uploaded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-166: every result of the quit said it, but its "could not be ended" error left the line out
    _Processes(monkeypatch, 11, ends_on=-1)
    _an_agent_started(11, home=str(tmp_path / 'home'))  # its settings missing
    _closes(monkeypatch)
    patch_server(monkeypatch, '_sampled_before_force', lambda pid, port: SAMPLED)
    with pytest.raises(server.ToolError, match='could not be ended') as raised:
        server.quit_designer(wait_s=2)
    assert 'Its crash reports may still be uploaded to Adobe' in str(raised.value), str(raised.value)


class _UnlistedFrom:
    """Designer's processes, which can't be listed from a moment on (pgrep failing: SRV-163's _NoListing)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, processes: _Processes) -> None:
        self.failing = False
        listed = server._designer_pids

        def pids() -> list[int]:
            if self.failing:
                raise server._NoListing("Designer's processes couldn't be listed (pgrep exit code 3: fork failed)")
            return list(listed())

        patch_server(monkeypatch, '_designer_pids', pids)

    def fail(self) -> None:
        self.failing = True


@_HOMES_OF_THEIR_OWN
@pytest.mark.parametrize('when', ['its wait', 'after its sample', 'its forced end'])
def test_a_quit_whose_processes_cant_be_listed_after_the_close_still_says_the_close_the_uploads_and_the_sample(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, when: str
) -> None:
    # REVIEW.md SRV-169: SRV-166 made the "could not be ended" error carry them; the listing's error, raised from any
    # of the looks after the close, carried none. SRV-171: the close's notes are empty unless unsaved packages were
    # dropped, so with the helper's own reply, the error didn't say the close was asked, nor that it was being forced
    processes = _Processes(monkeypatch, 11, ends_on=-1)
    unlisted = _UnlistedFrom(monkeypatch, processes)
    _an_agent_started(11, home=str(tmp_path / 'home'))  # its settings missing
    _closes(monkeypatch)

    def sample(pid: int, port: int) -> str:
        if when == 'after its sample':
            unlisted.fail()
        return SAMPLED

    patch_server(monkeypatch, '_sampled_before_force', sample)
    kill = processes.kill

    def signal_then_fail(pid: int, sig: int) -> None:
        kill(pid, sig)
        unlisted.fail()

    monkeypatch.setattr(os, 'kill', signal_then_fail if when == 'its forced end' else kill)
    if when == 'its wait':
        unlisted.fail()
    with pytest.raises(server._NoListing) as raised:
        server.quit_designer(wait_s=2)
    said = str(raised.value)
    assert said.startswith('Its crash reports may still be uploaded to Adobe'), said
    step = (
        'Designer 11 was asked to close.'
        if when == 'its wait'
        else 'Designer 11 did not quit within 2s and was being ended.'
    )
    assert step + " Designer's processes couldn't be listed" in said, said
    assert (SAMPLED.strip() in said) == (when != 'its wait'), said


@_HOMES_OF_THEIR_OWN
def test_an_agents_designer_whose_processes_cant_be_listed_as_it_is_ended_still_says_its_sample_and_its_uploads(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-169: _force_end's listing failing dropped what the end had found
    processes = _Processes(monkeypatch, 11, ends_on=-1)
    unlisted = _UnlistedFrom(monkeypatch, processes)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1, home=str(tmp_path / 'home'))  # its settings missing
    patch_server(monkeypatch, '_sampled_before_force', lambda pid, port: SAMPLED)
    kill = processes.kill

    def signal_then_fail(pid: int, sig: int) -> None:
        kill(pid, sig)
        unlisted.fail()

    monkeypatch.setattr(os, 'kill', signal_then_fail)
    with pytest.raises(server._NoListing) as raised:
        server._end_if_past_startup(server.PORT)
    said = str(raised.value)
    assert 'Its crash reports may still be uploaded to Adobe' in said and SAMPLED.strip() in said, said
    # REVIEW.md SRV-171: what was being done, said first
    ending = 'Designer 11, which an agent started, was not answering past its start-up and was being ended.'
    assert said.startswith(ending + " Designer's processes couldn't be listed"), said


def test_a_launch_whose_wait_cant_end_an_agents_designer_says_first_the_one_it_ended_before(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-169: the wait's "could not be ended" error left out told(), unlike the call's other errors
    _launch_fakes(monkeypatch, tmp_path)
    _Processes(monkeypatch, 12)
    ends: list[int] = []

    def end_if_past_startup(port: int) -> str:
        ends.append(port)
        if len(ends) == 1:  # as the call begins: one ended
            return ''
        raise server.ToolError(server._could_not_end(12))

    patch_server(monkeypatch, '_end_if_past_startup', end_if_past_startup)
    patch_server(monkeypatch, '_running_on', lambda port: True)  # another, not answering: waited for
    patch_server(monkeypatch, '_send', _no_bridge)
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    said = str(raised.value)
    assert said.startswith('Ended a Designer an agent started, which was not answering.\n') and len(ends) == 2, said
    assert 'Designer 12 could not be ended' in said, said


@_HOMES_OF_THEIR_OWN
@pytest.mark.parametrize('ends', [True, False], ids=['ended', 'not ended'])
def test_an_agents_designer_ended_past_its_start_up_says_its_uploads_then_its_sample_its_path_last(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, ends: bool
) -> None:
    # REVIEW.md SRV-166: the uploads sentence ran on right after the sample's path, which ends with no stop; SRV-168:
    # the stop SRV-166 put after the path was read as part of it, by the self-test (lifecycle/samples.py) and by an
    # agent copying it. Uploads first, as quit_designer says them, so nothing follows the path
    _Processes(monkeypatch, 11, ends_on=signal.SIGTERM if ends else -1)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1, home=str(tmp_path / 'home'))  # its settings missing
    patch_server(monkeypatch, '_sampled_before_force', lambda pid, port: SAMPLED)
    said = ''
    try:
        said = server._end_if_past_startup(server.PORT) or ''
    except server.ToolError as e:
        said = str(e)
    uploads, sample = said.find('Its crash reports may still be uploaded to Adobe'), said.find(SAMPLED.strip())
    assert 0 <= uploads < sample and said.endswith(SAMPLED), said
    found = re.search(re.escape(server.QUIT_SAMPLED) + r' (\S+)', said)  # as lifecycle/samples.py reads it
    assert found is not None and found.group(1) == SAMPLED.split()[-1], said


@_HOMES_OF_THEIR_OWN
def test_launch_turns_crash_uploads_off_before_ending_an_agents_not_answering(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-124: ended past its start-up, a crash in its teardown would be uploaded
    settings = _crashpad_settings(tmp_path / 'home')
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1, home=str(tmp_path / 'home'))
    at_the_end: list[int] = []
    force_end = server._force_end

    def end(pid: int, port: int, seen: bytes) -> bool:
        at_the_end.append(_uploads(settings))
        return bool(force_end(pid, port, seen))

    monkeypatch.setattr(subprocess, 'Popen', _popen(started, processes=processes))
    patch_server(monkeypatch, '_force_end', end)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    said = server.launch_designer(wait_s=30)
    assert 'Ended' in said and 'upload' not in said and at_the_end[:1] == [0], (said, at_the_end)


# --- who started it


@pytest.mark.parametrize(
    ('content', 'why'),
    [
        (None, 'no file'),
        ('not json', 'a corrupt file'),
        ('[1, 2]', 'not the right shape'),
        ('{"pid": "x", "start": "started 11"}', 'a pid that is no number'),
        ('{"pid": 11, "start": "another time"}', 'the ID was reused by another process'),
        ('{"pid": 12, "start": "started 12"}', 'that process has gone'),
    ],
)
def test_what_doesnt_count_as_an_agents(monkeypatch: pytest.MonkeyPatch, content: str | None, why: str) -> None:
    _Processes(monkeypatch, 11)
    path = Path(server.agent_designer_file(server.PORT))
    if content is not None:
        path.write_text(content)
    assert server._agent_designer(server.PORT) is None, why
    assert not path.exists(), 'a stale file is removed'


def test_a_process_that_isnt_designer_doesnt_count(monkeypatch: pytest.MonkeyPatch) -> None:
    # the ID and start time match a process, but it isn't among Designer's
    _Processes(monkeypatch, 11)
    patch_server(monkeypatch, '_process_start', lambda pid: 'started 12')
    _an_agent_started(12)
    assert server._agent_designer(server.PORT) is None


def test_the_file_is_read_again_by_a_new_server(monkeypatch: pytest.MonkeyPatch) -> None:
    # nothing but the file carries it, so a /mcp reconnect keeps it
    _Processes(monkeypatch, 11)
    _an_agent_started(11)
    assert server._agent_designer(server.PORT) == 11


def test_the_file_doesnt_depend_on_the_servers_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # the self-test's server wrote to /tmp while it looked in TMPDIR: the MCP client doesn't pass that on
    monkeypatch.undo()
    monkeypatch.setenv('TMPDIR', str(tmp_path))
    tempfile.tempdir = None
    try:
        path = server.agent_designer_file(server.PORT)
        assert not path.startswith(str(tmp_path)) and os.path.dirname(path) == os.path.expanduser('~')
        assert PLUGIN in os.path.basename(path)
    finally:
        tempfile.tempdir = None


def test_the_processes_are_listed_from_pgrep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.undo()  # the real function, with subprocess faked
    seen: list[list[str]] = []

    def run(cmd: list[str], **kw: Unpack[RunOptions]) -> subprocess.CompletedProcess[str]:
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout='11\n12\n', stderr='')

    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setattr(subprocess, 'run', run)
    assert server._designer_pids() == [11, 12] and seen[0][0] == 'pgrep'


def test_windows_never_lists_a_process_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    # not tried there (ROADMAP item 18), so every Designer counts as the user's
    monkeypatch.undo()
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.setattr(
        subprocess, 'run', lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout='11\n', stderr='')
    )
    assert server._designer_pids() == []


def test_designer_status_says_who_started_it(monkeypatch: pytest.MonkeyPatch) -> None:
    _Processes(monkeypatch, 11)
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': 'idle, 0 queued'})
    fake_bridge(monkeypatch, lambda code: 'process 11')
    assert 'Not started by an agent' in server.designer_status()
    _an_agent_started(11)
    assert 'Started by an agent' in server.designer_status()


def test_designer_status_goes_by_the_designer_answering(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-73: the record names one process, the package list comes from whichever holds the port
    _Processes(monkeypatch, 11, 12)
    _an_agent_started(12)
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': 'idle, 0 queued'})
    fake_bridge(monkeypatch, lambda code: 'process 11')
    assert 'Not started by an agent' in server.designer_status()
    fake_bridge(monkeypatch, lambda code: 'process 12')
    assert 'Started by an agent' in server.designer_status()


def test_designer_status_while_a_job_runs_cant_tell_two_apart(monkeypatch: pytest.MonkeyPatch) -> None:
    processes = _Processes(monkeypatch, 11, 12)
    _an_agent_started(12)
    patch_server(
        monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': 'running for 4.0s, 0 queued'}
    )
    assert 'Not started by an agent' in server.designer_status(), "unclear counts as the user's"
    processes.pids.remove(11)
    assert 'Started by an agent' in server.designer_status()


@pytest.mark.parametrize('state', ['idle, 0 queued', 'running for 4.0s, 0 queued'], ids=['idle', 'while a job runs'])
def test_designer_status_reads_each_record_once(monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    # ROADMAP item 106, REVIEW.md TST-502. Idle, _started_by read the port's record and _others every record. While a
    # job runs, _sorted_out read every record, _started_by the port's again and _others every record once more. Each read
    # lists Designer's processes again
    _Processes(monkeypatch, 11, 12)
    _an_agent_started(11)
    _an_agent_started(12, port=OTHER)
    reads = _record_reads(monkeypatch)
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': state})
    fake_bridge(monkeypatch, lambda code: 'process 11')
    text = server.designer_status()
    assert 'Started by an agent' in text and '%d (process 12)' % OTHER in text, text
    assert sorted(reads) == sorted([server.PORT, OTHER]), reads


# --- closing it


def _closes(monkeypatch: pytest.MonkeyPatch, said: str = 'closing Designer') -> list[str]:
    asked: list[str] = []

    def bridge(code: str) -> str:
        asked.append(code)
        return said

    fake_bridge(monkeypatch, bridge)
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': 'idle, 0 queued'})
    return asked


def test_quit_refuses_a_designer_no_agent_started(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    processes = _Processes(monkeypatch, 11)
    asked = _closes(monkeypatch)
    with pytest.raises(server.ToolError, match=r'ask the user to save, close and reopen'):
        server.quit_designer()
    assert not processes.signals and not asked, 'nothing is sent to it'


@_FORCE_ENDS
def test_quit_leaves_the_users_next_to_the_agents(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    processes = _Processes(monkeypatch, 11, 12)
    _closes(monkeypatch)
    _an_agent_started(12)
    server.quit_designer(wait_s=2)
    assert processes.signals == [(12, signal.SIGTERM)] and processes.pids == [11]


def test_quit_closes_an_agents_normally(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    asked = _closes(monkeypatch, 'discarding unsaved changes: /a.sbs\nclosing Designer')

    def gone(seconds: float) -> None:
        processes.pids.clear()

    monkeypatch.setattr(time, 'sleep', gone)
    text = server.quit_designer()
    assert 'Designer quit after' in text and 'discarding unsaved changes: /a.sbs' in text and asked
    assert not processes.signals and not Path(server.agent_designer_file(server.PORT)).exists()


@_FORCE_ENDS
def test_quit_forces_an_agents_that_stays(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    # REVIEW.md HLP-82: Designer can hang at the very end of its shutdown, past anything inside it
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    _closes(monkeypatch)
    text = server.quit_designer(wait_s=3)
    assert 'forced' in text and processes.signals == [(11, signal.SIGTERM)]
    assert not Path(server.agent_designer_file(server.PORT)).exists()


NEW = '===== New Session ====='  # the first line Designer logs at each start
START = '[INFO][Python] Python SDK Version 3.13'  # about 430 lines later, as the plugins load (read_designer_log)
CLOSED = '[INFO][Python] %s' % project_constants.QUIT_CLOSED  # the quit helper's line once every window closed


def _forced_with(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lines: list[str] | None) -> tuple[str, list[str]]:
    """quit_designer forcing the agent's Designer 11, whose own log holds `lines` (None: it has none). Skips on
    Windows: a home recorded reaches the crash uploads' fcntl (REVIEW.md TST-507)."""
    if sys.platform == 'win32':
        pytest.skip('Windows lacks fcntl')
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, home=str(tmp_path))
    asked = _closes(monkeypatch)
    log = tmp_path / 'log.txt'
    if lines is not None:
        log.write_text('\n'.join(lines))
    patch_server(monkeypatch, '_log_for', lambda port: pytest.fail('the shared log may be read (REVIEW.md SRV-108)'))

    def agent_log(port: int, home: str, written: float) -> str:
        if lines is None:  # as the real one says it (REVIEW.md TST-294)
            raise server.ToolError(
                'The Designer on port %d has no log yet: it is still starting. Try again shortly.' % port
            )
        return str(log)

    patch_server(monkeypatch, '_agent_log', agent_log)
    text = server.quit_designer(wait_s=3)
    assert processes.signals == [(11, signal.SIGTERM)] and asked
    return text, asked


def test_a_forced_quit_after_every_window_closed_says_so_and_quotes_its_logs_last_line(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path
) -> None:
    # ROADMAP item 69, REVIEW.md SRV-106: two quits in a full run hung in Designer's shutdown after their close had
    # taken; the result tells that from a close that didn't take, by the line the quit helper logs, wherever the
    # shutdown hangs after it (in aboutToQuit too, before Designer logs any teardown line)
    text, asked = _forced_with(
        monkeypatch, tmp_path, [NEW, START, '[INFO] ready', CLOSED, '[INFO][IPC] Remove PID', '', '   ', '']
    )  # blank lines after the last that isn't: the file ends in them (REVIEW.md TST-306)
    assert project_constants.QUIT_FORCED_IN_SHUTDOWN in text and '"[INFO][IPC] Remove PID"' in text
    assert project_constants.QUIT_FORCED_NOT_CLOSED not in text
    assert repr(project_constants.QUIT_CLOSED) in asked[0], 'the helper is given the line to log'


@pytest.mark.parametrize(
    'lines',
    [
        [NEW, START, '[INFO][Environment] Instance Execute'],  # running: its close didn't take
        [NEW, START, CLOSED, NEW, START, '[INFO][Environment] Instance Execute'],  # a close of an earlier start
        [NEW, START, CLOSED, NEW, '[INFO][3DView] Precompiling shaders done.'],  # REVIEW.md SRV-107: still starting
    ],
)
def test_a_forced_quit_says_it_had_not_closed_unless_its_session_logged_every_window_closed(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path, lines: list[str]
) -> None:
    text, _ = _forced_with(monkeypatch, tmp_path, lines)
    assert project_constants.QUIT_FORCED_NOT_CLOSED in text and '"%s"' % lines[-1] in text
    assert project_constants.QUIT_FORCED_IN_SHUTDOWN not in text


def test_a_forced_quit_with_no_log_of_its_own_says_so(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path
) -> None:
    # REVIEW.md SRV-106: "had not closed" only when its log was read
    text, _ = _forced_with(monkeypatch, tmp_path, None)
    assert 'forced' in text and 'its log could not be read' in text
    assert (
        project_constants.QUIT_FORCED_NOT_CLOSED not in text and project_constants.QUIT_FORCED_IN_SHUTDOWN not in text
    )


@_FORCE_ENDS
def test_a_forced_quit_reads_no_log_but_its_own(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    # one recorded without a home writes the shared log, the user's lines among its own: not read
    _Processes(monkeypatch, 11)
    _an_agent_started(11)
    _closes(monkeypatch)
    patch_server(monkeypatch, '_log_for', lambda port: pytest.fail('the shared log was read'))
    patch_server(monkeypatch, '_agent_log', lambda port, home, written: pytest.fail('a log read without a home'))
    assert 'its log could not be read' in server.quit_designer(wait_s=3)


def test_a_forced_quit_reads_its_record_once(monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path) -> None:
    # ROADMAP item 106: _quit read the record, then _quit_evidence read it again for the home, listing Designer's
    # processes again (REVIEW.md TST-501)
    reads = _record_reads(monkeypatch)
    text, _ = _forced_with(monkeypatch, tmp_path, [NEW, START, CLOSED, '[INFO][IPC] Remove PID'])
    assert project_constants.QUIT_FORCED_IN_SHUTDOWN in text and reads == [server.PORT], (text, reads)


@pytest.mark.skipif(
    sys.platform == 'win32', reason='Windows lacks fcntl: a home recorded reaches it (REVIEW.md TST-507)'
)
def test_a_designer_ending_while_its_log_is_read_is_not_reported_forced(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path
) -> None:
    # REVIEW.md SRV-108: the read takes time after the last look; one that ended in it quit by itself
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, home=str(tmp_path))
    _closes(monkeypatch)
    log = tmp_path / 'log.txt'
    log.write_text('\n'.join([NEW, START, CLOSED]))

    def read_as_it_ends(port: int, home: str, written: float) -> str:
        processes.pids.clear()
        return str(log)

    patch_server(monkeypatch, '_agent_log', read_as_it_ends)
    text = server.quit_designer(wait_s=3)
    assert 'Designer quit after' in text and 'forced' not in text and not processes.signals


# the quit's clean-up locks with fcntl once the platform is faked as macOS (REVIEW.md TST-308)
_POSIX_QUIT = pytest.mark.skipif(sys.platform == 'win32', reason="no fcntl there, and macOS's sample")


_Sampled = tuple[
    int, str, list[tuple[int, int]]
]  # a call of the fake _sample: the process, the path, the signals before


def _fake_sample(
    monkeypatch: pytest.MonkeyPatch, folder: Path, processes: _Processes, said: str | None = None
) -> list[_Sampled]:
    """As on macOS, with `folder` the agent's own: `_sample` faked, writing its file unless it says `said`; each call
    recorded with the signals sent before it."""
    patch_server(monkeypatch, '_checked_folder', lambda port: str(folder))
    calls: list[_Sampled] = []

    def sample(pid: int, path: str) -> str | None:
        calls.append((pid, path, list(processes.signals)))
        if said is None:
            Path(path).write_text('Call graph:')
        return said

    patch_server(monkeypatch, '_sample', sample)
    monkeypatch.setattr(sys, 'platform', 'darwin')
    return calls


def _sampling(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    said: str | None = None,
    home: str | None = None,
    ends_on: int = signal.SIGTERM,
) -> tuple[_Processes, list[_Sampled]]:
    """An agent's Designer 11, recorded with `home`, that stays past its quit's wait and ends on `ends_on`; its own
    folder tmp_path, its sample faked (_fake_sample)."""
    processes = _Processes(monkeypatch, 11, ends_on=ends_on)
    _an_agent_started(11, home=home)
    _closes(monkeypatch)
    return processes, _fake_sample(monkeypatch, tmp_path, processes, said)


@_POSIX_QUIT
def test_a_forced_quit_samples_its_threads_first_and_names_the_file(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path
) -> None:
    # ROADMAP item 70: what a Designer stuck past its quit's wait was doing, kept in its own folder
    processes, calls = _sampling(monkeypatch, tmp_path)
    text = server.quit_designer(wait_s=3)
    path = str(tmp_path / 'threads_11.sample.txt')
    assert calls == [(11, path, [])], 'sampled once, into its own folder, before any signal'
    assert processes.signals == [(11, signal.SIGTERM)] and text.endswith('sampled first: %s' % path)


@_POSIX_QUIT
def test_a_forced_quit_whose_sample_fails_is_forced_and_says_why(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path
) -> None:
    # as sample says it (measured), ending in a period: the sentence doesn't add one (REVIEW.md SRV-114)
    said = 'sample[5]: sample cannot examine process 11 because it no longer appears to be running.'
    processes, calls = _sampling(monkeypatch, tmp_path, said=said)
    text = server.quit_designer(wait_s=3)
    assert len(calls) == 1 and processes.signals == [(11, signal.SIGTERM)]
    assert 'could not be sampled first: %s' % said in text and '..' not in text


@_POSIX_QUIT
def test_a_forced_quit_samples_nothing_without_its_own_folder(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path
) -> None:
    processes, calls = _sampling(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_checked_folder', lambda port: None)  # another account's, or gone
    text = server.quit_designer(wait_s=3)
    assert not calls and processes.signals == [(11, signal.SIGTERM)] and 'sampled' not in text


def test_a_forced_quit_samples_nothing_off_macos(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path
) -> None:
    _, calls = _sampling(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, 'platform', 'win32')
    assert server._sampled_before_force(11, server.PORT) == '' and not calls


@_POSIX_QUIT
def test_a_designer_quitting_within_its_wait_is_not_sampled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-309: only one about to be forced; a sample costs seconds and a file
    processes, calls = _sampling(monkeypatch, tmp_path)
    monkeypatch.setattr(time, 'sleep', lambda s: processes.pids.clear())  # gone at the wait's first look
    text = server.quit_designer(wait_s=3)
    assert 'Designer quit after' in text and not calls and not processes.signals


@_POSIX_QUIT
def test_a_designer_ending_while_sampled_is_not_reported_forced(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path
) -> None:
    # as one ending while its log is read (REVIEW.md SRV-108); its sample, written as it ended (measured), is a hang's
    # evidence, named, the name without "forced", which a plain quit doesn't hold (REVIEW.md SRV-115)
    processes, _ = _sampling(monkeypatch, tmp_path)

    def sample(pid: int, path: str) -> None:
        Path(path).write_text('Call graph:')
        processes.pids.clear()

    patch_server(monkeypatch, '_sample', sample)
    text = server.quit_designer(wait_s=3)
    assert 'Designer quit after' in text and 'forced' not in text and not processes.signals
    assert text.endswith('%s %s' % (project_constants.QUIT_SAMPLED, tmp_path / 'threads_11.sample.txt'))


@_POSIX_QUIT
def test_a_close_logged_while_it_is_sampled_counts(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path
) -> None:
    # REVIEW.md SRV-111: the sample takes seconds; its log is read after it, just before the force
    processes, _ = _sampling(monkeypatch, tmp_path, home=str(tmp_path))
    log = tmp_path / 'log.txt'
    log.write_text('\n'.join([NEW, START, '[INFO] ready']))
    patch_server(monkeypatch, '_agent_log', lambda port, home, written: str(log))

    def sample(pid: int, path: str) -> None:
        log.write_text('\n'.join([NEW, START, '[INFO] ready', CLOSED]))  # its close taking meanwhile
        Path(path).write_text('Call graph:')

    patch_server(monkeypatch, '_sample', sample)
    text = server.quit_designer(wait_s=3)
    assert project_constants.QUIT_FORCED_IN_SHUTDOWN in text and processes.signals == [(11, signal.SIGTERM)]


@_POSIX_QUIT
def test_a_force_that_fails_names_the_sample(monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path) -> None:
    # REVIEW.md SRV-112: one no signal ends, when its stacks matter most
    _, calls = _sampling(monkeypatch, tmp_path, ends_on=-1)
    with pytest.raises(server.ToolError, match=r'kill -9 11`\. Its threads, sampled first: .*threads_11'):
        server.quit_designer(wait_s=3)
    assert len(calls) == 1


@_POSIX_QUIT
def test_launch_samples_an_agents_it_ends(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    # REVIEW.md SRV-113: one not answering past its start-up may be one hung in its shutdown
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1)
    own = tmp_path / 'own'
    own.mkdir()
    calls = _fake_sample(monkeypatch, own, processes)

    monkeypatch.setattr(subprocess, 'Popen', _popen(started, processes=processes))
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    text = server.launch_designer(wait_s=30)
    path = str(own / 'threads_11.sample.txt')
    assert calls == [(11, path, [])] and processes.signals == [(11, signal.SIGTERM)]
    assert 'which was not answering. Its threads, sampled first: %s\n' % path in text and 'Designer started in' in text


@_POSIX_QUIT
def test_launch_names_the_sample_of_one_it_cant_end(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11, ends_on=-1)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1)
    own = tmp_path / 'own'
    own.mkdir()
    _fake_sample(monkeypatch, own, processes)
    patch_server(monkeypatch, '_send', _no_bridge)
    with pytest.raises(server.ToolError, match=r'kill -9 11`\. Its threads, sampled first: .*threads_11'):
        server.launch_designer(wait_s=30)
    assert not started


@pytest.mark.parametrize(
    'outcome, said',
    [
        ((0, '', True), None),  # written
        ((1, 'sample[5]: sample cannot examine process 11\n', False), 'sample[5]: sample cannot examine process 11'),
        ((0, '', False), 'sample exited with 0'),  # no file: nothing to name
        (subprocess.TimeoutExpired(['sample'], 30), 'timed out'),
        (OSError(2, 'No such file or directory'), 'No such file or directory'),  # no sample here (TST-309)
    ],
)
def test_sample_runs_macos_sample_for_a_second_into_the_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, outcome: tuple[int, str, bool] | Exception, said: str | None
) -> None:
    path = str(tmp_path / 'threads_11.sample.txt')
    ran: list[tuple[list[str], float | None]] = []

    def run(cmd: list[str], **kw: Unpack[RunOptions]) -> subprocess.CompletedProcess[str]:
        ran.append((cmd, kw.get('timeout')))
        if isinstance(outcome, Exception):
            raise outcome
        code, stderr, writes = outcome
        if writes:
            Path(path).write_text('Call graph:')
        return subprocess.CompletedProcess(cmd, code, '', stderr)

    monkeypatch.setattr(subprocess, 'run', run)
    result = REAL_SAMPLE(11, path)
    assert ran == [(['/usr/bin/sample', '11', '1', '-file', path], 30)], 'one second, a limit of its own'
    assert result == said if said is None else said in str(result)


LISTENING = '[INFO] [%s] v8 listening on 127.0.0.1:9877' % PLUGIN
HANDED_OVER = '[INFO][IPC] Found instance PID: 1'  # a second process, handing its arguments over, then gone
ENDED = '[INFO][Environment] Application uninitialized'


@pytest.mark.parametrize(
    'lines, since, port',
    [
        # REVIEW.md SRV-107: Designer logs "Python SDK Version" about 430 lines into a session; before it, the previous
        # session's lines aren't this one's
        ([NEW, START, LISTENING, CLOSED, NEW, '[INFO] starting'], [NEW, '[INFO] starting'], None),
        # REVIEW.md TST-294: started, from its SDK line, as before
        ([NEW, '[INFO] start-up', START, LISTENING, 'x'], [START, LISTENING, 'x'], 9877),
        # REVIEW.md SRV-109: a process handing over to the running one logs a session that ends at once, no SDK line
        (
            [NEW, START, LISTENING, 'x', NEW, HANDED_OVER, ENDED, 'y'],
            [START, LISTENING, 'x', NEW, HANDED_OVER, ENDED, 'y'],
            9877,
        ),
        # REVIEW.md SRV-110: a hand-over while one starts ends its own session only, not the one starting
        (
            [NEW, START, LISTENING, CLOSED, ENDED, NEW, '[INFO] starting', NEW, HANDED_OVER, ENDED, 'still starting'],
            [NEW, '[INFO] starting', NEW, HANDED_OVER, ENDED, 'still starting'],
            None,
        ),
    ],
)
def test_the_last_start_is_the_session_still_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lines: list[str], since: list[str], port: int | None
) -> None:
    # for read_designer_log, the port its plugin last logged (_log_for) and a forced quit's evidence
    log = tmp_path / 'log.txt'
    log.write_text('\n'.join(lines))
    monkeypatch.setenv('SD_DESIGNER_LOG', str(log))
    assert server.read_designer_log(lines=100).splitlines()[1:] == since
    assert server._last_port(str(log)) == port


@pytest.mark.parametrize(
    'lines, closed',
    [
        # the previous session's line inside the tail, its first line before the cut
        ([NEW, START, 'p' * server.LOG_TAIL, CLOSED, 'q' * 100, NEW, START, '[INFO] running'], False),
        # this session longer than the tail, its line in it
        ([NEW, START, 'r' * server.LOG_TAIL, CLOSED, '[INFO][IPC] Remove PID'], True),
    ],
)
def test_a_forced_quit_reads_its_logs_tail_and_judges_this_session(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, tmp_path: Path, lines: list[str], closed: bool
) -> None:
    # REVIEW.md SRV-108, TST-294: only the end of the log is read
    text, _ = _forced_with(monkeypatch, tmp_path, lines)
    assert (project_constants.QUIT_FORCED_IN_SHUTDOWN in text) == closed and '"%s"' % lines[-1] in text


@_FORCE_ENDS
def test_quit_forces_harder_if_it_must(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    processes = _Processes(monkeypatch, 11, ends_on=signal.SIGKILL)
    _an_agent_started(11)
    _closes(monkeypatch)
    assert 'forced' in server.quit_designer(wait_s=1)
    assert processes.signals == [(11, signal.SIGTERM), (11, signal.SIGKILL)]


@_FORCE_ENDS
def test_quit_says_so_if_even_that_fails(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    _Processes(monkeypatch, 11, ends_on=-1)
    _an_agent_started(11)
    _closes(monkeypatch)
    with pytest.raises(server.ToolError, match=r'kill -9 11'):
        server.quit_designer(wait_s=1)


@_FORCE_ENDS
def test_quit_forces_an_agents_with_no_bridge(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)

    def dead(code: str) -> str:
        raise server.ToolError('Designer is not reachable.')

    fake_bridge(monkeypatch, dead)
    patch_server(monkeypatch, '_send', _no_bridge)
    text = server.quit_designer(wait_s=1)
    assert 'forced' in text and processes.signals and 'did not reply: Designer is not reachable' in text


@_FORCE_ENDS
def test_quit_names_the_process_it_means(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    # REVIEW.md SRV-73: the close goes to whichever Designer holds the port, and the helper refuses any other
    _Processes(monkeypatch, 11)
    _an_agent_started(11)
    asked = _closes(monkeypatch)
    server.quit_designer(wait_s=1)
    assert asked[0].rstrip().endswith('quit_designer(11, %r)' % project_constants.QUIT_CLOSED)


@_FORCE_ENDS
def test_quit_with_another_designer_on_the_port_only_ends_its_own(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None
) -> None:
    processes = _Processes(monkeypatch, 11, 12)
    _an_agent_started(12)
    _closes(monkeypatch, 'x\n--- ERROR ---\nRuntimeError: this is Designer 11, not 12: nothing closed')
    text = server.quit_designer(wait_s=1)
    assert processes.signals == [(12, signal.SIGTERM)] and processes.pids == [11]
    assert 'not asked to close' in text and 'this is Designer 11' in text and 'forced' in text


@pytest.mark.parametrize(('wait_s', 'limit'), [(1, 10), (30, 30)])
@_FORCE_ENDS
def test_the_close_has_a_limit_of_its_own(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, wait_s: int, limit: int
) -> None:
    # REVIEW.md SRV-78: a main thread frozen outside a job reads as idle, and the close then waited about 15 minutes
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    waits: list[float] = []

    def frozen(request: Request, wait: float, port: int | None = None) -> Reply:
        if request.get('cmd'):
            return {'ok': True, 'output': 'idle, 0 queued', 'error': ''}
        waits.append(wait)
        raise server.ToolError('No reply from Designer after %ds.' % wait)

    patch_server(monkeypatch, '_send', frozen)
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    text = server.quit_designer(wait_s=wait_s)
    assert waits == [limit] and processes.signals == [(11, signal.SIGTERM)]
    assert 'did not reply: No reply from Designer' in text and 'forced' in text


@pytest.mark.parametrize('state', ['running for 412.0s, 0 queued', 'idle, 2 queued'])
@_FORCE_ENDS
def test_quit_doesnt_queue_behind_a_job(monkeypatch: pytest.MonkeyPatch, no_sleep: None, state: str) -> None:
    # REVIEW.md SRV-74: the close would wait about 15 minutes in the queue before wait_s even started
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    asked = _closes(monkeypatch)
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': state})
    text = server.quit_designer(wait_s=1)
    assert not asked and processes.signals == [(11, signal.SIGTERM)]
    assert 'not asked to close' in text and state in text and 'forced' in text


@_FORCE_ENDS
def test_a_process_gone_or_not_ours_to_signal_doesnt_raise(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    processes = _Processes(monkeypatch, 11)

    def refuses(pid: int, sig: int) -> None:
        processes.pids.clear()
        raise ProcessLookupError

    monkeypatch.setattr(os, 'kill', refuses)
    assert server._force_end(11, server.PORT, b'') is True
    processes.pids.append(11)

    def denied(pid: int, sig: int) -> None:
        raise PermissionError

    monkeypatch.setattr(os, 'kill', denied)
    assert server._force_end(11, server.PORT, b'') is False


# --- a Designer on a chosen bridge port (ROADMAP item 49): several side by side, each with its own record


OTHER = 9901  # a port that isn't the server's (SD_BRIDGE_PORT, 9877 by default)


def _ports_answering(*ports: int, asked: list[int | None] | None = None) -> _Send:
    """_send that answers on `ports` only, noting the port of every request in asked."""

    def send(request: Request, wait: float, port: int | None = None) -> Reply:
        if asked is not None:
            asked.append(port)
        if port not in ports:
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle, 0 queued'}

    return send


@pytest.mark.parametrize('port', [None, OTHER], ids=['the servers', 'another'])
@_SETS_UNIX
def test_launch_opens_a_new_instance_hidden_with_the_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, port: int | None
) -> None:
    # `open -a` alone brings back a Designer already running and passes it no environment: the plugin reads its port
    # there. REVIEW.md SRV-152: started from its binary, its window came up in front of the active app's; opened
    # hidden (-j), as a new instance (-n), not brought to the front (-g), none of its windows showed in 4 of 4 launches
    assert server.PORT != OTHER
    monkeypatch.setattr(sys, 'platform', 'darwin')
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch)
    want = server.PORT if port is None else port
    asked: list[int | None] = []
    answering: list[int] = []

    def begin(cmd: list[str], **kw: Unpack[_PopenArgs]) -> _FakeProcess:
        started.append(cmd)
        _started_with.append(kw)
        processes.pids.append(77)
        answering.append(want)
        return _FakeProcess(77)

    def send(request: Request, wait: float, port: int | None = None) -> Reply:
        return _ports_answering(*answering, asked=asked)(request, wait, port)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', send)
    monkeypatch.setenv('PYTHONPATH', '/the/servers/own')
    text = server.launch_designer(wait_s=30, port=port)
    cmd = started[0]
    assert cmd[:4] == ['open', '-n', '-g', '-j'] and cmd[-2:] == ['-a', str(tmp_path)]
    passed = dict(cmd[i + 1].split('=', 1) for i, arg in enumerate(cmd) if arg == '--env')
    assert passed['SD_BRIDGE_PORT'] == str(want) and passed[server.STAY_BEHIND] == '1'
    assert 'PYTHONPATH' not in passed and 'HOME' not in passed, 'the variables Designer reads, as `--env`'
    kw = _started_with[0]
    assert kw['env']['SD_BRIDGE_PORT'] == str(want)
    assert kw['cwd'] == '/', "as `open -a` started it: not the server's folder, the repository"
    assert kw['env']['HOME'] == os.environ['HOME'], 'the rest of the environment passes on'
    assert 'PYTHONPATH' not in kw['env'], "Designer's own Python doesn't take the server's settings"
    assert set(asked) == {want}, 'every request goes to that port'
    assert 'Designer started in' in text and 'on port %d' % want in text
    assert server._agent_designer(want) == 77
    assert not os.path.exists(server.agent_designer_file(OTHER if port is None else server.PORT))


@pytest.mark.parametrize('platform', ['darwin', 'win32'])
def test_a_designer_started_on_macos_doesnt_make_itself_the_active_app(
    monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    # REVIEW.md SRV-149: Designer's Qt made it the active app as it finished launching, its window in front of the
    # user's and their keyboard in it until it answered; with this variable it stayed behind (measured)
    variable = 'QT_MAC_DISABLE_FOREGROUND_APPLICATION_TRANSFORM'  # read by Designer's Qt 6.8.6, its Cocoa plugin
    monkeypatch.setattr(sys, 'platform', platform)
    monkeypatch.delenv(variable, raising=False)
    env = server._designer_env(OTHER, None, None, '')
    assert env.get(variable) == ('1' if platform == 'darwin' else None)


def test_the_designer_started_is_reaped_when_it_exits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # a child nobody waits for lingers as a zombie, which still has its ID and start time
    import threading

    waited = threading.Event()

    class Process(_FakeProcess):
        def wait(self, timeout: float | None = None) -> int:
            waited.set()
            return 0

    started = _launch_fakes(monkeypatch, tmp_path)

    def begin(cmd: list[str], **kw: Unpack[_PopenArgs]) -> Process:
        started.append(cmd)
        return Process(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    # a binary, not an app bundle: `open`'s wait would set `waited` with no thread (REVIEW.md TST-437)
    binary = tmp_path / 'Designer'
    binary.write_text('')
    monkeypatch.setenv('SD_DESIGNER_APP', str(binary))
    patch_server(monkeypatch, '_designer_running', lambda: False)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    server.launch_designer(wait_s=30)
    assert waited.wait(5)


def test_launch_on_windows_passes_the_port_too(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    monkeypatch.setattr(sys, 'platform', 'win32')
    started = _launch_fakes(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_designer_running', lambda: False)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    server.launch_designer(wait_s=30, port=OTHER)
    assert started == [[str(tmp_path)]] and _started_with[0]['env']['SD_BRIDGE_PORT'] == str(OTHER)
    assert _started_with[0]['creationflags'], 'detached, as os.startfile started it'
    assert not os.path.exists(server.agent_designer_file(OTHER)), 'nothing is recorded there (ROADMAP item 18)'


def test_launch_on_windows_starts_none_next_to_a_running_designer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md TST-150: nothing is recorded there, so a second one would count as the user's; with any Designer
    # running, a launch on another port waits for it and starts none (simulated: no Windows tried)
    monkeypatch.setattr(sys, 'platform', 'win32')
    started = _launch_fakes(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_designer_running', lambda: True)
    patch_server(monkeypatch, '_send', _ports_answering(server.PORT))  # the running one, on the server's port
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError, match='already running, but its bridge did not answer within 30s'):
        server.launch_designer(wait_s=30, port=OTHER)
    assert started == [], 'a second Designer was started'


def test_each_port_has_a_record_of_its_own(monkeypatch: pytest.MonkeyPatch) -> None:
    # one file per port: servers launching at the same time never write the same one
    _Processes(monkeypatch, 11, 12)
    _an_agent_started(11)
    _an_agent_started(12, port=OTHER)
    assert server.agent_designer_file(OTHER) != server.agent_designer_file(server.PORT)
    assert server.agent_designer_ports() == sorted([server.PORT, OTHER])
    assert (server._agent_designer(server.PORT), server._agent_designer(OTHER)) == (11, 12)


@_RECORDED
def test_launch_on_a_port_next_to_an_agents_on_another(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    answering = [server.PORT]

    def begin(cmd: list[str], **kw: Unpack[_PopenArgs]) -> _FakeProcess:
        started.append(cmd)
        processes.pids.append(77)
        answering.append(OTHER)
        return _FakeProcess(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', lambda r, wait, port=None: _ports_answering(*answering)(r, wait, port))
    text = server.launch_designer(wait_s=30, port=OTHER)
    assert 'Designer started in' in text and len(started) == 1 and not processes.signals
    assert (server._agent_designer(server.PORT), server._agent_designer(OTHER)) == (11, 77)


def test_launch_refuses_to_start_one_next_to_the_users(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # Designers share the preferences plist (server_tools/lifecycle.py's docstring, Several Designers side by side),
    # not measured to undo anything (REVIEW.md TST-189: the refusal said the last to quit writes every settings file)
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    patch_server(monkeypatch, '_listening_ports', lambda pid: {server.PORT} if pid == 11 else set())
    patch_server(monkeypatch, '_send', _ports_answering(server.PORT))
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30, port=OTHER)
    message = str(raised.value)
    assert 'process 11' in message and 'preferences plist' in message and 'ask the user to close it' in message
    assert 'last to quit' not in message
    assert not started and not processes.signals


def test_launch_refuses_once_the_one_it_waits_for_turns_out_to_be_the_users(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # listening nowhere yet, a Designer starting may be the one on this port, so it is waited for, as before
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    looks: list[int] = []

    def listening(pid: int) -> set[int]:
        looks.append(pid)
        return {server.PORT} if len(looks) > 3 else set()

    patch_server(monkeypatch, '_listening_ports', listening)
    patch_server(monkeypatch, '_send', _no_bridge)
    clock = iter(range(0, 1000, 2))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError, match='ask the user to close it'):
        server.launch_designer(wait_s=60, port=OTHER)
    assert not started and not processes.signals and len(looks) > 3


def test_designer_status_on_a_port(monkeypatch: pytest.MonkeyPatch) -> None:
    _Processes(monkeypatch, 11, 12)
    _an_agent_started(11)
    _an_agent_started(12, port=OTHER)
    asked: list[int | None] = []
    patch_server(monkeypatch, '_send', _ports_answering(server.PORT, OTHER, asked=asked))

    def bridge(
        code: str,
        path: str | None = None,
        timeout: float | None = None,
        wait: float | None = None,
        port: int | None = None,
    ) -> str:
        asked.append(port)
        return 'process %d' % (12 if port == OTHER else 11)

    patch_server(monkeypatch, '_bridge', bridge)
    text = server.designer_status(port=OTHER)
    assert set(asked) == {OTHER}, 'every request goes to that port'
    assert 'Started by an agent' in text and 'Bridge port %d' % OTHER in text
    assert 'on other ports: %d (process 11)' % server.PORT in text
    text = server.designer_status()
    assert 'Started by an agent' in text and 'on other ports: %d (process 12)' % OTHER in text


def test_designer_status_while_a_job_runs_on_a_port(monkeypatch: pytest.MonkeyPatch) -> None:
    # with the process answering unknown, the one an agent started on another port isn't a second candidate
    _Processes(monkeypatch, 11, 12)
    _an_agent_started(11)
    _an_agent_started(12, port=OTHER)
    patch_server(
        monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': 'running for 4.0s, 0 queued'}
    )
    assert 'Started by an agent' in server.designer_status(port=OTHER)


def test_quit_on_a_port_closes_only_its_own(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    processes = _Processes(monkeypatch, 11, 12)
    _an_agent_started(11)
    _an_agent_started(12, port=OTHER)
    asked: list[tuple[str, int | None]] = []
    sent: list[int | None] = []
    patch_server(monkeypatch, '_send', _ports_answering(server.PORT, OTHER, asked=sent))

    def bridge(
        code: str,
        path: str | None = None,
        timeout: float | None = None,
        wait: float | None = None,
        port: int | None = None,
    ) -> str:
        asked.append((code, port))
        return 'closing Designer'

    def gone(seconds: float) -> None:
        if asked and 12 in processes.pids:
            processes.pids.remove(12)

    patch_server(monkeypatch, '_bridge', bridge)
    monkeypatch.setattr(time, 'sleep', gone)
    text = server.quit_designer(port=OTHER)
    assert 'Designer quit after' in text and not processes.signals and processes.pids == [11]
    assert (
        len(asked) == 1
        and asked[0][0].rstrip().endswith('quit_designer(12, %r)' % project_constants.QUIT_CLOSED)
        and asked[0][1] == OTHER
    )
    assert set(sent) == {OTHER}
    assert server._agent_designer(server.PORT) == 11 and not os.path.exists(server.agent_designer_file(OTHER))


@pytest.mark.parametrize('users', [False, True], ids=['an agents', 'the users'])
def test_quit_on_a_port_where_none_runs(monkeypatch: pytest.MonkeyPatch, no_sleep: None, users: bool) -> None:
    # the other Designer, an agent's or the user's listening on its own port, is left alone, and nothing is refused
    processes = _Processes(monkeypatch, 11)
    if users:
        patch_server(monkeypatch, '_listening_ports', lambda pid: {server.PORT})
    else:
        _an_agent_started(11)
    asked = _closes(monkeypatch)
    assert server.quit_designer(port=OTHER).startswith('No Designer is running on port %d.' % OTHER)
    assert not asked and not processes.signals


def test_quit_on_a_port_where_none_runs_reads_each_record_once(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    # ROADMAP item 106: _running_on read every record, then _others read them all again for the same answer, each read
    # listing Designer's processes again
    _Processes(monkeypatch, 11)
    _an_agent_started(11)
    reads = _record_reads(monkeypatch)
    text = server.quit_designer(port=OTHER)
    assert text.startswith('No Designer is running on port %d.' % OTHER), text
    assert '%d (process 11)' % server.PORT in text, text
    assert sorted(reads) == sorted([OTHER, server.PORT]), reads


@pytest.mark.parametrize('port', [0, 80, 1023, 65536, True], ids=str)
@pytest.mark.parametrize(
    'tool',
    [
        lambda port: server.launch_designer(wait_s=30, port=port),
        lambda port: server.designer_status(port=port),
        lambda port: server.quit_designer(port=port),
        lambda port: server.read_designer_log(port=port),
    ],
    ids=['launch_designer', 'designer_status', 'quit_designer', 'read_designer_log'],
)
def test_a_port_out_of_range_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tool: Callable[[int], str], port: int
) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    asked: list[int | None] = []
    patch_server(monkeypatch, '_send', _ports_answering(asked=asked))
    with pytest.raises(server.ToolError, match=r'port must be a number from 1024 to 65535'):
        tool(port)
    assert not started and not asked


def test_listening_ports_are_read_from_lsof(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.undo()  # the real function, with subprocess faked
    seen: list[list[str]] = []
    out = 'p11\nf5\nn127.0.0.1:9877\nf6\nn*:5000\n'

    def run(cmd: list[str], **kw: Unpack[RunOptions]) -> subprocess.CompletedProcess[str]:
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr='')

    monkeypatch.setattr(subprocess, 'run', run)
    assert server._listening_ports(11) == {9877, 5000}
    assert seen[0][0] == 'lsof' and '11' in seen[0] and '-sTCP:LISTEN' in seen[0]
    out = ''
    assert server._listening_ports(11) == set()

    def missing(cmd: list[str], **kw: Unpack[RunOptions]) -> NoReturn:
        raise FileNotFoundError('lsof')

    monkeypatch.setattr(subprocess, 'run', missing)
    assert server._listening_ports(11) == set(), 'not known: as if it listened nowhere yet'


def _launch_on_each_port(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *ports: int) -> list[dict[str, str]]:
    """The environment of the Designer launch_designer starts on each port, the real folders made under tmp_path."""
    for name, real in (('_own_temp', REAL_OWN_TEMP), ('_own_home', REAL_OWN_HOME)):
        patch_server(monkeypatch, name, real)
    patch_server(monkeypatch, 'SHORT_TEMP', str(tmp_path))
    envs = []
    for port in ports:
        _started_with.clear()
        started = _launch_fakes(monkeypatch, tmp_path)
        patch_server(monkeypatch, '_designer_running', lambda: False)
        patch_server(monkeypatch, '_send', _answers_once_started(started))
        server.launch_designer(wait_s=30, port=port)
        envs.append(_started_with[0]['env'])
    return envs


def _own_folder(tmp_path: Path, port: int) -> Path:
    return tmp_path / ('sd_mcp_%d_%d' % (os.getuid(), port))


@pytest.mark.parametrize('platform', _EACH_PLATFORM)
def test_each_designer_started_has_a_temp_folder_of_its_own(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, platform: str
) -> None:
    # measured: a Designer finds one already running through a socket in its temp folder (algipc-...), hands it its
    # arguments and exits, so with the temp folder they share, no second one starts
    monkeypatch.setattr(sys, 'platform', platform)
    monkeypatch.setenv('TMPDIR', '/the/servers/own/')
    temps = [env.get('TMPDIR') for env in _launch_on_each_port(monkeypatch, tmp_path, server.PORT, OTHER)]
    if platform == 'win32':  # a second Designer there hasn't been tried
        assert temps == ['/the/servers/own/'] * 2
        return
    assert temps == [str(_own_folder(tmp_path, port) / 'temp') + os.sep for port in (server.PORT, OTHER)]
    assert all(os.path.isdir(t) for t in temps if t)


@pytest.mark.parametrize('platform', _EACH_PLATFORM)
def test_each_designer_started_on_macos_has_a_home_of_its_own(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, platform: str
) -> None:
    # measured: with CFFIXED_USER_HOME, Designer writes its log, crash dumps and user settings under that folder, and
    # not one byte to the shared log; it then loads user plugins only from SBS_DESIGNER_PYTHON_PATH (its project file's
    # own folder, under the new home, is empty), and the bridge token stays in HOME, which doesn't change
    monkeypatch.setattr(sys, 'platform', platform)
    monkeypatch.delenv('CFFIXED_USER_HOME', raising=False)
    patch_server(monkeypatch, '_plugin_paths', lambda: '/the/plugins')
    envs = _launch_on_each_port(monkeypatch, tmp_path, server.PORT, OTHER)
    if platform != 'darwin':  # a macOS variable (CoreFoundation's)
        assert all('CFFIXED_USER_HOME' not in env and 'SBS_DESIGNER_PYTHON_PATH' not in env for env in envs)
        return
    assert [env['CFFIXED_USER_HOME'] for env in envs] == [
        str(_own_folder(tmp_path, p) / 'home') for p in (server.PORT, OTHER)
    ]
    assert all(os.path.isdir(env['CFFIXED_USER_HOME']) for env in envs)
    assert all(env['SBS_DESIGNER_PYTHON_PATH'] == '/the/plugins' and env['HOME'] == os.environ['HOME'] for env in envs)


def _project_file(data: Path, version: str, *urls: str) -> None:
    """A Designer project file listing these plugin folders, as Designer writes it."""
    folder = data / version
    folder.mkdir(parents=True)
    paths = ''.join('<_%d prefix="_"><url>%s</url></_%d>' % (i, url, i) for i, url in enumerate(urls, 1))
    (folder / 'default_project.sbsprj').write_text(
        '<root><resources><url>file:///not/a/plugin/folder</url></resources>'
        '<python><plugin_paths><size>%d</size>%s</plugin_paths></python></root>' % (len(urls), paths)
    )


def test_the_plugin_folders_are_those_the_users_designer_loads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # install.py --plugins-dir can put the plugin elsewhere: the folders come from the user's own project file (the
    # newest version's), less Designer's own, which it loads anyway; a value of the variable already set is kept,
    # since Designer splits it (measured: ours loaded as the second of two)
    data = tmp_path / 'data'
    _project_file(data, '15.0', 'file:///old/plugins')
    _project_file(
        data,
        '16.0',
        'file:///Users/me/My%20Plugins',
        'file:///Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app/Contents/Resources/python/sdplugins',
        'environment:SBS_DESIGNER_PYTHON_PATH',
    )
    os.utime(data / '15.0', (0, 0))
    patch_server(monkeypatch, '_designer_data_dir', lambda home=None: str(data))
    monkeypatch.delenv('SBS_DESIGNER_PYTHON_PATH', raising=False)
    assert REAL_PLUGIN_PATHS() == '/Users/me/My Plugins'
    monkeypatch.setenv('SBS_DESIGNER_PYTHON_PATH', '/their/own')
    assert REAL_PLUGIN_PATHS() == '/Users/me/My Plugins' + os.pathsep + '/their/own'
    patch_server(monkeypatch, '_designer_data_dir', lambda home=None: str(tmp_path / 'none'))
    monkeypatch.delenv('SBS_DESIGNER_PYTHON_PATH')
    assert REAL_PLUGIN_PATHS() == os.path.join(
        os.path.expanduser('~'), 'Documents', 'Adobe', 'Adobe Substance 3D Designer', 'python', 'sduserplugins'
    ), "no project file yet: Designer's default, where install.py puts it"


@pytest.mark.skipif(sys.platform == 'win32', reason="a Unix socket's path, in a folder named with os.getuid")
def test_the_temp_folder_leaves_room_for_designers_socket() -> None:
    # measured: the socket's name takes 41 bytes with a 5-digit process ID, in the folder's real path (/tmp is
    # /private/tmp), and a socket's whole path at most 103 (104 with its NUL). With too long a path Designer made none
    # (in /var/folders/.../T/sd_mcp_9877/, 110 bytes), and then no other Designer can find it
    folder = os.path.join(os.path.realpath(REAL_SHORT_TEMP), server.agent_folder_name(65535), 'temp')
    assert len(folder) + 1 + 42 <= 103, folder


@pytest.mark.parametrize('kind', ['_own_temp', '_own_home'])
@_SETS_UNIX
def test_a_folder_that_isnt_ours_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str) -> None:
    # /tmp is shared: a folder someone else made there, or a link to one, isn't given to Designer
    monkeypatch.setattr(sys, 'platform', 'darwin')
    patch_server(monkeypatch, kind, {'_own_temp': REAL_OWN_TEMP, '_own_home': REAL_OWN_HOME}[kind])
    patch_server(monkeypatch, 'SHORT_TEMP', str(tmp_path))
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    (tmp_path / server.agent_folder_name(OTHER)).symlink_to(elsewhere)
    # this user's own link: theirs to remove (REVIEW.md TST-186)
    with pytest.raises(server.ToolError, match='not a folder of this user: remove it, then call this again'):
        getattr(server, kind)(OTHER)


@pytest.mark.skipif(sys.platform == 'win32', reason='no owner ID there, and no folder of this kind')
@pytest.mark.parametrize('kind', ['_own_temp', '_own_home'])
def test_a_folder_another_user_owns_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str) -> None:
    # REVIEW.md TST-157: the symlink case above passes without the owner check; a real folder, named for this user but
    # owned by another (here: this user is someone else), is refused by that check alone
    monkeypatch.setattr(sys, 'platform', 'darwin')
    patch_server(monkeypatch, kind, {'_own_temp': REAL_OWN_TEMP, '_own_home': REAL_OWN_HOME}[kind])
    patch_server(monkeypatch, 'SHORT_TEMP', str(tmp_path))
    someone_else = os.getuid() + 1
    monkeypatch.setattr(os, 'getuid', lambda: someone_else)
    (tmp_path / server.agent_folder_name(OTHER)).mkdir()  # named for "this user", owned by the real one
    # in sticky /tmp only its owner can remove it: another port, or that account (REVIEW.md TST-186)
    with pytest.raises(server.ToolError, match='another account owns it') as refused:
        getattr(server, kind)(OTHER)
    assert 'launch on another port' in str(refused.value) and 'remove it, then' not in str(refused.value)


# --- read_designer_log(port): each Designer an agent started writes a log of its own (in its home)


def _logs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    """The shared log, and the log of the Designer an agent starts on OTHER, both written; macOS. Skips on Windows,
    before it says macOS: its folder's name takes os.getuid() (REVIEW.md TST-507)."""
    if sys.platform == 'win32':
        pytest.skip('Windows lacks os.getuid')
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.delenv('SD_DESIGNER_LOG', raising=False)
    patch_server(monkeypatch, 'SHORT_TEMP', str(tmp_path))
    shared = tmp_path / 'user' / 'Library/Application Support/Adobe/Adobe Substance 3D Designer/16.0/log.txt'
    own = (
        _own_folder(tmp_path, OTHER) / 'home/Library/Application Support/Adobe/Adobe Substance 3D Designer/16.0/log.txt'
    )
    for log, who in ((shared, 'the users'), (own, 'the agents')):
        log.parent.mkdir(parents=True)
        log.write_text('[INFO] Python SDK Version 3.13\n[INFO] written by %s\n' % who)
    real = server._designer_data_dir
    patch_server(monkeypatch, '_designer_data_dir', lambda home=None: real(home or str(tmp_path / 'user')))
    return shared, own


def test_the_log_of_a_designer_an_agent_started_is_its_own(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    shared, own = _logs(monkeypatch, tmp_path)
    _Processes(monkeypatch, 11, 12)
    _an_agent_started(12, port=OTHER, home=str(_own_folder(tmp_path, OTHER) / 'home'))
    os.utime(own, (time.time() + 5, time.time() + 5))  # written by it once started, after its record
    patch_server(monkeypatch, '_listening_ports', lambda pid: {server.PORT} if pid == 11 else set())
    text = server.read_designer_log(port=OTHER)
    assert text.startswith(str(own)) and 'written by the agents' in text
    text = server.read_designer_log()  # the user's, on the server's port
    assert text.startswith(str(shared)) and 'written by the users' in text


def test_the_log_of_a_designer_whose_record_goes_after_its_read_is_its_own(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-175: _agent_log looked at the record again, for its age, after _log_for's one read. A record removed
    # between them, by another server's quit once that Designer exited, failed the tool with a raw FileNotFoundError
    _, own = _logs(monkeypatch, tmp_path)
    _Processes(monkeypatch, 12)
    _an_agent_started(12, port=OTHER, home=str(_own_folder(tmp_path, OTHER) / 'home'))
    os.utime(own, (time.time() + 5, time.time() + 5))  # written by it once started, after its record
    reads = _record_reads(monkeypatch, then_gone=True)
    text = server.read_designer_log(port=OTHER)
    assert text.startswith(str(own)) and 'written by the agents' in text and reads == [OTHER], (text, reads)


def test_the_log_of_an_agents_designer_that_has_ended_is_still_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # after a crash is when it is wanted: none runs on the port, and its log is newer than the shared one
    shared, own = _logs(monkeypatch, tmp_path)
    os.utime(shared, (1, 1))
    assert server.read_designer_log(port=OTHER).startswith(str(own))
    os.utime(own, (0, 0))  # older: from an earlier run, and the shared one is the one written since
    assert server.read_designer_log(port=OTHER).startswith(str(shared))


def test_the_users_designer_on_a_port_is_read_from_the_shared_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    shared, own = _logs(monkeypatch, tmp_path)
    os.utime(shared, (0, 0))  # older: by the dates alone, the agent's would be read
    _Processes(monkeypatch, 11)
    patch_server(monkeypatch, '_listening_ports', lambda pid: {OTHER})  # the user's, set to that port
    assert own.exists()
    assert server.read_designer_log(port=OTHER).startswith(str(shared))


def test_a_designer_an_agent_started_without_a_home_is_read_from_the_shared_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # seen in a scratch run: a server running older code starts one with no home of its own, on a port where a home's
    # log is left from an earlier run; that log is stale, and the Designer writes to the shared one
    shared, own = _logs(monkeypatch, tmp_path)
    os.utime(shared, (0, 0))
    _Processes(monkeypatch, 12)
    _an_agent_started(12, port=OTHER)  # recorded with no home
    assert own.exists() and server.read_designer_log(port=OTHER).startswith(str(shared))


@_SETS_UNIX
def test_the_record_says_which_home_the_designer_got(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    monkeypatch.setattr(sys, 'platform', 'darwin')
    processes = _Processes(monkeypatch)
    patch_server(monkeypatch, '_plugin_paths', lambda: '/the/plugins')
    for name, real in (('_own_temp', REAL_OWN_TEMP), ('_own_home', REAL_OWN_HOME)):
        patch_server(monkeypatch, name, real)
    patch_server(monkeypatch, 'SHORT_TEMP', str(tmp_path))
    started = _launch_fakes(monkeypatch, tmp_path)

    monkeypatch.setattr(subprocess, 'Popen', _popen(started, processes=processes))
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    server.launch_designer(wait_s=30, port=OTHER)
    record = read_agent_record(server.agent_designer_file(OTHER))
    assert record['home'] == str(_own_folder(tmp_path, OTHER) / 'home')


# ---- a port another program holds (REVIEW.md SRV-85)
@contextlib.contextmanager
def _held_port(greeting: bytes | None = None) -> Iterator[int]:
    """A port on 127.0.0.1 held by a program that isn't the bridge: it greets each connection with greeting (None:
    says nothing), then reads until the client closes."""
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(8)
    listener.settimeout(0.1)
    stopped = threading.Event()

    def serve() -> None:
        while not stopped.is_set():
            try:
                conn, _ = listener.accept()
            except OSError:
                continue
            with conn:
                conn.settimeout(1)
                with contextlib.suppress(OSError):
                    if greeting is not None:
                        conn.sendall(greeting)
                    while conn.recv(65536):
                        pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1]
    finally:
        stopped.set()
        thread.join(5)
        listener.close()


def test_launch_refuses_a_port_another_program_holds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-85: a Designer started there couldn't listen on it, so the call would wait out wait_s and leave
    # that Designer running
    started = _launch_fakes(monkeypatch, tmp_path)
    _Processes(monkeypatch)
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_bind_error', REAL_BIND_ERROR)  # the fixtures' says every port is free
    with _held_port() as port, pytest.raises(server.ToolError, match='Port %d is held by another program' % port):
        server.launch_designer(wait_s=2, port=port)
    assert started == []


@pytest.mark.parametrize(
    'greeting', [b'{"nonce": "n1"}\n', b'{"protocol": 3}\n'], ids=['older', 'newer, no nonce (REVIEW.md SRV-88)']
)
def test_launch_stops_at_a_plugin_of_another_protocol(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, greeting: bytes
) -> None:
    # REVIEW.md SRV-85, the bridge's side: a plugin greeting with another protocol (older, before REVIEW.md SRV-82)
    # is a Designer answering; waiting for it or starting another wouldn't help
    started = _launch_fakes(monkeypatch, tmp_path)
    _Processes(monkeypatch)
    with _held_port(greeting) as port, pytest.raises(server.ToolError, match='another bridge protocol'):
        server.launch_designer(wait_s=2, port=port)
    assert started == []


def test_a_restart_during_the_wait_refuses_a_port_another_program_holds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md TST-169: the second way into start(): a Designer that isn't answering exits during the wait, and
    # meanwhile another program has the port
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 55)
    calls: list[int] = []

    def bridge(request: Request, wait: float, port: int | None = None) -> NoReturn:
        calls.append(1)
        if len(calls) == 2:  # the first call of the wait: the Designer has gone
            processes.pids.clear()
        raise server.ToolError('Designer is not reachable.')

    patch_server(monkeypatch, '_send', bridge)
    patch_server(monkeypatch, '_bind_error', REAL_BIND_ERROR)  # the fixtures' says every port is free
    with _held_port() as port, pytest.raises(server.ToolError, match='Port %d is held by another program' % port):
        server.launch_designer(wait_s=60, port=port)
    assert started == [] and len(calls) == 2, 'refused at the restart, after one call of the wait'


def test_the_refusal_of_a_held_port_says_why_and_how_to_find_the_holder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-90: the bind's own error, and a hint that also finds another account's listener (lsof without
    # root lists only this account's: measured, two listeners netstat shows that it doesn't name)
    started = _launch_fakes(monkeypatch, tmp_path)
    _Processes(monkeypatch)
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_bind_error', REAL_BIND_ERROR)
    with _held_port() as port, pytest.raises(server.ToolError) as refused:
        server.launch_designer(wait_s=2, port=port)
    message = str(refused.value)
    assert 'Port %d is held by another program' % port in message and 'Address already in use' in message, message
    assert 'sudo lsof -nP -iTCP:%d -sTCP:LISTEN' % port in message, message
    assert started == []


class _BindRefused:
    """A socket whose bind fails as Windows refuses a port in an excluded range (WSAEACCES)."""

    def __init__(
        self,
        family: socket.AddressFamily | int = -1,
        type: socket.SocketKind | int = -1,
        proto: int = -1,
        fileno: int | None = None,
    ) -> None:
        pass

    def __enter__(self) -> '_BindRefused':
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: types.TracebackType | None
    ) -> None:
        pass

    def setsockopt(self, level: int, option: int, value: int | bytes, /) -> None:
        pass

    def bind(self, address: tuple[str, int]) -> None:
        raise PermissionError(13, 'Permission denied')

    def close(self) -> None:
        pass


def test_a_port_that_cant_be_bound_for_another_reason_isnt_blamed_on_a_program(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-90: any failed bind read as another program holding the port
    started = _launch_fakes(monkeypatch, tmp_path)
    _Processes(monkeypatch)
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_bind_error', REAL_BIND_ERROR)
    monkeypatch.setattr(socket, 'socket', _BindRefused)
    with pytest.raises(server.ToolError) as refused:
        server.launch_designer(wait_s=2, port=40000)
    message = str(refused.value)
    assert "Port 40000 can't be used for the bridge ([Errno 13] Permission denied)" in message, message
    assert 'held by another program' not in message, message
    assert started == []


# ---- the record of a Designer an agent started, with servers side by side (REVIEW.md SRV-83)
@_RECORDED
def test_a_record_read_while_it_is_written_isnt_lost(monkeypatch: pytest.MonkeyPatch) -> None:
    # (b): the record was emptied, then written; another server reading it in between deleted it as unreadable, and
    # the write then went into the deleted file
    _Processes(monkeypatch, 77)
    real_dump = json.dump
    read_meanwhile: list[dict[int, int]] = []

    def dump(obj: object, f: IO[str], **kwargs: Unpack[DumpOptions]) -> None:
        read_meanwhile.append(server._agents())  # another server, at the worst moment
        real_dump(obj, f, **kwargs)

    monkeypatch.setattr(json, 'dump', dump)
    server._remember_started(9901, 77, None)
    assert read_meanwhile, 'the record is written with json.dump: the read meanwhile never happened'
    assert server._agent_designer(9901) == 77, 'the record was lost'


@pytest.mark.skipif(sys.platform == 'win32', reason='no ps there, and nothing is recorded')
def test_a_start_time_reads_the_same_whatever_the_servers_locale_and_time_zone(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-92: the record's start is ps's text, compared by other servers with their own; it changed with the
    # locale and the time zone (measured: "Sat Nov  7 13:32:26 2026", "Sa.  7 Nov. 13:32:26 2026" with LC_ALL=de_DE,
    # "Sat Nov  7 11:32:26 2026" with TZ=UTC), so a server in another environment took live records for stale ones
    environments = [
        {'TZ': 'UTC'},
        {'TZ': 'Asia/Tokyo', 'LC_ALL': 'de_DE.UTF-8'},
        {'TZ': 'America/New_York', 'LANG': 'fr_FR.UTF-8'},
    ]
    starts = []
    for env in environments:
        with monkeypatch.context() as m:
            for name in ('LC_ALL', 'LC_TIME', 'LANG', 'TZ'):
                m.delenv(name, raising=False)
            for name, value in env.items():
                m.setenv(name, value)
            starts.append(REAL_PROCESS_START(os.getpid()))
    assert starts[0] and len(set(starts)) == 1, starts


def _relaunched_meanwhile(monkeypatch: pytest.MonkeyPatch, processes: '_Processes', when: Callable[[], bool]) -> None:
    """Another server records its new Designer, 78, on the server's port the first time `when()` holds as the process
    list is read: it holds the port's lock and writes the record whole (REVIEW.md SRV-91)."""
    done: list[bool] = []

    def pids() -> list[int]:
        if not done and when():
            done.append(True)
            processes.pids.append(78)
            server._remember_started(server.PORT, 78, None)
        return list(processes.pids)

    patch_server(monkeypatch, '_designer_pids', pids)


def _recorded_pid() -> int:
    return read_agent_record(server.agent_designer_file(server.PORT))['pid']


@_RECORDED
def test_a_record_replaced_while_it_is_checked_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-91: the record of 77, which has ended, is found stale; meanwhile another server put 78's in place
    processes = _Processes(monkeypatch)
    _an_agent_started(77)
    _relaunched_meanwhile(monkeypatch, processes, lambda: True)
    assert server._agent_designer(server.PORT) is None  # 77's record, read first, was stale
    assert _recorded_pid() == 78 and server._agent_designer(server.PORT) == 78


@_RECORDED
def test_a_record_replaced_while_a_designer_is_forced_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-91: 77 is force-ended; as it goes, another server starts and records 78
    processes = _Processes(monkeypatch, 77)
    _an_agent_started(77)
    _relaunched_meanwhile(monkeypatch, processes, lambda: 77 not in processes.pids)
    assert server._force_end(77, server.PORT, Path(server.agent_designer_file(server.PORT)).read_bytes())
    assert _recorded_pid() == 78


@_RECORDED
def test_a_record_replaced_while_quit_waits_is_kept(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    # REVIEW.md SRV-91: quit_designer's wait sees 77 gone; another server has started and recorded 78 meanwhile
    processes = _Processes(monkeypatch, 77)
    _an_agent_started(77)
    _closes(monkeypatch)

    def gone(seconds: float) -> None:
        if 77 in processes.pids:
            processes.pids.remove(77)

    monkeypatch.setattr(time, 'sleep', gone)
    _relaunched_meanwhile(monkeypatch, processes, lambda: 77 not in processes.pids)
    assert 'Designer quit after' in server.quit_designer()
    assert _recorded_pid() == 78


@pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded there, so nothing is locked')
def test_a_stale_record_is_left_while_a_launch_holds_the_port(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-91: the record is removed only under the port's lock, without waiting for it (a launch holding it
    # sweeps every port's records itself: waiting could deadlock two servers); a stale record left is never matched
    import fcntl

    _Processes(monkeypatch)
    _an_agent_started(77)
    with open(os.path.join(server._own_folder(server.PORT, ''), 'launch.lock'), 'a', encoding='utf-8') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            assert server._agent_designer(server.PORT) is None
            assert _recorded_pid() == 77
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    assert server._agent_designer(server.PORT) is None and not os.path.exists(server.agent_designer_file(server.PORT))


def _starts_77(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[list[list[str]], '_Processes']:
    """launch_designer's fakes, its start giving process 77, running until it gets SIGTERM."""
    monkeypatch.setattr(sys, 'platform', 'darwin')
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch)

    monkeypatch.setattr(subprocess, 'Popen', _popen(started, processes=processes))
    patch_server(monkeypatch, '_send', _no_bridge)
    return started, processes


@_RECORDED
@pytest.mark.parametrize('folder', ['missing', 'read-only'])
def test_no_designer_is_started_where_its_record_cant_be_written(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, folder: str
) -> None:
    # REVIEW.md SRV-93: the record's write failed silently, and "Designer started" was reported: unrecorded, it counted
    # as the user's (quit_designer refused it, launches on other ports were refused naming it)
    started, _ = _starts_77(monkeypatch, tmp_path)
    records = tmp_path / 'records'
    if folder == 'read-only':
        records.mkdir()
        records.chmod(0o500)
    monkeypatch.setitem(vars(project_constants), 'AGENT_RECORD_DIR', str(records))
    try:
        with pytest.raises(server.ToolError, match='its record could not be written') as raised:
            server.launch_designer(wait_s=5)
    finally:
        if folder == 'read-only':
            records.chmod(0o700)
    assert started == [], 'started, though it could not be recorded'
    assert str(records) in str(raised.value)


@_RECORDED
def test_a_designer_whose_record_fails_after_the_start_is_ended(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-93: the folder took a file, then the record itself failed (the disk filled meanwhile): the process
    # just started, the server's own child, is ended rather than left running unrecorded
    started, processes = _starts_77(monkeypatch, tmp_path)

    def full(src: str, dst: str) -> None:
        raise OSError(28, 'No space left on device')

    monkeypatch.setattr(os, 'replace', full)
    with pytest.raises(server.ToolError, match='No space left on device') as raised:
        server.launch_designer(wait_s=5)
    assert started and (77, signal.SIGTERM) in processes.signals and 77 not in processes.pids
    assert 'ended' in str(raised.value)
    record = Path(server.agent_designer_file(server.PORT))
    assert not record.exists() and not list(record.parent.glob(record.name + '.*'))


@pytest.mark.skipif(sys.platform == 'win32', reason='no ps there, and nothing is recorded')
@pytest.mark.parametrize(
    'code, stderr, gone',
    [(1, '', True), (1, 'ps: cannot allocate memory', False), (2, '', False)],
    ids=['no such process', 'failing, exit 1', 'failing, exit 2'],
)
def test_a_failing_ps_is_an_error_not_a_process_gone(
    monkeypatch: pytest.MonkeyPatch, code: int, stderr: str, gone: bool
) -> None:
    # REVIEW.md SRV-97: any empty output was "the process has ended"; measured, ps on an unused process ID exits 1 and
    # says nothing on stderr
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: subprocess.CompletedProcess(cmd, code, '', stderr))
    if gone:
        assert REAL_PROCESS_START(4242) is None
        return
    with pytest.raises(server.ToolError, match="couldn't be read"):
        REAL_PROCESS_START(4242)


def _ps_fails(pid: int) -> NoReturn:
    raise server._NoListing(
        "the start of process %d couldn't be read (ps exit code 1: ps: cannot allocate memory)" % pid
    )


@_RECORDED
def test_a_failing_ps_keeps_a_live_record(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-97: a sweep read the record of a live Designer as stale and removed it; it can't tell, so the
    # record stays (and the Designer isn't taken for an agent's meanwhile)
    _Processes(monkeypatch, 77)
    _an_agent_started(77)
    patch_server(monkeypatch, '_process_start', _ps_fails)
    assert server._agent_designer(server.PORT) is None
    assert os.path.exists(server.agent_designer_file(server.PORT))


@_RECORDED
def test_a_designer_whose_start_cant_be_read_is_ended(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-97: with ps failing as it was recorded, the Designer just started ran unrecorded, silently
    started, processes = _starts_77(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_process_start', _ps_fails)
    with pytest.raises(server.ToolError, match='was started, then ended') as raised:
        server.launch_designer(wait_s=5)
    assert started and (77, signal.SIGTERM) in processes.signals and 'cannot allocate memory' in str(raised.value)


@_RECORDED
def test_a_designer_left_unrecorded_is_reported_when_its_end_cant_be_seen(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-100: the machine unable to fork, ps fails (no record) and then pgrep (its end can't be seen): the
    # error said only that processes couldn't be listed, not that a Designer was started and left unrecorded
    started, processes = _starts_77(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_process_start', _ps_fails)

    def pids() -> list[int]:
        if started:  # once it is started, pgrep fails too, its end included
            raise server._NoListing("Designer's processes couldn't be listed (pgrep exit code 3: fork failed)")
        return list(processes.pids)

    patch_server(monkeypatch, '_designer_pids', pids)
    with pytest.raises(server.ToolError, match='could not be ended') as raised:
        server.launch_designer(wait_s=5)
    assert started and 'kill -9 77' in str(raised.value) and (77, signal.SIGTERM) in processes.signals


@_RECORDED
def test_a_designer_is_recorded_even_when_its_reaper_cant_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-100: a thread that can't start (no resources) after Popen left start() before the record, the
    # Designer running unrecorded; the thread only reaps the child when it ends
    started, _ = _starts_77(monkeypatch, tmp_path)

    class NoThread:  # threading.Thread, called as launch_designer calls it
        def __init__(self, target: Callable[[], object] | None = None, *, daemon: bool | None = None) -> None:
            pass

        def start(self) -> None:
            raise RuntimeError("can't start new thread")

    monkeypatch.setitem(vars(server_tools.lifecycle), 'threading', types.SimpleNamespace(Thread=NoThread))
    with pytest.raises(server.ToolError, match='did not answer'):  # it starts, and never answers here
        server.launch_designer(wait_s=5)
    assert started and _recorded_pid() == 77


@pytest.mark.skipif(sys.platform == 'win32', reason='macOS: the homes of its own are there')
def test_a_log_older_than_the_designer_on_its_port_is_not_yet_its(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-99: the port's folder outlives a quit, so a Designer just relaunched there was given the earlier
    # run's log as its own until it wrote to it
    _, own = _logs(monkeypatch, tmp_path)
    os.utime(own, (1, 1))  # the earlier run's
    _Processes(monkeypatch, 12)
    _an_agent_started(12, port=OTHER, home=str(_own_folder(tmp_path, OTHER) / 'home'))  # recorded now
    with pytest.raises(server.ToolError, match='has no log yet'):
        server.read_designer_log(port=OTHER)
    own.write_text(own.read_text() + '[INFO] Python SDK Version 3.13\n')  # it starts writing
    assert server.read_designer_log(port=OTHER).startswith(str(own))


@pytest.mark.skipif(sys.platform == 'win32', reason='tasklist, not pgrep, lists them on Windows')
def test_a_failed_process_listing_keeps_a_live_record(monkeypatch: pytest.MonkeyPatch) -> None:
    # (c): pgrep failing (exit code 2 or 3, not 1 for nothing found) gave an empty list, and the record of a Designer
    # still running was deleted
    patch_server(monkeypatch, '_designer_pids', REAL_DESIGNER_PIDS)
    patch_server(monkeypatch, '_process_start', lambda pid: 'started 77' if pid == 77 else None)
    monkeypatch.setattr(
        subprocess, 'run', lambda cmd, **kw: subprocess.CompletedProcess(cmd, 2, '', 'pgrep: cannot allocate memory')
    )
    _an_agent_started(77, port=9901)
    assert server._agent_designer(9901) == 77, 'its start time still matches: it is the one recorded'
    assert os.path.exists(server.agent_designer_file(9901))


_NOT_LISTED = "Designer's processes couldn't be listed"


def _pgrep_failing(monkeypatch: pytest.MonkeyPatch, failing: str = 'exit code 3') -> list[list[str]]:
    """The real process checks, with pgrep failing: its own errors (exit code 2 or 3; 1 is nothing found) or missing.
    Returns the commands run; any other than pgrep fails the test."""
    patch_server(monkeypatch, '_designer_pids', REAL_DESIGNER_PIDS)
    patch_server(monkeypatch, '_designer_running', REAL_DESIGNER_RUNNING)
    ran: list[list[str]] = []

    def run(cmd: list[str], **kw: Unpack[RunOptions]) -> 'subprocess.CompletedProcess[str]':
        ran.append(cmd)
        assert cmd[0] == 'pgrep', cmd
        if failing == 'missing':
            raise FileNotFoundError(errno.ENOENT, 'No such file or directory', 'pgrep')
        return subprocess.CompletedProcess(cmd, int(failing.split()[-1]), '', 'pgrep: fork failed')

    monkeypatch.setattr(subprocess, 'run', run)
    return ran


@pytest.mark.skipif(sys.platform == 'win32', reason='tasklist, not pgrep, lists them on Windows')
@pytest.mark.parametrize('failing', ['exit code 2', 'exit code 3', 'missing'])
def test_a_failed_process_listing_isnt_read_as_no_designer_running(
    monkeypatch: pytest.MonkeyPatch, failing: str
) -> None:
    # REVIEW.md SRV-163: _designer_running read only pgrep's exit code 0, so its own errors read as none running
    _pgrep_failing(monkeypatch, failing)
    with pytest.raises(server.ToolError, match=_NOT_LISTED):
        server._designer_running()
    with pytest.raises(server.ToolError, match=_NOT_LISTED):
        server._running_on(OTHER)


@pytest.mark.skipif(sys.platform == 'win32', reason='tasklist, not pgrep, lists them on Windows')
@pytest.mark.parametrize(('code', 'running'), [(0, True), (1, False)], ids=['found', 'nothing found'])
def test_pgrep_finding_designer_or_nothing_reads_as_running_or_not(
    monkeypatch: pytest.MonkeyPatch, code: int, running: bool
) -> None:
    patch_server(monkeypatch, '_designer_running', REAL_DESIGNER_RUNNING)
    monkeypatch.setattr(
        subprocess, 'run', lambda cmd, **kw: subprocess.CompletedProcess(cmd, code, '4242\n' if code == 0 else '', '')
    )
    assert server._designer_running() is running


@pytest.mark.skipif(sys.platform == 'win32', reason='tasklist, not pgrep, lists them on Windows')
def test_a_quit_with_the_processes_unlisted_doesnt_say_none_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-163: with no record, quit_designer said "Designer is not running." while one may run
    _pgrep_failing(monkeypatch)
    with pytest.raises(server.ToolError, match=_NOT_LISTED):
        server.quit_designer()


@pytest.mark.skipif(sys.platform == 'win32', reason='tasklist, not pgrep, lists them on Windows')
def test_a_launch_with_the_processes_unlisted_starts_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-163: none read running, so the launch went on to start one; _users_next_to's listing refused it
    started = _launch_fakes(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_send', _no_bridge)
    _pgrep_failing(monkeypatch)
    with pytest.raises(server.ToolError, match=_NOT_LISTED):
        server.launch_designer(wait_s=30)
    assert started == []


def test_the_log_with_the_processes_unlisted_isnt_chosen_as_none_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-163: none read running, so the log of an agent's Designer that ended was taken for the port's
    _logs(monkeypatch, tmp_path)
    _pgrep_failing(monkeypatch)
    with pytest.raises(server.ToolError, match=_NOT_LISTED):
        server.read_designer_log(port=OTHER)


@pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded on Windows, so nothing is locked there')
def test_two_launches_on_one_port_at_once_start_one_designer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # (a): both saw no Designer and both started one; the second hands over to the first and exits, and its record
    # replaced the first's
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch)
    both_in = threading.Barrier(2, timeout=1)  # holds a start until the other launch is starting too, if it can be

    def begin(cmd: list[str], **kw: Unpack[_PopenArgs]) -> _FakeProcess:
        pid = 77 + len(started)
        started.append(cmd)
        processes.pids.append(pid)
        with contextlib.suppress(threading.BrokenBarrierError):
            both_in.wait()
        return _FakeProcess(pid)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    results: list[str] = []
    launches = [threading.Thread(target=lambda: results.append(server.launch_designer(wait_s=30))) for _ in range(2)]
    for launch in launches:
        launch.start()
    for launch in launches:
        launch.join(20)
    assert len(started) == 1, '%d Designers started' % len(started)
    assert sorted(r.split(' in ')[0].split(' on ')[0] for r in results) == [
        'Designer already running',
        'Designer started',
    ], results
    assert server._agent_designer(server.PORT) == 77


def _started_on(log: Path, port: int) -> None:
    """A log whose last start is a Designer whose plugin listened on `port`, as the plugin logs it."""
    log.write_text(
        '[INFO] Python SDK Version 3.13\n[INFO][Python] [%s] v4 listening on 127.0.0.1:%d\n' % (PLUGIN, port)
    )


def test_an_ended_agents_log_is_read_while_the_users_designer_writes_the_shared_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-84: an agent's Designer on OTHER crashed, the user's runs on the server's port: the shared log is
    # newer, but its last start says it isn't OTHER's
    shared, own = _logs(monkeypatch, tmp_path)
    _started_on(shared, server.PORT)
    os.utime(own, (1, 1))
    _Processes(monkeypatch, 11)
    patch_server(monkeypatch, '_listening_ports', lambda pid: {server.PORT})
    assert server.read_designer_log(port=OTHER).startswith(str(own))


@pytest.mark.skipif(sys.platform == 'win32', reason='macOS: the homes of its own are there')
@pytest.mark.parametrize('running', [False, True], ids=['none on the port', 'an agents on the port'])
def test_a_port_folder_another_account_owns_is_never_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, running: bool
) -> None:
    # REVIEW.md SRV-96: /tmp is shared: another account can make the port's folder first, with a log.txt of its own
    # text, which read_designer_log(port) showed (here this user is someone else, and the folder is the real user's)
    someone_else = os.getuid() + 1
    monkeypatch.setattr(os, 'getuid', lambda: someone_else)
    shared, _ = _logs(monkeypatch, tmp_path)  # the port's folder, named for "this user", owned by the real one
    _started_on(shared, server.PORT)
    os.utime(shared, (1, 1))
    _Processes(monkeypatch, *([11, 12] if running else [11]))  # 11: the user's, on the server's port
    patch_server(monkeypatch, '_listening_ports', lambda pid: {server.PORT} if pid == 11 else set())
    if running:
        _an_agent_started(12, port=OTHER, home=str(_own_folder(tmp_path, OTHER) / 'home'))
        with pytest.raises(server.ToolError, match='not a folder of this user'):
            server.read_designer_log(port=OTHER)
        return
    text = server.read_designer_log(port=OTHER)
    assert text.startswith(str(shared)) and 'written by the agents' not in text, text


@pytest.mark.skipif(sys.platform == 'win32', reason='macOS: the homes of its own are there')
def test_a_log_that_is_a_link_is_never_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md SRV-96: a log.txt linked to another file (the bridge token) was read through the link; Designer writes
    # its log as a file
    shared, own = _logs(monkeypatch, tmp_path)
    secret = tmp_path / 'token'
    secret.write_text('SECRET-TOKEN\n')
    own.unlink()
    own.symlink_to(secret)
    _started_on(shared, server.PORT)
    os.utime(shared, (1, 1))
    _Processes(monkeypatch, 11)
    patch_server(monkeypatch, '_listening_ports', lambda pid: {server.PORT})
    text = server.read_designer_log(port=OTHER)
    assert 'SECRET-TOKEN' not in text and text.startswith(str(shared)), text


def test_the_shared_log_is_read_when_the_users_designer_was_last_on_that_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # the other side of SRV-84: the user's Designer ran on OTHER after the agent's did; none runs now
    shared, own = _logs(monkeypatch, tmp_path)
    _started_on(shared, OTHER)
    os.utime(own, (1, 1))
    _Processes(monkeypatch)
    assert server.read_designer_log(port=OTHER).startswith(str(shared))


def test_an_agents_designer_with_no_log_yet_isnt_read_from_the_shared_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-84: just started, it hasn't written its own log yet; the shared one is the user's
    _shared, own = _logs(monkeypatch, tmp_path)
    own.unlink()
    _Processes(monkeypatch, 12)
    _an_agent_started(12, port=OTHER, home=str(_own_folder(tmp_path, OTHER) / 'home'))
    with pytest.raises(server.ToolError, match='no log yet'):
        server.read_designer_log(port=OTHER)


# ---- the folders and the plugin path, when something is off (REVIEW.md SRV-86)
@pytest.mark.parametrize('how', ['mkdir fails', 'a file in the way'])
@pytest.mark.parametrize('kind', ['_own_temp', '_own_home'])
@_SETS_UNIX
def test_a_folder_that_cant_be_made_is_refused_naming_the_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str, how: str
) -> None:
    # only a link or another owner was a ToolError; a full or read-only /tmp, or a file named temp or home, escaped
    # as a plain OSError
    monkeypatch.setattr(sys, 'platform', 'darwin')
    patch_server(monkeypatch, kind, {'_own_temp': REAL_OWN_TEMP, '_own_home': REAL_OWN_HOME}[kind])
    patch_server(monkeypatch, 'SHORT_TEMP', str(tmp_path))
    if how == 'mkdir fails':

        def refuse(path: str | os.PathLike[str], mode: int = 0o777) -> None:
            raise PermissionError(13, 'Permission denied', str(path))

        monkeypatch.setattr(os, 'mkdir', refuse)
    else:
        folder = tmp_path / server.agent_folder_name(OTHER)
        folder.mkdir(mode=0o700)
        (folder / {'_own_temp': 'temp', '_own_home': 'home'}[kind]).write_text('')
    with pytest.raises(server.ToolError, match='No folder for the Designer on port %d' % OTHER):
        getattr(server, kind)(OTHER)


@pytest.mark.parametrize('content', ['unreadable', 'malformed'])
def test_a_project_file_that_cant_be_read_gives_designers_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, content: str
) -> None:
    data = tmp_path / 'data'
    _project_file(data, '16.0', 'file:///Users/me/plugins')
    project = data / '16.0' / 'default_project.sbsprj'
    if content == 'unreadable':
        project.chmod(0)
    else:
        project.write_text('<root><python><plugin_paths><url>file:///Users/me/plugins</url>')
    patch_server(monkeypatch, '_designer_data_dir', lambda home=None: str(data))
    monkeypatch.delenv('SBS_DESIGNER_PYTHON_PATH', raising=False)
    try:
        assert REAL_PLUGIN_PATHS() == os.path.join(
            os.path.expanduser('~'), 'Documents', 'Adobe', 'Adobe Substance 3D Designer', 'python', 'sduserplugins'
        )
    finally:
        project.chmod(0o600)


def test_a_plugin_folder_with_an_xml_entity_is_decoded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # the project file is XML, and Designer writes folders raw (spaces as spaces): a & in one is stored as &amp;
    data = tmp_path / 'data'
    _project_file(data, '16.0', 'file:///Users/me/A&amp;B plugins')
    patch_server(monkeypatch, '_designer_data_dir', lambda home=None: str(data))
    monkeypatch.delenv('SBS_DESIGNER_PYTHON_PATH', raising=False)
    assert REAL_PLUGIN_PATHS() == '/Users/me/A&B plugins'


def test_no_unit_test_sees_a_designer_really_running(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-147: the autouse fixture replaced _designer_pids but not _designer_running, which ran the real
    # pgrep; with a Designer open, a test that set up no processes took it as one that may hold any port
    monkeypatch.setattr(
        subprocess,
        'run',
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, '4242\n', ''),  # as pgrep answers with a Designer open
    )
    assert server._designer_pids() == []
    assert server._designer_running() is False


def test_no_unit_test_reads_the_users_project_file(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-379: a launch with a home of its own read the plugin folders from the user's newest project file, in
    # their Designer's folder
    patch_server(monkeypatch, '_designer_data_dir', lambda home=None: pytest.fail("the user's Designer folder read"))
    assert server._plugin_paths()


# --- Designer's preferences plist, saved as an agent's Designer starts, put back once none runs (ROADMAP item 67)

_USERS: dict[str, Plist] = {
    'session.mainWindow.state': b"the user's layout",
    'session.lastSession.files': ['/Users/me/brick.sbs'],
}
_MACOS_PLIST = pytest.mark.skipif(sys.platform != 'darwin', reason='the preferences plist is macOS only')
_PUT_BACK = "Designer's preferences put back from their copy"
_NOT_SAVED = (
    "Designer's preferences couldn't be saved first (defaults export: exit code 1): if a Designer is started now, its "
    "changes to them won't be put back."
)


def _saved_as_by_a_launch(defaults: FakeDefaults, hours_ago: float = 0) -> None:
    """The user's file as it was, saved as a launch saves it (`hours_ago`), then changed as an agent's Designer may."""
    defaults.domain = dict(_USERS)
    with designer_preferences.saved(lambda: False, ended=False):
        pass
    at = time.time() - hours_ago * 3600
    os.utime(designer_preferences.saved_file(), (at, at))
    defaults.domain['session.instancePID'] = 11
    defaults.domain['session.mainWindow.state'] = b'floating'


@_MACOS_PLIST
def test_launch_saves_designers_preferences_before_its_designer_starts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    defaults.domain = dict(_USERS)
    copies: list[dict[str, Plist]] = []
    locked: list[bool] = []

    def at_start() -> None:
        with open(designer_preferences.saved_file(), 'rb') as f:
            copies.append(plistlib.load(f))
        # and held till it is started: a put-back finding none running meanwhile would drop the copy
        locked.append(lock_held())

    said = _launch_with_home(monkeypatch, tmp_path, tmp_path / 'home', at_start=at_start)
    assert copies == [_USERS] and locked == [True], 'saved before it starts, held while it starts'
    assert said.startswith('Designer started in') and 'preferences' not in said, said


@_MACOS_PLIST
def test_a_launch_that_times_out_still_says_what_its_save_did(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    defaults.fail['export'] = 'defaults export: exit code 1'
    started: list[list[str]] = []
    patch_server(monkeypatch, '_send', _no_bridge)
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', _popen(started))
    patch_server(monkeypatch, '_own_home', lambda port: str(tmp_path / 'home'))
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    assert started and str(raised.value).startswith(_NOT_SAVED + '\nDesigner did not answer within 30s'), raised.value


@_MACOS_PLIST
def test_a_launch_whose_designer_exits_during_the_wait_puts_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    # REVIEW.md SRV-135: it crashed as it started; none runs then, and no quit follows
    defaults.domain = dict(_USERS)
    started: list[list[str]] = []

    def changes(cmd: list[str]) -> list[str]:
        defaults.domain['session.instancePID'] = 77  # as it starts, before it crashes
        return cmd

    patch_server(monkeypatch, '_send', _no_bridge)
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', _popen(started, entry=changes))  # no process listed: it is gone
    patch_server(monkeypatch, '_own_home', lambda port: str(tmp_path / 'home'))
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    assert started and defaults.domain == _USERS, raised.value
    said = str(raised.value)
    assert said.startswith(_PUT_BACK) and '\nDesigner did not answer within 30s' in said, said


@_MACOS_PLIST
@pytest.mark.parametrize('after', ['a refusal', 'the Home screen failing'])
def test_a_launch_that_fails_once_started_still_says_what_its_save_did(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults, after: str
) -> None:
    # REVIEW.md SRV-129
    defaults.fail['export'] = 'defaults export: exit code 1'
    with pytest.raises(server.ToolError) as raised:
        _launch_with_home(
            monkeypatch,
            tmp_path,
            tmp_path / 'home',
            refuses=after == 'a refusal',
            home_screen=server.ToolError('the Home screen could not be left') if after != 'a refusal' else None,
        )
    assert str(raised.value).startswith(_NOT_SAVED + '\n'), raised.value
    assert isinstance(raised.value, server._Refused) == (after == 'a refusal'), 'a refusal still raised as one'


@_MACOS_PLIST
def test_a_launch_whose_designer_cant_be_started_still_says_what_its_save_did(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    # REVIEW.md SRV-129: a copy left behind put back, then the process doesn't start
    _saved_as_by_a_launch(defaults)
    _launch_fakes(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_own_home', lambda port: str(tmp_path / 'home'))

    def fails(cmd: list[str], **kw: Unpack[_PopenArgs]) -> NoReturn:
        raise PermissionError(13, 'Permission denied')

    monkeypatch.setattr(subprocess, 'Popen', fails)
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    assert defaults.domain == _USERS
    # the copy its start made: none started on it, and none would put it back (REVIEW.md SRV-138)
    assert not os.path.exists(designer_preferences.saved_file()), raised.value
    assert str(raised.value).startswith(_PUT_BACK) and '\nDesigner could not be started from' in str(raised.value), (
        raised.value
    )


def _unrecorded(port: int, pid: int, home: str | None) -> NoReturn:
    raise OSError(28, 'No space left on device')


@_MACOS_PLIST
@pytest.mark.parametrize('ended', [True, False], ids=['then ended', 'not ended'])
def test_a_launch_it_couldnt_record_still_says_what_its_save_did(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults, ended: bool
) -> None:
    # REVIEW.md TST-358, TST-368: told() in both raises after a start
    defaults.fail['export'] = 'defaults export: exit code 1'
    patch_server(monkeypatch, '_remember_started', _unrecorded)
    patch_server(monkeypatch, '_force_end', lambda pid, port, seen: ended)
    with pytest.raises(server.ToolError) as raised:
        _launch_with_home(monkeypatch, tmp_path, tmp_path / 'home')
    how = 'was started, then ended' if ended else 'was started and could not be ended'
    assert str(raised.value).startswith(_NOT_SAVED + '\nDesigner (process 77) ' + how), raised.value


@_MACOS_PLIST
def test_a_launch_that_ends_the_designer_it_couldnt_record_puts_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    # REVIEW.md SRV-135: none of its Designers runs then, and no quit follows
    defaults.domain = dict(_USERS)
    patch_server(monkeypatch, '_remember_started', _unrecorded)

    def end(pid: int, port: int, seen: bytes) -> bool:
        patch_server(monkeypatch, '_designer_pids', list)  # it is gone
        return True

    patch_server(monkeypatch, '_force_end', end)
    with pytest.raises(server.ToolError) as raised:
        _launch_with_home(
            monkeypatch,
            tmp_path,
            tmp_path / 'home',
            at_start=lambda: defaults.domain.update({'session.instancePID': 77}),
        )
    said = str(raised.value)
    assert defaults.domain == _USERS and said.startswith(_PUT_BACK), said
    assert '\nDesigner (process 77) was started, then ended' in said, said


@_MACOS_PLIST
def test_a_launch_ends_the_designer_it_couldnt_record_before_letting_the_preferences_lock_go(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    # REVIEW.md SRV-144: running unrecorded once that lock goes, another launch's look would take it for the user's
    defaults.domain = dict(_USERS)
    patch_server(monkeypatch, '_remember_started', _unrecorded)
    locked: list[bool] = []

    def end(pid: int, port: int, seen: bytes) -> bool:
        locked.append(lock_held())
        patch_server(monkeypatch, '_designer_pids', list)  # it is gone
        return True

    patch_server(monkeypatch, '_force_end', end)
    with pytest.raises(server.ToolError) as raised:
        _launch_with_home(monkeypatch, tmp_path, tmp_path / 'home')
    assert locked == [True], raised.value
    assert str(raised.value).startswith('Designer (process 77) was started, then ended'), raised.value


@_MACOS_PLIST
def test_a_launch_whose_save_and_start_fail_speaks_of_no_designer_it_started(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    # REVIEW.md SRV-145: "this Designer's changes" was said just before saying none was started
    defaults.fail['export'] = 'defaults export: exit code 1'
    _launch_fakes(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_own_home', lambda port: str(tmp_path / 'home'))

    def fails(cmd: list[str], **kw: Unpack[_PopenArgs]) -> NoReturn:
        raise PermissionError(13, 'Permission denied')

    monkeypatch.setattr(subprocess, 'Popen', fails)
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    assert str(raised.value).startswith(_NOT_SAVED + '\nDesigner could not be started from'), raised.value


def _no_home(port: int) -> NoReturn:
    raise server.ToolError('its folder is not one launch_designer made')


@_MACOS_PLIST
def test_a_launch_that_ended_a_designer_and_starts_none_says_its_put_backs_in_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    # REVIEW.md SRV-138: the put-back before the start failing, the start failing, then the put-back after it working:
    # said as they happened, the last word not that the copy is kept
    _saved_as_by_a_launch(defaults)
    _launch_fakes(monkeypatch, tmp_path)
    _Processes(monkeypatch, 11)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1, home=str(tmp_path / 'home'))
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_own_home', lambda port: str(tmp_path / 'home'))
    defaults.fail['import'] = 'the disk is full'

    def fails(cmd: list[str], **kw: Unpack[_PopenArgs]) -> NoReturn:
        del defaults.fail['import']  # the next put-back works
        raise PermissionError(13, 'Permission denied')

    monkeypatch.setattr(subprocess, 'Popen', fails)
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    said = str(raised.value)
    assert defaults.domain == _USERS and not os.path.exists(designer_preferences.saved_file()), said
    failed, put_back, start = (
        said.find(text)
        for text in (
            "couldn't be put back (the disk is full)",
            "Designer's preferences put back from",
            'Designer could not be started',
        )
    )
    assert said.startswith('Ended a Designer an agent started') and -1 < failed < put_back < start, said


@_MACOS_PLIST
def test_a_launch_refuses_once_a_designer_starts_during_its_put_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    # REVIEW.md SRV-139: the user's (other launches wait for the lock), not yet listening anywhere: it stops the
    # put-back of a copy left behind, and none is started next to it, as none is next to one already running
    _saved_as_by_a_launch(defaults)
    _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch)
    patch_server(monkeypatch, '_send', _no_bridge)  # not the real port, where a Designer may answer (REVIEW.md TST-376)
    patch_server(monkeypatch, '_own_home', lambda port: str(tmp_path / 'home'))
    patch_server(monkeypatch, '_listening_ports', lambda pid: set())

    def as_the_user_opens_theirs(*args: str) -> bytes:
        if args[0] == 'delete':
            processes.pids.append(555)
        return defaults(*args)

    monkeypatch.setitem(vars(designer_preferences), 'run_defaults', as_the_user_opens_theirs)

    def starts(cmd: list[str], **kw: Unpack[_PopenArgs]) -> NoReturn:
        raise AssertionError('started next to the Designer that appeared')

    monkeypatch.setattr(subprocess, 'Popen', starts)
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    said = str(raised.value)
    assert said.startswith(
        "Designer's preferences couldn't be put back (a Designer started meanwhile, or Designers couldn't be listed)"
    ), said
    assert '\nA Designer started as this one was about to (process 555): none is started next to it' in said, said


@_MACOS_PLIST
def test_a_launch_records_its_designer_before_letting_the_preferences_lock_go(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    # REVIEW.md SRV-141: another server's launch, which waits for that lock, would otherwise find it unrecorded,
    # listening nowhere yet, and take it for the user's (_appeared)
    defaults.domain = dict(_USERS)
    locked: list[bool] = []
    remember = server._remember_started

    def recorded(port: int, pid: int, home: str | None) -> None:
        locked.append(lock_held())
        remember(port, pid, home)

    patch_server(monkeypatch, '_remember_started', recorded)
    said = _launch_with_home(monkeypatch, tmp_path, tmp_path / 'home')
    assert locked == [True] and said.startswith('Designer started in'), said


@_MACOS_PLIST
def test_a_launch_refuses_a_designer_that_appears_as_it_starts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    # REVIEW.md SRV-141: every launch records its Designer before that lock goes, so one that appears meanwhile, not
    # recorded, is the user's, also when nothing was put back or saved again
    defaults.domain = dict(_USERS)
    _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch)
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_own_home', lambda port: str(tmp_path / 'home'))
    lock = designer_preferences._lock

    def as_the_user_opens_theirs() -> IO[str]:
        held = lock()
        processes.pids.append(555)
        return held

    monkeypatch.setitem(vars(designer_preferences), '_lock', as_the_user_opens_theirs)

    def starts(cmd: list[str], **kw: Unpack[_PopenArgs]) -> NoReturn:
        raise AssertionError('started next to the Designer that appeared')

    monkeypatch.setattr(subprocess, 'Popen', starts)
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    said = str(raised.value)
    assert said.startswith('A Designer started as this one was about to (process 555): none is started'), said
    assert not os.path.exists(designer_preferences.saved_file()), 'the copy saved for it removed (SRV-138)'


@_MACOS_PLIST
def test_a_launch_without_the_preferences_lock_takes_no_designer_for_the_users(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    # REVIEW.md SRV-141: without that lock no launch waits for another, so one another server has just started, not yet
    # recorded, can't be told from the user's; and nothing was put back meanwhile
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    patch_server(monkeypatch, '_own_home', lambda port: str(tmp_path / 'home'))

    def no_lock() -> NoReturn:
        processes.pids.append(556)  # another server's, started as this launch looks
        raise PermissionError(13, 'Permission denied')

    monkeypatch.setitem(vars(designer_preferences), '_lock', no_lock)
    said = server.launch_designer(wait_s=30)
    assert started and said.startswith(
        "Designer's preferences couldn't be saved first ([Errno 13] Permission denied)"
    ), said


@_MACOS_PLIST
@pytest.mark.parametrize(
    'refusal', ['port taken', 'not found', "the user's next to it", 'no record', 'no home', 'processes unlisted']
)
def test_a_launch_that_ended_a_designer_and_starts_none_puts_back_first(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults, refusal: str
) -> None:
    # REVIEW.md SRV-130, SRV-135, TST-368: it ended an agent's hung Designer, then refuses: none runs, and nothing else
    # would put the file back before the user's Designer next reads it; the copy old, as a Designer has just ended
    _saved_as_by_a_launch(defaults, hours_ago=designer_preferences.LEFTOVER_HOURS + 1)
    _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1, home=str(tmp_path / 'home'))
    patch_server(monkeypatch, '_send', _no_bridge)
    if refusal == 'port taken':
        patch_server(monkeypatch, '_bind_error', lambda port: OSError(errno.EADDRINUSE, 'Address already in use'))
    elif refusal == 'not found':
        monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path / 'no Designer here'))
    elif refusal == "the user's next to it":
        patch_server(monkeypatch, '_users_next_to', lambda port, note: server.ToolError("the user's Designer runs"))
    elif refusal == 'no record':
        patch_server(monkeypatch, '_record_error', lambda port: PermissionError(13, 'Permission denied'))
    elif refusal == 'processes unlisted':  # REVIEW.md SRV-164: the listing's error said nothing of the Designer ended

        def unlisted(port: int, note: str) -> NoReturn:
            raise server._NoListing("Designer's processes couldn't be listed (pgrep exit code 3: fork failed)")

        patch_server(monkeypatch, '_users_next_to', unlisted)
    else:  # before saved(): _own_home or _own_temp refusing the port's folder
        patch_server(monkeypatch, '_own_home', _no_home)
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    assert not processes.pids and defaults.domain == _USERS, raised.value
    said = str(raised.value)
    assert said.startswith('Ended a Designer an agent started') and ('\n' + _PUT_BACK) in said, said
    why = {
        'port taken': 'is held by another program',
        'not found': 'Designer not found at',
        "the user's next to it": "the user's Designer runs",
        'no record': 'its record could not be written',
        'no home': 'its folder is not one launch_designer made',
        'processes unlisted': "Designer's processes couldn't be listed",
    }
    assert why[refusal] in said, said


@_MACOS_PLIST
def test_a_launch_that_ended_a_designer_puts_back_an_old_copy_before_its_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    # REVIEW.md TST-368: launch_designer passes ended=True when it ended one: that one's changes are fresh, however old
    # the copy
    _saved_as_by_a_launch(defaults, hours_ago=designer_preferences.LEFTOVER_HOURS + 1)
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1, home=str(tmp_path / 'home'))
    patch_server(monkeypatch, '_own_home', lambda port: str(tmp_path / 'home'))
    at_the_start: list[dict[str, Plist]] = []

    def begin(cmd: list[str], **kw: Unpack[_PopenArgs]) -> _FakeProcess:
        at_the_start.append(dict(defaults.domain))
        started.append(cmd)
        processes.pids.append(77)
        return _FakeProcess(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    said = server.launch_designer(wait_s=30)
    assert at_the_start == [_USERS], said
    assert said.startswith('Ended a Designer an agent started') and ('\n' + _PUT_BACK) in said, said


def test_launch_of_a_designer_without_a_home_of_its_own_saves_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults
) -> None:
    # off macOS: no plist, and every Designer counts as the user's
    _launch_with_home(monkeypatch, tmp_path, None)
    assert not defaults.calls and not os.path.exists(designer_preferences.saved_file())


@_MACOS_PLIST
@pytest.mark.parametrize('old', [False, True], ids=['young', 'old'])
def test_launch_puts_back_a_copy_left_by_designers_ended_outside_the_tools(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults, old: bool
) -> None:
    # a Designer an agent started crashed, or was ended outside quit_designer: none runs now; past LEFTOVER_HOURS the
    # user may have worked since, so it is dropped (REVIEW.md TST-368: the launch passes ended=False when it ended none)
    _saved_as_by_a_launch(defaults, hours_ago=designer_preferences.LEFTOVER_HOURS + 1 if old else 0)
    changed = dict(defaults.domain)
    at_the_start: list[dict[str, Plist]] = []
    said = _launch_with_home(
        monkeypatch, tmp_path, tmp_path / 'home', at_start=lambda: at_the_start.append(dict(defaults.domain))
    )
    assert at_the_start == [changed if old else _USERS], 'put back before the next one starts, if young enough'
    done = "Designer's preferences left as they are: their copy" if old else _PUT_BACK
    assert said.startswith(done), 'said first, as it happened first: %s' % said


@_MACOS_PLIST
@pytest.mark.parametrize('closes', [True, False], ids=['closes', 'forced'])
def test_quit_puts_designers_preferences_back_once_its_designer_has_ended(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults, closes: bool
) -> None:
    # however old the copy: its Designer has just ended through the tools (an agent's long session)
    _saved_as_by_a_launch(defaults, hours_ago=designer_preferences.LEFTOVER_HOURS + 5)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, home=str(tmp_path / 'home'))
    _closes(monkeypatch)
    if closes:
        monkeypatch.setattr(time, 'sleep', lambda seconds: processes.pids.clear())
    said = server.quit_designer(wait_s=2)
    assert defaults.domain == _USERS and not os.path.exists(designer_preferences.saved_file())
    assert 'Designer quit after' in said and said.endswith(
        _PUT_BACK + ': 1 key added since removed and 1 value put back.'
    ), said


@_MACOS_PLIST
def test_quit_leaves_designers_preferences_while_another_designer_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, defaults: FakeDefaults
) -> None:
    _saved_as_by_a_launch(defaults)
    changed = dict(defaults.domain)
    processes = _Processes(monkeypatch, 11, 12)
    _an_agent_started(12, home=str(tmp_path / 'home'))
    _closes(monkeypatch)
    monkeypatch.setattr(time, 'sleep', lambda seconds: processes.pids.remove(12) if 12 in processes.pids else None)
    said = server.quit_designer(wait_s=2)
    assert 'Designer quit after' in said and 'preferences' not in said, said
    assert defaults.domain == changed and os.path.exists(designer_preferences.saved_file()), 'left for the last one'


@_MACOS_PLIST
def test_quit_with_no_designer_running_puts_back_a_copy_left(defaults: FakeDefaults) -> None:
    _saved_as_by_a_launch(defaults)
    said = server.quit_designer()
    assert defaults.domain == _USERS
    assert said.startswith('Designer is not running.\n') and 'preferences put back' in said, said


@_MACOS_PLIST
def test_quit_with_no_designer_running_drops_a_copy_left_too_long(defaults: FakeDefaults) -> None:
    # REVIEW.md SRV-125: none ended through the tools, and the user may have worked since with no log to show it
    hours = designer_preferences.LEFTOVER_HOURS + 1
    _saved_as_by_a_launch(defaults, hours_ago=hours)
    changed = dict(defaults.domain)
    said = server.quit_designer()
    assert defaults.domain == changed and not os.path.exists(designer_preferences.saved_file())
    assert said == (
        "Designer is not running.\nDesigner's preferences left as they are: their copy is over %d hours old and this "
        'call ended no Designer, so it was dropped: the user may have worked since.'
        % designer_preferences.LEFTOVER_HOURS
    ), said


@_MACOS_PLIST
def test_quit_puts_nothing_back_while_designers_cant_be_listed(
    monkeypatch: pytest.MonkeyPatch, defaults: FakeDefaults
) -> None:
    # pgrep failing: one may run, so the file is left (REVIEW.md SRV-83: an empty list would read as none running)
    _saved_as_by_a_launch(defaults)
    changed = dict(defaults.domain)

    def unlisted() -> list[int]:
        raise server._NoListing("Designer's processes couldn't be listed (pgrep exit code 3: out of memory)")

    patch_server(monkeypatch, '_designer_pids', unlisted)
    patch_server(monkeypatch, '_designer_running', lambda: False)
    said = server.quit_designer()
    assert defaults.domain == changed and os.path.exists(designer_preferences.saved_file()), said


# --- a Designer's process waited for by its exit, its status every POLL_S: never a fixed time (REVIEW.md SRV-150)


def test_launch_asks_the_status_every_poll_interval(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # every 2 s, so a launch ended up to 2 s after its Designer answered; nothing says when its bridge starts listening,
    # and a refused connection costs nothing
    started = _launch_fakes(monkeypatch, tmp_path)
    answers = iter([False, False, True])

    def bridge(request: Request, wait: float, port: int | None = None) -> Reply:
        if not next(answers, True):
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    patch_server(monkeypatch, '_send', bridge)
    slept: list[float] = []
    monkeypatch.setattr(time, 'sleep', slept.append)
    assert 'Designer started in' in server.launch_designer(wait_s=30) and started
    assert server.POLL_S == 0.1 and len(slept) >= 2 and set(slept) == {server.POLL_S}


def test_quit_waits_for_the_processs_exit(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    # it looked for the process every second, so a quit ended up to a second after its Designer went
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    _closes(monkeypatch)
    waited: list[tuple[int, float]] = []

    def exited(pid: int, limit: float) -> bool:
        waited.append((pid, limit))
        processes.pids.clear()
        return True

    patch_server(monkeypatch, '_exited', exited)
    assert 'Designer quit after' in server.quit_designer(wait_s=7)
    assert waited == [(11, 7)]


@_FORCE_ENDS
def test_a_forced_end_waits_for_the_processs_exit_after_each_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[int] = []
    waited: list[tuple[int, float]] = []
    monkeypatch.setattr(os, 'kill', lambda pid, sig: sent.append(sig))

    def stays(pid: int, limit: float) -> bool:
        waited.append((pid, limit))
        return False

    patch_server(monkeypatch, '_exited', stays)
    assert server._force_end(11, server.PORT, b'') is False
    assert sent == [signal.SIGTERM, signal.SIGKILL] and waited == [(11, server.FORCE_WAIT_S)] * 2


def test_without_an_exit_watch_the_process_is_looked_for_every_poll_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    # off macOS, or a process it can't watch (another user's)
    processes = _Processes(monkeypatch, 11)
    slept: list[float] = []
    clock = [0.0]

    def asleep(seconds: float) -> None:
        slept.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(time, 'sleep', asleep)
    assert server._exited(11, 0.3) is False and slept == [server.POLL_S] * 3
    slept.clear()

    def gone(seconds: float) -> None:
        slept.append(seconds)
        processes.pids.clear()

    monkeypatch.setattr(time, 'sleep', gone)
    assert server._exited(11, 5) is True and slept == [server.POLL_S]


def _child() -> 'subprocess.Popen[bytes]':
    """A process of this test's, which ends once its input is closed."""
    return subprocess.Popen([sys.executable, '-c', 'import sys; sys.stdin.read()'], stdin=subprocess.PIPE)


@pytest.mark.skipif(sys.platform != 'darwin', reason="macOS's kqueue")
def test_a_process_ending_is_seen_by_its_exit_event_not_looked_for(monkeypatch: pytest.MonkeyPatch) -> None:
    # a kqueue process-exit event: the wait ends as the process does
    child = _child()
    try:
        patch_server(monkeypatch, '_designer_pids', lambda: [child.pid])

        def watched_then_ended(pid: int) -> server_tools.lifecycle._ExitWatch | None:
            watch: server_tools.lifecycle._ExitWatch | None = REAL_EXIT_WATCH(pid)
            assert child.stdin is not None
            child.stdin.close()  # it ends from here on, the watch already there
            return watch

        patch_server(monkeypatch, '_exit_watch', watched_then_ended)
        monkeypatch.setattr(time, 'sleep', lambda seconds: pytest.fail('looked for every %g s' % seconds))
        assert server._exited(child.pid, 60) is True
    finally:
        child.kill()
        child.wait()


@pytest.mark.skipif(sys.platform != 'darwin', reason="macOS's kqueue")
def test_a_process_outliving_the_limit_isnt_said_to_have_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    child = _child()
    try:
        patch_server(monkeypatch, '_designer_pids', lambda: [child.pid])
        patch_server(monkeypatch, '_exit_watch', REAL_EXIT_WATCH)
        monkeypatch.setattr(time, 'sleep', lambda seconds: pytest.fail('looked for every %g s' % seconds))
        assert server._exited(child.pid, 0.05) is False
    finally:
        child.kill()
        child.wait()


@pytest.mark.skipif(sys.platform != 'darwin', reason="macOS's kqueue")
def test_a_process_gone_before_its_watch_has_ended() -> None:
    child = _child()
    child.kill()
    child.wait()  # reaped: no process has its id now, or another one, not watched as this
    watch = REAL_EXIT_WATCH(child.pid)
    assert watch is not None and watch.wait(0.05) is True


def test_the_poll_for_a_process_ends_at_its_limit_however_long_each_look_takes(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-153: ceil(limit / POLL_S) sleeps, each followed by a pgrep: a slow pgrep ran the wait past its limit
    clock = [0.0]
    looks: list[float] = []

    def slow_pids() -> list[int]:
        looks.append(clock[0])
        clock[0] += 0.4  # a pgrep under load
        return [11]

    patch_server(monkeypatch, '_designer_pids', slow_pids)
    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(time, 'sleep', lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    assert server._exited(11, 1.0) is False
    assert clock[0] < 1.0 + 0.5 + server.POLL_S, 'ended at %.1f s for a limit of 1 s' % clock[0]


def test_a_watch_that_times_out_with_the_process_already_gone_says_it_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-153: the branch where pgrep, not the watch, says the process is gone
    pids = [[11], []]
    patch_server(monkeypatch, '_designer_pids', lambda: pids.pop(0) if len(pids) > 1 else pids[0])
    patch_server(monkeypatch, '_exit_watch', lambda pid: SimpleNamespace(wait=lambda limit: False))
    assert server._exited(11, 0.1) is True


@pytest.mark.skipif(sys.platform != 'darwin', reason="macOS's kqueue")
def test_a_kqueue_that_cant_be_made_falls_back_to_the_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-153: select.kqueue() was called before the try, so an OSError there (no file descriptor left)
    # escaped _exit_watch
    import select

    def no_more() -> NoReturn:
        raise OSError(24, 'Too many open files')

    monkeypatch.setattr(select, 'kqueue', no_more)
    assert REAL_EXIT_WATCH(os.getpid()) is None


def test_the_exit_watch_type_checks_where_kqueue_doesnt_exist() -> None:
    # REVIEW.md SRV-153: `'select.kqueue | None'` names a class select has only on BSD and macOS
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'mypy',
            '--config-file',
            'mypy.ini',
            '--platform',
            'linux',
            'mcp_server/server_tools/lifecycle.py',
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert 'kqueue' not in result.stdout, result.stdout


def _refused_then_idle(refusals: int) -> _Send:
    left = [refusals]

    def bridge(request: Request, wait: float, port: int | None = None) -> Reply:
        if left[0]:
            left[0] -= 1
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    return bridge


def test_a_launch_waiting_for_its_own_start_looks_up_no_process_between_its_polls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-154: the refused path runs its lookups only for a Designer another launch started
    started = _launch_fakes(monkeypatch, tmp_path)
    looked: list[int] = []
    real = server._running_on

    def running_on(port: int) -> bool:
        looked.append(port)
        return bool(real(port))

    patch_server(monkeypatch, '_running_on', running_on)
    patch_server(monkeypatch, '_send', _refused_then_idle(5))
    monkeypatch.setattr(time, 'sleep', lambda seconds: None)
    assert 'Designer started in' in server.launch_designer(wait_s=30) and started
    assert len(looked) == 2  # before the start, and in it, under the launch lock


# another launch's Designer 11, recorded without a home (_agent_record)
ANOTHER_LAUNCHS = server_tools.lifecycle._Recorded(11, None, b'{}', 0.0)


def test_a_launch_waiting_for_another_launchs_designer_looks_it_up_once_its_process_exits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-154: pgrep and lsof ran every POLL_S while that Designer started; its exit is a callback
    _launch_fakes(monkeypatch, tmp_path)
    looked: list[int] = []

    def running_on(port: int) -> bool:
        looked.append(port)
        return True

    patch_server(monkeypatch, '_running_on', running_on)
    patch_server(monkeypatch, '_agent_record', lambda port: ANOTHER_LAUNCHS)
    patch_server(monkeypatch, '_still_starting', lambda port: True)
    patch_server(monkeypatch, '_exit_watch', lambda pid: SimpleNamespace(ended=lambda: False, close=lambda: None))
    patch_server(monkeypatch, '_send', _refused_then_idle(5))
    monkeypatch.setattr(time, 'sleep', lambda seconds: None)
    server.launch_designer(wait_s=30)
    assert len(looked) == 1, 'looked up %d times' % len(looked)


_MARKS = ('SD_BRIDGE_PORT=9879', 'CFFIXED_USER_HOME=/tmp/sd_mcp_501_9879/home')


def test_the_process_open_started_is_the_new_one_with_its_port(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    # REVIEW.md SRV-152: `open` gives no process ID; a new Designer's is taken only once its environment has the
    # launch's port, so a launch on another port starting at once isn't taken for it
    seen = [[11], [11, 80], [11, 80, 81]]
    patch_server(monkeypatch, '_designer_pids', lambda: seen.pop(0) if len(seen) > 1 else seen[0])
    patch_server(monkeypatch, '_carries', lambda pid, marks: pid == 81 and marks == _MARKS)
    assert REAL_FOUND_LAUNCHED(SimpleNamespace(pid=5), {11}, _MARKS) == 81


def test_a_process_open_started_that_never_shows_is_said(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    patch_server(monkeypatch, '_designer_pids', lambda: [11])
    patch_server(monkeypatch, '_carries', lambda pid, marks: False)
    with pytest.raises(server.ToolError, match="its process wasn't found"):
        REAL_FOUND_LAUNCHED(SimpleNamespace(pid=5), {11}, _MARKS)


def test_a_launch_is_known_by_its_port_and_its_home() -> None:
    # REVIEW.md SRV-165: the port alone is in the environment of a Designer the user starts with SD_BRIDGE_PORT set
    env = {'SD_BRIDGE_PORT': '9879', 'CFFIXED_USER_HOME': '/tmp/sd_mcp_501_9879/home', 'TMPDIR': '/tmp/t/', 'X': 'y'}
    assert server._launch_marks(env) == _MARKS


@pytest.mark.parametrize('look', ['_found_launched', '_launched_now'])
def test_a_designer_the_user_starts_with_the_launchs_port_isnt_taken_for_the_launchs(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, look: str
) -> None:
    # REVIEW.md SRV-165: the user's, started during the launch, is the newer, its environment setting the same port
    shown = {
        81: '/A/Designer SD_BRIDGE_PORT=9879 CFFIXED_USER_HOME=/tmp/sd_mcp_501_9879/home TMPDIR=/tmp/t/\n',
        82: '/A/Designer SD_BRIDGE_PORT=9879 HOME=/Users/u\n',
    }
    patch_server(monkeypatch, '_designer_pids', lambda: [11, 81, 82])
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: SimpleNamespace(stdout=shown[int(cmd[3])], returncode=0))
    if look == '_found_launched':
        assert REAL_FOUND_LAUNCHED(SimpleNamespace(pid=5), {11}, _MARKS) == 81
    else:
        assert server._launched_now({11}, _MARKS) == 81


@pytest.mark.parametrize(
    'shown, has',
    [
        ('/A/Designer TMPDIR=/tmp/t/ SD_BRIDGE_PORT=9879 XPC_FLAGS=0x0\n', True),
        ('/A/Designer TMPDIR=/tmp/t/ SD_BRIDGE_PORT=9879\n', True),
        ('/A/Designer SD_BRIDGE_PORT=98790 XPC_FLAGS=0x0\n', False),
        ('/A/Designer MY_SD_BRIDGE_PORT=9879 XPC_FLAGS=0x0\n', False),
    ],
    ids=['followed by another variable', 'printed last', 'another port', 'another variable'],
)
def test_the_port_is_read_as_a_whole_variable_of_ps(monkeypatch: pytest.MonkeyPatch, shown: str, has: bool) -> None:
    # REVIEW.md SRV-157: a substring; ps ends its line with a newline, so the port printed last didn't match
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: SimpleNamespace(stdout=shown, returncode=0))
    assert server._carries(81, ('SD_BRIDGE_PORT=9879',)) is has


@_MACOS_PLIST
@pytest.mark.parametrize('found', [True, False], ids=['found at a last look, and ended', 'not found'])
def test_a_designer_open_started_whose_process_isnt_found_keeps_the_copy_of_the_preferences(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, defaults: FakeDefaults, found: bool
) -> None:
    # REVIEW.md SRV-156: once `open` exited 0, Designer may run; handled as a start that failed, the copy was dropped
    # and the Designer left running unrecorded, said "could not be started"
    defaults.domain = dict(_USERS)
    _launch_fakes(monkeypatch, tmp_path)  # an app bundle: opened by `open`
    processes = _Processes(monkeypatch)
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_own_home', lambda port: str(tmp_path / 'home'))
    patch_server(monkeypatch, '_carries', lambda pid, marks: found and pid == 88)

    def not_found(opener: _FakeProcess, before: set[int], marks: tuple[str, ...]) -> int:
        processes.pids.append(88)  # it runs: its start writes the file
        defaults.domain['session.instancePID'] = 88
        raise server.ToolError("its process wasn't found within 60 s")

    patch_server(monkeypatch, '_found_launched', not_found)
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    said = str(raised.value)
    assert 'Designer was opened' in said and 'could not be started' not in said, said
    if found:
        assert processes.signals == [(88, signal.SIGTERM)], 'ended, as one an agent started'
        assert defaults.domain == _USERS, 'put back: none of its runs now'
    else:
        assert processes.signals == [] and "counts as the user's" in said, said
        assert os.path.exists(designer_preferences.saved_file()), 'the copy kept for its put-back'
        assert defaults.domain['session.instancePID'] == 88, 'not put back while it may run'


@_SETS_UNIX
def test_opens_failure_is_said_with_what_open_printed_and_its_wait_has_a_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-160: `open` waited for with no limit, and its message dropped (stderr to DEVNULL)
    monkeypatch.setattr(sys, 'platform', 'darwin')
    started = _launch_fakes(monkeypatch, tmp_path)
    limits: list[float | None] = []

    class Opener(_FakeProcess):
        def wait(self, timeout: float | None = None) -> int:
            limits.append(timeout)
            return 1

    def begin(cmd: list[str], **kw: Unpack[_PopenArgs]) -> Opener:
        started.append(cmd)
        said = kw.get('stderr')
        if isinstance(said, io.BufferedIOBase):  # the temporary file `open`'s errors go to
            said.write(b"Unable to find application named 'Nope'\n")
        return Opener(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_designer_running', lambda: False)
    patch_server(monkeypatch, '_send', _no_bridge)
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    said = str(raised.value)
    assert "`open` exited with 1 (Unable to find application named 'Nope')" in said, said
    assert limits and limits[0] is not None, 'a limit, a safety net'


@_SETS_UNIX
def test_an_open_that_doesnt_exit_is_said_as_a_designer_that_may_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-160: past its limit `open` is ended, and Designer may have been opened
    monkeypatch.setattr(sys, 'platform', 'darwin')
    started = _launch_fakes(monkeypatch, tmp_path)
    killed: list[int] = []

    class Opener(_FakeProcess):
        def wait(self, timeout: float | None = None) -> int:
            raise subprocess.TimeoutExpired('open', timeout or 0)

        def kill(self) -> None:
            killed.append(self.pid)

    def begin(cmd: list[str], **kw: Unpack[_PopenArgs]) -> Opener:
        started.append(cmd)
        return Opener(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_designer_running', lambda: False)
    patch_server(monkeypatch, '_send', _no_bridge)
    with pytest.raises(server.ToolError) as raised:
        server.launch_designer(wait_s=30)
    said = str(raised.value)
    assert killed == [77] and "Designer was opened, but `open` didn't exit within" in said, said


@_SETS_UNIX
def test_the_process_open_started_is_looked_for_with_the_launchs_port_and_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md TST-437: the conftest fake ignores the marks; SRV-165: the port's variable and the home's, each whole
    # (TST-443: the port the call was given)
    monkeypatch.setattr(sys, 'platform', 'darwin')
    started = _launch_fakes(monkeypatch, tmp_path)
    asked: list[tuple[str, ...]] = []

    def found(opener: _FakeProcess, before: set[int], marks: tuple[str, ...]) -> int:
        asked.append(marks)
        return int(opener.pid)

    patch_server(monkeypatch, '_found_launched', found)
    patch_server(monkeypatch, '_designer_running', lambda: False)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    home = tmp_path / 'home'
    patch_server(monkeypatch, '_own_home', lambda port: str(home))
    server.launch_designer(wait_s=30, port=OTHER)
    # its home too: the port alone is in a Designer the user starts with SD_BRIDGE_PORT set (REVIEW.md SRV-165)
    assert asked == [('SD_BRIDGE_PORT=%d' % OTHER, 'CFFIXED_USER_HOME=%s' % home)], asked


@_SETS_UNIX
def test_a_binary_in_sd_designer_app_is_started_itself_on_macos(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md TST-437: only an app bundle is opened by `open`
    monkeypatch.setattr(sys, 'platform', 'darwin')
    started = _launch_fakes(monkeypatch, tmp_path)
    binary = tmp_path / 'Designer'
    binary.write_text('')
    monkeypatch.setenv('SD_DESIGNER_APP', str(binary))
    patch_server(monkeypatch, '_designer_running', lambda: False)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    server.launch_designer(wait_s=30)
    assert started == [[str(binary)]], started
    assert _started_with[0]['start_new_session'] and _started_with[0]['cwd'] == '/'


@_SETS_UNIX
def test_processes_that_cant_be_listed_before_open_are_said_as_no_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md TST-437: _started's wrapping of _NoListing, before `open` runs
    monkeypatch.setattr(sys, 'platform', 'darwin')
    started = _launch_fakes(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_running_on', lambda port: False)
    patch_server(monkeypatch, '_users_next_to', lambda port, note: None)

    def no_listing() -> list[int]:
        raise server._NoListing('pgrep failed')

    patch_server(monkeypatch, '_designer_pids', no_listing)
    patch_server(monkeypatch, '_send', _no_bridge)
    with pytest.raises(server.ToolError, match=r'Designer could not be started from .*pgrep failed'):
        server.launch_designer(wait_s=30)
    assert started == [], '`open` never ran'


def test_a_negative_wait_for_an_exit_is_no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-159: kqueue refuses a negative timeout ("timeout must be positive or None"), after the close sent

    class Queue:
        def control(self, changes: None, events: int, timeout: float | None = None, /) -> list[object]:
            if timeout is not None and timeout < 0:
                raise ValueError('timeout must be positive or None')
            return []

        def close(self) -> None:
            pass

    patch_server(monkeypatch, '_designer_pids', lambda: [11])
    patch_server(monkeypatch, '_exit_watch', lambda pid: server._ExitWatch(Queue()))
    assert server._exited(11, -1) is False


class _Watch:
    """An exit watch, as launch_designer's wait uses it: ended() from `ends` (False once it runs out), close() counted."""

    def __init__(self, ends: list[bool], closed: list[int]) -> None:
        self.ends, self.closed = ends, closed

    def ended(self) -> bool:
        return self.ends.pop(0) if self.ends else False

    def close(self) -> None:
        self.closed.append(1)


def test_a_launch_waiting_for_another_launchs_designer_reads_its_record_once_and_closes_its_watch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-158: each refused round read the record twice (pgrep and ps each time), and the watches were never
    # closed
    _launch_fakes(monkeypatch, tmp_path)
    read: list[int] = []
    closed: list[int] = []
    patch_server(monkeypatch, '_running_on', lambda port: True)

    def record(port: int) -> server_tools.lifecycle._Recorded:
        read.append(port)
        return ANOTHER_LAUNCHS

    patch_server(monkeypatch, '_agent_record', record)
    patch_server(monkeypatch, '_still_starting', lambda port: True)
    patch_server(monkeypatch, '_exit_watch', lambda pid: _Watch([], closed))
    patch_server(monkeypatch, '_send', _refused_then_idle(5))
    monkeypatch.setattr(time, 'sleep', lambda seconds: None)
    server.launch_designer(wait_s=30)
    # once over the five refused rounds, and once as it answers (_already_running: its home, for its crash uploads)
    assert len(read) == 2 and closed == [1], (read, closed)


def test_a_launch_waiting_on_an_unrecorded_designer_starts_one_once_that_designer_leaves_the_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-162: an unrecorded Designer can stop holding the port without exiting: another launch records it on
    # its own port, or it starts listening on another. Watched only for its exit, it was never looked up again, and the
    # launch waited out wait_s, then named it to end. So it is looked up each round, as no callback says either
    started = _launch_fakes(monkeypatch, tmp_path)
    looks = [0]

    def sorted_out(port: int) -> tuple[list[int], list[int]]:
        looks[0] += 1
        return [22] if looks[0] <= 3 else [], []  # recorded by another launch on its own port at the fourth look

    patch_server(monkeypatch, '_running_on', lambda port: bool(sorted_out(port)[0]))
    patch_server(monkeypatch, '_agent_record', lambda port: None)
    patch_server(monkeypatch, '_sorted_out', sorted_out)
    patch_server(monkeypatch, '_exit_watch', lambda pid: _Watch([], []))  # it never exits
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    now = [time.time()]
    monkeypatch.setattr(time, 'sleep', lambda seconds: now.__setitem__(0, now[0] + seconds))
    monkeypatch.setattr(time, 'time', lambda: now[0])
    assert 'Designer started in' in server.launch_designer(wait_s=30) and started


def test_a_launch_waiting_on_a_designer_goes_on_when_its_processes_cant_be_listed_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-164: one pgrep failing in the wait's look ended the call; can't tell is read as may still hold the
    # port, and the wait goes on to the Designer's answer
    started = _launch_fakes(monkeypatch, tmp_path)
    looks = [0]

    def running_on(port: int) -> bool:
        looks[0] += 1
        if looks[0] == 2:
            raise server._NoListing("Designer's processes couldn't be listed (pgrep exit code 3: fork failed)")
        return True

    asked = [0]

    def send(request: Request, wait: float, port: int | None = None) -> Reply:
        asked[0] += 1
        if asked[0] <= 4:  # its bridge not up yet
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle, 0 queued'}

    patch_server(monkeypatch, '_running_on', running_on)
    patch_server(monkeypatch, '_agent_record', lambda port: None)  # unrecorded: looked up each round
    patch_server(monkeypatch, '_send', send)
    now = [time.time()]
    monkeypatch.setattr(time, 'sleep', lambda seconds: now.__setitem__(0, now[0] + seconds))
    monkeypatch.setattr(time, 'time', lambda: now[0])
    said = server.launch_designer(wait_s=30)
    assert said.startswith('Designer already running') and looks[0] > 2 and not started, said


@pytest.mark.parametrize('watchable', [True, False], ids=['its exit event come', 'no watch to be had'])
def test_a_launch_waiting_for_another_launchs_designer_starts_one_once_it_exited(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, watchable: bool
) -> None:
    # REVIEW.md TST-437: may_have_exited's ended and no-watch branches; without a watch it is looked up every round
    started = _launch_fakes(monkeypatch, tmp_path)
    running = [True]
    looked: list[int] = []
    rounds = [0]

    def running_on(port: int) -> bool:
        looked.append(port)
        return running[0]

    def ended() -> bool:
        rounds[0] += 1
        if rounds[0] == 3:  # it exits
            running[0] = False
        return not running[0]

    patch_server(monkeypatch, '_running_on', running_on)
    patch_server(monkeypatch, '_agent_record', lambda port: ANOTHER_LAUNCHS if running[0] else None)
    patch_server(monkeypatch, '_still_starting', lambda port: True)
    if watchable:
        patch_server(monkeypatch, '_exit_watch', lambda pid: SimpleNamespace(ended=ended, close=lambda: None))
    else:
        patch_server(monkeypatch, '_exit_watch', lambda pid: None)
        patch_server(monkeypatch, '_agent_record', lambda port: ANOTHER_LAUNCHS if ended() is False else None)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    monkeypatch.setattr(time, 'sleep', lambda seconds: None)
    assert 'Designer started in' in server.launch_designer(wait_s=30) and started
    # before the start, then: once it exited (watched), or each round (not), then in start() under its lock
    assert len(looked) == (3 if watchable else 5), looked


def test_the_home_comes_from_the_record_whose_designer_was_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-172: _agent_home checked one read of the record, then took the home from a second read: a record
    # put in place meanwhile, by another server's launch on the port, gave its home for the Designer checked before
    reads = iter(
        [
            (json.dumps({'pid': 77, 'start': 'then', 'home': '/a/home'}).encode(), 1.0),
            (json.dumps({'pid': 88, 'start': 'later', 'home': '/b/home'}).encode(), 2.0),
        ]
    )
    patch_server(monkeypatch, '_read_record', lambda port: next(reads))
    patch_server(monkeypatch, '_designer_pids', lambda: [77])
    patch_server(monkeypatch, '_process_start', lambda pid: 'then')
    assert server._agent_home(9901) == '/a/home'


def test_the_log_comes_from_the_record_whose_designer_was_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-174: _log_for checked one read of the record, then took the home from a second read: a quit by
    # another server meanwhile, which removes the record, gave the shared log, the user's lines, for the agent's Designer
    reads = iter([(json.dumps({'pid': 77, 'start': 'then', 'home': '/a/home'}).encode(), 1.0), None])
    patch_server(monkeypatch, '_read_record', lambda port: next(reads))
    patch_server(monkeypatch, '_designer_pids', lambda: [77])
    patch_server(monkeypatch, '_process_start', lambda pid: 'then')
    patch_server(monkeypatch, '_designer_log_path', lambda: '/the/shared/log.txt')
    patch_server(monkeypatch, '_agent_log', lambda port, home, written: 'the own log in %s' % home)
    assert server._log_for(9901) == 'the own log in /a/home'
