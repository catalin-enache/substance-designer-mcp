"""install.py, with everything that would change this machine (pip, venv, claude) intercepted."""
import filecmp
import importlib.util
import os
import sys

import pytest

from conftest import ROOT


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
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path), '--no-register')
    src = os.path.join(ROOT, 'plugin', 'sd_bridge')
    cmp = filecmp.dircmp(src, str(tmp_path / 'sd_bridge'), ignore=['__pycache__'])
    assert not (cmp.left_only or cmp.diff_files)
    assert not cmp.subdirs['sd_bridge'].left_only and not cmp.subdirs['sd_bridge'].diff_files
    assert not (tmp_path / 'sd_bridge' / 'sd_bridge' / '__pycache__').exists()
    # requirements installed into the project venv; nothing registered
    assert any('-r' in c and c[-1].endswith(os.path.join('mcp_server', 'requirements.txt')) for c in calls)
    assert not any(c[0] == 'claude' for c in calls)
    assert 'Register manually with' in capsys.readouterr().out


def test_rerun_updates_in_place(install, monkeypatch, tmp_path):
    module, _ = install
    monkeypatch.setattr(module.shutil, 'which', lambda name: None)
    stale = tmp_path / 'sd_bridge' / 'sd_bridge' / '__init__.py'
    stale.parent.mkdir(parents=True)
    stale.write_text('old')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path), '--no-register')
    with open(os.path.join(ROOT, 'plugin', 'sd_bridge', 'sd_bridge', '__init__.py')) as f:
        assert stale.read_text() == f.read()


def test_registers_with_claude_code(install, monkeypatch, tmp_path):
    module, calls = install
    monkeypatch.setattr(module.shutil, 'which', lambda name: '/usr/local/bin/claude')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert ['claude', 'mcp', 'remove', 'substance-designer', '-s', 'user'] in calls
    add = next(c for c in calls if c[:3] == ['claude', 'mcp', 'add'])
    assert add[3:6] == ['--scope', 'user', 'substance-designer']
    assert add[-1] == os.path.join(ROOT, 'mcp_server', 'server.py')
