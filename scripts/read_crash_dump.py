"""What a crash dump of Designer's says, read without a minidump parser: none at hand reads macOS arm64 dumps (the
`minidump` package refuses their system info). Designer's crash reporter (Sentry, through Crashpad) keeps one in
`Sentry-Crashpad/completed/` in Designer's data folder (in `pending/` while its upload waits; Crashpad's database): the
user's, or the home of a Designer an agent started (`/tmp/sd_mcp_<user ID>_<port>/home/...`).

Usage:
    python3 scripts/read_crash_dump.py [DUMP]   the newest dump of any of them when DUMP is omitted

It prints the exception (an abort says its signal), the messages Crashpad kept per module (an abort's reason, often),
the crashing thread's frames, newest first, through its frame pointers (the first two are the program counter and the
link register: for a crash in a function that calls others, the second may be a stale return address within it), each
as module + offset, named by `atos` where the module is a file outside the system's libraries (those are in the shared
cache, where atos names nothing, or the wrong function) of the build that crashed (its UUID, in the dump, against the
file's: an update since would give wrong names), the first frame outside the system's libraries, and the last
lines of Designer's log as it crashed (attached beside the dump). The Sentry event attached there, which holds the
user's Adobe account, is never read. macOS on arm64 only: other dumps are refused.

Exit status: 0 when it read a dump, 1 when it can't (it says why), 2 for a bad argument.
"""

# Annotations stay unevaluated: this script runs on the system Python, which can be older than 3.10
from __future__ import annotations

import argparse
import datetime
import glob
import os
import signal
import struct
import subprocess
import sys
import uuid
from collections.abc import Callable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from project_constants import agent_designer_folders  # noqa: E402

DATA = ('Library', 'Application Support', 'Adobe', 'Adobe Substance 3D Designer')
SIGNATURE, ARM64, MACOS = 0x504D444D, 12, 0x8101  # 'MDMP'; MINIDUMP_SYSTEM_INFO's arm64 and macOS
THREADS, MODULES, MEMORY, EXCEPTION, SYSTEM, CRASHPAD_INFO = 3, 4, 5, 6, 7, 0x43500001
EXC_CRASH = 10
# <mach/exception_types.h>
MACH_EXCEPTIONS = {
    1: 'EXC_BAD_ACCESS',
    2: 'EXC_BAD_INSTRUCTION',
    3: 'EXC_ARITHMETIC',
    4: 'EXC_EMULATION',
    5: 'EXC_SOFTWARE',
    6: 'EXC_BREAKPOINT',
    7: 'EXC_SYSCALL',
    8: 'EXC_MACH_SYSCALL',
    9: 'EXC_RPC_ALERT',
    10: 'EXC_CRASH',
    11: 'EXC_RESOURCE',
    12: 'EXC_GUARD',
    13: 'EXC_CORPSE_NOTIFY',
}
SYSTEM_LIBRARIES = ('/usr/lib/', '/System/Library/')
ADDRESS = (1 << 47) - 1  # a return address's pointer-authentication bits dropped
LOG_LINES = 8
DEPTH = 64  # frames said at most, so frame records walked too
# a Mach-O file's: universal (Designer's are, with one arm64 part each), arm64 code's, a 64-bit header's, the UUID's
# load command
FAT, CPU_ARM64, MACHO_64, LC_UUID = 0xCAFEBABE, 0x0100000C, 0xFEEDFACF, 0x1B


class CannotRead(Exception):
    """The dump can't be read, and the message says why."""


