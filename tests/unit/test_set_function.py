"""set_function: the read, the expression compiled on the server and checked against its target, then one undo step
building it (server_tools/functions.py), with the bridge and `_edit` faked; and the helper's build
(designer_helpers/functions.py), with sd faked. The live self-test builds real functions (tests/test_all_tools/functions)."""

import ast
import json
import re
import sys
import types
import typing
from collections.abc import Callable
from pathlib import Path
from unittest import mock

import pytest

from conftest import FakeGraph, fake_bridge, patch_server, server
from function_compiler import ExpressionError, Kind, Resource, compile_expression
from server_tools.functions import EXPRESSION, _Reach, _Resource, _ResourceTarget, _Target, _Typed

# the graph's inputs as the read gives them: a colour, read as a float4; an int; a string; a texture, which no function
# reads. Then the node's input values, by their #name: a float, as a Value Processor connected into it gives
INPUTS: dict[str, _Typed] = {
    'tint': {'type': 'ColorRGBA', 'getter': 'get_float4'},
    'mode': {'type': 'int', 'getter': 'get_integer1'},
    'name': {'type': 'string', 'getter': 'get_string'},
    'img': {'type': 'SDTypeTexture', 'getter': None},
    '#v': {'type': 'float', 'getter': 'get_float1'},
}
# what the compiler gets: each as its getter reads it
TYPES = {'tint': 'float4', 'mode': 'int', 'name': 'string', 'img': 'SDTypeTexture', '#v': 'float'}


def target(kind: Kind, parameter: str, value: _Typed, colorswitch: bool | None = None) -> _Target:
    """What the read prints: a Pixel Processor's perpixel, a Value Processor's function, or a parameter."""
    return {
        'graph': 'G',
        'package': '/p/mine.sbs',
        'node': '7',
        'parameter': parameter,
        'kind': kind,
        'value': value,
        'colorswitch': colorswitch,
        'inputs': INPUTS,
        'fed': {'#v': {'end': '9.unique_filter_output', 'type': 'float'}},
        'drives': [],
        'functions': {},
        'images': None if kind == 'parameter' else [],
    }


PIXEL = target('perpixel', 'perpixel', {'type': 'float4', 'getter': 'get_float4'}, colorswitch=True)
PIXEL_GREY: _Target = {**PIXEL, 'colorswitch': False}
VALUE = target('function', 'function', {'type': 'bool', 'getter': 'get_bool'})
LEVELS = target('parameter', 'leveloutlow', {'type': 'float4', 'getter': 'get_float4'})
COLOR = target('parameter', 'outputcolor', {'type': 'ColorRGBA', 'getter': 'get_float4'})
ENUM = target('parameter', 'blendingmode', {'type': 'sbs::compositing::blendingmode', 'getter': 'get_integer1'})
INT = target('parameter', '$randomseed', {'type': 'int', 'getter': 'get_integer1'})
FLOAT = target('parameter', 'opacity', {'type': 'float', 'getter': 'get_float1'})
SIZE = target('parameter', '$outputsize', {'type': 'int2', 'getter': 'get_integer2'})
FORMAT = target('parameter', '$format', {'type': 'sbs::compositing::format', 'getter': 'get_integer1'})


