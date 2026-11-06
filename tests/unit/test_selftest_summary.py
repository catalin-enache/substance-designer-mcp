"""The live self-test's summary (REVIEW.md TST-1): a tool counts as covered only when it had a
check that ran; one whose checks were all skipped is listed, not counted."""

import asyncio
import importlib
import os
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from conftest import SELFTEST_DIR, selftest_sources


def _selftest() -> Any:  # a module imported by name: PyCharm can't see its names
    """The self-test's index (tests/test_all_tools/__main__.py), imported afresh with all its modules,
    so each test starts with an empty check record."""
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    for name in [m for m in sys.modules if m == 'test_all_tools' or m.startswith('test_all_tools.')]:
        del sys.modules[name]
    return importlib.import_module('test_all_tools.__main__')


def test_skipped_only_tools_are_not_counted_as_covered() -> None:
    summary, ok = _selftest().summarize(['a', 'b', 'c'], {'a': [True], 'b': []}, [('b', 'closes Designer')])
    assert '1/3 tools covered' in summary
    assert "only skipped: ['b']" in summary and "NOT covered: ['c']" in summary
    assert not ok  # c has no check at all


def test_skips_alone_do_not_fail_the_run() -> None:
    # quit_designer is always skipped while your own Designer runs; that is reported, not a failure
    summary, ok = _selftest().summarize(['a', 'b'], {'a': [True, True], 'b': []}, [('b', 'x')])
    assert ok and '1/2 tools covered' in summary and "only skipped: ['b']" in summary
    assert 'checks passed: 2/2; skipped: 1; tools with failures: none' in summary


def test_a_failed_check_fails_the_run() -> None:
    summary, ok = _selftest().summarize(['a'], {'a': [True, False]}, [])
    assert not ok and 'tools with failures: a' in summary


def test_cleanup_covers_every_graph_the_self_test_creates() -> None:
    # REVIEW.md TST-9: the size-inheritance check's 'inherit_*' graphs weren't matched by CLEAN,
    # so they stayed open if the check failed midway
    import re

    src = '\n'.join(selftest_sources().values())
    created = [n for n in re.findall(r"setIdentifier\('([^']*)'", src) if n != '%s']  # '%s' is DUP_GRAPH
    assert created and all(name.startswith('mcp_selftest') for name in created), created
    assert ".startswith('mcp_selftest')" in _selftest().CLEAN


def test_a_check_that_is_not_a_bool_is_counted() -> None:
    # REVIEW.md TST-29: check() stored the condition as given; `refs and not missing` with no refs is
    # [], and summarize()'s sum then raised TypeError, so no summary was printed
    selftest = _selftest()  # imported afresh: no checks recorded yet
    selftest.check('tool', 'empty list', [])
    selftest.check('tool', 'none', None)
    text, ok = selftest.summarize(['tool'], selftest.results, [])
    assert not ok and 'checks passed: 0/2' in text


def test_a_bridge_error_in_the_library_clean_up_is_a_failed_check_not_a_crash() -> None:
    # REVIEW.md TST-33: an error answer there raised AttributeError in the self-test's finally,
    # skipping the rest of its clean-up (the snapshots, putting the user's graph back, the quit)
    import asyncio
    from types import SimpleNamespace

    selftest = _selftest()

    async def bridge_error(name: str, args: dict[str, Any] | None = None) -> SimpleNamespace:
        return SimpleNamespace(content=[SimpleNamespace(type='text', text='Error executing tool: bridge busy')])

    asyncio.run(selftest.restore_library_packages(bridge_error, []))
    assert selftest.results['self-test'] == [False]


@pytest.mark.parametrize('designer_running', [True, False])
def test_the_scratch_folder_is_only_deleted_once_designer_is_closed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, designer_running: bool
) -> None:
    # REVIEW.md PLG-18 (and PLG-9): deleting it while Designer ran crashed Designer twice, in its file
    # watcher; with a Designer still running it is left in the OS temp folder, and the path printed
    selftest = _selftest()
    scratch = tmp_path / 'sd_mcp_selftest_x'
    scratch.mkdir()
    (scratch / 'graph.sbs').write_text('x')
    monkeypatch.setattr(tempfile, 'mkdtemp', lambda prefix: str(scratch))

    async def run(scratch: str) -> list[str]:
        selftest.STATE['was_running'] = designer_running
        return []

    monkeypatch.setitem(vars(selftest), 'run', run)
    monkeypatch.setitem(vars(selftest), 'designer_alive', lambda: designer_running)
    monkeypatch.setitem(vars(selftest), 'new_crash_dumps', lambda before, wait_s=10: set())
    with pytest.raises(SystemExit):
        selftest.main()
    assert scratch.exists() == designer_running
    assert (str(scratch) in capsys.readouterr().out) == designer_running


