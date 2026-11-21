"""The undo category's checks (tests/test_all_tools/undo/checks.py) and how they send an Undo or a Redo and read it back
(undo/edit_menu.py), on a fake Designer: each read of the graph answers from a script, the clock moves only as the
checks wait, and each call is recorded by what it does."""

import asyncio
import re
import sys
import time
import typing
from collections.abc import Callable, Sequence
from types import ModuleType, SimpleNamespace
from typing import Literal

import pytest
from selftest_fakes import FakeCall, code_of, fresh, tool_result

from project_constants import ToolArgs

SCHEDULED = 'AT_SCHEDULE app=ApplicationInactive\nSCHEDULED'
FIRED = "FIRED app=ApplicationInactive menus: QStackedWidget: 'Undo' enabled=True"
NOT_FIRED = 'FIRED None'
CHANGED = "1 output @(300,0) identifier='undo_me' label='Undo' usage=roughness"
BACK = "1 output @(300,0) identifier='height' usage=none"
# the app in front as the Undo was scheduled and as the check read its result, read by the self-test (REVIEW.md TST-650)
FRONT = (
    'the app in front, as macOS said it: Terminal (321) as the Undo was scheduled, Terminal (321) as the check read it; '
    "Designer's process 99"
)
SET = "set: one Undo puts an output's fields back"
# a graph as describe_graph reads it: the number of sends of the Undo and of the Redo so far, the reads since the last
Graph = Callable[[int, int, int], str]


