"""Designer's history as the rollback (mcp_server/designer_rollback.py) reaches it through PySide6, and sd's undo
transactions as the code _with_undo sends opens and commits them, for test_rollback.py and test_plugin.py: the
toolbar's Undo and Redo buttons, their actions and dropdown menus, the history manager, an event loop in which an undo
lands, and sd's transactions. `modules()` gives the fake PySide6 modules, `Designer` one state of the history,
`install_sd()` the fake sd.

As PySide6 did in one Designer (designer_rollback.py's docstring), each defaultAction() and menu() gives a new
wrapper, and a menu's wrapper is no longer valid once the action wrapper it came from is dropped."""

import functools
import gc
import math
import sys
import types
import weakref
from collections.abc import Callable
from typing import Literal

import pytest

MANAGER = 'Alg::Gui::HistoryActionsMgr'  # the class name Designer's history manager reports
DELETED = 'Internal C++ object (PySide6.QtWidgets.QMenu) already deleted.'  # PySide6's message for a stale wrapper
LISTED = 25  # the newest steps a dropdown lists, at most, as Designer's do (designer_rollback.py's docstring)
# Steps' names for undo_edits' tests: a session's edits, oldest first, and reads, its calls' labels and tags; and a step
# of the user's or another client's, as Designer names one made outside any group
E0, E1, E2, E3 = ('Claude: apply 1 edits #0000000%d' % i for i in range(4))
READ, READ_2 = 'Claude: preview node #0000000a', 'Claude: node stats #0000000b'
OTHER = 'Add Atomic Node'


def full(*on_top: str) -> list[str]:
    """Designer's steps, newest first: `on_top`, then others, one more than a dropdown lists."""
    return list(on_top) + ['other %d' % i for i in range(LISTED + 1 - len(on_top))]


EventKind = Literal['ActionAdded', 'ActionRemoved']  # a menu's events the rollback's filter reads
Flag = Literal['ExcludeUserInputEvents']  # the event loop's flag the rollback passes
Slot = Literal['undo()']  # the history manager's slot the rollback calls
GroupEvent = tuple[Literal['enter', 'commit'], str]  # an undo group's enter or commit, with its name


class QEvent:
    """An event of a menu: only its type is read."""

    class Type:
        ActionAdded: EventKind = 'ActionAdded'
        ActionRemoved: EventKind = 'ActionRemoved'

    def __init__(self, kind: EventKind) -> None:
        self.kind = kind

    def type(self) -> EventKind:
        return self.kind


class QObject:
    """A Qt object: the event filters installed on it (on the object, not on a wrapper)."""

    def __init__(self) -> None:
        self.filters: list[QObject] = []

    def installEventFilter(self, watcher: 'QObject') -> None:
        self.filters.append(watcher)

    def removeEventFilter(self, watcher: 'QObject') -> None:
        self.filters.remove(watcher)

    def eventFilter(self, watched: 'QObject', event: QEvent) -> bool:
        return False


class _Step:
    def __init__(self, name: str) -> None:
        self.name = name

    def text(self) -> str:
        return self.name


class _MenuState(QObject):
    """A dropdown menu as Designer holds it: the steps it lists, newest first, and its event filters."""

    def __init__(self, steps: list[str]) -> None:
        super().__init__()
        self.steps = steps

    def notify(self, kind: EventKind) -> None:
        for watcher in list(self.filters):
            watcher.eventFilter(self, QEvent(kind))


class QMenu:
    """A wrapper of a dropdown menu, valid while the action wrapper it was taken from lives."""

    def __init__(self, state: _MenuState) -> None:
        self.state, self.valid = state, True

    def _checked(self) -> _MenuState:
        if not self.valid:
            raise RuntimeError(DELETED)
        return self.state

    def actions(self) -> list[_Step]:
        return [_Step(name) for name in self._checked().steps[:LISTED]]

    def installEventFilter(self, watcher: QObject) -> None:
        self._checked().installEventFilter(watcher)

    def removeEventFilter(self, watcher: QObject) -> None:
        if Designer.current.removing_raises is not None:
            raise Designer.current.removing_raises
        self._checked().removeEventFilter(watcher)


class _Method:
    """A slot's QMetaMethod: invoking it calls the slot, and says False, as Qt does when it isn't called, if the slot
    returns False."""

    def __init__(self, call: Callable[[], object]) -> None:
        self.call = call

    def invoke(self, obj: object) -> bool:
        return self.call() is not False


class _Meta:
    """The manager's meta-object: its slots, by signature."""

    def __init__(self, slots: dict[str, Callable[[], object]]) -> None:
        self.slots = list(slots.items())

    def indexOfMethod(self, signature: str) -> int:
        return next((i for i, (name, _) in enumerate(self.slots) if name == signature), -1)

    def method(self, index: int) -> _Method:
        return _Method(self.slots[index][1])


