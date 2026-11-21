"""The server starts without Designer, and the docs list every tool it serves."""

import asyncio
import inspect
import json
import os
import re
import sys
from pathlib import Path
from typing import cast, get_args

import pytest
from docs_text import guide_md, read
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult, ToolAnnotations
from pydantic.fields import FieldInfo

import designer_helpers
from conftest import (
    ROOT,
    SELFTEST_DIR,
    fake_bridge,
    patch_server,
    selftest_check_sources,
    selftest_sources,
    server,
    server_source,
)
from project_constants import Json

SERVER = os.path.join(ROOT, 'mcp_server', 'server.py')
# Claude Code keeps this many characters of a server's instructions (measured: the guide arrived cut at exactly this
# many), and of a tool's description when the tool loads at the session's start (its MCP docs, "Tool search for MCP
# server authors")
CLAUDE_CODE_LIMIT = 4096


async def _list_tools() -> tuple[str, dict[str, str]]:
    params = StdioServerParameters(command=sys.executable, args=[SERVER])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        init = await s.initialize()
        tools = (await s.list_tools()).tools
        global SCHEMAS, PROPERTIES, ANNOTATIONS
        SCHEMAS = {t.name: set((t.input_schema or {}).get('properties', {})) for t in tools}
        PROPERTIES = {t.name: (t.input_schema or {}).get('properties', {}) for t in tools}
        ANNOTATIONS = {t.name: _hints(t.annotations) for t in tools}
        return init.instructions or '', {t.name: t.description or '' for t in tools}


Hints = tuple[bool | None, bool | None, bool | None, bool | None]  # readOnly, destructive, idempotent, openWorld
TOOLS: tuple[str, dict[str, str]] | None = None
SCHEMAS: dict[str, set[str]] = {}
PROPERTIES: dict[str, dict[str, Json]] = {}  # each tool's parameters' JSON schemas
ANNOTATIONS: dict[str, Hints] = {}  # each tool's four hints, as the client reads them


def _hints(annotations: ToolAnnotations | None) -> Hints:
    a = annotations or ToolAnnotations()
    return a.read_only_hint, a.destructive_hint, a.idempotent_hint, a.open_world_hint


def _tools() -> tuple[str, dict[str, str]]:
    global TOOLS
    if TOOLS is None:
        TOOLS = asyncio.run(_list_tools())
    return TOOLS


def _described(tool: str, name: str) -> str:
    """The description a tool's parameter is given in its annotation (`Field(description=...)`)."""
    annotation = inspect.signature(getattr(server, tool)).parameters[name].annotation
    field = next(meta for meta in get_args(annotation)[1:] if isinstance(meta, FieldInfo))
    return field.description or ''


def test_server_starts_and_points_to_the_guide() -> None:
    instructions, tools = _tools()
    assert 'get_guide()' in instructions and 'get_guide' in tools
    assert len(tools) > 30
    assert all(desc.strip() for desc in tools.values()), 'every tool needs a docstring'


def test_every_tool_parameter_is_described_in_its_schema() -> None:
    # ROADMAP item 38: a client shows the schema's parameters, so each says what it means (its annotation's
    # Field(description=...)); the docstring keeps what the tool does
    _tools()
    missing = sorted(
        '%s(%s)' % (tool, name)
        for tool, params in PROPERTIES.items()
        for name, schema in params.items()
        if not (isinstance(schema, dict) and isinstance(text := schema.get('description'), str) and text.strip())
    )
    assert not missing, 'parameters without a description in their schema: %s' % missing


def test_no_tool_description_is_cut_by_claude_code() -> None:
    # Claude Code cuts the description of a tool loaded at the session's start (CLAUDE_CODE_LIMIT)
    _, tools = _tools()
    long = {name: len(text) for name, text in tools.items() if len(text) > CLAUDE_CODE_LIMIT}
    assert not long, 'tool descriptions over %d characters: %s' % (CLAUDE_CODE_LIMIT, long)


