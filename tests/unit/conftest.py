"""Unit tests that run without Designer: import server.py and test its pure-Python parts."""

import os
import sys
import tempfile
import types
from typing import Any, cast

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
sys.path.insert(0, os.path.join(ROOT, 'mcp_server'))
sys.path.insert(0, ROOT)

import project_constants  # noqa: E402
import server as _server_module  # noqa: E402  (importing doesn't start the server or contact Designer)
import server_tools  # noqa: E402  (server.py's code, one module per area)

# server.py copies every name of server_tools/ into itself at import time, which mypy can't follow:
# as a plain module its attributes (server.describe_graph, server._bridge...) are Any to the checker.
server: types.ModuleType = _server_module
REAL_OWN_TEMP = server._own_temp  # the autouse fixture below replaces them
REAL_OWN_HOME = server._own_home
REAL_SHORT_TEMP = server.SHORT_TEMP
REAL_BIND_ERROR = server._bind_error  # binds a real socket: a Designer listening here would count
REAL_DESIGNER_PIDS = server._designer_pids  # runs pgrep
REAL_DESIGNER_RUNNING = server._designer_running  # runs pgrep (tasklist on Windows)
REAL_PROCESS_START = server._process_start  # runs ps
REAL_SAMPLE = server._sample  # runs macOS's sample on a process
# as the test run found it, before the autouse fixture below replaces it
REAL_SNAPSHOT_DIR = os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), '.sd_mcp', 'snapshots')


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


SELFTEST_DIR = os.path.join(ROOT, 'tests', 'test_all_tools')  # the live self-test, one folder per category


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


@pytest.fixture
def temp_folders(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The folders tempfile.mkdtemp makes, newest last, each named with a backslash where paths don't use one (macOS),
    as a Windows path has: a fake bridge takes its folder from here, never back out of the helper call, whose %r
    doubles a backslash (REVIEW.md TST-325, TST-330)."""
    made: list[str] = []
    real = tempfile.mkdtemp

    def mkdtemp(suffix: str | None = None, prefix: str | None = None, dir: str | None = None) -> str:
        made.append(real(suffix, (prefix or 'tmp') + ('back\\slash_' if os.sep == '/' else ''), dir))
        return made[-1]

    monkeypatch.setattr(tempfile, 'mkdtemp', mkdtemp)
    return made


@pytest.fixture(autouse=True)
def guide_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tools refuse until get_guide() was called, so tests run as a session that has read the guide, both parts
    (test_guide.py covers the rest)."""
    monkeypatch.setitem(server._session, 'guide_read', True)
    monkeypatch.setitem(server._session, 'scripting_read', True)


@pytest.fixture
def sbs_path() -> str:
    return os.path.join(FIXTURES, 'two_graphs.sbs')


@pytest.fixture(autouse=True)
def no_real_designer_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """No unit test looks at, or ends, a Designer really running here, reads the real record of who started it or
    the real bridge token, or removes the self-test's real snapshots."""
    patch_server(monkeypatch, '_designer_pids', list)
    # follows whatever _designer_pids gives now (REVIEW.md TST-147: it ran the real pgrep)
    patch_server(monkeypatch, '_designer_running', lambda: bool(server._designer_pids()))
    patch_server(monkeypatch, '_process_start', lambda pid: None)
    # a test's process IDs are made up: a real sample would read whatever process has one (ROADMAP item 70)
    patch_server(monkeypatch, '_sample', lambda pid, path: pytest.fail('a real process sampled: %d' % pid))
    patch_server(monkeypatch, '_own_temp', lambda port: str(tmp_path / ('T_%d' % port)) + os.sep)
    patch_server(monkeypatch, '_own_home', lambda port: None)
    # beside tmp_path, not in it: tests list what they put there (test_install.py)
    own = tmp_path_factory.mktemp('no_real_designer')
    (own / 'short').mkdir()  # exists, as /tmp does
    patch_server(monkeypatch, 'SHORT_TEMP', str(own / 'short'))  # not the real /tmp/sd_mcp_* folders
    patch_server(monkeypatch, '_listening_ports', lambda pid: set())  # listening nowhere yet: it may be on any port
    patch_server(monkeypatch, '_bind_error', lambda port: None)  # the user's Designer may hold the server's port
    monkeypatch.setitem(vars(project_constants), 'AGENT_RECORD_DIR', str(tmp_path))
    # the self-test's clean-up removes the snapshots of its graph there (common.remove_test_snapshots), which a live
    # run on the real folder still reads (REVIEW.md TST-230)
    monkeypatch.setenv('SD_SNAPSHOT_DIR', str(own / 'snapshots'))
    # a token of its own: the real one gives code execution in Designer, and a fresh clone has none (REVIEW.md
    # TST-165); sd_run.py, loaded by the tests that use it, takes it from project_constants
    token = own / 'clients_token'  # not test_plugin.py's tmp_path/'token', which its token tests start without
    token.write_text('t' * 64)
    patch_server(monkeypatch, 'TOKEN_FILE', str(token))
    monkeypatch.setitem(vars(project_constants), 'TOKEN_FILE', str(token))
