"""Server fixes from the code review: regions, snapshots, cooking, the Windows process check,
connection errors, 16-bit previews, render_sbs size notes."""
import os
import socket
import threading

import numpy as np
import pytest
from PIL import Image

from conftest import server


@pytest.mark.parametrize('region', [[10, 10, 5, 20], [0, 0, 0, 5], [50, 50, 60, 60], [1, 2, 3]])
def test_bad_regions_are_errors(region):
    with pytest.raises(server.ToolError):
        server._crop(np.zeros((20, 20, 1)), region, 'region')


def test_region_is_clamped_not_wrapped():
    data = np.arange(100).reshape(10, 10, 1)
    assert server._crop(data, [-5, -5, 2, 2], 'region').shape == (2, 2, 1)   # not data[-5:2] (empty)
    assert server._crop(data, [8, 8, 50, 50], 'region').shape == (2, 2, 1)


def test_snapshots_in_the_same_second_dont_overwrite(monkeypatch, tmp_path):
    monkeypatch.setattr(server, 'SNAPSHOT_DIR', str(tmp_path))
    monkeypatch.setattr(server.time, 'strftime', lambda fmt: '20261029-120000')   # all in one second
    paths = []
    for _ in range(3):                         # each taken (written) before the next is named
        paths.append(server._new_snapshot_path('g', 'before x'))
        open(paths[-1], 'w').close()
    assert len(set(paths)) == 3
    names = [os.path.basename(p) for p in paths]
    assert names[1].split('-before')[0].endswith('_2') and names[2].split('-before')[0].endswith('_3')


def test_snapshot_label_matches_exactly(monkeypatch, tmp_path):
    monkeypatch.setattr(server, 'SNAPSHOT_DIR', str(tmp_path))
    for label in ('tweak', 'big tweak'):
        open(server._new_snapshot_path('g', label), 'w').close()
    labels = [server._SNAPSHOT_NAME.match(os.path.basename(p)).group(1) for p in server._snapshots('g')]
    assert sorted(labels) == ['big_tweak', 'tweak']
    assert [p for p in server._snapshots('g') if server._SNAPSHOT_NAME.match(os.path.basename(p)).group(1)
            == server._safe_name('tweak')] == [p for p in server._snapshots('g') if p.endswith('-tweak.sbs')
                                               and not p.endswith('big_tweak.sbs')]


