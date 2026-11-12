"""screenshot_designer's 3D view options (ROADMAP items 7 and 74): what the server refuses before reaching Designer, and how it
calls the helpers. Driving the 3D view itself is checked live (editor_panels_and_fit)."""

import os
from typing import Any

import pytest
from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image as PILImage

from conftest import patch_server, server

NOTE = "3D view: Plane, graph g's outputs on the mesh, view Top, framed, +2 wheel steps, tiling 2 (the Parameters panel back on g)"


def _bridge(
    monkeypatch: pytest.MonkeyPatch, folders: list[str], printed: str = '3d render 4x4\n', shot: bool = True
) -> list[str]:
    """The calls sent to Designer; each answers with `printed` and, if `shot`, leaves a 4x4 image where the shot
    goes, in the folder the server made (folders: the temp_folders fixture, its name with a backslash, as a Windows
    path has: REVIEW.md TST-325)."""
    sent: list[str] = []

    def bridge(code: str, path: str | None = None, timeout: float | None = None) -> str:
        sent.append(code)
        shot_path = os.path.join(folders[-1], 'shot.png')
        assert repr(shot_path) in code  # where the helper is told to save it
        if shot:
            PILImage.new('RGB', (4, 4)).save(shot_path)
        return printed

    patch_server(monkeypatch, '_bridge', bridge)
    return sent


def _call(code: str) -> str:
    """The helper call after the helpers' source (_helpers_call: the source, a blank line, the call)."""
    return code[code.rindex('\n\n') + 2 :]


OPTIONS = {
    'graph': 'g',
    'mesh': 'Plane',
    'view': 'Top',
    'zoom': 2,
    'tiling': 2.0,
    'orbit': [90.0, -30.0],
    'pan': [0.25, 0.5],
}


@pytest.mark.parametrize('option', sorted(OPTIONS))
def test_3d_options_need_the_3d_panel(monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], option: str) -> None:
    sent = _bridge(monkeypatch, temp_folders)
    with pytest.raises(ToolError, match=r"panel='3d'"):
        server.screenshot_designer('graph', **{option: OPTIONS[option]})
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
        ('orbit', [181.0, 0.0], r'orbit is \[right, up\] in degrees'),
        ('orbit', [0.0, -91.0], r'orbit is \[right, up\] in degrees'),
        ('orbit', [90.0], r'orbit is \[right, up\] in degrees'),
        ('orbit', [1.0, 2.0, 3.0], r'orbit is \[right, up\] in degrees'),
        ('pan', [1.5, 0.0], r'pan is \[right, up\] in fractions of the view'),
        ('pan', [0.0, -1.01], r'pan is \[right, up\] in fractions of the view'),
        ('pan', [0.5], r'pan is \[right, up\] in fractions of the view'),
    ],
)
def test_options_out_of_range_are_refused(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], option: str, value: Any, message: str
) -> None:
    sent = _bridge(monkeypatch, temp_folders)
    with pytest.raises(ToolError, match=message):
        server.screenshot_designer('3d', **{option: value})
    assert sent == []


def test_the_3d_view_is_set_up_in_the_same_job_before_its_render(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]
) -> None:
    sent = _bridge(monkeypatch, temp_folders, NOTE + '\n3d render 4x4\n')
    server.screenshot_designer('3d', **OPTIONS)
    assert len(sent) == 1
    call = _call(sent[0])
    setup = call.index("set_3d_view('g', 'Plane', 'Top', 2, 2.0, [90.0, -30.0], [0.25, 0.5])")
    assert setup < call.index("save_screenshot('3d', ")


STEPS = '3D view, setting: Plane\n3D view, setting: view Top, framed\n'


def test_the_setup_line_comes_beside_the_image(monkeypatch: pytest.MonkeyPatch, temp_folders: list[str]) -> None:
    # the notes said before each step aren't kept once the summary line is there (REVIEW.md HLP-119)
    _bridge(monkeypatch, temp_folders, STEPS + NOTE + '\n3d render 4x4\n')
    result: Any = server.screenshot_designer('3d', mesh='Plane')
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


@pytest.mark.parametrize('panel', ['3d', 'graph'])
@pytest.mark.parametrize(
    'option, value', [('orbit', [0.0, 0.0]), ('pan', [0.0, 0.0]), ('zoom', 0)], ids=['orbit', 'pan', 'zoom']
)
def test_a_turn_pan_or_zoom_of_zero_sets_nothing_up(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], panel: str, option: str, value: Any
) -> None:
    # REVIEW.md TST-336: nothing to set, so not sent, and not refused with another panel
    sent = _bridge(monkeypatch, temp_folders)
    result: Any = server.screenshot_designer(panel, **{option: value})
    assert 'set_3d_view' not in _call(sent[0])
    assert len(result) == 1 and isinstance(result[0], Image)


@pytest.mark.parametrize('panel', ['3d', 'graph'])
def test_without_options_nothing_is_set_up_and_only_the_image_comes_back(
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], panel: str
) -> None:
    sent = _bridge(monkeypatch, temp_folders)
    result: Any = server.screenshot_designer(panel)
    assert 'set_3d_view' not in _call(sent[0])
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
    monkeypatch: pytest.MonkeyPatch, temp_folders: list[str], printed: str, options: dict[str, Any]
) -> None:
    # REVIEW.md HLP-107: the user's 3D view was changed all the same
    _bridge(monkeypatch, temp_folders, printed, shot='crop' in options)
    with pytest.raises(ToolError) as raised:
        server.screenshot_designer('3d', mesh='Plane', **options)
    assert str(raised.value).splitlines()[-1] == NOTE
