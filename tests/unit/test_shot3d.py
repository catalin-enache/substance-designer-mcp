"""The helpers' side of screenshot_designer('3d') (designer_helpers/shot3d.py), with sd and PySide6 faked: Designer's
window put on screen for the shot, again before each render, and put back after (REVIEW.md SRV-146, HLP-124 to
HLP-126), and a render identical to the one before a set-up that moved the camera or switched the mesh taken again,
then said. The live self-test checks Designer itself (editor_panels_and_fit)."""

import contextlib
import sys
import types
from collections.abc import Callable, Iterator
from types import SimpleNamespace

import pytest


class Mac:
    """_MacWindow, faked: how macOS sees Designer's window, the window in front of it while it is covered, the windows
    no longer on screen, whether Designer is the active app, and what was done to the window, in order."""

    def __init__(
        self,
        minimized: bool = False,
        hidden: bool = False,
        covered: bool = False,
        above: int | None = 7,
        active: bool = False,
    ) -> None:
        self.state = {'minimized': minimized, 'hidden': hidden, 'covered': covered}
        self.window_above = above
        self.gone: set[int] = set()  # closed or minimized: not on screen
        self.is_active = active
        self.done: list[str] = []

    def minimized(self) -> bool:
        return self.state['minimized']

    def hidden(self) -> bool:
        return self.state['hidden']

    def covered(self) -> bool:  # no part on screen: minimized or hidden too, as macOS says (REVIEW.md TST-397)
        return any(self.state.values())

    def active(self) -> bool:
        return self.is_active

    def above(self) -> int | None:  # the window directly in front of it, while one is
        return self.window_above if self.covered() else None

    def on_screen(self, number: int) -> bool:
        return number not in self.gone

    def show(self) -> None:  # in front, without taking focus: un-minimized and uncovered too
        self.done.append('show')
        self.state.update(minimized=False, covered=False)

    def unhide(self) -> None:
        self.done.append('unhide')
        self.state['hidden'] = False

    def hide(self) -> None:
        self.done.append('hide')
        self.state['hidden'] = True

    def put_below(self, number: int) -> None:
        self.done.append('put below %d' % number)
        self.state['covered'] = True


class Window:
    """Designer's main window as Qt sees it: minimized only when Qt itself minimized it, exposed while macOS shows it
    (never, with `shows` False)."""

    def __init__(self, mac: Mac, qt_minimized: bool = False, shows: bool = True) -> None:
        self.mac = mac
        self.qt_minimized = qt_minimized
        self.shows = shows

    def isMinimized(self) -> bool:
        return self.qt_minimized

    def windowState(self) -> int:
        return 1

    def setWindowState(self, state: object) -> None:
        self.mac.done.append('qt restore')
        self.qt_minimized = False

    def windowHandle(self) -> SimpleNamespace:
        return SimpleNamespace(isExposed=lambda: self.shows and not any(self.mac.state.values()))


@pytest.fixture
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    module = faked_helpers
    vars(module)['_settle'] = lambda seconds: None
    return module


def _on(helpers: types.ModuleType, mac: Mac | None) -> None:
    vars(helpers)['_mac_window'] = lambda mw: mac


FRONT = "Designer's window: brought in front without taking focus, as its 3D view isn't drawn while covered"
PUT_BACK = "Designer's window: put back behind the window that was in front of it"
SHOWN = "Designer's window: shown without taking focus, as its 3D view isn't drawn while Designer is hidden"
HIDDEN = "Designer's window: hidden again"
UNMINIMIZED = "Designer's window: un-minimized, as its 3D view isn't drawn while minimized; it stays so"
LEFT = "Designer's window: left on screen, as Designer became the active app during the shot"
GONE = "Designer's window: left in front, as the window that was in front of it is no longer on screen"
NONE_IN_FRONT = "Designer's window: left in front, as no window was found in front of it"


