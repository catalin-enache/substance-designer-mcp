"""Designer itself: designer_status, launch_designer, quit_designer.

A Designer an agent started is disposable: it can be ended however works. Any other is the user's: the tools never end it.

Several Designers side by side (macOS; other platforms not tried). Designer is single-instance: starting, it reads the
ID of the last one started (`session.instancePID`, preferences plist) and looks for its socket (`algipc-...-<ID>`, 41
bytes) in its own temp folder; found, it hands over its arguments and exits (`[IPC] Found instance PID` in the log). So
launch_designer starts Designer (on macOS an app bundle through `open`: below), in `/`, with `SD_BRIDGE_PORT`, `TMPDIR=/tmp/sd_mcp_<uid>_<port>/temp/` (a socket path
has at most 103 bytes; under `/var/folders/...` it was too long and Designer made none) and, on macOS,
`CFFIXED_USER_HOME=.../home`: Designer then keeps its log, settings and crash-dump database there (not one byte to the
user's log, their `user_preferences.xml` left as it was) and loads user plugins from `SBS_DESIGNER_PYTHON_PATH`, set to
the plugin folders the user's Designer loads (its newest project file's, else Designer's default, where install.py puts
the plugin), then any value already set. `HOME` is unchanged, so the token is found. The preferences plist stays shared
(each Designer writes its `session.instancePID` there), so none is started next to the user's (`lsof`: listening on
another port), nor next to one that appears as a launch starts, mostly while it puts the file back first (_appeared,
under the lock it is saved under, which a launch holds until its Designer is recorded or ended); what agents' Designers
change in it is put back once none runs (designer_preferences.py).
Tests: test_lifecycle_env.py, lifecycle.check_launch_on_another_port,
lifecycle.check_a_designer_sharing_the_temp_folder_hands_over.

Starting hidden (macOS, measured 2026-11-15). Started from its binary, as below, a Designer's window still came up in
front of the active app's for up to 5.66 s in later launches (REVIEW.md SRV-152). So an app bundle is opened by `open -n
-g -j` (_opened): a new instance, not brought to the front, hidden; in 4 of 4 launches none of its windows showed and
it was never the active app. `open` says no process ID: the new process whose environment has the launch's port and
its home is its (_found_launched; the port alone is in a Designer the user starts with SD_BRIDGE_PORT set: REVIEW.md
SRV-165).

Starting behind the app in front (macOS, measured 2026-11-15, from Designer's binary). Designer's Qt (6.8.6) makes the app the active one as it
finishes launching, unless `QT_MAC_DISABLE_FOREGROUND_APPLICATION_TRANSFORM` (STAY_BEHIND) is set, so launch_designer
sets it. Watched from another process every 50 ms, with another app in front:
- without it, a Designer was the active app for 4.6 s of its start, and its window was in front of the other apps' for
  1.9 s. The user's typing went into it.
- with it, in four launches (two with `QT_MAC_SET_RAISE_PROCESS=0` too), Designer was never the active app, and its
  window was never the frontmost. It came up behind the active app's window, but over the other apps' windows: for
  1.9 s of one launch (2026-11-15, read with each window's bounds). One more window of Designer's showed above every
  normal window: at popup level, 575 x 387 in the middle of the screen, fading out for 0.1 to 0.2 s as Designer
  answered (its splash or Home screen, most likely).
`QT_MAC_SET_RAISE_PROCESS=0` would also stop a raise from making Designer the active app. It isn't set: it changed
nothing at the launch, and the self-test's Undo needs a raise to make Designer the active app (REVIEW.md TST-234).
give_back_activation stays, for a Designer that still becomes the active app (REVIEW.md SRV-148, SRV-149). Test:
lifecycle.check_launch_on_another_port.

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
for a Designer an agent started; launch_designer ends one not answering past its start-up the same way. Before either
force, on macOS, the server runs macOS's `sample` on it for a second, writing its threads' stacks into that Designer's
own folder, to read what a hang waits on (ROADMAP item 70): 1.5 to 2 s, without admin rights. The sample of one stuck in
its shutdown shows its main thread in `destroyApplication`, Designer's teardown, at whichever of its steps it waits
(measured: tests/test_all_tools/lifecycle/samples.py, and lifecycle's two sample checks). launch_designer
records the process it started, its start time and, on macOS, its home in `agent_designer_file(port)` (project_constants.py), one per port, so a /mcp reconnect keeps it and a
reused ID doesn't count; on Windows nothing is recorded, so every Designer counts as the user's. A close goes to
whichever Designer holds the port, so it names the recorded process and any other refuses (`os.getpid()` inside Designer
is that process, checked live). The plugin answers status from another thread, so a main thread frozen outside
a job reads as idle (measured with a timer slot sleeping in a loop).

Crash reports (measured 2026-11-12, macOS). Designer's crash reporter (Sentry, through Crashpad, in `Sentry-Crashpad`
in Designer's data folder) uploads each crash's report to Adobe, with Designer's log, its settings and the user's Adobe
account. Sentry turns uploads on in Crashpad's settings (`settings.dat`, bit 0 of the options) as Designer starts, and
Crashpad's handler reads them before each upload. So once a Designer launch_designer started with a home of its own
answers, it turns them off there (the user's choice: DECISIONS.md, Bridge and quitting), before leaving its Home screen,
and again whenever a launch finds it already running (the call that started it may have stopped waiting) or refusing
(another token, another protocol), and before quit_designer closes it or a launch ends it; never in the user's home. A crash before it answers may still be uploaded.
Measured: one crash's report was uploaded 4 s after the crash. In another Designer, uploads were turned off after its
start; they stayed off, and its crash's report was kept, never uploaded (Crashpad's own record on the file, its
extended attributes). That crash also opened Adobe's crash window (`AdobeCrashReportWindow`, which the handler
starts), and the crashed process stayed until the window was closed, so its quit was "could not be ended" (ROADMAP item
95); the two crashes before quit within their wait. A check: lifecycle.check_launch_on_another_port.
"""

import contextlib
import errno
import glob
import json
import os
import re
import select
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from collections.abc import Iterator, Sequence
from textwrap import dedent
from typing import Annotated, NamedTuple, Protocol, cast
from xml.etree import ElementTree

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

