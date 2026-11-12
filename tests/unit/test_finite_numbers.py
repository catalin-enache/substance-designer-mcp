"""A number that isn't finite (JSON's 1e999, Infinity, NaN, which the server's validation turns into inf and nan) is
refused by every tool before anything reaches Designer: written into a helper call with %r, it came out as `inf` or
`nan`, names the helpers don't define, and failed there as a NameError (REVIEW.md SRV-119). run_designer_script's args
go to Designer as JSON, which keeps them, so they pass."""

import asyncio
import json
from typing import Any

import pydantic
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from conftest import patch_server, server

INF, NAN = float('inf'), float('nan')

REFUSED = [
    ('open_graph', {'graph': 'g', 'rect': [0, 0, INF, 100]}, 'rect[2]'),
    ('arrange_graph', {'spacing': [NAN, 150]}, 'spacing[0]'),
    ('add_frame', {'node_ids': ['a'], 'title': 't', 'color': [0.1, 0.2, INF, 1]}, 'color[2]'),
    ('add_comment', {'text': 't', 'position': [0, -INF]}, 'position[1]'),
    ('set_link_display', {'longer_than': INF}, 'longer_than'),
    ('sweep_param', {'node_id': 'n', 'param': 'p', 'values': [0.5, NAN]}, 'values[1]'),
    (
        'apply_edits',
        {'ops': [{'op': 'move', 'node': 'n', 'position': [INF, 0]}]},
        "ops[0]['position'][0]",
    ),
    ('render_sbs', {'sbs_path': 'x.sbs', 'output_dir': 'out', 'params': {'roughness': NAN}}, "params['roughness']"),
    ('screenshot_designer', {'panel': '3d', 'tiling': INF}, 'tiling'),
    ('screenshot_designer', {'panel': '3d', 'orbit': [INF, 0]}, 'orbit[0]'),
    ('screenshot_designer', {'panel': '3d', 'pan': [0, NAN]}, 'pan[1]'),
]


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def bridge(code: str, *args: Any, **kwargs: Any) -> str:
        calls.append(code)
        return ''

    patch_server(monkeypatch, '_bridge', bridge)
    return calls


@pytest.mark.parametrize('tool, arguments, where', REFUSED, ids=[t for t, _, _ in REFUSED])
def test_a_number_that_isnt_finite_is_refused_by_name(sent: list[str], tool: str, arguments: Any, where: str) -> None:
    with pytest.raises(ToolError) as raised:  # the client gets it as an error result
        asyncio.run(server.server.call_tool(tool, arguments))
    said = str(raised.value)
    assert where + ' is ' in said and "isn't a finite number" in said, said
    assert sent == []


@pytest.mark.parametrize('written', ['1e999', 'Infinity', 'NaN'])
def test_json_gives_numbers_that_arent_finite(written: str) -> None:
    # what an agent can write: the reason for the refusal
    value = pydantic.TypeAdapter(list[float]).validate_python(json.loads('[%s]' % written))[0]
    assert value != value or abs(value) == INF


def test_the_args_of_a_designer_script_keep_them(sent: list[str], tmp_path: Any) -> None:
    script = tmp_path / 's.py'
    script.write_text('print(ARGS)\n')
    asyncio.run(server.server.call_tool('run_designer_script', {'path': str(script), 'args': {'x': INF}}))
    assert len(sent) == 1 and 'Infinity' in sent[0]
