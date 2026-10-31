"""set_link_display (server_tools/layout.py): the file-level edit, the copy of the saved file, the
reload in separate calls."""

import os
import time
from pathlib import Path
from typing import cast

import pytest

from conftest import patch_server, server


def test_reload_is_split_with_pauses(monkeypatch: pytest.MonkeyPatch) -> None:
    # unload, pause, load, pause: separate calls so Designer's event loop finishes tearing down
    # the old graph views before new ones are created (a back-to-back reload once crashed it)
    events: list[str] = []

    def bridge(code: str, path: str | None = None, timeout: float | None = None) -> str:
        events.append(code.rsplit('\n', 2)[-2].split('(')[0])
        return 'ok'

    patch_server(monkeypatch, '_bridge', bridge)
    monkeypatch.setattr(time, 'sleep', lambda s: events.append('sleep %.1f' % s))
    server._reload_package_file('/x/pkg.sbs')
    assert events == ['unload_package_file', 'sleep 0.5', 'load_package_file', 'sleep 0.5']


def _sbs(tmp_path: Path, graph_body: str) -> Path:
    path = tmp_path / 'p.sbs'
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?><package><content><graph>'
        '<identifier v="g"/>%s</graph></content></package>' % graph_body
    )
    return path


def test_set_link_display_reports_success_when_the_reopen_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-12: after the edit and reload, an ambiguous reopen was reported as a failure
    sbs = _sbs(
        tmp_path,
        '<compNodes><compNode><uid v="1"/></compNode><compNode><uid v="2"/><connections>'
        '<connection><identifier v="input1"/><connRef v="1"/></connection>'
        '</connections></compNode></compNodes>',
    )
    live = tmp_path / 'live.sbs'
    live.write_bytes(sbs.read_bytes())
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path / 'snaps'))
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: 'FILE=%s\nGRAPH=g\nOPEN=1' % sbs)
    patch_server(monkeypatch, 'snapshot_graph', lambda gid, label: 'saved: %s' % live)
    patch_server(monkeypatch, '_reload_package_file', lambda path, snapshot=None: None)

    def ambiguous(gid: str) -> str:
        raise server.ToolError("2 open graphs are called 'g'")

    patch_server(monkeypatch, 'open_graph', ambiguous)
    text = server.set_link_display('g', from_nodes=['1'])
    assert '1 of 1 selected link(s) changed to portal' in text
    assert "could not reopen g: 2 open graphs are called 'g'" in text
    assert '<displayType v="1"' in sbs.read_text()


def test_set_link_displays_copy_of_the_saved_file_keeps_relative_paths_working(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-14: the "file on disk" snapshot was a plain copy into the snapshot folder, but
    # Designer writes bitmap and dependency paths relative to the .sbs, so they pointed nowhere
    import xml.etree.ElementTree as ET

    project = tmp_path / 'project'
    (project / 'p.resources').mkdir(parents=True)
    (project / 'p.resources' / 'XXXXXX-img.png').write_bytes(b'png')
    (project / 'other.sbs').write_text('<package/>')
    sbs = project / 'p.sbs'
    sbs.write_text(
        '<?xml version="1.0" encoding="UTF-8"?><package>'
        '<dependencies><dependency><filename v="other.sbs"/></dependency>'
        '<dependency><filename v="sbs://pattern_shape.sbs"/></dependency>'
        '<dependency><filename v="?himself"/></dependency></dependencies>'
        '<content><resource><identifier v="img"/><filepath v="p.resources/XXXXXX-img.png"/></resource>'
        '<graph><identifier v="g"/><compNodes><compNode><uid v="1"/></compNode><compNode><uid v="2"/>'
        '<connections><connection><identifier v="input1"/><connRef v="1"/></connection></connections>'
        '</compNode></compNodes></graph></content></package>'
    )
    os.utime(sbs, (1000, 1000))  # saved long ago
    live = tmp_path / 'live.sbs'
    live.write_bytes(sbs.read_bytes())
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path / 'snaps'))
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: 'FILE=%s\nGRAPH=g\nOPEN=0' % sbs)
    patch_server(monkeypatch, 'snapshot_graph', lambda gid, label: 'saved: %s' % live)
    patch_server(monkeypatch, '_reload_package_file', lambda path, snapshot=None: None)
    server.set_link_display('g', from_nodes=['1'])
    copy = next(p for p in (tmp_path / 'snaps' / 'g').iterdir() if 'file_on_disk' in p.name)
    root = ET.parse(copy).getroot()
    paths = cast(list[str], [e.get('v') for e in root.iter('filepath')] + [e.get('v') for e in root.iter('filename')])
    local = [p for p in paths if '://' not in p and not p.startswith('?')]
    missing = [p for p in local if not os.path.isfile(os.path.join(os.path.dirname(copy), p))]
    assert len(local) == 2 and not missing, 'paths %s, missing %s' % (paths, missing)
    assert 'sbs://pattern_shape.sbs' in paths  # library references left alone
    assert '?himself' in paths  # the package's own graphs (REVIEW.md SRV-17)
    assert os.path.getmtime(copy) == 1000  # still older than the live snapshot (SRV-1)
