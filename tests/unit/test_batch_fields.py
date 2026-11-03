"""apply_edits' pre-check on an op's fields (designer_helpers/batch.py), with sd and PySide6 faked (REVIEW.md HLP-62):
an unknown field was ignored, and the result said the op was applied."""

import re
import sys
import types
from typing import Any
from unittest import mock

import pytest

import designer_helpers  # conftest puts mcp_server on sys.path


@pytest.fixture
def helpers(monkeypatch: pytest.MonkeyPatch) -> Any:
    fake = mock.MagicMock()
    imported = re.findall(r'^\s*(?:from|import) ((?:sd|PySide6)(?:\.\w+)*)', designer_helpers.source(), re.M)
    for name in sorted({'.'.join(m.split('.')[:i]) for m in imported for i in range(1, m.count('.') + 2)}):
        monkeypatch.setitem(sys.modules, name, fake)
    module: Any = types.ModuleType('helpers_under_test')
    exec(compile(designer_helpers.source(), 'designer_helpers', 'exec'), module.__dict__)
    return module


def graph() -> Any:
    g = mock.MagicMock()
    g.getNodeFromId.side_effect = lambda ident: object() if ident == '1' else None
    g.getIdentifier.return_value = 'G'
    return g


TYPOS: list[tuple[dict[str, Any], str]] = [
    ({'op': 'add', 'definition': 'levels', 'postion': [1, 2]}, 'postion'),
    ({'op': 'add', 'definition': 'levels', 'parmas': {}}, 'parmas'),
    ({'op': 'bitmap', 'path': '/a.png', 'embedd': 'copy'}, 'embedd'),
    ({'op': 'set', 'node': '1', 'params': {}, 'value': 1}, 'value'),
    ({'op': 'connect', 'from': '1', 'to': '1', 'input': 'i', 'from_output': 'o'}, 'from_output'),
    ({'op': 'disconnect', 'node': '1', 'input': 'i', 'output': 'o'}, 'output'),
    ({'op': 'move', 'node': '1', 'position': [1, 2], 'x': 1}, 'x'),
    ({'op': 'delete', 'node': '1', 'nodes': ['1']}, 'nodes'),
    ({'op': 'expose', 'node': '1', 'param': 'p', 'minimum': 0}, 'minimum'),
]


@pytest.mark.parametrize(('op', 'field'), TYPOS, ids=[t[0]['op'] for t in TYPOS])
def test_a_field_the_op_doesnt_take_refuses_the_batch(helpers: Any, op: dict[str, Any], field: str) -> None:
    with pytest.raises(RuntimeError) as raised:
        helpers._check_batch(graph(), [{'op': 'add', 'definition': 'blur'}, op])
    message = str(raised.value)
    assert message.startswith('op 1 (%s): unknown field %r' % (op['op'], field)), message
    assert message.endswith('; nothing was applied')
    for right in helpers._OP_FIELDS[op['op']]:  # says what it does take
        assert right in message


@pytest.mark.parametrize(
    'op',
    [
        {'op': 'add', 'definition': 'levels', 'ref': 'a', 'position': [1, 2], 'params': {}},
        {'op': 'bitmap', 'path': '/a.png', 'ref': 'b', 'embed': 'link', 'position': [1, 2], 'name': 'n'},
        {'op': 'set', 'node': '1', 'params': {}},
        {'op': 'connect', 'from': '1', 'to': '1', 'input': 'i', 'output': 'o'},
        {'op': 'disconnect', 'node': '1', 'input': 'i'},
        {'op': 'move', 'node': '1', 'position': [1, 2]},
        {'op': 'delete', 'node': '1'},
        {
            'op': 'expose',
            'node': '1',
            'param': 'p',
            'input_id': 'i',
            'label': 'l',
            'default': 1,
            'min': 0,
            'max': 1,
            'step': 0.1,
            'group': 'g',
        },
    ],
    ids=lambda op: op['op'],
)
def test_every_documented_field_passes(helpers: Any, op: dict[str, Any]) -> None:
    helpers._check_batch(graph(), [op])
