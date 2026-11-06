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
    """{path from the self-test's folder: source} of its Python files, the scripts of designer_scripts/ included."""
    sources: dict[str, str] = {}
    for folder, _, files in os.walk(SELFTEST_DIR):  # what designer_scripts/ runs inside Designer counts too
        for name in sorted(files):
            if name.endswith('.py'):
                path = os.path.join(folder, name)
                with open(path, encoding='utf-8') as f:
                    sources[os.path.relpath(path, SELFTEST_DIR)] = f.read()
    return sources


# what runs the suite's checks rather than being one: its own tool calls (launch_designer, quit_designer...) mustn't
# count as the suite exercising a tool
SELFTEST_RUNNERS = ('alone.py',)


def selftest_check_sources() -> dict[str, str]:
    """selftest_sources() without SELFTEST_RUNNERS: what the coverage checks read."""
    return {name: source for name, source in selftest_sources().items() if name not in SELFTEST_RUNNERS}


@pytest.fixture(autouse=True)
def guide_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool results start with a reminder until get_guide() was called; tests compare exact
    results, so they run as a session that has read the guide (test_guide.py covers the rest)."""
    monkeypatch.setitem(server._session, 'guide_read', True)


@pytest.fixture
def sbs_path() -> str:
    return os.path.join(FIXTURES, 'two_graphs.sbs')


@pytest.fixture(autouse=True)
def no_real_designer_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """No unit test looks at, or ends, a Designer really running here, or reads the real record of who started it."""
    patch_server(monkeypatch, '_designer_pids', list)
    patch_server(monkeypatch, 'agent_designer_file', lambda: str(tmp_path / 'agent_designer.json'))
