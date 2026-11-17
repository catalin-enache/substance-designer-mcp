"""What the self-test's 3D window checks read of Designer's window (editor_panels_and_fit/window_states.py): the
state lines its snippets print, and whether a shot left Designer not the active app, judged only where it can be
(REVIEW.md TST-392)."""

import ast
import re
from collections.abc import Sequence
from types import ModuleType

import pytest
from selftest_fakes import fresh

from project_constants import ToolArgs


@pytest.fixture
def window_states() -> ModuleType:
    return fresh('editor_panels_and_fit.window_states')


def test_focus_is_kept_while_designer_stays_not_the_active_app(window_states: ModuleType) -> None:
    assert window_states.focus({'active': 'False'}, {'active': 'False'}) is True


def test_focus_is_taken_when_the_shot_made_designer_the_active_app(window_states: ModuleType) -> None:
    assert window_states.focus({'active': 'False'}, {'active': 'True'}) is False


@pytest.mark.parametrize('after', ['True', 'False'])
def test_focus_isnt_judged_when_designer_was_the_active_app_before(window_states: ModuleType, after: str) -> None:
    # TST-392: a shot can't be seen taking focus Designer already had; hiding it again would read as not taking it
    assert window_states.focus({'active': 'True'}, {'active': after}) is None


@pytest.mark.parametrize('before, after', [({}, {'active': 'False'}), ({'active': 'False'}, {})])
def test_focus_isnt_judged_without_both_states(
    window_states: ModuleType, before: dict[str, str], after: dict[str, str]
) -> None:
    assert window_states.focus(before, after) is None


@pytest.mark.parametrize(
    'first, second, ahead',
    [('cover', 'main', True), ('main', 'below', True), ('below', 'main', False), ('later', 'main', False)],
)
def test_a_window_is_ahead_of_the_windows_listed_after_it(
    window_states: ModuleType, first: str, second: str, ahead: bool
) -> None:
    # REVIEW.md HLP-130, HLP-131: the order Designer's windows are left in; one not listed is ahead of none
    assert window_states.ahead('cover,main,below', first, second) is ahead


LEFT_UP = "Designer's window: left on screen, as Designer became the active app during the shot\n"


@pytest.mark.parametrize(
    'said, before, after, became',
    [
        (LEFT_UP, {'active': 'False'}, {'active': 'True'}, True),
        (LEFT_UP, {}, {}, True),  # said so, whatever was read
        ('', {'active': 'False'}, {'active': 'True'}, True),  # activation brought its windows in front: nothing said
        ('', {'active': 'True'}, {'active': 'True'}, False),  # the active app already
        ('', {'active': 'False'}, {'active': 'False'}, False),
        ('', {}, {'active': 'True'}, False),  # not read before: as the tool, judged
    ],
)
def test_designer_becoming_the_active_app_during_a_shot_is_told_apart(
    window_states: ModuleType, said: str, before: dict[str, str], after: dict[str, str], became: bool
) -> None:
    # REVIEW.md TST-399: the window's put-back can't be judged then; the tool leaves the window up, as decided
    assert window_states.became_active(said, before, after) is became


def test_the_last_state_line_of_each_kind_is_read(window_states: ModuleType) -> None:
    printed = (
        'BEFORE minimized=False active=False\n'
        '  STATE minimized=True order=main\n'
        "Designer's window: un-minimized\n"
        'STATE minimized=False order=cover,main,below\n'
    )
    assert window_states.states(printed) == {
        'BEFORE': {'minimized': 'False', 'active': 'False'},
        'STATE': {'minimized': 'False', 'order': 'cover,main,below'},
    }


def test_every_render_line_is_read_in_order(window_states: ModuleType) -> None:
    # the window's state as each render of a shot was read: all of them, not only the last
    printed = (
        'RENDER covered=False opacity=0 through=True\n'
        "Designer's window: brought in front again\n"
        '  RENDER covered=True opacity=0 through=True\n'
        'STATE covered=True opacity=1 through=False\n'
    )
    assert window_states.renders(printed) == [
        {'covered': 'False', 'opacity': '0', 'through': 'True'},
        {'covered': 'True', 'opacity': '0', 'through': 'True'},
    ]


