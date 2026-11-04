"""Find a REVIEW.md finding by its ID, or the numbers used so far, from any folder of the repo.

Usage:
    python3 scripts/review_lookup.py HLP-56       the whole entry, from the file or its git history
    python3 scripts/review_lookup.py --last-used  a **Last used** line from git history, for a REVIEW.md that went missing

Exit status: 0 when it printed what was asked, 1 when it can't (it says why), 2 for a bad argument.
"""

# Annotations stay unevaluated: this script runs on the system Python, which can be older than 3.10
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REVIEW = 'REVIEW.md'
AN_ID = re.compile(r'[A-Z]+-\d+')
NEXT_ENTRY = re.compile(r'- \[.\] \*\*|## ')
HISTORY_ENTRY = re.compile(r'(?m)^[-+]- \[.\] \*\*([A-Z]+)-(\d+) ')
HISTORY_COUNTERS = re.compile(r'(?m)^[-+]\*\*Last used:\*\* (.*)$')
COUNTER = re.compile(r'([A-Z]+)-(\d+)')


class CannotAnswer(Exception):
    """What was asked can't be answered, and the message says why."""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ['git', '-C', str(root), *args], capture_output=True, text=True, encoding='utf-8', errors='replace'
    )


def _repo_root() -> Path:
    try:
        done = _git(Path.cwd(), 'rev-parse', '--show-toplevel')
    except OSError as e:
        raise CannotAnswer('git could not be run: %s' % e) from e
    if done.returncode != 0:
        raise CannotAnswer('not inside a git repository: run this from a folder of the repo')
    return Path(done.stdout.strip())


def _is_shallow(root: Path) -> bool:
    return _git(root, 'rev-parse', '--is-shallow-repository').stdout.strip() == 'true'


def entry_in(text: str, finding: str) -> str | None:
    """The finding's whole entry in a version of REVIEW.md: its title line, up to the next entry or section."""
    start = re.compile(r'- \[.\] \*\*%s ' % re.escape(finding))
    lines = text.splitlines()
    for first, line in enumerate(lines):
        if start.match(line):
            last = first + 1
            while last < len(lines) and not NEXT_ENTRY.match(lines[last]):
                last += 1
            return '\n'.join(lines[first:last]).rstrip() + '\n'
    return None


def lookup(root: Path, finding: str) -> str:
    """Read the current file first. A finding not there was removed by the newest commit that added or removed it, so
    the commit before that one still has it."""
    review = root / REVIEW
    if review.exists():
        entry = entry_in(review.read_text(encoding='utf-8', errors='replace'), finding)
        if entry:
            return entry
    commits = _git(root, 'log', '--format=%H', '-S**%s ' % finding, '--', REVIEW).stdout.split()
    if commits:
        entry = entry_in(_git(root, 'show', '%s^:%s' % (commits[0], REVIEW)).stdout, finding)
        if entry:
            return entry
    if _is_shallow(root):
        raise CannotAnswer(
            '%s is not in %s, and a shallow clone may not have the history: git fetch --unshallow' % (finding, REVIEW)
        )
    raise CannotAnswer('%s is not in %s or its git history: it never existed, or a squash lost it' % (finding, REVIEW))


def last_used(root: Path) -> str | None:
    """The highest number ever used for each prefix: as an entry, or on the **Last used** line, which is all that is left
    of a finding a squash lost. None when the history has no numbers."""
    if _is_shallow(root):
        raise CannotAnswer('a shallow clone may not have the numbers: git fetch --unshallow')
    history = _git(root, 'log', '-p', '-U0', '--format=', '--no-color', '--no-ext-diff', '--', REVIEW).stdout
    found = HISTORY_ENTRY.findall(history)
    for line in HISTORY_COUNTERS.findall(history):
        found.extend(COUNTER.findall(line))
    highest: dict[str, int] = {}
    for prefix, number in found:
        highest[prefix] = max(highest.get(prefix, 0), int(number))
    used = ['%s-%d' % (prefix, highest[prefix]) for prefix in sorted(highest) if highest[prefix]]
    return '**Last used:** %s.\n' % ', '.join(used) if used else None


def _finding_id(value: str) -> str:
    if not AN_ID.fullmatch(value):
        raise argparse.ArgumentTypeError('%r is not a finding ID, such as HLP-56' % value)
    return value


def _print(text: str) -> None:
    sys.stdout.buffer.write(
        text.encode('utf-8')
    )  # entries hold non-ASCII, which a Windows console's encoding may refuse
    sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    what = parser.add_mutually_exclusive_group(required=True)
    what.add_argument('finding', nargs='?', type=_finding_id, help='a finding ID, such as HLP-56')
    what.add_argument('--last-used', action='store_true', help='print a **Last used** line from git history')
    args = parser.parse_args()
    try:
        root = _repo_root()
        if not args.last_used:
            _print(lookup(root, args.finding))
            return 0
        line = last_used(root)
    except CannotAnswer as e:
        print(e, file=sys.stderr)
        return 1
    if line:
        _print(line)
        print('A prefix this leaves out stays at 0.', file=sys.stderr)
    else:
        print('No numbers in the history of %s: every counter can stay at 0.' % REVIEW, file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
