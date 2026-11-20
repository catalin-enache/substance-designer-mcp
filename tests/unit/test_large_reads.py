"""The lead's hooks against large reads (`.claude/hooks/large_reads.py`, ROADMAP item 102): a read that returns over
20 KB is refused, whole or ranged, its line numbers counted, and so is a Bash command that would print over 20 KB of
files. A Bash output of 8,000 characters or more that reached the context gets a note, whether the command succeeded
or failed. The lead's 8th reading call of a turn, and each 8th after it, gets a note suggesting the `analyst`. All let a subagent's calls through, and an error lets any call through."""

import functools
import io
import json
import shlex
import sys
import tempfile
from pathlib import Path
from typing import Protocol

import pytest
from counted_reads import Counter
from docs_text import agents_md, flat, read
from hook_calls import HookCall, HookInput, HookResponse, load_script, run_hook
from notebook_files import cell, write_notebook

from conftest import ROOT

HOOK = Path(ROOT, '.claude', 'hooks', 'large_reads.py')
SETTINGS = Path(ROOT, '.claude', 'settings.json')
# the hook's command, as Claude Code reads it: nothing if the script is missing (Python would exit 2 on it, which
# blocks) or the venv is, else the script run by the venv's Python
COMMAND = (
    's="$CLAUDE_PROJECT_DIR/.claude/hooks/large_reads.py"; [ -f "$s" ] || exit 0; '
    'p="$CLAUDE_PROJECT_DIR/mcp_server/venv/bin/python"; '
    '[ -x "$p" ] || p="$CLAUDE_PROJECT_DIR/mcp_server/venv/Scripts/python.exe"; '
    '[ -x "$p" ] || exit 0; "$p" "$s"'
)
LINE = 'x' * 99 + '\n'
PYCHARM = 'mcp__pycharm__read_file'
SHELL = "git log -p --since='2 weeks ago' -- mcp_server tests/unit tests/test_all_tools client scripts install.py"


class _Hook(Protocol):
    """What the tests use of the hook's module."""

    BIG: int
    BLOCK: int
    OUTPUT_LIMIT: int
    PLAN: str
    PROJECT: str
    PYCHARM_LIMIT: int
    READ_LIMIT: int
    READING_TOOLS: tuple[str, ...]
    RESEARCH_NOTE: str
    RESEARCH_READS: int
    STATE_FOLDER: str

    def read_refusal(self, call: object) -> str | None: ...

    def bash_refusal(self, call: object) -> str | None: ...

    def bash_note(self, call: object) -> str | None: ...

    def web_refusal(self, call: object) -> str | None: ...

    def _returned(self, path: str, pycharm: bool, offset: object, limit: object) -> object: ...

    def research_note(self, call: object) -> str | None: ...

    def main(self) -> int: ...


@functools.cache
def _hook() -> _Hook:
    return load_script(HOOK)


def _settings() -> dict[str, object]:
    """`.claude/settings.json`, parsed."""
    settings: object = json.loads(SETTINGS.read_text(encoding='utf-8'))
    assert isinstance(settings, dict)
    return settings


def _big(path: Path, lines: int = 300, end: str = '\n') -> Path:
    """A file of `lines` lines of 99 `x` and `end`: by default 30,000 bytes in 300 lines, over the limit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return _write(path, LINE.replace('\n', end) * lines)


def _write(path: Path, text: str) -> Path:
    """`text` written to `path` in UTF-8, each newline as it is. Windows' `write_text` writes a CRLF for it instead, and
    the sizes the tests check change (REVIEW.md TST-579)."""
    path.write_bytes(text.encode())
    return path


def _linked(tmp_path: Path) -> tuple[Path, Path]:
    """The folders `project` and `elsewhere`, `project/link` a symlink to `elsewhere/target`. Each has a `big.py` and a
    `sub/big.py`: over the limit in `project` and `elsewhere/sub`, under it in `elsewhere` and `project/sub`. Only
    `elsewhere` has an `only/big.py`, over the limit, and a folder `q`."""
    project, elsewhere = tmp_path / 'project', tmp_path / 'elsewhere'
    _big(project / 'big.py')
    _big(elsewhere / 'big.py', 50)
    _big(elsewhere / 'only' / 'big.py')
    _big(elsewhere / 'sub' / 'big.py')
    _big(project / 'sub' / 'big.py', 50)
    (elsewhere / 'q').mkdir()
    (elsewhere / 'target').mkdir()
    (project / 'link').symlink_to(elsewhere / 'target')
    return project, elsewhere


def _bytes_read(monkeypatch: pytest.MonkeyPatch) -> Counter:
    """The bytes the hook reads from the files it opens in binary, from now on."""
    counter = Counter()
    monkeypatch.setitem(vars(_hook()), 'open', counter.open)
    return counter


def _returned(text: str) -> int:
    """The bytes read_file returns of `text`, read whole and under 2,000 lines: each line after `L<n>: `, and an empty
    line after a last newline."""
    return len('\n'.join('L%d: %s' % (number, line) for number, line in enumerate(text.split('\n'), 1)).encode())


def _payload(event: str, tool: str, cwd: Path | str, tool_input: HookInput) -> HookCall:
    """A payload as Claude Code sends the lead's hook, before the fields only some events carry."""
    return {
        'session_id': 's',
        'cwd': str(cwd),
        'hook_event_name': event,
        'tool_name': tool,
        'tool_input': tool_input,
        'tool_use_id': 't',
    }


def _read(path: Path | str, cwd: Path, more: HookInput | None = None, tool: str = 'Read') -> HookCall:
    """A PreToolUse payload as the lead's Read sends it; `more` adds to `tool_input`."""
    return _payload('PreToolUse', tool, cwd, {'file_path': str(path), **(more or {})})


def _run(command: str, cwd: Path, more: HookInput | None = None) -> HookCall:
    """A PreToolUse payload as the lead's Bash sends it, before the command runs; `more` adds to `tool_input`."""
    return _payload('PreToolUse', 'Bash', cwd, {'command': command, 'description': 'd', **(more or {})})


def _bash(stdout: str, stderr: str = '', command: str = SHELL, saved: HookResponse | None = None) -> HookCall:
    """A PostToolUse payload as the lead's Bash sends it after a command that succeeded; `saved` adds to
    `tool_response`."""
    call = _payload('PostToolUse', 'Bash', ROOT, {'command': command})
    call['tool_response'] = {
        'stdout': stdout,
        'stderr': stderr,
        'interrupted': False,
        'isImage': False,
        'noOutputExpected': False,
        **(saved or {}),
    }
    return call


def _failed(error: str, command: str = SHELL) -> HookCall:
    """A PostToolUseFailure payload as the lead's Bash sends it after a command that failed: `error` holds "Exit code
    N", then the output (measured 2026-11-19)."""
    call = _payload('PostToolUseFailure', 'Bash', ROOT, {'command': command})
    call['error'] = error
    call['is_interrupt'] = False
    return call


def _says(text: str | None, *said: str) -> str:
    """`text`, a refusal or a note that says each of `said`."""
    assert isinstance(text, str), text
    for part in said:
        assert part in text, (part, text)
    return text


def _check(reason: str | None, said: str | None) -> None:
    """`reason` is None if `said` is, else a refusal that says `said`."""
    if said is None:
        assert reason is None, reason
    else:
        _says(reason, said)


def test_a_whole_read_of_a_file_over_20_kb_is_refused_with_its_size_and_the_ways_on(tmp_path: Path) -> None:
    # 30,000 bytes in 300 lines, an empty line 301 after the last newline, and each line's number and a tab before it:
    # 1,096 bytes
    reason = _hook().read_refusal(_read(_big(tmp_path / 'big.py'), tmp_path))
    _says(reason, '32 KB', '301 lines', 'big.py', 'Read fewer lines with `offset` and `limit`, or ask the `analyst`')


def test_a_whole_read_just_over_the_limit_is_refused_and_one_at_it_passes(tmp_path: Path) -> None:
    # one line, and Read's 2 bytes of number before it, `1\t`: 20,000 bytes returned, then 20,001
    at, over = tmp_path / 'at.py', tmp_path / 'over.py'
    at.write_bytes(b'x' * 19_998)
    over.write_bytes(b'x' * 19_999)
    assert _hook().read_refusal(_read(at, tmp_path)) is None
    reason = _hook().read_refusal(_read(over, tmp_path))
    _says(reason, '21 KB')  # rounded up: a refused read never shows as 20 KB


def test_the_line_numbers_count_in_the_size(tmp_path: Path) -> None:
    # REVIEW.md AGT-9: 16,000 bytes in 2,000 lines, and the empty line 2001. Read puts each line's number and a tab
    # before it, unpadded (REVIEW.md AGT-19, measured 2026-11-19): 24,898 bytes. PyCharm's read_file shows 2,000 of the
    # 2,001 lines, each after 'L<n>: ', and one line saying how many it cut (measured 2026-11-19): about 28,900 bytes
    short = tmp_path / 'short.py'
    _write(short, ('x' * 7 + '\n') * 2000)
    hook = _hook()
    reason = hook.read_refusal(_read(short, tmp_path))
    _says(reason, '25 KB', '2001 lines')
    reason = hook.read_refusal(_read(short, tmp_path, tool=PYCHARM))
    _says(reason, '29 KB', '2000 lines')


def test_a_range_over_20_kb_is_refused_with_its_size_and_the_ways_on(tmp_path: Path) -> None:
    reason = _hook().read_refusal(_read(_big(tmp_path / 'big.py'), tmp_path, {'offset': 1, 'limit': 250}))
    _says(reason, '26 KB', '250 lines', 'big.py', '`offset`', '`limit`', '`analyst`')


