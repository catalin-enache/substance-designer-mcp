"""The helpers' side of screenshot_designer('3d', ...) (designer_helpers/view3d.py and scene3d.py), with sd and
PySide6 faked: what is checked before anything changes, what an error says was set, the graph's row found before its
context menu opens there, what the timers do while that menu runs, and the set-up through the 3D view's state file:
the camera, the mesh, the tiling and the environment written in one load and put back with the user's view, the
backup, and the relinks. The live self-test checks the 3D view itself (editor_panels_and_fit, facts)."""

import math
import os
import shutil
import sys
import types
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Literal, NoReturn, cast
from unittest import mock

import pytest

from conftest import FIXTURES, View3dOptions, with_added_material

if TYPE_CHECKING:  # for the checker only: the types the faked helpers take; sd and PySide6 are faked at run time
    from PySide6 import QtCore, QtGui, QtWidgets
    from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph

    from designer_helpers.core import Kept
    from designer_helpers.state3d import Pose

SAVED = Path(FIXTURES, 'state_file.sbsscn').read_text(encoding='utf-8')  # a state file a fresh Designer saved
USERS = SAVED.replace('<id>Rounded Cube</id>', '<id>file:///Users/u/box.fbx</id>')  # a mesh of the user's own, by URL


class MenuWindow:
    """_MacWindow of a menu, faked: what was done to the menu's own window, in the menu's `native`."""

    def __init__(self, menu: 'Menu') -> None:
        self.menu = menu

    def windows(self, every: bool) -> list[int]:
        return [7]

    def hold(self, window: int) -> None:
        self.menu.native.append('hold')

    def set_appearance(self, window: int, opacity: float, through: bool) -> None:
        self.menu.native.append('look %g %s' % (opacity, through))

    def let_go(self, window: int) -> None:
        self.menu.native.append('let go')


@pytest.fixture
def helpers(faked_helpers: types.ModuleType, tmp_path: Path) -> types.ModuleType:
    """The helpers faked, Designer's version folder in `tmp_path` (`16.0`), where its state file goes."""
    module = faked_helpers
    vars(module)['_process_events'] = lambda n=10: None
    vars(module)['_settle'] = lambda seconds: None
    vars(module)['_MacWindow'] = MenuWindow
    os.makedirs(tmp_path / '16.0')
    vars(module)['_version_folder'] = lambda: str(tmp_path / '16.0')
    return module


def qt(name: str) -> mock.MagicMock:
    """The faked PySide6 module `name` (QtCore, QtWidgets...), as the helpers import it: an attribute of the one fake
    every sd and PySide6 module is (conftest)."""
    return cast(mock.MagicMock, getattr(sys.modules['PySide6'], name))


class Index:
    """A model index: a parent chain ending at an invalid root."""

    def __init__(self, parent: 'Index | None' = None) -> None:
        self._parent = parent

    def parent(self) -> 'Index':
        return self._parent if self._parent is not None else Index.ROOT

    def isValid(self) -> bool:
        return self is not Index.ROOT

    ROOT: 'Index'


Index.ROOT = Index()


def _tree(row: Index, under: Index | None = None, inside: bool = True) -> SimpleNamespace:
    """The Explorer's tree: `under` is the row its point falls on (row by default), `inside` whether that point is in
    view. The row's point is only in view once scrolled to."""
    point = SimpleNamespace(name='the middle of the row')
    away = SimpleNamespace(name='out of view, not scrolled to')
    tree = SimpleNamespace(scrolled=[])
    tree.scrollTo = tree.scrolled.append
    tree.visualRect = lambda index: SimpleNamespace(center=lambda: point if index in tree.scrolled else away)
    tree.viewport = lambda: SimpleNamespace(rect=lambda: SimpleNamespace(contains=lambda at: inside and at is point))
    tree.indexAt = lambda at: row if under is None else under
    tree.point = point
    return tree


def test_a_graphs_row_is_scrolled_into_view_before_its_point_is_read(helpers: types.ModuleType) -> None:
    row = Index(Index())
    tree = _tree(row)
    assert helpers._row_point(tree, row, 'g') is tree.point
    assert tree.scrolled == [row]


@pytest.mark.parametrize('under, inside', [(Index(), True), (None, False)], ids=['another row there', 'out of view'])
def test_a_point_that_isnt_on_the_graphs_row_is_refused(
    helpers: types.ModuleType, under: Index | None, inside: bool
) -> None:
    # the menu opens for the row under the point: another graph's outputs would go on the mesh
    row = Index(Index())
    with pytest.raises(RuntimeError, match="graph g's row isn't showing in the Explorer"):
        helpers._row_point(_tree(row, under, inside), row, 'g')


class Menu:
    """The Explorer's context menu. `closed_as_faded`: something else closes it as the fade makes it transparent, before
    its action is picked (the live check does so: popups.closed_early)."""

    def __init__(
        self, *texts: str, disabled: tuple[str, ...] = (), raising: bool = False, closed_as_faded: bool = False
    ) -> None:
        self.triggered: list[str] = []
        self.closed = False
        self.closed_as_faded = closed_as_faded
        self.opacity_at_trigger: float | None = None
        self.opacity: float | None = None  # what setWindowOpacity set last
        self.opacities: list[float] = []  # each opacity setWindowOpacity set, in order
        self.native: list[str] = []  # what was done to its own window through _MacWindow (MenuWindow)
        self.flags: list[tuple[QtCore.Qt.WindowType, bool]] = []  # what its window's setFlag set

        def trigger(t: str) -> None:
            if raising:
                raise KeyboardInterrupt('an abort landing in the trigger')
            self.opacity_at_trigger = self.opacity
            self.triggered.append(t)

        self._actions = [
            SimpleNamespace(text=lambda t=t: t, isEnabled=lambda t=t: t not in disabled, trigger=lambda t=t: trigger(t))
            for t in texts
        ]

    def actions(self) -> list[SimpleNamespace]:
        return self._actions

    def close(self) -> None:
        self.closed = True

    def isVisible(self) -> bool:
        return not self.closed

    def windowOpacity(self) -> float:
        return 1.0 if self.opacity is None else self.opacity

    def setWindowOpacity(self, opacity: float) -> None:
        self.opacity = opacity
        self.opacities.append(opacity)
        if self.closed_as_faded:
            self.closed = True

    def windowHandle(self) -> SimpleNamespace:
        return SimpleNamespace(setFlag=lambda flag, on: self.flags.append((flag, on)))


VIEW = 'View Outputs In 3D View'


def test_the_pick_looks_again_until_the_menu_opens_then_triggers_the_action(helpers: types.ModuleType) -> None:
    pick = helpers._MenuPick(VIEW, None)
    menu = Menu('Open', '&View Outputs In 3D View', 'Compute Outputs')
    assert pick.pick(None) is False  # not open yet: its timer starts again
    assert pick.pick(menu) is True
    assert menu.triggered == ['&View Outputs In 3D View'] and menu.closed
    assert pick.failure('g', held=False) is None


