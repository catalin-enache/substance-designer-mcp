"""A finding removed from REVIEW.md by a cleanup stays findable in git (scripts/review_lookup.py), and the rules the
review docs agree on."""

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from conftest import ROOT

SKILLS = os.path.join('.claude', 'skills')
SCRIPT = os.path.join(ROOT, 'scripts', 'review_lookup.py')
LOOKUP_DOCS = (
    'REVIEW.md',
    os.path.join(SKILLS, 'project-code-review', 'TEMPLATE.md'),
    os.path.join(SKILLS, 'project-code-review', 'SKILL.md'),
)
REVIEW_SKILLS = ('address-review', 'cleanup-review', 'project-code-review')
SEVERITIES = ('High', 'Medium-high', 'Medium', 'Low-medium', 'Low')
GIT_ENV = {
    **os.environ,
    'GIT_AUTHOR_NAME': 't',
    'GIT_AUTHOR_EMAIL': 't@example.com',
    'GIT_COMMITTER_NAME': 't',
    'GIT_COMMITTER_EMAIL': 't@example.com',
    'GIT_CONFIG_GLOBAL': os.devnull,
}
FULL = """# REVIEW.md

## Low

- [x] **HLP-5 · a shorter id** · `a.py`
  - **Resolution: done.**
- [x] **HLP-56 · the finding** · `b.py`
  - **Defect.** Its body.
  - **Resolution: not reproduced.**
- [x] **TST-9 · the next one** · `c.py`
  - **Resolution: done.**

## Other

- [x] **TST-10 · last in its section** · `d.py`
  - **Resolution: done.**

## Next section
"""

needs_git = pytest.mark.skipif(shutil.which('git') is None, reason='needs git')
needs_sh = pytest.mark.skipif(shutil.which('sh') is None or shutil.which('git') is None, reason='needs sh and git')


def _read(path: str) -> str:
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return f.read()


def _sh(script: str, cwd: Path) -> str:
    return subprocess.run(['sh', '-c', script], cwd=cwd, env=GIT_ENV, capture_output=True, text=True).stdout


def _script(cwd: Path | str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, SCRIPT, *args], cwd=cwd, env=GIT_ENV, capture_output=True, text=True, encoding='utf-8'
    )


def _lookup(repo: Path, finding: str) -> str:
    return _script(repo, finding).stdout


def _last_used(repo: Path) -> list[str]:
    return re.findall(r'[A-Z]+-\d+', _script(repo, '--last-used').stdout)


def _commit(repo: Path, content: str, message: str = 'change') -> None:
    (repo / 'REVIEW.md').write_text(content, encoding='utf-8')
    subprocess.run(['git', 'add', 'REVIEW.md'], cwd=repo, env=GIT_ENV, check=True)
    subprocess.run(['git', 'commit', '-qm', message], cwd=repo, env=GIT_ENV, check=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, env=GIT_ENV, check=True)
    _commit(tmp_path, FULL)
    return tmp_path


@pytest.mark.parametrize('path', LOOKUP_DOCS)
def test_every_doc_runs_the_script_and_copies_no_commands(path: str) -> None:
    text = _read(path)
    assert 'python3 scripts/review_lookup.py HLP-56' in text
    assert 'git log --format' not in text and 'git log -p' not in text and 'awk' not in text


@needs_git
def test_the_script_works_from_any_folder_of_the_repo(repo: Path) -> None:
    (repo / 'sub' / 'folder').mkdir(parents=True)
    assert 'the finding' in _lookup(repo / 'sub' / 'folder', 'HLP-56')
    _commit(repo, '# REVIEW.md\n')
    assert 'the finding' in _lookup(repo / 'sub' / 'folder', 'HLP-56')
    assert _last_used(repo / 'sub' / 'folder') == ['HLP-56', 'TST-10']


def test_the_script_says_when_it_isnt_in_a_repo(tmp_path: Path) -> None:
    done = _script(tmp_path, 'HLP-56')
    assert done.returncode == 1 and done.stdout == '' and 'git repository' in done.stderr


@pytest.mark.parametrize('finding', ['hlp-56', 'HLP', '56', 'HLP-5x', '../REVIEW'])
def test_the_script_refuses_what_isnt_an_id(tmp_path: Path, finding: str) -> None:
    done = _script(tmp_path, finding)
    assert done.returncode == 2 and done.stdout == '' and 'HLP-56' in done.stderr


@needs_git
def test_a_removed_finding_comes_back_whole_and_alone(repo: Path) -> None:
    _commit(repo, '# REVIEW.md\n')
    found = _lookup(repo, 'HLP-56')
    assert found.startswith('- [x] **HLP-56 · the finding**')
    assert 'Its body.' in found and 'Resolution: not reproduced.' in found
    assert 'TST-9' not in found and 'HLP-5 ·' not in found


