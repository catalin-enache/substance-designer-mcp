"""The live self-test as a pool, the default on macOS: every category in a Designer of its own, started for it and
closed after it, `--workers N` of them at once (AT_ONCE by default), the next starting as soon as any ends, rather
than in batches waiting for their slowest. Each is a worker, `python tests/test_all_tools --worker <category>`, a
process of its own (the check record and common.PORT are module globals) with a bridge port, an MCP server, a Designer
and folders of its own; this parent shows each worker's lines and merges their results into one summary. A run is the
same with 1 worker (one after the other) or 4: no category sees what another did. Both suites took about 12 minutes
one after the other before the pool, which came on 2026-11-11. With it, they took about 8.7 minutes with 4 side by
side (2026-11-23, two full runs: 527 s, 521 s), before ROADMAP item 131 put the 3D view back after each shot; not
measured since. editor_panels_and_fit, facts and undo set that time: the first two never run at once, and undo runs
alone at the end (editor_panels_and_fit took about 6 minutes in a scratch run alone, 2026-11-26). A Designer took
about 1.9 GB after a run, about 11 GB after a heavy compute (2026-11-05); the peak of four at once wasn't measured
(ROADMAP item 66).

- **lifecycle starts first** (the longest category after editor_panels_and_fit, which starts next), and holds
  launch_lock's lock over its two windows: while it does, no other worker's Designer starts or quits.
  editor_panels_and_fit holds it too while its window checks read; lifecycle's own launches and quits within its checks
  go on then (REVIEW.md TST-467).
- **The clipboard:** facts and editor_panels_and_fit never run at once (categories.CLIPBOARD).
- **undo** runs last, alone (categories.SOLO): beside the others its Undo failed (the reason there).
- **The run's start checks** (get_guide, the Home screen) run once, in the first category to start after lifecycle
  (`--first`).
- **Crash dumps:** one wait at the end, after the last Designer quit, not 10 s after each quit; a dump in a category's
  Designer's folder fails that category's quit check, `closes <category>'s Designer, which left no crash dump`.
- **The unit suite** (`pytest`, no test ids) runs beside the pool, its result one check, `unit tests`; `--no-unit`
  leaves it out.
- **A quit forced during its shutdown** (its close taken: quit_designer says so) passes its own check; more than two in
  a run, lifecycle's normal closes that reach `common.normal_close` counted too, fail a check of their own. A category's
  Designer's folder is kept after its quit was forced or named a sample of its threads (one that ended while sampled),
  lifecycle's after one of its normal closes forced during its shutdown that its check reached, to read its log and
  sample (DECISIONS.md, Bridge and quitting; ROADMAP item 70). A category whose quit check failed keeps its Designer's
  folder too, its worker passed or not: the Designer gone before the quit, say, whose log may tell why (REVIEW.md
  TST-659).
- **A failed worker keeps its evidence** (its exit code not 0): its scratch folder, with the shots its checks saved,
  which the worker leaves (`__main__.one_run`), and its Designer's folder, with its log. The output names both, or
  says none was made. When a worker or the unit suite failed, the run's folder is kept, holding only their folders. A
  run failed only by the checks this parent makes (the quits, the preferences, the coverage) removes it. While a
  Designer of the run may still run, the whole run's folder is kept, and its ports are named. A passing worker's
  folders are removed.
- **When each worker ran:** the line before its output says when it started and ended, in seconds from the run's start.
- **No folder shared** between workers (worker_env): with the system's temp folder shared, two of five runs lost a
  Designer (ROADMAP item 59).
- **No unit test starts a real run:** `spawn` and the index's run refuse under pytest unless the test faked them (a
  unit test twice reached the real entry point and started Designers, the unit suite inside that run the test again).

The workers count as started by the test, decided here once: a worker asking for itself could take another's Designer,
just started and not yet recorded, for the user's. With a Designer running that no agent started (the user's) the run
asks for it to be closed and starts nothing (all share the preferences plist, which quit_designer puts back once none
runs: check_the_preferences). Off macOS, where launch_designer starts one per port only there, it is one run in one
Designer (`__main__.py`'s docstring)."""

import contextlib
import glob
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
from typing import IO, Protocol, TypedDict, Unpack, cast

