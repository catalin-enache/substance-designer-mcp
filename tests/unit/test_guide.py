"""The guide reaches every session: short instructions (MCP clients cut long ones; Claude Code at
4,096 characters) that point to get_guide(), which returns the core of mcp_server/GUIDE.md; get_guide('scripting') the rest. AGENTS.md holds what
contributors need; each file has its own size limit."""

import os
import re
import subprocess
from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from test_server import _tools

from conftest import ROOT, patch_server, server

CLAUDE_CODE_LIMIT = 4096  # measured: the guide arrived cut at exactly this many characters
# the sections of each file, by the audience that reads it
GUIDE_SECTIONS = (
    "## Rules that protect the user's work",
    '## Which tool for what',
    '## Undo and timeouts',
    '## Environment facts',
    '## First sd pitfalls',
    '## Library node facts (Designer 16)',
    '## Rendering and verifying',
    '## Example',
)
SCRIPTING_SECTIONS = ('## sd API gotchas', '## Designer UI (Qt)')
AGENTS_SECTIONS = (
    '## Working on this project',
    '### Running the tests',
    '### Keeping the docs current',
    '### Deploying and diagnosing',
)
# what the guide holds, as a link to it names it: its sections and the bold paragraphs other files point to
MOVED = (
    r'Rules|rules|Which tool|Undo|Environment facts|sd API|Designer UI|Library node|Rendering and verifying|Example'
    r'|Portals|Several Designers|Output nodes|Graph size|Screenshots|Quitting'
)


def _agents_md() -> str:
    with open(os.path.join(ROOT, 'AGENTS.md'), encoding='utf-8') as f:
        return f.read()


def _guide_md() -> str:
    with open(os.path.join(ROOT, 'mcp_server', 'GUIDE.md'), encoding='utf-8') as f:
        return f.read()


def _live_check_skill() -> str:
    return Path(ROOT, '.claude', 'skills', 'live-check', 'SKILL.md').read_text(encoding='utf-8')


def _parts() -> tuple[str, str]:
    """The guide file's two parts, the second starting at its level-1 Scripting heading."""
    parts = re.split(r'(?m)^(?=# Scripting)', _guide_md())
    assert len(parts) == 2, 'one Scripting heading'
    return parts[0].rstrip('\n') + '\n', parts[1]


def _headings(text: str) -> set[str]:
    return set(re.findall(r'(?m)^##+ .*$', re.sub(r'(?ms)^```.*?^```', '', text)))


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
    assert not _headings(text) & set(SCRIPTING_SECTIONS)


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
    core, scripting = map(_flat, _parts())
    for fact in ('derives from `BaseException`', 'graph.getNodeDefinitions()', 'Blend modes: copy 0'):
        assert fact in core and fact not in scripting, fact


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
    sent: list[object] = []

    def bridge(*a: object, **k: object) -> str:
        sent.append(a)
        return 'printed'

    patch_server(monkeypatch, '_bridge', bridge)
    script = tmp_path / 'a.py'
    script.write_text('print(1)')

    def run() -> str:
        result: str = (
            server.execute_designer_code('print(1)')
            if tool == 'execute_designer_code'
            else server.run_designer_script(str(script))
        )
        return result

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
    assert server.agents_guide() == _guide_md()


def test_guide_fits_in_one_tool_result() -> None:
    # Claude Code's default limit for one MCP tool result is 25,000 tokens; stay well below
    core, scripting = _parts()
    assert len(scripting) < 60000
    # every Designer session reads the core, so it is held to much less
    assert len(core) < 20000


def test_agents_md_stays_below_the_size_claude_code_warns_at() -> None:
    # loaded automatically into every session in this repo; Claude Code warns from 40 KB
    assert len(_agents_md().encode('utf-8')) < 40000


def test_each_audience_has_its_own_file() -> None:
    core, scripting = _parts()
    assert _headings(core) == set(GUIDE_SECTIONS)
    assert _headings(scripting) == set(SCRIPTING_SECTIONS)
    assert _headings(_agents_md()) == set(AGENTS_SECTIONS)


def test_the_live_check_skill_is_one_claude_code_can_find() -> None:
    assert re.match(
        r"---\nname: live-check\ndescription: '(?:[^']|'')*alone\.run(?:[^']|'')*'\n---\n", _live_check_skill()
    )


@pytest.mark.parametrize(
    'fact',
    [
        '`needs`',
        '**The check lives in the suite:**',
        '**The order:**',
        "**What a scratch run can't prove**",
        '**When the final check fails,**',
        '**The suites.**',
        'designer_scripts/<module>/',
    ],
)
def test_the_procedure_of_live_checks_is_in_the_skill(fact: str) -> None:
    # REVIEW.md TST-219: flat, or a rewrap breaks the test, or hides a copy from the second half
    assert _flat(fact) in _flat(_live_check_skill()) and _flat(fact) not in _flat(_agents_md())


