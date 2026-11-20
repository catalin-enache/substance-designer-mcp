"""Files that count the bytes read from them, for the tests that a hook stops reading a big file early (REVIEW.md
AGT-45). `Counter.open` stands in for the hook's `open` in binary mode."""

import contextlib
import dataclasses
import io
from collections.abc import Buffer, Iterator


@dataclasses.dataclass
class Counter:
    """The bytes read from the files `open` opened, since the last `at_most`."""

    read: int = 0

    def open(self, path: str, mode: str, buffering: int) -> io.BufferedReader:
        """`open(path, 'rb', buffering)`, counting the bytes read from the file. The hook gives the size it reads at a
        time (its `BLOCK`): Python's default changed in 3.14 (REVIEW.md TST-588)."""
        assert mode == 'rb', 'only binary reads are counted: %s' % mode
        return io.BufferedReader(_Counted(path, self), buffering)

    @contextlib.contextmanager
    def at_most(self, limit: int, what: object) -> Iterator[None]:
        """Check that the block reads under `limit` bytes. `what` names the block in the failure."""
        self.read = 0
        yield
        assert self.read < limit, (what, self.read)


class _Counted(io.FileIO):
    """A file that adds the bytes read from it to `counter`."""

    def __init__(self, path: str, counter: Counter) -> None:
        super().__init__(path)
        self.counter = counter

    def readinto(self, buffer: Buffer, /) -> int | None:
        count = super().readinto(buffer)
        self.counter.read += count or 0
        return count
