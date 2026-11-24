"""Running code in Designer: execute_designer_code, run_designer_script, cancel_designer_job."""

import json
import os
from typing import Annotated

from pydantic import Field

from .core import JsonObject, _bridge, _control, _tool, _with_undo

# the two code tools' timeout_s
Timeout = Annotated[
    int,
    Field(
        description='Seconds after which the script is aborted (0 = no limit in Designer). As with '
        'cancel_designer_job, the abort waits for the next Python code to run.'
    ),
]


# gated=False: stopping a runaway script must never wait for the guide
@_tool(read_only=False, destructive=False, idempotent=True, open_world=False, gated=False)
def cancel_designer_job() -> str:
    """Abort the script currently running in Designer (and drop queued ones). Takes effect the
    next time Python code runs, so one long C++ call (e.g. graph.compute()) finishes first."""
    return _control('cancel', wait=10)


@_tool(read_only=False, destructive=True, idempotent=False, open_world=True, scripting=True)
def execute_designer_code(
    code: Annotated[str, Field(description='The Python code to run.')],
    undo_label: Annotated[str, Field(description="The undo step's name.")] = 'Claude: code',
    timeout_s: Timeout = 120,
) -> str:
    """Run Python inside Substance Designer (full `sd` API) and return printed output and errors.
    All changes form one undo step (Ctrl+Z in Designer reverts them). A script queued
    behind another can wait up to 15 minutes before it starts, and one still queued then is dropped, never run late.
    This call stops waiting 15 minutes + `timeout_s` (15 minutes if 0) + 1 minute after it is sent, about 31 minutes
    for 0, while the script goes on (cancel_designer_job stops it)."""
    return _bridge(_with_undo(code, undo_label), '<execute_designer_code>', timeout_s)


# finite=False: its args reach Designer as JSON, which keeps inf and nan
@_tool(read_only=False, destructive=True, idempotent=False, open_world=True, scripting=True, finite=False)
def run_designer_script(
    path: Annotated[str, Field(description='The Python file to run.')],
    timeout_s: Timeout = 600,
    args: Annotated[
        JsonObject | None,
        Field(
            description='JSON values that reach the script as the global dict `ARGS`, empty without any; a script '
            "checked by mypy reads it with `ARGS: Args = globals()['ARGS']`, Args a TypedDict of its keys."
        ),
    ] = None,
) -> str:
    """Run a Python file inside Substance Designer; `__file__` is set to its absolute path.
    Only this tool sets `ARGS`.
    All changes form one undo step named after the file. A script queued behind another can wait up to 15 minutes before it
    starts, and one still queued then is dropped, never run late. This call stops waiting 15 minutes + `timeout_s`
    (15 minutes if 0) + 1 minute after it is sent, while the script goes on (cancel_designer_job stops it)."""
    path = os.path.abspath(os.path.expanduser(path))
    with open(path, encoding='utf-8') as f:
        script = _with_undo(f.read(), 'Claude: ' + os.path.basename(path))
    # on a line of its own, before the script's own compile, so its line numbers stay its own
    return _bridge('ARGS = __import__("json").loads(%r)\n' % json.dumps(args or {}) + script, path, timeout_s)