class Faked:
    """The bridge answering the read with `answer`, and `_edit`'s calls kept (call, undo label), answered with what the
    build helper prints."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, answer: str) -> None:
        self.reads: list[str] = []
        self.edits: list[tuple[str, str]] = []

        def bridge(code: str) -> str:
            self.reads.append(code.rstrip().splitlines()[-1])
            return answer

        def edit(call: str, label: str) -> str:
            self.edits.append((call, label))
            return '7.perpixel: built 3 function nodes, its output a float4'

        fake_bridge(monkeypatch, bridge)
        patch_server(monkeypatch, '_edit', edit)


def faked(monkeypatch: pytest.MonkeyPatch, read: _Target) -> Faked:
    return Faked(monkeypatch, 'FUNCTION_TARGET=%s\n' % json.dumps(read))


def arguments(call: str) -> list[object]:
    """The arguments of a helper call, as Python literals."""
    node = ast.parse(call, mode='eval').body
    assert isinstance(node, ast.Call)
    return [ast.literal_eval(a) for a in node.args]


def test_the_expression_is_read_compiled_and_built_in_one_undo_step(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = faked(monkeypatch, LEVELS)
    said = server.set_function('tint * 0.5', '7', 'leveloutlow', graph='G')
    assert fake.reads == ["function_target('G', '7', 'leveloutlow')"]
    [(call, label)] = fake.edits
    assert call.startswith('set_function(') and label == 'Claude: set function of 7.leveloutlow'
    # the target read is passed back, for the build to check it again, with the nodes compiled from the graph's inputs
    # as their getters read them
    assert arguments(call) == ['G', LEVELS, compile_expression('tint * 0.5', TYPES)]
    assert said.startswith('7.perpixel: built 3 function nodes')


def test_the_nodes_input_values_are_read_by_their_name(monkeypatch: pytest.MonkeyPatch) -> None:
    # a Value Processor connected into the node's #v drives its parameter (GUIDE.md, Building a function graph)
    fake = faked(monkeypatch, FLOAT)
    server.set_function('#v * tint.x', '7', 'opacity')
    [(call, _)] = fake.edits
    function = arguments(call)[2]
    assert function == compile_expression('#v * tint.x', TYPES)
    assert (
        isinstance(function, dict)
        and {'definition': 'get_float1', 'type': 'float', 'constant': '#v', 'inputs': {}} in function['nodes']
    )


FLOAT4_FED: _Target = {**FLOAT, 'fed': {'#v': {'end': '9.unique_filter_output', 'type': 'float4'}}}


def test_an_input_value_fed_another_type_is_refused_naming_both(monkeypatch: pytest.MonkeyPatch) -> None:
    # Designer keeps the connection as its source's type changes, and reads it wrongly (GUIDE.md, Input values)
    assert refused(monkeypatch, FLOAT4_FED, '#v * 0.5') == (
        '7.#v is an input value of type float, and 9.unique_filter_output, connected into it, gives float4, which '
        'Designer reads wrongly: connect that output into another #name. Nothing was built.'
    )


def test_a_parameter_refuses_an_input_value_with_nothing_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    # a parameter's function reading a float one computed no value (GUIDE.md, Input values)
    assert refused(monkeypatch, {**FLOAT, 'fed': {'#v': None}}, '#v') == (
        "7.#v has nothing connected: connect a value into it first (apply_edits' connect to input '#v'). Nothing was "
        'built.'
    )


@pytest.mark.parametrize('read', [PIXEL, VALUE], ids=['a Pixel Processor', 'a Value Processor'])
def test_a_processor_says_it_reads_0_from_a_float_input_value_with_nothing_connected(
    monkeypatch: pytest.MonkeyPatch, read: _Target
) -> None:
    # a processor's function reads 0 from a float one (GUIDE.md, Input values): it builds, and the result says so
    faked(monkeypatch, {**read, 'fed': {'#v': None}})
    said = server.set_function('float4(#v, #v, #v, 1)', '7', read['parameter'])
    assert said.endswith('\n7.#v has nothing connected: it reads 0.'), said


def test_a_processor_says_only_that_another_type_has_nothing_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    # only a float is measured (REVIEW.md SRV-196)
    pair: _Typed = {'type': 'float2', 'getter': 'get_float2'}
    faked(monkeypatch, {**PIXEL, 'inputs': {**INPUTS, '#w': pair}, 'fed': {'#v': None, '#w': None}})
    said = server.set_function('float4(#w, 0, 1)', '7')
    assert said.endswith(
        "\n7.#w has nothing connected: connect a value into it first (apply_edits' connect to input '#w')."
    ), said


def test_only_the_input_values_the_expression_reads_are_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    assert refused(monkeypatch, FLOAT4_FED, 'tint.x') is None
    assert refused(monkeypatch, {**FLOAT, 'fed': {'#v': None}}, '0.5') is None


DRIVING: _Target = {**VALUE, 'drives': [{'end': '12.#v', 'type': 'float'}, {'end': '13.#w', 'type': 'float'}]}


def test_a_value_processor_refuses_a_result_unlike_an_input_value_it_drives(monkeypatch: pytest.MonkeyPatch) -> None:
    assert refused(monkeypatch, DRIVING, 'float4(0.1, 0.2, 0.3, 1)') == (
        "7's output drives 12.#v, an input value of type float, and the expression gives a float4, which Designer "
        "would read wrongly there: give a float, or disconnect 12.#v first (an apply_edits disconnect op on node '12', "
        "input '#v'). Nothing was built."
    )
    assert refused(monkeypatch, DRIVING, '0.5') is None


def test_no_parameter_reads_the_nodes_own_function(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = faked(monkeypatch, PIXEL)
    server.set_function('0.5', '7')
    assert fake.reads == ["function_target(None, '7', None)"]


@pytest.mark.parametrize(
    ('expression', 'said'),
    [
        ('sqrt(nope)', 'column 6: unknown name `nope`; the graph inputs are img, mode, name, tint.'),
        ('sqrt(', "column 5: '(' was never closed."),
        ('img', "column 1: graph input `img` has type SDTypeTexture, which a function can't read."),
        ('-int(1)', 'which Designer computes wrongly: write -float(1).'),
        ('#nope', 'column 1: the node has no input value `#nope`; its input values are #v.'),
    ],
    ids=['an unknown name', 'a syntax error', 'an input no function reads', 'a negative int', 'a missing input value'],
)
def test_a_refused_expression_builds_nothing(monkeypatch: pytest.MonkeyPatch, expression: str, said: str) -> None:
    fake = faked(monkeypatch, PIXEL)
    with pytest.raises(server.ToolError) as raised:
        server.set_function(expression, '7')
    assert str(raised.value).endswith(said + ' Nothing was built.'), str(raised.value)
    assert fake.edits == []


def refused(monkeypatch: pytest.MonkeyPatch, read: _Target, expression: str) -> str | None:
    """set_function's refusal of `expression` on `read`'s target, or None when it builds; nothing built when refused."""
    fake = faked(monkeypatch, read)
    try:
        server.set_function(expression, '7', read['parameter'])
    except server.ToolError as e:
        assert fake.edits == []
        return str(e)
    assert len(fake.edits) == 1
    return None


BLACK = 'which a Pixel Processor computes as black. It takes a float or a float4'


@pytest.mark.parametrize(
    ('expression', 'refusal'),
    [
        ('0.5', None),
        ('float4(0.1, 0.2, 0.3, 1)', None),
        ('$pos', '7.perpixel: the expression gives a float2, %s. Nothing was built.' % BLACK),
        (
            'float3($pos, 1)',
            '7.perpixel: the expression gives a float3, %s: write float4(c, 1) for a colour c. Nothing was built.'
            % BLACK,
        ),
        ('true', '7.perpixel: the expression gives a bool, %s. Nothing was built.' % BLACK),
        ('int(1)', '7.perpixel: the expression gives an int, %s. Nothing was built.' % BLACK),
        ('int4(1, 2, 3, 4)', '7.perpixel: the expression gives an int4, %s. Nothing was built.' % BLACK),
    ],
    ids=['a float', 'a float4', 'a float2', 'a float3', 'a bool', 'an int', 'an int4'],
)
def test_a_pixel_processor_takes_a_float_or_a_float4(
    monkeypatch: pytest.MonkeyPatch, expression: str, refusal: str | None
) -> None:
    # the other types compute black, raising nothing (GUIDE.md, Building a function graph)
    assert refused(monkeypatch, PIXEL, expression) == refusal


@pytest.mark.parametrize('expression', ['true', 'mode', 'int3(1, 2, 3)', '0.5', 'float2(0.1, 0.2)', 'tint'])
def test_a_value_processor_takes_any_number_or_a_bool(monkeypatch: pytest.MonkeyPatch, expression: str) -> None:
    assert refused(monkeypatch, VALUE, expression) is None


def test_a_value_processor_refuses_a_string(monkeypatch: pytest.MonkeyPatch) -> None:
    assert refused(monkeypatch, VALUE, 'name') == (
        "7.function: the expression gives a string, and a Value Processor's function takes a bool, an int to int4 or "
        'a float to float4. Nothing was built.'
    )


@pytest.mark.parametrize(
    ('read', 'expression', 'refusal'),
    [
        (LEVELS, 'tint * 0.5', None),
        (
            LEVELS,
            '0.5',
            '7.leveloutlow takes a float4, and the expression gives a float: write float4(c, c, c, c) for its result c. '
            'Nothing was built.',
        ),
        (COLOR, 'tint', None),
        (
            COLOR,
            'tint.xyz',
            '7.outputcolor takes a float4 (its type, ColorRGBA, as a function gives it), and the expression gives a '
            'float3: write float4(c, 1) for its result c. Nothing was built.',
        ),
        (ENUM, 'mode', None),
        (
            ENUM,
            '3',
            '7.blendingmode takes an int (its type, sbs::compositing::blendingmode, as a function gives it), and the '
            'expression gives a float: write int(c) for its result c. Nothing was built.',
        ),
        (
            INT,
            '1',
            '7.$randomseed takes an int, and the expression gives a float: write int(c) for its result c. Nothing was '
            'built.',
        ),
        (
            FLOAT,
            'tint',
            '7.opacity takes a float, and the expression gives a float4: write c.x for its result c. Nothing was built.',
        ),
    ],
    ids=[
        'a float4',
        'a float for a float4',
        'a colour',
        'a float3 for a colour',
        'an enum',
        'a float for an enum',
        'a float for an int',
        'a float4 for a float',
    ],
)
def test_a_parameter_takes_its_own_type(
    monkeypatch: pytest.MonkeyPatch, read: _Target, expression: str, refusal: str | None
) -> None:
    # Designer would connect another type and compute a wrong value (GUIDE.md, Building a function graph)
    assert refused(monkeypatch, read, expression) == refusal


@pytest.mark.parametrize(
    ('read', 'expression', 'shown'),
    [
        (PIXEL, '0.5', 'colorswitch is on: the float is grey.'),
        (PIXEL, 'float4(0.1, 0.2, 0.3, 1)', 'colorswitch is on: the float4 is the colour.'),
        (PIXEL_GREY, '0.5', 'colorswitch is off: the float is the grayscale value.'),
        (
            PIXEL_GREY,
            'float4(0.1, 0.2, 0.3, 1)',
            'colorswitch is off: the float4 is averaged to grey (the mean of R, G and B, alpha left out).',
        ),
        (VALUE, 'float2(0.1, 0.2)', "The Value Processor's output is a float2 now."),
    ],
    ids=['grey', 'a colour', 'a grayscale value', 'a colour averaged', 'a Value Processor'],
)
def test_the_result_says_how_the_processor_gives_the_output(
    monkeypatch: pytest.MonkeyPatch, read: _Target, expression: str, shown: str
) -> None:
    faked(monkeypatch, read)
    said = server.set_function(expression, '7')
    assert said.rstrip('\n').splitlines()[-1] == shown, said


def test_a_parameters_result_adds_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    faked(monkeypatch, LEVELS)
    assert server.set_function('tint', '7', 'leveloutlow') == '7.perpixel: built 3 function nodes, its output a float4'


# Sampling a processor's input images: the read gives whether each is connected, up to the last one connected


@pytest.mark.parametrize('read', [PIXEL, VALUE], ids=['a Pixel Processor', 'a Value Processor'])
def test_a_processors_function_samples_its_input_images(monkeypatch: pytest.MonkeyPatch, read: _Target) -> None:
    # at a fixed place: `$pos` isn't the pixel's in a Value Processor's function
    fake = faked(monkeypatch, {**read, 'images': [True, True]})
    server.set_function('sample(1, float2(0.5, 0.5))', '7', read['parameter'])
    [(call, _)] = fake.edits
    assert arguments(call)[2] == compile_expression('sample(1, float2(0.5, 0.5))', TYPES, images=True)


# what the result says of a sampled input with nothing connected (GUIDE.md, Sampling an image)
UNTIL = 'has nothing connected: sampling it reads (0, 0, 0, 0) until an image is connected into it'


@pytest.mark.parametrize(
    ('images', 'expression', 'said'),
    [
        ([], 'sample(0, $pos)', "7.input %s (apply_edits' connect)." % UNTIL),
        ([True], 'sample(1, $pos)', "7.input:1 %s (apply_edits' connect)." % UNTIL),
        # Designer lists each input once the one before it is connected (GUIDE.md, A processor's input images)
        (
            [True],
            'sample(3, $pos)',
            "7.input:3 %s, and into input:1 to input:2 before it, in order (apply_edits' connect)." % UNTIL,
        ),
        ([], 'sample_lum(1, $pos)', "7.input:1 %s, and into input before it, in order (apply_edits' connect)." % UNTIL),
        # input:1 disconnected while input:2 is connected (GUIDE.md, Sampling an image)
        ([True, False, True], 'sample(1, $pos) + sample(2, $pos)', "7.input:1 %s (apply_edits' connect)." % UNTIL),
    ],
    ids=['no input', 'the next input', 'a later input', 'from none', 'a gap'],
)
def test_a_sample_of_an_input_with_nothing_connected_is_built_and_said(
    monkeypatch: pytest.MonkeyPatch, images: list[bool], expression: str, said: str
) -> None:
    fake = faked(monkeypatch, {**PIXEL, 'images': images})
    result = server.set_function(expression, '7')
    assert len(fake.edits) == 1
    assert result.endswith('\n' + said), result


@pytest.mark.parametrize(
    ('read', 'where'),
    [
        (VALUE, "a Value Processor's function, where it reads (0, 0)"),
        (LEVELS, "a parameter's function, where it reads another value"),
    ],
    ids=['value', 'parameter'],
)
def test_the_reads_kind_reaches_the_compiler(monkeypatch: pytest.MonkeyPatch, read: _Target, where: str) -> None:
    # `$pos` refused where it isn't the pixel's (REVIEW.md SRV-212, SRV-214, TST-758)
    assert refused(monkeypatch, read, '$pos') == (
        "column 1: `$pos` isn't the pixel's position in %s: use it in a Pixel Processor's function. Nothing was built."
        % where
    )


def test_a_parameters_function_samples_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    assert refused(monkeypatch, LEVELS, 'sample(0, $pos)') == (
        "column 1: `sample(0, $pos)` samples an input image, and only a Pixel or Value Processor's function has input "
        'images, or a function graph it calls. Nothing was built.'
    )


def test_a_call_samples_the_images_its_function_graph_samples(monkeypatch: pytest.MonkeyPatch) -> None:
    blur: _Resource = {'inputs': {'uv': FLOAT2}, 'output': 'float4', 'calls': [], 'samples': [1]}
    two: _Target = {**PIXEL, 'images': [True, True], 'functions': {'blur': blur}}
    faked(monkeypatch, two)
    assert 'nothing connected' not in server.set_function('blur($pos)', '7')
    faked(monkeypatch, {**two, 'images': [True]})
    assert server.set_function('blur($pos)', '7').endswith("\n7.input:1 %s (apply_edits' connect)." % UNTIL)


def test_a_function_graph_samples_its_callers_input_images(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = faked_resource(monkeypatch, resource_target({}))
    server.set_function('sample(1, uv)', function='paint', inputs={'uv': 'float2'})
    [(call, _)] = fake.edits
    assert arguments(call)[3] == compile_expression('sample(1, uv)', {'uv': 'float2'}, {}, 'paint', images=True)


def test_a_refused_read_builds_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = Faked(monkeypatch, "--- ERROR ---\nRuntimeError: node '9' not found in graph G")
    with pytest.raises(server.ToolError, match=r"^RuntimeError: node '9' not found in graph G$"):
        server.set_function('0.5', '9')
    assert fake.edits == []


def test_the_grammars_truncating_example_divides_ints() -> None:
    # number literals compile as floats where nothing says otherwise: `7 / 2` gave 3.5 (REVIEW.md SRV-216)
    found = re.search(r'/ of two ints truncates \((.+?) is 3\)', EXPRESSION)
    assert found is not None, 'the grammar gives no truncating example'
    function = compile_expression(found.group(1), {})
    assert function['type'] == 'int' and function['nodes'][function['output']]['definition'] == 'div'


# The helper's build, sd faked


@pytest.fixture
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    """The helpers with a Pixel Processor's function to replace: `fg`, holding one old node, `old`."""
    module = faked_helpers
    node, prop, fg = mock.MagicMock(), mock.MagicMock(), mock.MagicMock()
    prop.getId.return_value = 'perpixel'
    fg.getNodes.return_value = [mock.MagicMock(name='old')]
    vars(module)['_graph_to_edit'] = lambda identifier: mock.MagicMock()
    vars(module)['_target_of'] = lambda g, node_id, parameter: (node, prop, PIXEL)
    vars(module)['_driving_graph'] = lambda n, p: fg
    vars(module)['_make_value'] = lambda p, v: v
    vars(module).update(node=node, prop=prop, fg=fg)  # for the tests to read
    return module


