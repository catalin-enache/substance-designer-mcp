"""Designer itself: designer_status, launch_designer, quit_designer.

A Designer an agent started is disposable: it can be ended however works. Any other is the user's: the tools never end it.
"""

import contextlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from textwrap import dedent

from mcp.server.mcpserver.exceptions import ToolError

from project_constants import (  # on sys.path: the package's __init__ imports .core, which puts it there
    PLUGIN,
    STARTUP_LIMIT,
    agent_designer_file,
)

from .core import _bridge, _checked, _control, _designer_running, _helpers_call, _Refused, _server_versions, _tool


@_tool()
def designer_status() -> str:
    """Report Designer's version, the bridge state (idle/running) and the open user packages (an
    unsaved one by its UID, as list_snapshots names it), whether an agent started it, plus this server's Python and library versions. While a job runs or waits, only the bridge
    state is reported: the package list would have to wait for the job."""
    state = _control('status', wait=10)
    if 'idle, 0 queued' not in state:  # the listing is a job too; it would queue (REVIEW.md SRV-22)
        return (
            state
            + '\n'
            + _started_by()
            + '\n'
            + _server_versions()
            + '\n(Designer version and package list skipped while a job runs)'
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
        """)
    )
    answering = re.search(r'^process (\d+)$', listing, re.M)
    started_by = _started_by(int(answering.group(1)) if answering else None)
    return state + '\n' + started_by + '\n' + _server_versions() + '\n' + listing


def _started_by(answering: int | None = None) -> str:
    """Who started the Designer answering, or with its process unknown, the only one running. Unclear means the user's."""
    running = [answering] if answering is not None else _designer_pids()
    own = _agent_designer()
    if own is not None and running == [own]:
        return 'Started by an agent: disposable, nothing in it is kept.'
    return "Not started by an agent: it is the user's."


DESIGNER_APP = {
    'darwin': '/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app',
    'win32': r'C:\Program Files\Adobe\Adobe Substance 3D Designer\Adobe Substance 3D Designer.exe',
}


def _designer_pids() -> list[int]:
    """Designer's processes, where one may be ended. None on Windows: ending one there hasn't been tried."""
    if sys.platform == 'win32':
        return []
    out = subprocess.run(
        ['pgrep', '-f', 'MacOS/Adobe Substance 3D Designer( |$)'], capture_output=True, text=True
    ).stdout
    return [int(pid) for pid in out.split()]


def _process_start(pid: int) -> str | None:
    return (
        subprocess.run(['ps', '-o', 'lstart=', '-p', str(pid)], capture_output=True, text=True).stdout.strip() or None
    )


def _remember_started(before: list[int]) -> bool:
    """Record the one process that appeared since `before`. Two new ones can't be told apart, and neither counts."""
    new = [pid for pid in _designer_pids() if pid not in before]
    if len(new) != 1:
        return False
    start = _process_start(new[0])
    if start is None:
        return False
    with contextlib.suppress(OSError), open(agent_designer_file(), 'w', encoding='utf-8') as f:
        json.dump({'pid': new[0], 'start': start}, f)
    return True


def _forget_started() -> None:
    with contextlib.suppress(OSError):
        os.remove(agent_designer_file())


def _agent_designer() -> int | None:
    """The process ID of the Designer an agent started, if it is still running. The start time tells it from a later
    process given the same ID. Anything unclear means it isn't an agent's, and a stale file goes."""
    try:
        with open(agent_designer_file(), encoding='utf-8') as f:
            record = json.load(f)
        pid, start = record['pid'], record['start']
        if isinstance(pid, int) and pid in _designer_pids() and _process_start(pid) == start:
            return pid
    except OSError:
        return None
    except (ValueError, KeyError, TypeError):
        pass
    _forget_started()
    return None


def _still_starting() -> bool:
    """Whether the record, written as the process appeared, is younger than STARTUP_LIMIT."""
    try:
        return time.time() - os.path.getmtime(agent_designer_file()) < STARTUP_LIMIT
    except OSError:
        return False


def _force_end(pid: int) -> bool:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, sig)
        for _ in range(5):
            if pid not in _designer_pids():
                _forget_started()
                return True
            time.sleep(1)
    return False


def _end_if_past_startup() -> bool:
    """End the Designer an agent started, unless it may still be starting: it is disposable, so it isn't waited for past
    that (REVIEW.md HLP-82), but a retry mustn't kill one that is only slow (REVIEW.md SRV-75)."""
    own = _agent_designer()
    if own is None or _still_starting():
        return False
    if not _force_end(own):
        raise ToolError(_could_not_end(own))  # once is enough (REVIEW.md SRV-79)
    return True


def _could_not_end(pid: int) -> str:
    return 'Designer %d could not be ended; ask the user to run `kill -9 %d`.' % (pid, pid)


def _how_to_end() -> str:
    """What the user can do about a Designer the tools won't end."""
    pids = _designer_pids()
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