def test_no_tool_description_keeps_its_docstrings_indentation() -> None:
    # The SDK sends a tool's raw __doc__ unless it is given a description, and each line after the first keeps the
    # docstring's indentation, which agents pay for in every listing: _tool() gives it cleaned
    _, tools = _tools()
    indented = sorted(name for name, text in tools.items() if text != inspect.cleandoc(text))
    assert not indented, "tool descriptions with their docstring's indentation: %s" % indented


def test_readme_tool_count_and_table() -> None:
    _, tools = _tools()
    readme = read('README.md')
    assert '## Tools (%d)' % len(tools) in readme
    assert 'Defines the %d tools' % len(tools) in readme
    table = readme.split('## Tools', 1)[1].split('\n## ', 1)[0]
    missing = [t for t in tools if '`%s`' % t not in table]
    assert not missing, 'tools missing from README Tools table: %s' % missing


# Each tool's hints: (readOnlyHint, destructiveHint, idempotentHint, openWorldHint). How each is chosen: _tool()'s
# docstring (mcp_server/server_tools/core.py).
HINTS: dict[str, Hints] = {
    # read-only
    'get_guide': (True, False, True, False),
    'designer_status': (True, False, True, False),
    'read_designer_log': (True, False, True, False),
    'search_nodes': (True, False, True, False),
    'describe_node': (True, False, True, False),
    'describe_graph': (True, False, True, False),
    'list_graph_inputs': (True, False, True, False),
    'list_snapshots': (True, False, True, False),
    'diff_graph': (True, False, True, False),
    'sbsar_info': (True, False, True, False),
    'preview_maps': (True, False, True, False),
    # destructive: they can overwrite or remove the user's work or files
    'quit_designer': (False, True, True, False),
    'arrange_graph': (False, True, True, False),
    'set_link_display': (False, True, False, False),
    'apply_edits': (False, True, False, False),
    'create_graph': (False, True, False, False),
    'set_graph_size': (False, True, True, False),
    'remove_graph_input': (False, True, True, False),
    'execute_designer_code': (False, True, False, True),
    'run_designer_script': (False, True, False, True),
    'save_package': (False, True, True, False),
    'export_outputs': (False, True, True, False),
    'render_sbs': (False, True, True, False),
    # neither read-only nor destructive
    'launch_designer': (False, False, True, False),
    'cancel_designer_job': (False, False, True, False),
    'sweep_param': (False, False, True, False),
    'preview_node': (False, False, True, False),
    'node_stats': (False, False, True, False),
    'check_tiling': (False, False, True, False),
    'compare_to_reference': (False, False, True, False),
    'snapshot_graph': (False, False, False, False),
    'add_frame': (False, False, False, False),
    'add_comment': (False, False, False, False),
    'screenshot_designer': (False, False, False, False),
    'open_graph': (False, False, True, False),
}


def test_every_tool_declares_its_four_hints() -> None:
    _tools()
    missing = sorted(name for name, hints in ANNOTATIONS.items() if None in hints)
    assert not missing, 'tools without all four hints: %s' % missing
    assert ANNOTATIONS == HINTS


def test_readme_lists_every_category_the_self_test_runs() -> None:
    # the names --only takes (README, Self-test): one row each, no other
    categories = {p.parent.name for p in Path(SELFTEST_DIR).glob('*/checks.py')}
    section = read('README.md').split('### The categories', 1)[-1].split('\n## ', 1)[0].split('\n### ', 1)[0]
    listed: list[str] = re.findall(r'^\| `(\w+)` \|', section, re.M)
    assert len(listed) == len(set(listed)) and set(listed) == categories, sorted(categories ^ set(listed))


def test_designer_self_test_covers_every_tool() -> None:
    _, tools = _tools()
    selftest = '\n'.join(selftest_check_sources().values())
    called = set(re.findall(r"c\(\s*'(\w+)'", selftest))
    missing = sorted(set(tools) - called)
    assert not missing, 'tools without a check in tests/test_all_tools/: %s' % missing


def test_screenshots_never_grab_the_screen() -> None:
    # QScreen.grabWindow copies the screen area on macOS, capturing other apps (GUIDE.md, Screenshots)
    assert 'grabWindow' not in designer_helpers.source() and 'grabWindow' not in server_source()


