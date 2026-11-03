"""Saving a package that uses a never-saved package (REVIEW.md SRV-60): Designer opens a modal "Save Dependency" file
dialog, on its main thread, which a timer calling reject() didn't close (measured): the tools refuse before that.
With sd and PySide6 faked; the live self-test uses real packages, and calls the tools only once this refusal works."""

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
    module._PM = mock.MagicMock()
    module._is_library_package = lambda p: False
    return module


class FakeGraph:
    def __init__(self, identifier: str, package: Any) -> None:
        self.identifier, self.package = identifier, package

    def getIdentifier(self) -> str:
        return self.identifier

    def getPackage(self) -> Any:
        return self.package


def _package(file: str, graph: str, *uses: Any) -> Any:
    p = mock.MagicMock()
    p.getFilePath.return_value = file
    p.getUID.return_value = '{%s}' % graph
    p.getChildrenResources.return_value = [FakeGraph(graph, p)]
    p.getDependencies.return_value = [
        types.SimpleNamespace(getFilePath=lambda d=d: d.getFilePath(), getPackage=lambda d=d: d) for d in uses
    ]
    return p


def _wired(helpers: Any, host: Any) -> Any:
    helpers.SDSBSCompGraph = FakeGraph
    real_find = helpers.find_graph
    helpers.find_graph = lambda identifier=None: (
        host.getChildrenResources()[0] if identifier == 'host' else real_find(identifier)
    )
    helpers._APP = mock.MagicMock()
    helpers._package_of = lambda identifier: (host, None)
    helpers._current_graph = lambda: None
    used = [d.getPackage() for d in host.getDependencies.return_value]
    helpers._PM.getUserPackages.return_value = [host, *[u for u in used if u is not None]]
    return helpers


UNSAVED = _package('', 'dep_unsaved')
SAVED = _package('/p/dep.sbs', 'dep')

SAVES = [
    ('save_package in place', lambda h: h.save_package('host')),
    ('save_package with save_as', lambda h: h.save_package('host', '/tmp/x/host.sbs')),
    ('a snapshot copy', lambda h: h.save_package_copy('host', '/tmp/x/copy.sbs')),
    ('the file edit, saving', lambda h: h.package_file_of('host', save=True)),
    ('the file edit, looking first', lambda h: h.package_file_of('host')),
]


@pytest.mark.parametrize(('why', 'call'), SAVES, ids=[s[0] for s in SAVES])
def test_every_save_refuses_a_never_saved_dependency_before_saving(helpers: Any, why: str, call: Any) -> None:
    _wired(helpers, _package('/p/host.sbs', 'host', UNSAVED))
    with pytest.raises(RuntimeError) as raised:
        call(helpers)
    message = str(raised.value)
    assert "'dep_unsaved'" in message and 'never saved' in message and 'save_package' in message, why
    assert 'save_as' in message and '\n' not in message, why  # set_link_display reports the last line
    for save in (helpers._PM.savePackage, helpers._PM.savePackageAs, helpers._PM.saveCopyOfPackageAs):
        save.assert_not_called()


def test_a_saved_dependency_saves(helpers: Any, tmp_path: Any) -> None:
    _wired(helpers, _package('/p/host.sbs', 'host', SAVED))
    helpers.save_package('host')
    helpers._PM.savePackage.assert_called_once()
    helpers.save_package_copy('host', str(tmp_path / 'copy.sbs'))
    helpers._PM.saveCopyOfPackageAs.assert_called_once()


def test_a_package_without_dependencies_saves(helpers: Any) -> None:
    _wired(helpers, _package('/p/host.sbs', 'host'))
    helpers.save_package('host')
    helpers._PM.savePackage.assert_called_once()


def test_a_dependency_with_its_file_gone_saves(helpers: Any) -> None:
    # measured: a path and no package, and all three saves go through with no dialog
    host = _package('/p/host.sbs', 'host')
    host.getDependencies.return_value = [
        types.SimpleNamespace(getFilePath=lambda: '/p/gone.sbs', getPackage=lambda: None)
    ]
    _wired(helpers, host)
    helpers.save_package('host')
    helpers._PM.savePackage.assert_called_once()


