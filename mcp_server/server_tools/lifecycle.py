"""Designer itself: designer_status, launch_designer, quit_designer.

A Designer an agent started is disposable: it can be ended however works. Any other is the user's: the tools never end it.

Several Designers side by side (macOS; other platforms not tried). Designer is single-instance: starting, it reads the
ID of the last one started (`session.instancePID`, preferences plist) and looks for its socket (`algipc-...-<ID>`, 41
bytes) in its own temp folder; found, it hands over its arguments and exits (`[IPC] Found instance PID` in the log). So
launch_designer starts the binary, in `/`, with `SD_BRIDGE_PORT`, `TMPDIR=/tmp/sd_mcp_<uid>_<port>/temp/` (a socket path
has at most 103 bytes; under `/var/folders/...` it was too long and Designer made none) and, on macOS,
`CFFIXED_USER_HOME=.../home`: Designer then keeps its log, settings and crash-dump database there (not one byte to the
user's log, their `user_preferences.xml` left as it was) and loads user plugins from `SBS_DESIGNER_PYTHON_PATH`, set to
the plugin folders the user's Designer loads (its newest project file's, else Designer's default, where install.py puts
the plugin), then any value already set. `HOME` is unchanged, so the token is found. The preferences plist stays shared
(each Designer writes its `session.instancePID` there), so none is started next to the user's (`lsof`: listening on
another port). Tests: test_lifecycle_env.py, lifecycle.check_launch_on_another_port,
lifecycle.check_a_designer_sharing_the_temp_folder_hands_over.

Quitting. The window the user sees is a top-level `QStackedWidget` ("Adobe Substance 3D Designer"), not the hidden
`getMainWindow()`; closing the visible top-level widgets quits Designer normally, with a modal dialog open too. If a
window refuses to close, Qt 6's `QApplication.quit()` gives up too, and
`QApplication.exit(0)` stops the event loops, but Designer's teardown then races its own background threads: twice
Adobe's licence check (`Alg::BinaryHardeningService`, on a `QtConcurrent` thread) crashed reading a destroyed profile
and the process hung over 30 s. The shutdown can also hang at the very end, in `~QCoreApplication` waiting for the
thread pool (seen once with the licence check; a Python task held in `QThreadPool.globalInstance()` does it on demand).
In a full self-test run (2026-11-11) two Designers, just started, hung about 30 s after their close had taken, no crash
dump: the macOS system log shows their main thread silent from AppKit's termination on while another thread still
evaluated a certificate for the network work Designer starts with; not reproduced (ROADMAP item 69). Designer logs no
line of its teardown before its aboutToQuit handlers have run, so the quit helper logs QUIT_CLOSED once every window it
closed has closed, Designer's own among them, and a forced quit says from it whether its close had taken, as the
helper judged it (its limits: designer_helpers/quit.py), and quotes the last line of the log.
So quit_designer only closes the windows, and past its wait the server ends the process (SIGTERM, then SIGKILL), only
for a Designer an agent started. launch_designer records the process it started (its own child), its start time and, on
macOS, its home in `agent_designer_file(port)` (project_constants.py), one per port, so a /mcp reconnect keeps it and a
reused ID doesn't count; on Windows nothing is recorded, so every Designer counts as the user's. A close goes to
whichever Designer holds the port, so it names the recorded process and any other refuses (`os.getpid()` inside Designer
is that process, checked live). The plugin answers status from another thread, so a main thread frozen outside
a job reads as idle (measured with a timer slot sleeping in a loop).
"""

import contextlib
import errno
import glob
import json
import os
import re
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from collections.abc import Iterator
from textwrap import dedent
from xml.etree import ElementTree

from mcp.server.mcpserver.exceptions import ToolError

from project_constants import (  # on sys.path: the package's __init__ imports .core, which puts it there
    DESIGNER_PROCESS,
    PLUGIN,
    QUIT_CLOSED,
    QUIT_FORCED_IN_SHUTDOWN,
    QUIT_FORCED_NOT_CLOSED,
    SHORT_TEMP,
    STARTUP_LIMIT,
    agent_designer_file,
    agent_designer_ports,
    agent_folder_name,
)

from .core import (
    PORT,
    _bridge,
    _checked,
    _control,
    _designer_data_dir,
    _designer_running,
    _helpers_call,
    _Refused,
    _server_versions,
    _tool,
)


