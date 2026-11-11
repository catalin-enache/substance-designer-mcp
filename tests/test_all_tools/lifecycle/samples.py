"""The sample of a Designer's threads that a forced end names (quit_designer, launch_designer: ROADMAP item 70), read
for lifecycle's checks."""

import re
from pathlib import Path

from test_all_tools.common import QUIT_SAMPLED

# A call in macOS's sample: "    +   820 main  (in Adobe Substance 3D Designer) + 12432  [0x...]", deeper calls further
# right, branches marked with ! : |; the count's column is the call's depth
CALL = re.compile(r' *\+[ !:|+]*?(\d+) (.+?) {2}\(in (.+?)\)')
# the kernel's and pthread's waits, under every wait: left out, as the check's detail is short; the C library's calls
# (exit and its handlers) stay (REVIEW.md TST-311)
SYSTEM = ('libsystem_kernel', 'libsystem_pthread')


def sampled(result: str) -> tuple[str, str]:
    """From a tool's result naming a sample: its text, and the detail for a check, where the main thread was (the path
    left out: check() prints 150 characters, which the calls fill: REVIEW.md TST-312); ('', the result) when it names
    none, or the file is gone."""
    found = re.search(re.escape(QUIT_SAMPLED) + r' (\S+)', result)
    if not found or not Path(found.group(1)).is_file():
        return '', result
    stacks = Path(found.group(1)).read_text(encoding='utf-8', errors='replace')
    return stacks, main_thread(stacks)


def main_thread(stacks: str, frames: int = 6) -> str:
    """The main thread's heaviest path in a sample, its deepest `frames` calls but the kernel's and pthread's, deepest
    first, without their arguments: sample lists each call's callees heaviest first, so the path is the run of lines
    each one deeper than the last."""
    lines = stacks.splitlines()
    start = next((i for i, line in enumerate(lines) if 'com.apple.main-thread' in line), None)
    if start is None:
        return 'no main thread in the sample'
    path: list[str] = []
    depth = -1
    for line in lines[start + 1 :]:
        call = CALL.match(line)
        if call is None or call.start(1) <= depth:  # the next thread, or a lighter callee: the path has ended
            break
        depth = call.start(1)
        if not call.group(3).startswith(SYSTEM):
            path.append(_bare(call.group(2).strip()))
    return ' < '.join(reversed(path[-frames:])) or 'no calls in its sample'


def _bare(name: str) -> str:
    """A call's name without its arguments: the balanced (...) at its end, and a " const" after it; an Objective-C
    method, [...], whole (REVIEW.md TST-311)."""
    if name.endswith(']'):
        return name
    name = name.removesuffix(' const')
    if not name.endswith(')'):
        return name
    depth = 0
    for i in range(len(name) - 1, 0, -1):
        depth += {')': 1, '(': -1}.get(name[i], 0)
        if depth == 0:
            return name[:i]
    return name
