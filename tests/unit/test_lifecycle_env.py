"""launch/quit paths that can't be produced safely with a real Designer, designer_status,
environment-variable overrides (README, Configuration), log filtering and the missing-tools message."""

import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from textwrap import dedent
from typing import Any, NoReturn

import pytest

from conftest import ROOT, patch_server, server
from project_constants import PLUGIN, PLUGIN_PACKAGE_DIR
from server_tools.core import Reply


def _no_bridge(request: dict[str, Any], wait: float) -> NoReturn:
    raise server.ToolError('Designer is not reachable.')


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
    monkeypatch.setattr(subprocess, 'Popen', lambda cmd: started.append(cmd))
    monkeypatch.setattr(os, 'startfile', lambda p: started.append(p), raising=False)
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
    monkeypatch.setattr(subprocess, 'Popen', lambda cmd: started.append(cmd))
    monkeypatch.setattr(os, 'startfile', lambda p: started.append(p), raising=False)

    def home_screen(code: str, path: str | None = None, timeout: float | None = None) -> str:
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

    def bridge_comes_up(request: dict[str, Any], wait: float) -> Reply:
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


def _refused(request: dict[str, Any], wait: float) -> Reply:
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
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: 'closing Designer')
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', lambda cmd: started.append(cmd))
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
    monkeypatch.setattr(subprocess, 'Popen', lambda cmd: started.append(cmd))
    monkeypatch.setattr(os, 'startfile', lambda p: started.append(p), raising=False)

    def bridge(request: dict[str, Any], wait: float) -> Reply:
        if not started:
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    patch_server(monkeypatch, '_send', bridge)
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: '')
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
    monkeypatch.setattr(subprocess, 'Popen', lambda cmd: started.append(now[0]))
    monkeypatch.setattr(os, 'startfile', lambda p: started.append(now[0]), raising=False)

    def clock() -> int:
        now[0] += 5
        return now[0]

    monkeypatch.setattr(time, 'time', clock)

    def bridge(request: dict[str, Any], wait: float) -> Reply:
        if not started or now[0] < started[0] + 60:  # the new one needs 60 s to come up
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    patch_server(monkeypatch, '_send', bridge)
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: '')
    text = server.launch_designer(wait_s=180)
    match = re.search(r'started in (\d+)s', text)
    assert match is not None, text
    seconds = int(match.group(1))
    assert seconds <= 90, text  # timed from the restart, not the first call


def test_designer_status_reports_the_servers_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-13: the server's own Python and library versions
    import platform

    patch_server(monkeypatch, '_send', lambda request, wait: {'ok': True, 'output': 'bridge idle'})
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: 'Designer 16.0.7')
    text = server.designer_status()
    assert 'MCP server: Python %s' % platform.python_version() in text
    assert 'mcp ' in text and 'pillow ' in text and 'numpy ' in text


def test_designer_status_answers_while_a_job_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-22: the package listing queued behind the running job, so the status call
    # waited up to ~31 minutes although the plugin knew at once that it was busy
    patch_server(
        monkeypatch,
        '_send',
        lambda request, wait: {'ok': True, 'output': '%s v3: running for 412.0s, 0 queued' % server.PLUGIN},
    )
    queued: list[str] = []

    def package_list(code: str, path: str | None = None, timeout: float | None = None) -> str:
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


def _an_agent_started(pid: int, start: str | None = None, age: float = 0) -> None:
    """Recorded `age` seconds ago: launch_designer waits for one younger than STARTUP_LIMIT."""
    record = server.agent_designer_file()
    Path(record).write_text(json.dumps({'pid': pid, 'start': start or 'started %d' % pid}))
    os.utime(record, (time.time() - age, time.time() - age))


def _launch_fakes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[Any]:
    started: list[Any] = []
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', lambda cmd: started.append(cmd))
    monkeypatch.setattr(os, 'startfile', lambda p: started.append(p), raising=False)
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: '')
    return started


def _answers_once_started(started: list[Any]) -> Callable[[dict[str, Any], float], Reply]:
    def bridge(request: dict[str, Any], wait: float) -> Reply:
        if not started:
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    return bridge


def test_launch_state_not_running(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    home: list[str] = []
    processes = _Processes(monkeypatch)

    def begin(cmd: list[str]) -> None:
        started.append(cmd)
        processes.pids.append(77)

    def bridge(code: str, path: str | None = None, timeout: float | None = None) -> str:
        home.append(code)
        return ''

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    patch_server(monkeypatch, '_bridge', bridge)
    assert server.launch_designer(wait_s=30).startswith('Designer started in')
    assert len(started) == 1 and home and 'leave_home_screen' in home[0]
    assert server._agent_designer() == 77, 'it remembers the one it started'


def test_a_user_opening_one_at_the_same_moment_isnt_remembered(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None
) -> None:
    # two new processes: it can't tell which is its own, so neither counts as an agent's
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch)

    def begin(cmd: list[str]) -> None:
        started.append(cmd)
        processes.pids.extend([77, 78])

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    server.launch_designer(wait_s=30)
    assert server._agent_designer() is None


