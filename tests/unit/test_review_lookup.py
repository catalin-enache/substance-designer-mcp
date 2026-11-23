"""A finding removed from REVIEW.md by a cleanup stays findable in git (scripts/review_lookup.py), and the rules the
review docs agree on."""

import ast
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from docs_text import NOT_DOC_READERS, agent, bare_tags, flat, read, rule, skill, story_md

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
    text = read(path)
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
    lines: list[str] = re.findall(r'(?m)^\*\*Last used:\*\* (.*)\.$', text)
    if len(lines) != 1:
        return ['expected one **Last used** line, found %d' % len(lines)]
    used: list[tuple[str, str]] = re.findall(r'([A-Z]+)-(\d+)', lines[0])
    counters = {prefix: int(number) for prefix, number in used}
    entries: list[tuple[str, str]] = re.findall(r'(?m)^- \[.\] \*\*([A-Z]+)-(\d+) ', text)
    problems = []
    for prefix, number in entries:
        if int(number) > counters.get(prefix, -1):
            problems.append('%s-%s is above **Last used**' % (prefix, number))
    for prefix in _prefixes(text):
        if prefix not in counters:
            problems.append('**IDs** names %s, which **Last used** lacks' % prefix)
    return problems


def _prefixes(text: str) -> list[str]:
    """The prefixes the header's **IDs** paragraph names, one ending a line too."""
    return re.findall(r'\*\*([A-Z]{3})\*\*\s', text.split('**Last used:**')[0].split('**IDs.**')[-1])