class _Manager:
    """Designer's history manager, of the class `name`, with its undo() slot unless `slots` leaves it out."""

    def __init__(self, undo: Callable[[], object]) -> None:
        self.name = MANAGER
        self.slots: dict[str, Callable[[], object]] = {'undo()': undo}

    def inherits(self, name: str) -> bool:
        return name == self.name

    def metaObject(self) -> _Meta:
        return _Meta(self.slots)


class _Action:
    """A wrapper of a toolbar button's action: its menu's wrapper is invalidated once this one is gone."""

    def __init__(self, menu: _MenuState | None, manager: _Manager) -> None:
        self._menu, self._manager = menu, manager

    def menu(self) -> QMenu | None:
        if self._menu is None:
            return None
        wrapper = QMenu(self._menu)
        weakref.finalize(self, setattr, wrapper, 'valid', False)
        return wrapper

    def parent(self) -> _Manager:
        return self._manager


class QToolButton:
    def __init__(self, name: str, menu: _MenuState | None, manager: _Manager) -> None:
        self.name, self._menu, self._manager = name, menu, manager

    def objectName(self) -> str:
        return self.name

    def defaultAction(self) -> _Action:
        return _Action(self._menu, self._manager)  # a new wrapper each time, as PySide6 gives


class _Signal:
    def __init__(self) -> None:
        self.slots: list[Callable[[], object]] = []

    def connect(self, slot: Callable[[], object]) -> None:
        self.slots.append(slot)

    def emit(self) -> None:
        for slot in list(self.slots):
            slot()


class QTimer:
    """A timer whose timeout fires when the loop waits with nothing else to do, moving the clock on by its interval."""

    def __init__(self) -> None:
        self.timeout = _Signal()
        self.interval_ms, self.active, self.single = 0, False, False
        Designer.current.timers.append(self)

    def setSingleShot(self, single: bool) -> None:
        self.single = single

    def start(self, ms: int) -> None:
        self.interval_ms, self.active = ms, True

    def stop(self) -> None:
        self.active = False

    def isActive(self) -> bool:
        return self.active


class QEventLoop:
    """A loop whose exec() runs one pass of Designer's events, then, unless something called quit() during it, waits
    for the running timer, which fires (Designer.pass_events)."""

    class ProcessEventsFlag:
        ExcludeUserInputEvents: Flag = 'ExcludeUserInputEvents'

    def __init__(self) -> None:
        self.quitted = False

    def exec(self, flags: Flag) -> int:
        self.quitted = False
        return Designer.current.pass_events(self, flags)

    def quit(self) -> None:
        self.quitted = True


class QApplication:
    @staticmethod
    def allWidgets() -> list[object]:
        return Designer.current.widgets()


class Broken(BaseException):
    """An error of Designer's own that derives from BaseException, as sd's APIException does."""


class Designer:
    """One state of Designer's history: its steps, newest first; what was undone, newest first; and how an undo
    lands: at a pass of the event loop (`lands`; never with False; only the first `landing` undos, given it), after
    `stray` passes that change the Undo menu and land nothing. A pass that wakes nothing fires the running timer; with
    `quitting`, as Qt does once it quits, every pass returns -1 at once, nothing done. `current` is the Designer the
    fakes act on."""

    current: 'Designer'

    def __init__(
        self,
        steps: list[str],
        lands: bool = True,
        stray: int = 0,
        quitting: bool = False,
        landing: float = math.inf,
    ) -> None:
        self.steps: list[str] = list(steps)
        self.undone: list[str] = []
        self.lands, self.stray, self.quitting, self.landing = lands, stray, quitting, landing
        self.manager = _Manager(self.undo_sent)
        self.undo_menu, self.redo_menu = _MenuState(self.steps), _MenuState(self.undone)
        self.buttons = [
            QToolButton('undo-button', self.undo_menu, self.manager),
            QToolButton('redo-button', self.redo_menu, self.manager),
        ]
        self.invoked: list[Slot] = []  # the manager's slots called
        self.flags: list[Flag] = []  # each loop pass's flags
        self.timers: list[QTimer] = []
        self.clock = 0.0
        self.sent = False  # an undo was sent, not landed yet
        self.raises: BaseException | None = None  # what allWidgets() raises
        self.after_sent: BaseException | None = None  # what a pass of the loop raises once the undo was sent
        self.removing_raises: BaseException | None = None  # what removing an event filter raises
        Designer.current = self

    def widgets(self) -> list[object]:
        if self.raises is not None:
            raise self.raises
        return [object(), *self.buttons]

    def undo_sent(self) -> None:
        self.invoked.append('undo()')
        self.sent = True

    def pass_events(self, loop: QEventLoop, flags: Flag) -> int:
        """One pass of `loop`: a stray change, the undo landing, or an error once the undo was sent (`after_sent`).
        Unless that woke the loop (its quit()), the running timer then fires, the clock moved on by its interval, and
        must wake it. Returns what exec() returns."""
        self.flags.append(flags)
        if len(self.flags) > 100:  # a test fails rather than hang on a loop that never ends
            raise AssertionError('the loop spins: exec() called %d times' % len(self.flags))
        if self.quitting:
            return -1
        gc.collect()  # a wrapper dropped is gone before the next event, as in Designer
        if self.sent and self.after_sent is not None:
            raise self.after_sent
        if self.stray:
            self.stray -= 1
            self.undo_menu.notify(QEvent.Type.ActionAdded)
        elif self.sent and self.lands and self.landing > 0:
            self.sent = False
            self.landing -= 1
            self.undone.insert(0, self.steps.pop(0))
            for menu in (self.undo_menu, self.redo_menu):
                menu.notify(QEvent.Type.ActionRemoved)
                menu.notify(QEvent.Type.ActionAdded)
        if not loop.quitted:
            timer = next(timer for timer in self.timers if timer.active)  # none: the loop would wait forever
            self.clock += timer.interval_ms / 1000
            timer.active = not timer.single
            timer.timeout.emit()
            if not loop.quitted:  # a real exec() returns only on quit() (REVIEW.md TST-850)
                raise AssertionError("the loop would wait forever: its timer's timeout doesn't quit it")
        return 0


