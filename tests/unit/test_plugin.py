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
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast

import pytest

from conftest import ROOT, patch_server, server
from project_constants import PLUGIN_PACKAGE_DIR

PLUGIN = os.path.join(PLUGIN_PACKAGE_DIR, '__init__.py')
Bridge = tuple[types.ModuleType, Any, dict[str, bool]]  # the bridge fixture: the plugin, its _Server, the drain switch


class _FakeTimer:
    def __init__(self) -> None:
        self.timeout = types.SimpleNamespace(connect=lambda fn: None)

    def start(self, ms: int) -> None:
        pass

    def stop(self) -> None:
        pass


@pytest.fixture
def plugin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> types.ModuleType:
    qtcore = types.SimpleNamespace(QTimer=_FakeTimer)
    monkeypatch.setitem(sys.modules, 'PySide6', types.SimpleNamespace(QtCore=qtcore))
    monkeypatch.setitem(sys.modules, 'PySide6.QtCore', qtcore)
    spec = importlib.util.spec_from_file_location('bridge_plugin_under_test', PLUGIN)
    assert spec is not None and spec.loader is not None  # a .py file that exists
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # tests patch its names with monkeypatch.setitem(vars(module), ...): the same as setattr for a module,
    # but PyCharm checks setattr's name against the fixture function and reports it missing
    vars(module)['TOKEN_FILE'] = str(tmp_path / 'token')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        vars(module)['PORT'] = probe.getsockname()[1]
    return module


@pytest.fixture
def bridge(plugin: types.ModuleType) -> Iterator[Bridge]:
    srv = plugin._Server()
    draining = {'on': True}

    def drain() -> None:  # stands in for the QTimer on Designer's main thread
        while draining['on']:
            srv._drain()
            time.sleep(0.01)

    thread = threading.Thread(target=drain, daemon=True)
    thread.start()
    yield plugin, srv, draining
    draining['on'] = False
    srv.stop()


def _call(
    plugin: types.ModuleType, request: dict[str, Any] | None, token: str | None = None, raw: bytes | None = None
) -> Any:
    """One request; token=None uses the real token, raw sends these bytes instead of JSON."""
    with socket.create_connection(('127.0.0.1', plugin.PORT), timeout=10) as s:
        hello = b''
        while not hello.endswith(b'\n'):
            hello += s.recv(1024)
        nonce = json.loads(hello)['nonce']
        if raw is None:
            secret = token if token is not None else Path(plugin.TOKEN_FILE).read_text().strip()
            if secret:
                request = {
                    **cast(dict[str, Any], request),  # raw=None: the caller passed a request
                    'auth': hmac.new(secret.encode(), nonce.encode(), hashlib.sha256).hexdigest(),
                }
            raw = json.dumps(request).encode()
        s.sendall(raw)
        s.shutdown(socket.SHUT_WR)
        data = b''
        while chunk := s.recv(65536):
            data += chunk
    return json.loads(data)


# ---- token file
def test_token_created_owner_only(plugin: types.ModuleType) -> None:
    token = plugin._load_token()
    assert len(token) == 64 and Path(plugin.TOKEN_FILE).read_text() == token
    if os.name == 'posix':
        assert stat.S_IMODE(os.stat(plugin.TOKEN_FILE).st_mode) == 0o600


@pytest.mark.parametrize('content', ['', '   \n', 'short'])
def test_empty_or_short_token_is_replaced(plugin: types.ModuleType, content: str) -> None:
    with open(plugin.TOKEN_FILE, 'w') as f:
        f.write(content)
    token = plugin._load_token()
    assert len(token) == 64 and Path(plugin.TOKEN_FILE).read_text() == token


def test_good_token_kept_and_permissions_tightened(plugin: types.ModuleType) -> None:
    with open(plugin.TOKEN_FILE, 'w') as f:
        f.write('a' * 64)
    os.chmod(plugin.TOKEN_FILE, 0o644)
    assert plugin._load_token() == 'a' * 64
    if os.name == 'posix':
        assert stat.S_IMODE(os.stat(plugin.TOKEN_FILE).st_mode) == 0o600


