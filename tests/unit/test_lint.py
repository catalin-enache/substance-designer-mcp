"""Every Python file in the repository passes ruff's lint rules and is formatted by ruff (ruff.toml)."""

import importlib.util
import subprocess
import sys

import pytest

from conftest import ROOT


def _ruff(*args: str) -> subprocess.CompletedProcess[str]:
    if importlib.util.find_spec('ruff') is None:
        pytest.fail(
            'ruff is not installed: mcp_server/venv/bin/python -m pip install -r mcp_server/requirements-dev.txt'
        )
    return subprocess.run([sys.executable, '-m', 'ruff', *args], cwd=ROOT, capture_output=True, text=True)


def test_ruff_check_finds_nothing() -> None:
    result = _ruff('check', '--no-cache', '.')
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_file_is_formatted() -> None:
    result = _ruff('format', '--check', '--no-cache', '.')
    assert result.returncode == 0, result.stdout + result.stderr + '\nRun: mcp_server/venv/bin/ruff format .'
