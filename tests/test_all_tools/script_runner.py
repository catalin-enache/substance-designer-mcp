"""run_designer_script."""

import os

from .common import Ctx, check, text


async def run(ctx: Ctx) -> None:
    c, scratch = ctx.c, ctx.scratch
    # --- script runner
    script = os.path.join(scratch, 'probe_script.py')
    with open(script, 'w', encoding='utf-8') as f:
        f.write(
            "import sd\nprint('script file', __file__.endswith('probe_script.py'), "
            "sd.getContext().getSDApplication().getVersion())\nprint('utf-8: → é ✓')\n"
        )
    t = text(await c('run_designer_script', {'path': script, 'timeout_s': 30}))
    check('run_designer_script', '__file__ + sd', 'script file True' in t, t)
    # a UTF-8 script arrives intact whatever the server's locale (REVIEW.md SRV-11)
    check('run_designer_script', 'UTF-8 text survives', 'utf-8: → é ✓' in t, t)