FUNCTION = compile_expression('float4($pos, 0, 1)', {})  # a get_float2, a vector3 of it and a 0, a vector4 and a 1


def deleted_nodes(fg: mock.MagicMock) -> list[mock.MagicMock]:
    return [c.args[0] for c in fg.deleteNode.call_args_list]


def test_the_target_names_its_graph_and_its_package(faked_helpers: types.ModuleType) -> None:
    # with no graph given, the read and the build each take the editor's graph: a duplicate switched to between them,
    # its node ids the same, would get the function (REVIEW.md HLP-229)
    h = faked_helpers
    node, prop = mock.MagicMock(), mock.MagicMock()
    prop.getId.return_value = 'perpixel'
    vars(h).update(
        _node=lambda g, node_id: node,
        _definition_id=lambda n: 'sbs::compositing::pixelprocessor',
        _parameter=lambda n, node_id, pid: prop,
        _typed=lambda p: {'type': 'float4', 'getter': 'get_float4'},
        _graph_inputs=lambda g: [],
    )

    def graph(path: str) -> FakeGraph:
        package = mock.MagicMock()
        package.getFilePath.return_value = path
        return FakeGraph('G', package)

    read = h._target_of(graph('/p/a.sbs'), '7', None)[2]
    assert (read['graph'], read['package']) == ('G', '/p/a.sbs')
    vars(h)['_graph_to_edit'] = lambda identifier: graph('/p/copy.sbs')
    with pytest.raises(RuntimeError, match='changed since set_function read it; nothing was built'):
        h.set_function(None, read, FUNCTION)
    node.newPropertyGraph.assert_not_called()


def test_the_target_lists_the_nodes_input_values_and_only_those(faked_helpers: types.ModuleType) -> None:
    h = faked_helpers
    node, prop = mock.MagicMock(), mock.MagicMock()
    prop.getId.return_value = 'opacitymult'
    node.getProperties.return_value = [
        mock.MagicMock(**{'getId.return_value': pid}) for pid in ('opacitymult', 'source', '#v', '$outputsize', '#w')
    ]
    typed: dict[str, _Typed] = {
        '#v': {'type': 'float', 'getter': 'get_float1'},
        '#w': {'type': 'float2', 'getter': 'get_float2'},
    }
    # each connector connected into a #name, outputs too: a parameter's node drives nothing all the same
    node.getPropertyConnections.side_effect = lambda p: [connection('12', '#x', 'float')]
    vars(h).update(
        _node=lambda g, node_id: node,
        _parameter=lambda n, node_id, pid: prop,
        _is_processor_program=lambda n, p: False,
        _typed=lambda p: typed.get(p.getId(), {'type': 'float', 'getter': 'get_float1'}),
        _graph_inputs=lambda g: [],
    )
    read = h._target_of(FakeGraph('G', mock.MagicMock()), '7', 'opacitymult')[2]
    assert read['inputs'] == typed
    assert read['drives'] == []  # a parameter's: only a Value Processor's own function drives input values


def connection(node_id: str, pid: str, type_id: str) -> mock.MagicMock:
    """A connection whose other end (_other_end) is node `node_id`'s connector `pid`, of type `type_id`."""
    c = mock.MagicMock()
    c.getInputPropertyNode.return_value.getIdentifier.return_value = node_id
    c.getInputProperty.return_value.getId.return_value = pid
    c.getInputProperty.return_value.getType.return_value.getId.return_value = type_id
    return c


def test_the_target_reads_what_feeds_its_input_values_and_what_a_value_processor_drives(
    faked_helpers: types.ModuleType,
) -> None:
    h = faked_helpers
    node, prop = mock.MagicMock(), mock.MagicMock()
    prop.getId.return_value = 'function'
    fed, empty, out = (mock.MagicMock(**{'getId.return_value': pid}) for pid in ('#v', '#u', 'unique_filter_output'))
    connections = {
        '#v': [connection('9', 'unique_filter_output', 'float4')],
        '#u': [],
        'unique_filter_output': [
            connection('12', '#w', 'float2'),
            connection('13', 'inputNodeOutput', 'SDTypeTexture'),
        ],
    }
    output = h.SDPropertyCategory.Output
    node.getProperties.side_effect = lambda category: [out] if category is output else [fed, empty]
    node.getPropertyConnections.side_effect = lambda p: connections[p.getId()]
    vars(h).update(
        _node=lambda g, node_id: node,
        _parameter=lambda n, node_id, pid: prop,
        _is_processor_program=lambda n, p: True,
        _typed=lambda p: {'type': 'float2', 'getter': 'get_float2'},
        _graph_inputs=lambda g: [],
    )
    read = h._target_of(FakeGraph('G', mock.MagicMock()), '7', 'function')[2]
    assert read['fed'] == {'#v': {'end': '9.unique_filter_output', 'type': 'float4'}, '#u': None}
    assert read['drives'] == [{'end': '12.#w', 'type': 'float2'}]  # its output node's connector is no input value


def image(pid: str, connections: int) -> mock.MagicMock:
    """A processor's input image `pid`, connectable, with `connections` connections."""
    return mock.MagicMock(
        connections=[mock.MagicMock()] * connections,
        **{'getId.return_value': pid, 'isConnectable.return_value': True},
    )


@pytest.mark.parametrize(
    ('kind', 'listed', 'images'),
    [
        ('perpixel', [('input', 1), ('input:1', 1), ('input:2', 0)], [True, True]),
        # one disconnected while a later one is connected stays listed (GUIDE.md, A processor's input images)
        ('perpixel', [('input', 1), ('input:1', 0), ('input:2', 1), ('input:3', 0)], [True, False, True]),
        ('function', [('input', 0)], []),
        ('function', [('input', 0), ('input:1', 1), ('input:2', 0)], [False, True]),
        ('parameter', [('input', 1), ('input:1', 0)], None),  # a parameter's function samples none
    ],
    ids=['two connected', 'a gap', 'none', 'only input:1', "a parameter's"],
)
def test_the_target_reads_which_input_images_are_connected(
    faked_helpers: types.ModuleType, kind: str, listed: list[tuple[str, int]], images: list[bool] | None
) -> None:
    h = faked_helpers
    node, prop = mock.MagicMock(), mock.MagicMock()
    prop.getId.return_value = 'perpixel' if kind == 'perpixel' else 'function'
    # the input images, and an input value and a parameter beside them, which are none
    other = [image('#v', 1), mock.MagicMock(**{'getId.return_value': 'inputs', 'isConnectable.return_value': False})]
    node.getProperties.side_effect = lambda category: [*(image(*i) for i in listed), *other]
    node.getPropertyConnections.side_effect = lambda p: p.connections if hasattr(p, 'connections') else []
    vars(h).update(
        _node=lambda g, node_id: node,
        _parameter=lambda n, node_id, pid: prop,
        _is_processor_program=lambda n, p: kind != 'parameter',
        _typed=lambda p: {'type': 'float4', 'getter': 'get_float4'},
        _graph_inputs=lambda g: [],
    )
    assert h._target_of(FakeGraph('G', mock.MagicMock()), '7', prop.getId())[2]['images'] == images


