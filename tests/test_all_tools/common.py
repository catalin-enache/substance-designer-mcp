"""What every part of the live self-test shares: the check/skip record, the MCP and bridge helpers,
the code snippets sent to Designer, and the summary. The run itself is in __main__.py."""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Coroutine
from typing import Any, Protocol

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult

BUNDLE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BUNDLE)
from project_constants import (  # noqa: E402 (after the sys.path entry; `X as X` re-exports them)
    PLUGIN as PLUGIN,
    PLUGIN_PACKAGE_DIR as PLUGIN_PACKAGE_DIR,
    TOKEN_FILE as TOKEN_FILE,
)

sys.path.insert(0, os.path.join(BUNDLE, 'mcp_server'))
import designer_helpers  # noqa: E402

helpers_source = designer_helpers.source  # the helpers as sent to Designer (used by the categories)
SERVER = os.path.join(BUNDLE, 'mcp_server', 'server.py')
TEST_GRAPH = 'mcp_selftest'
SAVED_GRAPH = 'mcp_selftest_saved'  # create_graph(save_path=...)
DUP_GRAPH = 'mcp_selftest_dup'  # two open graphs with the same identifier
EXAMPLE_GRAPH = 'mcp_selftest_trimsheet'  # examples/build_dwarf_trimsheet.py, renamed
PORT = int(os.environ.get('SD_BRIDGE_PORT', '9877'))
PARAMS = StdioServerParameters(command=sys.executable, args=[SERVER])

results: dict[str, list[bool]] = {}
skipped: list[tuple[str, str]] = []


def check(tool: str, name: str, ok: object, detail: str = '') -> None:
    ok = bool(ok)  # a condition like `refs and not missing` may be [] or None (REVIEW.md TST-29)
    results.setdefault(tool, []).append(ok)
    print('%s  %-22s %s | %s' % ('PASS' if ok else 'FAIL', tool, name, detail.strip()[:150].replace('\n', ' / ')))


def skip(tool: str, name: str, why: str) -> None:
    results.setdefault(tool, [])
    skipped.append((tool, name))
    print('SKIP  %-22s %s | %s' % (tool, name, why))


def text(r: CallToolResult) -> str:
    return '\n'.join(c.text for c in r.content if c.type == 'text')


def is_image(r: CallToolResult) -> bool:
    return bool(r.content) and r.content[0].type == 'image' and not r.is_error


def added_id(t: str) -> str:
    # no match raises AttributeError, which the run's except reports (REVIEW.md TST-63)
    return re.search(r'added (\d+)', t).group(1)  # type: ignore[union-attr]


def _mean_png(path: str) -> float:
    import numpy as np
    from PIL import Image

    a = np.array(Image.open(path)).astype(float)
    return float(a.mean() / (65535.0 if a.max() > 255 else 255.0))


def pixel_values(t: str) -> dict[tuple[int, int], list[float]]:
    """'pixel (x,y): R=0.1, G=0.2' lines -> {(x, y): [0.1, 0.2]}"""
    return {
        (int(x), int(y)): [float(v) for v in re.findall(r'=(-?[\d.]+)', vals)]
        for x, y, vals in re.findall(r'pixel \((\d+),(\d+)\): (.*)', t)
    }


def raw_request(request: dict[str, Any], token: str | None = None) -> Any:
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


def lan_address() -> str | None:
    """This machine's non-loopback IPv4 address, or None (a UDP connect sends no packets)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as u:
            u.connect(('192.0.2.1', 9))
            ip: str = u.getsockname()[0]
        return None if ip.startswith('127.') or ip == '0.0.0.0' else ip
    except OSError:
        return None


def sd_run(*args: str, timeout: float = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, os.path.join(BUNDLE, 'client', 'sd_run.py'), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def image_size(r: CallToolResult) -> tuple[int, int]:
    import io

    from PIL import Image

    img = next(x for x in r.content if x.type == 'image')
    return Image.open(io.BytesIO(base64.b64decode(img.data))).size


def positions(t: str) -> dict[str, tuple[float, float]]:
    """describe_graph text -> {node id: (x, y)}"""
    return {i: (float(x), float(y)) for i, x, y in re.findall(r'^(\d+) \S+ @\((-?[\d.]+),(-?[\d.]+)\)', t, re.M)}


def clipboard_fingerprint() -> str | None:
    """Hash of the clipboard (never printed). None where we can't read it (non-macOS)."""
    if sys.platform != 'darwin':
        return None
    info = subprocess.run(['osascript', '-e', 'clipboard info'], capture_output=True).stdout
    data = subprocess.run(['pbpaste'], capture_output=True).stdout
    return hashlib.sha256(info + data).hexdigest()