@pytest.mark.parametrize(
    'rule',
    [
        '**Only the agent that changes the code runs tests.**',
        '**The full suites run only when the user asks:**',
        '**Lint and types always run too**',
        'tests/unit/test_lint.py tests/unit/test_types.py',
        'ruff check --fix .',
        '**Load the `live-check` skill',
    ],
)
def test_agents_md_keeps_the_hard_rules(rule: str) -> None:
    assert _flat(rule) in _flat(_agents_md()) and _flat(rule) not in _flat(_live_check_skill())


def test_agents_md_says_how_a_live_check_runs_even_if_the_skill_is_skipped() -> None:
    assert "with `alone.run` from a script in the session's scratchpad" in ' '.join(_agents_md().split())


@pytest.mark.parametrize(
    ('rule', 'patterns', 'skill'),
    [
        ('changing-tools.md', ['mcp_server/server_tools/**/*', 'mcp_server/designer_helpers/**/*'], 'mcp-builder'),
        ('live-checks.md', ['tests/test_all_tools/**/*'], 'live-check'),
    ],
)
def test_a_path_scoped_rule_asks_for_the_skill(rule: str, patterns: list[str], skill: str) -> None:
    # Claude Code loads it when a matching file is read or edited: a rule it can't parse never loads, silently
    text = Path(ROOT, '.claude', 'rules', rule).read_text(encoding='utf-8')
    frontmatter = re.match(r'---\npaths:\n((?:  - "[^"]+"\n)+)---\n', text)
    assert frontmatter, rule
    assert re.findall(r'"([^"]+)"', frontmatter.group(1)) == patterns
    assert '`%s`' % skill in text and Path(ROOT, '.claude', 'skills', skill, 'SKILL.md').is_file()
    for pattern in patterns:
        assert any(Path(ROOT).glob(pattern)), '%s matches no file' % pattern


def test_the_mcp_builder_description_covers_changing_a_tool_here() -> None:
    text = Path(ROOT, '.claude', 'skills', 'mcp-builder', 'SKILL.md').read_text(encoding='utf-8')
    found = re.search(r'(?m)^description: (.*)$', text)
    assert found, 'a description line'
    assert 'before adding, merging or removing a tool or changing its parameters' in found.group(1)
    assert ': ' not in found.group(1), 'would end the plain YAML value and break the frontmatter'


def _flat(text: str) -> str:
    return ' '.join(text.split())


def test_agents_md_asks_for_the_rules_before_touching_the_bridge() -> None:
    # REVIEW.md TST-204: they were loaded automatically before the split
    assert 'before touching the bridge, the token or the plugin, or running anything against Designer' in _flat(
        _agents_md()
    )


def _section(text: str, heading: str) -> str:
    return text.split('\n%s\n' % heading, 1)[1].split('\n## ', 1)[0]


def test_a_tools_only_agent_is_told_the_units() -> None:
    # REVIEW.md TST-205: the core is all it reads, and pixels passed as log2 were taken silently
    core, scripting = map(_flat, _parts())
    assert '`$outputsize` is log2' in core and 'node **centres**' in core
    assert '**Graph size** is log2' not in scripting and 'node **centres**' not in scripting, 'one place'
    doc = _flat(server.apply_edits.__doc__ or '')
    assert 'log2' in doc and 'centre' in doc


def test_the_core_says_when_outputsize_is_an_offset() -> None:
    # REVIEW.md TST-213: `expose` of a value read as log2 computed 8192 px on a 512 px graph
    core, scripting = map(_flat, _parts())
    assert 'while inherited it is a log2 offset, and so is a graph input bound to it' in core  # REVIEW.md HLP-90
    # REVIEW.md TST-221: a Pixel Processor computed the graph's 2048 px from a 512 px input
    assert (
        'Generators inherit the graph size; filters inherit from their input, a Pixel Processor from the graph' in core
    )
    assert 'is a log2 offset' not in scripting and 'Generators inherit' not in scripting, 'one place'


def test_the_core_names_the_tools_that_refuse_too_large_a_size() -> None:
    # REVIEW.md HLP-84
    assert '`apply_edits`, `sweep_param`, `create_graph` and `set_graph_size` refuse more' in _flat(_parts()[0])


@pytest.mark.parametrize('tool', ['create_graph', 'set_graph_size'])
def test_the_size_tools_state_the_largest_size(tool: str) -> None:
    # REVIEW.md HLP-84
    assert '13 is 8192 px, the largest' in _flat(getattr(server, tool).__doc__ or '')