def test_only_direct_dependencies_count(helpers: Any) -> None:
    # measured: a saved dependency using an unsaved package saves with no dialog
    _wired(helpers, _package('/p/host.sbs', 'host', _package('/p/mid.sbs', 'mid', UNSAVED)))
    helpers.save_package('host')
    helpers._PM.savePackage.assert_called_once()


def test_every_dependency_is_named(helpers: Any) -> None:
    _wired(helpers, _package('/p/host.sbs', 'host', UNSAVED, SAVED, _package('', 'other')))
    with pytest.raises(RuntimeError) as raised:
        helpers.save_package('host')
    assert "save_package('dep_unsaved', save_as=...)" in str(raised.value)
    assert "save_package('other', save_as=...)" in str(raised.value)
    assert "'dep'" not in str(raised.value)


# REVIEW.md HLP-67: what the refusal says to do has to be doable, and it depends on whether a name reaches the package
def _message(helpers: Any, host: Any, in_editor: Any = None) -> str:
    _wired(helpers, host)
    helpers._current_graph = lambda: in_editor
    with pytest.raises(RuntimeError) as raised:
        helpers._refuse_unsaved_dependencies(host)
    return str(raised.value)


def test_a_graph_a_name_reaches_is_told_by_name(helpers: Any) -> None:
    message = _message(helpers, _package('/p/host.sbs', 'host', _package('', 'dep_unsaved')))
    assert "save_package('dep_unsaved', save_as=...)" in message and 'in focus' not in message


def test_one_name_with_the_host_in_the_editor_isnt_told_a_name_that_finds_the_host(helpers: Any) -> None:
    # every new graph is "New_Graph": find_graph takes the one in the editor, and the same refusal comes back
    host = _package('', 'New_Graph', _package('', 'New_Graph'))
    host.getFilePath.return_value = '/p/host.sbs'
    host.getUID.return_value = '{host}'
    message = _message(helpers, host, in_editor=host.getChildrenResources()[0])
    assert 'save_package(' not in message
    assert "in focus in Designer's editor" in message and 'with no graph' in message
    assert 'UID {New_Graph}' in message  # tells it from the host, which has the same graph name


def test_one_name_with_nothing_in_the_editor_isnt_told_an_ambiguous_name(helpers: Any) -> None:
    host = _package('/p/host.sbs', 'New_Graph', _package('', 'New_Graph'))
    host.getUID.return_value = '{host}'
    message = _message(helpers, host)
    assert 'save_package(' not in message and "in focus in Designer's editor" in message


@pytest.mark.parametrize('reachable', [True, False], ids=['a package object', 'no package object'])
def test_a_closed_package_cant_be_saved_by_a_tool_and_the_refusal_says_so(helpers: Any, reachable: bool) -> None:
    # measured: closed while the host keeps its node, it stays a dependency with no file, and the dialog opens;
    # deleting the node removes the dependency
    host = _package('/p/host.sbs', 'host')
    closed = _package('', 'dep_closed') if reachable else None
    host.getDependencies.return_value = [types.SimpleNamespace(getFilePath=lambda: '', getPackage=lambda: closed)]
    _wired(helpers, host)
    helpers._PM.getUserPackages.return_value = [host]
    with pytest.raises(RuntimeError) as raised:
        helpers._refuse_unsaved_dependencies(host)
    message = str(raised.value)
    assert 'save_package(' not in message and 'closed' in message and 'delete the nodes' in message
    assert ("'dep_closed'" in message) is reachable


def test_only_graphs_are_named_all_of_them_and_inside_groups(helpers: Any) -> None:
    dep = _package('', 'first')
    folder = mock.MagicMock(**{'getIdentifier.return_value': 'Resources'})
    dep.getChildrenResources.return_value = [folder, FakeGraph('first', dep), FakeGraph('second', dep)]
    message = _message(helpers, _package('/p/host.sbs', 'host', dep))
    assert "'first', 'second'" in message and 'Resources' not in message
