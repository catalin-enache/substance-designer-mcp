"""Output (server_tools/output.py): cooking, sbsrender calls and their errors, render_sbs size notes,
sbsar_info, preview_maps."""

import os
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pytest
from PIL import Image

from conftest import patch_server, server


def test_cooking_never_writes_next_to_the_users_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sbs = tmp_path / 'mine.sbs'
    sbs.write_text('<package/>')
    (tmp_path / 'mine.sbsar').write_text('MY OWN SBSAR')
    calls: list[str] = []

    def fake_cooker(cmd: list[str], timeout: float) -> object:
        out = cmd[cmd.index('--output-path') + 1]
        calls.append(out)
        Path(out, 'mine.sbsar').write_text('cooked')
        return type('R', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()

    patch_server(monkeypatch, '_run_tool', fake_cooker)
    with server._cooked(str(sbs)) as sbsar:
        assert Path(sbsar).read_text() == 'cooked' and os.path.dirname(sbsar) != str(tmp_path)
    assert not os.path.exists(calls[0])  # temporary folder removed
    assert (tmp_path / 'mine.sbsar').read_text() == 'MY OWN SBSAR'


def test_cooker_failure_is_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    patch_server(
        monkeypatch,
        '_run_tool',
        lambda cmd, timeout: type('R', (), {'returncode': 1, 'stdout': 'boom', 'stderr': ''})(),
    )
    with pytest.raises(server.ToolError, match='sbscooker failed'), server._cooked(str(tmp_path / 'x.sbs')):
        pass


def test_tool_timeout_becomes_a_tool_error() -> None:
    with pytest.raises(server.ToolError, match='did not finish within 1s'):
        server._run_tool(['sleep', '5'], 1)


def test_dark_16bit_map_is_not_brightened(tmp_path: Path) -> None:
    path = tmp_path / 'dark.png'
    Image.fromarray(np.full((4, 4), 200, np.uint16)).save(path)  # 200/65535: nearly black
    assert np.array(server._load_8bit(str(path))).max() <= 1


def _render_with(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, exposed: set[str], sbs_name: str = 'two_graphs.sbs', **kw: Any
) -> tuple[str, list[str]]:
    import shutil

    from conftest import FIXTURES

    sbs = tmp_path / sbs_name
    shutil.copy(os.path.join(FIXTURES, sbs_name), sbs)
    seen: dict[str, list[str]] = {}
    patch_server(monkeypatch, 'SBSCOOKER', 'sbscooker')
    patch_server(monkeypatch, 'SBSRENDER', 'sbsrender')
    patch_server(monkeypatch, '_sbsar_contents', lambda sbsar: (exposed, ['pkg://one']))  # one graph

    class _Cooked:
        def __init__(self, path: str) -> None:
            self.path = path

        def __enter__(self) -> str:
            return str(self.path) + 'ar' if str(self.path).endswith('.sbs') else str(self.path)

        def __exit__(self, *a: object) -> Literal[False]:
            return False

    patch_server(monkeypatch, '_cooked', _Cooked)

    def fake_render(cmd: list[str], timeout: float) -> object:
        seen['cmd'] = cmd
        out = cmd[cmd.index('--output-path') + 1]
        Image.new('L', (8, 8)).save(os.path.join(out, 'height.png'))
        return type('R', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()

    patch_server(monkeypatch, '_run_tool', fake_render)
    text = server.render_sbs(str(sbs), str(tmp_path / 'out'), **kw)
    return text, seen['cmd']


def test_render_uses_the_graphs_default_size(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    text, cmd = _render_with(monkeypatch, tmp_path, {'$outputsize'}, graph='alpha')
    assert '$outputsize@9,9' in cmd and '--input-graph' in cmd and 'pkg://alpha' in cmd
    assert 'default parent size, 512 px' in text


def test_render_with_disagreeing_graphs_says_so(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    text, cmd = _render_with(monkeypatch, tmp_path, {'$outputsize'})
    assert not any(a.startswith('$outputsize@') for a in cmd)
    assert 'different default sizes' in text


def test_render_warns_about_unexposed_inputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    text, _cmd = _render_with(monkeypatch, tmp_path, set(), graph='alpha', params={'wear': 0.5}, size_log2=10)
    assert "input 'wear' is not exposed" in text and "input '$outputsize' is not exposed" in text
    assert 'graph output size is fixed' in text


def test_sbsar_info_reports_a_failed_sbsrender(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-6: a failing `sbsrender info` came back as a normal result
    import contextlib
    import subprocess

    patch_server(monkeypatch, 'SBSCOOKER', 'sbscooker')
    patch_server(monkeypatch, 'SBSRENDER', 'sbsrender')
    patch_server(monkeypatch, '_cooked', lambda path: contextlib.nullcontext('/tmp/x.sbsar'))
    patch_server(
        monkeypatch,
        '_run_tool',
        lambda cmd, timeout: subprocess.CompletedProcess(cmd, 1, '', '[ERROR] Unable to open /tmp/x.sbsar'),
    )
    with pytest.raises(server.ToolError) as error:
        server.sbsar_info('/tmp/x.sbs')
    assert 'Unable to open' in str(error.value)


@pytest.mark.parametrize('case', ['no pngs', 'unknown name', 'missing folder'])
def test_preview_maps_explains_what_is_missing(tmp_path: Path, case: str) -> None:
    # REVIEW.md SRV-12: these raised ValueError / FileNotFoundError from PIL or os
    if case != 'no pngs':
        Image.new('L', (4, 4)).save(tmp_path / 'height.png')
    folder = tmp_path / 'nowhere' if case == 'missing folder' else tmp_path
    with pytest.raises(server.ToolError) as error:
        server.preview_maps(str(folder), names=['roughness'] if case == 'unknown name' else None)
    assert {'no pngs': 'no .png files', 'unknown name': "'roughness'", 'missing folder': 'not a folder'}[case] in str(
        error.value
    )


@pytest.mark.parametrize(
    'crop, message', [([30, 0, 10, 8], 'empty'), ([100, 100, 120, 120], 'empty'), ([0, 0, 4], 'x0, y0, x1, y1')]
)
def test_preview_maps_checks_the_crop(tmp_path: Path, crop: list[int], message: str) -> None:
    # REVIEW.md SRV-23: an inverted box raised PIL's ValueError; one outside the image gave a black tile
    Image.new('L', (32, 16), 200).save(tmp_path / 'height.png')
    with pytest.raises(server.ToolError, match=message):
        server.preview_maps(str(tmp_path), crop=crop)
