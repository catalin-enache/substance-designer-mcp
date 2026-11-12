"""Tools that pick a node's first output say so when it has several (REVIEW.md HLP-65): a material's first is
`diffuse`, off by default and black on a metal. With sd and PySide6 faked; the live self-test uses a real material."""

import os
import re
import sys
import types
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from mcp.server.mcpserver import Image
from PIL import Image as PILImage

import designer_helpers  # conftest puts mcp_server on sys.path
from conftest import patch_server, server


@pytest.fixture
def helpers(monkeypatch: pytest.MonkeyPatch) -> Any:
    fake = mock.MagicMock()
    imported = re.findall(r'^\s*(?:from|import) ((?:sd|PySide6)(?:\.\w+)*)', designer_helpers.source(), re.M)
    for name in sorted({'.'.join(m.split('.')[:i]) for m in imported for i in range(1, m.count('.') + 2)}):
        monkeypatch.setitem(sys.modules, name, fake)
    module: Any = types.ModuleType('helpers_under_test')
    exec(compile(designer_helpers.source(), 'designer_helpers', 'exec'), module.__dict__)
    module.APIException = type('APIException', (BaseException,), {})  # sd's derives from BaseException too
    return module


def _node(*outputs: str) -> Any:
    node = mock.MagicMock()
    props = [mock.MagicMock(**{'getId.return_value': o}) for o in outputs]
    conn = mock.MagicMock(**{'getId.return_value': 'in', 'isConnectable.return_value': True})
    node.getProperties.side_effect = lambda category: props if category is OUT else [conn]
    return node


OUT = object()


@pytest.fixture
def wired(helpers: Any) -> Any:
    helpers.SDPropertyCategory = types.SimpleNamespace(Output=OUT, Input=object())
    helpers._graph_to_edit = lambda g: mock.MagicMock()
    return helpers


@pytest.mark.parametrize(
    ('outputs', 'chosen', 'note'),
    [
        (('diffuse', 'basecolor', 'normal'), None, True),
        (('diffuse', 'basecolor', 'normal'), 'basecolor', False),
        (('only',), None, False),
    ],
    ids=['first of several', 'told which', 'only one'],
)
def test_connect_says_when_it_took_the_first_of_several(
    wired: Any, capsys: pytest.CaptureFixture[str], outputs: tuple[str, ...], chosen: str | None, note: bool
) -> None:
    src = _node(*outputs)
    wired._node = lambda g, ident: src if ident == 'a' else _node('x')
    wired.connect('G', 'a', 'b', 'in', chosen)
    out = capsys.readouterr().out
    assert out.startswith('connected a.%s -> b.in' % (chosen or outputs[0]))
    assert ('no output given' in out) is note
    assert ('the first of 3 (diffuse, basecolor, normal); pass output' in out) is note


def _preview(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, printed: str, folders: list[str]) -> Any:
    """preview_node with a bridge saving its image in the folder the server made (folders: the temp_folders fixture),
    not one read back out of the call, which a Windows path's backslashes defeat (REVIEW.md TST-330)."""

    def bridge(code: str, path: str | None = None, timeout: float | None = None) -> str:
        out = os.path.join(folders[-1], 'node.png')
        PILImage.new('RGB', (4, 4)).save(out)
        return printed

    patch_server(monkeypatch, '_bridge', bridge)
    return server.preview_node('1')


def test_preview_returns_the_note_beside_the_image(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, temp_folders: list[str]
) -> None:
    note = "no output given: 'basecolor', tagged base colour, of 9 (diffuse, basecolor); pass output to pick another"
    result = _preview(monkeypatch, tmp_path, '%s\n1 a.diffuse 4x4 RGBA8\n' % note, temp_folders)
    assert isinstance(result[0], Image) and result[1] == note  # the image first, as before


def test_preview_returns_only_the_image_when_there_is_no_note(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, temp_folders: list[str]
) -> None:
    result = _preview(monkeypatch, tmp_path, '1 a.height 4x4 RGBA8\n', temp_folders)
    assert len(result) == 1 and isinstance(result[0], Image)


# REVIEW.md HLP-66: with no output given, the one tagged base colour, else the first
def _output_node(identifier: str, *usages: str) -> Any:
    def annotation(name: str) -> Any:
        if name == 'identifier':
            return types.SimpleNamespace(get=lambda: identifier)
        items = [types.SimpleNamespace(get=lambda u=u: types.SimpleNamespace(getName=lambda: u)) for u in usages]
        array = types.SimpleNamespace(getSize=lambda: len(items), getItem=lambda i: items[i])
        return types.SimpleNamespace(get=lambda: array)

    return types.SimpleNamespace(getAnnotationPropertyValueFromId=annotation)


def _instance(*tagged: Any) -> Any:
    node = mock.MagicMock()
    node.getReferencedResource.return_value = types.SimpleNamespace(getOutputNodes=lambda: list(tagged))
    return node


OUTPUTS = ['diffuse', 'basecolor', 'normal']


def test_the_output_tagged_base_colour_is_taken(helpers: Any) -> None:
    node = _instance(
        _output_node('diffuse', 'diffuse'), _output_node('basecolor', 'baseColor'), _output_node('normal', 'normal')
    )
    assert helpers._default_output(node, OUTPUTS) == (
        'basecolor',
        "'basecolor', tagged base colour, of 3 (diffuse, basecolor, normal)",
    )


