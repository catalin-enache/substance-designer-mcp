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

    def bridge(code: str, path: str | None = None, timeout: float | None = None) -> str:
        if 'open_graph(graph_in_file(' in code:  # the reopen, through the package file (REVIEW.md SRV-34)
            return "--- ERROR ---\nRuntimeError: graph 'g' not found in the package %s" % sbs
        return 'FILE=%s\nGRAPH=g\nOPEN=1' % sbs

    patch_server(monkeypatch, '_bridge', bridge)
    patch_server(monkeypatch, 'snapshot_graph', lambda gid, label: 'saved: %s' % live)
    patch_server(monkeypatch, '_reload_package_file', lambda path, snapshot=None: None)
    os.chmod(sbs, 0o644)
    text = server.set_link_display('g', from_nodes=['1'])
    assert '1 of 1 selected link(s) changed to portal' in text
    assert "could not reopen g: RuntimeError: graph 'g' not found in the package" in text
    assert '<displayType v="1"' in sbs.read_text()
    # the edited file replaced the user's with its permissions, and no temporary file is left (SRV-46)
    assert os.stat(sbs).st_mode & 0o777 == 0o644
    assert not [p.name for p in tmp_path.iterdir() if p.name.endswith('.tmp')]


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
        '<?xml version="1.0" encoding="UTF-8"?><package><fileUID v="{5f3c0a6e-1111-2222-3333-444455556666}"/>'
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
    copy = next(p for p in (tmp_path / 'snaps' / 'g').rglob('*.sbs') if 'file_on_disk' in p.name)
    root = ET.parse(copy).getroot()
    paths = cast(list[str], [e.get('v') for e in root.iter('filepath')] + [e.get('v') for e in root.iter('filename')])
    local = [p for p in paths if '://' not in p and not p.startswith('?')]
    missing = [p for p in local if not os.path.isfile(os.path.join(os.path.dirname(copy), p))]
    assert len(local) == 2 and not missing, 'paths %s, missing %s' % (paths, missing)
    assert 'sbs://pattern_shape.sbs' in paths  # library references left alone
    assert '?himself' in paths  # the package's own graphs (REVIEW.md SRV-17)
    assert os.path.getmtime(copy) == 1000  # still older than the live snapshot (SRV-1)
    # a saved file's copy keeps its UID: the notes tell it apart by file (REVIEW.md SRV-42, Option 1b)
    assert server._v(root, 'fileUID') == '{5f3c0a6e-1111-2222-3333-444455556666}'


def test_set_link_displays_copy_of_the_saved_file_leaves_nothing_when_its_note_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-43: a copy whose note failed to write (a full disk) stayed without a note, counted for
    # every package; now it is removed, and nothing is changed (the error comes before the save)
    import builtins
    import errno
    from typing import Any

    sbs = tmp_path / 'p.sbs'
    content = (
        '<?xml version="1.0" encoding="UTF-8"?><package><fileUID v="{5f3c0a6e-1111-2222-3333-444455556666}"/>'
        '<dependencies/><content><graph><identifier v="g"/><compNodes><compNode><uid v="1"/></compNode>'
        '<compNode><uid v="2"/><connections><connection><identifier v="input1"/><connRef v="1"/></connection>'
        '</connections></compNode></compNodes></graph></content></package>'
    )
    sbs.write_text(content)
    live = tmp_path / 'live.sbs'
    live.write_text(content)
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path / 'snaps'))
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: 'FILE=%s\nGRAPH=g\nOPEN=0' % sbs)
    patch_server(monkeypatch, 'snapshot_graph', lambda gid, label: 'saved: %s' % live)
    reloaded: list[str] = []
    patch_server(monkeypatch, '_reload_package_file', lambda path, snapshot=None: reloaded.append(path))
    real_open = builtins.open

    def fake_open(file: Any, mode: str = 'r', *a: Any, **kw: Any) -> Any:
        if str(file).endswith('.sbs.json') and 'w' in mode:
            raise OSError(errno.ENOSPC, 'No space left on device')
        return real_open(file, mode, *a, **kw)

    monkeypatch.setattr(builtins, 'open', fake_open)
    with pytest.raises(OSError):
        server.set_link_display('g', from_nodes=['1'])
    assert not [p for p in (tmp_path / 'snaps').rglob('*') if p.is_file()]
    assert sbs.read_text() == content and not reloaded


