"""read_designer_log."""

import os
import sys

from mcp.server.mcpserver.exceptions import ToolError

from .core import _tool


def _designer_log_path() -> str | None:
    if os.environ.get('SD_DESIGNER_LOG'):
        return os.environ['SD_DESIGNER_LOG']
    if sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support/Adobe/Adobe Substance 3D Designer')
    elif sys.platform == 'win32':
        base = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Adobe', 'Adobe Substance 3D Designer')
    else:
        base = os.path.expanduser('~/.local/share/Adobe/Adobe Substance 3D Designer')
    logs: list[str] = []
    for root, _dirs, files in os.walk(base):
        if 'log.txt' in files:
            logs.append(os.path.join(root, 'log.txt'))
    return max(logs, key=os.path.getmtime) if logs else None


@_tool()
def read_designer_log(
    lines: int = 60, contains: str | None = None, errors_only: bool = False, since_last_start: bool = True
) -> str:
    """Read the end of Designer's log, where every plugin/Python traceback lands. contains:
    case-insensitive text to filter on (e.g. 'listening on', 'Traceback'). errors_only: only
    [ERROR]/[WARNING] lines. since_last_start: ignore lines from before Designer's last start.
    Override the location with SD_DESIGNER_LOG."""
    path = _designer_log_path()
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


def _last_start(lines: list[str]) -> int:
    """Index of the most recent Designer start-up: Designer logs "Python SDK Version" exactly
    once per start, just before plugins load. 0 if not found."""
    for i in range(len(lines) - 1, -1, -1):
        if 'Python SDK Version' in lines[i]:
            return i
    return 0
