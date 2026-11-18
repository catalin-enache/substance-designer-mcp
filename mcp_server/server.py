"""
MCP server for Adobe Substance 3D Designer.

Talks to the bridge plugin running inside Designer (127.0.0.1:9877; name and token file in
project_constants.py) and wraps Designer's sbscooker / sbsrender command-line tools.

This file starts the server. The code is in server_tools/, one module per area (core: the bridge
and the tool decorator; edits, views, output...: the tools, whose docstrings describe them). For
tests and scripts that `import server`, every name bound in those modules (definitions and the names
they import) is re-exported here; a function looks names up in its own module, so a test that
replaces one patches it in every module that binds it (tests/unit/conftest.py, patch_server).
"""

import sys

# Claude Code starts this with the venv's Python, which an older Python may have made: one from before the minimum
# became 3.12, kept until install.py runs again. This check comes before any other import, and this file stays readable
# by 3.9, so that the server refuses with a message instead of a SyntaxError (REVIEW.md SRV-176)
if sys.version_info < (3, 12):
    sys.exit(
        'Python 3.12+ is required (found %s). If this is mcp_server/venv, an older Python made it: run install.py again, '
        'with a Python 3.12+' % sys.version.split()[0]
    )

import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_tools

for _module in server_tools.MODULES:
    globals().update({k: v for k, v in vars(_module).items() if not k.startswith('__')})
del _module

if __name__ == '__main__':
    server_tools.core.server.run()  # also re-exported above as `server`
