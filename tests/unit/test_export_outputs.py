"""export_outputs' second compute (REVIEW.md HLP-101), with sd and PySide6 faked; the live self-test reaches the state
it is for (measure/checks.py)."""

import re
import sys
import types
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

import designer_helpers  # conftest puts mcp_server on sys.path

OUT = object()


@pytest.fixture
def helpers(monkeypatch: pytest.MonkeyPatch) -> Any:
    fake = mock.MagicMock()
    imported = re.findall(r'^\s*(?:from|import) ((?:sd|PySide6)(?:\.\w+)*)', designer_helpers.source(), re.M)
    for name in sorted({'.'.join(m.split('.')[:i]) for m in imported for i in range(1, m.count('.') + 2)}):
        monkeypatch.setitem(sys.modules, name, fake)
    module: Any = types.ModuleType('helpers_under_test')
    exec(compile(designer_helpers.source(), 'designer_helpers', 'exec'), module.__dict__)
    module.APIException = type('APIException', (BaseException,), {})
    module.SDPropertyCategory = types.SimpleNamespace(Output=OUT, Input=object())
    return module


def _graph(helpers: Any, computes_with_no_image: float) -> Any:
    """A graph of one output node, 'out', whose texture appears after that many computes."""
    graph = mock.MagicMock()
    computed = [0]
    graph.compute.side_effect = lambda: computed.__setitem__(0, computed[0] + 1)
    texture = mock.MagicMock()
    texture.getSize.return_value = types.SimpleNamespace(x=4, y=4)
    node = mock.MagicMock()
    node.getAnnotationPropertyValueFromId.return_value.get.return_value = 'out'
    node.getProperties.return_value = [mock.MagicMock()]
    node.getPropertyValue.side_effect = lambda prop: mock.MagicMock(
        **{'get.return_value': texture if computed[0] > computes_with_no_image else None}
    )
    graph.getOutputNodes.return_value = [node]
    helpers.find_graph = lambda identifier: graph
    return graph


def test_an_output_with_no_image_after_the_first_compute_gets_a_second(
    helpers: Any, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    graph = _graph(helpers, computes_with_no_image=1)
    helpers.export_outputs('G', str(tmp_path))
    out = capsys.readouterr().out
    assert graph.compute.call_count == 2
    assert 'out.png' in out and 'computed no image' not in out, out


def test_outputs_with_an_image_are_computed_once(
    helpers: Any, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    graph = _graph(helpers, computes_with_no_image=0)
    helpers.export_outputs('G', str(tmp_path))
    assert graph.compute.call_count == 1 and 'out.png' in capsys.readouterr().out


def test_an_output_still_with_no_image_is_said_after_the_second_compute(helpers: Any, tmp_path: Path) -> None:
    graph = _graph(helpers, computes_with_no_image=float('inf'))
    with pytest.raises(RuntimeError, match='computed no image: out'):
        helpers.export_outputs('G', str(tmp_path))
    assert graph.compute.call_count == 2
