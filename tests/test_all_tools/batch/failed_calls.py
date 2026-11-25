"""What batch's rollback checks share: a call failing after a change to the self-test graph, and whether that graph is
as before it."""

from collections.abc import Awaitable, Callable
from typing import Literal

from test_all_tools.common import ROLLED_BACK, SD_RUN, Ctx, ToolArgs, check, described, positions, script_path, text

ERROR = '[an error result] '  # before the text of an error result (call_text): no tool's text holds it


async def call_text(ctx: Ctx, tool: str, args: ToolArgs) -> str:
    """A call's text, after ERROR when it is an error result."""
    r_ = await ctx.c(tool, args)
    return (ERROR if r_.is_error else '') + text(r_)


async def compared(ctx: Ctx, call: Callable[[], Awaitable[str]]) -> tuple[str, bool]:
    """The call's text, and whether the self-test graph is as before it. The nodes it left are deleted, also when it
    raises, so that a rollback that failed leaves the next check the graph it read (REVIEW.md TST-845)."""
    before = await described(ctx)
    try:
        t = await call()
    finally:
        now = await described(ctx)
        for node in sorted(set(positions(now)) - set(positions(before))):
            await ctx.c('apply_edits', {'ops': [{'op': 'delete', 'node': node}], **ctx.G})
    return t, now == before


async def rolled_back(ctx: Ctx, tool: str, name: str, says: list[str], call: Callable[[], Awaitable[str]]) -> None:
    """The check that `call` fails after a change to the self-test graph and is rolled back: the graph as before, and
    its text (the result and anything else the call gives) says each of `says` and that its step was taken back."""
    t, same = await compared(ctx, call)
    missing = [each for each in [*says, ROLLED_BACK] if each not in t]
    last = t.strip().splitlines()[-1] if t.strip() else 'no answer'
    check(
        tool,
        name,
        not missing and same,
        ('' if same else 'the graph changed | ') + ('missing %s | ' % missing if missing else '') + last,
    )


def during_rollback(what: Literal['cancel', 'queue']) -> ToolArgs:
    """run_designer_script's arguments for batch/designer_scripts/during_rollback.py: a call failing after a change, a
    second client acting while its rollback runs, `what` it does ('cancel' or 'queue')."""
    return {'path': script_path('batch/during_rollback'), 'timeout_s': 120, 'args': {'what': what, 'client': SD_RUN}}
