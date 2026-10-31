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
from typing import Any, cast

from mcp.types import TextResourceContents

from .common import (
    PLUGIN,
    PLUGIN_PACKAGE_DIR,
    PORT,
    TOKEN_FILE,
    Ctx,
    cancel_from_second_client,
    check,
    lan_address,
    raw_request,
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
        c('execute_designer_code', {'code': 'import time\nwhile True:\n    time.sleep(0.05)', 'timeout_s': 60})
    )
    cancel_text = await cancel_from_second_client()
    t = text(await task)
    check(
        'cancel_designer_job', 'running job', 'running: True' in cancel_text and 'cancelled by client' in t, cancel_text
    )

    # --- security (README, Security): token required, loopback only, private token file
    B = 'bridge security'
    token_file = TOKEN_FILE
    with open(token_file) as f:
        token = f.read().strip()  # used, never printed
    # the old protocol (the token itself) can only be told apart from a wrong answer with the
    # real token, which never crosses the socket: unit test
    # test_the_old_protocol_sending_the_token_is_refused (REVIEW.md TST-34)
    for name, req in (
        ('a wrong answer', {'auth': 'x' * 64, 'cmd': 'status'}),
        ('no answer', {'cmd': 'status'}),
        ('code with a wrong answer', {'auth': 'nope', 'code': "print('SHOULD NOT RUN')"}),
    ):
        reply = raw_request(req)
        check(
            B,
            'refuses ' + name,
            not reply['ok']
            and reply.get('error') == 'invalid token'
            and 'SHOULD NOT RUN' not in reply.get('output', ''),
            str(reply),
        )
    reply = raw_request({'cmd': 'status'}, token)
    check(B, 'accepts the right answer', reply['ok'] and '%s v3' % PLUGIN in reply['output'], reply['output'])
    with socket.create_connection(('127.0.0.1', PORT), timeout=10) as sock:
        sock.recv(1024)
        sock.sendall(b'{not json')
        sock.shutdown(socket.SHUT_WR)
        garbage = json.loads(sock.recv(65536))
    check(
        B, 'bad request gets no details', garbage == {'ok': False, 'output': '', 'error': 'bad request'}, str(garbage)
    )
    ip = lan_address()
    if ip is None:
        skip(B, 'not reachable from the network', 'no non-loopback address on this machine')
    else:
        try:
            socket.create_connection((ip, PORT), timeout=3).close()
            reachable = True
        except OSError:
            reachable = False
        check(B, 'not reachable from the network', not reachable, 'tried %s:%d' % (ip, PORT))
    if sys.platform == 'win32':
        skip(B, 'token file owner-only', 'POSIX permissions only')
    else:
        mode = os.stat(token_file).st_mode & 0o777
        check(B, 'token file owner-only', mode & 0o077 == 0, oct(mode))

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
        target=job, args=('long', {'code': 'import time\nwhile True:\n    time.sleep(0.05)', 'timeout': 30})
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
                    'import time\nfrom PySide6.QtWidgets import QApplication\nt = time.time()\n'
                    'while time.time() - t < 1.5:\n    QApplication.processEvents()\n    time.sleep(0.01)\n'
                    "print('A_END=%.3f' % time.time())"
                ),
                'timeout': 30,
            },
        ),
    )
    pumping.start()
    wait_for('running')
    second = threading.Thread(target=job, args=('second', {'code': "import time\nprint('B_START=%.3f' % time.time())"}))
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
            "import sd\nprint('cli', __file__.endswith('cli_probe.py'), sd.getContext().getSDApplication().getVersion())\n"
        )
    r = sd_run(cli_script)
    check('sd_run.py', 'script file', r.returncode == 0 and 'cli True' in r.stdout, r.stdout + r.stderr)
    r = sd_run('-c', 'while True: pass', '--timeout', '2')
    check('sd_run.py', '--timeout aborts', r.returncode == 1 and 'timed out' in r.stderr, r.stderr[-200:])
    r = sd_run('--cancel')
    check('sd_run.py', '--cancel when idle', r.returncode == 0, r.stdout + r.stderr)

    # --- the installed plugin is this repo's (README, Install: re-run install.py after changes)
    t = text(
        await c('execute_designer_code', {'code': "import sys\nprint('PLUGIN=' + sys.modules[%r].__file__)" % PLUGIN})
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
