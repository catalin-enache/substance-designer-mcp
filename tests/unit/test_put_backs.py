"""The helpers' put-backs of the user's state after an abort, wherever it lands (REVIEW.md HLP-177): the plugin's tracer
raises its abort at a traced event, then Python stops tracing; landed on a `finally`'s first line, the abort skipped
the rest of that `finally`. Each test raises one at every event of the helper and of the fakes standing for sd's
wrappers, which are Python too, in turn (aborts.at_each_event), and checks what each run left."""

import ast
import sys
import types
from collections.abc import Callable
from types import FrameType, SimpleNamespace
from typing import TYPE_CHECKING, ClassVar, TypedDict

import pytest
from aborts import Abort, Tracer, at_each_event

import designer_helpers

if TYPE_CHECKING:  # for the checker only: the types the faked helpers take; sd and PySide6 are faked at run time
    from PySide6 import QtCore, QtWidgets
    from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
    from sd.api.sdnode import SDNode
    from sd.api.sdpackage import SDPackage
    from sd.api.sdproperty import SDProperty, SDPropertyCategory, SDPropertyInheritanceMethod
    from sd.api.sdtexture import SDTexture

FILES = ('designer_helpers', __file__)  # the helpers as conftest's faked_helpers compiles them, and the fakes here


@pytest.fixture
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    return faked_helpers


class Target:
    """A node whose parameter is swept: changing its inheritance resets its value to the default, as Designer does
    (GUIDE.md; REVIEW.md HLP-26)."""

    def __init__(self) -> None:
        # strings stand for the user's inheritance and value; the swept values come as given (_make_value is faked)
        self.inherit: SDPropertyInheritanceMethod | str = 'relative to parent'
        self.value: list[int] | str = 'original'
        self.changed = False  # set by either change, put back or not

    def reset(self) -> None:
        self.inherit, self.value, self.changed = 'relative to parent', 'original', False

    def getPropertyFromId(self, param: str, category: 'SDPropertyCategory') -> SimpleNamespace:
        return SimpleNamespace(isConnectable=lambda: False)

    def getPropertyValue(self, prop: 'SDProperty') -> list[int] | str:
        return self.value

    def setPropertyValue(self, prop: 'SDProperty', value: list[int] | str) -> None:
        self.value, self.changed = value, True

    def getPropertyInheritanceMethod(self, prop: 'SDProperty') -> 'SDPropertyInheritanceMethod | str':
        return self.inherit

    def setPropertyInheritanceMethod(self, prop: 'SDProperty', method: 'SDPropertyInheritanceMethod | str') -> None:
        # one line, as Designer's change is one call: an abort lands before it or after it, never inside
        self.value, self.inherit, self.changed = ('default' if method != self.inherit else self.value), method, True


def _faked_sweep(
    helpers: types.ModuleType,
    target: Target,
    texture: 'Callable[[SDSBSCompGraph, SDNode, str | None, Callable[[SDTexture, SDProperty], None]], None]',
) -> Callable[[], None]:
    """sweep_param of `target`'s $outputsize over two values, `texture` standing for _with_node_texture."""
    for name, value in {
        '_graph_to_edit': lambda identifier: 'the graph',
        '_target': lambda g, node_id: target,
        '_driving_graph': lambda node, prop: None,
        '_refuse_bad_size_on_input': lambda node, prop, values: None,
        '_node': lambda g, ident: 'the node looked at',
        '_make_value': lambda prop, value: value,
        '_with_node_texture': texture,
        'fmt': str,
    }.items():
        vars(helpers)[name] = value

    def run() -> None:
        helpers.sweep_param('G', 'n', '$outputsize', [[7, 7], [8, 8]], 'out')

    return run


