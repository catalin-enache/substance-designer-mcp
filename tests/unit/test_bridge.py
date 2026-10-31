"""The bridge connection and the tool plumbing (server_tools/core.py): replies the server can't
use, the Windows process check, the quick-edit time limit."""

import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from conftest import patch_server, server


def test_windows_process_check_reads_full_names(monkeypatch: pytest.MonkeyPatch) -> None:
    # tasklist's table cuts names to 25 characters; the CSV form doesn't
    monkeypatch.setattr(sys, 'platform', 'win32')
    outputs = {
        'running': '"Adobe Substance 3D Designer.exe","1234","Console","1","2,000,000 K"\r\n',
        'gone': 'INFO: No tasks are running which match the specified criteria.\r\n',
    }
    for state, out in outputs.items():
        monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: type('R', (), {'stdout': out})())  # noqa: B023 (called below, this iteration)
        assert server._designer_running() == (state == 'running')


@pytest.mark.parametrize('reply', [b'', b'{"nonce": "n"}\n', b'{"nonce": "n"}\nnot json', b'garbage\n'])
def test_bad_replies_become_tool_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, reply: bytes) -> None:
    token = tmp_path / 'token'
    token.write_text('t' * 64)
    patch_server(monkeypatch, 'TOKEN_FILE', str(token))
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    patch_server(monkeypatch, 'PORT', listener.getsockname()[1])

    def answer() -> None:
        conn, _ = listener.accept()
        with conn:
            conn.sendall(reply)

    thread = threading.Thread(target=answer)
    thread.start()
    with pytest.raises(server.ToolError):
        server._send({'cmd': 'status'}, wait=5)
    thread.join(5)
    listener.close()


def test_quick_edits_have_time_for_a_big_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-5: one 60 s limit for a whole apply_edits batch (or an import, a layout)
    seen: list[float | None] = []

    def bridge(code: str, path: str | None = None, timeout: float | None = None) -> str:
        seen.append(timeout)
        return 'ok'

    patch_server(monkeypatch, '_bridge', bridge)
    server.apply_edits([{'op': 'move', 'node_id': '1', 'position': [0, 0]}] * 50, graph='g')
    assert seen and seen[0] is not None and seen[0] >= 300
