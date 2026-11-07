"""launch/quit paths that can't be produced safely with a real Designer, designer_status,
environment-variable overrides (README, Configuration), log filtering and the missing-tools message."""

import contextlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from textwrap import dedent
from typing import Any, NoReturn

import pytest

import project_constants
import server_tools
from conftest import (
    REAL_BIND_ERROR,
    REAL_DESIGNER_PIDS,
    REAL_OWN_HOME,
    REAL_OWN_TEMP,
    REAL_PROCESS_START,
    REAL_SHORT_TEMP,
    ROOT,
    patch_server,
    server,
)
from project_constants import PLUGIN, PLUGIN_PACKAGE_DIR
from server_tools.core import Reply


def _no_bridge(request: dict[str, Any], wait: float, port: int | None = None) -> NoReturn:
    raise server.ToolError('Designer is not reachable.')


class _FakeProcess:
    """What subprocess.Popen returns, as launch_designer uses it."""

    def __init__(self, pid: int) -> None:
        self.pid = pid

    def wait(self) -> int:
        return 0


def _popen(
    started: list[Any], entry: Callable[[list[str]], Any] = lambda cmd: cmd, pid: int = 77
) -> Callable[..., _FakeProcess]:
    """A fake subprocess.Popen: each start appends entry(cmd) to started, its keyword arguments to started_with."""

    def popen(cmd: list[str], **kw: Any) -> _FakeProcess:
        started.append(entry(cmd))
        _started_with.append(kw)
        return _FakeProcess(pid)

    return popen


_started_with: list[dict[str, Any]] = []


@pytest.fixture(autouse=True)
def _no_starts_left() -> Iterator[None]:
    _started_with.clear()
    yield
    _started_with.clear()


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, 'sleep', lambda s: None)


def test_launch_reports_missing_app(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_designer_running', lambda: False)
    monkeypatch.setenv('SD_DESIGNER_APP', '/no/such/Designer.app')
    with pytest.raises(server.ToolError, match='Designer not found'):
        server.launch_designer()


def test_launch_times_out_when_the_bridge_never_answers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    started: list[Any] = []
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
    started: list[Any] = []
    home: list[str] = []
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_designer_running', lambda: True)
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', _popen(started))

    def home_screen(
        code: str,
        path: str | None = None,
        timeout: float | None = None,
        wait: float | None = None,
        port: int | None = None,
    ) -> str:
        home.append(code)
        return ''

    patch_server(monkeypatch, '_bridge', home_screen)
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError) as error:
        server.launch_designer(wait_s=30)
    assert not started, 'started a second Designer'
    assert 'already running' in str(error.value) and 'did not answer within 30s' in str(error.value)
    # once it answers: reported as already running, and its Home screen is left alone
    answers: Iterator[Exception | Reply] = iter([server.ToolError('not yet'), {'ok': True, 'output': 'idle'}])

    def bridge_comes_up(request: dict[str, Any], wait: float, port: int | None = None) -> Reply:
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


def _refused(request: dict[str, Any], wait: float, port: int | None = None) -> Reply:
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
    started: list[Any] = []
    patch_server(monkeypatch, '_send', _refused)
    patch_server(monkeypatch, '_designer_running', lambda: True)
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None, wait=None, port=None: 'closing Designer')
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
    calls: tuple[Callable[[], object], ...] = (
        lambda: server.render_sbs('x.sbs', '/tmp/out'),
        lambda: server.sbsar_info('x.sbs'),
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
    started: list[Any] = []
    processes = iter([True, True, False])  # there at first, then gone
    patch_server(monkeypatch, '_designer_running', lambda: next(processes, False))
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', _popen(started))

    def bridge(request: dict[str, Any], wait: float, port: int | None = None) -> Reply:
        if not started:
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    patch_server(monkeypatch, '_send', bridge)
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None, wait=None, port=None: '')
    clock = iter(range(0, 1000, 5))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    assert server.launch_designer(wait_s=60).startswith('Designer started in')
    assert len(started) == 1


