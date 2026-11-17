"""Fakes for the waits woken by AppKit's notifications (designer_helpers/mac_window.py; ROADMAP item 101): what
_MacWindow.notices returns, and CoreFoundation's notification center as _Notices calls it."""

from collections.abc import Sequence

LOCAL = 100  # CoreFoundation's local notification center, as Center hands it out


class Notices:
    """_MacWindow.notices' result, faked: the notifications it relays, its signal, and how many times it was opened and
    closed."""

    def __init__(self, names: Sequence[str]) -> None:
        self.names = tuple(names)
        self.fired = 'notified of ' + ', '.join(names)
        self.opened = 0
        self.closed = 0

    def open(self) -> None:
        self.opened += 1

    def close(self) -> None:
        self.closed += 1


class Center:
    """CoreFoundation's functions _Notices calls, faked: the observers registered in the local center, each with the
    notifications it observes, as (name, sender), and the callback each registration was given."""

    def __init__(self) -> None:
        self.observers: dict[int, list[tuple[int, int | None]]] = {}
        self.callbacks: list[object] = []

    def CFNotificationCenterGetLocalCenter(self) -> int:
        return LOCAL

    def CFNotificationCenterAddObserver(
        self, center: int, observer: int, callback: object, name: int, sender: int | None, behaviour: int
    ) -> None:
        assert center == LOCAL
        self.observers.setdefault(observer, []).append((name, sender))
        self.callbacks.append(callback)

    def CFNotificationCenterRemoveEveryObserver(self, center: int, observer: int) -> None:
        assert center == LOCAL
        self.observers.pop(observer, None)
