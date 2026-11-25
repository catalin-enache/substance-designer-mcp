"""The guide reaches every session: short instructions (MCP clients cut long ones; Claude Code at
4,096 characters) that point to get_guide(), which returns the core of mcp_server/GUIDE.md; get_guide('scripting') the rest. AGENTS.md holds what
contributors need; each file has its own size limit."""

import functools
import os
import posixpath
import re
from pathlib import Path, PurePosixPath

import pytest
from doc_pointers import AFTER_FILE, TO_PART, dangling_pointers, labels
from docs_text import (
    DOC_SUFFIXES,
    agents_md,
    bare_tags,
    flat,
    guide_md,
    headings,
    read,
    repo_docs,
    repo_files,
    repo_texts,
    rule,
    section,
    skill,
    story_md,
    without_code,
)
from mcp.server.mcpserver.exceptions import ToolError
from test_server import CLAUDE_CODE_LIMIT, _described, _tools

from conftest import ROOT, fake_bridge, patch_server, server
from server_tools import scripting

AGENTS_MD_BUDGET = 15_000  # bytes (test_agents_md_stays_within_its_budget)
GUIDE_CORE_BUDGET = 14_000  # characters (test_the_core_of_the_guide_stays_within_its_budget)
# the sections of each file, by the audience that reads it
GUIDE_SECTIONS = (
    "## Rules that protect the user's work",
    '## Which tool for what',
    '## Environment facts',
    '## First sd pitfalls',
    '## Library node facts (Designer 16)',
)
SCRIPTING_SECTIONS = ('## sd API gotchas', '## Designer UI (Qt)', '## Example')
AGENTS_SECTIONS = (
    '## Working on this project',
    '### Running the tests',
    '### Delegating to subagents',
    '### Deploying and diagnosing',
)
# what the guide holds, as a link to it names it: its sections and the bold paragraphs other files point to
MOVED = (
    r'Rules|rules|Which tool|Undo|Environment facts|sd API|Designer UI|Library node|Example'
    r'|Portals|Output nodes|Graph size|Screenshots|Quitting'
)


def _rule_paths(name: str) -> list[str]:
    """The `paths:` of the rule `name`, as Claude Code parses them: a rule it can't parse never loads, silently."""
    frontmatter = re.match(r'---\npaths:\n((?:  - "[^"]+"\n)+)---\n', rule(name))
    assert frontmatter, name
    return re.findall(r'"([^"]+)"', frontmatter.group(1))


def _parts() -> tuple[str, str]:
    """The guide file's two parts, the second starting at its level-1 Scripting heading."""
    parts: list[str] = re.split(r'(?m)^(?=# Scripting)', guide_md())
    assert len(parts) == 2, 'one Scripting heading'
    return parts[0].rstrip('\n') + '\n', parts[1]


def test_instructions_fit_and_ask_for_the_guide_on_first_use() -> None:
    text = server.INSTRUCTIONS
    assert len(text) < CLAUDE_CODE_LIMIT
    # nothing up front: a session started for other work never loads the guide
    assert (
        'Do not call get_guide() or any other tool from this server unless the user asks for work in Designer' in text
    )
    assert 'Right before your first Designer tool call in this session, call get_guide()' in text
    assert 'tell the user' in text
    assert 'AGENTS.md' not in text, 'the guide is GUIDE.md now'
    assert "get_guide('scripting')" in text
    assert 'tell the user in one line that you have read the scripting part' in text


def test_get_guide_returns_the_core_of_the_guide_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(server._session, 'guide_read', False)
    monkeypatch.setitem(server._session, 'scripting_read', False)
    core, _ = _parts()
    text = server.get_guide()
    assert text.startswith(core) and server._session['guide_read']
    assert 'End of the core of the Designer guide (%d characters, complete)' % len(core) in text
    assert 'tell the user' in text.splitlines()[-1]
    assert not server._session['scripting_read'], 'the core says nothing of the scripting part'
    assert not headings(text) & set(SCRIPTING_SECTIONS)


def test_the_scripting_part_is_served_on_its_own(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(server._session, 'guide_read', False)
    monkeypatch.setitem(server._session, 'scripting_read', False)
    _, scripting = _parts()
    text = server.get_guide('scripting')
    assert text.startswith(scripting) and server._session['scripting_read']
    assert 'End of the scripting part of the Designer guide (%d characters, complete)' % len(scripting) in text
    assert 'tell the user in one line that you have read the scripting part' in text.splitlines()[-1]
    assert not server._session['guide_read'], 'the rules are in the core'


def test_an_unknown_part_is_refused_and_counts_as_nothing_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(server._session, 'guide_read', False)
    monkeypatch.setitem(server._session, 'scripting_read', False)
    with pytest.raises(ToolError, match="'core' or 'scripting'"):
        server.get_guide('nope')
    assert not server._session['guide_read'] and not server._session['scripting_read']


def test_the_pitfalls_everyone_hits_are_in_the_core() -> None:
    core, scripting = map(flat, _parts())
    for fact in ('derives from `BaseException`', 'graph.getNodeDefinitions()', 'Blend modes: copy 0'):
        assert fact in core and fact not in scripting, fact


def test_the_core_says_what_a_blend_of_a_grey_image_and_a_colour_one_gives() -> None:
    # ROADMAP item 127: a grey source over a colour destination gave the destination, black, with no error. The cases
    # measured, with their check, stay in the scripting part, which the core points to
    core, scripting = _parts()
    facts = flat(section(core, '## Library node facts (Designer 16)'))
    assert "gives its `destination`'s type" in facts
    assert 'a `source` of the other type blends as a zero of that type' in facts
    assert 'the scripting part, A blend of a grey image and a colour one' in facts
    assert '**A blend of a grey image and a colour one** ("designer facts"' in flat(scripting)


# open whatever was read: stopping a runaway script must never wait for a guide
OPEN_TOOLS = {'get_guide', 'cancel_designer_job'}


def test_every_tool_is_refused_until_the_guide_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    # the gate comes first, so no arguments are needed; every tool the server registers, image tools included
    monkeypatch.setitem(server._session, 'guide_read', False)
    monkeypatch.setitem(server._session, 'scripting_read', True)
    names = set(_tools()[1]) - OPEN_TOOLS
    assert len(names) > 30
    for name in sorted(names):
        with pytest.raises(ToolError) as refused:
            getattr(server, name)()
        assert str(refused.value) == server.GUIDE_NOT_READ, name


def test_a_tool_works_once_the_guide_is_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path))
    monkeypatch.setitem(server._session, 'guide_read', False)
    monkeypatch.setitem(server._session, 'scripting_read', False)
    server.get_guide()
    assert server.list_snapshots() == 'No snapshots.', 'only the code tools ask for the scripting part'


def test_cancelling_a_job_never_waits_for_the_guide(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_server(monkeypatch, '_control', lambda *a, **k: 'cancelled')
    monkeypatch.setitem(server._session, 'guide_read', False)
    monkeypatch.setitem(server._session, 'scripting_read', False)
    assert server.cancel_designer_job() == 'cancelled'


@pytest.mark.parametrize('tool', ['execute_designer_code', 'run_designer_script'])
def test_code_is_refused_before_it_runs_until_the_scripting_part_is_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tool: str
) -> None:
    sent: list[str] = []

    def bridge(code: str) -> str:
        sent.append(code)
        return 'printed'

    fake_bridge(monkeypatch, bridge)
    script = tmp_path / 'a.py'
    script.write_text('print(1)')

    def run() -> str:
        return (
            scripting.execute_designer_code('print(1)')
            if tool == 'execute_designer_code'
            else scripting.run_designer_script(str(script))
        )

    monkeypatch.setitem(server._session, 'scripting_read', False)
    with pytest.raises(ToolError) as refused:
        run()
    assert str(refused.value) == server.SCRIPTING_NOT_READ and not sent
    server.get_guide('scripting')
    assert run() == 'printed' and sent


def test_one_refusal_names_both_parts_when_neither_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    # one round trip, not one per part
    monkeypatch.setitem(server._session, 'guide_read', False)
    monkeypatch.setitem(server._session, 'scripting_read', False)
    with pytest.raises(ToolError) as refused:
        server.execute_designer_code('print(1)')
    assert server.GUIDE_NOT_READ in str(refused.value) and server.SCRIPTING_NOT_READ in str(refused.value)


def test_the_resource_serves_the_guide_file() -> None:
    assert server.agents_guide() == guide_md()


def test_guide_fits_in_one_tool_result() -> None:
    # Claude Code's default limit for one MCP tool result is 25,000 tokens; stay well below
    _, scripting = _parts()
    assert len(scripting) < 60000


def test_the_core_of_the_guide_stays_within_its_budget() -> None:
    # every Designer session reads the core whole (get_guide()) before any other tool works, so each character costs
    # all of them. The budget leaves room for about 30 lines of 200 characters (7,667 characters on 2026-11-24, after
    # ROADMAP item 126 trimmed it from 19,981; 7,885 with REVIEW.md INS-47's line)
    core, _ = _parts()
    assert len(core) <= GUIDE_CORE_BUDGET, (
        'The core of GUIDE.md is %d characters, over its budget of %d: move what an agent using only the tools '
        "doesn't need on its first try to where the table of `.claude/rules/docs.md` puts it"
        % (len(core), GUIDE_CORE_BUDGET)
    )


def _within(text: str, limit: int) -> bool:
    """Whether `text` takes at most `limit` bytes in UTF-8."""
    return len(text.encode('utf-8')) <= limit


