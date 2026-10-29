"""The committed .mcp.json registers the server for this repo only (no global registration) and
works wherever in the repo `claude` is started."""
import asyncio
import json
import os
import sys

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from conftest import ROOT


def _config():
    with open(os.path.join(ROOT, '.mcp.json')) as f:
        return json.load(f)['mcpServers']['substance-designer']


def test_no_claude_code_expansion_in_the_command():
    # Claude Code expands ${...} in .mcp.json itself (it rewrote a shell default away), so the
    # command must leave every variable to the shell
    cfg = _config()
    assert cfg['type'] == 'stdio' and cfg['command'] == 'sh'
    assert not any('${' in a for a in cfg['args'])


async def _tool_count(cwd, project_dir):
    cfg = _config()
    env = {k: v for k, v in os.environ.items() if k != 'CLAUDE_PROJECT_DIR'}
    if project_dir:
        env['CLAUDE_PROJECT_DIR'] = project_dir
    params = StdioServerParameters(command=cfg['command'], args=cfg['args'], cwd=cwd, env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return len((await s.list_tools()).tools)


@pytest.mark.skipif(sys.platform == 'win32', reason='.mcp.json uses sh; Windows registers per folder')
@pytest.mark.parametrize('subfolder, project_dir', [('', ROOT), ('tests', ROOT), ('tests', None),
                                                     (os.path.join('mcp_server', 'venv'), None)])
def test_server_starts_from_anywhere_in_the_repo(subfolder, project_dir):
    # Claude Code sets CLAUDE_PROJECT_DIR; without it the command falls back to the git root
    assert asyncio.run(_tool_count(os.path.join(ROOT, subfolder), project_dir)) > 30
