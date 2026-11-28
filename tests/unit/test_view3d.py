"""screenshot_designer's 3D view options (ROADMAP items 7, 73 and 74; the shader model, item 88; a mesh file, item 84)
and the 3D view as text (as_text, item 85): what the server refuses before reaching Designer, and how it calls the
helpers. Driving the 3D view itself is checked live (editor_panels_and_fit, facts)."""

import ast
import asyncio
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, InputRequiredResult, TextContent
from PIL import Image as PILImage

import designer_helpers
from conftest import fake_bridge, server
from project_constants import Json
from server_tools import views

if TYPE_CHECKING:  # for the checker: the part as the helpers hold it
    from designer_helpers import state3d
else:
    state3d = designer_helpers.standalone('state3d')

# the set-up's line as scene3d.py prints it: the fields of its one load, then the graph's outputs
NOTE = "3D view: Plane, view Top, framed, +2 zoom steps, tiling 2, graph g's outputs on the mesh"


def _bridge(
    monkeypatch: pytest.MonkeyPatch, folders: list[str], printed: str = '3d render 4x4\n', shot: bool = True
) -> list[str]:
    """The calls sent to Designer; each answers with `printed` and, if `shot`, leaves a 4x4 image where the shot
    goes, in the folder the server made (folders: the temp_folders fixture, its name with a backslash, as a Windows
    path has: REVIEW.md TST-325)."""
    sent: list[str] = []

    def bridge(code: str) -> str:
        sent.append(code)
        shot_path = os.path.join(folders[-1], 'shot.png')
        assert repr(shot_path) in code  # where the helper is told to save it
        if shot:
            PILImage.new('RGB', (4, 4)).save(shot_path)
        return printed

    fake_bridge(monkeypatch, bridge)
    return sent


def _call(code: str) -> str:
    """The helper call after the helpers' source (_helpers_call: the source, a blank line, the call, a newline), without
    the newline."""
    return code[code.rindex('\n\n') + 2 :].rstrip('\n')


OPTIONS: dict[str, Json] = {
    'graph': 'g',
    'mesh': 'Plane',
    'view': 'Top',
    'zoom': 2,
    'tiling': 2.0,
    'orbit': [90.0, -30.0],
    'pan': [0.25, 0.5],
    'environment': 'studio',
    'environment_rotation': 90.0,
    'environment_exposure': 1.0,
    'shader_model': 'AdobeStandardMaterial',
}


def _shoot(arguments: dict[str, Json]) -> CallToolResult | InputRequiredResult:
    """screenshot_designer called as an agent's client does: through the server, which validates the arguments first and
    gives the tool orbit and pan as tuples (REVIEW.md TST-534: called directly with lists, a test hid a TypeError)."""
    result: CallToolResult | InputRequiredResult = asyncio.run(
        server.server.call_tool('screenshot_designer', arguments)
    )
    return result


GATED: dict[str, Json] = {**OPTIONS, 'as_text': True}  # what goes with panel='3d' alone


@pytest.mark.parametrize('option', sorted(GATED))
def test_3d_options_need_the_3d_panel(monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], option: str) -> None:
    sent = _bridge(monkeypatch, temp_folders)
    with pytest.raises(ToolError, match=r"panel='3d'"):
        _shoot({'panel': 'graph', option: GATED[option]})
    assert sent == []


@pytest.mark.parametrize(
    'option, value, message',
    [
        ('zoom', 31, 'zoom'),
        ('zoom', -31, 'zoom'),
        ('tiling', 0.0, 'tiling'),
        ('tiling', -1.0, 'tiling'),
        ('tiling', float('nan'), 'tiling'),
        ('tiling', float('inf'), 'tiling'),  # REVIEW.md HLP-110, SRV-119: it reached Designer as a NameError
        ('orbit', [181.0, 0.0], r'orbit is \[right, up\] in degrees.*not \[181\.0, 0\.0\]'),
        ('orbit', [0.0, -91.0], r'orbit is \[right, up\] in degrees'),
        ('pan', [1.5, 0.0], r'pan is \[right, up\] in fractions of the view.*not \[1\.5, 0\.0\]'),
        ('pan', [0.0, -1.01], r'pan is \[right, up\] in fractions of the view'),
        # orbit [90] or [1, 2, 3], pan [0.5]: their schemas refuse them (test_server.py, REVIEW.md SRV-177)
        ('environment_rotation', 180.5, r'environment_rotation is in degrees, -180 to 180, not 180\.5'),
        ('environment_rotation', -181.0, 'environment_rotation is in degrees'),
        ('environment_rotation', float('nan'), 'environment_rotation'),
        # REVIEW.md SRV-183: "0 by default" read as its value when left out
        (
            'environment_exposure',
            10.5,
            r"environment_exposure is the environment's Exposure, -10 to 10 \(Designer starts at 0\), not 10\.5",
        ),
        ('environment_exposure', -11.0, 'environment_exposure is'),
        ('environment_exposure', float('nan'), 'environment_exposure'),
    ],
)
def test_options_out_of_range_are_refused(
    monkeypatch: pytest.MonkeyPatch,
    temp_folders: list[str],
    option: str,
    value: Json,
    message: str,
) -> None:
    sent = _bridge(monkeypatch, temp_folders)
    with pytest.raises(ToolError, match=message):
        _shoot({'panel': '3d', option: value})
    assert sent == []


