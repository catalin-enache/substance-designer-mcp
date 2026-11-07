"""
Uninstaller: undoes what install.py set up (macOS and Windows).

    python uninstall.py               # show what will be removed, ask, then remove it
    python uninstall.py --dry-run     # only show what would be removed
    python uninstall.py --yes         # don't ask
    python uninstall.py --remove-snapshots   # also delete the graph snapshots (kept by default)

Removes: the Designer plugin and its token, the Claude Code skill, every folder's
`claude mcp add --scope local` registration of this server (and a user-scope one, if someone
added it), mcp_server/venv, and what launch_designer left for the Designers it started: their
records and their folders in /tmp (kept while a Designer runs). Only things that are this project's are touched: a plugin, skill
or registration with the same name that points elsewhere is reported and left alone. This folder
itself is left for you to delete.
"""

# Annotations stay unevaluated: this script must run, or refuse with a message, on the system Python,
# which can be older than 3.10 (REVIEW.md INS-25)
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from typing import Any, cast

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import install  # noqa: E402  (shares paths, names and the skill marker with the installer)
import project_constants  # noqa: E402  (AGENT_RECORD_DIR, read when called)
from project_constants import PLUGIN, TOKEN_FILE, agent_designer_file, agent_designer_folders, agent_designer_ports  # noqa: E402

SERVER = os.path.join(HERE, 'mcp_server', 'server.py')
VENV = os.path.join(HERE, 'mcp_server', 'venv')


def claude_json() -> str:
    """Claude Code's own config, where local- and user-scope MCP registrations live."""
    if os.environ.get('CLAUDE_CONFIG_DIR'):
        return os.path.join(os.environ['CLAUDE_CONFIG_DIR'], '.claude.json')
    return os.path.join(os.path.expanduser('~'), '.claude.json')


def snapshot_dir() -> str:
    # same default as SNAPSHOT_DIR in mcp_server/server_tools/snapshots.py (which needs the venv to import)
    return os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), '.sd_mcp', 'snapshots')


is_our_plugin = install.is_our_plugin


def _points_here(entry: dict[str, Any]) -> bool:
    """A registration is ours when it runs this folder's server.py."""
    parts = [entry.get('command') or ''] + [str(a) for a in entry.get('args') or []]
    return any(os.path.normcase(SERVER) in os.path.normcase(p) for p in parts)


def find_registrations(path: str | None = None) -> tuple[list[tuple[str, str | None]], list[str]]:
    """([(scope, folder or None)] that run this server, [notes about other ones]) from ~/.claude.json.
    This repo's committed .mcp.json is project scope and goes away with the folder."""
    path = path or claude_json()
    try:
        with open(path, encoding='utf-8') as f:
            config = json.load(f)
    except (OSError, ValueError):
        return [], []
    found: list[tuple[str, str | None]] = []
    notes: list[str] = []
    entry = (config.get('mcpServers') or {}).get(install.SERVER_NAME)
    if entry:
        if _points_here(entry):
            found.append(('user', None))
        else:
            notes.append('a user-scope "%s" that runs something else' % install.SERVER_NAME)
    for folder, project in sorted((config.get('projects') or {}).items()):
        entry = (project.get('mcpServers') or {}).get(install.SERVER_NAME)
        if not entry:
            continue
        if _points_here(entry):
            found.append(('local', folder))
        else:
            notes.append('"%s" in %s runs something else' % (install.SERVER_NAME, folder))
    return found, notes


def remove_registration(scope: str, folder: str | None, claude: str) -> str | None:
    """Through Claude Code's own CLI (it owns ~/.claude.json); a local entry is keyed by the
    folder Claude Code started in, so the command runs there. Returns an error text or None."""
    cmd = [claude, 'mcp', 'remove', install.SERVER_NAME, '-s', scope]
    if folder is not None and not os.path.isdir(folder):
        return 'folder no longer exists; remove the entry from %s by hand, or ignore it' % claude_json()
    result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    return None if result.returncode == 0 else (result.stderr or result.stdout).strip()


# <folder>/<graph>/<YYYYmmdd-HHMMSS>[_n][-label].sbs, as mcp_server/server_tools/snapshots.py names them
# a snapshot, and the note of its package beside it (REVIEW.md SRV-34, INS-26)
SNAPSHOT_FILE = re.compile(r'^\d{8}-\d{6}(?:_\d+)?(?:-.*)?\.sbs(?:\.json)?$')


class Kept(str):
    """What an action returns when it did its part but something stays (not an error)."""


