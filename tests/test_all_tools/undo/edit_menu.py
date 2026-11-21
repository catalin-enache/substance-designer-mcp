"""An Undo or a Redo sent through Designer's Edit menu (common.UNDO_REDO), then read back with describe_graph until the
graph shows it, for the undo checks (checks.py; ROADMAP item 112):

- Between the send and the read that shows it, no code job goes to Designer, but the read of the action's state
  (common.UNDO_FIRED) once LANDING_S has passed. In both failures seen, code ran around the trigger (2026-11-20):
  - lsappinfo run in the action's timer callback after the trigger: 6 of 6 Undos fired and never landed. Run before
    the trigger, the add check failed;
  - the graph read by polling NODE_EXISTS, a code job running 20 processEvents(): 2 fired Undos never landed in 10 s.
    Polled with describe_graph, 3 of 3 landed at about 3 s.
  Why is unknown: an Undo whose action fired inside a code job's processEvents(), in the job that scheduled it or a
  later one, landed 21 of 21 times (12 on an added node, 9 on an output's fields), read with describe_graph or by code
  jobs (2026-11-20).
- The graph is read every common.POLL_S, LANDING_S at most after each send: a safety net. A read that fails ends the
  reads, and the check fails naming it (REVIEW.md TST-652, TST-655). The action's state is read then too, which
  disarms an action not fired yet (REVIEW.md TST-687). What it says is printed, and taken for nothing else (REVIEW.md
  TST-691).
- Not shown by then, the action's state is read, which disarms an action not fired yet. One that never fired is sent
  again, SENDS times at most. No earlier one can fire after that read, so the step is never undone twice. One that
  fired and never showed is sent no more, and the check fails naming it.
- A read of the action's state that fails may leave the action armed: the check says it may still fire.
- An action that found another graph current as it fired didn't fire (common.UNDO_REDO): the check fails saying so,
  and it is neither sent again nor put back (REVIEW.md TST-693).
- An action a check that raised left armed is read once nothing follows, at the end of the undo checks
  (read_left_armed; REVIEW.md TST-690).

A check that fails prints Designer's state as the action was scheduled and as it fired, the app in front as macOS said
it, and the graph as last read (Sent.say). The self-test reads the app in front itself (FrontRead), so that nothing
runs in Designer for it."""

import asyncio
import os
import re
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from test_all_tools import common
from test_all_tools.common import (
    POLL_S,
    TEST_GRAPH,
    UNDO_FIRED,
    UNDO_REDO,
    Call,
    agents_designers,
    check,
    positions,
    text,
)
from test_all_tools.window_server import active_app, process_name

LANDING_S = 10  # s at most the graph is read for after each send: a limit, the safety net
SENDS = 3  # sends at most, each after a read saying the one before never fired: a limit, the safety net
READS_THE_FRONT = sys.platform == 'darwin'  # lsappinfo, as window_server reads the app in front


def fields_back(described: str) -> bool:
    """Whether describe_graph's text shows the output's fields as before the set: identifier `height`, no usage."""
    return "identifier='height' usage=none" in described and 'undo_me' not in described


def nodes_gone(*ids: str) -> Callable[[str], bool]:
    """Whether describe_graph's text lists none of these nodes."""
    return lambda described: not set(ids) & set(positions(described))


def nodes_listed(*ids: str) -> Callable[[str], bool]:
    """Whether describe_graph's text lists all of these nodes."""
    return lambda described: set(ids) <= set(positions(described))


class FrontRead:
    """The app in front as macOS says it (window_server.active_app), read on a thread of its own as it is made: the
    check's calls go on meanwhile. A read between them would delay the next by tens of ms, which can hide a late Undo.
    On macOS only (READS_THE_FRONT)."""

    def __init__(self) -> None:
        self._active: int | None = None
        self._thread = threading.Thread(target=self._read, daemon=True)
        if READS_THE_FRONT:
            self._thread.start()

    def _read(self) -> None:
        self._active = active_app()

    def said(self) -> str:
        """'<name> (<pid>)', the name of its executable's file (ps gives its path); 'unread' when lsappinfo couldn't
        tell; 'not read' off macOS."""
        if self._thread.ident is None:
            return 'not read'
        self._thread.join()
        if self._active is None:
            return 'unread'
        return '%s (%d)' % (os.path.basename(process_name(self._active)), self._active)


