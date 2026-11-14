"""Designer's preferences plist (`com.adobe.Adobe Substance 3D Designer`), which every Designer of the user's account
shares on macOS, saved as the first Designer an agent starts is started and put back once none runs (ROADMAP item 67).
Used by the server's launch_designer and quit_designer (server_tools/lifecycle.py), uninstall.py and the self-test's
pool (tests/test_all_tools/workers.py), so it runs on the system Python too.

Measured 2026-11-13, macOS 26. No way to give a Designer a file of its own was found: `defaults write` with
CFFIXED_USER_HOME (which launch_designer sets) wrote to the real `~/Library/Preferences`, with
`__CFPREFERENCES_AVOID_DAEMON=1` added too. Agents' Designers did change the user's file: a full self-test run added 122
keys (`session.graph.thumbnail_mode.*`) and changed `session.modes.mixer.areas`, a probe's floated 3D view dock reached
the next Designer, and a Designer writes its `session.instancePID` there as it starts (lifecycle's hand-over check reads
it).

So saved(), around the start of a Designer an agent starts: the file exported (`defaults export`) into saved_file(),
unless a copy is there already (another agent's Designer runs, whose end puts it back), the lock held until the process
is started (and recorded: launch_designer), so that no put-back runs in between. An empty export of a file that holds
settings is refused: an unreadable file exports as an empty one, exit 0 (measured), and a put-back from it would delete
every key. A copy the user's Designer has run since is made again from the file as it is (a start goes ahead only with
the user's Designer closed). A copy made for a start that then fails is removed, as no Designer started on it (one made
again is kept: a Designer was running as it was made). put_back(), once no Designer runs: the keys added since deleted,
then the copy imported if a value differs (an import alone merges: a key added stays, measured), and the file read back:
equal to the copy, as measured on a scratch domain of nested and typed values; about 7 ms a key deleted. It looks for a
Designer started meanwhile every RECHECK_EVERY deletes and before the import, and stops, the copy kept, saying how far
it got. Never while a Designer runs (the user's would write the file again as it quits; an agent's isn't done), nor once
the user's Designer has run since the copy was made, their log (which agents' Designers, with homes of their own, never
write) newer than it: the copy is dropped then and the file left as it is, theirs. A copy left by Designers that ended
outside the tools is put back by the next call that finds none running, only if younger than LEFTOVER_HOURS, as the user
may have worked since with no log to show it; older, it is dropped (so is one whose put-back failed: only a call that
has just ended a Designer puts back an older one). A copy that can't be opened is kept (the cause may pass); one that
isn't a plist of keys is removed; one that can't be removed is given up (_give_up), never put back. A domain never
written exports as an empty one (measured). Written only through `defaults`, never directly: cfprefsd keeps the domain
in memory and writes it back. The copy is the user's alone (mode 0600), beside the records of the Designers an agent
started, in the home folder, so a restart doesn't lose it. Tests: tests/unit/test_designer_preferences.py, and the
pool's end check (workers.check_the_preferences), which compares the file with what the run's last quit should leave.
"""

from __future__ import annotations

import contextlib
import glob
import os
import plistlib
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from typing import IO

import project_constants

DOMAIN = 'com.adobe.Adobe Substance 3D Designer'
DEFAULTS = '/usr/bin/defaults'
# A copy no Designer just ended for (left by ones that ended outside the tools) is put back only this young: older, the
# user may have worked since with no log to show it (the user's choice: DECISIONS.md, Bridge and quitting)
LEFTOVER_HOURS = 6
RECHECK_EVERY = 50  # deletes between two looks for a Designer started meanwhile
# why a put-back stops at one: running() is also True when Designers can't be listed (REVIEW.md SRV-145)
STARTED = "a Designer started meanwhile, or Designers couldn't be listed"


class PreferencesError(Exception):
    """`defaults` failed, or what it printed isn't a plist of keys."""


