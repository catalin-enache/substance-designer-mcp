"""What the tools share: configuration, the MCP server and its tool decorator (with the
guide reminder), the bridge to the plugin inside Designer, and the helpers' calls."""

import functools
import hashlib
import hmac
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
from collections.abc import Callable
from typing import Any, ParamSpec, TypedDict, TypeVar, cast

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

PORT = int(os.environ.get('SD_BRIDGE_PORT', '9877'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from project_constants import PLUGIN, QUEUE_WAIT, TOKEN_FILE  # noqa: E402  (the plugin's name lives there)

# Folder holding sbscooker / sbsrender. Override with SD_DESIGNER_BIN_DIR.
DEFAULT_BIN_DIRS = {
    'darwin': ['/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app/Contents/MacOS'],
    'win32': [r'C:\Program Files\Adobe\Adobe Substance 3D Designer'],
}
EXE = '.exe' if sys.platform == 'win32' else ''


def _find_tool(name: str) -> str | None:
    dirs = [os.environ['SD_DESIGNER_BIN_DIR']] if os.environ.get('SD_DESIGNER_BIN_DIR') else []
    dirs += DEFAULT_BIN_DIRS.get(sys.platform, [])
    for d in dirs:
        path = os.path.join(d, name + EXE)
        if os.path.isfile(path):
            return path
    return shutil.which(name)


SBSCOOKER = _find_tool('sbscooker')
SBSRENDER = _find_tool('sbsrender')

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # mcp_server/
AGENTS_MD = os.path.join(os.path.dirname(HERE), 'AGENTS.md')
sys.path.insert(0, HERE)  # designer_helpers/, a folder of parts joined into one script
from designer_helpers import source as _helpers_source  # noqa: E402

HELPERS = _helpers_source()


def _agent_guide() -> str:
    try:
        with open(AGENTS_MD, encoding='utf-8') as f:
            return f.read()
    except OSError:
        return 'AGENTS.md not found next to mcp_server/.'


# Claude Code cuts a server's instructions at 4,096 characters (measured: AGENTS.md arrived cut
# there), so the instructions only point to get_guide(), whose result arrives in full. Claude Code
# starts this server with every session, so the guide is read on first use: a session started for
# other work never loads it.
INSTRUCTIONS = (
    "Tools for driving the user's Adobe Substance 3D Designer. Do not call get_guide() or any other "
    'tool from this server unless the user asks for work in Designer. Right before your first '
    'Designer tool call in this session, call get_guide() and read the whole result: it is the full '
    "guide (AGENTS.md), with the rules that protect the user's work (Undo, the bridge token, "
    'quitting Designer, snapshots) and the sd API pitfalls. Then tell the user in one line that you '
    'have read the Designer guide, and continue (launch_designer starts Designer if it is not running).'
)
GUIDE_NOT_READ = (
    'NOTE: the Designer guide has not been read in this session. Call get_guide() and '
    "read it before going on: it has the rules that protect the user's work."
)


def _designer_running() -> bool:
    """True while a Designer process exists (the bridge port closes before the process exits)."""
    if sys.platform == 'win32':
        # CSV: the default table cuts image names to 25 characters
        out = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq Adobe Substance 3D Designer.exe', '/FO', 'CSV', '/NH'],
            capture_output=True,
            text=True,
        ).stdout
        return '"Adobe Substance 3D Designer.exe"' in out
    return (
        subprocess.run(['pgrep', '-f', 'MacOS/Adobe Substance 3D Designer( |$)'], capture_output=True).returncode == 0
    )


server = MCPServer(name='substance-designer', instructions=INSTRUCTIONS)
_session: dict[str, bool] = {'guide_read': False}  # one server process per client session (stdio)


_nesting = threading.local()

P = ParamSpec('P')
R = TypeVar('R')


def _tool() -> Callable[[Callable[P, R]], Callable[P, R]]:
    """server.tool(), plus a reminder at the top of text results until get_guide() was called."""
    register = server.tool()

    def decorate(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # only the outermost call adds it: a tool that calls another (set_link_display calls
            # snapshot_graph and open_graph) would otherwise paste it twice (REVIEW.md SRV-28)
            # (per thread: tools may run on worker threads side by side)
            _nesting.depth = getattr(_nesting, 'depth', 0) + 1
            try:
                result = fn(*args, **kwargs)
            finally:
                _nesting.depth -= 1
            if not _session['guide_read'] and isinstance(result, str) and not _nesting.depth:
                return cast(R, GUIDE_NOT_READ + '\n\n' + result)
            return result

        return register(wrapper)

    return decorate


def _with_undo(code: str, label: str) -> str:
    # Group everything the script does into one undo step in Designer
    return (
        'from sd.api.sdhistoryutils import SDHistoryUtils as _SDH\n'
        'with _SDH.UndoGroup(%r):\n'
        '    exec(compile(%r, __file__, "exec"), globals())\n' % (label, code)
    )


def _helpers_call(call: str) -> str:
    return HELPERS + '\n\n' + call + '\n'


def _exchange(sock: socket.socket, token: str, request: dict[str, Any]) -> bytes:
    """The bridge protocol (plugin docstring): read the nonce line, answer with
    HMAC(token, nonce) instead of the token itself, return the raw reply bytes."""
    hello = b''
    while not hello.endswith(b'\n'):
        chunk = sock.recv(1024)
        if not chunk:
            raise ConnectionResetError('closed before the greeting')
        hello += chunk
    nonce: str = json.loads(hello.decode('utf-8'))['nonce']
    auth = hmac.new(token.encode('utf-8'), nonce.encode('utf-8'), hashlib.sha256).hexdigest()
    sock.sendall(json.dumps({**request, 'auth': auth}).encode('utf-8'))
    sock.shutdown(socket.SHUT_WR)
    data = b''
    while chunk := sock.recv(65536):
        data += chunk
    return data


class Reply(TypedDict, total=False):
    """The plugin's reply to a request (plugin docstring)."""

    ok: bool
    output: str
    error: str


def _send(request: dict[str, Any], wait: float) -> Reply:
    """Send one JSON request to the plugin and return its reply dict."""
    try:
        with open(TOKEN_FILE) as f:
            token = f.read().strip()
    except FileNotFoundError as e:
        raise ToolError('No bridge token found. Is the %s plugin loaded in Designer?' % PLUGIN) from e
    try:
        with socket.create_connection(('127.0.0.1', PORT), timeout=wait) as s:
            data = _exchange(s, token, request)
    except ConnectionRefusedError as e:
        raise ToolError('Designer is not reachable. Start Designer (the %s plugin loads on startup).' % PLUGIN) from e
    except TimeoutError as e:
        raise ToolError(
            'No reply from Designer after %ds. It may be busy with a long call; '
            'try cancel_designer_job or check Designer.' % wait
        ) from e
    except (OSError, ValueError, KeyError, TypeError) as e:
        # reset mid-quit or mid-start, or something that isn't the bridge on the port (REVIEW.md PLG-23)
        raise ToolError('Designer is not reachable (%s: %s).' % (type(e).__name__, e)) from e
    try:
        reply: Reply = json.loads(data.decode('utf-8'))
        return reply
    except ValueError as e:
        raise ToolError('Designer closed the connection without a reply (it may be starting or quitting).') from e


def _bridge(code: str, path: str | None = None, timeout: float | None = None) -> str:
    # timeout: seconds before the plugin aborts the script (None = no limit)
    request: dict[str, Any] = {'code': code, 'path': path}
    if timeout:
        request['timeout'] = timeout
    # wait for the plugin's queue and the script itself, or a job we gave up on could start later
    reply = _send(request, wait=QUEUE_WAIT + (timeout or 900) + 60)
    text = reply['output']
    if not reply['ok']:
        text += '\n--- ERROR ---\n' + reply['error']
    return text or '(no output)'


def _server_versions() -> str:
    from importlib.metadata import PackageNotFoundError, version

    def of(dist: str) -> str:
        try:
            return version(dist)
        except PackageNotFoundError:
            return '?'

    return 'MCP server: Python %s, mcp %s, pillow %s, numpy %s' % (
        platform.python_version(),
        of('mcp'),
        of('pillow'),
        of('numpy'),
    )


def _local_path(path: str | None) -> str | None:
    """A path as the user meant it: relative to this server's working directory, ~ expanded.
    Designer would resolve a relative path against its own working directory (REVIEW.md SRV-27)."""
    return os.path.abspath(os.path.expanduser(path)) if path else path


def _edit(call: str, label: str) -> str:
    # Quick edits run inside one undo step, like execute_designer_code. The limit only stops a
    # hang: a big apply_edits batch or a first use of many library packages can take minutes
    return _checked(_bridge(_with_undo(HELPERS + '\n\n' + call + '\n', label), '<quick edit>', 300))


def _checked(text: str) -> str:
    # Turn a Designer-side traceback into a clean tool error
    if '--- ERROR ---' in text:
        raise ToolError(text.strip().splitlines()[-1])
    return text