def test_the_hot_reload_rule_is_among_the_rules() -> None:
    # REVIEW.md TST-212: AGENTS.md sends whoever touches the plugin to the guide's rules
    core = _parts()[0]
    assert 'Never hot-reload' in _section(core, "## Rules that protect the user's work")
    assert core.count('Never hot-reload') == 1


def test_the_file_level_pattern_comes_with_the_inheritance_numbers() -> None:
    # REVIEW.md TST-203: the API's numbers and the file's differ
    core, scripting = map(_flat, _parts())
    assert 'RelativeToInput 0' in scripting and 'A .sbs `<relativeTo>`: 0 absolute' in scripting
    assert 'RelativeToInput 0' not in core
    # REVIEW.md TST-215: with the pattern, not among the Qt notes
    assert 'RelativeToInput 0' in _section(_parts()[1], '## sd API gotchas')
    # REVIEW.md TST-222: an instance with no input isn't relative to input by default
    assert 'relative to input on a blur, relative to parent on an instance with no input' in scripting


def test_a_tools_only_agent_is_told_where_the_crash_dumps_are() -> None:
    # REVIEW.md TST-226
    core, scripting = map(_flat, _parts())
    assert 'Sentry-Crashpad/completed' in core and 'Sentry-Crashpad/completed' not in scripting


def test_apply_edits_says_what_it_refuses_for_a_size() -> None:
    # REVIEW.md HLP-87
    assert 'above 13 or below 0 is refused' in _flat(server.apply_edits.__doc__ or '')


def test_the_skill_doesnt_call_a_guide_only_fix_code() -> None:
    # REVIEW.md TST-223: AGENTS.md says docs changed alone need no live run
    assert '`mcp_server/` (not GUIDE.md alone, which is docs: AGENTS.md, Running the tests)' in _flat(
        _live_check_skill()
    )


def test_the_texts_say_which_part_of_the_guide_a_call_returns() -> None:
    # REVIEW.md SRV-101
    text = _flat(server.INSTRUCTIONS)
    assert 'core of the guide' in text and 'first sd pitfalls' in text and 'full guide' not in text
    assert 'every tool but cancel_designer_job' in _flat(server.get_guide.__doc__ or '')
    assert 'until then those two refuse' in _flat(_guide_md())
    assert "`get_guide('scripting')`" in _agents_md()[:600]
    readme = _flat(Path(ROOT, 'README.md').read_text(encoding='utf-8'))
    assert 'the server sends it to the agent automatically' not in readme
    assert 'the server serves the guide to the agent' in readme


@pytest.mark.parametrize('rule', ['never only under `if TYPE_CHECKING:`', 'from __future__ import annotations'])
def test_the_typing_rules_are_where_every_python_change_sees_them(rule: str) -> None:
    # REVIEW.md TST-206
    assert rule in _flat(_agents_md()) and rule not in _flat(_live_check_skill())


@pytest.mark.parametrize(
    'rule', ['A string of several lines is written `dedent', 'Tests that read source text match whitespace-tolerantly']
)
def test_the_rules_for_all_python_are_where_every_python_change_sees_them(rule: str) -> None:
    # REVIEW.md TST-216: they cover the server's modules and every unit test, not only live checks
    assert rule in _flat(_agents_md()) and rule not in _flat(_live_check_skill())


def test_no_doc_says_every_measured_fact_is_in_the_guide() -> None:
    # REVIEW.md TST-217: AGENTS.md's table sends what only a maintainer needs to the module
    decisions = _flat(Path(ROOT, 'DECISIONS.md').read_text(encoding='utf-8'))
    assert "Measured Designer behaviour lives in `GUIDE.md` or the module's docstring" in decisions
    assert "the Designer behaviour GUIDE.md or a module's docstring states" in _flat(_live_check_skill())


def test_agents_md_says_which_part_of_the_guide_a_fact_goes_in() -> None:
    # REVIEW.md TST-220: facts in the wrong part are how TST-203 and TST-205 came about
    assert (
        'the core if an agent using only the tools needs it or every script hits it on the first try, otherwise under `# Scripting`'
        in _flat(_agents_md())
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
        'caused no crash in five tries',
    ],
)
def test_a_claim_keeps_the_scope_it_was_measured_on(scope: str) -> None:
    # REVIEW.md TST-207
    assert scope in _flat(_guide_md())


def test_what_a_helper_cites_for_a_measurement_states_it() -> None:
    # REVIEW.md TST-207
    text = Path(ROOT, 'mcp_server', 'designer_helpers', 'graph_inputs.py').read_text(encoding='utf-8')
    assert (
        '(measured on all six on a levels node and `$outputsize` on an instance node, tests/test_all_tools/designer_scripts/facts/function_states.py)'
        in _flat(text)
    )