# Read's offset is the first line (1-based) and limit the number of lines. Measured 2026-11-18: offset alone reads to
# the end, limit alone from the first line, an offset of 0 or less from the first line, a limit of 0 or less to the end.
# Read to the end, it shows the empty line 301 after the last newline (measured 2026-11-19). Each line from 100 on is
# 100 bytes and 4 of number: lines 108 to 301 are 20,076 bytes, lines 109 to 301 19,972
@pytest.mark.parametrize(
    ('ranged', 'said'),
    [
        ({'offset': 100, 'limit': 50}, None),
        ({'offset': 50}, '252 lines'),
        ({'offset': 250}, None),
        ({'limit': 250}, '250 lines'),
        ({'limit': 50}, None),
        ({'offset': 0, 'limit': 250}, '250 lines'),
        ({'offset': -3, 'limit': 250}, '250 lines'),
        ({'offset': 100, 'limit': 0}, '202 lines'),
        ({'offset': 100, 'limit': -1}, '202 lines'),
        ({'offset': 108, 'limit': 0}, '194 lines'),
        ({'offset': 109, 'limit': 0}, None),
    ],
)
def test_a_range_is_sized_by_the_lines_read_returns(tmp_path: Path, ranged: HookInput, said: str | None) -> None:
    _check(_hook().read_refusal(_read(_big(tmp_path / 'big.py'), tmp_path, ranged)), said)


@pytest.mark.parametrize('ranged', [{'offset': '1', 'limit': 250}, {'offset': True}, {'limit': 2.5}])
def test_a_range_it_cant_read_passes(tmp_path: Path, ranged: HookInput) -> None:
    assert _hook().read_refusal(_read(_big(tmp_path / 'big.py'), tmp_path, ranged)) is None


def test_a_range_of_a_file_it_cant_measure_or_lets_through_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook = _hook()
    monkeypatch.setitem(vars(hook), 'PLAN', tmp_path / 'PLAN.md')
    ranged: HookInput = {'offset': 1, 'limit': 250}
    for path in (tmp_path / 'missing.py', _big(tmp_path / 'shot.png'), _big(tmp_path / 'PLAN.md')):
        assert hook.read_refusal(_read(path, tmp_path, ranged)) is None, path
    assert hook.read_refusal(_read(_big(tmp_path / 'big.py'), tmp_path, ranged)) is not None


def test_a_range_given_as_null_is_a_whole_read(tmp_path: Path) -> None:
    assert _hook().read_refusal(_read(_big(tmp_path / 'big.py'), tmp_path, {'offset': None, 'limit': None})) is not None


def test_the_repositorys_plan_is_read_whole_and_no_other_file_of_that_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook = _hook()
    assert Path(hook.PLAN) == Path(ROOT, 'PLAN.md').resolve(), 'the PLAN.md at the root of the repository'
    # REVIEW.md AGT-102: AGENTS.md says to read it before anything else, not to read it whole
    assert 'read it before anything else' in flat(agents_md())
    source = HOOK.read_text(encoding='utf-8')
    assert (
        'PLAN.md, which AGENTS.md says to read before anything else' in source
        and 'read whole (AGENTS.md)' not in source
    )
    monkeypatch.setitem(vars(hook), 'PLAN', tmp_path / 'PLAN.md')
    assert hook.read_refusal(_read(_big(tmp_path / 'PLAN.md'), tmp_path)) is None
    assert hook.read_refusal(_read(_big(tmp_path / 'docs' / 'PLAN.md'), tmp_path)) is not None
    # REVIEW.md AGT-38: PyCharm's read_file too, which finds a relative PLAN.md from its project, not from the call's
    # cwd, where another PLAN.md is
    monkeypatch.setitem(vars(hook), 'PROJECT', str(tmp_path))
    docs = tmp_path / 'docs'
    assert hook.read_refusal(_read('PLAN.md', docs, tool=PYCHARM)) is None, "the project's PLAN.md"
    assert hook.read_refusal(_read(tmp_path / 'PLAN.md', docs, tool=PYCHARM)) is None
    assert hook.read_refusal(_read('docs/PLAN.md', docs, tool=PYCHARM)) is not None


# '..png' as pathlib reads it: a PNG, while os.path.splitext finds no extension
@pytest.mark.parametrize(
    'name', ['shot.png', 'a.jpg', 'a.jpeg', 'a.gif', 'a.webp', 'SHOT.PNG', 'a.pdf', 'a.ipynb', '..png']
)
def test_images_pdfs_and_notebooks_pass(tmp_path: Path, name: str) -> None:
    assert _hook().read_refusal(_read(_big(tmp_path / name), tmp_path)) is None


def test_a_path_it_cant_measure_passes(tmp_path: Path) -> None:
    hook = _hook()
    assert hook.read_refusal(_read(tmp_path / 'missing.py', tmp_path)) is None
    assert hook.read_refusal(_read(tmp_path, tmp_path)) is None  # a folder: not a regular file


def test_reads_relative_path_is_measured_from_the_calls_cwd(tmp_path: Path) -> None:
    # Read took `mypy.ini` for the file in the session's folder (measured 2026-11-19)
    _big(tmp_path / 'project' / 'sub' / 'big.py')
    hook = _hook()
    assert hook.read_refusal(_read('sub/big.py', tmp_path / 'project')) is not None
    assert hook.read_refusal(_read('../project/sub/big.py', tmp_path / 'project')) is not None
    assert hook.read_refusal(_read('sub/big.py', tmp_path)) is None  # no such file from there


def test_pycharms_relative_path_is_measured_from_its_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md AGT-3: read_file reads a relative path from its project, `projectPath` when the call gives one, else
    # the repository's, whatever folder an earlier `cd` left as the call's cwd
    hook = _hook()
    monkeypatch.setitem(vars(hook), 'PROJECT', str(tmp_path / 'repo'))
    _big(tmp_path / 'repo' / 'sub' / 'big.py')
    _big(tmp_path / 'other' / 'sub' / 'big.py', 50)
    _big(tmp_path / 'cwd' / 'sub' / 'big.py', 50)
    _big(tmp_path / 'cwd' / 'only_here.py')
    cwd = tmp_path / 'cwd'
    assert hook.read_refusal(_read('sub/big.py', cwd, tool=PYCHARM)) is not None, "the repository's file"
    assert hook.read_refusal(_read('only_here.py', cwd, tool=PYCHARM)) is None, 'no such file in the repository'
    other: HookInput = {'projectPath': str(tmp_path / 'other')}
    assert hook.read_refusal(_read('sub/big.py', cwd, other, tool=PYCHARM)) is None, "the other project's file"
    assert hook.read_refusal(_read('../repo/sub/big.py', cwd, other, tool=PYCHARM)) is not None


def test_a_refused_read_file_names_its_file_by_the_absolute_path_read_finds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md AGT-34: the refusal sends a read_file to Read for a range. Read finds a relative path from the call's
    # cwd, and read_file from its project, so the refusal names the file the hook measured by its absolute path
    hook = _hook()
    monkeypatch.setitem(vars(hook), 'PROJECT', str(tmp_path / 'repo'))
    cwd = tmp_path / 'cwd'
    big = _big(tmp_path / 'repo' / 'sub' / 'big.py')
    _says(hook.read_refusal(_read('sub/big.py', cwd, tool=PYCHARM)), ' lines of %s, line numbers' % big)
    other = _big(tmp_path / 'other' / 'sub' / 'big.py')
    project: HookInput = {'projectPath': str(tmp_path / 'other')}
    _says(hook.read_refusal(_read('sub/big.py', cwd, project, tool=PYCHARM)), ' lines of %s, line numbers' % other)


def test_pycharms_project_is_the_repository() -> None:
    assert Path(_hook().PROJECT) == Path(ROOT).resolve()


def test_reads_leading_tilde_names_the_home_folder_and_read_files_doesnt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Read takes the blanks off around the path and expands a leading `~/`. PyCharm's read_file expands no `~`
    # (measured 2026-11-19, REVIEW.md AGT-23). USERPROFILE is Windows' home folder
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    _big(tmp_path / 'big.py')
    elsewhere = tmp_path / 'elsewhere'
    for path in ('~/big.py', ' ~/big.py', '\t~/big.py  '):
        _says(_hook().read_refusal(_read(path, elsewhere)), '32 KB', path)
    assert _hook().read_refusal(_read('~/big.py', elsewhere, {'projectPath': str(elsewhere)}, PYCHARM)) is None


def test_a_trailing_slash_names_the_file(tmp_path: Path) -> None:
    # Read takes big.py/ for big.py and reads the whole file (measured 2026-11-18)
    big = str(_big(tmp_path / 'big.py'))
    for path in (big + '/', big + '/.'):
        assert _hook().read_refusal(_read(path, tmp_path)) is not None, path


def test_a_url_or_an_archive_entry_passes_even_where_a_file_has_that_name(tmp_path: Path) -> None:
    # each would name a big file if it were read as a path: the hook must not measure it. Windows file names can't hold
    # a colon
    if sys.platform != 'win32':
        _big(tmp_path / 'jar:' / 'big.class')
    _big(tmp_path / 'lib.jar!' / 'pkg' / 'Foo.class')
    hook = _hook()
    assert hook.read_refusal(_read('jar://big.class', tmp_path)) is None
    assert hook.read_refusal(_read(str(tmp_path / 'lib.jar') + '!/pkg/Foo.class', tmp_path)) is None


WEB_CALLS: list[tuple[str, HookInput]] = [
    ('WebFetch', {'url': 'https://code.claude.com/docs/en/settings', 'prompt': 'the bashOutputMaxChars entry'}),
    ('WebSearch', {'query': 'bashOutputMaxChars'}),
]