@pytest.mark.parametrize(
    'event, said, after, seen',
    [
        # a window brought over Designer's: the shot brought it in front again, and said so
        (
            'cover',
            "Designer's window: brought in front again, transparent, as another window covered it during the shot\n",
            {},
            True,
        ),
        ('cover', '', {}, False),
        # REVIEW.md TST-416: said without ', transparent' when Designer is the active app at that look
        (
            'cover',
            "Designer's window: brought in front again, as another window covered it during the shot\n",
            {},
            True,
        ),
        (
            'later',
            "Designer's window: brought in front again, as another window covered it during the shot\n",
            {},
            True,
        ),
        (
            'later',
            "Designer's window: brought in front again, transparent, as another window covered it during the shot\n",
            {},
            True,
        ),
        ('later', "Designer's window: put back behind the window that was in front of it\n", {}, False),
        # TWO's smaller window raised: in front of the cover after the shot, which TWO put in front of it
        ('raise', '', {'order': 'later,cover,main,below'}, True),
        ('raise', '', {'order': 'cover,later,main,below'}, False),
        # the cover closed or minimized: off screen after the shot, as CoreGraphics lists it
        ('close', '', {'cover_on_screen': 'False'}, True),
        ('close', '', {'cover_on_screen': 'True'}, False),
        ('minimize', '', {'cover_on_screen': 'False'}, True),
        ('minimize', '', {'cover_on_screen': 'True'}, False),
        ('minimize', '', {}, False),  # not read: not seen
        (None, '', {}, True),  # no event
    ],
)
def test_an_event_during_a_shot_is_seen_to_have_happened_only_by_its_effect(
    window_states: ModuleType, event: str | None, said: str, after: dict[str, str], seen: bool
) -> None:
    # REVIEW.md TST-415: an event that did nothing left the put-back check passing on the put-back it was made to catch
    assert window_states.event_seen(event, said, after) is seen


def test_every_event_has_a_way_to_be_seen(window_states: ModuleType) -> None:
    # REVIEW.md TST-415: a new event the check can't see would pass whatever it did
    assert set(window_states.SEEN_BY) == set(window_states.EVENTS)


@pytest.mark.parametrize(
    'printed, clear',
    [
        ('HITS opaque=main transparent=main through=cover\nIN_FRONT 0\n', True),
        ('HITS opaque=another transparent=another through=another\nIN_FRONT 1\n', False),
        ('IN_FRONT 2\nIN_FRONT 0\n', True),  # the last reading counts
        ('HITS opaque=main transparent=main through=cover\n', False),  # not read: not clear
    ],
)
def test_a_reading_is_clear_only_when_no_window_was_found_in_front(
    window_states: ModuleType, printed: str, clear: bool
) -> None:
    # REVIEW.md TST-417: another app's window in front of the window read changes the reading; that try is taken again
    assert window_states.nothing_in_front(printed) is clear


MADE_OPAQUE = "Designer's window: made opaque at once, as Designer became the active app during the shot\n"


@pytest.mark.parametrize(
    'said, off, after, activated',
    [
        (MADE_OPAQUE, {'active': 'False'}, {'active': 'False'}, True),  # made the active app, then left
        (LEFT_UP, {'active': 'False'}, {'active': 'True'}, True),
        ('', {'active': 'False'}, {'active': 'True'}, True),  # focus lost, nothing said
        ('', {'active': 'False'}, {'active': 'False'}, False),
        ('', {'active': 'True'}, {'active': 'True'}, False),  # the active app already as the shot began: not judged
        ('', {}, {'active': 'True'}, False),  # not read before the shot
    ],
)
def test_designer_made_the_active_app_during_a_shot_is_told_from_the_shot_and_the_states(
    window_states: ModuleType, said: str, off: dict[str, str], after: dict[str, str], activated: bool
) -> None:
    # REVIEW.md TST-418: such a way is taken again; a shot that makes Designer the active app itself does it each time
    assert window_states.activated(said, off, after) is activated