def run_defaults(*args: str) -> bytes:
    """macOS's `defaults` with `args`, what it printed; PreferencesError when it can't run or fails."""
    try:
        done = subprocess.run([DEFAULTS, *args], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise PreferencesError('defaults %s: %s' % (args[0], e)) from e
    if done.returncode != 0:
        said = done.stderr.decode('utf-8', 'replace').strip().splitlines()
        raise PreferencesError(
            'defaults %s: exit code %d%s' % (args[0], done.returncode, ': ' + said[-1] if said else '')
        )
    return done.stdout


def saved_file() -> str:
    """The copy of the file a launch saved, while one is kept."""
    return os.path.join(project_constants.AGENT_RECORD_DIR, '.%s_preferences.plist' % project_constants.PLUGIN)


def lock_file() -> str:
    """Held while the copy is made, read or put back, and while a Designer an agent starts is started; it also holds
    the time of a copy that couldn't be removed (_give_up)."""
    return os.path.join(project_constants.AGENT_RECORD_DIR, '.%s_preferences.lock' % project_constants.PLUGIN)


def plist_file() -> str:
    """The file itself, only read here: whether it holds settings when `defaults` reads none."""
    return os.path.join(os.path.expanduser('~'), 'Library', 'Preferences', '%s.plist' % DOMAIN)


def users_data_dir() -> str:
    """The user's Designer's folder on macOS, its log in it (the server's `_designer_data_dir()`, a unit test checks)."""
    return os.path.join(
        os.path.expanduser('~'), 'Library', 'Application Support', 'Adobe', 'Adobe Substance 3D Designer'
    )


def users_log_time() -> float:
    """When the user's Designer last wrote its log, of any version; 0 if it never did."""
    times = [0.0]
    for log in glob.glob(os.path.join(glob.escape(users_data_dir()), '*', 'log.txt')):
        with contextlib.suppress(OSError):
            times.append(os.path.getmtime(log))
    return max(times)


def _keys(data: bytes) -> dict[str, object]:
    try:
        read = plistlib.loads(data)
    except Exception as e:  # plistlib raises several kinds on what isn't a plist
        raise PreferencesError("what was read isn't a plist of keys (%s)" % e) from e
    if not isinstance(read, dict):
        raise PreferencesError("what was read isn't a plist of keys (a %s)" % type(read).__name__)
    return read


def current() -> dict[str, object]:
    """The file's keys and values, as `defaults` reads them."""
    return _keys(run_defaults('export', DOMAIN, '-'))


def _file_holds_settings() -> bool:
    """Whether the file itself holds any setting: True when it is there but can't be read (as if it did)."""
    try:
        with open(plist_file(), 'rb') as f:
            data = f.read()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    try:
        return bool(plistlib.loads(data))
    except Exception:  # not a plist: something is there
        return bool(data)


def _lock() -> IO[str]:
    """The lock, held until the file returned is closed; OSError when it can't be opened."""
    import fcntl  # POSIX: only reached on macOS

    lock = open(lock_file(), 'a', encoding='utf-8')  # noqa: SIM115  (closed by its callers, which hold it till then)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
    except OSError:
        lock.close()
        raise
    return lock


@contextlib.contextmanager
def saved(
    running: Callable[[], bool], *, ended: bool, check: Callable[[str], None] = lambda said: None
) -> Iterator[str]:
    """Around the start of a Designer an agent starts, which goes ahead only with the user's Designer closed
    (launch_designer refuses otherwise): a copy of the file kept unless one is (running() says whether a Designer runs,
    True when that can't be told; `ended`, whether this call has just ended one, as put_back's). A copy the user's
    Designer has run since (a Designer runs now: an agent's, or the user's just starting, which the launch then refuses)
    is made again from the file as it is. Yields what to say: a copy left behind put back first or dropped, the file
    saved again, or not saved (the start goes on, but its Designer's changes may stay); '' otherwise. check(what is to
    be said) runs under the lock before the start, and may raise to stop it (launch_designer's _appeared); not without
    the lock, which nothing then waits for. A copy made here, not again, is removed when the start raises. Nothing off
    macOS."""
    if sys.platform != 'darwin':
        yield ''
        return
    try:
        lock = _lock()
    except OSError as e:  # may not: a copy kept for another agent's Designer puts this one's back too (SRV-143)
        yield _not_saved(e, 'may not')
        return
    try:
        said: list[str] = [_put_back_or_say(running, ended)]
        made = _made()
        none = made is None or _given_up(made)  # one given up is no one's: saved over (REVIEW.md SRV-137)
        again = not none and made is not None and _users_ran_since(made)
        fresh = False
        if none or again:
            try:
                _save()
                fresh = none
                if again:
                    said.append(
                        "Designer's preferences saved again: the user's Designer ran since the last copy, so what the "
                        'file holds now is kept.'
                    )
            except (PreferencesError, OSError) as e:
                said.append(_not_saved(e))
        try:
            text = ' '.join(part for part in said if part)
            # under the lock, which a launch holds until its Designer is recorded or ended (REVIEW.md SRV-141, SRV-144)
            check(text)
            yield text
        except BaseException:
            if fresh:  # the start failed: no Designer started on it, nor any to put it back (REVIEW.md SRV-138)
                _dropped('')
            raise
    finally:
        lock.close()  # which lets the lock go


def _made() -> float | None:
    """When the copy was made, or None without one."""
    try:
        return os.path.getmtime(saved_file())
    except OSError:
        return None


def _users_ran_since(made: float) -> bool:
    """Whether the user's Designer has run since the copy was made: a put-back drops it then, a start makes it again."""
    return users_log_time() > made


def kept_copy() -> dict[str, object] | None:
    """The keys of the copy kept, what the put-back after the last agent's Designer has quit restores: None without one
    (removed as it is read too, by a put-back elsewhere: REVIEW.md TST-372), with one given up (_give_up), or once the
    user's Designer has run since it was made (dropped then, or made again by the next start). PreferencesError or
    OSError when it can't be read."""
    made = _made()
    if made is None or _given_up(made) or _users_ran_since(made):
        return None
    try:
        with open(saved_file(), 'rb') as f:
            return _keys(f.read())
    except FileNotFoundError:
        return None


def _not_saved(error: Exception, will: str = "won't") -> str:
    # said in errors too, where none was started (REVIEW.md SRV-145)
    return (
        "Designer's preferences couldn't be saved first (%s): if a Designer is started now, its changes to them %s "
        'be put back.' % (error, will)
    )


def _save() -> None:
    data = run_defaults('export', DOMAIN, '-')
    if not _keys(data) and _file_holds_settings():  # an unreadable file exports as empty, exit 0 (measured)
        raise PreferencesError('the file reads as empty, but holds settings')
    new = saved_file() + '.new'
    with contextlib.suppress(FileNotFoundError):
        os.remove(new)  # one a save cut short left: open(..., O_EXCL) below would refuse it
    fd = os.open(new, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # the user's settings: theirs alone
    with os.fdopen(fd, 'wb') as f:
        f.write(data)
    os.replace(new, saved_file())  # whole or not at all: a copy cut short would read as unreadable


def put_back(running: Callable[[], bool], *, ended: bool) -> str:
    """Once no Designer runs (running() False), the file as the copy has it, the copy then removed. `ended`: a
    Designer an agent started has just ended through the tools (quit_designer); otherwise the copy was left by ones that
    ended outside them, or by a put-back that failed, and is put back only if younger than LEFTOVER_HOURS. What to say:
    put back; left as it is (the user's Designer ran since, or the copy too old: the copy dropped); or couldn't be (the
    copy kept for the next call, how far it got said; or dropped when it isn't a plist of keys); '' when nothing was
    kept or changed, or a Designer runs. A copy given up (_give_up) is only removed, whenever it can be. Nothing off
    macOS."""
    if sys.platform != 'darwin' or not os.path.exists(saved_file()):
        return ''
    try:
        lock = _lock()
    except OSError as e:
        return _not_put_back(e)
    try:
        return _put_back_or_say(running, ended)
    finally:
        lock.close()


def _put_back_or_say(running: Callable[[], bool], ended: bool) -> str:
    try:
        return _put_back(running, ended)
    except OSError as e:
        return _not_put_back(e)


def _not_put_back(error: Exception, how_far: str = '') -> str:
    return "Designer's preferences couldn't be put back (%s)%s: their copy is kept, in %s." % (
        error,
        how_far,
        saved_file(),
    )


def _put_back(running: Callable[[], bool], ended: bool) -> str:
    path = saved_file()
    made = _made()
    if made is None:
        return ''
    if _given_up(made):  # no one's: removed now, or said again; never put back (REVIEW.md SRV-137)
        return _dropped('')
    if running():
        return ''
    if _users_ran_since(made):
        return _dropped(
            "Designer's preferences left as they are: the user's Designer ran since their copy was made, so it was "
            'dropped.'
        )
    if not ended and time.time() - made > LEFTOVER_HOURS * 3600:
        return _dropped(
            "Designer's preferences left as they are: their copy is over %d hours old and this call ended no Designer, "
            'so it was dropped: the user may have worked since.' % LEFTOVER_HOURS
        )
    with open(path, 'rb') as f:  # an OSError keeps it: the cause may pass (EMFILE), and too old, it is dropped unread
        data = f.read()
    try:
        before = _keys(data)
    except PreferencesError as e:  # what it holds: it never will be read; given up if it can't be removed (SRV-142)
        return _dropped(
            "Designer's preferences couldn't be put back: their copy could not be read (%s), so it was dropped." % e
        )
    added: list[str] = []
    changed: list[str] = []
    removed, imported = 0, False
    try:
        now = current()
        added = sorted(set(now) - set(before))
        changed = [key for key in before if key not in now or now[key] != before[key]]
        if not added and not changed:
            return _dropped('')
        for key in added:
            if removed and removed % RECHECK_EVERY == 0 and running():
                raise PreferencesError(STARTED)
            run_defaults('delete', DOMAIN, key)
            removed += 1
        if changed:  # with none, the file is as the copy now (REVIEW.md SRV-140)
            if running():  # it would read a half-restored file, and the import overwrite what it writes as it starts
                raise PreferencesError(STARTED)
            run_defaults('import', DOMAIN, path)
            imported = True
        if current() != before:
            raise PreferencesError('it reads back otherwise than the copy')
    except PreferencesError as e:  # how far it got: the file may be half-way (REVIEW.md SRV-133, SRV-140)
        how_far = ''
        if imported:
            what = 'the keys added since were removed and their copy imported' if added else 'their copy was imported'
            how_far = ', after ' + what
        elif removed and removed == len(added) and not changed:  # nothing was left to put back (REVIEW.md SRV-143)
            how_far = ', after the keys added since were removed'
        elif removed:
            how_far = ', only partly: %d of %s added since removed, no value put back yet' % (
                removed,
                _count(len(added), 'key'),
            )
        return _not_put_back(e, how_far)
    done = [_count(len(added), 'key') + ' added since removed'] if added else []
    done += [_count(len(changed), 'value') + ' put back'] if changed else []
    # from their copy, no more: one made again after the user's Designer ran holds agents' changes from before it
    return _dropped("Designer's preferences put back from their copy: %s." % ' and '.join(done))


def _dropped(said: str) -> str:
    """`said`, once the copy is removed: what was done to the file stands if it can't be, and the next call tries
    again, the copy given up meanwhile (_give_up)."""
    try:
        os.remove(saved_file())
    except FileNotFoundError:
        pass
    except OSError as e:
        said += " The copy of Designer's preferences %s couldn't be removed (%s): it is tried again next time%s." % (
            saved_file(),
            e,
            _give_up(),
        )
    return said.strip()


def _give_up() -> str:
    """The copy, which couldn't be removed, given up: its time written in the lock file, which is there already (a
    folder that can't be written doesn't stop it) and isn't the copy (nor does a flag on the copy). A copy given up is no
    one's (_given_up): never put back, saved over by the next start, removed by the next call that can. Otherwise a copy
    dropped as too old would be the next session's, put back by its quit however old (REVIEW.md SRV-137). What to add
    to the sentence."""
    try:
        made = os.path.getmtime(saved_file())
        with open(lock_file(), 'w', encoding='utf-8') as f:
            f.write(repr(made))
    except OSError:
        return ''
    return ', and never put back'


def _given_up(made: float) -> bool:
    """Whether the copy made at `made` was given up (_give_up)."""
    try:
        with open(lock_file(), encoding='utf-8') as f:
            return f.read() == repr(made)
    except OSError:
        return False


def _count(n: int, what: str) -> str:
    return '%d %s%s' % (n, what, '' if n == 1 else 's')
