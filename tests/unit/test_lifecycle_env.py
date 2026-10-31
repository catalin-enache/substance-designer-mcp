"""launch/quit paths that can't be produced safely with a real Designer, designer_status,
environment-variable overrides (README, Configuration), log filtering and the missing-tools message."""

import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path
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
    with pytest.raises(server.ToolError, match='did not answer within 30s'):
        server.launch_designer(wait_s=30)
    assert started, 'Designer was never started'


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
    answers: Iterator[Exception | Reply] = iter([server.ToolError('not yet'), {'output': 'idle'}])

    def bridge_comes_up(request: dict[str, Any], wait: float) -> Reply:
        a = next(answers)
        if isinstance(a, Exception):
            raise a
        return a

    patch_server(monkeypatch, '_send', bridge_comes_up)
    monkeypatch.setattr(time, 'time', lambda: 0)
    assert server.launch_designer(wait_s=30).startswith('Designer already running')
    assert not started and not home


def test_quit_when_not_running(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_designer_running', lambda: False)
    assert server.quit_designer() == 'Designer is not running.'


def test_quit_when_the_bridge_is_dead(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_server(monkeypatch, '_send', _no_bridge)
    patch_server(monkeypatch, '_designer_running', lambda: True)
    with pytest.raises(server.ToolError, match='bridge does not answer'):
        server.quit_designer()


def test_quit_times_out(monkeypatch: pytest.MonkeyPatch, no_sleep: None) -> None:
    patch_server(monkeypatch, '_send', lambda request, wait: {'ok': True, 'output': 'idle'})
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: 'closing Designer')
    patch_server(monkeypatch, '_designer_running', lambda: True)
    clock = iter(range(1000))
    monkeypatch.setattr(time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError, match='still running after 5s'):
        server.quit_designer(wait_s=5)


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
        'import sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n'
        'import server, server_tools.scripting\n'
        'server_tools.scripting._bridge = lambda code, path=None, timeout=None: code\n'  # where the tool looks it up
        'sent = server.run_designer_script(%r)\n'
        "print('SCRIPT_OK' if \"print('→ é ✓')\" in sent else 'SCRIPT_BAD')\n"
        "r = server._run_tool([sys.executable, '-c', \"import sys; sys.stdout.buffer.write('→ ✓'.encode())\"], 30)\n"
        "print('TOOL_OK' if r.stdout == '→ ✓' else 'TOOL_BAD %%r' %% r.stdout)\n"
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
        return {'output': 'idle'}

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
        return {'output': 'idle'}

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
