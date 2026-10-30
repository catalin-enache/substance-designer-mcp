"""Server fixes from the code review: regions, snapshots, cooking, the Windows process check,
connection errors, 16-bit previews, render_sbs size notes."""
import os
import re
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


def test_snapshot_latest_is_the_live_graph_after_set_link_display(monkeypatch, tmp_path):
    # REVIEW.md SRV-1: set_link_display writes '<stamp>-before_portals.sbs' (the live graph) and,
    # usually in the same second, '<stamp>-before_portals_file_on_disk.sbs' (a copy2 of the older
    # saved file). "latest" must be the live graph, not the copy that sorts last by name.
    import shutil
    monkeypatch.setattr(server, 'SNAPSHOT_DIR', str(tmp_path))
    monkeypatch.setattr(server.time, 'strftime', lambda fmt: '20261029-170000')
    saved = tmp_path / 'saved.sbs'
    saved.write_text('old saved file')
    os.utime(saved, (1, 1))                                   # saved long before
    live = server._new_snapshot_path('g', 'before portals')
    with open(live, 'w') as f:
        f.write('live graph')
    shutil.copy2(str(saved), server._new_snapshot_path('g', 'before portals (file on disk)'))
    assert server._snapshots('g')[-1] == live


def test_sweep_reports_a_value_that_failed(monkeypatch):
    # REVIEW.md SRV-2: tiles for the first values, then an error, then "restored" from the finally
    def fake_bridge(code, path=None, timeout=None):
        out_dir = re.search(r"(/[^'\\]*sd_sweep_\w+)", code).group(1)
        with open(os.path.join(out_dir, '0.raw'), 'wb') as f:
            f.write(bytes([128]))
        return ('SWEEP={"index": 0, "value": 0.1, "width": 1, "height": 1, "pitch": 1, "bpp": 1, "format": "LUM8"}\n'
                'restored n.p to 0.5\n--- ERROR ---\nTraceback ...\nRuntimeError: bad value for p')
    monkeypatch.setattr(server, '_bridge', fake_bridge)
    text = server.sweep_param('n', 'p', [0.1, 'bogus', 0.9])[0]
    assert 'RuntimeError: bad value for p' in text and 'stopped' in text


def test_quick_edits_have_time_for_a_big_batch(monkeypatch):
    # REVIEW.md SRV-5: one 60 s limit for a whole apply_edits batch (or an import, a layout)
    seen = []
    monkeypatch.setattr(server, '_bridge', lambda code, path=None, timeout=None: seen.append(timeout) or 'ok')
    server.apply_edits([{'op': 'move', 'node_id': '1', 'position': [0, 0]}] * 50, graph='g')
    assert seen and seen[0] >= 300


def test_designer_status_reports_the_servers_versions(monkeypatch):
    # REVIEW.md SRV-13: the server's own Python and library versions
    import platform
    monkeypatch.setattr(server, '_send', lambda request, wait: {'ok': True, 'output': 'bridge idle'})
    monkeypatch.setattr(server, '_bridge', lambda code, path=None, timeout=None: 'Designer 16.0.7')
    text = server.designer_status()
    assert 'MCP server: Python %s' % platform.python_version() in text
    assert 'mcp ' in text and 'pillow ' in text and 'numpy ' in text


def test_sbsar_info_reports_a_failed_sbsrender(monkeypatch):
    # REVIEW.md SRV-6: a failing `sbsrender info` came back as a normal result
    import contextlib
    import subprocess
    monkeypatch.setattr(server, 'SBSCOOKER', 'sbscooker')
    monkeypatch.setattr(server, 'SBSRENDER', 'sbsrender')
    monkeypatch.setattr(server, '_cooked', lambda path: contextlib.nullcontext('/tmp/x.sbsar'))
    monkeypatch.setattr(server, '_run_tool', lambda cmd, timeout: subprocess.CompletedProcess(
        cmd, 1, '', '[ERROR] Unable to open /tmp/x.sbsar'))
    with pytest.raises(server.ToolError) as error:
        server.sbsar_info('/tmp/x.sbs')
    assert 'Unable to open' in str(error.value)


