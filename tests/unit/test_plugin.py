"""The bridge plugin's server, run outside Designer: Qt's timer is replaced by a thread that
drains the job queue, everything else (sockets, authentication, queue, timeouts) is real."""
import hashlib
import hmac
import importlib.util
import json
import os
import socket
import stat
import sys
import threading
import time
import types

import pytest

from conftest import server
from project_constants import PLUGIN_PACKAGE_DIR

PLUGIN = os.path.join(PLUGIN_PACKAGE_DIR, '__init__.py')


class _FakeTimer:
    def __init__(self):
        self.timeout = types.SimpleNamespace(connect=lambda fn: None)

    def start(self, ms):
        pass

    def stop(self):
        pass


@pytest.fixture
def plugin(monkeypatch, tmp_path):
    qtcore = types.SimpleNamespace(QTimer=_FakeTimer)
    monkeypatch.setitem(sys.modules, 'PySide6', types.SimpleNamespace(QtCore=qtcore))
    monkeypatch.setitem(sys.modules, 'PySide6.QtCore', qtcore)
    spec = importlib.util.spec_from_file_location('bridge_plugin_under_test', PLUGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TOKEN_FILE = str(tmp_path / 'token')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        module.PORT = probe.getsockname()[1]
    return module


@pytest.fixture
def bridge(plugin):
    srv = plugin._Server()
    draining = {'on': True}

    def drain():                                   # stands in for the QTimer on Designer's main thread
        while draining['on']:
            srv._drain()
            time.sleep(0.01)
    thread = threading.Thread(target=drain, daemon=True)
    thread.start()
    yield plugin, srv, draining
    draining['on'] = False
    srv.stop()


def _call(plugin, request, token=None, raw=None):
    """One request; token=None uses the real token, raw sends these bytes instead of JSON."""
    with socket.create_connection(('127.0.0.1', plugin.PORT), timeout=10) as s:
        hello = b''
        while not hello.endswith(b'\n'):
            hello += s.recv(1024)
        nonce = json.loads(hello)['nonce']
        if raw is None:
            secret = token if token is not None else open(plugin.TOKEN_FILE).read().strip()
            if secret:
                request = {**request, 'auth': hmac.new(secret.encode(), nonce.encode(), hashlib.sha256).hexdigest()}
            raw = json.dumps(request).encode()
        s.sendall(raw)
        s.shutdown(socket.SHUT_WR)
        data = b''
        while chunk := s.recv(65536):
            data += chunk
    return json.loads(data)


# ---- token file
def test_token_created_owner_only(plugin):
    token = plugin._load_token()
    assert len(token) == 64 and open(plugin.TOKEN_FILE).read() == token
    if os.name == 'posix':
        assert stat.S_IMODE(os.stat(plugin.TOKEN_FILE).st_mode) == 0o600


@pytest.mark.parametrize('content', ['', '   \n', 'short'])
def test_empty_or_short_token_is_replaced(plugin, content):
    with open(plugin.TOKEN_FILE, 'w') as f:
        f.write(content)
    token = plugin._load_token()
    assert len(token) == 64 and open(plugin.TOKEN_FILE).read() == token


def test_good_token_kept_and_permissions_tightened(plugin):
    with open(plugin.TOKEN_FILE, 'w') as f:
        f.write('a' * 64)
    os.chmod(plugin.TOKEN_FILE, 0o644)
    assert plugin._load_token() == 'a' * 64
    if os.name == 'posix':
        assert stat.S_IMODE(os.stat(plugin.TOKEN_FILE).st_mode) == 0o600


# ---- authentication
def test_runs_code_with_the_right_answer(bridge):
    plugin, _, _ = bridge
    reply = _call(plugin, {'code': 'print(6 * 7)'})
    assert reply == {'ok': True, 'output': '42\n', 'error': ''}


@pytest.mark.parametrize('request_', [{'code': "print('RAN')"}, {'code': "print('RAN')", 'auth': 'x' * 64},
                                      {'cmd': 'status', 'auth': ''}])
def test_refuses_without_the_right_answer(bridge, request_):
    plugin, _, _ = bridge
    assert _call(plugin, request_, token='') == {'ok': False, 'output': '', 'error': 'invalid token'}


def test_the_old_protocol_sending_the_token_is_refused(bridge):
    plugin, _, _ = bridge
    token = open(plugin.TOKEN_FILE).read().strip()
    assert _call(plugin, {'cmd': 'status', 'token': token}, token='')['error'] == 'invalid token'


def test_an_empty_token_file_does_not_open_the_bridge(plugin):
    open(plugin.TOKEN_FILE, 'w').close()
    srv = plugin._Server()
    try:
        assert _call(plugin, {'cmd': 'status', 'auth': plugin.expected_auth('', 'anything')}, token='')['error'] \
            == 'invalid token'
    finally:
        srv.stop()


def test_clients_never_send_the_token(monkeypatch, tmp_path):
    # a squatter on the port only ever sees HMAC(token, its own nonce)
    token_file = tmp_path / 'token'
    token_file.write_text('s' * 64)
    monkeypatch.setattr(server, 'TOKEN_FILE', str(token_file))
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    monkeypatch.setattr(server, 'PORT', listener.getsockname()[1])
    seen = {}

    def squat():
        conn, _ = listener.accept()
        with conn:
            conn.sendall(b'{"nonce": "n1"}\n')
            data = b''
            while chunk := conn.recv(65536):
                data += chunk
            seen['request'] = data
            conn.sendall(b'{"ok": true, "output": "", "error": ""}')
    thread = threading.Thread(target=squat)
    thread.start()
    server._send({'cmd': 'status'}, wait=5)
    thread.join(5)
    listener.close()
    assert b's' * 64 not in seen['request']
    assert json.loads(seen['request'])['auth'] == hmac.new(b's' * 64, b'n1', hashlib.sha256).hexdigest()


# ---- robustness
def test_bad_requests_get_no_details(bridge):
    plugin, _, _ = bridge
    for raw in (b'not json', b'[1, 2]', b'\xff\xfe'):
        assert _call(plugin, None, raw=raw) == {'ok': False, 'output': '', 'error': 'bad request'}


def test_oversized_request_refused(bridge):
    plugin, _, _ = bridge
    plugin.MAX_REQUEST = 1000
    assert _call(plugin, None, raw=b'x' * 5000)['error'] == 'bad request'


def test_stalled_client_is_dropped(bridge):
    plugin, _, _ = bridge
    plugin.READ_TIMEOUT = 0.5
    with socket.create_connection(('127.0.0.1', plugin.PORT), timeout=10) as s:
        s.recv(1024)
        s.sendall(b'{"cmd": ')                      # never finishes, never closes its side
        assert json.loads(s.recv(65536))['error'] == 'bad request'


@pytest.mark.parametrize('timeout', ['5', -1, True, [1]])
def test_bad_timeout_rejected_not_queued(bridge, timeout):
    plugin, srv, _ = bridge
    reply = _call(plugin, {'code': "print('RAN')", 'timeout': timeout})
    assert not reply['ok'] and 'timeout must be a number' in reply['error']
    assert srv.jobs.qsize() == 0


def test_script_timeout_still_works(bridge):
    plugin, _, _ = bridge
    reply = _call(plugin, {'code': 'while True: pass', 'timeout': 0.3})
    assert not reply['ok'] and 'ScriptAborted: timed out' in reply['error']


def test_job_that_waited_too_long_never_runs(bridge, tmp_path):
    plugin, srv, draining = bridge
    draining['on'] = False                          # Designer "busy": nothing drains the queue
    time.sleep(0.05)
    plugin.QUEUE_WAIT = 0.3
    marker = tmp_path / 'ran'
    reply = _call(plugin, {'code': 'open(%r, "w").close()' % str(marker)})
    assert not reply['ok'] and 'was not run' in reply['error']
    srv._drain()                                    # Designer free again
    assert not marker.exists()


def test_cancel_drops_queued_jobs(bridge):
    plugin, srv, draining = bridge
    draining['on'] = False
    time.sleep(0.05)
    replies = []
    t = threading.Thread(target=lambda: replies.append(_call(plugin, {'code': "print('RAN')"})))
    t.start()
    for _ in range(100):
        if srv.jobs.qsize():
            break
        time.sleep(0.01)
    out = _call(plugin, {'cmd': 'cancel'})['output']
    t.join(5)
    assert out == 'cancel requested (running: False, queued dropped: 1)'
    assert replies[0]['error'] == 'ScriptAborted: cancelled before start'
