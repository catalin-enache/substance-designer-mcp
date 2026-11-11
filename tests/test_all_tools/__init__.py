"""The live self-test, one folder per category (categories.py); __main__.py runs them all (see its docstring)."""

import os
import sys

# the repository's root, for project_constants: importing any module of this package first must work
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
