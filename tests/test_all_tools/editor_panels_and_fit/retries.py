"""Readings and shots of the window checks taken again when the pool's other Designers get in the way: they handed
activation over as they quit (workers.py), and came in front of Designer's windows as they started, before
launch_designer opened them hidden (REVIEW.md SRV-152). A reading with a window of another app in front of the window
it reads changes (REVIEW.md TST-417), and so does a way of the focus check in which Designer became the active app
during the shot (REVIEW.md TST-418). Those windows and that activation came in bursts longer than the tries, so these
checks also read while no worker of the pool starts or quits its Designer (no_designer_starting). lifecycle's own
launches and quits, and other scratch runs, go on meanwhile (REVIEW.md TST-467).
"""

import contextlib
from collections.abc import Iterator

from test_all_tools import launch_lock
from test_all_tools.common import Ctx, text
from test_all_tools.editor_panels_and_fit import window_states
from test_all_tools.editor_panels_and_fit.window_states import at_rest

TRIES = 3  # the most times a reading or a way of the focus check is taken (the module docstring)


async def without_others_in_front(ctx: Ctx, code: str, tries: int = TRIES) -> tuple[str, int]:
    """What `code` printed, run again while it found a window in front of the window it read that the checks didn't
    make (window_states.nothing_in_front), at most `tries` times; and the tries taken. Each run is followed by
    at_rest, also when it fails."""
    tried, t = 0, ''
    while tried < tries:
        tried += 1
        try:
            t = text(await ctx.c('execute_designer_code', {'code': ctx.helper_source + code}))
        finally:
            await at_rest(ctx.c, ctx.helper_source)
        if window_states.nothing_in_front(t):
            break
    return t, tried


def tries_said(printed: str, tried: int) -> str:
    """A check's detail's end for a reading taken `tried` times (without_others_in_front): nothing for one try."""
    if not window_states.nothing_in_front(printed):
        return '; a window in the way in each of %d tries' % tried  # in front, or reached by the click (TST-419)
    return '; %d tries' % tried if tried > 1 else ''


@contextlib.contextmanager
def no_designer_starting() -> Iterator[None]:
    """The pool's launch lock, held by this category's worker (launch_lock.held, as lifecycle holds it): no worker of
    the pool starts or quits its Designer meanwhile, so none of those hands activation over (REVIEW.md TST-417).
    lifecycle's own launches and quits within its checks go on (REVIEW.md TST-467). Outside a pool (a scratch run, one
    run) nothing is held."""
    with launch_lock.held(own=__name__.split('.')[1]):
        yield
