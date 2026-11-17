"""lifecycle's "without a crash" checks: one wait for crash dumps at the end of its run, each dump given to the step it
appeared in (CrashWatch), shared by the checks of one run (watching_crashes). Only lifecycle/checks.py uses it; its
tests: tests/unit/test_selftest_crash_dumps.py."""

import contextlib
import os
import time
from collections.abc import Callable, Iterator, Sequence
from typing import Protocol


class _Common(Protocol):
    """What CrashWatch uses of common.py."""

    POLL_S: float

    def check(self, tool: str, name: str, ok: bool, detail: str = '') -> None: ...

    def crash_dumps(self, ports: Sequence[int] = (), run_port: bool = True) -> set[str]: ...

    def dumps_may_come(self, ports: Sequence[int], before: set[str], run_port: bool = True) -> bool: ...

    def new_dumps(self, after: set[str], before: set[str]) -> set[str]: ...


def _common() -> _Common:
    """common.py, imported when a check or a dump is looked up, not here: common imports this module (Ctx), and tests
    replace common's check and crash_dumps."""
    from test_all_tools import common

    return common


class CrashWatch:
    """The "without a crash" checks of a category's steps, settled with one wait at its end instead of
    new_crash_dumps' 10 s after each step: Designer writes a dump a few seconds after it goes down (REVIEW.md TST-21:
    about 3 s), so a dump appearing after the last step still counts. The wait lasts while a dump may still come
    (`coming`: common.dumps_may_come, looked at every POLL_S), `wait_s` at most (REVIEW.md SRV-151: 10 s, whatever
    happened). step() notes the dumps there before a step that
    could crash a Designer (a quit, by its own ports); check() records a check of it, held until settle(), which waits
    once and gives each new dump to the latest step that started before the dump was written, among those looking at
    its folder, failing that step's checks (or a check of its own, if the step's check stopped before recording any). A
    crash during the launch after a quit is given to that quit. later() holds a clean-up until then, as one deleting a
    Designer's home unless it holds a dump would delete a late one."""

    def __init__(
        self,
        wait_s: float = 10,
        find: Callable[[Sequence[int]], set[str]] | None = None,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
        mtime: Callable[[str], float] = os.path.getmtime,
        coming: Callable[[Sequence[int], set[str]], bool] | None = None,
    ) -> None:
        self.wait_s, self.clock, self.sleep, self.mtime = wait_s, clock, sleep, mtime
        self.find = find or (lambda ports: _common().crash_dumps(ports))
        self.coming = coming or (lambda ports, before: _common().dumps_may_come(ports, before))
        self.steps: list[_WatchedStep] = []
        self.clean_ups: list[Callable[[], None]] = []

    def step(self, ports: Sequence[int] = ()) -> '_WatchedStep':
        step = _WatchedStep(self.clock(), self.find(ports), tuple(ports))
        self.steps.append(step)
        return step

    def check(self, step: '_WatchedStep', tool: str, name: str, ok: bool, detail: str = '') -> None:
        step.checks.append((tool, name, bool(ok), detail))

    def later(self, clean_up: Callable[[], None]) -> None:
        self.clean_ups.append(clean_up)

    def settle(self) -> None:
        try:
            if self.steps:
                ports = sorted({port for step in self.steps for port in step.ports})
                # the dumps there before the first step; for a port's home first looked at later, those there then
                shared = self.find(())
                before = self.steps[0].before | {d for step in self.steps for d in step.before if d not in shared}
                deadline, poll_s = self.clock() + self.wait_s, _common().POLL_S
                # the clock first: given no wait, it looks at nothing (REVIEW.md TST-458)
                while self.clock() < deadline and self.coming(ports, before):
                    self.sleep(poll_s)
            found = {i: _common().new_dumps(self.find(step.ports), step.before) for i, step in enumerate(self.steps)}
            for dump in set().union(*found.values()):
                try:
                    written = self.mtime(dump)
                except OSError:  # gone already: given to the last step looking at it
                    written = float('inf')
                looking = [i for i, new in found.items() if dump in new]
                started = [i for i in looking if self.steps[i].start <= written]
                self.steps[max(started or looking)].dumps.add(dump)
            for step in self.steps:
                if step.dumps and not step.checks:  # its check stopped before recording any
                    _common().check(
                        'self-test', 'no crash dump during a check that stopped early', False, str(sorted(step.dumps))
                    )
                for tool, name, ok, detail in step.checks:
                    if step.dumps:
                        detail = '%s; new crash dumps: %s' % (detail, sorted(step.dumps))
                    _common().check(tool, name, ok and not step.dumps, detail)
        finally:
            for clean_up in self.clean_ups:
                clean_up()


class _WatchedStep:
    def __init__(self, start: float, before: set[str], ports: tuple[int, ...]) -> None:
        self.start, self.before, self.ports = start, before, ports
        self.checks: list[tuple[str, str, bool, str]] = []
        self.dumps: set[str] = set()


class _HoldsCrashWatch(Protocol):
    """What watching_crashes uses of a ctx (common.Ctx): the category's CrashWatch, or None outside one."""

    crash_watch: CrashWatch | None


@contextlib.contextmanager
def watching_crashes(ctx: _HoldsCrashWatch) -> Iterator[CrashWatch]:
    """The CrashWatch of the category running (lifecycle.run), or, for a check run alone (a scratch run), one of its
    own, settled when the check ends: one wait either way, at the end of the outermost user."""
    running: CrashWatch | None = getattr(ctx, 'crash_watch', None)
    if running is not None:
        yield running
        return
    ctx.crash_watch = watch = CrashWatch()
    try:
        yield watch
    finally:
        ctx.crash_watch = None
        watch.settle()
