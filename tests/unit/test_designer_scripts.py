"""Designer scripts of the live self-test (tests/test_all_tools/<category>/designer_scripts/ and designer_scripts/shared/) that can be run with a stand-in for Designer's own packages:
what they do on a failure, which a passing self-test doesn't show."""

import os
import sys
import traceback
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from conftest import SELFTEST_DIR


def script_path(name: str) -> str:
    """common.script_path: where common.designer_script finds the script it sends."""
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    from test_all_tools.common import script_path as path_of

    return path_of(name)


def _run(name: str, args: dict[str, Any]) -> tuple[str, str]:
    """(what it printed, the traceback or ''), run as the plugin runs it: compiled with its own path, so a traceback
    shows its source lines."""
    path = script_path(name)  # the self-test's own (REVIEW.md TST-238: this built the path itself)
    with open(path, encoding='utf-8') as f:
        code = compile(f.read(), path, 'exec')
    printed: list[str] = []
    scope = {'ARGS': args, '__file__': path, 'print': lambda *a: printed.append(' '.join(str(x) for x in a))}
    try:
        exec(code, scope)
    except BaseException:
        return '\n'.join(printed), traceback.format_exc()
    return '\n'.join(printed), ''


def _stand_in(monkeypatch: pytest.MonkeyPatch, *names: str) -> dict[str, MagicMock]:
    """Every name as an importable module of mocks, its parents too."""
    made: dict[str, MagicMock] = {}
    for name in names:
        parts = name.split('.')
        for i in range(1, len(parts) + 1):
            full = '.'.join(parts[:i])
            if full not in made:
                made[full] = MagicMock(spec_set=None)
                monkeypatch.setitem(sys.modules, full, made[full])
            if i > 1:
                setattr(made['.'.join(parts[: i - 1])], parts[i - 1], made[full])
    return made


def test_a_failing_3d_grab_does_not_read_as_no_3d_view(monkeypatch: pytest.MonkeyPatch) -> None:
    """facts/checks.py reads NO_3D_VIEW in the result as no 3D view, and a traceback shows the failing source line
    (REVIEW.md TST-117): the token can't be on a line that can fail."""
    made = _stand_in(monkeypatch, 'sd', 'PySide6.QtWidgets')
    viewport = MagicMock()
    viewport.metaObject.return_value.className.return_value = 'Alg::Gui3D::ViewportWidget'
    viewport.grab.side_effect = RuntimeError('Internal C++ object already deleted')
    dock = MagicMock()
    dock.objectName.return_value = 'areaD_'
    dock.findChildren.return_value = [viewport]
    ui = made['sd'].getContext.return_value.getSDApplication.return_value.getQtForPythonUIMgr.return_value
    ui.getMainWindow.return_value.findChildren.return_value = [dock]
    printed, error = _run('facts/grab_3d_view', {'path': 'unused.png'})
    assert 'already deleted' in error
    assert 'NO_3D_VIEW' not in printed + error


def test_no_3d_view_is_still_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    made = _stand_in(monkeypatch, 'sd', 'PySide6.QtWidgets')
    ui = made['sd'].getContext.return_value.getSDApplication.return_value.getQtForPythonUIMgr.return_value
    ui.getMainWindow.return_value.findChildren.return_value = []
    printed, error = _run('facts/grab_3d_view', {'path': 'unused.png'})
    assert (printed, error) == ('NO_3D_VIEW', '')


def _package_uid_stand_in(monkeypatch: pytest.MonkeyPatch, file_text: str, uid: str) -> None:
    made = _stand_in(monkeypatch, 'sd', 'sd.api.sbs.sdsbscompgraph')
    pm = made['sd'].getContext.return_value.getSDApplication.return_value.getPackageMgr.return_value
    pm.newUserPackage.return_value.getUID.return_value = uid
    pm.loadUserPackage.return_value.getUID.return_value = uid

    def save(_pkg: Any, path: str) -> None:
        Path(path).write_text(file_text)

    pm.savePackageAs.side_effect = save
    pm.saveCopyOfPackageAs.side_effect = save


def test_a_file_without_a_uid_fails_the_fact(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Two empty UIDs must not compare as the same UID (REVIEW.md TST-122)."""
    _package_uid_stand_in(monkeypatch, '<package/>', '')
    printed, error = _run('facts/package_uid', {'folder': str(tmp_path)})
    assert 'SAME_UID=True' not in printed
    assert 'no <fileUID>' in error
    assert not (tmp_path / 'S.sbs').exists()


def test_a_file_with_the_uid_passes_the_fact(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _package_uid_stand_in(monkeypatch, '<package><fileUID v="{u}"/></package>', '{u}')
    printed, error = _run('facts/package_uid', {'folder': str(tmp_path)})
    assert not error
    assert 'SAME_UID=True' in printed
    assert 'COPY_KEEPS_UID=True' in printed