class _Dump:
    def __init__(self, data: bytes) -> None:
        if len(data) < 32 or struct.unpack_from('<I', data)[0] != SIGNATURE:
            raise CannotRead('not a minidump (no MDMP signature)')
        self.data = data
        count, directory = struct.unpack_from('<II', data, 8)
        self.streams: dict[int, tuple[int, int]] = {}
        for i in range(count):
            kind, size, rva = struct.unpack_from('<III', data, directory + 12 * i)
            self.streams[kind] = (size, rva)
        for kind in (SYSTEM, MODULES, THREADS, EXCEPTION):
            if kind not in self.streams:
                raise CannotRead('the dump has no stream %d (the system, modules, threads or exception)' % kind)
        arch = struct.unpack_from('<H', data, self.streams[SYSTEM][1])[0]
        platform = struct.unpack_from('<I', data, self.streams[SYSTEM][1] + 20)[0]
        if (arch, platform) != (ARM64, MACOS):
            raise CannotRead(
                'this reads dumps of macOS on arm64; this one is of CPU %d, platform %#x' % (arch, platform)
            )
        self.modules = self._modules()
        self.memory = self._memory()

    def _modules(self) -> list[tuple[int, int, str, str | None]]:
        """(base, size, path, its build's UUID or None) per module."""
        rva = self.streams[MODULES][1]
        found = []
        for i in range(struct.unpack_from('<I', self.data, rva)[0]):
            entry = rva + 4 + 108 * i
            base, size, _sum, _time, name = struct.unpack_from('<QIIII', self.data, entry)
            length = struct.unpack_from('<I', self.data, name)[0]
            # a malformed name read too (REVIEW.md INS-31)
            path = self.data[name + 4 : name + 4 + length].decode('utf-16-le', 'replace')
            found.append((base, size, path, self._build(*struct.unpack_from('<II', self.data, entry + 76))))
        return found

    def _build(self, size: int, at: int) -> str | None:
        """The UUID of a module's build in its CodeView record (PDB 7.0's, Crashpad's for a Mach-O module: its LC_UUID
        as a GUID), None without one."""
        record = self.data[at : at + size]
        if len(record) < 20 or record[:4] != b'RSDS':  # the bytes there: a dump cut short too (REVIEW.md INS-33)
            return None
        return str(uuid.UUID(bytes_le=record[4:20])).upper()

    def _memory(self) -> list[tuple[int, bytes]]:
        ranges = []
        if MEMORY in self.streams:
            rva = self.streams[MEMORY][1]
            for i in range(struct.unpack_from('<I', self.data, rva)[0]):
                start, size, at = struct.unpack_from('<QII', self.data, rva + 4 + 16 * i)
                ranges.append((start, self.data[at : at + size]))
        rva = self.streams[THREADS][1]
        for i in range(struct.unpack_from('<I', self.data, rva)[0]):
            fields = struct.unpack_from('<IIIIQQII', self.data, rva + 4 + 48 * i)
            start, size, at = fields[5], fields[6], fields[7]
            ranges.append((start, self.data[at : at + size]))
        return ranges

    def module(self, address: int) -> tuple[int, int, str, str | None] | None:
        for module in self.modules:
            if module[0] <= address < module[0] + module[1]:
                return module
        return None

    def where(self, address: int) -> str:
        module = self.module(address)
        if module is None:
            return '%#x (in no module)' % address
        return '%s +%#x' % (os.path.basename(module[2]), address - module[0])

    def read64(self, address: int) -> int | None:
        for start, memory in self.memory:
            if start <= address and address + 8 <= start + len(memory):
                return int(struct.unpack_from('<Q', memory, address - start)[0])
        return None

    def exception(self) -> tuple[int, int, list[int], int]:
        """The crashing thread, the exception's code, its parameters, and the RVA of the thread's registers."""
        rva = self.streams[EXCEPTION][1]
        thread, _align, code, _flags, _record, _address, count = struct.unpack_from('<IIIIQQI', self.data, rva)
        params = list(struct.unpack_from('<%dQ' % min(count, 15), self.data, rva + 40))
        context = struct.unpack_from('<I', self.data, rva + 164)[0]
        return thread, code, params, context

    def frames(self, context: int) -> list[int]:
        """The program counter, the link register, then the return addresses of the frame records the frame pointer
        chains, as long as they rise on the stack and can be read; at most DEPTH."""
        regs = struct.unpack_from('<31Q', self.data, context + 8)
        pc = struct.unpack_from('<Q', self.data, context + 8 + 32 * 8)[0]  # after x0-x30 and sp
        found = [pc & ADDRESS, regs[30] & ADDRESS]
        fp = regs[29]
        for walked in range(DEPTH - len(found)):
            if not fp:
                break
            caller, ret = self.read64(fp), self.read64(fp + 8)
            if caller is None or ret is None or not ret:
                break
            # only the first record can repeat the link register: the crashing function saved it there and called
            # nothing since; later ones repeat only in a recursion, each frame said (REVIEW.md INS-28)
            if walked or ret & ADDRESS != found[-1]:
                found.append(ret & ADDRESS)
            if caller <= fp:  # not rising: a corrupt stack, which would go round
                break
            fp = caller
        return found

    def messages(self) -> list[str]:
        """The messages Crashpad kept per module (its list annotations), each after the module's name."""
        if CRASHPAD_INFO not in self.streams:
            return []
        rva = self.streams[CRASHPAD_INFO][1]
        listed = struct.unpack_from('<I', self.data, rva + 48)[0]
        if not listed:
            return []
        said = []
        for i in range(struct.unpack_from('<I', self.data, listed)[0]):
            index, _size, info = struct.unpack_from('<III', self.data, listed + 4 + 12 * i)
            size, texts = struct.unpack_from('<II', self.data, info + 4)
            if not size:
                continue
            name = os.path.basename(self.modules[index][2]) if index < len(self.modules) else 'module %d' % index
            for j in range(struct.unpack_from('<I', self.data, texts)[0]):
                at = struct.unpack_from('<I', self.data, texts + 4 + 4 * j)[0]
                length = struct.unpack_from('<I', self.data, at)[0]
                said.append('%s: %s' % (name, self.data[at + 4 : at + 4 + length].decode('utf-8', 'replace')))
        return said


