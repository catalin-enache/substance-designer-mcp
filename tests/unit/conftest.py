"""Unit tests that run without Designer: import server.py and test its pure-Python parts."""

import builtins
import configparser
import errno
import json
import os
import re
import sys
import tempfile
import types
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import IO, TypedDict, cast
from unittest import mock

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
sys.path.insert(0, os.path.join(ROOT, 'mcp_server'))
sys.path.insert(0, ROOT)

from fake_defaults import FakeDefaults  # noqa: E402  (imports designer_preferences, from ROOT)

import designer_helpers  # noqa: E402
import designer_preferences  # noqa: E402
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
REAL_EXIT_WATCH = server._exit_watch  # watches a real process's exit (macOS: a kqueue)
REAL_FOUND_LAUNCHED = server._found_launched  # runs pgrep and ps -E
REAL_PROCESS_START = server._process_start  # runs ps
REAL_SAMPLE = server._sample  # runs macOS's sample on a process
REAL_PLUGIN_PATHS = server._plugin_paths  # reads the user's newest Designer project file
REAL_RUN_DEFAULTS = designer_preferences.run_defaults  # runs macOS's defaults, on the user's preferences
REAL_USERS_DATA_DIR = designer_preferences.users_data_dir  # the user's Designer's folder, its log in it
# as the test run found it, before the autouse fixture below replaces it
REAL_SNAPSHOT_DIR = os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), '.sd_mcp', 'snapshots')


def patch_server(monkeypatch: pytest.MonkeyPatch, name: str, value: object) -> None:
    """monkeypatch.setattr for a server name: in server.py's re-exports and in every module of
    server_tools/ that defines or imports it, since a function looks names up in its own module."""
    modules = [m for m in (server, *server_tools.MODULES) if name in vars(m)]
    assert len(modules) > 1, 'no server module binds %r' % name
    for m in modules:
        monkeypatch.setattr(m, name, value)


class RunOptions(TypedDict, total=False):
    """The keyword arguments this repository's code passes to subprocess.run. A fake of subprocess.run takes them."""

    capture_output: bool
    text: bool
    check: bool
    timeout: float
    env: dict[str, str]
    cwd: str | None
    input: bytes
    encoding: str
    errors: str


class DumpOptions(TypedDict, total=False):
    """The keyword arguments of json.dump and json.dumps, as typeshed lists them, without their **kwds. A fake of
    either passes them on."""

    skipkeys: bool
    ensure_ascii: bool
    check_circular: bool
    allow_nan: bool
    cls: type[json.JSONEncoder] | None
    indent: int | str | None
    separators: tuple[str, str] | None
    default: Callable[[object], object] | None  # called with what JSON can't hold; returns what it can
    sort_keys: bool


class LoadOptions(TypedDict, total=False):
    """The keyword arguments of json.loads, as typeshed lists them, and JSONDecoder's `strict`, which json.loads passes
    on to it. A fake of json.loads passes them on."""

    cls: type[json.JSONDecoder] | None
    object_hook: Callable[[dict[str, object]], object] | None
    parse_float: Callable[[str], object] | None
    parse_int: Callable[[str], object] | None
    parse_constant: Callable[[str], object] | None
    object_pairs_hook: Callable[[list[tuple[str, object]]], object] | None
    strict: bool


class View3dOptions(TypedDict, total=False):
    """The keyword arguments of the 3D view's set-up: set_3d_view's, and shoot_3d's after its path
    (designer_helpers/view3d.py, shot3d.py)."""

    graph: str | None
    mesh: str | None
    view: str | None
    zoom: int
    tiling: float | None
    orbit: Sequence[float] | None  # a tuple from screenshot_designer (REVIEW.md HLP-188)
    pan: Sequence[float] | None
    environment: str | None
    environment_rotation: float | None
    environment_exposure: float | None


# What builtins.open takes as its file: typeshed's FileDescriptorOrPath, which exists for the checker only.
OpenedFile = int | str | bytes | os.PathLike[str] | os.PathLike[bytes]


def full_disk(monkeypatch: pytest.MonkeyPatch, full: Callable[[str, str], bool], opened_first: bool = False) -> None:
    """Fakes builtins.open: opening a file for which full(file, mode) is true fails as on a full disk. With
    `opened_first`, the file is opened first, and so created or emptied, then the write fails."""
    real_open = builtins.open

    def fake_open(
        file: OpenedFile,
        mode: str = 'r',
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
        closefd: bool = True,
        opener: Callable[[str, int], int] | None = None,
    ) -> IO[str] | IO[bytes]:
        if full(str(file), mode):
            if opened_first:
                real_open(file, mode, buffering, encoding, errors, newline, closefd, opener).close()
            raise OSError(errno.ENOSPC, 'No space left on device')
        return real_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    monkeypatch.setattr(builtins, 'open', fake_open)


