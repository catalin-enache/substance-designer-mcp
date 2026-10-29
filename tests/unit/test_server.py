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
            return init.instructions or '', {t.name: t.description or '' for t in tools}


TOOLS = None


def _tools():
    global TOOLS
    if TOOLS is None:
        TOOLS = asyncio.run(_list_tools())
    return TOOLS


def test_server_starts_and_serves_agents_md():
    instructions, tools = _tools()
    assert instructions.startswith('# AGENTS.md')
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