@pytest.mark.parametrize(
    'name',
    [
        'check_the_3d_view_isnt_drawn_while_designers_window_is_off_screen',
        'check_a_click_goes_through_designers_window_once_transparent_and_click_through',
        'check_a_window_under_designers_transparent_window_counts_as_visible',
        'check_a_3d_shot_puts_designers_window_on_screen_without_taking_focus',
        # REVIEW.md TST-453: they read the windows in front of Designer's, and retried without the lock
        'check_a_hidden_designers_window_is_brought_in_front_for_a_3d_shot_once_its_unhide_took',
        'check_the_3d_views_frames_say_when_it_has_drawn',
    ],
)
def test_the_window_checks_the_pool_disturbed_read_while_no_designer_starts(name: str) -> None:
    # REVIEW.md TST-417: the windows a Designer of the pool brings as it starts, and the activation it hands over,
    # came in bursts longer than the retries; holding the pool's launch lock, none starts or quits meanwhile
    import ast
    from pathlib import Path

    path = Path(__file__).parents[1] / 'test_all_tools' / 'editor_panels_and_fit' / 'checks.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    check = next(node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef) and node.name == name)
    held = [
        node
        for node in ast.walk(check)
        if isinstance(node, ast.With)
        and any('no_designer_starting' in ast.unparse(item.context_expr) for item in node.items)
    ]
    assert held, '%s reads windows without holding the launch lock' % name
    # the readings inside it: the snippets that read windows, or the shots
    inside = ast.unparse(held[0])
    readings = ('without_others_in_front(', "'screenshot_designer'", 'SHOWN_FROM_HIDDEN', 'WHO + FRAMES')
    assert any(call in inside for call in readings), inside[:200]


# --- nothing of Designer's in front of the user's windows unless asked (DECISIONS.md, Project rules)

CHECKS_FILE = 'editor_panels_and_fit/checks.py'


def _functions() -> dict[str, ast.AsyncFunctionDef]:
    from pathlib import Path

    path = Path(__file__).parents[1] / 'test_all_tools' / CHECKS_FILE
    tree = ast.parse(path.read_text(encoding='utf-8'))
    return {node.name: node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)}


def test_the_ways_off_the_users_screen_are_set_up_behind_every_window() -> None:
    # unhidden, un-minimized or just shown, Designer's windows came up near the front (2026-11-15)
    import ast
    import re

    states = fresh('editor_panels_and_fit.window_states')
    off = [*states.WAYS, 'transparent in front', states.TWO]
    assert not set(off) & set(states.IN_FRONT)
    m = re.search(r'if way in (\(.*?\)):  # IN_FRONT', states._PUT)
    assert m and ast.literal_eval(m.group(1)) == states.IN_FRONT, "the ways in front of the user's are IN_FRONT"
    behind = states._PUT.split('else:  # behind every window')[1].split('\n', 1)[1]
    assert behind.lstrip().startswith('to_back()')
    made = re.findall(r'window\((.*)\)\n', behind)
    assert made and all('place=' in args for args in made), 'each window of its own placed while transparent'
    assert behind.count('mac.show()') == 1 and "if way == 'transparent in front'" in behind.split('mac.show()')[0]
    steps = (
        'setWindowOpacity(0.0)',
        'made.show()',
        'next_to(shown._window, *place)',
        'setWindowOpacity(1.0)',
    )
    at = [states._WINDOW.index(step) for step in steps]
    assert at == sorted(at), 'shown transparent, placed, then made opaque'


def test_the_window_goes_back_to_rest_hidden_never_shown_on_the_way() -> None:
    states = fresh('editor_panels_and_fit.window_states')
    clear = states._CLEAR
    assert 'mac.show()' not in clear and 'mac.unhide()' not in clear and 'mac.hide()' in clear
    assert clear.index('fade(True)') < clear.index('deminiaturize') < clear.index('mac.hide()')