def test_agents_md_stays_within_its_budget() -> None:
    # AGENTS.md is loaded whole into every session and every agent in this repo, so each byte costs all of them. The
    # budget leaves room for about ten rounds of 100 to 200 bytes (13,145 bytes on 2026-11-20); Claude Code itself warns
    # only from 40 KB
    text = agents_md()
    assert _within(text, AGENTS_MD_BUDGET), (
        'AGENTS.md is %d bytes, over its budget of %d: move what only some work needs to a rule or a skill'
        % (len(text.encode('utf-8')), AGENTS_MD_BUDGET)
    )


def test_the_docs_rule_points_to_the_budget_without_its_figure() -> None:
    # the user, 2026-11-20: the rule every doc change loads names the budget by its constant. The figure stays here
    # alone, as `.claude/rules/docs.md` keeps each fact in one place
    docs = flat(rule('docs.md'))
    assert (
        'AGENTS.md has a byte budget (`AGENTS_MD_BUDGET` in `tests/unit/test_guide.py`), so what only some work needs'
        ' goes in a rule or a skill.' in docs
    )
    figures = (
        f'{AGENTS_MD_BUDGET:,}',
        f'{AGENTS_MD_BUDGET:_}',
        str(AGENTS_MD_BUDGET),
        f'{AGENTS_MD_BUDGET // 1000} KB',
    )
    assert [figure for figure in figures if figure in docs] == []


def test_a_text_within_a_budget_has_at_most_its_bytes() -> None:
    assert _within('a' * 10, 10) and not _within('a' * 11, 10)
    assert not _within('é' * 5, 9), 'bytes, not characters'


def test_each_audience_has_its_own_file() -> None:
    core, scripting = _parts()
    assert headings(core) == set(GUIDE_SECTIONS)
    assert headings(scripting) == set(SCRIPTING_SECTIONS)
    assert headings(agents_md()) == set(AGENTS_SECTIONS)


def test_the_live_check_skill_is_one_claude_code_can_find() -> None:
    assert re.match(
        r"---\nname: live-check\ndescription: '(?:[^']|'')*alone\.run(?:[^']|'')*'\n---\n", skill('live-check')
    )


@pytest.mark.parametrize(
    'fact',
    [
        '`<category>/preparations.py`',
        '**The check lives in the suite:**',
        '**The order:**',
        "**What a scratch run can't prove**",
        '**When the final check fails,**',
        '**The suites.**',
        '<category>/designer_scripts/',
    ],
)
def test_the_procedure_of_live_checks_is_in_the_skill(fact: str) -> None:
    # REVIEW.md TST-219: flat, or a rewrap breaks the test, or hides a copy from the second half
    assert flat(fact) in flat(skill('live-check')) and flat(fact) not in flat(agents_md())


@pytest.mark.parametrize(
    'label',
    [
        '**Tests run at two stages**',
        '**The full suites run only when the user asks:**',
        '**Lint and types always run too**',
    ],
)
def test_agents_md_keeps_the_hard_rules(label: str) -> None:
    assert flat(label) in flat(agents_md()) and flat(label) not in flat(skill('live-check'))


@pytest.mark.parametrize(
    'said', ['**Load the `live-check` skill', "with `alone.run` from a script in the session's scratchpad"]
)
def test_the_rule_of_the_self_test_says_how_a_live_check_runs_even_if_the_skill_is_skipped(said: str) -> None:
    # ROADMAP item 110: moved out of AGENTS.md to the rule every file of the self-test loads, not to the skill, which
    # can't ask for itself
    assert flat(said) in flat(rule('live-checks.md'))
    assert flat(said) not in flat(agents_md()) and flat(said) not in flat(skill('live-check'))


DOC_GLOBS = ['**/*' + suffix for suffix in DOC_SUFFIXES]  # the files whose text is read as docs, comments included
# every rule in .claude/rules/: its `paths:`, and the skill it asks for, or None. Each holds text moved out of AGENTS.md
RULES: dict[str, tuple[list[str], str | None]] = {
    'changing-tools.md': (['mcp_server/server_tools/**/*', 'mcp_server/designer_helpers/**/*'], 'mcp-builder'),
    'live-checks.md': (['tests/test_all_tools/**/*'], 'live-check'),
    'python.md': (['**/*.py'], None),
    'docs.md': (DOC_GLOBS, None),  # where docs, docstrings and comments are written
    'docs-tests.md': (DOC_GLOBS, None),  # on a change of a comment or a docstring too
    'unit-tests.md': (['tests/unit/**/*'], None),
    'waits.md': (  # the code that waits on Designer, Qt or the OS: test_waits.py's folders, the scripts and the tests
        [
            'mcp_server/**/*.py',
            'plugin/**/*.py',
            'client/**/*.py',
            'examples/**/*.py',
            'tests/**/*.py',
            'scripts/**/*.py',
            'designer_preferences.py',
        ],
        None,
    ),
    'designer-code.md': (
        [
            'mcp_server/**/*',
            'plugin/**/*',
            'client/**/*',
            'project_constants.py',
            'designer_preferences.py',
            'tests/test_all_tools/common.py',  # its `raw_request` speaks the bridge protocol (REVIEW.md AGT-70)
        ],
        None,
    ),
    'install.md': (['install.py', 'uninstall.py', '.mcp.json'], None),
}


@pytest.mark.parametrize('rule_name', sorted(RULES))
def test_a_path_scoped_rule_parses_and_matches_files(rule_name: str) -> None:
    # Claude Code loads it for a matching file (AGENTS.md, Working on this project: Rules for some files only). A rule
    # it can't parse never loads, silently
    patterns = RULES[rule_name][0]
    assert _rule_paths(rule_name) == patterns
    for pattern in patterns:
        assert any(Path(ROOT).glob(pattern)), '%s matches no file' % pattern


@pytest.mark.parametrize('name', sorted(name for name, (_, skill_name) in RULES.items() if skill_name))
def test_a_path_scoped_rule_asks_for_the_skill(name: str) -> None:
    asked = RULES[name][1]
    assert asked and '`%s`' % asked in rule(name) and Path(ROOT, '.claude', 'skills', asked, 'SKILL.md').is_file()


def test_rules_names_every_rule_there_is_and_no_other() -> None:
    # a new rule fails here until RULES has it, and a rule RULES names that no file holds fails too
    assert sorted(RULES) == sorted(path.name for path in Path(ROOT, '.claude', 'rules').glob('*.md'))


@pytest.mark.parametrize('rule_name', sorted(RULES))
def test_a_rule_moved_out_of_agents_md_is_listed_there(rule_name: str) -> None:
    # ROADMAP item 110: PyCharm's read_file loads no rule (AGENTS.md, Working on this project: Rules for some files
    # only), so AGENTS.md lists each one for the agents to read. A rule asking for a skill holds text moved out of
    # AGENTS.md too, so it is listed as well
    listed = re.search(r'(?ms)^\*\*Rules for some files only\*\*.*?(?=^\*\*)', agents_md())
    assert listed and '`%s`' % rule_name in listed.group(0)


def test_the_delegate_skill_is_one_claude_code_can_find_and_agents_md_names_it() -> None:
    # ROADMAP item 110: what a brief holds, loaded before starting an agent. The test below reads its frontmatter, and
    # test_review_lookup.py checks every skill's description is valid YAML
    text = skill('delegate')
    assert '`.claude/skills/delegate/SKILL.md`' in agents_md()
    assert "**The brief is the agent's only context about the task.**" in text
    assert "only context about the task.** Don't paste" not in agents_md(), 'one home'


def test_monitors_events_count_as_output_of_unknown_size() -> None:
    # the user, 2026-11-20: "yes add it". Monitor's events land in the lead's context, so its command is filtered as a
    # read is capped. The rule holds it, not a hook (the user's choice), and the story points to it
    caps = flat(agents_md()).split('**Any other output of unknown size is capped in the call itself,**')[1]
    assert (
        "Monitor too: its events land in the lead's context, so the lead filters its command to the few lines it acts "
        'on. A log to read goes to the `analyst`, and waiting for an end is a background Bash that exits on it (the '
        '`delegate` skill, `.claude/skills/delegate/SKILL.md`, A long run).'
    ) in caps.split('**')[0]
    assert '**A long run**' in skill('delegate')
    assert "Monitor's events count too (AGENTS.md, Delegating to subagents)" in flat(story_md())


@pytest.mark.parametrize('trigger', ['before starting or resuming an agent', 'before continuing the loop from PLAN.md'])
def test_agents_md_and_the_delegate_skill_give_the_same_triggers(trigger: str) -> None:
    # REVIEW.md AGT-81: a round of fixes resumes the developer, and a session's start or a compaction continues the loop
    # from PLAN.md, whose stop list is in the skill alone. AGENTS.md says when to load the skill, and Claude Code
    # matches the skill's description
    description = re.match(r'---\nname: delegate\ndescription: (.*)\n---\n', skill('delegate'))
    assert description and trigger.lower() in description.group(1).lower()
    assert trigger.lower() in flat(agents_md()).lower()


