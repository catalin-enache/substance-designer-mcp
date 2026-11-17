"""Waiting in Designer for something to happen: woken by the callbacks that say it did, looking again every TICK ms
where none comes, with a limit in case it never does (AGENTS.md: callbacks first, never a time measured here)."""

from .core import Callable, Protocol, QtCore, Sequence, _qt_app, cast

TICK = 100  # ms between looks where no callback wakes the wait


class _EventSpy(Protocol):
    """The event filter _event_signal returns: a QObject whose `fired` signal fires for each event it watches for. It is
    a Protocol, not a QObject subclass, so loading the helpers makes no Qt class. _unwatch removes it."""

    fired: QtCore.SignalInstance


def _settle(seconds: float) -> None:
    """Let Designer process its events for `seconds`. A wait for something to happen goes through _until instead
    (AGENTS.md)."""
    import time

    app = _qt_app()
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def _event_signal(
    watched: QtCore.QObject, kinds: Sequence[str], seen: Callable[[str], None] | None = None
) -> _EventSpy:
    """An event filter installed on `watched`, a Qt object: for each of its events of `kinds` (QEvent.Type names), calls
    `seen` with the event's kind (when given), then fires its `fired` signal, which a wait can be woken by (_until).
    The event goes on as usual. The caller removes it with _unwatch."""
    types: dict[QtCore.QEvent.Type, str] = {getattr(QtCore.QEvent.Type, kind): kind for kind in kinds}

    class Seen(QtCore.QObject):
        fired = QtCore.Signal()

        def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
            kind = types.get(event.type())
            if kind is not None:
                if seen is not None:
                    seen(kind)
                self.fired.emit()
            return False

    spy = Seen()
    watched.installEventFilter(spy)
    return spy


def _unwatch(watched: QtCore.QObject, spy: _EventSpy) -> None:
    """Removes the event filter `spy`, which _event_signal installed on `watched`."""
    watched.removeEventFilter(cast(QtCore.QObject, spy))


def _until(state: Callable[[], bool], limit: float, signals: Sequence[QtCore.SignalInstance] = ()) -> bool:
    """Waits for `state()` to be true, looking whenever one of `signals` fires and every TICK ms, while Designer goes
    on with its events. Gives up after `limit` s, a safety net, never the time the wait should take. Returns
    `state()`.

    The signals and the timers end the event loop's run (its quit, Qt's own slot), and `state()` is looked at here,
    between two runs: no Python runs in a slot. So an abort lands in this frame, not in a slot, where Qt drops it and
    the plugin raised it again at the finally's first line, which skipped the disconnects (REVIEW.md HLP-150: a
    function of the wait's stayed connected to the clipboard's dataChanged until Designer restarted).

    Once Designer quits (QCoreApplication.exit()), exec() returns -1 at once, running no event and no timer, so the wait
    ends there (REVIEW.md HLP-157: measured, it ran on, past its limit)."""
    if state():
        return True
    loop = QtCore.QEventLoop()  # the timers' parent too: they go with this frame, whatever an abort leaves undone
    tick = QtCore.QTimer(loop)
    tick.timeout.connect(loop.quit)
    end = QtCore.QTimer(loop)
    end.setSingleShot(True)
    end.timeout.connect(loop.quit)
    connected: list[QtCore.SignalInstance] = []
    try:
        for signal in signals:
            signal.connect(loop.quit)
            connected.append(signal)
        tick.start(TICK)
        end.start(int(limit * 1000))
        while not state() and end.isActive():
            if loop.exec() < 0:  # Qt's quit has run: no event comes to this loop any more
                break
    finally:
        tick.stop()
        end.stop()
        for signal in connected:
            signal.disconnect(loop.quit)
    return state()
