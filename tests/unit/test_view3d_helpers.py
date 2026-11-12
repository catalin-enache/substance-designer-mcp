"""The helpers' side of screenshot_designer('3d', ...) (designer_helpers/view3d.py), with sd and PySide6 faked: what is
checked before anything changes, what an error says was set, the graph's row found before its context menu opens
there, and what the timers do while that menu runs. The live self-test checks the 3D view itself
(editor_panels_and_fit)."""

import re
import sys
import types
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest

import designer_helpers  # conftest puts mcp_server on sys.path


@pytest.fixture
def helpers(monkeypatch: pytest.MonkeyPatch) -> Any:
    fake = mock.MagicMock()
    imported = re.findall(r'^\s*(?:from|import) ((?:sd|PySide6)(?:\.\w+)*)', designer_helpers.source(), re.M)
    for name in sorted({'.'.join(m.split('.')[:i]) for m in imported for i in range(1, m.count('.') + 2)}):
        monkeypatch.setitem(sys.modules, name, fake)
    module: Any = types.ModuleType('helpers_under_test')
    exec(compile(designer_helpers.source(), 'designer_helpers', 'exec'), module.__dict__)
    module._process_events = lambda n=10: None
    module._settle = lambda seconds: None
    module.APIException = type('APIException', (BaseException,), {})  # the sd API's: a BaseException, as in Designer
    return module


def qt(name: str) -> Any:
    """The faked PySide6 module `name` (QtCore, QtWidgets...), as the helpers import it."""
    return getattr(sys.modules['PySide6'], name)


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


def _tree(row: Index, under: Any = None, inside: bool = True) -> Any:
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


def test_a_graphs_row_is_scrolled_into_view_before_its_point_is_read(helpers: Any) -> None:
    row = Index(Index())
    tree = _tree(row)
    assert helpers._row_point(tree, row, 'g') is tree.point
    assert tree.scrolled == [row]


@pytest.mark.parametrize('under, inside', [(Index(), True), (None, False)], ids=['another row there', 'out of view'])
def test_a_point_that_isnt_on_the_graphs_row_is_refused(helpers: Any, under: Any, inside: bool) -> None:
    # the menu opens for the row under the point: another graph's outputs would go on the mesh
    row = Index(Index())
    with pytest.raises(RuntimeError, match="graph g's row isn't showing in the Explorer"):
        helpers._row_point(_tree(row, under, inside), row, 'g')


class Menu:
    def __init__(self, *texts: str, disabled: tuple[str, ...] = (), raising: bool = False) -> None:
        self.triggered: list[str] = []
        self.closed = False

        def trigger(t: str) -> None:
            if raising:
                raise KeyboardInterrupt('an abort landing in the trigger')
            self.triggered.append(t)

        self._actions = [
            SimpleNamespace(text=lambda t=t: t, isEnabled=lambda t=t: t not in disabled, trigger=lambda t=t: trigger(t))
            for t in texts
        ]

    def actions(self) -> list[Any]:
        return self._actions

    def close(self) -> None:
        self.closed = True


VIEW = 'View Outputs In 3D View'


def test_the_pick_looks_again_until_the_menu_opens_then_triggers_the_action(helpers: Any) -> None:
    pick = helpers._MenuPick(VIEW, None)
    menu = Menu('Open', '&View Outputs In 3D View', 'Compute Outputs')
    assert pick.pick(None) is False  # not open yet: its timer starts again
    assert pick.pick(menu) is True
    assert menu.triggered == ['&View Outputs In 3D View'] and menu.closed
    assert pick.failure('g', held=False) is None


def test_a_popup_open_before_the_menu_isnt_taken_for_it(helpers: Any) -> None:
    # REVIEW.md HLP-109: a menu of the user's, open as the job runs
    users = Menu('Cut', VIEW)
    pick = helpers._MenuPick(VIEW, users)
    assert pick.pick(users) is False
    assert not users.closed and users.triggered == []


