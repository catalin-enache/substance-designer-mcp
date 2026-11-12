"""Quitting and starting Designer, in a Designer the self-test started: it is disposable. Force-ending one that stays,
what is left to finish, refusing a Designer no agent started, launch_designer again. It relies on no other category:
run() starts from a Designer of its own and leaves none running, so it also runs alone, with
`alone.run(lifecycle.run, own_designer=True)`."""

import contextlib
import glob
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

from project_constants import (
    QUIT_CLOSED,
    QUIT_FORCED_IN_SHUTDOWN,
    QUIT_FORCED_NOT_CLOSED,
    STARTUP_LIMIT,
    TOKEN_FILE,
    agent_designer_file,
)
from test_all_tools import common, launch_lock
from test_all_tools.common import (
    Ctx,
    agent_folder,
    agents_designers,
    check,
    crash_dumps,
    designer_pids,
    designer_script,
    free_port,
    helpers_source,
    normal_close,
    raw_request,
    skip,
    text,
)
from test_all_tools.crash_watch import watching_crashes
from test_all_tools.lifecycle.samples import sampled

CLOSE_WINDOWS_ONLY = dedent("""\
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    def close_windows():
        for w in QApplication.instance().topLevelWidgets():
            if w.isVisible():
                w.close()
    QTimer.singleShot(300, close_windows)""")

BUSY_LOOP = dedent("""\
    import time
    while True:
        time.sleep(0.1)""")

# frozen outside any bridge job: the plugin's status, answered from another thread, can't tell
FREEZE_MAIN_THREAD = dedent("""\
    import time
    from PySide6.QtCore import QTimer
    def freeze():
        while True:
            time.sleep(0.1)
    QTimer.singleShot(300, freeze)""")


def users_log() -> tuple[str, int] | None:
    """The log Designers write that have no home of their own (the user's), as read_designer_log finds it
    (SD_DESIGNER_LOG included), and its size; None while there is none, where the user never opened Designer: then
    none appearing is the log left alone (REVIEW.md TST-156)."""
    from server_tools.log import _designer_log_path

    path = _designer_log_path()
    return (path, os.path.getsize(path)) if path and os.path.isfile(path) else None


def users_settings_file() -> str | None:
    """The settings file of the Designers that have no home of their own (the user's), the newest version's; macOS."""
    found = glob.glob(
        os.path.expanduser('~/Library/Application Support/Adobe/Adobe Substance 3D Designer/*/user_preferences.xml')
    )
    return max(found, key=os.path.getmtime) if found else None


def agent_port_free(port: int) -> bool:
    """No Designer an agent started is recorded on `port`, and none has its folder there: another run's, still starting,
    listens nowhere yet, so a port that binds may still be its (REVIEW.md TST-154, TST-172)."""
    return not os.path.exists(agent_designer_file(port)) and not os.path.exists(agent_folder(port))


def unused_port(take: Callable[[], int] | None = None) -> int:
    """A port from `take` (free_port by default) that is agent_port_free, or 0 after ten tries: every port a
    lifecycle check starts a Designer on, or holds, comes from here."""
    for _ in range(10):
        port = (take or free_port)()
        if agent_port_free(port):
            return port
    return 0


def own_pid() -> int | None:
    """The process of the Designer an agent recorded on this run's port, if it runs: what a quit check is about."""
    return agents_designers().get(common.PORT)


def has_ended(pid: int | None) -> bool:
    """Whether that process has ended. Not whether no Designer runs that may be the run's: in a pool another worker's,
    starting and not yet recorded, may be for all one can tell."""
    return pid is not None and pid not in designer_pids()


