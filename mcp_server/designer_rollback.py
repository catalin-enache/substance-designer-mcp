"""Runs inside Designer: takes back named undo steps, each only while it is on top of Designer's history, waiting for
each to land. Every undo the server sends goes through one function, undo_steps():

- roll_back(), the undo step of a tool call that failed, with the edits it holds. The server sends this file's text
  with the code of every call it groups into one undo step (`_with_undo`, server_tools/core.py). Once the call's code
  has raised and its group has committed, that code calls roll_back() with the step's name: the call's label and a tag
  of its own. roll_back() undoes the step on top only when its name is exactly that one, and never twice.
- undo_session(), undo_edits' undo of the session's last calls (server_tools/undo.py), by the names the server
  remembers, the steps in the way included only when the agent asks.

What Designer does, measured in Designer 16.0.7 (2026-11-24 and 2026-11-25; the batch category's "designer facts" and
rollback checks):

- Designer keeps one history for the whole app, every package's steps in it, the newest on top. The sd API can't undo.
- The toolbar's `undo-button` and `redo-button` each have a default action belonging to Alg::Gui::HistoryActionsMgr,
  whose slots undo() and redo() take the top step back or forward. Each action holds a dropdown menu listing the steps'
  names, newest first. A step is listed as its group commits, before any event is processed. The Undo dropdown lists
  the newest LISTED steps, 25: once the top one is undone, one more older step shows at its bottom.
- An undo transaction opened and never committed stays open: every later change goes into it, through a tool or
  outside any group, and none is listed. An undo then takes back the open transaction's newest change, not a listed
  step. One commit lists it all, under the name it was opened with. The plugin's abort left one so, landing in
  UndoGroup's exit or on its `with` line as the block ended (the plugin's _make_tracer). The server's calls commit
  theirs out of an abort's reach: Python's tracing is off from their code's end to the commit (server_tools/core.py,
  _with_undo; REVIEW.md SRV-273, SRV-276).
- A read tool's call can make a step: preview_node's did, adding a temporary output node to a node with no texture
  yet. describe_node's code makes steps of Designer's own for an atomic or a library node (its temporary package and
  node, the library package it opens), and so does search_nodes' first scan of the library with no compositing graph
  in the editor (a temporary package). One undo group holds each call's: undoing that step puts the open packages back
  as before. The server counts the steps of such calls as reads (server_tools/core.py, SessionStep).
- QMetaObject.invokeMethod refuses the slot's name as bytes, which its stubs ask for, and takes a str; the slot's
  QMetaMethod, found by its signature, invokes it as the stubs say.
- An undo lands as Designer processes the events after it. The dropdowns' actions are then removed and added again
  (ActionRemoved, ActionAdded), the graph already as before. 2000 added nodes took 2.9 s to undo.
- In one Designer, a menu taken from action.menu() read as deleted (PySide6's "Internal C++ object already deleted")
  once the action's wrapper was dropped, 200 times in 200, and never while it was held. A Designer just started didn't
  show it, so it isn't a check of the self-test; History holds the wrappers while it is used.
"""

from typing import NamedTuple, TypedDict

from PySide6.QtCore import QEvent, QEventLoop, QMetaMethod, QObject, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QToolButton

MANAGER = 'Alg::Gui::HistoryActionsMgr'  # the class of the object owning the toolbar's Undo and Redo actions
BUTTONS = ('undo-button', 'redo-button')  # the toolbar buttons' object names: no UI text, so any language works
LISTED = 25  # the newest steps the Undo dropdown lists, at most (the module docstring)


class _Dropdown(NamedTuple):
    """A toolbar button, its action and the action's dropdown menu: held together, which keeps the menu valid (the
    module docstring)."""

    button: QToolButton
    action: QAction
    menu: QMenu


class History:
    """Designer's history as its toolbar shows it: the Undo and Redo dropdowns, each listing the steps' names, newest
    first, and the manager's undo() slot."""

    def __init__(self, undo: _Dropdown, redo: _Dropdown, manager: QObject, slot: QMetaMethod) -> None:
        self.held = (undo, redo)
        self.undo, self.redo = undo.menu, redo.menu
        self.manager, self.slot = manager, slot


def _names(menu: QMenu) -> list[str]:
    """The steps' names a dropdown lists, newest first."""
    return [action.text() for action in menu.actions()]


