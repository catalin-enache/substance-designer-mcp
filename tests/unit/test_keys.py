"""A Gradient Map's keys and a Curve's points (ROADMAP item 116), with sd faked: the shape apply_edits' set takes
(edits._given_keys), checked before anything is built, each mistake naming its key; the form fmt reads them back in
(core._shown_keys, fmt), which set takes again; and describe_graph's line of many keys. Building them in Designer, and
what they compute: the params checks of the live self-test."""

import json
import re
import types
from types import SimpleNamespace
from unittest import mock

import pytest
from test_server import _described

from project_constants import Json
from server_tools.edits import OPS

GRADIENT, CURVE = 'sbs::compositing::gradient_key_rgba', 'sbs::compositing::curve_key'
# a curve_key's members, as Designer lists them (the params facts check)
CURVE_MEMBERS = ['position', 'isLocked', 'left', 'isLeftBroken', 'right', 'isRightBroken']


class _Value:
    """An SDValue: get() gives what it holds."""

    def __init__(self, held: object) -> None:
        self.held = held

    def get(self) -> object:
        return self.held


class _Member:
    def __init__(self, member_id: str) -> None:
        self.member_id = member_id

    def getId(self) -> str:
        return self.member_id


class _StructType:
    def __init__(self, type_id: str, member_ids: list[str]) -> None:
        self.type_id, self.member_ids = type_id, member_ids

    def getId(self) -> str:
        return self.type_id

    def getMembers(self) -> list[_Member]:
        return [_Member(m) for m in self.member_ids]


class _Key:
    """An SDValueStruct of `item`, its members' values in `values`."""

    def __init__(self, item: _StructType, values: dict[str, object]) -> None:
        self.item, self.values = item, values

    def getType(self) -> _StructType:
        return self.item

    def getPropertyValueFromId(self, member_id: str) -> _Value:
        return _Value(self.values[member_id])


class _Array:
    """An SDValueArray of keys."""

    def __init__(self, keys: list[_Key]) -> None:
        self.keys = keys

    def getSize(self) -> int:
        return len(self.keys)

    def getItem(self, index: int) -> _Key:
        return self.keys[index]


@pytest.fixture
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    """The helpers, sd's SDValueArray, SDValueStruct and SDTypeStruct the fakes above."""
    vars(faked_helpers).update(SDValueArray=_Array, SDValueStruct=_Key, SDTypeStruct=_StructType)
    return faked_helpers


def _gradient_key(position: float, colour: tuple[float, float, float, float], midpoint: float = 0.0) -> _Key:
    r, g, b, a = colour
    item = _StructType(GRADIENT, ['value', 'position', 'midpoint'])
    return _Key(item, {'value': SimpleNamespace(r=r, g=g, b=b, a=a), 'position': position, 'midpoint': midpoint})


def _curve_key(point: tuple[float, float], left: tuple[float, float], right: tuple[float, float]) -> _Key:
    item = _StructType(CURVE, CURVE_MEMBERS)
    values: dict[str, object] = {
        'position': SimpleNamespace(x=point[0], y=point[1]),
        'left': SimpleNamespace(x=left[0], y=left[1]),
        'right': SimpleNamespace(x=right[0], y=right[1]),
        'isLocked': False,
        'isLeftBroken': False,
        'isRightBroken': False,
    }
    return _Key(item, values)


# --- the shape set takes


def test_gradient_keys_give_each_keys_members(helpers: types.ModuleType) -> None:
    given = [[0, [1, 0, 0]], [0.5, [0.2, 0.6, 0.2, 0.5], 0.25], ['1', ['0', 0, 1]]]
    assert helpers._given_keys('gradientrgba', GRADIENT, given) == [
        {'position': 0.0, 'value': [1.0, 0.0, 0.0], 'midpoint': 0.0},
        {'position': 0.5, 'value': [0.2, 0.6, 0.2, 0.5], 'midpoint': 0.25},
        {'position': 1.0, 'value': [0.0, 0.0, 1.0], 'midpoint': 0.0},
    ]


