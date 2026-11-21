"""The project's subagents (`.claude/agents/`, ROADMAP item 102): each one parses and names only tools and skills that
exist, and only the developer starts agents. The agents that only read get no tool that writes or drives Designer, and
their Bash is for reading by their instructions alone (DECISIONS.md, No agent has a write guard). Every agent with Bash
can stop a command moved to the background. The review skill starts its reviewers as the `reviewer` agent, and
the `delegate` skill's routing names every agent."""

import asyncio
import functools
import json
import re
from pathlib import Path

import pytest
from docs_text import agent, agents_md, flat, headings, read, section, skill, story_md

from conftest import ROOT

AGENTS = Path(ROOT, '.claude', 'agents')
SKILLS = Path(ROOT, '.claude', 'skills')

# PyCharm's tools that only read (`.claude/rules/python.md`: navigating and checking code)
PYCHARM_READS = {
    'mcp__pycharm__' + name
    for name in (
        'search_symbol',
        'get_symbol_info',
        'analyze_calls',
        'get_file_problems',
        'search_text',
        'search_regex',
        'search_file',
        'read_file',
        'list_directory_tree',
        'lint_files',
        'get_project_dependencies',
    )
}
BUILT_IN_READS = {'Read', 'Grep', 'Glob', 'WebFetch', 'WebSearch'}
READS = BUILT_IN_READS | PYCHARM_READS
BUILT_IN = BUILT_IN_READS | {'Agent', 'Bash', 'Edit', 'Write', 'Skill', 'TaskStop', 'SendMessage'}
DESIGNER = 'mcp__substance-designer__'
WHOLE_SERVERS = {'mcp__pycharm__*', DESIGNER + '*'}

# Every agent, and whether it only reads. A new agent file fails here until its job is decided.
ONLY_READS = {'analyst': True, 'reviewer': True, 'developer': False, 'runner': False}
READING_AGENTS = sorted(name for name, reads in ONLY_READS.items() if reads)

Fields = dict[str, str | list[str]]


def _frontmatter(path: Path) -> Fields:
    """The fields of an agent's frontmatter: the value on the key's line, or else the lines indented under the key,
    each without its first two spaces."""
    found = re.match(r'---\n(.*?)\n---\n', path.read_text(encoding='utf-8'), re.S)
    assert found, '%s has no frontmatter' % path.name
    fields: Fields = {}
    key = ''
    lines: list[str] = found.group(1).split('\n')
    for line in lines:
        block = fields.get(key)
        if line.startswith('  ') and isinstance(block, list):
            block.append(line[2:])
            continue
        field = re.fullmatch(r'(\w+):(?: (.+))?', line)
        assert field, "%s: a line the frontmatter reader doesn't know: %r" % (path.name, line)
        named: str = field.group(1)  # a fresh local: a reassigned one would take group's `str | Any`
        value: str | None = field.group(2)
        key = named
        fields[key] = value if value is not None else []
    return fields


@functools.cache
def _agents() -> dict[str, Fields]:
    return {path.stem: _frontmatter(path) for path in sorted(AGENTS.glob('*.md'))}


def _body(name: str) -> str:
    """The text of the agent `name`'s file after its frontmatter, with its whitespace made single spaces."""
    return flat(agent(name).split('\n---\n', 1)[1])


def _tools(fields: Fields) -> list[str]:
    tools = fields['tools']
    assert isinstance(tools, str), 'tools as one line, separated by commas'
    return [tool.strip() for tool in tools.split(',')]


def _designer_tools() -> set[str]:
    from server_tools.core import server

    return {DESIGNER + tool.name for tool in asyncio.run(server.list_tools())}


def test_every_agent_has_its_job_decided() -> None:
    assert set(_agents()) == set(ONLY_READS)


@pytest.mark.parametrize('name', sorted(ONLY_READS))
def test_an_agent_parses_and_lists_its_tools(name: str) -> None:
    fields = _agents()[name]
    assert fields.get('name') == name
    for key in ('description', 'tools', 'model', 'effort'):  # without tools, an agent gets every tool the session has
        value = fields.get(key)
        assert isinstance(value, str) and value, '%s: no %s' % (name, key)
        assert ': ' not in value, "%s: a ': ' in %s would end the plain YAML value" % (name, key)
    # the user's choice (ROADMAP item 102). A model without the level "falls back to the highest supported level at or
    # below the one you set" (Claude Code's docs, model-config)
    assert fields['effort'] in ('low', 'medium', 'high', 'xhigh', 'max'), fields['effort']


