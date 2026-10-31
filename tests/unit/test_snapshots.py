"""Snapshots (server_tools/snapshots.py): file names, labels, which one is "latest"."""

import os
import time
from pathlib import Path

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