def test_curve_points_get_their_handles_on_the_point_unless_given(helpers: types.ModuleType) -> None:
    # a key from its position alone has handles at (0, 0), which bend the curve; on the point, straight lines (the
    # params facts check)
    given = [[0, 1], [[0.5, 0.2], [0.4, 0.1], [0.6, 0.3]], (1, -1)]
    assert helpers._given_keys('curveluminance', CURVE, given) == [
        {'position': [0.0, 1.0], 'left': [0.0, 1.0], 'right': [0.0, 1.0]},
        {'position': [0.5, 0.2], 'left': [0.4, 0.1], 'right': [0.6, 0.3]},
        {'position': [1.0, -1.0], 'left': [1.0, -1.0], 'right': [1.0, -1.0]},
    ]


def test_no_keys_is_a_value(helpers: types.ModuleType) -> None:
    assert helpers._given_keys('gradientrgba', GRADIENT, []) == []
    assert helpers._given_keys('curvered', CURVE, ()) == []


REFUSED: list[tuple[str, Json, str]] = [
    ('gradientrgba', 0.5, 'gradientrgba takes a list of keys, [[position, [r, g, b(, a)]], ...]'),
    ('gradientrgba', [[0, [1, 0, 0]], 0.5], 'gradientrgba[1]: a key is [position, [r, g, b(, a)]]'),
    ('gradientrgba', [[0, [1, 0, 0], 0.5, 1]], 'gradientrgba[0]: a key is [position, [r, g, b(, a)]]'),
    ('gradientrgba', [[0]], 'gradientrgba[0]: a key is'),
    ('gradientrgba', [[1.5, [1, 0, 0]]], 'gradientrgba[0]: position is a number from 0 to 1, not 1.5'),
    ('gradientrgba', [[0, [1, 0, 0]], [-0.1, [1, 0, 0]]], 'gradientrgba[1]: position is a number from 0'),
    ('gradientrgba', [[True, [1, 0, 0]]], 'gradientrgba[0]: position is a number from 0 to 1, not True'),
    ('gradientrgba', [['a', [1, 0, 0]]], "gradientrgba[0]: position is a number from 0 to 1, not 'a'"),
    ('gradientrgba', [[0, [1, 0]]], 'gradientrgba[0]: colour is [r, g, b] or [r, g, b, a], not [1, 0]'),
    ('gradientrgba', [[0, 'red']], "gradientrgba[0]: colour is [r, g, b] or [r, g, b, a], not 'red'"),
    ('gradientrgba', [[0, [1, None, 0]]], 'gradientrgba[0]: colour is [r, g, b] or [r, g, b, a]'),
    # a number written as a string reaches float(), which takes 'nan' and 'inf': refused as _position refuses them
    ('gradientrgba', [[0, [1, 'nan', 0]]], 'gradientrgba[0]: colour is [r, g, b] or [r, g, b, a]'),
    ('gradientrgba', [[0, [1, 0, 0], 2]], 'gradientrgba[0]: midpoint is a number from 0 to 1, not 2'),
    ('curveluminance', {'x': 0}, 'curveluminance takes a list of points, [[x, y], ...]'),
    ('curveluminance', [[0, 1], [1]], 'curveluminance[1]: a point is [x, y] or [[x, y], [left x, y], [right'),
    ('curveluminance', [[[0, 0], [0, 0]]], 'curveluminance[0]: a point is [x, y] or'),
    ('curveluminance', [[-0.2, 0]], 'curveluminance[0]: x is a number from 0 to 1, not -0.2'),
    ('curvered', [[0, 'y']], "curvered[0]: y is a number, not 'y'"),
    ('curvered', [[0, 'inf']], "curvered[0]: y is a number, not 'inf'"),
    ('curvered', [[[0, 0], [0, 0], [0.5, 'a']]], 'curvered[0]: the right handle must be [x, y], two numbers, not'),
    ('curvered', [[[0, 0], [0, 0], ['1e400', 0]]], 'curvered[0]: the right handle must be [x, y], two numbers'),
    ('curvered', [[[0, 0], 0, [0.5, 0]]], 'curvered[0]: the left handle must be [x, y], two numbers, not 0'),
    ('curvered', [[[2, 0], [0, 0], [0.5, 0]]], 'curvered[0]: x is a number from 0 to 1, not 2'),
]