# the forms a link to AGENTS.md took for what moved out of it to a rule or a skill, where the link names no section,
# names one AGENTS.md still has, or names the part in prose. Of the moved parts, only those named in lowercase are
# found in any prose form: the callbacks, navigating and checking, and the `mcp-builder` paragraph (REVIEW.md TST-611).
# The other forms are found as the links gave them (ROADMAP item 110; REVIEW.md AGT-66, AGT-72). A link naming a
# section AGENTS.md no longer has is test_every_pointer_names_a_section_its_file_has's
#
# where the pointer finder reads prose, in its own grammar (`doc_pointers.py`): a name in lowercase after a pointer to
# AGENTS.md, or after the name of a section and a part's separator. The finder reads a capitalised name as a section's,
# so this leaves it out. "AGENTS.md: " is no pointer to the finder, so this adds it
PROSE_AFTER_AGENTS_MD = r'AGENTS\.md`?(?:%s|:\s+)(?:[A-Z][^)]*?%s)?(?=[a-z])' % (AFTER_FILE, TO_PART)
MOVED_OUT = (
    r"AGENTS\.md(?:'s)?,?\s+(?:typing\s+(?:rules|paragraph)|mark(?:ed)?\b|registration\s+note)",
    r'(?:mark|platform\s+reason)\s+AGENTS\.md\s+asks\s+for',
    r'AGENTS\.md\s+(?:now\s+)?asks\s+for\s+the\s+most\s+specific\s+type',
    r'AGENTS\.md\s+command\b',
    r'AGENTS\.md:\s+a\s+fake',
    # the review rules, under a bold label AGENTS.md still has
    r"AGENTS\.md(?:'s)?[^)]{0,40}?\bReviews\s+go\s+in",
    # the wait rule, PyCharm's tools and the `mcp-builder` skill, named in prose within a few words, the link's
    # parentheses not closed between them
    PROSE_AFTER_AGENTS_MD + r'[^)]{0,40}?\b(?:callback|navigating\s+and\s+checking|the\s+`mcp-builder`\s+paragraph)',
    # the loop, named in prose
    r"AGENTS\.md\s+lists\*\*\s+\(The\s+loop\s+is\s+the\s+lead's",
    # the wait rule, and the skills' rules, named by the file's name alone
    r'(?:\btime|\bstate|_until\s+instead)\s+\(AGENTS\.md\)',
    r'wait\s+rule\s+in\s+AGENTS\.md',
    r'`(?:mcp-builder|live-check)`\s+skill(?:\s+first)?\s+\(AGENTS\.md\)',
    # PyCharm's tools, the routing table, the loop, the server's instructions, the hooks' rules, a hung quit's file
    r"PyCharm's\s+tools\s+first[^)]{0,60}\(AGENTS\.md",
    r'PyCharm\s+has\s+open\s+\(AGENTS\.md\)',
    r'brief\s+per\s+runner\s+\(AGENTS\.md',
    r'small\s+steps\s+\(AGENTS\.md\)',
    r'the\s+limit\s+is\s+in\s+\[AGENTS\.md\]',
    r'limits\s+and\s+the\s+rules\s+are\s+in\s+AGENTS\.md',
    r"quit's\s+result\s+names\s+\(AGENTS\.md",
    # how to document a finished item, and the size of a whole page a fetch returns (REVIEW.md AGT-82)
    r'as\s+AGENTS\.md\s+describes',
    r'whole\s+(?:#\s+)?page[^)]{0,60}?\(AGENTS\.md',
    # how the lead writes PLAN.md, and the merge, both moved from Working on this project to the `delegate` skill
    # (REVIEW.md TST-605). The final check before the merge stays AGENTS.md's (Running the tests)
    r'\blead\s+writes\s+PLAN\.md\b[^)]{0,80}?\(AGENTS\.md',
    r"(?:\bsquash|\bthe\s+merge\b|outlast\s+the\s+branch|branch's\s+last\s+commit)[^)]{0,60}?"
    r'\(AGENTS\.md(?=\)|,\s+Working\s+on\s+this\s+project)',
)
MOVED_OUT_LINK = re.compile('|'.join(MOVED_OUT))

# sentences pointing into AGENTS.md, `%s` standing for its name, each with what finds it: 'section' when it names a
# section AGENTS.md no longer has (the pointer finder), 'pattern' for the other stale forms (MOVED_OUT), None when it
# is correct
POINTERS_INTO_AGENTS_MD = [
    # the stale forms the move left (REVIEW.md AGT-66, AGT-72)
    ("one that stays takes %s's mark (typing)", 'pattern'),
    ("other than %s's marked `[explicit-any]`", 'pattern'),
    ("as %s's typing rules say", 'pattern'),
    ("%s's typing paragraph gives the mark and its line", 'pattern'),
    ('%s now asks for the most specific type', 'pattern'),
    ('with lint and types (the %s command).', 'pattern'),
    ("%s's registration note", 'pattern'),
    ('(%s, PyCharm)', 'section'),
    ('the platform reason %s asks for', 'pattern'),
    ("(%s: a fake standing in for a type it can't subclass)", 'pattern'),
    # the stale forms the moves of ROADMAP item 110's last step left
    ('(%s,\n  Keeping the docs current, says which fact goes where)', 'section'),
    ("as the table in %s's Keeping the docs current says", 'section'),
    ('as %s\'s "Keeping the docs current" table says', 'section'),
    ('(%s, Wait for callbacks)', 'section'),
    ('(%s: callbacks first, never a time measured here)', 'pattern'),
    ("%s's rule (callbacks, a poll every 100 ms, limits as safety nets)", 'pattern'),
    ('never a fixed time (%s). The', 'pattern'),
    ('a time measured here\n    # after a state (%s)', 'pattern'),
    ('goes through _until instead\n    (%s).', 'pattern'),
    ('the wait rule in %s, added after it', 'pattern'),
    ('(%s, Simplify the change before reviewing it)', 'section'),
    ('(%s, Working on this project: navigating and checking code)', 'pattern'),
    ('in its\n> %s (the `mcp-builder` paragraph)', 'pattern'),
    ('load the `mcp-builder` skill (%s).', 'pattern'),
    ('Load the `mcp-builder`\nskill first (%s).', 'pattern'),
    ('load the `live-check` skill (%s).', 'pattern'),
    ("(%s, The loop is the lead's)", 'section'),
    ("only for what %s lists** (The loop is the lead's)", 'pattern'),
    ('(%s, An agent that stops to ask)', 'section'),
    ('%s, Delegating to subagents (A long run): the developer', 'section'),
    ('%s (Delegating to subagents, A long\nrun)', 'section'),
    ('(%s, Deploying and diagnosing: How changes reach the\nagents)', 'section'),
    ("PyCharm's tools first, then `grep` when they don't help (%s, Working on this\n  project)", 'pattern'),
    ('the limit is in [%s](%s), Working on this project', 'pattern'),
    ('The limits and the rules are in %s, Delegating to subagents.', 'pattern'),
    ("the sample file the quit's result names\n  (%s, Deploying and diagnosing)", 'pattern'),
    ('# %s: a state no callback says is looked at every 100 ms', 'pattern'),
    ('the project PyCharm has open\n    (%s).', 'pattern'),
    ('gathered in one brief per runner (%s, Delegating to\n  subagents)', 'pattern'),
    ("after a step of the lead's loop, or a group of small steps (%s), or when", 'pattern'),
    ('and document the result as %s describes; checked', 'pattern'),
    ('a fetch may return a whole page, up to 100,000 characters, into your context (%s, Delegating', 'pattern'),
    ('as a fetch may return a whole\n    # page into the context (%s, Delegating to subagents)', 'pattern'),
    # the stale forms of PLAN.md's writing and the merge (REVIEW.md TST-605), the story's old line first
    ('The lead writes PLAN.md: the work in steps, each in full detail (%s, Working on this project).', 'pattern'),
    ("The merge into `main` is a squash, on the user's word (%s, Working on this project)", 'pattern'),
    ('what must outlast the branch is in DECISIONS.md or ROADMAP.md before the merge (%s)', 'pattern'),
    ("the lead deletes PLAN.md in the branch's last commit (%s, Working on this project)", 'pattern'),
    ('(%s, The merge)', 'section'),
    # the review rules, moved to the review skills from under a bold label still there
    ('each entry as in (%s, Reviews go in REVIEW.md)', 'pattern'),
    # a moved part named in lowercase, which the pointer finder reads as prose (REVIEW.md TST-611)
    ('(%s, callbacks first)', 'pattern'),
    ('(%s, Working on this project: wait for callbacks)', 'pattern'),
    ('(%s, Working on this project: the `mcp-builder` paragraph)', 'pattern'),
    # correct sentences both tests must leave alone
    ('%s marks the rule as the lead decided', None),
    ('%s commands no agent to commit', None),
    ('%s asks for a test with every change', None),
    ('%s, Running the tests', None),
    ('(%s, Start with the tests)', None),
    ('the `analyst` agent (%s, Delegating to subagents).', None),
    ('%s, Working on this project (Rules for some files only), lists them', None),
    ('the limits %s states (Delegating to subagents)', None),
    ('(%s, Deploying and diagnosing, points here)', None),
    ('the lead commits (%s), with `REVIEW.md` in the same commit', None),
    ('the final check before the squash merge (%s, Running the tests), when the brief asks', None),
    ('the final check (%s, Running the tests) and then the squash merge', None),
    ('A subagent never writes PLAN.md (%s, Working on this project)', None),
    ('Push, or merge into `main`, only when the user asks (%s)', None),
]


