"""The guide: get_guide and the designer://agents-guide resource."""

from mcp.server.mcpserver.exceptions import ToolError

from .core import _agent_guide, _session, server


@server.tool()
def get_guide(part: str = 'core') -> str:
    """The guide for agents driving Substance Designer (GUIDE.md). `part='core'`: rules that protect the
    user's work, which tool to use when, verified facts. Call it right before the first Designer tool
    call of a session (not otherwise), read all of it, then tell the user you have read it; every tool but cancel_designer_job refuses until you have.
    `part='scripting'`: the sd API and Designer UI pitfalls; read it before writing raw `sd` or Qt code
    (execute_designer_code, run_designer_script), which refuse until you have; then tell the user you have read it."""
    if part not in ('core', 'scripting'):
        raise ToolError("part is 'core' or 'scripting', not %r" % part)
    guide = _agent_guide(part)
    if part == 'scripting':
        _session['scripting_read'] = True
        return guide + (
            '\n\n---\nEnd of the scripting part of the Designer guide (%d characters, complete). Now tell the user in '
            'one line that you have read the scripting part, then continue.' % len(guide)
        )
    _session['guide_read'] = True
    return guide + (
        '\n\n---\nEnd of the core of the Designer guide (%d characters, complete). Now tell the user in '
        'one line that you have read the Designer guide, then continue.' % len(guide)
    )


@server.resource(
    'designer://agents-guide',
    name='agents-guide',
    mime_type='text/markdown',
    description='Notes and API gotchas for agents driving Substance Designer (GUIDE.md).',
)
def agents_guide() -> str:
    try:
        return _agent_guide()
    except ToolError as e:
        return str(e)
