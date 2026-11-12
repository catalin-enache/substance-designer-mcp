"""Synthetic minidumps, laid out as Designer's crash reporter (Crashpad) writes them on macOS arm64, holding only what
scripts/read_crash_dump.py reads: the system, the modules (with their builds' UUIDs), one thread with its stack and
registers, more memory, the exception and the messages Crashpad keeps per module; and Mach-O files holding only their
UUID, for the modules on disk. For its tests (test_read_crash_dump.py, test_old_python.py)."""

import struct
import uuid as uuids
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

ARM64, AMD64 = 12, 9  # MINIDUMP_SYSTEM_INFO's ProcessorArchitecture
MACOS, WINDOWS = 0x8101, 2  # its PlatformId
EXC_CRASH, SIGABRT_CODE = 10, 6 << 24  # an abort, as Crashpad records it: the Mach exception, its code (the signal)
CRASHPAD_INFO = 0x43500001
CPU_ARM64 = 0x0100000C  # a Mach-O file's cputype


@dataclass
class Module:
    path: str
    base: int
    size: int = 0x1000000
    uuid: bytes | None = None  # its build's (LC_UUID's 16 bytes), in a CodeView record as Crashpad writes it
    name_length: int | None = None  # the name's length in bytes as written, when not its UTF-16's


@dataclass
class Crash:
    """A crash: its modules, the crashing thread's registers and stack, the exception and Crashpad's messages."""

    modules: Sequence[Module]
    pc: int
    lr: int
    fp: int
    sp: int
    stack_start: int
    stack: bytes  # from stack_start: the frame records (the caller's fp, the return address) the walk follows
    params: Sequence[int] = (EXC_CRASH, SIGABRT_CODE, 0)
    code: int = 0
    messages: Sequence[tuple[int, str]] = ()  # (module index, text)
    arch: int = ARM64
    platform: int = MACOS
    thread: int = 7
    other_threads: Sequence[int] = field(default_factory=list)
    memory: Sequence[tuple[int, bytes]] = ()  # the memory list's ranges, (start, bytes), beside the thread's stack


class _Writer:
    def __init__(self) -> None:
        self.data = bytearray(32)  # the header, written last

    def add(self, blob: bytes) -> int:
        while len(self.data) % 4:
            self.data.append(0)
        rva = len(self.data)
        self.data += blob
        return rva


def frames(*records: tuple[int, int, int]) -> bytes:
    """Stack bytes holding frame records at given offsets: (offset, caller's fp, return address)."""
    size = max(offset for offset, _, _ in records) + 16
    stack = bytearray(size)
    for offset, fp, ret in records:
        struct.pack_into('<QQ', stack, offset, fp, ret)
    return bytes(stack)


STACK = 0x16F000000
KERNEL = Module('/usr/lib/system/libsystem_kernel.dylib', 0x180000000)
LIBC = Module('/usr/lib/system/libsystem_c.dylib', 0x181000000)
QTCORE = Module(
    '/Applications/Adobe Substance 3D Designer.app/Contents/Frameworks/QtCore.framework/QtCore', 0x118000000
)
DESIGNER = Module(
    '/Applications/Adobe Substance 3D Designer.app/Contents/MacOS/Adobe Substance 3D Designer', 0x100000000
)
PAC = 0x0012000000000000  # a return address's pointer-authentication bits, which the walk drops


def an_abort(**kw: Any) -> Crash:
    """An abort in the kernel (pc), called from libc (lr), with two frame records above it on the stack: QtCore's
    return address (signed), then Designer's, then the end of the chain; Crashpad kept libc's "abort() called"."""
    stack = frames(
        (0x20, STACK + 0x40, (QTCORE.base + 0xFD94C) | PAC), (0x40, STACK + 0x60, DESIGNER.base + 0x1234), (0x60, 0, 0)
    )
    defaults: dict[str, Any] = {
        'modules': (KERNEL, LIBC, QTCORE, DESIGNER),
        'pc': KERNEL.base + 0x95E8,
        'lr': LIBC.base + 0x78978,
        'fp': STACK + 0x20,
        'sp': STACK,
        'stack_start': STACK,
        'stack': stack,
        'messages': [(1, 'abort() called')],
    }
    return Crash(**{**defaults, **kw})


