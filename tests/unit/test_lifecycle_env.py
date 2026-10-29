"""launch/quit paths that can't be produced safely with a real Designer, environment-variable
overrides (README, Configuration), log filtering and the missing-tools message."""
import os
import subprocess
import sys

import pytest

from conftest import ROOT, server


def _no_bridge(request, wait):
    raise server.ToolError('Designer is not reachable.')


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(server.time, 'sleep', lambda s: None)


def test_launch_reports_missing_app(monkeypatch):
    monkeypatch.setattr(server, '_send', _no_bridge)
    monkeypatch.setenv('SD_DESIGNER_APP', '/no/such/Designer.app')
    with pytest.raises(server.ToolError, match='Designer not found'):
        server.launch_designer()


def test_launch_times_out_when_the_bridge_never_answers(monkeypatch, tmp_path, no_sleep):
    started = []
    monkeypatch.setattr(server, '_send', _no_bridge)
    monkeypatch.setenv('SD_DESIGNER_APP', str(tmp_path))                 # exists
    monkeypatch.setattr(server.subprocess, 'Popen', lambda cmd: started.append(cmd))
    monkeypatch.setattr(server.os, 'startfile', lambda p: started.append(p), raising=False)
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(server.time, 'time', lambda: next(clock))
    with pytest.raises(server.ToolError, match='did not answer within 30s'):
        server.launch_designer(wait_s=30)
    assert started, 'Designer was never started'


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
    for parts in (('plugin', 'sd_bridge', 'sd_bridge', '__init__.py'), ('mcp_server', 'server.py'), ('client', 'sd_run.py')):
        with open(os.path.join(ROOT, *parts)) as f:
            assert "os.environ.get('SD_BRIDGE_PORT'" in f.read(), parts


LOG = '''old run [ERROR] stale error
[INFO] Python SDK Version 1.0
[INFO] [sd_bridge] v2 listening on 127.0.0.1:9877
[WARNING] something odd
[ERROR] Traceback (most recent call last)
[INFO] ready'''


def test_read_log_from_sd_designer_log(monkeypatch, tmp_path):
    log = tmp_path / 'log.txt'
    log.write_text(LOG)
    monkeypatch.setenv('SD_DESIGNER_LOG', str(log))
    body = lambda t: t.splitlines()[1:]
    assert body(server.read_designer_log()) == LOG.splitlines()[1:]                     # since the last start
    assert body(server.read_designer_log(since_last_start=False)) == LOG.splitlines()
    assert body(server.read_designer_log(errors_only=True)) == ['[WARNING] something odd',
                                                                 '[ERROR] Traceback (most recent call last)']
    assert body(server.read_designer_log(contains='SD_BRIDGE')) == ['[INFO] [sd_bridge] v2 listening on 127.0.0.1:9877']
    assert server.read_designer_log(lines=1).startswith('%s (5 matching lines, showing 1)' % log)
    monkeypatch.setenv('SD_DESIGNER_LOG', str(tmp_path / 'missing.txt'))
    with pytest.raises(server.ToolError, match='log not found'):
        server.read_designer_log()


def test_render_tools_missing(monkeypatch):
    monkeypatch.setattr(server, 'SBSRENDER', None)
    for call in (lambda: server.render_sbs('x.sbs', '/tmp/out'), lambda: server.sbsar_info('x.sbs')):
        with pytest.raises(server.ToolError, match='SD_DESIGNER_BIN_DIR'):
            call()
