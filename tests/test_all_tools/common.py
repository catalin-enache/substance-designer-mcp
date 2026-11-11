"""What every category of the live self-test shares (each in a folder of its own: categories.py): the check/skip record, the MCP and bridge helpers,
the code snippets sent to Designer, and the summary. The run itself is in __main__.py."""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Awaitable, Callable, Coroutine, Sequence
from textwrap import dedent
from typing import Any, Protocol

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult

BUNDLE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BUNDLE)
from project_constants import (  # noqa: E402 (after the sys.path entry; `X as X` re-exports them)
    DESIGNER_PROCESS,
    PLUGIN as PLUGIN,
    PLUGIN_PACKAGE_DIR as PLUGIN_PACKAGE_DIR,
    QUIT_FORCED_IN_SHUTDOWN as QUIT_FORCED_IN_SHUTDOWN,
    QUIT_SAMPLED as QUIT_SAMPLED,
    SHORT_TEMP as SHORT_TEMP,  # where launch_designer makes the folders of a Designer it starts
    TOKEN_FILE as TOKEN_FILE,
    agent_designer_file,
    agent_folder_name,
)

sys.path.insert(0, os.path.join(BUNDLE, 'mcp_server'))
import designer_helpers  # noqa: E402
from test_all_tools.crash_watch import CrashWatch  # noqa: E402  (lifecycle's, kept on its Ctx)

helpers_source = designer_helpers.source  # the helpers as sent to Designer (used by the categories)
SERVER = os.path.join(BUNDLE, 'mcp_server', 'server.py')
TEST_GRAPH = 'mcp_selftest'
SAVED_GRAPH = 'mcp_selftest_saved'  # create_graph(save_path=...)
DUP_GRAPH = 'mcp_selftest_dup'  # two open graphs with the same identifier
EXAMPLE_GRAPH = 'mcp_selftest_trimsheet'  # examples/build_dwarf_trimsheet.py, renamed
PORT = int(os.environ.get('SD_BRIDGE_PORT', '9877'))
# this process's whole environment: stdio_client passes a minimal one otherwise, without SD_BRIDGE_PORT, and the
# server would listen for another port than PORT (REVIEW.md TST-153)
PARAMS = StdioServerParameters(command=sys.executable, args=[SERVER], env=dict(os.environ))

results: dict[str, list[bool]] = {}
skipped: list[tuple[str, str]] = []
times: dict[str, float] = {}  # seconds each category took: __main__.py's run_steps


def check(tool: str, name: str, ok: object, detail: str = '') -> None:
    ok = bool(ok)  # a condition like `refs and not missing` may be [] or None (REVIEW.md TST-29)
    results.setdefault(tool, []).append(ok)
    print('%s  %-22s %s | %s' % ('PASS' if ok else 'FAIL', tool, name, detail.strip()[:150].replace('\n', ' / ')))


def skip(tool: str, name: str, why: str) -> None:
    results.setdefault(tool, [])
    skipped.append((tool, name))
    print('SKIP  %-22s %s | %s' % (tool, name, why))


forced_in_shutdown: list[str] = []  # this process's normal closes forced during their shutdown, for the pool to count


def normal_close(t: str, what: str) -> bool:
    """closed_by_quit, for a check of a normal close (`what`), when the check reaches it: a quit forced during its
    shutdown is recorded, reported to the pool (its count, its folder kept: REVIEW.md TST-293), and any forced quit
    printed whole, as a check's detail is cut."""
    if 'forced' in t:
        print('      %s, its quit whole: %s' % (what, ' / '.join(t.strip().splitlines())))
    if QUIT_FORCED_IN_SHUTDOWN in t:
        forced_in_shutdown.append(what)
    return closed_by_quit(t)


def closed_by_quit(t: str) -> bool:
    """quit_designer's reply `t` says Designer quit with its close taken: not forced, or forced during its own shutdown,
    every window closed (it can hang there: server_tools/lifecycle.py, Quitting; DECISIONS.md, Bridge and quitting)."""
    return 'Designer quit after' in t and ('forced' not in t or QUIT_FORCED_IN_SHUTDOWN in t)


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