def test_a_menu_without_the_action_is_closed_and_said(helpers: Any) -> None:
    pick = helpers._MenuPick(VIEW, None)
    menu = Menu('Open', 'Rename')
    pick.pick(menu)
    assert menu.closed and menu.triggered == []
    assert pick.failure('g', held=False) == "the Explorer's menu for graph g had no 'View Outputs In 3D View'"


def test_a_disabled_action_isnt_triggered_and_is_said(helpers: Any) -> None:
    # REVIEW.md HLP-110
    pick = helpers._MenuPick(VIEW, None)
    menu = Menu('Open', VIEW, disabled=(VIEW,))
    pick.pick(menu)
    assert menu.closed and menu.triggered == []
    assert pick.failure('g', held=False) == "the Explorer's menu for graph g had 'View Outputs In 3D View' disabled"


def test_the_menu_is_closed_even_when_the_trigger_raises(helpers: Any) -> None:
    # REVIEW.md HLP-108: an abort (cancel, timeout) landing in the pick; an open menu holds the job
    pick = helpers._MenuPick(VIEW, None)
    menu = Menu(VIEW, raising=True)
    with pytest.raises(KeyboardInterrupt):
        pick.pick(menu)
    assert menu.closed


def test_a_menu_that_never_opened_is_said(helpers: Any) -> None:
    pick = helpers._MenuPick(VIEW, None)
    pick.pick(None)
    assert pick.failure('g', held=False) == "the Explorer's menu for graph g didn't open"


def test_a_menu_the_guard_closed_after_the_action_is_a_failure(helpers: Any) -> None:
    # a second menu (Designer asking which channel) holds the job until the guard closes it, unanswered
    pick = helpers._MenuPick(VIEW, None)
    pick.pick(Menu(VIEW))
    assert pick.failure('g', held=True) == (
        "a menu was still open 5 s after 'View Outputs In 3D View' (Designer asking something more?), and was closed "
        'unanswered'
    )


def test_the_guard_closes_the_popups_above_the_one_open_before_and_runs_no_python(helpers: Any) -> None:
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


def test_the_guard_closes_at_most_five_popups(helpers: Any) -> None:
    # a popup refusing to close stays the active one: the guard doesn't loop on it
    closes: list[str] = []
    stuck = SimpleNamespace(close=lambda: closes.append('close'))
    active = iter([stuck] * 50 + [None]).__next__
    helpers._popup_closer(active, None)()
    assert len(closes) == 5


class Timer:
    """A QTimer: started, stopped, never firing by itself; `run` is what its timeout was connected to. `aborted`: its
    start raises, as an abort landing there would."""

    def __init__(self, aborted: bool = False, parent: Any = None) -> None:
        self.active = False
        self.aborted = aborted
        self.parent = parent
        self.run: Any = None
        self.timeout = SimpleNamespace(connect=lambda run: setattr(self, 'run', run))

    def setSingleShot(self, single: bool) -> None:
        pass

    def start(self, after: int) -> None:
        if self.aborted:
            raise KeyboardInterrupt('an abort as the timer starts')
        self.active = True

    def stop(self) -> None:
        self.active = False

    def isActive(self) -> bool:
        return self.active


def _outputs_applied(
    helpers: Any, send_event: Any, aborted_start: int | None = None, timers: list[Timer] | None = None
) -> None:
    """_apply_outputs on a faked Explorer, the menu's run being `send_event(timers)`; the timers it makes go in
    `timers` (the one numbered `aborted_start` raising as it starts)."""
    made: list[Timer] = [] if timers is None else timers

    def new_timer(*args: Any) -> Timer:
        made.append(Timer(aborted=len(made) == aborted_start, parent=args[0] if args else None))
        return made[-1]

    qt('QtCore').QTimer.side_effect = new_timer
    qt('QtWidgets').QApplication.sendEvent.side_effect = lambda viewport, event: send_event(made)
    qt('QtWidgets').QApplication.activePopupWidget.return_value = None
    helpers._row_point = lambda tree, row, graph: 'the point'
    tree = SimpleNamespace(selectionModel=lambda: SimpleNamespace(selectedRows=lambda: [Index()]), viewport=mock.Mock())
    helpers._apply_outputs(tree, SimpleNamespace(getIdentifier=lambda: 'g'), [])