@pytest.mark.parametrize('pid, value, said', REFUSED, ids=[s for _, _, s in REFUSED])
def test_a_mistake_names_its_key(helpers: types.ModuleType, pid: str, value: Json, said: str) -> None:
    with pytest.raises(RuntimeError, match='^' + re.escape(said)):
        helpers._given_keys(pid, GRADIENT if pid == 'gradientrgba' else CURVE, value)


def test_every_key_is_checked_before_any_is_given(helpers: types.ModuleType) -> None:
    # the last key's mistake refuses the whole value: set_params builds nothing of it
    with pytest.raises(RuntimeError, match=r'^gradientrgba\[2\]'):
        helpers._given_keys('gradientrgba', GRADIENT, [[0, [1, 0, 0]], [0.5, [0, 1, 0]], [9, [0, 0, 1]]])


# --- the form fmt reads them back in


def test_gradient_keys_read_back_as_set_takes_them(helpers: types.ModuleType) -> None:
    # the order kept as Designer keeps it, a midpoint only when it isn't 0 (a new key's, and the shipped files')
    keys = _Array([_gradient_key(1.0, (0, 0, 1, 1)), _gradient_key(0.0, (1, 0.5, 0, 0.25), 0.3)])
    assert helpers.fmt(keys) == ((1.0, (0, 0, 1, 1)), (0.0, (1, 0.5, 0, 0.25), 0.3))


def test_curve_points_read_back_with_their_handles_only_off_the_point(helpers: types.ModuleType) -> None:
    keys = _Array([_curve_key((0, 1), (0, 1), (0, 1)), _curve_key((0.5, 0.2), (0.4, 0.1), (0.6, 0.3))])
    assert helpers.fmt(keys) == ((0, 1), ((0.5, 0.2), (0.4, 0.1), (0.6, 0.3)))


def test_a_broken_sides_handle_reads_back_on_the_point(helpers: types.ModuleType) -> None:
    # a side marked broken computes as if its handle were on the point (the params facts check), so set's [x, y] or
    # its handle on the point computes the same again
    one = _curve_key((0.5, 0.2), (0.3, 0.2), (0.7, 0.2))
    one.values['isLeftBroken'] = True
    both = _curve_key((1, 1), (0.5, 1), (1.2, 1))
    both.values.update(isLeftBroken=True, isRightBroken=True)
    assert helpers.fmt(_Array([one, both])) == (((0.5, 0.2), (0.5, 0.2), (0.7, 0.2)), (1, 1))


def test_no_keys_read_back_as_none(helpers: types.ModuleType) -> None:
    assert helpers.fmt(_Array([])) == ()


def test_another_array_reads_back_as_before(helpers: types.ModuleType) -> None:
    other = _Array([_Key(_StructType('sbs::other', ['a']), {'a': 1.0})])
    assert helpers.fmt(other) == '<SDArray>'