@needs_git
def test_a_shorter_id_doesnt_match_a_longer_one(repo: Path) -> None:
    _commit(repo, '# REVIEW.md\n')
    found = _lookup(repo, 'HLP-5')
    assert 'a shorter id' in found and 'the finding' not in found


@needs_git
def test_the_last_finding_of_a_section_stops_at_the_section(repo: Path) -> None:
    _commit(repo, '# REVIEW.md\n')
    found = _lookup(repo, 'TST-10')
    assert 'last in its section' in found and 'Next section' not in found


@needs_git
def test_a_later_cleanup_still_finds_what_an_earlier_one_removed(repo: Path) -> None:
    _commit(repo, '# REVIEW.md\n')
    _commit(repo, '# REVIEW.md\n\n- [ ] **NEW-1 · a later finding** · `e.py`\n  - Its body.\n')
    _commit(repo, '# REVIEW.md\n\nagain\n')
    assert 'the finding' in _lookup(repo, 'HLP-56')
    assert 'a later finding' in _lookup(repo, 'NEW-1')


@needs_git
def test_checking_a_finding_off_doesnt_hide_its_removal(repo: Path) -> None:
    _commit(repo, FULL.replace('- [x] **HLP-56', '- [ ] **HLP-56'))
    _commit(repo, FULL)
    _commit(repo, '# REVIEW.md\n')
    assert 'the finding' in _lookup(repo, 'HLP-56')


@needs_git
def test_a_finding_still_in_the_file_is_printed_as_it_is_now(repo: Path) -> None:
    """Before any cleanup the newest commit is the one that added it, and the commit before that doesn't have it."""
    assert 'the finding' in _lookup(repo, 'HLP-56'), 'added in the only commit'
    _commit(repo, FULL.replace('Its body.', 'Its newer body.'))
    assert 'Its newer body.' in _lookup(repo, 'HLP-56')
    (repo / 'REVIEW.md').write_text(FULL.replace('Its body.', 'Not committed yet.'), encoding='utf-8')
    assert 'Not committed yet.' in _lookup(repo, 'HLP-56')


@needs_git
def test_an_id_that_never_existed_prints_nothing(repo: Path) -> None:
    _commit(repo, '# REVIEW.md\n')
    done = _script(repo, 'HLP-999')
    assert done.returncode == 1 and done.stdout == ''
    assert 'never existed' in done.stderr and 'squash' in done.stderr


def _counter_problems(text: str) -> list[str]:
    """What is wrong with the header's **Last used** line, given the file's entries."""
    lines = re.findall(r'(?m)^\*\*Last used:\*\* (.*)\.$', text)
    if len(lines) != 1:
        return ['expected one **Last used** line, found %d' % len(lines)]
    counters = {prefix: int(number) for prefix, number in re.findall(r'([A-Z]+)-(\d+)', lines[0])}
    problems = []
    for prefix, number in re.findall(r'(?m)^- \[.\] \*\*([A-Z]+)-(\d+) ', text):
        if int(number) > counters.get(prefix, -1):
            problems.append('%s-%s is above **Last used**' % (prefix, number))
    for prefix in re.findall(r'\*\*([A-Z]{3})\*\* ', text.split('**Last used:**')[0].split('**IDs.**')[-1]):
        if prefix not in counters:
            problems.append('**IDs** names %s, which **Last used** lacks' % prefix)
    return problems


@pytest.mark.parametrize(
    'text, problem',
    [
        ('# REVIEW.md\n', 'expected one'),
        ('**Last used:** HLP-1.\n**Last used:** HLP-2.\n', 'expected one'),
        ('**Last used:** HLP-80.\n\n- [ ] **HLP-81 · forgot the counter** · `a.py`\n', 'HLP-81 is above'),
        ('**Last used:** HLP-80.\n\n- [ ] **SRV-1 · new prefix, not added** · `a.py`\n', 'SRV-1 is above'),
        ('**IDs.** **PLG** plugin, **HLP** helpers.\n\n**Last used:** HLP-80.\n', 'names PLG'),
    ],
)
def test_the_counter_check_catches(text: str, problem: str) -> None:
    assert any(problem in found for found in _counter_problems(text))


@pytest.mark.parametrize(
    'text',
    [
        '**Last used:** HLP-80.\n\n- [x] **HLP-80 · the last one** · `a.py`\n',
        '**Last used:** HLP-80, TST-140.\n',  # after a cleanup: no entries, and the numbers stay
        '**Last used:** HLP-80.\n\n- [ ] **HLP-3 · an old open one** · `a.py`\n',
        '**Last used:** HLP-2.\n\n- [x] **HLP-2 · follows HLP-900** · `a.py`\n  - Questioned by TST-900.\n',
    ],
)
def test_the_counter_check_accepts(text: str) -> None:
    assert _counter_problems(text) == []


@pytest.mark.parametrize('path', ('REVIEW.md', os.path.join(SKILLS, 'project-code-review', 'TEMPLATE.md')))
def test_the_header_counters_cover_every_finding(path: str) -> None:
    assert _counter_problems(_read(path)) == []


