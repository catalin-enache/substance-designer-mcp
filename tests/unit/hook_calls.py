"""The lead's hook (`.claude/hooks/large_reads.py`) loaded or run as Claude Code runs it, and the calls Claude Code sends
it, for test_large_reads.py (REVIEW.md TST-608)."""

import importlib.util
import json
import os
import subprocess
import types
from pathlib import Path
from typing import TypedDict


def load_script(path: str | os.PathLike[str]) -> types.ModuleType:
    """The Python file at `path`, loaded as a module named after it: for a script no folder on the path holds, such as
    `.claude/hooks/large_reads.py`."""
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    assert spec and spec.loader, path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HookInput(TypedDict, total=False):
    """A call's `tool_input`: a Bash command's, a Read's, a PyCharm `read_file`'s or search's, or a web fetch's or
    search's."""

    command: str
    description: str
    run_in_background: bool
    file_path: str
    offset: object  # a test passes values the tools refuse too: a string, a bool, a float
    limit: object
    projectPath: str
    url: str
    prompt: str
    query: str
    q: str  # PyCharm's searches
    pattern: str  # Grep's and Glob's


class HookResponse(TypedDict, total=False):
    """A Bash call's `tool_response`, which PostToolUse carries."""

    stdout: str
    stderr: str
    interrupted: bool
    isImage: bool
    noOutputExpected: bool
    persistedOutputPath: str
    persistedOutputSize: int


class HookCall(TypedDict, total=False):
    """A hook's call, as Claude Code sends it on stdin: the fields of PreToolUse, PostToolUse and PostToolUseFailure
    that `.claude/hooks/large_reads.py` reads or the tests send, and a subagent's `agent_id` and `agent_type`."""

    session_id: str
    prompt_id: str  # the same for every call made in one turn
    cwd: str
    hook_event_name: str
    tool_name: str
    tool_input: HookInput
    tool_use_id: str  # sent by the tests, read by no hook
    tool_response: HookResponse
    error: str  # PostToolUseFailure: "Exit code N", then the output
    is_interrupt: bool  # sent by the tests, read by no hook
    agent_id: str
    agent_type: str


def run_hook(
    command: str, project: str, payload: HookCall, more_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """A hook's command run as Claude Code runs it: through sh, for the project at `project`, with `payload` as JSON on
    stdin. `more_env` adds to its environment."""
    env = {'PATH': '/usr/bin:/bin', 'CLAUDE_PROJECT_DIR': project, **(more_env or {})}
    return subprocess.run(
        ['sh', '-c', command], input=json.dumps(payload), env=env, capture_output=True, text=True, timeout=60
    )