@pytest.mark.parametrize(('tool', 'tool_input'), WEB_CALLS)
def test_the_leads_web_fetch_and_search_go_to_the_analyst(tmp_path: Path, tool: str, tool_input: HookInput) -> None:
    # the user, 2026-11-19: every web fetch and search of the lead's goes to the analyst, as a fetch may return a whole
    # page into the context (the hook's docstring). A subagent's call passes
    call = _payload('PreToolUse', tool, tmp_path, tool_input)
    refusal = _says(
        _hook().web_refusal(call), 'Blocked', '`analyst`', 'the docstring of `.claude/hooks/large_reads.py`'
    )
    # the figure the refusal gives is in the docstring it points to (REVIEW.md AGT-82)
    assert '100,000 characters' in refusal and '100,000 characters' in flat(_hook().__doc__ or '')
    assert _hook().web_refusal({**call, 'agent_id': 'a1', 'agent_type': 'analyst'}) is None
    assert _hook().web_refusal(_read(_big(tmp_path / 'big.py'), tmp_path)) is None  # a read is read_refusal's


def test_a_subagents_read_passes(tmp_path: Path) -> None:
    # a large read inside the analyst is its job
    call = _read(_big(tmp_path / 'big.py'), tmp_path)
    assert _hook().read_refusal(call) is not None
    assert _hook().read_refusal({**call, 'agent_id': 'a1', 'agent_type': 'analyst'}) is None


def test_pycharms_read_file_is_treated_like_read(tmp_path: Path) -> None:
    hook = _hook()
    big = _big(tmp_path / 'big.py')
    assert hook.read_refusal(_read(big, tmp_path, tool=PYCHARM)) is not None
    assert hook.read_refusal(_read(big, tmp_path, {'offset': 1, 'limit': 20}, tool=PYCHARM)) is None
    # lines 1 to 125 and 177 to 301 of 100 bytes and 4 to 6 of number, and the line saying it cut 51
    reason = hook.read_refusal(_read(big, tmp_path, {'offset': 1, 'limit': 250}, tool=PYCHARM))
    # read_file's limit keeps the start and the end of what follows offset, not a range (measured 2026-11-18, the
    # hook's docstring): the refusal sends a range to Read
    sent_to_read = (
        'the `Read` tool with `offset` and `limit`',
        "`read_file`'s `limit` keeps",
        '), or ask the `analyst`',
    )
    _says(reason, '27 KB', '250 lines', *sent_to_read)
    # its limit is 2000 lines when not given
    assert hook.read_refusal(_read(big, tmp_path, {'offset': 50}, tool=PYCHARM)) is not None
    assert hook.read_refusal(_read(big, tmp_path, {'offset': 250}, tool=PYCHARM)) is None


def test_pycharms_read_file_is_sized_by_the_lines_it_shows(tmp_path: Path) -> None:
    # read_file shows the lines from offset to the end, cut in the middle to limit lines, and an empty line after a
    # last newline (measured 2026-11-18): here the first 20 short lines and the last 19 long ones, 38,276 bytes with
    # the numbers and the line saying it cut 91
    path = tmp_path / 'ends_long.py'
    _write(path, 'x\n' * 100 + ('y' * 1999 + '\n') * 30)
    hook = _hook()
    reason = hook.read_refusal(_read(path, tmp_path, {'offset': 1, 'limit': 40}, tool=PYCHARM))
    _says(reason, '39 KB', '40 lines')
    assert hook.read_refusal(_read(path, tmp_path, {'offset': 1, 'limit': 40})) is None, 'Read: 40 short lines'


def test_pycharms_whole_read_is_sized_by_the_2000_lines_it_shows(tmp_path: Path) -> None:
    # REVIEW.md AGT-8: 30,000 bytes in 15,000 lines. Without `limit`, read_file shows 2,000 of them (measured
    # 2026-11-18): about 18 KB with their numbers. Read returns all of them, and their numbers: about 135 KB
    path = tmp_path / 'many_short_lines.py'
    _write(path, 'x\n' * 15_000)
    hook = _hook()
    assert hook.read_refusal(_read(path, tmp_path, tool=PYCHARM)) is None
    assert hook.read_refusal(_read(path, tmp_path)) is not None
    reason = hook.read_refusal(_read(_big(tmp_path / 'big.py', 3000), tmp_path, tool=PYCHARM))
    _says(reason, '2000 lines')


# read_file answers an error, offset must be > 0 or limit must be > 0 or <= 5000 (measured 2026-11-18): nothing
# reaches the context. A last line of 25,000 bytes would be over the limit alone
@pytest.mark.parametrize(
    'ranged', [{'offset': 0, 'limit': 250}, {'offset': -1}, {'limit': 0}, {'limit': -1}, {'limit': 5001}]
)
def test_a_range_pycharms_read_file_refuses_passes(tmp_path: Path, ranged: HookInput) -> None:
    path = tmp_path / 'ends_long.py'
    _write(path, LINE * 300 + 'y' * 25_000)
    assert _hook().read_refusal(_read(path, tmp_path, ranged, tool=PYCHARM)) is None


def test_the_docstring_gives_the_ranges_pycharms_read_file_refuses() -> None:
    # the errors the test above relies on, as measured
    docstring = flat(_hook().__doc__ or '')
    assert 'An `offset` under 1, or a `limit` under 1 or over 5,000, got an error and no lines.' in docstring
    assert (
        "So did an `offset` past the file's last line: `offset=10000, limit=1` on `mypy.ini`, far shorter, got only the"
        ' error `offset exceeds file length` (measured by the lead, 2026-11-20).' in docstring
    )
    # REVIEW.md AGT-109: where the error starts, as `_has_line` counts the lines
    assert (
        'The first `offset` that got it was one past the last line, the empty line after a last newline counted, as'
        ' `_has_line` takes it. On a file of `a`, a newline and `b`, `offset=2` showed `L2: b` and `offset=3` got the'
        ' error. With a newline after `b`, `offset=3` showed the empty `L3: ` and `offset=4` got it (measured by the'
        ' lead, 2026-11-20).' in docstring
    )


def test_the_hooks_docstring_holds_no_control_character() -> None:
    # REVIEW.md AGT-110: in a docstring that isn't raw, `\r` written as two characters reads as a carriage return
    assert [char for char in _hook().__doc__ or '' if char < ' ' and char != '\n'] == []


@pytest.mark.parametrize('before', [300, 10_000])  # lines of 100 bytes before the long last one: under BIG, then over
@pytest.mark.parametrize('end', ['', '\n'])  # after a last newline, read_file numbers an empty line
def test_read_file_from_past_the_last_line_passes_and_from_the_last_lines_is_sized(
    tmp_path: Path, before: int, end: str
) -> None:
    # REVIEW.md AGT-108: read_file answers an `offset` past the last line it numbers with an error and no lines (the
    # test above), which the hook sizes as None, its answer for read_file's errors. Over BIG with `limit=1`, the hook
    # read the file's last line back from its end without checking that line `offset` was in the file, and refused the
    # call. From the long line, read_file shows its 25,000 bytes, over the limit alone, unless the empty line after it
    # is the one line `limit=1` keeps from the end
    path = _write(tmp_path / 'ends_long.log', LINE * before + 'y' * 25_000 + end)
    hook = _hook()
    long, last = before + 1, before + 1 + len(end)  # the long line, and the last line read_file numbers

    def refused(offset: int, limit: int) -> bool:
        return hook.read_refusal(_read(path, tmp_path, {'offset': offset, 'limit': limit}, tool=PYCHARM)) is not None

    for limit in (1, 2):
        for past in (last + 1, 10_000_000):
            assert hook._returned(str(path), True, past, limit) is None, (past, limit)
            assert not refused(past, limit), (past, limit)
        assert refused(long, limit) == (limit == 2 or not end), limit
        if end:  # from the empty line, read_file shows it alone
            assert not refused(last, limit), limit


def test_pycharms_notebook_is_sized_by_the_text_it_shows(tmp_path: Path) -> None:
    # REVIEW.md AGT-46: read_file shows a notebook as text (measured 2026-11-19, the hook's docstring). Each cell is a
    # line `#%%`, `#%% md` or `#%% ` and its type, then its source, with `\r\n` and `\r` as newlines and a `#` before a
    # line starting with `#%%`. Newlines join the cells, and their outputs and metadata don't show. Each `p` adds a byte
    shown = '#%%\n##%%\nx = 1\ny\nz\n\n#%% md\né€😀 # %%\n#%% md\n\n#%% raw\nraw\n  #%% kept\n#%% md\n'
    padding = _hook().READ_LIMIT - _returned(shown)

    def notebook(pad: int) -> Path:
        return write_notebook(
            tmp_path / 'cells.ipynb',
            cell('code', ['#%%\n', 'x = 1\r\n', 'y\r', 'z\n']),
            cell('markdown', 'é€😀 # %%'),
            cell('markdown', []),
            cell('raw', ['raw\n', '  #%% kept']),
            cell('markdown', ['p' * pad]),
        )

    assert _hook().read_refusal(_read(notebook(padding), tmp_path, tool=PYCHARM)) is None, 'exactly 20,000 bytes'
    _says(_hook().read_refusal(_read(notebook(padding + 1), tmp_path, tool=PYCHARM)), '21 KB and 15 lines')
    assert _hook().read_refusal(_read(notebook(padding + 1), tmp_path)) is None, "Read's notebooks pass, as they did"