def read_greeting(sock: socket.socket) -> bytes:
    """The bridge's greeting line, as it came; ConnectionResetError when the connection closes before its end, where
    adding recv()'s b'' forever would spin (REVIEW.md TST-176). The one loop for the tests' greetings."""
    hello = b''
    while not hello.endswith(b'\n'):
        chunk = sock.recv(1024)
        if not chunk:
            raise ConnectionResetError('closed before the greeting')
        hello += chunk
    return hello


def raw_request(request: dict[str, Any] | bytes, token: str | None = None, signed: bytes | None = None) -> Any:
    """One request straight to the bridge, bypassing the MCP server: a dict as JSON, bytes as they are. With token,
    it answers the plugin's challenge properly (the plugin's docstring: an HMAC of the nonce, the port and the bytes
    sent, on a line before them), over `signed` instead of the bytes sent when given (a request changed after
    signing); without, the request is sent alone, as clients of the older protocols sent it."""
    body = request if isinstance(request, bytes) else json.dumps(request).encode('utf-8')
    with socket.create_connection(('127.0.0.1', PORT), timeout=10) as sock:
        hello = read_greeting(sock)
        nonce = json.loads(hello)['nonce']
        if token:
            message = b'%s\n%d\n' % (nonce.encode(), PORT) + (body if signed is None else signed)
            body = hmac.new(token.encode(), message, hashlib.sha256).hexdigest().encode() + b'\n' + body
        sock.sendall(body)
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


def clipboard_text() -> bytes:
    """The text on the clipboard (macOS: pbpaste), never printed; b'' if it holds none."""
    return subprocess.run(['pbpaste'], capture_output=True, check=True).stdout


def set_clipboard_text(data: bytes) -> None:
    """The clipboard made this text alone (macOS: pbcopy): whatever else it held is gone."""
    subprocess.run(['pbcopy'], input=data, check=True)


# Designer's library packages loaded right now (their paths), so the run can unload the ones it
# loaded itself (describe_node, add ops of library graphs) and leave the user's (REVIEW.md TST-30)
LIBRARY_PACKAGES = dedent("""\
    import os, sd
    from sd.api.sdapplication import SDApplicationPath
    app = sd.getContext().getSDApplication()
    lib = os.path.normcase(os.path.join(app.getPath(SDApplicationPath.DefaultResourcesDir), 'packages'))
    print('LIBS=' + '|'.join(sorted(p.getFilePath() for p in app.getPackageMgr().getUserPackages()
                                    if os.path.normcase(p.getFilePath() or '').startswith(lib))))""")
UNLOAD_LIBRARY_PACKAGES = dedent("""\
    import os, sd
    from sd.api.sdapplication import SDApplicationPath
    app = sd.getContext().getSDApplication()
    keep = set(%r)
    lib = os.path.normcase(os.path.join(app.getPath(SDApplicationPath.DefaultResourcesDir), 'packages'))
    for p in list(app.getPackageMgr().getUserPackages()):
        path = p.getFilePath() or ''
        if os.path.normcase(path).startswith(lib) and path not in keep:
            app.getPackageMgr().unloadUserPackage(p)
""")
# Every graph the self-test creates is named mcp_selftest...: this closes them all
CLEAN = dedent("""\
    import sd
    pm=sd.getContext().getSDApplication().getPackageMgr()
    n=0
    for p in list(pm.getUserPackages()):
        if any(r.getIdentifier().startswith('mcp_selftest') for r in p.getChildrenResources(False)):
            pm.unloadUserPackage(p); n+=1
    print('removed', n)""")
# Undo/Redo via Designer's Edit menu, scheduled to run after this call's own undo group closes
UNDO_REDO = dedent("""\
    import sd
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMenu
    g=sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()
    if g is None or g.getIdentifier()!='%s':
        print('NOT_FOCUSED')
    else:
        acts=[a for w in QApplication.instance().allWidgets() if isinstance(w, QMenu) and w.title()=='&Edit'
              for a in w.actions() if a.text()=='%s' and a.isEnabled()]
        if acts:
            # in a Designer just started, with another Designer in front, Undo of an output's fields sometimes did
            # nothing without this (8 in 8 beside one idle Designer, 3 pool runs in 4, 1 in 3 in scratch runs; with it 4 in 4); it leaves the other
            # app in front (GUIDE.md, Undo)
            mw=sd.getContext().getSDApplication().getQtForPythonUIMgr().getMainWindow()
            mw.raise_()
            mw.activateWindow()
            QTimer.singleShot(0, acts[0].trigger)
            print('SCHEDULED')
        else:
            print('NO_ACTION')""")
