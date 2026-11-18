"""tests/test_all_tools/common.py's crash_dumps: a Designer launch_designer starts on macOS writes its crash dumps in a
home of its own (CFFIXED_USER_HOME), so the checks that no dump appeared look there as well as in the user's."""

import importlib
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, NoReturn, Unpack, cast

import pytest

from conftest import SELFTEST_DIR, RunOptions

if TYPE_CHECKING:  # for the checker only: each test imports crash_watch.py afresh (_crash_watch())
    from test_all_tools.crash_watch import CrashWatch

DUMPS = 'Library/Application Support/Adobe/Adobe Substance 3D Designer/Sentry-Crashpad/completed'
PENDING = DUMPS.replace('/completed', '/pending')  # Crashpad's reports waiting for their upload


def _common() -> ModuleType:  # a module imported by name: PyCharm can't see its names
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    return importlib.import_module('test_all_tools.common')


def _crash_watch() -> ModuleType:
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


def _users_folders(common: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
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
        self.handler_until: float | None = None  # a crash handler runs until then; None: none runs
        self.befores: list[set[str]] = []  # the dumps known before, as each wait's look was given them

    def find(self, ports: Sequence[int] = ()) -> set[str]:
        """As common.crash_dumps(ports): the user's folder, the run's own Designer's home (PORT) and those of `ports`."""
        return {d for d, (_, port) in self.written.items() if port is None or port == _common().PORT or port in ports}

    def write(self, path: str, port: int | None = None) -> None:
        self.written[path] = (self.now, port)

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.now += s
        for when, path, port in [c for c in self.coming if c[0] <= self.now]:
            self.written[path] = (when, port)
            self.coming.remove((when, path, port))

    def may_come(self, ports: Sequence[int], before: set[str]) -> bool:
        """A crash handler still runs (one, until `handler_until`, for every home: common.dumps_may_come looks for each
        port's) and no dump new since `before` is in a Designer's home, the run's own or one of `ports`. A dump in the
        user's folder doesn't end it (REVIEW.md TST-437, TST-448)."""
        self.befores.append(before)
        running = self.handler_until is not None and self.now < self.handler_until
        homes = {d for d, (_, port) in self.written.items() if port is not None and port in (_common().PORT, *ports)}
        return running and not (homes - before)

    def watch(self, common: ModuleType) -> 'CrashWatch':
        return cast(
            'CrashWatch',
            _crash_watch().CrashWatch(
                find=self.find,
                clock=lambda: self.now,
                sleep=self.sleep,
                mtime=lambda d: self.written[d][0],
                coming=self.may_come,
            ),
        )


def _results(common: ModuleType, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, bool, str]]:
    seen: list[tuple[str, str, bool, str]] = []
    monkeypatch.setitem(vars(common), 'check', lambda tool, name, ok, detail='': seen.append((tool, name, ok, detail)))
    return seen