def remove_snapshots(folder: str) -> Kept | None:
    """Only the snapshot files the server wrote, then the folders they leave empty: the folder may
    be a shared one (SD_SNAPSHOT_DIR). Says so when the folder stays."""
    saved_over = []
    for graph in os.listdir(folder):
        sub = os.path.join(folder, graph)
        if not os.path.isdir(sub):
            continue
        for name in os.listdir(sub):
            path = os.path.join(sub, name)
            snapshot = path[: -len('.json')] if name.endswith('.json') else path
            if not SNAPSHOT_FILE.match(name):
                continue
            if changed_since(snapshot):  # saved over since: it holds the user's work (REVIEW.md SRV-47)
                if path == snapshot:
                    saved_over.append(snapshot)
                continue
            os.remove(path)
        if not os.listdir(sub):
            os.rmdir(sub)
    if saved_over:
        return Kept(
            'the snapshots were deleted, except %d saved over since they were taken (they may hold your '
            'work): %s' % (len(saved_over), ', '.join(sorted(saved_over)))
        )
    if os.listdir(folder):
        return Kept('the snapshots were deleted; folder kept, other files are in it')
    os.rmdir(folder)
    return None


def changed_since(snapshot: str) -> bool:
    """Whether a snapshot's file no longer matches the size and time its note recorded when it was
    written (the server's _changed_since): opened in Designer and saved in place."""
    try:
        with open(snapshot + '.json', encoding='utf-8') as f:
            note = json.load(f)
        st = os.stat(snapshot)
    except (OSError, ValueError):
        return False
    if not isinstance(note, dict) or 'size' not in note or 'mtime_ns' not in note:
        return False
    return bool(note['size'] != st.st_size or note['mtime_ns'] != st.st_mtime_ns)


# an uninstall step: returns None when done, or an error text (Kept: done, but something stays)
Action = Callable[[], 'str | None']  # quoted: a module-level alias is evaluated even so (INS-25)


def folders_in_use() -> str | None:
    """Why the folders launch_designer made must be kept now, or None when they can go: a Designer runs (found as the
    server finds it), or that can't be told: pgrep failing or missing, or not macOS, where the pattern was made and
    tried (REVIEW.md INS-27). On Windows launch_designer makes no folders."""
    if sys.platform == 'win32':
        return None
    if sys.platform != 'darwin':
        return "Designer's processes can't be told apart here (only tried on macOS)"
    try:
        done = subprocess.run(['pgrep', '-f', project_constants.DESIGNER_PROCESS], capture_output=True, text=True)
    except OSError as e:
        return "Designer's processes couldn't be listed (%s)" % e
    if done.returncode == 0:
        return 'Designer runs'
    if done.returncode == 1:  # nothing found
        return None
    return "Designer's processes couldn't be listed (pgrep exit code %d: %s)" % (done.returncode, done.stderr.strip())


