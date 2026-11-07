"""REVIEW.md PLG-3: a client must wait at least as long as the plugin keeps a queued job, plus the
script's own time, or a job it gave up on can still start later with nobody waiting."""

import importlib.util
import json
import os
import re
import socket
import sys
import time
import types
from pathlib import Path
from typing import Any, cast

import pytest

from conftest import ROOT, patch_server, server
from project_constants import BRIDGE_PROTOCOL, PLUGIN, PLUGIN_PACKAGE_DIR


def _plugin_queue_wait() -> int:
    with open(os.path.join(PLUGIN_PACKAGE_DIR, '__init__.py'), encoding='utf-8') as f:
        return int(cast(re.Match[str], re.search(r'^QUEUE_WAIT = (\d+)', f.read(), re.M)).group(1))


def _sd_run() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location('sd_run_under_test', os.path.join(ROOT, 'client', 'sd_run.py'))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_clients_know_the_plugins_queue_wait() -> None:
    import project_constants

    assert _plugin_queue_wait() == project_constants.QUEUE_WAIT


@pytest.mark.parametrize('timeout', [None, 2, 120, 600])
def test_server_waits_for_the_queue_and_the_script(monkeypatch: pytest.MonkeyPatch, timeout: int | None) -> None:
    waits: list[float] = []

    def send(request: dict[str, Any], wait: float, port: int | None = None) -> dict[str, Any]:
        waits.append(wait)
        return {'ok': True, 'output': 'x'}

    patch_server(monkeypatch, '_send', send)
    server._bridge('print(1)', timeout=timeout)
    assert waits[0] >= _plugin_queue_wait() + (timeout or 0)


@pytest.mark.parametrize('args, timeout', [([], 0), (['--timeout', '10'], 10)])
def test_sd_run_waits_for_the_queue_and_the_script(
    monkeypatch: pytest.MonkeyPatch, args: list[str], timeout: int
) -> None:
    sd_run = _sd_run()
    waits: list[float] = []

    def send(request: dict[str, Any], wait: float, port: int | None = None) -> dict[str, Any]:
        waits.append(wait)
        return {'ok': True, 'output': '', 'error': ''}

    monkeypatch.setitem(vars(sd_run), 'send', send)
    monkeypatch.setattr(sys, 'argv', ['sd_run.py', '-c', 'print(1)', *args])
    sd_run.main()
    assert waits[0] >= _plugin_queue_wait() + timeout


def test_sd_run_reports_a_timeout_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    sd_run = _sd_run()

    def no_reply(request: dict[str, Any], wait: float) -> dict[str, Any]:
        raise TimeoutError('timed out')

    monkeypatch.setitem(vars(sd_run), 'send', no_reply)
    monkeypatch.setattr(sys, 'argv', ['sd_run.py', '-c', 'print(1)'])
    with pytest.raises(SystemExit) as stop:
        sd_run.main()
    assert stop.value.code == 1 and 'No reply from Designer' in capsys.readouterr().err


# the plugin's name, not the token file's folder (the home folder, REVIEW.md PLG-17)
@pytest.mark.parametrize(
    'error, hint',
    [
        (ConnectionRefusedError(61, 'refused'), 'not running, or its %s plugin' % PLUGIN),
        (FileNotFoundError(2, 'no token'), 'plugin installed'),
        # a full bridge closes the connection; a timeout on --status too
        # (REVIEW.md PLG-19)
        (ConnectionError('the bridge closed the connection'), 'closed the connection'),
        (TimeoutError('timed out'), 'No reply from Designer'),
    ],
)
def test_sd_run_explains_a_closed_designer_or_a_missing_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], error: OSError, hint: str
) -> None:
    # REVIEW.md PLG-16: these came out as raw tracebacks, though sd_run is the fallback for when MCP
    # isn't available, which is when Designer may well be closed
    sd_run = _sd_run()

    def fails(request: dict[str, Any], wait: float) -> dict[str, Any]:
        raise error

    monkeypatch.setitem(vars(sd_run), 'send', fails)
    for argv in (['sd_run.py', '--status'], ['sd_run.py', '-c', 'print(1)']):
        monkeypatch.setattr(sys, 'argv', argv)
        with pytest.raises(SystemExit) as stop:
            sd_run.main()
        assert stop.value.code == 1 and hint in capsys.readouterr().err


