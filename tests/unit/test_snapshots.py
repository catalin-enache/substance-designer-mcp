"""Snapshots (server_tools/snapshots.py): file names, labels, which one is "latest"."""

import os
import time
from pathlib import Path
from typing import Any

import pytest

from conftest import patch_server, server


def test_snapshots_in_the_same_second_dont_overwrite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path))
    monkeypatch.setattr(time, 'strftime', lambda fmt: '20261029-120000')  # all in one second
    paths: list[str] = []
    for _ in range(3):  # each taken (written) before the next is named
        paths.append(server._new_snapshot_path('g', 'before x'))
        open(paths[-1], 'w').close()
    assert len(set(paths)) == 3
    names = [os.path.basename(p) for p in paths]
    assert names[1].split('-before')[0].endswith('_2') and names[2].split('-before')[0].endswith('_3')


def test_snapshot_label_matches_exactly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path))
    for label in ('tweak', 'big tweak'):
        open(server._new_snapshot_path('g', label), 'w').close()
    labels = [server._SNAPSHOT_NAME.match(os.path.basename(p)).group(1) for p in server._snapshots('g')]
    assert sorted(labels) == ['big_tweak', 'tweak']
    assert [
        p
        for p in server._snapshots('g')
        if server._SNAPSHOT_NAME.match(os.path.basename(p)).group(1) == server._safe_name('tweak')
    ] == [p for p in server._snapshots('g') if p.endswith('-tweak.sbs') and not p.endswith('big_tweak.sbs')]


def test_snapshot_latest_is_the_live_graph_after_set_link_display(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-1: set_link_display writes '<stamp>-before_portals.sbs' (the live graph) and,
    # usually in the same second, '<stamp>-before_portals_file_on_disk.sbs' (a copy2 of the older
    # saved file). "latest" must be the live graph, not the copy that sorts last by name.
    import shutil

    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path))
    monkeypatch.setattr(time, 'strftime', lambda fmt: '20261029-170000')
    saved = tmp_path / 'saved.sbs'
    saved.write_text('old saved file')
    os.utime(saved, (1, 1))  # saved long before
    live = server._new_snapshot_path('g', 'before portals')
    with open(live, 'w') as f:
        f.write('live graph')
    shutil.copy2(str(saved), server._new_snapshot_path('g', 'before portals (file on disk)'))
    assert server._snapshots('g')[-1] == live


def test_snapshots_of_two_packages_with_one_graph_name_stay_apart(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-34: snapshots were kept per graph identifier only, and every new graph is
    # "New_Graph": a diff of package B against 'latest' compared it with package A's snapshot
    import re
    from typing import Any

    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path / 'snaps'))
    xml = '<package><content><graph><identifier v="New_Graph"/><compNodes/></graph></content></package>'
    current = {'file': '/a/A.sbs', 'uid': '1a'}

    def bridge(code: str, *a: Any, **kw: Any) -> str:
        info = 'PACKAGE=%s\nPACKAGE_UID=%s\nGRAPH=New_Graph\n' % (current['file'], current['uid'])
        copy = re.search(r"save_package_copy\(.*?, '(.*?)'\)", code)
        if copy:
            os.makedirs(os.path.dirname(copy.group(1)), exist_ok=True)
            with open(copy.group(1), 'w') as f:
                f.write(xml)
            return 'COPY=%s\n' % copy.group(1) + info
        return info

    patch_server(monkeypatch, '_bridge', bridge)
    server.snapshot_graph('New_Graph')  # package A
    assert 'New_Graph' in server.list_snapshots('New_Graph')
    for other in ({'file': '/b/B.sbs', 'uid': '2b'}, {'file': '', 'uid': '3c'}, {'file': '', 'uid': '4d'}):
        current.update(other)  # another package with a graph of that name: saved, then two unsaved
        with pytest.raises(server.ToolError, match='no snapshots'):
            server.diff_graph('New_Graph', against='latest')
        server.snapshot_graph('New_Graph')
        assert server.diff_graph('New_Graph', against='latest').endswith('No differences.')
    assert server.list_snapshots('New_Graph').count('\n') == 3  # all four listed
    # the last unsaved package, saved now (its UID unchanged): still its own
    current['file'] = '/d/D.sbs'
    assert server.diff_graph('New_Graph', against='latest').endswith('No differences.')
    # the same file, whatever the UID, finds that file's snapshots
    current.update({'file': '/b/B.sbs', 'uid': '9z'})
    assert server.diff_graph('New_Graph', against='latest').endswith('No differences.')
    # a copy of B's file has B's UID (measured: the UID is the file's <fileUID>), but it is another
    # package: B's snapshots aren't its own (REVIEW.md SRV-36); the error says so (SRV-37)
    current.update({'file': '/c/Copy of B.sbs', 'uid': '2b'})
    with pytest.raises(server.ToolError, match='no snapshots of New_Graph for this package'):
        server.diff_graph('New_Graph', against='latest')
    # unsaved packages are told apart in the list by their UID (SRV-37)
    listed = server.list_snapshots('New_Graph')
    assert 'an unsaved package, UID 3c' in listed and 'an unsaved package, UID 4d' in listed, listed