def test_an_output_without_a_tag_annotation_doesnt_stop_the_search(helpers: Any) -> None:
    untagged = types.SimpleNamespace(getAnnotationPropertyValueFromId=lambda name: None)
    node = _instance(untagged, _output_node('albedo', 'baseColor'))
    assert helpers._default_output(node, ['mask', 'albedo'])[0] == 'albedo'


def test_a_custom_name_with_the_tag_is_taken(helpers: Any) -> None:
    node = _instance(_output_node('mask'), _output_node('albedo', 'baseColor'))
    assert helpers._default_output(node, ['mask', 'albedo'])[0] == 'albedo'


def test_an_output_only_named_basecolor_isnt_taken(helpers: Any) -> None:
    # the tag decides, not the name
    node = _instance(_output_node('mask'), _output_node('basecolor', 'mask'))
    assert helpers._default_output(node, ['mask', 'basecolor']) == ('mask', "'mask', the first of 2 (mask, basecolor)")


@pytest.mark.parametrize(
    'node',
    [
        _instance(_output_node('height'), _output_node('normal')),  # no tags
        _instance(_output_node('other', 'baseColor')),  # a tag on an output this node doesn't have
        mock.MagicMock(**{'getReferencedResource.return_value': None}),  # an atomic node
        mock.MagicMock(**{'getReferencedResource.side_effect': RuntimeError('no')}),
        mock.MagicMock(**{'getReferencedResource.return_value': types.SimpleNamespace()}),  # a bitmap resource
    ],
    ids=['no tags', 'tag on another output', 'atomic', 'raises', 'not a graph'],
)
def test_anything_else_takes_the_first(helpers: Any, node: Any) -> None:
    assert helpers._default_output(node, ['height', 'normal']) == (
        'height',
        "'height', the first of 2 (height, normal)",
    )


def _pixels_bridge(monkeypatch: pytest.MonkeyPatch, printed: str, folders: list[str]) -> None:
    def bridge(code: str, path: str | None = None, timeout: float | None = None) -> str:
        out = os.path.join(folders[-1], 'pixels.raw')
        with open(out, 'wb') as f:
            f.write(bytes(4 * 4 * 4))
        meta = '{"width": 4, "height": 4, "pitch": 16, "bpp": 4, "format": "RGBA8", "node": "1 m.basecolor"}'
        return '%s\nPIXELS=%s\n' % (printed, meta)

    patch_server(monkeypatch, '_bridge', bridge)


NOTE = "no output given: 'basecolor', tagged base colour, of 9 (diffuse, basecolor); pass output to pick another"


@pytest.mark.parametrize(
    'call',
    [lambda: server.node_stats('1'), lambda: server.check_tiling('1')],
    ids=['node_stats', 'check_tiling'],
)
def test_the_pixel_tools_carry_the_note(monkeypatch: pytest.MonkeyPatch, call: Any, temp_folders: list[str]) -> None:
    _pixels_bridge(monkeypatch, NOTE, temp_folders)
    assert NOTE in call()
    _pixels_bridge(monkeypatch, '', temp_folders)
    assert 'no output given' not in call()


def _tagged_material() -> Any:
    node = _node('diffuse', 'basecolor', 'normal')
    node.getReferencedResource.return_value = types.SimpleNamespace(
        getOutputNodes=lambda: [_output_node('diffuse', 'diffuse'), _output_node('basecolor', 'baseColor')]
    )
    return node


def test_connect_wires_the_tagged_output(wired: Any, capsys: pytest.CaptureFixture[str]) -> None:
    src = _tagged_material()
    wired._node = lambda g, ident: src if ident == 'a' else _node('x')
    wired.connect('G', 'a', 'b', 'in')
    assert capsys.readouterr().out.startswith('connected a.basecolor -> b.in')
    src.newPropertyConnectionFromId.assert_called_once()
    assert src.newPropertyConnectionFromId.call_args.args[0] == 'basecolor'


@pytest.mark.parametrize(('named', 'expected'), [(None, 'basecolor'), ('normal', 'normal')], ids=['tagged', 'named'])
def test_the_tools_that_look_use_the_tagged_output_unless_told(wired: Any, named: str | None, expected: str) -> None:
    seen: list[str] = []
    wired._with_node_texture(
        mock.MagicMock(), _tagged_material(), named, lambda texture, prop: seen.append(prop.getId())
    )
    assert seen == [expected]


def test_a_failed_restore_is_reported_with_an_output_named_like_restored(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    # REVIEW.md SRV-61: the note puts output names in the text, so "'restored' in text" was true with no such line,
    # and the warning for a failed restore became an AttributeError
    def bridge(code: str, path: str | None = None, timeout: float | None = None) -> str:
        with open(os.path.join(temp_folders[-1], '0.raw'), 'wb') as f:
            f.write(bytes(16 * 4))
        meta = '{"index": 0, "value": 1, "width": 4, "height": 4, "pitch": 16, "bpp": 4, "format": "RGBA8"}'
        return (
            "no output given: 'restored_mask', the first of 2 (restored_mask, b); pass output to pick another\nSWEEP=%s\n"
            % meta
        )

    patch_server(monkeypatch, '_bridge', bridge)
    text = server.sweep_param('1', 'p', [1])[0]
    assert 'original NOT restored!' in text and 'WARNING: the original value may not have been restored' in text
