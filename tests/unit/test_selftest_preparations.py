"""Each category of the live self-test prepares its own environment (category_run.py): tests/test_all_tools/
category_run.py runs one category on a Ctx of its own, after its own preparation (<category>/preparations.py), and
cleans up after it; no category uses another's checks, setup or helpers. No Designer: a fake answers the tool calls."""

import ast
import asyncio
import importlib
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from conftest import REAL_SNAPSHOT_DIR, SELFTEST_DIR

# what every category gets from the run itself, not from a preparation (common.Ctx)
SHARED = {'c', 's', 'scratch', 'helper_source', 'was_running', 'crash_watch', 'fresh'}


def _module(name: str) -> Any:  # a module imported by name: PyCharm can't see its names
    """A module of the self-test, imported afresh with the others, so each test starts with an empty check record."""
    tests_dir = os.path.dirname(SELFTEST_DIR)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    for loaded in [m for m in sys.modules if m == 'test_all_tools' or m.startswith('test_all_tools.')]:
        del sys.modules[loaded]
    module = importlib.import_module('test_all_tools.' + name)
    if name == 'category_run':
        vars(module)['PAUSE_S'] = 0  # no Designer to wait for
    return module


def _folders() -> list[str]:
    """Every category's folder: one holding a checks.py."""
    return sorted(name for name in os.listdir(SELFTEST_DIR) if Path(SELFTEST_DIR, name, 'checks.py').is_file())


def _result(t: str, error: bool = False) -> Any:
    return SimpleNamespace(content=[SimpleNamespace(type='text', text=t)], is_error=error)