# Designer's library packages loaded right now (their paths), so the run can unload the ones it
# loaded itself (describe_node, add ops of library graphs) and leave the user's (REVIEW.md TST-30)
LIBRARY_PACKAGES = (
    'import os, sd\nfrom sd.api.sdapplication import SDApplicationPath\napp = sd.getContext().getSDApplication()\n'
    "lib = os.path.normcase(os.path.join(app.getPath(SDApplicationPath.DefaultResourcesDir), 'packages'))\n"
    "print('LIBS=' + '|'.join(sorted(p.getFilePath() for p in app.getPackageMgr().getUserPackages()\n"
    "                                if os.path.normcase(p.getFilePath() or '').startswith(lib))))"
)
UNLOAD_LIBRARY_PACKAGES = (
    'import os, sd\nfrom sd.api.sdapplication import SDApplicationPath\napp = sd.getContext().getSDApplication()\n'
    "keep = set(%r)\nlib = os.path.normcase(os.path.join(app.getPath(SDApplicationPath.DefaultResourcesDir), 'packages'))\n"
    'for p in list(app.getPackageMgr().getUserPackages()):\n'
    "    path = p.getFilePath() or ''\n"
    '    if os.path.normcase(path).startswith(lib) and path not in keep:\n'
    '        app.getPackageMgr().unloadUserPackage(p)\n'
)
# Every graph the self-test creates is named mcp_selftest...: this closes them all
CLEAN = (
    'import sd\npm=sd.getContext().getSDApplication().getPackageMgr()\nn=0\n'
    'for p in list(pm.getUserPackages()):\n'
    "    if any(r.getIdentifier().startswith('mcp_selftest') for r in p.getChildrenResources(False)):\n"
    "        pm.unloadUserPackage(p); n+=1\nprint('removed', n)"
)
# Undo/Redo via Designer's Edit menu, scheduled to run after this call's own undo group closes
UNDO_REDO = (
    'import sd\nfrom PySide6.QtCore import QTimer\nfrom PySide6.QtWidgets import QApplication, QMenu\n'
    'g=sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()\n'
    "if g is None or g.getIdentifier()!='%s':\n    print('NOT_FOCUSED')\nelse:\n"
    "    acts=[a for w in QApplication.instance().allWidgets() if isinstance(w, QMenu) and w.title()=='&Edit'\n"
    "          for a in w.actions() if a.text()=='%s' and a.isEnabled()]\n"
    "    if acts:\n        QTimer.singleShot(0, acts[0].trigger)\n        print('SCHEDULED')\n"
    "    else:\n        print('NO_ACTION')"
)
NODE_EXISTS = (
    'import sd\nfrom PySide6.QtWidgets import QApplication\n'
    'for _ in range(20):\n    QApplication.processEvents()\n'
    'g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() '
    "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
    "print('EXISTS=%%s' %% (g.getNodeFromId('%s') is not None))"
)
FACTS = (
    'import sd\nfrom sd.api.apiexception import APIException\nfrom sd.api.sdproperty import SDPropertyCategory\n'
    'g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() '
    "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
    "print('ATOMIC=%%d' %% len(g.getNodeDefinitions()))\n"
    "print('APIEXC_BASE_ONLY=%%s' %% (issubclass(APIException, BaseException) and not issubclass(APIException, Exception)))\n"
    "n=g.getNodeFromId('%s')\nc=n.getPropertyConnections(n.getPropertyFromId('input1', SDPropertyCategory.Input))[0]\n"
    "print('QUERIED_SIDE=%%s' %% (c.getOutputPropertyNode().getIdentifier()=='%s' and "
    "c.getInputPropertyNode().getIdentifier()=='%s' and c.getOutputProperty().getId()=='input1'))"
)
GRAPH_OF = (
    'import sd\ng=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() '
    "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
)
# Computed pixels to compare with a tolerance (two computes of one setting differ by a step or two,
# and raw buffers carry row padding; AGENTS.md): pixels(texture) -> integers, apart(a, b) -> the
# largest difference. Only 8- and 16-bit integer formats, where a tolerance in steps means something
# (REVIEW.md TST-54, TST-56)
PIXELS = (
    'import ctypes, array\n'
    'def pixels(t):\n'
    "    fmt = str(t.getPixelFormat()).split('.')[-1]\n"
    "    if not (fmt.endswith('8') or fmt.endswith('16')):\n"
    "        raise RuntimeError('pixels(): %s is not an 8- or 16-bit integer format' % fmt)\n"
    '    w, h, pitch, bpp = t.getSize().x, t.getSize().y, t.getRowPitch(), t.getBytesPerPixel()\n'
    '    raw = ctypes.string_at(t.getPixelBufferAddress(), pitch * h)\n'
    "    rows = b''.join(raw[y * pitch:y * pitch + w * bpp] for y in range(h))\n"
    "    return array.array('H' if fmt.endswith('16') else 'B', rows)\n"
    'def apart(a, b):\n'
    '    return max(abs(x - y) for x, y in zip(a, b))\n'
)
INHERIT = GRAPH_OF + (
    "from sd.api.sdproperty import SDPropertyCategory\nn=g.getNodeFromId('%s')\n"
    "p=n.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
    "print('INHERIT=%%s VALUE=%%s' %% (n.getPropertyInheritanceMethod(p).name, n.getPropertyValue(p).get()))"
)
# The graph in the editor when the run starts; the graph object is kept so the end of the run can
# check that the very same graph is back in the editor (REVIEW.md TST-5)
CURRENT_GRAPH = (
    'import sd, sys\ng=sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()\n'
    "sys._selftest_user_graph = g\nprint('CURRENT=' + (g.getIdentifier() if g else ''))"
)
# Reopens that graph object, not a graph found by name: two open graphs can share a name
SAME_GRAPH_BACK = (
    'import sd, sys\nfrom PySide6.QtWidgets import QApplication\n'
    "g = sys.__dict__.pop('_selftest_user_graph', None)\napp = sd.getContext().getSDApplication()\n"
    'if g is not None:\n    app.getUIMgr().openResourceInEditor(g)\n    QApplication.processEvents()\n'
    'cur = app.getQtForPythonUIMgr().getCurrentGraph()\n'
    'same = cur is not None and g is not None and cur.getPackage().getUID() == g.getPackage().getUID() '
    'and cur.getIdentifier() == g.getIdentifier()\n'
    "print('SAME=%s current=%s' % (same, cur.getIdentifier() if cur else None))"
)


