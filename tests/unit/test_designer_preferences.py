"""designer_preferences.py: Designer's preferences plist, which every Designer shares, saved as the first Designer an
agent starts is started and put back once none runs (ROADMAP item 67). `defaults` is conftest's fake (FakeDefaults: what
the real one does, as measured), the user's Designer's data folder and plist file the test's. The plist is macOS's:
the tests of what is done with it run there (REVIEW.md TST-356); those of nothing done elsewhere run everywhere."""

import errno
import os
import plistlib
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import IO, NoReturn

import pytest
from fake_defaults import FakeDefaults, lock_held

import designer_preferences as prefs
from conftest import REAL_RUN_DEFAULTS, REAL_USERS_DATA_DIR, server

MACOS = pytest.mark.skipif(sys.platform != 'darwin', reason='the preferences plist is macOS only')

BEFORE: dict[str, object] = {
    'session.mainWindow.state': b'\x00\x01layout',
    'session.modes.mixer.areas': {'left': [1, 2], 'size': 2.5},
    'session.lastSession.files': ['/Users/me/brick.sbs'],
}

NONE_RUNS = lambda: False  # noqa: E731
ONE_RUNS = lambda: True  # noqa: E731


def _a_designer_changes(defaults: FakeDefaults) -> None:
    """Changes of every kind a put-back undoes: a value changed, a key removed, two added."""
    defaults.domain['session.mainWindow.state'] = b'\x00\x02floating'
    del defaults.domain['session.lastSession.files']
    defaults.domain['session.instancePID'] = 4242
    defaults.domain['session.graph.thumbnail_mode.tmp.mcp_selftest·sbs.1'] = 1


def _saved(defaults: FakeDefaults, running: Callable[[], bool] = NONE_RUNS, ended: bool = False) -> str:
    """A save around a start, as launch_designer makes one: what it says."""
    with prefs.saved(running, ended=ended) as said:
        assert said is not None
    return said


def _the_users_designer_ran(defaults: FakeDefaults, at: float) -> None:
    log = defaults.users_data / '16.0' / 'log.txt'
    log.parent.mkdir(exist_ok=True)
    log.write_text('[INFO] the user opened Designer\n')
    os.utime(log, (at, at))


def _copy_made(seconds_ago: float) -> None:
    """The copy as if made `seconds_ago`."""
    at = time.time() - seconds_ago
    os.utime(prefs.saved_file(), (at, at))


def _copy() -> dict[str, object]:
    with open(prefs.saved_file(), 'rb') as f:
        read: dict[str, object] = plistlib.load(f)
    return read


@MACOS
def test_a_save_then_a_put_back_once_none_runs_leaves_the_file_as_it_was(defaults: FakeDefaults) -> None:
    defaults.domain = dict(BEFORE)
    assert _saved(defaults) == ''
    assert _copy() == BEFORE, 'the copy is the file as it was'
    _a_designer_changes(defaults)
    said = prefs.put_back(NONE_RUNS, ended=True)
    assert defaults.domain == BEFORE, 'the keys added deleted: an import alone merges (measured)'
    assert not os.path.exists(prefs.saved_file()), 'the copy is gone once put back'
    # from their copy, no more: one made again after the user's Designer ran holds agents' changes from before it
    # (REVIEW.md SRV-133, SRV-140)
    assert (
        said == "Designer's preferences put back from their copy: 2 keys added since removed and 2 values put back."
    ), said


@MACOS
def test_a_put_back_says_only_what_it_did(defaults: FakeDefaults) -> None:
    # one value changed, nothing added, as in a pool run of the bridge category (its end check: "1 value changed
    # (session.modes.mixer.areas), 0 keys added")
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    defaults.domain['session.modes.mixer.areas'] = {'left': [3]}
    said = prefs.put_back(NONE_RUNS, ended=True)
    assert said.endswith('from their copy: 1 value put back.'), said


@MACOS
def test_the_copy_is_the_users_alone(defaults: FakeDefaults) -> None:
    # it holds the user's settings: their last files, their layout
    _saved(defaults)
    assert os.stat(prefs.saved_file()).st_mode & 0o777 == 0o600