def test_an_abort_anywhere_in_a_sweep_leaves_the_parameter_and_its_inheritance_as_they_were(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # an abort at the `try:` after the inheritance was made Absolute, at the finally's inner `try:`, or at its inner
    # finally's first line left the inheritance Absolute or the last swept value (measured in plain Python). REVIEW.md
    # HLP-179: once changed, the parameter put back is said too ('restored ...'), which the server reads (SRV-2)
    target = Target()
    run = _faked_sweep(helpers, target, lambda g, node, output, use: None)

    def fresh() -> None:
        target.reset()
        capsys.readouterr()

    for where in at_each_event(run, FILES, fresh):
        assert (target.inherit, target.value) == ('relative to parent', 'original'), where
        assert 'restored n.$outputsize' in capsys.readouterr().out or not target.changed, where


def test_a_sweep_stopped_by_an_error_says_its_parameter_is_back(
    helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-179: the server says the parameter may not be back unless the helper printed 'restored ...' (SRV-2);
    # HLP-177 moved that line after the put-back's `try`, and an error on a later value skipped it, the value back
    target = Target()
    textures: list[int] = []

    def texture(
        g: 'SDSBSCompGraph', node: 'SDNode', output: str | None, use: 'Callable[[SDTexture, SDProperty], None]'
    ) -> None:
        textures.append(1)
        if len(textures) == 2:
            raise RuntimeError('the second value gave no texture')

    with pytest.raises(RuntimeError, match='second value'):
        _faked_sweep(helpers, target, texture)()
    said = capsys.readouterr().out
    assert (target.inherit, target.value) == ('relative to parent', 'original') and 'restored n.$outputsize' in said


class Node:
    def __init__(self, ident: str, graph: 'Graph') -> None:
        self.ident = ident
        self.graph = graph

    def getIdentifier(self) -> str:
        return self.ident

    def getProperties(self, category: 'SDPropertyCategory') -> list[SimpleNamespace]:
        return [SimpleNamespace(getId=lambda: 'output')]

    def getPropertyValue(self, prop: 'SDProperty') -> SimpleNamespace:
        # Designer computes the nodes that feed an output node (GUIDE.md): a texture once the temporary one is there
        fed = len(self.graph.nodes) > 1
        return SimpleNamespace(get=lambda: 'its texture' if fed else None)

    def newPropertyConnectionFromId(self, output: str, node: 'Node', connector: str) -> None:
        pass


class Graph:
    """The user's graph, with one node of theirs. Deleting a node twice raises: the second would find none."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.added = 0
        self.reset()

    def reset(self) -> None:
        self.nodes = {'theirs': Node('theirs', self)}
        self.added = 0

    def compute(self) -> None:
        pass

    def getNodes(self) -> list[Node]:
        return list(self.nodes.values())

    def newNode(self, definition: str) -> Node:
        self.added += 1
        node = Node('added_%d' % self.added, self)
        self.nodes[node.ident] = node
        return node

    def deleteNode(self, node: Node) -> None:
        del self.nodes[node.ident]


def test_an_abort_anywhere_in_a_measure_through_a_temporary_output_leaves_none_in_the_graph(
    helpers: types.ModuleType,
) -> None:
    # an abort at either line of the finally left the temporary output node in the user's graph
    graph = Graph()

    def run() -> None:
        helpers._with_node_texture(graph, graph.nodes['theirs'], None, lambda texture, prop: None)

    for where in at_each_event(run, FILES, fresh=graph.reset):
        assert list(graph.nodes) == ['theirs'], where


class Package:
    made = 0

    def __init__(self, path: str) -> None:
        self.path = path
        Package.made += 1
        self.uid = '{package %d}' % Package.made

    def getFilePath(self) -> str:
        return self.path

    def listed(self) -> SimpleNamespace:
        """A wrapper of its own, as each listing gives: the same UID and file, another handle."""
        return SimpleNamespace(package=self, getUID=lambda: self.uid, getFilePath=self.getFilePath)


class Packages:
    """Designer's package manager: a new package listed with a UID of its own and no file, a wrapper of its own each
    time it is listed (measured 2026-11-16: a package's handle differs from one listing to the next, its UID doesn't).
    Unloading one twice crashed Designer (measured): here it raises."""

    def __init__(self) -> None:
        self.loaded: list[Package] = []
        self.before: list[Package] = []
        self.reset()

    def reset(self) -> None:
        # a package of the user's on disk, and one they haven't saved, which has no file either
        self.loaded = [Package('/their/package.sbs'), Package('')]
        self.before = list(self.loaded)

    def getUserPackages(self) -> list[SimpleNamespace]:
        return [p.listed() for p in self.loaded]

    def newUserPackage(self) -> SimpleNamespace:
        self.loaded.append(Package(''))
        return self.loaded[-1].listed()

    def unloadUserPackage(self, listed: SimpleNamespace) -> None:
        if listed.package not in self.loaded:
            raise AssertionError('a package unloaded twice: Designer crashed (measured 2026-11-16)')
        self.loaded.remove(listed.package)


class CompGraph:
    @staticmethod
    def sNew(package: 'SDPackage') -> SimpleNamespace:
        node = SimpleNamespace(getProperties=lambda category: [])
        return SimpleNamespace(newNode=lambda definition: node, getNodeDefinitions=list)


@pytest.mark.parametrize('call', ['describe_node', 'list_atomic'])
def test_an_abort_anywhere_in_a_call_through_a_temporary_package_leaves_none_loaded_and_the_users_all(
    helpers: types.ModuleType, call: str
) -> None:
    # an abort at the finally's first line left the temporary package in the user's Explorer
    packages = Packages()
    vars(helpers)['_PM'] = packages
    vars(helpers)['SDSBSCompGraph'] = CompGraph
    vars(helpers)['atomic_definition_ids'] = lambda g: {'sbs::compositing::levels'}
    vars(helpers)['_current_graph'] = lambda: None  # list_atomic: no graph open, so it makes one in a package

    def run() -> None:
        if call == 'describe_node':
            helpers.describe_node('levels')
        else:
            helpers.list_atomic()

    for where in at_each_event(run, FILES, fresh=packages.reset):
        assert packages.loaded == packages.before, where


class Mac:
    """macOS's side of the Explorer menu's window: its look, and the holds on it. A release past the holds would free
    the window while Designer still uses it."""

    def __init__(self, menu: 'QtWidgets.QWidget') -> None:
        self.state = MENU_WINDOW

    def windows(self, all_of_them: bool) -> list[int]:
        return [1]

    def hold(self, window: int) -> None:
        self.state['holds'] += 1

    def let_go(self, window: int) -> None:
        self.state['holds'] -= 1
        if self.state['holds'] < 0:
            raise AssertionError('the window released more often than held')

    def set_appearance(self, window: int, alpha: float, through: bool) -> None:
        self.state['look'] = (alpha, through)


class MenuWindow(TypedDict):
    holds: int  # the holds on it not ended
    look: tuple[float, bool]  # its opacity, and whether the mouse goes through it


MENU_WINDOW: MenuWindow = {'holds': 0, 'look': (1.0, False)}


class Timer:
    made: ClassVar[list['Timer']] = []  # every one made, in order: the look's first

    def __init__(self, owner: 'QtCore.QObject | None') -> None:
        self.running = False
        self.slot: Callable[[], object] = lambda: None
        self.timeout = SimpleNamespace(connect=self.connect)
        Timer.made.append(self)

    def connect(self, slot: Callable[[], object]) -> None:
        self.slot = slot

    def setSingleShot(self, single: bool) -> None:
        pass

    def start(self, after: int) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def isActive(self) -> bool:
        return self.running


class Menu:
    """The Explorer's context menu, Qt's: its window's look is the one Mac reads and sets."""

    action_text = ''

    def __init__(self) -> None:
        self.open = True
        self.action = SimpleNamespace(text=lambda: Menu.action_text, isEnabled=lambda: True, trigger=lambda: None)

    def isVisible(self) -> bool:
        return self.open

    def actions(self) -> list[SimpleNamespace]:
        return [self.action]

    def close(self) -> None:
        self.open = False

    def setWindowOpacity(self, opacity: float) -> None:
        MENU_WINDOW['look'] = (opacity, MENU_WINDOW['look'][1])

    def windowHandle(self) -> SimpleNamespace:
        def set_flag(
            flag: 'QtCore.Qt.WindowType', on: bool
        ) -> None:  # WindowTransparentForInput: the window click-through
            MENU_WINDOW['look'] = (MENU_WINDOW['look'][0], on)

        return SimpleNamespace(setFlag=set_flag)


def test_an_abort_anywhere_in_an_explorer_menus_try_leaves_its_window_opaque_its_timers_stopped_and_no_extra_release(
    helpers: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # an abort at any of the finally's lines left the menu's window transparent and click-through, and the guard's
    # timer running, to close a menu of the user's later; one in the look before the fade left the menu open, opaque,
    # until the guard closed it
    qt = sys.modules['PySide6']
    monkeypatch.setattr(sys, 'platform', 'darwin')
    Menu.action_text = helpers.VIEW_OUTPUTS
    open_menus: list[Menu] = []
    dropped: list[BaseException] = []

    guarded: list[bool] = []

    def send(viewport: 'QtCore.QObject', event: 'QtCore.QEvent') -> None:
        # the menu runs, and its look's timer fires in it; Qt drops what a slot raises, and the plugin raises its
        # abort again at the next traced event, here as the menu's run ends. The menu runs until it closes: the guard
        # closes one still open, MENU_GUARD after it opened
        open_menus.append(Menu())
        try:
            Timer.made[0].slot()
        except BaseException as e:
            dropped.append(e)
        if open_menus[-1].open and Timer.made[1].running:
            guarded.append(True)
            Timer.made[1].slot()
        if dropped:
            raise dropped[-1]

    app = SimpleNamespace(
        activePopupWidget=lambda: next((m for m in reversed(open_menus) if m.open), None), sendEvent=send
    )
    qt.QtWidgets.QApplication = app
    qt.QtWidgets.QMenu = Menu
    qt.QtCore.QTimer = Timer
    qt.QtCore.QObject = object
    vars(helpers)['_MacWindow'] = Mac
    tree = SimpleNamespace(viewport=lambda: SimpleNamespace(mapToGlobal=lambda at: at))

    # an abort raised at the look's call, or at its first line (its `try:`, outside what it guards), comes before any of
    # it runs: the menu stays as it opened until the guard closes it
    menu_once = next(
        n
        for n in ast.walk(ast.parse(designer_helpers.source()))
        if isinstance(n, ast.FunctionDef) and n.name == '_menu_once'
    )
    look = next(n for n in ast.walk(menu_once) if isinstance(n, ast.FunctionDef) and n.name == 'look')
    before_the_look = {'look:%d call' % look.lineno, 'look:%d line' % look.body[0].lineno}

    def fresh() -> None:
        guarded.clear()
        MENU_WINDOW.update({'holds': 0, 'look': (1.0, False)})
        Timer.made.clear()
        open_menus.clear()
        dropped.clear()

    def run() -> None:
        helpers._menu_once(tree, 'at', [])

    for where in at_each_event(run, FILES, fresh, untraced=(send, Menu, Timer, app.activePopupWidget, tree.viewport)):
        assert MENU_WINDOW['look'] == (1.0, False), where
        assert not any(timer.running for timer in Timer.made), where
        assert not any(menu.open for menu in open_menus), where
        assert not guarded or where in before_the_look, where  # closed at once otherwise
        # a hold left is a closed window kept, never shown again: releasing it once more could free it twice
        assert MENU_WINDOW['holds'] in (0, 1), where


def test_an_abort_at_a_try_line_escapes_the_try_around_it_but_not_one_in_a_caller() -> None:
    # what the put-backs' handlers rely on (REVIEW.md HLP-177): a `try:` nested in another, in one function, is a hole
    # once the outer one's body has changed something (measured on Python 3.12 and Designer's 3.13); the handler of a
    # caller catches it, as look's catches an abort at fade's own `try:`
    caught: list[str] = []

    def inner() -> None:
        try:
            caught.append('inner ran')
        except BaseException:
            caught.append('inner handler')
            raise

    def nested() -> None:
        try:
            caught.append('outer body')
            try:
                caught.append('inner body')
            except BaseException:
                caught.append('inner handler')
                raise
        except BaseException:
            caught.append('outer handler')
            raise

    def calling() -> None:
        try:
            inner()
        except BaseException:
            caught.append('caller handler')
            raise

    for function, at in ((nested, nested.__code__.co_firstlineno + 3), (inner, inner.__code__.co_firstlineno + 1)):
        caught.clear()

        def tracer(frame: FrameType, event: str, arg: object, at: int = at) -> Tracer | None:
            if event == 'line' and frame.f_lineno == at and frame.f_code.co_filename == __file__:
                raise Abort
            return tracer

        previous = sys.gettrace()
        sys.settrace(tracer)
        try:
            with pytest.raises(Abort):
                (nested if function is nested else calling)()
        finally:
            sys.settrace(previous)
        assert caught == (['outer body'] if function is nested else ['caller handler']), caught
