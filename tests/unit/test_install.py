"""install.py, with everything that would change this machine (pip, venv, claude, the user's
skills folder) intercepted."""
import filecmp
import importlib.util
import os
import re
import sys

import pytest

from conftest import ROOT
from project_constants import PLUGIN, PLUGIN_DIR, PLUGIN_PACKAGE_DIR


@pytest.fixture
def install(monkeypatch, tmp_path_factory):
    spec = importlib.util.spec_from_file_location('install', os.path.join(ROOT, 'install.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    skills = str(tmp_path_factory.mktemp('skills'))
    monkeypatch.setattr(module, 'default_skills_dir', lambda: skills)
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
    (tmp_path / PLUGIN / 'pluginInfo.json').write_bytes(open(os.path.join(PLUGIN_DIR, 'pluginInfo.json'), 'rb').read())
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


def _skill(module):
    return os.path.join(module.default_skills_dir(), module.SERVER_NAME, 'SKILL.md')


def test_adds_the_skill_with_this_folders_paths(install, monkeypatch, tmp_path, capsys):
    module, _ = install
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    with open(_skill(module), encoding='utf-8') as f:
        text = f.read()
    # frontmatter Claude Code reads: name + a description that says when to load it
    head = text.split('---')[1]
    assert 'name: substance-designer\n' in head and 'description: ' in head and 'Substance 3D Designer' in head
    assert module.SKILL_MARKER in text
    assert os.path.join(ROOT, 'mcp_server', 'server.py') in text and '--scope local' in text
    assert os.path.join(ROOT, 'uninstall.py') in text
    assert 'Claude Code skill added' in capsys.readouterr().out


def test_rerun_replaces_its_own_skill(install, monkeypatch, tmp_path):
    module, _ = install
    os.makedirs(os.path.dirname(_skill(module)))
    with open(_skill(module), 'w', encoding='utf-8') as f:
        f.write('stale\n' + module.SKILL_MARKER)
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    with open(_skill(module), encoding='utf-8') as f:
        assert 'stale' not in f.read()


def test_leaves_someone_elses_skill_alone(install, monkeypatch, tmp_path, capsys):
    module, _ = install
    os.makedirs(os.path.dirname(_skill(module)))
    with open(_skill(module), 'w', encoding='utf-8') as f:
        f.write('my own skill')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    with open(_skill(module), encoding='utf-8') as f:
        assert f.read() == 'my own skill'
    assert 'left as it is' in capsys.readouterr().out


def test_no_skill_flag(install, monkeypatch, tmp_path):
    module, _ = install
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path), '--no-skill')
    assert not os.path.exists(os.path.dirname(_skill(module)))


def test_skills_dir_follows_claude_config_dir(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location('install_env', os.path.join(ROOT, 'install.py'))
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    monkeypatch.setenv('CLAUDE_CONFIG_DIR', str(tmp_path))
    assert fresh.default_skills_dir() == os.path.join(str(tmp_path), 'skills')


def _skill_commands(text):
    """The registration command (the code block) and the uninstall command (last backticks)."""
    register = text.split('```\n', 2)[1].strip()
    uninstall = re.findall(r'`([^`]*uninstall\.py[^`]*)`', text)[-1]
    return register, uninstall


@pytest.mark.parametrize('platform, repo', [('darwin', '/Users/me/My Tools/sd mcp'),
                                            ('win32', r'C:\Users\me\My Tools\sd-mcp')])
def test_skill_commands_survive_a_posix_shell(install, monkeypatch, platform, repo):
    # REVIEW.md INS-4: Claude Code's Bash tool is a POSIX shell everywhere (Git Bash on Windows),
    # which drops unquoted backslashes and splits on spaces
    import shlex
    module, _ = install
    monkeypatch.setattr(module.sys, 'platform', platform)
    sep = '\\' if platform == 'win32' else '/'
    monkeypatch.setattr(module, 'HERE', repo)
    py = sep.join([repo, 'mcp_server', 'venv', 'Scripts', 'python.exe'] if platform == 'win32'
                  else [repo, 'mcp_server', 'venv', 'bin', 'python'])
    server_py = sep.join([repo, 'mcp_server', 'server.py'])
    register, uninstall = _skill_commands(module.skill_text(py, server_py))
    as_posix = lambda p: p.replace('\\', '/')
    assert shlex.split(register)[-2:] == [as_posix(py), as_posix(server_py)]
    assert shlex.split(uninstall)[-1] == as_posix(sep.join([repo, 'uninstall.py']))


def test_reports_the_venvs_python(install, monkeypatch, tmp_path, capsys):
    # REVIEW.md INS-11: which Python the server runs on was nowhere to be seen
    module, _ = install
    monkeypatch.setattr(module.subprocess, 'check_output', lambda cmd, **kw: 'Python 3.12.10\n')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert any(l.startswith('[2/4]') and 'Python 3.12.10' in l for l in capsys.readouterr().out.splitlines())


def test_rerun_removes_files_dropped_from_the_plugin(install, monkeypatch, tmp_path):
    # REVIEW.md INS-10: copytree(dirs_exist_ok=True) kept stale modules importable
    module, _ = install
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))     # an earlier install of ours
    stale = tmp_path / PLUGIN / PLUGIN / 'old_module.py'
    stale.write_text('# from an older version')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert not stale.exists() and (tmp_path / PLUGIN / PLUGIN / '__init__.py').exists()


