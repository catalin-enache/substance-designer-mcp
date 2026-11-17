"""A pytest plugin that runs unit tests on macOS with what this code uses and Windows lacks taken away: the platform
set to 'win32', the modules of POSIX_ONLY unimportable (but `posix`), and NAMES gone from `os` and `signal` (ROADMAP item 18). It is not
Windows: only those differences are simulated. test_windows_simulation.py runs, under it, the files that mention the
system or one of those names, so a test that depends on them says so, with a skip, rather than failing on Windows
(REVIEW.md TST-508, TST-509)."""

import os
import signal
import sys

import pytest

# the modules only Unix has, which no file imports where it starts (test_lint.py); all but `posix`, which `os` is
# built on there, are made unimportable
POSIX_ONLY = ('fcntl', 'termios', 'pwd', 'grp', 'resource', 'posix')
NAMES = {os: ('getuid', 'geteuid'), signal: ('SIGKILL', 'SIGALRM', 'setitimer', 'ITIMER_REAL')}  # Unix's, which it uses


def pytest_configure(config: pytest.Config) -> None:
    sys.platform = 'win32'
    for module in POSIX_ONLY:
        if module != 'posix':  # os is built on it
            sys.modules[module] = None  # type: ignore[assignment]  # None makes `import <module>` fail, as on Windows
    for owner, names in NAMES.items():
        for name in names:
            delattr(owner, name)
