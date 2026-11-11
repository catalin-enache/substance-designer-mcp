"""The live self-test as a pool, the default on macOS: every category in a Designer of its own, started for it and
closed after it, `--workers N` of them at once (AT_ONCE by default), the next starting as soon as any ends, rather
than in batches waiting for their slowest (simulated with 4: 2.8 to 3.7 min against 5.9 to 6.5). Each is a worker,
`python tests/test_all_tools --worker <category>`, a process of its own (the check record and common.PORT are module
globals) with a bridge port, an MCP server, a Designer and folders of its own; this parent shows each worker's lines
and merges their results into one summary. A run is the same with 1 worker (one after the other) or 4: no category
sees what another did. Both suites took about 12 minutes one after the other before the pool; with it (2026-11-10)
3.4 minutes with 4 at once, 5.6 with 2, 10.5 with 1, lifecycle (about 3 minutes) and then undo alone setting the time
with 4. A Designer took about 1.9 GB after a run, about 11 GB after a heavy compute (2026-11-05); the peak of four at
once wasn't measured (ROADMAP item 66).

- **lifecycle starts first** (the longest), and holds launch_lock's lock over its two windows: while it does, no
  Designer of the run starts or quits.
- **The clipboard:** facts and editor_panels_and_fit never run at once (categories.CLIPBOARD).
- **undo** runs last, alone (categories.SOLO): beside the others its Undo failed (the reason there).
- **The run's start checks** (get_guide, the Home screen) run once, in the first category to start after lifecycle
  (`--first`).
- **Crash dumps:** one wait at the end, after the last Designer quit, not 10 s after each quit; a dump in a category's
  Designer's folder fails that category's quit check, `closes <category>'s Designer, which left no crash dump`.
- **The unit suite** (`pytest`, no test ids) runs beside the pool, its result one check, `unit tests`; `--no-unit`
  leaves it out.
- **No folder shared** between workers (worker_env): with the system's temp folder shared, two of five runs lost a
  Designer (ROADMAP item 59).
- **No unit test starts a real run:** `spawn` and the index's run refuse under pytest unless the test faked them (a
  unit test twice reached the real entry point and started Designers, the unit suite inside that run the test again).

The workers count as started by the test, decided here once: a worker asking for itself could take another's Designer,
just started and not yet recorded, for the user's. With a Designer running that no agent started (the user's) the run
asks for it to be closed and starts nothing (all share the preferences plist: ROADMAP item 67). Off macOS, where
launch_designer starts one per port only there, it is one run in one Designer (`__main__.py`'s docstring)."""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from typing import Any, Protocol

from test_all_tools import common
from test_all_tools.categories import CATEGORIES, CLIPBOARD, SOLO, category_name
from test_all_tools.common import (
    NoListing,
    agent_folder,
    agents_designers,
    crash_dumps,
    summarize,
    users_designer_running,
)
from test_all_tools.launch_lock import Gate
from test_all_tools.lifecycle.checks import unused_port

LIFECYCLE = 'lifecycle'
AT_ONCE = 4  # categories at once unless --workers says otherwise (ROADMAP item 66: the memory it takes)
INDEX = os.path.dirname(os.path.abspath(__file__))  # `python <this folder>` runs __main__.py
REPO = os.path.dirname(os.path.dirname(INDEX))
UNIT = 'unit tests'
CRASH_WAIT_S = 10  # Designer writes a crash dump a few seconds after it goes down: once, after the last quit
POLL_S = 0.2
sleep = time.sleep


class Process(Protocol):
    def poll(self) -> int | None: ...


class Gating(Protocol):
    def try_begin(self, name: str) -> bool: ...

    def end(self, name: str) -> None: ...

    def worker_ended(self, name: str) -> None: ...


class Refused(Exception):
    """No run: a Designer runs that no agent started (or that can't be told)."""


def names() -> list[str]:
    """The workers, in the pool's order: lifecycle, then the categories slowest first (`SOLO`'s start last)."""
    return [LIFECYCLE, *(category_name(step) for step in CATEGORIES)]