IN_FRONT_ONLY = (  # whole checks that need a window in front of the user's
    'check_a_click_goes_through_designers_window_once_transparent_and_click_through',
    'check_a_window_under_designers_transparent_window_counts_as_visible',
    'check_a_3d_shot_makes_designers_window_opaque_at_once_once_designer_is_the_active_app',
    'check_a_window_covered_during_a_3d_shot_is_put_in_front_again',
)
SPLIT = (  # checks run twice: their cases off screen, then with in_front=True those in front of the user's windows
    'check_the_3d_view_isnt_drawn_while_designers_window_is_off_screen',
    'check_a_3d_shot_puts_designers_window_on_screen_without_taking_focus',
    'check_a_3d_shot_keeps_designers_window_transparent_and_click_through_while_off_screen',
    'check_a_covered_window_goes_back_behind_its_cover_or_stays_in_front_once_the_cover_is_gone',
    'check_a_plain_3d_shot_shows_a_change_made_while_designers_window_was_off_screen',
)


def _awaits(nodes: Sequence[ast.AST]) -> list[str]:
    """The checks awaited in `nodes`, in order, each with ' in front' when called with in_front=True."""
    found = []
    for node in nodes:
        for n in ast.walk(node):
            if isinstance(n, ast.Await) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name):
                front = any(k.arg == 'in_front' and ast.unparse(k.value) == 'True' for k in n.value.keywords)
                found.append(n.value.func.id + (' in front' if front else ''))
    return found


def test_the_window_checks_off_screen_are_watched_and_those_in_front_run_after_together() -> None:
    # the user's windows: nothing of Designer's in front of them but where a check needs it, and those checks together
    import ast

    functions = _functions()
    run = functions['run']
    watched = [
        node
        for node in run.body
        if isinstance(node, ast.With) and any('FrontWatch' in ast.unparse(item.context_expr) for item in node.items)
    ]
    assert len(watched) == 1
    at = run.body.index(watched[0])
    inside = _awaits([watched[0]])
    after = _awaits(run.body[at + 1 :])
    assert after[0] == 'check_designer_stayed_behind', 'judged right after the block it watched'
    window_checks = {
        name
        for name, f in functions.items()
        if name.startswith('check_') and any(isinstance(n, ast.Name) and n.id == 'window_states' for n in ast.walk(f))
    }
    assert set(IN_FRONT_ONLY) | set(SPLIT) <= window_checks
    # watched from the first check on: the 3D checks before the window checks put the window on screen too (REVIEW.md
    # TST-471)
    assert [name for name in _awaits(run.body[:at]) if name.startswith('check_')] == [], 'a check before the watch'
    # off screen: every window check but those only in front, none of them in front
    assert set(window_checks) - set(IN_FRONT_ONLY) <= set(inside)
    assert not [name for name in inside if name.endswith(' in front') or name in IN_FRONT_ONLY], inside
    # then, right after the judgement, the cases in front of the user's, each once, and nothing after them: a check
    # there would go unwatched (REVIEW.md TST-473: the Scene menu check's 3D shots did)
    in_front = after[1:]
    assert sorted(in_front) == sorted([*IN_FRONT_ONLY, *(name + ' in front' for name in SPLIT)]), in_front


def test_the_put_back_cases_in_front_of_the_users_windows_are_those_that_need_it() -> None:
    checks = fresh('editor_panels_and_fit.checks')
    states = checks.window_states
    # each brings a window over Designer's, which the shot keeps in front of every window, raises one there, leaves
    # Designer's in front once its cover is gone, or has a cover on top; but the one set up behind every window
    assert set(checks.PUT_BACK) - checks.PUT_BACK_IN_FRONT == {'covered, nothing done during the shot'}
    way, event = checks.PUT_BACK['covered, nothing done during the shot'][:2]
    assert way not in states.IN_FRONT and event is None
    for case in checks.PUT_BACK_IN_FRONT:
        way, event = checks.PUT_BACK[case][:2]
        assert event in ('later', 'close', 'minimize', 'raise') or way in states.IN_FRONT, case