# ---- authentication
def test_runs_code_with_the_right_answer(bridge: Bridge) -> None:
    plugin, _, _ = bridge
    reply = _call(plugin, {'code': 'print(6 * 7)'})
    assert reply == {'ok': True, 'output': '42\n', 'error': ''}


@pytest.mark.parametrize(
    'request_', [{'code': "print('RAN')"}, {'code': "print('RAN')", 'auth': 'x' * 64}, {'cmd': 'status', 'auth': ''}]
)
def test_refuses_without_the_right_answer(bridge: Bridge, request_: dict[str, str]) -> None:
    plugin, _, _ = bridge
    assert _call(plugin, request_, token='') == {'ok': False, 'output': '', 'error': 'invalid token'}


def test_the_old_protocol_sending_the_token_is_refused(bridge: Bridge) -> None:
    plugin, _, _ = bridge
    token = Path(plugin.TOKEN_FILE).read_text().strip()
    assert _call(plugin, {'cmd': 'status', 'token': token}, token='')['error'] == 'invalid token'


def test_an_empty_token_file_does_not_open_the_bridge(plugin: types.ModuleType) -> None:
    open(plugin.TOKEN_FILE, 'w').close()
    srv = plugin._Server()
    try:
        assert (
            _call(plugin, {'cmd': 'status', 'auth': plugin.expected_auth('', 'anything')}, token='')['error']
            == 'invalid token'
        )
    finally:
        srv.stop()


def test_clients_never_send_the_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # a squatter on the port only ever sees HMAC(token, its own nonce)
    token_file = tmp_path / 'token'
    token_file.write_text('s' * 64)
    patch_server(monkeypatch, 'TOKEN_FILE', str(token_file))
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    patch_server(monkeypatch, 'PORT', listener.getsockname()[1])
    seen: dict[str, bytes] = {}

    def squat() -> None:
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


@pytest.mark.parametrize('client', ['sd_run', 'server'])
def test_both_clients_speak_the_plugins_protocol(bridge: Bridge, monkeypatch: pytest.MonkeyPatch, client: str) -> None:
    # README says the unit tests cover the clients' protocol: each client against the real plugin
    # server (REVIEW.md TST-8; sd_run.py was only exercised by the live self-test)
    plugin, _, _ = bridge
    if client == 'sd_run':
        monkeypatch.syspath_prepend(os.path.join(ROOT, 'client'))
        import sd_run

        monkeypatch.setitem(vars(sd_run), 'TOKEN_FILE', plugin.TOKEN_FILE)
        monkeypatch.setitem(vars(sd_run), 'PORT', plugin.PORT)
        send = sd_run.send
    else:
        patch_server(monkeypatch, 'TOKEN_FILE', plugin.TOKEN_FILE)
        patch_server(monkeypatch, 'PORT', plugin.PORT)
        send = server._send
    assert send({'code': 'print(6 * 7)'}, 10) == {'ok': True, 'output': '42\n', 'error': ''}
    assert send({'cmd': 'status'}, 10)['ok']


# ---- robustness
def test_bad_requests_get_no_details(bridge: Bridge) -> None:
    plugin, _, _ = bridge
    for raw in (b'not json', b'[1, 2]', b'\xff\xfe'):
        assert _call(plugin, None, raw=raw) == {'ok': False, 'output': '', 'error': 'bad request'}


def test_oversized_request_refused(bridge: Bridge) -> None:
    plugin, _, _ = bridge
    vars(plugin)['MAX_REQUEST'] = 1000
    assert _call(plugin, None, raw=b'x' * 5000)['error'] == 'bad request'


def test_stalled_client_is_dropped(bridge: Bridge) -> None:
    plugin, _, _ = bridge
    vars(plugin)['READ_TIMEOUT'] = 0.5
    with socket.create_connection(('127.0.0.1', plugin.PORT), timeout=10) as s:
        s.recv(1024)
        s.sendall(b'{"cmd": ')  # never finishes, never closes its side
        assert json.loads(s.recv(65536))['error'] == 'bad request'