@pytest.mark.parametrize('name', sorted(ONLY_READS))
def test_only_the_developer_starts_agents(name: str) -> None:
    # each one reports to the agent that started it, which decides what comes next. The developer starts `/simplify`'s
    # cleanup agents on its own change, and `analyst` agents (AGENTS.md, Delegating to subagents)
    assert bool({'Agent', 'Task'} & set(_tools(_agents()[name]))) == (name == 'developer'), name


@pytest.mark.parametrize('name', READING_AGENTS)
def test_an_agent_that_only_reads_gets_only_tools_that_read(name: str) -> None:
    # a review runs no tests (AGENTS.md, Running the tests), and its reviewers edit nothing and don't probe Designer
    # (the project-code-review skill): its tools enforce that, but for Bash
    fields = _agents()[name]
    tools = set(_tools(fields))
    assert tools <= READS | {'Bash', 'TaskStop'}
    # on macOS, Linux and WSL an agent with Bash gets no Grep or Glob tool: it searches with grep and find
    assert 'Bash' in tools, '%s has no Bash to search with' % name
    # no hook limits its Bash: its instructions are the rule (DECISIONS.md, No agent has a write guard)
    assert 'hooks' not in fields, '%s has a hook' % name
    assert 'Nothing enforces it' in _body(name), name


@pytest.mark.parametrize('name', sorted(ONLY_READS))
def test_only_the_agents_of_long_runs_can_answer_the_lead(name: str) -> None:
    # the `delegate` skill (A long run): the developer and the runner answer the lead's question on their status, and
    # nothing else
    tools = _tools(_agents()[name])
    assert ('SendMessage' in tools) == (name in ('developer', 'runner')), name
    if 'SendMessage' in tools:
        assert 'SendMessage is for that answer only' in _body(name), name
        # REVIEW.md AGT-68: a question that doesn't name its sender would leave the agent to guess its `to`
        assert 'SendMessage to `main`' in _body(name), name


def _delegate_paragraph(label: str) -> str:
    """The paragraph of the `delegate` skill that starts at the bold `label`, flat."""
    return flat(skill('delegate').split(label, 1)[1].split('\n\n')[0])


def test_the_delegate_skill_says_how_an_edited_agent_file_reaches_an_agent() -> None:
    # REVIEW.md AGT-69: a round of fixes resumes the developer, which keeps the definition it was started with
    edited = _delegate_paragraph('**How changes reach the agents**')
    for said in ('or resumes it with SendMessage', 'tools, model, preloaded skills or effort takes a new agent'):
        assert said in edited, said


def test_the_delegate_skill_says_how_a_long_run_is_timed() -> None:
    # REVIEW.md AGT-68: one timer per long run, stopped when the run ends first, and the answer measured
    run = flat(skill('delegate')).split('**A long run**')[1].split('**')[0]
    for said in ('one background command per run', 'TaskStop', 'to `main`', 'Measured 2026-11-19'):
        assert said in run, said


def test_a_finding_moved_to_roadmap_md_has_its_wording_and_stops_the_loop() -> None:
    # the user, 2026-11-20: a real finding whose fix is work for later, outside the branch's scope, becomes a
    # ROADMAP.md item once the user approves it. The item cites the finding's ID, and the entry is checked with a fifth
    # wording. The lead asks at once, as for a won't fix, since the finding stays open until the user answers
    delegate, review, address = (flat(skill(name)) for name in ('delegate', 'project-code-review', 'address-review'))
    for said in (
        "*not a bug*, *not reproducible*, *won't fix* or *moved to ROADMAP.md*",
        '`**Resolution: moved to ROADMAP.md** (item N, the user, <date>)`',
        "**Moved to ROADMAP.md is the user's decision too** (the user, 2026-11-20)",
        'a ROADMAP.md item instead, which closes the finding (**Moved to ROADMAP.md**, below)',
    ):
        assert said in address, said
    assert (
        'a finding to move to ROADMAP.md instead of a fix (the `address-review` skill, step 7), since it stays open until'
        ' the user answers (the user, 2026-11-20)' in delegate
    )
    assert "(not a bug, not reproducible, won't fix, moved to ROADMAP.md)" in review
    # REVIEW.md TST-637: the story's stop list and convergence report tell it too
    story = flat(story_md())
    assert '- a finding to move to ROADMAP.md instead of a fix' in story
    assert 'and the findings they moved to ROADMAP.md' in story
    assert "**Moved to ROADMAP.md:** does the item it names cite the finding's ID?" in flat(agent('reviewer'))
    # TEMPLATE.md's lists of the wordings: test_review_lookup.py, WORDINGS


