"""screenshot_designer's 3D view options (ROADMAP items 7 and 74): what the server refuses before reaching Designer, and how it
calls the helpers. Driving the 3D view itself is checked live (editor_panels_and_fit)."""

import asyncio
import os

import pytest
from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, InputRequiredResult
from PIL import Image as PILImage

from conftest import fake_bridge, server
from project_constants import Json
from server_tools import views

NOTE = "3D view: Plane, graph g's outputs on the mesh, view Top, framed, +2 wheel steps, tiling 2 (the Parameters panel back on g)"


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
}


def _shoot(arguments: dict[str, Json]) -> CallToolResult | InputRequiredResult:
    """screenshot_designer called as an agent's client does: through the server, which validates the arguments first and
    gives the tool orbit and pan as tuples (REVIEW.md TST-534: called directly with lists, a test hid a TypeError)."""
    result: CallToolResult | InputRequiredResult = asyncio.run(
        server.server.call_tool('screenshot_designer', arguments)
    )
    return result


@pytest.mark.parametrize('option', sorted(OPTIONS))
def test_3d_options_need_the_3d_panel(monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], option: str) -> None:
    sent = _bridge(monkeypatch, temp_folders)
    with pytest.raises(ToolError, match=r"panel='3d'"):
        _shoot({'panel': 'graph', option: OPTIONS[option]})
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


def test_the_3d_view_is_set_up_and_shot_in_one_helper_call(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    # shoot_3d keeps Designer's window on screen through both (REVIEW.md SRV-146)
    sent = _bridge(monkeypatch, temp_folders, NOTE + '\n3d render 4x4\n')
    _shoot({'panel': '3d', **OPTIONS})
    assert len(sent) == 1
    shot = os.path.join(temp_folders[-1], 'shot.png')
    assert _call(sent[0]) == "shoot_3d(%r, 'g', 'Plane', 'Top', 2, 2.0, (90.0, -30.0), (0.25, 0.5))" % shot


def _plain(panel: str, folders: list[str]) -> str:
    """The helper call of a shot with nothing set up: the 3D view's shoot_3d with no set-up, another panel's
    save_screenshot."""
    shot = os.path.join(folders[-1], 'shot.png')
    if panel == '3d':
        return 'shoot_3d(%r, None, None, None, 0, None, None, None)' % shot
    return 'save_screenshot(%r, %r)' % (panel, shot)


STEPS = '3D view, setting: Plane\n3D view, setting: view Top, framed\n'


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
        '3D view, setting: Plane',
        '3D view, setting: view Top, framed',
    ]


FRONT = (
    "Designer's window: brought in front, transparent and without taking focus, as its 3D view isn't drawn while "
    'covered'
)
BACK = "Designer's window: put back behind the window that was in front of it"
STALE = '3D render: identical to the render before the set-up, though the set-up moved the camera or switched the mesh.'


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
        '3D view, setting: Plane',
        '3D view, setting: view Top, framed',
    ]


@pytest.mark.parametrize('panel', ['3d', 'graph'])
@pytest.mark.parametrize(
    'option, value',
    [('orbit', [0.0, 0.0]), ('pan', [0.0, 0.0]), ('zoom', 0), ('graph', ''), ('mesh', ''), ('view', '')],
    ids=['orbit', 'pan', 'zoom', 'graph', 'mesh', 'view'],
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
    # REVIEW.md HLP-107: the user's 3D view was changed all the same
    _bridge(monkeypatch, temp_folders, printed, shot='crop' in options)
    with pytest.raises(ToolError) as raised:
        server.screenshot_designer('3d', mesh='Plane', **options)
    assert str(raised.value).splitlines()[-1] == NOTE
