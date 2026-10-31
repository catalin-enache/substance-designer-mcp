"""The committed .mcp.json registers the server for this repo only (no global registration) and
works wherever in the repo `claude` is started."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from conftest import ROOT


def _config() -> dict[str, Any]:
    with open(os.path.join(ROOT, '.mcp.json')) as f:
        config: dict[str, Any] = json.load(f)['mcpServers']['substance-designer']
        return config


def test_no_claude_code_expansion_in_the_command() -> None:
    # Claude Code expands ${...} in .mcp.json itself (it rewrote a shell default away), so the
    # command must leave every variable to the shell
    cfg = _config()
    assert cfg['type'] == 'stdio' and cfg['command'] == 'sh'
    assert not any('${' in a for a in cfg['args'])


async def _tool_count(cwd: str, project_dir: str | None) -> int:
    cfg = _config()
    env = {k: v for k, v in os.environ.items() if k != 'CLAUDE_PROJECT_DIR'}
    if project_dir:
        env['CLAUDE_PROJECT_DIR'] = project_dir
    params = StdioServerParameters(command=cfg['command'], args=cfg['args'], cwd=cwd, env=env)
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        return len((await s.list_tools()).tools)


@pytest.mark.skipif(sys.platform == 'win32', reason='.mcp.json uses sh; Windows registers per folder')
@pytest.mark.parametrize(
    'subfolder, project_dir', [('', ROOT), ('tests', ROOT), ('tests', None), (os.path.join('mcp_server', 'venv'), None)]
)
def test_server_starts_from_anywhere_in_the_repo(subfolder: str, project_dir: str | None) -> None:
    # Claude Code sets CLAUDE_PROJECT_DIR; without it the command falls back to the git root
    assert asyncio.run(_tool_count(os.path.join(ROOT, subfolder), project_dir)) > 30


@pytest.mark.skipif(sys.platform == 'win32', reason='.mcp.json uses sh; Windows registers per folder')
def test_starts_when_project_dir_is_a_subfolder() -> None:
    # REVIEW.md INS-5: a CLAUDE_PROJECT_DIR without the venv falls back to the git root
    assert asyncio.run(_tool_count(os.path.join(ROOT, 'tests'), os.path.join(ROOT, 'examples'))) > 30


@pytest.mark.skipif(sys.platform == 'win32', reason='.mcp.json uses sh; Windows registers per folder')
def test_a_missing_venv_says_to_run_the_installer(tmp_path: Path) -> None:
    # REVIEW.md INS-5: a fresh clone (or a deleted venv) only showed "failed to connect"
    import subprocess

    cfg = _config()
    env = {k: v for k, v in os.environ.items() if k != 'CLAUDE_PROJECT_DIR'}
    result = subprocess.run(
        [cfg['command'], *cfg['args']], cwd=str(tmp_path), env=env, capture_output=True, text=True, timeout=20
    )
    assert result.returncode != 0 and 'install.py' in result.stderr


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='runs a stand-in python.exe through sh; real Windows registers per folder (REVIEW.md INS-18)',
)
def test_a_windows_venv_is_used(tmp_path: Path) -> None:
    # REVIEW.md INS-14: with sh on PATH on Windows (Git Bash), the venv is
    # mcp_server/venv/Scripts/python.exe, and the command said there was no Python environment
    import stat
    import subprocess

    python = tmp_path / 'mcp_server' / 'venv' / 'Scripts' / 'python.exe'
    python.parent.mkdir(parents=True)
    python.write_text('#!/bin/sh\necho WINDOWS_VENV "$@"\n')
    python.chmod(python.stat().st_mode | stat.S_IXUSR)
    cfg = _config()
    env = {k: v for k, v in os.environ.items() if k != 'CLAUDE_PROJECT_DIR'}
    result = subprocess.run(
        [cfg['command'], *cfg['args']], cwd=str(tmp_path), env=env, capture_output=True, text=True, timeout=20
    )
    assert result.stdout.strip() == 'WINDOWS_VENV mcp_server/server.py', result.stderr
