"""launch/quit paths that can't be produced safely with a real Designer, environment-variable
overrides (README, Configuration), log filtering and the missing-tools message."""
import os
import re
import subprocess
import sys

import pytest

from conftest import ROOT, server
from project_constants import PLUGIN, PLUGIN_PACKAGE_DIR


def _no_bridge(request, wait):
    raise server.ToolError('Designer is not reachable.')


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(server.time, 'sleep', lambda s: None)


def test_launch_reports_missing_app(monkeypatch):
    monkeypatch.setattr(server, '_send', _no_bridge)
    monkeypatch.setattr(server, '_designer_running', lambda: False)
    monkeypatch.setenv('SD_DESIGNER_APP', '/no/such/Designer.app')
    with pytest.raises(server.ToolError, match='Designer not found'):
        server.launch_designer()


def test_launch_times_out_when_the_bridge_never_answers(monkeypatch, tmp_path, no_sleep):
    started = []
    monkeypatch.setattr(server, '_send', _no_bridge)
    monkeypatch.setattr(server, '_designer_running', lambda: False)
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))                 # exists
    monkeypatch.setattr(server.subprocess, 'Popen', lambda cmd: started.append(cmd))
    monkeypatch.setattr(server.os, 'startfile', lambda p: started.append(p), raising=False)
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(server.time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError, match='did not answer within 30s'):
        server.launch_designer(wait_s=30)
    assert started, 'Designer was never started'


def test_launch_waits_for_a_running_designer_instead_of_starting_another(monkeypatch, tmp_path, no_sleep):
    # REVIEW.md SRV-10: a running Designer whose bridge doesn't answer (still starting, a dialog,
    # the plugin failed to load) was launched again: a second instance on Windows
    started, home = [], []
    monkeypatch.setattr(server, '_send', _no_bridge)
    monkeypatch.setattr(server, '_designer_running', lambda: True)
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(server.subprocess, 'Popen', lambda cmd: started.append(cmd))
    monkeypatch.setattr(server.os, 'startfile', lambda p: started.append(p), raising=False)
    monkeypatch.setattr(server, '_bridge', lambda code, path=None, timeout=None: home.append(code) or '')
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(server.time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError) as error:
        server.launch_designer(wait_s=30)
    assert not started, 'started a second Designer'
    assert 'already running' in str(error.value) and 'did not answer within 30s' in str(error.value)
    # once it answers: reported as already running, and its Home screen is left alone
    answers = iter([server.ToolError('not yet'), {'output': 'idle'}])

    def bridge_comes_up(request, wait):
        a = next(answers)
        if isinstance(a, Exception):
            raise a
        return a
    monkeypatch.setattr(server, '_send', bridge_comes_up)
    monkeypatch.setattr(server.time, 'time', lambda: 0)
    assert server.launch_designer(wait_s=30).startswith('Designer already running')
    assert not started and not home


def test_quit_when_not_running(monkeypatch):
    monkeypatch.setattr(server, '_send', _no_bridge)
    monkeypatch.setattr(server, '_designer_running', lambda: False)
    assert server.quit_designer() == 'Designer is not running.'


def test_quit_when_the_bridge_is_dead(monkeypatch):
    monkeypatch.setattr(server, '_send', _no_bridge)
    monkeypatch.setattr(server, '_designer_running', lambda: True)
    with pytest.raises(server.ToolError, match='bridge does not answer'):
        server.quit_designer()


def test_quit_times_out(monkeypatch, no_sleep):
    monkeypatch.setattr(server, '_send', lambda request, wait: {'ok': True, 'output': 'idle'})
    monkeypatch.setattr(server, '_bridge', lambda code, path=None, timeout=None: 'closing Designer')
    monkeypatch.setattr(server, '_designer_running', lambda: True)
    clock = iter(range(0, 1000))
    monkeypatch.setattr(server.time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError, match='still running after 5s'):
        server.quit_designer(wait_s=5)


