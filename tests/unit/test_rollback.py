"""The rollback of a failed call's undo step (server_tools/core.py, _with_undo; mcp_server/designer_rollback.py): the
tag that makes the step the call's own, the code sent around the call, the rollback against Designer's history faked
(history_fakes.py), the error the tools give for each outcome, and what apply_edits says stays when it isn't rolled
back (designer_helpers/batch.py). That no abort stops a rollback halfway: test_plugin.py, through the plugin."""

import ast
import sys
import types
from collections.abc import Callable, Iterator
from typing import Literal, cast
from unittest import mock

import pytest
from history_fakes import (
    DELETED,
    E0,
    E1,
    E2,
    E3,
    LISTED,
    OTHER,
    READ,
    READ_2,
    Broken,
    Designer,
    GroupEvent,
    QToolButton,
    Recorded,
    full,
    group_events,
    install_sd,
    modules,
)
from test_designer_helpers import _bindings
from test_server import _described

import designer_helpers
from conftest import patch_server, server
from project_constants import Json

LABEL = 'Claude: apply 2 edits #0123abcd'

# --- the code sent around the call, and the tag in its step's name

PROBE = 'rollback_probe'  # the module the stand-in rollback records its calls in
STAND_IN = """\
import sys
import rollback_probe

def roll_back(label, limit_s):
    rollback_probe.calls.append(
        (label, limit_s, rollback_probe.events, sorted(k for k in globals() if not k.startswith('__')), sys.gettrace())
    )
    return 'undone'
"""


class _Probe(types.ModuleType):
    calls: list[tuple[str, float, list[GroupEvent], list[str], object]]
    recorded: Recorded  # the undo transactions opened and committed (history_fakes.group_events reads them)
    history: type  # sd's SDHistoryUtils, faked (history_fakes.install_sd)

    @property
    def events(self) -> list[GroupEvent]:
        return group_events(self.recorded)


@pytest.fixture
def probe(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Probe]:
    """The code _with_undo sends, run here: its undo transaction recorded by a fake of sd's, the rollback a stand-in
    recording what it is called with, when and with what in its scope."""
    probe = _Probe(PROBE)
    probe.calls, probe.recorded = [], []
    probe.history = install_sd(monkeypatch, probe.recorded)
    monkeypatch.setitem(sys.modules, PROBE, probe)
    patch_server(monkeypatch, 'ROLLBACK', STAND_IN)
    yield probe


def _run(code: str) -> None:
    """The code _with_undo sends for `code`, run as the plugin runs a job, with a trace function set as the plugin's
    is (sys.settrace). Its exception is raised."""
    sent = server._with_undo(code, 'Claude: apply 2 edits')
    previous = sys.gettrace()
    sys.settrace(lambda frame, event, arg: None)
    try:
        exec(compile(sent, '<quick edit>', 'exec'), {'__file__': '<quick edit>'})
    finally:
        sys.settrace(previous)


def test_each_call_names_its_step_with_its_label_and_a_tag_of_its_own(probe: _Probe) -> None:
    _run('pass')
    _run('pass')
    first, second = (name for kind, name in probe.events if kind == 'enter')
    for name in (first, second):
        assert name.startswith('Claude: apply 2 edits' + server.TAG_PREFIX), name
        tag = name[len('Claude: apply 2 edits' + server.TAG_PREFIX) :]
        assert len(tag) == server.TAG_LENGTH and set(tag) <= set(server.TAG_ALPHABET), name
    assert first != second


def test_no_step_a_test_remembers_reaches_the_next() -> None:
    # the tests above wrap calls with _with_undo, each adding its step's name to the server's memory (core.py, STEPS);
    # undo_edits' tests read that memory
    assert server.STEPS == []


def test_the_names_the_code_around_a_call_uses_after_it_are_none_the_helpers_bind() -> None:
    # the call's code runs in the script's own globals, and the helpers defined a _commit of their own, so the commit
    # after the code called the helpers' function (seen in Designer, 2026-11-25)
    template, helpers = (
        set().union(*map(_bindings, ast.parse(code).body))
        for code in (server._with_undo('pass', 'x'), designer_helpers.source())
    )
    assert template & helpers == set()


