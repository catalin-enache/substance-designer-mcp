"""Every Python file in the repository passes ruff's lint rules and is formatted by ruff (ruff.toml)."""

import importlib.util
import subprocess
import sys

import pytest
from windows_simulation import POSIX_ONLY

from conftest import ROOT, VERSION_CHECKED
from project_constants import MIN_PYTHON


def _ruff(*args: str) -> subprocess.CompletedProcess[str]:
    if importlib.util.find_spec('ruff') is None:
        pytest.fail(
            'ruff is not installed: mcp_server/venv/bin/python -m pip install -r mcp_server/requirements-dev.txt'
        )
    return subprocess.run([sys.executable, '-m', 'ruff', *args], cwd=ROOT, capture_output=True, text=True)


def test_ruff_check_finds_nothing() -> None:
    result = _ruff('check', '--no-cache', '.')
    assert result.returncode == 0, result.stdout + result.stderr


def test_ruff_checks_the_scripts_a_user_starts_as_python_3_9() -> None:
    """ruff checks the code as the minimum Python, 3.12 (project_constants.MIN_PYTHON). The scripts a user starts, and
    the server, must still parse on an older Python, a stock Mac's 3.9, to refuse it with a message (DECISIONS.md, Project
    rules): ruff checks them as 3.9, so it reports most of the syntax 3.9 lacks, and its fixes add none. ruff 0.17.3 lets
    `a[e := 0]` through (REVIEW.md TST-530): test_old_python.py's run on a real Python 3.9, where one is installed,
    catches the rest."""
    import os
    import tomllib

    with open(os.path.join(ROOT, 'ruff.toml'), 'rb') as f:
        config = tomllib.load(f)
    assert config['target-version'] == 'py%d%d' % MIN_PYTHON
    assert config.get('per-file-target-version') == dict.fromkeys(VERSION_CHECKED, 'py39')


def test_every_file_is_formatted() -> None:
    result = _ruff('format', '--check', '--no-cache', '.')
    assert result.returncode == 0, result.stdout + result.stderr + '\nRun: mcp_server/venv/bin/ruff format .'


def test_no_module_imports_a_posix_only_module_at_its_top() -> None:
    """The unit suite runs on Windows too (AGENTS.md, Running the tests), and so do the server, the self-test and the
    plugin, inside Designer: a POSIX-only module imported where a file starts stops it from loading there (REVIEW.md
    TST-356, TST-369). Import it inside the function or test that needs it."""
    import ast
    import os

    found = []
    for here, dirs, files in os.walk(ROOT):
        # every file of the repository's own: not its tools' (.git, .claude's vendored skill, the caches) nor the venv
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', '__pycache__', 'node_modules')]
        for name in files:
            if not name.endswith('.py'):
                continue
            path = os.path.join(here, name)
            with open(path, encoding='utf-8') as f:
                tree = ast.parse(f.read(), path)
            for node in tree.body:
                names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or '']
                    if isinstance(node, ast.ImportFrom)
                    else []
                )
                found += [
                    '%s:%d %s' % (os.path.relpath(path, ROOT), node.lineno, n)
                    for n in names
                    if n.split('.')[0] in POSIX_ONLY
                ]
    assert not found, found
