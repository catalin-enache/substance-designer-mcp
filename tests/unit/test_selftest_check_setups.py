"""What live checks do with the answers they get, on fakes: a capture ending on the client's side first (REVIEW.md
TST-256), a view not visible in a Designer the self-test started (TST-258), the state a check is about not reached
(TST-259), what the 3D zoom's checks say when they fail (TST-664 to TST-666), and a check skipped in the user's Designer
(TST-817). The checks themselves run against the real Designer: this is what a run that passes can't show."""

import ast
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import NoReturn, Unpack

import pytest
from selftest_fakes import Designer, FakeCall, code_of, fresh, tool_result

from conftest import View3dOptions
from project_constants import TAG_LENGTH, TAG_PREFIX, ToolArgs

NOT_VISIBLE = 'the 3D View panel is not visible in Designer'


def _image() -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type='image', data='')], is_error=False)


def _common() -> ModuleType:
    return sys.modules['test_all_tools.common']


def _clipboard(monkeypatch: pytest.MonkeyPatch, editor: ModuleType, held: bytes) -> tuple[list[bytes], list[bytes]]:
    """The machine's clipboard replaced: [what it holds], and what the check wrote to it."""
    state, written = [held], []

    def write(data: bytes) -> None:
        written.append(data)
        state[0] = data

    monkeypatch.setitem(vars(editor), 'clipboard_text', lambda: state[0])
    monkeypatch.setitem(vars(editor), 'set_clipboard_text', write)
    monkeypatch.setattr(editor.sys, 'platform', 'darwin')
    return state, written


def test_a_capture_cancelled_on_the_clients_side_can_only_put_the_users_text_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # REVIEW.md TST-256: Designer's job backs up the clipboard as it starts and restores it as it ends, after the
    # check's finally when the call ended first (Ctrl-C): what it backed up must be the user's text, not the check's
    editor = fresh('editor_panels_and_fit.checks')
    state, written = _clipboard(monkeypatch, editor, b'my text')
    backed_up: list[bytes] = []

    async def c(name: str, args: ToolArgs | None = None) -> NoReturn:
        backed_up.append(state[0])
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(editor.check_the_3d_capture_puts_the_text_back(SimpleNamespace(c=c, was_running=False)))
    assert backed_up == [b'my text'] and editor.TEXT not in written


@pytest.mark.parametrize('held', [b'my text', b''], ids=['the users text', 'no text'])
@pytest.mark.parametrize('put_back', [True, False], ids=['put back', 'not put back'])
def test_the_3d_capture_check_still_tells_a_capture_that_put_nothing_back(
    monkeypatch: pytest.MonkeyPatch, held: bytes, put_back: bool
) -> None:
    editor = fresh('editor_panels_and_fit.checks')
    state, _ = _clipboard(monkeypatch, editor, held)

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        if not put_back:
            state[0] = b''  # the render left there: no text
        return _image()

    asyncio.run(editor.check_the_3d_capture_puts_the_text_back(SimpleNamespace(c=c, was_running=False)))
    assert _common().results['screenshot_designer'] == [put_back]
    assert state[0] == held, "the user's text back, whatever the capture did"


@pytest.mark.parametrize('name', ['check_every_panels_screenshot', 'check_the_3d_capture_puts_the_text_back'])
@pytest.mark.parametrize('was_running', [True, False], ids=['the users Designer', 'one the self-test started'])
def test_a_view_not_visible_is_a_skip_only_in_the_users_designer(
    monkeypatch: pytest.MonkeyPatch, name: str, was_running: bool
) -> None:
    # REVIEW.md TST-258: in a Designer the self-test started every view shows; a skip hid whatever broke them
    editor = fresh('editor_panels_and_fit.checks')
    _clipboard(monkeypatch, editor, b'my text')

    async def c(tool: str, args: ToolArgs | None = None) -> SimpleNamespace:
        return tool_result(NOT_VISIBLE, True)

    asyncio.run(getattr(editor, name)(SimpleNamespace(c=c, was_running=was_running)))
    assert bool(_common().skipped) == was_running
    assert (False in _common().results['screenshot_designer']) != was_running


