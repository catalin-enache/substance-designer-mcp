"""
Installer for the Substance Designer bridge plugin + MCP server (macOS and Windows).

    python install.py                 # copy plugin, create venv, register with Claude Code
    python install.py --no-register   # skip `claude mcp add`
    python install.py --plugins-dir PATH   # custom Designer user-plugin folder

Run it with a Python 3.10+ interpreter. Re-running is safe (it updates in place).
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_NAME = 'substance-designer'


def default_plugins_dir():
    # Designer's default user plugin path on both platforms
    docs = os.path.join(os.path.expanduser('~'), 'Documents')
    return os.path.join(docs, 'Adobe', 'Adobe Substance 3D Designer', 'python', 'sduserplugins')


def venv_python(venv):
    if sys.platform == 'win32':
        return os.path.join(venv, 'Scripts', 'python.exe')
    return os.path.join(venv, 'bin', 'python')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plugins-dir', default=default_plugins_dir())
    ap.add_argument('--no-register', action='store_true')
    args = ap.parse_args()

    if sys.version_info < (3, 10):
        sys.exit('Python 3.10+ is required (found %s)' % sys.version.split()[0])

    # 1. Designer plugin
    src = os.path.join(HERE, 'plugin', 'sd_bridge')
    dst = os.path.join(args.plugins_dir, 'sd_bridge')
    os.makedirs(args.plugins_dir, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
    print('[1/3] Plugin installed to', dst)

    # 2. Virtual environment for the MCP server
    venv = os.path.join(HERE, 'mcp_server', 'venv')
    if not os.path.exists(venv_python(venv)):
        subprocess.check_call([sys.executable, '-m', 'venv', venv])
    py = venv_python(venv)
    subprocess.check_call([py, '-m', 'pip', 'install', '-q', '--upgrade', 'pip'])
    subprocess.check_call([py, '-m', 'pip', 'install', '-q', '-r',
                           os.path.join(HERE, 'mcp_server', 'requirements.txt')])
    print('[2/3] MCP server environment ready:', venv)

    # 3. Register with Claude Code
    server = os.path.join(HERE, 'mcp_server', 'server.py')
    # the path `which` found: on Windows that may be npm's claude.cmd, which CreateProcess
    # won't find from a bare 'claude'
    claude = shutil.which('claude')
    cmd = [claude or 'claude', 'mcp', 'add', '--scope', 'user', SERVER_NAME, '--', py, server]
    if args.no_register or not claude:
        print('[3/3] Register manually with:\n     ', subprocess.list2cmdline(cmd))
    elif subprocess.call([claude, 'mcp', 'get', SERVER_NAME],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
        # re-adding would drop environment variables set with -e at registration
        print('[3/3] MCP server "%s" is already registered; left as it is. To re-register:\n'
              '      claude mcp remove %s -s user, then re-run this installer' % (SERVER_NAME, SERVER_NAME))
    else:
        subprocess.check_call(cmd)
        print('[3/3] Registered MCP server "%s" (user scope)' % SERVER_NAME)

    print('\nDone. Restart Substance Designer so it loads the plugin, then restart Claude Code.')


if __name__ == '__main__':
    main()
