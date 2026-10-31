"""quit_designer's fallback (designer_helpers), run with fake windows, timer and clock: when it
forces the process to end with os._exit and when it leaves Designer's own shutdown to finish
(REVIEW.md HLP-12, HLP-17, HLP-19, HLP-23, TST-32)."""

import os
import re
import sys
import time
import types
from collections.abc import Callable
from typing import Any, cast
from unittest import mock

import pytest

import designer_helpers  # conftest puts mcp_server on sys.path

RunTimers = Callable[[float], float]  # run_timers(until_s): fires the timers due, returns the seconds since the quit


class Window:
    def __init__(self, refuses: bool = False, busy_s: float = 0) -> None:
        # busy_s: a close handler that runs that long, letting Qt's event loop run meanwhile (timers
        # fire inside it), as a slow or stuck handler does
        self.visible, self.refuses, self.busy_s = True, refuses, busy_s
        # set by the fixture: run_timers, the clock and the quit's start time
        self.while_busy: tuple[RunTimers, Clock, float] | None = None

    def isVisible(self) -> bool:
        return self.visible

    def close(self) -> None:
        if self.busy_s:
            run_timers, clock, start = cast(tuple[RunTimers, Clock, float], self.while_busy)
            end = clock.now + self.busy_s
            run_timers(end - start)
            clock.now = max(clock.now, end)
        if not self.refuses:
            self.visible = False


class Exits(list[int]):
    at: float | None = None  # seconds after the quit when os._exit was called


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


QuitWith = Callable[[list[Window]], tuple[RunTimers, Exits]]  # the quit_with fixture


@pytest.fixture
def quit_with(monkeypatch: pytest.MonkeyPatch) -> QuitWith:
    """quit_with(windows) runs quit_designer and returns (run_timers, exits): run_timers(until_s)
    fires the timers due up to until_s seconds after the quit, advancing the clock to each."""
    sd = mock.MagicMock()
    # every sd module the helpers import, and the packages above each (sd.api.sbs.x: sd, sd.api, sd.api.sbs)
    imported = re.findall(r'^\s*(?:from|import) (sd(?:\.\w+)*)', designer_helpers.source(), re.M)
    for name in sorted({'.'.join(m.split('.')[:i]) for m in imported for i in range(1, m.count('.') + 2)}):
        monkeypatch.setitem(sys.modules, name, sd)
    sd.getContext().getSDApplication().getPackageMgr().getUserPackages.return_value = []
    timers: list[tuple[float, Callable[[], None]]] = []
    clock = Clock()
    start = clock.now
    app = types.SimpleNamespace(windows=[])
    app.topLevelWidgets = lambda: app.windows
    qtcore = types.SimpleNamespace(
        QTimer=types.SimpleNamespace(singleShot=lambda ms, fn: timers.append((clock.now + ms / 1000.0, fn)))
    )
    qtwidgets = types.SimpleNamespace(QApplication=types.SimpleNamespace(instance=lambda: app))
    monkeypatch.setitem(sys.modules, 'PySide6', types.SimpleNamespace(QtCore=qtcore, QtWidgets=qtwidgets))
    monkeypatch.setitem(sys.modules, 'PySide6.QtCore', qtcore)
    monkeypatch.setitem(sys.modules, 'PySide6.QtWidgets', qtwidgets)
    monkeypatch.setattr(time, 'monotonic', clock)
    helpers: Any = types.ModuleType('helpers_under_test')  # the helpers as sent to Designer: one script
    exec(compile(designer_helpers.source(), 'designer_helpers', 'exec'), helpers.__dict__)
    exits = Exits()

    def fake_exit(code: int) -> None:
        exits.append(code)
        exits.at = clock.now - start

    monkeypatch.setattr(os, '_exit', fake_exit)

    def run(windows: list[Window]) -> tuple[RunTimers, Exits]:
        app.windows = windows
        helpers.quit_designer()

        def run_timers(until_s: float) -> float:
            while timers and not exits:
                timers.sort(key=lambda t: t[0])
                if timers[0][0] - start > until_s:
                    break
                due, fn = timers.pop(0)
                clock.now = max(clock.now, due)
                fn()
            return clock.now - start

        for w in windows:
            w.while_busy = (run_timers, clock, start)
        return run_timers, exits

    return run


def test_a_window_that_refuses_to_close_is_forced_at_5_s(quit_with: QuitWith) -> None:
    run_timers, exits = quit_with([Window(), Window(refuses=True)])
    assert run_timers(60) == pytest.approx(5) and exits == [0]


def test_a_designer_left_running_with_every_window_closed_is_forced_at_the_give_up_time(quit_with: QuitWith) -> None:
    # REVIEW.md HLP-23 / TST-32: every window closed, but the process didn't go on to quit
    run_timers, exits = quit_with([Window(), Window()])
    run_timers(34)
    assert exits == []  # its own shutdown is left to finish until then
    assert run_timers(60) == pytest.approx(35, abs=1) and exits == [0]


def test_a_slow_close_handler_is_left_to_finish(quit_with: QuitWith) -> None:
    # REVIEW.md HLP-17: its handler still runs at 5 s (the fallback fires inside it), then closes
    run_timers, exits = quit_with([Window(busy_s=7), Window()])
    run_timers(34)
    assert exits == []


def test_a_stuck_close_handler_is_forced_at_the_give_up_time(quit_with: QuitWith) -> None:
    # REVIEW.md HLP-19: a handler that never returns keeps its window showing; forced about 35 s in
    run_timers, exits = quit_with([Window(busy_s=600), Window()])
    run_timers(60)
    assert exits == [0] and exits.at == pytest.approx(35, abs=1)
