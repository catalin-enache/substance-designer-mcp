"""The live self-test's summary (REVIEW.md TST-1): a tool counts as covered only when it had a
check that ran; one whose checks were all skipped is listed, not counted."""
import importlib.util
import os

import pytest

from conftest import ROOT


def _selftest():
    spec = importlib.util.spec_from_file_location('selftest_under_test', os.path.join(ROOT, 'tests', 'test_all_tools.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_skipped_only_tools_are_not_counted_as_covered():
    summary, ok = _selftest().summarize(['a', 'b', 'c'], {'a': [True], 'b': []}, [('b', 'closes Designer')])
    assert '1/3 tools covered' in summary
    assert "only skipped: ['b']" in summary and "NOT covered: ['c']" in summary
    assert not ok                                   # c has no check at all


def test_skips_alone_do_not_fail_the_run():
    # quit_designer is always skipped while your own Designer runs; that is reported, not a failure
    summary, ok = _selftest().summarize(['a', 'b'], {'a': [True, True], 'b': []}, [('b', 'x')])
    assert ok and '1/2 tools covered' in summary and "only skipped: ['b']" in summary
    assert 'checks passed: 2/2; skipped: 1; tools with failures: none' in summary


def test_a_failed_check_fails_the_run():
    summary, ok = _selftest().summarize(['a'], {'a': [True, False]}, [])
    assert not ok and 'tools with failures: a' in summary


def test_cleanup_covers_every_graph_the_self_test_creates():
    # REVIEW.md TST-9: the size-inheritance check's 'inherit_*' graphs weren't matched by CLEAN,
    # so they stayed open if the check failed midway
    import re
    with open(os.path.join(ROOT, 'tests', 'test_all_tools.py'), encoding='utf-8') as f:
        src = f.read()
    created = [n for n in re.findall(r"setIdentifier\('([^']*)'", src) if n != '%s']   # '%s' is DUP_GRAPH
    assert created and all(name.startswith('mcp_selftest') for name in created), created
    assert ".startswith('mcp_selftest')" in _selftest().CLEAN


def test_a_check_that_is_not_a_bool_is_counted(monkeypatch):
    # REVIEW.md TST-29: check() stored the condition as given; `refs and not missing` with no refs is
    # [], and summarize()'s sum then raised TypeError, so no summary was printed
    selftest = _selftest()
    monkeypatch.setattr(selftest, 'results', {})
    selftest.check('tool', 'empty list', [])
    selftest.check('tool', 'none', None)
    text, ok = selftest.summarize(['tool'], selftest.results, [])
    assert not ok and 'checks passed: 0/2' in text


def test_a_bridge_error_in_the_library_clean_up_is_a_failed_check_not_a_crash():
    # REVIEW.md TST-33: an error answer there raised AttributeError in the self-test's finally,
    # skipping the rest of its clean-up (the snapshots, putting the user's graph back, the quit)
    import asyncio
    from types import SimpleNamespace
    selftest = _selftest()

    async def bridge_error(name, args=None):
        return SimpleNamespace(content=[SimpleNamespace(type='text', text='Error executing tool: bridge busy')])
    asyncio.run(selftest.restore_library_packages(bridge_error, []))
    assert selftest.results['self-test'] == [False]


@pytest.mark.parametrize('designer_running', [True, False])
def test_the_scratch_folder_is_only_deleted_once_designer_is_closed(monkeypatch, capsys, tmp_path, designer_running):
    # REVIEW.md PLG-18 (and PLG-9): deleting it while Designer ran crashed Designer twice, in its file
    # watcher; with a Designer still running it is left in the OS temp folder, and the path printed
    selftest = _selftest()
    scratch = tmp_path / 'sd_mcp_selftest_x'
    scratch.mkdir()
    (scratch / 'graph.sbs').write_text('x')
    monkeypatch.setattr(selftest.tempfile, 'mkdtemp', lambda prefix: str(scratch))

    async def run(scratch):
        selftest.STATE['was_running'] = designer_running
        return []
    monkeypatch.setattr(selftest, 'run', run)
    monkeypatch.setattr(selftest, 'designer_alive', lambda: designer_running)
    monkeypatch.setattr(selftest, 'new_crash_dumps', lambda before, wait_s=10: set())
    with pytest.raises(SystemExit):
        selftest.main()
    assert scratch.exists() == designer_running
    assert (str(scratch) in capsys.readouterr().out) == designer_running


def test_a_bridge_error_reading_the_library_packages_at_the_start_is_a_failed_check():
    # REVIEW.md TST-51: this ran before the try/finally, unguarded, so an error answer ended the run
    # with no summary and a Designer the self-test started was never quit
    import asyncio
    from types import SimpleNamespace
    selftest = _selftest()

    async def bridge_error(name, args=None):
        return SimpleNamespace(content=[SimpleNamespace(type='text', text='Error executing tool: bridge busy')])
    assert asyncio.run(selftest.library_packages(bridge_error)) is None
    assert selftest.results['self-test'] == [False]
    asyncio.run(selftest.restore_library_packages(bridge_error, None))   # then skipped, not a crash
    assert selftest.skipped == [('self-test', 'leaves the library packages loaded as it found them')]