def choose(asked: int | None) -> int:
    """How many at once: `asked`, AT_ONCE by default; 0 for one run, off macOS. Refused with a Designer running that no
    agent started, or when that can't be told."""
    if sys.platform != 'darwin':
        print('one run: several Designers side by side are for macOS only')
        return 0
    try:
        users = users_designer_running()
    except NoListing as e:
        raise Refused('nothing run: %s, so a Designer of yours may be open: close it, then run again' % e) from e
    if users:
        raise Refused(
            'nothing run: a Designer is open that no agent started (yours?): save your work and close it, then run '
            'the self-test again; it starts Designers of its own and never touches yours'
        )
    return asked or AT_ONCE


def ports(count: int, take: Callable[[], int] = unused_port) -> list[int]:
    """`count` distinct ports no Designer an agent started is recorded on (unused_port); RuntimeError if they can't
    be found."""
    chosen: list[int] = []
    for _ in range(count * 10):
        port = take()
        if port and port not in chosen:
            chosen.append(port)
        if len(chosen) == count:
            return chosen
    raise RuntimeError('no %d free ports found for the workers' % count)


def worker_env(port: int, folder: str, gate: Gate | None = None) -> dict[str, str]:
    """A worker's environment: this one's, with its port, the pool's lock (launch_lock), and no folder shared with
    another worker: its snapshots and its temp folder (TMPDIR: its scratch folder, its server's temporary files) in its
    own folder, by their real path (under a symlink, the paths Designer writes in a snapshot come out one `..` short:
    ROADMAP item 57). Its Designer's temp folder and home are its own already (launch_designer)."""
    real = os.path.realpath(folder)
    env = dict(os.environ)
    env['SD_BRIDGE_PORT'] = str(port)
    env['SD_SNAPSHOT_DIR'] = os.path.join(real, 'snapshots')
    env['TMPDIR'] = os.path.join(real, 'tmp')
    os.makedirs(env['TMPDIR'], exist_ok=True)
    if gate is not None:
        env.update(gate.env())
    return env


def spawn(command: list[str], **kwargs: Any) -> 'subprocess.Popen[bytes]':
    """The pool's one way to start a process (a worker, the unit suite). Refused under pytest unless the test replaced
    Popen: a unit test reaching it would start Designers, and the unit suite inside that run the same test again."""
    if os.environ.get('PYTEST_CURRENT_TEST') and getattr(subprocess.Popen, '__module__', '') == 'subprocess':
        raise RuntimeError('a unit test reached a real start of the self-test (%s): fake it' % command[-1])
    return subprocess.Popen(command, **kwargs)


def results_path(folder: str, name: str) -> str:
    return os.path.join(folder, name + '.json')


def start_unit(folder: str) -> 'subprocess.Popen[bytes]':
    """The whole unit suite from the repository, its lines going to <folder>/unit.log, with a temp folder of its own
    (its tests' tmp_path): no folder shared with a worker."""
    env = dict(os.environ)
    env['TMPDIR'] = os.path.join(os.path.realpath(folder), 'tmp')
    os.makedirs(env['TMPDIR'], exist_ok=True)
    with open(os.path.join(folder, 'unit.log'), 'wb') as log:
        return spawn([sys.executable, '-m', 'pytest', '-q'], cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)


def answering(port: int) -> bool:
    """Whether something listens on the port: the plugin of the worker's Designer, once it has started."""
    try:
        socket.create_connection(('127.0.0.1', port), timeout=1).close()
        return True
    except OSError:
        return False


def schedule(
    names: Sequence[str],
    slots: int,
    start: Callable[[str], Process],
    answering: Callable[[str], bool],
    gate: Gating,
    exclusive: Collection[str],
    solo: Collection[str] = (),
    sleep: Callable[[float], None] = time.sleep,
    on_end: Callable[[str], None] = lambda name: None,
) -> dict[str, int]:
    """Run every name, `slots` at most at once, in their order, the next as soon as any ends; one of `exclusive` only
    while no other of them runs; one of `solo` last, alone, once every other has ended; none while the gate refuses
    (lifecycle's lock), each start marked until its Designer answers or its worker ends; on_end(name) as each one ends.
    {name: exit code}."""
    pending = list(names)
    running: dict[str, Process] = {}
    starting: set[str] = set()
    codes: dict[str, int] = {}
    while pending or running:
        for name, proc in list(running.items()):
            code = proc.poll()
            if name in starting and (code is not None or answering(name)):
                gate.end(name)
                starting.discard(name)
            if code is not None:
                gate.worker_ended(name)  # its marks, and the lock if it held it, whatever ended it
                codes[name] = code
                del running[name]
                on_end(name)
        while len(running) < slots and not set(running) & set(solo):
            busy = set(running) & set(exclusive)
            others_left = bool(running) or any(n not in solo for n in pending)
            ready = next(
                (n for n in pending if not (n in exclusive and busy) and not (n in solo and others_left)), None
            )
            if ready is None or not gate.try_begin(ready):
                break
            pending.remove(ready)
            running[ready] = start(ready)
            starting.add(ready)
        if pending or running:
            sleep(POLL_S)
    return codes


