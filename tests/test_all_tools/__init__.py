"""The live self-test, one folder per category (categories.py); __main__.py runs them all (see its docstring)."""

import os
import sys

# the repository's root, for project_constants, and mcp_server, for the server's modules (function_compiler):
# importing any module of this package first must work
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _path in (_ROOT, os.path.join(_ROOT, 'mcp_server')):
    if _path not in sys.path:
        sys.path.insert(0, _path)