def test_a_notebook_whose_text_it_cant_rebuild_passes(tmp_path: Path) -> None:
    # the hook rebuilds only the text it measured read_file showing: not a notebook it can't parse, nor a cell whose
    # source isn't text
    broken = tmp_path / 'broken.ipynb'
    broken.write_text('{"cells": [' + '"x", ' * 10_000, encoding='utf-8')
    odd = write_notebook(tmp_path / 'odd.ipynb', {'cell_type': 'code', 'source': 3}, cell('code', LINE * 300))
    for path in (broken, odd):
        assert _hook().read_refusal(_read(path, tmp_path, tool=PYCHARM)) is None, path


def test_a_refused_notebook_isnt_sent_to_read(tmp_path: Path) -> None:
    # REVIEW.md AGT-49: Read shows a notebook's cells unsized, so a refused read_file of a notebook offers read_file
    # with a smaller `limit`, and a refused command printing one offers `head` and `sed -n`
    write_notebook(tmp_path / 'cells.ipynb', cell('code', LINE * 300))
    hook = _hook()
    reason = _says(
        hook.read_refusal(_read(tmp_path / 'cells.ipynb', tmp_path, tool=PYCHARM)),
        "Read fewer lines with `read_file`'s `offset` and a smaller `limit`",
        '`analyst`',
    )
    assert 'use the `Read` tool' not in reason, reason
    reason = _says(hook.bash_refusal(_run('cat cells.ipynb', tmp_path)), 'Print fewer lines with `head` or `sed -n`')
    assert "Read tool's `offset`" not in reason, reason


@pytest.mark.parametrize('end', ['\r\n', '\r'])
def test_pycharms_read_file_ends_a_line_at_crlf_and_at_a_lone_cr(tmp_path: Path, end: str) -> None:
    # read_file ends a line at LF, CRLF or a lone CR, and shows no CR (measured 2026-11-19, the hook's docstring): 180
    # lines, then `p`s, are exactly 20,000 bytes as read_file shows them, ended so
    hook = _hook()
    lines = LINE * 180
    padding = hook.READ_LIMIT - _returned(lines)
    at, over = tmp_path / 'at.txt', tmp_path / 'over.txt'
    _write(at, (lines + 'p' * padding).replace('\n', end))
    _write(over, (lines + 'p' * (padding + 1)).replace('\n', end))
    assert hook.read_refusal(_read(at, tmp_path, tool=PYCHARM)) is None, 'exactly 20,000 bytes'
    _says(hook.read_refusal(_read(over, tmp_path, tool=PYCHARM)), '21 KB and 181 lines')
    # Read ends a line only at LF: a file of lines ended by a lone CR shows as one line
    big = _big(tmp_path / 'big.txt', end=end)
    _says(hook.read_refusal(_read(big, tmp_path)), 'KB and %d lines' % (301 if end == '\r\n' else 1))


def test_a_crlf_across_the_bytes_read_at_a_time_is_one_line_end(tmp_path: Path) -> None:
    # the hook reads a file BLOCK bytes at a time: a CR ending them is a lone one only if no LF follows. Two lines here,
    # each after 4 bytes of number: 20,000 bytes
    block = _hook().BLOCK
    split = tmp_path / 'split.txt'
    split.write_bytes(b'x' * (block - 1) + b'\r\n' + b'y' * (_hook().READ_LIMIT - block - 8))
    assert _hook().read_refusal(_read(split, tmp_path, tool=PYCHARM)) is None


def test_pycharms_file_url_is_sized_as_its_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md AGT-46: read_file reads `file://` and an absolute path as that path, as written. It didn't decode `%41`,
    # and `file://localhost/` or `file://` and a relative path found no file (measured 2026-11-19). Read's URLs pass
    hook = _hook()
    monkeypatch.setitem(vars(hook), 'PROJECT', str(tmp_path))
    named = _big(tmp_path / 'b%41.py')
    _big(tmp_path / 'aA.py')
    _says(hook.read_refusal(_read('file://%s' % named, tmp_path, tool=PYCHARM)), '32 KB', ' of %s, line' % named)
    for url in ('file://%s' % (tmp_path / 'a%41.py'), 'file://localhost%s' % named, 'file://aA.py'):
        assert hook.read_refusal(_read(url, tmp_path, tool=PYCHARM)) is None, url
    assert hook.read_refusal(_read('file://%s' % named, tmp_path)) is None


@pytest.mark.skipif(
    sys.platform == 'win32', reason='a symlink, which Windows guards, and the tools as measured on macOS'
)
@pytest.mark.parametrize('tool', ['Read', PYCHARM])
def test_a_dot_dot_after_a_symlink_is_read_lexically(tmp_path: Path, tool: str) -> None:
    # REVIEW.md AGT-96: Read and PyCharm's read_file read `link/../x` as the `x` beside `link`, while the system opens
    # the `x` beside the link's target (measured 2026-11-20). Here the first is over the limit and the second under
    # it, then the other way round
    project, _ = _linked(tmp_path)
    refused = _hook().read_refusal(_read(project / 'link' / '..' / 'big.py', project, tool=tool))
    _says(refused, '301 lines')  # and the empty line after the last newline
    if tool == PYCHARM:  # named by the path it measured, which Read finds as read_file did
        _says(refused, ' of %s, ' % (project / 'big.py'))
    assert _hook().read_refusal(_read(project / 'link' / '..' / 'sub' / 'big.py', project, tool=tool)) is None


def test_a_command_printing_a_file_over_20_kb_is_refused_with_its_size_and_the_ways_on(tmp_path: Path) -> None:
    _big(tmp_path / 'big.py')
    refused = _hook().bash_refusal(_run('cat big.py', tmp_path))
    reason = _says(refused, '30 KB', '300 lines', 'big.py', '`offset`', '`limit`', '`head`', '`sed -n`', '`analyst`')
    # REVIEW.md AGT-5: Claude Code puts only part of a big output into the context (measured 2026-11-18 and
    # 2026-11-19): the reason says so, and not that it fills it
    assert 'only part' in reason and 'fills' not in reason, reason


# Claude Code's shell runs macOS's (BSD) head, tail and sed: what each prints was measured 2026-11-18
@pytest.mark.parametrize(
    ('command', 'said'),
    [
        ('cat big.py', '300 lines'),
        ('cat small.py', None),
        ('head -n 5000 big.py', '300 lines'),
        ('head -n 20 big.py', None),
        ('head big.py', None),  # 10 lines
        ('head -250 big.py', '250 lines'),
        ('head -n250 big.py', '250 lines'),
        ('head -n +250 big.py', '250 lines'),
        ('tail -n +2 big.py', '299 lines'),
        ('tail -n+2 big.py', '299 lines'),
        ('tail -n 20 big.py', None),
        ('tail -n 250 big.py', '250 lines'),
        ('tail -n -250 big.py', '250 lines'),
        ('tail -250 big.py', '250 lines'),
        ('tail -n 0 big.py', None),  # nothing
        ('tail -n +0 big.py', '300 lines'),  # from the first line
        ('tail -n +102 big.py', None),
        ('tail big.py', None),
        ("sed -n '1,5000p' big.py", '300 lines'),
        ("sed -n '1,20p' big.py", None),
        ("sed -n '50,$p' big.py", '251 lines'),
        ('sed -n 50,300p big.py', '251 lines'),
        ("sed -n '250p' big.py", None),
        ("sed -n '300,1p' big.py", None),  # line 300 alone
        ('cat small.py small.py', None),
        ('cat half.py half.py', '300 lines'),
        ('cat half.py; cat half.py', '300 lines'),
        ('cat half.py && head -n 150 half.py', '300 lines'),
        ('cat half.py || tail -n +1 half.py', '300 lines'),
        ('ls && git log -3 && cat small.py && cat small.py', None),
        ("cat 'a big.py'", '300 lines'),
        ('cat big.py # a comment', '300 lines'),
        ('echo # ; cat big.py', None),  # the comment holds the second command
        ('cat big.py;# a comment', '300 lines'),
        # REVIEW.md AGT-6: a quoted or escaped # begins no comment, nor one inside a word
        ("grep -c '# type: ignore' small.py && cat big.py", '300 lines'),
        ('grep -c "#" small.py && cat big.py', '300 lines'),
        ('grep -c \\# small.py && cat big.py', '300 lines'),
        ("grep -c x'#' small.py && cat big.py", '300 lines'),
        ('grep -c x#y small.py && cat big.py', '300 lines'),
        ('cd sub && cat deep.py', '300 lines'),  # only sub has deep.py
        ('cd sub; cat big.py', None),  # sub's big.py is small
        ('chdir sub && cat deep.py', '300 lines'),  # zsh's chdir is cd (REVIEW.md AGT-20)
        ('chdir sub; cat big.py', None),
        # REVIEW.md AGT-91: a cd that may not run ends the sizing, and one that runs before every later command doesn't
        ('cat big.py || cd sub; cat big.py', '300 lines'),
        ('true && cd sub && cat deep.py', '300 lines'),
        ('cd sub || true; cat deep.py', '300 lines'),  # only sub has deep.py (REVIEW.md TST-616)
        # the folder is known up to a command of MOVES, and a word of another command moves nothing
        ('cat big.py; eval x', '300 lines'),
        ('cat big.py; pushd sub', '300 lines'),
        ('grep -n source small.py; cat big.py', '300 lines'),
        ('git log -- eval && cat big.py', '300 lines'),
        ('command cd sub; cat big.py', '300 lines'),  # none of these moved zsh's folder (2026-11-19)
        ('env cd sub; cat big.py', '300 lines'),
        ('coproc cd sub; cat big.py', '300 lines'),
    ],
)
def test_a_command_is_sized_by_the_lines_it_prints(tmp_path: Path, command: str, said: str | None) -> None:
    for name in ('big.py', 'a big.py', 'sub/deep.py'):
        _big(tmp_path / name)
    for name, lines in (('small.py', 50), ('half.py', 150), ('sub/big.py', 50)):
        _big(tmp_path / name, lines)
    _check(_hook().bash_refusal(_run(command, tmp_path)), said)


