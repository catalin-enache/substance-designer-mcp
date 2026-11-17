"""uninstall.py against a fake home: plugin folder, token, skill, venv, snapshots and Claude Code's
config all live in tmp_path, and the `claude` CLI is intercepted."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import types
from collections.abc import Mapping
from pathlib import Path

import pytest
from fake_defaults import FakeDefaults
from typing_extensions import Unpack  # typing's from Python 3.11; mcp requires typing_extensions

import designer_preferences
from conftest import ROOT, RunOptions
from project_constants import PLUGIN, PLUGIN_DIR, JsonSent

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
    monkeypatch.setitem(vars(module.project_constants), 'AGENT_RECORD_DIR', str(tmp_path))
    monkeypatch.setitem(vars(module.install), 'OLD_TOKEN', str(home.old_token))
    monkeypatch.setitem(vars(module), 'VENV', str(home.venv))
    # the folders launch_designer makes for a Designer it starts (REVIEW.md TST-162), and no Designer running
    monkeypatch.setitem(vars(module.project_constants), 'SHORT_TEMP', str(tmp_path / 'tmp'))
    home.real_folders_in_use = vars(module)['folders_in_use']
    monkeypatch.setitem(vars(module), 'folders_in_use', lambda: None)
    monkeypatch.setenv('SD_SNAPSHOT_DIR', str(home.snapshots))
    monkeypatch.setenv('CLAUDE_CONFIG_DIR', str(home.config))
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/local/bin/claude')

    def run(cmd: list[str], **kw: Unpack[RunOptions]) -> subprocess.CompletedProcess[str]:
        home.calls.append((cmd, kw.get('cwd')))
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


def write_config(home: types.SimpleNamespace, config: Mapping[str, JsonSent]) -> None:
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


def test_removes_the_record_of_the_designer_an_agent_started(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # one per port (ROADMAP item 49), and the single one of earlier versions
    records = [Path(env.module.project_constants.agent_designer_file(port)) for port in (9877, 9901)]
    records.append(tmp_path / ('.%s_agent_designer.json' % PLUGIN))
    for record in records:
        record.write_text('{}')
    other = tmp_path / ('.%s_agent_designer_notes.json' % PLUGIN)  # not a record
    other.write_text('{}')
    run(env, monkeypatch, '--yes')
    assert not any(record.exists() for record in records) and other.exists()


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

    def rmtree(path: str, ignore_errors: bool = False) -> None:  # the parameters uninstall.py and install.py pass
        if str(path) == locked:
            raise PermissionError(13, 'Access is denied', locked)
        return real_rmtree(path, ignore_errors)

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


def test_remove_snapshots_removes_their_package_notes_and_folders(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md INS-26: each snapshot has a note of its package beside it (SRV-34); left behind, the
    # notes kept every graph's folder, and the snapshot folder itself
    graph = env.snapshots / 'graph'
    (graph / '20261031-120000-before_portals.sbs').write_text('snapshot')
    (graph / '20261031-120000-before_portals.sbs.json').write_text('{"package": "", "uid": "x"}')
    (graph / 'mine.json').write_text('not a note')  # another .json: kept, so is the folder
    other = env.snapshots / 'other'
    other.mkdir()
    (other / '20261031-120001.sbs').write_text('snapshot')
    (other / '20261031-120001.sbs.json').write_text('{}')
    run(env, monkeypatch, '--yes', '--remove-snapshots')
    assert sorted(p.name for p in graph.iterdir()) == ['mine.json'] and not other.exists()


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


def test_remove_snapshots_keeps_one_saved_over_since(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md SRV-47: a snapshot opened to recover and saved in place holds the user's work; its note
    # records the size and time it was written, and one that no longer matches is kept, and said so
    import json
    import os

    graph = env.snapshots / 'graph'
    untouched, saved_over = graph / '20261101-100000.sbs', graph / '20261101-110000.sbs'
    for path in (untouched, saved_over):
        path.write_text('snapshot')
        st = os.stat(path)
        (graph / (path.name + '.json')).write_text(
            json.dumps({'package': '/a/A.sbs', 'uid': 'x', 'size': st.st_size, 'mtime_ns': st.st_mtime_ns})
        )
    saved_over.write_text('the user saved work into the snapshot')
    run(env, monkeypatch, '--yes', '--remove-snapshots')
    assert sorted(p.name for p in graph.iterdir()) == [saved_over.name, saved_over.name + '.json']
    assert str(saved_over) in capsys.readouterr().out


def _agents_folders(root: Path) -> list[Path]:
    """The folders of two Designers an agent started, on ports 9877 and 9901, as launch_designer makes them."""
    ours = [root / ('sd_mcp_%d_%d' % (os.getuid(), port)) for port in (9877, 9901)]
    for folder in ours:
        (folder / 'home' / 'Library').mkdir(parents=True)
        (folder / 'temp').mkdir()
    return ours


@pytest.mark.skipif(sys.platform == 'win32', reason='launch_designer makes these folders on macOS and Linux only')
def test_removes_the_folders_of_the_designers_an_agent_started(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-162: their homes (settings, logs, crash dumps) stayed in /tmp after uninstalling
    root = tmp_path / 'tmp'
    ours = _agents_folders(root)
    someone = root / ('sd_mcp_%d_9877' % (os.getuid() + 1))  # another account's
    someone.mkdir()
    near = root / ('sd_mcp_%d_notes' % os.getuid())  # not a port
    near.mkdir()
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    (elsewhere / 'keep').write_text('x')
    (root / ('sd_mcp_%d_9902' % os.getuid())).symlink_to(elsewhere)  # a link isn't a folder launch_designer made
    run(env, monkeypatch, '--dry-run')
    out = capsys.readouterr().out
    assert all(str(folder) in out for folder in ours), out
    run(env, monkeypatch, '--yes')
    assert not any(folder.exists() for folder in ours)
    assert someone.exists() and near.exists() and (elsewhere / 'keep').exists()


@pytest.mark.skipif(sys.platform == 'win32', reason='launch_designer makes these folders on macOS and Linux only')
def test_keeps_those_folders_while_a_designer_runs(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # one an agent started uses its folder as its home, and its crash dumps may be wanted
    ours = _agents_folders(tmp_path / 'tmp')
    monkeypatch.setitem(vars(env.module), 'folders_in_use', lambda: 'Designer runs')
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert all(folder.exists() for folder in ours)
    assert 'while Designer runs' in out and all(str(folder) in out for folder in ours), out


def test_a_running_designer_is_found_as_the_server_finds_it(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    # one pattern for Designer's process, in project_constants.py (the fixture's subprocess.run answers 0: found)
    monkeypatch.setattr(sys, 'platform', 'darwin')
    found = env.real_folders_in_use() == 'Designer runs'
    pattern = env.module.project_constants.DESIGNER_PROCESS
    assert found and (['pgrep', '-f', pattern], None) in env.calls, env.calls


def _real_process_check(env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    """The real check for a Designer running, in place of the fixture's (none running)."""
    monkeypatch.setitem(vars(env.module), 'folders_in_use', env.real_folders_in_use)