def test_an_unsaved_package_and_a_recovered_copy_of_it_keep_their_snapshots_apart(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-38: a package with no file took every note with its UID, and a snapshot opened to
    # recover keeps the package's UID; SRV-39: after a Save As the refusal said "take one", though the
    # package's earlier snapshots are there under its old file
    import re
    from typing import Any

    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path / 'snaps'))
    current: dict[str, Any] = {'file': '', 'uid': 'U', 'nodes': 1}

    def xml() -> str:
        nodes = ''.join('<compNode><uid v="%d"/></compNode>' % i for i in range(current['nodes']))
        return (
            '<package><content><graph><identifier v="New_Graph"/><compNodes>%s</compNodes></graph></content></package>'
            % nodes
        )

    def bridge(code: str, *a: Any, **kw: Any) -> str:
        info = 'PACKAGE=%s\nPACKAGE_UID=%s\nGRAPH=New_Graph\n' % (current['file'], current['uid'])
        copy = re.search(r"save_package_copy\(.*?, '(.*?)'\)", code)
        if copy:
            os.makedirs(os.path.dirname(copy.group(1)), exist_ok=True)
            with open(copy.group(1), 'w') as f:
                f.write(xml())
            return 'COPY=%s\n' % copy.group(1) + info
        return info

    patch_server(monkeypatch, '_bridge', bridge)
    s1 = server.snapshot_graph('New_Graph').split('saved: ')[1].strip()  # unsaved package A, 1 node
    current.update({'file': s1, 'nodes': 3})  # s1 opened in Designer to recover: R, same UID
    server.snapshot_graph('New_Graph')
    current.update({'file': '', 'nodes': 1})  # back to A: its own snapshot is the latest
    assert server.diff_graph('New_Graph', against='latest').endswith('No differences.')
    server.snapshot_graph('New_Graph')  # A again, after R's: R must not take it (REVIEW.md SRV-40)
    current.update({'file': s1, 'nodes': 3})
    assert server.diff_graph('New_Graph', against='latest').endswith('No differences.')
    # a package saved at P, then saved as P2 (its UID unchanged): P's snapshots aren't P2's, and the
    # refusal says where they are
    current.update({'file': '/p/P.sbs', 'uid': 'V', 'nodes': 2})
    server.snapshot_graph('New_Graph')
    current['file'] = '/p/P2.sbs'
    with pytest.raises(server.ToolError, match=r'from other packages.*by its path'):
        server.diff_graph('New_Graph', against='latest')
    # an unknown label, with snapshots of its own and others': only the others are counted (SRV-41)
    server.snapshot_graph('New_Graph')
    with pytest.raises(server.ToolError) as refused:
        server.diff_graph('New_Graph', against='nolabel')
    own, every = len(server._snapshots('New_Graph', ('/p/P2.sbs', 'V'))), len(server._snapshots('New_Graph'))
    assert own == 1 and '(%d from other packages' % (every - own) in str(refused.value), str(refused.value)


