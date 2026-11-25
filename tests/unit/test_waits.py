"""Code waits for the callback that says a thing happened, polls every 100 ms only where none exists, and never waits a
time measured here (`.claude/rules/waits.md`; REVIEW.md SRV-150, TST-421). Read in the tools, the plugin, the
helpers, the client, the examples and the self-test, their snippets of Designer code included: every sleep, every
_settle, every `.start(...)` given a time and every single-shot timer after a number, written on one line, is a poll of
POLL_S or TICK, or one of the waits listed here, each with the reason it stays (REVIEW.md TST-426: a timer started at a
variable went unseen). A call split over lines isn't read, nor `Event.wait(...)`: the self-test's front watch samples
every FRONT_EVERY through one (window_server.py; REVIEW.md TST-456). A call spelled until( or _until( whose line reads
mac.hidden or mac.minimized is given AppKit's notifications by name too (ROADMAP item 101)."""

import os
import re
from collections import Counter
from collections.abc import Iterator

from conftest import ROOT
from project_constants import PLUGIN

FOLDERS = ('mcp_server', 'plugin', 'client', 'examples', os.path.join('tests', 'test_all_tools'))
FILES = ('designer_preferences.py',)
PLUGIN_FILE = 'plugin/%s/%s/__init__.py' % (PLUGIN, PLUGIN)
# a sleep or a _settle, anything started with an argument (a timer's time), a single-shot timer after a number
WAIT = re.compile(
    r'\b(?:(?:time|asyncio|self)\.)?(?:sleep|_settle)\(\s*[^)\n]*\)'
    r'|\b(?!(?:m|call|match|found)\b)\w+(?:\[-?\d+\])?\.start\(\s*(?!0\s*\))[^)\s][^)\n]*\)'
    r'|\bsingleShot\(\s*[1-9]\d*'
)
POLLS = {  # waits of a poll's interval: looking at a state no callback says
    'time.sleep(POLL_S)',
    'time.sleep(common.POLL_S)',
    'asyncio.sleep(POLL_S)',
    'sleep(POLL_S)',
    '_settle(0.1)',
    '_settle(TICK / 1000.0)',
    'tick.start(TICK)',
    'self.sleep(poll_s)',
}
STAYS: dict[tuple[str, str], tuple[int, str]] = {
    # (file, the wait): (how many there, why it stays)
    ('mcp_server/designer_helpers/waits.py', 'time.sleep(0.02)'): (
        1,
        "_settle itself, running Designer's events every 20 ms while a poll waits its interval",
    ),
    (PLUGIN_FILE, 'timer.start(100)'): (
        1,
        'the job queue polled every 100 ms, where no wake comes',
    ),
    (PLUGIN_FILE, 'delay.start(ms)'): (
        1,
        'WAKE_DELAY_MS between two jobs: DECISIONS.md, "No job starts sooner than 30 ms after the one before ended"; '
        "the wait rule's named exception (`.claude/rules/waits.md`; the user, 2026-11-20)",
    ),
    ('mcp_server/designer_helpers/waits.py', 'end.start(int(limit * 1000)'): (1, "the wait's limit, a safety net"),
    ('mcp_server/designer_rollback.py', 'limit.start(int(limit_s * 1000)'): (1, "the undo's limit, a safety net"),
    ('tests/test_all_tools/batch/designer_scripts/history_facts.py', 'limit.start(60000)'): (
        1,
        "the undo's limit, a safety net, as the rollback's",
    ),
    ('mcp_server/designer_helpers/view3d.py', 'timers[-1].start(after)'): (
        1,
        "the menu's look at once, and its guard's limit (MENU_GUARD), a safety net",
    ),
    (PLUGIN_FILE, 'time.sleep(delay)'): (
        1,
        "the accept loop's back-off after an error, not a wait for something to happen",
    ),
    ('mcp_server/designer_helpers/quit.py', 'singleShot(300'): (
        1,
        "an older plugin's close, one without _after_reply, until Designer restarts (REVIEW.md SRV-151); the wait "
        "rule's named exception (`.claude/rules/waits.md`; the user, 2026-11-20)",
    ),
    # the check's subject: a job holding the bridge, the main thread or the thread pool, a slow shutdown, a timer's
    # firings counted
    ('tests/test_all_tools/batch/checks.py', 'sleep(1)'): (1, 'code outlasting its timeout_s of 1 in one C call'),
    ('tests/test_all_tools/bridge/checks.py', 'time.sleep(0.05)'): (2, 'a job holding the bridge'),
    ('tests/test_all_tools/bridge/checks.py', 'time.sleep(0.01)'): (1, 'a job holding the bridge'),
    ('tests/test_all_tools/bridge/checks.py', 'time.sleep(0.3)'): (1, 'a long job, another queued behind it'),
    ('tests/test_all_tools/lifecycle/checks.py', 'time.sleep(0.1)'): (2, 'a job holding the bridge; a frozen thread'),
    ('tests/test_all_tools/lifecycle/designer_scripts/hold_thread_pool.py', 'time.sleep(0.5)'): (
        1,
        'a task holding the thread pool',
    ),
    ('tests/test_all_tools/lifecycle/designer_scripts/quit_slow_shutdown.py', 'time.sleep(0.05)'): (
        1,
        'a slow shutdown',
    ),
    ('tests/test_all_tools/editor_panels_and_fit/checks.py', 'timers[0].start(20)'): (1, "a timer's firings counted"),
    ('tests/test_all_tools/editor_panels_and_fit/checks.py', '_settle(0.2)'): (1, "a timer's firings counted"),
    ('tests/test_all_tools/editor_panels_and_fit/checks.py', '_settle(0.3)'): (1, "a timer's firings counted"),
    ('tests/test_all_tools/editor_panels_and_fit/window_states.py', 'tick.start(100)'): (1, "until()'s poll"),
    # the click and window-under facts time macOS's covered state on purpose (REVIEW.md TST-412)
    ('tests/test_all_tools/editor_panels_and_fit/window_states.py', '_settle(0.5)'): (
        2,
        "the click fact; the wait rule's named exception (`.claude/rules/waits.md`; the user, 2026-11-20)",
    ),
    ('tests/test_all_tools/editor_panels_and_fit/window_states.py', '_settle(1.0)'): (
        3,
        "the window-under fact; the wait rule's named exception (`.claude/rules/waits.md`; the user, 2026-11-20)",
    ),
}


