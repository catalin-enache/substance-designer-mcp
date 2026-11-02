"""_same_graph (designer_helpers): when two graphs are the same graph, run with fake graphs and
packages. Packages are told apart by file; only two never saved by UID (REVIEW.md HLP-53, HLP-54)."""

import re
import sys
import types
from typing import Any
from unittest import mock

import pytest

import designer_helpers  # conftest puts mcp_server on sys.path


@pytest.fixture
def helpers(monkeypatch: pytest.MonkeyPatch) -> Any:
    """The helpers as sent to Designer (one script), with sd and PySide6 faked."""
    fake = mock.MagicMock()
    imported = re.findall(r'^\s*(?:from|import) ((?:sd|PySide6)(?:\.\w+)*)', designer_helpers.source(), re.M)
    for name in sorted({'.'.join(m.split('.')[:i]) for m in imported for i in range(1, m.count('.') + 2)}):
        monkeypatch.setitem(sys.modules, name, fake)
    module: Any = types.ModuleType('helpers_under_test')
    exec(compile(designer_helpers.source(), 'designer_helpers', 'exec'), module.__dict__)
    return module


def graph(identifier: str, file: str, uid: str) -> Any:
    package = types.SimpleNamespace(getFilePath=lambda: file, getUID=lambda: uid)
    return types.SimpleNamespace(getIdentifier=lambda: identifier, getPackage=lambda: package)


U, V = '{7118f88c-fa69-44e8-a0de-9d25423b6019}', '{e4330d13-6031-4aa6-a58f-72fa9601ee0b}'

CASES = [
    # (graph a, graph b, the same graph?, why)
    (('G', '/p/A.sbs', U), ('G', '/p/A.sbs', U), True, 'one package'),
    (('G', '/p/A.sbs', U), ('G', '/p/sub/../A.sbs', U), True, 'one file under two spellings'),
    (('G', '/p/A.sbs', U), ('G', '/p/copy.sbs', U), False, 'a copy of the file: its UID, another file'),
    (('G', '/p/A.sbs', U), ('G', '', U), False, 'saved and never saved, one UID (an old snapshot opened)'),
    (('G', '', U), ('G', '/p/A.sbs', U), False, 'never saved and saved, one UID, the other way round'),
    (('G', '', U), ('G', '', U), True, 'never saved, one UID: one package'),
    (('G', '', U), ('G', '', V), False, 'two packages never saved'),
    (('G', '/p/A.sbs', U), ('H', '/p/A.sbs', U), False, 'two graphs of one package'),
]


@pytest.mark.parametrize(('a', 'b', 'same', 'why'), CASES, ids=[c[3] for c in CASES])
def test_same_graph(helpers: Any, a: tuple[str, str, str], b: tuple[str, str, str], same: bool, why: str) -> None:
    assert helpers._same_graph(graph(*a), graph(*b)) is same, why


def test_no_graph_is_never_the_same(helpers: Any) -> None:
    g = graph('G', '/p/A.sbs', U)
    assert helpers._same_graph(None, g) is False and helpers._same_graph(g, None) is False