# Every case _from_package tells apart, decided once (REVIEW.md SRV-34, -36, -38, -40): the note's
# file and UID against the package's. The UID is the file's <fileUID>: kept through saves, shared by
# a copy of the file (GUIDE.md); a snapshot opened to recover lives in the snapshot folder.
_SNAP = '<snapshots>'
_NOTE_CASES = [
    # (note file, note UID, package file, package UID, its own?, why)
    ('/a/A.sbs', 'U', '/a/A.sbs', 'U', True, 'the same file'),
    ('/a/A.sbs', 'U', '/a/A.sbs', 'X', True, 'the same file, whatever the UID'),
    ('/a/A.sbs', 'U', '/b/B.sbs', 'U', False, 'another file with its UID: a copy, or a Save As since'),
    ('/a/A.sbs', 'U', '', 'U', False, 'a package with no file never owns a noted file'),
    ('', 'U', '', 'U', True, 'the same unsaved package'),
    ('', 'U', '', 'V', False, 'another unsaved package'),
    ('', 'U', '/a/A.sbs', 'U', True, "taken before this package's first save"),
    ('', 'U', '/a/A.sbs', 'V', False, 'another package, never saved'),
    ('', 'U', _SNAP + '/g/s1.sbs', 'U', False, 'a snapshot opened to recover: not its unsaved original'),
    (_SNAP + '/g/s1.sbs', 'U', _SNAP + '/g/s1.sbs', 'U', True, "the recovered copy's own"),
    ('', 'U', '/proj/R.sbs', 'W', False, 'a recovered snapshot saved elsewhere: its fresh UID (SRV-42)'),
    (None, None, '/a/A.sbs', 'U', True, 'no note: taken before notes were kept, counts for any'),
]


@pytest.mark.parametrize(
    ('note_file', 'note_uid', 'file', 'uid', 'own', 'why'), _NOTE_CASES, ids=[c[5] for c in _NOTE_CASES]
)
def test_which_snapshots_are_a_packages_own(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    note_file: str | None,
    note_uid: str | None,
    file: str,
    uid: str,
    own: bool,
    why: str,
) -> None:
    snaps = tmp_path / 'snaps'
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(snaps))
    snapshot = snaps / 'g' / '20261031-120000.sbs'
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text('<package/>')
    if note_file is not None:
        server._note_package(str(snapshot), note_file.replace(_SNAP, str(snaps)), note_uid)
    assert server._from_package(str(snapshot), file.replace(_SNAP, str(snaps)), uid) is own, why


def test_a_snapshot_gets_a_fresh_uid_and_a_recovered_copy_saved_elsewhere_stays_apart(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-42: a snapshot copy kept the package's UID (measured), so a snapshot opened to
    # recover and saved elsewhere looked like the unsaved original saved for the first time, and took
    # its later snapshots. A snapshot of an unsaved package now gets a fresh <fileUID>; its note keeps
    # the package's
    import re
    import xml.etree.ElementTree as ET
    from typing import Any

    U = '{7118f88c-fa69-44e8-a0de-9d25423b6019}'  # a real UID's form: only that is re-stamped
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path / 'snaps'))
    current: dict[str, Any] = {'file': '', 'uid': U, 'nodes': 1}

    def xml() -> str:
        nodes = ''.join('<compNode><uid v="%d"/></compNode>' % i for i in range(current['nodes']))
        return (
            '<package><fileUID v="%s"/><dependencies><dependency><fileUID v="0"/></dependency></dependencies>'
            '<content><graph><identifier v="New_Graph"/><compNodes>%s</compNodes></graph></content></package>'
            % (current['uid'], nodes)
        )

    def bridge(code: str, *a: Any, **kw: Any) -> str:
        info = 'PACKAGE=%s\nPACKAGE_UID=%s\nGRAPH=New_Graph\n' % (current['file'], current['uid'])
        copy = re.search(r"save_package_copy\(.*?, '(.*?)'\)", code)
        if copy:
            os.makedirs(os.path.dirname(copy.group(1)), exist_ok=True)
            with open(copy.group(1), 'w') as f:
                f.write(xml())
            return 'COPY=%s\n' % copy.group(1) + info
        return info

    patch_server(monkeypatch, '_bridge', bridge)
    s1 = server.snapshot_graph('New_Graph').split('saved: ')[1].strip()  # unsaved package A
    root = ET.parse(s1).getroot()
    fresh = root.find('fileUID').get('v')  # type: ignore[union-attr]
    assert fresh not in (U, '0') and [d.get('v') for d in root.iter('fileUID')][1:] == ['0']
    assert '"uid": "%s"' % U in Path(s1 + '.json').read_text()
    # s1 opened to recover (it loads with the UID in its file: measured), then saved elsewhere
    current.update({'file': '/proj/R.sbs', 'uid': fresh, 'nodes': 3})
    server.snapshot_graph('New_Graph')
    current.update({'file': '', 'uid': U, 'nodes': 1})
    server.snapshot_graph('New_Graph')  # A again, after R's
    current.update({'file': '/proj/R.sbs', 'uid': fresh, 'nodes': 3})
    assert server.diff_graph('New_Graph', against='latest').endswith('No differences.')


