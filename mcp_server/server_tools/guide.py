"""The guide: get_guide and the designer://agents-guide resource."""

from .core import _agent_guide, _session, server


@server.tool()
def get_guide() -> str:
    """The full guide for agents driving Substance Designer (AGENTS.md): rules that protect the
    user's work, which tool to use when, sd API and Designer pitfalls, verified facts. Call it
    right before the first Designer tool call of a session (not otherwise), read all of it, then
    tell the user you have read it."""
    _session['guide_read'] = True
    guide = _agent_guide()
    return guide + (
        '\n\n---\nEnd of the Designer guide (%d characters, complete). Now tell the user in '
        'one line that you have read the Designer guide, then continue.' % len(guide)
    )


@server.resource(
    'designer://agents-guide',
    name='agents-guide',
    mime_type='text/markdown',
    description='Notes and API gotchas for agents driving Substance Designer (AGENTS.md).',
)
def agents_guide() -> str:
    return _agent_guide()