def test_a_restarted_designer_gets_the_whole_wait(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-19: after the old process went away late in the wait, the new Designer got
    # only what was left of wait_s, and "started in" counted the wait for the old one
    started: list[int] = []
    now = [0]
    processes = iter([True] + [True] * 33 + [False])  # the old one goes away at ~175 s of 180 (SRV-21)
    patch_server(monkeypatch, '_designer_running', lambda: next(processes, False))
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', _popen(started, lambda cmd: now[0]))

    def clock() -> int:
        now[0] += 5
        return now[0]

    monkeypatch.setattr(time, 'time', clock)

    def bridge(request: dict[str, Any], wait: float, port: int | None = None) -> Reply:
        if not started or now[0] < started[0] + 60:  # the new one needs 60 s to come up
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    patch_server(monkeypatch, '_send', bridge)
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None, wait=None, port=None: '')
    text = server.launch_designer(wait_s=180)
    match = re.search(r'started in (\d+)s', text)
    assert match is not None, text
    seconds = int(match.group(1))
    assert seconds <= 90, text  # timed from the restart, not the first call


def test_designer_status_reports_the_servers_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-13: the server's own Python and library versions
    import platform

    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': 'bridge idle'})
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None, wait=None, port=None: 'Designer 16.0.7')
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

    def package_list(
        code: str,
        path: str | None = None,
        timeout: float | None = None,
        wait: float | None = None,
        port: int | None = None,
    ) -> str:
        queued.append(code)
        return 'packages'

    patch_server(monkeypatch, '_bridge', package_list)
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


def _launch_fakes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[Any]:
    started: list[Any] = []
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', _popen(started))
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None, wait=None, port=None: '')
    return started


def _answers_once_started(started: list[Any]) -> Callable[[dict[str, Any], float], Reply]:
    def bridge(request: dict[str, Any], wait: float, port: int | None = None) -> Reply:
        if not started:
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    return bridge


def test_launch_state_not_running(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    home: list[str] = []
    processes = _Processes(monkeypatch)

    def begin(cmd: list[str], **kw: Any) -> _FakeProcess:
        started.append(cmd)
        processes.pids.append(77)
        return _FakeProcess(77)

    def bridge(
        code: str,
        path: str | None = None,
        timeout: float | None = None,
        wait: float | None = None,
        port: int | None = None,
    ) -> str:
        home.append(code)
        return ''

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    patch_server(monkeypatch, '_bridge', bridge)
    assert server.launch_designer(wait_s=30).startswith('Designer started in')
    assert len(started) == 1 and home and 'leave_home_screen' in home[0]
    assert server._agent_designer(server.PORT) == 77, 'it remembers the one it started'


def test_a_user_opening_one_at_the_same_moment_doesnt_confuse_the_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # the record is the process it started itself, so another appearing at the same moment can't be taken for it
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch)

    def begin(cmd: list[str], **kw: Any) -> _FakeProcess:
        started.append(cmd)
        processes.pids.extend([78, 77])
        return _FakeProcess(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    server.launch_designer(wait_s=30)
    assert server._agent_designer(server.PORT) == 77


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


def test_launch_state_agents_not_answering(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    # REVIEW.md HLP-82: an agent's Designer is disposable, so it isn't waited for
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1)

    def begin(cmd: list[str], **kw: Any) -> _FakeProcess:
        started.append(cmd)
        processes.pids.append(77)
        return _FakeProcess(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
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

    def answers_on_the_third(request: dict[str, Any], wait: float, port: int | None = None) -> Reply:
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


def test_launch_ends_an_agents_passing_the_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11, age=server.STARTUP_LIMIT - 20)

    def begin(cmd: list[str], **kw: Any) -> _FakeProcess:
        started.append(cmd)
        processes.pids.append(77)
        return _FakeProcess(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    now = time.time()
    clock = iter(range(0, 10000, 10))
    monkeypatch.setattr(time, 'time', lambda: now + next(clock))
    text = server.launch_designer(wait_s=1000)
    assert processes.signals == [(11, signal.SIGTERM)] and len(started) == 1
    assert 'Ended' in text and 'Designer started in' in text and server._agent_designer(server.PORT) == 77


def test_launch_stops_at_an_agents_it_cant_end(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    # REVIEW.md SRV-79: it said a later call would end it, right after failing to, and tried again at every poll
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11, ends_on=-1)
    _an_agent_started(11, age=server.STARTUP_LIMIT + 1)
    patch_server(monkeypatch, '_send', _no_bridge)
    with pytest.raises(server.ToolError, match=r'could not be ended; ask the user to run `kill -9 11`'):
        server.launch_designer(wait_s=30)
    assert processes.signals == [(11, signal.SIGTERM), (11, signal.SIGKILL)] and not started


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
    seen: list[Any] = []

    def run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
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
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None, wait=None, port=None: 'process 11')
    assert 'Not started by an agent' in server.designer_status()
    _an_agent_started(11)
    assert 'Started by an agent' in server.designer_status()


def test_designer_status_goes_by_the_designer_answering(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-73: the record names one process, the package list comes from whichever holds the port
    _Processes(monkeypatch, 11, 12)
    _an_agent_started(12)
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': 'idle, 0 queued'})
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None, wait=None, port=None: 'process 11')
    assert 'Not started by an agent' in server.designer_status()
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None, wait=None, port=None: 'process 12')
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