# The start of a short snippet: finds the graph with this identifier as g
GRAPH_OF = dedent("""\
    import sd
    g = [r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier() == '%s'][0]
""")
NODE_EXISTS = dedent("""\
    import sd
    from PySide6.QtWidgets import QApplication
    for _ in range(20):
        QApplication.processEvents()
    g=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]
    print('EXISTS=%%s' %% (g.getNodeFromId('%s') is not None))""")
# The graph in the editor when the run starts; the graph object is kept so the end of the run can
# check that the very same graph is back in the editor (REVIEW.md TST-5)
CURRENT_GRAPH = dedent("""\
    import sd, sys
    g=sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()
    sys._selftest_user_graph = g
    print('CURRENT=' + (g.getIdentifier() if g else ''))""")
# The graph in the editor now, for a check: nothing kept, as the run's start keeps the user's (REVIEW.md TST-271)
GRAPH_IN_EDITOR = dedent("""\
    import sd
    g=sd.getContext().getSDApplication().getQtForPythonUIMgr().getCurrentGraph()
    print('CURRENT=' + (g.getIdentifier() if g else ''))""")
# Reopens that graph object, not a graph found by name: two open graphs can share a name
SAME_GRAPH_BACK = dedent("""\
    import sd, sys
    from PySide6.QtWidgets import QApplication
    g = sys.__dict__.pop('_selftest_user_graph', None)
    app = sd.getContext().getSDApplication()
    if g is not None:
        app.getUIMgr().openResourceInEditor(g)
        QApplication.processEvents()
    cur = app.getQtForPythonUIMgr().getCurrentGraph()
    same = cur is not None and g is not None and cur.getPackage().getUID() == g.getPackage().getUID() and cur.getIdentifier() == g.getIdentifier()
    print('SAME=%s current=%s' % (same, cur.getIdentifier() if cur else None))""")


def agent_folder(port: int) -> str:
    """The folder launch_designer makes for the Designer it starts on `port` (its temp folder and home inside)."""
    return os.path.join(SHORT_TEMP, agent_folder_name(port))