async def check_launch_on_another_port(ctx: Ctx) -> None:
    """A second Designer an agent started, next to the run's on a port of its own (ROADMAP item 49): each answers on its
    own port from its own process, and quitting it leaves the first. It quits only the one it started, so it runs in a
    scratch run too (the live-check skill)."""
    c = ctx.c
    # a free port another run's Designer, still starting, doesn't hold: that one isn't this check's to quit
    # (REVIEW.md TST-154)
    other = unused_port()
    if not other:
        check('launch_designer', 'finds a port no Designer an agent started is recorded for', False, 'ten tries')
        return
    record = agent_designer_file(other)
    first = text(await c('execute_designer_code', {'code': 'import os; print(os.getpid())'})).strip()
    # a Designer finds one already running through a socket in its temp folder, and hands over to it (measured)
    temp = text(
        await c('execute_designer_code', {'code': 'from PySide6.QtCore import QDir; print(QDir.tempPath())'})
    ).strip()
    own = agent_folder(common.PORT)  # the folders launch_designer gives it
    check(
        'launch_designer',
        'gives the Designer it starts a temp folder of its own',
        os.path.realpath(temp) == os.path.realpath(own + '/temp'),
        temp,
    )
    # macOS: a home of its own (CFFIXED_USER_HOME), where it writes its log, and our plugin loads from
    # SBS_DESIGNER_PYTHON_PATH: the bridge answering these calls shows it did
    t = text(await c('read_designer_log', {'contains': 'listening on', 'lines': 1}))
    check(
        'launch_designer',
        'gives the Designer it starts a home of its own, where it writes its log',
        t.startswith(own + '/home/') and 'listening on 127.0.0.1:%d' % common.PORT in t,
        t,
    )
    # as `open -a` started it: nothing in the server's folder (the repository) is in Designer's
    cwd = text(await c('execute_designer_code', {'code': 'import os; print(os.getcwd())'})).strip()
    check('launch_designer', 'starts Designer in /, not in the folder of the server', cwd == '/', cwd)
    with watching_crashes(ctx) as watch:
        step = watch.step(ports=[other])
        log_before = users_log()
        users_settings = users_settings_file()
        settings_before = os.path.getmtime(users_settings) if users_settings else None
        second: int | None = None
        its_quit = ''  # the other port's quit: its folder kept if forced, to read its log (REVIEW.md TST-293)
        try:
            t = text(await c('launch_designer', {'port': other, 'wait_s': 240}))
            check(
                'launch_designer',
                'starts a second Designer on another port, recorded for it',
                'Designer started in' in t and 'on port %d' % other in t and os.path.exists(record),
                t,
            )
            # the port was free of any run's record and folder just before (unused_port), so one recorded now is this
            # launch's, unless the answer says one was already there (REVIEW.md TST-154); started and never answering,
            # it is left running by launch_designer: this check ends it (REVIEW.md TST-187)
            started = 'Designer started in' in t or ('did not answer within' in t and 'already running' not in t)
            if not started:
                return  # none started here: whatever answers there isn't this check's to quit
            if not os.path.exists(record):  # started, unrecorded: the tools take it for the user's
                print(
                    'lifecycle: a Designer started on port %d, unrecorded: %s'
                    % (other, text(await c('designer_status', {'port': other})))
                )
                return
            second = json.loads(Path(record).read_text())['pid']
            if 'Designer started in' not in t:
                return  # the check above failed, with why; the finally ends it
            theirs = os.path.join(agent_folder(other), 'home') + '/'
            t = text(await c('read_designer_log', {'port': other, 'contains': 'listening on'}))
            mine = text(await c('read_designer_log', {'contains': ':%d' % other, 'since_last_start': False}))
            check(
                'read_designer_log',
                "reads each Designer's own log: neither holds a line of the other's",
                t.startswith(theirs)
                and 'listening on 127.0.0.1:%d' % other in t
                and 'listening on 127.0.0.1:%d' % common.PORT not in t
                and '(0 matching lines' in mine.splitlines()[0],
                '%s / the first: %s' % (t, mine.splitlines()[0]),
            )
            log_after = users_log()
            check(
                'launch_designer',
                "the Designers it starts leave the user's log alone: not one byte written to it",
                log_after == log_before,
                '(log, size) before: %s, after: %s' % (log_before, log_after),
            )
            status = text(await c('designer_status', {'port': other}))
            check(
                'designer_status',
                'reaches the Designer on another port: its plugin listens there, in the process started',
                'process %s\n' % second in status
                and str(second) != first
                and 'Bridge port %d.' % other in status
                and 'Started by an agent' in status,
                '%s; the first: %s' % (status, first),
            )
            status = text(await c('designer_status'))
            check(
                'designer_status',
                "still reaches the first on the server's port, and lists the other",
                'process %s\n' % first in status
                and 'Bridge port %d.' % common.PORT in status
                and 'Started by an agent' in status
                # other runs' Designers may be listed too (alone.run(port=...) side by side)
                and re.search(
                    r'^Designers an agent started on other ports: .*\b%d \(process %s\)' % (other, second), status, re.M
                )
                is not None,
                status,
            )
            t = its_quit = text(await c('quit_designer', {'port': other, 'wait_s': 30}))
            status_after = await c('designer_status')
            check(
                'quit_designer',
                'closes the Designer on another port, and only that one',
                normal_close(t, 'closes the Designer on another port')
                and not os.path.exists(record)
                and second not in designer_pids()
                and int(first) in designer_pids()
                and 'process %s\n' % first in text(status_after),
                t,
            )
            watch.check(step, 'quit_designer', 'the second Designer leaves no crash dump', True)
            # its home, fresh for this port: its settings and its crash-dump database are there, the user's settings are
            # left as they were (server_tools/lifecycle.py; REVIEW.md TST-160)
            data = os.path.join(theirs, 'Library', 'Application Support', 'Adobe', 'Adobe Substance 3D Designer')
            settings = glob.glob(os.path.join(data, '*', 'user_preferences.xml'))
            after = os.path.getmtime(users_settings) if users_settings else None
            check(
                'launch_designer',
                "the Designer it starts keeps its settings and crash dumps in its own home, not the user's",
                bool(settings) and os.path.isdir(os.path.join(data, 'Sentry-Crashpad')) and after == settings_before,
                "%s; Sentry-Crashpad: %s; the user's settings %s: %s, then %s"
                % (
                    settings,
                    os.path.isdir(os.path.join(data, 'Sentry-Crashpad')),
                    users_settings,
                    settings_before,
                    after,
                ),
            )
        finally:
            if second is not None:  # only one this check started (REVIEW.md TST-154)
                if second in designer_pids():  # a failed check left it: it is disposable
                    await c('quit_designer', {'port': other, 'wait_s': 10})
                ended = second not in designer_pids()

                def remove_its_folder() -> None:  # once a late crash dump would be there
                    theirs_dumps = {d for d in crash_dumps([other]) if d.startswith(agent_folder(other) + '/')}
                    if ended and not theirs_dumps and 'forced' not in its_quit:  # a crash dump or forced quit: kept
                        shutil.rmtree(agent_folder(other), ignore_errors=True)
                    elif ended:
                        print('kept, to read:', agent_folder(other))

                watch.later(remove_its_folder)