@pytest.mark.parametrize('skill', REVIEW_SKILLS)
def test_each_skill_uses_the_counters_and_not_the_old_command(skill: str) -> None:
    text = _read(os.path.join(SKILLS, skill, 'SKILL.md'))
    assert '**Last used**' in text
    assert 'Last numbers' not in text and "grep -oE '^- " not in text


def _entry_numbers(text: str) -> dict[str, int]:
    highest: dict[str, int] = {}
    for prefix, number in re.findall(r'(?m)^[-+]?- \[.\] \*\*([A-Z]+)-(\d+) ', text):
        highest[prefix] = max(highest.get(prefix, 0), int(number))
    return highest


def _counter_against_history(repo: str | Path) -> list[str]:
    """The **Last used** line must equal the highest number ever used: in the file's entries now, or in any commit of
    its history, whether as an entry or on this line. So a lowered number can't pass by being committed, a cleanup's
    removed entries still count, and so does a finding a squash lost, which only the line remembers."""
    git = ['git', 'log', '-p', '-U0', '--format=', '--no-color', '--no-ext-diff', '--', 'REVIEW.md']
    history = subprocess.run(
        git, cwd=repo, env=GIT_ENV, capture_output=True, text=True, encoding='utf-8', check=True
    ).stdout
    with open(os.path.join(repo, 'REVIEW.md'), encoding='utf-8') as f:
        current = f.read()
    expected = _entry_numbers(history)
    for line in re.findall(r'(?m)^[-+]\*\*Last used:\*\* (.*)$', history):
        for prefix, number in re.findall(r'([A-Z]+)-(\d+)', line):
            expected[prefix] = max(expected.get(prefix, 0), int(number))
    for prefix, number in _entry_numbers(current).items():
        expected[prefix] = max(expected.get(prefix, 0), number)
    lines = re.findall(r'(?m)^\*\*Last used:\*\* (.*)\.$', current)
    counters = (
        {prefix: int(number) for prefix, number in re.findall(r'([A-Z]+)-(\d+)', lines[0])} if len(lines) == 1 else {}
    )
    return [
        '%s: **Last used** says %s, the highest ever used is %s' % (prefix, counters.get(prefix), expected.get(prefix))
        for prefix in sorted(set(expected) | set(counters))
        if counters.get(prefix, 0) != expected.get(prefix, 0)  # a prefix never used may be at 0, as in the template
    ]


TWO_ENTRIES = '**Last used:** HLP-81, TST-140.\n\n- [x] **HLP-81 · one** · `a.py`\n- [x] **TST-140 · two** · `b.py`\n'
AFTER_CLEANUP = '**Last used:** HLP-81, TST-140.\n'


@pytest.fixture
def reviewed(tmp_path: Path) -> Path:
    """A repo whose REVIEW.md had two findings, both removed by a committed cleanup."""
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, env=GIT_ENV, check=True)
    _commit(tmp_path, TWO_ENTRIES)
    _commit(tmp_path, AFTER_CLEANUP)
    return tmp_path


def test_a_cleanup_leaves_the_counter_correct(reviewed: Path) -> None:
    assert _counter_against_history(reviewed) == []


@pytest.mark.parametrize(
    'line',
    [
        '**Last used:** HLP-10, TST-140.',  # lowered, with no entry left in the file to contradict it
        '**Last used:** TST-140.',  # a prefix dropped
        'no counter line at all',
    ],
)
def test_lowering_the_counter_fails_even_when_committed(reviewed: Path, line: str) -> None:
    (reviewed / 'REVIEW.md').write_text(line + '\n', encoding='utf-8')
    assert _counter_against_history(reviewed), 'not committed'
    _commit(reviewed, line + '\n')
    assert _counter_against_history(reviewed), "committing it mustn't make it pass"


@pytest.mark.parametrize('line', ['**Last used:** HLP-82, TST-140.', '**Last used:** HLP-81, TST-140, SRV-5.'])
def test_raising_the_counter_with_no_finding_fails_until_committed(reviewed: Path, line: str) -> None:
    """Once committed it can't be told from a finding a squash lost, and all it does is skip a number."""
    (reviewed / 'REVIEW.md').write_text(line + '\n', encoding='utf-8')
    assert _counter_against_history(reviewed)
    _commit(reviewed, line + '\n')
    assert _counter_against_history(reviewed) == []


def _squashed_away(repo: Path) -> None:
    """HLP-2 was added and cleaned up on one branch, then squashed: main only ever saw the counter move."""
    subprocess.run(['git', 'init', '-q'], cwd=repo, env=GIT_ENV, check=True)
    _commit(repo, '**Last used:** HLP-1.\n\n- [x] **HLP-1 · old** · `a.py`\n')
    _commit(repo, '**Last used:** HLP-2.\n')


