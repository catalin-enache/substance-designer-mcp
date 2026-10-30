"""
Uninstaller: undoes what install.py set up (macOS and Windows).

    python uninstall.py               # show what will be removed, ask, then remove it
    python uninstall.py --dry-run     # only show what would be removed
    python uninstall.py --yes         # don't ask
    python uninstall.py --remove-snapshots   # also delete the graph snapshots (kept by default)

Removes: the Designer plugin and its token, the Claude Code skill, every folder's
`claude mcp add --scope local` registration of this server (and a user-scope one, if someone
added it), and mcp_server/venv. Only things that are this project's are touched: a plugin, skill
or registration with the same name that points elsewhere is reported and left alone. This folder
itself is left for you to delete.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import install  # noqa: E402  (shares paths, names and the skill marker with the installer)
from project_constants import PLUGIN, PLUGIN_DIR, TOKEN_FILE  # noqa: E402

SERVER = os.path.join(HERE, 'mcp_server', 'server.py')
VENV = os.path.join(HERE, 'mcp_server', 'venv')


def claude_json():
    """Claude Code's own config, where local- and user-scope MCP registrations live."""
    if os.environ.get('CLAUDE_CONFIG_DIR'):
        return os.path.join(os.environ['CLAUDE_CONFIG_DIR'], '.claude.json')
    return os.path.join(os.path.expanduser('~'), '.claude.json')


def snapshot_dir():
    # same default as SNAPSHOT_DIR in mcp_server/server.py (which needs the venv to import)
    return os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), '.sd_mcp', 'snapshots')


is_our_plugin = install.is_our_plugin


def _points_here(entry):
    """A registration is ours when it runs this folder's server.py."""
    parts = [entry.get('command') or ''] + [str(a) for a in entry.get('args') or []]
    return any(os.path.normcase(SERVER) in os.path.normcase(p) for p in parts)


def find_registrations(path=None):
    """([(scope, folder or None)] that run this server, [notes about other ones]) from ~/.claude.json.
    This repo's committed .mcp.json is project scope and goes away with the folder."""
    path = path or claude_json()
    try:
        with open(path, encoding='utf-8') as f:
            config = json.load(f)
    except (OSError, ValueError):
        return [], []
    found, notes = [], []
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


def remove_registration(scope, folder, claude):
    """Through Claude Code's own CLI (it owns ~/.claude.json); a local entry is keyed by the
    folder Claude Code started in, so the command runs there. Returns an error text or None."""
    cmd = [claude, 'mcp', 'remove', install.SERVER_NAME, '-s', scope]
    if folder is not None and not os.path.isdir(folder):
        return 'folder no longer exists; remove the entry from %s by hand, or ignore it' % claude_json()
    result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    return None if result.returncode == 0 else (result.stderr or result.stdout).strip()


# <folder>/<graph>/<YYYYmmdd-HHMMSS>[_n][-label].sbs, as server.py names them
SNAPSHOT_FILE = re.compile(r'^\d{8}-\d{6}(?:_\d+)?(?:-.*)?\.sbs$')


class Kept(str):
    """What an action returns when it did its part but something stays (not an error)."""


def remove_snapshots(folder):
    """Only the snapshot files the server wrote, then the folders they leave empty: the folder may
    be a shared one (SD_SNAPSHOT_DIR). Says so when the folder stays."""
    for graph in os.listdir(folder):
        sub = os.path.join(folder, graph)
        if not os.path.isdir(sub):
            continue
        for name in os.listdir(sub):
            if SNAPSHOT_FILE.match(name):
                os.remove(os.path.join(sub, name))
        if not os.listdir(sub):
            os.rmdir(sub)
    if os.listdir(folder):
        return Kept('the snapshots were deleted; folder kept, other files are in it')
    os.rmdir(folder)


def plan(args):
    """[(description, action or None)]; an action of None is only reported. An action returns
    None when done, or an error text."""
    items = []
    plugin = os.path.join(args.plugins_dir, PLUGIN)
    if os.path.isdir(plugin):
        if is_our_plugin(plugin):
            items.append(('Designer plugin: %s' % plugin, lambda: shutil.rmtree(plugin)))
        else:
            items.append(('%s is not this project\'s plugin; left as it is' % plugin, None))
    for suffix in ('.new', '.old'):   # left by an interrupted install (REVIEW.md INS-16)
        leftover = plugin + suffix
        if os.path.isdir(leftover):
            if is_our_plugin(leftover):
                items.append(('leftover plugin copy: %s' % leftover, lambda f=leftover: shutil.rmtree(f)))
            else:   # not ours, or a partly deleted copy (REVIEW.md INS-20)
                items.append(('%s is not this project\'s plugin (or a partly deleted copy); left as it is'
                              % leftover, None))
    old = os.path.join(args.plugins_dir, install.OLD_PLUGIN)
    if os.path.isdir(old):
        if install.is_old_plugin(old):
            items.append(('old plugin (before the rename): %s' % old,
                          lambda: install.remove_old_plugin(args.plugins_dir)))
        else:
            items.append(('%s is not this project\'s old plugin; left as it is' % old, None))
    for token in (TOKEN_FILE, install.OLD_TOKEN):
        if os.path.exists(token):
            # remove_old_plugin may already have deleted the old token
            items.append(('bridge token: %s' % token, lambda t=token: os.remove(t) if os.path.exists(t) else None))
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
            items.append(('MCP registration, %s' % where,
                          lambda scope=scope, folder=folder: remove_registration(scope, folder, claude)))
        else:
            items.append(('MCP registration, %s: `claude` not found; run there: claude mcp remove %s -s %s'
                          % (where, install.SERVER_NAME, scope), None))
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plugins-dir', default=install.default_plugins_dir())
    ap.add_argument('--skills-dir', default=install.default_skills_dir())
    ap.add_argument('--dry-run', action='store_true', help='only show what would be removed')
    ap.add_argument('--yes', '-y', action='store_true', help="don't ask before removing")
    ap.add_argument('--remove-snapshots', action='store_true', help='also delete the graph snapshots')
    args = ap.parse_args()

    if os.path.normcase(os.path.realpath(sys.prefix)) == os.path.normcase(os.path.realpath(VENV)):
        # its own files can't be deleted while it runs on Windows, and it removes them
        print("Note: this runs with the MCP server's own Python (mcp_server/venv), which it removes. "
              "Run it with your system Python instead: python3 uninstall.py (Windows: py -3 uninstall.py).\n")
    items = plan(args)
    actions = [(text, act) for text, act in items if act]
    if not items:
        print('Nothing to remove: the plugin, token, skill, registrations and venv are already gone.')
        return
    print('Will remove:' if actions else 'Nothing to remove.')
    for text, act in actions:
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
        except OSError as e:   # a locked or vanished file (Windows: a running server): go on
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
    print('\nDone. Restart Substance Designer (it still has the plugin loaded) and Claude Code.\n'
          'To finish, delete this folder: %s' % HERE)


if __name__ == '__main__':
    main()
