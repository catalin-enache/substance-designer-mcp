"""
Local script runner for Substance 3D Designer.

Listens on 127.0.0.1:PORT. A client sends one JSON request and receives one JSON reply.
Every request must carry the token stored in TOKEN_FILE (mode 0600).

  run:    {"token", "code", "path"?, "timeout"?}  -> {"ok", "output", "error"}
          Code runs on Designer's main thread. With "timeout" (seconds) the script is
          aborted once it exceeds that time.
  cancel: {"token", "cmd": "cancel"}              -> {"ok", "output"}
          Aborts the running script (and drops queued ones).
  status: {"token", "cmd": "status"}              -> {"ok", "output"}

Aborting works by a trace hook checked while Python code runs, so a single long call
into Designer's C++ (e.g. one graph.compute()) finishes before the abort takes effect.
"""
import contextlib
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
TOKEN_FILE = os.path.expanduser('~/.sd_bridge_token')
TIMEOUT = 900
VERSION = 2

_server = None


class ScriptAborted(BaseException):
    """Raised inside a running script when it is cancelled or exceeds its timeout."""


def _load_token():
    if not os.path.exists(TOKEN_FILE):
        fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(secrets.token_hex(32))
    with open(TOKEN_FILE) as f:
        return f.read().strip()


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
    scope = {'__name__': '__main__', '__file__': path or '<sd_bridge>'}
    deadline = time.monotonic() + timeout if timeout else None
    started = time.monotonic()
    previous = sys.gettrace()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            compiled = compile(code, path or '<sd_bridge>', 'exec')
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


class _Server:
    def __init__(self):
        self.token = _load_token()
        self.jobs = queue.Queue()
        self.cancel = threading.Event()
        self.busy_since = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        print('[sd_bridge] v%d listening on 127.0.0.1:%d' % (VERSION, PORT))

    def _accept_loop(self):
        while self.running:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _control(self, cmd):
        if cmd == 'cancel':
            dropped = 0
            while True:
                try:
                    _, _, _, box, done = self.jobs.get_nowait()
                except queue.Empty:
                    break
                box['result'] = {'ok': False, 'output': '', 'error': 'ScriptAborted: cancelled before start'}
                done.set()
                dropped += 1
            running = self.busy_since is not None
            if running:
                self.cancel.set()
            return {'ok': True, 'output': 'cancel requested (running: %s, queued dropped: %d)' % (running, dropped),
                    'error': ''}
        if cmd == 'status':
            busy = 'idle' if self.busy_since is None else 'running for %.1fs' % (time.monotonic() - self.busy_since)
            return {'ok': True, 'output': 'sd_bridge v%d: %s, %d queued' % (VERSION, busy, self.jobs.qsize()),
                    'error': ''}
        return {'ok': False, 'output': '', 'error': 'unknown cmd %r' % cmd}

    def _handle(self, conn):
        with conn:
            try:
                data = b''
                while True:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                req = json.loads(data.decode('utf-8'))
                if not secrets.compare_digest(str(req.get('token', '')), self.token):
                    reply = {'ok': False, 'output': '', 'error': 'invalid token'}
                elif req.get('cmd'):
                    # Control commands are answered from this thread, even while a script runs
                    reply = self._control(req['cmd'])
                else:
                    done = threading.Event()
                    box = {}
                    timeout = req.get('timeout')
                    self.jobs.put((req.get('code', ''), req.get('path'), timeout, box, done))
                    if done.wait(TIMEOUT):
                        reply = box['result']
                    else:
                        reply = {'ok': False, 'output': '', 'error': 'timed out waiting for Designer'}
            except Exception:
                reply = {'ok': False, 'output': '', 'error': traceback.format_exc()}
            conn.sendall(json.dumps(reply).encode('utf-8'))

    def _drain(self):
        while True:
            try:
                code, path, timeout, box, done = self.jobs.get_nowait()
            except queue.Empty:
                return
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
        print('[sd_bridge] not started, port %d unavailable (%s); another instance is probably running' % (PORT, e))


def uninitializeSDPlugin():
    global _server
    if _server:
        _server.stop()
        _server = None
