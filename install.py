"""
Installer for the Substance Designer bridge plugin + MCP server (macOS and Windows).

    python install.py                 # copy plugin, create venv, add the Claude Code skill
    python install.py --plugins-dir PATH   # custom Designer user-plugin folder
    python install.py --no-skill      # don't add the skill to ~/.claude/skills

Run it with a Python 3.10+ interpreter. Re-running is safe (it updates in place).
uninstall.py undoes all of it.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from project_constants import PLUGIN, PLUGIN_DIR  # noqa: E402  (the plugin's name lives there)
SERVER_NAME = 'substance-designer'
# Before the rename the plugin was "sd_bridge" with its token in ~/.sd_bridge_token. Both copies
# loaded together fight over the port, so an old copy of *this* plugin is removed.
OLD_PLUGIN, OLD_PLUGIN_NAME = 'sd_bridge', 'SD Bridge (local script runner)'
OLD_TOKEN = os.path.join(os.path.expanduser('~'), '.sd_bridge_token')


# The skill tells Claude Code sessions in other folders that this server exists and how to
# register it there; only its one-line description is in their context. The marker is how
# uninstall.py (and a re-install) know the skill folder is ours to replace or remove.
SKILL_MARKER = '<!-- Written by substance-designer-mcp install.py; uninstall.py removes it. -->'


def claude_config_dir():
    return os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude')


def default_skills_dir():
    return os.path.join(claude_config_dir(), 'skills')


def register_command(py, server):
    return subprocess.list2cmdline(['claude', 'mcp', 'add', '--scope', 'local', SERVER_NAME, '--', py, server])


def skill_text(py, server):
    return '''---
name: %(name)s
description: Use when the user asks for work in Adobe Substance 3D Designer (materials, node graphs, .sbs or .sbsar files, trim sheets) and this session has no mcp__%(name)s__* tools, not even deferred ones. Explains how to enable the local %(name)s MCP server in the current folder.
---
%(marker)s

# Substance Designer MCP: enabling it in this folder

The %(name)s MCP server (it drives the user's running Substance 3D Designer) is installed on
this machine in `%(repo)s`, but it is registered per folder on purpose, so sessions elsewhere
don't start it or spend context on it.

If this session already has `mcp__%(name)s__*` tools (deferred counts), you don't need this
skill: follow that server's instructions instead.

Otherwise:

1. Tell the user the server is installed but not enabled in this folder, and ask whether to
   enable it here. If yes, run in the current folder:
   ```
   %(cmd)s
   ```
   `--scope local` registers it for this folder and this user only (in Claude Code's own
   config, not in the project). Never use `--scope user` (every session everywhere) or
   `--scope project` (writes this machine's paths into the project's `.mcp.json`).
2. New MCP servers load when a session starts: ask the user to exit and run `claude --continue`
   in this folder to come back to this conversation with the tools.
3. In the new session, follow the server's instructions (call `get_guide()` before the first
   Designer tool). `launch_designer` starts Designer if it isn't running.

To disable it here again: `claude mcp remove %(name)s -s local`. To remove everything (plugin,
token, this skill, every folder's registration): `%(python)s %(uninstall)s`.
''' % {'name': SERVER_NAME, 'marker': SKILL_MARKER, 'repo': HERE, 'cmd': register_command(py, server),
       'python': 'py -3' if sys.platform == 'win32' else 'python3', 'uninstall': os.path.join(HERE, 'uninstall.py')}


def is_our_skill(folder):
    try:
        with open(os.path.join(folder, 'SKILL.md'), encoding='utf-8') as f:
            return SKILL_MARKER in f.read()
    except OSError:
        return False


def install_skill(skills_dir, py, server):
    """Write <skills_dir>/substance-designer/SKILL.md, unless that folder holds someone else's skill."""
    folder = os.path.join(skills_dir, SERVER_NAME)
    if os.path.exists(folder) and not is_our_skill(folder):
        print('      Note: %s exists and was not written by this installer; left as it is.' % folder)
        return None
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, 'SKILL.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(skill_text(py, server))
    return path


def default_plugins_dir():
    # Designer's default user plugin path on both platforms
    docs = os.path.join(os.path.expanduser('~'), 'Documents')
    return os.path.join(docs, 'Adobe', 'Adobe Substance 3D Designer', 'python', 'sduserplugins')


def venv_python(venv):
    if sys.platform == 'win32':
        return os.path.join(venv, 'Scripts', 'python.exe')
    return os.path.join(venv, 'bin', 'python')


def remove_old_plugin(plugins_dir):
    """Delete <plugins_dir>/sd_bridge and the old token, but only if that folder is this
    project's plugin (its pluginInfo.json name); anything else called sd_bridge is left alone."""
    old = os.path.join(plugins_dir, OLD_PLUGIN)
    if not os.path.isdir(old):
        return
    try:
        with open(os.path.join(old, 'pluginInfo.json'), encoding='utf-8') as f:
            ours = json.load(f).get('name') == OLD_PLUGIN_NAME
    except (OSError, ValueError):
        ours = False
    if not ours:
        print('      Note: %s exists but is not this project\'s old plugin; left as it is.' % old)
        return
    shutil.rmtree(old)
    print('      Removed the old plugin (renamed to %s): %s' % (PLUGIN, old))
    if os.path.exists(OLD_TOKEN):
        os.remove(OLD_TOKEN)
        print('      Removed its old token file: %s' % OLD_TOKEN)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plugins-dir', default=default_plugins_dir())
    ap.add_argument('--skills-dir', default=default_skills_dir(),
                    help='Claude Code user skills folder (default: ~/.claude/skills)')
    ap.add_argument('--no-skill', action='store_true', help="don't add the Claude Code skill")
    args = ap.parse_args()

    if sys.version_info < (3, 10):
        sys.exit('Python 3.10+ is required (found %s)' % sys.version.split()[0])

    # 1. Designer plugin
    src = PLUGIN_DIR
    dst = os.path.join(args.plugins_dir, PLUGIN)
    os.makedirs(args.plugins_dir, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
    print('[1/4] Plugin installed to', dst)
    remove_old_plugin(args.plugins_dir)

    # 2. Virtual environment for the MCP server
    venv = os.path.join(HERE, 'mcp_server', 'venv')
    if not os.path.exists(venv_python(venv)):
        subprocess.check_call([sys.executable, '-m', 'venv', venv])
    py = venv_python(venv)
    subprocess.check_call([py, '-m', 'pip', 'install', '-q', '--upgrade', 'pip'])
    subprocess.check_call([py, '-m', 'pip', 'install', '-q', '-r',
                           os.path.join(HERE, 'mcp_server', 'requirements.txt')])
    print('[2/4] MCP server environment ready:', venv)

    # 3. Registration: never global. This repo's .mcp.json registers the server for this folder
    # (Claude Code asks once to approve it); other folders opt in one by one.
    server = os.path.join(HERE, 'mcp_server', 'server.py')
    print('[3/4] Not registered globally. In this folder, .mcp.json registers it: start `claude` here and\n'
          '      approve "substance-designer" when asked. To use it in another folder, run there:\n'
          '      %s' % register_command(py, server))

    # 4. The skill: lets sessions in other folders know about the server (and how to register it)
    if args.no_skill:
        print('[4/4] Skill not added (--no-skill).')
    else:
        path = install_skill(args.skills_dir, py, server)
        if path:
            print('[4/4] Claude Code skill added: %s\n'
                  '      Sessions in other folders now know this server exists and offer to enable it.' % path)
    print('\nDone. Restart Substance Designer so it loads the plugin, then restart Claude Code.')


if __name__ == '__main__':
    main()