@pytest.fixture
def undo(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """undo/checks.py, imported afresh, with a clock that moves only as asyncio.sleep is asked to wait."""
    now = [100.0]

    async def wait(seconds: float) -> None:
        now[0] = round(now[0] + seconds, 6)  # no float error piling up over a limit's reads

    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    # setitem: PyCharm can't resolve 'sleep' through asyncio's star re-export of asyncio.tasks (`.claude/rules/unit-tests.md`)
    monkeypatch.setitem(vars(asyncio), 'sleep', wait)
    checks = fresh('undo.checks')
    menu = sys.modules['test_all_tools.undo.edit_menu']
    monkeypatch.setitem(vars(menu), 'READS_THE_FRONT', True)  # as on macOS, its lsappinfo and ps faked
    monkeypatch.setitem(vars(menu), 'active_app', lambda: 321)
    names = {321: 'Terminal', 400: '/System/Library/CoreServices/Finder.app/Contents/MacOS/Finder'}  # as ps names them
    monkeypatch.setitem(vars(menu), 'process_name', lambda pid: names.get(pid, 'gone'))
    monkeypatch.setitem(vars(menu), 'agents_designers', lambda: {menu.common.PORT: 99})
    return checks


def _graph(*nodes: str) -> str:
    """describe_graph's text of the self-test graph holding these node lines."""
    return '\n'.join(['graph mcp_selftest: %d nodes' % len(nodes), *nodes])


def _what(name: str, args: ToolArgs | None) -> str:
    """What a tool call of the checks does: the tool, or for code the snippet it runs."""
    if name == 'run_designer_script':
        return 'as prepared' if str((args or {}).get('path', '')).endswith('as_prepared.py') else name
    if name != 'execute_designer_code':
        return name
    code = code_of(args)
    if 'getNodeFromId' in code:
        return 'exists'
    for what, mark in (('Undo', "a.text()=='Undo'"), ('Redo', "a.text()=='Redo'"), ('fired', '_selftest_undo_fired')):
        if mark in code:
            return what
    if 'processEvents' in code:
        return 'processEvents'
    return 'two nodes' if 'IDS=' in code else 'code'


def _designer(
    graph: Graph, fired: Sequence[str] = (FIRED,), undo: str | Sequence[str] = SCHEDULED
) -> tuple[FakeCall, list[str]]:
    """A fake tool call: each describe_graph answers `graph` (an answer starting 'Error' is an error), each Undo sent
    answers `undo`, or the next of them (the last again once they run out), each read of the action's state the next of
    `fired` (the same way); and the calls it got."""
    calls: list[str] = []
    answers = {'apply_edits': 'added 7', 'Redo': SCHEDULED, 'two nodes': 'IDS=7,8'}
    fires = list(fired)
    undos = [undo] if isinstance(undo, str) else list(undo)
    since = [0]  # the graph's reads since the last call of another kind, a read of the action's state not counted

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        what = _what(name, args)
        calls.append(what)
        if what == 'describe_graph':
            read = graph(calls.count('Undo'), calls.count('Redo'), since[0])
            since[0] += 1
            return tool_result(read, error=read.startswith('Error'))
        if what == 'fired':
            read = fires.pop(0) if len(fires) > 1 else fires[0]
            return tool_result(read, error=read.startswith('Error'))
        since[0] = 0
        if what == 'Undo':
            return tool_result(undos.pop(0) if len(undos) > 1 else undos[0])
        return tool_result(answers.get(what, ''))

    return c, calls


def _ctx(c: FakeCall) -> SimpleNamespace:
    return SimpleNamespace(c=c, G={'graph': 'mcp_selftest'}, out='1')


def _line(out: str, name: str) -> str:
    """The line common.check printed for check `name`; '' if none."""
    return next((line for line in out.splitlines() if ' %s | ' % name in line), '')


def _said(out: str) -> list[str]:
    """The lines a failed check printed under its verdict."""
    return [line.strip() for line in out.splitlines() if line.startswith('      ')]


def _back_after(undos: int, reads: int = 0) -> Graph:
    """The output's fields back once `undos` Undos were sent, from the `reads`th read after the last: as set before."""
    return lambda u, r, since: BACK if u > undos or (u == undos and since >= reads) else CHANGED


def _between(calls: list[str], first: str, last: str) -> list[str]:
    """The calls after the first `first` and before the last `last`."""
    start = calls.index(first) + 1
    return calls[start : len(calls) - calls[::-1].index(last) - 1]


# --- the set of an output's fields


def test_an_undo_the_first_read_shows_passes_sent_once(undo: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    # ROADMAP item 112: no code job between the Undo and its read (the set check ran a processEvents job there, the add
    # check read with NODE_EXISTS): in both failures seen, code ran around the trigger (undo/edit_menu.py)
    c, calls = _designer(_back_after(1))
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, SET).startswith('PASS') and 'sent once' in _line(out, SET) and _said(out) == []
    assert calls == ['apply_edits', 'describe_graph', 'Undo', 'describe_graph', 'as prepared']


def test_an_undo_shown_late_passes_and_only_describe_graph_reads_meanwhile(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    c, calls = _designer(_back_after(1, reads=30))
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, SET).startswith('PASS') and 'sent once' in _line(out, SET)
    assert re.search(r'3\.0 s after', _line(out, SET)), _line(out, SET)
    assert _between(calls, 'Undo', 'as prepared') == ['describe_graph'] * 31


def test_an_action_that_never_fired_is_sent_again_and_only_then(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # the read of the action's state disarms one not fired yet (common.UNDO_FIRED), so it can't undo a second time
    c, calls = _designer(_back_after(2), fired=[NOT_FIRED])
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, SET).startswith('PASS') and 'sent 2 times' in _line(out, SET), _line(out, SET)
    first = _between(calls, 'Undo', 'Undo')
    assert first[-1] == 'fired' and set(first[:-1]) == {'describe_graph'}
    assert len(first) - 1 == 101, 'read every 0.1 s, from the send to 10 s after it, the limit'
    assert calls[-2:] == ['describe_graph', 'as prepared'] and calls.count('Undo') == 2 and 'Redo' not in calls


def test_an_action_that_fired_and_never_showed_fails_naming_it_then_is_redone(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    c, calls = _designer(lambda u, r, since: CHANGED)
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, SET).startswith('FAIL')
    assert "the Edit menu's action fired; describe_graph didn't show the Undo within 10 s" in _line(out, SET)
    assert _said(out) == [
        'the Undo, as it was last scheduled: app=ApplicationInactive',
        FRONT,
        "the Edit menu's action as it fired: " + FIRED.removeprefix('FIRED '),
        'the graph as last read: ' + CHANGED,
        # the Redo putting it back, read as the Undo was: the graph never changes (REVIEW.md TST-693)
        "the Redo putting it back: the Edit menu's action fired; describe_graph didn't show the Redo within 10 s",
    ]
    assert calls.count('Undo') == 1, 'never sent again: it fired'
    redo = calls.index('Redo')
    assert calls[redo - 1] == 'fired' and calls[-2:] == ['fired', 'as prepared'], (
        'the Redo puts back the step it undid, after the diagnostic, and is read'
    )


def test_an_action_that_never_fires_fails_once_sent_at_most_times(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    c, calls = _designer(lambda u, r, since: CHANGED, fired=[NOT_FIRED])
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    menu = sys.modules['test_all_tools.undo.edit_menu']
    assert _line(out, SET).startswith('FAIL')
    assert "the Edit menu's action never fired, sent %d times" % menu.SENDS in _line(out, SET)
    assert re.fullmatch(
        r"the Edit menu's action hadn't fired when read, 10\.\d s after it was scheduled", _said(out)[2]
    )
    assert calls.count('Undo') == calls.count('fired') == menu.SENDS
    assert 'Redo' not in calls, 'nothing was undone'


@pytest.mark.parametrize('refused', ['NOT_FOCUSED current=other_graph', 'NO_ACTION app=ApplicationActive menus: none'])
def test_an_undo_not_scheduled_fails_with_the_state_seen(
    undo: ModuleType, capsys: pytest.CaptureFixture[str], refused: str
) -> None:
    # the branch's rule 8: a skip it can't avoid fails, with the state it saw
    c, calls = _designer(_back_after(1), undo=refused)
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, SET).startswith('FAIL') and 'not scheduled: ' + refused in _line(out, SET), _line(out, SET)
    assert 'SKIP' not in out and calls == ['apply_edits', 'describe_graph', 'Undo', 'as prepared']


def test_a_set_not_applied_fails_the_undo_check_too_and_sends_none(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    c, calls = _designer(lambda u, r, since: BACK)
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, "set: an output's fields, before the Undo").startswith('FAIL')
    assert _line(out, SET).startswith('FAIL') and "the set wasn't applied" in _line(out, SET)
    assert 'Undo' not in calls


def test_a_failure_after_a_resend_says_how_many_sends(undo: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    # REVIEW.md TST-662: send 1 never fired, send 2 fired and never showed; the FAIL read as one send, and the evidence
    # that Designer's zero timer didn't run for 10 s was lost
    c, calls = _designer(lambda u, r, since: CHANGED, fired=[NOT_FIRED, FIRED])
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    line = _line(capsys.readouterr().out, SET)
    assert calls.count('Undo') == 2 and line.startswith('FAIL') and 'sent 2 times' in line, line


def test_a_resend_that_failed_says_why_and_how_many_sends(undo: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    # send 1 never fired; send 2's read failed: the failure says it, after the count of sends, not "never fired"
    c, calls = _designer(lambda u, r, since: 'Error: the graph is gone' if u == 2 else CHANGED, fired=[NOT_FIRED])
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    line = _line(out, SET)
    assert calls.count('Undo') == 2 and line.startswith('FAIL'), line
    assert 'sent 2 times, the action before never fired; a read failed: Error: the graph is gone' in line, line
    # REVIEW.md TST-667: send 1's "hadn't fired when read" was printed among send 2's lines, a read send 2 never made.
    # TST-691: send 2's own read of the state, after its failed read, is said
    assert _said(out) == [
        'the Undo, as it was last scheduled: app=ApplicationInactive',
        FRONT,
        "the Edit menu's action hadn't fired when read, 0.0 s after it was scheduled",  # at the failed read
        'the graph as last read: ' + ' / '.join(CHANGED.splitlines()),
    ]


def test_a_resend_refused_says_the_state_designer_gave(undo: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    # REVIEW.md TST-668: every Undo was answered alike, so a refused resend was never tested
    c, calls = _designer(lambda u, r, since: CHANGED, fired=[NOT_FIRED], undo=[SCHEDULED, 'NOT_FOCUSED current=x'])
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    line = _line(capsys.readouterr().out, SET)
    assert calls.count('Undo') == 2 and line.startswith('FAIL'), line
    assert 'sent 2 times, the action before never fired; not scheduled: NOT_FOCUSED current=x' in line, line


def test_which_is_undo_or_redo(undo: ModuleType) -> None:
    # REVIEW.md TST-663: a misspelt `which` passed mypy, and gave NO_ACTION at run time
    menu = sys.modules['test_all_tools.undo.edit_menu']
    wanted = Literal['Undo', 'Redo']
    assert typing.get_type_hints(menu.Sent)['which'] == wanted
    assert typing.get_type_hints(menu.send)['which'] == wanted


# --- the add of a node, and a code run adding two (REVIEW.md TST-641: the same reads for each Undo check)


@pytest.mark.parametrize(
    'step, name, graph',
    [
        ('check_one_undo_removes_an_added_node', 'add: one Undo removes the added node', ['7 blur @(0,400)']),
        (
            'check_one_undo_reverts_a_whole_code_run',
            'one Undo reverts the whole run',
            ['7 blur @(0,500)', '8 blur @(200,500)'],
        ),
    ],
    ids=['add', 'code run'],
)
def test_the_add_and_code_run_checks_say_why_an_undo_that_fired_never_showed(
    undo: ModuleType, capsys: pytest.CaptureFixture[str], step: str, name: str, graph: list[str]
) -> None:
    # REVIEW.md TST-661: TST-641's tests went with TST-655's rewrite; only the set check's diagnostics were asserted
    described = _graph(*graph)
    c, calls = _designer(lambda u, r, since: described)
    asyncio.run(getattr(undo, step)(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, name).startswith('FAIL')
    assert _said(out) == [
        'the Undo, as it was last scheduled: app=ApplicationInactive',
        FRONT,
        "the Edit menu's action as it fired: " + FIRED.removeprefix('FIRED '),
        'the graph as last read: ' + ' / '.join(described.splitlines()),
        # the Redo putting it back, read as the Undo was: the graph never changes (REVIEW.md TST-693)
        "the Redo putting it back: the Edit menu's action fired; describe_graph didn't show the Redo within 10 s",
    ]
    assert calls.count('Redo') == 1, 'the step it hit put back'


def test_the_add_check_reads_its_undo_and_redo_with_describe_graph(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    present = _graph('7 blur @(0,400)')
    c, calls = _designer(lambda u, r, since: _graph() if u > r else present)
    asyncio.run(undo.check_one_undo_removes_an_added_node(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, 'add: one Undo removes the added node').startswith('PASS')
    assert _line(out, 'add: Redo restores it').startswith('PASS')
    assert calls == ['apply_edits', 'Undo', 'describe_graph', 'Redo', 'describe_graph', 'apply_edits']


def test_the_code_run_check_reads_its_undo_and_redo_with_describe_graph(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    both = _graph('7 blur @(0,500)', '8 blur @(200,500)')
    # the Undo takes one node away at the first read, both at the second
    c, calls = _designer(
        lambda u, r, since: both if u == r else _graph('8 blur @(200,500)') if since == 0 and r == 0 else _graph()
    )
    asyncio.run(undo.check_one_undo_reverts_a_whole_code_run(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, 'one Undo reverts the whole run').startswith('PASS')
    assert _line(out, 'one Redo restores it').startswith('PASS')
    assert calls == [
        'two nodes',
        'Undo',
        'describe_graph',
        'describe_graph',
        'Redo',
        'describe_graph',
        'apply_edits',
    ]


@pytest.mark.parametrize('redo', [False, True], ids=['the Undo', 'the Redo'])
@pytest.mark.parametrize(
    'step, name',
    [
        ('check_one_undo_removes_an_added_node', ('add: one Undo removes the added node', 'add: Redo restores it')),
        ('check_one_undo_reverts_a_whole_code_run', ('one Undo reverts the whole run', 'one Redo restores it')),
    ],
    ids=['add', 'code run'],
)
def test_a_read_that_failed_fails_the_check_naming_it(
    undo: ModuleType, capsys: pytest.CaptureFixture[str], step: str, name: tuple[str, str], redo: bool
) -> None:
    # REVIEW.md TST-655: an error reply has no node in it, and two failed reads passed "one Undo reverts the whole run";
    # TST-652: read as every node gone, one said the Undo landed
    error = 'Error executing tool describe_graph: bridge busy'
    gone = _graph()
    c, calls = _designer(lambda u, r, since: error if r == int(redo) else gone)
    asyncio.run(getattr(undo, step)(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, name[int(redo)]).startswith('FAIL') and 'a read failed: ' + error in _line(out, name[int(redo)])
    assert calls.count('describe_graph') == 1 + int(redo), 'no read after the failed one'
    if not redo:
        assert _line(out, name[1]) == '' and 'Redo' not in calls


def test_a_read_of_the_action_that_failed_fails_the_check_naming_it(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    error = 'Error executing tool execute_designer_code: bridge busy'
    c, calls = _designer(lambda u, r, since: CHANGED, fired=[error])
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, SET).startswith('FAIL') and 'a read failed: ' + error in _line(out, SET)
    assert calls.count('Undo') == 1 and 'Redo' not in calls, (
        'neither sent again nor redone: whether it fired is unknown'
    )


@pytest.mark.parametrize(
    'step',
    [
        'check_one_undo_removes_an_added_node',
        'check_one_undo_puts_an_outputs_fields_back',
        'check_one_undo_reverts_a_whole_code_run',
    ],
)
def test_no_check_runs_qts_events_or_reads_a_node_by_code(undo: ModuleType, step: str) -> None:
    c, calls = _designer(_back_after(1))
    asyncio.run(getattr(undo, step)(_ctx(c)))
    assert 'processEvents' not in calls and 'exists' not in calls, calls


# --- what the diagnostic prints when a state wasn't said


def test_a_state_not_said_is_said_so(
    undo: ModuleType, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    menu = sys.modules['test_all_tools.undo.edit_menu']
    monkeypatch.setitem(vars(menu), 'READS_THE_FRONT', False)  # off macOS
    c, _ = _designer(lambda u, r, since: 'x', fired=['no such line'], undo='SCHEDULED')
    sent = asyncio.run(menu.send(c, {'graph': 'g'}, 'Undo', lambda described: False))
    # neither said to have fired nor not: it isn't sent again, nor redone after (test_a_read_of_the_action_that_failed_...)
    assert (
        sent.detail()
        == "describe_graph didn't show the Undo within 10 s; whether the Edit menu's action fired wasn't said"
    )
    sent.say()
    assert _said(capsys.readouterr().out) == [
        'the Undo, as it was last scheduled: not said',
        'the app in front, as macOS said it: not read as the Undo was scheduled, not read as the check read it; '
        "Designer's process 99",
        "the Edit menu's action as it fired: not read",
        'the graph as last read: x',
    ]


@pytest.mark.parametrize(
    'active, said',
    [(321, 'Terminal (321)'), (400, 'Finder (400)'), (500, 'gone (500)'), (None, 'unread')],
    ids=['an app', 'its executable named, not its path', 'one that has quit', "lsappinfo couldn't tell"],
)
def test_the_app_in_front_is_read_by_the_self_test(
    undo: ModuleType, monkeypatch: pytest.MonkeyPatch, active: int | None, said: str
) -> None:
    # REVIEW.md TST-650: read on a thread of the self-test's own, so nothing runs in Designer around the Undo and no
    # read delays the check's next call
    menu = sys.modules['test_all_tools.undo.edit_menu']
    monkeypatch.setitem(vars(menu), 'active_app', lambda: active)
    assert menu.FrontRead().said() == said


NO_ACTION = (  # as UNDO_REDO prints it (common.py), about 115 characters
    "NO_ACTION app=ApplicationActive active=MainWindow focus=MainWindowClassWindow menus: QStackedWidget 'Undo' "
    'enabled=False'
)


def test_a_refused_resend_prints_its_state_whole(undo: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    # REVIEW.md TST-685: the FAIL line keeps 150 characters, and cut a resent NO_ACTION right before "'Undo'
    # enabled=False", the fact that explains it; say() printed nothing for a refused send
    c, _ = _designer(lambda u, r, since: CHANGED, fired=[NOT_FIRED], undo=[SCHEDULED, NO_ACTION])
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    assert 'enabled=False' not in _line(out, SET), _line(out, SET)  # cut there, as the check keeps 150
    assert any(line.endswith(NO_ACTION) for line in _said(out)), _said(out)


def test_a_failed_read_of_the_graph_disarms_the_action_before_returning(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-687: send returned at a failed describe_graph read with the Edit menu's action maybe still armed,
    # to fire in a later job on the document then in focus, maybe the user's (the one run in their Designer)
    c, calls = _designer(lambda u, r, since: 'Error: the graph is gone' if u else CHANGED, fired=[NOT_FIRED])
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    # the read of the action's state after the failed read, which disarms one not fired yet
    assert calls[calls.index('Undo') :] == ['Undo', 'describe_graph', 'fired', 'as prepared'], calls
    assert 'may still fire' not in capsys.readouterr().out


@pytest.mark.parametrize('graph_read', ['failed', 'never showed it'])
def test_an_action_whose_state_couldnt_be_read_is_said_to_maybe_still_fire(
    undo: ModuleType, capsys: pytest.CaptureFixture[str], graph_read: str
) -> None:
    # REVIEW.md TST-687: a failed read of the action's state leaves it armed
    failed = 'Error: the graph is gone'
    c, _ = _designer(
        lambda u, r, since: failed if u and graph_read == 'failed' else CHANGED, fired=['Error: the bridge closed']
    )
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    assert "the Edit menu's action may still fire: its state wasn't read: Error: the bridge closed" in _said(out)


# the self-test graph holding what each check's Undo takes away: none of them ever shows
NONE_SHOWS = _graph('7 blur @(0,400)', '8 blur @(200,500)', CHANGED)


@pytest.mark.parametrize(
    'end, said',
    [
        (
            'ARMED True\nFIRED None',
            "the undo checks' end: the Edit menu's action armed last hadn't fired; reading its state disarmed it",
        ),
        (
            'Error: the bridge closed',
            "the undo checks' end: the Edit menu's action may still fire: its state wasn't read: "
            'Error: the bridge closed',
        ),
        ('ARMED True\n' + FIRED, None),
        ('ARMED False\nFIRED None', None),
    ],
    ids=['armed, not fired', 'the read failed', 'fired', 'none armed'],
)
def test_the_undo_checks_end_reading_the_action_left_armed(
    undo: ModuleType, capsys: pytest.CaptureFixture[str], end: str, said: str | None
) -> None:
    # REVIEW.md TST-690: put_back's Redo after the last check's Undo was never read, so never disarmed: fired later, it
    # would land on the document in focus then
    # each check's Undo, then the Redo putting it back, read as never shown (REVIEW.md TST-693)
    c, calls = _designer(lambda u, r, since: NONE_SHOWS, fired=[FIRED] * 6 + [end])
    asyncio.run(undo.run(_ctx(c)))
    out = _said(capsys.readouterr().out)
    assert calls.count('Redo') == 3 and calls[-3:] == ['fired', 'apply_edits', 'fired'], calls  # after the clean-up
    ended = [line for line in out if line.startswith("the undo checks' end")]
    assert ended == ([said] if said else []), out


@pytest.mark.parametrize(
    'state, said',
    [
        (FIRED, "the Edit menu's action as it fired: " + FIRED.removeprefix('FIRED ')),
        (
            NOT_FIRED,
            "the Edit menu's action hadn't fired when read, 0.0 s after it was scheduled",
        ),  # at the failed read
    ],
    ids=['fired', 'not fired'],
)
def test_a_failed_read_of_the_graph_says_what_the_actions_state_read_after_it_said(
    undo: ModuleType, capsys: pytest.CaptureFixture[str], state: str, said: str
) -> None:
    # REVIEW.md TST-691: the state read after a failed graph read kept only an error. Its answer is said, and taken for
    # nothing else: the detail and the put-back are as before
    c, calls = _designer(lambda u, r, since: 'Error: the graph is gone' if u else CHANGED, fired=[state])
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    assert said in _said(out), _said(out)
    assert _line(out, SET).endswith('a read failed: Error: the graph is gone') and 'Redo' not in calls, calls


def test_the_undo_checks_end_reads_the_action_left_armed_when_a_check_raised(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-690: the code-run check raising on a reply with no IDS skipped the end's read, the set check's
    # put_back Redo left armed
    c, calls = _designer(lambda u, r, since: NONE_SHOWS, fired=[FIRED] * 4 + ['ARMED True\nFIRED None'])

    async def no_ids(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        if _what(name, args) == 'two nodes':
            calls.append('two nodes')
            return tool_result('')
        return await c(name, args)

    with pytest.raises(AttributeError):
        asyncio.run(undo.run(_ctx(no_ids)))
    assert calls[-2:] == ['two nodes', 'fired'], calls
    assert "the undo checks' end: the Edit menu's action armed last hadn't fired; reading its state disarmed it" in (
        _said(capsys.readouterr().out)
    )


def test_an_action_that_found_another_graph_current_as_it_fired_fails_saying_so(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-693: it didn't fire, so it is neither sent again, to the graph current then, nor put back
    c, calls = _designer(lambda u, r, since: CHANGED, fired=['FIRED NOT_CURRENT current=probe_other'])
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = capsys.readouterr().out
    line = _line(out, SET)
    assert line.startswith('FAIL') and line.endswith(
        "the Edit menu's action didn't fire: NOT_CURRENT current=probe_other"
    ), line
    assert "the Edit menu's action didn't fire: NOT_CURRENT current=probe_other" in _said(out), _said(out)
    assert calls.count('Undo') == 1 and 'Redo' not in calls, calls


@pytest.mark.parametrize('lands', [True, False], ids=['lands', 'never shows'])
def test_the_redo_putting_back_an_undo_that_never_showed_is_read_until_it_shows(
    undo: ModuleType, capsys: pytest.CaptureFixture[str], lands: bool
) -> None:
    # REVIEW.md TST-693: put_back sent its Redo unread, its landing never confirmed. The Undo fired and never showed;
    # the Redo putting back the step it hit changes the graph from its last read
    redone = _graph('9 levels @(0,0)', CHANGED)
    c, calls = _designer(lambda u, r, since: redone if r and lands else CHANGED)
    asyncio.run(undo.check_one_undo_puts_an_outputs_fields_back(_ctx(c)))
    out = _said(capsys.readouterr().out)
    after = calls[calls.index('Redo') :]
    said = [line for line in out if line.startswith('the Redo putting it back')]
    if lands:
        assert (after, said) == (['Redo', 'describe_graph', 'as prepared'], []), (after, said)
    else:
        assert after[-2:] == ['fired', 'as prepared'] and 'describe_graph' in after, after
        assert said == [
            "the Redo putting it back: the Edit menu's action fired; describe_graph didn't show the Redo within 10 s"
        ], out