def test_crash_watch_waits_once_at_the_end_and_records_each_check(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-151: it slept 10 s whatever happened; it waits while a crash handler runs with no dump yet, every
    # POLL_S (a quit: the handler ends with its Designer, measured)
    common, dumps = _common(), _Dumps()
    seen = _results(common, monkeypatch)
    watch = dumps.watch(common)
    for n in range(3):
        step = watch.step()
        dumps.now += 30  # the quit, and the launch after it
        watch.check(step, 'quit_designer', 'quit %d, without a crash' % n, n != 1, 'detail %d' % n)
    assert seen == []  # recorded once the wait is over, not before
    dumps.handler_until = dumps.now + 0.35
    watch.settle()
    assert dumps.sleeps == [_common().POLL_S] * 4
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
    # in the run's own Designer's home: the wait ends only on a dump there (REVIEW.md TST-437)
    dumps.coming.append((dumps.now + 3, '/run/late.dmp', _common().PORT))
    dumps.handler_until = float('inf')  # a crash: Adobe's crash window keeps the handler, measured
    watch.settle()
    assert [(name, ok) for _, name, ok, _ in seen] == [('last', False)]
    assert '/run/late.dmp' in seen[0][3]
    assert 2.9 < sum(dumps.sleeps) < 3.2, 'until the dump came, not the limit'


def test_crash_watch_gives_up_at_its_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    common, dumps = _common(), _Dumps()
    _results(common, monkeypatch)
    watch = dumps.watch(common)
    watch.step()
    dumps.handler_until = float('inf')  # no dump ever comes
    watch.settle()
    assert watch.wait_s <= sum(dumps.sleeps) < watch.wait_s + 0.2


def test_crash_watch_looks_with_the_dumps_known_before_every_step(monkeypatch: pytest.MonkeyPatch) -> None:
    common, dumps = _common(), _Dumps()
    _results(common, monkeypatch)
    dumps.write('/dumps/old.dmp')
    watch = dumps.watch(common)
    watch.step()
    # REVIEW.md TST-437: in the home of the Designer only the next step looks at, there before that step; one in the
    # user's folder, which every step looks at, left the union untested
    dumps.write('/other/mid.dmp', port=9902)
    watch.step(ports=[9902])
    dumps.handler_until = dumps.now + 0.05
    watch.settle()
    assert dumps.befores and dumps.befores[0] == {'/dumps/old.dmp', '/other/mid.dmp'}


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
    dumps.handler_until = dumps.now + 0.05
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


def test_a_watch_with_no_time_to_wait_never_looks_whether_a_dump_may_come(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-458: settle looked before its deadline, so a watch given no wait (the unit tests' fakes) still ran
    # dumps_may_come once: the real one lists the crash handlers and the real crash-dump folders
    common, dumps = _common(), _Dumps()
    _results(common, monkeypatch)
    looked: list[Sequence[int]] = []

    def coming(ports: Sequence[int], before: set[str]) -> bool:
        looked.append(ports)
        return True

    watch = _crash_watch().CrashWatch(
        wait_s=0, find=dumps.find, clock=lambda: dumps.now, sleep=dumps.sleep, coming=coming
    )
    watch.check(watch.step(ports=[9901]), 'quit_designer', 'a quit', True)
    watch.settle()
    assert looked == [] and dumps.sleeps == []


def test_watching_crashes_shares_the_categorys_watch_and_settles_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """A check run alone (a scratch run) settles its own watch at its end; inside lifecycle.run it uses the category's,
    settled once at the category's end."""
    common = _common()
    settled: list[CrashWatch] = []  # each watch settled
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
    settled: list[CrashWatch] = []  # each watch settled
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


def test_a_dump_may_come_while_its_designers_crash_handler_runs_and_none_is_there(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-151, measured 2026-11-15: at a quit Designer's crash handler ends with it; after a crash the dump is
    # written as Adobe's crash window opens, and the handler runs as long as that window does. HOME isn't redirected:
    # crash_dumps reads the user's own folder too, and the filter that ignores it isn't tested here (REVIEW.md TST-448)
    common = _common()
    monkeypatch.setitem(vars(common), 'SHORT_TEMP', str(tmp_path))
    home = os.path.join(common.agent_folder(9902), 'home')
    handler = '41576 /Applications/Designer.app/Contents/MacOS/crashpad_handler --no-rate-limit --database=%s/%s' % (
        home,
        'Library/Application Support/Adobe/Adobe Substance 3D Designer/Sentry-Crashpad',
    )
    lines: list[str] = []
    monkeypatch.setitem(vars(common), 'crash_handlers', lambda: list(lines))
    assert common.dumps_may_come([9902], set(), run_port=False) is False  # no handler: its Designer is gone
    lines.append(handler)
    assert common.dumps_may_come([9902], set(), run_port=False) is True
    assert common.dumps_may_come([9903], set(), run_port=False) is False, "another Designer's handler"
    os.makedirs(os.path.join(home, DUMPS))
    Path(home, DUMPS, 'a.dmp').write_text('')
    assert common.dumps_may_come([9902], set(), run_port=False) is False, 'its dump is there'
    known = common.crash_dumps([9902], run_port=False)
    assert common.dumps_may_come([9902], known, run_port=False) is True, 'a dump from before is no new one'


def test_a_dump_may_come_from_the_runs_own_designer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md TST-437: no test passed run_port=True, which the crash watch uses. HOME isn't redirected: the filter
    # that ignores the user's own folder isn't tested here (REVIEW.md TST-448)
    common = _common()
    monkeypatch.setitem(vars(common), 'SHORT_TEMP', str(tmp_path))
    home = os.path.join(common.agent_folder(common.PORT), 'home')
    handler = '41576 /A/crashpad_handler --no-rate-limit --database=%s/Sentry-Crashpad' % home
    monkeypatch.setitem(vars(common), 'crash_handlers', lambda: [handler])
    assert common.dumps_may_come([], set()) is True
    assert common.dumps_may_come([], set(), run_port=False) is False


@pytest.mark.parametrize(
    'code, read',
    [(0, ['41576 /A/crashpad_handler --database=/x']), (1, []), (2, None), (3, None)],
    ids=['handlers found', 'none found', 'a syntax error', 'a fatal error'],
)
def test_a_failing_pgrep_reads_as_handlers_unknown_not_as_none_running(
    monkeypatch: pytest.MonkeyPatch, code: int, read: list[str] | None
) -> None:
    # REVIEW.md TST-447: pgrep's return code wasn't read, so a failing pgrep's empty output read as no crash handler,
    # and the crash waits ended at once. pgrep exits 1 when nothing matches, 2 or 3 on its own errors
    common = _common()
    monkeypatch.setattr(sys, 'platform', 'darwin')
    out = '41576 /A/crashpad_handler --database=/x\n' if code == 0 else ''
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: SimpleNamespace(returncode=code, stdout=out))
    assert common.crash_handlers() == read


def test_a_pgrep_that_cant_run_reads_as_handlers_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    common = _common()
    monkeypatch.setattr(sys, 'platform', 'darwin')

    def cant(cmd: list[str], **kw: Unpack[RunOptions]) -> NoReturn:
        raise OSError('no pgrep')

    monkeypatch.setattr(subprocess, 'run', cant)
    assert common.crash_handlers() is None


def test_a_dump_may_come_while_the_crash_handlers_cant_be_listed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md TST-447: the waits go on to their limit, as where nothing is known
    common = _common()
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setitem(vars(common), 'SHORT_TEMP', str(tmp_path))
    monkeypatch.setitem(vars(common), 'crash_handlers', lambda: None)
    assert common.dumps_may_come([9902], set(), run_port=False) is True