def test_a_failed_write_of_the_temporary_file_leaves_the_users_file_as_saved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-46: the edited .sbs was written over the user's file in place, so a write that
    # failed partway (a full disk) left it truncated, right after a save, so nothing warned the user.
    # This covers that write failing: the file stays as saved, and the error names the snapshot (the rename
    # after it isn't reached here)
    import builtins
    import errno
    from typing import Any

    from mcp.server.mcpserver.exceptions import ToolError

    project = tmp_path / 'project'
    project.mkdir()
    sbs = project / 'p.sbs'
    content = (
        '<?xml version="1.0" encoding="UTF-8"?><package><fileUID v="{5f3c0a6e-1111-2222-3333-444455556666}"/>'
        '<dependencies/><content><graph><identifier v="g"/><compNodes><compNode><uid v="1"/></compNode>'
        '<compNode><uid v="2"/><connections><connection><identifier v="input1"/><connRef v="1"/></connection>'
        '</connections></compNode></compNodes></graph></content></package>'
    )
    sbs.write_text(content)
    live = tmp_path / 'live.sbs'
    live.write_text(content)
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path / 'snaps'))
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: 'FILE=%s\nGRAPH=g\nOPEN=0' % sbs)
    patch_server(monkeypatch, 'snapshot_graph', lambda gid, label: 'saved: %s' % live)
    reloaded: list[str] = []
    patch_server(monkeypatch, '_reload_package_file', lambda path, snapshot=None: reloaded.append(path))
    real_open = builtins.open

    def fake_open(file: Any, mode: str = 'r', *a: Any, **kw: Any) -> Any:
        # a full disk in the project folder: the file is opened (and emptied), then the write fails
        if str(file).startswith(str(project)) and ('w' in mode or 'a' in mode):
            real_open(file, mode, *a, **kw).close()
            raise OSError(errno.ENOSPC, 'No space left on device')
        return real_open(file, mode, *a, **kw)

    monkeypatch.setattr(builtins, 'open', fake_open)
    with pytest.raises(ToolError) as raised:
        server.set_link_display('g', from_nodes=['1'])
    monkeypatch.setattr(builtins, 'open', real_open)
    assert sbs.read_text() == content  # the saved file, untouched
    assert sorted(p.name for p in project.iterdir()) == ['p.sbs']  # no temporary file left
    assert str(live) in str(raised.value) and not reloaded


def _link_display_setup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sbs: Path) -> list[str]:
    """set_link_display on the package file sbs, with Designer faked; returns the reloaded paths."""
    live = tmp_path / 'live.sbs'
    live.write_text(sbs.read_text())
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path / 'snaps'))
    patch_server(monkeypatch, '_bridge', lambda code, path=None, timeout=None: 'FILE=%s\nGRAPH=g\nOPEN=0' % sbs)
    patch_server(monkeypatch, 'snapshot_graph', lambda gid, label: 'saved: %s' % live)
    reloaded: list[str] = []
    patch_server(monkeypatch, '_reload_package_file', lambda path, snapshot=None: reloaded.append(path))
    return reloaded


_ONE_LINK = (
    '<?xml version="1.0" encoding="UTF-8"?><package><dependencies/><content><graph><identifier v="g"/>'
    '<compNodes><compNode><uid v="1"/></compNode><compNode><uid v="2"/><connections><connection>'
    '<identifier v="input1"/><connRef v="1"/></connection></connections></compNode></compNodes>'
    '</graph></content></package>'
)