def merge(
    parts: Mapping[str, dict[str, Any] | None],
) -> tuple[list[str], dict[str, list[bool]], list[tuple[str, str]], dict[str, float]]:
    """The workers' results as one run's: (tools, results, skipped, times); a worker with no results is a failed
    check."""
    tools: set[str] = set()
    results: dict[str, list[bool]] = {}
    skipped: list[tuple[str, str]] = []
    times: dict[str, float] = {}
    for name, part in parts.items():
        if part is None:
            results.setdefault('self-test', []).append(False)
            print('FAIL  %-22s worker %s reports its results | none written' % ('self-test', name))
            continue
        tools |= set(part['tools'])
        for tool, oks in part['results'].items():
            results.setdefault(tool, []).extend(oks)
        skipped += [(tool, check) for tool, check in part['skipped']]
        times.update(part['times'])
    return sorted(tools), results, skipped, times


def _read(path: str) -> dict[str, Any] | None:
    try:
        with open(path, encoding='utf-8') as f:
            found: dict[str, Any] = json.load(f)
        return found
    except (OSError, ValueError):
        return None


def _holds_a_crash_dump(folder: str) -> bool:
    return any(
        files and os.path.basename(here) == 'completed' and os.path.basename(os.path.dirname(here)) == 'Sentry-Crashpad'
        for here, _, files in os.walk(folder)
    )


def check_the_quits(parts: Mapping[str, dict[str, Any] | None], port_of: Mapping[str, int], before: set[str]) -> None:
    """After one wait from the last quit: each category's quit check, failed by a forced quit, none, or a
    crash dump in its Designer's folder; a new dump elsewhere (the shared folder) fails a check of its own."""
    quits = [part['quit_at'] for part in parts.values() if part and part.get('quit_at')]
    if quits:
        sleep(max(0.0, max(quits) + CRASH_WAIT_S - time.time()))
    new = crash_dumps(sorted(port_of.values()), run_port=False) - before
    placed: set[str] = set()
    for name, part in parts.items():
        # every worker's dumps are its own, lifecycle's included, never "outside the run" (REVIEW.md TST-236)
        folder = agent_folder(port_of[name]) + os.sep
        dumps = sorted(d for d in new if d.startswith(folder))
        placed |= set(dumps)
        if name == LIFECYCLE:  # it checks its own quits, with a watch of its own
            continue
        if part is None:  # no quit to check: its failure is already one (merge); its dumps, if any, one more
            if dumps:
                common.check('quit_designer', "%s's Designer left no crash dump" % name, False, str(dumps))
            continue
        t = part.get('quit') or 'no quit'
        common.check(
            'quit_designer',
            "closes %s's Designer, which left no crash dump" % name,
            'Designer quit after' in t and 'forced' not in t and not dumps,
            '%s; new crash dumps: %s' % (t, dumps),
        )
    if new - placed:
        common.check('self-test', 'no new crash dump outside the run', False, str(sorted(new - placed)))