def test_the_ways_wait_for_their_state_not_a_fixed_time() -> None:
    # REVIEW.md TST-420: each state was reported within 0.7 s (measured 2026-11-15), the snippets waited 4 to 7 s a way
    import re

    states = fresh('editor_panels_and_fit.window_states')
    for name in ('_PUT', '_CLEAR', '_READ'):
        long = [float(n) for n in re.findall(r'_settle\(([0-9.]+)\)', getattr(states, name)) if float(n) > 0.5]
        assert long == [], (name, long)
    helpers = states._WINDOW.split('def to_back')[1]  # to_back, and the window() it follows
    assert [
        n
        for n in re.findall(r'_settle\(([0-9.]+)\)', helpers + states._WINDOW.split('def window')[1])
        if float(n) > 0.3
    ] == []
    assert 'def until(' in states._WINDOW
    assert re.search(r'until\(reached\)[^\n]*\n\s*print\(.STATE ', states._PUT), 'the state waited for, then read'
    # no margin timed after a state: under load a time measured idle can be too short (the user, 2026-11-15); where
    # no event says the state, it is looked at every 100 ms, as the user asked
    assert 'MARGIN' not in states._WINDOW + states._PUT + states._CLEAR
    until = states._WINDOW.split('def until(')[1].split('    def ')[0]
    assert 'loop.exec()' in until and 'installEventFilter' in until and 'tick.start(100)' in until
    # Qt minimizing the page changes none of its flags: the 3D view's hide event says the view stopped
    qt = states._PUT.split("elif way == 'qt minimized':")[1].split('elif ')[0]
    assert 'QEvent.Type.Hide' in states._WINDOW and 'hidden_view(' in qt
    assert qt.index('hidden_view(') < qt.index('mw.showMinimized()')


def test_a_click_reading_that_reaches_neither_designers_window_nor_the_cover_names_it_and_is_taken_again(
    window_states: ModuleType,
) -> None:
    # REVIEW.md TST-419: through=another came on the first try with no window found in front: a window between
    # Designer's and the cover, or at another level, changes the reading unseen, and the log couldn't say whose
    hit = window_states._HITS.split('def hit():')[1].split('\n    mac.show()')[0]
    assert 'others.append(found)' in hit, 'counted as a window in the way: the reading is taken again'
    assert 'who(found)' in hit, 'named by its owner and layer'
    who = window_states._WINDOW.split('def who(')[1].split('\n    def ')[0]
    assert 'kCGWindowOwnerName' in who and 'kCGWindowLayer' in who
    printed = 'HITS opaque=main transparent=main through=another(Finder, layer 0)\nIN_FRONT 1\n'
    assert not window_states.nothing_in_front(printed)


def test_the_window_checks_drags_wait_for_the_view_to_take_each_move() -> None:
    # REVIEW.md TST-421, HLP-149: 0.2 s after each move, then 0.3 or 0.5 s; hidden or covered the view draws no frame,
    # but it asks for one (an UpdateRequest) once it took a move, and moves sent back to back were lost (measured)
    states = fresh('editor_panels_and_fit.window_states')
    for name in ('_DRAG', '_PANNED'):
        snippet = getattr(states, name)
        assert '_settle(' not in snippet, name
        assert snippet.count('.taking)') == snippet.count('_drag('), name


def test_an_event_during_the_pan_is_waited_for_by_its_state_not_a_fixed_time() -> None:
    # REVIEW.md TST-421: 0.5 s, "macOS says a window is covered about 0.07 s later"
    states = fresh('editor_panels_and_fit.window_states')
    assert '_settle(' not in states._DURING_PAN and 'until(' in states._DURING_PAN
    assert set(states.EVENT_DONE) == set(states.EVENTS)


def test_a_reading_after_a_shot_waits_for_the_state_it_is_read_for() -> None:
    # REVIEW.md TST-421: half a second, as macOS said a window was sent behind another about 0.1 s later
    states = fresh('editor_panels_and_fit.window_states')
    assert '_settle(' not in states._READ and '_settle(' not in states._PUT
    read = states.read(states.showing('covered=True'))
    assert 'until(' in read and "('covered=True',)" in read
    assert 'until(lambda: True)' in states.read()  # nothing to wait for: at once


def _check_source(module: str, name: str) -> str:
    """The source of `name`, a function or a constant of the self-test's `module` (a path under test_all_tools)."""
    import inspect

    found = getattr(fresh(module), name)
    return found if isinstance(found, str) else inspect.getsource(found)


