"""The bridge connection and the tool plumbing (server_tools/core.py): replies the server can't
use, the Windows process check, the quick-edit time limit."""

import importlib
import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest

import server_tools
from conftest import REAL_DESIGNER_RUNNING, ROOT, SELFTEST_DIR, patch_server, selftest_sources, server
from project_constants import BRIDGE_PROTOCOL


def test_windows_process_check_reads_full_names(monkeypatch: pytest.MonkeyPatch) -> None:
    # tasklist's table cuts names to 25 characters; the CSV form doesn't
    patch_server(monkeypatch, '_designer_running', REAL_DESIGNER_RUNNING)  # the fixture's follows _designer_pids
    monkeypatch.setattr(sys, 'platform', 'win32')
    outputs = {
        'running': '"Adobe Substance 3D Designer.exe","1234","Console","1","2,000,000 K"\r\n',
        'gone': 'INFO: No tasks are running which match the specified criteria.\r\n',
    }
    for state, out in outputs.items():
        monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: type('R', (), {'stdout': out})())  # noqa: B023 (called below, this iteration)
        assert server._designer_running() == (state == 'running')


def _greeting(**fields: object) -> bytes:
    """A greeting of this protocol (BRIDGE_PROTOCOL's, so a new one doesn't stop the cases below at its check)."""
    return json.dumps({'protocol': BRIDGE_PROTOCOL, **fields}).encode() + b'\n'


# each must reach its own path, so each says which error it gets (REVIEW.md TST-164: greetings without the protocol
# stopped at its check, and any ToolError passed)
NONCE = 'ab' * 16  # as the plugin makes them: 32 hex digits
NOT_THE_BRIDGE = r"not reachable \(ValueError: not the bridge's greeting"
BAD_REPLIES = [
    (b'', b'', r'not reachable \(ConnectionResetError'),
    (_greeting(nonce=NONCE), b'', 'without a reply'),
    (_greeting(nonce=NONCE), b'not json', 'without a reply'),
    # a nonce the plugin never makes: nothing signed with it (REVIEW.md SRV-94)
    (_greeting(nonce=NONCE[:-1] + '\n'), b'', NOT_THE_BRIDGE),  # a newline shifts the signed message's lines
    (_greeting(nonce=1), b'', NOT_THE_BRIDGE),  # not a string
    (_greeting(nonce='abc'), b'', NOT_THE_BRIDGE),  # too short
    (_greeting(hello='1'), b'', r'not reachable \(KeyError'),
    (b'garbage\n', b'', r'not reachable \(JSONDecodeError'),
    (b'{"nonce": "n"}\n', b'', 'another bridge protocol than this server'),  # its own case: nothing sent
    (b'{"hello": 1}\n', b'', NOT_THE_BRIDGE),  # no protocol, no nonce: not the bridge of any version (REVIEW.md SRV-95)
]


@pytest.mark.parametrize('greeting, reply, error', BAD_REPLIES)
def test_bad_replies_become_tool_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, greeting: bytes, reply: bytes, error: str
) -> None:
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
            if not greeting:  # closed at once: the client still waits for a greeting, so it sends nothing
                return
            conn.sendall(greeting)
            try:
                while conn.recv(65536):  # the whole request first: closing before it is a reset, another path
                    pass
                conn.sendall(reply)
            except OSError:
                pass

    thread = threading.Thread(target=answer)
    thread.start()
    with pytest.raises(server.ToolError, match=error):
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


def test_unit_tests_never_read_the_real_token(tmp_path_factory: pytest.TempPathFactory) -> None:
    # REVIEW.md TST-165: a test reaching the real _send opened the user's token (the secret giving code execution in
    # Designer); every client's TOKEN_FILE points into the run's temporary folders, at a token written there
    import project_constants

    bound = [
        vars(m)['TOKEN_FILE'] for m in (server, project_constants, *server_tools.MODULES) if 'TOKEN_FILE' in vars(m)
    ]
    assert len(bound) > 2 and all(path.startswith(str(tmp_path_factory.getbasetemp())) for path in bound), bound
    assert all(os.path.isfile(path) for path in bound)


def test_the_bridge_tests_pass_where_the_plugin_never_ran(tmp_path: Path) -> None:
    # REVIEW.md TST-165: with no token file (a fresh clone), the launch test reaching the real _send got "No bridge
    # token found", started the fake Designer and failed; HOME is empty here, so the user's token isn't touched
    test = 'tests/unit/test_lifecycle_env.py::test_launch_stops_at_a_plugin_of_another_protocol'
    run = subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', test],
        cwd=ROOT,
        env={**os.environ, 'HOME': str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stdout[-2000:]


def _selftest_common() -> Any:  # a module imported by name: PyCharm can't see its names
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    return importlib.import_module('test_all_tools.common')


def test_a_bridge_closing_before_its_greeting_is_an_error_not_a_hang(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-176: the tests' greeting loops added recv()'s b'' forever once the connection closed, spinning at
    # full CPU: the unit suite would hang where a regression closes connections before greeting
    common = _selftest_common()
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    monkeypatch.setitem(vars(common), 'PORT', listener.getsockname()[1])

    def closes_at_once() -> None:
        conn, _ = listener.accept()
        conn.close()

    threading.Thread(target=closes_at_once, daemon=True).start()
    raised: list[BaseException] = []

    def request() -> None:
        try:
            common.raw_request({'cmd': 'status'})
        except BaseException as e:
            raised.append(e)

    asker = threading.Thread(target=request, daemon=True)  # a daemon: a failing run leaves it spinning, not pytest hung
    asker.start()
    asker.join(5)
    listener.close()
    assert not asker.is_alive(), 'still reading the greeting of a closed connection'
    assert raised and isinstance(raised[0], ConnectionResetError), raised


def test_the_tests_read_greetings_through_one_helper() -> None:
    # REVIEW.md TST-176: eight loops of `while not hello.endswith(b'\n'): hello += s.recv(...)`, none ending at EOF
    sources = dict(selftest_sources())
    for path in sorted(Path(ROOT, 'tests', 'unit').glob('*.py')):
        if path.name != 'test_bridge.py':  # this test names the pattern
            sources['unit/' + path.name] = path.read_text(encoding='utf-8')
    loops = {name: source.count('hello.endswith(') for name, source in sources.items() if 'hello.endswith(' in source}
    assert loops == {'common.py': 1}, loops  # read_greeting's own