def modules() -> dict[str, types.ModuleType]:
    """The PySide6 modules the rollback imports, made of these fakes."""
    qtcore = types.ModuleType('PySide6.QtCore')
    vars(qtcore).update(QEvent=QEvent, QEventLoop=QEventLoop, QMetaMethod=_Method, QObject=QObject, QTimer=QTimer)
    qtwidgets = types.ModuleType('PySide6.QtWidgets')
    vars(qtwidgets).update(QApplication=QApplication, QMenu=QMenu, QToolButton=QToolButton)
    qtgui = types.ModuleType('PySide6.QtGui')
    vars(qtgui).update(QAction=_Action)
    pyside = types.ModuleType('PySide6')
    vars(pyside).update(QtCore=qtcore, QtGui=qtgui, QtWidgets=qtwidgets)
    return {'PySide6': pyside, 'PySide6.QtCore': qtcore, 'PySide6.QtGui': qtgui, 'PySide6.QtWidgets': qtwidgets}


Recorded = list[bytes | None]  # an undo transaction opened, by its name's bytes, or None for one committed


def install_sd(monkeypatch: pytest.MonkeyPatch, recorded: Recorded) -> type:
    """Puts the sd modules the code _with_undo sends imports in sys.modules for the test, and returns their
    SDHistoryUtils, whose functions a test may replace. SDHistoryUtils.newTransaction and commitTransaction are Python,
    as sd's are, and call getContext(), a Python function as sd's is, then its context's SDHistoryUtils_newTransaction
    or SDHistoryUtils_commitTransaction. Those two record each transaction opened and committed in `recorded`. In
    Designer they are C, reached through ctypes: here they are C too (list.append), so no trace event comes from them,
    but the two Python layers above them trace as sd's do (sd/api/sdhistoryutils.py). group_events reads `recorded`."""
    context = types.SimpleNamespace(
        SDHistoryUtils_newTransaction=recorded.append,
        SDHistoryUtils_commitTransaction=functools.partial(recorded.append, None),
    )
    sd = types.ModuleType('sd')
    vars(sd)['getContext'] = lambda: context

    class SDHistoryUtils:
        @staticmethod
        def newTransaction(name: str) -> None:
            sd.getContext().SDHistoryUtils_newTransaction(name.encode('utf-8'))

        @staticmethod
        def commitTransaction() -> None:
            sd.getContext().SDHistoryUtils_commitTransaction()

    history = types.ModuleType('sd.api.sdhistoryutils')
    vars(history)['SDHistoryUtils'] = SDHistoryUtils
    api = types.ModuleType('sd.api')
    vars(api)['sdhistoryutils'] = history
    for name, module in (('sd', sd), ('sd.api', api), ('sd.api.sdhistoryutils', history)):
        monkeypatch.setitem(sys.modules, name, module)
    return SDHistoryUtils


def group_events(recorded: Recorded) -> list[GroupEvent]:
    """The undo transactions install_sd's fakes recorded, opened and committed, each with the name of the last one opened."""
    events: list[GroupEvent] = []
    name = ''
    for item in recorded:
        if item is not None:
            name = item.decode('utf-8')
        events.append(('enter' if item is not None else 'commit', name))
    return events
