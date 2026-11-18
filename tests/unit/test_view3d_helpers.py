"""The helpers' side of screenshot_designer('3d', ...) (designer_helpers/view3d.py), with sd and PySide6 faked: what is
checked before anything changes, what an error says was set, the graph's row found before its context menu opens
there, what the timers do while that menu runs, and the drags that turn and pan the camera, under its Camera tool. The live self-test checks the 3D view itself
(editor_panels_and_fit)."""

import contextlib
import sys
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, NoReturn, cast
from unittest import mock

import pytest

from conftest import View3dOptions

if TYPE_CHECKING:  # for the checker only: the types the faked helpers take; sd and PySide6 are faked at run time
    from PySide6 import QtCore, QtGui, QtWidgets
    from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph

    from designer_helpers.core import Kept
    from designer_helpers.view3d import Pressed


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
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    module = faked_helpers
    vars(module)['_process_events'] = lambda n=10: None
    vars(module)['_settle'] = lambda seconds: None
    vars(module)['_MacWindow'] = MenuWindow
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


def test_the_material_is_the_meshs_only_one(helpers: types.ModuleType) -> None:
    _materials_menu(helpers, '&Default (overridden)')
    assert helpers._material(object(), []) == 'Default (overridden)'


def test_a_material_the_mesh_doesnt_use_isnt_counted(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-114: Materials > Add's, as Designer lists it (measured)
    _materials_menu(helpers, 'Default (overridden)', 'Second (unused) (overridden)')
    assert helpers._material(object(), []) == 'Default (overridden)'


def test_a_mesh_with_several_materials_is_refused(helpers: types.ModuleType) -> None:
    # tiling= would tile one of them (REVIEW.md TST-315)
    _materials_menu(helpers, 'Body', 'Glass')
    with pytest.raises(RuntimeError, match="the 3D view's mesh has 2 materials: Body, Glass"):
        helpers._material(object(), [])


class Frames:
    """_Frames, faked: each wait recorded in `events` as ('wait', (what,)), and raising as an abort would at the
    `abort_at`-th (from 1). `closed` once it stops watching."""

    def __init__(self, events: list[tuple[str, tuple[str, ...]]]) -> None:
        self.events = events
        self.abort_at = 0
        self.closed = False
        self.settled_since: list[int] = []  # the marks settled() waited from
        self.settle_error = ''  # settled() raising a RuntimeError of this text, when not empty
        self._waits = 0

    def _wait(self, what: str) -> None:
        self._waits += 1
        if self._waits == self.abort_at:
            raise KeyboardInterrupt('an abort in a wait')
        self.events.append(('wait', (what,)))

    def mark(self) -> int:
        return len(self.events)

    def settled(self, since: int) -> None:
        self.settled_since.append(since)
        if self.settle_error:
            raise RuntimeError(self.settle_error)
        self._wait('settled')

    def moved(self, since: int) -> None:
        self._wait('moved')

    def taken(self) -> bool:
        self._wait('taken')
        return True

    def taking(self) -> Callable[[], bool]:
        return self.taken

    def close(self) -> None:
        self.closed = True


MAPS = {'corsica_beach': '/maps/corsica_beach.exr', 'studio': '/maps/studio.hdr'}  # Designer's environment maps, faked


class Designer:
    """set_3d_view's Designer, faked: its panels (`hidden` ones not visible), the 3D view's menus (each path looked up
    and each triggered recorded), its environment maps (MAPS), and one graph with `outputs` outputs."""

    def __init__(
        self,
        helpers: types.ModuleType,
        hidden: tuple[str, ...] = (),
        outputs: int = 2,
        tool: str = 'Camera',
        tools: tuple[str, ...] = ('Scene Browser', 'Selection', 'Camera', 'Light'),
    ) -> None:
        self.events: list[tuple[str, tuple[str, ...]]] = []  # ('lookup' or 'trigger', the menu path or step)
        self.checked: set[tuple[str, ...]] = set()  # the menu paths whose action is checked, as a mesh shown is
        self.order: list[str] = []
        self.tool = tool  # the 3D view's toolbar's tool selected: Camera or Light, one group
        widgets = qt('QtWidgets')
        viewport = SimpleNamespace(
            metaObject=lambda: SimpleNamespace(className=lambda: 'Alg::Gui3D::ViewportWidget'),
            width=lambda: 400,
            height=lambda: 300,
        )
        tree = SimpleNamespace(objectName=lambda: 'mTreeView')
        actions = [self._tool(name) for name in tools]
        toolbar = SimpleNamespace(actions=lambda: actions)
        children = {
            widgets.QMenuBar: [object()],
            widgets.QTreeView: [tree],
            widgets.QWidget: [viewport],
            widgets.QToolBar: [toolbar],
        }
        dock = SimpleNamespace(findChildren=lambda cls: children[cls])
        areas = {helpers._PANEL_AREAS[name] for name in hidden}

        def visible_dock(mw: 'QtWidgets.QMainWindow', area: str) -> SimpleNamespace | None:
            self.order.append(area)
            return None if area in areas else dock

        def menu_action(bar: 'QtWidgets.QMenuBar', keep: list['Kept'], *path: str) -> SimpleNamespace:
            self.events.append(('lookup', path))
            return SimpleNamespace(
                trigger=lambda: self.events.append(('trigger', path)), isChecked=lambda: path in self.checked
            )

        vars(helpers)['_visible_dock'] = visible_dock
        vars(helpers)['_menu_action'] = menu_action
        vars(helpers)['_material'] = lambda bar, keep: 'Default (overridden)'
        vars(helpers)['_home_screen'] = lambda: None

        def wheel(viewport: 'QtWidgets.QWidget', steps: int, taking: Callable[[], Callable[[], bool]]) -> None:
            self.events.append(('trigger', ('wheel', str(steps))))
            for _ in range(abs(steps)):
                taking()()

        vars(helpers)['_wheel'] = wheel

        def drag(
            viewport: 'QtWidgets.QWidget',
            button: 'QtCore.Qt.MouseButton',
            dx: int,
            dy: int,
            pressed: 'Pressed',
            taking: Callable[[], Callable[[], bool]],
        ) -> None:
            which = 'left' if button is qt('QtCore').Qt.MouseButton.LeftButton else 'middle'
            taken = taking()
            self.events.append(('trigger', ('drag', which, str(dx), str(dy))))
            taken()

        vars(helpers)['_drag'] = drag
        vars(helpers)['_apply_outputs'] = lambda tree, g, keep: self.events.append(
            ('trigger', ('outputs', g.getIdentifier()))
        )

        def set_tiling(
            params: 'QtWidgets.QDockWidget',
            bar: 'QtWidgets.QMenuBar',
            value: float,
            keep: list['Kept'],
            watched: Frames,
        ) -> tuple[str, bool]:
            since = watched.mark()  # as the real one waits for its change from right before it (REVIEW.md HLP-195)
            self.events.append(('trigger', ('tiling', str(value))))
            watched.settled(since)
            return 'tiling %g' % value, True

        vars(helpers)['_set_tiling'] = set_tiling
        vars(helpers)['_environment_maps'] = lambda: dict(MAPS)

        def set_environment(
            params: 'QtWidgets.QDockWidget',
            bar: 'QtWidgets.QMenuBar',
            viewport: 'QtWidgets.QWidget',
            name: str | None,
            rotation: float | None,
            exposure: float | None,
            keep: list['Kept'],
            watched: Frames,
        ) -> tuple[str, bool]:
            since = watched.mark()  # as the real one waits for each change from right before it (REVIEW.md HLP-192)
            self.events.append(('trigger', ('environment', str(name), str(rotation), str(exposure))))
            watched.settled(since)
            return cast(str, helpers._environment_said(name, rotation, exposure)), True

        vars(helpers)['_set_environment'] = set_environment
        self.frames = Frames(self.events)
        frames = self.frames

        class Watching:  # a class, as _Frames is: the set-up's own annotation names it (frames: _Frames | None)
            def __new__(  # type: ignore[misc]  # a fake made by its class
                cls, viewport: 'QtWidgets.QWidget', render: 'Callable[[], QtGui.QImage]'
            ) -> Frames:
                return frames

        vars(helpers)['_Frames'] = Watching
        # the window as it is: the turn shown on screen has a test of its own (REVIEW.md HLP-158)
        vars(helpers)['_on_screen'] = lambda mw, frames: contextlib.nullcontext(SimpleNamespace(again=lambda: None))
        vars(helpers)['find_graph'] = lambda name: SimpleNamespace(
            getIdentifier=lambda: name, getOutputNodes=lambda: [object()] * outputs, compute=lambda: None
        )

    def triggered(self) -> list[tuple[str, ...]]:
        return [path for kind, path in self.events if kind == 'trigger']

    def looked_up_first(self) -> list[tuple[str, ...]]:
        """The menu paths looked up before the first change."""
        kinds = [kind for kind, _ in self.events]
        return [path for kind, path in self.events[: kinds.index('trigger')]]

    def _tool(self, name: str) -> SimpleNamespace:
        """A toolbar action; Camera and Light are one exclusive group, as in Designer."""

        def trigger() -> None:
            self.events.append(('trigger', ('tool', name)))
            if name in ('Camera', 'Light'):
                self.tool = name

        return SimpleNamespace(text=lambda: name, isChecked=lambda: self.tool == name, trigger=trigger)


@pytest.mark.parametrize(
    'outputs, said', [(1, 'graph g has one output: Designer would ask'), (0, 'graph g has no outputs to show')]
)
def test_a_graph_with_fewer_than_two_outputs_is_refused_before_the_panels_are_looked_at(
    helpers: types.ModuleType, outputs: int, said: str
) -> None:
    # REVIEW.md TST-318: the refusal doesn't hang on the 3D View being visible; HLP-110: no outputs said plainly
    designer = Designer(helpers, hidden=('3d',), outputs=outputs)
    with pytest.raises(RuntimeError, match=said):
        helpers.set_3d_view('g', 'Plane')
    assert designer.order == [] and designer.triggered() == []


@pytest.mark.parametrize(
    'hidden, options, said',
    [
        (('parameters',), {'mesh': 'Plane', 'view': 'Top', 'tiling': 2.0}, 'Parameters panel'),
        (('explorer',), {'mesh': 'Plane', 'graph': 'g'}, 'Explorer panel'),
        (('parameters',), {'mesh': 'Plane', 'environment_rotation': 0.0}, 'environment_rotation= goes through the Par'),
        (('parameters',), {'tiling': 2.0, 'environment': 'studio'}, 'tiling= and environment= go through the Par'),
    ],
    ids=['tiling', 'graph', 'environment', 'both'],
)
def test_a_panel_it_needs_is_checked_before_anything_changes(
    helpers: types.ModuleType, hidden: tuple[str, ...], options: View3dOptions, said: str
) -> None:
    # REVIEW.md HLP-107: the mesh changed, then the panel's error
    designer = Designer(helpers, hidden=hidden)
    with pytest.raises(RuntimeError, match=said):
        helpers.set_3d_view(**options)
    assert designer.triggered() == []


@pytest.mark.parametrize(
    'mesh, materials',
    [(None, ('Materials', 'Default (overridden)', 'Edit properties')), ('Plane', ('Materials',))],
    ids=['the mesh shown', 'another mesh'],
)
def test_the_menu_entries_it_needs_are_looked_up_before_anything_changes(
    helpers: types.ModuleType, mesh: str | None, materials: tuple[str, ...]
) -> None:
    # with mesh=, the material is the new mesh's, read once it shows (REVIEW.md HLP-114)
    designer = Designer(helpers)
    helpers.set_3d_view(mesh=mesh, view='Top', tiling=2.0)
    first = designer.looked_up_first()
    assert {('Camera', 'Top'), ('Camera', 'Frame'), materials} <= set(first)
    assert mesh is None or ('Scene', mesh) in first


def test_an_unknown_environment_is_refused_before_anything_changes_naming_the_maps(helpers: types.ModuleType) -> None:
    designer = Designer(helpers)
    with pytest.raises(RuntimeError, match=r"^unknown environment 'Studio'; Designer has corsica_beach, studio$"):
        helpers.set_3d_view(mesh='Plane', environment='Studio')
    assert designer.order == [] and designer.events == []


def test_the_environments_menu_entry_is_looked_up_before_anything_changes(helpers: types.ModuleType) -> None:
    designer = Designer(helpers)
    helpers.set_3d_view(mesh='Plane', environment_exposure=1.0)
    assert ('Environment', 'Edit properties') in designer.looked_up_first()


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


class MapField:
    """The Environment field of the Parameters panel, faked: the slots connected to its valueChanged() signal, which
    the fake drop emits; `signals`: whether it has that signal (index 33 in Designer's meta-object, measured)."""

    def __init__(self, signals: bool = True) -> None:
        self.slots: list[Callable[[], object]] = []
        self.signals = signals

    def metaObject(self) -> SimpleNamespace:
        return SimpleNamespace(
            indexOfSignal=lambda signature: 33 if self.signals and signature == 'valueChanged()' else -1
        )


class Flag:
    """A QTimer used as a flag, faked: started by the signal it is connected to."""

    def __init__(self, parent: object = None) -> None:
        self.active = False

    def setSingleShot(self, single: bool) -> None:
        pass

    def setInterval(self, ms: int) -> None:
        pass

    def start(self) -> None:
        self.active = True

    def isActive(self) -> bool:
        return self.active


def _connect(sender: MapField, signal: str, receiver: Flag, member: str) -> None:
    """QObject.connect of a signal to a receiver's slot, both by signature, faked for a MapField's valueChanged() and a
    Flag's start(): a C++ slot, so no Python runs as the signal comes (REVIEW.md HLP-150)."""
    assert (signal, member) == ('valueChanged()', 'start()'), (signal, member)
    sender.slots.append(receiver.start)


# the maps' files, by size in bytes: the smallest isn't the first (REVIEW.md TST-538)
SIZES = {'airport': 1000, 'corsica_beach': 10, 'studio': 500}


def _drops(
    helpers: types.ModuleType,
    folder: Path,
    shown: str,
    taken: Callable[[str], bool] = lambda name: True,
    signals: bool = True,
    answers: list[bool] | None = None,
) -> list[str]:
    """The maps _drop_map drops when asked for studio, by name, faked: Designer's maps are SIZES' files in `folder`, and
    each one `taken` takes becomes the one `shown`, signalled by the field when it changes, as in Designer (the module
    docstring); `signals`: whether the field has that signal. What _drop_map returns goes in `answers`, when given."""
    maps = {name: str(folder / (name + '.exr')) for name in SIZES}
    for name, path in maps.items():
        Path(path).write_bytes(b'x' * SIZES[name])
    dropped: list[str] = []
    state = {'shown': shown}

    def drop(viewport: 'QtWidgets.QWidget', path: str) -> None:
        name = Path(path).stem
        dropped.append(name)
        if taken(name) and name != state['shown']:
            state['shown'] = name
            for slot in field.slots:
                slot()

    field = MapField(signals)
    vars(helpers)['_drop'] = drop
    vars(helpers)['_environment_maps'] = lambda: dict(maps)
    qt_core = qt('QtCore')
    qt_core.SIGNAL = qt_core.SLOT = lambda signature: signature
    qt_core.QObject.connect = _connect
    qt_core.QTimer = Flag
    answer = vars(helpers)['_drop_map'](object(), field, 'studio')
    if answers is not None:
        answers.append(answer)
    return dropped


def test_a_map_dropped_is_taken_once_its_field_says_it_changed(helpers: types.ModuleType, tmp_path: Path) -> None:
    answers: list[bool] = []
    assert _drops(helpers, tmp_path, shown='corsica_beach', answers=answers) == ['studio']
    assert answers == [True]  # the map changed


def test_the_map_already_shown_is_dropped_again_after_the_smallest_other(
    helpers: types.ModuleType, tmp_path: Path
) -> None:
    # no change, no signal: another map dropped first tells it from a drop not taken (the module docstring). The
    # smallest file, as Designer loads it within the drop
    answers: list[bool] = []
    assert _drops(helpers, tmp_path, shown='studio', answers=answers) == ['studio', 'corsica_beach', 'studio']
    assert answers == [False]  # the map asked again: the render as before


def test_the_map_dropped_first_is_said_before_its_drop(
    helpers: types.ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-191: an abort right after it left the 3D view on a map neither the user nor the call asked for,
    # with only the environment asked for said
    def aborted(name: str) -> bool:
        if name == 'corsica_beach':
            raise KeyboardInterrupt('an abort as the other map is dropped')
        return True

    with pytest.raises(KeyboardInterrupt):
        _drops(helpers, tmp_path, shown='studio', taken=aborted)
    assert capsys.readouterr().out == '3D view, setting: environment corsica_beach first, then studio again\n'


def test_a_drop_the_3d_view_doesnt_take_is_an_error(helpers: types.ModuleType, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match=r'^the 3D view took no environment map dropped on it$'):
        _drops(helpers, tmp_path, shown='studio', taken=lambda name: False)


def test_the_map_not_taken_back_after_another_says_the_one_shown(helpers: types.ModuleType, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match=r"^the 3D view didn't take studio again: it shows corsica_beach$"):
        _drops(helpers, tmp_path, shown='studio', taken=lambda name: name == 'corsica_beach')


def test_an_environment_field_with_no_valuechanged_is_refused_before_any_drop(
    helpers: types.ModuleType, tmp_path: Path
) -> None:
    # REVIEW.md HLP-189: no flag would ever start, so the maps dropped were taken unseen, and the error said none was
    def none(name: str) -> NoReturn:  # a BaseException, which the refusal expected doesn't catch
        pytest.fail('%s dropped' % name)

    with pytest.raises(
        RuntimeError, match=r'^the Environment field has no valueChanged\(\) signal, which says a map was taken$'
    ):
        _drops(helpers, tmp_path, shown='corsica_beach', taken=none, signals=False)


def test_a_field_with_fewer_spin_boxes_than_asked_is_refused_naming_it(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-191: a bare IndexError named no field. The panel holds the field, built with one spin box
    field = SimpleNamespace(objectName=lambda: '12-dome_rotation_angle', findChildren=lambda kind: [Spin()])
    with pytest.raises(
        RuntimeError,
        match=r"^the environment's Rotation Angle has no spin box 2 in the Parameters panel \(it has 1\)$",
    ):
        helpers._panel_spin(
            SimpleNamespace(findChildren=lambda kind: [field]),
            'dome_rotation_angle',
            "the environment's Rotation Angle",
            [],
            1,
        )


def test_the_environment_said_is_what_its_spin_boxes_show(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-538: the rotation goes to the Degrees spin box, the second; the line says what the spin boxes show
    qt('QtCore').QMetaObject.invokeMethod.return_value = True
    spins = {('dome_rotation_angle', 1): Spin(45.0), ('intensity', 0): Spin(1.25)}
    asked: list[tuple[str, int]] = []
    dropped: list[str] = []

    def field(params: 'QtWidgets.QDockWidget', name: str, what: str, keep: list['Kept'], spins: int = 1) -> MapField:
        asked.append((name, spins))
        return MapField()

    def spin(params: 'QtWidgets.QDockWidget', name: str, what: str, keep: list['Kept'], index: int = 0) -> Spin:
        asked.append((name, index))
        return spins[name, index]

    vars(helpers)['_menu_action'] = lambda bar, keep, *path: SimpleNamespace(trigger=lambda: None)
    vars(helpers)['_panel_field'] = field
    vars(helpers)['_panel_spin'] = spin
    vars(helpers)['_drop_map'] = lambda viewport, field, name: dropped.append(name)
    vars(helpers)['_parameters_back'] = lambda: 'the Parameters panel back on g'
    said, changed = helpers._set_environment(panel('g'), object(), object(), 'studio', 90.0, 1.0, [], Frames([]))
    assert said == 'environment studio, rotation 45 degrees, exposure 1.25 (the Parameters panel back on g)'
    assert changed  # values committed
    assert asked == [('environment_texture_name', 0), ('dome_rotation_angle', 1), ('intensity', 0)]
    assert dropped == ['studio']
    assert spins['dome_rotation_angle', 1].set == [90.0] and spins['intensity', 0].set == [1.0]


def _panel_steps(helpers: types.ModuleType) -> Designer:
    """set_3d_view's Designer, faked, with the real steps through the Parameters panel (_set_tiling, _set_environment):
    each change of the tiling or the environment recorded in its events as ('change', (what,)), the Parameters panel's
    fields faked, each spin box showing 2.5."""
    real = helpers._set_tiling, helpers._set_environment
    designer = Designer(helpers)
    vars(helpers)['_set_tiling'], vars(helpers)['_set_environment'] = real
    vars(helpers)['_in_properties'] = lambda params, show, setting, properties: setting()
    vars(helpers)['_panel_field'] = lambda params, name, what, keep, spins=1: MapField()
    vars(helpers)['_panel_spin'] = lambda params, name, what, keep, index=0: Spin()

    def drop_map(viewport: 'QtWidgets.QWidget', field: MapField, name: str) -> bool:
        designer.events.append(('change', ('map', name)))
        return True  # taken at its first drop

    vars(helpers)['_drop_map'] = drop_map

    def commit(spin: Spin, value: float, what: str) -> None:
        designer.events.append(('change', (what,)))
        spin.shows = value  # taken

    vars(helpers)['_commit'] = commit
    return designer


@pytest.mark.parametrize(
    'options, changed',
    [
        ({'tiling': 2.0}, 1),
        # REVIEW.md HLP-192: one wait, from before the map's drop, ended before the exposure's change was drawn: the
        # view was back at rest between the changes
        ({'environment': 'studio', 'environment_rotation': 90.0, 'environment_exposure': 1.0}, 3),
    ],
    ids=['tiling', 'environment'],
)
def test_each_change_through_the_parameters_panel_is_waited_for_from_just_before_it(
    helpers: types.ModuleType, options: View3dOptions, changed: int
) -> None:
    designer = _panel_steps(helpers)
    helpers.set_3d_view(**options)
    changes = [i for i, (kind, _) in enumerate(designer.events) if kind == 'change']
    waits = [i for i, (kind, _) in enumerate(designer.events) if kind == 'wait']
    # the fake's mark is the index the next event gets: each change marked right before it, and waited for after it
    assert len(changes) == changed and designer.frames.settled_since == changes, designer.events
    assert waits == [i + 1 for i in changes], designer.events


@pytest.mark.parametrize(
    'options, shown',
    [
        # REVIEW.md HLP-195: committed again, its wait ran to its limit (1.5 s measured), the view drawing nothing
        ({'tiling': 2.0}, {('$tiling', 0): 2.0}),
        (
            {'environment_rotation': 90.0, 'environment_exposure': 1.0},
            {('dome_rotation_angle', 1): 90.0, ('intensity', 0): 1.0},
        ),
    ],
    ids=['tiling', 'environment'],
)
def test_a_value_the_parameters_panel_shows_already_is_neither_committed_nor_waited_for(
    helpers: types.ModuleType, options: View3dOptions, shown: dict[tuple[str, int], float]
) -> None:
    designer = _panel_steps(helpers)
    vars(helpers)['_panel_spin'] = lambda params, name, what, keep, index=0: Spin(shown[name, index])
    helpers.set_3d_view(**options)
    assert [e for e in designer.events if e[0] in ('change', 'wait')] == [], designer.events


@pytest.mark.parametrize(
    'options, shown, changed',
    [
        ({'tiling': 2.0}, None, True),
        ({'tiling': 2.0}, 2.0, False),
        ({'environment_exposure': 1.0}, None, True),
        ({'environment_exposure': 1.0}, 1.0, False),
        # REVIEW.md TST-552: 0 is a value set, not one left out
        ({'environment_rotation': 0.0}, None, True),
        ({'environment_exposure': 0.0}, None, True),
        ({'mesh': 'Sphere'}, None, True),
        ({'orbit': [90.0, 0.0]}, None, True),
        ({'zoom': 2}, None, True),
        ({'view': 'Top'}, None, False),
        ({'graph': 'g'}, None, False),
    ],
    ids=[
        'a tiling',
        'a tiling shown already',
        'an exposure',
        'an exposure shown already',
        'a rotation of 0',
        'an exposure of 0',
        'a mesh switch',
        'an orbit',
        'a zoom',
        'a view',
        'a graph',
    ],
)
def test_a_set_up_says_whether_it_changed_what_the_view_shows(
    helpers: types.ModuleType, options: View3dOptions, shown: float | None, changed: bool
) -> None:
    # the user's ask (2026-11-18): the shot compares its render with the one before only after such a change, the light
    # and the tiling as the camera. A view or a graph may be what is shown already, so they are no sign
    _panel_steps(helpers)
    if shown is not None:
        vars(helpers)['_panel_spin'] = lambda params, name, what, keep, index=0: Spin(shown)
    assert helpers._3d_set_up(**options)(None, None) is changed


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
        ({'view': 'Top'}, False, False),
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


@pytest.mark.parametrize(
    'taken, changed', [(True, True), (False, False)], ids=['taken at its first drop', 'asked again']
)
def test_a_map_changes_what_the_view_shows_only_when_taken_at_its_first_drop(
    helpers: types.ModuleType, taken: bool, changed: bool
) -> None:
    # asked again, the map shown is dropped after another: the render comes back as it was
    _panel_steps(helpers)
    vars(helpers)['_drop_map'] = lambda viewport, field, name: taken
    assert helpers._3d_set_up(environment='studio')(None, None) is changed


def test_a_map_asked_again_isnt_waited_for(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-201: dropped back after another, the map shown restarted nothing, and its wait ran to its limit
    # (0.95 s measured)
    designer = _panel_steps(helpers)
    vars(helpers)['_drop_map'] = lambda viewport, field, name: False
    helpers.set_3d_view(environment='studio')
    assert [e for e in designer.events if e[0] == 'wait'] == [], designer.events


def test_a_mesh_shown_already_is_neither_picked_again_nor_waited_for(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-195: picked again, it restarted nothing, and its wait ran to its limit (1.0 s measured)
    designer = Designer(helpers)
    designer.checked.add(('Scene', 'Sphere'))
    helpers.set_3d_view(mesh='Sphere')
    assert [e for e in designer.events if e[0] in ('trigger', 'wait')] == [], designer.events
    assert '3D view: Sphere\n' in capsys.readouterr().out


@pytest.mark.parametrize(
    'options, said',
    [({'tiling': 2.0}, 'tiling 2'), ({'environment_rotation': 90.0}, 'rotation 90 degrees')],
    ids=['tiling', 'environment'],
)
def test_a_wait_failing_after_a_commit_says_what_was_set(
    helpers: types.ModuleType, options: View3dOptions, said: str
) -> None:
    designer = _panel_steps(helpers)
    designer.frames.settle_error = 'the view took no frame'
    with pytest.raises(RuntimeError) as raised:
        helpers.set_3d_view(**options)
    assert str(raised.value).startswith('the view took no frame;') and said in str(raised.value), raised.value


@pytest.mark.parametrize(
    'options, said',
    [
        ({'mesh': 'Sphere'}, 'Sphere'),
        ({'graph': 'g'}, "graph g's outputs on the mesh"),
        ({'view': 'Top'}, 'view Top, framed'),  # an error in Frame's wait: the fake's moved() doesn't raise
        ({'environment': 'studio'}, 'environment studio'),
    ],
    ids=['a mesh', 'a graph', 'a view', 'a map'],
)
def test_a_wait_failing_after_a_steps_change_says_it_was_set(
    helpers: types.ModuleType, options: View3dOptions, said: str
) -> None:
    # REVIEW.md HLP-200: each step was said once its wait ended, so an error in that wait left out the change made
    designer = _panel_steps(helpers)
    designer.frames.settle_error = 'the view took no frame'
    with pytest.raises(RuntimeError) as raised:
        helpers.set_3d_view(**options)
    assert str(raised.value).startswith('the view took no frame;') and said in str(raised.value), raised.value


def test_an_error_after_the_maps_drop_says_the_environment_set_so_far(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-193: the 3D view showed the map, and the error said only that the rotation's spin box was missing
    _panel_steps(helpers)

    def missing(params: 'QtWidgets.QDockWidget', name: str, what: str, keep: list['Kept'], index: int = 0) -> NoReturn:
        raise RuntimeError('%s has no spin box 2 in the Parameters panel (it has 1)' % what)

    vars(helpers)['_panel_spin'] = missing
    with pytest.raises(RuntimeError) as raised:
        helpers.set_3d_view(environment='studio', environment_rotation=90.0)
    assert str(raised.value) == (
        "the environment's Rotation Angle has no spin box 2 in the Parameters panel (it has 1); environment studio set"
    )


@pytest.mark.parametrize(
    'step, shows',
    [('_set_tiling', "the 3D material's properties"), ('_set_environment', "the environment's properties")],
)
def test_with_no_graph_in_the_editor_the_panel_is_said_to_show_what_was_set(
    helpers: types.ModuleType, step: str, shows: str
) -> None:
    # REVIEW.md HLP-190: the environment's step said the panel showed the 3D material's properties
    qt('QtCore').QMetaObject.invokeMethod.return_value = True
    vars(helpers)['_current_graph'] = lambda: None
    vars(helpers)['_menu_action'] = lambda bar, keep, *path: SimpleNamespace(trigger=lambda: None)
    vars(helpers)['_material'] = lambda bar, keep: 'Default'
    vars(helpers)['_panel_spin'] = lambda params, name, what, keep, index=0: Spin()
    if step == '_set_tiling':
        said, _ = helpers._set_tiling(panel(), object(), 2.0, [], Frames([]))
    else:
        said, _ = helpers._set_environment(panel(), object(), object(), None, None, 1.0, [], Frames([]))
    assert said.endswith(' (the Parameters panel shows %s)' % shows), said


def test_the_parameters_panel_is_turned_back_when_setting_the_environment_fails(helpers: types.ModuleType) -> None:
    # as after the tiling (the module docstring): it showed the environment, turned to it by Edit properties
    events: list[str] = []
    vars(helpers)['_menu_action'] = lambda bar, keep, *path: SimpleNamespace(trigger=lambda: events.append(path[0]))
    vars(helpers)['_panel_field'] = lambda params, name, what, keep, spins=1: MapField()

    def failing(viewport: 'QtWidgets.QWidget', field: MapField, name: str) -> None:
        raise RuntimeError('the 3D view took no environment map dropped on it')

    vars(helpers)['_drop_map'] = failing
    vars(helpers)['_switched'] = lambda params, shown: events.append('switched')

    def parameters_back() -> str:
        events.append('back')
        return 'the Parameters panel back on g'

    vars(helpers)['_parameters_back'] = parameters_back
    with pytest.raises(RuntimeError, match='took no environment map'):
        helpers._set_environment(panel('g'), object(), object(), 'studio', 90.0, None, [], Frames([]))
    assert events == ['Environment', 'switched', 'back']


def test_tiling_with_a_mesh_doesnt_count_the_materials_of_the_mesh_it_replaces(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-114: the mesh shown had two; the Plane has one
    designer = Designer(helpers)

    def two(bar: 'QtWidgets.QMenuBar', keep: list['Kept']) -> str:
        raise RuntimeError("the 3D view's mesh has 2 materials: A, B; tiling= sets the material of a mesh with one")

    vars(helpers)['_material'] = two
    helpers.set_3d_view(mesh='Plane', tiling=2.0)
    assert ('tiling', '2.0') in designer.triggered()
    with pytest.raises(RuntimeError, match='2 materials'):
        helpers.set_3d_view(tiling=2.0)


def test_an_abort_after_a_change_says_what_was_set_and_goes_on(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-113: the plugin's abort is a BaseException, raised again unchanged so the plugin reports it
    Designer(helpers)

    def aborted(tree: 'QtWidgets.QTreeView', g: 'SDSBSCompGraph', keep: list['Kept']) -> None:
        raise KeyboardInterrupt('an abort as the outputs are applied')

    vars(helpers)['_apply_outputs'] = aborted
    with pytest.raises(KeyboardInterrupt, match='an abort as the outputs are applied'):
        helpers.set_3d_view('g', 'Plane', 'Top')
    assert capsys.readouterr().out == "3D view, setting: Plane\n3D view, setting: graph g's outputs on the mesh\n"


def test_an_abort_during_a_steps_wait_says_that_step(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-116: the mesh changed, then the abort in the wait after it: most of a set-up's time is its waits
    designer = Designer(helpers)
    designer.frames.abort_at = 1
    with pytest.raises(KeyboardInterrupt):
        helpers.set_3d_view(mesh='Plane')
    assert capsys.readouterr().out == '3D view, setting: Plane\n'
    assert designer.frames.closed


def test_an_abort_in_the_last_wait_says_each_step_begun(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-116: the waits after the mesh, the view's turn, then its Frame, the last one
    designer = Designer(helpers)
    designer.frames.abort_at = 3
    with pytest.raises(KeyboardInterrupt):
        helpers.set_3d_view(mesh='Plane', view='Top')
    assert capsys.readouterr().out.splitlines() == ['3D view, setting: Plane', '3D view, setting: view Top, framed']
    assert designer.frames.closed


@pytest.mark.parametrize('shot', [False, True], ids=['set up on its own', "in a shot, on the shot's watch"])
def test_the_cameras_turn_is_watched_with_designers_window_on_screen(helpers: types.ModuleType, shot: bool) -> None:
    # REVIEW.md HLP-158 (the user's choice, 2026-11-16): off screen the view draws no frame, nothing says the turn
    # ended, and Frame at once cancels it. Set up on its own, the viewpoint and Frame run with Designer's window on
    # screen, transparent, as the 3D shot shows it (_on_screen); in a shot, the window is on screen already
    designer = _watched_on_screen(helpers)
    if shot:
        helpers._3d_set_up(view='Top')(lambda: designer.events.append(('screen', ('again',))), designer.frames)
    else:
        helpers.set_3d_view(view='Top')
    seen = [path if kind == 'trigger' else path[0] for kind, path in designer.events if kind != 'lookup']
    # REVIEW.md HLP-163: off screen nothing says the turn ended, so moved() ends there; the look after it puts the
    # window back on screen and waits for the view there, before Frame
    turn = [('Camera', 'Top'), 'moved', 'again', ('Camera', 'Frame'), 'settled']
    if shot:
        assert seen == ['again', *turn], seen
    else:
        assert seen == ['on screen', *turn, 'put back'], seen


def _watched_on_screen(helpers: types.ModuleType) -> Designer:
    """set_3d_view's Designer, faked, with the window put on screen (_on_screen) recorded in its events: ('screen',
    ('on screen',)), the shot's look before each step ('screen', ('again',)), ('screen', ('put back',))."""
    designer = Designer(helpers)

    def again() -> None:
        designer.events.append(('screen', ('again',)))

    @contextlib.contextmanager
    def on_screen(mw: 'QtWidgets.QMainWindow', frames: Frames) -> Iterator[SimpleNamespace]:
        assert frames is designer.frames
        designer.events.append(('screen', ('on screen',)))
        try:
            yield SimpleNamespace(again=again)
        finally:
            designer.events.append(('screen', ('put back',)))

    vars(helpers)['_on_screen'] = on_screen
    return designer


@pytest.mark.parametrize(
    'options, shown',
    [
        # REVIEW.md HLP-168 (the user's choice, 2026-11-16): off screen, the same moves from the same start came out
        # differently between runs (a pan 68.5 grey levels apart in 1 of 2); on screen they repeated exactly
        ({'orbit': [90.0, 0.0]}, True),
        ({'pan': [0.25, 0.0]}, True),
        ({'zoom': 2}, True),
        ({'mesh': 'Sphere', 'orbit': [90.0, 0.0]}, True),
        # REVIEW.md HLP-196, HLP-197 (the user's choices, 2026-11-18): off screen, graph='s Explorer menu unhid a hidden
        # Designer and left it up, and a tiling after a mesh switch, in that call or the next, had its field deleted
        ({'graph': 'g'}, True),
        ({'mesh': 'Sphere'}, True),
        ({'mesh': 'Sphere', 'tiling': 2.0}, True),
        # none of these: off screen, but for a viewpoint's turn (HLP-158)
        ({'view': 'Top'}, False),
        ({'tiling': 2.0}, False),
        ({'environment_exposure': 1.0}, False),
    ],
    ids=[
        'orbit',
        'pan',
        'zoom',
        'a mesh and an orbit',
        'graph',
        'a mesh',
        'a mesh and a tiling',
        'a view',
        'a tiling',
        'an exposure',
    ],
)
def test_a_set_up_that_moves_the_camera_puts_outputs_on_or_switches_the_mesh_runs_with_designers_window_on_screen(
    helpers: types.ModuleType, options: View3dOptions, shown: bool
) -> None:
    designer = _watched_on_screen(helpers)
    helpers.set_3d_view(**options)
    seen = [path if kind == 'trigger' else path[0] for kind, path in designer.events if kind != 'lookup']
    if shown:  # whole, the shot's look before each step
        assert seen[:2] == ['on screen', 'again'] and seen[-1] == 'put back' and seen.count('on screen') == 1, seen
    else:
        assert seen[:2] != ['on screen', 'again'] and seen.count('on screen') == ('view' in options), seen
    assert designer.frames.closed


def test_a_mesh_shown_already_with_a_tiling_runs_off_screen(helpers: types.ModuleType) -> None:
    # no switch: nothing for the view to take before the tiling (HLP-195 skips the mesh step)
    designer = _watched_on_screen(helpers)
    designer.checked.add(('Scene', 'Sphere'))
    helpers.set_3d_view(mesh='Sphere', tiling=2.0)
    assert ('screen', ('on screen',)) not in designer.events, designer.events


@pytest.mark.parametrize(
    'options, waits',
    [
        ({'mesh': 'Sphere'}, [('Scene', 'Sphere'), 'settled']),
        ({'graph': 'g'}, [('outputs', 'g'), 'settled']),
        ({'view': 'Top'}, [('Camera', 'Top'), 'moved', ('Camera', 'Frame'), 'settled']),
        # REVIEW.md HLP-149: each drag and wheel step waits for the view to take it, also off screen, where it draws no
        # frame: sent back to back there, they were lost
        ({'orbit': [90.0, 0.0]}, [('drag', 'left', '-200', '0'), 'taken', 'settled']),
        ({'zoom': 2}, [('wheel', '2'), 'taken', 'taken', 'settled']),
        ({'tiling': 2.0}, [('tiling', '2.0'), 'settled']),
        ({'environment': 'studio'}, [('environment', 'studio', 'None', 'None'), 'settled']),
    ],
    ids=['mesh', 'graph', 'view', 'orbit', 'zoom', 'tiling', 'environment'],
)
def test_each_step_waits_for_the_3d_view_to_take_it(
    helpers: types.ModuleType, options: View3dOptions, waits: list[tuple[str, ...] | str]
) -> None:
    # REVIEW.md HLP-148: on the view's frames, never a fixed time (frames3d.py); a set-up of its own stops watching
    designer = Designer(helpers)
    helpers.set_3d_view(**options)
    seen = [path if kind == 'trigger' else path[0] for kind, path in designer.events if kind in ('trigger', 'wait')]
    assert [step for step in seen if step != ('tool', 'Camera') and step != ('tool', 'Light')] == waits
    assert designer.frames.closed


def test_a_set_up_given_the_shots_frames_leaves_them_watching(helpers: types.ModuleType) -> None:
    designer = Designer(helpers)
    run = helpers._3d_set_up(mesh='Sphere')
    run(None, designer.frames)
    assert not designer.frames.closed and ('wait', ('settled',)) in designer.events


def test_an_api_error_after_a_change_says_what_was_set(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-117: the sd API's error is a BaseException, not an abort
    Designer(helpers)

    def refused(tree: 'QtWidgets.QTreeView', g: 'SDSBSCompGraph', keep: list['Kept']) -> None:
        raise helpers.APIException('the API refused')

    vars(helpers)['_apply_outputs'] = refused
    with pytest.raises(RuntimeError) as raised:
        helpers.set_3d_view('g', 'Plane')
    assert str(raised.value) == 'the API refused; the 3D view was already set: Plane'


@pytest.mark.parametrize(
    'step, options',
    [('_set_tiling', {'tiling': 2.0}), ('_set_environment', {'environment_rotation': 90.0})],
    ids=['tiling', 'environment'],
)
def test_an_abort_escaping_a_step_through_the_parameters_panel_turns_it_back(
    helpers: types.ModuleType, step: str, options: View3dOptions
) -> None:
    # REVIEW.md HLP-118: one landing on the step's finally's first line skips its turn-back; the abort's handler, run
    # untraced, turns it back
    Designer(helpers)
    back: list[str] = []

    def aborted(*args: object) -> str:
        raise KeyboardInterrupt('an abort as the step ends')

    def parameters_back() -> str:
        back.append('back')
        return 'the Parameters panel back on g'

    vars(helpers)[step] = aborted
    vars(helpers)['_parameters_back'] = parameters_back
    with pytest.raises(KeyboardInterrupt):
        helpers.set_3d_view(**options)
    assert back == ['back']


def test_an_abort_while_the_menus_are_looked_up_says_nothing(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    designer = Designer(helpers)

    def aborted(bar: 'QtWidgets.QMenuBar', keep: list['Kept'], *path: str) -> NoReturn:
        raise KeyboardInterrupt('an abort as the menus are looked up')

    vars(helpers)['_menu_action'] = aborted
    with pytest.raises(KeyboardInterrupt):
        helpers.set_3d_view('g', 'Plane')
    assert capsys.readouterr().out == '' and designer.triggered() == []


def test_the_3d_view_before_any_graph_was_opened_is_said(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-115: Designer builds its menu bar and viewport once a graph is opened
    vars(helpers)['_visible_dock'] = lambda mw, area: SimpleNamespace(findChildren=lambda cls: [])
    with pytest.raises(RuntimeError, match=r"the 3D view isn't built yet: .*open_graph"):
        helpers._3d_dock(object())


def test_an_error_after_a_change_says_what_was_set(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-107
    Designer(helpers)

    def failing(tree: 'QtWidgets.QTreeView', g: 'SDSBSCompGraph', keep: list['Kept']) -> None:
        raise RuntimeError("the Explorer's menu for graph g didn't open")

    vars(helpers)['_apply_outputs'] = failing
    with pytest.raises(RuntimeError) as raised:
        helpers.set_3d_view('g', 'Plane', 'Top')
    assert str(raised.value) == "the Explorer's menu for graph g didn't open; the 3D view was already set: Plane"


EVERY_OPTION = ('g', 'Plane', 'Top', 2, 2.0, [90.0, 30.0], [0.25, -0.4], 'studio', 90.0, 1.0)


def test_the_line_says_what_was_set(helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    Designer(helpers)
    helpers.set_3d_view(*EVERY_OPTION)
    assert capsys.readouterr().out.splitlines()[-1] == (
        "3D view: Plane, graph g's outputs on the mesh, view Top, framed, orbit 90 degrees right, 30.1 up, "
        'pan 0.25 of the view right, 0.401 down, +2 wheel steps, tiling 2, '
        'environment studio, rotation 90 degrees, exposure 1'
    )


def test_each_step_is_said_before_its_change(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-119: an abort anywhere after a change finds it said; one before it finds the step said as begun
    designer = Designer(helpers)
    vars(helpers)['print'] = lambda line: designer.events.append(('print', (line,)))
    helpers.set_3d_view(*EVERY_OPTION)
    said = [(kind, path) for kind, path in designer.events if kind in ('print', 'trigger')]
    assert said == [
        ('print', ('3D view, setting: Plane',)),
        ('trigger', ('Scene', 'Plane')),
        ('print', ("3D view, setting: graph g's outputs on the mesh",)),
        ('trigger', ('outputs', 'g')),
        ('print', ('3D view, setting: view Top, framed',)),
        ('trigger', ('Camera', 'Top')),
        ('trigger', ('Camera', 'Frame')),
        ('print', ('3D view, setting: orbit 90 degrees right, 30.1 up',)),
        ('trigger', ('drag', 'left', '-200', '0')),
        ('trigger', ('drag', 'left', '0', '86')),
        ('print', ('3D view, setting: pan 0.25 of the view right, 0.401 down',)),
        ('trigger', ('drag', 'middle', '-89', '0')),
        ('trigger', ('drag', 'middle', '0', '-107')),
        ('print', ('3D view, setting: +2 wheel steps',)),
        ('trigger', ('wheel', '2')),
        ('print', ('3D view, setting: tiling 2',)),
        ('trigger', ('tiling', '2.0')),
        ('print', ('3D view, setting: environment studio, rotation 90 degrees, exposure 1',)),
        ('trigger', ('environment', 'studio', '90.0', '1.0')),
        (
            'print',
            (
                "3D view: Plane, graph g's outputs on the mesh, view Top, framed, orbit 90 degrees right, 30.1 up, "
                'pan 0.25 of the view right, 0.401 down, +2 wheel steps, tiling 2, '
                'environment studio, rotation 90 degrees, exposure 1',
            ),
        ),
    ]


def test_the_set_up_runs_the_shots_look_at_the_active_app_before_each_step(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-136: the 3D shot's look whether the user made Designer the active app (shot3d.py), before each step
    designer = Designer(helpers)
    vars(helpers)['print'] = lambda line: designer.events.append(('print', (line,)))
    run = helpers._3d_set_up(*EVERY_OPTION)
    run(lambda: designer.events.append(('between', ())), designer.frames)
    said = [event for event in designer.events if event[0] in ('print', 'between')]
    steps = [i for i, (kind, line) in enumerate(said) if kind == 'print' and line[0].startswith('3D view, setting: ')]
    assert len(steps) == 8 and all(said[i - 1] == ('between', ()) for i in steps)


@pytest.mark.parametrize(
    'options',
    [{'orbit': [90.0, 0.0], 'pan': [0.25, 0.0]}, {'orbit': [90.0, 0.0], 'zoom': 2}, {'pan': [0.25, 0.0]}],
    ids=['orbit then pan', 'orbit then zoom', 'pan alone'],
)
def test_the_moves_wait_from_a_mark_taken_after_the_look_before_the_last_of_them(
    helpers: types.ModuleType, options: View3dOptions
) -> None:
    # REVIEW.md HLP-161: the look before a step (`between`) brings the window back on screen if it went off, and waits
    # for the view to restart and settle; from a mark taken before it, that restart ended the moves' wait
    designer = Designer(helpers)
    run = helpers._3d_set_up(**options)
    run(lambda: designer.events.append(('between', ())), designer.frames)
    looks = [i for i, event in enumerate(designer.events) if event == ('between', ())]
    moves = [i for i, (kind, path) in enumerate(designer.events) if kind == 'trigger' and path[0] in ('drag', 'wheel')]
    assert len(designer.frames.settled_since) == 1, designer.frames.settled_since
    assert looks[-1] < designer.frames.settled_since[0] <= min(i for i in moves if i > looks[-1]), designer.events


def _drags(designer: Designer) -> list[tuple[str, ...]]:
    return [path for path in designer.triggered() if path[0] == 'drag']


def test_orbit_and_pan_are_drags_at_designers_own_rates(helpers: types.ModuleType) -> None:
    # ROADMAP item 74: 0.45 degrees a pixel across, 0.35 up and down; the view's width panned every 356 pixels
    # (designer_helpers/view3d.py)
    designer = Designer(helpers)
    helpers.set_3d_view(view='Front', orbit=[90.0, 30.0], pan=[0.25, -0.4])
    assert _drags(designer) == [
        ('drag', 'left', '-200', '0'),  # the camera right: the mouse left
        ('drag', 'left', '0', '86'),  # up: the mouse down
        ('drag', 'middle', '-89', '0'),  # the view right: the content, which follows the mouse, left
        ('drag', 'middle', '0', '-107'),  # 0.4 of the 300 px high view down: 120 px, 356 px a 400 px wide view
    ]


def test_a_turn_or_pan_of_zero_is_no_drag(helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    designer = Designer(helpers)
    helpers.set_3d_view(orbit=[0.0, -20.0], pan=[0.5, 0.0])
    assert _drags(designer) == [('drag', 'left', '0', '-57'), ('drag', 'middle', '-178', '0')]
    assert capsys.readouterr().out.splitlines()[-1] == '3D view: orbit 19.9 degrees down, pan 0.5 of the view right'


@pytest.mark.parametrize(
    'options',
    [
        {'orbit': [0.2, 0.0]},
        {'orbit': [0.1, 30.0]},
        {'orbit': [0.0, -0.1]},
        {'pan': [0.001, 0.0]},
        {'pan': [0.3, 0.0005]},
    ],
    ids=['across', 'across with a turn up', 'down', 'right', 'up with a pan right'],
)
def test_a_turn_or_pan_under_a_pixel_is_refused_before_anything_changes(
    helpers: types.ModuleType, options: View3dOptions
) -> None:
    # REVIEW.md HLP-121: rounded to no pixel, it was dropped and said as set ('3D view: ' alone for orbit=[0.2, 0])
    designer = Designer(helpers)
    with pytest.raises(RuntimeError, match="less than one pixel's drag"):
        helpers.set_3d_view(mesh='Plane', **options)
    assert designer.triggered() == []


def test_the_turn_and_pan_said_are_what_the_drags_carry(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-121: 10 degrees is 22 px, 9.9 degrees; 20 up is 57 px, 19.95; 0.4 of the 300 px high view down is
    # 107 px, 0.401 of it
    Designer(helpers)
    helpers.set_3d_view(orbit=[10.0, 20.0], pan=[0.25, -0.4])
    assert capsys.readouterr().out.splitlines()[-1] == (
        '3D view: orbit 9.9 degrees right, 19.9 up, pan 0.25 of the view right, 0.401 down'
    )


@pytest.mark.parametrize(
    'options', [{'orbit': [90.0, 0.0]}, {'pan': [0.25, 0.0]}, {'zoom': 2}], ids=['orbit', 'pan', 'zoom']
)
def test_under_the_light_tool_the_camera_tool_moves_the_camera_then_the_light_tool_comes_back(
    helpers: types.ModuleType, options: View3dOptions
) -> None:
    # REVIEW.md HLP-120: under the Light tool, drags and the wheel don't move the camera; zoom= said it zoomed
    designer = Designer(helpers, tool='Light')
    helpers.set_3d_view(view='Top', **options)
    triggered = designer.triggered()
    moves = [i for i, path in enumerate(triggered) if path[0] in ('drag', 'wheel')]
    assert moves and triggered[moves[0] - 1] == ('tool', 'Camera') and triggered[moves[-1] + 1] == ('tool', 'Light')
    assert [path for path in triggered if path[0] == 'tool'] == [('tool', 'Camera'), ('tool', 'Light')]
    assert designer.tool == 'Light'


def test_under_the_camera_tool_no_tool_is_selected(helpers: types.ModuleType) -> None:
    designer = Designer(helpers)
    helpers.set_3d_view(view='Top', orbit=[90.0, 0.0], pan=[0.25, 0.0], zoom=2)
    assert [path for path in designer.triggered() if path[0] == 'tool'] == []


def test_without_orbit_pan_or_zoom_the_tools_are_left_alone(helpers: types.ModuleType) -> None:
    designer = Designer(helpers, tool='Light', tools=())
    helpers.set_3d_view('g', 'Plane', 'Top', tiling=2.0)  # no toolbar needed either
    assert [path for path in designer.triggered() if path[0] == 'tool'] == []


def test_a_toolbar_without_the_camera_tool_is_refused_before_anything_changes(helpers: types.ModuleType) -> None:
    designer = Designer(helpers, tools=('Selection', 'Light'))
    with pytest.raises(RuntimeError, match="the 3D view's toolbar has no Camera tool"):
        helpers.set_3d_view(mesh='Plane', zoom=2)
    assert designer.triggered() == []


def test_the_light_tool_comes_back_when_a_drag_fails(helpers: types.ModuleType) -> None:
    designer = Designer(helpers, tool='Light')

    def failing(
        viewport: 'QtWidgets.QWidget',
        button: 'QtCore.Qt.MouseButton',
        dx: int,
        dy: int,
        pressed: 'Pressed',
        taken: Callable[[], Callable[[], bool]] | None,
    ) -> None:
        raise RuntimeError('a drag failed')

    vars(helpers)['_drag'] = failing
    with pytest.raises(RuntimeError) as raised:
        helpers.set_3d_view(view='Top', orbit=[90.0, 0.0])
    assert str(raised.value) == 'a drag failed; the 3D view was already set: view Top, framed'
    assert designer.tool == 'Light'


def test_an_abort_landing_as_the_light_tool_comes_back_brings_it_back(helpers: types.ModuleType) -> None:
    # as HLP-118 for the Parameters panel: one landing on the finally's first line skips its way back; the abort's
    # handler, run untraced, takes it again
    designer = Designer(helpers, tool='Light')
    real = helpers._tool_back
    calls: list[int] = []

    def tool_back(light: 'QtGui.QAction', switched: bool) -> None:
        calls.append(1)
        if len(calls) == 1:
            raise KeyboardInterrupt('an abort as the Light tool comes back')
        real(light, switched)

    vars(helpers)['_tool_back'] = tool_back
    with pytest.raises(KeyboardInterrupt):
        helpers.set_3d_view(zoom=2)
    assert designer.tool == 'Light'


def test_an_abort_that_skipped_a_drags_release_releases_its_button(helpers: types.ModuleType) -> None:
    Designer(helpers)
    released: Pressed = []

    def aborted(
        viewport: 'QtWidgets.QWidget',
        button: 'QtCore.Qt.MouseButton',
        dx: int,
        dy: int,
        pressed: 'Pressed',
        taken: Callable[[], Callable[[], bool]] | None,
    ) -> None:
        pressed.append((button, 0.0, 57.0))  # pressed, then the abort landing before its release
        raise KeyboardInterrupt('an abort in a drag')

    vars(helpers)['_drag'] = aborted
    vars(helpers)['_release'] = lambda viewport, button, x, y: released.append((button, x, y))
    with pytest.raises(KeyboardInterrupt):
        helpers.set_3d_view(orbit=[0.0, 20.0])
    assert released == [(qt('QtCore').Qt.MouseButton.LeftButton, 0.0, 57.0)]


class Mouse:
    """What _drag does to a 400 x 300 viewport, faked: (what, x, y) each, what its mouse events (press, move, release),
    'mark' and 'taken' (the wait for the view to take it: before the press, and after the release), 'guard on' or
    'guard off' (the filter for the user's mouse installed or removed)."""

    def __init__(self, fail_at_move: int = 0) -> None:
        self.sent: list[tuple[str, float, float]] = []
        core = qt('QtCore')
        self.kinds = {
            id(core.QEvent.Type.MouseButtonPress): 'press',
            id(core.QEvent.Type.MouseMove): 'move',
            id(core.QEvent.Type.MouseButtonRelease): 'release',
        }
        self.fail_at_move = fail_at_move
        self.pressed: Pressed = []  # the `pressed` handed to _drag
        self.held: list[Pressed] = []  # what it held at each mouse event
        self.viewport = SimpleNamespace(
            width=lambda: 400,
            height=lambda: 300,
            mapToGlobal=lambda point: point,
            installEventFilter=lambda guard: self.sent.append(('guard on', 0.0, 0.0)),
            removeEventFilter=lambda guard: self.sent.append(('guard off', 0.0, 0.0)),
        )

    def mouse(
        self,
        viewport: 'QtWidgets.QWidget',
        kind: 'QtCore.QEvent.Type',
        x: float,
        y: float,
        button: 'QtCore.Qt.MouseButton',
        buttons: 'QtCore.Qt.MouseButton',
    ) -> None:
        self.sent.append((self.kinds[id(kind)], x, y))
        self.held.append(list(self.pressed))
        if self.kinds[id(kind)] == 'move' and sum(what == 'move' for what, _, _ in self.sent) == self.fail_at_move:
            raise RuntimeError('a move failed')

    def what(self) -> list[str]:
        return [what for what, _, _ in self.sent]


def test_a_drag_is_a_press_moves_and_a_release_from_the_middle_then_the_wait_for_the_view_all_guarded(
    helpers: types.ModuleType,
) -> None:
    # the wait: a drag right after another cancelled it, or part of it; the guard: the user's mouse moving over the
    # viewport in a drag stopped it (REVIEW.md HLP-122), and a press before the view took it would undo it
    # (designer_helpers/view3d.py)
    mouse = Mouse()
    vars(helpers)['_mouse'] = mouse.mouse
    pressed: Pressed = []

    # the mark before the press, then the wait for the view to take the drag: its next frame, or off screen its next
    # UpdateRequest, which can come while the drag's own events run (REVIEW.md HLP-148, HLP-164)
    def taking() -> Callable[[], bool]:
        mouse.sent.append(('mark', 0.0, 0.0))

        def taken() -> bool:  # the wait _Frames.taking returns: whether the view took the drag
            mouse.sent.append(('taken', 0.0, 0.0))
            return True

        return taken

    helpers._drag(mouse.viewport, qt('QtCore').Qt.MouseButton.LeftButton, -200, 50, pressed, taking)
    moves = ['move'] * helpers.DRAG_MOVES
    assert mouse.what() == ['guard on', 'mark', 'press', *moves, 'release', 'taken', 'guard off']
    assert mouse.sent[2] == ('press', 200.0, 150.0) and mouse.sent[-4:-2] == [
        ('move', 0.0, 200.0),
        ('release', 0.0, 200.0),
    ]
    assert pressed == []


def test_a_drag_whose_move_fails_still_releases_its_button_and_removes_its_guard(helpers: types.ModuleType) -> None:
    mouse = Mouse(fail_at_move=3)
    vars(helpers)['_mouse'] = mouse.mouse
    pressed: Pressed = []
    with pytest.raises(RuntimeError, match='a move failed'):
        helpers._drag(mouse.viewport, qt('QtCore').Qt.MouseButton.MiddleButton, 100, 0, pressed)
    assert mouse.what()[-2:] == ['release', 'guard off'] and mouse.sent[-2] == ('release', 300.0, 150.0)
    assert pressed == []


def test_a_drag_holds_its_button_where_the_abort_handler_looks_while_it_is_down(helpers: types.ModuleType) -> None:
    # REVIEW.md TST-338: the abort's handler releases what `pressed` holds, at the drag's end
    mouse = Mouse()
    vars(helpers)['_mouse'] = mouse.mouse
    left = qt('QtCore').Qt.MouseButton.LeftButton
    helpers._drag(mouse.viewport, left, -200, 50, mouse.pressed)
    assert mouse.held == [[(left, 0.0, 200.0)]] * (helpers.DRAG_MOVES + 2)  # the press, every move, the release
    assert mouse.pressed == []


@pytest.mark.parametrize('fails', [False, True], ids=['sent', 'sending raises'])
def test_the_mouse_events_the_helpers_send_are_marked_for_the_guard_while_sent(
    helpers: types.ModuleType, fails: bool
) -> None:
    # REVIEW.md HLP-122: the drag's guard lets through only the events _mouse is sending
    marked: list[bool] = []

    def send(viewport: 'QtCore.QObject', event: 'QtCore.QEvent') -> None:
        marked.append(helpers._OWN_MOUSE[0])
        if fails:
            raise RuntimeError('sendEvent failed')

    qt('QtWidgets').QApplication.sendEvent.side_effect = send
    viewport = SimpleNamespace(mapToGlobal=lambda point: point)
    core = qt('QtCore')
    if fails:
        with pytest.raises(RuntimeError, match='sendEvent failed'):
            helpers._mouse(viewport, core.QEvent.Type.MouseMove, 1.0, 2.0, core.Qt.MouseButton.NoButton, 0)
    else:
        helpers._mouse(viewport, core.QEvent.Type.MouseMove, 1.0, 2.0, core.Qt.MouseButton.NoButton, 0)
    assert marked == [True] and helpers._OWN_MOUSE == [False]


class Spin:
    """A spin box of the Parameters panel, faked: the values set, and the one it `shows`, maybe not what was asked."""

    def __init__(self, shows: float = 2.5) -> None:
        self.set: list[float] = []
        self.shows = shows

    def setValue(self, value: float) -> None:
        self.set.append(value)

    def value(self) -> float:
        return self.shows


def _tiling(helpers: types.ModuleType, spin: 'Callable[[QtWidgets.QDockWidget, list[Kept]], Spin]') -> list[str]:
    """_set_tiling's Designer, faked; the panel's turns back, recorded."""
    back: list[str] = []
    vars(helpers)['_menu_action'] = lambda bar, keep, *path: SimpleNamespace(trigger=lambda: None)
    vars(helpers)['_material'] = lambda bar, keep: 'Default (overridden)'
    vars(helpers)['_tiling_spin'] = spin

    def parameters_back() -> str:
        back.append('back')
        return 'the Parameters panel back on g'

    vars(helpers)['_parameters_back'] = parameters_back
    return back


def panel(title: str = 'Material "Default" - Rasterizer') -> SimpleNamespace:
    """The Parameters panel, by its title."""
    return SimpleNamespace(windowTitle=lambda: title)


def test_a_turn_back_failing_after_a_value_was_set_says_it_was_set(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-204: the turn-back's error replaced what the setting returned, so it left the value set out
    vars(helpers)['_switched'] = lambda params, shown: None

    def back() -> NoReturn:
        raise RuntimeError('the graph in the editor is gone')

    vars(helpers)['_parameters_back'] = back
    with pytest.raises(RuntimeError) as raised:
        helpers._in_properties(panel(), lambda: None, lambda: ('tiling 2', True), "the 3D material's properties")
    assert str(raised.value) == 'the graph in the editor is gone; tiling 2 set', raised.value


def test_a_turn_back_failing_after_the_setting_failed_keeps_the_settings_error(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-206: the turn-back's error replaced the setting's, which said what was set
    vars(helpers)['_switched'] = lambda params, shown: None

    def back() -> NoReturn:
        raise RuntimeError('the graph in the editor is gone')

    def setting() -> NoReturn:
        raise RuntimeError('the view took no frame; tiling 2 set')

    vars(helpers)['_parameters_back'] = back
    with pytest.raises(RuntimeError) as raised:
        helpers._in_properties(panel(), lambda: None, setting, "the 3D material's properties")
    assert str(raised.value) == (
        'the view took no frame; tiling 2 set; and turning the Parameters panel back failed: the graph in the editor is'
        ' gone'
    ), raised.value


def test_the_parameters_panel_is_turned_back_when_the_tiling_fails(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-107: after Edit properties, the panel showed the 3D material
    def missing(params: 'QtWidgets.QDockWidget', keep: list['Kept']) -> NoReturn:
        raise RuntimeError("the 3D material's Tiling wasn't found in the Parameters panel")

    back = _tiling(helpers, missing)
    with pytest.raises(RuntimeError, match='Tiling'):
        helpers._set_tiling(panel(), object(), 2.0, [], Frames([]))
    assert back == ['back']


def test_the_parameters_panel_is_turned_back_when_edit_properties_raises(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-112: an abort landing in Edit properties' trigger or right after it
    back = _tiling(helpers, lambda params, keep: Spin())

    def aborted() -> None:
        raise KeyboardInterrupt('an abort in the trigger')

    vars(helpers)['_menu_action'] = lambda bar, keep, *path: SimpleNamespace(trigger=aborted)
    with pytest.raises(KeyboardInterrupt):
        helpers._set_tiling(panel(), object(), 2.0, [], Frames([]))
    assert back == ['back']


def test_the_parameters_panel_is_turned_back_once_it_shows_the_material(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-111: Designer switches the panel to the material over a few event loops after Edit properties;
    # turned back before that (an abort landing in the first poll), the switch came after and stayed
    waited = [0]
    vars(helpers)['_settle'] = lambda seconds: waited.__setitem__(0, waited[0] + 1)
    params = SimpleNamespace(windowTitle=lambda: 'g' if waited[0] < 3 else 'Material "Default" - Rasterizer')

    def aborted(params: 'QtWidgets.QDockWidget', keep: list['Kept']) -> NoReturn:
        raise KeyboardInterrupt('an abort in its first poll')

    _tiling(helpers, aborted)
    seen: list[str] = []

    def parameters_back() -> str:
        seen.append(params.windowTitle())
        return 'the Parameters panel back on g'

    vars(helpers)['_parameters_back'] = parameters_back
    with pytest.raises(KeyboardInterrupt):
        helpers._set_tiling(params, object(), 2.0, [], Frames([]))
    assert seen == ['Material "Default" - Rasterizer']


def test_the_wait_for_the_panel_to_switch_ends(helpers: types.ModuleType) -> None:
    # a panel that showed the material already: its title doesn't change
    waited = [0]
    vars(helpers)['_settle'] = lambda seconds: waited.__setitem__(0, waited[0] + 1)
    back = _tiling(helpers, lambda params, keep: Spin())
    qt('QtCore').QMetaObject.invokeMethod.return_value = True
    helpers._set_tiling(panel(), object(), 2.0, [], Frames([]))
    assert back == ['back'] and waited[0] <= 10


def test_a_tiling_the_spin_box_didnt_take_is_an_error(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-110: invokeMethod returns False when the spin box has no valueChanged(): nothing committed
    qt('QtCore').QMetaObject.invokeMethod.return_value = False
    back = _tiling(helpers, lambda params, keep: Spin())
    with pytest.raises(RuntimeError, match="Tiling didn't take 2"):
        helpers._set_tiling(panel(), object(), 2.0, [], Frames([]))
    assert back == ['back']


def test_the_tiling_said_is_the_spin_boxs(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-110
    qt('QtCore').QMetaObject.invokeMethod.return_value = True
    spin = Spin()
    _tiling(helpers, lambda params, keep: spin)
    assert helpers._set_tiling(panel(), object(), 2.0, [], Frames([])) == (
        'tiling 2.5 (the Parameters panel back on g)',
        True,
    )
    assert spin.set == [2.0]


class Rebuilt(Spin):
    """A spin box Designer deletes as it rebuilds the Parameters panel right after its commit: read after it, it
    raises, as PySide does."""

    def value(self) -> float:
        if self.set:
            raise RuntimeError('Internal C++ object (PySide6.QtWidgets.QDoubleSpinBox) already deleted.')
        return self.shows


def test_a_value_committed_is_read_back_from_the_panel_designer_rebuilt(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-198: off screen, in a Designer whose view never drew, Designer rebuilt the panel as the first tiling
    # was committed: the commit was taken (the panel then read 2), and reading the old spin box back raised
    qt('QtCore').QMetaObject.invokeMethod.return_value = True
    # REVIEW.md TST-551: found again, it shows another value than the one asked, so the line can only come from it
    found = iter([Rebuilt(1.0), Spin(2.5)])
    _tiling(helpers, lambda params, keep: next(found))
    assert helpers._set_tiling(panel(), object(), 2.0, [], Frames([])) == (
        'tiling 2.5 (the Parameters panel back on g)',
        True,
    )


def test_a_value_committed_but_not_found_again_is_said_committed(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-200: the spin box deleted after its commit and not found again, the error left out the value
    # committed
    qt('QtCore').QMetaObject.invokeMethod.return_value = True
    looks = [Rebuilt(1.0)]

    def find(params: 'QtWidgets.QDockWidget', keep: list['Kept']) -> Spin:
        if looks:
            return looks.pop()
        raise RuntimeError("the 3D material's Tiling wasn't found in the Parameters panel")

    _tiling(helpers, find)
    with pytest.raises(RuntimeError) as raised:
        helpers._set_tiling(panel(), object(), 2.0, [], Frames([]))
    assert str(raised.value) == (
        "the 3D material's Tiling wasn't found in the Parameters panel; the 3D material's Tiling committed to 2, not read"
        ' back'
    ), raised.value


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


def test_each_wheel_notch_waits_from_a_mark_taken_before_it_is_sent(helpers: types.ModuleType) -> None:
    # REVIEW.md HLP-164, measured: off screen the view asks for a frame once a notch. Delivered while the notch's own
    # events ran, it came before a mark taken after them, and the wait ran NO_RESTART
    done: list[str] = []
    sys.modules['PySide6.QtWidgets'].QApplication.sendEvent = lambda viewport, event: done.append('notch')
    vars(helpers)['_process_events'] = lambda times=1: done.append('events')

    def taking() -> Callable[[], bool]:
        done.append('mark')

        def taken() -> bool:  # the wait _Frames.taking returns: whether the view took the notch
            done.append('taken')
            return True

        return taken

    viewport = SimpleNamespace(width=lambda: 400, height=lambda: 300, mapToGlobal=lambda point: point)
    helpers._wheel(viewport, -2, taking)
    assert done == ['mark', 'notch', 'events', 'taken'] * 2, done