def test_a_finding_lost_in_a_squash_keeps_its_number(tmp_path: Path) -> None:
    _squashed_away(tmp_path)
    assert _counter_against_history(tmp_path) == [], 'the counter stays as it is, and that is right'


@needs_git
def test_a_finding_lost_in_a_squash_prints_nothing_but_its_number_isnt_reused(tmp_path: Path) -> None:
    _squashed_away(tmp_path)
    assert _lookup(tmp_path, 'HLP-2') == ''
    subprocess.run(['git', 'rm', '-q', 'REVIEW.md'], cwd=tmp_path, env=GIT_ENV, check=True)
    subprocess.run(['git', 'commit', '-qm', 'delete'], cwd=tmp_path, env=GIT_ENV, check=True)
    assert _last_used(tmp_path) == ['HLP-2']


@needs_sh
def test_the_cleanup_search_finds_every_wording_of_an_answer(tmp_path: Path) -> None:
    found = re.findall(r'```sh\n\s*(grep -nE .*?)```', _read(os.path.join(SKILLS, 'cleanup-review', 'SKILL.md')), re.S)
    assert len(found) == 1
    answers = [
        '**Resolution: not a bug** x',
        '**Resolution: not reproducible** x',
        '**Resolution: not reproduced** x',
        '**Resolution: done, defensively; not reproducible in Designer** x',
        '**Resolution: done; no loss reproduced** x',
        "**Resolution: won't fix** x",
        '**Resolution: done** A rule, chosen by the user over closing it.',
    ]
    plain = '**Resolution: done** the ordinary kind'
    (tmp_path / 'REVIEW.md').write_text('\n'.join([*answers, plain]) + '\n', encoding='utf-8')
    printed = _sh(found[0], tmp_path)
    assert all(answer in printed for answer in answers)
    assert plain not in printed


@pytest.mark.parametrize(
    'path',
    (
        'AGENTS.md',
        'REVIEW.md',
        os.path.join(SKILLS, 'project-code-review', 'TEMPLATE.md'),
        os.path.join(SKILLS, 'project-code-review', 'SKILL.md'),
        os.path.join(SKILLS, 'address-review', 'SKILL.md'),
    ),
)
def test_the_docs_ask_for_not_reproducible(path: str) -> None:
    head = _read(path).split('\n## Status')[0]  # REVIEW.md's old entries keep the wording they were written in
    assert 'not reproducible' in head and 'not reproduced' not in head.lower()


@pytest.mark.parametrize('path', LOOKUP_DOCS)
def test_the_docs_dont_say_empty_output_can_only_mean_one_thing(path: str) -> None:
    assert 'nothing only' not in _read(path).replace('\n', ' ')


@pytest.mark.parametrize(
    'path',
    (
        'AGENTS.md',
        'DECISIONS.md',
        'REVIEW.md',
        os.path.join(SKILLS, 'project-code-review', 'TEMPLATE.md'),
        os.path.join(SKILLS, 'project-code-review', 'SKILL.md'),
        os.path.join(SKILLS, 'address-review', 'SKILL.md'),
        os.path.join(SKILLS, 'cleanup-review', 'SKILL.md'),
    ),
)
def test_the_docs_say_what_each_file_remembers(path: str) -> None:
    assert 'memory per branch' in _read(path).replace('\n', ' ')


def test_decisions_says_it_is_the_memory_for_the_whole_project() -> None:
    assert 'memory for the whole project' in _read('DECISIONS.md').replace('\n', ' ')


def test_a_false_finding_waits_for_the_cleanup_and_the_users_acknowledgment() -> None:
    address = _read(os.path.join(SKILLS, 'address-review', 'SKILL.md'))
    cleanup = _read(os.path.join(SKILLS, 'cleanup-review', 'SKILL.md'))
    assert 'every *not a bug*' not in address and 'add the answer to `DECISIONS.md`' not in address
    assert 'plausibly raise again' in cleanup and 'acknowledg' in cleanup
    assert 'suggest' in cleanup and 'A cleanup only adds' not in cleanup


def test_a_review_reads_decisions_first_then_review() -> None:
    assert 'Read `DECISIONS.md` (repo root) first, then `REVIEW.md`.' in _read(
        os.path.join(SKILLS, 'project-code-review', 'SKILL.md')
    ).replace('\n', ' ')


def test_the_cleanup_says_where_the_header_ends() -> None:
    assert 'The header ends before `## Status`' in _read(os.path.join(SKILLS, 'cleanup-review', 'SKILL.md'))


def test_a_new_finding_must_move_the_counter(reviewed: Path) -> None:
    entry = '- [ ] **HLP-82 · new** · `a.py`\n'
    (reviewed / 'REVIEW.md').write_text('%s\n%s' % (AFTER_CLEANUP, entry), encoding='utf-8')
    assert _counter_against_history(reviewed) == ['HLP: **Last used** says 81, the highest ever used is 82']
    (reviewed / 'REVIEW.md').write_text('**Last used:** HLP-82, TST-140.\n\n' + entry, encoding='utf-8')
    assert _counter_against_history(reviewed) == []


