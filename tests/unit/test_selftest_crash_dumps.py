"""tests/test_all_tools/common.py's crash_dumps: a Designer launch_designer starts on macOS writes its crash dumps in a
home of its own (CFFIXED_USER_HOME), so the checks that no dump appeared look there as well as in the user's."""

import importlib
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from conftest import SELFTEST_DIR

DUMPS = 'Library/Application Support/Adobe/Adobe Substance 3D Designer/Sentry-Crashpad/completed'


def _common() -> Any:  # a module imported by name: PyCharm can't see its names
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    return importlib.import_module('test_all_tools.common')


pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='no os.getuid there, and no agent folders')


def test_crash_dumps_include_those_of_the_runs_own_designers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    common = _common()
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setenv('HOME', str(tmp_path / 'user'))
    monkeypatch.setitem(vars(common), 'SHORT_TEMP', str(tmp_path))
    monkeypatch.setitem(vars(common), 'PORT', 9901)  # the run's
    users = tmp_path / 'user' / DUMPS
    runs = tmp_path / ('sd_mcp_%d_9901' % os.getuid()) / 'home' / DUMPS
    # another run's, side by side (REVIEW.md TST-155): its crash isn't this run's, unless this run names its port
    beside = tmp_path / ('sd_mcp_%d_9902' % os.getuid()) / 'home' / DUMPS
    others = tmp_path / 'sd_mcp_0_9901' / 'home' / DUMPS  # another user's: not this run's
    for folder in (users, runs, beside, others):
        folder.mkdir(parents=True)
        (folder / 'a.dmp').write_text('')
    assert common.crash_dumps() == {str(users / 'a.dmp'), str(runs / 'a.dmp')}
    assert common.crash_dumps(ports=[9902]) == {str(users / 'a.dmp'), str(runs / 'a.dmp'), str(beside / 'a.dmp')}
    (beside / 'b.dmp').write_text('')
    assert common.new_crash_dumps(common.crash_dumps(), wait_s=0) == set()
    assert common.new_crash_dumps(set(), wait_s=0, ports=[9902]) >= {str(beside / 'b.dmp')}