def test_the_users_rules_of_2026_11_20_keep_their_wording() -> None:
    # REVIEW.md TST-610: the user's rules of 2026-11-20, in the skills that give them. A won't fix is the user's
    # decision, asked at once when the criteria hold and recapped at convergence. A decision that doesn't block the
    # next step waits in PLAN.md. Sonnet rounds review each step, and Opus rounds the entire branch after the last
    delegate, review, address = (flat(skill(name)) for name in ('delegate', 'project-code-review', 'address-review'))
    assert 'in a section Waiting for the user, the decisions waiting' in delegate
    for text in (delegate, review):
        assert 'waits in PLAN.md, Waiting for the user' in text
    assert (
        "a won't fix that meets the `address-review` skill's criteria (step 7), since its finding stays open"
        in delegate
    )
    for said in (
        "**Won't fix is the user's decision** (the user, 2026-11-20)",
        'the lead may propose one itself',
        '**The finding is real,**',
        '**Fixing it is never worth it, not just "not now".**',
        "**It isn't work for later.**",
        # REVIEW.md AGT-93: "when unsure whether (2) holds, have it fixed"
        'or the lead is unsure whether it holds, the finding is fixed',
        'When all hold, the lead tells the user at once',
        # Show the plan first is skipped in the loop, by the lead fixing findings itself too
        "During the lead's loop this step is skipped: by the developer, whose brief is the plan, and by the lead fixing"
        ' findings itself, since the loop runs without asking (the `project-code-review` skill, step 7). It applies'
        ' when the user asks for findings to be fixed outside the loop.',
    ):
        assert said in address, said
    assert 'A developer skips this step: its brief is the plan.' not in address
    assert "It also recaps the won't fixes the user agreed during the loop" in review
    # "sonnet by default and I ask you when to override with opus"
    assert _agents()['reviewer']['model'] == 'sonnet'
    assert 'only when the user asks for another model for that run' in _delegate_paragraph('**Pass `model`')
    # "let sonnet be the default until reviews converge and when you are about to say the reviews converged (5 - 7 low
    # findings) run another round with all opus instead of sonnet (you do the override when you call them)", then "run
    # review rounds with sonnet then when converged run with opus until converged again", and the Opus rounds on "the
    # entire branch diff against main". The flow the user confirmed (2026-11-20): Sonnet rounds per step, Opus rounds
    # on the entire branch after the last step only, the first one able to converge. Its one home is the review skill's
    # step 7, which the paragraph on `model` points to. A step's reviews are done; "converged" is the end of the
    # reviews alone, when the user is told (REVIEW.md AGT-97)
    for said in (
        'about 5 to 7 at most',
        "a Sonnet round reviews the step's diff",
        "until a Sonnet round's new findings are only a few Low ones, or none",
        "The step's reviews are then done, and the loop goes on with the next step",
        'an Opus round, the lead passing `model: opus` on each Agent call, reviews "the entire branch diff against main"',
        'Opus rounds review the fixes until one finds only a few Low ones, or none',
        'Then an Opus round reviews the entire branch again',
        'when an Opus round of the entire branch finds only a few Low ones, or none',
        # REVIEW.md AGT-100: a round finding a few, one of them above Low, goes on as one finding more than a few does
        'When it finds more than a few Low ones, or any above Low, the developer fixes them',
        'When that round finds more than a few Low ones, or any above Low, the Opus rounds on its fixes run again',
    ):
        assert said in review, said
    assert 'more than a few,' not in review
    for said in (
        "Sonnet rounds review each step, or group, until the step's reviews are done",
        'After the last step, Opus rounds review the entire branch and the fixes of their findings until the reviews '
        'look converged',
    ):
        assert said in delegate, said
    # no Opus round, and no convergence, before the last step (the user, 2026-11-20): in step 7 and in the loop
    for text, start in ((review, '7. **Go on with the loop**'), (delegate, "**The loop is the lead's**")):
        before = text.split(start, 1)[1].split('After the last step', 1)[0]
        assert 'Opus' not in before and 'converge' not in before, before
    model = _delegate_paragraph('**Pass `model`')
    # REVIEW.md AGT-100: "keep running only opus until reviews converge", so the rounds on the fixes run on Opus too
    assert (
        'the Opus rounds after the last step, on the entire branch and on its fixes (the `project-code-review` skill, '
        'step 7)' in model
    )