def _top(menu: QMenu) -> str | None:
    """The newest step's name in a dropdown, or None if it lists none."""
    actions = menu.actions()
    return actions[0].text() if actions else None


def _failed(e: BaseException) -> str:
    """The state of an undo stopped by its own error."""
    return 'failed: %s: %s' % (type(e).__name__, e)


def history() -> History | None:
    """Designer's history, or None unless the toolbar has exactly one Undo and one Redo button, each with a dropdown, of
    the history manager, which has its undo() slot."""
    found: dict[str, list[_Dropdown]] = {name: [] for name in BUTTONS}
    for widget in QApplication.allWidgets():
        if not isinstance(widget, QToolButton) or widget.objectName() not in found:
            continue
        action = widget.defaultAction()
        menu, manager = action.menu(), action.parent()
        if isinstance(menu, QMenu) and manager is not None and manager.inherits(MANAGER):
            found[widget.objectName()].append(_Dropdown(widget, action, menu))
    if any(len(each) != 1 for each in found.values()):
        return None
    (undo,), (redo,) = found[BUTTONS[0]], found[BUTTONS[1]]
    manager = undo.action.parent()
    index = manager.metaObject().indexOfMethod('undo()')
    return History(undo, redo, manager, manager.metaObject().method(index)) if index >= 0 else None


class _Changed(QObject):
    """Quits `loop` whenever a dropdown's actions change, as they do when an undo lands."""

    def __init__(self, loop: QEventLoop) -> None:
        super().__init__()
        self.loop = loop

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.ActionAdded, QEvent.Type.ActionRemoved):
            self.loop.quit()
        return False


def _undo(found: History, label: str, limit_s: float) -> str:
    """Sends one undo, then processes events, the user's input left for later, until the Redo dropdown lists other
    steps than before, `label` on top: 'undone'. Its top alone wouldn't show the landing: the step undone before may
    have the same name, as Designer names the user's steps by what they did. Once `limit_s` is over, a safety net: 'not landed: after <limit_s> s'. Once Qt is quitting,
    when the loop returns at once and no timer fires (designer_helpers/waits.py, _until): 'not landed: Qt is quitting'.
    If Qt says the slot wasn't called, the result is "failed: Designer's undo() slot wasn't called", and nothing was
    sent. An error once the undo was sent is 'not landed: <the error>', as the undo may still land; one before it is
    raised."""
    loop = QEventLoop()
    changed = _Changed(loop)
    limit = QTimer()
    limit.setSingleShot(True)
    limit.timeout.connect(loop.quit)
    menus = (found.undo, found.redo)
    for menu in menus:
        menu.installEventFilter(changed)
    try:
        limit.start(int(limit_s * 1000))
        before = _names(found.redo)
        if not found.slot.invoke(found.manager):  # Qt says the slot wasn't called: nothing was sent
            return "failed: Designer's undo() slot wasn't called"
        try:
            while _names(found.redo) == before or _top(found.redo) != label:
                if not limit.isActive():
                    return 'not landed: after %g s' % limit_s
                if loop.exec(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents) < 0:
                    return 'not landed: Qt is quitting'
        except BaseException as e:  # never an abort: the rollback runs untraced (roll_back)
            return 'not landed: %s: %s' % (type(e).__name__, e)
        return 'undone'
    finally:
        try:
            limit.stop()
            for menu in menus:
                menu.removeEventFilter(changed)
        except BaseException:
            pass  # the outcome is known by then, and a filter on a menu that is gone went with it


NO_HISTORY = "failed: no Undo and Redo dropdowns of Designer's history found"


def undo_steps(found: History, names: list[str], limit_s: float) -> tuple[list[str], str]:
    """Undoes the steps named `names`, newest first, each only while it is on top of the Undo dropdown, waiting until
    each lands, `limit_s` at most each (_undo). Stops at the first that isn't on top or doesn't land. Returns the names
    undone, and what happened:

    - 'undone': every step was undone;
    - "not ours: <the top step's name in quotes, or None>": the next step wasn't on top, and nothing was sent for it;
    - 'not landed: <why>': the next step's undo was sent, and wasn't seen landing, by the limit or by its own error;
    - 'failed: <why>': nothing was sent for the next step, as Designer's undo() slot wasn't called, or by its own
      error.

    Raises nothing. Its caller runs it untraced, so no abort of the plugin's lands between an undo sent and its
    landing."""
    undone: list[str] = []
    try:
        for name in names:
            top = _top(found.undo)
            if top != name:
                return undone, 'not ours: %s' % ('None' if top is None else "'%s'" % top)  # as it is (SRV-271)
            state = _undo(found, name, limit_s)
            if state != 'undone':
                return undone, state
            undone.append(name)
        return undone, 'undone'
    except BaseException as e:  # sd's APIException is a BaseException; no abort reaches it (the docstring)
        return undone, _failed(e)