import designer_preferences  # beside project_constants (on sys.path: core.py puts the repo root there)
from project_constants import (  # on sys.path: the package's __init__ imports .core, which puts it there
    PLUGIN,
    QUIT_CLOSED,
    QUIT_FORCED_IN_SHUTDOWN,
    QUIT_FORCED_NOT_CLOSED,
    QUIT_SAMPLED,
    SHORT_TEMP,
    STARTUP_LIMIT,
    AgentRecord,
    Json,
    agent_designer_file,
    agent_designer_ports,
    agent_folder_name,
)

from .core import (
    PORT,
    Port,
    _bridge,
    _checked,
    _control,
    _designer_data_dir,
    _designer_running,
    _helpers_call,
    _NoListing,
    _pgrep,
    _Refused,
    _sentence,
    _server_versions,
    _tool,
)


@_tool(read_only=True, destructive=False, idempotent=True, open_world=False)
def designer_status(port: Port = None) -> str:
    """Report Designer's version, the bridge state (idle/running) and the open user packages (an
    unsaved one by its UID, as list_snapshots names it), whether an agent started it, plus this server's Python and library versions. While a job runs or waits, the Designer
    version and package list are skipped: they would have to wait for the job. The result also lists
    the Designers an agent started on other ports."""
    port = _port(port)
    state = _control('status', wait=10, port=port)
    if 'idle, 0 queued' not in state:  # the listing is a job too; it would queue (REVIEW.md SRV-22)
        agents = _agents()  # every record read once, for both lines (ROADMAP item 106)
        return _lines(
            state,
            'Bridge port %d.' % port,
            _started_by(port, agents),
            _others(port, agents),
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
    agents = _agents()
    started_by = _started_by(port, agents, int(answering.group(1)) if answering else None)
    return _lines(state, 'Bridge port %d.' % port, started_by, _others(port, agents), _server_versions(), listing)


def _lines(*parts: str) -> str:
    return '\n'.join(part for part in parts if part)


def _port(port: int | None) -> int:
    """The bridge port a lifecycle tool works on: this server's (PORT) unless one is given."""
    if port is None:
        return PORT
    if isinstance(port, bool) or not 1024 <= port <= 65535:
        raise ToolError('port must be a number from 1024 to 65535 (lower ones need root), not %r' % (port,))
    return port


def _started_by(port: int, agents: dict[int, int], answering: int | None = None) -> str:
    """Who started the Designer answering on `port`, or with its process unknown, the only one that may be there.
    Unclear means the user's. `agents` is what _agents() read."""
    running = [answering] if answering is not None else _sorted_out(port, agents)[0]
    own = agents.get(port)
    if own is not None and running == [own]:
        return 'Started by an agent: disposable, nothing in it is kept.'
    return "Not started by an agent: it is the user's."


def _others(port: int, agents: dict[int, int]) -> str:
    """The Designers an agent started on other ports, or nothing. `agents` is what _agents() read."""
    others = sorted((p, pid) for p, pid in agents.items() if p != port)
    if not others:
        return ''
    return 'Designers an agent started on other ports: %s.' % ', '.join('%d (process %d)' % o for o in others)


DESIGNER_APP = {
    'darwin': '/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app',
    'win32': r'C:\Program Files\Adobe\Adobe Substance 3D Designer\Adobe Substance 3D Designer.exe',
}
DESIGNER_BINARY = 'Adobe Substance 3D Designer'  # macOS: in the app's Contents/MacOS
# read by Designer's Qt on macOS: set, Qt doesn't make Designer the active app as it starts (the module docstring)
STAY_BEHIND = 'QT_MAC_DISABLE_FOREGROUND_APPLICATION_TRANSFORM'


def _designer_pids() -> list[int]:
    """Designer's processes, where one may be ended. None on Windows: ending one there hasn't been tried. Raises
    _NoListing when pgrep fails (exit code 2 or 3; 1 is nothing found)."""
    if sys.platform == 'win32':
        return []
    return [int(pid) for pid in _pgrep().stdout.split()]


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
    a temp folder (TMPDIR) and a home of its own (CFFIXED_USER_HOME, with its plugin folders) when given. On macOS it
    also sets STAY_BEHIND, so Designer starts behind the app in front (REVIEW.md SRV-149). Shared by _start_designer
    and the self-test's hand-over check, which starts the binary itself (REVIEW.md TST-148)."""
    # the server's own Python settings aren't for Designer's Python
    env = {k: v for k, v in os.environ.items() if not k.startswith('PYTHON') and k != '__PYVENV_LAUNCHER__'}
    env['SD_BRIDGE_PORT'] = str(port)
    if temp:
        env['TMPDIR'] = temp
    if home:
        env['CFFIXED_USER_HOME'] = home
        env['SBS_DESIGNER_PYTHON_PATH'] = plugins
    if sys.platform == 'darwin':
        env[STAY_BEHIND] = '1'
    return env


class _NotStarted(ToolError):
    """No Designer started, after Designer's preferences were saved: what was said of them first, kept apart so that
    what is said after comes after it (REVIEW.md SRV-129, SRV-138)."""

    def __init__(self, said: str, error: ToolError) -> None:
        super().__init__(str(error))
        self.said = said


def _start_designer(
    app: str, port: int, ended: bool
) -> tuple[int, str | None, str, tuple[OSError | _NoListing, bool] | None]:
    """Start Designer with SD_BRIDGE_PORT set, as its plugin reads the port there, and return its process ID, the
    home of its own it got (None: the user's), what to say of Designer's preferences, which one with a home of its own
    changes in the user's file, saved first (designer_preferences.py; `ended`: this launch has just ended one), and,
    if it couldn't be recorded (_remember_started), why and whether it was ended; _NotStarted when it isn't started
    then. Recorded, or ended when it can't be, before the lock the preferences are saved under goes: another launch,
    which waits for it, then never takes this Designer for the user's (_appeared; REVIEW.md SRV-141, SRV-144); one that
    can't be ended either counts as the user's, as launch_designer's error says. On macOS an app bundle is opened as a
    new instance with its environment (`open -n --env`; `open -a` alone brings back a Designer already running and
    passes no environment: ROADMAP item 49), hidden (_opened); otherwise its own binary is started."""
    home = _own_home(port)
    env = _designer_env(port, _own_temp(port), home, _plugin_paths() if home else '')
    quiet = subprocess.DEVNULL

    def refuse(said: str) -> None:
        appeared = _appeared(port)
        if appeared:
            raise _NotStarted(said, appeared)

    saving = (
        designer_preferences.saved(_any_designer, ended=ended, check=refuse) if home else contextlib.nullcontext('')
    )
    unrecorded: tuple[OSError | _NoListing, bool] | None = None
    unfound: _OpenedUnfound | None = None
    with saving as said:
        try:
            proc = _started(app, env, quiet)
        except _OpenedUnfound as e:  # it may run: the copy stays for its put-back, as when unrecorded (SRV-156)
            unfound = e
            unfound.said, unfound.home = said, home
            if e.pid is not None:  # before the lock goes: unrecorded, another launch would take it for the user's
                with contextlib.suppress(_NoListing):  # new, with the launch's port and home: this launch's
                    unfound.ended = _force_end(e.pid, port, b'')
        except ToolError as e:  # what the save did stands: said too (REVIEW.md SRV-129)
            raise _NotStarted(said, e) from e
        else:
            # a binary started here is the server's child: reaped when it exits, or it would linger as a zombie, its ID
            # and start time still there; with the server gone first, the system reaps it. Without the thread (none to
            # be had) it is recorded as usual, only left a zombie when it ends (REVIEW.md SRV-100). One `open` started
            # is launchd's child: its wait returns at once (_Opened)
            with contextlib.suppress(RuntimeError):
                threading.Thread(target=proc.wait, daemon=True).start()
            try:
                _remember_started(port, proc.pid, home)
            except (OSError, _NoListing) as e:  # the folder filled, or its start can't be read (REVIEW.md SRV-97)
                try:  # before the lock goes: unrecorded, another launch's look would take it for the user's (SRV-144)
                    gone = _force_end(proc.pid, port, b'')  # just started by this launch: certainly an agent's
                except _NoListing:  # its end can't be seen either: said, with what to do (REVIEW.md SRV-100)
                    gone = False
                unrecorded = (e, gone)
    if unfound is not None:  # raised once saved() has kept the copy: raised inside, it is dropped (REVIEW.md SRV-138)
        raise unfound
    return proc.pid, home, said, unrecorded


def _appeared(port: int) -> ToolError | None:
    """The refusal to start one on `port` once a Designer appeared since start() looked (_users_next_to): mostly as
    saved() put Designer's preferences back, which takes a second or so (REVIEW.md SRV-139). Asked under the lock they
    are saved under, which every launch holds until its Designer is recorded, or ended when it can't be (SRV-141,
    SRV-144): one that appeared is the user's, not yet listening anywhere to be told from one starting on `port`, which
    start() found none of. None when none appeared, or that can't be told."""
    try:
        pids = [pid for found in _sorted_out(port) for pid in found]
    except _NoListing:
        return None
    if not pids:
        return None
    return ToolError(
        'A Designer started as this one was about to (%s %s): none is started next to it, since Designers share '
        "Designer's preferences plist. To start one on port %d, ask the user to close it."
        % ('process' if len(pids) == 1 else 'processes', ', '.join(map(str, pids)), port)
    )


OPEN_HIDDEN = ('open', '-n', '-g', '-j')  # a new instance, not brought to the front, hidden (REVIEW.md SRV-152)
OPENED_ENV = ('SD_', 'SBS_', 'QT_', 'TMPDIR', 'CFFIXED_USER_HOME')  # the variables passed as `open --env`
LAUNCH_FOUND_S = 60  # s at most for the process `open` started to be listed: a limit, in case it never is
OPEN_WAIT_S = 60  # s at most for `open` itself to exit: a limit, in case it never does (REVIEW.md SRV-160)


class _OpenedUnfound(ToolError):
    """Designer may run: `open` exited 0, or never exited, but its process wasn't found (REVIEW.md SRV-156). `pid`: the
    process found at a last look, or None. Once _start_designer has tried to end it: `ended`, whether it did; `said`,
    what was said of Designer's preferences, whose copy is kept; `home`, the home it got."""

    def __init__(self, why: str, pid: int | None) -> None:
        super().__init__(why)
        self.why = why
        self.pid = pid
        self.ended = False
        self.said = ''
        self.home: str | None = None


class _Opened:
    """The Designer `open` started, as _start_designer uses a process: launchd's child, so nothing to reap."""

    def __init__(self, pid: int) -> None:
        self.pid = pid

    def wait(self) -> int:
        return 0


def _launch_marks(env: dict[str, str]) -> tuple[str, ...]:
    """The variables of a launch's environment `env` that the Designer it starts has and no other: its port, and its
    home when it has one of its own. A Designer the user starts with SD_BRIDGE_PORT set has the port too (README,
    Configuration; REVIEW.md SRV-165)."""
    return tuple('%s=%s' % (key, env[key]) for key in ('SD_BRIDGE_PORT', 'CFFIXED_USER_HOME') if env.get(key))


def _carries(pid: int, marks: Sequence[str]) -> bool:
    """Whether process `pid`'s environment has each of `marks` (VAR=value; ps -E: this user's processes). Each a whole
    variable of ps's line, which ends with a newline (REVIEW.md SRV-157)."""
    shown = subprocess.run(['ps', '-E', '-p', str(pid), '-o', 'command='], capture_output=True, text=True).stdout
    variables = shown.split()
    return all(mark in variables for mark in marks)


def _launched_now(before: set[int], marks: Sequence[str]) -> int | None:
    """The process of the Designer `open` started with `marks` (_launch_marks), looked for once (_found_launched's
    look); None when none is listed, or the processes can't be."""
    try:
        return next((pid for pid in sorted(set(_designer_pids()) - before, reverse=True) if _carries(pid, marks)), None)
    except (_NoListing, OSError):
        return None


def _found_launched(opener: 'subprocess.Popen[bytes]', before: set[int], marks: Sequence[str]) -> int:
    """The process of the Designer `open` (`opener`, exited) just started: a new one, not in `before`, whose
    environment has the launch's `marks` (_launch_marks), so neither another launch's starting at once nor a Designer
    the user starts meanwhile is taken for it. `open` says no process ID, and nothing says when the process appears:
    looked for every POLL_S, LAUNCH_FOUND_S at most. The tests' fake takes the process from `opener`."""
    deadline = time.monotonic() + LAUNCH_FOUND_S
    while True:
        for pid in sorted(set(_designer_pids()) - before, reverse=True):
            if _carries(pid, marks):
                return pid
        if time.monotonic() >= deadline:
            raise ToolError("its process wasn't found within %d s" % LAUNCH_FOUND_S)
        time.sleep(POLL_S)


def _opened(app: str, env: dict[str, str], quiet: int) -> _Opened:
    """Designer opened from the app bundle `app` by macOS's `open`: a new instance, hidden, never brought to the
    front, with `env`, passed whole (`open` passes its own environment on: measured 2026-11-15, as `man open` says; the
    OPENED_ENV variables also go as `--env`). Started from its binary, its window came up in front of the active app's
    for up to 5.66 s, STAY_BEHIND set (REVIEW.md SRV-152, measured 2026-11-15): opened so, none of its windows showed
    and it was never the active app, in 4 of 4 launches. ToolError when `open` failed, with what it said;
    _OpenedUnfound when Designer may run but its process wasn't found (REVIEW.md SRV-156)."""
    before = set(_designer_pids())
    marks = _launch_marks(env)
    passed = [
        arg for key, value in env.items() if key.startswith(OPENED_ENV) for arg in ('--env', '%s=%s' % (key, value))
    ]
    with tempfile.TemporaryFile() as said:  # what `open` says when it fails (REVIEW.md SRV-160)
        opener = subprocess.Popen(
            [*OPEN_HIDDEN, *passed, '-a', app], env=env, stdin=quiet, stdout=quiet, stderr=said, cwd='/'
        )
        try:
            code = opener.wait(timeout=OPEN_WAIT_S)
        except subprocess.TimeoutExpired:
            opener.kill()
            raise _OpenedUnfound("`open` didn't exit within %d s" % OPEN_WAIT_S, _launched_now(before, marks)) from None
        said.seek(0)
        message = said.read().decode('utf-8', 'replace').strip()
    if code != 0:
        raise ToolError(
            'Designer could not be started from %r: `open` exited with %d%s; set SD_DESIGNER_APP'
            % (app, code, ' (%s)' % message if message else '')
        )
    try:
        return _Opened(_found_launched(opener, before, marks))
    except (ToolError, OSError) as e:  # opened: Designer may run (REVIEW.md SRV-156)
        raise _OpenedUnfound(str(e), _launched_now(before, marks)) from e


def _opens_hidden(app: str) -> bool:
    """Whether a Designer started from `app` is opened hidden by `open` (_opened): an app bundle, on macOS."""
    return sys.platform == 'darwin' and os.path.isdir(app)


def _started(app: str, env: dict[str, str], quiet: int) -> 'subprocess.Popen[bytes] | _Opened':
    """Designer's process, started from `app` with `env`: on macOS an app bundle is opened hidden (_opened)."""
    if _opens_hidden(app):
        try:
            return _opened(app, env, quiet)
        except _OpenedUnfound:  # opened: not a start that failed (REVIEW.md SRV-156)
            raise
        except _NoListing as e:
            raise ToolError('Designer could not be started from %r: %s' % (app, e)) from e
        except OSError as e:
            raise ToolError('Designer could not be started from %r: %s; set SD_DESIGNER_APP' % (app, e)) from e
    try:
        if sys.platform == 'win32':
            detached: int = getattr(subprocess, 'DETACHED_PROCESS', 0x8) | getattr(
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
    return proc


def _any_designer() -> bool:
    """Whether a Designer runs, the user's or an agent's; True when that can't be told (designer_preferences.py)."""
    try:
        return bool(_designer_pids())
    except _NoListing:
        return True


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
    """Record the process launch_designer started for `port`: the one it started, or the one `open` started with
    the launch's port and home (_found_launched), so no other can be taken for it; and
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
            record: AgentRecord = {'pid': pid, 'start': start, 'home': home}
            json.dump(record, f)
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


def _read_record(port: int) -> tuple[bytes, float] | None:
    """`port`'s record as read, and when it was written (its mtime), both from one open of the file: a caller needs no
    second look at it (REVIEW.md SRV-175). None without one."""
    try:
        with open(agent_designer_file(port), 'rb') as f:
            return f.read(), os.fstat(f.fileno()).st_mtime
    except OSError:
        return None


class _Recorded(NamedTuple):
    """The Designer an agent started on a port, still running, as one read of its record gave it (_agent_record)."""

    pid: int
    home: str | None  # the home of its own it got; None without one: older code started it, or not macOS
    seen: bytes  # the record as read: what _forget_started is given
    written: float  # when the record was written (its mtime): _agent_log's log is no older (REVIEW.md SRV-175)


def _agent_record(port: int) -> _Recorded | None:
    """The Designer an agent started on `port`, if it is still running. The start time tells it from a later process
    given the same ID. Anything unclear means it isn't an agent's, and a stale record goes, unless it was replaced
    meanwhile. Its callers take the fields they use from one call: a second read may find another record, or none
    (ROADMAP item 106)."""
    read = _read_record(port)
    if read is None:
        return None
    seen, written = read
    try:
        record: dict[str, Json] = json.loads(seen)  # not a dict, or no pid or start: TypeError or KeyError here
        pid, start, home = record['pid'], record['start'], record.get('home')
        if not isinstance(pid, int):
            raise TypeError
        found = _Recorded(pid, home if isinstance(home, str) else None, seen, written)
        try:
            listed: bool | None = pid in _designer_pids()
        except _NoListing:
            listed = None
        try:
            same = listed is not False and _process_start(pid) == start
        except _NoListing:  # can't tell: not taken for an agent's meanwhile, and the record is kept (REVIEW.md SRV-97)
            return None
        if listed is None:  # its start time alone tells; gone or not, the record is kept (REVIEW.md SRV-83)
            return found if same else None
        if listed and same:
            return found
    except (ValueError, KeyError, TypeError):
        pass
    _forget_started(port, seen)
    return None


def _agent_designer(port: int) -> int | None:
    """The process ID of the Designer an agent started on `port`, if it is still running (_agent_record)."""
    found = _agent_record(port)
    return found.pid if found else None


def _agent_home(port: int) -> str | None:
    """The home the Designer an agent started on `port` got, if it still runs: None for the user's (no home of its own,
    a record without one: older code started it, or not macOS) or when no agent's runs there."""
    found = _agent_record(port)  # the home from the record whose Designer was checked (REVIEW.md SRV-172)
    return found.home if found else None


def _agents() -> dict[int, int]:
    """{port: process ID} of the Designers an agent started that still run."""
    found = {}
    for port in agent_designer_ports():
        pid = _agent_designer(port)
        if pid is not None:
            found[port] = pid
    return found


def _sorted_out(port: int, agents: dict[int, int] | None = None) -> tuple[list[int], list[int]]:
    """Designer's processes as `port` sees them: those that may hold it, and those no agent started that listen on
    other ports but not this one (the user's, on their own). The ones an agent started on other ports are in neither.
    One listening nowhere yet may still be starting on this port. `agents` is what _agents() read, when the caller
    has it; read here otherwise."""
    if agents is None:
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


def _running_on(port: int, agents: dict[int, int] | None = None) -> bool:
    """Whether a Designer that may hold `port` runs. Processes that can't be listed (Windows) all may. `agents` is what
    _agents() read, when the caller has it (_sorted_out)."""
    if not _designer_running():
        return False
    return not _designer_pids() or bool(_sorted_out(port, agents)[0])


def _may_hold(port: int) -> bool:
    """_running_on, with "can't tell" read as a Designer that may hold `port`: a listing failing once doesn't end a wait
    for one (REVIEW.md SRV-164)."""
    try:
        return _running_on(port)
    except _NoListing:
        return True


def _still_starting(port: int) -> bool:
    """Whether the record, written as the process started, is younger than STARTUP_LIMIT."""
    try:
        written = os.path.getmtime(agent_designer_file(port))
    except OSError:  # no record
        return False
    return time.time() - written < STARTUP_LIMIT


POLL_S = 0.1  # s between looks at a state whose change nothing says (`.claude/rules/waits.md`)
FORCE_WAIT_S = 5  # s a forced end waits for the process to exit after each signal: a limit, in case it never does


class _Queue(Protocol):
    """A kqueue, as _ExitWatch uses it: select.kqueue exists only on BSD and macOS (REVIEW.md SRV-153: its name in an
    annotation failed mypy for the other platforms). control returns the events, select.kevent objects: only their
    count is read."""

    def control(self, changelist: None, max_events: int, timeout: float | None = None, /) -> Sequence[object]: ...

    def close(self) -> None: ...


class _ExitWatch:
    """A watch of one process's exit: a kqueue process-exit event (macOS), or none needed, as it had exited already."""

    def __init__(self, queue: _Queue | None) -> None:
        self._queue = queue
        self._ended = queue is None

    def wait(self, limit: float) -> bool:
        """Whether the process exits within `limit` s, woken as it does. The watch is done after."""
        try:
            return self._ended or bool(self._queue is not None and self._queue.control(None, 1, limit))
        finally:
            self.close()

    def ended(self) -> bool:
        """Whether the process has exited, at once: its exit event come (REVIEW.md SRV-154)."""
        if not self._ended and self._queue is not None:
            self._ended = bool(self._queue.control(None, 1, 0))
        return self._ended

    def close(self) -> None:
        """The watch done: its kqueue closed."""
        if self._queue is not None:
            self._queue.close()
            self._queue = None


def _exit_watch(pid: int) -> _ExitWatch | None:
    """A watch of process `pid`'s exit, or None where none can be made: off macOS, or a process this user can't
    watch."""
    if sys.platform != 'darwin':
        return None
    try:
        queue = select.kqueue()  # no file descriptor left: the poll instead (REVIEW.md SRV-153)
    except OSError:
        return None
    exit_event = select.kevent(pid, select.KQ_FILTER_PROC, select.KQ_EV_ADD | select.KQ_EV_ONESHOT, select.KQ_NOTE_EXIT)
    try:
        queue.control([exit_event], 0, 0)
    except ProcessLookupError:  # gone before the watch began
        queue.close()
        return _ExitWatch(None)
    except OSError:
        queue.close()
        return None
    return _ExitWatch(queue)


def _exited(pid: int, limit: float) -> bool:
    """Whether Designer's process `pid` exits within `limit` s: woken by its exit where it can be watched
    (_exit_watch), else looked for every POLL_S (REVIEW.md SRV-150: every second). A negative limit is none: kqueue
    refuses one (REVIEW.md SRV-159)."""
    limit = max(0.0, limit)
    if pid not in _designer_pids():
        return True
    watch = _exit_watch(pid)
    if watch is not None:
        return watch.wait(limit) or pid not in _designer_pids()
    deadline = time.monotonic() + limit  # each look's pgrep counts too (REVIEW.md SRV-153: it ran past the limit)
    while True:
        time.sleep(POLL_S)
        if pid not in _designer_pids():
            return True
        if time.monotonic() >= deadline:
            return False


def _force_end(pid: int, port: int, seen: bytes) -> bool:
    """End `pid`, the Designer an agent started on `port`, whose record was `seen`: SIGTERM, then SIGKILL, each followed
    by a wait for its exit, FORCE_WAIT_S at most."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, sig)
        if _exited(pid, FORCE_WAIT_S):
            _forget_started(port, seen)
            return True
    return False


def _end_if_past_startup(port: int) -> str | None:
    """End the Designer an agent started on `port`, unless it may still be starting: it is disposable, so it isn't
    waited for past that (REVIEW.md HLP-82), but a retry mustn't kill one that is only slow (REVIEW.md SRV-75). Its
    threads are sampled first, as it may be hung in its shutdown (REVIEW.md SRV-113). Returns what to say of it, or
    None when nothing was ended: the sentence saying its crash reports may still be uploaded, when they couldn't be
    turned off, then _sampled_before_force's sentence, which ends with the sample's path when one was written. Either
    can be ''. The error when it can't be ended says them too; so does the one when its processes can't be listed
    meanwhile, after saying it was being ended (REVIEW.md SRV-171)."""
    if _still_starting(port):  # a stat, before the record's pgrep and ps (REVIEW.md SRV-158)
        return None
    found = _agent_record(port)
    if found is None:
        return None
    own = found.pid
    uploads = _crash_uploads_off(found.home)  # a crash in its teardown isn't uploaded (REVIEW.md SRV-124)
    # the path last, as quit_designer says it: a stop after it would be read as part of it (REVIEW.md SRV-168)
    said = uploads + _sampled_before_force(own, port)
    try:
        ended = _force_end(own, port, found.seen)
    except _NoListing as e:  # what it was doing and found, said too (REVIEW.md SRV-169, SRV-171)
        ending = 'Designer %d, which an agent started, was not answering past its start-up and was being ended. ' % own
        raise _NoListing(ending + _sentence(str(e)) + said) from e
    if not ended:
        raise ToolError(_could_not_end(own) + said)  # once is enough (REVIEW.md SRV-79)
    return said


def _could_not_end(pid: int) -> str:
    return 'Designer %d could not be ended; ask the user to run `kill -9 %d`.' % (pid, pid)


def _how_to_end(port: int) -> str:
    """What the user can do about a Designer the tools won't end: without its process IDs when they can't be listed,
    so that the message it ends keeps the rest (REVIEW.md SRV-171)."""
    try:
        pids = _sorted_out(port)[0] or _designer_pids()
    except _NoListing:
        return 'ask the user to end it in Activity Monitor'  # only macOS lists them (pgrep)
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


@_tool(read_only=False, destructive=False, idempotent=True, open_world=False)
def launch_designer(
    wait_s: Annotated[int, Field(description='Seconds to wait until the bridge plugin answers.')] = 180,
    port: Annotated[
        int | None,
        Field(
            description="The bridge port the Designer's plugin listens on, 1024-65535; this server's (SD_BRIDGE_PORT, "
            '9877 by default) when omitted.'
        ),
    ] = None,
) -> str:
    """Start Substance Designer if it isn't running and wait until the bridge plugin answers.
    When it starts Designer it also closes the Home screen, so the editor panels are visible. On macOS it starts
    Designer hidden, without taking the keyboard (and gives it back if Designer takes it anyway): its Dock icon
    shows it.
    A Designer that is running but not answering yet is waited for, not started again; if it exits
    during the wait, a new one is started and gets its own wait_s, so the call can then take up to
    about twice wait_s. One an agent started is waited for only until 180 s after it started; past that, not answering,
    it is ended and a new one started, and the result says so.
    On macOS, Designers an agent started run side by side, one per port, each recorded on its
    own (other platforms not tried; on Windows nothing is recorded, and with any Designer running none is started);
    designer_status, quit_designer and read_designer_log take the same port. The other tools reach only this server's
    port: one on another is for a server or client/sd_run.py started with SD_BRIDGE_PORT set to it. None is started
    next to a Designer the user opened, on another port (GUIDE.md, Several Designers). None is started on a
    port the plugin couldn't listen on (another program holds it; the result gives the error), nor where its record
    can't be written (unrecorded, it would count as the user's); a plugin of another bridge protocol (another version)
    is reported at once. On macOS it saves Designer's preferences plist first (again if the user's own Designer ran
    since the last copy), which quit_designer puts back; a line before the result or error says what it did with them:
    a copy left behind put back or dropped, saved again, or not saved.
    For tests and work on this project: if a task needs Designer and it is closed, ask the user to open it.
    Override the app location with SD_DESIGNER_APP (on macOS the .app, opened hidden; a binary there starts shown)."""
    port = _port(port)
    try:
        status = _control('status', wait=5, port=port)
    except _Refused as refused:  # it runs and answers: starting or waiting for another wouldn't help
        raise _with_uploads_off(refused, _agent_home(port)) from None
    except ToolError:
        pass
    else:
        return _already_running(port, status)
    # A Designer process without an answering bridge (still starting, a dialog, the plugin didn't
    # load) is waited for, not started again (Windows would open a second instance). If it exits
    # while we wait (it was shutting down, or hung after a crash), a new one is started then.
    app = os.environ.get('SD_DESIGNER_APP') or DESIGNER_APP.get(sys.platform)

    ended_note = 'Ended a Designer an agent started, which was not answering.%s\n'
    ended_sample = _end_if_past_startup(port)
    note = '' if ended_sample is None else ended_note % ended_sample
    homes: list[str | None] = []  # of the Designers started here, the last one waited for
    preferences: list[str] = []  # what their starts said of Designer's preferences (designer_preferences.py)

    def told() -> str:
        """What comes before the result or any error once a start may have run: a Designer ended, what was done with
        Designer's preferences (REVIEW.md SRV-129)."""
        return note + ''.join(line + '\n' for line in preferences)

    def none_left() -> str:
        """told(), for an error that may leave none of this call's Designers running: Designer's preferences put back
        first if it ended or started one, since no quit follows (REVIEW.md SRV-130, SRV-135); a put-back does nothing
        while any Designer runs."""
        if note or homes:
            said = designer_preferences.put_back(_any_designer, ended=True)
            if said:
                preferences.append(said)
        return told()

    def start() -> bool:
        """Start one, unless another launch on this port started one meanwhile: False then, and that one is waited
        for (REVIEW.md SRV-83)."""
        with _launch_lock(port):
            if _running_on(port):
                return False
            if not app or not os.path.exists(app):
                raise ToolError('%sDesigner not found at %r; set SD_DESIGNER_APP' % (none_left(), app))
            refusal = _users_next_to(port, '')
            if refusal:
                raise ToolError(none_left() + str(refusal))
            unbindable = _bind_error(port)
            if unbindable:  # before the start: it would wait out wait_s and stay running (REVIEW.md SRV-85)
                raise _unusable_port(port, unbindable, none_left())
            unwritable = _record_error(port)
            if unwritable:  # unrecorded, it would count as the user's (REVIEW.md SRV-93)
                raise _unrecorded(port, unwritable, none_left(), 'No Designer was started')
            try:
                pid, home, said, unrecorded = _start_designer(app, port, ended=bool(note))
            except _OpenedUnfound as e:  # opened, its process not found: it may run (REVIEW.md SRV-156)
                if e.said:
                    preferences.append(e.said)
                homes.append(e.home)
                if e.ended:  # none of its own runs now: the copy put back
                    raise ToolError(
                        '%sDesigner was opened, but %s; its process %d, found then, was ended.'
                        % (none_left(), e.why, cast(int, e.pid))
                    ) from e
                if e.pid is not None:
                    raise ToolError(
                        '%sDesigner was opened, but %s; its process %d could not be ended (ask the user to run `kill '
                        "-9 %d`): unrecorded, it counts as the user's." % (told(), e.why, e.pid, e.pid)
                    ) from e
                raise ToolError(
                    "%sDesigner was opened, but %s: if one started, it isn't recorded as an agent's, so it counts as "
                    "the user's (ask the user to quit it)." % (told(), e.why)
                ) from e
            except ToolError as e:  # none started: its folder refused, one appeared, or it couldn't start (SRV-135)
                if isinstance(e, _NotStarted) and e.said:  # before what none_left() says, as it came first (SRV-138)
                    preferences.append(e.said)
                first = none_left()
                if not first:
                    raise
                raise ToolError(first + str(e)) from e
            homes.append(home)
            if said:
                preferences.append(said)
            if unrecorded is not None:  # the folder filled, or its start can't be read: ended if it could be (SRV-97)
                error, gone = unrecorded
                if gone:  # none of its own runs now (REVIEW.md SRV-135)
                    raise _unrecorded(
                        port, error, none_left(), 'Designer (process %d) was started, then ended' % pid
                    ) from error
                started = 'Designer (process %d) was started and could not be ended (ask the user to run `kill -9 %d`)'
                raise _unrecorded(port, error, told(), started % (pid, pid)) from error
            return True

    watched: dict[int, _ExitWatch | None] = {}  # the Designers waited for, by process: their exits watched

    def may_have_exited() -> bool:
        """Whether the Designer this call waits for on this port may no longer hold it. The one another launch recorded
        holds it until it exits, so it is looked up again only once its exit event comes, or when it can't be watched
        (REVIEW.md SRV-154, SRV-158: pgrep, ps and lsof ran every POLL_S while it started). With none recorded, always:
        an unrecorded Designer (the user's starting, or another launch's not recorded yet) can leave the port without
        exiting, as another launch records it on its own port or it listens on another, and nothing says so (REVIEW.md
        SRV-162)."""
        if watched and not any(watch is None or watch.ended() for watch in watched.values()):
            return False
        for watch in watched.values():
            if watch is not None:
                watch.close()
        watched.clear()
        found = _agent_record(port)
        if found is not None:
            watched[found.pid] = _exit_watch(found.pid)
        return not watched or None in watched.values()

    try:
        running, restarted = _running_on(port), False
        if not running:
            running = not start()
        started = time.time()
        while time.time() - started < wait_s:
            # nothing says when its bridge starts listening, and a refused connection costs nothing (REVIEW.md SRV-150)
            time.sleep(POLL_S)
            try:
                status = _control('status', wait=5, port=port)
            except _Refused as refused:
                refusal = _with_uploads_off(refused, homes[-1] if homes else _agent_home(port))
                raise (_Refused(told() + str(refusal)) if told() else refusal) from None  # a refusal still (SRV-129)
            except ToolError:
                try:
                    ended_sample = _end_if_past_startup(port) if running else None
                except _NoListing:
                    raise  # with none_left() in front, below
                except ToolError as e:  # what the call did before it, said first, as its other errors (SRV-169)
                    raise ToolError(told() + str(e)) from e
                if ended_sample is not None:
                    note = ended_note % ended_sample
                # it exited, or turned out to be the user's on another port
                if running and may_have_exited() and not _may_hold(port):
                    restarted = True
                    running = not start()
                    started = time.time()  # the new one gets the whole wait (REVIEW.md SRV-19)
                continue
            if running:
                return told() + _already_running(port, status)
            # Designer turns them on as it starts, so only now, before anything else that may fail (the module's
            # docstring: Crash reports; REVIEW.md SRV-120)
            uploads = _crash_uploads_off(homes[-1] if homes else None)
            # we started it, so nobody is using the Home screen: show the editor panels
            try:
                home = _bridge(_helpers_call('leave_home_screen()'), timeout=30, port=port).strip()
                # in case it became the active app anyway, the user's keyboard in it (REVIEW.md SRV-148, SRV-149); one
                # opened hidden is left hidden, as becoming the active app unhides it (REVIEW.md SRV-161)
                give_back = 'give_back_activation(%s)' % ('started_hidden=True' if app and _opens_hidden(app) else '')
                given = _bridge(_helpers_call(give_back), timeout=30, port=port).strip()
            except ToolError as e:
                if not told():
                    raise
                raise ToolError(told() + str(e)) from e
            done = '; '.join(part for part in (home, given) if part)
            return told() + 'Designer started in %.0fs, on port %d%s: %s' % (
                time.time() - started,
                port,
                ' (%s)' % done if done else '',
                _with_uploads(status, uploads),
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
                none_left(),  # the one it started may have exited meanwhile (REVIEW.md SRV-135)
                'Designer is already running, but its bridge' if running else 'Designer',
                wait_s,
                ' of being started' if restarted else '',
                PLUGIN,
                what_next,
            )
        )
    except _NoListing as e:  # what the call did before it, said first (REVIEW.md SRV-164)
        raise _NoListing(none_left() + str(e)) from e
    finally:  # the wait's watches closed, however it ends (REVIEW.md SRV-158)
        for watch in watched.values():
            if watch is not None:
                watch.close()


