"""Runs inside Designer: keeps a task in Qt's global thread pool, which Designer's shutdown waits for and which can't end
once Python has stopped: the hang seen with Adobe's licence check, on demand (lifecycle.py). Only in a Designer the
self-test started."""

import sys
import time

from PySide6.QtCore import QRunnable, QThreadPool


def hold() -> None:
    while True:
        time.sleep(0.5)


held = QRunnable.create(hold)
held.setAutoDelete(False)
vars(sys)['_selftest_held_task'] = held  # kept alive: Python would delete a task still in the pool
print('HELD=%s' % QThreadPool.globalInstance().tryStart(held))