def test_the_menu_is_made_transparent_once_it_opens(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-134: a popup above every window, it showed for 240 ms during a shot otherwise invisible
    pick = helpers._MenuPick(VIEW, None)
    menu = Menu(VIEW)
    assert pick.fade(None) is False  # not open yet: its timer starts again
    assert pick.fade(menu) is True and menu.opacity == 0.0
    assert menu.triggered == [] and not menu.closed  # the pick's, still to come


@pytest.mark.parametrize('platform', ['darwin', 'win32'])
def test_the_menu_made_transparent_lets_clicks_through_on_macos(
    helpers: types.ModuleType, monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    # the user's choice (DECISIONS.md): a click the user makes at its place goes to the window under it, as through
    # Designer's window; measured on macOS only
    monkeypatch.setattr(sys, 'platform', platform)
    menu = Menu(VIEW)
    assert helpers._MenuPick(VIEW, None).fade(menu) is True
    through = (qt('QtCore').Qt.WindowType.WindowTransparentForInput, True)
    assert menu.flags == ([through] if platform == 'darwin' else [])


def test_a_popup_open_before_the_menu_isnt_made_transparent(helpers: types.ModuleType) -> None:
    users = Menu('Cut', VIEW)
    pick = helpers._MenuPick(VIEW, users)
    assert pick.fade(users) is False and users.opacity is None and users.flags == []


def test_a_popup_open_before_the_menu_isnt_taken_for_it(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-109: a menu of the user's, open as the job runs
    users = Menu('Cut', VIEW)
    pick = helpers._MenuPick(VIEW, users)
    assert pick.pick(users) is False
    assert not users.closed and users.triggered == []


def test_a_menu_without_the_action_is_closed_and_said(helpers: types.ModuleType) -> None:
    pick = helpers._MenuPick(VIEW, None)
    menu = Menu('Open', 'Rename')
    pick.pick(menu)
    assert menu.closed and menu.triggered == []
    assert pick.failure('g', held=False) == "the Explorer's menu for graph g had no 'View Outputs In 3D View'"


def test_a_disabled_action_isnt_triggered_and_is_said(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-110
    pick = helpers._MenuPick(VIEW, None)
    menu = Menu('Open', VIEW, disabled=(VIEW,))
    pick.pick(menu)
    assert menu.closed and menu.triggered == []
    assert pick.failure('g', held=False) == "the Explorer's menu for graph g had 'View Outputs In 3D View' disabled"


def test_the_menu_is_closed_even_when_the_trigger_raises(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-108: an abort (cancel, timeout) landing in the pick; an open menu holds the job
    pick = helpers._MenuPick(VIEW, None)
    menu = Menu(VIEW, raising=True)
    with pytest.raises(KeyboardInterrupt):
        pick.pick(menu)
    assert menu.closed


def test_a_menu_that_never_opened_is_said(helpers: types.ModuleType) -> None:
    pick = helpers._MenuPick(VIEW, None)
    pick.pick(None)
    assert pick.failure('g', held=False) == "the Explorer's menu for graph g didn't open"


def test_a_menu_closed_before_its_pick_isnt_looked_in_and_is_said(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-146, HLP-147: closed by something else once open, before its action was picked
    pick = helpers._MenuPick(VIEW, None)
    menu = Menu(VIEW)
    menu.close()
    assert pick.pick(menu) is True  # its timer stops looking
    assert menu.triggered == [] and pick.closed
    assert pick.failure('g', held=False) == "the Explorer's menu for graph g closed before its action was picked"


def test_a_failure_in_every_try_says_how_many(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-147: the menu is opened again when it closed before its pick, MENU_TRIES times at most
    pick = helpers._MenuPick(VIEW, None)
    pick.pick(None)
    assert pick.failure('g', held=False, tries=3) == "the Explorer's menu for graph g didn't open, in each of 3 tries"


def test_a_menu_the_guard_closed_after_the_action_is_a_failure(helpers: types.ModuleType) -> None:
    # a second menu (Designer asking which channel) holds the job until the guard closes it, unanswered
    pick = helpers._MenuPick(VIEW, None)
    pick.pick(Menu(VIEW))
    assert pick.failure('g', held=True) == (
        "a menu was still open 5 s after 'View Outputs In 3D View' (Designer asking something more?), and was closed "
        'unanswered'
    )


def test_the_guard_closes_the_popups_above_the_one_open_before_and_runs_no_python(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-108: an abort is dropped in a Python slot, so the guard is C callables only; HLP-109: it leaves a
    # popup open before (the user's) alone. Popups whose close() is C too, so any Python frame would be the guard's
    import functools

    closed: list[str] = []
    users = SimpleNamespace(close=functools.partial(closed.append, 'users'))
    popups = [SimpleNamespace(close=functools.partial(closed.append, name)) for name in ('second', 'menu')]
    active = iter([*popups, users, users]).__next__  # what activePopupWidget() returns, call after call
    guard = helpers._popup_closer(active, users)
    frames: list[str] = []
    previous = sys.gettrace()
    sys.settrace(lambda frame, event, arg: frames.append(frame.f_code.co_name))
    try:
        guard()
    finally:
        sys.settrace(previous)
    assert closed == ['second', 'menu'] and frames == []


def test_the_guard_closes_at_most_five_popups(helpers: types.ModuleType) -> None:
    # a popup refusing to close stays the active one: the guard doesn't loop on it
    closes: list[str] = []
    stuck = SimpleNamespace(close=lambda: closes.append('close'))
    active = iter([stuck] * 50 + [None]).__next__
    helpers._popup_closer(active, None)()
    assert len(closes) == 5


class Timer:
    """A QTimer: started, stopped, never firing by itself; `run` is what its timeout was connected to. `aborted`: its
    start raises, as an abort landing there would."""

    def __init__(self, aborted: bool = False, parent: 'QtCore.QObject | None' = None) -> None:
        self.active = False
        self.aborted = aborted
        self.parent = parent
        self.run: Callable[[], object] = lambda: None
        self.timeout = SimpleNamespace(connect=lambda run: setattr(self, 'run', run))
        self.starts: list[int] = []  # each start's interval, in ms

    def setSingleShot(self, single: bool) -> None:
        pass

    def start(self, after: int) -> None:
        if self.aborted:
            raise KeyboardInterrupt('an abort as the timer starts')
        self.active = True
        self.starts.append(after)

    def stop(self) -> None:
        self.active = False

    def isActive(self) -> bool:
        return self.active


def _outputs_applied(
    helpers: types.ModuleType,
    send_event: Callable[[list[Timer]], None],
    aborted_start: int | None = None,
    timers: list[Timer] | None = None,
) -> None:
    """_apply_outputs on a faked Explorer, each menu's run being `send_event(timers)`; the timers it makes go in
    `timers`, two a try (the look, the guard), the one numbered `aborted_start` raising as it starts."""
    made: list[Timer] = [] if timers is None else timers

    def new_timer(parent: 'QtCore.QObject | None' = None) -> Timer:
        made.append(Timer(aborted=len(made) == aborted_start, parent=parent))
        return made[-1]

    qt('QtCore').QTimer.side_effect = new_timer
    qt('QtWidgets').QApplication.sendEvent.side_effect = lambda viewport, event: send_event(made)
    qt('QtWidgets').QApplication.activePopupWidget.return_value = None
    vars(helpers)['_row_point'] = lambda tree, row, graph: 'the point'
    tree = SimpleNamespace(selectionModel=lambda: SimpleNamespace(selectedRows=lambda: [Index()]), viewport=mock.Mock())
    helpers._apply_outputs(tree, SimpleNamespace(getIdentifier=lambda: 'g'), [])


def _menus(*menus: 'Menu | None') -> None:
    """The popups open as each try begins (none), then as its look runs: `menus`, one a try (None: none opened)."""
    qt('QtWidgets').QMenu = Menu
    qt('QtWidgets').QApplication.activePopupWidget.side_effect = [x for menu in menus for x in (None, menu)]


def _looked(timers: list[Timer]) -> None:
    """A try's menu run: its look, the first of its two timers."""
    timers[-2].run()


@pytest.mark.parametrize('menu_run', ['returns', 'raises', 'aborted as the guard starts'])
def test_every_timer_is_stopped_whatever_the_menu_does(helpers: types.ModuleType, menu_run: str) -> None:
    # REVIEW.md TST-316: a timer left running would later pick from, close or fade a menu of the user's; HLP-112: an
    # abort landing as a timer starts, the ones before it already running
    def send_event(timers: list[Timer]) -> None:
        if menu_run == 'raises':
            raise KeyboardInterrupt('an abort as the menu runs')

    timers: list[Timer] = []
    aborted = 1 if menu_run == 'aborted as the guard starts' else None
    with pytest.raises((RuntimeError, KeyboardInterrupt)):  # returning without a menu: it didn't open
        _outputs_applied(helpers, send_event, aborted, timers)
    tries = helpers.MENU_TRIES if menu_run == 'returns' else 1  # an abort isn't tried again
    assert len(timers) == 2 * tries and not any(t.active for t in timers)


def test_the_timers_go_with_the_function_whatever_runs_of_its_finally(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-118: an abort landing on the finally's first line skips the stops; the timers' parent, made for
    # this call and held by its frame alone, takes them with it (the live designer fact: editor_panels_and_fit)
    timers: list[Timer] = []
    with pytest.raises(RuntimeError):  # no menu: it didn't open
        _outputs_applied(helpers, lambda made: None, timers=timers)
    assert [t.parent for t in timers] == [qt('QtCore').QObject.return_value] * (2 * helpers.MENU_TRIES)


def test_a_menu_the_guard_had_to_close_is_a_failure(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-326: the guard's timer has run (no longer active) as the menu's loop ends
    def send_event(timers: list[Timer]) -> None:
        _looked(timers)  # the menu open: picked
        timers[-1].active = False

    _menus(Menu(VIEW))
    with pytest.raises(RuntimeError, match="a menu was still open 5 s after 'View Outputs In 3D View'"):
        _outputs_applied(helpers, send_event)


def test_the_menu_is_made_transparent_and_picked_as_soon_as_it_opens(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-134: transparent as it opens; HLP-147: its action is there at the first look (measured), so it is
    # picked then too, leaving nothing the time to close the menu before
    menu = Menu(VIEW)
    _menus(menu)
    _outputs_applied(helpers, _looked)
    assert menu.opacity_at_trigger == 0.0 and menu.triggered == [VIEW] and menu.closed


def test_the_look_starts_at_once_and_the_guard_after_menu_guard(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-406: the look at once, so the menu is transparent as it opens; the guard after MENU_GUARD
    timers: list[Timer] = []
    with pytest.raises(RuntimeError):  # no menu: it didn't open
        _outputs_applied(helpers, lambda made: None, timers=timers)
    assert [t.starts for t in timers] == [[0], [helpers.MENU_GUARD]] * helpers.MENU_TRIES


def test_the_look_looks_again_until_the_menu_opens_then_stops(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-406
    menu = Menu(VIEW)
    timers: list[Timer] = []

    def send_event(made: list[Timer]) -> None:
        made[0].run()  # no popup open yet
        made[0].run()  # the menu open

    qt('QtWidgets').QMenu = Menu
    qt('QtWidgets').QApplication.activePopupWidget.side_effect = [None, None, menu]  # before the menu, two looks
    _outputs_applied(helpers, send_event, timers=timers)
    assert timers[0].starts == [0, 0] and menu.opacities[0] == 0.0 and menu.triggered == [VIEW]


def test_a_menu_closed_before_its_pick_is_opened_again(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-147: something closed the menu before its action was picked, and the whole shot was refused
    first, second = Menu(VIEW, closed_as_faded=True), Menu(VIEW)
    _menus(first, second)
    _outputs_applied(helpers, _looked)
    assert first.triggered == [] and second.triggered == [VIEW]


def test_a_menu_that_didnt_open_is_opened_again(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-147: closed before the look saw it, a menu is one that didn't open
    menu = Menu(VIEW)
    _menus(None, menu)
    _outputs_applied(helpers, _looked)
    assert menu.triggered == [VIEW]


@pytest.mark.parametrize('platform', ['darwin', 'win32'])
def test_a_menu_closed_before_its_pick_in_every_try_is_said_so_and_each_window_gets_its_look_back(
    helpers: types.ModuleType, monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    # REVIEW.md HLP-146: made transparent and click-through at once, then closed by something else before the pick.
    # "didn't open" was said, and on macOS its window stayed so: the Explorer deletes the menu as it closes, and its
    # window was kept. Off macOS nothing was measured: only transparent, nothing held. HLP-147: tried again each time
    monkeypatch.setattr(sys, 'platform', platform)
    menus = [Menu(VIEW, closed_as_faded=True) for _ in range(helpers.MENU_TRIES)]
    _menus(*menus)
    with pytest.raises(
        RuntimeError,
        match="the Explorer's menu for graph g closed before its action was picked, in each of %d tries"
        % helpers.MENU_TRIES,
    ):
        _outputs_applied(helpers, _looked)
    for menu in menus:
        assert menu.native == (['hold', 'look 1 False', 'let go'] if platform == 'darwin' else [])
        assert not menu.triggered


def test_a_menu_without_the_action_isnt_opened_again(helpers: types.ModuleType) -> None:
    # Designer's answer, not something closing the menu: the same in every try
    _menus(Menu('Open', 'Rename'), Menu(VIEW))
    with pytest.raises(RuntimeError, match=r"the Explorer's menu for graph g had no 'View Outputs In 3D View'$"):
        _outputs_applied(helpers, _looked)


@pytest.mark.skipif(sys.platform != 'darwin', reason='only macOS holds a window transparent (view3d.py)')
def test_a_menu_picked_has_its_window_given_its_look_back_once_closed(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-146: the shot leaves no window of Designer's transparent, the menu's included
    menu = Menu(VIEW)

    def send_event(timers: list[Timer]) -> None:
        _looked(timers)  # the fade and the pick, which closes the menu
        assert menu.native == ['hold']  # still transparent while it ran

    _menus(menu)
    _outputs_applied(helpers, send_event)
    assert menu.native == ['hold', 'look 1 False', 'let go'] and menu.triggered == [VIEW] and menu.closed


def _materials_menu(helpers: types.ModuleType, *names: str) -> None:
    menu = SimpleNamespace(
        aboutToShow=mock.Mock(),
        actions=lambda: (
            [SimpleNamespace(text=lambda n=n: n, menu=lambda: object()) for n in names]
            + [SimpleNamespace(text=lambda: 'Add', menu=lambda: None)]
        ),
    )
    vars(helpers)['_menu_action'] = lambda bar, keep, *path: SimpleNamespace(menu=lambda: menu)


def test_a_mesh_using_one_material_is_taken(helpers: types.ModuleType) -> None:
    _materials_menu(helpers, '&Default (overridden)')
    helpers._material_checked(object(), [])


def test_a_material_the_mesh_doesnt_use_isnt_counted(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-114: Materials > Add's, as Designer lists it (measured)
    _materials_menu(helpers, 'Default (overridden)', 'Second (unused) (overridden)')
    helpers._material_checked(object(), [])


def test_a_mesh_with_several_materials_is_refused(helpers: types.ModuleType) -> None:
    # tiling= would tile one of them (REVIEW.md TST-315)
    _materials_menu(helpers, 'Body', 'Glass')
    with pytest.raises(
        RuntimeError, match=r"^the 3D view's mesh uses 2 materials \(Body, Glass\): tiling= sets the material of a mesh"
    ):
        helpers._material_checked(object(), [])


# an event the set-up's fakes record, by its kind: the menu path, the step or the line it names (REVIEW.md TST-952)
Event = tuple[Literal['between', 'lookup', 'print', 'render', 'trigger', 'wait'], tuple[str, ...]]


class Frames:
    """_Frames, faked: each wait recorded in `events` as ('wait', (what,)), and raising as an abort would at the
    `abort_at`-th (from 1). Designer's event loop (`events_ran`), where a load triggered before happens, runs in each
    settled(), and in until() when its state is false as it starts: until() reads it then and once the loop has run,
    each reading recorded in `states`, and returns the last, or the next of `ends` while there are."""

    def __init__(self, events: list[Event]) -> None:
        self.events = events
        self.settles: list[bool] = []  # what each settled() says, True once they run out
        self.ends: list[bool] = []  # what each until() says, its state's reading once they run out
        self.states: list[list[bool]] = []  # each until()'s readings of its state
        self.events_ran: Callable[[], None] = lambda: None  # Designer's event loop, run in each wait
        self.abort_at = 0
        self.settle_error = ''  # settled() raising a RuntimeError of this text, when not empty
        self.below = ''  # what below_rest() says
        self._waits = 0

    def _wait(self, what: str) -> None:
        self._waits += 1
        if self._waits == self.abort_at:
            raise KeyboardInterrupt('an abort in a wait')
        self.events.append(('wait', (what,)))

    def mark(self) -> int:
        return len(self.events)

    def settled(self, since: int) -> bool:
        self.events_ran()
        if self.settle_error:
            raise RuntimeError(self.settle_error)
        self._wait('settled')
        return self.settles.pop(0) if self.settles else True

    def restarted(self, since: int) -> bool:
        self.events_ran()  # a load triggered before happens in the wait, and restarts the view
        self._wait('restarted')
        return True

    def until(self, state: Callable[[], bool], limit: float) -> bool:
        self._wait('loaded')
        read = [state()]  # before the event loop ran: as the wait starts
        if not read[-1]:
            self.events_ran()
            read.append(state())
        self.states.append(read)
        return self.ends.pop(0) if self.ends else read[-1]

    def below_rest(self) -> str:
        return self.below


# Designer's environment maps, faked, each by the URL the state file names it by: the fixture's map among them
MAPS = {
    'corsica_beach': 'sd-3dview-maps://corsica_beach.exr',
    'panorama_map': 'sd-3dview-maps://panorama_map.hdr',
    'studio': 'sd-3dview-maps://studio.hdr',
}


SAVE, RESET = ('Scene', 'Save Current State As Default'), ('Scene', 'Reset Scene')
TORUS = 'sd-3dview-shapes://Torus.FBX'  # the Torus's id in the state file
OWN = (SAVE, RESET)  # the state file's own entries, which every set-up triggers


class Graph:
    """A compositing graph, faked: its identifier and its outputs. It stands for SDSBSCompGraph, as the editor's."""

    def __init__(self, name: str, outputs: int = 2) -> None:
        self.name, self.outputs = name, outputs

    def getIdentifier(self) -> str:
        return self.name

    def getOutputNodes(self) -> list[object]:
        return [object()] * self.outputs

    def compute(self) -> None:
        pass


class Designer:
    """The set-up's Designer, faked: its panels (`hidden` ones not visible), the 3D view's menus (each path looked up
    and each triggered recorded), its environment maps (MAPS), the graph `graph=` names with `outputs` outputs, the
    editor's graph `editor`, with `editor_outputs`, and its 3D viewport, `viewport` [width, height]. Its state file: a
    Save writes `state` (the fixture by default) to the default state file, or to `saves_to` (the Default State File
    Designer started with, set since), with a texture in the folder beside it while the view shows a graph's outputs
    (`linked`). Reset Scene raises `load_error` at the load it names (from 1), as Designer would; else Designer loads
    the file once the trigger has returned, in its event loop (a wait's, Frames.events_ran): it records the file in
    `loads`, makes it the state, unlinks the view, puts the AOV back to Beauty and turns each material's Override
    Material on. Till then the Scene menu checks no mesh (_scene_checked). A graph's outputs applied link it again,
    and turn each material's Override Material on, as the Explorer's View Outputs In 3D View does (REVIEW.md HLP-291,
    measured). The AOV shown is `aov`, and each material's Override Material `overridden`."""

    def __init__(
        self,
        helpers: types.ModuleType,
        hidden: tuple[str, ...] = (),
        outputs: int = 2,
        editor_outputs: int = 2,
        linked: bool = True,
        viewport: tuple[int, int] = (400, 300),
    ) -> None:
        self.events: list[Event] = []  # ('lookup' or 'trigger', the menu path or step)
        self.checked: set[tuple[str, ...]] = set()  # the menu paths whose action is checked, as a mesh shown is
        self.order: list[str] = []
        self.state = SAVED  # what a Save writes: the session's state
        self.linked = linked  # the view shows a graph's outputs: a Save writes their textures
        self.loads: list[str] = []  # each state file Reset Scene loaded
        self.loading = False  # Reset Scene triggered, the file not read yet
        self.load_error: tuple[int, str] = (0, '')  # (the Reset Scene that raises, from 1; its error)
        self.saves_to = ''  # where a Save writes, when not the default state file
        self.aov = 'Beauty'
        self.overridden = [True]  # each material's Override Material, in the Materials menu's order
        self.editor: Graph | None = Graph('editor', editor_outputs)
        self.path = os.path.join(helpers._version_folder(), helpers.STATE_NAME)
        self.resources = cast(Callable[[str], str], helpers._state_resources)
        widgets = qt('QtWidgets')
        viewport_widget = SimpleNamespace(
            metaObject=lambda: SimpleNamespace(className=lambda: 'Alg::Gui3D::ViewportWidget'),
            width=lambda: viewport[0],
            height=lambda: viewport[1],
        )
        tree = SimpleNamespace(objectName=lambda: 'mTreeView')
        children = {widgets.QMenuBar: [object()], widgets.QTreeView: [tree], widgets.QWidget: [viewport_widget]}
        dock = SimpleNamespace(findChildren=lambda cls: children[cls])
        areas = {helpers._PANEL_AREAS[name] for name in hidden}

        def visible_dock(mw: 'QtWidgets.QMainWindow', area: str) -> SimpleNamespace | None:
            self.order.append(area)
            return None if area in areas else dock

        def menu_action(bar: 'QtWidgets.QMenuBar', keep: list['Kept'], *path: str) -> SimpleNamespace:
            self.events.append(('lookup', path))
            return SimpleNamespace(trigger=lambda: self._trigger(path), isChecked=lambda: path in self.checked)

        vars(helpers)['_visible_dock'] = visible_dock
        vars(helpers)['_menu_action'] = menu_action
        # the Scene menu's checked entries: the mesh once a load has ended, Display UVs in 2D View throughout
        vars(helpers)['_scene_checked'] = lambda bar, keep: (
            {'Display UVs in 2D View'} | (set() if self.loading else {'Rounded cube'})
        )
        vars(helpers)['_overrides'] = lambda bar, keep: [self._override(i) for i in range(len(self.overridden))]
        vars(helpers)['_aov_menu'] = lambda dock, keep: SimpleNamespace(
            actions=lambda: [self._aov(name) for name in ('Beauty', 'Material roughness')]
        )
        vars(helpers)['_material_checked'] = lambda bar, keep: None
        vars(helpers)['_home_screen'] = lambda: None
        vars(helpers)['SDSBSCompGraph'] = Graph
        vars(helpers)['_current_graph'] = lambda: self.editor

        def apply_outputs(tree: 'QtWidgets.QTreeView', g: Graph, keep: list['Kept']) -> None:
            self.events.append(('trigger', ('outputs', g.getIdentifier())))
            self.linked = True
            self.overridden = [True] * len(self.overridden)

        vars(helpers)['_apply_outputs'] = apply_outputs

        vars(helpers)['_environment_maps'] = lambda: dict(MAPS)
        self.frames = Frames(self.events)
        frames = self.frames

        class Watching:  # a class, as _Frames is: the set-up's own annotation names it
            def __new__(  # type: ignore[misc]  # a fake made by its class
                cls, viewport: 'QtWidgets.QWidget', render: 'Callable[[], QtGui.QImage]'
            ) -> Frames:
                return frames

        vars(helpers)['_Frames'] = Watching
        vars(helpers)['find_graph'] = lambda name: Graph(name, outputs)
        frames.events_ran = self._loaded

    def _trigger(self, path: tuple[str, ...]) -> None:
        self.events.append(('trigger', path))
        saved = self.saves_to or self.path
        folder = self.resources(saved)
        if path == SAVE:
            written = os.stat(saved).st_mtime_ns if os.path.exists(saved) else 0
            Path(saved).write_text(self.state, encoding='utf-8')
            # a later time than the file had, as Designer's Save gives it seconds after the file was last written: a
            # clock of coarse steps would leave the time of a write milliseconds later as it was (REVIEW.md TST-927)
            os.utime(saved, ns=(written + 10**9, written + 10**9))
            shutil.rmtree(folder, ignore_errors=True)
            if self.linked:
                os.makedirs(folder)
                Path(folder, 'default_baseColor.png').write_bytes(b'ours')
        elif path == RESET:
            if self.triggered().count(RESET) == self.load_error[0]:
                raise RuntimeError(self.load_error[1])
            self.loading = True

    def _loaded(self) -> None:
        """The load triggered, as Designer makes it in its event loop: the file read then."""
        if self.loading:
            self.loading = False
            self.state = Path(self.saves_to or self.path).read_text(encoding='utf-8')
            self.loads.append(self.state)
            self.linked, self.aov = False, 'Beauty'
            self.overridden = [True] * len(self.overridden)

    def _override(self, i: int) -> SimpleNamespace:
        def trigger() -> None:
            self.events.append(('trigger', ('override', str(i))))
            self.overridden[i] = not self.overridden[i]

        return SimpleNamespace(isChecked=lambda: self.overridden[i], trigger=trigger)

    def _aov(self, name: str) -> SimpleNamespace:
        def trigger() -> None:
            self.events.append(('trigger', ('aov', name)))
            self.aov = name

        return SimpleNamespace(text=lambda: name, isChecked=lambda: self.aov == name, trigger=trigger)

    def steps(self, events: list[Event]) -> list[tuple[str, ...] | str]:
        """The changes triggered and the waits in `events`, in order: each change by its path, each wait by its name."""
        return [path if kind == 'trigger' else path[0] for kind, path in events if kind in ('trigger', 'wait')]

    def users_default(self) -> dict[str, bytes]:
        """The user's default state file and a texture beside it, written; files() of them."""
        Path(self.path).write_bytes(b'<the users own default/>\r\n')
        os.makedirs(self.resources(self.path))
        Path(self.resources(self.path), 'users.png').write_bytes(b'theirs')
        return files(self.path)

    def triggered(self) -> list[tuple[str, ...]]:
        return [path for kind, path in self.events if kind == 'trigger']

    def changes(self) -> list[tuple[str, ...]]:
        """What was triggered, less the state file's own Save and Reset Scene."""
        return [path for path in self.triggered() if path not in OWN]

    def set_up(self) -> list[Event]:
        """The events before the render: the set-up's, not its put-back's."""
        return self.events[: self.events.index(('render', ()))]

    def looked_up_first(self) -> list[tuple[str, ...]]:
        """The menu paths looked up before the first change."""
        kinds = [kind for kind, _ in self.events]
        return [path for kind, path in self.events[: kinds.index('trigger')]]


def set_up(
    helpers: types.ModuleType,
    *args: object,
    between: Callable[[], None] | None = None,
    render: Callable[[], None] | None = None,
    **options: object,
) -> bool:
    """The 3D view's set-up run as a 3D shot runs it (shot3d.py), on the Designer the test faked: on its watch of the
    frames, `between` before each step, around a render, recorded in its events as ('render', ()), then `render` if
    given. Returns whether it changed what the view shows."""
    frames = helpers._Frames(None, None)
    with helpers._3d_set_up(*args, **options).applied(between, frames) as changed:
        frames.events.append(('render', ()))
        if render is not None:
            render()
    return cast(bool, changed)


@pytest.mark.parametrize(
    'outputs, said', [(1, 'graph g has one output: Designer would ask'), (0, 'graph g has no outputs to show')]
)
def test_a_graph_with_fewer_than_two_outputs_is_refused_before_the_panels_are_looked_at(
    helpers: types.ModuleType, outputs: int, said: str
) -> None:
    # REVIEW.md TST-318: the refusal doesn't hang on the 3D View being visible; HLP-110: no outputs said plainly
    designer = Designer(helpers, hidden=('3d',), outputs=outputs)
    with pytest.raises(RuntimeError, match=said):
        set_up(helpers, 'g', 'Plane')
    assert designer.order == [] and designer.triggered() == []


def test_graph_is_refused_before_anything_changes_with_the_explorer_hidden(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-107: the mesh changed, then the panel's error
    designer = Designer(helpers, hidden=('explorer',))
    with pytest.raises(RuntimeError, match='Explorer panel'):
        set_up(helpers, mesh='Plane', graph='g')
    assert designer.triggered() == []


def test_the_mesh_the_tiling_and_the_light_need_no_parameters_panel(helpers: types.ModuleType) -> None:
    # through the state file: no Parameters panel, nor the material's or the environment's menu entries
    designer = Designer(helpers, hidden=('parameters',))
    set_up(helpers, mesh='Plane', tiling=2.0, environment='studio', environment_rotation=90.0)
    assert helpers._PANEL_AREAS['parameters'] not in designer.order
    assert [path for kind, path in designer.events if kind == 'lookup' and path[0] == 'Environment'] == []
    assert [path for kind, path in designer.events if kind == 'lookup' and len(path) > 2] == []


@pytest.mark.parametrize('mesh', [None, 'Plane'], ids=['no mesh', 'a mesh'])
def test_the_menu_entries_it_needs_are_looked_up_before_anything_changes(
    helpers: types.ModuleType, mesh: str | None
) -> None:
    # the mesh's entry, which tells whether the mesh shows already (_SetUp.may_change)
    designer = Designer(helpers)
    set_up(helpers, mesh=mesh, view='Top', tiling=2.0)
    first = designer.looked_up_first()
    assert {SAVE, RESET, ('Materials',)} <= set(first)
    assert mesh is None or ('Scene', mesh) in first


def test_the_materials_menu_every_set_up_reads_is_looked_up_before_anything_changes(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-276: each set-up reads Override Material there (_overrides), after the Save
    designer = Designer(helpers)
    set_up(helpers, orbit=[30.0, 0.0])
    assert ('Materials',) in designer.looked_up_first()


def test_an_unknown_environment_is_refused_before_anything_changes_naming_the_maps(helpers: types.ModuleType) -> None:
    designer = Designer(helpers)
    with pytest.raises(
        RuntimeError, match=r"^unknown environment 'Studio'; Designer has corsica_beach, panorama_map, studio$"
    ):
        set_up(helpers, mesh='Plane', environment='Studio')
    assert designer.order == [] and designer.events == []


@pytest.mark.parametrize(
    'name, rotation, exposure, said',
    [
        ('studio', 90.0, 1.0, 'environment studio, rotation 90 degrees, exposure 1'),
        (None, 0.0, None, 'environment rotation 0 degrees'),
        (None, None, -0.25, 'environment exposure -0.25'),
        ('corsica_beach', None, None, 'environment corsica_beach'),
    ],
)
def test_the_environment_is_said_with_what_was_given(
    helpers: types.ModuleType, name: str | None, rotation: float | None, exposure: float | None, said: str
) -> None:
    assert helpers._environment_said(name, rotation, exposure) == said


def test_the_environment_maps_are_designers_files_each_by_the_url_the_state_file_names_it_by(
    helpers: types.ModuleType, tmp_path: Path
) -> None:
    # measured 2026-11-26: each of Designer's 34 maps dropped on the view was saved as sd-3dview-maps:// and its file's
    # name, a space and a capital kept (the self-test's facts check of a map's URL)
    folder = tmp_path / 'view3d' / 'maps'
    os.makedirs(folder)
    for name in ('studio 02.exr', 'panorama_map.hdr', 'Soft_1Front.exr'):
        (folder / name).write_bytes(b'')
    vars(helpers)['_APP'] = SimpleNamespace(getPath=lambda which: str(tmp_path))
    assert list(helpers._environment_maps().items()) == [
        ('panorama_map', 'sd-3dview-maps://panorama_map.hdr'),
        ('Soft_1Front', 'sd-3dview-maps://Soft_1Front.exr'),
        ('studio 02', 'sd-3dview-maps://studio 02.exr'),
    ]


def test_every_option_is_written_in_one_load_the_rest_of_the_file_kept(helpers: types.ModuleType) -> None:
    # one Save, one edit, one load (the lead, 2026-11-26): the mesh by its id, the camera framed for it, the tiling, the
    # map by its URL, the rotation in turns and the exposure (the self-test's facts checks of the state file)
    designer = Designer(helpers, linked=False)
    set_up(
        helpers,
        mesh='Torus',
        view='Top',
        tiling=2.0,
        environment='studio',
        environment_rotation=90.0,
        environment_exposure=1.5,
    )
    framed = helpers._framed(TORUS, 'Top', (400.0, 300.0))
    written = {
        'mesh': TORUS,
        'camera': framed,
        'tiling': 2.0,
        'environment': MAPS['studio'],
        'rotation': 0.25,
        'exposure': 1.5,
    }
    assert designer.loads == [helpers._state_edited(SAVED, written), SAVED]
    assert designer.triggered().count(RESET) == 2 and designer.triggered().count(SAVE) == 1


@pytest.mark.parametrize('viewport', [(400, 300), (300, 400)], ids=['wider than tall', 'taller than wide'])
def test_a_mesh_is_framed_as_the_scene_menu_frames_it_from_the_users_cameras_direction(
    helpers: types.ModuleType, viewport: tuple[int, int]
) -> None:
    # the Scene menu's switch frames the new mesh as Frame does, the camera's direction kept, while a load of another
    # mesh's id keeps the file's camera (measured 2026-11-26; the self-test's facts checks of both). The fixture's camera
    # is Designer's Default view
    designer = Designer(helpers, linked=False, viewport=viewport)
    set_up(helpers, mesh='Torus')
    start = helpers._state_fields(SAVED, ['camera'])['camera']
    framed = helpers._framed(TORUS, 'Default', viewport)
    camera = helpers._state_fields(designer.loads[0], ['camera'])['camera']
    assert alike(camera, framed._replace(yaw=start.yaw, pitch=start.pitch))
    assert helpers._state_fields(designer.loads[0], ['mesh'])['mesh'] == TORUS


def test_a_mesh_and_an_orbit_turn_from_the_new_meshs_framing(helpers: types.ModuleType) -> None:
    designer = Designer(helpers, linked=False)
    set_up(helpers, mesh='Plane', orbit=[30.0, 0.0])
    start = helpers._state_fields(SAVED, ['camera'])['camera']
    framed = helpers._framed('plane', 'Default', (400, 300))._replace(yaw=start.yaw, pitch=start.pitch)
    moved = helpers._camera_moved(framed, (400.0, 300.0), (30.0, 0.0), (0.0, 0.0), 0)
    assert alike(helpers._state_fields(designer.loads[0], ['camera'])['camera'], moved)


def test_a_tiling_sets_the_material_the_mesh_uses_and_leaves_an_unused_one(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-114, HLP-280: one Materials > Add added, which Designer lists as unused, isn't counted
    designer = Designer(helpers, linked=False)
    users = designer.state = with_added_material(SAVED)  # kept: each load makes the state the file it read (TST-956)
    set_up(helpers, tiling=2.0)
    tiled = users.replace('<___usd___tiling>*float(1)</___usd___tiling>', '<___usd___tiling>float(2)</___usd___tiling>')
    assert designer.loads == [tiled, users]


def test_a_tiling_is_refused_before_anything_changes_for_a_mesh_using_several_materials(
    helpers: types.ModuleType,
) -> None:
    # REVIEW.md HLP-127: refused before the window comes on screen; with mesh=, the new mesh's, which isn't the menu's
    designer = Designer(helpers)

    def two(bar: 'QtWidgets.QMenuBar', keep: list['Kept']) -> NoReturn:
        raise RuntimeError("the 3D view's mesh uses 2 materials (A, B): tiling= sets the material of a mesh with one")

    vars(helpers)['_material_checked'] = two
    with pytest.raises(RuntimeError, match='2 materials'):
        helpers._3d_set_up(tiling=2.0)
    assert designer.triggered() == []
    set_up(helpers, mesh='Plane', tiling=2.0)
    assert RESET in designer.triggered()


@pytest.mark.parametrize(
    'options, changed',
    [
        ({'tiling': 2.0}, True),
        ({'environment': 'studio'}, True),
        ({'environment_exposure': 1.0}, True),
        ({'environment_rotation': 90.0}, True),
        ({'mesh': 'Sphere'}, True),
        ({'orbit': [90.0, 0.0]}, True),
        ({'zoom': 2}, True),
        # through the state file, the camera's pose is known: the fixture's is Designer's Default view
        ({'view': 'Top'}, True),
        ({'orbit': [0.0, 0.0]}, False),
        ({'graph': 'g'}, False),
        # the fixture's values: REVIEW.md TST-552, 0 is a value set, not one left out
        ({'tiling': 1.0}, False),
        ({'environment': 'panorama_map'}, False),
        ({'environment_rotation': 0.0, 'environment_exposure': 0.0}, False),
    ],
    ids=[
        'a tiling',
        'a map',
        'an exposure',
        'a rotation',
        'a mesh switch',
        'an orbit',
        'a zoom',
        'a view',
        'an orbit of 0',
        'a graph',
        'the tiling shown',
        'the map shown',
        'the rotation and exposure shown',
    ],
)
def test_a_set_up_says_whether_it_changed_what_the_view_shows(
    helpers: types.ModuleType, options: View3dOptions, changed: bool
) -> None:
    # the user's ask (2026-11-18): the shot compares its render with the one before only after such a change, the light
    # and the tiling as the camera. A graph may be what is shown already, so it is no sign
    Designer(helpers)
    assert set_up(helpers, **options) is changed


@pytest.mark.parametrize(
    'options, shown, may_change',
    [
        ({'orbit': [90.0, 0.0]}, False, True),
        ({'zoom': 2}, False, True),
        ({'mesh': 'Sphere'}, False, True),
        ({'mesh': 'Sphere'}, True, False),
        ({'tiling': 2.0}, False, True),
        ({'environment_exposure': 1.0}, False, True),
        ({'environment': 'studio'}, False, True),
        ({'view': 'Top'}, False, True),
        ({'graph': 'g'}, False, False),
    ],
    ids=[
        'an orbit',
        'a zoom',
        'a mesh switch',
        'a mesh shown',
        'a tiling',
        'an exposure',
        'a map',
        'a view',
        'a graph',
    ],
)
def test_a_set_up_says_beforehand_whether_it_may_change_what_the_view_shows(
    helpers: types.ModuleType, options: View3dOptions, shown: bool, may_change: bool
) -> None:
    # a 3D shot takes a render before such a set-up, to compare with (shot3d.py)
    designer = Designer(helpers)
    if shown:
        designer.checked.add(('Scene', 'Sphere'))
    assert helpers._3d_set_up(**options).may_change is may_change


def test_a_mesh_shown_already_is_neither_loaded_again_nor_waited_for(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-195: picked again, it restarted nothing, and its wait ran to its limit (1.0 s measured). The Scene
    # menu checks it: the fixture's id is Designer's own Rounded cube's, which isn't the menu's (state3d.py)
    designer = Designer(helpers)
    designer.checked.add(('Scene', 'Sphere'))
    set_up(helpers, mesh='Sphere')
    # the base saved, and nothing loaded back after: the view as it was
    assert [e for e in designer.events if e[0] in ('trigger', 'wait')] == [('trigger', SAVE)], designer.events
    assert capsys.readouterr().out.splitlines() == ['3D view, setting: Sphere', '3D view: Sphere']
    assert not os.path.exists(designer.path)  # the Designer had none: none left


@pytest.mark.parametrize(
    'options, said',
    [
        ({'mesh': 'Sphere'}, 'Sphere'),
        ({'graph': 'g'}, "graph g's outputs on the mesh"),
        ({'view': 'Top'}, 'view Top, framed'),
        ({'tiling': 2.0}, 'tiling 2'),
        ({'environment': 'studio'}, 'environment studio'),
    ],
    ids=['a mesh', 'a graph', 'a view', 'a tiling', 'a map'],
)
def test_a_wait_failing_after_a_steps_change_says_it_was_set(
    helpers: types.ModuleType, options: View3dOptions, said: str
) -> None:
    # REVIEW.md HLP-200: each step was said once its wait ended, so an error in that wait left out the change made
    designer = Designer(helpers)
    designer.frames.settle_error = 'the view took no frame'
    with pytest.raises(RuntimeError) as raised:
        set_up(helpers, **options)
    assert str(raised.value).startswith('the view took no frame;') and said in str(raised.value), raised.value


def test_an_abort_after_a_change_says_what_was_set_and_goes_on(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-113: the plugin's abort is a BaseException, raised again unchanged so the plugin reports it. The
    # backup is put back, and the view left as the call left it: no load (scene3d.py)
    designer = Designer(helpers)

    def aborted(tree: 'QtWidgets.QTreeView', g: 'SDSBSCompGraph', keep: list['Kept']) -> None:
        raise KeyboardInterrupt('an abort as the outputs are applied')

    vars(helpers)['_apply_outputs'] = aborted
    with pytest.raises(KeyboardInterrupt, match='an abort as the outputs are applied'):
        set_up(helpers, 'g', 'Plane', 'Top')
    assert capsys.readouterr().out.splitlines() == [
        '3D view, setting: Plane, view Top, framed',
        "3D view, setting: graph g's outputs on the mesh",
    ]
    assert len(designer.loads) == 1 and not os.path.exists(designer.path)  # the set-up's load alone; no file left


def test_an_abort_during_a_steps_wait_says_that_step(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-116: the mesh changed, then the abort in the wait after it: most of a set-up's time is its waits
    designer = Designer(helpers)
    designer.frames.abort_at = 1
    with pytest.raises(KeyboardInterrupt):
        set_up(helpers, mesh='Plane')
    assert capsys.readouterr().out == '3D view, setting: Plane\n'
    assert designer.loads == [] and not os.path.exists(designer.path)


def test_an_abort_in_the_last_wait_says_each_step_begun(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-116: the waits after the load, its end, the view's settle, then the relink's, the last one
    designer = Designer(helpers)
    designer.frames.abort_at = 3
    with pytest.raises(KeyboardInterrupt):
        set_up(helpers, mesh='Plane', view='Top')
    assert capsys.readouterr().out.splitlines() == ['3D view, setting: Plane, view Top, framed']
    assert len(designer.loads) == 1 and not os.path.exists(designer.path)


@pytest.mark.parametrize(
    'options, waits',
    [
        # through the state file: the load's end, then the camera's glide (scene3d.py). The view showed a graph's
        # outputs, so after a load, the editor's graph's are put on the mesh again
        ({'mesh': 'Sphere'}, [RESET, 'loaded', 'settled', ('outputs', 'editor'), 'settled']),
        ({'graph': 'g'}, [('outputs', 'g'), 'settled']),
        ({'view': 'Top'}, [RESET, 'loaded', 'settled', ('outputs', 'editor'), 'settled']),
        ({'orbit': [90.0, 0.0]}, [RESET, 'loaded', 'settled', ('outputs', 'editor'), 'settled']),
        ({'zoom': 2}, [RESET, 'loaded', 'settled', ('outputs', 'editor'), 'settled']),
        ({'tiling': 2.0}, [RESET, 'loaded', 'settled', ('outputs', 'editor'), 'settled']),
        ({'environment': 'studio'}, [RESET, 'loaded', 'settled', ('outputs', 'editor'), 'settled']),
    ],
    ids=['mesh', 'graph', 'view', 'orbit', 'zoom', 'tiling', 'environment'],
)
def test_each_step_waits_for_the_3d_view_to_take_it(
    helpers: types.ModuleType, options: View3dOptions, waits: list[tuple[str, ...] | str]
) -> None:
    # REVIEW.md HLP-148: on the view's frames, never a fixed time (frames3d.py)
    designer = Designer(helpers)
    set_up(helpers, **options)
    assert designer.steps(designer.set_up()) == [SAVE, *waits]


UNSETTLED = " (the 3D view hadn't settled within 3 s after it)"


@pytest.mark.parametrize(
    'options, settles, ends, said',
    [
        ({'zoom': 2}, [False], [], '+2 zoom steps' + UNSETTLED),
        ({'view': 'Top'}, [], [False], 'view Top, framed' + UNSETTLED),
        ({'mesh': 'Sphere'}, [False], [], 'Sphere' + UNSETTLED),
        # REVIEW.md TST-673: the other steps, each its own wait
        ({'graph': 'g'}, [False], [], "graph g's outputs on the mesh" + UNSETTLED),
        ({'tiling': 2.0}, [False], [], 'tiling 2' + UNSETTLED),
        (
            {'environment': 'studio', 'environment_rotation': 90.0},
            [False],
            [],
            'environment studio, rotation 90 degrees' + UNSETTLED,
        ),
    ],
    ids=[
        'the view settled after the load',
        "the load's end",
        'a mesh',
        "a graph's outputs",
        'the tiling',
        'the environment',
    ],
)
def test_a_step_whose_view_never_settled_says_so(
    helpers: types.ModuleType,
    capsys: pytest.CaptureFixture[str],
    options: View3dOptions,
    settles: list[bool],
    ends: list[bool],
    said: str,
) -> None:
    # REVIEW.md HLP-214: the settle's wait ended at its net and the render followed, the result saying nothing
    designer = Designer(helpers)
    designer.frames.settles, designer.frames.ends = settles, ends
    set_up(helpers, **options)
    assert next(line for line in capsys.readouterr().out.splitlines() if line.startswith('3D view: ')) == (
        '3D view: ' + said
    )


HELD = (
    ", its sample count at 4, below 8: it may still have been refining, or the Rasterizer's Samples may be set below 8 "
    'or its accumulation antialiasing off (Renderer > Edit settings)'
)


def test_a_view_held_below_8_samples_says_what_may_hold_it_there(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-215, the user's decision (2026-11-21): with the Rasterizer's Samples below 8 or its accumulation
    # antialiasing off, the count never comes back to 8, and the result names the setting and where to change it
    designer = Designer(helpers, linked=False)
    designer.frames.settles, designer.frames.below = [False], HELD
    set_up(helpers, zoom=2)
    said = [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D view: ')]
    assert said[0] == "3D view: +2 zoom steps (the 3D view hadn't settled within 3 s after it" + HELD + ')'


def test_an_api_error_after_a_change_says_what_was_set(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-117: the sd API's error is a BaseException, not an abort
    Designer(helpers)

    def refused(tree: 'QtWidgets.QTreeView', g: 'SDSBSCompGraph', keep: list['Kept']) -> None:
        raise helpers.APIException('the API refused')

    vars(helpers)['_apply_outputs'] = refused
    with pytest.raises(RuntimeError) as raised:
        set_up(helpers, 'g', 'Plane')
    assert str(raised.value) == 'the API refused; the 3D view was already set: Plane'


def test_an_abort_while_the_menus_are_looked_up_says_nothing(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    designer = Designer(helpers)

    def aborted(bar: 'QtWidgets.QMenuBar', keep: list['Kept'], *path: str) -> NoReturn:
        raise KeyboardInterrupt('an abort as the menus are looked up')

    vars(helpers)['_menu_action'] = aborted
    with pytest.raises(KeyboardInterrupt):
        set_up(helpers, 'g', 'Plane')
    assert capsys.readouterr().out == '' and designer.triggered() == []


def test_the_3d_view_before_any_graph_was_opened_is_said(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-115: Designer builds its menu bar and viewport once a graph is opened
    vars(helpers)['_visible_dock'] = lambda mw, area: SimpleNamespace(findChildren=lambda cls: [])
    with pytest.raises(RuntimeError, match=r"the 3D view isn't built yet: .*open_graph"):
        helpers._3d_dock(object())


def test_an_error_after_a_change_says_what_was_set(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-107. Then the view gets the base back, and the backup is put back (scene3d.py)
    designer = Designer(helpers)

    def failing(tree: 'QtWidgets.QTreeView', g: 'SDSBSCompGraph', keep: list['Kept']) -> None:
        raise RuntimeError("the Explorer's menu for graph %s didn't open" % g.getIdentifier())

    vars(helpers)['_apply_outputs'] = failing
    with pytest.raises(RuntimeError) as raised:
        set_up(helpers, 'g', 'Plane', 'Top')
    assert str(raised.value) == (
        "the Explorer's menu for graph g didn't open; the 3D view was already set: Plane, view Top, framed"
    )
    assert designer.loads[-1] == SAVED and not os.path.exists(designer.path)
    assert capsys.readouterr().out.splitlines()[-1] == (
        '3D view: put back as it was (it no longer follows the graph it showed: graph editor in the editor: the '
        "Explorer's menu for graph editor didn't open)"
    )


EVERY_OPTION = ('g', 'Plane', 'Top', 2, 2.0, [90.0, 30.0], [0.25, -0.4], 'studio', 90.0, 1.0)
# each option the state file holds, in one load, then the graph's outputs
LOADED = (
    'Plane, view Top, framed, orbit 90 degrees right, 30 up, pan 0.25 of the view right, 0.4 down, +2 zoom steps, '
    'tiling 2, environment studio, rotation 90 degrees, exposure 1'
)
EVERY_STEP = "3D view: %s, graph g's outputs on the mesh" % LOADED


def test_the_line_says_what_was_set_then_that_the_view_was_put_back(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    Designer(helpers)
    set_up(helpers, *EVERY_OPTION)
    said = [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D view: ')]
    assert said == [EVERY_STEP, '3D view: put back as it was']


def test_each_step_is_said_before_its_change(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-119: an abort anywhere after a change finds it said; one before it finds the step said as begun
    designer = Designer(helpers)
    vars(helpers)['print'] = lambda line: designer.events.append(('print', (line,)))
    set_up(helpers, *EVERY_OPTION)
    said = [(kind, path) for kind, path in designer.events if kind in ('print', 'trigger')]
    assert said == [
        ('trigger', SAVE),  # the base, the user's view
        ('print', ('3D view, setting: ' + LOADED,)),
        ('trigger', RESET),  # one load of every field
        ('print', ("3D view, setting: graph g's outputs on the mesh",)),
        ('trigger', ('outputs', 'g')),
        ('print', (EVERY_STEP,)),
        ('print', ('3D view, setting: the 3D view as it was',)),
        ('trigger', RESET),  # the base
        ('trigger', ('outputs', 'editor')),  # the view showed a graph's outputs: the editor's graph's again
        ('print', ('3D view: put back as it was',)),
    ]


def test_the_set_up_runs_the_shots_look_at_the_active_app_before_each_step(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-136: the 3D shot's look whether the user made Designer the active app (shot3d.py), before each step,
    # and before the put-back's load (HLP-264: the windows stayed transparent through it)
    designer = Designer(helpers)
    vars(helpers)['print'] = lambda line: designer.events.append(('print', (line,)))
    set_up(helpers, *EVERY_OPTION, between=lambda: designer.events.append(('between', ())))
    said = [event for event in designer.events if event[0] in ('print', 'between')]
    steps = [i for i, (kind, line) in enumerate(said) if kind == 'print' and line[0].startswith('3D view, setting: ')]
    assert len(steps) == 3 and all(said[i - 1] == ('between', ()) for i in steps)
    assert said[steps[-1]] == ('print', ('3D view, setting: the 3D view as it was',))


def test_the_camera_is_the_users_moved_by_the_options_the_rest_of_the_file_kept(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # each call's moves from the view the user left (ROADMAP item 131, the user's design): the fixture's camera, Designer's
    # Default view; a turn or pan of 0 one way isn't said
    designer = Designer(helpers)
    set_up(helpers, orbit=[0.0, -20.0], pan=[0.5, 0.0])
    start = helpers._state_fields(SAVED, ['camera'])['camera']
    moved = helpers._camera_moved(start, (400.0, 300.0), (0.0, -20.0), (0.5, 0.0), 0)
    assert designer.loads[0] == helpers._state_edited(SAVED, {'camera': moved})
    said = [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D view: ')]
    assert said[0] == '3D view: orbit 20 degrees down, pan 0.5 of the view right'


def files(path: str) -> dict[str, bytes]:
    """The state file `path` and its textures' folder, each file by its path relative to the version folder."""
    folder = os.path.dirname(path)
    found = {}
    for here, _, names in os.walk(folder):
        for name in names:
            found[os.path.relpath(os.path.join(here, name), folder)] = Path(here, name).read_bytes()
    return found


@pytest.mark.parametrize(
    'options',
    [{'orbit': [30.0, 0.0]}, {'mesh': 'Plane', 'tiling': 2.0}, {'graph': 'g'}],
    ids=['camera', 'mesh', 'graph'],
)
def test_the_default_state_file_and_its_folder_are_put_back_byte_for_byte(
    helpers: types.ModuleType, options: View3dOptions
) -> None:
    # the user's default state, which Designer's next launch reads too (ROADMAP item 131, the user's design)
    designer = Designer(helpers)
    before = designer.users_default()
    set_up(helpers, **options)
    assert files(designer.path) == before
    assert designer.loads[-1] == SAVED  # the view as the user left it, loaded back


def test_with_no_default_state_file_none_is_left(helpers: types.ModuleType) -> None:
    designer = Designer(helpers)
    set_up(helpers, orbit=[30.0, 0.0])
    assert files(designer.path) == {}


def test_a_leftover_backup_is_put_back_before_anything_and_said(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # a crash between an earlier call's backup and its put-back left ours as the default (ROADMAP item 131)
    designer = Designer(helpers)
    Path(designer.path).write_text('<the users/>', encoding='utf-8')
    aside = os.path.join(helpers._version_folder(), helpers.STATE_BACKUP)
    helpers._state_back_up(designer.path, aside)
    Path(designer.path).write_text('<ours, left by a crash/>', encoding='utf-8')
    set_up(helpers, orbit=[30.0, 0.0])
    assert Path(designer.path).read_text(encoding='utf-8') == '<the users/>'
    out = capsys.readouterr().out.splitlines()
    assert out[0] == '3D view: ' + helpers.LEFTOVER_PUT_BACK % designer.path


def test_a_leftover_backup_that_cant_be_put_back_is_removed_and_said(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # the user, 2026-11-26: removed automatically and said, and the call goes on
    designer = Designer(helpers)
    aside = os.path.join(helpers._version_folder(), helpers.STATE_BACKUP)
    os.makedirs(aside)  # one that records no path
    set_up(helpers, orbit=[30.0, 0.0])
    assert capsys.readouterr().out.splitlines()[0] == '3D view: ' + helpers.LEFTOVER_REMOVED % 'it records no path'
    assert len(designer.loads) == 2 and files(designer.path) == {}


def test_a_state_file_lacking_the_camera_is_refused_and_nothing_is_loaded(helpers: types.ModuleType) -> None:
    # a field the call reads, refused before anything changes; the user's file put back
    designer = Designer(helpers)
    designer.state = SAVED.replace('<name>Default Camera</name>', '<name>Another Camera</name>')
    Path(designer.path).write_text('<the users/>', encoding='utf-8')
    with pytest.raises(RuntimeError, match="holds the camera's <local_transform> 0 times"):
        set_up(helpers, orbit=[30.0, 0.0])
    assert designer.loads == [] and designer.changes() == []
    assert files(designer.path) == {helpers.STATE_NAME: b'<the users/>'}


def alike(a: 'Pose', b: 'Pose') -> bool:
    """Two poses alike, as written in a state file and read back: each value to 9 significant digits."""
    values = zip([*a.target, *a[1:]], [*b.target, *b[1:]], strict=True)
    return all(math.isclose(x, y, rel_tol=1e-8, abs_tol=1e-6) for x, y in values)


@pytest.mark.parametrize(
    'shown, mesh, framed',
    [('Rounded Cube', None, 'Rounded Cube'), ('plane', None, 'plane'), ('Rounded Cube', 'Torus', TORUS)],
    ids=["Designer's own mesh shown", 'the Plane shown', 'mesh='],
)
def test_a_view_is_framed_for_the_mesh_it_shows(
    helpers: types.ModuleType, shown: str, mesh: str | None, framed: str
) -> None:
    # the table of Frame's framing (state3d.FRAMING). The fixture's mesh is Designer's default, the Rounded cube, by
    # another id than the Scene menu's, and framed as the cube; the Plane's framing is another (REVIEW.md TST-948). With
    # mesh=, the new mesh's, written in the same load
    designer = Designer(helpers)
    users = designer.state = SAVED.replace('<id>Rounded Cube</id>', '<id>%s</id>' % shown)
    set_up(helpers, mesh=mesh, view='Top')
    assert alike(
        helpers._state_fields(designer.loads[0], ['camera'])['camera'], helpers._framed(framed, 'Top', (400, 300))
    )
    # REVIEW.md TST-921: the user's view loaded back, its mesh with it; the user's as it was before the run, as each load
    # makes the state the file it read (TST-956)
    assert designer.loads[-1] == users


@pytest.mark.parametrize(
    'options, viewport',
    [
        ({'tiling': 1.0}, (400, 300)),
        ({'environment': 'panorama_map', 'environment_rotation': 0.0, 'environment_exposure': 0.0}, (400, 300)),
        ({'mesh': 'Sphere'}, (400, 300)),
        # REVIEW.md HLP-265: Designer saves its Default camera at yaw 45.0000024 and pitch 29.9999973, its target 1e-5
        # off, the fixture's; framed in a viewport taller than wide, the cube's distance is FRAMING's
        ({'view': 'Default'}, (300, 400)),
    ],
    ids=['a tiling', 'the light', 'a mesh', 'a view'],
)
def test_a_set_up_that_changed_nothing_loads_nothing(
    helpers: types.ModuleType, options: View3dOptions, viewport: tuple[int, int]
) -> None:
    # values the view shows already, the fixture's (the mesh the Scene menu checks): no load, so nothing to put back,
    # and no load's wait (REVIEW.md HLP-195)
    designer = Designer(helpers, viewport=viewport)
    designer.checked.add(('Scene', 'Sphere'))
    assert set_up(helpers, **options) is False
    assert designer.loads == [] and RESET not in designer.triggered()


def test_the_aov_shown_is_set_back_after_each_load(helpers: types.ModuleType) -> None:
    # a load puts it back to Beauty (scene3d.py)
    designer = Designer(helpers)
    designer.aov = 'Material roughness'
    set_up(helpers, orbit=[30.0, 0.0])
    after = [path for path in designer.triggered() if path in (RESET, ('aov', 'Material roughness'))]
    assert after == [RESET, ('aov', 'Material roughness')] * 2 and designer.aov == 'Material roughness'


@pytest.mark.parametrize(
    'options, linked, relinked',
    [
        ({'orbit': [30.0, 0.0]}, True, [('outputs', 'editor'), ('outputs', 'editor')]),
        ({'orbit': [30.0, 0.0], 'graph': 'g'}, True, [('outputs', 'g'), ('outputs', 'editor')]),
        ({'orbit': [30.0, 0.0]}, False, []),
        ({'graph': 'g'}, False, [('outputs', 'g')]),
        ({'tiling': 2.0}, True, [('outputs', 'editor'), ('outputs', 'editor')]),
    ],
    ids=['a camera', 'a camera and a graph', 'not linked', 'a graph, not linked', 'a tiling'],
)
def test_a_view_that_showed_a_graphs_outputs_shows_the_editors_graphs_after_each_load(
    helpers: types.ModuleType, options: View3dOptions, linked: bool, relinked: list[tuple[str, ...]]
) -> None:
    # nothing tells which graph it showed, so the editor's is relinked; a view that showed none is left so (the user's
    # choice, 2026-11-26)
    designer = Designer(helpers, linked=linked)
    set_up(helpers, **options)
    assert [path for path in designer.triggered() if path[0] == 'outputs'] == relinked


@pytest.mark.parametrize(
    'editor, said',
    [
        (
            Graph('one', 1),
            # REVIEW.md HLP-290: its advice, opening another graph then the editor's, dropped: untested for one output
            'the graph it showed: graph one in the editor has one output: Designer would ask which channel of the'
            ' material to show it in',
        ),
        (None, 'the graph it showed: no graph is open in the editor'),
        # REVIEW.md HLP-282, measured: the Explorer's menu takes it with no error and puts nothing on the mesh
        (Graph('empty', 0), 'the graph it showed: graph empty in the editor has no outputs to show'),
    ],
    ids=['one output', 'no graph', 'no outputs'],
)
def test_a_view_whose_graph_cant_be_relinked_is_said_to_follow_it_no_longer(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], editor: Graph | None, said: str
) -> None:
    # REVIEW.md: a one-output graph's Explorer menu asks a channel of 47; a Return with none active did nothing (1 try)
    designer = Designer(helpers)
    designer.editor = editor
    set_up(helpers, orbit=[30.0, 0.0])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D view: ')]
    assert lines == [
        '3D view: orbit 30 degrees right (it no longer follows %s)' % said,
        '3D view: put back as it was (it no longer follows %s)' % said,
    ]
    assert [path for path in designer.triggered() if path[0] == 'outputs'] == []


def test_the_users_default_state_file_is_the_one_backed_up_and_put_back(
    helpers: types.ModuleType, tmp_path: Path
) -> None:
    # Project settings > 3D View: Designer saves and loads that file, its textures beside it (measured 2026-11-26)
    own = tmp_path / 'project' / 'mine.sbsscn'
    os.makedirs(own.parent)
    own.write_text('<the users own/>', encoding='utf-8')
    Path(helpers._version_folder(), 'user_project.sbsprj').write_text(
        '<root><preferences><view3d><stateSaveFileUrl>file://%s</stateSaveFileUrl></view3d></preferences></root>' % own,
        encoding='utf-8',
    )
    designer = Designer(helpers)
    designer.path = str(own)
    set_up(helpers, orbit=[30.0, 0.0])
    assert own.read_text(encoding='utf-8') == '<the users own/>' and len(designer.loads) == 2
    assert not os.path.exists(os.path.join(helpers._version_folder(), helpers.STATE_NAME))


def test_an_error_in_the_render_still_puts_the_view_and_the_file_back(helpers: types.ModuleType) -> None:
    designer = Designer(helpers)

    def failing() -> NoReturn:
        raise RuntimeError("the 3D view isn't drawn")

    with pytest.raises(RuntimeError, match="isn't drawn"):
        set_up(helpers, orbit=[30.0, 0.0], render=failing)
    assert designer.loads[-1] == SAVED and files(designer.path) == {}


def test_a_load_ends_only_once_the_scene_menu_checks_a_mesh_again(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-917: Designer reads the file once Reset Scene has returned; till the load has ended the Scene menu
    # checks no mesh, though it checks other entries (Display UVs in 2D View). Each load's end, read as its wait starts
    # and once Designer's event loop has run, then the camera's file loaded, and the user's after it
    designer = Designer(helpers)
    set_up(helpers, orbit=[30.0, 0.0])
    assert designer.frames.states == [[False, True], [False, True]]
    assert designer.loads[1] == SAVED


def test_a_load_of_a_mesh_of_the_users_own_ends_once_the_view_settled(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-283, measured: the Scene menu checks no mesh for a mesh of the user's own, a file:// id, before the
    # load or after it; each load waited its 3 s, and the shot said the view hadn't settled
    designer = Designer(helpers, linked=False)
    designer.state = USERS
    vars(helpers)['_scene_checked'] = lambda bar, keep: {'Display UVs in 2D View'}
    set_up(helpers, orbit=[30.0, 0.0])
    # REVIEW.md HLP-286: no menu wait ('loaded'), the load's own restart waited for instead, up to SETTLE_LIMIT
    steps = [SAVE, RESET, 'restarted', 'settled', RESET, 'restarted', 'settled']
    assert designer.steps(designer.events) == steps, designer.events
    said = [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D view: ')]
    assert said == ['3D view: orbit 30 degrees right', '3D view: put back as it was']


def test_each_load_waits_as_the_mesh_of_the_file_it_loads_says(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-949: the base a mesh of the user's own, the set-up's file the Sphere: the set-up's load waits on the
    # Scene menu, the put-back's on the view
    designer = Designer(helpers, linked=False)
    designer.state = USERS
    set_up(helpers, mesh='Sphere')
    assert designer.steps(designer.events) == [SAVE, RESET, 'loaded', 'settled', RESET, 'restarted', 'settled']


def test_a_light_set_in_a_file_with_no_mesh_id_is_loaded_as_one_of_a_listed_mesh(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-287: every load read the file's mesh after writing it, and refused one with none, though the call
    # read no mesh: refused after its step was said and the file written
    designer = Designer(helpers, linked=False)
    users = designer.state = SAVED.replace('<id>Rounded Cube</id>', '')  # kept: each load makes the state its file
    set_up(helpers, environment_exposure=1.0)
    assert designer.loads == [helpers._state_edited(users, {'exposure': 1.0}), users]
    assert designer.steps(designer.events) == [SAVE, RESET, 'loaded', 'settled', RESET, 'loaded', 'settled']


def test_the_put_back_loads_the_users_view_before_it_puts_the_backup_back(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-917: Designer reads the file in the load's wait; the user's file put back before it would be loaded
    designer = Designer(helpers)
    Path(designer.path).write_text('<the users own default/>', encoding='utf-8')
    set_up(helpers, orbit=[30.0, 0.0])
    assert designer.loads[-1] == SAVED
    assert Path(designer.path).read_text(encoding='utf-8') == '<the users own default/>'


def test_the_put_backs_load_is_waited_for_its_end_then_the_view_at_rest(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-918: the put-back's Reset Scene, then its waits, as the camera's (scene3d.py)
    designer = Designer(helpers, linked=False)
    set_up(helpers, orbit=[30.0, 0.0])
    after = designer.events[designer.events.index(('render', ())) :]
    assert designer.steps(after) == [RESET, 'loaded', 'settled']


@pytest.mark.parametrize(
    'settles, ends', [([True, False], []), ([], [True, False])], ids=['the view at rest', "the load's end"]
)
def test_a_put_back_whose_view_never_settled_says_so(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], settles: list[bool], ends: list[bool]
) -> None:
    # REVIEW.md TST-918: the put-back's wait, said as the steps' are
    designer = Designer(helpers, linked=False)
    designer.frames.settles, designer.frames.ends = settles, ends
    set_up(helpers, orbit=[30.0, 0.0])
    said = [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D view: ')]
    assert said == ['3D view: orbit 30 degrees right', '3D view: put back as it was' + UNSETTLED]


@pytest.mark.parametrize('render_fails', [True, False], ids=['after an error', 'after the render'])
def test_a_put_back_that_fails_still_puts_the_file_back_and_says_so(
    helpers: types.ModuleType, render_fails: bool
) -> None:
    # REVIEW.md TST-918: the user's default state file and folder put back whatever the put-back's load did; after an
    # error, the put-back's own said after it, not in its place
    designer = Designer(helpers)
    before = designer.users_default()
    designer.load_error = (2, 'Reset Scene failed')  # the put-back's load

    def failing() -> NoReturn:
        raise RuntimeError("the 3D view isn't drawn")

    with pytest.raises(RuntimeError) as raised:
        set_up(helpers, orbit=[30.0, 0.0], render=failing if render_fails else None)
    assert str(raised.value) == (
        "the 3D view isn't drawn; and putting the 3D view back failed: Reset Scene failed"
        if render_fails
        else 'Reset Scene failed'
    )
    assert files(designer.path) == before


def test_a_put_backs_look_that_fails_is_said_and_the_users_view_loaded_all_the_same(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-272: the shot's look raises once Designer's window went off screen each time it was brought back;
    # raised at the put-back, the view kept the shot's camera
    designer = Designer(helpers, linked=False)
    failed = "the 3D view isn't drawn: Designer's window went off screen again"

    def between() -> None:
        if ('render', ()) in designer.events:
            raise RuntimeError(failed)

    set_up(helpers, orbit=[30.0, 0.0], between=between)
    assert designer.loads[-1] == SAVED
    said = [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D view')]
    assert said[-2:] == [
        '3D view, setting: the 3D view as it was',
        '3D view: put back as it was (the look before it failed: %s)' % failed,
    ]


@pytest.mark.parametrize('yaw', [-180.0, -179.99999, 180.00001], ids=['-180', 'just past -180', 'just past 180'])
def test_a_pose_at_back_is_one_whichever_side_of_the_turn_its_yaw_is(helpers: types.ModuleType, yaw: float) -> None:
    # REVIEW.md HLP-273: Designer's Back camera decodes near 180, on either side by its noise's sign (179.999995 once,
    # 2026-11-26); view='Back' gives 180
    back = helpers.Pose((0.0, 0.0, 0.0), 180.0, 0.0, 147.78)
    assert helpers._same_pose(back, back._replace(yaw=yaw))
    assert not helpers._same_pose(back, back._replace(yaw=179.0))


def test_override_material_is_set_back_after_each_load(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-267, measured: a load turns each material's Materials > Override Material on, though the file holds
    # it off
    designer = Designer(helpers, linked=False)
    designer.overridden = [False]
    set_up(helpers, orbit=[30.0, 0.0])
    after = [path for path in designer.triggered() if path in (RESET, ('override', '0'))]
    assert after == [RESET, ('override', '0')] * 2 and designer.overridden == [False]


def test_override_material_is_set_back_after_each_relink(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-291, measured: the Explorer's View Outputs In 3D View turns Override Material on by itself, so the
    # relink after each load turned it on again once the load's had been set back; the render was overridden
    designer = Designer(helpers)
    designer.overridden = [False]
    rendered: list[list[bool]] = []
    set_up(helpers, orbit=[30.0, 0.0], render=lambda: rendered.append(list(designer.overridden)))
    after = [path for path in designer.triggered() if path in (RESET, ('override', '0')) or path[0] == 'outputs']
    assert after == [RESET, ('override', '0'), ('outputs', 'editor'), ('override', '0')] * 2
    assert rendered == [[False]] and designer.overridden == [False]


@pytest.mark.parametrize('settles', [[True, False], [False, False]], ids=['the relink alone', 'the load too'])
def test_a_relink_that_didnt_settle_is_said_once(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str], settles: list[bool]
) -> None:
    # REVIEW.md HLP-292: the relink's wait after the load said nothing of a view that hadn't settled
    designer = Designer(helpers)
    designer.frames.settles = list(settles)  # the load's settle, then the relink's
    set_up(helpers, orbit=[30.0, 0.0])
    said = [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D view: ')]
    assert said[0] == '3D view: orbit 30 degrees right' + UNSETTLED, said


def test_a_view_that_didnt_settle_after_the_aov_set_back_is_said(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-292: the waits after the AOV and Override Material set back after a load said nothing; with no
    # relink, the AOV's is the step's last
    designer = Designer(helpers, linked=False)
    designer.aov = 'Material roughness'
    designer.frames.settles = [True, False]  # the load's settle, then the AOV's
    set_up(helpers, orbit=[30.0, 0.0])
    said = [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D view: ')]
    assert said[0] == '3D view: orbit 30 degrees right' + UNSETTLED, said


def test_a_view_that_didnt_settle_after_override_material_set_back_is_said(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-954: the set-back's wait folded into the load's result, untested; with no relink, it is the step's
    # last
    designer = Designer(helpers, linked=False)
    designer.overridden = [False]
    designer.frames.settles = [True, False]  # the load's settle, then the set-back's
    set_up(helpers, orbit=[30.0, 0.0])
    said = [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D view: ')]
    assert said[0] == '3D view: orbit 30 degrees right' + UNSETTLED, said


def test_graphs_outputs_put_on_the_mesh_leave_override_material_on(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-291: graph= turns it on, as the Explorer's menu does, and the call asked for those outputs; the
    # put-back sets it back
    designer = Designer(helpers)
    designer.overridden = [False]
    rendered: list[list[bool]] = []
    set_up(helpers, 'g', render=lambda: rendered.append(list(designer.overridden)))
    assert rendered == [[True]] and designer.overridden == [False]


def test_override_material_on_as_a_load_leaves_it_is_left_alone(helpers: types.ModuleType) -> None:
    designer = Designer(helpers, linked=False)
    set_up(helpers, orbit=[30.0, 0.0])
    assert ('override', '0') not in designer.triggered() and designer.overridden == [True]


@pytest.mark.parametrize('found', [True, False], ids=['a file of the users', 'none'])
def test_a_save_that_didnt_write_the_default_state_file_is_refused_and_nothing_loaded(
    helpers: types.ModuleType, tmp_path: Path, found: bool
) -> None:
    # REVIEW.md HLP-268: Designer saves the Default State File it started with; a call reading another, set in Project
    # settings since, would edit and load that one. Refused once the Save has run, what was backed up put back
    designer = Designer(helpers)
    designer.saves_to = str(tmp_path / 'started_with.sbsscn')
    if found:
        Path(designer.path).write_text('<the users/>', encoding='utf-8')
    with pytest.raises(RuntimeError, match='takes a restart of Designer') as raised:
        set_up(helpers, orbit=[30.0, 0.0])
    assert designer.path in str(raised.value)
    # REVIEW.md HLP-274: the file Designer started with lost what it held, with no backup
    assert "The file Designer started with now holds the session's state" in str(raised.value)
    assert designer.loads == [] and designer.changes() == []
    assert files(designer.path) == ({helpers.STATE_NAME: b'<the users/>'} if found else {})


def test_a_relink_with_the_explorer_hidden_is_said_to_follow_the_graph_no_longer(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-269: with no graph=, a hidden Explorer refuses nothing, and the relink after the load says why not
    designer = Designer(helpers, hidden=('explorer',))
    set_up(helpers, orbit=[30.0, 0.0])
    said = [line for line in capsys.readouterr().out.splitlines() if line.startswith('3D view: ')]
    assert said[0] == (
        '3D view: orbit 30 degrees right (it no longer follows the graph it showed: graph editor in the editor: the'
        " Explorer panel isn't visible (Windows > Explorer))"
    )
    assert [path for path in designer.triggered() if path[0] == 'outputs'] == []


def test_a_relink_that_didnt_run_isnt_waited_for(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-269: nothing changed, so no restart to wait for (scene3d.py)
    designer = Designer(helpers)
    designer.editor = Graph('one', 1)
    set_up(helpers, orbit=[30.0, 0.0])
    assert designer.steps(designer.set_up()) == [SAVE, RESET, 'loaded', 'settled']


def test_the_camera_said_gives_each_value_to_3_digits(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-269
    said = helpers._camera_said(None, (12.3456, 0.0), (0.123456, -0.5), 0)
    assert said == 'orbit 12.3 degrees right, pan 0.123 of the view right, 0.5 down'


def test_tries_failing_for_different_reasons_say_each_one(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-153: "in each of N tries" was said with the last try's reason
    _menus(Menu(VIEW, closed_as_faded=True), None, None)
    with pytest.raises(RuntimeError) as raised:
        _outputs_applied(helpers, _looked)
    assert str(raised.value) == (
        "the Explorer's menu for graph g: closed before its action was picked, then didn't open, then didn't open "
        '(%d tries)' % helpers.MENU_TRIES
    )


def test_a_fade_that_raises_closes_the_menu_at_once_and_says_why(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-153: fade and pick run in one slot; a fade raising left the menu open until the guard closed it, 5 s
    # later, said not to have opened. Picked from then, the action would run with the menu not transparent
    class Unheld(MenuWindow):
        def hold(self, window: int) -> None:
            raise RuntimeError('no window to hold')

    vars(helpers)['_MacWindow'] = Unheld
    menu = Menu(VIEW)
    _menus(menu)
    # and still open as the look's handler asks for the popup it left open (REVIEW.md HLP-177)
    qt('QtWidgets').QApplication.activePopupWidget.side_effect = [None, menu, menu]

    def send_event(timers: list[Timer]) -> None:
        with pytest.raises(RuntimeError, match='no window to hold'):  # a slot's: Qt prints it and goes on
            _looked(timers)

    with pytest.MonkeyPatch.context() as patched:
        patched.setattr(sys, 'platform', 'darwin')
        with pytest.raises(RuntimeError) as raised:
            _outputs_applied(helpers, send_event)
    assert menu.closed and menu.triggered == []
    assert str(raised.value) == (
        "the Explorer's menu for graph g couldn't be made transparent (RuntimeError: no window to hold), and was closed"
    )


def test_a_menu_the_guard_closed_with_nothing_picked_is_said_so(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-153: it was said not to have opened
    pick = helpers._MenuPick(VIEW, None)
    assert pick.failure('g', held=True) == (
        "the Explorer's menu for graph g was still open %d s after it opened, and was closed with nothing picked"
        % (helpers.MENU_GUARD // 1000)
    )
