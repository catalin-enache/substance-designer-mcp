"""Tools that pick a node's first output say so when it has several (REVIEW.md HLP-65): a material's first is
`diffuse`, off by default and black on a metal. With sd and PySide6 faked; the live self-test uses a real material.
node_stats(against=...) is tested here too, through the same fake bridge, which gives each node, or each output
of one, its own pixels."""

import ast
import asyncio
import json
import os
import types
from collections.abc import Callable
from pathlib import Path
from typing import cast
from unittest import mock

import numpy as np
import numpy.typing as npt
import pytest
from mcp.server.mcpserver import Image
from PIL import Image as PILImage

from conftest import fake_bridge, server, undone
from server_tools import views


@pytest.fixture
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    module = faked_helpers
    return module


def _node(*outputs: str) -> mock.MagicMock:
    node = mock.MagicMock()
    props = [mock.MagicMock(**{'getId.return_value': o}) for o in outputs]
    conn = mock.MagicMock(**{'getId.return_value': 'in', 'isConnectable.return_value': True})
    node.getProperties.side_effect = lambda category: props if category is OUT else [conn]
    return node


OUT = object()


@pytest.fixture
def wired(helpers: types.ModuleType) -> types.ModuleType:
    vars(helpers)['SDPropertyCategory'] = types.SimpleNamespace(Output=OUT, Input=object())
    vars(helpers)['_graph_to_edit'] = lambda g: mock.MagicMock()
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
    wired: types.ModuleType,
    capsys: pytest.CaptureFixture[str],
    outputs: tuple[str, ...],
    chosen: str | None,
    note: bool,
) -> None:
    src = _node(*outputs)
    vars(wired)['_node'] = lambda g, ident: src if ident == 'a' else _node('x')
    wired.connect('G', 'a', 'b', 'in', chosen)
    out = capsys.readouterr().out
    assert out.startswith('connected a.%s -> b.in' % (chosen or outputs[0]))
    assert ('no output given' in out) is note
    assert ('the first of 3 (diffuse, basecolor, normal); pass output' in out) is note


def _preview(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, printed: str, folders: list[str]) -> list[str | Image]:
    """preview_node with a bridge saving its image in the folder the server made (folders: the temp_folders fixture),
    not one read back out of the call, which a Windows path's backslashes defeat (REVIEW.md TST-330)."""

    def bridge(code: str) -> str:
        out = os.path.join(folders[-1], 'node.png')
        PILImage.new('RGB', (4, 4)).save(out)
        return printed

    fake_bridge(monkeypatch, bridge)
    return views.preview_node('1')


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
def _output_node(identifier: str, *usages: str) -> types.SimpleNamespace:
    def annotation(name: str) -> types.SimpleNamespace:
        if name == 'identifier':
            return types.SimpleNamespace(get=lambda: identifier)
        items = [types.SimpleNamespace(get=lambda u=u: types.SimpleNamespace(getName=lambda: u)) for u in usages]
        array = types.SimpleNamespace(getSize=lambda: len(items), getItem=lambda i: items[i])
        return types.SimpleNamespace(get=lambda: array)

    return types.SimpleNamespace(getAnnotationPropertyValueFromId=annotation)


def _instance(*tagged: types.SimpleNamespace) -> mock.MagicMock:
    node = mock.MagicMock()
    node.getReferencedResource.return_value = types.SimpleNamespace(getOutputNodes=lambda: list(tagged))
    return node


OUTPUTS = ['diffuse', 'basecolor', 'normal']


def test_the_output_tagged_base_colour_is_taken(helpers: types.ModuleType) -> None:
    node = _instance(
        _output_node('diffuse', 'diffuse'), _output_node('basecolor', 'baseColor'), _output_node('normal', 'normal')
    )
    assert helpers._default_output(node, OUTPUTS) == (
        'basecolor',
        "'basecolor', tagged base colour, of 3 (diffuse, basecolor, normal)",
    )