@pytest.mark.parametrize('sentence, found_by', POINTERS_INTO_AGENTS_MD)
def test_the_moved_out_patterns_find_the_stale_forms_only(sentence: str, found_by: str | None) -> None:
    # the file's name is filled in here, so that this file holds no stale link for the test below to find
    assert bool(MOVED_OUT_LINK.search(sentence.replace('%s', 'AGENTS.md'))) == (found_by == 'pattern')


def _stale_links(link: re.Pattern[str]) -> list[str]:
    """Each match of `link` in `repo_texts`, as `<file>: <match>`."""
    return ['%s: %s' % (name, m.group(0)) for name, text in repo_texts() for m in link.finditer(text)]


def test_no_link_points_to_agents_md_for_what_moved_to_a_rule() -> None:
    stale = _stale_links(MOVED_OUT_LINK)
    assert not stale, stale


@pytest.mark.parametrize(
    'file, sentence, dangles',
    [('AGENTS.md', sentence, found_by == 'section') for sentence, found_by in POINTERS_INTO_AGENTS_MD]
    + [
        # the forms of a name the finder reads: quoted, possessive, in backticks, after a comment's or a quote's marker
        # on each line, shortened, followed by prose or by a part of the section
        ('AGENTS.md', '%s ("Start with the tests, always (TDD)"); this is the procedure', False),
        ('AGENTS.md', '%s\'s "Keep it yourself": the lead', False),
        ('AGENTS.md', "%s's (Running the tests)", False),
        ('AGENTS.md', '`%s`, Running the tests. The commands', False),
        ('AGENTS.md', '# point to %s, Running the tests\n    says = re.compile(r"final")', False),
        ('AGENTS.md', '# (%s, Working on this\n# project: Rules for some files only)', False),
        ('AGENTS.md', '%s, Running the tests and the `live-check` skill', False),
        ('AGENTS.md', '(%s, Working on this project and Running the tests, point here)', False),
        ('AGENTS.md', '(%s, Working on this project and Running the test suites, point here)', True),
        ('AGENTS.md', '%s\'s "a claim without a test is a guess" applies', False),
        ('AGENTS.md', '(%s, README.md)', False),
        ('AGENTS.md', '%s, Running the test suites', True),
        ('AGENTS.md', '# (%s, Keeping the\n# docs current)', True),
        ('AGENTS.md', '> (%s, Keeping the\n> docs current)', True),
        ('AGENTS.md', '%s (Working on this project, Rules for all files)', True),
        ('DECISIONS.md', '(%s, Project rules; ROADMAP item 105)', False),
        ('DECISIONS.md', '(%s, No agent has a write guard)', False),
        ('DECISIONS.md', '(%s, Output...), so ask first', False),
        ('DECISIONS.md', '%s, "No job starts sooner than 30 ms after the one before ended"; the wait rule', False),
        ('DECISIONS.md', '(%s, the 3D screenshot entry)', False),
        ('DECISIONS.md', '(%s, Projects rules)', True),
        ('DECISIONS.md', '%s, "No job starts sooner than 20 ms"', True),
    ],
)
def test_the_pointer_finder_finds_a_name_its_file_lacks(file: str, sentence: str, dangles: bool) -> None:
    # the file's name is filled in here, so that this file holds no dangling pointer for the test below to find. Of the
    # stale forms, it finds those naming a section AGENTS.md no longer has. Those naming a section AGENTS.md still has,
    # with the content moved out, are MOVED_OUT's, as are those naming no section and those naming the part in prose,
    # as far as MOVED_OUT's comment says
    found = dangling_pointers(sentence.replace('%s', file), file, labels(read(file)))
    assert bool(found) == dangles, found


@pytest.mark.parametrize('file', ['AGENTS.md', 'DECISIONS.md'])
def test_every_pointer_names_a_section_its_file_has(file: str) -> None:
    # a pointer names the section by a heading or a bold label of the file (`doc_pointers.py`). Pointers into the
    # skills, the rules, README.md and GUIDE.md aren't read: they name a step or a point of a list as well
    known = labels(read(file))
    dangling = [
        '%s: %s' % (name, found) for name, text in repo_texts() for found in dangling_pointers(text, file, known)
    ]
    assert not dangling, dangling


def _cells(row: str) -> int:
    """The cells of a row of a Markdown table that opens and closes with `|`: every `|` between them ends a cell, one
    in code too, but not one after a backslash (GitHub's tables, GFM)."""
    return row.replace('\\|', '').count('|') - 1


def test_no_doc_writes_a_placeholder_github_drops() -> None:
    # REVIEW.md TST-639: GitHub drops a tag it doesn't know, such as a bare `<date>` or `<who>`, so a placeholder of a
    # tag's form goes in backticks. README's collapsible section is HTML on purpose
    kept = ('<details>', '<summary>')
    found = ['%s: %s' % (name, tag) for name, text in repo_docs() for tag in bare_tags(text) if tag not in kept]
    assert not found, found


def test_every_row_of_a_docs_table_has_as_many_cells_as_its_header() -> None:
    # REVIEW.md TST-613, TST-615: ROADMAP item 111's row had 4 cells in a table of 6, and GitHub showed its steps under
    # Why and left the next cells empty. Every doc's tables are read, an indented one too, but not a fenced example.
    # REVIEW.md is no doc of `repo_docs`, but its tables before the review log are the lead's to write: the status
    # table, and the table by model, which gets the figures of each review
    review = read('REVIEW.md').split('\n## Review log\n')[0]
    wrong = []
    for name, text in (*repo_docs(), ('REVIEW.md', review)):
        header = 0
        for line in without_code(text).splitlines():
            row = line.strip()
            if not row.startswith('|'):
                header = 0  # the table ended
            elif not header:
                header = _cells(row)
            elif _cells(row) != header:
                wrong.append('%s: %d of %d cells: %s' % (name, _cells(row), header, row[:80]))
    assert not wrong, wrong


@functools.cache
def _repo_paths() -> frozenset[str]:
    """The files `repo_files` lists that are on disk, and their folders, with `/` between folders. The repository's
    own folder is `.`."""
    files = [Path(name).as_posix() for name in repo_files() if Path(ROOT, name).is_file()]
    return frozenset(files) | {str(folder) for name in files for folder in PurePosixPath(name).parents}


def _dead_links(name: str, text: str) -> list[str]:
    """The relative links of the Markdown `text`, the file `name`'s, that lead to no file or folder of the repository.
    A link resolves from its file's folder, and its target must be one of `_repo_paths`, in the same case, as on GitHub.
    Code is left out: `defaultdict[str, Any](int)` is no link."""
    folder = Path(name).parent.as_posix()
    targets: list[str] = re.findall(r'\]\(([^)\s:#]+)(?:#[^)]*)?\)', re.sub(r'(?ms)^```.*?^```|`[^`\n]*`', '', text))
    return [target for target in targets if posixpath.normpath(posixpath.join(folder, target)) not in _repo_paths()]


@pytest.mark.parametrize(
    'target, dead',
    [
        ('../ROADMAP.md', False),
        ('../.claude/rules/', False),
        ('..', False),
        # REVIEW.md TST-607: dead on GitHub, though `Path.exists` finds each here (the wrong case on a case-insensitive
        # volume)
        ('../roadmap.md', True),
        ('../mcp_server/venv', True),  # a folder git ignores
        ('../../%s/ROADMAP.md' % Path(ROOT).name, True),  # this file, by a path out of the repository
    ],
)
def test_a_link_leads_to_a_file_only_as_on_github(target: str, dead: bool) -> None:
    assert _dead_links('docs/agent-workflow.md', '[the link](%s)' % target) == ([target] if dead else [])


def test_every_relative_link_in_the_docs_leads_to_a_file() -> None:
    # REVIEW.md AGT-82: docs.md's `[ROADMAP.md](ROADMAP.md)`, moved from the root to `.claude/rules/`, led nowhere
    dead = ['%s: %s' % (name, target) for name, text in repo_docs() for target in _dead_links(name, text)]
    assert not dead, dead


# each home of a part moved out of AGENTS.md, with a phrase of each part it holds
MOVED_HOMES = {
    '.claude/rules/python.md': (
        "which `search_symbol` doesn't give",
        '**Simplify the change before reviewing it.**',
        '**Keep each file to its main logic.**',
    ),
    '.claude/rules/waits.md': ('**Wait for callbacks, never for measured times.**',),
    '.claude/rules/docs.md': ('| Kind of knowledge | Where it goes |', '**Subject and verb first.**'),
    '.claude/rules/changing-tools.md': ("Its defaults this project doesn't follow",),
    '.claude/rules/designer-code.md': (
        'must stay under 4,096 characters',
        "A port change must reach the plugin (Designer's environment) and the server alike.",
    ),
    '.claude/rules/live-checks.md': ('**Live checks while working: a scratch run.**',),
    '.claude/skills/project-code-review/SKILL.md': ('Each finding is one entry starting with a checkbox',),
    '.claude/skills/delegate/SKILL.md': (
        '| Agent | What to give it |',
        "**The loop is the lead's**",
        '**The `analyst` and the `reviewer` only read, by their instructions:**',
        '**An agent that stops to ask**',
        '**A long run**',
        '**Pass `model` on an Agent call only when the user asks for another model for that run**',
        '**What comes back is evidence, not a verdict:**',
        '**How changes reach the agents**',
        # REVIEW.md AGT-87: what only the lead needs, at a branch's start and end
        "If it isn't, research the branch's work first, with analysts",
        '**The merge** into `main` is a squash',
    ),
    '.claude/skills/live-check/SKILL.md': ('**When a Designer crashed or hung:**',),
}


