"""
Installer for the Substance Designer bridge plugin + MCP server (macOS and Windows).

    python install.py                 # copy plugin, create venv (registration: see the README)
    python install.py --plugins-dir PATH   # custom Designer user-plugin folder

Run it with a Python 3.10+ interpreter. Re-running is safe (it updates in place).
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
    args = ap.parse_args()

    if sys.version_info < (3, 10):
        sys.exit('Python 3.10+ is required (found %s)' % sys.version.split()[0])

    # 1. Designer plugin
    src = PLUGIN_DIR
    dst = os.path.join(args.plugins_dir, PLUGIN)
    os.makedirs(args.plugins_dir, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
    print('[1/3] Plugin installed to', dst)
    remove_old_plugin(args.plugins_dir)

    # 2. Virtual environment for the MCP server
    venv = os.path.join(HERE, 'mcp_server', 'venv')
    if not os.path.exists(venv_python(venv)):
        subprocess.check_call([sys.executable, '-m', 'venv', venv])
    py = venv_python(venv)
    subprocess.check_call([py, '-m', 'pip', 'install', '-q', '--upgrade', 'pip'])
    subprocess.check_call([py, '-m', 'pip', 'install', '-q', '-r',
                           os.path.join(HERE, 'mcp_server', 'requirements.txt')])
    print('[2/3] MCP server environment ready:', venv)

    # 3. Registration: never global. This repo's .mcp.json registers the server for this folder
    # (Claude Code asks once to approve it); other folders opt in one by one.
    server = os.path.join(HERE, 'mcp_server', 'server.py')
    print('[3/3] Not registered globally. In this folder, .mcp.json registers it: start `claude` here and\n'
          '      approve "substance-designer" when asked. To use it in another folder, run there:\n'
          '      %s' % subprocess.list2cmdline(['claude', 'mcp', 'add', '--scope', 'local', SERVER_NAME, '--', py, server]))
    print('\nDone. Restart Substance Designer so it loads the plugin, then restart Claude Code.')


if __name__ == '__main__':
    main()
