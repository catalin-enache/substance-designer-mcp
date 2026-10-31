"""The standalone scripts still behave on a Python older than 3.10 (a stock Mac's `python3` is 3.9):
install.py refuses with its message instead of a traceback, uninstall.py (which tells users to run it
with the system Python) works, and sd_run.py explains a timeout (REVIEW.md INS-25). Skipped when no
such interpreter is installed."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import ROOT

CANDIDATES = ('/usr/bin/python3', 'python3.9', 'python3.8')


def _old_python() -> str | None:
    for name in CANDIDATES:
        exe = name if os.path.isabs(name) else shutil.which(name)
        if not exe or not os.path.exists(exe):
            continue
        try:
            out = subprocess.run(
                [exe, '-c', 'import sys; print(sys.version_info < (3, 10))'], capture_output=True, text=True, timeout=30
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if out.stdout.strip() == 'True':
            return exe
    return None


@pytest.fixture(scope='module')
def old_python() -> str:
    exe = _old_python()
    if exe is None:
        pytest.skip('no Python older than 3.10 installed')
    return exe


def test_install_refuses_an_old_python_with_its_message(old_python: str, tmp_path: Path) -> None:
    plugins, skills = tmp_path / 'plugins', tmp_path / 'skills'
    result = subprocess.run(
        [old_python, os.path.join(ROOT, 'install.py'), '--plugins-dir', str(plugins), '--skills-dir', str(skills)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0 and 'Python 3.10+ is required' in result.stderr, result.stderr
    assert 'Traceback' not in result.stderr
    assert not plugins.exists() and not skills.exists()


def test_uninstall_runs_on_an_old_python(old_python: str) -> None:
    result = subprocess.run(
        [old_python, os.path.join(ROOT, 'uninstall.py'), '--help'], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0 and 'usage' in result.stdout, result.stderr


def test_sd_run_explains_a_timeout_on_an_old_python(old_python: str) -> None:
    # on 3.9 socket.timeout is not a TimeoutError: the bridge never answering raised it raw
    code = (
        'import socket, sys\n'
        'sys.path[:0] = [%r, %r]\n'
        'import sd_run\n'
        'def send(request, wait):\n'
        "    raise socket.timeout('timed out')\n"
        'sd_run.send = send\n'
        "sd_run._send_or_explain({'cmd': 'status'}, 1)\n"
    ) % (os.path.join(ROOT, 'client'), ROOT)
    result = subprocess.run([old_python, '-c', code], capture_output=True, text=True, timeout=60)
    assert result.returncode == 1 and 'No reply from Designer' in result.stderr, result.stderr