def crash_dumps(ports: Sequence[int] = (), run_port: bool = True) -> set[str]:
    """Designer's crash dumps (Crashpad's completed reports), as a set of paths; empty where none
    are found. On macOS also those in the homes of this run's Designers (agent_folder(port)/home, where they write
    theirs): on PORT (unless run_port is False: the pool's parent has no Designer there, REVIEW.md TST-280) and on
    `ports`, never another run's beside it (REVIEW.md TST-155)."""
    if sys.platform == 'darwin':
        bases = [os.path.expanduser('~/Library/Application Support/Adobe/Adobe Substance 3D Designer')]
        homes = [os.path.join(agent_folder(port), 'home') for port in ((PORT,) if run_port else ()) + tuple(ports)]
        bases += [
            os.path.join(home, 'Library', 'Application Support', 'Adobe', 'Adobe Substance 3D Designer')
            for home in homes
        ]
    else:
        bases = [os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Adobe', 'Adobe Substance 3D Designer')]
    dumps: set[str] = set()
    for base in bases:
        folder = os.path.join(base, 'Sentry-Crashpad', 'completed')
        if os.path.isdir(folder):
            dumps |= {os.path.join(folder, f) for f in os.listdir(folder)}
    return dumps


def new_crash_dumps(before: set[str], wait_s: float = 10, ports: Sequence[int] = ()) -> set[str]:
    """Crash dumps (crash_dumps(ports)) that appear within wait_s seconds (Designer writes one a few seconds after it
    goes down), compared with `before`."""
    deadline = time.time() + wait_s
    while True:
        new = crash_dumps(ports) - before
        if new or time.time() >= deadline:
            return new
        time.sleep(0.5)


def end_own_designer() -> None:
    """After a run that failed before its quit checks: the Designer the self-test started is disposable."""
    try:
        with open(agent_designer_file(PORT), encoding='utf-8') as f:
            record = json.load(f)
        pid, start = int(record['pid']), record['start']
        from server_tools.lifecycle import (
            _process_start,
        )  # the server's reading, which wrote the record (REVIEW.md SRV-92)

        if _process_start(pid) == start:
            os.kill(pid, signal.SIGTERM)
            time.sleep(5)
            if pid in designer_pids():  # its own, not any Designer: another run's may be up (REVIEW.md TST-170)
                os.kill(pid, signal.SIGKILL)
            print('ended the Designer this run started and left open:', pid)
    except Exception as e:  # a clean-up in main()'s finally: a line, not a traceback (the server's ToolError too)
        print('could not end a Designer this run left open:', e)


class NoListing(OSError):
    """Designer's processes couldn't be listed (pgrep failing or missing): not the same as none running (REVIEW.md
    INS-27; the server's _NoListing)."""


def _pgrep() -> 'subprocess.CompletedProcess[str]':
    """pgrep for Designer's process, as the server looks for it (project_constants.DESIGNER_PROCESS); NoListing when
    it fails (exit code 2 or 3; 1 is nothing found)."""
    try:
        done = subprocess.run(['pgrep', '-f', DESIGNER_PROCESS], capture_output=True, text=True)
    except OSError as e:
        raise NoListing("Designer's processes couldn't be listed: %s" % e) from e
    if done.returncode not in (0, 1):
        raise NoListing(
            "Designer's processes couldn't be listed (pgrep exit code %d: %s)" % (done.returncode, done.stderr.strip())
        )
    return done


def designer_pids() -> list[int]:
    """Designer's processes (as the server's own list; none on Windows). NoListing when they can't be listed."""
    if sys.platform == 'win32':
        return []
    return [int(pid) for pid in _pgrep().stdout.split()]


def free_port() -> int:
    """A TCP port nothing on this machine listens on now."""
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port: int = s.getsockname()[1]
    return port


def agents_designers() -> dict[int, int]:
    """{port: process ID} of the Designers an agent started that still run, as the server sees them (its records)."""
    from server_tools.lifecycle import _agents

    return _agents()


def users_designer_running() -> bool:
    """Whether a Designer runs that no agent's record names, on any port: the user's, or one still starting. Another
    run's, on its own port, isn't one (REVIEW.md TST-170). On Windows nothing is recorded: any Designer counts."""
    if sys.platform == 'win32':
        return designer_alive()
    agents = set(agents_designers().values())
    return any(pid not in agents for pid in designer_pids())


def designer_here() -> bool:
    """Whether a Designer runs that may be on this run's port (PORT): this run's, the user's, or one still starting;
    not another run's, recorded on its own port (REVIEW.md TST-170). On Windows, any Designer."""
    if sys.platform == 'win32':
        return designer_alive()
    elsewhere = {pid for port, pid in agents_designers().items() if port != PORT}
    return any(pid not in elsewhere for pid in designer_pids())


def designer_alive() -> bool:
    """True while a Designer process exists, on any port (as the server's own check). NoListing when pgrep fails."""
    if sys.platform == 'win32':
        out = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq Adobe Substance 3D Designer.exe', '/FO', 'CSV', '/NH'],
            capture_output=True,
            text=True,
        ).stdout
        return '"Adobe Substance 3D Designer.exe"' in out
    return _pgrep().returncode == 0


STATE: dict[str, bool] = {'was_running': False}  # set by run(): the run used the user's own, already open Designer


class Call(Protocol):
    """ctx.c: one tool call over the run's MCP session, `c(name, args)`."""

    def __call__(self, name: str, args: dict[str, Any] | None = None, /) -> Coroutine[Any, Any, CallToolResult]: ...


Step = Callable[['Ctx'], Awaitable[None]]  # a category's run(ctx), one of its checks, or its prepare(ctx)


async def designer_script(c: Call, name: str, /, **args: Any) -> CallToolResult:
    """Run a Designer script, name being '<category>/<script>' for <category>/designer_scripts/<script>.py, the folder
    of the category that runs it, or 'shared/<script>' for designer_scripts/shared/<script>.py, one that several run:
    Python with real logic lives in real files, which ruff and mypy check (the live-check skill).
    The keywords reach it as its ARGS. A script that raises is a failed check here, whatever the caller reads from the
    result: a traceback shows the failing source line, output token included, and a tool returns a script's error as
    normal text."""
    path = script_path(name)
    result = await c('run_designer_script', {'path': path, 'timeout_s': 120, 'args': args})
    if result.is_error or '--- ERROR ---' in text(result):
        print(text(result))  # a setup script discards its result: this is the only place the error shows
        check('run_designer_script', 'script %s ran' % name, False, text(result).strip().splitlines()[-1])
    return result


