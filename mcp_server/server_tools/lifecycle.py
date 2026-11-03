"""Designer itself: designer_status, launch_designer, quit_designer."""

import os
import subprocess
import sys
import time
from textwrap import dedent

from mcp.server.mcpserver.exceptions import ToolError

from project_constants import PLUGIN  # on sys.path: the package's __init__ imports .core, which puts it there

from .core import _bridge, _checked, _control, _designer_running, _helpers_call, _Refused, _server_versions, _tool


@_tool()
def designer_status() -> str:
    """Report Designer's version, the bridge state (idle/running) and the open user packages (an
    unsaved one by its UID, as list_snapshots names it), plus this server's Python and library versions. While a job runs or waits, only the bridge
    state is reported: the package list would have to wait for the job."""
    state = _control('status', wait=10)
    if 'idle, 0 queued' not in state:  # the listing is a job too; it would queue (REVIEW.md SRV-22)
        return state + '\n' + _server_versions() + '\n(Designer version and package list skipped while a job runs)'
    return (
        state
        + '\n'
        + _server_versions()
        + '\n'
        # an unsaved package is named by its UID, as list_snapshots names them (REVIEW.md SRV-45)
        + _bridge(
            dedent("""\
                import sd
                app = sd.getContext().getSDApplication()
                print('Designer', app.getVersion())
                for p in app.getPackageMgr().getUserPackages():
                    print('package:', p.getFilePath() or '(an unsaved package, UID %s)' % p.getUID())
                    for r in p.getChildrenResources(True):
                        print('   ', type(r).__name__, r.getIdentifier())
            """)
        )
    )


DESIGNER_APP = {
    'darwin': '/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app',
    'win32': r'C:\Program Files\Adobe\Adobe Substance 3D Designer\Adobe Substance 3D Designer.exe',
}


@_tool()
def launch_designer(wait_s: int = 180) -> str:
    """Start Substance Designer if it isn't running and wait until the bridge plugin answers.
    When it starts Designer it also closes the Home screen, so the editor panels are visible.
    A Designer that is running but not answering yet (still starting) is waited for, not started
    again; if it exits during the wait, a new one is started and gets its own wait_s, so the call
    can then take up to about twice wait_s.
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

    def start() -> None:
        if not app or not os.path.exists(app):
            raise ToolError('Designer not found at %r; set SD_DESIGNER_APP' % app)
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
        try:
            status = _control('status', wait=5)
        except _Refused:
            raise
        except ToolError:
            if running and not _designer_running():
                running, restarted = False, True
                start()
                started = time.time()  # the new one gets the whole wait (REVIEW.md SRV-19)
            continue
        if running:
            return 'Designer already running: ' + status
        # we started it, so nobody is using the Home screen: show the editor panels
        home = _bridge(_helpers_call('leave_home_screen()'), timeout=30).strip()
        return 'Designer started in %.0fs%s: %s' % (time.time() - started, ' (%s)' % home if home else '', status)
    raise ToolError(
        '%s did not answer within %ds%s. It may be showing a dialog, or the '
        '%s plugin did not load (check the Designer log).'
        % (
            'Designer is already running, but its bridge' if running else 'Designer',
            wait_s,
            ' of being started' if restarted else '',
            PLUGIN,
        )
    )


@_tool()
def quit_designer(discard_unsaved: bool = False, wait_s: int = 60) -> str:
    """Close Substance Designer and wait until its process has exited (for example to restart it
    after a plugin change, with launch_designer). Refuses while any open package has unsaved
    changes and lists them; save them first, or pass discard_unsaved=True to drop all of them
    (only when the user said so, or when every package listed is the self-test's own)."""
    try:
        _control('status', wait=5)
    except _Refused:
        raise
    except ToolError as e:
        if not _designer_running():
            return 'Designer is not running.'
        raise ToolError('A Designer process is running but the bridge does not answer; close Designer by hand.') from e
    text = _checked(_bridge(_helpers_call('quit_designer(%r)' % discard_unsaved), timeout=30))
    started = time.time()
    while time.time() - started < wait_s:
        time.sleep(1)
        if not _designer_running():
            notes = text.replace('closing Designer', '').strip()
            return (notes + '\n' if notes else '') + 'Designer quit after %.0fs.' % (time.time() - started)
    raise ToolError('Designer is still running after %ds; it may be showing a dialog.' % wait_s)