# Designer's own formatting (seen in its files): double-quoted declaration, no space before "/>",
# the package's own UID before <dependencies>, each dependency's fileUID "0"
_DESIGNER_SBS = (
    b'<?xml version="1.0" encoding="UTF-8"?><package><identifier v="Unsaved Package"/>'
    b'<formatVersion v="1.1.0.202502"/><fileUID v="{7118f88c-fa69-44e8-a0de-9d25423b6019}"/><versionUID v="0"/>'
    b'<dependencies><dependency><filename v="A.sbs"/><uid v="1585559310"/><fileUID v="0"/></dependency>'
    b'</dependencies><content><graph><identifier v="New_Graph"/></graph></content></package>'
)


def test_fresh_uid_changes_only_the_uid(tmp_path: Path) -> None:
    # REVIEW.md SRV-42, Option 1b: only the package's own UID changes, as bytes; Designer's formatting,
    # the dependencies' "0" and the file's date stay as they were
    import re

    path = tmp_path / 's.sbs'
    path.write_bytes(_DESIGNER_SBS)
    os.utime(path, (1000, 1000))
    server._fresh_uid(str(path))
    after = path.read_bytes()
    old = b'{7118f88c-fa69-44e8-a0de-9d25423b6019}'
    start = _DESIGNER_SBS.index(old)
    assert len(after) == len(_DESIGNER_SBS)
    assert after[:start] == _DESIGNER_SBS[:start] and after[start + len(old) :] == _DESIGNER_SBS[start + len(old) :]
    new = after[start : start + len(old)]
    assert new != old and re.fullmatch(rb'\{[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\}', new)
    assert os.path.getmtime(path) == 1000  # never sorts as the latest (SRV-1)


@pytest.mark.parametrize(
    'content',
    [
        b'<?xml version="1.0" encoding="UTF-8"?><package><dependencies/></package>',
        b'<package><fileUID v="0"/><dependencies/></package>',
        b'<package><dependencies><dependency><fileUID v="{7118f88c-fa69-44e8-a0de-9d25423b6019}"/>'
        b'</dependency></dependencies></package>',
        b'not xml at all',
    ],
    ids=['no own UID', 'own UID "0"', 'a real UID only inside <dependencies>', 'not a .sbs'],
)
def test_fresh_uid_leaves_a_file_without_its_own_uid_alone(tmp_path: Path, content: bytes) -> None:
    path = tmp_path / 's.sbs'
    path.write_bytes(content)
    server._fresh_uid(str(path))
    assert path.read_bytes() == content


@pytest.mark.parametrize(('package', 'restamped'), [('', True), ('/proj/A.sbs', False)], ids=['unsaved', 'saved'])
def test_only_a_snapshot_of_an_unsaved_package_gets_a_uid_of_its_own(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, package: str, restamped: bool
) -> None:
    # SRV-42, Option 1b: a saved package's snapshots are told apart by its file, so they stay Designer's
    # exact copy; only an unsaved package's, which the notes tell apart by UID, gets one of its own
    import re
    from typing import Any

    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path / 'snaps'))

    def bridge(code: str, *a: Any, **kw: Any) -> str:
        info = 'PACKAGE=%s\nPACKAGE_UID={7118f88c-fa69-44e8-a0de-9d25423b6019}\nGRAPH=New_Graph\n' % package
        copy = re.search(r"save_package_copy\(.*?, '(.*?)'\)", code)
        if copy:
            os.makedirs(os.path.dirname(copy.group(1)), exist_ok=True)
            Path(copy.group(1)).write_bytes(_DESIGNER_SBS)
            return 'COPY=%s\n' % copy.group(1) + info
        return info

    patch_server(monkeypatch, '_bridge', bridge)
    snap = Path(server.snapshot_graph('New_Graph').split('saved: ')[1].strip())
    assert (snap.read_bytes() != _DESIGNER_SBS) is restamped