@pytest.mark.parametrize('part, home', [(part, home) for home, parts in MOVED_HOMES.items() for part in parts])
def test_a_part_moved_out_of_agents_md_has_one_home(part: str, home: str) -> None:
    # ROADMAP item 110: each part only some work needs is where that work loads it, and AGENTS.md keeps a pointer.
    # Every doc counts, so a copy in a second rule, skill or agent file fails too (REVIEW.md TST-604). The story is left
    # out: it retells the setup by design (`.claude/rules/docs.md`, Keeping the docs current)
    wanted = flat(part)
    found = {name for name, text in repo_docs() if name != 'docs/agent-workflow.md' and wanted in flat(text)}
    assert found == {home}


# where a doc names AGENTS.md as an authority, or as the home of a kind of fact, it names the rules and skills that hold
# what moved out of AGENTS.md too (REVIEW.md AGT-83, AGT-84)
BESIDE_AGENTS_MD = {
    '.claude/rules/python.md': ('goes against AGENTS.md, a rule or skill it points to, or DECISIONS.md',),
    '.claude/agents/developer.md': (
        'AGENTS.md and the rules and skills it points to are your authority',
        'the sibling, AGENTS.md, a rule or skill AGENTS.md points to, GUIDE.md or DECISIONS.md settles it',
    ),
    '.claude/agents/reviewer.md': ('an AGENTS.md section, a rule or skill AGENTS.md points to, a GUIDE.md rule',),
    '.claude/skills/address-review/SKILL.md': (
        'a sentence of AGENTS.md, a rule or skill AGENTS.md points to, GUIDE.md or README.md that the fix made untrue',
        "A choice that AGENTS.md, a rule or skill AGENTS.md points to, or the code's comments already answer",
    ),
    '.claude/rules/docs.md': (
        '**AGENTS.md**, Deploying and diagnosing, or the rule or skill it points to for that work',
    ),
    # what wins over the `mcp-builder` skill, and what waits for the user's word (REVIEW.md AGT-90)
    '.claude/rules/changing-tools.md': (
        'Where it differs from AGENTS.md, a rule or skill AGENTS.md points to, or this file',
    ),
    'AGENTS.md': ("Where this file, or a rule or skill it points to, waits for the user's word",),
}


@pytest.mark.parametrize('path, said', [(path, said) for path, says in BESIDE_AGENTS_MD.items() for said in says])
def test_a_doc_naming_agents_md_as_an_authority_names_its_rules_and_skills_too(path: str, said: str) -> None:
    assert said in flat(read(path))


def test_one_doc_says_when_a_rule_loads() -> None:
    # REVIEW.md AGT-67, AGT-71: a Read, a Write, and a Bash `sed -n` or `grep` printing the file unpiped each load a
    # matching rule; a `wc -c`, a piped command and PyCharm's read_file don't (measured 2026-11-19). A `cat`, a `head`
    # and a `tail` do too, their output saved to a file past the cap included (measured 2026-11-20). After a compaction
    # the next such read loads it again (seen 2026-11-20). AGENTS.md says so once, and the other docs point there
    # instead of giving a trigger of their own, but the story, which retells it by design
    commands = '`cat`, `head`, `tail`, `sed -n` or `grep` prints its lines unpiped'
    rules = flat(agents_md()).split('**Rules for some files only**')[1].split('- `python.md`')[0]
    assert (
        "once per agent and again after a compaction, when a Read or a Write touches a file the rule's `paths:` match,"
        ' or a Bash ' + commands in rules
    )
    assert (
        "A `wc -c`, a piped command and PyCharm's `read_file` load none (measured 2026-11-19 and 2026-11-20; the"
        ' compaction, 2026-11-20)' in rules
    )
    assert 'or a shell ' + commands in flat(story_md())
    stale = _stale_links(re.compile(r'Read\s+(?:or\s+Write\s+)?opens|read\s+or\s+edited|Bash\s+read\b'))
    assert not stale, stale


def test_the_mcp_builder_description_covers_changing_a_tool_here() -> None:
    text = skill('mcp-builder')
    found = re.search(r'(?m)^description: (.*)$', text)
    assert found, 'a description line'
    assert 'before adding, merging or removing a tool or changing its parameters' in found.group(1)
    assert ': ' not in found.group(1), 'would end the plain YAML value and break the frontmatter'


def test_agents_md_asks_for_the_rules_before_touching_the_bridge() -> None:
    # REVIEW.md TST-204: they were loaded automatically before the split
    assert 'before touching the bridge, the token or the plugin, or running anything against Designer' in flat(
        agents_md()
    )


def test_a_tools_only_agent_is_told_the_units() -> None:
    # REVIEW.md TST-205: the core is all it reads, and pixels passed as log2 were taken silently
    core, scripting = map(flat, _parts())
    assert '`$outputsize` is log2' in core and 'node **centres**' in core
    assert '**Graph size** is log2' not in scripting and 'node **centres**' not in scripting, 'one place'
    ops = flat(_described('apply_edits', 'ops'))
    assert 'log2' in ops and 'centre' in ops


def test_the_core_names_the_tool_that_gives_the_slider_range_it_asks_for() -> None:
    # REVIEW.md TST-827: the core asks for values inside the slider range, so it says which tool gives one
    tools = flat(section(_parts()[0], '## Which tool for what'))
    assert 'pick values inside the slider range' in tools
    assert re.search(r'`describe_node` for [^.]*slider ranges', tools), tools


def test_apply_edits_says_which_of_two_gradient_keys_at_one_position_shows() -> None:
    # REVIEW.md SRV-245: an agent setting a hard edge with apply_edits reads its ops, not the scripting part. The
    # `params` check of keys measures it at the default interpmode alone (tests/test_all_tools/params/checks.py), so
    # the sentence names that mode, and so does the one on a colour input, measured there too (REVIEW.md SRV-246)
    ops = flat(_described('apply_edits', 'ops'))
    assert 'At interpmode 0, of two keys at one position, the first listed shows.' in ops
    assert 'At interpmode 0, a colour input gave every pixel the colour of the key at position 0' in ops
    assert 'first listed' not in flat(_parts()[1]), 'one place'


def test_the_core_routes_a_misbehaving_bridge_to_the_log() -> None:
    # REVIEW.md TST-835: no error message points to the log, and an agent reads read_designer_log's docstring only once
    # it has picked the tool
    assert '**Diagnose:** `read_designer_log`' in flat(section(_parts()[0], '## Which tool for what'))


def test_export_outputs_says_which_map_was_measured_against_the_cooked_render() -> None:
    # REVIEW.md SRV-247: the `render` check compares the height map alone (tests/test_all_tools/render/checks.py), and
    # renders of an AO map differ far more (ROADMAP item 17)
    _, tools = _tools()
    said = flat(tools['export_outputs'])
    assert 'An exported height map was within a few 1/65535 steps of the cooked render' in said
    assert 'Its textures are within' not in said


def test_the_default_of_grayscale_conversion_advanced_is_given_once() -> None:
    # REVIEW.md SRV-248: the scripting part's list of the measured greys holds it (the `bitmaps` check of greys)
    _, tools = _tools()
    said = flat(tools['analyze_reference'])
    assert '(not Grayscale Conversion Advanced)' in said and 'Desaturation' not in said
    assert 'Its default is Desaturation.' in flat(section(_parts()[1], '## sd API gotchas'))


def test_designer_status_says_the_library_packages_the_tools_loaded_are_listed() -> None:
    # REVIEW.md SRV-249: describe_node and apply_edits' add load them as user packages, and they stay loaded
    _, tools = _tools()
    assert "library packages the tools loaded, their file in Designer's packages folder" in flat(
        tools['designer_status']
    )


def test_the_core_says_when_outputsize_is_an_offset() -> None:
    # REVIEW.md TST-213: `expose` of a value read as log2 computed 8192 px on a 512 px graph
    core, scripting = map(flat, _parts())
    assert 'while inherited it is a log2 offset, and so is a graph input bound to it' in core  # REVIEW.md HLP-90
    # REVIEW.md TST-221: a Pixel Processor computed the graph's 2048 px from a 512 px input
    assert (
        'Generators inherit the graph size; filters inherit from their input, a Pixel Processor from the graph' in core
    )
    assert 'is a log2 offset' not in scripting and 'Generators inherit' not in scripting, 'one place'


def test_the_core_names_the_tools_that_refuse_too_large_a_size() -> None:
    # REVIEW.md HLP-84
    assert '`apply_edits`, `sweep_param`, `create_graph` and `set_graph_size` refuse more' in flat(_parts()[0])


@pytest.mark.parametrize('tool', ['create_graph', 'set_graph_size'])
def test_the_size_tools_state_the_largest_size(tool: str) -> None:
    # REVIEW.md HLP-84
    assert '13 is 8192 px, the largest' in flat(_described(tool, 'size_log2'))


def test_the_hot_reload_rule_is_among_the_rules() -> None:
    # REVIEW.md TST-212: AGENTS.md sends whoever touches the plugin to the guide's rules
    core = _parts()[0]
    assert 'Never hot-reload' in section(core, "## Rules that protect the user's work")
    assert core.count('Never hot-reload') == 1