Which = Literal['Undo', 'Redo']


@dataclass
class Sent:
    """What became of an Undo or a Redo sent (send): how many times it was sent, and whether and when the graph showed
    it, or why not."""

    which: Which
    sends: int = 0
    shown: float | None = None  # s from the last send to the read that showed it; None: never shown
    refused: str = ''  # what UNDO_REDO printed when it scheduled nothing (NOT_FOCUSED, NO_ACTION), with the state seen
    error: str = ''  # the error of the read that failed and ended the reads
    fired: bool | None = (
        None  # whether the action fired, as UNDO_FIRED read it; None: not read, or the read said nothing
    )
    # what that read said (_fired): Designer's state as the action fired, 'None', or 'not read'. Also the read after a
    # failed graph read, which `fired` isn't taken from (REVIEW.md TST-691)
    fired_said: str = ''
    fired_read: float = 0.0  # s from the last send to that read
    unread: str = ''  # why that read failed: the action may still fire (REVIEW.md TST-687)
    scheduled: str = ''  # what UNDO_REDO printed for the last send
    described: str = ''  # the graph as last read
    fronts: tuple[FrontRead, FrontRead] | None = None  # the app in front as the last send went, and as the reads ended

    def begin_send(self) -> None:
        """Clears what the send before read of the action, as a send starts: its lines are this send's (REVIEW.md
        TST-667)."""
        self.fired, self.fired_said, self.fired_read = None, '', 0.0

    def detail(self) -> str:
        """The check's detail: how many sends, and when the graph showed it; or what went wrong, after how many sends
        when more than one, first, so the 150 characters common.check keeps hold it (REVIEW.md TST-662)."""
        resent = 'sent %d times, the action before never fired; ' % self.sends if self.sends > 1 else ''
        if self.shown is not None:
            return '%sdescribe_graph showed it %.1f s after the last send' % (resent or 'sent once; ', self.shown)
        if self.fired is False:  # this send's: a resend refused, or whose read failed, is said by _why
            return "the Edit menu's action never fired, sent %d times" % self.sends
        return resent + self._why()

    def _why(self) -> str:
        """What went wrong, but an action that never fired: no schedule, a read that failed, or the graph not showing
        it."""
        if self.refused:
            return 'not scheduled: ' + self.refused
        if self.error:
            return 'a read failed: ' + self.error
        if self.fired_said.startswith(NOT_CURRENT):
            return "the Edit menu's action didn't fire: " + self.fired_said
        if self.fired is None:
            return "describe_graph didn't show the %s within %d s; whether the Edit menu's action fired wasn't said" % (
                self.which,
                LANDING_S,
            )
        return "the Edit menu's action fired; describe_graph didn't show the %s within %d s" % (self.which, LANDING_S)

    def say(self) -> None:
        """Prints, each on a line of its own, what a check's detail can't hold (common.check cuts it at 150 characters):
        Designer's state as the action was last scheduled; the app in front then and as the reads ended; the action's
        state as it fired, or that it hadn't when read, or that it may still fire; the graph as last read. A refusal is
        printed whole instead (REVIEW.md TST-685)."""
        if self.refused:
            print('      the %s, not scheduled: %s' % (self.which, self.refused))
            return
        at_schedule = re.search(r'AT_SCHEDULE (.*)', self.scheduled)
        print(
            '      the %s, as it was last scheduled: %s'
            % (self.which, at_schedule.group(1) if at_schedule else 'not said')
        )
        if self.fronts is not None:
            print(
                "      the app in front, as macOS said it: %s as the %s was scheduled, %s as the check read it; Designer's "
                'process %s'
                % (
                    self.fronts[0].said(),
                    self.which,
                    self.fronts[1].said(),
                    agents_designers().get(common.PORT, 'not recorded'),
                )
            )
        if self.unread:
            print("      the Edit menu's action may still fire: its state wasn't read: " + self.unread)
        elif self.fired_said.startswith(NOT_CURRENT):
            print("      the Edit menu's action didn't fire: " + self.fired_said)
        elif self.fired_said == 'None':
            print(
                "      the Edit menu's action hadn't fired when read, %.1f s after it was scheduled" % self.fired_read
            )
        elif self.fired_said:
            print("      the Edit menu's action as it fired: " + self.fired_said)
        print('      the graph as last read: ' + ' / '.join(self.described.strip().splitlines()))