def _exception(code: int, params: list[int]) -> str:
    """The exception as Crashpad records it on macOS: its first parameter the Mach exception; for EXC_CRASH, the
    signal in its code's top byte (measured: an abort is EXC_CRASH, 0x6000000, SIGABRT), its own code the exception
    the crash came from (0: a signal)."""
    if not params:
        return 'code %#x' % code
    said = MACH_EXCEPTIONS.get(params[0], 'Mach exception %d' % params[0])
    if params[0] == EXC_CRASH and len(params) > 1:
        number = (params[1] >> 24) & 0xFF
        try:
            said += ', signal %s' % signal.Signals(number).name
        except ValueError:
            said += ', signal %d' % number
        if code:
            said += ', from %s' % MACH_EXCEPTIONS.get(code, 'Mach exception %d' % code)
    return '%s (codes %s)' % (said, ', '.join('%#x' % p for p in params[1:]))


def _atos(path: str, base: int, addresses: list[int]) -> list[str]:
    """The names atos gives `addresses` in the module at `path`, loaded at `base`, one per address ('' unnamed)."""
    done = subprocess.run(
        ['atos', '-arch', 'arm64', '-o', path, '-l', hex(base)] + [hex(a) for a in addresses],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return [line.strip() for line in done.stdout.splitlines()]


def _file_build(path: str) -> str | None:
    """The UUID of the arm64 code's build in the Mach-O file at `path` (its LC_UUID), None when it can't be read: a
    count or size larger than the file is never read, nor a load command shorter than its header (REVIEW.md INS-33)."""
    try:
        with open(path, 'rb') as f:
            total = os.fstat(f.fileno()).st_size
            head = f.read(8)
            offset = 0
            if len(head) == 8 and struct.unpack_from('>I', head)[0] == FAT:  # universal: arm64's part
                count = struct.unpack_from('>I', head, 4)[0]
                if 20 * count > total:
                    return None
                table = f.read(20 * count)
                for i in range(count):
                    if struct.unpack_from('>I', table, 20 * i)[0] == CPU_ARM64:
                        offset = struct.unpack_from('>I', table, 20 * i + 8)[0]
                        break
                else:
                    return None
            f.seek(offset)
            header = f.read(32)
            if struct.unpack_from('<I', header)[0] != MACHO_64:
                return None
            count, size = struct.unpack_from('<II', header, 16)
            if size > total:
                return None
            commands = f.read(size)
        at = 0
        for _ in range(count):
            command, length = struct.unpack_from('<II', commands, at)
            if command == LC_UUID:
                return str(uuid.UUID(bytes=commands[at + 8 : at + 24])).upper()
            if length < 8:
                return None
            at += length
    except (OSError, struct.error, ValueError):
        pass
    return None


def _names(
    dump: _Dump,
    frames: list[int],
    name_frames: Callable[[str, int, list[int]], list[str]],
    build_of: Callable[[str], str | None],
) -> tuple[dict[int, str], list[str]]:
    """The frames' names, by address, and a line for each module on disk not named because it isn't the build that
    crashed (REVIEW.md INS-30): Designer updated since, its names at the dump's offsets would be wrong."""
    by_module: dict[tuple[str, int], list[int]] = {}
    skipped: set[str] = set()
    unnamed: list[str] = []
    for address in frames:
        module = dump.module(address)
        if (
            not module
            or module[2] in skipped
            or module[2].startswith(SYSTEM_LIBRARIES)
            or not os.path.isfile(module[2])
        ):
            continue
        key = (module[2], module[0])
        if key not in by_module:
            on_disk = None if module[3] is None else build_of(module[2])
            if module[3] is not None and on_disk != module[3]:  # none in the dump: nothing to compare, named as found
                skipped.add(module[2])
                unnamed.append(
                    "  %s's frames aren't named: the file on disk isn't the build that crashed (%s; the dump's %s)"
                    % (os.path.basename(module[2]), on_disk or "its build can't be read", module[3])
                )
                continue
            by_module[key] = []
        by_module[key].append(address)
    names: dict[int, str] = {}
    for (path, base), addresses in by_module.items():
        try:
            found = name_frames(path, base, addresses)
        except (OSError, subprocess.SubprocessError):
            continue
        for i, address in enumerate(addresses):  # no zip(strict=): this runs on Python 3.9 too
            name = found[i] if i < len(found) else ''
            if name and not name.startswith('0x'):
                names[address] = name
    return names, unnamed


def _log_tail(path: str) -> list[str]:
    """The last lines of the log Crashpad attached beside the dump (attachments/<its name>/log.txt), said with where."""
    database = os.path.dirname(os.path.dirname(os.path.abspath(path)))  # a bare file name too (REVIEW.md INS-32)
    log = os.path.join(database, 'attachments', os.path.splitext(os.path.basename(path))[0], 'log.txt')
    try:
        with open(log, encoding='utf-8', errors='replace') as f:
            lines = f.read().splitlines()[-LOG_LINES:]
    except OSError:
        return []
    return ["Designer's log as it crashed, its last %d lines (%s):" % (len(lines), log)] + ['  ' + li for li in lines]


def describe(
    path: str,
    name_frames: Callable[[str, int, list[int]], list[str]] | None = None,
    build_of: Callable[[str], str | None] | None = None,
) -> list[str]:
    """The lines said about the dump at `path`; CannotRead when it can't be read."""
    try:
        with open(path, 'rb') as f:
            data = f.read()
        written = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
    except OSError as e:
        raise CannotRead(str(e)) from e
    try:
        dump = _Dump(data)
        thread, code, params, context = dump.exception()
        frames = dump.frames(context)
        messages = dump.messages()
    except struct.error as e:
        raise CannotRead('the dump is cut short or malformed: %s' % e) from e
    names, unnamed = _names(dump, frames, name_frames or _atos, build_of or _file_build)
    lines = [path, '  written %s' % written, 'exception: %s' % _exception(code, params)]
    if messages:
        lines += ['messages Crashpad kept:'] + ['  ' + m for m in messages]
    lines.append('the crashing thread (%d), its frames newest first:' % thread)
    outside = None
    for i, address in enumerate(frames):
        where = dump.where(address)
        lines.append(('  %2d  %s  %s' % (i, where, names.get(address, ''))).rstrip())
        module = dump.module(address)
        if outside is None and module and not module[2].startswith(SYSTEM_LIBRARIES):
            outside = '#%d %s' % (i, where)
    lines += unnamed
    lines.append("first frame outside the system's libraries: %s" % (outside or 'none'))
    return lines + _log_tail(path)


def dump_folders() -> list[str]:
    """Where Designers keep their crash dumps: the user's, then those of the Designers agents started (macOS); in each,
    the reports waiting for their upload, then those done with it (REVIEW.md INS-29)."""
    homes = [os.path.expanduser('~')] + [os.path.join(folder, 'home') for folder in agent_designer_folders()]
    return [os.path.join(home, *DATA, 'Sentry-Crashpad', part) for home in homes for part in ('pending', 'completed')]


def _newest(paths: list[str]) -> str | None:
    """The one last written, passing over any gone meanwhile (Sentry prunes old reports; REVIEW.md INS-31)."""
    written = []
    for path in paths:
        try:
            written.append((os.path.getmtime(path), path))
        except OSError:
            continue
    return max(written)[1] if written else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="What a crash dump of Designer's says (macOS arm64).")
    parser.add_argument('dump', nargs='?', help='the dump; the newest of any Designer when omitted')
    args = parser.parse_args(argv)
    path = args.dump
    if path is None:
        folders = dump_folders()
        path = _newest([p for folder in folders for p in glob.glob(os.path.join(folder, '*.dmp'))])
        if path is None:
            print('No crash dump in: %s' % ', '.join(folders), file=sys.stderr)
            return 1
    try:
        lines = describe(path)
    except CannotRead as e:
        print('%s: %s' % (path, e), file=sys.stderr)
        return 1
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