@pytest.mark.parametrize(
    'command',
    [
        'cat big.py | grep x',  # the file reaches grep, not the context
        'cat big.py |& grep x',
        'cat big.py > out.txt',  # a redirection: the hook doesn't size the line
        'cat big.py 2>/dev/null',
        'cat < big.py',
        'cat big.py &',
        'cat $(echo big.py)',  # a subshell's operator, and $
        'cat `echo big.py`',  # its words are `echo and big.py`
        'cat $HOME/big.py',
        'cat "$F"',
        'cat *.py',  # the shell expands the glob: not sized
        'cat big.?y',
        'cat ~/big.py',
        'cat {big,small}.py',
        'cat -n big.py',  # an option it doesn't size
        'head -c 30000 big.py',
        'tail -f big.py',
        'sed -n -e 1,300p big.py',
        "sed -n '1,300p;5p' big.py",
        "sed -n '0,300p' big.py",
        "sed '1,300p' big.py",
        "sed -n '1,300p' big.py big.py",
        'head -n 0 big.py',  # an error: nothing printed
        'head -n -5 big.py',
        'cat',  # reads stdin
        'cat missing.py',
        'cat missing.py && cat big.py',
        'cat sub',  # a folder
        'cd missing && cat big.py',
        'cd && cat big.py',
        'cd sub other && cat big.py',
        'chdir missing && cat big.py',
        'pushd sub && cat big.py',
        'popd; cat big.py',
        # REVIEW.md AGT-20: a cd the hook doesn't follow. Each of these moved zsh's folder (2026-11-19)
        'builtin cd sub; cat big.py',
        'noglob cd sub; cat big.py',
        'nocorrect cd sub; cat big.py',
        '- cd sub; cat big.py',
        'X=1 cd sub; cat big.py',
        'time cd sub; cat big.py',
        '! cd sub; cat big.py',
        'if cd sub; then true; fi; cat big.py',
        'if true; then cd sub; fi; cat big.py',
        'if false; then true; else cd sub; fi; cat big.py',
        'if false; then true; elif cd sub; then true; fi; cat big.py',
        'while cd sub; do break; done; cat big.py',
        'until cd sub; do true; done; cat big.py',
        'for d in a; do cd sub; done; cat big.py',
        'repeat 1 cd sub; cat big.py',
        'eval cd sub; cat big.py',
        "eval 'cd sub'; cat big.py",
        '{ cd sub }; cat big.py',
        'source x; cat big.py',
        '. x; cat big.py',
        # REVIEW.md AGT-91: a cd that may not run while a command after it does: after `||`, or after `&&` with another
        # separator later
        'true || cd sub; cat big.py',
        'true || cd sub && cat big.py',
        'false && cd sub; cat big.py',
        'false && cd sub || cat big.py',
        'true || chdir sub; cat big.py',
        # a cd zsh refused: `missing` names no folder, though `sub` does (measured 2026-11-20)
        'cd missing/../sub; cat big.py',
        # a printer named by a path, after an assignment or after another word isn't sized
        '/bin/cat big.py',
        'X=1 cat big.py',
        'command cat big.py',
        'env cat big.py',
        'exec cat big.py',
        'nice cat big.py',
        'time cat big.py',
        "cat 'big.py",  # a quote never closed
        'cat big.py\n',  # a newline: the shell reads a command after it
        'cat big.py\r',
        '; cat big.py',
        'cat big.py ;; cat big.py',
        '',
    ],
)
def test_a_command_it_cant_size_passes(tmp_path: Path, command: str) -> None:
    # a file named as each word reads before the shell expands it, so that only the hook's rules let it through.
    # Windows file names can't hold * or ?
    names = ['big.py', 'sub/big.py', '~/big.py', '$HOME/big.py', '$F', '{big,small}.py', '`echo', 'big.py`']
    for name in names if sys.platform == 'win32' else [*names, '*.py', 'big.?y']:
        _big(tmp_path / name)
    assert _hook().bash_refusal(_run(command, tmp_path)) is None


def test_a_command_is_sized_from_the_calls_cwd(tmp_path: Path) -> None:
    big = _big(tmp_path / 'project' / 'big.py')
    hook = _hook()
    assert hook.bash_refusal(_run('cat big.py', tmp_path / 'project')) is not None
    assert hook.bash_refusal(_run('cat big.py', tmp_path)) is None
    assert hook.bash_refusal(_run('cat %s' % shlex.quote(str(big)), tmp_path)) is not None
    assert hook.bash_refusal(_run('cd %s && cat big.py' % shlex.quote(str(big.parent)), tmp_path)) is not None
    assert hook.bash_refusal(_run('cd project && cat big.py', tmp_path)) is not None


def test_a_refused_command_names_its_files_by_the_absolute_paths_read_finds(tmp_path: Path) -> None:
    # REVIEW.md AGT-48: the refusal sends the lead to Read, which finds a relative path from the call's cwd. The refused
    # command's `cd` never ran, so the refusal names each file by the absolute path the hook measured
    deep = _big(tmp_path / 'sub' / 'deep.py')
    half = _big(tmp_path / 'half.py', 150)
    _says(_hook().bash_refusal(_run('cd sub && cat deep.py', tmp_path)), ' of %s, and' % deep)
    _says(
        _hook().bash_refusal(_run('cat half.py && cd sub && cat deep.py', tmp_path)), ' of %s, %s, and' % (half, deep)
    )


@pytest.mark.skipif(sys.platform == 'win32', reason="zsh's cd, measured on macOS, and a symlink, which Windows guards")
def test_a_cd_reads_dot_dot_after_a_symlink_as_zsh_does(tmp_path: Path) -> None:
    # REVIEW.md AGT-91: zsh's cd reads a path logically where it can, and else physically (the hook's docstring,
    # measured 2026-11-20)
    project, elsewhere = _linked(tmp_path)
    for command in ('cd link/.. && cat big.py', 'cd link; cd ..; cat big.py', 'cd link/./../ && cat big.py'):
        _says(_hook().bash_refusal(_run(command, project)), ' of %s, and' % (project / 'big.py'))
    # `project/only` is no folder, nor `project/q`, so zsh reads these physically. The refusal names the file there by
    # its real path, as Read reads a `..` lexically (REVIEW.md AGT-91)
    for command, folder in (('cd link/../only', 'only'), ('cd link/../q/../sub', 'sub')):
        printed = (elsewhere / folder / 'big.py').resolve()
        _says(_hook().bash_refusal(_run(command + ' && cat big.py', project)), ' of %s, and' % printed)


@pytest.mark.skipif(sys.platform == 'win32', reason="zsh's cd, measured on macOS, and a symlink, which Windows guards")
def test_a_function_or_a_shell_option_set_earlier_in_the_line_moves_the_folder_unseen(tmp_path: Path) -> None:
    # REVIEW.md AGT-105: the hook follows neither a function nor a shell option (its docstring, measured 2026-11-20), so
    # it sizes the big `big.py` of the folder it followed, where zsh's `cat big.py` printed a small file
    project, _ = _linked(tmp_path)
    for command in ('function f { cd sub }; f; cat big.py', 'setopt chase_dots; cd link/.. && cat big.py'):
        _says(_hook().bash_refusal(_run(command, project)), ' of %s, and' % (project / 'big.py'))
    docstring = flat(_hook().__doc__ or '')
    assert "A function or a shell option, from the user's profile or set earlier in the line, moves" in docstring


@pytest.mark.skipif(sys.platform == 'win32', reason='a symlink, which Windows guards, and cat as measured on macOS')
def test_a_refused_file_is_named_by_the_real_path_cat_opens(tmp_path: Path) -> None:
    # REVIEW.md AGT-95: cat opens `link/../sub/big.py` physically, the big file in `elsewhere` (measured 2026-11-20),
    # while Read reads the `..` of the joined path lexically, the small `project/sub/big.py`. The refusal names the file
    # cat prints by its real path, which Read finds as cat did
    project, elsewhere = _linked(tmp_path)
    printed = (elsewhere / 'sub' / 'big.py').resolve()
    _says(_hook().bash_refusal(_run('cat link/../sub/big.py', project)), '300 lines', ' of %s, and' % printed)


def test_a_subagents_command_passes(tmp_path: Path) -> None:
    _big(tmp_path / 'big.py')
    call = _run('cat big.py', tmp_path)
    assert _hook().bash_refusal(call) is not None
    assert _hook().bash_refusal({**call, 'agent_id': 'a1', 'agent_type': 'analyst'}) is None


def test_a_command_run_in_the_background_passes(tmp_path: Path) -> None:
    # the user, 2026-11-20: a background call's output goes to a file, not into the lead's context, and the notice of
    # its end carries none. The lead reads that file later, with a Read the hook sizes. After the call, the note still
    # sizes what the call returned
    _big(tmp_path / 'big.py')
    hook = _hook()
    assert hook.bash_refusal(_run('cat big.py', tmp_path)) is not None
    assert hook.bash_refusal(_run('cat big.py', tmp_path, {'run_in_background': True})) is None
    returned = _bash(LINE * 80)
    returned['tool_input'] = {'command': SHELL, 'run_in_background': True}
    assert hook.bash_note(returned) is not None
    assert (
        'A call run in the background (`run_in_background`) is never sized (the user, 2026-11-20). Its output goes to a'
        ' file, not into the context, and the notice of its end carries none (seen by the lead, 2026-11-20).'
    ) in flat(hook.__doc__ or '')