def test_compare_ignores_transparent_pixels_of_a_grayscale_alpha_reference(tmp_path):
    # REVIEW.md SRV-9: an 'LA' reference was converted to 'L', so its transparent pixels counted
    a = np.zeros((4, 8, 2), np.uint8)
    a[:, :4] = (128, 255)                      # left half opaque mid-grey
    a[:, 4:] = (0, 0)                          # right half transparent black
    Image.fromarray(a, 'LA').save(tmp_path / 'la.png')
    ref, layout = server._load_reference(str(tmp_path / 'la.png'))
    lines, _ = server._compare_report(np.full((4, 8, 1), 128 / 255), 'L', ref, layout)
    text = '\n'.join(lines)
    assert 'ignoring 50.0% transparent reference pixels' in text
    assert re.search(r'^luma .*\+0\.000', text, re.M), text


def _sbs(tmp_path, graph_body):
    path = tmp_path / 'p.sbs'
    path.write_text('<?xml version="1.0" encoding="UTF-8"?><package><content><graph>'
                    '<identifier v="g"/>%s</graph></content></package>' % graph_body)
    return path


def test_links_of_a_graph_without_nodes():
    # REVIEW.md SRV-12: a graph without <compNodes> raised TypeError instead of counting 0 links
    import xml.etree.ElementTree as ET
    g = ET.fromstring('<graph><identifier v="g"/></graph>')
    assert server._select_links(g, 'portal', fanout_at_least=1) == ([], 0, 0)


@pytest.mark.parametrize('case', ['no pngs', 'unknown name', 'missing folder'])
def test_preview_maps_explains_what_is_missing(tmp_path, case):
    # REVIEW.md SRV-12: these raised ValueError / FileNotFoundError from PIL or os
    if case != 'no pngs':
        Image.new('L', (4, 4)).save(tmp_path / 'height.png')
    folder = tmp_path / 'nowhere' if case == 'missing folder' else tmp_path
    with pytest.raises(server.ToolError) as error:
        server.preview_maps(str(folder), names=['roughness'] if case == 'unknown name' else None)
    assert {'no pngs': 'no .png files', 'unknown name': "'roughness'",
            'missing folder': 'not a folder'}[case] in str(error.value)


def test_set_link_display_reports_success_when_the_reopen_fails(monkeypatch, tmp_path):
    # REVIEW.md SRV-12: after the edit and reload, an ambiguous reopen was reported as a failure
    sbs = _sbs(tmp_path, '<compNodes><compNode><uid v="1"/></compNode><compNode><uid v="2"/><connections>'
                         '<connection><identifier v="input1"/><connRef v="1"/></connection>'
                         '</connections></compNode></compNodes>')
    live = tmp_path / 'live.sbs'
    live.write_bytes(sbs.read_bytes())
    monkeypatch.setattr(server, 'SNAPSHOT_DIR', str(tmp_path / 'snaps'))
    monkeypatch.setattr(server, '_bridge', lambda code, path=None, timeout=None:
                        'FILE=%s\nGRAPH=g\nOPEN=1' % sbs)
    monkeypatch.setattr(server, 'snapshot_graph', lambda gid, label: 'saved: %s' % live)
    monkeypatch.setattr(server, '_reload_package_file', lambda path: None)

    def ambiguous(gid):
        raise server.ToolError("2 open graphs are called 'g'")
    monkeypatch.setattr(server, 'open_graph', ambiguous)
    text = server.set_link_display('g', from_nodes=['1'])
    assert '1 of 1 selected link(s) changed to portal' in text
    assert "could not reopen g: 2 open graphs are called 'g'" in text
    assert '<displayType v="1"' in sbs.read_text()