@_tool()
def launch_designer(wait_s: int = 180) -> str:
    """Start Substance Designer if it isn't running and wait until the bridge plugin answers.
    When it starts Designer it also closes the Home screen, so the editor panels are visible.
    A Designer that is running but not answering yet is waited for, not started again; if it exits
    during the wait, a new one is started and gets its own wait_s, so the call can then take up to
    about twice wait_s. One an agent started is waited for only until 180 s after it started; past that, not answering,
    it is ended and a new one started, and the result says so.
    For tests and work on this project: if a task needs Designer and it is closed, ask the user to open it.
    Override the app location with SD_DESIGNER_APP."""
    try:
        return 'Designer already running: ' + _control('status', wait=5)
    except _Refused:
        raise  # it runs and answers: starting or waiting for another wouldn't help
    except ToolError:
        pass
    # A Designer process without an answering bridge (still starting, a dialog, the plugin didn't
    # load) is waited for, not started again (Windows would open a second instance). If it exits
    # while we wait (it was shutting down, or hung after a crash), a new one is started then.
    app = os.environ.get('SD_DESIGNER_APP') or DESIGNER_APP.get(sys.platform)

    ended_note = 'Ended a Designer an agent started, which was not answering.\n'
    note = ended_note if _end_if_past_startup() else ''
    before: list[int] | None = None  # set once this call starts one: the processes there were

    def start() -> None:
        nonlocal before
        if not app or not os.path.exists(app):
            raise ToolError('%sDesigner not found at %r; set SD_DESIGNER_APP' % (note, app))
        before = _designer_pids()
        if sys.platform == 'darwin':
            subprocess.Popen(['open', '-a', app])
        elif sys.platform == 'win32':
            os.startfile(app)
        else:
            subprocess.Popen([app])

    running, restarted = _designer_running(), False
    if not running:
        start()
    started = time.time()
    while time.time() - started < wait_s:
        time.sleep(2)
        if before is not None and _remember_started(before):
            before = None
        try:
            status = _control('status', wait=5)
        except _Refused:
            raise
        except ToolError:
            if running and _end_if_past_startup():
                note = ended_note
            if running and not _designer_running():
                running, restarted = False, True
                start()
                started = time.time()  # the new one gets the whole wait (REVIEW.md SRV-19)
            continue
        if running:
            return note + 'Designer already running: ' + status
        # we started it, so nobody is using the Home screen: show the editor panels
        home = _bridge(_helpers_call('leave_home_screen()'), timeout=30).strip()
        return note + 'Designer started in %.0fs%s: %s' % (
            time.time() - started,
            ' (%s)' % home if home else '',
            status,
        )
    if not running:
        what_next = (
            ' If it needs longer, call this with a larger wait_s.'  # a retry may never finish (REVIEW.md SRV-80)
        )
    elif _agent_designer() is not None:
        what_next = (
            ' An agent started it: calling this again waits for it, and ends it once it has had %ds to start.'
            % STARTUP_LIMIT
        )
    else:
        what_next = (
            ' If its windows have closed, it is stuck closing and nothing is lost: %s. If they are open, ask the user to '
            'save and close it.' % _how_to_end()
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
def quit_designer(wait_s: int = 10) -> str:
    """Close a Designer an agent started, and wait until its process has exited: unsaved changes are dropped, and after
    wait_s it is force-ended; the result says which. Running a job, it isn't asked to close. Not replying to the close
    within wait_s (at least 10 s) adds that to the wait. Any other Designer is the user's: this ends nothing and says to ask them to save, close and reopen it."""
    own = _agent_designer()
    if own is None:
        if not _designer_running():
            return 'Designer is not running.'
        raise ToolError("This Designer wasn't started by an agent: ask the user to save, close and reopen it.")
    try:
        state = _control('status', wait=5)
        if 'idle, 0 queued' not in state:  # the close would queue behind it, for up to 15 minutes (REVIEW.md SRV-74)
            raise ToolError('busy: %s' % state)
        # it goes to whichever Designer holds the port, so it names this one and any other refuses (REVIEW.md SRV-73)
        call = _helpers_call('quit_designer(%d)' % own)
        # a frozen main thread reads as idle too, and a close running late runs in the process being ended (REVIEW.md SRV-78)
        reply = _bridge(call, timeout=30, wait=max(wait_s, 10))
        notes = _checked(reply).replace('closing Designer', '').strip()
    except ToolError as e:  # it can't be asked, only ended; or the reply was lost as it quit
        notes = 'Designer was not asked to close, or did not reply: %s' % e
    prefix = notes + '\n' if notes else ''
    started = time.time()
    while time.time() - started < wait_s:
        time.sleep(1)
        if own not in _designer_pids():
            _forget_started()
            return prefix + 'Designer quit after %.0fs.' % (time.time() - started)
    if _force_end(own):  # it can hang at the very end of its shutdown, past anything inside it (REVIEW.md HLP-82)
        return prefix + 'Designer quit after %.0fs (forced: it had not closed).' % (time.time() - started)
    raise ToolError(_could_not_end(own))