@pytest.mark.parametrize('timeout', ['5', -1, True, [1]])
def test_bad_timeout_rejected_not_queued(bridge: Bridge, timeout: Any) -> None:
    plugin, srv, _ = bridge
    reply = _call(plugin, {'code': "print('RAN')", 'timeout': timeout})
    assert not reply['ok'] and 'timeout must be a number' in reply['error']
    assert srv.jobs.qsize() == 0


def test_script_timeout_still_works(bridge: Bridge) -> None:
    plugin, _, _ = bridge
    reply = _call(plugin, {'code': 'while True: pass', 'timeout': 0.3})
    assert not reply['ok'] and 'ScriptAborted: timed out' in reply['error']


def test_job_that_waited_too_long_never_runs(bridge: Bridge, tmp_path: Path) -> None:
    plugin, srv, draining = bridge
    draining['on'] = False  # Designer "busy": nothing drains the queue
    time.sleep(0.05)
    vars(plugin)['QUEUE_WAIT'] = 0.3
    marker = tmp_path / 'ran'
    reply = _call(plugin, {'code': 'open(%r, "w").close()' % str(marker)})
    assert not reply['ok'] and 'was not run' in reply['error']
    srv._drain()  # Designer free again
    assert not marker.exists()


def test_cancel_drops_queued_jobs(bridge: Bridge) -> None:
    plugin, srv, draining = bridge
    draining['on'] = False
    time.sleep(0.05)
    replies: list[Any] = []
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