def test_the_core_gives_the_rules_the_servers_instructions_promise() -> None:
    # REVIEW.md TST-830: every session reads them there, so a cut of the core for its budget keeps each one
    assert "the rules that protect the user's work (Undo, the bridge token, quitting Designer, snapshots)" in flat(
        server.INSTRUCTIONS
    )
    rules = flat(section(_parts()[0], "## Rules that protect the user's work"))
    for promised in (
        '**Never print, log or send the bridge token**',
        '**Undo your own work with `undo_edits`, and only with it.**',
        '**A Designer the user opened is theirs: never close it.**',
        'A Designer an agent started is disposable: `quit_designer` ends it.',
        '**`snapshot_graph` before risky or large edits**',
    ):
        assert promised in rules, promised


# The rule the user approved, word for word (2026-11-25: "all agnets will use it exclusively for undoing work")
UNDO_RULE = (
    '**Undo your own work with `undo_edits`, and only with it.** It takes back your calls, newest first. If steps that '
    "aren't yours sit on top of them (the user's, or another session's), it stops and names them: ask the user whether "
    'those may be undone too, and if they agree, call it again with `include_others`. With no such steps on top, undo '
    'as you need.'
)
CODE_TOOLS_UNDO = "To undo, use `undo_edits`; don't trigger Undo in your code."  # the code tools' line of the rule


# The user's rule on Redo, word for word in GUIDE.md's scripting part
REDO_RULE = (
    'Redo you may trigger from code when you need it, for example to bring back steps `undo_edits` undid (the user, '
    '2026-11-25: "an agent can trigger redo from code as well if it needs it").'
)


def test_the_scripting_part_says_redo_may_be_triggered_from_code() -> None:
    assert REDO_RULE in flat(section(_parts()[1], '## Designer UI (Qt)'))


def test_the_rules_say_to_undo_with_undo_edits_only() -> None:
    assert UNDO_RULE in flat(section(_parts()[0], "## Rules that protect the user's work"))


def test_every_agent_is_told_to_undo_with_undo_edits_in_four_places() -> None:
    # the guide's core, the server's instructions, undo_edits' description and the code tools' descriptions
    _, tools = _tools()
    assert UNDO_RULE in flat(_parts()[0])
    assert 'Undo your own work with undo_edits, and only with it.' in server.INSTRUCTIONS
    assert UNDO_RULE.replace('**', '').replace('`', '') in flat(tools['undo_edits']).replace('`', '')
    for tool in ('execute_designer_code', 'run_designer_script'):
        assert CODE_TOOLS_UNDO in flat(tools[tool]), tool


def test_no_rule_steers_an_agent_from_undo_edits() -> None:
    # REVIEW.md TST-881: the snapshot rule said "Prefer this over Undo", two bullets below the rule to undo with
    # undo_edits; a snapshot reverts nothing
    assert 'Prefer this over Undo' not in flat(guide_md())


@pytest.mark.parametrize('path', ['README.md', 'mcp_server/GUIDE.md', 'ROADMAP.md'])
def test_the_one_undo_history_is_said_shared_by_every_package(path: str) -> None:
    # REVIEW.md TST-883: "one undo history for every package" read as one per package; Designer keeps one for the app
    text = flat(read(path)).lower()
    assert 'one undo history for every' not in text, path


def test_no_part_of_the_guide_describes_triggering_undo_another_way() -> None:
    # GUIDE.md's scripting part had a recipe (Edit > Undo's action, triggered from a timer): an Undo so triggered took
    # the step on top as it landed, not the one checked before (REVIEW.md TST-873)
    guide = flat(guide_md())
    ways = (
        'Edit > Undo',
        '.trigger',
        'singleShot',
        'undo()',
        'invokeMethod',
        'Ctrl+Z',
        'HistoryActionsMgr',
        'undo-button',
    )
    for way in ways:
        assert way not in guide, way


def test_the_scripting_part_says_where_library_graphs_are_and_how_loaded_ones_count() -> None:
    # REVIEW.md TST-828: some of Designer's library packages are in subfolders of `packages`, and a loaded one is among
    # the user packages, as the API has no flag for it (`_is_library_package`, designer_helpers/core.py)
    gotchas = flat(section(_parts()[1], '## sd API gotchas'))
    assert '`app.getPath(SDApplicationPath.DefaultResourcesDir)/packages` and its subfolders' in gotchas
    assert 'A loaded library package is among `getUserPackages()` too' in gotchas


def test_the_core_names_the_seed_and_the_values_of_matching_tile_masks() -> None:
    # REVIEW.md TST-832: the seed and the per-tile values the line means, as the example's planks use them
    # (examples/build_dwarf_trimsheet.py, plank_layout)
    facts = flat(section(_parts()[0], '## Library node facts (Designer 16)'))
    assert (
        'The same layout and `Offset_Random_Seed` twice give a matching per-tile random mask, with '
        '`Luminance_Variation-Contrast` on the second.' in facts
    )


def test_the_file_level_pattern_comes_with_the_inheritance_numbers() -> None:
    # REVIEW.md TST-203: the API's numbers and the file's differ
    core, scripting = map(flat, _parts())
    assert 'RelativeToInput 0' in scripting and 'A .sbs `<relativeTo>`: 0 absolute' in scripting
    assert 'RelativeToInput 0' not in core
    # REVIEW.md TST-215: with the pattern, not among the Qt notes
    assert 'RelativeToInput 0' in section(_parts()[1], '## sd API gotchas')
    # REVIEW.md TST-222: an instance with no input isn't relative to input by default
    assert 'relative to input on a blur, relative to parent on an instance with no input' in scripting


def test_a_tools_only_agent_is_told_where_the_crash_dumps_are() -> None:
    # REVIEW.md TST-226
    core, scripting = map(flat, _parts())
    assert 'Sentry-Crashpad/completed' in core and 'Sentry-Crashpad/completed' not in scripting


def test_apply_edits_says_what_it_refuses_for_a_size() -> None:
    # REVIEW.md HLP-87
    assert 'above 13 or below 0 is refused' in flat(_described('apply_edits', 'ops'))


def test_the_skill_doesnt_call_a_guide_only_fix_code() -> None:
    # REVIEW.md TST-223: docs changed alone need no live run (`.claude/rules/docs-tests.md`)
    assert '`mcp_server/` (not GUIDE.md alone, which is docs: `.claude/rules/docs-tests.md`)' in flat(
        skill('live-check')
    )


def test_the_texts_say_which_part_of_the_guide_a_call_returns() -> None:
    # REVIEW.md SRV-101
    text = flat(server.INSTRUCTIONS)
    assert 'core of the guide' in text and 'first sd pitfalls' in text and 'full guide' not in text
    assert 'every tool but cancel_designer_job' in flat(server.get_guide.__doc__ or '')
    assert 'until then those two refuse' in flat(guide_md())
    assert "`get_guide('scripting')`" in agents_md()[:600]
    readme = flat(read('README.md'))
    assert 'the server sends it to the agent automatically' not in readme
    assert 'the server serves the guide to the agent' in readme


@pytest.mark.parametrize(
    'said',
    [
        # the typing rules (REVIEW.md TST-206)
        'never only under `if TYPE_CHECKING:`',
        'from __future__ import annotations',
        # the server's modules and every unit test, not only live checks (REVIEW.md TST-216)
        'A string of several lines is written `dedent',
        'Tests that read source text match whitespace-tolerantly',
        # the commands after a change: the live-check skill has the suites' commands, not these
        'tests/unit/test_lint.py tests/unit/test_types.py',
        'ruff check --fix .',
    ],
)
def test_the_rules_for_all_python_are_where_every_python_change_sees_them(said: str) -> None:
    # ROADMAP item 110 and REVIEW.md TST-592: in the rule every Python file loads (RULES), and in neither AGENTS.md nor
    # any skill
    assert said in flat(rule('python.md'))
    skills = Path(ROOT, '.claude', 'skills').glob('*/SKILL.md')
    texts = {'AGENTS.md': agents_md(), **{path.parent.name: skill(path.parent.name) for path in skills}}
    assert sorted(name for name, text in texts.items() if said in flat(text)) == []


def test_where_the_final_check_is_given_so_is_its_form_for_docs_alone() -> None:
    # REVIEW.md TST-590: docs changed alone run only the docs tests, the final check included
    final = flat(agents_md()).split('The final check is both suites in full')[1].split('**')[0]
    suites = flat(skill('live-check')).split('- **Both suites**')[1].split('- **')[0]
    for text in (final, suites):
        assert '`.claude/rules/docs-tests.md`' in text, text


def test_the_docs_tests_run_on_a_change_of_a_comment_or_a_docstring_too() -> None:
    # the user, 2026-11-20, on the docs tests, which check comments and docstrings too (DOC_SUFFIXES): "widen the
    # trigger to include comment and docstring changes". The rule loads for those files (RULES), and a paragraph that
    # says they run on a change of Markdown names comments and docstrings too
    said = (
        'They run too on a change of a comment or a docstring in a `.py`, `.ini` or `.toml` file, which they also check'
    )
    assert said in flat(rule('docs-tests.md'))
    names = re.compile(r'docs[\s-]tests\b')
    stale = [
        '%s: %s' % (name, paragraph[:100])
        for name, text in repo_texts()
        if names.search(text)
        for paragraph in map(flat, _paragraphs(text))
        if names.search(paragraph) and 'Markdown' in paragraph and 'a comment or a docstring' not in paragraph
    ]
    assert not stale, stale


