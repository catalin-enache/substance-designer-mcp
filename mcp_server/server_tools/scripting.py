"""Running code in Designer: execute_designer_code, run_designer_script, cancel_designer_job."""

import os

from .core import _bridge, _send, _tool, _with_undo


@_tool()
def cancel_designer_job() -> str:
    """Abort the script currently running in Designer (and drop queued ones). Takes effect the
    next time Python code runs, so one long C++ call (e.g. graph.compute()) finishes first."""
    return _send({'cmd': 'cancel'}, wait=10).get('output', '')


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
def run_designer_script(path: str, timeout_s: int = 600) -> str:
    """Run a Python file inside Substance Designer; `__file__` is set to its absolute path.
    All changes form one undo step named after the file. Aborted after `timeout_s` seconds
    (0 = no limit in Designer). A script queued behind another can wait up to 15 minutes before it
    starts; this call stops waiting 15 minutes + `timeout_s` (15 minutes if 0) + 1 minute after it
    is sent, while the script goes on (cancel_designer_job stops it)."""
    path = os.path.abspath(os.path.expanduser(path))
    with open(path, encoding='utf-8') as f:
        return _bridge(_with_undo(f.read(), 'Claude: ' + os.path.basename(path)), path, timeout_s)
