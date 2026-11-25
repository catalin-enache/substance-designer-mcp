"""What the tools share: configuration, the MCP server and its tool decorator (with the
gate on the guide), the bridge to the plugin inside Designer, and the helpers' calls."""

import functools
import hashlib
import hmac
import inspect
import json
import math
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
from collections.abc import Callable
from textwrap import dedent
from typing import Annotated, Literal, NamedTuple, ParamSpec, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BeforeValidator, Field, JsonValue, WithJsonSchema

PORT = int(os.environ.get('SD_BRIDGE_PORT', '9877'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from project_constants import (  # noqa: E402  (the plugin's name and the bridge's messages live there)
    BRIDGE_PROTOCOL,
    DESIGNER_PROCESS,
    NONCE,
    PLUGIN,
    QUEUE_WAIT,
    ROLLED_BACK,
    TAG_ALPHABET,
    TAG_LENGTH,
    TAG_PREFIX,
    TOKEN_FILE,
    Json,
    JsonSent,
    Reply,
    Request,
    ScriptRequest,
    new_tag,
)

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
    'tell the user in one line that you have read the scripting part. Undo your own work with undo_edits, and only '
    'with it.'
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


class _NoListing(ToolError):
    """pgrep couldn't list Designer's processes: an empty list would read as none running (REVIEW.md SRV-83)."""


def _pgrep() -> subprocess.CompletedProcess[str]:
    """pgrep for Designer's processes: exit code 0 with their IDs, or 1 when none is found. Raises _NoListing when
    pgrep fails (exit code 2 or 3) or can't run."""
    try:
        done = subprocess.run(['pgrep', '-f', DESIGNER_PROCESS], capture_output=True, text=True)
    except OSError as e:
        raise _NoListing("Designer's processes couldn't be listed: %s" % e) from e
    if done.returncode not in (0, 1):
        raise _NoListing(
            "Designer's processes couldn't be listed (pgrep exit code %d: %s)" % (done.returncode, done.stderr.strip())
        )
    return done


def _designer_running() -> bool:
    """True while a Designer process exists (the bridge port closes before the process exits). Raises _NoListing when
    pgrep fails, which isn't none running (REVIEW.md SRV-163)."""
    if sys.platform == 'win32':
        # CSV: the default table cuts image names to 25 characters
        out = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq Adobe Substance 3D Designer.exe', '/FO', 'CSV', '/NH'],
            capture_output=True,
            text=True,
        ).stdout
        return '"Adobe Substance 3D Designer.exe"' in out
    return _pgrep().returncode == 0


server = MCPServer(name='substance-designer', instructions=INSTRUCTIONS)
_session: dict[str, bool] = {
    'guide_read': False,
    'scripting_read': False,
    # set_link_display reloaded a package, which leaves steps of Designer's own (server_tools/undo.py)
    'package_reloaded': False,
}  # one server process per client session (stdio)


P = ParamSpec('P')
R = TypeVar('R')

# The types of the tools' JSON parameters: a JSON object, and any JSON value. Their schemas are pinned to the ones
# agents saw before these parameters were narrowed to JsonValue, with the description each parameter's annotation adds.
JsonObject = Annotated[dict[str, JsonValue], WithJsonSchema({'additionalProperties': True, 'type': 'object'})]
AnyJson = Annotated[JsonValue, WithJsonSchema({})]


def _array(items: Literal['integer', 'number', 'string'], least: int, most: int | None = None) -> WithJsonSchema:
    """The schema of a parameter holding `least` (to `most`) values of the JSON type `items`: pydantic would describe a
    tuple's every position, which costs agents more to read. A call with another number is still refused before the
    tool runs, by the tuple type (REVIEW.md SRV-177)."""
    return WithJsonSchema({'type': 'array', 'items': {'type': items}, 'minItems': least, 'maxItems': most or least})


# The parameters of a fixed number of values (REVIEW.md SRV-177)
XY = Annotated[tuple[float, float], _array('number', 2)]  # [x, y], [dx, dy], [right, up]
Four = Annotated[tuple[float, float, float, float], _array('number', 4)]  # a rect, a crop's fractions
Box = Annotated[tuple[int, int, int, int], _array('integer', 4)]  # [x0, y0, x1, y1] in pixels
Pixel = Annotated[tuple[int, int], _array('integer', 2)]  # [x, y] in pixels
Color = Annotated[
    tuple[float, float, float] | tuple[float, float, float, float], _array('number', 3, 4)
]  # [r, g, b(, a)]
Link = Annotated[tuple[str, str], _array('string', 2)]  # [to_node, input]
T = TypeVar('T')


def _empty_is_none(value: object) -> object:
    """[] for an optional parameter of a fixed number of values: not given, as a client filling optional fields with
    empty values means it (REVIEW.md SRV-178; SRV-147 for strings)."""
    return None if value == [] else value


NoneIfEmpty = Annotated[T | None, BeforeValidator(_empty_is_none)]  # an optional XY, Four, Box or Color: None, or []

# The parameters that mean one thing in several tools, with the description their schema shows
Graph = Annotated[str | None, Field(description="The graph identifier (default: the graph open in Designer's UI).")]
Output = Annotated[
    str | None,
    Field(
        description="Which of the node's outputs (default: the one tagged base colour, else the first; the result says "
        'which).'
    ),
]
Port = Annotated[
    int | None,
    Field(description="The Designer on that bridge port (launch_designer's port); this server's when omitted."),
]


def _not_finite(value: JsonSent, where: str) -> tuple[str, float] | None:
    """The first number in `value`, its lists and dicts walked, that isn't finite, and where it is; or None. `value` is
    one of a tool's arguments, a JSON value once they are validated."""
    items: list[tuple[str, JsonSent]]
    if isinstance(value, float):
        return None if math.isfinite(value) else (where, value)
    if isinstance(value, dict):
        items = [('%s[%r]' % (where, k), v) for k, v in value.items()]
    elif isinstance(value, (list, tuple)):
        items = [('%s[%d]' % (where, i), v) for i, v in enumerate(value)]
    else:
        return None
    for inner, v in items:
        found = _not_finite(v, inner)
        if found:
            return found
    return None


def _tool(
    *,
    read_only: bool,
    destructive: bool,
    idempotent: bool,
    open_world: bool,
    scripting: bool = False,
    gated: bool = True,
    finite: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """server.tool(), refusing to run until the guide was read: any tool until get_guide() was called and, with
    `scripting`, a tool that runs code the caller wrote until get_guide('scripting') was too, so that nothing reaches
    Designer first. `gated=False` for a tool that must always work. `finite`: a number that isn't (JSON's 1e999,
    Infinity, NaN, which the arguments' validation turns into inf and nan) is refused by where it is, since written
    into a helper call with %r it comes out as a name Designer doesn't know (REVIEW.md SRV-119); False for a tool that
    sends its values as JSON.

    `read_only`, `destructive`, `idempotent` and `open_world` are the tool's four MCP hints:

    - `read_only`: the call changes none of the user's graphs, packages or files, not even while it runs, and nothing
      else they see, such as Designer's view, the editor's graph or the clipboard. A package the tool makes for itself
      and unloads isn't the user's, nor is a library package it opens to read (`describe_node` leaves it open). A tool
      that adds a temporary node to the user's graph isn't read-only: the graph changes while the call runs, and a
      library package can stay marked modified (DECISIONS.md, Library packages). The undo step a read-only tool's call
      can make (`describe_node`'s, `search_nodes`') isn't a change: it holds a temporary package and what was made in
      it, made and removed within the call, and `undo_edits` undoes it along the way, uncounted. It changes no graph,
      though, like any step, it clears Designer's Redo list.
    - `destructive`: the call can overwrite or remove the user's work or files. A change of the view, of the editor's
      graph or of the clipboard's text, put back, isn't one.
    - `idempotent`: a second call with the same arguments leaves the user's work as the first did.
    - `open_world`: True only for the two code tools, whose code can reach anything. The others talk only to the local
      Designer.

    The tool's description is its docstring cleaned by `inspect.getdoc`: the SDK would send the raw `__doc__`, each
    line after the first keeping the source's indentation."""
    hints = ToolAnnotations(
        read_only_hint=read_only,
        destructive_hint=destructive,
        idempotent_hint=idempotent,
        open_world_hint=open_world,
    )

    def decorate(fn: Callable[P, R]) -> Callable[P, R]:
        signature = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if gated:
                missing = [] if _session['guide_read'] else [GUIDE_NOT_READ]
                if scripting and not _session['scripting_read']:
                    missing.append(SCRIPTING_NOT_READ)
                if missing:
                    raise ToolError(' '.join(missing))
            if finite:
                for name, value in signature.bind_partial(*args, **kwargs).arguments.items():
                    found = _not_finite(value, name)
                    if found:
                        raise ToolError("%s is %r, which isn't a finite number: nothing was sent to Designer" % found)
            return fn(*args, **kwargs)

        return server.tool(annotations=hints, description=inspect.getdoc(fn))(wrapper)

    return decorate


def _output_note_in(text: str) -> str | None:
    """The helpers' line saying which of several outputs was taken, when none was named (REVIEW.md HLP-65)."""
    found = re.search(r'^no output given: .*$', text, re.M)
    return found.group(0) if found else None


# The tag that makes a call's undo step its own: project_constants.py's TAG_PREFIX, TAG_ALPHABET and TAG_LENGTH, and
# its new_tag
TAG_FORM = '%r, then %d random characters of %r' % (TAG_PREFIX, TAG_LENGTH, TAG_ALPHABET)  # for the docs
# The rollback _with_undo sends, run inside Designer, read once as the helpers are
ROLLBACK_FILE = os.path.join(HERE, 'designer_rollback.py')
with open(ROLLBACK_FILE, encoding='utf-8') as _file:
    ROLLBACK = _file.read()
ROLLBACK_LIMIT_S = 60  # s at most for an undo to land: a safety net (2000 added nodes took 2.9 s)
ROLLBACK_LINE = 'ROLLBACK='  # starts the line of a failed call's output saying what its rollback did
KEPT_LINE = 'KEPT='  # starts a helper's line saying what a failed call left changed, unless the rollback took it back
UNDONE = (
    "Designer's Undo %s, with its edits. What the call did that the step doesn't hold stays, such as a file it wrote, "
    'and its package may still show as modified.' % ROLLED_BACK
)
# A read's (SessionStep): no edits of its own, but a temporary node added to the user's graph or a value set and put
# back can leave the package marked modified (REVIEW.md SRV-268, SRV-270; DECISIONS.md, Library packages)
READ_UNDONE = "Designer's Undo %s, and the package it worked in may still show as modified." % ROLLED_BACK
NOT_LANDED = (
    "Designer's Undo of what the call had done before it failed was sent, but wasn't seen landing (%s): look with "
    "describe_graph or diff_graph before anything else, and don't undo again."
)
NOT_RUN = "The call's rollback couldn't run (%s)."  # why, after what a helper said stays changed


class SessionStep(NamedTuple):
    """The undo step of one call this session wrapped (_with_undo): its name, the call's label and tag, whether
    undo_edits counts it, and whether undo_edits undid it. A read's step (a temporary node added and removed, a value
    set and put back) changes nothing once the call ends, so undo_edits undoes it on the way without counting it. A
    step undone counts again once a Redo lists it (designer_rollback.undo_session)."""

    name: str
    edit: bool
    undone: bool = False


# The undo steps of this session's calls, oldest first: every call _with_undo wraps, whether or not it made a step. The
# server is one session's (stdio), so a reconnect starts with none. undo_edits marks those it undoes, which stay, and
# drops the others Designer's history no longer holds (server_tools/undo.py)
STEPS: list[SessionStep] = []


def _with_undo(code: str, label: str, edit: bool = True) -> str:
    """The script that runs `code` in Designer as one undo step, named `label` and a tag of its own (new_tag), the
    name remembered in STEPS (`edit` False for a read's call: SessionStep). If `code`
    raises, once the step has committed (an undo inside its group does nothing), the script runs the rollback
    (designer_rollback.py) in a scope of its own, prints what it did on a ROLLBACK_LINE of its own, after a newline,
    and raises the error again. The SystemExit of sys.exit(), sys.exit(0) or sys.exit(None) is a normal end, as the
    plugin's _run ends it too: it is raised again with no rollback. Any other exit is rolled back. How the step and the
    rollback run:

    - the step's transaction is opened and committed by sd's public SDHistoryUtils.newTransaction and
      commitTransaction, the functions UndoGroup calls, which raise on a refused open or commit. Nothing traced comes
      between `code`'s end and the commit, so the plugin's abort (a timeout, a cancel), which lands at a traced event,
      can't skip the commit. The script's own frame stops being traced (its f_trace None) first. Python's tracing is
      off around the open, and the plugin's tracer is put back before `code` runs; a refused open raises before it,
      and the plugin puts its tracer back after the job. Tracing is turned off again before the commit, and left
      off. Through UndoGroup, an abort landing in sd's Python after `code`'s last
      line skipped the commit, and the transaction stayed open, taking in every later change (REVIEW.md SRV-273,
      SRV-276; designer_rollback.py's docstring);
    - the rollback runs untraced, so that no abort of the plugin's stops it halfway; the plugin puts its tracer back
      after the job;
    - what the script needs after `code` is bound before `code` runs, as `code` shares its globals and may rebind
      print, exec or compile (`from re import *` does: REVIEW.md SRV-253). sys.settrace is bound too, so that turning
      tracing off before the commit imports nothing: Designer's __import__, a builtin named __feature_import__, runs
      Python (feature_import, in a loader.py), where the abort landed and the commit was skipped (measured 2026-11-25,
      the batch category's timeout check);
    - an error of the rollback's is said as its state ('failed: ...'), never raised in place of `code`'s. roll_back
      catches its own, but the module's imports and classes run before it, unguarded there (REVIEW.md SRV-257), so the
      script guards the whole rollback;
    - the state is printed on one line, its whitespace collapsed, as _failure reads it to the end of its line and an
      error's text can span several (PySide6's list signatures below: REVIEW.md SRV-258)."""
    tagged = label + new_tag()
    STEPS.append(SessionStep(tagged, edit))
    return dedent("""\
        import builtins as _builtins
        import sys as _sys
        from sd.api.sdhistoryutils import SDHistoryUtils as _mcp_history
        _step = %r
        _sys._getframe().f_trace = None
        _mcp_settrace, _mcp_tracer = _sys.settrace, _sys.gettrace()
        _mcp_settrace(None)
        _mcp_history.newTransaction(_step)
        _mcp_settrace(_mcp_tracer)
        try:
            exec(compile(%r, __file__, "exec"), globals())
        except BaseException as _raised:
            _mcp_settrace(None)
            _mcp_history.commitTransaction()
            if _builtins.isinstance(_raised, _builtins.SystemExit) and _raised.code in (None, 0):
                raise
            try:
                _rollback = {}
                _builtins.exec(_builtins.compile(%r, %r, "exec"), _rollback)
                _state = _rollback["roll_back"](%r, %r)
            except BaseException as _error:
                _state = "failed: " + _builtins.type(_error).__name__ + ": " + _builtins.str(_error)
            _builtins.print("\\n" + %r + " ".join(_state.split()))
            raise
        else:
            _mcp_settrace(None)
            _mcp_history.commitTransaction()
    """) % (tagged, code, ROLLBACK, ROLLBACK_FILE, tagged, ROLLBACK_LIMIT_S, ROLLBACK_LINE)


def _failure(output: str, error: str, code: str = '') -> tuple[str, str]:
    """A failed call's output without the rollback's line and the helpers' KEPT_LINE lines, and its error saying what
    the rollback did (designer_rollback.roll_back). The rollback's line is the last ROLLBACK_LINE printed after a
    newline (_with_undo), so a line of the script's own, or one it left unfinished, can't hide it (REVIEW.md SRV-255).
    `code` is the script sent, which names the call's step on its `_step = ...` line, opened with newTransaction:

    - 'undone': that Designer's Undo took back the call's step (UNDONE; READ_UNDONE for a read's), and the step is
      dropped from STEPS, as nothing is left to undo (REVIEW.md SRV-269);
    - 'not landed: <why>': to look before anything else (NOT_LANDED);
    - 'failed: <why>': the error as it was, then what a helper said stays changed, then why the rollback couldn't run
      (NOT_RUN);
    - 'not ours', or no rollback: the error as it was, then what a helper said stays changed, if anything."""
    lines = list(re.finditer(r'\n%s(.*)' % re.escape(ROLLBACK_LINE), output))
    state: str = lines[-1].group(1) if lines else ''
    if lines:
        output = output[: lines[-1].start()] + output[lines[-1].end() + 1 :]
    kept: list[str] = re.findall(r'^%s(.*)$' % re.escape(KEPT_LINE), output, re.M)
    output = re.sub(r'^%s.*\n?' % re.escape(KEPT_LINE), '', output, flags=re.M)
    word, _, why = state.partition(': ')
    if word == 'undone':
        step = next((step for step in reversed(STEPS) if '\n_step = %r\n' % step.name in code), None)  # the newest
        notes = [READ_UNDONE if step is not None and not step.edit else UNDONE]
        if step is not None:
            STEPS.remove(step)
    elif word == 'not landed':
        notes = [NOT_LANDED % why]
    elif word == 'failed':
        notes = [*kept, NOT_RUN % why]
    else:
        notes = kept
    if not notes:
        return output, error
    return output, ' '.join([_sentence(error.rstrip())] + [_sentence(note) for note in notes])


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


def _exchange(sock: socket.socket, token: str, request: Request, port: int) -> bytes:
    """The bridge protocol (plugin docstring): read the greeting, send the answer (an HMAC of the nonce, the port and
    the request's bytes) on a line before those bytes, instead of the token itself, and return the raw reply bytes. A
    greeting of another protocol gets nothing."""
    hello = b''
    while not hello.endswith(b'\n'):
        chunk = sock.recv(1024)
        if not chunk:
            raise ConnectionResetError('closed before the greeting')
        hello += chunk
    greeting: Json = json.loads(hello.decode('utf-8'))  # checked next
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


def _send(request: Request, wait: float, port: int | None = None) -> Reply:
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


def _control(cmd: Literal['cancel', 'status'], wait: float, port: int | None = None) -> str:
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
    request: ScriptRequest = {'code': code, 'path': path}
    if timeout:
        request['timeout'] = timeout
    # wait for the plugin's queue and the script itself, or a job we gave up on could start later
    reply = _send(request, wait=QUEUE_WAIT + (timeout or 900) + 60 if wait is None else wait, port=port)
    text = reply['output']
    if not reply['ok']:
        text, error = _failure(text, reply['error'], code)
        text += '\n--- ERROR ---\n' + error
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
