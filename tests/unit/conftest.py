"""Unit tests that run without Designer: import server.py and test its pure-Python parts."""

import os
import sys
import types
from typing import Any, cast

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
sys.path.insert(0, os.path.join(ROOT, 'mcp_server'))
sys.path.insert(0, ROOT)

import server as _server_module  # noqa: E402  (importing doesn't start the server or contact Designer)
import server_tools  # noqa: E402  (server.py's code, one module per area)

# server.py copies every name of server_tools/ into itself at import time, which mypy can't follow:
# as a plain module its attributes (server.describe_graph, server._bridge...) are Any to the checker.
server: types.ModuleType = _server_module


def patch_server(monkeypatch: pytest.MonkeyPatch, name: str, value: Any) -> None:
    """monkeypatch.setattr for a server name: in server.py's re-exports and in every module of
    server_tools/ that defines or imports it, since a function looks names up in its own module."""
    modules = [m for m in (server, *server_tools.MODULES) if name in vars(m)]
    assert len(modules) > 1, 'no server module binds %r' % name
    for m in modules:
        monkeypatch.setattr(m, name, value)


def server_source() -> str:
    """The server's code as text: server.py and every module of server_tools/."""
    texts = []
    for path in [cast(str, server.__file__)] + [cast(str, m.__file__) for m in server_tools.MODULES]:
        with open(path, encoding='utf-8') as f:
            texts.append(f.read())
    return '\n'.join(texts)


SELFTEST_DIR = os.path.join(ROOT, 'tests', 'test_all_tools')  # the live self-test, one module per category


def selftest_sources() -> dict[str, str]:
    """{file name: source} of every module of the live self-test."""
    sources: dict[str, str] = {}
    for name in sorted(os.listdir(SELFTEST_DIR)):
        if name.endswith('.py'):
            with open(os.path.join(SELFTEST_DIR, name), encoding='utf-8') as f:
                sources[name] = f.read()
    return sources


@pytest.fixture(autouse=True)
def guide_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool results start with a reminder until get_guide() was called; tests compare exact
    results, so they run as a session that has read the guide (test_guide.py covers the rest)."""
    monkeypatch.setitem(server._session, 'guide_read', True)


@pytest.fixture
def sbs_path() -> str:
    return os.path.join(FIXTURES, 'two_graphs.sbs')