def _sent_mesh(code: str) -> str:
    """The mesh a shoot_3d call sends, its third argument."""
    call = _call(code)
    assert call.startswith('shoot_3d(')
    return str(ast.literal_eval(call[len('shoot_3d') :])[2])


@pytest.mark.parametrize(
    'given', ['box.OBJ', os.path.join('meshes', '..', 'box.OBJ'), os.path.join('~', 'box.OBJ')], ids=['here', 'up', '~']
)
def test_a_mesh_files_path_is_made_absolute(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], tmp_path: Path, given: str
) -> None:
    # Designer would resolve a relative path against its own working folder, as the bitmap op's (REVIEW.md SRV-27). The
    # extension in any case: Designer's own meshes end in .FBX too
    (tmp_path / 'box.OBJ').write_text('o box\n', encoding='utf-8')
    os.makedirs(tmp_path / 'meshes')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('HOME', os.getcwd())
    monkeypatch.setenv('USERPROFILE', os.getcwd())  # ~ on Windows (REVIEW.md TST-349)
    sent = _bridge(monkeypatch, temp_folders)
    _shoot({'panel': '3d', 'mesh': given})
    assert _sent_mesh(sent[0]) == os.path.join(os.getcwd(), 'box.OBJ')


@pytest.mark.parametrize(
    'mesh, message',
    [
        (
            'box.png',
            r"mesh 'box\.png' is neither one of the 3D view's Scene menu nor a mesh file Designer imports \(usd, usda, "
            r'usdz, fbx, obj, 3ds, dae, dxf, stl, ply, gltf, glb\)$',
        ),
        (os.path.join('meshes', 'box'), r"mesh '.*box' is neither one of the 3D view's Scene menu"),  # no extension
        ('gone.fbx', 'mesh: no such file: {}$'),  # made absolute first, as os.path does (REVIEW.md TST-999)
    ],
    ids=['another extension', 'no extension', 'no such file'],
)
def test_a_mesh_path_of_another_format_or_of_no_file_is_refused_before_designer(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], tmp_path: Path, mesh: str, message: str
) -> None:
    (tmp_path / 'box.png').write_bytes(b'')
    monkeypatch.chdir(tmp_path)
    sent = _bridge(monkeypatch, temp_folders)
    with pytest.raises(ToolError, match=message.format(re.escape(os.path.join(os.getcwd(), mesh)))):
        _shoot({'panel': '3d', 'mesh': mesh})
    assert sent == []


@pytest.mark.parametrize('name', list(state3d.FRAMING))
def test_a_scene_menu_mesh_is_sent_by_its_name(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], name: str
) -> None:
    # no name of the Scene menu's has an extension or a folder: none is taken for a path (the helper knows the names)
    sent = _bridge(monkeypatch, temp_folders)
    _shoot({'panel': '3d', 'mesh': name})
    assert _sent_mesh(sent[0]) == name


def test_the_3d_view_is_set_up_and_shot_in_one_helper_call(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    # shoot_3d keeps Designer's window on screen through both (REVIEW.md SRV-146)
    sent = _bridge(monkeypatch, temp_folders, NOTE + '\n3d render 4x4\n')
    _shoot({'panel': '3d', **OPTIONS})
    assert len(sent) == 1
    shot = os.path.join(temp_folders[-1], 'shot.png')
    assert _call(sent[0]) == (
        "shoot_3d(%r, 'g', 'Plane', 'Top', 2, 2.0, (90.0, -30.0), (0.25, 0.5), 'studio', 90.0, 1.0, "
        "'AdobeStandardMaterial')" % shot
    )


@pytest.mark.parametrize(
    'option, value',
    [
        # the rotation and the exposure are values written in the state file, 0 included: unlike a turn, pan or zoom
        # of 0, not nothing to do
        ('environment_rotation', 0.0),
        ('environment_exposure', 0.0),
        # the limits taken (REVIEW.md TST-538: only values past them were tried)
        ('environment_rotation', 180.0),
        ('environment_rotation', -180.0),
        ('environment_exposure', 10.0),
        ('environment_exposure', -10.0),
    ],
)
def test_an_environment_value_is_sent_as_given(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], option: str, value: float
) -> None:
    sent = _bridge(monkeypatch, temp_folders)
    _shoot({'panel': '3d', option: value})
    rotation, exposure = (value, None) if option == 'environment_rotation' else (None, value)
    shot = os.path.join(temp_folders[-1], 'shot.png')
    assert _call(sent[0]) == 'shoot_3d(%r, None, None, None, 0, None, None, None, None, %r, %r, None)' % (
        shot,
        rotation,
        exposure,
    )
    with pytest.raises(ToolError, match=r"panel='3d'"):
        _shoot({'panel': 'graph', option: value})