def test_the_counter_shows_the_highest_number_ever_used_in_review_md() -> None:
    shallow = subprocess.run(
        ['git', 'rev-parse', '--is-shallow-repository'], cwd=ROOT, env=GIT_ENV, capture_output=True, text=True
    )
    if shallow.returncode != 0 or shallow.stdout.strip() != 'false':
        pytest.skip('needs a clone with full history')
    assert _counter_against_history(ROOT) == []


TEMPLATE = os.path.join(SKILLS, 'project-code-review', 'TEMPLATE.md')


def _delete_review(repo: Path) -> None:
    subprocess.run(['git', 'rm', '-q', 'REVIEW.md'], cwd=repo, env=GIT_ENV, check=True)
    subprocess.run(['git', 'commit', '-qm', 'delete REVIEW.md'], cwd=repo, env=GIT_ENV, check=True)


def _recreated(repo: Path) -> str:
    """REVIEW.md made from the template, with **Last used** set as the skill says."""
    text = _read(TEMPLATE)
    for found in _last_used(repo):
        prefix = found.split('-')[0]
        assert '%s-0' % prefix in text or prefix not in ('PLG', 'SRV', 'HLP', 'INS', 'TST')
        text = text.replace('%s-0' % prefix, found)
    return text


@needs_git
def test_the_template_alone_would_reuse_numbers_after_a_deletion(reviewed: Path) -> None:
    _delete_review(reviewed)
    (reviewed / 'REVIEW.md').write_text(_read(TEMPLATE), encoding='utf-8')
    assert [line.split(':')[0] for line in _counter_against_history(reviewed)] == ['HLP', 'TST']


@needs_git
def test_a_recreated_file_gets_its_counters_from_history(reviewed: Path) -> None:
    _delete_review(reviewed)
    assert _last_used(reviewed) == ['HLP-81', 'TST-140']
    recreated = _recreated(reviewed)
    assert '**Last used:** PLG-0, SRV-0, HLP-81, INS-0, TST-140.' in recreated
    (reviewed / 'REVIEW.md').write_text(recreated, encoding='utf-8')
    assert _counter_against_history(reviewed) == []


@needs_git
def test_a_recreated_file_still_finds_what_was_deleted(reviewed: Path) -> None:
    _delete_review(reviewed)
    _commit(reviewed, _recreated(reviewed))
    assert 'one' in _lookup(reviewed, 'HLP-81')


@needs_git
def test_the_numbers_survive_a_second_deletion(reviewed: Path) -> None:
    _delete_review(reviewed)
    text = _recreated(reviewed).replace('HLP-81,', 'HLP-82,') + '\n- [ ] **HLP-82 · newer** · `a.py`\n'
    _commit(reviewed, text)
    assert _counter_against_history(reviewed) == []
    _delete_review(reviewed)
    assert _last_used(reviewed) == ['HLP-82', 'TST-140']


@needs_git
def test_the_restore_command_ignores_ids_named_in_an_entrys_text(tmp_path: Path) -> None:
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, env=GIT_ENV, check=True)
    _commit(tmp_path, '- [x] **HLP-2 · follows HLP-900** · `a.py`\n  - Questioned by TST-900.\n')
    assert _last_used(tmp_path) == ['HLP-2']


@needs_git
def test_a_shallow_clone_says_so_instead_of_guessing(reviewed: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    """The history that holds the numbers and the removed entries isn't in the clone."""
    _delete_review(reviewed)
    shallow = tmp_path_factory.mktemp('shallow') / 'clone'
    subprocess.run(['git', 'clone', '-q', '--depth', '1', reviewed.as_uri(), str(shallow)], env=GIT_ENV, check=True)
    for args in (['--last-used'], ['HLP-81']):
        done = _script(shallow, *args)
        assert done.returncode == 1 and done.stdout == '' and 'shallow' in done.stderr, args


def test_last_used_prints_a_line_ready_to_paste(reviewed: Path) -> None:
    assert _script(reviewed, '--last-used').stdout == '**Last used:** HLP-81, TST-140.\n'


def test_last_used_with_no_history_says_so(tmp_path: Path) -> None:
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, env=GIT_ENV, check=True)
    done = _script(tmp_path, '--last-used')
    assert done.returncode == 0 and done.stdout == '' and 'stay at 0' in done.stderr


def test_a_prefix_never_used_may_stay_at_zero(tmp_path: Path) -> None:
    """A new project's file made from the template: nothing used yet, and that is correct."""
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, env=GIT_ENV, check=True)
    _commit(tmp_path, _read(TEMPLATE))
    assert _counter_against_history(tmp_path) == []


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(['git', *args], cwd=repo, env=GIT_ENV, capture_output=True, text=True)