def test_a_window_on_screen_is_left_as_it_is(helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    mac = Mac()
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['shot'] and capsys.readouterr().out == ''


def test_a_minimized_window_is_shown_without_focus_and_stays_so(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # the user's choice (DECISIONS.md): Qt doesn't see macOS minimize it, so macOS is asked
    mac = Mac(minimized=True)
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['show', 'shot']
    assert capsys.readouterr().out.splitlines() == [UNMINIMIZED]


def test_a_window_qt_minimized_is_restored_by_qt_too(helpers: types.ModuleType) -> None:
    # Designer's renderer follows the Qt state of getMainWindow(), a page: stale though macOS shows it (REVIEW.md TST-391)
    mac = Mac()
    _on(helpers, mac)
    with helpers._on_screen(Window(mac, qt_minimized=True)):
        mac.done.append('shot')
    assert mac.done == ['qt restore', 'show', 'shot']


def test_a_covered_window_is_brought_in_front_without_focus_and_put_back_behind_the_window_in_front_of_it(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-126: right behind the window that was in front of it, not behind every window
    mac = Mac(covered=True, above=7)
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['show', 'shot', 'put below 7']
    assert capsys.readouterr().out.splitlines() == [FRONT, PUT_BACK]


def test_a_covered_window_with_no_window_found_in_front_is_left_in_front(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-130: no normal window in front of it (an always-on-top window covered it): sending it to the back
    # would put the front-most normal window behind every window
    mac = Mac(covered=True, above=None)
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['show', 'shot']
    assert capsys.readouterr().out.splitlines() == [FRONT, NONE_IN_FRONT]


def test_a_covered_window_whose_window_in_front_went_off_screen_is_left_in_front(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-130: the user closed or minimized it during the shot; put behind it, Designer's window would go
    # behind every window (measured: mac_window.py)
    mac = Mac(covered=True, above=7)
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)):
        mac.done.append('shot')
        mac.gone.add(7)
    assert mac.done == ['show', 'shot']
    assert capsys.readouterr().out.splitlines() == [FRONT, GONE]


class Abort(BaseException):
    """The plugin's abort (ScriptAborted), raised where a cancel lands."""


def test_an_abort_while_the_window_in_front_is_looked_for_leaves_nothing_to_put_back(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-130: the window wasn't moved yet, so nothing is put back and nothing said of it
    mac = Mac(covered=True)

    def aborted() -> int | None:
        raise Abort

    vars(mac)['above'] = aborted
    _on(helpers, mac)
    with pytest.raises(Abort), helpers._on_screen(Window(mac)):
        mac.done.append('shot')
    assert mac.done == []
    assert capsys.readouterr().out.splitlines() == [FRONT]


def test_a_window_covered_again_during_the_shot_goes_back_behind_the_window_that_covered_it_first(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-131: the user's click on another window during the shot leaves that one in front, and Designer's
    # behind the window that covered it before
    mac = Mac(covered=True, above=7)
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)) as screen:
        mac.state['covered'], mac.window_above = True, 9
        screen.again()
    assert mac.done == ['show', 'show', 'put below 7']
    assert capsys.readouterr().out.splitlines()[-1] == PUT_BACK


def test_a_window_covered_again_after_its_first_cover_went_off_screen_goes_back_behind_the_later_one(
    helpers: types.ModuleType,
) -> None:
    mac = Mac(covered=True, above=7)
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)) as screen:
        mac.gone.add(7)
        mac.state['covered'], mac.window_above = True, 9
        screen.again()
    assert mac.done == ['show', 'show', 'put below 9']


def test_a_hidden_designer_is_shown_without_focus_and_hidden_again_after(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    mac = Mac(hidden=True)
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['unhide', 'show', 'shot', 'hide']
    assert capsys.readouterr().out.splitlines() == [SHOWN, HIDDEN]


def test_a_minimized_window_of_a_hidden_designer_is_shown_and_designer_hidden_again(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-393: both at once; the window stays un-minimized, inside the hidden app
    mac = Mac(minimized=True, hidden=True)
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['unhide', 'show', 'shot', 'hide']
    assert capsys.readouterr().out.splitlines() == [UNMINIMIZED, HIDDEN]


def test_the_view_is_given_time_to_draw_once_the_window_is_on_screen(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-393: a render at once may still be the last frame
    mac = Mac(minimized=True)
    _on(helpers, mac)
    vars(helpers)['_settle'] = lambda seconds: mac.done.append('wait %g' % seconds)
    with helpers._on_screen(Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['show', 'wait %g' % helpers.DRAW_WAIT, 'shot']


def test_a_window_still_not_on_screen_is_refused_and_put_back(helpers: types.ModuleType) -> None:
    mac = Mac(covered=True)
    _on(helpers, mac)
    refused = pytest.raises(RuntimeError, match=r"the 3D view isn't drawn: Designer's window isn't on screen")
    with refused, helpers._on_screen(Window(mac, shows=False)):
        mac.done.append('shot')
    assert mac.done == ['show', 'put below 7']


def test_a_shot_that_fails_still_puts_the_window_back(helpers: types.ModuleType) -> None:
    mac = Mac(hidden=True)
    _on(helpers, mac)
    with pytest.raises(RuntimeError, match='the render failed'), helpers._on_screen(Window(mac)):
        raise RuntimeError('the render failed')
    assert mac.done == ['unhide', 'show', 'hide']


@pytest.mark.parametrize(
    'off, done, said',
    [
        (
            'covered',
            ['shot', 'show', 'put below 9'],
            "Designer's window: brought in front again without taking focus, as another window covered it during the "
            'shot',
        ),
        (
            'minimized',
            ['shot', 'show'],
            "Designer's window: un-minimized again, as it was minimized during the shot; it stays so",
        ),
        (
            'hidden',
            ['shot', 'unhide', 'show', 'hide'],
            "Designer's window: shown again without taking focus, as Designer was hidden during the shot",
        ),
    ],
)
def test_a_window_put_off_screen_during_the_shot_is_put_on_screen_again(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], off: str, done: list[str], said: str
) -> None:
    # REVIEW.md HLP-124: the user clicked their own window back in front while the shot ran, or minimized or hid Designer
    mac = Mac(above=9)
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)) as screen:
        mac.done.append('shot')
        mac.state[off] = True
        screen.again()
    assert mac.done == done
    assert capsys.readouterr().out.splitlines()[0] == said


def test_a_window_on_screen_is_left_as_it_is_when_looked_at_again(helpers: types.ModuleType) -> None:
    mac = Mac()
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)) as screen:
        screen.again()
    assert mac.done == []