@pytest.mark.parametrize(
    ('definition', 'into', 'refusal'),
    [
        (
            'pixelprocessor',
            'input:3',
            "input 'input:3' not on node b; connectors: ['input', 'input:1', 'input:2']: a Pixel or Value Processor "
            'lists input:1, input:2... one at a time, each once the one before it has a connection: connect an image '
            'into input:2 first',
        ),
        (
            'valueprocessor',
            'input:5',
            "input 'input:5' not on node b; connectors: ['input', 'input:1', 'input:2']: a Pixel or Value Processor "
            'lists input:1, input:2... one at a time, each once the one before it has a connection: connect an image '
            'into input:2 first',
        ),
        ('blend', 'input:3', "input 'input:3' not on node b; connectors: ['input', 'input:1', 'input:2']"),
        # no processor lists input:0 or input:01: its first input is input (REVIEW.md HLP-240)
        ('pixelprocessor', 'input:0', "input 'input:0' not on node b; connectors: ['input', 'input:1', 'input:2']"),
        ('pixelprocessor', 'input:01', "input 'input:01' not on node b; connectors: ['input', 'input:1', 'input:2']"),
        ('pixelprocessor', 'inputx', "input 'inputx' not on node b; connectors: ['input', 'input:1', 'input:2']"),
    ],
    ids=['a Pixel Processor', 'a Value Processor', 'another node', 'input:0', 'input:01', 'another connector'],
)
def test_connect_names_the_input_image_to_connect_first(
    faked_helpers: types.ModuleType, definition: str, into: str, refusal: str
) -> None:
    # Designer lists input:N once input:N-1 has a connection, and refuses one into an input it doesn't list
    # (GUIDE.md, A processor's input images)
    src, dst = mock.MagicMock(), mock.MagicMock()
    src.getProperties.return_value = [mock.MagicMock(**{'getId.return_value': 'unique_filter_output'})]
    dst.getProperties.return_value = [image('input', 1), image('input:1', 1), image('input:2', 0)]
    dst.getDefinition.return_value.getId.return_value = 'sbs::compositing::' + definition
    nodes = {'a': src, 'b': dst}
    vars(faked_helpers).update(
        _graph_to_edit=lambda identifier: mock.MagicMock(),
        _node=lambda g, node_id: nodes[node_id],
        _default_output=lambda n, outs: (outs[0], None),
    )
    with pytest.raises(RuntimeError) as e:
        faked_helpers.connect('G', 'a', 'b', into)
    assert str(e.value) == refusal
    src.newPropertyConnectionFromId.assert_not_called()


def test_the_read_counts_the_samples_of_the_definitions_the_compiler_builds(faked_helpers: types.ModuleType) -> None:
    # the helpers can't import the compiler: a sampler the read missed would go unchecked
    from function_compiler import SAMPLES

    assert set(faked_helpers._SAMPLERS) == {'sbs::function::' + d for d in SAMPLES.values()}


def test_an_input_value_takes_the_types_a_value_processor_gives(faked_helpers: types.ModuleType) -> None:
    # connect makes an input value only for a value a Value Processor can give, which the server's check of its
    # function lists too
    from server_tools import functions

    assert faked_helpers._VALUE_TYPES == functions.VALUE


@pytest.mark.parametrize(
    ('name', 'taken'), [('#v', True), ('#a_2B', True), ('#1x', False), ('#a-b', False), ('#', False)]
)
def test_connect_makes_the_input_values_set_function_reads(
    faked_helpers: types.ModuleType, name: str, taken: bool
) -> None:
    # a name connect takes compiles as that input value; one it refuses doesn't (a comment, or another name)
    src, dst = mock.MagicMock(), mock.MagicMock()
    src.getPropertyFromId.return_value.getType.return_value.getId.return_value = 'float'
    dst.getPropertyFromId.return_value = None  # none yet: connect makes it
    if taken:
        assert faked_helpers._input_value(src, 'a', 'out', dst, 'b', name).startswith('; made %s, ' % name)
        # made of the very type the output gives (REVIEW.md TST-724)
        given = src.getPropertyFromId.return_value.getType.return_value
        dst.newProperty.assert_called_once_with(name, given, faked_helpers.SDPropertyCategory.Input)
        assert compile_expression(name, {name: 'float'})['nodes'][0]['constant'] == name
    else:
        with pytest.raises(RuntimeError, match='^input value %r' % name):
            faked_helpers._input_value(src, 'a', 'out', dst, 'b', name)
        with pytest.raises(ExpressionError):
            compile_expression(name, {name: 'float'})


@pytest.mark.parametrize(
    'read',
    [
        PIXEL_GREY,
        {**PIXEL, 'fed': {'#v': None}},
        {**PIXEL, 'drives': [{'end': '12.#v', 'type': 'float'}]},
    ],
    ids=['colorswitch', 'what feeds an input value', 'what it drives'],
)
def test_the_build_refuses_a_target_changed_since_the_read(helpers: types.ModuleType, read: _Target) -> None:
    with pytest.raises(RuntimeError, match='changed since set_function read it; nothing was built'):
        helpers.set_function('G', read, FUNCTION)
    helpers.fg.newNode.assert_not_called()
    helpers.node.newPropertyGraph.assert_not_called()


def test_the_build_replaces_the_old_nodes_once_the_new_output_is_set(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    fg: mock.MagicMock = helpers.fg
    [old] = fg.getNodes.return_value
    order: list[str] = []
    fg.setOutputNode.side_effect = lambda n, on: order.append('output')
    fg.deleteNode.side_effect = lambda n: order.append('deleted')
    helpers.set_function('G', PIXEL, FUNCTION)
    assert fg.newNode.call_count == len(FUNCTION['nodes'])
    assert order == ['output', 'deleted'] and deleted_nodes(fg) == [old]
    assert fg.setOutputNode.call_args.args == (fg.newNode.return_value, True)
    assert capsys.readouterr().out == (
        '7.perpixel: built 5 function nodes, its output a float4; deleted the 1 node it replaced\n'
    )


def failing_on(count: int) -> Callable[[str], mock.MagicMock]:
    """newNode raising on its `count`th call, each call before giving a node of its own."""
    made = 0

    def new_node(definition: str) -> mock.MagicMock:
        nonlocal made
        made += 1
        if made == count:
            raise RuntimeError('newNode failed')
        return mock.MagicMock(name='new %d' % made)

    return new_node


def test_a_failed_build_deletes_only_the_new_nodes(helpers: types.ModuleType) -> None:
    fg: mock.MagicMock = helpers.fg
    fg.newNode.side_effect = failing_on(3)
    with pytest.raises(RuntimeError, match='newNode failed'):
        helpers.set_function('G', PIXEL, FUNCTION)
    assert [n._mock_name for n in deleted_nodes(fg)] == ['new 1', 'new 2']  # the old node, and its output, are kept
    fg.setOutputNode.assert_not_called()


def test_a_function_missing_a_field_builds_nothing(helpers: types.ModuleType) -> None:
    # read after the function graph was made, it left the graph, its stored value reset (REVIEW.md HLP-226)
    vars(helpers)['_driving_graph'] = lambda n, p: None
    with pytest.raises(KeyError):
        helpers.set_function('G', PIXEL, {'type': 'float4', 'output': 0})
    helpers.node.newPropertyGraph.assert_not_called()


def taken_back(helpers: types.ModuleType) -> list[object]:
    """With no function before the build, the calls of _delete_function a failed build makes, and the value it puts
    back read as 'the value before'."""
    deleted: list[object] = []
    vars(helpers)['_driving_graph'] = lambda n, p: None
    vars(helpers)['_delete_function'] = lambda n, p: deleted.append((n, p))
    vars(helpers)['_value'] = lambda n, p: 'the value before'
    return deleted


def test_a_failure_reading_the_old_nodes_takes_the_new_function_back(helpers: types.ModuleType) -> None:
    # read outside the try, it left the graph made for the build (REVIEW.md HLP-226)
    deleted = taken_back(helpers)
    helpers.node.newPropertyGraph.return_value.getNodes.side_effect = RuntimeError('getNodes failed')
    with pytest.raises(RuntimeError, match='getNodes failed'):
        helpers.set_function('G', PIXEL, FUNCTION)
    assert deleted == [(helpers.node, helpers.prop)]
    helpers.node.setPropertyValue.assert_called_once_with(helpers.prop, 'the value before')


def test_a_parameter_newpropertygraph_makes_no_function_on_is_refused_naming_it(helpers: types.ModuleType) -> None:
    # sd types its result as optional, and Designer gives None on a curve's or a gradient's parameters: the build failed
    # with "'NoneType' object has no attribute 'getNodes'" (REVIEW.md HLP-249)
    deleted = taken_back(helpers)
    helpers.node.newPropertyGraph.return_value = None
    with pytest.raises(RuntimeError, match=r"^7\.perpixel takes no function: Designer's newPropertyGraph made none$"):
        helpers.set_function('G', PIXEL, FUNCTION)
    assert deleted == [(helpers.node, helpers.prop)]


def test_expose_refuses_a_parameter_newpropertygraph_makes_no_function_on(faked_helpers: types.ModuleType) -> None:
    # the same None in expose_param: the graph input it made goes too (REVIEW.md HLP-249)
    h = faked_helpers
    g, node, prop = mock.MagicMock(), mock.MagicMock(), mock.MagicMock()
    g.getPropertyFromId.return_value = None
    node.getPropertyGraph.return_value = None  # no function before
    node.newPropertyGraph.return_value = None
    prop.getType.return_value.getId.return_value = 'float'
    vars(h).update(
        _graph_to_edit=lambda identifier: g,
        _node=lambda g, node_id: node,
        _parameter=lambda n, node_id, pid: prop,
        SDTypeEnum=type('SDTypeEnum', (), {}),  # the parameter's type is none
    )
    with pytest.raises(
        RuntimeError, match=r"^7\.opacitymult takes no function: Designer's newPropertyGraph made none$"
    ):
        h.expose_param('G', '7', 'opacitymult')
    g.deleteProperty.assert_called_once_with(g.newProperty.return_value)


def absolute() -> object:
    """The Absolute inheritance, as the faked sd gives it."""
    return sys.modules['sd.api.sdproperty'].SDPropertyInheritanceMethod.Absolute


@pytest.mark.parametrize(
    ('read', 'expression', 'said'),
    [
        (
            SIZE,
            'int2(2, 2)',
            "7.$outputsize is Absolute now, as apply_edits' set makes it: the function gives log2 of the size in "
            'pixels (0 is 1 px, 11 is 2048 px, 13 is 8192 px, the largest)',
        ),
        (FORMAT, 'int(1)', "7.$format is Absolute now, as apply_edits' set makes it"),
    ],
    ids=['$outputsize', '$format'],
)
def test_a_dollar_parameter_is_made_absolute_once_its_function_is_built(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], read: _Target, expression: str, said: str
) -> None:
    # inherited, a function on $format is ignored, and one on $outputsize is an offset (GUIDE.md, Building a function
    # graph; REVIEW.md HLP-225)
    vars(helpers)['_target_of'] = lambda g, node_id, parameter: (helpers.node, helpers.prop, read)
    helpers.prop.getId.return_value = read['parameter']
    order: list[str] = []
    helpers.fg.setOutputNode.side_effect = lambda n, on: order.append('output')
    helpers.node.setPropertyInheritanceMethod.side_effect = lambda p, method: order.append(
        'absolute' if (p, method) == (helpers.prop, absolute()) else 'other'
    )
    helpers.set_function('G', read, compile_expression(expression, {}))
    assert order == ['output', 'absolute']
    assert capsys.readouterr().out.rstrip('\n').splitlines()[-1] == said


