"""
End-to-end self-test of every substance-designer MCP tool, over a real stdio MCP connection.

    macOS:   mcp_server/venv/bin/python tests/test_all_tools.py
    Windows: mcp_server\\venv\\Scripts\\python tests\\test_all_tools.py

If Designer isn't running, the test starts it (launch_designer) and closes it again at the end
(quit_designer); a Designer that was already running is left open. Everything that changes state happens in a
temporary graph ("mcp_selftest") that is removed at the end; the graph you had open in the
editor is reopened. It triggers Undo/Redo only while the self-test graph is the one in the editor
(Undo acts on the document in focus), checks that exactly its own step was undone, and redoes at
once if not. "designer facts" checks the Designer behaviour AGENTS.md documents.
The 3D screenshot is skipped if no 3D View is visible. Exits with code 1 if any check fails.
"""
import asyncio
import base64
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import filecmp
import hashlib
import hmac
import json
import socket

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

BUNDLE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BUNDLE)
from project_constants import PLUGIN, PLUGIN_PACKAGE_DIR, TOKEN_FILE  # noqa: E402
SERVER = os.path.join(BUNDLE, 'mcp_server', 'server.py')
TEST_GRAPH = 'mcp_selftest'
SAVED_GRAPH = 'mcp_selftest_saved'          # create_graph(save_path=...)
DUP_GRAPH = 'mcp_selftest_dup'              # two open graphs with the same identifier
EXAMPLE_GRAPH = 'mcp_selftest_trimsheet'    # examples/build_dwarf_trimsheet.py, renamed
PORT = int(os.environ.get('SD_BRIDGE_PORT', '9877'))
PARAMS = StdioServerParameters(command=sys.executable, args=[SERVER])

results = {}
skipped = []


def check(tool, name, ok, detail=''):
    ok = bool(ok)   # a condition like `refs and not missing` may be [] or None (REVIEW.md TST-29)
    results.setdefault(tool, []).append(ok)
    print('%s  %-22s %s | %s' % ('PASS' if ok else 'FAIL', tool, name, detail.strip()[:150].replace('\n', ' / ')))


def skip(tool, name, why):
    results.setdefault(tool, [])
    skipped.append((tool, name))
    print('SKIP  %-22s %s | %s' % (tool, name, why))


def text(r):
    return '\n'.join(c.text for c in r.content if c.type == 'text')


def is_image(r):
    return bool(r.content) and r.content[0].type == 'image' and not r.is_error


def added_id(t):
    return re.search(r'added (\d+)', t).group(1)


def _mean_png(path):
    from PIL import Image
    import numpy as np
    a = np.array(Image.open(path)).astype(float)
    return float(a.mean() / (65535.0 if a.max() > 255 else 255.0))


def pixel_values(t):
    """'pixel (x,y): R=0.1, G=0.2' lines -> {(x, y): [0.1, 0.2]}"""
    return {(int(x), int(y)): [float(v) for v in re.findall(r'=(-?[\d.]+)', vals)]
            for x, y, vals in re.findall(r'pixel \((\d+),(\d+)\): (.*)', t)}


def raw_request(request, token=None):
    """One request straight to the bridge, bypassing the MCP server. With token, it answers the
    plugin's challenge properly (HMAC of the nonce); without, the request is sent as given."""
    with socket.create_connection(('127.0.0.1', PORT), timeout=10) as sock:
        hello = b''
        while not hello.endswith(b'\n'):
            hello += sock.recv(1024)
        nonce = json.loads(hello)['nonce']
        if token:
            request = {**request, 'auth': hmac.new(token.encode(), nonce.encode(), hashlib.sha256).hexdigest()}
        sock.sendall(json.dumps(request).encode('utf-8'))
        sock.shutdown(socket.SHUT_WR)
        data = b''
        while chunk := sock.recv(65536):
            data += chunk
    return json.loads(data.decode('utf-8'))


def lan_address():
    """This machine's non-loopback IPv4 address, or None (a UDP connect sends no packets)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as u:
            u.connect(('192.0.2.1', 9))
            ip = u.getsockname()[0]
        return None if ip.startswith('127.') or ip == '0.0.0.0' else ip
    except OSError:
        return None


def sd_run(*args, timeout=60):
    return subprocess.run([sys.executable, os.path.join(BUNDLE, 'client', 'sd_run.py'), *args],
                          capture_output=True, text=True, timeout=timeout)


def image_size(r):
    from PIL import Image
    import io
    img = next(x for x in r.content if x.type == 'image')
    return Image.open(io.BytesIO(base64.b64decode(img.data))).size


def positions(t):
    """describe_graph text -> {node id: (x, y)}"""
    return {i: (float(x), float(y)) for i, x, y in re.findall(r'^(\d+) \S+ @\((-?[\d.]+),(-?[\d.]+)\)', t, re.M)}


def clipboard_fingerprint():
    """Hash of the clipboard (never printed). None where we can't read it (non-macOS)."""
    if sys.platform != 'darwin':
        return None
    info = subprocess.run(['osascript', '-e', 'clipboard info'], capture_output=True).stdout
    data = subprocess.run(['pbpaste'], capture_output=True).stdout
    return hashlib.sha256(info + data).hexdigest()


# Designer's library packages loaded right now (their paths), so the run can unload the ones it
# loaded itself (describe_node, add_node of library graphs) and leave the user's (REVIEW.md TST-30)
LIBRARY_PACKAGES = (
    "import os, sd\nfrom sd.api.sdapplication import SDApplicationPath\napp = sd.getContext().getSDApplication()\n"
    "lib = os.path.normcase(os.path.join(app.getPath(SDApplicationPath.DefaultResourcesDir), 'packages'))\n"
    "print('LIBS=' + '|'.join(sorted(p.getFilePath() for p in app.getPackageMgr().getUserPackages()\n"
    "                                if os.path.normcase(p.getFilePath() or '').startswith(lib))))")
UNLOAD_LIBRARY_PACKAGES = (
    "import os, sd\nfrom sd.api.sdapplication import SDApplicationPath\napp = sd.getContext().getSDApplication()\n"
    "keep = set(%r)\nlib = os.path.normcase(os.path.join(app.getPath(SDApplicationPath.DefaultResourcesDir), 'packages'))\n"
    "for p in list(app.getPackageMgr().getUserPackages()):\n"
    "    path = p.getFilePath() or ''\n"
    "    if os.path.normcase(path).startswith(lib) and path not in keep:\n"
    "        app.getPackageMgr().unloadUserPackage(p)\n")
# Every graph the self-test creates is named mcp_selftest...: this closes them all
CLEAN = ("import sd\npm=sd.getContext().getSDApplication().getPackageMgr()\nn=0\n"
         "for p in list(pm.getUserPackages()):\n"
         "    if any(r.getIdentifier().startswith('mcp_selftest') for r in p.getChildrenResources(False)):\n"
         "        pm.unloadUserPackage(p); n+=1\nprint('removed', n)")
# Undo/Redo via Designer's Edit menu, scheduled to run after this call's own undo group closes
UNDO_REDO = ("import sd\nfrom PySide6.QtCore import QTimer\nfrom PySide6.QtWidgets import QApplication, QMenu\n"
             "g=sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()\n"
             "if g is None or g.getIdentifier()!='%s':\n    print('NOT_FOCUSED')\nelse:\n"
             "    acts=[a for w in QApplication.instance().allWidgets() if isinstance(w, QMenu) and w.title()=='&Edit'\n"
             "          for a in w.actions() if a.text()=='%s' and a.isEnabled()]\n"
             "    if acts:\n        QTimer.singleShot(0, acts[0].trigger)\n        print('SCHEDULED')\n"
             "    else:\n        print('NO_ACTION')")
NODE_EXISTS = ("import sd\nfrom PySide6.QtWidgets import QApplication\n"
               "for _ in range(20):\n    QApplication.processEvents()\n"
               "g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() "
               "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
               "print('EXISTS=%%s' %% (g.getNodeFromId('%s') is not None))")
FACTS = ("import sd\nfrom sd.api.apiexception import APIException\nfrom sd.api.sdproperty import SDPropertyCategory\n"
         "g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() "
         "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
         "print('ATOMIC=%%d' %% len(g.getNodeDefinitions()))\n"
         "print('APIEXC_BASE_ONLY=%%s' %% (issubclass(APIException, BaseException) and not issubclass(APIException, Exception)))\n"
         "n=g.getNodeFromId('%s')\nc=n.getPropertyConnections(n.getPropertyFromId('input1', SDPropertyCategory.Input))[0]\n"
         "print('QUERIED_SIDE=%%s' %% (c.getOutputPropertyNode().getIdentifier()=='%s' and "
         "c.getInputPropertyNode().getIdentifier()=='%s' and c.getOutputProperty().getId()=='input1'))")
GRAPH_OF = ("import sd\ng=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() "
            "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n")
# Computed pixels to compare with a tolerance (two computes of one setting differ by a step or two,
# and raw buffers carry row padding; AGENTS.md): pixels(texture) -> integers, apart(a, b) -> the
# largest difference. Only 8- and 16-bit integer formats, where a tolerance in steps means something
# (REVIEW.md TST-54, TST-56)
PIXELS = (
    "import ctypes, array\n"
    "def pixels(t):\n"
    "    fmt = str(t.getPixelFormat()).split('.')[-1]\n"
    "    if not (fmt.endswith('8') or fmt.endswith('16')):\n"
    "        raise RuntimeError('pixels(): %s is not an 8- or 16-bit integer format' % fmt)\n"
    "    w, h, pitch, bpp = t.getSize().x, t.getSize().y, t.getRowPitch(), t.getBytesPerPixel()\n"
    "    raw = ctypes.string_at(t.getPixelBufferAddress(), pitch * h)\n"
    "    rows = b''.join(raw[y * pitch:y * pitch + w * bpp] for y in range(h))\n"
    "    return array.array('H' if fmt.endswith('16') else 'B', rows)\n"
    "def apart(a, b):\n"
    "    return max(abs(x - y) for x, y in zip(a, b))\n")
INHERIT = GRAPH_OF + ("from sd.api.sdproperty import SDPropertyCategory\nn=g.getNodeFromId('%s')\n"
                      "p=n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
                      "print('INHERIT=%%s VALUE=%%s' %% (n.getPropertyInheritanceMethod(p).name, n.getPropertyValue(p).get()))")
# The graph in the editor when the run starts; the graph object is kept so the end of the run can
# check that the very same graph is back in the editor (REVIEW.md TST-5)
CURRENT_GRAPH = ("import sd, sys\ng=sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()\n"
                 "sys._selftest_user_graph = g\nprint('CURRENT=' + (g.getIdentifier() if g else ''))")
# Reopens that graph object, not a graph found by name: two open graphs can share a name
SAME_GRAPH_BACK = ("import sd, sys\nfrom PySide6.QtWidgets import QApplication\n"
                   "g = sys.__dict__.pop('_selftest_user_graph', None)\napp = sd.getContext().getSDApplication()\n"
                   "if g is not None:\n    app.getUIMgr().openResourceInEditor(g)\n    QApplication.processEvents()\n"
                   "cur = app.getQtForPythonUIMgr().getCurrentGraph()\n"
                   "same = cur is not None and g is not None and cur.getPackage().getUID() == g.getPackage().getUID() "
                   "and cur.getIdentifier() == g.getIdentifier()\n"
                   "print('SAME=%s current=%s' % (same, cur.getIdentifier() if cur else None))")


def crash_dumps():
    """Designer's crash dumps (Crashpad's completed reports), as a set of paths; empty where none
    are found."""
    if sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support/Adobe/Adobe Substance 3D Designer')
    else:
        base = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Adobe', 'Adobe Substance 3D Designer')
    folder = os.path.join(base, 'Sentry-Crashpad', 'completed')
    return {os.path.join(folder, f) for f in os.listdir(folder)} if os.path.isdir(folder) else set()


def new_crash_dumps(before, wait_s=10):
    """Crash dumps that appear within wait_s seconds (Designer writes one a few seconds after it
    goes down), compared with `before`."""
    deadline = time.time() + wait_s
    while True:
        new = crash_dumps() - before
        if new or time.time() >= deadline:
            return new
        time.sleep(0.5)


def designer_alive():
    """True while a Designer process exists (as the server's own check)."""
    if sys.platform == 'win32':
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Adobe Substance 3D Designer.exe', '/FO', 'CSV', '/NH'],
                             capture_output=True, text=True).stdout
        return '"Adobe Substance 3D Designer.exe"' in out
    return subprocess.run(['pgrep', '-f', 'MacOS/Adobe Substance 3D Designer( |$)'], capture_output=True).returncode == 0


STATE = {'was_running': False}   # set by run(): the run used the user's own, already open Designer


async def cancel_from_second_client():
    await asyncio.sleep(2)
    async with stdio_client(PARAMS) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return text(await s.call_tool('cancel_designer_job', {}))


async def libs(c):
    """(the library packages loaded now, '') or (None, the bridge's answer) on an error."""
    t = text(await c('execute_designer_code', {'code': LIBRARY_PACKAGES}))
    m = re.search(r'LIBS=(.*)', t)
    return ([l for l in m.group(1).strip().split('|') if l], '') if m else (None, t)


async def library_packages(c):
    """The library packages loaded when the run starts, or None (a failed check) if the bridge
    answers with an error, so the run goes on to its summary and clean-up (REVIEW.md TST-51)."""
    found, error = await libs(c)
    if found is None:
        check('self-test', 'reads the library packages loaded at the start', False, error)
    return found


async def restore_library_packages(c, libs_before):
    """Unloads the library packages the run loaded and checks the user's are still there. A bridge
    error is a failed check, so the rest of the clean-up still runs (REVIEW.md TST-33)."""
    if libs_before is None:
        skip('self-test', 'leaves the library packages loaded as it found them', 'the list at the start could not be read')
        return
    loaded, error = await libs(c)
    if loaded is not None:
        await c('execute_designer_code', {'code': UNLOAD_LIBRARY_PACKAGES % libs_before})
        after, error = await libs(c)
    if loaded is None or after is None:
        check('self-test', 'leaves the library packages loaded as it found them', False, error)
        return
    check('self-test', 'leaves the library packages loaded as it found them', after == libs_before,
          'the run had loaded %d more; before %d, after %d: %s' % (
              len([l for l in loaded if l not in libs_before]), len(libs_before), len(after),
              sorted(set(after) ^ set(libs_before))[:4]))


