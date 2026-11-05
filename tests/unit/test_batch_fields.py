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


# --- naming and tagging an output node (ROADMAP item 47)
OUTPUT = 'sbs::compositing::output'


def _node(definition: str, identifier: str = '') -> Any:
    node = mock.MagicMock()
    node.getDefinition.return_value.getId.return_value = definition
    node.getIdentifier.return_value = identifier or 'node'
    node.getAnnotationPropertyValueFromId.return_value.get.return_value = identifier
    return node


def outputs_graph(*names: str) -> Any:
    """A graph with a levels node '1' and an output node per name, '2' and up."""
    g = graph()
    nodes = {'1': _node('sbs::compositing::levels')}
    outs = {str(i + 2): _node(OUTPUT, name) for i, name in enumerate(names)}
    nodes.update(outs)
    g.getNodeFromId.side_effect = nodes.get
    g.getOutputNodes.return_value = list(outs.values())
    return g


REFUSED: list[tuple[list[dict[str, Any]], str]] = [
    ([{'op': 'add', 'definition': 'levels', 'identifier': 'a'}], 'only an output node'),
    ([{'op': 'add', 'definition': 'levels', 'label': 'a'}], 'only an output node'),
    ([{'op': 'add', 'definition': 'levels', 'usage': 'normal'}], 'only an output node'),
    ([{'op': 'set', 'node': '1', 'identifier': 'a'}], 'only an output node'),
    ([{'op': 'set', 'node': 'graph', 'label': 'a'}], 'only an output node'),
    (
        [{'op': 'add', 'definition': 'levels', 'ref': 'l'}, {'op': 'set', 'node': 'l', 'usage': 'normal'}],
        'only an output node',
    ),
    ([{'op': 'set', 'node': '2', 'params': {}, 'identifier': 'a'}], 'params or'),
    ([{'op': 'add', 'definition': 'output', 'identifier': 'a b'}], 'identifier'),
    ([{'op': 'add', 'definition': 'output', 'identifier': ''}], 'identifier'),
    ([{'op': 'add', 'definition': 'output', 'identifier': '../x'}], 'identifier'),
    ([{'op': 'add', 'definition': 'output', 'identifier': 'x.png'}], 'identifier'),
    ([{'op': 'add', 'definition': 'output', 'identifier': 5}], 'identifier'),
    ([{'op': 'set', 'node': '2', 'identifier': 'é'}], 'identifier'),
    ([{'op': 'add', 'definition': 'output', 'label': 5}], 'label'),
    ([{'op': 'add', 'definition': 'output', 'usage': ''}], 'usage'),
    ([{'op': 'add', 'definition': 'output', 'usage': 'a b'}], 'usage'),
    ([{'op': 'set', 'node': '2', 'usage': ['normal']}], 'usage'),
]


@pytest.mark.parametrize(('ops', 'said'), REFUSED, ids=[str(i) for i in range(len(REFUSED))])
def test_a_wrong_output_field_refuses_the_batch(helpers: Any, ops: list[dict[str, Any]], said: str) -> None:
    with pytest.raises(RuntimeError) as raised:
        helpers._check_batch(outputs_graph('height'), ops)
    assert said in str(raised.value) and str(raised.value).endswith('; nothing was applied'), raised.value


@pytest.mark.parametrize(
    'ops',
    [
        [
            {
                'op': 'add',
                'definition': 'output',
                'identifier': 'base-color_1',
                'label': 'Base / é',
                'usage': 'baseColor',
            }
        ],
        [{'op': 'add', 'definition': OUTPUT, 'usage': '$matte'}],
        [{'op': 'set', 'node': '2', 'identifier': 'a'}],
        [{'op': 'set', 'node': '2', 'label': ''}],
        [{'op': 'add', 'definition': 'output', 'ref': 'o'}, {'op': 'set', 'node': 'o', 'usage': 'normal'}],
    ],
)
def test_right_output_fields_pass_the_check(helpers: Any, ops: list[dict[str, Any]]) -> None:
    helpers._check_batch(outputs_graph('height'), ops)


