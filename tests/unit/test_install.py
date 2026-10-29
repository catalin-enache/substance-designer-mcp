"""install.py, with everything that would change this machine (pip, venv, claude) intercepted."""
import filecmp
import importlib.util
import os
import sys

import pytest

from conftest import ROOT
from project_constants import PLUGIN, PLUGIN_DIR, PLUGIN_PACKAGE_DIR


@pytest.fixture
def install(monkeypatch):
    spec = importlib.util.spec_from_file_location('install', os.path.join(ROOT, 'install.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    monkeypatch.setattr(module.subprocess, 'check_call', lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setattr(module.subprocess, 'call', lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setattr(module.os.path, 'exists', lambda p, _real=os.path.exists: True if p.endswith(
        ('bin%spython' % os.sep, 'python.exe')) else _real(p))
    return module, calls


def _run(module, monkeypatch, *args):
    monkeypatch.setattr(sys, 'argv', ['install.py', *args])
    module.main()


def test_copies_the_plugin(install, monkeypatch, tmp_path, capsys):
    module, calls = install
    monkeypatch.setattr(module.shutil, 'which', lambda name: None)
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    src = PLUGIN_DIR
    cmp = filecmp.dircmp(src, str(tmp_path / PLUGIN), ignore=['__pycache__'])
    assert not (cmp.left_only or cmp.diff_files)
    assert not cmp.subdirs[PLUGIN].left_only and not cmp.subdirs[PLUGIN].diff_files
    assert not (tmp_path / PLUGIN / PLUGIN / '__pycache__').exists()
    # requirements installed into the project venv; nothing registered
    assert any('-r' in c and c[-1].endswith(os.path.join('mcp_server', 'requirements.txt')) for c in calls)


def test_rerun_updates_in_place(install, monkeypatch, tmp_path):
    module, _ = install
    monkeypatch.setattr(module.shutil, 'which', lambda name: None)
    stale = tmp_path / PLUGIN / PLUGIN / '__init__.py'
    stale.parent.mkdir(parents=True)
    stale.write_text('old')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    with open(os.path.join(PLUGIN_PACKAGE_DIR, '__init__.py')) as f:
        assert stale.read_text() == f.read()


def test_never_registers_globally(install, monkeypatch, tmp_path, capsys):
    # registration is per folder: this repo's .mcp.json, or `claude mcp add --scope local` elsewhere
    module, calls = install
    monkeypatch.setattr(module.shutil, 'which', lambda name: '/usr/local/bin/claude')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert not any('claude' in os.path.basename(str(c[0])) for c in calls)
    out = capsys.readouterr().out
    assert 'Not registered globally' in out and '.mcp.json' in out and '--scope local' in out


def _old_plugin(root, name):
    folder = root / 'sd_bridge'
    (folder / 'sd_bridge').mkdir(parents=True)
    (folder / 'pluginInfo.json').write_text('{"name": "%s"}' % name)
    return folder


def test_removes_this_projects_old_plugin_and_token(install, monkeypatch, tmp_path):
    module, _ = install
    monkeypatch.setattr(module.shutil, 'which', lambda name: None)
    token = tmp_path / 'old_token'
    token.write_text('x' * 64)
    monkeypatch.setattr(module, 'OLD_TOKEN', str(token))
    old = _old_plugin(tmp_path, 'SD Bridge (local script runner)')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert not old.exists() and not token.exists()
    assert (tmp_path / PLUGIN / PLUGIN / '__init__.py').exists()


def test_leaves_someone_elses_sd_bridge_alone(install, monkeypatch, tmp_path):
    module, _ = install
    monkeypatch.setattr(module.shutil, 'which', lambda name: None)
    token = tmp_path / 'old_token'
    token.write_text('x' * 64)
    monkeypatch.setattr(module, 'OLD_TOKEN', str(token))
    other = _old_plugin(tmp_path, 'Some other bridge')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert other.exists() and token.exists()
