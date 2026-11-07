"""The connection: designer_status, cancel_designer_job, the bridge's security and job queue, the MCP
resource, the command-line client (client/sd_run.py) and the installed plugin."""

import asyncio
import filecmp
import json
import os
import re
import socket
import sys
import threading
import time
from textwrap import dedent
from typing import Any, cast

from mcp.types import TextResourceContents

from . import common
from .common import (
    PLUGIN,
    PLUGIN_PACKAGE_DIR,
    TOKEN_FILE,
    Ctx,
    cancel_from_second_client,
    check,
    lan_address,
    raw_request,
    read_greeting,
    sd_run,
    skip,
    text,
)


async def run(ctx: Ctx) -> None:
    c, s, scratch = ctx.c, ctx.s, ctx.scratch
    # --- connection
    t = text(await c('designer_status'))
    check('designer_status', 'idle + version', 'idle' in t and 'Designer ' in t, t.splitlines()[0])
    t = text(await c('cancel_designer_job'))
    check('cancel_designer_job', 'idle', 'running: False' in t, t)
    task = asyncio.create_task(
        c(
            'execute_designer_code',
            {
                'code': dedent("""\
                    import time
                    while True:
                        time.sleep(0.05)"""),
                'timeout_s': 60,
            },
        )
    )
    cancel_text = await cancel_from_second_client()
    t = text(await task)
    check(
        'cancel_designer_job', 'running job', 'running: True' in cancel_text and 'cancelled by client' in t, cancel_text
    )

    await check_bridge_security(ctx)
    await check_a_relayed_answer_is_refused(ctx)
    with open(TOKEN_FILE) as f:
        token = f.read().strip()  # used, never printed

    # --- cancel aborts the running job and drops queued ones (two raw clients + sd_run.py --cancel)
    replies: dict[str, Any] = {}

    def job(name: str, req: dict[str, Any]) -> None:
        replies[name] = raw_request(req, token)

    def bridge_status() -> str:
        out: str = raw_request({'cmd': 'status'}, token)['output']
        return out

    def wait_for(text_part: str) -> bool:
        for _ in range(100):
            if text_part in bridge_status():
                return True
            time.sleep(0.05)
        return False

    long_job = threading.Thread(
        target=job,
        args=(
            'long',
            {
                'code': dedent("""\
                    import time
                    while True:
                        time.sleep(0.05)"""),
                'timeout': 30,
            },
        ),
    )
    long_job.start()
    wait_for('running')
    queued_job = threading.Thread(target=job, args=('queued', {'code': "print('QUEUED RAN')"}))
    queued_job.start()
    wait_for('1 queued')
    r = sd_run('--cancel')
    long_job.join(20)
    queued_job.join(20)
    check(
        'cancel_designer_job',
        'drops queued jobs',
        'running: True, queued dropped: 1' in r.stdout
        and 'cancel' in replies.get('long', {}).get('error', '')
        and 'cancelled before start' in replies.get('queued', {}).get('error', '')
        and 'QUEUED RAN' not in replies.get('queued', {}).get('output', ''),
        r.stdout + str(replies)[:200],
    )

    # --- a queued job never starts inside a running one that lets Qt process events
    # (REVIEW.md PLG-1: the drain timer fires during processEvents)
    pumping = threading.Thread(
        target=job,
        args=(
            'pumping',
            {
                'code': (
                    dedent("""\
                        import time
                        from PySide6.QtWidgets import QApplication
                        t = time.time()
                        while time.time() - t < 1.5:
                            QApplication.processEvents()
                            time.sleep(0.01)
                        print('A_END=%.3f' % time.time())""")
                ),
                'timeout': 30,
            },
        ),
    )
    pumping.start()
    wait_for('running')
    second = threading.Thread(
        target=job,
        args=(
            'second',
            {
                'code': dedent("""\
                    import time
                    print('B_START=%.3f' % time.time())""")
            },
        ),
    )
    second.start()
    pumping.join(20)
    second.join(20)
    a_end = re.search(r'A_END=([\d.]+)', replies.get('pumping', {}).get('output', ''))
    b_start = re.search(r'B_START=([\d.]+)', replies.get('second', {}).get('output', ''))
    check(
        'bridge queue',
        'a queued job waits for the running one',
        a_end is not None and b_start is not None and float(b_start.group(1)) >= float(a_end.group(1)),
        str(replies)[:300],
    )

    # --- MCP resource and the fallback command-line client
    res = await s.read_resource('designer://agents-guide')
    guide = cast(TextResourceContents, res.contents[0]).text  # served as text
    check('mcp resource', 'agents-guide serves AGENTS.md', guide.startswith('# AGENTS.md'), guide[:40])
    r = sd_run('--status')
    check('sd_run.py', '--status', r.returncode == 0 and PLUGIN in r.stdout, r.stdout + r.stderr)
    r = sd_run('-c', 'print(6 * 7)')
    check('sd_run.py', '-c code', r.returncode == 0 and r.stdout.strip() == '42', r.stdout + r.stderr)
    cli_script = os.path.join(scratch, 'cli_probe.py')
    with open(cli_script, 'w') as f:
        f.write(
            dedent("""\
                import sd
                print('cli', __file__.endswith('cli_probe.py'), sd.getContext().getSDApplication().getVersion())
            """)
        )
    r = sd_run(cli_script)
    check('sd_run.py', 'script file', r.returncode == 0 and 'cli True' in r.stdout, r.stdout + r.stderr)
    r = sd_run('-c', 'while True: pass', '--timeout', '2')
    check('sd_run.py', '--timeout aborts', r.returncode == 1 and 'timed out' in r.stderr, r.stderr[-200:])
    r = sd_run('--cancel')
    check('sd_run.py', '--cancel when idle', r.returncode == 0, r.stdout + r.stderr)

    # --- the installed plugin is this repo's (README, Install: re-run install.py after changes)
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': dedent("""\
                    import sys
                    print('PLUGIN=' + sys.modules[%r].__file__)""")
                % PLUGIN
            },
        )
    )
    found = re.search(r'PLUGIN=(.*)', t)
    if found:
        installed = os.path.dirname(found.group(1).strip())
        cmp = filecmp.dircmp(
            PLUGIN_PACKAGE_DIR, installed, ignore=['__pycache__', '.DS_Store']
        )  # Finder's folder files (REVIEW.md TST-79)
        stale = cmp.diff_files + cmp.left_only
        check(
            'install.py',
            'installed plugin matches the repo',
            not stale,
            '%s differ in %s (re-run install.py, restart Designer)' % (stale, installed) if stale else installed,
        )
    else:
        check('install.py', 'installed plugin matches the repo', False, t)


async def check_bridge_security(ctx: Ctx) -> None:
    """README, Security: a request needs the right answer, the bridge listens on loopback only, the token file is
    private."""
    # --- security (README, Security): token required, loopback only, private token file
    B = 'bridge security'
    token_file = TOKEN_FILE
    with open(token_file) as f:
        token = f.read().strip()  # used, never printed
    # the old protocol (the token itself) can only be told apart from a wrong answer with the
    # real token, which never crosses the socket: unit test
    # test_the_old_protocol_sending_the_token_is_refused (REVIEW.md TST-34)
    # on the plugin's own port, only the request in the signature stops a request swapped in (REVIEW.md TST-163)
    reply = raw_request({'code': "print('SHOULD NOT RUN')"}, token, signed=json.dumps({'cmd': 'status'}).encode())
    check(
        B,
        'refuses a request changed after signing',
        reply == {'ok': False, 'output': '', 'error': 'invalid token'},
        str(reply),
    )
    code = {'code': "print('SHOULD NOT RUN')"}

    def wrong_answer() -> Any:
        return raw_request(b'0' * 64 + b'\n' + json.dumps(code).encode())

    def another_key() -> Any:
        return raw_request(code, 'x' * 64)

    def no_answer() -> Any:
        return raw_request({'cmd': 'status'})

    def no_answer_an_auth_key() -> Any:
        return raw_request({'auth': 'nope', **code})

    # a wrong answer on its own line, and one made with another key, in the protocol's framing; and none, as clients
    # of the older protocols sent requests (REVIEW.md TST-175: the "wrong answer" cases sent none)
    for name, send in (
        ('a wrong answer', wrong_answer),
        ('an answer made with another key', another_key),
        ('no answer', no_answer),
        ('no answer, with an auth key', no_answer_an_auth_key),
    ):
        reply = send()
        check(
            B,
            'refuses ' + name,
            not reply['ok']
            and reply.get('error') == 'invalid token'
            and 'SHOULD NOT RUN' not in reply.get('output', ''),
            str(reply),
        )
    reply = raw_request({'cmd': 'status'}, token)
    with open(os.path.join(PLUGIN_PACKAGE_DIR, '__init__.py'), encoding='utf-8') as f:
        version = cast(re.Match[str], re.search(r'^VERSION = (\d+)', f.read(), re.M)).group(1)
    check(
        B, 'accepts the right answer', reply['ok'] and '%s v%s' % (PLUGIN, version) in reply['output'], reply['output']
    )
    # unsigned, bytes that aren't JSON aren't even parsed (REVIEW.md PLG-32); signed, they are, and get no details
    garbage = raw_request(b'{not json')
    check(
        B, 'refuses bad bytes unsigned', garbage == {'ok': False, 'output': '', 'error': 'invalid token'}, str(garbage)
    )
    garbage = raw_request(b'{not json', token)
    check(
        B, 'bad request gets no details', garbage == {'ok': False, 'output': '', 'error': 'bad request'}, str(garbage)
    )
    ip = lan_address()
    if ip is None:
        skip(B, 'not reachable from the network', 'no non-loopback address on this machine')
    else:
        try:
            socket.create_connection((ip, common.PORT), timeout=3).close()
            reachable = True
        except OSError:
            reachable = False
        check(B, 'not reachable from the network', not reachable, 'tried %s:%d' % (ip, common.PORT))
    if sys.platform == 'win32':
        skip(B, 'token file owner-only', 'POSIX permissions only')
    else:
        mode = os.stat(token_file).st_mode & 0o777
        check(B, 'token file owner-only', mode & 0o077 == 0, oct(mode))


def _relay_to_the_plugin() -> tuple[int, list[Any], threading.Event, threading.Thread]:
    """A listener on a free port passing each connection on to the plugin on common.PORT: the plugin's greeting to
    the client, then, with the client's answer, code of its own to the plugin. Returns its port, the plugin's
    replies, a stop event and its thread (REVIEW.md SRV-82)."""
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(4)
    listener.settimeout(0.2)
    replies: list[Any] = []
    stop = threading.Event()

    def serve() -> None:
        with listener:
            while not stop.is_set():
                try:
                    conn, _ = listener.accept()
                except OSError:  # the timeout, to look at stop again
                    continue
                try:
                    with conn, socket.create_connection(('127.0.0.1', common.PORT), timeout=10) as up:
                        conn.settimeout(10)
                        hello = read_greeting(up)
                        conn.sendall(hello)
                        data = b''
                        while chunk := conn.recv(65536):
                            data += chunk
                        answer = data.partition(b'\n')[0]  # the client's, with a request of its own
                        up.sendall(answer + b'\n' + json.dumps({'code': "print('RELAYED')"}).encode())
                        up.shutdown(socket.SHUT_WR)
                        reply = b''
                        while chunk := up.recv(65536):
                            reply += chunk
                        replies.append(json.loads(reply))
                        conn.sendall(reply)
                except (OSError, ValueError) as e:
                    replies.append('relay failed: %s' % e)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return listener.getsockname()[1], replies, stop, thread


async def check_a_relayed_answer_is_refused(ctx: Ctx) -> None:
    """REVIEW.md SRV-82: designer_status pointed at a port where another program listens answers that program's
    greeting; passed on to the plugin with code of its own, the answer must run nothing in Designer."""
    port, replies, stop, thread = _relay_to_the_plugin()
    try:
        await ctx.c('designer_status', {'port': port})
    finally:
        stop.set()
        thread.join(5)
    check(
        'bridge security',
        'refuses an answer relayed from another port',
        bool(replies) and all(isinstance(r, dict) and r.get('error') == 'invalid token' for r in replies),
        str(replies),
    )
