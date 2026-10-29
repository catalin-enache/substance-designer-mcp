"""
Local script runner for Substance 3D Designer.

Listens on 127.0.0.1:PORT. On connect the plugin sends one line, {"nonce": "<hex>"}. The client
replies with one JSON request carrying "auth" = HMAC-SHA256(token, nonce) in hex, where the
token is the secret in TOKEN_FILE (mode 0600), and closes its sending side. The plugin answers
with one JSON reply. The token itself never crosses the socket, so a process squatting on the
port while Designer is closed can't collect it.

  run:    {"auth", "code", "path"?, "timeout"?}  -> {"ok", "output", "error"}
          Code runs on Designer's main thread. With "timeout" (seconds) the script is
          aborted once it exceeds that time.
  cancel: {"auth", "cmd": "cancel"}              -> {"ok", "output"}
          Aborts the running script (and drops queued ones).
  status: {"auth", "cmd": "status"}              -> {"ok", "output"}

Aborting works by a trace hook checked while Python code runs, so a single long call
into Designer's C++ (e.g. one graph.compute()) finishes before the abort takes effect.
A job still queued when its client gives up waiting (QUEUE_WAIT) is dropped, never run late.
"""
import contextlib
import hashlib
import hmac
import io
import json
import os
import queue
import secrets
import socket
import sys
import threading
import time
import traceback

from PySide6 import QtCore

PORT = int(os.environ.get('SD_BRIDGE_PORT', '9877'))
# The name comes from this package's folder, so renaming the folders renames everything
NAME = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(os.path.expanduser('~'), '.%s_token' % NAME)
QUEUE_WAIT = 900          # seconds a job may wait for Designer before it is dropped
READ_TIMEOUT = 30         # seconds to receive a whole request
MAX_REQUEST = 64 << 20    # bytes
VERSION = 3

_server = None


class ScriptAborted(BaseException):
    """Raised inside a running script when it is cancelled or exceeds its timeout."""


def _load_token():
    """The shared secret, created on first use. An empty or short file (a crash mid-write, a
    user clearing it) is replaced, since an empty secret would match an empty answer."""
    try:
        with open(TOKEN_FILE) as f:
            token = f.read().strip()
    except FileNotFoundError:
        token = ''
    if len(token) < 32:
        token = secrets.token_hex(32)
        tmp = '%s.%d.tmp' % (TOKEN_FILE, os.getpid())
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(token)
        os.replace(tmp, TOKEN_FILE)
    if os.name == 'posix':
        os.chmod(TOKEN_FILE, 0o600)   # an existing file may have been created with looser rights
    return token


def expected_auth(token, nonce):
    return hmac.new(token.encode('utf-8'), nonce.encode('utf-8'), hashlib.sha256).hexdigest()


def _make_tracer(deadline, cancel):
    ticks = [0]

    def tracer(frame, event, arg):
        ticks[0] += 1
        # Checking every event is cheap enough, but skip most to keep overhead low
        if ticks[0] % 64 == 0:
            if cancel.is_set():
                raise ScriptAborted('cancelled by client')
            if deadline is not None and time.monotonic() > deadline:
                raise ScriptAborted('timed out')
        return tracer
    return tracer


def _run(code, path, timeout, cancel):
    buf = io.StringIO()
    result = {'ok': True, 'output': '', 'error': ''}
    scope = {'__name__': '__main__', '__file__': path or '<%s>' % NAME}
    deadline = time.monotonic() + timeout if timeout else None
    started = time.monotonic()
    previous = sys.gettrace()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            compiled = compile(code, path or '<%s>' % NAME, 'exec')
            sys.settrace(_make_tracer(deadline, cancel))
            try:
                exec(compiled, scope)
            finally:
                sys.settrace(previous)
    except ScriptAborted as e:
        result['ok'] = False
        result['error'] = 'ScriptAborted: %s after %.1fs\n%s' % (e, time.monotonic() - started,
                                                                 traceback.format_exc(limit=-3))
    except BaseException:
        result['ok'] = False
        result['error'] = traceback.format_exc()
    result['output'] = buf.getvalue()
    return result


def _fail(error):
    return {'ok': False, 'output': '', 'error': error}