@MACOS
def test_nothing_is_put_back_while_a_designer_runs(defaults: FakeDefaults) -> None:
    # the user's would write its own as it quits; an agent's isn't done, and its own end puts the file back
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    changed = dict(defaults.domain)
    assert prefs.put_back(ONE_RUNS, ended=True) == ''
    assert defaults.domain == changed and os.path.exists(prefs.saved_file()), 'left for the last one to end'
    prefs.put_back(NONE_RUNS, ended=True)
    assert defaults.domain == BEFORE


@MACOS
def test_a_designer_started_while_another_runs_keeps_the_first_copy(defaults: FakeDefaults) -> None:
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    assert _saved(defaults, running=ONE_RUNS) == ''
    assert _copy() == BEFORE, "the first, from before any agent's Designer"
    prefs.put_back(NONE_RUNS, ended=True)
    assert defaults.domain == BEFORE


@MACOS
def test_once_the_users_designer_ran_the_copy_is_dropped_and_their_file_left(defaults: FakeDefaults) -> None:
    # their log, which agents' Designers don't write, is newer than the copy: what the file holds may be theirs
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    changed = dict(defaults.domain)
    _the_users_designer_ran(defaults, os.path.getmtime(prefs.saved_file()) + 5)
    said = prefs.put_back(NONE_RUNS, ended=True)
    assert defaults.domain == changed and 'delete' not in defaults.verbs() and 'import' not in defaults.verbs()
    assert not os.path.exists(prefs.saved_file())
    assert said == (
        "Designer's preferences left as they are: the user's Designer ran since their copy was made, so it was dropped."
    ), said


@MACOS
def test_a_users_log_older_than_the_copy_changes_nothing(defaults: FakeDefaults) -> None:
    defaults.domain = dict(BEFORE)
    _the_users_designer_ran(defaults, time.time() - 3600)
    _saved(defaults)
    _a_designer_changes(defaults)
    prefs.put_back(NONE_RUNS, ended=True)
    assert defaults.domain == BEFORE


@MACOS
def test_a_file_left_as_it_was_is_not_written(defaults: FakeDefaults) -> None:
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    assert prefs.put_back(NONE_RUNS, ended=True) == ''
    assert defaults.verbs() == ['export', 'export'], 'read twice, never written'
    assert not os.path.exists(prefs.saved_file())


@MACOS
def test_a_copy_left_by_designers_ended_outside_the_tools_is_put_back_before_the_next_start(
    defaults: FakeDefaults,
) -> None:
    # one crashed, or was ended outside quit_designer: nothing put it back, and none runs now
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    with prefs.saved(NONE_RUNS, ended=False) as said:
        assert defaults.domain == BEFORE, 'put back before the next one starts'
        assert _copy() == BEFORE, 'and saved again for it'
    assert said.startswith("Designer's preferences put back from their copy"), said


@MACOS
def test_a_put_back_that_fails_keeps_the_copy_and_says_where(defaults: FakeDefaults) -> None:
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    defaults.fail['import'] = 'the disk is full'
    said = prefs.put_back(NONE_RUNS, ended=True)
    assert os.path.exists(prefs.saved_file())
    # the keys added were removed first: the file is half-way (REVIEW.md SRV-133)
    assert said == (
        "Designer's preferences couldn't be put back (the disk is full), only partly: 2 of 2 keys added since removed, "
        'no value put back yet: their copy is kept, in %s.' % prefs.saved_file()
    ), said
    del defaults.fail['import']
    prefs.put_back(NONE_RUNS, ended=True)
    assert defaults.domain == BEFORE, 'the next put-back finishes it'


@MACOS
@pytest.mark.parametrize('verb', ['export', 'delete'])
def test_a_put_back_whose_read_or_delete_fails_keeps_the_copy(defaults: FakeDefaults, verb: str) -> None:
    # REVIEW.md TST-358
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    defaults.fail[verb] = 'defaults %s: exit code 1' % verb
    said = prefs.put_back(NONE_RUNS, ended=True)
    assert os.path.exists(prefs.saved_file()), said
    # the file's read or the first delete failed: nothing done, nothing more said
    assert said.startswith(
        "Designer's preferences couldn't be put back (defaults %s: exit code 1): their copy" % verb
    ), said