def test_cooking_never_writes_next_to_the_users_file(monkeypatch, tmp_path):
    sbs = tmp_path / 'mine.sbs'
    sbs.write_text('<package/>')
    (tmp_path / 'mine.sbsar').write_text('MY OWN SBSAR')
    calls = []

    def fake_cooker(cmd, timeout):
        out = cmd[cmd.index('--output-path') + 1]
        calls.append(out)
        open(os.path.join(out, 'mine.sbsar'), 'w').write('cooked')
        return type('R', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()
    monkeypatch.setattr(server, '_run_tool', fake_cooker)
    with server._cooked(str(sbs)) as sbsar:
        assert open(sbsar).read() == 'cooked' and os.path.dirname(sbsar) != str(tmp_path)
    assert not os.path.exists(calls[0])                          # temporary folder removed
    assert (tmp_path / 'mine.sbsar').read_text() == 'MY OWN SBSAR'


def test_cooker_failure_is_reported(monkeypatch, tmp_path):
    monkeypatch.setattr(server, '_run_tool', lambda cmd, timeout: type('R', (), {
        'returncode': 1, 'stdout': 'boom', 'stderr': ''})())
    with pytest.raises(server.ToolError, match='sbscooker failed'):
        with server._cooked(str(tmp_path / 'x.sbs')):
            pass


def test_tool_timeout_becomes_a_tool_error():
    with pytest.raises(server.ToolError, match='did not finish within 1s'):
        server._run_tool(['sleep', '5'], 1)


def test_windows_process_check_reads_full_names(monkeypatch):
    # tasklist's table cuts names to 25 characters; the CSV form doesn't
    monkeypatch.setattr(server.sys, 'platform', 'win32')
    outputs = {'running': '"Adobe Substance 3D Designer.exe","1234","Console","1","2,000,000 K"\r\n',
               'gone': 'INFO: No tasks are running which match the specified criteria.\r\n'}
    for state, out in outputs.items():
        monkeypatch.setattr(server.subprocess, 'run', lambda cmd, **kw: type('R', (), {'stdout': out})())
        assert server._designer_running() == (state == 'running')


@pytest.mark.parametrize('reply', [b'', b'{"nonce": "n"}\n', b'{"nonce": "n"}\nnot json', b'garbage\n'])
def test_bad_replies_become_tool_errors(monkeypatch, tmp_path, reply):
    token = tmp_path / 'token'
    token.write_text('t' * 64)
    monkeypatch.setattr(server, 'TOKEN_FILE', str(token))
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    monkeypatch.setattr(server, 'PORT', listener.getsockname()[1])

    def answer():
        conn, _ = listener.accept()
        with conn:
            conn.sendall(reply)
    thread = threading.Thread(target=answer)
    thread.start()
    with pytest.raises(server.ToolError):
        server._send({'cmd': 'status'}, wait=5)
    thread.join(5)
    listener.close()


def test_dark_16bit_map_is_not_brightened(tmp_path):
    path = tmp_path / 'dark.png'
    Image.fromarray(np.full((4, 4), 200, np.uint16)).save(path)      # 200/65535: nearly black
    assert np.array(server._load_8bit(str(path))).max() <= 1


def _render_with(monkeypatch, tmp_path, exposed, sbs_name='two_graphs.sbs', **kw):
    from conftest import FIXTURES
    import shutil
    sbs = tmp_path / sbs_name
    shutil.copy(os.path.join(FIXTURES, sbs_name), sbs)
    seen = {}
    monkeypatch.setattr(server, 'SBSCOOKER', 'sbscooker')
    monkeypatch.setattr(server, 'SBSRENDER', 'sbsrender')
    monkeypatch.setattr(server, '_exposed_inputs', lambda sbsar: exposed)

    class _Cooked:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            return str(self.path) + 'ar' if str(self.path).endswith('.sbs') else str(self.path)

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(server, '_cooked', _Cooked)

    def fake_render(cmd, timeout):
        seen['cmd'] = cmd
        out = cmd[cmd.index('--output-path') + 1]
        Image.new('L', (8, 8)).save(os.path.join(out, 'height.png'))
        return type('R', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()
    monkeypatch.setattr(server, '_run_tool', fake_render)
    text = server.render_sbs(str(sbs), str(tmp_path / 'out'), **kw)
    return text, seen['cmd']


def test_render_uses_the_graphs_default_size(monkeypatch, tmp_path):
    text, cmd = _render_with(monkeypatch, tmp_path, {'$outputsize'}, graph='alpha')
    assert '$outputsize@9,9' in cmd and '--input-graph' in cmd and 'pkg://alpha' in cmd
    assert "default parent size, 512 px" in text


def test_render_with_disagreeing_graphs_says_so(monkeypatch, tmp_path):
    text, cmd = _render_with(monkeypatch, tmp_path, {'$outputsize'})
    assert not any(a.startswith('$outputsize@') for a in cmd)
    assert 'different default sizes' in text


def test_render_warns_about_unexposed_inputs(monkeypatch, tmp_path):
    text, cmd = _render_with(monkeypatch, tmp_path, set(), graph='alpha', params={'wear': 0.5}, size_log2=10)
    assert "input 'wear' is not exposed" in text and "input '$outputsize' is not exposed" in text
    assert 'graph output size is fixed' in text


def test_reload_is_split_with_pauses(monkeypatch):
    # unload, pause, load, pause: separate calls so Designer's event loop finishes tearing down
    # the old graph views before new ones are created (a back-to-back reload once crashed it)
    events = []
    monkeypatch.setattr(server, '_bridge', lambda code, path=None, timeout=None:
                        events.append(code.rsplit('\n', 2)[-2].split('(')[0]) or 'ok')
    monkeypatch.setattr(server.time, 'sleep', lambda s: events.append('sleep %.1f' % s))
    server._reload_package_file('/x/pkg.sbs')
    assert events == ['unload_package_file', 'sleep 0.5', 'load_package_file', 'sleep 0.5']