def _pgrep(monkeypatch: pytest.MonkeyPatch, outcome: int | Exception) -> None:
    """subprocess.run as the fixture's, but pgrep exits with `outcome`, or raises it."""
    real = subprocess.run

    def run(cmd: list[str], **kw: Unpack[RunOptions]) -> subprocess.CompletedProcess[str]:
        if cmd[0] != 'pgrep':
            return real(cmd, **kw)
        if isinstance(outcome, Exception):
            raise outcome
        return subprocess.CompletedProcess(cmd, outcome, '', 'pgrep: cannot allocate memory' if outcome > 1 else '')

    monkeypatch.setattr(subprocess, 'run', run)


@pytest.mark.skipif(sys.platform == 'win32', reason='launch_designer makes these folders on macOS and Linux only')
@pytest.mark.parametrize(
    'platform, outcome',
    [('darwin', 2), ('darwin', 3), ('darwin', FileNotFoundError(2, 'No such file', 'pgrep')), ('linux', 1)],
    ids=['pgrep fails', 'pgrep fails otherwise', 'no pgrep', 'not macOS'],
)
def test_keeps_those_folders_when_it_cant_tell_whether_a_designer_runs(
    env: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    platform: str,
    outcome: int | Exception,
) -> None:
    # REVIEW.md INS-27: a failing pgrep read as "none running", and the folders of a running Designer went; a missing
    # one crashed uninstall before it printed anything; on Linux the pattern, macOS's, never finds one
    ours = _agents_folders(tmp_path / 'tmp')
    _real_process_check(env, monkeypatch)
    monkeypatch.setattr(sys, 'platform', platform)
    _pgrep(monkeypatch, outcome)
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert all(folder.exists() for folder in ours), out
    assert all(str(folder) in out for folder in ours) and 'kept' in out, out


