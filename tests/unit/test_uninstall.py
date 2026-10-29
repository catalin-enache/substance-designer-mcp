"""uninstall.py against a fake home: plugin folder, token, skill, venv, snapshots and Claude Code's
config all live in tmp_path, and the `claude` CLI is intercepted."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import types

import pytest

from conftest import ROOT
from project_constants import PLUGIN, PLUGIN_DIR

SERVER = os.path.join(ROOT, 'mcp_server', 'server.py')


@pytest.fixture
def env(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location('uninstall', os.path.join(ROOT, 'uninstall.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    home = types.SimpleNamespace(
        plugins=tmp_path / 'plugins', skills=tmp_path / 'skills', config=tmp_path / 'config',
        token=tmp_path / 'token', old_token=tmp_path / 'old_token', venv=tmp_path / 'venv',
        snapshots=tmp_path / 'snapshots', other=tmp_path / 'other_project', calls=[], module=module)
    monkeypatch.setattr(module, 'TOKEN_FILE', str(home.token))
    monkeypatch.setattr(module.install, 'OLD_TOKEN', str(home.old_token))
    monkeypatch.setattr(module, 'VENV', str(home.venv))
    monkeypatch.setenv('SD_SNAPSHOT_DIR', str(home.snapshots))
    monkeypatch.setenv('CLAUDE_CONFIG_DIR', str(home.config))
    monkeypatch.setattr(module.shutil, 'which', lambda name: '/usr/local/bin/claude')

    def run(cmd, cwd=None, **kw):
        home.calls.append((cmd, cwd))
        return subprocess.CompletedProcess(cmd, 0, '', '')
    monkeypatch.setattr(module.subprocess, 'run', run)

    # everything install.py leaves behind, plus a project registered with --scope local
    shutil.copytree(PLUGIN_DIR, str(home.plugins / PLUGIN))
    home.token.write_text('x' * 64)
    skill = home.skills / module.install.SERVER_NAME
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('---\nname: x\n---\n' + module.install.SKILL_MARKER)
    (home.venv / 'bin').mkdir(parents=True)
    (home.snapshots / 'graph').mkdir(parents=True)
    home.other.mkdir()
    write_config(home, {'projects': {str(home.other): {'mcpServers': {
        'substance-designer': {'type': 'stdio', 'command': '/x/venv/bin/python', 'args': [SERVER]}}}}})
    return home


def write_config(home, config):
    home.config.mkdir(exist_ok=True)
    (home.config / '.claude.json').write_text(json.dumps(config))


def run(home, monkeypatch, *args):
    monkeypatch.setattr(sys, 'argv', ['uninstall.py', '--plugins-dir', str(home.plugins),
                                      '--skills-dir', str(home.skills), *args])
    home.module.main()


def test_removes_everything_install_left(env, monkeypatch, capsys):
    run(env, monkeypatch, '--yes')
    assert not (env.plugins / PLUGIN).exists() and not env.token.exists()
    assert not (env.skills / 'substance-designer').exists() and not env.venv.exists()
    assert env.calls == [(['/usr/local/bin/claude', 'mcp', 'remove', 'substance-designer', '-s', 'local'],
                          str(env.other))]
    assert env.snapshots.exists()   # the user's graph backups stay unless asked
    assert 'delete this folder' in capsys.readouterr().out


def test_dry_run_and_no_answer_remove_nothing(env, monkeypatch, capsys):
    run(env, monkeypatch, '--dry-run')
    out = capsys.readouterr().out
    assert 'Will remove:' in out and str(env.other) in out
    monkeypatch.setattr('builtins.input', lambda prompt: 'n')
    run(env, monkeypatch)
    assert 'Nothing removed.' in capsys.readouterr().out
    assert (env.plugins / PLUGIN).exists() and env.token.exists() and env.venv.exists()
    assert (env.skills / 'substance-designer').exists() and not env.calls


def test_leaves_other_peoples_things_alone(env, monkeypatch, capsys):
    shutil.rmtree(str(env.plugins / PLUGIN))
    (env.plugins / PLUGIN).mkdir()
    (env.plugins / PLUGIN / 'pluginInfo.json').write_text('{"name": "someone else"}')
    (env.skills / 'substance-designer' / 'SKILL.md').write_text('my own skill')
    write_config(env, {
        'mcpServers': {'substance-designer': {'command': 'other-server'}},
        'projects': {str(env.other): {'mcpServers': {'substance-designer': {'command': 'npx', 'args': ['x']}}}}})
    run(env, monkeypatch, '--yes')
    assert (env.plugins / PLUGIN / 'pluginInfo.json').exists()
    assert (env.skills / 'substance-designer' / 'SKILL.md').read_text() == 'my own skill'
    assert not env.calls
    assert capsys.readouterr().out.count('left as it is') == 4


def test_user_scope_registration_of_this_server_is_removed(env, monkeypatch):
    write_config(env, {'mcpServers': {'substance-designer': {'command': '/x/python', 'args': [SERVER]}}})
    run(env, monkeypatch, '--yes')
    assert env.calls == [(['/usr/local/bin/claude', 'mcp', 'remove', 'substance-designer', '-s', 'user'], None)]


def test_reports_registrations_it_cannot_remove(env, monkeypatch, capsys):
    gone = str(env.other) + '_deleted'
    write_config(env, {'projects': {gone: {'mcpServers': {'substance-designer': {'args': [SERVER]}}}}})
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert 'Could not remove MCP registration, %s: folder no longer exists' % gone in out
    assert 'Some items were not removed' in out and not env.calls


def test_reports_a_failing_claude_command(env, monkeypatch, capsys):
    monkeypatch.setattr(env.module.subprocess, 'run',
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, '', 'No MCP server found'))
    run(env, monkeypatch, '--yes')
    assert 'Could not remove MCP registration, %s: No MCP server found' % env.other in capsys.readouterr().out


def test_without_claude_prints_the_command(env, monkeypatch, capsys):
    monkeypatch.setattr(env.module.shutil, 'which', lambda name: None)
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert 'claude mcp remove substance-designer -s local' in out and not env.calls


def test_remove_snapshots_flag(env, monkeypatch):
    run(env, monkeypatch, '--yes', '--remove-snapshots')
    assert not env.snapshots.exists()


def test_removes_the_old_plugin_and_token(env, monkeypatch):
    old = env.plugins / 'sd_bridge'
    old.mkdir()
    (old / 'pluginInfo.json').write_text('{"name": "%s"}' % env.module.install.OLD_PLUGIN_NAME)
    env.old_token.write_text('x' * 64)
    run(env, monkeypatch, '--yes')
    assert not old.exists() and not env.old_token.exists()


def test_nothing_to_remove(env, monkeypatch, capsys):
    run(env, monkeypatch, '--yes', '--remove-snapshots')
    write_config(env, {})   # what `claude mcp remove` did
    capsys.readouterr()
    run(env, monkeypatch, '--yes')
    assert 'Nothing to remove' in capsys.readouterr().out


def test_snapshot_default_matches_the_server():
    with open(SERVER, encoding='utf-8') as f:
        assert ("SNAPSHOT_DIR = os.environ.get('SD_SNAPSHOT_DIR') or os.path.join(os.path.expanduser('~'), "
                "'.sd_mcp', 'snapshots')") in f.read()
