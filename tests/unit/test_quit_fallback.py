"""quit_designer's fallback (designer_helpers), run with fake windows, timer and clock: when it
forces the process to end with os._exit and when it leaves Designer's own shutdown to finish
(REVIEW.md HLP-12, HLP-17, HLP-19, HLP-23, TST-32)."""
import importlib.util
import os
import sys
import time
import types
from unittest import mock

import pytest

from conftest import ROOT


class Window:
    def __init__(self, refuses=False, busy_s=0):
        # busy_s: a close handler that runs that long, letting Qt's event loop run meanwhile (timers
        # fire inside it), as a slow or stuck handler does
        self.visible, self.refuses, self.busy_s = True, refuses, busy_s
        self.while_busy = None                     # set by the fixture: run_timers, and the clock

    def isVisible(self):
        return self.visible

    def close(self):
        if self.busy_s:
            run_timers, clock, start = self.while_busy
            end = clock.now + self.busy_s
            run_timers(end - start)
            clock.now = max(clock.now, end)
        if not self.refuses:
            self.visible = False


class Exits(list):
    at = None                                       # seconds after the quit when os._exit was called


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def quit_with(monkeypatch):
    """quit_with(windows) runs quit_designer and returns (run_timers, exits): run_timers(until_s)
    fires the timers due up to until_s seconds after the quit, advancing the clock to each."""
    sd = mock.MagicMock()
    for name in ('sd', 'sd.api', 'sd.api.apiexception', 'sd.api.sbs', 'sd.api.sbs.sdsbscompgraph',
                 'sd.api.sdapplication', 'sd.api.sdproperty', 'sd.api.sdtypeenum'):
        monkeypatch.setitem(sys.modules, name, sd)
    sd.getContext().getSDApplication().getPackageMgr().getUserPackages.return_value = []
    timers = []
    clock = Clock()
    start = clock.now
    qtcore = types.SimpleNamespace(QTimer=types.SimpleNamespace(
        singleShot=lambda ms, fn: timers.append((clock.now + ms / 1000.0, fn))))
    qtwidgets = types.SimpleNamespace(QApplication=types.SimpleNamespace(instance=lambda: app))
    monkeypatch.setitem(sys.modules, 'PySide6', types.SimpleNamespace(QtCore=qtcore, QtWidgets=qtwidgets))
    monkeypatch.setitem(sys.modules, 'PySide6.QtCore', qtcore)
    monkeypatch.setitem(sys.modules, 'PySide6.QtWidgets', qtwidgets)
    monkeypatch.setattr(time, 'monotonic', clock)
    spec = importlib.util.spec_from_file_location('helpers_under_test',
                                                  os.path.join(ROOT, 'mcp_server', 'designer_helpers.py'))
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    exits = Exits()

    def fake_exit(code):
        exits.append(code)
        exits.at = clock.now - start
    monkeypatch.setattr(helpers.os, '_exit', fake_exit)
    app = types.SimpleNamespace(windows=[])
    app.topLevelWidgets = lambda: app.windows

    def run(windows):
        app.windows = windows
        helpers.quit_designer()

        def run_timers(until_s):
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


def test_a_window_that_refuses_to_close_is_forced_at_5_s(quit_with):
    run_timers, exits = quit_with([Window(), Window(refuses=True)])
    assert run_timers(60) == pytest.approx(5) and exits == [0]


def test_a_designer_left_running_with_every_window_closed_is_forced_at_the_give_up_time(quit_with):
    # REVIEW.md HLP-23 / TST-32: every window closed, but the process didn't go on to quit
    run_timers, exits = quit_with([Window(), Window()])
    run_timers(34)
    assert exits == []                              # its own shutdown is left to finish until then
    assert run_timers(60) == pytest.approx(35, abs=1) and exits == [0]


def test_a_slow_close_handler_is_left_to_finish(quit_with):
    # REVIEW.md HLP-17: its handler still runs at 5 s (the fallback fires inside it), then closes
    run_timers, exits = quit_with([Window(busy_s=7), Window()])
    run_timers(34)
    assert exits == []


def test_a_stuck_close_handler_is_forced_at_the_give_up_time(quit_with):
    # REVIEW.md HLP-19: a handler that never returns keeps its window showing; forced about 35 s in
    run_timers, exits = quit_with([Window(busy_s=600), Window()])
    run_timers(60)
    assert exits == [0] and exits.at == pytest.approx(35, abs=1)