@pytest.mark.parametrize(
    'order, shown',
    [('cover,main', True), ('main,cover', False), ('main', False), ('below,cover,later,main', True)],
    ids=['in front', 'behind', 'no cover', 'others between'],
)
def test_in_orders_condition_holds_only_for_the_order_it_names(order: str, shown: bool) -> None:
    # REVIEW.md TST-428: the conditions were tested by their text only, an inverted comparison passing
    states = fresh('editor_panels_and_fit.window_states')
    assert eval(states.in_order([('cover', 'main')]), {'order': lambda: order}) is shown


def test_showings_condition_needs_every_field() -> None:
    states = fresh('editor_panels_and_fit.window_states')
    condition = states.showing('covered=True', 'hidden=False')
    assert eval(condition, {'state': lambda: 'hidden=False covered=True exposed=False'}) is True
    assert eval(condition, {'state': lambda: 'hidden=True covered=True'}) is False
    assert eval(condition, {'state': lambda: 'hidden=False covered=Truer'}) is False


def test_the_covered_during_a_shot_check_starts_on_screen_and_reads_the_order_after() -> None:
    # REVIEW.md TST-422: it began from the hidden Designer clear() leaves, which the shot hid again, and a hidden
    # Designer reads covered=True: the put-back behind the cover passed whatever became of the order
    body = _check_source(
        'editor_panels_and_fit.checks', 'check_a_window_covered_during_a_3d_shot_is_put_in_front_again'
    )
    assert "put('on screen')" in body.replace('window_states.', '')
    assert "in_order([('cover', 'main')])" in body.replace('window_states.', '')
    assert "showing('covered=True')" not in body.replace('window_states.', '')
    assert "'hidden') == 'False'" in body


def test_who_reads_the_booleans_ctypes_returns_as_booleans() -> None:
    # REVIEW.md TST-430: CFStringGetCString and CFNumberGetValue return a Boolean, read as a c_int without a restype
    window = _check_source('editor_panels_and_fit.window_states', '_WINDOW')
    for name in ('CFStringGetCString', 'CFNumberGetValue'):
        assert 'cf.%s.restype = ctypes.c_bool' % name in window, name


def test_clear_ends_every_hold_and_makes_the_windows_opaque_only_once_designer_is_hidden() -> None:
    # REVIEW.md TST-431, not a bug: at rest every window is opaque and clickable (_CLEAR's comment); the looks put back
    # first only end their holds. Put back last, a look recorded while transparent stayed so: the covered way then drew
    # its view, and three window checks failed in a scratch run (2026-11-15). TST-474: put back whether or not the hide
    # took, the looks made the windows opaque, then fade(True) transparent again, on the user's screen
    import ast

    clear = _check_source('editor_panels_and_fit.window_states', '_CLEAR')
    assert clear.index("getattr(sys, 'mcp_selftest_looks'") < clear.rindex('fade(not hidden)')
    states = fresh('editor_panels_and_fit.window_states')
    looks = next(
        n
        for n in ast.walk(ast.parse(states._CLEAR))
        if isinstance(n, ast.For) and 'mcp_selftest_looks' in ast.unparse(n)
    )
    put = [n for n in ast.walk(looks) if isinstance(n, ast.Call) and ast.unparse(n.func) == 'mac.set_appearance']
    only_hidden = [n for n in ast.walk(looks) if isinstance(n, ast.If) and ast.unparse(n.test) == 'hidden']
    assert put and all(any(call in ast.walk(branch) for branch in only_hidden) for call in put), ast.unparse(looks)
    assert 'mac.let_go(w)' in [ast.unparse(statement) for statement in looks.body], 'every hold ended, hidden or not'


def test_the_wheel_steps_check_compares_two_renders_saved_alike() -> None:
    # REVIEW.md TST-423: a tool's shot shrunk to max_size against shoot_3d's render at full size: 255 for two sizes
    body = _check_source(
        'editor_panels_and_fit.checks', 'check_wheel_steps_sent_as_designers_window_goes_off_screen_are_all_taken'
    )
    assert "c('screenshot_designer', {**THREE_D, 'zoom': zoom})" not in body
    assert body.count('grey_file(') == 2