# --- closing it


def _closes(monkeypatch: pytest.MonkeyPatch, said: str = 'closing Designer') -> list[str]:
    asked: list[str] = []

    def bridge(
        code: str,
        path: str | None = None,
        timeout: float | None = None,
        wait: float | None = None,
        port: int | None = None,
    ) -> str:
        asked.append(code)
        return said

    patch_server(monkeypatch, '_bridge', bridge)
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': 'idle, 0 queued'})
    return asked


def test_quit_refuses_a_designer_no_agent_started(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    processes = _Processes(monkeypatch, 11)
    asked = _closes(monkeypatch)
    with pytest.raises(server.ToolError, match=r'ask the user to save, close and reopen'):
        server.quit_designer()
    assert not processes.signals and not asked, 'nothing is sent to it'


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


def test_quit_forces_an_agents_that_stays(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    # REVIEW.md HLP-82: Designer can hang at the very end of its shutdown, past anything inside it
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    _closes(monkeypatch)
    text = server.quit_designer(wait_s=3)
    assert 'forced' in text and processes.signals == [(11, signal.SIGTERM)]
    assert not Path(server.agent_designer_file(server.PORT)).exists()


def test_quit_forces_harder_if_it_must(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    processes = _Processes(monkeypatch, 11, ends_on=signal.SIGKILL)
    _an_agent_started(11)
    _closes(monkeypatch)
    assert 'forced' in server.quit_designer(wait_s=1)
    assert processes.signals == [(11, signal.SIGTERM), (11, signal.SIGKILL)]


def test_quit_says_so_if_even_that_fails(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    _Processes(monkeypatch, 11, ends_on=-1)
    _an_agent_started(11)
    _closes(monkeypatch)
    with pytest.raises(server.ToolError, match=r'kill -9 11'):
        server.quit_designer(wait_s=1)


def test_quit_forces_an_agents_with_no_bridge(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)

    def dead(
        code: str,
        path: str | None = None,
        timeout: float | None = None,
        wait: float | None = None,
        port: int | None = None,
    ) -> str:
        raise server.ToolError('Designer is not reachable.')

    patch_server(monkeypatch, '_bridge', dead)
    patch_server(monkeypatch, '_send', _no_bridge)
    text = server.quit_designer(wait_s=1)
    assert 'forced' in text and processes.signals and 'did not reply: Designer is not reachable' in text


def test_quit_names_the_process_it_means(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    # REVIEW.md SRV-73: the close goes to whichever Designer holds the port, and the helper refuses any other
    _Processes(monkeypatch, 11)
    _an_agent_started(11)
    asked = _closes(monkeypatch)
    server.quit_designer(wait_s=1)
    assert asked[0].rstrip().endswith('quit_designer(11)')


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
def test_the_close_has_a_limit_of_its_own(
    monkeypatch: pytest.MonkeyPatch, no_sleep: None, wait_s: int, limit: int
) -> None:
    # REVIEW.md SRV-78: a main thread frozen outside a job reads as idle, and the close then waited about 15 minutes
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    waits: list[float] = []

    def frozen(request: dict[str, Any], wait: float, port: int | None = None) -> Reply:
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
def test_quit_doesnt_queue_behind_a_job(monkeypatch: pytest.MonkeyPatch, no_sleep: None, state: str) -> None:
    # REVIEW.md SRV-74: the close would wait about 15 minutes in the queue before wait_s even started
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    asked = _closes(monkeypatch)
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': state})
    text = server.quit_designer(wait_s=1)
    assert not asked and processes.signals == [(11, signal.SIGTERM)]
    assert 'not asked to close' in text and state in text and 'forced' in text


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


def _ports_answering(*ports: int, asked: list[int | None] | None = None) -> Callable[..., Reply]:
    """_send that answers on `ports` only, noting the port of every request in asked."""

    def send(request: dict[str, Any], wait: float, port: int | None = None) -> Reply:
        if asked is not None:
            asked.append(port)
        if port not in ports:
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle, 0 queued'}

    return send


@pytest.mark.parametrize('port', [None, OTHER], ids=['the servers', 'another'])
def test_launch_starts_the_binary_with_the_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None, port: int | None
) -> None:
    # `open -a` brings back a Designer already running and passes it no environment: the plugin reads its port there
    assert server.PORT != OTHER
    monkeypatch.setattr(sys, 'platform', 'darwin')
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch)
    want = server.PORT if port is None else port
    asked: list[int | None] = []
    answering: list[int] = []

    def begin(cmd: list[str], **kw: Any) -> _FakeProcess:
        started.append(cmd)
        _started_with.append(kw)
        processes.pids.append(77)
        answering.append(want)
        return _FakeProcess(77)

    def send(request: dict[str, Any], wait: float, port: int | None = None) -> Reply:
        return _ports_answering(*answering, asked=asked)(request, wait, port)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', send)
    monkeypatch.setenv('PYTHONPATH', '/the/servers/own')
    text = server.launch_designer(wait_s=30, port=port)
    assert started == [[os.path.join(str(tmp_path), 'Contents', 'MacOS', 'Adobe Substance 3D Designer')]]
    kw = _started_with[0]
    assert kw['env']['SD_BRIDGE_PORT'] == str(want) and kw['start_new_session'] is True
    assert kw['cwd'] == '/', "as `open -a` started it: not the server's folder, the repository"
    assert kw['env']['HOME'] == os.environ['HOME'], 'the rest of the environment passes on'
    assert 'PYTHONPATH' not in kw['env'], "Designer's own Python doesn't take the server's settings"
    assert set(asked) == {want}, 'every request goes to that port'
    assert 'Designer started in' in text and 'on port %d' % want in text
    assert server._agent_designer(want) == 77
    assert not os.path.exists(server.agent_designer_file(OTHER if port is None else server.PORT))


def test_the_designer_started_is_reaped_when_it_exits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # a child nobody waits for lingers as a zombie, which still has its ID and start time
    import threading

    waited = threading.Event()

    class Process(_FakeProcess):
        def wait(self) -> int:
            waited.set()
            return 0

    started = _launch_fakes(monkeypatch, tmp_path)

    def begin(cmd: list[str], **kw: Any) -> Process:
        started.append(cmd)
        return Process(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
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


def test_launch_on_a_port_next_to_an_agents_on_another(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    answering = [server.PORT]

    def begin(cmd: list[str], **kw: Any) -> _FakeProcess:
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
    # Designers share the preferences plist (AGENTS.md, Several Designers), not measured to undo anything (REVIEW.md
    # TST-189: the refusal said the last to quit writes every settings file)
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
    assert len(asked) == 1 and asked[0][0].rstrip().endswith('quit_designer(12)') and asked[0][1] == OTHER
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
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tool: Callable[[Any], str], port: Any
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

    def run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr='')

    monkeypatch.setattr(subprocess, 'run', run)
    assert server._listening_ports(11) == {9877, 5000}
    assert seen[0][0] == 'lsof' and '11' in seen[0] and '-sTCP:LISTEN' in seen[0]
    out = ''
    assert server._listening_ports(11) == set()

    def missing(cmd: list[str], **kw: Any) -> NoReturn:
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


@pytest.mark.parametrize('platform', ['darwin', 'linux', 'win32'])
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


@pytest.mark.parametrize('platform', ['darwin', 'linux', 'win32'])
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
    assert server._plugin_paths() == '/Users/me/My Plugins'
    monkeypatch.setenv('SBS_DESIGNER_PYTHON_PATH', '/their/own')
    assert server._plugin_paths() == '/Users/me/My Plugins' + os.pathsep + '/their/own'
    patch_server(monkeypatch, '_designer_data_dir', lambda home=None: str(tmp_path / 'none'))
    monkeypatch.delenv('SBS_DESIGNER_PYTHON_PATH')
    assert server._plugin_paths() == os.path.join(
        os.path.expanduser('~'), 'Documents', 'Adobe', 'Adobe Substance 3D Designer', 'python', 'sduserplugins'
    ), "no project file yet: Designer's default, where install.py puts it"


def test_the_temp_folder_leaves_room_for_designers_socket() -> None:
    # measured: the socket's name takes 41 bytes with a 5-digit process ID, in the folder's real path (/tmp is
    # /private/tmp), and a socket's whole path at most 103 (104 with its NUL). With too long a path Designer made none
    # (in /var/folders/.../T/sd_mcp_9877/, 110 bytes), and then no other Designer can find it
    folder = os.path.join(os.path.realpath(REAL_SHORT_TEMP), server.agent_folder_name(65535), 'temp')
    assert len(folder) + 1 + 42 <= 103, folder


@pytest.mark.parametrize('kind', ['_own_temp', '_own_home'])
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
    """The shared log, and the log of the Designer an agent starts on OTHER, both written; macOS."""
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

    def begin(cmd: list[str], **kw: Any) -> _FakeProcess:
        started.append(cmd)
        processes.pids.append(77)
        return _FakeProcess(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    server.launch_designer(wait_s=30, port=OTHER)
    record = json.loads(Path(server.agent_designer_file(OTHER)).read_text())
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

    def bridge(request: dict[str, Any], wait: float, port: int | None = None) -> NoReturn:
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

    def __init__(self, *args: Any) -> None:
        pass

    def __enter__(self) -> '_BindRefused':
        return self

    def __exit__(self, *exc: object) -> None:
        pass

    def setsockopt(self, *args: Any) -> None:
        pass

    def bind(self, address: Any) -> None:
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
def test_a_record_read_while_it_is_written_isnt_lost(monkeypatch: pytest.MonkeyPatch) -> None:
    # (b): the record was emptied, then written; another server reading it in between deleted it as unreadable, and
    # the write then went into the deleted file
    _Processes(monkeypatch, 77)
    real_dump = json.dump
    read_meanwhile: list[dict[int, int]] = []

    def dump(obj: Any, f: Any, *args: Any, **kwargs: Any) -> None:
        read_meanwhile.append(server._agents())  # another server, at the worst moment
        real_dump(obj, f, *args, **kwargs)

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


def _recorded_pid() -> Any:
    return json.loads(Path(server.agent_designer_file(server.PORT)).read_text())['pid']


@pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded there')
def test_a_record_replaced_while_it_is_checked_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-91: the record of 77, which has ended, is found stale; meanwhile another server put 78's in place
    processes = _Processes(monkeypatch)
    _an_agent_started(77)
    _relaunched_meanwhile(monkeypatch, processes, lambda: True)
    assert server._agent_designer(server.PORT) is None  # 77's record, read first, was stale
    assert _recorded_pid() == 78 and server._agent_designer(server.PORT) == 78


@pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded there')
def test_a_record_replaced_while_a_designer_is_forced_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-91: 77 is force-ended; as it goes, another server starts and records 78
    processes = _Processes(monkeypatch, 77)
    _an_agent_started(77)
    _relaunched_meanwhile(monkeypatch, processes, lambda: 77 not in processes.pids)
    assert server._force_end(77, server.PORT, server._record_bytes(server.PORT) or b'')
    assert _recorded_pid() == 78


@pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded there')
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


def _starts_77(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[list[Any], '_Processes']:
    """launch_designer's fakes, its start giving process 77, running until it gets SIGTERM."""
    monkeypatch.setattr(sys, 'platform', 'darwin')
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch)

    def begin(cmd: list[str], **kw: Any) -> _FakeProcess:
        started.append(cmd)
        processes.pids.append(77)
        return _FakeProcess(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', _no_bridge)
    return started, processes


@pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded there')
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


@pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded there')
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


@pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded there')
def test_a_failing_ps_keeps_a_live_record(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-97: a sweep read the record of a live Designer as stale and removed it; it can't tell, so the
    # record stays (and the Designer isn't taken for an agent's meanwhile)
    _Processes(monkeypatch, 77)
    _an_agent_started(77)
    patch_server(monkeypatch, '_process_start', _ps_fails)
    assert server._agent_designer(server.PORT) is None
    assert os.path.exists(server.agent_designer_file(server.PORT))


@pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded there')
def test_a_designer_whose_start_cant_be_read_is_ended(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-97: with ps failing as it was recorded, the Designer just started ran unrecorded, silently
    started, processes = _starts_77(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_process_start', _ps_fails)
    with pytest.raises(server.ToolError, match='was started, then ended') as raised:
        server.launch_designer(wait_s=5)
    assert started and (77, signal.SIGTERM) in processes.signals and 'cannot allocate memory' in str(raised.value)


@pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded there')
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


@pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded there')
def test_a_designer_is_recorded_even_when_its_reaper_cant_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # REVIEW.md SRV-100: a thread that can't start (no resources) after Popen left start() before the record, the
    # Designer running unrecorded; the thread only reaps the child when it ends
    started, _ = _starts_77(monkeypatch, tmp_path)

    class NoThread:
        def __init__(self, *args: Any, **kw: Any) -> None:
            pass

        def start(self) -> None:
            raise RuntimeError("can't start new thread")

    monkeypatch.setitem(vars(server_tools.lifecycle), 'threading', types.SimpleNamespace(Thread=NoThread))
    with pytest.raises(server.ToolError, match='did not answer'):  # it starts, and never answers here
        server.launch_designer(wait_s=5)
    assert started and json.loads(Path(server.agent_designer_file(server.PORT)).read_text())['pid'] == 77


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


@pytest.mark.skipif(sys.platform == 'win32', reason='nothing is recorded on Windows, so nothing is locked there')
def test_two_launches_on_one_port_at_once_start_one_designer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # (a): both saw no Designer and both started one; the second hands over to the first and exits, and its record
    # replaced the first's
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch)
    both_in = threading.Barrier(2, timeout=1)  # holds a start until the other launch is starting too, if it can be

    def begin(cmd: list[str], **kw: Any) -> _FakeProcess:
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
def test_a_folder_that_cant_be_made_is_refused_naming_the_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str, how: str
) -> None:
    # only a link or another owner was a ToolError; a full or read-only /tmp, or a file named temp or home, escaped
    # as a plain OSError
    monkeypatch.setattr(sys, 'platform', 'darwin')
    patch_server(monkeypatch, kind, {'_own_temp': REAL_OWN_TEMP, '_own_home': REAL_OWN_HOME}[kind])
    patch_server(monkeypatch, 'SHORT_TEMP', str(tmp_path))
    if how == 'mkdir fails':

        def refuse(path: Any, mode: int = 0o777) -> None:
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
        assert server._plugin_paths() == os.path.join(
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
    assert server._plugin_paths() == '/Users/me/A&B plugins'


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
