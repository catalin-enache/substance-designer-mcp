"""describe_selected (designer_helpers), what describe_graph(selected=True) runs: the graph in Designer's editor, only its
nodes selected there, with a faked UI manager. What the UI manager gives, measured, and the tool in Designer:
editor_open_and_zoom's checks."""

import sys
import types
from collections.abc import Callable, Sequence
from types import SimpleNamespace
from typing import NoReturn
from unittest import mock

import pytest

from conftest import FakeGraph


class Frame:
    """Stands for SDGraphObjectFrame."""

    def __init__(self, title: str) -> None:
        self.title = title

    def getTitle(self) -> str:
        return self.title


class Comment:
    """Stands for SDGraphObjectComment."""


class Pin:
    """Stands for SDGraphObjectPin."""


def node(identifier: str) -> SimpleNamespace:
    return SimpleNamespace(getIdentifier=lambda: identifier)


def never() -> NoReturn:
    raise AssertionError('the selection read before a refusal')


class ListedGraph(FakeGraph):
    """A compositing graph whose nodes describe_graph lists. It has no size or frames, which describe_graph skips."""

    def __init__(self, identifier: str, nodes: list[mock.MagicMock]) -> None:
        super().__init__(identifier, mock.MagicMock())
        self.nodes = nodes

    def getNodes(self) -> list[mock.MagicMock]:
        return self.nodes


def listed_node(identifier: str) -> mock.MagicMock:
    """A levels node with no connections, as describe_graph reads one."""
    n = mock.MagicMock()
    n.getIdentifier.return_value = identifier
    n.getReferencedResource.return_value = None
    n.getDefinition.return_value.getId.return_value = 'sbs::compositing::levels'
    n.getPosition.return_value = SimpleNamespace(x=0, y=0)
    return n


EDITOR = FakeGraph('G', mock.MagicMock())


@pytest.fixture
def selection_helpers(faked_helpers: types.ModuleType, monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """The helpers, sd's graph classes the fakes above."""
    vars(faked_helpers)['SDSBSCompGraph'] = FakeGraph
    sd = sys.modules['sd']  # every sd module is this one fake (conftest's faked_helpers)
    for name, fake in (('SDGraphObjectFrame', Frame), ('SDGraphObjectComment', Comment), ('SDGraphObjectPin', Pin)):
        monkeypatch.setattr(sd, name, fake)
    return faked_helpers


@pytest.fixture
def helpers(selection_helpers: types.ModuleType) -> types.ModuleType:
    """selection_helpers, describe_graph printing the graph, ids, include_params and limit it was given."""

    def describe_graph(g: FakeGraph, node_ids: list[str], include_params: bool, limit: int, hint: str) -> None:
        print('describe_graph(%s, %r, %r, %d)' % (g.getIdentifier(), node_ids, include_params, limit))

    vars(selection_helpers)['describe_graph'] = describe_graph
    return selection_helpers


def in_editor(
    helpers: types.ModuleType,
    graph: object,
    nodes: Callable[[], Sequence[object] | None] = never,
    objects: Callable[[], Sequence[object] | None] = never,
) -> None:
    """The UI manager, `graph` in the editor, its getters of the selected nodes and objects."""
    ui = SimpleNamespace(
        getCurrentGraph=lambda: graph, getCurrentGraphSelectedNodes=nodes, getCurrentGraphSelectedObjects=objects
    )
    vars(helpers)['_ui'] = lambda: ui


@pytest.mark.parametrize('empty', [[], None], ids=['empty arrays', 'None'])
def test_nothing_selected_is_one_line(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], empty: list[object] | None
) -> None:
    # empty arrays measured; the API types both getters as optional
    in_editor(helpers, EDITOR, lambda: empty, lambda: empty)
    helpers.describe_selected(None, False, 400)
    assert capsys.readouterr().out == 'graph G: nothing selected in the editor\n'


@pytest.mark.parametrize('identifier', [None, 'G'], ids=['no graph given', 'the graph in the editor given'])
def test_the_selected_nodes_are_described_as_node_ids_focuses_them(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], identifier: str | None
) -> None:
    in_editor(helpers, EDITOR, lambda: [node('2'), node('1')], list)
    helpers.describe_selected(identifier, True, 5)
    assert capsys.readouterr().out == "describe_graph(G, ['2', '1'], True, 5)\n"


def test_frames_comments_and_pins_selected_too_are_named_after_the_nodes(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    in_editor(
        helpers, EDITOR, lambda: [node('1')], lambda: [Frame('Shape'), Comment(), Pin(), Frame('Wood'), Comment()]
    )
    helpers.describe_selected(None, False, 400)
    assert capsys.readouterr().out == (
        "describe_graph(G, ['1'], False, 400)\nalso selected: frame 'Shape', frame 'Wood', 2 comments, 1 pin\n"
    )


def test_frames_alone_selected_say_no_node_is(helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    in_editor(helpers, EDITOR, list, lambda: [Frame('Shape'), Comment()])
    helpers.describe_selected(None, False, 400)
    assert capsys.readouterr().out == "graph G: no node selected in the editor, only frame 'Shape', 1 comment\n"


def test_another_graph_is_refused_naming_the_one_in_the_editor(helpers: types.ModuleType) -> None:
    in_editor(helpers, EDITOR)
    with pytest.raises(RuntimeError) as raised:
        helpers.describe_selected('H', False, 400)
    assert str(raised.value) == (
        "selected reads the selection of the graph in Designer's editor, which is 'G', not 'H'. To read one in 'H', "
        'open it there with open_graph and have the user select in it.'
    )


def test_no_graph_in_the_editor_is_refused_before_the_getters(helpers: types.ModuleType) -> None:
    in_editor(helpers, None)
    with pytest.raises(RuntimeError) as raised:
        helpers.describe_selected('H', False, 400)
    assert str(raised.value) == "No graph is open in Designer's editor, so nothing is selected there."


def test_a_function_graph_in_the_editor_is_refused_before_the_getters(helpers: types.ModuleType) -> None:
    in_editor(helpers, SimpleNamespace(getIdentifier=lambda: 'paint'))
    with pytest.raises(RuntimeError) as raised:
        helpers.describe_selected(None, False, 400)
    assert str(raised.value) == (
        "The graph open in Designer's editor (paint) is not a compositing graph: selected reads a compositing graph's "
        'selection only.'
    )


def test_a_capped_selection_says_to_raise_limit_not_to_filter_node_ids(
    selection_helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-254: describe_graph's own line said "or filter node_ids", which selected refuses
    nodes = [listed_node(i) for i in ('1', '2', '3')]
    in_editor(selection_helpers, ListedGraph('G', nodes), lambda: nodes, list)
    selection_helpers.describe_selected(None, False, 1)
    out = capsys.readouterr().out
    assert out.splitlines()[-1] == '... 2 more nodes (raise limit)', out
