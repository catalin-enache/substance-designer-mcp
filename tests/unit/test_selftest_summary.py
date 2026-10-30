"""The live self-test's summary (REVIEW.md TST-1): a tool counts as covered only when it had a
check that ran; one whose checks were all skipped is listed, not counted."""
import importlib.util
import os

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