def test_a_ref_reused_for_another_node_is_judged_by_the_newer_one(helpers: Any) -> None:
    ops: list[dict[str, Any]] = [
        {'op': 'add', 'definition': 'output', 'ref': 'n'},
        {'op': 'add', 'definition': 'levels', 'ref': 'n'},
        {'op': 'set', 'node': 'n', 'label': 'a'},
    ]
    with pytest.raises(RuntimeError, match='only an output node'):
        helpers._check_batch(outputs_graph(), ops)


@pytest.mark.parametrize(
    ('given', 'tag'),
    [
        ('baseColor', ('baseColor', 'RGBA', 'sRGB')),
        ('basecolor', ('baseColor', 'RGBA', 'sRGB')),
        ('EMISSIVE', ('emissive', 'RGBA', 'sRGB')),
        ('normal', ('normal', 'RGBA', 'Linear')),
        ('ambientocclusion', ('ambientOcclusion', 'RGBA', 'Linear')),
        ('myMask', ('myMask', 'RGBA', 'Linear')),
    ],
)
def test_a_usage_gets_its_exact_name_and_colour_space(helpers: Any, given: str, tag: tuple[str, str, str]) -> None:
    node = _node(OUTPUT, 'o')
    helpers.set_output_tags(outputs_graph(), node, None, None, given)
    sys.modules['sd.api.sdusage'].SDUsage.sNew.assert_called_with(*tag)
    assert [c.args[0] for c in node.setAnnotationPropertyValueFromId.call_args_list] == ['usages']


def test_only_what_was_given_is_set(helpers: Any) -> None:
    node = _node(OUTPUT, 'o')
    helpers.set_output_tags(outputs_graph(), node, 'a', None, None)
    assert [c.args[0] for c in node.setAnnotationPropertyValueFromId.call_args_list] == ['identifier']
    node = _node(OUTPUT, 'o')
    helpers.set_output_tags(outputs_graph(), node, None, 'a', None)
    assert [c.args[0] for c in node.setAnnotationPropertyValueFromId.call_args_list] == ['label']


@pytest.mark.parametrize('taken', ['height', 'Height'])
def test_a_name_another_output_has_is_refused_with_nothing_set(helpers: Any, taken: str) -> None:
    # Designer takes it, and export_outputs then refuses the two; by case too, for a Mac's or Windows' file names
    g = outputs_graph('height', 'other')
    node = g.getNodeFromId('3')
    with pytest.raises(RuntimeError, match='already'):
        helpers.set_output_tags(g, node, taken, 'label', 'normal')
    node.setAnnotationPropertyValueFromId.assert_not_called()


def test_an_output_can_keep_its_own_name(helpers: Any) -> None:
    g = outputs_graph('height')
    node = g.getNodeFromId('2')
    node.getIdentifier.return_value = '2'
    g.getOutputNodes.return_value = [node]
    helpers.set_output_tags(g, node, 'height', None, None)
    node.setAnnotationPropertyValueFromId.assert_called_once()


def test_renaming_an_existing_output_tells_the_agent_to_tell_the_user(helpers: Any, capsys: Any) -> None:
    # a closed graph using it keeps the old connector and computes black, with no error (REVIEW.md HLP-81)
    helpers.set_output_tags(outputs_graph(), _node(OUTPUT, 'old'), 'new', None, None, warn_rename=True)
    said = capsys.readouterr().out
    assert (
        'Tell the user' in said and "'old'" in said and "'new'" in said and 'black' in said and 'new instance' in said
    )


@pytest.mark.parametrize(
    ('identifier', 'label', 'warn'),
    [
        ('old', None, True),  # the name it already has
        (None, 'a label', True),  # no rename at all
        ('new', None, False),  # just added: nothing can be using it yet
    ],
)
def test_no_warning_without_a_rename_of_an_existing_output(
    helpers: Any, capsys: Any, identifier: str | None, label: str | None, warn: bool
) -> None:
    helpers.set_output_tags(outputs_graph(), _node(OUTPUT, 'old'), identifier, label, None, warn_rename=warn)
    assert 'Tell the user' not in capsys.readouterr().out


def test_only_a_change_of_case_still_warns(helpers: Any, capsys: Any) -> None:
    helpers.set_output_tags(outputs_graph(), _node(OUTPUT, 'old'), 'OLD', None, None, warn_rename=True)
    assert 'Tell the user' in capsys.readouterr().out
