"""What the tools share: configuration, the MCP server and its tool decorator (with the
gate on the guide), the bridge to the plugin inside Designer, and the helpers' calls."""

import functools
import hashlib
import hmac
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
from collections.abc import Callable
from textwrap import dedent
from typing import Any, ParamSpec, TypedDict, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

PORT = int(os.environ.get('SD_BRIDGE_PORT', '9877'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from project_constants import BRIDGE_PROTOCOL, DESIGNER_PROCESS, NONCE, PLUGIN, QUEUE_WAIT, TOKEN_FILE  # noqa: E402  (the plugin's name lives there)

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
GUIDE_MD = os.path.join(HERE, 'GUIDE.md')
sys.path.insert(0, HERE)  # designer_helpers/, a folder of parts joined into one script
from designer_helpers import source as _helpers_source  # noqa: E402

HELPERS = _helpers_source()


def _agent_guide(part: str | None = None) -> str:
    """The guide file, whole or its 'core' or 'scripting' part: the file's level-1 Scripting heading divides them.
    Raises ToolError if it can't be read, as a guide that wasn't read must not count as read."""
    restore = 'mcp_server/GUIDE.md %s: restore it (git checkout), then call get_guide again.'
    try:
        with open(GUIDE_MD, encoding='utf-8') as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        raise ToolError(restore % "can't be read") from e
    heading = re.search(r'(?m)^# Scripting.*$', text)
    core = text[: heading.start()] if heading else text
    if not core.strip():
        raise ToolError(restore % 'has no core')
    if part is None:
        return text
    if part == 'core':
        return core.rstrip('\n') + '\n'
    if heading is None or not text[heading.end() :].strip():
        raise ToolError(restore % 'has no scripting part')
    return text[heading.start() :]


# Claude Code cuts a server's instructions at 4,096 characters (measured: the guide arrived cut
# there), so the instructions only point to get_guide(), whose result arrives in full. Claude Code
# starts this server with every session, so the guide is read on first use: a session started for
# other work never loads it.
INSTRUCTIONS = (
    "Tools for driving the user's Adobe Substance 3D Designer. Do not call get_guide() or any other "
    'tool from this server unless the user asks for work in Designer. Right before your first '
    'Designer tool call in this session, call get_guide() and read the whole result: it is the core '
    "of the guide, with the rules that protect the user's work (Undo, the bridge token, "
    'quitting Designer, snapshots) and the first sd pitfalls. Then tell the user in one line that you '
    'have read the Designer guide, and continue (if Designer is not running, ask the user to open it). '
    "Before writing raw sd or Qt code, also call get_guide('scripting'), read the whole result, then "
    'tell the user in one line that you have read the scripting part.'
)
GUIDE_NOT_READ = (
    'Not run: the Designer guide has not been read in this session. Call get_guide() and '
    "read it first: it has the rules that protect the user's work."
)
SCRIPTING_NOT_READ = (
    "Not run: the scripting part of the Designer guide has not been read in this session. Call get_guide('scripting') "
    'and read it first: it has the sd API and Designer UI pitfalls.'
)


def _designer_data_dir(home: str | None = None) -> str:
    """Where Designer keeps its log, settings and crash dumps: in the user's home, or, given `home`, in that one: the
    home of its own launch_designer gives a Designer it starts on macOS."""
    if sys.platform == 'darwin':
        base = os.path.join(home or os.path.expanduser('~'), 'Library', 'Application Support')
    elif sys.platform == 'win32':
        base = os.environ.get('LOCALAPPDATA', '')
    else:
        base = os.path.expanduser('~/.local/share')
    return os.path.join(base, 'Adobe', 'Adobe Substance 3D Designer')


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
    return subprocess.run(['pgrep', '-f', DESIGNER_PROCESS], capture_output=True).returncode == 0


server = MCPServer(name='substance-designer', instructions=INSTRUCTIONS)
_session: dict[str, bool] = {
    'guide_read': False,
    'scripting_read': False,
}  # one server process per client session (stdio)


P = ParamSpec('P')
R = TypeVar('R')


def _tool(scripting: bool = False, gated: bool = True) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """server.tool(), refusing to run until the guide was read: any tool until get_guide() was called and, with
    `scripting`, a tool that runs code the caller wrote until get_guide('scripting') was too, so that nothing reaches
    Designer first. `gated=False` for a tool that must always work."""
    register = server.tool()

    def decorate(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if gated:
                missing = [] if _session['guide_read'] else [GUIDE_NOT_READ]
                if scripting and not _session['scripting_read']:
                    missing.append(SCRIPTING_NOT_READ)
                if missing:
                    raise ToolError(' '.join(missing))
            return fn(*args, **kwargs)

        return register(wrapper)

    return decorate


def _output_note_in(text: str) -> str | None:
    """The helpers' line saying which of several outputs was taken, when none was named (REVIEW.md HLP-65)."""
    found = re.search(r'^no output given: .*$', text, re.M)
    return found.group(0) if found else None


def _with_undo(code: str, label: str) -> str:
    # Group everything the script does into one undo step in Designer
    return dedent("""\
        from sd.api.sdhistoryutils import SDHistoryUtils as _SDH
        with _SDH.UndoGroup(%r):
            exec(compile(%r, __file__, "exec"), globals())
    """) % (label, code)


def _helpers_call(call: str) -> str:
    return HELPERS + '\n\n' + call + '\n'


OTHER_PROTOCOL = (
    'The %s plugin in Designer speaks another bridge protocol than this server (they are different versions); '
    'nothing was sent. Re-run install.py, then restart Designer: quit_designer and launch_designer for one an agent '
    "started; the user's, ask them to save, close and reopen it. If the server is the older one, the user reconnects "
    '/mcp.' % PLUGIN
)


class _Refused(ToolError):
    """A Designer's plugin answered, but refused the request (its reply's ok is false, e.g. 'invalid token') or speaks
    another bridge protocol: starting or waiting for another Designer wouldn't help."""


def bridge_answer(token: str, nonce: str, port: int, body: bytes) -> bytes:
    """The answer to the plugin's greeting (plugin docstring): HMAC(token) over the nonce, the port connected to and
    the request's bytes as sent, so it can't be passed on to a plugin on another port or with another request
    (REVIEW.md SRV-82, PLG-32)."""
    message = b'%s\n%d\n' % (nonce.encode('ascii'), port) + body
    return hmac.new(token.encode('utf-8'), message, hashlib.sha256).hexdigest().encode('ascii')


def _exchange(sock: socket.socket, token: str, request: dict[str, Any], port: int) -> bytes:
    """The bridge protocol (plugin docstring): read the greeting, send the answer (an HMAC of the nonce, the port and
    the request's bytes) on a line before those bytes, instead of the token itself, and return the raw reply bytes. A
    greeting of another protocol gets nothing."""
    hello = b''
    while not hello.endswith(b'\n'):
        chunk = sock.recv(1024)
        if not chunk:
            raise ConnectionResetError('closed before the greeting')
        hello += chunk
    greeting = json.loads(hello.decode('utf-8'))
    if not isinstance(greeting, dict):
        raise ValueError("not the bridge's greeting")
    # the protocol first: another one's greeting may hold no nonce (REVIEW.md SRV-88)
    if greeting.get('protocol') != BRIDGE_PROTOCOL:
        if 'protocol' not in greeting and 'nonce' not in greeting:  # no bridge's, of any version (REVIEW.md SRV-95)
            raise ValueError("not the bridge's greeting")
        raise _Refused(OTHER_PROTOCOL)  # a Designer answering (REVIEW.md SRV-85)
    nonce = greeting['nonce']
    if not isinstance(nonce, str) or not NONCE.fullmatch(nonce):  # nothing signed with it (REVIEW.md SRV-94)
        raise ValueError("not the bridge's greeting")
    body = json.dumps({key: value for key, value in request.items() if key != 'auth'}).encode('utf-8')
    sock.sendall(bridge_answer(token, nonce, port, body) + b'\n' + body)
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


def _send(request: dict[str, Any], wait: float, port: int | None = None) -> Reply:
    """Send one JSON request to the plugin on `port` (this server's PORT by default) and return its reply dict."""
    try:
        with open(TOKEN_FILE) as f:
            token = f.read().strip()
    except FileNotFoundError as e:
        raise ToolError('No bridge token found. Is the %s plugin loaded in Designer?' % PLUGIN) from e
    try:
        port = PORT if port is None else port
        with socket.create_connection(('127.0.0.1', port), timeout=wait) as s:
            data = _exchange(s, token, request, port)
    except ConnectionRefusedError as e:
        raise ToolError(
            'Designer is not reachable: if it is closed, ask the user to open it (the %s plugin loads on startup).'
            % PLUGIN
        ) from e
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


def _control(cmd: str, wait: float, port: int | None = None) -> str:
    """A control request ('status', 'cancel') and its output; a refusal raises _Refused with the
    plugin's error instead of reading as an answer (REVIEW.md SRV-33)."""
    reply = _send({'cmd': cmd}, wait=wait, port=port)
    if not reply.get('ok'):
        raise _Refused('Designer refused the %r request: %s' % (cmd, reply.get('error') or 'no reason given'))
    return reply.get('output', '')


def _bridge(
    code: str, path: str | None = None, timeout: float | None = None, wait: float | None = None, port: int | None = None
) -> str:
    # timeout: seconds before the plugin aborts the script (None = no limit)
    # wait: seconds to wait for a reply, for a job that may start late or not at all (None = as long as it may take)
    # port: the plugin's port (None = this server's PORT; launch_designer, designer_status and quit_designer take one)
    request: dict[str, Any] = {'code': code, 'path': path}
    if timeout:
        request['timeout'] = timeout
    # wait for the plugin's queue and the script itself, or a job we gave up on could start later
    reply = _send(request, wait=QUEUE_WAIT + (timeout or 900) + 60 if wait is None else wait, port=port)
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


def _sentence(text: str) -> str:
    """`text` ending in one stop: its own (. ? !), or a period: for a message a sentence of the caller's goes on after
    (REVIEW.md SRV-114, SRV-117)."""
    return text if text.endswith(('.', '?', '!')) else text + '.'


def _checked(text: str) -> str:
    # Turn a Designer-side traceback into a clean tool error
    if '--- ERROR ---' in text:
        raise ToolError(text.strip().splitlines()[-1])
    return text