def roll_back(label: str, limit_s: float) -> str:
    """Undoes the step on top of Designer's history if its name is `label` (undo_steps), and waits until the undo
    lands, `limit_s` at most. Returns what happened, for the server (server_tools/core.py, _failure): undo_steps'
    state, or 'failed: <why>' when Designer's history wasn't found, or by its own error. Nothing was sent unless it
    says 'undone' or 'not landed'.

    Raises nothing: its own error never takes the place of the call's. The caller runs it untraced, so no abort of the
    plugin's lands in it."""
    try:
        found = history()
        if found is None:
            return NO_HISTORY
        return undo_steps(found, [label], limit_s)[1]
    except BaseException as e:  # sd's APIException is a BaseException; no abort reaches it (the docstring)
        return _failed(e)


class Undone(TypedDict):
    """What undo_session did, for the server (server_tools/undo.py)."""

    listed: int  # how many steps the Undo dropdown listed, before anything was undone
    planned: list[str]  # the steps to undo, newest first: down to the last of the edits asked for
    undone: list[str]  # those undone, newest first
    gone: list[str]  # the session's names not undone, not listed, that would be if in the history (undo_session)
    state: str  # undo_steps' state, or 'others', 'beyond', 'none', or 'failed: <why>' before anything was planned


def undo_session(steps: list[tuple[str, bool, bool]], count: int, include_others: bool, limit_s: float) -> Undone:
    """Undoes the session's last `count` edits, from the top of the Undo dropdown down to the last of them, newest
    first (undo_steps). `steps` are the session's calls' steps, oldest first: each name, whether it is an edit's,
    which counts, and whether undo_edits undid it. The steps of its reads on the way are undone along, uncounted, and
    so are other steps, but only with `include_others`. Nothing is undone, the state saying why, when:

    - 'others': steps that aren't the session's are in the way, and `include_others` is False;
    - 'beyond': fewer than `count` edits are listed, the dropdown lists LISTED, and some edit not undone is older than
      the session's oldest step listed: it may be in the history below the list, where nothing can check it. An edit
      undone sits on the Redo list, or nowhere, and counts again once a Redo lists it;
    - 'none': no edit is listed;
    - 'failed: <why>': Designer's history wasn't found, or by its own error.

    With fewer than `count` listed and none older, it undoes those listed. The dropdown lists the newest steps with
    none left out, so a step not listed that is newer than the session's oldest one listed, or any not listed while the
    dropdown lists fewer than LISTED, isn't in the history: it is said gone (REVIEW.md SRV-266). A step undone is
    never said gone, as it may be on the Redo list. Raises nothing. The caller runs it untraced, as roll_back is."""
    done: Undone = {'listed': 0, 'planned': [], 'undone': [], 'gone': [], 'state': 'none'}
    try:
        found = history()
        if found is None:
            done['state'] = NO_HISTORY
            return done
        listed = _names(found.undo)
        session = {name for name, _, _ in steps}
        edits = {name for name, edit, _ in steps if edit}
        asked = [i for i, name in enumerate(listed) if name in edits][:count]  # the edits asked for, by their place
        done['planned'] = listed[: asked[-1] + 1] if asked else []  # the steps below the last of them stay
        full = len(listed) >= LISTED
        done['listed'] = len(listed)
        first = next((i for i, (name, _, _) in enumerate(steps) if name in listed), len(steps))  # its oldest listed
        done['gone'] = [name for name, _, undone in steps[first if full else 0 :] if name not in listed and not undone]
        # an edit not undone may be below the list
        if full and len(asked) < count and any(edit and not undone for _, edit, undone in steps[:first]):
            done['state'] = 'beyond'
        elif not done['planned']:
            done['state'] = 'none'
        elif not include_others and any(name not in session for name in done['planned']):
            done['state'] = 'others'
        else:
            done['undone'], done['state'] = undo_steps(found, done['planned'], limit_s)
    except BaseException as e:  # sd's APIException is a BaseException; no abort reaches it (the docstring)
        done['state'] = _failed(e)
    return done