def _selftest_calls() -> dict[str, set[str]]:
    """{tool: set of argument names} for every c('tool', {...}) call in the live self-test;
    **G counts as 'graph'."""
    import ast

    calls: dict[str, set[str]] = {}
    nodes = [n for source in selftest_check_sources().values() for n in ast.walk(ast.parse(source))]
    for node in nodes:
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, 'id', None) == 'c'
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            names = calls.setdefault(cast(str, node.args[0].value), set())
            if len(node.args) > 1 and getattr(node.args[1], 'id', None) == 'G':  # c('tool', G)
                names.add('graph')
            if len(node.args) > 1 and isinstance(node.args[1], ast.Dict):
                for key in node.args[1].keys:
                    names.add(
                        'graph' if key is None else cast(str, key.value) if isinstance(key, ast.Constant) else '?'
                    )
    return calls


def test_every_tool_parameter_is_exercised_live() -> None:
    # AGENTS.md: a new parameter needs a check, not just a docstring line
    _tools()
    calls = _selftest_calls()
    missing = sorted(
        '%s(%s)' % (tool, p) for tool, params in SCHEMAS.items() for p in params if p not in calls.get(tool, set())
    )
    assert not missing, 'parameters never passed by tests/test_all_tools/: %s' % missing


def _dispatched_ops() -> dict[str, set[str]]:
    """apply_edits op -> the op fields its branch reads, from the helpers' dispatcher (the code
    that runs), not from the docstring (REVIEW.md TST-6)."""
    body = designer_helpers.source().split('def apply_edits(', 1)[1].split('\ndef ', 1)[0]
    parts = re.split(r'\n\s+else:[^\n]*\n\s+raise', body, maxsplit=1)
    # the dispatcher ends at its else branch; without it the last op would take in the rest of
    # apply_edits (REVIEW.md TST-83)
    assert len(parts) == 2, "apply_edits' dispatcher has no `else: raise` branch to end at"
    branches = re.split(r"\n\s+(?:el)?if kind == '(\w+)':", parts[0])
    return {
        kind: {a or b for a, b in re.findall(r"op(?:\['(\w+)'\]|\.get\('(\w+)')", code)}
        for kind, code in zip(branches[1::2], branches[2::2], strict=False)
    }


def test_every_apply_edits_op_is_passed_live() -> None:
    # passed, not necessarily run: a batch the pre-check refuses counts too (REVIEW.md TST-92, as TST-88)
    ops = set(re.findall(r"\{\s*'op': '(\w+)'", '\n'.join(selftest_sources().values())))
    dispatched = set(_dispatched_ops())
    assert dispatched and dispatched <= ops, 'apply_edits ops never run live: %s' % sorted(dispatched - ops)


def _selftest_op_fields() -> dict[str, set[str]]:
    """apply_edits op -> the fields the self-test passes in literal op dicts ({'op': 'set', ...}),
    comprehensions included. Passed, not necessarily run: a batch the pre-check refuses counts too
    (REVIEW.md TST-88), so a field needs a batch that runs as well, which the reviews check by hand."""
    import ast

    fields: dict[str, set[str]] = {}
    for source in selftest_sources().values():
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Dict):
                continue
            keys = [k.value if isinstance(k, ast.Constant) else None for k in node.keys]
            if 'op' not in keys:
                continue
            kind = node.values[keys.index('op')]
            if isinstance(kind, ast.Constant) and isinstance(kind.value, str):
                fields.setdefault(kind.value, set()).update(cast(str, k) for k in keys if k not in (None, 'op'))
    return fields


def test_every_apply_edits_op_field_is_passed_live() -> None:
    # what test_every_tool_parameter_is_exercised_live did for the single-edit tools apply_edits replaced
    passed = _selftest_op_fields()
    missing = sorted(
        '%s.%s' % (kind, f) for kind, fields in _dispatched_ops().items() for f in fields - passed.get(kind, set())
    )
    assert not missing, 'apply_edits op fields never passed by tests/test_all_tools/: %s' % missing


