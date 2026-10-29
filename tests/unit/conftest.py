"""Unit tests that run without Designer: import server.py and test its pure-Python parts."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
sys.path.insert(0, os.path.join(ROOT, 'mcp_server'))
sys.path.insert(0, ROOT)

import server  # noqa: E402  (importing doesn't start the server or contact Designer)


@pytest.fixture(autouse=True)
def guide_read(monkeypatch):
    """Tool results start with a reminder until get_guide() was called; tests compare exact
    results, so they run as a session that has read the guide (test_guide.py covers the rest)."""
    monkeypatch.setitem(server._session, 'guide_read', True)


@pytest.fixture
def sbs_path():
    return os.path.join(FIXTURES, 'two_graphs.sbs')