def crash_dumps() -> set[str]:
    """Designer's crash dumps (Crashpad's completed reports), as a set of paths; empty where none
    are found."""
    if sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support/Adobe/Adobe Substance 3D Designer')
    else:
        base = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Adobe', 'Adobe Substance 3D Designer')
    folder = os.path.join(base, 'Sentry-Crashpad', 'completed')
    return {os.path.join(folder, f) for f in os.listdir(folder)} if os.path.isdir(folder) else set()


def new_crash_dumps(before: set[str], wait_s: float = 10) -> set[str]:
    """Crash dumps that appear within wait_s seconds (Designer writes one a few seconds after it
    goes down), compared with `before`."""
    deadline = time.time() + wait_s
    while True:
        new = crash_dumps() - before
        if new or time.time() >= deadline:
            return new
        time.sleep(0.5)


def designer_alive() -> bool:
    """True while a Designer process exists (as the server's own check)."""
    if sys.platform == 'win32':
        out = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq Adobe Substance 3D Designer.exe', '/FO', 'CSV', '/NH'],
            capture_output=True,
            text=True,
        ).stdout
        return '"Adobe Substance 3D Designer.exe"' in out
    return (
        subprocess.run(['pgrep', '-f', 'MacOS/Adobe Substance 3D Designer( |$)'], capture_output=True).returncode == 0
    )


STATE: dict[str, bool] = {'was_running': False}  # set by run(): the run used the user's own, already open Designer


class Call(Protocol):
    """ctx.c: one tool call over the run's MCP session, `c(name, args)`."""

    def __call__(self, name: str, args: dict[str, Any] | None = None, /) -> Coroutine[Any, Any, CallToolResult]: ...