def test_set_link_display_edits_the_file_a_symlinked_sbs_points_to(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-48: the edited file was renamed over the path, so a symlinked .sbs became a plain file
    # and its target (the user's real file) kept the old content
    real = tmp_path / 'real'
    real.mkdir()
    target = real / 'p.sbs'
    target.write_text(_ONE_LINK)
    project = tmp_path / 'project'
    project.mkdir()
    link = project / 'p.sbs'
    link.symlink_to(target)
    _link_display_setup(monkeypatch, tmp_path, link)
    server.set_link_display('g', from_nodes=['1'])
    assert link.is_symlink() and os.readlink(link) == str(target)
    assert '<displayType v="1"' in target.read_text()
    assert sorted(p.name for p in real.iterdir()) == ['p.sbs'] and sorted(p.name for p in project.iterdir()) == [
        'p.sbs'
    ]


def test_set_link_display_in_a_folder_it_cant_write_reports_the_file_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-49: the temporary file was created outside the try, so a folder it can't write to gave a
    # bare OSError, not the error saying the file is unchanged
    from mcp.server.mcpserver.exceptions import ToolError

    project = tmp_path / 'project'
    project.mkdir()
    sbs = project / 'p.sbs'
    sbs.write_text(_ONE_LINK)
    reloaded = _link_display_setup(monkeypatch, tmp_path, sbs)
    os.chmod(project, 0o555)  # the file stays writable, the folder doesn't
    try:
        with pytest.raises(ToolError) as raised:
            server.set_link_display('g', from_nodes=['1'])
    finally:
        os.chmod(project, 0o755)
    assert 'unchanged' in str(raised.value) and sbs.read_text() == _ONE_LINK and not reloaded


def test_set_link_display_edits_every_name_of_a_hard_linked_sbs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-51: the rename gave the path a new file, so another hard-linked name of the .sbs kept the
    # saved content; the edit now reaches the file itself, under every name
    project = tmp_path / 'project'
    project.mkdir()
    sbs = project / 'p.sbs'
    sbs.write_text(_ONE_LINK)
    other = tmp_path / 'backup.sbs'
    os.link(sbs, other)
    _link_display_setup(monkeypatch, tmp_path, sbs)
    server.set_link_display('g', from_nodes=['1'])
    assert '<displayType v="1"' in sbs.read_text() and other.read_text() == sbs.read_text()
    assert os.stat(sbs).st_ino == os.stat(other).st_ino
    assert sorted(p.name for p in project.iterdir()) == ['p.sbs']


def test_a_hard_linked_sbs_that_cant_be_written_keeps_the_edit_and_says_where(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # SRV-51: written in place for its other names, a failed write must not lose the edit: the temporary
    # file stays, and the error names it and the snapshot
    import builtins
    import errno
    from typing import Any

    from mcp.server.mcpserver.exceptions import ToolError

    project = tmp_path / 'project'
    project.mkdir()
    sbs = project / 'p.sbs'
    sbs.write_text(_ONE_LINK)
    os.link(sbs, tmp_path / 'backup.sbs')
    _link_display_setup(monkeypatch, tmp_path, sbs)
    real_open = builtins.open

    def fake_open(file: Any, mode: str = 'r', *a: Any, **kw: Any) -> Any:
        if str(file) == str(sbs) and ('w' in mode or 'a' in mode):
            raise OSError(errno.ENOSPC, 'No space left on device')
        return real_open(file, mode, *a, **kw)

    monkeypatch.setattr(builtins, 'open', fake_open)
    with pytest.raises(ToolError) as raised:
        server.set_link_display('g', from_nodes=['1'])
    monkeypatch.setattr(builtins, 'open', real_open)
    kept = [p for p in project.iterdir() if p.name.endswith('.tmp')]
    assert len(kept) == 1 and '<displayType v="1"' in kept[0].read_text()
    assert str(kept[0]) in str(raised.value) and 'live.sbs' in str(raised.value)


def test_a_hard_linked_sbs_whose_temporary_file_cant_be_removed_still_counts_as_edited(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-52: with the edit already in the file, a failed removal of the temporary file reported
    # the file as unchanged and skipped the reload, leaving Designer's old graph over the edited file
    import errno
    from typing import Any

    project = tmp_path / 'project'
    project.mkdir()
    sbs = project / 'p.sbs'
    sbs.write_text(_ONE_LINK)
    other = tmp_path / 'backup.sbs'
    os.link(sbs, other)
    reloaded = _link_display_setup(monkeypatch, tmp_path, sbs)
    real_remove = os.remove

    def fake_remove(path: Any, **kw: Any) -> None:
        if str(path).startswith(str(project)) and str(path).endswith('.tmp'):
            raise OSError(errno.EACCES, 'Permission denied')
        real_remove(path, **kw)

    monkeypatch.setattr(os, 'remove', fake_remove)
    result = server.set_link_display('g', from_nodes=['1'])
    assert '1 of 1 selected link(s) changed to portal' in result and reloaded == [str(sbs)]
    assert '<displayType v="1"' in sbs.read_text() and other.read_text() == sbs.read_text()
    assert len([p for p in project.iterdir() if p.name.endswith('.tmp')]) == 1  # it just stays