def _plain(panel: str, folders: list[str]) -> str:
    """The helper call of a shot with nothing set up: the 3D view's shoot_3d with no set-up, another panel's
    save_screenshot."""
    shot = os.path.join(folders[-1], 'shot.png')
    if panel == '3d':
        return 'shoot_3d(%r, None, None, None, 0, None, None, None, None, None, None, None)' % shot
    return 'save_screenshot(%r, %r)' % (panel, shot)


STEPS = "3D view, setting: Plane, view Top, framed, +2 zoom steps, tiling 2\n3D view, setting: graph g's outputs on the mesh\n"


def test_the_setup_line_comes_beside_the_image(monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]) -> None:
    # the notes said before each step aren't kept once the summary line is there (REVIEW.md HLP-119)
    _bridge(monkeypatch, temp_folders, STEPS + NOTE + '\n3d render 4x4\n')
    result = views.screenshot_designer('3d', mesh='Plane')
    assert isinstance(result[0], Image) and result[1:] == [NOTE]


def test_a_set_up_that_stopped_says_the_steps_it_began(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    # REVIEW.md HLP-119: an abort after the view's note, no summary printed
    printed = STEPS + '--- ERROR ---\nScriptAborted: cancelled by client after 3.0s\n'
    _bridge(monkeypatch, temp_folders, printed, shot=False)
    with pytest.raises(ToolError) as raised:
        server.screenshot_designer('3d', mesh='Plane', view='Top')
    assert str(raised.value).splitlines() == [
        'ScriptAborted: cancelled by client after 3.0s',
        *STEPS.splitlines(),
    ]


FRONT = (
    "Designer's window: brought in front, transparent and without taking focus, as its 3D view isn't drawn while "
    'covered'
)
BACK = "Designer's window: put back behind the window that was in front of it"
STALE = (
    '3D render: identical to the render before the set-up, though the set-up moved the camera, switched the mesh, or '
    'changed the tiling, the light or the shader model.'
)


def test_what_was_done_to_designers_window_and_a_stale_render_come_beside_the_image(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    # REVIEW.md SRV-146: the user's window changed, or the render may be the view's last frame
    printed = FRONT + '\n' + STEPS + NOTE + '\n3d render 4x4\n' + STALE + '\n' + BACK + '\n'
    _bridge(monkeypatch, temp_folders, printed)
    result = views.screenshot_designer('3d', mesh='Plane')
    assert isinstance(result[0], Image) and result[1:] == [FRONT, NOTE, STALE, BACK]


def test_a_shot_that_failed_says_what_was_done_to_designers_window(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    printed = FRONT + '\n' + STEPS + '--- ERROR ---\nScriptAborted: cancelled by client after 3.0s\n'
    _bridge(monkeypatch, temp_folders, printed, shot=False)
    with pytest.raises(ToolError) as raised:
        server.screenshot_designer('3d', mesh='Plane', view='Top')
    assert str(raised.value).splitlines() == [
        'ScriptAborted: cancelled by client after 3.0s',
        FRONT,
        *STEPS.splitlines(),
    ]


@pytest.mark.parametrize('panel', ['3d', 'graph'])
@pytest.mark.parametrize(
    'option, value',
    [
        ('orbit', [0.0, 0.0]),
        ('pan', [0.0, 0.0]),
        ('zoom', 0),
        ('graph', ''),
        ('mesh', ''),
        ('view', ''),
        ('environment', ''),
        ('shader_model', ''),
    ],
    ids=['orbit', 'pan', 'zoom', 'graph', 'mesh', 'view', 'environment', 'shader_model'],
)
def test_a_turn_pan_or_zoom_of_zero_or_an_empty_name_sets_nothing_up(
    monkeypatch: pytest.MonkeyPatch,
    temp_folders: list[str],
    panel: str,
    option: str,
    value: Json,
) -> None:
    # REVIEW.md TST-336: nothing to set, so not sent, and not refused with another panel; SRV-147: '' is no name
    sent = _bridge(monkeypatch, temp_folders)
    result = _shoot({'panel': panel, option: value})
    assert _call(sent[0]) == _plain(panel, temp_folders)
    assert isinstance(result, CallToolResult) and [b.type for b in result.content] == ['image']


@pytest.mark.parametrize('panel', ['3d', 'graph'])
def test_without_options_nothing_is_set_up_and_only_the_image_comes_back(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], panel: str
) -> None:
    sent = _bridge(monkeypatch, temp_folders)
    result = views.screenshot_designer(panel)
    assert _call(sent[0]) == _plain(panel, temp_folders)
    assert len(result) == 1 and isinstance(result[0], Image)


@pytest.mark.parametrize(
    'printed, options',
    [
        (STEPS + NOTE + '\nRuntimeError: the 3D View menu bar not found\n', {}),
        (STEPS + NOTE + '\n3d render 4x4\n', {'crop': [0.0, 0.0, 0.1, 0.1]}),
    ],
    ids=['render', 'crop'],
)
def test_a_shot_that_fails_after_the_set_up_says_what_was_set(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], printed: str, options: dict[str, list[float]]
) -> None:
    # REVIEW.md HLP-107: the set-up's line said after the error, the view put back after it (scene3d.py)
    _bridge(monkeypatch, temp_folders, printed, shot='crop' in options)
    with pytest.raises(ToolError) as raised:
        server.screenshot_designer('3d', mesh='Plane', **options)
    assert str(raised.value).splitlines()[-1] == NOTE


# what shown_3d prints, in part: the 3D view as text, a line each (designer_helpers/scene3d.py)
SHOWN = 'mesh: Sphere\ntiling: 2\nrenderer: Rasterizer\n'
LEFTOVER = (
    "3D view: a backup of the 3D view's default state, left by an earlier call, was put back first: "
    '/16.0/user_view3d_settings.sbsscn'
)


def _read(monkeypatch: pytest.MonkeyPatch, printed: str) -> list[str]:
    """The calls sent to Designer, each answered with `printed`: as_text renders nothing, so no shot is left."""
    sent: list[str] = []

    def bridge(code: str) -> str:
        sent.append(code)
        return printed

    fake_bridge(monkeypatch, bridge)
    return sent


def test_the_3d_view_as_text_is_read_with_no_render(monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]) -> None:
    sent = _read(monkeypatch, SHOWN)
    result = _shoot({'panel': '3d', 'as_text': True})
    assert [_call(code) for code in sent] == ['shown_3d()']
    assert temp_folders == []  # no folder for a shot
    assert isinstance(result, CallToolResult)
    assert [(type(b), b.text if isinstance(b, TextContent) else None) for b in result.content] == [
        (TextContent, SHOWN.strip())
    ]