async def run(scratch):
    async with stdio_client(PARAMS) as (r, w):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            c = lambda name, args=None: s.call_tool(name, args or {})
            tools = sorted(t.name for t in (await s.list_tools()).tools)
            print('server instructions: %d chars; tools: %d\n' % (len(init.instructions or ''), len(tools)))
            # --- the guide: short instructions point to get_guide(); a reminder until it is called
            instructions = init.instructions or ''
            check('get_guide', 'instructions fit (4,096 chars), guide on first use',
                  len(instructions) < 4096 and 'Right before your first Designer tool call' in instructions,
                  '%d chars' % len(instructions))
            t = text(await c('list_snapshots', {'graph': 'no_such_graph'}))
            check('get_guide', 'reminder before it is called', t.startswith('NOTE: the Designer guide has not been read'), t)
            with open(os.path.join(BUNDLE, 'AGENTS.md'), encoding='utf-8') as f:
                agents_md = f.read()
            t = text(await c('get_guide'))
            check('get_guide', 'returns all of AGENTS.md, asks to confirm', t.startswith(agents_md)
                  and 'tell the user' in t.splitlines()[-1], '%d chars' % len(t))
            t = text(await c('list_snapshots', {'graph': 'no_such_graph'}))
            check('get_guide', 'no reminder afterwards', t == 'No snapshots for no_such_graph.', t)
            was_running = STATE['was_running'] = not (await c('designer_status')).is_error
            t = text(await c('launch_designer', {'wait_s': 240}))
            check('launch_designer', 'already running' if was_running else 'started from closed',
                  ('already running' if was_running else 'Designer started in') in t and 'ERROR' not in t, t)
            user_graph = re.search(r'CURRENT=(.*)', text(await c('execute_designer_code', {'code': CURRENT_GRAPH}))).group(1).strip()
            libs_before = await library_packages(c)
            await c('execute_designer_code', {'code': CLEAN})
            try:
                # --- connection
                t = text(await c('designer_status'))
                check('designer_status', 'idle + version', 'idle' in t and 'Designer ' in t, t.splitlines()[0])
                t = text(await c('cancel_designer_job'))
                check('cancel_designer_job', 'idle', 'running: False' in t, t)
                job = asyncio.create_task(c('execute_designer_code', {
                    'code': 'import time\nwhile True:\n    time.sleep(0.05)', 'timeout_s': 60}))
                cancel_text = await cancel_from_second_client()
                t = text(await job)
                check('cancel_designer_job', 'running job', 'running: True' in cancel_text and 'cancelled by client' in t, cancel_text)

                # --- security (README, Security): token required, loopback only, private token file
                B = 'bridge security'
                token_file = TOKEN_FILE
                with open(token_file) as f:
                    token = f.read().strip()                      # used, never printed
                # the old protocol (the token itself) can only be told apart from a wrong answer with the
                # real token, which never crosses the socket: unit test
                # test_the_old_protocol_sending_the_token_is_refused (REVIEW.md TST-34)
                for name, req in (('a wrong answer', {'auth': 'x' * 64, 'cmd': 'status'}),
                                  ('no answer', {'cmd': 'status'}),
                                  ('code with a wrong answer', {'auth': 'nope', 'code': "print('SHOULD NOT RUN')"})):
                    reply = raw_request(req)
                    check(B, 'refuses ' + name, not reply['ok'] and reply.get('error') == 'invalid token'
                          and 'SHOULD NOT RUN' not in reply.get('output', ''), str(reply))
                reply = raw_request({'cmd': 'status'}, token)
                check(B, 'accepts the right answer', reply['ok'] and '%s v3' % PLUGIN in reply['output'], reply['output'])
                with socket.create_connection(('127.0.0.1', PORT), timeout=10) as sock:
                    sock.recv(1024)
                    sock.sendall(b'{not json')
                    sock.shutdown(socket.SHUT_WR)
                    garbage = json.loads(sock.recv(65536))
                check(B, 'bad request gets no details', garbage == {'ok': False, 'output': '', 'error': 'bad request'}, str(garbage))
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
                replies = {}
                def job(name, req):
                    replies[name] = raw_request(req, token)
                def bridge_status():
                    return raw_request({'cmd': 'status'}, token)['output']
                def wait_for(text_part):
                    for _ in range(100):
                        if text_part in bridge_status():
                            return True
                        time.sleep(0.05)
                    return False
                long_job = threading.Thread(target=job, args=('long', {'code': 'import time\nwhile True:\n    time.sleep(0.05)', 'timeout': 30}))
                long_job.start()
                wait_for('running')
                queued_job = threading.Thread(target=job, args=('queued', {'code': "print('QUEUED RAN')"}))
                queued_job.start()
                wait_for('1 queued')
                r = sd_run('--cancel')
                long_job.join(20)
                queued_job.join(20)
                check('cancel_designer_job', 'drops queued jobs', 'running: True, queued dropped: 1' in r.stdout
                      and 'cancel' in replies.get('long', {}).get('error', '')
                      and 'cancelled before start' in replies.get('queued', {}).get('error', '')
                      and 'QUEUED RAN' not in replies.get('queued', {}).get('output', ''), r.stdout + str(replies)[:200])

                # --- a queued job never starts inside a running one that lets Qt process events
                # (REVIEW.md PLG-1: the drain timer fires during processEvents)
                pumping = threading.Thread(target=job, args=('pumping', {'code': (
                    "import time\nfrom PySide6.QtWidgets import QApplication\nt = time.time()\n"
                    "while time.time() - t < 1.5:\n    QApplication.processEvents()\n    time.sleep(0.01)\n"
                    "print('A_END=%.3f' % time.time())"), 'timeout': 30}))
                pumping.start()
                wait_for('running')
                second = threading.Thread(target=job, args=('second', {'code': "import time\nprint('B_START=%.3f' % time.time())"}))
                second.start()
                pumping.join(20)
                second.join(20)
                a_end = re.search(r'A_END=([\d.]+)', replies.get('pumping', {}).get('output', ''))
                b_start = re.search(r'B_START=([\d.]+)', replies.get('second', {}).get('output', ''))
                check('bridge queue', 'a queued job waits for the running one', a_end is not None and b_start is not None
                      and float(b_start.group(1)) >= float(a_end.group(1)), str(replies)[:300])

                # --- MCP resource and the fallback command-line client
                res = await s.read_resource('designer://agents-guide')
                check('mcp resource', 'agents-guide serves AGENTS.md',
                      res.contents[0].text.startswith('# AGENTS.md'), res.contents[0].text[:40])
                r = sd_run('--status')
                check('sd_run.py', '--status', r.returncode == 0 and PLUGIN in r.stdout, r.stdout + r.stderr)
                r = sd_run('-c', 'print(6 * 7)')
                check('sd_run.py', '-c code', r.returncode == 0 and r.stdout.strip() == '42', r.stdout + r.stderr)
                cli_script = os.path.join(scratch, 'cli_probe.py')
                with open(cli_script, 'w') as f:
                    f.write("import sd\nprint('cli', __file__.endswith('cli_probe.py'), sd.getContext().getSDApplication().getVersion())\n")
                r = sd_run(cli_script)
                check('sd_run.py', 'script file', r.returncode == 0 and 'cli True' in r.stdout, r.stdout + r.stderr)
                r = sd_run('-c', 'while True: pass', '--timeout', '2')
                check('sd_run.py', '--timeout aborts', r.returncode == 1 and 'timed out' in r.stderr, r.stderr[-200:])
                r = sd_run('--cancel')
                check('sd_run.py', '--cancel when idle', r.returncode == 0, r.stdout + r.stderr)

                # --- the installed plugin is this repo's (README, Install: re-run install.py after changes)
                t = text(await c('execute_designer_code', {'code': "import sys\nprint('PLUGIN=' + sys.modules[%r].__file__)" % PLUGIN}))
                found = re.search(r'PLUGIN=(.*)', t)
                if found:
                    installed = os.path.dirname(found.group(1).strip())
                    cmp = filecmp.dircmp(PLUGIN_PACKAGE_DIR, installed,
                                         ignore=['__pycache__'])
                    stale = cmp.diff_files + cmp.left_only
                    check('install.py', 'installed plugin matches the repo', not stale,
                          '%s differ in %s (re-run install.py, restart Designer)' % (stale, installed) if stale else installed)
                else:
                    check('install.py', 'installed plugin matches the repo', False, t)

                # --- discovery
                t = text(await c('search_nodes', {'query': 'slope blur'}))
                check('search_nodes', 'library hit', 'slope_blur.sbs/slope_blur_grayscale_2' in t, t.splitlines()[0])
                t = text(await c('search_nodes', {'query': 'levels', 'limit': 2}))
                check('search_nodes', 'atomic ranked first', t.startswith('atomic   levels'), t.splitlines()[0])
                hidden = "definition='3d_texture_jump_flood'"            # hideInLibrary=1 in Designer 16
                shown = text(await c('search_nodes', {'query': 'jump flood'}))
                all_ = text(await c('search_nodes', {'query': 'jump flood', 'include_hidden': True}))
                check('search_nodes', 'include_hidden adds hidden graphs', hidden not in shown and hidden in all_, all_)
                t = text(await c('describe_node', {'definition': 'blend'}))
                check('describe_node', 'atomic enum', 'max=5' in t, '')
                t = text(await c('describe_node', {'definition': 'slope_blur.sbs/slope_blur_grayscale_2'}))
                check('describe_node', 'library', "output connector ids: ['Slope_Blur']" in t, t.splitlines()[0])

                # --- build a temporary graph with the edit tools
                t = text(await c('create_graph', {'name': TEST_GRAPH, 'size_log2': 9}))
                check('create_graph', '512 px', '(512 px)' in t, t)
                saved_sbs = os.path.join(scratch, SAVED_GRAPH + '.sbs')
                t = text(await c('create_graph', {'name': SAVED_GRAPH, 'save_path': saved_sbs, 'size_log2': 8}))
                check('create_graph', 'save_path writes the .sbs', os.path.isfile(saved_sbs), t)
                G = {'graph': TEST_GRAPH}
                await c('open_graph', {'graph': TEST_GRAPH})   # so you can watch the nodes appear
                r_ = await c('diff_graph', {'against': 'saved', **G})
                check('diff_graph', 'error: never saved', r_.is_error and 'never been saved' in text(r_), text(r_))
                r_ = await c('diff_graph', {'against': 'latest', 'graph': SAVED_GRAPH})
                check('diff_graph', 'error: no snapshots yet', r_.is_error and 'no snapshots for' in text(r_), text(r_))
                t = text(await c('add_node', {'definition': 'noise_clouds_2.sbs/clouds_2', 'params': {'scale': 4}, **G}))
                check('add_node', 'library + param', 'instance:clouds_2' in t and '-> 4' in t, t)
                clouds = added_id(t)
                slope = added_id(text(await c('add_node', {'definition': 'slope_blur.sbs/slope_blur_grayscale_2', **G})))
                t = text(await c('add_node', {'definition': 'levels', **G}))
                check('add_node', 'atomic', 'levels' in t, t.splitlines()[0])
                lv = added_id(t)
                out = added_id(text(await c('add_node', {'definition': 'output', **G})))
                r_ = await c('add_node', {'definition': 'not_a_real_node', **G})
                check('add_node', 'error on unknown type', r_.is_error and 'neither an atomic' in text(r_), '')
                t = text(await c('set_params', {'node_id': slope, 'params': {'Samples': 16, 'Intensity': 8.0}, **G}))
                check('set_params', 'int + float', '-> 16' in t and '-> 8.0' in t, t)
                t = text(await c('set_params', {'node_id': lv, 'params': {'levelinlow': [0.3] * 4}, **G}))
                check('set_params', 'float4', '(0.3, 0.3, 0.3, 0.3)' in t, t)
                t = text(await c('set_params', {'node_id': 'graph', 'params': {'$outputsize': [9, 9]}, **G}))
                check('set_params', 'graph $outputsize', '(9, 9)' in t, t)
                # on an overridable graph it is refused (it would quietly make the size fixed), pointing
                # to set_graph_size, and the graph stays overridable (REVIEW.md HLP-22)
                await c('set_graph_size', {'size_log2': 9, 'overridable': True, **G})
                r_ = await c('set_params', {'node_id': 'graph', 'params': {'$outputsize': [10, 10]}, **G})
                still = text(await c('execute_designer_code', {'code': GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory\n"
                    "p = g.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
                    "print('INHERIT=' + str(g.getPropertyInheritanceMethod(p)).split('.')[-1])")}))
                check('set_params', 'graph $outputsize on an overridable graph: refused, still overridable',
                      r_.is_error and 'set_graph_size' in text(r_) and 'INHERIT=RelativeToParent' in still,
                      text(r_).strip()[-120:] + ' | ' + still.strip())
                await c('set_graph_size', {'size_log2': 9, 'overridable': False, **G})
                # the graph's other $ parameters follow its parent too, and a value set while they do
                # changes nothing, so set_params makes them Absolute (REVIEW.md HLP-24); measured on a
                # generator that inherits the graph's format
                FORMAT_OF = GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory\n"
                    "from sd.api.sdvalueenum import SDValueEnum\n"
                    "p = g.getPropertyFromId('$format', SDPropertyCategory.Input)\n"
                    "%s\n"
                    "u = g.newNode('sbs::compositing::uniform'); o = g.newNode('sbs::compositing::output')\n"
                    "u.newPropertyConnectionFromId('unique_filter_output', o, 'inputNodeOutput')\n"
                    "try:\n    g.compute()\n"
                    "    t = u.getPropertyValue(u.getPropertyFromId('unique_filter_output', SDPropertyCategory.Output)).get()\n"
                    "    print('FORMAT=' + str(t.getPixelFormat()).split('.')[-1])\n"
                    "finally:\n    g.deleteNode(u); g.deleteNode(o)\n"   # no stray output if it fails (REVIEW.md TST-49)
                    "print('INHERIT=' + str(g.getPropertyInheritanceMethod(p)).split('.')[-1])")
                fact = text(await c('execute_designer_code', {'code': FORMAT_OF % (
                    "g.setPropertyValue(p, SDValueEnum.sFromValueId(p.getType().getId(), '16_bits_per_channel'))")}))
                check('designer facts', "an inherited graph $format ignores its value (AGENTS.md)",
                      'FORMAT=RGBA8' in fact and 'INHERIT=RelativeToParent' in fact, fact.strip())
                t = text(await c('set_params', {'node_id': 'graph', 'params': {'$format': '16_bits_per_channel'}, **G}))
                fmt16 = text(await c('execute_designer_code', {'code': FORMAT_OF % ''}))
                check('set_params', 'graph $format takes effect (made Absolute)',
                      'FORMAT=RGBA16' in fmt16 and 'INHERIT=Absolute' in fmt16, t.strip() + ' | ' + fmt16.strip())
                # later checks run on a graph like a new one: $format follows its parent again (REVIEW.md TST-35)
                back = text(await c('execute_designer_code', {'code': GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n"
                    "from sd.api.sdvalueenum import SDValueEnum\n"
                    "p = g.getPropertyFromId('$format', SDPropertyCategory.Input)\n"
                    "g.setPropertyValue(p, SDValueEnum.sFromValueId(p.getType().getId(), '8_bits_per_channel'))\n"
                    "g.setPropertyInheritanceMethod(p, IM.RelativeToParent)\n"
                    "print('INHERIT=' + str(g.getPropertyInheritanceMethod(p)).split('.')[-1])")}))
                check('self-test', 'the graph $format check puts the graph back as it was', 'INHERIT=RelativeToParent' in back, back.strip())
                # the graph's $randomseed is different: one that follows its parent is exposed in a
                # .sbsar (an Absolute one isn't) and its value still counts, so set_params leaves its
                # inheritance (REVIEW.md HLP-25; sbsar_info checks the exposure further down)
                SEED_OF = GRAPH_OF % TEST_GRAPH + PIXELS + (
                    "from sd.api.sdproperty import SDPropertyCategory\n"
                    "from sd.api.sdvalueint import SDValueInt\n"
                    "p = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                    "n = g.getNodeFromId('%s'); out = n.getProperties(SDPropertyCategory.Output)[0]\n"
                    "def look(seed):\n"
                    "    g.setPropertyValue(p, SDValueInt.sNew(seed)); g.compute()\n"
                    "    return pixels(n.getPropertyValue(out).get())\n"
                    "o = None\n"
                    "try:\n"   # no stray output for later checks if a step fails (REVIEW.md TST-38, TST-53)
                    "    o = g.newNode('sbs::compositing::output')\n"
                    "    n.newPropertyConnectionFromId(out.getId(), o, 'inputNodeOutput')\n"
                    "    looks = [look(s) for s in (0, 3, 3)]\n"
                    "finally:\n"
                    "    if o is not None:\n        g.deleteNode(o)\n"
                    "print('DIFFERS=%%s REPEATS=%%s INHERIT=%%s' %% (apart(looks[0], looks[1]) > 8, apart(looks[1], looks[2]) <= 8, "
                    "str(g.getPropertyInheritanceMethod(p)).split('.')[-1]))") % clouds
                fact = text(await c('execute_designer_code', {'code': SEED_OF}))
                check('designer facts', "an inherited graph $randomseed's value changes the output (AGENTS.md)",
                      'DIFFERS=True REPEATS=True INHERIT=RelativeToParent' in fact, fact.strip())
                # a node's seed: inherited, its value is added to the graph's; Absolute, it no longer follows
                # the graph's seed (nor a .sbsar's), so set_params leaves it inherited (REVIEW.md HLP-27).
                # Pixels compared with a tolerance: two computes of one setting differ by a step or two
                fact = text(await c('execute_designer_code', {'code': GRAPH_OF % TEST_GRAPH + PIXELS + (
                    "from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n"
                    "from sd.api.sdvalueint import SDValueInt\n"
                    "n = g.getNodeFromId('%s'); out = n.getProperties(SDPropertyCategory.Output)[0]\n"
                    "gp = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                    "np_ = n.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                    "kept = (g.getPropertyValue(gp).get(), n.getPropertyInheritanceMethod(np_), n.getPropertyValue(np_).get())\n"
                    "def look(inherit, graph_seed, node_seed):\n"
                    "    n.setPropertyInheritanceMethod(np_, inherit)\n"
                    "    g.setPropertyValue(gp, SDValueInt.sNew(graph_seed)); n.setPropertyValue(np_, SDValueInt.sNew(node_seed))\n"
                    "    g.compute(); return pixels(n.getPropertyValue(out).get())\n"
                    "o = None\n"
                    "try:\n"   # the output node inside the try too (REVIEW.md TST-53)
                    "    o = g.newNode('sbs::compositing::output')\n"
                    "    n.newPropertyConnectionFromId(out.getId(), o, 'inputNodeOutput')\n"
                    "    r03 = look(IM.RelativeToParent, 0, 3)\n"
                    "    near = max(apart(r03, look(IM.RelativeToParent, 3, 0)), apart(r03, look(IM.RelativeToParent, 1, 2)))\n"
                    "    counts = apart(r03, look(IM.RelativeToParent, 0, 0))\n"
                    "    a0 = look(IM.Absolute, 0, 0)\n"
                    "    follows = apart(a0, look(IM.Absolute, 3, 0))\n"
                    "finally:\n"
                    "    if o is not None:\n        g.deleteNode(o)\n"
                    "    n.setPropertyInheritanceMethod(np_, kept[1]); n.setPropertyValue(np_, SDValueInt.sNew(kept[2]))\n"
                    "    g.setPropertyValue(gp, SDValueInt.sNew(kept[0]))\n"
                    "print('ADDED_WITHIN=%%d VALUE_COUNTS_BY=%%d ABSOLUTE_MOVES_WITH_GRAPH_BY=%%d' %% (near, counts, follows))") % clouds}))
                m = re.search(r'ADDED_WITHIN=(\d+) VALUE_COUNTS_BY=(\d+) ABSOLUTE_MOVES_WITH_GRAPH_BY=(\d+)', fact)
                check('designer facts', "a node's $randomseed: inherited it's added to the graph's; Absolute it no longer follows it (AGENTS.md)",
                      m is not None and int(m.group(1)) <= 8 and int(m.group(2)) > 8 and int(m.group(3)) <= 8, fact.strip())
                t = text(await c('set_params', {'node_id': clouds, 'params': {'$randomseed': 7}, **G}))
                still = text(await c('execute_designer_code', {'code': GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory\nn = g.getNodeFromId('%s')\n"
                    "p = n.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                    "print('INHERIT=%%s VALUE=%%s' %% (n.getPropertyInheritanceMethod(p).name, n.getPropertyValue(p).get()))") % clouds}))
                check('set_params', "a node's $randomseed keeps following the graph's", 'INHERIT=RelativeToParent VALUE=7' in still,
                      t.strip() + ' | ' + still.strip())
                # and one already Absolute stays Absolute, on a node and on the graph: set_params never
                # changes a seed's inheritance (AGENTS.md; REVIEW.md HLP-29, TST-57)
                SEED_INHERIT = GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n"
                    "from sd.api.sdvalueint import SDValueInt\n"
                    "n = %s; p = n.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                    "%s\nprint('INHERIT=%%s VALUE=%%s' %% (n.getPropertyInheritanceMethod(p).name, n.getPropertyValue(p).get()))")
                for target, node_id in (("g.getNodeFromId('%s')" % clouds, clouds), ('g', 'graph')):
                    kept = re.search(r'VALUE=(-?\d+)', text(await c('execute_designer_code', {'code': SEED_INHERIT % (target, '')})))
                    await c('execute_designer_code', {'code': SEED_INHERIT % (target, 'n.setPropertyInheritanceMethod(p, IM.Absolute)')})
                    t = text(await c('set_params', {'node_id': node_id, 'params': {'$randomseed': 4}, **G}))
                    still = text(await c('execute_designer_code', {'code': SEED_INHERIT % (target, '')}))
                    check('set_params', "an Absolute $randomseed stays Absolute (%s)" % ('node' if node_id != 'graph' else 'graph'),
                          'INHERIT=Absolute VALUE=4' in still, t.strip() + ' | ' + still.strip())
                    # back as it was: inherited, then the value (changing the inheritance resets it)
                    await c('execute_designer_code', {'code': SEED_INHERIT % (target, (
                        'n.setPropertyInheritanceMethod(p, IM.RelativeToParent); n.setPropertyValue(p, SDValueInt.sNew(%s))'
                        % (kept.group(1) if kept else 0)))})
                await c('set_params', {'node_id': clouds, 'params': {'$randomseed': 0}, **G})
                # 5: a value SEED_OF never set, so the check sees set_params write it (REVIEW.md TST-37)
                t = text(await c('set_params', {'node_id': 'graph', 'params': {'$randomseed': 5}, **G}))
                still = text(await c('execute_designer_code', {'code': GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory\n"
                    "p = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                    "print('INHERIT=%s VALUE=%s' % (str(g.getPropertyInheritanceMethod(p)).split('.')[-1], g.getPropertyValue(p).get()))")}))
                check('set_params', 'graph $randomseed keeps following its parent (stays exposed)',
                      'INHERIT=RelativeToParent VALUE=5' in still, t.strip() + ' | ' + still.strip())
                r_ = await c('set_params', {'node_id': lv, 'params': {'levelinlow': [1, 2]}, **G})
                check('set_params', 'error on bad length', r_.is_error and 'expects 4' in text(r_), text(r_))
                before = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
                r_ = await c('set_params', {'node_id': lv, 'params': {'$outputsize': 11}, **G})
                after = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
                check('set_params', 'rejected value changes nothing (not even inheritance)',
                      r_.is_error and 'expects 2' in text(r_) and 'INHERIT=' in before and before == after, before + after)
                # every value is checked before any is set (REVIEW.md HLP-1): levelinlow stays at 0.3
                r_ = await c('set_params', {'node_id': lv, 'params': {'levelinlow': [0.6] * 4, 'levelinhigh': [1, 2]}, **G})
                t = text(await c('execute_designer_code', {'code': GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory\nn=g.getNodeFromId('%s')\n"
                    "print('LOW=%%.2f' %% n.getPropertyValue(n.getPropertyFromId('levelinlow', SDPropertyCategory.Input)).get().x)") % lv}))
                check('set_params', 'a bad later value changes nothing', r_.is_error and 'expects 4' in text(r_)
                      and 'LOW=0.30' in t, text(r_)[-120:] + ' / ' + t.strip())
                r_ = await c('set_params', {'node_id': slope, 'params': {'Samples': 16.5}, **G})
                check('set_params', 'error on a fractional integer', r_.is_error and 'not a whole number' in text(r_), text(r_))
                tmp_u = added_id(text(await c('add_node', {'definition': 'uniform', **G})))
                r_ = await c('set_params', {'node_id': tmp_u, 'params': {'outputcolor': [1, 0.5]}, **G})
                check('set_params', 'error on a 2-value colour', r_.is_error and 'expects a colour' in text(r_), text(r_))
                t = text(await c('set_params', {'node_id': tmp_u, 'params': {'colorswitch': 'false'}, **G}))
                check('set_params', "bool from the string 'false'", '-> False' in t, t)
                await c('delete_nodes', {'node_ids': [tmp_u], **G})
                linked = []
                for a, b, port in [(clouds, slope, 'Source'), (clouds, slope, 'Effect'),
                                   (slope, lv, 'input1'), (lv, out, 'inputNodeOutput')]:
                    t = text(await c('connect', {'from_node': a, 'to_node': b, 'to_input': port, **G}))
                    linked.append('-> %s.%s' % (b, port) in t)
                check('connect', '4 links', all(linked), str(linked))
                r_ = await c('connect', {'from_node': clouds, 'to_node': lv, 'to_input': 'nope', **G})
                check('connect', 'error on bad port', r_.is_error and 'connectors:' in text(r_), text(r_))
                t = text(await c('execute_designer_code', {'code': (
                    "import sd\nfrom sd.api.sdvaluestring import SDValueString\n"
                    "g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() "
                    "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
                    "n=g.getNodeFromId('%s'); n.setAnnotationPropertyValueFromId('identifier', SDValueString.sNew('height'))\n"
                    "print('output named height')") % (TEST_GRAPH, out), 'undo_label': 'self-test: name output'}))
                check('execute_designer_code', 'sd API call', 'output named height' in t, t)
                r_ = await c('execute_designer_code', {'code': 'raise ValueError("boom")'})
                check('execute_designer_code', 'error traceback', 'ValueError: boom' in text(r_), '')
                t = text(await c('execute_designer_code', {'code': 'while True: pass', 'timeout_s': 2}))
                check('execute_designer_code', 'timeout', 'ScriptAborted: timed out' in t, '')
                # the abort fires once (Python unsets a trace function that raises), so cleanup code
                # such as UndoGroup committing its transaction runs to the end (REVIEW.md PLG-2)
                t = text(await c('execute_designer_code', {'code': (
                    "try:\n    while True:\n        pass\nfinally:\n    total = 0\n"
                    "    for i in range(20000):\n        total += i\n    print('CLEANUP DONE', total)"), 'timeout_s': 1}))
                check('designer facts', 'an aborted script still finishes its cleanup',
                      'ScriptAborted: timed out' in t and 'CLEANUP DONE 199990000' in t, t[-200:])
                t = text(await c('execute_designer_code', {'code': (
                    "import sd\nprint('MODIFIED=%%s' %% any(p.isModified() for p in sd.getContext().getSDApplication()"
                    ".getPackageMgr().getUserPackages() if any(r.getIdentifier()=='%s' for r in p.getChildrenResources(False))))"
                    % TEST_GRAPH)}))
                if was_running:
                    # a regression here would close the user's Designer: only on our own instance
                    skip('quit_designer', 'refuses with unsaved changes', 'Designer was already running (yours)')
                elif 'MODIFIED=True' in t:   # otherwise quit_designer could really close Designer
                    r_ = await c('quit_designer')
                    still = not (await c('designer_status')).is_error
                    check('quit_designer', 'refuses with unsaved changes', r_.is_error and 'unsaved changes' in text(r_)
                          and TEST_GRAPH in text(r_) and still, text(r_))
                else:
                    skip('quit_designer', 'refuses with unsaved changes', 'self-test package not reported as modified')
                t = text(await c('move_nodes', {'positions': {clouds: [-600, 0], slope: [-300, 0], lv: [0, 0], out: [300, 0]}, **G}))
                check('move_nodes', '4 moved', t.count('moved') == 4, '')
                await c('open_graph', {'graph': TEST_GRAPH})   # fit the view to the nodes so far
                t = text(await c('describe_graph', {'include_params': True, **G}))
                check('describe_graph', 'links + params', 'Effect<-%s' % clouds in t and 'Samples = 16' in t, t.splitlines()[0])
                r_ = await c('preview_node', {'node_id': slope, **G})
                check('preview_node', 'intermediate node', is_image(r_), '' if is_image(r_) else text(r_))
                t = text(await c('disconnect', {'node_id': slope, 'input_id': 'Effect', **G}))
                check('disconnect', 'one link', 'removed 1' in t, t)
                tmp = added_id(text(await c('add_node', {'definition': 'blur', **G})))
                t = text(await c('delete_nodes', {'node_ids': [tmp], **G}))
                check('delete_nodes', 'one node', 'deleted %s blur' % tmp in t, t)

                # --- bitmaps
                from PIL import Image
                png = os.path.join(scratch, 'selftest_bitmap.png')
                Image.new('RGB', (64, 32), (200, 100, 50)).save(png)
                t = text(await c('import_bitmap', {'path': png, 'position': [-600, 300], **G}))
                check('import_bitmap', 'linked, native size', 'size (6, 5)' in t, t)
                bm = added_id(t)
                t = text(await c('node_stats', {'node_id': bm, 'points': [[0, 0]], **G}))
                check('import_bitmap', 'pixels match file', 'R=0.7843, G=0.3922, B=0.1961' in t, t)
                t = text(await c('apply_edits', {'ops': [{'op': 'bitmap', 'path': png, 'ref': 'img'},
                                                         {'op': 'delete', 'node': 'img'}], **G}))
                check('import_bitmap', 'apply_edits op, link reused', 'reusing bitmap resource' in t, t)
                r_ = await c('compare_to_reference', {'node_id': bm, 'reference_path': png, 'aligned': True, **G})
                t = text(r_)
                check('compare_to_reference', 'same image matches', 'EMD 0.000' in t and 'mean abs diff 0.0000' in t
                      and any(x.type == 'image' for x in r_.content), t)
                darker = os.path.join(scratch, 'selftest_darker.png')
                Image.new('RGB', (128, 64), (100, 50, 25)).save(darker)
                t = text(await c('compare_to_reference', {'node_id': bm, 'reference_path': darker, **G}))
                check('compare_to_reference', 'shift measured', 'R     0.784' in t and 'mean -0.392' in t, t)
                r_ = await c('compare_to_reference', {'node_id': bm, 'reference_path': png, 'region': [100, 100, 120, 120], **G})
                check('compare_to_reference', 'error on empty region', r_.is_error and 'is empty' in text(r_), text(r_))
                r_ = await c('import_bitmap', {'path': os.path.join(scratch, 'missing.png'), **G})
                check('import_bitmap', 'error on missing file', r_.is_error and 'no such file' in text(r_), '')
                # imported RGB JPGs and grey+alpha PNGs compute as RGBA8, like RGBA files; the other
                # pixel layouts are decoded too, but Designer's outputs weren't seen using them (REVIEW.md SRV-8)
                jpg, la_png = os.path.join(scratch, 'selftest_rgb.jpg'), os.path.join(scratch, 'selftest_la.png')
                Image.new('RGB', (8, 8), (200, 100, 50)).save(jpg, quality=100)
                la = Image.new('LA', (8, 8), (128, 255))
                la.paste((0, 0), (4, 0, 8, 8))                     # right half transparent
                la.save(la_png)
                formats = []
                for path in (jpg, la_png):
                    extra_bm = added_id(text(await c('import_bitmap', {'path': path, **G})))
                    formats.append(text(await c('node_stats', {'node_id': extra_bm, **G})).splitlines()[0].split()[-1])
                    await c('delete_nodes', {'node_ids': [extra_bm], **G})
                check('designer facts', 'imported JPG and grey+alpha PNG compute as RGBA8', formats == ['RGBA8'] * 2,
                      str(formats))
                # a grey+alpha reference's transparent half is ignored (REVIEW.md SRV-9)
                t = text(await c('compare_to_reference', {'node_id': bm, 'reference_path': la_png, **G}))
                check('compare_to_reference', 'grey+alpha reference: transparent pixels ignored',
                      'ignoring 50.0% transparent reference pixels' in t, t.splitlines()[1] if '\n' in t else t)

                # --- pixel statistics
                t = text(await c('node_stats', {'node_id': lv, 'points': [[0, 0]], 'region': [0, 0, 64, 64], **G}))
                check('node_stats', 'stats + region + point', 'min' in t and 'pixel (0,0)' in t and 'region' in t, t.splitlines()[0])
                uni = added_id(text(await c('add_node', {'definition': 'uniform', 'params': {'outputcolor': [0.2, 0.4, 0.6, 0.8]}, **G})))
                t = text(await c('node_stats', {'node_id': uni, 'points': [[1, 1]], **G}))
                check('node_stats', 'exact known colour', 'R=0.2000, G=0.4000, B=0.6000, A=0.8000' in t, t.splitlines()[-1])
                await c('delete_nodes', {'node_ids': [uni], **G})

                # --- parameter sweep, tiling, log
                before = text(await c('describe_graph', {'node_ids': [clouds], 'include_params': True, **G}))
                r_ = await c('sweep_param', {'node_id': clouds, 'param': 'scale', 'values': [1, 4, 16],
                                             'view_node': slope, 'tile_size': 128, **G})
                sweep_text = text(r_)
                images = [x for x in r_.content if x.type == 'image']
                after = text(await c('describe_graph', {'node_ids': [clouds], 'include_params': True, **G}))
                check('sweep_param', '3 values + image', len(images) == 1 and sweep_text.count('scale = ') == 3, sweep_text.splitlines()[0])
                check('sweep_param', 'original restored', 'restored' in sweep_text and before == after, '')
                before = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
                t = text(await c('sweep_param', {'node_id': lv, 'param': '$outputsize', 'values': [[7, 7], [8, 8]], **G}))
                after = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
                check('sweep_param', '$outputsize takes effect and is restored', '(128x128)' in t and '(256x256)' in t
                      and before == after, t + before + after)
                # changing a parameter's inheritance resets its value to the default (AGENTS.md), so a sweep
                # of one that isn't Absolute must put the inheritance back before the value (REVIEW.md HLP-26)
                RELATIVE_SIZE = GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n"
                    "from sd.api.sdvalueint2 import SDValueInt2\nfrom sd.api.sdbasetypes import int2\n"
                    "n = g.getNodeFromId('%s'); p = n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
                    "n.setPropertyInheritanceMethod(p, IM.RelativeToParent)\n"
                    "n.setPropertyValue(p, SDValueInt2.sNew(int2(1, 1)))\n"
                    "%s\n"
                    "v = n.getPropertyValue(p).get()\n"
                    "print('INHERIT=%%s VALUE=%%d,%%d' %% (n.getPropertyInheritanceMethod(p).name, v.x, v.y))")
                # each switch on its own, on a node and on the graph (REVIEW.md TST-42)
                fact = text(await c('execute_designer_code', {'code': GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n"
                    "from sd.api.sdvalueint import SDValueInt\nfrom sd.api.sdvalueint2 import SDValueInt2\n"
                    "from sd.api.sdbasetypes import int2\n"
                    "def resets(target, pid, value, read, start):\n"
                    "    p = target.getPropertyFromId(pid, SDPropertyCategory.Input); was = target.getPropertyInheritanceMethod(p)\n"
                    "    kept = target.getPropertyValue(p)\n"
                    "    seen = []\n"
                    "    try:\n"   # put back even if a call fails, for the later checks (REVIEW.md TST-46)
                    "        for there, back in ((start, IM.Absolute), (IM.Absolute, start)):\n"
                    "            target.setPropertyInheritanceMethod(p, there); target.setPropertyValue(p, value)\n"
                    "            target.setPropertyInheritanceMethod(p, back); seen.append(read(target.getPropertyValue(p).get()))\n"
                    "    finally:\n"
                    "        target.setPropertyInheritanceMethod(p, was); target.setPropertyValue(p, kept)\n"
                    "    return seen\n"
                    "n = g.getNodeFromId('%s')\n"
                    "print('NODE_SIZE=%%s' %% resets(n, '$outputsize', SDValueInt2.sNew(int2(1, 1)), lambda v: (v.x, v.y), IM.RelativeToParent))\n"
                    "print('GRAPH_SEED=%%s' %% resets(g, '$randomseed', SDValueInt.sNew(5), lambda v: v, IM.RelativeToParent))") % lv}))
                # neither switch keeps the value set (1, 1 / 5), and back to inherited gives the default
                # (REVIEW.md TST-45)
                kept_any = re.search(r'\(1, 1\)|SEED=\[[^]]*\b5\b', fact)
                default_back = re.search(r'NODE_SIZE=\[\([^)]*\), \(0, 0\)\]', fact) and re.search(r'GRAPH_SEED=\[-?\d+, 0\]', fact)
                check('designer facts', "changing a parameter's inheritance doesn't keep its value, either way, node or graph (AGENTS.md)",
                      default_back and not kept_any, fact.strip())
                await c('execute_designer_code', {'code': RELATIVE_SIZE % (lv, '')})
                t = text(await c('sweep_param', {'node_id': lv, 'param': '$outputsize', 'values': [[7, 7]], **G}))
                after = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
                check('sweep_param', 'a relative $outputsize comes back with its offset', 'INHERIT=RelativeToParent' in after
                      and 'VALUE=x: 1, y: 1' in after, t.splitlines()[-1] + ' | ' + after.strip())
                await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv) + (
                    "\nfrom sd.api.sdproperty import SDPropertyInheritanceMethod as IM\n"
                    "n.setPropertyInheritanceMethod(p, IM.RelativeToInput)")})   # back as before
                r_ = await c('sweep_param', {'node_id': lv, 'param': 'nope', 'values': [1], **G})
                check('sweep_param', 'error on bad param', r_.is_error and 'not a parameter' in text(r_), text(r_))
                t = text(await c('check_tiling', {'node_id': clouds, **G}))
                check('check_tiling', 'tileable noise passes both axes', t.count('tiles seamlessly') == 2, t)
                grad = added_id(text(await c('add_node', {'definition': 'gradient_linear_1', **G})))
                r_ = await c('check_tiling', {'node_id': grad, 'axis': 'diagonal', **G})
                check('check_tiling', 'error on bad axis', r_.is_error and "axis must be" in text(r_), text(r_))
                t = text(await c('check_tiling', {'node_id': grad, 'axis': 'vertical', **G}))
                check('check_tiling', 'vertical gradient has a seam', 'VISIBLE SEAM' in t, t.splitlines()[-1])
                await c('delete_nodes', {'node_ids': [grad], **G})
                t = text(await c('read_designer_log', {'contains': PLUGIN, 'lines': 5}))
                check('read_designer_log', 'finds bridge start', 'listening on' in t, t.splitlines()[0])
                # a warning of our own, so the filter has something to find (REVIEW.md TST-4)
                marker = 'mcp self-test warning %d' % os.getpid()
                await c('execute_designer_code', {'code': "import sd\nsd.getContext().getLogger().warning(%r)" % marker})
                t = text(await c('read_designer_log', {'errors_only': True, 'lines': 400}))
                found = t.splitlines()[1:]
                check('read_designer_log', 'errors_only filter', any(marker in l for l in found) and all(
                    ('[ERROR]' in l or '[WARNING]' in l) for l in found), t.splitlines()[0])
                t = text(await c('read_designer_log', {'lines': 5, 'since_last_start': False}))
                check('read_designer_log', 'whole log', 'log.txt' in t, t.splitlines()[0])

                # --- batch edits
                t = text(await c('apply_edits', {'ops': [
                    {'op': 'add', 'definition': 'uniform', 'ref': 'u', 'position': [-300, 300],
                     'params': {'colorswitch': False, 'outputcolor': [0.5, 0.5, 0.5, 1]}},
                    {'op': 'add', 'definition': 'blend', 'ref': 'b', 'params': {'blendingmode': 'multiply'}},
                    {'op': 'connect', 'from': 'u', 'to': 'b', 'input': 'source'},
                    {'op': 'connect', 'from': slope, 'to': 'b', 'input': 'destination'},
                    {'op': 'move', 'node': 'b', 'position': [0, 300]},
                    {'op': 'set', 'node': 'b', 'params': {'opacitymult': 0.5}},
                    {'op': 'disconnect', 'node': 'b', 'input': 'destination'},
                    {'op': 'expose', 'node': 'b', 'param': 'opacitymult', 'input_id': 'batch_opacity', 'max': 1,
                     'step': 0.05, 'group': 'Batch'},
                ], **G}))
                check('apply_edits', '8 ops with refs', 'applied 8 op(s)' in t and "removed 1 connection(s) into" in t
                      and "graph input 'batch_opacity'" in t, t.splitlines()[-1])
                line = next((l for l in text(await c('list_graph_inputs', G)).splitlines()
                             if l.startswith('batch_opacity')), '')
                check('apply_edits', 'expose op passes step and group', "group='Batch'" in line and 'step=0.05' in line, line)
                await c('remove_graph_input', {'input_id': 'batch_opacity', **G})
                batch_blend = re.search(r"'b': '(\d+)'", t).group(1)
                r_ = await c('apply_edits', {'ops': [
                    {'op': 'add', 'definition': 'levels', 'ref': 'x'},
                    {'op': 'connect', 'from': 'x', 'to': batch_blend, 'input': 'nope'},
                ], **G})
                check('apply_edits', 'stops at failing op', r_.is_error and 'op 1 (connect) failed' in text(r_), text(r_))
                # the "its node was added" note only when a node really was (REVIEW.md HLP-5)
                r_ = await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'not_a_real_node', 'params': {'a': 1}}], **G})
                check('apply_edits', 'a bad definition is not reported as added', r_.is_error
                      and 'op 0 (add) failed' in text(r_) and 'its node was added' not in text(r_), text(r_))
                r_ = await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels', 'params': {'nope': 1}}], **G})
                check('apply_edits', 'a node added before its params failed is reported', r_.is_error
                      and 'its node was added' in text(r_), text(r_))
                # an enum value as a numeric string, like int parameters accept (REVIEW.md HLP-11)
                r_ = await c('set_params', {'node_id': batch_blend, 'params': {'blendingmode': '3'}, **G})
                check('set_params', 'enum value as a numeric string', not r_.is_error, text(r_))
                t = text(await c('describe_graph', G))
                x_ids = [l.split()[0] for l in t.splitlines() if ' levels ' in l and l.split()[0] != lv]
                await c('delete_nodes', {'node_ids': x_ids + [batch_blend] + [l.split()[0] for l in t.splitlines()
                                         if ' uniform ' in l], **G})

                # --- exposed inputs and graph size
                t = text(await c('set_graph_size', {'size_log2': 9, 'overridable': True, **G}))
                check('set_graph_size', 'overridable 512', 'overridable, default 512 px' in t, t)
                await c('snapshot_graph', {'label': 'overridable size', **G})
                t = text(await c('set_graph_size', {'size_log2': 9, 'overridable': False, **G}))
                check('set_graph_size', 'fixed 512', 'size: fixed' in t, t)
                t = text(await c('diff_graph', {'against': 'overridable size', **G}))
                check('diff_graph', 'size labels (fixed is absolute)',
                      '~ graph outputsize: (default: relative to parent) -> 9 9 (absolute)' in t, t)
                await c('set_graph_size', {'size_log2': 9, 'overridable': True, **G})   # render checks need it
                t = text(await c('expose_param', {'node_id': lv, 'param': 'leveloutlow', 'input_id': 'floor',
                                                  'label': 'Floor', 'default': [0.25] * 4, 'min': 0, 'max': 1, **G}))
                check('expose_param', 'float4 with range', "graph input 'floor'" in t, t)
                t = text(await c('expose_param', {'node_id': slope, 'param': 'Samples', **G}))
                check('expose_param', 'int, defaults to current value', "'Samples'" in t and 'default 16' in t, t)
                # a failure after the function graph was created leaves no function graph behind
                # (REVIEW.md HLP-3): the getter for float4 renamed to a type that doesn't exist
                with open(os.path.join(BUNDLE, 'mcp_server', 'designer_helpers.py'), encoding='utf-8') as f:
                    helpers_src = f.read()
                t = text(await c('execute_designer_code', {'code': helpers_src + (
                    "\nset_params(%r, %r, {'levelinhigh': [0.8] * 4})\n"
                    "_GETTERS['float4'] = 'get_no_such_type'\n"
                    "try:\n    expose_param(%r, %r, 'levelinhigh', input_id='broken')\nexcept (Exception, APIException) as e:\n"
                    "    print('FAILED', type(e).__name__)\n"
                    "g = find_graph(%r); n = g.getNodeFromId(%r)\n"
                    "p = n.getPropertyFromId('levelinhigh', SDPropertyCategory.Input)\n"
                    "print('LEFT_GRAPH=%%s LEFT_INPUT=%%s VALUE=%%.2f' %% (n.getPropertyGraph(p) is not None, "
                    "g.getPropertyFromId('broken', SDPropertyCategory.Input) is not None, n.getPropertyValue(p).get().x))\n"
                    "set_params(%r, %r, {'levelinhigh': [1.0] * 4})") % (
                        TEST_GRAPH, lv, TEST_GRAPH, lv, TEST_GRAPH, lv, TEST_GRAPH, lv)}))
                # ...and the parameter keeps the value it had (adding the graph reset it; REVIEW.md HLP-21)
                check('expose_param', 'a failure midway leaves nothing behind', 'FAILED' in t
                      and 'LEFT_GRAPH=False LEFT_INPUT=False VALUE=0.80' in t, t.strip()[-160:])
                # and when the parameter already had an empty function graph, which is reused, a
                # failure leaves no half-made get node in it (REVIEW.md HLP-15)
                t = text(await c('execute_designer_code', {'code': helpers_src + (
                    "\ng = find_graph(%r); n = g.newNode('sbs::compositing::levels')\n"
                    "p = n.getPropertyFromId('levelinhigh', SDPropertyCategory.Input)\n"
                    "n.newPropertyGraph(p, 'SDSBSFunctionGraph')\ncls = type(n.getPropertyGraph(p))\n"
                    "real = cls.setOutputNode\n"
                    "def _fails(*a, **k):\n    raise RuntimeError('fails on purpose')\n"
                    "cls.setOutputNode = _fails\n"
                    "try:\n"
                    "    try:\n        expose_param(%r, n.getIdentifier(), 'levelinhigh', input_id='broken_reused')\n"
                    "    except (Exception, APIException) as e:\n        print('FAILED', type(e).__name__)\n"
                    "finally:\n    cls.setOutputNode = real\n"
                    "fg = n.getPropertyGraph(p)\n"
                    "print('LEFT_NODES=%%d LEFT_INPUT=%%s' %% (len(fg.getNodes()) if fg is not None else 0, "
                    "g.getPropertyFromId('broken_reused', SDPropertyCategory.Input) is not None))\n"
                    "g.deleteNode(n)") % (TEST_GRAPH, TEST_GRAPH)}))
                check('expose_param', 'a failure on a reused empty function graph leaves no node in it',
                      'FAILED' in t and 'LEFT_NODES=0 LEFT_INPUT=False' in t, t.strip()[-160:])
                # setting a driven parameter would change only a hidden constant (REVIEW.md HLP-2)
                r_ = await c('set_params', {'node_id': lv, 'params': {'leveloutlow': [0.5] * 4}, **G})
                check('set_params', 'refuses a parameter driven by a graph input', r_.is_error
                      and "driven by graph input 'floor'" in text(r_), text(r_))
                r_ = await c('expose_param', {'node_id': lv, 'param': 'leveloutlow', 'input_id': 'floor', **G})
                check('expose_param', 'error on duplicate input', r_.is_error and 'already has an input' in text(r_), text(r_))
                t = text(await c('list_graph_inputs', G))
                check('list_graph_inputs', 'inputs + users', "floor (float4)" in t and "label='Floor'" in t
                      and '%s.leveloutlow' % lv in t and 'Samples' in t, t)
                await c('expose_param', {'node_id': slope, 'param': 'Intensity', 'input_id': 'slope_amount',
                                         'group': 'Shape', 'step': 0.5, 'min': 0, 'max': 20, **G})
                t = text(await c('list_graph_inputs', G))
                line = next((l for l in t.splitlines() if l.startswith('slope_amount')), '')
                check('expose_param', 'group + step', "group='Shape'" in line and 'step=0.5' in line, line)
                await c('remove_graph_input', {'input_id': 'slope_amount', **G})
                await c('expose_param', {'node_id': lv, 'param': 'levelinmid', 'input_id': 'mid', **G})
                extra = GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory\nn=g.getNodeFromId('%s')\n"
                    "p=n.getPropertyFromId('levelinmid', SDPropertyCategory.Input)\n") % lv
                await c('execute_designer_code', {'code': extra + "n.getPropertyGraph(p).newNode('sbs::function::const_float1')\nprint('extra node')"})
                r_ = await c('remove_graph_input', {'input_id': 'mid', **G})
                still = 'mid (float4)' in text(await c('list_graph_inputs', G))
                check('remove_graph_input', 'refuses while a larger function reads it', r_.is_error
                      and 'read inside the functions' in text(r_) and still, text(r_))
                # an empty function graph on a parameter drives nothing (REVIEW.md HLP-13, HLP-16),
                # measured: adding one resets the stored value to its default and the output follows
                # that value; set_params then sets the value (which deletes the empty graph) and the
                # output follows again
                def stats_max(text_):
                    m = re.search(r'^\w: min [0-9.]+  max ([0-9.]+)', text_, re.M)
                    return float(m.group(1)) if m else None
                probe = GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory\nn=g.getNodeFromId('%s')\n"
                    "p=n.getPropertyFromId('levelouthigh', SDPropertyCategory.Input)\n") % lv
                max_default = stats_max(text(await c('node_stats', {'node_id': lv, **G})))
                await c('set_params', {'node_id': lv, 'params': {'levelouthigh': [0.5, 0.5, 0.5, 1]}, **G})
                max_half = stats_max(text(await c('node_stats', {'node_id': lv, **G})))
                empty_fn = text(await c('execute_designer_code', {'code': probe + (
                    "n.newPropertyGraph(p, 'SDSBSFunctionGraph')\n"
                    "print('EMPTY_FUNCTION nodes=%d value=%s' % (len(n.getPropertyGraph(p).getNodes()), "
                    "tuple(round(x, 3) for x in (lambda v: (v.x, v.y, v.z, v.w))(n.getPropertyValue(p).get()))))")}))
                max_empty = stats_max(text(await c('node_stats', {'node_id': lv, **G})))
                check('designer facts', 'adding a function graph resets the stored value; the output follows the stored value',
                      'EMPTY_FUNCTION nodes=0 value=(1.0, 1.0, 1.0, 1.0)' in empty_fn and max_half is not None
                      and max_half < max_default - 0.3 and abs(max_empty - max_default) < 0.002,   # render noise (TST-22)
                      'max %s at 1.0, %s at 0.5, %s with an empty graph added; %s'
                      % (max_default, max_half, max_empty, empty_fn.strip()))
                t = text(await c('describe_graph', {'node_ids': [lv], 'include_params': True, **G}))
                r_ = await c('set_params', {'node_id': lv, 'params': {'levelouthigh': [0.5, 0.5, 0.5, 1]}, **G})
                kept = text(await c('execute_designer_code', {'code': probe + "print('GRAPH_KEPT=%s' % (n.getPropertyGraph(p) is not None))"}))
                max_set = stats_max(text(await c('node_stats', {'node_id': lv, **G})))
                check('set_params', 'an empty function graph is not "driven": the value is set and drives the output',
                      not r_.is_error and 'levelouthigh <-' not in t and 'GRAPH_KEPT=False' in kept and abs(max_set - max_half) < 0.002,
                      '%s | %s | max %s' % (text(r_).strip()[-80:], kept.strip(), max_set))
                # sweep_param and expose_param agree (they use the same test, REVIEW.md TST-20)
                await c('execute_designer_code', {'code': probe + "n.newPropertyGraph(p, 'SDSBSFunctionGraph')"})
                r_sweep = await c('sweep_param', {'node_id': lv, 'param': 'levelouthigh', 'values': [[0.4] * 4, [0.6] * 4],
                                                  'tile_size': 64, **G})
                await c('execute_designer_code', {'code': probe + "n.newPropertyGraph(p, 'SDSBSFunctionGraph')"})
                r_expose = await c('expose_param', {'node_id': lv, 'param': 'levelouthigh', 'input_id': 'empty_fn_check', **G})
                await c('remove_graph_input', {'input_id': 'empty_fn_check', **G})
                check('sweep_param', 'an empty function graph is not "driven" for sweep_param and expose_param',
                      not r_sweep.is_error and not r_expose.is_error,
                      (text(r_sweep) if r_sweep.is_error else '') + (text(r_expose) if r_expose.is_error else '') or 'both ran')
                # a driven parameter shows its source, not the constant it hides (REVIEW.md HLP-9)
                t = text(await c('describe_graph', {'node_ids': [lv], 'include_params': True, **G}))
                check('describe_graph', 'driven parameters show what drives them',
                      "leveloutlow <- graph input 'floor'" in t and 'levelinmid <- a function' in t, t)
                r_ = await c('expose_param', {'node_id': lv, 'param': 'levelinmid', 'input_id': 'mid2', **G})
                check('expose_param', 'refuses a parameter driven by a function', r_.is_error
                      and 'already driven by a function' in text(r_), text(r_))
                await c('execute_designer_code', {'code': extra + "n.deletePropertyGraph(p)\nprint('function removed')"})
                t = text(await c('remove_graph_input', {'input_id': 'mid', **G}))
                check('remove_graph_input', 'removes once nothing reads it', 'removed graph input mid' in t, t)
                r_ = await c('sweep_param', {'node_id': 'graph', 'param': 'floor', 'values': [[0.1] * 4, [0.9] * 4],
                                             'view_node': lv, 'tile_size': 96, **G})
                means = [float(m) for m in re.findall(r'L [0-9.]+\.\.[0-9.]+ \(mean ([0-9.]+)\)', text(r_))]
                check('sweep_param', 'graph input changes output', len(means) == 2 and means[1] > means[0] + 0.3, text(r_))
                t = text(await c('remove_graph_input', {'input_id': 'Samples', **G}))
                check('remove_graph_input', 'unbinds + keeps value', 'kept value 16' in t and 'removed graph input' in t, t)

                # --- snapshots, diff, layout, frames
                t = text(await c('snapshot_graph', {'label': 'before tweak', **G}))
                check('snapshot_graph', 'saved', 'snapshot of %s saved' % TEST_GRAPH in t, t)
                snap_path = t.split('saved: ', 1)[1].strip()
                t = text(await c('list_snapshots', G))
                check('list_snapshots', 'lists it', snap_path in t, '')
                t = text(await c('list_snapshots'))
                check('list_snapshots', 'all graphs', snap_path in t, t[:200])
                r_ = await c('diff_graph', {'against': 'no such label', **G})
                check('diff_graph', 'error: unknown snapshot label', r_.is_error and 'no snapshot matching' in text(r_), text(r_))
                await c('set_params', {'node_id': lv, 'params': {'levelinhigh': [0.8] * 4}, **G})
                tmp_node = added_id(text(await c('add_node', {'definition': 'blur', **G})))
                t = text(await c('diff_graph', {'against': 'latest', **G}))
                check('diff_graph', 'sees param change + new node', 'levelinhigh' in t and '+ node %s blur' % tmp_node in t, t.splitlines()[0])
                t = text(await c('diff_graph', {'against': 'before tweak', **G}))
                check('diff_graph', 'by label', 'levelinhigh' in t, '')
                await c('delete_nodes', {'node_ids': [tmp_node], **G})
                await c('set_params', {'node_id': lv, 'params': {'levelinhigh': [1.0] * 4}, **G})   # undo the tweak
                t = text(await c('diff_graph', {'against': 'latest', **G}))
                check('diff_graph', 'no differences after reverting', 'No differences' in t or 'Only node positions' in t, t.splitlines()[-1])
                os.remove(snap_path)
                if not os.listdir(os.path.dirname(snap_path)):
                    os.rmdir(os.path.dirname(snap_path))
                t = text(await c('arrange_graph', G))
                check('arrange_graph', 'columns by data flow', 'arranged' in t and 'column' in t, t)
                t = text(await c('describe_graph', G))
                xs = {l.split()[0]: int(re.search(r'@\((-?\d+),', l).group(1)) for l in t.splitlines() if '@(' in l}
                check('arrange_graph', 'upstream left of downstream', xs[clouds] < xs[slope] < xs[lv] < xs[out], str(xs))
                t = text(await c('add_frame', {'node_ids': [clouds, slope], 'title': 'Shape', 'color': [0.2, 0.4, 0.8], **G}))
                check('add_frame', 'frame drawn', "frame 'Shape' around 2 node(s)" in t, t)
                t = text(await c('add_comment', {'text': 'self-test note', 'node_id': lv, **G}))
                check('add_comment', 'attached comment', 'comment added on node' in t, t)
                t = text(await c('add_comment', {'text': 'free note', 'position': [0, -300], **G}))
                check('add_comment', 'free-standing at a position', t.strip() == 'comment added', t)
                await c('add_frame', {'node_ids': [lv], 'title': 'Described', 'description': 'why this frame', **G})
                t = text(await c('execute_designer_code', {'code': (
                    "import sd\nfrom sd.api.sdgraphobjectframe import SDGraphObjectFrame\n"
                    "g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() "
                    "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
                    "print([o.getDescription() for o in g.getGraphObjects() if isinstance(o, SDGraphObjectFrame) "
                    "and o.getTitle()=='Described'])") % TEST_GRAPH}))
                check('add_frame', 'description stored', "['why this frame']" in t, t)
                await c('arrange_graph', {'node_ids': [clouds, slope], 'spacing': [300, 150], **G})
                xs = positions(text(await c('describe_graph', G)))
                check('arrange_graph', 'node_ids + spacing', abs(xs[slope][0] - xs[clouds][0] - 300) < 1, str(xs))
                await c('arrange_graph', G)
                t = text(await c('describe_graph', {'limit': 2, **G}))
                check('describe_graph', 'limit', re.search(r'\.\.\. \d+ more nodes', t) is not None, t.splitlines()[-1])
                t = text(await c('describe_graph', G))
                check('describe_graph', 'lists frames + comments', "frames: 'Shape', 'Described'" in t and 'comments: 2' in t,
                      next((l for l in t.splitlines() if 'frames' in l), t.splitlines()[1]))
                t = text(await c('describe_node', {'definition': 'bevel'}))
                check('describe_node', 'library slider range', 'range -1.0..1.0' in t, '')

                # --- Designer facts that AGENTS.md relies on (fail if a Designer update changes them)
                F = 'designer facts'
                t = text(await c('describe_node', {'definition': 'blend'}))
                check(F, 'blend mode ids', 'copy=0, add=1, substract=2, multiply=3, addsub=4, max=5, min=6, '
                      'switch=7, divide=8, overlay=9, screen=10, softlight=11' in t, '')
                check(F, '$format ids', '8_bits_per_channel=0, 16_bits_per_channel=1, hdr_low_precision=2, '
                      'hdr_high_precision=3' in t, '')
                for definition, ins, outs in [('bevel', ['input'], ['height', 'normal']),
                                              ('tile_generator', [], ['TileGenerator']),
                                              ('hbao', ['input'], ['output']),
                                              ('curvature_smooth', ['input'], ['height'])]:
                    t = text(await c('describe_node', {'definition': definition}))
                    out_line = re.search(r'output connector ids: (.*)', t)
                    ok = (out_line is not None and all("'%s'" % o in out_line.group(1) for o in outs)
                          and all(re.search(r'^\s+%s\s+CONNECTOR' % i, t, re.M) for i in ins))
                    check(F, '%s connectors' % definition, ok, out_line.group(0) if out_line else t[:150])
                t = text(await c('execute_designer_code', {'code': FACTS % (TEST_GRAPH, lv, lv, slope)}))
                check(F, '29 atomic nodes', 'ATOMIC=29' in t, t)
                check(F, 'APIException is not an Exception', 'APIEXC_BASE_ONLY=True' in t, t)
                check(F, 'connections reported from queried side', 'QUERIED_SIDE=True' in t, t)
                # how a .sbs stores size inheritance (server._RELATIVE_TO): measure it
                inherit_dir = os.path.join(scratch, 'inherit')
                t = text(await c('execute_designer_code', {'code': (
                    "import sd, os\nfrom sd.api.sbs.sdsbscompgraph import SDSBSCompGraph\n"
                    "from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as M\n"
                    "pm=sd.getContext().getSDApplication().getPackageMgr()\nos.makedirs(%r, exist_ok=True)\n"
                    "for m in (M.Absolute, M.RelativeToInput, M.RelativeToParent):\n"
                    "    pkg=pm.newUserPackage(); g=SDSBSCompGraph.sNew(pkg); g.setIdentifier('mcp_selftest_inherit_'+m.name)\n"
                    "    n=g.newNode('sbs::compositing::blur')\n"
                    "    g.setPropertyInheritanceMethod(g.getPropertyFromId('$outputsize', SDPropertyCategory.Input), m)\n"
                    "    n.setPropertyInheritanceMethod(n.getPropertyFromId('$outputsize', SDPropertyCategory.Input), m)\n"
                    "    pm.savePackageAs(pkg, os.path.join(%r, m.name + '.sbs')); pm.unloadUserPackage(pkg)\n"
                    "print('saved')") % (inherit_dir, inherit_dir)}))
                stored = {}
                for name in ('Absolute', 'RelativeToInput', 'RelativeToParent'):
                    import xml.etree.ElementTree as ET
                    g_el = next(ET.parse(os.path.join(inherit_dir, name + '.sbs')).getroot().iter('graph'))
                    graph_rel = [p.find('relativeTo').get('v') for p in g_el.find('baseParameters') or []]
                    node_rel = [p.find('relativeTo').get('v') for p in g_el.iter('parameter') if p.find('name').get('v') == 'outputsize'
                                and p not in list(g_el.find('baseParameters') or [])]
                    stored[name] = (graph_rel, node_rel)
                check(F, '.sbs size inheritance: 0 absolute, 1 parent, 2 input, defaults unstored',
                      stored == {'Absolute': (['0'], ['0']), 'RelativeToInput': (['2'], []), 'RelativeToParent': ([], ['1'])},
                      str(stored))
                # REVIEW.md TST-3: the remaining AGENTS.md facts, measured
                t = text(await c('execute_designer_code', {'code': (
                    "from sd.api.sdproperty import SDPropertyInheritanceMethod as M\n"
                    "print('API_INHERIT=%d,%d,%d' % (M.RelativeToInput.value, M.RelativeToParent.value, M.Absolute.value))")}))
                check(F, 'API inheritance: RelativeToInput 0, RelativeToParent 1, Absolute 2', 'API_INHERIT=0,1,2' in t, t)
                # two unsaved packages copy the same file, one after the other: AGENTS.md says the copy
                # goes to <OS temp>/Adobe/Adobe Substance 3D Designer/ with an XXXXXX- prefix, stays
                # after its package closes, and so the next copy of that name gets 1- in front
                # (REVIEW.md TST-15: the check used to test only "under the temp folder")
                t = text(await c('execute_designer_code', {'code': (
                    "import os, sd\nfrom sd.api.sbs.sdsbscompgraph import SDSBSCompGraph\n"
                    "from sd.api.sdresourcebitmap import SDResourceBitmap\nfrom sd.api.sdresource import EmbedMethod\n"
                    "pm=sd.getContext().getSDApplication().getPackageMgr()\n"
                    "for i in range(2):\n"
                    "    pkg=pm.newUserPackage()\n"
                    "    SDSBSCompGraph.sNew(pkg).setIdentifier('mcp_selftest_unsaved_copy')\n"
                    "    res=SDResourceBitmap.sNewFromFile(pkg, %r, EmbedMethod.CopiedAndLinked)\n"
                    "    path=res.getFilePath()\n    pm.unloadUserPackage(pkg)\n"
                    "    print('COPY=%%s STAYS=%%s' %% (path, os.path.isfile(path)))") % png}))
                copies = re.findall(r'COPY=(.*) STAYS=(\w+)', t)
                names = [os.path.basename(p) for p, _ in copies]
                folders = {os.path.normcase(os.path.realpath(os.path.dirname(p))) for p, _ in copies}
                expected_folder = os.path.normcase(os.path.realpath(os.path.join(
                    tempfile.gettempdir(), 'Adobe', 'Adobe Substance 3D Designer')))
                check(F, 'CopiedAndLinked before the first save: XXXXXX- copy in <OS temp>/Adobe/Adobe Substance 3D '
                      'Designer/, kept after closing, the next one numbered',
                      len(copies) == 2 and all(stays == 'True' for _, stays in copies) and folders == {expected_folder}
                      and names[0].endswith('XXXXXX-' + os.path.basename(png))
                      and names[1] != names[0] and re.match(r'^\d+-%s$' % re.escape(re.sub(r'^\d+-', '', names[0])),
                                                            names[1]) is not None, t.strip())
                for copy_path, _ in copies:
                    if os.path.isfile(copy_path) and 'XXXXXX-' in os.path.basename(copy_path):
                        os.remove(copy_path)   # Designer leaves them there
                t = text(await c('describe_node', {'definition': 'tile_generator'}))
                ids_ok = all(re.search(r'^\s+%s\s' % re.escape(i), t, re.M) for i in (
                    'Nb_X', 'Nb_Y', 'Pattern_Type', 'Scale', 'Offset', 'Offset_Random', 'Offset_Random_Seed',
                    'Free_Rotation', 'Luminance_Variation-Contrast'))
                pattern = re.search(r'^\s+Pattern_Type\s.*default=(\d+)\n\s+enum: (.*)$', t, re.M)
                check(F, 'tile_generator ids; Pattern_Type 1 image input, 2 square, 9 brick (default)', ids_ok and pattern is not None
                      and pattern.group(1) == '9' and 'Image input=1, Square=2' in pattern.group(2) and 'Brick=9' in pattern.group(2),
                      pattern.group(0).strip()[:150] if pattern else 'Pattern_Type not found')
                aniso = added_id(text(await c('add_node', {'definition': 'noise_anisotropic_noise.sbs/anisotropic_noise', **G})))
                r_ = await c('preview_node', {'node_id': aniso, 'max_size': 256, **G})
                if is_image(r_):
                    import numpy as np
                    from PIL import Image as PILImage
                    import io as _io
                    img = next(x for x in r_.content if x.type == 'image')
                    a_ = np.asarray(PILImage.open(_io.BytesIO(base64.b64decode(img.data))).convert('L'), dtype=float)
                    along_x, along_y = np.abs(np.diff(a_, axis=1)).mean(), np.abs(np.diff(a_, axis=0)).mean()
                    check(F, 'anisotropic noise streaks run horizontally by default', along_y > 2 * along_x,
                          'mean step along x %.2f, along y %.2f' % (along_x, along_y))
                else:
                    check(F, 'anisotropic noise streaks run horizontally by default', False, text(r_))
                await c('delete_nodes', {'node_ids': [aniso], **G})
                # exposing a parameter logs these until the function node is named: count each
                # message before and after an exposure made here, so earlier lines can't satisfy the
                # check (REVIEW.md TST-13: it once compared against a header it could never match)
                noise = ('No output node defined', "nodes don't have a variable name")   # logged as "Some <b>Get</b> nodes ..."

                async def noise_counts():
                    found = []
                    for message in noise:
                        header = text(await c('read_designer_log', {'contains': message, 'lines': 1})).splitlines()[0]
                        found.append(int(re.search(r'\((\d+) matching line', header).group(1)))
                    return found
                before = await noise_counts()
                log_lv = added_id(text(await c('add_node', {'definition': 'levels', **G})))
                await c('expose_param', {'node_id': log_lv, 'param': 'levelinlow', 'input_id': 'log_noise_check', **G})
                after = await noise_counts()
                await c('remove_graph_input', {'input_id': 'log_noise_check', **G})
                await c('delete_nodes', {'node_ids': [log_lv], **G})
                check(F, 'exposing an input logs the documented harmless messages',
                      all(b > a for a, b in zip(before, after)), 'counts before %s, after %s' % (before, after))
                # widget capture can't see the GPU-drawn 3D render: a grab of its viewport (leftover
                # content that changes from call to call) is clearly unlike the view's own render
                grab_png = os.path.join(scratch, 'grab3d.png')
                t = text(await c('execute_designer_code', {'code': (
                    "import sd\nfrom PySide6.QtWidgets import QDockWidget, QWidget\n"
                    "mw=sd.getContext().getSDApplication().getQtForPythonUIMgr().getMainWindow()\n"
                    "d=[d for d in mw.findChildren(QDockWidget) if d.objectName().startswith('areaD_') and d.isVisible()]\n"
                    "vp=[w for w in d[0].findChildren(QWidget) if w.metaObject().className()=='Alg::Gui3D::ViewportWidget'] if d else []\n"
                    "print('NO_3D_VIEW' if not vp else 'SAVED=%%s' %% vp[0].grab().save(%r))") % grab_png}))
                render = await c('screenshot_designer', {'panel': '3d', 'max_size': 128})
                if 'NO_3D_VIEW' in t or not is_image(render):
                    skip(F, 'widget capture of the 3D view is not the render', 'no 3D View visible in Designer')
                else:
                    import numpy as np
                    from PIL import Image as PILImage
                    import io as _io
                    shot = PILImage.open(_io.BytesIO(base64.b64decode(next(x for x in render.content if x.type == 'image').data)))
                    size = (64, 40)
                    a_ = np.asarray(shot.convert('L').resize(size), dtype=float)
                    b_ = np.asarray(PILImage.open(grab_png).convert('L').resize(size), dtype=float)
                    diff = float(np.abs(a_ - b_).mean())
                    check(F, 'widget capture of the 3D view is not the render', diff > 20,
                          'mean difference %.1f of 255 between the grab and the render' % diff)
                t = text(await c('execute_designer_code', {'code': GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdresourcebitmap import SDResourceBitmap\nfrom sd.api.sdresource import EmbedMethod\n"
                    "from sd.api.apiexception import APIException\n"
                    "try:\n    SDResourceBitmap.sNewFromFile(g.getPackage(), %r, EmbedMethod.BinaryEmbedded); print('EMBED=ok')\n"
                    "except APIException as e:\n    print('EMBED=' + str(e))\n"
                    "from sd.api.sdbasetypes import int2\nsaved=g.getDefaultParentSize()\n"
                    "g.setDefaultParentSize(int2(256, 256)); print('PARENT=%%d' %% g.getDefaultParentSize().x)\n"
                    "g.setDefaultParentSize(saved)") % png}))
                check(F, 'bitmaps cannot be embedded (NotSupported)', 'EMBED=SDApiError.NotSupported' in t, t)
                check(F, 'setDefaultParentSize takes pixels, not log2', 'PARENT=256' in t, t)
                grad = added_id(text(await c('add_node', {'definition': 'gradient_linear_1', 'position': [-600, 600], **G})))
                nrm = added_id(text(await c('add_node', {'definition': 'normal', 'position': [-400, 600],
                                                         'params': {'intensity': 5.0, 'inversedy': True}, **G})))
                await c('connect', {'from_node': grad, 'to_node': nrm, 'to_input': 'input1', **G})
                px = pixel_values(text(await c('node_stats', {'node_id': grad, 'points': [[0, 0], [511, 0], [0, 511], [300, 511]], **G})))
                check(F, 'gradient_linear_1: 1 at top, 0 at bottom', min(px[(0, 0)][0], px[(511, 0)][0]) > 0.99
                      and max(px[(0, 511)][0], px[(300, 511)][0]) < 0.01, str(px))
                # height rises towards the top: OpenGL (Y up) normals lean down there, so green < 0.5
                gl = pixel_values(text(await c('node_stats', {'node_id': nrm, 'points': [[256, 256]], **G})))[(256, 256)]
                await c('set_params', {'node_id': nrm, 'params': {'inversedy': False}, **G})
                dx = pixel_values(text(await c('node_stats', {'node_id': nrm, 'points': [[256, 256]], **G})))[(256, 256)]
                # a full-height ramp is a gentle slope (G about 0.49 vs 0.51); the sign is what matters
                check(F, 'normal inversedy=True is OpenGL', gl[1] < 0.497 and dx[1] > 0.503 and abs(gl[1] + dx[1] - 1) < 0.002,
                      'OpenGL G=%.3f, DirectX G=%.3f' % (gl[1], dx[1]))
                await c('delete_nodes', {'node_ids': [grad, nrm], **G})

                # --- graph lookup: same-named graphs are ambiguous; loaded library graphs aren't yours
                await c('execute_designer_code', {'code': (
                    "import sd\nfrom sd.api.sbs.sdsbscompgraph import SDSBSCompGraph\n"
                    "pm=sd.getContext().getSDApplication().getPackageMgr()\n"
                    "for _ in range(2):\n    SDSBSCompGraph.sNew(pm.newUserPackage()).setIdentifier('%s')") % DUP_GRAPH})
                r_ = await c('describe_graph', {'graph': DUP_GRAPH})
                check('describe_graph', 'error on two graphs with one name', r_.is_error and '2 open graphs are named' in text(r_), text(r_))
                r_ = await c('describe_graph', {'graph': 'bevel'})        # bevel.sbs is loaded by now (describe_node)
                check('describe_graph', 'library graphs are not user graphs', r_.is_error and 'not found' in text(r_), text(r_))

                # --- a node with several outputs (bevel: height, normal)
                bev = added_id(text(await c('add_node', {'definition': 'bevel', 'position': [-400, 300], **G})))
                await c('connect', {'from_node': clouds, 'to_node': bev, 'to_input': 'input', **G})
                lvn = added_id(text(await c('add_node', {'definition': 'levels', 'position': [-200, 300], **G})))
                t = text(await c('connect', {'from_node': bev, 'to_node': lvn, 'to_input': 'input1', 'from_output': 'normal', **G}))
                t2 = text(await c('describe_graph', {'node_ids': [lvn], **G}))
                check('connect', 'from_output picks the output', 'input1<-%s.normal' % bev in t2, t2)
                r_ = await c('preview_node', {'node_id': bev, 'output': 'normal', 'max_size': 128, **G})
                check('preview_node', 'output + max_size', is_image(r_) and max(image_size(r_)) <= 128,
                      str(image_size(r_)) if is_image(r_) else text(r_))
                t = text(await c('node_stats', {'node_id': bev, 'output': 'normal', **G}))
                check('node_stats', 'output picks the output', '%s instance:bevel.normal' % bev in t and 'B:' in t, t.splitlines()[0])
                t = text(await c('check_tiling', {'node_id': bev, 'output': 'height', 'axis': 'horizontal', **G}))
                check('check_tiling', 'output + one axis', '.height' in t and 'Horizontal' in t and 'Vertical' not in t, t)
                r_ = await c('sweep_param', {'node_id': clouds, 'param': 'scale', 'values': [2, 8], 'view_node': bev,
                                             'output': 'normal', 'tile_size': 64, **G})
                t = text(r_)
                check('sweep_param', 'view_node + output', 'restored %s.scale' % clouds in t and t.count('scale = ') == 2
                      and any(x.type == 'image' for x in r_.content), t)
                per_value = [l.split(': ', 1)[1] for l in t.splitlines() if l.startswith('scale = ')]
                check('sweep_param', 'a node feeding no output is recomputed per value',
                      len(per_value) == 2 and per_value[0] != per_value[1], str(per_value))
                r_ = await c('compare_to_reference', {'node_id': bev, 'output': 'normal', 'reference_path': png,
                                                      'reference_region': [0, 0, 32, 16], 'tile_size': 128, **G})
                t = text(r_)
                check('compare_to_reference', 'output + reference_region', '.normal' in t.splitlines()[0]
                      and '(32x16)' in t.splitlines()[0], t.splitlines()[0])
                await c('delete_nodes', {'node_ids': [bev, lvn], **G})

                # --- editor + screenshots
                t = text(await c('open_graph', {'graph': TEST_GRAPH, 'node_id': slope}))
                check('open_graph', 'open + focus', 'focused node' in t, t)
                r_ = await c('open_graph', {'graph': 'no_such_graph'})
                check('open_graph', 'error on unknown graph', r_.is_error and 'not found' in text(r_), '')

                def visible(t):
                    m = re.search(r'zoom (\d+)%, visible (-?\d+),(-?\d+) to (-?\d+),(-?\d+)', t)
                    return (int(m.group(1)), [int(v) for v in m.groups()[1:]]) if m else (None, None)

                def contains(box, points):
                    return box is not None and bool(points) and all(
                        box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in points)

                t = text(await c('execute_designer_code', {'code': GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdgraphobjectframe import SDGraphObjectFrame\n"
                    "f=[o for o in g.getGraphObjects() if isinstance(o, SDGraphObjectFrame) and o.getTitle()=='Shape'][0]\n"
                    "p,s=f.getPosition(),f.getSize()\nprint('FRAME=%d,%d,%d,%d' % (p.x, p.y, p.x+s.x, p.y+s.y))")}))
                fx0, fy0, fx1, fy1 = [int(v) for v in re.search(r'FRAME=(-?\d+),(-?\d+),(-?\d+),(-?\d+)', t).groups()]
                t = text(await c('open_graph', {'graph': TEST_GRAPH, 'frame': 'shape'}))   # title, any case
                zoom, box = visible(t)
                check('open_graph', 'frame fits in view', "fitted frame 'Shape'" in t and zoom is not None
                      and zoom <= 100 and contains(box, [(fx0, fy0), (fx1, fy1)]), t)
                shape_nodes = [clouds, slope]
                points = [(float(x), float(y)) for x, y in re.findall(
                    r'^\d+ \S+ @\((-?[\d.]+),(-?[\d.]+)\)', text(await c('describe_graph', {'node_ids': shape_nodes, **G})), re.M)]
                t = text(await c('open_graph', {'graph': TEST_GRAPH, 'node_ids': shape_nodes}))
                zoom, box = visible(t)
                check('open_graph', 'node_ids fit their bounding box', 'fitted 2 node(s)' in t and len(points) == 2
                      and contains(box, points), t)
                t = text(await c('open_graph', {'graph': TEST_GRAPH, 'rect': [0, 0, 10, 10]}))
                zoom, box = visible(t)
                check('open_graph', 'rect, zoom capped at 100%', zoom is not None and 100 / 1.2 <= zoom <= 100
                      and contains(box, [(0, 0), (10, 10)]), t)
                # the fit zooms through Designer's own wheel handling, so the user's next wheel step
                # continues from the fitted zoom (setting the view's transform directly made it jump)
                t = text(await c('execute_designer_code', {'code': (
                    "import sd\nfrom PySide6.QtWidgets import QApplication, QGraphicsView, QDockWidget\n"
                    "from PySide6.QtGui import QWheelEvent\nfrom PySide6.QtCore import QPoint, QPointF, Qt\n"
                    "mw=sd.getContext().getSDApplication().getQtForPythonUIMgr().getMainWindow()\n"
                    "d=[w for w in mw.findChildren(QDockWidget) if w.objectName().startswith('areaB_') and w.isVisible()][0]\n"
                    "v=max((x for x in d.findChildren(QGraphicsView) if x.isVisible()), key=lambda x: x.width()*x.height())\n"
                    "vp=v.viewport(); c=QPointF(vp.width()/2, vp.height()/2); before=v.transform().m11()\n"
                    "QApplication.sendEvent(vp, QWheelEvent(c, QPointF(vp.mapToGlobal(c.toPoint())), QPoint(0,0), QPoint(0,120), "
                    "Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False))\n"
                    "QApplication.processEvents(); print('STEP=%.4f' % (v.transform().m11() / before))")}))
                step = re.search(r'STEP=([\d.]+)', t)
                check('open_graph', 'a wheel step after a fit continues from the fitted zoom',
                      step is not None and abs(float(step.group(1)) - 1.2) < 0.01, t.strip())
                r_ = await c('open_graph', {'graph': TEST_GRAPH, 'node_id': slope, 'frame': 'Shape'})
                check('open_graph', 'refuses two view targets at once', r_.is_error
                      and 'choose one of' in text(r_) and 'node_id, frame' in text(r_), text(r_))
                r_ = await c('open_graph', {'graph': TEST_GRAPH, 'node_ids': ['graph']})
                check('open_graph', "node_ids never means the graph itself", r_.is_error
                      and "node 'graph' not found" in text(r_), text(r_))
                r_ = await c('open_graph', {'graph': TEST_GRAPH, 'frame': 'no such frame'})
                check('open_graph', 'error on unknown frame lists the frames', r_.is_error and "'Shape'" in text(r_), text(r_))
                # 'graph' captures the node view alone (no title bar, no toolbars); crop takes a part of it
                full = await c('screenshot_designer', {'panel': 'graph', 'max_size': 4000})
                t = text(await c('execute_designer_code', {'code': (
                    "from PySide6.QtWidgets import QApplication, QGraphicsView, QDockWidget\n"
                    "d=[w for w in QApplication.instance().allWidgets() if isinstance(w, QDockWidget) "
                    "and w.objectName().startswith('areaB_') and w.isVisible()][0]\n"
                    "v=max((x for x in d.findChildren(QGraphicsView) if x.isVisible()), key=lambda x: x.width()*x.height())\n"
                    "r=v.devicePixelRatioF()\nprint('VIEW=%d,%d DOCK=%d,%d' % (round(v.width()*r), round(v.height()*r), "
                    "round(d.width()*r), round(d.height()*r)))")}))
                sizes = re.search(r'VIEW=(\d+),(\d+) DOCK=(\d+),(\d+)', t)
                view_size = (int(sizes.group(1)), int(sizes.group(2))) if sizes else None
                check('screenshot_designer', 'graph is the node view, without toolbars', is_image(full) and sizes
                      and image_size(full) == view_size and int(sizes.group(4)) > view_size[1],
                      '%s vs %s' % (image_size(full) if is_image(full) else text(full), t.strip()))
                part = await c('screenshot_designer', {'panel': 'graph', 'max_size': 4000, 'crop': [0, 0, 0.5, 0.25]})
                check('screenshot_designer', 'crop', is_image(part) and view_size is not None and image_size(part) == (
                    round(view_size[0] * 0.5), round(view_size[1] * 0.25)), str(image_size(part)) if is_image(part) else text(part))
                r_ = await c('screenshot_designer', {'panel': 'graph', 'crop': [0, 0, 0.0001, 1]})
                check('screenshot_designer', 'error on a crop under a pixel', r_.is_error
                      and 'less than a pixel' in text(r_), text(r_))
                r_ = await c('screenshot_designer', {'panel': 'graph', 'crop': [0.5, 0, 0.2, 1]})
                check('screenshot_designer', 'error on a bad crop', r_.is_error and 'left < right' in text(r_), text(r_))

                # --- one tool call = one undo step (only acts while the self-test graph is in the editor)
                ub = added_id(text(await c('add_node', {'definition': 'blur', 'position': [0, 400], **G})))
                t = text(await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Undo')}))
                if 'SCHEDULED' not in t:
                    skip('add_node', 'one undo step', 'self-test graph not in focus or Undo unavailable (%s)' % t.strip())
                else:
                    gone = 'EXISTS=False' in text(await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, ub)}))
                    if not gone:
                        # Undo hit some other step: put it back at once
                        await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Redo')})
                        await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, ub)})
                    check('add_node', 'one Undo removes the added node', gone, '')
                    if gone:
                        await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Redo')})
                        back = 'EXISTS=True' in text(await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, ub)}))
                        check('add_node', 'Redo restores it', back, '')
                await c('delete_nodes', {'node_ids': [ub], **G})
                t = text(await c('execute_designer_code', {'undo_label': 'self-test: two nodes', 'code': (
                    "import sd\nfrom sd.api.sdbasetypes import float2\n"
                    "g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() "
                    "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\nids=[]\n"
                    "for i in range(2):\n    n=g.newNode('sbs::compositing::blur'); n.setPosition(float2(200*i, 500)); ids.append(n.getIdentifier())\n"
                    "print('IDS=' + ','.join(ids))") % TEST_GRAPH}))
                two = re.search(r'IDS=(\d+),(\d+)', t).groups()
                t = text(await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Undo')}))
                if 'SCHEDULED' not in t:
                    skip('execute_designer_code', 'one undo step', 'self-test graph not in focus or Undo unavailable')
                else:
                    states = [('EXISTS=True' in text(await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, i)}))) for i in two]
                    if any(states):
                        await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Redo')})
                    check('execute_designer_code', 'one Undo reverts the whole run', not any(states), str(states))
                    if not any(states):
                        await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, 'Redo')})
                        states = [('EXISTS=True' in text(await c('execute_designer_code', {'code': NODE_EXISTS % (TEST_GRAPH, i)}))) for i in two]
                        check('execute_designer_code', 'one Redo restores it', all(states), str(states))
                await c('delete_nodes', {'node_ids': list(two), **G})
                if not was_running:
                    # our own instance, so its layout doesn't matter: show the console (hidden by default)
                    await c('execute_designer_code', {'code': (
                        "from PySide6.QtWidgets import QApplication, QMenu\n"
                        "for w in QApplication.instance().allWidgets():\n"
                        "    if isinstance(w, QMenu) and w.title() == '&Windows':\n"
                        "        w.aboutToShow.emit()\n"
                        "        for a in w.actions():\n"
                        "            if a.text() == 'Console' and not a.isChecked(): a.trigger()\n"
                        "        break\nQApplication.processEvents()")})
                for panel in ('window', 'graph', '2d', 'parameters', 'explorer', 'library', 'console'):
                    r_ = await c('screenshot_designer', {'panel': panel, 'max_size': 700})
                    if not is_image(r_) and 'not visible' in text(r_):
                        skip('screenshot_designer', panel, 'panel not visible in Designer')
                    else:
                        check('screenshot_designer', panel, is_image(r_), '' if is_image(r_) else text(r_))
                before = clipboard_fingerprint()
                r_ = await c('screenshot_designer', {'panel': '3d', 'max_size': 700})
                if not is_image(r_) and 'not visible' in text(r_):
                    skip('screenshot_designer', '3d', 'no 3D View visible in Designer')
                else:
                    same = before is None or clipboard_fingerprint() == before
                    if not same:
                        # the user may have copied something meanwhile: measure again around a second capture
                        before = clipboard_fingerprint()
                        r_ = await c('screenshot_designer', {'panel': '3d', 'max_size': 700})
                        same = clipboard_fingerprint() == before
                    check('screenshot_designer', '3d' + (' + clipboard kept' if before else ''), is_image(r_) and same,
                          '' if is_image(r_) else text(r_))
                # the 3D capture backs up the clipboard from mimeData(): an empty clipboard still gives
                # an (empty) object, not None (REVIEW.md HLP-8). This clears the system clipboard and
                # restores it as the capture does, so it runs only where the clipboard can be
                # compared before and after (macOS), and fails if it didn't come back (REVIEW.md TST-14)
                if clipboard_fingerprint() is None:
                    skip('designer facts', 'an empty clipboard has mimeData (no formats), not None',
                         'the clipboard can only be compared before and after on macOS')
                else:
                    before = clipboard_fingerprint()
                    t = text(await c('execute_designer_code', {'code': (
                        "from PySide6 import QtCore, QtWidgets\napp = QtWidgets.QApplication.instance()\ncb = app.clipboard()\n"
                        "orig = cb.mimeData()\nbackup = QtCore.QMimeData()\n"
                        "for f in orig.formats():\n    backup.setData(f, orig.data(f))\n"
                        "try:\n    cb.clear()\n    app.processEvents()\n    m = cb.mimeData()\n"
                        "    print('EMPTY_MIME=%s' % ('None' if m is None else len(m.formats())))\n"
                        "finally:\n    cb.setMimeData(backup)\n    app.processEvents()")}))
                    kept = clipboard_fingerprint() == before
                    check('designer facts', 'an empty clipboard has mimeData (no formats), not None; clipboard kept',
                          'EMPTY_MIME=0' in t and kept, t.strip() + ('' if kept else ' | the clipboard did not come back'))
                r_ = await c('screenshot_designer', {'panel': 'foo'})
                check('screenshot_designer', 'error on bad panel', r_.is_error and "unknown panel 'foo'" in text(r_), text(r_))

                # --- save / export / render
                sbs = os.path.join(scratch, TEST_GRAPH + '.sbs')
                t = text(await c('save_package', {'graph_or_path': TEST_GRAPH, 'save_as': sbs}))
                check('save_package', 'save as', os.path.exists(sbs), t)
                r_ = await c('save_package', {'graph_or_path': TEST_GRAPH})
                t = text(r_)
                check('save_package', 'save in place', not r_.is_error and 'saved %s' % sbs in t, t)
                t = text(await c('save_package', {'graph_or_path': sbs}))
                check('save_package', 'by file path', 'saved %s' % sbs in t, t)
                state = GRAPH_OF % TEST_GRAPH + "p=g.getPackage()\nprint('STATE=%s %s' % (p.getFilePath(), p.isModified()))"
                before = text(await c('execute_designer_code', {'code': state}))
                await c('snapshot_graph', {'label': 'state check', **G})
                after = text(await c('execute_designer_code', {'code': state}))
                check('snapshot_graph', "leaves the package's file and saved state alone",
                      'STATE=%s False' % sbs in before and before == after, before + after)
                xs = positions(text(await c('describe_graph', G)))
                await c('move_nodes', {'positions': {clouds: [xs[clouds][0] + 50, xs[clouds][1]]}, **G})
                t = text(await c('diff_graph', {'against': sbs, 'show_positions': True, **G}))
                check('diff_graph', 'against a .sbs path, with positions', '1 node(s) moved' in t
                      and '~ node %s' % clouds in t and 'moved' in t, t)
                await c('move_nodes', {'positions': {clouds: list(xs[clouds])}, **G})
                t = text(await c('import_bitmap', {'path': png, 'embed': 'copy', 'name': 'selftest_copy', **G}))
                copied = re.search(r'selftest_copy \(copy\): (.*)', t)
                check('import_bitmap', 'copy into <package>.resources, named', copied is not None and os.path.isfile(copied.group(1))
                      and os.path.dirname(copied.group(1)) == os.path.join(scratch, TEST_GRAPH + '.resources')
                      and os.path.basename(copied.group(1)).startswith('XXXXXX-'), t)
                copied_node = added_id(t)
                # a snapshot keeps copied bitmaps reachable (REVIEW.md SRV-3): every bitmap file the
                # snapshot's .sbs points to exists, relative to the snapshot or absolute
                snap = text(await c('snapshot_graph', {'label': 'with copied bitmap', **G})).split('saved: ', 1)[1].strip()
                import xml.etree.ElementTree as ET
                refs = [f.get('v') for r in ET.parse(snap).getroot().iter('resource')
                        if r.find('filepath') is not None for f in [r.find('filepath')]]
                missing = [r for r in refs if not os.path.isfile(os.path.join(os.path.dirname(snap), r))]
                check('snapshot_graph', 'copied bitmaps stay reachable', any('selftest_copy' in r or 'XXXXXX-' in r for r in refs)
                      and not missing, 'refs %s, missing %s' % (refs, missing))
                await c('delete_nodes', {'node_ids': [copied_node], **G})
                stats_before = text(await c('node_stats', {'node_id': lv, **G}))
                # the reload behind set_link_display never unloads a package with unsaved changes
                # (REVIEW.md SRV-4): a saved package, then an edit, then the helper's unload
                with open(os.path.join(BUNDLE, 'mcp_server', 'designer_helpers.py'), encoding='utf-8') as f:
                    helpers = f.read()
                unsaved_sbs = os.path.join(scratch, 'unsaved_check.sbs')
                t = text(await c('execute_designer_code', {'code': helpers + (
                    "\nfrom sd.api.sbs.sdsbscompgraph import SDSBSCompGraph\n"
                    "pkg = _PM.newUserPackage()\ng = SDSBSCompGraph.sNew(pkg)\ng.setIdentifier('mcp_selftest_unsaved')\n"
                    "_PM.savePackageAs(pkg, %r)\ng.newNode('sbs::compositing::blur')\n"
                    "try:\n    unload_package_file(%r)\nexcept RuntimeError as e:\n    print('REFUSED', e)\n"
                    "still = [p for p in _PM.getUserPackages() if (p.getFilePath() or '') == %r]\n"
                    "print('STILL_OPEN=%%d' %% len(still))\n"
                    "for p in still:\n    _PM.unloadUserPackage(p)\n") % (unsaved_sbs, unsaved_sbs, unsaved_sbs)}))
                check('set_link_display', 'never unloads unsaved changes', 'REFUSED' in t and 'unsaved' in t
                      and 'STILL_OPEN=1' in t, t.strip()[-200:])
                # several ids: a bad one changes nothing, not even the ones before it (REVIEW.md HLP-4)
                spare = added_id(text(await c('add_node', {'definition': 'blur', 'position': [900, 900], **G})))
                r_ = await c('delete_nodes', {'node_ids': [spare, 'no_such_node'], **G})
                t = text(await c('describe_graph', {'node_ids': [spare], **G}))
                check('delete_nodes', 'a bad id deletes nothing', r_.is_error and '%s blur @(900,900)' % spare in t, t[-120:])
                r_ = await c('move_nodes', {'positions': {spare: [100, 100], 'no_such_node': [0, 0]}, **G})
                t = text(await c('describe_graph', {'node_ids': [spare], **G}))
                check('move_nodes', 'a bad id moves nothing', r_.is_error and '@(900,900)' in t, t[-120:])
                await c('delete_nodes', {'node_ids': [spare], **G})
                # a failed restore in sweep_param still restores the inheritance and keeps the first
                # error (REVIEW.md HLP-7): setPropertyValue made to fail when it puts the original back
                t = text(await c('execute_designer_code', {'code': helpers + (
                    "\nfrom sd.api.sdnode import SDNode\nfrom sd.api.sdproperty import SDPropertyInheritanceMethod\n"
                    "g = find_graph(%r); n = g.getNodeFromId(%r)\np = n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
                    "before = n.getPropertyInheritanceMethod(p).name; orig = n.getPropertyValue(p).get()\n"
                    "real = SDNode.setPropertyValue\n"
                    "def failing(self, prop, value):\n"
                    "    v = value.get()\n"
                    "    if prop.getId() == '$outputsize' and (v.x, v.y) == (orig.x, orig.y):\n"
                    "        raise RuntimeError('restore failed on purpose')\n"
                    "    return real(self, prop, value)\n"
                    "SDNode.setPropertyValue = failing\n"
                    "try:\n    sweep_param(%r, %r, '$outputsize', [[10, 10]], %r, None, None)\n"
                    "except Exception as e:\n    print('ERROR=' + str(e))\n"
                    "finally:\n    SDNode.setPropertyValue = real\n"
                    "    real(n, p, n.getPropertyValue(p).__class__.sNew(orig))\n"
                    "print('INHERIT before=%%s after=%%s' %% (before, n.getPropertyInheritanceMethod(p).name))\n"
                    "n.setPropertyInheritanceMethod(p, getattr(SDPropertyInheritanceMethod, before))") % (
                        TEST_GRAPH, lv, TEST_GRAPH, lv, os.path.join(scratch, 'sweep_restore'))}))
                inh = re.search(r'INHERIT before=(\w+) after=(\w+)', t)
                check('sweep_param', 'a failed restore still restores the inheritance', 'restore failed on purpose' in t
                      and inh is not None and inh.group(1) == inh.group(2), t.strip()[-200:])
                # and the other way round: the inheritance goes back first (HLP-26), so when that fails the
                # value must still come back (REVIEW.md TST-41); a relative size with offset 1 to tell
                t = text(await c('execute_designer_code', {'code': helpers + (
                    "\nfrom sd.api.sdnode import SDNode\nfrom sd.api.sdproperty import SDPropertyInheritanceMethod as IM\n"
                    "from sd.api.sdvalueint2 import SDValueInt2\nfrom sd.api.sdbasetypes import int2\n"
                    "g = find_graph(%r); n = g.getNodeFromId(%r)\np = n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
                    "before = n.getPropertyInheritanceMethod(p)\n"
                    "n.setPropertyInheritanceMethod(p, IM.RelativeToParent); n.setPropertyValue(p, SDValueInt2.sNew(int2(1, 1)))\n"
                    "owner = next(k for k in type(n).__mro__ if 'setPropertyInheritanceMethod' in k.__dict__)\n"
                    "real = owner.setPropertyInheritanceMethod\n"
                    "def failing(self, prop, method):\n"
                    "    if prop.getId() == '$outputsize' and method == IM.RelativeToParent:\n"
                    "        raise RuntimeError('inheritance restore failed on purpose')\n"
                    "    return real(self, prop, method)\n"
                    "owner.setPropertyInheritanceMethod = failing\n"
                    "try:\n    sweep_param(%r, %r, '$outputsize', [[10, 10]], %r, None, None)\n"
                    "except Exception as e:\n    print('ERROR=' + str(e))\n"
                    "finally:\n    owner.setPropertyInheritanceMethod = real\n"
                    "    v = n.getPropertyValue(p).get(); print('VALUE=%%d,%%d' %% (v.x, v.y))\n"
                    "    n.setPropertyInheritanceMethod(p, before)\n"
                    "    n.setPropertyValue(p, SDValueInt2.sNew(int2(0, 0)))") % (
                        TEST_GRAPH, lv, TEST_GRAPH, lv, os.path.join(scratch, 'sweep_restore2'))}))
                check('sweep_param', 'a failed inheritance restore still puts the value back',
                      'inheritance restore failed on purpose' in t and 'VALUE=1,1' in t, t.strip()[-200:])
                # a Designer library package is never chosen for saving (REVIEW.md HLP-10): by its path,
                # or as the graph in the editor; nothing is saved here, only the lookup is asked
                t = text(await c('execute_designer_code', {'code': helpers + (
                    "\nlib = next(p for p in _PM.getUserPackages() if _is_library_package(p))\n"
                    "for how in ('path', 'editor'):\n"
                    "    try:\n"
                    "        if how == 'path':\n            pkg, _ = _package_of(lib.getFilePath())\n"
                    "        else:\n            _current_graph = lambda: lib.getChildrenResources(False)[0]\n"
                    "            pkg, _ = _package_of(None)\n"
                    "        print(how.upper() + '=CHOSEN' if _is_library_package(pkg) else how.upper() + '=OTHER')\n"
                    "    except RuntimeError as e:\n        print(how.upper() + '=REFUSED', e)\n")}))
                check('save_package', 'never picks a Designer library package', 'PATH=REFUSED' in t and 'EDITOR=REFUSED' in t,
                      t.strip()[-200:])
                # and the refusal doesn't suggest save_as, which is refused too (REVIEW.md HLP-14), and
                # says to open the graph first, since snapshot_graph can't find a library graph by
                # name (HLP-18)
                check('save_package', 'the library refusal points to a way that works',
                      'save_as' not in t and 'open it in the editor' in t and 'snapshot_graph with no graph' in t,
                      t.strip()[-200:])
                # ...and that way works: a library graph open in the editor, snapshot_graph with no graph
                # (REVIEW.md HLP-20). Only in a Designer the self-test started: there is no API to close
                # the library graph's tab again, so it isn't left in yours (TST-27)
                if was_running:
                    skip('snapshot_graph', 'snapshots a library graph open in the editor, with no graph given',
                         'it opens a library graph in an editor tab, which can\'t be closed again from code')
                else:
                    t = text(await c('execute_designer_code', {'code': helpers + (
                        "\nlib = next(p for p in _PM.getUserPackages() if _is_library_package(p))\n"
                        "lg = next(r for r in lib.getChildrenResources(False) if isinstance(r, SDSBSCompGraph))\n"
                        "_APP.getUIMgr().openResourceInEditor(lg)\n_process_events()\n"
                        "print('LIBRARY_GRAPH=' + lg.getIdentifier())")}))
                    lib_graph = re.search(r'LIBRARY_GRAPH=(\S+)', t)
                    r_ = await c('snapshot_graph', {'label': 'library graph check'})
                    check('snapshot_graph', 'snapshots a library graph open in the editor, with no graph given',
                          lib_graph is not None and not r_.is_error and 'saved: ' in text(r_), text(r_).strip()[-150:])
                    # delete only this snapshot, and its folder only if nothing else is in it: the user may
                    # have snapshots of a graph with the same name (REVIEW.md TST-26)
                    if not r_.is_error and 'saved: ' in text(r_):
                        lib_snap = text(r_).split('saved: ', 1)[1].strip().splitlines()[0]
                        if os.path.isfile(lib_snap):
                            os.remove(lib_snap)
                        if os.path.isdir(os.path.dirname(lib_snap)) and not os.listdir(os.path.dirname(lib_snap)):
                            os.rmdir(os.path.dirname(lib_snap))
                    await c('open_graph', G)
                # two open graphs with one name, in different packages: each helper must act on the graph
                # it was given, not on any graph with that name (REVIEW.md HLP-6)
                dup_a, dup_b = os.path.join(scratch, 'dup_a.sbs'), os.path.join(scratch, 'dup_b.sbs')
                t = text(await c('execute_designer_code', {'code': helpers + (
                    "\nfrom sd.api.sbs.sdsbscompgraph import SDSBSCompGraph\n"
                    "made = []\n"
                    "for path in (%r, %r):\n"
                    "    pkg = _PM.newUserPackage()\n    g = SDSBSCompGraph.sNew(pkg)\n"
                    "    g.setIdentifier('mcp_selftest_dup')\n    n = g.newNode('sbs::compositing::blur')\n"
                    "    _PM.savePackageAs(pkg, path)\n    made.append((pkg, g, n))\n"
                    "    _APP.getUIMgr().openResourceInEditor(g)\n    _process_events()\n"
                    "(pa, ga, na), (pb, gb, nb) = made\n"
                    "package_file_of(ga)\n"                     # B is in the editor, A isn't
                    "open_graph(ga, node_id=na.getIdentifier())\n"
                    "open_graph(gb, node_id=nb.getIdentifier())\n"
                    "cur = _current_graph()\n"
                    "print('FOCUS_B=%%s' %% (cur.getPackage().getUID() == pb.getUID()))\n") % (dup_a, dup_b)}))
                # unloaded in a separate call, after Designer's event loop has run: both were open in
                # editor views, and an unload in the same call as the opening risks a crash (AGENTS.md,
                # Portals; after an unload in one call, Designer crashed once as the test ended, PLG-9)
                time.sleep(0.5)
                await c('execute_designer_code', {'code': (
                    "import sd\npm = sd.getContext().getSDApplication().getPackageMgr()\n"
                    "for p in list(pm.getUserPackages()):\n"
                    "    if (p.getFilePath() or '') in (%r, %r):\n        pm.unloadUserPackage(p)\n") % (dup_a, dup_b)})
                found = ' | '.join(l for l in t.splitlines() if l.startswith(('OPEN=', 'FOCUS_B=', 'sd.api.')))
                check('open_graph', 'two graphs with one name: the given one is focused', 'FOCUS_B=True' in t, found)
                check('set_link_display', 'two graphs with one name: only the one in the editor counts as open',
                      'OPEN=0' in t, found)
                r_ = await c('set_link_display', {'mode': 'dotted', 'from_nodes': [clouds], **G})
                check('set_link_display', 'error on bad mode', r_.is_error and "mode must be" in text(r_), text(r_))
                r_ = await c('set_link_display', {'mode': 'portal', **G})
                check('set_link_display', 'error without a selection', r_.is_error and 'choose links' in text(r_), text(r_))
                t = text(await c('set_link_display', {'mode': 'portal', 'from_nodes': [clouds], **G}))
                check('set_link_display', 'portals from a node', 'changed to portal' in t and 'reloaded' in t, t.split(';')[0])
                t = text(await c('diff_graph', {'against': 'latest', **G}))
                check('set_link_display', 'diff shows display only', 'shown as portal' in t and '0 added, 0 removed' in t, t.splitlines()[0])
                stats_after = text(await c('node_stats', {'node_id': lv, **G}))
                check('set_link_display', 'output unchanged', stats_after == stats_before, stats_after)
                snap_dir = os.path.join(os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(
                    os.path.expanduser('~'), '.sd_mcp', 'snapshots'), TEST_GRAPH)
                check('set_link_display', 'copies the saved file before saving over it',
                      any(f.endswith('before_portals_file_on_disk.sbs') for f in os.listdir(snap_dir)), str(os.listdir(snap_dir)))
                # and that copy's bitmap paths still lead to the files (REVIEW.md SRV-14)
                on_disk = [os.path.join(snap_dir, f) for f in os.listdir(snap_dir) if f.endswith('before_portals_file_on_disk.sbs')]
                refs = [f.get('v') for f in ET.parse(on_disk[0]).getroot().iter('filepath')] if on_disk else []
                missing = [r for r in refs if not os.path.isfile(os.path.join(snap_dir, r))]
                check('set_link_display', "the saved file's copy keeps its bitmaps reachable", refs and not missing,
                      'refs %s, missing %s' % (refs, missing))
                t = text(await c('set_link_display', {'mode': 'wire', 'from_nodes': [clouds], **G}))
                check('set_link_display', 'back to wires', 'changed to wire' in t, t.split(';')[0])
                t = text(await c('set_link_display', {'mode': 'wire', 'from_nodes': [clouds], **G}))
                check('set_link_display', 'nothing to change: no save, no reload', 'nothing to do' in t, t)
                # automatic selection, as AGENTS.md recommends: clouds feeds 3 inputs once this blend is in
                tb = added_id(text(await c('add_node', {'definition': 'blend', 'position': [-400, -300], **G})))
                for port in ('source', 'destination'):
                    await c('connect', {'from_node': clouds, 'to_node': tb, 'to_input': port, **G})
                t = text(await c('set_link_display', {'mode': 'portal', 'fanout_at_least': 3, **G}))
                check('set_link_display', 'fanout_at_least=3 to portals', '3 of 3 selected link(s) changed to portal' in t, t.split(';')[0])
                t = text(await c('set_link_display', {'mode': 'wire', 'fanout_at_least': 3, **G}))
                check('set_link_display', 'fanout_at_least=3 back to wires', '3 of 3 selected link(s) changed to wire' in t, t.split(';')[0])
                t = text(await c('set_link_display', {'mode': 'portal', 'links': [[lv, 'input1']], **G}))
                check('set_link_display', 'links=[[node, input]] to portal', '1 of 1 selected link(s) changed to portal' in t, t.split(';')[0])
                t = text(await c('set_link_display', {'mode': 'wire', 'links': [[lv, 'input1']], **G}))
                check('set_link_display', 'links=[[node, input]] back to wire', '1 of 1 selected link(s) changed to wire' in t, t.split(';')[0])
                t = text(await c('set_link_display', {'mode': 'portal', 'longer_than': 1, **G}))
                counts = re.search(r'(\d+) of (\d+) selected link\(s\) changed to portal in \S+ \(of (\d+) links', t)
                check('set_link_display', 'longer_than=1 picks every link', counts is not None
                      and counts.group(1) == counts.group(2) == counts.group(3), t.split(';')[0])
                await c('set_link_display', {'mode': 'wire', 'longer_than': 1, **G})
                await c('delete_nodes', {'node_ids': [tb], **G})
                t = text(await c('export_outputs', {'graph': TEST_GRAPH, 'output_dir': os.path.join(scratch, 'export')}))
                check('export_outputs', 'from Designer', 'height.png  512x512' in t, t)
                t = text(await c('sbsar_info', {'sbs_path': sbs}))
                check('sbsar_info', 'graph + output', 'pkg://%s' % TEST_GRAPH in t and 'OUTPUT height' in t, t.splitlines()[0])
                # the graph seed set with set_params is still a control of the cooked graph (REVIEW.md HLP-25)
                check('sbsar_info', 'the graph seed set with set_params is still exposed', 'INPUT $randomseed' in t,
                      ' / '.join(l for l in t.splitlines() if 'INPUT' in l))
                # and an Absolute one is not (AGENTS.md): a copy saved with it Absolute, the graph put back;
                # changing the inheritance resets the value, so the value goes back after it
                abs_sbs = os.path.join(scratch, 'seed_absolute.sbs')
                await c('execute_designer_code', {'code': GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n"
                    "from sd.api.sdvalueint import SDValueInt\n"
                    "p = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\nkept = g.getPropertyValue(p).get()\n"
                    "g.setPropertyInheritanceMethod(p, IM.Absolute)\n"
                    "try:\n    sd.getContext().getSDApplication().getPackageMgr().saveCopyOfPackageAs(g.getPackage(), %r)\n"
                    "finally:\n    g.setPropertyInheritanceMethod(p, IM.RelativeToParent)\n"
                    "    g.setPropertyValue(p, SDValueInt.sNew(kept))") % abs_sbs})
                t_abs = text(await c('sbsar_info', {'sbs_path': abs_sbs}))
                check('designer facts', 'an Absolute graph $randomseed is not exposed in a .sbsar (AGENTS.md)',
                      'INPUT $outputsize' in t_abs and 'INPUT $randomseed' not in t_abs,
                      ' / '.join(l for l in t_abs.splitlines() if 'INPUT' in l))
                # the stored seed (5) reaches the .sbsar too, added to the seed a render sets (AGENTS.md: "an
                # offset added to a render's seed"; REVIEW.md TST-39, TST-44): copies storing 0 and 3 to compare
                seed_copies = {}
                for stored_seed in (0, 3):   # copies of the graph storing another seed
                    seed_copies[stored_seed] = os.path.join(scratch, 'seed_stored%d.sbs' % stored_seed)
                    await c('execute_designer_code', {'code': GRAPH_OF % TEST_GRAPH + (
                        "from sd.api.sdproperty import SDPropertyCategory\nfrom sd.api.sdvalueint import SDValueInt\n"
                        "p = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                        "kept = g.getPropertyValue(p).get()\n"
                        "g.setPropertyValue(p, SDValueInt.sNew(%d))\n"
                        "try:\n    sd.getContext().getSDApplication().getPackageMgr().saveCopyOfPackageAs(g.getPackage(), %r)\n"
                        "finally:\n    g.setPropertyValue(p, SDValueInt.sNew(kept))") % (stored_seed, seed_copies[stored_seed])})
                zero_sbs = seed_copies[0]
                # and one with the clouds node's seed made Absolute (REVIEW.md TST-52); the graph's untouched
                abs_node_sbs = os.path.join(scratch, 'seed_absolute_node.sbs')
                await c('execute_designer_code', {'code': GRAPH_OF % TEST_GRAPH + (
                    "from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n"
                    "from sd.api.sdvalueint import SDValueInt\n"
                    "n = g.getNodeFromId('%s'); p = n.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                    "was, kept = n.getPropertyInheritanceMethod(p), n.getPropertyValue(p).get()\n"
                    "try:\n    n.setPropertyInheritanceMethod(p, IM.Absolute)\n"
                    "    sd.getContext().getSDApplication().getPackageMgr().saveCopyOfPackageAs(g.getPackage(), %r)\n"
                    "finally:\n    n.setPropertyInheritanceMethod(p, was); n.setPropertyValue(p, SDValueInt.sNew(kept))") % (
                        clouds, abs_node_sbs)})
                from PIL import Image
                import numpy as np
                # both count: the stored value (5 vs 0 at render seed 0) and the render seed (0 vs 5 for the
                # copy storing 0), so neither replaces the other (REVIEW.md TST-40)
                seed_maps, render_said = {}, {}
                for name, path, seed in (('stored5_seed0', sbs, 0), ('stored0_seed0', zero_sbs, 0), ('stored0_seed5', zero_sbs, 5),
                                         ('stored3_seed2', seed_copies[3], 2), ('abs_node_seed0', abs_node_sbs, 0),
                                         ('abs_node_seed5', abs_node_sbs, 5)):
                    d = os.path.join(scratch, 'seed_render_' + name)
                    t_r = text(await c('render_sbs', {'sbs_path': path, 'output_dir': d, 'outputs': ['height'],
                                                      'params': {'$randomseed': seed}}))
                    render_said[name] = t_r
                    f = os.path.join(d, 'height.png')
                    seed_maps[name] = np.array(Image.open(f)).astype(int) if os.path.isfile(f) else None

                def apart(a, b):
                    ma, mb = seed_maps[a], seed_maps[b]
                    return int(np.abs(ma - mb).max()) if ma is not None and mb is not None and ma.shape == mb.shape else -1
                stored, override = apart('stored5_seed0', 'stored0_seed0'), apart('stored0_seed0', 'stored0_seed5')
                # added: 3 + 2 gives the image of 0 + 5, within the parallel render noise (8, as export vs
                # render); a pair without zeros, since 5 + 0 = 0 + 5 also fits max, OR or XOR (REVIEW.md TST-44)
                added = apart('stored3_seed2', 'stored0_seed5')
                check('designer facts', 'an inherited graph seed stored in the .sbsar is added to the render seed (AGENTS.md)',
                      stored > 8 and override > 8 and 0 <= added <= 8,
                      'max difference: stored value %d, render seed %d, 3+2 vs 0+5 %d (/65535)%s' % (
                          stored, override, added, '' if min(stored, override, added) >= 0 else ' | ' + t_r[-150:]))
                # a node seed made Absolute ignores the render's seed: its noise is the same at render seed 0
                # and 5 (the height output's only randomness is that clouds node), while the copy where it
                # follows the graph changes (REVIEW.md TST-52)
                frozen = apart('abs_node_seed0', 'abs_node_seed5')
                # and the render seed did reach that copy: render_sbs only warns when an input isn't exposed
                # (REVIEW.md TST-58)
                reached = not any('is not exposed' in render_said[k] for k in ('abs_node_seed0', 'abs_node_seed5'))
                check('designer facts', "a node $randomseed made Absolute ignores the render's seed (AGENTS.md)",
                      0 <= frozen <= 8 and override > 8 and reached, 'max difference: Absolute node, render seed 0 vs 5: %d; '
                      'inherited: %d (/65535); render seed exposed: %s' % (frozen, override, reached))
                # and back to a new graph's seed for the later checks (REVIEW.md TST-37)
                t = text(await c('set_params', {'node_id': 'graph', 'params': {'$randomseed': 0}, **G}))
                check('self-test', 'the graph seed checks put the seed back as it was', '5 -> 0' in t, t)
                render_dir = os.path.join(scratch, 'render')
                t = text(await c('render_sbs', {'sbs_path': sbs, 'output_dir': render_dir, 'outputs': ['height']}))
                check('render_sbs', 'png', 'height.png  512x512' in t, t)
                from PIL import Image
                import numpy as np
                exported = np.array(Image.open(os.path.join(scratch, 'export', 'height.png'))).astype(int)
                rendered = np.array(Image.open(os.path.join(render_dir, 'height.png'))).astype(int)
                # the same to within a few 16-bit steps at a few pixels (AGENTS.md, Output; seen: 27 of
                # 262144 pixels off by <= 3/65535); parallel renders aren't bit-identical, so allow 8
                worst = np.abs(exported - rendered).max() if exported.shape == rendered.shape else -1
                check('export_outputs', 'matches render_sbs within 16-bit rounding', 0 <= worst <= 8,
                      'max difference %d/65535, %d pixel(s) differ' % (worst, int((exported != rendered).sum())))
                t = text(await c('export_outputs', {'graph': TEST_GRAPH, 'output_dir': os.path.join(scratch, 'export_exr'),
                                                    'outputs': ['height'], 'file_format': 'exr'}))
                check('export_outputs', 'subset + exr', 'height.exr' in t
                      and os.path.isfile(os.path.join(scratch, 'export_exr', 'height.exr')), t)
                r_ = await c('export_outputs', {'graph': TEST_GRAPH, 'output_dir': os.path.join(scratch, 'none'), 'outputs': ['nope']})
                check('export_outputs', 'error on unknown output', r_.is_error and 'no outputs exported' in text(r_), text(r_))
                t = text(await c('sbsar_info', {'sbs_path': sbs}))
                check('sbsar_info', 'exposed input + size', 'INPUT floor FLOAT4' in t and 'INPUT $outputsize' in t, '')
                means = []
                for v in (0.1, 0.9):
                    d = os.path.join(scratch, 'floor_%s' % v)
                    t = text(await c('render_sbs', {'sbs_path': sbs, 'output_dir': d, 'size_log2': 7,
                                                    'params': {'floor': [v] * 4}}))
                    means.append(t)
                check('render_sbs', 'size override 128', 'height.png  128x128' in means[0], means[0])
                check('render_sbs', 'exposed param changes output',
                      _mean_png(os.path.join(scratch, 'floor_0.1', 'height.png')) + 0.3
                      < _mean_png(os.path.join(scratch, 'floor_0.9', 'height.png')), '')
                t = text(await c('render_sbs', {'sbs_path': sbs, 'output_dir': render_dir, 'output_format': 'exr',
                                                'params': {'nope': 1}}))
                check('render_sbs', 'exr + unexposed warning', 'height.exr' in t and "input 'nope' is not exposed" in t, t)
                check('render_sbs', 'cooking leaves no .sbsar next to the .sbs',
                      not os.path.exists(os.path.splitext(sbs)[0] + '.sbsar'), '')
                sys.path.insert(0, os.path.join(BUNDLE, 'mcp_server'))
                import server as mcp_server_module           # for the sbscooker path only
                cooked = os.path.join(scratch, 'cooked')
                os.makedirs(cooked, exist_ok=True)              # sbscooker needs the folder to exist
                subprocess.run([mcp_server_module.SBSCOOKER, '--inputs', sbs, '--output-path', cooked],
                               capture_output=True, timeout=300)
                sbsar = os.path.join(cooked, TEST_GRAPH + '.sbsar')
                t = text(await c('sbsar_info', {'sbs_path': sbsar}))
                check('sbsar_info', 'reads a .sbsar', 'OUTPUT height' in t, t.splitlines()[0] if t else '')
                t = text(await c('render_sbs', {'sbs_path': sbsar, 'output_dir': os.path.join(scratch, 'from_sbsar'),
                                                'graph': TEST_GRAPH, 'output_format': 'tga'}))
                check('render_sbs', 'from a .sbsar, graph, tga', re.search(r'height\.tga  \d+x\d+', t) is not None, t)
                # cooking drops the graph's default parent size: a .sbsar keeps 256 px, and says so
                check('render_sbs', '.sbsar: own default size, stated', 'height.tga  256x256' in t
                      and "the .sbsar's own default, 256 px" in t, t)
                t = text(await c('render_sbs', {'sbs_path': sbsar, 'output_dir': os.path.join(scratch, 'from_sbsar_512'), 'size_log2': 9}))
                check('render_sbs', '.sbsar with size_log2', 'height.png  512x512' in t, t.splitlines()[-1])
                r_ = await c('render_sbs', {'sbs_path': sbsar, 'output_dir': os.path.join(scratch, 'nope'), 'graph': 'no_such_graph'})
                check('render_sbs', 'error on unknown graph', r_.is_error and 'no_such_graph' in text(r_), text(r_)[:150])
                r_ = await c('preview_maps', {'map_dir': os.path.join(scratch, 'export')})
                check('preview_maps', 'all maps in a folder', is_image(r_), '' if is_image(r_) else text(r_))
                r_ = await c('preview_maps', {'map_dir': render_dir, 'names': ['height'], 'tile_size': 256})
                check('preview_maps', 'side by side', is_image(r_), '')
                r_ = await c('preview_maps', {'map_dir': render_dir, 'names': ['height'], 'crop': [0, 0, 128, 128]})
                check('preview_maps', 'crop', is_image(r_), '')

                # --- README's full example: examples/build_dwarf_trimsheet.py, renamed so it can't touch
                # a trim sheet you have open (it closes earlier builds of its graph id) and saved to scratch
                E = 'example script'
                with open(os.path.join(BUNDLE, 'examples', 'build_dwarf_trimsheet.py')) as f:
                    source = f.read()
                example_sbs = os.path.join(scratch, 'example', EXAMPLE_GRAPH + '.sbs')
                source, n_out = re.subn(r'^OUT_SBS = .*$', 'OUT_SBS = %r' % example_sbs, source, flags=re.M)
                source, n_id = re.subn(r'^GRAPH_ID = .*$', 'GRAPH_ID = %r' % EXAMPLE_GRAPH, source, flags=re.M)
                if (n_out, n_id) != (1, 1):
                    check(E, 'output path and graph id can be redirected', False, 'OUT_SBS/GRAPH_ID lines changed?')
                else:
                    # a run that fails before its first save closes its own unsaved package, so failed
                    # runs don't pile up packages with the graph's name (REVIEW.md INS-13), also when it
                    # fails while setting the package up (INS-17)
                    for where, old, new in (
                            ('in the build', '\n    b.layout()\n', "\n    raise RuntimeError('fails on purpose')\n"),
                            ('setting up', 'self._set_graph_size()\n', "raise RuntimeError('fails on purpose')\n")):
                        failing = os.path.join(scratch, 'build_example_failing.py')
                        with open(failing, 'w') as f:
                            f.write(source.replace(old, new, 1))
                        r_ = await c('run_designer_script', {'path': failing, 'timeout_s': 300})
                        t = text(await c('execute_designer_code', {'code': (
                            "import sd\npm = sd.getContext().getSDApplication().getPackageMgr()\n"
                            "print('UNSAVED_LEFT=%%d' %% sum(1 for p in pm.getUserPackages() if not p.getFilePath() and "
                            "any(r.getIdentifier() == %r for r in p.getChildrenResources(False))))") % EXAMPLE_GRAPH}))
                        ran = text(r_)                     # a script's traceback comes back as text, not a tool error
                        check(E, 'a run failing %s closes its own unsaved package' % where, old in source
                              and 'fails on purpose' in ran and 'UNSAVED_LEFT=0' in t,
                              t.strip() + ' | ' + ran.strip()[-160:])
                    example = os.path.join(scratch, 'build_example.py')
                    with open(example, 'w') as f:
                        f.write(source)
                    t = text_build = text(await c('run_designer_script', {'path': example, 'timeout_s': 300}))
                    check(E, 'builds and saves', 'Saved trim sheet to' in t and 'ERROR' not in t
                          and 'WARNING' not in t and os.path.isfile(example_sbs), t[-300:])
                    # the readable-graph finish (ROADMAP item, now in the script): a frame per
                    # section, overridable size, portals written into the saved file
                    t = text(await c('execute_designer_code', {'code': GRAPH_OF % EXAMPLE_GRAPH + (
                        "from sd.api.sdgraphobjectframe import SDGraphObjectFrame\n"
                        "from sd.api.sdproperty import SDPropertyCategory\n"
                        "p=g.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
                        "print('FRAMES=%d SIZE=%s PARENT=%d' % (sum(isinstance(o, SDGraphObjectFrame) for o in g.getGraphObjects()),"
                        " g.getPropertyInheritanceMethod(p).name, g.getDefaultParentSize().x))")}))
                    check(E, 'frames per section, overridable 2048 size', 'FRAMES=17 SIZE=RelativeToParent PARENT=2048' in t, t)
                    with open(example_sbs, encoding='utf-8') as f:
                        portals = len(re.findall(r'<displayType v="1"\s*/>', f.read()))
                    reported = re.search(r'(\d+) of (\d+) links as portals', text_build)
                    check(E, 'long links between sections saved as portals',
                          reported is not None and portals == int(reported.group(1)) > 0, '%d in the file; %s' % (
                              portals, reported.group(0) if reported else 'no count printed'))
                    # a section larger than the view: fitting it zooms out below 100 %
                    t = text(await c('open_graph', {'graph': EXAMPLE_GRAPH, 'frame': 'K: wood planks'}))
                    m = re.search(r'zoom (\d+)%', t)
                    check('open_graph', 'a large frame zooms out to fit', m is not None and 5 < int(m.group(1)) < 100, t)
                    await c('open_graph', {'graph': EXAMPLE_GRAPH})   # so you can see it
                    t = text(await c('export_outputs', {'graph': EXAMPLE_GRAPH, 'output_dir': os.path.join(scratch, 'example_maps')}))
                    names = ('basecolor', 'normal', 'roughness', 'metallic', 'height', 'ambientocclusion')
                    check(E, '6 maps at 2048', 'exported 6 file(s)' in t and all('%s.png  2048x2048' % m in t for m in names), t)
                    t = text(await c('execute_designer_code', {'code': (
                        "import sd\ng=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() "
                        "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
                        "print(' '.join('%%s=%%s' %% (n.getAnnotationPropertyValueFromId('identifier').get(), n.getIdentifier()) "
                        "for n in g.getOutputNodes()))") % EXAMPLE_GRAPH}))
                    outs = dict(re.findall(r'(\w+)=(\d+)', t))
                    t = text(await c('execute_designer_code', {'code': GRAPH_OF % EXAMPLE_GRAPH + (
                        "n=g.getNodeFromId(%r)\nu=n.getAnnotationPropertyValueFromId('usages').get()[0].get()\n"
                        "print('USAGE=%%s %%s %%s' %% (u.getName(), u.getComponents(), u.getColorSpace()))") % outs.get('basecolor', '0')}))
                    check('designer facts', 'output usages read back (baseColor RGBA sRGB)', 'USAGE=baseColor RGBA sRGB' in t, t)
                    t = text(await c('check_tiling', {'node_id': outs.get('basecolor', '?'), 'graph': EXAMPLE_GRAPH, 'axis': 'horizontal'}))
                    ratio = re.search(r'ratio ([\d.]+)', t)
                    check(E, 'tiles horizontally (trim sheet)', ratio is not None and float(ratio.group(1)) <= 3, t.splitlines()[-1])
                    await c('open_graph', {'graph': TEST_GRAPH})
                    # the fit refuses to zoom a view that shows another graph (here: fit the trim
                    # sheet's frame while the self-test graph is in the editor, via the helper itself)
                    with open(os.path.join(BUNDLE, 'mcp_server', 'designer_helpers.py'), encoding='utf-8') as f:
                        helpers = f.read()
                    t = text(await c('execute_designer_code', {'code': helpers + (
                        "\ntry:\n    _fit_view_to(find_graph(%r), frame='K: wood planks')\n    print('FITTED')\n"
                        "except RuntimeError as e:\n    print('REFUSED', e)\n") % EXAMPLE_GRAPH}))
                    check('open_graph', 'never fits a view showing another graph',
                          'REFUSED' in t and 'not %s' % EXAMPLE_GRAPH in t, t.strip()[-200:])

                    # re-running the example never discards edits (REVIEW.md INS-8): a copy of its
                    # graph saved elsewhere and edited is left open, and unsaved edits to the
                    # previous build make it refuse instead of unloading them
                    decoy_sbs = os.path.join(scratch, 'example', 'my_copy.sbs')
                    edit_both = GRAPH_OF % EXAMPLE_GRAPH + (
                        "pm=sd.getContext().getSDApplication().getPackageMgr()\npm.saveCopyOfPackageAs(g.getPackage(), %r)\n"
                        "copy=pm.loadUserPackage(%r)\ncopy.getChildrenResources(False)[0].newNode('sbs::compositing::blur')\n"
                        "print('DECOY_MODIFIED=%%s' %% copy.isModified())") % (decoy_sbs, decoy_sbs)
                    state = "import os\n" + GRAPH_OF.replace("[0]\n", "\n") % EXAMPLE_GRAPH + (
                        "print('OPEN=' + ','.join('%s:%s' % (os.path.basename(r.getPackage().getFilePath() or '-'), "
                        "r.getPackage().isModified()) for r in g))")
                    t = text(await c('execute_designer_code', {'code': edit_both}))
                    t = text(await c('run_designer_script', {'path': example, 'timeout_s': 300}))
                    after = text(await c('execute_designer_code', {'code': state}))
                    check(E, 'a re-run leaves an edited copy elsewhere open', 'Saved trim sheet to' in t
                          and 'my_copy.sbs:True' in after, t.strip()[-150:] + ' / ' + after.strip())
                    t = text(await c('execute_designer_code', {'code': (
                        "import sd\npm=sd.getContext().getSDApplication().getPackageMgr()\n"
                        "for p in pm.getUserPackages():\n"
                        "    if (p.getFilePath() or '') == %r:\n        p.getChildrenResources(False)[0].newNode('sbs::compositing::blur')\n"
                        "        print('EDITED', p.isModified())") % example_sbs}))
                    t = text(await c('run_designer_script', {'path': example, 'timeout_s': 300}))
                    after = text(await c('execute_designer_code', {'code': state}))
                    check(E, 'a re-run refuses to discard unsaved edits', 'ERROR' in t and 'unsaved' in t
                          and '%s:True' % os.path.basename(example_sbs) in after, t.strip()[-150:] + ' / ' + after.strip())
                    # ...also when its graph was renamed: the package at OUT_SBS is matched by its path
                    # (REVIEW.md INS-22)
                    t = text(await c('execute_designer_code', {'code': (
                        "import sd\npm=sd.getContext().getSDApplication().getPackageMgr()\n"
                        "for p in pm.getUserPackages():\n"
                        "    if (p.getFilePath() or '') == %r:\n"
                        "        p.getChildrenResources(False)[0].setIdentifier('mcp_selftest_trimsheet_renamed')\n"
                        "        print('RENAMED', p.isModified(), p.getChildrenResources(False)[0].getIdentifier())") % example_sbs}))
                    t2 = text(await c('run_designer_script', {'path': example, 'timeout_s': 300}))
                    check(E, 'a re-run refuses to discard unsaved edits to a renamed previous build',
                          # the new name read back, so a rename that did nothing can't pass (REVIEW.md TST-50)
                          'RENAMED True mcp_selftest_trimsheet_renamed' in t and 'ERROR' in t2 and 'unsaved' in t2,
                          t.strip() + ' / ' + t2.strip()[-150:])
                    await c('execute_designer_code', {'code': (
                        "import sd\npm=sd.getContext().getSDApplication().getPackageMgr()\n"
                        "for p in list(pm.getUserPackages()):\n    if (p.getFilePath() or '') == %r:\n        pm.unloadUserPackage(p)") % decoy_sbs})

                # --- script runner
                script = os.path.join(scratch, 'probe_script.py')
                with open(script, 'w', encoding='utf-8') as f:
                    f.write("import sd\nprint('script file', __file__.endswith('probe_script.py'), "
                            "sd.getContext().getSDApplication().getVersion())\nprint('utf-8: → é ✓')\n")
                t = text(await c('run_designer_script', {'path': script, 'timeout_s': 30}))
                check('run_designer_script', '__file__ + sd', 'script file True' in t, t)
                # a UTF-8 script arrives intact whatever the server's locale (REVIEW.md SRV-11)
                check('run_designer_script', 'UTF-8 text survives', 'utf-8: → é ✓' in t, t)
            finally:
                print('\ncleanup:', text(await c('execute_designer_code', {'code': CLEAN})).strip())
                # the library packages the run loaded, in a separate call (graph views from the test
                # graph are torn down first); the user's own stay (REVIEW.md TST-30)
                time.sleep(0.5)
                await restore_library_packages(c, libs_before)
                shutil.rmtree(os.path.join(os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(
                    os.path.expanduser('~'), '.sd_mcp', 'snapshots'), TEST_GRAPH), ignore_errors=True)
                if user_graph and user_graph != TEST_GRAPH:
                    t = text(await c('execute_designer_code', {'code': SAME_GRAPH_BACK}))
                    check('open_graph', 'the self-test puts your graph back in the editor', 'SAME=True' in t, t.strip())
                if was_running:
                    skip('quit_designer', 'closes Designer', 'Designer was already running, so it is left open')
                else:
                    # our own instance: nothing of the user's can be lost. First make the window
                    # ignore Close (as a blocking dialog would): quit_designer must time out, then
                    # its fallback ends Designer anyway, without a crash (REVIEW.md PLG-8: the
                    # earlier exit() fallback crashed Designer's teardown, twice)
                    dumps_before = crash_dumps()
                    forced_marker = os.path.join(scratch, 'forced_quit_about_to_quit')
                    await c('execute_designer_code', {'code': (
                        "import sys\nfrom PySide6.QtCore import QObject, QEvent\nfrom PySide6.QtWidgets import QApplication\n"
                        "class _KeepOpen(QObject):\n    def eventFilter(self, obj, event):\n"
                        "        if event.type() == QEvent.Type.Close:\n            event.ignore()\n            return True\n"
                        "        return False\n"
                        "sys._selftest_keep_open = _KeepOpen()\n"
                        "for w in QApplication.instance().topLevelWidgets():\n"
                        "    if w.isVisible(): w.installEventFilter(sys._selftest_keep_open)\n"
                        "QApplication.instance().aboutToQuit.connect(lambda: open(%r, 'w').close())\n"
                        "print('ignoring Close')") % forced_marker})
                    r_ = await c('quit_designer', {'discard_unsaved': True, 'wait_s': 2})
                    check('quit_designer', 'times out when the window stays open', r_.is_error
                          and 'still running after 2s' in text(r_), text(r_))
                    deadline = time.time() + 30
                    while time.time() < deadline and not (await c('designer_status')).is_error:
                        time.sleep(1)
                    time.sleep(3)
                    gone = (await c('designer_status')).is_error
                    if sys.platform != 'win32':
                        gone = gone and subprocess.run(['pgrep', '-f', 'MacOS/Adobe Substance 3D Designer( |$)'],
                                                       capture_output=True).returncode != 0
                    new_dumps = new_crash_dumps(dumps_before)
                    check('quit_designer', 'fallback ends it anyway, without a crash', gone and not new_dumps,
                          'gone=%s, new crash dumps: %s' % (gone, sorted(new_dumps)))
                    # ...through os._exit, which never emits aboutToQuit: what tells a forced quit from a
                    # normal one in the check below (REVIEW.md TST-25)
                    check('designer facts', 'a forced quit (os._exit) never emits aboutToQuit',
                          gone and not os.path.exists(forced_marker), 'marker written: %s' % os.path.exists(forced_marker))
                    t = text(await c('launch_designer', {'wait_s': 240}))
                    check('launch_designer', 'starts again after a quit', 'Designer started in' in t and 'ERROR' not in t, t)
                    prompt_marker = os.path.join(scratch, 'prompt_shown')
                    # a window shown while the main window closes (a prompt appearing then) doesn't keep
                    # Designer alive: it quits once its main window has closed (REVIEW.md HLP-19, measured).
                    # A quit by itself emits aboutToQuit, which writes a marker; the fallback's os._exit
                    # (here at about 5 s, as the prompt stays visible) never does (REVIEW.md TST-25)
                    normal_quit = os.path.join(scratch, 'quit_normally')
                    await c('execute_designer_code', {'code': (
                        "import sys\nfrom PySide6.QtCore import QObject, QEvent, QTimer\n"
                        "from PySide6.QtWidgets import QApplication, QLabel\n"
                        "def _prompt():\n"
                        "    sys._selftest_prompt = QLabel('sd_mcp self-test: a prompt after closing')\n"
                        "    sys._selftest_prompt.show()\n"
                        "class _PromptAfterClose(QObject):\n    def eventFilter(self, obj, event):\n"
                        "        if event.type() == QEvent.Type.Close:\n            _prompt()\n"
                        "            open(%r, 'w').write(str(sys._selftest_prompt.isVisible()))\n"
                        "        return False\n"
                        "sys._selftest_prompt_filter = _PromptAfterClose()\n"
                        "QApplication.instance().aboutToQuit.connect(lambda: open(%r, 'w').close())\n"
                        "for w in QApplication.instance().topLevelWidgets():\n"
                        "    if w.isVisible() and w.metaObject().className() == 'QStackedWidget':\n"
                        "        w.installEventFilter(sys._selftest_prompt_filter)") % (prompt_marker, normal_quit)})
                    dumps_before, quit_started = crash_dumps(), time.time()
                    await c('quit_designer', {'discard_unsaved': True, 'wait_s': 2})
                    while time.time() - quit_started < 60 and designer_alive():
                        time.sleep(1)
                    took = time.time() - quit_started
                    new_dumps = new_crash_dumps(dumps_before)
                    check('designer facts', 'Designer quits once its main window closes, even with another window shown',
                          os.path.exists(prompt_marker) and open(prompt_marker).read() == 'True'
                          and os.path.exists(normal_quit) and not designer_alive() and not new_dumps,
                          'prompt shown: %s; quit by itself (aboutToQuit): %s; gone after %.0f s, new crash dumps: %s' % (
                              open(prompt_marker).read() if os.path.exists(prompt_marker) else 'no',
                              os.path.exists(normal_quit), took, sorted(new_dumps)))
                    t = text(await c('launch_designer', {'wait_s': 240}))
                    check('launch_designer', 'starts again after a forced quit', 'Designer started in' in t and 'ERROR' not in t, t)
                    # a slow normal shutdown must be left to finish, not killed by the os._exit
                    # fallback: 7 s of work in the window's close handler (HLP-17), then 7 s in an
                    # aboutToQuit handler (HLP-12) that shows a window, so only the fallback's
                    # "every window had closed" test can keep the process alive (TST-19, TST-23).
                    # Both keep processing events past the fallback's 5 s. No modal dialog here: with
                    # one open as well, Designer once didn't go on to quit and stayed without a window
                    # (REVIEW.md HLP-23; not reproduced on demand: hiding the main window instead of
                    # closing it still quits in 2 s)
                    slow_close = os.path.join(scratch, 'slow_close_finished')
                    slow_marker = os.path.join(scratch, 'slow_shutdown_finished')
                    await c('execute_designer_code', {'code': (
                        "import sys, time\nfrom PySide6.QtCore import QObject, QEvent\n"
                        "from PySide6.QtWidgets import QApplication, QLabel\n"
                        "def _busy(seconds):\n    started = time.time()\n"
                        "    while time.time() - started < seconds:\n"
                        "        QApplication.processEvents()\n        time.sleep(0.05)\n"
                        "class _SlowClose(QObject):\n    def eventFilter(self, obj, event):\n"
                        "        if event.type() == QEvent.Type.Close and not getattr(self, 'done', False):\n"
                        "            self.done = True\n            _busy(7)\n            open(%r, 'w').close()\n"
                        "        return False\n"
                        "def _slow_shutdown():\n"
                        "    sys._selftest_label = QLabel('sd_mcp self-test: slow shutdown')\n"
                        "    sys._selftest_label.show()\n    _busy(7)\n    open(%r, 'w').close()\n"
                        "sys._selftest_slow_close = _SlowClose()\n"
                        "for w in QApplication.instance().topLevelWidgets():\n"
                        "    if w.isVisible() and w.metaObject().className() == 'QStackedWidget':\n"
                        "        w.installEventFilter(sys._selftest_slow_close)\n"
                        "sys._selftest_slow_shutdown = _slow_shutdown\n"
                        "QApplication.instance().aboutToQuit.connect(_slow_shutdown)") % (slow_close, slow_marker)})
                    dumps_before = crash_dumps()
                    t = text(await c('quit_designer', {'discard_unsaved': True}))
                    gone = (await c('designer_status')).is_error
                    new_dumps = new_crash_dumps(dumps_before)   # a dump is written seconds later (REVIEW.md TST-17)
                    closed, finished = os.path.exists(slow_close), os.path.exists(slow_marker)
                    check('quit_designer', 'a slow close handler is left to finish', closed,
                          'its 7 s close handler finished' if closed
                          else 'the close handler did not finish: the process was ended under it')
                    check('quit_designer', 'a slow shutdown with a window showing is left to finish',
                          finished and 'Designer quit after' in t and gone and not new_dumps,
                          ('its 7 s aboutToQuit handler finished' if finished
                           else 'the aboutToQuit handler did not finish') + ' | ' + t.strip()[-80:])
                    t = text(await c('launch_designer', {'wait_s': 240}))
                    check('launch_designer', 'starts again after a slow quit', 'Designer started in' in t and 'ERROR' not in t, t)
                    # the realistic blocker: a modal dialog (its own event loop) must not stop quitting
                    await c('execute_designer_code', {'code': (
                        "from PySide6.QtCore import QTimer\nfrom PySide6.QtWidgets import QMessageBox\n"
                        "QTimer.singleShot(0, lambda: QMessageBox.information(None, 'sd_mcp self-test', "
                        "'A modal dialog; quit_designer must still close Designer.'))")})
                    time.sleep(1)
                    modal = text(await c('execute_designer_code', {'code': (
                        "from PySide6.QtWidgets import QApplication\n"
                        "print('MODAL=' + type(QApplication.instance().activeModalWidget()).__name__)")}))
                    dumps_before = crash_dumps()
                    t = text(await c('quit_designer', {'discard_unsaved': True}))
                    gone = (await c('designer_status')).is_error
                    new_dumps = new_crash_dumps(dumps_before)
                    check('quit_designer', 'closes the Designer it started, with a modal dialog open, without a crash',
                          'MODAL=QMessageBox' in modal and 'Designer quit after' in t and gone and not new_dumps,
                          modal + t + (' new crash dumps: %s' % sorted(new_dumps) if new_dumps else ''))
    return tools