class FakeDesigner:
    """c(name, args): the library packages listed as none, the clean-up answered, any other tool 'ok'."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, name: str, args: dict[str, Any] | None = None) -> Any:
        self.calls.append((name, args or {}))
        if name == 'execute_designer_code':
            return _result('removed 0' if 'unloadUserPackage' in (args or {}).get('code', '') else 'LIBS=')
        return _result('ok')


def _ctx(c: Any, scratch: str = 'scratch') -> Any:
    common = sys.modules['test_all_tools.common']
    return common.Ctx(c=c, s=None, scratch=scratch, helper_source='def helper(): pass', was_running=False)


def _step(module: str, name: str, body: Any = None) -> Any:
    """A step of the category <module> (test_all_tools.<module>.checks), running body(ctx) if given."""

    async def step(ctx: Any) -> None:
        if body is not None:
            await body(ctx)

    step.__module__, step.__qualname__ = 'test_all_tools.%s.checks' % module, name
    return step


def test_a_categorys_preparation_is_the_prepare_of_its_own_folder() -> None:
    run = _module('category_run')
    params = importlib.import_module('test_all_tools.params.checks')
    preparations = importlib.import_module('test_all_tools.params.preparations')
    assert run.preparation(params.run) is preparations.prepare
    assert run.preparation(_step('params', 'check_x')) is preparations.prepare  # a check of it run alone too


def test_a_category_with_no_preparations_module_has_none() -> None:
    run = _module('category_run')
    bridge = importlib.import_module('test_all_tools.bridge.checks')
    assert not Path(SELFTEST_DIR, 'bridge', 'preparations.py').exists()
    assert run.preparation(bridge.run) is None

    async def not_a_category(ctx: Any) -> None:
        pass

    assert run.preparation(not_a_category) is None


def test_the_preparation_runs_first_on_the_ctx_the_checks_get(monkeypatch: pytest.MonkeyPatch) -> None:
    run = _module('category_run')
    seen: list[tuple[str, Any]] = []

    async def prepare(ctx: Any) -> None:
        ctx.G = {'graph': 'mcp_selftest'}
        seen.append(('prepare', ctx))

    async def check(ctx: Any) -> None:
        seen.append(('check', ctx.G))

    monkeypatch.setitem(vars(run), 'preparation', lambda step: prepare)
    c = FakeDesigner()
    ran = asyncio.run(run.run_category(_ctx(c), [_step('params', 'run', check)]))
    assert ran.prepared and ran.cleaned
    assert [what for what, _ in seen] == ['prepare', 'check'] and seen[1][1] == {'graph': 'mcp_selftest'}


def test_a_preparation_that_raises_is_the_environment_failing_and_runs_no_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _module('category_run')
    ran_checks: list[str] = []

    async def prepare(ctx: Any) -> None:
        raise run.common.Unprepared('create_graph: Designer is not reachable')

    async def check(ctx: Any) -> None:
        ran_checks.append('check')

    monkeypatch.setitem(vars(run), 'preparation', lambda step: prepare)
    c = FakeDesigner()
    ran = asyncio.run(run.run_category(_ctx(c), [_step('params', 'run', check)]))
    assert not ran.prepared and ran_checks == []
    assert run.common.results['self-test'].count(False) == 1  # the environment, not each check
    assert ('execute_designer_code', {'code': run.common.CLEAN}) in c.calls, 'cleaned up all the same'


def test_a_setup_with_a_failed_check_is_the_environment_failing_too(monkeypatch: pytest.MonkeyPatch) -> None:
    # alone.run's setup(ctx) runs after the preparation, as part of the environment
    run = _module('category_run')
    ran_checks: list[str] = []

    async def setup(ctx: Any) -> None:
        run.common.check('tool', 'the environment', False)

    async def check(ctx: Any) -> None:
        ran_checks.append('check')

    monkeypatch.setitem(vars(run), 'preparation', lambda step: None)
    ran = asyncio.run(run.run_category(_ctx(FakeDesigner()), [_step('params', 'run', check)], setup=setup))
    assert not ran.prepared and ran_checks == []


def test_a_check_that_raises_fails_and_the_next_one_still_runs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run = _module('category_run')
    ran_checks: list[str] = []

    async def raises(ctx: Any) -> None:
        raise ValueError('a parse that found nothing')

    async def after(ctx: Any) -> None:
        ran_checks.append('after')

    monkeypatch.setitem(vars(run), 'preparation', lambda step: None)
    steps = [_step('facts', 'check_a', raises), _step('facts', 'check_b', after)]
    ran = asyncio.run(run.run_category(_ctx(FakeDesigner()), steps))
    assert ran.prepared and ran_checks == ['after']
    assert run.common.results['self-test'].count(False) == 1
    assert 'a parse that found nothing' in capsys.readouterr().out


def test_the_category_is_cleaned_up_after_its_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    # its graphs, then the library packages it loaded: the next category sees nothing it left (category_run.py)
    run = _module('category_run')
    monkeypatch.setitem(vars(run), 'preparation', lambda step: None)
    c = FakeDesigner()

    async def check(ctx: Any) -> None:
        c.calls.append(('the check', {}))

    asyncio.run(run.run_category(_ctx(c), [_step('facts', 'run', check)]))
    names = [name for name, _ in c.calls]
    assert names.index('the check') < c.calls.index(('execute_designer_code', {'code': run.common.CLEAN}))


def test_the_clean_up_removes_the_self_test_graphs_snapshots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # layout and save snapshot the self-test graph: the next category would find them (list_snapshots, diff_graph)
    run = _module('category_run')
    monkeypatch.setitem(vars(run), 'preparation', lambda step: None)
    monkeypatch.setenv('SD_SNAPSHOT_DIR', str(tmp_path))
    (tmp_path / 'mcp_selftest').mkdir()
    (tmp_path / 'mcp_selftest' / 'before.sbs').write_text('x')
    (tmp_path / 'someone_elses').mkdir()
    asyncio.run(run.run_category(_ctx(FakeDesigner()), [_step('layout', 'run')]))
    assert not (tmp_path / 'mcp_selftest').exists() and (tmp_path / 'someone_elses').exists()


def test_no_unit_test_cleans_up_the_real_snapshot_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-230: every unit test reaching run_category ends with remove_test_snapshots, which removed the real
    # folder's mcp_selftest (~/.sd_mcp/snapshots, or SD_SNAPSHOT_DIR as the test run found it) under a live run there
    import shutil

    real = os.path.realpath(REAL_SNAPSHOT_DIR)
    run = _module('category_run')
    removed: list[str] = []
    monkeypatch.setattr(shutil, 'rmtree', lambda path, **kw: removed.append(os.path.realpath(path)))
    monkeypatch.setitem(vars(run), 'preparation', lambda step: None)
    asyncio.run(run.run_category(_ctx(FakeDesigner()), [_step('layout', 'run')]))
    assert removed, "the clean-up removes the self-test graph's snapshots"
    assert not [path for path in removed if path.startswith(real)], removed


def test_a_fresh_ctx_shares_only_the_run_and_has_a_folder_of_its_own(tmp_path: Path) -> None:
    common = _module('common')
    ctx = common.Ctx(c=print, s=None, scratch=str(tmp_path), helper_source='h', was_running=True)
    ctx.G = {'graph': 'mcp_selftest'}
    fresh = ctx.fresh('params')
    assert (fresh.c, fresh.s, fresh.helper_source, fresh.was_running) == (print, None, 'h', True)
    assert fresh.scratch == str(tmp_path / 'params') and os.path.isdir(fresh.scratch)
    assert not hasattr(fresh, 'G'), 'what another category prepared'


def _category_sources(folder: str) -> dict[str, str]:
    """{file: source} of a category's own modules, not its Designer scripts."""
    return {
        name: Path(SELFTEST_DIR, folder, name).read_text(encoding='utf-8')
        for name in os.listdir(Path(SELFTEST_DIR, folder))
        if name.endswith('.py')
    }