async def send(c: Call, graph: dict[str, str], which: Which, shows: Callable[[str], bool]) -> Sent:
    """Sends `which` ('Undo' or 'Redo') through the Edit menu of the self-test graph, and reads `graph` with
    describe_graph until `shows` says its text shows it: sent again only when the action never fired (the module
    docstring)."""
    sent = Sent(which)
    while sent.sends < SENDS:
        front = FrontRead()
        sent.begin_send()
        sent.scheduled = text(await c('execute_designer_code', {'code': UNDO_REDO % (TEST_GRAPH, which)}))
        sent.sends += 1
        if 'SCHEDULED' not in sent.scheduled:
            sent.refused = ' '.join(sent.scheduled.split()) or 'nothing said'
            return sent
        at = time.monotonic()
        while True:
            read = await c('describe_graph', graph)
            if read.is_error:
                sent.error, sent.fronts = text(read).strip(), (front, FrontRead())
                # its state read, which disarms an action not fired yet, as nothing reads it after; its answer is not
                # taken for the check's, which this read's failure ends (REVIEW.md TST-687)
                state = await c('execute_designer_code', {'code': UNDO_FIRED})
                sent.fired_read = time.monotonic() - at
                if state.is_error:
                    sent.unread = text(state).strip()
                else:  # said, and kept out of `fired`: the detail and the put-back are as before (REVIEW.md TST-691)
                    sent.fired_said = _fired(text(state))
                return sent
            sent.described = text(read)
            if shows(sent.described):
                sent.shown = time.monotonic() - at
                return sent
            if time.monotonic() - at >= LANDING_S:
                break
            await asyncio.sleep(POLL_S)
        sent.fronts = (front, FrontRead())
        state = await c('execute_designer_code', {'code': UNDO_FIRED})
        sent.fired_read = time.monotonic() - at
        if state.is_error:
            sent.error = sent.unread = text(state).strip()
            return sent
        sent.fired_said = _fired(text(state))
        if sent.fired_said.startswith(NOT_CURRENT):  # it didn't fire, and sent again it would find that graph current
            return sent
        sent.fired = None if sent.fired_said == 'not read' else sent.fired_said != 'None'
        if sent.fired is not False:
            return sent
    return sent


# what UNDO_FIRED says of an action that found another graph current as it fired, and didn't fire (common.UNDO_REDO)
NOT_CURRENT = 'NOT_CURRENT'


def _fired(said: str) -> str:
    """What UNDO_FIRED `said` of the action: Designer's state as it fired, 'None' when it hadn't, 'not read' when it
    said nothing."""
    fired = re.search(r'FIRED (.*)', said)
    return fired.group(1) if fired else 'not read'


async def read_left_armed(c: Call) -> None:
    """Reads the Edit menu's action's state once nothing follows, at the end of the undo checks (checks.run), which
    disarms an action armed and not fired yet: one a check left armed as it raised before its send read it (REVIEW.md
    TST-690; put_back's Redo is read by send since TST-693). Read straight after a send, it would disarm the action
    before its timer runs. Says an action that hadn't fired, or that it may still fire when the read fails."""
    state = await c('execute_designer_code', {'code': UNDO_FIRED})
    said = text(state).strip()
    if state.is_error:
        print("      the undo checks' end: the Edit menu's action may still fire: its state wasn't read: " + said)
    elif 'ARMED True' in said and _fired(said) == 'None':
        print(
            "      the undo checks' end: the Edit menu's action armed last hadn't fired; reading its state disarmed it"
        )


def recorded(sent: Sent, tool: str, name: str) -> bool:
    """Records check `name` of `tool` on whether the graph showed `sent` (send), with how it went, and returns that. On
    failure it prints why (Sent.say)."""
    shown = sent.shown is not None
    check(tool, name, shown, sent.detail())
    if not shown:
        sent.say()
    return shown


async def put_back(c: Call, graph: dict[str, str], sent: Sent) -> None:
    """After an Undo that fired and never showed (send), which hit some other step: a Redo puts that back, sent and
    read as the Undo was, until `graph` changes from its last read; says when it never does (REVIEW.md TST-693)."""
    if sent.which == 'Undo' and sent.shown is None and sent.fired:
        before = sent.described
        redo = await send(c, graph, 'Redo', lambda described: described != before)
        if redo.shown is None:
            print('      the Redo putting it back: ' + redo.detail())