@pytest.mark.parametrize('was_running', [True, False], ids=['the users Designer', 'one the self-test started'])
def test_the_parent_item_facts_run_only_in_a_designer_the_self_test_started(was_running: bool) -> None:
    # REVIEW.md TST-817
    checks = fresh('editor_open_and_zoom.checks')
    c = Designer('')
    asyncio.run(checks.check_parent_item_hands_a_scene_item_to_python(SimpleNamespace(c=c, was_running=was_running)))
    assert bool(c.calls) != was_running, c.calls
    assert bool(_common().skipped) == was_running


def _measure_designer(calls: list[str], broken: str = '') -> FakeCall:
    """The answers of check_a_node_measured_right_after_the_one_feeding_it; `broken`: the setup call that fails."""

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        calls.append(name)
        args = args or {}
        if name == 'open_graph':
            return tool_result('no such graph', True) if broken == 'open_graph' else tool_result('opened g')
        if name == 'apply_edits':
            return tool_result("added 9\n  ref 'up' = 1\n  ref 'down' = 2\n")
        if name == 'node_stats' and args['node_id'] == '1' and broken == 'upstream':
            return tool_result('the node computed nothing', True)
        if name == 'node_stats':
            return tool_result('pixel (0,0) = 0\npixel (256,256) = 0')
        if name == 'execute_designer_code':
            return tool_result('TEXTURE=True')
        return _image()

    return c


def test_the_check_of_a_node_measured_after_its_upstream_passes_when_its_state_is_reached() -> None:
    measure = fresh('measure.checks')
    calls: list[str] = []
    ctx = SimpleNamespace(c=_measure_designer(calls), G={'graph': 'g'}, helper_source='')
    asyncio.run(measure.check_a_node_measured_right_after_the_one_feeding_it(ctx))
    assert not [tool for tool, oks in _common().results.items() if not all(oks)], _common().results


@pytest.mark.parametrize('broken', ['open_graph', 'upstream'])
def test_the_check_of_a_node_measured_after_its_upstream_fails_when_its_state_isnt_reached(broken: str) -> None:
    # REVIEW.md TST-259: HLP-100 shows only with the graph open and the upstream node just measured; neither answer
    # was read, so the check passed in a state where the defect never shows
    measure = fresh('measure.checks')
    calls: list[str] = []
    ctx = SimpleNamespace(c=_measure_designer(calls, broken), G={'graph': 'g'}, helper_source='')
    asyncio.run(measure.check_a_node_measured_right_after_the_one_feeding_it(ctx))
    assert [tool for tool, oks in _common().results.items() if not all(oks)], _common().results
    if broken == 'open_graph':
        assert 'node_stats' not in calls, 'nothing measured in a state the check is not about'


class Shots3d:
    """editor_panels_and_fit's 3D checks on fakes: each shot leaves an empty file where its code names one under
    `folder`, the tool answers `replies` by a mark its code holds (the first that matches; a call with no code by its
    tool's name), the renders' plane widths
    come from `widths` by file name (290 px otherwise), any two renders are 0.00 apart,
    and with_checker shows the checker or not. `said` holds the renders say_renders was given, `calls` what was
    called."""

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        folder: Path,
        widths: dict[str, int],
        replies: dict[str, str],
        checker: bool = True,
    ) -> None:
        self.editor = fresh('editor_panels_and_fit.checks')
        self.said: list[tuple[tuple[str, str], ...]] = []
        self.calls: list[str] = []
        monkeypatch.setattr(self.editor.sys, 'platform', 'darwin')

        async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
            code = code_of(args)
            # each path as the code holds it, written with %r, which escapes a backslash (REVIEW.md TST-689)
            for literal in re.findall(r"'(?:[^'\\]|\\.)*\.png'", code):
                path = Path(ast.literal_eval(literal))
                if path.is_relative_to(folder):
                    path.touch()
            self.calls.append(name)
            said = code or name  # a call with no code, as screenshot_designer's, answered by its name
            return tool_result(next((reply for mark, reply in replies.items() if mark in said), ''))

        async def with_checker(call: FakeCall, args: ToolArgs) -> SimpleNamespace:
            self.calls.append('with_checker')
            return _image()

        async def at_rest(call: FakeCall, source: str) -> None:
            pass

        def render(path: str) -> SimpleNamespace:
            return SimpleNamespace(path=path, shape=(362, 342))

        def width(a: SimpleNamespace) -> int:
            return widths.get(os.path.basename(a.path), 290)

        for name, value in {
            'with_checker': with_checker,
            'at_rest': at_rest,
            'grey': lambda r: r,
            'transitions': lambda a: 40 if checker else 0,
            'grey_file': render,
            'plane_width': width,
            'plane_columns': lambda a: (20, 300),
            'difference': lambda a, b: 0.0,
            'say_renders': lambda *renders: self.said.append(renders),
        }.items():
            monkeypatch.setitem(vars(self.editor), name, value)
        self.ctx = SimpleNamespace(c=c, was_running=False, scratch=str(folder), helper_source='')