def test_the_users_rule_on_tests_that_fail_at_random_keeps_its_wording() -> None:
    # REVIEW.md TST-676: the user's rule of 2026-11-21, its key clauses in six of the places it is written, all but the
    # `delegate` skill's merge sentence and the `address-review` skill's step 4 (DECISIONS.md, Project rules). A
    # test that fails in a full run and passes rerun alone, a live check with its category alone, failed at random: it
    # counts as passed, and is listed, or its row's count goes up. The coverage check, made only over a full run, names
    # its missing tools: their categories rerun alone. One that fails alone too is a failure
    coverage = (
        'The check that every tool was exercised, made only over a full run, names the tools no check ran for: the'
        ' categories whose checks exercise them are rerun alone, and if they pass with checks run for those tools, it'
        ' failed at random too'
    )
    decisions = flat(read('DECISIONS.md'))
    for said in (
        '**A test that fails in a full run and passes rerun alone failed at random, and counts as passed.**',
        '(`tests/test_all_tools --only <category>`)',
        coverage,
        'One already listed there that fails at random again has its count raised, and the merge goes ahead',
        # the user's answers to AGT-113, AGT-114 and the count, 2026-11-21
        'The pool\'s other checks over the whole run are rerun with what they need (the user, 2026-11-21: "rerun")',
        'a live check is rerun with its category alone in a scratch run',
        'it is fixed when ROADMAP.md gets to it, whatever its count',
        # the user's answers of 2026-11-21 on the reruns' edge cases (REVIEW.md AGT-119, AGT-120)
        'A check that skips in its rerun is rerun once the cause of the skip is cleared',
        'Another check failing in that rerun is rerun alone too, as a failure of the final check',
        "The checks only the whole run makes there, such as its start checks and its check that the user's graph is back"
        ' in the editor, are rerun with the whole run there',
        "A failure that meets another entry's Reopen if still meets it when its rerun passes",
        # the user's answer on the branch's own flaky check, 2026-11-21
        "A test the branch was to make robust that fails at random reopens the branch's ROADMAP.md item",
        "the item is unchecked, its Done note naming that row, as its fix isn't proven",
    ):
        assert said in decisions, said
    # the user changed the second time, 2026-11-21; it says what happens, in neither term, as the user's "counts as
    # failed" came with "no fix is mandatory" (REVIEW.md AGT-115)
    for gone in ('counts as passed once', 'again counts as passed', 'again counts as failed'):
        assert gone not in decisions, gone
    live = flat(skill('live-check'))
    for said in (
        '**When the final check fails,** the runner first reruns each failing test alone',
        'tests/test_all_tools --only <category>`',
        coverage,
        'A test that passes alone failed at random: the final check counts as passed for it, whatever its count',
        "The pool's other checks over the whole run are rerun with what they need",
        'the count of quits forced, with the categories it names, together: `--only <category> <category> ...`',
        'a live check is rerun with its category alone in a scratch run',
        '"Tests that failed at random", or raises the count of the row it has',
        "unchecks the branch's ROADMAP.md item, its Done note naming the test's row (DECISIONS.md)",
        'One that fails alone too is a failure (DECISIONS.md, Project rules)',
    ):
        assert said in live, said
    assert 'When the final check fails, rerun each failing test alone in the same brief' in flat(agent('runner'))
    assert 'a test that fails at random and passes rerun alone counting as passed' in flat(agents_md())
    assert (
        'it counts as passed, and the lead lists it in ROADMAP.md, or counts it again there, before the merge'
        in flat(story_md())
    )
    roadmap = section(read('ROADMAP.md'), '## Tests that failed at random')
    assert 'gets its count raised' in flat(roadmap) and 'and the merge goes ahead' in flat(roadmap)
    assert '| Test | Times | Last seen | Commit | Its last FAIL line | Evidence kept |' in roadmap