@pytest.mark.parametrize(
    'text, problem',
    [
        ('# REVIEW.md\n', 'expected one'),
        ('**Last used:** HLP-1.\n**Last used:** HLP-2.\n', 'expected one'),
        ('**Last used:** HLP-80.\n\n- [ ] **HLP-81 · forgot the counter** · `a.py`\n', 'HLP-81 is above'),
        ('**Last used:** HLP-80.\n\n- [ ] **SRV-1 · new prefix, not added** · `a.py`\n', 'SRV-1 is above'),
        ('**IDs.** **PLG** plugin, **HLP** helpers.\n\n**Last used:** HLP-80.\n', 'names PLG'),
        # a prefix ending a line, as **SRV** does in REVIEW.md, was skipped
        ('**IDs.** **HLP** helpers, **SRV**\nthe server.\n\n**Last used:** HLP-80.\n', 'names SRV'),
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
    assert _counter_problems(read(path)) == []


def test_the_template_names_every_prefix_review_md_names() -> None:
    # REVIEW.md TST-593: a REVIEW.md made from the template takes its **IDs**, and its **Last used** covers them
    assert sorted(_prefixes(read(TEMPLATE))) == sorted(_prefixes(read('REVIEW.md')))


@pytest.mark.parametrize('name', REVIEW_SKILLS)
def test_each_skill_uses_the_counters_and_not_the_old_command(name: str) -> None:
    text = skill(name)
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


@pytest.mark.parametrize(
    'path',
    (
        os.path.join(SKILLS, 'project-code-review', 'SKILL.md'),  # the REVIEW.md rules moved out of AGENTS.md
        'REVIEW.md',
        os.path.join(SKILLS, 'project-code-review', 'TEMPLATE.md'),
        os.path.join('.claude', 'agents', 'reviewer.md'),  # the reviewer's rules moved out of the review skill
        os.path.join(SKILLS, 'address-review', 'SKILL.md'),
    ),
)
def test_the_docs_ask_for_not_reproducible(path: str) -> None:
    head = _header(read(path))  # REVIEW.md's old entries keep the wording they were written in
    assert 'not reproducible' in head and 'not reproduced' not in head.lower()


@pytest.mark.parametrize('path', LOOKUP_DOCS)
def test_the_docs_dont_say_empty_output_can_only_mean_one_thing(path: str) -> None:
    assert 'nothing only' not in flat(read(path))


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
    assert 'memory per branch' in flat(read(path))


def test_decisions_says_it_is_the_memory_for_the_whole_project() -> None:
    assert 'memory for the whole project' in flat(read('DECISIONS.md'))


def test_decisions_and_roadmap_are_proposed_while_reviewing_and_addressing_never_at_a_cleanup() -> None:
    # the user's rule (2026-11-16): REVIEW.md is the memory per branch; what goes in DECISIONS.md (only what stops
    # reviewers raising the same finding again) or ROADMAP.md is proposed to them during the reviews and while the
    # findings are addressed, and added once they approve, never at a cleanup
    project = flat(skill('project-code-review'))
    address = flat(skill('address-review'))
    cleanup = flat(skill('cleanup-review'))
    assert 'moves nothing to `DECISIONS.md` or `ROADMAP.md`' in cleanup
    assert 'Simplifications' not in cleanup and 'Resolution: ' not in cleanup, 'no search for what to move'
    assert 'The `cleanup-review` skill proposes' not in address
    assert 'moves nothing to `DECISIONS.md`, so this is the time' in address
    assert 'propose it to the user for `ROADMAP.md`' in address
    assert '**Propose to the user' in project and 'a `ROADMAP.md` item' in project
    # the docs table's row on DECISIONS.md moved to `.claude/rules/docs.md` (REVIEW.md TST-602)
    for path in ('AGENTS.md', 'DECISIONS.md', os.path.join('.claude', 'rules', 'docs.md')):
        assert 'at a cleanup' not in flat(read(path)), path
    # REVIEW.md AGT-107: `docs.md`, which every agent loads, had it add new ideas to ROADMAP.md itself. It points to the
    # skill by its path, as a reviewer has no Skill tool to load it
    docs = flat(rule('docs.md'))
    assert 'add new ideas there' not in docs
    assert 'Propose new ideas to the user, who decides each one.' in docs
    assert "as the `address-review` skill's After a group says (`.claude/skills/address-review/SKILL.md`)" in docs


def test_roadmap_md_says_a_checked_items_figures_stay_as_they_were() -> None:
    # the user, 2026-11-20: a checked item's figures aren't updated after. Its pointers and paths still are: the docs
    # tests check them
    introduction = flat(read('ROADMAP.md').split('\n## ', 1)[0])
    said = "A checked item's figures (sizes, counts, times) are those of when it was checked, and aren't updated after."
    assert '(git history keeps the record). ' + said in introduction


def test_a_false_finding_gets_no_decisions_entry() -> None:
    # the user's rule (2026-11-20): a not-a-bug or not-reproducible answer is a review's finding that didn't hold, not
    # a decision, so it stays in REVIEW.md and nothing proposes it for DECISIONS.md
    address = flat(skill('address-review'))
    project = flat(skill('project-code-review'))
    developer = flat(agent('developer'))
    assert 'A false finding stays in `REVIEW.md` only' in address
    assert 'propose its entry' not in address
    assert 'never for a false finding' in project
    assert 'entry for a false finding' not in developer
    decisions = flat(read('DECISIONS.md'))
    assert 'is no decision and stays in `REVIEW.md`' in decisions
    for path in ('DECISIONS.md', os.path.join('.claude', 'rules', 'docs.md')):
        text = flat(read(path))
        assert 'not-a-bug answers' not in text and 'not-reproducible answer the user approved' not in text, path


def test_a_finding_names_who_found_it_and_the_model_it_ran_on() -> None:
    # the user, 2026-11-20: "in the reviews.md i want to know which model found what (logged with the finding)". Older
    # entries don't have it, so REVIEW.md's aren't read here
    text = read(TEMPLATE)
    titles: list[str] = re.findall(r'(?m)^- \[.\] \*\*ID · .*$', text)
    assert len(titles) == 2 and all(title.endswith('· found YYYY-MM-DD by `<who> (<model>)`') for title in titles), (
        titles
    )
    template = flat(text)
    for said in (
        '`found 2026-11-20 by a reviewer (Sonnet)`',
        '`by two reviewers (Opus, Sonnet)`',
        "its file's, or the one the lead passed on the Agent call",
        "Older entries don't have it",
    ):
        assert said in template, said
    project = flat(skill('project-code-review'))
    for said in (
        'its title line naming both reviewers and their models',  # step 4
        'Its title line ends with who found it and the model that agent ran on',  # step 5
        'the developer, or the runner whose probe found it',
    ):
        assert said in project, said
    assert 'mention that two reviewers found it' not in project


def test_each_review_round_adds_its_rows_to_the_table_by_model() -> None:
    # the user, 2026-11-20: "i also want to be logged in reviews how much time it took for the review to happen and how
    # many tokens were spent", "i want a different table for that so that it is easy to see which model found how many
    # bugs the time it took and the tokens spent", then "for each review round rows are added and filled in with values
    # for that round and a last row with total, that last row will keep increasing the counts during the branch life"
    text = read(TEMPLATE)
    assert text.index('\n## Status\n') < text.index('\n## Reviews by model\n') < text.index('\n## Review log\n')
    assert BY_MODEL_HEADER in text.splitlines()
    template = flat(text)
    for said in (
        "the lead adds that round's rows, every column filled: one row per model that ran, and a `settling` row when "
        'the lead used agents to settle suspicions',
        'The last row is **Total**, which the lead updates after each round and each developer run to sum every row above it',
        "counted from each finding's `found ... by <who> (<model>)`",
        "the round's slowest agent of the row",
        "the usage each agent's completion notice gives (its tokens and duration)",
        "The lead's own share isn't in it",
    ):
        assert said in template, said
    assert '**Cost:**' not in template, 'the table, not a field of each log entry'
    project = flat(skill('project-code-review'))
    assert "add the round's rows to the table under `## Reviews by model`, and update its **Total** row" in project
    # REVIEW.md TST-624: the list of what a review adds to REVIEW.md has the rows too
    assert "add an entry to the review log and the round's rows to the table under `## Reviews by model`" in project
    # "at cleanup review the table will be cleaned at the end"
    assert 'A cleanup empties the table at its end, and git keeps the rows' in template
    cleanup = flat(skill('cleanup-review'))
    assert '**Empty the table under `## Reviews by model`** last' in cleanup
    assert "Its heading, its explanation and the table's header row stay" in cleanup


def _by_model_rows(text: str) -> list[list[str]]:
    """The rows of the table under `## Reviews by model`, each its cells, after the header row and the separator."""
    section = re.search(r'(?ms)^## Reviews by model\n(.*?)(?=^## |\Z)', text)
    lines: list[str] = [line for line in (section.group(1) if section else '').splitlines() if line.startswith('|')]
    return [[cell.strip() for cell in line.strip('|').split('|')] for line in lines[2:]]


def _number(cell: str) -> int | None:
    """A cell of the table by model as a number: `**1,021,051**` is 1021051, `17 min` is 17. None for anything else."""
    found = re.fullmatch(r'\**([\d,]+)( min)?\**', cell)
    return int(found[1].replace(',', '')) if found else None


def _findings(cell: str) -> tuple[int, dict[str, int]] | None:
    """A findings cell of the table by model: its count, and the count of each severity in its brackets.
    `**9 [1 Low-medium, 8 Low]**` gives 9 and {'Low-medium': 1, 'Low': 8}, and `0` gives 0 and {}. None for a cell in
    another form: a severity unknown, out of order, of no finding or named twice."""
    found = re.fullmatch(r'\**(\d+)(?: \[([^\]]+)\])?\**', cell)
    if not found:
        return None
    brackets: str | None = found[2]
    severities: dict[str, int] = {}
    for part in brackets.split(', ') if brackets else []:
        counted = re.fullmatch(r'([1-9]\d*) (\S+)', part)
        if not counted or counted[2] not in SEVERITIES or counted[2] in severities:
            return None
        severities[counted[2]] = int(counted[1])
    return (int(found[1]), severities) if list(severities) == sorted(severities, key=SEVERITIES.index) else None


# the table by model's header row (the column Instances: the user, 2026-11-20)
BY_MODEL_HEADER = '| Review | Model | Instances | Real findings | Found only by this model | Tokens | Time |'
COLUMNS = [cell.strip() for cell in BY_MODEL_HEADER.strip('|').split('|')]
# the columns the Total row sums, by their place in a row: numbers, and counts of findings by severity
SUMMED = {column: COLUMNS[column] for column in (2, 5, 6)}
FINDINGS = {column: COLUMNS[column] for column in (3, 4)}
DEVELOPER = ' (developer)'  # ends the model of a developer run's row


def _by_model_problems(text: str) -> list[str]:
    """Where the table by model's last row isn't a Total summing the rows above it, each severity of the findings
    included; where a findings cell's severities don't add up to its count; and a developer's row that counts other
    than 1 instance. None for a table without rows: an older file, or one just cleaned up."""
    rows = _by_model_rows(text)
    if not rows:
        return []
    if rows[-1][0] != '**Total**':
        return ['the last row is no **Total** row: %s' % rows[-1]]
    problems = []
    for column, name in SUMMED.items():
        cells = [_number(row[column]) for row in rows]
        numbers = [cell for cell in cells if cell is not None]
        if len(numbers) < len(cells):
            problems.append('%s: a cell that is no number: %s' % (name, [row[column] for row in rows]))
        elif sum(numbers[:-1]) != numbers[-1]:
            problems.append('%s: the rows sum to %d, the Total says %d' % (name, sum(numbers[:-1]), numbers[-1]))
    for column, name in FINDINGS.items():
        counts = [_findings(row[column]) for row in rows]
        parsed = [count for count in counts if count is not None]
        if len(parsed) < len(counts):
            problems.append(
                '%s: a cell that is no count of findings by severity: %s' % (name, [r[column] for r in rows])
            )
            continue
        problems += [
            '%s: %s: its severities sum to %d' % (name, row[column], sum(severities.values()))
            for row, (count, severities) in zip(rows, parsed, strict=True)
            if sum(severities.values()) != count
        ]
        *above, (total, severities) = parsed
        summed = sum(count for count, _ in above)
        if summed != total:
            problems.append('%s: the rows sum to %d, the Total says %d' % (name, summed, total))
        for severity in SEVERITIES:
            summed, said = sum(counted.get(severity, 0) for _, counted in above), severities.get(severity, 0)
            if summed != said:
                problems.append("%s: the rows' %s sum to %d, the Total says %d" % (name, severity, summed, said))
    problems += [
        "%s: a developer's row counts 1 instance: %s" % (row[0], row)
        for row in rows
        if row[1].endswith(DEVELOPER) and _number(row[2]) != 1
    ]
    return problems


BY_MODEL_SAMPLE = (
    '## Reviews by model\n\n' + BY_MODEL_HEADER + '\n'
    '|---|---|---|---|---|---|---|\n'
    '| 2026-11-20, first | Opus | 4 | 8 [1 Medium, 7 Low] | 5 [1 Medium, 4 Low] | 1,021,051 | 17 min |\n'
    '| 2026-11-20, first | Sonnet | 4 | 7 [2 Low-medium, 5 Low] | 4 [1 Low-medium, 3 Low] | 971,644 | 11 min |\n'
    "| 2026-11-20, the first review's fixes | Opus (developer) | 1 | 2 [2 Low] | 2 [2 Low] | 412,300 | 9 min |\n"
    '| 2026-11-20, second | Sonnet | 2 | 0 | 0 | 373,952 | 8 min |\n'
    "| 2026-11-20, the second review's fixes | Opus (developer) | 1 | 0 | 0 | 158,200 | 4 min |\n"
    '| **Total** | all | **12** | **17 [1 Medium, 2 Low-medium, 14 Low]** | **11 [1 Medium, 1 Low-medium, 9 Low]** '
    '| **2,937,147** | **49 min** |\n'
    '\n## Review log\n'
)


def test_the_table_by_models_total_sums_its_rows() -> None:
    # REVIEW.md TST-623: the lead adds each round's rows and updates the Total by hand
    assert _by_model_problems(BY_MODEL_SAMPLE) == []
    assert _by_model_problems(read('REVIEW.md')) == []


@pytest.mark.parametrize(
    ('change', 'reported'),
    [
        (lambda s: s.replace('**2,937,147**', '**2,937,146**'), 'Tokens: the rows sum to 2937147'),
        (
            lambda s: s.replace('| 4 [1 Low-medium, 3 Low] |', '| 5 [1 Low-medium, 4 Low] |'),
            'Found only by this model: the rows sum to 12',
        ),
        (lambda s: s.replace('| 17 min |', '| 17 minutes |'), 'Time: a cell that is no number'),
        (lambda s: s.replace('| **Total** |', '| 2026-11-20, third |'), 'no **Total** row'),
        # the user's severities in the findings cells (2026-11-20): each one's Total sums the rows' too
        (
            lambda s: s.replace('**17 [1 Medium, 2 Low-medium, 14 Low]**', '**17 [2 Medium, 1 Low-medium, 14 Low]**'),
            "Real findings: the rows' Medium sum to 1, the Total says 2",
        ),
        (lambda s: s.replace('| 8 [1 Medium, 7 Low] |', '| 8 [1 Medium, 6 Low] |'), 'its severities sum to 7'),
        (
            lambda s: s.replace('| 2 [2 Low] | 2 [2 Low] |', '| 2 | 2 [2 Low] |'),
            'Real findings: 2: its severities sum to 0',
        ),
        (lambda s: s.replace('7 [2 Low-medium, 5 Low]', '7 [5 Low, 2 Low-medium]'), 'no count of findings by severity'),
        (lambda s: s.replace('8 [1 Medium, 7 Low]', '8 [1 Critical, 7 Low]'), 'no count of findings by severity'),
        (lambda s: s.replace('8 [1 Medium, 7 Low]', '8 [0 High, 1 Medium, 7 Low]'), 'no count of findings by severity'),
        (lambda s: s.replace('| 1 | 2 [2 Low] |', '| 2 | 2 [2 Low] |'), "a developer's row counts 1 instance"),
    ],
)
def test_the_table_by_models_check_catches_a_slip(change: Callable[[str], str], reported: str) -> None:
    assert change(BY_MODEL_SAMPLE) != BY_MODEL_SAMPLE, 'the sample must hold what this case changes'
    assert any(reported in problem for problem in _by_model_problems(change(BY_MODEL_SAMPLE)))


def test_the_table_by_model_has_the_developers_row_and_the_severities_in_its_cells() -> None:
    # the user, 2026-11-20, on the findings the developer finds while fixing a round's: "yes, count them in a developer
    # row". Then: "I'd like in the table with reviewers per model the findings to be grouped as 5 [3(low), 2(medium),
    # e.t.c] inside the cell value". Then: "i want a row everytime a developer works", with its cost
    text = read(TEMPLATE)
    template = flat(text)
    for said in (
        'The developer gets a row for each run: every Agent call to a `developer`, and every resume of one with '
        'SendMessage that ends in a report (the user, 2026-11-20)',
        "Its **Review** names the work, such as `2026-11-20, the nineteenth review's fixes`",
        'Its **Model** is `<model> (developer)`, such as `Opus (developer)`, and its **Instances** is 1',
        # the user, 2026-11-20: "i think the Reviewers header in REVIEW table for reviewers should be called Instances"
        '- **Instances:** how many agents the row counts.',
        'Its two findings cells count the new problems it found that the lead settled as real, or `0` for none',
        "Its **Tokens** and **Time** come from its completion notice, as a reviewer's do. For a resumed developer, the "
        "Tokens are those its notice adds since that agent's previous notice, and the Time is that run's duration",
        'A finding the runner or the lead found is recorded on its title line only, in no row',
        'then in brackets the count of each severity among them, most severe first: `9 [1 Low-medium, 8 Low]`, or '
        '`0` for none',
        'The **Total** row sums each severity too',
        'how many of those no other row of the round found, written the same way',
    ):
        assert said in template, said
    assert 'A finding another agent found (the developer, the runner, the lead)' not in template
    assert "are 0 and `0 min`, since the developer's run was the fixes'" not in template
    # where the lead takes in a developer's report, it adds the run's row
    assert 'Every developer run gets a row in the table by model, with its cost' in flat(skill('address-review'))
    assert 'After each developer run, the lead adds its row to the table under `## Reviews by model`' in flat(
        skill('project-code-review')
    )
    story = flat(story_md())
    assert 'per review round and per developer run' in story
    # REVIEW.md TST-637: and the files table's row on REVIEW.md
    assert 'a table by model of the findings, tokens and time of each round and each developer run' in story
    status = text.split('\n## Status\n', 1)[1].split('\n## ', 1)[0]
    assert tuple(re.findall(r'(?m)^\| ([A-Z][\w-]*) \| \d', status)) == SEVERITIES, 'most severe first'


def _header(markdown: str) -> str:
    """The header of a REVIEW.md, or of the template: what comes before `## Status`."""
    return markdown.split('\n## Status')[0]


def _header_paragraphs(markdown: str) -> list[str]:
    """The first word of each paragraph of a REVIEW.md's header, before `## Status`."""
    return [part.split()[0] for part in _header(markdown).split('\n\n') if part.strip()]


def _entry_titles(text: str) -> list[str]:
    """The title line of each entry of a REVIEW.md."""
    return re.findall(r'(?m)^- \[.\] \*\*[A-Z]+-\d+ .*$', text)


def test_review_md_has_the_templates_new_paragraphs_where_the_template_puts_them() -> None:
    # REVIEW.md TST-621, TST-623: its header is the template's, and the table by model's explanation too, in the
    # template's order (REVIEW.md's older paragraphs keep their wording, so only these three are compared). The
    # **IDs** paragraph is compared since the user's decision of 2026-11-20: AGT covers everything in `.claude/`, TST
    # the tests and the docs outside it, and a finding over several files takes the prefix of its first location
    template = read(TEMPLATE)
    paragraphs = template.split('\n\n')
    found_by = next(part for part in paragraphs if part.startswith('**Found by.**'))
    ids = next(part for part in paragraphs if part.startswith('**IDs.**'))
    assert '**AGT** everything in `.claude/`' in flat(ids) and 'takes the prefix of its first location' in flat(ids)
    explanation = template.split('## Reviews by model\n\n', 1)[1].split('\n|---', 1)[0]  # the header row too
    review = flat(read('REVIEW.md'))
    marks = [flat(found_by), flat(ids), '## Status', '## Reviews by model', flat(explanation), '## Review log']
    found = [review.find(mark) for mark in marks]
    assert -1 not in found and found == sorted(found), list(zip(marks, found, strict=True))
    # and every paragraph of the header in the template's order, by its first word: a paragraph put inside another,
    # between a label and its list, shows as one more (REVIEW.md's paragraphs keep their own wording)
    assert _header_paragraphs(read('REVIEW.md')) == _header_paragraphs(template)


FINDER_FROM = '2026-11-20'  # the first day an entry's title line names who found it (the user)


def test_every_entry_found_from_2026_11_20_names_who_found_it() -> None:
    # REVIEW.md TST-623: older entries don't have it
    titles = [re.search(r'· found (\S+)( by .+ \([^)]+\))?$', line) for line in _entry_titles(read('REVIEW.md'))]
    assert None not in titles, 'an entry without its date'
    assert [title[0] for title in titles if title and title[1] >= FINDER_FROM and not title[2]] == []


def test_a_false_finding_is_reported_for_the_lead_to_check() -> None:
    # REVIEW.md AGT-92, TST-615: only the lead writes REVIEW.md (the user, 2026-11-19), so step 2 has the developer
    # report a false finding's resolution, and the lead checks the entry off (step 7)
    address = flat(skill('address-review'))
    assert "report the entry's resolution as *not a bug* or *not reproducible* (step 7)" in address
    assert '*not reproducible* and check it' not in address


def test_a_review_reads_decisions_first_then_review() -> None:
    assert 'Read `DECISIONS.md` (repo root) first, then `REVIEW.md`.' in flat(skill('project-code-review'))


def test_the_cleanup_says_where_the_header_ends() -> None:
    assert 'The header ends before `## Status`' in skill('cleanup-review')


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
    text = read(TEMPLATE)
    for found in _last_used(repo):
        prefix = found.split('-')[0]
        assert '%s-0' % prefix in text or prefix not in _prefixes(text)
        text = text.replace('%s-0' % prefix, found)
    return text


@needs_git
def test_the_template_alone_would_reuse_numbers_after_a_deletion(reviewed: Path) -> None:
    _delete_review(reviewed)
    (reviewed / 'REVIEW.md').write_text(read(TEMPLATE), encoding='utf-8')
    assert [line.split(':')[0] for line in _counter_against_history(reviewed)] == ['HLP', 'TST']


@needs_git
def test_a_recreated_file_gets_its_counters_from_history(reviewed: Path) -> None:
    _delete_review(reviewed)
    assert _last_used(reviewed) == ['HLP-81', 'TST-140']
    recreated = _recreated(reviewed)
    assert '**Last used:** PLG-0, SRV-0, HLP-81, INS-0, TST-140, AGT-0.' in recreated
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
    _commit(tmp_path, read(TEMPLATE))
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


# a test naming one of these docs, or a folder of .claude that holds docs (its skills, agents and rules), validates the
# docs. The tests of .claude's hooks name .claude too, and validate code
DOC_TESTS = re.compile(
    r"""(['"])(?:AGENTS|GUIDE|README|ROADMAP|DECISIONS|REVIEW)\.md\1"""
    r"""|(['"])\.claude\2,\s*(['"])(?:skills|agents|rules)\3"""
)


def _reads_a_doc(source: str) -> bool:
    """Whether the test file's `source` names a doc (DOC_TESTS), or imports from docs_text.py what reads one."""
    return bool(DOC_TESTS.search(source)) or (
        'docs_text' in source
        and any(
            (isinstance(node, ast.Import) and 'docs_text' in {alias.name for alias in node.names})
            or (
                isinstance(node, ast.ImportFrom)
                and node.module == 'docs_text'
                and bool({alias.name for alias in node.names} - NOT_DOC_READERS)
            )
            for node in ast.walk(ast.parse(source))
        )
    )


@pytest.mark.parametrize(
    'source, reads',
    [
        ("Path(ROOT, 'AGENTS.md')", True),
        ('read("GUIDE.md")', True),
        ("os.path.join('.claude', 'skills')", True),
        ('os.path.join(".claude", "rules")', True),
        # a docstring's opening quote and an apostrophe after the name name no doc (REVIEW.md TST-773)
        ('"""GUIDE.md\'s recipe, end to end."""', False),
        ('"""See \'.claude", "rules" in ..."""', False),
        ('from docs_text import agents_md', True),
        ('from docs_text import (\n    flat,\n    skill,\n)', True),
        ('import docs_text', True),
        ('from docs_text import flat, headings, repo_files, section', False),
        ("Path(ROOT, 'mcp_server', 'server.py')", False),
    ],
)
def test_a_test_that_reads_a_doc_is_found(source: str, reads: bool) -> None:
    assert _reads_a_doc(source) == reads


def test_the_docs_command_names_every_test_that_reads_a_doc() -> None:
    """A commit of docs alone (`.claude/rules/docs-tests.md`) runs only these, so a new test reading a doc must join
    the list."""
    unit = os.path.join(ROOT, 'tests', 'unit')
    reading = {
        name
        for name in os.listdir(unit)
        if name.startswith('test_') and name.endswith('.py') and _reads_a_doc(read('tests', 'unit', name))
    }
    commands: list[str] = re.findall(
        r'`mcp_server/venv/bin/python -m pytest (tests/unit/[^`]+)`', rule('docs-tests.md')
    )
    assert len(commands) == 1, 'the rule should give the docs command once'
    assert {os.path.basename(path) for path in commands[0].split()} == reading


def test_the_wording_of_the_rules_agreed_on() -> None:
    project = flat(skill('project-code-review'))
    address = flat(skill('address-review'))
    cleanup = flat(skill('cleanup-review'))
    for path in LOOKUP_DOCS:
        text = flat(read(path))
        assert 'ever used twice' not in text, path
        assert 'Nothing lowers a committed number' in text, path
    assert 'merges second' in project and 'git diff main...HEAD' in project
    # an answer in both files follows the decision, and a false finding isn't raised again: the reviewer's own rules,
    # in its file (test_agents.py)
    # the user, 2026-11-19 (it replaces 2026-11-18's "all Low"): what counts is the findings, not the number of review
    # rounds. Only a few Low findings, the first review included, or none, mean the reviews look converged, and the
    # user decides on another round
    assert 'What counts is the findings, not the number of review rounds' in project
    assert 'new findings are only a few Low ones, the first review included, says the reviews look converged' in project
    assert 'review with no findings (the user, 2026-11-19)' in project and 'second review' not in project
    assert 'The user decides: another round, or the final check' in project
    assert 'in exactly these words' not in address and 'starts with' in address
    assert "and the entry's **Reopen if** doesn't hold" not in address, 'stop and ask whether it holds or not'
    assert 'tests that validate the docs' in cleanup
    assert 'lookup' in read('ROADMAP.md').split('## Review hotspots')[1].split('| Done |')[0]


def test_the_wording_of_the_smaller_points_agreed_on() -> None:
    docs = flat(rule('docs.md'))  # moved out of AGENTS.md
    project = flat(skill('project-code-review'))
    address = flat(skill('address-review'))
    assert 'One repeat is deliberate' in docs
    assert 'read by the review skills' in docs and 'both review skills' not in docs
    assert 'was usually removed by a cleanup' in project and 'was usually removed by a cleanup' in address
    for path in ('REVIEW.md', TEMPLATE):
        assert 'was usually removed by one' in flat(read(path)), path
    assert 'never edits or removes a decision on its own' in project
    assert 'what the user decides, if a reviewer could raise it again, goes in DECISIONS.md' in address


def _used_twice(text: str) -> list[str]:
    ids = re.findall(r'(?m)^- \[.\] \*\*([A-Z]+-\d+) ', text)
    return sorted({i for i in ids if ids.count(i) > 1})


def test_no_id_is_used_twice_in_review_md() -> None:
    assert _used_twice(read('REVIEW.md')) == []


def test_the_twice_check_catches_a_repeat_and_accepts_no_findings() -> None:
    assert _used_twice('- [x] **HLP-1 · one** · `a`\n- [ ] **HLP-1 · two** · `b`\n- [x] **HLP-2 · three** · `c`\n') == [
        'HLP-1'
    ]
    assert _used_twice('# REVIEW.md\n') == [], 'a cleanup with no open findings leaves none'


def _entries(text: str) -> dict[str, str]:
    """The entries of a REVIEW.md by ID, each its whole text: its title line, up to the next entry or section."""
    return {
        found[1]: found[0]
        for found in re.finditer(r'(?ms)^- \[.\] \*\*([A-Z]+-\d+) .*?(?=^- \[.\] \*\*|^## |\Z)', text)
    }


def _unquestioned(text: str) -> list[str]:
    """The "Questioned by" lines a REVIEW.md lacks, each as `<old ID>: Questioned by <new ID>`. The title line of the
    entry <new ID> follows <old ID> (`· follows X, generation N`, or several IDs joined by `, ` or ` and `), and the
    entry <old ID> has no line `- Questioned by` naming <new ID> (the `project-code-review` skill, step 2). An old entry
    a cleanup removed is skipped: there is nothing to add the line under."""
    entries = _entries(text)
    missing = []
    for new, entry in entries.items():
        follows = re.search(r'· follows ([A-Z]+-\d+(?:(?:, | and )[A-Z]+-\d+)*)', entry.partition('\n')[0])
        for old in re.findall(r'[A-Z]+-\d+', follows[1]) if follows else ():
            if old in entries and not re.search(r'(?m)^\s+- Questioned by .*\b%s\b' % new, entries[old]):
                missing.append('%s: Questioned by %s' % (old, new))
    return missing


def test_every_entry_a_follow_up_questions_says_so() -> None:
    # REVIEW.md TST-636: a reader of an old entry takes its resolution as standing, not seeing that a later finding
    # questioned it. The message gives every missing line, as the list's diff shows only the first
    missing = _unquestioned(read('REVIEW.md'))
    assert not missing, '; '.join(missing)


def test_the_questioned_check_catches_a_missing_line_and_skips_a_removed_entry() -> None:
    text = (
        '- [x] **HLP-1 · old** · `a`\n  - **Resolution: done.**\n  - Questioned by HLP-3, HLP-4 (2026-11-20).\n'
        '- [x] **HLP-2 · another old one** · `b`\n\n'
        '- [ ] **HLP-3 · new · follows HLP-1 and HLP-2, generation 2** · `c`\n'
        '- [ ] **HLP-4 · newer · follows HLP-1, HLP-9, generation 2** · `d`\n'  # a cleanup removed HLP-9
        '- [ ] **HLP-5 · The check follows HLP-2 in its own words** · `e`\n'  # no mark
        '  - Questioned by HLP-6 (2026-11-20).\n'  # under another entry than the one HLP-6 follows
        '\n## Low\n\n- [ ] **HLP-6 · last · follows HLP-2, generation 3** · `f`\n'
    )
    assert _unquestioned(text) == ['HLP-2: Questioned by HLP-3', 'HLP-2: Questioned by HLP-6']


# the wordings a checked entry's resolution starts with (the `address-review` skill, step 7). The last one names the
# ROADMAP.md item, the user and the date (the user, 2026-11-20)
WORDINGS = ('done', 'not a bug', 'not reproducible', "won't fix", 'moved to ROADMAP.md')
WORDED = re.compile(
    r'\*\*Resolution: (?:%s)\*\*' % '|'.join(map(re.escape, WORDINGS[:-1]))
    + r'|\*\*Resolution: %s\*\* \(item \d+, the user, \d{4}-\d{2}-\d{2}\)' % re.escape(WORDINGS[-1])
)


def _unworded(text: str) -> list[str]:
    """The IDs of the checked entries of a REVIEW.md whose first resolution line starts with none of the wordings."""
    unworded = []
    for finding, entry in _entries(text).items():
        resolution = re.search(r'\*\*Resolution\b', entry)
        if entry.startswith('- [x] ') and not (resolution and WORDED.match(entry, resolution.start())):
            unworded.append(finding)
    return unworded


def test_every_checked_entry_starts_its_resolution_with_a_wording() -> None:
    # the user, 2026-11-20: a finding moved to ROADMAP.md is closed with the fifth wording, which names the item. The
    # message gives every such entry, as the list's diff shows only the first
    unworded = _unworded(read('REVIEW.md'))
    assert not unworded, ', '.join(unworded)


def test_the_template_gives_the_wordings_the_check_accepts() -> None:
    # REVIEW.md TST-639: each in backticks, as GitHub drops a bare `<date>`
    template = flat(read(TEMPLATE))
    listed = ', '.join('`%s`' % wording for wording in (*WORDINGS[:-1], WORDINGS[-1] + ' (item N, the user, <date>)'))
    assert 'with one of these wordings: %s.' % listed in template
    assert '**Resolution: %s**' % ' | '.join(WORDINGS) in template


def test_review_mds_header_writes_no_placeholder_github_drops() -> None:
    # REVIEW.md TST-639: GitHub drops a tag it doesn't know, such as a bare `<date>`, so a placeholder of a tag's form
    # goes in backticks. The template, with every other doc, is test_guide.py's; REVIEW.md's entries keep their wording
    assert bare_tags(_header(read('REVIEW.md'))) == []


def test_the_wording_check_catches_a_resolution_without_one() -> None:
    text = (
        '- [x] **HLP-1 · one** · `a`\n  - **Resolution: done** (2026-11-20).\n'
        '- [x] **HLP-2 · two** · `b`\n  - **Resolution: not a bug** (2026-11-20).\n'
        '- [x] **HLP-3 · three** · `c`\n  - **Resolution: not reproducible** (2026-11-20).\n'
        "- [x] **HLP-4 · four** · `d`\n  - **Resolution: won't fix** (the user, 2026-11-20).\n"
        '- [x] **HLP-5 · five** · `e`\n  - **Resolution: moved to ROADMAP.md** (item 112, the user, 2026-11-20).\n'
        '- [x] **HLP-6 · no item named** · `f`\n  - **Resolution: moved to ROADMAP.md** (2026-11-20).\n'
        '- [x] **HLP-7 · another word** · `g`\n  - **Resolution: fixed** (2026-11-20).\n'
        '- [x] **HLP-8 · no resolution** · `h`\n  - **Defect.** It fails.\n'
        '- [ ] **HLP-9 · open** · `i`\n'
        '\n## Low\n\n- [x] **HLP-10 · last** · `j`\n  - **Resolution: done** (2026-11-20).\n'
    )
    assert _unworded(text) == ['HLP-6', 'HLP-7', 'HLP-8']


def _cleaned_up(text: str) -> str:
    """REVIEW.md as a cleanup with no open findings leaves it: the header kept, the status table reset, the table by
    model emptied to the template's section, everything else gone (the `cleanup-review` skill)."""
    template = read(TEMPLATE)  # its status table counts nothing, and its table by model has no rows
    return (
        text[: text.index('## Status')]
        + template[template.index('## Status\n') : template.index('## Review log\n')]
        + '## Review log\n\n## High\n\n## Medium-high\n\n## Medium\n\n## Low-medium\n\n## Low\n'
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
    assert _status_problems(read('REVIEW.md')) == []


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
    cleaned = _cleaned_up(read('REVIEW.md'))
    fresh = cleaned[cleaned.index('## Status') :].split('\n## ', 1)[0]
    assert any('Low:' in problem for problem in _status_problems(cleaned.replace(fresh, stale.rstrip('\n'))))


def test_a_cleaned_up_file_passes_the_checks_on_the_file() -> None:
    cleaned = _cleaned_up(read('REVIEW.md'))
    assert _used_twice(cleaned) == [] and _counter_problems(cleaned) == [] and _status_problems(cleaned) == []
    assert _unquestioned(cleaned) == []
    assert 'python3 scripts/review_lookup.py HLP-56' in cleaned
    # REVIEW.md TST-624: the cleanup leaves the table by model's section with its header row, and no rows
    assert '\n## Reviews by model\n' in cleaned and _by_model_rows(cleaned) == []


def test_resolutions_no_longer_record_commit_hashes() -> None:
    """Branches are squashed into main, so a branch commit's hash stops resolving."""
    assert 'abc1234' not in read(TEMPLATE)
    assert '`<commit>`' not in read(TEMPLATE)
    assert 'uncommitted on' not in skill('address-review')


def _skills(folder: str) -> list[str]:
    """The names of the skills in `folder`: its folders, hidden ones left out, as in test_constants.py (TST-79)."""
    return sorted(name for name in os.listdir(folder) if not name.startswith('.') and os.path.isdir(Path(folder, name)))


def test_the_skills_are_the_folders_with_a_skill_md(tmp_path: Path) -> None:
    # REVIEW.md TST-595: Finder writes .DS_Store into any folder it shows (TST-79), and a case of it reads
    # `.DS_Store/SKILL.md`
    copy = tmp_path / 'skills'
    shutil.copytree(os.path.join(ROOT, SKILLS), copy)
    (copy / '.DS_Store').write_bytes(b'')
    assert _skills(str(copy)) == sorted(path.parent.name for path in copy.glob('*/SKILL.md'))


@pytest.mark.parametrize('name', _skills(os.path.join(ROOT, SKILLS)))
def test_a_point_of_a_skill_is_named_with_its_list(name: str) -> None:
    # REVIEW.md TST-594: a skill numbers several lists, so a point's number follows the bold title of its list's section
    text = flat(skill(name))
    assert re.findall(r'\S+(?<!\*\*), point \d+', text) == []


@pytest.mark.parametrize('name', _skills(os.path.join(ROOT, SKILLS)))
def test_a_skills_description_is_one_valid_line(name: str) -> None:
    """Wrapped over two lines, the `: ` in address-review's description wasn't valid YAML, and the skill list
    fell back to the file's first heading, so agents no longer saw when to use the skill."""
    head = skill(name).split('---')[1]
    line = next(line for line in head.splitlines() if line.startswith('description:'))
    value = line[len('description:') :].strip()
    assert value, '%s: the description must stay on the one line' % name
    quoted = value[0] in '\'"' and value[-1] == value[0]
    assert quoted or ': ' not in value, '%s: a description with ": " must be quoted' % name