import designer_preferences
from test_all_tools import common
from test_all_tools.categories import CATEGORIES, CLIPBOARD, SOLO, category_name
from test_all_tools.common import (
    QUIT_FORCED_IN_SHUTDOWN,
    QUIT_SAMPLED,
    SCRATCH_PREFIX,
    NoListing,
    agent_folder,
    agents_designers,
    closed_by_quit,
    crash_dumps,
    designer_pids,
    dumps_may_come,
    new_dumps,
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
CRASH_WAIT_S = 10  # s at most for a crash dump after the last quit: a limit (wait_for_dumps)
POLL_S = 0.1
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
    env = dict(os.environ)
    env['SD_BRIDGE_PORT'] = str(port)
    env['SD_SNAPSHOT_DIR'] = os.path.join(os.path.realpath(folder), 'snapshots')
    env['TMPDIR'] = temp_folder(folder)
    os.makedirs(env['TMPDIR'], exist_ok=True)
    if gate is not None:
        env.update(gate.env())
    return env


def temp_folder(folder: str) -> str:
    """The temp folder (TMPDIR) a worker or the unit suite gets in its folder, by its real path (worker_env)."""
    return os.path.join(os.path.realpath(folder), 'tmp')


class _Start(TypedDict, total=False):
    """The keywords spawn passes on to subprocess.Popen: those its callers give."""

    cwd: str
    env: dict[str, str]
    stdout: IO[bytes]
    stderr: int  # subprocess.STDOUT


def spawn(command: list[str], **kwargs: Unpack[_Start]) -> 'subprocess.Popen[bytes]':
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
    env['TMPDIR'] = temp_folder(folder)
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


class WorkerEnd(TypedDict):
    """How a worker's Designer ended, the part of its results __main__.py's _ended() gives."""

    quit: str | None  # what its quit_designer said
    quit_at: float | None  # when it quit (time.time())
    forced_in_shutdown: list[str]  # its normal closes forced during their shutdown


class WorkerResults(WorkerEnd):
    """What a worker writes for the pool (__main__.py's results file), as JSON gives it back (REVIEW.md TST-443)."""

    tools: list[str]
    results: dict[str, list[bool]]
    skipped: list[list[str]]  # [tool, check] pairs
    times: dict[str, float]


def merge(
    parts: Mapping[str, WorkerResults | None],
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


def _quit_to_keep(part: WorkerResults) -> bool:
    """Whether a worker's Designer had its quit forced, or sampled as it ended by itself: its folder is kept then
    (REVIEW.md SRV-115)."""
    said = part.get('quit') or ''
    return 'forced' in said or QUIT_SAMPLED in said or bool(part.get('forced_in_shutdown'))


def _read(path: str) -> WorkerResults | None:
    try:
        with open(path, encoding='utf-8') as f:
            return cast(WorkerResults, json.load(f))  # written by the worker itself (__main__.py)
    except (OSError, ValueError):
        return None


def _holds_a_crash_dump(folder: str) -> bool:
    return any(
        files
        and os.path.basename(here) in ('completed', 'pending')  # waiting for its upload too (REVIEW.md TST-351)
        and os.path.basename(os.path.dirname(here)) == 'Sentry-Crashpad'
        for here, _, files in os.walk(folder)
    )


def wait_for_dumps(ports: Sequence[int], before: set[str], until: float) -> None:
    """Waits while a crash dump may still come from the Designers on `ports` (common.dumps_may_come: a crash handler
    still running with no dump new since `before`), looked at every POLL_S, until `until` (time.time()) at most
    (REVIEW.md SRV-151: 10 s after the last quit, whatever happened)."""
    while time.time() < until and dumps_may_come(ports, before, run_port=False):
        sleep(POLL_S)


def check_the_quits(
    parts: Mapping[str, WorkerResults | None], port_of: Mapping[str, int], before: set[str]
) -> set[str]:
    """After one wait from the last quit (wait_for_dumps): each category's quit check, failed by a quit forced before its close took or
    whose log couldn't be read (common.closed_by_quit), none, or a crash dump in its Designer's folder; more than two
    quits forced during their shutdown, the categories' and those of lifecycle's normal closes (its `forced_in_shutdown`),
    fail a check of their own, as does a new dump elsewhere (the shared folder). Returns the categories whose quit check
    failed: their Designers' folders are kept (REVIEW.md TST-659)."""
    failed: set[str] = set()
    quits = [at for part in parts.values() if part and (at := part.get('quit_at'))]
    if quits:
        wait_for_dumps(sorted(port_of.values()), before, max(quits) + CRASH_WAIT_S)
    new = new_dumps(crash_dumps(sorted(port_of.values()), run_port=False), before)
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
                failed.add(name)
            continue
        t = part.get('quit') or 'no quit'
        if 'forced' in t or QUIT_SAMPLED in t:  # whole: a check's detail is cut, the log's line and sample with it
            print("      %s's quit whole: %s" % (name, t))
        closed = closed_by_quit(t) and not dumps
        common.check(
            'quit_designer',
            "closes %s's Designer, which left no crash dump" % name,
            closed,
            '%s; new crash dumps: %s' % (t, dumps),
        )
        if not closed:
            failed.add(name)
    # each passes its own check (DECISIONS.md, Bridge and quitting); more than the two seen at once (ROADMAP item 69) is
    # a pattern, such as a task every Designer leaves in Qt's thread pool, which the user's own Designer would hang on too
    in_shutdown = sorted(n for n, part in parts.items() if part and QUIT_FORCED_IN_SHUTDOWN in (part.get('quit') or ''))
    in_shutdown += [
        '%s: %s' % (n, what) for n, part in parts.items() if part for what in part.get('forced_in_shutdown', [])
    ]
    common.check(
        'quit_designer',
        'no more than two quits forced during their shutdown',
        len(in_shutdown) <= 2,
        'quits forced during their shutdown: %s' % (', '.join(in_shutdown) or 'none'),
    )
    if new - placed:
        common.check('self-test', 'no new crash dump outside the run', False, str(sorted(new - placed)))
    return failed


PREFERENCES = "Designer's preferences are as before the run, once its Designers ended"
# when they were read, and the file's keys or why they couldn't be read
Preferences = tuple[float, dict[str, designer_preferences.Plist] | str]


def preferences_before() -> Preferences | None:
    """Designer's preferences plist as the run should leave it (macOS: None elsewhere), for check_the_preferences. A
    copy left by agents' Designers that ended outside the tools is put back, or dropped, first, as the run's first
    launch would. A copy still kept (a Designer outside the run runs, an `alone.run` one for instance) is what the
    run's last quit puts back, so it is what the file should be (REVIEW.md TST-357); unless the user's Designer ran
    since it was made: the run's first launch makes it again then, from the file (kept_copy(), REVIEW.md TST-367)."""
    if sys.platform != 'darwin':
        return None
    said = designer_preferences.put_back(_any_designer, ended=False)
    if said:
        print(said)
    at = time.time()
    try:
        kept = designer_preferences.kept_copy()
    except (designer_preferences.PreferencesError, OSError) as e:  # as the file can't be told then
        return at, "the copy kept couldn't be read (%s)" % e
    if kept is not None:
        return at, kept
    try:
        return at, designer_preferences.current()
    except designer_preferences.PreferencesError as e:
        return at, str(e)


def _any_designer() -> bool:
    """Whether a Designer runs; True when that can't be told."""
    try:
        return bool(designer_pids())
    except NoListing:
        return True


def check_the_preferences(before: Preferences | None, ports: Collection[int]) -> None:
    """Designer's preferences plist, which every Designer shares, as `before` the run once its Designers have ended:
    launch_designer saved it and quit_designer put it back once none ran (designer_preferences.py, ROADMAP item 67).
    Skipped when the user's Designer ran during the run (what the file holds may be theirs then: it is left) or a
    Designer outside the run still runs (the put-back waits for its end); failed while one of the run's still runs,
    when that can't be told, or when the file, or the copy kept, couldn't be read as the run started."""
    if before is None:
        return
    at, saved = before
    if designer_preferences.users_log_time() > at:
        common.skip('self-test', PREFERENCES, "the user's Designer ran during the run: the file is left as theirs")
        return
    try:
        left = sorted(set(ports) & set(agents_designers()))
        running = designer_pids()
        now = designer_preferences.current()
    except Exception as e:  # a listing or a read failing: can't tell (as _clean_up)
        common.check('self-test', PREFERENCES, False, "can't be told: %s" % e)
        return
    if left:
        common.check('self-test', PREFERENCES, False, "the run's Designers still run, on ports %s" % left)
        return
    if running:
        why = 'a Designer outside the run runs (%s): the put-back waits for its end' % ', '.join(map(str, running))
        common.skip('self-test', PREFERENCES, why)
        return
    if isinstance(saved, str):
        common.check('self-test', PREFERENCES, False, "they couldn't be read as the run started: %s" % saved)
        return
    added = sorted(set(now) - set(saved))
    changed = sorted(key for key in saved if key not in now or now[key] != saved[key])
    # the counts first: a check's detail is cut at 150 characters; every key whole on lines of their own (TST-361)
    if changed:
        print('      values changed: %s' % ', '.join(changed))
    if added:
        print('      keys added: %s' % ', '.join(added))
    names = '; '.join(
        '%s: %s' % (how, ', '.join(keys)) for how, keys in (('changed', changed), ('added', added)) if keys
    )
    common.check(
        'self-test',
        PREFERENCES,
        not added and not changed,
        '%s, %s%s'
        % (_count(changed, 'value', 'changed'), _count(added, 'key', 'added'), ' (%s)' % names if names else ''),
    )


def _count(keys: list[str], what: str, how: str) -> str:
    return '%d %s%s %s' % (len(keys), what, '' if len(keys) == 1 else 's', how)


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
    preferences = preferences_before()
    began: dict[str, float] = {}
    ended: dict[str, float] = {}
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
        on_end=lambda name: ended.update({name: time.monotonic()}),
    )
    unit_code = unit_proc.wait() if unit_proc else None
    wall = time.monotonic() - started
    parts: dict[str, WorkerResults | None] = {}
    for name in order:
        # when it ran, so who ran beside whom is read from these lines
        print(
            '\n===== worker %s (exit code %d, %.0f s, from %.0f s to %.0f s of the run) ====='
            % (name, codes[name], ended[name] - began[name], began[name] - started, ended[name] - started)
        )
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
    quit_failed = check_the_quits(parts, port_of, before)
    check_the_preferences(preferences, chosen)
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
    # a failed worker's evidence: the shots in its scratch folder, which it leaves (__main__.one_run), and its
    # Designer's log in its Designer's folder
    failed = [name for name in order if codes[name] != 0]
    for name in failed:
        scratch = sorted(glob.glob(os.path.join(temp_folder(folder_of[name]), SCRATCH_PREFIX + '*')))
        print('kept, %s failed, its scratch folder: %s' % (name, ', '.join(scratch) or 'none'))
    keep: dict[int, str] = {}  # each port's reasons, both when a failed worker's quit was forced too
    for name in order:
        part = parts[name]
        # each reason names the category: the folder's name holds only its port (REVIEW.md TST-670)
        why = (["%s failed, its Designer's folder" % name] if name in failed else []) + (
            ["%s's quit was forced or sampled" % name] if part and _quit_to_keep(part) else []
        )
        why += ["%s's quit check failed" % name] if name in quit_failed else []
        if why:
            keep[port_of[name]] = '; '.join(why)
    evidence = [folder_of[name] for name in failed] + ([unit_folder] if unit_code else [])
    _clean_up(root, chosen, keep, evidence, {port: name for name, port in port_of.items()})
    return 0 if ok else 1


def _clean_up(
    root: str, chosen: list[int], keep: Mapping[int, str], evidence: Sequence[str], owners: Mapping[int, str]
) -> None:
    """The folders launch_designer made for the workers' Designers (about 90 MB each), unless one still runs there, left
    a crash dump or is in `keep`, to read; then the run's folder, once none of its Designers is left: all of it, or all
    but the folders in `evidence`. run_pool's `keep`: the ports whose quit was forced or sampled, their log saying how
    far that quit got, those whose quit check failed, and those of the failed workers, each with why it is kept, the
    category named. Its `evidence`: the failed workers' folders, which hold their scratch folders, and the unit suite's
    when it failed. `owners`: each port's category, named on each line of a folder kept: a folder's name holds only its
    port (REVIEW.md TST-670)."""
    try:
        left = set(chosen) & set(agents_designers())
    except Exception as e:  # can't tell: everything kept
        left = set(chosen)
        print("the workers' Designers can't be listed (%s)" % e)
    for port in sorted(set(chosen) - left):
        folder = agent_folder(port)
        if _holds_a_crash_dump(folder):
            print("kept, %s's folder holds a crash dump: %s" % (owners[port], folder))
        elif port in keep:  # a worker that failed before its launch made none
            print('kept, %s: %s' % (keep[port], folder if os.path.isdir(folder) else 'none'))
        else:
            shutil.rmtree(folder, ignore_errors=True)
    if left:
        running = ', '.join("%s's (port %d)" % (owners[port], port) for port in sorted(left))
        print('folders kept, a Designer of the run may still be open: %s; %s' % (root, running))
    elif evidence:
        for entry in os.listdir(root):
            path = os.path.join(root, entry)
            if path in evidence:
                continue
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:  # the launch lock's file, which a worker killed holding the lock leaves
                with contextlib.suppress(OSError):
                    os.remove(path)
        names = ', '.join(os.path.basename(folder) for folder in evidence)
        print("the run's folder kept, with only the folders of what failed: %s (%s)" % (root, names))
    else:
        shutil.rmtree(root, ignore_errors=True)
