"""install.py, with everything that would change this machine (pip, venv, claude, the user's
skills folder) intercepted."""

import filecmp
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

from conftest import ROOT
from project_constants import PLUGIN, PLUGIN_DIR, PLUGIN_PACKAGE_DIR

Install = tuple[types.ModuleType, list[list[str]]]  # the install fixture: install.py's module, the commands it ran


@pytest.fixture
def install(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> Install:
    spec = importlib.util.spec_from_file_location('install', os.path.join(ROOT, 'install.py'))
    assert spec is not None and spec.loader is not None  # a .py file that exists
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    skills = str(tmp_path_factory.mktemp('skills'))
    monkeypatch.setitem(vars(module), 'default_skills_dir', lambda: skills)
    calls: list[list[str]] = []
    monkeypatch.setattr(subprocess, 'check_call', lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setattr(subprocess, 'call', lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setitem(
        vars(os.path),
        'exists',
        lambda p, _real=os.path.exists: True if p.endswith(('bin%spython' % os.sep, 'python.exe')) else _real(p),
    )
    return module, calls


def _run(module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr(sys, 'argv', ['install.py', *args])
    module.main()


def test_copies_the_plugin(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    module, calls = install
    monkeypatch.setattr(shutil, 'which', lambda name: None)
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    src = PLUGIN_DIR
    cmp = filecmp.dircmp(src, str(tmp_path / PLUGIN), ignore=['__pycache__'])
    assert not (cmp.left_only or cmp.diff_files)
    assert not cmp.subdirs[PLUGIN].left_only and not cmp.subdirs[PLUGIN].diff_files
    assert not (tmp_path / PLUGIN / PLUGIN / '__pycache__').exists()
    # requirements installed into the project venv; nothing registered
    assert any('-r' in c and c[-1].endswith(os.path.join('mcp_server', 'requirements.txt')) for c in calls)


def test_rerun_updates_in_place(install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module, _ = install
    monkeypatch.setattr(shutil, 'which', lambda name: None)
    stale = tmp_path / PLUGIN / PLUGIN / '__init__.py'
    stale.parent.mkdir(parents=True)
    stale.write_text('old')
    (tmp_path / PLUGIN / 'pluginInfo.json').write_bytes(Path(PLUGIN_DIR, 'pluginInfo.json').read_bytes())
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    with open(os.path.join(PLUGIN_PACKAGE_DIR, '__init__.py')) as f:
        assert stale.read_text() == f.read()


def test_never_registers_globally(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # registration is per folder: this repo's .mcp.json, or `claude mcp add --scope local` elsewhere
    module, calls = install
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/local/bin/claude')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert not any('claude' in os.path.basename(str(c[0])) for c in calls)
    out = capsys.readouterr().out
    assert 'Not registered globally' in out and '.mcp.json' in out and '--scope local' in out


def _old_plugin(root: Path, name: str) -> Path:
    folder = root / 'sd_bridge'
    (folder / 'sd_bridge').mkdir(parents=True)
    (folder / 'pluginInfo.json').write_text('{"name": "%s"}' % name)
    return folder


def test_removes_this_projects_old_plugin_and_token(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module, _ = install
    monkeypatch.setattr(shutil, 'which', lambda name: None)
    token = tmp_path / 'old_token'
    token.write_text('x' * 64)
    monkeypatch.setitem(vars(module), 'OLD_TOKEN', str(token))
    old = _old_plugin(tmp_path, 'SD Bridge (local script runner)')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert not old.exists() and not token.exists()
    assert (tmp_path / PLUGIN / PLUGIN / '__init__.py').exists()


def test_leaves_someone_elses_sd_bridge_alone(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module, _ = install
    monkeypatch.setattr(shutil, 'which', lambda name: None)
    token = tmp_path / 'old_token'
    token.write_text('x' * 64)
    monkeypatch.setitem(vars(module), 'OLD_TOKEN', str(token))
    other = _old_plugin(tmp_path, 'Some other bridge')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert other.exists() and token.exists()


def _skill(module: types.ModuleType) -> str:
    path: str = os.path.join(module.default_skills_dir(), module.SERVER_NAME, 'SKILL.md')
    return path


def test_adds_the_skill_with_this_folders_paths(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
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


def test_rerun_replaces_its_own_skill(install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module, _ = install
    os.makedirs(os.path.dirname(_skill(module)))
    with open(_skill(module), 'w', encoding='utf-8') as f:
        f.write('stale\n' + module.SKILL_MARKER)
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    with open(_skill(module), encoding='utf-8') as f:
        assert 'stale' not in f.read()


def test_leaves_someone_elses_skill_alone(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    module, _ = install
    os.makedirs(os.path.dirname(_skill(module)))
    with open(_skill(module), 'w', encoding='utf-8') as f:
        f.write('my own skill')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    with open(_skill(module), encoding='utf-8') as f:
        assert f.read() == 'my own skill'
    assert 'left as it is' in capsys.readouterr().out


def test_no_skill_flag(install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module, _ = install
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path), '--no-skill')
    assert not os.path.exists(os.path.dirname(_skill(module)))


def test_skills_dir_follows_claude_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location('install_env', os.path.join(ROOT, 'install.py'))
    assert spec is not None and spec.loader is not None  # a .py file that exists
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    monkeypatch.setenv('CLAUDE_CONFIG_DIR', str(tmp_path))
    assert fresh.default_skills_dir() == os.path.join(str(tmp_path), 'skills')


def _skill_commands(text: str) -> tuple[str, str]:
    """The registration command (the code block) and the uninstall command (last backticks)."""
    register = text.split('```\n', 2)[1].strip()
    uninstall = re.findall(r'`([^`]*uninstall\.py[^`]*)`', text)[-1]
    return register, uninstall


@pytest.mark.parametrize(
    'platform, repo', [('darwin', '/Users/me/My Tools/sd mcp'), ('win32', r'C:\Users\me\My Tools\sd-mcp')]
)
def test_skill_commands_survive_a_posix_shell(
    install: Install, monkeypatch: pytest.MonkeyPatch, platform: str, repo: str
) -> None:
    # REVIEW.md INS-4: Claude Code's Bash tool is a POSIX shell everywhere (Git Bash on Windows),
    # which drops unquoted backslashes and splits on spaces
    import shlex

    module, _ = install
    monkeypatch.setattr(sys, 'platform', platform)
    sep = '\\' if platform == 'win32' else '/'
    monkeypatch.setitem(vars(module), 'HERE', repo)
    py = sep.join(
        [repo, 'mcp_server', 'venv', 'Scripts', 'python.exe']
        if platform == 'win32'
        else [repo, 'mcp_server', 'venv', 'bin', 'python']
    )
    server_py = sep.join([repo, 'mcp_server', 'server.py'])
    register, uninstall = _skill_commands(module.skill_text(py, server_py))

    def as_posix(p: str) -> str:
        return p.replace('\\', '/')

    assert shlex.split(register)[-2:] == [as_posix(py), as_posix(server_py)]
    assert shlex.split(uninstall)[-1] == as_posix(sep.join([repo, 'uninstall.py']))


def test_reports_the_venvs_python(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md INS-11: which Python the server runs on was nowhere to be seen
    module, _ = install
    monkeypatch.setattr(subprocess, 'check_output', lambda cmd, **kw: 'Python 3.12.10\n')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert any(l.startswith('[2/4]') and 'Python 3.12.10' in l for l in capsys.readouterr().out.splitlines())


def test_rerun_removes_files_dropped_from_the_plugin(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md INS-10: copytree(dirs_exist_ok=True) kept stale modules importable
    module, _ = install
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))  # an earlier install of ours
    stale = tmp_path / PLUGIN / PLUGIN / 'old_module.py'
    stale.write_text('# from an older version')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert not stale.exists() and (tmp_path / PLUGIN / PLUGIN / '__init__.py').exists()


def test_every_requirement_has_a_tested_range() -> None:
    # REVIEW.md INS-9: an unbounded pillow or numpy lets a later install pick up a major version
    # nobody has tested; each line gives a lower bound and an upper bound below the next major
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'mcp_server', 'requirements.txt'
    )
    with open(path, encoding='utf-8') as f:
        lines = [l.split('#')[0].strip() for l in f if l.split('#')[0].strip()]
    loose = [l for l in lines if not re.fullmatch(r'[\w-]+>=[\d.]+,<\d+', l)]
    assert lines and not loose, 'requirements without a tested range: %s' % loose


def test_leaves_someone_elses_plugin_folder_alone(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
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


def test_a_failed_copy_keeps_the_installed_plugin(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md INS-12: the old plugin was deleted before the new one was copied, so a failing
    # copy (disk full, a locked file) left no plugin at all
    module, _ = install
    installed = tmp_path / PLUGIN
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    marker = installed / PLUGIN / 'installed_before.txt'
    marker.write_text('previous install')

    def failing_copy(src: str, dst: str, **kw: object) -> None:
        os.makedirs(dst)
        raise OSError('disk full')

    monkeypatch.setattr(shutil, 'copytree', failing_copy)
    with pytest.raises(OSError):
        _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert marker.read_text() == 'previous install'
    assert sorted(os.listdir(tmp_path)) == [PLUGIN]  # nothing half-copied left beside it


@pytest.mark.parametrize('failing_rename', [1, 2])
def test_a_failed_swap_rolls_back(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failing_rename: int
) -> None:
    # REVIEW.md INS-16: a failing rename (Windows: a handle open in the folder) left <name>.new
    # beside the plugin, or no plugin at all with .new and .old beside it
    module, _ = install
    installed = tmp_path / PLUGIN
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    marker = installed / PLUGIN / 'installed_before.txt'
    marker.write_text('previous install')
    renames: list[tuple[str, str]] = []
    real_rename = os.rename

    def rename(a: str, b: str) -> None:
        renames.append((a, b))
        if len(renames) == failing_rename:
            raise PermissionError('folder in use')
        real_rename(a, b)

    monkeypatch.setattr(os, 'rename', rename)
    with pytest.raises(OSError):
        _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    monkeypatch.setattr(os, 'rename', real_rename)
    assert marker.read_text() == 'previous install'  # the old plugin is back in place
    assert sorted(os.listdir(tmp_path)) == [PLUGIN]  # no .new or .old left beside it


def test_a_failed_rollback_still_removes_the_new_copy_and_says_where_the_old_one_is(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md INS-19: when renaming the old plugin back failed too, the new copy was never removed
    module, _ = install
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    renames: list[tuple[str, str]] = []
    real_rename = os.rename

    def rename(a: str, b: str) -> None:
        renames.append((a, b))
        if len(renames) >= 2:  # the swap's second rename, then the rollback
            raise PermissionError('folder in use')
        real_rename(a, b)

    monkeypatch.setattr(os, 'rename', rename)
    with pytest.raises(OSError):
        _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert not (tmp_path / (PLUGIN + '.new')).exists()
    assert (tmp_path / (PLUGIN + '.old')).exists() and PLUGIN + '.old' in capsys.readouterr().out


def test_refuses_a_leftover_copy_that_isnt_ours(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md INS-21: a <plugin>.new or .old that isn't ours stops the installer, untouched
    module, _ = install
    foreign = tmp_path / (PLUGIN + '.new')
    foreign.mkdir()
    (foreign / 'theirs.txt').write_text('keep me')
    with pytest.raises(SystemExit) as stop:
        _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert 'not this project' in str(stop.value) and 'partly deleted' in str(stop.value)  # INS-20
    assert (foreign / 'theirs.txt').read_text() == 'keep me'


def test_reports_an_old_copy_it_could_not_remove(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md INS-21: the "could not remove" note had no test
    module, _ = install
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    real_rmtree = module.shutil.rmtree
    monkeypatch.setattr(
        shutil,
        'rmtree',
        lambda path, ignore_errors=False: (
            None if str(path).endswith('.old') else real_rmtree(path, ignore_errors=ignore_errors)
        ),
    )
    capsys.readouterr()
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path))
    assert 'could not remove' in capsys.readouterr().out


def _venv_with_python(
    module: types.ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, target: str | Path
) -> None:
    """A repo folder whose venv's python links to `target`; the installer pointed at it."""
    import genericpath  # the fixture fakes os.path.exists itself (on the real os module)

    monkeypatch.setitem(vars(os.path), 'exists', genericpath.exists)
    here = tmp_path / 'repo'
    bindir = here / 'mcp_server' / 'venv' / 'bin'
    bindir.mkdir(parents=True)
    (bindir / 'python').symlink_to(target)
    monkeypatch.setitem(vars(module), 'HERE', str(here))


@pytest.mark.skipif(sys.platform == 'win32', reason='a dangling symlink venv is the macOS/Linux case')
def test_rerun_repairs_a_venv_whose_python_is_gone(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md INS-23: after a Python upgrade the venv's python is a dangling link; `-m venv` over
    # it without --clear exits 0 and keeps the link, so pip then failed: the documented repair didn't
    module, calls = install
    _venv_with_python(module, monkeypatch, tmp_path, tmp_path / 'gone' / 'python3.12')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path / 'plugins'), '--no-skill')
    venv_calls = [c for c in calls if c[1:3] == ['-m', 'venv']]
    assert venv_calls and '--clear' in venv_calls[0], calls


@pytest.mark.skipif(sys.platform == 'win32', reason='symlinks')
def test_rerun_keeps_a_working_venv(install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module, calls = install
    _venv_with_python(module, monkeypatch, tmp_path, sys.executable)
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path / 'plugins'), '--no-skill')
    assert not [c for c in calls if c[1:3] == ['-m', 'venv']], calls


def test_on_windows_step_3_gives_this_folders_command_not_mcp_json(
    install: Install, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md INS-24: .mcp.json runs `sh`, so on Windows the folder registers with claude mcp add
    # (README, test_mcp_json.py); the installer still pointed Windows users at .mcp.json
    module, _ = install
    monkeypatch.setattr(sys, 'platform', 'win32')
    _run(module, monkeypatch, '--plugins-dir', str(tmp_path), '--no-skill')
    step3 = capsys.readouterr().out.split('[3/4]')[1].split('[4/4]')[0]
    assert 'In this folder, .mcp.json registers it' not in step3
    assert 'this folder' in step3 and '--scope local' in step3, step3