def _failing_writes(monkeypatch: pytest.MonkeyPatch, suffix: str) -> None:
    """open() for writing a file ending in suffix fails as on a full disk."""
    import builtins
    import errno

    real_open = builtins.open

    def fake_open(file: Any, mode: str = 'r', *a: Any, **kw: Any) -> Any:
        if str(file).endswith(suffix) and ('w' in mode or 'a' in mode):
            raise OSError(errno.ENOSPC, 'No space left on device')
        return real_open(file, mode, *a, **kw)

    monkeypatch.setattr(builtins, 'open', fake_open)


@pytest.mark.parametrize(
    ('package', 'failing'),
    [('', '.sbs'), ('', '.sbs.json'), ('/proj/A.sbs', '.sbs.json')],
    ids=['re-stamp fails', 'note fails (unsaved)', 'note fails (saved)'],
)
def test_a_snapshot_that_fails_after_its_copy_leaves_nothing_behind(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, package: str, failing: str
) -> None:
    # REVIEW.md SRV-43: the re-stamp emptied the file before writing, and ran before the note: a failure
    # (a full disk) left a truncated snapshot with no note, which counts for every package and is the
    # newest, so every same-named graph's 'latest'. A note that fails to write leaves the same
    import re

    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path / 'snaps'))

    def bridge(code: str, *a: Any, **kw: Any) -> str:
        info = 'PACKAGE=%s\nPACKAGE_UID={7118f88c-fa69-44e8-a0de-9d25423b6019}\nGRAPH=New_Graph\n' % package
        copy = re.search(r"save_package_copy\(.*?, '(.*?)'\)", code)
        if copy:  # Designer writes the copy (not through Python's open)
            os.makedirs(os.path.dirname(copy.group(1)), exist_ok=True)
            Path(copy.group(1)).write_bytes(_DESIGNER_SBS)
            return 'COPY=%s\n' % copy.group(1) + info
        return info

    patch_server(monkeypatch, '_bridge', bridge)
    _failing_writes(monkeypatch, failing)
    with pytest.raises(OSError):
        server.snapshot_graph('New_Graph')
    assert os.listdir(tmp_path / 'snaps' / 'New_Graph') == []


def test_a_snapshot_saved_in_place_since_is_not_its_packages_latest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-47: a snapshot opened to recover and saved in place (Ctrl+S, in the snapshot folder)
    # became the newest file, still noted for its package: diff_graph('latest') took the user's edited
    # copy for the last snapshot. A snapshot changed since it was taken is left out of 'latest' and
    # labels, and list_snapshots says so
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path))
    times = iter(['20261101-100000', '20261101-110000'])
    monkeypatch.setattr(time, 'strftime', lambda fmt: next(times))
    taken = []
    for mtime in (1000, 2000):
        path = server._new_snapshot_path('g', 'before x')
        Path(path).write_text('<package>snapshot</package>')
        os.utime(path, (mtime, mtime))
        server._note_package(path, '/a/A.sbs', '{U}')
        taken.append(path)
    s1, s3 = taken
    Path(s1).write_text('<package>the user saved over the snapshot</package>')
    os.utime(s1, (3000, 3000))  # saved in place, after s3
    assert server._snapshots('g', ('/a/A.sbs', '{U}')) == [s3]
    assert server._snapshots('g') == [s3, s1]  # every snapshot is still listed
    listing = server.list_snapshots('g')
    line = next(line for line in listing.splitlines() if s1 in line)
    assert 'changed since it was taken' in line
    assert 'changed since' not in next(line for line in listing.splitlines() if s3 in line)


def test_a_refusal_counts_this_packages_snapshots_saved_over_apart(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-50: since SRV-47 a package's own list leaves out its snapshots saved over since, and the
    # refusal counted them as "from other packages, e.g. before a Save As", which was false
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path))
    path = server._new_snapshot_path('g', 'before x')
    Path(path).write_text('<package>snapshot</package>')
    server._note_package(path, '/a/A.sbs', '{U}')
    Path(path).write_text('<package>saved over in Designer</package>')
    text = server._others('g', ('/a/A.sbs', '{U}'))
    assert 'other packages' not in text
    assert '1 of this package' in text and 'saved over' in text and 'by its path' in text
    other = server._new_snapshot_path('g', 'from B')
    Path(other).write_text('<package>B</package>')
    server._note_package(other, '/b/B.sbs', '{V}')
    text = server._others('g', ('/a/A.sbs', '{U}'))
    assert '1 from other packages' in text and '1 of this package' in text
