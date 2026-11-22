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
# the Pixel Processor the set_function check adds, its function replaced, and with the function before
REPLACED = ('7 pixelprocessor @(0,600)', '    perpixel <- a function')
BEFORE = ('7 pixelprocessor @(0,600)', "    perpixel <- a function reading '$time'")
SET_FUNCTION = 'check_one_undo_reverts_a_set_function'
SET_FUNCTION_UNDO = 'one Undo brings back the function before, the node kept'
# the blend the input value check adds (ref bl, 8), connected from its Value Processor (ref vp, 7) into #u, and without
LINKED, UNLINKED = '8 blend @(200,800)  in: #u<-7.unique_filter_output', '8 blend @(200,800)'
INPUT_VALUE = 'check_one_undo_reverts_a_connect_into_a_new_input_value'
INPUT_VALUE_UNDO = 'connect into a new #name: one Undo removes the connection'
INPUT_VALUE_REDO = 'connect into a new #name: Redo brings the connection back'
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
    """What a tool call of the checks does: the tool, or for code the snippet it runs; set_function on a function graph
    of the package is 'set_function graph', and describe_graph of one 'describe function'."""
    if name in ('set_function', 'describe_graph') and (args or {}).get('function'):
        return 'set_function graph' if name == 'set_function' else 'describe function'
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
    graph: Graph,
    fired: Sequence[str] = (FIRED,),
    undo: str | Sequence[str] = SCHEDULED,
    values: Callable[[int, int], bool | str] | None = None,
    nodes: Callable[[int, int], str] | None = None,
) -> tuple[FakeCall, list[str]]:
    """A fake tool call: each describe_graph answers `graph` (an answer starting 'Error' is an error), each Undo sent
    answers `undo`, or the next of them (the last again once they run out), each read of the action's state the next of
    `fired` (the same way); and the calls it got. set_function refuses, listing the blend's input value #u when
    `values` says it has it, by the Undos and Redos sent (default: while the graph shows its link, LINKED), or answers
    the text `values` gives (an answer starting 'Error' is an error). A read of a function graph's nodes answers what
    `nodes` gives, by the Undos and Redos sent."""
    calls: list[str] = []
    # an add's refs: the Value Processor and the blend the input value check adds
    answers = {'apply_edits': "added 7\n  ref 'vp' = 7\n  ref 'bl' = 8", 'Redo': SCHEDULED, 'two nodes': 'IDS=7,8'}
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
        if what == 'describe function' and nodes:
            read = nodes(calls.count('Undo'), calls.count('Redo'))
            return tool_result(read, error=read.startswith('Error'))
        if what == 'set_function':
            u, r = calls.count('Undo'), calls.count('Redo')
            has = values(u, r) if values else LINKED in graph(u, r, since[0])
            if isinstance(has, str):
                return tool_result(has, error=has.startswith('Error'))
            listed = '; its input values are #u.' if has else ', nor any other: connect a value into it first.'
            return tool_result(
                'column 1: the node has no input value `#lacking`%s Nothing was built.' % listed, error=True
            )
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
        (SET_FUNCTION, SET_FUNCTION_UNDO, list(REPLACED)),
        (INPUT_VALUE, INPUT_VALUE_UNDO, [LINKED]),
    ],
    ids=['add', 'code run', 'set_function', 'input value'],
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


