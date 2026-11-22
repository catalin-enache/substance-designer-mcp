"""The Designer helpers reading function nodes and a package's function graphs (describe.py, describe_functions.py and
editor.py's list_atomic), with sd faked: what the live self-test can't make Designer do, a definition with no label or
description (REVIEW.md HLP-241), a module or a graph giving no definitions (HLP-248), a read of the function graphs
that fails (HLP-242), and a read of a node's function that fails (HLP-245); and the descriptions' HTML entities
(HLP-246)."""

import types
from unittest import mock

import pytest


class _Definition:
    """A definition of the sbs::function module whose label and description come as None, which sd's stub allows."""

    def getId(self) -> str:
        return 'sbs::function::lr'

    def getLabel(self) -> str | None:
        return None

    def getDescription(self) -> str | None:
        return None

    def getProperties(self, category: object) -> list[object]:
        return []


class _Described(_Definition):
    """lr as Designer describes it: its description's tags, and an entity."""

    def getLabel(self) -> str | None:
        return 'Lower'

    def getDescription(self) -> str | None:
        return 'The <b>Lower</b> function returns true if first entry is lower than second entry: A&lt;B'


class _Graph:
    """A compositing graph as list_atomic makes one when none is open: its atomic definitions, none here."""

    @staticmethod
    def sNew(package: object) -> '_Graph':
        return _Graph()

    def getNodeDefinitions(self) -> list[object]:
        return []


class _Undefined:
    """A compositing graph whose getNodeDefinitions() gives None, as sd's stub allows (REVIEW.md HLP-248)."""

    @staticmethod
    def sNew(package: object) -> '_Undefined':
        return _Undefined()

    def getNodeDefinitions(self) -> list[object] | None:
        return None


@pytest.fixture
def function_module() -> mock.MagicMock:
    """Designer's sbs::function module, faked: it holds _Definition."""
    module = mock.MagicMock()
    module.getDefinitions.return_value = [_Definition()]
    return module


@pytest.fixture
def helpers(faked_helpers: types.ModuleType, function_module: mock.MagicMock) -> types.ModuleType:
    """The helpers, Designer's application faked: its sbs::function module is function_module, and no graph is
    open."""
    app = mock.MagicMock()
    app.getPath.return_value = '/resources'
    app.getModuleMgr.return_value.getModuleFromId.return_value = function_module
    vars(faked_helpers).update(_APP=app, SDSBSCompGraph=_Graph, _current_graph=lambda: None)
    return faked_helpers


