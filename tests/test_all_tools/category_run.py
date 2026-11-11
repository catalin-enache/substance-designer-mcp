"""How one category of the live self-test runs, in a run of the suite (__main__.py) or on its own (alone.py): on a Ctx
of its own (Ctx.fresh), after its own preparation, then cleaned up, so the next category sees nothing it prepared or
left: a change to one category's setup can't reach any other (the user's choice, 2026-11-10).

A category's preparation is the `prepare(ctx)` of its folder's preparations.py, if it has one: it builds what its
checks read, from tool calls and common.py only, and records no check. One that fails, by raising (common.Unprepared:
a tool call that failed) or with a failed check of alone.run's setup, is the category's environment failing: one
failed check says so, and its checks don't run. A check that raises fails, and the next one still runs. Afterwards
the self-test's graphs are closed (CLEAN), the library packages the category loaded are unloaded, and the self-test
graph's snapshots are removed."""

import importlib
import time
import traceback
from collections.abc import Callable, Sequence
from typing import NamedTuple

from test_all_tools import common
from test_all_tools.common import (
    CLEAN,
    Ctx,
    Step,
    library_packages,
    remove_test_snapshots,
    restore_library_packages,
    text,
)

PAUSE_S = 0.5  # between the clean-up's calls, so graph views are torn down first


class Ran(NamedTuple):
    prepared: bool  # its environment was built, and its checks ran
    cleaned: bool  # the clean-up after it recorded no failure


def category_of(step: Step) -> str:
    """The folder of the category a step belongs to (test_all_tools.<category>.checks), or its module's name."""
    parts = step.__module__.split('.')
    return parts[1] if len(parts) == 3 and parts[0] == 'test_all_tools' and parts[2] == 'checks' else parts[-1]


def preparation(step: Step) -> Step | None:
    """The prepare(ctx) of the step's category (<category>/preparations.py), or None if it has none."""
    parts = step.__module__.split('.')
    if not (len(parts) == 3 and parts[0] == 'test_all_tools' and parts[2] == 'checks'):
        return None
    name = 'test_all_tools.%s.preparations' % parts[1]
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError as e:
        if e.name == name:
            return None
        raise
    prepare: Step = module.prepare
    return prepare


def _failures() -> int:
    return sum(not ok for oks in common.results.values() for ok in oks)


def _last_line() -> str:
    return traceback.format_exc().strip().splitlines()[-1]


async def run_category(
    ctx: Ctx,
    steps: Sequence[Step],
    setup: Step | None = None,
    announce: Callable[[Step], None] | None = None,
) -> Ran:
    """The steps (a category's run, or checks of it), all of one category, after its preparation and then `setup`
    (alone.run's), on ctx: a fresh one (Ctx.fresh). announce(step) is called before each step."""
    category = category_of(steps[0])
    libs_before = await library_packages(ctx.c)
    try:
        prepared = await _prepared(ctx, steps[0], setup, category)
        if prepared:
            for step in steps:
                if announce is not None:
                    announce(step)
                try:
                    await step(ctx)
                except Exception:
                    print(traceback.format_exc())
                    name = '%s.%s reaches its end' % (category, step.__qualname__)
                    common.check('self-test', name, False, _last_line())
    finally:
        cleaned = await _cleaned(ctx, libs_before)
    return Ran(prepared=prepared, cleaned=cleaned)


async def _prepared(ctx: Ctx, first: Step, setup: Step | None, category: str) -> bool:
    """Whether the category's preparation, then setup, built its environment; one failed check says so if not."""
    before = _failures()
    why = 'a check of the setup failed'
    try:
        prepare = preparation(first)
        if prepare is not None:
            await prepare(ctx)
        if setup is not None:
            await setup(ctx)
        if _failures() == before:
            return True
    except Exception:
        print(traceback.format_exc())
        why = _last_line()
    common.check('self-test', '%s: its own environment is prepared' % category, False, why)
    return False


async def _cleaned(ctx: Ctx, libs_before: list[str] | None) -> bool:
    """CLEAN, then the library packages put back as they were, then the self-test graph's snapshots removed: whether
    that recorded no failure."""
    before = _failures()
    print('clean-up: %s' % text(await ctx.c('execute_designer_code', {'code': CLEAN})).strip())
    time.sleep(PAUSE_S)
    await restore_library_packages(ctx.c, libs_before)
    remove_test_snapshots()
    return _failures() == before
