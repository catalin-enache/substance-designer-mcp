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


CLEAN = ("import sd\npm=sd.getContext().getSDApplication().getPackageMgr()\nn=0\n"
         "for p in list(pm.getUserPackages()):\n"
         "    if any(r.getIdentifier() in %r for r in p.getChildrenResources(False)):\n"
         "        pm.unloadUserPackage(p); n+=1\nprint('removed', n)" % ((TEST_GRAPH, SAVED_GRAPH, EXAMPLE_GRAPH, DUP_GRAPH),))
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
INHERIT = GRAPH_OF + ("from sd.api.sdproperty import SDPropertyCategory\nn=g.getNodeFromId('%s')\n"
                      "p=n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
                      "print('INHERIT=%%s VALUE=%%s' %% (n.getPropertyInheritanceMethod(p).name, n.getPropertyValue(p).get()))")
CURRENT_GRAPH = ("import sd\ng=sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()\n"
                 "print('CURRENT=' + (g.getIdentifier() if g else ''))")


async def cancel_from_second_client():
    await asyncio.sleep(2)
    async with stdio_client(PARAMS) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return text(await s.call_tool('cancel_designer_job', {}))


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
            was_running = not (await c('designer_status')).is_error
            t = text(await c('launch_designer', {'wait_s': 240}))
            check('launch_designer', 'already running' if was_running else 'started from closed',
                  ('already running' if was_running else 'Designer started in') in t and 'ERROR' not in t, t)
            user_graph = re.search(r'CURRENT=(.*)', text(await c('execute_designer_code', {'code': CURRENT_GRAPH}))).group(1).strip()
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
                for name, req in (('a wrong answer', {'auth': 'x' * 64, 'cmd': 'status'}),
                                  ('no answer', {'cmd': 'status'}),
                                  ('the token itself (old protocol)', {'token': token, 'cmd': 'status'}),
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
                r_ = await c('set_params', {'node_id': lv, 'params': {'levelinlow': [1, 2]}, **G})
                check('set_params', 'error on bad length', r_.is_error and 'expects 4' in text(r_), text(r_))
                before = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
                r_ = await c('set_params', {'node_id': lv, 'params': {'$outputsize': 11}, **G})
                after = text(await c('execute_designer_code', {'code': INHERIT % (TEST_GRAPH, lv)}))
                check('set_params', 'rejected value changes nothing (not even inheritance)',
                      r_.is_error and 'expects 2' in text(r_) and 'INHERIT=' in before and before == after, before + after)
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
                t = text(await c('read_designer_log', {'errors_only': True, 'lines': 3}))
                check('read_designer_log', 'errors_only filter', 'matching line' in t and all(
                    ('[ERROR]' in l or '[WARNING]' in l) for l in t.splitlines()[1:]), t.splitlines()[0])
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
                    {'op': 'expose', 'node': 'b', 'param': 'opacitymult', 'input_id': 'batch_opacity', 'max': 1},
                ], **G}))
                check('apply_edits', '8 ops with refs', 'applied 8 op(s)' in t and "removed 1 connection(s) into" in t
                      and "graph input 'batch_opacity'" in t, t.splitlines()[-1])
                await c('remove_graph_input', {'input_id': 'batch_opacity', **G})
                batch_blend = re.search(r"'b': '(\d+)'", t).group(1)
                r_ = await c('apply_edits', {'ops': [
                    {'op': 'add', 'definition': 'levels', 'ref': 'x'},
                    {'op': 'connect', 'from': 'x', 'to': batch_blend, 'input': 'nope'},
                ], **G})
                check('apply_edits', 'stops at failing op', r_.is_error and 'op 1 (connect) failed' in text(r_), text(r_))
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
                    "    pkg=pm.newUserPackage(); g=SDSBSCompGraph.sNew(pkg); g.setIdentifier('inherit_'+m.name)\n"
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
                      and os.path.dirname(copied.group(1)) == os.path.join(scratch, TEST_GRAPH + '.resources'), t)
                await c('delete_nodes', {'node_ids': [added_id(t)], **G})
                stats_before = text(await c('node_stats', {'node_id': lv, **G}))
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
                render_dir = os.path.join(scratch, 'render')
                t = text(await c('render_sbs', {'sbs_path': sbs, 'output_dir': render_dir, 'outputs': ['height']}))
                check('render_sbs', 'png', 'height.png  512x512' in t, t)
                from PIL import Image
                import numpy as np
                exported = np.array(Image.open(os.path.join(scratch, 'export', 'height.png'))).astype(int)
                rendered = np.array(Image.open(os.path.join(render_dir, 'height.png'))).astype(int)
                # same up to the last 16-bit step (seen: 27 of 262144 pixels off by <= 3/65535)
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

                # --- script runner
                script = os.path.join(scratch, 'probe_script.py')
                with open(script, 'w') as f:
                    f.write("import sd\nprint('script file', __file__.endswith('probe_script.py'), "
                            "sd.getContext().getSDApplication().getVersion())\n")
                t = text(await c('run_designer_script', {'path': script, 'timeout_s': 30}))
                check('run_designer_script', '__file__ + sd', 'script file True' in t, t)
            finally:
                print('\ncleanup:', text(await c('execute_designer_code', {'code': CLEAN})).strip())
                shutil.rmtree(os.path.join(os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(
                    os.path.expanduser('~'), '.sd_mcp', 'snapshots'), TEST_GRAPH), ignore_errors=True)
                if user_graph and user_graph != TEST_GRAPH:
                    await c('open_graph', {'graph': user_graph})
                    print('reopened your graph:', user_graph)
                if was_running:
                    skip('quit_designer', 'closes Designer', 'Designer was already running, so it is left open')
                else:
                    # our own instance: nothing of the user's can be lost. First make the window
                    # ignore Close (as a blocking dialog would): quit_designer must time out, then
                    # its exit() fallback ends Designer anyway.
                    await c('execute_designer_code', {'code': (
                        "import sys\nfrom PySide6.QtCore import QObject, QEvent\nfrom PySide6.QtWidgets import QApplication\n"
                        "class _KeepOpen(QObject):\n    def eventFilter(self, obj, event):\n"
                        "        if event.type() == QEvent.Type.Close:\n            event.ignore()\n            return True\n"
                        "        return False\n"
                        "sys._selftest_keep_open = _KeepOpen()\n"
                        "for w in QApplication.instance().topLevelWidgets():\n"
                        "    if w.isVisible(): w.installEventFilter(sys._selftest_keep_open)\nprint('ignoring Close')")})
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
                    check('quit_designer', 'exit() fallback ends it anyway', gone, '')
                    t = text(await c('launch_designer', {'wait_s': 240}))
                    check('launch_designer', 'starts again after a quit', 'Designer started in' in t and 'ERROR' not in t, t)
                    # the realistic blocker: a modal dialog (its own event loop) must not stop quitting
                    await c('execute_designer_code', {'code': (
                        "from PySide6.QtCore import QTimer\nfrom PySide6.QtWidgets import QMessageBox\n"
                        "QTimer.singleShot(0, lambda: QMessageBox.information(None, 'sd_mcp self-test', "
                        "'A modal dialog; quit_designer must still close Designer.'))")})
                    time.sleep(1)
                    modal = text(await c('execute_designer_code', {'code': (
                        "from PySide6.QtWidgets import QApplication\n"
                        "print('MODAL=' + type(QApplication.instance().activeModalWidget()).__name__)")}))
                    t = text(await c('quit_designer', {'discard_unsaved': True}))
                    gone = (await c('designer_status')).is_error
                    check('quit_designer', 'closes the Designer it started, with a modal dialog open',
                          'MODAL=QMessageBox' in modal and 'Designer quit after' in t and gone, modal + t)
    return tools


def main():
    scratch = tempfile.mkdtemp(prefix='sd_mcp_selftest_')
    try:
        tools = asyncio.run(run(scratch))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    missing = sorted(set(tools) - set(results))
    failed = sorted(k for k, v in results.items() if not all(v))
    passed = sum(sum(v) for v in results.values())
    total = sum(len(v) for v in results.values())
    print('\n%d/%d tools covered%s' % (len(set(tools) & set(results)), len(tools),
                                      ('; NOT covered: %s' % missing) if missing else ''))
    print('checks passed: %d/%d; skipped: %d; tools with failures: %s' % (
        passed, total, len(skipped), ', '.join(failed) or 'none'))
    sys.exit(1 if failed or missing else 0)


if __name__ == '__main__':
    main()