def test_the_material_check_judges_designer_hidden_again_and_puts_its_windows_back_in_a_finally() -> None:
    # REVIEW.md TST-425
    body = _check_source('editor_panels_and_fit.checks', 'check_a_material_the_mesh_doesnt_use_doesnt_stop_tiling')
    assert 'HIDDEN AGAIN=True' in body
    snippet = _check_source('editor_panels_and_fit.checks', 'ADD_MATERIAL')
    fade = snippet.index('mac.set_appearance(w, 0.0, True)')
    # REVIEW.md TST-437: a finally after the fade, which puts the windows back; where its try begins isn't judged
    assert snippet.index('finally:') > fade, 'a finally after the fade'
    assert snippet.index('mac.set_appearance(w, 1.0, False)') > snippet.index('finally:')
    # REVIEW.md TST-478: put back whatever the hide did, the windows went opaque on the user's screen, as _CLEAR's did
    # (TST-474); and Designer not hidden again stops the category, as no shot may take it for one an earlier shot left
    # transparent (shot3d.py, opaque_first)
    tree = ast.parse(snippet)
    put = [
        n for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n) == 'mac.set_appearance(w, 1.0, False)'
    ]
    only_hidden = [n for n in ast.walk(tree) if isinstance(n, ast.If) and ast.unparse(n.test) == 'mac.hidden()']
    assert put and all(any(call in ast.walk(branch) for branch in only_hidden) for call in put), snippet
    assert 'NOT_HIDDEN' in snippet and 'window_states.stopped_if_shown(added)' in body, body
    assert body.index('stopped_if_shown(added)') < body.index("'tiling': 2.0"), 'stopped before its 3D shot'


def test_a_clear_that_couldnt_hide_designer_stops_the_category(window_states: ModuleType) -> None:
    # REVIEW.md TST-478: its windows left transparent and click-through on screen, the next 3D shot made them opaque
    # where they were (shot3d.py, opaque_first), maybe in front of the user's windows: no check runs after it
    import asyncio

    from mcp.types import CallToolResult, TextContent

    printed = "NOT_HIDDEN Designer wasn't hidden: its windows left transparent and click-through\nSTATE hidden=False"
    with pytest.raises(RuntimeError, match="wasn't hidden"):
        window_states.stopped_if_shown(printed)
    window_states.stopped_if_shown('STATE hidden=True')  # hidden: nothing raised
    calls: list[str] = []

    async def c(name: str, args: ToolArgs) -> CallToolResult:
        calls.append(str(args['code']))
        return CallToolResult(content=[TextContent(type='text', text=printed)])

    with pytest.raises(RuntimeError, match="wasn't hidden"):
        asyncio.run(window_states.at_rest(c, 'HELPERS\n'))
    assert calls == ['HELPERS\n' + window_states._clear()]


def test_every_clear_of_the_window_checks_goes_through_at_rest() -> None:
    # REVIEW.md TST-478: a clear whose output went unread let the category go on with Designer shown; the snippet is
    # window_states' own (_clear), and no other module of the category builds it
    import os

    from conftest import SELFTEST_DIR

    folder = os.path.join(SELFTEST_DIR, 'editor_panels_and_fit')
    for name in sorted(os.listdir(folder)):
        if name.endswith('.py') and name != 'window_states.py':
            with open(os.path.join(folder, name)) as f:
                source = f.read()
            assert not re.search(r'window_states\.(_?clear\(|_CLEAR\b)|(?<![\w.])_?clear\(\)', source), name
    for name in ('checks.py', 'retries.py'):
        with open(os.path.join(folder, name)) as f:
            assert re.search(r'await at_rest\(', f.read()), name


def test_the_frames_facts_samples_off_wait_reads_the_paints_since_its_pan() -> None:
    # REVIEW.md TST-429: paints(read) read the whole list, never empty by then
    frames = _check_source('editor_panels_and_fit.checks', 'FRAMES')
    assert 'len(paints(read))' not in frames
    assert "'HIDDEN_PAINTS=" in frames  # every paint over the whole hidden stretch, up to its end


def _defs(states: ModuleType) -> dict[str, ast.FunctionDef]:
    """The functions the window checks' snippets define (window_states._WINDOW), by name."""
    return {n.name: n for n in ast.walk(ast.parse(states._WINDOW)) if isinstance(n, ast.FunctionDef)}


