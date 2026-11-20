"""Every Python file in the repository passes ruff's lint rules and is formatted by ruff (ruff.toml)."""

import importlib.util
import subprocess
import sys

import pytest
from windows_simulation import POSIX_ONLY

from conftest import ROOT, VERSION_CHECKED, mypy_files
from project_constants import MIN_PYTHON


def _ruff(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    if importlib.util.find_spec('ruff') is None:
        pytest.fail(
            'ruff is not installed: mcp_server/venv/bin/python -m pip install -r mcp_server/requirements-dev.txt'
        )
    return subprocess.run([sys.executable, '-m', 'ruff', *args], cwd=ROOT, input=stdin, capture_output=True, text=True)


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


@pytest.mark.parametrize(('args', 'source'), [(('check',), 'import os\n'), (('format', '--check'), 'x=1\n')])
def test_ruff_skips_claude_codes_worktrees(args: tuple[str, ...], source: str) -> None:
    # Claude Code makes its worktrees in `.claude/worktrees/`, copies of every module: `ruff check --fix .` would lint
    # and rewrite their files, and test_lint.py fail on a worktree's unfinished one (REVIEW.md TST-634). The source,
    # sent as a file of that path, fails the command anywhere else. mypy skips them too (test_types.py)
    for path, skipped in (('.claude/worktrees/w/x.py', True), ('tests/unit/x.py', False)):
        result = _ruff(*args, '--no-cache', '--force-exclude', '--stdin-filename', path, '-', stdin=source)
        assert (result.returncode == 0) == skipped, (path, result.stdout + result.stderr)


def test_every_file_is_formatted() -> None:
    result = _ruff('format', '--check', '--no-cache', '.')
    assert result.returncode == 0, result.stdout + result.stderr + '\nRun: mcp_server/venv/bin/ruff format .'


def test_no_module_imports_a_posix_only_module_at_its_top() -> None:
    """The unit suite runs on Windows too (the `live-check` skill, The suites), and so do the server, the self-test and the
    plugin, inside Designer, and the lead's hook: a POSIX-only module imported where a file starts stops it from loading
    there (REVIEW.md TST-356, TST-369, TST-634). Import it inside the function or test that needs it."""
    import ast
    import os

    found = []
    for path in _own_python_files():
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


def _own_python_files() -> list[str]:
    """The repository's own Python files: not its tools' (.git, .claude's vendored skill, Claude Code's worktrees, the
    caches) nor the venv. Each walk skips the folders whose name starts with a dot, so it walks each folder that
    mypy.ini's `files` names: the repository's, and `.claude/hooks`. test_types.py checks that those folders hold every
    Python file of the repository's own in a hidden folder (REVIEW.md TST-634)."""
    import os

    found = []
    for top in mypy_files():
        for here, dirs, files in os.walk(os.path.normpath(os.path.join(ROOT, top))):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', '__pycache__', 'node_modules')]
            found += [os.path.join(here, name) for name in files if name.endswith('.py')]
    return found


def test_the_posix_import_check_reads_the_hooks() -> None:
    # REVIEW.md TST-634: the hook is to run on Windows too (ROADMAP item 111), where a POSIX-only module at its top
    # stops it
    import os

    found = {os.path.relpath(path, ROOT) for path in _own_python_files()}
    assert {os.path.join('.claude', 'hooks', name) for name in ('large_reads.py', 'command_lines.py')} <= found