@pytest.mark.parametrize('menu_run', ['returns', 'raises', 'aborted as the guard starts'])
def test_both_timers_are_stopped_whatever_the_menu_does(helpers: Any, menu_run: str) -> None:
    # REVIEW.md TST-316: a timer left running would later pick from, or close, a menu of the user's; HLP-112: an abort
    # landing as the second timer starts, the first already running
    def send_event(timers: list[Timer]) -> None:
        if menu_run == 'raises':
            raise KeyboardInterrupt('an abort as the menu runs')

    timers: list[Timer] = []
    aborted = 1 if menu_run.startswith('aborted') else None
    with pytest.raises((RuntimeError, KeyboardInterrupt)):  # returning without a menu: it didn't open
        _outputs_applied(helpers, send_event, aborted, timers)
    assert len(timers) == 2 and not any(t.active for t in timers)


def test_the_timers_go_with_the_function_whatever_runs_of_its_finally(helpers: Any) -> None:
    # REVIEW.md HLP-118: an abort landing on the finally's first line skips the stops; the timers' parent, made for
    # this call and held by its frame alone, takes them with it (the live designer fact: editor_panels_and_fit)
    timers: list[Timer] = []
    with pytest.raises(RuntimeError):  # no menu: it didn't open
        _outputs_applied(helpers, lambda made: None, timers=timers)
    assert [t.parent for t in timers] == [qt('QtCore').QObject.return_value] * 2


def test_a_menu_the_guard_had_to_close_is_a_failure(helpers: Any) -> None:
    # REVIEW.md TST-326: the guard's timer has run (no longer active) as the menu's loop ends
    def send_event(timers: list[Timer]) -> None:
        timers[0].run()  # the pick, with the menu open
        timers[1].active = False

    qt('QtWidgets').QMenu = Menu
    qt('QtWidgets').QApplication.activePopupWidget.side_effect = [None, Menu(VIEW)]
    with pytest.raises(RuntimeError, match="a menu was still open 5 s after 'View Outputs In 3D View'"):
        _outputs_applied(helpers, send_event)


def test_a_menu_closed_by_the_pick_alone_is_no_failure(helpers: Any) -> None:
    def send_event(timers: list[Timer]) -> None:
        timers[0].run()

    qt('QtWidgets').QMenu = Menu
    qt('QtWidgets').QApplication.activePopupWidget.side_effect = [None, Menu(VIEW)]
    _outputs_applied(helpers, send_event)


def _materials_menu(helpers: Any, *names: str) -> None:
    menu = SimpleNamespace(
        aboutToShow=mock.Mock(),
        actions=lambda: (
            [SimpleNamespace(text=lambda n=n: n, menu=lambda: object()) for n in names]
            + [SimpleNamespace(text=lambda: 'Add', menu=lambda: None)]
        ),
    )
    helpers._menu_action = lambda bar, keep, *path: SimpleNamespace(menu=lambda: menu)


def test_the_material_is_the_meshs_only_one(helpers: Any) -> None:
    _materials_menu(helpers, '&Default (overridden)')
    assert helpers._material(object(), []) == 'Default (overridden)'


def test_a_material_the_mesh_doesnt_use_isnt_counted(helpers: Any) -> None:
    # REVIEW.md HLP-114: Materials > Add's, as Designer lists it (measured)
    _materials_menu(helpers, 'Default (overridden)', 'Second (unused) (overridden)')
    assert helpers._material(object(), []) == 'Default (overridden)'