def test_every_requirement_has_a_tested_range():
    # REVIEW.md INS-9: an unbounded pillow or numpy lets a later install pick up a major version
    # nobody has tested; each line gives a lower bound and an upper bound below the next major
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        'mcp_server', 'requirements.txt')
    with open(path, encoding='utf-8') as f:
        lines = [l.split('#')[0].strip() for l in f if l.split('#')[0].strip()]
    loose = [l for l in lines if not re.fullmatch(r'[\w-]+>=[\d.]+,<\d+', l)]
    assert lines and not loose, 'requirements without a tested range: %s' % loose


def test_leaves_someone_elses_plugin_folder_alone(install, monkeypatch, tmp_path, capsys):
    # REVIEW.md INS-12: the installer deleted any folder with the plugin's name, while the
    # uninstaller leaves one whose pluginInfo.json isn't ours
    module, _ = install
    foreign = tmp_path / PLUGIN
    foreign.mkdir()
    (foreign / 'pluginInfo.json').write_text('{"name": "someone else"}')
    (foreign / 'theirs.py').write_text('keep me')
    with pytest.raises(SystemExit) as stop:
        _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert 'not this project' in str(stop.value)
    assert (foreign / 'theirs.py').read_text() == 'keep me'


def test_a_failed_copy_keeps_the_installed_plugin(install, monkeypatch, tmp_path):
    # REVIEW.md INS-12: the old plugin was deleted before the new one was copied, so a failing
    # copy (disk full, a locked file) left no plugin at all
    module, _ = install
    installed = tmp_path / PLUGIN
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    marker = installed / PLUGIN / 'installed_before.txt'
    marker.write_text('previous install')

    def failing_copy(src, dst, **kw):
        os.makedirs(dst)
        raise OSError('disk full')
    monkeypatch.setattr(module.shutil, 'copytree', failing_copy)
    with pytest.raises(OSError):
        _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert marker.read_text() == 'previous install'
    assert sorted(os.listdir(tmp_path)) == [PLUGIN]            # nothing half-copied left beside it


@pytest.mark.parametrize('failing_rename', [1, 2])
def test_a_failed_swap_rolls_back(install, monkeypatch, tmp_path, failing_rename):
    # REVIEW.md INS-16: a failing rename (Windows: a handle open in the folder) left <name>.new
    # beside the plugin, or no plugin at all with .new and .old beside it
    module, _ = install
    installed = tmp_path / PLUGIN
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    marker = installed / PLUGIN / 'installed_before.txt'
    marker.write_text('previous install')
    renames, real_rename = [], os.rename

    def rename(a, b):
        renames.append((a, b))
        if len(renames) == failing_rename:
            raise PermissionError('folder in use')
        real_rename(a, b)
    monkeypatch.setattr(module.os, 'rename', rename)
    with pytest.raises(OSError):
        _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    monkeypatch.setattr(module.os, 'rename', real_rename)
    assert marker.read_text() == 'previous install'          # the old plugin is back in place
    assert sorted(os.listdir(tmp_path)) == [PLUGIN]           # no .new or .old left beside it


def test_a_failed_rollback_still_removes_the_new_copy_and_says_where_the_old_one_is(install, monkeypatch,
                                                                                    tmp_path, capsys):
    # REVIEW.md INS-19: when renaming the old plugin back failed too, the new copy was never removed
    module, _ = install
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    renames, real_rename = [], os.rename

    def rename(a, b):
        renames.append((a, b))
        if len(renames) >= 2:                                  # the swap's second rename, then the rollback
            raise PermissionError('folder in use')
        real_rename(a, b)
    monkeypatch.setattr(module.os, 'rename', rename)
    with pytest.raises(OSError):
        _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert not (tmp_path / (PLUGIN + '.new')).exists()
    assert (tmp_path / (PLUGIN + '.old')).exists() and PLUGIN + '.old' in capsys.readouterr().out


def test_refuses_a_leftover_copy_that_isnt_ours(install, monkeypatch, tmp_path):
    # REVIEW.md INS-21: a <plugin>.new or .old that isn't ours stops the installer, untouched
    module, _ = install
    foreign = tmp_path / (PLUGIN + '.new')
    foreign.mkdir()
    (foreign / 'theirs.txt').write_text('keep me')
    with pytest.raises(SystemExit) as stop:
        _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert 'not this project' in str(stop.value) and 'partly deleted' in str(stop.value)   # INS-20
    assert (foreign / 'theirs.txt').read_text() == 'keep me'


def test_reports_an_old_copy_it_could_not_remove(install, monkeypatch, tmp_path, capsys):
    # REVIEW.md INS-21: the "could not remove" note had no test
    module, _ = install
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    real_rmtree = module.shutil.rmtree
    monkeypatch.setattr(module.shutil, 'rmtree', lambda path, ignore_errors=False: None
                        if str(path).endswith('.old') else real_rmtree(path, ignore_errors=ignore_errors))
    capsys.readouterr()
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert 'could not remove' in capsys.readouterr().out