def test_launch_state_answering(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    started = _launch_fakes(monkeypatch, tmp_path)
    patch_server(monkeypatch, '_send', lambda request, wait: {'ok': True, 'output': 'idle'})
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

    def begin(cmd: list[str]) -> None:
        started.append(cmd)
        processes.pids.append(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    text = server.launch_designer(wait_s=30)
    assert processes.signals == [(11, signal.SIGTERM)] and len(started) == 1
    assert 'Ended' in text and 'Designer started in' in text and server._agent_designer() == 77


def test_launch_state_agents_still_starting(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_sleep: None) -> None:
    # REVIEW.md SRV-75: a retry, or a second session, mustn't kill a Designer that is only slow to start
    started = _launch_fakes(monkeypatch, tmp_path)
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    calls: list[int] = []

    def answers_on_the_third(request: dict[str, Any], wait: float) -> Reply:
        calls.append(1)
        if len(calls) < 3:
            raise server.ToolError('Designer is not reachable.')
        return {'ok': True, 'output': 'idle'}

    patch_server(monkeypatch, '_send', answers_on_the_third)
    assert server.launch_designer(wait_s=30).startswith('Designer already running')
    assert not processes.signals and not started and server._agent_designer() == 11
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

    def begin(cmd: list[str]) -> None:
        started.append(cmd)
        processes.pids.append(77)

    monkeypatch.setattr(subprocess, 'Popen', begin)
    patch_server(monkeypatch, '_send', _answers_once_started(started))
    now = time.time()
    clock = iter(range(0, 10000, 10))
    monkeypatch.setattr(time, 'time', lambda: now + next(clock))
    text = server.launch_designer(wait_s=1000)
    assert processes.signals == [(11, signal.SIGTERM)] and len(started) == 1
    assert 'Ended' in text and 'Designer started in' in text and server._agent_designer() == 77


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
    path = Path(server.agent_designer_file())
    if content is not None:
        path.write_text(content)
    assert server._agent_designer() is None, why
    assert not path.exists(), 'a stale file is removed'


def test_a_process_that_isnt_designer_doesnt_count(monkeypatch: pytest.MonkeyPatch) -> None:
    # the ID and start time match a process, but it isn't among Designer's
    _Processes(monkeypatch, 11)
    patch_server(monkeypatch, '_process_start', lambda pid: 'started 12')
    _an_agent_started(12)
    assert server._agent_designer() is None


def test_the_file_is_read_again_by_a_new_server(monkeypatch: pytest.MonkeyPatch) -> None:
    # nothing but the file carries it, so a /mcp reconnect keeps it
    _Processes(monkeypatch, 11)
    _an_agent_started(11)
    assert server._agent_designer() == 11


def test_the_file_doesnt_depend_on_the_servers_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # the self-test's server wrote to /tmp while it looked in TMPDIR: the MCP client doesn't pass that on
    monkeypatch.undo()
    monkeypatch.setenv('TMPDIR', str(tmp_path))
    tempfile.tempdir = None
    try:
        path = server.agent_designer_file()
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
    patch_server(monkeypatch, '_send', lambda request, wait: {'ok': True, 'output': 'idle, 0 queued'})
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: 'process 11')
    assert 'Not started by an agent' in server.designer_status()
    _an_agent_started(11)
    assert 'Started by an agent' in server.designer_status()


def test_designer_status_goes_by_the_designer_answering(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-73: the record names one process, the package list comes from whichever holds the port
    _Processes(monkeypatch, 11, 12)
    _an_agent_started(12)
    patch_server(monkeypatch, '_send', lambda request, wait: {'ok': True, 'output': 'idle, 0 queued'})
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: 'process 11')
    assert 'Not started by an agent' in server.designer_status()
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: 'process 12')
    assert 'Started by an agent' in server.designer_status()


def test_designer_status_while_a_job_runs_cant_tell_two_apart(monkeypatch: pytest.MonkeyPatch) -> None:
    processes = _Processes(monkeypatch, 11, 12)
    _an_agent_started(12)
    patch_server(monkeypatch, '_send', lambda request, wait: {'ok': True, 'output': 'running for 4.0s, 0 queued'})
    assert 'Not started by an agent' in server.designer_status(), "unclear counts as the user's"
    processes.pids.remove(11)
    assert 'Started by an agent' in server.designer_status()


# --- closing it


def _closes(monkeypatch: pytest.MonkeyPatch, said: str = 'closing Designer') -> list[str]:
    asked: list[str] = []

    def bridge(code: str, path: str | None = None, timeout: float | None = None, wait: float | None = None) -> str:
        asked.append(code)
        return said

    patch_server(monkeypatch, '_bridge', bridge)
    patch_server(monkeypatch, '_send', lambda request, wait: {'ok': True, 'output': 'idle, 0 queued'})
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
    assert not processes.signals and not Path(server.agent_designer_file()).exists()


def test_quit_forces_an_agents_that_stays(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    # REVIEW.md HLP-82: Designer can hang at the very end of its shutdown, past anything inside it
    processes = _Processes(monkeypatch, 11)
    _an_agent_started(11)
    _closes(monkeypatch)
    text = server.quit_designer(wait_s=3)
    assert 'forced' in text and processes.signals == [(11, signal.SIGTERM)]
    assert not Path(server.agent_designer_file()).exists()


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

    def dead(code: str, path: str | None = None, timeout: float | None = None, wait: float | None = None) -> str:
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

    def frozen(request: dict[str, Any], wait: float) -> Reply:
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
    patch_server(monkeypatch, '_send', lambda request, wait: {'ok': True, 'output': state})
    text = server.quit_designer(wait_s=1)
    assert not asked and processes.signals == [(11, signal.SIGTERM)]
    assert 'not asked to close' in text and state in text and 'forced' in text


def test_a_process_gone_or_not_ours_to_signal_doesnt_raise(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    processes = _Processes(monkeypatch, 11)

    def refuses(pid: int, sig: int) -> None:
        processes.pids.clear()
        raise ProcessLookupError

    monkeypatch.setattr(os, 'kill', refuses)
    assert server._force_end(11) is True
    processes.pids.append(11)

    def denied(pid: int, sig: int) -> None:
        raise PermissionError

    monkeypatch.setattr(os, 'kill', denied)
    assert server._force_end(11) is False
