"""tests/test_all_tools/common.py's crash_dumps: a Designer launch_designer starts on macOS writes its crash dumps in a
home of its own (CFFIXED_USER_HOME), so the checks that no dump appeared look there as well as in the user's."""

import importlib
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from conftest import SELFTEST_DIR

DUMPS = 'Library/Application Support/Adobe/Adobe Substance 3D Designer/Sentry-Crashpad/completed'
PENDING = DUMPS.replace('/completed', '/pending')  # Crashpad's reports waiting for their upload


def _common() -> Any:  # a module imported by name: PyCharm can't see its names
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    return importlib.import_module('test_all_tools.common')


def _crash_watch() -> Any:
    """crash_watch.py, which looks common's check and crash_dumps up when it calls them."""
    _common()
    return importlib.import_module('test_all_tools.crash_watch')


pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='no os.getuid there, and no agent folders')


def test_crash_dumps_include_those_of_the_runs_own_designers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    common = _common()
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setenv('HOME', str(tmp_path / 'user'))
    monkeypatch.setitem(vars(common), 'SHORT_TEMP', str(tmp_path))
    monkeypatch.setitem(vars(common), 'PORT', 9901)  # the run's
    users = tmp_path / 'user' / DUMPS
    runs = tmp_path / ('sd_mcp_%d_9901' % os.getuid()) / 'home' / DUMPS
    # another run's, side by side (REVIEW.md TST-155): its crash isn't this run's, unless this run names its port
    beside = tmp_path / ('sd_mcp_%d_9902' % os.getuid()) / 'home' / DUMPS
    others = tmp_path / 'sd_mcp_0_9901' / 'home' / DUMPS  # another user's: not this run's
    for folder in (users, runs, beside, others):
        folder.mkdir(parents=True)
        (folder / 'a.dmp').write_text('')
    assert common.crash_dumps() == {str(users / 'a.dmp'), str(runs / 'a.dmp')}
    assert common.crash_dumps(ports=[9902]) == {str(users / 'a.dmp'), str(runs / 'a.dmp'), str(beside / 'a.dmp')}
    # the pool's parent has no Designer on PORT: another run's may be there (REVIEW.md TST-280)
    assert common.crash_dumps(ports=[9902], run_port=False) == {str(users / 'a.dmp'), str(beside / 'a.dmp')}
    (beside / 'b.dmp').write_text('')
    assert common.new_crash_dumps(common.crash_dumps(), wait_s=0) == set()
    assert common.new_crash_dumps(set(), wait_s=0, ports=[9902]) >= {str(beside / 'b.dmp')}


