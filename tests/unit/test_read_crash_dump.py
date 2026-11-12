"""scripts/read_crash_dump.py: what a crash dump of Designer's says, read without a minidump parser (none at hand reads
macOS arm64 ones): the exception, the messages Crashpad kept, the crashing thread's frames through its frame pointers,
the first one outside the system's libraries, and Designer's log as it crashed; on synthetic dumps (minidumps.py)."""

import contextlib
import glob
import importlib.util
import os
import re
import signal
import struct
import subprocess
import sys
import time
import tracemalloc
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from minidumps import (
    AMD64,
    CPU_ARM64,
    DESIGNER,
    EXC_CRASH,
    KERNEL,
    LIBC,
    QTCORE,
    STACK,
    WINDOWS,
    Crash,
    Module,
    an_abort,
    frames,
    macho,
    minidump,
)

from conftest import ROOT

SCRIPT = os.path.join(ROOT, 'scripts', 'read_crash_dump.py')


def _reader() -> Any:  # a script, loaded from its file: PyCharm can't see its names
    spec = importlib.util.spec_from_file_location('read_crash_dump', SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DATA = ('Library', 'Application Support', 'Adobe', 'Adobe Substance 3D Designer')
BUILD, OTHER_BUILD = bytes(range(16)), bytes(range(16, 32))  # two builds' UUIDs


def _dump(tmp_path: Path, crash: Crash | None = None, name: str = 'a1b2.dmp', part: str = 'completed') -> Path:
    path = tmp_path / 'Sentry-Crashpad' / part / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(minidump(crash or an_abort()))
    return path


def _said(path: Path, **kw: Any) -> str:
    return '\n'.join(_reader().describe(str(path), **kw))


def test_the_crashing_threads_frames_follow_its_frame_pointers(tmp_path: Path) -> None:
    said = _said(_dump(tmp_path), name_frames=lambda path, base, addresses: [])
    expected = [
        '0  libsystem_kernel.dylib +0x95e8',
        '1  libsystem_c.dylib +0x78978',  # the link register: the leaf's caller
        '2  QtCore +0xfd94c',  # its signing bits dropped
        '3  Adobe Substance 3D Designer +0x1234',
    ]
    at = [said.find(line) for line in expected]
    assert -1 not in at and at == sorted(at), said
    assert '4  ' not in said, 'the chain ends at a frame pointer of 0'


def test_the_first_frame_outside_the_systems_libraries_is_named(tmp_path: Path) -> None:
    said = _said(_dump(tmp_path), name_frames=lambda path, base, addresses: [])
    assert "first frame outside the system's libraries: #2 QtCore +0xfd94c" in said


def test_an_abort_is_said_with_its_signal(tmp_path: Path) -> None:
    said = _said(_dump(tmp_path), name_frames=lambda path, base, addresses: [])
    assert 'exception: EXC_CRASH, signal SIGABRT' in said


def test_the_messages_crashpad_kept_are_said_with_their_module(tmp_path: Path) -> None:
    crash = an_abort(messages=[(1, 'abort() called'), (2, 'terminating due to uncaught exception')])
    said = _said(_dump(tmp_path, crash), name_frames=lambda path, base, addresses: [])
    assert 'libsystem_c.dylib: abort() called' in said
    assert 'QtCore: terminating due to uncaught exception' in said


def test_frames_in_a_module_on_disk_are_named_by_atos(tmp_path: Path) -> None:
    qtcore = tmp_path / 'QtCore'
    qtcore.write_bytes(macho(BUILD))  # a dump that records no build: named, whatever the file's (REVIEW.md TST-350)
    asked: list[tuple[str, int, list[int]]] = []

    def name_frames(path: str, base: int, addresses: list[int]) -> list[str]:
        asked.append((path, base, addresses))
        return ['QVariant::~QVariant() (in QtCore) + 112']

    crash = an_abort(modules=(KERNEL, LIBC, Module(str(qtcore), QTCORE.base), DESIGNER))
    said = _said(_dump(tmp_path, crash), name_frames=name_frames)
    # only the module on disk outside the system's libraries: those are in the shared cache, where atos names frames
    # wrongly or not at all (libsystem_kernel.dylib is also on disk)
    assert asked == [(str(qtcore), QTCORE.base, [QTCORE.base + 0xFD94C])]
    assert 'QtCore +0xfd94c  QVariant::~QVariant() (in QtCore) + 112' in said


def test_frames_are_said_when_atos_cant_name_them(tmp_path: Path) -> None:
    qtcore = tmp_path / 'QtCore'
    qtcore.write_text('')

    def fails(path: str, base: int, addresses: list[int]) -> list[str]:
        raise OSError('atos: no such file')

    crash = an_abort(modules=(KERNEL, LIBC, Module(str(qtcore), QTCORE.base), DESIGNER))
    assert '2  QtCore +0xfd94c' in _said(_dump(tmp_path, crash), name_frames=fails)


@pytest.mark.parametrize('kw', [{'arch': AMD64}, {'platform': WINDOWS}], ids=['x86_64', 'windows'])
def test_a_dump_of_another_system_is_refused(tmp_path: Path, kw: dict[str, int]) -> None:
    reader = _reader()
    with pytest.raises(reader.CannotRead, match='macOS on arm64'):
        reader.describe(str(_dump(tmp_path, an_abort(**kw))))


def test_a_file_that_isnt_a_minidump_is_refused(tmp_path: Path) -> None:
    path = tmp_path / 'x.dmp'
    path.write_bytes(b'not a dump at all, long enough for a header')
    reader = _reader()
    with pytest.raises(reader.CannotRead, match='not a minidump'):
        reader.describe(str(path))


def test_designers_log_as_it_crashed_ends_the_report_and_its_sentry_event_is_never_said(tmp_path: Path) -> None:
    # the event attached beside it holds the user's Adobe account
    path = _dump(tmp_path, name='a1b2.dmp')
    attachments = tmp_path / 'Sentry-Crashpad' / 'attachments' / 'a1b2'
    attachments.mkdir(parents=True)
    (attachments / 'log.txt').write_text('\n'.join('line %d' % i for i in range(1, 21)) + '\n')
    (attachments / '__sentry-event').write_text('email someone@example.com')
    said = _said(path, name_frames=lambda path, base, addresses: [])
    assert said.index('line 20') > said.index('first frame outside') and 'line 13' in said and 'line 12' not in said
    assert 'someone@example.com' not in said


def test_with_no_path_the_newest_dump_of_any_designer_is_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = _reader()
    # the newest neither the first found nor the last (REVIEW.md TST-347, TST-350)
    older, new, oldest = (_dump(tmp_path / folder, name=folder + '.dmp') for folder in ('older', 'new', 'oldest'))
    os.utime(older, (time.time() - 60, time.time() - 60))
    os.utime(oldest, (time.time() - 120, time.time() - 120))
    monkeypatch.setitem(vars(reader), 'dump_folders', lambda: [str(d.parent) for d in (older, new, oldest)])
    monkeypatch.setitem(vars(reader), '_atos', lambda path, base, addresses: [])
    assert reader.main([]) == 0
    assert capsys.readouterr().out.splitlines()[0] == str(new)


def test_with_no_dump_anywhere_it_says_where_it_looked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = _reader()
    monkeypatch.setitem(vars(reader), 'dump_folders', lambda: [str(tmp_path / 'none')])
    assert reader.main([]) == 1
    assert str(tmp_path / 'none') in capsys.readouterr().err


def _no_names(path: str, base: int, addresses: list[int]) -> list[str]:
    return []


def _home_is(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    """The user's home (`~`) taken to be `home`: HOME alone wouldn't do on Windows, where expanduser reads USERPROFILE
    (REVIEW.md TST-349)."""
    expand = os.path.expanduser
    monkeypatch.setattr(os.path, 'expanduser', lambda path: str(home) if path == '~' else expand(path))


class _TooLong(Exception):
    """Not an OSError (TimeoutError is one), which the code under test may catch."""


@contextlib.contextmanager
def _within(seconds: float) -> Iterator[None]:
    """Raises _TooLong past `seconds` where the system has the alarm signal (not Windows), so a loop that would run on
    doesn't hang the suite."""
    if not hasattr(signal, 'SIGALRM'):
        yield
        return

    def late(number: int, frame: object) -> None:
        raise _TooLong('still running after %s s' % seconds)

    before = signal.signal(signal.SIGALRM, late)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, before)


def _frames_at(said: str, where: str) -> int:
    """How many of the frames said are at `where` (module +offset)."""
    return len(re.findall(r'^ +\d+  %s$' % re.escape(where), said, re.M))


def test_a_recursion_shows_each_of_its_frames(tmp_path: Path) -> None:
    # REVIEW.md INS-28: F calling F, each frame record returning to the same place, showed F once
    ret = QTCORE.base + 0x500
    stack = frames(
        (0x20, STACK + 0x40, ret),
        (0x40, STACK + 0x60, ret),
        (0x60, STACK + 0x80, ret),
        (0x80, STACK + 0xA0, DESIGNER.base + 0x1234),
        (0xA0, 0, 0),
    )
    said = _said(_dump(tmp_path, an_abort(stack=stack)), name_frames=_no_names)
    assert _frames_at(said, 'QtCore +0x500') == 3 and '5  Adobe Substance 3D Designer +0x1234' in said, said


def test_a_return_address_the_link_register_holds_is_said_once(tmp_path: Path) -> None:
    # the crashing function saved the link register in its frame record and called nothing since: the record repeats it
    stack = frames(
        (0x20, STACK + 0x40, LIBC.base + 0x78978), (0x40, STACK + 0x60, DESIGNER.base + 0x1234), (0x60, 0, 0)
    )
    said = _said(_dump(tmp_path, an_abort(stack=stack)), name_frames=_no_names)
    assert _frames_at(said, 'libsystem_c.dylib +0x78978') == 1 and '2  Adobe Substance 3D Designer +0x1234' in said, (
        said
    )


def test_a_frame_record_pointing_to_itself_ends_the_walk(tmp_path: Path) -> None:
    # a corrupt stack: the walk ends there rather than going round (REVIEW.md TST-347)
    stack = frames((0x20, STACK + 0x20, QTCORE.base + 0x500))
    said = _said(_dump(tmp_path, an_abort(stack=stack)), name_frames=_no_names)
    assert _frames_at(said, 'QtCore +0x500') == 1 and '\n   3  ' not in said, said


def test_the_walk_stops_at_its_depth(tmp_path: Path) -> None:
    # a deep recursion: DEPTH frames, the records past them not walked (REVIEW.md INS-28, TST-347)
    reader = _reader()
    stack = frames(*[(0x20 * (i + 1), STACK + 0x20 * (i + 2), QTCORE.base + 0x500) for i in range(100)])
    said = _said(_dump(tmp_path, an_abort(stack=stack)), name_frames=_no_names)
    assert '  %2d  QtCore +0x500' % (reader.DEPTH - 1) in said and '  %2d  ' % reader.DEPTH not in said, said


def test_frame_records_are_read_from_the_dumps_memory_list_too(tmp_path: Path) -> None:
    # a real dump lists more memory than the thread's stack (27 ranges in one read): a record found in its second
    # range, beyond the stack (REVIEW.md TST-347)
    far = STACK + 0x100000
    stack = frames((0x20, far, QTCORE.base + 0x500))
    crash = an_abort(stack=stack, memory=[(STACK - 0x100000, bytes(64)), (far, frames((0, 0, DESIGNER.base + 0x1234)))])
    said = _said(_dump(tmp_path, crash), name_frames=_no_names)
    assert '3  Adobe Substance 3D Designer +0x1234' in said, said


def test_a_crash_from_another_exception_says_which(tmp_path: Path) -> None:
    # REVIEW.md TST-347: the exception's own code, the one the crash came from
    crash = an_abort(params=(EXC_CRASH, 11 << 24, 0), code=1)
    said = _said(_dump(tmp_path, crash), name_frames=_no_names)
    assert 'exception: EXC_CRASH, signal SIGSEGV, from EXC_BAD_ACCESS' in said, said


def test_a_module_name_of_an_odd_length_is_read_still(tmp_path: Path) -> None:
    # REVIEW.md INS-31: it raised UnicodeDecodeError, a traceback instead of the dump
    odd = Module(QTCORE.path, QTCORE.base, name_length=len(QTCORE.path) * 2 - 1)
    said = _said(_dump(tmp_path, an_abort(modules=(KERNEL, LIBC, odd, DESIGNER))), name_frames=_no_names)
    assert '2  QtCor' in said and ' +0xfd94c' in said, said


def test_a_dump_gone_during_the_search_is_passed_over(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md INS-31: removed between the search and its time read (Sentry pruning reports), it raised
    reader = _reader()
    there = _dump(tmp_path, name='there.dmp')
    found = glob.glob
    monkeypatch.setattr(glob, 'glob', lambda pattern: [str(there.parent / 'gone.dmp'), *found(pattern)])
    monkeypatch.setitem(vars(reader), 'dump_folders', lambda: [str(there.parent)])
    monkeypatch.setitem(vars(reader), '_atos', _no_names)
    assert reader.main([]) == 0
    assert capsys.readouterr().out.splitlines()[0] == str(there)


def test_a_dump_given_by_its_file_name_alone_has_designers_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md INS-32: from the dump's own folder, the log was looked for under it, and left out
    path = _dump(tmp_path, name='a1b2.dmp')
    attachments = tmp_path / 'Sentry-Crashpad' / 'attachments' / 'a1b2'
    attachments.mkdir(parents=True)
    (attachments / 'log.txt').write_text('the last line\n')
    monkeypatch.chdir(path.parent)
    assert 'the last line' in _said(Path('a1b2.dmp'), name_frames=_no_names)


def test_the_dumps_are_looked_for_in_each_designers_crashpad_folders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # the user's, then those of the Designers agents started; a finished report waits in pending/ until its upload is
    # done or skipped (REVIEW.md INS-29, TST-347)
    reader = _reader()
    _home_is(monkeypatch, tmp_path / 'me')
    monkeypatch.setitem(vars(reader), 'agent_designer_folders', lambda: ['/tmp/sd_mcp_501_9902'])
    # joined as the reader does: on Windows with a backslash (REVIEW.md TST-352)
    homes = [str(tmp_path / 'me'), os.path.join('/tmp/sd_mcp_501_9902', 'home')]
    expected = [
        os.path.join(home, *DATA, 'Sentry-Crashpad', part) for home in homes for part in ('pending', 'completed')
    ]
    assert reader.dump_folders() == expected


def test_a_dump_waiting_for_its_upload_is_read_as_the_newest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md INS-29: the user's Designer uploads its reports; while it does, the newest is in pending/; neither the
    # first found nor the last (REVIEW.md TST-350)
    reader = _reader()
    _home_is(monkeypatch, tmp_path / 'me')
    monkeypatch.setitem(vars(reader), 'agent_designer_folders', lambda: [str(tmp_path / 'agent')])
    monkeypatch.setitem(vars(reader), '_atos', _no_names)
    users, agents = tmp_path.joinpath('me', *DATA), tmp_path.joinpath('agent', 'home', *DATA)
    older = _dump(users, name='older.dmp', part='pending')
    new = _dump(agents, name='new.dmp', part='pending')
    oldest = _dump(agents, name='oldest.dmp')
    os.utime(older, (time.time() - 60, time.time() - 60))
    os.utime(oldest, (time.time() - 120, time.time() - 120))
    assert reader.main([]) == 0
    assert capsys.readouterr().out.splitlines()[0] == str(new)


@pytest.mark.parametrize('fat', [True, False], ids=['universal', 'arm64 only'])
def test_frames_of_the_build_that_crashed_are_named(tmp_path: Path, fat: bool) -> None:
    qtcore = tmp_path / 'QtCore'
    qtcore.write_bytes(macho(BUILD, fat=fat))
    crash = an_abort(modules=(KERNEL, LIBC, Module(str(qtcore), QTCORE.base, uuid=BUILD), DESIGNER))
    said = _said(_dump(tmp_path, crash), name_frames=lambda path, base, addresses: ['QVariant::~QVariant()'])
    assert 'QtCore +0xfd94c  QVariant::~QVariant()' in said, said


@pytest.mark.parametrize('on_disk', [macho(OTHER_BUILD), b''], ids=['another build', 'not a Mach-O file'])
def test_frames_of_another_build_on_disk_are_not_named(tmp_path: Path, on_disk: bytes) -> None:
    # REVIEW.md INS-30: Designer updated since the crash: the file's names at the dump's offsets are wrong
    qtcore = tmp_path / 'QtCore'
    qtcore.write_bytes(on_disk)
    asked: list[str] = []

    def name_frames(path: str, base: int, addresses: list[int]) -> list[str]:
        asked.append(path)
        return ['QVariant::~QVariant()']

    crash = an_abort(modules=(KERNEL, LIBC, Module(str(qtcore), QTCORE.base, uuid=BUILD), DESIGNER))
    said = _said(_dump(tmp_path, crash), name_frames=name_frames)
    assert not asked and 'QVariant' not in said, said
    assert "QtCore's frames aren't named: the file on disk isn't the build that crashed" in said, said


def test_a_build_record_cut_short_doesnt_stop_the_reading(tmp_path: Path) -> None:
    # REVIEW.md INS-33: a dump cut short within a module's CodeView record raised ValueError, a traceback; here the last
    # module's record is the file's last 10 bytes, its 'RSDS' and 6 of the UUID's 16 (the directory is written last)
    data = bytearray(minidump(an_abort()))
    count, directory = struct.unpack_from('<II', data, 8)
    streams = [struct.unpack_from('<III', data, directory + 12 * i) for i in range(count)]
    modules = next(rva for kind, _size, rva in streams if kind == 4)
    last = modules + 4 + 108 * (struct.unpack_from('<I', data, modules)[0] - 1)
    struct.pack_into('<II', data, last + 76, 24, len(data))
    path = tmp_path / 'cut.dmp'
    path.write_bytes(bytes(data) + b'RSDS' + bytes(6))
    assert '3  Adobe Substance 3D Designer +0x1234' in _said(path, name_frames=_no_names)


def _macho_header(commands: int, size: int) -> bytes:
    return struct.pack('<IIIIIIII', 0xFEEDFACF, CPU_ARM64, 0, 6, commands, size, 0, 0)


@pytest.mark.parametrize(
    'content',
    [
        _macho_header(0xFFFFFFFF, 8) + struct.pack('<II', 0x19, 0),  # a load command of size 0, then 2^32 - 1 more
        _macho_header(1, 0xFFFFFFFF) + struct.pack('<II', 0x1B, 24) + bytes(16),  # commands of 4 GB, said
        struct.pack('>II', 0xCAFEBABE, 0xFFFFFFFF),  # a universal file of 2^32 - 1 parts, said
    ],
    ids=['command of size 0', 'commands too long', 'too many parts'],
)
def test_a_malformed_macho_file_on_disk_gives_no_build(tmp_path: Path, content: bytes) -> None:
    # REVIEW.md INS-33: neither going round its commands nor reading what its sizes ask
    path = tmp_path / 'QtCore'
    path.write_bytes(content)
    reader = _reader()
    tracing = tracemalloc.is_tracing()  # already on (-X tracemalloc): its peak is the session's (REVIEW.md TST-353)
    if not tracing:
        tracemalloc.start()
    try:
        with _within(5):
            assert reader._file_build(str(path)) is None
        assert tracing or tracemalloc.get_traced_memory()[1] < 1 << 20, 'peak bytes'
    finally:
        if not tracing:
            tracemalloc.stop()


def test_it_runs_as_a_script(tmp_path: Path) -> None:
    done = subprocess.run([sys.executable, SCRIPT, str(_dump(tmp_path))], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0 and 'exception: EXC_CRASH, signal SIGABRT' in done.stdout, done.stderr
    refused = subprocess.run([sys.executable, SCRIPT, str(tmp_path / 'none.dmp')], capture_output=True, text=True)
    assert refused.returncode == 1 and 'none.dmp' in refused.stderr