def summarize(tools, results, skipped):
    """(summary text, ok). A tool counts as covered only with at least one check that ran; one
    whose checks were all skipped (quit_designer while your own Designer runs) is listed, and
    doesn't fail the run. Missing tools and failed checks do."""
    ran = {t for t, v in results.items() if v}
    covered = set(tools) & ran
    only_skipped = sorted(set(tools) & (set(results) - ran))
    missing = sorted(set(tools) - set(results))
    failed = sorted(k for k, v in results.items() if not all(v))
    passed = sum(sum(v) for v in results.values())
    total = sum(len(v) for v in results.values())
    lines = ['%d/%d tools covered%s%s' % (len(covered), len(tools),
                                         ('; only skipped: %s' % only_skipped) if only_skipped else '',
                                         ('; NOT covered: %s' % missing) if missing else ''),
             'checks passed: %d/%d; skipped: %d; tools with failures: %s' % (
                 passed, total, len(skipped), ', '.join(failed) or 'none')]
    return '\n'.join(lines), not failed and not missing


def main():
    scratch = tempfile.mkdtemp(prefix='sd_mcp_selftest_')
    try:
        tools = asyncio.run(run(scratch))
    finally:
        dumps_before = crash_dumps()       # just before the clean-up it is about (REVIEW.md TST-21)
        if designer_alive():
            # deleting it while Designer ran crashed Designer twice, in its own file watcher, and
            # couldn't be reproduced on demand (REVIEW.md PLG-9, PLG-18): leave it to the OS
            print('scratch folder left for the OS to clear, since Designer is running:', scratch)
        else:
            shutil.rmtree(scratch, ignore_errors=True)
    if STATE['was_running']:
        # and the user's Designer must still be running, with no new crash dump, a little after the
        # run's end (REVIEW.md PLG-9, TST-16; the scratch folder is no longer deleted then, TST-43)
        new_dumps = new_crash_dumps(dumps_before)
        alive = designer_alive()
        check('self-test', 'your Designer is still running after the run, with no crash dump', alive and not new_dumps,
              'running=%s, new crash dumps: %s' % (alive, sorted(new_dumps)))
    summary, ok = summarize(tools, results, skipped)
    print('\n' + summary)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