def _fake_bridge(greeting: bytes, reply: bytes, received: list[bytes] | None = None) -> int:
    """A listener on a free port that sends `greeting`, reads the request (into `received`, when given) and answers
    `reply` (bytes), once; returns its port."""
    import threading

    srv = socket.socket()
    srv.bind(('127.0.0.1', 0))
    srv.listen(1)

    def serve() -> None:
        conn, _ = srv.accept()
        with conn:
            conn.sendall(greeting)
            try:
                while chunk := conn.recv(65536):
                    if received is not None:
                        received.append(chunk)
                conn.sendall(reply)
            except OSError:
                pass
        srv.close()

    threading.Thread(target=serve, daemon=True).start()
    port: int = srv.getsockname()[1]
    return port


# no reply (Designer quit mid-script), a greeting without a nonce or not an object (another program
# on the port): one line, not a traceback (REVIEW.md PLG-23). Each case names the message it must get from sd_run and
# from the server: greetings of this protocol (BRIDGE_PROTOCOL's) reach those paths, where ones without it stopped at
# the protocol check and any error passed (REVIEW.md TST-164)
NO_REPLY = 'closed the connection without a reply'
GREETING = {'protocol': BRIDGE_PROTOCOL}
NONCE = 'ab' * 16  # as the plugin makes them: 32 hex digits
NOT_THE_BRIDGE = r"not reachable \(ValueError: not the bridge's greeting"
BAD_BRIDGES = [
    (json.dumps({**GREETING, 'nonce': NONCE}).encode() + b'\n', b'', NO_REPLY, NO_REPLY),
    # a nonce the plugin never makes: nothing signed with it (REVIEW.md SRV-94)
    (
        json.dumps({**GREETING, 'nonce': NONCE[:-1] + '\n'}).encode() + b'\n',
        b'',
        'something else answers',
        NOT_THE_BRIDGE,
    ),
    (json.dumps({**GREETING, 'nonce': 1}).encode() + b'\n', b'', 'something else answers', NOT_THE_BRIDGE),
    (json.dumps({**GREETING, 'nonce': 'abc'}).encode() + b'\n', b'', 'something else answers', NOT_THE_BRIDGE),
    (json.dumps({**GREETING, 'hello': 1}).encode() + b'\n', b'', 'something else answers', r'not reachable \(KeyError'),
    (b'[1, 2]\n', b'', 'something else answers', r'not reachable \(ValueError'),
    # no protocol, no nonce: another program, not the bridge of any version (REVIEW.md SRV-95)
    (b'{"hello": 1}\n', b'', 'something else answers', NOT_THE_BRIDGE),
    # its own case: a plugin of another protocol gets nothing
    (
        b'{"nonce": "abc"}\n',
        b'',
        'another bridge protocol than this client',
        'another bridge protocol than this server',
    ),
]


@pytest.mark.parametrize('greeting, reply, error, _', BAD_BRIDGES)
def test_sd_run_explains_a_bridge_that_answers_nothing_useful(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    greeting: bytes,
    reply: bytes,
    error: str,
    _: str,
) -> None:
    sd_run = _sd_run()
    token = tmp_path / 'token'
    token.write_text('t' * 40)
    monkeypatch.setitem(vars(sd_run), 'TOKEN_FILE', str(token))
    received: list[bytes] = []
    monkeypatch.setitem(vars(sd_run), 'PORT', _fake_bridge(greeting, reply, received))
    monkeypatch.setattr(sys, 'argv', ['sd_run.py', '--status'])
    with pytest.raises(SystemExit) as stop:
        sd_run.main()
    assert stop.value.code == 1 and error in capsys.readouterr().err
    # sd_run's line is the same for no reply and for a greeting refused: what tells them apart is whether the request
    # was sent (REVIEW.md SRV-94, TST-191)
    time.sleep(0.2)  # the fake's thread reads after the client has closed
    if _ == NOT_THE_BRIDGE:
        assert received == [], received
    elif error == NO_REPLY:
        assert received, 'the request never reached the bridge'


@pytest.mark.parametrize('greeting, reply, _, error', BAD_BRIDGES)
def test_the_server_explains_a_bridge_that_answers_nothing_useful(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, greeting: bytes, reply: bytes, _: str, error: str
) -> None:
    token = tmp_path / 'token'
    token.write_text('t' * 40)
    patch_server(monkeypatch, 'TOKEN_FILE', str(token))
    patch_server(monkeypatch, 'PORT', _fake_bridge(greeting, reply))
    with pytest.raises(server.ToolError, match=error):
        server._send({'cmd': 'status'}, 5)
