"""read_designer_log."""

import os
import re
import sys

from mcp.server.mcpserver.exceptions import ToolError

from project_constants import (
    PLUGIN,
    QUIT_CLOSED,
    agent_designer_file,
)  # on sys.path: the package's __init__ imports .core, which puts it there

from .core import _designer_data_dir, _tool
from .lifecycle import _agent_designer, _agent_home, _checked_folder, _own_home_path, _port, _running_on

NEW_SESSION = '===== New Session ====='  # the first line Designer logs at each start
ENDED = 'Application uninitialized'  # its last, in a session that ends


def _newest_log(base: str) -> str | None:
    """The most recently written log.txt under base (one folder per Designer version). Not one that is a link: Designer
    writes a file, and a link could lead anywhere, the bridge token included (REVIEW.md SRV-96)."""
    logs: list[str] = []
    for root, _dirs, files in os.walk(base):
        if 'log.txt' in files and not os.path.islink(os.path.join(root, 'log.txt')):
            logs.append(os.path.join(root, 'log.txt'))
    return max(logs, key=os.path.getmtime) if logs else None


def _designer_log_path() -> str | None:
    """The log Designers write that no agent started with a home of its own: the user's."""
    if os.environ.get('SD_DESIGNER_LOG'):
        return os.environ['SD_DESIGNER_LOG']
    return _newest_log(_designer_data_dir())


def _last_port(log: str) -> int | None:
    """The bridge port of the last Designer started that wrote this log: what our plugin logs as it starts listening,
    after the start-up line. None if its plugin didn't say (it didn't load, or the log is from elsewhere)."""
    with open(log, encoding='utf-8', errors='replace') as f:
        lines = f.read().splitlines()
    for line in lines[_last_start(lines) :]:
        found = re.search(r'\[%s\] v\d+ listening on 127\.0\.0\.1:(\d+)' % re.escape(PLUGIN), line)
        if found:
            return int(found.group(1))
    return None


def _log_for(port: int) -> str | None:
    """The log of the Designer on `port`: its own if an agent started it (macOS: in its home), and the shared one if
    the user's is there. With none running, its own, what it wrote before it ended, unless the user's Designer last
    started was on this port too: then the newer of the two (REVIEW.md SRV-84)."""
    shared = _designer_log_path()
    if _agent_designer(port) is not None:  # its record says where it writes
        home = _agent_home(port)
        if not home:  # older code started it, or not macOS: it writes the shared log
            return shared
        return _agent_log(port, home)
    # only from this user's own folder: another account may have made it first (REVIEW.md SRV-96)
    ours = sys.platform == 'darwin' and _checked_folder(port) is not None
    own = _newest_log(_designer_data_dir(_own_home_path(port))) if ours else None
    if not own or _running_on(port):
        return shared
    if shared is None or not os.path.exists(shared) or _last_port(shared) not in (port, None):
        return own  # the shared log's last Designer was on another port: it isn't this port's
    return own if os.path.getmtime(own) >= os.path.getmtime(shared) else shared


def _agent_log(port: int, home: str) -> str:
    """The own log of the Designer an agent started on `port`, whose home is `home`, never the shared one; ToolError if
    that folder isn't this user's or the log isn't written yet."""
    if _checked_folder(port) is None:  # its record names a home there (REVIEW.md SRV-96)
        raise ToolError(
            "%s is not a folder of this user: the log of the Designer on port %d isn't read from it"
            % (os.path.dirname(home), port)
        )
    own = _newest_log(_designer_data_dir(home))
    # older than its record, it is an earlier run's on this port: the folder outlives a quit (REVIEW.md SRV-99)
    if own is None or os.path.getmtime(own) < os.path.getmtime(agent_designer_file(port)):  # not the shared log
        raise ToolError('The Designer on port %d has no log yet: it is still starting. Try again shortly.' % port)
    return own


@_tool()
def read_designer_log(
    lines: int = 60,
    contains: str | None = None,
    errors_only: bool = False,
    since_last_start: bool = True,
    port: int | None = None,
) -> str:
    """Read the end of Designer's log, where every plugin/Python traceback lands. contains:
    case-insensitive text to filter on (e.g. 'listening on', 'Traceback'). errors_only: only
    [ERROR]/[WARNING] lines. since_last_start: ignore lines from before Designer's last start.
    port: the log of the Designer on that bridge port (launch_designer's port); this server's when omitted. One an agent
    started on macOS writes a log of its own, also read after it has ended (unless a Designer of the user's started
    since, on that port or without the plugin saying which); just started, it has none yet, and this says so. The user's write one log together, their lines not
    told apart. The first line names the file read. Override the shared log's location with SD_DESIGNER_LOG."""
    path = _log_for(_port(port))
    if not path or not os.path.exists(path):
        raise ToolError('Designer log not found; set SD_DESIGNER_LOG to its path')
    with open(path, encoding='utf-8', errors='replace') as f:
        content = f.read().splitlines()
    if since_last_start:
        content = content[_last_start(content) :]
    if errors_only:
        content = [l for l in content if '[ERROR]' in l or '[WARNING]' in l]
    if contains:
        needle = contains.lower()
        content = [l for l in content if needle in l.lower()]
    tail = content[-lines:] if lines > 0 else content
    header = '%s (%d matching line%s, showing %d)' % (path, len(content), '' if len(content) == 1 else 's', len(tail))
    return header + '\n' + '\n'.join(tail)


LOG_TAIL = 256 * 1024  # the end of its log a forced quit reads: the quit's lines are its last


def _quit_evidence(port: int) -> tuple[bool, str] | None:
    """From the own log of the Designer an agent started on `port`, since its last start: whether the quit helper logged
    every window closed (QUIT_CLOSED: its close taken, whatever its shutdown did next), and its last line that isn't
    blank. None without a log of its own to read; one recorded without a home writes the shared log, the user's lines
    among its own: never read here (REVIEW.md SRV-108)."""
    home = _agent_home(port)
    if not home:
        return None
    try:
        path = _agent_log(port, home)
        with open(path, 'rb') as f:
            f.seek(max(0, os.path.getsize(path) - LOG_TAIL))
            lines = f.read().decode('utf-8', errors='replace').splitlines()
    except (ToolError, OSError):
        return None
    lines = lines[_last_start(lines) :]
    said = [line.strip() for line in lines if line.strip()]
    return any(QUIT_CLOSED in line for line in lines), said[-1] if said else ''


def _last_start(lines: list[str]) -> int:
    """Index of the most recent Designer start-up: the "Python SDK Version" line Designer logs once per start, just
    before plugins load, or, while one starts, its session's first line ("===== New Session =====", about 430 lines
    earlier): the previous session's lines aren't this one's (REVIEW.md SRV-107). A session after the SDK line that has
    ended, in its own lines up to the next session (a process handing its arguments over to the running Designer, then
    gone: no SDK line), isn't a start (REVIEW.md SRV-109, SRV-110). 0 if neither is found."""
    sdk = next((i for i in range(len(lines) - 1, -1, -1) if 'Python SDK Version' in lines[i]), -1)
    end = len(lines)
    for i in range(len(lines) - 1, sdk, -1):  # sessions begun since, the latest first
        if lines[i].startswith(NEW_SESSION):
            if not any(ENDED in line for line in lines[i:end]):
                return i
            end = i
    return max(sdk, 0)
