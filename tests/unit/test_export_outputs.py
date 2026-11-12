"""export_outputs' second compute (REVIEW.md HLP-101), with sd and PySide6 faked; the live self-test reaches the state
it is for (measure/checks.py)."""

import types
from pathlib import Path
from unittest import mock

import pytest

OUT = object()


@pytest.fixture
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    module = faked_helpers
    vars(module)['SDPropertyCategory'] = types.SimpleNamespace(Output=OUT, Input=object())
    return module


def _graph(helpers: types.ModuleType, computes_with_no_image: float) -> mock.MagicMock:
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
    vars(helpers)['find_graph'] = lambda identifier: graph
    return graph


def test_an_output_with_no_image_after_the_first_compute_gets_a_second(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    graph = _graph(helpers, computes_with_no_image=1)
    helpers.export_outputs('G', str(tmp_path))
    out = capsys.readouterr().out
    assert graph.compute.call_count == 2
    assert 'out.png' in out and 'computed no image' not in out, out


def test_outputs_with_an_image_are_computed_once(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    graph = _graph(helpers, computes_with_no_image=0)
    helpers.export_outputs('G', str(tmp_path))
    assert graph.compute.call_count == 1 and 'out.png' in capsys.readouterr().out


def test_an_output_still_with_no_image_is_said_after_the_second_compute(
    helpers: types.ModuleType, tmp_path: Path
) -> None:
    graph = _graph(helpers, computes_with_no_image=float('inf'))
    with pytest.raises(RuntimeError, match='computed no image: out'):
        helpers.export_outputs('G', str(tmp_path))
    assert graph.compute.call_count == 2
