"""The scripts a user starts (conftest.ENTRY_SCRIPTS) refuse a Python older than the minimum, 3.12, with a message
instead of a traceback: a stock Mac's `python3` is 3.9 (DECISIONS.md, Project rules). Each script checks
sys.version_info before any other import, and keeps to the syntax Python 3.9 parses (ruff.toml). The refusal is checked
in this Python with sys.version_info set lower, and on a Python 3.9 when one is installed."""

import ast
import os
import re
import runpy
import shutil
import subprocess
import sys

import pytest

from conftest import ENTRY_SCRIPTS, ROOT, SERVER_SCRIPT, VERSION_CHECKED
from project_constants import MIN_PYTHON

CANDIDATES = ('/usr/bin/python3', 'python3.9')  # a stock Mac's python3 is 3.9 (REVIEW.md INS-40)
REFUSAL = r'Python %d\.%d\+ is required \(found %%s\)' % MIN_PYTHON  # the scripts' message, the found version left out
# what the server adds: Claude Code starts it with the venv's Python, which an older Python may have made (SRV-176)
AGAIN = '. If this is mcp_server/venv, an older Python made it: run install.py again, with a Python %d.%d+' % MIN_PYTHON


def _refusal(script: str, found: str) -> str:
    return REFUSAL % found + (re.escape(AGAIN) if script == SERVER_SCRIPT else '')


def _old_python() -> str | None:
    for name in CANDIDATES:
        exe = name if os.path.isabs(name) else shutil.which(name)
        if not exe or not os.path.exists(exe):
            continue
        try:
            out = subprocess.run(
                [exe, '-c', 'import sys; print((3, 9) <= sys.version_info < (3, 10))'],
                capture_output=True,
                text=True,
                timeout=30,
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
        pytest.skip('no Python 3.9 installed')
    return exe


def test_every_script_a_user_starts_is_listed() -> None:
    """ENTRY_SCRIPTS holds every file of the repository's root folder, client/ and scripts/ that runs as a script."""
    found = []
    for folder in ('', 'client', 'scripts'):
        for name in os.listdir(os.path.join(ROOT, folder)):
            if name.endswith('.py'):
                with open(os.path.join(ROOT, folder, name), encoding='utf-8') as f:
                    if re.search(r"^if __name__ == '__main__':$", f.read(), re.MULTILINE):
                        found.append('%s/%s' % (folder, name) if folder else name)
    assert sorted(found) == sorted(ENTRY_SCRIPTS)


@pytest.mark.parametrize('script', VERSION_CHECKED)
def test_each_script_checks_the_python_before_anything_else(script: str) -> None:
    """Only the docstring and `import sys` come before the check: any other import could need what an older Python
    lacks, and this project's modules use what 3.12 has."""
    with open(os.path.join(ROOT, script), encoding='utf-8') as f:
        tree = ast.parse(f.read())
    body = tree.body[1:] if ast.get_docstring(tree) is not None else tree.body
    assert ast.unparse(body[0]) == 'import sys'
    guard = body[1]
    assert isinstance(guard, ast.If) and ast.unparse(guard.test) == 'sys.version_info < %r' % (MIN_PYTHON,)


@pytest.mark.parametrize('version', [(3, 9, 6), (3, 11, 9)])
@pytest.mark.parametrize('script', VERSION_CHECKED)
def test_each_script_refuses_an_older_python(
    script: str, version: tuple[int, int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    found = '%d.%d.%d' % version
    monkeypatch.setattr(sys, 'version_info', version)
    monkeypatch.setattr(sys, 'version', found + ' (main)')
    monkeypatch.setattr(sys, 'argv', [script, '--help'])
    with pytest.raises(SystemExit, match='^%s$' % _refusal(script, re.escape(found))):
        runpy.run_path(os.path.join(ROOT, script), run_name='__main__')


@pytest.mark.parametrize('script', VERSION_CHECKED)
def test_each_script_refuses_a_real_python_3_9(old_python: str, script: str) -> None:
    """Python 3.9 parses the whole file before it runs the check: any syntax it lacks would fail first."""
    result = subprocess.run(
        [old_python, os.path.join(ROOT, script), '--help'], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 1 and not result.stdout, result.stdout + result.stderr
    assert re.fullmatch(_refusal(script, r'3\.9\.\d+') + '\n', result.stderr), result.stderr