UNDRAWN = "3D render: the 3D view hadn't settled within 3 s after Designer's window came back on screen"


# the 3D view as text (scene3d._3d_shown): the Plane, a light and a shader model unlike Designer's defaults, so that a
# reader saying them fails the test (REVIEW.md TST-965), then what isn't a set-up option
SHOWN_TEXT = [
    'mesh: Plane',
    'tiling: 1.5',
    'environment: studio',
    'environment_rotation: 108',
    'environment_exposure: 0.7',
    'camera: yaw 45, pitch 30 degrees (view Front then orbit [45, 30]), looking at (0, 50, 0) from 180.99 away',
    'shader_model: UsdPreviewSurface',
    'renderer: Rasterizer',
]


def shown_already_names(**fakes: object) -> dict[str, object]:
    """The names SHOWN_ALREADY (and SETTLED) take from the helpers, faked: a Designer whose 3D view as text is
    SHOWN_TEXT; `fakes` replace or add some."""
    names: dict[str, object] = {
        '_Frames': SimpleNamespace(settled=None),
        'shoot_3d': lambda path, **shown: None,
        '_3d_shown': lambda: list(SHOWN_TEXT),
        '_state_load': lambda bar, keep, watched, *rest: None,
    }
    return {**names, **fakes}


def test_the_shown_already_checks_count_of_waits_keeps_each_waits_result(capsys: pytest.CaptureFixture[str]) -> None:
    # REVIEW.md TST-678: the wrapper counting the settles returned None, read as unsettled since HLP-214: a failing
    # run's "hadn't settled" lines weren't so. TST-939: the snippet wraps _state_load too, which the fake shot never
    # calls, so it counts no load
    editor = fresh('editor_panels_and_fit.checks')
    results: list[object] = []

    class Frames:
        def settled(self, since: str) -> bool:
            return since == 'back at rest'

    def shoot_3d(path: str, **shown: object) -> None:
        if path.endswith('again.png'):  # the shot whose waits are counted
            results.extend(Frames().settled(since) for since in ('back at rest', 'its net reached'))

    exec(editor.SHOWN_ALREADY % '/folder', shown_already_names(_Frames=Frames, shoot_3d=shoot_3d))
    assert results == [True, False]
    assert re.search(r'^LOADS=0$', capsys.readouterr().out, re.M)


def test_the_shown_already_check_gives_the_shot_what_the_3d_view_as_text_says() -> None:
    # ROADMAP item 85: the values read as as_text reads them, the set-up's options passed back as the text gives them;
    # the reader's backup is where a shot finds a leftover (REVIEW.md TST-944: test_view3d_helpers.py)
    editor = fresh('editor_panels_and_fit.checks')
    shots: list[tuple[str, View3dOptions]] = []  # each shot's file and its set-up (REVIEW.md TST-1000)

    def shoot(path: str, **shown: Unpack[View3dOptions]) -> None:
        shots.append((os.path.basename(path), shown))

    exec(editor.SHOWN_ALREADY % '/folder', shown_already_names(shoot_3d=shoot))
    given: View3dOptions = {
        'mesh': 'Plane',
        'tiling': 1.5,
        'environment': 'studio',
        'environment_rotation': 108.0,
        'environment_exposure': 0.7,
        'shader_model': 'UsdPreviewSurface',
    }
    assert shots == [('plain.png', {}), ('again.png', given)]