def test_no_paragraph_says_what_the_final_check_runs_without_its_form_for_docs_alone() -> None:
    # REVIEW.md TST-597: the review skill's step 7 and live-check's `--only` bullet gave both suites in full, or a full
    # run, as what the final check runs, out of reach of TST-590's clause. A paragraph that says so gives the
    # docs-alone form too; the others name the final check and point to AGENTS.md, Running the tests
    says = re.compile(r'final\s+check\b[^.]*?(?:both\s+suites\s+in\s+full|stays\s+a\s+full\s+run)')
    stale = [
        '%s: %s' % (name, found.group(0))
        for name, text in repo_texts()
        if says.search(text)
        for paragraph in _paragraphs(text)
        for found in says.finditer(paragraph)
        if '`.claude/rules/docs-tests.md`' not in paragraph
    ]
    assert not stale, stale


def test_docs_changed_alone_means_markdown_files_only() -> None:
    # the user, 2026-11-20: "Markdown only". A change of a comment or a docstring, even alone, is a change of code: the
    # final check runs both full suites for it, and after a failed final check, a fix of only a comment in the code the
    # live self-test reaches runs that suite again. A paragraph that names docs (changed) alone says Markdown, or
    # points to the rule
    said = flat(rule('docs-tests.md'))
    assert 'Docs changed alone means a change of Markdown files only (the user, 2026-11-20)' in said
    assert 'A change of a comment or a docstring, even with nothing else changed, is a change of code' in said
    assert 'touch code it reaches, a comment or a docstring included' in flat(skill('live-check'))
    alone = re.compile(r'\bdocs?\s+(?:changed\s+)?alone\b', re.IGNORECASE)
    stale = [
        '%s: %s' % (name, paragraph[:100])
        for name, text in repo_texts()
        if alone.search(text)
        for paragraph in map(flat, _paragraphs(text))
        if alone.search(paragraph) and 'Markdown' not in paragraph and '`.claude/rules/docs-tests.md`' not in paragraph
    ]
    assert not stale, stale


def test_the_wait_rule_names_its_exceptions() -> None:
    # the user, 2026-11-20: three fixed waits stay, as the exceptions the rule names. The 30 ms between two jobs
    # (WAKE_DELAY_MS, the plugin), by its DECISIONS.md entry's title, which
    # test_every_pointer_names_a_section_its_file_has finds. The 300 ms before an older plugin's quit closes Designer's
    # windows, where no reply callback exists (REVIEW.md SRV-151). The settles of the self-test's window-state facts,
    # which time macOS's covered state on purpose (REVIEW.md TST-412). test_waits.py's STAYS lists the waits themselves
    waits = flat(rule('waits.md'))
    for said in (
        '**The exceptions the user chose** (the user, 2026-11-20):',
        'the 30 ms between two jobs, `WAKE_DELAY_MS` in the plugin',
        'DECISIONS.md, "No job starts sooner than 30 ms after the one before ended"',
        "the 300 ms before an older plugin's quit closes Designer's windows",
        '(`mcp_server/designer_helpers/quit.py`; REVIEW.md SRV-151)',
        "the 0.5 s and 1 s the self-test's click and window-under facts wait after a window is shown or its look is set",
        '(`tests/test_all_tools/editor_panels_and_fit/window_states.py`; REVIEW.md TST-412)',
    ):
        assert said in waits, said


def _paragraphs(text: str) -> list[str]:
    """The paragraphs of `text`, each item of a list one of its own."""
    return re.split(r'\n\s*\n|\n(?=\s*(?:-|\d+\.)\s)', text)


def test_the_live_check_skill_says_once_how_the_pool_runs() -> None:
    # REVIEW.md TST-591: an edit to one copy would leave the other stale
    assert flat(skill('live-check')).count('a Designer of its own, several at once') == 1


@pytest.mark.parametrize('doc', ['AGENTS.md', 'DECISIONS.md'])
def test_agents_md_and_decisions_md_name_each_skill_with_its_path(doc: str) -> None:
    # REVIEW.md AGT-65: an agent without the Skill tool, such as a reviewer or an analyst, Reads the file instead.
    # Reviewers read DECISIONS.md first (the user, 2026-11-20)
    text = read(doc)
    named: set[str] = set(re.findall(r'the `([\w-]+)` skill', text))
    assert named, '%s names skills' % doc
    assert sorted(name for name in named if '`.claude/skills/%s/' % name not in text) == []


def test_no_doc_says_every_measured_fact_is_in_the_guide() -> None:
    # REVIEW.md TST-217: the table of `.claude/rules/docs.md` sends what only a maintainer needs to the module
    decisions = flat(read('DECISIONS.md'))
    assert "Measured Designer behaviour lives in `GUIDE.md` or the module's docstring" in decisions
    assert "the Designer behaviour GUIDE.md or a module's docstring states" in flat(skill('live-check'))


def test_the_docs_rule_says_which_part_of_the_guide_a_fact_goes_in() -> None:
    # REVIEW.md TST-220: facts in the wrong part are how TST-203 and TST-205 came about
    assert (
        'the core if an agent using only the tools needs it or every script hits it on the first try, otherwise under `# Scripting`'
        in flat(rule('docs.md'))
    )


@pytest.mark.parametrize('part', ['core', 'scripting'])
def test_a_guide_that_cant_be_read_is_refused_and_opens_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, part: str
) -> None:
    # REVIEW.md SRV-102
    patch_server(monkeypatch, 'GUIDE_MD', str(tmp_path / 'missing.md'))
    monkeypatch.setitem(server._session, 'guide_read', False)
    monkeypatch.setitem(server._session, 'scripting_read', False)
    with pytest.raises(ToolError, match=r'GUIDE\.md'):
        server.get_guide(part)
    assert not server._session['guide_read'] and not server._session['scripting_read']
    assert 'GUIDE.md' in server.agents_guide(), 'the resource only says so'


def test_a_guide_without_its_scripting_part_opens_nothing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md SRV-102
    guide = tmp_path / 'GUIDE.md'
    guide.write_text('# GUIDE.md\n\nonly a core\n')
    patch_server(monkeypatch, 'GUIDE_MD', str(guide))
    monkeypatch.setitem(server._session, 'scripting_read', False)
    with pytest.raises(ToolError, match=r'GUIDE\.md'):
        server.get_guide('scripting')
    assert not server._session['scripting_read']


@pytest.mark.parametrize('content', ['', '\n \n', '\n# Scripting: only this part\n', '# Scripting: only this part\n'])
def test_a_guide_without_its_core_opens_nothing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, content: str) -> None:
    # REVIEW.md SRV-103
    guide = tmp_path / 'GUIDE.md'
    guide.write_text(content)
    patch_server(monkeypatch, 'GUIDE_MD', str(guide))
    monkeypatch.setitem(server._session, 'guide_read', False)
    with pytest.raises(ToolError, match=r'GUIDE\.md'):
        server.get_guide('core')
    assert not server._session['guide_read']
    assert 'GUIDE.md' in server.agents_guide(), 'the resource only says so'


def test_a_scripting_part_with_no_text_opens_nothing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md SRV-104
    guide = tmp_path / 'GUIDE.md'
    guide.write_text('# GUIDE.md\n\na core\n# Scripting: raw code\n\n')
    patch_server(monkeypatch, 'GUIDE_MD', str(guide))
    monkeypatch.setitem(server._session, 'scripting_read', False)
    with pytest.raises(ToolError, match=r'GUIDE\.md') as refusal:
        server.get_guide('scripting')
    assert not server._session['scripting_read']
    assert 'the tools refuse' not in str(refusal.value), 'the other tools still work here'  # REVIEW.md SRV-105


@pytest.mark.parametrize('part', ['core', 'scripting'])
def test_a_guide_that_isnt_text_opens_nothing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, part: str) -> None:
    # REVIEW.md SRV-104
    guide = tmp_path / 'GUIDE.md'
    guide.write_bytes(b'# GUIDE.md\n\xff\xfe\n# Scripting\n\nbody\n')
    patch_server(monkeypatch, 'GUIDE_MD', str(guide))
    monkeypatch.setitem(server._session, 'guide_read', False)
    monkeypatch.setitem(server._session, 'scripting_read', False)
    with pytest.raises(ToolError, match=r'GUIDE\.md'):
        server.get_guide(part)
    assert not server._session['guide_read'] and not server._session['scripting_read']
    assert 'GUIDE.md' in server.agents_guide(), 'the resource only says so'


@pytest.mark.parametrize(
    'scope',
    [
        'float4 and enum parameters of atomic nodes, float4 of an instance node',
        'relative to input on a levels node, all six; relative to parent on an instance node, `$outputsize` measured',
        "on a node's `$outputsize` and the graph's `$randomseed`, both directions",
    ],
)
def test_a_claim_keeps_the_scope_it_was_measured_on(scope: str) -> None:
    # REVIEW.md TST-207
    assert scope in flat(guide_md())


def test_the_examples_claim_keeps_the_scope_it_was_measured_on() -> None:
    # REVIEW.md TST-207; the example's notes for whoever changes it are in its docstring (REVIEW.md TST-782)
    assert 'caused no crash in five tries' in flat(read('examples', 'build_dwarf_trimsheet.py'))


def test_what_a_helper_cites_for_a_measurement_states_it() -> None:
    # REVIEW.md TST-207
    text = read('mcp_server', 'designer_helpers', 'graph_inputs.py')
    assert (
        '(measured on all six on a levels node and `$outputsize` on an instance node, tests/test_all_tools/facts/designer_scripts/function_states.py)'
        in flat(text)
    )
    # REVIEW.md HLP-207: why `_delete_function`'s inheritance calls have no guard, once in DECISIONS.md
    assert 'Neither inheritance call raised in any of those cases, so neither has a guard' in flat(text)