def _branch(code: str, test: str) -> ast.Module:
    """The body of the `if` (or `elif`) of `code` whose test reads `test`, without the branches after it."""
    found = next(n for n in ast.walk(ast.parse(code)) if isinstance(n, ast.If) and ast.unparse(n.test) == test)
    return ast.Module(body=found.body, type_ignores=[])


def _waits_not_stopping(node: ast.AST) -> list[str]:
    """The waits (until() calls) in `node` that aren't the test of an `if not` raising when their state didn't come."""
    stopping = {
        id(n.test.operand)
        for n in ast.walk(node)
        if isinstance(n, ast.If)
        and isinstance(n.test, ast.UnaryOp)
        and isinstance(n.test.op, ast.Not)
        and any(isinstance(s, ast.Raise) for s in n.body)
    }
    return [
        ast.unparse(n)
        for n in ast.walk(node)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'until' and id(n) not in stopping
    ]


def test_a_set_up_whose_wait_for_designers_window_runs_out_stops_before_it_places_a_window_or_makes_one_opaque() -> (
    None
):
    # REVIEW.md TST-460: until() returned nothing, so to_back, window() and the hidden way went on once its limit ran
    # out; Designer's windows, back near the front, were then made opaque in front of the user's
    states = fresh('editor_panels_and_fit.window_states')
    defs = _defs(states)
    last = defs['until'].body[-1]
    assert isinstance(last, ast.Return) and last.value is not None and ast.unparse(last.value) == 'state()'
    for name in ('window', 'to_back'):
        assert _waits_not_stopping(defs[name]) == [], name
    assert _waits_not_stopping(_branch(states.put('hidden'), "way == 'hidden'")) == []
    # at rest, made opaque only once Designer is hidden: left transparent and click-through otherwise
    clear = ast.parse(states._CLEAR)
    bare = [ast.unparse(n) for n in clear.body if isinstance(n, ast.Expr) and ast.unparse(n.value) == 'fade(False)']
    assert bare == [] and 'until(mac.hidden)' in states._CLEAR, bare


def test_a_window_the_checks_make_is_registered_for_the_clear_before_it_shows() -> None:
    # REVIEW.md TST-460: registered as window() returned, a window left by an abort after its show was never closed,
    # transparent and taking the user's clicks
    import re

    states = fresh('editor_panels_and_fit.window_states')
    window = ast.unparse(_defs(states)['window'])
    assert window.index("setattr(sys, 'mcp_selftest_' + name, made)") < window.index('made.show()')
    snippets = states._WINDOW + states._PUT + states._UNDER + ''.join(states.EVENTS.values())
    assert re.findall(r'sys\.mcp_selftest_\w+ = window\(', snippets) == [], 'window() registers its own'


def test_to_back_makes_designers_windows_transparent_before_it_shows_them_and_leaves_them_so() -> None:
    # REVIEW.md TST-470: shown first, Designer's windows came up near the front, opaque, until the orderBack:
    states = fresh('editor_panels_and_fit.window_states')
    to_back = ast.unparse(_defs(states)['to_back'])
    shows = [to_back.index(step) for step in ('mac.unhide()', "'deminiaturize:'", 'mw.setWindowState(')]
    assert to_back.index('fade(True)') < min(shows)
    assert max(shows) < to_back.index('until(shown_again)') < to_back.index("'orderBack:'")
    assert 'fade(False)' not in to_back, 'the caller makes them opaque, once behind'


def test_the_minimized_way_makes_designers_windows_opaque_only_once_the_window_is_off_screen() -> None:
    # REVIEW.md TST-472, measured: made opaque right after performMiniaturize:, the window flew to the Dock on screen,
    # at opacity 1, for about 0.55 s, 6 of 6
    states = fresh('editor_panels_and_fit.window_states')
    put = states.put('minimized')
    minimized = _branch(put, "way == 'minimized'")
    waits = [
        ast.unparse(n)
        for n in ast.walk(minimized)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'until'
    ]
    assert any('on_screen' in wait for wait in waits) and _waits_not_stopping(minimized) == [], waits
    assert "'performMiniaturize:'" in ast.unparse(minimized)
    assert 'fade(False)' not in ast.unparse(minimized), 'made opaque after it, with the other ways behind'