HUGE = 20_000  # lines of 100 bytes: 2 MB, a file over BIG
LITTLE = 60_000  # bytes: what the hook may read of a big file it stops early in, three times READ_LIMIT
OVER = 'returns over 20 KB of %s, line numbers'  # a read's refusal where the hook stopped early


def test_a_big_files_read_is_sized_only_until_it_passes_the_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md AGT-45: in a file over BIG, a whole Read, or one with an offset alone, is sized only until it passes
    # 20 KB, and the refusal says only that. A range near the start still stops at its end
    hook = _hook()
    huge = _big(tmp_path / 'huge.log', HUGE)
    assert huge.stat().st_size > hook.BIG
    counter = _bytes_read(monkeypatch)
    ranges: list[HookInput] = [{}, {'offset': 100}, {'offset': 1, 'limit': 5000}]
    for ranged in ranges:
        with counter.at_most(LITTLE, ranged):
            _says(hook.read_refusal(_read(huge, tmp_path, ranged)), OVER % huge)
    with counter.at_most(LITTLE, 'lines 1 to 50'):
        assert hook.read_refusal(_read(huge, tmp_path, {'offset': 1, 'limit': 50})) is None


def test_a_big_files_read_file_is_sized_only_until_it_passes_the_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md AGT-45: read_file shows the first lines of a file and its last ones (the hook's docstring). In a file
    # over BIG, the hook stops once the first lines pass 20 KB, and reads the last ones back from the end of the file
    hook = _hook()
    huge = _big(tmp_path / 'huge.log', HUGE)
    ends_long = tmp_path / 'ends_long.log'
    _write(ends_long, 'x\n' * 500_000 + LINE * 300)  # 1 MB of short lines, then 30 KB
    counter = _bytes_read(monkeypatch)
    for path in (huge, ends_long):
        with counter.at_most(LITTLE, path):
            _says(hook.read_refusal(_read(path, tmp_path, tool=PYCHARM)), OVER % path)
    # `limit=1` shows the last line alone, here the empty one after the last newline, and the line saying how many it
    # cut: whatever their numbers, far under the limit
    with counter.at_most(LITTLE, 'limit=1'):
        assert hook.read_refusal(_read(huge, tmp_path, {'limit': 1}, tool=PYCHARM)) is None
    # from near the end, the first half holds the rest of the file: 183 lines from 500,001, the last of 144 bytes, and
    # the empty line after them, each after 9 bytes of number. Exactly 20,000 bytes, and 20,011 from the line before
    near_end = tmp_path / 'near_end.log'
    _write(near_end, 'z\n' * 500_000 + LINE * 182 + 'w' * 143 + '\n')
    assert hook.read_refusal(_read(near_end, tmp_path, {'offset': 500_001}, tool=PYCHARM)) is None
    _says(hook.read_refusal(_read(near_end, tmp_path, {'offset': 500_000}, tool=PYCHARM)), 'returns over 20 KB')
    # REVIEW.md AGT-47: the same 184 lines with a limit of 366, whose first half ends before the empty line, and of 368,
    # whose first half holds it
    for limit in (366, 368):
        ranged: HookInput = {'offset': 500_001, 'limit': limit}
        assert hook.read_refusal(_read(near_end, tmp_path, ranged, tool=PYCHARM)) is None, limit
    # short lines at both ends: what the hook reads back can't tell, so it reads the whole file and gives the size. The
    # first 1,000 lines, of 3 bytes, and their numbers are 8,893 bytes. The last 1,000, numbered from 339,002 with the
    # empty line 340,001, are 11,997 bytes, and the line saying read_file cut 338,001 lines is 29: 20,919. read_file
    # ends a line at CRLF and at a lone CR too, and shows no CR: the same 20,919 bytes
    for end in ('\n', '\r\n', '\r'):
        short = _write(tmp_path / 'short.log', ('xx' + end) * 340_000)
        _says(hook.read_refusal(_read(short, tmp_path, tool=PYCHARM)), 'returns 21 KB and 2000 lines')


def test_a_big_files_lines_ended_by_a_lone_cr_are_read_back_from_its_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # in a file over BIG, read_file's last lines are read back from the end of the file, a lone CR ending them too.
    # `limit=1` shows the empty line after the last CR alone
    hook = _hook()
    huge = _big(tmp_path / 'huge.log', HUGE, '\r')
    counter = _bytes_read(monkeypatch)
    with counter.at_most(LITTLE, 'limit=1'):
        assert hook.read_refusal(_read(huge, tmp_path, {'limit': 1}, tool=PYCHARM)) is None
    with counter.at_most(LITTLE, 'a whole read'):
        _says(hook.read_refusal(_read(huge, tmp_path, tool=PYCHARM)), OVER % huge)


def test_a_big_files_last_lines_read_back_count_a_crlf_as_one_byte(tmp_path: Path) -> None:
    # REVIEW.md AGT-62: read_file shows a CRLF as one line end, and the lines read back from the end of a file over BIG
    # are counted so too. Lines 100,001 to 100,050 of `x`, the last 49 of 386 `p` and the empty line after them, with
    # their numbers and the line saying read_file cut 299,901 lines: 19,992 bytes. Each CRLF counted as two bytes would
    # put the lower bound at 20,012, and refuse the read
    crlf = _write(tmp_path / 'crlf.log', 'x\r\n' * 399_900 + ('p' * 386 + '\r\n') * 100)
    assert crlf.stat().st_size > _hook().BIG
    assert _hook().read_refusal(_read(crlf, tmp_path, {'offset': 100_001, 'limit': 100}, tool=PYCHARM)) is None


def test_a_big_files_command_is_sized_only_until_it_passes_the_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md AGT-45: in a file over BIG, a command's lines are sized only until they pass 20 KB, and tail's last
    # lines are read back from the end of the file
    hook = _hook()
    huge = _big(tmp_path / 'huge.log', HUGE)
    counter = _bytes_read(monkeypatch)
    over = 'would print over 20 KB of %s' % huge
    commands = [
        ('cat huge.log', over),
        ('tail -n +2 huge.log', over),
        ("sed -n '100,$p' huge.log", over),
        ('head -n 5000 huge.log', over),
        ('tail -n 250 huge.log', over),
        ('tail -n 20 huge.log', None),
        ('head -n 20 huge.log', None),
    ]
    for command, said in commands:
        with counter.at_most(LITTLE, command):
            _check(hook.bash_refusal(_run(command, tmp_path)), said)


def test_a_long_line_of_a_big_file_is_read_only_in_part(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md AGT-45: a line of 3 MB is read only until it passes 20 KB. A long line before a Read's range is passed,
    # and counts as one line
    hook = _hook()
    one_line = tmp_path / 'one_line.json'
    one_line.write_bytes(b'x' * 3_000_000)
    counter = _bytes_read(monkeypatch)
    for call in (_read(one_line, tmp_path), _read(one_line, tmp_path, tool=PYCHARM)):
        with counter.at_most(LITTLE, call):
            _says(hook.read_refusal(call), OVER % one_line)
    for command in ('cat one_line.json', 'tail -n 1 one_line.json'):
        with counter.at_most(LITTLE, command):
            _says(hook.bash_refusal(_run(command, tmp_path)), 'would print over 20 KB of %s' % one_line)
    long_first = tmp_path / 'long_first.log'
    long_first.write_bytes(b'y' * 1_500_000 + b'\n' + LINE.encode() * 300)
    _says(hook.read_refusal(_read(long_first, tmp_path, {'offset': 2})), 'returns over 20 KB')
    # lines 110 to 301 and the empty line 302: 19,200 bytes, and 772 of numbers
    assert hook.read_refusal(_read(long_first, tmp_path, {'offset': 110})) is None


def test_a_bash_output_of_8000_characters_gets_a_note_naming_the_command_and_its_size() -> None:
    # stderr counts too: 7,000 + 1,000 characters, 70 + 1 lines
    noted = _hook().bash_note(_bash(LINE * 70, 'e' * 999 + '\n'))
    note = _says(noted, SHELL[:70], '8,000 characters', '71 lines', '`analyst`', '`git diff --shortstat`', '`wc -c`')
    assert SHELL not in note, 'the command is cut to about 80 characters'
    multiline = _hook().bash_note(_bash(LINE * 80, command='git log -p \\\n    -- tests'))
    _says(multiline, '`git log -p \\ -- tests`')  # on one line


def test_a_bash_output_under_8000_characters_gets_none() -> None:
    assert _hook().bash_note(_bash(LINE * 70, 'e' * 998 + '\n')) is None


def test_a_saved_bash_output_gets_none() -> None:
    # Claude Code saved it to a file: only a 2 KB preview reached the context
    call = _bash('x' * 30_000, saved={'persistedOutputPath': '/tmp/out.txt', 'persistedOutputSize': 60_000})
    assert _hook().bash_note(call) is None


def test_a_subagents_bash_output_gets_none() -> None:
    for call in (_bash('x' * 10_000), _failed('Exit code 1\n' + 'x' * 10_000)):
        assert _hook().bash_note(call) is not None
        assert _hook().bash_note({**call, 'agent_id': 'a1', 'agent_type': 'analyst'}) is None


def test_a_failing_commands_output_gets_the_note_too() -> None:
    # REVIEW.md AGT-4: a command that fails gets PostToolUseFailure, whose `error` holds "Exit code N" and the output,
    # never saved to a file (measured 2026-11-19). Here 8,000 characters in 80 lines, then 7,999
    hook = _hook()
    note = hook.bash_note(_failed('Exit code 1\n' + LINE * 80))
    _says(note, SHELL[:70], 'was 8,000 characters', '80 lines', 'all of it', '`analyst`')
    assert hook.bash_note(_failed('Exit code 1\n' + LINE * 79 + 'x' * 99)) is None


def test_a_failing_commands_output_cut_short_is_at_least_its_size() -> None:
    # `error` keeps about 10,000 characters of the output: 10,040 of a 40,001-character one (measured 2026-11-19)
    note = _hook().bash_note(_failed('Exit code 6\n' + 'x' * 10_028))
    assert 'all of it' not in _says(note, 'at least 10,028 characters'), note


def test_only_a_bash_output_gets_the_note_on_its_size() -> None:
    # the hook runs after a reading call too, to count it: a Read's long error is no Bash output
    call = _payload('PostToolUseFailure', 'Read', ROOT, {'file_path': 'missing.py'})
    call['error'] = 'File does not exist. ' * 500
    assert _hook().bash_note(call) is None
    assert _hook().bash_note(_failed('Exit code 1\n' + 'x' * 10_500)) is not None


READ_CALL: tuple[str, HookInput] = ('Read', {'file_path': 'conftest.py'})
# The lead's reading calls, each counted toward the research note: Bash counts when each command of its line reads
READING_CALLS: list[tuple[str, HookInput]] = [
    READ_CALL,
    (PYCHARM, {'file_path': 'conftest.py'}),
    ('mcp__pycharm__search_text', {'q': 'def run'}),
    ('mcp__pycharm__search_regex', {'q': 'def run\\('}),
    ('mcp__pycharm__search_file', {'q': '*.py'}),
    ('mcp__pycharm__search_symbol', {'q': 'run'}),
    # only the tool's name counts, not its input
    ('mcp__pycharm__get_symbol_info', {}),
    ('mcp__pycharm__analyze_calls', {}),
    ('mcp__pycharm__list_directory_tree', {}),
    # Claude Code gives a session with Bash no Grep or Glob on macOS, Linux and WSL, but on Windows
    ('Grep', {'pattern': 'def run'}),
    ('Glob', {'pattern': '**/*.py'}),
    ('Bash', {'command': 'grep -rn "def run" mcp_server | head -20'}),
    ('Bash', {'command': 'git -C ../other log --oneline -5 2>/dev/null; git status --short'}),
    (
        'Bash',
        {
            'command': 'python3 scripts/review_lookup.py AGT-23 && mcp_server/venv/bin/python scripts/review_lookup.py TST-1'
        },
    ),
    ('Bash', {'command': "sed -n '1,20p' AGENTS.md && wc -l AGENTS.md || ls tests 2>&1"}),
]
# Calls that don't count: a Bash call with a command that doesn't read, and any other tool
OTHER_CALLS: list[tuple[str, HookInput]] = [
    ('Bash', {'command': 'mcp_server/venv/bin/python -m pytest tests/unit/test_agents.py'}),
    ('Bash', {'command': 'python3 scripts/other.py'}),
    ('Bash', {'command': 'git commit -m x'}),
    ('Bash', {'command': 'ls | xargs rm'}),
    ('Bash', {'command': 'grep -n x conftest.py > out.txt'}),
    ('Bash', {'command': 'grep -n x conftest.py 2>/dev/null >> out.txt'}),
    ('Bash', {'command': 'grep -c "$(rm x)" conftest.py'}),
    ('Bash', {'command': 'ls `rm x`'}),
    ('Bash', {'command': 'ls &'}),
    ('Bash', {'command': 'grep -rn x .', 'run_in_background': True}),  # REVIEW.md AGT-17
    ('Edit', {'file_path': 'conftest.py'}),
    ('WebFetch', {'url': 'https://example.com', 'prompt': 'p'}),
]


def _after(call: tuple[str, HookInput], prompt: str = 'p1', event: str = 'PostToolUse') -> HookCall:
    """A payload as the lead's call sends it after it ran, in the turn `prompt`."""
    tool, tool_input = call
    payload = _payload(event, tool, ROOT, tool_input)
    payload['prompt_id'] = prompt
    return payload


def _counting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Hook:
    """The hook, keeping its count of reading calls in `tmp_path`."""
    hook = _hook()
    monkeypatch.setitem(vars(hook), 'STATE_FOLDER', str(tmp_path))
    return hook


def _noted(hook: _Hook, calls: list[HookCall]) -> list[int]:
    """Which of `calls`, counted from 1, get the research note."""
    return [n for n, call in enumerate(calls, 1) if hook.research_note(call)]


def test_the_8th_reading_call_of_a_turn_and_each_8th_after_it_get_the_research_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # the size checks stop one big read, not many small ones adding up. The note suggests the analyst, and never
    # blocks: some work needs many reads (the user, 2026-11-19)
    hook = _counting(tmp_path, monkeypatch)
    notes = [hook.research_note(_after(READ_CALL)) for _ in range(24)]
    assert [n for n, note in enumerate(notes, 1) if note] == [8, 16, 24]
    assert (notes[7], notes[15]) == (hook.RESEARCH_NOTE % 8, hook.RESEARCH_NOTE % 16)
    _says(notes[7], '8 reading calls', 'Grep, Glob', "PyCharm's reads, searches and lookups", '`analyst`')


@pytest.mark.parametrize('call', READING_CALLS)
def test_each_reading_call_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, call: tuple[str, HookInput]) -> None:
    hook = _counting(tmp_path, monkeypatch)
    assert _noted(hook, [_after(call)] * 8) == [8]


@pytest.mark.parametrize('call', OTHER_CALLS)
def test_any_other_call_doesnt_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, call: tuple[str, HookInput]
) -> None:
    hook = _counting(tmp_path, monkeypatch)
    assert _noted(hook, [_after(READ_CALL)] * 7 + [_after(call)] * 8 + [_after(READ_CALL)]) == [16]