def test_a_leftover_in_the_branchs_own_code_is_fixed_in_the_branch() -> None:
    # REVIEW.md AGT-94: the lead decides it alone (the user, 2026-11-19), and the review and fix skills send such a
    # leftover there rather than to a ROADMAP.md proposal
    assert "a leftover in the branch's own code is fixed in the branch" in flat(skill('delegate'))
    for name in ('project-code-review', 'address-review'):
        assert "leftover in the branch's own code" in flat(skill(name)), name


def test_the_rules_agents_md_gave_every_agent_reach_the_agents_whose_files_load_none() -> None:
    # REVIEW.md AGT-85, AGT-88: they moved to a rule or a skill, which loads by a file's path or when asked for. A
    # developer measuring through the session's Designer tools loads no `live-check`, and its scratch scripts, like a
    # probe's, are in the scratchpad, which no rule's paths match. A reviewer reading a diff through `git diff` may
    # load no `docs.md`
    designer = flat(section(agent('developer'), '## Designer'))
    assert 'the `live-check` skill, When a Designer crashed or hung' in designer
    assert '`.claude/rules/waits.md`' in designer
    assert '`.claude/rules/docs.md`, Writing docs and comments' in _body('reviewer')
    probe = flat(skill('live-check')).split('**How a probe runs,**')[1].split('**When the final check fails,**')[0]
    assert '`.claude/rules/waits.md`' in probe
    # the runner reaches How a probe runs, and the crash procedure, only through the skill its file preloads (REVIEW.md
    # TST-606)
    assert '- live-check' in _agents()['runner'].get('skills', [])


@pytest.mark.parametrize('name', sorted(ONLY_READS))
def test_an_agent_with_bash_can_stop_a_command_moved_to_the_background(name: str) -> None:
    # a foreground command that outlives its timeout is moved to the background and keeps running (Claude Code's tools
    # reference, "Foreground commands that move to the background"; REVIEW.md AGT-24)
    tools = _tools(_agents()[name])
    if 'Bash' in tools:
        assert 'TaskStop' in tools, name
        assert 'TaskStop' in _body(name), '%s is never told to use it' % name


def test_every_tool_an_agent_names_exists() -> None:
    servers: dict[str, object] = json.loads(Path(ROOT, '.mcp.json').read_text(encoding='utf-8'))['mcpServers']
    assert 'mcp__%s__' % next(iter(servers)) == DESIGNER
    known = BUILT_IN | PYCHARM_READS | WHOLE_SERVERS | _designer_tools()
    unknown = {name: sorted(set(_tools(fields)) - known) for name, fields in _agents().items()}
    assert {name: tools for name, tools in unknown.items() if tools} == {}


def test_every_skill_an_agent_preloads_exists() -> None:
    for name, fields in _agents().items():
        skills = fields.get('skills', [])
        assert isinstance(skills, list), '%s: skills as a list, one per line' % name
        for item in skills:
            assert item.startswith('- '), '%s: a skill is a list item' % name
            skill_name = item[2:]
            assert Path(SKILLS, skill_name, 'SKILL.md').is_file(), '%s preloads %s, which is no skill here' % (
                name,
                skill_name,
            )


def test_the_frontmatter_reader_reads_blocks_and_refuses_what_it_doesnt_know(tmp_path: Path) -> None:
    path = tmp_path / 'a.md'
    path.write_text('---\nname: a\ntools: Read, Grep\nskills:\n  - live-check\n---\nBody\n', encoding='utf-8')
    assert _frontmatter(path) == {'name': 'a', 'tools': 'Read, Grep', 'skills': ['- live-check']}
    path.write_text('---\nname: a\n  nested: b\n---\n', encoding='utf-8')
    with pytest.raises(AssertionError, match="doesn't know"):
        _frontmatter(path)


def _review_skill_step_3() -> str:
    return (
        skill('project-code-review').split('3. **Split the work by area**')[1].split('4. **Settle every suspicion')[0]
    )


def test_the_review_skill_starts_its_reviewers_as_the_reviewer_agent() -> None:
    # ROADMAP item 102: step 3 says what the lead gives each reviewer; the reviewer's own rules (no tests, no probes,
    # the report format, the quoted code) are in its agent file, once
    step = flat(_review_skill_step_3())
    assert 'the `reviewer` agent' in step and '`.claude/agents/reviewer.md`' in step
    assert 'report format' not in step and 'must quote' not in step
    reviewer = _body('reviewer')
    for rule in ('runs no tests and no probes', 'the code, quoted', 'Drop only what reading disproves'):
        assert rule in reviewer, rule


