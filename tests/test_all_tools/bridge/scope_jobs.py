"""Two jobs, for the checks that a job leaves nothing of its scope alive once it ends: the first keeps a weak reference
to an object only its scope holds, and the second reads it."""

from textwrap import dedent

from test_all_tools.common import Ctx, check, text

# The first of two jobs: an object only its scope holds, and a weak reference to it waiting on `sys` for the second
_KEPT = dedent("""
    import sys
    import weakref


    class _Kept:
        def method(self):  # its globals: the job's scope
            pass


    _kept = _Kept()
    sys.mcp_selftest_kept = weakref.ref(_kept)
""")
_FREED = dedent("""\
    import gc
    import sys

    gc.collect()
    ref = sys.__dict__.pop('mcp_selftest_kept', None)
    print('FREED' if ref is not None and ref() is None else 'HELD' if ref is not None else 'NO_REF')""")


async def scope_freed(ctx: Ctx, job: str, what: str) -> None:
    """Checks that `job`, run after _KEPT in one job, leaves the object _KEPT made to be freed: a second job reads it."""
    t = text(await ctx.c('execute_designer_code', {'code': _KEPT + job + "\nprint('KEPT_SET')"}))
    after = text(await ctx.c('execute_designer_code', {'code': _FREED}))
    check(
        'execute_designer_code',
        what,
        'KEPT_SET' in t and 'FREED' in after,
        '%s / %s' % (t.strip()[-80:], after.strip()),
    )