def plan(args: argparse.Namespace) -> list[tuple[str, Action | None]]:
    """[(description, action or None)]; an action of None is only reported. An action returns
    None when done, or an error text."""
    items: list[tuple[str, Action | None]] = []
    plugin = os.path.join(args.plugins_dir, PLUGIN)
    if os.path.isdir(plugin):
        if is_our_plugin(plugin):
            items.append(('Designer plugin: %s' % plugin, lambda: shutil.rmtree(plugin)))
        else:
            items.append(("%s is not this project's plugin; left as it is" % plugin, None))
    for suffix in ('.new', '.old'):  # left by an interrupted install (REVIEW.md INS-16)
        leftover = plugin + suffix
        if os.path.isdir(leftover):
            if is_our_plugin(leftover):
                items.append(('leftover plugin copy: %s' % leftover, cast(Action, lambda f=leftover: shutil.rmtree(f))))
            else:  # not ours, or a partly deleted copy (REVIEW.md INS-20)
                items.append(
                    ("%s is not this project's plugin (or a partly deleted copy); left as it is" % leftover, None)
                )
    old = os.path.join(args.plugins_dir, install.OLD_PLUGIN)
    if os.path.isdir(old):
        if install.is_old_plugin(old):
            items.append(
                ('old plugin (before the rename): %s' % old, lambda: install.remove_old_plugin(args.plugins_dir))
            )
        else:
            items.append(("%s is not this project's old plugin; left as it is" % old, None))
    for token in (TOKEN_FILE, install.OLD_TOKEN):
        if os.path.exists(token):
            # remove_old_plugin may already have deleted the old token
            items.append(
                ('bridge token: %s' % token, cast(Action, lambda t=token: os.remove(t) if os.path.exists(t) else None))
            )
    # one per bridge port, and the single one of earlier versions
    records = [agent_designer_file(port) for port in agent_designer_ports()]
    records.append(os.path.join(project_constants.AGENT_RECORD_DIR, '.%s_agent_designer.json' % PLUGIN))
    for record in records:
        if os.path.exists(record):
            items.append(
                (
                    'record of a Designer an agent started: %s' % record,
                    cast(Action, lambda r=record: os.remove(r) if os.path.exists(r) else None),
                )
            )
    # the folders launch_designer made for Designers it started: their homes (settings, logs, crash dumps)
    agent_folders: list[str] = []
    for agent_folder in agent_designer_folders():
        info = os.lstat(agent_folder)
        if stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid():
            agent_folders.append(agent_folder)
        else:  # a link, or not this user's: not one launch_designer made
            items.append(('%s is not a folder launch_designer made; left as it is' % agent_folder, None))
    in_use = folders_in_use() if agent_folders else None  # one an agent started uses its folder as its home
    if in_use:
        why = 'while Designer runs' if in_use == 'Designer runs' else 'since %s' % in_use
        items.append(('folders of Designers an agent started, kept %s: %s' % (why, ', '.join(agent_folders)), None))
    else:
        for agent_folder in agent_folders:
            items.append(
                (
                    'folder of a Designer an agent started (its settings, log, crash dumps): %s' % agent_folder,
                    cast(Action, lambda f=agent_folder: shutil.rmtree(f)),
                )
            )
    skill = os.path.join(args.skills_dir, install.SERVER_NAME)
    if os.path.isdir(skill):
        if install.is_our_skill(skill):
            items.append(('Claude Code skill: %s' % skill, lambda: shutil.rmtree(skill)))
        else:
            items.append(('%s was not written by install.py; left as it is' % skill, None))

    found, notes = find_registrations()
    claude = shutil.which('claude')
    for scope, folder in found:
        where = 'user scope (every folder)' if scope == 'user' else folder
        if claude:
            items.append(
                (
                    'MCP registration, %s' % where,
                    cast(Action, lambda scope=scope, folder=folder: remove_registration(scope, folder, claude)),
                )
            )
        else:
            items.append(
                (
                    'MCP registration, %s: `claude` not found; run there: claude mcp remove %s -s %s'
                    % (where, install.SERVER_NAME, scope),
                    None,
                )
            )
    for note in notes:
        items.append(('%s; left as it is' % note, None))

    if os.path.isdir(VENV):
        items.append(('MCP server environment: %s' % VENV, lambda: shutil.rmtree(VENV)))
    snapshots = snapshot_dir()
    if os.path.isdir(snapshots):
        if args.remove_snapshots:
            items.append(('graph snapshots: %s' % snapshots, lambda: remove_snapshots(snapshots)))
        else:
            items.append(('graph snapshots kept (--remove-snapshots deletes them): %s' % snapshots, None))
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--plugins-dir', default=install.default_plugins_dir())
    ap.add_argument('--skills-dir', default=install.default_skills_dir())
    ap.add_argument('--dry-run', action='store_true', help='only show what would be removed')
    ap.add_argument('--yes', '-y', action='store_true', help="don't ask before removing")
    ap.add_argument('--remove-snapshots', action='store_true', help='also delete the graph snapshots')
    args = ap.parse_args()

    if os.path.normcase(os.path.realpath(sys.prefix)) == os.path.normcase(os.path.realpath(VENV)):
        # its own files can't be deleted while it runs on Windows, and it removes them
        print(
            "Note: this runs with the MCP server's own Python (mcp_server/venv), which it removes. "
            'Run it with your system Python instead: python3 uninstall.py (Windows: py -3 uninstall.py).\n'
        )
    items = plan(args)
    actions = [(text, act) for text, act in items if act]
    if not items:
        print('Nothing to remove: the plugin, token, skill, registrations and venv are already gone.')
        return
    print('Will remove:' if actions else 'Nothing to remove.')
    for text, _act in actions:
        print('  - ' + text)
    kept = [text for text, act in items if not act]
    if kept:
        print('Not touched:')
        for text in kept:
            print('  - ' + text)
    if not actions or args.dry_run:
        return
    if not args.yes and input('Proceed? [y/N] ').strip().lower() not in ('y', 'yes'):
        print('Nothing removed.')
        return
    failed = False
    for text, act in actions:
        try:
            error = act()
        except OSError as e:  # a locked or vanished file (Windows: a running server): go on
            error = str(e)
        if isinstance(error, Kept):
            print('Removed %s (%s)' % (text, error))
        elif error:
            failed = True
            print('Could not remove %s: %s' % (text, error))
        else:
            print('Removed ' + text)
    if failed:
        print('\nSome items were not removed (see above).')
    print(
        '\nDone. Restart Substance Designer (it still has the plugin loaded) and Claude Code.\n'
        'To finish, delete this folder: %s' % HERE
    )


if __name__ == '__main__':
    main()