def test_set_link_displays_copy_of_the_saved_file_keeps_relative_paths_working(monkeypatch, tmp_path):
    # REVIEW.md SRV-14: the "file on disk" snapshot was a plain copy into the snapshot folder, but
    # Designer writes bitmap and dependency paths relative to the .sbs, so they pointed nowhere
    import xml.etree.ElementTree as ET
    project = tmp_path / 'project'
    (project / 'p.resources').mkdir(parents=True)
    (project / 'p.resources' / 'XXXXXX-img.png').write_bytes(b'png')
    (project / 'other.sbs').write_text('<package/>')
    sbs = project / 'p.sbs'
    sbs.write_text('<?xml version="1.0" encoding="UTF-8"?><package>'
                   '<dependencies><dependency><filename v="other.sbs"/></dependency>'
                   '<dependency><filename v="sbs://pattern_shape.sbs"/></dependency>'
                   '<dependency><filename v="?himself"/></dependency></dependencies>'
                   '<content><resource><identifier v="img"/><filepath v="p.resources/XXXXXX-img.png"/></resource>'
                   '<graph><identifier v="g"/><compNodes><compNode><uid v="1"/></compNode><compNode><uid v="2"/>'
                   '<connections><connection><identifier v="input1"/><connRef v="1"/></connection></connections>'
                   '</compNode></compNodes></graph></content></package>')
    os.utime(sbs, (1000, 1000))                                # saved long ago
    live = tmp_path / 'live.sbs'
    live.write_bytes(sbs.read_bytes())
    monkeypatch.setattr(server, 'SNAPSHOT_DIR', str(tmp_path / 'snaps'))
    monkeypatch.setattr(server, '_bridge', lambda code, path=None, timeout=None: 'FILE=%s\nGRAPH=g\nOPEN=0' % sbs)
    monkeypatch.setattr(server, 'snapshot_graph', lambda gid, label: 'saved: %s' % live)
    monkeypatch.setattr(server, '_reload_package_file', lambda path: None)
    server.set_link_display('g', from_nodes=['1'])
    copy = next(p for p in (tmp_path / 'snaps' / 'g').iterdir() if 'file_on_disk' in p.name)
    root = ET.parse(copy).getroot()
    paths = [e.get('v') for e in root.iter('filepath')] + [e.get('v') for e in root.iter('filename')]
    local = [p for p in paths if '://' not in p and not p.startswith('?')]
    missing = [p for p in local if not os.path.isfile(os.path.join(os.path.dirname(copy), p))]
    assert len(local) == 2 and not missing, 'paths %s, missing %s' % (paths, missing)
    assert 'sbs://pattern_shape.sbs' in paths                  # library references left alone
    assert '?himself' in paths                                 # the package's own graphs (REVIEW.md SRV-17)
    assert os.path.getmtime(copy) == 1000                      # still older than the live snapshot (SRV-1)


def test_designer_status_answers_while_a_job_runs(monkeypatch):
    # REVIEW.md SRV-22: the package listing queued behind the running job, so the status call
    # waited up to ~31 minutes although the plugin knew at once that it was busy
    monkeypatch.setattr(server, '_send', lambda request, wait: {'ok': True,
                        'output': '%s v3: running for 412.0s, 0 queued' % server.PLUGIN})
    queued = []
    monkeypatch.setattr(server, '_bridge', lambda code, path=None, timeout=None: queued.append(code) or 'packages')
    text = server.designer_status()
    assert 'running for 412.0s' in text and not queued and 'package list' in text


@pytest.mark.parametrize('crop, message', [([30, 0, 10, 8], 'empty'), ([100, 100, 120, 120], 'empty'),
                                           ([0, 0, 4], 'x0, y0, x1, y1')])
def test_preview_maps_checks_the_crop(tmp_path, crop, message):
    # REVIEW.md SRV-23: an inverted box raised PIL's ValueError; one outside the image gave a black tile
    Image.new('L', (32, 16), 200).save(tmp_path / 'height.png')
    with pytest.raises(server.ToolError, match=message):
        server.preview_maps(str(tmp_path), crop=crop)
