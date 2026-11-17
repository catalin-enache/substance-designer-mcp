"""The plugin's abort, raised at each traced event in turn, for tests of the helpers' put-backs (REVIEW.md HLP-171,
HLP-177). The plugin's tracer raises ScriptAborted at a traced event, and Python then stops tracing (sys.settrace's
docs), so whatever runs after the abort runs to its end."""

import sys
from collections.abc import Callable, Collection, Iterator
from types import CodeType, FrameType
from typing import Protocol

Tracer = Callable[[FrameType, str, object], 'Tracer | None']  # a function sys.settrace takes
LIMIT = 20000  # events at most: a safety net, in case a run never ends


class Abort(BaseException):
    """The plugin's ScriptAborted, a BaseException."""


class _HasCode(Protocol):
    """A function or a lambda: what has the code _codes reads."""

    @property
    def __code__(self) -> CodeType: ...


def _codes(of: object) -> set[CodeType]:
    """The code of a function or of a class's functions, with the code defined in it (its lambdas)."""
    if isinstance(of, type):
        return set().union(*(_codes(member) for member in vars(of).values()))
    code = getattr(of, '__code__', None)
    if not isinstance(code, CodeType):
        return set()
    found = {code}
    stack = [code]
    while stack:
        for const in stack.pop().co_consts:
            if isinstance(const, CodeType):
                found.add(const)
                stack.append(const)
    return found


def at_each_event(
    run: Callable[[], None],
    files: Collection[str],
    fresh: Callable[[], None],
    untraced: Collection[_HasCode | type] = (),
) -> Iterator[str]:
    """Calls `run` once per event Python traces in code from `files` (co_filename), the abort raised at that event:
    the first run at the first event, the next at the second, and so on, each after `fresh()`, untraced, has set the
    fakes up as they were. Not counted: `run` itself, and the functions
    and classes in `untraced`, fakes standing for C++ code, such as Qt's, where no abort can land. Yields where each
    abort landed ('function:line event'), once `run` has ended on it, so the caller can check what it left. Stops after
    the first run that ends without an abort: every event has had one. An abort that doesn't reach `run`'s caller
    fails: the job would go on."""
    skipped = set().union(_codes(run), *(_codes(fake) for fake in untraced))
    for n in range(1, LIMIT):
        seen = [0]
        landed: list[str] = []
        escaped = False

        def tracer(
            frame: FrameType, event: str, arg: object, n: int = n, seen: list[int] = seen, landed: list[str] = landed
        ) -> Tracer | None:
            if frame.f_code.co_filename not in files or frame.f_code in skipped:
                return None
            seen[0] += 1
            if seen[0] == n:
                landed.append('%s:%d %s' % (frame.f_code.co_name, frame.f_lineno, event))
                raise Abort
            return tracer

        fresh()
        previous = sys.gettrace()
        sys.settrace(tracer)
        try:
            run()
        except Abort:
            escaped = True
        finally:
            sys.settrace(previous)
        if not landed:
            return
        assert escaped, "the abort at %s didn't reach the caller" % landed[0]
        yield landed[0]
    raise AssertionError('the run went on past %d events' % LIMIT)