async def check_launch_refuses_a_port_another_program_holds(ctx: Ctx) -> None:
    """REVIEW.md SRV-85: a program listening on 127.0.0.1 at the port asked for keeps the plugin off it, so
    launch_designer refuses at once instead of starting a Designer that can't listen there. It quits only a Designer
    it started, so it runs in a scratch run too (the live-check skill)."""
    held: list[socket.socket] = []

    def hold() -> int:
        holder = socket.socket()
        holder.bind(('127.0.0.1', 0))
        holder.listen(4)
        held.append(holder)
        return int(holder.getsockname()[1])

    port = unused_port(hold)  # not one another run's Designer is starting on (REVIEW.md TST-172)
    for other in held[:-1]:
        other.close()
    holder = held[-1]
    if not port:
        holder.close()
        check(
            'launch_designer', 'refuses a port another program holds, starting nothing', False, 'no port free of runs'
        )
        return
    record = agent_designer_file(port)
    began = time.time()
    try:
        r_ = await ctx.c('launch_designer', {'port': port, 'wait_s': 30})
        took = time.time() - began
        check(
            'launch_designer',
            'refuses a port another program holds, starting nothing',
            r_.is_error and 'Port %d is held by another program' % port in text(r_) and not os.path.exists(record),
            '%.0fs: %s' % (took, text(r_)),
        )
    finally:
        holder.close()
        if os.path.exists(record):  # a failed check started one: it is disposable
            await ctx.c('quit_designer', {'port': port, 'wait_s': 10})
        shutil.rmtree(agent_folder(port), ignore_errors=True)


