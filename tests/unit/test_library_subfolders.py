"""Designer's library in subfolders of `packages` (ROADMAP item 41): search_nodes finds those packages, and
`definition` names them by path. Real files in a temporary folder; the live self-test uses Designer's own."""

import os
import re
import sys
import types
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

import designer_helpers  # conftest puts mcp_server on sys.path
from conftest import patch_server, server


def _graph(ident: str, label: str, hidden: bool = False) -> str:
    return (
        '<graph><identifier v="%s"/><attributes><label v="%s"/><category v="PBR Materials/Bricks"/>%s</attributes></graph>'
        % (
            ident,
            label,
            '<hideInLibrary v="1"/>' if hidden else '',
        )
    )


def _group(ident: str, *inside: str) -> str:
    return '<group><identifier v="%s"/><content>%s</content></group>' % (ident, ''.join(inside))


def _sbs(*inside: str) -> str:
    return '<?xml version="1.0"?><package><content>%s</content></package>' % ''.join(inside)


@pytest.fixture
def resources(tmp_path: Path) -> Path:
    """A resources folder like Designer's: packages at the top, ready-made materials below, and other files."""
    pbr = tmp_path / 'packages/materials/pbr'
    pbr.mkdir(parents=True)
    (tmp_path / 'packages/resources').mkdir()
    (tmp_path / 'packages/resources/notes.txt').write_text('not a package')
    (tmp_path / 'packages/hbao.sbs').write_text(_sbs(_graph('hbao', 'HBAO')))
    (tmp_path / 'packages/constant_values.sbs').write_text(
        _sbs(_group('float', _graph('constant_float', 'Constant Float'), _group('deep', _graph('deeper', 'Deeper'))))
    )
    (pbr / 'bricks_001.sbs').write_text(_sbs(_graph('bricks_001', 'Bricks 001')))
    (pbr / 'fabric_002.sbs').write_text(
        _sbs(_graph('fabric_002', 'Fabric 002'), _group('Resources', _graph('stains', 'Stains')))
    )
    (pbr / 'old_concrete.sbs').write_text(_sbs(_graph('old_concrete', 'Old concrete', True)))
    (tmp_path / 'secret.sbs').write_text(_sbs(_graph('secret', 'Secret')))
    (tmp_path / 'packages/both').mkdir()
    (tmp_path / 'packages/both.sbs').write_text(_sbs(_graph('both', 'Both')))
    (tmp_path / 'packages/both/inner.sbs').write_text(_sbs(_graph('inner', 'Inner')))
    return tmp_path


@pytest.fixture
def index(monkeypatch: pytest.MonkeyPatch, resources: Path) -> None:
    patch_server(monkeypatch, '_LIBRARY_CACHE', {})
    patch_server(
        monkeypatch,
        '_bridge',
        lambda code, path=None, timeout=None: 'RESOURCES_DIR=%s\nATOMIC=sbs::compositing::levels\n' % resources,
    )


@pytest.mark.usefixtures('index')
def test_search_finds_a_material_in_a_subfolder_by_its_path() -> None:
    out = server.search_nodes('bricks')
    assert "definition='materials/pbr/bricks_001'" in out and 'Bricks 001' in out and 'PBR Materials/Bricks' in out


@pytest.mark.usefixtures('index')
def test_a_graph_in_a_group_is_named_with_its_group() -> None:
    # REVIEW.md SRV-56: findResourceFromUrl finds a grouped graph only by its whole path (measured: 'stains' no,
    # 'Resources/stains' yes), for 146 graphs of Designer 16, 8 of them visible
    assert "definition='materials/pbr/fabric_002.sbs/Resources/stains'" in server.search_nodes('stains')
    assert "definition='constant_values.sbs/float/constant_float'" in server.search_nodes('constant float')
    assert "definition='constant_values.sbs/float/deep/deeper'" in server.search_nodes('deeper')


@pytest.mark.usefixtures('index')
def test_a_top_level_package_keeps_its_short_definition() -> None:
    assert "definition='hbao'" in server.search_nodes('hbao')


@pytest.mark.usefixtures('index')
def test_a_hidden_material_stays_hidden_but_the_result_says_so() -> None:
    # REVIEW.md SRV-55: "No node types match" for a material Designer ships, hidden from its library
    out = server.search_nodes('old concrete')
    assert 'definition=' not in out
    assert out.startswith('No node types match') and '1 hidden graph(s) match too: include_hidden=True' in out
    assert "definition='materials/pbr/old_concrete'" in server.search_nodes('old concrete', include_hidden=True)
    assert 'hidden graph(s)' not in server.search_nodes('old concrete', include_hidden=True)


@pytest.mark.usefixtures('index')
def test_the_hidden_count_only_comes_with_an_empty_result() -> None:
    # REVIEW.md SRV-58: half of Designer's graphs are hidden, so next to results it came on 24 of 25 queries
    both = server.search_nodes('PBR Materials')  # the category of the fixture's visible and hidden ones alike
    assert 'bricks_001' in both and 'hidden' not in both


def _index_with(monkeypatch: pytest.MonkeyPatch, resources: Path) -> None:
    patch_server(monkeypatch, '_LIBRARY_CACHE', {})
    patch_server(
        monkeypatch,
        '_bridge',
        lambda code, path=None, timeout=None: 'RESOURCES_DIR=%s\nATOMIC=sbs::compositing::levels\n' % resources,
    )


