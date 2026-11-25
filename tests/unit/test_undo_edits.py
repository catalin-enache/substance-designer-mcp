"""undo_edits (server_tools/undo.py): the server's memory of the undo steps of this session's calls (core.py,
_with_undo, STEPS), the job the tool sends, run here against Designer's history faked (history_fakes.py), and the
tool's text for each outcome. The undo itself (designer_rollback.undo_session): test_rollback.py."""

import contextlib
import inspect
import io
import os
import re
import sys
from collections.abc import Callable
from types import ModuleType

import pytest
from docs_text import flat
from history_fakes import E0, E1, E2, E3, LISTED, OTHER, READ, Designer, full, modules
from selftest_fakes import fresh

import project_constants
from conftest import fake_bridge, patch_server, server
from project_constants import Json, Reply, ScriptRequest
from server_tools import core
from server_tools.core import SessionStep


@pytest.fixture
def steps() -> list[SessionStep]:
    """The server's memory of its calls' steps, empty: a session just started (conftest.py, fresh_session)."""
    return core.STEPS


def _remember(steps: list[SessionStep], edits: list[str], reads: tuple[str, ...] = ()) -> None:
    """The memory holding `edits` and `reads`, as calls of this session made them."""
    steps.extend([SessionStep(name, True) for name in edits] + [SessionStep(name, False) for name in reads])