def _users_folders(common: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    """The user's pending/ and completed/, made, with no Designer of the run's own."""
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setenv('HOME', str(tmp_path / 'user'))
    monkeypatch.setitem(vars(common), 'SHORT_TEMP', str(tmp_path))
    pending, completed = tmp_path / 'user' / PENDING, tmp_path / 'user' / DUMPS
    pending.mkdir(parents=True)
    completed.mkdir(parents=True)
    return pending, completed


def test_crash_dumps_include_reports_waiting_for_their_upload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-351: a finished report waits in pending/ until its upload is done or skipped; a failed one stays
    common = _common()
    pending, _ = _users_folders(common, monkeypatch, tmp_path)
    (pending / 'a.dmp').write_text('')
    assert common.crash_dumps() == {str(pending / 'a.dmp')}


def test_a_report_uploaded_meanwhile_is_no_new_crash_dump(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-351: the user's Designer crashed just before; its report, uploaded during the step, moves to
    # completed/: the same report, not a crash of the step's
    common = _common()
    pending, completed = _users_folders(common, monkeypatch, tmp_path)
    (pending / 'a.dmp').write_text('')
    before = common.crash_dumps()
    (pending / 'a.dmp').rename(completed / 'a.dmp')
    assert common.new_crash_dumps(before, wait_s=0) == set()
    (pending / 'b.dmp').write_text('')
    assert common.new_crash_dumps(before, wait_s=0) == {str(pending / 'b.dmp')}


class _Dumps:
    """Crash dumps by path: the time each is written and the port whose home holds it (None: the user's), on a clock
    that only sleeping moves."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.written: dict[str, tuple[float, int | None]] = {}
        self.sleeps: list[float] = []
        self.coming: list[tuple[float, str, int | None]] = []  # written once the clock reaches the time

    def find(self, ports: Any = ()) -> set[str]:
        return {d for d, (_, port) in self.written.items() if port is None or port in ports}

    def write(self, path: str, port: int | None = None) -> None:
        self.written[path] = (self.now, port)

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.now += s
        for when, path, port in [c for c in self.coming if c[0] <= self.now]:
            self.written[path] = (when, port)
            self.coming.remove((when, path, port))

    def watch(self, common: Any) -> Any:
        return _crash_watch().CrashWatch(
            find=self.find, clock=lambda: self.now, sleep=self.sleep, mtime=lambda d: self.written[d][0]
        )


def _results(common: Any, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, bool, str]]:
    seen: list[tuple[str, str, bool, str]] = []
    monkeypatch.setitem(vars(common), 'check', lambda tool, name, ok, detail='': seen.append((tool, name, ok, detail)))
    return seen


def test_crash_watch_waits_once_at_the_end_and_records_each_check(monkeypatch: pytest.MonkeyPatch) -> None:
    common, dumps = _common(), _Dumps()
    seen = _results(common, monkeypatch)
    watch = dumps.watch(common)
    for n in range(3):
        step = watch.step()
        dumps.now += 30  # the quit, and the launch after it
        watch.check(step, 'quit_designer', 'quit %d, without a crash' % n, n != 1, 'detail %d' % n)
    assert seen == []  # recorded once the wait is over, not before
    watch.settle()
    assert dumps.sleeps == [10]
    assert [(name, ok) for _, name, ok, _ in seen] == [
        ('quit 0, without a crash', True),
        ('quit 1, without a crash', False),  # failing on its own, no dump needed
        ('quit 2, without a crash', True),
    ]
    assert seen[0][3] == 'detail 0'


def test_crash_watch_gives_a_dump_to_the_step_it_appeared_in(monkeypatch: pytest.MonkeyPatch) -> None:
    common, dumps = _common(), _Dumps()
    seen = _results(common, monkeypatch)
    watch = dumps.watch(common)
    first = watch.step()
    dumps.now += 30
    watch.check(first, 'quit_designer', 'first', True)
    second = watch.step()
    dumps.now += 5
    dumps.write('/dumps/a.dmp')  # a few seconds into the second step, while the first's checks were long done
    dumps.now += 25
    watch.check(second, 'quit_designer', 'second', True)
    watch.check(second, 'quit_designer', 'second, another check', True)
    third = watch.step()
    dumps.now += 30
    watch.check(third, 'quit_designer', 'third', True)
    watch.settle()
    assert [(name, ok) for _, name, ok, _ in seen] == [
        ('first', True),
        ('second', False),
        ('second, another check', False),
        ('third', True),
    ]
    assert '/dumps/a.dmp' in seen[1][3]


def test_crash_watch_counts_a_dump_appearing_late(monkeypatch: pytest.MonkeyPatch) -> None:
    """Written a few seconds after the last quit, during the one wait (REVIEW.md TST-21: about 3 s after a crash)."""
    common, dumps = _common(), _Dumps()
    seen = _results(common, monkeypatch)
    watch = dumps.watch(common)
    step = watch.step()
    dumps.now += 30
    watch.check(step, 'quit_designer', 'last', True)
    dumps.coming.append((dumps.now + 3, '/dumps/late.dmp', None))
    watch.settle()
    assert [(name, ok) for _, name, ok, _ in seen] == [('last', False)]
    assert '/dumps/late.dmp' in seen[0][3]


def test_crash_watch_gives_a_dump_only_to_steps_looking_at_its_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    """A dump in the home of the Designer on another port belongs to the step about that one, though written later."""
    common, dumps = _common(), _Dumps()
    seen = _results(common, monkeypatch)
    watch = dumps.watch(common)
    other = watch.step(ports=[9902])
    dumps.now += 30
    watch.check(other, 'quit_designer', 'other port', True)
    mine = watch.step()
    dumps.now += 5
    dumps.write('/other/a.dmp', port=9902)
    dumps.now += 25
    watch.check(mine, 'quit_designer', 'this port', True)
    watch.settle()
    assert [(name, ok) for _, name, ok, _ in seen] == [('other port', False), ('this port', True)]


def test_crash_watch_ignores_dumps_there_before_a_step(monkeypatch: pytest.MonkeyPatch) -> None:
    common, dumps = _common(), _Dumps()
    seen = _results(common, monkeypatch)
    dumps.write('/dumps/old.dmp')
    watch = dumps.watch(common)
    dumps.now += 1
    step = watch.step()
    dumps.now += 30
    watch.check(step, 'quit_designer', 'quit', True)
    watch.settle()
    assert seen == [('quit_designer', 'quit', True, '')]


def test_crash_watch_runs_its_clean_ups_after_the_wait_and_the_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    """A clean-up deleting a Designer's home unless it holds a dump runs after the wait: run at once, it would delete
    a dump written late, and the crash with it."""
    common, dumps = _common(), _Dumps()
    seen = _results(common, monkeypatch)
    order: list[str] = []
    watch = dumps.watch(common)
    step = watch.step()
    watch.check(step, 'quit_designer', 'quit', True)
    watch.later(lambda: order.append('clean-up after %d sleep(s), %d check(s)' % (len(dumps.sleeps), len(seen))))
    assert order == []
    watch.settle()
    assert order == ['clean-up after 1 sleep(s), 1 check(s)']


def test_crash_watch_with_no_step_does_not_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    common, dumps = _common(), _Dumps()
    _results(common, monkeypatch)
    ran: list[bool] = []
    watch = dumps.watch(common)
    watch.later(lambda: ran.append(True))
    watch.settle()
    assert dumps.sleeps == [] and ran == [True]


def test_watching_crashes_shares_the_categorys_watch_and_settles_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """A check run alone (a scratch run) settles its own watch at its end; inside lifecycle.run it uses the category's,
    settled once at the category's end."""
    common = _common()
    settled: list[object] = []
    monkeypatch.setattr(_crash_watch().CrashWatch, 'settle', lambda self: settled.append(self))
    ctx = common.Ctx(c=None, s=None, scratch='', helper_source='', was_running=False)
    with _crash_watch().watching_crashes(ctx) as outer:
        with _crash_watch().watching_crashes(ctx) as inner:
            assert inner is outer
        assert settled == []
    assert settled == [outer]
    assert ctx.crash_watch is None
    with _crash_watch().watching_crashes(ctx) as alone:  # a check alone: a watch of its own
        assert alone is not outer
    assert settled == [outer, alone]


def test_watching_crashes_settles_when_a_check_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    common = _common()
    settled: list[object] = []
    monkeypatch.setattr(_crash_watch().CrashWatch, 'settle', lambda self: settled.append(self))
    ctx = common.Ctx(c=None, s=None, scratch='', helper_source='', was_running=False)
    with pytest.raises(RuntimeError), _crash_watch().watching_crashes(ctx):
        raise RuntimeError('a check failed')
    assert len(settled) == 1 and ctx.crash_watch is None


def test_crash_watch_reports_a_dump_of_a_step_whose_checks_never_ran(monkeypatch: pytest.MonkeyPatch) -> None:
    """A check that stopped early (its launch failed, say) recorded nothing for its step: a dump given to that step
    still fails a check, rather than none."""
    common, dumps = _common(), _Dumps()
    seen = _results(common, monkeypatch)
    watch = dumps.watch(common)
    watch.step(ports=[9902])  # its check returned before recording anything
    dumps.now += 5
    dumps.write('/other/a.dmp', port=9902)
    watch.settle()
    assert [(tool, ok) for tool, _, ok, _ in seen] == [('self-test', False)]
    assert '/other/a.dmp' in seen[0][3]


def test_crash_watch_takes_no_report_uploaded_meanwhile_for_a_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-351: there before the step, waiting for its upload, then moved to completed/ during it
    common, dumps = _common(), _Dumps()
    seen = _results(common, monkeypatch)
    dumps.write('/user/Sentry-Crashpad/pending/a.dmp')
    watch = dumps.watch(common)
    step = watch.step()
    dumps.now += 5
    del dumps.written['/user/Sentry-Crashpad/pending/a.dmp']
    dumps.write('/user/Sentry-Crashpad/completed/a.dmp')
    watch.check(step, 'quit_designer', 'quit', True)
    watch.settle()
    assert [(name, ok) for _, name, ok, _ in seen] == [('quit', True)]