def test_a_missing_library_folder_is_an_error_and_not_remembered(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW.md SRV-57: os.walk swallows it, so this read as "no matches" for the server's life. As on main
    _index_with(monkeypatch, tmp_path)
    with pytest.raises(OSError):
        server.search_nodes('bricks')
    (tmp_path / 'packages').mkdir()
    (tmp_path / 'packages/hbao.sbs').write_text(_sbs(_graph('hbao', 'HBAO')))
    assert "definition='hbao'" in server.search_nodes('hbao')


def test_an_unreadable_library_subfolder_is_an_error(monkeypatch: pytest.MonkeyPatch, resources: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip('root reads everything')
    _index_with(monkeypatch, resources)
    locked = resources / 'packages/materials/pbr'
    locked.chmod(0o000)
    try:
        with pytest.raises(OSError):
            server.search_nodes('bricks')
    finally:
        locked.chmod(0o755)


@pytest.fixture
def helpers(monkeypatch: pytest.MonkeyPatch, resources: Path) -> Any:
    """The helpers as sent to Designer, with sd and PySide6 faked and the library folder real."""
    fake = mock.MagicMock()
    imported = re.findall(r'^\s*(?:from|import) ((?:sd|PySide6)(?:\.\w+)*)', designer_helpers.source(), re.M)
    for name in sorted({'.'.join(m.split('.')[:i]) for m in imported for i in range(1, m.count('.') + 2)}):
        monkeypatch.setitem(sys.modules, name, fake)
    module: Any = types.ModuleType('helpers_under_test')
    exec(compile(designer_helpers.source(), 'designer_helpers', 'exec'), module.__dict__)
    module._APP = mock.MagicMock()
    module._APP.getPath.return_value = str(resources)
    return module


DEFINITIONS = [
    # (definition, file under packages, graph, why)
    ('hbao', 'hbao.sbs', 'hbao', 'a top-level package'),
    ('hbao.sbs', 'hbao.sbs', 'hbao', 'with its extension'),
    ('hbao.sbs/hbao', 'hbao.sbs', 'hbao', 'file and graph'),
    ('hbao/other', 'hbao.sbs', 'other', 'file without the extension, and graph, as before'),
    ('materials/pbr/bricks_001', 'materials/pbr/bricks_001.sbs', 'bricks_001', 'a package in a subfolder'),
    ('materials/pbr/bricks_001.sbs', 'materials/pbr/bricks_001.sbs', 'bricks_001', 'with its extension'),
    (
        'materials/pbr/fabric_002.sbs/Resources/stains',
        'materials/pbr/fabric_002.sbs',
        'Resources/stains',
        'file and group',
    ),
    # REVIEW.md HLP-60: without the extension too, as at the top level
    (
        'materials/pbr/fabric_002/Resources/stains',
        'materials/pbr/fabric_002.sbs',
        'Resources/stains',
        'no extension, group',
    ),
    ('materials/pbr/bricks_001/bricks_001', 'materials/pbr/bricks_001.sbs', 'bricks_001', 'no extension, graph'),
    (
        'constant_values/float/constant_float',
        'constant_values.sbs',
        'float/constant_float',
        'top level, no extension, group',
    ),
    ('both/inner', 'both/inner.sbs', 'inner', 'a package and a folder of one name: the longest part wins'),
    ('both/other', 'both.sbs', 'other', 'a package and a folder of one name: the package, with a graph'),
    # nothing there: the refusal names what was looked for, not a materials.sbs
    ('materials/pbr/nope', 'materials/pbr/nope.sbs', 'nope', 'no such package'),
]


@pytest.mark.parametrize(('name', 'file', 'graph', 'why'), DEFINITIONS, ids=[d[3] + ': ' + d[0] for d in DEFINITIONS])
def test_definition_names_a_package_and_a_graph(
    helpers: Any, resources: Path, name: str, file: str, graph: str, why: str
) -> None:
    assert helpers._library_path(name) == (os.path.join(str(resources), 'packages', *file.split('/')), graph), why


@pytest.mark.parametrize(
    'name',
    ['../secret', '../secret.sbs', '../secret.sbs/secret', 'materials/../../secret', '{root}/secret.sbs'],
    ids=['up', 'up with extension', 'up with graph', 'up from a subfolder', 'absolute'],
)
def test_a_definition_never_leaves_the_library_folder(helpers: Any, resources: Path, name: str) -> None:
    assert (resources / 'secret.sbs').exists()  # it would be found
    with pytest.raises(RuntimeError, match='neither an atomic node nor a library package'):
        path, _ = helpers._library_path(name.replace('{root}', str(resources)))
        # as both callers do: a missing file is refused the same way
        if not os.path.exists(path):
            raise RuntimeError('neither an atomic node nor a library package')


class FakeFolder:
    pass


def _lookup_finding(helpers: Any, found: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    helpers.SDResourceFolder = FakeFolder
    helpers.atomic_definition_ids = lambda g: set()
    helpers._load_library = lambda path: types.SimpleNamespace(findResourceFromUrl=lambda url: found)
    helpers._PM = mock.MagicMock()


@pytest.mark.parametrize('call', ['describe_node', '_resolve_definition'])
def test_a_definition_naming_a_group_says_so(helpers: Any, monkeypatch: pytest.MonkeyPatch, call: str) -> None:
    # REVIEW.md HLP-63: findResourceFromUrl finds a group too, and newInstanceNode then raises NotSupported
    _lookup_finding(helpers, FakeFolder(), monkeypatch)
    args = (
        (mock.MagicMock(), 'constant_values.sbs/float')
        if call == '_resolve_definition'
        else ('constant_values.sbs/float',)
    )
    with pytest.raises(RuntimeError, match=r"'constant_values\.sbs/float' names a group of its package, not a graph"):
        getattr(helpers, call)(*args)


def test_a_definition_naming_a_graph_passes(helpers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    found = object()
    _lookup_finding(helpers, found, monkeypatch)
    g = mock.MagicMock()
    helpers._resolve_definition(g, 'hbao')
    g.newInstanceNode.assert_called_once_with(found)