CRASHPAD_MAGIC = 0x43506473  # Crashpad's settings file ('sdPC'); its options next but one, bit 0 uploads enabled
CRASHPAD_VERSION = 1  # the layout read here; another may move the options (REVIEW.md SRV-122)


def _already_running(port: int, status: str) -> str:
    """The result for a Designer found answering. One an agent started gets its crash uploads turned off too: Designer
    turns them on at each start, and the call that started it may have stopped waiting first (REVIEW.md SRV-120)."""
    return 'Designer already running on port %d: %s' % (
        port,
        _with_uploads(status, _crash_uploads_off(_agent_home(port))),
    )


def _with_uploads_off(refused: _Refused, home: str | None) -> _Refused:
    """A refusal from a Designer an agent started (its `home`), its crash uploads turned off first: a refusal is an
    answer, so Designer has turned them on (REVIEW.md SRV-123); with the sentence if they couldn't be."""
    uploads = _crash_uploads_off(home)
    return _Refused(_with_uploads(str(refused), uploads)) if uploads else refused


def _with_uploads(status: str, uploads: str) -> str:
    """The plugin's status, then the sentence saying crash uploads couldn't be turned off, if any: the status ends with
    no stop (REVIEW.md SRV-121)."""
    return _sentence(status) + uploads if uploads else status