def _others_used(source: str, folder: str, folders: list[str]) -> set[str]:
    """The other categories a module of `folder` (at its top level) imports or names: `test_all_tools.<name>`, `from
    test_all_tools import <name>`, `from .. import <name>`, `from ..<name>... import`."""
    used = set(re.findall(r'\btest_all_tools\.(\w+)', source))
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            if node.module == 'test_all_tools' or (node.level == 2 and node.module is None):
                used |= {alias.name for alias in node.names}
            elif node.level == 2 and node.module:
                used.add(node.module.split('.')[0])
    return {name for name in used if name in folders and name != folder}


def test_no_category_uses_another_categorys_code() -> None:
    # a change to one category's checks, preparation or helpers can't reach any other (the user's choice, 2026-11-10)
    folders = _folders()
    assert len(folders) == 23, folders
    used = [
        '%s/%s uses %s' % (folder, name, sorted(others))
        for folder in folders
        for name, source in _category_sources(folder).items()
        if (others := _others_used(source, folder, folders))
    ]
    assert not used, used


@pytest.mark.parametrize(
    'line',
    [
        'from test_all_tools import params',
        'from .. import params',
        'from ..params.checks import run',
        'from test_all_tools.params import checks',
        'import test_all_tools.params.checks',
    ],
)
def test_every_form_of_import_of_another_category_is_seen(line: str) -> None:
    # REVIEW.md TST-239: the first two, the form the code uses (bridge/checks.py), went unseen
    assert _others_used(line + '\n', 'bridge', _folders()) == {'params'}


def _attributes(source: str, assigned: bool) -> set[str]:
    pattern = r'\bctx\.(\w+)\s*=(?!=)' if assigned else r'\bctx\.(\w+)\b(?!\s*=[^=])'
    return set(re.findall(pattern, source)) - SHARED


def test_each_category_prepares_what_its_checks_read_from_ctx() -> None:
    missing: list[str] = []
    for folder in _folders():
        sources = _category_sources(folder)
        prepared = _attributes(sources.get('preparations.py', ''), assigned=True)
        checks = ''.join(source for name, source in sources.items() if name != 'preparations.py')
        for attribute in sorted(_attributes(checks, assigned=False) - _attributes(checks, assigned=True) - prepared):
            missing.append('%s reads ctx.%s, which its preparation never sets' % (folder, attribute))
    assert not missing, missing


def test_a_preparation_records_no_check() -> None:
    # it is the environment, not a check: a tool failing in it raises common.Unprepared (common.prepared_call)
    for folder in _folders():
        source = _category_sources(folder).get('preparations.py')
        if source is not None:
            assert 'async def prepare(ctx: Ctx) -> None:' in source, folder
            assert not re.search(r'\b(check|skip|designer_script)\(', source), folder


def test_a_prepared_call_returns_the_text_and_raises_on_an_error() -> None:
    common = _module('common')

    async def c(name: str, args: dict[str, Any] | None = None) -> Any:
        if name == 'create_graph':
            return _result('Created mcp_selftest (512 px)')
        if name == 'run_designer_script':
            return _result('ok\n--- ERROR ---\nTraceback ...\nValueError: no node', False)
        return _result('Designer is not reachable', True)

    assert asyncio.run(common.prepared_call(c, 'create_graph', {'name': 'x'})) == 'Created mcp_selftest (512 px)'
    with pytest.raises(common.Unprepared, match='apply_edits: Designer is not reachable'):
        asyncio.run(common.prepared_call(c, 'apply_edits', {}))
    with pytest.raises(common.Unprepared, match='ValueError: no node'):
        asyncio.run(common.prepared_call(c, 'run_designer_script', {}))


def test_the_refs_of_an_apply_edits_result_are_read_by_name() -> None:
    common = _module('common')
    t = "add clouds_2 -> 1201\n  ref 'clouds' = 1201\nadd levels -> 1202\n  ref 'lv' = 1202\napplied 2 op(s); refs: ..."
    assert common.refs(t) == {'clouds': '1201', 'lv': '1202'}


def test_a_category_whose_clean_up_fails_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md TST-238: _cleaned always returning True passed every test
    run = _module('category_run')
    monkeypatch.setitem(vars(run), 'preparation', lambda step: None)

    async def restore(c: Any, libs_before: Any) -> None:
        run.common.check('self-test', 'leaves the library packages loaded as it found them', False, '1 more')

    monkeypatch.setitem(vars(run), 'restore_library_packages', restore)
    ran = asyncio.run(run.run_category(_ctx(FakeDesigner()), [_step('layout', 'run')]))
    assert ran.prepared and not ran.cleaned