@pytest.mark.parametrize('off, done', [('hidden', ['unhide', 'show']), ('covered', ['show'])])
def test_a_designer_the_user_made_the_active_app_during_the_shot_is_left_on_screen(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], off: str, done: list[str]
) -> None:
    # REVIEW.md HLP-125: the user clicked into the window that came up: hiding it, or sending it back, takes it away
    mac = Mac(**{off: True})
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)):
        mac.is_active = True
    assert mac.done == done
    assert capsys.readouterr().out.splitlines()[-1] == LEFT


def test_a_window_covered_while_designer_was_already_the_active_app_is_put_back(helpers: types.ModuleType) -> None:
    # one of Designer's own windows over it, Designer in front: the user didn't take it up during the shot
    mac = Mac(covered=True, active=True)
    _on(helpers, mac)
    with helpers._on_screen(Window(mac)):
        mac.done.append('shot')
    assert mac.done == ['show', 'shot', 'put below 7']


def test_off_macos_the_window_is_left_as_it_is(helpers: types.ModuleType) -> None:
    # not measured elsewhere: the shot is taken as before
    mac = Mac()
    _on(helpers, None)
    with helpers._on_screen(Window(mac, qt_minimized=True)) as screen:
        mac.done.append('shot')
        screen.again()
    assert mac.done == ['shot']


def test_designers_window_is_asked_of_macos_only_on_macos(
    helpers: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md TST-393: elsewhere the Objective-C runtime isn't there to ask
    monkeypatch.setattr(sys, 'platform', 'win32')
    assert helpers._mac_window(object()) is None


class Render:
    """A 3D render (a QImage): equal to another of the same name, as QImage compares pixels."""

    def __init__(self, name: str, saved: list[str]) -> None:
        self.name = name
        self._saved = saved

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Render) and other.name == self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def save(self, path: str) -> bool:
        self._saved.append('%s to %s' % (self.name, path))
        return True

    def width(self) -> int:
        return 4

    def height(self) -> int:
        return 3


class Shot:
    """shoot_3d's Designer, faked: the renders it gives in turn (the last one again once they run out), the mesh shown,
    and what happened, in order. The set-up's checks are the real argument checks (_set_up_checked); `refused` is
    raised by the rest of them."""

    def __init__(
        self, helpers: types.ModuleType, *renders: str, mesh: str = 'Plane', refused: str | None = None
    ) -> None:
        self.events: list[str] = []
        self.saved: list[str] = []
        renders_left = [Render(name, self.saved) for name in renders]
        checked = vars(helpers)['_set_up_checked']

        def render(mw: object) -> Render:
            r = renders_left.pop(0) if len(renders_left) > 1 else renders_left[0]
            self.events.append('render ' + r.name)
            return r

        @contextlib.contextmanager
        def on_screen(mw: object) -> Iterator[SimpleNamespace]:
            self.events.append('on screen')
            yield SimpleNamespace(again=lambda: self.events.append('again'))
            self.events.append('put back')

        def set_up(*args: object) -> Callable[[], None]:
            checked(*args[:3])
            if refused:
                raise RuntimeError(refused)
            return lambda: self.events.append('set up %r' % (args,))

        vars(helpers)['_3d_render'] = render
        vars(helpers)['_on_screen'] = on_screen
        vars(helpers)['_3d_dock'] = lambda mw: object()
        vars(helpers)['_mesh_shown'] = lambda mw, keep: mesh
        vars(helpers)['_3d_set_up'] = set_up
        vars(helpers)['_settle'] = lambda seconds: self.events.append('wait %g' % seconds)
        vars(helpers)['find_graph'] = lambda name: SimpleNamespace(
            getIdentifier=lambda: name, getOutputNodes=lambda: [object()] * (1 if name == 'one' else 2)
        )