def test_a_function_node_with_no_label_or_description_is_listed(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # list_atomic's lines are search_nodes' index: one raising there fails every search (REVIEW.md HLP-241)
    helpers.list_atomic()
    assert 'FUNCTION=sbs::function::lr\t\t\n' in capsys.readouterr().out


def test_a_function_node_with_no_label_or_description_is_described(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    helpers.describe_node('sbs::function::lr')
    assert capsys.readouterr().out.startswith('function node sbs::function::lr ""\noutputs:\ninputs:\n')


def test_a_module_giving_no_definitions_lists_no_function_node(
    helpers: types.ModuleType, function_module: mock.MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    # sd's stub lets getDefinitions() give None: every describe_node and search_nodes failed (REVIEW.md HLP-248)
    function_module.getDefinitions.return_value = None
    helpers.list_atomic()
    assert 'FUNCTION=' not in capsys.readouterr().out
    with pytest.raises(RuntimeError, match=r"^'sbs::function::lr' is no function node; search_nodes lists them$"):
        helpers.describe_node('sbs::function::lr')


def test_a_graph_giving_no_node_definitions_lists_no_atomic_node(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # getNodeDefinitions(), the same pattern, read by list_atomic and by describe_node and the add op through
    # atomic_definition_ids (REVIEW.md HLP-248)
    vars(helpers)['SDSBSCompGraph'] = _Undefined
    helpers.list_atomic()
    out = capsys.readouterr().out
    assert 'ATOMIC=' not in out and 'FUNCTION=sbs::function::lr' in out
    assert helpers.atomic_definition_ids(_Undefined()) == set()


def test_a_function_nodes_description_shows_the_characters_its_entities_stand_for(
    helpers: types.ModuleType, function_module: mock.MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    # "A&lt;B" was shown as it is (REVIEW.md HLP-246)
    function_module.getDefinitions.return_value = [_Described()]
    helpers.describe_node('sbs::function::lr')
    first = capsys.readouterr().out.splitlines()[0]
    assert first == (
        'function node sbs::function::lr "Lower": The Lower function returns true if first entry is lower than second '
        'entry: A<B'
    )


def test_a_parameters_description_shows_the_characters_its_entities_stand_for(helpers: types.ModuleType) -> None:
    # a library graph's, as paths_tools' mask_to_paths has: describe_node showed "values &lt; Mask Threshold Value"
    # (REVIEW.md HLP-246)
    prop = mock.MagicMock()
    prop.getDescription.return_value = '<p>The outside (values &lt; Mask Threshold Value) &amp; the inside</p>'
    assert helpers._short_description(prop) == 'The outside (values < Mask Threshold Value) & the inside'


def _describe(helpers: types.ModuleType, listed: object, node_ids: list[str] | None) -> None:
    """describe_graph of a graph with no node, whose package's function graphs `listed` gives, or raises."""
    graph = mock.MagicMock()
    graph.getIdentifier.return_value = 'G'
    graph.getNodes.return_value = []
    vars(helpers).update(find_graph=lambda identifier: graph, _function_graphs_line=listed)
    helpers.describe_graph('G', node_ids)


def test_a_function_graphs_line_that_fails_says_so(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # a package whose function graphs can't be read isn't one with none (REVIEW.md HLP-242)
    def unread(package: object) -> str:
        raise RuntimeError('an unreadable function graph')

    _describe(helpers, unread, None)
    out = capsys.readouterr().out
    assert 'function graphs of the package: not read (an unreadable function graph)\n' in out


def test_a_description_focused_on_nodes_leaves_the_function_graphs_out(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # every focused describe_graph carried the line, however many function graphs (REVIEW.md HLP-242)
    _describe(helpers, lambda package: 'function graphs of the package: f() -> float', ['7'])
    out = capsys.readouterr().out
    assert 'function graphs' not in out and 'not found: 7' in out


def test_describing_a_node_with_no_function_of_its_own_names_node_ids(helpers: types.ModuleType) -> None:
    # describe_graph(node_id=<a blend>) said only "name the parameter": node_ids describes the node in its graph
    vars(helpers).update(
        find_graph=lambda identifier: mock.MagicMock(),
        _node=lambda g, node_id: mock.MagicMock(),
        _definition_id=lambda n: 'sbs::compositing::blend',
    )
    with pytest.raises(RuntimeError) as raised:
        helpers.describe_function('G', '3', None, None)
    # the call to make, as node_id goes to the function (REVIEW.md SRV-218)
    assert str(raised.value) == (
        'node 3 is sbs::compositing::blend, which has no function of its own: name the parameter; see describe_node, '
        "or describe the node in its graph: describe_graph(node_ids=['3']), with no node_id"
    )


def test_a_nodes_function_that_cant_be_read_says_so(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # "has no function" said of a function that couldn't be read, the agent would build over it (REVIEW.md HLP-245)
    node, prop = mock.MagicMock(), mock.MagicMock()
    prop.getId.return_value = 'leveloutlow'
    node.getPropertyGraph.side_effect = RuntimeError('unreadable')
    vars(helpers).update(
        find_graph=lambda identifier: mock.MagicMock(),
        _function_parameter=lambda g, n, p, other_way: (node, prop, 'parameter'),
    )
    helpers.describe_function('G', '7', 'leveloutlow', None)
    assert capsys.readouterr().out == "7.leveloutlow: its function couldn't be read (unreadable)\n"