def _import_server_with(env):
    code = ('import sys; sys.path.insert(0, %r); import server; '
            'print(server.SNAPSHOT_DIR); print(server.PORT); print(server.SBSRENDER)') % os.path.join(ROOT, 'mcp_server')
    out = subprocess.run([sys.executable, '-c', code], env={**os.environ, **env}, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout.splitlines()


def test_environment_overrides(tmp_path):
    fake = tmp_path / ('sbsrender.exe' if sys.platform == 'win32' else 'sbsrender')
    fake.write_text('')
    snap_dir, port, render = _import_server_with({'SD_SNAPSHOT_DIR': str(tmp_path / 'snaps'),
                                                   'SD_BRIDGE_PORT': '9999', 'SD_DESIGNER_BIN_DIR': str(tmp_path)})
    assert (snap_dir, port, render) == (str(tmp_path / 'snaps'), '9999', str(fake))


def test_every_component_reads_the_port_variable():
    # a port change must be made for the plugin and the server alike (README, Configuration)
    for path in (os.path.join(PLUGIN_PACKAGE_DIR, '__init__.py'), os.path.join(ROOT, 'mcp_server', 'server.py'),
                 os.path.join(ROOT, 'client', 'sd_run.py')):
        with open(path) as f:
            assert "os.environ.get('SD_BRIDGE_PORT'" in f.read(), path


LOG = '''old run [ERROR] stale error
[INFO] Python SDK Version 1.0
[INFO] [%s] v2 listening on 127.0.0.1:9877
[WARNING] something odd
[ERROR] Traceback (most recent call last)
[INFO] ready''' % PLUGIN


def test_read_log_from_sd_designer_log(monkeypatch, tmp_path):
    log = tmp_path / 'log.txt'
    log.write_text(LOG)
    monkeypatch.setenv('SD_DESIGNER_LOG', str(log))
    body = lambda t: t.splitlines()[1:]
    assert body(server.read_designer_log()) == LOG.splitlines()[1:]                     # since the last start
    assert body(server.read_designer_log(since_last_start=False)) == LOG.splitlines()
    assert body(server.read_designer_log(errors_only=True)) == ['[WARNING] something odd',
                                                                 '[ERROR] Traceback (most recent call last)']
    assert body(server.read_designer_log(contains=PLUGIN.upper())) == ['[INFO] [%s] v2 listening on 127.0.0.1:9877' % PLUGIN]
    assert server.read_designer_log(lines=1).startswith('%s (5 matching lines, showing 1)' % log)
    monkeypatch.setenv('SD_DESIGNER_LOG', str(tmp_path / 'missing.txt'))
    with pytest.raises(server.ToolError, match='log not found'):
        server.read_designer_log()


def test_render_tools_missing(monkeypatch):
    monkeypatch.setattr(server, 'SBSRENDER', None)
    for call in (lambda: server.render_sbs('x.sbs', '/tmp/out'), lambda: server.sbsar_info('x.sbs')):
        with pytest.raises(server.ToolError, match='SD_DESIGNER_BIN_DIR'):
            call()


def test_scripts_and_tool_output_are_read_as_utf8_whatever_the_locale(tmp_path):
    # REVIEW.md SRV-11: run_designer_script read the file in the locale's encoding (cp1252 on
    # many Windows machines), and _run_tool decoded sbsrender's output the same way. A Latin-1
    # locale with UTF-8 mode off stands in for cp1252 here.
    script = tmp_path / 's.py'
    script.write_text("print('→ é ✓')\n", encoding='utf-8')
    probe = (
        "import sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
        "import server\n"
        "server._bridge = lambda code, path=None, timeout=None: code\n"
        "sent = server.run_designer_script(%r)\n"
        "print('SCRIPT_OK' if \"print('→ é ✓')\" in sent else 'SCRIPT_BAD')\n"
        "r = server._run_tool([sys.executable, '-c', \"import sys; sys.stdout.buffer.write('→ ✓'.encode())\"], 30)\n"
        "print('TOOL_OK' if r.stdout == '→ ✓' else 'TOOL_BAD %%r' %% r.stdout)\n"
    ) % (os.path.join(ROOT, 'mcp_server'), ROOT, str(script))
    env = dict(os.environ, LC_ALL='en_US.ISO8859-1', PYTHONIOENCODING='utf-8')
    env.pop('PYTHONUTF8', None)
    out = subprocess.run([sys.executable, '-X', 'utf8=0', '-c', probe], capture_output=True, text=True,
                         encoding='utf-8', errors='replace', env=env, cwd=str(tmp_path))
    assert 'SCRIPT_OK' in out.stdout and 'TOOL_OK' in out.stdout, out.stdout + out.stderr


def test_launch_starts_designer_when_the_running_one_exits_during_the_wait(monkeypatch, tmp_path, no_sleep):
    # REVIEW.md SRV-15: the process was looked for once; when that Designer (shutting down, or hung
    # after a crash) went away during the wait, nothing was started and the error still said
    # "already running"
    started = []
    processes = iter([True, True, False])                 # there at first, then gone
    monkeypatch.setattr(server, '_designer_running', lambda: next(processes, False))
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(server.subprocess, 'Popen', lambda cmd: started.append(cmd))
    monkeypatch.setattr(server.os, 'startfile', lambda p: started.append(p), raising=False)

    def bridge(request, wait):
        if not started:
            raise server.ToolError('Designer is not reachable.')
        return {'output': 'idle'}
    monkeypatch.setattr(server, '_send', bridge)
    monkeypatch.setattr(server, '_bridge', lambda code, path=None, timeout=None: '')
    clock = iter(range(0, 1000, 5))
    monkeypatch.setattr(server.time, 'time', lambda: next(clock))
    assert server.launch_designer(wait_s=60).startswith('Designer started in')
    assert len(started) == 1


def test_a_restarted_designer_gets_the_whole_wait(monkeypatch, tmp_path, no_sleep):
    # REVIEW.md SRV-19: after the old process went away late in the wait, the new Designer got
    # only what was left of wait_s, and "started in" counted the wait for the old one
    started = []
    processes = iter([True] + [True] * 33 + [False])      # the old one goes away at ~175 s of 180 (SRV-21)
    monkeypatch.setattr(server, '_designer_running', lambda: next(processes, False))
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))
    monkeypatch.setattr(server.subprocess, 'Popen', lambda cmd: started.append(now[0]))
    monkeypatch.setattr(server.os, 'startfile', lambda p: started.append(now[0]), raising=False)
    now = [0]

    def clock():
        now[0] += 5
        return now[0]
    monkeypatch.setattr(server.time, 'time', clock)

    def bridge(request, wait):
        if not started or now[0] < started[0] + 60:      # the new one needs 60 s to come up
            raise server.ToolError('Designer is not reachable.')
        return {'output': 'idle'}
    monkeypatch.setattr(server, '_send', bridge)
    monkeypatch.setattr(server, '_bridge', lambda code, path=None, timeout=None: '')
    text = server.launch_designer(wait_s=180)
    seconds = int(re.search(r'started in (\d+)s', text).group(1))
    assert seconds <= 90, text                            # timed from the restart, not the first call