@_tool()
def designer_status(port: int | None = None) -> str:
    """Report Designer's version, the bridge state (idle/running) and the open user packages (an
    unsaved one by its UID, as list_snapshots names it), whether an agent started it, plus this server's Python and library versions. While a job runs or waits, the Designer
    version and package list are skipped: they would have to wait for the job.
    port: the Designer on that bridge port (launch_designer's port); this server's when omitted. The result also lists
    the Designers an agent started on other ports."""
    port = _port(port)
    state = _control('status', wait=10, port=port)
    if 'idle, 0 queued' not in state:  # the listing is a job too; it would queue (REVIEW.md SRV-22)
        return _lines(
            state,
            'Bridge port %d.' % port,
            _started_by(port),
            _others(port),
            _server_versions(),
            '(Designer version and package list skipped while a job runs)',
        )
    # an unsaved package is named by its UID, as list_snapshots names them (REVIEW.md SRV-45)
    listing = _bridge(
        dedent("""\
            import os
            import sd
            app = sd.getContext().getSDApplication()
            print('process', os.getpid())
            print('Designer', app.getVersion())
            for p in app.getPackageMgr().getUserPackages():
                print('package:', p.getFilePath() or '(an unsaved package, UID %s)' % p.getUID())
                for r in p.getChildrenResources(True):
                    print('   ', type(r).__name__, r.getIdentifier())
        """),
        port=port,
    )
    answering = re.search(r'^process (\d+)$', listing, re.M)
    started_by = _started_by(port, int(answering.group(1)) if answering else None)
    return _lines(state, 'Bridge port %d.' % port, started_by, _others(port), _server_versions(), listing)


def _lines(*parts: str) -> str:
    return '\n'.join(part for part in parts if part)


def _port(port: int | None) -> int:
    """The bridge port a lifecycle tool works on: this server's (PORT) unless one is given."""
    if port is None:
        return PORT
    if isinstance(port, bool) or not 1024 <= port <= 65535:
        raise ToolError('port must be a number from 1024 to 65535 (lower ones need root), not %r' % (port,))
    return port


def _started_by(port: int, answering: int | None = None) -> str:
    """Who started the Designer answering on `port`, or with its process unknown, the only one that may be there.
    Unclear means the user's."""
    running = [answering] if answering is not None else _sorted_out(port)[0]
    own = _agent_designer(port)
    if own is not None and running == [own]:
        return 'Started by an agent: disposable, nothing in it is kept.'
    return "Not started by an agent: it is the user's."


def _others(port: int) -> str:
    """The Designers an agent started on other ports, or nothing."""
    others = sorted((p, pid) for p, pid in _agents().items() if p != port)
    if not others:
        return ''
    return 'Designers an agent started on other ports: %s.' % ', '.join('%d (process %d)' % o for o in others)


DESIGNER_APP = {
    'darwin': '/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app',
    'win32': r'C:\Program Files\Adobe\Adobe Substance 3D Designer\Adobe Substance 3D Designer.exe',
}
DESIGNER_BINARY = 'Adobe Substance 3D Designer'  # macOS: in the app's Contents/MacOS


class _NoListing(ToolError):
    """pgrep couldn't list Designer's processes: an empty list would read as none running (REVIEW.md SRV-83)."""


def _designer_pids() -> list[int]:
    """Designer's processes, where one may be ended. None on Windows: ending one there hasn't been tried. Raises
    _NoListing when pgrep fails (exit code 2 or 3; 1 is nothing found)."""
    if sys.platform == 'win32':
        return []
    try:
        done = subprocess.run(['pgrep', '-f', DESIGNER_PROCESS], capture_output=True, text=True)
    except OSError as e:
        raise _NoListing("Designer's processes couldn't be listed: %s" % e) from e
    if done.returncode not in (0, 1):
        raise _NoListing(
            "Designer's processes couldn't be listed (pgrep exit code %d: %s)" % (done.returncode, done.stderr.strip())
        )
    return [int(pid) for pid in done.stdout.split()]


def _process_start(pid: int) -> str | None:
    """When `pid` started, as ps prints it in the C locale and UTC: the same text in every server whatever its own
    locale and time zone, since servers compare it with the one another recorded (REVIEW.md SRV-92)."""
    env = {**os.environ, 'LC_ALL': 'C', 'TZ': 'UTC'}
    try:
        done = subprocess.run(['ps', '-o', 'lstart=', '-p', str(pid)], capture_output=True, text=True, env=env)
    except OSError as e:
        raise _NoListing("the start of process %d couldn't be read: %s" % (pid, e)) from e
    if done.returncode == 0:
        return done.stdout.strip() or None
    if done.returncode == 1 and not done.stderr.strip():  # no such process (measured): it has ended
        return None
    # anything else is ps failing, not the process gone (REVIEW.md SRV-97)
    raise _NoListing(
        "the start of process %d couldn't be read (ps exit code %d: %s)" % (pid, done.returncode, done.stderr.strip())
    )