def test_a_bridge_error_reading_the_library_packages_at_the_start_is_a_failed_check() -> None:
    # REVIEW.md TST-51: this ran before the try/finally, unguarded, so an error answer ended the run
    # with no summary and a Designer the self-test started was never quit
    import asyncio
    from types import SimpleNamespace

    selftest = _selftest()

    async def bridge_error(name: str, args: dict[str, Any] | None = None) -> SimpleNamespace:
        return SimpleNamespace(content=[SimpleNamespace(type='text', text='Error executing tool: bridge busy')])

    assert asyncio.run(selftest.library_packages(bridge_error)) is None
    assert selftest.results['self-test'] == [False]
    asyncio.run(selftest.restore_library_packages(bridge_error, None))  # then skipped, not a crash
    assert selftest.skipped == [('self-test', 'leaves the library packages loaded as it found them')]


def test_a_bridge_error_reading_the_editors_graph_at_the_start_is_a_failed_check() -> None:
    # REVIEW.md TST-59: this parse ran before the try/finally, unguarded, like TST-51's
    import asyncio
    from types import SimpleNamespace

    selftest = _selftest()

    async def bridge_error(name: str, args: dict[str, Any] | None = None) -> SimpleNamespace:
        return SimpleNamespace(content=[SimpleNamespace(type='text', text='Error executing tool: bridge busy')])

    assert asyncio.run(selftest.editor_graph(bridge_error)) == ''
    assert selftest.results['self-test'] == [False]


def test_every_category_function_is_run() -> None:
    # REVIEW.md TST-74: the coverage scans read every module of the folder, so a category function left
    # out of CATEGORIES would count as covering its tools, parameters and ops while it never runs
    import inspect
    import pkgutil

    selftest = _selftest()
    package = sys.modules['test_all_tools']
    run = set(selftest.CATEGORIES) | {selftest.lifecycle.run}  # lifecycle: from the finally, own Designer only
    defined: set[Any] = set()
    for info in pkgutil.iter_modules(package.__path__):
        if info.name in ('common', '__main__', 'alone'):  # helpers, the index itself, and the runner of single checks
            continue
        module = importlib.import_module('test_all_tools.' + info.name)
        source = inspect.getsource(module)
        defined |= {
            f
            for f in vars(module).values()
            if inspect.iscoroutinefunction(f)
            and f.__module__ == module.__name__
            # a check of its own, check_<what>(ctx), runs when a category function of its module awaits it
            # (AGENTS.md, the self-test); alone.py runs it on its own too
            and not (f.__name__.startswith('check_') and re.search(r'await\s+%s\(' % f.__name__, source))
        }
    assert defined, 'no category functions found'
    missing = sorted('%s.%s' % (f.__module__.split('.')[-1], f.__name__) for f in defined - run)
    assert not missing, 'category functions not in CATEGORIES (never run): %s' % missing


def _run_designer_script(reply: str, is_error: bool = False) -> list[bool]:
    """The checks recorded under run_designer_script by one designer_script call with this reply."""
    _selftest()
    common = importlib.import_module('test_all_tools.common')
    common.results.pop('run_designer_script', None)
    result = SimpleNamespace(content=[SimpleNamespace(type='text', text=reply)], is_error=is_error)

    async def call(name: str, args: dict[str, Any] | None = None) -> Any:
        return result

    assert asyncio.run(common.designer_script(call, 'facts/a_script', graph='g')) is result
    return list(common.results.pop('run_designer_script', []))


def test_a_script_that_raises_fails_the_run() -> None:
    """A traceback shows the failing source line, and its output token with it, so a check reading that token can
    pass having measured nothing (REVIEW.md TST-117, TST-125): the failure is recorded where it happens."""
    assert _run_designer_script('NODES=3\n\n--- ERROR ---\nTraceback (most recent call last):\n') == [False]
    assert _run_designer_script('no such file', is_error=True) == [False]


def test_a_script_that_runs_adds_no_check() -> None:
    assert _run_designer_script('NODES=3\n') == []


def test_a_failed_script_shows_its_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Setup scripts discard their result, so this is the only place it shows (REVIEW.md TST-132)."""
    trace = 'Traceback (most recent call last):\n  File "%s", line 3\nValueError: the real reason' % ('/long/path' * 30)
    assert _run_designer_script('\n--- ERROR ---\n' + trace) == [False]
    printed = capsys.readouterr().out
    fail_line = next(l for l in printed.splitlines() if l.startswith('FAIL'))
    assert 'ValueError: the real reason' in fail_line
    assert trace in printed