def test_an_output_without_a_tag_annotation_doesnt_stop_the_search(helpers: types.ModuleType) -> None:
    untagged = types.SimpleNamespace(getAnnotationPropertyValueFromId=lambda name: None)
    node = _instance(untagged, _output_node('albedo', 'baseColor'))
    assert helpers._default_output(node, ['mask', 'albedo'])[0] == 'albedo'


def test_a_custom_name_with_the_tag_is_taken(helpers: types.ModuleType) -> None:
    node = _instance(_output_node('mask'), _output_node('albedo', 'baseColor'))
    assert helpers._default_output(node, ['mask', 'albedo'])[0] == 'albedo'


def test_an_output_only_named_basecolor_isnt_taken(helpers: types.ModuleType) -> None:
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
def test_anything_else_takes_the_first(helpers: types.ModuleType, node: mock.MagicMock) -> None:
    assert helpers._default_output(node, ['height', 'normal']) == (
        'height',
        "'height', the first of 2 (height, normal)",
    )


# a node's 8-bit pixel format and its pixels (H, W, C), as Designer stores them
Stored = tuple[str, npt.NDArray[np.uint8]]
BLACK: Stored = ('RGBA8', np.zeros((4, 4, 4), np.uint8))


def _dumped(code: str) -> tuple[str, str | None, str | None]:
    """The node, the graph and the output that the dump_node_pixels call in `code` names: the last line in its undo
    group."""
    node, _, graph, output = cast(
        tuple[str, str, str | None, str | None],
        ast.literal_eval(undone(code).rstrip().splitlines()[-1].removeprefix('dump_node_pixels')),
    )
    return node, graph, output


def _pixels_bridge(
    monkeypatch: pytest.MonkeyPatch, printed: str, folders: list[str], stored: dict[str, Stored] | None = None
) -> list[tuple[str, str | None, str | None]]:
    """dump_node_pixels faked: each call writes its output's pixels where the server reads them, from `stored` by
    '<node id>.<output>', else by node id (BLACK for neither). The output read is the one named, basecolor without one.
    It prints `printed` when the call names no output, as the helpers print their note, then the PIXELS= line. Returns
    the calls' (node, graph, output), in order, as they come."""
    calls: list[tuple[str, str | None, str | None]] = []
    by_key = stored or {}

    def bridge(code: str) -> str:
        calls.append(_dumped(code))
        node, _, output = calls[-1]
        read = output or 'basecolor'
        fmt, pixels = by_key.get('%s.%s' % (node, read)) or by_key.get(node, BLACK)
        h, w, channels = pixels.shape
        with open(os.path.join(folders[-1], 'pixels.raw'), 'wb') as f:
            f.write(pixels.tobytes())
        meta = {
            'width': w,
            'height': h,
            'pitch': w * channels,
            'bpp': channels,
            'format': fmt,
            'node': '%s m.%s' % (node, read),
        }
        return '%s\nPIXELS=%s\n' % (printed if output is None else '', json.dumps(meta))

    fake_bridge(monkeypatch, bridge)
    return calls


NOTE = "no output given: 'basecolor', tagged base colour, of 9 (diffuse, basecolor); pass output to pick another"


@pytest.mark.parametrize(
    'call',
    [lambda: server.node_stats('1'), lambda: server.check_tiling('1')],
    ids=['node_stats', 'check_tiling'],
)
def test_the_pixel_tools_carry_the_note(
    monkeypatch: pytest.MonkeyPatch, call: Callable[[], str], temp_folders: list[str]
) -> None:
    _pixels_bridge(monkeypatch, NOTE, temp_folders)
    assert NOTE in call()
    _pixels_bridge(monkeypatch, '', temp_folders)
    assert 'no output given' not in call()