def _listening_ports(pid: int) -> set[int]:
    """The TCP ports a process listens on, from lsof; none when that can't be told."""
    try:
        out = subprocess.run(
            ['lsof', '-nP', '-a', '-p', str(pid), '-iTCP', '-sTCP:LISTEN', '-Fn'],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    return {int(found) for found in re.findall(r'^n.*:(\d+)$', out, re.M)}


def _own_home_path(port: int) -> str:
    """Where the home of the Designer launch_designer starts on `port` is (_own_home), whether or not it was made."""
    return os.path.join(SHORT_TEMP, agent_folder_name(port), 'home')


def _checked_folder(port: int) -> str | None:
    """The folder launch_designer makes for `port` (_own_folder's), if it is there and is this user's own folder, not a
    link: the only one anything is read from (REVIEW.md SRV-96: /tmp is shared, and another account may have made it
    first). Never made here. POSIX only."""
    folder = os.path.join(SHORT_TEMP, agent_folder_name(port))
    try:
        info = os.lstat(folder)
    except OSError:
        return None
    return folder if stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() else None


def _own_folder(port: int, part: str) -> str:
    """<SHORT_TEMP>/sd_mcp_<user ID>_<port>/<part>, made if missing: the folders of the Designer launch_designer starts
    on `port`. In /tmp, which is shared, so it must be the user's own; and short, for the temp folder's socket."""
    folder = os.path.join(SHORT_TEMP, agent_folder_name(port))
    try:  # a full or read-only /tmp, no permission: said as this, not as a bare OSError (REVIEW.md SRV-86)
        with contextlib.suppress(FileExistsError):
            os.mkdir(folder, 0o700)
        info = os.lstat(folder)
    except OSError as e:
        raise ToolError('No folder for the Designer on port %d (%s): %s' % (port, folder, e)) from e
    if info.st_uid != os.getuid():  # in sticky /tmp only its owner can remove it (REVIEW.md TST-186)
        raise ToolError(
            '%s is not a folder of this user: another account owns it, so launch on another port, or have that account '
            'remove it' % folder
        )
    if not stat.S_ISDIR(info.st_mode):
        raise ToolError('%s is not a folder of this user: remove it, then call this again' % folder)
    path = os.path.join(folder, part)
    try:
        os.makedirs(path, exist_ok=True)  # inside a folder only the user can write to
    except OSError as e:  # a file named as the folder, for one
        raise ToolError('No folder for the Designer on port %d (%s): %s' % (port, path, e)) from e
    return path


def _own_temp(port: int) -> str | None:
    """A temp folder of its own for the Designer started on `port`, or None (Windows: a second Designer there hasn't
    been tried). Why: Several Designers, in this module's docstring."""
    if sys.platform == 'win32':
        return None
    return _own_folder(port, 'temp') + os.sep


def _own_home(port: int) -> str | None:
    """A home of its own for the Designer started on `port` (CFFIXED_USER_HOME, CoreFoundation's: the module's
    docstring says what it holds), or None (not macOS)."""
    if sys.platform != 'darwin':
        return None
    return _own_folder(port, 'home')


def _plugin_paths() -> str:
    """SBS_DESIGNER_PYTHON_PATH for a Designer with a home of its own: the user plugin folders the user's Designer
    loads (its newest project file's, less Designer's own), or Designer's default, where install.py puts the plugin,
    then any value already set (Designer splits it: measured, ours loaded as the second of two)."""
    folders: list[str] = []
    projects = glob.glob(os.path.join(_designer_data_dir(), '*', 'default_project.sbsprj'))
    urls: list[str] = []
    if projects:
        # XML, read as XML: a & in a folder is stored as &amp;; one that can't be read is as none (REVIEW.md SRV-86)
        with contextlib.suppress(OSError, ElementTree.ParseError):
            root = ElementTree.parse(max(projects, key=os.path.getmtime)).getroot()
            urls = [url.text or '' for python in root.iter('python') for url in python.iter('url')]
    for url in urls:
        folder = urllib.parse.unquote(url[len('file://') :]) if url.startswith('file://') else ''
        if folder and '.app/Contents/' not in folder and folder not in folders:
            folders.append(folder)
    if not folders:
        folders.append(
            os.path.join(
                os.path.expanduser('~'), 'Documents', 'Adobe', 'Adobe Substance 3D Designer', 'python', 'sduserplugins'
            )
        )
    if os.environ.get('SBS_DESIGNER_PYTHON_PATH'):
        folders.append(os.environ['SBS_DESIGNER_PYTHON_PATH'])
    return os.pathsep.join(folders)


def _designer_env(port: int, temp: str | None, home: str | None, plugins: str) -> dict[str, str]:
    """The environment of a Designer started on `port`: the server's, less its Python settings, with the bridge port,
    a temp folder (TMPDIR) and a home of its own (CFFIXED_USER_HOME, with its plugin folders) when given. Shared by
    _start_designer and the self-test's hand-over check, which starts the binary itself (REVIEW.md TST-148)."""
    # the server's own Python settings aren't for Designer's Python (not seen: `open -a` never passed them on)
    env = {k: v for k, v in os.environ.items() if not k.startswith('PYTHON') and k != '__PYVENV_LAUNCHER__'}
    env['SD_BRIDGE_PORT'] = str(port)
    if temp:
        env['TMPDIR'] = temp
    if home:
        env['CFFIXED_USER_HOME'] = home
        env['SBS_DESIGNER_PYTHON_PATH'] = plugins
    return env


def _start_designer(app: str, port: int) -> tuple[int, str | None]:
    """Start Designer with SD_BRIDGE_PORT set, as its plugin reads the port there, and return its process ID and the
    home of its own it got (None: the user's). Its own binary, not `open -a`, which brings back a Designer already
    running and passes no environment (ROADMAP item 49)."""
    home = _own_home(port)
    env = _designer_env(port, _own_temp(port), home, _plugin_paths() if home else '')
    quiet = subprocess.DEVNULL
    try:
        if sys.platform == 'win32':
            detached = getattr(subprocess, 'DETACHED_PROCESS', 0x8) | getattr(
                subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x200
            )
            proc = subprocess.Popen([app], env=env, stdin=quiet, stdout=quiet, stderr=quiet, creationflags=detached)
        else:
            binary = os.path.join(app, 'Contents', 'MacOS', DESIGNER_BINARY) if os.path.isdir(app) else app
            # a session of its own and / as its folder, as `open -a` gave it: the server ending doesn't end it, and
            # nothing in the server's folder (the repository) is in Designer's
            proc = subprocess.Popen(
                [binary], env=env, stdin=quiet, stdout=quiet, stderr=quiet, start_new_session=True, cwd='/'
            )
    except OSError as e:
        raise ToolError('Designer could not be started from %r: %s; set SD_DESIGNER_APP' % (app, e)) from e
    # reaped when it exits, or it would linger as a zombie, its ID and start time still there; with the server gone
    # first, the system reaps it
    # reaps it once it ends; without it (no thread to be had) it is still the server's child, recorded as usual, only
    # left a zombie when it ends (REVIEW.md SRV-100)
    with contextlib.suppress(RuntimeError):
        threading.Thread(target=proc.wait, daemon=True).start()
    return proc.pid, home


def _record_error(port: int) -> OSError | None:
    """Why `port`'s record couldn't be written now (a file made and removed beside it), or None: checked before a
    start, so that none starts unrecorded (REVIEW.md SRV-93). Windows records nothing."""
    if sys.platform == 'win32':
        return None
    path = agent_designer_file(port)
    try:
        fd, probe = tempfile.mkstemp(dir=os.path.dirname(path), prefix=os.path.basename(path) + '.')
        os.close(fd)
        os.remove(probe)
    except OSError as e:
        return e
    return None


def _unrecorded(port: int, error: Exception, note: str, started: str) -> ToolError:
    return ToolError(
        "%s%s: its record could not be written in %s (%s), so it would count as the user's and quit_designer could "
        'not end it.' % (note, started, os.path.dirname(agent_designer_file(port)), error)
    )


def _remember_started(port: int, pid: int, home: str | None) -> None:
    """Record the process launch_designer started for `port`: its own child, so no other can be taken for it; and
    its home, where it writes its log (None: the user's). OSError when the record can't be written; nothing when the
    process has already ended."""
    if sys.platform == 'win32':  # nothing counts as an agent's there (ROADMAP item 18)
        return
    start = _process_start(pid)
    if start is None:
        return
    # written whole, then put in place: a server reading it meanwhile sees the old record or none, never part of one,
    # which it would delete as unreadable (REVIEW.md SRV-83)
    path = agent_designer_file(port)
    fd, written = tempfile.mkstemp(dir=os.path.dirname(path), prefix=os.path.basename(path) + '.')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump({'pid': pid, 'start': start, 'home': home}, f)
        os.replace(written, path)
    except OSError:
        with contextlib.suppress(OSError):
            os.remove(written)
        raise


@contextlib.contextmanager
def _launch_lock(port: int) -> Iterator[None]:
    """One launch at a time on `port`, across servers: held while deciding to start a Designer and recording it, not
    during the wait for it to answer (REVIEW.md SRV-83). A lock file in the port's folder, released if its holder dies.
    Not on Windows, where nothing is recorded."""
    if sys.platform == 'win32':
        yield
        return
    import fcntl

    with open(os.path.join(_own_folder(port, ''), 'launch.lock'), 'a', encoding='utf-8') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


@contextlib.contextmanager
def _launch_lock_if_free(port: int) -> Iterator[bool]:
    """_launch_lock, only if no one holds it: True then. Never waits for it (Windows: nothing is recorded or locked)."""
    if sys.platform == 'win32':
        yield True
        return
    import fcntl

    try:
        lock = open(os.path.join(_own_folder(port, ''), 'launch.lock'), 'a', encoding='utf-8')  # noqa: SIM115
    except (OSError, ToolError):
        lock = None
    held = False
    if lock is not None:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            held = True
        except OSError:
            pass
    try:
        yield held
    finally:
        if lock is not None:
            if held:
                fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()


def _forget_started(port: int, seen: bytes) -> None:
    """Remove `port`'s record if it still holds `seen`, the one the caller decided on: another server may have put a
    new one in place meanwhile (REVIEW.md SRV-91). Under the port's launch lock, which that server held while writing,
    and only if it is free: a launch holding it reads every port's records itself, so waiting could deadlock two
    servers; a stale record left is never matched, and the next launch replaces it."""
    with _launch_lock_if_free(port) as held:
        if not held:
            return
        path = agent_designer_file(port)
        with contextlib.suppress(OSError):
            with open(path, 'rb') as f:
                if f.read() != seen:
                    return
            os.remove(path)


def _record_bytes(port: int) -> bytes | None:
    try:
        with open(agent_designer_file(port), 'rb') as f:
            return f.read()
    except OSError:
        return None


def _agent_record(port: int) -> tuple[int, bytes] | None:
    """The process ID of the Designer an agent started on `port`, if it is still running, with its record as read
    (what _forget_started is given). The start time tells it from a later process given the same ID. Anything unclear
    means it isn't an agent's, and a stale record goes, unless it was replaced meanwhile."""
    seen = _record_bytes(port)
    if seen is None:
        return None
    try:
        record = json.loads(seen)
        pid, start = record['pid'], record['start']
        if not isinstance(pid, int):
            raise TypeError
        try:
            listed: bool | None = pid in _designer_pids()
        except _NoListing:
            listed = None
        try:
            same = listed is not False and _process_start(pid) == start
        except _NoListing:  # can't tell: not taken for an agent's meanwhile, and the record is kept (REVIEW.md SRV-97)
            return None
        if listed is None:  # its start time alone tells; gone or not, the record is kept (REVIEW.md SRV-83)
            return (pid, seen) if same else None
        if listed and same:
            return pid, seen
    except (ValueError, KeyError, TypeError):
        pass
    _forget_started(port, seen)
    return None


def _agent_designer(port: int) -> int | None:
    """The process ID of the Designer an agent started on `port`, if it is still running (_agent_record)."""
    found = _agent_record(port)
    return found[0] if found else None


def _agent_home(port: int) -> str | None:
    """The home the Designer an agent started on `port` got, if it still runs: None for the user's (no home of its own,
    a record without one: older code started it, or not macOS) or when no agent's runs there."""
    if _agent_designer(port) is None:
        return None
    try:
        with open(agent_designer_file(port), encoding='utf-8') as f:
            home = json.load(f).get('home')
    except (OSError, ValueError, AttributeError):
        return None
    return home if isinstance(home, str) else None


def _agents() -> dict[int, int]:
    """{port: process ID} of the Designers an agent started that still run."""
    found = {}
    for port in agent_designer_ports():
        pid = _agent_designer(port)
        if pid is not None:
            found[port] = pid
    return found


def _sorted_out(port: int) -> tuple[list[int], list[int]]:
    """Designer's processes as `port` sees them: those that may hold it, and those no agent started that listen on
    other ports but not this one (the user's, on their own). The ones an agent started on other ports are in neither.
    One listening nowhere yet may still be starting on this port."""
    agents = _agents()
    elsewhere = {pid for p, pid in agents.items() if p != port}
    here: list[int] = []
    users: list[int] = []
    for pid in _designer_pids():
        if pid in elsewhere:
            continue
        ports = set() if pid == agents.get(port) else _listening_ports(pid)
        (users if ports and port not in ports else here).append(pid)
    return here, users


def _running_on(port: int) -> bool:
    """Whether a Designer that may hold `port` runs. Processes that can't be listed (Windows) all may."""
    if not _designer_running():
        return False
    return not _designer_pids() or bool(_sorted_out(port)[0])


def _still_starting(port: int) -> bool:
    """Whether the record, written as the process started, is younger than STARTUP_LIMIT."""
    try:
        return time.time() - os.path.getmtime(agent_designer_file(port)) < STARTUP_LIMIT
    except OSError:
        return False


def _force_end(pid: int, port: int, seen: bytes) -> bool:
    """End `pid`, the Designer an agent started on `port`, whose record was `seen`."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, sig)
        for _ in range(5):
            if pid not in _designer_pids():
                _forget_started(port, seen)
                return True
            time.sleep(1)
    return False


def _end_if_past_startup(port: int) -> bool:
    """End the Designer an agent started on `port`, unless it may still be starting: it is disposable, so it isn't
    waited for past that (REVIEW.md HLP-82), but a retry mustn't kill one that is only slow (REVIEW.md SRV-75)."""
    found = _agent_record(port)
    if found is None or _still_starting(port):
        return False
    own, seen = found
    if not _force_end(own, port, seen):
        raise ToolError(_could_not_end(own))  # once is enough (REVIEW.md SRV-79)
    return True


def _could_not_end(pid: int) -> str:
    return 'Designer %d could not be ended; ask the user to run `kill -9 %d`.' % (pid, pid)


def _how_to_end(port: int) -> str:
    """What the user can do about a Designer the tools won't end."""
    pids = _sorted_out(port)[0] or _designer_pids()
    if not pids:
        return 'ask the user to end it in Task Manager'
    if len(pids) > 1:
        return (
            'ask the user to check which of the Designers %s it is, and to end that one in Activity Monitor, or with `kill <ID>` (`kill -9 <ID>` if it stays)'
            % ', '.join(map(str, pids))
        )
    return 'ask the user to end it in Activity Monitor, or with `kill %d` (`kill -9 %d` if it stays)' % (
        pids[0],
        pids[0],
    )


def _bind_error(port: int) -> OSError | None:
    """Why the plugin couldn't listen on `port` now, or None if it could: bound as the plugin binds it (127.0.0.1, with
    SO_REUSEADDR; on Windows SO_EXCLUSIVEADDRUSE). Measured on macOS: a program listening on 127.0.0.1 holds it, one on
    every address (*:5000, AirPlay's) doesn't, and 127.0.0.1 then reaches the plugin (REVIEW.md SRV-85); a port that is
    only a connection's local end, or left in TIME_WAIT, doesn't either (REVIEW.md SRV-90)."""
    with socket.socket() as probe:
        if sys.platform == 'win32':
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(('127.0.0.1', port))
        except OSError as e:
            return e
    return None


def _unusable_port(port: int, error: OSError, note: str) -> ToolError:
    """The refusal to start a Designer on a port the plugin couldn't listen on, saying why (REVIEW.md SRV-90)."""
    own = " (for this server's own port, set SD_BRIDGE_PORT for Designer and the server alike: README, Configuration)"
    in_use = error.errno in {errno.EADDRINUSE, getattr(errno, 'WSAEADDRINUSE', errno.EADDRINUSE)}
    # lsof without root lists only this account's sockets (measured: two listeners netstat shows, which it doesn't name)
    which = (
        ' `lsof -nP -iTCP:%d -sTCP:LISTEN` names it if it runs as you, `sudo lsof -nP -iTCP:%d -sTCP:LISTEN` if '
        'another account runs it.' % (port, port)
        if in_use and sys.platform != 'win32'
        else ''
    )
    what = 'is held by another program (%s), not the %s bridge' if in_use else "can't be used for the bridge (%s)"
    return ToolError(
        '%sPort %d %s: a Designer started now could not listen on it. Nothing was started; choose another port%s.%s'
        % (note, port, what % ((error, PLUGIN) if in_use else (error,)), own if port == PORT else '', which)
    )


def _users_next_to(port: int, note: str) -> ToolError | None:
    """The refusal to start a Designer on `port` next to one the user opened on another, if one runs."""
    users = _sorted_out(port)[1]
    if not users:
        return None
    ports = sorted(set().union(*(_listening_ports(pid) for pid in users)))
    return ToolError(
        '%sA Designer no agent started is running (%s %s, on %s %s): none is started next to it, since Designers '
        "share Designer's preferences plist. To start one on port %d, ask the user to close it."
        % (
            note,
            'process' if len(users) == 1 else 'processes',
            ', '.join(map(str, users)),
            'port' if len(ports) == 1 else 'ports',
            ', '.join(map(str, ports)),
            port,
        )
    )


@_tool()
def launch_designer(wait_s: int = 180, port: int | None = None) -> str:
    """Start Substance Designer if it isn't running and wait until the bridge plugin answers.
    When it starts Designer it also closes the Home screen, so the editor panels are visible.
    A Designer that is running but not answering yet is waited for, not started again; if it exits
    during the wait, a new one is started and gets its own wait_s, so the call can then take up to
    about twice wait_s. One an agent started is waited for only until 180 s after it started; past that, not answering,
    it is ended and a new one started, and the result says so.
    port (1024-65535): the bridge port the Designer's plugin listens on; this server's (SD_BRIDGE_PORT, 9877 by
    default) when omitted. On macOS, Designers an agent started run side by side, one per port, each recorded on its
    own (other platforms not tried; on Windows nothing is recorded, and with any Designer running none is started);
    designer_status, quit_designer and read_designer_log take the same port. The other tools reach only this server's
    port: one on another is for a server or client/sd_run.py started with SD_BRIDGE_PORT set to it. None is started
    next to a Designer the user opened, on another port (GUIDE.md, Several Designers). None is started on a
    port the plugin couldn't listen on (another program holds it; the result gives the error), nor where its record
    can't be written (unrecorded, it would count as the user's); a plugin of another bridge protocol (another version)
    is reported at once.
    For tests and work on this project: if a task needs Designer and it is closed, ask the user to open it.
    Override the app location with SD_DESIGNER_APP (on macOS the .app, whose own binary is started)."""
    port = _port(port)
    try:
        return 'Designer already running on port %d: %s' % (port, _control('status', wait=5, port=port))
    except _Refused:
        raise  # it runs and answers: starting or waiting for another wouldn't help
    except ToolError:
        pass
    # A Designer process without an answering bridge (still starting, a dialog, the plugin didn't
    # load) is waited for, not started again (Windows would open a second instance). If it exits
    # while we wait (it was shutting down, or hung after a crash), a new one is started then.
    app = os.environ.get('SD_DESIGNER_APP') or DESIGNER_APP.get(sys.platform)

    ended_note = 'Ended a Designer an agent started, which was not answering.\n'
    note = ended_note if _end_if_past_startup(port) else ''

    def start() -> bool:
        """Start one, unless another launch on this port started one meanwhile: False then, and that one is waited
        for (REVIEW.md SRV-83)."""
        with _launch_lock(port):
            if _running_on(port):
                return False
            if not app or not os.path.exists(app):
                raise ToolError('%sDesigner not found at %r; set SD_DESIGNER_APP' % (note, app))
            refusal = _users_next_to(port, note)
            if refusal:
                raise refusal
            unbindable = _bind_error(port)
            if unbindable:  # before the start: it would wait out wait_s and stay running (REVIEW.md SRV-85)
                raise _unusable_port(port, unbindable, note)
            unwritable = _record_error(port)
            if unwritable:  # unrecorded, it would count as the user's (REVIEW.md SRV-93)
                raise _unrecorded(port, unwritable, note, 'No Designer was started')
            pid, home = _start_designer(app, port)
            try:
                _remember_started(port, pid, home)
            except (OSError, _NoListing) as e:  # the folder filled, or its start can't be read (REVIEW.md SRV-97)
                try:
                    ended = _force_end(pid, port, b'')  # its own child, just started: certainly an agent's
                except _NoListing:  # its end can't be seen either: said, with what to do (REVIEW.md SRV-100)
                    ended = False
                if ended:
                    raise _unrecorded(port, e, note, 'Designer (process %d) was started, then ended' % pid) from e
                started = 'Designer (process %d) was started and could not be ended (ask the user to run `kill -9 %d`)'
                raise _unrecorded(port, e, note, started % (pid, pid)) from e
            return True

    running, restarted = _running_on(port), False
    if not running:
        running = not start()
    started = time.time()
    while time.time() - started < wait_s:
        time.sleep(2)
        try:
            status = _control('status', wait=5, port=port)
        except _Refused:
            raise
        except ToolError:
            if running and _end_if_past_startup(port):
                note = ended_note
            if running and not _running_on(port):  # it exited, or turned out to be the user's on another port
                restarted = True
                running = not start()
                started = time.time()  # the new one gets the whole wait (REVIEW.md SRV-19)
            continue
        if running:
            return note + 'Designer already running on port %d: %s' % (port, status)
        # we started it, so nobody is using the Home screen: show the editor panels
        home = _bridge(_helpers_call('leave_home_screen()'), timeout=30, port=port).strip()
        return note + 'Designer started in %.0fs, on port %d%s: %s' % (
            time.time() - started,
            port,
            ' (%s)' % home if home else '',
            status,
        )
    if not running:
        what_next = (
            ' If it needs longer, call this with a larger wait_s.'  # a retry may never finish (REVIEW.md SRV-80)
        )
    elif _agent_designer(port) is not None:
        what_next = (
            ' An agent started it: calling this again waits for it, and ends it once it has had %ds to start.'
            % STARTUP_LIMIT
        )
    else:
        what_next = (
            ' If its windows have closed, it is stuck closing and nothing is lost: %s. If they are open, ask the user to '
            'save and close it.' % _how_to_end(port)
        )
    raise ToolError(
        '%s%s did not answer within %ds%s. It may be showing a dialog, or the %s plugin did not load (check the '
        'Designer log).%s'
        % (
            note,
            'Designer is already running, but its bridge' if running else 'Designer',
            wait_s,
            ' of being started' if restarted else '',
            PLUGIN,
            what_next,
        )
    )


@_tool()
def quit_designer(wait_s: int = 10, port: int | None = None) -> str:
    """Close a Designer an agent started, and wait until its process has exited: unsaved changes are dropped, and after
    wait_s it is force-ended; the result says which and, if forced, whether its close had taken (its own shutdown
    then hung) and the last line of its log. Running a job, it isn't asked to close. Not replying to the close within
    wait_s (at least 10 s) adds that to the wait. Any other Designer is the user's: this ends nothing and says to ask them to save, close and reopen it.
    port: the one on that bridge port (launch_designer's port); this server's when omitted. Others are left alone."""
    port = _port(port)
    found = _agent_record(port)
    if found is None:
        if not _designer_running():
            return 'Designer is not running.'
        if not _running_on(port):
            return _lines('No Designer is running on port %d.' % port, _others(port))
        raise ToolError("This Designer wasn't started by an agent: ask the user to save, close and reopen it.")
    own, seen = found
    try:
        state = _control('status', wait=5, port=port)
        if 'idle, 0 queued' not in state:  # the close would queue behind it, for up to 15 minutes (REVIEW.md SRV-74)
            raise ToolError('busy: %s' % state)
        # it goes to whichever Designer holds the port, so it names this one and any other refuses (REVIEW.md SRV-73)
        call = _helpers_call('quit_designer(%d, %r)' % (own, QUIT_CLOSED))
        # a frozen main thread reads as idle too, and a close running late runs in the process being ended (REVIEW.md SRV-78)
        reply = _bridge(call, timeout=30, wait=max(wait_s, 10), port=port)
        notes = _checked(reply).replace('closing Designer', '').strip()
    except ToolError as e:  # it can't be asked, only ended; or the reply was lost as it quit
        notes = 'Designer was not asked to close, or did not reply: %s' % e
    prefix = notes + '\n' if notes else ''
    started = time.time()
    while time.time() - started < wait_s:
        time.sleep(1)
        if own not in _designer_pids():
            _forget_started(port, seen)  # only its own: another server may have recorded a new one (REVIEW.md SRV-91)
            return prefix + 'Designer quit after %.0fs.' % (time.time() - started)
    from .log import _quit_evidence  # here: log.py imports from this module

    evidence = _quit_evidence(port)  # read while it still runs: how far its quit got
    if own not in _designer_pids():  # it ended while that was read: by itself (REVIEW.md SRV-108)
        _forget_started(port, seen)
        return prefix + 'Designer quit after %.0fs.' % (time.time() - started)
    if _force_end(
        own, port, seen
    ):  # it can hang in its own shutdown, past anything inside it (REVIEW.md HLP-82, ROADMAP item 69)
        took = time.time() - started
        if evidence is None:
            return prefix + 'Designer quit after %.0fs (forced; its log could not be read).' % took
        closed, last = evidence
        how = QUIT_FORCED_IN_SHUTDOWN + ': its close had taken' if closed else QUIT_FORCED_NOT_CLOSED
        return prefix + 'Designer quit after %.0fs (%s; its log stopped at "%s").' % (took, how, last)
    raise ToolError(_could_not_end(own))