def test_a_seed_keeps_its_inheritance(helpers: types.ModuleType) -> None:
    # inherited, a seed counts too: added to its parent's, it follows the graph's seed (GUIDE.md, Graph size)
    vars(helpers)['_target_of'] = lambda g, node_id, parameter: (helpers.node, helpers.prop, INT)
    helpers.prop.getId.return_value = '$randomseed'
    helpers.set_function('G', INT, compile_expression('int(3)', {}))
    helpers.node.setPropertyInheritanceMethod.assert_not_called()


def test_a_constant_size_above_13_is_refused_as_set_refuses_it(helpers: types.ModuleType) -> None:
    # Designer computes 8192 px from 15, refusing nothing (REVIEW.md HLP-225)
    vars(helpers)['_target_of'] = lambda g, node_id, parameter: (helpers.node, helpers.prop, SIZE)
    vars(helpers)['_driving_graph'] = lambda n, p: None
    with pytest.raises(RuntimeError) as raised:
        helpers.set_function('G', SIZE, compile_expression('int2(15, 15)', {}))
    assert str(raised.value) == (
        '$outputsize is log2 of the size in pixels (0 is 1 px, 11 is 2048 px, 13 is 8192 px, the largest), not (15, 15)'
    )
    helpers.node.newPropertyGraph.assert_not_called()


def test_a_failed_build_on_a_new_function_deletes_it_and_puts_the_value_back(helpers: types.ModuleType) -> None:
    # a parameter with no function: the one made for the build goes, and the value it reset comes back, as expose's does
    deleted = taken_back(helpers)
    fg: mock.MagicMock = helpers.node.newPropertyGraph.return_value
    fg.getNodes.return_value = []
    fg.newNode.side_effect = failing_on(2)
    with pytest.raises(RuntimeError, match='newNode failed'):
        helpers.set_function('G', PIXEL, FUNCTION)
    assert deleted == [(helpers.node, helpers.prop)]
    helpers.node.setPropertyValue.assert_called_once_with(helpers.prop, 'the value before')


def plain(annotation: object) -> object:
    """An annotation as a value to compare: a TypedDict as its fields, a type alias as what it stands for, a union as
    the set of its members, a generic as its origin and arguments (REVIEW.md HLP-228)."""
    if isinstance(annotation, typing.TypeAliasType):
        return plain(annotation.__value__)
    if typing.is_typeddict(annotation):
        return ('TypedDict', tuple((k, plain(v)) for k, v in typing.get_type_hints(annotation).items()))
    origin, args = typing.get_origin(annotation), typing.get_args(annotation)
    if origin in (typing.Union, types.UnionType):
        members: set[object] = set()
        for a in args:
            p = plain(a)
            members |= p if isinstance(p, frozenset) else {p}
        return frozenset(members)
    if origin is not None:
        return (origin, tuple(plain(a) for a in args))
    return annotation


def test_the_build_reads_the_compilers_function_and_the_reads_target_as_they_are(helpers: types.ModuleType) -> None:
    # the helpers can't import the compiler's types or the server's, so they hold their own: the same fields, each of
    # the same type
    from function_compiler import Function
    from server_tools import functions

    assert plain(helpers._Function) == plain(Function)
    assert plain(helpers._Target) == plain(functions._Target)
    assert plain(helpers._ResourceTarget) == plain(functions._ResourceTarget)


def test_the_server_uses_only_the_compilers_public_names() -> None:
    # REVIEW.md HLP-228: it imported _a
    from server_tools import functions

    tree = ast.parse(Path(functions.__file__).read_text(encoding='utf-8'))
    names = [
        a.name for n in tree.body if isinstance(n, ast.ImportFrom) and n.module == 'function_compiler' for a in n.names
    ]
    assert names and not [n for n in names if n.startswith('_')], names


# A function graph of the package (set_function's `function`)

FLOAT2: _Typed = {'type': 'float2', 'getter': 'get_float2'}
FLOAT1: _Typed = {'type': 'float', 'getter': 'get_float1'}
# the package's function graphs as the read gives them: paint(uv, k), a float4; wrap(uv), calling paint
PAINT: _Resource = {'inputs': {'uv': FLOAT2, 'k': FLOAT1}, 'output': 'float4', 'calls': [], 'samples': []}
WRAP: _Resource = {'inputs': {'uv': FLOAT2}, 'output': 'float4', 'calls': ['paint'], 'samples': []}


def resource_target(
    functions: dict[str, _Resource],
    callers: list[str] | None = None,
    fx_map_callers: list[str] | None = None,
    reaching: list[_Reach] | None = None,
) -> _ResourceTarget:
    """What the read prints for the function graph paint of G's package."""
    return {
        'graph': 'G',
        'package': '/p/mine.sbs',
        'function': 'paint',
        'functions': functions,
        'callers': callers or [],
        'fx_map_callers': fx_map_callers or [],
        'reaching': reaching or [],
    }


def faked_resource(monkeypatch: pytest.MonkeyPatch, read: _ResourceTarget) -> Faked:
    return Faked(monkeypatch, 'FUNCTION_RESOURCE=%s\n' % json.dumps(read))


def test_a_function_graph_is_read_compiled_with_its_inputs_and_built_in_one_undo_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read = resource_target({'wrap': WRAP})
    fake = faked_resource(monkeypatch, read)
    said = server.set_function('float4(uv, k, 1)', function='paint', inputs={'uv': 'float2', 'k': 'float'}, graph='G')
    assert fake.reads == ["function_resource_target('G', 'paint')"]
    [(call, label)] = fake.edits
    assert call.startswith('set_function_resource(') and label == 'Claude: set function graph paint'
    # the read passed back, for the build to check it again; the inputs in their order; the nodes compiled from them
    function = compile_expression('float4(uv, k, 1)', {'uv': 'float2', 'k': 'float'}, {}, 'paint')
    assert arguments(call) == ['G', read, [('uv', 'float2'), ('k', 'float')], function]
    assert said == '7.perpixel: built 3 function nodes, its output a float4'  # what the build printed


def test_a_function_graphs_expression_reads_pos(monkeypatch: pytest.MonkeyPatch) -> None:
    # a function graph can't know its callers: _set_resource passes no kind (REVIEW.md TST-759)
    fake = faked_resource(monkeypatch, resource_target({}))
    server.set_function('$pos.x', function='paint')
    [(call, _)] = fake.edits
    assert arguments(call)[3] == compile_expression('$pos.x', {}, {}, 'paint', images=True)


@pytest.mark.parametrize('inputs', [None, {}], ids=['left out', 'empty, as a client fills an optional field'])
def test_a_function_graph_keeps_its_inputs_when_none_are_given(
    monkeypatch: pytest.MonkeyPatch, inputs: dict[str, str] | None
) -> None:
    fake = faked_resource(monkeypatch, resource_target({'paint': PAINT}))
    server.set_function('float4(uv.yx, k, 1)', function='paint', inputs=inputs)
    [(call, _)] = fake.edits
    function = arguments(call)[3]
    assert arguments(call)[2] is None and isinstance(function, dict)
    assert function == compile_expression('float4(uv.yx, k, 1)', {'uv': 'float2', 'k': 'float'}, {}, 'paint')


def test_inputs_left_out_reach_the_build_as_none_to_keep_them(monkeypatch: pytest.MonkeyPatch) -> None:
    # a colour input, read as a float4, compares equal to itself only by Designer's type: passed as a float4 it would
    # be made again, and the calls' connections into it lost (REVIEW.md HLP-233)
    colour: _Typed = {'type': 'ColorRGBA', 'getter': 'get_float4'}
    tinted: _Resource = {'inputs': {'tint': colour, 'k': FLOAT1}, 'output': 'float', 'calls': [], 'samples': []}
    fake = faked_resource(monkeypatch, resource_target({'paint': tinted}))
    server.set_function('tint.x * k', function='paint')
    [(call, _)] = fake.edits
    assert arguments(call)[2:] == [
        None,
        compile_expression('tint.x * k', {'tint': 'float4', 'k': 'float'}, {}, 'paint'),
    ]