@pytest.mark.parametrize('snippet', ['SETTLED', 'SHOWN_ALREADY'])
def test_a_snippet_wrapping_the_state_files_load_passes_the_set_ups_arguments_through(snippet: str) -> None:
    # the set-up's loads give _state_load whether the Scene menu lists the file's mesh (REVIEW.md HLP-283): a wrapper
    # taking three arguments raised a TypeError at the shot's first load
    editor = fresh('editor_panels_and_fit.checks')
    passed: list[tuple[object, ...]] = []
    names = shown_already_names(
        _state_load=lambda *args: passed.append(args), _relinked=lambda *args: '', _3d_render=lambda mw: None
    )

    def shoot_3d(path: str, **options: object) -> None:  # the set-up's load, as scene3d's loading calls it
        load = names['_state_load']
        assert callable(load)
        load('bar', 'keep', 'watched', False)

    names['shoot_3d'] = shoot_3d
    code = getattr(editor, snippet)
    exec(code % (('/after.png', '/shot.png', 'studio') if snippet == 'SETTLED' else '/folder'), names)
    assert ('bar', 'keep', 'watched', False) in passed, passed


def test_a_package_file_with_no_uid_is_read_as_none() -> None:
    # REVIEW.md TST-945: a cast hid the None, and the check's AttributeError ended facts.run before the state file checks
    facts = fresh('facts.checks')
    assert facts._file_uid('<package><fileUID v="1234"/></package>') == '1234'
    assert facts._file_uid('<package/>') is None


RASTER_CHECK = 'check_an_on_screen_3d_zoom_held_below_8_samples_names_the_rasterizers_settings'
# the zoom's plane, 3 steps closer than at the start's 290 px (editor checks' STEP)
ZOOMED = {'raster_samples_zoom.png': 397, 'raster_aa_zoom.png': 397}


@pytest.mark.parametrize(
    'samples_back, aa_back, says',
    [
        # each put-back raised, its reply holding another line with ' after', as UNDRAWN's was before REVIEW.md HLP-222
        (UNDRAWN + '\nRuntimeError: NOT_AS_READ', UNDRAWN + '\nRuntimeError: NOT_AS_READ', ["wasn't read after"] * 2),
        (  # left as set
            'RASTERIZER samples=4.0 aa=True after',
            'RASTERIZER samples=8.0 aa=False after',
            ['Samples 4.0 (8.0 by default)', 'antialiasing False (True by default)'],
        ),
        ('RASTERIZER samples=8.0 aa=True after',) * 2 + ([],),  # put back
    ],
    ids=['the put-back raised', 'the value left as set', 'put back'],
)
def test_the_rasterizer_check_fails_when_its_setting_isnt_put_back(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    samples_back: str,
    aa_back: str,
    says: list[str],
) -> None:
    # REVIEW.md TST-677: each put-back's reply held UNDRAWN ("... after Designer's window came back on screen") before
    # HLP-222, so a guard reading ' after' couldn't fail: the later 3D checks would run at Samples 4. TST-683: the FAIL
    # says what it read after the put-back, as the precondition does before
    before = 'RASTERIZER samples=8.0 aa=True before\n'
    replies = {
        'float(4.0)': before + 'RASTERIZER samples=4.0 aa=True after',
        'float(False)': before + 'RASTERIZER samples=8.0 aa=False after',
        'float(8.0)': samples_back,
        'float(True)': aa_back,
    }
    shots = Shots3d(monkeypatch, tmp_path, {}, replies)
    asyncio.run(getattr(shots.editor, RASTER_CHECK)(shots.ctx))
    lines = [line for line in capsys.readouterr().out.splitlines() if 'after the put-back' in line]
    assert len(lines) == len(says) and all(line.startswith('FAIL') for line in lines), lines
    assert all(part in line for part, line in zip(says, lines, strict=True)), lines