def _read_request(conn):
    conn.settimeout(READ_TIMEOUT)
    data = bytearray()
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            return bytes(data)
        data += chunk
        if len(data) > MAX_REQUEST:
            raise ValueError('request too large')


class _Server:
    def __init__(self):
        self.token = _load_token()
        self.jobs = queue.Queue()
        self.cancel = threading.Event()
        self.lock = threading.Lock()   # dequeuing a job and marking it running happen together
        self.busy_since = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if sys.platform == 'win32':
            # SO_REUSEADDR on Windows would let a second socket bind the same port
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('127.0.0.1', PORT))
        self.sock.listen(4)
        self.running = True
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        # Jobs are executed on the main (Qt) thread, polled by this timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._drain)
        self.timer.start(100)
        print('[%s] v%d listening on 127.0.0.1:%d' % (NAME, VERSION, PORT))

    def _accept_loop(self):
        while self.running:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _control(self, cmd):
        if cmd == 'cancel':
            with self.lock:
                dropped = 0
                while True:
                    try:
                        _, _, _, box, done = self.jobs.get_nowait()
                    except queue.Empty:
                        break
                    box['result'] = _fail('ScriptAborted: cancelled before start')
                    done.set()
                    dropped += 1
                running = self.busy_since is not None
                if running:
                    self.cancel.set()
            return {'ok': True, 'output': 'cancel requested (running: %s, queued dropped: %d)' % (running, dropped),
                    'error': ''}
        if cmd == 'status':
            busy = 'idle' if self.busy_since is None else 'running for %.1fs' % (time.monotonic() - self.busy_since)
            return {'ok': True, 'output': '%s v%d: %s, %d queued' % (NAME, VERSION, busy, self.jobs.qsize()),
                    'error': ''}
        return _fail('unknown cmd %r' % cmd)

    def _handle(self, conn):
        with conn:
            try:
                nonce = secrets.token_hex(16)
                conn.sendall(json.dumps({'nonce': nonce}).encode('utf-8') + b'\n')
                try:
                    req = json.loads(_read_request(conn).decode('utf-8'))
                    if not isinstance(req, dict):
                        raise ValueError
                except (ValueError, UnicodeDecodeError, OSError):
                    reply = _fail('bad request')   # no details before authentication
                else:
                    reply = self._authorised(req, nonce)
            except Exception:
                reply = _fail('bad request')
            try:
                conn.sendall(json.dumps(reply).encode('utf-8'))
            except OSError:
                pass

    def _authorised(self, req, nonce):
        if not hmac.compare_digest(str(req.get('auth', '')), expected_auth(self.token, nonce)):
            return _fail('invalid token')
        if req.get('cmd'):
            # Control commands are answered from this thread, even while a script runs
            return self._control(req['cmd'])
        timeout = req.get('timeout')
        if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout < 0):
            return _fail('timeout must be a number of seconds, got %r' % (timeout,))
        code = req.get('code', '')
        if not isinstance(code, str):
            return _fail('code must be a string')
        done = threading.Event()
        box = {}
        self.jobs.put((code, req.get('path'), timeout, box, done))
        if not box.get('started') and not done.wait(QUEUE_WAIT):
            with self.lock:
                if not box.get('started'):
                    box['abandoned'] = True   # _drain skips it: never run with nobody waiting
                    return _fail('Designer was busy for %ds; the script was not run' % QUEUE_WAIT)
        done.wait()   # started: it ends by itself, by its timeout or by a cancel
        return box['result']

    def _drain(self):
        while True:
            with self.lock:
                try:
                    code, path, timeout, box, done = self.jobs.get_nowait()
                except queue.Empty:
                    return
                if box.get('abandoned'):
                    continue
                box['started'] = True
                self.cancel.clear()
                self.busy_since = time.monotonic()
            try:
                box['result'] = _run(code, path, timeout, self.cancel)
            finally:
                self.busy_since = None
            done.set()

    def stop(self):
        self.running = False
        self.timer.stop()
        try:
            self.sock.close()
        except OSError:
            pass


def initializeSDPlugin():
    global _server
    try:
        _server = _Server()
    except OSError as e:
        print('[%s] not started: %s (port %d; is another instance running?)' % (NAME, e, PORT))


def uninitializeSDPlugin():
    global _server
    if _server:
        _server.stop()
        _server = None