def test_node_stats_against_comes_after_the_channel_lines_and_before_the_points(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    other = BLACK[1].copy()
    other[0, 1, 0] = 51  # R 0.2 at (1,0)
    _pixels_bridge(monkeypatch, '', temp_folders, {'2': ('RGBA8', other)})
    # the point is where the two differ: its values are node 1's (REVIEW.md SRV-250)
    assert server.node_stats('1', points=[[1, 0]], against='2').splitlines() == [
        '1 m.basecolor: 4x4 RGBA8',
        *('%s: min 0.0000  max 0.0000  mean 0.0000  std 0.0000' % n for n in 'RGBA'),
        'against 2 m.basecolor: 4x4 RGBA8',
        'R diff: max 0.200000 at (1,0)  mean 0.012500  over 0.002: 1 px (6.25%)',
        *('%s diff: max 0.000000 at (0,0)  mean 0.000000  over 0.002: 0 px (0.00%%)' % n for n in 'GBA'),
        'pixel (1,0): R=0.0000, G=0.0000, B=0.0000, A=0.0000',
    ]


def test_node_stats_against_in_a_region_locates_in_the_whole_image(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    other = BLACK[1].copy()
    other[2, 3, 1] = 51  # G 0.2 at (3,2), inside the region
    other[0, 0, 1] = 255  # outside it
    _pixels_bridge(monkeypatch, '', temp_folders, {'2': ('RGBA8', other)})
    lines = server.node_stats('1', region=[2, 1, 4, 4], against='2').splitlines()
    assert 'G diff: max 0.200000 at (3,2)  mean 0.033333  over 0.002: 1 px (16.67%)' in lines, lines


def test_node_stats_against_reads_both_nodes_in_the_graph_given(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    # REVIEW.md TST-838: without a graph, the helpers take the one shown in the UI, which the live check opens
    calls = _pixels_bridge(monkeypatch, '', temp_folders)
    server.node_stats('1', graph='g', output='o1', against='2', against_output='o2')
    assert calls == [('1', 'g', 'o1'), ('2', 'g', 'o2')]


def test_node_stats_against_itself_compares_two_of_its_outputs(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    second = BLACK[1].copy()
    second[0, 1, 0] = 51  # R 0.2 at (1,0) in o2 alone
    _pixels_bridge(monkeypatch, '', temp_folders, {'1.o2': ('RGBA8', second)})
    lines = server.node_stats('1', output='o1', against='1', against_output='o2').splitlines()
    assert lines[0] == '1 m.o1: 4x4 RGBA8' and 'against 1 m.o2: 4x4 RGBA8' in lines, lines
    assert 'R diff: max 0.200000 at (1,0)  mean 0.012500  over 0.002: 1 px (6.25%)' in lines, lines


def test_without_against_its_other_parameters_change_nothing(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    _pixels_bridge(monkeypatch, NOTE, temp_folders)
    assert server.node_stats('1', against_output='x', tolerance=0.5) == server.node_stats('1')


def test_node_stats_against_carries_the_second_nodes_note(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    _pixels_bridge(monkeypatch, NOTE, temp_folders)
    lines = server.node_stats('1', output='basecolor', against='2').splitlines()
    assert lines.count(NOTE) == 1 and lines[lines.index(NOTE) - 1] == 'against 2 m.basecolor: 4x4 RGBA8', lines
    assert NOTE not in server.node_stats('1', output='basecolor', against='2', against_output='basecolor')


GREY: Stored = ('LUM8', np.zeros((4, 4, 1), np.uint8))
GREY_ALPHA: Stored = ('LUMALPHA8', np.zeros((4, 4, 2), np.uint8))


@pytest.mark.parametrize(
    'stored, named',
    [
        ({'2': ('RGBA8', np.zeros((2, 8, 4), np.uint8))}, ['4x4', '8x2']),
        ({'1': GREY}, ['LUM8', 'RGBA8']),
        ({'2': GREY}, ['LUM8', 'RGBA8']),
        ({'1': GREY_ALPHA}, ['LUMALPHA8', 'RGBA8']),  # shares A with RGBA, still refused: one is grey, the other colour
    ],
    ids=['another size', 'grey against colour', 'colour against grey', 'grey with alpha against colour'],
)
def test_node_stats_against_refuses_naming_both(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], stored: dict[str, Stored], named: list[str]
) -> None:
    _pixels_bridge(monkeypatch, '', temp_folders, stored)
    with pytest.raises(server.ToolError) as refused:
        server.node_stats('1', against='2')
    said = str(refused.value)
    assert all(part in said for part in ['1 m.basecolor', '2 m.basecolor', *named]), said


def test_node_stats_against_grey_with_alpha_against_grey_compares_their_grey(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    grey = GREY[1].copy()
    grey[0, 0, 0] = 51
    _pixels_bridge(monkeypatch, '', temp_folders, {'1': GREY_ALPHA, '2': ('LUM8', grey)})
    lines = server.node_stats('1', against='2').splitlines()
    assert [l for l in lines if ' diff: ' in l] == [
        'L diff: max 0.200000 at (0,0)  mean 0.012500  over 0.002: 1 px (6.25%)'
    ], lines


def test_a_negative_tolerance_is_refused_before_anything_reaches_designer(sent: list[str]) -> None:
    with pytest.raises(server.ToolError, match=r'validation error(.|\n)*tolerance'):
        asyncio.run(server.server.call_tool('node_stats', {'node_id': '1', 'against': '2', 'tolerance': -0.1}))
    assert sent == []


def _tagged_material() -> mock.MagicMock:
    node = _node('diffuse', 'basecolor', 'normal')
    node.getReferencedResource.return_value = types.SimpleNamespace(
        getOutputNodes=lambda: [_output_node('diffuse', 'diffuse'), _output_node('basecolor', 'baseColor')]
    )
    return node


def test_connect_wires_the_tagged_output(wired: types.ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    src = _tagged_material()
    vars(wired)['_node'] = lambda g, ident: src if ident == 'a' else _node('x')
    wired.connect('G', 'a', 'b', 'in')
    assert capsys.readouterr().out.startswith('connected a.basecolor -> b.in')
    src.newPropertyConnectionFromId.assert_called_once()
    assert src.newPropertyConnectionFromId.call_args.args[0] == 'basecolor'


@pytest.mark.parametrize(('named', 'expected'), [(None, 'basecolor'), ('normal', 'normal')], ids=['tagged', 'named'])
def test_the_tools_that_look_use_the_tagged_output_unless_told(
    wired: types.ModuleType, named: str | None, expected: str
) -> None:
    seen: list[str] = []
    wired._with_node_texture(
        mock.MagicMock(), _tagged_material(), named, lambda texture, prop: seen.append(prop.getId())
    )
    assert seen == [expected]


def test_an_output_the_node_lacks_is_refused_naming_the_node(wired: types.ModuleType) -> None:
    # REVIEW.md HLP-255: node_stats(against=...) reads two nodes, so the message says whose output is missing
    node = _node('height', 'normal')
    node.getIdentifier.return_value = '7'
    with pytest.raises(RuntimeError, match=r"^output 'nope' not on node 7; outputs: \['height', 'normal'\]$"):
        wired._with_node_texture(mock.MagicMock(), node, 'nope', lambda texture, prop: None)


def test_a_failed_restore_is_reported_with_an_output_named_like_restored(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    # REVIEW.md SRV-61: the note puts output names in the text, so "'restored' in text" was true with no such line,
    # and the warning for a failed restore became an AttributeError
    def bridge(code: str) -> str:
        with open(os.path.join(temp_folders[-1], '0.raw'), 'wb') as f:
            f.write(bytes(16 * 4))
        meta = '{"index": 0, "value": 1, "width": 4, "height": 4, "pitch": 16, "bpp": 4, "format": "RGBA8"}'
        return (
            "no output given: 'restored_mask', the first of 2 (restored_mask, b); pass output to pick another\nSWEEP=%s\n"
            % meta
        )

    fake_bridge(monkeypatch, bridge)
    text = server.sweep_param('1', 'p', [1])[0]
    assert 'original NOT restored!' in text and 'WARNING: the original value may not have been restored' in text