STALE = (
    '3D render: identical to the render before the set-up, though the set-up moved the camera or switched the mesh. '
    'The 3D view may not have been drawn. Shoot again with no set-up before judging it: pan, orbit and zoom move the '
    'camera from where it is. With no mesh in view, a pan or zoom changes nothing'
)


def test_a_render_identical_after_a_pan_is_taken_again_until_it_differs(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    shot = Shot(helpers, 'A', 'A', 'A', 'B')
    helpers.shoot_3d('out.png', pan=[0.25, 0.0])
    wait = 'wait %g' % helpers.DRAW_WAIT
    assert shot.events == [
        'on screen',
        'again',
        'render A',  # before the set-up
        'set up (None, None, None, 0, None, None, [0.25, 0.0])',
        'again',
        'render A',
        wait,
        'again',
        'render A',
        wait,
        'again',
        'render B',
        'put back',
    ]
    assert shot.saved == ['B to out.png']
    assert capsys.readouterr().out.splitlines() == ["3d render 4x3 (the clipboard's text put back)"]


def test_a_render_still_identical_after_the_retakes_is_said(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-128: a set-up sent again would move the camera again
    shot = Shot(helpers, 'A')
    helpers.shoot_3d('out.png', orbit=[90.0, 0.0])
    assert shot.events.count('render A') == 2 + helpers.RETAKES
    assert shot.saved == ['A to out.png']
    assert capsys.readouterr().out.splitlines()[-1] == STALE


@pytest.mark.parametrize(
    'options',
    [{'zoom': 2}, {'pan': [0.0, 0.1]}, {'orbit': [0.0, -5.0]}, {'mesh': 'Sphere'}],
    ids=['zoom', 'pan', 'orbit', 'another mesh'],
)
def test_a_set_up_that_moves_the_camera_or_switches_the_mesh_is_compared(
    helpers: types.ModuleType, options: dict[str, object]
) -> None:
    shot = Shot(helpers, 'A', 'B')
    helpers.shoot_3d('out.png', **options)
    assert shot.events[2] == 'render A' and shot.saved == ['B to out.png']


@pytest.mark.parametrize(
    'options',
    [{'graph': 'g'}, {'view': 'Top'}, {'tiling': 2.0}, {'mesh': 'Plane'}, {}],
    ids=['graph', 'view', 'tiling', 'the mesh shown', 'nothing'],
)
def test_a_shot_that_needs_no_comparison_takes_one_render(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], options: dict[str, object]
) -> None:
    # a view or a graph may be what is shown already: an identical render is no sign of a stale one
    shot = Shot(helpers, 'A')
    helpers.shoot_3d('out.png', **options)
    assert [e for e in shot.events if e.startswith('render')] == ['render A']
    assert not [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D render: ')]


def test_without_options_nothing_is_set_up(helpers: types.ModuleType) -> None:
    shot = Shot(helpers, 'A')
    helpers.shoot_3d('out.png')
    assert shot.events == ['on screen', 'again', 'render A', 'put back']


@pytest.mark.parametrize(
    'options, said',
    [
        ({'mesh': 'Teapot'}, "unknown mesh 'Teapot'"),
        ({'view': 'Diagonal'}, "unknown view 'Diagonal'"),
        ({'graph': 'one'}, 'graph one has one output'),
    ],
)
def test_a_set_up_refused_doesnt_touch_the_window(
    helpers: types.ModuleType, options: dict[str, object], said: str
) -> None:
    # refused before anything changes, the user's window included
    shot = Shot(helpers, 'A')
    with pytest.raises(RuntimeError, match=said):
        helpers.shoot_3d('out.png', **options)
    assert shot.events == []


def test_a_set_up_refused_by_what_designer_shows_doesnt_touch_the_window(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-127: set_3d_view's own checks (an orbit of less than a pixel, a panel not shown...) come first too
    refused = "orbit's 0.2 degrees right is less than one pixel's drag, 0.45 degrees: it would do nothing"
    shot = Shot(helpers, 'A', refused=refused)
    with pytest.raises(RuntimeError, match='less than one pixel'):
        helpers.shoot_3d('out.png', orbit=[0.2, 0.0])
    assert shot.events == []


def test_a_3d_view_not_shown_is_refused_before_the_window_changes(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-393: the docstring's promise
    shot = Shot(helpers, 'A')

    def not_shown(mw: object) -> object:
        raise RuntimeError('the 3D View panel is not visible')

    vars(helpers)['_3d_dock'] = not_shown
    with pytest.raises(RuntimeError, match='3D View panel is not visible'):
        helpers.shoot_3d('out.png')
    assert shot.events == []