async def check_a_designer_sharing_the_temp_folder_hands_over(ctx: Ctx) -> None:
    """Why launch_designer gives each Designer a temp folder of its own: a Designer starting reads the process ID of
    the last one started (`session.instancePID` in Designer's settings) and looks for that one's socket
    (algipc-...-<ID>) in its own temp folder; found, it hands it its arguments and exits, its own log naming that one's
    process. Started here from the binary as launch_designer starts one (_designer_env: a home of its own, so its log is
    its own and the user's is left alone; no plugins), on a port of its own, with the temp folder of the run's
    Designer; ended if it stays. It ends only the Designer it
    started, so it runs in a scratch run too (the live-check skill), but skips unless the run's Designer was
    the last one started: run it before check_launch_on_another_port."""
    c = ctx.c
    name = 'a Designer sharing the temp folder of the last one started hands over to it and exits'
    if sys.platform != 'darwin':
        skip('designer facts', name, 'measured on macOS')
        return
    probe = 'import os; from PySide6.QtCore import QDir; print(QDir.tempPath()); print(os.getpid())'
    temp, pid = text(await c('execute_designer_code', {'code': probe})).strip().splitlines()
    saved = subprocess.run(
        ['defaults', 'read', 'com.adobe.Adobe Substance 3D Designer', 'session.instancePID'],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if saved != pid:  # only read: the settings are the user's too
        skip('designer facts', name, "the last Designer started is %s, not the run's %s" % (saved or '?', pid))
        return
    app = (
        os.environ.get('SD_DESIGNER_APP') or '/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app'
    )
    port = unused_port()  # not one another run's Designer is starting on (REVIEW.md TST-172)
    if not port:
        check('designer facts', name, False, 'no port free of other runs in ten tries')
        return
    folder = agent_folder(port)
    home = os.path.join(folder, 'home')  # where it writes its log, with a home of its own (REVIEW.md TST-148)
    log_before = users_log()
    # as launch_designer starts one (a home of its own, the server's Python settings left out), but the run Designer's
    # temp folder, which is the point, and no plugins: it is to hand over before loading any
    from server_tools.lifecycle import _designer_env, _own_folder

    env = _designer_env(port, temp + '/', _own_folder(port, 'home'), '')
    quiet = subprocess.DEVNULL
    with watching_crashes(ctx) as watch:
        step = watch.step(ports=[port])
        try:
            proc = subprocess.Popen(
                [os.path.join(app, 'Contents', 'MacOS', 'Adobe Substance 3D Designer')],
                env=env,
                stdin=quiet,
                stdout=quiet,
                stderr=quiet,
                start_new_session=True,
                cwd='/',
            )
            try:
                try:
                    proc.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    pass
                exited = proc.poll() is not None
                first = await c('designer_status')
            finally:
                if proc.poll() is None:  # it stayed: disposable, started here
                    proc.terminate()
                    try:
                        proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
            # its own log names the run's Designer as the one it handed over to: a crash or a failed start says nothing of
            # the kind (REVIEW.md TST-149)
            own_logs = glob.glob(
                os.path.join(
                    home, 'Library', 'Application Support', 'Adobe', 'Adobe Substance 3D Designer', '*', 'log.txt'
                )
            )
            found = [
                line.strip()
                for log in own_logs
                for line in Path(log).read_text(encoding='utf-8', errors='replace').splitlines()
                if '[IPC] Found instance PID:' in line
            ]
            log_after = users_log()
            watch.check(
                step,
                'designer facts',
                name,
                exited and not first.is_error and found == ['[INFO][IPC] Found instance PID: %s' % pid],
                'exited: %s (code %s); the one running still answers: %s; its own log: %s'
                % (exited, proc.returncode, not first.is_error, found or own_logs or 'none'),
            )
            check(
                'designer facts',
                "the Designer started for it leaves the user's log alone",
                log_after == log_before,
                '(log, size) before: %s, after: %s' % (log_before, log_after),
            )
        finally:

            def remove_its_folder() -> None:  # once a late crash dump would be there
                if not crash_dumps([port]) - step.before:  # a crash dump is kept, to read
                    shutil.rmtree(folder, ignore_errors=True)

            watch.later(remove_its_folder)


async def check_a_designer_of_its_own(ctx: Ctx) -> bool:
    """What the checks below need and nothing else of the suite gives them: the guide read (tools refuse before it), and
    a Designer started here, so it holds nothing an earlier check left and is the last one started (the hand-over check).
    One an agent started is replaced; one no agent started is left alone and nothing runs. Whether they can run."""
    c = ctx.c
    await c('get_guide')
    await c('get_guide', {'part': 'scripting'})
    name = 'the lifecycle checks start from a Designer of their own'
    status = await c('designer_status')
    if not status.is_error:
        if 'Started by an agent' not in text(status):
            check('launch_designer', name, False, "a Designer no agent started answers on this port: it isn't theirs")
            return False
        with watching_crashes(ctx) as watch:  # in a scratch run, where alone keeps its Designer (REVIEW.md TST-257)
            step = watch.step()
            quit_ = await c('quit_designer', {'wait_s': 30})
            watch.check(
                step,
                'quit_designer',
                "closes the agent's Designer it replaces, without a crash",
                not quit_.is_error,
                text(quit_),
            )
    t = text(await c('launch_designer', {'wait_s': 240}))
    started = 'Designer started in' in t and 'ERROR' not in t
    check('launch_designer', name, started, t)
    return started


# the 3D view's dock looked up, then a set-up with no render: a 3D shot would go through the clipboard, which the
# categories of categories.CLIPBOARD use beside this one
WAITS_FOR_A_GRAPH = dedent("""
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    for step in (lambda: _3d_dock(mw), lambda: set_3d_view(None, 'Plane')):
        try:
            step()
            print('BUILT')
        except RuntimeError as e:
            print('REFUSED: %s' % e)""")


async def check_the_3d_view_waits_for_a_graph(ctx: Ctx) -> None:
    """Designer builds its 3D view (the menu bar and the viewport) once a graph is opened, so in a Designer just started
    the 3D view's dock, which screenshot_designer('3d') and its set-up both go through, says to open one (REVIEW.md
    HLP-115). Measured right after its Designer starts, before any graph is opened."""
    t = text(await ctx.c('execute_designer_code', {'code': ctx.helper_source + WAITS_FOR_A_GRAPH}))
    check(
        'screenshot_designer',
        '3d with no graph opened yet says to open one, a set-up too',
        t.count("REFUSED: the 3D view isn't built yet") == 2 and 'open_graph' in t and 'BUILT' not in t,
        t.strip()[-300:],
    )


async def run(ctx: Ctx) -> None:
    with watching_crashes(ctx):  # one wait for crash dumps, at the end, for every check below
        # in a pool, no other Designer starts from before its own does until the hand-over check has used it: that one
        # needs it to be the last one started (launch_lock)
        with launch_lock.held(own='lifecycle'):
            if not await check_a_designer_of_its_own(ctx):
                return
            await check_a_designer_sharing_the_temp_folder_hands_over(ctx)
        await check_the_3d_view_waits_for_a_graph(ctx)  # before any graph is opened: the hand-over check opens none
        await check_launch_on_another_port(ctx)
        await check_launch_refuses_a_port_another_program_holds(ctx)
        await check_quitting_and_starting_again(ctx)


async def check_quitting_and_starting_again(ctx: Ctx) -> None:
    """Refusing a Designer no agent started, then the quits of the run's own Designer (normal, forced, stuck, busy,
    frozen, slow, with a dialog), each followed by launch_designer: it ends with none running."""
    c, scratch = ctx.c, ctx.scratch
    with watching_crashes(ctx) as watch:
        # a Designer no agent started is the user's: with the record gone this one counts as that, and nothing reaches it
        record = agent_designer_file(common.PORT)
        check('launch_designer', 'records the Designer it started', os.path.exists(record), record)
        if not os.path.exists(record):
            return  # nothing below can run: the check above says so
        kept = record + '.kept'
        # meanwhile any launch_designer on the machine refuses, a Designer no agent started being open: none in a pool
        with launch_lock.held(own='lifecycle'):
            os.replace(record, kept)
            try:
                status = text(await c('designer_status'))
                r_ = await c('quit_designer')
                time.sleep(2)
                refused = r_.is_error and 'ask the user to save, close and reopen' in text(r_)
                alive = not (await c('designer_status')).is_error
            finally:
                os.replace(kept, record)
        check('quit_designer', 'refuses a Designer no agent started, and it stays open', refused and alive, text(r_))
        check('designer_status', 'says when no agent started it', 'Not started by an agent' in status, status)
        status = text(await c('designer_status'))
        check('designer_status', 'says when an agent started it', 'Started by an agent' in status, status)

        # unsaved changes in an agent's Designer are dropped, and it says so
        await c('create_graph', {'name': 'mcp_selftest_unsaved_at_quit', 'size_log2': 4})
        await c(
            'apply_edits', {'ops': [{'op': 'add', 'definition': 'levels'}], 'graph': 'mcp_selftest_unsaved_at_quit'}
        )

        # the close names its process: asked of another, it refuses before touching anything (REVIEW.md SRV-73)
        call = '\n\nquit_designer(1, %r)\n' % QUIT_CLOSED
        r_ = await c('execute_designer_code', {'code': helpers_source() + call})
        time.sleep(1)
        status = text(await c('designer_status'))
        check(
            'quit_designer',
            'the close asked of another process changes nothing',
            'nothing closed' in text(r_) and 'mcp_selftest_unsaved_at_quit' in status,
            text(r_).strip().splitlines()[-1],
        )
        pid = text(await c('execute_designer_code', {'code': 'import os; print(os.getpid())'})).strip()
        check(
            'designer_status',
            'names the process answering, the one recorded',
            'process %s\n' % pid in status and str(json.loads(Path(record).read_text())['pid']) == pid,
            pid,
        )

        step = watch.step()
        quitting = own_pid()  # the process this quit is about
        t = text(await c('quit_designer', {'wait_s': 30}))
        check(
            'quit_designer',
            "closes an agent's Designer with unsaved changes, dropping them",
            'discarding unsaved changes' in t
            and normal_close(t, "closes an agent's Designer with unsaved changes")
            and has_ended(quitting),
            t,
        )
        watch.check(step, 'quit_designer', 'a normal close leaves no crash dump', True, t)
        t = text(await c('launch_designer', {'wait_s': 240}))
        check('launch_designer', 'starts again after a quit', 'Designer started in' in t and 'ERROR' not in t, t)

        # windows ignoring Close, as under a blocking dialog: past its wait it is forced, with no aboutToQuit
        step = watch.step()
        forced_marker = os.path.join(scratch, 'forced_quit_about_to_quit')
        await designer_script(c, 'lifecycle/quit_ignores_close', marker=forced_marker)
        quitting = own_pid()  # the process this quit is about
        t = text(await c('quit_designer', {'wait_s': 2}))
        watch.check(
            step,
            'quit_designer',
            'forces one whose window stays open, without a crash',
            QUIT_FORCED_NOT_CLOSED in t and has_ended(quitting) and not os.path.exists(forced_marker),
            t,
        )
        t = text(await c('launch_designer', {'wait_s': 240}))
        check('launch_designer', 'starts again after a forced quit', 'Designer started in' in t and 'ERROR' not in t, t)

        # stuck at the very end of its shutdown, where nothing inside Designer can act (REVIEW.md HLP-82)
        step = watch.step()
        held = text(await designer_script(c, 'lifecycle/hold_thread_pool'))
        quitting = own_pid()  # the process this quit is about
        t = text(await c('quit_designer', {'wait_s': 15}))
        watch.check(
            step,
            'quit_designer',
            'forces one stuck in its shutdown, without a crash',
            'HELD=True' in held and QUIT_FORCED_IN_SHUTDOWN in t and has_ended(quitting),
            held + t,
        )
        # its threads sampled before the force, for the cause of a hang (ROADMAP item 70): this one waits for the pool;
        # the detail says where its main thread was, as the pool deletes lifecycle's folder (REVIEW.md TST-310)
        stacks, where = sampled(t)
        check(
            'quit_designer',
            "samples one stuck in its shutdown before forcing it, the thread pool's wait shown",
            'QThreadPool::waitForDone' in stacks,
            where,
        )
        t = text(await c('launch_designer', {'wait_s': 240}))
        check(
            'launch_designer', 'starts again after a stuck shutdown', 'Designer started in' in t and 'Ended' not in t, t
        )

        # running a job, it isn't asked to close: the close would queue, with wait_s not even started (REVIEW.md SRV-74)
        token = Path(TOKEN_FILE).read_text().strip()  # used, never printed

        def hold_the_bridge() -> None:
            with contextlib.suppress(OSError, ValueError):  # no reply: Designer is ended under it
                raw_request({'code': BUSY_LOOP, 'timeout': 60}, token)

        long_job = threading.Thread(target=hold_the_bridge, daemon=True)
        long_job.start()
        time.sleep(2)
        step, quit_started = watch.step(), time.time()  # a dump of this quit is its own (REVIEW.md TST-236)
        quitting = own_pid()  # the process this quit is about
        t = text(await c('quit_designer', {'wait_s': 2}))
        took = time.time() - quit_started
        watch.check(
            step,
            'quit_designer',
            'forces one running a job after its wait, not asking it to close',
            'did not reply: busy' in t and QUIT_FORCED_NOT_CLOSED in t and has_ended(quitting) and took < 30,
            '%s; took %.0f s' % (t, took),
        )
        t = text(await c('launch_designer', {'wait_s': 240}))
        check(
            'launch_designer', 'starts again after a job was forced', 'Designer started in' in t and 'ERROR' not in t, t
        )

        # its main thread frozen outside a job, it reads as idle, and the close has a limit of its own (REVIEW.md SRV-78)
        await c('execute_designer_code', {'code': FREEZE_MAIN_THREAD})
        time.sleep(2)
        state = raw_request({'cmd': 'status'}, token)['output']
        check('designer facts', 'a main thread frozen outside a job reads as idle', 'idle, 0 queued' in state, state)
        step, quit_started = watch.step(), time.time()  # a dump of this quit is its own (REVIEW.md TST-236)
        quitting = own_pid()  # the process this quit is about
        t = text(await c('quit_designer', {'wait_s': 2}))
        took = time.time() - quit_started
        watch.check(
            step,
            'quit_designer',
            'forces one with a frozen main thread, within the limit of its close',
            'did not reply: No reply' in t and QUIT_FORCED_NOT_CLOSED in t and has_ended(quitting) and took < 30,
            '%s; took %.0f s' % (t, took),
        )
        t = text(await c('launch_designer', {'wait_s': 240}))
        check('launch_designer', 'starts again after a freeze', 'Designer started in' in t and 'ERROR' not in t, t)

        # the same, found by launch_designer: an agent's Designer not answering isn't waited for, past the startup limit
        step = watch.step()  # it ends that Designer, whose shutdown starts here (REVIEW.md TST-257)
        await designer_script(c, 'lifecycle/hold_thread_pool')
        await c('execute_designer_code', {'code': CLOSE_WINDOWS_ONLY})
        deadline = time.time() + 30
        while time.time() < deadline and not (await c('designer_status')).is_error:
            time.sleep(1)
        long_ago = time.time() - STARTUP_LIMIT - 1
        os.utime(record, (long_ago, long_ago))
        t = text(await c('launch_designer', {'wait_s': 240}))
        watch.check(
            step,
            'launch_designer',
            "ends an agent's Designer not answering, and starts a new one",
            'Ended a Designer an agent started' in t and 'Designer started in' in t,
            t,
        )
        stacks, where = sampled(t)  # it can be one hung in its shutdown, as this one is (REVIEW.md SRV-113)
        check(
            'launch_designer',
            "samples the agent's Designer it ends before forcing it, the thread pool's wait shown",
            'QThreadPool::waitForDone' in stacks,
            where,
        )

        # a window shown while the main window closes (a prompt appearing then), accepting its close: Designer quits once
        # the helper has closed both (REVIEW.md HLP-105, TST-307). A quit by itself emits aboutToQuit, which writes a marker
        prompt_marker = os.path.join(scratch, 'prompt_shown')
        normal_quit = os.path.join(scratch, 'quit_normally')
        await designer_script(
            c, 'lifecycle/quit_prompt_after_close', prompt_marker=prompt_marker, normal_quit=normal_quit, refuse=False
        )
        step, quit_started = watch.step(), time.time()
        quitting = own_pid()  # the process this quit is about
        t = text(await c('quit_designer', {'wait_s': 60}))
        took = time.time() - quit_started
        watch.check(
            step,
            'designer facts',
            'Designer quits once the helper has closed its window and a prompt shown as it closed',
            os.path.exists(prompt_marker)
            and Path(prompt_marker).read_text() == 'True'
            and os.path.exists(normal_quit)
            and has_ended(quitting),
            'prompt shown: %s; quit by itself (aboutToQuit): %s; gone after %.0f s'
            % (
                Path(prompt_marker).read_text() if os.path.exists(prompt_marker) else 'no',
                os.path.exists(normal_quit),
                took,
            ),
        )
        logged = text(await c('read_designer_log', {'contains': QUIT_CLOSED, 'lines': 1}))
        check(
            'quit_designer',
            'logs its close taken when a window shows as the main window closes',
            normal_close(t, 'a window shown as the main window closes') and QUIT_CLOSED in logged,
            '%s / %s' % (t, logged.splitlines()[-1]),
        )  # the prompt, shown after the helper listed the windows, accepts its close (REVIEW.md HLP-102, HLP-105)
        t = text(await c('launch_designer', {'wait_s': 240}))
        check('launch_designer', 'starts again', 'Designer started in' in t and 'ERROR' not in t, t)

        # the same prompt refusing its own close keeps Designer from quitting (measured): a forced quit says it had not
        # closed (REVIEW.md HLP-105)
        refusing_marker = os.path.join(scratch, 'refusing_prompt_shown')
        refusing_quit = os.path.join(scratch, 'refusing_prompt_quit')
        await designer_script(
            c,
            'lifecycle/quit_prompt_after_close',
            prompt_marker=refusing_marker,
            normal_quit=refusing_quit,
            refuse=True,
        )
        step = watch.step()
        quitting = own_pid()  # the process this quit is about
        t = text(await c('quit_designer', {'wait_s': 5}))
        shown = os.path.exists(refusing_marker) and Path(refusing_marker).read_text() == 'True'
        watch.check(
            step,
            'quit_designer',
            'forces one kept open by a prompt refusing its close, saying it had not closed, without a crash',
            shown and not os.path.exists(refusing_quit) and QUIT_FORCED_NOT_CLOSED in t and has_ended(quitting),
            '%s; prompt shown: %s; quit by itself (aboutToQuit): %s' % (t, shown, os.path.exists(refusing_quit)),
        )
        t = text(await c('launch_designer', {'wait_s': 240}))
        check(
            'launch_designer',
            'starts again after a quit kept open by a prompt',
            'Designer started in' in t and 'ERROR' not in t,
            t,
        )

        # Designer quits on its own window, the visible QStackedWidget (REVIEW.md HLP-19): with it hidden and another
        # window shown, the helper closes that one, Designer stays, and a forced quit says it had not closed (REVIEW.md
        # HLP-102, HLP-104)
        hidden = text(await designer_script(c, 'lifecycle/hide_own_window'))
        step = watch.step()
        quitting = own_pid()  # the process this quit is about
        t = text(await c('quit_designer', {'wait_s': 5}))
        watch.check(
            step,
            'quit_designer',
            "forces one whose own window wasn't shown, saying it had not closed, without a crash",
            'HIDDEN=1' in hidden and QUIT_FORCED_NOT_CLOSED in t and has_ended(quitting),
            '%s / %s' % (hidden.strip(), t),
        )
        t = text(await c('launch_designer', {'wait_s': 240}))
        check(
            'launch_designer',
            'starts again after a quit with its own window hidden',
            'Designer started in' in t and 'ERROR' not in t,
            t,
        )

        # forced in its aboutToQuit, its close taken: Designer's own shutdown, before it logs a line of its teardown, is
        # told from a close that didn't take by the line the quit helper logs (REVIEW.md SRV-106)
        early_close = os.path.join(scratch, 'early_close_finished')
        early_marker = os.path.join(scratch, 'early_shutdown_finished')
        await designer_script(c, 'lifecycle/quit_slow_shutdown', slow_close=early_close, slow_marker=early_marker)
        step = watch.step()
        quitting = own_pid()  # the process this quit is about
        t = text(await c('quit_designer', {'wait_s': 10}))
        closed_only = os.path.exists(early_close) and not os.path.exists(early_marker)
        watch.check(
            step,
            'quit_designer',
            'forces one stuck in its aboutToQuit, saying its close had taken, without a crash',
            closed_only and QUIT_FORCED_IN_SHUTDOWN in t and has_ended(quitting),
            '%s; its close handler finished and its aboutToQuit not: %s' % (t, closed_only),
        )
        t = text(await c('launch_designer', {'wait_s': 240}))
        check(
            'launch_designer',
            'starts again after a quit forced in its aboutToQuit',
            'Designer started in' in t and 'ERROR' not in t,
            t,
        )

        # wait_s is respected: 7 s in the window's close handler, then 7 s in an aboutToQuit handler, left to finish; a
        # force, if any, only after the whole wait (REVIEW.md TST-289)
        slow_close = os.path.join(scratch, 'slow_close_finished')
        slow_marker = os.path.join(scratch, 'slow_shutdown_finished')
        await designer_script(c, 'lifecycle/quit_slow_shutdown', slow_close=slow_close, slow_marker=slow_marker)
        step = watch.step()
        quitting = own_pid()  # the process this quit is about
        t = text(await c('quit_designer', {'wait_s': 40}))
        finished = os.path.exists(slow_close) and os.path.exists(slow_marker)
        waited = re.search(r'quit after (\d+)s', t)
        whole_wait = 'forced' not in t or (waited is not None and int(waited.group(1)) >= 40)
        watch.check(
            step,
            'quit_designer',
            'a slow shutdown within its wait is left to finish',
            finished and normal_close(t, 'a slow shutdown within its wait') and whole_wait and has_ended(quitting),
            '%s; both handlers finished: %s' % (t, finished),
        )
        t = text(await c('launch_designer', {'wait_s': 240}))
        check('launch_designer', 'starts again after a slow quit', 'Designer started in' in t and 'ERROR' not in t, t)

        # the realistic blocker: a modal dialog (its own event loop) must not stop quitting
        await designer_script(c, 'lifecycle/modal_dialog')
        time.sleep(1)
        modal = text(
            await c(
                'execute_designer_code',
                {
                    'code': dedent("""\
                        from PySide6.QtWidgets import QApplication
                        print('MODAL=' + type(QApplication.instance().activeModalWidget()).__name__)""")
                },
            )
        )
        step = watch.step()
        t = text(await c('quit_designer', {'wait_s': 30}))
        gone = (await c('designer_status')).is_error
        watch.check(
            step,
            'quit_designer',
            'closes the Designer it started, with a modal dialog open, without a crash',
            'MODAL=QMessageBox' in modal
            and normal_close(t, 'closes the Designer it started, with a modal dialog open')
            and gone,
            modal + t,
        )
