"""Reading node_stats' comparison lines in measure's checks."""

import re

# node_stats(against=...)'s line for one channel: its name, the largest difference, the mean, the pixels over the
# tolerance
DIFF = re.compile(r'^(\w+) diff: max ([\d.]+) at \(\d+,\d+\)  mean ([\d.]+)  over [^:]+: (\d+) px', re.M)
REFUSED = 'Error executing tool node_stats: '  # how a node_stats error's text starts, as the client gives it


def diffs(t: str) -> dict[str, tuple[float, float, int]]:
    """node_stats(against=...)'s 'R diff: max 0.2 at (0,0)  mean 0.2  over 0.002: 262144 px (100.00%)' lines ->
    {'R': (0.2, 0.2, 262144)}: per channel the largest difference, the mean, and how many pixels differ by more than
    the tolerance."""
    return {name: (float(top), float(mean), int(over)) for name, top, mean, over in DIFF.findall(t)}


def compared(t: str) -> str:
    """node_stats' result from its `against` line on, or all of it without one. A check's detail is this part, as
    common.check prints 150 characters and the stats lines before it would fill them (REVIEW.md TST-839)."""
    found = re.search(r'^against .*', t, re.M | re.S)
    return found.group(0) if found else t


def refusal(t: str) -> str:
    """A node_stats error's text without the client's prefix, so that the 150 characters common.check prints hold
    both nodes and their sizes or formats (REVIEW.md TST-839)."""
    return t.removeprefix(REFUSED)