def test_a_subagents_reading_calls_dont_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hook = _counting(tmp_path, monkeypatch)
    analyst: HookCall = {**_after(READ_CALL), 'agent_id': 'a1', 'agent_type': 'analyst'}
    assert _noted(hook, [_after(READ_CALL)] * 7 + [analyst] * 8 + [_after(READ_CALL)]) == [16]


def test_a_failed_reading_call_counts_too(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # a failed call gets PostToolUseFailure, whose payload carries session_id and prompt_id too (measured 2026-11-19).
    # grep finding nothing exits 1
    hook = _counting(tmp_path, monkeypatch)
    grep = _after(('Bash', {'command': 'grep -rn nothing .'}), event='PostToolUseFailure')
    missing = _after(('Read', {'file_path': 'missing.py'}), event='PostToolUseFailure')
    assert _noted(hook, [grep, missing] * 4) == [8]


def test_a_new_turn_counts_from_1_and_the_count_is_one_small_file_per_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook = _counting(tmp_path, monkeypatch)
    other: HookCall = {**_after(READ_CALL), 'session_id': 'other-session'}
    calls = [_after(READ_CALL, 'p1')] * 7 + [_after(READ_CALL, 'p2')] * 7 + [other] * 3 + [_after(READ_CALL, 'p2')]
    assert _noted(hook, calls) == [18]
    # each session's file holds only its prompt and its count
    states: list[object] = [json.loads(path.read_text(encoding='utf-8')) for path in tmp_path.iterdir()]
    assert sorted(states, key=str) == [{'prompt_id': 'p1', 'count': 3}, {'prompt_id': 'p2', 'count': 8}]


def test_the_count_is_kept_in_the_systems_temporary_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # the hook imports tempfile only to count (the hook's comment there says why)
    monkeypatch.setattr(tempfile, 'tempdir', str(tmp_path))
    hook = _hook()
    assert hook.STATE_FOLDER == '', 'the system temporary folder, found as the call is counted'
    hook.research_note(_after(READ_CALL))
    assert [path.name for path in tmp_path.iterdir()] == ['large_reads_s.json']


def test_a_call_it_cant_count_gets_no_note_and_raises_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hook = _counting(tmp_path, monkeypatch)
    # no prompt_id, or a session_id that can't name a file of its own
    unnamed: list[HookCall] = [
        _payload('PostToolUse', 'Read', ROOT, {'file_path': 'conftest.py'}),
        {**_after(READ_CALL), 'session_id': '../s'},
        {**_after(READ_CALL), 'session_id': ''},
    ]
    assert _noted(hook, unnamed * 8) == []
    assert list(tmp_path.iterdir()) == []
    # a state file cut short counts again from 1
    assert _noted(hook, [_after(READ_CALL)] * 5) == []
    (state,) = tmp_path.iterdir()
    state.write_text('{"prompt_id": "p', encoding='utf-8')
    assert _noted(hook, [_after(READ_CALL)] * 8) == [8]
    # a folder it can't write to: no count, so no note
    monkeypatch.setitem(vars(hook), 'STATE_FOLDER', str(tmp_path / 'missing'))
    assert _noted(hook, [_after(READ_CALL)] * 8) == []


def test_the_research_note_goes_into_the_context_with_the_bash_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    hook = _counting(tmp_path, monkeypatch)
    for _ in range(7):
        monkeypatch.setattr(sys, 'stdin', io.StringIO(json.dumps(_after(READ_CALL))))
        assert hook.main() == 0
    assert capsys.readouterr() == ('', '')
    # the 8th: a command that only reads, whose big output gets the Bash note too. Both go in one additionalContext
    bash = _bash(LINE * 90, command='git log -p -3')
    bash['prompt_id'] = 'p1'
    monkeypatch.setattr(sys, 'stdin', io.StringIO(json.dumps(bash)))
    assert hook.main() == 0
    out, err = capsys.readouterr()
    printed: object = json.loads(out)
    context = '%s\n\n%s' % (hook.bash_note(bash), hook.RESEARCH_NOTE % 8)
    assert (printed, err) == (
        {'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': context}},
        '',
    )