def test_a_job_never_starts_inside_the_running_one(plugin: types.ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md PLG-1. In Designer the drain runs on a QTimer, and a script that lets Qt process
    # events (screenshots, open_graph) fires that timer again: the queued job must wait.
    import builtins

    srv = plugin._Server()
    seen: dict[str, bool] = {}
    box_a: dict[str, Any] = {}
    box_b: dict[str, Any] = {}
    done_a, done_b = threading.Event(), threading.Event()

    def timer_fires_meanwhile() -> None:  # what processEvents() does inside job A
        srv._drain()
        seen['b_started_inside_a'] = bool(box_b.get('started'))
        seen['a_still_busy'] = srv.busy_since is not None

    monkeypatch.setitem(builtins.__dict__, '_timer_fires_meanwhile', timer_fires_meanwhile)  # a new name, removed after
    srv.jobs.put(('_timer_fires_meanwhile()', None, None, box_a, done_a))
    srv.jobs.put(("print('B ran')", None, None, box_b, done_b))
    try:
        srv._drain()
        srv._drain()  # the next tick (one job per tick, PLG-13)
    finally:
        srv.stop()
    assert box_a['result']['ok'], box_a['result']['error']
    assert seen == {'b_started_inside_a': False, 'a_still_busy': True}
    assert done_b.is_set() and box_b['result']['output'] == 'B ran\n'  # B ran afterwards
    assert srv.busy_since is None


def test_an_abort_lets_cleanup_code_finish(plugin: types.ModuleType) -> None:
    # REVIEW.md PLG-2. The abort is raised once; finally blocks and context-manager exits (such
    # as Designer's UndoGroup committing its transaction) must then run to the end.
    cancel = threading.Event()
    cancel.set()
    code = (
        'try:\n    while True:\n        pass\nfinally:\n    total = 0\n'
        "    for i in range(20000):\n        total += i\n    print('cleanup finished', total)\n"
    )
    result = plugin._run(code, None, None, cancel)
    assert not result['ok'] and 'ScriptAborted: cancelled by client' in result['error']
    assert 'cleanup finished 199990000' in result['output']


def test_a_trickling_client_is_dropped_by_a_total_deadline(bridge: Bridge) -> None:
    # REVIEW.md PLG-4: the read timeout applied per recv, so a byte every so often kept a
    # connection (and its buffer) open before authentication forever
    plugin, _, _ = bridge
    vars(plugin)['READ_TIMEOUT'] = 0.6
    with socket.create_connection(('127.0.0.1', plugin.PORT), timeout=10) as s:
        s.recv(1024)  # the nonce greeting
        started = time.monotonic()
        closed = False
        while time.monotonic() - started < 4:
            try:
                s.sendall(b' ')
            except OSError:
                closed = True
                break
            s.settimeout(0.25)
            try:
                if s.recv(65536):  # the plugin answered (and will close)
                    closed = True
                    break
            except TimeoutError:
                pass
        assert closed and time.monotonic() - started < 2.5


def test_connections_beyond_the_limit_are_closed_at_once(bridge: Bridge) -> None:
    # REVIEW.md PLG-4: one thread and one buffer per connection, with no cap
    plugin, _, _ = bridge
    vars(plugin)['MAX_CLIENTS'] = 2
    held = [socket.create_connection(('127.0.0.1', plugin.PORT), timeout=5) for _ in range(2)]
    try:
        for h in held:
            h.recv(1024)  # both got a greeting and stay open
        with socket.create_connection(('127.0.0.1', plugin.PORT), timeout=5) as extra:
            extra.settimeout(2)
            assert extra.recv(1024) == b''  # closed without a greeting
    finally:
        for h in held:
            h.close()
    time.sleep(0.2)
    assert _call(plugin, {'code': "print('ok')"})['output'] == 'ok\n'  # slots free again


def test_status_does_not_count_abandoned_jobs(bridge: Bridge) -> None:
    # REVIEW.md PLG-7: a job dropped after QUEUE_WAIT stays in the queue until the main thread
    # gets to it, and status counted it as queued
    plugin, _srv, draining = bridge
    draining['on'] = False  # Designer busy: nothing drains the queue
    time.sleep(0.05)
    vars(plugin)['QUEUE_WAIT'] = 0.2
    assert 'was not run' in _call(plugin, {'code': "print('late')"})['error']
    assert _call(plugin, {'cmd': 'status'})['output'].endswith(': idle, 0 queued')


def test_stop_answers_queued_clients_and_frees_the_port(bridge: Bridge) -> None:
    # REVIEW.md PLG-5: stop() closed the socket only, so clients whose jobs were queued waited
    # out QUEUE_WAIT (900 s), and a blocked accept() could hold the port
    plugin, srv, draining = bridge
    draining['on'] = False
    time.sleep(0.05)
    replies: list[Any] = []
    waiter = threading.Thread(target=lambda: replies.append(_call(plugin, {'code': "print('never')"})))
    waiter.start()
    deadline = time.monotonic() + 5
    while srv.jobs.qsize() == 0 and time.monotonic() < deadline:
        time.sleep(0.01)
    started = time.monotonic()
    srv.stop()
    waiter.join(5)
    assert replies and not replies[0]['ok'] and 'closing' in replies[0]['error']
    assert time.monotonic() - started < 2
    srv.thread.join(2)
    assert not srv.thread.is_alive(), 'the accept thread is still blocked'
    with socket.socket() as again:  # the port can be bound again at once
        again.bind(('127.0.0.1', plugin.PORT))


def test_control_commands_are_answered_while_queued_jobs_fill_the_cap(bridge: Bridge) -> None:
    # REVIEW.md PLG-10: a client waiting for its queued job kept its connection slot, so with the
    # cap full of them, cancel and status were closed without a greeting
    plugin, srv, draining = bridge
    draining['on'] = False  # a long job "runs": nothing drains the queue
    time.sleep(0.05)
    vars(plugin)['MAX_CLIENTS'] = 2
    waiting = [
        threading.Thread(target=_call, args=(plugin, {'code': "print('queued')"}), daemon=True) for _ in range(2)
    ]
    for w in waiting:
        w.start()
    deadline = time.monotonic() + 5
    while srv.jobs.qsize() < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert srv.jobs.qsize() == 2
    reply = _call(plugin, {'cmd': 'status'})
    assert reply['ok'] and '2 queued' in reply['output']
    assert 'queued dropped: 2' in _call(plugin, {'cmd': 'cancel'})['output']


def test_status_while_a_job_ends_is_not_a_bad_request(bridge: Bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md PLG-11: busy_since was read twice outside the lock; a job ending between the two
    # reads made status fail with "bad request"
    plugin, srv, _ = bridge
    srv.busy_since = time.monotonic()
    real: Callable[[], float] = plugin.time.monotonic

    def job_ends_now() -> float:
        srv.busy_since = None  # the main thread finishes the job right here
        return real()

    monkeypatch.setitem(vars(plugin.time), 'monotonic', job_ends_now)
    reply = srv._control('status')
    assert reply['ok'] and ('idle' in reply['output'] or 'running for' in reply['output'])


def test_a_job_arriving_after_stop_is_answered_at_once(bridge: Bridge) -> None:
    # REVIEW.md PLG-12: a request read before stop() but queued after it waited out QUEUE_WAIT
    plugin, srv, draining = bridge
    draining['on'] = False
    time.sleep(0.05)
    vars(plugin)['QUEUE_WAIT'] = 1.5
    srv.stop()
    nonce = 'n' * 32
    started = time.monotonic()
    reply = srv._authorised({'code': "print('late')", 'auth': plugin.expected_auth(srv.token, nonce)}, nonce)
    assert not reply['ok'] and 'closing' in reply['error'] and time.monotonic() - started < 1


def test_one_job_per_timer_tick(bridge: Bridge) -> None:
    # REVIEW.md PLG-13: one tick ran every queued job back to back, without returning to Qt's
    # event loop in between (AGENTS.md, Portals: an unload and a load need that)
    plugin, srv, draining = bridge
    draining['on'] = False
    time.sleep(0.05)
    replies: list[Any] = []
    for i in range(2):
        threading.Thread(
            target=lambda i=i: replies.append(_call(plugin, {'code': 'print(%d)' % i})), daemon=True
        ).start()
        deadline = time.monotonic() + 5
        while srv.jobs.qsize() < i + 1 and time.monotonic() < deadline:
            time.sleep(0.01)
    srv._drain()  # one tick
    time.sleep(0.3)
    assert len(replies) == 1 and srv.jobs.qsize() == 1
    srv._drain()
    time.sleep(0.3)
    assert len(replies) == 2


def test_cancel_does_not_count_abandoned_jobs(bridge: Bridge) -> None:
    # REVIEW.md PLG-14: status skips abandoned jobs (PLG-7), but cancel counted them as dropped
    plugin, _srv, draining = bridge
    draining['on'] = False
    time.sleep(0.05)
    vars(plugin)['QUEUE_WAIT'] = 0.2
    assert 'was not run' in _call(plugin, {'code': "print('late')"})['error']
    assert 'queued dropped: 0' in _call(plugin, {'cmd': 'cancel'})['output']


def test_one_failed_accept_does_not_stop_the_bridge(bridge: Bridge) -> None:
    # REVIEW.md PLG-15: any OSError from accept() ended the accept loop for good (a momentary
    # EMFILE or ECONNABORTED), so every later connection waited unanswered
    plugin, srv, _ = bridge
    real = srv.sock

    class FailsOnce:
        failed = False

        def accept(self) -> Any:
            if not FailsOnce.failed:
                FailsOnce.failed = True
                raise ConnectionAbortedError('aborted before accept')
            return real.accept()

        def __getattr__(self, name: str) -> Any:
            return getattr(real, name)

    srv.sock = FailsOnce()
    assert _call(plugin, {'code': "print('first')"})['output'] == 'first\n'  # served by the pending accept
    assert _call(plugin, {'code': "print('after')"})['output'] == 'after\n'  # the loop went on
    assert FailsOnce.failed


def test_a_lasting_accept_error_backs_off_and_is_logged_once(
    bridge: Bridge, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md PLG-20: since PLG-15 the loop retried every 0.1 s and printed every time, so an
    # error that lasts (EMFILE) wrote ten lines a second into Designer's log
    plugin, srv, _ = bridge
    real = srv.sock
    sleeps: list[float] = []
    real_sleep = plugin.time.sleep

    def sleep(seconds: float) -> None:  # time.sleep is global: record the accept loop's, let the others sleep
        if sys._getframe(1).f_code.co_name == '_accept_loop':
            sleeps.append(seconds)
        else:
            real_sleep(seconds)

    monkeypatch.setitem(vars(plugin.time), 'sleep', sleep)

    # eight failures (past the 5 s cap), one with another error (a new line), a success, then one
    # more failure, which starts again at 0.1 s with a new line (REVIEW.md TST-55)
    emfile, reset = OSError(24, 'Too many open files'), ConnectionAbortedError('aborted before accept')
    script = [emfile] * 8 + [reset, None, emfile, None]

    class Scripted:
        def accept(self) -> Any:
            step = script.pop(0) if script else None
            if step is not None:
                raise step
            return real.accept()

        def __getattr__(self, name: str) -> Any:
            return getattr(real, name)

    srv.sock = Scripted()
    assert _call(plugin, {'code': "print('first')"})['output'] == 'first\n'  # served by the pending accept
    assert _call(plugin, {'code': "print('second')"})['output'] == 'second\n'  # after nine failures
    assert _call(plugin, {'code': "print('third')"})['output'] == 'third\n'  # after one more
    assert not script
    assert capsys.readouterr().out.count('accept failed') == 3
    assert sleeps == pytest.approx([0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 5, 5, 5, 0.1]), sleeps


def test_a_job_whose_run_fails_still_answers_its_client(bridge: Bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md PLG-22: done.set() came after the try/finally and buf.getvalue() was outside _run's
    # try, so a MemoryError there left the client waiting with no timeout and no reply
    plugin, _, _ = bridge
    real_run = plugin._run

    def run(code: str, path: str | None, timeout: float | None, cancel: threading.Event) -> Any:
        if 'boom' in code:
            raise MemoryError('reading the output')
        return real_run(code, path, timeout, cancel)

    monkeypatch.setitem(vars(plugin), '_run', run)
    reply = _call(plugin, {'code': "print('boom')"})
    assert reply['ok'] is False and 'MemoryError' in reply['error']
    assert _call(plugin, {'code': "print('next')"})['output'] == 'next\n'  # and the bridge goes on


def test_a_scripts_output_is_capped_keeping_the_end(bridge: Bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md PLG-22: output was buffered without limit; now only the last MAX_OUTPUT characters
    plugin, _, _ = bridge
    monkeypatch.setitem(vars(plugin), 'MAX_OUTPUT', 1000)
    out = _call(plugin, {'code': "for i in range(2000):\n    print('line %d' % i)"})['output']
    assert len(out) < 1200 and out.endswith('line 1999\n') and 'cut' in out.splitlines()[0], out[:200]


def test_an_abort_anywhere_in_a_write_keeps_the_output_written_before(
    plugin: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md PLG-24: the abort tracer runs inside _TailBuffer.write too; one landing between
    # truncate() and the write of the kept tail left the buffer empty
    import inspect

    monkeypatch.setitem(vars(plugin), 'MAX_OUTPUT', 100)
    source, first = inspect.getsourcelines(plugin._TailBuffer.write)
    lines = range(first + 1, first + len(source))

    class Abort(BaseException):
        pass

    for line in lines:
        buf = plugin._TailBuffer()
        buf.write('a' * 150 + 'KEEP')  # below 2 x MAX_OUTPUT: nothing trimmed yet

        def tracer(frame: types.FrameType, event: str, arg: Any, line: int = line) -> Any:
            if frame.f_code is plugin._TailBuffer.write.__code__ and event == 'line' and frame.f_lineno == line:
                raise Abort()
            return tracer

        def start(frame: types.FrameType, event: str, arg: Any) -> Any:
            return tracer if frame.f_code is plugin._TailBuffer.write.__code__ else None

        before = sys.gettrace()
        aborted = False
        sys.settrace(start)
        try:
            buf.write('b' * 60)  # crosses 2 x MAX_OUTPUT: a trim
        except Abort:
            aborted = True
        finally:
            sys.settrace(before)  # whatever tracer was there (a debugger, coverage)
        # the abort really fired on that line, and nothing written before it was lost (REVIEW.md TST-72)
        assert aborted, line
        assert 'KEEP' in buf.getvalue() or buf.getvalue().endswith('b' * 60), (line, buf.getvalue()[-80:])