def test_the_rasterizer_checks_precondition_says_which_setting_it_read_off_its_default(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-680: "not set, not at Designer's defaults" was said when the case's own set ran, the other setting
    # left lowered by the case before
    replies = {
        'float(4.0)': 'RASTERIZER samples=8.0 aa=False before\nRASTERIZER samples=4.0 aa=False after',
        'float(False)': 'RASTERIZER samples=4.0 aa=True before\nRASTERIZER samples=4.0 aa=False after',
    }
    shots = Shots3d(monkeypatch, tmp_path, {}, replies)
    asyncio.run(getattr(shots.editor, RASTER_CHECK)(shots.ctx))
    out = capsys.readouterr().out
    said = [line for line in out.splitlines() if 'by default' in line]
    assert len(said) == 2 and all(line.startswith('FAIL') for line in said), out
    assert 'antialiasing False (True by default)' in said[0] and 'Samples 4.0 (8.0 by default)' in said[1], said
    assert 'not set' not in out, out


# what the zoom's shot says of its step left below 8 (designer_helpers/scene3d.py; frames3d.HELD)
UNSETTLED = "3D view: view Top, framed, +3 zoom steps (the 3D view hadn't settled within 3 s after it%s)"
CAUSES = ' (Renderer > Edit settings)'


@pytest.mark.parametrize(
    'said, named',
    [
        (UNSETTLED % ', its sample count at 2 when last drawn, below 8', True),  # left mid-accumulation off screen
        (UNSETTLED % '', False),  # no count
        (UNSETTLED % ', its sample count at 8', False),
        # with the antialiasing off no step reads a restart: the render's line says it (frames3d.py)
        (
            "3D render: the 3D view hadn't settled within 3 s after Designer's window came back on screen, its sample "
            'count at 1, below 8',
            True,
        ),
    ],
    ids=['a count last drawn lower', 'no count', 'at 8', "the render's line"],
)
def test_the_rasterizer_check_takes_any_count_below_8_said(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    said: str,
    named: bool,
) -> None:
    # REVIEW.md TST-681: off screen, a count last drawn while the window left mid-accumulation reads lower than the
    # case's own; requiring the case's count, a full run could fail the check at random
    before = 'RASTERIZER samples=8.0 aa=True before\n'
    replies = {
        'float(4.0)': before + 'RASTERIZER samples=4.0 aa=True after',
        'float(False)': before + 'RASTERIZER samples=8.0 aa=False after',
        'float(8.0)': 'RASTERIZER samples=8.0 aa=True after',
        'float(True)': 'RASTERIZER samples=8.0 aa=True after',
        'raster_samples_zoom': 'RENDER_COUNT 4\n' + said + CAUSES,
        'raster_aa_zoom': 'RENDER_COUNT 1\n' + said + CAUSES,
    }
    shots = Shots3d(monkeypatch, tmp_path, ZOOMED, replies)
    asyncio.run(getattr(shots.editor, RASTER_CHECK)(shots.ctx))
    verdicts = [line for line in capsys.readouterr().out.splitlines() if line.startswith(('PASS', 'FAIL'))]
    assert len(verdicts) == 2 and all(line.startswith('PASS' if named else 'FAIL') for line in verdicts), verdicts


def test_the_3d_checks_fake_touches_a_path_as_the_code_writes_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-689: the checks write paths with %r, which doubles a backslash; the fake matched them unescaped,
    # and on Windows touched no render. A folder holding a backslash shows it here
    folder = tmp_path / 'back\\slash'
    folder.mkdir(parents=True)  # two folders on Windows
    before = 'RASTERIZER samples=8.0 aa=True before\n'
    replies = {
        'float(4.0)': before + 'RASTERIZER samples=4.0 aa=True after',
        'float(False)': before + 'RASTERIZER samples=8.0 aa=False after',
        'float(8.0)': 'RASTERIZER samples=8.0 aa=True after',
        'float(True)': 'RASTERIZER samples=8.0 aa=True after',
    }
    shots = Shots3d(monkeypatch, folder, ZOOMED, replies)
    asyncio.run(getattr(shots.editor, RASTER_CHECK)(shots.ctx))
    verdicts = [line for line in capsys.readouterr().out.splitlines() if 'zoomed, the settings named' in line]
    assert len(verdicts) == 2 and not any('a shot failed' in line for line in verdicts), verdicts


@pytest.mark.parametrize(
    'printed, wrong',
    [
        ('[]', 'the whole: Input should be an object'),
        ('{"sbs::function::add": {"outputs": []}}', 'add.inputs: Field required'),
        ('{"sbs::function::add": {"inputs": [{"id": "a", "types": "float"}], "outputs": []}}', 'add.inputs.0.types'),
        ('{"sbs::function::add": {"inputs": [], "outputs": [{"types": []}]}}', 'add.outputs.0.id: Field required'),
        (
            '{"sbs::function::add": {"inputs": [{"id": "a", "types": [], "connectable": 1}], "outputs": []}}',
            'add.inputs.0.connectable',
        ),
    ],
)
def test_definitions_of_another_shape_fail_a_check_that_says_what_is_wrong(
    capsys: pytest.CaptureFixture[str], printed: str, wrong: str
) -> None:
    # REVIEW.md TST-699: the definitions' JSON was typed without a check, so another shape raised a KeyError or a
    # TypeError in a comprehension instead of failing a check that names it
    functions = fresh('functions.checks')

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        return tool_result('DEFINITIONS=' + printed)

    asyncio.run(functions.check_the_function_definitions(SimpleNamespace(c=c)))
    failed = [line for line in capsys.readouterr().out.splitlines() if line.startswith('FAIL')]
    assert any('the printed definitions have the shape the checks read' in line and wrong in line for line in failed), (
        failed
    )


ADD_TAKES = 'int,int2,int3,int4,float,float2,float3,float4'  # the table's types of add's inputs


@pytest.mark.parametrize(
    'changed, detail',
    [
        ({}, ''),
        ({'add': ('b', ['int', 'float'])}, 'add: input b: Designer int,float; the table %s' % ADD_TAKES),
        ({'add': ('b', ['int']), 'pow2': None}, 'add: input b: Designer int; the table %s; also pow2' % ADD_TAKES),
        ({'pow2': None}, 'pow2: not in Designer'),
    ],
)
def test_the_definitions_check_names_the_first_difference_in_short(
    capsys: pytest.CaptureFixture[str], changed: dict[str, tuple[str, list[str]] | None], detail: str
) -> None:
    # REVIEW.md TST-701: the detail printed both whole entries, which common.check cuts at 150 characters
    functions = fresh('functions.checks')
    printed = functions.compiler_table()
    for name, change in changed.items():
        if change is None:
            del printed[name]
        else:
            next(p for p in printed[name]['inputs'] if p['id'] == change[0])['types'] = change[1]

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        return tool_result('DEFINITIONS=' + json.dumps({'sbs::function::' + k: v for k, v in printed.items()}))

    asyncio.run(functions.check_the_function_definitions(SimpleNamespace(c=c)))
    line = next(l for l in capsys.readouterr().out.splitlines() if "gives the compiler's table" in l)
    assert line.startswith('FAIL' if changed else 'PASS'), line
    assert line.split(' | ', 1)[1] == detail


def test_the_timeout_check_commits_only_a_step_shown_open() -> None:
    # REVIEW.md TST-887: a commit only when the call's node is there and the Undo top unchanged, never into a Designer
    # whose top is a step of the user's
    checks = fresh('batch.checks')
    own, top = 'Claude: code' + TAG_PREFIX + 'a' * TAG_LENGTH, 'Claude: code' + TAG_PREFIX + 'b' * TAG_LENGTH
    assert checks.step_shown(own, top, 4, 4) == 'listed'
    assert checks.step_shown(top, top, 4, 4) == 'open'
    assert checks.step_shown('Add Atomic Node', top, 4, 4) == 'other'  # the user's step on top
    assert checks.step_shown(top, top, 3, 4) == 'other'  # the call's node isn't there
    assert checks.step_shown(own, top, 3, 4) == 'other'