@pytest.mark.skipif(sys.platform == 'win32', reason='launch_designer makes these folders on macOS and Linux only')
def test_removes_those_folders_when_pgrep_finds_no_designer(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ours = _agents_folders(tmp_path / 'tmp')
    _real_process_check(env, monkeypatch)
    monkeypatch.setattr(sys, 'platform', 'darwin')
    _pgrep(monkeypatch, 1)  # nothing found
    run(env, monkeypatch, '--yes')
    assert not any(folder.exists() for folder in ours)


@pytest.mark.skipif(sys.platform == 'win32', reason='launch_designer makes these folders on macOS and Linux only')
def test_keeps_a_folder_another_account_owns_though_named_for_this_one(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-171: the "another account's" folder above is named for another user ID, so the name already left
    # it out; one named for this user but owned by another reaches the owner check alone (here this user is someone
    # else, and the folder is the real user's)
    someone_else = os.getuid() + 1
    monkeypatch.setattr(os, 'getuid', lambda: someone_else)
    theirs = tmp_path / 'tmp' / ('sd_mcp_%d_9877' % someone_else)
    (theirs / 'home').mkdir(parents=True)
    run(env, monkeypatch, '--yes')
    assert theirs.is_dir() and 'not a folder launch_designer made' in capsys.readouterr().out


def _preferences_saved_and_changed(defaults: FakeDefaults) -> None:
    """A copy of Designer's preferences as launch_designer saves one, and the file changed since by an agent's
    Designer that ended outside the tools, so nothing put it back (designer_preferences.py, ROADMAP item 67)."""
    defaults.domain = {'session.mainWindow.state': b'the user'}
    with designer_preferences.saved(lambda: False, ended=False):
        pass
    defaults.domain['session.instancePID'] = 11


_COPY_ITEM = (
    "the copy of Designer's preferences launch_designer saved, put back first unless your own Designer ran since or "
    'it is over %d hours old: %%s' % designer_preferences.LEFTOVER_HOURS
)
_MACOS = pytest.mark.skipif(sys.platform != 'darwin', reason='the plist is macOS only')


@_MACOS
def test_puts_designers_preferences_back_and_removes_their_copy(
    env: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    defaults: FakeDefaults,
) -> None:
    _preferences_saved_and_changed(defaults)
    Path(designer_preferences.saved_file() + '.new').write_bytes(b'half')  # a save cut short (REVIEW.md INS-34)
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert defaults.domain == {'session.mainWindow.state': b'the user'}, out
    assert not any(
        os.path.exists(path)
        for path in (
            designer_preferences.saved_file(),
            designer_preferences.saved_file() + '.new',
            designer_preferences.lock_file(),
        )
    ), out
    assert ("Removed %s (Designer's preferences put back" % (_COPY_ITEM % designer_preferences.saved_file())) in out, (
        out
    )


@_MACOS
def test_a_copy_dropped_as_the_users_says_so(
    env: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    defaults: FakeDefaults,
) -> None:
    # REVIEW.md INS-34: their Designer ran since, so the file is left as theirs, and the item's label says it may be
    _preferences_saved_and_changed(defaults)
    changed = dict(defaults.domain)
    log = defaults.users_data / '16.0' / 'log.txt'
    log.parent.mkdir()
    log.write_text('the user ran it\n')
    later = os.path.getmtime(designer_preferences.saved_file()) + 5
    os.utime(log, (later, later))
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert defaults.domain == changed and not os.path.exists(designer_preferences.saved_file()), out
    assert (
        "Removed %s (Designer's preferences left as they are: the user's Designer ran since"
        % (_COPY_ITEM % designer_preferences.saved_file())
    ) in out, out
    assert 'Some items were not removed' not in out, out


@_MACOS
def test_an_old_copy_of_designers_preferences_is_dropped_as_the_label_says(
    env: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    defaults: FakeDefaults,
) -> None:
    # REVIEW.md INS-35, TST-368: uninstall ends no Designer (ended=False), so a copy past LEFTOVER_HOURS is dropped: the
    # user may have worked since
    _preferences_saved_and_changed(defaults)
    changed = dict(defaults.domain)
    old = time.time() - (designer_preferences.LEFTOVER_HOURS + 1) * 3600
    os.utime(designer_preferences.saved_file(), (old, old))
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert defaults.domain == changed and not os.path.exists(designer_preferences.saved_file()), out
    assert (
        "Removed %s (Designer's preferences left as they are: their copy is over"
        % (_COPY_ITEM % designer_preferences.saved_file())
    ) in out, out


@_MACOS
def test_keeps_the_copy_of_designers_preferences_while_a_designer_runs(
    env: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    defaults: FakeDefaults,
) -> None:
    # put back only once none runs: that Designer writes the file again as it quits
    _preferences_saved_and_changed(defaults)
    changed = dict(defaults.domain)
    monkeypatch.setitem(vars(env.module), 'folders_in_use', lambda: 'Designer runs')
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert defaults.domain == changed and os.path.exists(designer_preferences.saved_file())
    assert (
        "the copy of Designer's preferences launch_designer saved, kept while Designer runs: %s"
        % designer_preferences.saved_file()
    ) in out, out


_NO_LISTING = "Designer's processes couldn't be listed (pgrep exit code 3: fork failed)"


@_MACOS
@pytest.mark.parametrize('how', ['import fails', 'a Designer started meanwhile', 'the listing fails'])
def test_says_when_designers_preferences_couldnt_be_put_back(
    env: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    defaults: FakeDefaults,
    how: str,
) -> None:
    # REVIEW.md INS-34: the copy kept, to put back later
    _preferences_saved_and_changed(defaults)
    if how == 'import fails':
        defaults.domain['session.mainWindow.state'] = (
            b'floating'  # a value to put back: no import without one (SRV-140)
        )
        defaults.fail['import'] = 'the disk is full'
    else:  # none at the listing, then one by the put-back, or the listing failing then (REVIEW.md TST-358, INS-36)
        then = 'Designer runs' if how == 'a Designer started meanwhile' else _NO_LISTING
        answers = iter([None, then])
        monkeypatch.setitem(vars(env.module), 'folders_in_use', lambda: next(answers, then))
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert "Could not remove the copy of Designer's preferences" in out and 'Some items were not removed' in out, out
    why = {
        'import fails': 'the disk is full',
        'a Designer started meanwhile': 'a Designer runs',
        'the listing fails': _NO_LISTING,
    }
    assert why[how] in out, out
    assert how != 'the listing fails' or 'a Designer runs' not in out, out
    assert os.path.exists(designer_preferences.saved_file()), 'kept, to put back later'


@_MACOS
def test_a_copy_of_designers_preferences_that_isnt_a_plist_is_removed_with_its_lock(
    env: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    defaults: FakeDefaults,
) -> None:
    # REVIEW.md INS-35: the put-back removes it, saying nothing was put back: removed, with what is left beside it, not
    # "Could not remove ... so it was removed"
    _preferences_saved_and_changed(defaults)
    Path(designer_preferences.saved_file()).write_bytes(b'not a plist')
    Path(designer_preferences.saved_file() + '.new').write_bytes(b'half')
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert (
        "Removed %s (Designer's preferences couldn't be put back: their copy could not be read"
        % (_COPY_ITEM % designer_preferences.saved_file())
    ) in out, out
    assert 'Could not remove' not in out and 'Some items were not removed' not in out, out
    left = [
        designer_preferences.saved_file(),
        designer_preferences.saved_file() + '.new',
        designer_preferences.lock_file(),
    ]
    assert not any(os.path.exists(path) for path in left), out


@_MACOS
@pytest.mark.parametrize('cut_short', [False, True], ids=['alone', 'with a save cut short'])
def test_removes_the_lock_of_designers_preferences_left_with_no_copy(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], cut_short: bool
) -> None:
    # every launch_designer that starts one on macOS leaves it, the copy gone once put back; a first save cut short
    # leaves the user's settings beside it, with no copy (REVIEW.md INS-35)
    Path(designer_preferences.lock_file()).write_text('')
    new = designer_preferences.saved_file() + '.new'
    if cut_short:
        Path(new).write_bytes(b'half')
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert not os.path.exists(designer_preferences.lock_file()) and not os.path.exists(new), out
    what = 'lock and a save cut short' if cut_short else 'lock'
    files = designer_preferences.lock_file() + (', ' + new if cut_short else '')
    assert ("Removed %s of the copy of Designer's preferences launch_designer saved: %s" % (what, files)) in out, out


@_MACOS
def test_lists_the_lock_of_designers_preferences_kept_while_a_designer_runs(
    env: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md INS-34: a launch may hold it; unlinked, a later one would lock a new file beside the holder's
    Path(designer_preferences.lock_file()).write_text('')
    monkeypatch.setitem(vars(env.module), 'folders_in_use', lambda: 'Designer runs')
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert os.path.exists(designer_preferences.lock_file())
    assert (
        "lock of the copy of Designer's preferences launch_designer saved, kept while Designer runs: %s"
        % designer_preferences.lock_file()
    ) in out, out


@_MACOS
def test_a_lock_that_cant_be_removed_after_a_put_back_is_no_failure(
    env: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    defaults: FakeDefaults,
) -> None:
    # REVIEW.md INS-34: the file was put back and the copy removed
    _preferences_saved_and_changed(defaults)
    real = os.remove

    def remove(path: str) -> None:
        if path == designer_preferences.lock_file():
            raise PermissionError(1, 'Operation not permitted')
        real(path)

    monkeypatch.setattr(os, 'remove', remove)
    run(env, monkeypatch, '--yes')
    out = capsys.readouterr().out
    assert defaults.domain == {'session.mainWindow.state': b'the user'} and 'Could not remove' not in out, out


@pytest.mark.parametrize(
    'config',
    [
        '[]',
        '{"mcpServers": [1]}',
        '{"mcpServers": {"substance-designer": "x"}}',
        '{"projects": ["x"]}',
        '{"projects": {"/a": []}}',
        '{"projects": {"/a": {"mcpServers": [1]}}}',
        '{"projects": {"/a": {"mcpServers": {"substance-designer": 1}}}}',
        '{"mcpServers": ',
    ],
    ids=[
        'a list',
        'servers a list',
        'a server a string',
        'projects a list',
        'a project a list',
        "a project's servers a list",
        "a project's server a number",
        'not JSON',
    ],
)
def test_a_config_holding_no_json_object_where_one_belongs_finds_no_registration(
    env: types.SimpleNamespace, config: str
) -> None:
    # REVIEW.md SRV-173: ~/.claude.json was taken for the dicts it is read as, so JSON that isn't an object at any
    # level raised AttributeError past except (OSError, ValueError), which takes a file that isn't JSON as none
    env.config.mkdir(exist_ok=True)
    (env.config / '.claude.json').write_text(config)
    assert env.module.find_registrations(str(env.config / '.claude.json')) == ([], [])


@pytest.mark.parametrize(
    ('config', 'note'),
    [
        (
            {'mcpServers': {'substance-designer': {'command': 5}}},
            'a user-scope "substance-designer" that runs something else',
        ),
        (
            {'mcpServers': {'substance-designer': {'args': 5}}},
            'a user-scope "substance-designer" that runs something else',
        ),
        (
            {'projects': {'/a': {'mcpServers': {'substance-designer': {'args': 5}}}}},
            '"substance-designer" in /a runs something else',
        ),
    ],
    ids=['a command a number', 'args a number', "a project's args a number"],
)
def test_a_registration_whose_command_or_args_have_another_type_runs_something_else(
    env: types.SimpleNamespace, config: dict[str, JsonSent], note: str
) -> None:
    # REVIEW.md TST-490, SRV-173: a command was taken for a string and args for a list, so a number in either raised
    # TypeError past except (OSError, ValueError)
    write_config(env, config)
    assert env.module.find_registrations() == ([], [note])
