"""The server starts without Designer, and the docs list every tool it serves."""

import asyncio
import os
import re
import sys
from pathlib import Path
from typing import Any, cast

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult

import designer_helpers
from conftest import ROOT, patch_server, selftest_sources, server, server_source

SERVER = os.path.join(ROOT, 'mcp_server', 'server.py')


def _read(*parts: str) -> str:
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as f:
        return f.read()


async def _list_tools() -> tuple[str, dict[str, str]]:
    params = StdioServerParameters(command=sys.executable, args=[SERVER])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        init = await s.initialize()
        tools = (await s.list_tools()).tools
        global SCHEMAS
        SCHEMAS = {t.name: set((t.input_schema or {}).get('properties', {})) for t in tools}
        return init.instructions or '', {t.name: t.description or '' for t in tools}


TOOLS: tuple[str, dict[str, str]] | None = None
SCHEMAS: dict[str, set[str]] = {}


def _tools() -> tuple[str, dict[str, str]]:
    global TOOLS
    if TOOLS is None:
        TOOLS = asyncio.run(_list_tools())
    return TOOLS


def test_server_starts_and_points_to_the_guide() -> None:
    instructions, tools = _tools()
    assert 'get_guide()' in instructions and 'get_guide' in tools
    assert len(tools) > 30
    assert all(desc.strip() for desc in tools.values()), 'every tool needs a docstring'


def test_readme_tool_count_and_table() -> None:
    _, tools = _tools()
    readme = _read('README.md')
    assert '## Tools (%d)' % len(tools) in readme
    assert 'Defines the %d tools' % len(tools) in readme
    table = readme.split('## Tools', 1)[1].split('\n## ', 1)[0]
    missing = [t for t in tools if '`%s`' % t not in table]
    assert not missing, 'tools missing from README Tools table: %s' % missing


def test_designer_self_test_covers_every_tool() -> None:
    _, tools = _tools()
    selftest = '\n'.join(selftest_sources().values())
    called = set(re.findall(r"c\(\s*'(\w+)'", selftest))
    missing = sorted(set(tools) - called)
    assert not missing, 'tools without a check in tests/test_all_tools/: %s' % missing


def test_screenshots_never_grab_the_screen() -> None:
    # QScreen.grabWindow copies the screen area on macOS, capturing other apps (AGENTS.md, Screenshots)
    assert 'grabWindow' not in designer_helpers.source() and 'grabWindow' not in server_source()


def _selftest_calls() -> dict[str, set[str]]:
    """{tool: set of argument names} for every c('tool', {...}) call in the live self-test;
    **G counts as 'graph'."""
    import ast

    calls: dict[str, set[str]] = {}
    nodes = [n for source in selftest_sources().values() for n in ast.walk(ast.parse(source))]
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
    branches = re.split(r"\n\s+(?:el)?if kind == '(\w+)':", body.split('else:\n                raise', 1)[0])
    return {
        kind: {a or b for a, b in re.findall(r"op(?:\['(\w+)'\]|\.get\('(\w+)')", code)}
        for kind, code in zip(branches[1::2], branches[2::2], strict=False)
    }


def test_every_apply_edits_op_is_exercised_live() -> None:
    ops = set(re.findall(r"\{\s*'op': '(\w+)'", '\n'.join(selftest_sources().values())))
    dispatched = set(_dispatched_ops())
    assert dispatched and dispatched <= ops, 'apply_edits ops never run live: %s' % sorted(dispatched - ops)


def test_apply_edits_docstring_lists_every_op_and_field() -> None:
    text = server_source().split('def apply_edits(', 1)[1].split('Refs let', 1)[0]
    doc = {
        m.group(1): set(re.findall(r'"(\w+)"\??:', m.group(0))) - {'op'}
        for m in re.finditer(r'\{"op": "(\w+)"[^{]*', text)
    }
    for kind, fields in _dispatched_ops().items():
        assert kind in doc, 'apply_edits op %r is not in the docstring' % kind
        assert fields <= doc[kind], 'apply_edits %r: fields %s not in the docstring' % (
            kind,
            sorted(fields - doc[kind]),
        )


def test_relative_paths_are_resolved_here_not_in_designer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # REVIEW.md SRV-27: these went to Designer as given and were resolved against Designer's working
    # directory (`/` when started from the Finder), unlike render_sbs or preview_maps
    sent: list[str] = []

    def bridge(code: str, *a: Any, **kw: Any) -> str:
        sent.append(code)
        return 'ok'

    patch_server(monkeypatch, '_bridge', bridge)
    monkeypatch.chdir(tmp_path)
    here = str(tmp_path)
    server.export_outputs('Mat', 'renders')
    server.save_package('Mat', 'out/mat.sbs')
    server.save_package('pkg.sbs')
    server.import_bitmap('ref.png', graph='Mat')
    server.create_graph('Mat2', save_path='mat2.sbs')
    server.apply_edits([{'op': 'bitmap', 'path': 'img.png', 'ref': 'i'}], graph='Mat')
    for name in ('renders', 'out/mat.sbs', 'pkg.sbs', 'ref.png', 'mat2.sbs', 'img.png'):
        # the absolute path, however the call is quoted (an edit wraps it in one more string)
        assert any(os.path.join(here, name) in code for code in sent), (name, [c[-200:] for c in sent])
    server.save_package('Mat')  # a graph identifier stays as it is
    assert "'Mat'" in sent[-1] and os.path.join(here, 'Mat') not in sent[-1]


def test_a_tool_calling_another_tool_shows_the_guide_reminder_once(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-28: set_link_display pastes snapshot_graph's and open_graph's results into its
    # own, so before get_guide() the reminder appeared twice
    from types import SimpleNamespace

    from server_tools.core import _tool  # server._tool itself, with its type

    patch_server(monkeypatch, 'server', SimpleNamespace(tool=lambda: lambda fn: fn))  # no registration
    monkeypatch.setitem(server._session, 'guide_read', False)

    @_tool()
    def inner() -> str:
        return 'inner result'

    @_tool()
    def outer() -> str:
        return 'outer, with ' + inner()

    assert outer().count(server.GUIDE_NOT_READ) == 1
    assert inner().startswith(server.GUIDE_NOT_READ)  # called on its own it still has one


def test_a_failed_reload_says_the_package_was_closed_and_where_it_is(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-29: after the unload, a failing load left the user's package closed in Designer,
    # and the error gave only Designer's last line
    import pytest

    answers = iter(['unloaded 1 package(s): /p/mat.sbs', '--- ERROR ---\nRuntimeError: cannot read /p/mat.sbs'])
    patch_server(monkeypatch, '_bridge', lambda code, *a, **kw: next(answers))
    patch_server(monkeypatch, 'RELOAD_SETTLE_S', 0)
    with pytest.raises(server.ToolError) as error:
        server._reload_package_file('/p/mat.sbs', '/snaps/mat_before.sbs')
    message = str(error.value)
    assert (
        'cannot read' in message
        and 'closed' in message
        and '/p/mat.sbs' in message
        and '/snaps/mat_before.sbs' in message
    ), message


def test_a_sweep_with_no_values_is_refused_before_designer(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-30: values=[] produced no images and failed with "restored X.p to ..." as the error
    import pytest

    sent: list[str] = []

    def bridge(code: str, *a: Any, **kw: Any) -> str:
        sent.append(code)
        return ''

    patch_server(monkeypatch, '_bridge', bridge)
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
