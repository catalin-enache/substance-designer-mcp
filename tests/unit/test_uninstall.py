"""uninstall.py against a fake home: plugin folder, token, skill, venv, snapshots and Claude Code's
config all live in tmp_path, and the `claude` CLI is intercepted."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from conftest import ROOT
from project_constants import PLUGIN, PLUGIN_DIR

SERVER = os.path.join(ROOT, 'mcp_server', 'server.py')


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> types.SimpleNamespace:
    spec = importlib.util.spec_from_file_location('uninstall', os.path.join(ROOT, 'uninstall.py'))
    assert spec is not None and spec.loader is not None  # a .py file that exists
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    home = types.SimpleNamespace(
        plugins=tmp_path / 'plugins',
        skills=tmp_path / 'skills',
        config=tmp_path / 'config',
        token=tmp_path / 'token',
        old_token=tmp_path / 'old_token',
        venv=tmp_path / 'venv',
        snapshots=tmp_path / 'snapshots',
        other=tmp_path / 'other_project',
        calls=[],
        module=module,
    )
    monkeypatch.setitem(vars(module), 'TOKEN_FILE', str(home.token))
    monkeypatch.setitem(vars(module.install), 'OLD_TOKEN', str(home.old_token))
    monkeypatch.setitem(vars(module), 'VENV', str(home.venv))
    monkeypatch.setenv('SD_SNAPSHOT_DIR', str(home.snapshots))
    monkeypatch.setenv('CLAUDE_CONFIG_DIR', str(home.config))
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/local/bin/claude')

    def run(cmd: list[str], cwd: str | None = None, **kw: object) -> subprocess.CompletedProcess[str]:
        home.calls.append((cmd, cwd))
        return subprocess.CompletedProcess(cmd, 0, '', '')

    monkeypatch.setattr(subprocess, 'run', run)

    # everything install.py leaves behind, plus a project registered with --scope local
    shutil.copytree(PLUGIN_DIR, str(home.plugins / PLUGIN))
    home.token.write_text('x' * 64)
    skill = home.skills / module.install.SERVER_NAME
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('---\nname: x\n---\n' + module.install.SKILL_MARKER)
    (home.venv / 'bin').mkdir(parents=True)
    (home.snapshots / 'graph').mkdir(parents=True)
    home.other.mkdir()
    write_config(
        home,
        {
            'projects': {
                str(home.other): {
                    'mcpServers': {
                        'substance-designer': {'type': 'stdio', 'command': '/x/venv/bin/python', 'args': [SERVER]}
                    }
                }
            }
        },
    )
    return home


def write_config(home: types.SimpleNamespace, config: dict[str, Any]) -> None:
    home.config.mkdir(exist_ok=True)
    (home.config / '.claude.json').write_text(json.dumps(config))


def run(home: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr(
        sys, 'argv', ['uninstall.py', '--plugins-dir', str(home.plugins), '--skills-dir', str(home.skills), *args]
    )
    home.module.main()


def test_removes_everything_install_left(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run(env, monkeypatch, '--yes')
    assert not (env.plugins / PLUGIN).exists() and not env.token.exists()
    assert not (env.skills / 'substance-designer').exists() and not env.venv.exists()
    assert env.calls == [
        (['/usr/local/bin/claude', 'mcp', 'remove', 'substance-designer', '-s', 'local'], str(env.other))
    ]
    assert env.snapshots.exists()  # the user's graph backups stay unless asked
    assert 'delete this folder' in capsys.readouterr().out


def test_dry_run_and_no_answer_remove_nothing(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run(env, monkeypatch, '--dry-run')
    out = capsys.readouterr().out
    assert 'Will remove:' in out and str(env.other) in out
    monkeypatch.setattr('builtins.input', lambda prompt: 'n')
    run(env, monkeypatch)
    assert 'Nothing removed.' in capsys.readouterr().out
    assert (env.plugins / PLUGIN).exists() and env.token.exists() and env.venv.exists()
    assert (env.skills / 'substance-designer').exists() and not env.calls


def test_leaves_other_peoples_things_alone(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    shutil.rmtree(str(env.plugins / PLUGIN))
    (env.plugins / PLUGIN).mkdir()
    (env.plugins / PLUGIN / 'pluginInfo.json').write_text('{"name": "someone else"}')
    (env.skills / 'substance-designer' / 'SKILL.md').write_text('my own skill')
    write_config(
        env,
        {
            'mcpServers': {'substance-designer': {'command': 'other-server'}},
            'projects': {str(env.other): {'mcpServers': {'substance-designer': {'command': 'npx', 'args': ['x']}}}},
        },
    )
    run(env, monkeypatch, '--yes')
    assert (env.plugins / PLUGIN / 'pluginInfo.json').exists()
    assert (env.skills / 'substance-designer' / 'SKILL.md').read_text() == 'my own skill'
    assert not env.calls
    assert capsys.readouterr().out.count('left as it is') == 4


def test_user_scope_registration_of_this_server_is_removed(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_config(env, {'mcpServers': {'substance-designer': {'command': '/x/python', 'args': [SERVER]}}})
    run(env, monkeypatch, '--yes')
    assert env.calls == [(['/usr/local/bin/claude', 'mcp', 'remove', 'substance-designer', '-s', 'user'], None)]


def test_reports_registrations_it_cannot_remove(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    gone = str(env.other) + '_deleted'
    write_config(env, {'projects': {gone: {'mcpServers': {'substance-designer': {'args': [SERVER]}}}}})
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert 'Could not remove MCP registration, %s: folder no longer exists' % gone in out
    assert 'Some items were not removed' in out and not env.calls


def test_reports_a_failing_claude_command(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        subprocess, 'run', lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, '', 'No MCP server found')
    )
    run(env, monkeypatch, '--yes')
    assert 'Could not remove MCP registration, %s: No MCP server found' % env.other in capsys.readouterr().out


def test_without_claude_prints_the_command(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(shutil, 'which', lambda name: None)
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert 'claude mcp remove substance-designer -s local' in out and not env.calls


def test_remove_snapshots_flag(env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    run(env, monkeypatch, '--yes', '--remove-snapshots')
    assert not env.snapshots.exists()


def test_removes_the_old_plugin_and_token(env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    old = env.plugins / 'sd_bridge'
    old.mkdir()
    (old / 'pluginInfo.json').write_text('{"name": "%s"}' % env.module.install.OLD_PLUGIN_NAME)
    env.old_token.write_text('x' * 64)
    run(env, monkeypatch, '--yes')
    assert not old.exists() and not env.old_token.exists()


def test_nothing_to_remove(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run(env, monkeypatch, '--yes', '--remove-snapshots')
    write_config(env, {})  # what `claude mcp remove` did
    capsys.readouterr()
    run(env, monkeypatch, '--yes')
    assert 'Nothing to remove' in capsys.readouterr().out


def test_snapshot_default_matches_the_server() -> None:
    with open(os.path.join(ROOT, 'mcp_server', 'server_tools', 'snapshots.py'), encoding='utf-8') as f:
        assert (
            "SNAPSHOT_DIR = os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), "
            "'.sd_mcp', 'snapshots')"
        ) in f.read()


def test_one_failure_does_not_stop_the_rest(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md INS-2: on Windows a running server locks files; one item failing must not leave
    # the rest undone or end in a traceback
    real_rmtree = shutil.rmtree
    locked = str(env.plugins / PLUGIN)

    def rmtree(path: str, *a: Any, **kw: Any) -> None:
        if str(path) == locked:
            raise PermissionError(13, 'Access is denied', locked)
        return real_rmtree(path, *a, **kw)

    monkeypatch.setattr(shutil, 'rmtree', rmtree)
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert (env.plugins / PLUGIN).exists()
    assert not env.token.exists() and not env.venv.exists() and not (env.skills / 'substance-designer').exists()
    assert 'Could not remove Designer plugin' in out and 'Access is denied' in out
    assert 'Some items were not removed' in out


def test_warns_when_run_with_the_venvs_own_python(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, 'prefix', str(env.venv))
    run(env, monkeypatch, '--dry-run')
    assert 'python3 uninstall.py' in capsys.readouterr().out


def test_someone_elses_sd_bridge_is_never_reported_as_removed(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md INS-6: it was listed under "Will remove" and printed as "Removed" although
    # remove_old_plugin left it alone
    other = env.plugins / 'sd_bridge'
    other.mkdir()
    (other / 'pluginInfo.json').write_text('{"name": "Some other bridge"}')
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert other.exists()
    removed = [l for l in out.splitlines() if l.startswith('Removed ')]
    assert not any(str(other) in l for l in removed), removed
    assert str(other) in out.split('Not touched:')[1].split('Removed')[0]


def test_remove_snapshots_deletes_only_the_snapshots(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md INS-7: SD_SNAPSHOT_DIR may point at a shared folder; only what the server wrote goes
    snap = env.snapshots / 'graph' / '20261029-170000-before_tweak.sbs'
    snap.write_text('snapshot')
    mine = env.snapshots / 'notes.txt'
    mine.write_text('not a snapshot')
    run(env, monkeypatch, '--yes', '--remove-snapshots')
    assert not snap.exists() and mine.exists()


def test_a_kept_snapshot_folder_is_reported_as_kept(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md INS-15: other files keep the folder, but the summary said it was removed
    (env.snapshots / 'notes.txt').write_text('not a snapshot')
    capsys.readouterr()
    run(env, monkeypatch, '--yes', '--remove-snapshots')
    line = next(l for l in capsys.readouterr().out.splitlines() if 'graph snapshots' in l and 'Removed' in l)
    assert 'folder kept' in line, line


def test_removes_leftover_copies_of_the_plugin(env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md INS-16: an interrupted install can leave <plugin>.new or <plugin>.old (each a full
    # copy of ours); someone else's folder with such a name is left alone
    import shutil

    ours = env.plugins / PLUGIN
    for suffix in ('.new', '.old'):
        shutil.copytree(ours, env.plugins / (PLUGIN + suffix))
    foreign = env.plugins / (PLUGIN + '.bak')
    foreign.mkdir()
    run(env, monkeypatch, '--yes')
    assert not (env.plugins / (PLUGIN + '.new')).exists() and not (env.plugins / (PLUGIN + '.old')).exists()
    assert foreign.exists()


def test_reports_a_leftover_copy_that_isnt_ours(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md INS-20: a partly deleted <plugin>.old (no pluginInfo.json any more) was skipped silently
    partial = env.plugins / (PLUGIN + '.old')
    partial.mkdir()
    (partial / 'stuck.dll').write_text('locked')
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert partial.exists() and str(partial) in out and 'left as it is' in out
