"""The refusal for Designer's library packages (designer_helpers): one message on every path, with fake
graphs and packages (ROADMAP item 27; REVIEW.md HLP-10, HLP-14, HLP-18, HLP-20). The live self-test runs
what the message suggests (safeguards.py)."""

import ast
import os
import re
import sys
import types
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

import designer_helpers  # conftest puts mcp_server on sys.path

LIBRARY = '/app/packages/bevel.sbs'
WAY = (
    "With it in focus in Designer's editor (the user opens it; open_graph can't reach it), read tools work with "
    'no graph given, and snapshot_graph with no graph keeps a copy'
)
BY_NAME = (
    "No open user graph is named 'bevel'; a loaded Designer library graph is, and tools don't find those by name "
    'or edit them. '
)


class FakeGraph:
    def __init__(self, identifier: str, package: Any) -> None:
        self.identifier, self.package = identifier, package

    def getIdentifier(self) -> str:
        return self.identifier

    def getPackage(self) -> Any:
        return self.package


def package(file: str, *graphs: str) -> Any:
    p = mock.MagicMock()
    p.getFilePath.return_value = file
    p.getChildrenResources.return_value = [FakeGraph(g, p) for g in graphs]
    return p


@pytest.fixture
def helpers(monkeypatch: pytest.MonkeyPatch) -> Any:
    """The helpers as sent to Designer, a library package and a user's one open, the library graph in the editor."""
    fake = mock.MagicMock()
    imported = re.findall(r'^\s*(?:from|import) ((?:sd|PySide6)(?:\.\w+)*)', designer_helpers.source(), re.M)
    for name in sorted({'.'.join(m.split('.')[:i]) for m in imported for i in range(1, m.count('.') + 2)}):
        monkeypatch.setitem(sys.modules, name, fake)
    module: Any = types.ModuleType('helpers_under_test')
    exec(compile(designer_helpers.source(), 'designer_helpers', 'exec'), module.__dict__)
    library, mine = package(LIBRARY, 'bevel', 'shared'), package('/p/mine.sbs', 'G', 'shared')
    module._PM = mock.MagicMock()
    module._PM.getUserPackages.return_value = [library, mine]
    module.SDSBSCompGraph = FakeGraph
    module._is_library_package = lambda p: p.getFilePath() == LIBRARY
    module._current_graph = lambda: library.getChildrenResources()[0]
    return module


def real_check(helpers: Any) -> Any:
    """_is_library_package as sent to Designer (the fixture replaces it for the other tests)."""
    namespace: dict[str, Any] = {'os': os, '_APP': helpers._APP, 'SDApplicationPath': mock.MagicMock()}
    tree = ast.parse(designer_helpers.source())
    found = next(f for f in tree.body if isinstance(f, ast.FunctionDef) and f.name == '_is_library_package')
    found.returns = None
    for arg in found.args.args:
        arg.annotation = None
    exec(compile(ast.Module([found], []), 'designer_helpers', 'exec'), namespace)
    return namespace['_is_library_package']


REFUSALS = [
    ('a library graph by name', lambda h: h.find_graph('bevel'), BY_NAME),
    ('saving by name', lambda h: h._package_of('bevel'), BY_NAME),
    ('saving by file', lambda h: h._package_of(LIBRARY), LIBRARY + " belongs to Designer's library; not saving it"),
    (
        'saving the editor graph',
        lambda h: h._package_of(None),
        LIBRARY + " belongs to Designer's library; not saving it",
    ),
    ('the file edit by name', lambda h: h.package_file_of('bevel'), BY_NAME),
    (
        'the file edit, editor graph',
        lambda h: h.package_file_of(None),
        "Graph 'bevel' belongs to Designer's library; its file is not edited. ",
    ),
]


@pytest.mark.parametrize(('why', 'refused', 'start'), REFUSALS, ids=[r[0] for r in REFUSALS])
def test_every_path_refuses_with_one_way_to_keep_a_copy(helpers: Any, why: str, refused: Any, start: str) -> None:
    with pytest.raises(RuntimeError) as raised:
        refused(helpers)
    message = str(raised.value)
    assert message.startswith(start), why
    assert message.endswith(WAY), why
    assert 'save_as' not in message and '\n' not in message, why  # set_link_display reports the last line
    helpers._PM.savePackage.assert_not_called()


def test_a_save_with_the_refused_graph_saves_nothing(helpers: Any) -> None:
    with pytest.raises(RuntimeError):
        helpers.package_file_of(None, save=True)
    helpers._PM.savePackage.assert_not_called()


def test_a_name_in_no_package_is_still_just_not_found(helpers: Any) -> None:
    with pytest.raises(RuntimeError, match=r"^Graph 'nope' not found in open user packages\.$"):
        helpers.find_graph('nope')


def test_the_users_graph_wins_over_a_library_graph_of_the_same_name(helpers: Any) -> None:
    assert helpers.find_graph('shared').getPackage().getFilePath() == '/p/mine.sbs'