def test_apply_edits_checks_the_node_fields_of_every_op() -> None:
    # the pre-check (_check_batch) knows every op the dispatcher runs and checks each field that names
    # a node; an op or a node field added only to the dispatcher would run unchecked
    import ast

    block = designer_helpers.source().split('_NODE_FIELDS: dict[str, tuple[str, ...]] = ', 1)[1].split('\n}', 1)[0]
    node_fields = cast(dict[str, tuple[str, ...]], ast.literal_eval(block + '\n}'))
    dispatched = _dispatched_ops()
    assert dispatched and set(node_fields) == set(dispatched)
    for kind, fields in dispatched.items():
        assert fields & {'node', 'from', 'to'} == set(node_fields[kind]), (kind, fields, node_fields[kind])


def test_apply_edits_ops_description_lists_every_op_and_field() -> None:
    # the ops' grammar: an op's line starts with {"op", and its next lines with a space
    doc = {
        m.group(1): set(re.findall(r'"(\w+)"\??:', m.group(0))) - {'op'}
        for m in re.finditer(r'^\{"op": "(\w+)".*(?:\n .*)*', _described('apply_edits', 'ops'), re.M)
    }
    for kind, fields in _dispatched_ops().items():
        assert kind in doc, "apply_edits op %r is not in ops' description" % kind
        assert fields <= doc[kind], "apply_edits %r: fields %s not in ops' description" % (
            kind,
            sorted(fields - doc[kind]),
        )


def test_relative_paths_are_resolved_here_not_in_designer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md SRV-27: these went to Designer as given and were resolved against Designer's working
    # directory (`/` when started from the Finder), unlike render_sbs or preview_maps
    sent: list[str] = []

    def bridge(code: str) -> str:
        sent.append(code)
        return 'ok'

    fake_bridge(monkeypatch, bridge)
    monkeypatch.chdir(tmp_path)
    here = str(tmp_path)
    server.export_outputs('renders', graph='Mat')
    server.save_package('Mat', 'out/mat.sbs')
    server.save_package('pkg.sbs')
    server.create_graph('Mat2', save_path='mat2.sbs')
    server.apply_edits([{'op': 'bitmap', 'path': 'img.png', 'ref': 'i'}], graph='Mat')
    for name in ('renders', 'out/mat.sbs', 'pkg.sbs', 'mat2.sbs', 'img.png'):
        # the absolute path, however the call is quoted (an edit wraps it in one more string)
        assert any(os.path.join(here, name) in code for code in sent), (name, [c[-200:] for c in sent])
    server.save_package('Mat')  # a graph identifier stays as it is
    assert "'Mat'" in sent[-1] and os.path.join(here, 'Mat') not in sent[-1]


