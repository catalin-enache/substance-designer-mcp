"""run_designer_script."""

import os
from textwrap import dedent

from test_all_tools.common import Ctx, check, text


async def run(ctx: Ctx) -> None:
    c, scratch = ctx.c, ctx.scratch
    # --- script runner
    script = os.path.join(scratch, 'probe_script.py')
    with open(script, 'w', encoding='utf-8') as f:
        f.write(
            dedent("""\
                import sd
                print('script file', __file__.endswith('probe_script.py'), sd.getContext().getSDApplication().getVersion())
                print('utf-8: → é ✓')
            """)
        )
    t = text(await c('run_designer_script', {'path': script, 'timeout_s': 30}))
    check('run_designer_script', '__file__ + sd', 'script file True' in t, t)
    # a UTF-8 script arrives intact whatever the server's locale (REVIEW.md SRV-11)
    check('run_designer_script', 'UTF-8 text survives', 'utf-8: → é ✓' in t, t)
    # args reach the script as ARGS, whatever they hold, and its tracebacks keep its own line numbers
    args_script = os.path.join(scratch, 'probe_args.py')
    with open(args_script, 'w', encoding='utf-8') as f:
        f.write(
            dedent("""\
                print('ARGS=%r' % (ARGS,))
                raise ValueError('on line 2')
            """)
        )
    args = {'name': 'it\'s "quoted" → é', 'ids': [1, 2.5, None, True]}
    t = text(await c('run_designer_script', {'path': args_script, 'timeout_s': 30, 'args': args}))
    check('run_designer_script', 'args reach the script as ARGS', 'ARGS=%r' % (args,) in t, t)
    check('run_designer_script', 'a traceback keeps the line numbers of the script', 'probe_args.py", line 2' in t, t)
    t = text(await c('run_designer_script', {'path': args_script, 'timeout_s': 30}))
    check('run_designer_script', 'ARGS is empty without args', 'ARGS={}' in t, t)