def test_a_new_function_graph_given_no_inputs_has_none(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = faked_resource(monkeypatch, resource_target({}))
    server.set_function('3.14159', function='paint')
    [(call, _)] = fake.edits
    assert arguments(call)[2] is None  # a new one has none to keep


def test_a_nodes_expression_calls_the_packages_function_graphs(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = faked(monkeypatch, {**PIXEL, 'functions': {'paint': PAINT, 'wrap': WRAP}})
    server.set_function('wrap($pos)', '7')
    [(call, _)] = fake.edits
    package = {
        'paint': Resource({'uv': 'float2', 'k': 'float'}, 'float4', ()),
        'wrap': Resource({'uv': 'float2'}, 'float4', ('paint',)),
    }
    function = arguments(call)[2]
    assert function == compile_expression('wrap($pos)', TYPES, package)
    assert isinstance(function, dict) and function['nodes'][-1]['definition'] == 'instance'


def resource_refused(
    monkeypatch: pytest.MonkeyPatch, read: _ResourceTarget, expression: str, inputs: dict[str, str] | None = None
) -> str:
    """set_function's refusal of `expression` as paint's function, with `inputs`; nothing built."""
    fake = faked_resource(monkeypatch, read)
    with pytest.raises(server.ToolError) as raised:
        server.set_function(expression, function='paint', inputs=inputs)
    assert fake.edits == []
    return str(raised.value)


def test_a_function_graph_calling_itself_through_another_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    said = resource_refused(monkeypatch, resource_target({'paint': PAINT, 'wrap': WRAP}), 'wrap(uv)')
    assert said == (
        "column 1: `wrap(uv)` calls wrap, which calls paint: a function can't call itself, through others either. "
        'Nothing was built.'
    )


def test_a_function_graph_reads_only_its_own_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    # the graph's inputs aren't its own: the instance passes none of them
    said = resource_refused(monkeypatch, resource_target({}), 'uv.x + tint.x', {'uv': 'float2'})
    assert said == 'column 8: unknown name `tint`; its inputs are uv. Nothing was built.'


@pytest.mark.parametrize(
    ('call', 'said'),
    [
        (
            lambda: server.set_function('0.5'),
            "Give node_id, for a node's function, or function, for a function graph of the package.",
        ),
        (
            lambda: server.set_function('0.5', '7', function='paint'),
            "Give node_id, for a node's function, or function, for a function graph of the package, not both.",
        ),
        (
            lambda: server.set_function('0.5', parameter='perpixel', function='paint'),
            "parameter is a node's: a function graph has none.",
        ),
        (
            lambda: server.set_function('0.5', '7', inputs={'uv': 'float2'}),
            "inputs are a function graph's: a node's function reads its graph's inputs.",
        ),
    ],
    ids=['neither', 'both', 'a parameter for a function graph', 'inputs for a node'],
)
def test_set_function_takes_a_node_or_a_function_graph(
    monkeypatch: pytest.MonkeyPatch, call: Callable[[], str], said: str
) -> None:
    fake = faked(monkeypatch, PIXEL)
    with pytest.raises(server.ToolError) as raised:
        call()
    assert str(raised.value) == said + ' Nothing was built.'
    assert fake.reads == [] and fake.edits == []


@pytest.mark.parametrize(
    ('function', 'inputs', 'said'),
    [
        ('clamp', None, '`clamp` is a function of the grammar, which a call by that name would build'),
        ('float3', None, '`float3` is a cast of the grammar, which a call by that name would build'),
        (
            '2pi',
            None,
            '`2pi` is not a name an expression can write: write letters, digits and _, not starting with a digit',
        ),
        (
            'paint',
            {'not': 'float'},
            "input `not`: `not` is one of Python's keywords, which an expression can't write as a name",
        ),
        (
            'paint',
            {'uv': 'string'},
            "input `uv`: string is no type a function graph's input takes: give bool, int, int2, int3, int4, float, "
            'float2, float3 or float4',
        ),
    ],
    ids=['a function', 'a cast', 'no name', 'an input no name', 'an input of another type'],
)
def test_a_function_graph_an_expression_could_not_call_is_refused_before_the_read(
    monkeypatch: pytest.MonkeyPatch, function: str, inputs: dict[str, str] | None, said: str
) -> None:
    fake = faked_resource(monkeypatch, resource_target({}))
    with pytest.raises(server.ToolError) as raised:
        server.set_function('0.5', function=function, inputs=inputs)
    assert str(raised.value) == said + '. Nothing was built.'
    assert fake.reads == [] and fake.edits == []


def test_a_function_graph_gives_a_value(monkeypatch: pytest.MonkeyPatch) -> None:
    # a string can't be an input, so no expression gives one: only a person's function graph could
    said = resource_refused(
        monkeypatch, resource_target({'text': {'inputs': {}, 'output': 'string', 'calls': [], 'samples': []}}), 'text()'
    )
    assert said == (
        'paint: the expression gives a string, and a function graph gives a bool, an int to int4 or a float to float4. '
        'Nothing was built.'
    )


CALLED = resource_target({'paint': PAINT}, callers=['G/7.perpixel', 'wrap'])


@pytest.mark.parametrize(
    ('expression', 'inputs'),
    [('float4(uv, 0, 1)', {'uv': 'float2'}), ('uv.x', None), ('float4(k, uv, 1)', {'k': 'float', 'uv': 'float2'})],
    ids=['an input less', 'another output', 'the inputs in another order'],
)
def test_a_function_graph_whose_inputs_or_output_change_names_what_calls_it(
    monkeypatch: pytest.MonkeyPatch, expression: str, inputs: dict[str, str] | None
) -> None:
    # Designer drops a call's connection into an input deleted or made again, which then reads 0, and the call takes
    # the new output's type (GUIDE.md, Function graphs of the package)
    faked_resource(monkeypatch, CALLED)
    said = server.set_function(expression, function='paint', inputs=inputs)
    assert said.splitlines()[-1] == (
        "paint's inputs or output changed, and G/7.perpixel and wrap call it: give each its function again with "
        'set_function, as a call reads 0 for an input it lost, and gives the new output.'
    ), said


# what set_function says of an FX-Map's call, which it can't reach (REVIEW.md HLP-239)
FX_MAP_SAID = (
    "paint's inputs or output changed, and G/9/3.opacity, in an FX-Map, calls it, which set_function can't reach: tell "
    'the user to give each its function again in Designer.'
)


@pytest.mark.parametrize(
    ('callers', 'said'),
    [
        (
            ['G/7.perpixel'],
            [
                "paint's inputs or output changed, and G/7.perpixel calls it: give each its function again with "
                'set_function, as a call reads 0 for an input it lost, and gives the new output.',
                FX_MAP_SAID,
            ],
        ),
        (
            [],
            [FX_MAP_SAID],
        ),
    ],
    ids=['and a node', 'alone'],
)
def test_a_call_from_an_fx_map_is_named_for_the_user_to_set_in_designer(
    monkeypatch: pytest.MonkeyPatch, callers: list[str], said: list[str]
) -> None:
    # set_function can't reach an FX-Map's inner node (REVIEW.md HLP-239)
    faked_resource(monkeypatch, resource_target({'paint': PAINT}, callers, ['G/9/3.opacity']))
    lines = server.set_function('float4(uv, 0, 1)', function='paint', inputs={'uv': 'float2'}).splitlines()
    assert lines[1:] == said


def test_a_function_graph_whose_inputs_and_output_stay_adds_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    faked_resource(monkeypatch, CALLED)
    said = server.set_function('float4(uv.yx, k * 0.5, 1)', function='paint')
    assert said == '7.perpixel: built 3 function nodes, its output a float4'


def test_a_function_graph_sampling_an_input_its_callers_lack_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    # each node calling it, directly or through others, reads (0, 0, 0, 0) there (REVIEW.md SRV-199)
    reaching: list[_Reach] = [
        {'where': 'G/7', 'parameter': 'perpixel', 'images': [True]},
        {'where': 'G/8', 'parameter': 'function', 'images': [True, True]},
        {'where': 'G/9', 'parameter': 'opacity', 'images': None},
    ]
    faked_resource(monkeypatch, resource_target({}, reaching=reaching))
    said = server.set_function('sample(1, uv)', function='paint', inputs={'uv': 'float2'})
    assert said.splitlines()[1:] == [
        "paint is called from G/7.perpixel, and G/7.input:1 %s (apply_edits' connect)." % UNTIL,
        "G/9.opacity calls paint, which samples an input image, and only a Pixel or Value Processor's function has "
        'input images: give G/9.opacity another function with set_function.',
    ]
    faked_resource(monkeypatch, resource_target({}, reaching=reaching))
    assert '\n' not in server.set_function('0.5', function='paint', inputs={'uv': 'float2'})  # sampling nothing


def test_a_refused_read_of_a_function_graph_builds_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = Faked(monkeypatch, "--- ERROR ---\nRuntimeError: the package holds a graph named 'G' already")
    with pytest.raises(server.ToolError, match=r"^RuntimeError: the package holds a graph named 'G' already$"):
        server.set_function('0.5', function='G')
    assert fake.edits == []


# The helper's read and build of a function graph of the package, sd faked


class FakeFunction:
    """Stands for a function graph of the package: the helpers' SDSBSFunctionGraph is set to this class, so that their
    isinstance checks take it for one, and its sNew makes one. It holds its identifier, its inputs (each a property
    with its type's id), its nodes and its output node, and whether it was deleted."""

    made: list['FakeFunction']  # set per test: the function graphs sNew made

    def __init__(
        self, identifier: str = '', inputs: tuple[tuple[str, str], ...] = (), output: str | None = None
    ) -> None:
        self.identifier, self.deleted = identifier, False
        self.package = PACKAGE
        self.inputs = [typed_property(pid, type_id) for pid, type_id in inputs]
        self.nodes: list[mock.MagicMock] = [mock.MagicMock(name='old')]
        self.outputs = [] if output is None else [typed_output(output)]
        self.newNode = mock.MagicMock(side_effect=lambda definition: mock.MagicMock(name=definition))
        self.newInstanceNode = mock.MagicMock(side_effect=lambda resource: mock.MagicMock(name='instance'))
        self.setOutputNode, self.deleteNode = mock.MagicMock(), mock.MagicMock()

    @staticmethod
    def sNew(package: mock.MagicMock) -> 'FakeFunction':
        made = FakeFunction()
        made.nodes = []  # a new function graph has none
        FakeFunction.made.append(made)
        return made

    def getIdentifier(self) -> str:
        return self.identifier

    def setIdentifier(self, identifier: str) -> None:
        self.identifier = identifier

    def getPackage(self) -> mock.MagicMock:
        return self.package

    def getProperties(self, category: object) -> list[mock.MagicMock]:
        return list(self.inputs)

    def newProperty(self, pid: str, of: mock.MagicMock, category: object) -> mock.MagicMock:
        made = typed_property(pid, of.getId())
        self.inputs.append(made)
        return made

    def deleteProperty(self, p: mock.MagicMock) -> None:
        self.inputs.remove(p)

    def getNodes(self) -> list[mock.MagicMock]:
        return list(self.nodes)

    def getOutputNodes(self) -> list[mock.MagicMock]:
        return list(self.outputs)

    def delete(self) -> None:
        self.deleted = True


PACKAGE = mock.MagicMock(**{'getFilePath.return_value': '/p/mine.sbs'})


def typed_property(pid: str, type_id: str) -> mock.MagicMock:
    return mock.MagicMock(
        type_id=type_id, **{'getId.return_value': pid, 'getType.return_value.getId.return_value': type_id}
    )


def typed_output(type_id: str) -> mock.MagicMock:
    """An output node whose unique_filter_output lists the one type `type_id`."""
    listed = [mock.MagicMock(**{'getId.return_value': type_id})]
    return mock.MagicMock(**{'getPropertyFromId.return_value.getTypes.return_value': listed})


def instance_of(resource: FakeFunction) -> mock.MagicMock:
    """An instance node of `resource`."""
    return mock.MagicMock(
        **{
            'getDefinition.return_value.getId.return_value': 'sbs::function::instance',
            'getReferencedResource.return_value': resource,
        }
    )


class GraphOfNodes(FakeGraph):
    """A compositing graph of the package, with its nodes."""

    def __init__(self, identifier: str, nodes: list[mock.MagicMock]) -> None:
        super().__init__(identifier, PACKAGE)
        self.nodes = nodes

    def getNodes(self) -> list[mock.MagicMock]:
        return self.nodes


@pytest.fixture
def package(faked_helpers: types.ModuleType) -> types.ModuleType:
    """The helpers with the package of G holding the resources a test puts in PACKAGE's list, sd's types faked."""
    h = faked_helpers
    FakeFunction.made = []
    PACKAGE.getChildrenResources.return_value = []
    vars(h).update(
        SDSBSFunctionGraph=FakeFunction,
        SDSBSCompGraph=FakeGraph,
        SDTypeEnum=type('SDTypeEnum', (), {}),  # none is: the helpers' own _typed gives each its getter (TST-734)
        _new_type=lambda type_id: mock.MagicMock(**{'getId.return_value': type_id}),
        _type=lambda p: p.getType(),
        _make_value=lambda p, v: v,
    )
    return h


def holding(*resources: object) -> GraphOfNodes:
    """G, its package holding G and `resources`."""
    g = GraphOfNodes('G', [])
    PACKAGE.getChildrenResources.return_value = [g, *resources]
    return g


def test_the_read_gives_the_packages_function_graphs_and_what_calls_the_one_set(package: types.ModuleType) -> None:
    pi = FakeFunction('pi', output='float')
    paint = FakeFunction('paint', (('uv', 'float2'), ('k', 'float')), 'float4')
    paint.nodes = [instance_of(pi), mock.MagicMock(name='add')]
    wrap = FakeFunction('wrap', (('uv', 'float2'),), 'float4')
    wrap.nodes = [instance_of(paint)]
    other = FakeFunction('Pi', output='float')
    other.package = mock.MagicMock(**{'getFilePath.return_value': '/library/functions.sbs'})
    wrap.nodes.append(instance_of(other))  # another package's: no call of this one
    pp = mock.MagicMock(**{'getIdentifier.return_value': '7'})
    perpixel = mock.MagicMock(**{'getId.return_value': 'perpixel'})
    caller = mock.MagicMock(**{'getNodes.return_value': [instance_of(paint)]})
    # an FX-Map whose inner node 3's opacity calls paint too (REVIEW.md HLP-236)
    inner = mock.MagicMock(**{'getIdentifier.return_value': '3'})
    opacity = mock.MagicMock(**{'getId.return_value': 'opacity'})
    fx = mock.MagicMock(
        **{
            'getIdentifier.return_value': '9',
            'getDefinition.return_value.getId.return_value': 'sbs::compositing::fxmaps',
            'getReferencedResource.return_value.getNodes.return_value': [inner],
        }
    )
    g = holding(pi, paint, wrap)
    g.nodes = [pp, fx]
    functions = {id(pp): [(perpixel, caller)], id(inner): [(opacity, caller)]}
    vars(package).update(
        _functions_of=lambda node: functions.get(id(node), []),
        _images=lambda node, p: [True],
    )
    read = package._resource_target(g, 'paint')
    assert read == {
        'graph': 'G',
        'package': '/p/mine.sbs',
        'function': 'paint',
        'functions': {
            'pi': {'inputs': {}, 'output': 'float', 'calls': [], 'samples': []},
            'paint': {
                'inputs': {
                    'uv': {'type': 'float2', 'getter': 'get_float2'},
                    'k': {'type': 'float', 'getter': 'get_float1'},
                },
                'output': 'float4',
                'calls': ['pi'],
                'samples': [],
            },
            'wrap': {
                'inputs': {'uv': {'type': 'float2', 'getter': 'get_float2'}},
                'output': 'float4',
                'calls': ['paint'],
                'samples': [],
            },
        },
        'callers': ['wrap', 'G/7.perpixel'],
        'fx_map_callers': ['G/9/3.opacity'],
        'reaching': [{'where': 'G/7', 'parameter': 'perpixel', 'images': [True]}],
    }


def test_the_read_gives_each_nodes_function_reaching_the_function_graph_with_its_images(
    package: types.ModuleType,
) -> None:
    # a node's function calling wrap, which calls paint, samples what paint samples (REVIEW.md SRV-199)
    paint = FakeFunction('paint', (('uv', 'float2'),), 'float4')
    wrap = FakeFunction('wrap', (('uv', 'float2'),), 'float4')
    wrap.nodes = [instance_of(paint)]
    nodes = [mock.MagicMock(**{'getIdentifier.return_value': i}) for i in ('7', '8', '9')]
    perpixel, opacity = (mock.MagicMock(**{'getId.return_value': pid}) for pid in ('perpixel', 'opacity'))
    calls_wrap = mock.MagicMock(**{'getNodes.return_value': [instance_of(wrap)]})
    calls_nothing = mock.MagicMock(**{'getNodes.return_value': []})
    functions = {
        id(nodes[0]): [(perpixel, calls_wrap)],
        id(nodes[1]): [(opacity, calls_wrap)],
        id(nodes[2]): [(perpixel, calls_nothing)],
    }
    g = holding(paint, wrap)
    g.nodes = nodes
    vars(package).update(
        _functions_of=lambda node: functions.get(id(node), []),
        _images=lambda node, p: [True, False] if p is perpixel else None,
    )
    read = package._resource_target(g, 'paint')
    assert read['callers'] == ['wrap']  # its own inputs are connected by wrap's call only
    assert read['reaching'] == [
        {'where': 'G/7', 'parameter': 'perpixel', 'images': [True, False]},
        {'where': 'G/8', 'parameter': 'opacity', 'images': None},  # a parameter's function has none
    ]


def sampler(definition: str, index: int, mode: int) -> mock.MagicMock:
    """A samplecol or samplelum node (`definition`) of the input image `index`, in `mode`."""
    return mock.MagicMock(
        **{
            'getDefinition.return_value.getId.return_value': 'sbs::function::' + definition,
            'getPropertyValueFromId.return_value.get.return_value': mock.MagicMock(x=index, y=mode),
        }
    )


def test_the_read_gives_the_input_images_a_function_graph_samples(package: types.ModuleType) -> None:
    # the first component of its samplecol and samplelum nodes' __constant__ (GUIDE.md, Sampling an image)
    blur = FakeFunction('blur', (('uv', 'float2'),), 'float4')
    # and one of -1, made in Designer: no input image, it reads (0, 0, 0, 0) (REVIEW.md SRV-201)
    blur.nodes = [
        sampler('samplecol', 2, 1),
        sampler('samplelum', 0, 3),
        sampler('samplecol', 2, 0),
        sampler('samplecol', -1, 0),
    ]
    blur.nodes.append(mock.MagicMock(**{'getDefinition.return_value.getId.return_value': 'sbs::function::add'}))
    assert package._resource_target(holding(blur), 'paint')['functions']['blur']['samples'] == [0, 2]


def test_a_function_graph_with_no_output_of_one_type_reads_as_none(package: types.ModuleType) -> None:
    unset = FakeFunction('unset')
    unsettled = FakeFunction('unsettled', output='float')
    unsettled.outputs[0].getPropertyFromId.return_value.getTypes.return_value = [
        mock.MagicMock(**{'getId.return_value': t}) for t in ('int', 'float')
    ]
    g = holding(unset, unsettled)
    functions = package._resource_target(g, 'paint')['functions']
    assert functions['unset']['output'] is None and functions['unsettled']['output'] is None


@pytest.mark.parametrize('listed', ['None', 'raises'])
def test_a_function_graph_whose_output_types_cant_be_read_reads_as_no_output(  # REVIEW.md HLP-237
    package: types.ModuleType, listed: str
) -> None:
    # one such graph would otherwise break set_function on every node of the package, which reads them all
    odd = FakeFunction('odd', output='float')
    types_read = odd.outputs[0].getPropertyFromId.return_value.getTypes
    if listed == 'None':
        types_read.return_value = None  # sd's stub allows it
    else:
        types_read.side_effect = package.APIException('getTypes failed')
    assert package._resource_target(holding(odd), 'paint')['functions']['odd']['output'] is None


def test_the_read_refuses_an_identifier_another_resource_of_the_package_has(package: types.ModuleType) -> None:
    # Designer would name the function graph G_1 (GUIDE.md, Function graphs of the package)
    g = holding()
    with pytest.raises(RuntimeError, match=r"^the package holds a graph named 'G' already: give the function graph"):
        package._resource_target(g, 'G')


PAINT_FUNCTION = compile_expression('float4(uv, k, 1)', {'uv': 'float2', 'k': 'float'}, {}, 'paint')


def built_resource(
    package: types.ModuleType, existing: FakeFunction | None, inputs: list[tuple[str, str]] | None
) -> None:
    """set_function_resource building paint, with `existing` the package's paint or None, its read taken as is."""
    g = holding(*([existing] if existing else []))
    vars(package)['_graph_to_edit'] = lambda identifier: g
    target = package._resource_target(g, 'paint')
    package.set_function_resource('G', target, inputs, PAINT_FUNCTION)


def test_the_build_makes_a_function_graph_with_its_inputs_in_order(
    package: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    built_resource(package, None, [('uv', 'float2'), ('k', 'float')])
    [made] = FakeFunction.made
    assert made.identifier == 'paint' and not made.deleted
    assert [(p.getId(), p.type_id) for p in made.inputs] == [('uv', 'float2'), ('k', 'float')]
    assert made.newNode.call_count == len(PAINT_FUNCTION['nodes'])
    assert made.setOutputNode.call_args.args[1] is True
    assert capsys.readouterr().out == (
        'paint(uv float2, k float), a new function graph of /p/mine.sbs: built 5 function nodes, its output a float4\n'
    )


@pytest.mark.parametrize(
    ('wanted', 'kept'),
    [
        ([('uv', 'float2'), ('x', 'float')], ['uv', 'x']),
        # m comes before x: x is made again after it, as Designer lists an input made again last
        ([('uv', 'float2'), ('m', 'float'), ('x', 'float')], ['uv']),
        ([('k', 'float'), ('x', 'float')], ['k', 'x']),
    ],
    ids=['the middle one dropped', 'one put before the last', 'the first one dropped'],
)
def test_the_build_keeps_each_input_that_is_the_next_one_wanted(
    package: types.ModuleType, wanted: list[tuple[str, str]], kept: list[str]
) -> None:
    # a call keeps its connections into an input kept (REVIEW.md HLP-233; GUIDE.md, Function graphs of the package)
    paint = FakeFunction('paint', (('uv', 'float2'), ('k', 'float'), ('x', 'float')), 'float4')
    had = {p.getId(): p for p in paint.inputs}
    built_resource(package, paint, wanted)
    assert [(p.getId(), p.type_id) for p in paint.inputs] == wanted
    assert [p.getId() for p in paint.inputs if had.get(p.getId()) is p] == kept


def test_inputs_left_out_are_left_as_designer_has_them(
    package: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # a colour's ColorRGBA too, which the server reads as a float4 (REVIEW.md HLP-233)
    paint = FakeFunction('paint', (('tint', 'ColorRGBA'), ('k', 'float')), 'float')
    inputs = list(paint.inputs)
    built_resource(package, paint, None)
    assert paint.inputs == inputs
    assert capsys.readouterr().out.startswith('paint(tint ColorRGBA, k float): built ')


def test_the_inputs_are_set_once_the_output_node_moved(package: types.ModuleType) -> None:
    # a failed build then leaves them as they were (REVIEW.md HLP-234)
    paint = FakeFunction('paint', (('uv', 'float2'), ('k', 'float')), 'float4')
    order: list[str] = []
    paint.setOutputNode.side_effect = lambda n, on: order.append('output')
    added = paint.newProperty

    def new_property(pid: str, of: mock.MagicMock, category: object) -> mock.MagicMock:
        order.append('input')
        return added(pid, of, category)

    vars(paint)['newProperty'] = new_property
    built_resource(package, paint, [('uv', 'float2'), ('m', 'float')])
    assert order == ['output', 'input']


def test_a_failed_build_of_a_new_function_graph_deletes_it(
    package: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(pkg: mock.MagicMock) -> FakeFunction:
        made = FakeFunction()
        made.newNode.side_effect = failing_on(2)
        FakeFunction.made.append(made)
        return made

    monkeypatch.setattr(FakeFunction, 'sNew', staticmethod(failing))
    with pytest.raises(RuntimeError, match='newNode failed'):
        built_resource(package, None, [('uv', 'float2'), ('k', 'float')])
    [made] = FakeFunction.made
    assert made.deleted


def test_a_failed_build_leaves_a_function_graphs_inputs_and_nodes_as_they_were(package: types.ModuleType) -> None:
    # the calls' connections into them too: none is deleted or made again (REVIEW.md HLP-234)
    paint = FakeFunction('paint', (('uv', 'float2'), ('k', 'float')), 'float4')
    inputs, old = list(paint.inputs), paint.nodes[0]
    paint.newNode.side_effect = failing_on(3)
    with pytest.raises(RuntimeError, match='newNode failed'):
        built_resource(package, paint, [('uv', 'float2'), ('m', 'float')])
    assert not paint.deleted and paint.inputs == inputs
    assert [c.args[0]._mock_name for c in paint.deleteNode.call_args_list] == ['new 1', 'new 2']
    assert old in paint.nodes
    paint.setOutputNode.assert_not_called()


def renamed_input(made: FakeFunction) -> None:
    """`made`'s newProperty gives `k` the id `k_1`, as Designer could (REVIEW.md HLP-235)."""
    added = made.newProperty
    vars(made)['newProperty'] = lambda pid, of, category: added('k_1' if pid == 'k' else pid, of, category)


def renamed_graph(made: FakeFunction) -> None:
    """`made` named paint_1 whatever it is given, as Designer names one whose identifier is taken."""
    vars(made)['setIdentifier'] = lambda identifier: setattr(made, 'identifier', 'paint_1')


def failing_input(made: FakeFunction) -> None:
    """`made`'s newProperty raising."""
    vars(made)['newProperty'] = mock.MagicMock(side_effect=RuntimeError('newProperty failed'))


@pytest.mark.parametrize(
    ('change', 'said'),
    [
        (
            renamed_input,
            'Designer gave the function graph paint the inputs uv float2, k_1 float, not uv float2, k float',
        ),
        (renamed_graph, 'Designer named the function graph paint_1, not paint'),
        (failing_input, 'newProperty failed'),
    ],
    ids=['an input renamed', 'the graph renamed', 'an input not made'],
)
def test_a_new_function_graph_designer_doesnt_make_as_asked_is_deleted(
    package: types.ModuleType, monkeypatch: pytest.MonkeyPatch, change: Callable[[FakeFunction], None], said: str
) -> None:
    # REVIEW.md HLP-235, TST-734
    new = FakeFunction.sNew

    def made_otherwise(pkg: mock.MagicMock) -> FakeFunction:
        made = new(pkg)
        change(made)
        return made

    monkeypatch.setattr(FakeFunction, 'sNew', staticmethod(made_otherwise))
    with pytest.raises(RuntimeError, match='^' + re.escape(said)):
        built_resource(package, None, [('uv', 'float2'), ('k', 'float')])
    [made] = FakeFunction.made
    assert made.deleted


def test_an_input_not_made_leaves_an_existing_function_graph_with_its_new_function(package: types.ModuleType) -> None:
    # the output node has moved by then: the function stays, with the inputs set so far (the module docstring)
    paint = FakeFunction('paint', (('uv', 'float2'),), 'float4')
    failing_input(paint)
    # the error says so (REVIEW.md HLP-238)
    with pytest.raises(
        RuntimeError, match=r'^newProperty failed; paint keeps its new function, and the inputs set so far$'
    ):
        built_resource(package, paint, [('uv', 'float2'), ('k', 'float')])
    assert not paint.deleted and paint.setOutputNode.called
    assert [p.getId() for p in paint.inputs] == ['uv']


def test_an_existing_function_graph_whose_input_designer_renames_is_refused(package: types.ModuleType) -> None:
    paint = FakeFunction('paint', (('uv', 'float2'),), 'float4')
    renamed_input(paint)
    with pytest.raises(RuntimeError, match=r'^Designer gave the function graph paint the inputs uv float2, k_1 float'):
        built_resource(package, paint, [('uv', 'float2'), ('k', 'float')])
    assert not paint.deleted


def test_the_build_refuses_a_function_graph_changed_since_the_read(package: types.ModuleType) -> None:
    g = holding()
    vars(package)['_graph_to_edit'] = lambda identifier: g
    read = package._resource_target(g, 'paint')
    holding(FakeFunction('paint', (('uv', 'float2'),), 'float4'))  # made in Designer since
    with pytest.raises(RuntimeError, match='the function graph paint changed since set_function read it; nothing was'):
        package.set_function_resource('G', read, [('uv', 'float2')], PAINT_FUNCTION)
    assert FakeFunction.made == []


def test_a_call_builds_an_instance_node_of_the_function_graph(helpers: types.ModuleType) -> None:
    paint = FakeFunction('paint', (('uv', 'float2'), ('k', 'float')), 'float4')
    vars(helpers)['_package_functions'] = lambda pkg: {'paint': paint}
    package_ = {'paint': Resource({'uv': 'float2', 'k': 'float'}, 'float4', ())}
    helpers.set_function('G', PIXEL, compile_expression('paint($pos, 0.5)', {}, package_))
    fg: mock.MagicMock = helpers.fg
    fg.newInstanceNode.assert_called_once_with(paint)
    instance = fg.newInstanceNode.return_value
    instance.setPropertyValue.assert_not_called()  # its constant names the graph: it has no __constant__
    assert sorted(c.args[2] for c in fg.newNode.return_value.newPropertyConnectionFromId.call_args_list) == ['k', 'uv']