def test_address_review_sends_a_measured_fact_where_the_table_says() -> None:
    # REVIEW.md TST-208
    text = flat(skill('address-review'))
    # the table of where each fact goes, in the docs' rule (Keeping the docs current)
    assert text.count("GUIDE.md or the module's docstring, as the table in `.claude/rules/docs.md` says") == 2


def test_small_text_defects_stay_fixed() -> None:
    # REVIEW.md TST-210
    core, _ = _parts()
    assert '\n\n## First sd pitfalls' in core
    guide = flat(guide_md())
    assert 'in its home)' not in guide and '`/tmp/sd_mcp_<uid>_<port>/home`' in guide
    assert 'It ends only a Designer an agent started' not in guide
    lifecycle = flat(read('mcp_server', 'server_tools', 'lifecycle.py'))
    assert 'a main thread frozen outside a job reads as idle' in lifecycle
    assert lifecycle.count('41 bytes') == 1, 'the socket is explained once'
    # REVIEW.md TST-215
    assert lifecycle.count('writes its `session.instancePID` there') == 1, 'the plist is explained once'


def test_the_guide_and_agents_md_point_to_each_other() -> None:
    assert 'mcp_server/GUIDE.md' in agents_md()
    assert 'AGENTS.md' in guide_md()


@pytest.mark.parametrize(
    ('fact', 'module'),
    [
        ('algipc', 'server_tools/lifecycle.py'),
        ('CFFIXED_USER_HOME', 'server_tools/lifecycle.py'),
        ('SBS_DESIGNER_PYTHON_PATH', 'server_tools/lifecycle.py'),
        ('BinaryHardeningService', 'server_tools/lifecycle.py'),
        ('QThreadPool', 'server_tools/lifecycle.py'),
        ('agent_designer_file', 'server_tools/lifecycle.py'),
        ('node_align_tools', 'server_tools/layout.py'),
        ('userId', 'server_tools/layout.py'),
        ('close_btn', 'designer_helpers/editor.py'),
        ('Copy Render to Clipboard', 'designer_helpers/screenshots.py'),
    ],
)
def test_what_only_a_maintainer_needs_lives_with_the_code(fact: str, module: str) -> None:
    # would an agent using the tools act differently if it knew this? If not, it is in the module, not the guide
    assert fact not in flat(guide_md())
    assert fact in read('mcp_server', module)


@pytest.mark.parametrize('module', ['server_tools/lifecycle.py', 'server_tools/layout.py'])
def test_the_guide_says_where_the_details_went(module: str) -> None:
    assert '`%s`' % module in guide_md()


def test_no_link_points_to_agents_md_for_what_moved_to_the_guide() -> None:
    stale = _stale_links(re.compile(r"AGENTS\.md(?:'s)?(?:,\s*|\s*\(|\s+)(?:the\s+)?(?:%s)" % MOVED))
    assert not stale, stale


# the instructions limit; the atomic node count (not a ROADMAP item number `| 29 |` or an ID like HLP-29); where the
# record of a Designer an agent started is kept (REVIEW.md TST-159)
@pytest.mark.parametrize('fact', [r'4,096', r'(?<!\| )(?<!-)\b29\b(?! \|)', r'agent_designer_file\(port\)'])
def test_facts_are_stated_once_in_the_docs(fact: str) -> None:
    # `.claude/rules/docs.md`, Keeping the docs current: each fact in one place, linked from elsewhere (REVIEW.md
    # TST-10, TST-18). Every doc counts, so a fact moved to a rule or a skill is still counted
    found = {name: len(re.findall(fact, text)) for name, text in repo_docs()}
    assert sum(found.values()) <= 1, '%r appears in %s' % (fact, {name: n for name, n in found.items() if n})


def test_the_lifecycle_checks_that_run_alone_are_the_ones_the_skill_names() -> None:
    # REVIEW.md TST-168: the live-check skill (its paragraph on lifecycle.py) names the lifecycle checks that run alone; a
    # check saying so in its docstring and missing there, or named there without saying so, is a list gone stale
    import ast

    tree = ast.parse(read('tests', 'test_all_tools', 'lifecycle', 'checks.py'))
    say_so = {
        node.name
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name.startswith('check_')
        and 'runs in a scratch run too' in flat(ast.get_docstring(node) or '')
    }
    listed = re.search(r'Three of its checks end only.*?(?=\n\n)', skill('live-check'), re.S)
    assert listed, "the live-check skill's list of the lifecycle checks that run alone"
    named: set[str] = set(re.findall(r'`(check_\w+)`', listed.group(0)))
    assert say_so and named == say_so, 'named in the skill: %s; saying so in their docstring: %s' % (
        sorted(named),
        sorted(say_so),
    )


# the names of the pool's rules, as workers.py's docstring gives them
POOL_RULES = ('launch_lock', 'CLIPBOARD', 'SOLO', 'start checks', 'worker_env', 'spawn')
# phrases of workers.py's docstring saying where and when the pool runs things
POOL_RULE_WORDINGS = (
    'starts first',
    'never run at once',
    'last, alone',
    'first category to start after',
    'one wait at the end',
)


def _selftest_docstring(module: str) -> str:
    """The docstring of tests/test_all_tools/<module>, flat."""
    import ast

    return flat(ast.get_docstring(ast.parse(read('tests', 'test_all_tools', module))) or '')


def _skill_bullet() -> str:
    """The live-check skill's bullet on the self-test, flat."""
    bullet = re.search(
        r'(?ms)^- `mcp_server/venv/bin/python tests/test_all_tools`.*?(?=^ {2}- |^- |^$)', skill('live-check')
    )
    assert bullet, "the live-check skill's bullet on the self-test"
    return flat(bullet.group(0))


def _skill_cant_prove_list() -> str:
    """The live-check skill's list of what a scratch run can't prove, flat."""
    found = re.search(r"(?s)\*\*What a scratch run can't prove\*\*.*?(?=\n\n\*\*)", skill('live-check'))
    assert found, "the live-check skill's list of what a scratch run can't prove"
    return flat(found.group(0))


@pytest.mark.parametrize('rule_name', POOL_RULES)
def test_the_skills_bullet_points_at_workers_py_and_names_none_of_the_pools_rules(rule_name: str) -> None:
    # ROADMAP item 68: the skill's bullet on the self-test repeated the rules workers.py's docstring holds, and a copy
    # had drifted once; it points there, as it does for alone.py's. Only these names are looked for, as whole words
    # (REVIEW.md TST-284, TST-286)
    text = _skill_bullet()
    # REVIEW.md TST-600: the rules there are the pool's, not the live suite's
    assert '(the pool: `tests/test_all_tools/workers.py`)' in text
    word = r'\b%s\b' % re.escape(rule_name)
    assert re.search(word, _selftest_docstring('workers.py')) and not re.search(word, text)


@pytest.mark.parametrize('wording', POOL_RULE_WORDINGS)
def test_the_skills_pool_passages_have_none_of_these_phrases_of_workers_py(wording: str) -> None:
    # REVIEW.md TST-283: the skill's bullet on the self-test and its list of what a scratch run can't prove name the
    # pool's rules and leave where and when they run to workers.py's docstring (the start checks' sentence had gone
    # false once: TST-265). Only these phrases are looked for, and only there: elsewhere the skill words other modules'
    # rules alike (REVIEW.md TST-286)
    assert wording in _selftest_docstring('workers.py')
    assert wording not in _skill_bullet() and wording not in _skill_cant_prove_list()


def test_workers_py_sends_a_windows_run_to_the_index_which_says_what_it_does() -> None:
    # REVIEW.md TST-285: the skill points at workers.py, whose sentence on Windows said only "one run, as before"
    assert "one run in one Designer (`__main__.py`'s docstring)" in _selftest_docstring('workers.py')
    index = _selftest_docstring('__main__.py')
    assert 'every category but `lifecycle`' in index and 'leaves it open at the end' in index


@pytest.mark.parametrize(
    'name',
    [
        'README.md',
        'AGENTS.md',
        os.path.join('.claude', 'skills', 'live-check', 'SKILL.md'),
        os.path.join('tests', 'test_all_tools', '__main__.py'),
    ],
)
def test_these_docs_have_none_of_these_phrasings_of_four_at_once_or_by_default(name: str) -> None:
    # ROADMAP item 68: each of these said "four at once" or "4 by default"; the number is workers.AT_ONCE, which --help
    # prints. Only these phrasings are looked for (REVIEW.md TST-284, TST-286): four or 4 up to two words before "at
    # once", or right beside "by default", "default", "default:" or "defaults to"; a measurement made with four is
    # written without "at once" ("four side by side")
    text = flat(read(name))
    pattern = (
        r'\b(?:four|4)(?: \S+){0,2} at once\b'
        r'|\b(?:four|4) by default\b|\bdefault:? (?:four|4)\b|\bdefaults to (?:four|4)\b'
    )
    assert not re.search(pattern, text, re.I)


def test_the_code_tools_and_the_scripting_part_say_not_to_open_an_undo_group() -> None:
    # REVIEW.md SRV-275: the call is one undo step already, and a timeout inside a group of the code's own can leave it
    # open
    tools = _tools()[1]
    for text in (tools['execute_designer_code'], tools['run_designer_script'], _parts()[1]):
        assert 'undo group of your own' in flat(text), text[:80]