UNTAKEN: dict[str, Json] = {**OPTIONS, 'crop': [0.0, 0.0, 0.5, 0.5]}  # what as_text takes none of


@pytest.mark.parametrize('option', sorted(UNTAKEN))
def test_as_text_with_a_set_up_option_or_a_crop_is_refused(monkeypatch: pytest.MonkeyPatch, option: str) -> None:
    # as_text says what the view shows: a set-up would change it, and a crop needs a render. The option named after
    # the message's own words, which hold "3D view" (REVIEW.md TST-969)
    sent = _read(monkeypatch, SHOWN)
    with pytest.raises(ToolError, match=r'it takes no .*\b%s\b' % option):
        _shoot({'panel': '3d', 'as_text': True, option: UNTAKEN[option]})
    assert sent == []


@pytest.mark.parametrize(
    'option, value',
    [('orbit', [0.0, 0.0]), ('pan', [0.0, 0.0]), ('zoom', 0), ('mesh', ''), ('environment', ''), ('shader_model', '')],
    ids=['orbit', 'pan', 'zoom', 'mesh', 'environment', 'shader_model'],
)
def test_as_text_takes_the_options_that_set_nothing_up(
    monkeypatch: pytest.MonkeyPatch, option: str, value: Json
) -> None:
    # a turn, pan or zoom of 0, or an empty name, sets nothing up (REVIEW.md TST-336, SRV-147): no reason to refuse
    sent = _read(monkeypatch, SHOWN)
    _shoot({'panel': '3d', 'as_text': True, option: value})
    assert [_call(code) for code in sent] == ['shown_3d()']


def test_as_text_that_failed_says_the_leftover_backup_put_back(monkeypatch: pytest.MonkeyPatch) -> None:
    # a backup an earlier call left, put back before the Save that then failed: said as a shot says it (scene3d.py)
    error = "RuntimeError: Scene > Save Current State As Default didn't write /16.0/user_view3d_settings.sbsscn"
    _read(monkeypatch, LEFTOVER + '\n--- ERROR ---\n' + error + '\n')
    with pytest.raises(ToolError) as raised:
        views.screenshot_designer('3d', as_text=True)
    assert str(raised.value).splitlines() == [error, LEFTOVER]
