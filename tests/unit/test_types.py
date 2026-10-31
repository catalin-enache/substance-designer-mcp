"""Every Python file in the repository is fully typed: mypy, strict (mypy.ini), finds nothing.

The helpers, the plugin and the example run inside Designer, so they are checked against Designer's
own `sd` package and the PySide6 stubs it bundles, found in the Designer install (SD_DESIGNER_APP or
the default location, as launch_designer finds it). Without Designer those imports count as Any, so
the ignores written for sd calls go unused and sd values return Any: the check then drops those two
warnings (unused ignores, Any returns) for the whole repository, and keeps the rest of strict mode."""

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import ROOT
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
    try:
        import mypy  # noqa: F401
    except ImportError:
        pytest.fail(
            'mypy is not installed: mcp_server/venv/bin/python -m pip install -r mcp_server/requirements-dev.txt'
        )
    # Designer's packages sit next to its whole site-packages, which mypy refuses on its path:
    # link just these three into a folder of their own
    packages = designer_packages()
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
    env = dict(os.environ, MYPYPATH=str(tmp_path))
    relaxed = [] if 'sd' in packages else ['--no-warn-unused-ignores', '--no-warn-return-any']
    result = subprocess.run(
        [sys.executable, '-m', 'mypy', '--cache-dir', str(tmp_path / '.cache'), *relaxed],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_designer_packages_found_when_designer_is_installed() -> None:
    """The check above only covers the Designer-side code against the real sd API when the lookup works."""
    app = os.environ.get('SD_DESIGNER_APP') or DESIGNER_APP.get(sys.platform)
    if not app or not os.path.exists(app):
        pytest.skip('Designer is not installed here')
    found = designer_packages()
    assert os.path.isfile(os.path.join(found['sd'], 'api', 'sdnode.py'))
    assert os.path.isfile(os.path.join(found['PySide6'], 'QtCore.pyi'))