@MACOS
def test_a_put_back_that_reads_back_otherwise_keeps_the_copy(defaults: FakeDefaults) -> None:
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    defaults.lossy = True
    said = prefs.put_back(NONE_RUNS, ended=True)
    assert "couldn't be put back (it reads back otherwise than the copy)" in said and os.path.exists(
        prefs.saved_file()
    ), said


@MACOS
def test_a_save_that_fails_says_so_and_the_start_goes_on(defaults: FakeDefaults) -> None:
    defaults.fail['export'] = 'defaults export: exit code 1'
    started = []
    with prefs.saved(NONE_RUNS, ended=False) as said:
        started.append(True)
    assert started and not os.path.exists(prefs.saved_file())
    assert said == (
        "Designer's preferences couldn't be saved first (defaults export: exit code 1): if a Designer is started now, "
        "its changes to them won't be put back."
    ), said


@MACOS
def test_an_export_that_isnt_a_plist_is_not_saved(defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-358: a copy that can't be read later would only be dropped
    monkeypatch.setitem(vars(prefs), 'run_defaults', lambda *args: b'not a plist')
    said = _saved(defaults)
    assert not os.path.exists(prefs.saved_file()) and said.startswith(
        "Designer's preferences couldn't be saved first (what was read isn't a plist of keys"
    ), said


@MACOS
@pytest.mark.parametrize('file', ['holding settings', 'unreadable'])
def test_an_empty_read_of_a_file_holding_settings_is_not_saved(defaults: FakeDefaults, file: str) -> None:
    # REVIEW.md SRV-126: an unreadable plist exports as an empty one, exit 0 (measured); saved so, a put-back would delete
    # every key of the user's file once it reads again
    defaults.domain = {}
    with open(defaults.plist, 'wb') as f:
        plistlib.dump(BEFORE, f)
    if file == 'unreadable':
        os.chmod(defaults.plist, 0)
    try:
        said = _saved(defaults)
    finally:
        os.chmod(defaults.plist, 0o600)
    assert not os.path.exists(prefs.saved_file())
    assert said == (
        "Designer's preferences couldn't be saved first (the file reads as empty, but holds settings): if a Designer "
        "is started now, its changes to them won't be put back."
    ), said


@MACOS
@pytest.mark.parametrize('file', ['none', 'empty'])
def test_an_empty_read_of_a_file_holding_none_is_saved(defaults: FakeDefaults, file: str) -> None:
    # a Designer never run here: what an agent's adds is deleted again
    if file == 'empty':
        with open(defaults.plist, 'wb') as f:
            plistlib.dump({}, f)
    assert _saved(defaults) == '' and _copy() == {}
    defaults.domain['session.mainWindow.state'] = b'an agent'
    prefs.put_back(NONE_RUNS, ended=True)
    assert defaults.domain == {}


@MACOS
def test_a_save_cut_short_leaves_nothing_in_the_next_ones_way(defaults: FakeDefaults) -> None:
    # REVIEW.md TST-358
    defaults.domain = dict(BEFORE)
    Path(prefs.saved_file() + '.new').write_bytes(b'half')
    assert _saved(defaults) == '' and _copy() == BEFORE
    assert not os.path.exists(prefs.saved_file() + '.new')


@MACOS
def test_a_start_says_both_a_put_back_and_a_save_that_failed(
    defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md TST-358: a copy left behind put back, then the fresh save failing
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    exports: list[int] = []

    def third_export_fails(*args: str) -> bytes:
        if args[0] == 'export':
            exports.append(1)
            if len(exports) == 3:  # the put-back reads twice, then the save
                raise prefs.PreferencesError('defaults export: exit code 1')
        return defaults(*args)

    monkeypatch.setitem(vars(prefs), 'run_defaults', third_export_fails)
    said = _saved(defaults)
    assert said.startswith("Designer's preferences put back from their copy"), said
    assert said.endswith(
        "Designer's preferences couldn't be saved first (defaults export: exit code 1): if a Designer is started now, "
        "its changes to them won't be put back."
    ), said


@MACOS
def test_a_copy_that_cant_be_read_is_removed_and_said(defaults: FakeDefaults) -> None:
    defaults.domain = dict(BEFORE)
    Path(prefs.saved_file()).write_bytes(b'not a plist')
    said = prefs.put_back(NONE_RUNS, ended=True)
    assert defaults.domain == BEFORE and not os.path.exists(prefs.saved_file())
    assert said.startswith("Designer's preferences couldn't be put back: their copy could not be read"), said
    assert 'could not be read' in said and 'dropped' in said, said


@MACOS
def test_a_copy_that_cant_be_opened_now_is_kept(defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-134: out of file descriptors in the long-running server, for one: the copy may read next time, and
    # removed, the next launch would save the agents' changes as the user's file
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    changed = dict(defaults.domain)

    def opening(file: str, mode: str = 'r', encoding: str | None = None) -> object:
        if file == prefs.saved_file():
            raise OSError(errno.EMFILE, 'Too many open files')
        return open(file, mode, encoding=encoding)

    monkeypatch.setitem(vars(prefs), 'open', opening)  # the module's own name, before the builtin
    said = prefs.put_back(NONE_RUNS, ended=True)
    assert os.path.exists(prefs.saved_file()) and defaults.domain == changed, said
    assert said == (
        "Designer's preferences couldn't be put back ([Errno 24] Too many open files): their copy is kept, in %s."
        % prefs.saved_file()
    ), said
    monkeypatch.delitem(vars(prefs), 'open')
    prefs.put_back(NONE_RUNS, ended=True)
    assert defaults.domain == BEFORE, 'put back by the next call'


@MACOS
def test_a_lock_that_cant_be_opened_is_said(defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-358: the home folder read-only, for one
    def no_lock() -> NoReturn:
        raise PermissionError(13, 'Permission denied')

    monkeypatch.setitem(vars(prefs), '_lock', no_lock)
    # a copy kept for another agent's Designer is put back with what this one changes, when the lock opens then
    # (REVIEW.md SRV-143)
    assert _saved(defaults) == (
        "Designer's preferences couldn't be saved first ([Errno 13] Permission denied): if a Designer is started now, "
        'its changes to them may not be put back.'
    )
    Path(prefs.saved_file()).write_bytes(plistlib.dumps(BEFORE))
    said = prefs.put_back(NONE_RUNS, ended=True)
    assert said.startswith("Designer's preferences couldn't be put back ([Errno 13] Permission denied)"), said


@MACOS
@pytest.mark.parametrize('how', ['put back', 'dropped'])
def test_a_copy_that_cant_be_removed_doesnt_unsay_what_was_done(
    defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch, how: str
) -> None:
    # REVIEW.md SRV-128: the file was put back (or left as the user's); only the copy stays, for the next call
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    if how == 'dropped':
        _the_users_designer_ran(defaults, os.path.getmtime(prefs.saved_file()) + 5)
    real = os.remove

    def remove(path: str) -> None:
        if path == prefs.saved_file():
            raise PermissionError(1, 'Operation not permitted')
        real(path)

    monkeypatch.setattr(os, 'remove', remove)
    said = prefs.put_back(NONE_RUNS, ended=True)
    done = (
        'put back from their copy: 2 keys added since removed and 2 values put back.'
        if how == 'put back'
        else "left as they are: the user's Designer ran since"
    )
    assert said.startswith("Designer's preferences " + done), said
    # tried again, not certain to work: a lasting cause fails each time (REVIEW.md TST-371); done with, whatever the
    # next call's `ended` (SRV-137)
    assert said.endswith(
        " The copy of Designer's preferences %s couldn't be removed ([Errno 1] Operation not permitted): it is tried"
        ' again next time, and never put back.' % prefs.saved_file()
    ), said
    monkeypatch.setattr(os, 'remove', real)
    prefs.put_back(NONE_RUNS, ended=True)
    assert not os.path.exists(prefs.saved_file()), 'removed by the next call'


@MACOS
def test_a_designer_starting_during_a_put_back_stops_it_and_keeps_the_copy(defaults: FakeDefaults) -> None:
    # REVIEW.md SRV-127: it would read a half-restored file, and the import would overwrite what it writes as it starts
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    said = prefs.put_back(lambda: 'delete' in defaults.verbs(), ended=True)  # one starts once the deletes begin
    assert 'import' not in defaults.verbs() and os.path.exists(prefs.saved_file())
    assert said == (
        "Designer's preferences couldn't be put back (a Designer started meanwhile, or Designers couldn't be listed), "
        'only partly: 2 of 2 keys added since removed, no value put back yet: their copy is kept, in %s.'
        % prefs.saved_file()
    ), said


@MACOS
def test_a_designer_starting_during_many_deletes_stops_them_soon(defaults: FakeDefaults) -> None:
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    defaults.domain.update({'session.graph.thumbnail_mode.%d' % i: 1 for i in range(3 * prefs.RECHECK_EVERY)})
    said = prefs.put_back(lambda: 'delete' in defaults.verbs(), ended=True)
    assert defaults.verbs().count('delete') == prefs.RECHECK_EVERY, 'asked again every RECHECK_EVERY deletes'
    # how far it got: the file is half-way (REVIEW.md SRV-133)
    assert (
        ', only partly: %d of %d keys added since removed, no value put back yet: '
        % (
            prefs.RECHECK_EVERY,
            3 * prefs.RECHECK_EVERY,
        )
        in said
    ), said


@MACOS
@pytest.mark.parametrize('hours', [prefs.LEFTOVER_HOURS - 1, prefs.LEFTOVER_HOURS + 0.9])
def test_a_copy_left_behind_is_put_back_only_within_its_hours(defaults: FakeDefaults, hours: float) -> None:
    # REVIEW.md SRV-125: no Designer just ended through the tools, and the user's log may be gone: an old copy would
    # revert the user's own changes since
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    changed = dict(defaults.domain)
    _copy_made(hours * 3600)
    said = prefs.put_back(NONE_RUNS, ended=False)
    assert not os.path.exists(prefs.saved_file())
    if hours < prefs.LEFTOVER_HOURS:
        assert defaults.domain == BEFORE and said.startswith("Designer's preferences put back"), said
    else:
        assert defaults.domain == changed and 'delete' not in defaults.verbs(), said
        # no cause it can't know: a put-back that failed after a quit is retried so too; and 6.9 hours is over 6, not
        # "6 hours old" (REVIEW.md SRV-133)
        assert said == (
            "Designer's preferences left as they are: their copy is over %d hours old and this call ended no "
            'Designer, so it was dropped: the user may have worked since.' % prefs.LEFTOVER_HOURS
        ), said


@MACOS
def test_an_old_copy_is_put_back_right_after_its_designer_ended(defaults: FakeDefaults) -> None:
    # an agent's long session: its Designer just ended through the tools
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    _copy_made((prefs.LEFTOVER_HOURS + 5) * 3600)
    prefs.put_back(NONE_RUNS, ended=True)
    assert defaults.domain == BEFORE


@MACOS
@pytest.mark.parametrize('ended', [True, False], ids=['after an end', 'after none'])
def test_a_start_puts_back_an_old_copy_only_right_after_an_end(defaults: FakeDefaults, ended: bool) -> None:
    # REVIEW.md TST-368: saved() passes `ended` on to its put-back: launch_designer's, when it has just ended a hung
    # Designer, whose changes are fresh however old the copy; otherwise a copy past LEFTOVER_HOURS is dropped
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    changed = dict(defaults.domain)
    _copy_made((prefs.LEFTOVER_HOURS + 1) * 3600)
    said = _saved(defaults, ended=ended)
    assert _copy() == (BEFORE if ended else changed), said
    done = 'put back' if ended else 'left as they are'
    assert said.startswith("Designer's preferences " + done), said


@MACOS
def test_the_copy_kept_is_what_a_put_back_restores(defaults: FakeDefaults) -> None:
    # REVIEW.md TST-367: the pool's end check compares the file with it
    assert prefs.kept_copy() is None, 'none kept'
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    assert prefs.kept_copy() == BEFORE
    _the_users_designer_ran(defaults, os.path.getmtime(prefs.saved_file()) + 5)
    assert prefs.kept_copy() is None, "the user's Designer ran since: dropped, or made again by the next start"


@MACOS
def test_a_kept_copy_that_isnt_a_plist_of_keys_is_refused(defaults: FakeDefaults) -> None:
    # REVIEW.md SRV-136: read as the put-back reads it, not taken as one whatever it holds
    Path(prefs.saved_file()).write_bytes(plistlib.dumps([1, 2]))
    with pytest.raises(prefs.PreferencesError, match="isn't a plist of keys"):
        prefs.kept_copy()


@MACOS
def test_a_copy_removed_as_it_is_read_counts_as_none(defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-372: a put-back elsewhere removing it between the look and the read: no copy, not an unreadable one
    defaults.domain = dict(BEFORE)
    _saved(defaults)

    def opening(file: str, mode: str = 'r', encoding: str | None = None) -> object:
        if file == prefs.saved_file():
            raise FileNotFoundError(errno.ENOENT, 'No such file or directory')
        return open(file, mode, encoding=encoding)

    monkeypatch.setitem(vars(prefs), 'open', opening)  # the module's own name, before the builtin
    assert prefs.kept_copy() is None


@MACOS
@pytest.mark.parametrize('replaced', [True, False], ids=['replaced', 'not even replaced'])
def test_a_copy_a_drop_couldnt_remove_is_never_put_back(
    defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch, replaced: bool
) -> None:
    # REVIEW.md SRV-137: dropped as too old but still there, it would be the next session's copy, which that session's
    # quit puts back however old (ended=True): over what the user did since with no log to show it
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    changed = dict(defaults.domain)
    _copy_made((prefs.LEFTOVER_HOURS + 1) * 3600)
    remove, replace = os.remove, os.replace

    def removing(path: str) -> None:  # an immutable flag, the folder's permissions: a lasting cause
        if path == prefs.saved_file():
            raise PermissionError(1, 'Operation not permitted')
        remove(path)

    def replacing(source: str, path: str) -> None:
        if path == prefs.saved_file():
            raise PermissionError(1, 'Operation not permitted')
        replace(source, path)

    monkeypatch.setattr(os, 'remove', removing)
    if not replaced:
        monkeypatch.setattr(os, 'replace', replacing)
    said = _saved(defaults)  # the next launch, with none running
    assert 'is over %d hours old' % prefs.LEFTOVER_HOURS in said and "couldn't be removed" in said, said
    assert prefs.kept_copy() == (changed if replaced else None), 'what the next put-back restores: %s' % said
    defaults.domain['session.instancePID'] = 5151  # the Designer that launch started
    said = prefs.put_back(NONE_RUNS, ended=True)  # and its quit
    assert defaults.domain == (changed if replaced else {**changed, 'session.instancePID': 5151})
    # whose copy, with nothing said before it (REVIEW.md SRV-143)
    removing_said = "The copy of Designer's preferences %s couldn't be removed" % prefs.saved_file()
    assert replaced or said.startswith(removing_said), said


@MACOS
@pytest.mark.parametrize('made', ['now', 'again'])
def test_a_start_that_fails_removes_only_a_copy_it_made(defaults: FakeDefaults, made: str) -> None:
    # REVIEW.md SRV-138: no Designer started on a copy made now, and none would put it back: as if never made. One made
    # again is the copy of the Designer that runs, whose quit puts it back.
    defaults.domain = dict(BEFORE)
    running = NONE_RUNS
    if made == 'again':
        _saved(defaults)
        _the_users_designer_ran(defaults, os.path.getmtime(prefs.saved_file()) + 5)
        running = ONE_RUNS
    with pytest.raises(PermissionError), prefs.saved(running, ended=False):
        assert os.path.exists(prefs.saved_file())
        raise PermissionError(13, 'Permission denied')  # Designer's process couldn't be started
    assert os.path.exists(prefs.saved_file()) == (made == 'again')


@MACOS
def test_a_put_back_failing_after_its_import_says_how_far_it_got(
    defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md SRV-140: the read-back failing, once the keys added were removed and the copy imported, is no failure
    # before anything was done
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)

    def read_back_fails(*args: str) -> bytes:
        if args[0] == 'export' and 'import' in defaults.verbs():
            raise prefs.PreferencesError('defaults export: exit code 1')
        return defaults(*args)

    monkeypatch.setitem(vars(prefs), 'run_defaults', read_back_fails)
    said = prefs.put_back(NONE_RUNS, ended=True)
    assert os.path.exists(prefs.saved_file()), said
    assert said == (
        "Designer's preferences couldn't be put back (defaults export: exit code 1), after the keys added since were "
        'removed and their copy imported: their copy is kept, in %s.' % prefs.saved_file()
    ), said


@MACOS
def test_a_put_back_with_nothing_left_to_put_back_says_so_when_its_read_back_fails(
    defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md SRV-143: every key added removed and no value to put back: not "only partly"
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    defaults.domain['session.instancePID'] = 4242
    defaults.domain['session.graph.thumbnail_mode.1'] = 1

    def read_back_fails(*args: str) -> bytes:
        if args[0] == 'export' and 'delete' in defaults.verbs():
            raise prefs.PreferencesError('defaults export: exit code 1')
        return defaults(*args)

    monkeypatch.setitem(vars(prefs), 'run_defaults', read_back_fails)
    said = prefs.put_back(NONE_RUNS, ended=True)
    assert said == (
        "Designer's preferences couldn't be put back (defaults export: exit code 1), after the keys added since were "
        'removed: their copy is kept, in %s.' % prefs.saved_file()
    ), said


@MACOS
def test_a_copy_that_cant_be_read_nor_removed_is_given_up(
    defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md SRV-142: kept, it would never be put back nor saved over, and every later line would say it is kept
    defaults.domain = dict(BEFORE)
    Path(prefs.saved_file()).write_bytes(b'not a plist')
    remove = os.remove

    def removing(path: str) -> None:  # an immutable flag, the folder's permissions (SRV-137)
        if path == prefs.saved_file():
            raise PermissionError(1, 'Operation not permitted')
        remove(path)

    monkeypatch.setattr(os, 'remove', removing)
    said = prefs.put_back(NONE_RUNS, ended=True)
    assert said.startswith("Designer's preferences couldn't be put back: their copy could not be read"), said
    assert said.endswith(
        "couldn't be removed ([Errno 1] Operation not permitted): it is tried again next time, and never put back."
    ), said
    assert prefs.kept_copy() is None
    _saved(defaults)  # the next launch saves over it
    assert prefs.kept_copy() == BEFORE


@MACOS
def test_a_put_back_with_no_value_to_put_back_imports_nothing(defaults: FakeDefaults) -> None:
    # REVIEW.md SRV-140: once the keys added are removed the file is as the copy; a Designer starting then stops nothing,
    # where "only partly: 2 of 2" was said
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    defaults.domain['session.instancePID'] = 4242
    defaults.domain['session.graph.thumbnail_mode.1'] = 1
    said = prefs.put_back(lambda: 'delete' in defaults.verbs(), ended=True)  # one starts once the deletes begin
    assert defaults.domain == BEFORE and 'import' not in defaults.verbs(), said
    assert not os.path.exists(prefs.saved_file()), said
    assert said == "Designer's preferences put back from their copy: 2 keys added since removed.", said


@MACOS
def test_a_start_after_the_users_designer_ran_saves_the_file_again(defaults: FakeDefaults) -> None:
    # REVIEW.md SRV-131: the copy could only be dropped now, and later agents' changes would stay; a start goes ahead
    # only with the user's Designer closed (launch_designer), so the file as it is holds their run
    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _copy_made(60)
    defaults.domain['session.instancePID'] = 4242  # agent A, still running
    _the_users_designer_ran(defaults, os.path.getmtime(prefs.saved_file()) + 5)
    defaults.domain['session.mainWindow.state'] = b"the user's new layout"
    now = dict(defaults.domain)
    said = _saved(defaults, running=ONE_RUNS)  # agent B starts, A running
    assert _copy() == now
    assert said == (
        "Designer's preferences saved again: the user's Designer ran since the last copy, so what the file holds now "
        'is kept.'
    ), said
    defaults.domain['session.graph.thumbnail_mode.B'] = 1
    prefs.put_back(NONE_RUNS, ended=True)
    assert defaults.domain == now, "B's change undone, the user's kept"


@MACOS
def test_a_start_holds_the_copy_until_its_designer_is_started(defaults: FakeDefaults) -> None:
    # no put-back between the save and the process starting: it would find none running and drop the copy, and that
    # Designer's changes would stay
    with prefs.saved(NONE_RUNS, ended=False):
        assert lock_held()
    assert not lock_held()


@MACOS
def test_a_put_back_waits_for_a_start_in_progress(defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-477: it waited 0.3 s for the put-back to block, and a thread slower than that passed with no lock at
    # all; the put-back's thread now says when it meets the start's lock, and the test waits for that
    import fcntl

    defaults.domain = dict(BEFORE)
    _saved(defaults)
    _a_designer_changes(defaults)
    running: list[bool] = []
    done: list[str] = []
    blocked = threading.Event()
    flock = fcntl.flock

    def met(fd: int | IO[str], operation: int) -> None:  # the lock taken, saying first when it is held elsewhere
        if operation == fcntl.LOCK_EX:
            try:
                flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                blocked.set()
        flock(fd, operation)

    monkeypatch.setattr(fcntl, 'flock', met)
    with prefs.saved(lambda: bool(running), ended=False):  # a start in progress: what it changes is put back at its end
        waiting = threading.Thread(target=lambda: done.append(prefs.put_back(lambda: bool(running), ended=True)))
        waiting.start()
        assert blocked.wait(10) and not done, 'waits for the start'  # 10 s: a limit, the lock met at once
        running.append(True)  # the one started
    waiting.join(10)
    assert done == [''] and os.path.exists(prefs.saved_file()), 'it found the new one running'


def test_off_macos_nothing_is_saved_or_put_back(defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'platform', 'win32')
    assert _saved(defaults) == '' and prefs.put_back(NONE_RUNS, ended=True) == ''
    assert not defaults.calls and not os.path.exists(prefs.saved_file())


def test_off_macos_a_copy_left_is_not_put_back(defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-358: the copy there, so only the platform stops it
    Path(prefs.saved_file()).write_bytes(plistlib.dumps(BEFORE))
    defaults.domain = {'session.instancePID': 1}
    monkeypatch.setattr(sys, 'platform', 'win32')
    assert prefs.put_back(NONE_RUNS, ended=False) == '' and not defaults.calls


@MACOS
def test_the_users_log_time_is_their_newest_log(defaults: FakeDefaults) -> None:
    assert prefs.users_log_time() == 0.0, 'none: never ran'
    _the_users_designer_ran(defaults, 1000.0)
    older = defaults.users_data / '15.0' / 'log.txt'
    older.parent.mkdir()
    older.write_text('x')
    os.utime(older, (500.0, 500.0))
    assert prefs.users_log_time() == 1000.0


@MACOS
def test_the_users_data_folder_is_the_one_the_server_reads_their_log_in() -> None:
    assert REAL_USERS_DATA_DIR() == server._designer_data_dir()


@MACOS
def test_defaults_failing_raises_its_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # the real runner, on a program that isn't defaults: never the real one here, which reads the user's file
    monkeypatch.setitem(vars(prefs), 'DEFAULTS', '/usr/bin/false')
    with pytest.raises(prefs.PreferencesError, match=r'defaults export: exit code 1'):
        REAL_RUN_DEFAULTS('export', prefs.DOMAIN, '-')
    monkeypatch.setitem(vars(prefs), 'DEFAULTS', '/no/such/defaults')
    with pytest.raises(prefs.PreferencesError, match=r'defaults export: .*No such file'):
        REAL_RUN_DEFAULTS('export', prefs.DOMAIN, '-')


def test_no_unit_test_reaches_the_real_defaults(defaults: FakeDefaults) -> None:
    # REVIEW.md TST-360: the runner is the fake, and a call that bypassed it would find no program
    assert prefs.run_defaults is defaults
    assert not os.path.exists(prefs.DEFAULTS) and prefs.DEFAULTS != '/usr/bin/defaults'
    with pytest.raises(prefs.PreferencesError):
        REAL_RUN_DEFAULTS('export', prefs.DOMAIN, '-')


@MACOS
def test_current_reads_the_domain_and_refuses_what_isnt_one(
    defaults: FakeDefaults, monkeypatch: pytest.MonkeyPatch
) -> None:
    defaults.domain = dict(BEFORE)
    assert prefs.current() == BEFORE
    for printed in (plistlib.dumps([1, 2]), b'not a plist'):
        monkeypatch.setitem(vars(prefs), 'run_defaults', lambda *args, out=printed: out)
        with pytest.raises(prefs.PreferencesError, match="isn't a plist of keys"):
            prefs.current()