def _two_branches(repo: Path, theirs: str, mine: str) -> None:
    """Both branches add a finding from the same counters; theirs merges into main first."""
    _git(repo, 'init', '-q', '-b', 'main')
    _commit(repo, '**Last used:** HLP-1, SRV-1.\n\n## Low\n\n- [x] **HLP-1 · old** · `a.py`\n')
    base = (repo / 'REVIEW.md').read_text(encoding='utf-8')
    _git(repo, 'checkout', '-qb', 'mine')
    (repo / 'mine.py').write_text('# %s\n' % mine, encoding='utf-8')
    _git(repo, 'add', 'mine.py')
    _commit(repo, _with_finding(base, mine, 'my finding'))
    _git(repo, 'checkout', '-q', 'main')
    _git(repo, 'checkout', '-qb', 'theirs')
    (repo / 'theirs.py').write_text('# %s\n' % theirs, encoding='utf-8')
    _git(repo, 'add', 'theirs.py')
    _commit(repo, _with_finding(base, theirs, 'their finding'))
    _git(repo, 'checkout', '-q', 'main')
    _git(repo, 'merge', '-q', '--squash', 'theirs')
    _git(repo, 'commit', '-qm', 'their branch, squashed')
    _git(repo, 'checkout', '-q', 'mine')


def _with_finding(text: str, finding: str, title: str) -> str:
    prefix = finding.split('-')[0]
    return (
        re.sub(r'%s-\d+' % prefix, finding, text.split('\n\n')[0], count=1)
        + '\n\n'
        + '\n\n'.join(text.split('\n\n')[1:])
        + '- [ ] **%s · %s** · `x.py`\n' % (finding, title)
    )


@needs_git
@pytest.mark.parametrize('how', [('merge', '--no-edit', 'main'), ('merge', '--squash', 'main'), ('rebase', 'main')])
@pytest.mark.parametrize('theirs, mine', [('HLP-2', 'HLP-2'), ('SRV-2', 'HLP-2')])
def test_two_branches_raising_a_counter_conflict(tmp_path: Path, how: tuple[str, ...], theirs: str, mine: str) -> None:
    """Even for different prefixes: it is one line, so a branch can't pass silently with a stale number."""
    _two_branches(tmp_path, theirs, mine)
    assert _git(tmp_path, *how).returncode != 0


@needs_git
def test_the_second_branch_renumbers_from_mains_counters(tmp_path: Path) -> None:
    _two_branches(tmp_path, 'HLP-2', 'HLP-2')
    own = _git(tmp_path, 'diff', 'main...HEAD').stdout
    assert 'mine.py' in own and 'theirs.py' not in own, 'this diff shows only the references this branch added'
    assert _git(tmp_path, 'merge', '--no-edit', 'main').returncode != 0
    resolved = (
        '**Last used:** HLP-3, SRV-1.\n\n## Low\n\n- [x] **HLP-1 · old** · `a.py`\n'
        '- [ ] **HLP-2 · their finding** · `x.py`\n- [ ] **HLP-3 · my finding** · `x.py`\n'
    )
    (tmp_path / 'mine.py').write_text('# HLP-3\n', encoding='utf-8')
    _git(tmp_path, 'add', 'mine.py')
    _commit(tmp_path, resolved)
    assert _counter_against_history(tmp_path) == []
    assert 'their finding' in _lookup(tmp_path, 'HLP-2') and 'my finding' in _lookup(tmp_path, 'HLP-3')


DOC_TESTS = re.compile(r"""['"](?:AGENTS|README|ROADMAP|DECISIONS|REVIEW)\.md['"]""")


def test_the_docs_command_names_every_test_that_reads_a_doc() -> None:
    """A commit of docs alone runs only these, so a new test reading a doc must join the list."""
    unit = os.path.join(ROOT, 'tests', 'unit')
    reading = {
        name
        for name in os.listdir(unit)
        if name.startswith('test_')
        and name.endswith('.py')
        and DOC_TESTS.search(_read(os.path.join('tests', 'unit', name)))
    }
    commands = re.findall(r'`mcp_server/venv/bin/python -m pytest (tests/unit/[^`]+)`', _read('AGENTS.md'))
    assert len(commands) == 1, 'AGENTS.md should give the docs-only command once'
    assert {os.path.basename(path) for path in commands[0].split()} == reading


def test_the_wording_of_the_rules_agreed_on() -> None:
    project = _read(os.path.join(SKILLS, 'project-code-review', 'SKILL.md')).replace('\n', ' ')
    address = _read(os.path.join(SKILLS, 'address-review', 'SKILL.md')).replace('\n', ' ')
    cleanup = _read(os.path.join(SKILLS, 'cleanup-review', 'SKILL.md')).replace('\n', ' ')
    for path in LOOKUP_DOCS:
        text = _read(path).replace('\n', ' ')
        assert 'ever used twice' not in text, path
        assert 'Nothing lowers a committed number' in text, path
    assert 'merges second' in project and 'git diff main...HEAD' in project
    assert 'also in `DECISIONS.md`' in project, 'an answer in both files follows the decision'
    assert "don't raise the same finding again" in project
    assert 'in exactly these words' not in address and 'starts with' in address
    assert "and the entry's **Reopen if** doesn't hold" not in address, 'stop and ask whether it holds or not'
    assert 'tests that validate the docs' in cleanup
    assert 'lookup' in _read('ROADMAP.md').split('## Review hotspots')[1].split('| Done |')[0]