# REVIEW.md HLP-55: with no graph given, the editor's graph can be a library one. Designer takes the edit (the
# package counts as modified, and another package's instance of the graph sees it at once; measured)
EDITS = [
    ('apply_edits', lambda h: h.apply_edits(None, [])),
    ('move_nodes', lambda h: h.move_nodes(None, {})),
    ('set_params', lambda h: h.set_params(None, '1', {})),
    ('add_node', lambda h: h.add_node(None, 'levels')),
    ('connect', lambda h: h.connect(None, '1', '2', 'input1')),
    ('disconnect', lambda h: h.disconnect(None, '1', 'input1')),
    ('delete_nodes', lambda h: h.delete_nodes(None, ['1'])),
    ('import_bitmap', lambda h: h.import_bitmap(None, __file__)),
    ('expose_param', lambda h: h.expose_param(None, '1', 'p')),
    ('remove_graph_input', lambda h: h.remove_graph_input(None, 'i')),
    ('set_graph_size', lambda h: h.set_graph_size(None, 10)),
    ('arrange_graph', lambda h: h.arrange_graph(None)),
    ('add_frame', lambda h: h.add_frame(None, ['1'], 't')),
    ('add_comment', lambda h: h.add_comment(None, 't')),
    ('sweep_param', lambda h: h.sweep_param(None, '1', 'p', [1], '/tmp')),
]


@pytest.mark.parametrize(('name', 'edit'), EDITS, ids=[e[0] for e in EDITS])
def test_no_edit_reaches_a_library_graph_in_the_editor(helpers: Any, name: str, edit: Any) -> None:
    with pytest.raises(RuntimeError) as raised:
        edit(helpers)
    assert str(raised.value) == "Graph 'bevel' belongs to Designer's library, and tools don't edit it. " + WAY, name


def test_every_helper_either_edits_through_the_check_or_only_reads(helpers: Any) -> None:
    # a new helper using find_graph has to be put in one group or the other
    reads = {
        '_found_by_name',
        '_graph_to_edit',
        '_package_of',
        'describe_graph',
        'dump_node_pixels',
        'export_outputs',
        'list_graph_inputs',
        'open_graph',
        'package_file_of',
        'save_node_output',
        'save_package_copy',
    }
    tree = ast.parse(designer_helpers.source())
    uses = {
        f.name
        for f in tree.body
        if isinstance(f, ast.FunctionDef)
        for n in ast.walk(f)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'find_graph'
    }
    assert uses == reads


def test_a_library_graph_object_is_refused_too(helpers: Any) -> None:
    library = helpers._PM.getUserPackages()[0].getChildrenResources()[0]
    with pytest.raises(RuntimeError, match="tools don't edit it"):
        helpers._graph_to_edit(library)


def test_the_users_graph_passes_the_check(helpers: Any) -> None:
    assert helpers._graph_to_edit('G').getIdentifier() == 'G'


# REVIEW.md HLP-57: 30 of Designer 16's packages are in subfolders of `packages` (materials/pbr/...)
LOCATIONS = [
    ('directly in the folder', 'app/packages/bevel.sbs', True),
    ('in a subfolder', 'app/packages/materials/pbr/concrete_070.sbs', True),
    ('a parent folder spelled with ..', 'app/packages/materials/../bevel.sbs', True),
    ('a doubled separator', 'app//packages/bevel.sbs', True),
    ('a folder whose name only starts the same', 'app/packages_extra/bevel.sbs', False),
    ('beside the folder', 'app/bevel.sbs', False),
    ("a project's own packages folder", 'project/packages/bevel.sbs', False),
]


@pytest.mark.parametrize(('why', 'file', 'library'), LOCATIONS, ids=[c[0] for c in LOCATIONS])
def test_a_library_package_is_any_file_under_the_folder(
    helpers: Any, tmp_path: Path, why: str, file: str, library: bool
) -> None:
    (tmp_path / 'app/packages/materials/pbr').mkdir(parents=True)
    helpers._APP = mock.MagicMock()
    helpers._APP.getPath.return_value = str(tmp_path / 'app')
    assert real_check(helpers)(package(str(tmp_path) + '/' + file)) is library, why


def test_a_library_folder_reached_through_a_link_is_the_same_folder(helpers: Any, tmp_path: Path) -> None:
    (tmp_path / 'app/packages').mkdir(parents=True)
    (tmp_path / 'link').symlink_to(tmp_path / 'app')
    helpers._APP = mock.MagicMock()
    helpers._APP.getPath.return_value = str(tmp_path / 'link')
    assert real_check(helpers)(package(str(tmp_path / 'app/packages/bevel.sbs'))) is True
    helpers._APP.getPath.return_value = str(tmp_path / 'app')
    assert real_check(helpers)(package(str(tmp_path / 'link/packages/bevel.sbs'))) is True


def test_an_unsaved_package_or_another_drive_isnt_a_library_package(
    helpers: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helpers._APP = mock.MagicMock()
    helpers._APP.getPath.return_value = str(tmp_path)
    assert real_check(helpers)(package('')) is False

    def other_drive(paths: Any) -> str:  # what Windows does for two drives
        raise ValueError('Paths do not have the same drive')

    monkeypatch.setattr(os.path, 'commonpath', other_drive)
    assert real_check(helpers)(package(str(tmp_path / 'packages/bevel.sbs'))) is False