def _crash_uploads_off(home: str | None) -> str:
    """Crash uploads turned off in the Crashpad settings of the Designer started with `home`, a home of its own
    (macOS; the module's docstring: Crash reports): '' once off, or with no such home, else the sentence for the result
    saying why not. Under Crashpad's own lock, as its handler may read them at that moment."""
    if not home:
        return ''
    import fcntl  # POSIX's: only a home of its own gets here

    path = os.path.join(_designer_data_dir(home), 'Sentry-Crashpad', 'settings.dat')
    try:
        with open(path, 'r+b') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            head = f.read(12)
            version = int.from_bytes(head[4:8], 'little')
            if len(head) < 12 or int.from_bytes(head[:4], 'little') != CRASHPAD_MAGIC:
                why = "%s isn't Crashpad's settings" % path
            elif version != CRASHPAD_VERSION:
                why = "%s is Crashpad's settings of version %d, whose layout isn't known here" % (path, version)
            else:
                options = int.from_bytes(head[8:12], 'little')
                f.seek(8)
                f.write((options & ~1).to_bytes(4, 'little'))
                return ''
    except OSError as e:
        why = str(e)
    return ' Its crash reports may still be uploaded to Adobe: %s.' % why


SAMPLE = '/usr/bin/sample'  # macOS's: the stacks of a process's threads, the process left running


