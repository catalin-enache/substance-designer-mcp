"""A pytest plugin that runs unit tests on macOS with what this code uses and Windows lacks taken away: the platform
set to 'win32', the modules of POSIX_ONLY unimportable (but `posix`), and NAMES gone from `os` and `signal` (ROADMAP item 18). It is not
Windows: only those differences are simulated, and one more: a write through `open` in mode 'w', 'a' or 'x', without
'b' or '+', that gives no `newline` ends each line with '\\r\\n'. A read-write mode ('+') is left as it is.
test_windows_simulation.py runs, under it, the files that mention the system or one of
those names, so a test that depends on them says so, with a skip, rather than failing on Windows (REVIEW.md TST-508,
TST-509)."""

import builtins
import io
import os
import signal
import sys
from collections.abc import Callable
from typing import IO

import pytest

# the modules only Unix has, which no file imports where it starts (test_lint.py); all but `posix`, which `os` is
# built on there, are made unimportable
POSIX_ONLY = ('fcntl', 'termios', 'pwd', 'grp', 'resource', 'posix')
NAMES = {os: ('getuid', 'geteuid'), signal: ('SIGKILL', 'SIGALRM', 'setitimer', 'ITIMER_REAL')}  # Unix's, which it uses
# What open takes as its file: typeshed's FileDescriptorOrPath, which exists for the checker only. A copy of conftest.py's,
# which this plugin doesn't import: conftest.py imports the server
OpenedFile = int | str | bytes | os.PathLike[str] | os.PathLike[bytes]
REAL_OPEN = io.open  # as it is before pytest_configure replaces it


def pytest_configure(config: pytest.Config) -> None:
    sys.platform = 'win32'
    for module in POSIX_ONLY:
        if module != 'posix':  # os is built on it
            sys.modules[module] = None  # type: ignore[assignment]  # None makes `import <module>` fail, as on Windows
    for owner, names in NAMES.items():
        for name in names:
            delattr(owner, name)
    # `Path.open`, `os.fdopen` and `tempfile` open through `io.open`, which `builtins.open` is
    vars(io)['open'] = vars(builtins)['open'] = _open_as_on_windows


def _open_as_on_windows(
    file: OpenedFile,
    mode: str = 'r',
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: Callable[[str, int], int] | None = None,
) -> IO[str] | IO[bytes]:
    """`open`, but a text-mode write that gives no `newline` ('w', 'a' or 'x', without 'b' or '+') writes '\\r\\n' for
    each '\\n', as on Windows. A text-mode read already turns '\\r\\n' back into '\\n' on macOS."""
    chars = set(mode)
    if newline is None and chars & set('wax') and not chars & set('b+'):
        newline = '\r\n'
    return REAL_OPEN(file, mode, buffering, encoding, errors, newline, closefd, opener)
