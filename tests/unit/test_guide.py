"""The guide reaches every session: short instructions (MCP clients cut long ones; Claude Code at
4,096 characters) that point to get_guide(), which returns all of AGENTS.md."""

import os
import re
from pathlib import Path

import pytest

from conftest import ROOT, patch_server, server

CLAUDE_CODE_LIMIT = 4096  # measured: AGENTS.md arrived cut at exactly this many characters


def _agents_md() -> str:
    with open(os.path.join(ROOT, 'AGENTS.md'), encoding='utf-8') as f:
        return f.read()


def test_instructions_fit_and_ask_for_the_guide_on_first_use() -> None:
    text = server.INSTRUCTIONS
    assert len(text) < CLAUDE_CODE_LIMIT
    # nothing up front: a session started for other work never loads the guide
    assert (
        'Do not call get_guide() or any other tool from this server unless the user asks for work in Designer' in text
    )
    assert 'Right before your first Designer tool call in this session, call get_guide()' in text
    assert 'tell the user' in text


def test_get_guide_returns_all_of_agents_md(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(server._session, 'guide_read', False)
    text = server.get_guide()
    assert text.startswith(_agents_md()) and server._session['guide_read']
    assert 'End of the Designer guide (%d characters, complete)' % len(_agents_md()) in text
    assert 'tell the user' in text.splitlines()[-1]


def test_guide_fits_in_one_tool_result() -> None:
    # Claude Code's default limit for one MCP tool result is 25,000 tokens; stay well below
    assert len(_agents_md()) < 60000


def test_reminder_until_the_guide_is_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    patch_server(monkeypatch, 'SNAPSHOT_DIR', str(tmp_path))
    monkeypatch.setitem(server._session, 'guide_read', False)
    assert server.list_snapshots().startswith(server.GUIDE_NOT_READ + '\n\nNo snapshots')
    server.get_guide()
    assert server.list_snapshots() == 'No snapshots.'


def test_reminder_leaves_non_text_results_alone(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from PIL import Image

    Image.new('L', (4, 4)).save(tmp_path / 'a.png')
    monkeypatch.setitem(server._session, 'guide_read', False)
    result = server.preview_maps(str(tmp_path))
    assert not isinstance(result, str) and result.data


@pytest.mark.parametrize('fact', [r'4,096', r'\b29\b'])  # the instructions limit; the atomic node count
def test_facts_are_stated_once_in_the_docs(fact: str) -> None:
    # AGENTS.md, Keeping the docs current: each fact in one place, linked from elsewhere (REVIEW.md TST-10,
    # TST-18)
    count = sum(
        len(re.findall(fact, Path(ROOT, name).read_text(encoding='utf-8')))
        for name in ('AGENTS.md', 'README.md', 'ROADMAP.md')
    )
    assert count <= 1, '%r appears %d times in AGENTS.md, README.md and ROADMAP.md' % (fact, count)
