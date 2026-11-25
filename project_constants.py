"""The bridge plugin's name, in one place for everything that runs from this repo: the MCP
server, the CLI client, the installer and the tests.

The plugin itself (running inside Designer from its installed copy) can't import this file; it
takes its name from its own folder. So renaming the plugin means: change PLUGIN here and rename
both plugin/<PLUGIN>/ folders to match. tests/unit/test_constants.py checks that the folders
match, that no other code spells the name out, and that README.md, GUIDE.md and
.claude/rules/designer-code.md mention it.

The self-test's Designer scripts import this file inside Designer, for new_tag. So it imports only the standard library
(tests/unit/test_constants.py).
"""

import json
import os
import re
import secrets
from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict

PLUGIN = 'sd_claude_bridge_kve'
MIN_PYTHON = (3, 12)  # every Python file's minimum (DECISIONS.md, Project rules; ROADMAP item 105)

ROOT = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.join(ROOT, 'plugin', PLUGIN)  # what install.py copies (holds pluginInfo.json)
PLUGIN_PACKAGE_DIR = os.path.join(PLUGIN_DIR, PLUGIN)  # the Python package Designer imports
TOKEN_FILE = os.path.join(os.path.expanduser('~'), '.%s_token' % PLUGIN)  # the plugin's secret
# Seconds the plugin keeps a queued job before dropping it (its own QUEUE_WAIT, which it can't
# import from here; tests/unit/test_queue_wait.py checks they match). A client waits at least
# this long plus the script's time, so a job it gave up on can't start later.
QUEUE_WAIT = 900
# The bridge protocol (the plugin's docstring): its greeting names it, and a client of another one sends nothing. The
# plugin's own PROTOCOL, which it can't import from here either (tests/unit/test_plugin.py checks they match).
BRIDGE_PROTOCOL = 2
# The nonce in its greeting, as the plugin makes it (secrets.token_hex(16)): the clients sign nothing with another, which
# could hold a newline and shift the signed message's lines (REVIEW.md SRV-94; tests/unit/test_plugin.py checks it).
NONCE = re.compile(r'[0-9a-f]{32}')
# A JSON value, as json.loads gives it and json.dumps takes it: the bridge's messages, the agent records and the tools'
# JSON arguments.
type Json = bool | int | float | str | list[Json] | dict[str, Json] | None
# A JSON value to send, only read on its way: as Json, with any sequence or mapping of them. So a list[str] is one, where
# it is no list[Json]: a list[Json] may be given any JSON value, which a list[str] must not hold.
type JsonSent = bool | int | float | str | Sequence[JsonSent] | Mapping[str, JsonSent] | None
# A tool's arguments as the tests send them: JSON values by name
ToolArgs = Mapping[str, JsonSent]


# The bridge's messages (the plugin's docstring), for its clients: the server, the CLI client and the self-test. The
# plugin, which can't import this file, has its own Reply and reads requests as plain JSON.
class Greeting(TypedDict):
    """The plugin's greeting line, the first thing it sends on a connection."""

    nonce: str
    protocol: int


class _Script(TypedDict):
    code: str
    path: str | None


class ScriptRequest(_Script, total=False):
    """A script for the plugin to run: its code, the path it runs as (its __file__, named in its tracebacks), and the
    seconds before the plugin aborts it."""

    timeout: float


class ControlRequest(TypedDict):
    """A control request: cancel or status."""

    cmd: Literal['cancel', 'status']


# What a client sends: one JSON object
Request = ScriptRequest | ControlRequest


class Reply(TypedDict, total=False):
    """The plugin's reply to a request."""

    ok: bool
    output: str
    error: str


# Seconds launch_designer gives a Designer an agent started before it counts as stuck: its default wait
STARTUP_LIMIT = 180