def test_a_tag_has_as_many_names_as_8_hex_digits_at_least() -> None:
    # a call that made no step must not find the call before's step on top by chance
    assert len(set(server.TAG_ALPHABET)) == len(server.TAG_ALPHABET)
    assert len(server.TAG_ALPHABET) ** server.TAG_LENGTH >= 16**8


def test_a_call_that_succeeds_runs_no_rollback(probe: _Probe, capsys: pytest.CaptureFixture[str]) -> None:
    _run('x = 1')
    assert probe.calls == [] and [kind for kind, _ in probe.events] == ['enter', 'commit']
    assert server.ROLLBACK_LINE not in capsys.readouterr().out


def test_a_failed_calls_step_is_rolled_back_once_committed_and_its_error_raised_again(
    probe: _Probe, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(ValueError, match='the call failed'):
        _run("user_name = 1\nraise ValueError('the call failed')")
    [(label, limit_s, events, names, trace)] = probe.calls
    assert events == [('enter', label), ('commit', label)]  # after the step committed: inside it, an undo does nothing
    assert label.startswith('Claude: apply 2 edits' + server.TAG_PREFIX) and limit_s == server.ROLLBACK_LIMIT_S
    assert 'user_name' not in names and 'roll_back' in names  # in a scope of its own
    assert trace is None  # untraced: no abort stops it halfway
    assert capsys.readouterr().out == '\n' + server.ROLLBACK_LINE + 'undone\n'  # its state, on a line of its own


def _refused(*args: object) -> None:
    """sd's open or commit refused, as SDHistoryUtils raises an APIException on an error result."""
    raise Broken('refused')


def test_an_open_sd_refuses_raises_its_error_and_the_code_never_runs(
    probe: _Probe, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md SRV-276: the step is opened through sd's public newTransaction, which raises on an error result
    monkeypatch.setattr(probe.history, 'newTransaction', staticmethod(_refused))
    with pytest.raises(Broken, match='refused'):
        _run("raise ValueError('the code ran')")
    assert probe.events == [] and probe.calls == []


def test_a_commit_sd_refuses_raises_its_error(probe: _Probe, monkeypatch: pytest.MonkeyPatch) -> None:
    # REVIEW.md SRV-276: the step is committed through sd's public commitTransaction, which raises on an error result
    monkeypatch.setattr(probe.history, 'commitTransaction', staticmethod(_refused))
    with pytest.raises(Broken, match='refused'):
        _run('x = 1')


def test_the_code_runs_traced(probe: _Probe) -> None:
    # tracing is off around the open only: the plugin's tracer is back before the code runs, so an abort reaches it
    _run("import sys\nassert sys.gettrace() is not None, 'the code runs untraced'")


@pytest.mark.parametrize('end', ['sys.exit()', 'sys.exit(0)', 'sys.exit(None)'])
def test_a_call_ending_with_sys_exit_of_0_or_none_is_not_rolled_back(
    probe: _Probe, capsys: pytest.CaptureFixture[str], end: str
) -> None:
    # a normal end (the user, 2026-11-24), which the plugin ends normally too (test_plugin.py)
    with pytest.raises(SystemExit):
        _run('import sys\n' + end)
    assert probe.calls == [] and [kind for kind, _ in probe.events] == ['enter', 'commit']
    assert server.ROLLBACK_LINE not in capsys.readouterr().out


@pytest.mark.parametrize('end', ['sys.exit(1)', "sys.exit('no')"])
def test_a_call_exiting_otherwise_is_rolled_back(probe: _Probe, capsys: pytest.CaptureFixture[str], end: str) -> None:
    with pytest.raises(SystemExit):
        _run('import sys\n' + end)
    assert len(probe.calls) == 1
    assert capsys.readouterr().out == '\n' + server.ROLLBACK_LINE + 'undone\n'


def test_the_undo_labels_description_gives_the_tags_form() -> None:
    # the tag's form is the constants alone (the user, 2026-11-24): its description says it from them
    described = _described('execute_designer_code', 'undo_label')
    assert repr(server.TAG_PREFIX) in described and repr(server.TAG_ALPHABET) in described
    assert ' %d ' % server.TAG_LENGTH in described


def test_the_rollbacks_line_starts_a_line_of_its_own_after_output_left_unfinished(
    probe: _Probe, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md SRV-255: printed at once after a script's own `print(..., end='')`, it began mid-line
    with pytest.raises(ValueError):
        _run("print('partial', end='')\nraise ValueError('the call failed')")
    assert capsys.readouterr().out == 'partial\n' + server.ROLLBACK_LINE + 'undone\n'


def test_a_call_rebinding_builtins_is_still_rolled_back_and_its_own_error_raised(
    probe: _Probe, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md SRV-253: the rollback's code looked up exec, compile, print and __import__ in the script's globals, where
    # `from re import *` puts re.compile
    with pytest.raises(ValueError, match='the call failed'):
        _run("from re import *\nprint = exec = __import__ = None\nraise ValueError('the call failed')")
    assert len(probe.calls) == 1
    assert capsys.readouterr().out == '\n' + server.ROLLBACK_LINE + 'undone\n'


def test_a_state_of_several_lines_is_printed_on_one(
    probe: _Probe, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md SRV-258: the server reads the state to the end of its line, and PySide6's errors list signatures below
    said = 'failed: TypeError: called with wrong argument types:\n  invoke(QObject)\n'
    patch_server(monkeypatch, 'ROLLBACK', 'def roll_back(label, limit_s):\n    return %r\n' % said)
    with pytest.raises(ValueError, match='the call failed'):
        _run("raise ValueError('the call failed')")
    expected = 'failed: TypeError: called with wrong argument types: invoke(QObject)'
    assert capsys.readouterr().out == '\n' + server.ROLLBACK_LINE + expected + '\n'


def test_a_rollback_whose_own_module_fails_to_load_leaves_the_calls_own_error(
    probe: _Probe, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md SRV-257: roll_back catches its own errors, but its module's imports and classes run in the template;
    # a Designer update moving a name it imports must not replace the call's error. The error is said on one line
    # (REVIEW.md SRV-258)
    patch_server(monkeypatch, 'ROLLBACK', 'raise ImportError("cannot import name\\n  QMetaMethod")\n')
    with pytest.raises(ValueError, match='the call failed'):
        _run("raise ValueError('the call failed')")
    assert (
        capsys.readouterr().out == '\n' + server.ROLLBACK_LINE + 'failed: ImportError: cannot import name QMetaMethod\n'
    )


# --- the rollback, against Designer's history faked


@pytest.fixture
def rollback(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """The rollback as the server sends it (server.ROLLBACK), on the fake PySide6."""
    for name, module in modules().items():
        monkeypatch.setitem(sys.modules, name, module)
    module = types.ModuleType('rollback_under_test')
    exec(compile(server.ROLLBACK, server.ROLLBACK_FILE, 'exec'), vars(module))
    return module


def test_the_calls_own_step_on_top_is_undone_once(rollback: types.ModuleType) -> None:
    designer = Designer([LABEL, 'Claude: apply 1 edits #ffff0000'])
    assert rollback.roll_back(LABEL, 60) == 'undone'
    assert designer.invoked == ['undo()']
    assert designer.steps == ['Claude: apply 1 edits #ffff0000'] and designer.undone == [LABEL]
    assert designer.clock == 0  # woken by the menus' change, not by the limit (REVIEW.md TST-842)


@pytest.mark.parametrize(
    'steps',
    [
        ['Add Atomic Node', LABEL],  # a step made after the call's
        ['Claude: apply 2 edits #ffffffff'],  # another call's of the same label
        ['Claude: apply 2 edits'],  # the label without the tag
        [],  # no step at all
        ['Claude: code' + '\u200b\u200c\u200d\u2060' * 4],  # the tag's invisible form, said as it is (SRV-272)
    ],
    ids=['a step after it', 'another tag', 'no tag', 'no step', 'invisible tag'],
)
def test_another_step_on_top_is_left_alone(rollback: types.ModuleType, steps: list[str]) -> None:
    designer = Designer(steps)
    assert rollback.roll_back(LABEL, 60) == 'not ours: %s' % ("'%s'" % steps[0] if steps else None)
    assert designer.invoked == [] and designer.steps == steps


def _no_redo_button(designer: Designer) -> None:
    designer.buttons.pop()


def _two_undo_buttons(designer: Designer) -> None:
    designer.buttons.append(designer.buttons[0])


def _another_managers_actions(designer: Designer) -> None:
    designer.manager.name = 'Alg::Gui::SomethingElse'


def _a_button_without_a_menu(designer: Designer) -> None:
    designer.buttons[1] = QToolButton('redo-button', None, designer.manager)


def _no_undo_slot(designer: Designer) -> None:
    del designer.manager.slots['undo()']


@pytest.mark.parametrize(
    'change', [_no_redo_button, _two_undo_buttons, _another_managers_actions, _a_button_without_a_menu, _no_undo_slot]
)
def test_without_one_undo_and_one_redo_dropdown_of_the_history_nothing_is_undone(
    rollback: types.ModuleType, change: Callable[[Designer], None]
) -> None:
    designer = Designer([LABEL])
    change(designer)
    assert rollback.roll_back(LABEL, 60) == "failed: no Undo and Redo dropdowns of Designer's history found"
    assert designer.invoked == [] and designer.steps == [LABEL]


def test_it_waits_through_other_changes_of_the_menus_with_no_user_input_until_the_undo_lands(
    rollback: types.ModuleType,
) -> None:
    designer = Designer([LABEL], stray=2)
    assert rollback.roll_back(LABEL, 60) == 'undone'  # its menus' wrappers still valid: held (history_fakes.py)
    assert designer.invoked == ['undo()']
    assert designer.flags == ['ExcludeUserInputEvents'] * 3
    assert designer.clock == 0  # each pass woken by the menus' change, not by the limit (REVIEW.md TST-842)


def test_an_undo_slot_not_called_is_said_failed_and_nothing_is_waited_for(rollback: types.ModuleType) -> None:
    # REVIEW.md SRV-254: invoke's False, nothing sent, was taken for an undo sent, and the whole limit waited
    designer = Designer([LABEL])
    designer.manager.slots['undo()'] = lambda: False
    assert rollback.roll_back(LABEL, 60) == "failed: Designer's undo() slot wasn't called"
    assert designer.flags == [] and designer.steps == [LABEL]


def test_an_error_once_the_undo_was_sent_is_said_as_not_seen_landing(rollback: types.ModuleType) -> None:
    # REVIEW.md SRV-252: the undo sent may land, so its error isn't a rollback that never ran
    designer = Designer([LABEL])
    designer.after_sent = Broken('lost')
    assert rollback.roll_back(LABEL, 60) == 'not landed: Broken: lost'
    assert designer.invoked == ['undo()']


def test_an_error_clearing_up_after_the_undo_landed_still_says_undone(rollback: types.ModuleType) -> None:
    # REVIEW.md SRV-252: the outcome is known by then
    designer = Designer([LABEL])
    designer.removing_raises = RuntimeError(DELETED)
    assert rollback.roll_back(LABEL, 60) == 'undone'
    assert designer.undone == [LABEL]


def test_an_undo_that_never_lands_is_sent_once_and_said_once_the_limit_is_over(rollback: types.ModuleType) -> None:
    designer = Designer([LABEL], lands=False)
    assert rollback.roll_back(LABEL, 60) == 'not landed: after 60 s'
    assert designer.invoked == ['undo()'] and designer.clock == 60


def test_it_stops_waiting_once_qt_is_quitting(rollback: types.ModuleType) -> None:
    # quitting, the loop returns at once and no timer fires: waiting on would spin, untraced, forever (REVIEW.md HLP-157)
    designer = Designer([LABEL], quitting=True)
    assert rollback.roll_back(LABEL, 60) == 'not landed: Qt is quitting'
    assert designer.invoked == ['undo()'] and len(designer.flags) == 1


@pytest.mark.parametrize('lands', [True, False])
def test_it_leaves_no_event_filter_and_no_timer_running(rollback: types.ModuleType, lands: bool) -> None:
    designer = Designer([LABEL], lands=lands)
    rollback.roll_back(LABEL, 60)
    assert designer.undo_menu.filters == [] and designer.redo_menu.filters == []
    assert not any(timer.active for timer in designer.timers)


@pytest.mark.parametrize('error', [Broken('lost'), RuntimeError(DELETED)])
def test_its_own_error_is_said_never_raised(rollback: types.ModuleType, error: BaseException) -> None:
    designer = Designer([LABEL])
    designer.raises = error
    assert rollback.roll_back(LABEL, 60) == 'failed: %s: %s' % (type(error).__name__, error)


def test_the_rollback_undoes_through_the_shared_function_with_its_one_name(
    rollback: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # one function undoes every list of named steps, the failed call's one name or undo_edits' (the user, 2026-11-25)
    calls: list[tuple[list[str], float]] = []

    def recorded(found: object, names: list[str], limit_s: float) -> tuple[list[str], str]:
        calls.append((names, limit_s))
        return names, 'undone'

    monkeypatch.setitem(vars(rollback), 'undo_steps', recorded)
    designer = Designer([LABEL])
    assert rollback.roll_back(LABEL, 60) == 'undone'
    assert calls == [([LABEL], 60)] and designer.invoked == []


# --- undo_edits' undo of the session's steps (undo_session), against Designer's history faked


def _session(*names: str) -> list[tuple[str, bool, bool]]:
    """The session's steps, oldest first, as the server sends them: each name, whether it is an edit's (READ and
    READ_2 are reads'), and whether undo_edits undid it (none here)."""
    return [(name, name not in (READ, READ_2), False) for name in names]


def test_the_sessions_steps_on_top_are_undone_newest_first(rollback: types.ModuleType) -> None:
    designer = Designer([E3, E2, E1, OTHER])
    assert rollback.undo_session(_session(E1, E2, E3), 3, False, 60) == {
        'listed': 4,
        'planned': [E3, E2, E1],
        'undone': [E3, E2, E1],
        'gone': [],
        'state': 'undone',
    }
    assert designer.steps == [OTHER] and designer.undone == [E1, E2, E3] and designer.invoked == ['undo()'] * 3


def test_another_step_in_the_way_is_named_and_nothing_is_undone_without_include_others(
    rollback: types.ModuleType,
) -> None:
    designer = Designer([E2, OTHER, E1])
    done = rollback.undo_session(_session(E1, E2), 2, False, 60)
    assert done['state'] == 'others' and done['planned'] == [E2, OTHER, E1] and done['undone'] == []
    assert designer.invoked == [] and designer.steps == [E2, OTHER, E1]


def test_with_include_others_the_steps_in_the_way_are_undone_through(rollback: types.ModuleType) -> None:
    designer = Designer([OTHER, E1, 'older'])
    done = rollback.undo_session(_session(E1), 1, True, 60)
    assert done['state'] == 'undone' and done['undone'] == [OTHER, E1]
    assert designer.steps == ['older']


def test_steps_of_one_name_in_the_way_are_each_seen_landing(rollback: types.ModuleType) -> None:
    # Designer names the user's steps by what they did, so two in a row can share a name: the Redo top being that name
    # once the first has landed doesn't show the second's landing
    designer = Designer([OTHER, OTHER, E1, 'older'])
    done = rollback.undo_session(_session(E1), 1, True, 60)
    assert done['state'] == 'undone' and done['undone'] == [OTHER, OTHER, E1]
    assert designer.steps == ['older'] and designer.invoked == ['undo()'] * 3


def test_steps_asked_for_beyond_the_listed_ones_are_refused(rollback: types.ModuleType) -> None:
    # Designer's dropdown lists the newest LISTED steps: E1 below them may still be in the history
    designer = Designer([*full(E2), E1])
    done = rollback.undo_session(_session(E1, E2), 2, True, 60)
    assert rollback.LISTED == LISTED
    assert done['state'] == 'beyond' and done['listed'] == LISTED and done['undone'] == [] and done['gone'] == []
    assert designer.invoked == []


def test_with_the_dropdown_full_the_calls_asked_for_all_listed_are_undone(rollback: types.ModuleType) -> None:
    # REVIEW.md SRV-266: kills taking every full list as one with older calls (`elif full:` as beyond)
    designer = Designer(full(E2, E1))
    done = rollback.undo_session(_session(E1, E2), 2, False, 60)
    assert done['state'] == 'undone' and done['undone'] == [E2, E1] and done['gone'] == []
    assert designer.steps == full(E2, E1)[2:]


def test_with_the_dropdown_full_a_count_above_the_sessions_edits_undoes_them_all(rollback: types.ModuleType) -> None:
    # REVIEW.md SRV-266: kills refusing a count above the session's edits when all of them are listed
    designer = Designer(full(E2, E1))
    done = rollback.undo_session(_session(E1, E2), 5, False, 60)
    assert done['state'] == 'undone' and done['undone'] == [E2, E1]
    assert designer.invoked == ['undo()'] * 2


def test_with_the_dropdown_full_a_call_with_no_step_newer_than_one_listed_is_gone(rollback: types.ModuleType) -> None:
    # REVIEW.md SRV-266: E2 failed and was rolled back. Newer than E1, which is listed, it would be listed too: it is
    # gone, not maybe older than the steps listed
    designer = Designer(full(E3, E1))
    done = rollback.undo_session(_session(E1, E2, E3), 3, False, 60)
    assert done['state'] == 'undone' and done['undone'] == [E3, E1] and done['gone'] == [E2]
    assert designer.steps == full(E3, E1)[2:]


def test_with_the_dropdown_full_a_read_older_than_those_listed_doesnt_refuse_the_count(
    rollback: types.ModuleType,
) -> None:
    # REVIEW.md TST-879: a read below the list holds no edit that could be asked for
    Designer(full(E2, E1))
    done = rollback.undo_session(_session(READ, E1, E2), 3, False, 60)
    assert done['state'] == 'undone' and done['undone'] == [E2, E1]


def test_with_the_dropdown_full_a_call_older_than_those_listed_is_kept(rollback: types.ModuleType) -> None:
    # E0, not listed, is older than E1, the session's oldest listed: it may be beyond the dropdown, so it isn't dropped
    Designer(full(E1))
    done = rollback.undo_session(_session(E0, E1), 1, False, 60)
    assert done['state'] == 'undone' and done['undone'] == [E1] and done['gone'] == []


def test_a_step_not_landing_midway_stops_and_says_what_was_undone(rollback: types.ModuleType) -> None:
    designer = Designer([E3, E2, E1], landing=1)
    done = rollback.undo_session(_session(E1, E2, E3), 3, False, 60)
    assert done['undone'] == [E3] and done['state'] == 'not landed: after 60 s'
    assert designer.invoked == ['undo()'] * 2  # the third was never sent


def test_a_count_above_the_sessions_steps_listed_undoes_those_listed_and_says_which_are_gone(
    rollback: types.ModuleType,
) -> None:
    designer = Designer([E2, E1, OTHER])
    assert rollback.undo_session(_session(E0, E1, E2), 5, False, 60) == {
        'listed': 3,
        'planned': [E2, E1],
        'undone': [E2, E1],
        'gone': [E0],  # not listed, while the dropdown lists fewer than its most: undone, rolled back or never made
        'state': 'undone',
    }
    assert designer.steps == [OTHER]


def test_a_reads_step_is_undone_along_the_way_and_not_counted(rollback: types.ModuleType) -> None:
    # a read's step (a temporary node added and removed) changes nothing: the agent's edit below it is the one asked for
    designer = Designer([READ, E2, READ_2, E1])
    done = rollback.undo_session(_session(E1, READ_2, E2, READ), 1, False, 60)
    assert done['state'] == 'undone' and done['planned'] == done['undone'] == [READ, E2]
    assert designer.steps == [READ_2, E1]


def test_with_none_of_the_sessions_edits_listed_nothing_is_undone(rollback: types.ModuleType) -> None:
    designer = Designer([READ, OTHER])
    done = rollback.undo_session(_session(E1, READ), 1, True, 60)
    assert done['state'] == 'none' and done['planned'] == [] and done['gone'] == [E1]
    assert designer.invoked == []


@pytest.mark.parametrize(
    ('change', 'state'),
    [
        (_no_redo_button, "failed: no Undo and Redo dropdowns of Designer's history found"),
        (lambda designer: setattr(designer, 'raises', Broken('lost')), 'failed: Broken: lost'),
    ],
    ids=['no history', 'its own error'],
)
def test_without_the_history_nothing_is_undone_and_its_error_is_said(
    rollback: types.ModuleType, change: Callable[[Designer], None], state: str
) -> None:
    designer = Designer([E1])
    change(designer)
    done = rollback.undo_session(_session(E1), 1, False, 60)
    assert done['state'] == state and done['undone'] == [] and designer.invoked == []


# --- the error the tools give

ERROR = 'Traceback (most recent call last):\n  File "<quick edit>", line 4, in <module>\nRuntimeError: op 1 (connect) failed: no'
FAILED = 'RuntimeError: op 1 (connect) failed: no'
TAKE_BACK = '; undo_edits takes back the whole batch'  # how the agent undoes what stays (GUIDE.md, the rules)
KEPT = "ops 0-0 were applied (added: 7 (ref 'a'))" + TAKE_BACK


# each outcome of a failed call's rollback, as _note says it
Says = Literal['undone', 'not landed', 'not landed, its error', 'kept', 'kept, not run', 'kept, failed', 'failed']


def _note(says: Says) -> str:
    """The sentences a failed call's error ends with, for each outcome of its rollback (core.py, _failure)."""
    notes: dict[Says, str] = {
        'undone': server.UNDONE,
        'not landed': server.NOT_LANDED % 'after 60 s',
        'not landed, its error': server.NOT_LANDED % 'Broken: lost',
        'kept': KEPT + '.',
        'kept, not run': KEPT + '. ' + server.NOT_RUN % "no Undo and Redo dropdowns of Designer's history found",
        'kept, failed': KEPT + '. ' + server.NOT_RUN % 'RuntimeError: lost',
        'failed': server.NOT_RUN % 'RuntimeError: lost',
    }
    return notes[says]


@pytest.mark.parametrize(
    ('state', 'kept', 'says'),
    [
        ('undone', True, 'undone'),
        ('undone', False, 'undone'),
        ('not landed: after 60 s', True, 'not landed'),
        ('not landed: Broken: lost', True, 'not landed, its error'),  # REVIEW.md SRV-252
        ("not ours: 'Add Atomic Node'", True, 'kept'),
        ("not ours: 'Add Atomic Node'", False, None),
        ("failed: no Undo and Redo dropdowns of Designer's history found", True, 'kept, not run'),  # why (SRV-252)
        ('failed: RuntimeError: lost', True, 'kept, failed'),
        ('failed: RuntimeError: lost', False, 'failed'),
        (None, False, None),  # no rollback: the call's code never got so far
    ],
)
def test_a_failed_calls_error_says_what_its_rollback_did(
    monkeypatch: pytest.MonkeyPatch, state: str | None, kept: bool, says: Says | None
) -> None:
    last = FAILED + ('. ' + _note(says) if says else '')
    output = 'printed\n' + (server.KEPT_LINE + KEPT + '\n' if kept else '')
    output += '\n' + server.ROLLBACK_LINE + state + '\n' if state else ''  # as the code _with_undo sends prints it
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': False, 'output': output, 'error': ERROR})
    text = server._bridge('code')
    assert text.splitlines()[-1] == last
    assert text.startswith('printed\n\n--- ERROR ---\nTraceback')  # the two lines taken out of the output
    with pytest.raises(server.ToolError) as raised:
        server._checked(text)
    assert str(raised.value) == last


@pytest.mark.parametrize(
    ('output', 'left'),
    [
        ('partial\n' + server.ROLLBACK_LINE + 'undone\n', 'partial'),  # a line left unfinished (REVIEW.md SRV-255)
        (
            '\n' + server.ROLLBACK_LINE + "not ours: 'x'\nmore\n\n" + server.ROLLBACK_LINE + 'undone\n',
            "\nROLLBACK=not ours: 'x'\nmore\n",  # both after a newline: the last one is read (REVIEW.md TST-851)
        ),
    ],
    ids=['after an unfinished line', 'the last one'],
)
def test_the_rollbacks_line_is_the_last_one_printed_after_a_newline(output: str, left: str) -> None:
    taken, error = server._failure(output, FAILED)
    assert taken == left and error == FAILED + '. ' + server.UNDONE


def test_a_call_that_succeeds_keeps_its_output_whole(monkeypatch: pytest.MonkeyPatch) -> None:
    output = 'applied 1 op(s)\n'
    patch_server(monkeypatch, '_send', lambda request, wait, port=None: {'ok': True, 'output': output, 'error': ''})
    assert server._bridge('code') == output


# --- what apply_edits says stays when it isn't rolled back


@pytest.mark.parametrize(
    ('ops', 'counts', 'kept'),
    [
        (
            [{'op': 'add', 'definition': 'blur', 'ref': 'a'}, {'op': 'connect', 'from': 'a', 'to': '1', 'input': 'x'}],
            [0, 1, 1],
            "ops 0-0 were applied (added: 11 (ref 'a'))",
        ),
        (  # a node added without a ref is named too (REVIEW.md HLP-49)
            [{'op': 'add', 'definition': 'blur'}, {'op': 'set', 'node': '1', 'params': {'nope': 1}}],
            [0, 1, 1],
            'ops 0-0 were applied (added: 11)',
        ),
        (  # a node added then deleted isn't listed (REVIEW.md HLP-52)
            [
                {'op': 'add', 'definition': 'blur', 'ref': 'gone'},
                {'op': 'delete', 'node': 'gone'},
                {'op': 'set', 'node': '1', 'params': {'nope': 1}},
            ],
            [0, 1, 0, 0],
            'ops 0-1 were applied',
        ),
        (  # an add failing after it made its node (REVIEW.md HLP-5)
            [{'op': 'add', 'definition': 'levels'}],
            [0, 1],
            'its node was added before the failure',
        ),
        (
            [{'op': 'add', 'definition': 'blur', 'ref': 'a'}, {'op': 'add', 'definition': 'levels'}],
            [0, 1, 2],
            "ops 0-0 were applied (added: 11 (ref 'a')), its node was added before the failure",
        ),
        (  # the first op fails: nothing to revert, so no undo_edits, which would undo the step before
            [{'op': 'connect', 'from': '1', 'to': '1', 'input': 'x'}],
            [1, 1],
            None,
        ),
    ],
    ids=['after an add', 'a node with no ref', 'a node deleted', 'an add', 'an add after an add', 'the first op'],
)
def test_what_a_failed_batch_applied_is_said_apart_from_its_error(
    faked_helpers: types.ModuleType,
    capsys: pytest.CaptureFixture[str],
    ops: list[dict[str, Json]],
    counts: list[int],
    kept: str | None,
) -> None:
    # `counts`: the graph's number of nodes as each op starts, then as the last one fails; adding a levels node fails
    g = mock.MagicMock()
    g.getNodes.return_value.getSize.side_effect = counts
    added = iter(['11', '12'])

    def fail(*args: object) -> str:
        raise RuntimeError("input 'nope' not on node 1")

    vars(faked_helpers).update(
        _graph_to_edit=lambda identifier: g,
        _check_batch=lambda graph, given: None,
        add_node=lambda graph, definition, *rest: fail() if definition == 'levels' else next(added),
        delete_nodes=lambda *args: None,
        connect=fail,
        set_params=fail,
    )
    with pytest.raises(RuntimeError) as raised:
        faked_helpers.apply_edits('G', ops)
    assert str(raised.value) == "op %d (%s) failed: input 'nope' not on node 1" % (
        len(ops) - 1,
        cast(str, ops[-1]['op']),
    )
    printed = [line for line in capsys.readouterr().out.splitlines() if line.startswith(server.KEPT_LINE)]
    assert printed == ([server.KEPT_LINE + kept + TAKE_BACK] if kept else [])


def test_an_add_whose_node_cant_be_removed_again_says_so_apart_from_its_error(
    faked_helpers: types.ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md HLP-256, its pattern in add_node: what a failure leaves is said on a KEPT line, which the server shows
    # only when the call's rollback didn't take it back
    g = mock.MagicMock()
    g.deleteNode.side_effect = RuntimeError('locked')
    node = mock.MagicMock()
    node.getIdentifier.return_value = '11'

    def bad_value(*args: object) -> None:
        raise RuntimeError('levelinlow expects 4 values')

    vars(faked_helpers).update(
        _graph_to_edit=lambda identifier: g,
        _nodes=lambda graph: [],
        _resolve_definition=lambda graph, definition: node,
        _place=lambda n, position, existing: (0, 0),
        node_kind=lambda n: 'levels',
        set_params=bad_value,
    )
    with pytest.raises(RuntimeError) as raised:
        faked_helpers.add_node('G', 'levels', None, {'levelinlow': 1})
    assert str(raised.value) == 'levelinlow expects 4 values'
    printed = [line for line in capsys.readouterr().out.splitlines() if line.startswith(server.KEPT_LINE)]
    assert printed == [server.KEPT_LINE + 'node 11 could not be removed again (locked): delete it by hand']