@pytest.fixture
def jobs(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The code each call sends to Designer, run here as the plugin runs a job (a trace function set, its output the
    reply's) against the fake PySide6 of history_fakes.py, on the Designer the test made last."""
    for name, module in modules().items():
        monkeypatch.setitem(sys.modules, name, module)
    codes: list[str] = []

    def send(request: ScriptRequest, wait: float, port: int | None = None) -> Reply:  # the tools here send scripts
        code = request['code']
        codes.append(code)
        out = io.StringIO()
        previous = sys.gettrace()
        sys.settrace(lambda frame, event, arg: None)
        try:
            with contextlib.redirect_stdout(out):
                exec(compile(code, '<job>', 'exec'), {'__file__': '<job>'})
        finally:
            sys.settrace(previous)
        return {'ok': True, 'output': out.getvalue(), 'error': ''}

    patch_server(monkeypatch, '_send', send)
    return codes


@pytest.fixture
def invisible(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """The tag's invisible form, which its constants allow (project_constants.py): characters repr escapes. The
    constants are switched here, where the names are made and read, in the self-test's common loaded afresh too.
    Returns the batch category's checks, loaded so, for their pattern of a step (said_step)."""
    batch_checks = fresh('batch.checks')
    for module in (project_constants, sys.modules['test_all_tools.common']):
        monkeypatch.setitem(vars(module), 'TAG_PREFIX', '')
        monkeypatch.setitem(vars(module), 'TAG_ALPHABET', '\u200b\u200c\u200d\u2060')
        monkeypatch.setitem(vars(module), 'TAG_LENGTH', 16)
    return batch_checks


Names = tuple[str, str, str]  # two of the session's steps, oldest first, and another session's


@pytest.fixture(params=['plain', 'invisible'])
def names(request: pytest.FixtureRequest) -> Names:
    """Steps' names, plain, or with tags of the invisible form (`invisible`): the replies must name them as they are,
    in the steps undone, a refusal's others and a stop midway (REVIEW.md SRV-272)."""
    if request.param == 'plain':
        return E1, E2, OTHER
    request.getfixturevalue('invisible')
    first, second, other = ('Claude: %s' % label + project_constants.new_tag() for label in ('a', 'b', 'c'))
    return first, second, other


def _error(call: Callable[[], object]) -> str:
    """The text of the ToolError `call` raises."""
    with pytest.raises(server.ToolError) as raised:
        call()
    return str(raised.value)


# --- the server's memory


def test_each_wrapped_call_adds_its_steps_name_in_order(steps: list[SessionStep]) -> None:
    codes = [server._with_undo('pass', 'Claude: a'), server._with_undo('pass', 'Claude: b', edit=False)]
    assert [step.edit for step in steps] == [True, False]
    for step, label, code in zip(steps, ['Claude: a', 'Claude: b'], codes, strict=True):
        assert step.name.startswith(label + server.TAG_PREFIX)
        assert '\n_step = %r\n' % step.name in code  # the name the call's undo step is opened with


@pytest.mark.parametrize(
    ('tool', 'args', 'label', 'edit'),
    [
        ('apply_edits', {'ops': [{'op': 'move', 'node': '1', 'position': [0, 0]}]}, 'Claude: apply 1 edits', True),
        ('create_graph', {'name': 'g'}, 'Claude: create graph g', True),
        ('execute_designer_code', {'code': 'pass'}, 'Claude: code', True),
        # the reads: their step, a temporary node added and removed or a value set and put back, changes nothing
        ('preview_node', {'node_id': '1'}, 'Claude: preview node', False),
        ('node_stats', {'node_id': '1'}, 'Claude: node stats', False),
        ('check_tiling', {'node_id': '1'}, 'Claude: check tiling', False),
        # its temporary package and node, and the library package it opens (REVIEW.md SRV-265)
        ('describe_node', {'definition': 'blend'}, 'Claude: describe node', False),
        ('sweep_param', {'node_id': '1', 'param': 'x', 'values': [1]}, 'Claude: sweep x', False),
    ],
)
def test_each_tools_step_is_remembered_a_reads_as_not_counted(
    steps: list[SessionStep], sent: list[str], tool: str, args: dict[str, Json], label: str, edit: bool
) -> None:
    with contextlib.suppress(server.ToolError):  # a read finds no image in the empty reply
        getattr(server, tool)(**args)
    [step] = steps
    assert step.name.startswith(label + server.TAG_PREFIX) and step.edit is edit


def test_search_nodes_library_scan_is_remembered_as_a_read(
    steps: list[SessionStep], monkeypatch: pytest.MonkeyPatch, tmp_path: os.PathLike[str]
) -> None:
    # with no graph in the editor, its temporary package made steps of Designer's own (REVIEW.md SRV-265's pattern)
    patch_server(monkeypatch, '_LIBRARY_CACHE', {})  # a server's first search scans the library
    os.mkdir(os.path.join(tmp_path, 'packages'))  # Designer's library, empty
    fake_bridge(monkeypatch, lambda code: 'RESOURCES_DIR=%s\n' % tmp_path)
    server.search_nodes('levels')
    [step] = steps
    assert step.name.startswith('Claude: search nodes' + server.TAG_PREFIX) and not step.edit


READ_FAILED = 'Traceback (most recent call last):\n  File "<x>", line 1, in <module>\nRuntimeError: no such node'


def _failing(monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    """Every call fails with READ_FAILED, its rollback saying `state`, as the code _with_undo sends prints it."""
    failed: Reply = {'ok': False, 'output': '\n%s%s\n' % (server.ROLLBACK_LINE, state), 'error': READ_FAILED}
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: failed)


@pytest.mark.parametrize(
    ('tool', 'args', 'says'),
    [
        ('describe_node', {'definition': 'nope'}, 'READ_UNDONE'),  # the reads
        ('preview_node', {'node_id': '1'}, 'READ_UNDONE'),
        ('node_stats', {'node_id': '1'}, 'READ_UNDONE'),
        ('sweep_param', {'node_id': '1', 'param': 'x', 'values': [1]}, 'READ_UNDONE'),
        ('apply_edits', {'ops': [{'op': 'move', 'node': '1', 'position': [0, 0]}]}, 'UNDONE'),  # an edit
    ],
)
def test_a_reads_failure_says_only_its_own_step_was_taken_back(
    steps: list[SessionStep], monkeypatch: pytest.MonkeyPatch, tool: str, args: dict[str, Json], says: str
) -> None:
    # REVIEW.md SRV-268: a read's failure said its edits were taken back, and its package might show as modified
    _failing(monkeypatch, 'undone')
    said = _error(lambda: getattr(server, tool)(**args))
    assert said == 'RuntimeError: no such node. ' + getattr(server, says)


@pytest.mark.parametrize(('state', 'kept'), [('undone', False), ("not ours: 'Add Atomic Node'", True)])
def test_a_failed_calls_step_its_rollback_took_back_is_forgotten(
    steps: list[SessionStep], monkeypatch: pytest.MonkeyPatch, state: str, kept: bool
) -> None:
    # REVIEW.md SRV-269: rolled back, it was kept, and once 25 steps were listed it counted as maybe older
    _failing(monkeypatch, state)
    with pytest.raises(server.ToolError):
        server.apply_edits([{'op': 'move', 'node': '1', 'position': [0, 0]}])
    assert len(steps) == int(kept)


def test_a_script_runs_step_is_remembered_as_an_edit(
    steps: list[SessionStep], sent: list[str], tmp_path: os.PathLike[str]
) -> None:
    script = os.path.join(tmp_path, 'edit.py')
    with open(script, 'w', encoding='utf-8') as f:
        f.write('pass\n')
    server.run_designer_script(script)
    assert [(step.name.startswith('Claude: edit.py' + server.TAG_PREFIX), step.edit) for step in steps] == [
        (True, True)
    ]


def test_a_failed_calls_step_its_rollback_left_stays_for_undo_edits(
    steps: list[SessionStep], monkeypatch: pytest.MonkeyPatch, jobs: list[str]
) -> None:
    # its error says what stays and that undo_edits takes it back (designer_helpers/batch.py, the KEPT line)
    run_here = server._send  # the job run here (the `jobs` fixture)
    _failing(monkeypatch, "not ours: '%s'" % OTHER)
    with pytest.raises(server.ToolError):
        server.apply_edits([{'op': 'move', 'node': '1', 'position': [0, 0]}])
    [step] = steps
    assert step.edit
    designer = Designer([OTHER, step.name])
    patch_server(monkeypatch, '_send', run_here)
    text = server.undo_edits(include_others=True)
    assert "'%s'" % step.name in text and designer.steps == [] and steps == [step._replace(undone=True)]


# --- the tool's text for each outcome, the job run against Designer's history faked


def test_the_sessions_last_calls_are_undone_newest_first_and_named(steps: list[SessionStep], jobs: list[str]) -> None:
    _remember(steps, [E1, E2, E3])
    designer = Designer([E3, E2, E1, OTHER])
    text = server.undo_edits(count=3)
    assert text == "Undid 3 steps, newest first: '%s', '%s', '%s'. %s" % (E3, E2, E1, server.ON_REDO)
    assert designer.steps == [OTHER] and steps == [SessionStep(name, True, True) for name in (E1, E2, E3)]


def test_a_reads_step_is_undone_along_and_marked(steps: list[SessionStep], jobs: list[str]) -> None:
    _remember(steps, [E1], (READ,))
    designer = Designer([READ, E1])
    text = server.undo_edits()
    assert text == "Undid 2 steps, newest first: '%s'%s, '%s'. %s" % (READ, server.MARK_READ, E1, server.ON_REDO)
    assert designer.steps == [] and steps == [SessionStep(E1, True, True), SessionStep(READ, False, True)]


def test_a_step_that_isnt_the_sessions_on_top_is_named_and_nothing_undone(
    steps: list[SessionStep], jobs: list[str], names: Names
) -> None:
    first, _, other = names
    _remember(steps, [first])
    designer = Designer([other, first])
    assert _error(server.undo_edits) == server.OTHERS % ("'%s'" % other)
    assert designer.steps == [other, first] and designer.invoked == [] and len(steps) == 1


def test_with_include_others_the_step_on_top_is_undone_too_and_marked(
    steps: list[SessionStep], jobs: list[str], names: Names
) -> None:
    first, _, other = names
    _remember(steps, [first])
    designer = Designer([other, first])
    text = server.undo_edits(include_others=True)
    assert text == "Undid 2 steps, newest first: '%s'%s, '%s'. %s" % (other, server.MARK_OTHER, first, server.ON_REDO)
    assert designer.steps == [] and steps == [SessionStep(first, True, True)]


def test_calls_asked_for_beyond_the_listed_steps_are_refused(steps: list[SessionStep], jobs: list[str]) -> None:
    _remember(steps, [E1, E2])
    designer = Designer([*full(E2), E1])
    assert _error(lambda: server.undo_edits(count=2, include_others=True)) == server.BEYOND % (LISTED, 1, 2)
    assert designer.invoked == [] and len(steps) == 2


def test_a_count_above_the_sessions_steps_listed_undoes_those_listed_and_says_so(
    steps: list[SessionStep], jobs: list[str]
) -> None:
    _remember(steps, [E0, E1])
    designer = Designer([E1, OTHER])
    text = server.undo_edits(count=3)
    assert text == "Undid 1 step, newest first: '%s'. %s %s" % (E1, server.ON_REDO, server.FEWER % (1, 3))
    assert designer.steps == [OTHER] and steps == [SessionStep(E1, True, True)]  # E0, not listed, is dropped


def test_with_none_of_the_sessions_calls_listed_nothing_is_undone(steps: list[SessionStep], jobs: list[str]) -> None:
    _remember(steps, [E1])
    designer = Designer([OTHER])
    assert _error(server.undo_edits) == server.NO_STEPS
    assert designer.invoked == [] and steps == []  # E1, not listed, is dropped


def test_the_description_gives_the_steps_the_undo_list_shows() -> None:
    # Designer's dropdown lists the newest LISTED steps (designer_rollback.py; the batch category's designer facts)
    assert 'the newest %d steps the Undo list shows' % LISTED in (inspect.getdoc(server.undo_edits) or '')


def test_with_the_dropdown_full_a_call_with_no_step_is_dropped_and_the_rest_undone(
    steps: list[SessionStep], jobs: list[str]
) -> None:
    # REVIEW.md SRV-266: E2 failed and was rolled back; it was refused as maybe older than the steps listed
    _remember(steps, [E1, E2, E3])
    designer = Designer(full(E3, E1))
    text = server.undo_edits(count=3)
    assert text == "Undid 2 steps, newest first: '%s', '%s'. %s %s" % (E3, E1, server.ON_REDO, server.FEWER % (2, 3))
    assert designer.undone == [E1, E3] and steps == [SessionStep(E1, True, True), SessionStep(E3, True, True)]


def test_a_step_undone_then_redone_counts_again_unmarked(steps: list[SessionStep], jobs: list[str]) -> None:
    # a step undone is kept, and counts as the session's again once a Redo lists it (the user, 2026-11-25)
    _remember(steps, [E1, E2])
    designer = Designer([E2, E1])
    server.undo_edits()
    designer.steps.insert(0, designer.undone.pop(0))  # a Redo from code
    text = server.undo_edits(count=2)
    assert text == "Undid 2 steps, newest first: '%s', '%s'. %s" % (E2, E1, server.ON_REDO)
    assert designer.steps == [] and steps == [SessionStep(E1, True, True), SessionStep(E2, True, True)]


def test_steps_undone_by_two_calls_then_redone_both_count_again(steps: list[SessionStep], jobs: list[str]) -> None:
    # a step undone isn't said gone while it is off the Undo list: it may be on the Redo list (the user, 2026-11-25)
    _remember(steps, [E1, E2])
    designer = Designer([E2, E1])
    server.undo_edits()
    server.undo_edits()
    for _ in range(2):  # two Redos from code
        designer.steps.insert(0, designer.undone.pop(0))
    text = server.undo_edits(count=2)
    assert text == "Undid 2 steps, newest first: '%s', '%s'. %s" % (E2, E1, server.ON_REDO)


def test_a_step_undone_that_never_comes_back_is_never_counted(steps: list[SessionStep], jobs: list[str]) -> None:
    # a change after the undo clears the Redo list: the step undone is nowhere, and stays in the memory, marked
    _remember(steps, [E1, E2])
    designer = Designer([E2, E1])
    server.undo_edits()
    designer.undone.clear()
    designer.steps.insert(0, E3)
    _remember(steps, [E3])
    text = server.undo_edits(count=3)
    assert text == "Undid 2 steps, newest first: '%s', '%s'. %s %s" % (E3, E1, server.ON_REDO, server.FEWER % (2, 3))
    assert SessionStep(E2, True, True) in steps


def test_with_the_dropdown_full_the_sessions_steps_all_undone_are_never_older_than_it(
    steps: list[SessionStep], jobs: list[str]
) -> None:
    # steps undone sit on the Redo list, not below the Undo list's: no BEYOND refusal (the user, 2026-11-25)
    _remember(steps, [E1, E2])
    designer = Designer([E2, E1, *full()])
    server.undo_edits(count=2)
    assert _error(server.undo_edits) == server.NO_STEPS
    assert designer.invoked == ['undo()'] * 2 and len(steps) == 2


# Designer's own steps of set_link_display's reload, as the Undo dropdown names them (REVIEW.md SRV-265; the
# link_display category's undo_edits check)
RELOADED = ['Open Package(s)', 'Unknown', 'Unreference package', 'Unset User Package']


@pytest.mark.parametrize('reloaded', [True, False])
def test_a_refusal_names_the_steps_of_a_reload_as_designers_own(
    steps: list[SessionStep], jobs: list[str], monkeypatch: pytest.MonkeyPatch, reloaded: bool
) -> None:
    # only once set_link_display has reloaded a package this session: the user's steps may have those names too
    monkeypatch.setitem(server._session, 'package_reloaded', reloaded)
    _remember(steps, [E1])
    Designer([*RELOADED, OTHER, E1])  # a step of another name too, which the note leaves out (REVIEW.md TST-879)
    others = ', '.join("'%s'" % name for name in [*RELOADED, OTHER])
    note = ' ' + server.RELOAD_STEPS_NOTE % ', '.join("'%s'" % name for name in RELOADED) if reloaded else ''
    assert _error(server.undo_edits) == server.OTHERS % others + note


def test_a_reads_rollback_text_claims_nothing_of_what_its_step_held() -> None:
    # REVIEW.md SRV-270: a sweep's step holds values set on the user's node, and a temporary output node is added to
    # the user's graph, either of which can leave its package marked modified
    assert 'made for itself' not in server.READ_UNDONE and 'may still show as modified' in server.READ_UNDONE


def test_with_the_tags_invisible_form_the_reply_names_each_step_as_it_is(
    steps: list[SessionStep], jobs: list[str], invisible: ModuleType
) -> None:
    # REVIEW.md SRV-271: a reply quoting names with repr showed escapes, and the live checks' pattern of a step
    # (SAID_STEP, batch/checks.py) found none
    server._with_undo('pass', 'Claude: apply 1 edits')
    server._with_undo('pass', 'Claude: preview node', edit=False)
    [edit, read] = [step.name for step in steps]
    Designer([OTHER, read, edit])
    refused = _error(server.undo_edits)
    text = server.undo_edits(include_others=True)
    for said in (refused, text):
        assert '\\u' not in said, said
    assert re.findall(invisible.said_step() + invisible.READ_MARK, text) == [
        ('Claude: preview node', invisible.READ_SAID),
        ('Claude: apply 1 edits', ''),
    ]


def test_the_reload_note_says_the_steps_are_most_likely_its_own_and_where_its_save_stays() -> None:
    # REVIEW.md SRV-267: the flag holds for the session and the names are Designer's generic ones, so a step of the
    # user's can match; and the reload saved the package, which an undo in Designer leaves in the file
    assert 'most likely' in server.RELOAD_STEPS_NOTE and "not the user's" not in server.RELOAD_STEPS_NOTE
    described = flat(inspect.getdoc(server.set_link_display) or '')
    assert 'the file keeps what it saved, the edits made before it included' in described


def test_set_link_displays_reload_is_remembered(sent: list[str]) -> None:
    server._reload_package_file('/nowhere/g.sbs')
    assert server._session['package_reloaded'] and len(sent) == 2  # the unload, then the load


def test_a_session_with_no_call_wrapped_sends_nothing(steps: list[SessionStep], jobs: list[str]) -> None:
    # after a reconnect: a new server, its memory empty
    assert _error(server.undo_edits) == server.NO_STEPS and jobs == []


@pytest.mark.parametrize('count', [0, -1])
def test_a_count_below_1_is_refused(steps: list[SessionStep], jobs: list[str], count: int) -> None:
    _remember(steps, [E1])
    assert _error(lambda: server.undo_edits(count=count)) == 'count is 1 or more, not %d' % count and jobs == []


def test_a_step_not_landing_midway_stops_and_says_what_was_undone(
    steps: list[SessionStep], jobs: list[str], names: Names
) -> None:
    first, second, _ = names
    _remember(steps, [first, second])
    designer = Designer([second, first], landing=1)
    said = _error(lambda: server.undo_edits(count=2))
    assert said == "Undid 1 of the 2 steps, newest first: '%s'. %s Then %s" % (
        second,
        server.ON_REDO,
        server.STEP_NOT_LANDED % ("'%s'" % first, 'after %g s' % server.ROLLBACK_LIMIT_S),
    )
    # it may still land
    assert designer.invoked == ['undo()'] * 2 and steps == [SessionStep(first, True), SessionStep(second, True, True)]


def test_a_step_made_on_top_midway_stops_the_undo_and_is_named(
    steps: list[SessionStep], jobs: list[str], names: Names
) -> None:
    # the step on top is named as undo_steps' "not ours" gives it (designer_rollback.py)
    first, second, other = names
    _remember(steps, [first, second])
    designer = Designer([second, first])

    def undo() -> None:
        designer.undo_sent()
        if not designer.undone:  # a step made as the first undo lands, on top once it has
            designer.steps.insert(1, other)

    designer.manager.slots['undo()'] = undo
    said = _error(lambda: server.undo_edits(count=2))
    assert said == "Undid 1 of the 2 steps, newest first: '%s'. %s Then %s" % (
        second,
        server.ON_REDO,
        server.STEP_NOT_ON_TOP % ("'%s'" % other, "'%s'" % first),
    )
    assert designer.steps == [other, first]


def test_an_undo_that_cant_be_sent_says_so(steps: list[SessionStep], jobs: list[str]) -> None:
    _remember(steps, [E1])
    designer = Designer([E1])
    designer.manager.slots['undo()'] = lambda: False  # Qt says the slot wasn't called
    said = _error(server.undo_edits)
    assert said == 'Nothing undone: ' + server.STEP_FAILED % ("'%s'" % E1, "Designer's undo() slot wasn't called")
    assert designer.steps == [E1] and len(steps) == 1


def test_without_designers_history_nothing_is_undone_and_it_says_why(steps: list[SessionStep], jobs: list[str]) -> None:
    _remember(steps, [E1])
    designer = Designer([E1])
    designer.buttons.pop()
    assert _error(server.undo_edits) == server.NO_HISTORY % "no Undo and Redo dropdowns of Designer's history found"
    assert designer.steps == [E1] and len(steps) == 1


def test_the_job_undoes_untraced(steps: list[SessionStep], jobs: list[str]) -> None:
    # as the rollback does: no abort of the plugin's (a cancel, a timeout) stops it between an undo sent and its landing
    _remember(steps, [E1])
    designer = Designer([E1])
    traces: list[object] = []

    def undo() -> None:
        traces.append(sys.gettrace())
        designer.undo_sent()

    designer.manager.slots['undo()'] = undo
    server.undo_edits()
    assert traces == [None] and designer.undone == [E1]