def _diff_commands(text: str) -> list[str]:
    """The `git diff` commands `text` gives, in backticks."""
    return re.findall(r'`(git diff [^`]*)`', flat(text))


def test_every_diff_command_the_review_skill_gives_leaves_plan_md_out() -> None:
    # REVIEW.md TST-580: a reviewer reads its diff from the command its brief names, and never reads PLAN.md, the lead's
    # own account of the work (`reviewer.md`, Review blind). TST-593: the lead copies the template's Scope example too
    scope = skill('project-code-review').split('\n## Scope\n')[1].split('\n## ')[0]
    template = read('.claude', 'skills', 'project-code-review', 'TEMPLATE.md')
    for where, text in (("the skill's Scope", scope), ('TEMPLATE.md', template)):
        commands = _diff_commands(text)
        assert commands, '%s gives the diff commands' % where
        assert [command for command in commands if " -- . ':(exclude)PLAN.md'" not in command] == [], where
    # REVIEW.md AGT-99: a reviewer reads REVIEW.md as the record, and it is a quarter of the whole branch's diff, so the
    # whole-branch commands leave it out too. A round's diff keeps it: its newly checked entries are what step 2
    # rechecks
    branch = [command for command in _diff_commands(scope) if 'main' in command]
    assert len(branch) == 2 and all(command.endswith(" ':(exclude)REVIEW.md'") for command in branch), branch
    assert 'REVIEW.md is read as the record' in flat(scope)


def test_a_step_is_quoted_as_the_user_approved_it() -> None:
    # REVIEW.md AGT-99: PLAN.md changes after the user approves a step, the lead's notes joining it, so the brief quotes
    # the step from the first commit that holds it
    step = flat(_review_skill_step_3())
    assert 'taken from the first commit of PLAN.md that holds it' in step
    assert "each step's section of PLAN.md that the user approved" not in step
    # REVIEW.md AGT-106: the user's later instructions that change a step join the claim, the later one standing. The
    # whole-branch briefs added them by hand. The `delegate` skill's brief and the reviewer's file say so too
    later = 'Where two texts differ, the later one stands.'
    assert "The user's later instructions that change a step join it, each quoted word for word with its date." in step
    assert later in step and later in _body('reviewer')
    brief = flat(section(skill('delegate'), '## The brief'))
    assert "the claim is the text the user approved, with the user's later dated instructions that change it" in brief


def test_a_reviewer_needs_only_its_file_and_its_brief() -> None:
    # ROADMAP item 102: the reviewer's own rules (what it looks for, how it rechecks a resolution, rates a finding and
    # marks a follow-up's generation) are in its file alone, so a reviewer doesn't read the review skill, which is the
    # lead's procedure
    reviewer, review = _body('reviewer'), flat(skill('project-code-review'))
    for rule in (
        'the more specific the better',
        'does the fix address the cause it names',
        "don't raise the same finding again",
        'also in `DECISIONS.md`',
        '`follows <old ID>, generation N`',
        'Generation 3 or later, Low or Low-medium, and only about tests or docs',
        # REVIEW.md TST-598: what a reviewer makes of an ID the lookup can't find, and of an old commit hash
        'a broken reference or a lost finding; say which you can tell',
        "An old resolution's commit hash may no longer resolve",
    ):
        assert rule in reviewer and rule not in review, rule
    assert 'project-code-review` skill,' not in reviewer, 'a rule of its own read from the skill'


def test_the_review_skill_names_the_reviewers_rules_by_file_and_section() -> None:
    # REVIEW.md TST-599: "their rules: step 3" read as a step of reviewer.md, which has none
    review = flat(skill('project-code-review'))
    assert re.findall(r'rules(?::|\s+say)?\s*\(?step\s+\d', review) == []
    reviewer = headings(agent('reviewer'))
    for name in ('Before reviewing', 'Rechecking a resolution', 'Follow-up chains'):
        assert '(`.claude/agents/reviewer.md`, %s)' % name in review, name
        assert '## %s' % name in reviewer, name


def test_the_delegate_skill_says_what_to_give_each_agent() -> None:
    # a new agent file fails here until the lead's routing table has a row for it, and a row for no agent fails too.
    # The section's prose names each agent as well, so only the rows count (REVIEW.md TST-571)
    routing = section(skill('delegate'), '## Which agent for what')
    assert set(re.findall(r'^\| `(\w+)` \|', routing, re.M)) == set(ONLY_READS)