def fake_bridge(monkeypatch: pytest.MonkeyPatch, answer: Callable[[str], str]) -> None:
    """Fakes server._bridge with a function of its signature. Each call returns answer(code), for the code it was given.
    A fake that reads the other arguments is written out in its test instead."""

    def bridge(
        code: str,
        path: str | None = None,
        timeout: float | None = None,
        wait: float | None = None,
        port: int | None = None,
    ) -> str:
        return answer(code)

    patch_server(monkeypatch, '_bridge', bridge)


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The code each tool call sends to Designer, through a bridge that answers nothing: a test of a refusal asserts it
    stays empty."""
    calls: list[str] = []

    def bridge(code: str) -> str:
        calls.append(code)
        return ''

    fake_bridge(monkeypatch, bridge)
    return calls


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


# The scripts a user starts, with whatever python3 is installed: each refuses a Python older than the minimum before any
# other import, and keeps to the syntax Python 3.9 parses (DECISIONS.md, Project rules; test_old_python.py)
ENTRY_SCRIPTS = (
    'client/sd_run.py',
    'install.py',
    'scripts/read_crash_dump.py',
    'scripts/review_lookup.py',
    'uninstall.py',
)
# The server, started by Claude Code with the venv's Python, which an older Python may have made: it refuses one the same
# way, saying to run install.py again (REVIEW.md SRV-176)
SERVER_SCRIPT = 'mcp_server/server.py'
VERSION_CHECKED = (*ENTRY_SCRIPTS, SERVER_SCRIPT)  # each checks the Python first, readable by 3.9


# what runs the suite's checks rather than being one: its own tool calls (launch_designer, quit_designer...) mustn't
# count as the suite exercising a tool
SELFTEST_RUNNERS = ('alone.py',)


def mypy_config() -> configparser.SectionProxy:
    """The [mypy] section of mypy.ini."""
    config = configparser.ConfigParser()
    config.read(os.path.join(ROOT, 'mypy.ini'), encoding='utf-8')
    return config['mypy']


def mypy_files() -> list[str]:
    """The folders mypy.ini's `files` names, as written: `.`, and each hidden folder holding Python files of the
    repository's own, which mypy's search of `.` skips (test_types.py)."""
    return [entry.strip() for entry in mypy_config()['files'].split(',')]


def selftest_check_sources() -> dict[str, str]:
    """selftest_sources() without SELFTEST_RUNNERS: what the coverage checks read."""
    return {name: source for name, source in selftest_sources().items() if name not in SELFTEST_RUNNERS}


@pytest.fixture
def faked_helpers(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """The helpers as Designer runs them (designer_helpers.source(), one script) in a module of their own, every sd and
    PySide6 module they import faked by one MagicMock, and sd's APIException a BaseException, as in Designer. A test
    file's `helpers` fixture takes it and adds what its tests need."""
    fake = mock.MagicMock()
    imported = re.findall(r'^\s*(?:from|import) ((?:sd|PySide6)(?:\.\w+)*)', designer_helpers.source(), re.M)
    for name in sorted({'.'.join(m.split('.')[:i]) for m in imported for i in range(1, m.count('.') + 2)}):
        monkeypatch.setitem(sys.modules, name, fake)
    module = types.ModuleType('helpers_under_test')
    exec(compile(designer_helpers.source(), 'designer_helpers', 'exec'), module.__dict__)
    vars(module)['APIException'] = type('APIException', (BaseException,), {})
    return module


class FakeGraph:
    """Stands for a compositing graph, with its identifier and its package. A test sets the helpers' SDSBSCompGraph to
    this class, so that their isinstance checks take a FakeGraph for a compositing graph."""

    def __init__(self, identifier: str, package: mock.MagicMock) -> None:
        self.identifier, self.package = identifier, package

    def getIdentifier(self) -> str:
        return self.identifier

    def getPackage(self) -> mock.MagicMock:
        return self.package


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
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """No unit test looks at, or ends, a Designer really running here, reads the real record of who started it, the
    real bridge token or the user's project file, or removes the self-test's real snapshots."""
    patch_server(monkeypatch, '_designer_pids', list)
    # follows whatever _designer_pids gives now (REVIEW.md TST-147: it ran the real pgrep)
    patch_server(monkeypatch, '_designer_running', lambda: bool(server._designer_pids()))
    patch_server(monkeypatch, '_process_start', lambda pid: None)
    # a test's process IDs are made up: watched, a real process's exit would be waited for (REVIEW.md SRV-150)
    patch_server(monkeypatch, '_exit_watch', lambda pid: None)
    # the process `open` started: in a test, the fake opener's own (REVIEW.md SRV-152)
    patch_server(monkeypatch, '_found_launched', lambda opener, before, marks: opener.pid)
    # a test's process IDs are made up: a real sample would read whatever process has one (ROADMAP item 70)
    patch_server(monkeypatch, '_sample', lambda pid, path: pytest.fail('a real process sampled: %d' % pid))
    patch_server(monkeypatch, '_own_temp', lambda port: str(tmp_path / ('T_%d' % port)) + os.sep)
    patch_server(monkeypatch, '_own_home', lambda port: None)
    # a launch with a home of its own: not the plugin folders the user's own project file lists (REVIEW.md TST-379)
    patch_server(monkeypatch, '_plugin_paths', lambda: str(tmp_path / 'plugins'))
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


@pytest.fixture(autouse=True)
def defaults(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> FakeDefaults:
    """No unit test reads or writes the user's preferences plist, or reads their Designer's log: `defaults` is a fake
    holding one domain (empty until a test fills it), and the user's data folder and plist file the test's (the folder
    empty, the file not there). Its copy goes in AGENT_RECORD_DIR, the test's (no_real_designer_process). `defaults`
    itself points nowhere, so a call that bypassed run_defaults would fail rather than reach the user's file (REVIEW.md
    TST-360)."""
    fake = FakeDefaults(tmp_path_factory.mktemp('users_designer_data'), tmp_path_factory.mktemp('users_preferences'))
    monkeypatch.setitem(vars(designer_preferences), 'run_defaults', fake)
    monkeypatch.setitem(vars(designer_preferences), 'users_data_dir', lambda: str(fake.users_data))
    monkeypatch.setitem(vars(designer_preferences), 'plist_file', lambda: str(fake.plist))
    monkeypatch.setitem(vars(designer_preferences), 'DEFAULTS', str(fake.users_data / 'no_defaults_here'))
    return fake