def test_a_failed_reload_says_the_package_was_closed_and_where_it_is(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-29: after the unload, a failing load left the user's package closed in Designer,
    # and the error gave only Designer's last line
    import pytest

    answers = iter(['unloaded 1 package(s): /p/mat.sbs', '--- ERROR ---\nRuntimeError: cannot read /p/mat.sbs'])
    fake_bridge(monkeypatch, lambda code: next(answers))
    with pytest.raises(server.ToolError) as error:
        server._reload_package_file('/p/mat.sbs', '/snaps/mat_before.sbs')
    message = str(error.value)
    assert (
        'cannot read' in message
        and 'closed' in message
        and '/p/mat.sbs' in message
        and '/snaps/mat_before.sbs' in message
    ), message


def test_a_failed_reloads_message_keeps_its_own_period(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-117: the bridge's own errors end in one, which the sentence after it doubled
    import pytest

    said = 'Designer closed the connection without a reply (it may be starting or quitting).'
    calls: list[str] = []

    def bridge(code: str) -> str:  # the unload, then the load
        calls.append(code)
        if len(calls) == 1:
            return 'unloaded 1 package(s): /p/mat.sbs'
        raise server.ToolError(said)

    fake_bridge(monkeypatch, bridge)
    with pytest.raises(server.ToolError) as error:
        server._reload_package_file('/p/mat.sbs')
    assert str(error.value).startswith(said + ' The package was closed in Designer'), str(error.value)


def test_a_sweep_with_no_values_is_refused_before_designer(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-30: values=[] produced no images and failed with "restored X.p to ..." as the error
    import pytest

    sent: list[str] = []

    def bridge(code: str) -> str:
        sent.append(code)
        return ''

    fake_bridge(monkeypatch, bridge)
    with pytest.raises(server.ToolError) as error:
        server.sweep_param('n1', 'scale', [])
    assert 'values' in str(error.value) and not sent


@pytest.mark.parametrize('content', [None, 'not xml at all'])
def test_diff_graph_explains_a_missing_or_unreadable_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, content: str | None
) -> None:
    # REVIEW.md SRV-30: against='/missing.sbs' raised a raw FileNotFoundError (or ParseError)
    ref = tmp_path / 'other.sbs'
    if content is not None:
        ref.write_text(content)
    patch_server(monkeypatch, '_copy_package', lambda graph, path: {'GRAPH': 'Mat'})
    with pytest.raises(server.ToolError) as error:
        server.diff_graph('Mat', against=str(ref))
    assert str(ref) in str(error.value)


@pytest.mark.skipif(not (server.SBSCOOKER and server.SBSRENDER), reason='needs sbscooker/sbsrender')
def test_render_sbs_keeps_every_graphs_maps_when_names_repeat(tmp_path: Path) -> None:
    # REVIEW.md SRV-26: without `graph`, every graph rendered as {outputNodeName}, so two graphs with
    # an output of the same name wrote one file and the count said 1
    out = tmp_path / 'maps'
    text = server.render_sbs(os.path.join(ROOT, 'tests', 'unit', 'fixtures', 'two_graphs_same_output.sbs'), str(out))
    assert sorted(os.listdir(out)) == ['first_output.png', 'second_output.png'], text
    assert 'Rendered 2 file(s)' in text


def test_every_server_module_is_loaded_and_re_exported() -> None:
    # a module missing from server_tools.MODULES would be left out of server.py's re-exports (and of
    # patch_server); one never imported would register none of its tools
    import server_tools

    folder = os.path.dirname(server_tools.__file__)
    files = sorted(f[:-3] for f in os.listdir(folder) if f.endswith('.py') and f != '__init__.py')
    assert sorted(m.__name__.split('.')[-1] for m in server_tools.MODULES) == files
    _, tools = _tools()
    assert all(callable(getattr(server, name, None)) for name in tools), 'tools not re-exported by server.py'


def test_tools_returning_images_have_no_output_schema() -> None:
    """MCP renders a result as content blocks (text + images) only when the return annotation names
    the content types: `-> list[Any]` made it dump sweep_param's image as structured data, which
    failed for every call; `-> list[str | Image]` keeps it content."""
    from mcp.server.mcpserver import Image

    from server_tools.core import server as mcp_server

    tools = asyncio.run(mcp_server.list_tools())
    returning_images = [t for t in tools if 'Image' in repr(getattr(server, t.name).__annotations__.get('return'))]
    assert {'sweep_param', 'compare_to_reference', 'preview_node'} <= {t.name for t in returning_images}
    for t in returning_images:
        assert t.output_schema is None, '%s returns images but gets structured output' % t.name
    # and a result of such a tool converts to text and image blocks
    tool = mcp_server._tool_manager.get_tool('sweep_param')
    assert tool is not None
    image = Image(data=b'\x89PNG\r\n\x1a\n', format='png')
    result = tool.fn_metadata.convert_result(['text', image])
    assert isinstance(result, CallToolResult) and result.structured_content is None
    assert [b.type for b in result.content] == ['text', 'image']


def test_every_tools_graph_can_be_left_out_except_open_graphs(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-53: the library refusal says read tools work with no graph given (the graph in focus), and
    # export_outputs asked for one. open_graph is the one exception: the refusal says it can't reach that graph
    import inspect

    from server_tools.core import server as mcp_server

    tools = asyncio.run(mcp_server.list_tools())
    signatures = {t.name: inspect.signature(getattr(server, t.name)).parameters for t in tools}
    with_graph = {name: p['graph'] for name, p in signatures.items() if 'graph' in p}
    assert len(with_graph) >= 20  # the check still sees them
    assert {n for n, p in with_graph.items() if p.default is inspect.Parameter.empty} == {'open_graph'}
    sent: list[str] = []

    def bridge(code: str) -> str:
        sent.append(code)
        return 'ok'

    fake_bridge(monkeypatch, bridge)
    server.export_outputs('/tmp/renders')
    assert "export_outputs(None, '/tmp/renders'," in sent[-1]


def _op_fields() -> dict[str, tuple[str, ...]]:
    """_OP_FIELDS, read from the helpers' source."""
    import ast

    block = re.search(r'_OP_FIELDS[^=]*= (\{.*?\n\})', designer_helpers.source(), re.S)
    assert block is not None, 'no _OP_FIELDS table in batch.py'
    return cast(dict[str, tuple[str, ...]], ast.literal_eval(block.group(1)))


def test_the_op_fields_are_the_ones_each_op_reads() -> None:
    # REVIEW.md HLP-62: the table the pre-check refuses by can't drift from what the ops use
    assert {k: set(v) for k, v in _op_fields().items()} == _dispatched_ops()


def test_the_self_test_passes_no_field_an_op_doesnt_take() -> None:
    # how from_output went unnoticed (TST-113)
    allowed = _op_fields()
    # kinds outside the table are the self-test's own unknown-op checks
    passed = {k: v for k, v in _selftest_op_fields().items() if k in allowed}
    wrong = {k: sorted(v - set(allowed[k])) for k, v in passed.items() if v - set(allowed[k])}
    # the one on purpose: the self-test's batch/checks.py check that such a field is refused
    assert wrong == {'add': ['postion']}, 'op fields no op takes, in tests/test_all_tools/: %s' % wrong


def _sent_by_script(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source: str, args: dict[str, Json] | None
) -> tuple[str, Json]:
    """What run_designer_script sends for this script, and the ARGS that text defines."""
    sent: list[str] = []

    def bridge(code: str) -> str:
        sent.append(code)
        return 'ok'

    fake_bridge(monkeypatch, bridge)
    script = tmp_path / 'probe.py'
    script.write_text(source, encoding='utf-8')
    server.run_designer_script(str(script), args=args)
    scope: dict[str, object] = {}
    exec(sent[0].split('\n', 1)[0], scope)
    return sent[0], cast(Json, scope['ARGS'])  # the first line sets ARGS with json.loads


def test_run_designer_script_passes_args(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    args: dict[str, Json] = {'name': 'it\'s "quoted" → é', 'ids': [1, 2.5, None, True], 'nested': {'a': 'b\nc'}}
    _, received = _sent_by_script(monkeypatch, tmp_path, 'print(1)\n', args)
    assert received == args


def test_run_designer_script_args_default_to_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _, received = _sent_by_script(monkeypatch, tmp_path, 'print(1)\n', None)
    assert received == {}


def test_run_designer_script_args_leave_the_script_text_alone(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The script is compiled on its own, so the line numbers in its tracebacks stay its own."""
    source = 'first = 1\nraise ValueError("line 2")\n'
    code, _ = _sent_by_script(monkeypatch, tmp_path, source, {'a': 1})
    assert repr(source) in code


def test_the_fallback_client_sends_no_args() -> None:
    """GUIDE.md: a script reading ARGS runs through the MCP tool, not client/sd_run.py (REVIEW.md SRV-62)."""
    assert 'ARGS' not in read('client', 'sd_run.py')
    assert 'no `ARGS`' in guide_md()


# The JSON parameters' schemas, as agents saw them before the parameters were typed as pydantic's JsonValue, which
# would describe each nested value (ROADMAP item 98). The test adds beside them the description each one's annotation
# gives.
_PINNED: dict[tuple[str, str], dict[str, Json]] = {
    ('apply_edits', 'ops'): {
        'items': {'additionalProperties': True, 'type': 'object'},
        'title': 'Ops',
        'type': 'array',
    },
    ('sweep_param', 'values'): {'items': {}, 'title': 'Values', 'type': 'array'},
    ('run_designer_script', 'args'): {
        'anyOf': [{'additionalProperties': True, 'type': 'object'}, {'type': 'null'}],
        'default': None,
        'title': 'Args',
    },
}


@pytest.mark.parametrize(('tool', 'name'), list(_PINNED), ids=['%s.%s' % key for key in _PINNED])
def test_the_json_parameters_keep_the_schemas_agents_saw(tool: str, name: str) -> None:
    # REVIEW.md TST-485: the schemas were said to be pinned, with no test
    _tools()
    assert PROPERTIES[tool][name] == {**_PINNED[(tool, name)], 'description': _described(tool, name)}


# The parameters that take a fixed number of values (their descriptions), and the least and most their schemas allow; for a
# list of such items, those of each item; and the array parameters that take any number (REVIEW.md SRV-177)
_FIXED: dict[tuple[str, str], tuple[int, int, str]] = {  # (least, most, the values' JSON type)
    ('add_comment', 'position'): (2, 2, 'number'),
    ('add_frame', 'color'): (3, 4, 'number'),
    ('arrange_graph', 'spacing'): (2, 2, 'number'),
    ('compare_to_reference', 'region'): (4, 4, 'integer'),
    ('compare_to_reference', 'reference_region'): (4, 4, 'integer'),
    ('node_stats', 'region'): (4, 4, 'integer'),
    ('open_graph', 'rect'): (4, 4, 'number'),
    ('preview_maps', 'crop'): (4, 4, 'integer'),
    ('screenshot_designer', 'crop'): (4, 4, 'number'),
    ('screenshot_designer', 'orbit'): (2, 2, 'number'),
    ('screenshot_designer', 'pan'): (2, 2, 'number'),
}
_FIXED_ITEMS: dict[tuple[str, str], tuple[int, int, str]] = {  # the same, of each item
    ('node_stats', 'points'): (2, 2, 'integer'),
    ('set_link_display', 'links'): (2, 2, 'string'),
}
_A_VALUE: dict[str, Json] = {'integer': 1, 'number': 1, 'string': 'a'}  # one of each JSON type
_ANY_LENGTH = {
    ('add_frame', 'node_ids'),
    ('apply_edits', 'ops'),
    ('arrange_graph', 'node_ids'),
    ('describe_graph', 'node_ids'),
    ('export_outputs', 'outputs'),
    ('open_graph', 'node_ids'),
    ('preview_maps', 'names'),
    ('render_sbs', 'outputs'),
    ('set_link_display', 'from_nodes'),
    ('sweep_param', 'values'),
}


def _arrays(schema: Json) -> list[dict[str, Json]]:
    """The array forms a parameter's schema allows, its null left out."""
    assert isinstance(schema, dict)
    forms = schema.get('anyOf', [schema])
    assert isinstance(forms, list)
    return [f for f in forms if isinstance(f, dict) and f.get('type') == 'array']


def _bounds(array: dict[str, Json]) -> tuple[Json, Json, Json]:
    """The least and most items an array schema allows, None where it sets none, and its items' JSON type."""
    items = array.get('items')
    return array.get('minItems'), array.get('maxItems'), items.get('type') if isinstance(items, dict) else None


def test_every_array_parameter_says_how_many_values_it_takes() -> None:
    """A new parameter of a fixed number of values typed `list[...]` would let any number through (REVIEW.md SRV-177):
    each array parameter is one of the three kinds above, and those taking any number say no bound."""
    _tools()
    arrays = {(tool, name) for tool, params in PROPERTIES.items() for name, s in params.items() if _arrays(s)}
    assert arrays == set(_FIXED) | set(_FIXED_ITEMS) | _ANY_LENGTH
    assert all(_bounds(a)[:2] == (None, None) for key in _ANY_LENGTH for a in _arrays(PROPERTIES[key[0]][key[1]]))


@pytest.mark.parametrize(('tool', 'name'), list(_FIXED), ids=['%s.%s' % key for key in _FIXED])
def test_a_parameter_of_a_fixed_length_says_it_in_its_schema(tool: str, name: str) -> None:
    _tools()
    assert [_bounds(a) for a in _arrays(PROPERTIES[tool][name])] == [_FIXED[(tool, name)]]


@pytest.mark.parametrize(('tool', 'name'), list(_FIXED_ITEMS), ids=['%s.%s' % key for key in _FIXED_ITEMS])
def test_a_list_of_items_of_a_fixed_length_says_it_in_its_schema(tool: str, name: str) -> None:
    _tools()
    (array,) = _arrays(PROPERTIES[tool][name])
    items = array.get('items')
    assert (
        _bounds(array)[:2] == (None, None) and isinstance(items, dict) and _bounds(items) == _FIXED_ITEMS[(tool, name)]
    )


# What each of those tools needs besides the parameter tested
_REQUIRED: dict[str, dict[str, Json]] = {
    'add_comment': {'text': 't'},
    'add_frame': {'node_ids': ['a'], 'title': 't'},
    'arrange_graph': {},
    'compare_to_reference': {'node_id': 'n', 'reference_path': 'r.png'},
    'node_stats': {'node_id': 'n'},
    'open_graph': {'graph': 'g'},
    'preview_maps': {'map_dir': '.'},
    'screenshot_designer': {},
    'set_link_display': {},
}


def _wrong_counts() -> list[tuple[str, str, Json]]:
    """(tool, parameter, value) for each parameter of a fixed number of values: one value too few and one too many; for a
    list of such items, one item of each. The schema tests read only the published schema, and the tuple type alone
    refuses (REVIEW.md TST-535)."""
    cases: list[tuple[str, str, Json]] = []
    for (tool, name), (least, most, kind) in _FIXED.items():  # values of the right type: refused for their number
        for n in (least - 1, most + 1):
            values: list[Json] = [_A_VALUE[kind]] * n
            cases.append((tool, name, values))
    for (tool, name), (least, most, kind) in _FIXED_ITEMS.items():
        for n in (least - 1, most + 1):
            items: list[Json] = [[_A_VALUE[kind]] * n]
            cases.append((tool, name, items))
    return cases


_WRONG_COUNTS = _wrong_counts()


@pytest.mark.parametrize(
    ('tool', 'name', 'value'), _WRONG_COUNTS, ids=['%s.%s=%s' % (t, n, json.dumps(v)) for t, n, v in _WRONG_COUNTS]
)
def test_a_wrong_number_of_values_is_refused_before_anything_reaches_designer(
    sent: list[str], tool: str, name: str, value: Json
) -> None:
    """The schema refuses it with a message naming the parameter. Read in the tool, `for x, y in points` refused a point
    of 3 with 'too many values to unpack', which didn't say what was wrong (REVIEW.md SRV-177)."""
    with pytest.raises(server.ToolError, match=r'validation error(.|\n)*%s' % name):
        asyncio.run(server.server.call_tool(tool, {**_REQUIRED[tool], name: value}))
    assert sent == []


@pytest.mark.parametrize(('tool', 'name'), list(_FIXED), ids=['%s.%s' % key for key in _FIXED])
def test_an_empty_array_is_taken_as_not_given(tool: str, name: str) -> None:
    """A client filling optional fields with empty values sends [] for one it doesn't give: main took it so (`if region:`),
    and the tuple types refused it (REVIEW.md SRV-178; SRV-147 for strings)."""
    found = server.server._tool_manager.get_tool(tool)
    assert found is not None
    arguments = found.fn_metadata.arg_model.model_validate({**_REQUIRED[tool], name: []})
    assert getattr(arguments, name) is None


@pytest.mark.parametrize(
    ('arguments', 'sent_as'),
    [
        ({'frame': ''}, 'None, None, None, None'),
        ({'node_ids': ['a', 'b'], 'frame': ''}, "None, ['a', 'b'], None, None"),
        ({'node_id': '', 'node_ids': [], 'frame': 'Shape'}, "None, None, 'Shape', None"),
    ],
    ids=['an empty frame', 'nodes and an empty frame', 'a frame and empty others'],
)
def test_open_graph_sends_an_empty_choice_as_not_given(
    sent: list[str], arguments: dict[str, Json], sent_as: str
) -> None:
    """'' or [] for node_id, node_ids or frame is not given, as the check of one choice counts it (SRV-147's rule): the
    helper took frame='' as a frame titled '' and refused it (REVIEW.md SRV-180)."""
    asyncio.run(server.server.call_tool('open_graph', {'graph': 'g', **arguments}))
    assert sent and sent[0].rstrip('\n').endswith("open_graph('g', %s)" % sent_as), sent[-1:]
