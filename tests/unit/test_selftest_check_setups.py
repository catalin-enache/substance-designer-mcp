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
from typing import NoReturn

import pytest
from selftest_fakes import Designer, FakeCall, code_of, fresh, tool_result

from project_constants import ToolArgs

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
    come from `widths` by file name (290 px otherwise), any two renders are 0.00 apart (a plain shot after one too),
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

        async def plain_after(call: FakeCall, source: str, path: str) -> tuple[str, float, str]:
            after = path.replace('.png', '_after.png')
            Path(after).touch()
            return after, 0.0, '3d render 4x3'

        def render(path: str) -> SimpleNamespace:
            return SimpleNamespace(path=path, shape=(362, 342))

        def width(a: SimpleNamespace) -> int:
            return widths.get(os.path.basename(a.path), 290)

        for name, value in {
            'with_checker': with_checker,
            'at_rest': at_rest,
            'plain_after': plain_after,
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


ZOOM_CHECK = 'check_wheel_steps_sent_as_designers_window_goes_off_screen_are_all_taken'
STOPPED = "3D view: +6 wheel steps (wheel step 3 of 6: no sign the 3D view took it within 3 s; the camera's moves stopped there)"
# a re-framing whose zoom stopped short (REVIEW.md TST-672)
REFRAMED = (
    "3D view: Plane, view Top, framed, -4 wheel steps (wheel step 2 of 4 not sent: the 3D view didn't come to rest)"
)
UNDRAWN = "3D render: the 3D view hadn't settled within 3 s after Designer's window came back on screen"


def test_a_failed_zoom_check_prints_the_tools_lines_and_the_plain_shot_after(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-664: a run failing with "the plane 1.69x" couldn't tell whether the tool stopped the zoom and said
    # why, or lost a step silently; the plain shot after it went unsaid
    mid = 'PAINTED_BEFORE_THE_HIDE True\nHIDDEN_AT_THE_FIRST_STEP exposed=False\n3D view, setting: +6 wheel steps\n'
    shots = Shots3d(
        monkeypatch,
        tmp_path,
        {'zoom_start.png': 154, 'hidden_mid_zoom.png': 261},
        {
            'PAINTED_BEFORE_THE_HIDE': mid + STOPPED + '\n' + UNDRAWN,
            'shoot_3d(': '3D view: +6 wheel steps',
            'screenshot_designer': REFRAMED,
        },
    )
    asyncio.run(getattr(shots.editor, ZOOM_CHECK)(shots.ctx))
    out = capsys.readouterr().out
    assert [line for line in out.splitlines() if line.startswith('FAIL')], out
    assert STOPPED in out and 'PAINTED_BEFORE_THE_HIDE True' in out, out
    # REVIEW.md TST-672: the re-framing's reply was dropped, and the tool's "3D render:" lines weren't printed
    assert REFRAMED in out and UNDRAWN in out, out
    renders = [path for given in shots.said for _, path in given]
    assert any(path.endswith('hidden_mid_zoom_after.png') for path in renders), renders


def test_the_zoom_check_fails_when_the_checker_never_showed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-666: compared on a plain plane, an unsettled render reads 0.00 (HLP-210), and the check passed blind
    shots = Shots3d(monkeypatch, tmp_path, {'zoom_start.png': 154}, {}, checker=False)
    asyncio.run(getattr(shots.editor, ZOOM_CHECK)(shots.ctx))
    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith(('PASS', 'FAIL'))]
    assert len(lines) == 3 and all(line.startswith('FAIL') and 'checker' in line for line in lines), lines
    assert shots.calls == ['with_checker', 'execute_designer_code'], 'the start rendered, no zoom'


def test_a_failed_wheel_facts_check_says_which_event_differed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-665: the events' detail is 165 characters, cut at 150: a differing 14th event looked like a passing
    # list cut short
    rest = 'AT_REST_BEFORE_THE_NOTCHES True\nHIDDEN_BEFORE_THE_NOTCHES exposed=False\n'
    events = {
        'wheel_one_shown': rest + 'SENT True/False',
        'wheel_back_shown': rest + '\n'.join(['SENT True/False'] * 6),
        'wheel_one_hidden': rest + 'SENT True/False',
        'wheel_back_hidden': rest + '\n'.join(['SENT True/False'] * 5 + ['SENT True/True']),
        'wheel_apart': rest + 'STOPPED None',
        'screenshot_designer': REFRAMED,  # each re-framing between the cases (REVIEW.md TST-672)
    }
    widths = {'wheel_start.png': 154, 'wheel_apart_shown.png': 290, 'wheel_apart_hidden.png': 290}
    widths |= {'wheel_%s_%s.png' % (mode, where): 172 for mode in ('one', 'back') for where in ('shown', 'hidden')}
    shots = Shots3d(monkeypatch, tmp_path, widths, events)
    asyncio.run(shots.editor.check_the_3d_views_wheel_takes_one_notch_an_event_and_drops_those_back_to_back(shots.ctx))
    out = capsys.readouterr().out
    line = next(line for line in out.splitlines() if 'isAccepted() False' in line)
    assert line.startswith('FAIL') and 'True/True' in line, line
    assert 'back, hidden' in line, line
    assert REFRAMED in out, out
    back = next(line for line in out.splitlines() if 'the shot stopped:' in line)
    assert back.endswith('; looks 0'), back  # TST-684: the shot's looks in 'apart'


def test_the_shown_already_checks_count_of_waits_keeps_each_waits_result() -> None:
    # REVIEW.md TST-678: the wrapper counting the settles returned None, read as unsettled since HLP-214: a failing
    # run's "hadn't settled" lines weren't so
    editor = fresh('editor_panels_and_fit.checks')
    results: list[object] = []

    class Frames:
        def settled(self, since: str) -> bool:
            return since == 'back at rest'

    def shoot_3d(path: str, **shown: object) -> None:
        if path.endswith('again.png'):  # the shot whose waits are counted
            results.extend(Frames().settled(since) for since in ('back at rest', 'its net reached'))

    def set_3d_view(**options: object) -> None:  # the environment reset after
        pass

    exec(
        editor.SHOWN_ALREADY % ('/folder', 'studio'),
        {'_Frames': Frames, 'shoot_3d': shoot_3d, 'set_3d_view': set_3d_view},
    )
    assert results == [True, False]


RASTER_CHECK = 'check_an_on_screen_3d_zoom_held_below_8_samples_is_refused_naming_the_rasterizers_settings'


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
        ('RASTERIZER samples=8.0 aa=True after (the Parameters panel back on g)',) * 2 + ([],),  # put back
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
        'float(4.0)': before + 'RASTERIZER samples=4.0 aa=True after (the Parameters panel back on g)',
        'float(False)': before + 'RASTERIZER samples=8.0 aa=False after (the Parameters panel back on g)',
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


STOP = "3D view: +3 wheel steps (wheel step 1 of 3 not sent: the 3D view didn't come to rest within %s s%s; the camera's moves stopped there)"
CAUSES = ' (Renderer > Edit settings)'


@pytest.mark.parametrize(
    'waited, stopped, refused',
    [
        ('3', ', its sample count at 2 when last drawn, below 8', True),  # left mid-accumulation off screen: below 8
        ('3', '', False),  # no count
        ('3', ', its sample count at 8', False),
        # REVIEW.md HLP-219: the time the rest waited, its looks again included (HLP-218), not always 3 s
        ('6.1', ', its sample count at 4, below 8', True),
    ],
    ids=['a count last drawn lower', 'no count', 'at 8', 'a rest that waited 6.1 s'],
)
def test_the_rasterizer_checks_refusal_takes_any_count_below_8(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    waited: str,
    stopped: str,
    refused: bool,
) -> None:
    # REVIEW.md TST-681: off screen, a count last drawn while the window left mid-accumulation reads lower than the
    # case's own; the refusal required the case's count, so a full run could fail it at random
    before = 'RASTERIZER samples=8.0 aa=True before\n'
    replies = {
        'float(4.0)': before + 'RASTERIZER samples=4.0 aa=True after',
        'float(False)': before + 'RASTERIZER samples=8.0 aa=False after',
        'float(8.0)': 'RASTERIZER samples=8.0 aa=True after',
        'float(True)': 'RASTERIZER samples=8.0 aa=True after',
        'raster_samples_zoom': 'RENDER_COUNT 4\n' + STOP % (waited, stopped) + CAUSES,
        'raster_aa_zoom': 'RENDER_COUNT 1\n' + STOP % (waited, stopped) + CAUSES,
    }
    shots = Shots3d(monkeypatch, tmp_path, {}, replies)
    asyncio.run(getattr(shots.editor, RASTER_CHECK)(shots.ctx))
    verdicts = [line for line in capsys.readouterr().out.splitlines() if line.startswith(('PASS', 'FAIL'))]
    assert len(verdicts) == 2 and all(line.startswith('PASS' if refused else 'FAIL') for line in verdicts), verdicts


LOOKED = "Designer's window: shown again, transparent, as Designer was hidden during the shot"  # _bring's line, a look


def test_the_zoom_check_says_how_many_looks_each_shot_made(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-684: a wheel step's rest may make the shot's look again (HLP-218); a tool that now looked every time
    # would pass unseen. Said after the plane's figures, within the 150 characters check() keeps
    # two looks, and a line of the window's that is no look (shot3d.py: Designer made the active app)
    opaque = "Designer's window: made opaque at once, as Designer became the active app during the shot"
    mid = (
        'PAINTED_BEFORE_THE_HIDE True\nHIDDEN_AT_THE_FIRST_STEP exposed=False\n%s\n%s\n%s\n3D view: +6 wheel steps'
        % (
            LOOKED,
            opaque,
            LOOKED,
        )
    )
    shots = Shots3d(
        monkeypatch,
        tmp_path,
        {'zoom_start.png': 154},
        {'PAINTED_BEFORE_THE_HIDE': mid, 'HIDDEN_BEFORE': LOOKED + '\n3D view: +6 wheel steps'},
    )
    asyncio.run(getattr(shots.editor, ZOOM_CHECK)(shots.ctx))
    verdicts = [line for line in capsys.readouterr().out.splitlines() if line.startswith(('PASS', 'FAIL'))]
    assert len(verdicts) == 3, verdicts
    assert verdicts[0].endswith('looks 0'), verdicts[0]  # the undisturbed zoom, on screen throughout
    assert verdicts[1].endswith('looks 2') and verdicts[2].endswith('looks 1'), verdicts


def test_the_zoom_checks_longest_detail_keeps_its_looks(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # TST-684: the looks come last; the longest detail (the plane clipped, both differences 12.34, the case not
    # forced, 10 looks) must still fit the 150 characters check() keeps
    shots = Shots3d(monkeypatch, tmp_path, {}, {'HIDDEN_BEFORE': '\n'.join([LOOKED] * 10)})
    monkeypatch.setitem(vars(shots.editor), 'plane_columns', lambda a: (0, 341))
    monkeypatch.setitem(vars(shots.editor), 'difference', lambda a, b: 12.34)

    async def plain_after(call: FakeCall, source: str, path: str) -> tuple[str, float, str]:
        return path.replace('.png', '_after.png'), 12.34, '3d render 4x3'

    monkeypatch.setitem(vars(shots.editor), 'plain_after', plain_after)
    asyncio.run(getattr(shots.editor, ZOOM_CHECK)(shots.ctx))
    line = next(line for line in capsys.readouterr().out.splitlines() if 'from the first are all taken' in line)
    assert line.endswith('; looks 10'), line


def test_the_zoom_check_says_what_its_plain_shot_after_said_when_it_saved_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-688: plain_after dropped its shot's reply, and the undisturbed zoom's settled FAIL gave no line
    failed = "RuntimeError: the 3D view isn't drawn: Designer's window isn't on screen 3 s after it was shown again"
    shots = Shots3d(monkeypatch, tmp_path, {'zoom_start.png': 154}, {})

    async def plain_after(call: FakeCall, source: str, path: str) -> tuple[str, float, str]:
        return path.replace('.png', '_after.png'), 255.0, failed  # nothing saved

    monkeypatch.setitem(vars(shots.editor), 'plain_after', plain_after)
    asyncio.run(getattr(shots.editor, ZOOM_CHECK)(shots.ctx))
    out = capsys.readouterr().out
    verdicts = [line for line in out.splitlines() if line.startswith(('PASS', 'FAIL'))]
    assert len(verdicts) == 3 and all(line.startswith('FAIL') for line in verdicts), verdicts
    assert out.count('      a plain shot after, the tool said: ' + failed) == 3, out


def test_the_3d_checks_fake_touches_a_path_as_the_code_writes_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-689: the checks write paths with %r, which doubles a backslash; the fake matched them unescaped,
    # and on Windows touched no render. A folder holding a backslash shows it here
    folder = tmp_path / 'back\\slash'
    folder.mkdir(parents=True)  # two folders on Windows
    shots = Shots3d(monkeypatch, folder, {'zoom_start.png': 154}, {})
    asyncio.run(getattr(shots.editor, ZOOM_CHECK)(shots.ctx))
    verdicts = [line for line in capsys.readouterr().out.splitlines() if line.startswith(('PASS', 'FAIL'))]
    assert verdicts and not any('no checker on the plane at the start' in line for line in verdicts), verdicts


def test_the_undisturbed_zooms_failure_says_its_shots_and_their_renders_when_both_saved(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # REVIEW.md TST-692: the settled FAIL said only a shot that saved nothing; the plain shot after, rendered at its
    # look's limit, read as the zoom's own failure
    shots = Shots3d(monkeypatch, tmp_path, {'zoom_start.png': 154}, {})
    undisturbed, after = str(tmp_path / 'undisturbed_zoom.png'), str(tmp_path / 'undisturbed_zoom_after.png')

    async def plain_after(call: FakeCall, source: str, path: str) -> tuple[str, float, str]:
        later = path.replace('.png', '_after.png')
        Path(later).touch()
        return later, 1.5, '3d render 4x3\n' + UNDRAWN

    monkeypatch.setitem(vars(shots.editor), 'plain_after', plain_after)
    asyncio.run(getattr(shots.editor, ZOOM_CHECK)(shots.ctx))
    out = capsys.readouterr().out.splitlines()
    settled = next(i for i, line in enumerate(out) if 'the render is of the view at rest' in line)
    assert out[settled].startswith('FAIL')
    assert '      a plain shot after, the tool said: ' + UNDRAWN in out[settled + 1 : settled + 4], out
    assert shots.said[0] == (('undisturbed', undisturbed), ('a plain shot after', after)), shots.said


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