def minidump(crash: Crash) -> bytes:
    w = _Writer()
    streams: list[tuple[int, int, int]] = []  # type, size, rva

    def stream(kind: int, blob: bytes) -> None:
        streams.append((kind, len(blob), w.add(blob)))

    system = struct.pack('<HHHBBIIIIIHH', crash.arch, 0, 0, 8, 1, 26, 6, 2, crash.platform, 0, 0, 0) + bytes(24)
    stream(7, system)
    entries = b''
    for m in crash.modules:
        length = len(m.path) * 2 if m.name_length is None else m.name_length
        entry = bytearray(108)
        struct.pack_into(
            '<QIIII',
            entry,
            0,
            m.base,
            m.size,
            0,
            0,
            w.add(struct.pack('<I', length) + m.path.encode('utf-16-le') + b'\0\0'),
        )
        if m.uuid is not None:  # PDB 7.0's record, the UUID as a GUID (little-endian fields), its age, an empty name
            cv = b'RSDS' + uuids.UUID(bytes=m.uuid).bytes_le + struct.pack('<I', 0) + b'\0'
            struct.pack_into('<II', entry, 76, len(cv), w.add(cv))
        entries += bytes(entry)
    stream(4, struct.pack('<I', len(crash.modules)) + entries)
    if crash.memory:
        ranges = [(start, len(blob), w.add(blob)) for start, blob in crash.memory]
        stream(5, struct.pack('<I', len(ranges)) + b''.join(struct.pack('<QII', *r) for r in ranges))
    regs = [0] * 31
    regs[29], regs[30] = crash.fp, crash.lr
    context = struct.pack('<II31QQQ', 0, 0, *regs, crash.sp, crash.pc) + bytes(640)
    context_rva = w.add(context)
    stack_rva = w.add(crash.stack)
    threads = [
        struct.pack(
            '<IIIIQQIIII',
            crash.thread,
            0,
            0,
            0,
            0,
            crash.stack_start,
            len(crash.stack),
            stack_rva,
            len(context),
            context_rva,
        )
    ]
    for other in crash.other_threads:  # no stack, no registers of their own: never walked
        threads.append(struct.pack('<IIIIQQIIII', other, 0, 0, 0, 0, 0, 0, 0, len(context), context_rva))
    stream(3, struct.pack('<I', len(threads)) + b''.join(threads))
    params = list(crash.params) + [0] * (15 - len(crash.params))
    exception = struct.pack(
        '<IIIIQQII15QII',
        crash.thread,
        0,
        crash.code,
        0,
        0,
        crash.pc,
        len(crash.params),
        0,
        *params,
        len(context),
        context_rva,
    )
    stream(6, exception)
    if crash.messages:
        links = []
        for index, message in crash.messages:
            text = w.add(struct.pack('<I', len(message.encode())) + message.encode() + b'\0')
            listed = w.add(struct.pack('<II', 1, text))
            info = w.add(struct.pack('<IIIIIII', 1, 8, listed, 0, 0, 0, 0))
            links.append(struct.pack('<III', index, 28, info))
        module_list = w.add(struct.pack('<I', len(links)) + b''.join(links))
        stream(
            CRASHPAD_INFO,
            struct.pack('<I', 1) + bytes(32) + struct.pack('<IIII', 0, 0, 4 + 12 * len(links), module_list),
        )
    directory = w.add(b''.join(struct.pack('<III', *s) for s in streams))
    struct.pack_into('<IIIIIIQ', w.data, 0, 0x504D444D, 0xA793, len(streams), directory, 0, 0, 0)
    return bytes(w.data)


def macho(uuid: bytes, fat: bool = True) -> bytes:
    """A Mach-O file of arm64 code holding only its build's UUID (LC_UUID); universal, as Designer's QtCore is, when
    `fat`."""
    thin = struct.pack('<IIIIIIII', 0xFEEDFACF, CPU_ARM64, 0, 6, 1, 24, 0, 0) + struct.pack('<II', 0x1B, 24) + uuid
    if not fat:
        return thin
    head = struct.pack('>II', 0xCAFEBABE, 1) + struct.pack('>IIIII', CPU_ARM64, 0, 0x1000, len(thin), 12)
    return head + bytes(0x1000 - len(head)) + thin