def test_a_mesh_with_several_materials_is_refused(helpers: Any) -> None:
    # tiling= would tile one of them (REVIEW.md TST-315)
    _materials_menu(helpers, 'Body', 'Glass')
    with pytest.raises(RuntimeError, match="the 3D view's mesh has 2 materials: Body, Glass"):
        helpers._material(object(), [])


class Designer:
    """set_3d_view's Designer, faked: its panels (`hidden` ones not visible), the 3D view's menus (each path looked up
    and each triggered recorded), and one graph with `outputs` outputs."""

    def __init__(self, helpers: Any, hidden: tuple[str, ...] = (), outputs: int = 2) -> None:
        self.events: list[tuple[str, tuple[str, ...]]] = []  # ('lookup' or 'trigger', the menu path or step)
        self.order: list[str] = []
        widgets = qt('QtWidgets')
        viewport = SimpleNamespace(metaObject=lambda: SimpleNamespace(className=lambda: 'Alg::Gui3D::ViewportWidget'))
        tree = SimpleNamespace(objectName=lambda: 'mTreeView')
        children = {widgets.QMenuBar: [object()], widgets.QTreeView: [tree], widgets.QWidget: [viewport]}
        dock = SimpleNamespace(findChildren=lambda cls: children[cls])
        areas = {helpers._PANEL_AREAS[name] for name in hidden}

        def visible_dock(mw: Any, area: str) -> Any:
            self.order.append(area)
            return None if area in areas else dock

        def menu_action(bar: Any, keep: Any, *path: str) -> Any:
            self.events.append(('lookup', path))
            return SimpleNamespace(trigger=lambda: self.events.append(('trigger', path)))

        helpers._visible_dock = visible_dock
        helpers._menu_action = menu_action
        helpers._material = lambda bar, keep: 'Default (overridden)'
        helpers._home_screen = lambda: None
        helpers._wheel = lambda viewport, steps, pause: self.events.append(('trigger', ('wheel', str(steps))))
        helpers._apply_outputs = lambda tree, g, keep: self.events.append(('trigger', ('outputs', g.getIdentifier())))

        def set_tiling(params: Any, bar: Any, value: float, keep: Any) -> str:
            self.events.append(('trigger', ('tiling', str(value))))
            return 'tiling %g' % value

        helpers._set_tiling = set_tiling
        helpers.find_graph = lambda name: SimpleNamespace(
            getIdentifier=lambda: name, getOutputNodes=lambda: [object()] * outputs, compute=lambda: None
        )

    def triggered(self) -> list[tuple[str, ...]]:
        return [path for kind, path in self.events if kind == 'trigger']


@pytest.mark.parametrize(
    'outputs, said', [(1, 'graph g has one output: Designer would ask'), (0, 'graph g has no outputs to show')]
)
def test_a_graph_with_fewer_than_two_outputs_is_refused_before_the_panels_are_looked_at(
    helpers: Any, outputs: int, said: str
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
    ],
    ids=['tiling', 'graph'],
)
def test_a_panel_it_needs_is_checked_before_anything_changes(
    helpers: Any, hidden: tuple[str, ...], options: dict[str, Any], said: str
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
    helpers: Any, mesh: str | None, materials: tuple[str, ...]
) -> None:
    # with mesh=, the material is the new mesh's, read once it shows (REVIEW.md HLP-114)
    designer = Designer(helpers)
    helpers.set_3d_view(mesh=mesh, view='Top', tiling=2.0)
    first = [path for kind, path in designer.events[: [kind for kind, _ in designer.events].index('trigger')]]
    assert {('Camera', 'Top'), ('Camera', 'Frame'), materials} <= set(first)
    assert mesh is None or ('Scene', mesh) in first


