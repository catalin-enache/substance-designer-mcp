"""The plugin's name lives only in project_constants.py (plus the two plugin folders, which
Designer loads by name). A rename = change PLUGIN, rename the folders, and these tests point at
anything left over."""

import os
import subprocess

import pytest

from conftest import ROOT
from project_constants import PLUGIN, PLUGIN_DIR, PLUGIN_PACKAGE_DIR, TOKEN_FILE


def test_plugin_folders_match_the_constant() -> None:
    # hidden files left out: Finder writes .DS_Store into any folder it shows (REVIEW.md TST-79)
    assert [n for n in os.listdir(os.path.join(ROOT, 'plugin')) if not n.startswith('.')] == [PLUGIN]
    assert os.path.isfile(os.path.join(PLUGIN_DIR, 'pluginInfo.json'))
    assert os.path.isfile(os.path.join(PLUGIN_PACKAGE_DIR, '__init__.py'))


def test_plugin_takes_its_name_from_its_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util
    import sys
    import types

    qtcore = types.SimpleNamespace(QTimer=object)
    monkeypatch.setitem(sys.modules, 'PySide6', types.SimpleNamespace(QtCore=qtcore))
    monkeypatch.setitem(sys.modules, 'PySide6.QtCore', qtcore)
    spec = importlib.util.spec_from_file_location('plugin_name_check', os.path.join(PLUGIN_PACKAGE_DIR, '__init__.py'))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.NAME == PLUGIN and module.TOKEN_FILE == TOKEN_FILE


def test_no_code_spells_out_the_name() -> None:
    tracked = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True).stdout.split()
    untracked = subprocess.run(
        ['git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT, capture_output=True, text=True
    ).stdout.split()
    offenders = []
    for rel in tracked + untracked:
        if rel == 'project_constants.py' or not rel.endswith(('.py', '.json', '.txt', '.cfg', '.toml', '.ini')):
            continue
        path = os.path.join(ROOT, rel)
        if os.path.isfile(path):
            with open(path, encoding='utf-8', errors='replace') as f:
                if PLUGIN in f.read():
                    offenders.append(rel)
    assert not offenders, 'use project_constants.PLUGIN instead of spelling the name out in: %s' % offenders


def test_docs_mention_the_current_name() -> None:
    for doc in ('README.md', 'AGENTS.md'):
        with open(os.path.join(ROOT, doc), encoding='utf-8') as f:
            text = f.read()
        assert PLUGIN in text and os.path.basename(TOKEN_FILE) in text, doc