def _code_lines() -> Iterator[tuple[str, str]]:
    """(file, its code) for each line of code read here, but a comment's or a def's: the file relative to the root."""
    paths = [os.path.join(ROOT, f) for f in FILES]
    for folder in FOLDERS:
        for top, dirs, files in os.walk(os.path.join(ROOT, folder)):
            dirs[:] = [d for d in dirs if d not in ('venv', '__pycache__')]
            paths += [os.path.join(top, f) for f in files if f.endswith('.py')]
    for path in paths:
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.lstrip().startswith('#') or re.match(r'\s*def ', line):
                    continue
                yield os.path.relpath(path, ROOT).replace(os.sep, '/'), line.split('  #')[0]  # a comment after it


def _waits() -> Counter[tuple[str, str]]:
    found: Counter[tuple[str, str]] = Counter()
    for path, code in _code_lines():
        for wait in WAIT.findall(code):
            found[(path, wait)] += 1
    return found


def test_nothing_waits_a_fixed_time_but_the_waits_that_stay() -> None:
    found = _waits()
    fixed = {key: n for key, n in found.items() if key[1] not in POLLS}
    assert {key: n for key, n in fixed.items() if STAYS.get(key, (0, ''))[0] != n} == {}
    assert [key for key in STAYS if key not in fixed] == [], 'listed, no longer there'


# a wait the guard reads: a call spelled until( or _until( whose line reads macOS's hidden or minimized flag through a
# variable named mac (mac.hidden, mac.minimized). The helpers' waits on AppKit's notifications (_until_notified,
# _wait_unhidden, _wait_unlisted) don't match it
MACOS_FLAG = re.compile(r'\b_?until\(.*\bmac\.(?:hidden|minimized)\b')
# given AppKit's notifications by name: window_states.py's until(), names= one of mac_window.py's tuples
NOTIFIED = re.compile(r'\bnames=(?:UNHIDDEN|HIDDEN|OFF_SCREEN|UNMINIMIZED)\b')


def test_a_wait_on_macoss_hidden_or_minimized_flag_wakes_on_appkits_notifications() -> None:
    # ROADMAP item 101: Qt sends no event as macOS hides, shows or minimizes Designer (REVIEW.md HLP-173), so a wait
    # woken by Qt's events and a poll alone sees the flag change up to 100 ms late. Read on the wait's line only: a
    # state read through a function of its own (window_states.py's shown_again) isn't seen here
    found = [(path, code.strip()) for path, code in _code_lines() if MACOS_FLAG.search(code)]
    assert found, 'no wait on the flags found: the pattern no longer matches the code'
    assert [wait for wait in found if not NOTIFIED.search(wait[1])] == []


def test_the_polls_look_every_100_ms() -> None:
    # `.claude/rules/waits.md`: a state no callback says is looked at every 100 ms; the helpers' TICK isn't read here
    from selftest_fakes import fresh

    from conftest import server

    assert server.POLL_S == 0.1
    for name in ('common', 'launch_lock', 'workers'):
        assert fresh(name).POLL_S == 0.1, name
