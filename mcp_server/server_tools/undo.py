"""Taking back this session's calls: undo_edits. The undo runs inside Designer, in one job (designer_rollback.py,
undo_session), by the names of the calls' undo steps the server remembers (core.py, STEPS). Every undo the server
sends, this one and a failed call's rollback, goes through the same function there (undo_steps)."""

import json
import re
from typing import Annotated, TypedDict

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from .core import ROLLBACK, ROLLBACK_LIMIT_S, STEPS, _bridge, _checked, _session, _tool

UNDO_LINE = 'UNDO_EDITS='  # starts the job's line of JSON saying what it did
ON_REDO = "They are on Designer's Redo list until the next change."
MARK_READ = " (a read of this session's: it changed nothing)"  # after a read's step in the reply
MARK_OTHER = " (not this session's)"  # after a step of the user's or another session's
NO_STEPS = (
    "Nothing undone: no call of this session's has its step in Designer's Undo list. Steps undone or rolled back "
    "already, and calls that changed nothing, don't count, and a reconnect starts a new session."
)
OTHERS = (
    "Nothing undone: steps that aren't this session's sit on top of the calls asked for: %s. Ask the user whether "
    'they may be undone too, and if they agree, call undo_edits again with include_others=true.'
)
BEYOND = (
    "Nothing undone: Designer's Undo list shows its newest %d steps, and only %d of the %d calls asked for are among "
    "them. An older step can't be checked, so none is undone."
)
FEWER = "Only %d of the %d calls asked for had a step in Designer's Undo list."
NO_HISTORY = "Nothing undone: Designer's history couldn't be read (%s)."
STEP_NOT_LANDED = (
    "the undo of %s was sent, but wasn't seen landing (%s): look with describe_graph or diff_graph before anything "
    "else, and don't undo again."
)
STEP_NOT_ON_TOP = 'the step on top was %s, not %s, so nothing more was undone.'
STEP_FAILED = "the undo of %s couldn't be sent (%s)."
# Designer's own steps of set_link_display's reload, as its Undo dropdown names them, untagged (REVIEW.md SRV-265;
# measured 2026-11-25, the link_display category's undo_edits check)
RELOAD_STEPS = ('Unset User Package', 'Unreference package', 'Unknown', 'Open Package(s)')
RELOAD_STEPS_NOTE = "Of these, %s are most likely Designer's own steps of set_link_display's reload of a package."


class _Undone(TypedDict):
    """What the job did: designer_rollback.Undone, as JSON."""

    listed: int
    planned: list[str]
    undone: list[str]
    gone: list[str]
    state: str


@_tool(read_only=False, destructive=True, idempotent=False, open_world=False)
def undo_edits(
    count: Annotated[int, Field(description="How many of this session's calls to take back, the newest first.")] = 1,
    include_others: Annotated[
        bool,
        Field(
            description="Also undo the steps that aren't this session's on top of those calls. Only once the user "
            'has agreed.'
        ),
    ] = False,
) -> str:
    """Undo your own work with `undo_edits`, and only with it. It takes back your calls, newest first. If steps that
    aren't yours sit on top of them (the user's, or another session's), it stops and names them: ask the user whether
    those may be undone too, and if they agree, call it again with `include_others`. With no such steps on top, undo as
    you need.
    Each step is undone only while it is the newest of Designer's Undo list, and seen landing before the next. A read's
    step on the way (preview_node, node_stats, check_tiling, compare_to_reference, sweep_param, describe_node,
    search_nodes), which changed nothing, is undone too and not counted. set_link_display's reload leaves steps of Designer's own on top of
    the calls before it: they count as not this session's, and a refusal names them so. The reply names every step
    undone, newest first, and marks the reads' and those that aren't this session's. Nothing is undone when the calls
    asked for aren't all among the newest 25 steps the Undo list shows.
    Only this session's calls count, and all agents of one session share its memory, its subagents included: each
    takes back the newest calls, whichever agent made them. A step undone counts again once a Redo puts it back on the
    Undo list. A step rolled back doesn't count, and a reconnect starts a new session. A call that made no step, such
    as code that changed nothing, still counts once it is older than the steps listed, so a count reaching past those
    is refused."""
    if count < 1:
        raise ToolError('count is 1 or more, not %d' % count)
    edits = {step.name for step in STEPS if step.edit}
    if not edits:
        raise ToolError(NO_STEPS)
    reads = {step.name for step in STEPS if not step.edit}
    call = 'print(%r + __import__("json").dumps(undo_session(%r, %d, %r, %r)))' % (
        UNDO_LINE,
        [tuple(step) for step in STEPS],
        count,
        include_others,
        ROLLBACK_LIMIT_S,
    )
    # untraced, as a failed call's rollback is (core.py, _with_undo): no abort lands between an undo sent and its landing
    text = _checked(_bridge('__import__("sys").settrace(None)\n' + ROLLBACK + '\n' + call + '\n', '<undo_edits>'))
    found = re.search(r'^%s(.*)$' % re.escape(UNDO_LINE), text, re.M)
    if not found:
        raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'the undo said nothing')
    done: _Undone = json.loads(found.group(1))
    undone, gone = set(done['undone']), set(done['gone'])
    STEPS[:] = [step._replace(undone=step.undone or step.name in undone) for step in STEPS if step.name not in gone]
    return _said(done, count, edits, reads)


def _quoted(name: str) -> str:
    """A step's name as the replies give it: in quotes, as it is. repr would escape the characters of the tag's
    invisible form (project_constants.py, TAG_PREFIX; REVIEW.md SRV-271)."""
    return "'%s'" % name


def _said(done: _Undone, count: int, edits: set[str], reads: set[str]) -> str:
    """undo_edits' reply for what the job did: the steps undone, or a ToolError saying why it undid nothing or
    stopped midway."""

    def named(names: list[str]) -> str:
        return ', '.join(_quoted(n) + (MARK_READ if n in reads else '' if n in edits else MARK_OTHER) for n in names)

    planned, undone, state = done['planned'], done['undone'], done['state']
    counted = len([name for name in planned if name in edits])
    word, _, why = state.partition(': ')
    if state == 'others':
        session = edits | reads
        others = [name for name in planned if name not in session]
        said = OTHERS % ', '.join(map(_quoted, others))
        reloaded = [_quoted(name) for name in others if name in RELOAD_STEPS]
        if reloaded and _session['package_reloaded']:
            said += ' ' + RELOAD_STEPS_NOTE % ', '.join(reloaded)
        raise ToolError(said)
    if state == 'beyond':
        raise ToolError(BEYOND % (done['listed'], counted, count))
    if state == 'none':
        raise ToolError(NO_STEPS)
    if word == 'failed' and not planned:
        raise ToolError(NO_HISTORY % why)
    if state == 'undone':
        plural = '' if len(undone) == 1 else 's'
        said = 'Undid %d step%s, newest first: %s. %s' % (len(undone), plural, named(undone), ON_REDO)
        return said + (' ' + FEWER % (counted, count) if counted < count else '')
    stopped_at = _quoted(planned[len(undone)])
    if word == 'not landed':
        stop = STEP_NOT_LANDED % (stopped_at, why)
    elif word == 'not ours':
        stop = STEP_NOT_ON_TOP % (why, stopped_at)
    else:
        stop = STEP_FAILED % (stopped_at, why)
    if not undone:
        raise ToolError('Nothing undone: ' + stop)
    raise ToolError(
        'Undid %d of the %d steps, newest first: %s. %s Then %s'
        % (len(undone), len(planned), named(undone), ON_REDO, stop)
    )
