"""Every Python file in the repository is fully typed: mypy, strict (mypy.ini), finds nothing.

The helpers, the plugin and the example run inside Designer, so they are checked against Designer's
own `sd` package and the PySide6 stubs it bundles, found in the Designer install (SD_DESIGNER_APP or
the default location, as launch_designer finds it). Without Designer those imports count as Any, so
the ignores written for sd calls go unused, sd values return Any and a QObject subclass subclasses Any: the check
then drops those three warnings for the whole repository, and keeps the rest of strict mode."""

import glob
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from docs_text import repo_files

from conftest import ROOT, mypy_config, mypy_files
from project_constants import MIN_PYTHON
from server_tools.lifecycle import DESIGNER_APP


def designer_packages() -> dict[str, str]:
    """{'sd': folder, 'PySide6': folder, 'shiboken6': folder} from the Designer install; {} without one."""
    app = os.environ.get('SD_DESIGNER_APP') or DESIGNER_APP.get(sys.platform)
    if not app or not os.path.exists(app):
        return {}
    root = app if os.path.isdir(app) else os.path.dirname(app)  # the macOS .app, or the folder of the .exe
    sd = glob.glob(os.path.join(glob.escape(root), '**', 'sd', 'api', 'sdnode.py'), recursive=True)
    qt = glob.glob(os.path.join(glob.escape(root), '**', 'site-packages', 'PySide6', 'QtCore.pyi'), recursive=True)
    found = {}
    if sd:
        found['sd'] = os.path.dirname(os.path.dirname(sd[0]))
    if qt:
        site = os.path.dirname(os.path.dirname(qt[0]))
        found['PySide6'] = os.path.join(site, 'PySide6')
        if os.path.isdir(os.path.join(site, 'shiboken6')):
            found['shiboken6'] = os.path.join(site, 'shiboken6')
    return found


def test_mypy_strict_finds_nothing(tmp_path: Path) -> None:
    _assert_mypy_finds_nothing(tmp_path, designer_packages())


def test_mypy_finds_nothing_without_designer(tmp_path: Path) -> None:
    """A fresh clone on a machine without Designer (REVIEW.md TST-131): sd and PySide6 are Any there."""
    _assert_mypy_finds_nothing(tmp_path, {})


def test_mypy_checks_as_the_minimum_python() -> None:
    """Every file, the scripts a user starts included, uses what the minimum Python has (DECISIONS.md, Project rules)."""
    assert mypy_config()['python_version'] == '%d.%d' % MIN_PYTHON


def test_mypy_reaches_the_python_files_in_hidden_folders() -> None:
    """mypy's search of `files = .` skips every folder whose name starts with a dot, such as `.claude`, so mypy.ini
    names each such folder that holds Python files (`.claude/hooks`). It doesn't name all of `.claude`: Claude Code
    makes its worktrees in `.claude/worktrees/`, each with a copy of every module, and mypy stops on the duplicates
    (REVIEW.md TST-558)."""
    named = [entry.rstrip('/') + '/' for entry in mypy_files() if entry != '.']
    assert [entry for entry in named if '.claude/worktrees/'.startswith(entry)] == []
    excluded = re.compile(mypy_config()['exclude'])
    hidden = [
        path
        for path in (name.replace(os.sep, '/') for name in repo_files())
        if path.endswith('.py')
        and any(part.startswith('.') for part in path.split('/')[:-1])
        and not excluded.search(path)
    ]
    assert '.claude/hooks/large_reads.py' in hidden
    assert [path for path in hidden if not path.startswith(tuple(named))] == []


def _assert_mypy_finds_nothing(tmp_path: Path, packages: dict[str, str]) -> None:
    # Designer's packages sit next to its whole site-packages, which mypy refuses on its path:
    # link just these three into a folder of their own
    for name, folder in packages.items():
        try:
            (tmp_path / name).symlink_to(folder, target_is_directory=True)
        except OSError:  # Windows without symlink rights: copy the sources and stubs only
            shutil.copytree(
                folder,
                tmp_path / name,
                ignore=lambda d, names: [
                    n for n in names if not os.path.isdir(os.path.join(d, n)) and not n.endswith(('.py', '.pyi'))
                ],
            )
    relaxed = (
        [] if 'sd' in packages else ['--no-warn-unused-ignores', '--no-warn-return-any', '--allow-subclassing-any']
    )
    result = _mypy(tmp_path, *relaxed, env=dict(os.environ, MYPYPATH=str(tmp_path)))
    assert result.returncode == 0, result.stdout + result.stderr