class Ctx:
    """What the categories share, in the order they run (__main__.py): set when the run starts, then by
    the category named beside each later one. One not yet set raises AttributeError when read."""

    c: Call  # c(tool name, args): one tool call
    s: ClientSession
    scratch: str  # the run's temporary folder
    helper_source: str  # the Designer helpers, sent ahead of snippets that call them
    was_running: bool  # the user's own Designer was already running
    G: dict[str, str]  # graph_edit.create: {'graph': TEST_GRAPH}, the self-test graph
    clouds: str  # graph_edit.create: node ids (clouds -> slope blur -> levels -> output)
    slope: str
    lv: str
    out: str
    COUNT_NODES: str  # graph_edit.create: a snippet printing NODES=<count>
    png: str  # bitmaps.run: the path of the PNG it imported
    sbs: str  # save.run: where the self-test graph was saved
    stats_before: str  # save.run: node_stats of lv, for set_link_display

    def __init__(self, c: Call, s: ClientSession, scratch: str, helper_source: str, was_running: bool) -> None:
        self.c, self.s, self.scratch, self.helper_source, self.was_running = c, s, scratch, helper_source, was_running


async def cancel_from_second_client() -> str:
    await asyncio.sleep(2)
    async with stdio_client(PARAMS) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        return text(await s.call_tool('cancel_designer_job', {}))


async def libs(c: Call) -> tuple[list[str] | None, str]:
    """(the library packages loaded now, '') or (None, the bridge's answer) on an error."""
    t = text(await c('execute_designer_code', {'code': LIBRARY_PACKAGES}))
    m = re.search(r'LIBS=(.*)', t)
    return ([l for l in m.group(1).strip().split('|') if l], '') if m else (None, t)


async def editor_graph(c: Call) -> str:
    """The identifier of the graph in the editor when the run starts ('' if none), or '' and a failed
    check if the bridge answers with an error, so the run goes on to its summary (REVIEW.md TST-59)."""
    t = text(await c('execute_designer_code', {'code': CURRENT_GRAPH}))
    m = re.search(r'CURRENT=(.*)', t)
    if m is None:
        check('self-test', 'reads the graph in the editor at the start', False, t)
    return m.group(1).strip() if m else ''


async def library_packages(c: Call) -> list[str] | None:
    """The library packages loaded when the run starts, or None (a failed check) if the bridge
    answers with an error, so the run goes on to its summary and clean-up (REVIEW.md TST-51)."""
    found, error = await libs(c)
    if found is None:
        check('self-test', 'reads the library packages loaded at the start', False, error)
    return found


async def restore_library_packages(c: Call, libs_before: list[str] | None) -> None:
    """Unloads the library packages the run loaded and checks the user's are still there. A bridge
    error is a failed check, so the rest of the clean-up still runs (REVIEW.md TST-33)."""
    if libs_before is None:
        skip(
            'self-test',
            'leaves the library packages loaded as it found them',
            'the list at the start could not be read',
        )
        return
    loaded, error = await libs(c)
    if loaded is not None:
        await c('execute_designer_code', {'code': UNLOAD_LIBRARY_PACKAGES % libs_before})
        after, error = await libs(c)
    if loaded is None or after is None:
        check('self-test', 'leaves the library packages loaded as it found them', False, error)
        return
    check(
        'self-test',
        'leaves the library packages loaded as it found them',
        after == libs_before,
        'the run had loaded %d more; before %d, after %d: %s'
        % (
            len([l for l in loaded if l not in libs_before]),
            len(libs_before),
            len(after),
            sorted(set(after) ^ set(libs_before))[:4],
        ),
    )


def summarize(tools: list[str], results: dict[str, list[bool]], skipped: list[tuple[str, str]]) -> tuple[str, bool]:
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
    lines = [
        '%d/%d tools covered%s%s'
        % (
            len(covered),
            len(tools),
            ('; only skipped: %s' % only_skipped) if only_skipped else '',
            ('; NOT covered: %s' % missing) if missing else '',
        ),
        'checks passed: %d/%d; skipped: %d; tools with failures: %s'
        % (passed, total, len(skipped), ', '.join(failed) or 'none'),
    ]
    return '\n'.join(lines), not failed and not missing