def test_keys_read_back_are_taken_again_as_they_were(helpers: types.ModuleType) -> None:
    # keys read back go into set again, in the shape it takes (ROADMAP item 116): the read form, as JSON's lists, gives
    # the same members
    gradient = _Array([_gradient_key(0.25, (1, 0.5, 0, 1), 0.4), _gradient_key(1, (0, 0, 1, 1))])
    again = helpers._given_keys('gradientrgba', GRADIENT, json.loads(json.dumps(helpers.fmt(gradient))))
    assert again == [
        {'position': 0.25, 'value': [1.0, 0.5, 0.0, 1.0], 'midpoint': 0.4},
        {'position': 1.0, 'value': [0.0, 0.0, 1.0, 1.0], 'midpoint': 0.0},
    ]
    curve = _Array([_curve_key((0, 1), (0, 1), (0, 1)), _curve_key((0.5, 0.2), (0.4, 0.1), (0.6, 0.3))])
    assert helpers._given_keys('curveluminance', CURVE, json.loads(json.dumps(helpers.fmt(curve)))) == [
        {'position': [0.0, 1.0], 'left': [0.0, 1.0], 'right': [0.0, 1.0]},
        {'position': [0.5, 0.2], 'left': [0.4, 0.1], 'right': [0.6, 0.3]},
    ]


# --- describe_graph's line of many keys


def _parameter_line(
    helpers: types.ModuleType, value: _Array, capsys: pytest.CaptureFixture[str], node_ids: list[str] | None = None
) -> str:
    """describe_graph(include_params) of a graph whose one node, a gradient (7), holds `value` in gradientrgba, focused
    on `node_ids` if given: the parameter's line, '' when none is listed."""
    prop = mock.MagicMock()
    prop.getId.return_value = 'gradientrgba'
    prop.isConnectable.return_value = False
    node = mock.MagicMock()
    node.getIdentifier.return_value = '7'
    node.getReferencedResource.return_value = None
    node.getDefinition.return_value.getId.return_value = 'sbs::compositing::gradient'
    node.getPosition.return_value = SimpleNamespace(x=0, y=0)
    node.getProperties.return_value = [prop]
    node.getPropertyValue.return_value = value
    graph = mock.MagicMock()
    graph.getIdentifier.return_value = 'G'
    graph.getNodes.return_value = [node]
    vars(helpers).update(
        find_graph=lambda identifier: graph,
        _function_graphs_line=lambda package: '',
        _driving_graph=lambda n, p: None,
        _fx_map_functions=lambda n: [],
    )
    helpers.describe_graph('G', node_ids, True)
    return next((line for line in capsys.readouterr().out.splitlines() if 'gradientrgba' in line), '')


def test_describe_graph_shows_keys_up_to_keys_shown_and_counts_more(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # a whole graph's listing stays short (KEYS_SHOWN), while node_ids on the node, set's result and fmt give every
    # key, so a value read there can be set again
    shown = helpers.KEYS_SHOWN
    keys = [_gradient_key(0, (1, 0, 0, 1))] * (shown + 1)
    assert _parameter_line(helpers, _Array(keys[:shown]), capsys) == '    gradientrgba = %r' % (
        ((0, (1, 0, 0, 1)),) * shown,
    )
    assert _parameter_line(helpers, _Array(keys), capsys) == "    gradientrgba = '<%d keys>'" % (shown + 1)
    assert len(helpers.fmt(_Array(keys))) == shown + 1


def test_describe_graph_focused_on_the_node_shows_every_key(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-250: past KEYS_SHOWN keys, no tool read them; focused on the node, describe_graph shows every one
    count = helpers.KEYS_SHOWN + 1
    keys = _Array([_gradient_key(0, (1, 0, 0, 1))] * count)
    assert _parameter_line(helpers, keys, capsys, ['7']) == '    gradientrgba = %r' % (((0, (1, 0, 0, 1)),) * count,)


def test_describe_graph_lists_no_keys_as_a_new_node_has_them(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # Designer gives these parameters no default (None, measured): no keys is a new node's value, not a change
    assert _parameter_line(helpers, _Array([]), capsys) == ''


def test_the_tools_texts_give_the_cut_describe_graph_makes(helpers: types.ModuleType) -> None:
    # the figure agents read in describe_graph's and apply_edits' texts, kept with KEYS_SHOWN
    cut = 'past %d' % helpers.KEYS_SHOWN
    assert cut in _described('describe_graph', 'include_params') and cut in OPS