def _mypy(tmp_path: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """mypy run from the repository's root, where it finds mypy.ini, with a cache in tmp_path. Its output is never
    coloured, so a test can read it (REVIEW.md TST-499)."""
    if importlib.util.find_spec('mypy') is None:
        pytest.fail(
            'mypy is not installed: mcp_server/venv/bin/python -m pip install -r mcp_server/requirements-dev.txt'
        )
    return subprocess.run(
        [sys.executable, '-m', 'mypy', '--no-color-output', '--cache-dir', str(tmp_path / '.cache'), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


# Each line ending in '# reported' must draw mypy's explicit-any error, and no other line any error
_ANY_PROBE = dedent("""\
    import json
    from collections import defaultdict
    from collections.abc import Callable
    from typing import Any, cast

    a: Any = 1  # reported
    b: dict[str, Any] = {}  # reported
    c: Callable[..., int] = len  # reported
    d = cast(Any, 1)  # reported
    Pair = tuple[str, Any]  # reported
    e: Any = 1  # type: ignore[explicit-any]  # the mark `.claude/rules/python.md` asks for
    f = json.loads('1')
    g = defaultdict[str, Any](int)  # an Any inside an expression (REVIEW.md TST-497)


    def h(x: Any) -> None: ...  # reported


    def i(  # type: ignore[explicit-any]  # on the def line of a signature over several lines (REVIEW.md TST-496)
        x: Any,
    ) -> None: ...
    """)


def test_mypy_refuses_an_explicit_any(tmp_path: Path) -> None:
    """mypy.ini's disallow_any_explicit (ROADMAP item 99): mypy reports an Any written in an annotation, a signature, a
    cast or a type alias, the ... of Callable[..., T] included. `.claude/rules/python.md`'s mark silences one, on a function's def
    line. mypy doesn't report an Any inside an expression, nor one that comes in implicitly."""
    probe = tmp_path / 'probe.py'
    probe.write_text(_ANY_PROBE, encoding='utf-8')
    # Colour forced, as a user's FORCE_COLOR or MYPY_FORCE_COLOR does even into a pipe: the output must stay plain text
    # (REVIEW.md TST-499). mypy reads MYPY_FORCE_COLOR first
    result = _mypy(tmp_path, str(probe), env=dict(os.environ, MYPY_FORCE_COLOR='1'))
    errors: set[tuple[str, str]] = set(
        re.findall(r'probe\.py:(\d+): error: .*\[([a-z-]+)\]$', result.stdout, re.MULTILINE)
    )
    expected = {
        (str(n), 'explicit-any') for n, line in enumerate(_ANY_PROBE.splitlines(), 1) if line.endswith('# reported')
    }
    assert errors == expected, result.stdout + result.stderr


def test_designer_packages_found_when_designer_is_installed() -> None:
    """The check above only covers the Designer-side code against the real sd API when the lookup works."""
    app = os.environ.get('SD_DESIGNER_APP') or DESIGNER_APP.get(sys.platform)
    if not app or not os.path.exists(app):
        pytest.skip('Designer is not installed here')
    found = designer_packages()
    assert os.path.isfile(os.path.join(found['sd'], 'api', 'sdnode.py'))
    assert os.path.isfile(os.path.join(found['PySide6'], 'QtCore.pyi'))


def _iml_source_roots() -> list[str]:
    with open(os.path.join(ROOT, '.idea', 'substance-designer-mcp.iml'), encoding='utf-8') as f:
        return re.findall(r'<sourceFolder url="file://([^"]+)"', f.read())


def _dead_roots(roots: list[str], found: dict[str, str], app: str) -> list[str]:
    """The folders holding Designer's packages that the source roots miss, for an install where the repo's paths
    apply. Elsewhere, a person adds their own (README.md, Working in PyCharm)."""
    return [
        os.path.dirname(folder)
        for name, folder in found.items()
        if name in ('sd', 'PySide6') and folder.startswith(app + '/') and os.path.dirname(folder) not in roots
    ]


def test_pycharm_reads_designers_own_packages() -> None:
    """The venv has neither sd nor PySide6, so .idea marks Designer's folders as source roots: interpreter paths alone
    leave PySide6's names unresolved (README.md, Working in PyCharm). The roots hold what this install has, when it
    is at the default location."""
    roots = _iml_source_roots()
    app = DESIGNER_APP['darwin']
    assert app + '/Contents/Resources/python' in roots
    assert app + '/Contents/plugins/pythonsdk/lib/python3.13/site-packages' in roots
    assert not _dead_roots(roots, designer_packages(), app)


def test_a_designer_update_that_moves_its_packages_is_noticed() -> None:
    """REVIEW.md TST-123: a new Python folder in Designer leaves the .iml's root dead."""
    app = DESIGNER_APP['darwin']
    moved = app + '/Contents/plugins/pythonsdk/lib/python3.14/site-packages'
    found = {
        'sd': app + '/Contents/Resources/python/sd',
        'PySide6': moved + '/PySide6',
        'shiboken6': moved + '/shiboken6',
    }
    assert _dead_roots(_iml_source_roots(), found, app) == [moved]
    assert not _dead_roots(_iml_source_roots(), {'PySide6': '/elsewhere/site-packages/PySide6'}, app)
