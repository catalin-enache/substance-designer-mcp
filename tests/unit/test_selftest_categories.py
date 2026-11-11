"""tests/test_all_tools/categories.py: the one list of the live self-test's categories, read by the index and by
the pool (workers.py). No category requires another (category_run.py): each prepares its own environment
(test_selftest_preparations.py). No Designer."""

import importlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from conftest import SELFTEST_DIR


def _categories() -> Any:  # a module imported by name: PyCharm can't see its names
    """categories.py imported afresh with the self-test's modules, as the index and the pool import it."""
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    for name in [m for m in sys.modules if m == 'test_all_tools' or m.startswith('test_all_tools.')]:
        del sys.modules[name]
    return importlib.import_module('test_all_tools.categories')


def test_the_index_runs_the_declared_categories() -> None:
    categories = _categories()
    index = importlib.import_module('test_all_tools.__main__')
    assert index.CATEGORIES is categories.CATEGORIES


def test_every_category_but_lifecycle_is_listed_once_by_its_run() -> None:
    categories = _categories()
    names = [categories.category_name(step) for step in categories.CATEGORIES]
    folders = sorted(n for n in os.listdir(SELFTEST_DIR) if Path(SELFTEST_DIR, n, 'checks.py').is_file())
    assert sorted(names) == sorted(set(folders) - {'lifecycle'}), 'each one whole: its run(ctx)'


@pytest.mark.parametrize(
    'module',
    [
        '__main__',
        *sorted(
            os.path.relpath(os.path.join(folder, name), SELFTEST_DIR)[:-3].replace(os.sep, '.')
            for folder, _, names in os.walk(SELFTEST_DIR)
            if 'designer_scripts' not in folder
            for name in names
            if name.endswith('.py') and name != '__main__.py' and 'project_constants' in Path(folder, name).read_text()
        ),
    ],
)
def test_a_module_imports_first_in_a_fresh_interpreter(module: str) -> None:
    # `python tests/test_all_tools` stopped at its first import: project_constants was on the path only once common.py
    # had been imported, which the order of the index's imports happened to give. The unit tests' own path hides that
    code = 'import sys; sys.path.insert(0, %r); import test_all_tools.%s' % (os.path.dirname(SELFTEST_DIR), module)
    done = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd='/', env={})
    assert done.returncode == 0, done.stderr


# what touches the machine's one clipboard: a 3D screenshot (it goes through the clipboard), Qt's clipboard, or the
# self-test's own clipboard helpers
USES_THE_CLIPBOARD = re.compile(r"'panel':\s*'3d'|\.clipboard\(\)|\bclipboard_text\(|\bset_clipboard_text\(")


def test_the_clipboard_group_is_the_categories_that_use_the_clipboard() -> None:
    # never two of them at once in a pool, and no other category held back with them (REVIEW.md TST-241)
    categories = _categories()
    using = {
        folder.name
        for folder in Path(SELFTEST_DIR).iterdir()
        if (folder / 'checks.py').exists()
        and any(USES_THE_CLIPBOARD.search(f.read_text(encoding='utf-8')) for f in folder.rglob('*.py'))
    }
    assert using == set(categories.CLIPBOARD)