# quit_designer's words for a Designer an agent started that it had to force-end: during its own shutdown, every window
# closed, or before its close took (the self-test tells them apart: DECISIONS.md, Bridge and quitting)
QUIT_FORCED_IN_SHUTDOWN = 'forced during its shutdown'
QUIT_FORCED_NOT_CLOSED = 'forced: it had not closed'
# The line the quit helper logs in Designer once every window it closed has closed, Designer's own among them: its close
# taken, as the helper judges it before Designer's own quit decides (its limits: designer_helpers/quit.py), whatever its
# shutdown does next
QUIT_CLOSED = '[%s] quit: every window closed' % PLUGIN
# Before the path of the file a Designer an agent started had its threads sampled into, when it was about to be forced
# (macOS: server_tools/lifecycle.py); a quit naming one keeps the self-test's folder of it (ROADMAP item 70)
QUIT_SAMPLED = 'Its threads, sampled first:'
# In a failed call's error once Designer's Undo took back the call's step (server_tools/core.py, UNDONE): the self-test's
# rollback checks match it
ROLLED_BACK = "took back the call's own undo step"
# The tag that makes a call's undo step its own: TAG_PREFIX, then TAG_LENGTH characters of TAG_ALPHABET drawn at random
# for each call (new_tag). Its form is these three only (the user, 2026-11-24). The self-test reads them too, its facts
# of Designer's history included. An invisible tag is '', '\u200b\u200c\u200d\u2060' and 16: as many names
# (4**16 = 16**8), and Designer's dropdowns show the label alone (measured 2026-11-24).
TAG_PREFIX = ' #'
TAG_ALPHABET = '0123456789abcdef'
TAG_LENGTH = 8


def new_tag() -> str:
    """A tag of its own for one call's undo step: TAG_PREFIX, then TAG_LENGTH random characters of TAG_ALPHABET."""
    return TAG_PREFIX + ''.join(secrets.choice(TAG_ALPHABET) for _ in range(TAG_LENGTH))


# Where the records of the Designers an agent started go (agent_designer_file). In the home folder, as the temp folder
# depends on how the server was started, and the MCP client doesn't pass TMPDIR on
AGENT_RECORD_DIR = os.path.expanduser('~')


def agent_designer_file(port: int) -> str:
    """Which Designer an agent started on bridge `port` (server_tools/lifecycle.py), in a file so a /mcp reconnect
    doesn't lose it. One file per port; launches on one port take turns (launch_designer's lock), and each record is
    written whole, then put in place, so a server reading it meanwhile never sees part of one."""
    return os.path.join(AGENT_RECORD_DIR, '.%s_agent_designer_%d.json' % (PLUGIN, port))


class AgentRecord(TypedDict):
    """What an agent_designer_file holds, as launch_designer writes it: the process ID of the Designer it started, that
    process's start as ps says it, and the Designer's home (None: the user's). The server's reader
    (server_tools/lifecycle.py, _agent_record) checks what it reads; read_agent_record, for the tests, doesn't."""

    pid: int
    start: str
    home: str | None


def read_agent_record(path: str) -> AgentRecord:
    """The record in `path`, an agent_designer_file, taken as launch_designer writes it. The tests read records with it,
    and it checks nothing. Raises OSError when the file can't be read, and ValueError when it isn't JSON."""
    with open(path, encoding='utf-8') as f:
        record: AgentRecord = json.load(f)
    return record


def agent_designer_ports() -> list[int]:
    """The ports with a record (agent_designer_file), whether or not its Designer still runs."""
    try:
        names = os.listdir(AGENT_RECORD_DIR)
    except OSError:
        return []
    pattern = re.compile(r'\.%s_agent_designer_(\d+)\.json$' % re.escape(PLUGIN))
    return sorted(int(m.group(1)) for m in map(pattern.match, names) if m)


# Where launch_designer makes the folders of a Designer it starts, one per port (server_tools/lifecycle.py): short, as
# a socket path in its temp folder has at most 103 bytes. uninstall.py removes them.
SHORT_TEMP = '/tmp'
# Designer's process as `pgrep -f` finds it on macOS: the server and uninstall.py look for it so
DESIGNER_PROCESS = 'MacOS/Adobe Substance 3D Designer( |$)'


def agent_folder_name(port: int) -> str:
    """The folder launch_designer makes in SHORT_TEMP for the Designer it starts on `port` (POSIX: it holds the user's
    ID, as /tmp is shared)."""
    return 'sd_mcp_%d_%d' % (os.getuid(), port)


def agent_designer_folders() -> list[str]:
    """This user's folders in SHORT_TEMP named as launch_designer names them, whether or not their Designer runs; none
    on Windows, where launch_designer makes none."""
    if not hasattr(os, 'getuid'):
        return []
    try:
        names = os.listdir(SHORT_TEMP)
    except OSError:
        return []
    pattern = re.compile(r'sd_mcp_%d_\d+$' % os.getuid())
    return sorted(os.path.join(SHORT_TEMP, name) for name in names if pattern.match(name))