def script_path(name: str) -> str:
    """The file of designer_script's `name`: '<category>/<script>' or 'shared/<script>'."""
    owner, script = name.split('/')
    here = os.path.dirname(os.path.abspath(__file__))
    folder = (
        os.path.join(here, 'designer_scripts', 'shared')
        if owner == 'shared'
        else os.path.join(here, owner, 'designer_scripts')
    )
    return os.path.join(folder, script + '.py')


class Ctx:
    """What one category runs on (category_run.py): the run's session and folder, set when the run starts, and what
    the category's own preparation (<category>/preparations.py) sets for its checks. Each category gets a fresh one
    (fresh()), so none reads what another prepared; one not set raises AttributeError when read."""

    c: Call  # c(tool name, args): one tool call
    s: ClientSession
    scratch: str  # the category's temporary folder, in the run's
    helper_source: str  # the Designer helpers, sent ahead of snippets that call them
    was_running: bool  # the user's own Designer was already running
    # set by a category's preparation, for its checks: the names they read
    G: dict[str, str]  # {'graph': TEST_GRAPH}, the self-test graph
    clouds: str  # node ids (clouds -> slope blur -> levels -> output)
    slope: str
    lv: str
    out: str
    png: str  # the path of a PNG the preparation wrote
    sbs: str  # where the self-test graph was saved
    stats_before: str  # node_stats of lv, before set_link_display

    def __init__(self, c: Call, s: ClientSession, scratch: str, helper_source: str, was_running: bool) -> None:
        self.c, self.s, self.scratch, self.helper_source, self.was_running = c, s, scratch, helper_source, was_running
        self.crash_watch: CrashWatch | None = None  # crash_watch.watching_crashes

    def fresh(self, category: str) -> 'Ctx':
        """A Ctx for one category: the run's session and Designer, a scratch folder of its own, nothing prepared."""
        scratch = os.path.join(self.scratch, category)
        os.makedirs(scratch, exist_ok=True)
        return Ctx(c=self.c, s=self.s, scratch=scratch, helper_source=self.helper_source, was_running=self.was_running)


class Unprepared(Exception):
    """A category's preparation couldn't build its environment: its checks don't run (category_run.py)."""


async def prepared_call(c: Call, name: str, args: dict[str, Any] | None = None) -> str:
    """A tool call of a preparation: its text, or Unprepared if it failed (an error result, or a Designer script's
    traceback), so a preparation records no check of its own."""
    result = await c(name, args or {})
    t = text(result)
    if result.is_error or '--- ERROR ---' in t:
        last = t.strip().splitlines()[-1] if t.strip() else 'no answer'
        raise Unprepared('%s: %s' % (name, last))
    return t


def remove_test_snapshots() -> None:
    """The self-test graph's snapshots (snapshot_graph's folder for TEST_GRAPH), none other."""
    root = os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), '.sd_mcp', 'snapshots')
    shutil.rmtree(os.path.join(root, TEST_GRAPH), ignore_errors=True)


def refs(t: str) -> dict[str, str]:
    """apply_edits' result -> {ref: the id of the node added under it}."""
    return dict(re.findall(r"^\s*ref '(\w+)' = (\d+)", t, re.M))


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


async def graph_in_editor(c: Call) -> str:
    """The identifier of the graph in the editor now ('' if none or if the bridge answers with an error), for a check:
    unlike editor_graph, it keeps nothing."""
    m = re.search(r'CURRENT=(.*)', text(await c('execute_designer_code', {'code': GRAPH_IN_EDITOR})))
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


def summarize(
    tools: list[str],
    results: dict[str, list[bool]],
    skipped: list[tuple[str, str]],
    times: dict[str, float] | None = None,
) -> tuple[str, bool]:
    """(summary text, ok). A tool counts as covered only with at least one check that ran; one
    whose checks were all skipped (quit_designer on Windows) is listed, and
    doesn't fail the run. Missing tools and failed checks do. `times`, the seconds per category, are listed slowest
    first."""
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
    if times:
        lines.append('time per category, slowest first (total %.1f s):' % sum(times.values()))
        lines += ['%7.1f s  %s' % (seconds, name) for name, seconds in sorted(times.items(), key=lambda t: -t[1])]
    return '\n'.join(lines), not failed and not missing