def test_the_set_function_check_reads_its_undo_and_redo_with_describe_graph(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    c, calls = _designer(lambda u, r, since: _graph(*BEFORE) if u > r else _graph(*REPLACED))
    asyncio.run(undo.check_one_undo_reverts_a_set_function(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, SET_FUNCTION_UNDO).startswith('PASS')
    assert _line(out, 'Redo brings back the new one').startswith('PASS')
    assert calls == [
        'apply_edits',
        'set_function',
        'set_function',
        'describe_graph',
        'Undo',
        'describe_graph',
        'Redo',
        'describe_graph',
        'apply_edits',
    ]


def test_the_input_value_check_reads_its_undo_and_redo_with_describe_graph(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    c, calls = _designer(lambda u, r, since: _graph(UNLINKED) if u > r else _graph(LINKED))
    asyncio.run(undo.check_one_undo_reverts_a_connect_into_a_new_input_value(_ctx(c)))
    out = capsys.readouterr().out
    for name in (INPUT_VALUE_UNDO, 'connect into a new #name: one Undo removes the #name it made', INPUT_VALUE_REDO):
        assert _line(out, name).startswith('PASS'), out
    assert _line(out, 'connect into a new #name: Redo brings the #name back').startswith('PASS'), out
    assert calls == [
        'apply_edits',
        'apply_edits',
        'describe_graph',
        'set_function',
        'Undo',
        'describe_graph',
        'set_function',
        'Redo',
        'describe_graph',
        'set_function',
        'apply_edits',
    ]


def test_the_input_value_check_fails_when_the_undo_leaves_the_name(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # the connection gone and #u left: set_function would read it with nothing connected (REVIEW.md TST-725)
    c, _ = _designer(lambda u, r, since: _graph(UNLINKED) if u > r else _graph(LINKED), values=lambda u, r: True)
    asyncio.run(undo.check_one_undo_reverts_a_connect_into_a_new_input_value(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, INPUT_VALUE_UNDO).startswith('PASS'), out
    assert _line(out, 'connect into a new #name: one Undo removes the #name it made').startswith('FAIL'), out


def test_the_input_value_check_fails_naming_a_read_of_the_values_that_failed(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-731: a reply listing none was taken for no input value; a read that fails fails the check, naming
    # it, as TST-652 and TST-655 set
    error = 'Error executing tool set_function: bridge busy'
    c, _ = _designer(
        lambda u, r, since: _graph(UNLINKED) if u > r else _graph(LINKED), values=lambda u, r: error if u > r else True
    )
    asyncio.run(undo.check_one_undo_reverts_a_connect_into_a_new_input_value(_ctx(c)))
    line = _line(capsys.readouterr().out, 'connect into a new #name: one Undo removes the #name it made')
    assert line.startswith('FAIL') and line.endswith('a read failed: ' + error), line


@pytest.mark.parametrize(
    'after',
    [_graph(), _graph(*REPLACED), _graph('7 pixelprocessor @(0,600)')],
    ids=['the node gone', 'the new function left', 'no function'],
)
def test_the_set_function_check_fails_unless_the_undo_brings_back_the_function_before(
    undo: ModuleType, capsys: pytest.CaptureFixture[str], after: str
) -> None:
    # REVIEW.md TST-713: an Undo taking the node away, or only part of the replacement, isn't the function back
    c, _ = _designer(lambda u, r, since: after if u > r else _graph(*REPLACED))
    asyncio.run(undo.check_one_undo_reverts_a_set_function(_ctx(c)))
    assert _line(capsys.readouterr().out, SET_FUNCTION_UNDO).startswith('FAIL')


FUNCTION_GRAPH = 'check_one_undo_reverts_a_function_graph'
# what describe_graph of the self-test graph says of its package's function graphs: none, undo_fn made with k, given m
UNDO_FN = (
    '',
    'function graphs of the package: undo_fn(k float) -> float',
    'function graphs of the package: undo_fn(k float, m float) -> float',
)
FUNCTION_GRAPH_LINES = (
    'a function graph made: one Undo removes it',
    'a function graph made: Redo brings it back',
    'a function graph given another input: one Undo brings back its inputs before',
    'a function graph given another input: Redo brings back the new ones',
)
# what describe_graph says of undo_fn itself, after each of them: refused, k * 0.5's nodes, k + m's (REVIEW.md TST-740)
UNDO_FN_NODES = (
    "Error executing tool describe_graph: the package of graph mcp_selftest has no function graph 'undo_fn'; its "
    'function graphs: none',
    'function graph undo_fn of /p/mine.sbs: 3 nodes, output node 9 mul -> float\ninputs: k float',
    'function graph undo_fn of /p/mine.sbs: 3 nodes, output node 9 add -> float\ninputs: k float, m float',
)
FUNCTION_GRAPH_NODES = (
    'a function graph made: one Undo removes its nodes too',
    'a function graph made: Redo brings back its nodes too',
    'a function graph given another input: one Undo brings back its nodes before too',
    'a function graph given another input: Redo brings back the new nodes too',
)
State = Callable[[int, int, int], int]  # (set_function on undo_fn so far, Undos, Redos) -> UNDO_FN's index


def _function_graphs(
    undone: State = lambda made, u, r: made - u + r, nodes: State | None = None
) -> tuple[FakeCall, list[str]]:
    """A fake Designer for the function graph check: set_function on undo_fn makes it, then gives it m too; each read,
    describe_graph of the self-test graph, names what the package has, by `undone` as UNDO_FN's index: as one step
    each, by default. describe_graph of undo_fn answers by `nodes` (default: `undone`) as UNDO_FN_NODES' index."""

    def state(given: State, u: int, r: int) -> int:
        return max(0, min(2, given(calls.count('set_function graph'), u, r)))

    c, calls = _designer(
        lambda u, r, since: '\n'.join(line for line in (_graph(), UNDO_FN[state(undone, u, r)]) if line),
        nodes=lambda u, r: UNDO_FN_NODES[state(nodes or undone, u, r)],
    )
    return c, calls


def test_the_function_graph_check_reads_its_undo_and_redo_with_describe_graph(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-735 read the function graph with set_function's refusal of a call, as describe_graph showed none
    c, calls = _function_graphs()
    asyncio.run(undo.check_one_undo_reverts_a_function_graph(_ctx(c)))
    out = capsys.readouterr().out
    for name in FUNCTION_GRAPH_LINES + FUNCTION_GRAPH_NODES:
        assert _line(out, name).startswith('PASS'), out
    assert 'describe_graph showed it' in _line(out, FUNCTION_GRAPH_LINES[0])
    # the nodes read with describe_graph's function once each Undo and Redo has shown, never between a send and that
    # read; no Qt events, no node read by code (REVIEW.md TST-741: with the function graph's own states, so that each is
    # reached)
    shown = ['describe_graph', 'describe function']
    assert calls == [
        'set_function graph',
        'describe_graph',
        'Undo',
        *shown,
        'Redo',
        *shown,
        'set_function graph',
        'describe_graph',
        'Undo',
        *shown,
        'Redo',
        *shown,
    ]


def test_the_function_graph_check_fails_when_an_undo_brings_back_the_inputs_and_not_the_nodes(
    undo: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW.md TST-740: the inputs alone would pass the Undo of the replacement
    c, _ = _function_graphs(nodes=lambda made, u, r: 2 if made == 2 else made - u + r)
    asyncio.run(undo.check_one_undo_reverts_a_function_graph(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, FUNCTION_GRAPH_LINES[2]).startswith('PASS'), out
    assert _line(out, FUNCTION_GRAPH_NODES[2]).startswith('FAIL'), out


@pytest.mark.parametrize(
    ('undone', 'failing'),
    [
        # the Undo of the replacement taking undo_fn away whole
        (lambda made, u, r: 0 if made == 2 and u > r else made - u + r, FUNCTION_GRAPH_LINES[2]),
        # an Undo that leaves undo_fn
        (lambda made, u, r: made, FUNCTION_GRAPH_LINES[0]),
    ],
    ids=['an Undo of the replacement removing it', 'an Undo leaving it'],
)
def test_the_function_graph_check_fails_unless_one_undo_brings_back_what_was_before(
    undo: ModuleType, capsys: pytest.CaptureFixture[str], undone: State, failing: str
) -> None:
    c, _ = _function_graphs(undone)
    asyncio.run(undo.check_one_undo_reverts_a_function_graph(_ctx(c)))
    assert _line(capsys.readouterr().out, failing).startswith('FAIL')


@pytest.mark.parametrize(
    ('said', 'nodes'),
    [
        (UNDO_FN_NODES[0], 'none'),
        (UNDO_FN_NODES[1], '3 nodes, output mul'),
        # a step of its build undone alone, as a build outside one undo group leaves it
        ('function graph undo_fn of /p/mine.sbs: 3 nodes, no output node\ninputs: k float', None),
        ('Error executing tool describe_graph: bridge busy', None),
    ],
    ids=['none', 'k * 0.5', 'no output node', 'another reply'],
)
def test_the_function_graphs_nodes_are_read_from_describe_graph(undo: ModuleType, said: str, nodes: str | None) -> None:
    # anything but a function graph's nodes or its absence is said as it came, never taken for either
    menu = sys.modules['test_all_tools.undo.edit_menu']

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        assert name == 'describe_graph' and args == {'graph': 'mcp_selftest', 'function': 'undo_fn'}
        return tool_result(said, error=said.startswith('Error'))

    read = asyncio.run(menu.function_graph_nodes(c, {'graph': 'mcp_selftest'}, 'undo_fn'))
    assert read == (nodes or said.splitlines()[0])


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
    'step, name, start, shown, before',
    [
        (
            'check_one_undo_removes_an_added_node',
            ('add: one Undo removes the added node', 'add: Redo restores it'),
            _graph(*REPLACED),
            _graph(),
            0,
        ),
        (
            'check_one_undo_reverts_a_whole_code_run',
            ('one Undo reverts the whole run', 'one Redo restores it'),
            _graph(*REPLACED),
            _graph(),
            0,
        ),
        # one read before the Undo: the function replaced
        (SET_FUNCTION, (SET_FUNCTION_UNDO, 'Redo brings back the new one'), _graph(*REPLACED), _graph(*BEFORE), 1),
        # one read before the Undo: the connection made
        (INPUT_VALUE, (INPUT_VALUE_UNDO, INPUT_VALUE_REDO), _graph(LINKED), _graph(UNLINKED), 1),
    ],
    ids=['add', 'code run', 'set_function', 'input value'],
)
def test_a_read_that_failed_fails_the_check_naming_it(
    undo: ModuleType,
    capsys: pytest.CaptureFixture[str],
    step: str,
    name: tuple[str, str],
    start: str,
    shown: str,
    before: int,
    redo: bool,
) -> None:
    # REVIEW.md TST-655: an error reply has no node in it, and two failed reads passed "one Undo reverts the whole run";
    # TST-652: read as every node gone, one said the Undo landed
    error = 'Error executing tool describe_graph: bridge busy'
    c, calls = _designer(lambda u, r, since: start if u == 0 else error if r == int(redo) else shown)
    asyncio.run(getattr(undo, step)(_ctx(c)))
    out = capsys.readouterr().out
    assert _line(out, name[int(redo)]).startswith('FAIL') and 'a read failed: ' + error in _line(out, name[int(redo)])
    assert calls.count('describe_graph') == before + 1 + int(redo), 'no read after the failed one'
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
    'step, graph',
    [
        ('check_one_undo_removes_an_added_node', _back_after(1)),
        ('check_one_undo_puts_an_outputs_fields_back', _back_after(1)),
        ('check_one_undo_reverts_a_whole_code_run', _back_after(1)),
        (SET_FUNCTION, lambda u, r, since: _graph(*BEFORE) if u > r else _graph(*REPLACED)),
        (INPUT_VALUE, lambda u, r, since: _graph(UNLINKED) if u > r else _graph(LINKED)),
        (FUNCTION_GRAPH, None),
    ],
    ids=['add', 'set', 'code run', 'set_function', 'input value', 'function graph'],
)
def test_no_check_runs_qts_events_or_reads_a_node_by_code(undo: ModuleType, step: str, graph: Graph | None) -> None:
    c, calls = _designer(graph) if graph else _function_graphs()
    asyncio.run(getattr(undo, step)(_ctx(c)))
    assert 'processEvents' not in calls and 'exists' not in calls and 'code' not in calls, calls


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
NONE_SHOWS = _graph('7 blur @(0,400)', '8 blur @(200,500)', CHANGED, '    perpixel <- a function', LINKED)


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
    c, calls = _designer(lambda u, r, since: NONE_SHOWS, fired=[FIRED] * 10 + [end])
    asyncio.run(undo.run(_ctx(c)))
    out = _said(capsys.readouterr().out)
    assert calls.count('Redo') == 5 and calls[-3:] == ['fired', 'apply_edits', 'fired'], calls  # after the clean-up
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