def test_an_error_lets_the_call_through(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hook = _hook()

    def broken(call: object) -> str | None:
        raise RuntimeError('a bug in the hook')

    monkeypatch.setitem(vars(hook), 'read_refusal', broken)
    monkeypatch.setattr(sys, 'stdin', io.StringIO(json.dumps(_read(_big(tmp_path / 'big.py'), tmp_path))))
    assert hook.main() == 0


@pytest.mark.skipif(sys.platform == 'win32', reason='runs the command with sh, as Claude Code runs it on macOS')
def test_the_hook_exits_2_to_refuse_a_read_and_prints_the_note_as_json(tmp_path: Path) -> None:
    refused = run_hook(COMMAND, ROOT, _read(_big(tmp_path / 'big.py'), tmp_path))
    assert refused.returncode == 2 and '32 KB' in refused.stderr and refused.stdout == '', refused
    passed = run_hook(COMMAND, ROOT, _read(tmp_path / 'big.py', tmp_path, {'offset': 1, 'limit': 10}))
    assert (passed.returncode, passed.stdout, passed.stderr) == (0, '', '')
    # the note goes into the context on stdout, in the event's own name: after a command that failed too
    for call in (_bash('x' * 9_000), _failed('Exit code 1\n' + 'x' * 9_000)):
        noted = run_hook(COMMAND, ROOT, call)
        assert noted.returncode == 0 and noted.stderr == '', noted
        note = _hook().bash_note(call)
        printed: object = json.loads(noted.stdout)
        assert note and printed == {
            'hookSpecificOutput': {'hookEventName': call.get('hook_event_name'), 'additionalContext': note}
        }, printed


@pytest.mark.skipif(sys.platform == 'win32', reason='runs the command with sh, as Claude Code runs it on macOS')
def test_the_hook_exits_2_to_refuse_the_leads_web_call(tmp_path: Path) -> None:
    for tool, tool_input in WEB_CALLS:
        refused = run_hook(COMMAND, ROOT, _payload('PreToolUse', tool, tmp_path, tool_input))
        assert refused.returncode == 2 and '`analyst`' in refused.stderr and refused.stdout == '', refused
        call: HookCall = {**_payload('PreToolUse', tool, tmp_path, tool_input), 'agent_id': 'a1'}
        passed = run_hook(COMMAND, ROOT, call)
        assert (passed.returncode, passed.stdout, passed.stderr) == (0, '', '')


@pytest.mark.skipif(sys.platform == 'win32', reason='runs the command with sh, as Claude Code runs it on macOS')
def test_the_hook_exits_2_to_refuse_a_command(tmp_path: Path) -> None:
    _big(tmp_path / 'big.py')
    refused = run_hook(COMMAND, ROOT, _run('cat big.py', tmp_path))
    assert refused.returncode == 2 and '30 KB' in refused.stderr and refused.stdout == '', refused
    passed = run_hook(COMMAND, ROOT, _run('head -n 20 big.py', tmp_path))
    assert (passed.returncode, passed.stdout, passed.stderr) == (0, '', '')


@pytest.mark.skipif(sys.platform == 'win32', reason='runs the command with sh, as Claude Code runs it on macOS')
def test_the_hook_finds_its_parser_when_python_puts_no_script_folder_on_its_path(tmp_path: Path) -> None:
    # REVIEW.md AGT-103: with PYTHONSAFEPATH set (Python 3.11 and later), Python doesn't put the script's folder on its
    # path, where the hook imports its parser from (command_lines.py). The import failed, and the hook let `cat` through
    _big(tmp_path / 'big.py')
    refused = run_hook(COMMAND, ROOT, _run('cat big.py', tmp_path), {'PYTHONSAFEPATH': '1'})
    assert refused.returncode == 2 and '30 KB' in refused.stderr and refused.stdout == '', refused


@pytest.mark.skipif(sys.platform == 'win32', reason='runs the command with sh, as Claude Code runs it on macOS')
def test_the_hook_fails_open(tmp_path: Path) -> None:
    # a project with the venv's Python but without the script: Python would exit 2 on a script it can't open, which
    # Claude Code reads as a block (REVIEW.md TST-557)
    with_venv = tmp_path / 'with_venv'
    python = with_venv / 'mcp_server' / 'venv' / 'bin' / 'python'
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    missing = run_hook(COMMAND, str(with_venv), _read(_big(tmp_path / 'big.py'), tmp_path))
    assert (missing.returncode, missing.stdout, missing.stderr) == (0, '', '')
    # a clone without the venv (AGENTS.md: install.py first): the shell would end the hook in an error on every call
    no_venv = tmp_path / 'no_venv'
    script = no_venv / '.claude' / 'hooks' / HOOK.name
    script.parent.mkdir(parents=True)
    script.write_bytes(HOOK.read_bytes())
    without = run_hook(COMMAND, str(no_venv), _read(tmp_path / 'big.py', tmp_path))
    assert (without.returncode, without.stdout, without.stderr) == (0, '', '')


def test_the_hook_fails_open_without_its_command_line_parser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # the parser of a command line is the module beside the hook (REVIEW.md AGT-101). The settings' command checks only
    # that the hook's script exists: a hook without the parser must still let every Bash call through, the one it would
    # size and the one it would count as a read
    monkeypatch.setitem(sys.modules, 'command_lines', None)  # importing it then fails, as when its file is missing
    hook: _Hook = load_script(HOOK)  # loaded again: a hook importing the parser at its top would fail to load
    monkeypatch.setitem(vars(hook), 'STATE_FOLDER', str(tmp_path))
    _big(tmp_path / 'big.py')
    counted = _bash('x')
    counted['prompt_id'] = 'p1'
    for call in (_run('cat big.py', tmp_path), counted):
        monkeypatch.setattr(sys, 'stdin', io.StringIO(json.dumps(call)))
        assert hook.main() == 0
        assert capsys.readouterr() == ('', '')
    assert list(tmp_path.glob('large_reads_*.json')) == [], 'no call counted'


@pytest.mark.parametrize('malformed', ['not json', '[]', '{"hook_event_name": "PreToolUse", "tool_input": 3}'])
def test_a_malformed_call_passes_with_no_output(
    malformed: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, 'stdin', io.StringIO(malformed))
    assert _hook().main() == 0
    out, err = capsys.readouterr()
    assert (out, err) == ('', '')


def test_the_settings_register_the_hook_for_reads_and_bash_commands_and_outputs() -> None:
    # a command that fails gets PostToolUseFailure instead of PostToolUse (measured 2026-11-19). After a call, the hook
    # runs for Bash and every reading call: one matcher, so that a call is counted once
    registered = _settings()['hooks']
    hooks = [{'type': 'command', 'command': COMMAND}]
    reading = ('Bash', *_hook().READING_TOOLS)
    assert set(reading) == {tool for tool, _ in READING_CALLS}, 'a test of each tool the hook counts'
    after = '|'.join(reading)
    assert registered == {
        'PreToolUse': [
            {'matcher': 'WebFetch|WebSearch', 'hooks': hooks},
            {'matcher': 'Read|mcp__pycharm__read_file', 'hooks': hooks},
            {'matcher': 'Bash', 'hooks': hooks},
        ],
        'PostToolUse': [{'matcher': after, 'hooks': hooks}],
        'PostToolUseFailure': [{'matcher': after, 'hooks': hooks}],
    }


def test_the_settings_cap_a_successful_bash_output() -> None:
    # past the cap, Claude Code saves a successful output to a file and shows a 2 KB preview; a failing one isn't capped
    # by it (measured 2026-11-19: a 12,000-character output was saved, a failing 15,000-character one reached the
    # context whole)
    assert _settings().get('bashOutputMaxChars') == 10_000


def test_the_docs_give_the_limits_the_hook_and_the_settings_apply() -> None:
    # the hook's docstring holds the hooks' rules, and AGENTS.md states the limits the lead works by (Delegating to
    # subagents), the notes' included (REVIEW.md AGT-89): a limit changed here must change in both
    hook = _hook()
    docstring = flat(hook.__doc__ or '')
    agents = flat(agents_md())
    readme = flat(read('README.md'))
    cap = _settings().get('bashOutputMaxChars')
    assert isinstance(cap, int)
    both = (
        f'a read that returns over {hook.READ_LIMIT // 1000} KB',
        f'would print over {hook.READ_LIMIT // 1000} KB of files',
        f'an output of {hook.OUTPUT_LIMIT:,} characters or more',
        f"the lead's {hook.RESEARCH_READS}th reading call of a turn, and each {hook.RESEARCH_READS}th after it",
    )
    claims = (
        (docstring, (*both, f'cut in the middle to `limit` lines, {hook.PYCHARM_LIMIT:,} without it')),
        # the claim about the setting, not the condition of the measurement dated beside it (REVIEW.md TST-603)
        (docstring, (f"so a successful command can't put more than {cap:,} characters into the context",)),
        (agents, (*both, f"caps a successful command's output at {cap:,} characters (`bashOutputMaxChars`)")),
        # every limit is in the docstring, so README sends its readers there (REVIEW.md AGT-89)
        (readme, ('The limits and the rules are in the docstring of `.claude/hooks/large_reads.py`.',)),
    )
    assert [claim for text, said in claims for claim in said if claim not in text] == []
