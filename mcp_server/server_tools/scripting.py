"""Running code in Designer: execute_designer_code, run_designer_script, cancel_designer_job."""

import json
import os
from typing import Any

from .core import _bridge, _control, _tool, _with_undo


@_tool()
def cancel_designer_job() -> str:
    """Abort the script currently running in Designer (and drop queued ones). Takes effect the
    next time Python code runs, so one long C++ call (e.g. graph.compute()) finishes first."""
    return _control('cancel', wait=10)


@_tool()
def execute_designer_code(code: str, undo_label: str = 'Claude: code', timeout_s: int = 120) -> str:
    """Run Python inside Substance Designer (full `sd` API) and return printed output and errors.
    All changes form one undo step named `undo_label` (Ctrl+Z in Designer reverts them).
    The script is aborted after `timeout_s` seconds (0 = no limit in Designer). A script queued
    behind another can wait up to 15 minutes before it starts; this call stops waiting 15 minutes
    + `timeout_s` (15 minutes if 0) + 1 minute after it is sent, about 31 minutes for 0, while the
    script goes on (cancel_designer_job stops it)."""
    return _bridge(_with_undo(code, undo_label), '<execute_designer_code>', timeout_s)


@_tool()
def run_designer_script(path: str, timeout_s: int = 600, args: dict[str, Any] | None = None) -> str:
    """Run a Python file inside Substance Designer; `__file__` is set to its absolute path.
    `args` (JSON values) reach the script as the global dict `ARGS`, empty without any; a script
    checked by mypy reads it with `ARGS: dict[str, Any] = globals()['ARGS']`. Only this tool sets it.
    All changes form one undo step named after the file. Aborted after `timeout_s` seconds
    (0 = no limit in Designer). A script queued behind another can wait up to 15 minutes before it
    starts; this call stops waiting 15 minutes + `timeout_s` (15 minutes if 0) + 1 minute after it
    is sent, while the script goes on (cancel_designer_job stops it)."""
    path = os.path.abspath(os.path.expanduser(path))
    with open(path, encoding='utf-8') as f:
        script = _with_undo(f.read(), 'Claude: ' + os.path.basename(path))
    # on a line of its own, before the script's own compile, so its line numbers stay its own
    return _bridge('ARGS = __import__("json").loads(%r)\n' % json.dumps(args or {}) + script, path, timeout_s)