def test_the_wording_of_the_smaller_points_agreed_on() -> None:
    agents = _read('AGENTS.md').replace('\n', ' ')
    project = _read(os.path.join(SKILLS, 'project-code-review', 'SKILL.md')).replace('\n', ' ')
    address = _read(os.path.join(SKILLS, 'address-review', 'SKILL.md')).replace('\n', ' ')
    assert 'One repeat is deliberate' in agents
    assert 'read by the review skills' in agents and 'both review skills' not in agents
    assert 'was usually removed by a cleanup' in project and 'was usually removed by a cleanup' in address
    for path in ('REVIEW.md', TEMPLATE):
        assert 'was usually removed by one' in _read(path).replace('\n', ' '), path
    assert 'never edits or removes a decision on its own' in project
    assert 'what the user decides, if a reviewer could raise it again, goes in DECISIONS.md' in address


def _used_twice(text: str) -> list[str]:
    ids = re.findall(r'(?m)^- \[.\] \*\*([A-Z]+-\d+) ', text)
    return sorted({i for i in ids if ids.count(i) > 1})


def test_no_id_is_used_twice_in_review_md() -> None:
    assert _used_twice(_read('REVIEW.md')) == []


def test_the_twice_check_catches_a_repeat_and_accepts_no_findings() -> None:
    assert _used_twice('- [x] **HLP-1 · one** · `a`\n- [ ] **HLP-1 · two** · `b`\n- [x] **HLP-2 · three** · `c`\n') == [
        'HLP-1'
    ]
    assert _used_twice('# REVIEW.md\n') == [], 'a cleanup with no open findings leaves none'


def _cleaned_up(text: str) -> str:
    """REVIEW.md as a cleanup with no open findings leaves it: the header kept, everything else gone."""
    return (
        text[: text.index('## Status')]
        + _status_table(dict.fromkeys(SEVERITIES, (0, 0)))
        + '\n## Review log\n\n## High\n\n## Medium-high\n\n## Medium\n\n## Low-medium\n\n## Low\n'
    )


def _status_table(counts: dict[str, tuple[int, int]]) -> str:
    rows = ''.join('| %s | %d | %d |\n' % (severity, *counts[severity]) for severity in SEVERITIES)
    opened, resolved = sum(c[0] for c in counts.values()), sum(c[1] for c in counts.values())
    return '## Status\n\n| Severity | Open | Resolved |\n|---|---|---|\n%s| **Total** | **%d** | **%d** |\n' % (
        rows,
        opened,
        resolved,
    )


def _status_problems(text: str) -> list[str]:
    """Where the status table disagrees with the entries in the severity sections, the only place it counts."""
    status = re.search(r'(?ms)^## Status\n(.*?)(?=^## |\Z)', text)
    table = status.group(1) if status else ''
    problems = [] if status else ['no ## Status section']
    totals = [0, 0]
    for severity in SEVERITIES:
        section = re.search(r'(?ms)^## %s\n(.*?)(?=^## |\Z)' % severity, text)
        row = re.search(r'(?m)^\| %s \| (\d+) \| (\d+) \|$' % severity, table)
        if not section or not row:
            problems.append('%s: no %s' % (severity, 'section' if not section else 'row in the status table'))
            continue
        entries = section.group(1)
        counted = [len(re.findall(r'(?m)^- \[%s\] \*\*' % mark, entries)) for mark in (' ', 'x')]
        totals = [totals[0] + counted[0], totals[1] + counted[1]]
        if [int(row.group(1)), int(row.group(2))] != counted:
            problems.append(
                '%s: the table says %s open and %s resolved, the section has %s and %s'
                % (severity, *row.groups(), *counted)
            )
    total = re.search(r'(?m)^\| \*\*Total\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \|$', table)
    if not total:
        problems.append('no Total row in the status table')
    elif [int(total.group(1)), int(total.group(2))] != totals:
        problems.append(
            'Total: the table says %s open and %s resolved, the sections have %s and %s' % (*total.groups(), *totals)
        )
    return problems


def test_the_status_table_counts_the_entries_in_review_md() -> None:
    assert _status_problems(_read('REVIEW.md')) == []


def _sample_review(status: str) -> str:
    return (
        status
        + '\n## Review log\n\n- [x] **HLP-9 · not an entry of a section** · `a`\n'
        + '\n## High\n\n- [ ] **HLP-1 · open** · `a`\n  - **Defect.** A body.\n'
        + '\n## Medium-high\n\n## Medium\n\n- [x] **HLP-2 · resolved** · `b`\n- [x] **HLP-3 · resolved** · `c`\n'
        + '\n## Low-medium\n\n## Low\n'
    )


