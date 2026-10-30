"""The server starts without Designer, and the docs list every tool it serves."""
import asyncio
import os
import re
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from conftest import ROOT

SERVER = os.path.join(ROOT, 'mcp_server', 'server.py')


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as f:
        return f.read()


async def _list_tools():
    params = StdioServerParameters(command=sys.executable, args=[SERVER])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            tools = (await s.list_tools()).tools
            global SCHEMAS
            SCHEMAS = {t.name: set((t.input_schema or {}).get('properties', {})) for t in tools}
            return init.instructions or '', {t.name: t.description or '' for t in tools}


TOOLS = None
SCHEMAS = {}


def _tools():
    global TOOLS
    if TOOLS is None:
        TOOLS = asyncio.run(_list_tools())
    return TOOLS


def test_server_starts_and_points_to_the_guide():
    instructions, tools = _tools()
    assert 'get_guide()' in instructions and 'get_guide' in tools
    assert len(tools) > 30
    assert all(desc.strip() for desc in tools.values()), 'every tool needs a docstring'


def test_readme_tool_count_and_table():
    _, tools = _tools()
    readme = _read('README.md')
    assert '## Tools (%d)' % len(tools) in readme
    assert 'Defines the %d tools' % len(tools) in readme
    table = readme.split('## Tools', 1)[1].split('\n## ', 1)[0]
    missing = [t for t in tools if '`%s`' % t not in table]
    assert not missing, 'tools missing from README Tools table: %s' % missing


def test_designer_self_test_covers_every_tool():
    _, tools = _tools()
    selftest = _read('tests', 'test_all_tools.py')
    called = set(re.findall(r"c\('(\w+)'", selftest))
    missing = sorted(set(tools) - called)
    assert not missing, 'tools without a check in tests/test_all_tools.py: %s' % missing


def test_screenshots_never_grab_the_screen():
    # QScreen.grabWindow copies the screen area on macOS, capturing other apps (AGENTS.md, Screenshots)
    for name in ('designer_helpers.py', 'server.py'):
        assert 'grabWindow' not in _read('mcp_server', name)


def _selftest_calls():
    """{tool: set of argument names} for every c('tool', {...}) call in the live self-test;
    **G counts as 'graph'."""
    import ast
    calls = {}
    for node in ast.walk(ast.parse(_read('tests', 'test_all_tools.py'))):
        if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'c' and node.args \
                and isinstance(node.args[0], ast.Constant):
            names = calls.setdefault(node.args[0].value, set())
            if len(node.args) > 1 and getattr(node.args[1], 'id', None) == 'G':   # c('tool', G)
                names.add('graph')
            if len(node.args) > 1 and isinstance(node.args[1], ast.Dict):
                for key in node.args[1].keys:
                    names.add('graph' if key is None else key.value if isinstance(key, ast.Constant) else '?')
    return calls


def test_every_tool_parameter_is_exercised_live():
    # AGENTS.md: a new parameter needs a check, not just a docstring line
    _tools()
    calls = _selftest_calls()
    missing = sorted('%s(%s)' % (tool, p) for tool, params in SCHEMAS.items() for p in params
                     if p not in calls.get(tool, set()))
    assert not missing, 'parameters never passed by tests/test_all_tools.py: %s' % missing


def _dispatched_ops():
    """apply_edits op -> the op fields its branch reads, from the helpers' dispatcher (the code
    that runs), not from the docstring (REVIEW.md TST-6)."""
    body = _read('mcp_server', 'designer_helpers.py').split('def apply_edits(', 1)[1].split('\ndef ', 1)[0]
    branches = re.split(r"\n\s+(?:el)?if kind == '(\w+)':", body.split('else:\n                raise', 1)[0])
    return {kind: {a or b for a, b in re.findall(r"op(?:\['(\w+)'\]|\.get\('(\w+)')", code)}
            for kind, code in zip(branches[1::2], branches[2::2])}


def test_every_apply_edits_op_is_exercised_live():
    ops = set(re.findall(r"\{'op': '(\w+)'", _read('tests', 'test_all_tools.py')))
    dispatched = set(_dispatched_ops())
    assert dispatched and dispatched <= ops, 'apply_edits ops never run live: %s' % sorted(dispatched - ops)


def test_apply_edits_docstring_lists_every_op_and_field():
    text = _read('mcp_server', 'server.py').split('def apply_edits(', 1)[1].split('Refs let', 1)[0]
    doc = {m.group(1): set(re.findall(r'"(\w+)"\??:', m.group(0))) - {'op'}
           for m in re.finditer(r'\{"op": "(\w+)"[^{]*', text)}
    for kind, fields in _dispatched_ops().items():
        assert kind in doc, 'apply_edits op %r is not in the docstring' % kind
        assert fields <= doc[kind], 'apply_edits %r: fields %s not in the docstring' % (kind, sorted(fields - doc[kind]))

