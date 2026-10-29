"""Unit tests that run without Designer: import server.py and test its pure-Python parts."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
sys.path.insert(0, os.path.join(ROOT, 'mcp_server'))

import server  # noqa: E402  (importing doesn't start the server or contact Designer)


@pytest.fixture
def sbs_path():
    return os.path.join(FIXTURES, 'two_graphs.sbs')