SAMPLE_COUNTS = {'High': (1, 0), 'Medium-high': (0, 0), 'Medium': (0, 2), 'Low-medium': (0, 0), 'Low': (0, 0)}


def test_the_status_check_accepts_a_table_that_matches_its_sections() -> None:
    assert _status_problems(_sample_review(_status_table(SAMPLE_COUNTS))) == []


@pytest.mark.parametrize(
    ('change', 'reported'),
    [
        (lambda s: s.replace('| High | 1 | 0 |', '| High | 0 | 0 |'), 'High: the table says 0 open and 0 resolved'),
        (
            lambda s: s.replace('| Medium | 0 | 2 |', '| Medium | 0 | 3 |'),
            'Medium: the table says 0 open and 3 resolved',
        ),
        (lambda s: s.replace('**1** | **2**', '**1** | **9**'), 'Total: the table says 1 open and 9 resolved'),
        (lambda s: s.replace('| Low | 0 | 0 |\n', ''), 'Low: no row'),
        (lambda s: s.replace('## Low\n', ''), 'Low: no section'),
        (lambda s: s.replace('| **Total** | **1** | **2** |\n', ''), 'no Total row'),
        (lambda s: s.replace('## Status\n', ''), 'no ## Status'),
    ],
)
def test_the_status_check_catches_a_table_that_does_not_match(change: Callable[[str], str], reported: str) -> None:
    text = _sample_review(_status_table(SAMPLE_COUNTS))
    assert change(text) != text, 'the sample must hold what this case changes'
    assert any(reported in problem for problem in _status_problems(change(text)))


def test_the_status_check_catches_resolved_counts_a_cleanup_left_behind() -> None:
    stale = _status_table({**dict.fromkeys(SEVERITIES, (0, 0)), 'Low': (0, 241)})
    cleaned = _cleaned_up(_read('REVIEW.md'))
    fresh = cleaned[cleaned.index('## Status') : cleaned.index('\n## Review log')]
    assert any('Low:' in problem for problem in _status_problems(cleaned.replace(fresh, stale.rstrip('\n'))))


def test_a_cleaned_up_file_passes_the_checks_on_the_file() -> None:
    cleaned = _cleaned_up(_read('REVIEW.md'))
    assert _used_twice(cleaned) == [] and _counter_problems(cleaned) == [] and _status_problems(cleaned) == []
    assert 'python3 scripts/review_lookup.py HLP-56' in cleaned


@needs_sh
def test_the_cleanup_lists_what_the_log_and_notes_would_take_with_them(tmp_path: Path) -> None:
    found = re.findall(
        r"`(grep -nE '[^`]*Simplifications[^`]*)`", _read(os.path.join(SKILLS, 'cleanup-review', 'SKILL.md'))
    )
    assert len(found) == 1
    wanted = [
        '- **Simplifications:** a dead fallback',
        '  - Note (2026-11-02): a leftover',
        '    - Note (2026-11-03): deeper',
    ]
    (tmp_path / 'REVIEW.md').write_text(
        '\n'.join([*wanted, '- **How:** five reviewers', '  - **Fix.** Note this']) + '\n', encoding='utf-8'
    )
    printed = _sh(found[0], tmp_path)
    assert all(line in printed for line in wanted)
    assert 'five reviewers' not in printed and 'Note this' not in printed
    assert 'ROADMAP.md' in _read(os.path.join(SKILLS, 'cleanup-review', 'SKILL.md'))


def test_resolutions_no_longer_record_commit_hashes() -> None:
    """Branches are squashed into main, so a branch commit's hash stops resolving."""
    assert 'abc1234' not in _read(os.path.join(SKILLS, 'project-code-review', 'TEMPLATE.md'))
    assert '`<commit>`' not in _read(os.path.join(SKILLS, 'project-code-review', 'TEMPLATE.md'))
    assert 'uncommitted on' not in _read(os.path.join(SKILLS, 'address-review', 'SKILL.md'))


@pytest.mark.parametrize('skill', REVIEW_SKILLS)
def test_a_skills_description_is_one_valid_line(skill: str) -> None:
    """Wrapped over two lines, the `: ` in address-review's description wasn't valid YAML, and the skill list
    fell back to the file's first heading, so agents no longer saw when to use the skill."""
    head = _read(os.path.join(SKILLS, skill, 'SKILL.md')).split('---')[1]
    line = next(line for line in head.splitlines() if line.startswith('description:'))
    value = line[len('description:') :].strip()
    assert value, '%s: the description must stay on the one line' % skill
    quoted = value[0] in '\'"' and value[-1] == value[0]
    assert quoted or ': ' not in value, '%s: a description with ": " must be quoted' % skill