def test_tiling_with_a_mesh_doesnt_count_the_materials_of_the_mesh_it_replaces(helpers: Any) -> None:
    # REVIEW.md HLP-114: the mesh shown had two; the Plane has one
    designer = Designer(helpers)

    def two(bar: Any, keep: Any) -> str:
        raise RuntimeError("the 3D view's mesh has 2 materials: A, B; tiling= sets the material of a mesh with one")

    helpers._material = two
    helpers.set_3d_view(mesh='Plane', tiling=2.0)
    assert ('tiling', '2.0') in designer.triggered()
    with pytest.raises(RuntimeError, match='2 materials'):
        helpers.set_3d_view(tiling=2.0)


def test_an_abort_after_a_change_says_what_was_set_and_goes_on(
    helpers: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-113: the plugin's abort is a BaseException, raised again unchanged so the plugin reports it
    Designer(helpers)

    def aborted(tree: Any, g: Any, keep: Any) -> None:
        raise KeyboardInterrupt('an abort as the outputs are applied')

    helpers._apply_outputs = aborted
    with pytest.raises(KeyboardInterrupt, match='an abort as the outputs are applied'):
        helpers.set_3d_view('g', 'Plane', 'Top')
    assert capsys.readouterr().out == "3D view, setting: Plane\n3D view, setting: graph g's outputs on the mesh\n"


def _settle_aborted_at(helpers: Any, call: int) -> None:
    """_settle raising as an abort would, on its `call`-th call (from 1): most of a set-up's time is its waits."""
    calls = [0]

    def settle(seconds: float) -> None:
        calls[0] += 1
        if calls[0] == call:
            raise KeyboardInterrupt('an abort in a wait')

    helpers._settle = settle


def test_an_abort_during_a_steps_wait_says_that_step(helpers: Any, capsys: pytest.CaptureFixture[str]) -> None:
    # REVIEW.md HLP-116: the mesh changed, then the abort in the wait after it
    Designer(helpers)
    _settle_aborted_at(helpers, 1)
    with pytest.raises(KeyboardInterrupt):
        helpers.set_3d_view(mesh='Plane')
    assert capsys.readouterr().out == '3D view, setting: Plane\n'


def test_an_abort_in_the_last_wait_says_all_that_was_set(helpers: Any, capsys: pytest.CaptureFixture[str]) -> None:
    # REVIEW.md HLP-116: the waits after the mesh, the view's turn and its frame, then the last one
    Designer(helpers)
    _settle_aborted_at(helpers, 4)
    with pytest.raises(KeyboardInterrupt):
        helpers.set_3d_view(mesh='Plane', view='Top')
    assert capsys.readouterr().out.splitlines()[-1] == '3D view: Plane, view Top, framed'


def test_an_api_error_after_a_change_says_what_was_set(helpers: Any) -> None:
    # REVIEW.md HLP-117: the sd API's error is a BaseException, not an abort
    Designer(helpers)

    def refused(tree: Any, g: Any, keep: Any) -> None:
        raise helpers.APIException('the API refused')

    helpers._apply_outputs = refused
    with pytest.raises(RuntimeError) as raised:
        helpers.set_3d_view('g', 'Plane')
    assert str(raised.value) == 'the API refused; the 3D view was already set: Plane'


def test_an_abort_escaping_the_tiling_turns_the_panel_back(helpers: Any) -> None:
    # REVIEW.md HLP-118: one landing on _set_tiling's finally's first line skips its turn-back; the abort's handler, run
    # untraced, turns it back
    Designer(helpers)
    back: list[str] = []

    def aborted(params: Any, bar: Any, value: float, keep: Any) -> str:
        raise KeyboardInterrupt('an abort as the tiling ends')

    def parameters_back() -> str:
        back.append('back')
        return 'the Parameters panel back on g'

    helpers._set_tiling = aborted
    helpers._parameters_back = parameters_back
    with pytest.raises(KeyboardInterrupt):
        helpers.set_3d_view(tiling=2.0)
    assert back == ['back']


def test_an_abort_while_the_menus_are_looked_up_says_nothing(helpers: Any, capsys: pytest.CaptureFixture[str]) -> None:
    designer = Designer(helpers)

    def aborted(bar: Any, keep: Any, *path: str) -> Any:
        raise KeyboardInterrupt('an abort as the menus are looked up')

    helpers._menu_action = aborted
    with pytest.raises(KeyboardInterrupt):
        helpers.set_3d_view('g', 'Plane')
    assert capsys.readouterr().out == '' and designer.triggered() == []


def test_the_3d_view_before_any_graph_was_opened_is_said(helpers: Any) -> None:
    # REVIEW.md HLP-115: Designer builds its menu bar and viewport once a graph is opened
    helpers._visible_dock = lambda mw, area: SimpleNamespace(findChildren=lambda cls: [])
    with pytest.raises(RuntimeError, match=r"the 3D view isn't built yet: .*open_graph"):
        helpers._3d_dock(object())


def test_an_error_after_a_change_says_what_was_set(helpers: Any) -> None:
    # REVIEW.md HLP-107
    Designer(helpers)

    def failing(tree: Any, g: Any, keep: Any) -> None:
        raise RuntimeError("the Explorer's menu for graph g didn't open")

    helpers._apply_outputs = failing
    with pytest.raises(RuntimeError) as raised:
        helpers.set_3d_view('g', 'Plane', 'Top')
    assert str(raised.value) == "the Explorer's menu for graph g didn't open; the 3D view was already set: Plane"


def test_the_line_says_what_was_set(helpers: Any, capsys: pytest.CaptureFixture[str]) -> None:
    Designer(helpers)
    helpers.set_3d_view('g', 'Plane', 'Top', 2, 2.0)
    assert capsys.readouterr().out.splitlines()[-1] == (
        "3D view: Plane, graph g's outputs on the mesh, view Top, framed, +2 wheel steps, tiling 2"
    )


def test_each_step_is_said_before_its_change(helpers: Any) -> None:
    # REVIEW.md HLP-119: an abort anywhere after a change finds it said; one before it finds the step said as begun
    designer = Designer(helpers)
    helpers.print = lambda line: designer.events.append(('print', (line,)))
    helpers.set_3d_view('g', 'Plane', 'Top', 2, 2.0)
    said = [(kind, path) for kind, path in designer.events if kind in ('print', 'trigger')]
    assert said == [
        ('print', ('3D view, setting: Plane',)),
        ('trigger', ('Scene', 'Plane')),
        ('print', ("3D view, setting: graph g's outputs on the mesh",)),
        ('trigger', ('outputs', 'g')),
        ('print', ('3D view, setting: view Top, framed',)),
        ('trigger', ('Camera', 'Top')),
        ('trigger', ('Camera', 'Frame')),
        ('print', ('3D view, setting: +2 wheel steps',)),
        ('trigger', ('wheel', '2')),
        ('print', ('3D view, setting: tiling 2',)),
        ('trigger', ('tiling', '2.0')),
        ('print', ("3D view: Plane, graph g's outputs on the mesh, view Top, framed, +2 wheel steps, tiling 2",)),
    ]


class Spin:
    def __init__(self) -> None:
        self.set: list[float] = []

    def setValue(self, value: float) -> None:
        self.set.append(value)

    def value(self) -> float:
        return 2.5  # what the spin box holds, maybe not what was asked


def _tiling(helpers: Any, spin: Any) -> list[str]:
    """_set_tiling's Designer, faked; the panel's turns back, recorded."""
    back: list[str] = []
    helpers._menu_action = lambda bar, keep, *path: SimpleNamespace(trigger=lambda: None)
    helpers._material = lambda bar, keep: 'Default (overridden)'
    helpers._tiling_spin = spin

    def parameters_back() -> str:
        back.append('back')
        return 'the Parameters panel back on g'

    helpers._parameters_back = parameters_back
    return back


def panel(title: str = 'Material "Default" - Rasterizer') -> Any:
    """The Parameters panel, by its title."""
    return SimpleNamespace(windowTitle=lambda: title)


def test_the_parameters_panel_is_turned_back_when_the_tiling_fails(helpers: Any) -> None:
    # REVIEW.md HLP-107: after Edit properties, the panel showed the 3D material
    def missing(params: Any, keep: Any) -> Any:
        raise RuntimeError("the 3D material's Tiling wasn't found in the Parameters panel")

    back = _tiling(helpers, missing)
    with pytest.raises(RuntimeError, match='Tiling'):
        helpers._set_tiling(panel(), object(), 2.0, [])
    assert back == ['back']


def test_the_parameters_panel_is_turned_back_when_edit_properties_raises(helpers: Any) -> None:
    # REVIEW.md HLP-112: an abort landing in Edit properties' trigger or right after it
    back = _tiling(helpers, lambda params, keep: Spin())

    def aborted() -> None:
        raise KeyboardInterrupt('an abort in the trigger')

    helpers._menu_action = lambda bar, keep, *path: SimpleNamespace(trigger=aborted)
    with pytest.raises(KeyboardInterrupt):
        helpers._set_tiling(panel(), object(), 2.0, [])
    assert back == ['back']


def test_the_parameters_panel_is_turned_back_once_it_shows_the_material(helpers: Any) -> None:
    # REVIEW.md HLP-111: Designer switches the panel to the material over a few event loops after Edit properties;
    # turned back before that (an abort landing in the first poll), the switch came after and stayed
    waited = [0]
    helpers._settle = lambda seconds: waited.__setitem__(0, waited[0] + 1)
    params = SimpleNamespace(windowTitle=lambda: 'g' if waited[0] < 3 else 'Material "Default" - Rasterizer')

    def aborted(params: Any, keep: Any) -> Any:
        raise KeyboardInterrupt('an abort in its first poll')

    _tiling(helpers, aborted)
    seen: list[str] = []

    def parameters_back() -> str:
        seen.append(params.windowTitle())
        return 'the Parameters panel back on g'

    helpers._parameters_back = parameters_back
    with pytest.raises(KeyboardInterrupt):
        helpers._set_tiling(params, object(), 2.0, [])
    assert seen == ['Material "Default" - Rasterizer']


def test_the_wait_for_the_panel_to_switch_ends(helpers: Any) -> None:
    # a panel that showed the material already: its title doesn't change
    waited = [0]
    helpers._settle = lambda seconds: waited.__setitem__(0, waited[0] + 1)
    back = _tiling(helpers, lambda params, keep: Spin())
    qt('QtCore').QMetaObject.invokeMethod.return_value = True
    helpers._set_tiling(panel(), object(), 2.0, [])
    assert back == ['back'] and waited[0] <= 10


def test_a_tiling_the_spin_box_didnt_take_is_an_error(helpers: Any) -> None:
    # REVIEW.md HLP-110: invokeMethod returns False when the spin box has no valueChanged(): nothing committed
    qt('QtCore').QMetaObject.invokeMethod.return_value = False
    back = _tiling(helpers, lambda params, keep: Spin())
    with pytest.raises(RuntimeError, match="Tiling didn't take 2"):
        helpers._set_tiling(panel(), object(), 2.0, [])
    assert back == ['back']


def test_the_tiling_said_is_the_spin_boxs(helpers: Any) -> None:
    # REVIEW.md HLP-110
    qt('QtCore').QMetaObject.invokeMethod.return_value = True
    spin = Spin()
    _tiling(helpers, lambda params, keep: spin)
    assert helpers._set_tiling(panel(), object(), 2.0, []) == 'tiling 2.5 (the Parameters panel back on g)'
    assert spin.set == [2.0]