def _sample(pid: int, path: str) -> str | None:
    """Sample process `pid` for a second into `path`: None once written, else why not."""
    try:
        done = subprocess.run(
            [SAMPLE, str(pid), '1', '-file', path], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return str(e)
    if done.returncode == 0 and os.path.isfile(path):
        return None
    said = done.stderr.strip().splitlines()
    return said[-1] if said else 'sample exited with %d' % done.returncode


def _sampled_before_force(pid: int, port: int) -> str:
    """On macOS, the threads of the Designer an agent started on `port`, about to be forced, sampled into its own
    folder: what a hang in its shutdown waits on (ROADMAP item 70). The sentence for the result; '' without that folder
    (_checked_folder's) or off macOS."""
    folder = _checked_folder(port) if sys.platform == 'darwin' else None
    if folder is None:
        return ''
    path = os.path.join(folder, 'threads_%d.sample.txt' % pid)  # not "forced": it may quit while sampled
    failed = _sample(pid, path)
    return (
        ' Its threads could not be sampled first: %s' % _sentence(failed) if failed else ' %s %s' % (QUIT_SAMPLED, path)
    )


@_tool(read_only=False, destructive=True, idempotent=True, open_world=False)
def quit_designer(
    wait_s: Annotated[int, Field(description="Seconds to wait for the Designer's process to exit.")] = 10,
    port: Port = None,
) -> str:
    """Close a Designer an agent started, and wait until its process has exited: unsaved changes are dropped, and after
    wait_s it is force-ended; the result says which and, if forced, whether its close had taken (its own shutdown
    then hung) and the last line of its log. On macOS, one still running past wait_s has its threads sampled into a
    file the result names, also when it then quits by itself. Running a job, it isn't asked to close. Not replying to
    the close within wait_s (at least 10 s) adds that to the wait. Any other Designer is the user's: this ends nothing
    and says to ask them to save, close and reopen it. Designers on other ports are left alone.
    On macOS, once no Designer runs, it puts Designer's preferences plist back from the copy launch_designer saved,
    unless the user's Designer ran since, or the copy is over 6 hours old and this call ended none (it is dropped
    then); the result says which."""
    said, ended = _quit(_port(port), wait_s)
    # after an end, by itself or forced; with none running at all too: one ended outside the tools left it changed
    return _lines(said, designer_preferences.put_back(_any_designer, ended=ended))


def _quit(port: int, wait_s: int) -> tuple[str, bool]:
    """quit_designer without the put-back of Designer's preferences, and whether it ended a Designer."""
    found = _agent_record(port)
    if found is None:
        if not _designer_running():
            return 'Designer is not running.', False
        agents = _agents()  # every record read once, for both (ROADMAP item 106)
        if not _running_on(port, agents):
            return _lines('No Designer is running on port %d.' % port, _others(port, agents)), False
        raise ToolError("This Designer wasn't started by an agent: ask the user to save, close and reopen it.")
    own, seen = found.pid, found.seen
    # the call that started it may have stopped waiting, so none turned them off: a crash as it quits isn't uploaded
    # (REVIEW.md SRV-124)
    uploads = _crash_uploads_off(found.home).strip()
    try:
        state = _control('status', wait=5, port=port)
        if 'idle, 0 queued' not in state:  # the close would queue behind it, for up to 15 minutes (REVIEW.md SRV-74)
            raise ToolError('busy: %s' % state)
        # it goes to whichever Designer holds the port, so it names this one and any other refuses (REVIEW.md SRV-73)
        call = _helpers_call('quit_designer(%d, %r)' % (own, QUIT_CLOSED))
        # a frozen main thread reads as idle too, and a close running late runs in the process being ended (REVIEW.md SRV-78)
        reply = _bridge(call, timeout=30, wait=max(wait_s, 10), port=port)
        notes = _checked(reply).replace('closing Designer', '').strip()
        step = 'Designer %d was asked to close. ' % own  # said if its processes can't be listed (REVIEW.md SRV-171)
    except ToolError as e:  # it can't be asked, only ended; or the reply was lost as it quit
        notes = 'Designer was not asked to close, or did not reply: %s' % e
        step = ''  # the notes say so
    prefix = ''.join(line + '\n' for line in (notes, uploads) if line)
    started = time.time()
    sampled = ''
    try:  # what was done before the processes can't be listed, said with the error too (REVIEW.md SRV-169)
        if _exited(own, wait_s):  # woken as it exits (REVIEW.md SRV-150)
            _forget_started(port, seen)  # only its own: another server may have recorded a new one (REVIEW.md SRV-91)
            return prefix + 'Designer quit after %.0fs.' % (time.time() - started), True
        from .log import _quit_evidence  # here: log.py imports from this module

        step = 'Designer %d did not quit within %ds and was being ended. ' % (own, wait_s)
        sampled = _sampled_before_force(own, port)  # what it is stuck in (ROADMAP item 70)
        # read while it still runs, after the sample: how far its quit got (REVIEW.md SRV-111)
        evidence = _quit_evidence(port, found)  # from its one read (ROADMAP item 106)
        if own not in _designer_pids():  # it ended while those were read: by itself (REVIEW.md SRV-108)
            _forget_started(port, seen)
            # a shutdown that hung past its wait, then ended: its sample is a hang's evidence (REVIEW.md SRV-115)
            return prefix + 'Designer quit after %.0fs.%s' % (time.time() - started, sampled), True
        # it can hang in its own shutdown, past anything inside it (REVIEW.md HLP-82, ROADMAP item 69)
        forced = _force_end(own, port, seen)
    except _NoListing as e:
        raise _NoListing(prefix + step + _sentence(str(e)) + sampled) from e
    if forced:
        took = time.time() - started
        if evidence is None:
            return prefix + 'Designer quit after %.0fs (forced; its log could not be read).%s' % (took, sampled), True
        closed, last = evidence
        how = QUIT_FORCED_IN_SHUTDOWN + ': its close had taken' if closed else QUIT_FORCED_NOT_CLOSED
        return prefix + 'Designer quit after %.0fs (%s; its log stopped at "%s").%s' % (took, how, last, sampled), True
    raise ToolError(prefix + _could_not_end(own) + sampled)  # its notes and uploads line too (REVIEW.md SRV-166)
