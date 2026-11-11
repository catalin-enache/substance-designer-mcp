"""What live checks do with the answers they get, on fakes: a capture ending on the client's side first (REVIEW.md
TST-256), a view not visible in a Designer the self-test started (TST-258), the state a check is about not reached
(TST-259). The checks themselves run against the real Designer: this is what a run that passes can't show."""

import asyncio
import sys
from collections.abc import Callable, Coroutine
from types import SimpleNamespace
from typing import Any

import pytest
from selftest_fakes import fresh

NOT_VISIBLE = 'the 3D View panel is not visible in Designer'


def _said(t: str, error: bool = False) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type='text', text=t)], is_error=error)


def _image() -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type='image', data='')], is_error=False)


def _common() -> Any:
    return sys.modules['test_all_tools.common']


def _clipboard(monkeypatch: pytest.MonkeyPatch, editor: Any, held: bytes) -> tuple[list[bytes], list[bytes]]:
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

    async def c(name: str, args: dict[str, Any] | None = None) -> Any:
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

    async def c(name: str, args: dict[str, Any] | None = None) -> Any:
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

    async def c(tool: str, args: dict[str, Any] | None = None) -> Any:
        return _said(NOT_VISIBLE, True)

    asyncio.run(getattr(editor, name)(SimpleNamespace(c=c, was_running=was_running)))
    assert bool(_common().skipped) == was_running
    assert (False in _common().results['screenshot_designer']) != was_running


def _measure_designer(calls: list[str], broken: str = '') -> Callable[..., Coroutine[Any, Any, Any]]:
    """The answers of check_a_node_measured_right_after_the_one_feeding_it; `broken`: the setup call that fails."""

    async def c(name: str, args: dict[str, Any] | None = None) -> Any:
        calls.append(name)
        args = args or {}
        if name == 'open_graph':
            return _said('no such graph', True) if broken == 'open_graph' else _said('opened g')
        if name == 'apply_edits':
            return _said("added 9\n  ref 'up' = 1\n  ref 'down' = 2\n")
        if name == 'node_stats' and args['node_id'] == '1' and broken == 'upstream':
            return _said('the node computed nothing', True)
        if name == 'node_stats':
            return _said('pixel (0,0) = 0\npixel (256,256) = 0')
        if name == 'execute_designer_code':
            return _said('TEXTURE=True')
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
