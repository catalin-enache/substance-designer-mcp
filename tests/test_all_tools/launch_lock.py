"""The pool's lock on Designers starting and quitting (workers.py). In a pool (workers.py), lifecycle
has two windows during which no other Designer of the run may start (or quit, which also writes Designer's settings):
from its own launch to the end of its hand-over check, which needs its Designer to be the last one started
(`session.instancePID`), and while its record is aside, when its Designer counts as the user's and launch_designer
refuses to start any next to it.

Files in the run's folder, named by the environment of every worker (Gate.env): the lock, and a folder of marks, one
per Designer starting or quitting. Each side announces before it looks: the pool marks a start, then sees whether the
lock exists (if it does, it takes the mark back and starts nothing yet); a holder creates the lock (one at a time, its name in it, so the pool can remove it after a worker killed inside a window),
then waits for the marks to go. So neither can miss the other. Without that environment (a scratch run, one run) nothing is held."""

import contextlib
import os
import time
from collections.abc import Callable, Iterator

LOCK_ENV = 'SD_SELFTEST_LAUNCH_LOCK'
CHANGING_ENV = 'SD_SELFTEST_LAUNCHING'
POLL_S = 0.2


class Gate:
    """The pool's side: a mark for each Designer it starts, until it answers or its worker ends."""

    def __init__(self, root: str) -> None:
        self.lock = os.path.join(root, 'launch.lock')
        self.changing = os.path.join(root, 'changing')
        os.makedirs(self.changing, exist_ok=True)

    def env(self) -> dict[str, str]:
        return {LOCK_ENV: self.lock, CHANGING_ENV: self.changing}

    def try_begin(self, name: str) -> bool:
        """Mark `name` starting, unless the lock is held: then no mark, and False."""
        mark = os.path.join(self.changing, name)
        open(mark, 'w').close()
        if os.path.exists(self.lock):
            os.remove(mark)
            return False
        return True

    def end(self, name: str) -> None:
        with contextlib.suppress(FileNotFoundError):
            os.remove(os.path.join(self.changing, name))

    def worker_ended(self, name: str) -> None:
        """A worker ended, however it did: its mark goes, and the lock if it held it (the lock names its holder). One
        killed inside a window never ran its finally, which held every start and quit for ever (REVIEW.md TST-235)."""
        self.end(name)
        with contextlib.suppress(FileNotFoundError):
            with open(self.lock, encoding='utf-8') as f:
                holder = f.read()
            if holder == name:
                os.remove(self.lock)


def _paths() -> tuple[str, str] | None:
    lock, changing = os.environ.get(LOCK_ENV), os.environ.get(CHANGING_ENV)
    return (lock, changing) if lock and changing else None


@contextlib.contextmanager
def held(
    own: str | None = None,
    timeout_s: float = 300,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Iterator[None]:
    """lifecycle's side: no Designer of the run starts or quits meanwhile. Taken once no other holder has it (one at a
    time), then held from when the
    Designers starting or quitting have done so (timeout_s at most: one that never answers doesn't hold it forever),
    but for the start of `own`, the worker holding it: the pool clears that mark once its Designer answers, which it
    starts inside the lock."""
    paths = _paths()
    if paths is None:
        yield
        return
    lock, changing = paths
    taken = clock()
    deadline = taken + timeout_s
    mine = False
    waited = 0.0
    try:
        while not mine and clock() < deadline:  # another holder's window first
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                mine = True
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(own or '')  # its holder, for the pool (Gate.worker_ended)
            except FileExistsError:
                sleep(POLL_S)
        while set(os.listdir(changing)) - {own} and clock() < deadline:
            sleep(POLL_S)
        waited = clock() - taken
        yield
    finally:
        if mine:
            with contextlib.suppress(FileNotFoundError):
                os.remove(lock)
        # its two windows, measured (2026-11-10: 4.6 to 5.7 s waiting and 16.3 to 16.6 s held for the first, 0 to 1.2 s
        # and 2.4 to 3.5 s for the second): how long the pool's starts waited for it
        print(
            'launch lock: %.1f s waiting for Designers starting or quitting, held %.1f s in all'
            % (waited, clock() - taken)
        )


@contextlib.contextmanager
def changing(
    name: str,
    sleep: Callable[[float], None] = time.sleep,
    timeout_s: float = 300,
    clock: Callable[[], float] = time.monotonic,
) -> Iterator[None]:
    """A worker's side, around its Designer quitting: once no lock is held (timeout_s at most, as held(): a lock left
    behind mustn't hold the quit for ever, REVIEW.md TST-235), marked meanwhile."""
    paths = _paths()
    if paths is None:
        yield
        return
    lock, folder = paths
    mark = os.path.join(folder, name)
    deadline = clock() + timeout_s
    while True:
        open(mark, 'w').close()
        if not os.path.exists(lock):
            break
        if clock() >= deadline:
            print('launch lock: still held after %d s; quitting all the same' % timeout_s)
            break
        os.remove(mark)
        sleep(POLL_S)
    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.remove(mark)