def test_address_review_sends_a_measured_fact_where_the_table_says() -> None:
    # REVIEW.md TST-208
    text = _flat(Path(ROOT, '.claude', 'skills', 'address-review', 'SKILL.md').read_text(encoding='utf-8'))
    assert text.count("GUIDE.md or the module's docstring, as AGENTS.md's table says") == 2


def test_small_text_defects_stay_fixed() -> None:
    # REVIEW.md TST-210
    core, _ = _parts()
    assert '\n\n## First sd pitfalls' in core
    guide = _flat(_guide_md())
    assert 'in its home)' not in guide and '`/tmp/sd_mcp_<uid>_<port>/home`' in guide
    assert 'It ends only a Designer an agent started' not in guide
    lifecycle = _flat(Path(ROOT, 'mcp_server', 'server_tools', 'lifecycle.py').read_text(encoding='utf-8'))
    assert 'a main thread frozen outside a job reads as idle' in lifecycle
    assert lifecycle.count('41 bytes') == 1, 'the socket is explained once'
    # REVIEW.md TST-215
    assert lifecycle.count('writes its `session.instancePID` there') == 1, 'the plist is explained once'


def test_the_guide_and_agents_md_point_to_each_other() -> None:
    assert 'mcp_server/GUIDE.md' in _agents_md()
    assert 'AGENTS.md' in _guide_md()


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
    assert fact not in _flat(_guide_md())
    assert fact in Path(ROOT, 'mcp_server', module).read_text(encoding='utf-8')


@pytest.mark.parametrize('module', ['server_tools/lifecycle.py', 'server_tools/layout.py'])
def test_the_guide_says_where_the_details_went(module: str) -> None:
    assert '`%s`' % module in _guide_md()


def test_no_link_points_to_agents_md_for_what_moved_to_the_guide() -> None:
    listed = subprocess.run(
        ['git', 'ls-files', '-co', '--exclude-standard'], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split('\n')
    link = re.compile(r"AGENTS\.md(?:'s)?(?:,\s*|\s*\(|\s+)(?:the\s+)?(?:%s)" % MOVED)
    stale = []
    for name in listed:
        # REVIEW.md's entries keep the wording they were written in
        if not name.endswith(('.md', '.py')) or name == 'REVIEW.md' or not Path(ROOT, name).is_file():
            continue
        stale += ['%s: %s' % (name, m.group(0)) for m in link.finditer(Path(ROOT, name).read_text(encoding='utf-8'))]
    assert not stale, stale


# the instructions limit; the atomic node count (not a ROADMAP item number `| 29 |` or an ID like HLP-29); where the
# record of a Designer an agent started is kept (REVIEW.md TST-159)
@pytest.mark.parametrize('fact', [r'4,096', r'(?<!\| )(?<!-)\b29\b(?! \|)', r'agent_designer_file\(port\)'])
def test_facts_are_stated_once_in_the_docs(fact: str) -> None:
    # AGENTS.md, Keeping the docs current: each fact in one place, linked from elsewhere (REVIEW.md TST-10,
    # TST-18)
    count = sum(
        len(re.findall(fact, Path(ROOT, name).read_text(encoding='utf-8')))
        for name in ('AGENTS.md', os.path.join('mcp_server', 'GUIDE.md'), 'README.md', 'ROADMAP.md')
    )
    assert count <= 1, '%r appears %d times in AGENTS.md, GUIDE.md, README.md and ROADMAP.md' % (fact, count)


def test_the_lifecycle_checks_that_run_alone_are_the_ones_the_skill_names() -> None:
    # REVIEW.md TST-168: the live-check skill (What a scratch run can't prove) names the lifecycle checks that do run alone; a
    # check saying so in its docstring and missing there, or named there without saying so, is a list gone stale
    import ast

    tree = ast.parse(Path(ROOT, 'tests', 'test_all_tools', 'lifecycle.py').read_text(encoding='utf-8'))
    say_so = {
        node.name
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name.startswith('check_')
        and 'runs in a scratch run too' in ' '.join((ast.get_docstring(node) or '').split())
    }
    bullet = re.search(
        r'^- \*\*`lifecycle\.py`, the whole category:\*\*(.*?)(?=^- \*\*)', _live_check_skill(), re.M | re.S
    )
    assert bullet, "the live-check skill's lifecycle bullet under What a scratch run can't prove"
    named = set(re.findall(r'`(check_\w+)`', bullet.group(1)))
    assert say_so and named == say_so, 'named in the skill: %s; saying so in their docstring: %s' % (
        sorted(named),
        sorted(say_so),
    )