def run_pool(slots: int, unit: bool = True, only: Sequence[str] | None = None) -> int:
    """The pool, with the unit suite beside it unless `unit` is False; `only`: those categories alone, in the pool's
    order, the coverage of every tool left to a full run. Its exit code: 0 every check passed and, in a full run, every
    tool was exercised; 1 otherwise."""
    root = os.path.realpath(tempfile.mkdtemp(prefix='sd_mcp_selftest_workers_'))
    order = [name for name in names() if only is None or name in only]
    chosen = ports(len(order))
    port_of = dict(zip(order, chosen, strict=True))
    folder_of = {name: os.path.join(root, name) for name in order}
    for folder in folder_of.values():
        os.makedirs(folder, exist_ok=True)
    gate = Gate(root)
    unit_folder = os.path.join(root, 'unit')
    os.makedirs(unit_folder, exist_ok=True)
    what = '%d at once%s' % (slots, ' and the unit tests' if unit else '')
    print('%d categories, %s; their folders in %s\n' % (len(order), what, root))
    before = crash_dumps(chosen, run_port=False)
    began: dict[str, float] = {}
    took: dict[str, float] = {}
    # the first to start after lifecycle (which runs none of them), not the one SOLO keeps for last unless it is alone
    others = [name for name in order if name != LIFECYCLE]
    first = next((name for name in others if name not in SOLO), others[0] if others else None)

    def start(name: str) -> Process:
        began[name] = time.monotonic()
        folder = folder_of[name]
        with open(os.path.join(folder, name + '.log'), 'wb') as log:
            return spawn(
                [
                    sys.executable,
                    '-u',
                    INDEX,
                    '--worker',
                    name,
                    '--results',
                    results_path(folder, name),
                    *(['--first'] if name == first else []),
                ],
                env=worker_env(port_of[name], folder, gate),
                stdout=log,
                stderr=subprocess.STDOUT,
            )

    started = time.monotonic()
    unit_proc = start_unit(unit_folder) if unit else None
    codes = schedule(
        order,
        slots,
        start=start,
        answering=lambda name: answering(port_of[name]),
        gate=gate,
        exclusive=CLIPBOARD,
        solo=SOLO,
        on_end=lambda name: took.update({name: time.monotonic() - began[name]}),
    )
    unit_code = unit_proc.wait() if unit_proc else None
    wall = time.monotonic() - started
    parts: dict[str, dict[str, Any] | None] = {}
    for name in order:
        print('\n===== worker %s (exit code %d, %.0f s) =====' % (name, codes[name], took.get(name, 0.0)))
        with open(os.path.join(folder_of[name], name + '.log'), encoding='utf-8', errors='replace') as log:
            print(log.read().rstrip())
        parts[name] = _read(results_path(folder_of[name], name))
    unit_lines = ''
    if unit_code is not None:
        print('\n===== %s (exit code %d) =====' % (UNIT, unit_code))
        with open(os.path.join(unit_folder, 'unit.log'), encoding='utf-8', errors='replace') as log:
            unit_lines = log.read().rstrip()
        print(unit_lines)
    print('\n===== all workers =====')
    tools, results, skipped, times = merge(parts)
    for tool, oks in results.items():
        common.results.setdefault(tool, []).extend(oks)
    common.skipped.extend(skipped)
    common.times.update(times)
    check_the_quits(parts, port_of, before)
    if unit_code is not None:
        last = unit_lines.splitlines()[-1] if unit_lines else 'no output'
        common.check(UNIT, 'the whole unit suite passes, beside the workers', unit_code == 0, last)
        unit_s = re.search(r' in ([\d.]+)s', last)
        if unit_s:
            common.times[UNIT] = float(unit_s.group(1))
    if only is not None:  # every worker lists all the server's tools; only those the categories named ran are judged
        tools = sorted(set(tools) & set(common.results))
        print('--only: the coverage of every tool: a full run')
    summary, ok = summarize(tools, common.results, common.skipped, common.times)
    print(summary)
    print('wall time %.0f s, %d categories, %s' % (wall, len(order), what))
    _clean_up(root, chosen)
    return 0 if ok else 1


def _clean_up(root: str, chosen: list[int]) -> None:
    """The folders launch_designer made for the workers' Designers (about 90 MB each), unless one still runs there or
    left a crash dump, to read; then the run's folder, once none of its Designers is left."""
    try:
        left = set(chosen) & set(agents_designers())
    except Exception as e:  # can't tell: everything kept
        left = set(chosen)
        print("the workers' Designers can't be listed (%s)" % e)
    for port in sorted(set(chosen) - left):
        if _holds_a_crash_dump(agent_folder(port)):
            print('kept, it holds a crash dump:', agent_folder(port))
        else:
            shutil.rmtree(agent_folder(port), ignore_errors=True)
    if left:
        print('folders kept, a Designer of the run may still be open:', root, sorted(left))
    else:
        shutil.rmtree(root, ignore_errors=True)
